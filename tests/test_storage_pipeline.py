"""Test doc upload to Supabase Storage + full pipeline against real data."""
import os, sys, asyncio, httpx, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv('.env.local', override=True)
from app.core.database import async_session_maker
from sqlalchemy import select, text

CASE_ID = "d379ee9b-19f7-4871-a86e-9684c69a11c3"  # from seeder
FIRM_ID = "11111111-1111-4111-8111-111111111111"

def make_pdf(title, content):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 700, title)
    c.setFont("Helvetica", 10)
    y = 670
    for line in content.split('\n'):
        if y < 50: c.showPage(); c.setFont("Helvetica", 10); y = 700
        c.drawString(50, y, line[:120]); y -= 14
    c.save()
    return buf.getvalue()

async def main():
    supa_url = os.environ.get('STORAGE_SUPABASE_URL','')
    supa_key = os.environ.get('STORAGE_SUPABASE_SERVICE_ROLE_KEY','')
    bucket = os.environ.get('STORAGE_BUCKET','trace-medical-records')
    
    print(f"Storage URL: {supa_url}")
    print(f"Key present: {bool(supa_key)}")
    print(f"Bucket: {bucket}")
    print()
    
    # 1. Verify case exists
    async with async_session_maker() as s:
        from app.models.case import Case
        r = await s.execute(select(Case).where(Case.case_id == CASE_ID))
        case = r.scalar_one_or_none()
        if not case:
            print("Case not found!")
            return
        print(f"[1] Case found: {case.case_id}")
        print(f"    Stage: {case.case_stage}")
        print(f"    HIPAA: {case.hipaa_auth_status}")
    
    # 2. Upload PDF to Supabase Storage
    doc_content = (
        "PATIENT: Maria Rodriguez\n"
        "DOB: 04/12/1985\n"
        "DATE OF SERVICE: 03/15/2024\n\n"
        "HISTORY: 38-year-old female presents with cervical spine pain\n"
        "following motor vehicle accident. Rear-end collision at intersection.\n"
        "Complains of neck pain radiating to shoulders, headaches,\n"
        "and limited range of motion.\n\n"
        "EXAMINATION: Cervical spine MRI performed 03/20/2024 shows\n"
        "C4-C5 disc herniation with C5-C6 bulging disc.\n"
        "Positive foraminal stenosis at C5-C6.\n"
        "Rotator cuff tear right shoulder confirmed on MRI.\n\n"
        "TREATMENT: Physical therapy initiated 03/22/2024, 2x/week.\n"
        "Prescribed: Cyclobenzaprine 10mg, Ibuprofen 800mg,\n"
        "Norco 5/325mg for breakthrough pain.\n"
        "Lumbar spine X-ray ordered to rule out additional injury.\n\n"
        "REFERRAL: Dr. James Wilson, Orthopedic Surgery,\n"
        "for surgical consultation regarding C4-C5 herniation.\n"
        "Pain management referral to Pacific Pain Center.\n\n"
        "DISCHARGE: Patient discharged home with prescriptions.\n"
        "Follow-up with primary care physician in 2 weeks.\n"
        "Released from Cedars-Sinai Emergency Department."
    )
    pdf = make_pdf("ER Visit - Cedars-Sinai Medical Center", doc_content)
    doc_name = f"er_note_{CASE_ID[:8]}.pdf"
    
    async with httpx.AsyncClient(timeout=30) as supa:
        r = await supa.post(
            f'{supa_url}/storage/v1/object/{bucket}/{doc_name}',
            headers={'Authorization': f'Bearer {supa_key}'},
            content=pdf,
        )
        print(f"[2] Upload: {r.status_code}")
        if r.status_code == 400 and 'already exists' in r.text.lower():
            print(f"    File already exists - OK")
        elif r.status_code not in (200, 201):
            print(f"    Error: {r.text[:200]}")
    
    # 3. Create Document record
    import uuid as uuid_mod
    async with async_session_maker() as s:
        from app.models.document import Document
        existing = await s.execute(select(Document).where(Document.s3_key == doc_name))
        doc = existing.scalar_one_or_none()
        if doc:
            print(f"[3] Doc exists: {doc.document_id}")
        else:
            doc = Document(
                case_id=CASE_ID, provider_id=None,
                s3_bucket=bucket, s3_key=doc_name,
                document_type='ER_NOTE', page_count=1,
                ocr_status='PENDING', source='ATTORNEY_UPLOAD',
                original_filename=doc_name,
            )
            s.add(doc); await s.commit()
            print(f"[3] Doc created: {doc.document_id}")
    
    # 4. Simulate OCR + chronology (direct python, not API)
    print(f"\n[4] Simulating OCR via Mistral...")
    
    # Download the PDF back
    async with httpx.AsyncClient(timeout=60) as supa:
        r = await supa.get(
            f'{supa_url}/storage/v1/object/{bucket}/{doc_name}',
            headers={'Authorization': f'Bearer {supa_key}'},
        )
        if r.status_code == 200:
            pdf_bytes = r.content
            print(f"    Downloaded PDF: {len(pdf_bytes)} bytes")
            
            # Run the OCR pipeline
            from app.services.ocr_pipeline import run_ocr_pipeline
            from app.services.chronology import build_chronology
            
            ocr_result = await run_ocr_pipeline(CASE_ID, pdf_bytes)
            print(f"    OCR method: {ocr_result.method}")
            print(f"    Pages: {len(ocr_result.pages)}")
            
            if ocr_result.pages:
                page = ocr_result.pages[0]
                print(f"    Raw text length: {len(page.raw_text)}")
                print(f"    Redacted length: {len(page.redacted_text)}")
                print(f"    Full text: {page.raw_text[:300]}")
                print(f"    Quality flags: {page.quality_flags}")
            
            # Build chronology from OCR output
            redacted = [{'redacted_text': p.redacted_text, 'page_number': p.page_number} 
                        for p in ocr_result.pages if p.redacted_text]
            chron = await build_chronology(CASE_ID, redacted)
            print(f"\n[5] Chronology: {chron.total_entries} entries")
            if chron.entries:
                for e in chron.entries[:3]:
                    print(f"    - {e.event_date.date()} | {e.event_type.value} | {e.clinical_description[:60]}")
            else:
                print(f"    (No clinical entities found in text)")
            
            # Export
            from app.services.export import ChronologyExporter
            exporter = ChronologyExporter()
            entries_dicts = [{'event_date': e.event_date.isoformat(), 'event_type': e.event_type.value, 'description': e.clinical_description, 'provider': e.facility_name} for e in chron.entries]
            try:
                json_out = exporter.export_json("SYN-001", "2024-03-15", "2026-03-15", "v1", True, entries_dicts)
                print(f"[6] Export JSON: {len(json_out)} bytes")
            except Exception as exc:
                print(f"[6] Export JSON: {exc}")
        else:
            print(f"    Download failed: {r.status_code}")
    
    print(f"\nPipeline complete")

import json
asyncio.run(main())

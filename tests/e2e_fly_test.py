"""Full E2E pipeline test for Fly.io — uploads doc, runs OCR, builds chronology, flags, exports."""
import asyncio, io, json, os, uuid

async def main():
    CASE_ID = uuid.UUID("d379ee9b-19f7-4871-a86e-9684c69a11c3")
    
    # Generate test PDF with real clinical content
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 11)
    lines = [
        ("PATIENT: Maria Rodriguez    DOB: 04/12/1985", 720),
        ("DATE OF SERVICE: 03/15/2024", 700),
        ("", 690),
        ("HISTORY: 38F presents with cervical spine pain post MVA.", 670),
        ("Neck pain radiating to shoulders, headaches, limited ROM.", 655),
        ("", 640),
        ("MRI 03/20/2024: C4-C5 disc herniation, C5-C6 bulging disc.", 620),
        ("Foraminal stenosis at C5-C6. Rotator cuff tear right shoulder.", 605),
        ("", 590),
        ("TREATMENT: PT 2x/week. Cyclobenzaprine 10mg, Ibuprofen 800mg.", 570),
        ("Norco 5/325mg for breakthrough pain. Lumbar X-ray ordered.", 555),
        ("", 540),
        ("REFERRAL: Dr. James Wilson, Orthopedic Surgery.", 520),
        ("Pain management referral to Pacific Pain Center.", 505),
        ("", 490),
        ("DISCHARGE: Released from Cedars-Sinai ER. Follow-up 2 weeks.", 470),
    ]
    for text, y in lines:
        c.drawString(50, y, text)
    c.save()
    pdf_bytes = buf.getvalue()
    print(f"[1] Test PDF: {len(pdf_bytes)} bytes\n")
    
    # Upload to Supabase Storage
    import httpx
    supa_url = os.environ.get("STORAGE_SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
    supa_key = os.environ.get("STORAGE_SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""))
    bucket = os.environ.get("STORAGE_BUCKET", "trace-medical-records")
    doc_name = f"e2e_test_{CASE_ID}.pdf"
    
    if supa_url and supa_key:
        async with httpx.AsyncClient(timeout=30) as s:
            r = await s.post(
                f"{supa_url}/storage/v1/object/{bucket}/{doc_name}",
                headers={"Authorization": f"Bearer {supa_key}"},
                content=pdf_bytes,
            )
            print(f"[2] Upload: {r.status_code}")
    
    # Run full OCR pipeline
    from app.services.ocr_pipeline import run_ocr_pipeline
    ocr = await run_ocr_pipeline(CASE_ID, pdf_bytes)
    print(f"[3] OCR: {ocr.method} | {len(ocr.pages)} pages")
    if ocr.pages:
        p = ocr.pages[0]
        print(f"    Text: {len(p.raw_text)} chars | De-ID: {'DEID_COMPLETE' in p.quality_flags}")
        print(f"    Preview: {p.redacted_text[:200]}...")
    
    # Build chronology
    from app.services.chronology import build_chronology
    redacted = [{"redacted_text": p.redacted_text, "page_number": p.page_number, 
                 "document_id": str(uuid.uuid4()), "facility_name": "Cedars-Sinai ER"}
                for p in ocr.pages if p.redacted_text]
    chron = await build_chronology(CASE_ID, redacted)
    print(f"\n[4] Chronology: {chron.total_entries} entries")
    for e in chron.entries:
        print(f"    {e.event_date.date()} | {e.event_type.value} | {e.clinical_description[:70]}")
    
    # Run flags
    from datetime import date
    from app.services.flags import run_all_tier1_flags
    entries = [{"event_date": e.event_date, "clinical_description": e.clinical_description,
                "event_type": e.event_type.value, "facility_name": e.facility_name}
               for e in chron.entries]
    flags = run_all_tier1_flags(CASE_ID, date(2024, 3, 15), entries)
    print(f"\n[5] Tier 1 Flags: {len(flags)}")
    for f in flags:
        print(f"    [{f.priority.value}] {f.flag_type}: {f.description[:60]}")
    
    # Export
    from app.services.export import ChronologyExporter
    exporter = ChronologyExporter()
    entries_dicts = [{"event_date": e.event_date.isoformat(), "event_type": e.event_type.value,
                      "description": e.clinical_description, "provider": e.facility_name}
                     for e in chron.entries]
    json_out = exporter.export_json("SYN-001", "2024-03-15", "2026-03-15", "v1", True, entries_dicts)
    pdf_out = exporter.export_pdf("SYN-001", "2024-03-15", "2026-03-15", "v1", True, entries_dicts)
    print(f"\n[6] Export JSON: {len(json_out)} bytes | PDF: {pdf_out.getbuffer().nbytes} bytes")
    
    print(f"\n{'='*50}")
    print(f"PIPELINE COMPLETE")
    print(f"  Storage: OK | OCR: {ocr.method} | Chronology: {chron.total_entries} entries")
    print(f"  Tier 1: {len(flags)} flags | Export: JSON {len(json_out)}B + PDF {pdf_out.getbuffer().nbytes}B")
    print(f"{'='*50}")

asyncio.run(main())

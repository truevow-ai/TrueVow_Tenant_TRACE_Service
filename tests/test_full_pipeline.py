"""Full pipeline test: upload docs -> OCR -> chronology -> flags -> export."""
import os, sys, asyncio, uuid, jwt, httpx, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['ENVIRONMENT']='development'
os.environ['AUTH_MODE']='local'
os.environ['LOCAL_JWT_SECRET']='test-secret-at-least-32-bytes-long-000'
from dotenv import load_dotenv; load_dotenv('.env.local', override=True)
from app.main import app
from app.core.database import async_session_maker

FIRM_ID = uuid.UUID('11111111-1111-4111-8111-111111111111')

def auth_header():
    token = jwt.encode({'sub':'test','firm_id':str(FIRM_ID),'role':'attorney'},
                        'test-secret-at-least-32-bytes-long-000', algorithm='HS256')
    return {'Authorization': f'Bearer {token}'}

def make_test_pdf(title, content):
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
        c.drawString(50, y, line[:120])
        y -= 14
    c.save()
    return buf.getvalue()

async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as c:
        h = auth_header()
        print("=" * 50)
        print("FULL PIPELINE TEST")
        print("=" * 50)
        
        # 1. Create case
        r = await c.post('/api/v1/trace/cases', headers=h, json={
            'intake_record_id': str(uuid.uuid4()),
            'client_data': {'name':'Pipeline Test','dob':'1990-01-01','address':'123 St','phone':'555'},
            'incident_date': '2024-01-15', 'jurisdiction_state': 'CA',
        })
        case = r.json()
        cid = case.get('case_id','')
        print(f'[1] Case: {cid} stage={case.get("stage")}')
        if not cid:
            print('Case creation failed')
            return
        
        # 2. Document
        supabase_url = os.environ.get('STORAGE_SUPABASE_URL','')
        supabase_key = os.environ.get('STORAGE_SUPABASE_SERVICE_ROLE_KEY','')
        bucket = os.environ.get('STORAGE_BUCKET','trace-medical-records')
        
        doc_content = (
            "PATIENT: Pipeline Test | DOB: 01/01/1990\n"
            "DATE OF VISIT: 01/15/2024\n\n"
            "HISTORY: Neck pain and headaches post MVA 01/15/2024. Rear-end collision.\n"
            "EXAMINATION: Cervical tenderness C4-C6. Limited ROM. Muscle spasms.\n"
            "MRI: Ordered 01/20/2024.\n"
            "ASSESSMENT: Cervical strain. Rule out disc herniation.\n"
            "PLAN: PT 2x/week x6weeks. Referral ortho. Cyclobenzaprine 10mg."
        )
        pdf_bytes = make_test_pdf("ER Visit - Cedars-Sinai", doc_content)
        doc_name = f"er_note_{cid[:8]}.pdf"
        
        # Upload using Supabase Storage REST API
        async with httpx.AsyncClient(timeout=30) as supa:
            r = await supa.post(
                f'{supabase_url}/storage/v1/object/{bucket}/{doc_name}',
                headers={'Authorization': f'Bearer {supabase_key}'},
                content=pdf_bytes,
            )
            print(f'[2] Upload: {r.status_code} {r.text[:80]}')
        
        # 3. Create document record
        async with async_session_maker() as session:
            from app.models.document import Document
            doc = Document(
                case_id=uuid.UUID(cid), provider_id=None,
                s3_bucket=bucket, s3_key=doc_name,
                document_type='ER_NOTE', page_count=1,
                ocr_status='PENDING', source='api_upload',
                original_filename=doc_name,
            )
            session.add(doc); await session.commit()
            print(f'[3] Doc record: {doc.document_id}')
        
        # 4. Chronology
        r = await c.get(f'/api/v1/trace/cases/{cid}/chronology', headers=h)
        print(f'[4] Chronology: {r.json().get("total_entries",0)} entries | stage={r.json().get("case_stage")}')
        
        # 5. Readiness
        r = await c.get(f'/api/v1/trace/cases/{cid}/readiness', headers=h)
        d = r.json()
        print(f'[5] Readiness: stage={d.get("stage")} | providers={d.get("provider_count")} | liens={d.get("lien_count")} | ready={d.get("ready_to_export")}')
        
        # 6. Export
        r = await c.get(f'/api/v1/trace/cases/{cid}/export?format=json', headers=h)
        print(f'[6] Export: {r.status_code} ({len(r.content)} bytes)' if r.status_code==200 else f'[6] Export: {r.status_code}')
        
        print(f"\nCase: {cid}")
        print("=" * 50)

asyncio.run(main())

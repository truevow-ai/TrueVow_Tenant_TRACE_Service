"""Test attorney upload + portal link routes."""
import os, sys, io, jwt, httpx, asyncio, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['ENVIRONMENT']='development'
os.environ['AUTH_MODE']='local'
os.environ['LOCAL_JWT_SECRET']='test-secret-at-least-32-bytes-long-000'
from dotenv import load_dotenv
load_dotenv('.env.local', override=True)
os.environ['AUTH_MODE']='local'  # re-override after dotenv
os.environ['LOCAL_JWT_SECRET']='test-secret-at-least-32-bytes-long-000'
from app.main import app

FIRM = '11111111-1111-4111-8111-111111111111'
CASE = 'd379ee9b-19f7-4871-a86e-9684c69a11c3'

def auth():
    t = jwt.encode({'sub':'test','firm_id':FIRM,'role':'attorney'}, 'test-secret-at-least-32-bytes-long-000', algorithm='HS256')
    return {'Authorization': f'Bearer {t}'}

async def test():
    t = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=t, base_url='http://test') as c:
        h = auth()
        
        # 1. Upload test
        pdf = io.BytesIO(b'%PDF-1.4 test content')
        r = await c.post(f'/api/v1/trace/cases/{CASE}/documents/upload', headers=h, files={'file': ('test.pdf', pdf, 'application/pdf')})
        print(f'[1] Upload: {r.status_code} {r.text[:200]}')
        
        # 2. Portal link test (won't work without real URL but validates route exists)
        r = await c.post(f'/api/v1/trace/cases/{CASE}/documents/portal-link', headers=h, json={
            'url': 'https://example.com/test.pdf', 'filename': 'portal_test.pdf'
        })
        print(f'[2] Portal: {r.status_code} {r.text[:200]}')

asyncio.run(test())

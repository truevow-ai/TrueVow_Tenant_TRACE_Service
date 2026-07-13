import os, sys, jwt, httpx, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['ENVIRONMENT']='development'
os.environ['AUTH_MODE']='local'
os.environ['LOCAL_JWT_SECRET']='test-secret-at-least-32-bytes-long-000'
from app.main import app
transport = httpx.ASGITransport(app=app)

async def test():
    token = jwt.encode({
        'sub':'test','firm_id':'11111111-1111-4111-8111-111111111111','role':'attorney'
    }, os.environ['LOCAL_JWT_SECRET'], algorithm='HS256')
    h = {'Authorization': f'Bearer {token}'}
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as c:
        r = await c.get('/api/v1/trace/cases', headers=h)
        print('LIST:', r.status_code)
        cases = r.json().get('cases', [])
        if cases:
            cid = cases[0]['case_id']
            print('First case:', cid)
            r2 = await c.get(f'/api/v1/trace/cases/{cid}', headers=h)
            print('GET case:', r2.status_code, r2.text[:150])
            r3 = await c.get(f'/api/v1/trace/cases/{cid}/providers', headers=h)
            print('Providers:', r3.status_code, r3.text[:150])
            r4 = await c.get(f'/api/v1/trace/cases/{cid}/liens', headers=h)
            print('Liens:', r4.status_code, r4.text[:150])
        else:
            print('No cases found')

        # Try creating one
        r5 = await c.post('/api/v1/trace/cases', headers=h, json={
            "intake_record_id": str(__import__('uuid').uuid4()),
            "client_data": {"name":"Test","dob":"1990-01-01","address":"123 St","phone":"555"},
            "incident_date": "2024-01-01",
            "jurisdiction_state": "CA",
        })
        print('CREATE:', r5.status_code, r5.text[:150])
        if r5.status_code == 201:
            cid = r5.json().get('case_id')
            r6 = await c.get(f'/api/v1/trace/cases/{cid}', headers=h)
            print('GET created:', r6.status_code, r6.text[:150])

asyncio.run(test())

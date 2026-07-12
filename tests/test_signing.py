import os, sys, jwt, httpx, asyncio, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['ENVIRONMENT']='development'
os.environ['AUTH_MODE']='local'
os.environ['LOCAL_JWT_SECRET']='test-secret-at-least-32-bytes-long-000'

async def test():
    token = jwt.encode({'sub':'test','firm_id':'11111111-1111-4111-8111-111111111111','role':'attorney'}, 
                        os.environ['LOCAL_JWT_SECRET'], algorithm='HS256')
    h = {'Authorization': f'Bearer {token}'}
    async with httpx.AsyncClient(base_url='https://truevow-trace.fly.dev', timeout=30) as c:
        # Get existing case
        r = await c.get('/api/v1/trace/cases', headers=h)
        cases = r.json().get('cases', [])
        if cases:
            cid = cases[0]['case_id']
            print(f'Case: {cid} stage={cases[0].get("case_stage","?")}')
            r2 = await c.post(f'/api/v1/trace/cases/{cid}/signing/send', headers=h, json={
                'signer_email': 'synthetic@truevow.law',
                'signer_name': 'Test Client',
            })
            print(f'Signing: {r2.status_code} {r2.text[:300]}')
        else:
            print('No cases')

asyncio.run(test())

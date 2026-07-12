import asyncio, os
from dotenv import load_dotenv
load_dotenv('.env.local', override=True)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

url = os.getenv('TRACE_DATABASE_URL','').replace('postgresql://','postgresql+asyncpg://',1)

async def fix():
    e = create_async_engine(url, connect_args={
        'statement_cache_size': 0,
        'server_settings': {'search_path': 'trace'}
    })
    async with e.begin() as c:
        await c.execute(text(
            "ALTER TABLE trace.audit_log ALTER COLUMN ip_address "
            "TYPE VARCHAR(45) USING COALESCE(ip_address::text, '')"
        ))
        print('audit_log.ip_address -> VARCHAR(45)')
    await e.dispose()

asyncio.run(fix())

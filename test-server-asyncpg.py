#!/usr/bin/env python3
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Testing: {DATABASE_URL[:50]}...")

async def test():
    try:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
        print("✅ AsyncPG pool created successfully!")
        async with pool.acquire() as conn:
            result = await conn.fetchrow("SELECT 1 as test")
            print(f"✅ Query result: {result}")
        await pool.close()
    except Exception as e:
        print(f"❌ AsyncPG Error: {e}")

if __name__ == "__main__":
    asyncio.run(test()) 
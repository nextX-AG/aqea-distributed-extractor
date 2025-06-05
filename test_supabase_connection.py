#!/usr/bin/env python3
"""Test Supabase connection locally"""

import asyncio
import sys
import os
import traceback
import asyncpg
from urllib.parse import unquote
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('.')

from src.utils.config import Config
from src.database.supabase import SupabaseDatabase

async def test_connection():
    print("=== Supabase Connection Test ===")
    
    # Check environment variables
    db_url = os.getenv('DATABASE_URL', 'NOT_SET')
    print(f"DATABASE_URL: {db_url}")
    print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT_SET')}")
    
    # URL decode test
    decoded_url = unquote(db_url)
    print(f"Decoded URL: {decoded_url}")
    
    # Load config and create database instance
    config = Config.load('config/default.yml')
    db = SupabaseDatabase(config)
    
    print(f"Constructed DB URL: {db.database_url}")
    
    # Direct asyncpg test
    print("\n=== Direct asyncpg Test ===")
    try:
        print("Testing direct asyncpg connection...")
        conn = await asyncpg.connect(db.database_url)
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Direct connection successful! Result: {result}")
        await conn.close()
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
    
    # Test with URL decoding
    print("\n=== Testing with decoded URL ===")
    try:
        print("Testing with URL-decoded connection string...")
        conn = await asyncpg.connect(decoded_url)
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Decoded URL connection successful! Result: {result}")
        await conn.close()
    except Exception as e:
        print(f"❌ Decoded URL connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
    
    # Test connection pool
    print("\n=== Testing Connection Pool ===")
    try:
        print("Attempting pool connection...")
        result = await db.connect()
        print(f"Pool connection result: {result}")
        
        if result:
            print("✅ Supabase connection working!")
            await db.disconnect()
        else:
            print("❌ Pool connection failed")
            
    except Exception as e:
        print(f"❌ Pool connection error: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection()) 
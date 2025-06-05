#!/usr/bin/env python3
"""Test new Supabase implementation"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('.')

from src.utils.config import Config
from src.database.supabase import SupabaseDatabase
from src.aqea.schema import AQEAEntry
from datetime import datetime

async def test_new_supabase():
    print("=== New Supabase Implementation Test ===")
    
    # Check environment variables
    print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT_SET')}")
    print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY', 'NOT_SET')[:20]}...")
    
    # Load config and create database instance
    config = Config.load('config/default.yml')
    
    try:
        db = SupabaseDatabase(config)
        print(f"✅ SupabaseDatabase instance created")
        print(f"Supabase URL: {db.supabase_url}")
        
        # Test connection
        print("\n=== Testing Connection ===")
        result = await db.connect()
        print(f"Connection result: {result}")
        
        if result:
            print("✅ Connection successful!")
            
            # Test storing a sample AQEA entry
            print("\n=== Testing AQEA Entry Storage ===")
            test_entry = AQEAEntry(
                address="0x20:01:01:01",
                label="Test Wort",
                description="German word 'Test Wort'. A test entry for validation.",
                domain="0x20",
                lang_ui="de",
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="test-system",
                meta={
                    "lemma": "Test",
                    "source": "test",
                    "pos": "noun"
                }
            )
            
            # Store the entry
            store_result = await db.store_aqea_entries([test_entry])
            print(f"Store result: {store_result}")
            
            if store_result['inserted'] > 0:
                print("✅ AQEA entry stored successfully!")
                
                # Try to retrieve it
                print("\n=== Testing AQEA Entry Retrieval ===")
                retrieved = await db.get_aqea_entry("0x20:01:01:01")
                if retrieved:
                    print(f"✅ Retrieved entry: {retrieved.label}")
                    print(f"   Address: {retrieved.address}")
                    print(f"   Description: {retrieved.description}")
                else:
                    print("❌ Could not retrieve entry")
            else:
                print("❌ Failed to store AQEA entry")
            
            # Test statistics
            print("\n=== Testing Statistics ===")
            stats = await db.get_extraction_statistics()
            print(f"Statistics: {stats}")
            
            await db.disconnect()
        else:
            print("❌ Connection failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_new_supabase()) 
#!/usr/bin/env python3
"""Teste die aktuelle Adressallokation"""

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
from datetime import datetime

async def test_address_allocation():
    print("=== Adressallokation Test ===")
    
    # Load config and create database instance
    config = Config.load('config/default.yml')
    
    try:
        db = SupabaseDatabase(config)
        print(f"✅ SupabaseDatabase instance created")
        
        # Test connection
        print("\n=== Testing Connection ===")
        result = await db.connect()
        print(f"Connection result: {result}")
        
        if result:
            print("✅ Connection successful!")
            
            # Test getting allocated addresses
            print("\n=== Testing get_allocated_addresses ===")
            addresses = await db.get_allocated_addresses(None)
            print(f"Found {len(addresses)} categories with allocations")
            for category, ids in addresses.items():
                print(f"Category {category}: {len(ids)} addresses allocated")
                if len(ids) > 0:
                    print(f"  First few IDs: {ids[:5]}")
            
            # Test allocating a new address
            print("\n=== Testing allocate_address ===")
            test_category = "20:01:01"  # Deutsch:Nomen:Natur
            test_element_id = 42
            test_word = "Testword"
            
            allocated_id = await db.allocate_address(
                test_category, test_element_id, "test-script", test_word
            )
            
            if allocated_id is not None:
                print(f"✅ Successfully allocated address in category {test_category}")
                print(f"  Allocated ID: {allocated_id}")
                
                # Verify allocation by getting it again
                print("\n=== Verifying allocation ===")
                addresses = await db.get_allocated_addresses(test_category)
                if test_category in addresses:
                    if allocated_id in addresses[test_category]:
                        print(f"✅ Allocation verified! ID {allocated_id} is in category {test_category}")
                    else:
                        print(f"❌ Allocation not found in retrieved addresses!")
                else:
                    print(f"❌ Category {test_category} not found in retrieved addresses!")
            else:
                print(f"❌ Failed to allocate address in category {test_category}")
            
            await db.disconnect()
        else:
            print("❌ Connection failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_address_allocation()) 
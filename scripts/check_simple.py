#!/usr/bin/env python3
"""Einfache Überprüfung der Tabelle address_allocations"""

import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

def check_table():
    print("=== Simple Table Check ===")
    
    # Get credentials from environment
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    # Create Supabase client
    supabase = create_client(url, key)
    print("✅ Supabase client created")
    
    # Try to select columns that don't exist to trigger an error that shows available columns
    try:
        result = supabase.table('address_allocations').select('this_column_doesnt_exist').limit(1).execute()
    except Exception as e:
        print(f"Expected error (shows available columns): {e}")
    
    # Try to insert a test row
    try:
        print("\n=== Trying a test insertion ===")
        # Test with different possible column names
        test_row = {
            'category_key': 'test_key',
            'element_id': 1,
            'word': 'test',
            'allocated_by': 'test',
            'allocated_at': '2023-01-01'
        }
        result = supabase.table('address_allocations').insert(test_row).execute()
        print(f"Insert result: {result.data}")
    except Exception as e:
        print(f"Insert error (shows column validation): {e}")
    
    # Try simple query
    try:
        print("\n=== Trying a simple query ===")
        result = supabase.table('address_allocations').select('*').limit(5).execute()
        if result.data:
            print(f"Found {len(result.data)} rows")
            if len(result.data) > 0:
                print(f"Column names: {list(result.data[0].keys())}")
        else:
            print("No data found in table")
    except Exception as e:
        print(f"Query error: {e}")

if __name__ == "__main__":
    check_table() 
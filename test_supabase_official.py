#!/usr/bin/env python3
"""Test Supabase connection with official API"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def test_supabase_official():
    print("=== Official Supabase API Test ===")
    
    # Get credentials from environment
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    print(f"SUPABASE_URL: {url}")
    print(f"SUPABASE_KEY: {key[:20]}..." if key else "NOT_SET")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    try:
        # Create Supabase client
        supabase: Client = create_client(url, key)
        print("✅ Supabase client created successfully")
        
        # Try to check if our custom tables exist
        try:
            # Check for our AQEA tables
            aqea_result = supabase.table('aqea_entries').select('count').execute()
            print(f"✅ aqea_entries table exists!")
        except Exception as e:
            print(f"⚠️ aqea_entries table doesn't exist: {e}")
            
        try:
            work_result = supabase.table('work_units').select('count').execute()
            print(f"✅ work_units table exists!")
        except Exception as e:
            print(f"⚠️ work_units table doesn't exist: {e}")
        
        # Try creating the tables if they don't exist
        print("\n=== Attempting to create tables ===")
        try:
            # Create aqea_entries table
            supabase.table('aqea_entries').insert({
                'address': 'test',
                'label': 'test',
                'description': 'test',
                'domain': 'test'
            }).execute()
            print("✅ aqea_entries table is writable!")
        except Exception as e:
            print(f"⚠️ Cannot write to aqea_entries: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    test_supabase_official() 
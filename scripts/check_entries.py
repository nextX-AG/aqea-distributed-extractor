#!/usr/bin/env python3
"""Überprüfe die aktuell in Supabase gespeicherten AQEA-Einträge"""

import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

async def check_aqea_entries():
    print("=== AQEA-Einträge in Supabase ===")
    
    # Get credentials from environment
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    try:
        # Create Supabase client
        supabase = create_client(url, key)
        print("✅ Supabase client created")
        
        # Get count of AQEA entries
        result = supabase.table('aqea_entries').select('count').execute()
        if hasattr(result, 'count'):
            count = result.count
        else:
            count = len(result.data) if result.data else 0
            
        print(f"✅ Total AQEA entries: {count}")
        
        # Get sample entries
        entries = supabase.table('aqea_entries').select('*').limit(5).execute()
        
        if entries.data:
            print(f"\n=== Sample entries ({len(entries.data)}) ===")
            for i, entry in enumerate(entries.data):
                print(f"\nEntry {i+1}:")
                print(f"  Address: {entry.get('address')}")
                print(f"  Label: {entry.get('label')}")
                print(f"  Description: {entry.get('description')}")
                print(f"  Created at: {entry.get('created_at')}")
        else:
            print("No entries found")
            
        # Get entries by domain
        domains_result = supabase.table('aqea_entries').select('domain,count').group_by('domain').execute()
        if domains_result.data:
            print("\n=== Entries by domain ===")
            for domain_data in domains_result.data:
                domain = domain_data.get('domain')
                count = domain_data.get('count')
                print(f"  {domain}: {count} entries")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_aqea_entries()) 
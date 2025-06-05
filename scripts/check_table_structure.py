#!/usr/bin/env python3
"""Überprüfe die Struktur der Tabellen in Supabase"""

import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

async def check_table_structure():
    print("=== Checking Supabase Table Structure ===")
    
    # Get credentials from environment
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    
    print(f"SUPABASE_URL: {url}")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_KEY")
        return
    
    try:
        # Create Supabase client
        supabase = create_client(url, key)
        print("✅ Supabase client created successfully")
        
        # Check if address_allocations table exists and get its structure
        print("\n=== Checking 'address_allocations' table ===")
        
        # First, check if table exists by trying to select from it
        try:
            # Try to select one row (will fail if table doesn't exist)
            result = supabase.table('address_allocations').select('*').limit(1).execute()
            print("✅ Table 'address_allocations' exists")
            
            # If that worked, check the columns by using a simple query
            # This query will return information about the columns
            # Use RPC function to get column information
            rpc_result = supabase.rpc('get_table_columns', {'table_name': 'address_allocations'}).execute()
            if not hasattr(rpc_result, 'data'):
                print("⚠️ Could not get column information via RPC")
                # Fallback: Try to check columns by selecting with a specific structure
                print("\n=== Fallback: Checking columns directly ===")
                # Try to get actual column names by selecting a row and inspecting keys
                result = supabase.table('address_allocations').select('*').limit(1).execute()
                if result.data and len(result.data) > 0:
                    print(f"Column names: {list(result.data[0].keys())}")
                else:
                    print("No data in table, trying alternative method")
                    # Try to deliberately cause an error to see column names in error message
                    try:
                        supabase.table('address_allocations').select('non_existent_column').limit(1).execute()
                    except Exception as e:
                        print(f"Error response (contains available columns): {str(e)}")
            else:
                # Process RPC result
                columns = rpc_result.data
                print(f"Found {len(columns)} columns in 'address_allocations' table:")
                for col in columns:
                    print(f"  - {col['column_name']} ({col['data_type']})")
        
        except Exception as e:
            print(f"❌ Error checking 'address_allocations' table: {e}")
            print("Table might not exist or there's a permissions issue")
            
            # Try to get a list of all tables
            print("\n=== Trying to list all tables ===")
            try:
                # Execute a query to list tables (might need RLS bypass or admin rights)
                rpc_result = supabase.rpc('get_all_tables').execute()
                if hasattr(rpc_result, 'data'):
                    tables = rpc_result.data
                    print(f"Available tables: {', '.join(tables)}")
                else:
                    print("Could not list tables via RPC")
            except Exception as list_err:
                print(f"❌ Could not list tables: {list_err}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

# Create RPC functions for getting table info
async def create_helper_functions():
    # This part requires admin rights, so it's usually done once
    # during setup, not in this check script
    pass

if __name__ == "__main__":
    asyncio.run(check_table_structure()) 
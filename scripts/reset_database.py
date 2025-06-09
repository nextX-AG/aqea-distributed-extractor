#!/usr/bin/env python3
"""
AQEA Database Reset Script

Komplett leert alle AQEA-Datenbanken:
- SQLite lokale Datenbank
- Supabase Cloud-Datenbank
- Lokale JSON-Fallback-Dateien

Usage:
    python scripts/reset_database.py --confirm
    python scripts/reset_database.py --sqlite-only
    python scripts/reset_database.py --supabase-only
"""

import asyncio
import argparse
import os
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from database import get_database
from utils.config import Config


async def reset_sqlite_database():
    """Reset local SQLite database."""
    print("🗑️  Resetting SQLite database...")
    
    # Remove SQLite database file if exists
    sqlite_files = ['aqea_database.db', 'aqea_database.db-journal', 'aqea_database.db-wal']
    
    removed_count = 0
    for file in sqlite_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"   ✅ Removed {file}")
            removed_count += 1
    
    if removed_count == 0:
        print("   ℹ️  No SQLite database files found")
    else:
        print(f"   ✅ {removed_count} SQLite files removed")


async def reset_supabase_database():
    """Reset Supabase cloud database."""
    print("☁️  Resetting Supabase database...")
    
    try:
        # Load config for Supabase
        config_obj = Config()
        config = config_obj.data
        config['database'] = config.get('database', {})
        config['database']['type'] = 'supabase'  # Force Supabase mode
        
        # Get Supabase database instance
        db = await get_database(config)
        
        if db is None:
            print("   ❌ Supabase database not available")
            return False
        
        # Get current entries count
        try:
            # Use Supabase client to get count
            result = db.client.table('aqea_entries').select('address', count='exact').execute()
            count_before = result.count if hasattr(result, 'count') else 0
            print(f"   📊 Found {count_before} entries in Supabase")
        except Exception as e:
            print(f"   ⚠️  Could not count entries: {e}")
            count_before = "unknown"
        
        # Delete all entries from aqea_entries table
        try:
            # Supabase doesn't have a direct "delete all" - we need to use a condition
            # Let's delete where address is not null (which should be all entries)
            result = db.client.table('aqea_entries').delete().neq('address', '').execute()
            print(f"   ✅ Deleted all AQEA entries")
        except Exception as e:
            print(f"   ⚠️  Error deleting AQEA entries: {e}")
        
        # Delete all work units
        try:
            result = db.client.table('work_units').delete().neq('work_id', '').execute()
            print(f"   ✅ Deleted all work units")
        except Exception as e:
            print(f"   ⚠️  Error deleting work units: {e}")
        
        # Delete all worker status
        try:
            result = db.client.table('worker_status').delete().neq('worker_id', '').execute()
            print(f"   ✅ Deleted all worker status")
        except Exception as e:
            print(f"   ⚠️  Error deleting worker status: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error resetting Supabase: {e}")
        return False


def reset_local_files():
    """Reset local JSON fallback files."""
    print("📁 Resetting local extracted data files...")
    
    # Remove extracted_data directory contents
    extracted_data_dir = Path('extracted_data')
    
    if not extracted_data_dir.exists():
        print("   ℹ️  No extracted_data directory found")
        return
    
    removed_count = 0
    for file in extracted_data_dir.iterdir():
        if file.is_file() and (file.suffix == '.json' or file.name.startswith('aqea_entries_')):
            file.unlink()
            print(f"   ✅ Removed {file.name}")
            removed_count += 1
    
    if removed_count == 0:
        print("   ℹ️  No extracted data files found")
    else:
        print(f"   ✅ {removed_count} extracted data files removed")


async def get_current_status():
    """Get current database status before reset."""
    print("📊 Current Database Status:")
    print("=" * 50)
    
    # Check SQLite
    sqlite_files = ['aqea_database.db']
    sqlite_exists = any(os.path.exists(f) for f in sqlite_files)
    print(f"SQLite Database: {'✅ Exists' if sqlite_exists else '❌ Not found'}")
    
    # Check Supabase
    try:
        config_obj = Config()
        config = config_obj.data
        config['database'] = config.get('database', {})
        config['database']['type'] = 'supabase'
        db = await get_database(config)
        
        if db:
            try:
                result = db.client.table('aqea_entries').select('address', count='exact').execute()
                count = result.count if hasattr(result, 'count') else 0
                print(f"Supabase Entries: ✅ {count} entries")
            except Exception as e:
                print(f"Supabase Entries: ⚠️  Error counting: {e}")
        else:
            print("Supabase Database: ❌ Not available")
    except Exception as e:
        print(f"Supabase Database: ❌ Error: {e}")
    
    # Check local files
    extracted_data_dir = Path('extracted_data')
    if extracted_data_dir.exists():
        json_files = list(extracted_data_dir.glob('*.json'))
        print(f"Local JSON Files: ✅ {len(json_files)} files")
    else:
        print("Local JSON Files: ❌ No directory")
    
    print("=" * 50)


async def main():
    parser = argparse.ArgumentParser(description='Reset AQEA databases')
    parser.add_argument('--confirm', action='store_true', 
                       help='Confirm that you want to delete ALL data')
    parser.add_argument('--sqlite-only', action='store_true',
                       help='Only reset SQLite database')
    parser.add_argument('--supabase-only', action='store_true',
                       help='Only reset Supabase database')
    parser.add_argument('--status-only', action='store_true',
                       help='Only show current status, do not reset')
    
    args = parser.parse_args()
    
    print("🗑️  AQEA Database Reset Script")
    print("=" * 50)
    
    # Show current status
    await get_current_status()
    
    if args.status_only:
        print("\n✅ Status check complete")
        return
    
    if not args.confirm:
        print("\n❌ You must use --confirm flag to proceed with database reset")
        print("⚠️  This will DELETE ALL AQEA data!")
        print("\nExample: python scripts/reset_database.py --confirm")
        return
    
    print(f"\n⚠️  WARNING: This will DELETE ALL AQEA data!")
    print("Type 'DELETE ALL DATA' to continue:")
    confirmation = input("> ")
    
    if confirmation != 'DELETE ALL DATA':
        print("❌ Reset cancelled")
        return
    
    print("\n🚀 Starting database reset...")
    
    # Reset based on flags
    if args.sqlite_only:
        await reset_sqlite_database()
    elif args.supabase_only:
        await reset_supabase_database()
    else:
        # Reset everything
        await reset_sqlite_database()
        await reset_supabase_database()
        reset_local_files()
    
    print("\n✅ Database reset complete!")
    print("💡 You can now start a fresh extraction with:")
    print("   python scripts/start_with_sqlite.py --workers 1")


if __name__ == '__main__':
    asyncio.run(main()) 
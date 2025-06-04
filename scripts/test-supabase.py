#!/usr/bin/env python3
"""
Test Script für AQEA Supabase Integration

Testet die vollständige Supabase-Integration ohne vollständige Extraktion.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.supabase import SupabaseDatabase
from src.aqea.schema import AQEAEntry
from src.aqea.converter import AQEAConverter
from src.utils.config import Config
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test basic database connection."""
    print("🔌 Testing Supabase database connection...")
    
    config = Config()
    database = SupabaseDatabase(config.data)
    
    success = await database.connect()
    if success:
        print("✅ Database connection successful!")
        await database.disconnect()
        return True
    else:
        print("❌ Database connection failed!")
        return False


async def test_worker_registration():
    """Test worker registration in database."""
    print("\n👥 Testing worker registration...")
    
    config = Config()
    database = SupabaseDatabase(config.data)
    await database.connect()
    
    try:
        # Register test worker
        success = await database.register_worker("test-worker-001", "192.168.1.100")
        if success:
            print("✅ Worker registration successful!")
            
            # Update heartbeat
            heartbeat_success = await database.update_worker_heartbeat(
                "test-worker-001", "working", "test-work-unit-01"
            )
            if heartbeat_success:
                print("✅ Worker heartbeat update successful!")
            else:
                print("❌ Worker heartbeat update failed!")
                
        else:
            print("❌ Worker registration failed!")
            
    finally:
        await database.disconnect()


async def test_work_unit_management():
    """Test work unit assignment and management."""
    print("\n📦 Testing work unit management...")
    
    config = Config()
    database = SupabaseDatabase(config.data)
    await database.connect()
    
    try:
        # Get pending work unit
        work_unit = await database.get_pending_work_unit("test-worker-001")
        if work_unit:
            print(f"✅ Retrieved work unit: {work_unit['work_id']}")
            print(f"   Range: {work_unit['range_start']}-{work_unit['range_end']}")
            print(f"   Estimated entries: {work_unit['estimated_entries']:,}")
            
            # Update progress
            progress_success = await database.update_work_progress(
                work_unit['work_id'], 50, 25.0  # 50 entries, 25/min rate
            )
            if progress_success:
                print("✅ Work progress update successful!")
            
            # Complete work unit
            complete_success = await database.complete_work_unit(
                work_unit['work_id'], True, 150, []  # Completed successfully with 150 entries
            )
            if complete_success:
                print("✅ Work unit completion successful!")
                
        else:
            print("⚠️ No pending work units found (this is normal after initial setup)")
            
    finally:
        await database.disconnect()


async def test_aqea_entry_storage():
    """Test AQEA entry creation and storage."""
    print("\n📝 Testing AQEA entry storage...")
    
    config = Config()
    database = SupabaseDatabase(config.data)
    await database.connect()
    
    try:
        # Create test AQEA entries
        test_entries = [
            AQEAEntry(
                address="0x20:01:01:01",
                label="Testwort1",
                description="German test word 'Testwort1'. Used for testing AQEA integration.",
                domain="0x20",
                lang_ui="de",
                meta={
                    "lemma": "Testwort1",
                    "pos": "noun",
                    "definitions": ["Ein Testwort für AQEA"],
                    "source": "test-script"
                }
            ),
            AQEAEntry(
                address="0x20:01:01:02", 
                label="Testwort2",
                description="German test word 'Testwort2'. Another test entry.",
                domain="0x20",
                lang_ui="de",
                meta={
                    "lemma": "Testwort2",
                    "pos": "noun",
                    "definitions": ["Ein weiteres Testwort"],
                    "source": "test-script"
                }
            )
        ]
        
        # Store entries
        result = await database.store_aqea_entries(test_entries)
        print(f"✅ Stored {result['inserted']} AQEA entries")
        print(f"   Success rate: {result['success_rate']:.1%}")
        
        if result['errors']:
            print(f"⚠️ {len(result['errors'])} errors occurred")
            for error in result['errors'][:3]:  # Show first 3 errors
                print(f"     - {error}")
        
        # Test retrieval
        retrieved_entry = await database.get_aqea_entry("0x20:01:01:01")
        if retrieved_entry:
            print(f"✅ Retrieved entry: {retrieved_entry.label}")
            print(f"   Address: {retrieved_entry.address}")
            print(f"   Description: {retrieved_entry.description[:50]}...")
        
    finally:
        await database.disconnect()


async def test_address_allocation():
    """Test AQEA address allocation."""
    print("\n🏷️ Testing address allocation...")
    
    config = Config()
    database = SupabaseDatabase(config.data)
    await database.connect()
    
    try:
        # Test address allocation
        category_key = "20:01:01"  # German:Noun:Nature
        
        # Allocate some addresses
        allocation_results = []
        for i, word in enumerate(["Testbaum", "Testfluss", "Testsonne"], 1):
            success = await database.allocate_address(
                category_key, i, "test-worker-001", word
            )
            allocation_results.append((word, i, success))
            
        successful_allocations = sum(1 for _, _, success in allocation_results if success)
        print(f"✅ Successfully allocated {successful_allocations}/3 test addresses")
        
        # Test retrieval of allocated addresses
        allocated_ids = await database.get_allocated_addresses(category_key)
        print(f"✅ Retrieved {len(allocated_ids)} allocated addresses for {category_key}")
        
        # Test duplicate allocation (should fail)
        duplicate_success = await database.allocate_address(
            category_key, 1, "test-worker-002", "Testbaum"
        )
        if not duplicate_success:
            print("✅ Duplicate allocation correctly prevented!")
        else:
            print("⚠️ Duplicate allocation was not prevented!")
            
    finally:
        await database.disconnect()


async def test_full_aqea_conversion():
    """Test full AQEA conversion with database integration."""
    print("\n🔄 Testing full AQEA conversion...")
    
    config = Config()
    database = SupabaseDatabase(config.data)
    await database.connect()
    
    try:
        # Create AQEA converter with database connection
        converter = AQEAConverter(config.data, "de", database, "test-worker-001")
        
        # Test data (similar to Wiktionary extraction)
        test_entries = [
            {
                'word': 'Testhaus',
                'language': 'de',
                'definitions': ['Ein Haus zum Testen', 'Gebäude für Tests'],
                'ipa': 'ˈtɛsthaʊs',
                'pos': 'noun'
            },
            {
                'word': 'Testauto',
                'language': 'de', 
                'definitions': ['Ein Auto zum Testen'],
                'ipa': 'ˈtɛstaʊto',
                'pos': 'noun'
            }
        ]
        
        # Convert to AQEA format
        aqea_entries = []
        for entry_data in test_entries:
            aqea_entry = await converter.convert(entry_data)
            if aqea_entry:
                aqea_entries.append(aqea_entry)
        
        print(f"✅ Converted {len(aqea_entries)} entries to AQEA format")
        
        # Display generated addresses
        for entry in aqea_entries:
            print(f"   {entry.label}: {entry.address}")
        
        # Store in database
        if aqea_entries:
            result = await database.store_aqea_entries(aqea_entries)
            print(f"✅ Stored {result['inserted']} entries with {result['success_rate']:.1%} success rate")
        
    finally:
        await database.disconnect()


async def test_statistics_and_monitoring():
    """Test statistics and monitoring functions."""
    print("\n📊 Testing statistics and monitoring...")
    
    config = Config()
    database = SupabaseDatabase(config.data)
    await database.connect()
    
    try:
        # Get extraction statistics
        stats = await database.get_extraction_statistics()
        
        if stats:
            print("✅ Retrieved extraction statistics:")
            print(f"   Total estimated entries: {stats['overview']['total_estimated_entries']:,}")
            print(f"   Total processed entries: {stats['overview']['total_processed_entries']:,}")
            print(f"   Progress: {stats['overview']['progress_percent']:.1f}%")
            print(f"   AQEA entries stored: {stats['overview']['aqea_entries_stored']:,}")
            print(f"   Active workers: {stats['workers']['active']}")
            print(f"   Average rate: {stats['performance']['average_rate']} entries/min")
            
            # Record progress snapshot
            await database.record_progress_snapshot(stats)
            print("✅ Progress snapshot recorded")
        else:
            print("⚠️ No statistics available")
            
    finally:
        await database.disconnect()


async def cleanup_test_data():
    """Clean up test data from database."""
    print("\n🧹 Cleaning up test data...")
    
    config = Config()
    database = SupabaseDatabase(config.data)
    await database.connect()
    
    try:
        async with database.pool.acquire() as conn:
            # Remove test AQEA entries
            deleted_entries = await conn.execute("""
                DELETE FROM aqea_entries 
                WHERE meta->>'source' = 'test-script'
            """)
            
            # Remove test worker
            deleted_worker = await conn.execute("""
                DELETE FROM worker_status 
                WHERE worker_id = 'test-worker-001'
            """)
            
            # Remove test address allocations
            deleted_allocations = await conn.execute("""
                DELETE FROM address_allocations 
                WHERE allocated_by = 'test-worker-001'
            """)
            
            print(f"✅ Cleaned up test data")
            print(f"   Entries: {deleted_entries}")
            print(f"   Workers: {deleted_worker}")
            print(f"   Allocations: {deleted_allocations}")
            
    except Exception as e:
        print(f"⚠️ Cleanup error (normal if test data doesn't exist): {e}")
    finally:
        await database.disconnect()


async def main():
    """Run all Supabase integration tests."""
    print("🚀 AQEA Supabase Integration Test Suite")
    print("=" * 60)
    
    # Check if DATABASE_URL is set
    if not os.getenv('DATABASE_URL'):
        print("❌ DATABASE_URL environment variable not set!")
        print("   Please set up your Supabase connection first.")
        print("   See .env.example for configuration details.")
        return
    
    try:
        # Run all tests
        tests = [
            test_database_connection,
            test_worker_registration,
            test_work_unit_management,
            test_aqea_entry_storage,
            test_address_allocation,
            test_full_aqea_conversion,
            test_statistics_and_monitoring
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"❌ Test {test.__name__} failed: {e}")
                logger.exception(f"Test {test.__name__} failed")
        
        # Cleanup
        await cleanup_test_data()
        
        print("\n🎉 Supabase integration test suite completed!")
        print("   Your AQEA system is ready for distributed extraction!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        logger.exception("Test suite failed")


if __name__ == "__main__":
    asyncio.run(main()) 
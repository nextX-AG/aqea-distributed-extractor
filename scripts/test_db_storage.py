#!/usr/bin/env python3
"""
Test script for database storage
Tests if AQEA entries can be properly stored in Supabase
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_database
from src.aqea.schema import AQEAEntry
from src.utils.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_test")

async def test_database_connection():
    """Test connection to Supabase database."""
    config = Config.load("config/default.yml")
    db = await get_database(config)
    
    if not db or not db.client:
        logger.error("❌ Failed to connect to Supabase database")
        return None
    
    logger.info("✅ Connected to Supabase database")
    return db

async def test_store_entries(db):
    """Test storing AQEA entries in the database."""
    if not db:
        return
    
    # Create test entry
    test_entry = AQEAEntry(
        address="0x20:01:01:FF",  # Test address
        label="Test Wort",
        description="German word 'Test Wort'. A test entry for validation.",
        domain="0x20",
        lang_ui="de",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by="test_db_storage.py",
        meta={
            "lemma": "Test Wort",
            "source": "test",
            "extraction_timestamp": datetime.now().isoformat()
        }
    )
    
    # Try to store entry
    result = await db.store_aqea_entries([test_entry])
    
    if result['inserted'] > 0:
        logger.info(f"✅ Successfully stored test entry: {result}")
    else:
        logger.error(f"❌ Failed to store test entry: {result}")
    
    # Check if entry was actually stored
    stored_entry = await db.get_aqea_entry("0x20:01:01:FF")
    
    if stored_entry:
        logger.info(f"✅ Successfully retrieved test entry: {stored_entry.label}")
    else:
        logger.error("❌ Failed to retrieve test entry")
    
    return result

async def check_existing_entries(db):
    """Check how many entries are currently in the database."""
    if not db:
        return
    
    try:
        # Manual count query using the client
        result = db.client.table('aqea_entries').select('count').execute()
        count = result.data[0]['count'] if result.data else 0
        
        logger.info(f"📊 Current entries in database: {count}")
        
        # Get statistics
        stats = await db.get_extraction_statistics()
        logger.info(f"📊 Statistics: {stats}")
        
        return stats
    except Exception as e:
        logger.error(f"❌ Error checking existing entries: {e}")
        return None

async def main():
    """Run the database tests."""
    # Test database connection
    db = await test_database_connection()
    if not db:
        return
    
    # Check current entries
    await check_existing_entries(db)
    
    # Test storing an entry
    await test_store_entries(db)
    
    # Check entries again
    await check_existing_entries(db)

if __name__ == "__main__":
    asyncio.run(main()) 
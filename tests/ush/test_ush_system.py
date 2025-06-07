#!/usr/bin/env python3
"""
Direct USH System Test - bypasses complex startup scripts
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import setup_logging
from src.utils.config import Config
from src.coordinator.master import MasterCoordinator

async def test_ush_system():
    """Test the USH system directly."""
    setup_logging(level="INFO")
    logger = logging.getLogger("ush_test")
    
    # Load config
    config = Config.load("config/default.yml")
    
    # Override database config for SQLite
    config.data['database'] = {
        'type': 'sqlite',
        'sqlite_path': 'aqea.db'
    }
    
    # Add USH config
    config.data['aqea'] = {
        'use_legacy_mode': False,
        'enable_cross_linguistic': True,
        'ush_version': '1.0',
        'address_format': 'ush'
    }
    
    logger.info("🧪 Starting USH System Test")
    logger.info(f"Database: {config.data['database']}")
    logger.info(f"AQEA Config: {config.data['aqea']}")
    
    # Create master coordinator
    coordinator = MasterCoordinator(
        config=config,
        language="de",
        source="wiktionary", 
        expected_workers=1,
        port=8080
    )
    
    # Test database initialization
    db_ok = await coordinator.initialize_db()
    logger.info(f"Database initialized: {db_ok}")
    
    # Test work unit loading
    await coordinator.reload_work_units()
    logger.info(f"Work units loaded: {len(coordinator.work_queue)}")
    
    # List work units
    for wu in coordinator.work_queue:
        logger.info(f"Work Unit: {wu.id} ({wu.start_range}-{wu.end_range})")
    
    logger.info("🎉 USH System Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_ush_system()) 
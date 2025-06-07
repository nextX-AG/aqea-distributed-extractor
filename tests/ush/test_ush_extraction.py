#!/usr/bin/env python3
"""
Complete USH Extraction Test - Master + Worker mit realer USH-Adressierung
"""

import asyncio
import logging
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import setup_logging
from src.utils.config import Config
from src.coordinator.master import MasterCoordinator
from src.workers.worker import ExtractionWorker

async def start_master():
    """Starte den Master Coordinator."""
    setup_logging(level="INFO")
    logger = logging.getLogger("ush_master")
    
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
    
    logger.info("🎯 Starting USH Master Coordinator on port 8081")
    
    # Create master coordinator
    coordinator = MasterCoordinator(
        config=config,
        language="de",
        source="wiktionary", 
        expected_workers=1,
        port=8081
    )
    
    # Initialize and start
    await coordinator.run()

async def start_worker():
    """Starte einen Worker."""
    # Warte kurz, bis der Master bereit ist
    await asyncio.sleep(3)
    
    setup_logging(level="INFO")
    logger = logging.getLogger("ush_worker")
    
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
    
    logger.info("🔧 Starting USH Worker connecting to port 8081")
    
    # Create worker
    worker = ExtractionWorker(
        config=config,
        worker_id="ush-test-worker-01",
        master_host="localhost",
        master_port=8081
    )
    
    # Start worker
    await worker.run()

async def run_full_test():
    """Führe einen vollständigen Test aus."""
    logger = logging.getLogger("ush_full_test")
    logger.info("🚀 Starting Full USH Integration Test")
    
    # Starte Master und Worker parallel
    try:
        await asyncio.gather(
            start_master(),
            start_worker()
        )
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_full_test()) 
#!/usr/bin/env python3
"""Start Master with explicit import paths"""

import sys
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.coordinator.master import MasterCoordinator
from src.utils.config import Config
from src.utils import logger

async def start_master():
    logger.setup_logging(level="INFO")
    config = Config.load("config/default.yml")
    
    language = os.getenv('LANGUAGE', 'de')
    source = "wiktionary"
    expected_workers = int(os.getenv('WORKER_COUNT', '2'))
    port = 8080
    
    # Set these in config for other components
    config.set("language", language)
    config.set("source", source)
    config.set("expected_workers", expected_workers)
    
    # Pass explicit arguments to constructor
    master = MasterCoordinator(
        config=config, 
        language=language,
        source=source,
        expected_workers=expected_workers,
        port=port
    )
    
    print(f"Starting master coordinator for {language} {source} with {expected_workers} workers on port {port}...")
    await master.run()

if __name__ == "__main__":
    asyncio.run(start_master()) 
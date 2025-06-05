#!/usr/bin/env python3
"""
Test script for Wiktionary extraction
Tests the improved German Wiktionary extraction
"""

import asyncio
import sys
import os
import logging
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_sources.wiktionary import WiktionaryDataSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wiktionary_test")

async def test_extraction(language: str, start_range: str, end_range: str):
    """Test extraction from Wiktionary for a specific range."""
    config = {}  # No special config needed
    source = WiktionaryDataSource(config)
    
    logger.info(f"Testing {language} Wiktionary extraction for range {start_range}-{end_range}")
    
    # Test API connection
    connected = await source.test_connection()
    if not connected:
        logger.error("❌ Failed to connect to Wiktionary API")
        return
    
    logger.info("✅ Connected to Wiktionary API")
    
    # Test extraction for a range
    total_entries = 0
    all_entries = []
    
    async for batch in source.extract_range(language, start_range, end_range, batch_size=10):
        logger.info(f"Received batch of {len(batch)} entries")
        total_entries += len(batch)
        all_entries.extend(batch)
    
    logger.info(f"✅ Extraction complete: {total_entries} entries extracted")
    
    # Display some sample entries
    if all_entries:
        logger.info("Sample entries:")
        for i, entry in enumerate(all_entries[:5]):
            logger.info(f"  Entry {i+1}:")
            logger.info(f"    Word: {entry.get('word')}")
            logger.info(f"    POS: {entry.get('pos')}")
            logger.info(f"    IPA: {entry.get('ipa')}")
            logger.info(f"    Definitions: {entry.get('definitions')}")
            logger.info("")
    else:
        logger.warning("No entries were extracted!")
    
    return all_entries

async def main():
    """Run the test."""
    # Test German Wiktionary extraction
    await test_extraction("de", "A", "B")  # Just a small range for testing
    
    # If you want to test other languages:
    # await test_extraction("en", "A", "B")

if __name__ == "__main__":
    asyncio.run(main()) 
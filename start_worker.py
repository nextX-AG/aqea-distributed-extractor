#!/usr/bin/env python3
"""Start Worker with explicit import paths"""

import sys
import os
import asyncio
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.workers.worker import ExtractionWorker
from src.utils.config import Config
from src.utils import logger

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Start an AQEA extraction worker")
    parser.add_argument("--worker-id", default="aqea-worker-001", help="Worker ID (e.g. aqea-worker-001)")
    parser.add_argument("--master-host", default="localhost", help="Master host (default: localhost)")
    parser.add_argument("--master-port", default=8080, type=int, help="Master port (default: 8080)")
    args = parser.parse_args()
    
    worker_id = args.worker_id
    master_host = args.master_host
    master_port = args.master_port
    
    logger.setup_logging(level="INFO")
    config = Config.load("config/default.yml")
    
    worker = ExtractionWorker(
        worker_id=worker_id,
        config=config,
        master_host=master_host,
        master_port=master_port
    )
    
    print(f"Starting worker {worker_id} connecting to {master_host}:{master_port}...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main()) 
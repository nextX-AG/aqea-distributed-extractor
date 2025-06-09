#!/usr/bin/env python3
"""
AQEA Guaranteed Extraction Script

Dieses Skript führt eine vollständige Extraktion durch und garantiert, dass
ALLE extrahierten Daten in JSON-Dateien gespeichert werden, unabhängig von 
der Datenbankverbindung.

Nutzung:
python scripts/extract_all_guaranteed.py --language de --workers 2
"""

import asyncio
import argparse
import os
import sys
import logging
import signal
import json
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coordinator.master import MasterCoordinator
from src.workers.worker import ExtractionWorker
from src.utils.config import Config
from src.utils.logger import setup_logging

# Configure logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for process management
master_process = None
worker_processes = []
running = True

def signal_handler(sig, frame):
    """Handle interrupt signals gracefully."""
    global running
    logger.info("⚠️ Empfangenes Unterbrechungssignal, Shutdown wird eingeleitet...")
    running = False
    # Shutdown wird später im Hauptloop behandelt

async def start_master(args, config):
    """Start the master coordinator."""
    logger.info(f"🎯 Starte AQEA Master Coordinator - Sprache: {args.language}, Workers: {args.workers}")
    
    # Create the master coordinator
    master = MasterCoordinator(
        config=config,
        language=args.language,
        source='wiktionary',
        expected_workers=args.workers,
        port=args.port
    )
    
    # Start the master coordinator
    await master.run()

async def start_worker(worker_id, args, config):
    """Start a worker node."""
    logger.info(f"🔧 Starte AQEA Worker {worker_id} - Master: {args.master_host}:{args.port}")
    
    # Create the worker
    worker = ExtractionWorker(
        config=config,
        worker_id=worker_id,
        master_host=args.master_host,
        master_port=args.port
    )
    
    # Start the worker
    await worker.run()

async def run_extraction(args):
    """Run the entire extraction process with master and workers."""
    global running
    
    # Load configuration
    config = Config.load(args.config)
    
    # Add guaranteed JSON storage path to config
    json_storage_path = "extracted_data/guaranteed"
    os.makedirs(json_storage_path, exist_ok=True)
    config.data.setdefault('storage', {})['json_path'] = json_storage_path
    
    # Start master task
    master_task = asyncio.create_task(start_master(args, config))
    
    # Wait a moment for master to initialize
    await asyncio.sleep(2)
    
    # Start worker tasks
    worker_tasks = []
    for i in range(args.workers):
        worker_id = f"worker-{i+1:03d}"
        worker_task = asyncio.create_task(start_worker(worker_id, args, config))
        worker_tasks.append(worker_task)
    
    # Monitor tasks and handle shutdown
    try:
        while running:
            # Check if any task has completed or failed
            done_tasks, _ = await asyncio.wait(
                [master_task] + worker_tasks, 
                timeout=1.0,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done_tasks:
                # A task has completed, check which one
                if task == master_task:
                    logger.error("❌ Master hat unerwartet beendet, initiiere Shutdown...")
                    running = False
                else:
                    # A worker has completed, maybe restart it?
                    worker_idx = worker_tasks.index(task)
                    logger.warning(f"⚠️ Worker-{worker_idx+1:03d} hat unerwartet beendet, initiiere Shutdown...")
                    running = False
            
            # Could add more monitoring logic here
            
    except asyncio.CancelledError:
        logger.info("Extraction wurde abgebrochen")
    except Exception as e:
        logger.error(f"Fehler im Haupt-Loop: {e}")
    finally:
        # Cancel all tasks
        logger.info("Beende alle Tasks...")
        
        # Cancel workers first
        for task in worker_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for workers to terminate
        if worker_tasks:
            await asyncio.wait(worker_tasks, timeout=5.0)
        
        # Then cancel master
        if not master_task.done():
            master_task.cancel()
        
        try:
            await master_task
        except asyncio.CancelledError:
            pass
        
        logger.info("Extraktion beendet.")

def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AQEA Guaranteed Extraction")
    parser.add_argument("--language", "-l", default="de", help="Language to extract (default: de)")
    parser.add_argument("--workers", "-w", type=int, default=2, help="Number of worker processes (default: 2)")
    parser.add_argument("--master-host", "-m", default="localhost", help="Master host (default: localhost)")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Master port (default: 8080)")
    parser.add_argument("--config", "-c", default="config/default.yml", help="Config file path (default: config/default.yml)")
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the extraction
    try:
        asyncio.run(run_extraction(args))
    except KeyboardInterrupt:
        logger.info("Extraction interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
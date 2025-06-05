#!/usr/bin/env python3
"""
Start optimized extraction with improved work units and extraction
"""

import os
import sys
import json
import argparse
import subprocess
import logging
import time
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("optimized_extraction")

def start_master(port=8080, work_units_file="config/work_units.json"):
    """Start master coordinator with optimized work units."""
    if not os.path.exists(work_units_file):
        logger.error(f"Work units file not found: {work_units_file}")
        logger.info("Please run scripts/generate_smaller_work_units.py first")
        return False
    
    # Load work units
    with open(work_units_file, 'r', encoding='utf-8') as f:
        work_units = json.load(f)
    
    logger.info(f"Starting master with {len(work_units)} optimized work units on port {port}")
    
    # Get the language from work units
    language = work_units[0]['language'] if work_units else 'de'
    
    # Start master in a new process
    cmd = [
        sys.executable,
        '-m', 'src.main',
        'start-master',
        '--language', language,
        '--port', str(port),
        '--workers', '2',  # Initial expected workers
        '--work-units-file', work_units_file
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        logger.info(f"Master started with PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to start master: {e}")
        return None

def start_worker(worker_id, master_host="localhost", master_port=8080):
    """Start a worker with optimized configuration."""
    logger.info(f"Starting worker {worker_id} connecting to {master_host}:{master_port}")
    
    # Start worker in a new process
    cmd = [
        sys.executable,
        '-m', 'src.main',
        'start-worker',
        '--worker-id', worker_id,
        '--master-host', master_host,
        '--master-port', str(master_port)
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        logger.info(f"Worker {worker_id} started with PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to start worker {worker_id}: {e}")
        return None

def main():
    """Start the optimized extraction system."""
    parser = argparse.ArgumentParser(description="Start optimized extraction")
    parser.add_argument('--port', type=int, default=8080, help="Master port")
    parser.add_argument('--workers', type=int, default=2, help="Number of workers to start")
    parser.add_argument('--work-units-file', default="config/work_units.json", help="Work units file")
    args = parser.parse_args()
    
    # Ensure work units exist or generate them
    if not os.path.exists(args.work_units_file):
        logger.info("Work units file not found, generating...")
        generate_script = os.path.join('scripts', 'generate_smaller_work_units.py')
        subprocess.run([sys.executable, generate_script])
    
    # Start master
    master_process = start_master(args.port, args.work_units_file)
    if not master_process:
        return
    
    # Wait for master to start
    logger.info("Waiting for master to start...")
    time.sleep(5)
    
    # Start workers
    worker_processes = []
    for i in range(1, args.workers + 1):
        worker_id = f"optimized-worker-{i:02d}"
        process = start_worker(worker_id, "localhost", args.port)
        if process:
            worker_processes.append(process)
    
    if not worker_processes:
        logger.error("No workers started, terminating master")
        master_process.terminate()
        return
    
    logger.info(f"✅ System started with 1 master and {len(worker_processes)} workers")
    logger.info(f"Master: http://localhost:{args.port}/api/status")
    
    try:
        # Keep the script running until Ctrl+C
        logger.info("Press Ctrl+C to stop all processes")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Terminating all processes...")
        for p in worker_processes:
            p.terminate()
        master_process.terminate()

if __name__ == "__main__":
    main() 
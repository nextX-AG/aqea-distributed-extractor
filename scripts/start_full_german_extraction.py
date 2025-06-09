#!/usr/bin/env python3
"""
AQEA Full German Extraction Script

Startet eine vollständige deutsche Wiktionary-Extraktion mit:
- SQLite-Datenbank für lokale Speicherung
- Erweiterte Metadaten (IPA, Audio, Flexion, Beispiele, Synonyme)
- Ein Worker für optimale Stabilität
- Alle 500k+ deutschen Wiktionary-Einträge

Usage:
    python scripts/start_full_german_extraction.py
    python scripts/start_full_german_extraction.py --workers 2
"""

import argparse
import asyncio
import signal
import sys
import subprocess
import time
from pathlib import Path

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m' 
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color):
    print(f"{color}{text}{Colors.ENDC}")

def print_header(text):
    print_colored(f"\n🚀 {text}", Colors.HEADER + Colors.BOLD)

def print_success(text):
    print_colored(f"✅ {text}", Colors.OKGREEN)

def print_warning(text):
    print_colored(f"⚠️  {text}", Colors.WARNING)

def print_error(text):
    print_colored(f"❌ {text}", Colors.FAIL)

# Global variables for process management
master_process = None
worker_processes = []

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print_warning("\nShutdown signal received...")
    cleanup_processes()
    sys.exit(0)

def cleanup_processes():
    """Clean up all running processes."""
    global master_process, worker_processes
    
    print_warning("Stopping all processes...")
    
    # Stop workers first
    for i, worker in enumerate(worker_processes):
        if worker and worker.poll() is None:
            print(f"  Stopping worker-{i+1:03d}...")
            worker.terminate()
            try:
                worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.kill()
    
    # Stop master
    if master_process and master_process.poll() is None:
        print("  Stopping master...")
        master_process.terminate()
        try:
            master_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            master_process.kill()
    
    print_success("All processes stopped")

def check_prerequisites():
    """Check if system is ready for extraction."""
    print_header("Checking Prerequisites")
    
    # Check virtual environment
    if sys.prefix == sys.base_prefix:
        print_error("Virtual environment not activated!")
        print("Please run: source aqea-venv/bin/activate")
        return False
    
    print_success("Virtual environment active")
    
    # Check if old database exists
    if Path('aqea_database.db').exists():
        print_warning("Old database detected - removing for fresh start")
        Path('aqea_database.db').unlink()
    
    # Check src directory
    if not Path('src').exists():
        print_error("src/ directory not found!")
        return False
    
    print_success("Project structure valid")
    
    # Create extracted_data directory if needed
    Path('extracted_data').mkdir(exist_ok=True)
    print_success("Data directories ready")
    
    return True

def start_master():
    """Start the master coordinator."""
    global master_process
    
    print_header("Starting Master Coordinator")
    
    cmd = [
        sys.executable, '-m', 'src.main', 'start-master',
        '--language', 'de',   # Use de for German Wiktionary
        '--workers', '1',     # Single worker for stability
        '--source', 'wiktionary',
        '--port', '8080'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        master_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Wait a bit for master to start
        time.sleep(3)
        
        if master_process.poll() is None:
            print_success("Master coordinator started successfully")
            return True
        else:
            print_error("Master coordinator failed to start")
            return False
            
    except Exception as e:
        print_error(f"Failed to start master: {e}")
        return False

def start_workers(num_workers):
    """Start worker processes."""
    global worker_processes
    
    print_header(f"Starting {num_workers} Worker(s)")
    
    for i in range(num_workers):
        worker_id = f"worker-{i+1:03d}"
        
        cmd = [
            sys.executable, '-m', 'src.main', 'start-worker',
            '--worker-id', worker_id,
            '--master-host', 'localhost',
            '--master-port', '8080'
        ]
        
        print(f"Starting {worker_id}...")
        
        try:
            worker = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            worker_processes.append(worker)
            
            # Brief delay between workers
            time.sleep(1)
            
        except Exception as e:
            print_error(f"Failed to start {worker_id}: {e}")
            return False
    
    print_success(f"All {num_workers} workers started")
    return True

def monitor_progress(limit=None):
    """Monitor extraction progress."""
    print_header("Monitoring Extraction Progress")
    print("📊 Open http://localhost:8080/api/status for live monitoring")
    print("📈 Check extracted_data/ directory for intermediate results")
    if limit:
        print(f"🎯 Will stop after {limit} entries are extracted")
    print("🛑 Press Ctrl+C to stop extraction gracefully")
    print()
    
    entries_extracted = 0
    
    try:
        while True:
            # Check if master is still running
            if master_process and master_process.poll() is not None:
                print_warning("Master process has stopped")
                break
            
            # Check if any workers are still running
            active_workers = sum(1 for w in worker_processes if w and w.poll() is None)
            
            if active_workers == 0:
                print_success("All workers have completed!")
                break
            
            # Check extraction count if limit is set
            if limit:
                # Try to get current count from database
                try:
                    if Path('data/aqea_extraction.db').exists():
                        import subprocess
                        result = subprocess.run([
                            'sqlite3', 'data/aqea_extraction.db', 
                            'SELECT COUNT(*) FROM aqea_entries;'
                        ], capture_output=True, text=True)
                        if result.returncode == 0:
                            current_count = int(result.stdout.strip())
                            print(f"⏳ {active_workers} workers active, {current_count} entries extracted...", end='\r')
                            
                            if current_count >= limit:
                                print_success(f"\n🎯 Target of {limit} entries reached! Stopping extraction...")
                                break
                        else:
                            print(f"⏳ {active_workers} workers still active...", end='\r')
                    else:
                        print(f"⏳ {active_workers} workers still active...", end='\r')
                except Exception as e:
                    print(f"⏳ {active_workers} workers still active...", end='\r')
            else:
                print(f"⏳ {active_workers} workers still active...", end='\r')
            
            time.sleep(5)
    
    except KeyboardInterrupt:
        print_warning("\nInterrupted by user")

def print_final_status():
    """Print final extraction status."""
    print_header("Extraction Complete!")
    
    # Check database
    db_path = Path('aqea_database.db')
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print_success(f"SQLite database: {size_mb:.2f} MB")
    
    # Check extracted data files
    data_dir = Path('extracted_data')
    if data_dir.exists():
        json_files = list(data_dir.glob('*.json'))
        if json_files:
            print_success(f"Backup JSON files: {len(json_files)} files")
    
    print()
    print_colored("🎉 German Wiktionary extraction complete!", Colors.HEADER + Colors.BOLD)
    print_colored("📊 Check database with: sqlite3 aqea_database.db", Colors.OKBLUE)
    print_colored("🔍 Query example: SELECT COUNT(*) FROM aqea_entries;", Colors.OKBLUE)

def main():
    parser = argparse.ArgumentParser(description='Start full German AQEA extraction')
    parser.add_argument('--workers', type=int, default=1, 
                       help='Number of worker processes (default: 1)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit extraction to N entries (for testing)')
    
    args = parser.parse_args()
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print_colored("🧠 AQEA Full German Extraction", Colors.HEADER + Colors.BOLD)
    if args.limit:
        print_colored(f"🔬 TEST MODE: Limited to {args.limit} entries", Colors.WARNING + Colors.BOLD)
    print_colored("=" * 50, Colors.HEADER)
    
    # Prerequisites check
    if not check_prerequisites():
        sys.exit(1)
    
    # Start master
    if not start_master():
        sys.exit(1)
    
    # Start workers
    if not start_workers(args.workers):
        cleanup_processes()
        sys.exit(1)
    
    # Monitor progress
    try:
        monitor_progress(limit=args.limit)
    finally:
        cleanup_processes()
        print_final_status()

if __name__ == '__main__':
    main() 
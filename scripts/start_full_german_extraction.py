#!/usr/bin/env python3
"""
AQEA Full German Extraction Script

Startet eine vollständige deutsche Wiktionary-Extraktion mit:
- Garantierte JSON-Speicherung aller extrahierten Daten
- Optional: SQLite-Datenbank für lokale Speicherung
- Erweiterte Metadaten (IPA, Audio, Flexion, Beispiele, Synonyme)
- Ein oder mehrere Worker für flexible Performance
- Alle 800k+ deutschen Wiktionary-Einträge

Usage:
    python scripts/start_full_german_extraction.py
    python scripts/start_full_german_extraction.py --workers 2
    python scripts/start_full_german_extraction.py --json-only  # Nur JSON, keine Datenbank
"""

import argparse
import asyncio
import signal
import sys
import subprocess
import time
import os
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
    
    # Check src directory
    if not Path('src').exists():
        print_error("src/ directory not found!")
        return False
    
    print_success("Project structure valid")
    
    # Create extracted_data directory if needed
    Path('extracted_data').mkdir(exist_ok=True)
    print_success("Data directories ready")
    
    # Modify worker.py to guarantee JSON storage if not already modified
    ensure_json_storage()
    
    return True

def ensure_json_storage():
    """Ensure worker.py has JSON storage capability."""
    worker_path = Path('src/workers/worker.py')
    if not worker_path.exists():
        print_error("Worker implementation not found!")
        return False
    
    worker_code = worker_path.read_text()
    
    # Check if JSON storage is already implemented
    if 'GARANTIERTE Speicherung' in worker_code:
        print_success("JSON storage already implemented")
        return True
    
    print_warning("Adding JSON storage capability to worker.py")
    
    # Find the _store_entries method
    if '_store_entries' not in worker_code:
        print_error("Could not find _store_entries method in worker.py")
        return False
    
    # Add JSON storage code
    new_code = worker_code.replace(
        "async def _store_entries(self, aqea_entries: List[Any]):",
        """async def _store_entries(self, aqea_entries: List[Any]):
        \"\"\"Store AQEA entries to database or send to master coordinator.\"\"\"
        if not aqea_entries:
            return {'inserted': 0, 'errors': []}
        
        # GARANTIERTE JSON-SPEICHERUNG: Speichere immer alle Einträge in JSON
        try:
            import json
            import os
            from datetime import datetime
            
            # Erstelle Verzeichnis, falls es nicht existiert
            os.makedirs('extracted_data', exist_ok=True)
            
            # Erstelle eindeutigen Dateinamen mit Zeitstempel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"extracted_data/aqea_entries_{self.worker_id}_{timestamp}.json"
            
            # Konvertiere Einträge in JSON-serialisierbares Format
            entries_data = []
            for entry in aqea_entries:
                entry_dict = {
                    'address': entry.address,
                    'label': entry.label,
                    'description': entry.description,
                    'domain': entry.domain,
                    'created_at': entry.created_at.isoformat() if hasattr(entry.created_at, 'isoformat') else str(entry.created_at),
                    'updated_at': entry.updated_at.isoformat() if hasattr(entry.updated_at, 'isoformat') else str(entry.updated_at),
                    'meta': entry.meta
                }
                entries_data.append(entry_dict)
            
            # Speichere als JSON
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(entries_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"✅ GARANTIERTE Speicherung: {len(entries_data)} Einträge in {filename} gesichert")
        except Exception as e:
            logger.error(f"❌ Fehler bei JSON-Speicherung: {e}")
        
        # Original-Code für Datenbankoperationen folgt"""
    )
    
    # Write modified code back
    worker_path.write_text(new_code)
    print_success("JSON storage capability added to worker.py")
    return True

def start_master(json_only=False):
    """Start the master coordinator."""
    global master_process
    
    print_header("Starting Master Coordinator")
    
    env = os.environ.copy()
    if json_only:
        # Disable database connection by setting empty config
        env['AQEA_DB_TYPE'] = 'none'
        print_warning("Running in JSON-only mode (no database)")
    
    cmd = [
        sys.executable, '-m', 'src.main', 'start-master',
        '--language', 'de',   # Use de for German Wiktionary
        '--workers', '1',     # Will be overridden by argument
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
            bufsize=1,
            env=env
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

def start_workers(num_workers, json_only=False):
    """Start worker processes."""
    global worker_processes
    
    print_header(f"Starting {num_workers} Worker(s)")
    
    env = os.environ.copy()
    if json_only:
        # Disable database connection by setting empty config
        env['AQEA_DB_TYPE'] = 'none'
    
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
                bufsize=1,
                env=env
            )
            
            worker_processes.append(worker)
            
            # Brief delay between workers
            time.sleep(1)
            
        except Exception as e:
            print_error(f"Failed to start {worker_id}: {e}")
            return False
    
    print_success(f"All {num_workers} workers started")
    return True

def monitor_progress(limit=None, json_only=False):
    """Monitor extraction progress."""
    print_header("Monitoring Extraction Progress")
    print("📊 Open http://localhost:8080/api/status for live monitoring")
    print("📈 Check extracted_data/ directory for JSON results")
    if limit:
        print(f"🎯 Will stop after {limit} entries are extracted")
    print("🛑 Press Ctrl+C to stop extraction gracefully")
    print()
    
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
                
            # Count JSON files and approximate entries
            json_files = list(Path('extracted_data').glob('*.json'))
            approx_entries = len(json_files) * 40  # Etwa 40 Einträge pro Datei
            
            # Show progress
            print(f"⏳ {active_workers} workers active, ~{approx_entries} entries in {len(json_files)} JSON files...", end='\r')
            
            # Check database if not in json-only mode
            if not json_only and limit:
                try:
                    if Path('data/aqea_extraction.db').exists():
                        import subprocess
                        result = subprocess.run([
                            'sqlite3', 'data/aqea_extraction.db', 
                            'SELECT COUNT(*) FROM aqea_entries;'
                        ], capture_output=True, text=True)
                        if result.returncode == 0:
                            db_count = int(result.stdout.strip())
                            if db_count >= limit:
                                print_success(f"\n🎯 Target of {limit} entries reached! Stopping extraction...")
                                break
                except Exception:
                    pass
                
            time.sleep(5)
    
    except KeyboardInterrupt:
        print_warning("\nInterrupted by user")

def print_final_status(json_only=False):
    """Print final extraction status."""
    print_header("Extraction Complete!")
    
    # Check database if not in json-only mode
    if not json_only:
        db_path = Path('data/aqea_extraction.db')
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            print_success(f"SQLite database: {size_mb:.2f} MB")
            
            # Count entries in database
            try:
                import subprocess
                result = subprocess.run([
                    'sqlite3', 'data/aqea_extraction.db', 
                    'SELECT COUNT(*) FROM aqea_entries;'
                ], capture_output=True, text=True)
                if result.returncode == 0:
                    db_count = int(result.stdout.strip())
                    print_success(f"Database entries: {db_count}")
            except Exception:
                pass
    
    # Check extracted data files
    data_dir = Path('extracted_data')
    if data_dir.exists():
        json_files = list(data_dir.glob('*.json'))
        if json_files:
            # Calculate total size
            total_size = sum(f.stat().st_size for f in json_files) / (1024 * 1024)
            print_success(f"JSON-Dateien: {len(json_files)} Dateien, insgesamt {total_size:.2f} MB")
            
            # Estimate entry count
            approx_entries = len(json_files) * 40  # Etwa 40 Einträge pro Datei
            print_success(f"Geschätzte Einträge in JSON: ~{approx_entries}")
    
    print()
    print_colored("🎉 German Wiktionary extraction complete!", Colors.HEADER + Colors.BOLD)
    
    if not json_only:
        print_colored("📊 Check database with: sqlite3 data/aqea_extraction.db", Colors.OKBLUE)
        print_colored("🔍 Query example: SELECT COUNT(*) FROM aqea_entries;", Colors.OKBLUE)
        
    print_colored("💾 JSON files stored in extracted_data/ directory", Colors.OKBLUE)
    print_colored("🔍 Analyze with: scripts/count_json_entries.py", Colors.OKBLUE)

def main():
    parser = argparse.ArgumentParser(description='Start full German AQEA extraction')
    parser.add_argument('--workers', type=int, default=1, 
                       help='Number of worker processes (default: 1)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit extraction to N entries (for testing)')
    parser.add_argument('--json-only', action='store_true',
                       help='Store data only as JSON, skip database storage')
    
    args = parser.parse_args()
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print_colored("🧠 AQEA Full German Extraction", Colors.HEADER + Colors.BOLD)
    if args.json_only:
        print_colored("💾 MODE: JSON-only (keine Datenbank-Speicherung)", Colors.WARNING + Colors.BOLD)
    if args.limit:
        print_colored(f"🔬 TEST MODE: Limited to {args.limit} entries", Colors.WARNING + Colors.BOLD)
    print_colored("=" * 50, Colors.HEADER)
    
    # Prerequisites check
    if not check_prerequisites():
        sys.exit(1)
    
    # Start master
    if not start_master(json_only=args.json_only):
        sys.exit(1)
    
    # Start workers
    if not start_workers(args.workers, json_only=args.json_only):
        cleanup_processes()
        sys.exit(1)
    
    # Monitor progress
    try:
        monitor_progress(limit=args.limit, json_only=args.json_only)
    finally:
        cleanup_processes()
        print_final_status(json_only=args.json_only)

if __name__ == '__main__':
    main() 
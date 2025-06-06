#!/usr/bin/env python3
"""
Start AQEA Distributed Extractor with SQLite Database

Dieses Skript startet den Master-Coordinator mit einer SQLite-Datenbank
und optional mehrere Worker.
"""

import os
import sys
import argparse
import logging
import time
import asyncio
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import setup_logging

# Konfiguriere Logging
setup_logging(level="INFO")
logger = logging.getLogger("sqlite_extractor")

def ensure_directories():
    """Stelle sicher, dass alle benötigten Verzeichnisse existieren."""
    directories = [
        'data',
        'extracted_data',
        'config'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Verzeichnis überprüft: {directory}")

def create_config():
    """Erstelle eine Konfigurationsdatei für SQLite."""
    config_path = "config/sqlite_config.json"
    
    if os.path.exists(config_path):
        logger.info(f"Konfigurationsdatei existiert bereits: {config_path}")
        return config_path
    
    config = {
        "database": {
            "type": "sqlite",
            "sqlite_path": "data/aqea_extraction.db"
        },
        "extraction": {
            "batch_size": 10,
            "request_delay": 0.5
        },
        "logging": {
            "level": "INFO"
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
    
    logger.info(f"SQLite-Konfiguration erstellt: {config_path}")
    return config_path

def create_work_units(language, work_units_file="config/work_units.json"):
    """Erstelle die Arbeitspakete."""
    if os.path.exists(work_units_file):
        logger.info(f"Arbeitspakete existieren bereits: {work_units_file}")
        return work_units_file
    
    # Alphabetbereiche für Arbeitspakete
    if language == "de":
        # Für deutsches Wiktionary - kleinere, gleichmäßigere Pakete
        ranges = [
            {"work_id": "de_wiktionary_01", "language": "de", "source": "wiktionary", "range_start": "A", "range_end": "Ad", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_02", "language": "de", "source": "wiktionary", "range_start": "Ae", "range_end": "Al", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_03", "language": "de", "source": "wiktionary", "range_start": "Am", "range_end": "Ap", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_04", "language": "de", "source": "wiktionary", "range_start": "Aq", "range_end": "Az", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_05", "language": "de", "source": "wiktionary", "range_start": "B", "range_end": "Bd", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_06", "language": "de", "source": "wiktionary", "range_start": "Be", "range_end": "Bh", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_07", "language": "de", "source": "wiktionary", "range_start": "Bi", "range_end": "Bm", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_08", "language": "de", "source": "wiktionary", "range_start": "Bn", "range_end": "Bq", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_09", "language": "de", "source": "wiktionary", "range_start": "Br", "range_end": "Bz", "estimated_entries": 18000},
            {"work_id": "de_wiktionary_10", "language": "de", "source": "wiktionary", "range_start": "C", "range_end": "Cl", "estimated_entries": 18000},
            # ...weitere Bereiche...
        ]
    else:
        # Standardbereiche für andere Sprachen
        ranges = [
            {"work_id": f"{language}_wiktionary_01", "language": language, "source": "wiktionary", "range_start": "A", "range_end": "E", "estimated_entries": 160000},
            {"work_id": f"{language}_wiktionary_02", "language": language, "source": "wiktionary", "range_start": "F", "range_end": "J", "estimated_entries": 160000},
            {"work_id": f"{language}_wiktionary_03", "language": language, "source": "wiktionary", "range_start": "K", "range_end": "O", "estimated_entries": 160000},
            {"work_id": f"{language}_wiktionary_04", "language": language, "source": "wiktionary", "range_start": "P", "range_end": "T", "estimated_entries": 160000},
            {"work_id": f"{language}_wiktionary_05", "language": language, "source": "wiktionary", "range_start": "U", "range_end": "Z", "estimated_entries": 160000},
        ]
    
    with open(work_units_file, 'w', encoding='utf-8') as f:
        json.dump(ranges, f, indent=4)
    
    logger.info(f"Arbeitspakete erstellt: {work_units_file}")
    return work_units_file

def start_master(port, language, work_units_file, config_file):
    """Starte den Master-Coordinator."""
    cmd = [
        sys.executable, "-m", "src.main",
        "start-master",
        "--language", language,
        "--work-units-file", work_units_file,
        "--config-file", config_file,
        "--port", str(port)
    ]
    
    logger.info(f"Starte Master-Coordinator auf Port {port}...")
    process = subprocess.Popen(cmd)
    logger.info(f"Master-Coordinator gestartet mit PID {process.pid}")
    return process

def start_worker(worker_id, master_host, master_port, config_file):
    """Starte einen Worker."""
    cmd = [
        sys.executable, "-m", "src.main",
        "start-worker",
        "--worker-id", worker_id,
        "--master-host", master_host,
        "--master-port", str(master_port)
    ]
    
    logger.info(f"Starte Worker {worker_id}...")
    process = subprocess.Popen(cmd)
    logger.info(f"Worker {worker_id} gestartet mit PID {process.pid}")
    return process

def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(description="Starte AQEA Distributed Extractor mit SQLite-Datenbank")
    parser.add_argument("--workers", "-w", type=int, default=2, help="Anzahl der Worker-Prozesse")
    parser.add_argument("--language", "-l", default="de", help="Sprache für die Extraktion (de, en, fr, es)")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port für den Master-Coordinator")
    parser.add_argument("--host", default="localhost", help="Hostname für die Worker-Verbindung")
    args = parser.parse_args()
    
    # Erstelle Verzeichnisse und Konfiguration
    ensure_directories()
    config_file = create_config()
    work_units_file = create_work_units(args.language)
    
    # Starte den Master
    master_process = start_master(args.port, args.language, work_units_file, config_file)
    
    # Warte, bis der Master bereit ist
    logger.info("Warte 5 Sekunden, bis der Master bereit ist...")
    time.sleep(5)
    
    # Starte Worker
    worker_processes = []
    for i in range(args.workers):
        worker_id = f"sqlite-worker-{i+1:02d}"
        process = start_worker(worker_id, args.host, args.port, config_file)
        worker_processes.append(process)
    
    logger.info(f"✅ System gestartet mit 1 Master und {args.workers} Workern")
    logger.info(f"Master: http://{args.host}:{args.port}/api/status")
    logger.info("Drücke Ctrl+C zum Beenden")
    
    try:
        # Halte das Skript am Laufen
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Beende alle Prozesse...")
        for process in worker_processes:
            process.terminate()
        master_process.terminate()
        logger.info("Alle Prozesse beendet")

if __name__ == "__main__":
    main() 
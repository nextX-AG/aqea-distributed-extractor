#!/usr/bin/env python3
"""
Start AQEA Distributed Extractor mit SQLite-Datenbank

Dieses Skript startet den Master-Koordinator und eine konfigurierbare Anzahl an Worker-Nodes,
alle mit der lokalen SQLite-Datenbank konfiguriert für direkte Datenspeicherung ohne JSON-Dumps.

Beispielaufruf:
    python scripts/start_with_sqlite.py --workers 2 --language de
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path
import json
import subprocess
from datetime import datetime

# Füge src zum Python-Pfad hinzu, um Imports aus dem Paket zu ermöglichen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coordinator.master import MasterCoordinator
from src.workers.worker import ExtractionWorker
from src.database.sqlite import SQLiteDatabase
from src.utils.logger import setup_logging

# Logging einrichten
logger = logging.getLogger(__name__)
setup_logging(level=logging.INFO)

# Globale Variablen für Prozessverwaltung
master_process = None
worker_processes = []

def parse_args():
    """Befehlszeilenargumente parsen."""
    parser = argparse.ArgumentParser(description="AQEA-System mit SQLite-Datenbank starten")
    parser.add_argument("--workers", type=int, default=2, help="Anzahl der Worker-Prozesse")
    parser.add_argument("--language", type=str, default="de", help="Sprache für die Extraktion")
    parser.add_argument("--source", type=str, default="wiktionary", help="Datenquelle (wiktionary, panlex, etc.)")
    parser.add_argument("--master-port", type=int, default=8080, help="Port für den Master-Koordinator")
    parser.add_argument("--db-path", type=str, default="data/aqea_extraction.db", help="Pfad zur SQLite-Datenbank")
    return parser.parse_args()

def start_master(args):
    """Master-Koordinator in einem separaten Prozess starten."""
    global master_process
    
    # Konfiguration für den Master
    config = {
        'database': {
            'type': 'sqlite',
            'sqlite_path': args.db_path
        },
        'language': args.language,
        'source': args.source,
        'expected_workers': args.workers,
        'languages': {
            'de': {
                'name': 'German',
                'estimated_entries': 800000,
                'alphabet_ranges': [
                    {'start': 'A', 'end': 'E', 'weight': 0.2},
                    {'start': 'F', 'end': 'J', 'weight': 0.15},
                    {'start': 'K', 'end': 'O', 'weight': 0.175},
                    {'start': 'P', 'end': 'T', 'weight': 0.225},
                    {'start': 'U', 'end': 'Z', 'weight': 0.25}
                ]
            },
            'en': {
                'name': 'English',
                'estimated_entries': 6000000,
                'alphabet_ranges': [
                    {'start': 'A', 'end': 'E', 'weight': 0.2},
                    {'start': 'F', 'end': 'J', 'weight': 0.15},
                    {'start': 'K', 'end': 'O', 'weight': 0.175},
                    {'start': 'P', 'end': 'T', 'weight': 0.225},
                    {'start': 'U', 'end': 'Z', 'weight': 0.25}
                ]
            }
        }
    }
    
    # Config-Datei erstellen
    os.makedirs('config', exist_ok=True)
    with open('config/sqlite_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    # Master-Prozess starten
    cmd = [
        sys.executable, '-m', 'src.main', 'start-master',
        '--language', args.language,
        '--source', args.source,
        '--workers', str(args.workers),
        '--port', str(args.master_port),
        '--config-file', 'config/sqlite_config.json'
    ]
    
    logger.info(f"Starte Master-Koordinator: {' '.join(cmd)}")
    master_process = subprocess.Popen(cmd)
    logger.info(f"Master-Prozess gestartet mit PID {master_process.pid}")
    
    # Warte kurz, damit der Master hochfahren kann
    time.sleep(2)

def start_workers(args):
    """Worker-Prozesse starten."""
    global worker_processes
    
    # Konfiguration für die Worker
    config = {
        'database': {
            'type': 'sqlite',
            'sqlite_path': args.db_path
        },
        'language': args.language,
        'source': args.source
    }
    
    # Config-Datei erstellen
    with open('config/sqlite_worker_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    # Worker-Prozesse starten
    for i in range(args.workers):
        worker_id = f"worker-{i+1:03d}"
        
        # Worker starten mit Umgebungsvariablen statt config-file
        env = os.environ.copy()
        # Datenbank-Konfiguration in Umgebungsvariablen
        env["DB_TYPE"] = "sqlite"
        env["SQLITE_PATH"] = os.path.abspath(args.db_path)
        # Setze eine Variable, die unser SQLite-Script als Marker verwenden kann
        env["AQEA_DIRECT_SQLITE"] = "1"
        # Definiere explizit die Sprache für den Worker
        env["AQEA_LANGUAGE"] = args.language
        # Definiere die Datenquelle
        env["AQEA_SOURCE"] = args.source
        
        cmd = [
            sys.executable, '-m', 'src.main', 'start-worker',
            '--worker-id', worker_id,
            '--master-host', 'localhost',
            '--master-port', str(args.master_port)
        ]
        
        logger.info(f"Starte Worker {worker_id}: {' '.join(cmd)}")
        worker_process = subprocess.Popen(cmd, env=env)
        worker_processes.append(worker_process)
        logger.info(f"Worker-Prozess {worker_id} gestartet mit PID {worker_process.pid}")
        
        # Kurze Pause zwischen Worker-Starts
        time.sleep(1)

def monitor_processes():
    """Überwache die laufenden Prozesse und logge Status."""
    while True:
        try:
            # Prüfe Master-Status
            if master_process and master_process.poll() is not None:
                logger.error(f"Master-Prozess beendet mit Exit-Code {master_process.returncode}")
                cleanup_and_exit()
            
            # Prüfe Worker-Status
            for i, proc in enumerate(worker_processes):
                if proc.poll() is not None:
                    logger.error(f"Worker-{i+1:03d} beendet mit Exit-Code {proc.returncode}")
                    # Wenn ein Worker abstürzt, starte ihn neu
                    worker_id = f"worker-{i+1:03d}"
                    cmd = [
                        sys.executable, '-m', 'src.main', 'start-worker',
                        '--worker-id', worker_id,
                        '--master-host', 'localhost',
                        '--master-port', str(args.master_port)
                    ]
                    logger.info(f"Starte Worker {worker_id} neu: {' '.join(cmd)}")
                    worker_processes[i] = subprocess.Popen(cmd, env=env)
            
            # Status abrufen
            try:
                import requests
                response = requests.get(f"http://localhost:{args.master_port}/api/status")
                if response.status_code == 200:
                    status = response.json()
                    progress = status.get('progress', {})
                    workers = status.get('workers', {})
                    
                    logger.info(
                        f"Status: {progress.get('progress_percent', 0):.1f}% abgeschlossen, "
                        f"{progress.get('total_processed_entries', 0)} Einträge, "
                        f"Rate: {progress.get('current_rate_per_minute', 0):.1f}/min, "
                        f"ETA: {progress.get('eta_hours', 0):.1f}h"
                    )
                else:
                    logger.warning(f"Konnte Status nicht abrufen: HTTP {response.status_code}")
            except Exception as e:
                logger.warning(f"Fehler beim Abrufen des Status: {e}")
            
            time.sleep(30)  # Alle 30 Sekunden prüfen
                
        except KeyboardInterrupt:
            logger.info("Keyboard-Interrupt erkannt, beende Prozesse...")
            cleanup_and_exit()
        except Exception as e:
            logger.error(f"Fehler bei der Prozessüberwachung: {e}")
            time.sleep(10)

def cleanup_and_exit():
    """Prozesse ordnungsgemäß beenden."""
    logger.info("Bereinige Prozesse...")
    
    # Worker-Prozesse beenden
    for i, proc in enumerate(worker_processes):
        if proc.poll() is None:  # Wenn Prozess noch läuft
            logger.info(f"Beende Worker-{i+1:03d} (PID: {proc.pid})")
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Worker-{i+1:03d} reagiert nicht, erzwinge Beendigung")
                proc.kill()
    
    # Master-Prozess beenden
    if master_process and master_process.poll() is None:
        logger.info(f"Beende Master-Prozess (PID: {master_process.pid})")
        try:
            master_process.terminate()
            master_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Master reagiert nicht, erzwinge Beendigung")
            master_process.kill()
    
    logger.info("Alle Prozesse beendet.")
    sys.exit(0)

def signal_handler(sig, frame):
    """Signal-Handler für Ctrl+C und andere Signals."""
    logger.info(f"Signal {sig} erhalten, beende Prozesse...")
    cleanup_and_exit()

if __name__ == "__main__":
    # Signal-Handler registrieren
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Argumente parsen
    args = parse_args()
    
    try:
        # Stelle sicher, dass Datenbankverzeichnis existiert
        os.makedirs(os.path.dirname(args.db_path), exist_ok=True)
        
        # Starte Master
        start_master(args)
        
        # Starte Worker
        start_workers(args)
        
        # Ausgabe URL für Statusabfrage
        logger.info(f"System gestartet mit SQLite-Datenbank: {args.db_path}")
        logger.info(f"Master-Koordinator läuft auf http://localhost:{args.master_port}")
        logger.info(f"Status-API: http://localhost:{args.master_port}/api/status")
        logger.info(f"Drücke Ctrl+C zum Beenden")
        
        # Überwache Prozesse
        monitor_processes()
        
    except KeyboardInterrupt:
        logger.info("Keyboard-Interrupt erkannt, beende Prozesse...")
        cleanup_and_exit()
    except Exception as e:
        logger.error(f"Fehler beim Starten des Systems: {e}")
        cleanup_and_exit() 
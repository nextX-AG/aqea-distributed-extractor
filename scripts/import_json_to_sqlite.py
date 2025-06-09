#!/usr/bin/env python3
"""
JSON to SQLite Importer

Dieses Skript importiert AQEA-Einträge aus den generierten JSON-Dateien
in die SQLite-Datenbank. Es unterstützt das Zusammenführen aller extrahierten
Daten in eine zentrale Datenbank.
"""

import os
import sys
import json
import logging
import sqlite3
import argparse
import glob
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# Füge das Projekt-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/json_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("json-importer")

def setup_database(db_path):
    """Richtet die SQLite-Datenbank ein und erstellt Tabellen falls nötig."""
    logger.info(f"Initialisiere Datenbank: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Erstelle aqea_entries Tabelle falls sie nicht existiert
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS aqea_entries (
        address TEXT PRIMARY KEY,
        label TEXT,
        description TEXT,
        domain TEXT,
        status TEXT,
        created_at TEXT,
        updated_at TEXT,
        created_by TEXT,
        lang_ui TEXT,
        meta TEXT,
        relations TEXT
    )
    ''')
    
    # Erstelle einen Index für schnellere Suche
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain ON aqea_entries(domain)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_label ON aqea_entries(label)')
    
    conn.commit()
    
    # Prüfe, ob die Tabelle erfolgreich erstellt wurde
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aqea_entries'")
    if cursor.fetchone():
        logger.info("Datenbank-Schema erfolgreich initialisiert")
    else:
        logger.error("Fehler beim Erstellen des Datenbank-Schemas")
        sys.exit(1)
    
    return conn

def find_json_files(source_dir):
    """Findet alle AQEA JSON-Dateien im angegebenen Verzeichnis."""
    json_pattern = os.path.join(source_dir, "**", "*.json")
    files = glob.glob(json_pattern, recursive=True)
    
    # Filtere auf AQEA-Dateien
    aqea_files = [f for f in files if "aqea" in f.lower()]
    
    logger.info(f"{len(aqea_files)} AQEA-JSON-Dateien gefunden")
    return aqea_files

def import_file(file_path, conn, batch_size=1000, source_name="json-importer"):
    """Importiert AQEA-Einträge aus einer JSON-Datei in die Datenbank."""
    logger.info(f"Verarbeite Datei: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Datei {file_path}: {e}")
        return 0, 0
    
    # Stelle sicher, dass wir mit einer Liste von Einträgen arbeiten
    if isinstance(data, dict) and "entries" in data:
        entries = data["entries"]
    elif isinstance(data, list):
        entries = data
    else:
        logger.warning(f"Unerwartetes Format in {file_path}, überspringe...")
        return 0, 0
    
    cursor = conn.cursor()
    inserted = 0
    skipped = 0
    batch = []
    
    for entry in entries:
        # Prüfe und bereite die Daten vor
        if not validate_entry(entry):
            skipped += 1
            continue
        
        # Bereite Daten für SQLite vor
        prepared_entry = prepare_entry(entry, source_name)
        batch.append(prepared_entry)
        
        # Führe Batch-Import durch, wenn die Batch-Größe erreicht ist
        if len(batch) >= batch_size:
            inserted += process_batch(batch, cursor)
            batch = []
    
    # Verarbeite verbleibende Einträge
    if batch:
        inserted += process_batch(batch, cursor)
    
    conn.commit()
    logger.info(f"Datei {file_path} verarbeitet: {inserted} Einträge importiert, {skipped} übersprungen")
    return inserted, skipped

def validate_entry(entry):
    """Validiert einen AQEA-Eintrag auf notwendige Felder."""
    required_fields = ["address", "label"]
    for field in required_fields:
        if field not in entry:
            return False
    return True

def prepare_entry(entry, source_name):
    """Bereitet einen AQEA-Eintrag für den Datenbank-Import vor."""
    # Standardwerte setzen, falls Felder fehlen
    if "description" not in entry:
        entry["description"] = f"Entry for {entry['label']}"
    
    if "domain" not in entry and "address" in entry:
        # Extrahiere Domain aus der Adresse (erstes Byte)
        parts = entry["address"].split(":")
        if len(parts) >= 1:
            entry["domain"] = parts[0]
    
    # Meta-Daten aus anderen Feldern extrahieren und als JSON speichern
    meta_dict = {}
    for key, value in entry.items():
        if key not in ["address", "label", "description", "domain", "status", 
                      "created_at", "updated_at", "created_by", "lang_ui", "relations"]:
            meta_dict[key] = value
    
    meta_json = json.dumps(meta_dict) if meta_dict else "{}"
    
    # Relationen als JSON speichern (falls vorhanden)
    relations_json = json.dumps(entry.get("relations", {})) if "relations" in entry else None
    
    # Setze created_by, falls nicht vorhanden
    created_by = entry.get("created_by", source_name)
    
    return (
        entry["address"],
        entry["label"],
        entry["description"],
        entry.get("domain", "unknown"),
        entry.get("status", "active"),
        entry.get("created_at", datetime.now().isoformat()),
        entry.get("updated_at", datetime.now().isoformat()),
        created_by,
        entry.get("lang_ui"),
        meta_json,
        relations_json
    )

def process_batch(batch, cursor):
    """Verarbeitet einen Batch von AQEA-Einträgen."""
    try:
        cursor.executemany('''
        INSERT OR REPLACE INTO aqea_entries 
        (address, label, description, domain, status, created_at, updated_at, created_by, lang_ui, meta, relations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', batch)
        return len(batch)
    except Exception as e:
        logger.error(f"Fehler beim Batch-Import: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description="Importiert AQEA-Einträge aus JSON-Dateien in eine SQLite-Datenbank")
    parser.add_argument("--source-dir", "-s", default="extracted_data/dump/aqea",
                       help="Verzeichnis mit AQEA-JSON-Dateien")
    parser.add_argument("--db-path", "-d", default="data/aqea_extraction.db",
                       help="Pfad zur SQLite-Datenbank")
    parser.add_argument("--batch-size", "-b", type=int, default=1000,
                       help="Anzahl der Einträge pro Batch")
    parser.add_argument("--source-name", default="json-importer",
                       help="Name des Importers (für created_by Feld)")
    parser.add_argument("--clear-db", action="store_true",
                       help="Löscht vorhandene Einträge vor dem Import")
    args = parser.parse_args()
    
    # Erstelle Verzeichnisse, falls nicht vorhanden
    os.makedirs(os.path.dirname(args.db_path), exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Datenbankverbindung aufbauen
    conn = setup_database(args.db_path)
    
    # Lösche vorhandene Einträge, falls gewünscht
    if args.clear_db:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM aqea_entries")
        conn.commit()
        logger.info("Alle vorhandenen Einträge wurden gelöscht")
    
    # JSON-Dateien finden
    json_files = find_json_files(args.source_dir)
    
    if not json_files:
        logger.warning(f"Keine AQEA-JSON-Dateien in {args.source_dir} gefunden")
        return
    
    # Statistik initialisieren
    total_inserted = 0
    total_skipped = 0
    
    # Dateien verarbeiten mit Fortschrittsbalken
    for file_path in tqdm(json_files, desc="Verarbeite AQEA-Dateien"):
        inserted, skipped = import_file(file_path, conn, args.batch_size, args.source_name)
        total_inserted += inserted
        total_skipped += skipped
    
    # Verbindung schließen
    conn.close()
    
    # Zusammenfassung anzeigen
    logger.info("=" * 50)
    logger.info(f"Import abgeschlossen:")
    logger.info(f"- Verarbeitete Dateien: {len(json_files)}")
    logger.info(f"- Importierte Einträge: {total_inserted}")
    logger.info(f"- Übersprungene Einträge: {total_skipped}")
    logger.info("=" * 50)
    
    # Datenbankstatistiken anzeigen
    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM aqea_entries")
    total_entries = cursor.fetchone()[0]
    
    cursor.execute("SELECT domain, COUNT(*) FROM aqea_entries GROUP BY domain")
    domain_stats = cursor.fetchall()
    
    logger.info(f"Datenbankstatistik:")
    logger.info(f"- Gesamtanzahl Einträge: {total_entries}")
    logger.info("- Einträge pro Domain:")
    for domain, count in domain_stats:
        logger.info(f"  - {domain}: {count}")
    
    conn.close()

if __name__ == "__main__":
    main() 
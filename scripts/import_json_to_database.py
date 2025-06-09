#!/usr/bin/env python3
"""
AQEA JSON to Database Importer

Dieses Skript importiert alle in JSON-Dateien gespeicherten AQEA-Einträge in die Datenbank.
Es ist ideal für die Verarbeitung von Daten, die mit dem "extract_all_guaranteed.py"-Skript
extrahiert wurden.

Nutzung:
python scripts/import_json_to_database.py --input-dir extracted_data
"""

import asyncio
import argparse
import os
import sys
import logging
import json
import glob
from datetime import datetime
from typing import Dict, List, Any, Set

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import get_database, close_database
from src.utils.config import Config
from src.utils.logger import setup_logging
from src.aqea.schema import AQEAEntry

# Configure logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

async def import_entries_batch(database, entries_data, batch_size=100):
    """Import a batch of entries into the database."""
    total_entries = len(entries_data)
    imported = 0
    errors = []
    
    # Process in batches
    for i in range(0, total_entries, batch_size):
        batch = entries_data[i:i+batch_size]
        batch_entries = []
        
        # Convert dictionaries to AQEAEntry objects
        for entry_dict in batch:
            try:
                entry = AQEAEntry(
                    address=entry_dict['address'],
                    label=entry_dict['label'],
                    description=entry_dict['description'],
                    domain=entry_dict['domain'],
                    status=entry_dict.get('status', 'active'),
                    created_at=datetime.fromisoformat(entry_dict['created_at'].replace('Z', '+00:00')) if isinstance(entry_dict['created_at'], str) else entry_dict['created_at'],
                    updated_at=datetime.fromisoformat(entry_dict['updated_at'].replace('Z', '+00:00')) if isinstance(entry_dict['updated_at'], str) else entry_dict['updated_at'],
                    created_by=entry_dict.get('created_by', 'json-importer'),
                    lang_ui=entry_dict.get('lang_ui'),
                    meta=entry_dict.get('meta', {})
                )
                batch_entries.append(entry)
            except Exception as e:
                error = f"Error converting entry {entry_dict.get('address', 'unknown')}: {str(e)}"
                logger.warning(error)
                errors.append(error)
                continue
        
        # Store entries in database
        if batch_entries:
            try:
                result = await database.store_aqea_entries(batch_entries)
                imported += result.get('inserted', 0)
                if result.get('errors'):
                    errors.extend(result['errors'])
                
                logger.info(f"Batch {i//batch_size + 1}/{(total_entries+batch_size-1)//batch_size}: "
                          f"{result.get('inserted', 0)}/{len(batch_entries)} Einträge importiert")
            except Exception as e:
                error = f"Database error in batch {i//batch_size + 1}: {str(e)}"
                logger.error(error)
                errors.append(error)
    
    return {
        'total': total_entries,
        'imported': imported,
        'errors': len(errors),
        'error_details': errors[:10]  # Only show first 10 errors
    }

async def process_json_file(file_path, database, processed_addresses):
    """Process a single JSON file and import its entries to the database."""
    logger.info(f"Verarbeite Datei: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            entries_data = json.load(f)
        
        # Skip entries with addresses we've already processed
        unique_entries = []
        for entry in entries_data:
            address = entry.get('address')
            if address and address not in processed_addresses:
                unique_entries.append(entry)
                processed_addresses.add(address)
        
        if not unique_entries:
            logger.info(f"Keine neuen Einträge in {file_path} gefunden")
            return {'file': file_path, 'imported': 0, 'skipped': len(entries_data)}
        
        logger.info(f"Importiere {len(unique_entries)} von {len(entries_data)} Einträgen aus {file_path}")
        result = await import_entries_batch(database, unique_entries)
        result['file'] = file_path
        result['skipped'] = len(entries_data) - len(unique_entries)
        
        return result
    
    except json.JSONDecodeError:
        logger.error(f"Ungültiges JSON-Format in {file_path}")
        return {'file': file_path, 'error': 'Invalid JSON format', 'imported': 0}
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten von {file_path}: {e}")
        return {'file': file_path, 'error': str(e), 'imported': 0}

async def run_import(args):
    """Run the import process."""
    # Load configuration
    config = Config.load(args.config)
    
    # Connect to database
    logger.info("Verbinde mit Datenbank...")
    database = await get_database(config)
    if not database:
        logger.error("Keine Datenbankverbindung möglich, Abbruch")
        return 1
    
    # Find all JSON files
    input_dir = os.path.abspath(args.input_dir)
    if not os.path.isdir(input_dir):
        logger.error(f"Verzeichnis nicht gefunden: {input_dir}")
        return 1
    
    json_pattern = os.path.join(input_dir, '**', '*.json')
    json_files = glob.glob(json_pattern, recursive=True)
    
    if not json_files:
        logger.warning(f"Keine JSON-Dateien gefunden in {input_dir}")
        return 0
    
    logger.info(f"Gefunden: {len(json_files)} JSON-Dateien in {input_dir}")
    
    # Track processed addresses to avoid duplicates
    processed_addresses = set()
    
    # Process files
    total_stats = {
        'files_processed': 0,
        'entries_imported': 0,
        'entries_skipped': 0,
        'files_with_errors': 0
    }
    
    # Sort files by creation time to process older files first
    json_files.sort(key=lambda f: os.path.getctime(f))
    
    for file_path in json_files:
        try:
            result = await process_json_file(file_path, database, processed_addresses)
            
            total_stats['files_processed'] += 1
            total_stats['entries_imported'] += result.get('imported', 0)
            total_stats['entries_skipped'] += result.get('skipped', 0)
            
            if 'error' in result:
                total_stats['files_with_errors'] += 1
            
            # Report progress periodically
            if total_stats['files_processed'] % 10 == 0:
                logger.info(f"Fortschritt: {total_stats['files_processed']}/{len(json_files)} Dateien, "
                          f"{total_stats['entries_imported']} Einträge importiert")
                
            # Optional: move processed files to an "archive" directory
            if args.archive and not 'error' in result:
                archive_dir = os.path.join(input_dir, 'archive')
                os.makedirs(archive_dir, exist_ok=True)
                archive_path = os.path.join(archive_dir, os.path.basename(file_path))
                os.rename(file_path, archive_path)
                logger.debug(f"Datei verschoben nach: {archive_path}")
                
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei {file_path}: {e}")
            total_stats['files_with_errors'] += 1
    
    # Final report
    logger.info("=== Import abgeschlossen ===")
    logger.info(f"Dateien verarbeitet: {total_stats['files_processed']}/{len(json_files)}")
    logger.info(f"Einträge importiert: {total_stats['entries_imported']}")
    logger.info(f"Einträge übersprungen (Duplikate): {total_stats['entries_skipped']}")
    logger.info(f"Dateien mit Fehlern: {total_stats['files_with_errors']}")
    
    # Close database connection
    await close_database()
    return 0

def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AQEA JSON to Database Importer")
    parser.add_argument("--input-dir", "-i", default="extracted_data", 
                      help="Verzeichnis mit JSON-Dateien (Standard: extracted_data)")
    parser.add_argument("--config", "-c", default="config/default.yml", 
                      help="Konfigurationsdatei (Standard: config/default.yml)")
    parser.add_argument("--archive", "-a", action="store_true", 
                      help="Verschiebe verarbeitete Dateien in ein Archiv-Verzeichnis")
    args = parser.parse_args()
    
    # Run the import
    try:
        return asyncio.run(run_import(args))
    except KeyboardInterrupt:
        logger.info("Import unterbrochen")
        return 1
    except Exception as e:
        logger.error(f"Unbehandelte Ausnahme: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
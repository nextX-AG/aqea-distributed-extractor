#!/usr/bin/env python3
"""
AQEA JSON Entry Counter

Dieses Skript zählt die Anzahl der Einträge in allen JSON-Dateien im angegebenen Verzeichnis.
Es zeigt sowohl die Gesamtzahl als auch die Anzahl der eindeutigen Einträge (basierend auf AQEA-Adressen).

Nutzung:
python scripts/count_json_entries.py --input-dir extracted_data
"""

import argparse
import os
import sys
import logging
import json
import glob
from typing import Dict, List, Any, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def count_entries(input_dir: str):
    """Count entries in all JSON files in the directory."""
    input_dir = os.path.abspath(input_dir)
    if not os.path.isdir(input_dir):
        logger.error(f"Verzeichnis nicht gefunden: {input_dir}")
        return 1
    
    # Find all JSON files
    json_pattern = os.path.join(input_dir, '**', '*.json')
    json_files = glob.glob(json_pattern, recursive=True)
    
    if not json_files:
        logger.warning(f"Keine JSON-Dateien gefunden in {input_dir}")
        return 0
    
    logger.info(f"Gefunden: {len(json_files)} JSON-Dateien in {input_dir}")
    
    # Count entries
    total_entries = 0
    unique_addresses = set()
    entries_by_file = {}
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
                
                if not isinstance(entries, list):
                    logger.warning(f"Ungültiges Format in {file_path}: Kein Array")
                    continue
                
                file_entries = len(entries)
                total_entries += file_entries
                
                # Count unique addresses
                addresses = [entry.get('address') for entry in entries if entry.get('address')]
                unique_in_file = len(set(addresses))
                
                # Add to global unique set
                unique_addresses.update(addresses)
                
                # Store statistics for this file
                entries_by_file[file_path] = {
                    'total': file_entries,
                    'unique': unique_in_file
                }
                
                logger.info(f"Datei {os.path.basename(file_path)}: {file_entries} Einträge ({unique_in_file} eindeutig)")
                
        except json.JSONDecodeError:
            logger.error(f"Ungültiges JSON-Format in {file_path}")
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von {file_path}: {e}")
    
    # Print summary
    logger.info("=== Zusammenfassung ===")
    logger.info(f"Gesamtzahl Dateien: {len(json_files)}")
    logger.info(f"Gesamtzahl Einträge: {total_entries}")
    logger.info(f"Eindeutige AQEA-Adressen: {len(unique_addresses)}")
    logger.info(f"Duplikate: {total_entries - len(unique_addresses)}")
    
    # Show most common addresses if duplicates exist
    if total_entries > len(unique_addresses):
        address_counts = {}
        for file_path in json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                    
                    for entry in entries:
                        address = entry.get('address')
                        if address:
                            address_counts[address] = address_counts.get(address, 0) + 1
            except:
                pass
        
        # Find addresses with multiple occurrences
        duplicates = {addr: count for addr, count in address_counts.items() if count > 1}
        
        if duplicates:
            # Sort by count (most duplicates first)
            top_duplicates = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]
            
            logger.info("Top-Duplikate:")
            for address, count in top_duplicates:
                logger.info(f"  {address}: {count}x")
    
    return 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AQEA JSON Entry Counter")
    parser.add_argument("--input-dir", "-i", default="extracted_data",
                      help="Verzeichnis mit JSON-Dateien (Standard: extracted_data)")
    
    args = parser.parse_args()
    
    try:
        return count_entries(args.input_dir)
    except KeyboardInterrupt:
        logger.info("Zählung unterbrochen")
        return 1
    except Exception as e:
        logger.error(f"Unbehandelte Ausnahme: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
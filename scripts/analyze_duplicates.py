#!/usr/bin/env python3
"""
Duplikat-Analyse für AQEA-Einträge

Dieses Skript analysiert die JSON-Dateien auf Duplikate, um zu verstehen, 
warum nur ein kleiner Teil der Einträge in der Datenbank landet.
"""

import os
import sys
import json
import glob
import logging
from collections import Counter
from datetime import datetime
from tqdm import tqdm

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("duplicate-analyzer")

def find_json_files(source_dir):
    """Findet alle AQEA JSON-Dateien im angegebenen Verzeichnis."""
    json_pattern = os.path.join(source_dir, "**", "*.json")
    files = glob.glob(json_pattern, recursive=True)
    
    # Filtere auf AQEA-Dateien
    aqea_files = [f for f in files if "aqea" in f.lower()]
    
    logger.info(f"{len(aqea_files)} AQEA-JSON-Dateien gefunden")
    return aqea_files

def analyze_file(file_path, address_counter):
    """Analysiert eine JSON-Datei auf Duplikate."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Datei {file_path}: {e}")
        return 0
    
    # Stelle sicher, dass wir mit einer Liste von Einträgen arbeiten
    if isinstance(data, dict) and "entries" in data:
        entries = data["entries"]
    elif isinstance(data, list):
        entries = data
    else:
        logger.warning(f"Unerwartetes Format in {file_path}, überspringe...")
        return 0
    
    file_entries = 0
    for entry in entries:
        if "address" in entry:
            address_counter[entry["address"]] += 1
            file_entries += 1
    
    return file_entries

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analysiert AQEA-Einträge auf Duplikate")
    parser.add_argument("--source-dir", "-s", default="extracted_data/dump/aqea",
                       help="Verzeichnis mit AQEA-JSON-Dateien")
    args = parser.parse_args()
    
    # JSON-Dateien finden
    json_files = find_json_files(args.source_dir)
    
    if not json_files:
        logger.warning(f"Keine AQEA-JSON-Dateien in {args.source_dir} gefunden")
        return
    
    # Counter für Adressen initialisieren
    address_counter = Counter()
    
    # Dateien verarbeiten mit Fortschrittsbalken
    total_entries = 0
    for file_path in tqdm(json_files, desc="Analysiere Dateien"):
        file_entries = analyze_file(file_path, address_counter)
        total_entries += file_entries
    
    # Ergebnisse zusammenfassen
    unique_addresses = len(address_counter)
    duplicate_ratio = (total_entries - unique_addresses) / total_entries * 100 if total_entries > 0 else 0
    
    print("\n" + "=" * 60)
    print(f"Duplikat-Analyse Ergebnisse:")
    print(f"- Verarbeitete Dateien: {len(json_files)}")
    print(f"- Gesamtzahl der Einträge: {total_entries}")
    print(f"- Eindeutige AQEA-Adressen: {unique_addresses}")
    print(f"- Duplikat-Verhältnis: {duplicate_ratio:.2f}%")
    print("=" * 60)
    
    # Top-Duplikate anzeigen
    print("\nTop 20 häufigsten Duplikate:")
    for address, count in address_counter.most_common(20):
        if count > 1:  # Nur Duplikate anzeigen
            print(f"- Adresse: {address} - {count} mal")
    
    # Verteilung der Duplikate
    counts = list(address_counter.values())
    singles = counts.count(1)
    duplicates = sum(1 for c in counts if c > 1)
    
    print("\nVerteilung der Duplikate:")
    print(f"- Einträge, die nur einmal vorkommen: {singles}")
    print(f"- Einträge, die mehr als einmal vorkommen: {duplicates}")
    
    if duplicates > 0:
        # Berechne Statistiken zu den Duplikaten
        duplicate_counts = [c for c in counts if c > 1]
        avg_duplicates = sum(duplicate_counts) / len(duplicate_counts)
        max_duplicates = max(duplicate_counts)
        
        print(f"- Durchschnittliche Anzahl Duplikate pro mehrfach vorkommender Adresse: {avg_duplicates:.2f}")
        print(f"- Maximale Anzahl Duplikate für eine Adresse: {max_duplicates}")

if __name__ == "__main__":
    main() 
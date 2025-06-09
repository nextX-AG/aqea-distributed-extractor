#!/usr/bin/env python3
"""
AQEA-Wortvielfalt-Analyse

Dieses Skript analysiert die Vielfalt der Wörter (Label) 
für jede AQEA-Adresse in den JSON-Dateien.
"""

import os
import sys
import json
import glob
import logging
from collections import defaultdict, Counter
from tqdm import tqdm

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("word-diversity-analyzer")

def find_json_files(source_dir):
    """Findet alle AQEA JSON-Dateien im angegebenen Verzeichnis."""
    json_pattern = os.path.join(source_dir, "**", "*.json")
    files = glob.glob(json_pattern, recursive=True)
    
    # Filtere auf AQEA-Dateien
    aqea_files = [f for f in files if "aqea" in f.lower()]
    
    logger.info(f"{len(aqea_files)} AQEA-JSON-Dateien gefunden")
    return aqea_files

def analyze_file(file_path, address_to_labels):
    """Analysiert eine JSON-Datei auf Wortvielfalt pro Adresse."""
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
        if "address" in entry and "label" in entry:
            address = entry["address"]
            label = entry["label"]
            address_to_labels[address].add(label)
            file_entries += 1
    
    return file_entries

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analysiert die Wortvielfalt für AQEA-Adressen")
    parser.add_argument("--source-dir", "-s", default="extracted_data/dump/aqea",
                       help="Verzeichnis mit AQEA-JSON-Dateien")
    parser.add_argument("--top", "-t", type=int, default=20,
                       help="Anzahl der Top-Adressen, die angezeigt werden sollen")
    parser.add_argument("--min-words", "-m", type=int, default=2,
                       help="Minimale Anzahl unterschiedlicher Wörter für Adressen, die angezeigt werden")
    parser.add_argument("--sample-address", "-a", 
                       help="Zeige Beispiele für eine bestimmte Adresse")
    args = parser.parse_args()
    
    # JSON-Dateien finden
    json_files = find_json_files(args.source_dir)
    
    if not json_files:
        logger.warning(f"Keine AQEA-JSON-Dateien in {args.source_dir} gefunden")
        return
    
    # Dictionary für Adressen zu Labels initialisieren
    address_to_labels = defaultdict(set)
    
    # Dateien verarbeiten mit Fortschrittsbalken
    total_entries = 0
    for file_path in tqdm(json_files, desc="Analysiere Dateien"):
        file_entries = analyze_file(file_path, address_to_labels)
        total_entries += file_entries
    
    # Ergebnisse zusammenfassen
    unique_addresses = len(address_to_labels)
    total_unique_labels = sum(len(labels) for labels in address_to_labels.values())
    
    print("\n" + "=" * 60)
    print(f"Wortvielfalt-Analyse Ergebnisse:")
    print(f"- Verarbeitete Dateien: {len(json_files)}")
    print(f"- Gesamtzahl der Einträge: {total_entries}")
    print(f"- Eindeutige AQEA-Adressen: {unique_addresses}")
    print(f"- Eindeutige Wörter (Labels) insgesamt: {total_unique_labels}")
    print(f"- Durchschnittliche Wörter pro Adresse: {total_unique_labels/unique_addresses:.2f}")
    print("=" * 60)
    
    # Wortvielfalt pro Adresse berechnen
    word_diversity = {address: len(labels) for address, labels in address_to_labels.items()}
    
    # Verteilung der Wortvielfalt
    diversity_counter = Counter(word_diversity.values())
    
    print("\nVerteilung der Wortvielfalt:")
    print(f"- Adressen mit genau einem Wort: {diversity_counter[1]}")
    print(f"- Adressen mit 2-5 Wörtern: {sum(diversity_counter[i] for i in range(2, 6))}")
    print(f"- Adressen mit 6-10 Wörtern: {sum(diversity_counter[i] for i in range(6, 11))}")
    print(f"- Adressen mit mehr als 10 Wörtern: {sum(diversity_counter[i] for i in range(11, max(diversity_counter.keys())+1))}")
    
    # Top-Adressen mit der größten Wortvielfalt
    print(f"\nTop {args.top} Adressen mit der größten Wortvielfalt:")
    for i, (address, count) in enumerate(sorted(word_diversity.items(), key=lambda x: x[1], reverse=True)[:args.top]):
        if count >= args.min_words:
            print(f"{i+1}. Adresse: {address} - {count} unterschiedliche Wörter")
            # Zeige Beispielwörter für jede Adresse
            sample_words = list(address_to_labels[address])[:5]  # Zeige maximal 5 Beispiele
            print(f"   Beispiele: {', '.join(sample_words)}" + (", ..." if len(sample_words) < len(address_to_labels[address]) else ""))
    
    # Falls eine spezifische Adresse angegeben wurde, zeige alle Wörter dafür
    if args.sample_address and args.sample_address in address_to_labels:
        print(f"\nAlle Wörter für Adresse {args.sample_address}:")
        for word in sorted(address_to_labels[args.sample_address]):
            print(f"- {word}")

if __name__ == "__main__":
    main() 
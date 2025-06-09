#!/usr/bin/env python
"""
Überwachungsskript für den Dump-Extraktionsprozess

Dieses Skript überwacht den Fortschritt der Dump-Extraktion in Echtzeit und
zeigt verschiedene Statistiken an.
"""

import os
import sys
import json
import time
import argparse
import psutil
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

def find_extraction_process():
    """Sucht nach einem laufenden Extraktionsprozess."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'extract_from_dump.py' in ' '.join(cmdline):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def get_file_stats(output_dir):
    """Sammelt Statistiken über die extrahierten Dateien."""
    stats = {
        'raw_files': 0,
        'raw_size': 0,
        'aqea_files': 0,
        'aqea_size': 0,
        'single_raw_entries': 0,
        'single_aqea_entries': 0,
    }
    
    raw_dir = output_dir / 'raw'
    aqea_dir = output_dir / 'aqea'
    
    # Überprüfe das Raw-Verzeichnis
    if raw_dir.exists():
        for file in raw_dir.glob('*.json'):
            stats['raw_files'] += 1
            stats['raw_size'] += file.stat().st_size
            
            # Überprüfe auf Single-File-Modus
            if file.name.startswith('de_all_entries'):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        # Zähle die Einträge durch Zählen der Kommas
                        content = f.read()
                        # Ungefähre Zählung durch Zählen der Kommas zwischen Objekten
                        stats['single_raw_entries'] = content.count('}, {') + 1
                except Exception as e:
                    print(f"Fehler beim Lesen der Datei {file}: {e}")
    
    # Überprüfe das AQEA-Verzeichnis
    if aqea_dir.exists():
        for file in aqea_dir.glob('*.json'):
            stats['aqea_files'] += 1
            stats['aqea_size'] += file.stat().st_size
            
            # Überprüfe auf Single-File-Modus
            if file.name.startswith('de_all_aqea_entries'):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Ungefähre Zählung durch Zählen der Kommas zwischen Objekten
                        stats['single_aqea_entries'] = content.count('}, {') + 1
                except Exception as e:
                    print(f"Fehler beim Lesen der Datei {file}: {e}")
    
    return stats

def check_logs(log_file):
    """Überprüft die Logs auf wichtige Meldungen."""
    if not log_file.exists():
        return None
    
    try:
        last_lines = []
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-10:]  # Letzte 10 Zeilen
        
        # Extrahiere Informationen aus den Log-Zeilen
        extraction_rate = None
        for line in reversed(last_lines):
            if 'Verarbeitungsrate:' in line:
                parts = line.split('Verarbeitungsrate:')
                if len(parts) > 1:
                    rate_part = parts[1].strip()
                    try:
                        extraction_rate = float(rate_part.split()[0])
                    except ValueError:
                        pass
                break
        
        return {
            'last_lines': last_lines,
            'extraction_rate': extraction_rate
        }
    except Exception as e:
        print(f"Fehler beim Lesen der Log-Datei: {e}")
        return None

def format_size(size_bytes):
    """Formatiert Bytes in eine menschenlesbare Größe."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def monitor_extraction(output_dir, refresh_interval=5):
    """Überwacht den Extraktionsprozess in Echtzeit."""
    output_dir = Path(output_dir)
    log_file = Path('logs/dump_extraction.log')
    
    # Initialisiere tqdm für den Fortschrittsbalken
    pbar = tqdm(total=100, desc="Extraktion", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}")
    
    try:
        last_entries = 0
        last_check_time = time.time()
        last_update_time = time.time()
        
        while True:
            # Überprüfe, ob der Extraktionsprozess noch läuft
            proc = find_extraction_process()
            if not proc:
                print("\nExtraktionsprozess nicht gefunden oder beendet.")
                
                # Zeige abschließende Statistiken
                final_stats = get_file_stats(output_dir)
                print("\n=== Abschließende Statistiken ===")
                print(f"Extrahierte Einträge: {final_stats['single_raw_entries']}")
                print(f"AQEA-Einträge: {final_stats['single_aqea_entries']}")
                print(f"Konvertierungsrate: {final_stats['single_aqea_entries'] / final_stats['single_raw_entries'] * 100:.2f}% (falls Einträge > 0)")
                print(f"Gesamtgröße: {format_size(final_stats['raw_size'] + final_stats['aqea_size'])}")
                
                # Überprüfe, ob eine Zusammenfassungsdatei existiert
                summary_file = output_dir / "de_extraction_summary.json"
                if summary_file.exists():
                    try:
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                            print("\n=== Zusammenfassung ===")
                            print(f"Verarbeitete Seiten: {summary['statistics']['processed_pages']:,}")
                            print(f"Verarbeitungsrate: {summary['extraction_info']['processing_rate']:.1f} Seiten/Sekunde")
                            print(f"Dauer: {summary['extraction_info']['duration']}")
                    except Exception as e:
                        print(f"Fehler beim Lesen der Zusammenfassungsdatei: {e}")
                
                break
            
            # Sammle Statistiken
            stats = get_file_stats(output_dir)
            log_info = check_logs(log_file)
            
            # Berechne die aktuelle Extraktionsrate
            current_time = time.time()
            elapsed = current_time - last_check_time
            entries_diff = stats['single_raw_entries'] - last_entries
            entries_per_second = entries_diff / elapsed if elapsed > 0 else 0
            
            # Aktualisiere den Fortschrittsbalken
            if current_time - last_update_time >= refresh_interval:
                # Schätze den Fortschritt basierend auf der erwarteten Gesamtzahl (ca. 800.000 Einträge)
                progress = min(100, stats['single_raw_entries'] / 800000 * 100)
                pbar.n = progress
                pbar.set_postfix({
                    'Einträge': stats['single_raw_entries'], 
                    'AQEA': stats['single_aqea_entries'],
                    'Rate': f"{entries_per_second:.1f} E/s"
                })
                pbar.update(0)  # Aktualisiert die Anzeige ohne den Wert zu ändern
                
                # Zeige zusätzliche Informationen
                if log_info and log_info['extraction_rate']:
                    print(f"\nVerarbeitungsrate: {log_info['extraction_rate']:.1f} Seiten/Sekunde")
                
                # Speichere die aktuellen Werte für die nächste Berechnung
                last_entries = stats['single_raw_entries']
                last_check_time = current_time
                last_update_time = current_time
            
            # Warte kurz
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nÜberwachung beendet.")
    finally:
        pbar.close()

def main():
    parser = argparse.ArgumentParser(description="Überwache den Fortschritt der Dump-Extraktion")
    parser.add_argument("--output-dir", "-o", default="extracted_data/dump",
                       help="Verzeichnis mit den Ausgabedateien (Standard: extracted_data/dump)")
    parser.add_argument("--refresh", "-r", type=int, default=5,
                       help="Aktualisierungsintervall in Sekunden (Standard: 5)")
    
    args = parser.parse_args()
    
    print("=== Dump-Extraktions-Monitor ===")
    print(f"Überwache Ausgabeverzeichnis: {args.output_dir}")
    print(f"Aktualisierungsintervall: {args.refresh} Sekunden")
    print("Drücke Strg+C zum Beenden...")
    print("")
    
    monitor_extraction(args.output_dir, args.refresh)

if __name__ == "__main__":
    main() 
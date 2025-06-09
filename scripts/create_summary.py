#!/usr/bin/env python
"""
Erstellt eine Zusammenfassungsdatei für die extrahierten Daten

Dieses Skript analysiert die extrahierten Daten und erstellt eine JSON- und
Textdatei mit Zusammenfassungen und Statistiken.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import platform

def format_size(size_bytes):
    """Formatiert Bytes in eine menschenlesbare Größe."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def count_entries(file_path):
    """Zählt die Anzahl der Einträge in einer JSON-Datei."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Ungefähre Zählung durch Zählen der Kommas zwischen Objekten
            count = content.count('}, {') + 1
            return count
    except Exception as e:
        print(f"Fehler beim Zählen der Einträge in {file_path}: {e}")
        return 0

def analyze_aqea_entries(file_path):
    """Analysiert die AQEA-Einträge nach verschiedenen Kriterien."""
    try:
        # Wenn die Datei zu groß ist, verwenden wir eine Stichprobe
        file_size = os.path.getsize(file_path)
        
        if file_size > 100 * 1024 * 1024:  # > 100 MB
            print(f"Datei ist groß ({format_size(file_size)}), analysiere nur eine Stichprobe...")
            sample_size = 10000
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Sehr grobe Schätzung der Gesamtzahl der Einträge
                total_entries = content.count('}, {') + 1
                
                # Versuche, den Anfang der Datei zu laden
                try:
                    # Finde die ersten N Einträge
                    entries = []
                    start_pos = content.find('[{')
                    if start_pos >= 0:
                        # Zähle die gefundenen schließenden Klammern
                        count = 0
                        pos = start_pos + 2  # Überspringe '[{'
                        
                        while count < sample_size and pos < len(content):
                            if content[pos:pos+2] == '}, ':
                                count += 1
                                if count < sample_size:
                                    entries.append(content[start_pos:pos+1])
                                    start_pos = pos + 2
                            pos += 1
                    
                    if not entries:
                        return {"error": "Konnte keine Einträge für die Stichprobe finden"}
                except Exception as e:
                    return {"error": f"Fehler bei der Stichprobenanalyse: {e}"}
        else:
            # Datei ist klein genug für vollständige Analyse
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                entries = json.loads(content)
                total_entries = len(entries)
        
        # Analyse der Einträge
        categories = {}
        domains = {}
        
        # Entweder die Stichprobe oder alle Einträge durchlaufen
        if isinstance(entries, list):
            for entry in entries:
                # Domain extrahieren (z.B. 0x20 für Deutsch)
                domain = entry.get('domain', 'unbekannt')
                if domain in domains:
                    domains[domain] += 1
                else:
                    domains[domain] = 1
                
                # Kategorie extrahieren (aus der Adresse, z.B. 0x20:01:01:01)
                address = entry.get('address', '')
                if ':' in address:
                    parts = address.split(':')
                    if len(parts) >= 2:
                        category = parts[1]
                        if category in categories:
                            categories[category] += 1
                        else:
                            categories[category] = 1
        
        # Normalisiere die Zahlen, wenn wir eine Stichprobe verwendet haben
        if file_size > 100 * 1024 * 1024:
            ratio = total_entries / len(entries)
            for key in domains:
                domains[key] = int(domains[key] * ratio)
            for key in categories:
                categories[key] = int(categories[key] * ratio)
        
        return {
            "total_entries": total_entries,
            "domains": domains,
            "categories": categories,
            "is_sample": file_size > 100 * 1024 * 1024
        }
    except Exception as e:
        print(f"Fehler bei der Analyse der AQEA-Einträge: {e}")
        return {"error": str(e)}

def create_summary(output_dir, language="de"):
    """Erstellt eine Zusammenfassungsdatei für die extrahierten Daten."""
    output_dir = Path(output_dir)
    
    # Überprüfe, ob die Verzeichnisse existieren
    raw_dir = output_dir / "raw"
    aqea_dir = output_dir / "aqea"
    
    if not raw_dir.exists() or not aqea_dir.exists():
        print(f"Fehler: Verzeichnisse {raw_dir} oder {aqea_dir} existieren nicht.")
        return False
    
    # Suche nach den Single-File-Einträgen
    raw_file = raw_dir / f"{language}_all_entries.json"
    aqea_file = aqea_dir / f"{language}_all_aqea_entries.json"
    
    if not raw_file.exists() or not aqea_file.exists():
        print(f"Fehler: Single-File-Einträge ({raw_file} oder {aqea_file}) existieren nicht.")
        return False
    
    # Sammle Statistiken
    raw_entries = count_entries(raw_file)
    aqea_entries = count_entries(aqea_file)
    
    raw_size = os.path.getsize(raw_file)
    aqea_size = os.path.getsize(aqea_file)
    
    # Analysiere AQEA-Einträge
    aqea_analysis = analyze_aqea_entries(aqea_file)
    
    # Erstelle die Zusammenfassung
    summary = {
        "extraction_info": {
            "language": language,
            "timestamp": datetime.now().isoformat(),
            "created_by": f"create_summary.py ({platform.python_version()})"
        },
        "statistics": {
            "raw_entries": raw_entries,
            "aqea_entries": aqea_entries,
            "conversion_rate": round(aqea_entries / raw_entries * 100, 2) if raw_entries > 0 else 0,
            "raw_size": raw_size,
            "aqea_size": aqea_size,
            "total_size": raw_size + aqea_size
        },
        "files": {
            "raw_entries_file": str(raw_file),
            "aqea_entries_file": str(aqea_file)
        },
        "aqea_analysis": aqea_analysis,
        "system_info": {
            "system": platform.system(),
            "python_version": platform.python_version()
        }
    }
    
    # Speichere die Zusammenfassung als JSON
    summary_file = output_dir / f"{language}_extraction_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"JSON-Zusammenfassung gespeichert in {summary_file}")
    
    # Erstelle auch eine Textdatei für bessere Lesbarkeit
    summary_txt_path = output_dir / f"{language}_extraction_summary.txt"
    with open(summary_txt_path, "w", encoding="utf-8") as f:
        f.write(f"AQEA Wiktionary Dump Extraktion - {language.upper()}\n")
        f.write(f"========================================\n\n")
        f.write(f"Erstellt am: {summary['extraction_info']['timestamp']}\n\n")
        
        f.write(f"STATISTIKEN:\n")
        f.write(f"  Extrahierte Einträge:   {summary['statistics']['raw_entries']:,}\n")
        f.write(f"  AQEA-Einträge:          {summary['statistics']['aqea_entries']:,}\n")
        f.write(f"  Konvertierungsrate:     {summary['statistics']['conversion_rate']}%\n")
        f.write(f"  Roheinträge-Größe:      {format_size(summary['statistics']['raw_size'])}\n")
        f.write(f"  AQEA-Einträge-Größe:    {format_size(summary['statistics']['aqea_size'])}\n")
        f.write(f"  Gesamtgröße:            {format_size(summary['statistics']['total_size'])}\n\n")
        
        f.write(f"DATEIEN:\n")
        f.write(f"  Roheinträge:            {summary['files']['raw_entries_file']}\n")
        f.write(f"  AQEA-Einträge:          {summary['files']['aqea_entries_file']}\n\n")
        
        f.write(f"AQEA-ANALYSE:\n")
        if "error" in summary["aqea_analysis"]:
            f.write(f"  Fehler bei der Analyse: {summary['aqea_analysis']['error']}\n")
        else:
            f.write(f"  Gesamteinträge:         {summary['aqea_analysis']['total_entries']:,}\n")
            f.write(f"  Basierend auf Stichprobe: {'Ja' if summary['aqea_analysis']['is_sample'] else 'Nein'}\n\n")
            
            f.write(f"  DOMAINS:\n")
            for domain, count in sorted(summary["aqea_analysis"]["domains"].items(), key=lambda x: x[1], reverse=True):
                percentage = count / summary["aqea_analysis"]["total_entries"] * 100 if summary["aqea_analysis"]["total_entries"] > 0 else 0
                f.write(f"    {domain}: {count:,} ({percentage:.1f}%)\n")
            
            f.write(f"\n  KATEGORIEN (TOP 10):\n")
            sorted_categories = sorted(summary["aqea_analysis"]["categories"].items(), key=lambda x: x[1], reverse=True)[:10]
            for category, count in sorted_categories:
                percentage = count / summary["aqea_analysis"]["total_entries"] * 100 if summary["aqea_analysis"]["total_entries"] > 0 else 0
                f.write(f"    {category}: {count:,} ({percentage:.1f}%)\n")
        
        f.write(f"\nSYSTEM:\n")
        f.write(f"  System:                 {summary['system_info']['system']}\n")
        f.write(f"  Python-Version:         {summary['system_info']['python_version']}\n")
    
    print(f"Text-Zusammenfassung gespeichert in {summary_txt_path}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Erstellt eine Zusammenfassungsdatei für die extrahierten Daten")
    parser.add_argument("--output-dir", "-o", default="extracted_data/dump",
                       help="Verzeichnis mit den Ausgabedateien (Standard: extracted_data/dump)")
    parser.add_argument("--language", "-l", default="de",
                       help="Sprache der extrahierten Daten (Standard: de)")
    
    args = parser.parse_args()
    
    print("=== Dump-Extraktions-Zusammenfassung ===")
    print(f"Analysiere Ausgabeverzeichnis: {args.output_dir}")
    print(f"Sprache: {args.language}")
    print("")
    
    if create_summary(args.output_dir, args.language):
        print("\nZusammenfassung erfolgreich erstellt.")
    else:
        print("\nFehler bei der Erstellung der Zusammenfassung.")
        sys.exit(1)

if __name__ == "__main__":
    main() 
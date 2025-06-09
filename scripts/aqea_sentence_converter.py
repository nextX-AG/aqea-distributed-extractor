#!/usr/bin/env python3
"""
AQEA Satz-Konverter

Dieses Skript nimmt einen Satz als Eingabe, schlägt jedes Wort in den extrahierten 
AQEA-JSON-Dateien nach und gibt den kompletten Satz mit AQEA-codierten Wörtern zurück.
"""

import os
import sys
import json
import logging
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Füge das Projekt-Verzeichnis zum Python-Pfad hinzu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("aqea-sentence")

class AQEASentenceConverter:
    """Konvertiert Sätze in AQEA-Format, indem jedes Wort einzeln nachgeschlagen wird."""
    
    def __init__(self, json_dir: str = "extracted_data/dump/aqea"):
        """Initialisiert den Konverter mit dem Verzeichnis der JSON-Dateien."""
        self.json_dir = Path(json_dir)
        if not self.json_dir.exists():
            logger.warning(f"Verzeichnis {json_dir} existiert nicht!")
        
        self.aqea_cache = {}  # Cache für bereits nachgeschlagene Wörter
        self.loaded_files = set()  # Menge der bereits geladenen JSON-Dateien
        
        logger.info(f"AQEA Satz-Konverter initialisiert. Verzeichnis: {json_dir}")
    
    async def load_json_files(self):
        """Lädt alle AQEA-JSON-Dateien aus dem Verzeichnis."""
        logger.info(f"Lade AQEA-JSON-Dateien aus {self.json_dir}...")
        
        if not self.json_dir.exists():
            logger.error(f"Verzeichnis {self.json_dir} existiert nicht!")
            return
        
        json_files = list(self.json_dir.glob("*.json"))
        if not json_files:
            logger.warning(f"Keine JSON-Dateien in {self.json_dir} gefunden!")
            return
        
        logger.info(f"{len(json_files)} JSON-Dateien gefunden.")
        
        # Lade jede Datei und füge die Einträge zum Cache hinzu
        for json_file in json_files:
            if json_file in self.loaded_files:
                continue  # Überspringe bereits geladene Dateien
                
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                
                # Füge jeden Eintrag zum Cache hinzu
                for entry in entries:
                    if 'label' in entry and 'address' in entry:
                        # Normalisiere das Label (Kleinbuchstaben, ohne Sonderzeichen)
                        normalized_label = self._normalize_word(entry['label'])
                        self.aqea_cache[normalized_label] = entry
                
                self.loaded_files.add(json_file)
                logger.debug(f"Datei {json_file.name} geladen. Cache-Größe: {len(self.aqea_cache)}")
            
            except Exception as e:
                logger.error(f"Fehler beim Laden von {json_file}: {e}")
        
        logger.info(f"Insgesamt {len(self.aqea_cache)} einzigartige AQEA-Einträge geladen.")
    
    def _normalize_word(self, word: str) -> str:
        """Normalisiert ein Wort für den Vergleich (Kleinbuchstaben, ohne Sonderzeichen)."""
        # Entferne alle Sonderzeichen außer Buchstaben und Zahlen
        normalized = re.sub(r'[^\w\s]', '', word.lower())
        return normalized.strip()
    
    async def find_aqea_for_word(self, word: str) -> Optional[Dict[str, Any]]:
        """Sucht die AQEA-Adresse für ein einzelnes Wort."""
        normalized_word = self._normalize_word(word)
        
        # Prüfe zuerst den Cache
        if normalized_word in self.aqea_cache:
            return self.aqea_cache[normalized_word]
        
        # Wenn nicht im Cache, durchsuche alle JSON-Dateien
        if not self.loaded_files:
            await self.load_json_files()
            
            # Erneut im Cache prüfen
            if normalized_word in self.aqea_cache:
                return self.aqea_cache[normalized_word]
        
        logger.debug(f"Kein AQEA-Eintrag für '{word}' gefunden.")
        return None
    
    async def convert_sentence(self, sentence: str) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
        """Konvertiert einen Satz, indem jedes Wort in ein AQEA-Format umgewandelt wird."""
        if not sentence.strip():
            return []
        
        # Stelle sicher, dass die JSON-Dateien geladen sind
        if not self.loaded_files:
            await self.load_json_files()
        
        # Teile den Satz in Wörter
        words = re.findall(r'\b\w+\b', sentence)
        
        result = []
        for word in words:
            aqea_entry = await self.find_aqea_for_word(word)
            result.append((word, aqea_entry))
        
        return result
    
    def format_result(self, converted_sentence: List[Tuple[str, Optional[Dict[str, Any]]]]) -> str:
        """Formatiert das Ergebnis der Satzkonvertierung als lesbaren Text."""
        if not converted_sentence:
            return "Kein Ergebnis."
        
        output = []
        for word, aqea_entry in converted_sentence:
            if aqea_entry:
                output.append(f"{word} [{aqea_entry['address']}]")
            else:
                output.append(f"{word} [???]")
        
        return " ".join(output)

async def main_async():
    """Hauptfunktion für den interaktiven Modus."""
    print("="*60)
    print("🧠 AQEA Satz-Konverter 🧠")
    print("="*60)
    print("Mit diesem Tool kannst du ganze Sätze eingeben.")
    print("Jedes Wort wird in den AQEA-JSON-Dateien nachgeschlagen.")
    print("Gib 'exit' oder 'quit' ein, um das Programm zu beenden.")
    print("="*60)
    
    # Standardmäßiges JSON-Verzeichnis
    json_dir = "extracted_data/dump/aqea"
    if not os.path.exists(json_dir):
        print(f"\n⚠️ Standardverzeichnis {json_dir} nicht gefunden.")
        print("Bitte gib den Pfad zum Verzeichnis mit den AQEA-JSON-Dateien ein:")
        user_dir = input("> ").strip()
        if user_dir and os.path.exists(user_dir):
            json_dir = user_dir
        else:
            print(f"❌ Verzeichnis {user_dir} existiert nicht oder ist leer.")
            print("Verwende das Standardverzeichnis. Es könnten Fehler auftreten.")
    
    # Erstelle den Konverter
    converter = AQEASentenceConverter(json_dir)
    
    # Lade die JSON-Dateien vorab
    print("\nLade AQEA-Daten... (Dies kann je nach Datenmenge einige Zeit dauern)")
    await converter.load_json_files()
    print(f"✅ {len(converter.aqea_cache)} AQEA-Einträge geladen und bereit.")
    
    # Hauptschleife
    while True:
        print("\nGib einen Satz ein (oder 'exit' zum Beenden):")
        sentence = input("> ").strip()
        
        if sentence.lower() in ['exit', 'quit', 'ende', 'beenden']:
            print("Auf Wiedersehen! 👋")
            break
        
        if not sentence:
            print("⚠️ Bitte gib einen Satz ein.")
            continue
        
        print("\nAnalysiere Satz...")
        converted = await converter.convert_sentence(sentence)
        
        # Zeige die Ergebnisse an
        print("\n📝 Original: " + sentence)
        print("🧠 AQEA-Kodiert: " + converter.format_result(converted))
        
        # Detaillierte Ausgabe
        print("\n📊 Detaillierte Analyse:")
        for word, aqea_entry in converted:
            if aqea_entry:
                print(f"  • {word}: {aqea_entry['address']} - {aqea_entry.get('description', 'Keine Beschreibung')}")
            else:
                print(f"  • {word}: Nicht gefunden in der AQEA-Datenbank")

def main():
    """Wrapper für die asynchrone Hauptfunktion."""
    asyncio.run(main_async())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer beendet.")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")
        print(f"❌ Ein unerwarteter Fehler ist aufgetreten: {e}") 
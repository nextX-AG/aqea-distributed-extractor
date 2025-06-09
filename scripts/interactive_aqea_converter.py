#!/usr/bin/env python3
"""
Interaktiver AQEA-Konverter

Dieses Skript ermöglicht die direkte Eingabe von Wörtern oder Sätzen in der Konsole,
die dann in AQEA-Adressen konvertiert und angezeigt werden.
"""

import os
import sys
import logging
import json
import asyncio
from pathlib import Path

# Füge das Projekt-Verzeichnis zum Python-Pfad hinzu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import der AQEA-Module
from src.aqea.converter import AQEAConverter
try:
    from src.aqea.ush_converter import USHConverter
    HAS_USH = True
except ImportError:
    HAS_USH = False

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("interactive-aqea")

def setup_converter(language="de", use_ush=False):
    """Erstellt einen passenden AQEA-Konverter"""
    config = {
        'language': language,
        'aqea': {
            'use_legacy_mode': not use_ush,
            'enable_cross_linguistic': use_ush
        }
    }
    
    if use_ush and HAS_USH:
        logger.info(f"Verwende USH-Konverter für {language}")
        return USHConverter(config, language)
    else:
        logger.info(f"Verwende Standard-AQEA-Konverter für {language}")
        return AQEAConverter(config, language)

async def convert_input(text, pos="noun", language="de", use_ush=False):
    """Konvertiert einen eingegebenen Text in eine AQEA-Adresse"""
    # Verwende den kompletten Text als Eingabe
    converter = setup_converter(language, use_ush)
    
    # Erstelle ein einfaches Wörterbuch-ähnliches Objekt
    entry = {
        "word": text,
        "language": language,
        "pos": pos,
        "definitions": ["Eingabe aus der interaktiven Konsole"],
        "ipa": ""
    }
    
    try:
        # Konvertiere den Eintrag - mit await, da die Methode asynchron ist
        aqea_entry = await converter.convert(entry)
        return aqea_entry
    except Exception as e:
        logger.error(f"Fehler bei der Konvertierung: {e}")
        return None

def display_result(aqea_entry, detailed=True):
    """Zeigt das Ergebnis der Konvertierung an"""
    if not aqea_entry:
        print("\n❌ Konvertierung fehlgeschlagen. Siehe Fehlerprotokoll oben.")
        return
    
    print("\n✅ AQEA-Konvertierung erfolgreich:")
    print(f"📍 Adresse: {aqea_entry.address}")
    print(f"🔤 Label: {aqea_entry.label}")
    print(f"📝 Beschreibung: {aqea_entry.description}")
    
    if detailed:
        print("\nMetadaten:")
        for key, value in aqea_entry.meta.items():
            print(f"  {key}: {value}")
    
    print(f"\nDomain-Byte: {aqea_entry.domain} ({get_language_name(aqea_entry.domain)})")
    
    # Zusätzliche Analyse der Adresskomponenten
    if ":" in aqea_entry.address:
        parts = aqea_entry.address.split(":")
        if len(parts) == 4:
            domain, category, subcategory, element = parts
            print(f"\nAdress-Komponenten:")
            print(f"  Domain: {domain} ({get_language_name(domain)})")
            print(f"  Kategorie: {category} ({get_category_name(category)})")
            print(f"  Subkategorie: {subcategory}")
            print(f"  Element-ID: {element}")

def get_language_name(domain_byte):
    """Gibt den Sprachnamen für ein Domain-Byte zurück"""
    languages = {
        "0x20": "Deutsch",
        "0x21": "Englisch",
        "0x22": "Französisch",
        "0x23": "Spanisch",
        "0x24": "Italienisch",
        "0x25": "Portugiesisch",
        "0x26": "Niederländisch",
        "0x27": "Russisch",
        "0x28": "Chinesisch",
        "0x29": "Japanisch",
        "0x2A": "Arabisch"
    }
    return languages.get(domain_byte, "Unbekannt")

def get_category_name(category_byte):
    """Gibt den Kategorienamen für ein Kategorie-Byte zurück"""
    categories = {
        "0x01": "Nomen",
        "0x02": "Verb",
        "0x03": "Adjektiv",
        "0x04": "Adverb",
        "0x05": "Pronomen",
        "0x06": "Präposition",
        "0x07": "Konjunktion",
        "0x08": "Interjektion",
        "0x09": "Artikel",
        "0x0A": "Zahl"
    }
    return categories.get(category_byte, "Spezielle Kategorie")

async def async_main():
    """Asynchrone Hauptfunktion für die interaktive Konsole"""
    print("="*60)
    print("🧠 AQEA Interaktiver Konverter 🧠")
    print("="*60)
    print("Mit diesem Tool kannst du Wörter oder ganze Sätze in AQEA-Adressen konvertieren.")
    print()
    print("Befehle:")
    print("  exit, quit - Programm beenden")
    print("  language:XX - Sprache ändern (de, en, fr, es, ...)")
    print("  pos:XXX - Wortart ändern (noun, verb, adj, ...)")
    print("  ush:on/off - USH-Konverter aktivieren/deaktivieren")
    print("="*60)
    
    language = "de"
    pos = "noun"
    use_ush = False
    
    while True:
        print(f"\nAktuelle Einstellungen: Sprache={language}, Wortart={pos}, USH={'an' if use_ush else 'aus'}")
        text = input("\nGib ein Wort oder Satz ein (oder Kommando): ")
        
        if not text.strip():
            print("⚠️ Bitte gib etwas ein.")
            continue
        
        if text.lower() in ['exit', 'quit', 'ende', 'beenden']:
            print("Auf Wiedersehen! 👋")
            break
        
        elif text.lower().startswith('language:'):
            new_lang = text.split(':', 1)[1].strip()
            if new_lang:
                language = new_lang
                print(f"Sprache auf {language} geändert")
            continue
        
        elif text.lower().startswith('pos:'):
            new_pos = text.split(':', 1)[1].strip()
            if new_pos:
                pos = new_pos
                print(f"Wortart auf {pos} geändert")
            continue
        
        elif text.lower() in ['ush:on', 'ush:an']:
            if HAS_USH:
                use_ush = True
                print("USH-Konverter aktiviert")
            else:
                print("⚠️ USH-Konverter nicht verfügbar. Standard-Konverter wird verwendet.")
            continue
        
        elif text.lower() in ['ush:off', 'ush:aus']:
            use_ush = False
            print("Standard-AQEA-Konverter aktiviert")
            continue
        
        aqea_entry = await convert_input(text, pos, language, use_ush)
        display_result(aqea_entry)

def main():
    """Wrapper für die asynchrone Hauptfunktion"""
    asyncio.run(async_main())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer beendet.")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}")
        print(f"❌ Ein unerwarteter Fehler ist aufgetreten: {e}") 
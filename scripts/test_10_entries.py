#!/usr/bin/env python3
"""
Test Script: 10 Deutsche AQEA Einträge

Erstellt 10 Test-Einträge direkt in der SQLite-Datenbank
ohne die Wiktionary-API zu verwenden.
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path for imports  
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from database.sqlite import SQLiteDatabase
from aqea.schema import AQEAEntry
from aqea.converter import AQEAConverter
from utils.config import Config

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m' 
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color):
    print(f"{color}{text}{Colors.ENDC}")

def print_success(text):
    print_colored(f"✅ {text}", Colors.OKGREEN)

def print_error(text):
    print_colored(f"❌ {text}", Colors.FAIL)

def print_header(text):
    print_colored(f"\n🚀 {text}", Colors.HEADER + Colors.BOLD)

# Test data - 10 deutsche Wörter
TEST_WORDS = [
    {
        "word": "Wasser",
        "pos": "noun", 
        "definitions": ["H₂O", "Flüssigkeit zum Trinken"],
        "ipa": "ˈvasɐ"
    },
    {
        "word": "Haus",
        "pos": "noun",
        "definitions": ["Gebäude zum Wohnen", "Zuhause"],
        "ipa": "haʊ̯s"
    },
    {
        "word": "gehen", 
        "pos": "verb",
        "definitions": ["sich zu Fuß fortbewegen", "verlassen"],
        "ipa": "ˈɡeːən"
    },
    {
        "word": "groß",
        "pos": "adjective", 
        "definitions": ["von beträchtlicher Größe", "bedeutend"],
        "ipa": "ɡʁoːs"
    },
    {
        "word": "ich",
        "pos": "pronoun",
        "definitions": ["erste Person Singular"],
        "ipa": "ɪç"
    },
    {
        "word": "Auto",
        "pos": "noun",
        "definitions": ["Kraftfahrzeug", "PKW"], 
        "ipa": "ˈaʊ̯to"
    },
    {
        "word": "schnell",
        "pos": "adverb",
        "definitions": ["mit hoher Geschwindigkeit", "rasch"],
        "ipa": "ʃnɛl"
    },
    {
        "word": "Buch",
        "pos": "noun", 
        "definitions": ["Sammlung von Seiten mit Text", "Literatur"],
        "ipa": "buːx"
    },
    {
        "word": "sprechen",
        "pos": "verb",
        "definitions": ["mit Worten kommunizieren", "reden"],
        "ipa": "ˈʃpʁɛçən"
    },
    {
        "word": "schön",
        "pos": "adjective",
        "definitions": ["ästhetisch ansprechend", "hübsch"], 
        "ipa": "ʃøːn"
    }
]

async def create_aqea_entries():
    """Create AQEA entries from test words."""
    print_header("AQEA Einträge erstellen")
    
    # Load config for SQLite
    config_obj = Config()
    config = config_obj.data
    
    # Force SQLite mode
    config['database'] = {
        'type': 'sqlite',
        'sqlite_path': 'data/aqea_extraction.db'
    }
    
    # Initialize converter
    converter = AQEAConverter(config, language='deu')
    
    entries = []
    
    for i, word_data in enumerate(TEST_WORDS, 1):
        print(f"   {i:2d}. Konvertiere '{word_data['word']}'...")
        
        try:
            # Convert to AQEA entry
            entry = await converter.convert({
                'title': word_data['word'],
                'language': 'deu',
                'pos': word_data['pos'],
                'definitions': word_data['definitions'],
                'ipa': word_data['ipa'],
                'source': 'test_data'
            })
            
            if entry:
                entries.append(entry)
                print(f"      ✅ Adresse: {entry.address}")
            else:
                print(f"      ❌ Konvertierung fehlgeschlagen")
                
        except Exception as e:
            print(f"      ❌ Fehler: {e}")
    
    print_success(f"{len(entries)} AQEA-Einträge erstellt")
    return entries

async def store_entries_in_database(entries):
    """Store entries in SQLite database."""
    print_header("In SQLite-Datenbank speichern")
    
    # Initialize database
    config = {
        'database': {
            'type': 'sqlite',
            'sqlite_path': 'data/aqea_extraction.db'
        }
    }
    
    db = SQLiteDatabase(config['database'])
    
    # Connect to database
    if not await db.connect():
        print_error("Datenbankverbindung fehlgeschlagen")
        return False
    
    print_success("Datenbankverbindung hergestellt")
    
    # Store entries
    try:
        result = await db.store_aqea_entries(entries)
        
        print(f"   📊 Einträge eingefügt: {result['inserted']}")
        print(f"   📊 Erfolgreichkeitsrate: {result['success_rate']:.1%}")
        
        if result['errors']:
            print_error(f"Fehler aufgetreten: {len(result['errors'])}")
            for error in result['errors'][:3]:  # Nur erste 3 Fehler zeigen
                print(f"      - {error}")
        
        await db.disconnect()
        return result['inserted'] > 0
        
    except Exception as e:
        print_error(f"Speicherung fehlgeschlagen: {e}")
        await db.disconnect()
        return False

async def verify_database():
    """Verify entries were stored correctly."""
    print_header("Datenbank verifizieren")
    
    config = {
        'database': {
            'type': 'sqlite', 
            'sqlite_path': 'data/aqea_extraction.db'
        }
    }
    
    db = SQLiteDatabase(config['database'])
    
    if not await db.connect():
        print_error("Datenbankverbindung für Verifizierung fehlgeschlagen")
        return
    
    try:
        # Get statistics
        stats = await db.get_extraction_statistics()
        
        print(f"   📊 Gesamt AQEA-Einträge: {stats.get('total_aqea_entries', 0)}")
        print(f"   📊 Domänen: {len(stats.get('domains', []))}")
        print(f"   📊 Sprachen: {len(stats.get('languages', []))}")
        
        # Get some sample entries
        import sqlite3
        cursor = db.connection.cursor()
        cursor.execute("SELECT address, label, SUBSTR(description, 1, 50) as desc FROM aqea_entries LIMIT 5")
        rows = cursor.fetchall()
        
        if rows:
            print("\n   📋 Beispiel-Einträge:")
            for row in rows:
                print(f"      {row[0]} | {row[1]} | {row[2]}...")
        
    except Exception as e:
        print_error(f"Verifizierung fehlgeschlagen: {e}")
    
    await db.disconnect()

async def main():
    print_colored("🧠 AQEA 10 Deutsche Test-Einträge", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 50, Colors.HEADER)
    
    # Step 1: Create AQEA entries
    entries = await create_aqea_entries()
    
    if not entries:
        print_error("Keine AQEA-Einträge erstellt")
        return
    
    # Step 2: Store in database
    success = await store_entries_in_database(entries)
    
    if not success:
        print_error("Speicherung in Datenbank fehlgeschlagen")
        return
    
    # Step 3: Verify
    await verify_database()
    
    print_colored("\n🎉 Test erfolgreich abgeschlossen!", Colors.OKGREEN + Colors.BOLD)
    print("📊 SQLite-Datenbank: data/aqea_extraction.db")
    print("🔍 Prüfen: sqlite3 data/aqea_extraction.db \"SELECT COUNT(*) FROM aqea_entries;\"")

if __name__ == '__main__':
    asyncio.run(main()) 
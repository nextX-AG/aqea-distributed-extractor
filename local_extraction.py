#!/usr/bin/env python3
"""
Lokale Extraktion mit Supabase-Integration
Einfacher Test der Extraktion und Speicherung von Wiktionary-Einträgen in Supabase
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from supabase import create_client
from aiohttp import ClientSession

# Lokale Module importieren
from src.utils.config import Config
from src.aqea.schema import AQEAEntry
from src.data_sources.wiktionary import WiktionaryDataSource

# Logging einrichten
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Umgebungsvariablen laden
load_dotenv()

async def extract_and_store():
    """Extrahiere und speichere einige deutsche Wörterbucheinträge"""
    
    logger.info("Starte lokale Extraktion mit Supabase-Integration")
    
    # Konfiguration laden
    config = Config.load("config/default.yml")
    
    # Supabase-Client erstellen
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL oder SUPABASE_KEY nicht gefunden in .env Datei")
        return
    
    logger.info(f"Verbinde mit Supabase: {supabase_url}")
    supabase_client = create_client(supabase_url, supabase_key)
    
    # Erstelle eine HTTP-Session
    async with ClientSession() as session:
        # Wiktionary-Datenquelle erstellen
        data_source = WiktionaryDataSource(config)
        data_source.session = session  # Session setzen
        
        # Einige deutsche Wörter extrahieren
        test_words = ["Wasser", "Computer", "Haus", "Auto", "Baum"]
        
        for word in test_words:
            logger.info(f"Extrahiere Wiktionary-Eintrag für '{word}'")
            try:
                # Wiktionary-Seite extrahieren
                entry_data = await data_source._extract_single_entry("de", word)
                
                if entry_data:
                    # AQEA-Eintrag erstellen
                    aqea_entry = AQEAEntry(
                        address=f"de:wikt:{word.lower()}",
                        label=word,
                        description=entry_data.get('definitions', [""])[0] if entry_data.get('definitions') else f"German word '{word}'",
                        source="de.wiktionary.org",
                        language="de",
                        data=entry_data
                    )
                    
                    # In Supabase speichern
                    logger.info(f"Speichere Eintrag in Supabase: {aqea_entry.label}")
                    
                    # Wandle in Dict um (manuell, falls to_dict Probleme macht)
                    entry_dict = {
                        "address": aqea_entry.address,
                        "label": aqea_entry.label,
                        "description": aqea_entry.description,
                        "source": aqea_entry.source,
                        "language": aqea_entry.language,
                        "data": aqea_entry.data
                    }
                    
                    result = supabase_client.table('aqea_entries').upsert([entry_dict]).execute()
                    
                    if result.data:
                        logger.info(f"✅ Eintrag für '{word}' erfolgreich in Supabase gespeichert")
                    else:
                        logger.error(f"❌ Fehler beim Speichern von '{word}' in Supabase")
                else:
                    logger.warning(f"⚠️ Kein Eintrag gefunden für '{word}'")
            
            except Exception as e:
                logger.error(f"❌ Fehler bei der Extraktion von '{word}': {e}")
                import traceback
                logger.error(traceback.format_exc())
        
    # Statistiken abrufen
    stats = supabase_client.table('aqea_entries').select('*').execute()
    logger.info(f"📊 Gesamtzahl der Einträge in Supabase: {len(stats.data)}")
    
    # Zeige die neuesten Einträge
    if stats.data:
        logger.info("Neueste Einträge in der Datenbank:")
        for i, entry in enumerate(stats.data[:5]):
            logger.info(f"  {i+1}. {entry.get('label')} - {entry.get('description')[:50]}...")

if __name__ == "__main__":
    asyncio.run(extract_and_store()) 
#!/usr/bin/env python
# Debug-Skript für AQEA-Extraktion mit detaillierten Logs

import asyncio
import logging
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Füge das Projekt-Verzeichnis zum Python-Pfad hinzu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import der AQEA-Module
from src.data_sources.wiktionary import WiktionaryDataSource
from src.aqea.converter import AQEAConverter
from src.utils.config import Config

# Konfiguriere detailliertes Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/debug_extraction.log')
    ]
)

logger = logging.getLogger("debug_extraction")

async def debug_extraction():
    """
    Führt eine Extraktion im Debug-Modus aus mit detaillierten Informationen
    zu jedem Schritt des Prozesses.
    """
    # Lade Konfiguration
    config = Config("config/default.yml").data
    logger.debug("Konfiguration geladen: %s", config)
    
    # Stelle sicher, dass Ausgabeverzeichnisse existieren
    Path("extracted_data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Initialisiere Extractor
    language = "de"  # Deutsch als Standard
    wiktionary = WiktionaryDataSource(config)
    logger.info(f"Wiktionary-Extractor für Sprache '{language}' initialisiert")
    
    # Initialisiere Converter ohne Datenbank
    converter = AQEAConverter(config, language, None)
    logger.info("AQEA-Converter initialisiert")
    
    # Extrahiere einen kleinen Bereich (für Debug-Zwecke)
    letter_range = ("A", "B")  # Nur A bis B für schnelles Testen
    logger.info(f"Starte Extraktion für Bereich {letter_range[0]}-{letter_range[1]}")
    
    try:
        # Hole Liste von Seiten
        pages = await wiktionary._get_pages_in_range(language, letter_range[0], letter_range[1])
        logger.info(f"Gefundene Seiten: {len(pages)}")
        
        # Begrenze auf 10 Seiten für Debugging
        pages = pages[:10]
        
        # Akkumuliere extrahierte Daten
        extracted_entries = []
        aqea_entries = []
        
        # Verarbeite jede Seite
        for i, page in enumerate(pages):
            logger.debug(f"Verarbeite Seite {i+1}/{len(pages)}: {page}")
            
            try:
                # Extrahiere Einträge
                entry = await wiktionary._extract_single_entry(language, page)
                logger.debug(f"Extrahierter Eintrag für {page}: {entry}")
                
                if not entry:
                    logger.warning(f"Kein Eintrag gefunden für {page}")
                    continue
                
                # Speichere Roheintrag für Debugging
                extracted_entries.append(entry)
                
                # Konvertiere zu AQEA
                try:
                    logger.debug(f"Konvertiere Eintrag: {entry}")
                    aqea_entry = await converter.convert(entry)
                    
                    if aqea_entry:
                        logger.info(f"✅ AQEA-Adresse generiert: {aqea_entry.address} für {entry.get('word')}")
                        aqea_entries.append(aqea_entry.to_dict())
                    else:
                        logger.warning(f"❌ Keine AQEA-Adresse generiert für {entry.get('word')}")
                except Exception as e:
                    logger.error(f"Fehler bei Konvertierung von {entry.get('word')}: {str(e)}", exc_info=True)
            
            except Exception as e:
                logger.error(f"Fehler bei Extraktion von {page}: {str(e)}", exc_info=True)
        
        # Speichere Ergebnisse in JSON-Dateien
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Speichere Roheinträge
        with open(f"extracted_data/raw_entries_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump(extracted_entries, f, ensure_ascii=False, indent=2)
            logger.info(f"Roheinträge gespeichert: {len(extracted_entries)}")
        
        # Speichere AQEA-Einträge
        with open(f"extracted_data/aqea_entries_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump(aqea_entries, f, ensure_ascii=False, indent=2)
            logger.info(f"AQEA-Einträge gespeichert: {len(aqea_entries)}")
        
        # Analysiere Erfolgsrate
        success_rate = len(aqea_entries) / len(extracted_entries) * 100 if extracted_entries else 0
        logger.info(f"Extraktion abgeschlossen. Erfolgsrate: {success_rate:.2f}%")
        logger.info(f"Extrahierte Einträge: {len(extracted_entries)}")
        logger.info(f"AQEA-Einträge generiert: {len(aqea_entries)}")
        
    except Exception as e:
        logger.error(f"Kritischer Fehler während der Extraktion: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("=== AQEA Debug-Extraktion gestartet ===")
    asyncio.run(debug_extraction())
    logger.info("=== AQEA Debug-Extraktion beendet ===") 
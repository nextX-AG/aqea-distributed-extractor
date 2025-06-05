#!/usr/bin/env python3
"""Test des Wiktionary-API zur Überprüfung der Extraktion"""

import asyncio
import aiohttp
import json
import logging
from urllib.parse import urlencode

logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_wiktionary_api():
    """Teste die Wiktionary-API für das deutsche Wörterbuch."""
    logger.info("Starte Wiktionary API Test")
    
    language = "de"
    base_url = f"https://{language}.wiktionary.org/w/api.php"
    
    # Test 1: Liste von Seiten abrufen (A*)
    async with aiohttp.ClientSession() as session:
        # Abfrage für Seiten, die mit 'A' beginnen
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'allpages',
            'apprefix': 'A',
            'aplimit': 10,  # Nur 10 für Test
        }
        
        query_url = f"{base_url}?{urlencode(params)}"
        logger.info(f"Abfrage: {query_url}")
        
        try:
            async with session.get(query_url) as response:
                if response.status == 200:
                    result = await response.json()
                    pages = result.get('query', {}).get('allpages', [])
                    
                    logger.info(f"Gefundene Seiten: {len(pages)}")
                    for page in pages:
                        logger.info(f"Seite: {page.get('title')}")
                    
                    # Test 2: Inhalt einer Seite abrufen
                    if pages:
                        page_title = pages[0].get('title')
                        await get_page_content(session, base_url, page_title)
                else:
                    logger.error(f"API-Fehler: HTTP {response.status}")
                    logger.error(await response.text())
        except Exception as e:
            logger.error(f"Fehler bei API-Anfrage: {e}")

async def get_page_content(session, base_url, title):
    """Rufe den Inhalt einer bestimmten Seite ab."""
    logger.info(f"Hole Inhalt für '{title}'")
    
    params = {
        'action': 'parse',
        'format': 'json',
        'page': title,
        'prop': 'wikitext'
    }
    
    query_url = f"{base_url}?{urlencode(params)}"
    
    try:
        async with session.get(query_url) as response:
            if response.status == 200:
                result = await response.json()
                wikitext = result.get('parse', {}).get('wikitext', {}).get('*', '')
                
                # Zeige die ersten 500 Zeichen
                logger.info(f"Wikitext für '{title}' (erste 500 Zeichen):")
                logger.info(wikitext[:500] + "..." if len(wikitext) > 500 else wikitext)
                
                # Analysiere Wikitext
                logger.info("Analysiere Wikitext...")
                extract_from_wikitext(title, wikitext)
            else:
                logger.error(f"API-Fehler: HTTP {response.status}")
                logger.error(await response.text())
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Seiteninhalts: {e}")

def extract_from_wikitext(title, wikitext):
    """Extrahiere Informationen aus Wikitext (vereinfachte Version)."""
    # POS-Marker im deutschen Wiktionary
    pos_markers = {
        'Substantiv': 'noun',
        'Verb': 'verb',
        'Adjektiv': 'adjective',
        'Adverb': 'adverb'
    }
    
    # Gefundene Daten
    extracted = {
        'word': title,
        'language': 'de',
        'pos': None,
        'definitions': []
    }
    
    # Extrahiere Wortart
    for marker, pos in pos_markers.items():
        if f"{{{{Wortart|{marker}" in wikitext:
            extracted['pos'] = pos
            logger.info(f"Wortart gefunden: {pos}")
            break
    
    # Extrahiere Definitionen
    definition_lines = []
    in_definition_section = False
    
    for line in wikitext.split('\n'):
        if line.startswith('{{Bedeutungen}}'):
            in_definition_section = True
            continue
        elif in_definition_section and line.startswith('{{'):
            if not line.startswith('{{#'): # Ignoriere Templates
                in_definition_section = False
                continue
        
        if in_definition_section and line.strip().startswith(':'):
            definition = line.strip()[1:].strip()
            definition_lines.append(definition)
    
    extracted['definitions'] = definition_lines
    
    logger.info(f"Extrahierte Daten: {json.dumps(extracted, indent=2, ensure_ascii=False)}")
    
    # In AQEA umwandeln
    if extracted['pos']:
        address = generate_simple_address(extracted)
        logger.info(f"Generierte AQEA-Adresse: {address}")

def generate_simple_address(entry):
    """Generiere eine einfache AQEA-Adresse für den Eintrag."""
    # Einfache Zuordnung (nur für Demo)
    domain = '0x20'  # Deutsch
    
    # Wortart
    pos_to_category = {
        'noun': '01',
        'verb': '02', 
        'adjective': '03',
        'adverb': '04'
    }
    category = pos_to_category.get(entry.get('pos'), '00')
    
    # Erste Definition für Subkategorie
    subcategory = '01'  # Default
    
    # Element ID
    element_id = '01'  # Für Demo immer 01
    
    return f"{domain}:{category}:{subcategory}:{element_id}"

if __name__ == "__main__":
    asyncio.run(test_wiktionary_api()) 
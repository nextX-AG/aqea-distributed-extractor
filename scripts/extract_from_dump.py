#!/usr/bin/env python
"""
Wiktionary Dump Extractor für AQEA

Dieses Skript lädt den kompletten Wiktionary-Dump herunter und extrahiert
AQEA-Einträge offline, ohne die Wiktionary API zu nutzen.
Vorteile:
- Keine API-Beschränkungen
- Höhere Geschwindigkeit
- Vollständigkeit der Daten
- Offline-Fähigkeit
"""

import os
import sys
import logging
import asyncio
import argparse
import bz2
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import json
import multiprocessing
from tqdm import tqdm
import requests
import re
import shutil  # Hinzugefügt für Verzeichnislöschung

# Füge das Projekt-Verzeichnis zum Python-Pfad hinzu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import der AQEA-Module
from src.aqea.converter import AQEAConverter
from src.utils.config import Config

# Konfiguriere Logging
logging.basicConfig(
    level=logging.DEBUG,  # Auf DEBUG geändert für mehr Details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/dump_extraction.log')
    ]
)

logger = logging.getLogger("dump_extractor")

# Wiktionary-Dump-URLs für verschiedene Sprachen
DUMP_URLS = {
    'de': 'https://dumps.wikimedia.org/dewiktionary/latest/dewiktionary-latest-pages-articles.xml.bz2',
    'en': 'https://dumps.wikimedia.org/enwiktionary/latest/enwiktionary-latest-pages-articles.xml.bz2',
    'fr': 'https://dumps.wikimedia.org/frwiktionary/latest/frwiktionary-latest-pages-articles.xml.bz2',
    'es': 'https://dumps.wikimedia.org/eswiktionary/latest/eswiktionary-latest-pages-articles.xml.bz2'
}

class WiktionaryDumpExtractor:
    """Extrahiert AQEA-Einträge aus einem Wiktionary-XML-Dump."""
    
    def __init__(self, language, config, output_dir, batch_size=2000, num_processes=None, debug=False, clean_output=True):
        """
        Initialisiert den Dump-Extractor.
        
        Args:
            language: Sprachcode (de, en, fr, es)
            config: Konfigurationsobjekt
            output_dir: Verzeichnis für die Ausgabedateien
            batch_size: Anzahl der Einträge pro Ausgabedatei
            num_processes: Anzahl paralleler Prozesse (Standard: CPU-Kerne)
            debug: Debug-Modus aktivieren
            clean_output: Vor der Extraktion alte Dateien löschen
        """
        self.language = language
        self.config = config
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.num_processes = num_processes or max(1, multiprocessing.cpu_count() - 1)
        self.debug = debug
        self.clean_output = clean_output
        
        # Erstelle Ausgabeverzeichnisse
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "raw").mkdir(exist_ok=True)
        (self.output_dir / "aqea").mkdir(exist_ok=True)
        
        # Lösche alte Dateien, wenn gewünscht
        if self.clean_output:
            self._clean_output_directories()
        
        # Debug-Verzeichnis
        if self.debug:
            (self.output_dir / "debug").mkdir(exist_ok=True)
        
        # Statistiken
        self.stats = {
            'total_pages': 0,
            'processed_pages': 0,
            'extracted_entries': 0,
            'aqea_entries': 0,
            'started_at': datetime.now(),
            'processing_rate': 0,
            'skipped_pages': 0
        }
        
        # AQEA Converter
        self.converter = AQEAConverter(self.config.data, self.language, None)
        
        logger.info(f"Initialisiert für Sprache '{language}' mit {self.num_processes} Prozessen")
        logger.info(f"Ausgabeverzeichnis: {self.output_dir}")
        logger.info(f"Batchgröße: {self.batch_size} Einträge pro Datei")
        
        # Debug-Counter für Fehlgeschlagene Extraktionen
        self.debug_counter = 0
        self.sample_pages = []
    
    def _clean_output_directories(self):
        """Löscht alle vorhandenen Dateien in den Ausgabeverzeichnissen."""
        aqea_dir = self.output_dir / "aqea"
        raw_dir = self.output_dir / "raw"
        
        # Lösche AQEA-Dateien
        if aqea_dir.exists():
            logger.info(f"Lösche bestehende Dateien in {aqea_dir}")
            file_count = 0
            for file in aqea_dir.glob("*.json"):
                file.unlink()
                file_count += 1
            logger.info(f"✅ {file_count} AQEA-Dateien gelöscht")
        
        # Lösche Raw-Dateien
        if raw_dir.exists():
            logger.info(f"Lösche bestehende Dateien in {raw_dir}")
            file_count = 0
            for file in raw_dir.glob("*.json"):
                file.unlink()
                file_count += 1
            logger.info(f"✅ {file_count} Raw-Dateien gelöscht")
    
    def download_dump(self, force=False):
        """
        Lädt den Wiktionary-Dump herunter, falls er nicht vorhanden ist.
        
        Args:
            force: Wenn True, wird der Dump auch dann heruntergeladen, 
                  wenn er bereits existiert
        
        Returns:
            Path zum heruntergeladenen Dump-File
        """
        if self.language not in DUMP_URLS:
            raise ValueError(f"Kein Dump-URL für Sprache '{self.language}' konfiguriert")
        
        url = DUMP_URLS[self.language]
        filename = url.split('/')[-1]
        dump_path = Path('data') / 'dumps' / filename
        
        # Erstelle Verzeichnis für Dumps
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Überprüfe, ob Dump bereits existiert
        if dump_path.exists() and not force:
            logger.info(f"Dump-Datei existiert bereits: {dump_path}")
            return dump_path
        
        # Datei herunterladen
        logger.info(f"Starte Download von {url}")
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(dump_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, 
                     desc=f"Downloading {filename}") as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        logger.info(f"Download abgeschlossen: {dump_path}")
        return dump_path
    
    def _parse_wikitext(self, title, text):
        """
        Parst den Wikitext eines Eintrags.
        
        Args:
            title: Titel des Eintrags
            text: Wikitext-Inhalt
            
        Returns:
            Dictionary mit extrahierten Informationen oder None,
            wenn der Eintrag nicht relevant ist
        """
        if text is None:
            return None
            
        # Debug: Sammle einige Beispielseiten
        if self.debug and len(self.sample_pages) < 5 and '==' in text and 'Deutsch' in text:
            self.sample_pages.append((title, text))
        
        # Überprüfe, ob es ein deutscher Eintrag ist (nicht zu streng)
        if self.language == 'de':
            # Suche nach Deutsch-Abschnitt oder {{Sprache|Deutsch}}
            if not ('{{Sprache|Deutsch}}' in text or 
                    re.search(r'==\s*[^=]*?\(?\s*\{\{Sprache\|Deutsch\}\}\s*\)?', text) or
                    re.search(r'==\s*Deutsch\s*==', text) or
                    re.search(r'==\s*[^=]+\s*\(Deutsch\)\s*==', text)):
                return None
            
            # Debug-Ausgabe für deutsche Einträge
            if self.debug and self.debug_counter < 20:
                logger.debug(f"DEBUG: Deutscher Eintrag gefunden: {title}")
                logger.debug(f"Text-Ausschnitt: {text[:500]}...")
                self.debug_counter += 1
                
            # GEÄNDERT: Deklinierte und konjugierte Formen nicht mehr überspringen
            # Wir wollen alle deutschen Wörter extrahieren, nicht nur Grundformen
            
        elif self.language == 'en':
            # Englische Einträge
            if not re.search(r'==\s*English\s*==', text):
                return None
        
        # Grundlegende Informationen
        entry = {
            'word': title,
            'language': self.language,
            'definitions': [],
            'ipa': None,
            'pos': None,
            'examples': []  # Beispiele hinzugefügt
        }
        
        # Extrahiere Wortart (Part of Speech)
        if self.language == 'de':
            # Suche nach {{Wortart|...}} mit verschiedenen Mustern
            pos_patterns = [
                r'\{\{Wortart\|([^|{}]+)',                  # {{Wortart|Substantiv
                r'\{\{Wortart\|([^|{}]+)\|Deutsch\}\}',     # {{Wortart|Substantiv|Deutsch}}
                r'===\s*\{\{Wortart\|([^|{}]+)',            # === {{Wortart|Substantiv
                r'Deutsch\s+([A-Za-zÄÖÜäöüß]+)\s+Übersicht' # Deutsch Substantiv Übersicht
            ]
            
            for pattern in pos_patterns:
                pos_match = re.search(pattern, text)
                if pos_match:
                    german_pos = pos_match.group(1).strip()
                    break
            else:
                # Wenn keine direkte Wortart gefunden wurde, versuchen wir andere Hinweise
                if "{{Deutsch Substantiv Übersicht" in text:
                    german_pos = "Substantiv"
                elif "{{Deutsch Verb Übersicht" in text:
                    german_pos = "Verb"
                elif "{{Deutsch Adjektiv Übersicht" in text:
                    german_pos = "Adjektiv"
                elif "{{Deutsch Adverb Übersicht" in text:
                    german_pos = "Adverb"
                elif "{{Deutsch Deklinierte Form" in text or "{{Wortart|Deklinierte Form" in text:
                    german_pos = "Deklinierte Form"
                elif "{{Deutsch Konjugierte Form" in text or "{{Wortart|Konjugierte Form" in text:
                    german_pos = "Konjugierte Form"
                elif "{{Deutsch Partizip" in text or "{{Wortart|Partizip" in text:
                    german_pos = "Partizip"
                else:
                    german_pos = "Unbekannt"  # Standardwert, wenn nichts gefunden wird
            
            if german_pos:
                # Übersetze deutsche Wortarten ins Englische
                pos_mapping = {
                    'Substantiv': 'noun',
                    'Verb': 'verb',
                    'Adjektiv': 'adjective',
                    'Adverb': 'adverb',
                    'Pronomen': 'pronoun',
                    'Präposition': 'preposition',
                    'Konjunktion': 'conjunction',
                    'Artikel': 'article',
                    'Numerale': 'numeral',
                    'Interjektion': 'interjection',
                    'Redewendung': 'phrase',
                    'Sprichwort': 'proverb',
                    'Abkürzung': 'abbreviation',
                    'Toponym': 'toponym',
                    'Eigenname': 'proper_noun',
                    'Deklinierte Form': 'inflected_noun',
                    'Konjugierte Form': 'inflected_verb',
                    'Partizip': 'participle',
                    'Unbekannt': 'unknown'
                }
                entry['pos'] = pos_mapping.get(german_pos, 'unknown')
                
                # HINZUGEFÜGT: Wenn es eine Deklinierte oder Konjugierte Form ist, 
                # setzen wir die Grundform als Metadaten
                if german_pos in ['Deklinierte Form', 'Konjugierte Form', 'Partizip']:
                    grundform_match = re.search(r'\[\[([^\]]+)\]\]', text)
                    if grundform_match:
                        entry['base_form'] = grundform_match.group(1).strip()
                
                # Debug-Ausgabe
                if self.debug and entry['pos'] != 'unknown':
                    logger.debug(f"DEBUG: Wortart gefunden für {title}: {german_pos} -> {entry['pos']}")
        
        # Extrahiere IPA-Aussprache
        ipa_match = None
        if self.language == 'de':
            # Verschiedene Muster für die IPA-Aussprache im deutschen Wiktionary
            ipa_patterns = [
                r'\{\{Lautschrift\}\}\s*\[\[([^\]]+)\]\]',                # {{Lautschrift}} [[ˈvaːsɐ]]
                r'\{\{IPA\}\}\s*\{\{Lautschrift\|([^}]+)',                # {{IPA}} {{Lautschrift|ˈvaːsɐ}}
                r'\{\{IPA\}\}\s*\[\[([^\]]+)\]\]',                        # {{IPA}} [[ˈvaːsɐ]]
                r':{{IPA}}.*?{{Lautschrift\|([^}]+)}}',                   # :{{IPA}}...{{Lautschrift|ˈvaːsɐ}}
                r'{{Lautschrift\|([^}]+)}}',                              # {{Lautschrift|ˈvaːsɐ}}
                r':\[\[IPA\]\]: \[\[([^\]]+)\]\]'                         # :[[IPA]]: [[ˈvaːsɐ]]
            ]
            
            for pattern in ipa_patterns:
                ipa_match = re.search(pattern, text)
                if ipa_match:
                    break
        
        if ipa_match:
            entry['ipa'] = ipa_match.group(1).strip()
            
            # Debug-Ausgabe
            if self.debug:
                logger.debug(f"DEBUG: IPA gefunden für {title}: {entry['ipa']}")
        
        # Extrahiere Definitionen - verschiedene Methoden
        definitions = []
        
        if self.language == 'de':
            # Methode 1: Bereich zwischen {{Bedeutungen}} und dem nächsten Abschnitt
            bedeutungen_section = False
            for line in text.split('\n'):
                if '{{Bedeutungen}}' in line:
                    bedeutungen_section = True
                    continue
                # Prüfe auf Ende des Bedeutungs-Abschnitts (neuer Abschnitt oder neue Vorlage)
                elif bedeutungen_section and (
                    line.strip().startswith('====') or 
                    line.strip().startswith('===') or
                    (line.strip().startswith('{{') and not line.strip().startswith('{{#'))):
                    bedeutungen_section = False
                    continue
                
                if bedeutungen_section and line.strip().startswith(':'):
                    # Entferne führendes : und Leerzeichen
                    definition_line = line.strip()[1:].strip()
                    
                    # Bereinige Wiki-Markup
                    definition = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', definition_line)
                    definition = re.sub(r'\{\{[^}]+\}\}', '', definition)
                    definition = re.sub(r'<[^>]+>', '', definition)
                    definition = re.sub(r'\s+', ' ', definition).strip()
                    
                    # Entferne Referenzen wie <ref>...</ref>
                    definition = re.sub(r'<ref>.*?</ref>', '', definition)
                    definition = re.sub(r'<ref .*?</ref>', '', definition)
                    definition = re.sub(r'<ref .*?/>', '', definition)
                    
                    if definition:
                        definitions.append(definition)
                        
                        # Debug-Ausgabe
                        if self.debug and len(definitions) == 1:
                            logger.debug(f"DEBUG: Definition gefunden für {title}: {definition}")
            
            # Methode 2: Direkte Suche nach nummerierten Definitionen mit einem regulären Ausdruck
            if not definitions:
                # Suche nach Definitionen im Format [1] Text oder :[1] Text
                bedeutungen_pattern = r'(?:\:)?\[\d+\]\s*([^\n\[\]]+)'
                for match in re.finditer(bedeutungen_pattern, text):
                    definition = match.group(1).strip()
                    
                    # Bereinige Wiki-Markup wie oben
                    definition = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', definition)
                    definition = re.sub(r'\{\{[^}]+\}\}', '', definition)
                    definition = re.sub(r'<[^>]+>', '', definition)
                    definition = re.sub(r'\s+', ' ', definition).strip()
                    
                    if definition:
                        definitions.append(definition)
                        
                        # Debug-Ausgabe
                        if self.debug and len(definitions) == 1:
                            logger.debug(f"DEBUG: Definition (Methode 2) gefunden für {title}: {definition}")
            
            # Methode 3: Nach typischen Definition-Markierungen suchen, die nicht unbedingt mit {{Bedeutungen}} gekennzeichnet sind
            if not definitions:
                definition_patterns = [
                    r':\s*\[\d+\]\s*([^\n\[\]]+)',         # : [1] Definition
                    r':\[\d+\]\s*([^\n\[\]]+)',           # :[1] Definition
                    r'\[\d+\]\s*([^\n\[\]]+)',            # [1] Definition (ohne :)
                    r'{{Bedeutung\|([^}]+)}}',            # {{Bedeutung|Definition}}
                    r'Definition:\s*([^\n]+)',            # Definition: Text
                    r'Bedeutung:\s*([^\n]+)'              # Bedeutung: Text
                ]
                
                for pattern in definition_patterns:
                    for match in re.finditer(pattern, text):
                        definition = match.group(1).strip()
                        
                        # Bereinige Wiki-Markup
                        definition = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', definition)
                        definition = re.sub(r'\{\{[^}]+\}\}', '', definition)
                        definition = re.sub(r'<[^>]+>', '', definition)
                        definition = re.sub(r'\s+', ' ', definition).strip()
                        
                        if definition and definition not in definitions:
                            definitions.append(definition)
                            
                            # Debug-Ausgabe
                            if self.debug and len(definitions) == 1:
                                logger.debug(f"DEBUG: Definition (Methode 3) gefunden für {title}: {definition}")
            
            # Extrahiere Beispiele
            examples = []
            beispiele_section = False
            for line in text.split('\n'):
                if '{{Beispiele}}' in line:
                    beispiele_section = True
                    continue
                elif beispiele_section and (
                    line.strip().startswith('====') or 
                    line.strip().startswith('===') or
                    (line.strip().startswith('{{') and not line.strip().startswith('{{#'))):
                    beispiele_section = False
                    continue
                
                if beispiele_section and line.strip().startswith(':'):
                    # Entferne führendes : und Leerzeichen
                    example_line = line.strip()[1:].strip()
                    
                    # Bereinige Wiki-Markup
                    example = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', example_line)
                    example = re.sub(r'\{\{[^}]+\}\}', '', example)
                    example = re.sub(r'<[^>]+>', '', example)
                    example = re.sub(r'\s+', ' ', example).strip()
                    
                    # Entferne Referenzen
                    example = re.sub(r'<ref>.*?</ref>', '', example)
                    example = re.sub(r'<ref .*?</ref>', '', example)
                    example = re.sub(r'<ref .*?/>', '', example)
                    
                    if example:
                        examples.append(example)
                        
                        # Debug-Ausgabe
                        if self.debug and len(examples) == 1:
                            logger.debug(f"DEBUG: Beispiel gefunden für {title}: {example}")
            
            # Beschränke auf die ersten 3 Beispiele
            entry['examples'] = examples[:3]
        
        # Beschränke auf die ersten 5 Definitionen
        entry['definitions'] = definitions[:5]
        
        # GEÄNDERT: Weniger strenge Validierung - wir akzeptieren mehr Einträge
        # Für deklinierte Formen ist keine Definition nötig
        # Für alle anderen Einträge reicht es, wenn wir die Wortart kennen
        if not entry['definitions'] and entry['pos'] not in ['inflected_noun', 'inflected_verb', 'participle']:
            # Wenn es keine Definitionen gibt und es keine flektierte Form ist, 
            # prüfen wir noch auf andere Metadaten
            has_metadata = entry.get('ipa') is not None or entry.get('examples')
            
            # Wenn es keine ausreichenden Daten gibt, überspringe den Eintrag
            if not has_metadata and entry['pos'] == 'unknown':
                if self.debug and self.debug_counter % 100 == 0:
                    logger.debug(f"DEBUG: Unvollständiger Eintrag übersprungen: {title} - keine Wortart, keine Definitionen")
                return None
        
        # Wenn wir hier sind, haben wir einen gültigen Eintrag
        if self.debug:
            logger.debug(f"DEBUG: ✅ Gültiger Eintrag extrahiert: {title}, POS: {entry['pos']}, "
                        f"Def. count: {len(entry['definitions'])}, Examples: {len(entry['examples'])}")
        
        return entry
    
    def _process_chunk(self, pages):
        """
        Verarbeitet einen Chunk von Seiten.
        
        Args:
            pages: Liste von (title, text) Tupeln
            
        Returns:
            Tuple mit extrahierten Einträgen und AQEA-Einträgen
        """
        extracted_entries = []
        aqea_entries = []
        
        for title, text in pages:
            # Parse den Wikitext
            entry = self._parse_wikitext(title, text)
            if entry:
                extracted_entries.append(entry)
                
                # Konvertiere zu AQEA
                try:
                    # Da convert() eine async-Methode ist, müssen wir hier synchron arbeiten
                    event_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(event_loop)
                    aqea_entry = event_loop.run_until_complete(self.converter.convert(entry))
                    event_loop.close()
                    
                    if aqea_entry:
                        # Füge zusätzliche Informationen zum AQEA-Eintrag hinzu, falls vorhanden
                        aqea_dict = aqea_entry.to_dict()
                        
                        # Füge Beispiele hinzu, falls vorhanden
                        if entry.get('examples') and len(entry['examples']) > 0:
                            if 'meta' not in aqea_dict:
                                aqea_dict['meta'] = {}
                            aqea_dict['meta']['examples'] = entry['examples']
                        
                        aqea_entries.append(aqea_dict)
                        
                except Exception as e:
                    if self.debug:
                        logger.error(f"Fehler bei Konvertierung von {entry.get('word')}: {e}")
        
        return extracted_entries, aqea_entries
    
    def process_dump(self, dump_path):
        """
        Verarbeitet den XML-Dump und extrahiert Einträge.
        
        Args:
            dump_path: Pfad zur Dump-Datei
            
        Returns:
            Statistiken über die Extraktion
        """
        logger.info(f"Starte Verarbeitung von: {dump_path}")
        
        # Wähle den richtigen Decompressor basierend auf der Dateiendung
        if str(dump_path).endswith('.bz2'):
            open_func = bz2.open
        elif str(dump_path).endswith('.gz'):
            open_func = gzip.open
        else:
            open_func = open
        
        # Verarbeitungsstatistiken
        start_time = datetime.now()
        total_extracted = 0
        total_aqea = 0
        
        # Multiprocessing-Pool für parallele Verarbeitung
        pool = multiprocessing.Pool(processes=self.num_processes)
        
        # Batches für parallele Verarbeitung und Dateispeicherung
        current_chunk = []
        current_raw_batch = []
        current_aqea_batch = []
        batch_count = 0
        page_count = 0
        
        # Tracking für extrahierte/AQEA Einträge pro Batch
        last_extracted_count = 0
        last_aqea_count = 0
        
        # Für die Fortschrittsanzeige
        progress_bar = None
        total_pages_estimate = 0
        
        # Zuerst schätzen wir die Gesamtzahl der Seiten ab
        try:
            # Dateigröße ermitteln und Seiten schätzen
            file_size = os.path.getsize(dump_path)
            # Schätzung basierend auf typischen Werten (ca. 1.3M Seiten für 1GB bei dewiktionary)
            total_pages_estimate = int(file_size / 1024 / 1024 / 1024 * 1300000)
            logger.info(f"Dump-Größe: {file_size/1024/1024/1024:.2f} GB, geschätzte Seiten: ~{total_pages_estimate}")
            
            # Erstelle eine Fortschrittsanzeige
            progress_bar = tqdm(total=total_pages_estimate, desc="Verarbeite Seiten", 
                               unit="Seiten", dynamic_ncols=True)
        except Exception as e:
            logger.warning(f"Konnte Fortschrittsanzeige nicht initialisieren: {e}")
        
        try:
            # Öffne und parse die Dump-Datei
            with open_func(dump_path, 'rt', encoding='utf-8') as f:
                context = ET.iterparse(f, events=('start', 'end'))
                
                # Flag für aktuelle Seite
                in_page = False
                in_title = False
                in_text = False
                
                # Titel und Text der aktuellen Seite
                title = None
                text = None
                
                # Iteration über XML-Events
                for event, elem in context:
                    tag = elem.tag.split('}')[-1]  # Entferne Namespace
                    
                    if event == 'start':
                        if tag == 'page':
                            in_page = True
                            title = None
                            text = None
                        elif in_page and tag == 'title':
                            in_title = True
                        elif in_page and tag == 'text':
                            in_text = True
                    
                    elif event == 'end':
                        if tag == 'title' and in_title:
                            title = elem.text
                            in_title = False
                        elif tag == 'text' and in_text:
                            text = elem.text
                            in_text = False
                        elif tag == 'page' and in_page:
                            in_page = False
                            page_count += 1
                            
                            # Update Fortschrittsanzeige
                            if progress_bar:
                                progress_bar.update(1)
                            
                            # Debug-Ausgabe bei bestimmten Schwellen
                            if self.debug and page_count % 100000 == 0:
                                logger.debug(f"DEBUG: Verarbeite Seite {page_count}: {title}")
                                if text and len(text) > 100:
                                    logger.debug(f"Textanfang: {text[:100]}...")
                                elif text:
                                    logger.debug(f"Text: {text}")
                                else:
                                    logger.debug("Kein Text vorhanden")
                            
                            # Prüfe auf gültigen Artikel im Hauptnamensraum
                            if title and ':' not in title:
                                current_chunk.append((title, text))
                                
                                # Wenn Chunk voll ist, zur Verarbeitung senden
                                if len(current_chunk) >= 50:  # Kleinere Chunks für bessere Fortschrittsanzeige
                                    # Parallelisierte Verarbeitung
                                    result = pool.apply_async(self._process_chunk, (current_chunk,))
                                    
                                    # Extrahierte Einträge und AQEA-Einträge erhalten
                                    extracted, aqea = result.get()
                                    
                                    # Zu Batches hinzufügen
                                    current_raw_batch.extend(extracted)
                                    current_aqea_batch.extend(aqea)
                                    
                                    # Statistiken aktualisieren
                                    total_extracted += len(extracted)
                                    total_aqea += len(aqea)
                                    
                                    # Chunk zurücksetzen
                                    current_chunk = []
                                    
                                    # Periodische Ausgabe - zeige nur Änderungen an
                                    if page_count % 10000 == 0 or (total_extracted > last_extracted_count) or (total_aqea > last_aqea_count):
                                        elapsed = (datetime.now() - start_time).total_seconds()
                                        rate = page_count / elapsed if elapsed > 0 else 0
                                        extraction_rate = total_extracted / (page_count or 1) * 100
                                        
                                        # Progress-Bar-Beschreibung aktualisieren
                                        if progress_bar:
                                            progress_bar.set_postfix({
                                                "Extrahiert": total_extracted, 
                                                "AQEA": total_aqea,
                                                "Rate": f"{rate:.1f}/s",
                                                "Extr.%": f"{extraction_rate:.2f}%"
                                            })
                                        
                                        # Nur ausgeben, wenn es neue Einträge gibt oder bei bestimmten Intervallen
                                        if page_count % 100000 == 0 or (total_extracted > last_extracted_count + 100) or (total_aqea > last_aqea_count + 100):
                                            logger.info(f"Verarbeitet: {page_count} Seiten, "
                                                       f"Extrahiert: {total_extracted} Einträge, "
                                                       f"AQEA: {total_aqea} Einträge, "
                                                       f"Rate: {rate:.1f} Seiten/Sekunde, "
                                                       f"Extraktionsrate: {extraction_rate:.2f}%")
                                        
                                        # Spezielles Logging für neue Einträge
                                        if total_extracted > last_extracted_count:
                                            new_extracted = total_extracted - last_extracted_count
                                            if new_extracted > 10:  # Nur ausgeben, wenn es mindestens 10 neue Einträge gibt
                                                logger.info(f"✅ Neue Einträge extrahiert: +{new_extracted}")
                                            last_extracted_count = total_extracted
                                        
                                        if total_aqea > last_aqea_count:
                                            new_aqea = total_aqea - last_aqea_count
                                            if new_aqea > 10:  # Nur ausgeben, wenn es mindestens 10 neue AQEA-Einträge gibt
                                                logger.info(f"✅ Neue AQEA-Einträge: +{new_aqea}")
                                            last_aqea_count = total_aqea
                                    
                                    # Speichere Batches, wenn voll oder wenn genügend neue Einträge da sind
                                    if len(current_raw_batch) >= self.batch_size or (len(current_raw_batch) > 0 and page_count % 250000 == 0):
                                        self._save_batch(current_raw_batch, current_aqea_batch, batch_count)
                                        current_raw_batch = []
                                        current_aqea_batch = []
                                        batch_count += 1
                            
                            # Element freigeben, um Speicher zu sparen
                            elem.clear()
                
                # Verarbeite verbleibenden Chunk
                if current_chunk:
                    extracted, aqea = self._process_chunk(current_chunk)
                    current_raw_batch.extend(extracted)
                    current_aqea_batch.extend(aqea)
                    total_extracted += len(extracted)
                    total_aqea += len(aqea)
                
                # Speichere verbleibenden Batch
                if current_raw_batch:
                    self._save_batch(current_raw_batch, current_aqea_batch, batch_count)
                
                # Speichere Debug-Beispiele
                if self.debug and self.sample_pages:
                    debug_file = self.output_dir / "debug" / "sample_pages.json"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        json.dump(self.sample_pages, f, ensure_ascii=False, indent=2)
                    logger.debug(f"Debug-Beispiele gespeichert in {debug_file}")
        
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung: {e}", exc_info=True)
        finally:
            # Progress-Bar schließen
            if progress_bar:
                progress_bar.close()
            
            # Pool schließen
            pool.close()
            pool.join()
        
        # Aktualisiere Statistiken
        self.stats['total_pages'] = page_count
        self.stats['processed_pages'] = page_count
        self.stats['extracted_entries'] = total_extracted
        self.stats['aqea_entries'] = total_aqea
        
        # Berechne Verarbeitungsrate
        elapsed = (datetime.now() - self.stats['started_at']).total_seconds()
        self.stats['processing_rate'] = page_count / elapsed if elapsed > 0 else 0
        
        logger.info(f"Verarbeitung abgeschlossen. Ergebnisse:")
        logger.info(f"  Verarbeitete Seiten: {page_count}")
        logger.info(f"  Extrahierte Einträge: {total_extracted}")
        logger.info(f"  AQEA-Einträge: {total_aqea}")
        logger.info(f"  Extraktionsrate: {(total_extracted / page_count * 100) if page_count else 0:.2f}%")
        logger.info(f"  AQEA-Konvertierungsrate: {(total_aqea / total_extracted * 100) if total_extracted else 0:.2f}%")
        logger.info(f"  Verarbeitungsrate: {self.stats['processing_rate']:.1f} Seiten/Sekunde")
        logger.info(f"  Gesamtdauer: {datetime.now() - self.stats['started_at']}")
        
        return self.stats
    
    def _save_batch(self, raw_entries, aqea_entries, batch_num):
        """
        Speichert einen Batch von Einträgen als JSON-Dateien.
        
        Args:
            raw_entries: Liste von extrahierten Einträgen
            aqea_entries: Liste von AQEA-Einträgen
            batch_num: Batch-Nummer für die Dateinamen
        """
        if not raw_entries:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Speichere Roheinträge
        raw_path = self.output_dir / "raw" / f"entries_batch_{batch_num}_{timestamp}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_entries, f, ensure_ascii=False, indent=2)
        
        # Speichere AQEA-Einträge
        if aqea_entries:
            aqea_path = self.output_dir / "aqea" / f"aqea_entries_batch_{batch_num}_{timestamp}.json"
            with open(aqea_path, "w", encoding="utf-8") as f:
                json.dump(aqea_entries, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Batch {batch_num} gespeichert: {len(raw_entries)} Roheinträge, "
                    f"{len(aqea_entries)} AQEA-Einträge")


def main():
    """Hauptfunktion für die Kommandozeilen-Ausführung."""
    parser = argparse.ArgumentParser(description="Extrahiere AQEA-Einträge aus Wiktionary-Dumps")
    
    parser.add_argument("--language", "-l", default="de", choices=DUMP_URLS.keys(),
                       help="Sprache des Wiktionary-Dumps (de, en, fr, es)")
    parser.add_argument("--output-dir", "-o", default="extracted_data/dump",
                       help="Verzeichnis für die Ausgabedateien")
    parser.add_argument("--batch-size", "-b", type=int, default=2000,
                       help="Anzahl der Einträge pro Ausgabedatei")
    parser.add_argument("--processes", "-p", type=int, default=None,
                       help="Anzahl paralleler Prozesse (Standard: CPU-Kerne)")
    parser.add_argument("--force-download", "-f", action="store_true",
                       help="Dump auch dann herunterladen, wenn er bereits existiert")
    parser.add_argument("--debug", "-d", action="store_true",
                       help="Debug-Modus aktivieren mit detaillierten Ausgaben")
    parser.add_argument("--limit", type=int, default=0,
                       help="Maximale Anzahl zu verarbeitender Seiten (0 = keine Begrenzung)")
    parser.add_argument("--no-clean", action="store_true",
                       help="Bestehende Dateien in den Ausgabeverzeichnissen nicht löschen")
    
    args = parser.parse_args()
    
    # Lade Konfiguration
    config = Config.load("config/default.yml")
    
    # Erstelle und starte Extractor
    extractor = WiktionaryDumpExtractor(
        language=args.language,
        config=config,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        num_processes=args.processes,
        debug=args.debug,
        clean_output=not args.no_clean
    )
    
    try:
        # Dump herunterladen
        dump_path = extractor.download_dump(force=args.force_download)
        
        # Dump verarbeiten
        stats = extractor.process_dump(dump_path)
        
        # Statistiken ausgeben
        print("\n=== Extraktions-Statistiken ===")
        print(f"Sprache: {args.language}")
        print(f"Verarbeitete Seiten: {stats['processed_pages']}")
        print(f"Extrahierte Einträge: {stats['extracted_entries']}")
        print(f"AQEA-Einträge: {stats['aqea_entries']}")
        print(f"Extraktionsrate: {(stats['extracted_entries'] / stats['processed_pages'] * 100) if stats['processed_pages'] else 0:.2f}%")
        print(f"AQEA-Konvertierungsrate: {(stats['aqea_entries'] / stats['extracted_entries'] * 100) if stats['extracted_entries'] else 0:.2f}%")
        print(f"Verarbeitungsrate: {stats['processing_rate']:.1f} Seiten/Sekunde")
        print(f"Gesamtdauer: {datetime.now() - stats['started_at']}")
        
    except Exception as e:
        logger.error(f"Fehler: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Enhanced JSON to SQLite Importer with Category-Refinement

Dieses Skript importiert AQEA-Einträge aus JSON-Dateien mit verbesserter
Kategorisierung basierend auf linguistischen Merkmalen. Es nutzt 6 neue
QQ-Codes anstatt des 0xFF-Catch-All-Ansatzes.
"""

import os
import sys
import json
import logging
import sqlite3
import argparse
import glob
import re
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from collections import defaultdict, Counter

# Füge das Projekt-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/enhanced_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("enhanced-importer")

class EnhancedAQEAImporter:
    """
    Enhanced AQEA Importer mit linguistischer Re-Kategorisierung.
    
    Neue QQ-Codes:
    - 0x10: Grundformen (Singular, Infinitiv)
    - 0x11: Komparativ/Superlativ-Formen
    - 0x12: Komposita und Wortbildungen
    - 0x13: Idiome und Mehrwortausdrücke
    - 0x14: Fachterminologie und Fremdwörter
    - 0x15: Flektierte Formen (Plural, Konjugationen)
    - 0xFF: Miscellaneous (deutlich reduziert)
    """
    
    ENHANCED_QQ_CODES = {
        0x10: "base_forms",          # Grundformen
        0x11: "comparative_forms",   # Steigerungsformen
        0x12: "compounds",           # Komposita
        0x13: "idioms_phrases",      # Idiome und Phrasen
        0x14: "technical_terms",     # Fachterminologie
        0x15: "inflected_forms",     # Flektierte Formen
        0xFF: "miscellaneous"        # Catch-All (reduziert)
    }
    
    # Unterstützte Sprachen
    SUPPORTED_LANGUAGES = {
        'deu': {'name': 'Deutsch', 'family': 'germanic', 'domain_byte': 0xA0},
        'eng': {'name': 'English', 'family': 'germanic', 'domain_byte': 0xA1},
        'fra': {'name': 'Français', 'family': 'romance', 'domain_byte': 0xB0},
        'spa': {'name': 'Español', 'family': 'romance', 'domain_byte': 0xB1},
    }
    
    # Domain-Byte zu ISO-Codes Mapping (umgekehrt)
    DOMAIN_TO_LANGUAGE = {
        '0xA0': 'deu',
        '0xA1': 'eng',
        '0xB0': 'fra',
        '0xB1': 'spa'
    }
    
    def __init__(self, database_path="data/aqea_extraction.db"):
        self.database_path = database_path
        self.connection = None
        self.stats = {
            'total_processed': 0,
            'category_distribution': defaultdict(int),
            'address_changes': 0,
            'original_addresses': set(),
            'enhanced_addresses': set(),
            'language_distribution': defaultdict(int)
        }
        
        # Compile regex patterns für bessere Performance
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Kompiliert alle Regex-Patterns für bessere Performance nach Sprache."""
        # Gemeinsame Patterns für alle Sprachen
        self.common_patterns = {
            'technical': [
                re.compile(r'.*[A-Z]{2,}.*'),  # Abkürzungen mit Großbuchstaben
                re.compile(r'.*[0-9].*'),      # Zahlen enthalten
            ]
        }
        
        # Deutsch
        self.de_patterns = {
            'compound': [
                re.compile(r'.{10,}'),  # Länge > 10 Zeichen
                re.compile(r'.*[A-Z][a-z]+[A-Z][a-z]+.*'),  # CamelCase-ähnlich
                re.compile(r'.*(straße|haus|werk|dienst|wasser|stoff|system).*', re.IGNORECASE),
                re.compile(r'.*[a-z]+[A-Z][a-z]+.*')  # InternalCapitalization
            ],
            'comparative': [
                re.compile(r'.*(er|ere|eres|eren|erem)$'),  # Komparativ
                re.compile(r'.*(ste|stes|sten|stem)$'),     # Superlativ
                re.compile(r'.*(erer|erste|esten)$')        # Erweiterte Formen
            ],
            'idiom': [
                re.compile(r'^sich .*', re.IGNORECASE),     # Reflexive Wendungen
                re.compile(r'.* (auf|mit|für|von|zu) .*', re.IGNORECASE),  # Präpositionale Wendungen
                re.compile(r'(lege artis|per se|ad hoc|de facto)', re.IGNORECASE),  # Lateinisch
                re.compile(r'.* (haben|sein|werden)$', re.IGNORECASE)  # Funktionsverbgefüge
            ],
            'technical': [
                re.compile(r'.*(ologie|ismus|ität|ation|ierung)$'),  # Fachwort-Endungen
                re.compile(r'^(bio|geo|physio|psycho|neuro|cardio).*', re.IGNORECASE),  # Fach-Präfixe
                re.compile(r'.*(synthese|analyse|diagnose|therapie).*', re.IGNORECASE),  # Med/Wiss
            ],
            'inflected': [
                re.compile(r'.*(en|est|et|te|ten|tes)$'),   # Verb-Endungen
                re.compile(r'.*(er|es|em|en)$'),            # Adjektiv-Deklinationen
                re.compile(r'.*(s|es|ens|ern)$'),           # Substantiv-Deklinationen
                re.compile(r'.*(nd|nde|nden|ndes)$')        # Partizipien
            ],
            'base_form': [
                re.compile(r'^[a-zA-ZäöüÄÖÜß]{2,8}$'),     # Einfache, kurze Wörter
                re.compile(r'^(der|die|das|ein|eine) .+', re.IGNORECASE),  # Mit Artikel
                re.compile(r'^[A-ZÄÖÜ][a-zäöüß]{2,}$')     # Eigenname-Pattern
            ]
        }
        
        # Englisch
        self.en_patterns = {
            'compound': [
                re.compile(r'.*-.*-.*'),  # Multi-hyphenated
                re.compile(r'.{12,}'),    # Very long words
                re.compile(r'.*(house|room|work|water|stone|wood|maker).*', re.IGNORECASE),
            ],
            'comparative': [
                re.compile(r'.*(er|est)$'),  # Comparative/superlative
                re.compile(r'^(more|most) .*', re.IGNORECASE),  # Periphrastic
            ],
            'idiom': [
                re.compile(r'.*( on| off| up| down| in| out) .*', re.IGNORECASE),  # Phrasal
                re.compile(r'.* (to|for|with|at|by) .*', re.IGNORECASE),  # Prepositional
                re.compile(r'.*( a | an | the ).*', re.IGNORECASE),  # Articles in phrases
            ],
            'technical': [
                re.compile(r'.*(ology|osis|itis|tion|ment)$'),  # Technical suffixes
                re.compile(r'^(bio|geo|psycho|neuro|cardio|hydro).*', re.IGNORECASE),  # Technical prefixes
            ],
            'inflected': [
                re.compile(r'.*(ing|ed)$'),  # Verb inflections
                re.compile(r'.*(s|es)$'),    # Plural nouns
                re.compile(r'.*(\'s|s\')$'), # Possessive
            ],
            'base_form': [
                re.compile(r'^[a-zA-Z]{2,8}$'),  # Simple short words
                re.compile(r'^(a|an|the) .+', re.IGNORECASE),  # With article
                re.compile(r'^[A-Z][a-z]{2,}$')  # Proper noun pattern
            ]
        }
        
        # Französisch
        self.fr_patterns = {
            'compound': [
                re.compile(r'.*-.*-.*'),  # Multi-hyphenated
                re.compile(r'.{12,}'),    # Very long words
            ],
            'comparative': [
                re.compile(r'^(plus|moins) .*', re.IGNORECASE),  # Comparative
                re.compile(r'^(le plus|le moins) .*', re.IGNORECASE),  # Superlative
            ],
            'idiom': [
                re.compile(r'.* (de|à|en|dans|sur|avec) .*', re.IGNORECASE),  # Prepositional
                re.compile(r'.*( le| la| les| un| une| des ).*', re.IGNORECASE),  # Articles in phrases
            ],
            'technical': [
                re.compile(r'.*(logie|tion|ment|isme|ité)$'),  # Technical suffixes
                re.compile(r'^(bio|géo|psycho|neuro|cardio).*', re.IGNORECASE),  # Technical prefixes
            ],
            'inflected': [
                re.compile(r'.*(é|és|ée|ées)$'),  # Past participle
                re.compile(r'.*(ant|ons|ez|ent|ais|ait|aient)$'),  # Verb conjugations
                re.compile(r'.*(s|x)$'),  # Plural
            ],
            'base_form': [
                re.compile(r'^[a-zA-Zàâçéèêëîïôùûüÿ]{2,8}$'),  # Simple short words
                re.compile(r'^(le|la|les|un|une|des) .+', re.IGNORECASE),  # With article
                re.compile(r'^[A-Z][a-zàâçéèêëîïôùûüÿ]{2,}$')  # Proper noun pattern
            ]
        }
        
        # Spanisch
        self.es_patterns = {
            'compound': [
                re.compile(r'.*-.*-.*'),  # Multi-hyphenated
                re.compile(r'.{12,}'),    # Very long words
            ],
            'comparative': [
                re.compile(r'^(más|menos) .*', re.IGNORECASE),  # Comparative
                re.compile(r'^(el más|la más|lo más) .*', re.IGNORECASE),  # Superlative
            ],
            'idiom': [
                re.compile(r'.* (de|en|con|por|para) .*', re.IGNORECASE),  # Prepositional
                re.compile(r'.*( el| la| los| las| un| una) .*', re.IGNORECASE),  # Articles in phrases
            ],
            'technical': [
                re.compile(r'.*(logía|ción|miento|dad|ismo)$'),  # Technical suffixes
                re.compile(r'^(bio|geo|psico|neuro|cardio).*', re.IGNORECASE),  # Technical prefixes
            ],
            'inflected': [
                re.compile(r'.*(ado|ados|ada|adas|ido|idos|ida|idas)$'),  # Past participle
                re.compile(r'.*(o|as|a|an|amos|áis|aba|abas)$'),  # Verb conjugations
                re.compile(r'.*(s|es)$'),  # Plural
            ],
            'base_form': [
                re.compile(r'^[a-zA-Záéíóúñ]{2,8}$'),  # Simple short words
                re.compile(r'^(el|la|los|las|un|una) .+', re.IGNORECASE),  # With article
                re.compile(r'^[A-Z][a-záéíóúñ]{2,}$')  # Proper noun pattern
            ]
        }
        
        # Dictionary mit allen Sprachmustern
        self.language_patterns = {
            'deu': self.de_patterns,
            'eng': self.en_patterns,
            'fra': self.fr_patterns,
            'spa': self.es_patterns
        }
    
    def _detect_language_from_address(self, address):
        """Erkennt die Sprache aus der AQEA-Adresse."""
        try:
            domain = address.split(':')[0]
            return self.DOMAIN_TO_LANGUAGE.get(domain, 'unknown')
        except:
            return 'unknown'
    
    def _detect_language_from_meta(self, meta):
        """Erkennt die Sprache aus den Metadaten."""
        if not meta:
            return 'unknown'
        
        lang = meta.get('language', '')
        
        # ISO 639-1 zu ISO 639-3 konvertieren
        if lang == 'de':
            return 'deu'
        elif lang == 'en':
            return 'eng'
        elif lang == 'fr':
            return 'fra'
        elif lang == 'es':
            return 'spa'
            
        return lang
    
    def is_compound(self, label, language):
        """Erkennt Komposita in verschiedenen Sprachen."""
        # Gemeinsame Kriterien für alle Sprachen
        if ' ' not in label and '-' in label and len(label.split('-')) >= 2:
            return True
            
        # Sehr lange Wörter (sehr wahrscheinlich Komposita)
        if len(label) > 15:
            return True
            
        # Sprachspezifische Muster anwenden
        patterns = self.language_patterns.get(language, {}).get('compound', [])
        for pattern in patterns:
            if pattern.match(label):
                return True
                
        # Für Deutsch: Zusätzliche Spezialbehandlung
        if language == 'deu':
            compound_indicators = 0
            
            # CamelCase-ähnliche Struktur
            if re.match(r'.*[A-Z][a-z]+[A-Z][a-z]+.*', label):
                compound_indicators += 1
                
            # Typische Komposita-Komponenten
            if re.search(r'.*(straße|haus|werk|dienst|stoff|system|bau|raum).*', label, re.IGNORECASE):
                compound_indicators += 1
                
            # Länge als schwacher Indikator
            if len(label) > 10:
                compound_indicators += 1
                
            # Nur als Komposita klassifizieren wenn mehrere Indikatoren zutreffen
            return compound_indicators >= 2
            
        return False
    
    def is_comparative_superlative(self, label, meta, language):
        """Erkennt Steigerungsformen in verschiedenen Sprachen."""
        # POS-Information nutzen wenn verfügbar
        pos = meta.get('pos', '').lower()
        if any(word in pos for word in ['comparative', 'superlative', 'comp', 'sup', 'komparativ', 'superlativ']):
            return True
        
        # Sprachspezifische Muster anwenden
        patterns = self.language_patterns.get(language, {}).get('comparative', [])
        for pattern in patterns:
            if pattern.match(label):
                return True
                
        return False
    
    def is_idiom_or_phrase(self, label, language):
        """Erkennt Idiome und Mehrwortausdrücke in verschiedenen Sprachen."""
        # Mehrere Wörter (einfachster Fall)
        if ' ' in label and len(label.split()) >= 2:
            return True
        
        # Sprachspezifische Muster anwenden
        patterns = self.language_patterns.get(language, {}).get('idiom', [])
        for pattern in patterns:
            if pattern.match(label):
                return True
                
        return False
    
    def is_technical_term(self, label, meta, language):
        """Erkennt Fachterminologie in verschiedenen Sprachen."""
        # Fachbereich in Metadaten
        domain = meta.get('domain', '').lower()
        if any(term in domain for term in ['medical', 'scientific', 'technical', 'biology', 'chemistry', 
                                          'medizin', 'wissenschaft', 'technik', 'biologie', 'chemie']):
            return True
        
        # Sprachunabhängige technische Wörter
        scientific_terms = [
            'dna', 'rna', 'atp', 'laser', 'radar', 'covid', 'quantum', 'algorithm',
            'synthesis', 'analysis', 'diagnostic', 'therapy', 'pathology'
        ]
        
        if label.lower() in scientific_terms:
            return True
        
        # Gemeinsame technische Muster für alle Sprachen
        for pattern in self.common_patterns.get('technical', []):
            if pattern.match(label):
                return True
        
        # Sprachspezifische Muster anwenden
        patterns = self.language_patterns.get(language, {}).get('technical', [])
        for pattern in patterns:
            if pattern.match(label):
                return True
                
        return False
    
    def is_inflected_form(self, label, meta, language):
        """Erkennt flektierte Formen in verschiedenen Sprachen."""
        # POS-Information nutzen
        pos = meta.get('pos', '').lower()
        if any(word in pos for word in ['inflected', 'conjugated', 'declined', 'plural', 
                                       'flektiert', 'konjugiert', 'dekliniert', 'mehrzahl']):
            return True
        
        # Sprachspezifische Muster anwenden
        patterns = self.language_patterns.get(language, {}).get('inflected', [])
        for pattern in patterns:
            if pattern.match(label):
                # Aber nicht bei Komposita (die haben Vorrang)
                if not self.is_compound(label, language):
                    return True
                    
        return False
    
    def is_base_form(self, label, meta, language):
        """Erkennt Grundformen in verschiedenen Sprachen."""
        # POS-Information nutzen
        pos = meta.get('pos', '').lower()
        if any(word in pos for word in ['base', 'lemma', 'infinitive', 'singular', 'nominative', 
                                       'grundform', 'infinitiv', 'einzahl', 'nominativ']):
            return True
        
        # Gemeinsame Liste sehr häufiger Wörter (sprachübergreifend)
        common_intl_words = [
            'water', 'eau', 'wasser', 'agua',
            'house', 'maison', 'haus', 'casa',
            'man', 'homme', 'mann', 'hombre',
            'woman', 'femme', 'frau', 'mujer',
            'time', 'temps', 'zeit', 'tiempo'
        ]
        
        if label.lower() in common_intl_words:
            return True
        
        # Sprachspezifische Muster anwenden
        patterns = self.language_patterns.get(language, {}).get('base_form', [])
        for pattern in patterns:
            if pattern.match(label):
                return True
                    
        return False
    
    def determine_enhanced_category(self, label, meta, language):
        """
        Intelligente Kategorie-Bestimmung basierend auf linguistischen Merkmalen.
        
        Reihenfolge ist wichtig: Spezifischere Kategorien zuerst!
        """
        # 1. Idiome und Phrasen (höchste Priorität)
        if self.is_idiom_or_phrase(label, language):
            return 0x13
        
        # 2. Fachterminologie (vor Komposita prüfen!)
        if self.is_technical_term(label, meta, language):
            return 0x14
        
        # 3. Grundformen (einfache Wörter vor komplexeren prüfen)
        if self.is_base_form(label, meta, language):
            return 0x10
        
        # 4. Komparativ/Superlativ
        if self.is_comparative_superlative(label, meta, language):
            return 0x11
        
        # 5. Flektierte Formen
        if self.is_inflected_form(label, meta, language):
            return 0x15
        
        # 6. Komposita (niedrigere Priorität)
        if self.is_compound(label, language):
            return 0x12
        
        # 7. Fallback zu Miscellaneous
        return 0xFF
    
    def regenerate_aqea_address(self, original_address, new_qq_code):
        """Generiert neue AQEA-Adresse mit verbessertem QQ-Code."""
        try:
            parts = original_address.split(':')
            if len(parts) != 4:
                logger.warning(f"Unexpected address format: {original_address}")
                return original_address
            
            # QQ-Teil ersetzen (Index 1)
            parts[1] = f"{new_qq_code:02X}"
            
            return ':'.join(parts)
        except Exception as e:
            logger.error(f"Error regenerating address {original_address}: {e}")
            return original_address
    
    def process_entry_with_enhanced_categorization(self, entry):
        """Verarbeitet einen JSON-Eintrag mit verbesserter Kategorisierung."""
        try:
            original_address = entry.get('address', '')
            original_label = entry.get('label', '')
            original_meta = entry.get('meta', {})
            
            # Erkenne Sprache aus Adresse und Metadaten
            language_from_address = self._detect_language_from_address(original_address)
            language_from_meta = self._detect_language_from_meta(original_meta)
            
            # Verwende bevorzugt die Metadaten-Sprache, fallback auf Adress-Sprache
            language = language_from_meta if language_from_meta != 'unknown' else language_from_address
            
            # Statistiken für Original-Adresse
            self.stats['original_addresses'].add(original_address)
            self.stats['language_distribution'][language] += 1
            
            # Neue Kategorie bestimmen
            new_qq_code = self.determine_enhanced_category(original_label, original_meta, language)
            
            # Neue Adresse generieren
            new_address = self.regenerate_aqea_address(original_address, new_qq_code)
            
            # Hat sich die Adresse geändert?
            if new_address != original_address:
                self.stats['address_changes'] += 1
            
            # Entry aktualisieren
            enhanced_entry = entry.copy()
            enhanced_entry['address'] = new_address
            enhanced_entry['meta'] = original_meta.copy()
            enhanced_entry['meta']['original_address'] = original_address
            enhanced_entry['meta']['enhanced_category'] = hex(new_qq_code)
            enhanced_entry['meta']['category_name'] = self.ENHANCED_QQ_CODES[new_qq_code]
            enhanced_entry['meta']['detected_language'] = language
            
            # Statistiken aktualisieren
            self.stats['enhanced_addresses'].add(new_address)
            self.stats['category_distribution'][hex(new_qq_code)] += 1
            self.stats['total_processed'] += 1
            
            return enhanced_entry
            
        except Exception as e:
            logger.error(f"Error processing entry {entry}: {e}")
            return entry  # Return original entry on error
    
    def initialize_database(self):
        """Initialisiert die SQLite-Datenbank mit dem korrekten Schema."""
        try:
            # Erstelle Verzeichnis falls nicht vorhanden
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
            
            self.connection = sqlite3.connect(self.database_path)
            cursor = self.connection.cursor()
            
            # AQEA entries Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS aqea_entries (
                    address TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    description TEXT,
                    domain TEXT,
                    meta TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index für bessere Performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON aqea_entries(domain)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_label ON aqea_entries(label)")
            
            self.connection.commit()
            logger.info(f"Database initialized: {self.database_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def insert_batch_to_database(self, enhanced_entries):
        """Fügt einen Batch von enhanced entries in die Datenbank ein."""
        try:
            cursor = self.connection.cursor()
            
            batch_data = []
            for entry in enhanced_entries:
                batch_data.append((
                    entry['address'],
                    entry['label'],
                    entry.get('description', ''),
                    entry.get('domain', ''),
                    json.dumps(entry.get('meta', {}), ensure_ascii=False),
                ))
            
            cursor.executemany("""
                INSERT OR REPLACE INTO aqea_entries 
                (address, label, description, domain, meta)
                VALUES (?, ?, ?, ?, ?)
            """, batch_data)
            
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"Error inserting batch to database: {e}")
            raise
    
    def find_json_files(self, source_dir):
        """Findet alle AQEA JSON-Dateien im angegebenen Verzeichnis."""
        json_pattern = os.path.join(source_dir, "**", "*.json")
        files = glob.glob(json_pattern, recursive=True)
        
        # Filtere auf AQEA-Dateien
        aqea_files = [f for f in files if "aqea" in f.lower()]
        
        if not aqea_files:
            logger.warning(f"No AQEA JSON files found in {source_dir}")
            
            # Diagnose durchführen, um das Problem zu verstehen
            raw_files = [f for f in files if "raw" in f.lower()]
            if raw_files:
                logger.info(f"Found {len(raw_files)} raw JSON files, but no AQEA files.")
                logger.info("Checking raw files for content...")
                
                try:
                    # Öffne eine der Raw-Dateien, um zu sehen, was drin ist
                    with open(raw_files[0], 'r', encoding='utf-8') as f:
                        raw_data = json.load(f)
                        
                    if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
                        sample_entry = raw_data[0]
                        has_definitions = bool(sample_entry.get('definitions', []))
                        has_pos = bool(sample_entry.get('pos'))
                        
                        logger.info(f"Sample raw entry: {sample_entry}")
                        logger.info(f"Has definitions: {has_definitions}, Has POS: {has_pos}")
                        
                        if not has_definitions and not has_pos:
                            logger.error("Raw entries have no definitions or POS information.")
                            logger.error("This is likely why AQEA conversion failed - insufficient data for meaningful conversion.")
                    else:
                        logger.error("Raw files exist but may be empty or malformed.")
                except Exception as e:
                    logger.error(f"Error analyzing raw files: {e}")
        else:
            logger.info(f"Found {len(aqea_files)} AQEA JSON files")
            
        return aqea_files
    
    def import_with_enhanced_categorization(self, source_dir="extracted_data"):
        """Importiert JSON-Dateien mit verbesserter Kategorisierung."""
        logger.info("Starting enhanced AQEA import with category refinement...")
        
        # Datenbank initialisieren
        self.initialize_database()
        
        # JSON-Dateien finden
        json_files = self.find_json_files(source_dir)
        
        if not json_files:
            logger.error("No JSON files found to process")
            return False
        
        # Verarbeitung mit verbessertem Progress Bar
        with tqdm(total=len(json_files), 
                 desc="Processing files", 
                 bar_format="{l_bar}{bar:30}{r_bar}",
                 unit="files") as pbar:
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        entries = json.load(f)
                    
                    if not isinstance(entries, list):
                        logger.warning(f"Unexpected JSON structure in {json_file}")
                        pbar.update(1)
                        continue
                    
                    # Anzahl der Einträge für Status
                    entry_count = len(entries)
                    
                    # Batch-Enhancement
                    enhanced_entries = []
                    for entry in entries:
                        enhanced_entry = self.process_entry_with_enhanced_categorization(entry)
                        enhanced_entries.append(enhanced_entry)
                    
                    # Batch-Insert in DB
                    if enhanced_entries:
                        self.insert_batch_to_database(enhanced_entries)
                    
                    # Progress Bar aktualisieren mit zusätzlichen Infos
                    pbar.set_postfix({
                        "Entries": entry_count,
                        "Addr.Changes": self.stats['address_changes'],
                        "Categories": len(self.stats['category_distribution'])
                    })
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Error processing file {json_file}: {e}")
                    pbar.update(1)
                    continue
        
        # Schließe Datenbankverbindung
        if self.connection:
            self.connection.close()
        
        logger.info("Enhanced import completed!")
        return True
    
    def print_statistics(self):
        """Druckt detaillierte Statistiken der Enhanced Kategorisierung."""
        print("\n" + "="*60)
        print("🚀 ENHANCED AQEA CATEGORIZATION RESULTS")
        print("="*60)
        
        print(f"\n📊 PROCESSING SUMMARY:")
        print(f"├── Total entries processed: {self.stats['total_processed']:,}")
        print(f"├── Address changes made: {self.stats['address_changes']:,}")
        print(f"├── Original unique addresses: {len(self.stats['original_addresses']):,}")
        print(f"└── Enhanced unique addresses: {len(self.stats['enhanced_addresses']):,}")
        
        print(f"\n🏷️ CATEGORY DISTRIBUTION:")
        total_entries = sum(self.stats['category_distribution'].values())
        
        for qq_code_hex, count in sorted(self.stats['category_distribution'].items()):
            qq_code = int(qq_code_hex, 16)
            category_name = self.ENHANCED_QQ_CODES.get(qq_code, "unknown")
            percentage = (count / total_entries) * 100 if total_entries > 0 else 0
            
            print(f"├── {qq_code_hex} ({category_name}): {count:,} ({percentage:.1f}%)")
        
        # Berechne Verbesserungen
        ff_percentage = (self.stats['category_distribution'].get('0xff', 0) / total_entries) * 100 if total_entries > 0 else 0
        
        print(f"\n🎯 QUALITY IMPROVEMENTS:")
        print(f"├── 0xFF usage reduced to: {ff_percentage:.1f}% (Target: <20%)")
        print(f"├── Categories utilized: {len([c for c in self.stats['category_distribution'].values() if c > 0])}/7")
        print(f"└── Address diversity improved: {len(self.stats['enhanced_addresses'])} unique addresses")
        
        # Erfolg-Indikatoren
        success_indicators = []
        if ff_percentage < 20:
            success_indicators.append("✅ 0xFF usage target achieved")
        if len(self.stats['category_distribution']) >= 6:
            success_indicators.append("✅ Category diversity achieved")
        if self.stats['address_changes'] > 0:
            success_indicators.append("✅ Intelligent re-categorization working")
        
        if success_indicators:
            print(f"\n🏆 SUCCESS INDICATORS:")
            for indicator in success_indicators:
                print(f"├── {indicator}")
        
        print("="*60)
    
    def run_sample_tests(self):
        """Testet die Kategorisierung an Stichproben."""
        print("\n🧪 RUNNING SAMPLE TESTS...")
        
        test_cases = [
            ("Wasserstoffatome", 0x12, "compound"),
            ("schönere", 0x11, "comparative"),  
            ("lege artis", 0x13, "idiom"),
            ("Photosynthese", 0x14, "technical"),
            ("Häusern", 0x15, "inflected"),
            ("Wasser", 0x10, "base_form"),
            ("sich freuen", 0x13, "reflexive_phrase"),
            ("Universitätsgebäude", 0x12, "long_compound"),
            ("Analyse", 0x14, "scientific_term")
        ]
        
        passed = 0
        total = len(test_cases)
        
        for word, expected_category, reason in test_cases:
            actual_category = self.determine_enhanced_category(word, {}, 'deu')
            
            if actual_category == expected_category:
                print(f"✅ {word} → {hex(actual_category)} ({reason})")
                passed += 1
            else:
                print(f"❌ {word} → {hex(actual_category)} (expected {hex(expected_category)}, {reason})")
        
        print(f"\nTest Results: {passed}/{total} passed ({(passed/total)*100:.1f}%)")
        return passed == total


def main():
    parser = argparse.ArgumentParser(description="Enhanced AQEA JSON to SQLite Importer")
    parser.add_argument("--source-dir", default="extracted_data", 
                       help="Directory containing AQEA JSON files")
    parser.add_argument("--database", default="data/aqea_extraction.db",
                       help="SQLite database path")
    parser.add_argument("--test", action="store_true",
                       help="Run sample tests for categorization")
    
    args = parser.parse_args()
    
    # Enhanced Importer erstellen
    importer = EnhancedAQEAImporter(args.database)
    
    # Sample Tests ausführen falls gewünscht
    if args.test:
        test_passed = importer.run_sample_tests()
        if not test_passed:
            logger.error("Sample tests failed! Check categorization logic.")
            return 1
    
    # Backup der bestehenden Datenbank erstellen
    if os.path.exists(args.database):
        backup_path = f"{args.database}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(args.database, backup_path)
        logger.info(f"Existing database backed up to: {backup_path}")
    
    # Enhanced Import durchführen
    success = importer.import_with_enhanced_categorization(args.source_dir)
    
    if success:
        # Statistiken anzeigen
        importer.print_statistics()
        logger.info("Enhanced categorization completed successfully!")
        return 0
    else:
        logger.error("Enhanced categorization failed!")
        return 1


if __name__ == "__main__":
    exit(main()) 
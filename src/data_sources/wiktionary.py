"""
Wiktionary Data Source for AQEA Distributed Extractor
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, AsyncGenerator
from aiohttp import ClientSession

logger = logging.getLogger(__name__)


class WiktionaryDataSource:
    """Wiktionary data source using MediaWiki Action API."""
    
    def __init__(self, config):
        self.config = config
        self.session = None
        self.base_urls = {
            'de': 'https://de.wiktionary.org/w/api.php',
            'en': 'https://en.wiktionary.org/w/api.php',
            'fr': 'https://fr.wiktionary.org/w/api.php',
            'es': 'https://es.wiktionary.org/w/api.php'
        }
        self.request_delay = 0.2  # 200ms between requests
        
    async def test_connection(self) -> bool:
        """Test connection to Wiktionary API."""
        if not self.session:
            self.session = ClientSession()
        
        try:
            api_url = self.base_urls['en']
            params = {
                'action': 'query',
                'format': 'json',
                'meta': 'siteinfo'
            }
            
            async with self.session.get(api_url, params=params) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def test_extraction(self, count: int = 10) -> List[Dict[str, Any]]:
        """Test extraction of a small number of entries."""
        async with ClientSession() as session:
            self.session = session
        results = []
        test_words = ['water', 'house', 'run', 'good', 'time']
        
        for word in test_words[:count]:
            try:
                entry = await self._extract_single_entry('en', word)
                if entry:
                    results.append(entry)
            except Exception as e:
                logger.warning(f"Failed to extract test word '{word}': {e}")
        
            self.session = None
        return results
    
    async def extract_range(self, language: str, start_range: str, end_range: str, 
                          batch_size: int = 10) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Extract entries in alphabetical range."""
        if not self.session:
            self.session = ClientSession()
        
        # Get all pages in the range
        logger.info(f"Starting extraction for {language} Wiktionary range {start_range}-{end_range}")
        all_pages = await self._get_pages_in_range(language, start_range, end_range)
        
        total_pages = len(all_pages)
        if total_pages == 0:
            logger.warning(f"No pages found in range {start_range}-{end_range}")
            return
        
        logger.info(f"Beginning extraction of {total_pages} pages from {language} Wiktionary")
        
        # Process in batches
        batch = []
        processed = 0
        success = 0
        
        for page_title in all_pages:
            processed += 1
            
            try:
                entry = await self._extract_single_entry(language, page_title)
                if entry:
                    batch.append(entry)
                    success += 1
                    logger.debug(f"Extracted '{page_title}' successfully")
                else:
                    logger.debug(f"Skipped '{page_title}' (no valid data)")
                
                if len(batch) >= batch_size:
                    logger.info(f"Yielding batch of {len(batch)} entries ({processed}/{total_pages} processed)")
                    yield batch
                    batch = []
                
                # Report progress periodically
                if processed % 10 == 0:
                    logger.info(f"Progress: {processed}/{total_pages} pages ({success} successful)")
                
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.warning(f"Failed to extract '{page_title}': {e}")
                continue
        
        if batch:
            logger.info(f"Yielding final batch of {len(batch)} entries")
            yield batch
            
        logger.info(f"Extraction complete: {processed}/{total_pages} pages processed, {success} entries extracted")
    
    async def _get_pages_in_range(self, language: str, start_char: str, end_char: str) -> List[str]:
        """Get page titles in alphabetical range."""
        api_url = self.base_urls[language]
        all_pages = []
        
        # QUICK FIX: Lade nur wenige Seiten für Testing
        continue_token = None
        count = 0
        max_pages = 100  # DRASTISCH reduziert für Testing 
        
        logger.info(f"Fetching pages from {start_char} to {end_char} in {language} Wiktionary")
        
        while count < max_pages:
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'allpages',
                'apfrom': start_char,
                'apto': end_char + 'zzz',
                'aplimit': 50,  # Kleinere Batches für bessere Stabilität
                'apnamespace': 0
            }
            
            if continue_token:
                params['apcontinue'] = continue_token
            
            try:
                async with self.session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'query' in data and 'allpages' in data['query']:
                            pages = data['query']['allpages']
                            for page in pages:
                                title = page['title']
                                if self._is_valid_entry_title(title):
                                    all_pages.append(title)
                                    count += 1
                            
                            # QUICK FIX: Stoppe nach ersten Batch für Testing
                            logger.info(f"TESTING MODE: Stopping after first batch ({len(pages)} pages)")
                            break  # Stoppe nach erstem Batch
                        else:
                            break
                    else:
                        logger.warning(f"Error status {response.status} fetching pages")
                        break
            except Exception as e:
                logger.error(f"Error getting pages: {e}")
                await asyncio.sleep(1)  # Längere Wartezeit bei Fehlern
        
        logger.info(f"Found {len(all_pages)} valid pages in range {start_char}-{end_char}")
        return all_pages
    
    def _is_valid_entry_title(self, title: str) -> bool:
        """Check if title is a valid dictionary entry."""
        if not title or len(title) > 50:
            return False
        
        # Skip special pages
        if ':' in title:
            return False
        
        # Skip parenthetical titles like "Word (disambiguation)"
        if ' (' in title:
            return False
        
        # Skip numbers only
        if title.isdigit():
            return False
            
        # Skip titles with special characters that aren't likely to be words
        if re.search(r'[/\[\]{}]', title):
            return False
        
        # Allow German umlauts, common European letters, hyphens and apostrophes
        return bool(re.match(r'^[a-zA-ZÀ-ÿĀ-žА-яäöüÄÖÜß\s\-\']+$', title))
    
    async def _extract_single_entry(self, language: str, title: str) -> Optional[Dict[str, Any]]:
        """Extract data for a single entry."""
        api_url = self.base_urls[language]
        
        params = {
            'action': 'query',
            'format': 'json',
            'titles': title,
            'prop': 'revisions',
            'rvprop': 'content',
            'rvslots': 'main'
        }
        
        try:
            async with self.session.get(api_url, params=params) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                pages = data.get('query', {}).get('pages', {})
                page_id = list(pages.keys())[0]
                
                if page_id == '-1':
                    return None
                
                page = pages[page_id]
                if 'revisions' not in page:
                    return None
                
                content = page['revisions'][0]['slots']['main']['*']
                return await self._parse_wikitext(title, content, language)
                
        except Exception as e:
            logger.warning(f"Error extracting '{title}': {e}")
            return None
    
    async def _parse_wikitext(self, title: str, wikitext: str, language: str) -> Optional[Dict[str, Any]]:
        """Parse Wikitext content."""
        entry = {
            'word': title,
            'language': language,
            'definitions': [],
            'ipa': None,
            'audio': None,
            'pos': None,
            'forms': [],
            'labels': []
        }
        
        # Anpassung für verschiedene Sprachen
        if language == 'de':
            return self._parse_german_wikitext(entry, wikitext)
        else:
            return self._parse_generic_wikitext(entry, wikitext)
    
    def _parse_german_wikitext(self, entry: Dict[str, Any], wikitext: str) -> Optional[Dict[str, Any]]:
        """Parse German Wiktionary wikitext."""
        # Extrahiere Wortart ({{Wortart|...}})
        pos_match = re.search(r'\{\{Wortart\|([^|{}]+)', wikitext)
        if pos_match:
            german_pos = pos_match.group(1).strip()
            # Übersetze deutsche Wortarten
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
                'Interjektion': 'interjection'
            }
            entry['pos'] = pos_mapping.get(german_pos, 'unknown')
            logger.debug(f"Extracted German POS: {german_pos} -> {entry['pos']}")
        
        # Extrahiere IPA
        ipa_match = re.search(r'\{\{Lautschrift\}\}\s*\[\[([^\]]+)\]\]', wikitext)
        if ipa_match:
            entry['ipa'] = ipa_match.group(1).strip()
        
        # Extrahiere Definitionen - nach {{Bedeutungen}}
        definitions = []
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
                definition = self._clean_definition(definition)
                if definition:
                    definitions.append(definition)
        
        entry['definitions'] = definitions[:5]  # Bis zu 5 Definitionen
        
        return entry if entry['definitions'] or entry['pos'] else None
            
    def _parse_generic_wikitext(self, entry: Dict[str, Any], wikitext: str) -> Optional[Dict[str, Any]]:
        """Parse Wikitext content for non-German languages."""
        # Extract IPA
        ipa_match = re.search(r'\{\{IPA\|[^}]*\|([^}|]+)', wikitext)
        if ipa_match:
            entry['ipa'] = ipa_match.group(1).strip()
        
        # Extract audio
        audio_match = re.search(r'\{\{audio\|[^}]*\|([^}|]+)', wikitext, re.IGNORECASE)
        if audio_match:
            entry['audio'] = audio_match.group(1).strip()
        
        # Extract definitions
        definition_lines = re.findall(r'^#\s*([^#\n]+)', wikitext, re.MULTILINE)
        entry['definitions'] = [self._clean_definition(def_line) for def_line in definition_lines[:3]]
        
        # Extract part of speech
        pos_match = re.search(r'===(Noun|Verb|Adjective|Adverb)===', wikitext, re.IGNORECASE)
        if pos_match:
            entry['pos'] = pos_match.group(1).lower()
        
        return entry if entry['definitions'] or entry['ipa'] else None
    
    def _clean_definition(self, definition: str) -> str:
        """Clean definition text."""
        # Remove wiki markup
        definition = re.sub(r'\[\[([^|\]]+\|)?([^\]]+)\]\]', r'\2', definition)
        definition = re.sub(r'\{\{[^}]+\}\}', '', definition)
        definition = re.sub(r'<[^>]+>', '', definition)
        return re.sub(r'\s+', ' ', definition).strip() 
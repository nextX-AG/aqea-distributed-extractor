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
        if not self.session:
            self.session = ClientSession()
        
        results = []
        test_words = ['water', 'house', 'run', 'good', 'time']
        
        for word in test_words[:count]:
            try:
                entry = await self._extract_single_entry('en', word)
                if entry:
                    results.append(entry)
            except Exception as e:
                logger.warning(f"Failed to extract test word '{word}': {e}")
        
        return results
    
    async def extract_range(self, language: str, start_range: str, end_range: str, 
                          batch_size: int = 50) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Extract entries in alphabetical range."""
        if not self.session:
            self.session = ClientSession()
        
        # Get all pages in the range
        all_pages = await self._get_pages_in_range(language, start_range, end_range)
        
        # Process in batches
        batch = []
        for page_title in all_pages:
            try:
                entry = await self._extract_single_entry(language, page_title)
                if entry:
                    batch.append(entry)
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
                
                await asyncio.sleep(self.request_delay)
                
            except Exception as e:
                logger.warning(f"Failed to extract '{page_title}': {e}")
                continue
        
        if batch:
            yield batch
    
    async def _get_pages_in_range(self, language: str, start_char: str, end_char: str) -> List[str]:
        """Get page titles in alphabetical range."""
        api_url = self.base_urls[language]
        all_pages = []
        
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'allpages',
            'apfrom': start_char,
            'apto': end_char + 'zzz',
            'aplimit': 500,
            'apnamespace': 0
        }
        
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
        except Exception as e:
            logger.error(f"Error getting pages: {e}")
        
        return all_pages
    
    def _is_valid_entry_title(self, title: str) -> bool:
        """Check if title is a valid dictionary entry."""
        if not title or len(title) > 50:
            return False
        
        # Skip special pages
        if ':' in title or '(' in title:
            return False
        
        # Should be mostly alphabetic
        return bool(re.match(r'^[a-zA-ZÀ-ÿĀ-žА-я\s\-\']+$', title))
    
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
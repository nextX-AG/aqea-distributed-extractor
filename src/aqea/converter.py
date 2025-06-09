"""
AQEA Converter - Transform language data to AQEA format

Converts extracted dictionary entries to AQEA 4-byte address format.
Based on AQEA specification: AA:QQ:EE:A2

UPDATED: Now uses final 0xA0-0xDF Language Family Blocks 
from UNIVERSAL_LANGUAGE_DOMAIN_FINAL.md
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .address_generator import AddressGenerator
from .schema import AQEAEntry
from .language_mappings import (
    get_language_domain,
    get_language_name,
    get_language_family_by_code,
    is_valid_language_domain,
    ISO_639_1_TO_3
)

logger = logging.getLogger(__name__)


class AQEAConverter:
    """Converts extracted language data to AQEA format.
    
    UPDATED: Now uses 0xA0-0xDF Family Blocks for language encoding:
    - 0xA0-0xAF: Germanic (deu=0xA0, eng=0xA1, etc.)
    - 0xB0-0xBF: Romance (fra=0xB0, spa=0xB1, etc.)
    - 0xC0-0xCF: Slavic (rus=0xC0, pol=0xC1, etc.)
    - 0xD0-0xDF: Asian (cmn=0xD0, jpn=0xD1, etc.)
    """
    
    # Part of speech mappings (QQ byte)
    POS_CATEGORIES = {
        'noun': 0x01,
        'verb': 0x02,
        'adjective': 0x03,
        'adverb': 0x04,
        'pronoun': 0x05,
        'preposition': 0x06,
        'conjunction': 0x07,
        'interjection': 0x08,
        'article': 0x09,
        'numeral': 0x0A,
        'unknown': 0xFF
    }
    
    # Semantic subcategories (EE byte)
    SEMANTIC_CATEGORIES = {
        # Nature & Environment
        'nature': 0x01,
        'animals': 0x02,
        'plants': 0x03,
        'weather': 0x04,
        'geography': 0x05,
        
        # Human & Society
        'body': 0x10,
        'family': 0x11,
        'profession': 0x12,
        'emotion': 0x13,
        'social': 0x14,
        
        # Objects & Technology
        'tools': 0x20,
        'food': 0x21,
        'clothing': 0x22,
        'transport': 0x23,
        'technology': 0x24,
        
        # Abstract & Concepts
        'time': 0x30,
        'space': 0x31,
        'quantity': 0x32,
        'quality': 0x33,
        'action': 0x34,
        
        # Default
        'general': 0x01
    }
    
    def __init__(self, config: Dict[str, Any], language: str, database=None, worker_id: str = None):
        self.config = config
        
        # Support both ISO 639-1 and ISO 639-3 codes
        self.language = self._normalize_language_code(language)
        self.address_generator = AddressGenerator(self.language, database, worker_id)
        
        # Validate language support and get AA-byte
        self.domain_byte = get_language_domain(self.language)
        if not self.domain_byte or not is_valid_language_domain(self.domain_byte):
            raise ValueError(f"Language '{language}' not supported in AQEA Family Blocks (0xA0-0xDF)")
        
        self.language_name = get_language_name(self.domain_byte)
        self.language_family = get_language_family_by_code(self.language)
        
        logger.info(f"AQEA Converter initialized for {self.language_name} "
                   f"(0x{self.domain_byte:02X}, {self.language_family} family)")
    
    def _normalize_language_code(self, language: str) -> str:
        """Convert language code to ISO 639-3 format if needed."""
        language = language.lower().strip()
        
        # Convert if it's a 2-letter code using the centralized mapping
        if len(language) == 2 and language in ISO_639_1_TO_3:
            return ISO_639_1_TO_3[language]
        
        # Assume it's already ISO 639-3 or return as-is
        return language
        
    async def convert(self, entry: Dict[str, Any]) -> Optional[AQEAEntry]:
        """Convert a dictionary entry to AQEA format."""
        try:
            word = entry.get('word', '').strip()
            if not word:
                logger.warning("Empty word in entry, skipping")
                return None
            
            # Generate AQEA address
            address = await self._generate_address(entry)
            if not address:
                logger.warning(f"Could not generate AQEA address for '{word}'")
                return None
            
            # Create AQEA entry
            aqea_entry = AQEAEntry(
                address=address,
                label=word,
                description=self._create_description(entry),
                domain=f"0x{self.domain_byte:02X}",
                lang_ui=self.language,
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="aqea-distributed-extractor",
                meta=self._create_meta(entry)
            )
            
            logger.debug(f"Converted '{word}' to AQEA address {address}")
            return aqea_entry
            
        except Exception as e:
            logger.error(f"Error converting entry '{entry.get('word', 'unknown')}': {e}")
            return None
    
    async def _generate_address(self, entry: Dict[str, Any]) -> Optional[str]:
        """Generate AQEA 4-byte address for the entry."""
        try:
            word = entry.get('word', '')
            if word is None:
                word = ''
            
            # Domain byte (AA) - Language (using new Family Block system)
            aa = self.domain_byte
            
            # Category byte (QQ) - Part of Speech
            pos = entry.get('pos', 'unknown')
            if pos is not None:
                pos = pos.lower()
            else:
                pos = 'unknown'
            qq = self.POS_CATEGORIES.get(pos, self.POS_CATEGORIES['unknown'])
            
            # Subcategory byte (EE) - Semantic category
            ee = self._determine_semantic_category(entry)
            
            # Erstelle einen eindeutigeren Hash-basierten Seed für dieses Wort
            # Berücksichtige mehr Merkmale als nur das Wort selbst
            seed_text = f"{word}|{pos}|{entry.get('language', self.language)}|{','.join(entry.get('definitions', [])[:1])}"
            hash_obj = hashlib.md5(seed_text.encode('utf-8'))
            hash_int = int(hash_obj.hexdigest(), 16)
            suggested_a2 = (hash_int % 250) + 1  # Werte zwischen 1-250, vermeide 0, 0xFF
            
            # Element byte (A2) - Unique identifier within subcategory
            a2 = await self.address_generator.get_next_element_id(aa, qq, ee, word, suggested_a2)
            
            # Format as hex string
            address = f"0x{aa:02X}:{qq:02X}:{ee:02X}:{a2:02X}"
            logger.debug(f"Generated address {address} for '{word}' (pos={pos}, ee={ee:02X}, a2={a2:02X})")
            return address
            
        except Exception as e:
            logger.error(f"Error generating address: {e}")
            return None
    
    def _determine_semantic_category(self, entry: Dict[str, Any]) -> int:
        """Determine semantic category based on entry content."""
        word = entry.get('word', '')
        if word is None:
            word = ''
        word = word.lower()
        
        definitions = entry.get('definitions', [])
        labels = entry.get('labels', [])
        
        # Combine all text for analysis
        text_for_analysis = f"{word} {' '.join(str(d) for d in definitions if d is not None)} {' '.join(str(l) for l in labels if l is not None)}".lower()
        
        # Keyword-based categorization
        categorization_rules = {
            'nature': ['water', 'earth', 'fire', 'air', 'nature', 'natural', 'environment'],
            'animals': ['animal', 'dog', 'cat', 'bird', 'fish', 'mammal', 'species'],
            'plants': ['plant', 'tree', 'flower', 'leaf', 'garden', 'grow'],
            'weather': ['weather', 'rain', 'sun', 'cloud', 'wind', 'storm'],
            'body': ['body', 'head', 'hand', 'foot', 'eye', 'nose', 'mouth'],
            'family': ['family', 'mother', 'father', 'child', 'parent', 'relative'],
            'food': ['food', 'eat', 'drink', 'cook', 'meal', 'hunger', 'taste'],
            'time': ['time', 'hour', 'day', 'week', 'month', 'year', 'moment'],
            'action': ['do', 'make', 'go', 'come', 'run', 'walk', 'move']
        }
        
        # Check for category matches
        for category, keywords in categorization_rules.items():
            if any(keyword in text_for_analysis for keyword in keywords):
                return self.SEMANTIC_CATEGORIES.get(category, self.SEMANTIC_CATEGORIES['general'])
        
        # Default to general category
        return self.SEMANTIC_CATEGORIES['general']
    
    def _create_description(self, entry: Dict[str, Any]) -> str:
        """Create English description for the entry."""
        word = entry.get('word', '')
        pos = entry.get('pos', 'word')
        definitions = entry.get('definitions', [])
        
        # Create base description using language name from mappings
        if definitions:
            main_def = definitions[0][:100]  # Limit length
            description = f"{self.language_name} {pos} '{word}'. {main_def}"
        else:
            description = f"{self.language_name} {pos} '{word}'"
        
        # Add IPA if available
        if entry.get('ipa'):
            description += f" Pronunciation: /{entry['ipa']}/"
        
        return description
    
    def _create_meta(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive meta object with all available linguistic data."""
        meta = {
            'lemma': entry.get('word', ''),
            'source': 'wiktionary',
            'extraction_timestamp': datetime.now().isoformat(),
            'language': self.language,
            'language_name': self.language_name,
            'language_family': self.language_family
        }
        
        # === PHONETIC DATA ===
        if entry.get('ipa'):
            meta['ipa'] = entry['ipa']
        
        if entry.get('audio'):
            meta['audio'] = entry['audio']  # List of audio files with descriptions
            
        if entry.get('hyphenation'):
            meta['hyphenation'] = entry['hyphenation']
        
        # === GRAMMATICAL DATA ===
        if entry.get('pos'):
            meta['pos'] = entry['pos']
        
        if entry.get('flexion'):
            meta['flexion'] = entry['flexion']  # Nominativ, Genitiv, Dativ, Akkusativ forms
        
        if entry.get('forms'):
            meta['forms'] = entry['forms'][:5]  # Limit to 5 forms
        
        # === SEMANTIC DATA ===
        if entry.get('definitions'):
            meta['definitions'] = entry['definitions'][:5]  # Limit to 5 definitions
            
        if entry.get('examples'):
            meta['examples'] = entry['examples'][:3]  # Limit to 3 examples
            
        if entry.get('synonyms'):
            meta['synonyms'] = entry['synonyms'][:5]  # Limit to 5 synonyms
        
        if entry.get('labels'):
            meta['labels'] = entry['labels']
        
        # === FREQUENCY & STATISTICS ===
        meta['frequency'] = self._estimate_frequency(entry)
        meta['richness_score'] = self._calculate_richness_score(entry)
        
        return meta
    
    def _calculate_richness_score(self, entry: Dict[str, Any]) -> int:
        """Calculate richness score based on available metadata (0-100)."""
        score = 0
        
        # Basic data (20 points)
        if entry.get('word'): score += 5
        if entry.get('pos'): score += 5
        if entry.get('definitions'): score += 10
        
        # Phonetic data (25 points)
        if entry.get('ipa'): score += 15
        if entry.get('audio'): score += 10
        
        # Grammatical data (25 points)
        if entry.get('flexion'): score += 15
        if entry.get('hyphenation'): score += 5
        if entry.get('forms'): score += 5
        
        # Semantic data (30 points)
        if entry.get('examples'): score += 15
        if entry.get('synonyms'): score += 10
        if entry.get('labels'): score += 5
        
        return min(score, 100)  # Cap at 100
    
    def _estimate_frequency(self, entry: Dict[str, Any]) -> int:
        """Estimate word frequency based on available data."""
        word = entry.get('word', '')
        if word is None:
            word = ''
        
        # Simple heuristics for frequency estimation
        # In a real implementation, this would use actual frequency data
        
        base_frequency = 1000
        
        # Shorter words are often more frequent
        if len(word) <= 3:
            base_frequency += 500
        elif len(word) <= 5:
            base_frequency += 200
        
        # Common parts of speech are more frequent
        pos = entry.get('pos', '')
        if pos is not None and pos.lower() in ['noun', 'verb', 'adjective']:
            base_frequency += 300
        
        # Words with many definitions are often more frequent
        definitions = entry.get('definitions', [])
        if definitions is not None:
            base_frequency += len(definitions) * 50
        
        return min(base_frequency, 9999)  # Cap at 9999
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        return self.address_generator.get_statistics() 
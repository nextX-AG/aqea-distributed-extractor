"""
AQEA Converter - Transform language data to AQEA format

Converts extracted dictionary entries to AQEA 4-byte address format.
Based on AQEA specification: AA:QQ:EE:A2
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from .address_generator import AddressGenerator
from .schema import AQEAEntry

logger = logging.getLogger(__name__)


class AQEAConverter:
    """Converts extracted language data to AQEA format."""
    
    # Language domain mappings (0x20-0x2F for languages)
    LANGUAGE_DOMAINS = {
        'de': 0x20,  # German
        'en': 0x21,  # English
        'fr': 0x22,  # French
        'es': 0x23,  # Spanish
        'it': 0x24,  # Italian
        'pt': 0x25,  # Portuguese
        'ru': 0x26,  # Russian
        'zh': 0x27,  # Chinese
        'ja': 0x28,  # Japanese
        'ar': 0x29,  # Arabic
    }
    
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
    
    def __init__(self, config: Dict[str, Any], language: str):
        self.config = config
        self.language = language.lower()
        self.address_generator = AddressGenerator(language)
        
        # Validate language support
        if self.language not in self.LANGUAGE_DOMAINS:
            raise ValueError(f"Language '{language}' not supported in AQEA mapping")
        
        self.domain_byte = self.LANGUAGE_DOMAINS[self.language]
        
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
            word = entry['word']
            
            # Domain byte (AA) - Language
            aa = self.domain_byte
            
            # Category byte (QQ) - Part of Speech
            pos = entry.get('pos', 'unknown').lower()
            qq = self.POS_CATEGORIES.get(pos, self.POS_CATEGORIES['unknown'])
            
            # Subcategory byte (EE) - Semantic category
            ee = self._determine_semantic_category(entry)
            
            # Element byte (A2) - Unique identifier within subcategory
            a2 = await self.address_generator.get_next_element_id(aa, qq, ee, word)
            
            # Format as hex string
            address = f"0x{aa:02X}:{qq:02X}:{ee:02X}:{a2:02X}"
            return address
            
        except Exception as e:
            logger.error(f"Error generating address: {e}")
            return None
    
    def _determine_semantic_category(self, entry: Dict[str, Any]) -> int:
        """Determine semantic category based on entry content."""
        word = entry.get('word', '').lower()
        definitions = entry.get('definitions', [])
        labels = entry.get('labels', [])
        
        # Combine all text for analysis
        text_for_analysis = f"{word} {' '.join(definitions)} {' '.join(labels)}".lower()
        
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
        language = entry.get('language', self.language)
        pos = entry.get('pos', 'word')
        definitions = entry.get('definitions', [])
        
        # Create base description
        if definitions:
            main_def = definitions[0][:100]  # Limit length
            description = f"{language.title()} {pos} '{word}'. {main_def}"
        else:
            description = f"{language.title()} {pos} '{word}'"
        
        # Add IPA if available
        if entry.get('ipa'):
            description += f" Pronunciation: /{entry['ipa']}/"
        
        return description
    
    def _create_meta(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Create meta object with language-specific data."""
        meta = {
            'lemma': entry.get('word', ''),
            'source': 'wiktionary',
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        # Add available linguistic data
        if entry.get('ipa'):
            meta['ipa'] = entry['ipa']
        
        if entry.get('pos'):
            meta['pos'] = entry['pos']
        
        if entry.get('definitions'):
            meta['definitions'] = entry['definitions'][:3]  # Limit to 3 definitions
        
        if entry.get('forms'):
            meta['forms'] = entry['forms'][:5]  # Limit to 5 forms
        
        if entry.get('labels'):
            meta['labels'] = entry['labels']
        
        if entry.get('audio'):
            meta['audio'] = entry['audio']
        
        # Add language-specific metadata
        meta['frequency'] = self._estimate_frequency(entry)
        
        return meta
    
    def _estimate_frequency(self, entry: Dict[str, Any]) -> int:
        """Estimate word frequency based on available data."""
        word = entry.get('word', '')
        
        # Simple heuristics for frequency estimation
        # In a real implementation, this would use actual frequency data
        
        base_frequency = 1000
        
        # Shorter words are often more frequent
        if len(word) <= 3:
            base_frequency += 500
        elif len(word) <= 5:
            base_frequency += 200
        
        # Common parts of speech are more frequent
        pos = entry.get('pos', '').lower()
        if pos in ['noun', 'verb', 'adjective']:
            base_frequency += 300
        
        # Words with many definitions are often more frequent
        definitions = entry.get('definitions', [])
        base_frequency += len(definitions) * 50
        
        return min(base_frequency, 9999)  # Cap at 9999
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        return self.address_generator.get_statistics() 
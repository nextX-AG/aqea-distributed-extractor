"""
USH-Enhanced AQEA Converter

Advanced converter that implements the Universal Semantic Hierarchy for AQEA addressing.
Extends the original AQEAConverter with USH capabilities.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .address_generator import AddressGenerator
from .schema import AQEAEntry
from .ush_adapter import USHAdapter

logger = logging.getLogger(__name__)


class USHConverter:
    """USH-enhanced AQEA converter for universal semantic addressing."""
    
    def __init__(self, config: Dict[str, Any], language: str, database=None, worker_id: str = None):
        self.config = config
        self.language = language.lower()
        self.address_generator = AddressGenerator(language, database, worker_id)
        self.ush_adapter = USHAdapter(config, language)
        
        # Backward compatibility flag
        self.use_legacy_mode = config.get('aqea', {}).get('use_legacy_mode', False)
        
        # Cross-linguistic mapping
        self.enable_cross_linguistic = config.get('aqea', {}).get('enable_cross_linguistic', True)
        
        # Track statistics
        self.stats = {
            'total_converted': 0,
            'ush_addresses_generated': 0,
            'legacy_addresses_generated': 0,
            'migrations_performed': 0,
            'cross_linguistic_mappings': 0
        }
    
    async def convert(self, entry: Dict[str, Any]) -> Optional[AQEAEntry]:
        """Convert a dictionary entry to AQEA format with USH addressing."""
        try:
            word = entry.get('word', '').strip()
            if not word:
                logger.warning("Empty word in entry, skipping")
                return None
            
            # Generate AQEA address
            address, meta_updates = await self._generate_address(entry)
            if not address:
                logger.warning(f"Could not generate AQEA address for '{word}'")
                return None
            
            # Update entry metadata with USH information
            entry_meta = self._create_meta(entry)
            entry_meta.update(meta_updates)
            
            # Create AQEA entry
            aqea_entry = AQEAEntry(
                address=address,
                label=word,
                description=self._create_description(entry),
                domain=f"0x{self.ush_adapter.domain_byte:02X}",
                lang_ui=self.language,
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="aqea-ush-converter",
                meta=entry_meta
            )
            
            # Update statistics
            self.stats['total_converted'] += 1
            
            logger.debug(f"Converted '{word}' to USH address {address}")
            return aqea_entry
            
        except Exception as e:
            logger.error(f"Error converting entry '{entry.get('word', 'unknown')}': {e}")
            return None
    
    async def _generate_address(self, entry: Dict[str, Any]) -> tuple[Optional[str], Dict[str, Any]]:
        """Generate AQEA address with USH format or legacy format based on configuration."""
        try:
            # Check if using legacy mode
            if self.use_legacy_mode:
                # Use legacy address generation logic
                aa = self.ush_adapter.domain_byte
                
                # Use legacy POS mapping (simplified)
                pos = entry.get('pos', 'unknown')
                if pos is None:
                    pos = 'unknown'
                pos = pos.lower()
                
                # Legacy POS to QQ mapping
                legacy_pos_map = {
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
                
                qq = legacy_pos_map.get(pos, 0xFF)
                
                # Legacy semantic category (simplified)
                ee = 0x01  # General category
                
                # Get element ID from address generator
                word = entry.get('word', '')
                a2 = await self.address_generator.get_next_element_id(aa, qq, ee, word)
                
                # Format as hex string
                address = f"0x{aa:02X}:{qq:02X}:{ee:02X}:{a2:02X}"
                
                self.stats['legacy_addresses_generated'] += 1
                
                # Legacy metadata
                metadata = {
                    'address_format': 'legacy',
                    'ush_compatible': False
                }
                
                return address, metadata
            else:
                # Use USH address generation
                ush_address, ush_metadata = self.ush_adapter.generate_ush_address(entry)
                
                # Check if cross-linguistic mappings should be registered
                if self.enable_cross_linguistic:
                    self._register_cross_linguistic_mapping(ush_address, entry)
                
                self.stats['ush_addresses_generated'] += 1
                
                # Add USH compatibility flag
                ush_metadata['address_format'] = 'ush'
                ush_metadata['ush_compatible'] = True
                
                return ush_address, ush_metadata
                
        except Exception as e:
            logger.error(f"Error generating address: {e}")
            return None, {}
    
    def _register_cross_linguistic_mapping(self, address: str, entry: Dict[str, Any]) -> None:
        """Register cross-linguistic mapping if translations are available."""
        try:
            # Check if entry has translations
            translations = entry.get('translations', {})
            if not translations:
                return
            
            # Register each translation
            for target_lang, target_words in translations.items():
                if not target_words:
                    continue
                
                # Take first translation as primary
                target_word = target_words[0] if isinstance(target_words, list) else target_words
                
                # Register mapping
                if self.ush_adapter.register_cross_linguistic_mapping(address, target_lang, target_word):
                    self.stats['cross_linguistic_mappings'] += 1
                    
        except Exception as e:
            logger.warning(f"Error registering cross-linguistic mapping: {e}")
    
    def _create_description(self, entry: Dict[str, Any]) -> str:
        """Create English description for the entry with USH categorization."""
        word = entry.get('word', '')
        language = entry.get('language', self.language)
        pos = entry.get('pos', 'word')
        definitions = entry.get('definitions', [])
        
        # Get USH category and cluster descriptions
        category_name, qq = self.ush_adapter.determine_semantic_category(entry)
        cluster_name, ee = self.ush_adapter.determine_hierarchical_cluster(entry)
        
        # Format USH category for description
        ush_category = category_name.replace('_', ' ').title()
        ush_cluster = cluster_name.replace('_', ' ').title()
        
        # Create base description
        if definitions:
            main_def = definitions[0][:100] if definitions[0] else ""  # Limit length
            description = f"{language.title()} {pos} '{word}'. {main_def}"
        else:
            description = f"{language.title()} {pos} '{word}'"
        
        # Add USH categorization
        description += f" [USH: {ush_category}, {ush_cluster}]"
        
        # Add IPA if available
        if entry.get('ipa'):
            description += f" Pronunciation: /{entry['ipa']}/"
        
        return description
    
    def _create_meta(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Create meta object with language-specific data and USH information."""
        meta = {
            'lemma': entry.get('word', ''),
            'source': entry.get('source', 'wiktionary'),
            'extraction_timestamp': datetime.now().isoformat(),
            'ush_version': '1.0'
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
        
        if entry.get('translations'):
            meta['translations'] = entry['translations']
        
        # Add USH-specific metadata
        category_name, _ = self.ush_adapter.determine_semantic_category(entry)
        cluster_name, _ = self.ush_adapter.determine_hierarchical_cluster(entry)
        
        meta['ush_category'] = category_name
        meta['ush_cluster'] = cluster_name
        
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
    
    async def migrate_entry(self, entry: AQEAEntry) -> Optional[AQEAEntry]:
        """Migrate an existing entry from legacy to USH addressing."""
        try:
            # Check if migration is needed
            if not self.ush_adapter.needs_migration(entry.address):
                return entry
            
            # Convert entry to dictionary for adapter
            entry_dict = {
                'word': entry.label,
                'pos': entry.meta.get('pos', 'unknown'),
                'definitions': entry.meta.get('definitions', []),
                'labels': entry.meta.get('labels', []),
                'ipa': entry.meta.get('ipa')
            }
            
            # Generate new USH address
            new_address, ush_metadata = self.ush_adapter.migrate_legacy_address(entry.address, entry_dict)
            
            # Update entry
            entry.address = new_address
            entry.meta.update(ush_metadata)
            entry.meta['migrated_from'] = entry.address
            entry.meta['migration_timestamp'] = datetime.now().isoformat()
            entry.updated_at = datetime.now()
            
            # Update statistics
            self.stats['migrations_performed'] += 1
            
            return entry
            
        except Exception as e:
            logger.error(f"Error migrating entry {entry.address}: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        stats = self.address_generator.get_statistics()
        stats.update(self.stats)
        return stats
    
    def find_cross_linguistic_equivalent(self, address: str, target_language: str) -> Optional[str]:
        """Find equivalent address in target language."""
        return self.ush_adapter.find_cross_linguistic_equivalent(address, target_language) 
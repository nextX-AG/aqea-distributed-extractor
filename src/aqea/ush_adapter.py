"""
Universal Semantic Hierarchy (USH) Adapter for AQEA.

This module provides the adapter functionality between the legacy AQEA addressing
and the new USH (Universal Semantic Hierarchy) addressing system.
"""

import logging
import hashlib
from typing import Dict, Any, Optional, List, Tuple
import re
from datetime import datetime
import random

from .ush_categories import (
    LANGUAGE_DOMAINS, 
    UNIVERSAL_CATEGORIES, 
    HIERARCHICAL_CLUSTERS,
    SEMANTIC_ROLES,
    POS_TO_UNIVERSAL_CATEGORY,
    CATEGORY_KEYWORDS,
    FREQUENCY_RANK_TO_CLUSTER
)

logger = logging.getLogger(__name__)


class USHAdapter:
    """
    Adapter for converting between legacy AQEA addressing and USH addressing.
    
    The USHAdapter provides methods to:
    1. Generate USH-compatible addresses
    2. Migrate legacy addresses to USH
    3. Find cross-linguistic equivalents
    4. Parse and validate USH addresses
    """
    
    def __init__(self, config: Dict[str, Any], language: str):
        """
        Initialize the USH adapter.
        
        Args:
            config: Configuration dictionary
            language: ISO 639-1 language code
        """
        self.config = config
        self.language = language.lower()
        
        # Map language to domain byte
        if self.language in LANGUAGE_DOMAINS:
            self.domain_byte = LANGUAGE_DOMAINS[self.language]
        else:
            # Default to user-defined domain (0xF0-0xFF)
            self.domain_byte = 0xF0
            logger.warning(f"Language '{language}' not in standard domains, using 0xF0")
        
        # Cross-linguistic mapping cache
        self.cross_linguistic_map = {}
        
        # Configure USH behavior
        self.ush_config = config.get('aqea', {})
        self.legacy_mode = self.ush_config.get('use_legacy_mode', False)
        self.enable_cross_linguistic = self.ush_config.get('enable_cross_linguistic', True)
        self.ush_version = self.ush_config.get('ush_version', '1.0')
        
        # Try to load language-specific frequency lists if available
        self.frequency_data = self._load_frequency_data()
        
        # Track cross-linguistic mappings
        self.concept_mappings = {}
    
    def _load_frequency_data(self) -> Dict[str, int]:
        """Load frequency data for the current language if available."""
        frequency_data = {}
        try:
            # This would be implemented to load from files or database
            # For now, return empty dict
            return frequency_data
        except Exception as e:
            logger.warning(f"Could not load frequency data for {self.language}: {e}")
            return {}
    
    def map_pos_to_universal_category(self, pos: str) -> Tuple[str, int]:
        """
        Map part of speech to universal semantic category.
        
        Args:
            pos: Part of speech (noun, verb, etc.)
            
        Returns:
            Tuple of (category_name, category_value)
        """
        pos = pos.lower()
        
        # Basic mapping
        if pos == 'noun':
            return 'physical_object', UNIVERSAL_CATEGORIES['physical_object']
        elif pos == 'verb':
            return 'action_verb', UNIVERSAL_CATEGORIES['action_verb']
        elif pos == 'adjective':
            return 'property', UNIVERSAL_CATEGORIES['property']
        elif pos == 'adverb':
            return 'manner', UNIVERSAL_CATEGORIES['manner']
        elif pos == 'preposition':
            return 'spatial_relation', UNIVERSAL_CATEGORIES['spatial_relation']
        elif pos == 'pronoun':
            return 'person', UNIVERSAL_CATEGORIES['person']
        elif pos == 'determiner':
            return 'quantifier', UNIVERSAL_CATEGORIES['quantifier']
        elif pos == 'conjunction':
            return 'logical_relation', UNIVERSAL_CATEGORIES['logical_relation']
        elif pos == 'interjection':
            return 'emotional_expression', UNIVERSAL_CATEGORIES['emotional_expression']
        else:
            # Default to abstract_concept
            return 'abstract_concept', UNIVERSAL_CATEGORIES['abstract_concept']
    
    def determine_semantic_category(self, entry: Dict[str, Any]) -> Tuple[str, int]:
        """
        Determine the semantic category based on word attributes.
        
        Args:
            entry: Dictionary containing word data
            
        Returns:
            Tuple of (category_name, category_value)
        """
        # Extract relevant attributes
        word = entry.get('word', '').lower()
        pos = entry.get('pos', '').lower()
        definitions = entry.get('definitions', [])
        labels = entry.get('labels', [])
        translations = entry.get('translations', {})
        
        # Convert definitions to lowercase string for easier matching
        def_text = ' '.join([d.lower() for d in definitions])
        
        # Category patterns (prioritized)
        patterns = [
            # Nature and physical world
            (r'water|liquid|h₂o|drink|river|lake|ocean|sea', 'natural_phenomenon', UNIVERSAL_CATEGORIES['natural_phenomenon']),
            (r'animal|creature|mammal|bird|fish|insect', 'animal', UNIVERSAL_CATEGORIES['animal']),
            (r'plant|tree|flower|grass|vegetable|fruit', 'plant', UNIVERSAL_CATEGORIES['plant']),
            (r'body|organ|limb|anatomy|head|heart|blood', 'body_part', UNIVERSAL_CATEGORIES['body_part']),
            (r'food|eat|drink|meal|cuisine|dish|meat|fruit', 'food_substance', UNIVERSAL_CATEGORIES['food_substance']),
            
            # Human and culture
            (r'person|human|people|man|woman|child|adult', 'person', UNIVERSAL_CATEGORIES['person']),
            (r'family|parent|mother|father|child|sibling', 'kinship', UNIVERSAL_CATEGORIES['kinship']),
            (r'tool|device|instrument|machine|apparatus', 'tool_instrument', UNIVERSAL_CATEGORIES['tool_instrument']),
            (r'building|structure|house|home|room|wall', 'building_structure', UNIVERSAL_CATEGORIES['building_structure']),
            (r'clothes|clothing|wear|garment|dress|hat', 'clothing', UNIVERSAL_CATEGORIES['clothing']),
            
            # Abstract concepts
            (r'time|period|duration|hour|minute|day|month', 'time_period', UNIVERSAL_CATEGORIES['time_period']),
            (r'number|quantity|amount|count|measure', 'quantity', UNIVERSAL_CATEGORIES['quantity']),
            (r'space|place|location|position|area|region', 'space_location', UNIVERSAL_CATEGORIES['space_location']),
            (r'color|colour|red|blue|green|yellow|hue', 'color_property', UNIVERSAL_CATEGORIES['color_property']),
            (r'think|thought|concept|idea|notion|theory', 'cognition', UNIVERSAL_CATEGORIES['cognition']),
            
            # Actions and events
            (r'move|movement|motion|go|come|travel|walk', 'motion_verb', UNIVERSAL_CATEGORIES['motion_verb']),
            (r'change|alter|transform|become|turn|convert', 'change_verb', UNIVERSAL_CATEGORIES['change_verb']),
            (r'communication|speak|talk|say|tell|express', 'communication_verb', UNIVERSAL_CATEGORIES['communication_verb']),
            (r'create|make|produce|generate|construct', 'creation_verb', UNIVERSAL_CATEGORIES['creation_verb']),
            (r'consume|use|utilize|apply|employ', 'consumption_verb', UNIVERSAL_CATEGORIES['consumption_verb']),
            
            # Properties and relations
            (r'big|large|small|tiny|size|dimension|volume', 'dimension_adj', UNIVERSAL_CATEGORIES['dimension_adj']),
            (r'good|bad|positive|negative|quality|value', 'evaluation_adj', UNIVERSAL_CATEGORIES['evaluation_adj']),
            (r'old|new|young|age|recent|ancient', 'age_adj', UNIVERSAL_CATEGORIES['age_adj']),
            (r'fast|slow|quick|speed|velocity|pace', 'speed_adj', UNIVERSAL_CATEGORIES['speed_adj']),
            (r'hard|soft|texture|consistency|tough', 'physical_property', UNIVERSAL_CATEGORIES['physical_property']),
            
            # Emotions and mental states
            (r'feel|feeling|emotion|mood|affect', 'emotion_noun', UNIVERSAL_CATEGORIES['emotion_noun']),
            (r'happy|sad|angry|joy|sorrow|love|hate', 'emotion_noun', UNIVERSAL_CATEGORIES['emotion_noun']),
            (r'know|knowledge|understand|comprehend', 'cognitive_state', UNIVERSAL_CATEGORIES['cognitive_state']),
            (r'perceive|perception|sense|sensation', 'perception_verb', UNIVERSAL_CATEGORIES['perception_verb']),
            (r'want|desire|wish|hope|intention', 'desire_verb', UNIVERSAL_CATEGORIES['desire_verb']),
            
            # Spatial and logical relations
            (r'in|inside|within|contain|interior', 'spatial_relation', UNIVERSAL_CATEGORIES['spatial_relation']),
            (r'on|above|over|top|surface|upon', 'spatial_relation', UNIVERSAL_CATEGORIES['spatial_relation']),
            (r'under|below|beneath|underneath', 'spatial_relation', UNIVERSAL_CATEGORIES['spatial_relation']),
            (r'between|among|amid|middle|center', 'spatial_relation', UNIVERSAL_CATEGORIES['spatial_relation']),
            (r'cause|effect|result|consequence|lead to', 'causal_relation', UNIVERSAL_CATEGORIES['causal_relation']),
        ]
        
        # Check for special labels
        if 'emotion' in labels or 'feeling' in labels:
            if pos == 'noun':
                return 'emotion_noun', UNIVERSAL_CATEGORIES['emotion_noun']
            else:
                return 'emotion_verb', UNIVERSAL_CATEGORIES['emotion_verb']
        
        if 'motion' in labels or 'movement' in labels:
            return 'motion_verb', UNIVERSAL_CATEGORIES['motion_verb']
        
        if 'nature' in labels or 'natural' in labels:
            return 'natural_phenomenon', UNIVERSAL_CATEGORIES['natural_phenomenon']
        
        if 'food' in labels or 'drink' in labels:
            return 'food_substance', UNIVERSAL_CATEGORIES['food_substance']
        
        if 'position' in labels or 'relation' in labels:
            if pos == 'preposition':
                return 'spatial_relation', UNIVERSAL_CATEGORIES['spatial_relation']
        
        if 'dimension' in labels or 'size' in labels:
            if pos == 'adjective':
                return 'dimension_adj', UNIVERSAL_CATEGORIES['dimension_adj']
        
        # Match definitions against patterns
        for pattern, category_name, category_value in patterns:
            if re.search(pattern, def_text):
                return category_name, category_value
        
        # Fall back to POS-based category if no pattern matched
        return self.map_pos_to_universal_category(pos)
    
    def determine_hierarchical_cluster(self, entry: Dict[str, Any]) -> Tuple[str, int]:
        """
        Determine the hierarchical cluster based on word attributes.
        
        Args:
            entry: Dictionary containing word data
            
        Returns:
            Tuple of (cluster_name, cluster_value)
        """
        # Extract frequency data if available
        frequency = entry.get('frequency', 0)
        pos = entry.get('pos', '').lower()
        word = entry.get('word', '').lower()
        translations = entry.get('translations', {})
        
        # If explicit frequency provided, use it
        if frequency > 0:
            if frequency > 2000:
                return 'ultra_frequent', HIERARCHICAL_CLUSTERS['ultra_frequent']
            elif frequency > 1800:
                return 'very_frequent', HIERARCHICAL_CLUSTERS['very_frequent']
            elif frequency > 1500:
                return 'frequent', HIERARCHICAL_CLUSTERS['frequent']
            elif frequency > 1200:
                return 'medium_frequent', HIERARCHICAL_CLUSTERS['medium_frequent']
            elif frequency > 900:
                return 'less_frequent', HIERARCHICAL_CLUSTERS['less_frequent']
            elif frequency > 600:
                return 'infrequent', HIERARCHICAL_CLUSTERS['infrequent']
            elif frequency > 300:
                return 'rare', HIERARCHICAL_CLUSTERS['rare']
            else:
                return 'very_rare', HIERARCHICAL_CLUSTERS['very_rare']
        
        # Estimate frequency based on heuristics
        score = 1000  # Base score
        
        # 1. Word length (shorter words tend to be more frequent)
        score += max(0, 10 - len(word)) * 50
        
        # 2. Number of translations (more common words have more translations)
        translation_count = sum(len(v) for v in translations.values())
        score += min(translation_count * 30, 300)
        
        # 3. Part of speech frequency distribution
        pos_frequency = {
            'article': 500,      # Very frequent
            'pronoun': 400,      # Very frequent
            'preposition': 350,  # Very frequent
            'conjunction': 300,  # Very frequent
            'verb': 200,         # Frequent
            'adverb': 150,       # Frequent
            'adjective': 100,    # Medium
            'noun': 50,          # Less frequent as a category (many nouns)
            'interjection': -50, # Infrequent
        }
        score += pos_frequency.get(pos, 0)
        
        # 4. Add some controlled randomness for variety
        score += random.randint(-50, 50)
        
        # Map score to cluster
        if score > 1800:
            return 'ultra_frequent', HIERARCHICAL_CLUSTERS['ultra_frequent']
        elif score > 1600:
            return 'very_frequent', HIERARCHICAL_CLUSTERS['very_frequent']
        elif score > 1400:
            return 'frequent', HIERARCHICAL_CLUSTERS['frequent']
        elif score > 1200:
            return 'medium_frequent', HIERARCHICAL_CLUSTERS['medium_frequent']
        elif score > 1000:
            return 'less_frequent', HIERARCHICAL_CLUSTERS['less_frequent']
        elif score > 800:
            return 'infrequent', HIERARCHICAL_CLUSTERS['infrequent']
        elif score > 600:
            return 'rare', HIERARCHICAL_CLUSTERS['rare']
        else:
            return 'very_rare', HIERARCHICAL_CLUSTERS['very_rare']
    
    def determine_semantic_role(self, entry: Dict[str, Any]) -> int:
        """
        Determine the semantic role (A2 byte most significant bits).
        
        Args:
            entry: Dictionary containing word data
            
        Returns:
            Semantic role value (upper 2 bits of A2 byte)
        """
        # This could be expanded with more sophisticated analysis
        pos = entry.get('pos', '').lower()
        
        if pos == 'noun':
            return 0x00  # 00xxxxxx - Default noun role
        elif pos == 'verb':
            return 0x40  # 01xxxxxx - Default verb role
        elif pos == 'adjective' or pos == 'adverb':
            return 0x80  # 10xxxxxx - Default modifier role
        else:
            return 0xC0  # 11xxxxxx - Other functional roles
    
    def generate_embedding_based_a2(self, entry: Dict[str, Any], semantic_role: int) -> int:
        """
        Generate the A2 byte based on semantic properties.
        
        Args:
            entry: Dictionary containing word data
            semantic_role: The semantic role value (upper 2 bits)
            
        Returns:
            A2 byte value
        """
        # In a production system, this could use actual word embeddings
        # For now, we'll use a hash-based approach
        
        word = entry.get('word', '').lower()
        definitions = ' '.join(entry.get('definitions', []))
        
        # Create a simple hash from the word and its primary definition
        hash_base = hash(word + definitions[:20]) & 0x3F  # 6 bits (0-63)
        
        # Combine with semantic role
        return semantic_role | hash_base
    
    def generate_ush_address(self, entry: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a USH-compatible address for an entry.
        
        Args:
            entry: Dictionary containing word data
            
        Returns:
            Tuple of (ush_address, metadata)
        """
        # 1. Determine domain byte (AA)
        aa = self.domain_byte
        
        # 2. Determine universal semantic category (QQ)
        category_name, qq = self.determine_semantic_category(entry)
        
        # 3. Determine hierarchical cluster (EE)
        cluster_name, ee = self.determine_hierarchical_cluster(entry)
        
        # 4. Determine semantic role and element ID (A2)
        semantic_role = self.determine_semantic_role(entry)
        a2 = self.generate_embedding_based_a2(entry, semantic_role)
        
        # 5. Format the address string
        address = f"0x{aa:02X}:{qq:02X}:{ee:02X}:{a2:02X}"
        
        # 6. Create metadata
        # Add estimated frequency for metadata
        if 'frequency' not in entry:
            # Map cluster to approximate frequency value
            frequency_map = {
                'ultra_frequent': 2100,
                'very_frequent': 1900,
                'frequent': 1650, 
                'medium_frequent': 1400,
                'less_frequent': 1150,
                'infrequent': 900,
                'rare': 650,
                'very_rare': 400
            }
            frequency = frequency_map.get(cluster_name, 1000)
        else:
            frequency = entry.get('frequency')
        
        metadata = {
            'ush_category': category_name,
            'ush_cluster': cluster_name,
            'frequency': frequency,
            'conversion_timestamp': datetime.now().isoformat(),
            'address_format': 'ush',
            'ush_compatible': True,
            'ush_version': self.ush_version
        }
        
        return address, metadata
    
    def parse_ush_address(self, address: str) -> Tuple[int, int, int, int]:
        """
        Parse a USH address into its component bytes.
        
        Args:
            address: USH address string (e.g., "0x20:08:10:42")
            
        Returns:
            Tuple of (aa, qq, ee, a2) as integers
        """
        # Remove 0x prefix if present
        if address.startswith('0x'):
            address = address[2:]
        
        # Split by colon
        parts = address.split(':')
        if len(parts) != 4:
            raise ValueError(f"Invalid USH address format: {address}")
        
        # Convert each part to integer
        try:
            aa = int(parts[0], 16)
            qq = int(parts[1], 16)
            ee = int(parts[2], 16)
            a2 = int(parts[3], 16)
            return aa, qq, ee, a2
        except ValueError:
            raise ValueError(f"Invalid USH address components: {address}")
    
    def is_ush_compatible(self, address: str) -> bool:
        """
        Check if an address is USH-compatible.
        
        Args:
            address: AQEA address string
            
        Returns:
            Boolean indicating USH compatibility
        """
        try:
            aa, qq, ee, a2 = self.parse_ush_address(address)
            
            # Check if category and cluster are valid
            category_valid = qq in [v for v in UNIVERSAL_CATEGORIES.values()]
            cluster_valid = ee in [v for v in HIERARCHICAL_CLUSTERS.values()]
            
            return category_valid and cluster_valid
        except ValueError:
            return False
    
    def find_cross_linguistic_equivalent(self, address: str, target_language: str) -> Optional[str]:
        """
        Find cross-linguistic equivalent of an address in target language.
        
        Args:
            address: Source AQEA address
            target_language: Target language code
            
        Returns:
            Equivalent address in target language, if found
        """
        if not self.enable_cross_linguistic:
            return None
        
        # Check if mapping exists in cache
        key = f"{address}:{target_language}"
        if key in self.cross_linguistic_map:
            return self.cross_linguistic_map[key]
        
        # Get target language domain
        if target_language in LANGUAGE_DOMAINS:
            target_domain = LANGUAGE_DOMAINS[target_language]
        else:
            target_domain = 0xF0  # Default user domain
        
        # Parse source address
        try:
            aa, qq, ee, a2 = self.parse_ush_address(address)
            
            # Create target address with same QQ:EE:A2 but different domain
            target_address = f"0x{target_domain:02X}:{qq:02X}:{ee:02X}:{a2:02X}"
            
            # Cache the mapping
            self.cross_linguistic_map[key] = target_address
            
            return target_address
        except ValueError:
            return None
    
    def register_cross_linguistic_mapping(self, source_address: str, target_language: str, 
                                         target_word: str) -> bool:
        """
        Register a cross-linguistic mapping between addresses.
        
        Args:
            source_address: Source AQEA address
            target_language: Target language code
            target_word: Target word
            
        Returns:
            Success boolean
        """
        if not self.enable_cross_linguistic:
            return False
        
        # Create a proxy target address
        target_address = self.find_cross_linguistic_equivalent(source_address, target_language)
        if not target_address:
            return False
        
        # In a real implementation, this would store the mapping in a database
        key = f"{source_address}:{target_language}"
        self.cross_linguistic_map[key] = target_address
        
        # Also store reverse mapping
        reverse_key = f"{target_address}:{self.language}"
        self.cross_linguistic_map[reverse_key] = source_address
        
        return True
    
    def migrate_legacy_address(self, legacy_address: str, entry: Dict[str, Any]) -> str:
        """
        Migrate a legacy AQEA address to USH format.
        
        Args:
            legacy_address: Legacy AQEA address
            entry: Dictionary containing word data
            
        Returns:
            USH-compatible address
        """
        # Parse legacy address
        try:
            aa, qq, ee, a2 = self.parse_ush_address(legacy_address)
            
            # Keep the domain byte
            # Map the other bytes to USH format
            ush_address, _ = self.generate_ush_address(entry)
            
            # Extract the USH components
            _, ush_qq, ush_ee, ush_a2 = self.parse_ush_address(ush_address)
            
            # Create hybrid address with domain from legacy and QQ:EE:A2 from USH
            hybrid_address = f"0x{aa:02X}:{ush_qq:02X}:{ush_ee:02X}:{ush_a2:02X}"
            
            return hybrid_address
        except ValueError:
            # If parsing fails, generate a completely new address
            ush_address, _ = self.generate_ush_address(entry)
            return ush_address
    
    def get_ush_category_description(self, qq: int) -> str:
        """Get human-readable description of USH category."""
        for name, value in UNIVERSAL_CATEGORIES.items():
            if value == qq:
                return name.replace('_', ' ').title()
        return f"Unknown Category (0x{qq:02X})"
    
    def get_ush_cluster_description(self, ee: int) -> str:
        """Get human-readable description of USH cluster."""
        for name, value in HIERARCHICAL_CLUSTERS.items():
            if value == ee:
                return name.replace('_', ' ').title()
        return f"Unknown Cluster (0x{ee:02X})"
    
    def get_semantic_role_description(self, a2: int) -> Optional[str]:
        """Get human-readable description of semantic role if A2 is a special value."""
        if a2 <= 0x0F:
            for name, value in SEMANTIC_ROLES.items():
                if value == a2:
                    return name.replace('_', ' ').title()
        return None 
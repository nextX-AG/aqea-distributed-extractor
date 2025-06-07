"""
Test USH Integration

Tests the integration of Universal Semantic Hierarchy (USH) into AQEA addressing.
"""

import asyncio
import unittest
import sys
import os

# Füge das Hauptverzeichnis zum Pfad hinzu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aqea import USHConverter, USHAdapter, UNIVERSAL_CATEGORIES, HIERARCHICAL_CLUSTERS


class TestUSHIntegration(unittest.TestCase):
    """Test suite for USH integration in AQEA addressing."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = {
            'aqea': {
                'use_legacy_mode': False,
                'enable_cross_linguistic': True
            }
        }
        self.language = 'de'  # German
        self.ush_adapter = USHAdapter(self.config, self.language)
        self.ush_converter = USHConverter(self.config, self.language)
        
        # Sample entry
        self.sample_entry = {
            'word': 'Wasser',
            'pos': 'noun',
            'definitions': ['H₂O, drinking liquid', 'A clear, colorless liquid that falls as rain'],
            'labels': ['nature', 'fluid'],
            'ipa': 'ˈvasɐ',
            'translations': {
                'en': ['water'],
                'fr': ['eau'],
                'es': ['agua']
            }
        }
    
    def test_ush_adapter_initialization(self):
        """Test USH adapter initialization."""
        self.assertEqual(self.ush_adapter.language, 'de')
        self.assertEqual(self.ush_adapter.domain_byte, 0x20)  # German = 0x20
    
    def test_universal_category_mapping(self):
        """Test mapping POS to universal categories."""
        category_name, category_value = self.ush_adapter.map_pos_to_universal_category('noun')
        self.assertEqual(category_name, 'physical_object')
        self.assertEqual(category_value, UNIVERSAL_CATEGORIES['physical_object'])
        
        category_name, category_value = self.ush_adapter.map_pos_to_universal_category('verb')
        self.assertEqual(category_name, 'action_verb')
        self.assertEqual(category_value, UNIVERSAL_CATEGORIES['action_verb'])
    
    def test_semantic_category_detection(self):
        """Test semantic category detection based on content."""
        category_name, category_value = self.ush_adapter.determine_semantic_category(self.sample_entry)
        
        # "Wasser" with definition containing "water" should be classified as "natural_phenomenon"
        self.assertEqual(category_name, 'natural_phenomenon')
        self.assertEqual(category_value, UNIVERSAL_CATEGORIES['natural_phenomenon'])
    
    def test_hierarchical_cluster_assignment(self):
        """Test hierarchical cluster assignment."""
        cluster_name, cluster_value = self.ush_adapter.determine_hierarchical_cluster(self.sample_entry)
        
        # "Wasser" is a common word, should be in a frequent cluster
        self.assertIn('frequent', cluster_name)
        self.assertIn(cluster_value, [
            HIERARCHICAL_CLUSTERS['ultra_frequent'],
            HIERARCHICAL_CLUSTERS['very_frequent'],
            HIERARCHICAL_CLUSTERS['frequent'],
            HIERARCHICAL_CLUSTERS['medium_frequent']  # Hinzugefügt, da es auch in diese Kategorie fallen kann
        ])
    
    def test_ush_address_generation(self):
        """Test USH address generation."""
        address, metadata = self.ush_adapter.generate_ush_address(self.sample_entry)
        
        # Address format validation
        self.assertTrue(self.ush_adapter.is_ush_compatible(address))
        
        # Parse components
        aa, qq, ee, a2 = self.ush_adapter.parse_ush_address(address)
        
        # Check domain byte (German)
        self.assertEqual(aa, 0x20)
        
        # Check category byte (should be natural_phenomenon = 0x08)
        self.assertEqual(qq, UNIVERSAL_CATEGORIES['natural_phenomenon'])
        
        # Check cluster byte (should be one of the frequency clusters)
        self.assertIn(ee, [
            HIERARCHICAL_CLUSTERS['ultra_frequent'],
            HIERARCHICAL_CLUSTERS['very_frequent'],
            HIERARCHICAL_CLUSTERS['frequent'],
            HIERARCHICAL_CLUSTERS['medium_frequent']  # Hinzugefügt, da es auch in diese Kategorie fallen kann
        ])
        
        # Check metadata
        self.assertEqual(metadata['ush_category'], 'natural_phenomenon')
        self.assertIn('ush_cluster', metadata)
        self.assertEqual(metadata['ush_version'], '1.0')
    
    def test_cross_linguistic_mapping(self):
        """Test cross-linguistic mapping."""
        # Generate address for German "Wasser"
        address, _ = self.ush_adapter.generate_ush_address(self.sample_entry)
        
        # Register cross-linguistic mapping
        result = self.ush_adapter.register_cross_linguistic_mapping(address, 'en', 'water')
        self.assertTrue(result)
        
        # Find equivalent in English
        english_address = self.ush_adapter.find_cross_linguistic_equivalent(address, 'en')
        self.assertIsNotNone(english_address)
        
        # Parse components
        aa, qq, ee, a2 = self.ush_adapter.parse_ush_address(english_address)
        
        # Should have English domain byte
        self.assertEqual(aa, 0x21)  # English = 0x21
        
        # But same QQ:EE:A2 pattern as original
        original_aa, original_qq, original_ee, original_a2 = self.ush_adapter.parse_ush_address(address)
        self.assertEqual(qq, original_qq)
        self.assertEqual(ee, original_ee)
        self.assertEqual(a2, original_a2)
    
    def test_ush_converter(self):
        """Test full USH converter functionality."""
        # Run in asyncio event loop
        loop = asyncio.get_event_loop()
        aqea_entry = loop.run_until_complete(self.ush_converter.convert(self.sample_entry))
        
        # Check AQEA entry
        self.assertIsNotNone(aqea_entry)
        self.assertEqual(aqea_entry.label, 'Wasser')
        self.assertEqual(aqea_entry.domain, '0x20')  # German
        
        # Check USH metadata
        self.assertEqual(aqea_entry.meta['ush_category'], 'natural_phenomenon')
        self.assertIn('ush_cluster', aqea_entry.meta)
        self.assertEqual(aqea_entry.meta['ush_version'], '1.0')
        self.assertEqual(aqea_entry.meta['address_format'], 'ush')
        self.assertTrue(aqea_entry.meta['ush_compatible'])
        
        # Description should include USH categorization
        self.assertIn('USH:', aqea_entry.description)
        self.assertIn('Natural Phenomenon', aqea_entry.description)


if __name__ == '__main__':
    unittest.main() 
"""
Unit tests for AQEA Converter System
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from src.aqea.converter import AQEAConverter
from src.aqea.address_generator import AddressGenerator
from src.aqea.schema import AQEAEntry
from src.utils.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    return config


@pytest.fixture
def sample_entry():
    """Create a sample dictionary entry."""
    return {
        'word': 'Wasser',
        'language': 'de',
        'pos': 'noun',
        'definitions': [
            'Eine chemische Verbindung aus Wasserstoff und Sauerstoff',
            'Flüssigkeit zum Trinken'
        ],
        'ipa': 'ˈvasər',
        'forms': ['Wasser', 'Wassers', 'Wässer', 'Wässern'],
        'labels': ['chemistry', 'nature']
    }


class TestAQEAConverter:
    """Test cases for AQEAConverter."""
    
    def test_language_domain_mapping(self, mock_config):
        """Test language domain byte mapping."""
        converter = AQEAConverter(mock_config, 'de')
        assert converter.domain_byte == 0x20
        
        converter = AQEAConverter(mock_config, 'en')
        assert converter.domain_byte == 0x21
        
        # Test unsupported language
        with pytest.raises(ValueError):
            AQEAConverter(mock_config, 'unsupported')
    
    def test_pos_category_mapping(self, mock_config):
        """Test part-of-speech category mapping."""
        converter = AQEAConverter(mock_config, 'de')
        
        assert converter.POS_CATEGORIES['noun'] == 0x01
        assert converter.POS_CATEGORIES['verb'] == 0x02
        assert converter.POS_CATEGORIES['adjective'] == 0x03
        assert converter.POS_CATEGORIES['unknown'] == 0xFF
    
    def test_semantic_categorization(self, mock_config, sample_entry):
        """Test semantic category determination."""
        converter = AQEAConverter(mock_config, 'de')
        
        # Test nature category
        category = converter._determine_semantic_category(sample_entry)
        assert category == converter.SEMANTIC_CATEGORIES['nature']
        
        # Test animal category
        animal_entry = {
            'word': 'Hund',
            'definitions': ['Ein Haustier, ein Säugetier'],
            'labels': ['animal', 'mammal']
        }
        category = converter._determine_semantic_category(animal_entry)
        assert category == converter.SEMANTIC_CATEGORIES['animals']
    
    @pytest.mark.asyncio
    async def test_address_generation(self, mock_config, sample_entry):
        """Test AQEA address generation."""
        converter = AQEAConverter(mock_config, 'de')
        
        with patch.object(converter.address_generator, 'get_next_element_id', return_value=0x01):
            address = await converter._generate_address(sample_entry)
            
            # Should be German domain (0x20), noun (0x01), nature (0x01), element 0x01
            assert address == "0x20:01:01:01"
    
    @pytest.mark.asyncio
    async def test_entry_conversion(self, mock_config, sample_entry):
        """Test complete entry conversion to AQEA format."""
        converter = AQEAConverter(mock_config, 'de')
        
        with patch.object(converter.address_generator, 'get_next_element_id', return_value=0x01):
            aqea_entry = await converter.convert(sample_entry)
            
            assert isinstance(aqea_entry, AQEAEntry)
            assert aqea_entry.address == "0x20:01:01:01"
            assert aqea_entry.label == "Wasser"
            assert aqea_entry.domain == "0x20"
            assert aqea_entry.lang_ui == "de"
            assert aqea_entry.status == "active"
            
            # Check meta data
            assert aqea_entry.meta['lemma'] == 'Wasser'
            assert aqea_entry.meta['ipa'] == 'ˈvasər'
            assert aqea_entry.meta['pos'] == 'noun'
            assert len(aqea_entry.meta['definitions']) <= 3
            assert len(aqea_entry.meta['forms']) <= 5
    
    def test_description_creation(self, mock_config, sample_entry):
        """Test description creation."""
        converter = AQEAConverter(mock_config, 'de')
        
        description = converter._create_description(sample_entry)
        
        assert 'German' in description
        assert 'noun' in description
        assert 'Wasser' in description
        assert 'ˈvasər' in description  # IPA should be included
    
    def test_frequency_estimation(self, mock_config):
        """Test word frequency estimation."""
        converter = AQEAConverter(mock_config, 'de')
        
        # Short word should have higher frequency
        short_entry = {'word': 'ich', 'pos': 'pronoun', 'definitions': ['I']}
        short_freq = converter._estimate_frequency(short_entry)
        
        # Long word should have lower frequency
        long_entry = {'word': 'Antidisestablishmentarianism', 'pos': 'noun', 'definitions': ['Long word']}
        long_freq = converter._estimate_frequency(long_entry)
        
        assert short_freq > long_freq
    
    @pytest.mark.asyncio
    async def test_empty_word_handling(self, mock_config):
        """Test handling of empty or invalid entries."""
        converter = AQEAConverter(mock_config, 'de')
        
        # Empty word
        empty_entry = {'word': '', 'pos': 'noun'}
        result = await converter.convert(empty_entry)
        assert result is None
        
        # Missing word
        missing_entry = {'pos': 'noun'}
        result = await converter.convert(missing_entry)
        assert result is None


class TestAddressGenerator:
    """Test cases for AddressGenerator."""
    
    def test_initialization(self):
        """Test address generator initialization."""
        generator = AddressGenerator('de')
        assert generator.language == 'de'
        assert len(generator.allocated_addresses) == 0
        assert len(generator.word_to_address) == 0
    
    @pytest.mark.asyncio
    async def test_element_id_generation(self):
        """Test element ID generation."""
        generator = AddressGenerator('de')
        
        # First allocation should work
        element_id = await generator.get_next_element_id(0x20, 0x01, 0x01, 'test')
        assert 0 <= element_id < 0xFE
        
        # Same word should return same ID
        element_id2 = await generator.get_next_element_id(0x20, 0x01, 0x01, 'test')
        assert element_id == element_id2
        
        # Different word should get different ID
        element_id3 = await generator.get_next_element_id(0x20, 0x01, 0x01, 'different')
        assert element_id3 != element_id
    
    def test_address_availability(self):
        """Test address availability checking."""
        generator = AddressGenerator('de')
        
        # Address should be available initially
        assert generator.is_address_available(0x20, 0x01, 0x01, 0x01)
        
        # Reserve address
        assert generator.reserve_address(0x20, 0x01, 0x01, 0x01)
        
        # Should no longer be available
        assert not generator.is_address_available(0x20, 0x01, 0x01, 0x01)
        
        # Double reservation should fail
        assert not generator.reserve_address(0x20, 0x01, 0x01, 0x01)
    
    def test_category_usage_statistics(self):
        """Test category usage statistics."""
        generator = AddressGenerator('de')
        
        # Reserve some addresses
        generator.reserve_address(0x20, 0x01, 0x01, 0x01)
        generator.reserve_address(0x20, 0x01, 0x01, 0x02)
        
        usage = generator.get_category_usage(0x20, 0x01, 0x01)
        
        assert usage['allocated_count'] == 2
        assert usage['available_count'] == 252  # 254 - 2
        assert usage['utilization_percent'] > 0
        assert not usage['is_full']
    
    def test_statistics(self):
        """Test comprehensive statistics."""
        generator = AddressGenerator('de')
        
        # Generate some addresses
        generator.reserve_address(0x20, 0x01, 0x01, 0x01)
        generator.reserve_address(0x20, 0x01, 0x02, 0x01)
        
        stats = generator.get_statistics()
        
        assert stats['language'] == 'de'
        assert stats['total_categories_used'] == 2
        assert stats['total_addresses_allocated'] == 2
        assert 'efficiency_metrics' in stats
    
    def test_export_import_mappings(self):
        """Test export and import of address mappings."""
        generator = AddressGenerator('de')
        
        # Generate some data
        generator.reserve_address(0x20, 0x01, 0x01, 0x01)
        generator.word_to_address['test'] = '0x20:01:01:01'
        
        # Export
        exported = generator.export_mappings()
        
        # Create new generator and import
        new_generator = AddressGenerator('de')
        assert new_generator.import_mappings(exported)
        
        # Verify data was imported
        assert not new_generator.is_address_available(0x20, 0x01, 0x01, 0x01)
        assert 'test' in new_generator.word_to_address
    
    def test_address_format_validation(self):
        """Test address format validation."""
        generator = AddressGenerator('de')
        
        # Valid format
        assert generator.validate_address_format('0x20:01:01:01')
        
        # Invalid formats
        assert not generator.validate_address_format('20:01:01:01')  # Missing 0x
        assert not generator.validate_address_format('0x20:01:01')   # Too few parts
        assert not generator.validate_address_format('0x20:01:01:01:02')  # Too many parts
        assert not generator.validate_address_format('0xZZ:01:01:01')  # Invalid hex


class TestAQEAEntry:
    """Test cases for AQEAEntry schema."""
    
    def test_entry_creation(self):
        """Test AQEA entry creation."""
        entry = AQEAEntry(
            address='0x20:01:01:01',
            label='Test',
            description='Test entry',
            domain='0x20'
        )
        
        assert entry.address == '0x20:01:01:01'
        assert entry.label == 'Test'
        assert entry.status == 'active'  # Default value
        assert isinstance(entry.created_at, datetime)
    
    def test_validation(self):
        """Test entry validation."""
        # Valid entry
        entry = AQEAEntry(
            address='0x20:01:01:01',
            label='Test',
            description='Test entry',
            domain='0x20'
        )
        errors = entry.validate()
        assert len(errors) == 0
        
        # Invalid entry - missing required fields
        invalid_entry = AQEAEntry(
            address='',
            label='',
            description='',
            domain=''
        )
        errors = invalid_entry.validate()
        assert len(errors) > 0
    
    def test_dict_conversion(self):
        """Test conversion to/from dictionary."""
        entry = AQEAEntry(
            address='0x20:01:01:01',
            label='Test',
            description='Test entry',
            domain='0x20'
        )
        
        # Convert to dict
        entry_dict = entry.to_dict()
        assert entry_dict['address'] == '0x20:01:01:01'
        assert entry_dict['label'] == 'Test'
        
        # Convert back from dict
        restored_entry = AQEAEntry.from_dict(entry_dict)
        assert restored_entry.address == entry.address
        assert restored_entry.label == entry.label
    
    def test_json_conversion(self):
        """Test JSON serialization/deserialization."""
        entry = AQEAEntry(
            address='0x20:01:01:01',
            label='Test',
            description='Test entry',
            domain='0x20'
        )
        
        # Convert to JSON
        json_str = entry.to_json()
        assert '0x20:01:01:01' in json_str
        
        # Convert back from JSON
        restored_entry = AQEAEntry.from_json(json_str)
        assert restored_entry.address == entry.address
    
    def test_byte_extraction(self):
        """Test extraction of individual bytes from address."""
        entry = AQEAEntry(
            address='0x20:01:02:03',
            label='Test',
            description='Test entry',
            domain='0x20'
        )
        
        assert entry.get_domain_byte() == 0x20
        assert entry.get_category_byte() == 0x01
        assert entry.get_subcategory_byte() == 0x02
        assert entry.get_element_byte() == 0x03
    
    def test_relations(self):
        """Test relation management."""
        entry = AQEAEntry(
            address='0x20:01:01:01',
            label='Test',
            description='Test entry',
            domain='0x20'
        )
        
        # Add relation
        entry.add_relation('synonym_of', '0x20:01:01:02', confidence=0.9)
        assert len(entry.relations) == 1
        
        # Get relations by type
        synonyms = entry.get_relations_by_type('synonym_of')
        assert len(synonyms) == 1
        assert synonyms[0]['target'] == '0x20:01:01:02'
        
        # Remove relation
        assert entry.remove_relation('synonym_of', '0x20:01:01:02')
        assert len(entry.relations) == 0
    
    def test_meta_management(self):
        """Test metadata management."""
        entry = AQEAEntry(
            address='0x20:01:01:01',
            label='Test',
            description='Test entry',
            domain='0x20'
        )
        
        # Update meta
        entry.update_meta('frequency', 1500)
        assert entry.get_meta('frequency') == 1500
        assert entry.get_meta('nonexistent', 'default') == 'default'


if __name__ == '__main__':
    pytest.main([__file__]) 
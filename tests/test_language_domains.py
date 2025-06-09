#!/usr/bin/env python3
"""
Test Suite for AQEA Language Family Blocks (0xA0-0xDF)
Based on UNIVERSAL_LANGUAGE_DOMAIN_FINAL.md
"""

import pytest
import asyncio
from src.aqea.language_mappings import (
    encode_language,
    decode_language, 
    get_language_family,
    get_language_info,
    list_supported_languages,
    list_families,
    get_family_languages,
    is_valid_language_aa,
    validate_mappings,
    get_statistics,
    UnsupportedLanguageError,
    InvalidAddressError
)
from src.aqea.converter import AQEAConverter


class TestLanguageMappings:
    """Test Language Mapping functionality."""
    
    def test_encode_language_success(self):
        """Test successful language encoding."""
        # Germanic family
        assert encode_language('deu') == 0xA0
        assert encode_language('eng') == 0xA1
        assert encode_language('nld') == 0xA2
        
        # Romance family  
        assert encode_language('fra') == 0xB0
        assert encode_language('spa') == 0xB1
        assert encode_language('ita') == 0xB2
        
        # Slavic family
        assert encode_language('rus') == 0xC0
        assert encode_language('pol') == 0xC1
        assert encode_language('ces') == 0xC2
        
        # Asian family
        assert encode_language('cmn') == 0xD0
        assert encode_language('jpn') == 0xD2
        assert encode_language('kor') == 0xD3
    
    def test_encode_language_failure(self):
        """Test language encoding with unsupported languages."""
        with pytest.raises(UnsupportedLanguageError):
            encode_language('xyz')
        
        with pytest.raises(UnsupportedLanguageError):
            encode_language('invalid')
    
    def test_decode_language_success(self):
        """Test successful language decoding."""
        # Germanic family
        assert decode_language(0xA0) == 'deu'
        assert decode_language(0xA1) == 'eng'
        assert decode_language(0xA2) == 'nld'
        
        # Romance family
        assert decode_language(0xB0) == 'fra'
        assert decode_language(0xB1) == 'spa'
        assert decode_language(0xB2) == 'ita'
        
        # Slavic family
        assert decode_language(0xC0) == 'rus'
        assert decode_language(0xC1) == 'pol'
        assert decode_language(0xC2) == 'ces'
        
        # Asian family  
        assert decode_language(0xD0) == 'cmn'
        assert decode_language(0xD2) == 'jpn'
        assert decode_language(0xD3) == 'kor'
    
    def test_decode_language_failure(self):
        """Test language decoding with invalid AA-bytes."""
        with pytest.raises(InvalidAddressError):
            decode_language(0x20)  # Old language range
            
        with pytest.raises(InvalidAddressError):
            decode_language(0xFF)  # Invalid range
            
        with pytest.raises(InvalidAddressError):
            decode_language(0xAA)  # Reserved slot
    
    def test_family_classification(self):
        """Test language family classification."""
        # Germanic
        assert get_language_family('deu') == 'Germanic'
        assert get_language_family('eng') == 'Germanic'
        assert get_language_family('nld') == 'Germanic'
        
        # Romance
        assert get_language_family('fra') == 'Romance'
        assert get_language_family('spa') == 'Romance'
        assert get_language_family('ita') == 'Romance'
        
        # Slavic
        assert get_language_family('rus') == 'Slavic'
        assert get_language_family('pol') == 'Slavic'
        assert get_language_family('ces') == 'Slavic'
        
        # Asian
        assert get_language_family('cmn') == 'Asian'
        assert get_language_family('jpn') == 'Asian'
        assert get_language_family('kor') == 'Asian'
    
    def test_language_info(self):
        """Test language information retrieval."""
        # German
        deu_info = get_language_info('deu')
        assert deu_info['name_english'] == 'German'
        assert deu_info['name_native'] == 'Deutsch'
        assert deu_info['family'] == 'Germanic'
        assert deu_info['aa_byte'] == 0xA0
        assert deu_info['aa_hex'] == '0xA0'
        
        # English
        eng_info = get_language_info('eng')
        assert eng_info['name_english'] == 'English'
        assert eng_info['speakers'] == 1_500_000_000
        assert eng_info['family'] == 'Germanic'
        assert eng_info['aa_byte'] == 0xA1
    
    def test_family_functions(self):
        """Test family-related functions."""
        families = list_families()
        assert 'Germanic' in families
        assert 'Romance' in families
        assert 'Slavic' in families
        assert 'Asian' in families
        
        # Test family languages
        germanic_langs = get_family_languages('Germanic')
        assert 'deu' in germanic_langs
        assert 'eng' in germanic_langs
        
        romance_langs = get_family_languages('Romance')
        assert 'fra' in romance_langs
        assert 'spa' in romance_langs
    
    def test_validation_functions(self):
        """Test validation functions."""
        # Valid language AA-bytes
        assert is_valid_language_aa(0xA0) == True
        assert is_valid_language_aa(0xB5) == True
        assert is_valid_language_aa(0xCF) == True
        assert is_valid_language_aa(0xDF) == True
        
        # Invalid AA-bytes
        assert is_valid_language_aa(0x20) == False  # Old range
        assert is_valid_language_aa(0x9F) == False  # Before range
        assert is_valid_language_aa(0xE0) == False  # After range
        assert is_valid_language_aa(0xFF) == False  # System reserved
    
    def test_statistics(self):
        """Test statistics generation."""
        stats = get_statistics()
        
        assert stats['total_languages'] > 40
        assert stats['total_speakers'] > 4_000_000_000
        
        # Check family statistics
        assert 'Germanic' in stats['families']
        assert 'Romance' in stats['families']
        assert 'Slavic' in stats['families']
        assert 'Asian' in stats['families']
        
        # Check range usage
        assert 'Germanic' in stats['aa_range_usage']
        assert stats['aa_range_usage']['Germanic']['total'] == 16
        assert stats['aa_range_usage']['Germanic']['used'] > 5
    
    def test_mapping_validation(self):
        """Test that all mappings are valid."""
        # This should not raise any exceptions
        validate_mappings()


class TestAQEAConverterIntegration:
    """Test AQEA Converter integration with new language mappings."""
    
    @pytest.fixture
    def test_config(self):
        return {
            'aqea': {
                'use_legacy_mode': False
            }
        }
    
    def test_converter_initialization_iso_639_1(self, test_config):
        """Test converter initialization with ISO 639-1 codes."""
        # Test Germanic family
        converter_de = AQEAConverter(test_config, 'de', database=None, worker_id="test")
        assert converter_de.language == 'deu'
        assert converter_de.domain_byte == 0xA0
        assert converter_de.language_family == 'Germanic'
        
        # Test Romance family
        converter_fr = AQEAConverter(test_config, 'fr', database=None, worker_id="test")
        assert converter_fr.language == 'fra'
        assert converter_fr.domain_byte == 0xB0
        assert converter_fr.language_family == 'Romance'
    
    def test_converter_initialization_iso_639_3(self, test_config):
        """Test converter initialization with ISO 639-3 codes."""
        # Test Slavic family
        converter_rus = AQEAConverter(test_config, 'rus', database=None, worker_id="test")
        assert converter_rus.language == 'rus'
        assert converter_rus.domain_byte == 0xC0
        assert converter_rus.language_family == 'Slavic'
        
        # Test Asian family
        converter_cmn = AQEAConverter(test_config, 'cmn', database=None, worker_id="test")
        assert converter_cmn.language == 'cmn'
        assert converter_cmn.domain_byte == 0xD0
        assert converter_cmn.language_family == 'Asian'
    
    def test_converter_unsupported_language(self, test_config):
        """Test converter with unsupported language."""
        with pytest.raises(ValueError, match="not supported in AQEA Family Blocks"):
            AQEAConverter(test_config, 'xyz', database=None, worker_id="test")
    
    @pytest.mark.asyncio
    async def test_address_generation_by_family(self, test_config):
        """Test AQEA address generation for different language families."""
        
        # Test Germanic family (German)
        converter_de = AQEAConverter(test_config, 'de', database=None, worker_id="test")
        entry_de = {
            'word': 'Wasser',
            'language': 'de',
            'pos': 'noun',
            'definitions': ['H₂O', 'Water']
        }
        
        aqea_entry_de = await converter_de.convert(entry_de)
        assert aqea_entry_de is not None
        assert aqea_entry_de.address.startswith('0xA0:')  # Germanic family
        assert aqea_entry_de.label == 'Wasser'
        assert aqea_entry_de.domain == '0xA0'
        
        # Test Romance family (French)
        converter_fr = AQEAConverter(test_config, 'fr', database=None, worker_id="test")
        entry_fr = {
            'word': 'eau',
            'language': 'fr',
            'pos': 'noun',
            'definitions': ['water', 'liquid H₂O']
        }
        
        aqea_entry_fr = await converter_fr.convert(entry_fr)
        assert aqea_entry_fr is not None
        assert aqea_entry_fr.address.startswith('0xB0:')  # Romance family
        assert aqea_entry_fr.label == 'eau'
        assert aqea_entry_fr.domain == '0xB0'
        
        # Test Slavic family (Russian)
        converter_ru = AQEAConverter(test_config, 'ru', database=None, worker_id="test")
        entry_ru = {
            'word': 'вода',
            'language': 'ru',
            'pos': 'noun',
            'definitions': ['water', 'H₂O']
        }
        
        aqea_entry_ru = await converter_ru.convert(entry_ru)
        assert aqea_entry_ru is not None
        assert aqea_entry_ru.address.startswith('0xC0:')  # Slavic family
        assert aqea_entry_ru.label == 'вода'
        assert aqea_entry_ru.domain == '0xC0'
    
    @pytest.mark.asyncio
    async def test_cross_family_concept_consistency(self, test_config):
        """Test that the same concept gets similar addresses across families."""
        
        # Create converters for different families
        converter_de = AQEAConverter(test_config, 'de', database=None, worker_id="test")
        converter_fr = AQEAConverter(test_config, 'fr', database=None, worker_id="test")
        
        # Same concept: "water" in different languages
        water_de = {
            'word': 'Wasser',
            'language': 'de',
            'pos': 'noun',
            'definitions': ['H₂O', 'transparent liquid']
        }
        
        water_fr = {
            'word': 'eau',
            'language': 'fr', 
            'pos': 'noun',
            'definitions': ['H₂O', 'transparent liquid']
        }
        
        # Convert both
        aqea_de = await converter_de.convert(water_de)
        aqea_fr = await converter_fr.convert(water_fr)
        
        assert aqea_de is not None
        assert aqea_fr is not None
        
        # Parse addresses
        parts_de = aqea_de.address.split(':')
        parts_fr = aqea_fr.address.split(':')
        
        # Different families (AA-byte should differ)
        assert parts_de[0] != parts_fr[0]  # Different families
        assert parts_de[0] == '0xA0'       # Germanic
        assert parts_fr[0] == '0xB0'       # Romance
        
        # Same semantic pattern (QQ:EE should be similar for same concept)
        # This validates cross-linguistic semantic consistency
        assert parts_de[1] == parts_fr[1]  # Same POS (noun)


class TestCrossLinguisticEquivalence:
    """Test cross-linguistic semantic equivalence."""
    
    def test_universal_concept_water(self):
        """Test that 'water' concept maps consistently across families."""
        water_languages = [
            ('deu', 'Wasser'),    # Germanic
            ('eng', 'water'),     # Germanic  
            ('fra', 'eau'),       # Romance
            ('spa', 'agua'),      # Romance
            ('rus', 'вода'),      # Slavic (if implemented)
            ('cmn', '水'),        # Asian (if implemented)
        ]
        
        family_aa_ranges = {
            'Germanic': (0xA0, 0xAF),
            'Romance': (0xB0, 0xBF),
            'Slavic': (0xC0, 0xCF),
            'Asian': (0xD0, 0xDF)
        }
        
        for iso_code, word in water_languages:
            try:
                aa_byte = encode_language(iso_code)
                family = get_language_family(iso_code)
                
                # Validate AA-byte is in correct family range
                start, end = family_aa_ranges[family]
                assert start <= aa_byte <= end, f"{iso_code} not in {family} range"
                
                print(f"✅ {word} ({iso_code}): 0x{aa_byte:02X} ({family})")
                
            except UnsupportedLanguageError:
                print(f"⚠️ {word} ({iso_code}): Not yet implemented")
    
    def test_family_block_boundaries(self):
        """Test that family blocks have correct boundaries."""
        # Test boundary languages
        assert encode_language('deu') == 0xA0  # Germanic start
        assert encode_language('fra') == 0xB0  # Romance start  
        assert encode_language('rus') == 0xC0  # Slavic start
        assert encode_language('cmn') == 0xD0  # Asian start
        
        # Validate no overlap between families
        all_aa_bytes = [encode_language(lang) for lang in list_supported_languages()]
        assert len(all_aa_bytes) == len(set(all_aa_bytes)), "Duplicate AA-bytes detected"


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v']) 
"""
AQEA Language Mappings - Final Implementation
Based on UNIVERSAL_LANGUAGE_DOMAIN_FINAL.md

Family-based language blocks with direct AA-to-language mapping:
- 0xA0-0xAF: Germanic Languages (16 slots)
- 0xB0-0xBF: Romance Languages (16 slots)  
- 0xC0-0xCF: Slavic Languages (16 slots)
- 0xD0-0xDF: Sino-Tibetan & Major Asian (16 slots)
"""

from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# LANGUAGE TO AA-BYTE MAPPINGS (Direct Implementation)
# =============================================================================

LANGUAGE_TO_AA: Dict[str, int] = {
    # =============================================================================
    # GERMANIC BLOCK (0xA0-0xAF) - 16 slots
    # =============================================================================
    'deu': 0xA0,  # German - Deutsch (100M speakers)
    'eng': 0xA1,  # English - English (1.5B speakers)
    'nld': 0xA2,  # Dutch - Nederlands (25M speakers)
    'swe': 0xA3,  # Swedish - Svenska (10M speakers)
    'dan': 0xA4,  # Danish - Dansk (6M speakers)
    'nor': 0xA5,  # Norwegian - Norsk (5M speakers)
    'isl': 0xA6,  # Icelandic - Íslenska (400K speakers)
    'afr': 0xA7,  # Afrikaans - Afrikaans (7M speakers)
    'yid': 0xA8,  # Yiddish - ייִדיש (600K speakers)
    'fry': 0xA9,  # Frisian - Frysk (500K speakers)
    # 0xAA-0xAF: Reserved for Germanic expansion
    
    # =============================================================================
    # ROMANCE BLOCK (0xB0-0xBF) - 16 slots
    # =============================================================================
    'fra': 0xB0,  # French - Français (280M speakers)
    'spa': 0xB1,  # Spanish - Español (500M speakers)
    'ita': 0xB2,  # Italian - Italiano (65M speakers)
    'por': 0xB3,  # Portuguese - Português (260M speakers)
    'ron': 0xB4,  # Romanian - Română (22M speakers)
    'cat': 0xB5,  # Catalan - Català (10M speakers)
    'glg': 0xB6,  # Galician - Galego (2.4M speakers)
    'oci': 0xB7,  # Occitan - Occitan (200K speakers)
    'lat': 0xB8,  # Latin - Latina (historical)
    'srd': 0xB9,  # Sardinian - Sardu (1.3M speakers)
    # 0xBA-0xBF: Reserved for Romance expansion
    
    # =============================================================================
    # SLAVIC BLOCK (0xC0-0xCF) - 16 slots
    # =============================================================================
    'rus': 0xC0,  # Russian - Русский (260M speakers)
    'pol': 0xC1,  # Polish - Polski (45M speakers)
    'ces': 0xC2,  # Czech - Čeština (10M speakers)
    'slk': 0xC3,  # Slovak - Slovenčina (5M speakers)
    'ukr': 0xC4,  # Ukrainian - Українська (40M speakers)
    'bel': 0xC5,  # Belarusian - Беларуская (5M speakers)
    'bul': 0xC6,  # Bulgarian - Български (9M speakers)
    'hrv': 0xC7,  # Croatian - Hrvatski (5M speakers)
    'srp': 0xC8,  # Serbian - Српски (9M speakers)
    'slv': 0xC9,  # Slovenian - Slovenščina (2M speakers)
    'mkd': 0xCA,  # Macedonian - Македонски (2M speakers)
    # 0xCB-0xCF: Reserved for Slavic expansion
    
    # =============================================================================
    # SINO-TIBETAN & MAJOR ASIAN BLOCK (0xD0-0xDF) - 16 slots
    # =============================================================================
    'cmn': 0xD0,  # Mandarin Chinese - 普通话 (900M speakers)
    'yue': 0xD1,  # Cantonese - 粵語 (85M speakers)
    'jpn': 0xD2,  # Japanese - 日本語 (125M speakers)
    'kor': 0xD3,  # Korean - 한국어 (77M speakers)
    'vie': 0xD4,  # Vietnamese - Tiếng Việt (95M speakers)
    'tha': 0xD5,  # Thai - ไทย (60M speakers)
    'khm': 0xD6,  # Khmer - ខ្មែរ (16M speakers)
    'mya': 0xD7,  # Burmese - မြန်မာ (33M speakers)
    'bod': 0xD8,  # Tibetan - བོད་སྐད (6M speakers)
    'mon': 0xD9,  # Mongolian - Монгол (5M speakers)
    # 0xDA-0xDF: Reserved for Asian expansion
}

# Reverse mapping for decoding
AA_TO_LANGUAGE: Dict[int, str] = {v: k for k, v in LANGUAGE_TO_AA.items()}

# =============================================================================
# FAMILY BLOCK DEFINITIONS
# =============================================================================

FAMILY_BLOCKS = {
    'Germanic': {
        'range': (0xA0, 0xAF),
        'description': 'Germanic language family',
        'languages': ['deu', 'eng', 'nld', 'swe', 'dan', 'nor', 'isl', 'afr', 'yid', 'fry']
    },
    'Romance': {
        'range': (0xB0, 0xBF), 
        'description': 'Romance language family',
        'languages': ['fra', 'spa', 'ita', 'por', 'ron', 'cat', 'glg', 'oci', 'lat', 'srd']
    },
    'Slavic': {
        'range': (0xC0, 0xCF),
        'description': 'Slavic language family', 
        'languages': ['rus', 'pol', 'ces', 'slk', 'ukr', 'bel', 'bul', 'hrv', 'srp', 'slv', 'mkd']
    },
    'Asian': {
        'range': (0xD0, 0xDF),
        'description': 'Sino-Tibetan and major Asian languages',
        'languages': ['cmn', 'yue', 'jpn', 'kor', 'vie', 'tha', 'khm', 'mya', 'bod', 'mon']
    }
}

# =============================================================================
# LANGUAGE METADATA
# =============================================================================

LANGUAGE_METADATA = {
    # Germanic Languages
    'deu': {'name_english': 'German', 'name_native': 'Deutsch', 'speakers': 100_000_000, 'family': 'Germanic'},
    'eng': {'name_english': 'English', 'name_native': 'English', 'speakers': 1_500_000_000, 'family': 'Germanic'},
    'nld': {'name_english': 'Dutch', 'name_native': 'Nederlands', 'speakers': 25_000_000, 'family': 'Germanic'},
    'swe': {'name_english': 'Swedish', 'name_native': 'Svenska', 'speakers': 10_000_000, 'family': 'Germanic'},
    'dan': {'name_english': 'Danish', 'name_native': 'Dansk', 'speakers': 6_000_000, 'family': 'Germanic'},
    'nor': {'name_english': 'Norwegian', 'name_native': 'Norsk', 'speakers': 5_000_000, 'family': 'Germanic'},
    'isl': {'name_english': 'Icelandic', 'name_native': 'Íslenska', 'speakers': 400_000, 'family': 'Germanic'},
    'afr': {'name_english': 'Afrikaans', 'name_native': 'Afrikaans', 'speakers': 7_000_000, 'family': 'Germanic'},
    'yid': {'name_english': 'Yiddish', 'name_native': 'ייִדיש', 'speakers': 600_000, 'family': 'Germanic'},
    'fry': {'name_english': 'Frisian', 'name_native': 'Frysk', 'speakers': 500_000, 'family': 'Germanic'},
    
    # Romance Languages
    'fra': {'name_english': 'French', 'name_native': 'Français', 'speakers': 280_000_000, 'family': 'Romance'},
    'spa': {'name_english': 'Spanish', 'name_native': 'Español', 'speakers': 500_000_000, 'family': 'Romance'},
    'ita': {'name_english': 'Italian', 'name_native': 'Italiano', 'speakers': 65_000_000, 'family': 'Romance'},
    'por': {'name_english': 'Portuguese', 'name_native': 'Português', 'speakers': 260_000_000, 'family': 'Romance'},
    'ron': {'name_english': 'Romanian', 'name_native': 'Română', 'speakers': 22_000_000, 'family': 'Romance'},
    'cat': {'name_english': 'Catalan', 'name_native': 'Català', 'speakers': 10_000_000, 'family': 'Romance'},
    'glg': {'name_english': 'Galician', 'name_native': 'Galego', 'speakers': 2_400_000, 'family': 'Romance'},
    'oci': {'name_english': 'Occitan', 'name_native': 'Occitan', 'speakers': 200_000, 'family': 'Romance'},
    'lat': {'name_english': 'Latin', 'name_native': 'Latina', 'speakers': 0, 'family': 'Romance'},  # Historical
    'srd': {'name_english': 'Sardinian', 'name_native': 'Sardu', 'speakers': 1_300_000, 'family': 'Romance'},
    
    # Slavic Languages
    'rus': {'name_english': 'Russian', 'name_native': 'Русский', 'speakers': 260_000_000, 'family': 'Slavic'},
    'pol': {'name_english': 'Polish', 'name_native': 'Polski', 'speakers': 45_000_000, 'family': 'Slavic'},
    'ces': {'name_english': 'Czech', 'name_native': 'Čeština', 'speakers': 10_000_000, 'family': 'Slavic'},
    'slk': {'name_english': 'Slovak', 'name_native': 'Slovenčina', 'speakers': 5_000_000, 'family': 'Slavic'},
    'ukr': {'name_english': 'Ukrainian', 'name_native': 'Українська', 'speakers': 40_000_000, 'family': 'Slavic'},
    'bel': {'name_english': 'Belarusian', 'name_native': 'Беларуская', 'speakers': 5_000_000, 'family': 'Slavic'},
    'bul': {'name_english': 'Bulgarian', 'name_native': 'Български', 'speakers': 9_000_000, 'family': 'Slavic'},
    'hrv': {'name_english': 'Croatian', 'name_native': 'Hrvatski', 'speakers': 5_000_000, 'family': 'Slavic'},
    'srp': {'name_english': 'Serbian', 'name_native': 'Српски', 'speakers': 9_000_000, 'family': 'Slavic'},
    'slv': {'name_english': 'Slovenian', 'name_native': 'Slovenščina', 'speakers': 2_000_000, 'family': 'Slavic'},
    'mkd': {'name_english': 'Macedonian', 'name_native': 'Македонски', 'speakers': 2_000_000, 'family': 'Slavic'},
    
    # Asian Languages
    'cmn': {'name_english': 'Mandarin Chinese', 'name_native': '普通话', 'speakers': 900_000_000, 'family': 'Asian'},
    'yue': {'name_english': 'Cantonese', 'name_native': '粵語', 'speakers': 85_000_000, 'family': 'Asian'},
    'jpn': {'name_english': 'Japanese', 'name_native': '日本語', 'speakers': 125_000_000, 'family': 'Asian'},
    'kor': {'name_english': 'Korean', 'name_native': '한국어', 'speakers': 77_000_000, 'family': 'Asian'},
    'vie': {'name_english': 'Vietnamese', 'name_native': 'Tiếng Việt', 'speakers': 95_000_000, 'family': 'Asian'},
    'tha': {'name_english': 'Thai', 'name_native': 'ไทย', 'speakers': 60_000_000, 'family': 'Asian'},
    'khm': {'name_english': 'Khmer', 'name_native': 'ខ្មែរ', 'speakers': 16_000_000, 'family': 'Asian'},
    'mya': {'name_english': 'Burmese', 'name_native': 'မြန်မာ', 'speakers': 33_000_000, 'family': 'Asian'},
    'bod': {'name_english': 'Tibetan', 'name_native': 'བོད་སྐད', 'speakers': 6_000_000, 'family': 'Asian'},
    'mon': {'name_english': 'Mongolian', 'name_native': 'Монгол', 'speakers': 5_000_000, 'family': 'Asian'},
}

# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def encode_language(iso_639_3: str) -> int:
    """
    Convert ISO 639-3 language code to AA-byte.
    
    Args:
        iso_639_3: Three-letter ISO language code (e.g., 'deu', 'eng')
    
    Returns:
        int: AA-byte value (0xA0-0xDF)
    
    Raises:
        UnsupportedLanguageError: If language is not supported
    
    Example:
        >>> encode_language('deu')
        160  # 0xA0
        >>> encode_language('eng') 
        161  # 0xA1
    """
    if iso_639_3 not in LANGUAGE_TO_AA:
        supported = list(LANGUAGE_TO_AA.keys())
        raise UnsupportedLanguageError(
            f"Language '{iso_639_3}' not supported. "
            f"Supported languages: {', '.join(supported[:10])}..."
        )
    
    aa_byte = LANGUAGE_TO_AA[iso_639_3]
    logger.debug(f"Encoded language '{iso_639_3}' to AA-byte: 0x{aa_byte:02X}")
    return aa_byte

def decode_language(aa_byte: int) -> str:
    """
    Convert AA-byte to ISO 639-3 language code.
    
    Args:
        aa_byte: AA-byte value (0xA0-0xDF)
    
    Returns:
        str: ISO 639-3 language code
    
    Raises:
        InvalidAddressError: If AA-byte is not valid
    
    Example:
        >>> decode_language(0xA0)
        'deu'
        >>> decode_language(0xA1)
        'eng'
    """
    if aa_byte not in AA_TO_LANGUAGE:
        raise InvalidAddressError(
            f"Invalid language AA-byte: 0x{aa_byte:02X}. "
            f"Valid range: 0xA0-0xDF"
        )
    
    iso_code = AA_TO_LANGUAGE[aa_byte]
    logger.debug(f"Decoded AA-byte 0x{aa_byte:02X} to language: '{iso_code}'")
    return iso_code

def get_language_family(iso_639_3: str) -> Optional[str]:
    """
    Get language family for ISO 639-3 code.
    
    Args:
        iso_639_3: ISO language code
    
    Returns:
        str: Family name ('Germanic', 'Romance', 'Slavic', 'Asian') or None
    """
    if iso_639_3 in LANGUAGE_METADATA:
        return LANGUAGE_METADATA[iso_639_3]['family']
    return None

def get_family_range(family_name: str) -> Optional[Tuple[int, int]]:
    """
    Get AA-byte range for language family.
    
    Args:
        family_name: Name of language family
    
    Returns:
        tuple: (start_aa, end_aa) range or None
    """
    if family_name in FAMILY_BLOCKS:
        return FAMILY_BLOCKS[family_name]['range']
    return None

def list_supported_languages() -> List[str]:
    """Get list of all supported ISO 639-3 language codes."""
    return list(LANGUAGE_TO_AA.keys())

def list_families() -> List[str]:
    """Get list of all language families."""
    return list(FAMILY_BLOCKS.keys())

def get_family_languages(family_name: str) -> List[str]:
    """
    Get all languages in a family.
    
    Args:
        family_name: Name of language family
    
    Returns:
        list: ISO 639-3 codes in family
    """
    if family_name in FAMILY_BLOCKS:
        return FAMILY_BLOCKS[family_name]['languages']
    return []

def is_valid_language_aa(aa_byte: int) -> bool:
    """
    Check if AA-byte is in valid language range.
    
    Args:
        aa_byte: AA-byte to validate
    
    Returns:
        bool: True if valid language AA-byte
    """
    return 0xA0 <= aa_byte <= 0xDF

def get_language_info(iso_639_3: str) -> Optional[Dict]:
    """
    Get complete language information.
    
    Args:
        iso_639_3: ISO language code
    
    Returns:
        dict: Complete language metadata or None
    """
    if iso_639_3 not in LANGUAGE_METADATA:
        return None
    
    info = LANGUAGE_METADATA[iso_639_3].copy()
    info['iso_639_3'] = iso_639_3
    
    if iso_639_3 in LANGUAGE_TO_AA:
        info['aa_byte'] = LANGUAGE_TO_AA[iso_639_3]
        info['aa_hex'] = f"0x{LANGUAGE_TO_AA[iso_639_3]:02X}"
    
    return info

# =============================================================================
# EXCEPTION CLASSES
# =============================================================================

class UnsupportedLanguageError(Exception):
    """Raised when trying to encode unsupported language."""
    pass

class InvalidAddressError(Exception):
    """Raised when trying to decode invalid AA-byte."""
    pass

# =============================================================================
# VALIDATION & STATISTICS
# =============================================================================

def validate_mappings():
    """Validate language mappings for consistency."""
    errors = []
    
    # Check for duplicate AA-bytes
    aa_values = list(LANGUAGE_TO_AA.values())
    if len(aa_values) != len(set(aa_values)):
        errors.append("Duplicate AA-byte values detected")
    
    # Check AA-byte ranges
    for iso, aa in LANGUAGE_TO_AA.items():
        if not is_valid_language_aa(aa):
            errors.append(f"Language '{iso}' has invalid AA-byte: 0x{aa:02X}")
    
    # Check metadata consistency
    for iso in LANGUAGE_TO_AA:
        if iso not in LANGUAGE_METADATA:
            errors.append(f"Language '{iso}' missing metadata")
    
    if errors:
        raise ValueError(f"Mapping validation failed: {'; '.join(errors)}")
    
    logger.info("Language mappings validation: PASSED")

def get_statistics() -> Dict:
    """Get statistics about language mappings."""
    stats = {
        'total_languages': len(LANGUAGE_TO_AA),
        'families': {},
        'aa_range_usage': {},
        'total_speakers': 0
    }
    
    # Family statistics
    for family_name, family_data in FAMILY_BLOCKS.items():
        family_languages = family_data['languages']
        assigned_count = sum(1 for lang in family_languages if lang in LANGUAGE_TO_AA)
        
        stats['families'][family_name] = {
            'total_slots': 16,
            'assigned_languages': assigned_count,
            'available_slots': 16 - assigned_count,
            'languages': family_languages
        }
    
    # AA-range usage
    for range_name, (start, end) in [
        ('Germanic', (0xA0, 0xAF)),
        ('Romance', (0xB0, 0xBF)), 
        ('Slavic', (0xC0, 0xCF)),
        ('Asian', (0xD0, 0xDF))
    ]:
        used = sum(1 for aa in LANGUAGE_TO_AA.values() if start <= aa <= end)
        stats['aa_range_usage'][range_name] = {
            'used': used,
            'total': 16,
            'percentage': (used / 16) * 100
        }
    
    # Speaker statistics
    stats['total_speakers'] = sum(
        LANGUAGE_METADATA[iso]['speakers'] 
        for iso in LANGUAGE_TO_AA 
        if iso in LANGUAGE_METADATA
    )
    
    return stats

# =============================================================================
# INITIALIZATION
# =============================================================================

# Validate mappings on import
try:
    validate_mappings()
except ValueError as e:
    logger.error(f"Language mapping validation failed: {e}")
    raise

logger.info(f"AQEA Language Mappings loaded: {len(LANGUAGE_TO_AA)} languages across {len(FAMILY_BLOCKS)} families") 
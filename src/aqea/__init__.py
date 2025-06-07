"""
AQEA Format Conversion Module

Converts extracted language data to AQEA 4-byte address format.
Now with Universal Semantic Hierarchy (USH) support.
"""

from .converter import AQEAConverter
from .address_generator import AddressGenerator
from .schema import AQEAEntry
from .ush_adapter import USHAdapter
from .ush_converter import USHConverter
from .ush_categories import (
    LANGUAGE_DOMAINS, 
    UNIVERSAL_CATEGORIES, 
    HIERARCHICAL_CLUSTERS,
    SEMANTIC_ROLES
)

__all__ = [
    'AQEAConverter',  # Legacy converter
    'AddressGenerator', 
    'AQEAEntry',
    'USHAdapter',  # New USH adapter
    'USHConverter',  # New USH converter
    'LANGUAGE_DOMAINS', 
    'UNIVERSAL_CATEGORIES', 
    'HIERARCHICAL_CLUSTERS',
    'SEMANTIC_ROLES'
] 
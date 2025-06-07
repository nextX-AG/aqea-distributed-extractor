#!/usr/bin/env python3
"""
Universal Semantic Hierarchy (USH) Demo

Demonstrates the usage of USH addressing in AQEA.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Füge das Hauptverzeichnis zum Pfad hinzu, damit die Module gefunden werden
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aqea import USHConverter, USHAdapter

# Ensure examples directory exists
os.makedirs('examples/output', exist_ok=True)


async def main():
    """Run USH demonstration."""
    # Configuration
    config = {
        'aqea': {
            'use_legacy_mode': False,
            'enable_cross_linguistic': True
        }
    }
    
    # Create USH converter for German
    de_converter = USHConverter(config, 'de')
    
    # Sample entries for German
    german_entries = [
        {
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
        },
        {
            'word': 'gehen',
            'pos': 'verb',
            'definitions': ['to walk', 'to go', 'to move by foot'],
            'labels': ['motion', 'movement'],
            'ipa': 'ˈɡeːən',
            'translations': {
                'en': ['go', 'walk'],
                'fr': ['aller', 'marcher'],
                'es': ['ir', 'caminar']
            }
        },
        {
            'word': 'groß',
            'pos': 'adjective',
            'definitions': ['big', 'large', 'of considerable size'],
            'labels': ['dimension', 'size'],
            'ipa': 'ɡʁoːs',
            'translations': {
                'en': ['big', 'large'],
                'fr': ['grand'],
                'es': ['grande']
            }
        },
        {
            'word': 'Liebe',
            'pos': 'noun',
            'definitions': ['strong affection', 'deep romantic feeling'],
            'labels': ['emotion', 'feeling'],
            'ipa': 'ˈliːbə',
            'translations': {
                'en': ['love'],
                'fr': ['amour'],
                'es': ['amor']
            }
        },
        {
            'word': 'unter',
            'pos': 'preposition',
            'definitions': ['below', 'beneath', 'under'],
            'labels': ['position', 'relation'],
            'ipa': 'ˈʊntɐ',
            'translations': {
                'en': ['under', 'below'],
                'fr': ['sous'],
                'es': ['bajo']
            }
        }
    ]
    
    # Convert entries to AQEA format with USH addressing
    german_aqea_entries = []
    for entry in german_entries:
        aqea_entry = await de_converter.convert(entry)
        if aqea_entry:
            german_aqea_entries.append(aqea_entry.to_dict())
            print(f"Converted '{entry['word']}' to {aqea_entry.address}")
            print(f"  - Category: {aqea_entry.meta['ush_category']}")
            print(f"  - Cluster: {aqea_entry.meta['ush_cluster']}")
            print()
    
    # Create USH converter for English
    en_converter = USHConverter(config, 'en')
    
    # Sample entries for English
    english_entries = [
        {
            'word': 'water',
            'pos': 'noun',
            'definitions': ['clear liquid H₂O', 'liquid that falls as rain'],
            'labels': ['nature', 'fluid'],
            'ipa': 'ˈwɔːtə(r)',
            'translations': {
                'de': ['Wasser'],
                'fr': ['eau'],
                'es': ['agua']
            }
        },
        {
            'word': 'go',
            'pos': 'verb',
            'definitions': ['move from one place to another', 'travel'],
            'labels': ['motion', 'movement'],
            'ipa': 'ɡəʊ',
            'translations': {
                'de': ['gehen'],
                'fr': ['aller'],
                'es': ['ir']
            }
        }
    ]
    
    # Convert entries to AQEA format with USH addressing
    english_aqea_entries = []
    for entry in english_entries:
        aqea_entry = await en_converter.convert(entry)
        if aqea_entry:
            english_aqea_entries.append(aqea_entry.to_dict())
            print(f"Converted '{entry['word']}' to {aqea_entry.address}")
            print(f"  - Category: {aqea_entry.meta['ush_category']}")
            print(f"  - Cluster: {aqea_entry.meta['ush_cluster']}")
            print()
    
    # Demonstrate cross-linguistic equivalence
    print("\n=== CROSS-LINGUISTIC EQUIVALENCE DEMONSTRATION ===")
    
    de_adapter = USHAdapter(config, 'de')
    en_adapter = USHAdapter(config, 'en')
    
    # German -> English mapping
    de_water_address = german_aqea_entries[0]['address']  # 'Wasser'
    en_water_address = english_aqea_entries[0]['address']  # 'water'
    
    # Extract QQ:EE:A2 pattern (same for equivalent concepts)
    _, de_qq, de_ee, de_a2 = de_adapter.parse_ush_address(de_water_address)
    _, en_qq, en_ee, en_a2 = en_adapter.parse_ush_address(en_water_address)
    
    print(f"German 'Wasser': {de_water_address}")
    print(f"English 'water': {en_water_address}")
    print(f"Universal pattern (German): {de_qq:02X}:{de_ee:02X}:{de_a2:02X}")
    print(f"Universal pattern (English): {en_qq:02X}:{en_ee:02X}:{en_a2:02X}")
    
    # Check if concepts are equivalent (should have same QQ:EE:A2)
    are_equivalent = (de_qq == en_qq and de_ee == en_ee)
    print(f"Same universal category: {de_qq == en_qq}")
    print(f"Same hierarchical cluster: {de_ee == en_ee}")
    print(f"Overall equivalence: {are_equivalent}")
    
    # Save results to file
    results = {
        'timestamp': datetime.now().isoformat(),
        'german_entries': german_aqea_entries,
        'english_entries': english_aqea_entries,
        'cross_linguistic_demo': {
            'german_water_address': de_water_address,
            'english_water_address': en_water_address,
            'universal_pattern_german': f"{de_qq:02X}:{de_ee:02X}:{de_a2:02X}",
            'universal_pattern_english': f"{en_qq:02X}:{en_ee:02X}:{en_a2:02X}",
            'are_equivalent': are_equivalent
        }
    }
    
    with open('examples/output/ush_demo_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\nResults saved to examples/output/ush_demo_results.json")


if __name__ == '__main__':
    asyncio.run(main()) 
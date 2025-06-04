"""
AQEA Address Generator

Generates unique AQEA addresses and manages element ID allocation.
"""

import asyncio
import hashlib
import logging
from typing import Dict, Any, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class AddressGenerator:
    """Generates unique AQEA addresses."""
    
    def __init__(self, language: str):
        self.language = language
        
        # Track allocated addresses: {(aa, qq, ee): {a2_values}}
        self.allocated_addresses: Dict[tuple, Set[int]] = defaultdict(set)
        
        # Cache word to address mappings for consistency
        self.word_to_address: Dict[str, str] = {}
        
        # Statistics
        self.stats = {
            'total_generated': 0,
            'collisions_resolved': 0,
            'cache_hits': 0
        }
        
    async def get_next_element_id(self, aa: int, qq: int, ee: int, word: str) -> int:
        """Get next available element ID (A2 byte) for the given category."""
        # Check cache first
        cache_key = f"{aa:02X}:{qq:02X}:{ee:02X}:{word}"
        if cache_key in self.word_to_address:
            self.stats['cache_hits'] += 1
            # Extract A2 from cached address
            cached_address = self.word_to_address[cache_key]
            return int(cached_address.split(':')[-1], 16)
        
        # Generate deterministic starting point based on word
        word_hash = hashlib.md5(word.encode('utf-8')).hexdigest()
        base_id = int(word_hash[:2], 16)
        
        # Ensure we don't use reserved values (0xFE, 0xFF)
        if base_id >= 0xFE:
            base_id = base_id % 0xFE
        
        category_key = (aa, qq, ee)
        allocated = self.allocated_addresses[category_key]
        
        # Find next available ID
        element_id = base_id
        attempts = 0
        max_attempts = 256  # Maximum possible values
        
        while element_id in allocated and attempts < max_attempts:
            element_id = (element_id + 1) % 0xFE  # Wrap around, avoid 0xFE/0xFF
            attempts += 1
        
        if attempts >= max_attempts:
            # This category is full, use overflow strategy
            logger.warning(f"Category {aa:02X}:{qq:02X}:{ee:02X} is full, using overflow")
            element_id = self._handle_overflow(category_key)
        
        # Mark as allocated
        allocated.add(element_id)
        
        # Cache the mapping
        address = f"0x{aa:02X}:{qq:02X}:{ee:02X}:{element_id:02X}"
        self.word_to_address[cache_key] = address
        
        # Update statistics
        self.stats['total_generated'] += 1
        if attempts > 0:
            self.stats['collisions_resolved'] += attempts
        
        logger.debug(f"Generated element ID {element_id:02X} for '{word}' in category {aa:02X}:{qq:02X}:{ee:02X}")
        
        return element_id
    
    def _handle_overflow(self, category_key: tuple) -> int:
        """Handle overflow when a category is full."""
        # For now, use a simple strategy: reuse the first allocated ID
        # In a production system, this might trigger category subdivision
        allocated = self.allocated_addresses[category_key]
        if allocated:
            return min(allocated)
        else:
            return 0x01  # Fallback
    
    def is_address_available(self, aa: int, qq: int, ee: int, a2: int) -> bool:
        """Check if an address is available."""
        category_key = (aa, qq, ee)
        allocated = self.allocated_addresses[category_key]
        return a2 not in allocated
    
    def reserve_address(self, aa: int, qq: int, ee: int, a2: int) -> bool:
        """Reserve a specific address."""
        if self.is_address_available(aa, qq, ee, a2):
            category_key = (aa, qq, ee)
            self.allocated_addresses[category_key].add(a2)
            return True
        return False
    
    def get_category_usage(self, aa: int, qq: int, ee: int) -> Dict[str, Any]:
        """Get usage statistics for a specific category."""
        category_key = (aa, qq, ee)
        allocated = self.allocated_addresses[category_key]
        
        return {
            'category': f"{aa:02X}:{qq:02X}:{ee:02X}",
            'allocated_count': len(allocated),
            'available_count': 254 - len(allocated),  # 0x00-0xFD available
            'utilization_percent': (len(allocated) / 254) * 100,
            'is_full': len(allocated) >= 254
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        total_categories = len(self.allocated_addresses)
        total_allocated = sum(len(allocated) for allocated in self.allocated_addresses.values())
        
        # Find most used categories
        category_usage = []
        for category_key, allocated in self.allocated_addresses.items():
            aa, qq, ee = category_key
            usage = self.get_category_usage(aa, qq, ee)
            category_usage.append(usage)
        
        # Sort by utilization
        category_usage.sort(key=lambda x: x['allocated_count'], reverse=True)
        
        return {
            'language': self.language,
            'total_addresses_generated': self.stats['total_generated'],
            'total_categories_used': total_categories,
            'total_addresses_allocated': total_allocated,
            'collisions_resolved': self.stats['collisions_resolved'],
            'cache_hits': self.stats['cache_hits'],
            'average_addresses_per_category': total_allocated / total_categories if total_categories > 0 else 0,
            'top_categories': category_usage[:10],  # Top 10 most used categories
            'efficiency_metrics': {
                'collision_rate': (self.stats['collisions_resolved'] / self.stats['total_generated']) * 100 if self.stats['total_generated'] > 0 else 0,
                'cache_hit_rate': (self.stats['cache_hits'] / (self.stats['total_generated'] + self.stats['cache_hits'])) * 100 if (self.stats['total_generated'] + self.stats['cache_hits']) > 0 else 0
            }
        }
    
    def export_mappings(self) -> Dict[str, Any]:
        """Export all current address mappings for backup/restore."""
        return {
            'language': self.language,
            'allocated_addresses': {
                f"{aa:02X}:{qq:02X}:{ee:02X}": list(allocated)
                for (aa, qq, ee), allocated in self.allocated_addresses.items()
            },
            'word_mappings': dict(self.word_to_address),
            'statistics': self.stats.copy()
        }
    
    def import_mappings(self, data: Dict[str, Any]) -> bool:
        """Import address mappings from backup."""
        try:
            if data.get('language') != self.language:
                logger.warning(f"Language mismatch: expected {self.language}, got {data.get('language')}")
            
            # Import allocated addresses
            for category_str, allocated_list in data.get('allocated_addresses', {}).items():
                aa, qq, ee = [int(x, 16) for x in category_str.split(':')]
                category_key = (aa, qq, ee)
                self.allocated_addresses[category_key] = set(allocated_list)
            
            # Import word mappings
            self.word_to_address.update(data.get('word_mappings', {}))
            
            # Import statistics
            self.stats.update(data.get('statistics', {}))
            
            logger.info(f"Imported {len(self.word_to_address)} word mappings and {len(self.allocated_addresses)} categories")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import mappings: {e}")
            return False
    
    def validate_address_format(self, address: str) -> bool:
        """Validate AQEA address format."""
        try:
            # Expected format: 0xAA:QQ:EE:A2
            parts = address.split(':')
            if len(parts) != 4:
                return False
            
            # Check each part is valid hex
            for part in parts:
                if not part.startswith('0x') and len(part) == 4:
                    return False
                int(part, 16)  # This will raise ValueError if invalid
            
            return True
            
        except (ValueError, AttributeError):
            return False 
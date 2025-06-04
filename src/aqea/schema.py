"""
AQEA Schema Definitions

Defines the data structures for AQEA entries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
import json


@dataclass
class AQEAEntry:
    """AQEA Entry data structure following the specification."""
    
    # Core AQEA fields
    address: str                    # AQEA 4-byte address (AA:QQ:EE:A2)
    label: str                      # Short label (≤ 60 characters)
    description: str                # 1-3 sentences, English default
    domain: str                     # Domain byte (redundant to AA for query speed)
    
    # Lifecycle & Management
    status: str = "active"          # draft|active|deprecated|pending_review
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"      # Creator identifier
    
    # Optional fields
    lang_ui: Optional[str] = None   # UI language (BCP-47)
    reviewed_by: Optional[str] = None
    dictionary_id: Optional[str] = None
    version_hash: Optional[str] = None
    signature: Optional[str] = None
    element_hash: Optional[str] = None
    vector: Optional[List[float]] = None
    embedding_source: Optional[str] = None
    aqea_path: Optional[str] = None
    license: Optional[str] = None
    
    # Relations and metadata
    relations: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'address': self.address,
            'label': self.label,
            'description': self.description,
            'domain': self.domain,
            'lang_ui': self.lang_ui,
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'created_by': self.created_by,
            'reviewed_by': self.reviewed_by,
            'dictionary_id': self.dictionary_id,
            'version_hash': self.version_hash,
            'signature': self.signature,
            'element_hash': self.element_hash,
            'vector': self.vector,
            'embedding_source': self.embedding_source,
            'aqea_path': self.aqea_path,
            'license': self.license,
            'relations': self.relations,
            'meta': self.meta
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AQEAEntry':
        """Create from dictionary."""
        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif created_at is None:
            created_at = datetime.now()
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        elif updated_at is None:
            updated_at = datetime.now()
        
        return cls(
            address=data['address'],
            label=data['label'],
            description=data['description'],
            domain=data['domain'],
            lang_ui=data.get('lang_ui'),
            status=data.get('status', 'active'),
            created_at=created_at,
            updated_at=updated_at,
            created_by=data.get('created_by', 'system'),
            reviewed_by=data.get('reviewed_by'),
            dictionary_id=data.get('dictionary_id'),
            version_hash=data.get('version_hash'),
            signature=data.get('signature'),
            element_hash=data.get('element_hash'),
            vector=data.get('vector'),
            embedding_source=data.get('embedding_source'),
            aqea_path=data.get('aqea_path'),
            license=data.get('license'),
            relations=data.get('relations', []),
            meta=data.get('meta', {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AQEAEntry':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> List[str]:
        """Validate the AQEA entry and return list of errors."""
        errors = []
        
        # Required fields
        if not self.address:
            errors.append("Address is required")
        elif not self._validate_address_format(self.address):
            errors.append(f"Invalid address format: {self.address}")
        
        if not self.label:
            errors.append("Label is required")
        elif len(self.label) > 60:
            errors.append(f"Label too long: {len(self.label)} > 60 characters")
        
        if not self.description:
            errors.append("Description is required")
        
        if not self.domain:
            errors.append("Domain is required")
        
        # Status validation
        valid_statuses = ['draft', 'active', 'deprecated', 'pending_review']
        if self.status not in valid_statuses:
            errors.append(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
        
        # Vector validation
        if self.vector is not None:
            if not isinstance(self.vector, list):
                errors.append("Vector must be a list of floats")
            elif not all(isinstance(x, (int, float)) for x in self.vector):
                errors.append("Vector must contain only numeric values")
        
        # Relations validation
        if self.relations:
            for i, relation in enumerate(self.relations):
                if not isinstance(relation, dict):
                    errors.append(f"Relation {i} must be a dictionary")
                    continue
                
                if 'type' not in relation:
                    errors.append(f"Relation {i} missing 'type' field")
                
                if 'target' not in relation:
                    errors.append(f"Relation {i} missing 'target' field")
                elif not self._validate_address_format(relation['target']):
                    errors.append(f"Relation {i} has invalid target address: {relation['target']}")
        
        return errors
    
    def _validate_address_format(self, address: str) -> bool:
        """Validate AQEA address format: 0xAA:QQ:EE:A2"""
        try:
            parts = address.split(':')
            if len(parts) != 4:
                return False
            
            for part in parts:
                # Each part should be 0xXX format
                if not part.startswith('0x') or len(part) != 4:
                    return False
                int(part, 16)  # Validate hex
            
            return True
        except (ValueError, AttributeError):
            return False
    
    def get_domain_byte(self) -> int:
        """Extract domain byte from address."""
        try:
            return int(self.address.split(':')[0], 16)
        except (ValueError, IndexError):
            return 0
    
    def get_category_byte(self) -> int:
        """Extract category byte from address."""
        try:
            return int(self.address.split(':')[1], 16)
        except (ValueError, IndexError):
            return 0
    
    def get_subcategory_byte(self) -> int:
        """Extract subcategory byte from address."""
        try:
            return int(self.address.split(':')[2], 16)
        except (ValueError, IndexError):
            return 0
    
    def get_element_byte(self) -> int:
        """Extract element byte from address."""
        try:
            return int(self.address.split(':')[3], 16)
        except (ValueError, IndexError):
            return 0
    
    def add_relation(self, relation_type: str, target_address: str, confidence: Optional[float] = None):
        """Add a relation to another AQEA entry."""
        relation = {
            'type': relation_type,
            'target': target_address
        }
        
        if confidence is not None:
            relation['confidence'] = confidence
        
        self.relations.append(relation)
    
    def remove_relation(self, relation_type: str, target_address: str) -> bool:
        """Remove a relation. Returns True if removed."""
        for i, relation in enumerate(self.relations):
            if relation.get('type') == relation_type and relation.get('target') == target_address:
                del self.relations[i]
                return True
        return False
    
    def get_relations_by_type(self, relation_type: str) -> List[Dict[str, Any]]:
        """Get all relations of a specific type."""
        return [r for r in self.relations if r.get('type') == relation_type]
    
    def update_meta(self, key: str, value: Any):
        """Update metadata field."""
        self.meta[key] = value
        self.updated_at = datetime.now()
    
    def get_meta(self, key: str, default: Any = None) -> Any:
        """Get metadata field with default."""
        return self.meta.get(key, default) 
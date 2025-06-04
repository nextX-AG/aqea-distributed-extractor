"""
Data Source Factory for AQEA Distributed Extractor
"""

from typing import Dict, Any
from .wiktionary import WiktionaryDataSource


class DataSourceFactory:
    """Factory for creating data source instances."""
    
    _sources = {
        'wiktionary': WiktionaryDataSource,
        # 'panlex': PanLexDataSource,  # Future implementation
        # 'wikidata': WikidataDataSource,  # Future implementation
    }
    
    @classmethod
    def create(cls, source_name: str, config: Dict[str, Any]):
        """Create a data source instance."""
        if source_name not in cls._sources:
            raise ValueError(f"Unknown data source: {source_name}")
        
        source_class = cls._sources[source_name]
        return source_class(config)
    
    @classmethod
    def list_sources(cls):
        """List available data sources."""
        return list(cls._sources.keys()) 
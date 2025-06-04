"""
Configuration Management for AQEA Distributed Extractor

Handles all configuration settings and environment variables.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "aqea"
    username: str = "aqea"
    password: str = "aqea"
    pool_size: int = 10
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class LanguageConfig:
    """Language-specific configuration."""
    name: str
    estimated_entries: int
    alphabet_ranges: List[Dict[str, Any]] = field(default_factory=list)
    supported_pos: List[str] = field(default_factory=lambda: ["noun", "verb", "adjective", "adverb"])
    frequency_threshold: int = 1
    
    def get_range_for_worker(self, worker_id: int, total_workers: int) -> Optional[Dict[str, str]]:
        """Get alphabet range for a specific worker."""
        if not self.alphabet_ranges or worker_id >= len(self.alphabet_ranges):
            return None
        
        # Simple distribution - each worker gets one range
        if worker_id < len(self.alphabet_ranges):
            return self.alphabet_ranges[worker_id]
        
        return None


@dataclass
class CloudProviderConfig:
    """Cloud provider configuration."""
    name: str
    master_instance_type: str
    worker_instance_type: str
    cost_per_hour: float
    max_workers: int = 10
    regions: List[str] = field(default_factory=list)


class Config:
    """Main configuration class."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/default.yml"
        self.data: Dict[str, Any] = {}
        
        # Default configurations
        self.database = DatabaseConfig()
        self.languages: Dict[str, LanguageConfig] = {}
        self.cloud_providers: Dict[str, CloudProviderConfig] = {}
        
        # Load configuration
        self.load()
    
    def load(self):
        """Load configuration from file and environment variables."""
        # Load from file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.data = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_file}: {e}")
                self.data = {}
        else:
            logger.info(f"Config file {self.config_file} not found, using defaults")
            self.data = self._get_default_config()
        
        # Override with environment variables
        self._load_from_environment()
        
        # Parse configurations
        self._parse_database_config()
        self._parse_language_configs()
        self._parse_cloud_provider_configs()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'database': 'aqea',
                'username': 'aqea',
                'password': 'aqea',
                'pool_size': 10
            },
            'languages': {
                'de': {
                    'name': 'German',
                    'estimated_entries': 800000,
                    'alphabet_ranges': [
                        {'start': 'A', 'end': 'E', 'weight': 0.2},
                        {'start': 'F', 'end': 'J', 'weight': 0.15},
                        {'start': 'K', 'end': 'O', 'weight': 0.175},
                        {'start': 'P', 'end': 'T', 'weight': 0.225},
                        {'start': 'U', 'end': 'Z', 'weight': 0.25}
                    ]
                },
                'en': {
                    'name': 'English',
                    'estimated_entries': 6000000,
                    'alphabet_ranges': [
                        {'start': 'A', 'end': 'E', 'weight': 0.2},
                        {'start': 'F', 'end': 'J', 'weight': 0.15},
                        {'start': 'K', 'end': 'O', 'weight': 0.175},
                        {'start': 'P', 'end': 'T', 'weight': 0.225},
                        {'start': 'U', 'end': 'Z', 'weight': 0.25}
                    ]
                },
                'fr': {
                    'name': 'French',
                    'estimated_entries': 4000000,
                    'alphabet_ranges': [
                        {'start': 'A', 'end': 'E', 'weight': 0.2},
                        {'start': 'F', 'end': 'J', 'weight': 0.15},
                        {'start': 'K', 'end': 'O', 'weight': 0.175},
                        {'start': 'P', 'end': 'T', 'weight': 0.225},
                        {'start': 'U', 'end': 'Z', 'weight': 0.25}
                    ]
                },
                'es': {
                    'name': 'Spanish',
                    'estimated_entries': 1000000,
                    'alphabet_ranges': [
                        {'start': 'A', 'end': 'E', 'weight': 0.2},
                        {'start': 'F', 'end': 'J', 'weight': 0.15},
                        {'start': 'K', 'end': 'O', 'weight': 0.175},
                        {'start': 'P', 'end': 'T', 'weight': 0.225},
                        {'start': 'U', 'end': 'Z', 'weight': 0.25}
                    ]
                }
            },
            'cloud_providers': {
                'hetzner': {
                    'name': 'Hetzner Cloud',
                    'master_instance_type': 'cx21',
                    'worker_instance_type': 'cx11',
                    'cost_per_hour': 0.015,
                    'max_workers': 20,
                    'regions': ['nbg1', 'fsn1', 'hel1']
                },
                'digitalocean': {
                    'name': 'DigitalOcean',
                    'master_instance_type': 's-2vcpu-4gb',
                    'worker_instance_type': 's-1vcpu-2gb',
                    'cost_per_hour': 0.024,
                    'max_workers': 20,
                    'regions': ['fra1', 'ams3', 'nyc1']
                }
            },
            'data_sources': {
                'wiktionary': {
                    'request_delay': 0.2,
                    'batch_size': 50,
                    'max_retries': 3,
                    'timeout': 30
                }
            },
            'extraction': {
                'default_batch_size': 50,
                'progress_report_interval': 100,
                'max_definitions': 3,
                'max_forms': 5
            }
        }
    
    def _load_from_environment(self):
        """Load configuration overrides from environment variables."""
        # Database overrides
        if os.getenv('DATABASE_URL'):
            # Parse DATABASE_URL format: postgresql://user:pass@host:port/db
            import urllib.parse as urlparse
            url = urlparse.urlparse(os.getenv('DATABASE_URL'))
            self.data.setdefault('database', {}).update({
                'host': url.hostname or 'localhost',
                'port': url.port or 5432,
                'database': url.path.lstrip('/') or 'aqea',
                'username': url.username or 'aqea',
                'password': url.password or 'aqea'
            })
        
        # Individual database settings
        db_config = self.data.setdefault('database', {})
        db_config.update({
            k: os.getenv(f'DB_{k.upper()}', v)
            for k, v in db_config.items()
            if f'DB_{k.upper()}' in os.environ
        })
        
        # Worker settings
        if os.getenv('WORKER_ID'):
            self.data['worker_id'] = os.getenv('WORKER_ID')
        
        if os.getenv('MASTER_HOST'):
            self.data['master_host'] = os.getenv('MASTER_HOST')
        
        if os.getenv('MASTER_PORT'):
            self.data['master_port'] = int(os.getenv('MASTER_PORT'))
    
    def _parse_database_config(self):
        """Parse database configuration."""
        db_data = self.data.get('database', {})
        self.database = DatabaseConfig(
            host=db_data.get('host', 'localhost'),
            port=int(db_data.get('port', 5432)),
            database=db_data.get('database', 'aqea'),
            username=db_data.get('username', 'aqea'),
            password=db_data.get('password', 'aqea'),
            pool_size=int(db_data.get('pool_size', 10))
        )
    
    def _parse_language_configs(self):
        """Parse language configurations."""
        languages_data = self.data.get('languages', {})
        
        for lang_code, lang_data in languages_data.items():
            self.languages[lang_code] = LanguageConfig(
                name=lang_data.get('name', lang_code.title()),
                estimated_entries=int(lang_data.get('estimated_entries', 100000)),
                alphabet_ranges=lang_data.get('alphabet_ranges', []),
                supported_pos=lang_data.get('supported_pos', ["noun", "verb", "adjective", "adverb"]),
                frequency_threshold=int(lang_data.get('frequency_threshold', 1))
            )
    
    def _parse_cloud_provider_configs(self):
        """Parse cloud provider configurations."""
        providers_data = self.data.get('cloud_providers', {})
        
        for provider_name, provider_data in providers_data.items():
            self.cloud_providers[provider_name] = CloudProviderConfig(
                name=provider_data.get('name', provider_name.title()),
                master_instance_type=provider_data.get('master_instance_type', 'medium'),
                worker_instance_type=provider_data.get('worker_instance_type', 'small'),
                cost_per_hour=float(provider_data.get('cost_per_hour', 0.02)),
                max_workers=int(provider_data.get('max_workers', 10)),
                regions=provider_data.get('regions', [])
            )
    
    def get_language_config(self, language: str) -> Optional[LanguageConfig]:
        """Get configuration for a specific language."""
        return self.languages.get(language.lower())
    
    def get_cloud_provider_config(self, provider: str) -> Optional[CloudProviderConfig]:
        """Get configuration for a specific cloud provider."""
        return self.cloud_providers.get(provider.lower())
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)."""
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value by key (supports dot notation)."""
        keys = key.split('.')
        data = self.data
        
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        data[keys[-1]] = value
    
    def save(self, file_path: Optional[str] = None):
        """Save configuration to file."""
        file_path = file_path or self.config_file
        
        # Create directory if it doesn't exist
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.data, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {file_path}: {e}")
    
    @classmethod
    def load(cls, config_file: str) -> 'Config':
        """Load configuration from file."""
        return cls(config_file)
    
    def __repr__(self) -> str:
        return f"Config(languages={list(self.languages.keys())}, providers={list(self.cloud_providers.keys())})" 
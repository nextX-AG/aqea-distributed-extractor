"""
Cost and Performance Estimator for AQEA Distributed Extractor

Estimates costs, performance, and resource requirements for different scenarios.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .config import Config, LanguageConfig, CloudProviderConfig

logger = logging.getLogger(__name__)


@dataclass
class EstimationResult:
    """Result of cost and performance estimation."""
    language: str
    servers: int
    estimated_entries: int
    processing_time_hours: float
    cost_total: float
    cost_currency: str
    entries_per_minute: float
    speedup_factor: float
    efficiency_metrics: Dict[str, Any]


class CostEstimator:
    """Estimates costs and performance for distributed extraction."""
    
    # Base performance assumptions
    BASE_ENTRIES_PER_MINUTE = 50  # Single server performance
    COORDINATION_OVERHEAD = 0.1   # 10% overhead for coordination
    API_RATE_LIMIT_FACTOR = 0.95  # 5% reduction due to API limits
    
    def __init__(self, config: Config):
        self.config = config
    
    def calculate(
        self,
        language: str,
        servers: int,
        hours: Optional[float] = None,
        cloud_provider: str = 'hetzner'
    ) -> EstimationResult:
        """Calculate cost and performance estimation."""
        
        # Get language configuration
        lang_config = self.config.get_language_config(language)
        if not lang_config:
            raise ValueError(f"Language '{language}' not supported")
        
        # Get cloud provider configuration
        provider_config = self.config.get_cloud_provider_config(cloud_provider)
        if not provider_config:
            raise ValueError(f"Cloud provider '{cloud_provider}' not supported")
        
        # Calculate performance metrics
        estimated_entries = lang_config.estimated_entries
        
        # Effective processing rate with overhead and limits
        single_server_rate = self.BASE_ENTRIES_PER_MINUTE
        multi_server_rate = single_server_rate * servers * (1 - self.COORDINATION_OVERHEAD) * self.API_RATE_LIMIT_FACTOR
        
        # Calculate processing time
        if hours is None:
            processing_time_hours = estimated_entries / (multi_server_rate * 60)
        else:
            processing_time_hours = hours
            estimated_entries = int(multi_server_rate * 60 * hours)
        
        # Calculate costs
        total_cost = self._calculate_costs(servers, processing_time_hours, provider_config)
        
        # Calculate speedup factor
        single_server_time = estimated_entries / (single_server_rate * 60)
        speedup_factor = single_server_time / processing_time_hours
        
        # Efficiency metrics
        efficiency_metrics = self._calculate_efficiency_metrics(
            servers, processing_time_hours, estimated_entries, 
            single_server_rate, multi_server_rate, provider_config
        )
        
        return EstimationResult(
            language=language,
            servers=servers,
            estimated_entries=estimated_entries,
            processing_time_hours=processing_time_hours,
            cost_total=total_cost,
            cost_currency='EUR',  # Assuming EUR for most providers
            entries_per_minute=multi_server_rate,
            speedup_factor=speedup_factor,
            efficiency_metrics=efficiency_metrics
        )
    
    def _calculate_costs(
        self,
        servers: int,
        hours: float,
        provider_config: CloudProviderConfig
    ) -> float:
        """Calculate total costs for the deployment."""
        
        # Master server cost (always 1)
        master_cost = 1 * provider_config.cost_per_hour * hours
        
        # Worker server costs
        worker_cost = servers * provider_config.cost_per_hour * hours
        
        # Additional costs (bandwidth, storage, etc.) - estimated 10% overhead
        overhead_cost = (master_cost + worker_cost) * 0.1
        
        return master_cost + worker_cost + overhead_cost
    
    def _calculate_efficiency_metrics(
        self,
        servers: int,
        hours: float,
        entries: int,
        single_rate: float,
        multi_rate: float,
        provider_config: CloudProviderConfig
    ) -> Dict[str, Any]:
        """Calculate various efficiency metrics."""
        
        # Cost per entry
        total_cost = self._calculate_costs(servers, hours, provider_config)
        cost_per_entry = total_cost / entries if entries > 0 else 0
        
        # Parallel efficiency
        theoretical_max_rate = single_rate * servers
        parallel_efficiency = (multi_rate / theoretical_max_rate) * 100 if theoretical_max_rate > 0 else 0
        
        # Resource utilization
        resource_hours = servers * hours
        entry_throughput = entries / resource_hours if resource_hours > 0 else 0
        
        # Time to completion for different scenarios
        time_scenarios = self._calculate_time_scenarios(entries, single_rate)
        
        # ROI calculation
        opportunity_cost = hours * 20  # Assume 20 EUR/hour opportunity cost for laptop time
        roi_factor = opportunity_cost / total_cost if total_cost > 0 else 0
        
        return {
            'cost_per_entry': round(cost_per_entry, 6),
            'parallel_efficiency_percent': round(parallel_efficiency, 1),
            'entries_per_resource_hour': round(entry_throughput, 1),
            'coordination_overhead_percent': self.COORDINATION_OVERHEAD * 100,
            'api_limit_reduction_percent': (1 - self.API_RATE_LIMIT_FACTOR) * 100,
            'time_scenarios': time_scenarios,
            'roi_factor': round(roi_factor, 2),
            'break_even_point_hours': round(opportunity_cost / (total_cost / hours), 1) if total_cost > 0 else 0
        }
    
    def _calculate_time_scenarios(self, entries: int, single_rate: float) -> Dict[str, float]:
        """Calculate time requirements for different server counts."""
        scenarios = {}
        
        for server_count in [1, 2, 3, 5, 10]:
            effective_rate = single_rate * server_count * (1 - self.COORDINATION_OVERHEAD) * self.API_RATE_LIMIT_FACTOR
            time_hours = entries / (effective_rate * 60)
            scenarios[f'{server_count}_servers'] = round(time_hours, 2)
        
        return scenarios
    
    def compare_scenarios(
        self,
        language: str,
        scenarios: list,
        cloud_provider: str = 'hetzner'
    ) -> Dict[str, EstimationResult]:
        """Compare multiple scenarios."""
        results = {}
        
        for scenario in scenarios:
            if isinstance(scenario, dict):
                servers = scenario.get('servers', 1)
                hours = scenario.get('hours')
                name = scenario.get('name', f'{servers}_servers')
            else:
                servers = scenario
                hours = None
                name = f'{servers}_servers'
            
            try:
                result = self.calculate(language, servers, hours, cloud_provider)
                results[name] = result
            except Exception as e:
                logger.error(f"Failed to calculate scenario {name}: {e}")
        
        return results
    
    def optimize_server_count(
        self,
        language: str,
        max_cost: float,
        max_time_hours: float,
        cloud_provider: str = 'hetzner'
    ) -> Optional[EstimationResult]:
        """Find optimal server count within constraints."""
        
        provider_config = self.config.get_cloud_provider_config(cloud_provider)
        if not provider_config:
            return None
        
        best_result = None
        best_efficiency = 0
        
        # Test different server counts
        for servers in range(1, min(provider_config.max_workers, 21)):
            try:
                result = self.calculate(language, servers, None, cloud_provider)
                
                # Check constraints
                if result.cost_total > max_cost:
                    continue
                
                if result.processing_time_hours > max_time_hours:
                    continue
                
                # Calculate efficiency score (entries per unit cost per hour)
                efficiency = result.estimated_entries / (result.cost_total * result.processing_time_hours)
                
                if efficiency > best_efficiency:
                    best_efficiency = efficiency
                    best_result = result
                    
            except Exception as e:
                logger.warning(f"Failed to calculate for {servers} servers: {e}")
                continue
        
        return best_result
    
    def get_language_comparison(
        self,
        servers: int = 5,
        cloud_provider: str = 'hetzner'
    ) -> Dict[str, EstimationResult]:
        """Compare extraction costs across different languages."""
        results = {}
        
        for language_code in self.config.languages.keys():
            try:
                result = self.calculate(language_code, servers, None, cloud_provider)
                results[language_code] = result
            except Exception as e:
                logger.error(f"Failed to calculate for language {language_code}: {e}")
        
        return results
    
    def estimate_total_project_cost(
        self,
        languages: list,
        servers: int = 5,
        cloud_provider: str = 'hetzner'
    ) -> Dict[str, Any]:
        """Estimate total cost for extracting multiple languages."""
        
        total_cost = 0
        total_time = 0
        total_entries = 0
        language_results = {}
        
        for language in languages:
            try:
                result = self.calculate(language, servers, None, cloud_provider)
                language_results[language] = result
                total_cost += result.cost_total
                total_time += result.processing_time_hours
                total_entries += result.estimated_entries
            except Exception as e:
                logger.error(f"Failed to calculate for language {language}: {e}")
        
        # Calculate project summary
        average_rate = total_entries / (total_time * 60) if total_time > 0 else 0
        cost_per_entry = total_cost / total_entries if total_entries > 0 else 0
        
        return {
            'total_cost': round(total_cost, 2),
            'total_time_hours': round(total_time, 2),
            'total_entries': total_entries,
            'average_rate_per_minute': round(average_rate, 1),
            'cost_per_entry': round(cost_per_entry, 6),
            'language_breakdown': language_results,
            'sequential_vs_parallel': {
                'sequential_time_hours': total_time,
                'parallel_time_hours': max(r.processing_time_hours for r in language_results.values()) if language_results else 0,
                'time_saved_hours': total_time - max(r.processing_time_hours for r in language_results.values()) if language_results else 0
            }
        } 
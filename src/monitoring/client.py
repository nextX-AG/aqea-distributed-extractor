"""
Status Client for AQEA Distributed Extractor

Retrieves status information from the master coordinator.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from aiohttp import ClientSession, ClientTimeout, ClientError

logger = logging.getLogger(__name__)


class StatusClient:
    """Client for retrieving status from master coordinator."""
    
    def __init__(self, master_host: str, master_port: int = 8080, timeout: int = 10):
        self.master_host = master_host
        self.master_port = master_port
        self.base_url = f"http://{master_host}:{master_port}"
        self.timeout = ClientTimeout(total=timeout)
        
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status from master coordinator."""
        try:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/status") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise ClientError(f"HTTP {response.status}: {response.reason}")
        except Exception as e:
            logger.error(f"Failed to get status from {self.base_url}: {e}")
            raise
    
    async def get_health(self) -> Dict[str, Any]:
        """Get health check from master coordinator."""
        try:
            async with ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/health") as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise ClientError(f"HTTP {response.status}: {response.reason}")
        except Exception as e:
            logger.error(f"Failed to get health from {self.base_url}: {e}")
            raise
    
    async def is_master_available(self) -> bool:
        """Check if master coordinator is available."""
        try:
            await self.get_health()
            return True
        except Exception:
            return False
    
    async def wait_for_master(self, max_wait_seconds: int = 60, check_interval: int = 5) -> bool:
        """Wait for master coordinator to become available."""
        logger.info(f"Waiting for master coordinator at {self.base_url}...")
        
        for attempt in range(max_wait_seconds // check_interval):
            if await self.is_master_available():
                logger.info("Master coordinator is available")
                return True
            
            logger.debug(f"Master not available, attempt {attempt + 1}/{max_wait_seconds // check_interval}")
            await asyncio.sleep(check_interval)
        
        logger.error(f"Master coordinator not available after {max_wait_seconds} seconds")
        return False
    
    async def get_worker_details(self, worker_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about workers."""
        status = await self.get_status()
        workers = status.get('workers', {}).get('details', [])
        
        if worker_id:
            # Find specific worker
            for worker in workers:
                if worker.get('worker_id') == worker_id:
                    return worker
            raise ValueError(f"Worker {worker_id} not found")
        
        return {'workers': workers}
    
    async def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of extraction progress."""
        status = await self.get_status()
        
        progress = status.get('progress', {})
        overview = status.get('overview', {})
        workers = status.get('workers', {})
        
        return {
            'language': overview.get('language', 'unknown'),
            'source': overview.get('source', 'unknown'),
            'started_at': overview.get('started_at'),
            'runtime_hours': overview.get('runtime_hours', 0),
            'progress_percent': progress.get('progress_percent', 0),
            'entries_processed': progress.get('total_processed_entries', 0),
            'entries_estimated': progress.get('total_estimated_entries', 0),
            'current_rate': progress.get('current_rate_per_minute', 0),
            'eta_hours': progress.get('eta_hours'),
            'active_workers': workers.get('active', 0),
            'total_workers': workers.get('total', 0),
            'status': overview.get('status', 'unknown')
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics and statistics."""
        status = await self.get_status()
        
        workers = status.get('workers', {}).get('details', [])
        work_units = status.get('work_units', {})
        
        # Calculate performance metrics
        total_rate = sum(w.get('average_rate', 0) for w in workers)
        active_workers = [w for w in workers if w.get('status') == 'working']
        
        # Work unit statistics
        completed_units = work_units.get('completed', 0)
        total_units = work_units.get('total', 1)
        completion_rate = (completed_units / total_units) * 100 if total_units > 0 else 0
        
        # Worker efficiency
        worker_efficiency = []
        for worker in workers:
            if worker.get('total_processed', 0) > 0:
                efficiency = {
                    'worker_id': worker.get('worker_id'),
                    'total_processed': worker.get('total_processed', 0),
                    'average_rate': worker.get('average_rate', 0),
                    'status': worker.get('status', 'unknown')
                }
                worker_efficiency.append(efficiency)
        
        return {
            'total_processing_rate': total_rate,
            'active_worker_count': len(active_workers),
            'work_unit_completion_rate': completion_rate,
            'worker_efficiency': worker_efficiency,
            'system_health': 'healthy' if len(active_workers) > 0 else 'idle'
        }
    
    async def monitor_continuously(
        self, 
        interval_seconds: int = 30,
        max_duration_minutes: Optional[int] = None,
        callback=None
    ) -> None:
        """Monitor status continuously and call callback with updates."""
        logger.info(f"Starting continuous monitoring (interval: {interval_seconds}s)")
        
        start_time = asyncio.get_event_loop().time()
        max_duration_seconds = max_duration_minutes * 60 if max_duration_minutes else None
        
        try:
            while True:
                try:
                    # Get current status
                    status = await self.get_status()
                    progress = await self.get_progress_summary()
                    
                    # Call callback if provided
                    if callback:
                        callback(status, progress)
                    
                    # Check if extraction is complete
                    if progress.get('progress_percent', 0) >= 100:
                        logger.info("Extraction completed, stopping monitoring")
                        break
                    
                    # Check maximum duration
                    if max_duration_seconds:
                        elapsed = asyncio.get_event_loop().time() - start_time
                        if elapsed >= max_duration_seconds:
                            logger.info(f"Maximum monitoring duration reached ({max_duration_minutes} minutes)")
                            break
                    
                    # Wait for next check
                    await asyncio.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"Error during monitoring: {e}")
                    # Continue monitoring even if individual checks fail
                    await asyncio.sleep(interval_seconds)
                    
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            raise


class MetricsCollector:
    """Collects and aggregates metrics over time."""
    
    def __init__(self, max_samples: int = 100):
        self.max_samples = max_samples
        self.samples = []
        
    def add_sample(self, status: Dict[str, Any], progress: Dict[str, Any]):
        """Add a status sample to the collection."""
        import time
        
        sample = {
            'timestamp': time.time(),
            'progress_percent': progress.get('progress_percent', 0),
            'entries_processed': progress.get('entries_processed', 0),
            'current_rate': progress.get('current_rate', 0),
            'active_workers': progress.get('active_workers', 0),
            'eta_hours': progress.get('eta_hours')
        }
        
        self.samples.append(sample)
        
        # Keep only recent samples
        if len(self.samples) > self.max_samples:
            self.samples.pop(0)
    
    def get_trends(self) -> Dict[str, Any]:
        """Calculate trends from collected samples."""
        if len(self.samples) < 2:
            return {}
        
        first = self.samples[0]
        last = self.samples[-1]
        
        time_delta = last['timestamp'] - first['timestamp']
        if time_delta <= 0:
            return {}
        
        # Calculate rates of change
        progress_rate = (last['progress_percent'] - first['progress_percent']) / time_delta * 3600  # per hour
        entry_rate = (last['entries_processed'] - first['entries_processed']) / time_delta * 60  # per minute
        
        # Calculate averages
        avg_rate = sum(s['current_rate'] for s in self.samples) / len(self.samples)
        avg_workers = sum(s['active_workers'] for s in self.samples) / len(self.samples)
        
        return {
            'progress_rate_per_hour': round(progress_rate, 2),
            'average_entry_rate': round(entry_rate, 1),
            'average_processing_rate': round(avg_rate, 1),
            'average_active_workers': round(avg_workers, 1),
            'sample_count': len(self.samples),
            'monitoring_duration_minutes': round(time_delta / 60, 1)
        } 
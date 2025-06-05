"""
Extraction Worker for AQEA Distributed System

Processes work units assigned by the master coordinator.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from aiohttp import ClientSession
import socket

from ..data_sources.factory import DataSourceFactory
from ..aqea.converter import AQEAConverter
from ..database import get_database

logger = logging.getLogger(__name__)


class ExtractionWorker:
    """Worker that processes extraction tasks."""
    
    def __init__(self, config, worker_id: str, master_host: str, master_port: int = 8080):
        self.config = config
        self.worker_id = worker_id
        self.master_host = master_host
        self.master_port = master_port
        self.master_url = f"http://{master_host}:{master_port}"
        
        # Worker state
        self.is_running = False
        self.current_work = None
        self.session = None
        self.database = None  # Supabase connection
        
        # Statistics
        self.total_processed = 0
        self.start_time = None
        self.processing_rate = 0.0
        
        # Get local IP address
        self.local_ip = self._get_local_ip()
        
    def _get_local_ip(self) -> str:
        """Get the local IP address of this worker."""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    async def register_with_master(self) -> bool:
        """Register this worker with the master coordinator."""
        try:
            async with self.session.post(
                f"{self.master_url}/api/register",
                json={
                    'worker_id': self.worker_id,
                    'ip_address': self.local_ip
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Successfully registered worker {self.worker_id}")
                    return result.get('success', False)
                else:
                    logger.error(f"Failed to register: HTTP {response.status}")
                    return False
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False
    
    async def request_work(self) -> Optional[Dict[str, Any]]:
        """Request work from the master coordinator."""
        try:
            async with self.session.get(
                f"{self.master_url}/api/work",
                params={'worker_id': self.worker_id}
            ) as response:
                if response.status == 200:
                    work_data = await response.json()
                    logger.info(f"Received work unit: {work_data['id']}")
                    return work_data
                elif response.status == 204:
                    logger.debug("No work available")
                    return None
                else:
                    logger.error(f"Failed to get work: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Failed to request work: {e}")
            return None
    
    async def report_progress(self, work_id: str, entries_processed: int, processing_rate: float):
        """Report progress to the master coordinator."""
        try:
            async with self.session.post(
                f"{self.master_url}/api/progress",
                json={
                    'worker_id': self.worker_id,
                    'work_id': work_id,
                    'entries_processed': entries_processed,
                    'processing_rate': processing_rate
                }
            ) as response:
                if response.status != 200:
                    logger.warning(f"Failed to report progress: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Failed to report progress: {e}")
    
    async def report_completion(self, work_id: str, success: bool, final_count: int, errors: List[str]):
        """Report work completion to the master coordinator."""
        try:
            async with self.session.post(
                f"{self.master_url}/api/complete",
                json={
                    'worker_id': self.worker_id,
                    'work_id': work_id,
                    'success': success,
                    'final_count': final_count,
                    'errors': errors
                }
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully reported completion of {work_id}")
                else:
                    logger.error(f"Failed to report completion: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Failed to report completion: {e}")
    
    async def process_work_unit(self, work_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single work unit."""
        work_id = work_data['id']
        language = work_data['language']
        source = work_data['source']
        start_range = work_data['start_range']
        end_range = work_data['end_range']
        
        logger.info(f"Processing work unit {work_id}: {language} {start_range}-{end_range} from {source}")
        
        entries_processed = 0
        errors = []
        success = False
        
        try:
            # Create data source
            data_source = DataSourceFactory.create(source, self.config)
            
            # Create AQEA converter with database connection
            aqea_converter = AQEAConverter(self.config, language, self.database, self.worker_id)
            
            # Process entries in batches
            batch_size = 50
            progress_report_interval = 100  # Report every 100 entries
            
            start_time = time.time()
            last_progress_report = 0
            
            async for batch in data_source.extract_range(language, start_range, end_range, batch_size):
                # Convert to AQEA format
                aqea_entries = []
                for entry in batch:
                    try:
                        aqea_entry = await aqea_converter.convert(entry)
                        if aqea_entry:
                            aqea_entries.append(aqea_entry)
                    except Exception as e:
                        errors.append(f"Conversion error for {entry.get('word', 'unknown')}: {str(e)}")
                        continue
                
                # Store entries (database, file, etc.)
                if aqea_entries:
                    await self._store_entries(aqea_entries)
                
                entries_processed += len(batch)
                
                # Calculate processing rate
                elapsed_time = time.time() - start_time
                self.processing_rate = (entries_processed / elapsed_time) * 60  # entries per minute
                
                # Report progress periodically
                if entries_processed - last_progress_report >= progress_report_interval:
                    # Report to HTTP master
                    await self.report_progress(work_id, entries_processed, self.processing_rate)
                    # Update database (if available)
                    if self.database:
                        await self.database.update_work_progress(work_id, entries_processed, self.processing_rate)
                    
                    last_progress_report = entries_processed
                    
                    logger.info(f"Progress: {entries_processed} entries processed "
                              f"({self.processing_rate:.1f} entries/min)")
            
            success = True
            logger.info(f"Completed work unit {work_id}: {entries_processed} entries processed")
            
        except Exception as e:
            error_msg = f"Fatal error processing work unit {work_id}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        return {
            'work_id': work_id,
            'success': success,
            'entries_processed': entries_processed,
            'errors': errors,
            'processing_rate': self.processing_rate
        }
    
    async def _store_entries(self, aqea_entries: List[Any]):
        """Store AQEA entries to Supabase database or local placeholder."""
        if not aqea_entries:
            return {'inserted': 0, 'errors': []}
        
        if self.database:
            logger.debug(f"Storing {len(aqea_entries)} AQEA entries to Supabase")
            
            try:
                # Store entries in Supabase
                result = await self.database.store_aqea_entries(aqea_entries)
                
                if result['inserted'] > 0:
                    logger.info(f"✅ Stored {result['inserted']} entries to Supabase (Success rate: {result['success_rate']:.1%})")
                
                if result['errors']:
                    logger.warning(f"⚠️ {len(result['errors'])} errors occurred during storage")
                    
                return result
                
            except Exception as e:
                logger.error(f"❌ Failed to store entries to Supabase: {e}")
                return {'inserted': 0, 'errors': [str(e)]}
        else:
            # Fallback: Store to local JSON files
            try:
                import os
                import json
                from datetime import datetime
                
                # Create output directory
                output_dir = "extracted_data"
                os.makedirs(output_dir, exist_ok=True)
                
                # Create filename with timestamp and worker ID
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{output_dir}/aqea_entries_{self.worker_id}_{timestamp}.json"
                
                # Convert entries to dict format
                entries_data = []
                for entry in aqea_entries:
                    if hasattr(entry, 'to_dict'):
                        entries_data.append(entry.to_dict())
                    else:
                        entries_data.append(entry)
                
                # Write to JSON file
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({
                        'worker_id': self.worker_id,
                        'timestamp': datetime.now().isoformat(),
                        'entry_count': len(entries_data),
                        'entries': entries_data
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"💾 Stored {len(aqea_entries)} AQEA entries to local file: {filename}")
                return {'inserted': len(aqea_entries), 'errors': []}
                
            except Exception as e:
                logger.error(f"❌ Failed to store entries to local file: {e}")
                return {'inserted': 0, 'errors': [str(e)]}
    
    async def work_loop(self):
        """Main work loop - request and process work units."""
        task_session = None
        while self.is_running:
            try:
                # Request work from master
                work_data = await self.request_work()
                
                if work_data:
                    self.current_work = work_data
                    
                    # Process the work unit
                    result = await self.process_work_unit(work_data)
                    
                    # Report completion to HTTP master
                    await self.report_completion(
                        result['work_id'],
                        result['success'],
                        result['entries_processed'],
                        result['errors']
                    )
                    
                    # Mark as completed in database (if available)
                    if self.database:
                        await self.database.complete_work_unit(
                        result['work_id'],
                        result['success'],
                        result['entries_processed'],
                        result['errors']
                    )
                    
                    # Update statistics
                    self.total_processed += result['entries_processed']
                    self.current_work = None
                    
                else:
                    # No work available, wait a bit
                    logger.debug("No work available, waiting...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error in work loop: {e}")
                await asyncio.sleep(10)
    
    async def heartbeat_loop(self):
        """Send periodic heartbeats to the database (if available)."""
        while self.is_running:
            try:
                # Update worker status in Supabase database (if available)
                if self.database:
                    current_work_id = self.current_work['id'] if self.current_work else None
                    status = 'working' if current_work_id else 'idle'
                    
                    await self.database.update_worker_heartbeat(
                        self.worker_id, 
                        status, 
                        current_work_id
                    )
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(60)
    
    async def cleanup_sessions(self):
        """Cleanup all client sessions properly."""
        if hasattr(self, 'session') and self.session:
            try:
                await self.session.close()
                logger.debug(f"Closed client session for worker {self.worker_id}")
            except Exception as e:
                logger.error(f"Error closing client session: {e}")
    
    async def run(self):
        """Start the worker."""
        logger.info(f"Starting extraction worker {self.worker_id}")
        logger.info(f"Local IP: {self.local_ip}")
        logger.info(f"Master: {self.master_url}")
        
        # Create HTTP session
        self.session = ClientSession()
        
        try:
            # Try to connect to Supabase database (optional for local testing)
            try:
                self.database = await get_database(self.config)
                if self.database and hasattr(self.database, 'pool') and self.database.pool:
                    logger.info("✅ Connected to Supabase database")
                else:
                    raise Exception("Database connection returned None or invalid pool")
            except Exception as e:
                logger.warning(f"⚠️ Could not connect to Supabase database: {e}")
                logger.info("📝 Running in HTTP-only mode (no database integration)")
                self.database = None
            
            # Register with master (HTTP)
            registration_attempts = 5
            for attempt in range(registration_attempts):
                # Register with HTTP master
                http_success = await self.register_with_master()
                
                # Register with Supabase database (if available)
                db_success = True  # Default to success if no database
                if self.database:
                    db_success = await self.database.register_worker(self.worker_id, self.local_ip)
                
                if http_success and db_success:
                    if self.database:
                        logger.info(f"✅ Worker {self.worker_id} registered with master and database")
                    else:
                        logger.info(f"✅ Worker {self.worker_id} registered with master (HTTP-only mode)")
                    break
                    
                logger.warning(f"Registration attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(5)
            else:
                raise RuntimeError("Failed to register with master after multiple attempts")
            
            # Start worker
            self.is_running = True
            self.start_time = datetime.now()
            
            # Run work loop and heartbeat loop (if database available)
            if self.database:
                await asyncio.gather(
                    self.work_loop(),
                    self.heartbeat_loop()
                )
            else:
                # HTTP-only mode: just run work loop
                await self.work_loop()
            
        except KeyboardInterrupt:
            logger.info(f"Worker {self.worker_id} interrupted")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {e}")
        finally:
            self.is_running = False
            # Clean up sessions
            await self.cleanup_sessions()
            
            logger.info(f"Worker {self.worker_id} stopped. Total processed: {self.total_processed}")


class WorkerMetrics:
    """Collects and manages worker performance metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.entries_processed = 0
        self.errors_count = 0
        self.processing_times = []
        
    def record_batch(self, batch_size: int, processing_time: float):
        """Record a processed batch."""
        self.entries_processed += batch_size
        self.processing_times.append(processing_time)
        
        # Keep only recent processing times for rate calculation
        if len(self.processing_times) > 100:
            self.processing_times = self.processing_times[-100:]
    
    def record_error(self):
        """Record an error."""
        self.errors_count += 1
    
    def get_rate(self) -> float:
        """Get current processing rate in entries per minute."""
        if not self.processing_times:
            return 0.0
        
        elapsed = time.time() - self.start_time
        if elapsed <= 0:
            return 0.0
        
        return (self.entries_processed / elapsed) * 60
    
    def get_average_batch_time(self) -> float:
        """Get average batch processing time."""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    def get_error_rate(self) -> float:
        """Get error rate as percentage."""
        total_operations = self.entries_processed + self.errors_count
        if total_operations == 0:
            return 0.0
        return (self.errors_count / total_operations) * 100 
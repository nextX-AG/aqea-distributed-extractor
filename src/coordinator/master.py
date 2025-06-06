"""
Master Coordinator for AQEA Distributed Extraction

Orchestrates work distribution across multiple worker instances.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from aiohttp import web, ClientSession
import json
import os
import sqlite3

from ..database import get_database
from ..aqea.schema import AQEAEntry

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON Encoder that can handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class WorkUnit:
    """A unit of work to be processed by a worker."""
    id: str
    language: str
    source: str
    start_range: str
    end_range: str
    estimated_entries: int
    status: str = 'pending'  # pending, assigned, processing, completed, failed
    worker_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    entries_processed: int = 0
    processing_rate: float = 0.0  # entries per minute
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


@dataclass
class WorkerInfo:
    """Information about a registered worker."""
    worker_id: str
    ip_address: str
    status: str = 'idle'  # idle, working, error, offline
    current_work_id: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    total_processed: int = 0
    average_rate: float = 0.0
    registered_at: Optional[datetime] = None


class MasterCoordinator:
    """Master coordinator for distributed AQEA extraction."""
    
    def __init__(self, config, language: str, source: str, expected_workers: int, port: int = 8080,
                 work_units_file: str = None):
        self.config = config
        self.language = language
        self.source = source
        self.expected_workers = expected_workers
        self.port = port
        self.work_units_file = work_units_file
        self.database = None
        
        # Work management
        self.work_queue: List[WorkUnit] = []
        self.completed_work: List[WorkUnit] = []
        self.workers: Dict[str, WorkerInfo] = {}
        
        # Statistics
        self.started_at = datetime.now()
        self.total_estimated_entries = 0
        self.total_processed_entries = 0
        
    async def create_work_plan(self) -> List[WorkUnit]:
        """Create work units based on language and source configuration."""
        # Check if we should load from a custom work units file
        if self.work_units_file and os.path.exists(self.work_units_file):
            return await self.load_work_units_from_file()
        
        # Otherwise, use the default configuration
        work_units = []
        
        # Get language configuration
        lang_config = self.config.get_language_config(self.language)
        if not lang_config:
            raise ValueError(f"No configuration found for language: {self.language}")
        
        # Create work units based on alphabet ranges
        ranges = lang_config.alphabet_ranges
        total_estimated = lang_config.estimated_entries
        
        for i, range_config in enumerate(ranges):
            estimated_for_range = int(total_estimated * range_config.get('weight', 0.2))
            
            work_unit = WorkUnit(
                id=f"{self.language}_{self.source}_{i+1:02d}",
                language=self.language,
                source=self.source,
                start_range=range_config['start'],
                end_range=range_config['end'],
                estimated_entries=estimated_for_range
            )
            work_units.append(work_unit)
        
        self.work_queue = work_units
        self.total_estimated_entries = sum(wu.estimated_entries for wu in work_units)
        
        logger.info(f"Created {len(work_units)} work units for {self.language} from {self.source}")
        logger.info(f"Total estimated entries: {self.total_estimated_entries:,}")
        
        return work_units
    
    async def load_work_units_from_file(self) -> List[WorkUnit]:
        """Load work units from a JSON file."""
        try:
            logger.info(f"Loading work units from {self.work_units_file}")
            with open(self.work_units_file, 'r', encoding='utf-8') as f:
                work_units_data = json.load(f)
            
            work_units = []
            for item in work_units_data:
                work_unit = WorkUnit(
                    id=item['work_id'],
                    language=item['language'],
                    source=item['source'],
                    start_range=item['range_start'],
                    end_range=item['range_end'],
                    estimated_entries=item['estimated_entries']
                )
                work_units.append(work_unit)
            
            self.work_queue = work_units
            self.total_estimated_entries = sum(wu.estimated_entries for wu in work_units)
            
            logger.info(f"Loaded {len(work_units)} work units from file")
            logger.info(f"Total estimated entries: {self.total_estimated_entries:,}")
            
            return work_units
        except Exception as e:
            logger.error(f"Error loading work units from file: {e}")
            logger.info("Falling back to default work plan")
            # Set work_units_file to None to use default config
            self.work_units_file = None
            return await self.create_work_plan()
    
    async def register_worker(self, worker_id: str, ip_address: str) -> bool:
        """Register a new worker."""
        if worker_id in self.workers:
            logger.warning(f"Worker {worker_id} already registered, updating info")
        
        self.workers[worker_id] = WorkerInfo(
            worker_id=worker_id,
            ip_address=ip_address,
            registered_at=datetime.now(),
            last_heartbeat=datetime.now()
        )
        
        logger.info(f"Registered worker {worker_id} from {ip_address}")
        return True
    
    async def assign_work(self, worker_id: str) -> Optional[WorkUnit]:
        """Assign next available work unit to a worker."""
        if worker_id not in self.workers:
            logger.error(f"Unknown worker {worker_id} requesting work")
            return None
        
        # Find next pending work unit
        for work_unit in self.work_queue:
            if work_unit.status == 'pending':
                work_unit.status = 'assigned'
                work_unit.worker_id = worker_id
                work_unit.assigned_at = datetime.now()
                
                # Update worker status
                worker = self.workers[worker_id]
                worker.status = 'working'
                worker.current_work_id = work_unit.id
                worker.last_heartbeat = datetime.now()
                
                logger.info(f"Assigned work unit {work_unit.id} to worker {worker_id}")
                return work_unit
        
        logger.info(f"No work available for worker {worker_id}")
        return None
    
    async def update_progress(self, worker_id: str, work_id: str, 
                           entries_processed: int, processing_rate: float) -> bool:
        """Update progress from a worker."""
        if worker_id not in self.workers:
            logger.error(f"Progress update from unknown worker {worker_id}")
            return False
        
        # Update worker info
        worker = self.workers[worker_id]
        worker.last_heartbeat = datetime.now()
        worker.average_rate = processing_rate
        
        # Update work unit
        for work_unit in self.work_queue:
            if work_unit.id == work_id and work_unit.worker_id == worker_id:
                work_unit.entries_processed = entries_processed
                work_unit.processing_rate = processing_rate
                work_unit.status = 'processing'
                break
        
        return True
    
    async def complete_work(self, worker_id: str, work_id: str, success: bool, 
                         final_count: int, errors: List[str] = None) -> bool:
        """Mark work unit as completed."""
        if errors is None:
            errors = []
        
        # Find and update work unit
        for i, work_unit in enumerate(self.work_queue):
            if work_unit.id == work_id and work_unit.worker_id == worker_id:
                work_unit.status = 'completed' if success else 'failed'
                work_unit.completed_at = datetime.now()
                work_unit.entries_processed = final_count
                work_unit.errors = errors
                
                # Move to completed queue
                completed_work = self.work_queue.pop(i)
                self.completed_work.append(completed_work)
                
                # Update worker
                worker = self.workers[worker_id]
                worker.status = 'idle'
                worker.current_work_id = None
                worker.total_processed += final_count
                worker.last_heartbeat = datetime.now()
                
                # Update totals
                if success:
                    self.total_processed_entries += final_count
                
                logger.info(f"Work unit {work_id} completed by {worker_id} - "
                          f"Success: {success}, Entries: {final_count}")
                return True
        
        logger.error(f"Could not find work unit {work_id} for worker {worker_id}")
        return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status report."""
        now = datetime.now()
        runtime = (now - self.started_at).total_seconds() / 3600  # hours
        
        # Calculate progress
        progress_percent = (self.total_processed_entries / self.total_estimated_entries * 100) \
                          if self.total_estimated_entries > 0 else 0
        
        # Calculate current processing rate
        current_rate = sum(w.average_rate for w in self.workers.values() if w.status == 'working')
        
        # Estimate remaining time
        remaining_entries = self.total_estimated_entries - self.total_processed_entries
        eta_hours = (remaining_entries / (current_rate * 60)) if current_rate > 0 else None
        
        # Worker statistics
        total_workers = len(self.workers)
        active_workers = len([w for w in self.workers.values() if w.status == 'working'])
        idle_workers = len([w for w in self.workers.values() if w.status == 'idle'])
        
        return {
            'overview': {
                'language': self.language,
                'source': self.source,
                'started_at': self.started_at.isoformat(),
                'runtime_hours': round(runtime, 2),
                'status': 'running' if active_workers > 0 else 'idle'
            },
            'progress': {
                'total_estimated_entries': self.total_estimated_entries,
                'total_processed_entries': self.total_processed_entries,
                'progress_percent': round(progress_percent, 2),
                'current_rate_per_minute': round(current_rate, 1),
                'eta_hours': round(eta_hours, 1) if eta_hours else None
            },
            'work_units': {
                'total': len(self.work_queue) + len(self.completed_work),
                'pending': len([wu for wu in self.work_queue if wu.status == 'pending']),
                'assigned': len([wu for wu in self.work_queue if wu.status == 'assigned']),
                'processing': len([wu for wu in self.work_queue if wu.status == 'processing']),
                'completed': len([wu for wu in self.completed_work if wu.status == 'completed']),
                'failed': len([wu for wu in self.completed_work if wu.status == 'failed'])
            },
            'workers': {
                'total': total_workers,
                'active': active_workers,
                'idle': idle_workers,
                'expected': self.expected_workers,
                'details': [asdict(worker) for worker in self.workers.values()]
            },
            'recent_completions': [asdict(wu) for wu in self.completed_work[-5:]]
        }
    
    # HTTP Handlers
    async def handle_register(self, request):
        """Handle worker registration."""
        data = await request.json()
        success = await self.register_worker(data['worker_id'], data['ip_address'])
        return web.json_response({'success': success})
    
    async def handle_get_work(self, request):
        """Handle work assignment requests."""
        worker_id = request.query.get('worker_id')
        if not worker_id:
            return web.json_response({'error': 'worker_id required'}, status=400)
        
        work_unit = await self.assign_work(worker_id)
        if work_unit:
            return web.json_response(asdict(work_unit), dumps=lambda obj: json.dumps(obj, cls=DateTimeEncoder))
        else:
            return web.json_response({'message': 'No work available'}, status=204)
    
    async def handle_progress(self, request):
        """Handle progress updates."""
        data = await request.json()
        success = await self.update_progress(
            data['worker_id'], data['work_id'],
            data['entries_processed'], data['processing_rate']
        )
        return web.json_response({'success': success})
    
    async def handle_complete(self, request):
        """Handle work completion notifications."""
        data = await request.json()
        success = await self.complete_work(
            data['worker_id'], data['work_id'], data['success'],
            data['final_count'], data.get('errors', [])
        )
        return web.json_response({'success': success})
    
    async def handle_status(self, request):
        """Handle status requests."""
        status = await self.get_status()
        return web.json_response(status, dumps=lambda obj: json.dumps(obj, cls=DateTimeEncoder))
    
    async def handle_health(self, request):
        """Health check endpoint."""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'workers': len(self.workers),
            'work_units': len(self.work_queue)
        })
    
    async def handle_store_entries(self, request):
        """Handle entry storage from workers."""
        data = await request.json()
        worker_id = data.get('worker_id')
        entries = data.get('entries', [])
        
        if not worker_id or not entries:
            return web.json_response({'error': 'worker_id and entries required'}, status=400)
        
        # Konvertiere Einträge in AQEAEntry-Objekte
        aqea_entries = []
        for entry_data in entries:
            try:
                # Konvertiere ISO-Datum-Strings in datetime-Objekte
                created_at = entry_data.get('created_at')
                updated_at = entry_data.get('updated_at')
                
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                
                # Erstelle AQEAEntry-Objekt
                entry = AQEAEntry(
                    address=entry_data.get('address'),
                    label=entry_data.get('label'),
                    description=entry_data.get('description'),
                    domain=entry_data.get('domain'),
                    created_at=created_at,
                    updated_at=updated_at,
                    meta=entry_data.get('meta', {}),
                    status='active',
                    created_by=worker_id
                )
                aqea_entries.append(entry)
            except Exception as e:
                logger.error(f"Fehler beim Konvertieren eines Eintrags: {e}")
        
        # Speichere Einträge in der Datenbank
        result = {'inserted': 0, 'errors': []}
        
        if self.database and hasattr(self.database, 'store_aqea_entries'):
            try:
                result = await self.database.store_aqea_entries(aqea_entries)
                logger.info(f"✅ {result.get('inserted', 0)} Einträge von Worker {worker_id} in Datenbank gespeichert")
            except Exception as e:
                error_msg = f"Fehler beim Speichern von Einträgen in Datenbank: {e}"
                logger.error(f"❌ {error_msg}")
                result['errors'].append(error_msg)
        else:
            # Fallback: Speichere lokal als JSON
            try:
                # Erstelle Verzeichnis, falls es nicht existiert
                os.makedirs('extracted_data', exist_ok=True)
                
                # Erstelle Dateinamen mit Zeitstempel
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"extracted_data/master_entries_{worker_id}_{timestamp}.json"
                
                # Konvertiere Einträge in JSON-serialisierbares Format
                entries_data = []
                for entry in aqea_entries:
                    entry_dict = {
                        'address': entry.address,
                        'label': entry.label,
                        'description': entry.description,
                        'domain': entry.domain,
                        'created_at': entry.created_at.isoformat() if isinstance(entry.created_at, datetime) else entry.created_at,
                        'updated_at': entry.updated_at.isoformat() if isinstance(entry.updated_at, datetime) else entry.updated_at,
                        'meta': entry.meta
                    }
                    entries_data.append(entry_dict)
                
                # Speichere in JSON-Datei
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(entries_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ {len(entries_data)} Einträge von Worker {worker_id} in lokale Datei gespeichert: {filename}")
                result = {'inserted': len(entries_data), 'errors': []}
            except Exception as e:
                error_msg = f"Fehler beim lokalen Speichern: {e}"
                logger.error(f"❌ {error_msg}")
                result['errors'].append(error_msg)
        
        return web.json_response(result)
    
    async def run(self):
        """Start the master coordinator server."""
        logger.info("Starting AQEA Master Coordinator")
        
        # Initialize database
        await self.initialize_db()
        
        # Create work plan
        await self.create_work_plan()
        
        # Setup web application
        app = web.Application()
        app.router.add_post('/api/register', self.handle_register)
        app.router.add_get('/api/work', self.handle_get_work)
        app.router.add_post('/api/progress', self.handle_progress)
        app.router.add_post('/api/complete', self.handle_complete)
        app.router.add_get('/api/status', self.handle_status)
        app.router.add_get('/api/health', self.handle_health)
        app.router.add_post('/api/store_entries', self.handle_store_entries)
        
        # Start server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        
        logger.info(f"Master coordinator started on port {self.port}")
        logger.info(f"Waiting for {self.expected_workers} workers to connect...")
        
        await site.start()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(10)
                
                # Log periodic status
                status = await self.get_status()
                active_workers = status['workers']['active']
                progress = status['progress']['progress_percent']
                
                if active_workers > 0:
                    logger.info(f"Progress: {progress:.1f}% - "
                              f"{active_workers} workers active - "
                              f"{status['progress']['current_rate_per_minute']:.1f} entries/min")
                
        except asyncio.CancelledError:
            logger.info("Master coordinator shutting down")
            await runner.cleanup()

    async def initialize_db(self):
        """Initialize database connection."""
        if not self.database:
            logger.info("Initialisiere Datenbankverbindung...")
            
            # Try to connect to database
            try:
                self.database = await get_database(self.config)
                if self.database:
                    logger.info("✅ Datenbankverbindung hergestellt")
                    
                    # Speichere Arbeitspakete in der Datenbank
                    if hasattr(self.database, 'connection'):
                        # SQLite Datenbank (lokale Implementierung)
                        await self._initialize_work_units_in_db()
                        logger.info("✅ Arbeitspakete in SQLite initialisiert")
                    else:
                        # Andere Datenbank (z.B. Supabase)
                        logger.info("⚠️ Arbeitspakete werden nicht in Datenbank gespeichert")
                else:
                    logger.warning("⚠️ Keine Datenbankverbindung verfügbar, verwende In-Memory-Speicherung")
            except Exception as e:
                logger.error(f"❌ Datenbankverbindung fehlgeschlagen: {e}")
                self.database = None
                
        return self.database is not None
    
    async def _initialize_work_units_in_db(self):
        """Speichere die Arbeitspakete in der SQLite-Datenbank."""
        if not self.database or not hasattr(self.database, 'connection'):
            return
            
        try:
            # Prüfe, ob bereits Arbeitspakete in der Datenbank sind
            cursor = self.database.connection.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM work_units")
            count = cursor.fetchone()['count']
            
            if count > 0:
                # Lade bestehende Arbeitspakete aus der Datenbank
                cursor.execute("SELECT * FROM work_units")
                rows = cursor.fetchall()
                
                # Konvertiere zu WorkUnit-Objekten
                for row in rows:
                    work_unit = WorkUnit(
                        id=row['work_id'],
                        language=row['language'],
                        source=row['source'],
                        start_range=row['start_range'],
                        end_range=row['end_range'],
                        estimated_entries=row['estimated_entries'],
                        status=row['status'],
                    )
                    
                    # Aktualisiere nur, wenn nicht bereits in self.work_units
                    if work_unit.id not in [w.id for w in self.work_queue]:
                        self.work_queue.append(work_unit)
                        
                logger.info(f"✅ {len(rows)} bestehende Arbeitspakete aus Datenbank geladen")
                return
                
            # Arbeitspakete in die Datenbank speichern
            for work_unit in self.work_queue:
                cursor.execute("""
                    INSERT INTO work_units (
                        work_id, language, source, start_range, end_range, 
                        estimated_entries, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(work_id) DO UPDATE SET
                        language = excluded.language,
                        source = excluded.source,
                        start_range = excluded.start_range,
                        end_range = excluded.end_range,
                        estimated_entries = excluded.estimated_entries,
                        status = excluded.status
                """, (
                    work_unit.id,
                    work_unit.language,
                    work_unit.source,
                    work_unit.start_range,
                    work_unit.end_range,
                    work_unit.estimated_entries,
                    work_unit.status,
                ))
                
            self.database.connection.commit()
            logger.info(f"✅ {len(self.work_queue)} Arbeitspakete in Datenbank gespeichert")
                
        except Exception as e:
            logger.error(f"❌ Fehler beim Initialisieren der Arbeitspakete in der Datenbank: {e}")
            if hasattr(self.database, 'connection'):
                self.database.connection.rollback() 
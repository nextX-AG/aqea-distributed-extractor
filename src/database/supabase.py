"""
Supabase Database Interface for AQEA Distributed Extractor

Zentrale Datenbank-Anbindung für alle Worker.
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncpg
import json

from ..aqea.schema import AQEAEntry

logger = logging.getLogger(__name__)


class SupabaseDatabase:
    """Zentrale Supabase-Datenbank für alle Worker."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool = None
        
        # Supabase Connection Details
        self.database_url = self._get_database_url()
        self.pool_size = config.get('database', {}).get('pool_size', 10)
        
    def _get_database_url(self) -> str:
        """Get Supabase database URL from config or environment."""
        # Try environment variable first
        if os.getenv('DATABASE_URL'):
            return os.getenv('DATABASE_URL')
        
        # Try from config
        db_config = self.config.get('database', {})
        if 'url' in db_config:
            return db_config['url']
        
        # Construct from individual components
        host = db_config.get('host', 'localhost')
        port = db_config.get('port', 5432)
        database = db_config.get('database', 'postgres')
        username = db_config.get('username', 'postgres')
        password = db_config.get('password', '')
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode=require"
    
    async def connect(self) -> bool:
        """Establish connection pool to Supabase."""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=self.pool_size,
                command_timeout=60
            )
            
            # Test connection
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    logger.info("✅ Connected to Supabase database successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase: {e}")
            return False
        
        return False
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")
    
    # =========================================================================
    # AQEA ENTRIES MANAGEMENT
    # =========================================================================
    
    async def store_aqea_entries(self, entries: List[AQEAEntry]) -> Dict[str, Any]:
        """Store AQEA entries in Supabase (batch insert)."""
        if not entries:
            return {'inserted': 0, 'errors': []}
        
        inserted = 0
        errors = []
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for entry in entries:
                        try:
                            # Convert entry to database format
                            entry_data = self._aqea_entry_to_db(entry)
                            
                            # Insert or update (upsert)
                            await conn.execute("""
                                INSERT INTO aqea_entries (
                                    address, label, description, domain, status,
                                    created_at, updated_at, created_by, lang_ui,
                                    meta, relations
                                ) VALUES (
                                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
                                )
                                ON CONFLICT (address) DO UPDATE SET
                                    label = EXCLUDED.label,
                                    description = EXCLUDED.description,
                                    updated_at = EXCLUDED.updated_at,
                                    meta = EXCLUDED.meta
                            """, *entry_data)
                            
                            inserted += 1
                            
                        except Exception as e:
                            error_msg = f"Failed to insert {entry.address}: {str(e)}"
                            errors.append(error_msg)
                            logger.warning(error_msg)
                            continue
                    
                    logger.info(f"✅ Stored {inserted} AQEA entries to Supabase")
                    
        except Exception as e:
            logger.error(f"❌ Batch insert failed: {e}")
            errors.append(f"Batch insert error: {str(e)}")
        
        return {
            'inserted': inserted,
            'errors': errors,
            'success_rate': inserted / len(entries) if entries else 0
        }
    
    def _aqea_entry_to_db(self, entry: AQEAEntry) -> tuple:
        """Convert AQEAEntry to database tuple."""
        return (
            entry.address,
            entry.label,
            entry.description,
            entry.domain,
            entry.status,
            entry.created_at,
            entry.updated_at,
            entry.created_by,
            entry.lang_ui,
            json.dumps(entry.meta) if entry.meta else '{}',
            json.dumps(entry.relations) if entry.relations else '[]'
        )
    
    async def get_aqea_entry(self, address: str) -> Optional[AQEAEntry]:
        """Get single AQEA entry by address."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM aqea_entries WHERE address = $1", 
                    address
                )
                
                if row:
                    return self._db_row_to_aqea_entry(dict(row))
                    
        except Exception as e:
            logger.error(f"Failed to get AQEA entry {address}: {e}")
        
        return None
    
    def _db_row_to_aqea_entry(self, row: Dict[str, Any]) -> AQEAEntry:
        """Convert database row to AQEAEntry."""
        return AQEAEntry(
            address=row['address'],
            label=row['label'],
            description=row['description'],
            domain=row['domain'],
            status=row['status'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            created_by=row['created_by'],
            lang_ui=row['lang_ui'],
            meta=json.loads(row['meta']) if row['meta'] else {},
            relations=json.loads(row['relations']) if row['relations'] else []
        )
    
    # =========================================================================
    # WORK UNIT MANAGEMENT
    # =========================================================================
    
    async def get_pending_work_unit(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get next pending work unit for worker."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Get and lock a pending work unit
                    row = await conn.fetchrow("""
                        UPDATE work_units 
                        SET status = 'assigned',
                            assigned_worker = $1,
                            assigned_at = NOW()
                        WHERE work_id = (
                            SELECT work_id FROM work_units 
                            WHERE status = 'pending'
                            ORDER BY created_at ASC
                            LIMIT 1
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING *
                    """, worker_id)
                    
                    if row:
                        work_unit = dict(row)
                        logger.info(f"✅ Assigned work unit {work_unit['work_id']} to {worker_id}")
                        return work_unit
                        
        except Exception as e:
            logger.error(f"Failed to get work unit for {worker_id}: {e}")
        
        return None
    
    async def update_work_progress(self, work_id: str, entries_processed: int, 
                                 processing_rate: float) -> bool:
        """Update work unit progress."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE work_units 
                    SET entries_processed = $2,
                        processing_rate = $3,
                        status = 'processing',
                        updated_at = NOW()
                    WHERE work_id = $1
                """, work_id, entries_processed, processing_rate)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update progress for {work_id}: {e}")
            return False
    
    async def complete_work_unit(self, work_id: str, success: bool, 
                               final_count: int, errors: List[str]) -> bool:
        """Mark work unit as completed."""
        status = 'completed' if success else 'failed'
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE work_units 
                    SET status = $2,
                        entries_processed = $3,
                        completed_at = NOW(),
                        errors = $4,
                        updated_at = NOW()
                    WHERE work_id = $1
                """, work_id, status, final_count, json.dumps(errors))
                
                logger.info(f"✅ Work unit {work_id} marked as {status}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to complete work unit {work_id}: {e}")
            return False
    
    # =========================================================================
    # WORKER STATUS MANAGEMENT
    # =========================================================================
    
    async def register_worker(self, worker_id: str, ip_address: str) -> bool:
        """Register worker in database."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO worker_status (
                        worker_id, ip_address, status, registered_at, last_heartbeat
                    ) VALUES ($1, $2, 'idle', NOW(), NOW())
                    ON CONFLICT (worker_id) DO UPDATE SET
                        ip_address = EXCLUDED.ip_address,
                        status = 'idle',
                        last_heartbeat = NOW()
                """, worker_id, ip_address)
                
                logger.info(f"✅ Worker {worker_id} registered from {ip_address}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register worker {worker_id}: {e}")
            return False
    
    async def update_worker_heartbeat(self, worker_id: str, status: str = 'working',
                                    current_work_id: Optional[str] = None) -> bool:
        """Update worker heartbeat and status."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE worker_status 
                    SET status = $2,
                        current_work_id = $3,
                        last_heartbeat = NOW()
                    WHERE worker_id = $1
                """, worker_id, status, current_work_id)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to update heartbeat for {worker_id}: {e}")
            return False
    
    # =========================================================================
    # ADDRESS ALLOCATION MANAGEMENT
    # =========================================================================
    
    async def allocate_address(self, category_key: str, element_id: int, 
                             worker_id: str, word: str) -> bool:
        """Allocate AQEA address to prevent collisions."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO address_allocations (
                        category_key, element_id, allocated_by, word
                    ) VALUES ($1, $2, $3, $4)
                """, category_key, element_id, worker_id, word)
                
                return True
                
        except asyncpg.UniqueViolationError:
            # Address already allocated
            logger.debug(f"Address {category_key}:{element_id:02X} already allocated")
            return False
        except Exception as e:
            logger.error(f"Failed to allocate address: {e}")
            return False
    
    async def get_allocated_addresses(self, category_key: str) -> List[int]:
        """Get list of allocated element IDs for category."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT element_id FROM address_allocations 
                    WHERE category_key = $1
                """, category_key)
                
                return [row['element_id'] for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get allocated addresses: {e}")
            return []
    
    # =========================================================================
    # STATISTICS & MONITORING
    # =========================================================================
    
    async def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get comprehensive extraction statistics."""
        try:
            async with self.pool.acquire() as conn:
                # Overall progress
                overall = await conn.fetchrow("""
                    SELECT 
                        SUM(estimated_entries) as total_estimated,
                        SUM(entries_processed) as total_processed,
                        AVG(processing_rate) as avg_rate,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed_units,
                        COUNT(*) FILTER (WHERE status = 'processing') as processing_units,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending_units,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed_units
                    FROM work_units
                """)
                
                # Worker stats
                workers = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_workers,
                        COUNT(*) FILTER (WHERE status = 'working') as active_workers,
                        COUNT(*) FILTER (WHERE status = 'idle') as idle_workers,
                        COUNT(*) FILTER (WHERE last_heartbeat > NOW() - INTERVAL '2 minutes') as online_workers
                    FROM worker_status
                """)
                
                # Recent AQEA entries count
                entries_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM aqea_entries
                """)
                
                total_estimated = overall['total_estimated'] or 0
                total_processed = overall['total_processed'] or 0
                
                return {
                    'overview': {
                        'total_estimated_entries': total_estimated,
                        'total_processed_entries': total_processed,
                        'progress_percent': (total_processed / total_estimated * 100) if total_estimated > 0 else 0,
                        'aqea_entries_stored': entries_count
                    },
                    'work_units': {
                        'completed': overall['completed_units'] or 0,
                        'processing': overall['processing_units'] or 0,
                        'pending': overall['pending_units'] or 0,
                        'failed': overall['failed_units'] or 0
                    },
                    'workers': {
                        'total': workers['total_workers'] or 0,
                        'active': workers['active_workers'] or 0,
                        'idle': workers['idle_workers'] or 0,
                        'online': workers['online_workers'] or 0
                    },
                    'performance': {
                        'average_rate': round(overall['avg_rate'] or 0, 1),
                        'estimated_completion': self._calculate_eta(
                            total_estimated - total_processed, 
                            overall['avg_rate'] or 0
                        )
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def _calculate_eta(self, remaining_entries: int, rate_per_minute: float) -> Optional[str]:
        """Calculate estimated time to completion."""
        if rate_per_minute <= 0 or remaining_entries <= 0:
            return None
        
        minutes_remaining = remaining_entries / rate_per_minute
        hours = int(minutes_remaining // 60)
        minutes = int(minutes_remaining % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    async def record_progress_snapshot(self, stats: Dict[str, Any]):
        """Record progress snapshot for monitoring."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO progress_snapshots (
                        total_estimated_entries, total_processed_entries, progress_percent,
                        current_rate_per_minute, eta_hours,
                        total_workers, active_workers, idle_workers,
                        pending_work_units, processing_work_units, 
                        completed_work_units, failed_work_units
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    stats['overview']['total_estimated_entries'],
                    stats['overview']['total_processed_entries'],
                    stats['overview']['progress_percent'],
                    stats['performance']['average_rate'],
                    None,  # eta_hours
                    stats['workers']['total'],
                    stats['workers']['active'],
                    stats['workers']['idle'],
                    stats['work_units']['pending'],
                    stats['work_units']['processing'],
                    stats['work_units']['completed'],
                    stats['work_units']['failed']
                )
                
        except Exception as e:
            logger.error(f"Failed to record progress snapshot: {e}")


# Global database instance
_db_instance = None

async def get_database(config: Dict[str, Any]) -> SupabaseDatabase:
    """Get or create database instance."""
    global _db_instance
    
    if _db_instance is None:
        _db_instance = SupabaseDatabase(config)
        await _db_instance.connect()
    
    return _db_instance

async def close_database():
    """Close database connection."""
    global _db_instance
    
    if _db_instance:
        await _db_instance.disconnect()
        _db_instance = None 
"""
Supabase Database Interface for AQEA Distributed Extractor

Zentrale Datenbank-Anbindung für alle Worker.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from supabase import create_client, Client
from ..aqea.schema import AQEAEntry

logger = logging.getLogger(__name__)


class SupabaseDatabase:
    """Zentrale Supabase-Datenbank für alle Worker."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[Client] = None
        
        # Supabase Connection Details from environment
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")
        
    async def connect(self) -> bool:
        """Establish connection to Supabase."""
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            
            # Test connection with a simple query
            test_result = self.client.table('aqea_entries').select('count').execute()
            
            logger.info("✅ Connected to Supabase database successfully")
            return True
                    
        except Exception as e:
            logger.error(f"❌ Failed to connect to Supabase: {e}")
            return False
    
    async def disconnect(self):
        """Close database connection."""
        # Supabase client doesn't need explicit disconnection
        self.client = None
        logger.info("Database connection closed")
    
    # =========================================================================
    # AQEA ENTRIES MANAGEMENT
    # =========================================================================
    
    async def store_aqea_entries(self, entries: List[AQEAEntry]) -> Dict[str, Any]:
        """Store AQEA entries in Supabase (batch insert)."""
        if not entries or not self.client:
            return {'inserted': 0, 'errors': []}
        
        inserted = 0
        errors = []
        
        try:
            # Convert entries to database format
            entries_data = []
            for entry in entries:
                try:
                    entry_data = self._aqea_entry_to_db_dict(entry)
                    entries_data.append(entry_data)
                except Exception as e:
                    error_msg = f"Failed to convert entry {entry.address}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
            
            if entries_data:
                # Batch insert with upsert
                result = self.client.table('aqea_entries').upsert(
                    entries_data,
                    on_conflict='address'
                ).execute()
                
                inserted = len(result.data) if result.data else len(entries_data)
                logger.info(f"✅ Stored {inserted} AQEA entries to Supabase")
                    
        except Exception as e:
            logger.error(f"❌ Batch insert failed: {e}")
            errors.append(f"Batch insert error: {str(e)}")
        
        return {
            'inserted': inserted,
            'errors': errors,
            'success_rate': inserted / len(entries) if entries else 0
        }
    
    def _aqea_entry_to_db_dict(self, entry: AQEAEntry) -> dict:
        """Convert AQEAEntry to database dictionary."""
        return {
            'address': entry.address,
            'label': entry.label,
            'description': entry.description,
            'domain': entry.domain,
            'status': entry.status,
            'created_at': entry.created_at.isoformat() if isinstance(entry.created_at, datetime) else entry.created_at,
            'updated_at': entry.updated_at.isoformat() if isinstance(entry.updated_at, datetime) else entry.updated_at,
            'created_by': entry.created_by,
            'lang_ui': entry.lang_ui,
            'meta': entry.meta if entry.meta else {},
            'relations': entry.relations if entry.relations else []
        }
    
    async def get_aqea_entry(self, address: str) -> Optional[AQEAEntry]:
        """Get single AQEA entry by address."""
        if not self.client:
            return None
            
        try:
            result = self.client.table('aqea_entries').select('*').eq('address', address).execute()
            
            if result.data and len(result.data) > 0:
                return self._db_dict_to_aqea_entry(result.data[0])
                    
        except Exception as e:
            logger.error(f"Failed to get AQEA entry {address}: {e}")
        
        return None
    
    def _db_dict_to_aqea_entry(self, row: Dict[str, Any]) -> AQEAEntry:
        """Convert database dictionary to AQEAEntry."""
        return AQEAEntry(
            address=row['address'],
            label=row['label'],
            description=row['description'],
            domain=row['domain'],
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if isinstance(row['created_at'], str) else row['created_at'],
            updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if isinstance(row['updated_at'], str) else row['updated_at'],
            created_by=row['created_by'],
            lang_ui=row['lang_ui'],
            meta=row['meta'] if row['meta'] else {},
            relations=row['relations'] if row['relations'] else []
        )
    
    # =========================================================================
    # WORK UNIT MANAGEMENT (simplified for HTTP-only coordination)
    # =========================================================================
    
    async def get_pending_work_unit(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get next pending work unit for worker."""
        if not self.client:
            return None
            
        try:
            # Get and update a pending work unit atomically
            result = self.client.table('work_units').select('*').eq('status', 'pending').limit(1).execute()
            
            if result.data and len(result.data) > 0:
                work_unit = result.data[0]
                
                # Update status to assigned
                self.client.table('work_units').update({
                    'status': 'assigned',
                    'assigned_worker': worker_id,
                    'assigned_at': datetime.now().isoformat()
                }).eq('work_id', work_unit['work_id']).execute()
                
                logger.info(f"✅ Assigned work unit {work_unit['work_id']} to {worker_id}")
                return work_unit
                        
        except Exception as e:
            logger.error(f"Failed to get work unit for {worker_id}: {e}")
        
        return None
    
    async def update_work_progress(self, work_id: str, entries_processed: int, 
                                 processing_rate: float) -> bool:
        """Update work unit progress."""
        if not self.client:
            return False
            
        try:
            self.client.table('work_units').update({
                'entries_processed': entries_processed,
                'processing_rate': processing_rate,
                'status': 'processing',
                'updated_at': datetime.now().isoformat()
            }).eq('work_id', work_id).execute()
            
            return True
                
        except Exception as e:
            logger.error(f"Failed to update progress for {work_id}: {e}")
            return False
    
    async def complete_work_unit(self, work_id: str, success: bool, 
                               final_count: int, errors: List[str]) -> bool:
        """Mark work unit as completed."""
        if not self.client:
            return False
            
        status = 'completed' if success else 'failed'
        
        try:
            self.client.table('work_units').update({
                'status': status,
                'entries_processed': final_count,
                'completed_at': datetime.now().isoformat(),
                'errors': errors,
                'updated_at': datetime.now().isoformat()
            }).eq('work_id', work_id).execute()
            
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
        if not self.client:
            return False
            
        try:
            self.client.table('worker_status').upsert({
                'worker_id': worker_id,
                'ip_address': ip_address,
                'status': 'idle',
                'registered_at': datetime.now().isoformat(),
                'last_heartbeat': datetime.now().isoformat()
            }, on_conflict='worker_id').execute()
            
            logger.info(f"✅ Worker {worker_id} registered from {ip_address}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to register worker {worker_id}: {e}")
            return False
    
    async def update_worker_heartbeat(self, worker_id: str, status: str = 'working',
                                    current_work_id: Optional[str] = None) -> bool:
        """Update worker heartbeat and status."""
        if not self.client:
            return False
            
        try:
            self.client.table('worker_status').update({
                'status': status,
                'current_work_id': current_work_id,
                'last_heartbeat': datetime.now().isoformat()
            }).eq('worker_id', worker_id).execute()
            
            return True
                
        except Exception as e:
            logger.error(f"Failed to update heartbeat for {worker_id}: {e}")
            return False
    
    # =========================================================================
    # STATISTICS & MONITORING (simplified)
    # =========================================================================
    
    async def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get basic extraction statistics."""
        if not self.client:
            return {}
            
        try:
            # Get AQEA entries count
            entries_result = self.client.table('aqea_entries').select('*', count='exact').execute()
            entries_count = entries_result.count if hasattr(entries_result, 'count') else 0
            
            # Get work units statistics
            work_result = self.client.table('work_units').select('*').execute()
            work_units = work_result.data if work_result.data else []
            
            completed = len([wu for wu in work_units if wu['status'] == 'completed'])
            processing = len([wu for wu in work_units if wu['status'] == 'processing'])
            pending = len([wu for wu in work_units if wu['status'] == 'pending'])
            failed = len([wu for wu in work_units if wu['status'] == 'failed'])
            
            total_processed = sum(wu.get('entries_processed', 0) for wu in work_units)
            
            return {
                'overview': {
                    'total_estimated_entries': sum(wu.get('estimated_entries', 0) for wu in work_units),
                    'total_processed_entries': total_processed,
                    'progress_percent': 0,  # Calculate if needed
                    'aqea_entries_stored': entries_count
                },
                'work_units': {
                    'completed': completed,
                    'processing': processing,
                    'pending': pending,
                    'failed': failed
                },
                'workers': {
                    'total': 0,  # Implement if needed
                    'active': 0,
                    'idle': 0,
                    'online': 0
                },
                'performance': {
                    'average_rate': 0,  # Calculate if needed
                    'estimated_completion': None
                }
            }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


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
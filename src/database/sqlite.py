"""
SQLite Database Interface for AQEA Distributed Extractor

Zentrale lokale Datenbank-Anbindung für den Master Coordinator.
"""

import logging
import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..aqea.schema import AQEAEntry

logger = logging.getLogger(__name__)


class SQLiteDatabase:
    """Zentrale SQLite-Datenbank für den Master Coordinator."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get('sqlite_path', 'data/aqea_extraction.db')
        self.connection = None
        
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    async def connect(self) -> bool:
        """Verbindung zur SQLite-Datenbank herstellen."""
        try:
            # SQLite Connection erstellen
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            
            # Tabellen erstellen, falls sie nicht existieren
            await self._create_tables()
            
            logger.info(f"✅ Verbunden mit SQLite-Datenbank: {self.db_path}")
            return True
                    
        except Exception as e:
            logger.error(f"❌ Verbindung zur SQLite-Datenbank fehlgeschlagen: {e}")
            return False
    
    async def disconnect(self):
        """Datenbankverbindung schließen."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Datenbankverbindung geschlossen")
    
    async def _create_tables(self):
        """Erstelle die benötigten Tabellen, falls sie nicht existieren."""
        cursor = self.connection.cursor()
        
        # AQEA Entries Tabelle
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS aqea_entries (
            address TEXT PRIMARY KEY,
            label TEXT,
            description TEXT,
            domain TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT,
            created_by TEXT,
            lang_ui TEXT,
            meta TEXT,
            relations TEXT
        )
        ''')
        
        # Work Units Tabelle
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_units (
            work_id TEXT PRIMARY KEY,
            language TEXT,
            source TEXT,
            start_range TEXT,
            end_range TEXT,
            estimated_entries INTEGER,
            status TEXT,
            assigned_worker TEXT,
            assigned_at TEXT,
            completed_at TEXT,
            updated_at TEXT,
            entries_processed INTEGER,
            processing_rate REAL,
            errors TEXT
        )
        ''')
        
        # Worker Status Tabelle
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS worker_status (
            worker_id TEXT PRIMARY KEY,
            ip_address TEXT,
            status TEXT,
            current_work_id TEXT,
            last_heartbeat TEXT,
            total_processed INTEGER,
            average_rate REAL,
            registered_at TEXT
        )
        ''')
        
        # Address Allocations Tabelle
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS address_allocations (
            aa_byte INTEGER,
            qq_byte INTEGER,
            ee_byte INTEGER,
            a2_byte INTEGER,
            reserved_by TEXT,
            reserved_at TEXT,
            language TEXT,
            domain TEXT,
            PRIMARY KEY (aa_byte, qq_byte, ee_byte, a2_byte)
        )
        ''')
        
        # Add missing columns to existing tables (migration)
        try:
            cursor.execute("ALTER TABLE work_units ADD COLUMN updated_at TEXT")
            logger.info("✅ Added missing updated_at column to work_units table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                logger.debug("updated_at column already exists in work_units table")
            else:
                logger.warning(f"Could not add updated_at column: {e}")
        
        self.connection.commit()
    
    # =========================================================================
    # AQEA ENTRIES MANAGEMENT
    # =========================================================================
    
    async def store_aqea_entries(self, entries: List[AQEAEntry]) -> Dict[str, Any]:
        """Store AQEA entries in SQLite (batch insert)."""
        if not entries or not self.connection:
            return {'inserted': 0, 'errors': []}
        
        inserted = 0
        errors = []
        
        try:
            # Konvertiere Einträge in Datenbankformat
            entries_data = []
            unique_addresses = set()  # Vermeide Duplikate im selben Batch
            
            for entry in entries:
                try:
                    # Überspringe doppelte Adressen im selben Batch
                    if entry.address in unique_addresses:
                        logger.debug(f"Überspringe doppelte Adresse im Batch: {entry.address}")
                        continue
                        
                    entry_data = self._aqea_entry_to_db_dict(entry)
                    entries_data.append(entry_data)
                    unique_addresses.add(entry.address)
                except Exception as e:
                    error_msg = f"Fehler beim Konvertieren von Eintrag {entry.address}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
            
            if entries_data:
                cursor = self.connection.cursor()
                
                # Verarbeite in kleineren Batches, um Fehler zu vermeiden
                batch_size = 10
                for i in range(0, len(entries_data), batch_size):
                    batch = entries_data[i:i+batch_size]
                    try:
                        # Batch Insert mit UPSERT-Logik
                        for entry in batch:
                            cursor.execute('''
                            INSERT INTO aqea_entries (
                                address, label, description, domain, status, 
                                created_at, updated_at, created_by, lang_ui, meta, relations
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(address) DO UPDATE SET
                                label = excluded.label,
                                description = excluded.description,
                                domain = excluded.domain,
                                status = excluded.status,
                                updated_at = excluded.updated_at,
                                lang_ui = excluded.lang_ui,
                                meta = excluded.meta,
                                relations = excluded.relations
                            ''', (
                                entry['address'],
                                entry['label'],
                                entry['description'],
                                entry['domain'],
                                entry['status'],
                                entry['created_at'],
                                entry['updated_at'],
                                entry['created_by'],
                                entry['lang_ui'],
                                entry['meta'],
                                entry['relations']
                            ))
                        
                        self.connection.commit()
                        inserted += len(batch)
                        logger.info(f"✅ Batch von {len(batch)} AQEA-Einträgen in SQLite gespeichert")
                    except Exception as e:
                        batch_error = f"Batch-Insert-Fehler (Batch {i//batch_size+1}): {str(e)}"
                        errors.append(batch_error)
                        logger.error(f"❌ {batch_error}")
                        self.connection.rollback()  # Rollback bei Fehler
                        continue
                    
        except Exception as e:
            logger.error(f"❌ Batch-Insert-Prozess fehlgeschlagen: {e}")
            errors.append(f"Batch-Insert-Prozess-Fehler: {str(e)}")
        
        return {
            'inserted': inserted,
            'errors': errors,
            'success_rate': inserted / len(entries) if entries else 0
        }
    
    def _aqea_entry_to_db_dict(self, entry: AQEAEntry) -> dict:
        """Konvertiere AQEAEntry in Datenbank-Dictionary."""
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
            'meta': json.dumps(entry.meta) if entry.meta else "{}",
            'relations': json.dumps(entry.relations) if entry.relations else "[]"
        }
    
    async def get_aqea_entry(self, address: str) -> Optional[AQEAEntry]:
        """Get single AQEA entry by address."""
        if not self.connection:
            return None
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM aqea_entries WHERE address = ?", (address,))
            row = cursor.fetchone()
            
            if row:
                return self._db_dict_to_aqea_entry(dict(row))
                    
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des AQEA-Eintrags {address}: {e}")
        
        return None
    
    def _db_dict_to_aqea_entry(self, row: Dict[str, Any]) -> AQEAEntry:
        """Konvertiere Datenbank-Dictionary in AQEAEntry."""
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
            meta=json.loads(row['meta']) if row['meta'] else {},
            relations=json.loads(row['relations']) if row['relations'] else []
        )
    
    # =========================================================================
    # ADDRESS ALLOCATION MANAGEMENT
    # =========================================================================
    
    async def get_allocated_addresses(self, category_key: Optional[str] = None) -> Dict[str, List[int]]:
        """Get allocated addresses for a category or all categories."""
        if not self.connection:
            return {}
            
        try:
            cursor = self.connection.cursor()
            
            # Abfrage bauen
            if category_key:
                # Zerlege den category_key (z.B. "20:01:01") in einzelne Bytes
                parts = category_key.split(":")
                if len(parts) == 3:
                    aa = int(parts[0], 16)
                    qq = int(parts[1], 16)
                    ee = int(parts[2], 16)
                    
                    cursor.execute("""
                        SELECT aa_byte, qq_byte, ee_byte, a2_byte 
                        FROM address_allocations 
                        WHERE aa_byte = ? AND qq_byte = ? AND ee_byte = ?
                    """, (aa, qq, ee))
            else:
                cursor.execute("SELECT aa_byte, qq_byte, ee_byte, a2_byte FROM address_allocations")
                
            rows = cursor.fetchall()
            
            # Gruppiere nach Kategorie
            allocated_addresses = {}
            for row in rows:
                aa = row['aa_byte']
                qq = row['qq_byte']
                ee = row['ee_byte']
                a2 = row['a2_byte']
                
                # Erstelle category_key im Format "AA:QQ:EE"
                cat_key = f"{aa:02X}:{qq:02X}:{ee:02X}"
                
                if cat_key not in allocated_addresses:
                    allocated_addresses[cat_key] = []
                
                allocated_addresses[cat_key].append(a2)
            
            return allocated_addresses
                
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der zugewiesenen Adressen: {e}")
            return {}
    
    async def allocate_address(self, category_key: str, element_id: int, 
                             worker_id: str, word: str) -> Optional[int]:
        """Allocate an address in the database."""
        if not self.connection:
            return None
            
        try:
            cursor = self.connection.cursor()
            
            # Zerlege den category_key (z.B. "20:01:01") in einzelne Bytes
            parts = category_key.split(":")
            if len(parts) != 3:
                raise ValueError(f"Ungültiges category_key-Format: {category_key}")
                
            aa = int(parts[0], 16)
            qq = int(parts[1], 16)
            ee = int(parts[2], 16)
            
            # Prüfe, ob das Wort bereits eine Zuweisung hat
            cursor.execute("""
                SELECT a2_byte FROM address_allocations
                WHERE aa_byte = ? AND qq_byte = ? AND ee_byte = ?
                LIMIT 1
            """, (aa, qq, ee))
            
            row = cursor.fetchone()
            if row:
                # Wort hat bereits eine Zuweisung, gib sie zurück
                return row['a2_byte']
            
            # Versuche die angeforderte element_id zu allokieren
            try:
                cursor.execute("""
                    INSERT INTO address_allocations (aa_byte, qq_byte, ee_byte, a2_byte, reserved_by, reserved_at, language, domain)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    aa, qq, ee, element_id, worker_id, datetime.now().isoformat(), 
                    'de', f"0x{aa:02X}"  # Default zu Deutsch, Domain-Byte als Hex-String
                ))
                self.connection.commit()
                return element_id
            except sqlite3.IntegrityError:
                # Element ID vermutlich bereits vergeben, Fallback
                pass
            
            # Fallback: Finde nächste verfügbare ID
            for attempt_id in range(1, 254):  # Vermeide 0x00, 0xFE, 0xFF
                if attempt_id == element_id:
                    continue  # Diese haben wir schon versucht
                    
                try:
                    cursor.execute("""
                        INSERT INTO address_allocations (aa_byte, qq_byte, ee_byte, a2_byte, reserved_by, reserved_at, language, domain)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        aa, qq, ee, attempt_id, worker_id, datetime.now().isoformat(), 
                        'de', f"0x{aa:02X}"
                    ))
                    self.connection.commit()
                    return attempt_id
                except sqlite3.IntegrityError:
                    # Diese ID ist auch vergeben, versuche die nächste
                    continue
            
            logger.warning(f"Adresszuweisung in Kategorie {category_key} fehlgeschlagen: alle IDs belegt")
            return None
                
        except Exception as e:
            logger.error(f"Adresszuweisung fehlgeschlagen: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    # =========================================================================
    # WORK UNIT MANAGEMENT
    # =========================================================================
    
    async def get_pending_work_unit(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get next pending work unit for worker."""
        if not self.connection:
            return None
            
        try:
            cursor = self.connection.cursor()
            
            # Finde eine ausstehende Arbeitseinheit
            cursor.execute("SELECT * FROM work_units WHERE status = 'pending' LIMIT 1")
            row = cursor.fetchone()
            
            if row:
                work_unit = dict(row)
                
                # Status auf "assigned" setzen
                cursor.execute("""
                    UPDATE work_units 
                    SET status = 'assigned', 
                        assigned_worker = ?, 
                        assigned_at = ?
                    WHERE work_id = ?
                """, (
                    worker_id, 
                    datetime.now().isoformat(),
                    work_unit['work_id']
                ))
                self.connection.commit()
                
                logger.info(f"✅ Arbeitseinheit {work_unit['work_id']} wurde {worker_id} zugewiesen")
                return work_unit
                        
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Arbeitseinheit für {worker_id}: {e}")
            if self.connection:
                self.connection.rollback()
        
        return None
    
    async def update_work_progress(self, work_id: str, entries_processed: int, 
                                 processing_rate: float) -> bool:
        """Update work unit progress."""
        if not self.connection:
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE work_units 
                SET entries_processed = ?,
                    processing_rate = ?,
                    status = 'processing',
                    updated_at = ?
                WHERE work_id = ?
            """, (
                entries_processed,
                processing_rate,
                datetime.now().isoformat(),
                work_id
            ))
            self.connection.commit()
            
            return True
                
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Fortschritts für {work_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    async def complete_work_unit(self, work_id: str, success: bool, 
                               final_count: int, errors: List[str]) -> bool:
        """Mark work unit as completed."""
        if not self.connection:
            return False
            
        status = 'completed' if success else 'failed'
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE work_units 
                SET status = ?,
                    entries_processed = ?,
                    completed_at = ?,
                    errors = ?
                WHERE work_id = ?
            """, (
                status,
                final_count,
                datetime.now().isoformat(),
                json.dumps(errors),
                work_id
            ))
            self.connection.commit()
            
            logger.info(f"✅ Arbeitseinheit {work_id} als {status} markiert")
            return True
                
        except Exception as e:
            logger.error(f"Fehler beim Abschließen der Arbeitseinheit {work_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    # =========================================================================
    # WORKER STATUS MANAGEMENT
    # =========================================================================
    
    async def register_worker(self, worker_id: str, ip_address: str) -> bool:
        """Register worker in database."""
        if not self.connection:
            return False
            
        try:
            cursor = self.connection.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO worker_status (
                    worker_id, ip_address, status, last_heartbeat, registered_at, 
                    total_processed, average_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    ip_address = excluded.ip_address,
                    status = excluded.status,
                    last_heartbeat = excluded.last_heartbeat
            """, (
                worker_id,
                ip_address,
                'idle',
                now,
                now,
                0,
                0.0
            ))
            self.connection.commit()
            
            logger.info(f"✅ Worker {worker_id} registriert von {ip_address}")
            return True
                
        except Exception as e:
            logger.error(f"Fehler beim Registrieren des Workers {worker_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    async def update_worker_heartbeat(self, worker_id: str, status: str = 'working',
                                    current_work_id: Optional[str] = None) -> bool:
        """Update worker heartbeat and status."""
        if not self.connection:
            return False
            
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE worker_status 
                SET status = ?,
                    current_work_id = ?,
                    last_heartbeat = ?
                WHERE worker_id = ?
            """, (
                status,
                current_work_id,
                datetime.now().isoformat(),
                worker_id
            ))
            
            # Prüfe, ob ein Update stattgefunden hat
            if cursor.rowcount == 0:
                # Worker existiert möglicherweise nicht in der Datenbank, neu registrieren
                logger.warning(f"Worker {worker_id} Heartbeat fehlgeschlagen, versuche Neuregistrierung")
                cursor.execute("""
                    INSERT INTO worker_status (
                        worker_id, status, current_work_id, last_heartbeat, registered_at, 
                        total_processed, average_rate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    worker_id,
                    status,
                    current_work_id,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    0,
                    0.0
                ))
            
            self.connection.commit()
            return True
                
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Heartbeats für {worker_id}: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    # =========================================================================
    # STATISTICS & MONITORING
    # =========================================================================
    
    async def get_extraction_statistics(self) -> Dict[str, Any]:
        """Get basic extraction statistics."""
        if not self.connection:
            return {}
            
        try:
            cursor = self.connection.cursor()
            
            # Anzahl der AQEA-Einträge
            cursor.execute("SELECT COUNT(*) as count FROM aqea_entries")
            entries_count = cursor.fetchone()['count']
            
            # Work Units Statistiken
            cursor.execute("SELECT * FROM work_units")
            work_units = [dict(row) for row in cursor.fetchall()]
            
            completed = len([wu for wu in work_units if wu['status'] == 'completed'])
            processing = len([wu for wu in work_units if wu['status'] == 'processing'])
            pending = len([wu for wu in work_units if wu['status'] == 'pending'])
            failed = len([wu for wu in work_units if wu['status'] == 'failed'])
            
            total_processed = sum(wu.get('entries_processed', 0) for wu in work_units)
            
            # Worker Statistiken
            cursor.execute("SELECT * FROM worker_status")
            workers = [dict(row) for row in cursor.fetchall()]
            
            active_workers = len([w for w in workers if w['status'] == 'working'])
            idle_workers = len([w for w in workers if w['status'] == 'idle'])
            
            return {
                'overview': {
                    'total_estimated_entries': sum(wu.get('estimated_entries', 0) for wu in work_units),
                    'total_processed_entries': total_processed,
                    'progress_percent': 0,  # Berechnen, falls nötig
                    'aqea_entries_stored': entries_count
                },
                'work_units': {
                    'completed': completed,
                    'processing': processing,
                    'pending': pending,
                    'failed': failed
                },
                'workers': {
                    'total': len(workers),
                    'active': active_workers,
                    'idle': idle_workers,
                    'online': active_workers + idle_workers
                },
                'performance': {
                    'average_rate': 0,  # Berechnen, falls nötig
                    'estimated_completion': None
                }
            }
                
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Statistiken: {e}")
            return {}


# Globale Datenbankinstanz
_db_instance = None

async def get_database(config: Dict[str, Any]) -> SQLiteDatabase:
    """Datenbankinstanz abrufen oder erstellen."""
    global _db_instance
    
    if _db_instance is None:
        _db_instance = SQLiteDatabase(config)
        success = await _db_instance.connect()
        if not success:
            logger.error("❌ SQLite-Datenbank-Verbindung fehlgeschlagen")
            _db_instance = None
            return None
    
    return _db_instance

async def close_database():
    """Datenbankverbindung schließen."""
    global _db_instance
    
    if _db_instance:
        await _db_instance.disconnect()
        _db_instance = None 
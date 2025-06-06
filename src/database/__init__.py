"""
Database initialization module
"""

from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

# Global database instance
_database = None

async def get_database(config: Dict[str, Any]):
    """Get configured database instance based on config."""
    global _database
    
    if _database is not None:
        return _database
    
    db_type = config.get('database', {}).get('type', 'sqlite')
    
    if db_type == 'supabase':
        try:
            from .supabase import get_database as get_supabase_db
            logger.info("Initialisiere Supabase-Datenbank...")
            _database = await get_supabase_db(config)
            if _database:
                logger.info("✅ Supabase-Datenbank erfolgreich initialisiert")
                return _database
        except Exception as e:
            logger.warning(f"⚠️ Supabase-Datenbank konnte nicht initialisiert werden: {e}")
            logger.info("Fallback auf SQLite-Datenbank...")
    
    # Verwende SQLite als Standard oder als Fallback
    try:
        from .sqlite import get_database as get_sqlite_db
        logger.info("Initialisiere lokale SQLite-Datenbank...")
        _database = await get_sqlite_db(config)
        if _database:
            logger.info("✅ SQLite-Datenbank erfolgreich initialisiert")
            return _database
    except Exception as e:
        logger.error(f"❌ SQLite-Datenbank konnte nicht initialisiert werden: {e}")
    
    logger.warning("⚠️ Keine Datenbank verfügbar, System läuft im eingeschränkten Modus")
    return None

async def close_database():
    """Close database connection."""
    global _database
    
    if _database is not None:
        if hasattr(_database, 'disconnect'):
            await _database.disconnect()
        elif hasattr(_database, 'client') and hasattr(_database.client, 'close'):
            await _database.client.close()
        _database = None
        logger.info("Datenbankverbindung geschlossen") 
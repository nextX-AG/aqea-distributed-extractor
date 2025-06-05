#!/usr/bin/env python3
"""
Create Database Tables Script for AQEA Distributed Extractor

Dieses Skript erstellt die erforderlichen Tabellen in der Supabase-Datenbank.
"""

import asyncio
import os
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv
import asyncpg

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lade Umgebungsvariablen aus .env Datei
load_dotenv()

# SQL zur Erstellung der Tabellen
CREATE_TABLES_SQL = """
-- AQEA Entries Tabelle
CREATE TABLE IF NOT EXISTS aqea_entries (
    id SERIAL PRIMARY KEY,
    address VARCHAR(50) NOT NULL UNIQUE,
    label TEXT NOT NULL,
    description TEXT,
    domain VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(50),
    lang_ui VARCHAR(10) DEFAULT 'de',
    meta JSONB DEFAULT '{}',
    relations JSONB DEFAULT '[]'
);

-- Work Units Tabelle
CREATE TABLE IF NOT EXISTS work_units (
    id SERIAL PRIMARY KEY,
    unit_id VARCHAR(50) NOT NULL UNIQUE,
    language VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL,
    range_start VARCHAR(20),
    range_end VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    assigned_to VARCHAR(50),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    entries_processed INTEGER DEFAULT 0,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Worker Status Tabelle
CREATE TABLE IF NOT EXISTS worker_status (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(50) NOT NULL UNIQUE,
    ip_address VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    current_work_unit VARCHAR(50),
    total_entries_processed INTEGER DEFAULT 0,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Address Ranges Tabelle
CREATE TABLE IF NOT EXISTS address_ranges (
    id SERIAL PRIMARY KEY,
    language VARCHAR(10) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    a1_byte INTEGER NOT NULL,
    a2_byte INTEGER,
    a3_byte INTEGER,
    a4_byte INTEGER,
    reserved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(language, domain, a1_byte, a2_byte, a3_byte, a4_byte)
);

-- Indizes für Performance
CREATE INDEX IF NOT EXISTS idx_aqea_entries_address ON aqea_entries(address);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_domain ON aqea_entries(domain);
CREATE INDEX IF NOT EXISTS idx_work_units_status ON work_units(status);
CREATE INDEX IF NOT EXISTS idx_worker_status_worker_id ON worker_status(worker_id);
CREATE INDEX IF NOT EXISTS idx_address_ranges_language ON address_ranges(language);
"""

async def create_tables():
    """Create tables in Supabase database."""
    print("🔧 Creating tables in Supabase database...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL nicht gefunden!")
        return False
    
    try:
        # Verbindung zur Datenbank herstellen
        conn = await asyncpg.connect(database_url)
        
        # Ausführen der SQL-Befehle
        await conn.execute(CREATE_TABLES_SQL)
        
        # Verbindung schließen
        await conn.close()
        
        print("✅ Tabellen erfolgreich erstellt oder bereits vorhanden!")
        return True
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der Tabellen: {e}")
        return False

if __name__ == "__main__":
    print("=== AQEA Database Tables Setup ===\n")
    
    # Tabellen erstellen
    success = asyncio.run(create_tables())
    
    if success:
        print("\n✅ Datenbankeinrichtung abgeschlossen!")
        sys.exit(0)
    else:
        print("\n❌ Datenbankeinrichtung fehlgeschlagen!")
        sys.exit(1) 
-- AQEA Distributed Extractor - Database Schema
-- Führen Sie dieses SQL im Supabase SQL Editor aus

-- 1. AQEA Entries - Haupttabelle für alle Spracheinträge
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

-- 2. Work Units - Arbeitseinheiten für die Worker
CREATE TABLE IF NOT EXISTS work_units (
    id SERIAL PRIMARY KEY,
    work_id VARCHAR(50) NOT NULL UNIQUE,
    language VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL,
    range_start VARCHAR(20),
    range_end VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',
    assigned_worker VARCHAR(50),
    assigned_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    entries_processed INTEGER DEFAULT 0,
    estimated_entries INTEGER DEFAULT 0,
    processing_rate REAL DEFAULT 0.0,
    success BOOLEAN,
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Worker Status - Live-Tracking aller Worker
CREATE TABLE IF NOT EXISTS worker_status (
    id SERIAL PRIMARY KEY,
    worker_id VARCHAR(50) NOT NULL UNIQUE,
    ip_address VARCHAR(50),
    status VARCHAR(20) DEFAULT 'idle',
    current_work_id VARCHAR(50),
    total_processed INTEGER DEFAULT 0,
    processing_rate REAL DEFAULT 0.0,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    errors_count INTEGER DEFAULT 0
);

-- 4. Address Allocations - AQEA-Adressvergabe
CREATE TABLE IF NOT EXISTS address_allocations (
    id SERIAL PRIMARY KEY,
    language VARCHAR(10) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    aa_byte INTEGER NOT NULL,
    qq_byte INTEGER NOT NULL,
    ee_byte INTEGER NOT NULL,
    a2_byte INTEGER NOT NULL,
    reserved_by VARCHAR(50),
    reserved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(language, domain, aa_byte, qq_byte, ee_byte, a2_byte)
);

-- 5. Progress Snapshots - Für Dashboard und Monitoring
CREATE TABLE IF NOT EXISTS progress_snapshots (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_estimated_entries INTEGER,
    total_processed_entries INTEGER,
    progress_percent REAL,
    current_rate_per_minute REAL,
    eta_hours REAL,
    total_workers INTEGER,
    active_workers INTEGER,
    idle_workers INTEGER,
    pending_work_units INTEGER,
    processing_work_units INTEGER,
    completed_work_units INTEGER,
    failed_work_units INTEGER
);

-- Indizes für Performance
CREATE INDEX IF NOT EXISTS idx_aqea_entries_address ON aqea_entries(address);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_domain ON aqea_entries(domain);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_lang_ui ON aqea_entries(lang_ui);
CREATE INDEX IF NOT EXISTS idx_work_units_status ON work_units(status);
CREATE INDEX IF NOT EXISTS idx_work_units_worker ON work_units(assigned_worker);
CREATE INDEX IF NOT EXISTS idx_worker_status_worker_id ON worker_status(worker_id);
CREATE INDEX IF NOT EXISTS idx_worker_status_heartbeat ON worker_status(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_address_allocations_language ON address_allocations(language);

-- Row Level Security (RLS) aktivieren
ALTER TABLE aqea_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_units ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE address_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE progress_snapshots ENABLE ROW LEVEL SECURITY;

-- Policies für öffentlichen Zugriff (für AQEA-System)
CREATE POLICY "Enable all operations for service role" ON aqea_entries FOR ALL USING (true);
CREATE POLICY "Enable all operations for service role" ON work_units FOR ALL USING (true);
CREATE POLICY "Enable all operations for service role" ON worker_status FOR ALL USING (true);
CREATE POLICY "Enable all operations for service role" ON address_allocations FOR ALL USING (true);
CREATE POLICY "Enable all operations for service role" ON progress_snapshots FOR ALL USING (true);

-- Erfolgsmeldung
DO $$
BEGIN
    RAISE NOTICE '🎉 AQEA Database Schema erfolgreich erstellt!';
    RAISE NOTICE '   - aqea_entries: Haupttabelle für Spracheinträge';
    RAISE NOTICE '   - work_units: Arbeitseinheiten für Worker';
    RAISE NOTICE '   - worker_status: Live-Worker-Tracking';
    RAISE NOTICE '   - address_allocations: AQEA-Adressvergabe';
    RAISE NOTICE '   - progress_snapshots: Dashboard-Monitoring';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Ihr AQEA Distributed Extractor ist bereit!';
END $$; 
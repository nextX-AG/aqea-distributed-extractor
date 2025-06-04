-- AQEA Distributed Extractor - Supabase Database Schema
-- Creates tables for distributed language data extraction

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- CORE AQEA TABLES
-- =============================================================================

-- AQEA Entries - Haupttabelle für alle AQEA-Einträge
CREATE TABLE IF NOT EXISTS aqea_entries (
    -- AQEA Core Fields
    address VARCHAR(16) PRIMARY KEY,  -- 0x20:01:01:01
    label VARCHAR(60) NOT NULL,       -- "Wasser"
    description TEXT NOT NULL,        -- "German noun 'Wasser'. H₂O, drinking liquid"
    domain VARCHAR(4) NOT NULL,       -- "0x20"
    
    -- Lifecycle & Management
    status VARCHAR(20) DEFAULT 'active',  -- draft|active|deprecated|pending_review
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'aqea-distributed-extractor',
    
    -- Optional Fields
    lang_ui VARCHAR(10),              -- "de"
    reviewed_by VARCHAR(100),
    dictionary_id VARCHAR(50),
    version_hash VARCHAR(64),
    signature VARCHAR(128),
    element_hash VARCHAR(64),
    vector FLOAT[],                   -- Embeddings
    embedding_source VARCHAR(50),
    aqea_path VARCHAR(200),
    license VARCHAR(50),
    
    -- Language-specific metadata (JSON)
    meta JSONB DEFAULT '{}',
    
    -- Relations to other entries
    relations JSONB DEFAULT '[]',
    
    -- Indexing & Search
    search_vector TSVECTOR,
    
    CONSTRAINT valid_status CHECK (status IN ('draft', 'active', 'deprecated', 'pending_review')),
    CONSTRAINT valid_address_format CHECK (address ~ '^0x[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}$')
);

-- =============================================================================
-- COORDINATION & WORK MANAGEMENT
-- =============================================================================

-- Work Units - Verteilte Arbeitseinheiten
CREATE TABLE IF NOT EXISTS work_units (
    work_id VARCHAR(50) PRIMARY KEY,
    language VARCHAR(10) NOT NULL,
    source VARCHAR(20) NOT NULL,      -- wiktionary, panlex, etc.
    range_start VARCHAR(10) NOT NULL, -- "A"
    range_end VARCHAR(10) NOT NULL,   -- "E"
    estimated_entries INTEGER DEFAULT 0,
    
    -- Status & Assignment
    status VARCHAR(20) DEFAULT 'pending',  -- pending|assigned|processing|completed|failed
    assigned_worker VARCHAR(50),
    assigned_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Progress Tracking
    entries_processed INTEGER DEFAULT 0,
    processing_rate REAL DEFAULT 0.0,  -- entries per minute
    progress_percent REAL DEFAULT 0.0,
    
    -- Error Handling
    errors JSONB DEFAULT '[]',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_work_status CHECK (status IN ('pending', 'assigned', 'processing', 'completed', 'failed'))
);

-- Worker Status - Live-Tracking der Worker
CREATE TABLE IF NOT EXISTS worker_status (
    worker_id VARCHAR(50) PRIMARY KEY,
    ip_address INET,
    
    -- Status
    status VARCHAR(20) DEFAULT 'idle',  -- idle|working|error|offline
    current_work_id VARCHAR(50) REFERENCES work_units(work_id),
    
    -- Performance Metrics
    total_processed INTEGER DEFAULT 0,
    average_rate REAL DEFAULT 0.0,
    uptime_seconds INTEGER DEFAULT 0,
    
    -- Timestamps
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_work_completed TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    worker_version VARCHAR(20),
    capabilities JSONB DEFAULT '{}',
    
    CONSTRAINT valid_worker_status CHECK (status IN ('idle', 'working', 'error', 'offline'))
);

-- =============================================================================
-- AQEA ADDRESS MANAGEMENT
-- =============================================================================

-- Address Allocations - Verhindert Adress-Kollisionen
CREATE TABLE IF NOT EXISTS address_allocations (
    category_key VARCHAR(12) NOT NULL,  -- "20:01:01"
    element_id INTEGER NOT NULL,        -- 0x01-0xFE
    allocated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    allocated_by VARCHAR(50),           -- worker_id
    word VARCHAR(100),                  -- Für Debugging
    
    PRIMARY KEY (category_key, element_id),
    CONSTRAINT valid_element_id CHECK (element_id BETWEEN 1 AND 254)
);

-- =============================================================================
-- MONITORING & STATISTICS
-- =============================================================================

-- Extraction Statistics - Performance-Tracking
CREATE TABLE IF NOT EXISTS extraction_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Time & Scope
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    time_window_minutes INTEGER DEFAULT 1,
    language VARCHAR(10),
    source VARCHAR(20),
    
    -- Performance Metrics
    entries_processed INTEGER DEFAULT 0,
    processing_rate REAL DEFAULT 0.0,
    active_workers INTEGER DEFAULT 0,
    
    -- Quality Metrics
    success_rate REAL DEFAULT 0.0,
    error_count INTEGER DEFAULT 0,
    duplicate_count INTEGER DEFAULT 0,
    
    -- Resource Usage
    cpu_usage_percent REAL,
    memory_usage_mb INTEGER,
    network_io_mb REAL
);

-- Progress Snapshots - Für Dashboard & ETA
CREATE TABLE IF NOT EXISTS progress_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Overall Progress
    total_estimated_entries INTEGER,
    total_processed_entries INTEGER,
    progress_percent REAL,
    
    -- Performance
    current_rate_per_minute REAL,
    eta_hours REAL,
    
    -- Worker Stats
    total_workers INTEGER,
    active_workers INTEGER,
    idle_workers INTEGER,
    
    -- Work Unit Stats
    pending_work_units INTEGER,
    processing_work_units INTEGER,
    completed_work_units INTEGER,
    failed_work_units INTEGER
);

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- AQEA Entries Indexes
CREATE INDEX IF NOT EXISTS idx_aqea_entries_domain ON aqea_entries(domain);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_status ON aqea_entries(status);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_lang_ui ON aqea_entries(lang_ui);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_created_at ON aqea_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_search ON aqea_entries USING GIN(search_vector);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_meta ON aqea_entries USING GIN(meta);

-- Work Units Indexes
CREATE INDEX IF NOT EXISTS idx_work_units_status ON work_units(status);
CREATE INDEX IF NOT EXISTS idx_work_units_language ON work_units(language);
CREATE INDEX IF NOT EXISTS idx_work_units_assigned_worker ON work_units(assigned_worker);
CREATE INDEX IF NOT EXISTS idx_work_units_created_at ON work_units(created_at);

-- Worker Status Indexes
CREATE INDEX IF NOT EXISTS idx_worker_status_status ON worker_status(status);
CREATE INDEX IF NOT EXISTS idx_worker_status_last_heartbeat ON worker_status(last_heartbeat);

-- Address Allocations Indexes
CREATE INDEX IF NOT EXISTS idx_address_allocations_category ON address_allocations(category_key);
CREATE INDEX IF NOT EXISTS idx_address_allocations_allocated_at ON address_allocations(allocated_at);

-- =============================================================================
-- TRIGGERS & FUNCTIONS
-- =============================================================================

-- Update search vector for AQEA entries
CREATE OR REPLACE FUNCTION update_aqea_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', 
        COALESCE(NEW.label, '') || ' ' || 
        COALESCE(NEW.description, '') || ' ' ||
        COALESCE(NEW.meta->>'lemma', '') || ' ' ||
        COALESCE(array_to_string(
            array(SELECT jsonb_array_elements_text(NEW.meta->'definitions')), 
            ' '
        ), '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_search_vector
    BEFORE INSERT OR UPDATE ON aqea_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_aqea_search_vector();

-- Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_aqea_entries_updated_at
    BEFORE UPDATE ON aqea_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_work_units_updated_at
    BEFORE UPDATE ON work_units
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================================================

-- Enable RLS for sensitive tables
ALTER TABLE aqea_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_units ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_status ENABLE ROW LEVEL SECURITY;

-- Policies (can be customized based on authentication)
CREATE POLICY "Allow all operations for service role" ON aqea_entries
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for service role" ON work_units
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for service role" ON worker_status
    FOR ALL USING (true);

-- =============================================================================
-- SAMPLE DATA
-- =============================================================================

-- Insert initial work units for German
INSERT INTO work_units (work_id, language, source, range_start, range_end, estimated_entries) VALUES
    ('de_wiktionary_01', 'de', 'wiktionary', 'A', 'E', 160000),
    ('de_wiktionary_02', 'de', 'wiktionary', 'F', 'J', 120000),
    ('de_wiktionary_03', 'de', 'wiktionary', 'K', 'O', 140000),
    ('de_wiktionary_04', 'de', 'wiktionary', 'P', 'T', 180000),
    ('de_wiktionary_05', 'de', 'wiktionary', 'U', 'Z', 200000)
ON CONFLICT (work_id) DO NOTHING;

-- Initial progress snapshot
INSERT INTO progress_snapshots (
    total_estimated_entries, total_processed_entries, progress_percent,
    current_rate_per_minute, total_workers, active_workers, idle_workers,
    pending_work_units, processing_work_units, completed_work_units, failed_work_units
) VALUES (
    800000, 0, 0.0, 0.0, 0, 0, 0, 5, 0, 0, 0
);

-- Success! Schema created for AQEA Distributed Extractor
COMMENT ON DATABASE postgres IS 'AQEA Distributed Extractor - Central Supabase Database'; 
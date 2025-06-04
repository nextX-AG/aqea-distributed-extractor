-- AQEA Distributed Extractor Database Schema
-- PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create AQEA entries table
CREATE TABLE IF NOT EXISTS aqea_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(16) NOT NULL UNIQUE, -- AQEA 4-byte address (0xAA:QQ:EE:A2)
    label VARCHAR(60) NOT NULL,
    description TEXT NOT NULL,
    domain VARCHAR(4) NOT NULL, -- Domain byte (0xAA)
    lang_ui VARCHAR(10),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL DEFAULT 'system',
    reviewed_by VARCHAR(255),
    dictionary_id VARCHAR(100),
    version_hash VARCHAR(64),
    signature TEXT,
    element_hash VARCHAR(64),
    vector REAL[],
    embedding_source VARCHAR(50),
    aqea_path VARCHAR(255),
    license VARCHAR(50),
    relations JSONB DEFAULT '[]'::jsonb,
    meta JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_aqea_entries_address ON aqea_entries (address);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_domain ON aqea_entries (domain);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_status ON aqea_entries (status);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_label ON aqea_entries (label);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_created_at ON aqea_entries (created_at);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_lang_ui ON aqea_entries (lang_ui);

-- Indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_aqea_entries_meta_gin ON aqea_entries USING GIN (meta);
CREATE INDEX IF NOT EXISTS idx_aqea_entries_relations_gin ON aqea_entries USING GIN (relations);

-- Create work units table for distributed coordination
CREATE TABLE IF NOT EXISTS work_units (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_id VARCHAR(50) NOT NULL UNIQUE,
    language VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL,
    range_start VARCHAR(10) NOT NULL,
    range_end VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    assigned_worker VARCHAR(50),
    assigned_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    entries_processed INTEGER DEFAULT 0,
    estimated_entries INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    error_message TEXT,
    progress_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for work units
CREATE INDEX IF NOT EXISTS idx_work_units_status ON work_units (status);
CREATE INDEX IF NOT EXISTS idx_work_units_worker ON work_units (assigned_worker);
CREATE INDEX IF NOT EXISTS idx_work_units_language ON work_units (language);
CREATE INDEX IF NOT EXISTS idx_work_units_created_at ON work_units (created_at);

-- Create worker status table
CREATE TABLE IF NOT EXISTS worker_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'idle', -- idle, working, error, offline
    current_work_id VARCHAR(50),
    last_heartbeat TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    total_processed INTEGER DEFAULT 0,
    session_processed INTEGER DEFAULT 0,
    average_rate REAL DEFAULT 0.0,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    worker_info JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for worker status
CREATE INDEX IF NOT EXISTS idx_worker_status_worker_id ON worker_status (worker_id);
CREATE INDEX IF NOT EXISTS idx_worker_status_status ON worker_status (status);
CREATE INDEX IF NOT EXISTS idx_worker_status_heartbeat ON worker_status (last_heartbeat);

-- Create extraction sessions table
CREATE TABLE IF NOT EXISTS extraction_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(50) NOT NULL UNIQUE,
    language VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running', -- running, completed, failed, paused
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    total_workers INTEGER DEFAULT 0,
    total_work_units INTEGER DEFAULT 0,
    completed_work_units INTEGER DEFAULT 0,
    failed_work_units INTEGER DEFAULT 0,
    total_entries_processed INTEGER DEFAULT 0,
    estimated_total_entries INTEGER DEFAULT 0,
    configuration JSONB DEFAULT '{}'::jsonb,
    statistics JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for extraction sessions
CREATE INDEX IF NOT EXISTS idx_extraction_sessions_session_id ON extraction_sessions (session_id);
CREATE INDEX IF NOT EXISTS idx_extraction_sessions_status ON extraction_sessions (status);
CREATE INDEX IF NOT EXISTS idx_extraction_sessions_started_at ON extraction_sessions (started_at);

-- Create address mapping cache table
CREATE TABLE IF NOT EXISTS address_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    language VARCHAR(10) NOT NULL,
    domain_byte INTEGER NOT NULL,
    category_byte INTEGER NOT NULL,
    subcategory_byte INTEGER NOT NULL,
    element_byte INTEGER NOT NULL,
    word VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create unique constraint and indexes for address mappings
CREATE UNIQUE INDEX IF NOT EXISTS idx_address_mappings_unique 
    ON address_mappings (language, domain_byte, category_byte, subcategory_byte, element_byte);
CREATE INDEX IF NOT EXISTS idx_address_mappings_word ON address_mappings (word);
CREATE INDEX IF NOT EXISTS idx_address_mappings_language ON address_mappings (language);

-- Create functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_aqea_entries_updated_at 
    BEFORE UPDATE ON aqea_entries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_work_units_updated_at 
    BEFORE UPDATE ON work_units 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_worker_status_updated_at 
    BEFORE UPDATE ON worker_status 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_extraction_sessions_updated_at 
    BEFORE UPDATE ON extraction_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE OR REPLACE VIEW active_workers AS
SELECT 
    worker_id,
    status,
    current_work_id,
    last_heartbeat,
    total_processed,
    average_rate,
    EXTRACT(EPOCH FROM (NOW() - last_heartbeat)) AS seconds_since_heartbeat
FROM worker_status
WHERE status != 'offline' 
    AND last_heartbeat > NOW() - INTERVAL '5 minutes';

CREATE OR REPLACE VIEW work_unit_summary AS
SELECT 
    language,
    source,
    status,
    COUNT(*) as count,
    SUM(entries_processed) as total_entries,
    AVG(entries_processed) as avg_entries,
    MIN(created_at) as earliest_created,
    MAX(updated_at) as latest_updated
FROM work_units
GROUP BY language, source, status;

CREATE OR REPLACE VIEW session_progress AS
SELECT 
    s.session_id,
    s.language,
    s.source,
    s.status,
    s.started_at,
    s.total_workers,
    s.total_work_units,
    s.completed_work_units,
    s.failed_work_units,
    s.total_entries_processed,
    s.estimated_total_entries,
    CASE 
        WHEN s.estimated_total_entries > 0 
        THEN (s.total_entries_processed::REAL / s.estimated_total_entries) * 100
        ELSE 0
    END as progress_percent,
    EXTRACT(EPOCH FROM (NOW() - s.started_at)) / 3600 as runtime_hours
FROM extraction_sessions s;

-- Insert initial configuration data
INSERT INTO extraction_sessions (
    session_id, 
    language, 
    source, 
    status, 
    configuration
) VALUES (
    'initial-setup',
    'system',
    'configuration',
    'completed',
    '{"version": "1.0.0", "initialized_at": "' || NOW()::text || '"}'::jsonb
) ON CONFLICT (session_id) DO NOTHING;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aqea;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aqea;

-- Create helpful utility functions
CREATE OR REPLACE FUNCTION get_next_available_address(
    p_language VARCHAR(10),
    p_domain_byte INTEGER,
    p_category_byte INTEGER,
    p_subcategory_byte INTEGER
) RETURNS INTEGER AS $$
DECLARE
    next_element_byte INTEGER;
BEGIN
    -- Find the next available element byte for this category
    SELECT COALESCE(MAX(element_byte) + 1, 1)
    INTO next_element_byte
    FROM address_mappings
    WHERE language = p_language
        AND domain_byte = p_domain_byte
        AND category_byte = p_category_byte
        AND subcategory_byte = p_subcategory_byte;
    
    -- Ensure we don't exceed the reserved values (0xFE, 0xFF)
    IF next_element_byte >= 254 THEN
        RAISE EXCEPTION 'Address space exhausted for category %:%.%:%.%', 
            p_language, p_domain_byte, p_category_byte, p_subcategory_byte;
    END IF;
    
    RETURN next_element_byte;
END;
$$ LANGUAGE plpgsql;

-- Performance monitoring view
CREATE OR REPLACE VIEW performance_metrics AS
SELECT 
    w.worker_id,
    w.status,
    w.total_processed,
    w.average_rate,
    wu.work_id,
    wu.entries_processed as current_work_entries,
    wu.progress_data->>'processing_rate' as current_rate,
    EXTRACT(EPOCH FROM (w.last_heartbeat - wu.started_at)) / 60 as work_duration_minutes
FROM worker_status w
LEFT JOIN work_units wu ON w.current_work_id = wu.work_id
WHERE w.status = 'working';

-- Final initialization log
INSERT INTO extraction_sessions (
    session_id,
    language,
    source,
    status,
    configuration
) VALUES (
    'db-initialized-' || EXTRACT(EPOCH FROM NOW())::bigint,
    'system',
    'database',
    'completed',
    jsonb_build_object(
        'tables_created', ARRAY['aqea_entries', 'work_units', 'worker_status', 'extraction_sessions', 'address_mappings'],
        'views_created', ARRAY['active_workers', 'work_unit_summary', 'session_progress', 'performance_metrics'],
        'initialized_at', NOW()
    )
) ON CONFLICT (session_id) DO NOTHING; 
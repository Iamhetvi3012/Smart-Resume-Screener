-- SQL script to create caching tables in Supabase
-- Run this in your Supabase SQL Editor
-- 
-- Two-level caching strategy:
-- 1. parsed_resumes: Cache parsed resume data by file hash
-- 2. screening_results: Cache screening results by file hash + job details

-- ============================================================================
-- TABLE 1: Parsed Resumes Cache
-- Stores parsed resume data indexed by file hash
-- ============================================================================

CREATE TABLE IF NOT EXISTS parsed_resumes (
    id BIGSERIAL PRIMARY KEY,
    file_hash TEXT UNIQUE NOT NULL,
    parsed_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups by file hash
CREATE INDEX IF NOT EXISTS idx_parsed_file_hash ON parsed_resumes(file_hash);

-- Comment
COMMENT ON TABLE parsed_resumes IS 'Caches parsed resume data to avoid re-parsing the same resume file';

-- ============================================================================
-- TABLE 2: Screening Results Cache
-- Stores screening results indexed by composite key (file hash + job details)
-- ============================================================================

CREATE TABLE IF NOT EXISTS screening_results (
    id BIGSERIAL PRIMARY KEY,
    screening_key TEXT UNIQUE NOT NULL,
    file_hash TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_description TEXT NOT NULL,
    screening_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups by screening key
CREATE INDEX IF NOT EXISTS idx_screening_key ON screening_results(screening_key);

-- Index for lookups by file hash (to find all screenings for a resume)
CREATE INDEX IF NOT EXISTS idx_screening_file_hash ON screening_results(file_hash);

-- Comment
COMMENT ON TABLE screening_results IS 'Caches screening results for resume+job combinations';

-- ============================================================================
-- TRIGGER: Auto-update timestamps
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for parsed_resumes
CREATE TRIGGER update_parsed_resumes_updated_at BEFORE UPDATE
    ON parsed_resumes FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for screening_results
CREATE TRIGGER update_screening_results_updated_at BEFORE UPDATE
    ON screening_results FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

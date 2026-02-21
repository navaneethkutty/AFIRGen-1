-- Migration: Add database indexes for FIR tables
-- Task: 2.6 Create database indexes for FIR tables
-- Requirements: 1.2

-- Add user_id column if it doesn't exist
ALTER TABLE fir_records 
ADD COLUMN IF NOT EXISTS user_id VARCHAR(100) AFTER session_id;

-- Drop existing basic indexes (they will be replaced with optimized versions)
-- Note: Using IF EXISTS to make migration idempotent
DROP INDEX IF EXISTS idx_fir_number ON fir_records;
DROP INDEX IF EXISTS idx_session_id ON fir_records;
DROP INDEX IF EXISTS idx_status ON fir_records;
DROP INDEX IF EXISTS idx_created_at ON fir_records;

-- Primary indexes on frequently queried columns
-- These support single-column lookups efficiently
CREATE INDEX idx_fir_number ON fir_records(fir_number);
CREATE INDEX idx_session_id ON fir_records(session_id);
CREATE INDEX idx_status ON fir_records(status);
CREATE INDEX idx_created_at ON fir_records(created_at DESC);
CREATE INDEX idx_user_id ON fir_records(user_id);

-- Composite indexes for common query patterns
-- Pattern 1: User's FIRs ordered by creation date (most common query)
CREATE INDEX idx_user_created ON fir_records(user_id, created_at DESC);

-- Pattern 2: Filter by status and sort by date (dashboard queries)
CREATE INDEX idx_status_created ON fir_records(status, created_at DESC);

-- Pattern 3: User's FIRs filtered by status (user-specific status queries)
CREATE INDEX idx_user_status_created ON fir_records(user_id, status, created_at DESC);

-- Pattern 4: Finalized FIRs ordered by finalization date
CREATE INDEX idx_status_finalized ON fir_records(status, finalized_at DESC);

-- Full-text indexes for search functionality
-- Enable full-text search on complaint text
ALTER TABLE fir_records 
ADD FULLTEXT INDEX ft_complaint_text (complaint_text);

-- Enable full-text search on FIR content
ALTER TABLE fir_records 
ADD FULLTEXT INDEX ft_fir_content (fir_content);

-- Covering index for common SELECT queries
-- This index includes all columns typically retrieved together
-- Allows index-only scans without table lookups
CREATE INDEX idx_covering_list ON fir_records(
    user_id, 
    status, 
    created_at DESC, 
    fir_number, 
    session_id
);

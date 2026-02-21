-- Rollback Migration: Remove database indexes for FIR tables
-- Task: 2.6 Create database indexes for FIR tables
-- This script reverts the changes made by 001_add_fir_indexes.sql

-- Drop full-text indexes
ALTER TABLE fir_records DROP INDEX IF EXISTS ft_complaint_text;
ALTER TABLE fir_records DROP INDEX IF EXISTS ft_fir_content;

-- Drop covering index
DROP INDEX IF EXISTS idx_covering_list ON fir_records;

-- Drop composite indexes
DROP INDEX IF EXISTS idx_user_created ON fir_records;
DROP INDEX IF EXISTS idx_status_created ON fir_records;
DROP INDEX IF EXISTS idx_user_status_created ON fir_records;
DROP INDEX IF EXISTS idx_status_finalized ON fir_records;

-- Drop primary indexes (new ones)
DROP INDEX IF EXISTS idx_user_id ON fir_records;

-- Restore original basic indexes
CREATE INDEX idx_fir_number ON fir_records(fir_number);
CREATE INDEX idx_session_id ON fir_records(session_id);
CREATE INDEX idx_status ON fir_records(status);
CREATE INDEX idx_created_at ON fir_records(created_at);

-- Note: We don't remove the user_id column in rollback to prevent data loss
-- If you need to remove it, run this separately after backing up data:
-- ALTER TABLE fir_records DROP COLUMN user_id;

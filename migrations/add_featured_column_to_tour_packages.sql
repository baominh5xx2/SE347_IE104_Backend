-- =====================================================
-- Migration: Add Featured Column to Tour Packages
-- Description: Add is_featured column to support Admin Control Tour Recommendations
-- Date: 2025-12-10
-- =====================================================

-- Add is_featured column to tour_packages
ALTER TABLE tour_packages
ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;

-- Add comment to column
COMMENT ON COLUMN tour_packages.is_featured IS 'Indicates if tour is featured/promoted by admin for recommendations';

-- Create partial index for featured tours (only TRUE values)
-- This improves query performance when fetching featured tours
CREATE INDEX IF NOT EXISTS idx_packages_featured 
ON tour_packages (is_featured) 
WHERE is_featured = TRUE;

-- Create compound index for active featured tours (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_packages_featured_active 
ON tour_packages (is_featured, is_active) 
WHERE is_featured = TRUE AND is_active = TRUE;

-- Update statistics for query planner
ANALYZE tour_packages;

-- Verification query (run manually to check)
-- SELECT COUNT(*) as featured_count FROM tour_packages WHERE is_featured = TRUE;

-- Migration: Update all tour package dates to year 2026
-- Description: Updates start_date and end_date of all tour packages to 2026
-- while preserving the month and day

-- Update tour packages dates to 2026
UPDATE tour_packages
SET 
    start_date = start_date + INTERVAL '1 year' * (2026 - EXTRACT(YEAR FROM start_date)::int),
    end_date = end_date + INTERVAL '1 year' * (2026 - EXTRACT(YEAR FROM end_date)::int),
    updated_at = NOW()
WHERE 
    EXTRACT(YEAR FROM start_date) < 2026
    OR EXTRACT(YEAR FROM end_date) < 2026;

-- Verify the update
SELECT 
    package_id,
    package_name,
    start_date,
    end_date,
    EXTRACT(YEAR FROM start_date) as start_year,
    EXTRACT(YEAR FROM end_date) as end_year
FROM tour_packages
ORDER BY start_date
LIMIT 10;

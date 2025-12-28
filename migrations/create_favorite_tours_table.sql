-- ============================================
-- Create Favorite Tours Table
-- Migration để tạo bảng lưu tours yêu thích của users
-- ============================================

-- Tạo bảng favorite_tours
CREATE TABLE IF NOT EXISTS favorite_tours (
    favorite_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    package_id UUID NOT NULL REFERENCES tour_packages(package_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tạo unique constraint để tránh user favorite cùng 1 tour nhiều lần
CREATE UNIQUE INDEX IF NOT EXISTS idx_favorite_tours_user_package 
    ON favorite_tours(user_id, package_id);

-- Tạo index để optimize queries theo user_id
CREATE INDEX IF NOT EXISTS idx_favorite_tours_user ON favorite_tours(user_id);

-- Tạo index để optimize queries theo package_id
CREATE INDEX IF NOT EXISTS idx_favorite_tours_package ON favorite_tours(package_id);

-- Tạo index để optimize queries theo created_at (sắp xếp theo thời gian)
CREATE INDEX IF NOT EXISTS idx_favorite_tours_created_at ON favorite_tours(created_at DESC);

-- Verification query
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'favorite_tours'
ORDER BY ordinal_position;

-- Check unique constraint
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'favorite_tours'::regclass
    AND contype = 'u';


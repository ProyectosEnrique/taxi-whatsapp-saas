-- ============================================================================
-- Migration: Add is_beverage field to categories table
-- Description: Separates beverages from food items for routing to different screens
--              - Beverages go to waiter dashboard
--              - Food items go to kitchen display
-- Date: 2024-12-16
-- ============================================================================

-- Step 1: Add the is_beverage column
ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_beverage BOOLEAN DEFAULT FALSE;

-- Step 2: Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_categories_is_beverage ON categories(is_beverage);

-- Step 3: Mark existing beverage categories
-- This will mark any category with common beverage-related names
UPDATE categories SET is_beverage = TRUE
WHERE LOWER(name) LIKE '%bebida%'
   OR LOWER(name) LIKE '%refresco%'
   OR LOWER(name) LIKE '%cerveza%'
   OR LOWER(name) LIKE '%licor%'
   OR LOWER(name) LIKE '%vino%'
   OR LOWER(name) LIKE '%jugo%'
   OR LOWER(name) LIKE '%agua%'
   OR LOWER(name) LIKE '%drink%'
   OR LOWER(name) LIKE '%beverage%'
   OR LOWER(name) LIKE '%coffee%'
   OR LOWER(name) LIKE '%cafe%'
   OR LOWER(name) LIKE '%té%'
   OR LOWER(name) LIKE '%tea%'
   OR LOWER(name) LIKE '%cocktail%'
   OR LOWER(name) LIKE '%coctel%';

-- Step 4: Verify the migration
SELECT id, name, is_beverage FROM categories ORDER BY is_beverage DESC, name;

-- ============================================================================
-- ROLLBACK (if needed):
-- ALTER TABLE categories DROP COLUMN is_beverage;
-- ============================================================================

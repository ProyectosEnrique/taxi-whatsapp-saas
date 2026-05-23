-- ============================================================================
-- Migration 004: Add Meta Commerce Catalog Fields
-- ============================================================================
-- Agrega campos para integracion con WhatsApp Business Catalog (Meta Commerce)
-- Permite sincronizacion automatica de productos con el catalogo de Meta
-- ============================================================================

-- Agregar campos Meta a la tabla products
ALTER TABLE products ADD COLUMN IF NOT EXISTS product_retailer_id VARCHAR(100) UNIQUE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_image_id VARCHAR(100);
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_last_sync TIMESTAMP WITH TIME ZONE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS meta_sync_error TEXT;

-- Crear indices para optimizar busquedas
CREATE INDEX IF NOT EXISTS idx_products_retailer_id ON products(product_retailer_id);
CREATE INDEX IF NOT EXISTS idx_products_meta_sync_status ON products(meta_sync_status);

-- Comentarios descriptivos
COMMENT ON COLUMN products.product_retailer_id IS 'ID unico del producto en el catalogo de Meta Commerce';
COMMENT ON COLUMN products.meta_image_id IS 'ID de la imagen subida a Meta Media API';
COMMENT ON COLUMN products.meta_sync_status IS 'Estado de sincronizacion: pending, synced, error';
COMMENT ON COLUMN products.meta_last_sync IS 'Fecha y hora de la ultima sincronizacion exitosa';
COMMENT ON COLUMN products.meta_sync_error IS 'Mensaje del ultimo error de sincronizacion';

-- Generar product_retailer_id para productos existentes (usando uuid existente)
UPDATE products
SET product_retailer_id = CONCAT('product_', id)
WHERE product_retailer_id IS NULL;

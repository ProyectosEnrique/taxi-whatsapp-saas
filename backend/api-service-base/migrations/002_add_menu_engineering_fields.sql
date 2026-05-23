-- ============================================================================
-- MIGRACION: Agregar campos de Ingenieria del Menu
-- Version: 002
-- Fecha: 2025-01-27
-- ============================================================================

ALTER TABLE products ADD COLUMN IF NOT EXISTS video_url VARCHAR(500);
ALTER TABLE products ADD COLUMN IF NOT EXISTS ingredients TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS spice_level INTEGER DEFAULT 0;
ALTER TABLE products ADD COLUMN IF NOT EXISTS popularity INTEGER DEFAULT 3;
ALTER TABLE products ADD COLUMN IF NOT EXISTS profitability VARCHAR(10) DEFAULT 'media';
ALTER TABLE products ADD COLUMN IF NOT EXISTS cost DECIMAL(10, 2);
ALTER TABLE products ADD COLUMN IF NOT EXISTS menu_classification VARCHAR(20);

CREATE INDEX IF NOT EXISTS idx_products_menu_classification ON products(menu_classification);
CREATE INDEX IF NOT EXISTS idx_products_popularity ON products(popularity);
CREATE INDEX IF NOT EXISTS idx_products_profitability ON products(profitability);

COMMENT ON COLUMN products.video_url IS 'URL del video para platillos estrella';
COMMENT ON COLUMN products.ingredients IS 'Ingredientes principales (alergias/preferencias)';
COMMENT ON COLUMN products.spice_level IS 'Nivel de picante: 0=nada, 1=bajo, 2=medio, 3=alto';
COMMENT ON COLUMN products.popularity IS 'Popularidad: 1=poco pedido, 5=muy pedido';
COMMENT ON COLUMN products.profitability IS 'Rentabilidad: alta, media, baja';
COMMENT ON COLUMN products.cost IS 'Costo del platillo para calcular margen';
COMMENT ON COLUMN products.menu_classification IS 'Clasificacion: estrella, caballo, perro, rompecabezas';

-- ============================================================================
-- MULTI-TENANT WHATSAPP SAAS - PostgreSQL Schema
-- ============================================================================
-- Sistema multi-tenant con números dedicados por tienda
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- TABLA: restaurants (Tiendas/Negocios)
-- ============================================================================
CREATE TABLE restaurants (
    id SERIAL PRIMARY KEY,
    restaurant_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,

    -- Información del dueño
    owner_name VARCHAR(255) NOT NULL,
    owner_email VARCHAR(255) NOT NULL,
    owner_phone VARCHAR(20) NOT NULL,

    -- Tipo de negocio
    business_type VARCHAR(50) NOT NULL,
    business_category VARCHAR(100),

    -- Ubicación
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'México',
    postal_code VARCHAR(20),

    -- Configuración WhatsApp/Twilio
    twilio_number VARCHAR(20) UNIQUE,
    twilio_sid VARCHAR(100),
    whatsapp_business_name VARCHAR(255),

    -- Plan y billing
    plan VARCHAR(50) DEFAULT 'basic',
    monthly_price DECIMAL(10,2),
    subscription_status VARCHAR(50) DEFAULT 'active',
    subscription_started_at TIMESTAMP,
    subscription_expires_at TIMESTAMP,

    -- Branding
    logo_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#4F46E5',

    -- Configuración
    timezone VARCHAR(50) DEFAULT 'America/Mexico_City',
    currency VARCHAR(3) DEFAULT 'MXN',
    language VARCHAR(5) DEFAULT 'es',
    business_hours JSONB,

    -- Estado
    status VARCHAR(50) DEFAULT 'active',
    is_demo BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

CREATE INDEX idx_restaurants_restaurant_id ON restaurants(restaurant_id);
CREATE INDEX idx_restaurants_twilio_number ON restaurants(twilio_number);
CREATE INDEX idx_restaurants_status ON restaurants(status);

-- ============================================================================
-- TABLA: users (Usuarios del sistema)
-- ============================================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,

    -- Autenticación
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Información personal
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),

    -- Rol y permisos
    role VARCHAR(50) NOT NULL,
    permissions JSONB,

    -- Estado
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),

    -- Password reset
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP,

    -- Timestamps
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_restaurant_id ON users(restaurant_id);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================================
-- TABLA: categories (Categorías de productos)
-- ============================================================================
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    category_id VARCHAR(50) UNIQUE NOT NULL,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    icon VARCHAR(50),
    description TEXT,

    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_restaurant_id ON categories(restaurant_id);

-- ============================================================================
-- TABLA: products (Productos por tienda)
-- ============================================================================
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(50) UNIQUE NOT NULL,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    category_id VARCHAR(50) REFERENCES categories(category_id) ON DELETE SET NULL,

    -- Información básica
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,

    -- Precio
    price DECIMAL(10,2) NOT NULL,
    compare_at_price DECIMAL(10,2),
    cost DECIMAL(10,2),

    -- Imágenes
    image_url TEXT,
    images JSONB,

    -- Inventario
    track_inventory BOOLEAN DEFAULT FALSE,
    stock_quantity INTEGER DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 10,

    -- Disponibilidad
    available BOOLEAN DEFAULT TRUE,
    available_start_time TIME,
    available_end_time TIME,

    -- Opciones y variantes
    has_variants BOOLEAN DEFAULT FALSE,
    variants JSONB,
    modifiers JSONB,

    -- Orden y destacados
    display_order INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL
);

CREATE INDEX idx_products_restaurant_id ON products(restaurant_id);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_available ON products(available);

-- ============================================================================
-- TABLA: customers (Clientes por tienda)
-- ============================================================================
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,

    -- Identificación
    phone VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),

    -- Información adicional
    birthday DATE,
    address TEXT,
    notes TEXT,
    tags JSONB,

    -- Estadísticas
    total_orders INTEGER DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0,
    average_order_value DECIMAL(10,2) DEFAULT 0,

    -- Timestamps
    first_order_at TIMESTAMP,
    last_order_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(restaurant_id, phone)
);

CREATE INDEX idx_customers_restaurant_id ON customers(restaurant_id);
CREATE INDEX idx_customers_phone ON customers(phone);

-- ============================================================================
-- TABLA: orders (Pedidos)
-- ============================================================================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    customer_id VARCHAR(50) REFERENCES customers(customer_id) ON DELETE SET NULL,

    -- Cliente
    customer_phone VARCHAR(20) NOT NULL,
    customer_name VARCHAR(255),

    -- Items del pedido
    items JSONB NOT NULL,

    -- Montos
    subtotal DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    loyalty_discount DECIMAL(10,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    delivery_fee DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(10,2) NOT NULL,

    -- Pago
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'pending',
    payment_details JSONB,

    -- Entrega
    delivery_type VARCHAR(50) DEFAULT 'pickup',
    delivery_address TEXT,
    delivery_notes TEXT,

    -- Estado del pedido
    status VARCHAR(50) DEFAULT 'pending',

    -- Notas
    customer_notes TEXT,
    internal_notes TEXT,

    -- Loyalty
    loyalty_points_used INTEGER DEFAULT 0,
    loyalty_points_earned INTEGER DEFAULT 0,

    -- Origen
    source VARCHAR(50) DEFAULT 'whatsapp',

    -- Timestamps
    confirmed_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_restaurant_id ON orders(restaurant_id);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- ============================================================================
-- TABLA: loyalty_configs (Configuración de puntos por tienda)
-- ============================================================================
CREATE TABLE loyalty_configs (
    id SERIAL PRIMARY KEY,
    restaurant_id VARCHAR(50) UNIQUE REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,

    enabled BOOLEAN DEFAULT TRUE,

    points_per_currency DECIMAL(5,2) DEFAULT 0.1,
    currency_per_point DECIMAL(5,2) DEFAULT 0.5,

    min_points_to_redeem INTEGER DEFAULT 100,
    max_redeem_percentage DECIMAL(5,2) DEFAULT 50.0,
    points_expire_days INTEGER DEFAULT 365,

    tiers_enabled BOOLEAN DEFAULT TRUE,
    tier_thresholds JSONB,
    tier_multipliers JSONB,
    tier_benefits JSONB,

    birthday_bonus INTEGER DEFAULT 100,
    referral_bonus INTEGER DEFAULT 50,
    first_purchase_bonus INTEGER DEFAULT 50,

    notify_points_earned BOOLEAN DEFAULT TRUE,
    notify_tier_upgrade BOOLEAN DEFAULT TRUE,
    notify_points_expiring BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA: loyalty_accounts (Cuentas de puntos por cliente)
-- ============================================================================
CREATE TABLE loyalty_accounts (
    id SERIAL PRIMARY KEY,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    customer_id VARCHAR(50) REFERENCES customers(customer_id) ON DELETE CASCADE,
    customer_phone VARCHAR(20) NOT NULL,

    points_balance INTEGER DEFAULT 0,
    points_lifetime INTEGER DEFAULT 0,
    points_redeemed INTEGER DEFAULT 0,

    tier_level VARCHAR(50) DEFAULT 'bronze',
    tier_progress INTEGER DEFAULT 0,

    total_spent DECIMAL(10,2) DEFAULT 0,
    total_orders INTEGER DEFAULT 0,

    last_earned_at TIMESTAMP,
    last_redeemed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(restaurant_id, customer_phone)
);

CREATE INDEX idx_loyalty_accounts_restaurant_id ON loyalty_accounts(restaurant_id);
CREATE INDEX idx_loyalty_accounts_customer_id ON loyalty_accounts(customer_id);

-- ============================================================================
-- TABLA: loyalty_transactions (Transacciones de puntos)
-- ============================================================================
CREATE TABLE loyalty_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    customer_id VARCHAR(50) REFERENCES customers(customer_id) ON DELETE CASCADE,
    order_id VARCHAR(50) REFERENCES orders(order_id) ON DELETE SET NULL,

    transaction_type VARCHAR(50) NOT NULL,

    points_amount INTEGER NOT NULL,
    points_balance_before INTEGER NOT NULL,
    points_balance_after INTEGER NOT NULL,

    description TEXT,
    metadata JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_loyalty_transactions_restaurant_id ON loyalty_transactions(restaurant_id);
CREATE INDEX idx_loyalty_transactions_customer_id ON loyalty_transactions(customer_id);
CREATE INDEX idx_loyalty_transactions_created_at ON loyalty_transactions(created_at);

-- ============================================================================
-- TABLA: sessions (Sesiones de WhatsApp)
-- ============================================================================
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,

    phone VARCHAR(20) NOT NULL,

    state VARCHAR(50) DEFAULT 'idle',
    context JSONB,
    cart JSONB,

    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_restaurant_id ON sessions(restaurant_id);
CREATE INDEX idx_sessions_phone ON sessions(phone);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

-- ============================================================================
-- TABLA: payment_methods (Métodos de pago configurados)
-- ============================================================================
CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    restaurant_id VARCHAR(50) REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,

    provider VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,

    config JSONB,

    display_name VARCHAR(255),
    icon VARCHAR(50),
    instructions TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_methods_restaurant_id ON payment_methods(restaurant_id);

-- ============================================================================
-- TRIGGERS para updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_restaurants_updated_at BEFORE UPDATE ON restaurants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DATOS INICIALES
-- ============================================================================

-- Insertar super admin
INSERT INTO users (user_id, email, password_hash, full_name, role, is_active, email_verified)
VALUES (
    'user_superadmin',
    'admin@tuplatforma.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ztN4YqT8XrYK',
    'Super Admin',
    'super_admin',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

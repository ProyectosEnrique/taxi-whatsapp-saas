# ============================================================================
# DATABASE - Configuración de PostgreSQL con SQLAlchemy
# ============================================================================

import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# URL de la base de datos
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/whatsapp_saas"
)

# Si es SQLite para desarrollo local
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    DATABASE_URL = "sqlite:///./whatsapp_saas.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    logger.info("Using SQLite database for development")
else:
    # PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )
    logger.info(f"Connected to PostgreSQL database")


# ============================================================================
# SESSION
# ============================================================================

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos ORM
Base = declarative_base()


# ============================================================================
# DEPENDENCY
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de base de datos.
    Uso en FastAPI:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# INIT DATABASE
# ============================================================================

def init_db():
    """
    Inicializar base de datos.
    Crea todas las tablas si no existen.
    """
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def drop_all_tables():
    """
    CUIDADO: Elimina todas las tablas.
    Solo para desarrollo.
    """
    logger.warning("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped")


# ============================================================================
# HEALTH CHECK
# ============================================================================

def check_db_connection() -> bool:
    """
    Verificar conexión a base de datos.
    """
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

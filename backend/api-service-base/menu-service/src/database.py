"""
================================================================================
DATABASE - Menu Service
================================================================================
Configuración de SQLAlchemy y gestión de sesiones de base de datos
================================================================================
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from .config import settings

# ==============================================================================
# ENGINE
# ==============================================================================

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.POSTGRES_POOL_SIZE,
    max_overflow=settings.POSTGRES_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verificar conexión antes de usar
    echo=settings.ENVIRONMENT == "development",  # SQL logging en desarrollo
)

# ==============================================================================
# SESSION
# ==============================================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ==============================================================================
# BASE
# ==============================================================================

Base = declarative_base()

# ==============================================================================
# DEPENDENCY
# ==============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de base de datos

    Uso en FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

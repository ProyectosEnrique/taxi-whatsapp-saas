"""
================================================================================
DATABASE HELPER
================================================================================
Helper para conexiones y queries a PostgreSQL desde voice-assistant.
Usado principalmente por WhatsApp analytics y segmentation.
================================================================================
"""

import os
import logging
from typing import List, Dict, Optional, Any
import asyncpg
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseHelper:
    """Helper para operaciones de base de datos asíncronas"""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'restaurant_db'),
            'user': os.getenv('POSTGRES_USER', 'restaurant'),
            'password': os.getenv('POSTGRES_PASSWORD', 'restaurant_2025_prod'),
        }

    async def connect(self):
        """Inicializar connection pool"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    **self.db_config,
                    min_size=2,
                    max_size=10,
                    command_timeout=60
                )
                logger.info("[DB] Connection pool creado exitosamente")
            except Exception as e:
                logger.error(f"[DB] Error creando connection pool: {e}")
                raise

    async def close(self):
        """Cerrar connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("[DB] Connection pool cerrado")

    @asynccontextmanager
    async def acquire(self):
        """Context manager para adquirir conexión del pool"""
        if self.pool is None:
            await self.connect()

        async with self.pool.acquire() as conn:
            yield conn

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """
        Ejecutar query SELECT y retornar resultados como lista de dicts.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Lista de diccionarios con resultados
        """
        try:
            async with self.acquire() as conn:
                rows = await conn.fetch(query, *args)
                # Convertir Record a dict
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[DB] Error en fetch: {e}\nQuery: {query}")
            return []

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """
        Ejecutar query SELECT y retornar primera fila como dict.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Diccionario con resultado o None
        """
        try:
            async with self.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"[DB] Error en fetchrow: {e}\nQuery: {query}")
            return None

    async def fetchval(self, query: str, *args) -> Any:
        """
        Ejecutar query y retornar primer valor de primera fila.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Valor único o None
        """
        try:
            async with self.acquire() as conn:
                return await conn.fetchval(query, *args)
        except Exception as e:
            logger.error(f"[DB] Error en fetchval: {e}\nQuery: {query}")
            return None

    async def execute(self, query: str, *args) -> str:
        """
        Ejecutar query INSERT/UPDATE/DELETE.

        Args:
            query: SQL query
            *args: Query parameters

        Returns:
            Status string from PostgreSQL
        """
        try:
            async with self.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"[DB] Error en execute: {e}\nQuery: {query}")
            raise

    async def executemany(self, query: str, args_list: List[tuple]) -> None:
        """
        Ejecutar query múltiples veces con diferentes parámetros.

        Args:
            query: SQL query
            args_list: Lista de tuplas con parámetros
        """
        try:
            async with self.acquire() as conn:
                await conn.executemany(query, args_list)
        except Exception as e:
            logger.error(f"[DB] Error en executemany: {e}\nQuery: {query}")
            raise


# Singleton
_db_helper = None


def get_db_helper() -> DatabaseHelper:
    """Obtiene instancia singleton de DatabaseHelper"""
    global _db_helper
    if _db_helper is None:
        _db_helper = DatabaseHelper()
    return _db_helper


async def init_db():
    """Inicializar base de datos (llamar al inicio de la aplicación)"""
    db = get_db_helper()
    await db.connect()
    logger.info("[DB] Database helper initialized")


async def close_db():
    """Cerrar base de datos (llamar al final de la aplicación)"""
    db = get_db_helper()
    await db.close()
    logger.info("[DB] Database helper closed")

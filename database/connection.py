"""
Database connection management for PostgreSQL.
Handles connection pooling and database initialization.
"""

import asyncio
import asyncpg
import logging
import os
from typing import Optional
from contextlib import asynccontextmanager

log = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


class DatabaseConfig:
    """Database configuration from environment variables."""

    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.database = os.getenv("DB_NAME", "aimod_bot")
        self.user = os.getenv("DB_USER", "aimod_user")
        self.password = os.getenv("DB_PASSWORD", "")
        self.database_url = os.getenv("DATABASE_URL")

    def get_connection_kwargs(self) -> dict:
        """Get connection parameters for asyncpg."""
        if self.database_url:
            # asyncpg doesn't support the +asyncpg scheme, so we remove it
            dsn = self.database_url.replace("postgresql+asyncpg", "postgresql")
            return {"dsn": dsn}
        else:
            return {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "user": self.user,
                "password": self.password,
            }


async def create_pool(min_size: int = 5, max_size: int = 20) -> asyncpg.Pool:
    """Create a connection pool to the PostgreSQL database."""
    config = DatabaseConfig()
    connection_kwargs = config.get_connection_kwargs()

    try:
        pool = await asyncpg.create_pool(
            min_size=min_size,
            max_size=max_size,
            command_timeout=60,
            **connection_kwargs,
        )
        log.info(f"Created database connection pool (min={min_size}, max={max_size})")
        return pool
    except Exception as e:
        log.error(f"Failed to create database connection pool: {e}")
        raise


async def initialize_database() -> bool:
    """
    Initialize the database with required tables and indexes only if they don't exist.
    """
    from database.models import SCHEMA_SQL, INDEXES_SQL, TRIGGERS_SQL

    config = DatabaseConfig()
    connection_kwargs = config.get_connection_kwargs()

    conn = None
    try:
        # Create a single connection for initialization
        conn = await asyncpg.connect(**connection_kwargs)

        # Split SQL into individual statements and execute them if tables/indexes/triggers don't exist
        # This allows for incremental updates without dropping existing data.

        # Execute schema creation statements
        for statement in SCHEMA_SQL.split(";")[
            :-1
        ]:  # Split by semicolon, ignore last empty string
            if statement.strip():
                try:
                    await conn.execute(statement)
                    log.info(
                        f"Executed schema statement: {statement.strip().splitlines()[0]}..."
                    )
                except asyncpg.exceptions.DuplicateTableError:
                    log.info(
                        f"Table already exists for statement: {statement.strip().splitlines()[0]}..."
                    )
                except Exception as e:
                    log.error(
                        f"Error executing schema statement: {statement.strip().splitlines()[0]}... Error: {e}"
                    )
                    raise

        log.info("Database schema initialization complete.")

        # Execute index creation statements
        for statement in INDEXES_SQL.split(";")[:-1]:
            if statement.strip():
                try:
                    await conn.execute(statement)
                    log.info(
                        f"Executed index statement: {statement.strip().splitlines()[0]}..."
                    )
                except asyncpg.exceptions.DuplicateObjectError:
                    log.info(
                        f"Index already exists for statement: {statement.strip().splitlines()[0]}..."
                    )
                except Exception as e:
                    log.error(
                        f"Error executing index statement: {statement.strip().splitlines()[0]}... Error: {e}"
                    )
                    raise

        log.info("Database indexes initialization complete.")

        # Execute trigger creation statements as a single block
        try:
            await conn.execute(TRIGGERS_SQL)
            log.info("Database triggers created/updated successfully.")
        except asyncpg.exceptions.DuplicateObjectError:
            log.info("Triggers already exist. Skipping creation.")
        except Exception as e:
            log.error(f"Error executing trigger statements: {e}")
            raise

        log.info("Database triggers initialization complete.")
        return True

    except Exception as e:
        log.error(f"Failed to initialize database: {e}")
        return False
    finally:
        if conn:
            await conn.close()


async def get_pool() -> asyncpg.Pool:
    """Get the global connection pool, creating it if necessary."""
    global _pool

    if _pool is None:
        _pool = await create_pool()

    return _pool


async def close_pool():
    """Close the global connection pool."""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None
        log.info("Database connection pool closed")


@asynccontextmanager
async def get_connection():
    """Get a database connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as connection:
        yield connection


@asynccontextmanager
async def get_transaction():
    """Get a database transaction."""
    async with get_connection() as conn:
        async with conn.transaction():
            yield conn


async def execute_query(
    query: str, *args, fetch_one: bool = False, fetch_all: bool = False
):
    """Execute a database query with automatic connection management."""
    async with get_connection() as conn:
        if fetch_one:
            return await conn.fetchrow(query, *args)
        elif fetch_all:
            return await conn.fetch(query, *args)
        else:
            return await conn.execute(query, *args)


async def test_connection() -> bool:
    """Test the database connection."""
    try:
        async with get_connection() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        log.error(f"Database connection test failed: {e}")
        return False


# Utility functions for common operations


async def insert_or_update(table: str, conflict_columns: list, data: dict) -> bool:
    """Insert or update a record using ON CONFLICT."""
    columns = list(data.keys())
    values = list(data.values())
    placeholders = [f"${i+1}" for i in range(len(values))]

    # Build the conflict resolution part
    conflict_cols = ", ".join(conflict_columns)
    update_cols = ", ".join(
        [f"{col} = EXCLUDED.{col}" for col in columns if col not in conflict_columns]
    )

    query = f"""
        INSERT INTO {table} ({", ".join(columns)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT ({conflict_cols})
        DO UPDATE SET {update_cols}
    """

    try:
        await execute_query(query, *values)
        return True
    except Exception as e:
        log.error(f"Failed to insert/update in {table}: {e}")
        return False


async def delete_record(table: str, where_clause: str, *args) -> bool:
    """Delete a record from a table."""
    query = f"DELETE FROM {table} WHERE {where_clause}"

    try:
        await execute_query(query, *args)
        return True
    except Exception as e:
        log.error(f"Failed to delete from {table}: {e}")
        return False


async def count_records(table: str, where_clause: str = "", *args) -> int:
    """Count records in a table."""
    query = f"SELECT COUNT(*) FROM {table}"
    if where_clause:
        query += f" WHERE {where_clause}"

    try:
        result = await execute_query(query, *args, fetch_one=True)
        return result[0] if result else 0
    except Exception as e:
        log.error(f"Failed to count records in {table}: {e}")
        return 0

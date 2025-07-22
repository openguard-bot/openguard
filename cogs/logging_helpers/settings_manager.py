"""
Settings manager for PostgreSQL database storage.
Provides database-backed settings management for the logging system.
"""

import logging
from .postgresql_db import (
    get_setting,
    set_setting,
    setup_moderation_log_table,
)

log = logging.getLogger(__name__)


# Database initialization function
async def initialize_database():
    """Initializes the PostgreSQL database."""
    try:
        await setup_moderation_log_table()
        log.info("PostgreSQL database initialization complete.")
    except Exception as e:
        log.exception(f"Error initializing PostgreSQL database: {e}")


async def run_migrations():
    """Compatibility function for migrations - handled by database setup."""
    log.info("Database migrations handled by setup scripts.")


# Settings access functions


async def get_guild_prefix(guild_id: int, default_prefix: str) -> str:
    """Gets the command prefix for a guild."""
    try:
        prefix = await get_setting(guild_id, "prefix", default_prefix)
        return prefix if prefix is not None else default_prefix
    except Exception as e:
        log.exception(f"Error getting prefix for guild {guild_id}: {e}")
        return default_prefix


async def set_guild_prefix(guild_id: int, prefix: str) -> bool:
    """Sets the command prefix for a guild."""
    try:
        success = await set_setting(guild_id, "prefix", prefix)
        if success:
            log.info(f"Set prefix for guild {guild_id} to '{prefix}'")
        return success
    except Exception as e:
        log.exception(f"Error setting prefix for guild {guild_id}: {e}")
        return False


# Generic settings functions (re-exported from json_db)

# Mod log settings functions (re-exported from json_db)

# Logging webhook functions (re-exported from json_db)

# Log event toggle functions (re-exported from json_db)

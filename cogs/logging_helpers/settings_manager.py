"""
Settings manager for PostgreSQL database storage.
Provides database-backed settings management for the logging system.
"""

import logging
from typing import Optional, Dict

from .postgresql_db import (
    get_setting,
    set_setting,
    setup_moderation_log_table,
    get_logging_webhook as _get_logging_webhook,
    set_logging_webhook as _set_logging_webhook,
    is_log_event_enabled as _is_log_event_enabled,
    set_log_event_enabled as _set_log_event_enabled,
    get_all_log_event_toggles as _get_all_log_event_toggles,
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


async def get_setting_value(guild_id: int, key: str, default=None):
    """Wrapper around ``get_setting`` for backwards compatibility."""
    return await get_setting(guild_id, key, default)


async def set_setting_value(guild_id: int, key: str, value) -> bool:
    """Wrapper around ``set_setting`` for backwards compatibility."""
    return await set_setting(guild_id, key, value)


# Mod log settings functions (re-exported from json_db)


async def get_mod_log_channel_id(guild_id: int) -> Optional[int]:
    """Gets the mod log channel ID for a guild."""
    channel_id = await get_setting(guild_id, "mod_log_channel_id")
    return int(channel_id) if channel_id is not None else None


async def set_mod_log_channel_id(guild_id: int, channel_id: int) -> bool:
    """Sets the mod log channel ID for a guild."""
    return await set_setting(guild_id, "mod_log_channel_id", channel_id)


async def is_mod_log_enabled(guild_id: int, default: bool = False) -> bool:
    """Checks if mod logging is enabled for a guild."""
    enabled = await get_setting(guild_id, "mod_log_enabled", default)
    return bool(enabled)


async def set_mod_log_enabled(guild_id: int, enabled: bool) -> bool:
    """Sets the mod log enabled status for a guild."""
    return await set_setting(guild_id, "mod_log_enabled", enabled)


# Logging webhook functions (re-exported from json_db)


async def get_logging_webhook(guild_id: int) -> Optional[str]:
    """Gets the logging webhook URL for a guild."""
    return await _get_logging_webhook(guild_id)


async def set_logging_webhook(guild_id: int, webhook_url: Optional[str]) -> bool:
    """Sets the logging webhook URL for a guild."""
    return await _set_logging_webhook(guild_id, webhook_url)


# Log event toggle functions (re-exported from json_db)


async def is_log_event_enabled(guild_id: int, event_key: str, default_enabled: bool = True) -> bool:
    """Checks if a specific log event is enabled for a guild."""
    return await _is_log_event_enabled(guild_id, event_key, default_enabled)


async def set_log_event_enabled(guild_id: int, event_key: str, enabled: bool) -> bool:
    """Sets the enabled status for a specific log event in a guild."""
    return await _set_log_event_enabled(guild_id, event_key, enabled)


async def get_all_log_event_toggles(guild_id: int) -> Dict[str, bool]:
    """Gets all log event toggles for a guild."""
    return await _get_all_log_event_toggles(guild_id)

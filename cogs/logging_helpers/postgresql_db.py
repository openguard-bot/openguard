"""
PostgreSQL-based database abstraction layer for logging functionality.
Replaces the JSON-based version with PostgreSQL operations.
"""

# pylint: disable=no-member,function-redefined

import logging
from typing import Optional, List, Dict, Any

from database.operations import (
    add_mod_log_entry as db_add_mod_log,
    get_mod_log as db_get_mod_log,
    get_user_mod_logs as db_get_user_mod_logs,
    get_guild_mod_logs as db_get_guild_mod_logs,
    update_mod_log_reason as db_update_mod_log_reason,
    get_guild_setting,
    set_guild_setting,
    get_log_event_enabled as db_get_log_event_enabled,
    set_log_event_enabled as db_set_log_event_enabled,
    get_all_log_event_toggles as db_get_all_log_event_toggles,
)
from database.connection import initialize_database

log = logging.getLogger(__name__)

# Moderation Logs Functions


async def add_mod_log(
    guild_id: int,
    moderator_id: int,
    target_user_id: int,
    action_type: str,
    reason: Optional[str],
    duration_seconds: Optional[int] = None,
) -> Optional[int]:
    """Adds a new moderation log entry and returns the case_id."""
    try:
        return await db_add_mod_log(
            guild_id,
            moderator_id,
            target_user_id,
            action_type,
            reason,
            duration_seconds,
        )
    except Exception as e:
        log.error(f"Error adding moderation log: {e}")
        return None


async def get_mod_log(case_id: int) -> Optional[Dict[str, Any]]:
    """Gets a specific moderation log entry by case_id."""
    try:
        return await db_get_mod_log(case_id)
    except Exception as e:
        log.error(f"Error getting moderation log {case_id}: {e}")
        return None


async def get_user_mod_logs(guild_id: int, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Gets moderation logs for a specific user in a guild."""
    try:
        return await db_get_user_mod_logs(guild_id, user_id, limit)
    except Exception as e:
        log.error(f"Error getting user mod logs for user {user_id} in guild {guild_id}: {e}")
        return []


async def get_guild_mod_logs(guild_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Gets moderation logs for a guild."""
    try:
        return await db_get_guild_mod_logs(guild_id, limit)
    except Exception as e:
        log.error(f"Error getting guild mod logs for guild {guild_id}: {e}")
        return []


async def update_mod_log_reason(case_id: int, new_reason: str) -> bool:
    """Updates the reason for a specific moderation log entry."""
    try:
        return await db_update_mod_log_reason(case_id, new_reason)
    except Exception as e:
        log.error(f"Error updating mod log reason for case {case_id}: {e}")
        return False


async def update_mod_log_message_details(case_id: int, message_id: int, channel_id: int) -> bool:
    """Updates the message details for a moderation log entry."""
    try:
        from database.connection import execute_query

        await execute_query(
            "UPDATE moderation_logs SET message_id = $1, channel_id = $2 WHERE case_id = $3",
            message_id,
            channel_id,
            case_id,
        )
        return True
    except Exception as e:
        log.error(f"Error updating mod log message details for case {case_id}: {e}")
        return False


async def delete_mod_log(case_id: int) -> bool:
    """Deletes a moderation log entry."""
    try:
        from database.connection import delete_record

        return await delete_record("moderation_logs", "case_id = $1", case_id)
    except Exception as e:
        log.error(f"Error deleting mod log {case_id}: {e}")
        return False


async def clear_user_mod_logs(guild_id: int, user_id: int) -> bool:
    """Clears all moderation logs for a user in a guild."""
    try:
        from database.connection import delete_record

        return await delete_record(
            "moderation_logs",
            "guild_id = $1 AND target_user_id = $2",
            guild_id,
            user_id,
        )
    except Exception as e:
        log.error(f"Error clearing mod logs for user {user_id} in guild {guild_id}: {e}")
        return False


# Settings Management Functions


async def get_setting(guild_id: int, key: str, default=None):
    """Gets a specific setting for a guild."""
    try:
        return await get_guild_setting(guild_id, key, default)
    except Exception as e:
        log.error(f"Error getting setting '{key}' for guild {guild_id}: {e}")
        return default


async def set_setting(guild_id: int, key: str, value: Any) -> bool:
    """Sets a specific setting for a guild."""
    try:
        return await set_guild_setting(guild_id, key, value)
    except Exception as e:
        log.error(f"Error setting '{key}' for guild {guild_id}: {e}")
        return False


# Logging Webhook Functions


async def get_logging_webhook(guild_id: int) -> Optional[str]:
    """Gets the logging webhook URL for a guild."""
    try:
        return await get_setting(guild_id, "logging_webhook_url")
    except Exception as e:
        log.error(f"Error getting logging webhook for guild {guild_id}: {e}")
        return None


async def set_logging_webhook(guild_id: int, webhook_url: Optional[str]) -> bool:
    """Sets the logging webhook URL for a guild."""
    try:
        return await set_setting(guild_id, "logging_webhook_url", webhook_url)
    except Exception as e:
        log.error(f"Error setting logging webhook for guild {guild_id}: {e}")
        return False


# Log Event Toggle Functions


async def is_log_event_enabled(guild_id: int, event_key: str, default_enabled: bool = True) -> bool:
    """Checks if a specific log event is enabled for a guild."""
    try:
        return await db_get_log_event_enabled(guild_id, event_key, default_enabled)
    except Exception as e:
        log.error(f"Error checking log event '{event_key}' for guild {guild_id}: {e}")
        return default_enabled  # Use the provided default


async def set_log_event_enabled(guild_id: int, event_key: str, enabled: bool) -> bool:
    """Sets the enabled status for a specific log event in a guild."""
    try:
        return await db_set_log_event_enabled(guild_id, event_key, enabled)
    except Exception as e:
        log.error(f"Error setting log event '{event_key}' for guild {guild_id}: {e}")
        return False


async def get_all_log_event_toggles(guild_id: int) -> Dict[str, bool]:
    """Gets all log event toggles for a guild."""
    try:
        return await db_get_all_log_event_toggles(guild_id)
    except Exception as e:
        log.error(f"Error getting log event toggles for guild {guild_id}: {e}")
        return {}


# Database Setup Functions


async def setup_moderation_log_table():
    """Initializes the database tables and connections."""
    try:
        success = await initialize_database()
        if success:
            log.info("Successfully initialized PostgreSQL database.")
        else:
            log.error("Failed to initialize PostgreSQL database.")
        return success
    except Exception as e:
        log.error(f"Error setting up database: {e}")
        return False

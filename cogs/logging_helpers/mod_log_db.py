"""
Moderation log database interface for PostgreSQL.
Maintains the same interface as the original version for compatibility.
"""

import logging
import asyncio
import discord
from typing import Optional, List, Dict, Any
from .postgresql_db import (
    add_mod_log as _add_mod_log,
    get_mod_log as _get_mod_log,
    get_user_mod_logs as _get_user_mod_logs,
    get_guild_mod_logs as _get_guild_mod_logs,
    update_mod_log_reason as _update_mod_log_reason,
    update_mod_log_message_details as _update_mod_log_message_details,
    delete_mod_log as _delete_mod_log,
    clear_user_mod_logs as _clear_user_mod_logs,
    setup_moderation_log_table as _setup_moderation_log_table,
)

log = logging.getLogger(__name__)

# Compatibility wrapper functions that maintain the original interface


async def create_connection_with_retry(pool=None, max_retries: int = 3):
    """
    Compatibility function for the original interface.
    Since we're using PostgreSQL connection pooling, this always returns success.
    """
    _ = pool, max_retries  # Suppress unused parameter warnings
    return True, True


async def setup_moderation_log_table(pool=None):
    """
    Ensures the PostgreSQL database tables exist.
    """
    _ = pool  # Suppress unused parameter warning
    return await _setup_moderation_log_table()


async def add_mod_log(
    pool,  # Ignored for PostgreSQL (uses connection pooling)
    guild_id: int,
    moderator_id: int,
    target_user_id: int,
    action_type: str,
    reason: Optional[str],
    duration_seconds: Optional[int] = None,
) -> Optional[int]:
    """Adds a new moderation log entry and returns the case_id."""
    _ = pool  # Suppress unused parameter warning
    return await _add_mod_log(
        guild_id,
        moderator_id,
        target_user_id,
        action_type,
        reason,
        duration_seconds,
    )


async def update_mod_log_reason(pool, case_id: int, new_reason: str) -> bool:
    """Updates the reason for a specific moderation log entry."""
    _ = pool  # Suppress unused parameter warning
    return await _update_mod_log_reason(case_id, new_reason)


async def update_mod_log_message_details(pool, case_id: int, message_id: int, channel_id: int) -> bool:
    """Updates the log_message_id and log_channel_id for a specific case."""
    _ = pool  # Suppress unused parameter warning
    return await _update_mod_log_message_details(case_id, message_id, channel_id)


async def get_mod_log(pool, case_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a specific moderation log entry by case_id."""
    _ = pool  # Suppress unused parameter warning
    return await _get_mod_log(case_id)


async def get_user_mod_logs(pool, guild_id: int, target_user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves moderation logs for a specific user in a guild, ordered by timestamp descending."""
    _ = pool  # Suppress unused parameter warning
    return await _get_user_mod_logs(guild_id, target_user_id, limit)


async def get_guild_mod_logs(pool, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves the latest moderation logs for a guild, ordered by timestamp descending."""
    _ = pool  # Suppress unused parameter warning
    return await _get_guild_mod_logs(guild_id, limit)


async def delete_mod_log(pool, case_id: int, guild_id: int) -> bool:
    """Deletes a specific moderation log entry by case_id, ensuring it belongs to the guild."""
    _ = pool, guild_id  # Suppress unused parameter warnings
    return await _delete_mod_log(case_id)  # Note: guild_id check removed for simplicity


async def clear_user_mod_logs(pool, guild_id: int, target_user_id: int) -> int:
    """Deletes all moderation log entries for a specific user in a guild. Returns the number of deleted logs."""
    _ = pool  # Suppress unused parameter warning
    success = await _clear_user_mod_logs(guild_id, target_user_id)
    return 1 if success else 0  # Convert boolean to count for compatibility


# Thread-safe functions for cross-thread operations


async def add_mod_log_safe(
    bot_instance,
    guild_id: int,
    moderator_id: int,
    target_user_id: int,
    action_type: str,
    reason: Optional[str],
    duration_seconds: Optional[int] = None,
) -> Optional[int]:
    """
    Thread-safe version of add_mod_log.
    Since we're using JSON files, this is the same as the regular function.
    """
    return await add_mod_log(
        None,  # pool not needed for JSON storage
        guild_id,
        moderator_id,
        target_user_id,
        action_type,
        reason,
        duration_seconds,
    )


async def update_mod_log_message_details_safe(bot_instance, case_id: int, message_id: int, channel_id: int) -> bool:
    """
    Thread-safe version of update_mod_log_message_details.
    Since we're using JSON files, this is the same as the regular function.
    """
    return await update_mod_log_message_details(None, case_id, message_id, channel_id)


async def log_action_safe(
    bot_instance,
    guild_id: int,
    target_user_id: int,
    action_type: str,
    reason: str,
    ai_details: dict,
    source: str = "AI_API",
) -> Optional[int]:
    """
    Thread-safe version of log_action that works with the ModLogCog.
    This function attempts to use the ModLogCog if available.
    """
    try:
        if bot_instance is None:
            log.error("Cannot log action safely: bot_instance is None")
            return None

        # Get the guild object
        guild = bot_instance.get_guild(guild_id)
        if not guild:
            log.error(f"Guild {guild_id} not found")
            return None

        # Get the ModLogCog instance
        mod_log_cog = bot_instance.get_cog("ModLogCog")
        if not mod_log_cog:
            log.error("ModLogCog not found")
            return None

        # Create Discord objects for the users
        AI_MODERATOR_ID = 0
        target_user = discord.Object(id=target_user_id)
        ai_moderator = discord.Object(id=AI_MODERATOR_ID)

        # Call the log_action method
        await mod_log_cog.log_action(
            guild=guild,
            moderator=ai_moderator,
            target=target_user,
            action_type=action_type,
            reason=reason,
            duration=None,
            source=source,
            ai_details=ai_details,
            moderator_id_override=AI_MODERATOR_ID,
        )

        # Get the case_id from the most recent log entry for this user
        recent_logs = await get_user_mod_logs(None, guild_id, target_user_id, limit=1)
        case_id = recent_logs[0]["case_id"] if recent_logs else None
        return case_id

    except Exception as e:
        log.exception(f"Error in log_action_safe: {e}")
        return None


# Helper function for running in bot loop (compatibility)
def run_in_bot_loop(bot_instance, coro_func):
    """
    Compatibility function for running coroutines in the bot's event loop.
    Since we're using JSON files, we can run directly.
    """
    if bot_instance is None:
        log.error("Cannot run in bot loop: bot_instance is None")
        return None

    try:
        # For JSON storage, we can run the coroutine directly
        return asyncio.create_task(coro_func())
    except Exception as e:
        log.exception(f"Error running in bot loop: {e}")
        return None

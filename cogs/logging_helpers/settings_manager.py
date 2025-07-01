"""
Settings manager adapted for JSON file storage.
Provides the same interface as the PostgreSQL/Redis version but uses JSON files.
"""

import logging
from typing import Dict, Any, Optional
from .json_db import (
    get_setting,
    set_setting,
    get_mod_log_channel_id,
    set_mod_log_channel_id,
    is_mod_log_enabled,
    set_mod_log_enabled,
    get_logging_webhook,
    set_logging_webhook,
    is_log_event_enabled,
    set_log_event_enabled,
    get_all_log_event_toggles,
    setup_moderation_log_table,
)

log = logging.getLogger(__name__)

# Database initialization function
async def initialize_database():
    """Creates necessary JSON files if they don't exist."""
    try:
        await setup_moderation_log_table()
        log.info("JSON storage initialization complete.")
    except Exception as e:
        log.exception(f"Error initializing JSON storage: {e}")

async def run_migrations():
    """Compatibility function for migrations - no-op for JSON storage."""
    log.info("No migrations needed for JSON storage.")

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

# Starboard functions (simplified for this implementation)

async def get_starboard_settings(guild_id: int) -> Optional[Dict[str, Any]]:
    """Gets the starboard settings for a guild."""
    try:
        settings = await get_setting(guild_id, "starboard_settings")
        if settings is None:
            # Return default settings
            default_settings = {
                "enabled": True,
                "star_emoji": "⭐",
                "threshold": 3,
                "starboard_channel_id": None,
                "ignore_bots": True,
                "self_star": False,
            }
            await set_setting(guild_id, "starboard_settings", default_settings)
            return default_settings
        return settings
    except Exception as e:
        log.exception(f"Error getting starboard settings for guild {guild_id}: {e}")
        return None

async def update_starboard_settings(guild_id: int, **kwargs) -> bool:
    """Updates starboard settings for a guild."""
    try:
        current_settings = await get_starboard_settings(guild_id)
        if current_settings is None:
            current_settings = {}
        
        # Update with new values
        current_settings.update(kwargs)
        
        success = await set_setting(guild_id, "starboard_settings", current_settings)
        if success:
            log.info(f"Updated starboard settings for guild {guild_id}: {kwargs}")
        return success
    except Exception as e:
        log.exception(f"Error updating starboard settings for guild {guild_id}: {e}")
        return False

async def get_starboard_entry(guild_id: int, original_message_id: int) -> Optional[Dict[str, Any]]:
    """Gets a starboard entry for a specific message."""
    try:
        entries = await get_setting(guild_id, "starboard_entries", {})
        return entries.get(str(original_message_id))
    except Exception as e:
        log.exception(f"Error getting starboard entry for message {original_message_id} in guild {guild_id}: {e}")
        return None

async def create_starboard_entry(
    guild_id: int,
    original_message_id: int,
    original_channel_id: int,
    starboard_message_id: int,
    author_id: int,
    star_count: int = 1,
) -> bool:
    """Creates a new starboard entry."""
    try:
        entries = await get_setting(guild_id, "starboard_entries", {})
        
        entry = {
            "original_message_id": original_message_id,
            "original_channel_id": original_channel_id,
            "starboard_message_id": starboard_message_id,
            "author_id": author_id,
            "star_count": star_count,
        }
        
        entries[str(original_message_id)] = entry
        
        success = await set_setting(guild_id, "starboard_entries", entries)
        if success:
            log.info(f"Created starboard entry for message {original_message_id} in guild {guild_id}")
        return success
    except Exception as e:
        log.exception(f"Error creating starboard entry for message {original_message_id} in guild {guild_id}: {e}")
        return False

async def update_starboard_entry(
    guild_id: int, original_message_id: int, star_count: int
) -> bool:
    """Updates the star count for an existing starboard entry."""
    try:
        entries = await get_setting(guild_id, "starboard_entries", {})
        
        if str(original_message_id) in entries:
            entries[str(original_message_id)]["star_count"] = star_count
            success = await set_setting(guild_id, "starboard_entries", entries)
            if success:
                log.info(f"Updated star count to {star_count} for message {original_message_id} in guild {guild_id}")
            return success
        else:
            log.warning(f"Starboard entry not found for message {original_message_id} in guild {guild_id}")
            return False
    except Exception as e:
        log.exception(f"Error updating starboard entry for message {original_message_id} in guild {guild_id}: {e}")
        return False

async def delete_starboard_entry(guild_id: int, original_message_id: int) -> bool:
    """Deletes a starboard entry."""
    try:
        entries = await get_setting(guild_id, "starboard_entries", {})
        
        if str(original_message_id) in entries:
            del entries[str(original_message_id)]
            success = await set_setting(guild_id, "starboard_entries", entries)
            if success:
                log.info(f"Deleted starboard entry for message {original_message_id} in guild {guild_id}")
            return success
        else:
            log.warning(f"Starboard entry not found for message {original_message_id} in guild {guild_id}")
            return False
    except Exception as e:
        log.exception(f"Error deleting starboard entry for message {original_message_id} in guild {guild_id}: {e}")
        return False

async def clear_starboard_entries(guild_id: int) -> bool:
    """Clears all starboard entries for a guild."""
    try:
        success = await set_setting(guild_id, "starboard_entries", {})
        if success:
            log.info(f"Cleared all starboard entries for guild {guild_id}")
        return success
    except Exception as e:
        log.exception(f"Error clearing starboard entries for guild {guild_id}: {e}")
        return False

# Starboard reaction functions (simplified)

async def add_starboard_reaction(guild_id: int, message_id: int, user_id: int) -> int:
    """Records a user's star reaction to a message and returns the new count."""
    try:
        reactions = await get_setting(guild_id, "starboard_reactions", {})
        message_key = str(message_id)
        
        if message_key not in reactions:
            reactions[message_key] = []
        
        if user_id not in reactions[message_key]:
            reactions[message_key].append(user_id)
            await set_setting(guild_id, "starboard_reactions", reactions)
        
        return len(reactions[message_key])
    except Exception as e:
        log.exception(f"Error adding starboard reaction for message {message_id} in guild {guild_id}: {e}")
        return 0

async def remove_starboard_reaction(guild_id: int, message_id: int, user_id: int) -> int:
    """Removes a user's star reaction from a message and returns the new count."""
    try:
        reactions = await get_setting(guild_id, "starboard_reactions", {})
        message_key = str(message_id)
        
        if message_key in reactions and user_id in reactions[message_key]:
            reactions[message_key].remove(user_id)
            await set_setting(guild_id, "starboard_reactions", reactions)
        
        return len(reactions.get(message_key, []))
    except Exception as e:
        log.exception(f"Error removing starboard reaction for message {message_id} in guild {guild_id}: {e}")
        return 0

async def get_starboard_reaction_count(guild_id: int, message_id: int) -> int:
    """Gets the count of star reactions for a message."""
    try:
        reactions = await get_setting(guild_id, "starboard_reactions", {})
        message_key = str(message_id)
        return len(reactions.get(message_key, []))
    except Exception as e:
        log.exception(f"Error getting starboard reaction count for message {message_id} in guild {guild_id}: {e}")
        return 0

async def has_user_reacted(guild_id: int, message_id: int, user_id: int) -> bool:
    """Checks if a user has already reacted to a message."""
    try:
        reactions = await get_setting(guild_id, "starboard_reactions", {})
        message_key = str(message_id)
        return user_id in reactions.get(message_key, [])
    except Exception as e:
        log.exception(f"Error checking if user {user_id} reacted to message {message_id} in guild {guild_id}: {e}")
        return False

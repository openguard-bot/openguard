"""
JSON-based database abstraction layer for logging functionality.
Provides the same interface as the PostgreSQL version but uses JSON files for storage.
"""

import json
import os
import asyncio
import aiofiles
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
import uuid

log = logging.getLogger(__name__)

# Data directory for storing JSON files
DATA_DIR = os.path.join(os.getcwd(), "logging-data")
os.makedirs(DATA_DIR, exist_ok=True)

# File paths
MODERATION_LOGS_PATH = os.path.join(DATA_DIR, "moderation_logs.json")
GUILD_SETTINGS_PATH = os.path.join(DATA_DIR, "guild_settings.json")
LOG_EVENT_TOGGLES_PATH = os.path.join(DATA_DIR, "log_event_toggles.json")

# File locks for thread safety
_file_locks = {}


def get_file_lock(file_path: str) -> asyncio.Lock:
    """Get or create a lock for a specific file."""
    if file_path not in _file_locks:
        _file_locks[file_path] = asyncio.Lock()
    return _file_locks[file_path]


async def load_json_file(file_path: str, default_value: Any = None) -> Any:
    """Load data from a JSON file with error handling."""
    if not os.path.exists(file_path):
        if default_value is not None:
            await save_json_file(file_path, default_value)
            return default_value
        return {}

    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content) if content.strip() else (default_value or {})
    except Exception as e:
        log.error(f"Error loading JSON file {file_path}: {e}")
        return default_value or {}


async def save_json_file(file_path: str, data: Any) -> bool:
    """Save data to a JSON file with error handling."""
    try:
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=2, default=str))
        return True
    except Exception as e:
        log.error(f"Error saving JSON file {file_path}: {e}")
        return False


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
    lock = get_file_lock(MODERATION_LOGS_PATH)
    async with lock:
        try:
            logs = await load_json_file(MODERATION_LOGS_PATH, [])

            # Generate a new case_id
            case_id = max([log.get("case_id", 0) for log in logs], default=0) + 1

            new_log = {
                "case_id": case_id,
                "guild_id": guild_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "moderator_id": moderator_id,
                "target_user_id": target_user_id,
                "action_type": action_type,
                "reason": reason,
                "duration_seconds": duration_seconds,
                "log_message_id": None,
                "log_channel_id": None,
            }

            logs.append(new_log)

            if await save_json_file(MODERATION_LOGS_PATH, logs):
                log.info(
                    f"Added mod log entry for guild {guild_id}, action {action_type}. Case ID: {case_id}"
                )
                return case_id
            else:
                log.error(
                    f"Failed to save mod log entry for guild {guild_id}, action {action_type}"
                )
                return None

        except Exception as e:
            log.exception(f"Error adding mod log entry: {e}")
            return None


async def get_mod_log(case_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a specific moderation log entry by case_id."""
    try:
        logs = await load_json_file(MODERATION_LOGS_PATH, [])
        for log_entry in logs:
            if log_entry.get("case_id") == case_id:
                return log_entry
        return None
    except Exception as e:
        log.exception(f"Error retrieving mod log for case_id {case_id}: {e}")
        return None


async def get_user_mod_logs(
    guild_id: int, target_user_id: int, limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieves moderation logs for a specific user in a guild, ordered by timestamp descending."""
    try:
        logs = await load_json_file(MODERATION_LOGS_PATH, [])

        # Filter logs for the specific guild and user
        user_logs = [
            log_entry
            for log_entry in logs
            if log_entry.get("guild_id") == guild_id
            and log_entry.get("target_user_id") == target_user_id
        ]

        # Sort by timestamp descending
        user_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return user_logs[:limit]
    except Exception as e:
        log.exception(
            f"Error retrieving user mod logs for user {target_user_id} in guild {guild_id}: {e}"
        )
        return []


async def get_guild_mod_logs(guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves the latest moderation logs for a guild, ordered by timestamp descending."""
    try:
        logs = await load_json_file(MODERATION_LOGS_PATH, [])

        # Filter logs for the specific guild
        guild_logs = [
            log_entry for log_entry in logs if log_entry.get("guild_id") == guild_id
        ]

        # Sort by timestamp descending
        guild_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return guild_logs[:limit]
    except Exception as e:
        log.exception(f"Error retrieving guild mod logs for guild {guild_id}: {e}")
        return []


async def update_mod_log_reason(case_id: int, new_reason: str) -> bool:
    """Updates the reason for a specific moderation log entry."""
    lock = get_file_lock(MODERATION_LOGS_PATH)
    async with lock:
        try:
            logs = await load_json_file(MODERATION_LOGS_PATH, [])

            for log_entry in logs:
                if log_entry.get("case_id") == case_id:
                    log_entry["reason"] = new_reason
                    if await save_json_file(MODERATION_LOGS_PATH, logs):
                        log.info(f"Updated reason for case_id {case_id}")
                        return True
                    else:
                        log.error(
                            f"Failed to save updated reason for case_id {case_id}"
                        )
                        return False

            log.warning(f"Could not find case_id {case_id} to update reason")
            return False

        except Exception as e:
            log.exception(f"Error updating mod log reason for case_id {case_id}: {e}")
            return False


async def update_mod_log_message_details(
    case_id: int, message_id: int, channel_id: int
) -> bool:
    """Updates the log_message_id and log_channel_id for a specific case."""
    lock = get_file_lock(MODERATION_LOGS_PATH)
    async with lock:
        try:
            logs = await load_json_file(MODERATION_LOGS_PATH, [])

            for log_entry in logs:
                if log_entry.get("case_id") == case_id:
                    log_entry["log_message_id"] = message_id
                    log_entry["log_channel_id"] = channel_id
                    if await save_json_file(MODERATION_LOGS_PATH, logs):
                        log.info(f"Updated message details for case_id {case_id}")
                        return True
                    else:
                        log.error(
                            f"Failed to save message details for case_id {case_id}"
                        )
                        return False

            log.warning(f"Could not find case_id {case_id} to update message details")
            return False

        except Exception as e:
            log.exception(
                f"Error updating mod log message details for case_id {case_id}: {e}"
            )
            return False


async def delete_mod_log(case_id: int, guild_id: int) -> bool:
    """Deletes a specific moderation log entry by case_id, ensuring it belongs to the guild."""
    lock = get_file_lock(MODERATION_LOGS_PATH)
    async with lock:
        try:
            logs = await load_json_file(MODERATION_LOGS_PATH, [])

            original_count = len(logs)
            logs = [
                log_entry
                for log_entry in logs
                if not (
                    log_entry.get("case_id") == case_id
                    and log_entry.get("guild_id") == guild_id
                )
            ]

            if len(logs) < original_count:
                if await save_json_file(MODERATION_LOGS_PATH, logs):
                    log.info(
                        f"Deleted mod log entry for case_id {case_id} in guild {guild_id}"
                    )
                    return True
                else:
                    log.error(f"Failed to save after deleting case_id {case_id}")
                    return False
            else:
                log.warning(
                    f"Could not find case_id {case_id} in guild {guild_id} to delete"
                )
                return False

        except Exception as e:
            log.exception(
                f"Error deleting mod log entry for case_id {case_id} in guild {guild_id}: {e}"
            )
            return False


async def clear_user_mod_logs(guild_id: int, target_user_id: int) -> int:
    """Deletes all moderation log entries for a specific user in a guild. Returns the number of deleted logs."""
    lock = get_file_lock(MODERATION_LOGS_PATH)
    async with lock:
        try:
            logs = await load_json_file(MODERATION_LOGS_PATH, [])

            original_count = len(logs)
            logs = [
                log_entry
                for log_entry in logs
                if not (
                    log_entry.get("guild_id") == guild_id
                    and log_entry.get("target_user_id") == target_user_id
                )
            ]

            deleted_count = original_count - len(logs)

            if deleted_count > 0:
                if await save_json_file(MODERATION_LOGS_PATH, logs):
                    log.info(
                        f"Cleared {deleted_count} mod log entries for user {target_user_id} in guild {guild_id}"
                    )
                    return deleted_count
                else:
                    log.error(
                        f"Failed to save after clearing logs for user {target_user_id}"
                    )
                    return 0
            else:
                log.info(
                    f"No mod log entries found to clear for user {target_user_id} in guild {guild_id}"
                )
                return 0

        except Exception as e:
            log.exception(
                f"Error clearing mod log entries for user {target_user_id} in guild {guild_id}: {e}"
            )
            return 0


# Settings Management Functions


async def get_setting(guild_id: int, key: str, default=None):
    """Gets a specific setting for a guild."""
    try:
        settings = await load_json_file(GUILD_SETTINGS_PATH, {})
        guild_str = str(guild_id)

        if guild_str in settings and key in settings[guild_str]:
            return settings[guild_str][key]
        return default
    except Exception as e:
        log.exception(f"Error getting setting '{key}' for guild {guild_id}: {e}")
        return default


async def set_setting(guild_id: int, key: str, value: Any) -> bool:
    """Sets a specific setting for a guild."""
    lock = get_file_lock(GUILD_SETTINGS_PATH)
    async with lock:
        try:
            settings = await load_json_file(GUILD_SETTINGS_PATH, {})
            guild_str = str(guild_id)

            if guild_str not in settings:
                settings[guild_str] = {}

            settings[guild_str][key] = value

            if await save_json_file(GUILD_SETTINGS_PATH, settings):
                log.info(f"Set setting '{key}' for guild {guild_id} to '{value}'")
                return True
            else:
                log.error(f"Failed to save setting '{key}' for guild {guild_id}")
                return False

        except Exception as e:
            log.exception(f"Error setting '{key}' for guild {guild_id}: {e}")
            return False


# Mod Log Settings Functions


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


# Logging Webhook Functions


async def get_logging_webhook(guild_id: int) -> Optional[str]:
    """Gets the logging webhook URL for a guild."""
    return await get_setting(guild_id, "logging_webhook_url")


async def set_logging_webhook(guild_id: int, webhook_url: Optional[str]) -> bool:
    """Sets the logging webhook URL for a guild."""
    return await set_setting(guild_id, "logging_webhook_url", webhook_url)


# Log Event Toggle Functions


async def is_log_event_enabled(
    guild_id: int, event_key: str, default_enabled: bool = True
) -> bool:
    """Checks if a specific log event is enabled for a guild."""
    try:
        toggles = await load_json_file(LOG_EVENT_TOGGLES_PATH, {})
        guild_str = str(guild_id)

        if guild_str in toggles and event_key in toggles[guild_str]:
            return bool(toggles[guild_str][event_key])
        return default_enabled
    except Exception as e:
        log.exception(
            f"Error checking if event '{event_key}' is enabled for guild {guild_id}: {e}"
        )
        return default_enabled


async def set_log_event_enabled(guild_id: int, event_key: str, enabled: bool) -> bool:
    """Sets the enabled status for a specific log event in a guild."""
    lock = get_file_lock(LOG_EVENT_TOGGLES_PATH)
    async with lock:
        try:
            toggles = await load_json_file(LOG_EVENT_TOGGLES_PATH, {})
            guild_str = str(guild_id)

            if guild_str not in toggles:
                toggles[guild_str] = {}

            toggles[guild_str][event_key] = enabled

            if await save_json_file(LOG_EVENT_TOGGLES_PATH, toggles):
                log.info(
                    f"Set event '{event_key}' enabled status to {enabled} for guild {guild_id}"
                )
                return True
            else:
                log.error(
                    f"Failed to save event toggle for '{event_key}' in guild {guild_id}"
                )
                return False

        except Exception as e:
            log.exception(
                f"Error setting event '{event_key}' enabled status for guild {guild_id}: {e}"
            )
            return False


async def get_all_log_event_toggles(guild_id: int) -> Dict[str, bool]:
    """Gets all log event toggles for a guild."""
    try:
        toggles = await load_json_file(LOG_EVENT_TOGGLES_PATH, {})
        guild_str = str(guild_id)

        if guild_str in toggles:
            return toggles[guild_str]
        return {}
    except Exception as e:
        log.exception(f"Error getting all event toggles for guild {guild_id}: {e}")
        return {}


# Compatibility functions for the original interface


async def setup_moderation_log_table():
    """Compatibility function - creates necessary directories and files."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)

        # Initialize files if they don't exist
        await load_json_file(MODERATION_LOGS_PATH, [])
        await load_json_file(GUILD_SETTINGS_PATH, {})
        await load_json_file(LOG_EVENT_TOGGLES_PATH, {})

        log.info("Successfully ensured JSON storage files exist.")
        return True
    except Exception as e:
        log.exception(f"Error setting up JSON storage: {e}")
        return False


# Thread-safe helper functions for cross-thread operations


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
        guild_id,
        moderator_id,
        target_user_id,
        action_type,
        reason,
        duration_seconds,
    )


async def update_mod_log_message_details_safe(
    bot_instance, case_id: int, message_id: int, channel_id: int
) -> bool:
    """
    Thread-safe version of update_mod_log_message_details.
    Since we're using JSON files, this is the same as the regular function.
    """
    return await update_mod_log_message_details(case_id, message_id, channel_id)

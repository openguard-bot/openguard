"""
Database operations for the Discord bot.
This module provides high-level database operations that replace the JSON file operations.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union

from .connection import execute_query, get_connection, get_transaction, insert_or_update, delete_record, count_records
from .models import (
    GuildConfig, UserInfraction, Appeal, GlobalBan, ModerationLog,
    GuildSetting, LogEventToggle, BotDetectConfig, UserData, AppealStatus
)

log = logging.getLogger(__name__)


# Guild Configuration Operations

async def get_guild_config(guild_id: int, key: str, default=None):
    """Get a guild configuration value."""
    try:
        result = await execute_query(
            "SELECT value FROM guild_config WHERE guild_id = $1 AND key = $2",
            guild_id, key, fetch_one=True
        )
        if result:
            value = result['value']
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        return default
    except Exception as e:
        log.error(f"Failed to get guild config {key} for guild {guild_id}: {e}")
        return default


async def set_guild_config(guild_id: int, key: str, value: Any) -> bool:
    """Set a guild configuration value."""
    try:
        # Always convert to JSON for JSONB storage
        json_value = json.dumps(value)
        data = {
            'guild_id': guild_id,
            'key': key,
            'value': json_value
        }
        return await insert_or_update('guild_config', ['guild_id', 'key'], data)
    except Exception as e:
        log.error(f"Failed to set guild config {key} for guild {guild_id}: {e}")
        return False


async def get_all_guild_config(guild_id: int) -> Dict[str, Any]:
    """Get all configuration for a guild."""
    try:
        results = await execute_query(
            "SELECT key, value FROM guild_config WHERE guild_id = $1",
            guild_id, fetch_all=True
        )
        config = {}
        for row in results:
            value = row['value']
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    config[row['key']] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    config[row['key']] = value
            else:
                config[row['key']] = value
        return config
    except Exception as e:
        log.error(f"Failed to get all guild config for guild {guild_id}: {e}")
        return {}


# User Infractions Operations

async def add_user_infraction(guild_id: int, user_id: int, timestamp: datetime, 
                            rule_violated: Optional[str], action_taken: str, 
                            reasoning: Optional[str]) -> Optional[int]:
    """Add a user infraction and return the ID."""
    try:
        result = await execute_query(
            """INSERT INTO user_infractions (guild_id, user_id, timestamp, rule_violated, action_taken, reasoning)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            guild_id, user_id, timestamp, rule_violated, action_taken, reasoning,
            fetch_one=True
        )
        return result['id'] if result else None
    except Exception as e:
        log.error(f"Failed to add user infraction: {e}")
        return None


async def get_user_infractions(guild_id: int, user_id: int) -> List[Dict[str, Any]]:
    """Get all infractions for a user in a guild."""
    try:
        results = await execute_query(
            """SELECT id, timestamp, rule_violated, action_taken, reasoning, created_at
               FROM user_infractions 
               WHERE guild_id = $1 AND user_id = $2 
               ORDER BY timestamp DESC""",
            guild_id, user_id, fetch_all=True
        )
        return [dict(row) for row in results]
    except Exception as e:
        log.error(f"Failed to get user infractions for user {user_id} in guild {guild_id}: {e}")
        return []


async def clear_user_infractions(guild_id: int, user_id: int) -> bool:
    """Clear all infractions for a user in a guild."""
    try:
        return await delete_record(
            'user_infractions',
            'guild_id = $1 AND user_id = $2',
            guild_id, user_id
        )
    except Exception as e:
        log.error(f"Failed to clear user infractions for user {user_id} in guild {guild_id}: {e}")
        return False


# Appeals Operations

async def create_appeal(user_id: int, reason: str, original_infraction: Dict[str, Any]) -> Optional[str]:
    """Create a new appeal and return the appeal ID."""
    try:
        appeal_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        await execute_query(
            """INSERT INTO appeals (appeal_id, user_id, reason, timestamp, status, original_infraction)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            appeal_id, user_id, reason, timestamp, AppealStatus.PENDING.value, json.dumps(original_infraction)
        )
        return appeal_id
    except Exception as e:
        log.error(f"Failed to create appeal: {e}")
        return None


async def get_appeal(appeal_id: str) -> Optional[Dict[str, Any]]:
    """Get an appeal by ID."""
    try:
        result = await execute_query(
            """SELECT appeal_id, user_id, reason, timestamp, status, original_infraction, created_at, updated_at
               FROM appeals WHERE appeal_id = $1""",
            appeal_id, fetch_one=True
        )
        if result:
            appeal_data = dict(result)
            if appeal_data['original_infraction']:
                appeal_data['original_infraction'] = json.loads(appeal_data['original_infraction'])
            return appeal_data
        return None
    except Exception as e:
        log.error(f"Failed to get appeal {appeal_id}: {e}")
        return None


async def update_appeal_status(appeal_id: str, status: str) -> bool:
    """Update the status of an appeal."""
    try:
        await execute_query(
            "UPDATE appeals SET status = $1 WHERE appeal_id = $2",
            status, appeal_id
        )
        return True
    except Exception as e:
        log.error(f"Failed to update appeal status for {appeal_id}: {e}")
        return False


async def get_user_appeals(user_id: int) -> List[Dict[str, Any]]:
    """Get all appeals for a user."""
    try:
        results = await execute_query(
            """SELECT appeal_id, user_id, reason, timestamp, status, original_infraction, created_at, updated_at
               FROM appeals WHERE user_id = $1 ORDER BY timestamp DESC""",
            user_id, fetch_all=True
        )
        appeals = []
        for row in results:
            appeal_data = dict(row)
            if appeal_data['original_infraction']:
                appeal_data['original_infraction'] = json.loads(appeal_data['original_infraction'])
            appeals.append(appeal_data)
        return appeals
    except Exception as e:
        log.error(f"Failed to get appeals for user {user_id}: {e}")
        return []


# Global Bans Operations

async def add_global_ban(user_id: int, reason: Optional[str] = None, banned_by: Optional[int] = None) -> bool:
    """Add a user to the global ban list."""
    try:
        await execute_query(
            "INSERT INTO global_bans (user_id, reason, banned_by) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING",
            user_id, reason, banned_by
        )
        return True
    except Exception as e:
        log.error(f"Failed to add global ban for user {user_id}: {e}")
        return False


async def remove_global_ban(user_id: int) -> bool:
    """Remove a user from the global ban list."""
    try:
        return await delete_record('global_bans', 'user_id = $1', user_id)
    except Exception as e:
        log.error(f"Failed to remove global ban for user {user_id}: {e}")
        return False


async def is_globally_banned(user_id: int) -> bool:
    """Check if a user is globally banned."""
    try:
        result = await execute_query(
            "SELECT 1 FROM global_bans WHERE user_id = $1",
            user_id, fetch_one=True
        )
        return result is not None
    except Exception as e:
        log.error(f"Failed to check global ban status for user {user_id}: {e}")
        return False


async def get_all_global_bans() -> List[int]:
    """Get all globally banned user IDs."""
    try:
        results = await execute_query(
            "SELECT user_id FROM global_bans ORDER BY banned_at DESC",
            fetch_all=True
        )
        return [row['user_id'] for row in results]
    except Exception as e:
        log.error(f"Failed to get global bans: {e}")
        return []


# Moderation Logs Operations

async def add_mod_log(guild_id: int, moderator_id: int, target_user_id: int, 
                     action_type: str, reason: Optional[str], 
                     duration_seconds: Optional[int] = None) -> Optional[int]:
    """Add a moderation log entry and return the case ID."""
    try:
        result = await execute_query(
            """INSERT INTO moderation_logs (guild_id, moderator_id, target_user_id, action_type, reason, duration_seconds)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING case_id""",
            guild_id, moderator_id, target_user_id, action_type, reason, duration_seconds,
            fetch_one=True
        )
        return result['case_id'] if result else None
    except Exception as e:
        log.error(f"Failed to add moderation log: {e}")
        return None


async def get_mod_log(case_id: int) -> Optional[Dict[str, Any]]:
    """Get a moderation log by case ID."""
    try:
        result = await execute_query(
            """SELECT case_id, guild_id, moderator_id, target_user_id, action_type, reason, 
                      duration_seconds, timestamp, message_id, channel_id
               FROM moderation_logs WHERE case_id = $1""",
            case_id, fetch_one=True
        )
        return dict(result) if result else None
    except Exception as e:
        log.error(f"Failed to get moderation log {case_id}: {e}")
        return None


async def update_mod_log_reason(case_id: int, new_reason: str) -> bool:
    """Update the reason for a moderation log entry."""
    try:
        await execute_query(
            "UPDATE moderation_logs SET reason = $1 WHERE case_id = $2",
            new_reason, case_id
        )
        return True
    except Exception as e:
        log.error(f"Failed to update mod log reason for case {case_id}: {e}")
        return False


async def get_user_mod_logs(guild_id: int, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Get moderation logs for a specific user."""
    try:
        results = await execute_query(
            """SELECT case_id, guild_id, moderator_id, target_user_id, action_type, reason, 
                      duration_seconds, timestamp, message_id, channel_id
               FROM moderation_logs 
               WHERE guild_id = $1 AND target_user_id = $2 
               ORDER BY timestamp DESC LIMIT $3""",
            guild_id, user_id, limit, fetch_all=True
        )
        return [dict(row) for row in results]
    except Exception as e:
        log.error(f"Failed to get mod logs for user {user_id} in guild {guild_id}: {e}")
        return []


async def get_guild_mod_logs(guild_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Get moderation logs for a guild."""
    try:
        results = await execute_query(
            """SELECT case_id, guild_id, moderator_id, target_user_id, action_type, reason, 
                      duration_seconds, timestamp, message_id, channel_id
               FROM moderation_logs 
               WHERE guild_id = $1 
               ORDER BY timestamp DESC LIMIT $2""",
            guild_id, limit, fetch_all=True
        )
        return [dict(row) for row in results]
    except Exception as e:
        log.error(f"Failed to get mod logs for guild {guild_id}: {e}")
        return []


# Guild Settings Operations (for logging system)

async def get_guild_setting(guild_id: int, key: str, default=None):
    """Get a guild setting value."""
    try:
        result = await execute_query(
            "SELECT value FROM guild_settings WHERE guild_id = $1 AND key = $2",
            guild_id, key, fetch_one=True
        )
        if result:
            value = result['value']
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        return default
    except Exception as e:
        log.error(f"Failed to get guild setting {key} for guild {guild_id}: {e}")
        return default


async def set_guild_setting(guild_id: int, key: str, value: Any) -> bool:
    """Set a guild setting value."""
    try:
        # Always convert to JSON for JSONB storage
        json_value = json.dumps(value)
        data = {
            'guild_id': guild_id,
            'key': key,
            'value': json_value
        }
        return await insert_or_update('guild_settings', ['guild_id', 'key'], data)
    except Exception as e:
        log.error(f"Failed to set guild setting {key} for guild {guild_id}: {e}")
        return False


# Log Event Toggles Operations

async def get_log_event_enabled(guild_id: int, event_key: str, default_enabled: bool = True) -> bool:
    """Check if a log event is enabled for a guild."""
    try:
        result = await execute_query(
            "SELECT enabled FROM log_event_toggles WHERE guild_id = $1 AND event_key = $2",
            guild_id, event_key, fetch_one=True
        )
        return result['enabled'] if result else default_enabled  # Use provided default
    except Exception as e:
        log.error(f"Failed to get log event status for {event_key} in guild {guild_id}: {e}")
        return default_enabled


async def set_log_event_enabled(guild_id: int, event_key: str, enabled: bool) -> bool:
    """Set the enabled status for a log event."""
    try:
        data = {
            'guild_id': guild_id,
            'event_key': event_key,
            'enabled': enabled
        }
        return await insert_or_update('log_event_toggles', ['guild_id', 'event_key'], data)
    except Exception as e:
        log.error(f"Failed to set log event status for {event_key} in guild {guild_id}: {e}")
        return False


async def get_all_log_event_toggles(guild_id: int) -> Dict[str, bool]:
    """Get all log event toggles for a guild."""
    try:
        results = await execute_query(
            "SELECT event_key, enabled FROM log_event_toggles WHERE guild_id = $1",
            guild_id, fetch_all=True
        )
        return {row['event_key']: row['enabled'] for row in results}
    except Exception as e:
        log.error(f"Failed to get log event toggles for guild {guild_id}: {e}")
        return {}


# Bot Detection Configuration Operations

async def get_botdetect_config(guild_id: int, key: str, default=None):
    """Get a bot detection configuration value."""
    try:
        result = await execute_query(
            "SELECT value FROM botdetect_config WHERE guild_id = $1 AND key = $2",
            guild_id, key, fetch_one=True
        )
        if result:
            value = result['value']
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        return default
    except Exception as e:
        log.error(f"Failed to get botdetect config {key} for guild {guild_id}: {e}")
        return default


async def set_botdetect_config(guild_id: int, key: str, value: Any) -> bool:
    """Set a bot detection configuration value."""
    try:
        # Always convert to JSON for JSONB storage
        json_value = json.dumps(value)
        data = {
            'guild_id': guild_id,
            'key': key,
            'value': json_value
        }
        return await insert_or_update('botdetect_config', ['guild_id', 'key'], data)
    except Exception as e:
        log.error(f"Failed to set botdetect config {key} for guild {guild_id}: {e}")
        return False


async def get_all_botdetect_config(guild_id: int) -> Dict[str, Any]:
    """Get all bot detection configuration for a guild."""
    try:
        results = await execute_query(
            "SELECT key, value FROM botdetect_config WHERE guild_id = $1",
            guild_id, fetch_all=True
        )
        config = {}
        for row in results:
            value = row['value']
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    config[row['key']] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    config[row['key']] = value
            else:
                config[row['key']] = value
        return config
    except Exception as e:
        log.error(f"Failed to get botdetect config for guild {guild_id}: {e}")
        return {}


# User Data Operations (for abtuser.py)

async def get_user_data(user_id: int) -> Dict[str, Any]:
    """Get custom user data."""
    try:
        result = await execute_query(
            "SELECT data FROM user_data WHERE user_id = $1",
            user_id, fetch_one=True
        )
        if result and result['data']:
            return json.loads(result['data']) if isinstance(result['data'], str) else result['data']
        return {}
    except Exception as e:
        log.error(f"Failed to get user data for user {user_id}: {e}")
        return {}


async def set_user_data(user_id: int, data: Dict[str, Any]) -> bool:
    """Set custom user data."""
    try:
        user_data = {
            'user_id': user_id,
            'data': json.dumps(data)
        }
        return await insert_or_update('user_data', ['user_id'], user_data)
    except Exception as e:
        log.error(f"Failed to set user data for user {user_id}: {e}")
        return False


async def update_user_data_field(user_id: int, field: str, value: Any) -> bool:
    """Update a specific field in user data."""
    try:
        current_data = await get_user_data(user_id)
        current_data[field] = value
        return await set_user_data(user_id, current_data)
    except Exception as e:
        log.error(f"Failed to update user data field {field} for user {user_id}: {e}")
        return False


async def delete_user_data(user_id: int) -> bool:
    """Delete all custom user data."""
    try:
        return await delete_record('user_data', 'user_id = $1', user_id)
    except Exception as e:
        log.error(f"Failed to delete user data for user {user_id}: {e}")
        return False

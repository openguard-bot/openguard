"""
Database operations for the Discord bot.
This module provides high-level database operations that replace the JSON file operations.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from cryptography.fernet import Fernet
from os import getenv

from .cache import delete_cache, get_cache, set_cache

from .connection import (
    execute_query,
    insert_or_update,
    delete_record,
)
from .models import (
    GuildAPIKey,
    AppealStatus,
    CaptchaConfig,
    CaptchaAttempt,
)

log = logging.getLogger(__name__)

# Encryption setup
ENCRYPTION_KEY = getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable not set.")
fernet = Fernet(ENCRYPTION_KEY.encode())


def encrypt_data(data: str) -> str:
    """Encrypts a string."""
    return fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypts a string."""
    return fernet.decrypt(encrypted_data.encode()).decode()


# Guild Configuration Operations


async def get_guild_config(guild_id: int, key: str, default=None):
    """Get a guild configuration value."""
    cache_key = f"guild_config:{guild_id}:{key}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        result = await execute_query(
            "SELECT value FROM guild_config WHERE guild_id = $1 AND key = $2",
            guild_id,
            key,
            fetch_one=True,
        )
        if result:
            value = result["value"]
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
            await set_cache(cache_key, value)
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
            "guild_id": guild_id,
            "key": key,
            "value": json_value,
        }
        success = await insert_or_update("guild_config", ["guild_id", "key"], data)
        if success:
            await set_cache(f"guild_config:{guild_id}:{key}", value)
        return success
    except Exception as e:
        log.error(f"Failed to set guild config {key} for guild {guild_id}: {e}")
        return False


async def get_all_guild_config(guild_id: int) -> Dict[str, Any]:
    """Get all configuration for a guild."""
    try:
        results = await execute_query(
            "SELECT key, value FROM guild_config WHERE guild_id = $1",
            guild_id,
            fetch_all=True,
        )
        config = {}
        for row in results:
            value = row["value"]
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    config[row["key"]] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    config[row["key"]] = value
            else:
                config[row["key"]] = value
        return config
    except Exception as e:
        log.error(f"Failed to get all guild config for guild {guild_id}: {e}")
        return {}


# User Infractions Operations


async def add_user_infraction(
    guild_id: int,
    user_id: int,
    timestamp: datetime,
    rule_violated: Optional[str],
    action_taken: str,
    reasoning: Optional[str],
) -> Optional[int]:
    """Add a user infraction and return the ID."""
    try:
        result = await execute_query(
            """INSERT INTO user_infractions (guild_id, user_id, timestamp, rule_violated, action_taken, reasoning)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            guild_id,
            user_id,
            timestamp,
            rule_violated,
            action_taken,
            reasoning,
            fetch_one=True,
        )
        return result["id"] if result else None
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
            guild_id,
            user_id,
            fetch_all=True,
        )
        return [dict(row) for row in results]
    except Exception as e:
        log.error(f"Failed to get user infractions for user {user_id} in guild {guild_id}: {e}")
        return []


async def clear_user_infractions(guild_id: int, user_id: int) -> bool:
    """Clear all infractions for a user in a guild."""
    try:
        return await delete_record("user_infractions", "guild_id = $1 AND user_id = $2", guild_id, user_id)
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
            appeal_id,
            user_id,
            reason,
            timestamp,
            AppealStatus.PENDING.value,
            json.dumps(original_infraction),
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
            appeal_id,
            fetch_one=True,
        )
        if result:
            appeal_data = dict(result)
            if appeal_data["original_infraction"]:
                appeal_data["original_infraction"] = json.loads(appeal_data["original_infraction"])
            return appeal_data
        return None
    except Exception as e:
        log.error(f"Failed to get appeal {appeal_id}: {e}")
        return None


async def update_appeal_status(appeal_id: str, status: str) -> bool:
    """Update the status of an appeal."""
    try:
        await execute_query("UPDATE appeals SET status = $1 WHERE appeal_id = $2", status, appeal_id)
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
            user_id,
            fetch_all=True,
        )
        appeals = []
        for row in results:
            appeal_data = dict(row)
            if appeal_data["original_infraction"]:
                appeal_data["original_infraction"] = json.loads(appeal_data["original_infraction"])
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
            user_id,
            reason,
            banned_by,
        )
        return True
    except Exception as e:
        log.error(f"Failed to add global ban for user {user_id}: {e}")
        return False


async def remove_global_ban(user_id: int) -> bool:
    """Remove a user from the global ban list."""
    try:
        return await delete_record("global_bans", "user_id = $1", user_id)
    except Exception as e:
        log.error(f"Failed to remove global ban for user {user_id}: {e}")
        return False


async def is_globally_banned(user_id: int) -> bool:
    """Check if a user is globally banned."""
    try:
        result = await execute_query("SELECT 1 FROM global_bans WHERE user_id = $1", user_id, fetch_one=True)
        return result is not None
    except Exception as e:
        log.error(f"Failed to check global ban status for user {user_id}: {e}")
        return False


async def get_all_global_bans() -> List[int]:
    """Get all globally banned user IDs."""
    try:
        results = await execute_query("SELECT user_id FROM global_bans ORDER BY banned_at DESC", fetch_all=True)
        return [row["user_id"] for row in results]
    except Exception as e:
        log.error(f"Failed to get global bans: {e}")
        return []


# Moderation Logs Operations


async def add_mod_log_entry(
    guild_id: int,
    moderator_id: int,
    target_user_id: int,
    action_type: str,
    reason: Optional[str],
    duration_seconds: Optional[int] = None,
) -> Optional[int]:
    """Add a moderation log entry and return the case ID."""
    try:
        result = await execute_query(
            """INSERT INTO moderation_logs (guild_id, moderator_id, target_user_id, action_type, reason, duration_seconds)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING case_id""",
            guild_id,
            moderator_id,
            target_user_id,
            action_type,
            reason,
            duration_seconds,
            fetch_one=True,
        )
        return result["case_id"] if result else None
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
            case_id,
            fetch_one=True,
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
            new_reason,
            case_id,
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
            guild_id,
            user_id,
            limit,
            fetch_all=True,
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
            guild_id,
            limit,
            fetch_all=True,
        )
        return [dict(row) for row in results]
    except Exception as e:
        log.error(f"Failed to get mod logs for guild {guild_id}: {e}")
        return []


# Guild Settings Operations (for logging system)


async def get_guild_setting(guild_id: int, key: str, default=None):
    """Get a guild setting value."""
    cache_key = f"guild_setting:{guild_id}:{key}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        result = await execute_query(
            "SELECT value FROM guild_settings WHERE guild_id = $1 AND key = $2",
            guild_id,
            key,
            fetch_one=True,
        )
        if result:
            value = result["value"]
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
            await set_cache(cache_key, value)
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
            "guild_id": guild_id,
            "key": key,
            "value": json_value,
        }
        success = await insert_or_update("guild_settings", ["guild_id", "key"], data)
        if success:
            await set_cache(f"guild_setting:{guild_id}:{key}", value)
        return success
    except Exception as e:
        log.error(f"Failed to set guild setting {key} for guild {guild_id}: {e}")
        return False


# Log Event Toggles Operations


async def get_log_event_enabled(guild_id: int, event_key: str, default_enabled: bool = True) -> bool:
    """Check if a log event is enabled for a guild."""
    try:
        result = await execute_query(
            "SELECT enabled FROM log_event_toggles WHERE guild_id = $1 AND event_key = $2",
            guild_id,
            event_key,
            fetch_one=True,
        )
        return result["enabled"] if result else default_enabled  # Use provided default
    except Exception as e:
        log.error(f"Failed to get log event status for {event_key} in guild {guild_id}: {e}")
        return default_enabled


async def set_log_event_enabled(guild_id: int, event_key: str, enabled: bool) -> bool:
    """Set the enabled status for a log event."""
    try:
        data = {"guild_id": guild_id, "event_key": event_key, "enabled": enabled}
        return await insert_or_update("log_event_toggles", ["guild_id", "event_key"], data)
    except Exception as e:
        log.error(f"Failed to set log event status for {event_key} in guild {guild_id}: {e}")
        return False


async def get_all_log_event_toggles(guild_id: int) -> Dict[str, bool]:
    """Get all log event toggles for a guild."""
    try:
        results = await execute_query(
            "SELECT event_key, enabled FROM log_event_toggles WHERE guild_id = $1",
            guild_id,
            fetch_all=True,
        )
        return {row["event_key"]: row["enabled"] for row in results}
    except Exception as e:
        log.error(f"Failed to get log event toggles for guild {guild_id}: {e}")
        return {}


# Bot Detection Configuration Operations


async def get_botdetect_config(guild_id: int, key: str, default=None):
    """Get a bot detection configuration value."""
    cache_key = f"botdetect_config:{guild_id}:{key}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    try:
        result = await execute_query(
            "SELECT value FROM botdetect_config WHERE guild_id = $1 AND key = $2",
            guild_id,
            key,
            fetch_one=True,
        )
        if result:
            value = result["value"]
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
            await set_cache(cache_key, value)
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
            "guild_id": guild_id,
            "key": key,
            "value": json_value,
        }
        success = await insert_or_update("botdetect_config", ["guild_id", "key"], data)
        if success:
            await set_cache(f"botdetect_config:{guild_id}:{key}", value)
        return success
    except Exception as e:
        log.error(f"Failed to set botdetect config {key} for guild {guild_id}: {e}")
        return False


async def get_all_botdetect_config(guild_id: int) -> Dict[str, Any]:
    """Get all bot detection configuration for a guild."""
    try:
        results = await execute_query(
            "SELECT key, value FROM botdetect_config WHERE guild_id = $1",
            guild_id,
            fetch_all=True,
        )
        config = {}
        for row in results:
            value = row["value"]
            # Parse JSON if it's a string
            if isinstance(value, str):
                try:
                    config[row["key"]] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    config[row["key"]] = value
            else:
                config[row["key"]] = value
        return config
    except Exception as e:
        log.error(f"Failed to get botdetect config for guild {guild_id}: {e}")
        return {}


# User Data Operations (for abtuser.py)


async def get_user_data(user_id: int) -> Dict[str, Any]:
    """Get custom user data."""
    try:
        result = await execute_query("SELECT data FROM user_data WHERE user_id = $1", user_id, fetch_one=True)
        if result and result["data"]:
            return json.loads(result["data"]) if isinstance(result["data"], str) else result["data"]
        return {}
    except Exception as e:
        log.error(f"Failed to get user data for user {user_id}: {e}")
        return {}


async def set_user_data(user_id: int, data: Dict[str, Any]) -> bool:
    """Set custom user data."""
    try:
        user_data = {"user_id": user_id, "data": json.dumps(data)}
        return await insert_or_update("user_data", ["user_id"], user_data)
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
        return await delete_record("user_data", "user_id = $1", user_id)
    except Exception as e:
        log.error(f"Failed to delete user data for user {user_id}: {e}")
        return False


# Guild API Key Operations


async def set_guild_api_key(
    guild_id: int,
    api_provider: str,
    key_data: Union[str, Dict[str, Any]],
) -> bool:
    """
    Set a guild's API key. Handles both standard keys (str) and GitHub Copilot auth (dict).
    """
    try:
        encrypted_key = None
        encrypted_github_auth = None

        if api_provider == "github_copilot" and isinstance(key_data, dict):
            # Custom JSON serialization to handle datetime objects
            def datetime_converter(o):
                if isinstance(o, datetime):
                    return o.isoformat()

            encrypted_string = encrypt_data(json.dumps(key_data, default=datetime_converter))
            encrypted_github_auth = json.dumps({"data": encrypted_string})
        elif isinstance(key_data, str):
            encrypted_key = encrypt_data(key_data)
        else:
            log.error(f"Invalid key_data type for provider {api_provider}")
            return False

        data = {
            "guild_id": guild_id,
            "api_provider": api_provider,
            "encrypted_api_key": encrypted_key,
            "encrypted_github_auth_info": encrypted_github_auth,
        }
        success = await insert_or_update("guild_api_keys", ["guild_id"], data)
        if success:
            await delete_cache(f"guild_api_key:{guild_id}")
        return success
    except Exception as e:
        log.error(f"Failed to set API key for guild {guild_id}: {e}")
        return False


async def get_guild_api_key(guild_id: int) -> Optional[GuildAPIKey]:
    """
    Get a guild's API key. Returns a GuildAPIKey object with decrypted data.
    This function is for internal use by the bot only.
    """
    cache_key = f"guild_api_key:{guild_id}"
    cached = await get_cache(cache_key)
    if cached:
        return GuildAPIKey(**cached)

    try:
        result = await execute_query("SELECT * FROM guild_api_keys WHERE guild_id = $1", guild_id, fetch_one=True)
        if not result:
            return None

        db_data = dict(result)
        api_key = None
        github_auth_info = None

        if db_data.get("encrypted_api_key"):
            api_key = decrypt_data(db_data["encrypted_api_key"])

        if db_data.get("encrypted_github_auth_info"):
            # The data is stored as a JSON string like '{"data": "..."}'
            auth_data_wrapper = json.loads(db_data["encrypted_github_auth_info"])
            encrypted_string = auth_data_wrapper["data"]
            decrypted_auth_str = decrypt_data(encrypted_string)
            github_auth_info = json.loads(decrypted_auth_str)
            if "expires_at" in github_auth_info:
                github_auth_info["expires_at"] = datetime.fromisoformat(github_auth_info["expires_at"])

        guild_key = GuildAPIKey(
            guild_id=db_data["guild_id"],
            api_provider=db_data["api_provider"],
            api_key=api_key,
            github_auth_info=github_auth_info,
            created_at=db_data["created_at"],
            updated_at=db_data["updated_at"],
        )

        await set_cache(cache_key, guild_key.__dict__)
        return guild_key
    except Exception as e:
        log.error(f"Failed to get API key for guild {guild_id}: {e}")
        return None


async def remove_guild_api_key(guild_id: int) -> bool:
    """Delete a guild's API key."""
    try:
        success = await delete_record("guild_api_keys", "guild_id = $1", guild_id)
        if success:
            await delete_cache(f"guild_api_key:{guild_id}")
        return success
    except Exception as e:
        log.error(f"Failed to delete API key for guild {guild_id}: {e}")
        return False


# AI Decision Operations


async def add_ai_decision(
    guild_id: int,
    message_id: int,
    author_id: int,
    author_name: str,
    message_content_snippet: str,
    decision: Dict[str, Any],
) -> Optional[int]:
    """Add an AI moderation decision."""
    try:
        result = await execute_query(
            """
            INSERT INTO ai_decisions (
                guild_id,
                message_id,
                author_id,
                author_name,
                message_content_snippet,
                decision
            ) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
            """,
            guild_id,
            message_id,
            author_id,
            author_name,
            message_content_snippet,
            json.dumps(decision),
            fetch_one=True,
        )
        return result["id"] if result else None
    except Exception as e:
        log.error(f"Failed to add AI decision: {e}")
        return None


async def get_ai_decisions(guild_id: int, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieve AI decisions for a guild."""
    try:
        results = await execute_query(
            """
            SELECT id, guild_id, message_id, author_id, author_name,
                   message_content_snippet, decision, decision_timestamp
            FROM ai_decisions
            WHERE guild_id = $1
            ORDER BY decision_timestamp DESC
            LIMIT $2 OFFSET $3
            """,
            guild_id,
            limit,
            offset,
            fetch_all=True,
        )
        normalized = []
        for row in results:
            decision_json = row["decision"]
            decision = json.loads(decision_json) if decision_json else {}
            normalized.append(
                {
                    "guild_id": row["guild_id"],
                    "message_id": row["message_id"],
                    "author_id": row["author_id"],
                    "author_name": row["author_name"],
                    "message_content_snippet": row["message_content_snippet"],
                    "timestamp": (row["decision_timestamp"].isoformat() if row["decision_timestamp"] else None),
                    "ai_decision": decision,
                }
            )
        return normalized
    except Exception as e:
        log.error(f"Failed to fetch AI decisions for guild {guild_id}: {e}")
        return []


# Captcha Configuration Operations


async def get_captcha_config(guild_id: int) -> Optional[CaptchaConfig]:
    """Get captcha configuration for a guild."""
    cache_key = f"captcha_config:{guild_id}"
    cached = await get_cache(cache_key)
    if cached:
        return CaptchaConfig(**cached)

    try:
        result = await execute_query("SELECT * FROM captcha_config WHERE guild_id = $1", guild_id, fetch_one=True)
        if result:
            config = CaptchaConfig(**dict(result))
            await set_cache(cache_key, config.__dict__)
            return config
        return None
    except Exception as e:
        log.error(f"Failed to get captcha config for guild {guild_id}: {e}")
        return None


async def set_captcha_config(guild_id: int, config: CaptchaConfig) -> bool:
    """Set captcha configuration for a guild."""
    try:
        data = {
            "guild_id": guild_id,
            "enabled": config.enabled,
            "verification_role_id": config.verification_role_id,
            "max_attempts": config.max_attempts,
            "fail_action": config.fail_action,
            "timeout_duration": config.timeout_duration,
            "verification_channel_id": config.verification_channel_id,
        }
        success = await insert_or_update("captcha_config", ["guild_id"], data)
        if success:
            await set_cache(f"captcha_config:{guild_id}", config.__dict__)
        return success
    except Exception as e:
        log.error(f"Failed to set captcha config for guild {guild_id}: {e}")
        return False


async def update_captcha_config_field(guild_id: int, field: str, value: Any) -> bool:
    """Update a specific field in captcha configuration."""
    try:
        await execute_query(
            f"UPDATE captcha_config SET {field} = $1, updated_at = CURRENT_TIMESTAMP WHERE guild_id = $2",
            value,
            guild_id,
        )
        await delete_cache(f"captcha_config:{guild_id}")
        return True
    except Exception as e:
        log.error(f"Failed to update captcha config field {field} for guild {guild_id}: {e}")
        return False


# Captcha Attempts Operations


async def get_captcha_attempt(guild_id: int, user_id: int) -> Optional[CaptchaAttempt]:
    """Get captcha attempt record for a user in a guild."""
    try:
        result = await execute_query(
            "SELECT * FROM captcha_attempts WHERE guild_id = $1 AND user_id = $2",
            guild_id,
            user_id,
            fetch_one=True,
        )
        return CaptchaAttempt(**dict(result)) if result else None
    except Exception as e:
        log.error(f"Failed to get captcha attempt for user {user_id} in guild {guild_id}: {e}")
        return None


async def update_captcha_attempt(guild_id: int, user_id: int, increment: bool = True, verified: bool = False) -> bool:
    """Update or create captcha attempt record."""
    try:
        current_time = datetime.now(timezone.utc)

        # Try to get existing record
        existing = await get_captcha_attempt(guild_id, user_id)

        if existing:
            new_count = existing.attempt_count + 1 if increment else existing.attempt_count
            await execute_query(
                """UPDATE captcha_attempts
                   SET attempt_count = $1, last_attempt = $2, verified = $3
                   WHERE guild_id = $4 AND user_id = $5""",
                new_count,
                current_time,
                verified,
                guild_id,
                user_id,
            )
        else:
            # Create new record
            await execute_query(
                """INSERT INTO captcha_attempts (guild_id, user_id, attempt_count, last_attempt, verified)
                   VALUES ($1, $2, $3, $4, $5)""",
                guild_id,
                user_id,
                1 if increment else 0,
                current_time,
                verified,
            )
        return True
    except Exception as e:
        log.error(f"Failed to update captcha attempt for user {user_id} in guild {guild_id}: {e}")
        return False


async def reset_captcha_attempts(guild_id: int, user_id: int) -> bool:
    """Reset captcha attempts for a user."""
    try:
        return await delete_record("captcha_attempts", "guild_id = $1 AND user_id = $2", guild_id, user_id)
    except Exception as e:
        log.error(f"Failed to reset captcha attempts for user {user_id} in guild {guild_id}: {e}")
        return False


# Captcha Embeds Operations


async def store_captcha_embed(guild_id: int, channel_id: int, message_id: int) -> bool:
    """Store a captcha verification embed for persistence."""
    try:
        data = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "message_id": message_id,
            "is_active": True,
        }
        return await insert_or_update("captcha_embeds", ["guild_id", "channel_id", "message_id"], data)
    except Exception as e:
        log.error(f"Failed to store captcha embed for guild {guild_id}: {e}")
        return False


async def get_active_captcha_embeds(guild_id: Optional[int] = None) -> list:
    """Get all active captcha verification embeds."""
    try:
        if guild_id:
            query = "SELECT * FROM captcha_embeds WHERE guild_id = $1 AND is_active = TRUE"
            params = [guild_id]
        else:
            query = "SELECT * FROM captcha_embeds WHERE is_active = TRUE"
            params = []

        results = await execute_query(query, *params, fetch_all=True)
        return [dict(result) for result in results] if results else []
    except Exception as e:
        log.error(f"Failed to get active captcha embeds: {e}")
        return []


async def deactivate_captcha_embed(guild_id: int, channel_id: int, message_id: int) -> bool:
    """Deactivate a captcha verification embed."""
    try:
        await execute_query(
            "UPDATE captcha_embeds SET is_active = FALSE WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3",
            guild_id,
            channel_id,
            message_id,
        )
        return True
    except Exception as e:
        log.error(f"Failed to deactivate captcha embed for guild {guild_id}: {e}")
        return False


async def cleanup_inactive_captcha_embeds() -> bool:
    """Clean up inactive captcha embeds older than 30 days."""
    try:
        await execute_query(
            "DELETE FROM captcha_embeds WHERE is_active = FALSE AND created_at < NOW() - INTERVAL '30 days'"
        )
        return True
    except Exception as e:
        log.error(f"Failed to cleanup inactive captcha embeds: {e}")
        return False


# Verification Token Operations


async def store_verification_token(guild_id: int, user_id: int, token: str, expires_at: datetime) -> bool:
    """Store a verification token with expiration."""
    try:
        await execute_query(
            """INSERT INTO verification_tokens (guild_id, user_id, token, expires_at)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (guild_id, user_id)
               DO UPDATE SET token = $3, expires_at = $4, created_at = CURRENT_TIMESTAMP""",
            guild_id,
            user_id,
            token,
            expires_at,
        )
        return True
    except Exception as e:
        log.error(f"Failed to store verification token for user {user_id} in guild {guild_id}: {e}")
        return False


async def get_verification_token(guild_id: int, user_id: int) -> Optional[str]:
    """Get a valid verification token for a user."""
    try:
        result = await execute_query(
            """SELECT token FROM verification_tokens
               WHERE guild_id = $1 AND user_id = $2 AND expires_at > CURRENT_TIMESTAMP""",
            guild_id,
            user_id,
            fetch_one=True,
        )
        return result["token"] if result else None
    except Exception as e:
        log.error(f"Failed to get verification token for user {user_id} in guild {guild_id}: {e}")
        return None


async def validate_verification_token(token: str) -> Optional[tuple[int, int]]:
    """Validate a verification token and return (guild_id, user_id) if valid."""
    try:
        result = await execute_query(
            """SELECT guild_id, user_id FROM verification_tokens
               WHERE token = $1 AND expires_at > CURRENT_TIMESTAMP""",
            token,
            fetch_one=True,
        )
        return (result["guild_id"], result["user_id"]) if result else None
    except Exception as e:
        log.error(f"Failed to validate verification token {token}: {e}")
        return None


async def cleanup_expired_tokens() -> bool:
    """Clean up expired verification tokens."""
    try:
        await execute_query("DELETE FROM verification_tokens WHERE expires_at <= CURRENT_TIMESTAMP")
        return True
    except Exception as e:
        log.error(f"Failed to cleanup expired tokens: {e}")
        return False

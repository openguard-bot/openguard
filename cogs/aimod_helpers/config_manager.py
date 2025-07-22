import os
import asyncio
from typing import Optional

# Import database operations
from database.operations import (
    get_guild_config as db_get_guild_config,
    set_guild_config as db_set_guild_config,
)

# OpenRouter/LiteLLM configuration
DEFAULT_AI_MODEL = "github_copilot/gpt-4.1"

# Legacy environment variables (kept for compatibility)
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION")
DEFAULT_VERTEX_AI_MODEL = DEFAULT_AI_MODEL  # Alias for backward compatibility

# Note: Safety settings are now handled by OpenRouter/model providers
# and are not configurable through LiteLLM in the same way as Google GenAI

MOD_LOG_API_SECRET_ENV_VAR = "MOD_LOG_API_SECRET"

# Channel-specific configuration keys
CHANNEL_EXCLUSIONS_KEY = "AI_EXCLUDED_CHANNELS"
CHANNEL_RULES_KEY = "AI_CHANNEL_RULES"
ANALYSIS_MODE_KEY = "AI_ANALYSIS_MODE"
MESSAGE_RULES_KEY = "AI_KEYWORD_RULES"
VANITY_LOCK_KEY = "VANITY_URL_LOCK"
VANITY_NOTIFY_CHANNEL_KEY = "VANITY_URL_NOTIFY_CHANNEL"
VANITY_NOTIFY_TARGET_KEY = "VANITY_URL_NOTIFY_TARGET"

# Legacy paths (kept for compatibility but not used)
GUILD_CONFIG_DIR = os.path.join(os.getcwd(), "wdiscordbot-json-data")
GUILD_CONFIG_PATH = os.path.join(GUILD_CONFIG_DIR, "guild_config.json")
USER_INFRACTIONS_PATH = os.path.join(GUILD_CONFIG_DIR, "user_infractions.json")
APPEALS_PATH = os.path.join(GUILD_CONFIG_DIR, "appeals.json")
GLOBAL_BANS_PATH = os.path.join(GUILD_CONFIG_DIR, "global_bans.json")

# Legacy variables for backward compatibility (now use database)
GUILD_CONFIG = {}  # Deprecated - use database functions
USER_INFRACTIONS = {}  # Deprecated - use database functions
APPEALS = {}  # Deprecated - use database functions
GLOBAL_BANS = []  # Deprecated - use database functions

CONFIG_LOCK = asyncio.Lock()


# Legacy save functions (now no-ops for compatibility)
async def save_guild_config():
    """Legacy function - now a no-op since data is saved directly to database."""
    pass


async def save_user_infractions():
    """Legacy function - now a no-op since data is saved directly to database."""
    pass


async def save_appeals():
    """Legacy function - now a no-op since data is saved directly to database."""
    pass


async def save_global_bans():
    """Legacy function - now a no-op since data is saved directly to database."""
    pass


def get_guild_config(guild_id: int, key: str, default=None):
    """Get guild configuration value from database."""
    try:
        # This is a sync function, so we need to handle it carefully
        # For now, return default and log a warning
        import logging

        logging.warning(
            f"get_guild_config called synchronously for guild {guild_id}, key {key}. Use async version instead."
        )
        return default
    except Exception as e:
        print(f"Error in get_guild_config: {e}")
        return default


async def set_guild_config(guild_id: int, key: str, value):
    """Set guild configuration value in database."""
    try:
        return await db_set_guild_config(guild_id, key, value)
    except Exception as e:
        print(f"Failed to set guild config {key} for guild {guild_id}: {e}")
        return False


async def get_guild_config_async(guild_id: int, key: str, default=None):
    """Get guild configuration value from database (async version)."""
    try:
        return await db_get_guild_config(guild_id, key, default)
    except Exception as e:
        print(f"Failed to get guild config {key} for guild {guild_id}: {e}")
        return default


GUILD_LANGUAGE_KEY = "LANGUAGE_CODE"
DEFAULT_LANGUAGE = "en"
TRANSLATIONS = {
    "en": {
        "rules_updated": "Server rules have been updated from the rules channel.",
        "rules_not_found": "Could not find a rules channel in this server.",
        "rules_channel_empty": "The rules channel is empty or could not be read.",
        "rules_set": "Rules have been set for this server.",
        "no_permission": "You do not have permission to use this command.",
    },
    "es": {
        "rules_updated": "Las reglas del servidor se han actualizado desde el canal de reglas.",
        "rules_not_found": "No se pudo encontrar un canal de reglas en este servidor.",
        "rules_channel_empty": "El canal de reglas está vacío o no se pudo leer.",
        "rules_set": "Las reglas han sido establecidas para este servidor.",
        "no_permission": "No tienes permiso para usar este comando.",
    },
    "de": {
        "rules_updated": "Die Serverregeln wurden aus dem Regelkanal aktualisiert.",
        "rules_not_found": "Es konnte kein Regelkanal auf diesem Server gefunden werden.",
        "rules_channel_empty": "Der Regelkanal ist leer oder konnte nicht gelesen werden.",
        "rules_set": "Regeln wurden für diesen Server festgelegt.",
        "no_permission": "Du hast keine Berechtigung, diesen Befehl zu verwenden.",
    },
    "ko": {
        "rules_updated": "서버 규칙이 규칙 채널에서 업데이트되었습니다.",
        "rules_not_found": "이 서버에서 규칙 채널을 찾을 수 없습니다.",
        "rules_channel_empty": "규칙 채널이 비어 있거나 읽을 수 없습니다.",
        "rules_set": "이 서버에 대한 규칙이 설정되었습니다.",
        "no_permission": "이 명령을 사용할 권한이 없습니다.",
    },
    "ja": {
        "rules_updated": "サーバールールがルールチャンネルから更新されました。",
        "rules_not_found": "このサーバーにルールチャンネルが見つかりません。",
        "rules_channel_empty": "ルールチャンネルが空か、読み取れません。",
        "rules_set": "このサーバーのルールが設定されました。",
        "no_permission": "このコマンドを使用する権限がありません。",
    },
    "ru": {
        "rules_updated": "Правила сервера были обновлены из канала правил.",
        "rules_not_found": "Не удалось найти канал правил на этом сервере.",
        "rules_channel_empty": "Канал правил пуст или не может быть прочитан.",
        "rules_set": "Правила установлены для этого сервера.",
        "no_permission": "У вас нет прав для использования этой команды.",
    },
    "it": {
        "rules_updated": "Le regole del server sono state aggiornate dal canale delle regole.",
        "rules_not_found": "Non è stato possibile trovare un canale delle regole in questo server.",
        "rules_channel_empty": "Il canale delle regole è vuoto o non è stato possibile leggerlo.",
        "rules_set": "Le regole sono state impostate per questo server.",
        "no_permission": "Non hai il permesso di usare questo comando.",
    },
}


def get_guild_language(guild_id: int) -> str:
    """Get guild language (sync version - returns default for compatibility)."""
    # This is a sync function but database operations are async
    # For compatibility, return default language
    _ = guild_id  # Suppress unused parameter warning
    return DEFAULT_LANGUAGE


async def get_guild_language_async(guild_id: int) -> str:
    """Get guild language from database (async version)."""
    try:
        return await db_get_guild_config(guild_id, GUILD_LANGUAGE_KEY, DEFAULT_LANGUAGE)
    except Exception as e:
        print(f"Failed to get guild language for guild {guild_id}: {e}")
        return DEFAULT_LANGUAGE


def t(guild_id: int, key: str) -> str:
    """Get translated text (sync version - uses default language for compatibility)."""
    lang = get_guild_language(guild_id)
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE]).get(key, key)


# Channel-specific AI moderation configuration functions


async def get_excluded_channels(guild_id: int) -> list:
    """Get list of channels excluded from AI moderation."""
    return await get_guild_config_async(guild_id, CHANNEL_EXCLUSIONS_KEY, [])


async def add_excluded_channel(guild_id: int, channel_id: int) -> bool:
    """Add a channel to the AI moderation exclusion list."""
    excluded_channels = await get_excluded_channels(guild_id)
    if channel_id not in excluded_channels:
        excluded_channels.append(channel_id)
        return await set_guild_config(guild_id, CHANNEL_EXCLUSIONS_KEY, excluded_channels)
    return True  # Already excluded


async def remove_excluded_channel(guild_id: int, channel_id: int) -> bool:
    """Remove a channel from the AI moderation exclusion list."""
    excluded_channels = await get_excluded_channels(guild_id)
    if channel_id in excluded_channels:
        excluded_channels.remove(channel_id)
        return await set_guild_config(guild_id, CHANNEL_EXCLUSIONS_KEY, excluded_channels)
    return True  # Already not excluded


async def is_channel_excluded(guild_id: int, channel_id: int) -> bool:
    """Check if a channel is excluded from AI moderation."""
    excluded_channels = await get_excluded_channels(guild_id)
    return channel_id in excluded_channels


async def get_channel_rules(guild_id: int, channel_id: int) -> str:
    """Get custom rules for a specific channel."""
    channel_rules = await get_guild_config_async(guild_id, CHANNEL_RULES_KEY, {})
    return channel_rules.get(str(channel_id), "")


async def set_channel_rules(guild_id: int, channel_id: int, rules: str) -> bool:
    """Set custom rules for a specific channel."""
    channel_rules = await get_guild_config_async(guild_id, CHANNEL_RULES_KEY, {})
    channel_rules[str(channel_id)] = rules
    return await set_guild_config(guild_id, CHANNEL_RULES_KEY, channel_rules)


async def remove_channel_rules(guild_id: int, channel_id: int) -> bool:
    """Remove custom rules for a specific channel."""
    channel_rules = await get_guild_config_async(guild_id, CHANNEL_RULES_KEY, {})
    if str(channel_id) in channel_rules:
        del channel_rules[str(channel_id)]
        return await set_guild_config(guild_id, CHANNEL_RULES_KEY, channel_rules)
    return True  # Already no custom rules


async def get_all_channel_rules(guild_id: int) -> dict:
    """Get all channel-specific rules for a guild."""
    return await get_guild_config_async(guild_id, CHANNEL_RULES_KEY, {})


async def get_analysis_mode(guild_id: int) -> str:
    """Get the AI analysis mode for a guild."""
    return await get_guild_config_async(guild_id, ANALYSIS_MODE_KEY, "all")


async def set_analysis_mode(guild_id: int, mode: str) -> bool:
    """Set the AI analysis mode for a guild."""
    return await set_guild_config(guild_id, ANALYSIS_MODE_KEY, mode)


async def get_message_rules(guild_id: int) -> list:
    """Retrieve keyword/regex-based message rules."""
    return await get_guild_config_async(guild_id, MESSAGE_RULES_KEY, [])


async def set_message_rules(guild_id: int, rules: list) -> bool:
    """Set keyword/regex-based message rules."""
    return await set_guild_config(guild_id, MESSAGE_RULES_KEY, rules)


async def get_vanity_lock(guild_id: int) -> Optional[str]:
    """Get the locked vanity URL code for a guild."""
    return await get_guild_config_async(guild_id, VANITY_LOCK_KEY)


async def set_vanity_lock(guild_id: int, code: Optional[str]) -> bool:
    """Set or clear the locked vanity URL code for a guild."""
    return await set_guild_config(guild_id, VANITY_LOCK_KEY, code)


async def get_vanity_notify_channel(guild_id: int) -> Optional[int]:
    """Get the notification channel ID for vanity changes."""
    return await get_guild_config_async(guild_id, VANITY_NOTIFY_CHANNEL_KEY)


async def set_vanity_notify_channel(guild_id: int, channel_id: Optional[int]) -> bool:
    """Set the notification channel ID for vanity changes."""
    return await set_guild_config(guild_id, VANITY_NOTIFY_CHANNEL_KEY, channel_id)


async def get_vanity_notify_target(guild_id: int) -> Optional[int]:
    """Get the role or member ID to mention for vanity change alerts."""
    return await get_guild_config_async(guild_id, VANITY_NOTIFY_TARGET_KEY)


async def set_vanity_notify_target(guild_id: int, target_id: Optional[int]) -> bool:
    """Set the role or member ID to mention for vanity change alerts."""
    return await set_guild_config(guild_id, VANITY_NOTIFY_TARGET_KEY, target_id)


async def t_async(guild_id: int, key: str) -> str:
    """Get translated text (async version)."""
    lang = await get_guild_language_async(guild_id)
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE]).get(key, key)

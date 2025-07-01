import json
import os
import asyncio
import aiofiles
from google.genai import types

VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION")
DEFAULT_VERTEX_AI_MODEL = "gemini-2.5-flash-preview-05-20"

STANDARD_SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold="BLOCK_NONE"
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold="BLOCK_NONE",
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold="BLOCK_NONE",
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold="BLOCK_NONE"
    ),
]


MOD_LOG_API_SECRET_ENV_VAR = "MOD_LOG_API_SECRET"

GUILD_CONFIG_DIR = os.path.join(os.getcwd(), "wdiscordbot-json-data")
GUILD_CONFIG_PATH = os.path.join(GUILD_CONFIG_DIR, "guild_config.json")
USER_INFRACTIONS_PATH = os.path.join(GUILD_CONFIG_DIR, "user_infractions.json")
APPEALS_PATH = os.path.join(GUILD_CONFIG_DIR, "appeals.json")
GLOBAL_BANS_PATH = os.path.join(GUILD_CONFIG_DIR, "global_bans.json")

os.makedirs(GUILD_CONFIG_DIR, exist_ok=True)

if not os.path.exists(GUILD_CONFIG_PATH):
    with open(GUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)
try:
    with open(GUILD_CONFIG_PATH, "r", encoding="utf-8") as f:
        GUILD_CONFIG = json.load(f)
except Exception as e:
    print(f"Failed to load per-guild config from {GUILD_CONFIG_PATH}: {e}")
    GUILD_CONFIG = {}

if not os.path.exists(USER_INFRACTIONS_PATH):
    with open(USER_INFRACTIONS_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)
try:
    with open(USER_INFRACTIONS_PATH, "r", encoding="utf-8") as f:
        USER_INFRACTIONS = json.load(f)
except Exception as e:
    print(f"Failed to load user infractions from {USER_INFRACTIONS_PATH}: {e}")
    USER_INFRACTIONS = {}

if not os.path.exists(APPEALS_PATH):
    with open(APPEALS_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)
try:
    with open(APPEALS_PATH, "r", encoding="utf-8") as f:
        APPEALS = json.load(f)
except Exception as e:
    print(f"Failed to load appeals from {APPEALS_PATH}: {e}")
    APPEALS = {}

if not os.path.exists(GLOBAL_BANS_PATH):
    with open(GLOBAL_BANS_PATH, "w", encoding="utf-8") as f:
        json.dump([], f)
try:
    with open(GLOBAL_BANS_PATH, "r", encoding="utf-8") as f:
        GLOBAL_BANS = json.load(f)
except Exception as e:
    print(f"Failed to load global bans from {GLOBAL_BANS_PATH}: {e}")
    GLOBAL_BANS = []

CONFIG_LOCK = asyncio.Lock()

async def save_guild_config():
    async with CONFIG_LOCK:
        try:
            async with aiofiles.open(GUILD_CONFIG_PATH, "w", encoding="utf-8") as f:
                await f.write(json.dumps(GUILD_CONFIG, indent=2))
        except Exception as e:
            print(f"Failed to save per-guild config: {e}")

async def save_user_infractions():
    async with CONFIG_LOCK:
        try:
            async with aiofiles.open(USER_INFRACTIONS_PATH, "w", encoding="utf-8") as f:
                await f.write(json.dumps(USER_INFRACTIONS, indent=2))
        except Exception as e:
            print(f"Failed to save user infractions: {e}")

async def save_appeals():
    async with CONFIG_LOCK:
        try:
            async with aiofiles.open(APPEALS_PATH, "w", encoding="utf-8") as f:
                await f.write(json.dumps(APPEALS, indent=2))
        except Exception as e:
            print(f"Failed to save appeals: {e}")

async def save_global_bans():
    async with CONFIG_LOCK:
        try:
            async with aiofiles.open(GLOBAL_BANS_PATH, "w", encoding="utf-8") as f:
                await f.write(json.dumps(GLOBAL_BANS, indent=2))
        except Exception as e:
            print(f"Failed to save global bans: {e}")

def get_guild_config(guild_id: int, key: str, default=None):
    guild_str = str(guild_id)
    if guild_str in GUILD_CONFIG and key in GUILD_CONFIG[guild_str]:
        return GUILD_CONFIG[guild_str][key]
    return default

async def set_guild_config(guild_id: int, key: str, value):
    guild_str = str(guild_id)
    if guild_str not in GUILD_CONFIG:
        GUILD_CONFIG[guild_str] = {}
    GUILD_CONFIG[guild_str][key] = value
    await save_guild_config()

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
        "no_permission": "Non hai il permesso di usare questo comando."
    }
}

def get_guild_language(guild_id: int) -> str:
    return get_guild_config(guild_id, GUILD_LANGUAGE_KEY, DEFAULT_LANGUAGE)

def t(guild_id: int, key: str) -> str:
    lang = get_guild_language(guild_id)
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE]).get(key, key)
import datetime
from .config_manager import USER_INFRACTIONS, save_user_infractions

def truncate_text(text: str, max_length: int = 1024) -> str:
    """Truncate text for embed fields, adding ellipsis if needed."""
    if not isinstance(text, str):
        text = str(text)
    return text if len(text) <= max_length else text[:max_length-3] + "..."

def format_timestamp(dt: datetime.datetime) -> str:
    """Format a datetime object as a readable string."""
    if not isinstance(dt, datetime.datetime):
        return str(dt)
    return dt.strftime('%Y-%m-%d %H:%M:%S UTC')

def get_user_infraction_history(guild_id: int, user_id: int) -> list:
    """Retrieves a list of past infractions for a specific user in a guild."""
    key = f"{guild_id}_{user_id}"
    return USER_INFRACTIONS.get(key, [])

async def add_user_infraction(guild_id: int, user_id: int, rule_violated: str, action_taken: str, reasoning: str, timestamp: str):
    """Adds a new infraction record for a user, keeping only the last 10."""
    key = f"{guild_id}_{user_id}"
    if key not in USER_INFRACTIONS:
        USER_INFRACTIONS[key] = []
    infraction_record = {
        "timestamp": timestamp,
        "rule_violated": rule_violated,
        "action_taken": action_taken,
        "reasoning": reasoning
    }
    if not any(
        i['timestamp'] == timestamp and i['rule_violated'] == rule_violated and i['action_taken'] == action_taken and i['reasoning'] == reasoning
        for i in USER_INFRACTIONS[key]
    ):
        USER_INFRACTIONS[key].append(infraction_record)
        USER_INFRACTIONS[key] = USER_INFRACTIONS[key][-10:]
        await save_user_infractions()
import asyncio
import json
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
import redis.asyncio as redis
from . import schemas, crud
from .db import get_db
from sqlalchemy.orm import Session
from .api import (
    _fetch_from_discord_api,
    get_current_admin,
    is_bot_admin,
)
from database.cache import get_cache, get_redis

router = APIRouter()


async def get_guild_details(guild_id: int):
    """
    Fetches guild details from cache or Discord API.
    """
    redis_client = await get_redis()
    details = None
    if redis_client:
        cache_key = f"guild_details:{guild_id}"
        cached_details = await redis_client.get(cache_key)
        if cached_details:
            details = json.loads(cached_details)

    if not details:
        details = await _fetch_from_discord_api(f"/guilds/{guild_id}?with_counts=true")
        if redis_client:
            await redis_client.set(
                cache_key, json.dumps(details), ex=300
            )  # 5-minute TTL

    # Fetch member count from the new cache
    if redis_client:
        member_count = await redis_client.scard(f"guild:{guild_id}:members")
        details["member_count"] = member_count

    # The owner_id is already in the details from the Discord API
    details["owner_id"] = details.get("owner_id")

    return details


@router.get(
    "/guilds",
    response_model=List[schemas.Guild],
    dependencies=[Depends(get_current_admin)],
)
async def get_all_guilds():
    """
    Get a list of all guilds the bot is in.
    Tries to fetch from cache first, then falls back to the Discord API.
    """
    bot_guilds = await _fetch_from_discord_api("/users/@me/guilds")
    if not bot_guilds:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve guild list from Discord API.",
        )

    guild_ids = [guild["id"] for guild in bot_guilds]

    guilds = await asyncio.gather(
        *[get_guild_details(int(guild_id)) for guild_id in guild_ids]
    )
    return guilds


@router.get(
    "/guilds/{guild_id}",
    response_model=schemas.Guild,
    dependencies=[Depends(get_current_admin)],
)
async def get_guild_details_admin(guild_id: int):
    """
    Get detailed information for a specific guild.
    """
    return await get_guild_details(guild_id)


@router.post(
    "/guilds/{guild_id}/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def refresh_guild_cache(guild_id: int):
    """
    Manually refresh the cache for a specific guild.
    """
    redis_client = await get_redis()
    if redis_client:
        await redis_client.delete(f"guild_details:{guild_id}")
    return None


@router.get(
    "/guilds/{guild_id}/analytics",
    response_model=schemas.CommandAnalytics,
    dependencies=[Depends(get_current_admin)],
)
async def get_guild_analytics_admin(guild_id: int, db: Session = Depends(get_db)):
    """
    Get command usage analytics for a specific guild.
    """
    analytics = await crud.get_command_analytics(db, days=30, guild_id=guild_id)
    return analytics


@router.post(
    "/guilds/{guild_id}/send_message",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def send_message_admin(guild_id: int, message: schemas.AdminMessage):
    """
    Send a message to a channel or user.
    """
    if not message.channel_id and not message.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either channel_id or user_id must be provided.",
        )

    if message.channel_id:
        await _fetch_from_discord_api(
            f"/channels/{message.channel_id}/messages",
            method="POST",
            json={"content": message.content},
        )
    elif message.user_id:
        # To DM a user, we first need to create a DM channel
        dm_channel = await _fetch_from_discord_api(
            "/users/@me/channels",
            method="POST",
            json={"recipient_id": message.user_id},
        )
        await _fetch_from_discord_api(
            f"/channels/{dm_channel['id']}/messages",
            method="POST",
            json={"content": message.content},
        )

    return None


@router.get(
    "/guilds/{guild_id}/settings",
    response_model=schemas.GuildConfig,
    dependencies=[Depends(get_current_admin)],
)
async def get_guild_settings_admin(guild_id: int, db: Session = Depends(get_db)):
    """
    Get all settings for a specific guild.
    """
    return await crud.get_all_guild_settings(db, guild_id)


@router.put(
    "/guilds/{guild_id}/settings",
    response_model=schemas.GuildConfig,
    dependencies=[Depends(get_current_admin)],
)
async def update_guild_settings_admin(
    guild_id: int,
    settings_data: schemas.GuildConfigUpdate,
    db: Session = Depends(get_db),
):
    """
    Update all settings for a specific guild.
    """
    return await crud.update_all_guild_settings(db, guild_id, settings_data)


# Raw DB Access Endpoints


@router.get(
    "/db/tables",
    response_model=List[str],
    dependencies=[Depends(get_current_admin)],
)
async def get_db_tables(db: Session = Depends(get_db)):
    """
    Get a list of all table names in the database.
    """
    return await crud.get_table_names(db)


@router.get(
    "/db/tables/{table_name}",
    response_model=List[dict],
    dependencies=[Depends(get_current_admin)],
)
async def get_db_table_data(
    table_name: str, guild_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """
    Get data from a specific table, optionally filtered by guild_id.
    """
    try:
        return await crud.get_table_data(db, table_name, guild_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/db/tables/{table_name}/{pk_value}",
    response_model=dict,
    dependencies=[Depends(get_current_admin)],
)
async def update_db_table_row(
    table_name: str,
    pk_value: Any,
    update_data: schemas.RawTableRowUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a row in a specific table.
    """
    try:
        # The pk_value from the URL can be a string, int, etc.
        # We try to convert it to an int if it looks like one.
        try:
            pk_value_int = int(pk_value)
            pk_value = pk_value_int
        except ValueError:
            pass  # Keep it as a string if conversion fails

        return await crud.update_table_row(
            db, table_name, pk_value, update_data.row_data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )


@router.delete(
    "/db/tables/{table_name}/{pk_value}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def delete_db_table_row(
    table_name: str,
    pk_value: Any,
    db: Session = Depends(get_db),
):
    """
    Delete a row from a specific table.
    """
    try:
        try:
            pk_value_int = int(pk_value)
            pk_value = pk_value_int
        except ValueError:
            pass

        success = await crud.delete_table_row(db, table_name, pk_value)
        if not success:
            raise HTTPException(status_code=404, detail="Row not found.")
        return None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}"
        )

import asyncio
import json
from typing import List
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
    if redis_client:
        cache_key = f"guild_details:{guild_id}"
        cached_details = await redis_client.get(cache_key)
        if cached_details:
            return json.loads(cached_details)

    details = await _fetch_from_discord_api(f"/guilds/{guild_id}?with_counts=true")

    if redis_client:
        await redis_client.set(
            cache_key, json.dumps(details), ex=300
        )  # 5-minute TTL
    return details


@router.get(
    "/guilds",
    response_model=List[schemas.Guild],
    dependencies=[Depends(get_current_admin)],
)
async def get_all_guilds():
    """
    Get a list of all guilds the bot is in.
    """
    bot_guild_ids = await get_cache("bot_guilds")
    if not bot_guild_ids:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve guild list from cache.",
        )

    guilds = await asyncio.gather(
        *[get_guild_details(int(guild_id)) for guild_id in bot_guild_ids]
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
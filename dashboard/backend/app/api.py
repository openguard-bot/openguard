import os
import aiohttp
import logging
import asyncio
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt as jose_jwt  # type: ignore
from typing import List, Optional

from lists import Owners, OwnersTuple

from . import schemas, crud
from .db import get_db
from sqlalchemy.orm import Session  # type: ignore
from database.cache import get_cache
from cachetools import TTLCache
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# --- Caching ---
guild_cache = TTLCache(maxsize=100, ttl=300)
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost"))

# --- Configuration ---
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv(
    "DISCORD_REDIRECT_URI", "http://localhost/api/callback"
)
DISCORD_API_URL = "https://discord.com/api"
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- Rate Limiting ---
def handle_rate_limit(func):
    async def wrapper(*args, **kwargs):
        retries = 5
        delay = 1
        for i in range(retries):
            try:
                return await func(*args, **kwargs)
            except HTTPException as e:
                if e.status_code == 429:
                    retry_after = int(e.headers.get("Retry-After", delay))
                    logger.warning(
                        f"Rate limited. Retrying after {retry_after} seconds."
                    )
                    await asyncio.sleep(retry_after)
                    delay *= 2
                else:
                    raise e
        raise HTTPException(
            status_code=429, detail="Exceeded retry limit for rate-limited requests."
        )

    return wrapper


# --- Discord API Helpers ---


@handle_rate_limit
async def _fetch_discord_guilds_from_api(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{DISCORD_API_URL}/users/@me/guilds", headers=headers
        ) as resp:
            if resp.status != 200:
                raise HTTPException(
                    status_code=resp.status,
                    detail="Failed to get guilds from Discord",
                    headers=resp.headers,
                )
            return await resp.json()


async def fetch_user_guilds(access_token: str, user_id: str):
    """
    Fetches user guilds, using cache if available.
    Populates both list cache and individual guild caches.
    """
    user_guilds_cache_key = f"user_guilds:{user_id}"
    cached_guilds = await redis_client.get(user_guilds_cache_key)
    if cached_guilds:
        logger.info(f"Returning cached guild list for user {user_id}")
        return json.loads(cached_guilds)

    logger.info(f"Fetching guilds from Discord for user {user_id}")
    guilds_data = await _fetch_discord_guilds_from_api(access_token)

    # Cache the full list for the user
    await redis_client.set(user_guilds_cache_key, json.dumps(guilds_data), ex=300)

    # Also cache each guild individually
    for guild in guilds_data:
        await redis_client.set(f"guild:{guild['id']}", json.dumps(guild), ex=300)

    return guilds_data


# --- OAuth2 and JWT ---


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jose_jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        # The token is in the format "Bearer <token>"
        token = token.split(" ")[1]
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except (JWTError, IndexError):
        raise credentials_exception

    # This part is a placeholder. We need to store and retrieve user from DB
    # For now, we'll just return a dummy user from the token.
    user = schemas.User(
        id=payload.get("id"),
        username=username,
        discriminator=payload.get("discriminator"),
        avatar=payload.get("avatar"),
    )
    if user is None:
        raise credentials_exception
    return user


async def has_admin_permissions(guild_id: int, request: Request):
    """
    Dependency to check if the authenticated user has admin permissions in a guild.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        token = token.split(" ")[1]
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        access_token = payload.get("access_token")
        user_id = payload.get("id")
    except (JWTError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    guilds_data = await fetch_user_guilds(access_token, user_id)

    user_guild = next(
        (guild for guild in guilds_data if int(guild["id"]) == guild_id), None
    )

    if not user_guild:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guild not found or user is not a member",
        )

    # Check for ADMINISTRATOR permission
    permissions = int(user_guild["permissions"])
    if not (permissions & 0x8):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have admin permissions in this guild",
        )

    return True


def is_blog_admin(user: schemas.User) -> bool:
    """Check if the user is authorized to manage blog posts."""
    authorized_user_ids = OwnersTuple
    return user.id in authorized_user_ids


async def get_current_blog_admin(
    current_user: schemas.User = Depends(get_current_user),
) -> schemas.User:
    """Dependency to ensure only authorized users can manage blog posts."""
    if not is_blog_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage blog posts",
        )
    return current_user


# --- API Endpoints ---


@router.get("/login")
async def login():
    """Redirects to Discord for authentication."""
    return RedirectResponse(
        f"{DISCORD_API_URL}/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify guilds"
    )


@router.get("/callback")
async def callback(code: str, db: Session = Depends(get_db)):
    """Handles the callback from Discord."""
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")

    # Exchange code for access token
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DISCORD_API_URL}/oauth2/token", data=data, headers=headers
        ) as resp:
            if resp.status != 200:
                raise HTTPException(
                    status_code=400, detail="Failed to get token from Discord"
                )
            token_data = await resp.json()

    access_token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Fetch user info
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{DISCORD_API_URL}/users/@me", headers=headers) as resp:
            if resp.status != 200:
                raise HTTPException(
                    status_code=400, detail="Failed to get user info from Discord"
                )
            user_data = await resp.json()

    # Create JWT
    jwt_data = {
        "sub": user_data["username"],
        "id": user_data["id"],
        "discriminator": user_data["discriminator"],
        "avatar": user_data["avatar"],
        "access_token": access_token,
    }
    jwt_token = create_access_token(data=jwt_data)

    response = RedirectResponse(
        url="/dashboard/"
    )  # Redirect to frontend dashboard with trailing slash
    response.set_cookie(
        key="access_token",
        value=f"Bearer {jwt_token}",
        httponly=True,
        secure=True,
        samesite="Strict",
    )
    return response


@router.get("/guilds", response_model=List[schemas.Guild])
async def get_guilds(request: Request):
    """
    Returns a list of guilds the user and the bot are both in,
    and where the user has 'Manage Server' permissions.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        token = token.split(" ")[1]
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        access_token = payload.get("access_token")
    except (JWTError, IndexError):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Get bot's guilds from cache
    bot_guild_ids = await get_cache("bot_guilds")
    if bot_guild_ids is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve the bot's guild list from cache. The bot may be offline, or the cache service might be down. Please try again later.",
        )

    user_id = payload.get("id")
    user_guilds_data = await fetch_user_guilds(access_token, user_id)

    # Filter guilds
    managed_guilds = []
    for guild in user_guilds_data:
        # Check if bot is in the guild
        if int(guild["id"]) not in bot_guild_ids:
            continue

        # Check for 'Manage Server' permission (0x20)
        permissions = int(guild["permissions"])
        if (permissions & 0x20) == 0x20:
            managed_guilds.append(guild)

    return managed_guilds


@router.post("/guilds/refresh")
async def refresh_guilds(request: Request):
    """
    Clears the cached guild list for the current user.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        token = token.split(" ")[1]
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("id")
    except (JWTError, IndexError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user_guilds_cache_key = f"user_guilds:{user_id}"

    # To get all guild IDs, we might need to fetch from cache
    cached_guilds_list = await redis_client.get(user_guilds_cache_key)
    if cached_guilds_list:
        guilds_data = json.loads(cached_guilds_list)
        for guild in guilds_data:
            await redis_client.delete(f"guild:{guild['id']}")

    await redis_client.delete(user_guilds_cache_key)
    logger.info(f"Cache cleared for user {user_id}")
    return JSONResponse(content={"status": "success"}, status_code=200)


@router.get("/guilds/{guild_id}", response_model=schemas.Guild)
async def get_guild(
    guild_id: int,
    request: Request,
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Returns detailed information for a specific guild.
    """
    if not has_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have admin permissions in this guild",
        )

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        token = token.split(" ")[1]
        payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        access_token = payload.get("access_token")
    except (JWTError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user_id = payload.get("id")

    # 1. Check for individual guild in cache
    guild_cache_key = f"guild:{guild_id}"
    cached_guild = await redis_client.get(guild_cache_key)
    if cached_guild:
        logger.info(f"Returning cached guild {guild_id}")
        return json.loads(cached_guild)

    # 2. If not found, fetch all, which will populate the individual caches
    logger.info(f"Guild {guild_id} not in cache. Fetching from Discord.")
    guilds_data = await fetch_user_guilds(access_token, user_id)

    guild = next((g for g in guilds_data if int(g["id"]) == guild_id), None)

    if not guild:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guild not found or user is not a member",
        )

    return guild


@router.get("/stats", response_model=schemas.Stats)
async def get_stats(request: Request, db: Session = Depends(get_db)):
    """
    Returns global statistics.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    total_guilds = await crud.get_total_guilds(db)
    total_users = await crud.get_total_users(db)
    commands_ran = await crud.get_total_commands_ran(db)

    # Uptime is not yet implemented, so we'll keep it as a placeholder for now.
    # This will require a separate mechanism to track bot uptime.
    uptime = 99.9

    return schemas.Stats(
        total_guilds=total_guilds,
        total_users=total_users,
        commands_ran=commands_ran,
        uptime=uptime,
    )


@router.get("/analytics/commands", response_model=schemas.CommandAnalytics)
async def get_command_analytics(
    request: Request,
    days: int = 30,
    guild_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Returns command usage analytics for the specified time period.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    analytics = await crud.get_command_analytics(db, days=days, guild_id=guild_id)
    return analytics


@router.get("/analytics/moderation", response_model=schemas.ModerationAnalytics)
async def get_moderation_analytics(
    request: Request,
    days: int = 30,
    guild_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Returns moderation analytics for the specified time period.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    analytics = await crud.get_moderation_analytics(db, days=days, guild_id=guild_id)
    return analytics


@router.get("/analytics/users", response_model=schemas.UserAnalytics)
async def get_user_analytics(
    request: Request,
    days: int = 30,
    guild_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Returns user activity analytics for the specified time period.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    analytics = await crud.get_user_analytics(db, days=days, guild_id=guild_id)
    return analytics


@router.get("/system/health", response_model=schemas.SystemHealth)
async def get_system_health(request: Request):
    """
    Returns system health metrics and status.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Get system metrics
    import psutil
    import time

    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Get bot-specific metrics (placeholder for now)
    bot_status = "online"  # This would come from bot status check
    latency = 50  # This would come from Discord API latency

    return schemas.SystemHealth(
        cpu_usage=cpu_percent,
        memory_usage=memory.percent,
        disk_usage=disk.percent,
        bot_status=bot_status,
        api_latency=latency,
        uptime_seconds=int(time.time() - 1640995200),  # Placeholder start time
    )


@router.get("/users/@me", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    """
    Get the current authenticated user.
    """
    return current_user


@router.get("/owners", response_model=List[int])
async def get_owners():
    """
    Returns a list of owner user IDs.
    """
    return list(Owners.__dict__.values())


# --- Blog Post API Endpoints ---


@router.get("/blog/posts", response_model=schemas.BlogPostList)
async def get_blog_posts(
    page: int = 1,
    per_page: int = 10,
    published_only: bool = False,
    db: Session = Depends(get_db),
):
    """Get a list of blog posts."""
    skip = (page - 1) * per_page
    posts = await crud.get_blog_posts(
        db, skip=skip, limit=per_page, published_only=published_only
    )
    total = await crud.count_blog_posts(db, published_only=published_only)

    return schemas.BlogPostList(posts=posts, total=total, page=page, per_page=per_page)


@router.get("/blog/posts/{post_id}", response_model=schemas.BlogPost)
async def get_blog_post(post_id: int, db: Session = Depends(get_db)):
    """Get a specific blog post by ID."""
    post = await crud.get_blog_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return post


@router.post("/blog/posts", response_model=schemas.BlogPost)
async def create_blog_post(
    post: schemas.BlogPostCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_blog_admin),
):
    """Create a new blog post."""
    # Check if slug already exists
    existing_post = await crud.get_blog_post_by_slug(db, post.slug)
    if existing_post:
        raise HTTPException(
            status_code=400, detail="A post with this slug already exists"
        )

    return await crud.create_blog_post(db, post, int(current_user.id))


@router.put("/blog/posts/{post_id}", response_model=schemas.BlogPost)
async def update_blog_post(
    post_id: int,
    post_update: schemas.BlogPostUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_blog_admin),
):
    """Update a blog post."""
    # Check if post exists
    existing_post = await crud.get_blog_post(db, post_id)
    if not existing_post:
        raise HTTPException(status_code=404, detail="Blog post not found")

    # Check if new slug conflicts with existing posts
    if post_update.slug and post_update.slug != existing_post.slug:
        slug_conflict = await crud.get_blog_post_by_slug(db, post_update.slug)
        if slug_conflict:
            raise HTTPException(
                status_code=400, detail="A post with this slug already exists"
            )

    updated_post = await crud.update_blog_post(db, post_id, post_update)
    if not updated_post:
        raise HTTPException(status_code=404, detail="Blog post not found")

    return updated_post


@router.delete("/blog/posts/{post_id}")
async def delete_blog_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_blog_admin),
):
    """Delete a blog post."""
    success = await crud.delete_blog_post(db, post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Blog post not found")

    return {"message": "Blog post deleted successfully"}


@router.get("/guilds/{guild_id}/config", response_model=schemas.GuildConfig)
async def get_guild_configuration(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get the configuration for a specific guild.
    """
    if has_admin:
        return await crud.get_guild_config(db=db, guild_id=guild_id)


@router.get("/guilds/{guild_id}/users", response_model=List[schemas.GuildUser])
async def get_guild_users(
    guild_id: int,
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get users in a guild with pagination and search.
    """
    if has_admin:
        return await crud.get_guild_users(
            db=db, guild_id=guild_id, page=page, limit=limit, search=search
        )


@router.get(
    "/guilds/{guild_id}/infractions", response_model=List[schemas.UserInfraction]
)
async def get_guild_infractions(
    guild_id: int,
    page: int = 1,
    limit: int = 50,
    user_id: Optional[int] = None,
    action_type: Optional[str] = None,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get infractions for a guild with filtering options.
    """
    if has_admin:
        return await crud.get_guild_infractions(
            db=db,
            guild_id=guild_id,
            page=page,
            limit=limit,
            user_id=user_id,
            action_type=action_type,
        )


@router.get("/guilds/{guild_id}/appeals", response_model=List[schemas.Appeal])
async def get_guild_appeals(
    guild_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get appeals for a guild with status filtering.
    """
    if has_admin:
        return await crud.get_guild_appeals(db=db, guild_id=guild_id, status=status)


@router.post("/guilds/{guild_id}/appeals/{appeal_id}/respond")
async def respond_to_appeal(
    guild_id: int,
    appeal_id: str,
    response: schemas.AppealResponse,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Respond to an appeal (accept/reject).
    """
    if has_admin:
        return await crud.respond_to_appeal(
            db=db, appeal_id=appeal_id, status=response.status, reason=response.reason
        )


@router.get("/users/{user_id}/profile", response_model=schemas.UserProfile)
async def get_user_profile(
    user_id: int,
    guild_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_user),
):
    """
    Get detailed user profile including infractions and statistics.
    """
    return await crud.get_user_profile(db=db, user_id=user_id, guild_id=guild_id)


@router.post("/guilds/{guild_id}/moderation/action")
async def create_moderation_action(
    guild_id: int,
    action: schemas.ModerationAction,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Create a new moderation action.
    """
    if has_admin:
        return await crud.create_moderation_action(
            db=db, guild_id=guild_id, action=action
        )


# Enhanced Configuration Endpoints


@router.get(
    "/guilds/{guild_id}/config/comprehensive",
    response_model=schemas.ComprehensiveGuildConfig,
)
async def get_comprehensive_guild_config(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get all configuration settings for a guild in one comprehensive response.
    """
    if has_admin:
        return await crud.get_comprehensive_guild_config(db=db, guild_id=guild_id)


@router.get(
    "/guilds/{guild_id}/config/bot-detection",
    response_model=schemas.BotDetectionSettings,
)
async def get_bot_detection_config(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get bot detection configuration for a guild.
    """
    if has_admin:
        return await crud.get_bot_detection_config(db=db, guild_id=guild_id)


@router.put(
    "/guilds/{guild_id}/config/bot-detection",
    response_model=schemas.BotDetectionSettings,
)
async def update_bot_detection_config(
    guild_id: int,
    settings: schemas.BotDetectionSettingsUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update bot detection configuration for a guild.
    """
    if has_admin:
        return await crud.update_bot_detection_config(
            db=db, guild_id=guild_id, settings=settings
        )


@router.get(
    "/guilds/{guild_id}/config/message-rate", response_model=schemas.MessageRateSettings
)
async def get_message_rate_config(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get message rate limiting configuration for a guild.
    """
    if has_admin:
        return await crud.get_message_rate_config(db=db, guild_id=guild_id)


@router.put(
    "/guilds/{guild_id}/config/message-rate", response_model=schemas.MessageRateSettings
)
async def update_message_rate_config(
    guild_id: int,
    settings: schemas.MessageRateSettingsUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update message rate limiting configuration for a guild.
    """
    if has_admin:
        return await crud.update_message_rate_config(
            db=db, guild_id=guild_id, settings=settings
        )


@router.get(
    "/guilds/{guild_id}/config/raid-defense", response_model=schemas.RaidDefenseSettings
)
async def get_raid_defense_config(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get raid defense configuration for a guild.
    """
    if has_admin:
        return await crud.get_raid_defense_config(db=db, guild_id=guild_id)


@router.put(
    "/guilds/{guild_id}/config/raid-defense", response_model=schemas.RaidDefenseSettings
)
async def update_raid_defense_config(
    guild_id: int,
    settings: schemas.RaidDefenseSettingsUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update raid defense configuration for a guild.
    """
    if has_admin:
        return await crud.update_raid_defense_config(
            db=db, guild_id=guild_id, settings=settings
        )


@router.get(
    "/guilds/{guild_id}/config/advanced-logging",
    response_model=schemas.AdvancedLoggingSettings,
)
async def get_advanced_logging_config(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get advanced logging configuration for a guild.
    """
    if has_admin:
        return await crud.get_advanced_logging_config(db=db, guild_id=guild_id)


@router.put(
    "/guilds/{guild_id}/config/advanced-logging",
    response_model=schemas.AdvancedLoggingSettings,
)
async def update_advanced_logging_config(
    guild_id: int,
    settings: schemas.AdvancedLoggingSettingsUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update advanced logging configuration for a guild.
    """
    if has_admin:
        return await crud.update_advanced_logging_config(
            db=db, guild_id=guild_id, settings=settings
        )


@router.post("/guilds/{guild_id}/config", response_model=schemas.GuildConfig)
async def update_guild_configuration(
    guild_id: int,
    config_data: schemas.GuildConfigUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update the configuration for a specific guild.
    """
    if has_admin:
        return await crud.update_guild_config(
            db=db, guild_id=guild_id, config_data=config_data
        )


@router.get("/guilds/{guild_id}/config/general", response_model=schemas.GeneralSettings)
async def get_general_config(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get the general configuration for a specific guild.
    """
    if has_admin:
        return await crud.get_general_settings(db=db, guild_id=guild_id)


@router.post(
    "/guilds/{guild_id}/config/general", response_model=schemas.GeneralSettings
)
async def update_general_config(
    guild_id: int,
    settings_data: schemas.GeneralSettingsUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update the general configuration for a specific guild.
    """
    if has_admin:
        return await crud.update_general_settings(
            db=db, guild_id=guild_id, settings_data=settings_data
        )


@router.get(
    "/guilds/{guild_id}/config/moderation", response_model=schemas.ModerationSettings
)
async def get_moderation_config(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get the moderation configuration for a specific guild.
    """
    if has_admin:
        return await crud.get_moderation_settings(db=db, guild_id=guild_id)


@router.post(
    "/guilds/{guild_id}/config/moderation", response_model=schemas.ModerationSettings
)
async def update_moderation_config(
    guild_id: int,
    settings_data: schemas.ModerationSettingsUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update the moderation configuration for a specific guild.
    """
    if has_admin:
        return await crud.update_moderation_settings(
            db=db, guild_id=guild_id, settings_data=settings_data
        )


@router.get("/guilds/{guild_id}/config/logging", response_model=schemas.LoggingSettings)
async def get_logging_config(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get the logging configuration for a specific guild.
    """
    if has_admin:
        return await crud.get_logging_settings(db=db, guild_id=guild_id)


@router.post(
    "/guilds/{guild_id}/config/logging", response_model=schemas.LoggingSettings
)
async def update_logging_config(
    guild_id: int,
    settings_data: schemas.LoggingSettingsUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update the logging configuration for a specific guild.
    """
    if has_admin:
        return await crud.update_logging_settings(
            db=db, guild_id=guild_id, settings_data=settings_data
        )


@router.post("/guilds/{guild_id}/api_key", response_model=schemas.GuildAPIKey)
async def set_guild_api_key_endpoint(
    guild_id: int,
    key_data: schemas.GuildAPIKeyUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Set or update the API key for a specific guild.
    """
    if has_admin:
        return await crud.set_guild_api_key(db=db, guild_id=guild_id, key_data=key_data)


@router.delete("/guilds/{guild_id}/api_key")
async def remove_guild_api_key_endpoint(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Delete the API key for a specific guild.
    """
    if has_admin:
        return await crud.remove_guild_api_key(db=db, guild_id=guild_id)


@router.get(
    "/guilds/{guild_id}/config/channel-exclusions",
    response_model=schemas.ChannelExclusionSettings,
)
async def get_channel_exclusions(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get channel exclusions for AI moderation.
    """
    if has_admin:
        return await crud.get_channel_exclusions(db=db, guild_id=guild_id)


@router.post(
    "/guilds/{guild_id}/config/channel-exclusions",
    response_model=schemas.ChannelExclusionSettings,
)
async def update_channel_exclusions(
    guild_id: int,
    settings: schemas.ChannelExclusionSettings,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update channel exclusions for AI moderation.
    """
    if has_admin:
        return await crud.update_channel_exclusions(
            db=db, guild_id=guild_id, settings=settings
        )


@router.get(
    "/guilds/{guild_id}/config/channel-rules", response_model=schemas.ChannelRulesUpdate
)
async def get_channel_rules(
    guild_id: int,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Get channel-specific AI moderation rules.
    """
    if has_admin:
        return await crud.get_channel_rules(db=db, guild_id=guild_id)


@router.post(
    "/guilds/{guild_id}/config/channel-rules", response_model=schemas.ChannelRulesUpdate
)
async def update_channel_rules(
    guild_id: int,
    settings: schemas.ChannelRulesUpdate,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Update channel-specific AI moderation rules.
    """
    if has_admin:
        return await crud.update_channel_rules(
            db=db, guild_id=guild_id, settings=settings
        )


@router.delete("/guilds/{guild_id}/config/channel-rules/{channel_id}")
async def delete_channel_rules(
    guild_id: int,
    channel_id: str,
    db: Session = Depends(get_db),
    has_admin: bool = Depends(has_admin_permissions),
):
    """
    Delete custom rules for a specific channel.
    """
    if has_admin:
        return await crud.delete_channel_rules(
            db=db, guild_id=guild_id, channel_id=channel_id
        )

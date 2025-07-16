from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from . import schemas
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import logging
from .db import redis_client

logger = logging.getLogger(__name__)


async def get_general_settings(db: Session, guild_id: int) -> schemas.GeneralSettings:
    """Retrieve general settings for a guild."""
    result = await db.execute(
        text(
            "SELECT key, value FROM guild_settings WHERE guild_id = :guild_id AND key IN ('prefix')"
        ),
        {"guild_id": guild_id},
    )
    settings_data: Dict[str, Any] = {
        "prefix": "o!",  # Default prefix
    }
    for key, value in result.fetchall():
        if isinstance(value, str):
            try:
                settings_data[key] = json.loads(value)
            except json.JSONDecodeError:
                settings_data[key] = value
        else:
            settings_data[key] = value
    logger.info(f"General settings data for guild {guild_id}: {settings_data}")
    try:
        return schemas.GeneralSettings(**settings_data)
    except Exception as e:
        logger.error(f"Error creating GeneralSettings for guild {guild_id}: {e}")
        raise


async def update_general_settings(
    db: Session, guild_id: int, settings_data: schemas.GeneralSettingsUpdate
) -> schemas.GeneralSettings:
    """Update general settings for a guild."""
    for key, value in settings_data.model_dump(exclude_unset=True).items():
        db_value = json.dumps(value)
        await db.execute(
            text(
                """
                INSERT INTO guild_settings (guild_id, key, value)
                VALUES (:guild_id, :key, :value)
                ON CONFLICT (guild_id, key)
                DO UPDATE SET value = :value
                """
            ),
            {"guild_id": guild_id, "key": key, "value": db_value},
        )
        if key == "prefix":
            await redis_client.publish("prefix_updates", f"{guild_id}:{db_value}")
    await db.commit()
    return await get_general_settings(db, guild_id)


async def create_command_log(
    db: Session, log: schemas.CommandLog
) -> schemas.CommandLog:
    """Create a new command log entry."""
    await db.execute(
        text(
            """
            INSERT INTO command_logs (guild_id, user_id, command_name, timestamp)
            VALUES (:guild_id, :user_id, :command_name, :timestamp)
            """
        ),
        {
            "guild_id": log.guild_id,
            "user_id": log.user_id,
            "command_name": log.command_name,
            "timestamp": log.timestamp if log.timestamp else datetime.utcnow(),
        },
    )
    await db.commit()
    return log


async def get_total_guilds(db: Session) -> int:
    """Get the total number of unique guilds from guild_settings."""
    result = await db.execute(
        text("SELECT COUNT(DISTINCT guild_id) FROM guild_settings")
    )
    return result.scalar_one()


async def get_total_users(db: Session) -> int:
    """Get the total number of unique users from user_data."""
    result = await db.execute(text("SELECT COUNT(DISTINCT user_id) FROM user_data"))
    return result.scalar_one()


async def get_total_commands_ran(db: Session) -> int:
    """Get the total number of commands ran from command_logs."""
    result = await db.execute(text("SELECT COUNT(*) FROM command_logs"))
    return result.scalar_one()


async def get_moderation_settings(
    db: Session, guild_id: int
) -> schemas.ModerationSettings:
    """Retrieve moderation settings for a guild."""
    result = await db.execute(
        text(
            "SELECT key, value FROM guild_settings WHERE guild_id = :guild_id AND key IN ('mod_log_channel_id', 'moderator_role_id', 'server_rules', 'action_confirmation_settings', 'confirmation_ping_role_id')"
        ),
        {"guild_id": guild_id},
    )
    settings_data: Dict[str, Any] = {
        "mod_log_channel_id": None,
        "moderator_role_id": None,
        "server_rules": None,
        "action_confirmation_settings": {},
        "confirmation_ping_role_id": None,
    }
    for key, value in result.fetchall():
        if key == "action_confirmation_settings" and isinstance(value, str):
            try:
                settings_data[key] = json.loads(value)
            except json.JSONDecodeError:
                settings_data[key] = {}  # Fallback to default
        else:
            settings_data[key] = value
    return schemas.ModerationSettings(**settings_data)


async def update_moderation_settings(
    db: Session, guild_id: int, settings_data: schemas.ModerationSettingsUpdate
) -> schemas.ModerationSettings:
    """Update moderation settings for a guild."""
    for key, value in settings_data.model_dump(exclude_unset=True).items():
        # Serialize dicts to JSON strings before storing
        db_value = json.dumps(value) if isinstance(value, dict) else value
        await db.execute(
            text(
                """
                INSERT INTO guild_settings (guild_id, key, value)
                VALUES (:guild_id, :key, :value)
                ON CONFLICT (guild_id, key)
                DO UPDATE SET value = :value
                """
            ),
            {"guild_id": guild_id, "key": key, "value": db_value},
        )
    await db.commit()
    return await get_moderation_settings(db, guild_id)


async def get_logging_settings(db: Session, guild_id: int) -> schemas.LoggingSettings:
    """Retrieve logging settings for a guild."""
    result = await db.execute(
        text(
            "SELECT key, value FROM guild_settings WHERE guild_id = :guild_id AND key IN ('log_channel_id', 'message_delete_logging', 'message_edit_logging', 'member_join_logging', 'member_leave_logging')"
        ),
        {"guild_id": guild_id},
    )
    settings_data: Dict[str, Any] = {
        "log_channel_id": None,
        "message_delete_logging": False,
        "message_edit_logging": False,
        "member_join_logging": False,
        "member_leave_logging": False,
    }
    for key, value in result.fetchall():
        settings_data[key] = value
    logger.info(f"Logging settings data for guild {guild_id}: {settings_data}")
    try:
        return schemas.LoggingSettings(**settings_data)
    except Exception as e:
        logger.error(f"Error creating LoggingSettings for guild {guild_id}: {e}")
        raise


async def update_logging_settings(
    db: Session, guild_id: int, settings_data: schemas.LoggingSettingsUpdate
) -> schemas.LoggingSettings:
    """Update logging settings for a guild."""
    for key, value in settings_data.model_dump(exclude_unset=True).items():
        await db.execute(
            text(
                """
                INSERT INTO guild_settings (guild_id, key, value)
                VALUES (:guild_id, :key, :value)
                ON CONFLICT (guild_id, key)
                DO UPDATE SET value = :value
                """
            ),
            {"guild_id": guild_id, "key": key, "value": value},
        )
    await db.commit()
    return await get_logging_settings(db, guild_id)


# Analytics CRUD Functions
async def get_command_analytics(
    db: Session, days: int = 30, guild_id: Optional[int] = None
) -> schemas.CommandAnalytics:
    """Get command usage analytics."""
    params = {"days": days}
    guild_filter = ""
    if guild_id:
        guild_filter = "AND guild_id = :guild_id"
        params["guild_id"] = guild_id

    # Get total commands
    total_result = await db.execute(
        text(
            """
            SELECT COUNT(*) as total_commands
            FROM command_logs
            WHERE timestamp >= NOW() - INTERVAL :days::INTEGER * INTERVAL '1 day' {guild_filter}
        """
        ),
        {"guild_id": guild_id, "days": days} if guild_id else {"days": days},
    )
    total_commands = total_result.fetchone()[0] or 0

    # Get unique commands
    unique_result = await db.execute(
        text(
            """
            SELECT COUNT(DISTINCT command_name) as unique_commands
            FROM command_logs
            WHERE timestamp >= NOW() - INTERVAL :days::INTEGER * INTERVAL '1 day' {guild_filter}
        """
        ),
        {"guild_id": guild_id, "days": days} if guild_id else {"days": days},
    )
    unique_commands = unique_result.fetchone()[0] or 0

    # Get top commands
    top_commands_result = await db.execute(
        text(
            """
            SELECT command_name, COUNT(*) as usage_count, MAX(timestamp) as last_used
            FROM command_logs
            WHERE timestamp >= NOW() - INTERVAL :days::INTEGER * INTERVAL '1 day' {guild_filter}
            GROUP BY command_name
            ORDER BY usage_count DESC
            LIMIT 10
        """
        ),
        {"guild_id": guild_id, "days": days} if guild_id else {"days": days},
    )

    top_commands = [
        schemas.CommandUsageData(
            command_name=row[0], usage_count=row[1], last_used=row[2]
        )
        for row in top_commands_result.fetchall()
    ]

    # Get daily usage
    daily_usage_result = await db.execute(
        text(
            f"""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM command_logs
            WHERE timestamp >= NOW() - INTERVAL ':days days' {guild_filter}
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        ),
        params,
    )

    daily_usage = [
        schemas.DailyUsageData(date=str(row[0]), count=row[1])
        for row in daily_usage_result.fetchall()
    ]

    return schemas.CommandAnalytics(
        total_commands=total_commands,
        unique_commands=unique_commands,
        top_commands=top_commands,
        daily_usage=daily_usage,
    )


async def get_moderation_analytics(
    db: Session, days: int = 30, guild_id: Optional[int] = None
) -> schemas.ModerationAnalytics:
    """Get moderation analytics."""
    params = {"days": days}
    guild_filter = ""
    if guild_id:
        guild_filter = "AND guild_id = :guild_id"
        params["guild_id"] = guild_id

    # Get total actions
    total_result = await db.execute(
        text(
            """
            SELECT COUNT(*) as total_actions
            FROM moderation_logs
            WHERE timestamp >= NOW() - INTERVAL :days {guild_filter}
        """.format(
                guild_filter=guild_filter
            )
        ),
        {"guild_id": guild_id, "days": days} if guild_id else {"days": days},
    )
    total_actions = total_result.fetchone()[0] or 0

    # Get actions by type
    actions_by_type_result = await db.execute(
        text(
            """
            SELECT action_type, COUNT(*) as count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
            FROM moderation_logs
            WHERE timestamp >= NOW() - INTERVAL :days {guild_filter}
            GROUP BY action_type
            ORDER BY count DESC
        """.format(
                guild_filter=guild_filter
            )
        ),
        {"guild_id": guild_id, "days": days} if guild_id else {"days": days},
    )

    actions_by_type = [
        schemas.ModerationActionData(
            action_type=row[0], count=row[1], percentage=row[2]
        )
        for row in actions_by_type_result.fetchall()
    ]

    # Get daily actions
    daily_actions_result = await db.execute(
        text(
            """
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM moderation_logs
            WHERE timestamp >= NOW() - INTERVAL :days {guild_filter}
            GROUP BY DATE(timestamp)
            ORDER BY date
        """.format(
                guild_filter=guild_filter
            )
        ),
        {"guild_id": guild_id, "days": days} if guild_id else {"days": days},
    )

    daily_actions = [
        schemas.DailyUsageData(date=str(row[0]), count=row[1])
        for row in daily_actions_result.fetchall()
    ]

    # Get top moderators
    top_moderators_result = await db.execute(
        text(
            """
            SELECT moderator_id, COUNT(*) as action_count
            FROM moderation_logs
            WHERE timestamp >= NOW() - INTERVAL :days {guild_filter}
            GROUP BY moderator_id
            ORDER BY action_count DESC
            LIMIT 10
        """.format(
                guild_filter=guild_filter
            )
        ),
        {"guild_id": guild_id, "days": days} if guild_id else {"days": days},
    )

    top_moderators = [
        schemas.TopModeratorData(moderator_id=row[0], action_count=row[1])
        for row in top_moderators_result.fetchall()
    ]

    return schemas.ModerationAnalytics(
        total_actions=total_actions,
        actions_by_type=actions_by_type,
        daily_actions=daily_actions,
        top_moderators=top_moderators,
    )


async def get_user_analytics(
    db: Session, days: int = 30, guild_id: Optional[int] = None
) -> schemas.UserAnalytics:
    """Get user activity analytics."""
    params = {"days": days}
    guild_filter = ""
    if guild_id:
        guild_filter = "AND guild_id = :guild_id"
        params["guild_id"] = guild_id

    # Get total active users (users who ran commands)
    active_users_result = await db.execute(
        text(
            """
            SELECT COUNT(DISTINCT user_id) as active_users
            FROM command_logs
            WHERE timestamp >= NOW() - INTERVAL :days {guild_filter}
        """.replace(
                "{guild_filter}", guild_filter
            )
        ),
        (
            {"guild_id": guild_id, "days": f"{days} days"}
            if guild_id
            else {"days": f"{days} days"}
        ),
    )
    total_active_users = active_users_result.fetchone()[0] or 0

    # Get new users today (placeholder - would need join tracking)
    new_users_today = 0  # This would require member join tracking

    # Get activity timeline
    activity_result = await db.execute(
        text(
            """
            SELECT
                DATE(timestamp) as date,
                COUNT(DISTINCT user_id) as active_users,
                0 as new_users,  -- Placeholder
                COUNT(*) as commands_used
            FROM command_logs
            WHERE timestamp >= NOW() - INTERVAL :days {guild_filter}
            GROUP BY DATE(timestamp)
            ORDER BY date
        """.replace(
                "{guild_filter}", guild_filter
            )
        ),
        (
            {"guild_id": guild_id, "days": f"{days} days"}
            if guild_id
            else {"days": f"{days} days"}
        ),
    )

    activity_timeline = [
        schemas.UserActivityData(
            date=str(row[0]),
            active_users=row[1],
            new_users=row[2],
            commands_used=row[3],
        )
        for row in activity_result.fetchall()
    ]

    return schemas.UserAnalytics(
        total_active_users=total_active_users,
        new_users_today=new_users_today,
        activity_timeline=activity_timeline,
    )


async def get_guild_users(
    db: Session,
    guild_id: int,
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
) -> list[schemas.GuildUser]:
    """Get users in a guild with pagination and search."""
    offset = (page - 1) * limit
    search_filter = ""
    params = {"guild_id": guild_id, "limit": limit, "offset": offset}

    if search:
        search_filter = "AND (username ILIKE :search OR discriminator ILIKE :search)"
        params["search"] = f"%{search}%"

    # This is a placeholder query - in reality, you'd need to track guild members
    result = await db.execute(
        text(
            f"""
            SELECT DISTINCT
                cl.user_id,
                'Unknown' as username,
                '0000' as discriminator,
                NULL as avatar,
                NULL as joined_at,
                '[]' as roles,
                COALESCE(inf_count.count, 0) as infraction_count,
                MAX(cl.timestamp) as last_active
            FROM command_logs cl
            LEFT JOIN (
                SELECT user_id, COUNT(*) as count
                FROM user_infractions
                WHERE guild_id = :guild_id
                GROUP BY user_id
            ) inf_count ON cl.user_id = inf_count.user_id
            WHERE cl.guild_id = :guild_id {search_filter}
            GROUP BY cl.user_id, inf_count.count
            ORDER BY last_active DESC
            LIMIT :limit OFFSET :offset
        """
        ),
        params,
    )

    return [
        schemas.GuildUser(
            user_id=row[0],
            username=row[1],
            discriminator=row[2],
            avatar=row[3],
            joined_at=row[4],
            roles=json.loads(row[5]) if row[5] else [],
            infraction_count=row[6],
            last_active=row[7],
        )
        for row in result.fetchall()
    ]


async def get_guild_infractions(
    db: Session,
    guild_id: int,
    page: int = 1,
    limit: int = 50,
    user_id: Optional[int] = None,
    action_type: Optional[str] = None,
) -> list[schemas.UserInfraction]:
    """Get infractions for a guild with filtering."""
    offset = (page - 1) * limit
    filters = ["guild_id = :guild_id"]
    params = {"guild_id": guild_id, "limit": limit, "offset": offset}

    if user_id:
        filters.append("user_id = :user_id")
        params["user_id"] = user_id

    if action_type:
        filters.append("action_taken = :action_type")
        params["action_type"] = action_type

    where_clause = " AND ".join(filters)

    result = await db.execute(
        text(
            f"""
            SELECT id, guild_id, user_id, timestamp, rule_violated,
                   action_taken, reasoning, NULL as moderator_id,
                   'Unknown' as moderator_name
            FROM user_infractions
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """
        ),
        params,
    )

    return [
        schemas.UserInfraction(
            id=row[0],
            guild_id=row[1],
            user_id=row[2],
            timestamp=row[3],
            rule_violated=row[4],
            action_taken=row[5],
            reasoning=row[6],
            moderator_id=row[7],
            moderator_name=row[8],
        )
        for row in result.fetchall()
    ]


async def get_guild_appeals(
    db: Session, guild_id: int, status: Optional[str] = None
) -> list[schemas.Appeal]:
    """Get appeals for a guild."""
    filters = []
    params = {}

    if status:
        filters.append("status = :status")
        params["status"] = status

    where_clause = " AND ".join(filters) if filters else "1=1"

    result = await db.execute(
        text(
            f"""
            SELECT appeal_id, user_id, 'Unknown' as username, reason,
                   timestamp, status, original_infraction, created_at
            FROM appeals
            WHERE {where_clause}
            ORDER BY created_at DESC
        """
        ),
        params,
    )

    return [
        schemas.Appeal(
            appeal_id=row[0],
            user_id=row[1],
            username=row[2],
            reason=row[3],
            timestamp=row[4],
            status=row[5],
            original_infraction=json.loads(row[6]) if row[6] else None,
            created_at=row[7],
        )
        for row in result.fetchall()
    ]


async def respond_to_appeal(
    db: Session, appeal_id: str, status: str, reason: Optional[str] = None
):
    """Respond to an appeal."""
    await db.execute(
        text(
            """
            UPDATE appeals
            SET status = :status, updated_at = CURRENT_TIMESTAMP
            WHERE appeal_id = :appeal_id
        """
        ),
        {"appeal_id": appeal_id, "status": status},
    )
    await db.commit()
    return {"success": True, "message": f"Appeal {status}"}


async def get_user_profile(
    db: Session, user_id: int, guild_id: Optional[int] = None
) -> schemas.UserProfile:
    """Get detailed user profile."""
    guild_filter = "AND guild_id = :guild_id" if guild_id else ""
    params = {"user_id": user_id}
    if guild_id:
        params["guild_id"] = guild_id

    # Get total infractions
    infractions_result = await db.execute(
        text(
            f"""
            SELECT COUNT(*) as total_infractions
            FROM user_infractions
            WHERE user_id = :user_id {guild_filter}
        """
        ),
        params,
    )
    total_infractions = infractions_result.fetchone()[0] or 0

    # Get recent infractions
    recent_infractions_result = await db.execute(
        text(
            f"""
            SELECT id, guild_id, user_id, timestamp, rule_violated,
                   action_taken, reasoning, NULL as moderator_id,
                   'Unknown' as moderator_name
            FROM user_infractions
            WHERE user_id = :user_id {guild_filter}
            ORDER BY timestamp DESC
            LIMIT 5
        """
        ),
        params,
    )

    recent_infractions = [
        schemas.UserInfraction(
            id=row[0],
            guild_id=row[1],
            user_id=row[2],
            timestamp=row[3],
            rule_violated=row[4],
            action_taken=row[5],
            reasoning=row[6],
            moderator_id=row[7],
            moderator_name=row[8],
        )
        for row in recent_infractions_result.fetchall()
    ]

    # Get command usage count
    command_usage_result = await db.execute(
        text(
            f"""
            SELECT COUNT(*) as command_count
            FROM command_logs
            WHERE user_id = :user_id {guild_filter}
        """
        ),
        params,
    )
    command_usage_count = command_usage_result.fetchone()[0] or 0

    return schemas.UserProfile(
        user_id=user_id,
        username="Unknown",  # Would need to fetch from Discord API
        discriminator="0000",
        avatar=None,
        total_infractions=total_infractions,
        recent_infractions=recent_infractions,
        guild_join_date=None,  # Would need member tracking
        last_active=None,  # Would need activity tracking
        roles=[],  # Would need role tracking
        command_usage_count=command_usage_count,
    )


async def create_moderation_action(
    db: Session, guild_id: int, action: schemas.ModerationAction
):
    """Create a new moderation action."""
    await db.execute(
        text(
            """
            INSERT INTO moderation_logs
            (guild_id, moderator_id, target_user_id, action_type, reason, duration_seconds)
            VALUES (:guild_id, :moderator_id, :target_user_id, :action_type, :reason, :duration_seconds)
        """
        ),
        {
            "guild_id": guild_id,
            "moderator_id": 0,  # Would need current user ID
            "target_user_id": action.target_user_id,
            "action_type": action.action_type,
            "reason": action.reason,
            "duration_seconds": action.duration_seconds,
        },
    )
    await db.commit()
    return {"success": True, "message": "Moderation action created"}


# Blog Post CRUD Functions


async def create_blog_post(
    db: Session, post: schemas.BlogPostCreate, author_id: int
) -> schemas.BlogPost:
    """Create a new blog post."""
    result = await db.execute(
        text(
            """
            INSERT INTO blog_posts (title, content, author_id, published, slug)
            VALUES (:title, :content, :author_id, :published, :slug)
            RETURNING id, title, content, author_id, published, slug, created_at, updated_at
        """
        ),
        {
            "title": post.title,
            "content": post.content,
            "author_id": author_id,
            "published": post.published,
            "slug": post.slug,
        },
    )
    await db.commit()
    row = result.fetchone()
    return schemas.BlogPost(**dict(row))


async def get_blog_post(db: Session, post_id: int) -> Optional[schemas.BlogPost]:
    """Get a blog post by ID."""
    result = await db.execute(
        text("SELECT * FROM blog_posts WHERE id = :post_id"), {"post_id": post_id}
    )
    row = result.fetchone()
    if row:
        return schemas.BlogPost(**dict(row))
    return None


async def get_blog_post_by_slug(db: Session, slug: str) -> Optional[schemas.BlogPost]:
    """Get a blog post by slug."""
    result = await db.execute(
        text("SELECT * FROM blog_posts WHERE slug = :slug"), {"slug": slug}
    )
    row = result.fetchone()
    if row:
        return schemas.BlogPost(**dict(row))
    return None


async def get_blog_posts(
    db: Session, skip: int = 0, limit: int = 10, published_only: bool = False
) -> list[schemas.BlogPost]:
    """Get a list of blog posts."""
    query = "SELECT * FROM blog_posts"
    params = {}

    if published_only:
        query += " WHERE published = true"

    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
    params.update({"limit": limit, "skip": skip})

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [schemas.BlogPost(**row._asdict()) for row in rows]


async def update_blog_post(
    db: Session, post_id: int, post_update: schemas.BlogPostUpdate
) -> Optional[schemas.BlogPost]:
    """Update a blog post."""
    # Build dynamic update query
    update_fields = []
    params = {"post_id": post_id}

    if post_update.title is not None:
        update_fields.append("title = :title")
        params["title"] = post_update.title

    if post_update.content is not None:
        update_fields.append("content = :content")
        params["content"] = post_update.content

    if post_update.published is not None:
        update_fields.append("published = :published")
        params["published"] = post_update.published

    if post_update.slug is not None:
        update_fields.append("slug = :slug")
        params["slug"] = post_update.slug

    if not update_fields:
        # No fields to update, return existing post
        return await get_blog_post(db, post_id)

    query = f"""
        UPDATE blog_posts
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = :post_id
        RETURNING id, title, content, author_id, published, slug, created_at, updated_at
    """

    result = await db.execute(text(query), params)
    await db.commit()
    row = result.fetchone()
    if row:
        return schemas.BlogPost(**dict(row))
    return None


async def delete_blog_post(db: Session, post_id: int) -> bool:
    """Delete a blog post."""
    result = await db.execute(
        text("DELETE FROM blog_posts WHERE id = :post_id"), {"post_id": post_id}
    )
    await db.commit()
    return result.rowcount > 0


async def count_blog_posts(db: Session, published_only: bool = False) -> int:
    """Count total blog posts."""
    query = "SELECT COUNT(*) FROM blog_posts"
    if published_only:
        query += " WHERE published = true"

    result = await db.execute(text(query))
    return result.scalar_one()


# Enhanced Configuration CRUD Functions


async def get_bot_detection_config(
    db: Session, guild_id: int
) -> schemas.BotDetectionSettings:
    """Get bot detection configuration for a guild."""
    result = await db.execute(
        text(
            """
            SELECT key, value FROM botdetect_config
            WHERE guild_id = :guild_id
        """
        ),
        {"guild_id": guild_id},
    )

    config_data = {row[0]: row[1] for row in result.fetchall()}

    # Apply defaults if not set
    defaults = {
        "enabled": False,
        "keywords": [],
        "action": "warn",
        "timeout_duration": 300,
        "log_channel": None,
        "whitelist_roles": [],
        "whitelist_users": [],
    }

    for key, default_value in defaults.items():
        if key not in config_data:
            config_data[key] = default_value

    return schemas.BotDetectionSettings(**config_data)


async def update_bot_detection_config(
    db: Session, guild_id: int, settings: schemas.BotDetectionSettingsUpdate
) -> schemas.BotDetectionSettings:
    """Update bot detection configuration for a guild."""
    for key, value in settings.model_dump(exclude_unset=True).items():
        if value is not None:
            await db.execute(
                text(
                    """
                    INSERT INTO botdetect_config (guild_id, key, value)
                    VALUES (:guild_id, :key, :value)
                    ON CONFLICT (guild_id, key)
                    DO UPDATE SET value = :value, updated_at = CURRENT_TIMESTAMP
                """
                ),
                {"guild_id": guild_id, "key": key, "value": json.dumps(value)},
            )

    await db.commit()
    return await get_bot_detection_config(db, guild_id)


# Channel Exclusions and Rules CRUD functions


async def get_channel_exclusions(
    db: Session, guild_id: int
) -> schemas.ChannelExclusionSettings:
    """Get channel exclusions for AI moderation."""
    result = await db.execute(
        text(
            "SELECT value FROM guild_config WHERE guild_id = :guild_id AND key = 'AI_EXCLUDED_CHANNELS'"
        ),
        {"guild_id": guild_id},
    )
    row = result.fetchone()
    excluded_channels = []
    if row and row[0]:
        try:
            excluded_channels = (
                json.loads(row[0]) if isinstance(row[0], str) else row[0]
            )
            # Convert integers to strings for API consistency
            excluded_channels = [str(ch) for ch in excluded_channels]
        except (json.JSONDecodeError, TypeError):
            excluded_channels = []

    return schemas.ChannelExclusionSettings(excluded_channels=excluded_channels)


async def update_channel_exclusions(
    db: Session, guild_id: int, settings: schemas.ChannelExclusionSettings
) -> schemas.ChannelExclusionSettings:
    """Update channel exclusions for AI moderation."""
    # Convert string channel IDs to integers for storage
    excluded_channels = [int(ch) for ch in settings.excluded_channels]

    await db.execute(
        text(
            """
            INSERT INTO guild_config (guild_id, key, value)
            VALUES (:guild_id, :key, :value)
            ON CONFLICT (guild_id, key)
            DO UPDATE SET value = :value, updated_at = CURRENT_TIMESTAMP
        """
        ),
        {
            "guild_id": guild_id,
            "key": "AI_EXCLUDED_CHANNELS",
            "value": json.dumps(excluded_channels),
        },
    )
    await db.commit()
    return await get_channel_exclusions(db, guild_id)


async def get_channel_rules(db: Session, guild_id: int) -> schemas.ChannelRulesUpdate:
    """Get channel-specific AI moderation rules."""
    result = await db.execute(
        text(
            "SELECT value FROM guild_config WHERE guild_id = :guild_id AND key = 'AI_CHANNEL_RULES'"
        ),
        {"guild_id": guild_id},
    )
    row = result.fetchone()
    channel_rules = {}
    if row and row[0]:
        try:
            channel_rules = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except (json.JSONDecodeError, TypeError):
            channel_rules = {}

    return schemas.ChannelRulesUpdate(channel_rules=channel_rules)


async def update_channel_rules(
    db: Session, guild_id: int, settings: schemas.ChannelRulesUpdate
) -> schemas.ChannelRulesUpdate:
    """Update channel-specific AI moderation rules."""
    await db.execute(
        text(
            """
            INSERT INTO guild_config (guild_id, key, value)
            VALUES (:guild_id, :key, :value)
            ON CONFLICT (guild_id, key)
            DO UPDATE SET value = :value, updated_at = CURRENT_TIMESTAMP
        """
        ),
        {
            "guild_id": guild_id,
            "key": "AI_CHANNEL_RULES",
            "value": json.dumps(settings.channel_rules),
        },
    )
    await db.commit()
    return await get_channel_rules(db, guild_id)


async def delete_channel_rules(db: Session, guild_id: int, channel_id: str) -> dict:
    """Delete custom rules for a specific channel."""
    # Get current channel rules
    current_rules = await get_channel_rules(db, guild_id)

    # Remove the specific channel
    if channel_id in current_rules.channel_rules:
        del current_rules.channel_rules[channel_id]

        # Update the database
        await db.execute(
            text(
                """
                INSERT INTO guild_config (guild_id, key, value)
                VALUES (:guild_id, :key, :value)
                ON CONFLICT (guild_id, key)
                DO UPDATE SET value = :value, updated_at = CURRENT_TIMESTAMP
            """
            ),
            {
                "guild_id": guild_id,
                "key": "AI_CHANNEL_RULES",
                "value": json.dumps(current_rules.channel_rules),
            },
        )
        await db.commit()
        return {"message": f"Custom rules for channel {channel_id} have been deleted."}
    else:
        return {"message": f"No custom rules found for channel {channel_id}."}


async def get_rate_limiting_settings(
    db: Session, guild_id: int
) -> schemas.RateLimitingSettings:
    """Get rate limiting configuration for a guild."""
    result = await db.execute(
        text(
            """
            SELECT key, value FROM guild_settings
            WHERE guild_id = :guild_id AND key LIKE 'message_rate_%'
        """
        ),
        {"guild_id": guild_id},
    )

    config_data = {}
    for key, value in result.fetchall():
        # Remove 'message_rate_' prefix
        clean_key = key.replace("message_rate_", "")
        config_data[clean_key] = value

    # Apply defaults
    defaults = {
        "enabled": False,
        "high_rate_threshold": 10,
        "low_rate_threshold": 3,
        "high_rate_slowmode": 5,
        "low_rate_slowmode": 2,
        "check_interval": 30,
        "analysis_window": 60,
        "notifications_enabled": True,
        "notification_channel": None,
    }

    for key, default_value in defaults.items():
        if key not in config_data:
            config_data[key] = default_value

    return schemas.RateLimitingSettings(**config_data)


async def update_rate_limiting_settings(
    db: Session, guild_id: int, settings: schemas.RateLimitingSettingsUpdate
) -> schemas.RateLimitingSettings:
    """Update rate limiting configuration for a guild."""
    for key, value in settings.model_dump(exclude_unset=True).items():
        if value is not None:
            prefixed_key = f"message_rate_{key}"
            await db.execute(
                text(
                    """
                    INSERT INTO guild_settings (guild_id, key, value)
                    VALUES (:guild_id, :key, :value)
                    ON CONFLICT (guild_id, key)
                    DO UPDATE SET value = :value, updated_at = CURRENT_TIMESTAMP
                """
                ),
                {"guild_id": guild_id, "key": prefixed_key, "value": json.dumps(value)},
            )

    await db.commit()
    return await get_rate_limiting_settings(db, guild_id)


async def get_security_settings(
    db: Session, guild_id: int
) -> schemas.SecuritySettings:
    """Get security settings for a guild."""
    bot_detection = await get_bot_detection_config(db, guild_id)
    return schemas.SecuritySettings(bot_detection=bot_detection)


async def update_security_settings(
    db: Session, guild_id: int, settings: schemas.SecuritySettingsUpdate
) -> schemas.SecuritySettings:
    """Update security settings for a guild."""
    if settings.bot_detection:
        await update_bot_detection_config(
            db, guild_id, settings.bot_detection
        )
    return await get_security_settings(db, guild_id)


async def get_ai_settings(db: Session, guild_id: int) -> schemas.AISettings:
    """Get AI settings for a guild."""
    channel_exclusions = await get_channel_exclusions(db, guild_id)
    channel_rules = await get_channel_rules(db, guild_id)
    return schemas.AISettings(
        channel_exclusions=channel_exclusions, channel_rules=channel_rules
    )


async def update_ai_settings(
    db: Session, guild_id: int, settings: schemas.AISettingsUpdate
) -> schemas.AISettings:
    """Update AI settings for a guild."""
    if settings.channel_exclusions:
        await update_channel_exclusions(db, guild_id, settings.channel_exclusions)
    if settings.channel_rules:
        await update_channel_rules(db, guild_id, settings.channel_rules)
    return await get_ai_settings(db, guild_id)


async def get_channels_settings(
    db: Session, guild_id: int
) -> schemas.ChannelsSettings:
    """Get channels settings for a guild."""
    exclusions = await get_channel_exclusions(db, guild_id)
    rules = await get_channel_rules(db, guild_id)
    return schemas.ChannelsSettings(
        exclusions=exclusions.excluded_channels, rules=rules.channel_rules
    )


async def update_channels_settings(
    db: Session, guild_id: int, settings: schemas.ChannelsSettingsUpdate
) -> schemas.ChannelsSettings:
    """Update channels settings for a guild."""
    if settings.exclusions:
        await update_channel_exclusions(
            db,
            guild_id,
            schemas.ChannelExclusionSettings(excluded_channels=settings.exclusions),
        )
    if settings.rules:
        await update_channel_rules(
            db, guild_id, schemas.ChannelRulesUpdate(channel_rules=settings.rules)
        )
    return await get_channels_settings(db, guild_id)


async def get_raid_defense_config(
    db: Session, guild_id: int
) -> schemas.RaidDefenseSettings:
    """Get raid defense configuration for a guild."""
    result = await db.execute(
        text(
            """
            SELECT key, value FROM guild_settings
            WHERE guild_id = :guild_id AND key LIKE 'raid_defense_%'
        """
        ),
        {"guild_id": guild_id},
    )

    config_data = {}
    for key, value in result.fetchall():
        # Remove 'raid_defense_' prefix
        clean_key = key.replace("raid_defense_", "")
        config_data[clean_key] = value

    # Apply defaults
    defaults = {
        "enabled": False,
        "threshold": 10,
        "timeframe": 60,
        "alert_channel": None,
        "auto_action": "none",
    }

    for key, default_value in defaults.items():
        if key not in config_data:
            config_data[key] = default_value

    return schemas.RaidDefenseSettings(**config_data)


async def update_raid_defense_config(
    db: Session, guild_id: int, settings: schemas.RaidDefenseSettingsUpdate
) -> schemas.RaidDefenseSettings:
    """Update raid defense configuration for a guild."""
    for key, value in settings.model_dump(exclude_unset=True).items():
        if value is not None:
            prefixed_key = f"raid_defense_{key}"
            await db.execute(
                text(
                    """
                    INSERT INTO guild_settings (guild_id, key, value)
                    VALUES (:guild_id, :key, :value)
                    ON CONFLICT (guild_id, key)
                    DO UPDATE SET value = :value, updated_at = CURRENT_TIMESTAMP
                """
                ),
                {"guild_id": guild_id, "key": prefixed_key, "value": json.dumps(value)},
            )

    await db.commit()
    return await get_raid_defense_config(db, guild_id)


async def get_all_guild_settings(db: Session, guild_id: int) -> schemas.GuildConfig:
    """Retrieve all settings for a guild."""
    result = await db.execute(
        text("SELECT key, value FROM guild_settings WHERE guild_id = :guild_id"),
        {"guild_id": guild_id},
    )
    settings_data = {}
    for key, value in result.fetchall():
        try:
            settings_data[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            settings_data[key] = value
    return schemas.GuildConfig(**settings_data)


async def update_all_guild_settings(
    db: Session, guild_id: int, settings_data: schemas.GuildConfigUpdate
) -> schemas.GuildConfig:
    """Update all settings for a guild."""
    for key, value in settings_data.model_dump(exclude_unset=True).items():
        db_value = json.dumps(value)
        await db.execute(
            text(
                """
                INSERT INTO guild_settings (guild_id, key, value)
                VALUES (:guild_id, :key, :value)
                ON CONFLICT (guild_id, key)
                DO UPDATE SET value = :value
                """
            ),
            {"guild_id": guild_id, "key": key, "value": db_value},
        )
        if key == "prefix":
            await redis_client.publish("prefix_updates", f"{guild_id}:{db_value}")
    await db.commit()
    return await get_all_guild_settings(db, guild_id)


# Raw DB Access CRUD Functions


async def get_table_names(db: Session) -> List[str]:
    """Retrieve all table names in the public schema."""
    result = await db.execute(
        text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
    )
    return [row[0] for row in result.fetchall()]


async def get_table_data(
    db: Session, table_name: str, guild_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Retrieve data from a specific table, optionally filtered by guild_id."""
    # Sanitize table_name to prevent SQL injection
    safe_table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
    if safe_table_name != table_name:
        raise ValueError("Invalid table name")

    # Get column names for the table from the database inspector
    def get_columns_sync(sync_conn):
        inspector = inspect(sync_conn.bind)
        return inspector.get_columns(table_name)

    column_dicts = await db.run_sync(get_columns_sync)
    columns = [c["name"] for c in column_dicts]

    query_str = f"SELECT * FROM {safe_table_name}"
    params = {}
    if guild_id and "guild_id" in columns:
        query_str += " WHERE guild_id = :guild_id"
        params["guild_id"] = guild_id

    result = await db.execute(text(query_str), params)

    data = []
    for row in result.mappings().all():
        row_data = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                row_data[key] = value.isoformat()
            else:
                row_data[key] = value
        data.append(row_data)
    return data


async def get_primary_key_column(db: Session, table_name: str) -> Optional[str]:
    """Get the primary key column name for a table."""
    result = await db.execute(
        text(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_name = :table_name
              AND tc.table_schema = 'public';
            """
        ),
        {"table_name": table_name},
    )
    pk_column = result.scalar_one_or_none()
    return pk_column


async def update_table_row(
    db: Session, table_name: str, pk_value: Any, row_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a row in a specific table."""
    safe_table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
    if safe_table_name != table_name:
        raise ValueError("Invalid table name")

    pk_column = await get_primary_key_column(db, safe_table_name)
    if not pk_column:
        raise ValueError(f"No primary key found for table {safe_table_name}")

    update_fields = []
    params = {f"pk_value": pk_value}
    for key, value in row_data.items():
        # Do not allow updating the primary key
        if key == pk_column:
            continue

        sanitized_key = "".join(c for c in key if c.isalnum() or c == "_")
        if sanitized_key != key:
            # skip potentially malicious keys
            continue

        update_fields.append(f"{sanitized_key} = :{key}")
        params[key] = value

    if not update_fields:
        raise ValueError("No fields to update")

    query = f"""
        UPDATE {safe_table_name}
        SET {', '.join(update_fields)}
        WHERE {pk_column} = :pk_value
        RETURNING *
    """

    result = await db.execute(text(query), params)
    await db.commit()

    updated_row = result.mappings().one()

    # Convert datetime objects to ISO format strings
    response_data = {}
    for key, value in updated_row.items():
        if isinstance(value, datetime):
            response_data[key] = value.isoformat()
        else:
            response_data[key] = value

    return response_data



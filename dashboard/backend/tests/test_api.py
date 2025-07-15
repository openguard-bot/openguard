import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
import asyncio
from typing import AsyncGenerator

from dashboard.backend.main import app
from dashboard.backend.app.db import get_db
from dashboard.backend.app.api import get_current_user, has_admin_permissions
from dashboard.backend.app.schemas import User

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=True)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency override for getting a DB session.
    """
    async with TestingSessionLocal() as session:
        yield session


async def override_get_current_user() -> User:
    """
    Dependency override for getting the current user. Returns a mock user.
    """
    return User(
        id="12345",
        username="testuser",
        discriminator="1234",
        avatar=None,
    )


async def override_has_admin_permissions():
    """
    Dependency override for checking admin permissions.
    """
    return True


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[has_admin_permissions] = override_has_admin_permissions


@pytest.fixture(scope="session")
def event_loop():
    """
    Creates an asyncio event loop for the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an async test client for making API requests.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Keep the original test for the root endpoint
client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the backend!"}


@pytest.mark.asyncio
async def test_read_users_me(async_client: AsyncClient):
    """
    Test for fetching the current user's profile.
    """
    response = await async_client.get("/api/users/@me")
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "testuser"
    assert user_data["id"] == "12345"


@pytest.mark.asyncio
async def test_get_guild_roles(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching guild roles.
    """
    async def mock_fetch_from_discord_api(endpoint: str):
        return [
            {"id": "1", "name": "Admin", "position": 2},
            {"id": "2", "name": "Moderator", "position": 1},
        ]

    monkeypatch.setattr(
        "dashboard.backend.app.api._fetch_from_discord_api",
        mock_fetch_from_discord_api,
    )

    response = await async_client.get("/api/guilds/123/roles")
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) == 2
    assert roles[0]["name"] == "Admin"


@pytest.mark.asyncio
async def test_get_guild_channels(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching guild channels.
    """
    async def mock_fetch_from_discord_api(endpoint: str):
        return [
            {"id": "1", "name": "general", "type": 0, "position": 0},
            {"id": "2", "name": "random", "type": 0, "position": 1},
        ]

    monkeypatch.setattr(
        "dashboard.backend.app.api._fetch_from_discord_api",
        mock_fetch_from_discord_api,
    )

    response = await async_client.get("/api/guilds/123/channels")
    assert response.status_code == 200
    channels = response.json()
    assert len(channels) == 2
    assert channels[0]["name"] == "general"


@pytest.mark.asyncio
async def test_get_general_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching general settings.
    """
    async def mock_get_general_settings(db, guild_id):
        return {"prefix": "!"}

    monkeypatch.setattr(
        "dashboard.backend.app.crud.get_general_settings",
        mock_get_general_settings,
    )

    response = await async_client.get("/api/guilds/123/config/general")
    assert response.status_code == 200
    settings = response.json()
    assert settings["prefix"] == "!"


@pytest.mark.asyncio
async def test_update_general_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for updating general settings.
    """
    async def mock_update_general_settings(db, guild_id, settings_data):
        return {"prefix": settings_data.prefix}

    monkeypatch.setattr(
        "dashboard.backend.app.crud.update_general_settings",
        mock_update_general_settings,
    )

    response = await async_client.put(
        "/api/guilds/123/config/general", json={"prefix": "$"}
    )
    assert response.status_code == 200
    settings = response.json()
    assert settings["prefix"] == "$"


@pytest.mark.asyncio
async def test_get_moderation_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching moderation settings.
    """
    async def mock_get_moderation_settings(db, guild_id):
        return {
            "mod_log_channel_id": "12345",
            "moderator_role_id": "67890",
            "server_rules": "Be nice",
            "action_confirmation_settings": {"ban": "manual"},
            "confirmation_ping_role_id": "54321",
        }

    monkeypatch.setattr(
        "dashboard.backend.app.crud.get_moderation_settings",
        mock_get_moderation_settings,
    )

    response = await async_client.get("/api/guilds/123/config/moderation")
    assert response.status_code == 200
    settings = response.json()
    assert settings["mod_log_channel_id"] == "12345"
    assert settings["moderator_role_id"] == "67890"


@pytest.mark.asyncio
async def test_update_moderation_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for updating moderation settings.
    """
    async def mock_update_moderation_settings(db, guild_id, settings_data):
        return settings_data.dict(exclude_unset=True)

    monkeypatch.setattr(
        "dashboard.backend.app.crud.update_moderation_settings",
        mock_update_moderation_settings,
    )

    update_data = {
        "mod_log_channel_id": "54321",
        "moderator_role_id": "98765",
    }
    response = await async_client.put(
        "/api/guilds/123/config/moderation", json=update_data
    )
    assert response.status_code == 200
    settings = response.json()
    assert settings["mod_log_channel_id"] == "54321"
    assert settings["moderator_role_id"] == "98765"


@pytest.mark.asyncio
async def test_get_logging_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching logging settings.
    """
    async def mock_get_logging_settings(db, guild_id):
        return {
            "log_channel_id": "11111",
            "message_delete_logging": True,
            "message_edit_logging": True,
            "member_join_logging": False,
            "member_leave_logging": False,
        }

    monkeypatch.setattr(
        "dashboard.backend.app.crud.get_logging_settings",
        mock_get_logging_settings,
    )

    response = await async_client.get("/api/guilds/123/config/logging")
    assert response.status_code == 200
    settings = response.json()
    assert settings["log_channel_id"] == "11111"
    assert settings["message_delete_logging"] is True


@pytest.mark.asyncio
async def test_update_logging_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for updating logging settings.
    """
    async def mock_update_logging_settings(db, guild_id, settings_data):
        return settings_data.dict(exclude_unset=True)

    monkeypatch.setattr(
        "dashboard.backend.app.crud.update_logging_settings",
        mock_update_logging_settings,
    )

    update_data = {
        "log_channel_id": "22222",
        "message_delete_logging": False,
    }
    response = await async_client.put(
        "/api/guilds/123/config/logging", json=update_data
    )
    assert response.status_code == 200
    settings = response.json()
    assert settings["log_channel_id"] == "22222"
    assert settings["message_delete_logging"] is False


@pytest.mark.asyncio
async def test_get_security_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching security settings.
    """
    async def mock_get_security_settings(db, guild_id):
        return {
            "bot_detection": {
                "enabled": True, "keywords": ["bot1"], "action": "kick",
                "timeout_duration": 600, "log_channel": "123",
                "whitelist_roles": ["456"], "whitelist_users": ["789"]
            }
        }

    monkeypatch.setattr(
        "dashboard.backend.app.crud.get_security_settings",
        mock_get_security_settings,
    )

    response = await async_client.get("/api/guilds/123/config/security")
    assert response.status_code == 200
    settings = response.json()
    assert settings["bot_detection"]["enabled"] is True


@pytest.mark.asyncio
async def test_get_ai_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching AI settings.
    """
    async def mock_get_ai_settings(db, guild_id):
        return {
            "channel_exclusions": {"excluded_channels": ["123"]},
            "channel_rules": {"channel_rules": {"456": "Be nice"}},
        }
    monkeypatch.setattr("dashboard.backend.app.crud.get_ai_settings", mock_get_ai_settings)

    response = await async_client.get("/api/guilds/123/config/ai")
    assert response.status_code == 200
    settings = response.json()
    assert settings["channel_exclusions"]["excluded_channels"] == ["123"]


@pytest.mark.asyncio
async def test_get_channels_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching channels settings.
    """
    async def mock_get_channels_settings(db, guild_id):
        return {"exclusions": ["123"], "rules": {"456": "Be nice"}}
    monkeypatch.setattr("dashboard.backend.app.crud.get_channels_settings", mock_get_channels_settings)

    response = await async_client.get("/api/guilds/123/config/channels")
    assert response.status_code == 200
    settings = response.json()
    assert settings["exclusions"] == ["123"]


@pytest.mark.asyncio
async def test_get_rate_limiting_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching rate limiting settings.
    """
    async def mock_get_rate_limiting_settings(db, guild_id):
        return {
            "enabled": True, "high_rate_threshold": 10, "low_rate_threshold": 5,
            "high_rate_slowmode": 10, "low_rate_slowmode": 3, "check_interval": 60,
            "analysis_window": 120, "notifications_enabled": True, "notification_channel": "123"
        }
    monkeypatch.setattr("dashboard.backend.app.crud.get_rate_limiting_settings", mock_get_rate_limiting_settings)

    response = await async_client.get("/api/guilds/123/config/rate-limiting")
    assert response.status_code == 200
    settings = response.json()
    assert settings["enabled"] is True


@pytest.mark.asyncio
async def test_get_raid_defense_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching raid defense settings.
    """
    async def mock_get_raid_defense_config(db, guild_id):
        return {"enabled": True, "threshold": 10, "timeframe": 60, "alert_channel": "123", "auto_action": "kick"}
    monkeypatch.setattr("dashboard.backend.app.crud.get_raid_defense_config", mock_get_raid_defense_config)

    response = await async_client.get("/api/guilds/123/config/raid-defense")
    assert response.status_code == 200
    settings = response.json()
    assert settings["enabled"] is True
@pytest.mark.asyncio
async def test_update_security_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for updating security settings.
    """
    async def mock_update_security_settings(db, guild_id, settings):
        return {
            "bot_detection": {
                "enabled": settings.bot_detection.enabled,
                "keywords": ["bot1"], "action": "kick", "timeout_duration": 600,
                "log_channel": "123", "whitelist_roles": ["456"], "whitelist_users": ["789"]
            }
        }
    monkeypatch.setattr("dashboard.backend.app.crud.update_security_settings", mock_update_security_settings)

    update_data = {"bot_detection": {"enabled": False}}
    response = await async_client.put("/api/guilds/123/config/security", json=update_data)
    assert response.status_code == 200
    settings = response.json()
    assert settings["bot_detection"]["enabled"] is False


@pytest.mark.asyncio
async def test_update_ai_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for updating AI settings.
    """
    async def mock_update_ai_settings(db, guild_id, settings):
        return {
            "channel_exclusions": {"excluded_channels": settings.channel_exclusions.excluded_channels},
            "channel_rules": {"channel_rules": settings.channel_rules.channel_rules},
        }
    monkeypatch.setattr("dashboard.backend.app.crud.update_ai_settings", mock_update_ai_settings)

    update_data = {
        "channel_exclusions": {"excluded_channels": ["456"]},
        "channel_rules": {"channel_rules": {"789": "No spam"}},
    }
    response = await async_client.put("/api/guilds/123/config/ai", json=update_data)
    assert response.status_code == 200
    settings = response.json()
    assert settings["channel_exclusions"]["excluded_channels"] == ["456"]


@pytest.mark.asyncio
async def test_update_channels_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for updating channels settings.
    """
    async def mock_update_channels_settings(db, guild_id, settings):
        return {"exclusions": settings.exclusions, "rules": settings.rules}
    monkeypatch.setattr("dashboard.backend.app.crud.update_channels_settings", mock_update_channels_settings)

    update_data = {"exclusions": ["channel1"], "rules": {"channel2": "rule2"}}
    response = await async_client.put("/api/guilds/123/config/channels", json=update_data)
    assert response.status_code == 200
    settings = response.json()
    assert settings["exclusions"] == ["channel1"]


@pytest.mark.asyncio
async def test_update_rate_limiting_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for updating rate limiting settings.
    """
    async def mock_update_rate_limiting_settings(db, guild_id, settings):
        return settings.dict(exclude_unset=True)
    monkeypatch.setattr("dashboard.backend.app.crud.update_rate_limiting_settings", mock_update_rate_limiting_settings)

    update_data = {"enabled": False, "high_rate_threshold": 20}
    response = await async_client.put("/api/guilds/123/config/rate-limiting", json=update_data)
    assert response.status_code == 200
    settings = response.json()
    assert settings["enabled"] is False
    assert settings["high_rate_threshold"] == 20


@pytest.mark.asyncio
async def test_update_raid_defense_settings(async_client: AsyncClient, monkeypatch):
    """
    Test for updating raid defense settings.
    """
    async def mock_update_raid_defense_config(db, guild_id, settings):
        return settings.dict(exclude_unset=True)
    monkeypatch.setattr("dashboard.backend.app.crud.update_raid_defense_config", mock_update_raid_defense_config)

    update_data = {"enabled": False, "threshold": 5}
    response = await async_client.put("/api/guilds/123/config/raid-defense", json=update_data)
    assert response.status_code == 200
    settings = response.json()
    assert settings["enabled"] is False
    assert settings["threshold"] == 5
@pytest.mark.asyncio
async def test_create_blog_post(async_client: AsyncClient, monkeypatch):
    """
    Test for creating a blog post.
    """
    async def mock_get_current_blog_admin():
        return User(id="123", username="admin", discriminator="1234", avatar=None)
    app.dependency_overrides["dashboard.backend.app.api.get_current_blog_admin"] = mock_get_current_blog_admin

    async def mock_create_blog_post(db, post, author_id):
        return {
            "id": 1, "title": post.title, "content": post.content, "slug": post.slug,
            "published": post.published, "author_id": author_id,
            "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00"
        }
    monkeypatch.setattr("dashboard.backend.app.crud.create_blog_post", mock_create_blog_post)

    async def mock_get_blog_post_by_slug(db, slug):
        return None
    monkeypatch.setattr("dashboard.backend.app.crud.get_blog_post_by_slug", mock_get_blog_post_by_slug)

    post_data = {"title": "Test Post", "content": "Test content", "slug": "test-post", "published": True}
    response = await async_client.post("/api/blog/posts", json=post_data)
    assert response.status_code == 200
    post = response.json()
    assert post["title"] == "Test Post"
    del app.dependency_overrides["dashboard.backend.app.api.get_current_blog_admin"]


@pytest.mark.asyncio
async def test_get_blog_posts(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching blog posts.
    """
    async def mock_get_blog_posts(db, skip, limit, published_only):
        return [{"id": 1, "title": "Test Post", "content": "Test content", "slug": "test-post", "published": True, "author_id": 123, "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00"}]
    monkeypatch.setattr("dashboard.backend.app.crud.get_blog_posts", mock_get_blog_posts)

    async def mock_count_blog_posts(db, published_only):
        return 1
    monkeypatch.setattr("dashboard.backend.app.crud.count_blog_posts", mock_count_blog_posts)

    response = await async_client.get("/api/blog/posts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["posts"]) == 1


@pytest.mark.asyncio
async def test_get_blog_post(async_client: AsyncClient, monkeypatch):
    """
    Test for fetching a single blog post.
    """
    async def mock_get_blog_post(db, post_id):
        return {"id": 1, "title": "Test Post", "content": "Test content", "slug": "test-post", "published": True, "author_id": 123, "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00"}
    monkeypatch.setattr("dashboard.backend.app.crud.get_blog_post", mock_get_blog_post)

    response = await async_client.get("/api/blog/posts/1")
    assert response.status_code == 200
    post = response.json()
    assert post["title"] == "Test Post"


@pytest.mark.asyncio
async def test_update_blog_post(async_client: AsyncClient, monkeypatch):
    """
    Test for updating a blog post.
    """
    async def mock_get_current_blog_admin():
        return User(id="123", username="admin", discriminator="1234", avatar=None)
    app.dependency_overrides["dashboard.backend.app.api.get_current_blog_admin"] = mock_get_current_blog_admin

    async def mock_get_blog_post(db, post_id):
        return {"id": 1, "title": "Test Post", "content": "Test content", "slug": "test-post", "published": True, "author_id": 123, "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00"}
    monkeypatch.setattr("dashboard.backend.app.crud.get_blog_post", mock_get_blog_post)

    async def mock_update_blog_post(db, post_id, post_update):
        return {"id": 1, "title": post_update.title, "content": "Test content", "slug": "test-post", "published": True, "author_id": 123, "created_at": "2023-01-01T00:00:00", "updated_at": "2023-01-01T00:00:00"}
    monkeypatch.setattr("dashboard.backend.app.crud.update_blog_post", mock_update_blog_post)

    update_data = {"title": "Updated Post"}
    response = await async_client.put("/api/blog/posts/1", json=update_data)
    assert response.status_code == 200
    post = response.json()
    assert post["title"] == "Updated Post"
    del app.dependency_overrides["dashboard.backend.app.api.get_current_blog_admin"]


@pytest.mark.asyncio
async def test_delete_blog_post(async_client: AsyncClient, monkeypatch):
    """
    Test for deleting a blog post.
    """
    async def mock_get_current_blog_admin():
        return User(id="123", username="admin", discriminator="1234", avatar=None)
    app.dependency_overrides["dashboard.backend.app.api.get_current_blog_admin"] = mock_get_current_blog_admin

    async def mock_delete_blog_post(db, post_id):
        return True
    monkeypatch.setattr("dashboard.backend.app.crud.delete_blog_post", mock_delete_blog_post)

    response = await async_client.delete("/api/blog/posts/1")
    assert response.status_code == 200
    assert response.json() == {"message": "Blog post deleted successfully"}
    del app.dependency_overrides["dashboard.backend.app.api.get_current_blog_admin"]
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

from dashboard.backend.app import api
from dashboard.backend.app.schemas import User


@pytest.mark.asyncio
async def test_handle_rate_limit_retries(monkeypatch):
    calls = {"count": 0}

    async def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise HTTPException(status_code=429, headers={"Retry-After": "0"})
        return "ok"

    async def dummy_sleep(_: float):
        pass

    monkeypatch.setattr(api.asyncio, "sleep", dummy_sleep)
    wrapped = api.handle_rate_limit(flaky)
    result = await wrapped()
    assert result == "ok"
    assert calls["count"] == 3


def test_create_access_token():
    api.SECRET_KEY = "secret"
    token = api.create_access_token(
        {"sub": "user"}, expires_delta=api.timedelta(minutes=1)
    )
    payload = jose_jwt.decode(token, "secret", algorithms=[api.ALGORITHM])
    assert payload["sub"] == "user"
    assert "exp" in payload


def test_is_blog_admin(monkeypatch):
    monkeypatch.setattr(api.config, "OwnersTuple", (1, 2))
    assert api.is_blog_admin(User(id="1", username="x", discriminator="0", avatar=None))
    assert not api.is_blog_admin(
        User(id="3", username="x", discriminator="0", avatar=None)
    )


def test_is_bot_admin(monkeypatch):
    monkeypatch.setattr(api.config, "Owners", SimpleNamespace(OWNER1=1, OWNER2=2))
    assert api.is_bot_admin(User(id="2", username="x", discriminator="0", avatar=None))
    assert not api.is_bot_admin(
        User(id="3", username="x", discriminator="0", avatar=None)
    )


@pytest.mark.asyncio
async def test_fetch_user_guilds_cached(monkeypatch):
    cached = [{"id": "1", "name": "guild"}]
    mock_redis = SimpleNamespace(
        get=AsyncMock(return_value=json.dumps(cached)),
        set=AsyncMock(),
    )
    monkeypatch.setattr(api, "redis_client", mock_redis)
    fetch_mock = AsyncMock()
    monkeypatch.setattr(api, "_fetch_discord_guilds_from_api", fetch_mock)

    result = await api.fetch_user_guilds("token", "123")
    assert result == cached
    fetch_mock.assert_not_called()
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_user_guilds_fetches_and_caches(monkeypatch):
    guilds = [{"id": "1", "name": "guild"}]
    mock_redis = SimpleNamespace(
        get=AsyncMock(return_value=None),
        set=AsyncMock(),
    )
    monkeypatch.setattr(api, "redis_client", mock_redis)
    fetch_mock = AsyncMock(return_value=guilds)
    monkeypatch.setattr(api, "_fetch_discord_guilds_from_api", fetch_mock)

    result = await api.fetch_user_guilds("token", "123")
    assert result == guilds
    fetch_mock.assert_awaited_once_with("token")
    mock_redis.set.assert_any_call("user_guilds:123", json.dumps(guilds), ex=300)
    mock_redis.set.assert_any_call("guild:1", json.dumps(guilds[0]), ex=300)

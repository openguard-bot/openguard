import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from bot import (
    on_member_join,
    on_member_remove,
    update_guild_member_cache,
    update_all_guild_member_caches,
)


@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    member.id = 111
    member.guild = MagicMock(spec=discord.Guild)
    member.guild.id = 999
    return member


@pytest.mark.asyncio
async def test_on_member_join_adds_to_cache(mock_member):
    redis_mock = AsyncMock()
    with patch("bot.get_redis_client", new=AsyncMock(return_value=redis_mock)), patch("builtins.print") as mock_print:
        await on_member_join(mock_member)
        redis_mock.sadd.assert_awaited_once_with("guild:999:members", 111)
        mock_print.assert_called_once_with("Added member 111 to cache for guild 999")


@pytest.mark.asyncio
async def test_on_member_join_no_redis(mock_member):
    with patch("bot.get_redis_client", new=AsyncMock(return_value=None)), patch("builtins.print") as mock_print:
        await on_member_join(mock_member)
        mock_print.assert_not_called()


@pytest.mark.asyncio
async def test_on_member_remove_removes_from_cache(mock_member):
    redis_mock = AsyncMock()
    with patch("bot.get_redis_client", new=AsyncMock(return_value=redis_mock)), patch("builtins.print") as mock_print:
        await on_member_remove(mock_member)
        redis_mock.srem.assert_awaited_once_with("guild:999:members", 111)
        mock_print.assert_called_once_with("Removed member 111 from cache for guild 999")


@pytest.mark.asyncio
async def test_on_member_remove_no_redis(mock_member):
    with patch("bot.get_redis_client", new=AsyncMock(return_value=None)), patch("builtins.print") as mock_print:
        await on_member_remove(mock_member)
        mock_print.assert_not_called()


@pytest.mark.asyncio
async def test_update_guild_member_cache_success():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 42
    guild.name = "Guild"
    guild.members = [MagicMock(id=1), MagicMock(id=2)]

    redis_mock = MagicMock()
    pipe_mock = MagicMock()
    pipe_mock.delete = MagicMock()
    pipe_mock.sadd = MagicMock()
    pipe_mock.execute = AsyncMock()
    redis_mock.pipeline.return_value = pipe_mock

    with patch("bot.get_redis_client", new=AsyncMock(return_value=redis_mock)), patch("builtins.print") as mock_print:
        await update_guild_member_cache(guild)

        redis_mock.pipeline.assert_called_once()
        pipe_mock.delete.assert_called_once_with("guild:42:members")
        pipe_mock.sadd.assert_called_once_with("guild:42:members", "1", "2")
        pipe_mock.execute.assert_awaited_once()
        mock_print.assert_called_once_with("Updated member cache for guild Guild (42) with 2 members.")


@pytest.mark.asyncio
async def test_update_guild_member_cache_no_redis():
    guild = MagicMock(spec=discord.Guild)
    guild.id = 42
    guild.name = "Guild"
    guild.members = []
    with patch("bot.get_redis_client", new=AsyncMock(return_value=None)):
        await update_guild_member_cache(guild)


@pytest.mark.asyncio
async def test_update_all_guild_member_caches():
    guilds = [MagicMock(spec=discord.Guild), MagicMock(spec=discord.Guild)]
    mock_bot = MagicMock()
    mock_bot.guilds = guilds
    with (
        patch("bot.bot", mock_bot),
        patch("bot.update_guild_member_cache", new=AsyncMock()) as mock_update,
        patch("builtins.print") as mock_print,
    ):
        await update_all_guild_member_caches()
        assert mock_update.await_count == 2
        mock_print.assert_any_call("Starting to cache all guild members...")
        mock_print.assert_any_call("Finished caching all guild members.")

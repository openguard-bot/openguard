import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import discord
from discord.ext import commands
from discord.ext.commands import BucketType
from bot import (
    bot,
    get_prefix,
    MyBot,
    DualStream,
    prefix_cache,
    load_cogs,
    send_error_dm,
    catch_exceptions,
    ERROR_NOTIFICATION_USER_ID,
    ERROR_NOTIFICATION_CHANNEL_ID,
    update_bot_guilds_cache,
    update_launch_time_cache,
    prefix_update_listener,
    main,
    on_error,
    on_command_error,
    on_app_command_error,
    on_ready,
    on_guild_join,
    on_guild_remove,
    on_shard_ready,
)
from database.connection import get_pool, initialize_database, close_pool
from database.cache import close_redis, set_cache, get_redis_client
import os
import io
import json
import shutil
import asyncio
import sys
from collections import namedtuple
from discord import app_commands
from lists import config
import traceback


# Mock the config.Owners for testing purposes
class MockOwners:
    ILIKEPANCAKES = 1234567890


config.Owners = MockOwners
bot.ERROR_NOTIFICATION_CHANNEL_ID = None


# Clear the cache before each test that uses it
@pytest.fixture(autouse=True)
def clear_prefix_cache():
    prefix_cache.clear()
    yield
    prefix_cache.clear()


@pytest.fixture
def mock_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    # Create a real MyBot instance to test its methods
    bot = MyBot(command_prefix="!", intents=intents)
    bot._connection = MagicMock()
    bot._connection.user = MagicMock(spec=discord.ClientUser)
    bot.user.id = 9876543210
    bot.loop = asyncio.get_event_loop()  # Assign an event loop for tasks
    return bot


@pytest.fixture
def mock_context(mock_bot):
    ctx = AsyncMock(spec=commands.Context)
    ctx.bot = mock_bot
    ctx.send = AsyncMock()
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.id = 123
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.name = "Test Guild"
    ctx.guild.id = 456
    ctx.channel = MagicMock(spec=discord.TextChannel)
    ctx.command = MagicMock()
    ctx.command.name = "test_command"
    ctx.prefix = "!"
    ctx.invoked_with = "test_command"
    return ctx


@pytest.fixture
def mock_interaction(mock_bot):
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.client = mock_bot
    interaction.response = MagicMock(spec=discord.InteractionResponse)
    interaction.response.send_message = AsyncMock()
    interaction.response.is_done.return_value = False
    interaction.followup = MagicMock(spec=discord.WebhookMessage)
    interaction.followup.send = AsyncMock()
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 789
    interaction.user.name = "testuser"
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.name = "Test Guild"
    interaction.guild.id = 456
    interaction.channel = MagicMock(spec=discord.TextChannel)
    interaction.command = MagicMock()
    interaction.command.name = "test_slash_command"
    return interaction


@pytest.fixture
def temp_cogs_dir(tmp_path):
    """Create a temporary cogs directory for testing."""
    cogs_dir = tmp_path / "cogs"
    cogs_dir.mkdir()
    original_listdir = os.listdir

    def mock_listdir(path):
        if path == "cogs":
            return [f.name for f in cogs_dir.iterdir()]
        return original_listdir(path)

    with patch("os.listdir", side_effect=mock_listdir):
        yield cogs_dir


# Helper to create a mock Discord User/Member
def mock_user(user_id, is_owner_val=False):
    user = MagicMock(spec=discord.User)
    user.id = user_id
    # You might need to mock other attributes depending on what is_owner checks
    return user


# --- MyBot.is_owner Tests ---
@pytest.mark.asyncio
async def test_is_owner_true(mock_bot):
    owner_id = list(config.Owners.__dict__.values())[0]  # Get one of the owner IDs
    user = mock_user(owner_id)
    assert await mock_bot.is_owner(user) is True


@pytest.mark.asyncio
async def test_is_owner_false(mock_bot):
    user = mock_user(9999999999)  # Not an owner ID
    assert await mock_bot.is_owner(user) is False


@pytest.mark.asyncio
async def test_is_owner_none_user(mock_bot):
    with pytest.raises(
        ValueError, match="User/User ID was None, or user object had no ID property"
    ):
        await mock_bot.is_owner(None)


@pytest.mark.asyncio
async def test_is_owner_user_no_id(mock_bot):
    user = MagicMock(spec=discord.User)
    del user.id  # Simulate user object without id
    with pytest.raises(
        ValueError, match="User/User ID was None, or user object had no ID property"
    ):
        await mock_bot.is_owner(user)


# --- DualStream Tests ---
def test_dualstream_write():
    mock_original_stream = MagicMock(spec=io.StringIO)
    mock_log_file = MagicMock(spec=io.StringIO)
    stream = DualStream(mock_original_stream, mock_log_file)

    test_data = "Hello, world!"
    stream.write(test_data)

    mock_original_stream.write.assert_called_once_with(test_data)
    mock_log_file.write.assert_called_once_with(test_data)
    mock_log_file.flush.assert_called_once()


def test_dualstream_flush():
    mock_original_stream = MagicMock(spec=io.StringIO)
    mock_log_file = MagicMock(spec=io.StringIO)
    stream = DualStream(mock_original_stream, mock_log_file)

    stream.flush()

    mock_original_stream.flush.assert_called_once()
    mock_log_file.flush.assert_called_once()


# --- get_prefix Tests (from original file, kept for completeness) ---
@pytest.mark.asyncio
async def test_get_prefix_from_db(mock_bot):
    mock_message = MagicMock()
    mock_message.guild = MagicMock()
    mock_message.guild.id = 12345
    mock_message.guild.name = "Test Guild"

    with patch("bot.get_pool", new_callable=AsyncMock) as mock_get_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = json.dumps("test!")  # Ensure JSON string
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        prefix = await get_prefix(mock_bot, mock_message)
        assert prefix == "test!"
        mock_conn.fetchval.assert_called_once_with(
            "SELECT value FROM guild_settings WHERE guild_id = $1 AND key = 'prefix'",
            12345,
        )
        assert prefix_cache[12345] == "test!"


@pytest.mark.asyncio
async def test_get_prefix_default(mock_bot):
    mock_message = MagicMock()
    mock_message.guild = MagicMock()
    mock_message.guild.id = 67890
    mock_message.guild.name = "Another Test Guild"

    with patch("bot.get_pool", new_callable=AsyncMock) as mock_get_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = None
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        prefix = await get_prefix(mock_bot, mock_message)
        assert prefix == "o!"
        mock_conn.fetchval.assert_called_once_with(
            "SELECT value FROM guild_settings WHERE guild_id = $1 AND key = 'prefix'",
            67890,
        )
        assert prefix_cache[67890] == "o!"


@pytest.mark.asyncio
async def test_get_prefix_caching(mock_bot):
    mock_message = MagicMock()
    mock_message.guild = MagicMock()
    mock_message.guild.id = 112233
    mock_message.guild.name = "Cached Guild"

    with patch("bot.get_pool", new_callable=AsyncMock) as mock_get_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = json.dumps("cached!")
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        # First call, should hit DB and cache
        prefix1 = await get_prefix(mock_bot, mock_message)
        assert prefix1 == "cached!"
        mock_get_pool.assert_called_once()  # DB was called

        # Second call, should hit cache, not DB
        mock_get_pool.reset_mock()  # Reset mock to check if it's called again
        prefix2 = await get_prefix(mock_bot, mock_message)
        assert prefix2 == "cached!"
        mock_get_pool.assert_not_called()  # DB should not be called again


@pytest.mark.asyncio
async def test_get_prefix_no_guild(mock_bot):
    mock_message = MagicMock()
    mock_message.guild = None  # Simulate DM

    prefix = await get_prefix(mock_bot, mock_message)
    assert prefix == "o!"
    assert not prefix_cache  # Should not cache for DMs


@pytest.mark.asyncio
async def test_get_prefix_no_pool(mock_bot):
    mock_message = MagicMock()
    mock_message.guild = MagicMock()
    mock_message.guild.id = 98765

    with patch(
        "bot.get_pool", new_callable=AsyncMock, return_value=None
    ) as mock_get_pool:
        prefix = await get_prefix(mock_bot, mock_message)
        assert prefix == "o!"
        mock_get_pool.assert_called_once()
        assert 98765 not in prefix_cache  # Should not cache if pool is None


# --- prefix_update_listener Tests ---
@pytest.mark.asyncio
async def test_prefix_update_listener_updates_cache():
    mock_redis = AsyncMock()
    mock_pubsub = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    # Simulate receiving two messages
    async def get_message_mock(ignore_subscribe_messages, timeout):
        if get_message_mock.call_count == 0:
            get_message_mock.call_count += 1
            return {"type": "message", "data": b'123: "new_prefix!"'}
        elif get_message_mock.call_count == 1:
            get_message_mock.call_count += 1
            return {"type": "message", "data": b'456: "another_prefix?"'}
        else:
            raise asyncio.CancelledError  # To stop the loop

    get_message_mock.call_count = 0
    mock_pubsub.get_message.side_effect = get_message_mock

    with patch(
        "bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ), patch("builtins.print") as mock_print:

        # We create a task for the listener and then cancel it to stop the infinite loop
        listener_task = asyncio.create_task(prefix_update_listener())

        # Give the listener a moment to process messages
        await asyncio.sleep(0.1)

        # Cancel the task to prevent it from running forever
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass  # Expected cancellation

        mock_pubsub.subscribe.assert_called_once_with("prefix_updates")
        assert prefix_cache[123] == "new_prefix!"
        assert prefix_cache[456] == "another_prefix?"
        mock_print.assert_any_call("Updated prefix for guild 123 to 'new_prefix!'")
        mock_print.assert_any_call("Updated prefix for guild 456 to 'another_prefix?'")


@pytest.mark.asyncio
async def test_prefix_update_listener_no_redis():
    with patch(
        "bot.get_redis_client", new_callable=AsyncMock, return_value=None
    ) as mock_get_redis_client, patch("builtins.print") as mock_print:
        await prefix_update_listener()
        mock_print.assert_called_once_with(
            "Redis not available, prefix update listener will not run."
        )
        mock_get_redis_client.assert_called_once()


@pytest.mark.asyncio
async def test_prefix_update_listener_handles_error():
    mock_redis = AsyncMock()
    mock_pubsub = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    # Simulate an error after one message, then a cancellation to stop the loop
    async def get_message_error_mock(ignore_subscribe_messages, timeout):
        if get_message_error_mock.call_count == 0:
            get_message_error_mock.call_count += 1
            return {"type": "message", "data": b'123: "new_prefix!"'}
        elif get_message_error_mock.call_count == 1:
            get_message_error_mock.call_count += 1
            raise Exception("Simulated pubsub error")
        else:
            raise asyncio.CancelledError

    get_message_error_mock.call_count = 0
    mock_pubsub.get_message.side_effect = get_message_error_mock

    with patch(
        "bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
    ), patch("builtins.print") as mock_print:

        listener_task = asyncio.create_task(prefix_update_listener())

        # The internal mock will now raise CancelledError, so we just await the task.
        try:
            await asyncio.wait_for(listener_task, timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass  # Task is expected to be cancelled or finish

        mock_print.assert_any_call(
            "Error in prefix_update_listener: Simulated pubsub error"
        )
        assert prefix_cache[123] == "new_prefix!"


# --- send_error_dm Tests ---
@pytest.mark.asyncio
async def test_send_error_dm_success(mock_bot):
    mock_user_obj = AsyncMock(spec=discord.User)
    mock_user_obj.send = AsyncMock()
    mock_bot.fetch_user = AsyncMock(return_value=mock_user_obj)

    error_type = "TestError"
    error_message = "Something went wrong."
    error_traceback = "Traceback data."
    context_info = "Context details."

    with patch("bot.ERROR_NOTIFICATION_CHANNEL_ID", None):
        await send_error_dm(
            mock_bot, error_type, error_message, error_traceback, context_info
        )

    mock_bot.fetch_user.assert_called_once_with(ERROR_NOTIFICATION_USER_ID)
    expected_content = (
        f"**Error Type:** {error_type}\n"
        f"**Error Message:** {error_message}\n"
        f"**Context:** {context_info}\n"
        f"**Traceback:**\n```\n{error_traceback}\n```"
    )
    mock_user_obj.send.assert_called_once_with(expected_content)


@pytest.mark.asyncio
async def test_send_error_dm_no_user(mock_bot):
    mock_bot.fetch_user = AsyncMock(return_value=None)  # Simulate user not found

    with patch("bot.ERROR_NOTIFICATION_CHANNEL_ID", None), patch(
        "builtins.print"
    ) as mock_print:
        await send_error_dm(mock_bot, "Type", "Message")

    mock_bot.fetch_user.assert_called_once_with(ERROR_NOTIFICATION_USER_ID)
    mock_print.assert_called_once()
    assert "Could not find user with ID" in mock_print.call_args[0][0]


@pytest.mark.asyncio
async def test_send_error_dm_truncates_traceback(mock_bot):
    mock_user_obj = AsyncMock(spec=discord.User)
    mock_user_obj.send = AsyncMock()
    mock_bot.fetch_user = AsyncMock(return_value=mock_user_obj)

    long_traceback = "A" * 2000  # Longer than 1500 limit

    with patch("bot.ERROR_NOTIFICATION_CHANNEL_ID", None):
        await send_error_dm(mock_bot, "Type", "Message", long_traceback)

    sent_content = mock_user_obj.send.call_args[0][0]
    assert len(sent_content) < 1500 + 100  # Rough check for truncation
    assert sent_content.endswith("...(truncated)\n```")
    assert sent_content.count("A") == 1500


@pytest.mark.asyncio
async def test_send_error_dm_handles_dm_error(mock_bot):
    mock_user_obj = AsyncMock(spec=discord.User)
    mock_user_obj.send.side_effect = Exception("DM send error")
    mock_bot.fetch_user = AsyncMock(return_value=mock_user_obj)

    with patch("bot.bot", new=mock_bot), patch("builtins.print") as mock_print:
        await send_error_dm(mock_bot, "Type", "Message")

    mock_print.assert_called_once()
    assert "Failed to send error DM" in mock_print.call_args[0][0]


@pytest.mark.asyncio
async def test_send_error_dm_sends_to_channel(mock_bot):
    mock_channel_obj = AsyncMock(spec=discord.TextChannel)
    mock_channel_obj.send = AsyncMock()
    mock_bot.get_channel = MagicMock(return_value=None)
    mock_bot.fetch_channel = AsyncMock(return_value=mock_channel_obj)
    mock_bot.fetch_user = AsyncMock()

    with patch("bot.bot", new=mock_bot), patch(
        "bot.ERROR_NOTIFICATION_CHANNEL_ID", 999
    ):
        await send_error_dm(mock_bot, "Type", "Message")

    mock_bot.get_channel.assert_called_once_with(999)
    mock_bot.fetch_channel.assert_called_once_with(999)
    mock_channel_obj.send.assert_called_once()
    mock_bot.fetch_user.assert_not_called()


# --- catch_exceptions decorator Tests ---
@pytest.mark.asyncio
async def test_catch_exceptions_no_error(mock_bot):
    mock_func = AsyncMock(return_value="success")
    wrapped_func = catch_exceptions(mock_func)
    mock_bot.fetch_user = AsyncMock()

    with patch("bot.bot", new=mock_bot):
        result = await wrapped_func()

    mock_func.assert_called_once()
    assert result == "success"
    mock_bot.fetch_user.assert_not_called()  # No error, no DM


@pytest.mark.asyncio
async def test_catch_exceptions_sends_dm_on_error(mock_bot):
    # The function being decorated must have a __name__ and __module__
    async def mock_func():
        raise ValueError("Test exception")

    mock_func.__module__ = "test_bot"  # Manually set module for consistent test results

    wrapped_func = catch_exceptions(mock_func)

    mock_user_obj = AsyncMock(spec=discord.User)
    mock_user_obj.send = AsyncMock()
    mock_bot.fetch_user = AsyncMock(return_value=mock_user_obj)

    with patch("bot.bot", new=mock_bot), patch(
        "bot.ERROR_NOTIFICATION_CHANNEL_ID", None
    ), patch(
        "sys.exc_info", return_value=(ValueError, ValueError("Test exception"), None)
    ), patch(
        "traceback.format_exception",
        return_value=["Traceback line 1\n", "Traceback line 2\n"],
    ):

        with pytest.raises(ValueError, match="Test exception"):
            await wrapped_func()

    mock_bot.fetch_user.assert_called_once_with(ERROR_NOTIFICATION_USER_ID)
    mock_user_obj.send.assert_called_once()
    sent_content = mock_user_obj.send.call_args[0][0]
    assert "**Error Type:** ValueError" in sent_content
    assert "**Error Message:** Test exception" in sent_content
    assert (
        "**Context:** Function: mock_func, Module: test_bot" in sent_content
    )  # Module name changes based on where test is run
    assert (
        "**Traceback:**\n```\nTraceback line 1\nTraceback line 2\n```" in sent_content
    )


@pytest.mark.asyncio
async def test_catch_exceptions_with_self_and_bot_attribute(mock_bot):
    class MockCog:
        def __init__(self, bot_instance):
            self.bot = bot_instance

        @catch_exceptions
        async def my_method(self):
            raise TypeError("Cog error")

    cog_instance = MockCog(mock_bot)

    mock_user_obj = AsyncMock(spec=discord.User)
    mock_user_obj.send = AsyncMock()
    mock_bot.fetch_user = AsyncMock(return_value=mock_user_obj)

    with patch("bot.bot", new=mock_bot), patch(
        "bot.ERROR_NOTIFICATION_CHANNEL_ID", None
    ):
        with pytest.raises(TypeError, match="Cog error"):
            await cog_instance.my_method()

    mock_bot.fetch_user.assert_called_once_with(ERROR_NOTIFICATION_USER_ID)
    sent_content = mock_user_obj.send.call_args[0][0]
    assert "**Error Type:** TypeError" in sent_content
    assert "**Error Message:** Cog error" in sent_content
    assert (
        "**Context:** Function: my_method, Module: tests.test_bot, Class: MockCog"
        in sent_content
    )


@pytest.mark.asyncio
async def test_catch_exceptions_with_bot_instance_as_arg(mock_bot):
    # The function being decorated must have a __name__ and __module__
    @catch_exceptions
    async def my_function(bot_instance):
        """A docstring."""
        raise IndexError("List out of bounds")

    my_function.__module__ = (
        "test_bot"  # Manually set module for consistent test results
    )

    mock_user_obj = AsyncMock(spec=discord.User)
    mock_user_obj.send = AsyncMock()
    mock_bot.fetch_user = AsyncMock(return_value=mock_user_obj)

    with patch("bot.bot", new=mock_bot), patch(
        "bot.ERROR_NOTIFICATION_CHANNEL_ID", None
    ):
        with pytest.raises(IndexError, match="List out of bounds"):
            await my_function(mock_bot)

    mock_bot.fetch_user.assert_called_once_with(ERROR_NOTIFICATION_USER_ID)
    sent_content = mock_user_obj.send.call_args[0][0]
    assert "**Error Type:** IndexError" in sent_content
    assert "**Error Message:** List out of bounds" in sent_content
    assert "**Context:** Function: my_function, Module: tests.test_bot" in sent_content


# --- load_cogs Tests ---
@pytest.mark.asyncio
async def test_load_cogs_success(mock_bot, temp_cogs_dir):
    mock_bot.load_extension = AsyncMock()

    # Create dummy cog files in the temporary directory
    (temp_cogs_dir / "test_cog1.py").write_text("# dummy cog")
    (temp_cogs_dir / "test_cog2.py").write_text("# dummy cog")
    (temp_cogs_dir / "aimod.py").write_text("# excluded cog")
    (temp_cogs_dir / "_ignored.py").write_text("# ignored cog")

    with patch("bot.bot", new=mock_bot), patch("builtins.print") as mock_print, patch(
        "bot.send_error_dm", new=AsyncMock()
    ) as mock_send_error_dm:

        await load_cogs()

        mock_bot.load_extension.assert_has_calls(
            [call("cogs.test_cog1"), call("cogs.test_cog2")], any_order=True
        )
        assert mock_bot.load_extension.call_count == 2
        mock_print.assert_any_call("Loaded cog: test_cog1")
        mock_print.assert_any_call("Loaded cog: test_cog2")
        mock_send_error_dm.assert_not_called()


@pytest.mark.asyncio
async def test_load_cogs_failure(mock_bot, temp_cogs_dir):
    mock_bot.load_extension = AsyncMock(side_effect=Exception("Load error"))

    (temp_cogs_dir / "failing_cog.py").write_text("# dummy failing cog")

    with patch("bot.bot", new=mock_bot), patch("builtins.print") as mock_print, patch(
        "bot.send_error_dm", new=AsyncMock()
    ) as mock_send_error_dm:

        await load_cogs()

        mock_bot.load_extension.assert_called_once_with("cogs.failing_cog")
        mock_print.assert_any_call("Failed to load cog failing_cog: Load error")
        mock_send_error_dm.assert_called_once()
        sent_args, sent_kwargs = mock_send_error_dm.call_args
        assert sent_kwargs["error_type"] == "Exception"
        assert sent_kwargs["error_message"] == "Load error"
        assert "Error loading cog: failing_cog" in sent_kwargs["context_info"]


@pytest.mark.asyncio
async def test_load_cogs_send_error_dm_failure(mock_bot, temp_cogs_dir):
    mock_bot.load_extension = AsyncMock(side_effect=Exception("Load error"))

    (temp_cogs_dir / "failing_cog.py").write_text("# dummy failing cog")

    with patch("bot.bot", new=mock_bot), patch("builtins.print") as mock_print, patch(
        "bot.send_error_dm", new=AsyncMock(side_effect=Exception("DM error"))
    ) as mock_send_error_dm:

        await load_cogs()

        mock_send_error_dm.assert_called_once()
        mock_print.assert_any_call(
            "Failed to send error DM for cog loading error: DM error"
        )


# --- on_error Tests ---
@pytest.mark.asyncio
async def test_on_error_sends_dm(mock_bot):
    mock_send_error_dm = AsyncMock()
    mock_sys_exc_info = MagicMock(
        return_value=(ValueError, ValueError("Event error"), MagicMock())
    )
    mock_traceback_format_exception = MagicMock(return_value=["Event Traceback\n"])

    with patch("bot.send_error_dm", new=mock_send_error_dm), patch(
        "sys.exc_info", new=mock_sys_exc_info
    ), patch("traceback.format_exception", new=mock_traceback_format_exception), patch(
        "builtins.print"
    ) as mock_print:

        # We need to patch the global bot object for the event handler to use it
        with patch("bot.bot", new=mock_bot):
            await on_error("on_message", "arg1", kwarg1="val1")

        mock_print.assert_any_call("Error in event on_message:")
        mock_print.assert_any_call("Event Traceback\n")
        mock_send_error_dm.assert_called_once()
        sent_args, sent_kwargs = mock_send_error_dm.call_args
        assert sent_kwargs["error_type"] == "ValueError"
        assert sent_kwargs["error_message"] == "Event error"
        assert (
            "Event: on_message, Args: ('arg1',), Kwargs: {'kwarg1': 'val1'}"
            in sent_kwargs["context_info"]
        )
        assert sent_kwargs["error_traceback"] == "Event Traceback\n"


# --- on_command_error Tests ---
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_type, user_message_part, should_notify",
    [
        (commands.CommandNotFound("test"), "Command `test_command` not found.", False),
        (
            commands.MissingRequiredArgument(
                param=namedtuple("Param", "name displayed_name")("arg", "arg")
            ),
            "Missing required argument: `arg`.",
            False,
        ),
        (commands.BadArgument("bad arg"), "Invalid argument provided.", False),
        (commands.TooManyArguments(), "Too many arguments provided.", False),
        (
            commands.MissingPermissions(["kick_members"]),
            "Required permissions: kick_members",
            False,
        ),
        (
            commands.BotMissingPermissions(["send_messages"]),
            "Missing permissions: send_messages",
            False,
        ),
        (
            commands.NoPrivateMessage(),
            "This command cannot be used in private messages.",
            False,
        ),
        (
            commands.PrivateMessageOnly(),
            "This command can only be used in private messages.",
            False,
        ),
        (
            commands.NotOwner("Not owner"),
            "This command can only be used by the bot owner.",
            False,
        ),
        (
            commands.CommandOnCooldown(MagicMock(), 10.0, BucketType.default),
            "Try again in 10.00 seconds.",
            False,
        ),
        (
            commands.DisabledCommand("disabled"),
            "This command is currently disabled.",
            False,
        ),
        (
            commands.CheckFailure("check failed"),
            "You don't have permission to use this command.",
            False,
        ),
        (
            Exception("Generic error"),
            "An error occurred while executing the command. The bot owner has been notified.",
            True,
        ),
    ],
)
async def test_on_command_error_handles_known_errors(
    mock_bot, mock_context, error_type, user_message_part, should_notify
):
    mock_send_error_dm = AsyncMock()
    with patch("bot.send_error_dm", new=mock_send_error_dm), patch(
        "builtins.print"
    ) as mock_print:

        await on_command_error(mock_context, error_type)

        mock_context.send.assert_called_once()
        assert user_message_part in mock_context.send.call_args[0][0]

        if should_notify:
            mock_send_error_dm.assert_called_once()
            sent_args, sent_kwargs = mock_send_error_dm.call_args
            assert sent_kwargs["error_type"] == type(error_type).__name__
            assert sent_kwargs["error_message"] == str(error_type)
            assert (
                f"Command: {mock_context.command.name}" in sent_kwargs["context_info"]
            )
            assert f"Author: {mock_context.author}" in sent_kwargs["context_info"]
        else:
            mock_send_error_dm.assert_not_called()


@pytest.mark.asyncio
async def test_on_command_error_send_message_failure(mock_bot, mock_context):
    mock_context.send.side_effect = Exception("Send message error")
    mock_send_error_dm = AsyncMock()

    with patch("bot.send_error_dm", new=mock_send_error_dm), patch(
        "builtins.print"
    ) as mock_print:

        await on_command_error(mock_context, commands.CommandNotFound("test"))

        mock_context.send.assert_called_once()
        # No error should be re-raised, just print
        mock_print.assert_not_called()  # send_error_dm is not called for CommandNotFound


@pytest.mark.asyncio
async def test_on_command_error_original_error(mock_bot, mock_context):
    original_error = ValueError("Original error")
    error_with_original = commands.CommandInvokeError(original_error)

    mock_send_error_dm = AsyncMock()
    with patch("bot.send_error_dm", new=mock_send_error_dm), patch(
        "builtins.print"
    ) as mock_print:

        await on_command_error(mock_context, error_with_original)

        mock_context.send.assert_called_once()
        assert "An error occurred" in mock_context.send.call_args[0][0]

        mock_send_error_dm.assert_called_once()
        sent_args, sent_kwargs = mock_send_error_dm.call_args
        assert sent_kwargs["error_type"] == "ValueError"
        assert sent_kwargs["error_message"] == "Original error"


# --- on_app_command_error Tests ---
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_type, user_message_part, should_notify",
    [
        (
            app_commands.CommandNotFound("test", parents=[]),
            "Command `test` not found.",
            False,
        ),
        (
            app_commands.MissingPermissions(["kick_members"]),
            "You are missing the following required permissions: kick_members",
            False,
        ),
        (
            app_commands.BotMissingPermissions(["send_messages"]),
            "I don't have the required permissions to execute this command. Missing permissions: send_messages",
            False,
        ),
        (
            app_commands.NoPrivateMessage(),
            "This command cannot be used in private messages.",
            False,
        ),
        (
            app_commands.CommandOnCooldown(MagicMock(), 10.0),
            "This command is on cooldown. Try again in 10.00 seconds.",
            False,
        ),
        (
            app_commands.CheckFailure("check failed"),
            "You don't have permission to use this command.",
            False,
        ),
        (
            app_commands.TransformerError(
                MagicMock(),
                MagicMock(),
                MagicMock(type=discord.AppCommandOptionType.string),
            ),
            "Invalid input provided:",
            False,
        ),
        (
            commands.MissingRequiredArgument(
                param=namedtuple("Param", "name displayed_name")("arg", "arg")
            ),
            "Missing required argument: `arg`.",
            False,
        ),
        (commands.BadArgument("bad arg"), "Invalid argument provided.", False),
        (
            commands.NotOwner("Not owner"),
            "This command can only be used by the bot owner.",
            False,
        ),
        (
            Exception("Generic app error"),
            "An error occurred while executing the command. The bot owner has been notified.",
            True,
        ),
    ],
)
async def test_on_app_command_error_handles_known_errors(
    mock_bot, mock_interaction, error_type, user_message_part, should_notify
):
    mock_send_error_dm = AsyncMock()
    with patch("bot.send_error_dm", new=mock_send_error_dm), patch(
        "builtins.print"
    ) as mock_print:

        # We need to patch the global bot object for the event handler to use it
        with patch("bot.bot", new=mock_bot):
            await on_app_command_error(mock_interaction, error_type)

        mock_interaction.response.send_message.assert_called_once()
        assert (
            user_message_part in mock_interaction.response.send_message.call_args[0][0]
        )

        if should_notify:
            mock_send_error_dm.assert_called_once()
            sent_args, sent_kwargs = mock_send_error_dm.call_args
            assert sent_kwargs["error_type"] == type(error_type).__name__
            assert sent_kwargs["error_message"] == str(error_type)
            assert (
                f"Command: {mock_interaction.command.name}"
                in sent_kwargs["context_info"]
            )
            assert f"Author: {mock_interaction.user}" in sent_kwargs["context_info"]
        else:
            mock_send_error_dm.assert_not_called()


@pytest.mark.asyncio
async def test_on_app_command_error_already_responded(mock_bot, mock_interaction):
    mock_interaction.response.is_done.return_value = (
        True  # Simulate response already done
    )
    mock_send_error_dm = AsyncMock()

    with patch("bot.send_error_dm", new=mock_send_error_dm), patch(
        "builtins.print"
    ) as mock_print:

        with patch("bot.bot", new=mock_bot):
            await on_app_command_error(
                mock_interaction, app_commands.CheckFailure("check failed")
            )

        mock_interaction.response.send_message.assert_not_called()
        mock_interaction.followup.send.assert_called_once()
        assert (
            "You don't have permission"
            in mock_interaction.followup.send.call_args[0][0]
        )
        mock_send_error_dm.assert_not_called()


@pytest.mark.asyncio
async def test_on_app_command_error_send_message_failure(mock_bot, mock_interaction):
    mock_interaction.response.send_message.side_effect = Exception("Send message error")
    mock_send_error_dm = AsyncMock()

    with patch("bot.send_error_dm", new=mock_send_error_dm), patch(
        "builtins.print"
    ) as mock_print:

        with patch("bot.bot", new=mock_bot):
            await on_app_command_error(
                mock_interaction, app_commands.CommandNotFound("test", parents=[])
            )

        mock_interaction.response.send_message.assert_called_once()
        # No error should be re-raised, just print
        mock_print.assert_not_called()  # send_error_dm is not called for CommandNotFound


@pytest.mark.asyncio
async def test_on_app_command_error_original_error(mock_bot, mock_interaction):
    original_error = ValueError("Original app error")
    error_with_original = app_commands.AppCommandError(original_error)

    mock_send_error_dm = AsyncMock()
    with patch("bot.send_error_dm", new=mock_send_error_dm), patch(
        "builtins.print"
    ) as mock_print:

        with patch("bot.bot", new=mock_bot):
            await on_app_command_error(mock_interaction, error_with_original)

        mock_interaction.response.send_message.assert_called_once()
        assert (
            "An error occurred"
            in mock_interaction.response.send_message.call_args[0][0]
        )

        mock_send_error_dm.assert_called_once()
        sent_args, sent_kwargs = mock_send_error_dm.call_args
        assert sent_kwargs["error_type"] == "AppCommandError"
        assert sent_kwargs["error_message"] == "Original app error"


# --- on_ready Tests ---
@pytest.mark.asyncio
async def test_on_ready_success(mock_bot):
    mock_bot.tree.sync = AsyncMock()
    mock_bot.launch_time = discord.utils.utcnow()

    with patch.object(
        type(mock_bot), "guilds", [MagicMock(id=1), MagicMock(id=2)]
    ), patch("bot.bot", new=mock_bot), patch("builtins.print") as mock_print, patch(
        "bot.send_error_dm", new=AsyncMock()
    ) as mock_send_error_dm, patch(
        "bot.update_bot_guilds_cache", new=AsyncMock()
    ) as mock_update_guilds, patch(
        "bot.update_launch_time_cache", new=AsyncMock()
    ) as mock_update_launch_time:

        await on_ready()

        mock_bot.tree.sync.assert_called_once()
        mock_print.assert_any_call("Commands synced successfully!")
        mock_print.assert_any_call(f"Logged in as {mock_bot.user}")
        mock_update_guilds.assert_called_once()
        mock_update_launch_time.assert_called_once()
        # mock_create_task.assert_called_once() # This is now handled by the global fixture
        mock_send_error_dm.assert_not_called()


@pytest.mark.asyncio
async def test_on_ready_sync_failure(mock_bot):
    mock_bot.tree.sync = AsyncMock(side_effect=Exception("Sync error"))
    mock_bot.launch_time = discord.utils.utcnow()

    with patch.object(type(mock_bot), "guilds", []), patch(
        "bot.bot", new=mock_bot
    ), patch("builtins.print") as mock_print, patch(
        "bot.send_error_dm", new=AsyncMock()
    ) as mock_send_error_dm, patch(
        "bot.update_bot_guilds_cache", new=AsyncMock()
    ), patch(
        "bot.update_launch_time_cache", new=AsyncMock()
    ):
        # patch('bot.bot.loop.create_task') as mock_create_task: # This is now handled by the global fixture

        await on_ready()

        mock_bot.tree.sync.assert_called_once()
        mock_print.assert_any_call("Failed to sync commands: Sync error")
        mock_send_error_dm.assert_called_once()
        sent_args, sent_kwargs = mock_send_error_dm.call_args
        assert sent_kwargs["error_type"] == "Exception"
        assert sent_kwargs["error_message"] == "Sync error"
        assert (
            "Error occurred during command sync in on_ready event"
            in sent_kwargs["context_info"]
        )
        # mock_create_task.assert_called_once() # This is now handled by the global fixture


# --- update_bot_guilds_cache Tests ---
@pytest.mark.asyncio
async def test_update_bot_guilds_cache(mock_bot):
    mock_set_cache = AsyncMock()

    with patch.object(
        type(mock_bot), "guilds", [MagicMock(id=123), MagicMock(id=456)]
    ), patch("bot.bot", new=mock_bot), patch(
        "bot.set_cache", new=mock_set_cache
    ), patch(
        "builtins.print"
    ) as mock_print:

        await update_bot_guilds_cache()

        mock_set_cache.assert_called_once_with("bot_guilds", [123, 456])
        mock_print.assert_called_once_with("Updated bot guilds cache.")


# --- update_launch_time_cache Tests ---
@pytest.mark.asyncio
async def test_update_launch_time_cache(mock_bot):
    mock_bot.launch_time = discord.utils.utcnow()
    mock_set_cache = AsyncMock()

    with patch("bot.bot", new=mock_bot), patch(
        "bot.set_cache", new=mock_set_cache
    ), patch("builtins.print") as mock_print:

        await update_launch_time_cache()

        mock_set_cache.assert_called_once_with(
            "bot_launch_time", mock_bot.launch_time.timestamp()
        )
        mock_print.assert_called_once_with("Updated bot launch time cache.")


# --- on_guild_join Tests ---
@pytest.mark.asyncio
async def test_on_guild_join(mock_bot):
    mock_guild = MagicMock(spec=discord.Guild)
    mock_guild.name = "New Guild"
    mock_guild.id = 789
    mock_update_bot_guilds_cache = AsyncMock()

    with patch("bot.bot", new=mock_bot), patch(
        "bot.update_bot_guilds_cache", new=AsyncMock()
    ) as mock_update_bot_guilds_cache, patch("builtins.print") as mock_print:

        await on_guild_join(mock_guild)

        mock_print.assert_called_once_with(
            f"Joined guild: {mock_guild.name} ({mock_guild.id})"
        )
        mock_update_bot_guilds_cache.assert_called_once()


# --- on_guild_remove Tests ---
@pytest.mark.asyncio
async def test_on_guild_remove(mock_bot):
    mock_guild = MagicMock(spec=discord.Guild)
    mock_guild.name = "Removed Guild"
    mock_guild.id = 1011
    mock_update_bot_guilds_cache = AsyncMock()

    with patch("bot.bot", new=mock_bot), patch(
        "bot.update_bot_guilds_cache", new=mock_update_bot_guilds_cache
    ), patch("builtins.print") as mock_print:

        await on_guild_remove(mock_guild)

        mock_print.assert_called_once_with(
            f"Removed from guild: {mock_guild.name} ({mock_guild.id})"
        )
        mock_update_bot_guilds_cache.assert_called_once()


# --- on_shard_ready Tests ---
@pytest.mark.asyncio
async def test_on_shard_ready(mock_bot):
    shard_id = 0
    with patch("builtins.print") as mock_print:
        await on_shard_ready(shard_id)
        mock_print.assert_called_once_with(f"Shard {shard_id} is ready.")


# --- test_error command Tests ---
@pytest.mark.asyncio
async def test_test_error_command(mock_context):
    # Define the command function
    @commands.command(name="testerror")
    async def test_error(ctx):
        await ctx.send(f"Testing error handling in {ctx.command}...")
        raise ValueError("This is a test error to verify error handling")

    # The on_command_error handler uses the global `bot` object, so we must add the command to it
    # and then clean it up afterwards to not interfere with other tests.
    # with patch('asyncio.create_task'): # Prevent prefix_update_listener from being created - now handled by global fixture
    try:
        mock_context.bot.add_command(test_error)

        # Ensure the command is found before executing
        command = mock_context.bot.get_command("testerror")
        assert command is not None

        # Execute the command, which should raise the error
        with pytest.raises(
            ValueError, match="This is a test error to verify error handling"
        ):
            await command.callback(mock_context)

        mock_context.send.assert_called_once_with(
            f"Testing error handling in {mock_context.command}..."
        )

    finally:
        # Cleanup: remove the command from the global bot
        mock_context.bot.remove_command("testerror")


# --- test_error_slash command Tests ---
@pytest.mark.asyncio
async def test_test_error_slash_command(mock_interaction):
    # Define the slash command function
    @app_commands.command(name="testerror_slash", description="Test slash command")
    async def test_error_slash(interaction: discord.Interaction):
        await interaction.response.send_message(
            "Testing error handling in slash command..."
        )
        raise ValueError("This is a test error to verify slash command error handling")

    # The on_app_command_error handler uses the global `bot` object's tree, so we add the command there
    try:
        mock_interaction.client.tree.add_command(test_error_slash)

        # Manually set the command for the interaction mock
        command = mock_interaction.client.tree.get_command("testerror_slash")
        mock_interaction.command = command
        assert command is not None

        # Execute the command callback, which should raise the error
        with pytest.raises(
            ValueError,
            match="This is a test error to verify slash command error handling",
        ):
            await command.callback(mock_interaction)

        mock_interaction.response.send_message.assert_called_once_with(
            "Testing error handling in slash command..."
        )

    finally:
        # Cleanup: remove the command from the global bot's tree
        mock_interaction.client.tree.remove_command("testerror_slash")


# --- main function tests ---
@pytest.mark.asyncio
async def test_main_success():
    with patch(
        "bot.initialize_database", new_callable=AsyncMock, return_value=True
    ) as mock_init_db, patch(
        "bot.load_cogs", new_callable=AsyncMock
    ) as mock_load_cogs, patch(
        "bot.bot.start", new_callable=AsyncMock
    ) as mock_bot_start, patch(
        "bot.close_pool", new_callable=AsyncMock
    ) as mock_close_pool, patch(
        "bot.close_redis", new_callable=AsyncMock
    ) as mock_close_redis, patch(
        "builtins.print"
    ) as mock_print, patch(
        "os.getenv"
    ) as mock_getenv:

        mock_getenv.return_value = "FAKE_TOKEN"
        await main()

        mock_init_db.assert_called_once()
        mock_load_cogs.assert_called_once()
        mock_bot_start.assert_called_once_with("FAKE_TOKEN")
        mock_close_pool.assert_called_once()
        mock_close_redis.assert_called_once()
        mock_print.assert_any_call("Initializing database connection...")
        mock_print.assert_any_call("Database initialized successfully!")
        mock_print.assert_any_call("Closing database connections...")
        mock_print.assert_any_call("Database connections closed.")


@pytest.mark.asyncio
async def test_main_db_init_failure():
    with patch(
        "bot.initialize_database", new_callable=AsyncMock, return_value=False
    ) as mock_init_db, patch(
        "bot.load_cogs", new_callable=AsyncMock
    ) as mock_load_cogs, patch(
        "bot.bot.start", new_callable=AsyncMock
    ) as mock_bot_start, patch(
        "bot.close_pool", new_callable=AsyncMock
    ) as mock_close_pool, patch(
        "bot.close_redis", new_callable=AsyncMock
    ) as mock_close_redis, patch(
        "builtins.print"
    ) as mock_print, patch(
        "os.getenv", return_value="FAKE_TOKEN"
    ):

        await main()

        mock_init_db.assert_called_once()
        mock_load_cogs.assert_not_called()
        mock_bot_start.assert_not_called()
        mock_close_pool.assert_called_once()
        mock_close_redis.assert_called_once()
        mock_print.assert_any_call("Failed to initialize database. Exiting.")


@pytest.mark.asyncio
async def test_main_bot_start_failure():
    with patch(
        "bot.initialize_database", new_callable=AsyncMock, return_value=True
    ), patch("bot.load_cogs", new_callable=AsyncMock), patch(
        "bot.bot.start",
        new_callable=AsyncMock,
        side_effect=Exception("Bot start error"),
    ) as mock_bot_start, patch(
        "bot.close_pool", new_callable=AsyncMock
    ) as mock_close_pool, patch(
        "bot.close_redis", new_callable=AsyncMock
    ) as mock_close_redis, patch(
        "os.getenv", return_value="FAKE_TOKEN"
    ):

        # The exception should propagate from main
        with pytest.raises(Exception, match="Bot start error"):
            await main()

        mock_bot_start.assert_called_once()
        # The finally block in main ensures these are always called
        mock_close_pool.assert_called_once()
        mock_close_redis.assert_called_once()

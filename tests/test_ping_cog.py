import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import discord
from discord.ext import commands
from cogs.ping import Ping
import datetime


@pytest.fixture
def mock_bot():
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    return bot


@pytest.fixture
def mock_ctx():
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.id = 123
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 456
    ctx.channel = MagicMock(spec=discord.TextChannel)
    return ctx


@pytest.mark.asyncio
async def test_ping_cog_init(mock_bot):
    cog = Ping(mock_bot)
    assert cog.bot is mock_bot


@pytest.mark.asyncio
async def test_ping_cog_initialize(mock_bot):
    cog = Ping(mock_bot)
    with patch(
        "cogs.ping.get_redis", new_callable=AsyncMock, return_value=AsyncMock()
    ) as mock_get_redis:
        await cog.initialize()
        mock_get_redis.assert_called_once()
        assert cog.redis is not None


@pytest.mark.asyncio
async def test_ping_cog_initialize_redis_fail(mock_bot):
    cog = Ping(mock_bot)
    with patch(
        "cogs.ping.get_redis", new_callable=AsyncMock, return_value=None
    ) as mock_get_redis:
        await cog.initialize()
        mock_get_redis.assert_called_once()
        assert cog.redis is None


@pytest.mark.asyncio
async def test_sample_pg(mock_bot):
    cog = Ping(mock_bot)
    mock_conn = AsyncMock()
    # Create a mock for the async context manager
    mock_get_connection_context = AsyncMock()
    mock_get_connection_context.__aenter__.return_value = mock_conn
    mock_get_connection_context.__aexit__.return_value = None

    # Mock time.perf_counter to control latency calculation
    with patch("time.perf_counter", side_effect=[0, 0.001]):  # 1ms
        with patch(
            "cogs.ping.get_connection", return_value=mock_get_connection_context
        ):
            latency = await cog._sample_pg(samples=1)
            assert latency == pytest.approx(1.0)  # Should be in ms


@pytest.mark.asyncio
async def test_sample_pg_no_connection(mock_bot):
    cog = Ping(mock_bot)
    # Create a mock for the async context manager that returns None on __aenter__
    mock_get_connection_context = AsyncMock()
    mock_get_connection_context.__aenter__.return_value = None
    mock_get_connection_context.__aexit__.return_value = None

    with patch("cogs.ping.get_connection", return_value=mock_get_connection_context):
        latency = await cog._sample_pg(samples=1)
        assert latency == float("inf")


@pytest.mark.asyncio
async def test_sample_redis(mock_bot):
    cog = Ping(mock_bot)
    cog.redis = AsyncMock()
    cog.redis.ping.return_value = True

    # Mock time.perf_counter to control elapsed time
    with patch(
        "time.perf_counter", side_effect=[0, 0.01, 0.01, 0.02, 0.02, 0.03]
    ):  # Simulate 10ms per ping
        latency = await cog._sample_redis(samples=3)
        assert latency == pytest.approx(10.0)


@pytest.mark.asyncio
async def test_sample_redis_no_redis(mock_bot):
    cog = Ping(mock_bot)
    cog.redis = None
    latency = await cog._sample_redis(samples=1)
    assert latency == float("inf")


@pytest.mark.asyncio
async def test_slash_ping_command(mock_bot, mock_ctx):
    cog = Ping(mock_bot)
    mock_bot.launch_time = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(hours=1)

    # Mock the send method to capture the message and return a mock message object
    mock_message = AsyncMock(spec=discord.Message)
    mock_ctx.send.return_value = mock_message

    with patch.object(
        type(mock_bot), "latency", new_callable=PropertyMock, return_value=0.123
    ), patch.object(
        cog, "_sample_pg", new_callable=AsyncMock, return_value=50.0
    ), patch.object(
        cog, "_sample_redis", new_callable=AsyncMock, return_value=20.0
    ), patch(
        "psutil.Process"
    ) as mock_process, patch(
        "psutil.cpu_percent"
    ) as mock_cpu, patch(
        "socket.gethostname", return_value="TestHost"
    ), patch(
        "humanize.naturaldelta", return_value="1 hour"
    ):

        # Configure psutil mocks
        mock_process.return_value.memory_info.return_value.rss = (
            256 * 1024 * 1024
        )  # 256 MB
        mock_cpu.return_value = 55.5

        # A hybrid command's callback must be called with the cog instance
        await cog.slash_ping.callback(cog, mock_ctx)

        mock_ctx.send.assert_called_once()
        mock_message.edit.assert_called_once()

        # Check the content of the final message
        edited_content = mock_message.edit.call_args[1]["content"]
        assert "WS latency: 123.00ms" in edited_content
        assert "RTT: " in edited_content  # RTT is dynamic, just check it's there
        assert "Postgres latency (avg): 50.00ms" in edited_content
        assert "Redis latency (avg): 20.00ms" in edited_content
        assert "Bot uptime: 1 hour" in edited_content
        assert "Bot RAM usage: 256.00 MB" in edited_content
        assert "System CPU usage: 55.50%" in edited_content
        assert "Hostname: TestHost" in edited_content


@pytest.mark.asyncio
async def test_slash_ping_command_pg_fail(mock_bot, mock_ctx):
    cog = Ping(mock_bot)
    mock_bot.launch_time = datetime.datetime.now(datetime.timezone.utc)
    mock_message = AsyncMock(spec=discord.Message)
    mock_ctx.send.return_value = mock_message

    with patch.object(
        cog, "_sample_pg", new_callable=AsyncMock, return_value=float("inf")
    ), patch.object(cog, "_sample_redis", new_callable=AsyncMock, return_value=20.0):

        await cog.slash_ping.callback(cog, mock_ctx)

        edited_content = mock_message.edit.call_args[1]["content"]
        assert "Postgres: Unreachable" in edited_content


@pytest.mark.asyncio
async def test_slash_ping_command_redis_fail(mock_bot, mock_ctx):
    cog = Ping(mock_bot)
    mock_bot.launch_time = datetime.datetime.now(datetime.timezone.utc)
    mock_message = AsyncMock(spec=discord.Message)
    mock_ctx.send.return_value = mock_message
    cog.redis = None  # Simulate no redis connection

    with patch.object(cog, "_sample_pg", new_callable=AsyncMock, return_value=50.0):
        await cog.slash_ping.callback(cog, mock_ctx)

        edited_content = mock_message.edit.call_args[1]["content"]
        assert "Redis: Unreachable" in edited_content


@pytest.mark.asyncio
async def test_setup_function(mock_bot):
    mock_bot.add_cog = AsyncMock()

    # We patch the class to inspect the instance created
    with patch("cogs.ping.Ping", autospec=True) as MockPing:
        # The instance's methods need to be async mocks
        mock_instance = MockPing.return_value
        mock_instance.initialize = AsyncMock()

        # Import and call the setup function from the cog file
        from cogs.ping import setup

        await setup(mock_bot)

        # Assertions
        MockPing.assert_called_once_with(mock_bot)
        mock_instance.initialize.assert_called_once()
        mock_bot.add_cog.assert_called_once_with(mock_instance)

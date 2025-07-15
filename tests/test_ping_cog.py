import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = MagicMock(spec=discord.InteractionResponse)
    interaction.response.send_message = AsyncMock()
    return interaction

@pytest.mark.asyncio
async def test_ping_cog_init(mock_bot):
    cog = Ping(mock_bot)
    assert cog.bot is mock_bot

@pytest.mark.asyncio
async def test_ping_cog_initialize(mock_bot):
    cog = Ping(mock_bot)
    with patch('cogs.ping.get_redis', new_callable=AsyncMock, return_value=AsyncMock()) as mock_get_redis:
        await cog.initialize()
        mock_get_redis.assert_called_once()
        assert cog.redis is not None

@pytest.mark.asyncio
async def test_ping_cog_initialize_redis_fail(mock_bot):
    cog = Ping(mock_bot)
    with patch('cogs.ping.get_redis', new_callable=AsyncMock, return_value=None) as mock_get_redis:
        await cog.initialize()
        mock_get_redis.assert_called_once()
        assert cog.redis is None

@pytest.mark.asyncio
async def test_sample_pg(mock_bot):
    cog = Ping(mock_bot)
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = datetime.timedelta(microseconds=1000) # 1ms
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    with patch('cogs.ping.get_connection', new_callable=MagicMock, return_value=mock_pool):
        latency = await cog._sample_pg(samples=1)
        assert latency == 1.0 # Should be in ms

@pytest.mark.asyncio
async def test_sample_pg_no_connection(mock_bot):
    cog = Ping(mock_bot)
    with patch('cogs.ping.get_connection', new_callable=MagicMock, return_value=None):
        latency = await cog._sample_pg(samples=1)
        assert latency == float('inf')

@pytest.mark.asyncio
async def test_sample_redis(mock_bot):
    cog = Ping(mock_bot)
    cog.redis = AsyncMock()
    cog.redis.ping.return_value = True

    # Mock time.time() to control elapsed time
    with patch('time.time', side_effect=[0, 0.01, 0.02, 0.03]): # Simulate 10ms per ping
        latency = await cog._sample_redis(samples=3)
        assert latency == pytest.approx(10.0) # Should be in ms

@pytest.mark.asyncio
async def test_sample_redis_no_redis(mock_bot):
    cog = Ping(mock_bot)
    cog.redis = None
    latency = await cog._sample_redis(samples=1)
    assert latency == float('inf')

@pytest.mark.asyncio
async def test_slash_ping_command(mock_bot, mock_interaction):
    cog = Ping(mock_bot)
    await cog.initialize() # Ensure redis is mocked
    cog.redis = AsyncMock()
    cog.redis.ping.return_value = True

    # Mock _sample_pg and _sample_redis
    with patch.object(cog, '_sample_pg', new_callable=AsyncMock, return_value=50.0), \
         patch.object(cog, '_sample_redis', new_callable=AsyncMock, return_value=20.0), \
         patch('discord.Embed') as mock_embed:
        
        mock_embed_instance = MagicMock()
        mock_embed.return_value = mock_embed_instance
        
        await cog.slash_ping(mock_interaction)
        
        mock_interaction.response.send_message.assert_called_once_with(embed=mock_embed_instance, ephemeral=True)
        mock_embed.assert_called_once()
        
        # Verify embed fields are called with correct data
        mock_embed_instance.add_field.assert_any_call(name="Bot Latency", value=pytest.approx(mock_bot.latency * 1000, abs=1.0), inline=True)
        mock_embed_instance.add_field.assert_any_call(name="Database Latency", value="50.00ms", inline=True)
        mock_embed_instance.add_field.assert_any_call(name="Redis Latency", value="20.00ms", inline=True)
        mock_embed_instance.set_footer.assert_called_once()

@pytest.mark.asyncio
async def test_slash_ping_command_pg_fail(mock_bot, mock_interaction):
    cog = Ping(mock_bot)
    await cog.initialize()
    cog.redis = AsyncMock()
    cog.redis.ping.return_value = True

    with patch.object(cog, '_sample_pg', new_callable=AsyncMock, return_value=float('inf')), \
         patch.object(cog, '_sample_redis', new_callable=AsyncMock, return_value=20.0), \
         patch('discord.Embed') as mock_embed:
        
        mock_embed_instance = MagicMock()
        mock_embed.return_value = mock_embed_instance
        
        await cog.slash_ping(mock_interaction)
        
        mock_embed_instance.add_field.assert_any_call(name="Database Latency", value="N/A", inline=True)

@pytest.mark.asyncio
async def test_slash_ping_command_redis_fail(mock_bot, mock_interaction):
    cog = Ping(mock_bot)
    await cog.initialize()
    cog.redis = None # Simulate no redis connection

    with patch.object(cog, '_sample_pg', new_callable=AsyncMock, return_value=50.0), \
         patch('discord.Embed') as mock_embed:
        
        mock_embed_instance = MagicMock()
        mock_embed.return_value = mock_embed_instance
        
        await cog.slash_ping(mock_interaction)
        
        mock_embed_instance.add_field.assert_any_call(name="Redis Latency", value="N/A", inline=True)

@pytest.mark.asyncio
async def test_setup_function(mock_bot):
    with patch('cogs.ping.Ping', new=MagicMock) as MockPing:
        mock_ping_instance = MockPing.return_value
        mock_ping_instance.initialize = AsyncMock()
        
        await cog.ping.setup(mock_bot)
        
        MockPing.assert_called_once_with(mock_bot)
        mock_bot.add_cog.assert_called_once_with(mock_ping_instance)
        mock_ping_instance.initialize.assert_called_once()
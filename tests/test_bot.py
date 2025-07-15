import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from bot import get_prefix, MyBot
from database import operations as db_operations
from cachetools import TTLCache

@pytest.fixture
def mock_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    bot = MyBot(command_prefix="!", intents=intents)
    bot.is_owner = AsyncMock(return_value=True) # Mock is_owner for testing
    return bot

@pytest.mark.asyncio
async def test_get_prefix_from_db(mock_bot):
    mock_message = MagicMock()
    mock_message.guild.id = 12345

    with patch('bot.get_pool', new_callable=AsyncMock) as mock_get_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = '["test!"]'
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        prefix = await get_prefix(mock_bot, mock_message)
        assert prefix == ['test!']

@pytest.mark.asyncio
async def test_get_prefix_default(mock_bot):
    mock_message = MagicMock()
    mock_message.guild.id = 67890

    with patch('bot.get_pool', new_callable=AsyncMock) as mock_get_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = None
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        prefix = await get_prefix(mock_bot, mock_message)
        assert prefix == 'o!'

@pytest.mark.asyncio
async def test_get_prefix_caching(mock_bot):
    mock_message = MagicMock()
    mock_message.guild.id = 112233

    with patch('bot.get_pool', new_callable=AsyncMock) as mock_get_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = '["cached!"]'
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        # First call, should hit DB and cache
        prefix1 = await get_prefix(mock_bot, mock_message)
        assert prefix1 == ['cached!']

        # Second call, should hit cache, not DB
        mock_get_pool.reset_mock()
        prefix2 = await get_prefix(mock_bot, mock_message)
        assert prefix2 == ['cached!']
        mock_get_pool.assert_not_called()
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
from cogs.human_moderation_cog import HumanModerationCog
import datetime
from datetime import timedelta

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
    ctx.me = MagicMock(spec=discord.Member) # Mock the bot's member in the guild
    ctx.me.guild_permissions = MagicMock(spec=discord.Permissions)
    ctx.me.guild_permissions.ban_members = True
    ctx.me.guild_permissions.kick_members = True
    return ctx

@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    member.id = 789
    member.name = "test_member"
    member.mention = "<@789>"
    member.guild = MagicMock(spec=discord.Guild)
    member.guild.id = 456
    member.top_role = MagicMock(spec=discord.Role)
    member.top_role.position = 10
    return member

@pytest.fixture
def mock_user():
    user = MagicMock(spec=discord.User)
    user.id = 999
    user.name = "test_user"
    user.mention = "<@999>"
    return user

@pytest.mark.asyncio
async def test_human_moderation_cog_init(mock_bot):
    cog = HumanModerationCog(mock_bot)
    assert cog.bot is mock_bot

# --- _parse_duration Tests ---
@pytest.mark.parametrize("duration_str, expected_timedelta", [
    ("1d", timedelta(days=1)),
    ("2h", timedelta(hours=2)),
    ("30m", timedelta(minutes=30)),
    ("1d2h30m", timedelta(days=1, hours=2, minutes=30)),
    ("1w", timedelta(weeks=1)),
    ("1w2d3h4m", timedelta(weeks=1, days=2, hours=3, minutes=4)),
    ("1D", timedelta(days=1)), # Test case insensitivity
    ("10", None), # Invalid format
    ("", None), # Empty string
    ("abc", None), # Invalid string
])
def test_parse_duration(duration_str, expected_timedelta):
    cog = HumanModerationCog(MagicMock()) # Bot mock not needed for this method
    result = cog._parse_duration(duration_str)
    assert result == expected_timedelta

# --- moderate_ban_callback Tests ---
@pytest.mark.asyncio
async def test_moderate_ban_callback_success(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.ban = AsyncMock()
    mock_ctx.me.top_role.position = 20 # Bot has higher role than member
    
    with patch('database.operations.add_mod_log_entry', new_callable=AsyncMock) as mock_add_log:
        await cog.moderate_ban_callback(cog, mock_ctx, mock_member, "Test ban reason", 7, False)
        
        mock_ctx.guild.ban.assert_called_once_with(mock_member, reason="Test ban reason", delete_message_days=7)
        mock_add_log.assert_called_once()
        mock_ctx.send.assert_called_once()
        assert "Successfully banned" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_member_not_found(mock_bot, mock_ctx):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.get_member.return_value = None # Simulate member not found
    
    await cog.moderate_ban_callback(cog, mock_ctx, None, "Test ban reason", 0, False, user_id=12345)
    
    mock_ctx.send.assert_called_once()
    assert "Could not find that member or user." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_bot_has_no_permissions(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.me.guild_permissions.ban_members = False # Bot has no ban permission
    
    await cog.moderate_ban_callback(cog, mock_ctx, mock_member, "Test ban reason", 0, False)
    
    mock_ctx.send.assert_called_once()
    assert "I don't have permission to ban members." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_cannot_ban_higher_role(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.me.top_role.position = 5 # Bot's role is lower
    mock_member.top_role.position = 10 # Member's role is higher
    
    await cog.moderate_ban_callback(cog, mock_ctx, mock_member, "Test ban reason", 0, False)
    
    mock_ctx.send.assert_called_once()
    assert "I cannot ban this user as their highest role is higher than or equal to my highest role." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_dm_user(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.ban = AsyncMock()
    mock_member.send = AsyncMock()
    mock_ctx.me.top_role.position = 20

    with patch('database.operations.add_mod_log_entry', new_callable=AsyncMock):
        await cog.moderate_ban_callback(cog, mock_ctx, mock_member, "Test ban reason", 0, True)
        mock_member.send.assert_called_once()
        assert "You have been banned from" in mock_member.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_dm_fail(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.ban = AsyncMock()
    mock_member.send.side_effect = discord.Forbidden # Simulate DM failure
    mock_ctx.me.top_role.position = 20

    with patch('database.operations.add_mod_log_entry', new_callable=AsyncMock):
        await cog.moderate_ban_callback(cog, mock_ctx, mock_member, "Test ban reason", 0, True)
        mock_member.send.assert_called_once() # Still attempts to send
        mock_ctx.send.assert_called_once()
        assert "Successfully banned" in mock_ctx.send.call_args[0][0]
        assert "However, I could not DM the user." in mock_ctx.send.call_args[0][0]

# --- moderate_unban_callback Tests ---
@pytest.mark.asyncio
async def test_moderate_unban_callback_success(mock_bot, mock_ctx, mock_user):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.unban = AsyncMock()
    mock_ctx.guild.fetch_ban.return_value = MagicMock(user=mock_user) # Simulate ban exists
    
    with patch('database.operations.add_mod_log_entry', new_callable=AsyncMock) as mock_add_log:
        await cog.moderate_unban_callback(cog, mock_ctx, mock_user.id, "Test unban reason")
        
        mock_ctx.guild.unban.assert_called_once_with(mock_user, reason="Test unban reason")
        mock_add_log.assert_called_once()
        mock_ctx.send.assert_called_once()
        assert "Successfully unbanned" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_unban_callback_user_not_banned(mock_bot, mock_ctx, mock_user):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.fetch_ban.side_effect = discord.NotFound # Simulate user not banned
    
    await cog.moderate_unban_callback(cog, mock_ctx, mock_user.id, "Test unban reason")
    
    mock_ctx.send.assert_called_once()
    assert "That user is not banned from this server." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_unban_callback_bot_has_no_permissions(mock_bot, mock_ctx, mock_user):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.me.guild_permissions.ban_members = False # Bot has no unban permission (same as ban)
    
    await cog.moderate_unban_callback(cog, mock_ctx, mock_user.id, "Test unban reason")
    
    mock_ctx.send.assert_called_once()
    assert "I don't have permission to unban members." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_unban_callback_fetch_ban_error(mock_bot, mock_ctx, mock_user):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.fetch_ban.side_effect = Exception("Fetch ban error")
    
    await cog.moderate_unban_callback(cog, mock_ctx, mock_user.id, "Test unban reason")
    
    mock_ctx.send.assert_called_once()
    assert "An unexpected error occurred while fetching ban information." in mock_ctx.send.call_args[0][0]
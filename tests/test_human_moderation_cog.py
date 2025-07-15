import pytest
import discord
from discord.ext import commands
from cogs.human_moderation_cog import HumanModerationCog
import datetime
from datetime import timedelta

from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

@pytest.fixture
def mock_bot():
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # Mock the 'user' property correctly
    mock_user = MagicMock(spec=discord.ClientUser)
    mock_user.id = 987654321
    type(bot).user = PropertyMock(return_value=mock_user)
    
    return bot

def create_mock_role(position: int) -> MagicMock:
    """Creates a mock role that is comparable based on its position."""
    role = MagicMock(spec=discord.Role)
    role.position = position
    role.__le__ = lambda other: role.position <= other.position
    role.__lt__ = lambda other: role.position < other.position
    role.__ge__ = lambda other: role.position >= other.position
    role.__gt__ = lambda other: role.position > other.position
    return role

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.id = 123
    ctx.author.top_role = create_mock_role(15)
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 456
    ctx.channel = MagicMock(spec=discord.TextChannel)
    ctx.guild.me = MagicMock(spec=discord.Member) # Mock the bot's member in the guild
    ctx.guild.me.guild_permissions = MagicMock(spec=discord.Permissions)
    ctx.guild.me.guild_permissions.ban_members = True
    ctx.guild.me.guild_permissions.kick_members = True
    ctx.guild.me.top_role = create_mock_role(20)
    ctx.interaction = None # Simulate a prefix command context by default
    return ctx

@pytest.fixture
def mock_member():
    member = MagicMock(spec=discord.Member)
    member.id = 789
    member.name = "test_member"
    member.mention = "<@789>"
    member.guild = MagicMock(spec=discord.Guild)
    member.guild.id = 456
    member.top_role = create_mock_role(10)
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
    
    with patch('cogs.human_moderation_cog.ModLogCog') as mock_mod_log_cog:
        mock_log_instance = mock_mod_log_cog.return_value
        mock_log_instance.log_action = AsyncMock()
        mock_bot.get_cog = MagicMock(return_value=mock_log_instance)

        await cog.moderate_ban_callback.callback(cog, ctx=mock_ctx, member=mock_member, reason="Test ban reason", delete_days=7, send_dm=False)
        
        mock_ctx.guild.ban.assert_called_once_with(mock_member, reason="Test ban reason", delete_message_days=7)
        mock_log_instance.log_action.assert_called_once()
        mock_ctx.send.assert_called_once()
        assert "Banned" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_member_not_found(mock_bot, mock_ctx):
    cog = HumanModerationCog(mock_bot)
    mock_bot.fetch_user = AsyncMock(side_effect=discord.NotFound(MagicMock(), "Unknown User"))
    mock_ctx.guild.ban.side_effect = discord.NotFound(MagicMock(), "Unknown User")

    await cog.moderate_ban_callback.callback(cog, ctx=mock_ctx, user_id="12345", reason="Test ban reason")

    mock_ctx.send.assert_called_once()
    assert "Could not find a user with the ID" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_bot_has_no_permissions(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.me.guild_permissions.ban_members = False
    
    await cog.moderate_ban_callback.callback(cog, ctx=mock_ctx, member=mock_member, reason="Test ban reason")
    
    mock_ctx.send.assert_called_once()
    assert "I don't have permission to ban members." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_cannot_ban_higher_role(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.me.top_role = create_mock_role(5)
    mock_member.top_role = create_mock_role(10)

    await cog.moderate_ban_callback.callback(cog, ctx=mock_ctx, member=mock_member, reason="Test ban reason")

    mock_ctx.send.assert_called_once()
    assert "I cannot ban someone with a higher or equal role than me." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_ban_callback_dm_user(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.ban = AsyncMock()
    mock_member.send = AsyncMock()

    with patch('cogs.human_moderation_cog.ModLogCog'):
        await cog.moderate_ban_callback.callback(cog, ctx=mock_ctx, member=mock_member, reason="Test ban reason", send_dm=True)
        mock_member.send.assert_called_once()
        embed = mock_member.send.call_args.kwargs['embed']
        assert "You have been banned from" in embed.description

@pytest.mark.asyncio
async def test_moderate_ban_callback_dm_fail(mock_bot, mock_ctx, mock_member):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.ban = AsyncMock()
    mock_member.send.side_effect = discord.Forbidden

    with patch('cogs.human_moderation_cog.ModLogCog'):
        await cog.moderate_ban_callback.callback(cog, ctx=mock_ctx, member=mock_member, reason="Test ban reason", send_dm=True)
        mock_member.send.assert_called_once()
        mock_ctx.send.assert_called_once()
        assert "Banned" in mock_ctx.send.call_args[0][0]
        assert "Could not send DM notification" in mock_ctx.send.call_args[0][0]

# --- moderate_unban_callback Tests ---
@pytest.mark.asyncio
async def test_moderate_unban_callback_success(mock_bot, mock_ctx, mock_user):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.unban = AsyncMock()
    mock_ctx.guild.fetch_ban.return_value = MagicMock(user=mock_user)
    
    with patch('cogs.human_moderation_cog.ModLogCog') as mock_mod_log_cog:
        mock_log_instance = mock_mod_log_cog.return_value
        mock_log_instance.log_action = AsyncMock()
        mock_bot.get_cog = MagicMock(return_value=mock_log_instance)

        await cog.moderate_unban_callback.callback(cog, ctx=mock_ctx, user_id=str(mock_user.id), reason="Test unban reason")
        
        mock_ctx.guild.unban.assert_called_once_with(mock_user, reason="Test unban reason")
        mock_log_instance.log_action.assert_called_once()
        mock_ctx.send.assert_called_once()
        assert "Unbanned" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_unban_callback_user_not_banned(mock_bot, mock_ctx, mock_user):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.fetch_ban.side_effect = discord.NotFound(MagicMock(), "User not found")

    await cog.moderate_unban_callback.callback(cog, ctx=mock_ctx, user_id=str(mock_user.id), reason="Test unban reason")
    
    mock_ctx.send.assert_called_once()
    assert "This user is not banned." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_unban_callback_bot_has_no_permissions(mock_bot, mock_ctx, mock_user):
    cog = HumanModerationCog(mock_bot)
    mock_ctx.guild.me.guild_permissions.ban_members = False
    
    await cog.moderate_unban_callback.callback(cog, ctx=mock_ctx, user_id=str(mock_user.id), reason="Test unban reason")
    
    mock_ctx.send.assert_called_once()
    assert "I don't have permission to unban users." in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_moderate_unban_callback_fetch_ban_error(mock_bot, mock_ctx, mock_user):
    cog = HumanModerationCog(mock_bot)
    # Correctly instantiate the HTTPException
    mock_response = MagicMock()
    mock_response.status = 500
    mock_ctx.guild.fetch_ban.side_effect = discord.HTTPException(mock_response, "Fetch ban error")

    await cog.moderate_unban_callback.callback(cog, ctx=mock_ctx, user_id=str(mock_user.id), reason="Test unban reason")
    
    mock_ctx.send.assert_called_once()
    assert "An error occurred while checking the ban list" in mock_ctx.send.call_args[0][0]
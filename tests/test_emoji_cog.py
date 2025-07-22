import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands
import datetime
from cogs.emoji_cog import EmojiCog


@pytest.fixture
def mock_bot():
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    return bot


@pytest.fixture
def mock_ctx(mock_bot):  # Add mock_bot as an argument to the fixture
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.id = 123
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 456
    ctx.channel = MagicMock(spec=discord.TextChannel)
    ctx.bot = mock_bot  # Assign the mock_bot to ctx.bot
    ctx.message = MagicMock()  # Add a mock message object
    ctx.message.edited_at = datetime.datetime(
        2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
    )  # Mock edited_at attribute
    ctx.message.created_at = datetime.datetime(
        2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
    )  # Mock created_at attribute
    ctx.message.content = "!emojis"  # Mock message content for command parsing
    ctx.prefix = "!"  # Mock command prefix
    ctx.view = MagicMock()  # Mock the view attribute of the context
    return ctx


@pytest.mark.asyncio
async def test_emoji_cog_init(mock_bot):
    cog = EmojiCog(mock_bot)
    assert cog.bot is mock_bot


@pytest.mark.asyncio
async def test_emojis_command(mock_bot, mock_ctx):
    mock_config_data = {
        "CustomEmoji": {
            "TEST_EMOJI": "<:testemoji1:111>",
            "ANIMATED_EMOJI": "<a:animatedemoji:222>",
        }
    }
    with (
        patch("cogs.emoji_cog.yaml.safe_load", return_value=mock_config_data),
        patch("builtins.open", MagicMock()),
        patch.object(mock_bot, "get_emoji") as mock_get_emoji,
    ):  # Move this patch here
        # Mock bot.get_emoji to return specific emojis
        mock_emoji1 = MagicMock(spec=discord.Emoji)
        mock_emoji1.name = "testemoji1"
        mock_emoji1.id = 111
        mock_emoji1.animated = False
        mock_emoji1.url = "http://example.com/emoji1.png"
        mock_emoji1.__str__.return_value = "<:testemoji1:111>"

        mock_emoji2 = MagicMock(spec=discord.Emoji)
        mock_emoji2.name = "animatedemoji"
        mock_emoji2.id = 222
        mock_emoji2.animated = True
        mock_emoji2.url = "http://example.com/emoji2.gif"
        mock_emoji2.__str__.return_value = "<a:animatedemoji:222>"

        def get_emoji_side_effect(emoji_id):
            if emoji_id == 111:
                return mock_emoji1
            elif emoji_id == 222:
                return mock_emoji2
            return None

        mock_get_emoji.side_effect = get_emoji_side_effect

        cog = EmojiCog(mock_bot)
        await mock_bot.add_cog(cog)
        mock_ctx.command = cog.emojis  # Assign the command to the context
        with patch.object(cog.emojis, "_prepare_cooldowns", MagicMock()):  # Bypass cooldown check
            await cog.emojis.invoke(mock_ctx)

        mock_ctx.send.assert_called_once()
        sent_message = mock_ctx.send.call_args[0][0]

        assert "Available Custom Emojis" in sent_message
        assert "TEST_EMOJI: <:testemoji1:111>" in sent_message
        assert "ANIMATED_EMOJI: <a:animatedemoji:222>" in sent_message
        assert mock_get_emoji.call_args_list == [((111,), {}), ((222,), {})]


@pytest.mark.asyncio
async def test_emojis_command_no_emojis(mock_bot, mock_ctx):
    mock_config_data = {"CustomEmoji": {}}
    with patch("cogs.emoji_cog.yaml.safe_load", return_value=mock_config_data), patch("builtins.open", MagicMock()):
        cog = EmojiCog(mock_bot)
        await mock_bot.add_cog(cog)
        mock_ctx.command = cog.emojis  # Assign the command to the context
        with patch.object(cog.emojis, "_prepare_cooldowns", MagicMock()):  # Bypass cooldown check
            await cog.emojis.invoke(mock_ctx)

        mock_ctx.send.assert_called_once()
        sent_message = mock_ctx.send.call_args[0][0]

        assert "No custom emojis configured." in sent_message


@pytest.mark.asyncio
async def test_emojis_command_emoji_not_found(mock_bot, mock_ctx):
    with patch.object(mock_bot, "get_emoji", return_value=None):
        mock_config_data = {"CustomEmoji": {"UNKNOWN_EMOJI": 999}}
        with patch("cogs.emoji_cog.yaml.safe_load", return_value=mock_config_data), patch("builtins.open", MagicMock()):
            cog = EmojiCog(mock_bot)  # Moved outside with statement
            await mock_bot.add_cog(cog)
            mock_ctx.command = cog.emojis  # Assign the command to the context
            with patch.object(cog.emojis, "_prepare_cooldowns", MagicMock()):  # Bypass cooldown check
                await cog.emojis.invoke(mock_ctx)

        mock_ctx.send.assert_called_once()
        sent_message = mock_ctx.send.call_args[0][0]

        assert "UNKNOWN_EMOJI: Emoji not found" in sent_message

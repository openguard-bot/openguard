# pylint: disable=no-member
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from .aimod_helpers.config_manager import (
    get_excluded_channels,
    add_excluded_channel,
    remove_excluded_channel,
    is_channel_excluded,
    get_channel_rules,
    set_channel_rules,
    remove_channel_rules,
    get_all_channel_rules,
)


from .core_ai_cog import CoreAICog


class AIChannelConfigCog(commands.Cog, name="AI Channel Config"):
    """
    Manages channel-specific AI moderation settings including exclusions and custom rules.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @CoreAICog.ai.group(
        name="channel",
        description="Manage AI moderation settings for specific channels",
    )
    async def channel(self, ctx: commands.Context):
        """AI channel configuration commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @channel.command(name="exclude", description="Exclude a channel from AI moderation")
    @app_commands.describe(
        channel="The channel to exclude from AI moderation (defaults to current channel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def exclude_channel(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        """Exclude a channel from AI moderation."""
        if channel is None:
            channel = ctx.channel

        guild_id = ctx.guild.id
        channel_id = channel.id

        # Check if already excluded
        if await is_channel_excluded(guild_id, channel_id):
            response = f"❌ {channel.mention} is already excluded from AI moderation."
        else:
            success = await add_excluded_channel(guild_id, channel_id)
            if success:
                response = f"✅ {channel.mention} has been excluded from AI moderation."
            else:
                response = f"❌ Failed to exclude {channel.mention} from AI moderation."

        if ctx.interaction:
            await ctx.interaction.response.send_message(response)
        else:
            await ctx.send(response)

    @channel.command(
        name="include",
        description="Include a channel in AI moderation (remove exclusion)",
    )
    @app_commands.describe(
        channel="The channel to include in AI moderation (defaults to current channel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def include_channel(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        """Include a channel in AI moderation (remove exclusion)."""
        if channel is None:
            channel = ctx.channel

        guild_id = ctx.guild.id
        channel_id = channel.id

        # Check if not excluded
        if not await is_channel_excluded(guild_id, channel_id):
            response = f"❌ {channel.mention} is not excluded from AI moderation."
        else:
            success = await remove_excluded_channel(guild_id, channel_id)
            if success:
                response = f"✅ {channel.mention} has been included in AI moderation."
            else:
                response = f"❌ Failed to include {channel.mention} in AI moderation."

        if ctx.interaction:
            await ctx.interaction.response.send_message(response)
        else:
            await ctx.send(response)

    @channel.command(
        name="listexcluded", description="List all channels excluded from AI moderation"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def list_excluded(self, ctx: commands.Context):
        """List all channels excluded from AI moderation."""
        guild_id = ctx.guild.id
        excluded_channels = await get_excluded_channels(guild_id)

        if not excluded_channels:
            response = "No channels are currently excluded from AI moderation."
        else:
            channel_mentions = []
            for channel_id in excluded_channels:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    channel_mentions.append(channel.mention)
                else:
                    channel_mentions.append(f"<#{channel_id}> (deleted)")

            response = (
                f"**Excluded Channels ({len(excluded_channels)}):**\n"
                + "\n".join(channel_mentions)
            )

        if ctx.interaction:
            await ctx.interaction.response.send_message(response)
        else:
            await ctx.send(response)

    @channel.command(
        name="setrules",
        description="Set custom AI moderation rules for a specific channel",
    )
    @app_commands.describe(
        channel="The channel to set custom rules for (defaults to current channel)",
        rules="The custom rules for this channel (use 'default' to remove custom rules)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel_rules(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
        *,
        rules: str,
    ):
        """Set custom AI moderation rules for a specific channel."""
        if channel is None:
            channel = ctx.channel

        guild_id = ctx.guild.id
        channel_id = channel.id

        if rules.lower().strip() == "default":
            # Remove custom rules
            success = await remove_channel_rules(guild_id, channel_id)
            if success:
                response = f"✅ Custom rules removed for {channel.mention}. Using server default rules."
            else:
                response = f"❌ Failed to remove custom rules for {channel.mention}."
        else:
            # Set custom rules
            success = await set_channel_rules(guild_id, channel_id, rules)
            if success:
                response = f"✅ Custom rules set for {channel.mention}."
            else:
                response = f"❌ Failed to set custom rules for {channel.mention}."

        if ctx.interaction:
            await ctx.interaction.response.send_message(response)
        else:
            await ctx.send(response)

    @channel.command(
        name="viewrules",
        description="View custom AI moderation rules for a specific channel",
    )
    @app_commands.describe(
        channel="The channel to view custom rules for (defaults to current channel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def view_channel_rules(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        """View custom AI moderation rules for a specific channel."""
        if channel is None:
            channel = ctx.channel

        guild_id = ctx.guild.id
        channel_id = channel.id

        custom_rules = await get_channel_rules(guild_id, channel_id)

        if not custom_rules:
            response = f"No custom rules set for {channel.mention}. Using server default rules."
        else:
            embed = discord.Embed(
                title=f"Custom Rules for {channel.name}",
                description=custom_rules,
                color=discord.Color.blue(),
            )
            embed.set_footer(text=f"Channel ID: {channel_id}")

            if ctx.interaction:
                await ctx.interaction.response.send_message(embed=embed)
            else:
                await ctx.send(embed=embed)
            return

        if ctx.interaction:
            await ctx.interaction.response.send_message(response)
        else:
            await ctx.send(response)

    @channel.command(
        name="listallrules",
        description="List all channels with custom AI moderation rules",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def list_all_rules(self, ctx: commands.Context):
        """List all channels with custom AI moderation rules."""
        guild_id = ctx.guild.id
        all_channel_rules = await get_all_channel_rules(guild_id)

        if not all_channel_rules:
            response = "No channels have custom AI moderation rules set."
        else:
            embed = discord.Embed(
                title="Channels with Custom Rules", color=discord.Color.blue()
            )

            for channel_id_str, rules in all_channel_rules.items():
                channel_id = int(channel_id_str)
                channel = ctx.guild.get_channel(channel_id)
                channel_name = (
                    channel.name if channel else f"Deleted Channel ({channel_id})"
                )

                # Truncate rules if too long
                truncated_rules = rules[:100] + "..." if len(rules) > 100 else rules
                embed.add_field(name=channel_name, value=truncated_rules, inline=False)

            if ctx.interaction:
                await ctx.interaction.response.send_message(embed=embed)
            else:
                await ctx.send(embed=embed)
            return

        if ctx.interaction:
            await ctx.interaction.response.send_message(response)
        else:
            await ctx.send(response)

    @channel.command(
        name="status", description="Check AI moderation status for a specific channel"
    )
    @app_commands.describe(
        channel="The channel to check status for (defaults to current channel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def channel_status(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        """Check AI moderation status for a specific channel."""
        if channel is None:
            channel = ctx.channel

        guild_id = ctx.guild.id
        channel_id = channel.id

        is_excluded = await is_channel_excluded(guild_id, channel_id)
        custom_rules = await get_channel_rules(guild_id, channel_id)

        embed = discord.Embed(
            title=f"AI Moderation Status for {channel.name}",
            color=discord.Color.red() if is_excluded else discord.Color.green(),
        )

        embed.add_field(
            name="AI Moderation",
            value="❌ Excluded" if is_excluded else "✅ Active",
            inline=True,
        )

        embed.add_field(
            name="Custom Rules",
            value="✅ Yes" if custom_rules else "❌ No (using server default)",
            inline=True,
        )

        if custom_rules:
            truncated_rules = (
                custom_rules[:500] + "..." if len(custom_rules) > 500 else custom_rules
            )
            embed.add_field(
                name="Rules Preview", value=f"```{truncated_rules}```", inline=False
            )

        embed.set_footer(text=f"Channel ID: {channel_id}")

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(AIChannelConfigCog(bot))

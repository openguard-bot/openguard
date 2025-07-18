"""
Message Rate Limiting Cog for Discord Bot
Automatically adjusts channel slowmode based on message activity.
Uses Singapore Time (UTC+8) for all timestamps and logging.
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from database.operations import get_guild_config, set_guild_config

# Singapore timezone (UTC+8)
SINGAPORE_TZ = timezone(timedelta(hours=8))

log = logging.getLogger(__name__)


class MessageRateCog(commands.Cog):
    """Automatic message rate limiting based on channel activity."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Track message timestamps per channel (last 100 messages)
        self.message_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
        # Track current slowmode settings
        self.current_slowmodes: Dict[int, int] = {}
        # Track auto rate limiting enabled channels
        self.auto_enabled_channels: Dict[int, bool] = {}

        # Configuration constants
        self.HIGH_RATE_THRESHOLD = 10  # messages per minute to trigger high rate
        self.LOW_RATE_THRESHOLD = 3  # messages per minute to trigger low rate
        self.HIGH_RATE_SLOWMODE = 5  # 5 seconds slowmode for high activity
        self.LOW_RATE_SLOWMODE = 2  # 2 seconds slowmode for low activity
        self.NO_SLOWMODE = 0  # No slowmode
        self.CHECK_INTERVAL = 30  # Check every 30 seconds
        self.ANALYSIS_WINDOW = 60  # Analyze last 60 seconds of activity

        # Start the monitoring task
        self.rate_monitor.start()

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.rate_monitor.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Track message timestamps for rate analysis."""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return

        channel_id = message.channel.id
        current_time = datetime.now(SINGAPORE_TZ)

        # Add message timestamp to history
        self.message_history[channel_id].append(current_time)

    @tasks.loop(seconds=30)  # Check every 30 seconds
    async def rate_monitor(self):
        """Monitor message rates and adjust slowmode automatically."""
        try:
            current_time = datetime.now(SINGAPORE_TZ)
            analysis_cutoff = current_time - timedelta(seconds=self.ANALYSIS_WINDOW)

            # Check each channel with auto rate limiting enabled
            for guild in self.bot.guilds:
                guild_enabled = await self.is_auto_rate_enabled(guild.id)
                if not guild_enabled:
                    continue

                for channel in guild.text_channels:
                    channel_enabled = await self.is_channel_auto_rate_enabled(
                        guild.id, channel.id
                    )
                    if not channel_enabled:
                        continue

                    # Check if bot has permission to manage channel
                    if not channel.permissions_for(guild.me).manage_channels:
                        continue

                    await self.analyze_and_adjust_rate(
                        channel, current_time, analysis_cutoff
                    )

        except Exception as e:
            log.error(f"Error in rate monitor: {e}")

    @rate_monitor.before_loop
    async def before_rate_monitor(self):
        """Wait for bot to be ready before starting the monitor."""
        await self.bot.wait_until_ready()

    async def analyze_and_adjust_rate(
        self,
        channel: discord.TextChannel,
        current_time: datetime,
        analysis_cutoff: datetime,
    ):
        """Analyze message rate for a channel and adjust slowmode if needed."""
        try:
            channel_id = channel.id

            # Get recent messages within analysis window
            recent_messages = [
                timestamp
                for timestamp in self.message_history[channel_id]
                if timestamp >= analysis_cutoff
            ]

            messages_per_minute = len(recent_messages)
            current_slowmode = channel.slowmode_delay

            # Determine appropriate slowmode based on activity
            target_slowmode = self.calculate_target_slowmode(messages_per_minute)

            # Only change if different from current setting
            if target_slowmode != current_slowmode:
                await channel.edit(slowmode_delay=target_slowmode)
                self.current_slowmodes[channel_id] = target_slowmode

                # Log the change
                activity_level = self.get_activity_level(messages_per_minute)
                log.info(
                    f"Auto-adjusted slowmode for #{channel.name} in {channel.guild.name}: "
                    f"{current_slowmode}s -> {target_slowmode}s (Activity: {activity_level}, "
                    f"Rate: {messages_per_minute} msg/min)"
                )

                # Send notification if configured
                await self.send_rate_change_notification(
                    channel,
                    current_slowmode,
                    target_slowmode,
                    messages_per_minute,
                    activity_level,
                )

        except discord.Forbidden:
            log.warning(f"No permission to edit slowmode in #{channel.name}")
        except Exception as e:
            log.error(f"Error adjusting rate for #{channel.name}: {e}")

    def calculate_target_slowmode(self, messages_per_minute: int) -> int:
        """Calculate the appropriate slowmode delay based on message rate."""
        if messages_per_minute >= self.HIGH_RATE_THRESHOLD:
            return self.HIGH_RATE_SLOWMODE
        elif messages_per_minute >= self.LOW_RATE_THRESHOLD:
            return self.LOW_RATE_SLOWMODE
        else:
            return self.NO_SLOWMODE

    def get_activity_level(self, messages_per_minute: int) -> str:
        """Get human-readable activity level."""
        if messages_per_minute >= self.HIGH_RATE_THRESHOLD:
            return "High"
        elif messages_per_minute >= self.LOW_RATE_THRESHOLD:
            return "Medium"
        else:
            return "Low"

    async def send_rate_change_notification(
        self,
        channel: discord.TextChannel,
        old_slowmode: int,
        new_slowmode: int,
        messages_per_minute: int,
        activity_level: str,
    ):
        """Send notification about rate limit changes if configured."""
        try:
            # Check if notifications are enabled
            notify_enabled = await get_guild_config(
                channel.guild.id, "AUTO_RATE_NOTIFY", False
            )
            if not notify_enabled:
                return

            # Get notification channel (default to the channel being modified)
            notify_channel_id = await get_guild_config(
                channel.guild.id, "AUTO_RATE_NOTIFY_CHANNEL", channel.id
            )
            notify_channel = self.bot.get_channel(notify_channel_id)

            if not notify_channel:
                return

            # Create notification embed
            embed = discord.Embed(
                title="🕒 Auto Rate Limit Adjusted",
                color=(
                    discord.Color.blue()
                    if new_slowmode > old_slowmode
                    else discord.Color.green()
                ),
            )

            embed.add_field(name="Channel", value=channel.mention, inline=True)

            embed.add_field(name="Activity Level", value=activity_level, inline=True)

            embed.add_field(
                name="Message Rate", value=f"{messages_per_minute} msg/min", inline=True
            )

            embed.add_field(
                name="Slowmode Change",
                value=f"{old_slowmode}s → {new_slowmode}s",
                inline=False,
            )

            embed.timestamp = datetime.now(SINGAPORE_TZ)

            await notify_channel.send(embed=embed)

        except Exception as e:
            log.error(f"Error sending rate change notification: {e}")

    async def is_auto_rate_enabled(self, guild_id: int) -> bool:
        """Check if auto rate limiting is enabled for a guild."""
        return await get_guild_config(guild_id, "AUTO_RATE_ENABLED", False)

    async def is_channel_auto_rate_enabled(
        self, guild_id: int, channel_id: int
    ) -> bool:
        """Check if auto rate limiting is enabled for a specific channel."""
        # Get list of enabled channels
        enabled_channels = await get_guild_config(guild_id, "AUTO_RATE_CHANNELS", [])
        return channel_id in enabled_channels

    async def enable_channel_auto_rate(self, guild_id: int, channel_id: int) -> bool:
        """Enable auto rate limiting for a channel."""
        enabled_channels = await get_guild_config(guild_id, "AUTO_RATE_CHANNELS", [])
        if channel_id not in enabled_channels:
            enabled_channels.append(channel_id)
            return await set_guild_config(
                guild_id, "AUTO_RATE_CHANNELS", enabled_channels
            )
        return True

    async def disable_channel_auto_rate(self, guild_id: int, channel_id: int) -> bool:
        """Disable auto rate limiting for a channel."""
        enabled_channels = await get_guild_config(guild_id, "AUTO_RATE_CHANNELS", [])
        if channel_id in enabled_channels:
            enabled_channels.remove(channel_id)
            return await set_guild_config(
                guild_id, "AUTO_RATE_CHANNELS", enabled_channels
            )
        return True

    # Slash Commands

    @commands.hybrid_group(name="message", description="Message rate limiting commands")
    async def message(self, ctx: commands.Context):
        """Message rate limiting commands."""
        await ctx.send_help(ctx.command)

    @message.command(
        name="ratelimit", description="Configure automatic message rate limiting"
    )
    @app_commands.describe(
        action="Action to perform",
        channel="Channel to configure (defaults to current channel)",
        notifications="Enable/disable notifications for rate changes",
        notification_channel="Channel to send notifications to",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="toggle", value="toggle"),
            app_commands.Choice(name="enable", value="enable"),
            app_commands.Choice(name="disable", value="disable"),
            app_commands.Choice(name="status", value="status"),
            app_commands.Choice(name="config", value="config"),
        ]
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def message_ratelimit(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        channel: Optional[discord.TextChannel] = None,
        notifications: Optional[bool] = None,
        notification_channel: Optional[discord.TextChannel] = None,
    ):
        """Configure automatic message rate limiting for channels."""
        if hasattr(interaction, 'response'):
            await interaction.response.defer()
        else:
            await interaction.defer()

        guild_id = interaction.guild.id
        target_channel = channel or interaction.channel

        if action.value == "toggle":
            await self.handle_toggle_action(interaction, guild_id, target_channel)
        elif action.value == "enable":
            await self.handle_enable_action(interaction, guild_id, target_channel)
        elif action.value == "disable":
            await self.handle_disable_action(interaction, guild_id, target_channel)
        elif action.value == "status":
            await self.handle_status_action(interaction, guild_id, target_channel)
        elif action.value == "config":
            await self.handle_config_action(
                interaction, guild_id, notifications, notification_channel
            )

    async def handle_toggle_action(
        self,
        interaction: discord.Interaction,
        guild_id: int,
        channel: discord.TextChannel,
    ):
        """Handle toggle action for auto rate limiting."""
        try:
            is_enabled = await self.is_channel_auto_rate_enabled(guild_id, channel.id)

            if is_enabled:
                await self.disable_channel_auto_rate(guild_id, channel.id)
                # Reset slowmode to 0
                if channel.permissions_for(interaction.guild.me).manage_channels:
                    await channel.edit(slowmode_delay=0)

                embed = discord.Embed(
                    title="✅ Auto Rate Limiting Disabled",
                    description=f"Automatic rate limiting has been **disabled** for {channel.mention}",
                    color=discord.Color.red(),
                )
            else:
                # Enable guild-wide auto rate if not already enabled
                if not await self.is_auto_rate_enabled(guild_id):
                    await set_guild_config(guild_id, "AUTO_RATE_ENABLED", True)

                await self.enable_channel_auto_rate(guild_id, channel.id)

                embed = discord.Embed(
                    title="✅ Auto Rate Limiting Enabled",
                    description=f"Automatic rate limiting has been **enabled** for {channel.mention}",
                    color=discord.Color.green(),
                )

                embed.add_field(
                    name="Configuration",
                    value=f"• High activity (≥{self.HIGH_RATE_THRESHOLD} msg/min): {self.HIGH_RATE_SLOWMODE}s slowmode\n"
                    f"• Medium activity (≥{self.LOW_RATE_THRESHOLD} msg/min): {self.LOW_RATE_SLOWMODE}s slowmode\n"
                    f"• Low activity: No slowmode",
                    inline=False,
                )

            if hasattr(interaction, 'followup'):
                await interaction.followup.send(embed=embed)
            else:
                await interaction.send(embed=embed)

        except Exception as e:
            log.error(f"Error in toggle action: {e}")
            if hasattr(interaction, 'followup'):
                await interaction.followup.send(
                    "❌ An error occurred while toggling auto rate limiting.",
                    ephemeral=True,
                )
            else:
                await interaction.send(
                    "❌ An error occurred while toggling auto rate limiting."
                )

    async def handle_enable_action(
        self,
        interaction: discord.Interaction,
        guild_id: int,
        channel: discord.TextChannel,
    ):
        """Handle enable action for auto rate limiting."""
        try:
            # Enable guild-wide auto rate if not already enabled
            if not await self.is_auto_rate_enabled(guild_id):
                await set_guild_config(guild_id, "AUTO_RATE_ENABLED", True)

            await self.enable_channel_auto_rate(guild_id, channel.id)

            embed = discord.Embed(
                title="✅ Auto Rate Limiting Enabled",
                description=f"Automatic rate limiting has been **enabled** for {channel.mention}",
                color=discord.Color.green(),
            )

            embed.add_field(
                name="Configuration",
                value=f"• High activity (≥{self.HIGH_RATE_THRESHOLD} msg/min): {self.HIGH_RATE_SLOWMODE}s slowmode\n"
                f"• Medium activity (≥{self.LOW_RATE_THRESHOLD} msg/min): {self.LOW_RATE_SLOWMODE}s slowmode\n"
                f"• Low activity: No slowmode",
                inline=False,
            )

            if hasattr(interaction, 'followup'):
                await interaction.followup.send(embed=embed)
            else:
                await interaction.send(embed=embed)

        except Exception as e:
            log.error(f"Error in enable action: {e}")
            if hasattr(interaction, 'followup'):
                await interaction.followup.send(
                    "❌ An error occurred while enabling auto rate limiting.",
                    ephemeral=True,
                )
            else:
                await interaction.send(
                    "❌ An error occurred while enabling auto rate limiting."
                )

    async def handle_disable_action(
        self,
        interaction: discord.Interaction,
        guild_id: int,
        channel: discord.TextChannel,
    ):
        """Handle disable action for auto rate limiting."""
        try:
            await self.disable_channel_auto_rate(guild_id, channel.id)

            # Reset slowmode to 0
            if channel.permissions_for(interaction.guild.me).manage_channels:
                await channel.edit(slowmode_delay=0)

            embed = discord.Embed(
                title="✅ Auto Rate Limiting Disabled",
                description=f"Automatic rate limiting has been **disabled** for {channel.mention}",
                color=discord.Color.red(),
                )

            if hasattr(interaction, 'followup'):
                await interaction.followup.send(embed=embed)
            else:
                await interaction.send(embed=embed)

        except Exception as e:
            log.error(f"Error in disable action: {e}")
            if hasattr(interaction, 'followup'):
                await interaction.followup.send(
                    "❌ An error occurred while toggling auto rate limiting.",
                    ephemeral=True,
                )
            else:
                await interaction.send(
                    "❌ An error occurred while toggling auto rate limiting."
                )

    async def handle_status_action(
        self,
        interaction: discord.Interaction,
        guild_id: int,
        channel: discord.TextChannel,
    ):
        """Handle status action to show current configuration."""
        try:
            guild_enabled = await self.is_auto_rate_enabled(guild_id)
            channel_enabled = await self.is_channel_auto_rate_enabled(
                guild_id, channel.id
            )

            # Get current activity stats
            current_time = datetime.now(SINGAPORE_TZ)
            analysis_cutoff = current_time - timedelta(seconds=self.ANALYSIS_WINDOW)

            recent_messages = [
                timestamp
                for timestamp in self.message_history[channel.id]
                if timestamp >= analysis_cutoff
            ]

            messages_per_minute = len(recent_messages)
            activity_level = self.get_activity_level(messages_per_minute)
            current_slowmode = channel.slowmode_delay

            embed = discord.Embed(
                title=f"📊 Auto Rate Limiting Status - #{channel.name}",
                description=f"🕐 Using Singapore Time (UTC+8)",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Guild Status",
                value="✅ Enabled" if guild_enabled else "❌ Disabled",
                inline=True,
            )

            embed.add_field(
                name="Channel Status",
                value="✅ Enabled" if channel_enabled else "❌ Disabled",
                inline=True,
            )

            embed.add_field(
                name="Current Slowmode", value=f"{current_slowmode}s", inline=True
            )

            embed.add_field(
                name="Current Activity",
                value=f"{activity_level} ({messages_per_minute} msg/min)",
                inline=True,
            )

            embed.add_field(
                name="Thresholds",
                value=f"High: ≥{self.HIGH_RATE_THRESHOLD} msg/min\nMedium: ≥{self.LOW_RATE_THRESHOLD} msg/min",
                inline=True,
            )

            embed.add_field(
                name="Slowmode Settings",
                value=f"High: {self.HIGH_RATE_SLOWMODE}s\nMedium: {self.LOW_RATE_SLOWMODE}s\nLow: {self.NO_SLOWMODE}s",
                inline=True,
            )

            # Get enabled channels for this guild
            enabled_channels = await get_guild_config(
                guild_id, "AUTO_RATE_CHANNELS", []
            )
            if enabled_channels:
                channel_mentions = []
                for ch_id in enabled_channels[
                    :10
                ]:  # Limit to 10 channels to avoid embed limits
                    ch = interaction.guild.get_channel(ch_id)
                    if ch:
                        channel_mentions.append(ch.mention)

                if channel_mentions:
                    embed.add_field(
                        name=f"Enabled Channels ({len(enabled_channels)})",
                        value="\n".join(channel_mentions)
                        + ("..." if len(enabled_channels) > 10 else ""),
                        inline=False,
                    )

            if hasattr(interaction, 'followup'):
                await interaction.followup.send(embed=embed)
            else:
                await interaction.send(embed=embed)

        except Exception as e:
            log.error(f"Error in status action: {e}")
            if hasattr(interaction, 'followup'):
                await interaction.followup.send(
                    "❌ An error occurred while getting status.",
                    ephemeral=True,
                )
            else:
                await interaction.send(
                    "❌ An error occurred while getting status."
                )

    async def handle_config_action(
        self,
        interaction: discord.Interaction,
        guild_id: int,
        notifications: Optional[bool],
        notification_channel: Optional[discord.TextChannel],
    ):
        """Handle config action for global settings."""
        try:
            changes = []

            if notifications is not None:
                await set_guild_config(guild_id, "AUTO_RATE_NOTIFY", notifications)
                changes.append(
                    f"Notifications: {'✅ Enabled' if notifications else '❌ Disabled'}"
                )

            if notification_channel is not None:
                await set_guild_config(
                    guild_id, "AUTO_RATE_NOTIFY_CHANNEL", notification_channel.id
                )
                changes.append(f"Notification channel: {notification_channel.mention}")

            if not changes:
                # Show current config
                notify_enabled = await get_guild_config(
                    guild_id, "AUTO_RATE_NOTIFY", False
                )
                notify_channel_id = await get_guild_config(
                    guild_id, "AUTO_RATE_NOTIFY_CHANNEL", None
                )
                notify_channel = (
                    interaction.guild.get_channel(notify_channel_id)
                    if notify_channel_id
                    else None
                )

                embed = discord.Embed(
                    title="⚙️ Auto Rate Limiting Configuration",
                    color=discord.Color.blue(),
                )

                embed.add_field(
                    name="Notifications",
                    value="✅ Enabled" if notify_enabled else "❌ Disabled",
                    inline=True,
                )

                embed.add_field(
                    name="Notification Channel",
                    value=notify_channel.mention if notify_channel else "Not set",
                    inline=True,
                )

                embed = discord.Embed(
                    title="⚙️ Auto Rate Limiting Configuration",
                    color=discord.Color.blue(),
                )

                embed.add_field(
                    name="Notifications",
                    value="✅ Enabled" if notify_enabled else "❌ Disabled",
                    inline=True,
                )

                embed.add_field(
                    name="Notification Channel",
                    value=notify_channel.mention if notify_channel else "Not set",
                    inline=True,
                )

            if hasattr(interaction, 'followup'):
                await interaction.followup.send(embed=embed)
            else:
                await interaction.send(embed=embed)

        except Exception as e:
            log.error(f"Error in config action: {e}")
            if hasattr(interaction, 'followup'):
                await interaction.followup.send(
                    "❌ An error occurred while updating configuration.", ephemeral=True
                )
            else:
                await interaction.send(
                    "❌ An error occurred while updating configuration."
                )


async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(MessageRateCog(bot))

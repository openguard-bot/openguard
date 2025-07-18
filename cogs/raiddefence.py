import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import json
import os
from collections import defaultdict, deque
from .aimod_helpers.config_manager import (
    get_guild_config_async,
    set_guild_config,
    save_guild_config,
)


class RaidDefenceView(discord.ui.View):
    """View with Stop Raid button for guild owners"""

    def __init__(self, guild_id: int, suspicious_users: list, cog):
        super().__init__(timeout=300)  # 5 minute timeout
        self.guild_id = guild_id
        self.suspicious_users = suspicious_users
        self.cog = cog

    @discord.ui.button(label="Stop Raid", style=discord.ButtonStyle.danger, emoji="🛡️")
    async def stop_raid(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Check if user is guild owner
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "Only the server owner can stop raids.", ephemeral=True
            )
            return

        await interaction.response.defer()

        banned_count = 0
        failed_bans = []

        for user_id in self.suspicious_users:
            try:
                user = interaction.guild.get_member(user_id)
                if user:
                    await interaction.guild.ban(
                        user,
                        reason="Raid Defense: Suspicious join pattern detected",
                        delete_message_days=1,
                    )
                    banned_count += 1
                    print(
                        f"[RAID DEFENSE] Banned user {user} ({user_id}) from guild {interaction.guild.name}"
                    )
            except discord.Forbidden:
                failed_bans.append(user_id)
                print(
                    f"[RAID DEFENSE] Failed to ban user {user_id} - insufficient permissions"
                )
            except discord.HTTPException as e:
                failed_bans.append(user_id)
                print(f"[RAID DEFENSE] Failed to ban user {user_id} - HTTP error: {e}")

        # Create response embed
        embed = discord.Embed(
            title="🛡️ Raid Defense Activated",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Users Banned", value=str(banned_count), inline=True)
        embed.add_field(name="Failed Bans", value=str(len(failed_bans)), inline=True)
        embed.add_field(
            name="Total Processed", value=str(len(self.suspicious_users)), inline=True
        )

        if failed_bans:
            embed.add_field(
                name="Failed Ban User IDs",
                value=", ".join(str(uid) for uid in failed_bans[:10])
                + ("..." if len(failed_bans) > 10 else ""),
                inline=False,
            )

        embed.set_footer(text="Raid defense completed")

        # Disable the button
        button.disabled = True
        await interaction.edit_original_response(view=self)

        # Send completion message
        await interaction.followup.send(embed=embed, ephemeral=False)

        # Log to aimod log if configured
        await self.cog.log_raid_action(
            interaction.guild, banned_count, len(failed_bans)
        )


class RaidDefenceCog(commands.Cog):
    """Raid Defense System for detecting and preventing server raids"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.join_tracking = defaultdict(
            lambda: deque(maxlen=50)
        )  # Track last 50 joins per guild
        self.raid_cooldowns = defaultdict(float)  # Prevent spam alerts

    # Security command group
    @commands.hybrid_group(
        name="security", description="Security and raid defense commands."
    )
    async def security(self, ctx: commands.Context):
        """Security and raid defense commands."""
        await ctx.send_help(ctx.command)

    @security.group(name="raid", description="Raid defense configuration.")
    async def raid(self, ctx: commands.Context):
        """Raid defense configuration."""
        await ctx.send_help(ctx.command)

    @raid.command(name="config", description="Configure raid defense settings.")
    @app_commands.describe(
        enable="Enable or disable raid defense (true/false)",
        threshold="Number of joins in timeframe to trigger alert (default: 10)",
        timeframe="Timeframe in seconds to monitor joins (default: 60)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def raid_config(
        self,
        interaction: discord.Interaction,
        enable: bool,
        threshold: int = 10,
        timeframe: int = 60,
    ):
        """Configure raid defense settings for the guild"""

        if threshold < 3 or threshold > 50:
            await interaction.response.send_message(
                "Threshold must be between 3 and 50 users.", ephemeral=True
            )
            return

        if timeframe < 30 or timeframe > 300:
            await interaction.response.send_message(
                "Timeframe must be between 30 and 300 seconds.", ephemeral=True
            )
            return

        guild_id = interaction.guild.id

        # Save configuration
        await set_guild_config(guild_id, "RAID_DEFENSE_ENABLED", enable)
        await set_guild_config(guild_id, "RAID_DEFENSE_THRESHOLD", threshold)
        await set_guild_config(guild_id, "RAID_DEFENSE_TIMEFRAME", timeframe)

        embed = discord.Embed(
            title="🛡️ Raid Defense Configuration",
            color=discord.Color.green() if enable else discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Status", value="Enabled" if enable else "Disabled", inline=True
        )
        embed.add_field(name="Threshold", value=f"{threshold} users", inline=True)
        embed.add_field(name="Timeframe", value=f"{timeframe} seconds", inline=True)

        user = interaction.user if hasattr(interaction, "user") else interaction.author
        embed.set_footer(text=f"Configured by {user}")

        if hasattr(interaction, "response"):
            await interaction.response.send_message(embed=embed, ephemeral=False)
        else:
            await interaction.send(embed=embed, ephemeral=False)
        print(
            f"[RAID DEFENSE] Configuration updated for guild {interaction.guild.name}: enabled={enable}, threshold={threshold}, timeframe={timeframe}"
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Monitor member joins for potential raids"""
        guild_id = member.guild.id

        # Check if raid defense is enabled
        if not await get_guild_config_async(guild_id, "RAID_DEFENSE_ENABLED", False):
            return

        # Get configuration
        threshold = await get_guild_config_async(guild_id, "RAID_DEFENSE_THRESHOLD", 10)
        timeframe = await get_guild_config_async(guild_id, "RAID_DEFENSE_TIMEFRAME", 60)

        # Add join to tracking
        current_time = datetime.datetime.utcnow().timestamp()
        self.join_tracking[guild_id].append(
            {
                "user_id": member.id,
                "timestamp": current_time,
                "account_age": (
                    datetime.datetime.utcnow() - member.created_at
                ).total_seconds(),
            }
        )

        # Check for raid pattern
        await self.check_raid_pattern(member.guild, threshold, timeframe)

    async def check_raid_pattern(
        self, guild: discord.Guild, threshold: int, timeframe: int
    ):
        """Check if current join pattern indicates a raid"""
        guild_id = guild.id
        current_time = datetime.datetime.utcnow().timestamp()

        # Check cooldown to prevent spam alerts
        if current_time - self.raid_cooldowns[guild_id] < 300:  # 5 minute cooldown
            return

        # Get recent joins within timeframe
        recent_joins = [
            join
            for join in self.join_tracking[guild_id]
            if current_time - join["timestamp"] <= timeframe
        ]

        if len(recent_joins) >= threshold:
            # Analyze suspiciousness
            suspicious_users = self.analyze_suspicious_joins(recent_joins)

            if len(suspicious_users) >= max(
                3, threshold // 2
            ):  # At least 3 or half the threshold
                await self.trigger_raid_alert(
                    guild, suspicious_users, len(recent_joins)
                )
                self.raid_cooldowns[guild_id] = current_time

    def analyze_suspicious_joins(self, recent_joins: list) -> list:
        """Analyze joins to identify suspicious patterns"""
        suspicious_users = []

        for join in recent_joins:
            suspicion_score = 0

            # Very new accounts (less than 1 day old)
            if join["account_age"] < 86400:  # 1 day
                suspicion_score += 3
            # New accounts (less than 1 week old)
            elif join["account_age"] < 604800:  # 1 week
                suspicion_score += 2
            # Somewhat new accounts (less than 1 month old)
            elif join["account_age"] < 2592000:  # 1 month
                suspicion_score += 1

            # If suspicion score is high enough, mark as suspicious
            if suspicion_score >= 2:
                suspicious_users.append(join["user_id"])

        return suspicious_users

    async def trigger_raid_alert(
        self, guild: discord.Guild, suspicious_users: list, total_joins: int
    ):
        """Trigger raid alert and send notifications"""
        print(
            f"[RAID DEFENSE] Potential raid detected in guild {guild.name}: {total_joins} joins, {len(suspicious_users)} suspicious"
        )

        # Create alert embed
        embed = discord.Embed(
            title="🚨 Potential Raid Detected",
            description=f"Suspicious join activity detected in **{guild.name}**",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Total Recent Joins", value=str(total_joins), inline=True)
        embed.add_field(
            name="Suspicious Users", value=str(len(suspicious_users)), inline=True
        )
        embed.add_field(name="Server", value=guild.name, inline=True)
        embed.set_footer(text="Click 'Stop Raid' to ban all suspicious users")

        # Create view with stop raid button
        view = RaidDefenceView(guild.id, suspicious_users, self)

        # Send to guild owner
        try:
            owner = guild.owner
            if owner:
                await owner.send(embed=embed, view=view)
                print(f"[RAID DEFENSE] Alert sent to guild owner {owner}")
        except discord.Forbidden:
            print(f"[RAID DEFENSE] Could not DM guild owner {guild.owner}")

        # Send to mod log channel if configured
        mod_log_channel_id = await get_guild_config_async(
            guild.id, "MOD_LOG_CHANNEL_ID"
        )
        if mod_log_channel_id:
            mod_log_channel = guild.get_channel(mod_log_channel_id)
            if mod_log_channel:
                try:
                    await mod_log_channel.send(embed=embed, view=view)
                    print(f"[RAID DEFENSE] Alert sent to mod log channel")
                except discord.Forbidden:
                    print(f"[RAID DEFENSE] Could not send to mod log channel")

        # Send to general channel as fallback
        general_channel = discord.utils.get(guild.text_channels, name="general")
        if general_channel and general_channel.permissions_for(guild.me).send_messages:
            try:
                await general_channel.send(
                    f"🚨 **RAID ALERT** - {guild.owner.mention if guild.owner else 'Server Owner'}",
                    embed=embed,
                    view=view,
                )
                print(f"[RAID DEFENSE] Alert sent to general channel")
            except discord.Forbidden:
                print(f"[RAID DEFENSE] Could not send to general channel")

    async def log_raid_action(
        self, guild: discord.Guild, banned_count: int, failed_count: int
    ):
        """Log raid defense action to aimod log"""
        mod_log_channel_id = await get_guild_config_async(
            guild.id, "MOD_LOG_CHANNEL_ID"
        )
        if mod_log_channel_id:
            mod_log_channel = guild.get_channel(mod_log_channel_id)
            if mod_log_channel:
                embed = discord.Embed(
                    title="🛡️ Raid Defense Action Completed",
                    color=discord.Color.orange(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.add_field(
                    name="Users Banned", value=str(banned_count), inline=True
                )
                embed.add_field(
                    name="Failed Bans", value=str(failed_count), inline=True
                )
                embed.set_footer(text="Automated raid defense system")

                try:
                    await mod_log_channel.send(embed=embed)
                except discord.Forbidden:
                    pass


async def setup(bot):
    await bot.add_cog(RaidDefenceCog(bot))

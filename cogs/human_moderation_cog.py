import discord
from discord.ext import commands
from discord import app_commands, Object

from cogs.ban_appeal_cog import BanAppealView
import datetime
import logging
from typing import Optional, Union, List

# Use absolute import for ModLogCog
from cogs.mod_log_cog import ModLogCog
from .logging_helpers import mod_log_db

# Configure logging
logger = logging.getLogger(__name__)


class HumanModerationCog(commands.Cog):
    """Real moderation commands that perform actual moderation actions."""

    def __init__(self, bot):
        self.bot = bot

        # Create the main command group for this cog

    @commands.hybrid_group(
        name="moderate", description="Moderation commands for server management"
    )
    async def moderate(self, ctx: commands.Context):
        """Moderation commands for server management"""
        await ctx.send_help(ctx.command)

        # Register commands
        # Add command group to the bot's tree
        self.bot.tree.add_command(self.moderate)

    def _user_display(self, user: Union[discord.Member, discord.User]) -> str:
        """Return display name, username and ID string for a user."""
        display = user.display_name if isinstance(user, discord.Member) else user.name
        username = f"{user.name}#{user.discriminator}"
        return f"{display} ({username}) [ID: {user.id}]"

    # Helper method for parsing duration strings
    def _parse_duration(self, duration_str: str) -> Optional[datetime.timedelta]:
        """
        Parse a duration string like '1w2d3h4m' into a timedelta.
        Supports: w (weeks), d (days), h (hours), m (minutes), s (seconds).
        """
        if not duration_str:
            return None

        import re

        regex = re.compile(r"(\d+)([wdhms])")
        matches = regex.findall(duration_str.lower())

        if not matches:
            return None

        total_seconds = 0
        for amount, unit in matches:
            amount = int(amount)
            if unit == "w":
                total_seconds += amount * 604800
            elif unit == "d":
                total_seconds += amount * 86400
            elif unit == "h":
                total_seconds += amount * 3600
            elif unit == "m":
                total_seconds += amount * 60
            elif unit == "s":
                total_seconds += amount

        return datetime.timedelta(seconds=total_seconds)

    # --- Command Callbacks ---

    @moderate.command(
        name="ban",
        description="Ban a user from the server, by member object or user ID",
    )
    @app_commands.describe(
        member="The member to ban (if in the server)",
        user_id="The ID of the user to ban (if not in the server)",
        reason="The reason for the ban",
        delete_days="Number of days of messages to delete (0-7)",
        send_dm="Whether to send a DM notification to the user (default: True)",
    )
    async def moderate_ban_callback(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        user_id: Optional[str] = None,
        reason: str = None,
        delete_days: int = 0,
        send_dm: bool = True,
    ):
        """Ban a user from the server, by member object or user ID."""
        if (member and user_id) or (not member and not user_id):
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "❌ Please provide either a member or a user ID, but not both.",
                    ephemeral=True,
                )
            else:
                await ctx.send(
                    "❌ Please provide either a member or a user ID, but not both."
                )
            return

        target: Union[discord.Member, discord.User, Object]

        # --- Resolve Target ---
        if user_id:
            try:
                user_id_int = int(user_id)
                target = discord.Object(id=user_id_int)
            except ValueError:
                if ctx.interaction:
                    await ctx.interaction.response.send_message(
                        "❌ Invalid user ID. Please provide a valid user ID.",
                        ephemeral=True,
                    )
                else:
                    await ctx.send(
                        "❌ Invalid user ID. Please provide a valid user ID."
                    )
                return
        else:
            target = member

        # --- Permission Checks ---
        if not ctx.author.guild_permissions.ban_members:
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "❌ You don't have permission to ban members.", ephemeral=True
                )
            else:
                await ctx.send("❌ You don't have permission to ban members.")
            return

        if not ctx.guild.me.guild_permissions.ban_members:
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "❌ I don't have permission to ban members.", ephemeral=True
                )
            else:
                await ctx.send("❌ I don't have permission to ban members.")
            return

        # --- Target Checks ---
        if target.id == ctx.author.id:
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "❌ You cannot ban yourself.", ephemeral=True
                )
            else:
                await ctx.send("❌ You cannot ban yourself.")
            return

        if target.id == self.bot.user.id:
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "❌ I cannot ban myself.", ephemeral=True
                )
            else:
                await ctx.send("❌ I cannot ban myself.")
            return

        # If the target is a member in the server, perform role hierarchy checks
        if isinstance(target, discord.Member):
            if (
                ctx.author.top_role.position <= target.top_role.position
                and ctx.author.id != ctx.guild.owner_id
            ):
                if ctx.interaction:
                    await ctx.interaction.response.send_message(
                        "❌ You cannot ban someone with a higher or equal role.",
                        ephemeral=True,
                    )
                else:
                    await ctx.send(
                        "❌ You cannot ban someone with a higher or equal role."
                    )
                return
            if ctx.guild.me.top_role.position <= target.top_role.position:
                if ctx.interaction:
                    await ctx.interaction.response.send_message(
                        "❌ I cannot ban someone with a higher or equal role than me.",
                        ephemeral=True,
                    )
                else:
                    await ctx.send(
                        "❌ I cannot ban someone with a higher or equal role than me."
                    )
                return

        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=False)

        # --- Perform Ban ---
        try:
            # Ensure delete_days is within valid range (0-7)
            delete_days = max(0, min(7, delete_days))

            # Fetch the user object for logging and DMing.
            # This is now done *before* the ban to ensure we have the object.
            full_user_object: Optional[Union[discord.User, discord.Member]] = None
            if isinstance(target, discord.Member):
                full_user_object = target
            else:
                try:
                    full_user_object = await self.bot.fetch_user(target.id)
                except discord.NotFound:
                    # This is a special case. The user doesn't exist on Discord.
                    # We can still ban the ID, but we can't DM or get their name.
                    pass

            # --- Send DM ---
            dm_sent = False
            if send_dm and full_user_object:
                try:
                    embed = discord.Embed(
                        title="Ban Notice",
                        description=f"You have been banned from **{ctx.guild.name}**",
                        color=discord.Color.red(),
                    )
                    embed.add_field(
                        name="Reason",
                        value=reason or "No reason provided",
                        inline=False,
                    )
                    embed.add_field(
                        name="Moderator", value=ctx.author.name, inline=False
                    )
                    embed.set_footer(
                        text=f"Server ID: {ctx.guild.id} • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC • Use the button or send !banappeal to appeal"
                    )
                    await full_user_object.send(
                        embed=embed, view=BanAppealView(ctx.guild.id)
                    )
                    dm_sent = True
                except discord.Forbidden:
                    pass  # User has DMs closed or is not fetchable
                except Exception as e:
                    logger.error(
                        f"Error sending ban DM to {full_user_object} (ID: {full_user_object.id}): {e}"
                    )

            # Use the original target (Object or Member) for the ban action
            await ctx.guild.ban(target, reason=reason, delete_message_days=delete_days)

            # --- Logging ---
            log_target = full_user_object or target  # Use full object if available
            logger.info(
                f"User {log_target} (ID: {log_target.id}) was banned from {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id}). Reason: {reason}"
            )

            mod_log_cog: ModLogCog = self.bot.get_cog("ModLogCog")
            if mod_log_cog:
                await mod_log_cog.log_action(
                    guild=ctx.guild,
                    moderator=ctx.author,
                    target=log_target,
                    action_type="BAN",
                    reason=reason,
                    duration=None,
                )

            # --- Confirmation Message ---
            target_text = (
                self._user_display(log_target)
                if full_user_object
                else f"User ID `{target.id}`"
            )
            dm_status = ""
            if send_dm:
                dm_status = (
                    "✅ DM notification sent"
                    if dm_sent
                    else "❌ Could not send DM notification (user may have DMs disabled or could not be fetched)"
                )

            response_message = (
                f"🔨 **Banned {target_text}**! Reason: {reason or 'No reason provided'}"
            )
            if dm_status:
                response_message += f"\n{dm_status}"

            if ctx.interaction:
                await ctx.interaction.followup.send(response_message, ephemeral=False)
            else:
                await ctx.send(response_message)

        except discord.NotFound:
            # This is raised by guild.ban if the user_id is invalid
            if ctx.interaction:
                await ctx.interaction.followup.send(
                    f"❌ Could not find a user with the ID `{target.id}`.",
                    ephemeral=True,
                )
            else:
                await ctx.send(f"❌ Could not find a user with the ID `{target.id}`.")
        except discord.Forbidden:
            if ctx.interaction:
                await ctx.interaction.followup.send(
                    "❌ I don't have permission to ban this user. My role might be too low or I lack the 'Ban Members' permission.",
                    ephemeral=True,
                )
            else:
                await ctx.send(
                    "❌ I don't have permission to ban this user. My role might be too low or I lack the 'Ban Members' permission."
                )
        except discord.HTTPException as e:
            # Check for "already banned" error string, as there's no specific exception
            if "already banned" in str(e).lower():
                if ctx.interaction:
                    await ctx.interaction.followup.send(
                        f"❌ User with ID `{target.id}` is already banned.",
                        ephemeral=True,
                    )
                else:
                    await ctx.send(f"❌ User with ID `{target.id}` is already banned.")
            elif ctx.interaction:
                await ctx.interaction.followup.send(
                    f"❌ An error occurred while banning the user: {e}", ephemeral=True
                )
            else:
                await ctx.send(f"❌ An error occurred while banning the user: {e}")

    @moderate.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user_id="The ID of the user to unban", reason="The reason for the unban"
    )
    async def moderate_unban_callback(
        self, ctx: commands.Context, user_id: str, reason: str = None
    ):
        """Unban a user from the server."""
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True, thinking=False)

        async def send_response(message, ephemeral=True):
            if ctx.interaction:
                if ctx.interaction.response.is_done():
                    await ctx.interaction.followup.send(message, ephemeral=ephemeral)
                else:
                    await ctx.interaction.response.send_message(
                        message, ephemeral=ephemeral
                    )
            else:
                await ctx.send(message)

        # Check if the user has permission to ban members (which includes unbanning)
        if not ctx.author.guild_permissions.ban_members:
            await send_response("❌ You don't have permission to unban users.")
            return

        # Check if the bot has permission to ban members (which includes unbanning)
        if not ctx.guild.me.guild_permissions.ban_members:
            await send_response("❌ I don't have permission to unban users.")
            return

        # Validate user ID
        try:
            user_id_int = int(user_id)
        except ValueError:
            await send_response("❌ Invalid user ID. Please provide a valid user ID.")
            return

        # Check if the user is banned
        try:
            ban_entry = await ctx.guild.fetch_ban(discord.Object(id=user_id_int))
            banned_user = ban_entry.user
        except discord.NotFound:
            await send_response("❌ This user is not banned.")
            return
        except discord.Forbidden:
            await send_response("❌ I don't have permission to view the ban list.")
            return
        except discord.HTTPException as e:
            await send_response(
                f"❌ An error occurred while checking the ban list: {e}"
            )
            return

        # Perform the unban
        try:
            await ctx.guild.unban(banned_user, reason=reason)

            # Log the action
            logger.info(
                f"User {banned_user} (ID: {banned_user.id}) was unbanned from {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id}). Reason: {reason}"
            )

            # --- Add to Mod Log DB ---
            mod_log_cog: ModLogCog = self.bot.get_cog("ModLogCog")
            if mod_log_cog:
                await mod_log_cog.log_action(
                    guild=ctx.guild,
                    moderator=ctx.author,
                    target=banned_user,  # Use the fetched user object
                    action_type="UNBAN",
                    reason=reason,
                    duration=None,
                )
            # -------------------------

            # Send confirmation message
            await send_response(
                f"🔓 **Unbanned {self._user_display(banned_user)}**! Reason: {reason or 'No reason provided'}",
                ephemeral=False,  # Public confirmation
            )
        except discord.Forbidden:
            await send_response("❌ I don't have permission to unban this user.")
        except discord.HTTPException as e:
            await send_response(f"❌ An error occurred while unbanning the user: {e}")

    @moderate.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(
        member="The member to kick", reason="The reason for the kick"
    )
    async def moderate_kick_callback(
        self,
        ctx: commands.Context,
        member: discord.Member,
        reason: str = None,
    ):
        """Kick a member from the server."""
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=False)

        async def send_response(message, ephemeral=True):
            if ctx.interaction:
                if ctx.interaction.response.is_done():
                    await ctx.interaction.followup.send(message, ephemeral=ephemeral)
                else:
                    await ctx.interaction.response.send_message(
                        message, ephemeral=ephemeral
                    )
            else:
                await ctx.send(message)

        # Check if the user has permission to kick members
        if not ctx.author.guild_permissions.kick_members:
            await send_response(
                "❌ You don't have permission to kick members.", ephemeral=True
            )
            return

        # Check if the bot has permission to kick members
        if not ctx.guild.me.guild_permissions.kick_members:
            await send_response(
                "❌ I don't have permission to kick members.", ephemeral=True
            )
            return

        # Check if the user is trying to kick themselves
        if member.id == ctx.author.id:
            await send_response("❌ You cannot kick yourself.", ephemeral=True)
            return

        # Check if the user is trying to kick the bot
        if member.id == self.bot.user.id:
            await send_response("❌ I cannot kick myself.", ephemeral=True)
            return

        # Check if the user is trying to kick someone with a higher role
        if (
            ctx.author.top_role.position <= member.top_role.position
            and ctx.author.id != ctx.guild.owner_id
        ):
            await send_response(
                "❌ You cannot kick someone with a higher or equal role.",
                ephemeral=True,
            )
            return

        # Check if the bot can kick the member (role hierarchy)
        if ctx.guild.me.top_role.position <= member.top_role.position:
            await send_response(
                "❌ I cannot kick someone with a higher or equal role than me.",
                ephemeral=True,
            )
            return

        # Try to send a DM to the user before kicking them
        dm_sent = False
        try:
            embed = discord.Embed(
                title="Kick Notice",
                description=f"You have been kicked from **{ctx.guild.name}**",
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="Reason", value=reason or "No reason provided", inline=False
            )
            embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
            embed.set_footer(
                text=f"Server ID: {ctx.guild.id} • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            # User has DMs closed, ignore
            pass
        except Exception as e:
            logger.error(f"Error sending kick DM to {member} (ID: {member.id}): {e}")

        # Perform the kick
        try:
            await member.kick(reason=reason)

            # Log the action
            logger.info(
                f"User {member} (ID: {member.id}) was kicked from {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id}). Reason: {reason}"
            )

            # --- Add to Mod Log DB ---
            mod_log_cog: ModLogCog = self.bot.get_cog("ModLogCog")
            if mod_log_cog:
                await mod_log_cog.log_action(
                    guild=ctx.guild,
                    moderator=ctx.author,
                    target=member,
                    action_type="KICK",
                    reason=reason,
                    duration=None,
                )
            # -------------------------

            # Send confirmation message with DM status
            dm_status = (
                "✅ DM notification sent"
                if dm_sent
                else "❌ Could not send DM notification (user may have DMs disabled)"
            )
            await send_response(
                f"👢 **Kicked {self._user_display(member)}**! Reason: {reason or 'No reason provided'}\n{dm_status}",
                ephemeral=False,
            )
        except discord.Forbidden:
            await send_response(
                "❌ I don't have permission to kick this member.", ephemeral=True
            )
        except discord.HTTPException as e:
            await send_response(
                f"❌ An error occurred while kicking the member: {e}", ephemeral=True
            )

    @moderate.command(name="timeout", description="Timeout a member in the server")
    @app_commands.describe(
        member="The member to timeout",
        duration="The duration of the timeout (e.g., '1d', '2h', '30m', '60s')",
        reason="The reason for the timeout",
    )
    async def moderate_timeout_callback(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: str,
        reason: str = None,
    ):
        """Timeout a member in the server."""
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=False)

        async def send_response(message, ephemeral=True, embed=None):
            if ctx.interaction:
                # After deferring, we must use followup
                await ctx.interaction.followup.send(
                    message, ephemeral=ephemeral, embed=embed
                )
            else:
                await ctx.send(message, embed=embed)

        # Check if the user has permission to moderate members
        if not ctx.author.guild_permissions.moderate_members:
            await send_response(
                "❌ You don't have permission to timeout members.", ephemeral=True
            )
            return

        # Check if the bot has permission to moderate members
        if not ctx.guild.me.guild_permissions.moderate_members:
            await send_response(
                "❌ I don't have permission to timeout members.", ephemeral=True
            )
            return

        # Check if the user is trying to timeout themselves
        if member.id == ctx.author.id:
            await send_response("❌ You cannot timeout yourself.", ephemeral=True)
            return

        # Check if the user is trying to timeout the bot
        if member.id == self.bot.user.id:
            await send_response("❌ I cannot timeout myself.", ephemeral=True)
            return

        # Check if the user is trying to timeout someone with a higher role
        if (
            ctx.author.top_role.position <= member.top_role.position
            and ctx.author.id != ctx.guild.owner_id
        ):
            await send_response(
                "❌ You cannot timeout someone with a higher or equal role.",
                ephemeral=True,
            )
            return

        # Check if the bot can timeout the member (role hierarchy)
        if ctx.guild.me.top_role.position <= member.top_role.position:
            await send_response(
                "❌ I cannot timeout someone with a higher or equal role than me.",
                ephemeral=True,
            )
            return

        # Parse the duration
        delta = self._parse_duration(duration)
        if not delta:
            await send_response(
                "❌ Invalid duration format. Please use formats like '1d', '2h', '30m', or '60s'.",
                ephemeral=True,
            )
            return

        # Check if the duration is within Discord's limits (max 28 days)
        max_timeout = datetime.timedelta(days=28)
        if delta > max_timeout:
            await send_response(
                "❌ Timeout duration cannot exceed 28 days.", ephemeral=True
            )
            return

        # Calculate the end time
        until = discord.utils.utcnow() + delta

        # Try to send a DM to the user before timing them out
        dm_sent = False
        try:
            embed = discord.Embed(
                title="Timeout Notice",
                description=f"You have been timed out in **{ctx.guild.name}** for {duration}",
                color=discord.Color.gold(),
            )
            embed.add_field(
                name="Reason", value=reason or "No reason provided", inline=False
            )
            embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
            embed.add_field(name="Duration", value=duration, inline=False)
            embed.add_field(
                name="Expires", value=f"<t:{int(until.timestamp())}:F>", inline=False
            )
            embed.set_footer(
                text=f"Server ID: {ctx.guild.id} • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            # User has DMs closed, ignore
            pass
        except Exception as e:
            logger.error(f"Error sending timeout DM to {member} (ID: {member.id}): {e}")

        # Perform the timeout
        try:
            await member.timeout(until, reason=reason)

            # Log the action
            logger.info(
                f"User {member} (ID: {member.id}) was timed out in {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id}) for {duration}. Reason: {reason}"
            )

            # --- Add to Mod Log DB ---
            mod_log_cog: ModLogCog = self.bot.get_cog("ModLogCog")
            if mod_log_cog:
                await mod_log_cog.log_action(
                    guild=ctx.guild,
                    moderator=ctx.author,
                    target=member,
                    action_type="TIMEOUT",
                    reason=reason,
                    duration=delta,  # Pass the timedelta object
                )
            # -------------------------

            # Send confirmation message with DM status
            dm_status = (
                "✅ DM notification sent"
                if dm_sent
                else "❌ Could not send DM notification (user may have DMs disabled)"
            )
            await send_response(
                f"⏰ **Timed out {self._user_display(member)}** for {duration}! Reason: {reason or 'No reason provided'}\n{dm_status}",
                ephemeral=False,
            )
        except discord.Forbidden:
            await send_response(
                "❌ I don't have permission to timeout this member.", ephemeral=True
            )
        except discord.HTTPException as e:
            await send_response(
                f"❌ An error occurred while timing out the member: {e}", ephemeral=True
            )

    @moderate.command(
        name="removetimeout", description="Remove a timeout from a member"
    )
    @app_commands.describe(
        member="The member to remove timeout from",
        reason="The reason for removing the timeout",
    )
    async def moderate_remove_timeout_callback(
        self,
        ctx: commands.Context,
        member: discord.Member,
        reason: str = None,
    ):
        """Remove a timeout from a member."""
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=False)

        async def send_response(message, ephemeral=True):
            if ctx.interaction:
                if ctx.interaction.response.is_done():
                    await ctx.interaction.followup.send(message, ephemeral=ephemeral)
                else:
                    await ctx.interaction.response.send_message(
                        message, ephemeral=ephemeral
                    )
            else:
                await ctx.send(message)

        # Check if the user has permission to moderate members
        if not ctx.author.guild_permissions.moderate_members:
            await send_response(
                "❌ You don't have permission to remove timeouts.", ephemeral=True
            )
            return

        # Check if the bot has permission to moderate members
        if not ctx.guild.me.guild_permissions.moderate_members:
            await send_response(
                "❌ I don't have permission to remove timeouts.", ephemeral=True
            )
            return

        # Check if the member is timed out
        if not member.timed_out_until:
            await send_response("❌ This member is not timed out.", ephemeral=True)
            return

        # Try to send a DM to the user about the timeout removal
        dm_sent = False
        try:
            embed = discord.Embed(
                title="Timeout Removed",
                description=f"Your timeout in **{ctx.guild.name}** has been removed",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Reason", value=reason or "No reason provided", inline=False
            )
            embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
            embed.set_footer(
                text=f"Server ID: {ctx.guild.id} • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            # User has DMs closed, ignore
            pass
        except Exception as e:
            logger.error(
                f"Error sending timeout removal DM to {member} (ID: {member.id}): {e}"
            )

        # Perform the timeout removal
        try:
            await member.timeout(None, reason=reason)

            # Log the action
            logger.info(
                f"Timeout was removed from user {member} (ID: {member.id}) in {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id}). Reason: {reason}"
            )

            # --- Add to Mod Log DB ---
            mod_log_cog: ModLogCog = self.bot.get_cog("ModLogCog")
            if mod_log_cog:
                await mod_log_cog.log_action(
                    guild=ctx.guild,
                    moderator=ctx.author,
                    target=member,
                    action_type="REMOVE_TIMEOUT",
                    reason=reason,
                    duration=None,
                )
            # -------------------------

            # Send confirmation message with DM status
            dm_status = (
                "✅ DM notification sent"
                if dm_sent
                else "❌ Could not send DM notification (user may have DMs disabled)"
            )
            await send_response(
                f"⏰ **Removed timeout from {self._user_display(member)}**! Reason: {reason or 'No reason provided'}\n{dm_status}",
                ephemeral=False,
            )
        except discord.Forbidden:
            await send_response(
                "❌ I don't have permission to remove the timeout from this member.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await send_response(
                f"❌ An error occurred while removing the timeout: {e}", ephemeral=True
            )

    @moderate.command(
        name="purge", description="Delete a specified number of messages from a channel"
    )
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Optional: Only delete messages from this user",
    )
    async def moderate_purge_callback(
        self,
        ctx: commands.Context,
        amount: int,
        user: Optional[discord.Member] = None,
    ):
        """Delete a specified number of messages from a channel."""
        # For purge, the response should be ephemeral to not clutter the channel
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)

        async def send_response(message, ephemeral=True):
            if ctx.interaction:
                await ctx.interaction.followup.send(message, ephemeral=ephemeral)
            else:
                # For prefix commands, we can send and then delete the response after a delay
                msg = await ctx.send(message)
                await msg.delete(delay=5)

        # Check if the user has permission to manage messages
        if not ctx.author.guild_permissions.manage_messages:
            await send_response("❌ You don't have permission to purge messages.")
            return

        # Check if the bot has permission to manage messages
        if not ctx.guild.me.guild_permissions.manage_messages:
            await send_response("❌ I don't have permission to purge messages.")
            return

        # Validate the amount
        if amount < 1 or amount > 100:
            await send_response(
                "❌ You can only purge between 1 and 100 messages at a time."
            )
            return

        # Perform the purge
        try:
            # We need to handle the channel differently for interaction vs. context
            channel = ctx.channel

            if user:
                # Delete messages from a specific user
                def check(message):
                    return message.author.id == user.id

                deleted = await channel.purge(limit=amount, check=check)

                # Log the action
                logger.info(
                    f"{len(deleted)} messages from user {user} (ID: {user.id}) were purged from channel {channel.name} (ID: {channel.id}) in {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id})."
                )

                # Send confirmation message
                await send_response(
                    f"🧹 **Purged {len(deleted)} messages** from {self._user_display(user)}!"
                )
            else:
                # Delete messages from anyone
                deleted = await channel.purge(limit=amount)

                # Log the action
                logger.info(
                    f"{len(deleted)} messages were purged from channel {channel.name} (ID: {channel.id}) in {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id})."
                )

                # Send confirmation message
                await send_response(f"🧹 **Purged {len(deleted)} messages**!")
        except discord.Forbidden:
            await send_response(
                "❌ I don't have permission to delete messages in this channel."
            )
        except discord.HTTPException as e:
            await send_response(f"❌ An error occurred while purging messages: {e}")

    @moderate.command(name="warn", description="Warn a member in the server")
    @app_commands.describe(
        member="The member to warn", reason="The reason for the warning"
    )
    async def moderate_warn_callback(
        self, ctx: commands.Context, member: discord.Member, reason: str
    ):
        """Warn a member in the server."""
        if ctx.interaction:
            # A warning is a public action, so we don't defer ephemerally
            await ctx.interaction.response.defer(thinking=False)

        async def send_response(message, ephemeral=False):
            if ctx.interaction:
                if ctx.interaction.response.is_done():
                    await ctx.interaction.followup.send(message, ephemeral=ephemeral)
                else:
                    await ctx.interaction.response.send_message(
                        message, ephemeral=ephemeral
                    )
            else:
                await ctx.send(message)

        # Check if the user has permission to kick members (using kick permission as a baseline for warning)
        if not ctx.author.guild_permissions.kick_members:
            await send_response(
                "❌ You don't have permission to warn members.", ephemeral=True
            )
            return

        # Check if the user is trying to warn themselves
        if member.id == ctx.author.id:
            await send_response("❌ You cannot warn yourself.", ephemeral=True)
            return

        # Check if the user is trying to warn the bot
        if member.id == self.bot.user.id:
            await send_response("❌ I cannot warn myself.", ephemeral=True)
            return

        # Check if the user is trying to warn someone with a higher role
        if (
            ctx.author.top_role.position <= member.top_role.position
            and ctx.author.id != ctx.guild.owner_id
        ):
            await send_response(
                "❌ You cannot warn someone with a higher or equal role.",
                ephemeral=True,
            )
            return

        # Log the warning (using standard logger first)
        logger.info(
            f"User {member} (ID: {member.id}) was warned in {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id}). Reason: {reason}"
        )

        # --- Add to Mod Log DB ---
        mod_log_cog: ModLogCog = self.bot.get_cog("ModLogCog")
        if mod_log_cog:
            await mod_log_cog.log_action(
                guild=ctx.guild,
                moderator=ctx.author,
                target=member,
                action_type="WARN",
                reason=reason,
                duration=None,
            )
        # -------------------------

        # Send warning message in the channel
        await send_response(
            f"⚠️ **{self._user_display(member)} has been warned**! Reason: {reason}"
        )

        # Try to DM the user about the warning
        try:
            embed = discord.Embed(
                title="Warning Notice",
                description=f"You have been warned in **{ctx.guild.name}**",
                color=discord.Color.yellow(),
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=ctx.author.name, inline=False)
            embed.set_footer(
                text=f"Server ID: {ctx.guild.id} • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            await member.send(embed=embed)
        except discord.Forbidden:
            # User has DMs closed, ignore
            pass
        except Exception as e:
            logger.error(f"Error sending warning DM to {member} (ID: {member.id}): {e}")

    @moderate.command(name="dmbanned", description="Send a DM to a banned user")
    @app_commands.describe(
        user_id="The ID of the banned user to DM",
        message="The message to send to the banned user",
    )
    async def moderate_dm_banned_callback(
        self, ctx: commands.Context, user_id: str, message: str
    ):
        """Send a DM to a banned user."""
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)

        async def send_response(message, ephemeral=True, embed=None):
            if ctx.interaction:
                await ctx.interaction.followup.send(
                    message, ephemeral=ephemeral, embed=embed
                )
            else:
                await ctx.send(message, embed=embed)

        # Check if the user has permission to ban members
        if not ctx.author.guild_permissions.ban_members:
            await send_response("❌ You don't have permission to DM banned users.")
            return

        # Validate user ID
        try:
            user_id_int = int(user_id)
        except ValueError:
            await send_response("❌ Invalid user ID. Please provide a valid user ID.")
            return

        # Check if the user is banned
        try:
            ban_entry = await ctx.guild.fetch_ban(discord.Object(id=user_id_int))
            banned_user = ban_entry.user
        except discord.NotFound:
            await send_response("❌ This user is not banned.")
            return
        except discord.Forbidden:
            await send_response("❌ I don't have permission to view the ban list.")
            return
        except discord.HTTPException as e:
            await send_response(
                f"❌ An error occurred while checking the ban list: {e}"
            )
            return

        # Try to send a DM to the banned user
        try:
            # Create an embed with the message
            embed = discord.Embed(
                title=f"Message from {ctx.guild.name}",
                description=message,
                color=discord.Color.red(),
            )
            embed.add_field(name="Sent by", value=ctx.author.name, inline=False)
            embed.set_footer(
                text=f"Server ID: {ctx.guild.id} • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            # Send the DM
            await banned_user.send(embed=embed)

            # Log the action
            logger.info(
                f"DM sent to banned user {banned_user} (ID: {banned_user.id}) in {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id})."
            )

            # Send confirmation message
            await send_response(f"✅ **DM sent to banned user {banned_user}**!")
        except discord.Forbidden:
            await send_response(
                "❌ I couldn't send a DM to this user. They may have DMs disabled or have blocked the bot."
            )
        except discord.HTTPException as e:
            await send_response(f"❌ An error occurred while sending the DM: {e}")
        except Exception as e:
            logger.error(
                f"Error sending DM to banned user {banned_user} (ID: {banned_user.id}): {e}"
            )
            await send_response(f"❌ An unexpected error occurred: {e}")

    @moderate.command(
        name="infractions", description="View moderation infractions for a user"
    )
    @app_commands.describe(member="The member whose infractions to view")
    async def moderate_view_infractions_callback(
        self, ctx: commands.Context, member: discord.Member
    ):
        """View moderation infractions for a user."""
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)

        async def send_response(message=None, ephemeral=True, embed=None):
            if ctx.interaction:
                await ctx.interaction.followup.send(
                    message, ephemeral=ephemeral, embed=embed
                )
            else:
                await ctx.send(message, embed=embed)

        if (
            not ctx.author.guild_permissions.kick_members
        ):  # Using kick_members as a general mod permission
            await send_response("❌ You don't have permission to view infractions.")
            return

        if not self.bot.pg_pool:
            await send_response("❌ Database connection is not available.")
            logger.error("Cannot view infractions: pg_pool is None.")
            return

        infractions = await mod_log_db.get_user_mod_logs(
            self.bot.pg_pool, ctx.guild.id, member.id
        )

        if not infractions:
            await send_response(
                f"No infractions found for {self._user_display(member)}."
            )
            return

        embed = discord.Embed(
            title=f"Infractions for {member.display_name}", color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        for infraction in infractions[:25]:  # Display up to 25 infractions
            action_type = infraction["action_type"]
            reason = infraction["reason"] or "No reason provided"
            moderator_id = infraction["moderator_id"]
            timestamp = infraction["timestamp"]
            case_id = infraction["case_id"]
            duration_seconds = infraction["duration_seconds"]

            moderator = ctx.guild.get_member(moderator_id) or f"ID: {moderator_id}"

            value = f"**Case ID:** {case_id}\n"
            value += f"**Action:** {action_type}\n"
            value += f"**Moderator:** {moderator}\n"
            if duration_seconds:
                duration_str = str(datetime.timedelta(seconds=duration_seconds))
                value += f"**Duration:** {duration_str}\n"
            value += f"**Reason:** {reason}\n"
            value += f"**Date:** {discord.utils.format_dt(timestamp, style='f')}"

            embed.add_field(name=f"Infraction #{case_id}", value=value, inline=False)

        if len(infractions) > 25:
            embed.set_footer(text=f"Showing 25 of {len(infractions)} infractions.")

        await send_response(embed=embed)

    @moderate.command(
        name="removeinfraction",
        description="Remove a specific infraction by its case ID",
    )
    @app_commands.describe(
        case_id="The case ID of the infraction to remove",
        reason="The reason for removing the infraction",
    )
    async def moderate_remove_infraction_callback(
        self, ctx: commands.Context, case_id: int, reason: str = None
    ):
        """Remove a specific infraction by its case ID."""
        if ctx.interaction:
            await ctx.interaction.response.defer(ephemeral=True)

        async def send_response(message, ephemeral=True):
            if ctx.interaction:
                await ctx.interaction.followup.send(message, ephemeral=ephemeral)
            else:
                await ctx.send(message)

        if (
            not ctx.author.guild_permissions.ban_members
        ):  # Higher permission for removing infractions
            await send_response("❌ You don't have permission to remove infractions.")
            return

        if not self.bot.pg_pool:
            await send_response("❌ Database connection is not available.")
            logger.error("Cannot remove infraction: pg_pool is None.")
            return

        # Fetch the infraction to ensure it exists and to log details
        infraction_to_remove = await mod_log_db.get_mod_log(self.bot.pg_pool, case_id)
        if not infraction_to_remove or infraction_to_remove["guild_id"] != ctx.guild.id:
            await send_response(
                f"❌ Infraction with Case ID {case_id} not found in this server."
            )
            return

        deleted = await mod_log_db.delete_mod_log(
            self.bot.pg_pool, case_id, ctx.guild.id
        )

        if deleted:
            logger.info(
                f"Infraction (Case ID: {case_id}) removed by {ctx.author} (ID: {ctx.author.id}) in guild {ctx.guild.id}. Reason: {reason}"
            )

            # Log the removal action itself
            mod_log_cog: ModLogCog = self.bot.get_cog("ModLogCog")
            if mod_log_cog:
                target_user_id = infraction_to_remove["target_user_id"]
                target_user = await self.bot.fetch_user(
                    target_user_id
                )  # Fetch user for logging

                await mod_log_cog.log_action(
                    guild=ctx.guild,
                    moderator=ctx.author,
                    target=target_user if target_user else Object(id=target_user_id),
                    action_type="REMOVE_INFRACTION",
                    reason=f"Removed Case ID {case_id}. Original reason: {infraction_to_remove['reason']}. Removal reason: {reason or 'Not specified'}",
                    duration=None,
                )
            await send_response(
                f"✅ Infraction with Case ID {case_id} has been removed. Reason: {reason or 'Not specified'}"
            )
        else:
            await send_response(
                f"❌ Failed to remove infraction with Case ID {case_id}. It might have already been removed or an error occurred."
            )

    @moderate.command(
        name="clearinfractions",
        description="Clear all moderation infractions for a user",
    )
    @app_commands.describe(
        member="The member whose infractions to clear",
        reason="The reason for clearing all infractions",
    )
    async def moderate_clear_infractions_callback(
        self,
        ctx: commands.Context,
        member: discord.Member,
        reason: str = None,
    ):
        """Clear all moderation infractions for a user."""
        # This command uses a view, so it must be an interaction.
        # If it's a prefix command, we inform the user it's not supported.
        if not ctx.interaction:
            await ctx.send(
                "This command can only be used as a slash command due to the confirmation buttons."
            )
            return

        interaction = ctx.interaction

        # This is a destructive action, so require ban_members permission
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message(
                "❌ You don't have permission to clear all infractions for a user.",
                ephemeral=True,
            )
            return

        if not self.bot.pg_pool:
            await interaction.response.send_message(
                "❌ Database connection is not available.", ephemeral=True
            )
            logger.error("Cannot clear infractions: pg_pool is None.")
            return

        # Confirmation step
        view = discord.ui.View()
        confirm_button = discord.ui.Button(
            label="Confirm Clear All",
            style=discord.ButtonStyle.danger,
            custom_id="confirm_clear_all",
        )
        cancel_button = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.secondary,
            custom_id="cancel_clear_all",
        )

        async def confirm_callback(interaction_confirm: discord.Interaction):
            if interaction_confirm.user.id != interaction.user.id:
                await interaction_confirm.response.send_message(
                    "❌ You are not authorized to confirm this action.", ephemeral=True
                )
                return

            deleted_count = await mod_log_db.clear_user_mod_logs(
                self.bot.pg_pool, interaction.guild.id, member.id
            )

            if deleted_count > 0:
                logger.info(
                    f"{deleted_count} infractions for user {member} (ID: {member.id}) cleared by {interaction.user} (ID: {interaction.user.id}) in guild {interaction.guild.id}. Reason: {reason}"
                )

                # Log the clear all action
                mod_log_cog: ModLogCog = self.bot.get_cog("ModLogCog")
                if mod_log_cog:
                    await mod_log_cog.log_action(
                        guild=interaction.guild,
                        moderator=interaction.user,
                        target=member,
                        action_type="CLEAR_INFRACTIONS",
                        reason=f"Cleared {deleted_count} infractions. Reason: {reason or 'Not specified'}",
                        duration=None,
                    )
                await interaction_confirm.response.edit_message(
                    content=f"✅ Successfully cleared {deleted_count} infractions for {self._user_display(member)}. Reason: {reason or 'Not specified'}",
                    view=None,
                )
            elif deleted_count == 0:
                await interaction_confirm.response.edit_message(
                    content=f"ℹ️ No infractions found for {self._user_display(member)} to clear.",
                    view=None,
                )
            else:  # Should not happen if 0 is returned for no logs
                await interaction_confirm.response.edit_message(
                    content=f"❌ Failed to clear infractions for {self._user_display(member)}. An error occurred.",
                    view=None,
                )

        async def cancel_callback(interaction_cancel: discord.Interaction):
            if interaction_cancel.user.id != interaction.user.id:
                await interaction_cancel.response.send_message(
                    "❌ You are not authorized to cancel this action.", ephemeral=True
                )
                return
            await interaction_cancel.response.edit_message(
                content="🚫 Infraction clearing cancelled.", view=None
            )

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.response.send_message(
            f"⚠️ Are you sure you want to clear **ALL** infractions for {self._user_display(member)}?\n"
            f"This action is irreversible. Reason: {reason or 'Not specified'}",
            view=view,
            ephemeral=True,
        )

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} cog has been loaded.")


# Modals for context menu commands


class BanModal(discord.ui.Modal, title="Ban User"):
    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member
        self.send_dm = True  # Default to True

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter reason for ban",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=512,
    )

    delete_days = discord.ui.TextInput(
        label="Delete message history (days)",
        placeholder="0-7 (default 0)",
        required=False,
        max_length=1,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Defer the modal submission

        cog = interaction.client.get_cog("HumanModerationCog")
        if cog:
            reason = self.reason.value or "No reason provided"
            delete_days = (
                int(self.delete_days.value)
                if self.delete_days.value and self.delete_days.value.isdigit()
                else 0
            )
            # Create a context and call the existing ban callback
            ctx = await cog.bot.get_context(interaction)
            ctx.author = interaction.user  # Ensure author is set correctly
            await cog.moderate_ban_callback(
                ctx,
                member=self.member,
                reason=reason,
                delete_days=delete_days,
                send_dm=self.send_dm,
            )
        else:
            await interaction.followup.send(
                "Error: Moderation cog not found.", ephemeral=True
            )


class KickModal(discord.ui.Modal, title="Kick User"):
    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter reason for kick",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=512,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Defer the modal submission

        cog = interaction.client.get_cog("HumanModerationCog")
        if cog:
            reason = self.reason.value or "No reason provided"
            # Create a context and call the existing kick callback
            ctx = await cog.bot.get_context(interaction)
            ctx.author = interaction.user
            await cog.moderate_kick_callback(ctx, member=self.member, reason=reason)
        else:
            await interaction.followup.send(
                "Error: Moderation cog not found.", ephemeral=True
            )


class TimeoutModal(discord.ui.Modal, title="Timeout User"):
    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member

    duration = discord.ui.TextInput(
        label="Duration",
        placeholder="e.g., 1d, 2h, 30m, 60s",
        required=True,
        max_length=10,
    )

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter reason for timeout",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=512,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Defer the modal submission

        cog = interaction.client.get_cog("HumanModerationCog")
        if cog:
            duration = self.duration.value
            reason = self.reason.value or "No reason provided"
            # Create a context and call the existing timeout callback
            ctx = await cog.bot.get_context(interaction)
            ctx.author = interaction.user
            await cog.moderate_timeout_callback(
                ctx, member=self.member, duration=duration, reason=reason
            )
        else:
            await interaction.followup.send(
                "Error: Moderation cog not found.", ephemeral=True
            )


class RemoveTimeoutModal(discord.ui.Modal, title="Remove Timeout"):
    def __init__(self, member: discord.Member):
        super().__init__()
        self.member = member

    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter reason for removing timeout",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=512,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Defer the modal submission

        cog = interaction.client.get_cog("HumanModerationCog")
        if cog:
            reason = self.reason.value or "No reason provided"
            # Create a context and call the existing remove timeout callback
            ctx = await cog.bot.get_context(interaction)
            ctx.author = interaction.user
            await cog.moderate_remove_timeout_callback(
                ctx, member=self.member, reason=reason
            )
        else:
            await interaction.followup.send(
                "Error: Moderation cog not found.", ephemeral=True
            )


# Context menu commands must be defined at module level


class BanOptionsView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=60)  # 60 second timeout
        self.member = member
        self.send_dm = True  # Default to True
        self.update_button_label()

    def update_button_label(self):
        self.toggle_dm_button.label = f"Send DM: {'Yes' if self.send_dm else 'No'}"
        self.toggle_dm_button.style = (
            discord.ButtonStyle.green if self.send_dm else discord.ButtonStyle.red
        )

    @discord.ui.button(
        label="Send DM: Yes", style=discord.ButtonStyle.green, custom_id="toggle_dm"
    )
    async def toggle_dm_button(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        # Toggle the send_dm value
        self.send_dm = not self.send_dm
        self.update_button_label()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="Continue to Ban",
        style=discord.ButtonStyle.danger,
        custom_id="continue_ban",
    )
    async def continue_button(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ):
        # Create and show the modal
        modal = BanModal(self.member)
        modal.send_dm = self.send_dm  # Pass the send_dm setting to the modal
        await interaction.response.send_modal(modal)
        # Stop listening for interactions on this view
        self.stop()


@app_commands.context_menu(name="Ban User")
async def ban_user_context_menu(
    interaction: discord.Interaction, member: discord.Member
):
    """Bans the selected user via a modal."""
    # Check permissions before showing the modal
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message(
            "❌ You don't have permission to ban members.", ephemeral=True
        )
        return
    if not interaction.guild.me.guild_permissions.ban_members:
        await interaction.response.send_message(
            "❌ I don't have permission to ban members.", ephemeral=True
        )
        return
    if (
        interaction.user.top_role.position <= member.top_role.position
        and interaction.user.id != interaction.guild.owner_id
    ):
        await interaction.response.send_message(
            "❌ You cannot ban someone with a higher or equal role.", ephemeral=True
        )
        return
    if interaction.guild.me.top_role.position <= member.top_role.position:
        await interaction.response.send_message(
            "❌ I cannot ban someone with a higher or equal role than me.",
            ephemeral=True,
        )
        return
    if member.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ You cannot ban yourself.", ephemeral=True
        )
        return
    if member.id == interaction.client.user.id:
        await interaction.response.send_message(
            "❌ I cannot ban myself.", ephemeral=True
        )
        return

    # Show options view first
    view = BanOptionsView(member)
    await interaction.response.send_message(
        f"⚠️ You are about to ban **{member.display_name}** ({member.id}).\nPlease select your options:",
        view=view,
        ephemeral=True,
    )


@app_commands.context_menu(name="Kick User")
async def kick_user_context_menu(
    interaction: discord.Interaction, member: discord.Member
):
    """Kicks the selected user via a modal."""
    # Check permissions before showing the modal
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message(
            "❌ You don't have permission to kick members.", ephemeral=True
        )
        return
    if not interaction.guild.me.guild_permissions.kick_members:
        await interaction.response.send_message(
            "❌ I don't have permission to kick members.", ephemeral=True
        )
        return
    if (
        interaction.user.top_role.position <= member.top_role.position
        and interaction.user.id != interaction.guild.owner_id
    ):
        await interaction.response.send_message(
            "❌ You cannot kick someone with a higher or equal role.", ephemeral=True
        )
        return
    if interaction.guild.me.top_role.position <= member.top_role.position:
        await interaction.response.send_message(
            "❌ I cannot kick someone with a higher or equal role than me.",
            ephemeral=True,
        )
        return
    if member.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ You cannot kick yourself.", ephemeral=True
        )
        return
    if member.id == interaction.client.user.id:
        await interaction.response.send_message(
            "❌ I cannot kick myself.", ephemeral=True
        )
        return

    modal = KickModal(member)
    await interaction.response.send_modal(modal)


@app_commands.context_menu(name="Timeout User")
async def timeout_user_context_menu(
    interaction: discord.Interaction, member: discord.Member
):
    """Timeouts the selected user via a modal."""
    # Check permissions before showing the modal
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ You don't have permission to timeout members.", ephemeral=True
        )
        return
    if not interaction.guild.me.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ I don't have permission to timeout members.", ephemeral=True
        )
        return
    if (
        interaction.user.top_role.position <= member.top_role.position
        and interaction.user.id != interaction.guild.owner_id
    ):
        await interaction.response.send_message(
            "❌ You cannot timeout someone with a higher or equal role.", ephemeral=True
        )
        return
    if interaction.guild.me.top_role.position <= member.top_role.position:
        await interaction.response.send_message(
            "❌ I cannot timeout someone with a higher or equal role than me.",
            ephemeral=True,
        )
        return
    if member.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ You cannot timeout yourself.", ephemeral=True
        )
        return
    if member.id == interaction.client.user.id:
        await interaction.response.send_message(
            "❌ I cannot timeout myself.", ephemeral=True
        )
        return

    modal = TimeoutModal(member)
    await interaction.response.send_modal(modal)


@app_commands.context_menu(name="Remove Timeout")
async def remove_timeout_context_menu(
    interaction: discord.Interaction, member: discord.Member
):
    """Removes timeout from the selected user via a modal."""
    # Check permissions before showing the modal
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ You don't have permission to remove timeouts.", ephemeral=True
        )
        return
    if not interaction.guild.me.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ I don't have permission to remove timeouts.", ephemeral=True
        )
        return
    # Check if the member is timed out before showing the modal
    if not member.timed_out_until:
        await interaction.response.send_message(
            "❌ This member is not timed out.", ephemeral=True
        )
        return

    modal = RemoveTimeoutModal(member)
    await interaction.response.send_modal(modal)


async def setup(bot: commands.Bot):
    cog = HumanModerationCog(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(ban_user_context_menu)
    bot.tree.add_command(kick_user_context_menu)
    bot.tree.add_command(timeout_user_context_menu)
    bot.tree.add_command(remove_timeout_context_menu)

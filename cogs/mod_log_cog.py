import discord
from discord.ext import commands
from discord import app_commands, Interaction, Color, User, Member, Object, ui
import logging
from typing import Optional, Union, Dict, Any
import datetime

# Import our JSON-based database modules
from .logging_helpers import mod_log_db
from .logging_helpers import settings_manager as sm
from .aimod_helpers.config_manager import get_guild_config_async

log = logging.getLogger(__name__)


class ModLogCog(commands.Cog):
    """Cog for handling integrated moderation logging and related commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Create the main command group for this cog
        # Register commands within the group

    class LogView(ui.LayoutView):
        """View used for moderation log messages."""

        def __init__(
            self,
            bot: commands.Bot,
            title: str,
            color: discord.Color,
            lines: list[str],
            footer: str,
        ):
            super().__init__(timeout=None)
            container = ui.Container(accent_colour=color)
            self.add_item(container)
            container.add_item(ui.TextDisplay(f"**{title}**"))
            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            for line in lines:
                container.add_item(ui.TextDisplay(line))
            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            self.footer_display = ui.TextDisplay(footer)
            container.add_item(self.footer_display)

    def _format_user(
        self, user: Union[Member, User, Object], guild: Optional[discord.Guild] = None
    ) -> str:
        """Return a string with display name, username and ID for a user-like object."""
        if isinstance(user, Object):
            return f"Unknown User (ID: {user.id})"
        if isinstance(user, Member):
            display = user.display_name
        elif guild and isinstance(user, User):
            member = guild.get_member(user.id)
            display = member.display_name if member else user.name
        else:
            display = user.name
        username = (
            f"{user.name}#{user.discriminator}"
            if isinstance(user, (Member, User))
            else "Unknown"
        )
        return f"{display} ({username}) [ID: {user.id}]"

    async def _fetch_user_display(self, user_id: int, guild: discord.Guild) -> str:
        """Fetch and format a user by ID for display."""
        member = guild.get_member(user_id)
        if member:
            return self._format_user(member, guild)
        user = self.bot.get_user(user_id)
        if user:
            return self._format_user(user, guild)
        try:
            user = await self.bot.fetch_user(user_id)
            return self._format_user(user, guild)
        except discord.HTTPException:
            return f"Unknown User (ID: {user_id})"

    @commands.hybrid_group(
        name="logs",
        description="Commands for viewing and managing moderation logs",
    )
    async def logs(self, ctx: commands.Context):
        """Commands for viewing and managing moderation logs"""
        await ctx.send_help(ctx.command)

    # --- Core Logging Function ---

    async def log_action(
        self,
        guild: discord.Guild,
        moderator: Union[User, Member],  # For bot actions
        target: Union[
            User, Member, Object
        ],  # Can be user, member, or just an ID object
        action_type: str,
        reason: Optional[str],
        duration: Optional[datetime.timedelta] = None,
        source: str = "BOT",  # Default source is the bot itself
        ai_details: Optional[Dict[str, Any]] = None,  # Details from AI API
        moderator_id_override: Optional[
            int
        ] = None,  # Allow overriding moderator ID for AI source
    ):
        """Logs a moderation action to the database and configured channel."""
        if not guild:
            log.warning("Attempted to log action without guild context.")
            return

        guild_id = guild.id
        # Use override if provided (for AI source), otherwise use moderator object ID
        moderator_id = (
            moderator_id_override if moderator_id_override is not None else moderator.id
        )
        target_user_id = target.id
        duration_seconds = int(duration.total_seconds()) if duration else None

        # 1. Add initial log entry to DB
        case_id = await mod_log_db.add_mod_log(
            None,  # pool not needed for JSON storage
            guild_id,
            moderator_id,
            target_user_id,
            action_type,
            reason,
            duration_seconds,
        )

        if not case_id:
            log.error(
                f"Failed to get case_id when logging action {action_type} in guild {guild_id}"
            )
            return  # Don't proceed if we couldn't save the initial log

        # 2. Check settings and send log message
        try:
            log_channel_id = await get_guild_config_async(
                guild_id, "moderation_log_channel_id"
            )
            log_enabled = bool(log_channel_id)

            if not log_enabled or not log_channel_id:
                log.debug(
                    f"Mod logging disabled or channel not set for guild {guild_id}. Skipping Discord log message."
                )
                return

            log_channel = guild.get_channel(log_channel_id)
            if not log_channel or not isinstance(log_channel, discord.TextChannel):
                log.warning(
                    f"Mod log channel {log_channel_id} not found or not a text channel in guild {guild_id}."
                )
                return

            # 3. Format and send view
            view = self._format_log_embed(
                case_id=case_id,
                moderator=moderator,  # Pass the object for display formatting
                target=target,
                action_type=action_type,
                reason=reason,
                duration=duration,
                guild=guild,
                source=source,
                ai_details=ai_details,
                moderator_id_override=moderator_id_override,  # Pass override for formatting
            )
            log_message = await log_channel.send(view=view)

            # 4. Update DB with message details
            await mod_log_db.update_mod_log_message_details(
                None, case_id, log_message.id, log_channel.id
            )

        except Exception as e:
            log.exception(
                f"Error during Discord mod log message sending/updating for case {case_id} in guild {guild_id}: {e}"
            )

    def _format_log_embed(
        self,
        case_id: int,
        moderator: Union[User, Member],
        target: Union[User, Member, Object],
        action_type: str,
        reason: Optional[str],
        duration: Optional[datetime.timedelta],
        guild: discord.Guild,
        source: str = "BOT",
        ai_details: Optional[Dict[str, Any]] = None,
        moderator_id_override: Optional[int] = None,
    ) -> ui.LayoutView:
        """Helper function to create the standard log view."""
        color_map = {
            "BAN": Color.red(),
            "UNBAN": Color.green(),
            "KICK": Color.orange(),
            "TIMEOUT": Color.gold(),
            "REMOVE_TIMEOUT": Color.blue(),
            "WARN": Color.yellow(),
            "AI_ALERT": Color.purple(),
            "AI_DELETE_REQUESTED": Color.dark_grey(),
        }
        embed_color = (
            Color.blurple()
            if source == "AI_API"
            else color_map.get(action_type.upper(), Color.greyple())
        )
        action_title_prefix = (
            "🤖 AI Moderation Action"
            if source == "AI_API"
            else action_type.replace("_", " ").title()
        )
        action_title = f"{action_title_prefix} | Case #{case_id}"
        target_display = self._format_user(target, guild)
        moderator_display = (
            f"AI System (ID: {moderator_id_override or 'Unknown'})"
            if source == "AI_API"
            else self._format_user(moderator, guild)
        )
        lines = [f"**User:** {target_display}", f"**Moderator:** {moderator_display}"]
        if ai_details:
            if "rule_violated" in ai_details:
                lines.append(f"**Rule Violated:** {ai_details['rule_violated']}")
            if "reasoning" in ai_details:
                reason_to_display = reason or ai_details["reasoning"]
                lines.append(
                    f"**Reason / AI Reasoning:** {reason_to_display or 'No reason provided.'}"
                )
                if reason and reason != ai_details["reasoning"]:
                    lines.append(f"**Original Bot Reason:** {reason}")
            else:
                lines.append(f"**Reason:** {reason or 'No reason provided.'}")
            if "message_content" in ai_details:
                message_content = ai_details["message_content"]
                if len(message_content) > 1000:
                    message_content = message_content[:997] + "..."
                lines.append(f"**Message Content:** {message_content}")
        else:
            lines.append(f"**Reason:** {reason or 'No reason provided.'}")
        if duration:
            total_seconds = int(duration.total_seconds())
            days, remainder = divmod(total_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = ""
            if days > 0:
                duration_str += f"{days}d "
            if hours > 0:
                duration_str += f"{hours}h "
            if minutes > 0:
                duration_str += f"{minutes}m "
            if seconds > 0 or not duration_str:
                duration_str += f"{seconds}s"
            duration_str = duration_str.strip()
            lines.append(f"**Duration:** {duration_str}")
            if action_type.upper() == "TIMEOUT":
                expires_at = discord.utils.utcnow() + duration
                lines.append(f"**Expires:** <t:{int(expires_at.timestamp())}:R>")
        footer = (
            f"AI Moderation Action • {guild.name} ({guild.id})"
            if source == "AI_API"
            else f"Guild: {guild.name} ({guild.id})"
        )
        return self.LogView(self.bot, action_title, embed_color, lines, footer)

    # --- View Command Callback ---
    @logs.command(
        name="view",
        description="View moderation logs for a user or the server",
    )
    @app_commands.describe(user="Optional: The user whose logs you want to view")
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def view(
        self, interaction: Interaction, user: Optional[discord.User] = None
    ):
        """Callback for the /modlog view command."""
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild_id

        if not guild_id:
            await interaction.followup.send(
                "❌ This command can only be used in a server.", ephemeral=True
            )
            return

        records = []
        if user:
            records = await mod_log_db.get_user_mod_logs(None, guild_id, user.id)
            title = f"Moderation Logs for {user.name} ({user.id})"
        else:
            records = await mod_log_db.get_guild_mod_logs(None, guild_id)
            title = f"Recent Moderation Logs for {interaction.guild.name}"

        if not records:
            await interaction.followup.send(
                "No moderation logs found matching your criteria.", ephemeral=True
            )
            return

        # Format the logs into a text response
        response_lines = [f"**{title}**"]
        for record in records:
            timestamp_str = record["timestamp"][:19]  # Remove timezone info for display
            reason_str = record["reason"] or "N/A"
            duration_str = (
                f" ({record['duration_seconds']}s)"
                if record["duration_seconds"]
                else ""
            )
            target_disp = await self._fetch_user_display(
                record["target_user_id"], interaction.guild
            )
            if record["moderator_id"] == 0:
                mod_disp = "AI System"
            else:
                mod_disp = await self._fetch_user_display(
                    record["moderator_id"], interaction.guild
                )
            response_lines.append(
                f"`Case #{record['case_id']}` [{timestamp_str}] **{record['action_type']}** "
                f"Target: {target_disp} Mod: {mod_disp} "
                f"Reason: {reason_str}{duration_str}"
            )

        # Handle potential message length limits
        full_response = "\n".join(response_lines)
        if len(full_response) > 2000:
            full_response = full_response[:1990] + "\n... (truncated)"

        await interaction.followup.send(full_response, ephemeral=True)

    @logs.command(
        name="case",
        description="View details for a specific moderation case ID",
    )
    @app_commands.describe(case_id="The ID of the moderation case to view")
    @app_commands.checks.has_permissions(
        moderate_members=True
    )
    async def case(self, interaction: Interaction, case_id: int):
        """Callback for the /modlog case command."""
        await interaction.response.defer(ephemeral=True)
        record = await mod_log_db.get_mod_log(None, case_id)

        if not record:
            await interaction.followup.send(
                f"❌ Case ID #{case_id} not found.", ephemeral=True
            )
            return

        # Ensure the case belongs to the current guild for security/privacy
        if record["guild_id"] != interaction.guild_id:
            await interaction.followup.send(
                f"❌ Case ID #{case_id} does not belong to this server.", ephemeral=True
            )
            return

        # Fetch user objects if possible to show names
        # Special handling for AI moderator (ID 0) to avoid Discord API 404 error
        if record["moderator_id"] == 0:
            # AI moderator uses ID 0, which is not a valid Discord user ID
            moderator = None
        else:
            try:
                moderator = await self.bot.fetch_user(record["moderator_id"])
            except discord.NotFound:
                log.warning(
                    f"Moderator with ID {record['moderator_id']} not found when viewing case {case_id}"
                )
                moderator = None

        try:
            target = await self.bot.fetch_user(record["target_user_id"])
        except discord.NotFound:
            log.warning(
                f"Target user with ID {record['target_user_id']} not found when viewing case {case_id}"
            )
            target = None

        duration = (
            datetime.timedelta(seconds=record["duration_seconds"])
            if record["duration_seconds"]
            else None
        )

        view = self._format_log_embed(
            case_id,
            moderator
            or Object(
                id=record["moderator_id"]
            ),  # Fallback to Object if user not found
            target
            or Object(
                id=record["target_user_id"]
            ),  # Fallback to Object if user not found
            record["action_type"],
            record["reason"],
            duration,
            interaction.guild,
        )

        # Add log message link if available
        if record["log_message_id"] and record["log_channel_id"]:
            link = f"https://discord.com/channels/{record['guild_id']}/{record['log_channel_id']}/{record['log_message_id']}"
            # Append jump link as extra line
            view.footer_display.content += f" | [Jump to Log]({link})"

        await interaction.followup.send(view=view, ephemeral=True)

    @logs.command(
        name="reason",
        description="Update the reason for a specific moderation case ID",
    )
    @app_commands.describe(
        case_id="The ID of the moderation case to update",
        new_reason="The new reason for the moderation action",
    )
    @app_commands.checks.has_permissions(
        manage_guild=True
    )
    async def reason(
        self, interaction: Interaction, case_id: int, new_reason: str
    ):
        """Callback for the /modlog reason command."""
        await interaction.response.defer(ephemeral=True)

        # 1. Get the original record to verify guild and existence
        original_record = await mod_log_db.get_mod_log(None, case_id)
        if not original_record:
            await interaction.followup.send(
                f"❌ Case ID #{case_id} not found.", ephemeral=True
            )
            return
        if original_record["guild_id"] != interaction.guild_id:
            await interaction.followup.send(
                f"❌ Case ID #{case_id} does not belong to this server.", ephemeral=True
            )
            return

        # 2. Update the reason in the database
        success = await mod_log_db.update_mod_log_reason(None, case_id, new_reason)

        if not success:
            await interaction.followup.send(
                f"❌ Failed to update reason for Case ID #{case_id}. Please check logs.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"✅ Updated reason for Case ID #{case_id}.", ephemeral=True
        )

        # 3. (Optional but recommended) Update the original log message embed
        if original_record["log_message_id"] and original_record["log_channel_id"]:
            try:
                log_channel = interaction.guild.get_channel(
                    original_record["log_channel_id"]
                )
                if log_channel and isinstance(log_channel, discord.TextChannel):
                    log_message = await log_channel.fetch_message(
                        original_record["log_message_id"]
                    )
                    if log_message and log_message.author == self.bot.user:
                        # Re-fetch users/duration to reconstruct embed accurately
                        # Special handling for AI moderator (ID 0) to avoid Discord API 404 error
                        if original_record["moderator_id"] == 0:
                            # AI moderator uses ID 0, which is not a valid Discord user ID
                            moderator = None
                        else:
                            try:
                                moderator = await self.bot.fetch_user(
                                    original_record["moderator_id"]
                                )
                            except discord.NotFound:
                                log.warning(
                                    f"Moderator with ID {original_record['moderator_id']} not found when updating case {case_id}"
                                )
                                moderator = None

                        try:
                            target = await self.bot.fetch_user(
                                original_record["target_user_id"]
                            )
                        except discord.NotFound:
                            log.warning(
                                f"Target user with ID {original_record['target_user_id']} not found when updating case {case_id}"
                            )
                            target = None

                        duration = (
                            datetime.timedelta(
                                seconds=original_record["duration_seconds"]
                            )
                            if original_record["duration_seconds"]
                            else None
                        )

                        new_view = self._format_log_embed(
                            case_id,
                            moderator or Object(id=original_record["moderator_id"]),
                            target or Object(id=original_record["target_user_id"]),
                            original_record["action_type"],
                            new_reason,  # Use the new reason here
                            duration,
                            interaction.guild,
                        )
                        link = f"https://discord.com/channels/{original_record['guild_id']}/{original_record['log_channel_id']}/{original_record['log_message_id']}"
                        new_view.footer_display.content += f" | [Jump to Log]({link}) | Updated By: {interaction.user.mention}"

                        await log_message.edit(view=new_view)
                        log.info(
                            f"Successfully updated log message view for case {case_id}"
                        )
            except discord.NotFound:
                log.warning(
                    f"Original log message or channel not found for case {case_id} when updating reason."
                )
            except discord.Forbidden:
                log.warning(
                    f"Missing permissions to edit original log message for case {case_id}."
                )
            except Exception as e:
                log.exception(
                    f"Error updating original log message embed for case {case_id}: {e}"
                )

    async def cog_load(self):
        """
        Method called when the cog is loaded.
        """
        print(f"ModLogCog has been loaded.")


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(ModLogCog(bot))

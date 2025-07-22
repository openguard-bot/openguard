import discord
from discord.ext import commands, tasks
from discord import AllowedMentions, ui
import datetime
import asyncio
import aiohttp  # Added for webhook sending
import logging  # Use logging instead of print
from typing import Optional, Union

# Import our JSON-based settings manager
from .logging_helpers import settings_manager

log = logging.getLogger(__name__)  # Setup logger for this cog

# Mapping for consistent event styling
EVENT_STYLES = {
    "message_edit": ("✏️", discord.Color.light_grey()),
    "message_delete": ("🗑️", discord.Color.dark_grey()),
}

# Define all possible event keys for toggling
# Keep this list updated if new loggable events are added
ALL_EVENT_KEYS = sorted(
    [
        # Direct Events
        "member_join",
        "member_remove",
        "member_ban_event",
        "member_unban",
        "member_update",
        "role_create_event",
        "role_delete_event",
        "role_update_event",
        "channel_create_event",
        "channel_delete_event",
        "channel_update_event",
        "message_edit",
        "message_delete",
        "reaction_add",
        "reaction_remove",
        "reaction_clear",
        "reaction_clear_emoji",
        "voice_state_update",
        "guild_update_event",
        "emoji_update_event",
        "invite_create_event",
        "invite_delete_event",
        "command_error",  # Potentially noisy
        "thread_create",
        "thread_delete",
        "thread_update",
        "thread_member_join",
        "thread_member_remove",
        "webhook_update",
        # Audit Log Actions (prefixed with 'audit_')
        "audit_kick",
        "audit_prune",
        "audit_ban",
        "audit_unban",
        "audit_member_role_update",
        "audit_member_update_timeout",  # Specific member_update cases
        "audit_message_delete",
        "audit_message_bulk_delete",
        "audit_role_create",
        "audit_role_delete",
        "audit_role_update",
        "audit_channel_create",
        "audit_channel_delete",
        "audit_channel_update",
        "audit_emoji_create",
        "audit_emoji_delete",
        "audit_emoji_update",
        "audit_invite_create",
        "audit_invite_delete",
        "audit_guild_update",
        # Add more audit keys if needed, e.g., "audit_stage_instance_create"
    ]
)


class LoggingCog(commands.Cog):
    """Handles comprehensive server event logging via webhooks with granular toggling."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None  # Session for webhooks
        self.last_audit_log_ids: dict[int, Optional[int]] = {}  # Store last ID per guild
        # Start the audit log poller task if the bot is ready, otherwise wait
        if bot.is_ready():
            asyncio.create_task(self.initialize_cog())  # Use async init helper
        else:
            asyncio.create_task(self.start_audit_log_poller_when_ready())  # Keep this for initial start

    class LogView(ui.LayoutView):
        """View used for logging messages."""

        def __init__(
            self,
            bot: commands.Bot,
            title: str,
            description: str,
            color: discord.Color,
            author: Optional[discord.abc.User],
            footer: Optional[str],
        ) -> None:
            super().__init__(timeout=None)
            self.container = ui.Container(accent_colour=color)
            self.add_item(self.container)

            title_display = ui.TextDisplay(f"**{title}**")
            desc_display = ui.TextDisplay(description) if description else None
            self.header_items: list[ui.TextDisplay] = [title_display]
            if desc_display:
                self.header_items.append(desc_display)

            self.header_section: Optional[ui.Section] = None
            if author is not None:
                self.header_section = ui.Section(accessory=ui.Thumbnail(media=author.display_avatar.url))
                for item in self.header_items:
                    self.header_section.add_item(item)
                self.container.add_item(self.header_section)
            else:
                for item in self.header_items:
                    self.container.add_item(item)
            self.container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

            # Use same container to avoid nesting issues and track separator
            self.content_container = self.container
            self.bottom_separator = ui.Separator(spacing=discord.SeparatorSpacing.small)
            self.container.add_item(self.bottom_separator)

            timestamp = discord.utils.format_dt(datetime.datetime.utcnow(), style="f")
            parts = [timestamp, footer or f"Bot ID: {bot.user.id}"]
            if author:
                parts.append(f"User ID: {author.id}")
            footer_text = " | ".join(parts)
            self.footer_display = ui.TextDisplay(footer_text)
            self.container.add_item(self.footer_display)

        def add_field(self, name: str, value: str, inline: bool = False) -> None:
            field = ui.TextDisplay(f"**{name}:** {value}")
            # Ensure the field is properly registered with the view by using
            # add_item first, then repositioning it before the bottom separator
            if hasattr(self.container, "_children"):
                self.container.add_item(field)
                try:
                    children = self.container._children
                    index = children.index(self.bottom_separator)
                    children.remove(field)
                    children.insert(index, field)
                except ValueError:
                    # Fallback to default behaviour if the separator is missing
                    pass
            else:
                self.content_container.add_item(field)

        def set_author(self, user: discord.abc.User) -> None:
            """Add or update the thumbnail and append the user ID to the footer."""
            if self.header_section is None:
                self.header_section = ui.Section(accessory=ui.Thumbnail(media=user.display_avatar.url))
                for item in self.header_items:
                    self.container.remove_item(item)
                    self.header_section.add_item(item)
                # Insert at the beginning to keep layout consistent
                if hasattr(self.container, "children"):
                    self.container.children.insert(0, self.header_section)
                else:
                    self.container.add_item(self.header_section)
            else:
                self.header_section.accessory = ui.Thumbnail(media=user.display_avatar.url)
            if "User ID:" not in self.footer_display.content:
                self.footer_display.content += f" | User ID: {user.id}"

        def set_footer(self, text: str) -> None:
            """Replace the footer text while preserving the timestamp."""
            timestamp = discord.utils.format_dt(datetime.datetime.utcnow(), style="f")
            self.footer_display.content = f"{timestamp} | {text}"

    def _user_display(self, user: Union[discord.Member, discord.User]) -> str:
        """Return display name, username and ID string for a user."""
        display = user.display_name if isinstance(user, discord.Member) else user.name
        username = f"{user.name}#{user.discriminator}"
        return f"{display} ({username}) [ID: {user.id}]"

    async def initialize_cog(self):
        """Asynchronous initialization tasks."""
        log.info("Initializing LoggingCog...")
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
            log.info("aiohttp ClientSession created for LoggingCog.")
        await self.initialize_audit_log_ids()
        if not self.poll_audit_log.is_running():
            self.poll_audit_log.start()
            log.info("Audit log poller started during initialization.")

    async def initialize_audit_log_ids(self):
        """Fetch the latest audit log ID for each guild the bot is in."""
        log.info("Initializing last audit log IDs for guilds...")
        for guild in self.bot.guilds:
            if guild.id not in self.last_audit_log_ids:  # Only initialize if not already set
                try:
                    if guild.me.guild_permissions.view_audit_log:
                        async for entry in guild.audit_logs(limit=1):
                            self.last_audit_log_ids[guild.id] = entry.id
                            log.debug(f"Initialized last_audit_log_id for guild {guild.id} to {entry.id}")
                            break  # Only need the latest one
                    else:
                        log.warning(
                            f"Missing 'View Audit Log' permission in guild {guild.id}. Cannot initialize audit log ID."
                        )
                        self.last_audit_log_ids[guild.id] = None  # Mark as unable to fetch
                except discord.Forbidden:
                    log.warning(f"Forbidden error fetching initial audit log ID for guild {guild.id}.")
                    self.last_audit_log_ids[guild.id] = None
                except discord.HTTPException as e:
                    log.error(f"HTTP error fetching initial audit log ID for guild {guild.id}: {e}")
                    self.last_audit_log_ids[guild.id] = None
                except Exception as e:
                    log.exception(f"Unexpected error fetching initial audit log ID for guild {guild.id}: {e}")
                    self.last_audit_log_ids[guild.id] = None  # Mark as unable on other errors
        log.info("Finished initializing audit log IDs.")

    async def start_audit_log_poller_when_ready(self):
        """Waits until bot is ready, then initializes and starts the poller."""
        await self.bot.wait_until_ready()
        await self.initialize_cog()  # Call the main init helper

    async def cog_unload(self):
        """Clean up resources when the cog is unloaded."""
        self.poll_audit_log.cancel()
        log.info("Audit log poller stopped.")
        if self.session and not self.session.closed:
            await self.session.close()
            log.info("aiohttp ClientSession closed for LoggingCog.")

    async def _send_log_embed(self, guild: discord.Guild, embed: ui.LayoutView) -> None:
        """Sends the log view via the configured webhook for the guild."""
        if not self.session or self.session.closed:
            log.error(f"aiohttp session not available or closed in LoggingCog for guild {guild.id}. Cannot send log.")
            return

        webhook_url = await settings_manager.get_logging_webhook(guild.id)

        log.info(f"For guild {guild.id}, retrieved webhook_url: {webhook_url} (type: {type(webhook_url)})")
        if not webhook_url:
            # log.debug(f"Logging webhook not configured for guild {guild.id}. Skipping log.") # Can be noisy
            return

        try:
            webhook = discord.Webhook.from_url(
                webhook_url,
                session=self.session,
                client=self.bot,
            )
            await webhook.send(
                view=embed,
                username=f"{self.bot.user.name} Logs",
                avatar_url=self.bot.user.display_avatar.url,
                allowed_mentions=AllowedMentions.none(),
            )
            # log.debug(f"Sent log embed via webhook for guild {guild.id}") # Can be noisy
        except ValueError as e:
            log.exception(f"ValueError sending log via webhook for guild {guild.id}. Error: {e}")
        except (discord.Forbidden, discord.NotFound):
            log.error(f"Webhook permissions error or webhook not found for guild {guild.id}. URL: {webhook_url}")
        except discord.HTTPException as e:
            log.error(f"HTTP error sending log via webhook for guild {guild.id}: {e}")
        except aiohttp.ClientError as e:
            log.error(f"aiohttp client error sending log via webhook for guild {guild.id}: {e}")
        except Exception as e:
            log.exception(f"Unexpected error sending log via webhook for guild {guild.id}: {e}")

    def _create_log_embed(
        self,
        title: str,
        description: str = "",
        color: discord.Color = discord.Color.blue(),
        author: Optional[Union[discord.User, discord.Member]] = None,
        footer: Optional[str] = None,
    ) -> ui.LayoutView:
        """Creates a standardized log view."""
        return self.LogView(self.bot, title, description, color, author, footer)

    def _add_id_footer(
        self,
        embed: ui.LayoutView,
        obj: Union[
            discord.Member,
            discord.User,
            discord.Role,
            discord.abc.GuildChannel,
            discord.Message,
            discord.Invite,
            None,
        ] = None,
        obj_id: Optional[int] = None,
        id_name: str = "ID",
    ) -> None:
        """Adds an ID to the footer text if possible."""
        target_id = obj_id or (obj.id if obj else None)
        if target_id:
            existing_footer = getattr(embed, "footer_display", None)
            if existing_footer:
                parts = [f"{id_name}: {target_id}"]
                link = None
                if hasattr(obj, "jump_url"):
                    link = f"[Jump]({obj.jump_url})"
                elif isinstance(obj, discord.abc.GuildChannel):
                    link = obj.mention
                if link:
                    parts.append(link)
                sep = " | " if existing_footer.content else ""
                existing_footer.content += sep + " | ".join(parts)

    async def _check_log_enabled(self, guild_id: int, event_key: str) -> bool:
        """Checks if logging is enabled for a specific event key in a guild."""
        # First, check if the webhook is configured at all
        webhook_url = await settings_manager.get_logging_webhook(guild_id)
        if not webhook_url:
            return False
        # Then, check if the specific event is enabled (defaults to True if not set)
        enabled = await settings_manager.is_log_event_enabled(guild_id, event_key, default_enabled=True)
        return enabled

    async def _is_recent_audit_log_for_target(
        self,
        guild: discord.Guild,
        action: discord.AuditLogAction,
        target_id: int,
        max_age: float = 5.0,
    ) -> bool:
        """Return True if the latest audit log entry matches the target within ``max_age`` seconds."""
        try:
            async for entry in guild.audit_logs(limit=1, action=action):
                if (
                    entry.target.id == target_id
                    and (discord.utils.utcnow() - entry.created_at).total_seconds() <= max_age
                ):
                    return True
            return False
        except discord.Forbidden:
            return True
        except Exception:
            return False

    # --- Event Listeners ---

    # Simple audit log poller (placeholder)
    @tasks.loop(minutes=5)
    async def poll_audit_log(self):
        """Simple audit log poller - placeholder for now."""
        # This is a simplified version - the original had complex audit log processing
        # For now, we'll just keep it as a placeholder
        pass

    @poll_audit_log.before_loop
    async def before_poll_audit_log(self):
        await self.bot.wait_until_ready()

    # --- Event Listeners ---

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize audit log ID when joining a new guild."""
        log.info(f"Joined guild {guild.id}. Initializing audit log ID.")
        if guild.id not in self.last_audit_log_ids:
            try:
                if guild.me.guild_permissions.view_audit_log:
                    async for entry in guild.audit_logs(limit=1):
                        self.last_audit_log_ids[guild.id] = entry.id
                        log.debug(f"Initialized last_audit_log_id for new guild {guild.id} to {entry.id}")
                        break
                else:
                    log.warning(f"Missing 'View Audit Log' permission in new guild {guild.id}.")
                    self.last_audit_log_ids[guild.id] = None
            except Exception as e:
                log.exception(f"Error fetching initial audit log ID for new guild {guild.id}: {e}")
                self.last_audit_log_ids[guild.id] = None

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Remove guild data when leaving."""
        log.info(f"Left guild {guild.id}. Removing audit log ID.")
        self.last_audit_log_ids.pop(guild.id, None)

    # --- Member Events ---
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        event_key = "member_join"
        if not await self._check_log_enabled(guild.id, event_key):
            return

        embed = self._create_log_embed(
            title="📥 Member Joined",
            description=f"{self._user_display(member)} joined the server.",
            color=discord.Color.green(),
            author=member,
        )
        embed.add_field(
            name="Account Created",
            value=discord.utils.format_dt(member.created_at, style="F"),
            inline=False,
        )
        await self._send_log_embed(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        event_key = "member_remove"
        if not await self._check_log_enabled(guild.id, event_key):
            return

        embed = self._create_log_embed(
            title="📤 Member Left",
            description=f"{self._user_display(member)} left the server.",
            color=discord.Color.orange(),
            author=member,
        )
        self._add_id_footer(embed, member, id_name="User ID")
        await self._send_log_embed(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: Union[discord.User, discord.Member]):
        event_key = "member_ban_event"
        if not await self._check_log_enabled(guild.id, event_key):
            return

        embed = self._create_log_embed(
            title="🔨 Member Banned (Event)",
            description=f"{self._user_display(user)} was banned.\n*Audit log may contain moderator and reason.*",
            color=discord.Color.red(),
            author=user,
        )
        self._add_id_footer(embed, user, id_name="User ID")
        await self._send_log_embed(guild, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        event_key = "member_unban"
        if not await self._check_log_enabled(guild.id, event_key):
            return

        embed = self._create_log_embed(
            title="🔓 Member Unbanned",
            description=f"{self._user_display(user)} was unbanned.",
            color=discord.Color.blurple(),
            author=user,
        )
        self._add_id_footer(embed, user, id_name="User ID")
        await self._send_log_embed(guild, embed)

    # --- Message Events ---
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        event_key = "message_delete"
        if not await self._check_log_enabled(message.guild.id, event_key):
            return

        embed = self._create_log_embed(
            title="🗑️ Message Deleted",
            description=f"Message by {self._user_display(message.author)} deleted in {message.channel.mention}",
            color=discord.Color.dark_grey(),
            author=message.author,
        )

        if message.content:
            content = message.content
            if len(content) > 1000:
                content = content[:997] + "..."
            embed.add_field(name="Content", value=content, inline=False)

        self._add_id_footer(embed, message, id_name="Message ID")
        await self._send_log_embed(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.guild or after.author.bot or before.content == after.content:
            return

        event_key = "message_edit"
        if not await self._check_log_enabled(after.guild.id, event_key):
            return

        embed = self._create_log_embed(
            title="✏️ Message Edited",
            description=f"Message by {self._user_display(after.author)} edited in {after.channel.mention}",
            color=discord.Color.light_grey(),
            author=after.author,
        )

        if before.content:
            before_content = before.content
            if len(before_content) > 500:
                before_content = before_content[:497] + "..."
            embed.add_field(name="Before", value=before_content, inline=False)

        if after.content:
            after_content = after.content
            if len(after_content) > 500:
                after_content = after_content[:497] + "..."
            embed.add_field(name="After", value=after_content, inline=False)

        self._add_id_footer(embed, after, id_name="Message ID")
        await self._send_log_embed(after.guild, embed)


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(LoggingCog(bot))

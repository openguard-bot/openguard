import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from typing import Optional, Union

from .aimod_helpers.config_manager import (
    get_guild_config_async,
    set_guild_config,
    VANITY_LOCK_KEY,
    VANITY_NOTIFY_CHANNEL_KEY,
    VANITY_NOTIFY_TARGET_KEY,
)


class VanityLockCog(commands.Cog):
    """Cog to lock a guild's vanity URL to a specific code."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _set_vanity_code(self, guild_id: int, code: str) -> bool:
        session = await self._ensure_session()
        url = f"https://discord.com/api/v10/guilds/{guild_id}/vanity-url"
        headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json",
        }
        async with session.patch(url, json={"code": code}, headers=headers) as resp:
            return resp.status == 200

    @commands.hybrid_group(name="vanity", description="Manage vanity URL lock")
    async def vanity(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @vanity.command(name="lock", description="Lock the server vanity URL")
    @app_commands.describe(code="The vanity code to enforce")
    async def vanity_lock(self, ctx: commands.Context, code: str):
        guild = ctx.guild
        if guild.owner_id != ctx.author.id:
            await ctx.send("Only the server owner can use this command.", ephemeral=True)
            return
        await set_guild_config(guild.id, VANITY_LOCK_KEY, code)
        success = await self._set_vanity_code(guild.id, code)
        if success:
            await ctx.send(f"Vanity URL locked to `{code}`.", ephemeral=True)
        else:
            await ctx.send(
                "Lock saved but failed to set vanity URL. Check bot permissions.",
                ephemeral=True,
            )

    @vanity.command(name="unlock", description="Remove vanity URL lock")
    async def vanity_unlock(self, ctx: commands.Context):
        guild = ctx.guild
        if guild.owner_id != ctx.author.id:
            await ctx.send("Only the server owner can use this command.", ephemeral=True)
            return
        await set_guild_config(guild.id, VANITY_LOCK_KEY, None)
        await ctx.send("Vanity URL lock removed.", ephemeral=True)

    @vanity.command(name="notify", description="Set notification channel and ping")
    @app_commands.describe(channel="Channel for vanity change alerts", target="Member or role to mention")
    async def vanity_notify(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        target: Optional[Union[discord.Member, discord.Role]] = None,
    ):
        guild = ctx.guild
        if guild.owner_id != ctx.author.id:
            await ctx.send("Only the server owner can use this command.", ephemeral=True)
            return
        channel_id = channel.id if channel else None
        target_id = target.id if target else None
        await set_guild_config(guild.id, VANITY_NOTIFY_CHANNEL_KEY, channel_id)
        await set_guild_config(guild.id, VANITY_NOTIFY_TARGET_KEY, target_id)
        if channel:
            await ctx.send("Notification settings updated.", ephemeral=True)
        else:
            await ctx.send("Notifications disabled.", ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if before.vanity_url_code == after.vanity_url_code:
            return
        locked_code = await get_guild_config_async(after.id, VANITY_LOCK_KEY)
        notify_channel_id = await get_guild_config_async(after.id, VANITY_NOTIFY_CHANNEL_KEY)
        notify_target_id = await get_guild_config_async(after.id, VANITY_NOTIFY_TARGET_KEY)

        changer = None
        if after.me.guild_permissions.view_audit_log:
            try:
                async for entry in after.audit_logs(action=discord.AuditLogAction.guild_update, limit=5):
                    before_change = getattr(entry.before, "vanity_url_code", None)
                    after_change = getattr(entry.after, "vanity_url_code", None)
                    if before_change == before.vanity_url_code and after_change == after.vanity_url_code:
                        changer = entry.user
                        break
            except discord.Forbidden:
                pass

        if locked_code and after.vanity_url_code != locked_code:
            await self._set_vanity_code(after.id, locked_code)

        if notify_channel_id:
            channel = after.get_channel(notify_channel_id)
            if not channel:
                try:
                    channel = await after.fetch_channel(notify_channel_id)
                except Exception:
                    channel = None
        else:
            channel = None

        mention = ""
        if notify_target_id:
            target = after.get_role(notify_target_id) or after.get_member(notify_target_id)
            if target:
                mention = target.mention

        message = f"Vanity URL changed: `{before.vanity_url_code}` → `{after.vanity_url_code}`"
        if locked_code and after.vanity_url_code != locked_code:
            message += f" (reverted to `{locked_code}`)"
        if changer:
            message += f" by {changer.mention}"

        if channel:
            try:
                await channel.send(f"{mention} {message}" if mention else message)
            except Exception:
                pass
        else:
            try:
                owner = after.owner
                if owner:
                    await owner.send(message)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(VanityLockCog(bot))

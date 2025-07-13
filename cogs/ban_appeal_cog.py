import discord
from discord.ext import commands
from discord import app_commands
import datetime
import logging

import cogs.logging_helpers.settings_manager as sm


log = logging.getLogger(__name__)


class BanAppealModal(discord.ui.Modal):
    """Modal for submitting a ban appeal."""

    appeal_reason = discord.ui.TextInput(
        label="Why should you be unbanned?",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(self, guild_id: int):
        super().__init__(title="Ban Appeal")
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        guild = interaction.client.get_guild(self.guild_id)
        if not guild:
            await interaction.response.send_message(
                "Server not found. I might have left the guild.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="New Ban Appeal",
            description=self.appeal_reason.value,
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(
            name="User",
            value=f"{interaction.user} ({interaction.user.id})",
            inline=False,
        )
        embed.add_field(name="Server", value=f"{guild.name} ({guild.id})", inline=False)

        # --- New Logic using settings_manager ---
        channel = None
        content = None

        try:
            # 1. Determine the destination channel with fallback logic
            appeal_channel_id = await sm.get_ban_appeal_channel_id(guild.id)
            if appeal_channel_id:
                channel = guild.get_channel(appeal_channel_id)
            else:
                # Fallback to mod log channel
                mod_log_channel_id = await sm.get_mod_log_channel_id(guild.id)
                if mod_log_channel_id:
                    channel = guild.get_channel(mod_log_channel_id)

            # 2. If no channel is configured, fall back to the guild owner's DMs
            if not channel:
                owner = guild.owner
                if owner:
                    try:
                        channel = owner.dm_channel or await owner.create_dm()
                    except discord.Forbidden:
                        log.warning(
                            f"Could not create DM channel for guild owner {owner.id} in guild {guild.id}."
                        )
                        channel = None

            # 3. Determine if we need to ping the moderator role
            should_ping = await sm.get_ping_on_ban_appeal(guild.id)
            if should_ping:
                mod_role_id = await sm.get_moderator_role_id(guild.id)
                if mod_role_id:
                    mod_role = guild.get_role(mod_role_id)
                    if mod_role:
                        content = f"New ban appeal submitted. {mod_role.mention}"

            # 4. Send the appeal
            if channel:
                try:
                    await channel.send(content=content, embed=embed)
                except discord.Forbidden:
                    log.error(
                        f"Missing permissions to send ban appeal to channel {channel.id} in guild {guild.id}."
                    )
                except Exception as e:
                    log.error(f"Error sending appeal to channel {channel.id}: {e}")
            else:
                log.warning(
                    f"No valid channel or owner DM could be found to send ban appeal for guild {guild.id}."
                )

        except Exception as e:
            log.exception(f"An error occurred during the ban appeal submission process for guild {guild.id}: {e}")

        await interaction.response.send_message(
            "Your appeal has been submitted.", ephemeral=True
        )


class BanAppealView(discord.ui.View):
    """Persistent view with a button to open the appeal modal."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="Appeal Ban", style=discord.ButtonStyle.green)
    async def appeal_button(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(BanAppealModal(self.guild_id))


class AppealSelectView(discord.ui.View):
    """View listing guilds for a user to choose where to appeal."""

    def __init__(self, guilds: list[discord.Guild]):
        super().__init__(timeout=60)
        for guild in guilds:
            custom_id = f"appeal_select_{guild.id}"
            button = discord.ui.Button(
                label=guild.name[:80],
                style=discord.ButtonStyle.primary,
                custom_id=custom_id,
            )
            button.callback = self._make_callback(guild.id)
            self.add_item(button)

    def _make_callback(self, guild_id: int):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(BanAppealModal(guild_id))

        return callback


class BanAppealCog(commands.Cog):
    """Cog providing a ban appeal command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="banappeal", description="Appeal a server ban.")
    async def appeal_command(self, ctx: commands.Context) -> None:
        """Command to appeal a ban in servers the bot is in."""
        wait_msg = await ctx.send("Please wait while I check your bans...")
        user = ctx.author
        banned_guilds = []
        for guild in self.bot.guilds:
            me = guild.me
            if not me:
                continue
            try:
                await guild.fetch_ban(user)
            except discord.NotFound:
                continue
            except discord.Forbidden:
                continue
            except discord.HTTPException:
                continue
            else:
                banned_guilds.append(guild)

        if not banned_guilds:
            await wait_msg.edit(
                content="You are not banned in any servers I'm in."
            )
            return

        banned_guilds = banned_guilds[:25]
        description = "\n".join(f"- {g.name} ({g.id})" for g in banned_guilds)
        view = AppealSelectView(banned_guilds)
        await ctx.send(
            f"You are banned in the following servers:\n{description}\nSelect one to submit an appeal:",
            view=view,
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BanAppealCog(bot))
    log.info("BanAppealCog loaded.")

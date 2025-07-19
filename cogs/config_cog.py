import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from database.models import ActionType
from .aimod_helpers.config_manager import (
    get_guild_config_async,
    set_guild_config,
    GUILD_LANGUAGE_KEY,
)
from .logging_helpers import settings_manager


class ConfigCog(commands.Cog, name="Configuration"):
    """
    Commands for configuring the AI moderation system for a guild.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(
        name="config", description="Configure AI moderation settings."
    )
    async def config(self, ctx: commands.Context):
        """Configure AI moderation settings."""
        await ctx.send_help(ctx.command)

    @config.group(name="logging", description="Configure logging settings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def logging(self, ctx: commands.Context):
        """Configure logging settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @logging.command(name="set", description="Set the channel for a specific log type.")
    @app_commands.describe(
        log_type="The type of log to configure.",
        channel="The text channel to send the logs to. Leave empty to disable.",
    )
    @app_commands.choices(
        log_type=[
            app_commands.Choice(name="Moderation Logs", value="moderation"),
            app_commands.Choice(name="Server Event Logs", value="server_events"),
            app_commands.Choice(name="AI Action Logs", value="ai_actions"),
        ]
    )
    async def logging_set(
        self,
        ctx: commands.Context,
        log_type: app_commands.Choice[str],
        channel: Optional[discord.TextChannel],
    ):
        """Sets the channel for a specific log type."""
        guild_id = ctx.guild.id
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )

        if log_type.value == "server_events":
            if channel:
                # Check for existing webhooks in the channel
                existing_webhook = None
                try:
                    for wh in await channel.webhooks():
                        if wh.name == f"{ctx.guild.name}-server-events-log":
                            existing_webhook = wh
                            break
                except discord.Forbidden:
                    await response_func(
                        "I don't have permissions to manage webhooks in that channel. Please grant 'Manage Webhooks' permission.",
                        ephemeral=True,
                    )
                    return
                except Exception as e:
                    await response_func(
                        f"An error occurred while checking webhooks: {e}",
                        ephemeral=True,
                    )
                    return

                if existing_webhook:
                    webhook_url = existing_webhook.url
                    message = f"Server Event Logs will now be sent to {channel.mention} using the existing webhook."
                else:
                    try:
                        webhook = await channel.create_webhook(name=f"{ctx.guild.name}-server-events-log")
                        webhook_url = webhook.url
                        message = f"Server Event Logs will now be sent to {channel.mention} via a new webhook."
                    except discord.Forbidden:
                        await response_func(
                            "I don't have permissions to create webhooks in that channel. Please grant 'Manage Webhooks' permission.",
                            ephemeral=True,
                        )
                        return
                    except Exception as e:
                        await response_func(
                            f"An error occurred while creating webhook: {e}",
                            ephemeral=True,
                        )
                        return
                
                await settings_manager.set_logging_webhook(guild_id, webhook_url)
                await response_func(message, ephemeral=True)
            else:
                # Disable server event logging by clearing the webhook URL
                await settings_manager.set_logging_webhook(guild_id, None)
                await response_func(f"{log_type.name} have been disabled.", ephemeral=True)
        else:
            # Existing logic for other log types (moderation, ai_actions)
            key_map = {
                "moderation": "moderation_log_channel_id",
                "ai_actions": "ai_actions_log_channel_id",
            }
            key = key_map[log_type.value]
            channel_id = channel.id if channel else None
            await set_guild_config(guild_id, key, channel_id)

            if channel:
                await response_func(
                    f"{log_type.name} will now be sent to {channel.mention}.",
                    ephemeral=True,
                )
            else:
                await response_func(f"{log_type.name} have been disabled.", ephemeral=True)

    @config.command(
        name="setlang", description="Set the language for bot responses in this guild."
    )
    @app_commands.describe(language="The language to use")
    @app_commands.choices(
        language=[
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="Spanish", value="es"),
            app_commands.Choice(name="German", value="de"),
            app_commands.Choice(name="Korean", value="ko"),
            app_commands.Choice(name="Japanese", value="ja"),
            app_commands.Choice(name="Russian", value="ru"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_language(
        self, ctx: commands.Context, language: app_commands.Choice[str]
    ):
        """Sets the language for bot responses in this guild."""
        guild_id = ctx.guild.id
        lang_code = language.value
        await set_guild_config(guild_id, GUILD_LANGUAGE_KEY, lang_code)
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(
            f"Bot language set to `{lang_code}` for this guild.",
            ephemeral=False if ctx.interaction else False,
        )

    @config.command(
        name="suggestionschannel", description="Set the suggestions channel."
    )
    @app_commands.describe(channel="The text channel to use for suggestions.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_suggestions_channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        await set_guild_config(ctx.guild.id, "SUGGESTIONS_CHANNEL_ID", channel.id)
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(
            f"Suggestions channel set to {channel.mention}.",
            ephemeral=False if ctx.interaction else False,
        )

    @config.command(name="moderatorrole", description="Set the moderator role.")
    @app_commands.describe(role="The role that identifies moderators.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_moderator_role(self, ctx: commands.Context, role: discord.Role):
        await set_guild_config(ctx.guild.id, "MODERATOR_ROLE_ID", role.id)
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(
            f"Moderator role set to {role.mention}.",
            ephemeral=False if ctx.interaction else False,
        )

    @config.command(
        name="suicidalpingrole",
        description="Set the role to ping for suicidal content.",
    )
    @app_commands.describe(role="The role to ping for urgent suicidal content alerts.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_suicidal_ping_role(
        self, ctx: commands.Context, role: discord.Role
    ):
        await set_guild_config(ctx.guild.id, "SUICIDAL_PING_ROLE_ID", role.id)
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(
            f"Suicidal content ping role set to {role.mention}.",
            ephemeral=False if ctx.interaction else False,
        )

    @config.command(
        name="addnsfwchannel", description="Add a channel to the list of NSFW channels."
    )
    @app_commands.describe(channel="The text channel to mark as NSFW for the bot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_add_nsfw_channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        guild_id = ctx.guild.id
        nsfw_channels: list[int] = await get_guild_config_async(
            guild_id, "NSFW_CHANNEL_IDS", []
        )
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        if channel.id not in nsfw_channels:
            nsfw_channels.append(channel.id)
            await set_guild_config(guild_id, "NSFW_CHANNEL_IDS", nsfw_channels)
            await response_func(
                f"{channel.mention} added to NSFW channels list.",
                ephemeral=False if ctx.interaction else False,
            )
        else:
            await response_func(
                f"{channel.mention} is already in the NSFW channels list.",
                ephemeral=True if ctx.interaction else False,
            )

    @config.command(
        name="removensfwchannel",
        description="Remove a channel from the list of NSFW channels.",
    )
    @app_commands.describe(channel="The text channel to remove from the NSFW list.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_remove_nsfw_channel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ):
        guild_id = ctx.guild.id
        nsfw_channels: list[int] = await get_guild_config_async(
            guild_id, "NSFW_CHANNEL_IDS", []
        )
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        if channel.id in nsfw_channels:
            nsfw_channels.remove(channel.id)
            await set_guild_config(guild_id, "NSFW_CHANNEL_IDS", nsfw_channels)
            await response_func(
                f"{channel.mention} removed from NSFW channels list.",
                ephemeral=False if ctx.interaction else False,
            )
        else:
            await response_func(
                f"{channel.mention} is not in the NSFW channels list.",
                ephemeral=True if ctx.interaction else False,
            )

    @config.command(
        name="listnsfwchannels", description="List currently configured NSFW channels."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_list_nsfw_channels(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        nsfw_channel_ids: list[int] = await get_guild_config_async(
            guild_id, "NSFW_CHANNEL_IDS", []
        )
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        if not nsfw_channel_ids:
            await response_func(
                "No NSFW channels are currently configured.",
                ephemeral=False if ctx.interaction else False,
            )
            return

        channel_mentions = []
        for channel_id in nsfw_channel_ids:
            channel_obj = ctx.guild.get_channel(channel_id)
            if channel_obj:
                channel_mentions.append(channel_obj.mention)
            else:
                channel_mentions.append(f"ID:{channel_id} (not found)")

        await response_func(
            f"Configured NSFW channels:\n- " + "\n- ".join(channel_mentions),
            ephemeral=False if ctx.interaction else False,
        )

    @config.command(
        name="set_action_confirmation",
        description="Set the confirmation mode for a specific AI moderation action.",
    )
    @app_commands.describe(
        action="The AI action to configure.",
        mode="The confirmation mode to set for this action.",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Warn", value=ActionType.WARN.value),
            app_commands.Choice(
                name="Timeout (Short)", value=ActionType.TIMEOUT_SHORT.value
            ),
            app_commands.Choice(
                name="Timeout (Medium)", value=ActionType.TIMEOUT_MEDIUM.value
            ),
            app_commands.Choice(
                name="Timeout (Long)", value=ActionType.TIMEOUT_LONG.value
            ),
            app_commands.Choice(name="Kick", value=ActionType.KICK.value),
            app_commands.Choice(name="Ban", value=ActionType.BAN.value),
        ],
        mode=[
            app_commands.Choice(name="Automatic", value="automatic"),
            app_commands.Choice(name="Manual", value="manual"),
        ],
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_action_confirmation(
        self,
        ctx: commands.Context,
        action: app_commands.Choice[str],
        mode: app_commands.Choice[str],
    ):
        """Sets the confirmation mode for a specific AI moderation action."""
        guild_id = ctx.guild.id
        key = "ACTION_CONFIRMATION_SETTINGS"
        settings = await get_guild_config_async(guild_id, key, {})
        settings[action.value] = mode.value
        await set_guild_config(guild_id, key, settings)
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(
            f"Confirmation mode for **{action.name}** set to **{mode.name}**.",
            ephemeral=True,
        )

    @config.command(
        name="view_action_confirmations",
        description="View the current AI action confirmation settings.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def view_action_confirmations(self, ctx: commands.Context):
        """Views the current AI action confirmation settings."""
        guild_id = ctx.guild.id
        key = "ACTION_CONFIRMATION_SETTINGS"
        settings = await get_guild_config_async(guild_id, key, {})

        embed = discord.Embed(
            title="Action Confirmation Settings",
            description="This shows which AI moderation actions are automatic and which require manual moderator approval.",
            color=discord.Color.blue(),
        )

        action_types = [
            ActionType.WARN,
            ActionType.TIMEOUT_SHORT,
            ActionType.TIMEOUT_MEDIUM,
            ActionType.TIMEOUT_LONG,
            ActionType.KICK,
            ActionType.BAN,
        ]

        for action in action_types:
            mode = settings.get(action.value, "automatic")  # Default to automatic
            action_name = action.name.replace("_", " ").title()
            embed.add_field(
                name=action_name, value=f"`{mode.capitalize()}`", inline=True
            )

        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(embed=embed, ephemeral=True)

    @config.command(
        name="set_confirmation_ping_role",
        description="Set the role to ping when an action requires confirmation.",
    )
    @app_commands.describe(role="The role to ping for manual confirmation.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_confirmation_ping_role(
        self, ctx: commands.Context, role: discord.Role
    ):
        """Sets the role to ping for manual confirmation."""
        guild_id = ctx.guild.id
        key = "CONFIRMATION_PING_ROLE_ID"
        await set_guild_config(guild_id, key, role.id)
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(
            f"Confirmation ping role set to {role.mention}.", ephemeral=False
        )

    @config.command(
        name="clear_confirmation_ping_role",
        description="Clear the role that is pinged for manual confirmation.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_confirmation_ping_role(self, ctx: commands.Context):
        """Clears the role that is pinged for manual confirmation."""
        guild_id = ctx.guild.id
        key = "CONFIRMATION_PING_ROLE_ID"
        await set_guild_config(guild_id, key, None)
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(
            f"Confirmation ping role has been cleared.", ephemeral=False
        )

    @config.command(
        name="enable",
        description="Enable or disable moderation for this guild (admin only).",
    )
    @app_commands.describe(enabled="Enable moderation (true/false)")
    @app_commands.checks.has_permissions(administrator=True)
    async def modenable(self, ctx: commands.Context, enabled: bool):
        await set_guild_config(ctx.guild.id, "ENABLED", enabled)
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        await response_func(
            f"Moderation is now {'enabled' if enabled else 'disabled'} for this guild.",
            ephemeral=False if ctx.interaction else False,
        )

    @config.command(
        name="testmode",
        description="Enable or disable AI moderation test mode for this guild (admin only).",
    )
    @app_commands.describe(enabled="Enable test mode (true/false)")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_testmode(self, ctx: commands.Context, enabled: bool):
        """Enables or disables AI moderation test mode."""
        if not ctx.guild:
            await ctx.reply(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        await set_guild_config(ctx.guild.id, "TEST_MODE_ENABLED", enabled)
        await ctx.reply(
            f"AI moderation test mode is now {'enabled' if enabled else 'disabled'} for this guild.",
            ephemeral=False,
        )

    @app_commands.command(
        name="pull_rules",
        description="Update the AI moderation rules for this guild from the rules channel.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def pull_rules(self, ctx: commands.Context):
        """
        Locates the rules channel in the guild, fetches its content, and updates the per-guild rules for AI moderation.
        """
        guild = ctx.guild
        response_func = (
            ctx.interaction.response.send_message if ctx.interaction else ctx.send
        )
        if not guild:
            await response_func(
                "This command can only be used in a server.",
                ephemeral=True if ctx.interaction else False,
            )
            return
        rules_channel = None
        for channel in guild.text_channels:
            if channel.name.lower() in ("rules", "server-rules", "rule", "guidelines"):
                rules_channel = channel
                break
        if not rules_channel:
            await response_func(
                "Could not find a rules channel (named 'rules', 'server-rules', or 'guidelines'). Please specify the channel name or create one.",
                ephemeral=True if ctx.interaction else False,
            )
            return
        try:
            messages = [
                msg async for msg in rules_channel.history(limit=10, oldest_first=True)
            ]
            rules_content = []

            for msg in messages:
                # Add regular message content if it exists
                if msg.content.strip():
                    rules_content.append(msg.content.strip())

                # Add embed content if embeds exist
                if msg.embeds:
                    for embed in msg.embeds:
                        embed_text_parts = []

                        # Add embed title
                        if embed.title:
                            embed_text_parts.append(f"**{embed.title}**")

                        # Add embed description
                        if embed.description:
                            embed_text_parts.append(embed.description)

                        # Add embed fields
                        if embed.fields:
                            for field in embed.fields:
                                if field.name and field.value:
                                    embed_text_parts.append(
                                        f"**{field.name}**\n{field.value}"
                                    )

                        # Add embed footer
                        if embed.footer and embed.footer.text:
                            embed_text_parts.append(f"*{embed.footer.text}*")

                        # Join all embed parts and add to rules content
                        if embed_text_parts:
                            rules_content.append("\n".join(embed_text_parts))

            rules_text = "\n\n".join(rules_content)
        except Exception as e:
            await response_func(
                f"Failed to fetch messages from the rules channel: {e}",
                ephemeral=True if ctx.interaction else False,
            )
            return
        if not rules_text.strip():
            await response_func(
                "The rules channel appears to be empty.",
                ephemeral=True if ctx.interaction else False,
            )
            return
        try:
            await set_guild_config(guild.id, "SERVER_RULES", rules_text)
            await response_func(
                "Successfully updated the AI moderation rules for this guild from the rules channel.",
                ephemeral=True if ctx.interaction else False,
            )
        except Exception as e:
            await response_func(
                f"Failed to update rules in config: {e}",
                ephemeral=True if ctx.interaction else False,
            )
            return


async def setup(bot: commands.Bot):
    """Loads the ConfigCog."""
    await bot.add_cog(ConfigCog(bot))
    print("ConfigCog has been loaded.")

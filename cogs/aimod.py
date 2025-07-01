import json
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import collections
import datetime
import base64
import uuid
import random
import os
import asyncio
import aiofiles
from google.genai import types
from google.api_core import exceptions as google_exceptions
import google.genai as genai
from .aimod_helpers.ui import AppealButton, AppealActions
from .aimod_helpers.config_manager import (
    VERTEX_PROJECT_ID, VERTEX_LOCATION, DEFAULT_VERTEX_AI_MODEL, STANDARD_SAFETY_SETTINGS,
    MOD_LOG_API_SECRET_ENV_VAR,
    GUILD_CONFIG, USER_INFRACTIONS, APPEALS, GLOBAL_BANS,
    save_guild_config, save_user_infractions, save_appeals, save_global_bans,
    get_guild_config, set_guild_config, t, GUILD_LANGUAGE_KEY, DEFAULT_LANGUAGE,
)
from .aimod_helpers.utils import (
    truncate_text, format_timestamp, get_user_infraction_history, add_user_infraction
)
from .aimod_helpers.media_processor import MediaProcessor
from .aimod_helpers.system_prompt import SUICIDAL_HELP_RESOURCES, SYSTEM_PROMPT_TEMPLATE

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DEV_AIMODTEST_USER_IDS = {1146391317295935570, 452666956353503252, 1141746562922459136}
DEV_AIMODTEST_ENABLED = False

def is_dev_aimodtest_user(interaction: discord.Interaction) -> bool:
    return interaction.user.id in DEV_AIMODTEST_USER_IDS

class ModerationCog(commands.Cog):
    """
    A Discord Cog that uses Vertex AI to moderate messages based on server rules.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.last_ai_decisions = collections.deque(maxlen=5)
        self.media_processor = MediaProcessor()
        try:
            self.genai_client = genai.Client(vertexai=False, api_key=GEMINI_API_KEY)
            print("ModerationCog: GenAI client initialized successfully.")
        except Exception as e:
            print(f"ModerationCog: Failed to initialize GenAI client: {e}")
            self.genai_client = None
        print("ModerationCog Initializing.")

    async def cog_load(self):
        print("ModerationCog cog_load started.")
        if not self.genai_client:
            try:
                self.genai_client = genai.Client(vertexai=False, api_key=GEMINI_API_KEY)
                print("ModerationCog: GenAI client re-initialized on load.")
            except Exception as e:
                print(f"ModerationCog: Failed to re-initialize GenAI client on load: {e}")
        print("ModerationCog cog_load finished.")

        # Auto-ban any users already in servers who are on the global ban list
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.id in GLOBAL_BANS:
                    try:
                        ban_reason = "Globally banned for severe universal violation. (Auto-enforced on cog load)"
                        await guild.ban(member, reason=ban_reason)
                        print(f"[GLOBAL BAN] Auto-banned {member} ({member.id}) from {guild.name} on cog load.")
                        try:
                            dm_channel = await member.create_dm()
                            await dm_channel.send(f"You have been globally banned for a severe universal violation and have been banned from **{guild.name}**.")
                        except Exception as e:
                            print(f"Could not DM globally banned user {member}: {e}")
                        # Optionally log to mod log channel
                        log_channel_id = get_guild_config(guild.id, "MOD_LOG_CHANNEL_ID")
                        log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
                        if log_channel:
                            embed = discord.Embed(
                                title="🚨 Global Ban Enforcement 🚨",
                                description=f"Globally banned user was present and has been auto-banned.",
                                color=discord.Color.dark_red()
                            )
                            embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
                            embed.add_field(name="Action", value="Automatically Banned (Global Ban List)", inline=False)
                            embed.add_field(name="Reason", value=ban_reason, inline=False)
                            embed.timestamp = discord.utils.utcnow()
                            try:
                                await log_channel.send(embed=embed)
                            except discord.Forbidden:
                                print(f"WARNING: Missing permissions to send global ban enforcement log to channel {log_channel.id} in guild {guild.id}.")
                            except Exception as e:
                                print(f"Error sending global ban enforcement log: {e}")
                    except discord.Forbidden:
                        print(f"WARNING: Missing permissions to ban user {member} ({member.id}) from guild {guild.name} during cog load.")
                    except Exception as e:
                        print(f"Error auto-banning globally banned user {member} ({member.id}) from guild {guild.name}: {e}")

    async def cog_unload(self):
        if self.session:
            await self.session.close()
        print("ModerationCog Unloaded, session closed.")

    aimod_group = app_commands.Group(name="aimod", description="AI Moderation commands.")
    config_subgroup = app_commands.Group(name="config", description="Configure AI moderation settings.", parent=aimod_group)
    infractions_subgroup = app_commands.Group(name="infractions", description="Manage user infractions.", parent=aimod_group)
    globalban_subgroup = app_commands.Group(name="globalban", description="Manage global bans.", parent=aimod_group)
    model_subgroup = app_commands.Group(name="model", description="Manage the AI model for moderation.", parent=aimod_group)
    debug_subgroup = app_commands.Group(name="debug", description="Debugging commands for AI moderation.", parent=aimod_group)
    appeals_subgroup = app_commands.Group(name="appeals", description="Manage moderation appeals.", parent=aimod_group)

    @globalban_subgroup.command(name="manage", description="Add or remove a user from the global ban list.")
    @app_commands.describe(action="Whether to add or remove the user.", userid="The ID of the user to manage.")
    @app_commands.choices(action=[
        app_commands.Choice(name="Add", value="add"),
        app_commands.Choice(name="Remove", value="remove"),
    ])
    @app_commands.check(is_dev_aimodtest_user)
    async def globalban_manage(self, interaction: discord.Interaction, action: app_commands.Choice[str], userid: str, globalbanreason: str):
        """Adds or removes a user from the global ban list."""

        try:
            user_id = int(userid)
        except ValueError:
            await interaction.response.send_message("Invalid user ID. Please provide a numerical user ID.", ephemeral=True)
            return

        global GLOBAL_BANS
        if action.value == "add":
            if user_id not in GLOBAL_BANS:
                GLOBAL_BANS.append(user_id)
                await save_global_bans()
                await interaction.response.send_message(f"User ID `{user_id}` added to the global ban list. Reason {globalbanreason}", ephemeral=False)
                print(f"[MODERATION] User ID {user_id} added to global ban list by {interaction.user} ({interaction.user.id}).")
            else:
                await interaction.response.send_message(f"User ID `{user_id}` is already in the global ban list.", ephemeral=True)
        elif action.value == "remove":
            if user_id in GLOBAL_BANS:
                GLOBAL_BANS.remove(user_id)
                await save_global_bans()
                await interaction.response.send_message(f"User ID `{user_id}` removed from the global ban list. {globalbanreason}", ephemeral=False)
                print(f"[MODERATION] User ID {user_id} removed from global ban list by {interaction.user} ({interaction.user.id}).")
            else:
                await interaction.response.send_message(f"User ID `{user_id}` is not in the global ban list.", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid action. Please choose 'add' or 'remove'.", ephemeral=True)

    aimoddata_group = app_commands.Group(name="aimoddata", description="AI Mod Data commands.")

    @aimoddata_group.command(name="stats", description="Show bot stats")
    async def aimoddata_stats(self, interaction: discord.Interaction):
        bot_user = self.bot.user
        if not bot_user:
            await interaction.response.send_message("Bot user not found.", ephemeral=True)
            return
        server_count = len(self.bot.guilds)
        embed = discord.Embed(
            title="AiMod Project Beta",
            description=f"servers being guarded: **{server_count}**",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=bot_user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @aimod_group.command(name="testlog", description="Send a test moderation log embed.")
    @app_commands.describe(language="The language code for the embed (e.g., 'en', 'es', 'ja')", action="The action to simulate ('timeout', 'kick', 'ban')")
    @app_commands.choices(action=[
        app_commands.Choice(name="Timeout", value="timeout"),
        app_commands.Choice(name="Kick", value="kick"),
        app_commands.Choice(name="Ban", value="ban"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def aimod_testlog(self, interaction: discord.Interaction, language: str, action: app_commands.Choice[str]):
        """Sends a test moderation log embed."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        simulated_user_name = "test"
        simulated_user_id = 1234567890
        simulated_reasoning = "this is a test"
        simulated_rule = "Test Rule"
        simulated_action = action.value.upper()

        class DummyMessage:
            def __init__(self, author, channel, guild, content, id, jump_url):
                self.author = author
                self.channel = channel
                self.guild = guild
                self.content = content
                self.id = id
                self.jump_url = jump_url
                self.attachments = []

        class DummyAuthor:
            def __init__(self, name, id):
                self.display_name = name
                self.id = id
                self.mention = f"<@{id}>"
                self.guild_permissions = discord.Permissions(administrator=False)

            def __str__(self):
                return self.display_name

        dummy_author = DummyAuthor(simulated_user_name, simulated_user_id)
        dummy_message = DummyMessage(
            author=dummy_author,
            channel=interaction.channel,
            guild=interaction.guild,
            content="This is a test message content.",
            id=9876543210,
            jump_url="https://discord.com/channels/dummy/dummy/dummy"
        )

        notification_embed = discord.Embed(
            title="🚨 Rule Violation Detected (TEST) 🚨",
            description=f"AI analysis detected a violation of server rules.",
            color=discord.Color.red()
        )
        notification_embed.add_field(name="User", value=f"{dummy_author.mention} (`{dummy_author.id}`)", inline=False)
        notification_embed.add_field(name="Channel", value=interaction.channel.mention, inline=False)
        notification_embed.add_field(name="Rule Violated", value=f"**{simulated_rule}**", inline=True)
        notification_embed.add_field(name="AI Suggested Action", value=f"`{simulated_action}`", inline=True)
        notification_embed.add_field(name="AI Reasoning", value=f"_{simulated_reasoning}_", inline=False)
        notification_embed.add_field(name="Message Link", value=f"[Jump to Message]({dummy_message.jump_url})", inline=False)
        notification_embed.add_field(name="Message Content", value=dummy_message.content, inline=False)

        if simulated_action == "BAN":
            notification_embed.color = discord.Color.dark_red()
        elif simulated_action == "KICK":
            notification_embed.color = discord.Color.from_rgb(255, 127, 0)
        elif simulated_action == "TIMEOUT":
            notification_embed.color = discord.Color.blue()

        footer_text = f"Test Log | Language: {language} | Simulated Action: {simulated_action}"
        notification_embed.set_footer(text=footer_text)
        notification_embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=notification_embed, ephemeral=False)


    @config_subgroup.command(name="logchannel", description="Set the moderation log channel.")
    @app_commands.describe(channel="The text channel to use for moderation logs.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_guild_config(interaction.guild.id, "MOD_LOG_CHANNEL_ID", channel.id)
        await interaction.response.send_message(f"Moderation log channel set to {channel.mention}.", ephemeral=False)

    @config_subgroup.command(name="setlang", description="Set the language for bot responses in this guild.")
    @app_commands.describe(language="The language to use")
    @app_commands.choices(language=[
        app_commands.Choice(name="English", value="en"),
        app_commands.Choice(name="Spanish", value="es"),
        app_commands.Choice(name="German", value="de"),
        app_commands.Choice(name="Korean", value="ko"),
        app_commands.Choice(name="Japanese", value="ja"),
        app_commands.Choice(name="Russian", value="ru"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_language(self, interaction: discord.Interaction, language: app_commands.Choice[str]):
        """Sets the language for bot responses in this guild."""
        guild_id = interaction.guild.id
        lang_code = language.value
        await set_guild_config(guild_id, GUILD_LANGUAGE_KEY, lang_code)
        await interaction.response.send_message(f"Bot language set to `{lang_code}` for this guild.", ephemeral=False)


    @config_subgroup.command(name="suggestionschannel", description="Set the suggestions channel.")
    @app_commands.describe(channel="The text channel to use for suggestions.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_suggestions_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_guild_config(interaction.guild.id, "SUGGESTIONS_CHANNEL_ID", channel.id)
        await interaction.response.send_message(f"Suggestions channel set to {channel.mention}.", ephemeral=False)

    @config_subgroup.command(name="moderatorrole", description="Set the moderator role.")
    @app_commands.describe(role="The role that identifies moderators.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_moderator_role(self, interaction: discord.Interaction, role: discord.Role):
        await set_guild_config(interaction.guild.id, "MODERATOR_ROLE_ID", role.id)
        await interaction.response.send_message(f"Moderator role set to {role.mention}.", ephemeral=False)

    @config_subgroup.command(name="suicidalpingrole", description="Set the role to ping for suicidal content.")
    @app_commands.describe(role="The role to ping for urgent suicidal content alerts.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_suicidal_ping_role(self, interaction: discord.Interaction, role: discord.Role):
        await set_guild_config(interaction.guild.id, "SUICIDAL_PING_ROLE_ID", role.id)
        await interaction.response.send_message(f"Suicidal content ping role set to {role.mention}.", ephemeral=False)

    @config_subgroup.command(name="addnsfwchannel", description="Add a channel to the list of NSFW channels.")
    @app_commands.describe(channel="The text channel to mark as NSFW for the bot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_add_nsfw_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id
        nsfw_channels: list[int] = get_guild_config(guild_id, "NSFW_CHANNEL_IDS", [])
        if channel.id not in nsfw_channels:
            nsfw_channels.append(channel.id)
            await set_guild_config(guild_id, "NSFW_CHANNEL_IDS", nsfw_channels)
            await interaction.response.send_message(f"{channel.mention} added to NSFW channels list.", ephemeral=False)
        else:
            await interaction.response.send_message(f"{channel.mention} is already in the NSFW channels list.", ephemeral=True)

    @config_subgroup.command(name="removensfwchannel", description="Remove a channel from the list of NSFW channels.")
    @app_commands.describe(channel="The text channel to remove from the NSFW list.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_remove_nsfw_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id
        nsfw_channels: list[int] = get_guild_config(guild_id, "NSFW_CHANNEL_IDS", [])
        if channel.id in nsfw_channels:
            nsfw_channels.remove(channel.id)
            await set_guild_config(guild_id, "NSFW_CHANNEL_IDS", nsfw_channels)
            await interaction.response.send_message(f"{channel.mention} removed from NSFW channels list.", ephemeral=False)
        else:
            await interaction.response.send_message(f"{channel.mention} is not in the NSFW channels list.", ephemeral=True)

    @config_subgroup.command(name="listnsfwchannels", description="List currently configured NSFW channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def modset_list_nsfw_channels(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        nsfw_channel_ids: list[int] = get_guild_config(guild_id, "NSFW_CHANNEL_IDS", [])
        if not nsfw_channel_ids:
            await interaction.response.send_message("No NSFW channels are currently configured.", ephemeral=False)
            return

        channel_mentions = []
        for channel_id in nsfw_channel_ids:
            channel_obj = interaction.guild.get_channel(channel_id)
            if channel_obj:
                channel_mentions.append(channel_obj.mention)
            else:
                channel_mentions.append(f"ID:{channel_id} (not found)")

        await interaction.response.send_message(f"Configured NSFW channels:\n- " + "\n- ".join(channel_mentions), ephemeral=False)

    @config_subgroup.command(name="enable", description="Enable or disable moderation for this guild (admin only).")
    @app_commands.describe(enabled="Enable moderation (true/false)")
    async def modenable(self, interaction: discord.Interaction, enabled: bool):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=False)
            return
        await set_guild_config(interaction.guild.id, "ENABLED", enabled)
        await interaction.response.send_message(f"Moderation is now {'enabled' if enabled else 'disabled'} for this guild.", ephemeral=False)

    @infractions_subgroup.command(name="view", description="View a user's AI moderation infraction history (mod/admin only).")
    @app_commands.describe(user="The user to view infractions for")
    async def viewinfractions(self, interaction: discord.Interaction, user: discord.Member):
        moderator_role_id = get_guild_config(interaction.guild.id, "MODERATOR_ROLE_ID")
        moderator_role = interaction.guild.get_role(moderator_role_id) if moderator_role_id else None

        has_permission = (interaction.user.guild_permissions.administrator or
                         (moderator_role and moderator_role in interaction.user.roles))

        if not has_permission:
            await interaction.response.send_message("You must be an administrator or have the moderator role to use this command.", ephemeral=True)
            return

        infractions = get_user_infraction_history(interaction.guild.id, user.id)

        if not infractions:
            await interaction.response.send_message(f"{user.mention} has no recorded infractions.", ephemeral=False)
            return

        embed = discord.Embed(
            title=f"Infraction History for {user.display_name}",
            description=f"User ID: {user.id}",
            color=discord.Color.orange()
        )

        for i, infraction in enumerate(infractions, 1):
            timestamp = infraction.get('timestamp', 'Unknown date')[:19].replace('T', ' ')
            rule = infraction.get('rule_violated', 'Unknown rule')
            action = infraction.get('action_taken', 'Unknown action')
            reason = infraction.get('reasoning', 'No reason provided')
            reason = truncate_text(reason, 200)
            embed.add_field(
                name=f"Infraction #{i} - {timestamp}",
                value=f"**Rule Violated:** {rule}\n**Action Taken:** {action}\n**Reason:** {reason}",
                inline=False
            )

        embed.set_footer(text=f"Total infractions: {len(infractions)}")
        embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @infractions_subgroup.command(name="clear", description="Clear a user's AI moderation infraction history (admin only).")
    @app_commands.describe(user="The user to clear infractions for")
    async def clearinfractions(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
            return

        key = f"{interaction.guild.id}_{user.id}"
        infractions = USER_INFRACTIONS.get(key, [])

        if not infractions:
            await interaction.response.send_message(f"{user.mention} has no recorded infractions to clear.", ephemeral=False)
            return

        USER_INFRACTIONS[key] = []
        await save_user_infractions()

        print(f"[MODERATION] Cleared {len(infractions)} infraction(s) for user {user} (ID: {user.id}) in guild {interaction.guild.name} (ID: {interaction.guild.id}) by {interaction.user} (ID: {interaction.user.id}) at {datetime.datetime.now(datetime.timezone.utc).isoformat()}.".replace(')', ')\n'))

        try:
            dm_channel = await user.create_dm()
            await dm_channel.send(f"Your infraction history in **{interaction.guild.name}** has been cleared by an administrator.")
        except discord.Forbidden:
            print(f"[MODERATION] Could not DM user {user} about infraction clearance (DMs disabled).")
        except Exception as e:
            print(f"[MODERATION] Error DMing user {user} about infraction clearance: {e}")

        await interaction.response.send_message(f"Cleared {len(infractions)} infraction(s) for {user.mention}.", ephemeral=False)

    @model_subgroup.command(name="set", description="Change the AI model used for moderation (admin only).")
    @app_commands.describe(model="The Vertex AI model to use (e.g., 'gemini-1.5-flash-001')")
    @app_commands.checks.has_permissions(administrator=True)
    async def modsetmodel(self, interaction: discord.Interaction, model: str):

        if not model or len(model) < 5:
            await interaction.response.send_message("Invalid model format. Please provide a valid Vertex AI model ID (e.g., 'gemini-1.5-flash-001').", ephemeral=False)
            return

        guild_id = interaction.guild.id
        await set_guild_config(guild_id, "AI_MODEL", model)

        await interaction.response.send_message(f"AI moderation model updated to `{model}` for this guild.", ephemeral=False)

    @model_subgroup.command(name="get", description="View the current AI model used for moderation.")
    async def modgetmodel(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        model_used = get_guild_config(guild_id, "AI_MODEL", DEFAULT_VERTEX_AI_MODEL)
        embed = discord.Embed(
            title="AI Moderation Model",
            description=f"The current AI model used for moderation in this server is:",
            color=discord.Color.blue()
        )
        embed.add_field(name="Model", value=f"`{model_used}`", inline=False)
        embed.add_field(name="Default Model", value=f"`{DEFAULT_VERTEX_AI_MODEL}`", inline=False)
        embed.set_footer(text="Use /modsetmodel to change the model")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def query_vertex_ai(self, message: discord.Message, message_content: str, user_history: str, image_data_list=None):
        """
        Sends the message content, user history, and additional context to the Vertex AI API for analysis.
        """
        guild_id = message.guild.id
        model_used = get_guild_config(guild_id, "AI_MODEL", DEFAULT_VERTEX_AI_MODEL)
        rules_text = self.get_server_rules(guild_id)
        system_prompt_text = SYSTEM_PROMPT_TEMPLATE.format(rules_text=rules_text)

        user_role = "Member"
        if message.author.guild_permissions.administrator:
            user_role = "Admin"
        elif message.author.guild_permissions.manage_messages:
            user_role = "Moderator"
        elif message.guild.owner_id == message.author.id:
            user_role = "Server Owner"

        channel_category = message.channel.category.name if message.channel.category else "No Category"
        is_nsfw_channel = getattr(message.channel, 'nsfw', False)

        replied_to_content = ""
        if message.reference and message.reference.message_id:
            try:
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                replied_to_content = f"Replied-to Message: {replied_message.author.display_name}: {replied_message.content[:200]}"
            except:
                replied_to_content = "Replied-to Message: [Could not fetch]"

        recent_history = []
        try:
            async for hist_message in message.channel.history(limit=4, before=message):
                if not hist_message.author.bot:
                    recent_history.append(f"{hist_message.author.display_name}: {hist_message.content[:100]}")
        except:
            recent_history = ["[Could not fetch recent history]"]

        recent_history_text = "\n".join(recent_history[:3]) if recent_history else "No recent history available."

        user_prompt = f"""
**Context Information:**
- User's Server Role: {user_role}
- Channel Category: {channel_category}
- Channel Age-Restricted/NSFW (Discord Setting): {is_nsfw_channel}
- {replied_to_content}
- Recent Channel History:
{recent_history_text}

**User's Infraction History:**
{user_history}

**Message Content:**
{message_content if message_content else "[No text content]"}
"""
        
        request_contents = [system_prompt_text, user_prompt]
        if image_data_list:
            for mime_type, image_bytes, attachment_type, filename in image_data_list:
                request_contents.append(types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes)))
                print(f"Added {attachment_type} attachment to AI analysis: {filename}")

        try:
            thinking_config = types.ThinkingConfig(
                thinking_budget=2048
            )
            generation_config = types.GenerateContentConfig(
                temperature=0.2,
                safety_settings=STANDARD_SAFETY_SETTINGS,
                thinking_config=thinking_config
            )
            response = await self.genai_client.aio.models.generate_content(
                model=model_used,
                contents=request_contents,
                config=generation_config,
            )
            
            ai_response_text = response.text

            if not ai_response_text:
                print("Error: Empty response from Vertex AI API.")
                return None

            try:
                json_start_index = ai_response_text.find('{')
                if json_start_index == -1:
                    print("Error: Could not find the start of the JSON object in AI response.")
                    print(f"Raw AI response: {ai_response_text}")
                    return None

                json_string = ai_response_text[json_start_index:].strip()

                if json_string.startswith("```json"):
                    json_string = json_string[7:]
                if json_string.endswith("```"):
                    json_string = json_string[:-3]
                json_string = json_string.strip()

                ai_decision = json.loads(json_string)

                required_keys = ["reasoning", "violation", "rule_violated", "action"]
                if not all(key in ai_decision for key in required_keys):
                    print(f"Error: AI response missing required keys. Got: {ai_decision}")
                    return None

                print(f"AI Decision: {ai_decision}")
                return ai_decision

            except json.JSONDecodeError as e:
                print(f"Error parsing AI response as JSON: {e}")
                print(f"Raw AI response: {ai_response_text}")
                return None
        except google_exceptions.GoogleAPICallError as e:
            print(f"Vertex AI API call error: {e}")
            return None
        except Exception as e:
            print(f"Exception during Vertex AI API call: {e}")
            return None

    async def handle_violation(self, message: discord.Message, ai_decision: dict, notify_mods_message: str = None):
        """
        Takes action based on the AI's violation decision.
        """
        guild_id = message.guild.id
        user_id = message.author.id

        test_mode_enabled = get_guild_config(guild_id, "TEST_MODE_ENABLED", False)
        if test_mode_enabled:
            print(f"Test mode is enabled for guild {guild_id}. Skipping actual moderation actions.")
            ai_decision["action"] = f"TEST_MODE_{ai_decision.get('action', 'UNKNOWN')}"
            ai_decision["reasoning"] = f"[TEST MODE] {ai_decision.get('reasoning', 'No reasoning provided.')}"

        rule_violated = ai_decision.get("rule_violated", "Unknown")
        reasoning = ai_decision.get("reasoning", "No reasoning provided.")
        action = ai_decision.get("action", "NOTIFY_MODS").upper()

        moderator_role_id = get_guild_config(guild_id, "MODERATOR_ROLE_ID")
        moderator_role = message.guild.get_role(moderator_role_id) if moderator_role_id else None
        mod_ping = moderator_role.mention if moderator_role else f"Moderators (Role ID {moderator_role_id} not found)"

        current_timestamp_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        action_taken_message = ""
        model_used = get_guild_config(guild_id, "AI_MODEL", DEFAULT_VERTEX_AI_MODEL)

        notification_embed = discord.Embed(
            title="🚨 Rule Violation Detected 🚨",
            description=f"AI analysis detected a violation of server rules.",
            color=discord.Color.red()
        )
        notification_embed.add_field(name="User", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
        notification_embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        notification_embed.add_field(name="Rule Violated", value=f"**Rule {rule_violated}**", inline=True)
        notification_embed.add_field(name="AI Suggested Action", value=f"`{action}`", inline=True)
        notification_embed.add_field(name="AI Reasoning", value=f"_{reasoning}_", inline=False)
        notification_embed.add_field(name="Message Link", value=f"[Jump to Message]({message.jump_url})", inline=False)
        msg_content = message.content if message.content else "*No text content*"
        notification_embed.add_field(name="Message Content", value=msg_content[:1024], inline=False)
        if message.attachments:
            attachment_info = []
            for i, attachment in enumerate(message.attachments):
                attachment_info.append(f"{i+1}. {attachment.filename} ({attachment.content_type})")
            attachment_text = "\n".join(attachment_info)
            notification_embed.add_field(name="Attachments", value=attachment_text[:1024], inline=False)
        notification_embed.set_footer(text=f"AI Model: {model_used}. Learnhelp AI Moderation.")
        notification_embed.timestamp = discord.utils.utcnow()

        if test_mode_enabled:
            action_taken_message = f"Action Taken: **TEST MODE - No action performed.** (AI suggested `{action}`)"
            notification_embed.color = discord.Color.light_grey()
        else:
            try:
                if action == "GLOBAL_BAN":
                    action_taken_message = f"Action Taken: User **GLOBALLY BANNED** and message deleted."
                    notification_embed.color = discord.Color.dark_red()
                    try:
                        await message.delete()
                    except discord.NotFound: print("Message already deleted before global banning.")
                    except discord.Forbidden:
                        print(f"WARNING: Missing permissions to delete message before global banning user {message.author}.")
                        action_taken_message += " (Failed to delete message - check permissions)"

                    ban_reason = f"AI Mod: Severe Universal Violation (Rule {rule_violated}). Reason: {reasoning}"

                    if user_id not in GLOBAL_BANS:
                        GLOBAL_BANS.append(user_id)
                        await save_global_bans()
                        print(f"[MODERATION] Added user {message.author} ({user_id}) to global ban list.")
                    else:
                        print(f"[MODERATION] User {message.author} ({user_id}) is already on the global ban list.")
                        action_taken_message += " (User already on global ban list)"

                    try:
                        await message.guild.ban(message.author, reason=ban_reason, delete_message_days=1)
                        print(f"[MODERATION] BANNED user {message.author} from current guild {message.guild.name} for global ban.")
                    except discord.Forbidden:
                        print(f"WARNING: Missing permissions to ban user {message.author} from current guild {message.guild.name} during global ban.")
                        action_taken_message += " (Failed to ban from current guild - check permissions)"
                    except Exception as e:
                        print(f"Error banning user {message.author} from current guild {message.guild.name} during global ban: {e}")
                        action_taken_message += f" (Error banning from current guild: {e})"

                    banned_guilds = []
                    failed_guilds = []
                    for guild in self.bot.guilds:
                        if guild.id != message.guild.id:
                            try:
                                member = guild.get_member(user_id)
                                if member:
                                    await guild.ban(discord.Object(id=user_id), reason=ban_reason)
                                    banned_guilds.append(guild.name)
                                    print(f"Globally banned user {user_id} from guild {guild.name} ({guild.id}).")
                                else:
                                    print(f"User {user_id} not found in guild {guild.name} ({guild.id}), skipping ban.")
                            except discord.Forbidden:
                                failed_guilds.append(f"{guild.name} (Missing Permissions)")
                                print(f"WARNING: Missing permissions to ban user {user_id} from guild {guild.name} ({guild.id}) during global ban.")
                            except Exception as e:
                                failed_guilds.append(f"{guild.name} (Error: {e})")
                                print(f"Error banning user {user_id} from guild {guild.name} ({guild.id}) during global ban: {e}")

                    if banned_guilds:
                        action_taken_message += f"\nAlso banned from: {', '.join(banned_guilds)}"
                    if failed_guilds:
                        action_taken_message += f"\nFailed to ban from: {', '.join(failed_guilds)} (Check permissions)"

                    await add_user_infraction(guild_id, user_id, rule_violated, "GLOBAL_BAN", reasoning, current_timestamp_iso)

                    try:
                        dm_channel = await message.author.create_dm()
                        await dm_channel.send(
                            f"You have been globally banned for a severe universal violation by the AI moderation system.\n"
                            f"**Reason:** {reasoning}\n"
                            f"**Rule Violated:** {rule_violated}\n"
                            f"If you believe this was a mistake, you may appeal using the `/aimod appeal` command in any server where the bot is present."
                        )
                    except Exception as e:
                        print(f"Could not DM globally banned user {message.author}: {e}")

                elif action == "BAN":
                    action_taken_message = f"Action Taken: User **BANNED** and message deleted."
                    notification_embed.color = discord.Color.dark_red()
                    try:
                        await message.delete()
                    except discord.NotFound: print("Message already deleted before banning.")
                    except discord.Forbidden:
                        print(f"WARNING: Missing permissions to delete message before banning user {message.author}.")
                        action_taken_message += " (Failed to delete message - check permissions)"
                    ban_reason = f"AI Mod: Rule {rule_violated}. Reason: {reasoning}"
                    await message.guild.ban(message.author, reason=ban_reason, delete_message_days=1)
                    print(f"[MODERATION] BANNED user {message.author} for violating rule {rule_violated}.")
                    await add_user_infraction(guild_id, user_id, rule_violated, "BAN", reasoning, current_timestamp_iso)
                    try:
                        dm_channel = await message.author.create_dm()
                        await dm_channel.send(
                            f"You have been banned from **{message.guild.name}** by the AI moderation system.\n"
                            f"**Reason:** {reasoning}\n"
                            f"**Rule Violated:** {rule_violated}\n"
                            f"If you believe this was a mistake, you may appeal using the `/aimod appeal` command."
                        )
                    except Exception as e:
                        print(f"Could not DM banned user: {e}")
                elif action == "KICK":
                    action_taken_message = f"Action Taken: User **KICKED** and message deleted."
                    notification_embed.color = discord.Color.from_rgb(255, 127, 0)
                    try:
                        await message.delete()
                    except discord.NotFound: print("Message already deleted before kicking.")
                    except discord.Forbidden:
                        print(f"WARNING: Missing permissions to delete message before kicking user {message.author}.")
                        action_taken_message += " (Failed to delete message - check permissions)"
                    kick_reason = f"AI Mod: Rule {rule_violated}. Reason: {reasoning}"
                    await message.author.kick(reason=kick_reason)
                    print(f"[MODERATION] KICKED user {message.author} for violating rule {rule_violated}.")
                    await add_user_infraction(guild_id, user_id, rule_violated, "KICK", reasoning, current_timestamp_iso)
                    try:
                        dm_channel = await message.author.create_dm()
                        await dm_channel.send(
                            f"You have been kicked from **{message.guild.name}** by the AI moderation system.\n"
                            f"**Reason:** {reasoning}\n"
                            f"**Rule Violated:** {rule_violated}\n"
                            f"If you believe this was a mistake, you may appeal using the `/aimod appeal` command."
                        )
                    except Exception as e:
                        print(f"Could not DM kicked user: {e}")

                elif action.startswith("TIMEOUT"):
                    duration_seconds = 0
                    duration_readable = ""
                    if action == "TIMEOUT_SHORT":
                        duration_seconds = 10 * 60
                        duration_readable = "10 minutes"
                    elif action == "TIMEOUT_MEDIUM":
                        duration_seconds = 60 * 60
                        duration_readable = "1 hour"
                    elif action == "TIMEOUT_LONG":
                        duration_seconds = 24 * 60 * 60
                        duration_readable = "1 day"

                    if duration_seconds > 0:
                        action_taken_message = f"Action Taken: User **TIMED OUT for {duration_readable}** and message deleted."
                        notification_embed.color = discord.Color.blue()
                        try:
                            await message.delete()
                        except discord.NotFound: print(f"Message already deleted before timeout for {message.author}.")
                        except discord.Forbidden:
                            print(f"WARNING: Missing permissions to delete message before timeout for {message.author}.")
                            action_taken_message += " (Failed to delete message - check permissions)"

                        timeout_reason = f"AI Mod: Rule {rule_violated}. Reason: {reasoning}"
                        await message.author.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds), reason=timeout_reason)
                        print(f"[MODERATION] TIMED OUT user {message.author} for {duration_readable} for violating rule {rule_violated}.")
                        await add_user_infraction(guild_id, user_id, rule_violated, action, reasoning, current_timestamp_iso)
                    try:
                        dm_channel = await message.author.create_dm()
                        await dm_channel.send(
                            f"You have been timed out in **{message.guild.name}** for {duration_readable} by the AI moderation system.\n"
                            f"**Reason:** {reasoning}\n"
                            f"**Rule Violated:** {rule_violated}\n"
                            f"If you believe this was a mistake, you may appeal using the `/aimod appeal` command."
                        )
                    except Exception as e:
                        print(f"Could not DM timed out user: {e}")
                    else:
                        action_taken_message = "Action Taken: **Unknown timeout duration, notifying mods.**"
                        action = "NOTIFY_MODS"
                        print(f"[MODERATION] Unknown timeout duration for action {action}. Defaulting to NOTIFY_MODS.")

                elif action == "DELETE":
                    action_taken_message = f"Action Taken: Message **DELETED**."
                    await message.delete()
                    print(f"[MODERATION] DELETED message from {message.author} for violating rule {rule_violated}.")

                elif action == "WARN":
                    action_taken_message = f"Action Taken: Message **DELETED** (AI suggested WARN)."
                    notification_embed.color = discord.Color.orange()
                    await message.delete()
                    print(f"[MODERATION] DELETED message from {message.author} (AI suggested WARN for rule {rule_violated}).")
                    try:
                        dm_channel = await message.author.create_dm()
                        await dm_channel.send(
                            f"Your recent message in **{message.guild.name}** was removed for violating Rule **{rule_violated}**. "
                            f"Reason: _{reasoning}_. Please review the server rules. This is a formal warning.\n"
                            f"If you believe this was a mistake, you may appeal using the `/aimod appeal` command."
                        )
                        action_taken_message += " User notified via DM with warning."
                    except discord.Forbidden:
                        print(f"[MODERATION] Could not DM warning to {message.author} (DMs likely disabled).")
                        action_taken_message += " (Could not DM user for warning)."
                    except Exception as e:
                        print(f"[MODERATION] Error sending warning DM to {message.author}: {e}")
                        action_taken_message += " (Error sending warning DM)."
                    await add_user_infraction(guild_id, user_id, rule_violated, "WARN", reasoning, current_timestamp_iso)

                elif action == "NOTIFY_MODS":
                    action_taken_message = "Action Taken: **Moderator review requested.**"
                    notification_embed.color = discord.Color.gold()
                    print(f"[MODERATION] Notifying moderators about potential violation (Rule {rule_violated}) by {message.author}.")
                    if notify_mods_message:
                        notification_embed.add_field(name="Additional Mod Message", value=notify_mods_message, inline=False)

                elif action == "SUICIDAL":
                    action_taken_message = "Action Taken: **User DMed resources, relevant role notified.**"
                    notification_embed.title = "🚨 Suicidal Content Detected 🚨"
                    notification_embed.color = discord.Color.dark_purple()
                    notification_embed.description = "AI analysis detected content indicating potential suicidal ideation."
                    print(f"[MODERATION] SUICIDAL content detected from {message.author}. DMing resources and notifying role.")
                    try:
                        dm_channel = await message.author.create_dm()
                        await dm_channel.send(f"{SUICIDAL_HELP_RESOURCES}")
                        action_taken_message += " User successfully DMed."
                    except discord.Forbidden:
                        print(f"Could not DM suicidal help resources to {message.author} (DMs likely disabled).")
                        action_taken_message += " (Could not DM user - DMs disabled)."
                    except Exception as e:
                        print(f"Error sending suicidal help resources DM to {message.author}: {e}")
                        action_taken_message += f" (Error DMing user: {e})."

                else:
                    if ai_decision.get("violation"):
                         action_taken_message = "Action Taken: **None** (AI suggested IGNORE despite flagging violation - Review Recommended)."
                         notification_embed.color = discord.Color.light_grey()
                         print(f"[MODERATION] AI flagged violation ({rule_violated}) but suggested IGNORE for message by {message.author}. Notifying mods for review.")
                    else:
                         print(f"[MODERATION] No action taken for message by {message.author} (AI Action: {action}, Violation: False)")
                         return

            except discord.Forbidden as e:
                print(f"[MODERATION] ERROR: Missing Permissions to perform action '{action}' for rule {rule_violated}. Details: {e}")
                if moderator_role:
                    try:
                        await message.channel.send(
                            f"{mod_ping} **PERMISSION ERROR!** Could not perform action `{action}` on message by {message.author.mention} "
                            f"for violating Rule {rule_violated}. Please check bot permissions.\n"
                            f"Reasoning: _{reasoning}_\nMessage Link: {message.jump_url}\n"
                        )
                    except discord.Forbidden:
                        print(f"[MODERATION] FATAL: Bot lacks permission to send messages, even error notifications.")
            except discord.NotFound:
                 print(f"[MODERATION] Message {message.id} was likely already deleted when trying to perform action '{action}'.")
            except Exception as e:
                print(f"[MODERATION] An unexpected error occurred during action execution for message {message.id}: {e}")
                if moderator_role:
                     try:
                        await message.channel.send(
                            f"{mod_ping} **UNEXPECTED ERROR!** An error occurred while handling rule violation "
                            f"for {message.author.mention}. Please check bot logs.\n"
                            f"Rule: {rule_violated}, Action Attempted: {action}\nMessage Link: {message.jump_url}\n"
                        )
                     except discord.Forbidden:
                        print(f"FATAL: Bot lacks permission to send messages, even error notifications.")

        log_channel_id = get_guild_config(message.guild.id, "MOD_LOG_CHANNEL_ID")
        log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
        if not log_channel:
            print(f"[MODERATION] ERROR: Moderation log channel (ID: {log_channel_id}) not found or not configured. Defaulting to message channel.")
            log_channel = message.channel
            if not log_channel:
                print(f"[MODERATION] ERROR: Could not find even the original message channel {message.channel.id} to send notification.")
                return

        if action == "SUICIDAL":
            suicidal_role_id = get_guild_config(message.guild.id, "SUICIDAL_PING_ROLE_ID")
            suicidal_role = message.guild.get_role(suicidal_role_id) if suicidal_role_id else None
            ping_target = suicidal_role.mention if suicidal_role else f"Role ID {suicidal_role_id} (Suicidal Content)"
            if not suicidal_role:
                print(f"[MODERATION] ERROR: Suicidal ping role ID {suicidal_role_id} not found.")
            final_message = f"{ping_target}\n{action_taken_message}"
            await log_channel.send(content=final_message, embed=notification_embed)
        elif moderator_role:
            final_message = f"{mod_ping}\n{action_taken_message}"
            await log_channel.send(content=final_message, embed=notification_embed)
        else:
            print(f"[MODERATION] ERROR: Moderator role ID {moderator_role_id} not found for action {action}.")

    def is_globally_banned(self, user_id: int) -> bool:
        """Checks if a user ID is in the global ban list."""
        return user_id in GLOBAL_BANS

    @commands.Cog.listener(name="on_member_join")
    async def member_join_listener(self, member: discord.Member):
        """Checks if a joining member is globally banned and bans them if so."""
        print(f"on_member_join triggered for user: {member} ({member.id}) in guild: {member.guild.name} ({member.guild.id})")
        if self.is_globally_banned(member.id):
            print(f"User {member} ({member.id}) is globally banned. Banning from guild {member.guild.name} ({member.guild.id}).")
            try:
                ban_reason = "Globally banned for severe universal violation."
                await member.guild.ban(member, reason=ban_reason)
                print(f"Successfully banned globally banned user {member} ({member.id}) from guild {member.guild.name}.")
                try:
                    dm_channel = await member.create_dm()
                    await dm_channel.send(f"You have been globally banned for a severe universal violation and have been banned from **{member.guild.name}**.")
                except Exception as e:
                    print(f"Could not DM globally banned user {member}: {e}")

                log_channel_id = get_guild_config(member.guild.id, "MOD_LOG_CHANNEL_ID")
                log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
                if log_channel:
                    embed = discord.Embed(
                        title="🚨 Global Ban Enforcement 🚨",
                        description=f"Globally banned user attempted to join.",
                        color=discord.Color.dark_red()
                    )
                    embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
                    embed.add_field(name="Action", value="Automatically Banned (Global Ban List)", inline=False)
                    embed.add_field(name="Reason", value=ban_reason, inline=False)
                    embed.timestamp = discord.utils.utcnow()
                    try:
                        await log_channel.send(embed=embed)
                    except discord.Forbidden:
                        print(f"WARNING: Missing permissions to send global ban enforcement log to channel {log_channel.id} in guild {member.guild.id}.")
                    except Exception as e:
                        print(f"Error sending global ban enforcement log: {e}")

            except discord.Forbidden:
                print(f"WARNING: Missing permissions to ban user {member} ({member.id}) from guild {member.guild.name} ({member.guild.id}).")
                log_channel_id = get_guild_config(member.guild.id, "MOD_LOG_CHANNEL_ID")
                log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
                if log_channel:
                     mod_role_id = get_guild_config(member.guild.id, "MODERATOR_ROLE_ID")
                     mod_ping = f"<@&{mod_role_id}>" if mod_role_id else "Moderators"
                     try:
                         await log_channel.send(f"{mod_ping} **PERMISSION ERROR!** Could not ban globally banned user {member.mention} (`{member.id}`) from this server. Please check bot permissions.")
                     except discord.Forbidden:
                         print(f"FATAL: Bot lacks permission to send messages, even permission errors.")
            except Exception as e:
                print(f"An unexpected error occurred during global ban enforcement for user {member} ({member.id}) in guild {member.guild.name}: {e}")
                log_channel_id = get_guild_config(member.guild.id, "MOD_LOG_CHANNEL_ID")
                log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
                if log_channel:
                     mod_role_id = get_guild_config(member.guild.id, "MODERATOR_ROLE_ID")
                     mod_ping = f"<@&{mod_role_id}>" if mod_role_id else "Moderators"
                     try:
                         await log_channel.send(f"{mod_ping} **UNEXPECTED ERROR!** An error occurred while enforcing global ban for user {member.mention} (`{member.id}`). Please check bot logs.")
                     except discord.Forbidden:
                         print(f"FATAL: Bot lacks permission to send messages, even error notifications.")
            return

    @commands.Cog.listener(name="on_message")
    async def message_listener(self, message: discord.Message):
        """Listens to messages and triggers moderation checks."""
        print(f"on_message triggered for message ID: {message.id}")
        if message.author.bot:
            print(f"Ignoring message {message.id} from bot.")
            return
        if not message.content and not message.attachments:
             print(f"Ignoring message {message.id} with no content or attachments.")
             return
        if not message.guild:
            print(f"Ignoring message {message.id} from DM.")
            return
        if not get_guild_config(message.guild.id, "ENABLED", True):
            print(f"Moderation disabled for guild {message.guild.id}. Ignoring message {message.id}.")
            return
        if self.is_globally_banned(message.author.id):
            print(f"Globally banned user {message.author} ({message.author.id}) sent a message in guild {message.guild.name}. Attempting to ban.")
            try:
                 ban_reason = "Globally banned user sent message."
                 await message.guild.ban(message.author, reason=ban_reason, delete_message_days=1)
                 print(f"Successfully banned globally banned user {message.author} from guild {message.guild.name} after they sent a message.")
            except discord.Forbidden:
                 print(f"WARNING: Missing permissions to ban globally banned user {message.author} ({message.author.id}) from guild {message.guild.name} after they sent a message.")
                 log_channel_id = get_guild_config(message.guild.id, "MOD_LOG_CHANNEL_ID")
                 log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
                 if log_channel:
                      mod_role_id = get_guild_config(message.guild.id, "MODERATOR_ROLE_ID")
                      mod_ping = f"<@&{mod_role_id}>" if mod_role_id else "Moderators"
                      try:
                          await log_channel.send(f"{mod_ping} **PERMISSION ERROR!** Globally banned user {message.author.mention} (`{message.author.id}`) sent a message but could not be banned from this server. Please check bot permissions.")
                      except discord.Forbidden:
                          print(f"FATAL: Bot lacks permission to send messages, even error notifications.")
            except Exception as e:
                 print(f"An unexpected error occurred when banning globally banned user {message.author} ({message.author.id}) after they sent a message: {e}")
                 log_channel_id = get_guild_config(message.guild.id, "MOD_LOG_CHANNEL_ID")
                 log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
                 if log_channel:
                      mod_role_id = get_guild_config(message.guild.id, "MODERATOR_ROLE_ID")
                      mod_ping = f"<@&{mod_role_id}>" if mod_role_id else "Moderators"
                      try:
                          await log_channel.send(f"{mod_ping} **UNEXPECTED ERROR!** An error occurred while banning globally banned user {message.author.mention} (`{message.author.id}`) after they sent a message. Please check bot logs.")
                      except discord.Forbidden:
                          print(f"FATAL: Bot lacks permission to send messages, even error notifications.")
            return

        message_content = message.content
        image_data_list = []
        if message.attachments:
            for attachment in message.attachments:
                mime_type, image_bytes, attachment_type = await self.media_processor.process_attachment(attachment)
                if mime_type and image_bytes and attachment_type:
                    image_data_list.append((mime_type, image_bytes, attachment_type, attachment.filename))
                    print(f"Processed attachment: {attachment.filename} as {attachment_type}")

            if image_data_list:
                print(f"Processed {len(image_data_list)} attachments for message {message.id}")

        if not message_content and not image_data_list:
            print(f"Ignoring message {message.id} with no content or valid attachments.")
            return

        if not self.genai_client:
             print(f"Skipping AI analysis for message {message.id}: Vertex AI Client is not available.")
             return

        infractions = get_user_infraction_history(message.guild.id, message.author.id)
        history_summary_parts = []
        if infractions:
            for infr in infractions:
                history_summary_parts.append(f"- Action: {infr.get('action_taken', 'N/A')} for Rule {infr.get('rule_violated', 'N/A')} on {infr.get('timestamp', 'N/A')[:10]}. Reason: {infr.get('reasoning', 'N/A')[:50]}...")
        user_history_summary = "\n".join(history_summary_parts) if history_summary_parts else "No prior infractions recorded."

        max_history_len = 500
        if len(user_history_summary) > max_history_len:
            user_history_summary = user_history_summary[:max_history_len-3] + "..."

        print(f"Analyzing message {message.id} from {message.author} in #{message.channel.name} with history...")
        if image_data_list:
            attachment_types = [data[2] for data in image_data_list]
            print(f"Including {len(image_data_list)} attachments in analysis: {', '.join(attachment_types)}")
        ai_decision = await self.query_vertex_ai(message, message_content, user_history_summary, image_data_list)

        if not ai_decision:
            print(f"Failed to get valid AI decision for message {message.id}.")
            self.last_ai_decisions.append({
                "message_id": message.id,
                "author_name": str(message.author),
                "author_id": message.author.id,
                "message_content_snippet": message.content[:100] + "..." if len(message.content) > 100 else message.content,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "ai_decision": {"error": "Failed to get valid AI decision", "raw_response": None}
            })
            return

        self.last_ai_decisions.append({
            "message_id": message.id,
            "author_name": str(message.author),
            "author_id": message.author.id,
            "message_content_snippet": message.content[:100] + "..." if len(message.content) > 100 else message.content,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "ai_decision": ai_decision
        })

        if ai_decision.get("violation"):
            notify_mods_message = ai_decision.get("notify_mods_message") if ai_decision.get("action") == "NOTIFY_MODS" else None
            await self.handle_violation(message, ai_decision, notify_mods_message)
        else:
            print(f"AI analysis complete for message {message.id}. No violation detected.")

    @debug_subgroup.command(name="testmode", description="Enable or disable AI moderation test mode for this guild (admin only).")
    @app_commands.describe(enabled="Enable test mode (true/false)")
    @app_commands.checks.has_permissions(administrator=True)
    async def aidebug_testmode(self, interaction: discord.Interaction, enabled: bool):
        """Enables or disables AI moderation test mode."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        await set_guild_config(interaction.guild.id, "TEST_MODE_ENABLED", enabled)
        await interaction.response.send_message(f"AI moderation test mode is now {'enabled' if enabled else 'disabled'} for this guild.", ephemeral=False)

    @debug_subgroup.command(name="last_decisions", description="View the last 5 AI moderation decisions (admin only).")
    @app_commands.checks.has_permissions(administrator=True)
    async def aidebug_last_decisions(self, interaction: discord.Interaction):
        if not self.last_ai_decisions:
            await interaction.response.send_message("No AI decisions have been recorded yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Last 5 AI Moderation Decisions",
            color=discord.Color.purple()
        )
        embed.timestamp = discord.utils.utcnow()

        for i, record in enumerate(reversed(list(self.last_ai_decisions))):
            decision_info = record.get("ai_decision", {})
            violation = decision_info.get("violation", "N/A")
            rule_violated = decision_info.get("rule_violated", "N/A")
            reasoning = decision_info.get("reasoning", "N/A")
            action = decision_info.get("action", "N/A")
            error_msg = decision_info.get("error")

            field_value = (
                f"**Author:** {record.get('author_name', 'N/A')} ({record.get('author_id', 'N/A')})\n"
                f"**Message ID:** {record.get('message_id', 'N/A')}\n"
                f"**Content Snippet:** ```{record.get('message_content_snippet', 'N/A')}```\n"
                f"**Timestamp:** {record.get('timestamp', 'N/A')[:19].replace('T', ' ')}\n"
            )
            if error_msg:
                field_value += f"**Status:** <font color='red'>Error during processing: {error_msg}</font>\n"
            else:
                field_value += (
                    f"**Violation:** {violation}\n"
                    f"**Rule Violated:** {rule_violated}\n"
                    f"**Action:** {action}\n"
                    f"**Reasoning:** ```{reasoning}```\n"
                )

            if len(field_value) > 1024:
                field_value = field_value[:1020] + "..."

            embed.add_field(
                name=f"Decision #{len(self.last_ai_decisions) - i}",
                value=field_value,
                inline=False
            )
            if len(embed.fields) >= 5:
                break

        if not embed.fields:
             await interaction.response.send_message("Could not format AI decisions.", ephemeral=True)
             return

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @aidebug_last_decisions.error
    async def aidebug_last_decisions_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You must be an administrator to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)
            print(f"Error in aidebug_last_decisions command: {error}")

    @appeals_subgroup.command(name="appeal", description="Submit an appeal for a recent moderation action.")
    @app_commands.describe(reason="The reason for your appeal.")
    async def submit_appeal(self, interaction: discord.Interaction, reason: str):
        user_id = interaction.user.id
        # Check if user is globally banned
        if user_id in GLOBAL_BANS:
            try:
                dm_channel = await interaction.user.create_dm()
                await dm_channel.send(
                    f"You are globally banned. To appeal, please email help@learnhelp with your User ID ({user_id}) and your reasoning for the appeal.\n\nReason you provided: {reason}"
                )
                await interaction.response.send_message(
                    "You are globally banned. Please check your DMs for instructions on how to appeal.", ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"You are globally banned. Please email help@learnhelp with your User ID ({user_id}) and your reasoning for the appeal. (Could not DM you: {e})",
                    ephemeral=True
                )
            return
        # Normal appeal process for non-globally banned users
        last_infraction = None

        for key, infractions in USER_INFRACTIONS.items():
            if f"_{user_id}" in key:
                guild_id_str = key.split('_')[0]
                for infraction in reversed(infractions):
                    if infraction.get("action_taken") in ["BAN", "GLOBAL_BAN"] or "TIMEOUT" in infraction.get("action_taken", ""):
                        last_infraction = infraction
                        last_infraction['guild_id'] = int(guild_id_str)
                        break
                if last_infraction:
                    break
        
        if not last_infraction:
            await interaction.response.send_message("No recent appealable moderation action found for your account.", ephemeral=True)
            return

        appeal_id = str(uuid.uuid4())
        appeal_data = {
            "appeal_id": appeal_id,
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending",
            "original_infraction": last_infraction
        }

        APPEALS[appeal_id] = appeal_data
        await save_appeals()

        admin_user_id = 1141746562922459136
        admin_user = self.bot.get_user(admin_user_id)

        if not admin_user:
            print(f"CRITICAL: Could not find admin user with ID {admin_user_id} to send appeal.")
            await interaction.response.send_message("Your appeal has been submitted, but there was an error notifying the admin.", ephemeral=True)
            return
        
        guild_id = last_infraction['guild_id']
        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else f"Guild ID: {guild_id}"

        embed = discord.Embed(
            title="New Moderation Appeal",
            description=f"An appeal has been submitted by a user.",
            color=discord.Color.yellow()
        )
        embed.add_field(name="User", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="Guild", value=guild_name, inline=False)
        embed.add_field(name="Reason for Appeal", value=reason, inline=False)
        embed.add_field(name="Original Action", value=f"`{last_infraction.get('action_taken')}`", inline=True)
        embed.add_field(name="Original Reason", value=f"_{last_infraction.get('reasoning')}_", inline=True)
        embed.set_footer(text=f"Appeal ID: {appeal_id}")
        embed.timestamp = discord.utils.utcnow()

        try:
            await admin_user.send(embed=embed, view=AppealActions(appeal_id=appeal_id))
            await interaction.response.send_message("Your appeal has been successfully submitted for review.", ephemeral=True)
        except discord.Forbidden:
            print(f"CRITICAL: Could not DM admin user {admin_user_id}. They may have DMs disabled.")
            await interaction.response.send_message("Your appeal has been submitted, but there was an error notifying the admin.", ephemeral=True)
        except Exception as e:
            print(f"CRITICAL: An unexpected error occurred when sending appeal to admin: {e}")
            await interaction.response.send_message("Your appeal has been submitted, but an unexpected error occurred.", ephemeral=True)

    @commands.Cog.listener(name="on_interaction")
    async def on_appeal_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("appeal_"):
            return
        
        admin_user_id = 1141746562922459136
        if interaction.user.id != admin_user_id:
            await interaction.response.send_message("You are not authorized to handle this appeal.", ephemeral=True)
            return

        parts = custom_id.split('_')
        action = parts[1]
        appeal_id = "_".join(parts[2:])

        appeal_data = APPEALS.get(appeal_id)
        if not appeal_data:
            await interaction.response.send_message("This appeal could not be found. It might be outdated.", ephemeral=True)
            return
        
        if appeal_data["status"] != "pending":
            await interaction.response.send_message(f"This appeal has already been {appeal_data['status']}.", ephemeral=True)
            return

        original_infraction = appeal_data["original_infraction"]
        user_id = appeal_data["user_id"]
        guild_id = original_infraction["guild_id"]
        guild = self.bot.get_guild(guild_id)
        user_to_notify = self.bot.get_user(user_id)

        original_message = interaction.message
        new_embed = original_message.embeds[0]
        new_embed.color = discord.Color.green() if action == "accept" else discord.Color.red()

        if action == "accept":
            appeal_data["status"] = "accepted"
            new_embed.title = "Appeal Accepted"
            
            if not guild:
                print(f"Could not find guild {guild_id} to revert action for appeal {appeal_id}")
                if user_to_notify:
                    try:
                        await user_to_notify.send(f"Your appeal ({appeal_id}) was accepted, but we could not find the original server to revert the action. Please contact an admin.")
                    except discord.Forbidden:
                        print(f"Could not DM user {user_id} about accepted appeal with missing guild.")
            else:
                action_reverted = False
                original_action = original_infraction.get("action_taken")
                if original_action == "BAN":
                    try:
                        await guild.unban(discord.Object(id=user_id), reason=f"Appeal {appeal_id} accepted.")
                        action_reverted = True
                    except Exception as e:
                        print(f"Failed to unban user {user_id} in guild {guild_id} for appeal {appeal_id}: {e}")
                elif original_action == "GLOBAL_BAN":
                    if user_id in GLOBAL_BANS:
                        GLOBAL_BANS.remove(user_id)
                        await save_global_bans()
                    try:
                        await guild.unban(discord.Object(id=user_id), reason=f"Appeal {appeal_id} accepted.")
                        action_reverted = True
                    except Exception as e:
                        print(f"Failed to unban user {user_id} in guild {guild_id} for global ban appeal {appeal_id}: {e}")
                elif "TIMEOUT" in original_action:
                    try:
                        member = await guild.fetch_member(user_id)
                        await member.timeout(None, reason=f"Appeal {appeal_id} accepted.")
                        action_reverted = True
                    except discord.NotFound:
                         print(f"User {user_id} not found in guild {guild_id} to remove timeout for appeal {appeal_id}")
                    except Exception as e:
                        print(f"Failed to remove timeout for user {user_id} in guild {guild_id} for appeal {appeal_id}: {e}")

                if user_to_notify:
                    try:
                        if action_reverted:
                            await user_to_notify.send(f"Your appeal regarding the action in **{guild.name}** has been **accepted**, and the action has been reverted.")
                        else:
                            await user_to_notify.send(f"Your appeal regarding the action in **{guild.name}** has been **accepted**, but we failed to automatically revert the action. Please contact an admin.")
                    except discord.Forbidden:
                        print(f"Could not DM user {user_id} about accepted appeal.")

        else:
            appeal_data["status"] = "denied"
            new_embed.title = "Appeal Denied"
            if user_to_notify:
                try:
                    await user_to_notify.send(f"Your appeal has been **denied**.")
                except discord.Forbidden:
                    print(f"Could not DM user {user_id} about denied appeal.")

        await save_appeals()
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Accepted" if action == "accept" else "Accept", style=discord.ButtonStyle.success, disabled=True))
        view.add_item(discord.ui.Button(label="Denied" if action == "deny" else "Deny", style=discord.ButtonStyle.danger, disabled=True))
        
        await interaction.response.edit_message(embed=new_embed, view=view)

    @app_commands.command(name="pull_rules", description="Update the AI moderation rules for this guild from the rules channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def pull_rules(self, interaction: discord.Interaction):
        """
        Locates the rules channel in the guild, fetches its content, and updates the per-guild rules for AI moderation.
        """
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return
        rules_channel = None
        for channel in guild.text_channels:
            if channel.name.lower() in ("rules", "server-rules", "rule", "guidelines"):
                rules_channel = channel
                break
        if not rules_channel:
            await interaction.response.send_message(
                "Could not find a rules channel (named 'rules', 'server-rules', or 'guidelines'). Please specify the channel name or create one.",
                ephemeral=True
            )
            return
        try:
            messages = [msg async for msg in rules_channel.history(limit=10, oldest_first=True)]
            rules_text = "\n\n".join(msg.content for msg in messages if msg.content.strip())
        except Exception as e:
            await interaction.response.send_message(f"Failed to fetch messages from the rules channel: {e}", ephemeral=True)
            return
        if not rules_text.strip():
            await interaction.response.send_message("The rules channel appears to be empty.", ephemeral=True)
            return
        try:
            await set_guild_config(guild.id, "SERVER_RULES", rules_text)
            await interaction.response.send_message("Successfully updated the AI moderation rules for this guild from the rules channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to update rules in config: {e}", ephemeral=True)
            return

    def get_server_rules(self, guild_id: int) -> str:
        return get_guild_config(guild_id, "SERVER_RULES", globals().get("SERVER_RULES", "No rules set."))

async def setup(bot: commands.Bot):
    """Loads the ModerationCog."""
    bot.add_view(AppealButton())
    await bot.add_cog(ModerationCog(bot))
    print("ModerationCog has been loaded.")

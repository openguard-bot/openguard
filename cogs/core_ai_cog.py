import json
import discord
from discord.ext import commands
from discord import app_commands
import collections
import datetime
import os

from lists import Owners, OwnersTuple
from .aimod_helpers.config_manager import (
    DEFAULT_VERTEX_AI_MODEL,
    GLOBAL_BANS,
    USER_INFRACTIONS,
    save_global_bans,
    save_user_infractions,
    get_guild_config_async,
    set_guild_config,
    is_channel_excluded,
    get_channel_rules,
)
from .aimod_helpers.utils import (
    truncate_text,
    get_user_infraction_history,
    add_user_infraction,
)
from .aimod_helpers.media_processor import MediaProcessor
from .aimod_helpers.system_prompt import SUICIDAL_HELP_RESOURCES, SYSTEM_PROMPT_TEMPLATE
from .aimod_helpers.litellm_config import get_litellm_client
from .aimod_helpers.ui import ActionConfirmationView
from database.operations import get_guild_api_key

DEV_AIMODTEST_USER_IDS = OwnersTuple
DEV_AIMODTEST_ENABLED = False


def is_dev_aimodtest_user(interaction: discord.Interaction) -> bool:
    return interaction.user.id in DEV_AIMODTEST_USER_IDS


class CoreAICog(commands.Cog, name="Core AI"):
    """
    The core of the AI moderation system. Handles message analysis, violation detection, and core moderation commands.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_ai_decisions = collections.deque(maxlen=5)
        self.media_processor = MediaProcessor()
        try:
            self.genai_client = get_litellm_client()
            print("CoreAICog: LiteLLM client initialized successfully.")
        except Exception as e:
            print(f"CoreAICog: Failed to initialize LiteLLM client: {e}")
            self.genai_client = None
        print("CoreAICog Initializing.")

    async def cog_load(self):
        print("CoreAICog cog_load started.")
        if not self.genai_client:
            try:
                self.genai_client = get_litellm_client()
                print("CoreAICog: LiteLLM client re-initialized on load.")
            except Exception as e:
                print(
                    f"CoreAICog: Failed to re-initialize LiteLLM client on load: {e}"
                )
        print("CoreAICog cog_load finished.")

        # Auto-ban any users already in servers who are on the global ban list
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.id in GLOBAL_BANS:
                    try:
                        ban_reason = "Globally banned for severe universal violation. (Auto-enforced on cog load)"
                        await guild.ban(member, reason=ban_reason)
                        print(
                            f"[GLOBAL BAN] Auto-banned {member} ({member.id}) from {guild.name} on cog load."
                        )
                        try:
                            dm_channel = await member.create_dm()
                            await dm_channel.send(
                                f"You have been globally banned for a severe universal violation and have been banned from **{guild.name}**."
                            )
                        except Exception as e:
                            print(f"Could not DM globally banned user {member}: {e}")
                        # Optionally log to mod log channel
                        log_channel_id = await get_guild_config_async(
                            guild.id, "ai_actions_log_channel_id"
                        )
                        log_channel = (
                            self.bot.get_channel(log_channel_id)
                            if log_channel_id
                            else None
                        )
                        if log_channel:
                            embed = discord.Embed(
                                title="🚨 Global Ban Enforcement 🚨",
                                description=f"Globally banned user was present and has been auto-banned.",
                                color=discord.Color.dark_red(),
                            )
                            embed.add_field(
                                name="User",
                                value=f"{member.mention} (`{member.id}`)",
                                inline=False,
                            )
                            embed.add_field(
                                name="Action",
                                value="Automatically Banned (Global Ban List)",
                                inline=False,
                            )
                            embed.add_field(
                                name="Reason", value=ban_reason, inline=False
                            )
                            embed.timestamp = discord.utils.utcnow()
                            try:
                                await log_channel.send(embed=embed)
                            except discord.Forbidden:
                                print(
                                    f"WARNING: Missing permissions to send global ban enforcement log to channel {log_channel.id} in guild {guild.id}."
                                )
                            except Exception as e:
                                print(f"Error sending global ban enforcement log: {e}")
                    except discord.Forbidden:
                        print(
                            f"WARNING: Missing permissions to ban user {member} ({member.id}) from guild {guild.name} during cog load."
                        )
                    except Exception as e:
                        print(
                            f"Error auto-banning globally banned user {member} ({member.id}) from guild {guild.name}: {e}"
                        )

    async def cog_unload(self):
        """
        Close any open connections when the cog is unloaded.
        """
        print("CoreAICog Unloaded.")

    @commands.hybrid_group(
        name="infractions", description="Manage user infractions."
    )
    async def infractions(self, ctx: commands.Context):
        """Manage user infractions."""
        await ctx.send_help(ctx.command)

    @commands.hybrid_group(
        name="globalban", description="Manage global bans."
    )
    async def globalban(self, ctx: commands.Context):
        """Manage global bans."""
        await ctx.send_help(ctx.command)

    @commands.hybrid_group(
        name="debug", description="Debugging commands for AI moderation."
    )
    async def debug(self, ctx: commands.Context):
        """Debugging commands for AI moderation."""
        await ctx.send_help(ctx.command)

    @globalban.command(
        name="manage", description="[DEVELOPER ONLY] Add or remove a user from the global ban list."
    )
    @app_commands.describe(
        action="Whether to add or remove the user.",
        userid="The ID of the user to manage.",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
        ]
    )
    @app_commands.check(is_dev_aimodtest_user)
    async def globalban_manage(
        self,
        ctx: commands.Context,
        action: app_commands.Choice[str],
        userid: str,
        globalbanreason: str,
    ):
        """Adds or removes a user from the global ban list."""

        try:
            user_id = int(userid)
        except ValueError:
            await ctx.reply(
                "Invalid user ID. Please provide a numerical user ID.", ephemeral=True
            )
            return

        global GLOBAL_BANS
        if action.value == "add":
            if user_id not in GLOBAL_BANS:
                GLOBAL_BANS.append(user_id)
                await save_global_bans()
                await ctx.reply(
                    f"User ID `{user_id}` added to the global ban list. Reason {globalbanreason}",
                    ephemeral=False,
                )
                print(
                    f"[MODERATION] User ID {user_id} added to global ban list by {ctx.author} ({ctx.author.id})."
                )
            else:
                await ctx.reply(
                    f"User ID `{user_id}` is already in the global ban list.",
                    ephemeral=True,
                )
        elif action.value == "remove":
            if user_id in GLOBAL_BANS:
                GLOBAL_BANS.remove(user_id)
                await save_global_bans()
                await ctx.reply(
                    f"User ID `{user_id}` removed from the global ban list. {globalbanreason}",
                    ephemeral=False,
                )
                print(
                    f"[MODERATION] User ID {user_id} removed from global ban list by {ctx.author} ({ctx.author.id})."
                )
            else:
                await ctx.reply(
                    f"User ID `{user_id}` is not in the global ban list.",
                    ephemeral=True,
                )
        else:
            await ctx.reply(
                "Invalid action. Please choose 'add' or 'remove'.", ephemeral=True
            )

    @commands.hybrid_command(name="stats", description="Show bot stats")
    async def stats(self, ctx: commands.Context):
        bot_user = self.bot.user
        if not bot_user:
            await ctx.reply(
                "Bot user not found.", ephemeral=True
            )
            return
        server_count = len(self.bot.guilds)
        embed = discord.Embed(
            title="AiMod Project Beta",
            description=f"servers being guarded: **{server_count}**",
            color=discord.Color.green(),
        )
        embed.set_thumbnail(url=bot_user.display_avatar.url)
        await ctx.reply(embed=embed, ephemeral=False)

    @app_commands.command(
        name="testlog", description="Send a test moderation log embed."
    )
    @app_commands.describe(
        language="The language code for the embed (e.g., 'en', 'es', 'ja')",
        action="The action to simulate ('timeout', 'kick', 'ban')",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Timeout", value="timeout"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Ban", value="ban"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def aimod_testlog(
        self,
        interaction: discord.Interaction,
        language: str,
        action: app_commands.Choice[str],
    ):
        """Sends a test moderation log embed."""
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
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
            jump_url="https://discord.com/channels/dummy/dummy/dummy",
        )

        notification_embed = discord.Embed(
            title="🚨 Rule Violation Detected (TEST) 🚨",
            description=f"AI analysis detected a violation of server rules.",
            color=discord.Color.red(),
        )
        notification_embed.add_field(
            name="User",
            value=f"{dummy_author.mention} (`{dummy_author.id}`)",
            inline=False,
        )
        notification_embed.add_field(
            name="Channel", value=interaction.channel.mention, inline=False
        )
        notification_embed.add_field(
            name="Rule Violated", value=f"**{simulated_rule}**", inline=True
        )
        notification_embed.add_field(
            name="AI Suggested Action", value=f"`{simulated_action}`", inline=True
        )
        notification_embed.add_field(
            name="AI Reasoning", value=f"_{simulated_reasoning}_", inline=False
        )
        notification_embed.add_field(
            name="Message Link",
            value=f"[Jump to Message]({dummy_message.jump_url})",
            inline=False,
        )
        notification_embed.add_field(
            name="Message Content", value=dummy_message.content, inline=False
        )

        if simulated_action == "BAN":
            notification_embed.color = discord.Color.dark_red()
        elif simulated_action == "KICK":
            notification_embed.color = discord.Color.from_rgb(255, 127, 0)
        elif simulated_action == "TIMEOUT":
            notification_embed.color = discord.Color.blue()

        footer_text = (
            f"Test Log | Language: {language} | Simulated Action: {simulated_action}"
        )
        notification_embed.set_footer(text=footer_text)
        notification_embed.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(
            embed=notification_embed, ephemeral=False
        )

    @infractions.command(
        name="view",
        description="View a user's AI moderation infraction history (mod/admin only).",
    )
    @app_commands.describe(user="The user to view infractions for")
    async def viewinfractions(
        self, ctx: commands.Context, user: discord.Member
    ):
        moderator_role_id = await get_guild_config_async(
            ctx.guild.id, "MODERATOR_ROLE_ID"
        )
        moderator_role = (
            ctx.guild.get_role(moderator_role_id) if moderator_role_id else None
        )

        has_permission = ctx.author.guild_permissions.administrator or (
            moderator_role and moderator_role in ctx.author.roles
        )

        if not has_permission:
            await ctx.reply(
                "You must be an administrator or have the moderator role to use this command.",
                ephemeral=True,
            )
            return

        infractions = get_user_infraction_history(ctx.guild.id, user.id)

        if not infractions:
            await ctx.reply(
                f"{user.mention} has no recorded infractions.", ephemeral=False
            )
            return

        embed = discord.Embed(
            title=f"Infraction History for {user.display_name}",
            description=f"User ID: {user.id}",
            color=discord.Color.orange(),
        )

        for i, infraction in enumerate(infractions, 1):
            timestamp = infraction.get("timestamp", "Unknown date")[:19].replace(
                "T", " "
            )
            rule = infraction.get("rule_violated", "Unknown rule")
            action = infraction.get("action_taken", "Unknown action")
            reason = infraction.get("reasoning", "No reason provided")
            reason = truncate_text(reason, 200)
            embed.add_field(
                name=f"Infraction #{i} - {timestamp}",
                value=f"**Rule Violated:** {rule}\n**Action Taken:** {action}\n**Reason:** {reason}",
                inline=False,
            )

        embed.set_footer(text=f"Total infractions: {len(infractions)}")
        embed.timestamp = discord.utils.utcnow()

        await ctx.reply(embed=embed, ephemeral=False)

    @infractions.command(
        name="clear",
        description="Clear a user's AI moderation infraction history (admin only).",
    )
    @app_commands.describe(user="The user to clear infractions for")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearinfractions(
        self, ctx: commands.Context, user: discord.Member
    ):
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply(
                "You must be an administrator to use this command.", ephemeral=True
            )
            return

        key = f"{ctx.guild.id}_{user.id}"
        infractions = USER_INFRACTIONS.get(key, [])

        if not infractions:
            await ctx.reply(
                f"{user.mention} has no recorded infractions to clear.", ephemeral=False
            )
            return

        USER_INFRACTIONS[key] = []
        await save_user_infractions()

        print(
            f"[MODERATION] Cleared {len(infractions)} infraction(s) for user {user} (ID: {user.id}) in guild {ctx.guild.name} (ID: {ctx.guild.id}) by {ctx.author} (ID: {ctx.author.id}) at {datetime.datetime.now(datetime.timezone.utc).isoformat()}.".replace(
                ")", ")\n"
            )
        )

        try:
            dm_channel = await user.create_dm()
            await dm_channel.send(
                f"Your infraction history in **{ctx.guild.name}** has been cleared by an administrator."
            )
        except discord.Forbidden:
            print(
                f"[MODERATION] Could not DM user {user} about infraction clearance (DMs disabled)."
            )
        except Exception as e:
            print(
                f"[MODERATION] Error DMing user {user} about infraction clearance: {e}"
            )

        await ctx.reply(
            f"Cleared {len(infractions)} infraction(s) for {user.mention}.",
            ephemeral=False,
        )

    async def query_vertex_ai(
        self,
        message: discord.Message,
        message_content: str,
        user_history: str,
        image_data_list=None,
    ):
        """
        Sends the message content, user history, and additional context to the LiteLLM API for analysis.
        """
        guild_id = message.guild.id
        user_id = message.author.id

        # Fetch guild's API key
        guild_api_key = await get_guild_api_key(guild_id)
        
        api_key = None
        auth_info = None
        model_used = await get_guild_config_async(
            guild_id, "AI_MODEL", DEFAULT_VERTEX_AI_MODEL
        )

        if guild_api_key:
            if guild_api_key.api_provider == "github_copilot":
                auth_info = guild_api_key.github_auth_info
            else:
                # For other providers, the key is the api_key
                api_key = guild_api_key.api_key
                # The model is still taken from the guild config, not overridden by the provider name
                model_used = await get_guild_config_async(
                    guild_id, "AI_MODEL", DEFAULT_VERTEX_AI_MODEL
                )

        # Check for channel-specific rules first, fallback to server rules
        channel_rules = await get_channel_rules(guild_id, message.channel.id)
        if channel_rules:
            rules_text = channel_rules
            print(f"Using channel-specific rules for channel {message.channel.name} (ID: {message.channel.id})")
        else:
            rules_text = await self.get_server_rules(guild_id)
            print(f"Using server default rules for channel {message.channel.name} (ID: {message.channel.id})")

        system_prompt_text = SYSTEM_PROMPT_TEMPLATE.format(rules_text=rules_text)

        user_role = "Member"
        if message.author.guild_permissions.administrator:
            user_role = "Admin"
        elif message.author.guild_permissions.manage_messages:
            user_role = "Moderator"
        elif message.guild.owner_id == message.author.id:
            user_role = "Server Owner"

        # Get user's top 10 roles, highest first
        user_role_list = [
            role.name
            for role in reversed(message.author.roles)
            if not role.is_default()
        ]
        top_10_roles = user_role_list[:10]
        user_roles_text = (
            ", ".join(top_10_roles) if top_10_roles else "User has no roles."
        )

        channel_category = (
            message.channel.category.name if message.channel.category else "No Category"
        )
        is_nsfw_channel = getattr(message.channel, "nsfw", False)

        replied_to_content = ""
        if message.reference and message.reference.message_id:
            try:
                replied_message = await message.channel.fetch_message(
                    message.reference.message_id
                )
                replied_to_content = f"Replied-to Message: {replied_message.author.display_name}: {replied_message.content[:200]}"
            except:
                replied_to_content = "Replied-to Message: [Could not fetch]"

        recent_history = []
        try:
            async for hist_message in message.channel.history(limit=4, before=message):
                if not hist_message.author.bot:
                    recent_history.append(
                        f"{hist_message.author.display_name}: {hist_message.content[:100]}"
                    )
        except:
            recent_history = ["[Could not fetch recent history]"]

        recent_history_text = (
            "\n".join(recent_history[:3])
            if recent_history
            else "No recent history available."
        )

        user_prompt = f"""
**Context Information:**
- User's Server Role: {user_role}
- User's Top 10 Roles: {user_roles_text}
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

        # Prepare messages for LiteLLM format
        messages = [
            {"role": "system", "content": system_prompt_text},
            {"role": "user", "content": user_prompt},
        ]

        # Handle image attachments for LiteLLM
        if image_data_list:
            # For now, we'll add image descriptions to the user message
            # LiteLLM/OpenRouter vision support may vary by model
            image_descriptions = []
            for mime_type, image_bytes, attachment_type, filename in image_data_list:
                image_descriptions.append(
                    f"[{attachment_type.upper()} ATTACHMENT: {filename}]"
                )
                print(f"Added {attachment_type} attachment to AI analysis: {filename}")

            if image_descriptions:
                messages[-1]["content"] += "\n\nAttachments:\n" + "\n".join(
                    image_descriptions
                )

        try:
            response = await self.genai_client.generate_content(
                model=model_used,
                messages=messages,
                api_key=api_key,
                auth_info=auth_info,
                temperature=0.2,
                max_tokens=4096,
            )

            ai_response_text = response.text

            if not ai_response_text:
                print("Error: Empty response from LiteLLM API.")
                return None

            try:
                json_start_index = ai_response_text.find("{")
                if json_start_index == -1:
                    print(
                        "Error: Could not find the start of the JSON object in AI response."
                    )
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
                    print(
                        f"Error: AI response missing required keys. Got: {ai_decision}"
                    )
                    return None

                print(f"AI Decision: {ai_decision}")
                return ai_decision

            except json.JSONDecodeError as e:
                print(f"Error parsing AI response as JSON: {e}")
                print(f"Raw AI response: {ai_response_text}")
                return None
        except Exception as e:
            print(f"Exception during LiteLLM API call: {e}")
            return None

    async def _execute_ban(
        self, message: discord.Message, reason: str, rule_violated: str
    ):
        """Helper function to execute a ban."""
        ban_reason = f"AI Mod: Rule {rule_violated}. Reason: {reason}"
        await message.guild.ban(message.author, reason=ban_reason, delete_message_days=1)
        print(
            f"[MODERATION] BANNED user {message.author} for violating rule {rule_violated}."
        )
        await add_user_infraction(
            message.guild.id,
            message.author.id,
            rule_violated,
            "BAN",
            reason,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        try:
            await message.author.send(
                f"You have been banned from **{message.guild.name}** by the AI moderation system.\n"
                f"**Reason:** {reason}\n"
                f"**Rule Violated:** {rule_violated}\n"
                f"If you believe this was a mistake, you may appeal using the `/appeal` command."
            )
        except Exception as e:
            print(f"Could not DM banned user: {e}")

    async def _execute_kick(
        self, message: discord.Message, reason: str, rule_violated: str
    ):
        """Helper function to execute a kick."""
        kick_reason = f"AI Mod: Rule {rule_violated}. Reason: {reason}"
        await message.author.kick(reason=kick_reason)
        print(
            f"[MODERATION] KICKED user {message.author} for violating rule {rule_violated}."
        )
        await add_user_infraction(
            message.guild.id,
            message.author.id,
            rule_violated,
            "KICK",
            reason,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        try:
            await message.author.send(
                f"You have been kicked from **{message.guild.name}** by the AI moderation system.\n"
                f"**Reason:** {reason}\n"
                f"**Rule Violated:** {rule_violated}\n"
                f"You may rejoin the server, but please review the rules."
            )
        except Exception as e:
            print(f"Could not DM kicked user: {e}")

    async def _execute_timeout(
        self,
        message: discord.Message,
        reason: str,
        rule_violated: str,
        action: str,
        duration_seconds: int,
        duration_readable: str,
    ):
        """Helper function to execute a timeout."""
        timeout_reason = f"AI Mod: Rule {rule_violated}. Reason: {reason}"
        await message.author.timeout(
            discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds),
            reason=timeout_reason,
        )
        print(
            f"[MODERATION] TIMED OUT user {message.author} for {duration_readable} for violating rule {rule_violated}."
        )
        await add_user_infraction(
            message.guild.id,
            message.author.id,
            rule_violated,
            action,
            reason,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        try:
            await message.author.send(
                f"You have been timed out in **{message.guild.name}** for {duration_readable} by the AI moderation system.\n"
                f"**Reason:** {reason}\n"
                f"**Rule Violated:** {rule_violated}\n"
                f"If you believe this was a mistake, you may appeal using the `/appeal` command."
            )
        except Exception as e:
            print(f"Could not DM timed out user: {e}")

    async def _execute_warn(
        self, message: discord.Message, reason: str, rule_violated: str
    ):
        """Helper function to execute a warn."""
        print(
            f"[MODERATION] DELETED message from {message.author} (AI suggested WARN for rule {rule_violated})."
        )
        try:
            await message.author.send(
                f"Your recent message in **{message.guild.name}** was removed for violating Rule **{rule_violated}**. "
                f"Reason: _{reason}_. Please review the server rules. This is a formal warning.\n"
                f"If you believe this was a mistake, you may appeal using the `/appeal` command."
            )
        except Exception as e:
            print(f"[MODERATION] Error sending warning DM to {message.author}: {e}")
        await add_user_infraction(
            message.guild.id,
            message.author.id,
            rule_violated,
            "WARN",
            reason,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    async def handle_violation(
        self,
        message: discord.Message,
        ai_decision: dict,
        notify_mods_message: str = None,
    ):
        guild_id = message.guild.id
        user_id = message.author.id

        # --- Configuration Fetching ---
        test_mode_enabled = await get_guild_config_async(
            guild_id, "TEST_MODE_ENABLED", False
        )
        confirmation_settings = await get_guild_config_async(
            guild_id, "ACTION_CONFIRMATION_SETTINGS", {}
        )
        ping_role_id = await get_guild_config_async(
            guild_id, "CONFIRMATION_PING_ROLE_ID"
        )
        moderator_role_id = await get_guild_config_async(guild_id, "MODERATOR_ROLE_ID")
        log_channel_id = await get_guild_config_async(
            guild_id, "ai_actions_log_channel_id"
        )
        model_used = await get_guild_config_async(
            guild_id, "AI_MODEL", DEFAULT_VERTEX_AI_MODEL
        )

        # --- Decision and Context Setup ---
        rule_violated = ai_decision.get("rule_violated", "Unknown")
        reasoning = ai_decision.get("reasoning", "No reasoning provided.")
        action = ai_decision.get("action", "NOTIFY_MODS").upper()

        # --- Build Base Notification Embed ---
        notification_embed = discord.Embed(
            title="🚨 Rule Violation Detected 🚨",
            description="AI analysis detected a violation of server rules.",
            color=discord.Color.red(),
        )
        # ... (rest of embed building is the same)
        notification_embed.add_field(
            name="User",
            value=f"{message.author.mention} (`{user_id}`)",
            inline=False,
        )
        notification_embed.add_field(
            name="Channel", value=message.channel.mention, inline=False
        )
        notification_embed.add_field(
            name="Rule Violated", value=f"**Rule {rule_violated}**", inline=True
        )
        notification_embed.add_field(
            name="AI Suggested Action", value=f"`{action}`", inline=True
        )
        notification_embed.add_field(name="AI Reasoning", value=f"_{reasoning}_", inline=False)
        notification_embed.add_field(
            name="Message Link",
            value=f"[Jump to Message]({message.jump_url})",
            inline=False,
        )
        msg_content = message.content if message.content else "*No text content*"
        notification_embed.add_field(
            name="Message Content", value=msg_content[:1024], inline=False
        )
        notification_embed.set_footer(text=f"AI Model: {model_used}")
        notification_embed.timestamp = discord.utils.utcnow()

        # --- Determine Action Mode (Manual vs. Automatic) ---
        confirmation_mode = confirmation_settings.get(action, "automatic")
        if test_mode_enabled:
            confirmation_mode = "manual"  # Force manual review in test mode

        # --- Define Action Logic ---
        action_function = None
        action_args = (message, reasoning, rule_violated)
        action_taken_message = ""

        if action == "BAN":
            action_function = self._execute_ban
            notification_embed.color = discord.Color.dark_red()
        elif action == "KICK":
            action_function = self._execute_kick
            notification_embed.color = discord.Color.orange()
        elif action.startswith("TIMEOUT"):
            duration_map = {
                "TIMEOUT_SHORT": (10 * 60, "10 minutes"),
                "TIMEOUT_MEDIUM": (60 * 60, "1 hour"),
                "TIMEOUT_LONG": (24 * 60 * 60, "1 day"),
            }
            duration_seconds, duration_readable = duration_map.get(action, (0, ""))
            if duration_seconds > 0:
                action_function = self._execute_timeout
                action_args = action_args + (action, duration_seconds, duration_readable)
                notification_embed.color = discord.Color.blue()
        elif action == "WARN":
            action_function = self._execute_warn
            notification_embed.color = discord.Color.yellow()

        # --- Execution ---
        log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None
        if not log_channel:
            log_channel = message.channel

        if confirmation_mode == "manual" and action_function:
            notification_embed.title = "Moderator Approval Required"
            notification_embed.description = "The AI has suggested an action that requires manual approval."
            notification_embed.color = discord.Color.gold()

            async def confirm_action():
                try:
                    await message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
                await action_function(*action_args)
                print(f"Moderator approved action '{action}' for user {user_id}")

            async def deny_action():
                print(f"Moderator denied action '{action}' for user {user_id}")

            view = ActionConfirmationView(
                action=action,
                author_id=user_id,
                confirm_callback=confirm_action,
                deny_callback=deny_action,
            )

            ping_role = message.guild.get_role(ping_role_id) if ping_role_id else None
            content = ping_role.mention if ping_role else "Moderators, please review."

            await log_channel.send(content=content, embed=notification_embed, view=view)

        elif action_function:  # Automatic mode
            try:
                await message.delete()
            except (discord.NotFound, discord.Forbidden) as e:
                print(f"Could not delete message before action '{action}': {e}")

            try:
                await action_function(*action_args)
                action_taken_message = f"Action Taken: **{action.replace('_', ' ').title()}** (Automatic)"
                notification_embed.add_field(name="Status", value=action_taken_message, inline=False)
                await log_channel.send(embed=notification_embed)
            except discord.Forbidden as e:
                print(f"Permission error executing {action}: {e}")
                # Notify mods of permission failure
                mod_ping = f"<@&{moderator_role_id}>" if moderator_role_id else "Moderators"
                await log_channel.send(
                    f"{mod_ping} **PERMISSION ERROR!** Could not perform action `{action}` on {message.author.mention}. Please check bot permissions.",
                    embed=notification_embed,
                )
            except Exception as e:
                print(f"Unexpected error executing {action}: {e}")
        else:  # Fallback for NOTIFY_MODS, SUICIDAL, etc.
            # This part handles actions that are always manual or have special handling
            if action == "NOTIFY_MODS":
                action_taken_message = "Action Taken: **Moderator review requested.**"
                notification_embed.color = discord.Color.gold()
            elif action == "SUICIDAL":
                action_taken_message = "Action Taken: **User DMed resources, relevant role notified.**"
                notification_embed.title = "🚨 Suicidal Content Detected 🚨"
                notification_embed.color = discord.Color.dark_purple()
                try:
                    await message.author.send(SUICIDAL_HELP_RESOURCES)
                except Exception as e:
                    print(f"Could not DM suicidal help resources: {e}")
            else:
                action_taken_message = "Action Taken: **None** (AI suggested IGNORE or unhandled action)."
                notification_embed.color = discord.Color.light_grey()

            notification_embed.add_field(name="Status", value=action_taken_message, inline=False)
            await log_channel.send(embed=notification_embed)

    def is_globally_banned(self, user_id: int) -> bool:
        """Checks if a user ID is in the global ban list."""
        return user_id in GLOBAL_BANS

    @commands.Cog.listener(name="on_member_join")
    async def member_join_listener(self, member: discord.Member):
        """Checks if a joining member is globally banned and bans them if so."""
        print(
            f"on_member_join triggered for user: {member} ({member.id}) in guild: {member.guild.name} ({member.guild.id})"
        )
        if self.is_globally_banned(member.id):
            print(
                f"User {member} ({member.id}) is globally banned. Banning from guild {member.guild.name} ({member.guild.id})."
            )
            try:
                ban_reason = "Globally banned for severe universal violation."
                await member.guild.ban(member, reason=ban_reason)
                print(
                    f"Successfully banned globally banned user {member} ({member.id}) from guild {member.guild.name}."
                )
                try:
                    dm_channel = await member.create_dm()
                    await dm_channel.send(
                        f"You have been globally banned for a severe universal violation and have been banned from **{member.guild.name}**."
                    )
                except Exception as e:
                    print(f"Could not DM globally banned user {member}: {e}")

                log_channel_id = await get_guild_config_async(
                    member.guild.id, "ai_actions_log_channel_id"
                )
                log_channel = (
                    self.bot.get_channel(log_channel_id) if log_channel_id else None
                )
                if log_channel:
                    embed = discord.Embed(
                        title="🚨 Global Ban Enforcement 🚨",
                        description=f"Globally banned user attempted to join.",
                        color=discord.Color.dark_red(),
                    )
                    embed.add_field(
                        name="User",
                        value=f"{member.mention} (`{member.id}`)",
                        inline=False,
                    )
                    embed.add_field(
                        name="Action",
                        value="Automatically Banned (Global Ban List)",
                        inline=False,
                    )
                    embed.add_field(name="Reason", value=ban_reason, inline=False)
                    embed.timestamp = discord.utils.utcnow()
                    try:
                        await log_channel.send(embed=embed)
                    except discord.Forbidden:
                        print(
                            f"WARNING: Missing permissions to send global ban enforcement log to channel {log_channel.id} in guild {member.guild.id}."
                        )
                    except Exception as e:
                        print(f"Error sending global ban enforcement log: {e}")

            except discord.Forbidden:
                print(
                    f"WARNING: Missing permissions to ban user {member} ({member.id}) from guild {member.guild.name} ({member.guild.id})."
                )
                log_channel_id = await get_guild_config_async(
                    member.guild.id, "ai_actions_log_channel_id"
                )
                log_channel = (
                    self.bot.get_channel(log_channel_id) if log_channel_id else None
                )
                if log_channel:
                    mod_role_id = await get_guild_config_async(
                        member.guild.id, "MODERATOR_ROLE_ID"
                    )
                    mod_ping = f"<@&{mod_role_id}>" if mod_role_id else "Moderators"
                    try:
                        await log_channel.send(
                            f"{mod_ping} **PERMISSION ERROR!** Could not ban globally banned user {member.mention} (`{member.id}`) from this server. Please check bot permissions."
                        )
                    except discord.Forbidden:
                        print(
                            f"FATAL: Bot lacks permission to send messages, even permission errors."
                        )
            except Exception as e:
                print(
                    f"An unexpected error occurred during global ban enforcement for user {member} ({member.id}) in guild {member.guild.name}: {e}"
                )
                log_channel_id = await get_guild_config_async(
                    member.guild.id, "ai_actions_log_channel_id"
                )
                log_channel = (
                    self.bot.get_channel(log_channel_id) if log_channel_id else None
                )
                if log_channel:
                    mod_role_id = await get_guild_config_async(
                        member.guild.id, "MODERATOR_ROLE_ID"
                    )
                    mod_ping = f"<@&{mod_role_id}>" if mod_role_id else "Moderators"
                    try:
                        await log_channel.send(
                            f"{mod_ping} **UNEXPECTED ERROR!** An error occurred while enforcing global ban for user {member.mention} (`{member.id}`). Please check bot logs."
                        )
                    except discord.Forbidden:
                        print(
                            f"FATAL: Bot lacks permission to send messages, even error notifications."
                        )
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
        if not await get_guild_config_async(message.guild.id, "ENABLED", True):
            print(
                f"Moderation disabled for guild {message.guild.id}. Ignoring message {message.id}."
            )
            return

        # Check if channel is excluded from AI moderation
        if await is_channel_excluded(message.guild.id, message.channel.id):
            print(
                f"Channel {message.channel.name} (ID: {message.channel.id}) is excluded from AI moderation. Ignoring message {message.id}."
            )
            return
        if self.is_globally_banned(message.author.id):
            print(
                f"Globally banned user {message.author} ({message.author.id}) sent a message in guild {message.guild.name}. Attempting to ban."
            )
            try:
                ban_reason = "Globally banned user sent message."
                await message.guild.ban(
                    message.author, reason=ban_reason, delete_message_days=1
                )
                print(
                    f"Successfully banned globally banned user {message.author} from guild {message.guild.name} after they sent a message."
                )
            except discord.Forbidden:
                print(
                    f"WARNING: Missing permissions to ban globally banned user {message.author} ({message.author.id}) from guild {message.guild.name} after they sent a message."
                )
                log_channel_id = await get_guild_config_async(
                    message.guild.id, "ai_actions_log_channel_id"
                )
                log_channel = (
                    self.bot.get_channel(log_channel_id) if log_channel_id else None
                )
                if log_channel:
                    mod_role_id = await get_guild_config_async(
                        message.guild.id, "MODERATOR_ROLE_ID"
                    )
                    mod_ping = f"<@&{mod_role_id}>" if mod_role_id else "Moderators"
                    try:
                        await log_channel.send(
                            f"{mod_ping} **PERMISSION ERROR!** Globally banned user {message.author.mention} (`{message.author.id}`) sent a message but could not be banned from this server. Please check bot permissions."
                        )
                    except discord.Forbidden:
                        print(
                            f"FATAL: Bot lacks permission to send messages, even error notifications."
                        )
            except Exception as e:
                print(
                    f"An unexpected error occurred when banning globally banned user {message.author} ({message.author.id}) after they sent a message: {e}"
                )
                log_channel_id = await get_guild_config_async(
                    message.guild.id, "ai_actions_log_channel_id"
                )
                log_channel = (
                    self.bot.get_channel(log_channel_id) if log_channel_id else None
                )
                if log_channel:
                    mod_role_id = await get_guild_config_async(
                        message.guild.id, "MODERATOR_ROLE_ID"
                    )
                    mod_ping = f"<@&{mod_role_id}>" if mod_role_id else "Moderators"
                    try:
                        await log_channel.send(
                            f"{mod_ping} **UNEXPECTED ERROR!** An error occurred while banning globally banned user {message.author.mention} (`{message.author.id}`) after they sent a message. Please check bot logs."
                        )
                    except discord.Forbidden:
                        print(
                            f"FATAL: Bot lacks permission to send messages, even error notifications."
                        )
            return

        message_content = message.content
        image_data_list = []
        if message.attachments:
            for attachment in message.attachments:
                mime_type, image_bytes, attachment_type = (
                    await self.media_processor.process_attachment(attachment)
                )
                if mime_type and image_bytes and attachment_type:
                    image_data_list.append(
                        (mime_type, image_bytes, attachment_type, attachment.filename)
                    )
                    print(
                        f"Processed attachment: {attachment.filename} as {attachment_type}"
                    )

            if image_data_list:
                print(
                    f"Processed {len(image_data_list)} attachments for message {message.id}"
                )

        if not message_content and not image_data_list:
            print(
                f"Ignoring message {message.id} with no content or valid attachments."
            )
            return

        if not self.genai_client:
            print(
                f"Skipping AI analysis for message {message.id}: LiteLLM Client is not available."
            )
            return

        infractions = get_user_infraction_history(message.guild.id, message.author.id)
        history_summary_parts = []
        if infractions:
            for infr in infractions:
                history_summary_parts.append(
                    f"- Action: {infr.get('action_taken', 'N/A')} for Rule {infr.get('rule_violated', 'N/A')} on {infr.get('timestamp', 'N/A')[:10]}. Reason: {infr.get('reasoning', 'N/A')[:50]}..."
                )
        user_history_summary = (
            "\n".join(history_summary_parts)
            if history_summary_parts
            else "No prior infractions recorded."
        )

        max_history_len = 500
        if len(user_history_summary) > max_history_len:
            user_history_summary = user_history_summary[: max_history_len - 3] + "..."

        print(
            f"Analyzing message {message.id} from {message.author} in #{message.channel.name} with history..."
        )
        if image_data_list:
            attachment_types = [data[2] for data in image_data_list]
            print(
                f"Including {len(image_data_list)} attachments in analysis: {', '.join(attachment_types)}"
            )
        ai_decision = await self.query_vertex_ai(
            message, message_content, user_history_summary, image_data_list
        )

        if not ai_decision:
            print(f"Failed to get valid AI decision for message {message.id}.")
            self.last_ai_decisions.append(
                {
                    "message_id": message.id,
                    "author_name": str(message.author),
                    "author_id": message.author.id,
                    "message_content_snippet": (
                        message.content[:100] + "..."
                        if len(message.content) > 100
                        else message.content
                    ),
                    "timestamp": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "ai_decision": {
                        "error": "Failed to get valid AI decision",
                        "raw_response": None,
                    },
                }
            )
            return

        self.last_ai_decisions.append(
            {
                "message_id": message.id,
                "author_name": str(message.author),
                "author_id": message.author.id,
                "message_content_snippet": (
                    message.content[:100] + "..."
                    if len(message.content) > 100
                    else message.content
                ),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "ai_decision": ai_decision,
            }
        )

        if ai_decision.get("violation"):
            notify_mods_message = (
                ai_decision.get("notify_mods_message")
                if ai_decision.get("action") == "NOTIFY_MODS"
                else None
            )
            await self.handle_violation(message, ai_decision, notify_mods_message)
        else:
            print(
                f"AI analysis complete for message {message.id}. No violation detected."
            )

    @debug.command(
        name="last_decisions",
        description="View the last 5 AI moderation decisions (admin only).",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def aidebug_last_decisions(self, ctx: commands.Context):
        if not self.last_ai_decisions:
            await ctx.reply(
                "No AI decisions have been recorded yet.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Last 5 AI Moderation Decisions", color=discord.Color.purple()
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
                inline=False,
            )
            if len(embed.fields) >= 5:
                break

        if not embed.fields:
            await ctx.reply(
                "Could not format AI decisions.", ephemeral=True
            )
            return

        await ctx.reply(embed=embed, ephemeral=True)

    @aidebug_last_decisions.error
    async def aidebug_last_decisions_error(
        self, ctx: commands.Context, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await ctx.reply(
                "You must be an administrator to use this command.", ephemeral=True
            )
        else:
            await ctx.reply(
                f"An error occurred: {error}", ephemeral=True
            )
            print(f"Error in aidebug_last_decisions command: {error}")

    async def get_server_rules(self, guild_id: int) -> str:
        return await get_guild_config_async(
            guild_id, "SERVER_RULES", "No rules set."
        )

async def setup(bot: commands.Bot):
    """Loads the CoreAICog."""
    await bot.add_cog(CoreAICog(bot))
    print("CoreAICog has been loaded.")
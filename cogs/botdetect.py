import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import List, Dict, Any, Optional

# Import database operations
from database.operations import (
    get_botdetect_config,
    set_botdetect_config,
    get_all_botdetect_config,
)

# Legacy configuration paths (kept for compatibility but not used)
BOTDETECT_CONFIG_DIR = "wdiscordbot-json-data"
BOTDETECT_CONFIG_PATH = "wdiscordbot-json-data/botdetect_config.json"

# Common scam bot keywords
DEFAULT_SCAM_KEYWORDS = [
    # Discord Nitro scams
    "free nitro",
    "discord nitro",
    "nitro gift",
    "nitro giveaway",
    "claim nitro",
    "get nitro",
    "discord.gift",
    "discordgift",
    "nitro for free",
    "free discord nitro",
    # Steam scams
    "free steam",
    "steam gift",
    "steam wallet",
    "steam card",
    "cs:go skins",
    "csgo skins",
    "free skins",
    "skin giveaway",
    "steam giveaway",
    "steamcommunity",
    "steam-community",
    # Cryptocurrency/investment scams
    "crypto giveaway",
    "bitcoin giveaway",
    "eth giveaway",
    "free crypto",
    "investment opportunity",
    "guaranteed profit",
    "double your money",
    "crypto airdrop",
    "nft giveaway",
    "free nft",
    # Phishing and malicious links
    "click here",
    "limited time",
    "expires soon",
    "claim now",
    "verify account",
    "account suspended",
    "urgent action required",
    "confirm identity",
    "security alert",
    "suspicious activity",
    # Generic scam phrases
    "congratulations you won",
    "you have been selected",
    "exclusive offer",
    "act fast",
    "don't miss out",
    "last chance",
    "winner announcement",
    "prize claim",
    "free money",
    "easy money",
    # Fake support/admin impersonation
    "discord support",
    "discord admin",
    "discord staff",
    "official discord",
    "discord team",
    "account verification",
    "verify your account",
    "discord security",
    # Suspicious domains (partial matches)
    "bit.ly",
    "tinyurl",
    "discord-nitro",
    "steam-community",
    "steamcommunlty",
    "steampowered",
]

# Legacy variables (now use database)
BOTDETECT_CONFIG = {}  # Deprecated - use database functions
CONFIG_LOCK = asyncio.Lock()


async def save_botdetect_config():
    """Legacy function - now a no-op since data is saved directly to database."""
    pass


async def get_guild_botdetect_config(guild_id: int) -> Dict[str, Any]:
    """Get bot detection configuration for a guild from database."""
    try:
        config = await get_all_botdetect_config(guild_id)

        # If no config exists, return default configuration
        if not config:
            default_config = {
                "enabled": False,
                "keywords": DEFAULT_SCAM_KEYWORDS.copy(),
                "action": "warn",
                "timeout_duration": 300,
                "log_channel": None,
                "whitelist_roles": [],
                "whitelist_users": [],
            }
            # Save default config to database
            for key, value in default_config.items():
                await set_botdetect_config(guild_id, key, value)
            return default_config

        # Convert database format to expected format
        result = {}
        for key, value in config.items():
            result[key] = value

        # Ensure all required keys exist with defaults
        defaults = {
            "enabled": False,
            "keywords": DEFAULT_SCAM_KEYWORDS.copy(),
            "action": "warn",
            "timeout_duration": 300,
            "log_channel": None,
            "whitelist_roles": [],
            "whitelist_users": [],
        }

        for key, default_value in defaults.items():
            if key not in result:
                result[key] = default_value
                await set_botdetect_config(guild_id, key, default_value)

        return result

    except Exception as e:
        print(f"Failed to get botdetect config for guild {guild_id}: {e}")
        # Return default config on error
        return {
            "enabled": False,
            "keywords": DEFAULT_SCAM_KEYWORDS.copy(),
            "action": "warn",
            "timeout_duration": 300,
            "log_channel": None,
            "whitelist_roles": [],
            "whitelist_users": [],
        }


async def set_guild_botdetect_config(guild_id: int, config: Dict[str, Any]):
    """Set bot detection configuration for a guild in database."""
    try:
        for key, value in config.items():
            await set_botdetect_config(guild_id, key, value)
    except Exception as e:
        print(f"Failed to set botdetect config for guild {guild_id}: {e}")


class BotDetectCog(commands.Cog):
    """
    A Discord Cog that detects potential bot messages based on configured keywords
    and takes specified actions against them.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("BotDetectCog initialized.")

    @commands.hybrid_group(name="botdetect", description="Bot detection commands.")
    async def botdetect(self, ctx: commands.Context):
        """Bot detection commands."""
        await ctx.send_help(ctx.command)

    @botdetect.command(
        name="config", description="Configure bot detection settings for this server."
    )
    @app_commands.describe(
        action="Action to take when bot is detected",
        keywords="Comma-separated list of keywords to detect (leave empty to view current)",
        enabled="Enable or disable bot detection",
        timeout_duration="Duration in seconds for timeout action (default: 300)",
        log_channel="Channel to log bot detection events",
        add_keyword="Add a single keyword to the list",
        remove_keyword="Remove a single keyword from the list",
        whitelist_role="Role to whitelist from bot detection",
        whitelist_user="User to whitelist from bot detection",
        remove_whitelist_role="Remove a role from whitelist",
        remove_whitelist_user="Remove a user from whitelist",
        load_default_keywords="Load default scam bot keywords (replaces current keywords)",
        clear_keywords="Clear all keywords from the list",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Warn (send warning message)", value="warn"),
            app_commands.Choice(name="Kick user", value="kick"),
            app_commands.Choice(name="Ban user", value="ban"),
            app_commands.Choice(name="Timeout user", value="timeout"),
            app_commands.Choice(name="Delete message only", value="delete"),
        ]
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def botdetect_config(
        self,
        ctx: commands.Context,
        action: Optional[app_commands.Choice[str]] = None,
        keywords: Optional[str] = None,
        enabled: Optional[bool] = None,
        timeout_duration: Optional[int] = None,
        log_channel: Optional[discord.TextChannel] = None,
        add_keyword: Optional[str] = None,
        remove_keyword: Optional[str] = None,
        whitelist_role: Optional[discord.Role] = None,
        whitelist_user: Optional[discord.Member] = None,
        remove_whitelist_role: Optional[discord.Role] = None,
        remove_whitelist_user: Optional[discord.Member] = None,
        load_default_keywords: Optional[bool] = None,
        clear_keywords: Optional[bool] = None,
    ):
        """Configure bot detection settings for the server."""

        if not ctx.guild:
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "This command can only be used in a server.", ephemeral=True
                )
            else:
                await ctx.send("This command can only be used in a server.")
            return

        guild_id = ctx.guild.id
        config = await get_guild_botdetect_config(guild_id)

        # If no parameters provided, show current configuration
        if all(
            param is None
            for param in [
                action,
                keywords,
                enabled,
                timeout_duration,
                log_channel,
                add_keyword,
                remove_keyword,
                whitelist_role,
                whitelist_user,
                remove_whitelist_role,
                remove_whitelist_user,
                load_default_keywords,
                clear_keywords,
            ]
        ):
            embed = discord.Embed(
                title="Bot Detection Configuration",
                description=f"Current settings for **{ctx.guild.name}**",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Status",
                value="🟢 Enabled" if config["enabled"] else "🔴 Disabled",
                inline=True,
            )

            embed.add_field(name="Action", value=config["action"].title(), inline=True)

            if config["action"] == "timeout":
                embed.add_field(
                    name="Timeout Duration",
                    value=f"{config['timeout_duration']} seconds",
                    inline=True,
                )

            embed.add_field(
                name="Keywords",
                value=(
                    ", ".join(config["keywords"])
                    if config["keywords"]
                    else "None configured"
                ),
                inline=False,
            )

            if config["log_channel"]:
                log_channel_obj = ctx.guild.get_channel(config["log_channel"])
                log_channel_name = (
                    log_channel_obj.mention if log_channel_obj else "Unknown Channel"
                )
            else:
                log_channel_name = "None"

            embed.add_field(name="Log Channel", value=log_channel_name, inline=True)

            # Show whitelisted roles
            if config["whitelist_roles"]:
                role_mentions = []
                for role_id in config["whitelist_roles"]:
                    role = ctx.guild.get_role(role_id)
                    if role:
                        role_mentions.append(role.mention)
                embed.add_field(
                    name="Whitelisted Roles",
                    value=", ".join(role_mentions) if role_mentions else "None",
                    inline=True,
                )

            # Show whitelisted users
            if config["whitelist_users"]:
                user_mentions = []
                for user_id in config["whitelist_users"]:
                    user = ctx.guild.get_member(user_id)
                    if user:
                        user_mentions.append(user.mention)
                embed.add_field(
                    name="Whitelisted Users",
                    value=", ".join(user_mentions) if user_mentions else "None",
                    inline=True,
                )

            if ctx.interaction:
                await ctx.interaction.response.send_message(embed=embed)
            else:
                await ctx.send(embed=embed)
            return

        # Update configuration based on provided parameters
        changes = []

        if enabled is not None:
            config["enabled"] = enabled
            changes.append(f"Status: {'Enabled' if enabled else 'Disabled'}")

        if action is not None:
            config["action"] = action.value
            changes.append(f"Action: {action.value.title()}")

        if timeout_duration is not None:
            if timeout_duration < 1 or timeout_duration > 2419200:  # Max 28 days
                if ctx.interaction:
                    await ctx.interaction.response.send_message(
                        "Timeout duration must be between 1 second and 28 days (2419200 seconds).",
                        ephemeral=True,
                    )
                else:
                    await ctx.send(
                        "Timeout duration must be between 1 second and 28 days (2419200 seconds)."
                    )
                return
            config["timeout_duration"] = timeout_duration
            changes.append(f"Timeout duration: {timeout_duration} seconds")

        if keywords is not None:
            keyword_list = [
                kw.strip().lower() for kw in keywords.split(",") if kw.strip()
            ]
            config["keywords"] = keyword_list
            changes.append(
                f"Keywords: {', '.join(keyword_list) if keyword_list else 'None'}"
            )

        if add_keyword is not None:
            keyword = add_keyword.strip().lower()
            if keyword and keyword not in config["keywords"]:
                config["keywords"].append(keyword)
                changes.append(f"Added keyword: {keyword}")
            elif keyword in config["keywords"]:
                changes.append(f"Keyword '{keyword}' already exists")

        if remove_keyword is not None:
            keyword = remove_keyword.strip().lower()
            if keyword in config["keywords"]:
                config["keywords"].remove(keyword)
                changes.append(f"Removed keyword: {keyword}")
            else:
                changes.append(f"Keyword '{keyword}' not found")

        if log_channel is not None:
            config["log_channel"] = log_channel.id
            changes.append(f"Log channel: {log_channel.mention}")

        if whitelist_role is not None:
            if whitelist_role.id not in config["whitelist_roles"]:
                config["whitelist_roles"].append(whitelist_role.id)
                changes.append(f"Added whitelisted role: {whitelist_role.mention}")
            else:
                changes.append(f"Role {whitelist_role.mention} already whitelisted")

        if whitelist_user is not None:
            if whitelist_user.id not in config["whitelist_users"]:
                config["whitelist_users"].append(whitelist_user.id)
                changes.append(f"Added whitelisted user: {whitelist_user.mention}")
            else:
                changes.append(f"User {whitelist_user.mention} already whitelisted")

        if remove_whitelist_role is not None:
            if remove_whitelist_role.id in config["whitelist_roles"]:
                config["whitelist_roles"].remove(remove_whitelist_role.id)
                changes.append(
                    f"Removed whitelisted role: {remove_whitelist_role.mention}"
                )
            else:
                changes.append(f"Role {remove_whitelist_role.mention} not in whitelist")

        if remove_whitelist_user is not None:
            if remove_whitelist_user.id in config["whitelist_users"]:
                config["whitelist_users"].remove(remove_whitelist_user.id)
                changes.append(
                    f"Removed whitelisted user: {remove_whitelist_user.mention}"
                )
            else:
                changes.append(f"User {remove_whitelist_user.mention} not in whitelist")

        if load_default_keywords is not None and load_default_keywords:
            config["keywords"] = DEFAULT_SCAM_KEYWORDS.copy()
            changes.append(
                f"Loaded {len(DEFAULT_SCAM_KEYWORDS)} default scam detection keywords"
            )

        if clear_keywords is not None and clear_keywords:
            config["keywords"] = []
            changes.append("Cleared all keywords")

        # Save the updated configuration
        await set_guild_botdetect_config(guild_id, config)

        # Send confirmation message
        embed = discord.Embed(
            title="Bot Detection Configuration Updated",
            description="The following changes were made:",
            color=discord.Color.green(),
        )

        for i, change in enumerate(changes, 1):
            embed.add_field(name=f"Change {i}", value=change, inline=False)

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)

    @botdetect.command(
        name="defaults", description="View the default scam bot keywords available."
    )
    async def botdetect_defaults(self, ctx: commands.Context):
        """Show the default scam bot keywords that can be loaded."""

        embed = discord.Embed(
            title="🤖 Default Scam Bot Keywords",
            description=f"Here are the {len(DEFAULT_SCAM_KEYWORDS)} default keywords used to detect common scam bots:",
            color=discord.Color.blue(),
        )

        # Group keywords by category for better readability
        categories = {
            "Discord Nitro Scams": [
                kw for kw in DEFAULT_SCAM_KEYWORDS if "nitro" in kw or "discord" in kw
            ],
            "Steam/Gaming Scams": [
                kw
                for kw in DEFAULT_SCAM_KEYWORDS
                if "steam" in kw or "skin" in kw or "cs" in kw
            ],
            "Crypto/Investment": [
                kw
                for kw in DEFAULT_SCAM_KEYWORDS
                if any(
                    word in kw
                    for word in [
                        "crypto",
                        "bitcoin",
                        "eth",
                        "nft",
                        "investment",
                        "profit",
                        "money",
                    ]
                )
            ],
            "Phishing Phrases": [
                kw
                for kw in DEFAULT_SCAM_KEYWORDS
                if any(
                    word in kw
                    for word in [
                        "click",
                        "verify",
                        "account",
                        "security",
                        "urgent",
                        "confirm",
                    ]
                )
            ],
            "Generic Scam Phrases": [
                kw
                for kw in DEFAULT_SCAM_KEYWORDS
                if any(
                    word in kw
                    for word in [
                        "congratulations",
                        "winner",
                        "selected",
                        "prize",
                        "free",
                        "exclusive",
                    ]
                )
            ],
            "Support Impersonation": [
                kw
                for kw in DEFAULT_SCAM_KEYWORDS
                if any(
                    word in kw
                    for word in ["support", "admin", "staff", "official", "team"]
                )
            ],
            "Suspicious Domains": [
                kw
                for kw in DEFAULT_SCAM_KEYWORDS
                if any(
                    word in kw
                    for word in ["bit.ly", "tinyurl", "discrod", "steampowered"]
                )
            ],
        }

        # Add uncategorized keywords
        categorized = set()
        for cat_keywords in categories.values():
            categorized.update(cat_keywords)

        uncategorized = [kw for kw in DEFAULT_SCAM_KEYWORDS if kw not in categorized]
        if uncategorized:
            categories["Other"] = uncategorized

        # Add fields for each category
        for category, keywords in categories.items():
            if keywords:
                # Limit to first 10 keywords per category to avoid embed limits
                display_keywords = keywords[:10]
                if len(keywords) > 10:
                    keyword_text = (
                        ", ".join(display_keywords)
                        + f"\n*...and {len(keywords) - 10} more*"
                    )
                else:
                    keyword_text = ", ".join(display_keywords)

                embed.add_field(
                    name=f"{category} ({len(keywords)})",
                    value=f"`{keyword_text}`",
                    inline=False,
                )

        embed.add_field(
            name="💡 Usage",
            value="Use `/botdetect config load_default_keywords:True` to load these keywords into your server's configuration.",
            inline=False,
        )

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)

    @botdetect.command(
        name="enable",
        description="Quickly enable or disable bot detection for this server.",
    )
    @app_commands.describe(enabled="Enable (True) or disable (False) bot detection")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def botdetect_enable(self, ctx: commands.Context, enabled: bool):
        """Quickly enable or disable bot detection."""

        if not ctx.guild:
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "This command can only be used in a server.", ephemeral=True
                )
            else:
                await ctx.send("This command can only be used in a server.")
            return

        guild_id = ctx.guild.id
        config = await get_guild_botdetect_config(guild_id)

        # Update the enabled status
        config["enabled"] = enabled
        await set_guild_botdetect_config(guild_id, config)

        # Create response embed
        if enabled:
            embed = discord.Embed(
                title="🟢 Bot Detection Enabled",
                description=f"Bot detection is now **enabled** for **{ctx.guild.name}**",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Current Settings",
                value=f"**Action:** {config['action'].title()}\n"
                f"**Keywords:** {len(config['keywords'])} configured\n"
                f"**Log Channel:** {'Set' if config['log_channel'] else 'Not set'}",
                inline=False,
            )
            if len(config["keywords"]) == 0:
                embed.add_field(
                    name="⚠️ No Keywords Configured",
                    value="Use `/botdetect config load_default_keywords:True` to load default scam detection keywords.",
                    inline=False,
                )
        else:
            embed = discord.Embed(
                title="🔴 Bot Detection Disabled",
                description=f"Bot detection is now **disabled** for **{ctx.guild.name}**",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="Note",
                value="Your configuration has been saved. Use `/botdetect enable enabled:True` to re-enable detection.",
                inline=False,
            )

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)

    @botdetect.command(
        name="status",
        description="Check the current bot detection status for this server.",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def botdetect_status(self, ctx: commands.Context):
        """Show a quick status overview of bot detection."""

        if not ctx.guild:
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "This command can only be used in a server.", ephemeral=True
                )
            else:
                await ctx.send("This command can only be used in a server.")
            return

        guild_id = ctx.guild.id
        config = await get_guild_botdetect_config(guild_id)

        # Create status embed
        embed = discord.Embed(
            title="🤖 Bot Detection Status",
            description=f"Status for **{ctx.guild.name}**",
            color=discord.Color.green() if config["enabled"] else discord.Color.red(),
        )

        # Status indicator
        status_emoji = "🟢" if config["enabled"] else "🔴"
        status_text = "Enabled" if config["enabled"] else "Disabled"
        embed.add_field(
            name="Status", value=f"{status_emoji} **{status_text}**", inline=True
        )

        # Action
        embed.add_field(name="Action", value=config["action"].title(), inline=True)

        # Keywords count
        embed.add_field(
            name="Keywords", value=f"{len(config['keywords'])} configured", inline=True
        )

        # Log channel
        if config["log_channel"]:
            log_channel = ctx.guild.get_channel(config["log_channel"])
            log_text = log_channel.mention if log_channel else "Unknown Channel"
        else:
            log_text = "Not set"

        embed.add_field(name="Log Channel", value=log_text, inline=True)

        # Whitelists
        whitelist_info = []
        if config["whitelist_roles"]:
            whitelist_info.append(f"**Roles:** {len(config['whitelist_roles'])}")
        if config["whitelist_users"]:
            whitelist_info.append(f"**Users:** {len(config['whitelist_users'])}")

        embed.add_field(
            name="Whitelisted",
            value=", ".join(whitelist_info) if whitelist_info else "None",
            inline=True,
        )

        # Quick actions
        embed.add_field(
            name="Quick Actions",
            value="• `/botdetect enable` - Toggle on/off\n"
            "• `/botdetect config` - Full configuration\n"
            "• `/botdetect defaults` - View default keywords",
            inline=False,
        )

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages and check for bot detection keywords."""

        # Ignore messages from bots, DMs, or if the author is the bot itself
        if message.author.bot or not message.guild or message.author == self.bot.user:
            return

        guild_id = message.guild.id
        config = await get_guild_botdetect_config(guild_id)

        # Check if bot detection is enabled
        if not config["enabled"]:
            return

        # Check if user is whitelisted
        if message.author.id in config["whitelist_users"]:
            return

        # Check if user has whitelisted role
        user_role_ids = [role.id for role in message.author.roles]
        if any(role_id in config["whitelist_roles"] for role_id in user_role_ids):
            return

        # Check if message contains any keywords
        message_content = message.content.lower()
        detected_keywords = []

        for keyword in config["keywords"]:
            if keyword in message_content:
                detected_keywords.append(keyword)

        # If keywords detected, take action
        if detected_keywords:
            await self._handle_bot_detection(message, detected_keywords, config)

    async def _handle_bot_detection(
        self, message: discord.Message, keywords: List[str], config: Dict[str, Any]
    ):
        """Handle detected bot message based on configuration."""

        action = config["action"]
        guild = message.guild
        member = message.author

        # Log the detection
        await self._log_detection(message, keywords, action, config)

        try:
            # Delete the message first (for all actions)
            try:
                await message.delete()
            except discord.NotFound:
                pass  # Message already deleted
            except discord.Forbidden:
                pass  # No permission to delete

            # Take the configured action
            if action == "warn":
                try:
                    embed = discord.Embed(
                        title="⚠️ Bot Detection Warning",
                        description=f"Your message was flagged as potential bot activity and has been removed.",
                        color=discord.Color.orange(),
                    )
                    embed.add_field(
                        name="Detected Keywords",
                        value=", ".join(keywords),
                        inline=False,
                    )
                    embed.add_field(name="Server", value=guild.name, inline=True)
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass  # Can't DM user

            elif action == "kick":
                if guild.me.guild_permissions.kick_members:
                    try:
                        await member.kick(
                            reason=f"Bot detection: keywords detected: {', '.join(keywords)}"
                        )
                    except discord.Forbidden:
                        pass  # No permission or can't kick this user

            elif action == "ban":
                if guild.me.guild_permissions.ban_members:
                    try:
                        await member.ban(
                            reason=f"Bot detection: keywords detected: {', '.join(keywords)}",
                            delete_message_days=1,
                        )
                    except discord.Forbidden:
                        pass  # No permission or can't ban this user

            elif action == "timeout":
                if guild.me.guild_permissions.moderate_members:
                    try:
                        import datetime

                        timeout_until = discord.utils.utcnow() + datetime.timedelta(
                            seconds=config["timeout_duration"]
                        )
                        await member.timeout(
                            timeout_until,
                            reason=f"Bot detection: keywords detected: {', '.join(keywords)}",
                        )
                    except discord.Forbidden:
                        pass  # No permission or can't timeout this user

            # "delete" action just deletes the message, which we already did above

        except Exception as e:
            print(f"Error handling bot detection in {guild.name}: {e}")

    async def _log_detection(
        self,
        message: discord.Message,
        keywords: List[str],
        action: str,
        config: Dict[str, Any],
    ):
        """Log bot detection event to the configured log channel."""

        log_channel_id = config.get("log_channel")
        if not log_channel_id:
            return

        log_channel = message.guild.get_channel(log_channel_id)
        if not log_channel:
            return

        try:
            embed = discord.Embed(
                title="🤖 Bot Detection Alert",
                description=f"Potential bot activity detected and action taken.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            embed.add_field(
                name="User",
                value=f"{message.author.mention} ({message.author})",
                inline=True,
            )

            embed.add_field(name="Channel", value=message.channel.mention, inline=True)

            embed.add_field(name="Action Taken", value=action.title(), inline=True)

            embed.add_field(
                name="Detected Keywords", value=", ".join(keywords), inline=False
            )

            # Truncate message content if too long
            content = message.content
            if len(content) > 1000:
                content = content[:1000] + "..."

            embed.add_field(
                name="Message Content",
                value=f"```{content}```" if content else "*No text content*",
                inline=False,
            )

            embed.set_footer(text=f"User ID: {message.author.id}")

            await log_channel.send(embed=embed)

        except Exception as e:
            print(f"Error logging bot detection: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(BotDetectCog(bot))

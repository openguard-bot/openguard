import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict, Any
import inspect

from bot import get_prefix


class HelpView(discord.ui.View):
    """Interactive view for the help command with category navigation."""

    # --- Configuration ---
    EXCLUDED_COGS = ["Shell", "UpdateCog"]
    EXCLUDED_COMMANDS = []  # Qualified names

    # Maps cogs to user-friendly categories. Cogs not in this map will get their own category.
    CATEGORY_MAPPING = {
        "overview": {
            "name": "Overview",
            "description": "General bot information and quick start guide.",
            "emoji": "📋",
            "color": discord.Color.blue(),
        },
        "moderation": {
            "name": "AI & Human Moderation",
            "description": "Commands for both AI and human moderation actions.",
            "emoji": "🛡️",
            "color": discord.Color.red(),
            "cogs": ["CoreAICog", "HumanModerationCog", "AppealCog"],
            "footer": "💡 Most commands require Administrator or Moderator permissions.",
        },
        "ai_configuration": {
            "name": "AI Configuration",
            "description": "Commands for configuring the AI model and its behavior.",
            "emoji": "🧠",
            "color": discord.Color.purple(),
            "cogs": ["ConfigCog", "ModelManagementCog"],
            "footer": "💡 Configuration commands require Administrator permissions.",
        },
        "logging": {
            "name": "Logging",
            "description": "Server event and moderation action logging.",
            "emoji": "📝",
            "color": discord.Color.green(),
            "cogs": ["LoggingCog", "ModLogCog"],
            "footer": "💡 Logging commands require Administrator permissions.",
        },
        "security": {
            "name": "Security",
            "description": "Bot detection, raid defense, and security features.",
            "emoji": "🔒",
            "color": discord.Color.orange(),
            "cogs": ["BotDetectCog", "RaidDefenceCog"],
            "footer": "💡 Security commands require Manage Messages or Administrator permissions.",
        },
        "messagerate": {
            "name": "Message Rate Limiting",
            "description": "Commands for managing message rate limits and user information.",
            "emoji": "📊",
            "color": discord.Color.gold(),
            "cogs": ["MessageRateCog"],
            "footer": "💡 Some commands may require moderation permissions.",
        },
        "utility": {
            "name": "Utility",
            "description": "General utility commands.",
            "emoji": "🔧",
            "color": discord.Color.teal(),
            "cogs": ["UserInfoCog", "Ping", "HelpCog", "CreditsCog"],
            "footer": "💡 Some commands may require special permissions.",
        },
        "system": {
            "name": "System",
            "description": "System information.",
            "emoji": "⚙️",
            "color": discord.Color.dark_purple(),
            "cogs": ["HwInfo"],
            "footer": "💡 Some commands are owner-only or require special permissions.",
        },
    }

    def __init__(self, bot: commands.Bot, user: discord.User):
        super().__init__(timeout=900)
        self.bot = bot
        self.user = user
        self.current_category = "overview"
        self.categories = {}
        self._command_cache = None
        # Defer setup until the first interaction to ensure all cogs are loaded.

    def _generate_categories(self):
        """Dynamically generate categories from the mapping and loaded cogs."""
        self.categories = {k: v for k, v in self.CATEGORY_MAPPING.items()}
        
        cog_to_category = {}
        for key, data in self.CATEGORY_MAPPING.items():
            if "cogs" in data:
                for cog_name in data["cogs"]:
                    cog_to_category[cog_name] = key

        for cog_name, cog in self.bot.cogs.items():
            if cog_name in self.EXCLUDED_COGS or cog_name in cog_to_category:
                continue
            
            self.categories[cog_name.lower()] = {
                "name": cog_name.replace("Cog", ""),
                "description": inspect.getdoc(cog) or "No description available.",
                "emoji": "🧩",
                "color": discord.Color.default(),
                "cogs": [cog_name]
            }

    async def _discover_commands(self) -> Dict[str, List[Dict[str, Any]]]:
        """Discover and categorize all bot commands based on cogs."""
        if self._command_cache is not None:
            return self._command_cache

        self._generate_categories()

        categorized_commands = {category: [] for category in self.categories.keys()}
        processed_qnames = set() # To prevent duplication of hybrid commands/groups
        
        cog_to_category = {}
        for key, data in self.categories.items():
            if "cogs" in data:
                for cog_name in data["cogs"]:
                    cog_to_category[cog_name] = key

        # 1. Process all commands from bot.commands (includes hybrid and pure prefix)
        for cmd in self.bot.commands: # Renamed 'command' to 'cmd'
            if cmd.qualified_name in self.EXCLUDED_COMMANDS or not cmd.cog:
                continue

            cog_name = cmd.cog.__class__.__name__
            if cog_name in self.EXCLUDED_COGS:
                continue
            
            category = cog_to_category.get(cog_name, cog_name.lower())
            if category not in categorized_commands:
                continue

            # If it's a hybrid command or group, prefer its slash representation
            if isinstance(cmd, (commands.HybridCommand, commands.HybridGroup)) and cmd.app_command:
                app_cmd = cmd.app_command
                # If it's a hybrid group, we don't list the group itself, but its subcommands will be handled by walk_commands
                if isinstance(app_cmd, app_commands.Group):
                    # Mark the group's qualified name as processed to avoid listing its prefix form
                    processed_qnames.add(cmd.qualified_name)
                    continue # Skip adding the group itself as a command

                # This is a hybrid command (not a group)
                signature = f"/{app_cmd.qualified_name}"
                params = [f"<{p.name}>" if p.required else f"[{p.name}]" for p in app_cmd.parameters]
                if params:
                    signature += " " + " ".join(params)

                categorized_commands[category].append({
                    "name": signature,
                    "description": app_cmd.description or "No description available",
                    "type": "slash",
                })
                processed_qnames.add(cmd.qualified_name) # Mark the hybrid command as processed
            
            # If it's a pure prefix command (or a hybrid command that somehow doesn't have app_command)
            elif cmd.qualified_name not in processed_qnames: # Ensure it hasn't been processed as a slash command
                signature = f"o!{cmd.name}"
                if cmd.signature:
                    signature += f" {cmd.signature}"

                categorized_commands[category].append({
                    "name": signature,
                    "description": cmd.help or "No description available",
                    "type": "prefix",
                })
                processed_qnames.add(cmd.qualified_name) # Mark as processed

        # 2. Discover pure slash commands (those not bound to a commands.Command)
        for cmd in self.bot.tree.walk_commands(): # Renamed 'command' to 'cmd'
            if cmd.qualified_name in self.EXCLUDED_COMMANDS:
                continue
            
            # If this slash command's qualified name was already processed (as part of a hybrid command), skip it
            if cmd.qualified_name in processed_qnames:
                continue

            # If it's an app_commands.Group, we don't list it directly, only its subcommands
            if isinstance(cmd, app_commands.Group):
                continue

            # Now 'cmd' is guaranteed to be an app_commands.Command that is not hybrid
            cog_name = cmd.binding.__class__.__name__ if cmd.binding else None
            if not cog_name or cog_name in self.EXCLUDED_COGS:
                continue

            category = cog_to_category.get(cog_name, cog_name.lower())
            if category not in categorized_commands:
                continue

            signature = f"/{cmd.qualified_name}"
            params = [f"<{p.name}>" if p.required else f"[{p.name}]" for p in cmd.parameters]
            if params:
                signature += " " + " ".join(params)

            categorized_commands[category].append({
                "name": signature,
                "description": cmd.description or "No description available",
                "type": "slash",
            })
            processed_qnames.add(cmd.qualified_name) # Mark as processed

        final_categorized_commands = {}
        for category, command_list in categorized_commands.items():
            if command_list:
                command_list.sort(key=lambda x: x["name"])
                final_categorized_commands[category] = command_list
        
        self.categories = {k: v for k, v in self.categories.items() if k in final_categorized_commands or k == "overview"}

        self._command_cache = final_categorized_commands
        return final_categorized_commands

    def setup_dropdown(self):
        """Setup the category selection dropdown."""
        sorted_categories = sorted(
            self.categories.items(),
            key=lambda item: (item[0] != 'overview', item[1]['name'])
        )

        options = []
        for key, category in sorted_categories:
            options.append(
                discord.SelectOption(
                    label=category["name"],
                    description=category.get("description", "Commands"),
                    emoji=category.get("emoji", "❓"),
                    value=key,
                    default=(key == self.current_category),
                )
            )

        select = CategorySelect(options, self)
        self.clear_items()
        self.add_item(select)
        self.add_item(RefreshButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact with the view."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ You can't interact with this help menu. Use `o!help` to get your own!",
                ephemeral=True,
            )
            return False
        return True

    async def update_category(self, interaction: discord.Interaction, category: str):
        """Update the displayed category."""
        self.current_category = category
        embed = await self.create_category_embed(category)
        self.setup_dropdown()
        await interaction.message.edit(embed=embed, view=self)

    async def on_timeout(self):
        """Handle view timeout."""
        for item in self.children:
            item.disabled = True
        if hasattr(self, "message") and self.message:
            try:
                embed = discord.Embed(
                    title="⏰ Help Menu Timed Out",
                    description="This help menu has timed out. Use `o!help` to get a new one!",
                    color=discord.Color.greyple(),
                )
                await self.message.edit(embed=embed, view=self)
            except (discord.NotFound, discord.Forbidden):
                pass

    async def create_category_embed(self, category: str, ctx: commands.Context) -> discord.Embed:
        """Create an embed for the specified category."""
        if not self.categories:
            await self._discover_commands()
            self.setup_dropdown()

        if category == "overview":
            return await self.create_overview_embed(ctx)
        elif category in self.categories:
            return await self._create_command_embed(category)
        else:
            return await self.create_overview_embed(ctx)

    async def _create_command_embed(self, category_key: str) -> discord.Embed:
        """Create a generic command embed for a given category."""
        category_info = self.categories[category_key]
        embed = discord.Embed(
            title=f"{category_info['emoji']} {category_info['name']}",
            description=category_info["description"],
            color=category_info["color"],
        )
        commands_data = await self._discover_commands()
        category_commands = commands_data.get(category_key, [])

        if not category_commands:
            embed.add_field(
                name="No Commands Found",
                value=f"No commands are currently available in the {category_info['name']} category.",
                inline=False,
            )
        else:
            current_field_value = ""
            field_count = 1
            for cmd in category_commands:
                command_line = f"`{cmd['name']}` - {cmd['description']}\n"
                if len(current_field_value) + len(command_line) > 1024:
                    embed.add_field(
                        name=f"Commands (Part {field_count})",
                        value=current_field_value,
                        inline=False,
                    )
                    current_field_value = ""
                    field_count += 1
                current_field_value += command_line
            
            if current_field_value:
                embed.add_field(
                    name="Commands" if field_count == 1 else f"Commands (Part {field_count})",
                    value=current_field_value,
                    inline=False,
                )

        if "footer" in category_info:
            embed.set_footer(text=category_info["footer"])
        return embed

    async def create_overview_embed(self, ctx: commands.Context) -> discord.Embed:
        """Create the overview embed."""
        # Ensure categories and commands are loaded before creating the embed
        if not self.categories:
            await self._discover_commands()
            self.setup_dropdown()
            
        category_info = self.categories["overview"]
        embed = discord.Embed(
            title="🤖 AI Moderation Bot - Help",
            description="Welcome to the AI Moderation Bot! This bot provides advanced AI-powered moderation, comprehensive logging, and security features for your Discord server.",
            color=category_info["color"],
        )
        embed.add_field(
            name="🚀 Quick Start",
            value=(
                "• Use the dropdown below to browse command categories.\n"
                "• Almost all commands are slash commands (start with `/`).\n"
                f"• All commands can also be invoked using the prefix `{await get_prefix(self.bot, ctx)}`, but they may not behave correctly, and can't be ephemeral.\n"
                "• Use `/help <command>` for detailed help on a specific command."
            ),
            inline=False,
        )
        
        commands_data = await self._discover_commands()
        total_commands = sum(len(cmds) for cmds in commands_data.values())

        embed.add_field(
            name="📊 Bot Statistics",
            value=(
                f"• **Servers**: {len(self.bot.guilds)}\n"
                f"• **Commands**: {total_commands}\n"
                f"• **Prefix**: `{await get_prefix(self.bot, ctx)}`\n"
            ),
            inline=True,
        )
        embed.add_field(
            name="🔗 Key Features",
            value=(
                "• AI-powered content moderation\n"
                "• Comprehensive event logging\n"
                "• Bot/raid detection\n"
                "• User information tools"
            ),
            inline=True,
        )
        embed.add_field(
            name="💡 Need Help?",
            value=(
                "• Browse categories using the dropdown.\n"
                "• Check command descriptions for usage.\n"
                "• Admin permissions are required for most configuration commands."
            ),
            inline=False,
        )
        embed.set_footer(
            text="Select a category from the dropdown to view specific commands."
        )
        return embed


class CategorySelect(discord.ui.Select):
    """Dropdown for selecting help categories."""

    def __init__(self, options: List[discord.SelectOption], view: HelpView):
        super().__init__(placeholder="Select a category...", options=options)
        self.help_view = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.help_view.update_category(interaction, self.values[0])


class RefreshButton(discord.ui.Button):
    """Button to refresh the help menu."""

    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary, emoji="🔄", label="Refresh"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        view = self.view
        if isinstance(view, HelpView):
            view._command_cache = None
            embed = await view.create_category_embed(view.current_category)
            view.setup_dropdown()
            await interaction.message.edit(embed=embed, view=view)


class HelpCog(commands.Cog):
    """Comprehensive help system that replaces the default discord.py help command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Remove the default help command
        self.bot.remove_command("help")

    @commands.hybrid_command(name="help", aliases=["h"], description="Show help information for the bot.")
    async def help_command(
        self, ctx: commands.Context, *, command: Optional[str] = None
    ):
        """
        Show help information for the bot.
        """
        if command:
            await self.show_command_help(ctx, command)
        else:
            await self.show_main_help(ctx)

    async def show_main_help(self, ctx: commands.Context):
        """Show the main interactive help menu."""
        view = HelpView(self.bot, ctx.author)
        
        # The embed creation will trigger command discovery and dropdown setup.
        embed = await view.create_category_embed(view.current_category, ctx)

        try:
            message = await ctx.send(embed=embed, view=view)
            view.message = message
        except discord.Forbidden:
            await ctx.send(
                "❌ I need permission to send embeds to display the help menu properly."
            )

    async def show_command_help(self, ctx: commands.Context, command_name: str):
        """Show detailed help for a specific command."""
        # Try to find the command
        cmd = self.bot.get_command(command_name)
        if cmd:
            await self.show_prefix_command_help(ctx, cmd)
            return

        # Try to find slash command
        slash_cmd = None
        for cmd in self.bot.tree.walk_commands():
            if cmd.name == command_name or (
                hasattr(cmd, "qualified_name") and cmd.qualified_name == command_name
            ):
                slash_cmd = cmd
                break

        if slash_cmd:
            await self.show_slash_command_help(ctx, slash_cmd)
            return

        # Command not found
        embed = discord.Embed(
            title="❌ Command Not Found",
            description=f"No command named `{command_name}` was found.",
            color=discord.Color.red(),
        )
        embed.add_field(
            name="💡 Suggestions",
            value=(
                "• Use `o!help` to see all available commands\n"
                "• Check your spelling\n"
                "• Some commands may be slash commands (use `/` instead of `o!`)"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

    async def show_prefix_command_help(
        self, ctx: commands.Context, command: commands.Command
    ):
        """Show help for a prefix command."""
        embed = discord.Embed(
            title=f"📖 Command: {command.name}",
            description=command.help or "No description available.",
            color=discord.Color.green(),
        )

        # Add usage information
        usage = f"o!{command.name}"
        if command.signature:
            usage += f" {command.signature}"
        embed.add_field(name="📝 Usage", value=f"`{usage}`", inline=False)

        # Add aliases if any
        if command.aliases:
            aliases = ", ".join([f"`o!{alias}`" for alias in command.aliases])
            embed.add_field(name="🔗 Aliases", value=aliases, inline=False)

        # Add permissions if any
        if hasattr(command, "checks") and command.checks:
            perms = []
            for check in command.checks:
                if hasattr(check, "__name__"):
                    if "owner" in check.__name__:
                        perms.append("Bot Owner")
                    elif "admin" in check.__name__:
                        perms.append("Administrator")
            if perms:
                embed.add_field(
                    name="🔒 Required Permissions", value=", ".join(perms), inline=False
                )

        await ctx.send(embed=embed)

    async def show_slash_command_help(
        self, ctx: commands.Context, command: app_commands.Command
    ):
        """Show help for a slash command."""
        embed = discord.Embed(
            title=f"📖 Slash Command: /{command.qualified_name}",
            description=command.description or "No description available.",
            color=discord.Color.green(),
        )

        # Add usage information
        usage = f"/{command.qualified_name}"
        if hasattr(command, "parameters") and command.parameters:
            params = []
            for param in command.parameters:
                if param.required:
                    params.append(f"<{param.name}>")
                else:
                    params.append(f"[{param.name}]")
            if params:
                usage += " " + " ".join(params)

        embed.add_field(name="📝 Usage", value=f"`{usage}`", inline=False)

        # Add parameter details if any
        if hasattr(command, "parameters") and command.parameters:
            param_details = []
            for param in command.parameters:
                required = "Required" if param.required else "Optional"
                param_details.append(
                    f"• `{param.name}` ({required}): {param.description or 'No description'}"
                )

            if param_details:
                embed.add_field(
                    name="📋 Parameters",
                    value="\n".join(
                        param_details[:5]
                    ),  # Limit to 5 to avoid embed limits
                    inline=False,
                )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))

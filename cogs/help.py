import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List, Dict, Any
import inspect

class HelpView(discord.ui.View):
    """Interactive view for the help command with category navigation."""
    
    def __init__(self, bot: commands.Bot, user: discord.User):
        super().__init__(timeout=900)
        self.bot = bot
        self.user = user
        self.current_category = "overview"

        # Define command categories with their mappings
        self.categories = {
            "overview": {
                "name": "📋 Overview",
                "description": "General bot information and quick start guide",
                "emoji": "📋",
                "color": discord.Color.blue()
            },
            "moderation": {
                "name": "🛡️ AI Moderation",
                "description": "AI-powered moderation commands",
                "emoji": "🛡️",
                "color": discord.Color.red(),
                "footer": "💡 Most commands require Administrator permissions"
            },
            "logging": {
                "name": "📝 Logging",
                "description": "Server event logging and moderation logs",
                "emoji": "📝",
                "color": discord.Color.green(),
                "footer": "💡 Logging commands require Administrator permissions"
            },
            "security": {
                "name": "🔒 Security",
                "description": "Bot detection, raid defense, and security features",
                "emoji": "🔒",
                "color": discord.Color.orange(),
                "footer": "💡 Security commands require Manage Messages or Administrator permissions"
            },
            "system": {
                "name": "⚙️ System",
                "description": "System information and bot management",
                "emoji": "⚙️",
                "color": discord.Color.purple(),
                "footer": "💡 Some commands are owner-only or require special permissions"
            },
            "utility": {
                "name": "🔧 Utility",
                "description": "User information and general utility commands",
                "emoji": "🔧",
                "color": discord.Color.teal(),
                "footer": "💡 Admin commands require Administrator permissions"
            },
            "admin": {
                "name": "👑 Admin",
                "description": "Administrative and owner-only commands",
                "emoji": "👑",
                "color": discord.Color.gold(),
                "footer": "🚨 These commands require the highest level of permissions"
            }
        }

        # Cache for discovered commands
        self._command_cache = None

        self.setup_dropdown()

    def _categorize_command(self, command_name: str, cog_name: str = None, group_name: str = None) -> str:
        """Categorize a command based on its name, cog, or group."""
        command_lower = command_name.lower()
        cog_lower = cog_name.lower() if cog_name else ""
        group_lower = group_name.lower() if group_name else ""

        # Admin/Owner commands
        if any(keyword in command_lower for keyword in ["shell", "update", "testerror"]) or \
           any(keyword in cog_lower for keyword in ["shell", "update"]):
            return "admin"

        # AI Moderation commands
        if command_lower.startswith("aimod") or group_lower == "aimod" or \
           any(keyword in command_lower for keyword in ["aimod", "globalban", "infractions", "appeals"]) or \
           any(keyword in cog_lower for keyword in ["aimod", "moderation"]):
            return "moderation"

        # Logging commands
        if group_lower in ["log", "modlog"] or \
           any(keyword in command_lower for keyword in ["log", "modlog"]) or \
           any(keyword in cog_lower for keyword in ["logging", "mod_log"]):
            return "logging"

        # Security commands
        if group_lower in ["botdetect", "security"] or \
           any(keyword in command_lower for keyword in ["botdetect", "security", "raid"]) or \
           any(keyword in cog_lower for keyword in ["botdetect", "raiddefence", "security"]):
            return "security"

        # System commands
        if group_lower == "system" or \
           any(keyword in command_lower for keyword in ["system", "temps", "check"]) or \
           any(keyword in cog_lower for keyword in ["hwinfo", "system"]):
            return "system"

        # Utility commands
        if any(keyword in command_lower for keyword in ["aboutuser", "userinfo"]) or \
           any(keyword in cog_lower for keyword in ["abtuser", "utility"]):
            return "utility"

        # Default to utility for uncategorized commands
        return "utility"

    async def _discover_commands(self) -> Dict[str, List[Dict[str, Any]]]:
        """Discover and categorize all bot commands."""
        if self._command_cache is not None:
            return self._command_cache

        categorized_commands = {category: [] for category in self.categories.keys()}

        # Discover slash commands
        for command in self.bot.tree.walk_commands():
            if isinstance(command, app_commands.Group):
                continue
            cog_name = command.binding.__class__.__name__ if command.binding else ''
            group_name = command.parent.name if command.parent else ''

            category = self._categorize_command(command.name, cog_name, group_name)

            # Build command signature
            signature = f"/{command.qualified_name}"
            if hasattr(command, 'parameters') and command.parameters:
                params = []
                for param in command.parameters:
                    if param.required:
                        params.append(f"<{param.name}>")
                    else:
                        params.append(f"[{param.name}]")
                if params:
                    signature += " " + " ".join(params)

            categorized_commands[category].append({
                'name': signature,
                'description': command.description or "No description available",
                'type': 'slash'
            })

        # Discover prefix commands
        for command in self.bot.commands:
            cog_name = command.cog.__class__.__name__ if command.cog else ''

            category = self._categorize_command(command.name, cog_name)

            # Build command signature
            signature = f"o!{command.name}"
            if command.signature:
                signature += f" {command.signature}"

            categorized_commands[category].append({
                'name': signature,
                'description': command.help or "No description available",
                'type': 'prefix'
            })

        # Sort commands within each category
        for category in categorized_commands:
            categorized_commands[category].sort(key=lambda x: x['name'])

        self._command_cache = categorized_commands
        return categorized_commands
    
    def setup_dropdown(self):
        """Setup the category selection dropdown."""
        options = []
        for key, category in self.categories.items():
            options.append(discord.SelectOption(
                label=category["name"],
                description=category["description"],
                emoji=category["emoji"],
                value=key,
                default=(key == self.current_category)
            ))
        
        select = CategorySelect(options, self)
        self.clear_items()
        self.add_item(select)

        # Add refresh button
        refresh_button = RefreshButton()
        self.add_item(refresh_button)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensure only the command user can interact with the view."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ You can't interact with this help menu. Use `o!help` to get your own!",
                ephemeral=True
            )
            return False
        return True
    
    async def update_category(self, interaction: discord.Interaction, category: str):
        """Update the displayed category."""
        # Deferral is handled by the component callback
        self.current_category = category
        embed = await self.create_category_embed(category)
        self.setup_dropdown()
        # Edit the original message the component is attached to
        await interaction.message.edit(embed=embed, view=self)

    async def on_timeout(self):
        """Handle view timeout."""
        # Disable all items
        for item in self.children:
            item.disabled = True

        # Try to edit the message to show it's timed out
        if hasattr(self, 'message') and self.message:
            try:
                embed = discord.Embed(
                    title="⏰ Help Menu Timed Out",
                    description="This help menu has timed out. Use `o!help` to get a new one!",
                    color=discord.Color.greyple()
                )
                await self.message.edit(embed=embed, view=self)
            except discord.NotFound:
                pass  # Message was deleted
            except discord.Forbidden:
                pass  # No permission to edit
    
    async def create_category_embed(self, category: str) -> discord.Embed:
        """Create an embed for the specified category."""
        if category == "overview":
            return await self.create_overview_embed()
        elif category in self.categories:
            return await self._create_command_embed(category)
        else:
            return await self.create_overview_embed()  # Fallback

    async def _create_command_embed(self, category_key: str) -> discord.Embed:
        """Create a generic command embed for a given category."""
        category_info = self.categories[category_key]
        
        embed = discord.Embed(
            title=f"{category_info['emoji']} {category_info['name']}",
            description=category_info['description'],
            color=category_info['color']
        )

        commands_data = await self._discover_commands()
        category_commands = commands_data.get(category_key, [])

        if not category_commands:
            embed.add_field(
                name="No Commands Found",
                value=f"No commands are currently available in the {category_key} category.",
                inline=False
            )
        else:
            # Group commands
            grouped_commands = {}
            for cmd in category_commands:
                group_key = "Commands"  # Default group
                
                # Custom grouping logic per category
                if category_key == "moderation":
                    parts = cmd['name'].split()
                    if len(parts) >= 3 and parts[0].startswith('/aimod'):
                        group_key = f"{parts[1].title()} Commands"
                    elif len(parts) >= 2 and parts[0].startswith('/'):
                        group_key = f"{parts[0][1:].title()} Commands"
                elif category_key == "logging":
                    if "/log" in cmd['name']: group_key = "🔧 Event Logging"
                    elif "/modlog" in cmd['name']: group_key = "📋 Moderation Logs"
                elif category_key == "security":
                    if "/botdetect" in cmd['name']: group_key = "🤖 Bot Detection"
                    elif "/security" in cmd['name'] or "/raid" in cmd['name']: group_key = "🛡️ Raid Defense"
                elif category_key == "system":
                    if "/system" in cmd['name']: group_key = "📊 System Information"
                    elif "info" in cmd['name']: group_key = "ℹ️ Information Commands"
                    elif cmd['type'] == 'prefix': group_key = "🔧 Bot Management"
                elif category_key == "utility":
                    if "aboutuser" in cmd['name']: group_key = "👤 User Information"
                    elif "userinfo" in cmd['name']: group_key = "🛠️ Admin User Tools"
                elif category_key == "admin":
                    group_key = "🔧 Bot Management"

                if group_key not in grouped_commands:
                    grouped_commands[group_key] = []
                grouped_commands[group_key].append(cmd)

            # Add fields for each group
            for group_name, commands in grouped_commands.items():
                command_list = [f"`{cmd['name']}` - {cmd['description']}" for cmd in commands[:10]]
                if command_list:
                    embed.add_field(name=group_name, value="\n".join(command_list), inline=False)

        # Add special fields for certain categories
        if category_key == "logging":
            embed.add_field(
                name="📊 Logged Events",
                value=("• Member joins/leaves • Message edits/deletes\n"
                       "• Role changes • Channel updates\n"
                       "• Voice activity • Moderation actions\n"
                       "• And many more server events!"),
                inline=False
            )
        elif category_key == "security":
            embed.add_field(
                name="⚡ Detection Features",
                value=("• Scam bot keyword detection\n"
                       "• Suspicious join pattern monitoring\n"
                       "• Configurable action responses\n"
                       "• Whitelist system for trusted users/roles"),
                inline=False
            )
        elif category_key == "utility":
            embed.add_field(
                name="📋 Features",
                value=("• Detailed user profiles with avatars/banners\n"
                       "• Join dates and account creation info\n"
                       "• Role and permission information\n"
                       "• Custom administrative notes"),
                inline=False
            )
        elif category_key == "admin":
            embed.add_field(
                name="⚠️ Access Requirements",
                value=("• **Bot Owner Only**: Shell, update commands\n"
                       "• **Administrator**: Most configuration commands\n"
                       "• **Manage Messages**: Some security features\n"
                       "• **Moderate Members**: Moderation log access"),
                inline=False
            )
            embed.add_field(
                name="🔒 Security Notice",
                value=("⚠️ **Warning**: Admin commands can affect bot operation\n"
                       "• Shell commands have full system access\n"
                       "• Update commands restart the bot\n"
                       "• Use with caution and proper authorization"),
                inline=False
            )

        if "footer" in category_info:
            embed.set_footer(text=category_info["footer"])
            
        return embed

    async def create_overview_embed(self) -> discord.Embed:
        """Create the overview embed."""
        category_info = self.categories["overview"]
        embed = discord.Embed(
            title="🤖 AI Moderation Bot - Help",
            description="Welcome to the AI Moderation Bot! This bot provides advanced AI-powered moderation, comprehensive logging, and security features for your Discord server.",
            color=category_info['color']
        )
        
        embed.add_field(
            name="🚀 Quick Start",
            value=(
                "• Use the dropdown below to browse command categories\n"
                "• Most commands are slash commands (start with `/`)\n"
                "• Some admin commands use prefix `o!`\n"
                "• Use `o!help <command>` for detailed command help"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Bot Statistics",
            value=(
                f"• Servers: {len(self.bot.guilds)}\n"
                f"• Commands: {len([cmd for cmd in self.bot.tree.walk_commands()])+ len(self.bot.commands)}\n"
                f"• Prefix: `o!`"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🔗 Key Features",
            value=(
                "• AI-powered content moderation\n"
                "• Comprehensive event logging\n"
                "• Bot/raid detection\n"
                "• User information tools"
            ),
            inline=True
        )
        
        embed.add_field(
            name="💡 Need Help?",
            value=(
                "• Browse categories using the dropdown\n"
                "• Check command descriptions for usage\n"
                "• Admin permissions required for most config commands"
            ),
            inline=False
        )
        
        embed.set_footer(text="Select a category from the dropdown to view specific commands")
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
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            label="Refresh"
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
        self.bot.remove_command('help')
    
    @commands.command(name='help', aliases=['h'])
    async def help_command(self, ctx: commands.Context, *, command: Optional[str] = None):
        """
        Show help information for the bot.
        
        Usage:
        - `o!help` - Show the main help menu
        - `o!help <command>` - Show detailed help for a specific command
        """
        if command:
            await self.show_command_help(ctx, command)
        else:
            await self.show_main_help(ctx)
    
    async def show_main_help(self, ctx: commands.Context):
        """Show the main interactive help menu."""
        view = HelpView(self.bot, ctx.author)
        embed = await view.create_overview_embed()
        
        try:
            message = await ctx.send(embed=embed, view=view)
            view.message = message
        except discord.Forbidden:
            # Fallback if bot can't send embeds
            await ctx.send("❌ I need permission to send embeds to display the help menu properly.")
    
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
            if cmd.name == command_name or (hasattr(cmd, 'qualified_name') and cmd.qualified_name == command_name):
                slash_cmd = cmd
                break
        
        if slash_cmd:
            await self.show_slash_command_help(ctx, slash_cmd)
            return
        
        # Command not found
        embed = discord.Embed(
            title="❌ Command Not Found",
            description=f"No command named `{command_name}` was found.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="💡 Suggestions",
            value=(
                "• Use `o!help` to see all available commands\n"
                "• Check your spelling\n"
                "• Some commands may be slash commands (use `/` instead of `o!`)"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    async def show_prefix_command_help(self, ctx: commands.Context, command: commands.Command):
        """Show help for a prefix command."""
        embed = discord.Embed(
            title=f"📖 Command: {command.name}",
            description=command.help or "No description available.",
            color=discord.Color.green()
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
        if hasattr(command, 'checks') and command.checks:
            perms = []
            for check in command.checks:
                if hasattr(check, '__name__'):
                    if 'owner' in check.__name__:
                        perms.append("Bot Owner")
                    elif 'admin' in check.__name__:
                        perms.append("Administrator")
            if perms:
                embed.add_field(name="🔒 Required Permissions", value=", ".join(perms), inline=False)

        await ctx.send(embed=embed)

    async def show_slash_command_help(self, ctx: commands.Context, command: app_commands.Command):
        """Show help for a slash command."""
        embed = discord.Embed(
            title=f"📖 Slash Command: /{command.qualified_name}",
            description=command.description or "No description available.",
            color=discord.Color.green()
        )

        # Add usage information
        usage = f"/{command.qualified_name}"
        if hasattr(command, 'parameters') and command.parameters:
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
        if hasattr(command, 'parameters') and command.parameters:
            param_details = []
            for param in command.parameters:
                required = "Required" if param.required else "Optional"
                param_details.append(f"• `{param.name}` ({required}): {param.description or 'No description'}")

            if param_details:
                embed.add_field(
                    name="📋 Parameters",
                    value="\n".join(param_details[:5]),  # Limit to 5 to avoid embed limits
                    inline=False
                )

        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))

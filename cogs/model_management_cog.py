import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
from .aimod_helpers.config_manager import (
    get_guild_config_async,
    set_guild_config,
    DEFAULT_VERTEX_AI_MODEL,
)
from database.operations import (
    get_guild_api_key,
    set_guild_api_key,
    remove_guild_api_key,
)
from .aimod_helpers.copilot_auth import start_copilot_login


class ApiKeyModal(discord.ui.Modal):
    def __init__(self, title: str, provider: str, guild_id: int):
        super().__init__(title=title)
        self.provider = provider
        self.guild_id = guild_id

        self.api_key_input = discord.ui.TextInput(
            label="API Key",
            style=discord.TextStyle.short,
            placeholder="Enter the API key here",
            required=True,
        )
        self.add_item(self.api_key_input)

    async def on_submit(self, interaction: discord.Interaction):
        api_key = self.api_key_input.value
        success = await set_guild_api_key(self.guild_id, api_provider=self.provider, key_data=api_key)

        if success:
            await interaction.response.send_message(
                f"The guild's API key for `{self.provider}` has been set successfully.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Failed to set the guild's API key. Please try again later.",
                ephemeral=True,
            )


class OpenRouterApiKeyModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Set OpenRouter API Key")
        self.guild_id = guild_id

        self.api_key_input = discord.ui.TextInput(
            label="OpenRouter API Key",
            style=discord.TextStyle.short,
            placeholder="sk-or-v1-...",
            required=True,
            max_length=200,
        )
        self.add_item(self.api_key_input)

    async def on_submit(self, interaction: discord.Interaction):
        api_key = self.api_key_input.value.strip()
        
        # Validate OpenRouter key format
        if not api_key.startswith("sk-or-v1-"):
            await interaction.response.send_message(
                "❌ Invalid OpenRouter API key format. OpenRouter keys must start with `sk-or-v1-`.",
                ephemeral=True,
            )
            return

        # Test the API key
        await interaction.response.defer(ephemeral=True)
        
        try:
            is_valid = await self._test_openrouter_key(api_key)
            if not is_valid:
                await interaction.followup.send(
                    "❌ The provided OpenRouter API key is invalid or has insufficient permissions. Please check your key and try again.",
                    ephemeral=True,
                )
                return
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to validate the OpenRouter API key: {str(e)}",
                ephemeral=True,
            )
            return

        # Store the validated key
        success = await set_guild_api_key(self.guild_id, api_provider="openrouter", key_data=api_key)

        if success:
            await interaction.followup.send(
                "✅ OpenRouter API key has been set successfully and validated!",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "❌ Failed to store the OpenRouter API key. Please try again later.",
                ephemeral=True,
            )

    async def _test_openrouter_key(self, api_key: str) -> bool:
        """Test the OpenRouter API key by making a simple API call."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                
                # Test with a simple models list request
                async with session.get(
                    "https://openrouter.ai/api/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return response.status == 200
        except Exception:
            return False


class ModelManagementCog(commands.Cog, name="Model Management"):
    """
    Commands for managing the AI model and API keys.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="model", description="Manage the AI model for moderation.")
    async def model(self, ctx: commands.Context):
        """Manage the AI model for moderation."""
        await ctx.send_help(ctx.command)

    @commands.hybrid_group(name="byok", description="Manage the guild's API keys for the bot.")
    async def byok(self, ctx: commands.Context):
        """Manage the guild's API keys for the bot."""
        await ctx.send_help(ctx.command)

    @model.command(name="set", description="Change the AI model used for moderation (admin only).")
    @app_commands.describe(model="The OpenRouter model to use (e.g., 'google/gemini-2.0-flash-001')")
    @app_commands.checks.has_permissions(administrator=True)
    async def modsetmodel(self, ctx: commands.Context, model: str):
        if not model or len(model) < 5:
            response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
            await response_func(
                "Invalid model format. Please provide a valid OpenRouter model ID (e.g., 'google/gemini-2.0-flash-001').",
                ephemeral=False if ctx.interaction else False,
            )
            return

        guild_id = ctx.guild.id
        await set_guild_config(guild_id, "AI_MODEL", model)

        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(
            f"AI moderation model updated to `{model}` for this guild.",
            ephemeral=False if ctx.interaction else False,
        )

    @model.command(name="get", description="View the current AI model used for moderation.")
    async def modgetmodel(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        model_used = await get_guild_config_async(guild_id, "AI_MODEL", DEFAULT_VERTEX_AI_MODEL)
        embed = discord.Embed(
            title="AI Moderation Model",
            description="The current AI model used for moderation in this server is:",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Model", value=f"`{model_used}`", inline=False)
        embed.add_field(name="Default Model", value=f"`{DEFAULT_VERTEX_AI_MODEL}`", inline=False)
        embed.set_footer(text="Use /model set to change the model")
        embed.timestamp = discord.utils.utcnow()
        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(embed=embed, ephemeral=False if ctx.interaction else False)

    @byok.command(name="set", description="Set the guild's API key for a specific provider.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(provider="The provider to set the key for (e.g., 'openai', 'anthropic').")
    async def byok_set(self, ctx: commands.Context, provider: str):
        """Sets the guild's API key via a modal."""
        # Check if this is a slash command (has interaction) or text command
        if ctx.interaction:
            # Slash command - can use modal
            modal = ApiKeyModal(
                title=f"Set API Key for {provider}",
                provider=provider,
                guild_id=ctx.guild.id,
            )
            await ctx.interaction.response.send_modal(modal)
        else:
            # Text command - cannot use modal, inform user to use slash command
            await ctx.send(
                "⚠️ This command requires the use of a secure modal for API key input. "
                "Please use the slash command version: `/byok set` instead of the text command.",
                ephemeral=False,
            )

    @byok.command(
        name="info",
        description="Check the guild's currently configured API key provider.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def byok_info(self, ctx: commands.Context):
        """Checks the guild's currently configured API key provider."""
        guild_api_key = await get_guild_api_key(ctx.guild.id)
        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        if guild_api_key and guild_api_key.api_provider:
            await response_func(
                f"This guild's currently configured API provider is: `{guild_api_key.api_provider}`.",
                ephemeral=True if ctx.interaction else False,
            )
        else:
            await response_func(
                "This guild does not have a custom API key configured.",
                ephemeral=True if ctx.interaction else False,
            )

    @byok.command(name="remove", description="Remove the guild's configured API key.")
    @app_commands.checks.has_permissions(administrator=True)
    async def byok_remove(self, ctx: commands.Context):
        """Removes the guild's API key."""
        success = await remove_guild_api_key(ctx.guild.id)
        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        if success:
            await response_func(
                "The guild's API key has been successfully removed.",
                ephemeral=True if ctx.interaction else False,
            )
        else:
            await response_func(
                "This guild does not have an API key configured or an error occurred.",
                ephemeral=True if ctx.interaction else False,
            )

    @byok.command(
        name="copilot-login",
        description="Authenticate with GitHub Copilot for the guild.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def byok_copilot_login(self, ctx: commands.Context):
        """Initiates the GitHub Copilot device authentication flow for the guild."""
        await start_copilot_login(ctx, ctx.guild.id)

    @byok.command(
        name="openrouter",
        description="Set the guild's OpenRouter API key for AI moderation.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def byok_openrouter(self, ctx: commands.Context):
        """Sets the guild's OpenRouter API key via a secure modal."""
        # Check if this is a slash command (has interaction) or text command
        if ctx.interaction:
            # Slash command - can use modal
            modal = OpenRouterApiKeyModal(guild_id=ctx.guild.id)
            await ctx.interaction.response.send_modal(modal)
        else:
            # Text command - cannot use modal, inform user to use slash command
            await ctx.send(
                "⚠️ This command requires the use of a secure modal for API key input. "
                "Please use the slash command version: `/byok openrouter` instead of the text command.",
                ephemeral=False,
            )


async def setup(bot: commands.Bot):
    """Loads the ModelManagementCog."""
    await bot.add_cog(ModelManagementCog(bot))
    print("ModelManagementCog has been loaded.")

import discord
from discord.ext import commands
from discord import app_commands
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
      success = await set_guild_api_key(
          self.guild_id, api_provider=self.provider, key_data=api_key
      )

      if success:
          await interaction.response.send_message(
              f"The guild's API key for `{self.provider}` has been set successfully.",
              ephemeral=True,
          )
      else:
          await interaction.response.send_message(
              "Failed to set the guild's API key. Please try again later.", ephemeral=True
          )


class ModelManagementCog(commands.Cog, name="Model Management"):
    """
    Commands for managing the AI model and API keys.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(
        name="model", description="Manage the AI model for moderation."
    )
    async def model(self, ctx: commands.Context):
        """Manage the AI model for moderation."""
        await ctx.send_help(ctx.command)

    @commands.hybrid_group(
       name="byok", description="Manage the guild's API keys for the bot."
    )
    async def byok(self, ctx: commands.Context):
        """Manage the guild's API keys for the bot."""
        await ctx.send_help(ctx.command)

    @model.command(
        name="set", description="Change the AI model used for moderation (admin only)."
    )
    @app_commands.describe(
        model="The OpenRouter model to use (e.g., 'google/gemini-2.0-flash-001')"
    )
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
            f"AI moderation model updated to `{model}` for this guild.", ephemeral=False if ctx.interaction else False
        )

    @model.command(
        name="get", description="View the current AI model used for moderation."
    )
    async def modgetmodel(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        model_used = await get_guild_config_async(
            guild_id, "AI_MODEL", DEFAULT_VERTEX_AI_MODEL
        )
        embed = discord.Embed(
            title="AI Moderation Model",
            description=f"The current AI model used for moderation in this server is:",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Model", value=f"`{model_used}`", inline=False)
        embed.add_field(
            name="Default Model", value=f"`{DEFAULT_VERTEX_AI_MODEL}`", inline=False
        )
        embed.set_footer(text="Use /model set to change the model")
        embed.timestamp = discord.utils.utcnow()
        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(embed=embed, ephemeral=False if ctx.interaction else False)

    @byok.command(name="set", description="Set the guild's API key for a specific provider.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(provider="The provider to set the key for (e.g., 'openai', 'anthropic').")
    async def byok_set(self, interaction: discord.Interaction, provider: str):
       """Sets the guild's API key via a modal."""
       modal = ApiKeyModal(title=f"Set API Key for {provider}", provider=provider, guild_id=interaction.guild.id)
       await interaction.response.send_modal(modal)

    @byok.command(name="info", description="Check the guild's currently configured API key provider.")
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
               "This guild does not have a custom API key configured.", ephemeral=True if ctx.interaction else False
           )

    @byok.command(name="remove", description="Remove the guild's configured API key.")
    @app_commands.checks.has_permissions(administrator=True)
    async def byok_remove(self, ctx: commands.Context):
       """Removes the guild's API key."""
       success = await remove_guild_api_key(ctx.guild.id)
       response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
       if success:
           await response_func(
               "The guild's API key has been successfully removed.", ephemeral=True if ctx.interaction else False
           )
       else:
           await response_func(
               "This guild does not have an API key configured or an error occurred.",
               ephemeral=True if ctx.interaction else False,
           )

    @byok.command(name="copilot-login", description="Authenticate with GitHub Copilot for the guild.")
    @app_commands.checks.has_permissions(administrator=True)
    async def byok_copilot_login(self, ctx: commands.Context):
       """Initiates the GitHub Copilot device authentication flow for the guild."""
       await start_copilot_login(ctx, ctx.guild.id)


async def setup(bot: commands.Bot):
    """Loads the ModelManagementCog."""
    await bot.add_cog(ModelManagementCog(bot))
    print("ModelManagementCog has been loaded.")
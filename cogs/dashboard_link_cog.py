import discord
from discord.ext import commands

from lists import config


class DashboardLinkCog(commands.Cog):
    """Provides a command to link the dashboard."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.url = getattr(getattr(config, "Dashboard", None), "URL", None)

    @commands.hybrid_command(name="dashboard", description="Get the dashboard link")
    async def dashboard(self, ctx: commands.Context):
        """Send a button linking to the dashboard."""
        if not self.url:
            await ctx.send("Dashboard URL is not configured.", ephemeral=True if ctx.interaction else False)
            return
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Dashboard", url=self.url))
        if ctx.interaction:
            await ctx.interaction.response.send_message(
                "Use the button below to access the dashboard.", view=view, ephemeral=True
            )
        else:
            await ctx.send("Use the button below to access the dashboard.", view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DashboardLinkCog(bot))
    print("DashboardLinkCog has been loaded.")

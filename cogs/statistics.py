import discord
from discord.ext import commands
from discord import app_commands

class StatisticsCog(commands.Cog):
    """
    Cog that provides statistics about the bot, including server count and bot avatar.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(StatisticsCog(bot))
    pass

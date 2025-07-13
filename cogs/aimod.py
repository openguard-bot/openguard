from discord.ext import commands

# This file is deprecated. The functionality has been split into:
# - core_ai_cog.py
# - config_cog.py
# - model_management_cog.py
# - appeal_cog.py

# This setup function is kept to avoid breaking changes if other parts of the bot
# still try to load this cog. It now does nothing.
async def setup(bot: commands.Bot):
    """This cog is deprecated and no longer loads any functionality."""
    print("AIModerationCog is deprecated and is no longer loaded.")
    pass

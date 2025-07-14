# Test custom emojis for the app/bot

import asyncio
from discord.ext import commands
from lists import CustomEmoji

class EmojiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="emojis")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def emojis(self, ctx: commands.Context):
        """Iterates through all custom emojis and sends them."""
        for emoji_name, emoji_value in CustomEmoji.__dict__.items():
            if not emoji_name.startswith('__'):
                await ctx.send(emoji_value)
                await asyncio.sleep(1) # To avoid rate limits

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EmojiCog(bot))
# Test custom emojis for the app/bot

from discord.ext import commands
from lists import CustomEmoji


class EmojiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="emojis")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def emojis(self, ctx: commands.Context):
        """Sends all custom emojis in one message."""
        emojis = [
            str(emoji.value) for emoji in CustomEmoji
        ]
        if emojis:
            await ctx.send(" ".join(emojis))
        else:
            await ctx.send("No custom emojis found.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EmojiCog(bot))

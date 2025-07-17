# Test custom emojis for the app/bot

import os
import yaml
import re
from discord.ext import commands


class EmojiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.custom_emojis = {}
        self._load_emojis_from_config()

    def _load_emojis_from_config(self):
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "configs", "config.yaml"
        )
        with open(config_path, "r") as file:
            config_data = yaml.safe_load(file)
            if "CustomEmoji" in config_data:
                self.custom_emojis = config_data["CustomEmoji"]

    @commands.command(name="emojis")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def emojis(self, ctx: commands.Context):
        """Sends all custom emojis in one message."""
        if not self.custom_emojis:
            await ctx.send("No custom emojis configured.")
            return

        emoji_messages = []
        for emoji_name, emoji_str_or_id in self.custom_emojis.items():
            # Extract emoji ID if it's in the format "<:name:id>" or "<a:name:id>"
            emoji_id = None
            if isinstance(emoji_str_or_id, str):
                import re

                match = re.search(r":(\d+)>", emoji_str_or_id)
                if match:
                    emoji_id = int(match.group(1))
            elif isinstance(emoji_str_or_id, int):
                emoji_id = emoji_str_or_id

            if emoji_id:
                discord_emoji = self.bot.get_emoji(emoji_id)
                if discord_emoji:
                    emoji_messages.append(f"{emoji_name}: {discord_emoji}")
                else:
                    emoji_messages.append(f"{emoji_name}: Emoji not found")
            else:
                emoji_messages.append(f"{emoji_name}: Invalid emoji format")

        if emoji_messages:
            await ctx.send("Available Custom Emojis:\n" + "\n".join(emoji_messages))
        else:
            await ctx.send("No custom emojis found.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EmojiCog(bot))

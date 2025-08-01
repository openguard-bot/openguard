import discord
from discord.ext import commands

# List of authorized user IDs
AUTHORIZED_USERS = [
    1141746562922459136,
    452666956353503252
]

class BotStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """
        A local check that applies to all commands in this cog.
        Ensures that only authorized users can use these commands.
        """
        return ctx.author.id in AUTHORIZED_USERS

    @commands.group(name="status", invoke_without_command=True)
    async def status(self, ctx):
        """
        Sets the bot's universal status (playing/listening/watching).
        Usage: o!status [playing/listening/watching] [text]
        """
        await ctx.send("Invalid status type. Please use playing, listening, or watching.")

    @status.command(name="playing")
    async def status_playing(self, ctx, *, text: str):
        """Sets the bot's status to 'Playing' with the specified text."""
        activity = discord.Game(name=text)
        await self.bot.change_presence(activity=activity)
        await ctx.send(f"Bot status set to: Playing {text}")

    @status.command(name="listening")
    async def status_listening(self, ctx, *, text: str):
        """Sets the bot's status to 'Listening to' with the specified text."""
        activity = discord.Activity(type=discord.ActivityType.listening, name=text)
        await self.bot.change_presence(activity=activity)
        await ctx.send(f"Bot status set to: Listening to {text}")

    @status.command(name="watching")
    async def status_watching(self, ctx, *, text: str):
        """Sets the bot's status to 'Watching' with the specified text."""
        activity = discord.Activity(type=discord.ActivityType.watching, name=text)
        await self.bot.change_presence(activity=activity)
        await ctx.send(f"Bot status set to: Watching {text}")

    @commands.command(name="presence")
    async def presence(self, ctx, status_type: str):
        """
        Sets the bot's online presence (online/idle/dnd/offline).
        Usage: o!presence [online/idle/dnd/offline]
        """
        status_type = status_type.lower()
        if status_type == "online":
            await self.bot.change_presence(status=discord.Status.online)
            await ctx.send("Bot presence set to: Online")
        elif status_type == "idle":
            await self.bot.change_presence(status=discord.Status.idle)
            await ctx.send("Bot presence set to: Idle")
        elif status_type == "dnd" or status_type == "do-not-disturb":
            await self.bot.change_presence(status=discord.Status.dnd)
            await ctx.send("Bot presence set to: Do Not Disturb")
        elif status_type == "offline":
            await self.bot.change_presence(status=discord.Status.offline)
            await ctx.send("Bot presence set to: Offline")
        else:
            await ctx.send("Invalid presence type. Please use online, idle, dnd, or offline.")

async def setup(bot):
    await bot.add_cog(BotStatus(bot))
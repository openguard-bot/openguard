import discord
from discord.ext import commands
from discord import app_commands

class InfoCog(commands.Cog):
    """
    Cog that provides information about all /aimod commands when /aimodinfo help is used.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    aimodinfo_group = app_commands.Group(name="aimodinfo", description="AI Mod Info commands.")

    @aimodinfo_group.command(name="help", description="Show all /aimod commands and their descriptions.")
    async def aimodinfo_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="AI Moderation Bot - Command List",
            description="Here are all available `/aimod` commands:",
            color=discord.Color.blue()
        )
        embed.add_field(name="/aimod testlog", value="Send a test moderation log embed.", inline=False)
        embed.add_field(name="/aimod config logchannel", value="Set the moderation log channel.", inline=False)
        embed.add_field(name="/aimod config setlang", value="Set the language for bot responses in this guild.", inline=False)
        embed.add_field(name="/aimod config suggestionschannel", value="Set the suggestions channel.", inline=False)
        embed.add_field(name="/aimod config moderatorrole", value="Set the moderator role.", inline=False)
        embed.add_field(name="/aimod config suicidalpingrole", value="Set the role to ping for suicidal content.", inline=False)
        embed.add_field(name="/aimod config addnsfwchannel", value="Add a channel to the list of NSFW channels.", inline=False)
        embed.add_field(name="/aimod config removensfwchannel", value="Remove a channel from the list of NSFW channels.", inline=False)
        embed.add_field(name="/aimod config listnsfwchannels", value="List currently configured NSFW channels.", inline=False)
        embed.add_field(name="/aimod config enable", value="Enable or disable moderation for this guild.", inline=False)
        embed.add_field(name="/aimod infractions view", value="View a user's AI moderation infraction history.", inline=False)
        embed.add_field(name="/aimod infractions clear", value="Clear a user's AI moderation infraction history.", inline=False)
        embed.add_field(name="/aimod model set", value="Change the AI model used for moderation.", inline=False)
        embed.add_field(name="/aimod model get", value="View the current AI model used for moderation.", inline=False)
        embed.add_field(name="/aimod debug testmode", value="Enable or disable AI moderation test mode.", inline=False)
        embed.add_field(name="/aimod debug last_decisions", value="View the last 5 AI moderation decisions.", inline=False)
        embed.add_field(name="/aimod appeals appeal", value="Submit an appeal for a recent moderation action.", inline=False)
        embed.add_field(name="/pull_rules", value="Update the AI moderation rules for this guild from the rules channel.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCog(bot))

import discord
from discord.ext import commands
from discord import app_commands
import random


class DevsFacts(commands.Cog):
    """
    A cog that displays random facts about developers.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # List of developer names
        self.developers = ["slipstreamm", "ilikepancakes", "izzy"]

        # List of fact templates with placeholders
        self.fact_templates = [
            "{dev} has had {number} monster drinks today",
            "{dev} has written {number} lines of code this week",
            "{dev} has debugged {number} bugs in the last hour",
            "{dev} has consumed {number} cups of coffee today",
            "{dev} has pushed {number} commits to GitHub this month",
            "{dev} has spent {number} minutes staring at error messages today",
            "{dev} has googled 'how to fix' {number} times this week",
            "{dev} has {number} browser tabs open right now",
            "{dev} has restarted their IDE {number} times today",
            "{dev} has said 'it works on my machine' {number} times this month",
            "{dev} has {number} unfinished side projects",
            "{dev} has forgotten {number} semicolons today",
            "{dev} has blamed {number} issues on caching this week",
            "{dev} has {number} Stack Overflow tabs bookmarked",
            "{dev} has refactored the same function {number} times",
            "{dev} has {number} TODO comments in their code",
            "{dev} has spent {number} hours in meetings about coding instead of coding",
            "{dev} has {number} different versions of Node.js installed",
            "{dev} has {number} energy drinks in their fridge right now",
            "{dev} has typed 'console.log' {number} times today",
        ]

    @commands.hybrid_group(
        name="devs", description="Commands related to the developers"
    )
    async def devs(self, ctx: commands.Context):
        """Commands related to the developers."""
        await ctx.send_help(ctx.command)

    @devs.command(
        name="facts", description="Display a random fact about the developers"
    )
    async def devs_facts(self, ctx: commands.Context):
        """Display a random fact about one of the developers."""

        # Pick a random developer
        dev = random.choice(self.developers)

        # Pick a random fact template
        fact_template = random.choice(self.fact_templates)

        # Generate a random number (1 to 32-bit integer limit: 2,147,483,647)
        random_number = random.randint(1, 18446744073709551615)

        # Format the fact
        fact = fact_template.format(dev=dev, number=random_number)

        # Create an embed for better presentation
        embed = discord.Embed(
            title="🔍 Developer Fact", description=fact, color=discord.Color.blue()
        )

        # Add a footer with some flavor text
        embed.set_footer(text="*These facts are 100% scientifically accurate")

        # Handle both slash commands and regular commands
        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Load the DevsFacts cog."""
    await bot.add_cog(DevsFacts(bot))
    print("DevsFacts cog has been loaded.")

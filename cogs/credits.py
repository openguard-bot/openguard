import discord
from discord.ext import commands
from discord import app_commands


class CreditsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="aimodcredits", description="aimod credits")
    async def credits(self, ctx: commands.Context):
        embed = discord.Embed(
            title="AI Mod", description="W devs icl", color=discord.Color.blue()
        )
        embed.add_field(name="Developer", value="pancakes-proxy", inline=False)
        embed.add_field(name="Developer", value="slipstream", inline=False)
        embed.add_field(name="help from", value="izzy39", inline=False)
        embed.set_footer(text="Tuff")

        if ctx.interaction:
            await ctx.interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CreditsCog(bot))

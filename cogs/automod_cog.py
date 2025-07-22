import discord
from discord.ext import commands
from discord import app_commands
from .aimod_helpers import gemini_client


class AutoModCog(commands.Cog, name="Discord AutoMod"):
    """Commands to manage Discord AutoMod rules."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="automod", description="Manage Discord AutoMod rules")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @automod.command(name="list", description="List AutoMod rules")
    async def list_rules(self, ctx: commands.Context):
        rules = await ctx.guild.fetch_automod_rules()
        if not rules:
            await ctx.send("No AutoMod rules found.")
            return
        embed = discord.Embed(title="AutoMod Rules", color=discord.Color.blue())
        for rule in rules:
            embed.add_field(name=f"{rule.name} ({rule.id})", value=f"Trigger: {rule.trigger.type.name}", inline=False)
        await ctx.send(embed=embed)

    @automod.command(name="create", description="Create a simple regex AutoMod rule")
    @app_commands.describe(name="Rule name", regex="Regex pattern to match")
    async def create_rule(self, ctx: commands.Context, name: str, regex: str):
        trigger = discord.AutoModTrigger(
            type=discord.AutoModRuleTriggerType.keyword,
            regex_patterns=[regex],
        )
        action = discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)
        rule = await ctx.guild.create_automod_rule(
            name=name,
            event_type=discord.AutoModRuleEventType.message_send,
            trigger=trigger,
            actions=[action],
            enabled=True,
        )
        await ctx.send(f"Created AutoMod rule `{rule.name}` with ID `{rule.id}`")

    @automod.command(name="ai_create", description="Create a regex AutoMod rule using AI")
    @app_commands.describe(name="Rule name", description="Describe what the rule should block")
    async def ai_create(self, ctx: commands.Context, name: str, description: str):
        prompt = [
            {"role": "system", "content": "You create Discord AutoMod regex patterns. Return only the regex."},
            {"role": "user", "content": description},
        ]
        regex = await gemini_client.generate_content(prompt)
        trigger = discord.AutoModTrigger(
            type=discord.AutoModRuleTriggerType.keyword,
            regex_patterns=[regex.strip()],
        )
        action = discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)
        rule = await ctx.guild.create_automod_rule(
            name=name,
            event_type=discord.AutoModRuleEventType.message_send,
            trigger=trigger,
            actions=[action],
            enabled=True,
        )
        await ctx.send(f"Created AI rule `{rule.name}` with regex `{regex.strip()}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoModCog(bot))
    print("AutoModCog has been loaded.")

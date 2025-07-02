from discord.ext import commands
from discord import app_commands
import subprocess
class Shell(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='shell', aliases=['exec', 'cmd'])
    @commands.is_owner()
    async def shell_command(self, ctx: commands.Context, *, command: str):
        """Executes a shell command (Owner only)."""
        try:
            process = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            stdout = process.stdout
            stderr = process.stderr

            output = ""
            if stdout:
                output += f"**Stdout:**\n```\n{stdout}\n```"
            if stderr:
                output += f"**Stderr:**\n```\n{stderr}\n```"

            if not output:
                output = "Command executed successfully with no output."

            if len(output) > 2000:
                chunks = [output[i:i+1990] for i in range(0, len(output), 1990)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(output)

        except subprocess.CalledProcessError as e:
            await ctx.send(f"**Error executing command:**\n```\n{e}\n```\n**Stderr:**\n```\n{e.stderr}\n```")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: ```\n{e}\n```")


async def setup(bot: commands.Bot):
    await bot.add_cog(Shell(bot))

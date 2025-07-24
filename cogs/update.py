# pylint: disable=import-error
import discord
from discord.ext import commands
from discord import app_commands
import sys
import os
import asyncio
import pkg_resources
import re

from lists import config

# The user IDs that can run the update command
AUTHORIZED_USER_IDS = config.OwnersTuple


class UpdateCog(commands.Cog):
    """
    A Discord Cog that handles Git updates and bot restarts.
    Only authorized users can execute the update command.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("UpdateCog initialized.")

    @commands.command(name="aimod")
    async def aimod_command(self, ctx: commands.Context, subcommand: str = None):
        """Handle aimod commands. Usage: o!aimod [update|restart]"""

        if subcommand == "update":
            await self.update_bot_internal(ctx, force_restart=False)
        elif subcommand == "restart":
            await self.update_bot_internal(ctx, force_restart=True)
        else:
            await ctx.send(
                "❌ Invalid subcommand. Use `o!aimod update` to update the bot or `o!aimod restart` to force a restart."
            )
            return

    async def update_bot_internal(self, ctx: commands.Context, force_restart: bool = False):
        """Internal method to handle the bot update process."""
        if ctx.author.id not in AUTHORIZED_USER_IDS:
            await ctx.send("❌ You are not authorized to use this command.", ephemeral=True)
            return

        status_msg = await ctx.send("🔄 Starting bot update process...")
        embed = discord.Embed(
            title="🔄 Bot Update Started",
            description="Checking for updates...",
            color=discord.Color.blue(),
        )
        await status_msg.edit(embed=embed)

        try:
            # 1. Get pre-pull commit hash
            pre_pull_hash_result = await self._execute_git_command(["git", "rev-parse", "HEAD"])
            pre_pull_hash = pre_pull_hash_result["output"] if pre_pull_hash_result["success"] else None

            # 2. Execute git pull
            embed.description = "Pulling changes from the Git repository..."
            await status_msg.edit(embed=embed)
            git_result = await self._execute_git_pull()

            if not git_result["success"]:
                embed.title = "❌ Git Pull Failed"
                embed.description = f"```\n{git_result['error']}\n```"
                embed.color = discord.Color.red()
                await status_msg.edit(embed=embed)
                return

            if "Already up to date" in git_result["output"] and not force_restart:
                embed.title = "✅ Bot Already Up-to-Date"
                embed.description = "No new changes to pull from the repository."
                embed.color = discord.Color.green()
                await status_msg.edit(embed=embed)
                return

            # 3. Get post-pull commit hash and changed files
            post_pull_hash_result = await self._execute_git_command(["git", "rev-parse", "HEAD"])
            post_pull_hash = post_pull_hash_result["output"] if post_pull_hash_result["success"] else None

            changed_files = []
            if pre_pull_hash and post_pull_hash and pre_pull_hash != post_pull_hash:
                diff_result = await self._execute_git_command(
                    ["git", "diff", "--name-only", pre_pull_hash, post_pull_hash]
                )
                if diff_result["success"]:
                    changed_files = [f for f in diff_result["output"].strip().split("\n") if f]

            # 4. Check for dependency changes
            embed.description = "Checking for dependency changes..."
            await status_msg.edit(embed=embed)
            deps_result = await self._check_and_install_dependencies()

            # 5. Decide whether to restart or reload
            critical_files = ["bot.py", "pyproject.toml", "requirements.txt"]
            if force_restart or any(f in changed_files for f in critical_files):
                await self._perform_full_restart(status_msg, git_result, deps_result, changed_files, force_restart)
            else:
                await self._perform_cog_reload(status_msg, git_result, deps_result, changed_files)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Update Failed",
                description=f"An unexpected error occurred: {e}",
                color=discord.Color.red(),
            )
            await status_msg.edit(embed=error_embed)

    async def _execute_git_pull(self):
        """Execute git pull command and return results."""
        try:
            # Change to the bot's directory (should be the repo root)
            cwd = os.getcwd()

            # Execute git pull
            process = await asyncio.create_subprocess_exec(
                "git",
                "pull",
                "origin",
                "main",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8").strip() if stdout else "",
                "error": stderr.decode("utf-8").strip() if stderr else "",
                "return_code": process.returncode,
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Exception during git pull: {str(e)}",
                "return_code": -1,
            }

    async def _perform_cog_reload(self, status_msg, git_result, deps_result, changed_files):
        """Handle the cog reloading process and update the user."""
        embed = discord.Embed(title="🔄 Bot Update: Reloading Cogs", color=discord.Color.orange())

        cogs_to_reload = [
            f"cogs.{os.path.basename(f)[:-3]}" for f in changed_files if f.startswith("cogs/") and f.endswith(".py")
        ]

        if not cogs_to_reload:
            embed.title = "✅ Bot Update Complete"
            embed.description = "No cogs were changed. Nothing to reload."
            embed.color = discord.Color.green()
            await status_msg.edit(embed=embed)
            return

        reloaded_cogs, failed_cogs = await self._reload_cogs(cogs_to_reload)

        if not failed_cogs:
            embed.title = "✅ Bot Update Complete"
            embed.color = discord.Color.green()
            embed.description = "Successfully reloaded all changed cogs."
        else:
            embed.title = "⚠️ Bot Update Partially Complete"
            embed.color = discord.Color.orange()
            embed.description = "Some cogs failed to reload."

        if reloaded_cogs:
            embed.add_field(
                name="✅ Reloaded Cogs",
                value="```\n" + "\n".join(reloaded_cogs) + "\n```",
                inline=False,
            )

        if failed_cogs:
            failed_text = "\n".join([f"{name}: {err[:100]}" for name, err in failed_cogs])
            embed.add_field(
                name="❌ Failed Cogs",
                value="```\n" + failed_text + "\n```",
                inline=False,
            )

        await status_msg.edit(embed=embed)

    async def _perform_full_restart(self, status_msg, git_result, deps_result, changed_files, force_restart=False):
        """Handle the full bot restart process and update the user."""
        embed = discord.Embed(title="🔄 Bot Update: Restarting", color=discord.Color.orange())

        if force_restart:
            reason = "Restart was manually triggered."
        elif "requirements.txt" in changed_files:
            reason = "Dependencies were updated."
        else:
            reason = "A critical file was changed."

        embed.description = f"{reason} A full restart is required."

        embed.add_field(
            name="Git Pull",
            value=f"```\n{git_result['output'][:500]}\n```",
            inline=False,
        )

        if deps_result["missing_packages"]:
            status = "Successfully installed" if deps_result["install_success"] else "Failed to install"
            embed.add_field(
                name="Dependencies",
                value=f"{status} {len(deps_result['missing_packages'])} packages.",
                inline=False,
            )

        embed.add_field(name="Next Step", value="Restarting in 3 seconds...", inline=False)

        await status_msg.edit(embed=embed)
        await asyncio.sleep(3)

        final_embed = discord.Embed(
            title="🔄 Restarting Bot",
            description="Bot is now restarting...",
            color=discord.Color.red(),
        )
        await status_msg.edit(embed=final_embed)
        await self._restart_bot()

    async def _reload_cogs(self, cogs_to_reload):
        """Reloads a list of cogs and returns success/failure lists."""
        reloaded = []
        failed = []
        for cog_name in cogs_to_reload:
            try:
                await self.bot.reload_extension(cog_name)
                reloaded.append(cog_name)
            except commands.ExtensionError as e:
                failed.append((cog_name, str(e)))
        return reloaded, failed

    async def _restart_bot(self):
        """Gracefully close the bot and restart the process."""
        try:
            await self.bot.close()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"Error during restart: {e}")
            sys.exit(1)

    @commands.command(
        name="git_status",
        description="Check Git repository status (authorized users only).",
    )
    async def git_status(self, ctx: commands.Context):
        """Check the current Git status."""

        # Check if user is authorized
        if ctx.author.id not in AUTHORIZED_USER_IDS:
            await ctx.reply("❌ You are not authorized to use this command.", ephemeral=True)
            return
        async with ctx.typing():
            try:
                # Get git status
                status_result = await self._execute_git_command(["git", "status", "--porcelain"])
                branch_result = await self._execute_git_command(["git", "branch", "--show-current"])
                commit_result = await self._execute_git_command(["git", "log", "-1", "--oneline"])

                embed = discord.Embed(title="📊 Git Repository Status", color=discord.Color.blue())

                # Current branch
                if branch_result["success"]:
                    embed.add_field(
                        name="Current Branch",
                        value=f"`{branch_result['output'] or 'unknown'}`",
                        inline=True,
                    )

                # Latest commit
                if commit_result["success"]:
                    embed.add_field(
                        name="Latest Commit",
                        value=f"`{commit_result['output'] or 'unknown'}`",
                        inline=False,
                    )

                # Working directory status
                if status_result["success"]:
                    if status_result["output"]:
                        embed.add_field(
                            name="Working Directory",
                            value=f"⚠️ Uncommitted changes detected:\n```\n{status_result['output'][:500]}\n```",
                            inline=False,
                        )
                    else:
                        embed.add_field(
                            name="Working Directory",
                            value="✅ Clean (no uncommitted changes)",
                            inline=False,
                        )

                embed.add_field(
                    name="Repository",
                    value="git@github.com:Learnhelp-cc/aimod.git",
                    inline=False,
                )

                await ctx.reply(embed=embed)

            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Git Status Error",
                    description=f"Failed to get Git status: {str(e)}",
                    color=discord.Color.red(),
                )
                await ctx.reply(embed=error_embed)

    @app_commands.command(
        name="check_deps",
        description="Check for missing dependencies in requirements.txt (authorized users only).",
    )
    async def check_dependencies(self, ctx: commands.Context):
        """Check for missing dependencies without installing them."""

        # Check if user is authorized
        if ctx.author.id not in AUTHORIZED_USER_IDS:
            response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
            await response_func(
                "❌ You are not authorized to use this command.",
                ephemeral=True if ctx.interaction else False,
            )
            return

        if ctx.interaction:
            await ctx.interaction.response.defer()
        else:
            await ctx.defer()

        try:
            requirements_path = os.path.join(os.getcwd(), "requirements.txt")

            if not os.path.exists(requirements_path):
                embed = discord.Embed(
                    title="❌ Requirements Check",
                    description="requirements.txt file not found",
                    color=discord.Color.red(),
                )
                response_func = ctx.interaction.followup.send if ctx.interaction else ctx.send
                await response_func(embed=embed)
                return

            # Read and parse requirements
            with open(requirements_path, "r", encoding="utf-8") as f:
                requirements = f.read().strip().split("\n")

            installed_packages = {pkg.project_name.lower(): pkg.version for pkg in pkg_resources.working_set}
            missing_packages = []
            installed_count = 0

            for req_line in requirements:
                req_line = req_line.strip()
                if not req_line or req_line.startswith("#"):
                    continue

                # Parse package name
                package_name = re.split(r"[>=<~!]", req_line)[0].strip()

                if package_name.lower() not in installed_packages:
                    missing_packages.append(req_line)
                else:
                    installed_count += 1

            embed = discord.Embed(
                title="📦 Dependencies Check",
                color=(discord.Color.green() if not missing_packages else discord.Color.orange()),
            )

            embed.add_field(name="✅ Installed", value=f"{installed_count} packages", inline=True)

            embed.add_field(
                name="❌ Missing" if missing_packages else "✅ Missing",
                value=f"{len(missing_packages)} packages",
                inline=True,
            )

            if missing_packages:
                missing_text = "\n".join(missing_packages[:10])  # Show first 10
                if len(missing_packages) > 10:
                    missing_text += f"\n... and {len(missing_packages) - 10} more"

                embed.add_field(
                    name="Missing Packages",
                    value=f"```\n{missing_text}\n```",
                    inline=False,
                )

                embed.add_field(
                    name="💡 Tip",
                    value="Use `/update` to automatically install missing dependencies",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Status",
                    value="🎉 All dependencies are installed!",
                    inline=False,
                )

            response_func = ctx.interaction.followup.send if ctx.interaction else ctx.send
            await response_func(embed=embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Dependency Check Error",
                description=f"Failed to check dependencies: {str(e)}",
                color=discord.Color.red(),
            )
            response_func = ctx.interaction.followup.send if ctx.interaction else ctx.send
            await response_func(embed=error_embed)

    async def _execute_git_command(self, command):
        """Execute a git command and return results."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8").strip() if stdout else "",
                "error": stderr.decode("utf-8").strip() if stderr else "",
                "return_code": process.returncode,
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Exception: {str(e)}",
                "return_code": -1,
            }

    async def _check_and_install_dependencies(self):
        """Check requirements.txt and install missing dependencies."""
        try:
            requirements_path = os.path.join(os.getcwd(), "requirements.txt")

            if not os.path.exists(requirements_path):
                return {
                    "checked": False,
                    "missing_packages": [],
                    "install_success": False,
                    "install_output": "requirements.txt not found",
                }

            # Read requirements.txt
            with open(requirements_path, "r", encoding="utf-8") as f:
                requirements = f.read().strip().split("\n")

            # Parse requirements and check which are missing
            missing_packages = []
            installed_packages = {pkg.project_name.lower(): pkg.version for pkg in pkg_resources.working_set}

            for req_line in requirements:
                req_line = req_line.strip()
                if not req_line or req_line.startswith("#"):
                    continue

                # Parse package name (handle version specifiers)
                package_name = re.split(r"[>=<~!]", req_line)[0].strip()

                if package_name.lower() not in installed_packages:
                    missing_packages.append(req_line)

            if not missing_packages:
                return {
                    "checked": True,
                    "missing_packages": [],
                    "install_success": True,
                    "install_output": "All dependencies already installed",
                }

            # Install missing packages
            install_result = await self._install_packages(missing_packages)

            return {
                "checked": True,
                "missing_packages": missing_packages,
                "install_success": install_result["success"],
                "install_output": install_result["output"] + install_result["error"],
            }

        except Exception as e:
            return {
                "checked": False,
                "missing_packages": [],
                "install_success": False,
                "install_output": f"Exception during dependency check: {str(e)}",
            }

    async def _install_packages(self, packages):
        """Install packages using pip."""
        try:
            # Prepare pip install command
            cmd = [sys.executable, "-m", "pip", "install"] + packages

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8").strip() if stdout else "",
                "error": stderr.decode("utf-8").strip() if stderr else "",
                "return_code": process.returncode,
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Exception during package installation: {str(e)}",
                "return_code": -1,
            }


async def setup(bot: commands.Bot):
    await bot.add_cog(UpdateCog(bot))

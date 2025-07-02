import discord
from discord.ext import commands
from discord import app_commands
import subprocess
import sys
import os
import asyncio
import pkg_resources
import re

# The user IDs that can run the update command
AUTHORIZED_USER_IDS = (1141746562922459136, 452666956353503252)

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
        """Handle aimod commands. Usage: o!aimod update"""

        if subcommand != "update":
            await ctx.send("❌ Invalid subcommand. Use `o!aimod update` to update the bot.")
            return

        await self.update_bot_internal(ctx)

    async def update_bot_internal(self, ctx: commands.Context):
        """Internal method to handle the bot update process."""

        # Check if user is authorized
        if ctx.author.id not in AUTHORIZED_USER_IDS:
            await ctx.send(
                "❌ You are not authorized to use this command.",
                ephemeral=True
            )
            return

        # Send initial status message
        status_msg = await ctx.send("🔄 Starting bot update process...")

        try:
            # Create status embed
            embed = discord.Embed(
                title="🔄 Bot Update Started",
                description="Pulling from Git repository and restarting bot...",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Repository", 
                value="git@github.com:Learnhelp-cc/aimod.git", 
                inline=False
            )
            embed.add_field(
                name="Status",
                value="🔄 Pulling changes...",
                inline=False
            )

            await status_msg.edit(content=None, embed=embed)

            # Execute git pull
            git_result = await self._execute_git_pull()

            # Check and install dependencies
            deps_result = await self._check_and_install_dependencies()

            # Update embed with git and dependency results
            embed = discord.Embed(
                title="🔄 Bot Update Progress",
                description="Git pull and dependency check completed. Preparing to restart...",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Repository",
                value="git@github.com:Learnhelp-cc/aimod.git",
                inline=False
            )

            if git_result["success"]:
                embed.add_field(
                    name="✅ Git Pull Status",
                    value="Successfully pulled changes",
                    inline=False
                )
                if git_result["output"]:
                    # Truncate output if too long
                    output = git_result["output"]
                    if len(output) > 500:
                        output = output[:500] + "..."
                    embed.add_field(
                        name="Git Output",
                        value=f"```\n{output}\n```",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="⚠️ Git Pull Status",
                    value="Git pull encountered issues but continuing with restart",
                    inline=False
                )
                if git_result["error"]:
                    error = git_result["error"]
                    if len(error) > 500:
                        error = error[:500] + "..."
                    embed.add_field(
                        name="Git Error",
                        value=f"```\n{error}\n```",
                        inline=False
                    )

            # Add dependency check results
            if deps_result["checked"]:
                if deps_result["missing_packages"]:
                    if deps_result["install_success"]:
                        embed.add_field(
                            name="✅ Dependencies",
                            value=f"Installed {len(deps_result['missing_packages'])} missing packages",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="⚠️ Dependencies",
                            value="Some dependencies failed to install",
                            inline=False
                        )

                    if deps_result["install_output"]:
                        output = deps_result["install_output"]
                        if len(output) > 500:
                            output = output[:500] + "..."
                        embed.add_field(
                            name="Dependency Install Output",
                            value=f"```\n{output}\n```",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="✅ Dependencies",
                        value="All dependencies are up to date",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="⚠️ Dependencies",
                    value="Could not check dependencies",
                    inline=False
                )

            embed.add_field(
                name="Next Step",
                value="🔄 Restarting bot in 3 seconds...",
                inline=False
            )

            await status_msg.edit(embed=embed)

            # Wait a moment before restarting
            await asyncio.sleep(3)

            # Final message before restart
            final_embed = discord.Embed(
                title="🔄 Restarting Bot",
                description="Bot is restarting now. This may take a moment...",
                color=discord.Color.red()
            )
            final_embed.add_field(
                name="Status",
                value="🔄 Shutting down and restarting...",
                inline=False
            )

            await status_msg.edit(embed=final_embed)

            # Restart the bot
            await self._restart_bot()

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Update Failed",
                description="An error occurred during the update process.",
                color=discord.Color.red()
            )
            error_embed.add_field(
                name="Error",
                value=f"```\n{str(e)}\n```",
                inline=False
            )

            try:
                await status_msg.edit(embed=error_embed)
            except:
                # If we can't edit the message, try to send a new one
                await ctx.send(embed=error_embed)

    async def _execute_git_pull(self):
        """Execute git pull command and return results."""
        try:
            # Change to the bot's directory (should be the repo root)
            cwd = os.getcwd()
            
            # Execute git pull
            process = await asyncio.create_subprocess_exec(
                "git", "pull", "origin", "main",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8").strip() if stdout else "",
                "error": stderr.decode("utf-8").strip() if stderr else "",
                "return_code": process.returncode
            }
            
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Exception during git pull: {str(e)}",
                "return_code": -1
            }

    async def _restart_bot(self):
        """Restart the bot process."""
        try:
            # Close the bot connection gracefully
            await self.bot.close()
            
            # Restart the Python process
            # This will exit the current process and start a new one
            os.execv(sys.executable, [sys.executable] + sys.argv)
            
        except Exception as e:
            print(f"Error during restart: {e}")
            # If graceful restart fails, force exit
            sys.exit(1)

    @app_commands.command(name="git_status", description="Check Git repository status (authorized users only).")
    async def git_status(self, interaction: discord.Interaction):
        """Check the current Git status."""
        
        # Check if user is authorized
        if interaction.user.id not in AUTHORIZED_USER_IDS:
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.", 
                ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            # Get git status
            status_result = await self._execute_git_command(["git", "status", "--porcelain"])
            branch_result = await self._execute_git_command(["git", "branch", "--show-current"])
            commit_result = await self._execute_git_command(["git", "log", "-1", "--oneline"])
            
            embed = discord.Embed(
                title="📊 Git Repository Status",
                color=discord.Color.blue()
            )
            
            # Current branch
            if branch_result["success"]:
                embed.add_field(
                    name="Current Branch",
                    value=f"`{branch_result['output'] or 'unknown'}`",
                    inline=True
                )
            
            # Latest commit
            if commit_result["success"]:
                embed.add_field(
                    name="Latest Commit",
                    value=f"`{commit_result['output'] or 'unknown'}`",
                    inline=False
                )
            
            # Working directory status
            if status_result["success"]:
                if status_result["output"]:
                    embed.add_field(
                        name="Working Directory",
                        value=f"⚠️ Uncommitted changes detected:\n```\n{status_result['output'][:500]}\n```",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Working Directory",
                        value="✅ Clean (no uncommitted changes)",
                        inline=False
                    )
            
            embed.add_field(
                name="Repository",
                value="git@github.com:Learnhelp-cc/aimod.git",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Git Status Error",
                description=f"Failed to get Git status: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

    @app_commands.command(name="check_deps", description="Check for missing dependencies in requirements.txt (authorized users only).")
    async def check_dependencies(self, interaction: discord.Interaction):
        """Check for missing dependencies without installing them."""

        # Check if user is authorized
        if interaction.user.id not in AUTHORIZED_USER_IDS:
            await interaction.response.send_message(
                "❌ You are not authorized to use this command.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        try:
            requirements_path = os.path.join(os.getcwd(), "requirements.txt")

            if not os.path.exists(requirements_path):
                embed = discord.Embed(
                    title="❌ Requirements Check",
                    description="requirements.txt file not found",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)
                return

            # Read and parse requirements
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements = f.read().strip().split('\n')

            installed_packages = {pkg.project_name.lower(): pkg.version for pkg in pkg_resources.working_set}
            missing_packages = []
            installed_count = 0

            for req_line in requirements:
                req_line = req_line.strip()
                if not req_line or req_line.startswith('#'):
                    continue

                # Parse package name
                package_name = re.split(r'[>=<~!]', req_line)[0].strip()

                if package_name.lower() not in installed_packages:
                    missing_packages.append(req_line)
                else:
                    installed_count += 1

            embed = discord.Embed(
                title="📦 Dependencies Check",
                color=discord.Color.green() if not missing_packages else discord.Color.orange()
            )

            embed.add_field(
                name="✅ Installed",
                value=f"{installed_count} packages",
                inline=True
            )

            embed.add_field(
                name="❌ Missing" if missing_packages else "✅ Missing",
                value=f"{len(missing_packages)} packages",
                inline=True
            )

            if missing_packages:
                missing_text = "\n".join(missing_packages[:10])  # Show first 10
                if len(missing_packages) > 10:
                    missing_text += f"\n... and {len(missing_packages) - 10} more"

                embed.add_field(
                    name="Missing Packages",
                    value=f"```\n{missing_text}\n```",
                    inline=False
                )

                embed.add_field(
                    name="💡 Tip",
                    value="Use `/update` to automatically install missing dependencies",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Status",
                    value="🎉 All dependencies are installed!",
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Dependency Check Error",
                description=f"Failed to check dependencies: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

    async def _execute_git_command(self, command):
        """Execute a git command and return results."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8").strip() if stdout else "",
                "error": stderr.decode("utf-8").strip() if stderr else "",
                "return_code": process.returncode
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Exception: {str(e)}",
                "return_code": -1
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
                    "install_output": "requirements.txt not found"
                }

            # Read requirements.txt
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements = f.read().strip().split('\n')

            # Parse requirements and check which are missing
            missing_packages = []
            installed_packages = {pkg.project_name.lower(): pkg.version for pkg in pkg_resources.working_set}

            for req_line in requirements:
                req_line = req_line.strip()
                if not req_line or req_line.startswith('#'):
                    continue

                # Parse package name (handle version specifiers)
                package_name = re.split(r'[>=<~!]', req_line)[0].strip()

                if package_name.lower() not in installed_packages:
                    missing_packages.append(req_line)

            if not missing_packages:
                return {
                    "checked": True,
                    "missing_packages": [],
                    "install_success": True,
                    "install_output": "All dependencies already installed"
                }

            # Install missing packages
            install_result = await self._install_packages(missing_packages)

            return {
                "checked": True,
                "missing_packages": missing_packages,
                "install_success": install_result["success"],
                "install_output": install_result["output"] + install_result["error"]
            }

        except Exception as e:
            return {
                "checked": False,
                "missing_packages": [],
                "install_success": False,
                "install_output": f"Exception during dependency check: {str(e)}"
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
                cwd=os.getcwd()
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "output": stdout.decode("utf-8").strip() if stdout else "",
                "error": stderr.decode("utf-8").strip() if stderr else "",
                "return_code": process.returncode
            }

        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Exception during package installation: {str(e)}",
                "return_code": -1
            }

async def setup(bot: commands.Bot):
    await bot.add_cog(UpdateCog(bot))

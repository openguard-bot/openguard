# pylint: disable=import-error
import platform
import psutil
import discord
from discord.ext import commands
import asyncio
import time
import GPUtil
import distro

try:
    import wmi

    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


class HwInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="system", description="System related commands.")
    async def system(self, ctx: commands.Context):
        """System related commands."""
        await ctx.send_help(ctx.command)

    @system.command(name="check", description="Shows detailed system and bot information.")
    async def systemcheck(self, ctx: commands.Context):
        """Check the bot and system status."""
        if ctx.interaction:  # Check if it's an application command
            await ctx.interaction.response.defer(thinking=True)
        else:
            await ctx.defer()  # For prefix commands
        try:
            embed = await self._system_check_logic(ctx)  # Pass ctx
            if ctx.interaction:
                await ctx.interaction.followup.send(embed=embed)
            else:
                await ctx.send(embed=embed)  # For prefix commands
        except Exception as e:
            print(f"Error in systemcheck command: {e}")
            if ctx.interaction:
                await ctx.interaction.followup.send(f"An error occurred while checking system status: {e}")
            else:
                await ctx.send(f"An error occurred while checking system status: {e}")

    async def _system_check_logic(self, context_or_interaction):
        """Return detailed bot and system information as a Discord embed."""
        bot_user = self.bot.user
        guild_count = len(self.bot.guilds)

        user_ids = set()
        for guild in self.bot.guilds:
            try:
                for member in guild.members:
                    if not member.bot:
                        user_ids.add(member.id)
            except Exception as e:
                print(f"Error counting members in guild {guild.name}: {e}")
        user_count = len(user_ids)

        system = platform.system()
        os_info = f"{system} {platform.release()}"
        hostname = platform.node()
        distro_info_str = ""

        if system == "Linux":
            try:
                distro_name = distro.name(pretty=True)
                distro_info_str = f"\n**Distro:** {distro_name}"
            except ImportError:
                distro_info_str = "\n**Distro:** (Install 'distro' package for details)"
            except Exception as e:
                distro_info_str = f"\n**Distro:** (Error getting info: {e})"
        elif system == "Windows":
            try:
                win_ver = platform.version()
                win_build = platform.win32_ver()[1]
                os_info = f"Windows {win_ver} (Build {win_build})"
            except Exception as e:
                print(f"Could not get detailed Windows version: {e}")

        uptime_seconds = time.time() - psutil.boot_time()
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = ""
        if days > 0:
            uptime_str += f"{int(days)}d "
        uptime_str += f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        uptime = uptime_str.strip()

        cpu_usage = psutil.cpu_percent(interval=0.1)

        try:
            if platform.system() == "Windows":
                cpu_name_base = platform.processor()
            elif platform.system() == "Linux":
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        for line in f:
                            if line.startswith("model name"):
                                cpu_name_base = line.split(":")[1].strip()
                                break
                        else:
                            cpu_name_base = "Unknown CPU"
                except Exception:
                    cpu_name_base = platform.processor() or "Unknown CPU"
            else:
                cpu_name_base = platform.processor() or "Unknown CPU"

            physical_cores = psutil.cpu_count(logical=False)
            total_threads = psutil.cpu_count(logical=True)
            cpu_name = f"{cpu_name_base} ({physical_cores}C/{total_threads}T)"
        except Exception as e:
            print(f"Error getting CPU info: {e}")
            cpu_name = "N/A"

        motherboard_info = self._get_motherboard_info()

        memory = psutil.virtual_memory()
        ram_usage = f"{memory.used // (1024**2)} MB / {memory.total // (1024**2)} MB ({memory.percent}%)"

        gpu_info_lines = []
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                for gpu in gpus:
                    gpu_info_lines.append(
                        f"{gpu.name} ({gpu.load * 100:.1f}% Load, {gpu.memoryUsed:.0f}/{gpu.memoryTotal:.0f} MB VRAM)"
                    )
                gpu_info = "\n".join(gpu_info_lines)
            else:
                gpu_info = "No dedicated GPU detected by GPUtil."
        except ImportError:
            gpu_info = "GPUtil library not installed. Cannot get detailed GPU info."
        except Exception as e:
            print(f"Error getting GPU info via GPUtil: {e}")
            gpu_info = f"Error retrieving GPU info: {e}"

        if isinstance(context_or_interaction, commands.Context):
            user = context_or_interaction.author
            avatar_url = user.display_avatar.url
        elif isinstance(context_or_interaction, discord.Interaction):
            user = context_or_interaction.user
            avatar_url = user.display_avatar.url
        else:
            user = self.bot.user
            avatar_url = self.bot.user.display_avatar.url if self.bot.user else None

        embed = discord.Embed(title="📊 System Status", color=discord.Color.blue())
        if bot_user:
            embed.set_thumbnail(url=bot_user.display_avatar.url)

        if bot_user:
            embed.add_field(
                name="🤖 Bot Information",
                value=f"**Name:** {bot_user.name}\n"
                f"**ID:** {bot_user.id}\n"
                f"**Servers:** {guild_count}\n"
                f"**Unique Users:** {user_count}",
                inline=False,
            )
        else:
            embed.add_field(
                name="🤖 Bot Information",
                value="Bot user information not available.",
                inline=False,
            )

        embed.add_field(
            name="🖥️ System Information",
            value=f"**OS:** {os_info}{distro_info_str}\n**Hostname:** {hostname}\n**Uptime:** {uptime}",
            inline=False,
        )

        embed.add_field(
            name="⚙️ Hardware Information",
            value=f"**Device Model:** {motherboard_info}\n"
            f"**CPU:** {cpu_name}\n"
            f"**CPU Usage:** {cpu_usage}%\n"
            f"**RAM Usage:** {ram_usage}\n"
            f"**GPU Info:**\n{gpu_info}",
            inline=False,
        )

        if user:
            embed.set_footer(text=f"Requested by: {user.display_name}", icon_url=avatar_url)

        embed.timestamp = discord.utils.utcnow()
        return embed

    def _get_motherboard_info(self):
        """Get motherboard information based on the operating system."""
        system = platform.system()
        try:
            if system == "Windows":
                if WMI_AVAILABLE:
                    w = wmi.WMI()
                    for board in w.Win32_BaseBoard():
                        return f"{board.Manufacturer} {board.Product}"
                return "WMI module not available"
            elif system == "Linux":
                try:
                    with open("/sys/devices/virtual/dmi/id/product_name", "r") as f:
                        product_name = f.read().strip()
                    return product_name if product_name else "Unknown motherboard"
                except FileNotFoundError:
                    return "/sys/devices/virtual/dmi/id/product_name not found"
                except Exception as e:
                    return f"Error reading motherboard info: {e}"
            else:
                return f"Unsupported OS: {system}"
        except Exception as e:
            print(f"Error getting motherboard info: {e}")
            return "Error retrieving motherboard info"

    @system.command(
        name="temps",
        description="Runs the 'sensors' command and sends its output to chat.",
    )
    async def temps(self, ctx: commands.Context):
        """Executes the sensors command and returns the output."""
        try:
            process = await asyncio.create_subprocess_exec(
                "sensors",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode("utf-8").strip() or stderr.decode("utf-8").strip() or "No output."
        except Exception as e:
            output = f"Error executing sensors command: {e}"

        if len(output) > 1900:
            file_name = "temps.txt"
            with open(file_name, "w") as f:
                f.write(output)
            if ctx.interaction:
                await ctx.interaction.response.send_message(
                    "Output was too long; see attached file:",
                    file=discord.File(file_name),
                )
            else:
                await ctx.send(
                    "Output was too long; see attached file:",
                    file=discord.File(file_name),
                )
        else:
            if ctx.interaction:
                await ctx.interaction.response.send_message(f"```\n{output}\n```")
            else:
                await ctx.send(f"```\n{output}\n```")


async def setup(bot: commands.Bot):
    await bot.add_cog(HwInfo(bot))

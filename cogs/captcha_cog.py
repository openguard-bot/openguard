"""
Captcha Verification Cog for Discord Bot
Provides captcha verification using OpenCaptcha API with configurable settings.
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from database.operations import (
    get_captcha_config,
    set_captcha_config,
    update_captcha_config_field,
    get_captcha_attempt,
    update_captcha_attempt,
    reset_captcha_attempts,
)
from database.models import CaptchaConfig, CaptchaAttempt

log = logging.getLogger(__name__)


class CaptchaView(discord.ui.View):
    """View for captcha verification with buttons and input."""

    def __init__(self, cog, user: discord.Member, captcha_data: Dict[str, Any]):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user = user
        self.captcha_data = captcha_data
        self.captcha_id = captcha_data.get("id")

    @discord.ui.button(label="Solve Captcha", style=discord.ButtonStyle.primary, emoji="🔐")
    async def solve_captcha(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show modal for captcha solution input."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This captcha is not for you!", ephemeral=True)
            return

        modal = CaptchaModal(self.cog, self.user, self.captcha_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Get New Captcha", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def new_captcha(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Generate a new captcha."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This captcha is not for you!", ephemeral=True)
            return

        await interaction.response.defer()
        
        # Generate new captcha
        new_captcha_data = await self.cog.generate_captcha()
        if new_captcha_data:
            self.captcha_data = new_captcha_data
            self.captcha_id = new_captcha_data.get("id")
            
            embed = self.cog.create_captcha_embed(new_captcha_data)
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.followup.send("Failed to generate new captcha. Please try again.", ephemeral=True)


class CaptchaModal(discord.ui.Modal):
    """Modal for captcha solution input."""

    def __init__(self, cog, user: discord.Member, captcha_id: str):
        super().__init__(title="Solve Captcha")
        self.cog = cog
        self.user = user
        self.captcha_id = captcha_id

        self.solution = discord.ui.TextInput(
            label="Enter the text you see in the image:",
            placeholder="Type the captcha solution here...",
            required=True,
            max_length=50,
        )
        self.add_item(self.solution)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle captcha solution submission."""
        await interaction.response.defer(ephemeral=True)
        
        solution = self.solution.value.strip()
        result = await self.cog.verify_captcha(self.captcha_id, solution)
        
        if result:
            await self.cog.handle_successful_verification(interaction, self.user)
        else:
            await self.cog.handle_failed_verification(interaction, self.user)


class CaptchaCog(commands.Cog):
    """Captcha verification system using OpenCaptcha."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.opencaptcha_base_url = "https://api.opencaptcha.com/v1"
        print("CaptchaCog initialized.")

    async def cog_load(self):
        """Initialize HTTP session when cog loads."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        """Clean up HTTP session when cog unloads."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session is available."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    @commands.hybrid_group(name="captcha", description="Captcha verification commands.")
    async def captcha(self, ctx: commands.Context):
        """Captcha verification commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @captcha.command(name="enable", description="Enable captcha verification for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable_captcha(self, ctx: commands.Context):
        """Enable captcha verification system."""
        guild_id = ctx.guild.id
        
        # Get or create config
        config = await get_captcha_config(guild_id)
        if not config:
            config = CaptchaConfig(guild_id=guild_id, enabled=True)
        else:
            config.enabled = True
        
        success = await set_captcha_config(guild_id, config)
        
        if success:
            embed = discord.Embed(
                title="✅ Captcha Enabled",
                description="Captcha verification has been enabled for this server.\n\n"
                           "**Next steps:**\n"
                           "• Use `/captcha config roleset <role>` to set the verification role\n"
                           "• Use `/captcha config failverify <attempts> <punishment>` to configure failure handling\n"
                           "• Use `/captcha embed send <channel>` to send verification embed",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to enable captcha verification. Please try again.",
                color=discord.Color.red(),
            )
        
        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(embed=embed, ephemeral=False)

    @captcha.group(name="config", description="Configure captcha settings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def config(self, ctx: commands.Context):
        """Configure captcha settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @config.command(name="roleset", description="Set the role given after successful verification.")
    @app_commands.describe(role="The role to give users after they complete captcha verification")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_verification_role(self, ctx: commands.Context, role: discord.Role):
        """Set the verification role."""
        guild_id = ctx.guild.id
        
        success = await update_captcha_config_field(guild_id, "verification_role_id", role.id)
        
        if success:
            embed = discord.Embed(
                title="✅ Verification Role Set",
                description=f"Users will receive {role.mention} after completing captcha verification.",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to set verification role. Please try again.",
                color=discord.Color.red(),
            )
        
        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(embed=embed, ephemeral=False)

    @config.command(name="failverify", description="Configure what happens when users fail verification.")
    @app_commands.describe(
        attempts="Maximum number of attempts before punishment (1-10)",
        punishment="What to do when max attempts reached"
    )
    @app_commands.choices(punishment=[
        app_commands.Choice(name="Kick from server", value="kick"),
        app_commands.Choice(name="Ban from server", value="ban"),
        app_commands.Choice(name="Timeout (requires duration)", value="timeout"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def set_fail_verification(self, ctx: commands.Context, attempts: int, punishment: app_commands.Choice[str], timeout_duration: Optional[int] = None):
        """Configure failure verification settings."""
        guild_id = ctx.guild.id
        
        if not 1 <= attempts <= 10:
            embed = discord.Embed(
                title="❌ Invalid Input",
                description="Attempts must be between 1 and 10.",
                color=discord.Color.red(),
            )
            response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
            await response_func(embed=embed, ephemeral=True)
            return
        
        if punishment.value == "timeout" and (not timeout_duration or timeout_duration < 60):
            embed = discord.Embed(
                title="❌ Invalid Input",
                description="Timeout duration must be at least 60 seconds when using timeout punishment.",
                color=discord.Color.red(),
            )
            response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
            await response_func(embed=embed, ephemeral=True)
            return
        
        # Update config
        config = await get_captcha_config(guild_id)
        if not config:
            config = CaptchaConfig(guild_id=guild_id)
        
        config.max_attempts = attempts
        config.fail_action = punishment.value
        config.timeout_duration = timeout_duration if punishment.value == "timeout" else None
        
        success = await set_captcha_config(guild_id, config)
        
        if success:
            punishment_text = punishment.name
            if punishment.value == "timeout" and timeout_duration:
                punishment_text += f" for {timeout_duration} seconds"
            
            embed = discord.Embed(
                title="✅ Failure Settings Updated",
                description=f"**Max attempts:** {attempts}\n**Punishment:** {punishment_text}",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to update failure settings. Please try again.",
                color=discord.Color.red(),
            )
        
        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(embed=embed, ephemeral=False)

    @captcha.group(name="embed", description="Manage captcha verification embeds.")
    @app_commands.checks.has_permissions(administrator=True)
    async def embed_group(self, ctx: commands.Context):
        """Manage captcha verification embeds."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @embed_group.command(name="send", description="Send captcha verification embed to a channel.")
    @app_commands.describe(channel="The channel to send the verification embed to")
    @app_commands.checks.has_permissions(administrator=True)
    async def send_verification_embed(self, ctx: commands.Context, channel: discord.TextChannel):
        """Send verification embed to specified channel."""
        guild_id = ctx.guild.id

        # Check if captcha is enabled
        config = await get_captcha_config(guild_id)
        if not config or not config.enabled:
            embed = discord.Embed(
                title="❌ Captcha Not Enabled",
                description="Please enable captcha verification first using `/captcha enable`.",
                color=discord.Color.red(),
            )
            response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
            await response_func(embed=embed, ephemeral=True)
            return

        # Update verification channel in config
        await update_captcha_config_field(guild_id, "verification_channel_id", channel.id)

        # Create verification embed
        verification_embed = discord.Embed(
            title="🔐 Server Verification Required",
            description=(
                "Welcome to the server! To gain access, you need to complete a captcha verification.\n\n"
                "**How to verify:**\n"
                "1. Click the **Start Verification** button below\n"
                "2. Solve the captcha image that appears\n"
                "3. Enter your solution in the text box\n"
                "4. Get your verified role and access to the server!\n\n"
                "⚠️ **Note:** You have limited attempts, so look carefully at the image."
            ),
            color=discord.Color.blue(),
        )
        verification_embed.set_footer(text="Powered by OpenCaptcha")

        # Create verification view
        view = VerificationStartView(self)

        try:
            await channel.send(embed=verification_embed, view=view)

            success_embed = discord.Embed(
                title="✅ Verification Embed Sent",
                description=f"Captcha verification embed has been sent to {channel.mention}.",
                color=discord.Color.green(),
            )
        except discord.Forbidden:
            success_embed = discord.Embed(
                title="❌ Permission Error",
                description=f"I don't have permission to send messages in {channel.mention}.",
                color=discord.Color.red(),
            )
        except Exception as e:
            log.error(f"Failed to send verification embed: {e}")
            success_embed = discord.Embed(
                title="❌ Error",
                description="Failed to send verification embed. Please try again.",
                color=discord.Color.red(),
            )

        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(embed=success_embed, ephemeral=False)

    async def generate_captcha(self) -> Optional[Dict[str, Any]]:
        """Generate a new captcha using OpenCaptcha API."""
        session = await self._ensure_session()

        try:
            async with session.post(f"{self.opencaptcha_base_url}/generate") as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    log.error(f"OpenCaptcha API error: {response.status}")
                    return None
        except Exception as e:
            log.error(f"Failed to generate captcha: {e}")
            return None

    async def verify_captcha(self, captcha_id: str, solution: str) -> bool:
        """Verify captcha solution using OpenCaptcha API."""
        session = await self._ensure_session()

        try:
            payload = {
                "id": captcha_id,
                "solution": solution
            }

            async with session.post(f"{self.opencaptcha_base_url}/verify", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("success", False)
                else:
                    log.error(f"OpenCaptcha verify API error: {response.status}")
                    return False
        except Exception as e:
            log.error(f"Failed to verify captcha: {e}")
            return False

    def create_captcha_embed(self, captcha_data: Dict[str, Any]) -> discord.Embed:
        """Create embed for captcha challenge."""
        embed = discord.Embed(
            title="🔐 Captcha Verification",
            description="Please solve the captcha below to verify you're human.",
            color=discord.Color.blue(),
        )

        if "image_url" in captcha_data:
            embed.set_image(url=captcha_data["image_url"])

        embed.add_field(
            name="Instructions",
            value="Look at the image and enter the text you see in the input field.",
            inline=False,
        )

        embed.set_footer(text="This captcha will expire in 5 minutes.")
        return embed

    async def handle_successful_verification(self, interaction: discord.Interaction, user: discord.Member):
        """Handle successful captcha verification."""
        guild_id = interaction.guild.id

        # Mark as verified in database
        await update_captcha_attempt(guild_id, user.id, increment=False, verified=True)

        # Get config to assign role
        config = await get_captcha_config(guild_id)
        if config and config.verification_role_id:
            try:
                role = interaction.guild.get_role(config.verification_role_id)
                if role:
                    await user.add_roles(role, reason="Captcha verification completed")

                    embed = discord.Embed(
                        title="✅ Verification Successful!",
                        description=f"Congratulations! You have been verified and given the {role.mention} role.\n"
                                   "You now have access to the server!",
                        color=discord.Color.green(),
                    )
                else:
                    embed = discord.Embed(
                        title="✅ Verification Successful!",
                        description="You have been verified! However, the verification role could not be found.",
                        color=discord.Color.orange(),
                    )
            except discord.Forbidden:
                embed = discord.Embed(
                    title="✅ Verification Successful!",
                    description="You have been verified! However, I don't have permission to assign roles.",
                    color=discord.Color.orange(),
                )
        else:
            embed = discord.Embed(
                title="✅ Verification Successful!",
                description="You have been verified! No verification role is configured.",
                color=discord.Color.green(),
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    async def handle_failed_verification(self, interaction: discord.Interaction, user: discord.Member):
        """Handle failed captcha verification."""
        guild_id = interaction.guild.id

        # Update attempt count
        await update_captcha_attempt(guild_id, user.id, increment=True, verified=False)

        # Get current attempt count and config
        attempt_record = await get_captcha_attempt(guild_id, user.id)
        config = await get_captcha_config(guild_id)

        if not attempt_record or not config:
            embed = discord.Embed(
                title="❌ Verification Failed",
                description="Incorrect solution. Please try again.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        attempts_left = config.max_attempts - attempt_record.attempt_count

        if attempts_left <= 0:
            # Max attempts reached, apply punishment
            await self.apply_punishment(interaction, user, config)
        else:
            embed = discord.Embed(
                title="❌ Verification Failed",
                description=f"Incorrect solution. You have **{attempts_left}** attempt(s) remaining.\n"
                           "Please try again carefully.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    async def apply_punishment(self, interaction: discord.Interaction, user: discord.Member, config: CaptchaConfig):
        """Apply punishment for failed verification attempts."""
        try:
            if config.fail_action == "kick":
                await user.kick(reason="Failed captcha verification - maximum attempts exceeded")
                action_text = "kicked from the server"
            elif config.fail_action == "ban":
                await user.ban(reason="Failed captcha verification - maximum attempts exceeded")
                action_text = "banned from the server"
            elif config.fail_action == "timeout" and config.timeout_duration:
                timeout_until = datetime.now(timezone.utc) + timedelta(seconds=config.timeout_duration)
                await user.timeout(timeout_until, reason="Failed captcha verification - maximum attempts exceeded")
                action_text = f"timed out for {config.timeout_duration} seconds"
            else:
                action_text = "no action taken (invalid configuration)"

            embed = discord.Embed(
                title="❌ Maximum Attempts Exceeded",
                description=f"You have exceeded the maximum number of verification attempts and have been {action_text}.",
                color=discord.Color.red(),
            )

            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass  # User might be kicked/banned already

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Maximum Attempts Exceeded",
                description="You have exceeded the maximum number of verification attempts, but I don't have permission to apply punishment.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Failed to apply punishment: {e}")


class VerificationStartView(discord.ui.View):
    """View for starting verification process."""

    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog

    @discord.ui.button(label="Start Verification", style=discord.ButtonStyle.primary, emoji="🔐")
    async def start_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start the verification process for a user."""
        user = interaction.user
        guild_id = interaction.guild.id

        # Check if already verified
        attempt_record = await get_captcha_attempt(guild_id, user.id)
        if attempt_record and attempt_record.verified:
            embed = discord.Embed(
                title="✅ Already Verified",
                description="You have already completed verification!",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user has exceeded attempts
        config = await get_captcha_config(guild_id)
        if config and attempt_record and attempt_record.attempt_count >= config.max_attempts:
            embed = discord.Embed(
                title="❌ Maximum Attempts Exceeded",
                description="You have exceeded the maximum number of verification attempts.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Generate captcha
        captcha_data = await self.cog.generate_captcha()
        if not captcha_data:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to generate captcha. Please try again later.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Create captcha embed and view
        embed = self.cog.create_captcha_embed(captcha_data)
        view = CaptchaView(self.cog, user, captcha_data)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the CaptchaCog."""
    await bot.add_cog(CaptchaCog(bot))
    print("CaptchaCog has been loaded.")

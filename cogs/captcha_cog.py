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
import traceback
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from database.operations import (
    get_captcha_config,
    set_captcha_config,
    update_captcha_config_field,
    get_captcha_attempt,
    update_captcha_attempt,
    reset_captcha_attempts,
    store_verification_token,
    get_verification_token,
    validate_verification_token,
    cleanup_expired_tokens,
)
from database.models import CaptchaConfig, CaptchaAttempt

log = logging.getLogger(__name__)


async def send_error_dm(bot_instance, error_type, error_message, error_traceback=None, context_info=None):
    """Import the send_error_dm function from bot.py for error reporting."""
    # Import here to avoid circular imports
    from bot import send_error_dm as _send_error_dm
    await _send_error_dm(bot_instance, error_type, error_message, error_traceback, context_info)


class HCaptchaVerificationView(discord.ui.View):
    """View for hCaptcha verification with web interface."""

    def __init__(self, cog, user: discord.Member, verification_token: str):
        super().__init__(timeout=600)  # 10 minute timeout
        self.cog = cog
        self.user = user
        self.verification_token = verification_token

    @discord.ui.button(label="Complete Verification", style=discord.ButtonStyle.primary, emoji="🔐")
    async def complete_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open verification page in browser."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This verification is not for you!", ephemeral=True)
            return

        # Create verification URL using the backend endpoint
        base_url = os.getenv("BACKEND_URL", "https://openguard.lol")
        verification_url = f"{base_url}/api/verify?token={self.verification_token}&user={self.user.id}&guild={interaction.guild.id}"

        embed = discord.Embed(
            title="🔐 Complete Verification",
            description=(
                f"Click the link below to complete your verification:\n\n"
                f"[**Open Verification Page**]({verification_url})\n\n"
                f"**Instructions:**\n"
                f"1. Click the link above\n"
                f"2. Complete the hCaptcha challenge\n"
                f"3. Return here - you'll automatically get your role!\n\n"
                f"⚠️ **This link expires in 10 minutes**"
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Verification Token: {self.verification_token[:8]}...")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Enter hCaptcha Response", style=discord.ButtonStyle.secondary, emoji="📝")
    async def manual_response(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Allow manual entry of hCaptcha response token."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This verification is not for you!", ephemeral=True)
            return

        modal = HCaptchaResponseModal(self.cog, self.user)
        await interaction.response.send_modal(modal)


class HCaptchaResponseModal(discord.ui.Modal):
    """Modal for hCaptcha response token input."""

    def __init__(self, cog, user: discord.Member):
        super().__init__(title="Enter hCaptcha Response")
        self.cog = cog
        self.user = user

        self.response_token = discord.ui.TextInput(
            label="hCaptcha Response Token:",
            placeholder="Paste the hCaptcha response token here...",
            required=True,
            max_length=2000,
            style=discord.TextStyle.paragraph,
        )
        self.add_item(self.response_token)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle hCaptcha response token submission."""
        await interaction.response.defer(ephemeral=True)

        response_token = self.response_token.value.strip()

        # Verify the hCaptcha response
        result = await self.cog.verify_hcaptcha_response(response_token)

        if result:
            await self.cog.handle_successful_verification(interaction, self.user)
        else:
            await self.cog.handle_failed_verification(interaction, self.user)


class CaptchaCog(commands.Cog):
    """Captcha verification system using OpenCaptcha."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.hcaptcha_verify_url = "https://hcaptcha.com/siteverify"
        # You'll need to set these environment variables
        import os
        self.hcaptcha_secret = os.getenv("HCAPTCHA_SECRET_KEY")
        self.hcaptcha_site_key = os.getenv("HCAPTCHA_SITE_KEY")

        if not self.hcaptcha_secret:
            print("WARNING: HCAPTCHA_SECRET_KEY environment variable not set!")
        if not self.hcaptcha_site_key:
            print("WARNING: HCAPTCHA_SITE_KEY environment variable not set!")

        print("CaptchaCog initialized with hCaptcha.")

    async def cog_load(self):
        """Initialize HTTP session when cog loads."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()

        # Start cleanup task
        self.cleanup_task.start()

    async def cog_unload(self):
        """Clean up HTTP session when cog unloads."""
        if self.session and not self.session.closed:
            await self.session.close()

        # Stop cleanup task
        self.cleanup_task.cancel()

    @commands.loop(minutes=30)
    async def cleanup_task(self):
        """Periodic cleanup of expired verification tokens."""
        try:
            await cleanup_expired_tokens()
            log.info("Cleaned up expired verification tokens")
        except Exception as e:
            log.error(f"Error cleaning up expired tokens: {e}")

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

    @captcha.command(name="verify", description="Manually verify a user with hCaptcha response token.")
    @app_commands.describe(
        user="The user to verify",
        hcaptcha_response="The hCaptcha response token"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def manual_verify(self, ctx: commands.Context, user: discord.Member, hcaptcha_response: str):
        """Manually verify a user with hCaptcha response token."""
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

        # Verify the hCaptcha response
        result = await self.verify_hcaptcha_response(hcaptcha_response.strip())

        if result:
            # Mark as verified and assign role
            try:
                await update_captcha_attempt(guild_id, user.id, increment=False, verified=True)

                if config.verification_role_id:
                    role = ctx.guild.get_role(config.verification_role_id)
                    if role:
                        await user.add_roles(role, reason="Manual captcha verification by administrator")

                        embed = discord.Embed(
                            title="✅ User Verified",
                            description=f"{user.mention} has been successfully verified and given the {role.mention} role.",
                            color=discord.Color.green(),
                        )
                    else:
                        embed = discord.Embed(
                            title="✅ User Verified",
                            description=f"{user.mention} has been verified, but the verification role could not be found.",
                            color=discord.Color.orange(),
                        )
                else:
                    embed = discord.Embed(
                        title="✅ User Verified",
                        description=f"{user.mention} has been verified. No verification role is configured.",
                        color=discord.Color.green(),
                    )
            except Exception as e:
                log.error(f"Error in manual verification: {e}")
                embed = discord.Embed(
                    title="❌ Error",
                    description="Verification succeeded but there was an error assigning the role.",
                    color=discord.Color.red(),
                )
        else:
            embed = discord.Embed(
                title="❌ Verification Failed",
                description="The hCaptcha response token is invalid or expired.",
                color=discord.Color.red(),
            )

        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(embed=embed, ephemeral=False)

    async def verify_hcaptcha_response(self, hcaptcha_response: str, user_ip: Optional[str] = None) -> bool:
        """Verify hCaptcha response using hCaptcha API."""
        if not self.hcaptcha_secret:
            log.error("hCaptcha secret key not configured")
            return False

        session = await self._ensure_session()

        # Prepare verification payload
        payload = {
            "secret": self.hcaptcha_secret,
            "response": hcaptcha_response,
        }

        if user_ip:
            payload["remoteip"] = user_ip

        try:
            async with session.post(self.hcaptcha_verify_url, data=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    success = data.get("success", False)

                    if not success:
                        error_codes = data.get("error-codes", [])
                        log.warning(f"hCaptcha verification failed: {error_codes}")

                        # Report specific hCaptcha errors
                        error_context = (
                            f"hCaptcha Verification Failed - "
                            f"Error codes: {error_codes}, "
                            f"Response: {data}"
                        )

                        await send_error_dm(
                            self.bot,
                            error_type="hCaptchaVerificationFailed",
                            error_message=f"hCaptcha verification failed with error codes: {error_codes}",
                            error_traceback=None,
                            context_info=error_context,
                        )

                    return success
                else:
                    # Detailed error reporting for API errors
                    error_text = await response.text()
                    error_context = (
                        f"hCaptcha API Error - Status: {response.status}, "
                        f"URL: {self.hcaptcha_verify_url}, "
                        f"Response: {error_text[:500]}..."
                    )

                    await send_error_dm(
                        self.bot,
                        error_type="hCaptchaAPIError",
                        error_message=f"Failed to verify hCaptcha - HTTP {response.status}",
                        error_traceback=None,
                        context_info=error_context,
                    )

                    log.error(f"hCaptcha API error: {response.status} - {error_text}")
                    return False
        except aiohttp.ClientError as e:
            # Network/connection errors
            tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_context = (
                f"hCaptcha Network Error - URL: {self.hcaptcha_verify_url}, "
                f"Error Type: {type(e).__name__}"
            )

            await send_error_dm(
                self.bot,
                error_type="hCaptchaNetworkError",
                error_message=str(e),
                error_traceback=tb_string,
                context_info=error_context,
            )

            log.error(f"Network error verifying hCaptcha: {e}")
            return False
        except Exception as e:
            # Unexpected errors
            tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_context = (
                f"Unexpected error in hCaptcha verification - URL: {self.hcaptcha_verify_url}"
            )

            await send_error_dm(
                self.bot,
                error_type=type(e).__name__,
                error_message=str(e),
                error_traceback=tb_string,
                context_info=error_context,
            )

            log.error(f"Unexpected error verifying hCaptcha: {e}")
            return False

    def get_hcaptcha_site_key(self) -> Optional[str]:
        """Get the hCaptcha site key for embedding."""
        return self.hcaptcha_site_key

    async def create_verification_endpoint(self, guild_id: int, user_id: int, verification_token: str) -> bool:
        """Store verification token for later validation."""
        try:
            # Store in database with expiration (10 minutes)
            from datetime import datetime, timezone, timedelta
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

            # You could store this in the database or Redis
            # For now, we'll just log it
            log.info(f"Created verification token {verification_token} for user {user_id} in guild {guild_id}, expires at {expires_at}")
            return True
        except Exception as e:
            log.error(f"Failed to create verification endpoint: {e}")
            return False

    def create_hcaptcha_embed(self, verification_token: str) -> discord.Embed:
        """Create embed for hCaptcha verification."""
        embed = discord.Embed(
            title="🔐 hCaptcha Verification Required",
            description=(
                "To complete verification, you need to solve an hCaptcha challenge.\n\n"
                "**Choose one of the options below:**\n"
                "• **Complete Verification** - Opens a web page with hCaptcha\n"
                "• **Enter Response** - Manually enter hCaptcha response token\n\n"
                "⚠️ **Note:** You must complete this within 10 minutes."
            ),
            color=discord.Color.blue(),
        )

        if self.hcaptcha_site_key:
            embed.add_field(
                name="Site Key",
                value=f"`{self.hcaptcha_site_key}`",
                inline=False,
            )

        embed.add_field(
            name="Verification Token",
            value=f"`{verification_token}`",
            inline=False,
        )

        embed.set_footer(text="Powered by hCaptcha • This verification will expire in 10 minutes")
        return embed

    async def handle_successful_verification(self, interaction: discord.Interaction, user: discord.Member):
        """Handle successful captcha verification."""
        guild_id = interaction.guild.id

        # Mark as verified in database
        try:
            await update_captcha_attempt(guild_id, user.id, increment=False, verified=True)
        except Exception as e:
            # Report database error but continue with role assignment
            tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_context = (
                f"Database error marking user as verified - Guild: {guild_id}, "
                f"User: {user.id} ({user})"
            )

            await send_error_dm(
                self.bot,
                error_type=type(e).__name__,
                error_message=str(e),
                error_traceback=tb_string,
                context_info=error_context,
            )

            log.error(f"Database error marking user {user.id} as verified: {e}")

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
        try:
            await update_captcha_attempt(guild_id, user.id, increment=True, verified=False)
        except Exception as e:
            # Report database error
            tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_context = (
                f"Database error updating failed attempt - Guild: {guild_id}, "
                f"User: {user.id} ({user})"
            )

            await send_error_dm(
                self.bot,
                error_type=type(e).__name__,
                error_message=str(e),
                error_traceback=tb_string,
                context_info=error_context,
            )

            log.error(f"Database error updating failed attempt for user {user.id}: {e}")

        # Get current attempt count and config
        try:
            attempt_record = await get_captcha_attempt(guild_id, user.id)
            config = await get_captcha_config(guild_id)
        except Exception as e:
            # Report database error
            tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            error_context = (
                f"Database error retrieving captcha data - Guild: {guild_id}, "
                f"User: {user.id} ({user})"
            )

            await send_error_dm(
                self.bot,
                error_type=type(e).__name__,
                error_message=str(e),
                error_traceback=tb_string,
                context_info=error_context,
            )

            log.error(f"Database error retrieving captcha data for user {user.id}: {e}")

            # Fallback response
            embed = discord.Embed(
                title="❌ Verification Failed",
                description="Incorrect solution and database error occurred. Please contact administrators.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

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

        # Generate a unique verification token for this user
        import uuid
        verification_token = str(uuid.uuid4())

        # Store the verification token in database with 10 minute expiration
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        success = await store_verification_token(guild_id, user.id, verification_token, expires_at)

        if not success:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to create verification session. Please try again.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Create hCaptcha embed and view
        embed = self.cog.create_hcaptcha_embed(verification_token)
        view = HCaptchaVerificationView(self.cog, user, verification_token)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the CaptchaCog."""
    await bot.add_cog(CaptchaCog(bot))
    print("CaptchaCog has been loaded.")

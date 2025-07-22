"""
Captcha Verification Cog for Discord Bot
Provides captcha verification using locally generated images.
"""

import discord
from discord.ext import commands, tasks
from discord import app_commands

# pylint: disable=no-member
import logging
import traceback
import io
import random
from typing import Optional
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

from database.operations import (
    get_captcha_config,
    set_captcha_config,
    update_captcha_config_field,
    get_captcha_attempt,
    update_captcha_attempt,
)
from database.models import CaptchaConfig

log = logging.getLogger(__name__)


async def send_error_dm(bot_instance, error_type, error_message, error_traceback=None, context_info=None):
    """Import the send_error_dm function from bot.py for error reporting."""
    # Import here to avoid circular imports
    from bot import send_error_dm as _send_error_dm

    await _send_error_dm(bot_instance, error_type, error_message, error_traceback, context_info)


class LocalCaptchaGenerator:
    """Generate captcha images locally using PIL."""

    def __init__(self):
        self.width = 200
        self.height = 80
        self.font_size = 24

    def generate_captcha_text(self, length: int = 5) -> str:
        """Generate random captcha text."""
        # Use only uppercase letters and numbers, avoiding confusing characters
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return "".join(random.choice(chars) for _ in range(length))

    def generate_captcha_image(self, text: str) -> io.BytesIO:
        """Generate a captcha image with the given text."""
        # Create image with white background
        image = Image.new("RGB", (self.width, self.height), "white")
        draw = ImageDraw.Draw(image)

        # Try to use a built-in font, fallback to default if not available
        try:
            # Try to load a system font
            font = ImageFont.truetype("arial.ttf", self.font_size)
        except (OSError, IOError):
            try:
                # Try alternative font names
                font = ImageFont.truetype("DejaVuSans.ttf", self.font_size)
            except (OSError, IOError):
                # Use default font as fallback
                font = ImageFont.load_default()

        # Add some noise lines
        for _ in range(random.randint(3, 6)):
            x1, y1 = random.randint(0, self.width), random.randint(0, self.height)
            x2, y2 = random.randint(0, self.width), random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill=random.choice(["gray", "lightgray", "darkgray"]), width=1)

        # Calculate text position to center it
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2

        # Draw each character with slight random positioning and rotation
        char_x = x
        for char in text:
            # Add slight random offset
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)

            # Random color (dark colors for visibility)
            color = random.choice(["black", "darkblue", "darkred", "darkgreen", "purple"])

            draw.text((char_x + offset_x, y + offset_y), char, font=font, fill=color)

            # Move to next character position
            char_bbox = draw.textbbox((0, 0), char, font=font)
            char_width = char_bbox[2] - char_bbox[0]
            char_x += char_width + random.randint(2, 8)

        # Add some noise dots
        for _ in range(random.randint(20, 40)):
            x, y = random.randint(0, self.width), random.randint(0, self.height)
            draw.point((x, y), fill=random.choice(["gray", "lightgray"]))

        # Save to BytesIO
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        return img_buffer


class CaptchaVerificationView(discord.ui.View):
    """View for local captcha verification."""

    def __init__(self, cog, user: discord.Member, captcha_id: str):
        super().__init__(timeout=600)  # 10 minute timeout
        self.cog = cog
        self.user = user
        self.captcha_id = captcha_id

    @discord.ui.button(label="Enter Solution", style=discord.ButtonStyle.primary, emoji="✏️")
    async def enter_solution(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open modal for captcha solution input."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This verification is not for you!", ephemeral=True)
            return

        modal = CaptchaSolutionModal(self.cog, self.user, self.captcha_id)
        await interaction.response.send_modal(modal)


class CaptchaSolutionModal(discord.ui.Modal):
    """Modal for captcha solution input."""

    def __init__(self, cog, user: discord.Member, captcha_id: str):
        super().__init__(title="Enter Captcha Solution")
        self.cog = cog
        self.user = user
        self.captcha_id = captcha_id

        self.solution = discord.ui.TextInput(
            label="Enter the text from the image:",
            placeholder="Type what you see in the captcha image...",
            required=True,
            max_length=10,
            style=discord.TextStyle.short,
        )
        self.add_item(self.solution)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle captcha solution submission."""
        await interaction.response.defer(ephemeral=True)

        user_solution = self.solution.value.strip().upper()

        # Get the correct solution from database
        correct_solution = await self.cog.get_captcha_solution(self.captcha_id)

        if not correct_solution:
            embed = discord.Embed(
                title="❌ Captcha Expired",
                description="This captcha has expired. Please start verification again.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Verify the solution
        if user_solution == correct_solution.upper():
            await self.cog.handle_successful_verification(interaction, self.user)
            # Clean up the captcha from database
            await self.cog.cleanup_captcha(self.captcha_id)
        else:
            await self.cog.handle_failed_verification(interaction, self.user)
            # Clean up the captcha from database
            await self.cog.cleanup_captcha(self.captcha_id)


class CaptchaCog(commands.Cog):
    """Captcha verification system using locally generated images."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.captcha_generator = LocalCaptchaGenerator()
        print("CaptchaCog initialized with local captcha generation.")

    async def cog_load(self):
        """Initialize when cog loads."""
        # Start cleanup task
        self.cleanup_task.start()

    async def cog_unload(self):
        """Clean up when cog unloads."""
        # Stop cleanup task
        self.cleanup_task.cancel()

    @tasks.loop(minutes=30)
    async def cleanup_task(self):
        """Periodic cleanup of expired captcha data."""
        try:
            await self._cleanup_expired_captchas()
            log.info("Cleaned up expired captcha data")
        except Exception as e:
            log.error(f"Error cleaning up expired captchas: {e}")

    async def store_captcha(
        self, guild_id: int, user_id: int, captcha_id: str, captcha_text: str, expires_at: datetime
    ) -> bool:
        """Store a captcha solution with expiration."""
        try:
            from database.connection import execute_query

            await execute_query(
                """INSERT INTO captcha_solutions (guild_id, user_id, captcha_id, solution, expires_at)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (guild_id, user_id)
                   DO UPDATE SET captcha_id = $3, solution = $4, expires_at = $5, created_at = CURRENT_TIMESTAMP""",
                guild_id,
                user_id,
                captcha_id,
                captcha_text,
                expires_at,
            )
            return True
        except Exception as e:
            log.error(f"Failed to store captcha for user {user_id} in guild {guild_id}: {e}")
            return False

    async def get_captcha_solution(self, captcha_id: str) -> Optional[str]:
        """Get captcha solution by ID."""
        try:
            from database.connection import execute_query

            result = await execute_query(
                "SELECT solution FROM captcha_solutions WHERE captcha_id = $1 AND expires_at > CURRENT_TIMESTAMP",
                captcha_id,
                fetch_one=True,
            )
            return result["solution"] if result else None
        except Exception as e:
            log.error(f"Failed to get captcha solution for {captcha_id}: {e}")
            return None

    async def cleanup_captcha(self, captcha_id: str) -> bool:
        """Clean up a specific captcha by ID."""
        try:
            from database.connection import execute_query

            await execute_query("DELETE FROM captcha_solutions WHERE captcha_id = $1", captcha_id)
            return True
        except Exception as e:
            log.error(f"Failed to cleanup captcha {captcha_id}: {e}")
            return False

    async def _cleanup_expired_captchas(self) -> bool:
        """Clean up expired captcha solutions."""
        try:
            from database.connection import execute_query

            await execute_query("DELETE FROM captcha_solutions WHERE expires_at <= CURRENT_TIMESTAMP")
            return True
        except Exception as e:
            log.error(f"Failed to cleanup expired captchas: {e}")
            return False

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

    @config.command(
        name="failverify",
        description="Configure what happens when users fail verification.",
    )
    @app_commands.describe(
        attempts="Maximum number of attempts before punishment (1-10)",
        punishment="What to do when max attempts reached",
    )
    @app_commands.choices(
        punishment=[
            app_commands.Choice(name="Kick from server", value="kick"),
            app_commands.Choice(name="Ban from server", value="ban"),
            app_commands.Choice(name="Timeout (requires duration)", value="timeout"),
        ]
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_fail_verification(
        self,
        ctx: commands.Context,
        attempts: int,
        punishment: app_commands.Choice[str],
        timeout_duration: Optional[int] = None,
    ):
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
                "2. Look at the captcha image that appears\n"
                "3. Enter the text you see in the image\n"
                "4. Get your verified role and access to the server!\n\n"
                "⚠️ **Note:** You have limited attempts, so look carefully at the image."
            ),
            color=discord.Color.blue(),
        )
        verification_embed.set_footer(text="OpenGuard Captcha Verification")

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

    @captcha.command(
        name="verify",
        description="Manually verify a user (admin only).",
    )
    @app_commands.describe(user="The user to verify")
    @app_commands.checks.has_permissions(administrator=True)
    async def manual_verify(self, ctx: commands.Context, user: discord.Member):
        """Manually verify a user (admin bypass)."""
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
                description="There was an error during verification.",
                color=discord.Color.red(),
            )

        response_func = ctx.interaction.response.send_message if ctx.interaction else ctx.send
        await response_func(embed=embed, ephemeral=False)

    async def generate_captcha_for_user(self, guild_id: int, user_id: int) -> tuple[discord.File, str]:
        """Generate a captcha image for a user and return the file and captcha ID."""
        try:
            # Generate captcha text and image
            captcha_text = self.captcha_generator.generate_captcha_text()
            captcha_image = self.captcha_generator.generate_captcha_image(captcha_text)

            # Generate unique captcha ID
            import uuid

            captcha_id = str(uuid.uuid4())

            # Store captcha solution in database with 10 minute expiration
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            await self.store_captcha(guild_id, user_id, captcha_id, captcha_text, expires_at)

            # Create Discord file
            captcha_file = discord.File(captcha_image, filename=f"captcha_{captcha_id}.png")

            return captcha_file, captcha_id

        except Exception as e:
            log.error(f"Failed to generate captcha for user {user_id}: {e}")
            raise

    def create_captcha_embed(self, captcha_id: str) -> discord.Embed:
        """Create embed for local captcha verification."""
        embed = discord.Embed(
            title="🔐 Captcha Verification Required",
            description=(
                "Please look at the image below and enter the text you see.\n\n"
                "**Instructions:**\n"
                "• Look carefully at the captcha image\n"
                "• Enter the text exactly as you see it\n"
                "• Click **Enter Solution** when ready\n\n"
                "⚠️ **Note:** This captcha will expire in 10 minutes."
            ),
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="Tips",
            value="• The text is case-insensitive\n• Look for letters and numbers\n• Ignore background noise",
            inline=False,
        )

        embed.set_footer(text="Powered by Local Captcha Generation • This verification will expire in 10 minutes")
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
            error_context = f"Database error marking user as verified - Guild: {guild_id}, User: {user.id} ({user})"

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
            error_context = f"Database error updating failed attempt - Guild: {guild_id}, User: {user.id} ({user})"

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
            error_context = f"Database error retrieving captcha data - Guild: {guild_id}, User: {user.id} ({user})"

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

    async def apply_punishment(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        config: CaptchaConfig,
    ):
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
                await user.timeout(
                    timeout_until,
                    reason="Failed captcha verification - maximum attempts exceeded",
                )
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
            except Exception:
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

        try:
            # Generate captcha image and get captcha ID
            captcha_file, captcha_id = await self.cog.generate_captcha_for_user(guild_id, user.id)

            # Create captcha embed and view
            embed = self.cog.create_captcha_embed(captcha_id)
            view = CaptchaVerificationView(self.cog, user, captcha_id)

            await interaction.followup.send(embed=embed, file=captcha_file, view=view, ephemeral=True)

        except Exception as e:
            log.error(f"Failed to generate captcha for user {user.id}: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to generate captcha. Please try again.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Load the CaptchaCog."""
    await bot.add_cog(CaptchaCog(bot))
    print("CaptchaCog has been loaded.")

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from datetime import datetime, timezone

# Import database operations
from database.operations import get_user_data, set_user_data, update_user_data_field
from lists import CustomEmoji


class UserInfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.developer_badges = {
            1141746562922459136: f"{CustomEmoji.STAFF_BLUE}OpenGuard Developer",
            452666956353503252: f"{CustomEmoji.STAFF_PINK}OpenGuard Developer",
        }
        # Legacy variables for compatibility
        self.custom_data_file = "user_data.json"
        self.custom_user_data = {}

    def _truncate_field_value(self, text: str, max_length: int = 1020) -> str:
        """Truncate text to fit Discord embed field limits."""
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text

    def _format_time_difference(self, past_time: datetime) -> str:
        """Calculate and format the time difference from a past datetime to now."""
        now = datetime.now(timezone.utc)
        # Ensure past_time is timezone-aware
        if past_time.tzinfo is None:
            past_time = past_time.replace(tzinfo=timezone.utc)

        diff = now - past_time

        # Calculate total minutes
        total_minutes = int(diff.total_seconds() / 60)

        # Calculate years, days, hours, minutes
        years = total_minutes // (365 * 24 * 60)
        remaining_minutes = total_minutes % (365 * 24 * 60)

        days = remaining_minutes // (24 * 60)
        remaining_minutes = remaining_minutes % (24 * 60)

        hours = remaining_minutes // 60
        minutes = remaining_minutes % 60

        # Build the formatted string
        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        if not parts:
            return "Less than a minute"

        return ", ".join(parts)

    async def load_custom_data(self):
        """Legacy function - now a no-op since data is loaded from database."""
        pass

    async def save_custom_data(self):
        """Legacy function - now a no-op since data is saved directly to database."""
        pass

    async def get_custom_user_data(self, user_id):
        """Get custom user data from database."""
        try:
            return await get_user_data(user_id)
        except Exception as e:
            print(f"Failed to get user data for user {user_id}: {e}")
            return {}

    async def set_custom_user_value(self, user_id, key, value):
        """Set a custom user value in the database."""
        try:
            return await update_user_data_field(user_id, key, value)
        except Exception as e:
            print(f"Failed to set custom user value for user {user_id}: {e}")
            return False

    async def remove_custom_user_value(self, user_id, key):
        """Remove a custom user value from the database."""
        try:
            current_data = await get_user_data(user_id)
            if key in current_data:
                del current_data[key]
                await set_user_data(user_id, current_data)
                return True
            return False
        except Exception as e:
            print(f"Failed to remove custom user value for user {user_id}: {e}")
            return False

    async def is_authorized_admin(self, ctx: commands.Context):
        return ctx.author.guild_permissions.administrator

    @commands.hybrid_command(
        name="aboutuser",
        description="Display comprehensive info about a user or yourself.",
    )
    @app_commands.describe(user="The user to get info about (optional)")
    async def aboutuser(
        self, ctx: commands.Context, user: Optional[discord.Member] = None
    ):
        member = user or ctx.author
        if ctx.guild:
            member = ctx.guild.get_member(member.id) or member
        user_obj = member._user if hasattr(member, "_user") else member
        banner_url = None
        try:
            user_obj = await self.bot.fetch_user(member.id)
            if user_obj.banner:
                banner_url = user_obj.banner.url
        except Exception:
            pass
        user_data = {
            "member": member,
            "user_obj": user_obj,
            "banner_url": banner_url,
            "is_guild_member": isinstance(member, discord.Member) and ctx.guild,
            "interaction_user_id": ctx.author.id,
        }
        embed, view = await self._create_main_view(user_data)
        await ctx.reply(embed=embed, view=view)

    async def _create_main_view(self, user_data):
        member = user_data["member"]
        user_obj = user_data["user_obj"]
        banner_url = user_data["banner_url"]
        is_guild_member = user_data["is_guild_member"]
        status = "Unknown"
        device_str = "Unknown"
        if is_guild_member:
            status = str(member.status).title()
            if member.desktop_status != "offline":
                device_str = "Desktop"
            elif member.mobile_status != "offline":
                device_str = "Mobile"
            elif member.web_status != "offline":
                device_str = "Website"
        activity_str = "None"
        if member.activities:
            activity = member.activities[0]
            if isinstance(activity, discord.Game):
                activity_str = f"Playing {activity.name}"
            elif isinstance(activity, discord.Streaming):
                activity_str = f"Streaming on {activity.platform}"
            elif isinstance(activity, discord.CustomActivity):
                activity_str = f"{activity.emoji} {activity.name}"
            elif isinstance(activity, discord.Spotify):
                activity_str = f"Listening to {activity.title} by {activity.artist}"

        # Truncate activity string if too long
        activity_str = self._truncate_field_value(activity_str)
        roles_str = "None"
        if is_guild_member and member.roles:
            roles = [
                role.mention
                for role in reversed(member.roles)
                if role.name != "@everyone"
            ]
            if roles:
                roles_str = ", ".join(roles)
                # Truncate if too long for Discord embed field limit
                roles_str = self._truncate_field_value(roles_str)
            else:
                roles_str = "None"
        badge_map = {
            "staff": "Discord Staff 🛡️",
            "partner": "Partner ⭐",
            "hypesquad": "HypeSquad Event 🏆",
            "bug_hunter": "Bug Hunter 🐛",
            "hypesquad_bravery": "Bravery 🦁",
            "hypesquad_brilliance": "Brilliance 🧠",
            "hypesquad_balance": "Balance ⚖️",
            "early_supporter": "Early Supporter 🕰️",
            "team_user": "Team User 👥",
            "system": "System 🤖",
            "bug_hunter_level_2": "Bug Hunter Level 2 🐞",
            "verified_bot": "Verified Bot 🤖",
            "verified_developer": "Early Verified Bot Dev 🛠️",
            "discord_certified_moderator": "Certified Mod 🛡️",
            "active_developer": "Active Developer 🧑‍💻",
        }
        user_flags = getattr(user_obj, "public_flags", None)
        badges = []
        if user_flags:
            for flag in badge_map:
                if getattr(user_flags, flag, False):
                    badges.append(badge_map[flag])
        badge_str = ", ".join(badges) if badges else ""
        developer_badge = self.developer_badges.get(member.id)
        if developer_badge:
            badge_str = (badge_str + ", " if badge_str else "") + developer_badge

        # Truncate badge string if too long
        badge_str = self._truncate_field_value(badge_str)
        embed = discord.Embed(
            title=f"User Info: {member.display_name}",
            color=member.color if hasattr(member, "color") else discord.Color.blurple(),
            description=f"Profile of {member.mention}",
        )

        # Set banner as the main image (appears at top of embed)
        if banner_url:
            embed.set_image(url=banner_url)

        # Set user avatar as thumbnail (appears at top right corner)
        embed.set_thumbnail(url=member.display_avatar.url)

        if badge_str:
            embed.add_field(name="Badge", value=badge_str, inline=False)

        custom_user_data = await self.get_custom_user_data(member.id)
        if custom_user_data:
            notes_str = ""
            for key, value in custom_user_data.items():
                notes_str += f"**{key.replace('_', ' ').title()}:** {value}\n"
            if notes_str:
                # Truncate notes if too long for Discord embed field limit
                notes_str = self._truncate_field_value(notes_str)
                embed.add_field(name="📋 Admin Notes", value=notes_str, inline=False)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(
            name="Username", value=f"{member.name}#{member.discriminator}", inline=True
        )
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Device", value=device_str, inline=True)
        embed.add_field(name="Activity", value=activity_str, inline=True)
        embed.add_field(name="Roles", value=roles_str, inline=False)
        # Calculate time differences
        account_age = self._format_time_difference(member.created_at)
        account_created_text = f"{member.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n({account_age} ago)"

        embed.add_field(
            name="Account Created",
            value=account_created_text,
            inline=True,
        )
        if hasattr(member, "joined_at") and member.joined_at:
            server_join_age = self._format_time_difference(member.joined_at)
            joined_server_text = f"{member.joined_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n({server_join_age} ago)"
            embed.add_field(
                name="Joined Server",
                value=joined_server_text,
                inline=True,
            )
        embed.set_footer(
            text=f"Requested by {user_data['interaction_user_id']}",
            icon_url=self.bot.get_user(
                user_data["interaction_user_id"]
            ).display_avatar.url,
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="View Permissions",
                style=discord.ButtonStyle.secondary,
                custom_id=f"userinfo_permissions_{member.id}",
            )
        )
        return embed, view

    @commands.hybrid_group(
        name="usernote",
        description="Admin commands for managing user notes.",
    )
    async def usernote(self, ctx: commands.Context):
        """Admin commands for managing user notes."""
        await ctx.send_help(ctx.command)

    @usernote.command(name="set", description="Set a note for a user.")
    @app_commands.describe(
        user="The user to set a note for.",
        key="The note's title or key.",
        value="The content of the note.",
    )
    async def set_custom_value(
        self,
        ctx: commands.Context,
        user: discord.Member,
        key: str,
        value: str,
    ):
        if not await self.is_authorized_admin(ctx):
            return

        key = key.strip().lower().replace(" ", "_")
        if not key or len(key) > 50:
            await ctx.reply(
                "❌ Key must be between 1-50 characters and contain no spaces.",
                ephemeral=True,
            )
            return

        value = value.strip()
        if not value or len(value) > 500:
            await ctx.reply(
                "❌ Value must be between 1-500 characters.", ephemeral=True
            )
            return

        await self.set_custom_user_value(user.id, key, value)
        await ctx.reply(
            f"✅ Set note for {user.mention}:\n**{key}:** {value}",
            ephemeral=True,
        )

    @usernote.command(
        name="remove", description="Remove a note from a user."
    )
    @app_commands.describe(
        user="The user to remove a note from.", key="The title/key of the note to remove."
    )
    async def remove_custom_value(
        self, ctx: commands.Context, user: discord.Member, key: str
    ):
        if await self.remove_custom_user_value(user.id, key):
            await ctx.reply(
                f"✅ Removed note '{key}' for {user.mention}", ephemeral=True
            )
        else:
            await ctx.reply(
                f"❌ No note with key '{key}' found for {user.mention}", ephemeral=True
            )

    @usernote.command(
        name="list", description="List all notes for a user."
    )
    @app_commands.describe(user="The user to list notes for.")
    async def list_custom_values(
        self, ctx: commands.Context, user: discord.Member
    ):
        if not await self.is_authorized_admin(ctx):
            return

        custom_data = await self.get_custom_user_data(user.id)
        if not custom_data:
            await ctx.reply(
                f"❌ No notes found for {user.mention}", ephemeral=True
            )
            return

        content = f"**Notes for {user.display_name}**\n\n"
        for key, value in custom_data.items():
            display_value = value if len(value) <= 100 else value[:97] + "..."
            content += f"**{key}:** {display_value}\n"

        await ctx.reply(content, ephemeral=True)

    @usernote.command(
        name="clear", description="Clear all notes for a user."
    )
    @app_commands.describe(user="The user to clear all notes for.")
    async def clear_custom_values(
        self, ctx: commands.Context, user: discord.Member
    ):
        if not await self.is_authorized_admin(ctx):
            return

        try:
            from database.operations import delete_user_data

            success = await delete_user_data(user.id)
            if success:
                await ctx.reply(
                    f"✅ Cleared all custom data for {user.mention}", ephemeral=True
                )
            else:
                await ctx.reply(
                    f"❌ No custom data found for {user.mention}", ephemeral=True
                )
        except Exception as e:
            print(f"Failed to clear custom data for user {user.id}: {e}")
            await ctx.reply(
                f"❌ Error clearing custom data for {user.mention}", ephemeral=True
            )

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component and interaction.data[
            "custom_id"
        ].startswith("userinfo_"):
            custom_id_parts = interaction.data["custom_id"].split("_")
            action = custom_id_parts[1]
            user_id = int(custom_id_parts[2])

            if action == "permissions":
                await self.show_permissions(interaction, user_id)

    async def show_permissions(self, interaction: discord.Interaction, user_id: int):
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message(
                "Could not find that member in this server.", ephemeral=True
            )
            return

        permissions = member.guild_permissions
        sorted_perms = sorted(list(permissions), key=lambda x: x[0])

        embed = discord.Embed(
            title=f"Permissions for {member.display_name}",
            color=member.color,
            description="✅ = Granted, ❌ = Denied",
        )

        columns = [[], [], []]
        col_char_limits = [0, 0, 0]
        max_col_chars = 900

        for perm, value in sorted_perms:
            perm_str = f"{'✅' if value else '❌'} {perm.replace('_', ' ').title()}\n"

            best_col = -1
            min_len = float("inf")
            for i in range(3):
                if col_char_limits[i] + len(perm_str) < max_col_chars:
                    if col_char_limits[i] < min_len:
                        min_len = col_char_limits[i]
                        best_col = i

            if best_col != -1:
                columns[best_col].append(perm_str)
                col_char_limits[best_col] += len(perm_str)
            else:
                shortest_col = col_char_limits.index(min(col_char_limits))
                columns[shortest_col].append(perm_str)
                col_char_limits[shortest_col] += len(perm_str)

        for i in range(3):
            if columns[i]:
                embed.add_field(
                    name=f"Permissions {i+1}", value="".join(columns[i]), inline=True
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UserInfoCog(bot))

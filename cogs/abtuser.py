import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import json
import os

class UserInfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.custom_data_file = 'user_data.json'
        self.custom_user_data = self.load_custom_data()

    def load_custom_data(self):
        if os.path.exists(self.custom_data_file):
            with open(self.custom_data_file, 'r') as f:
                return json.load(f)
        return {}

    def save_custom_data(self):
        with open(self.custom_data_file, 'w') as f:
            json.dump(self.custom_user_data, f, indent=4)

    def get_custom_user_data(self, user_id):
        return self.custom_user_data.get(str(user_id), {})

    def set_custom_user_value(self, user_id, key, value):
        user_id_str = str(user_id)
        if user_id_str not in self.custom_user_data:
            self.custom_user_data[user_id_str] = {}
        self.custom_user_data[user_id_str][key] = value
        self.save_custom_data()

    def remove_custom_user_value(self, user_id, key):
        user_id_str = str(user_id)
        if user_id_str in self.custom_user_data and key in self.custom_user_data[user_id_str]:
            del self.custom_user_data[user_id_str][key]
            if not self.custom_user_data[user_id_str]:
                del self.custom_user_data[user_id_str]
            self.save_custom_data()
            return True
        return False

    async def is_authorized_admin(self, interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator

    @app_commands.command(name="aboutuser", description="Display comprehensive info about a user or yourself.")
    @app_commands.describe(user="The user to get info about (optional)")
    async def aboutuser(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        member = user or interaction.user
        if interaction.guild:
            member = interaction.guild.get_member(member.id) or member
        user_obj = member._user if hasattr(member, '_user') else member
        banner_url = None
        try:
            user_obj = await self.bot.fetch_user(member.id)
            if user_obj.banner:
                banner_url = user_obj.banner.url
        except Exception:
            pass
        user_data = {
            'member': member,
            'user_obj': user_obj,
            'banner_url': banner_url,
            'is_guild_member': isinstance(member, discord.Member) and interaction.guild,
            'interaction_user_id': interaction.user.id
        }
        embed, view = await self._create_main_view(user_data)
        await interaction.response.send_message(embed=embed, view=view)

    async def _create_main_view(self, user_data):
        member = user_data['member']
        user_obj = user_data['user_obj']
        banner_url = user_data['banner_url']
        is_guild_member = user_data['is_guild_member']
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
        roles_str = "None"
        if is_guild_member and member.roles:
            roles = [role.mention for role in reversed(member.roles) if role.name != "@everyone"]
            roles_str = ", ".join(roles) if roles else "None"
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
            "active_developer": "Active Developer 🧑‍💻"
        }
        user_flags = getattr(user_obj, 'public_flags', None)
        badges = []
        if user_flags:
            for flag in badge_map:
                if getattr(user_flags, flag, False):
                    badges.append(badge_map[flag])
        badge_str = ", ".join(badges) if badges else ""
        if member.id == 1141746562922459136:
            badge_str = (badge_str + ", " if badge_str else "") + "Bot Developer 🛠️"
        embed = discord.Embed(
            title=f"User Info: {member.display_name}",
            color=member.color if hasattr(member, 'color') else discord.Color.blurple(),
            description=f"Profile of {member.mention}"
        )
        if banner_url:
            embed.set_image(url=banner_url)
        if badge_str:
            embed.add_field(name="Badge", value=badge_str, inline=False)

        custom_user_data = self.get_custom_user_data(member.id)
        organization = custom_user_data.get('organization')
        if organization:
            embed.add_field(name="Organization", value=organization, inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="Username", value=f"{member.name}#{member.discriminator}", inline=True)
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Device", value=device_str, inline=True)
        embed.add_field(name="Activity", value=activity_str, inline=True)
        embed.add_field(name="Roles", value=roles_str, inline=False)
        embed.add_field(name="Account Created", value=member.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        if hasattr(member, 'joined_at') and member.joined_at:
            embed.add_field(name="Joined Server", value=member.joined_at.strftime('%Y-%m-%d %H:%M:%S UTC'), inline=True)
        embed.set_footer(text=f"Requested by {user_data['interaction_user_id']}", icon_url=self.bot.get_user(user_data['interaction_user_id']).display_avatar.url)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View Permissions", style=discord.ButtonStyle.secondary, custom_id=f"userinfo_permissions_{member.id}"))
        return embed, view

    userinfo_admin = app_commands.Group(name="userinfo_admin", description="Admin commands for managing custom user data")

    @userinfo_admin.command(name="set", description="Set a custom value for a user")
    @app_commands.describe(user="The user to set custom data for", key="The key/field name", value="The value to set")
    async def set_custom_value(self, interaction: discord.Interaction, user: discord.Member, key: str, value: str):
        if not await self.is_authorized_admin(interaction):
            return

        key = key.strip().lower().replace(' ', '_')
        if not key or len(key) > 50:
            await interaction.response.send_message("❌ Key must be between 1-50 characters and contain no spaces.", ephemeral=True)
            return

        value = value.strip()
        if not value or len(value) > 500:
            await interaction.response.send_message("❌ Value must be between 1-500 characters.", ephemeral=True)
            return

        self.set_custom_user_value(user.id, key, value)
        await interaction.response.send_message(f"✅ Set custom value for {user.mention}:\n**{key}:** {value}", ephemeral=True)

    @userinfo_admin.command(name="remove", description="Remove a custom value for a user")
    @app_commands.describe(user="The user to remove custom data from", key="The key/field name to remove")
    async def remove_custom_value(self, interaction: discord.Interaction, user: discord.Member, key: str):
        if self.remove_custom_user_value(user.id, key):
            await interaction.response.send_message(f"✅ Removed custom value '{key}' for {user.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ No custom value '{key}' found for {user.mention}", ephemeral=True)

    @userinfo_admin.command(name="list", description="List all custom values for a user")
    @app_commands.describe(user="The user to list custom data for")
    async def list_custom_values(self, interaction: discord.Interaction, user: discord.Member):
        if not await self.is_authorized_admin(interaction):
            return

        custom_data = self.get_custom_user_data(user.id)
        if not custom_data:
            await interaction.response.send_message(f"❌ No custom data found for {user.mention}", ephemeral=True)
            return

        content = f"**Custom Data for {user.display_name}**\n\n"
        for key, value in custom_data.items():
            display_value = value if len(value) <= 100 else value[:97] + "..."
            content += f"**{key}:** {display_value}\n"

        await interaction.response.send_message(content, ephemeral=True)

    @userinfo_admin.command(name="clear", description="Clear all custom values for a user")
    @app_commands.describe(user="The user to clear all custom data for")
    async def clear_custom_values(self, interaction: discord.Interaction, user: discord.Member):
        if not await self.is_authorized_admin(interaction):
            return

        user_id_str = str(user.id)
        if user_id_str in self.custom_user_data:
            del self.custom_user_data[user_id_str]
            self.save_custom_data()
            await interaction.response.send_message(f"✅ Cleared all custom data for {user.mention}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ No custom data found for {user.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component and interaction.data['custom_id'].startswith("userinfo_"):
            custom_id_parts = interaction.data['custom_id'].split('_')
            action = custom_id_parts[1]
            user_id = int(custom_id_parts[2])

            if action == "permissions":
                await self.show_permissions(interaction, user_id)

    async def show_permissions(self, interaction: discord.Interaction, user_id: int):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message("Could not find that member in this server.", ephemeral=True)
            return

        permissions = member.guild_permissions
        sorted_perms = sorted(list(permissions), key=lambda x: x[0])

        embed = discord.Embed(
            title=f"Permissions for {member.display_name}",
            color=member.color,
            description="✅ = Granted, ❌ = Denied"
        )

        columns = [[], [], []]
        col_char_limits = [0, 0, 0]
        max_col_chars = 900

        for perm, value in sorted_perms:
            perm_str = f"{'✅' if value else '❌'} {perm.replace('_', ' ').title()}\n"
            
            best_col = -1
            min_len = float('inf')
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
                embed.add_field(name=f"Permissions {i+1}", value="".join(columns[i]), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserInfoCog(bot))

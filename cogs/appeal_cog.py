import discord
from discord.ext import commands
from discord import app_commands
import datetime
import uuid

from lists import Owners
from .aimod_helpers.config_manager import (
    GLOBAL_BANS,
    USER_INFRACTIONS,
    APPEALS,
    save_appeals,
    save_global_bans, 
)
from .aimod_helpers.ui import AppealActions


class AppealCog(commands.Cog, name="Appeals"):
    """
    Handles moderation appeals.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="appeal", description="Submit an appeal for a recent moderation action."
    )
    @app_commands.describe(reason="The reason for your appeal.")
    async def submit_appeal(self, interaction: discord.Interaction, reason: str):
        user_id = interaction.user.id
        # Check if user is globally banned
        if user_id in GLOBAL_BANS:
            try:
                dm_channel = await interaction.user.create_dm()
                await dm_channel.send(
                    f"You are globally banned. To appeal, please email help@learnhelp with your User ID ({user_id}) and your reasoning for the appeal.\n\nReason you provided: {reason}"
                )
                await interaction.response.send_message(
                    "You are globally banned. Please check your DMs for instructions on how to appeal.",
                    ephemeral=True,
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"You are globally banned. Please email help@learnhelp with your User ID ({user_id}) and your reasoning for the appeal. (Could not DM you: {e})",
                    ephemeral=True,
                )
            return
        # Normal appeal process for non-globally banned users
        last_infraction = None

        for key, infractions in USER_INFRACTIONS.items():
            if f"_{user_id}" in key:
                guild_id_str = key.split("_")[0]
                for infraction in reversed(infractions):
                    if infraction.get("action_taken") in [
                        "BAN",
                        "GLOBAL_BAN",
                    ] or "TIMEOUT" in infraction.get("action_taken", ""):
                        last_infraction = infraction
                        last_infraction["guild_id"] = int(guild_id_str)
                        break
                if last_infraction:
                    break

        if not last_infraction:
            await interaction.response.send_message(
                "No recent appealable moderation action found for your account.",
                ephemeral=True,
            )
            return

        appeal_id = str(uuid.uuid4())
        appeal_data = {
            "appeal_id": appeal_id,
            "user_id": user_id,
            "reason": reason,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending",
            "original_infraction": last_infraction,
        }

        APPEALS[appeal_id] = appeal_data
        await save_appeals()

        admin_user_id = Owners.ILIKEPANCAKES.value
        admin_user = self.bot.get_user(admin_user_id)

        if not admin_user:
            print(
                f"CRITICAL: Could not find admin user with ID {admin_user_id} to send appeal."
            )
            await interaction.response.send_message(
                "Your appeal has been submitted, but there was an error notifying the admin.",
                ephemeral=True,
            )
            return

        guild_id = last_infraction["guild_id"]
        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else f"Guild ID: {guild_id}"

        embed = discord.Embed(
            title="New Moderation Appeal",
            description=f"An appeal has been submitted by a user.",
            color=discord.Color.yellow(),
        )
        embed.add_field(
            name="User",
            value=f"{interaction.user.mention} (`{interaction.user.id}`)",
            inline=False,
        )
        embed.add_field(name="Guild", value=guild_name, inline=False)
        embed.add_field(name="Reason for Appeal", value=reason, inline=False)
        embed.add_field(
            name="Original Action",
            value=f"`{last_infraction.get('action_taken')}`",
            inline=True,
        )
        embed.add_field(
            name="Original Reason",
            value=f"_{last_infraction.get('reasoning')}_",
            inline=True,
        )
        embed.set_footer(text=f"Appeal ID: {appeal_id}")
        embed.timestamp = discord.utils.utcnow()

        try:
            await admin_user.send(embed=embed, view=AppealActions(appeal_id=appeal_id))
            await interaction.response.send_message(
                "Your appeal has been successfully submitted for review.",
                ephemeral=True,
            )
        except discord.Forbidden:
            print(
                f"CRITICAL: Could not DM admin user {admin_user_id}. They may have DMs disabled."
            )
            await interaction.response.send_message(
                "Your appeal has been submitted, but there was an error notifying the admin.",
                ephemeral=True,
            )
        except Exception as e:
            print(
                f"CRITICAL: An unexpected error occurred when sending appeal to admin: {e}"
            )
            await interaction.response.send_message(
                "Your appeal has been submitted, but an unexpected error occurred.",
                ephemeral=True,
            )

    @commands.Cog.listener(name="on_interaction")
    async def on_appeal_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("appeal_"):
            return

        admin_user_id = Owners.ILIKEPANCAKES.value
        if interaction.user.id != admin_user_id:
            await interaction.response.send_message(
                "You are not authorized to handle this appeal.", ephemeral=True
            )
            return

        parts = custom_id.split("_")
        action = parts[1]
        appeal_id = "_".join(parts[2:])

        appeal_data = APPEALS.get(appeal_id)
        if not appeal_data:
            await interaction.response.send_message(
                "This appeal could not be found. It might be outdated.", ephemeral=True
            )
            return

        if appeal_data["status"] != "pending":
            await interaction.response.send_message(
                f"This appeal has already been {appeal_data['status']}.", ephemeral=True
            )
            return

        original_infraction = appeal_data["original_infraction"]
        user_id = appeal_data["user_id"]
        guild_id = original_infraction["guild_id"]
        guild = self.bot.get_guild(guild_id)
        user_to_notify = self.bot.get_user(user_id)

        original_message = interaction.message
        new_embed = original_message.embeds[0]
        new_embed.color = (
            discord.Color.green() if action == "accept" else discord.Color.red()
        )

        if action == "accept":
            appeal_data["status"] = "accepted"
            new_embed.title = "Appeal Accepted"

            if not guild:
                print(
                    f"Could not find guild {guild_id} to revert action for appeal {appeal_id}"
                )
                if user_to_notify:
                    try:
                        await user_to_notify.send(
                            f"Your appeal ({appeal_id}) was accepted, but we could not find the original server to revert the action. Please contact an admin."
                        )
                    except discord.Forbidden:
                        print(
                            f"Could not DM user {user_id} about accepted appeal with missing guild."
                        )
            else:
                action_reverted = False
                original_action = original_infraction.get("action_taken")
                if original_action == "BAN":
                    try:
                        await guild.unban(
                            discord.Object(id=user_id),
                            reason=f"Appeal {appeal_id} accepted.",
                        )
                        action_reverted = True
                    except Exception as e:
                        print(
                            f"Failed to unban user {user_id} in guild {guild_id} for appeal {appeal_id}: {e}"
                        )
                elif original_action == "GLOBAL_BAN":
                    if user_id in GLOBAL_BANS:
                        GLOBAL_BANS.remove(user_id)
                        await save_global_bans()
                    try:
                        await guild.unban(
                            discord.Object(id=user_id),
                            reason=f"Appeal {appeal_id} accepted.",
                        )
                        action_reverted = True
                    except Exception as e:
                        print(
                            f"Failed to unban user {user_id} in guild {guild_id} for global ban appeal {appeal_id}: {e}"
                        )
                elif "TIMEOUT" in original_action:
                    try:
                        member = await guild.fetch_member(user_id)
                        await member.timeout(
                            None, reason=f"Appeal {appeal_id} accepted."
                        )
                        action_reverted = True
                    except discord.NotFound:
                        print(
                            f"User {user_id} not found in guild {guild_id} to remove timeout for appeal {appeal_id}"
                        )
                    except Exception as e:
                        print(
                            f"Failed to remove timeout for user {user_id} in guild {guild_id} for appeal {appeal_id}: {e}"
                        )

                if user_to_notify:
                    try:
                        if action_reverted:
                            await user_to_notify.send(
                                f"Your appeal regarding the action in **{guild.name}** has been **accepted**, and the action has been reverted."
                            )
                        else:
                            await user_to_notify.send(
                                f"Your appeal regarding the action in **{guild.name}** has been **accepted**, but we failed to automatically revert the action. Please contact an admin."
                            )
                    except discord.Forbidden:
                        print(f"Could not DM user {user_id} about accepted appeal.")

        else:
            appeal_data["status"] = "denied"
            new_embed.title = "Appeal Denied"
            if user_to_notify:
                try:
                    await user_to_notify.send(f"Your appeal has been **denied**.")
                except discord.Forbidden:
                    print(f"Could not DM user {user_id} about denied appeal.")

        await save_appeals()

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Accepted" if action == "accept" else "Accept",
                style=discord.ButtonStyle.success,
                disabled=True,
            )
        )
        view.add_item(
            discord.ui.Button(
                label="Denied" if action == "deny" else "Deny",
                style=discord.ButtonStyle.danger,
                disabled=True,
            )
        )

        await interaction.response.edit_message(embed=new_embed, view=view)


async def setup(bot: commands.Bot):
    """Loads the AppealCog."""
    await bot.add_cog(AppealCog(bot))
    print("AppealCog has been loaded.")
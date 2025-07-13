import asyncio
import logging
from typing import Coroutine
import discord
from litellm.llms.github_copilot.authenticator import GithubCopilotAuthManager
from database.operations import set_guild_api_key

log = logging.getLogger(__name__)

async def start_copilot_login(interaction: discord.Interaction, guild_id: int):
    """
    Initiates the GitHub Copilot device authentication flow for a guild.
    """
    await interaction.response.defer(ephemeral=True)

    try:
        auth_manager = GithubCopilotAuthManager()
        login_info = auth_manager.start_login()
        
        user_code = login_info['user_code']
        verification_uri = login_info['verification_uri']
        device_code = login_info['device_code']

        embed = discord.Embed(
            title="GitHub Copilot Authentication",
            description=(
                f"Please visit {verification_uri} and enter the code below to link GitHub Copilot to this server:"
            ),
            color=discord.Color.blue()
        )
        embed.add_field(name="Your Code", value=f"`{user_code}`", inline=False)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open Authentication Page", url=verification_uri))

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        # Start polling for the token in a background task
        asyncio.create_task(
            poll_and_save_token(interaction, auth_manager, device_code, guild_id)
        )

    except Exception as e:
        log.error(f"Error starting Copilot login for guild {guild_id}: {e}")
        await interaction.followup.send(
            "An error occurred while starting the authentication process. Please try again later.",
            ephemeral=True
        )

async def poll_and_save_token(
    interaction: discord.Interaction,
    auth_manager: GithubCopilotAuthManager,
    device_code: str,
    guild_id: int
):
    """
    Polls for the authentication token and saves it to the database for the guild.
    """
    try:
        # This will block until the user authenticates
        auth_info = await asyncio.to_thread(auth_manager.poll_for_token, device_code)

        success = await set_guild_api_key(
            guild_id=guild_id,
            api_provider="github_copilot",
            key_data=auth_info
        )

        if success:
            await interaction.followup.send(
                "✅ The GitHub Copilot account has been successfully linked to this server.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Failed to save the authentication token. Please try again.",
                ephemeral=True
            )

    except Exception as e:
        log.error(f"Error polling for Copilot token for guild {guild_id}: {e}")
        await interaction.followup.send(
            "An error occurred during the authentication process. Please try again.",
            ephemeral=True
        )
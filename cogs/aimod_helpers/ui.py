import discord
from typing import Callable, Awaitable, Dict, Any

# Define a mapping from our action names to Discord permissions
ACTION_PERMISSION_MAP = {
    "BAN": "ban_members",
    "KICK": "kick_members",
    "TIMEOUT_SHORT": "moderate_members",
    "TIMEOUT_MEDIUM": "moderate_members",
    "TIMEOUT_LONG": "moderate_members",
    "WARN": "moderate_members",
}


class ActionConfirmationView(discord.ui.View):
    """
    A view that provides "Confirm" and "Deny" buttons for a moderation action.
    It handles permission checks and executes the appropriate callback.
    """

    def __init__(
        self,
        action: str,
        author_id: int,
        confirm_callback: Callable[[], Awaitable[None]],
        deny_callback: Callable[[], Awaitable[None]],
        timeout=86400,  # 24 hours
    ):
        super().__init__(timeout=timeout)
        self.action = action
        self.author_id = author_id
        self.confirm_callback = confirm_callback
        self.deny_callback = deny_callback
        self.required_permission = ACTION_PERMISSION_MAP.get(self.action)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Checks if the user interacting with the view has the required permissions.
        """
        if not self.required_permission:
            await interaction.response.send_message(
                "This action has no permission requirement configured.", ephemeral=True
            )
            return False

        # Get the permission value from the member's guild permissions
        author_permissions = interaction.user.guild_permissions
        has_permission = getattr(author_permissions, self.required_permission, False)

        if not has_permission:
            await interaction.response.send_message(
                f"You need the `{self.required_permission}` permission to respond to this action.",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """
        Confirms the action, executes the callback, and disables the view.
        """
        await self.confirm_callback()
        self.disable_all_items()
        # Update the original message to show it was confirmed
        new_embed = interaction.message.embeds[0]
        new_embed.color = discord.Color.green()
        new_embed.set_footer(
            text=f"Action confirmed by {interaction.user.display_name}"
        )
        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Denies the action, executes the callback, and disables the view.
        """
        await self.deny_callback()
        self.disable_all_items()
        # Update the original message to show it was denied
        new_embed = interaction.message.embeds[0]
        new_embed.color = discord.Color.red()
        new_embed.set_footer(text=f"Action denied by {interaction.user.display_name}")
        await interaction.response.edit_message(embed=new_embed, view=self)

    def disable_all_items(self):
        """Disables all buttons in the view."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True


class AppealButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="How to Appeal",
        style=discord.ButtonStyle.secondary,
        custom_id="appeal_info_button",
    )
    async def appeal_info(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_message(
            "To appeal, please use the `/aimod appeals appeal` command in this DM or in any server where I am present.\n\n"
            "**Example:** `/aimod appeals appeal reason: I believe my message was misinterpreted.`",
            ephemeral=True,
        )


class AppealActions(discord.ui.View):
    def __init__(self, appeal_id: str):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="Accept",
                style=discord.ButtonStyle.success,
                custom_id=f"appeal_accept_{appeal_id}",
            )
        )
        self.add_item(
            discord.ui.Button(
                label="Deny",
                style=discord.ButtonStyle.danger,
                custom_id=f"appeal_deny_{appeal_id}",
            )
        )

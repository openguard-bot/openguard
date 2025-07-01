import discord

class AppealButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="How to Appeal", style=discord.ButtonStyle.secondary, custom_id="appeal_info_button")
    async def appeal_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "To appeal, please use the `/aimod appeals appeal` command in this DM or in any server where I am present.\n\n"
            "**Example:** `/aimod appeals appeal reason: I believe my message was misinterpreted.`",
            ephemeral=True
        )


class AppealActions(discord.ui.View):
    def __init__(self, appeal_id: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Accept", style=discord.ButtonStyle.success, custom_id=f"appeal_accept_{appeal_id}"))
        self.add_item(discord.ui.Button(label="Deny", style=discord.ButtonStyle.danger, custom_id=f"appeal_deny_{appeal_id}"))
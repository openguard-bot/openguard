mport discord
from discord.ext import commands
from discord import app_commands
import aiohttp

# The GitHub repository to fetch contributors from
REPO_OWNER = "openguard-bot"
REPO_NAME = "openguard"

class CreditsCog(commands.Cog):
    """A cog to display credits for the OpenGuard project."""

    def __init__(self, bot: commands.Bot):
        """Initializes the CreditsCog."""
        self.bot = bot

    @app_commands.command(name="credits", description="Show the contributors for OpenGuard.")
    async def credits(self, interaction: discord.Interaction):
        """
        Fetches and displays the list of contributors from the OpenGuard GitHub repository.
        """
        await interaction.response.defer()

        # The URL for the GitHub API endpoint to get contributors
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contributors"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        contributors = await response.json()
                        
                        # Sort contributors by the number of contributions in descending order
                        contributors.sort(key=lambda x: x['contributions'], reverse=True)

                        # Create the embed
                        embed = discord.Embed(
                            title="OpenGuard Credits",
                            description="A heartfelt thank you to all our amazing contributors!",
                            color=discord.Color.blue()
                        )

                        if contributors:
                            # Set the thumbnail to the top contributor's avatar
                            embed.set_thumbnail(url=contributors[0]['avatar_url'])

                        description_text = ""
                        for contributor in contributors:
                            # Using get() is safer in case a key is missing
                            login = contributor.get('login', 'Unknown User')
                            contributions = contributor.get('contributions', 0)
                            profile_url = contributor.get('html_url', 'https://github.com')
                            
                            description_text += f"[{login}]({profile_url}) - **{contributions}** contributions\n"

                        embed.description += "\n\n" + description_text

                        await interaction.followup.send(embed=embed)

                    else:
                        # Handle cases where the API call fails
                        error_message = f"Failed to fetch contributors. GitHub API returned status: {response.status}"
                        await interaction.followup.send(error_message)

        except aiohttp.ClientError as e:
            # Handle network-related errors
            error_message = f"An error occurred while trying to connect to GitHub: {e}"
            await interaction.followup.send(error_message)
        except Exception as e:
            # Handle other potential errors
            await interaction.followup.send(f"An unexpected error occurred: {e}")

async def setup(bot: commands.Bot):
    """Sets up the cog."""
    await bot.add_cog(CreditsCog(bot))

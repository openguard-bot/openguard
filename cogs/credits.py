import discord
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

    async def _get_repo_owner_avatar_url(self) -> str | None:
        """Fetches the avatar URL of the repository owner."""
        user_url = f"https://api.github.com/users/{REPO_OWNER}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(user_url) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        return user_data.get('avatar_url')
                    else:
                        print(f"Failed to fetch repo owner avatar. GitHub API returned status: {response.status}")
                        return None
        except aiohttp.ClientError as e:
            print(f"An error occurred while trying to connect to GitHub for repo owner avatar: {e}")
            return None

    @app_commands.command(name="credits", description="Show the contributors for OpenGuard.")
    async def credits(self, interaction: discord.Interaction):
        """
        Fetches and displays the list of contributors from the OpenGuard GitHub repository.
        """
        await interaction.response.defer()

        # The URL for the GitHub API endpoint to get contributors
        contributors_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contributors"
        repo_owner_avatar_url = await self._get_repo_owner_avatar_url()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(contributors_url) as response:
                    if response.status == 200:
                        contributors = await response.json()
                        
                        # Sort contributors by the number of contributions in descending order
                        contributors.sort(key=lambda x: x['contributions'], reverse=True)

                        # Create the embed
                        embed = discord.Embed(
                            title="OpenGuard Credits",
                            description="tuff coders",
                            color=discord.Color.blue()
                        )

                        # Set the thumbnail to the repository owner's avatar
                        if repo_owner_avatar_url:
                            embed.set_thumbnail(url=repo_owner_avatar_url)
                        elif contributors:
                            # Fallback to top contributor's avatar if repo owner avatar not found
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

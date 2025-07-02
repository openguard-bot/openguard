import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import traceback
import sys
import functools
from discord import app_commands
import sys
import io

# Import database connection management
from database.connection import initialize_database, get_pool, close_pool

class DualStream:
    def __init__(self, original_stream, log_file):
        self.original_stream = original_stream
        self.log_file = log_file

    def write(self, data):
        self.original_stream.write(data)
        self.log_file.write(data)
        self.log_file.flush()

    def flush(self):
        self.original_stream.flush()
        self.log_file.flush()

log_file = open("bot.log", "a")
sys.stdout = DualStream(sys.stdout, log_file)
sys.stderr = DualStream(sys.stderr, log_file)

print("Logging started.")

load_dotenv("keys.env")
discord_token = os.getenv("DISCORD_TOKEN")

if not discord_token:
    raise ValueError("Missing DISCORD_TOKEN environment variable.")

intents = discord.Intents.all()
class MyBot(commands.Bot):
    async def is_owner(self, user: discord.User | discord.Member):
        if user is not None and getattr(user, 'id', None) is not None:
            return user.id in (1141746562922459136, 452666956353503252)
        raise ValueError("User/User ID was None, or user object had no ID property")

bot = MyBot(command_prefix="o!", intents=intents, help_command=None)

ERROR_NOTIFICATION_USER_ID = 1141746562922459136

def catch_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))

            print(f"Uncaught exception in {func.__name__}:")
            print(tb_string)

            context = f"Function: {func.__name__}, Module: {func.__module__}"
            if args and hasattr(args[0], '__class__'):
                context += f", Class: {args[0].__class__.__name__}"

            bot_instance = None
            if args and hasattr(args[0], 'bot'):
                bot_instance = args[0].bot
            elif args and isinstance(args[0], commands.Bot):
                bot_instance = args[0]

            if bot_instance:
                user = await bot_instance.fetch_user(ERROR_NOTIFICATION_USER_ID)
                if user:
                    error_content = f"**Error Type:** {type(e).__name__}\n"
                    error_content += f"**Error Message:** {str(e)}\n"
                    error_content += f"**Context:** {context}\n"

                    if tb_string:
                        if len(tb_string) > 1500:
                            tb_string = tb_string[:1500] + "...(truncated)"
                        error_content += f"**Traceback:**\n```\n{tb_string}\n```"

                    await user.send(error_content)

            raise
    return wrapper

async def load_cogs():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename}")
            except Exception as e:
                print(f"Failed to load cog {filename}: {e}")

                tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                try:
                    await send_error_dm(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        error_traceback=tb_string,
                        context_info=f"Error loading cog: {filename}"
                    )
                except Exception as dm_error:
                    print(f"Failed to send error DM for cog loading error: {dm_error}")

async def send_error_dm(error_type, error_message, error_traceback=None, context_info=None):
    try:
        user = await bot.fetch_user(ERROR_NOTIFICATION_USER_ID)
        if not user:
            print(f"Could not find user with ID {ERROR_NOTIFICATION_USER_ID} to send error notification")
            return

        error_content = f"**Error Type:** {error_type}\n"
        error_content += f"**Error Message:** {error_message}\n"

        if context_info:
            error_content += f"**Context:** {context_info}\n"

        if error_traceback:
            if len(error_traceback) > 1500:
                error_traceback = error_traceback[:1500] + "...(truncated)"
            error_content += f"**Traceback:**\n```\n{error_traceback}\n```"

        await user.send(error_content)
    except Exception as e:
        print(f"Failed to send error DM: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    error_type, error_value, error_traceback = sys.exc_info()
    tb_string = "".join(traceback.format_exception(error_type, error_value, error_traceback))

    print(f"Error in event {event}:")
    print(tb_string)

    context = f"Event: {event}"
    if args:
        context += f", Args: {args}"
    if kwargs:
        context += f", Kwargs: {kwargs}"

    await send_error_dm(
        error_type=error_type.__name__,
        error_message=str(error_value),
        error_traceback=tb_string,
        context_info=context
    )

@bot.event
async def on_command_error(ctx, error):
    error = getattr(error, 'original', error)

    # Handle specific user-facing errors
    user_message = None
    should_notify_owner = True

    if isinstance(error, commands.CommandNotFound):
        user_message = f"❌ Command `{ctx.invoked_with}` not found. Use `{ctx.prefix}help` to see available commands."
        should_notify_owner = False
    elif isinstance(error, commands.MissingRequiredArgument):
        user_message = f"❌ Missing required argument: `{error.param.name}`. Use `{ctx.prefix}help {ctx.command}` for usage information."
        should_notify_owner = False
    elif isinstance(error, commands.BadArgument):
        user_message = f"❌ Invalid argument provided. Use `{ctx.prefix}help {ctx.command}` for usage information."
        should_notify_owner = False
    elif isinstance(error, commands.TooManyArguments):
        user_message = f"❌ Too many arguments provided. Use `{ctx.prefix}help {ctx.command}` for usage information."
        should_notify_owner = False
    elif isinstance(error, commands.MissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        user_message = f"❌ You don't have permission to use this command. Required permissions: {missing_perms}"
        should_notify_owner = False
    elif isinstance(error, commands.BotMissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        user_message = f"❌ I don't have the required permissions to execute this command. Missing permissions: {missing_perms}"
        should_notify_owner = False
    elif isinstance(error, commands.NoPrivateMessage):
        user_message = "❌ This command cannot be used in private messages."
        should_notify_owner = False
    elif isinstance(error, commands.PrivateMessageOnly):
        user_message = "❌ This command can only be used in private messages."
        should_notify_owner = False
    elif isinstance(error, commands.NotOwner):
        user_message = "❌ This command can only be used by the bot owner."
        should_notify_owner = False
    elif isinstance(error, commands.CommandOnCooldown):
        user_message = f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds."
        should_notify_owner = False
    elif isinstance(error, commands.DisabledCommand):
        user_message = "❌ This command is currently disabled."
        should_notify_owner = False
    elif isinstance(error, commands.CheckFailure):
        user_message = "❌ You don't have permission to use this command."
        should_notify_owner = False

    # Send user-friendly message or generic error message
    try:
        if user_message:
            await ctx.send(user_message)
        else:
            await ctx.send("❌ An error occurred while executing the command. The bot owner has been notified.")
    except:
        pass

    # Only notify owner for unexpected errors
    if should_notify_owner:
        tb_string = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        print(f"Command error in {ctx.command}:")
        print(tb_string)

        context = f"Command: {ctx.command}, Author: {ctx.author} ({ctx.author.id}), Guild: {ctx.guild.name if ctx.guild else 'DM'} ({ctx.guild.id if ctx.guild else 'N/A'}), Channel: {ctx.channel}"

        await send_error_dm(
            error_type=type(error).__name__,
            error_message=str(error),
            error_traceback=tb_string,
            context_info=context
        )

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    error = getattr(error, 'original', error)

    # Handle specific user-facing errors
    user_message = None
    should_notify_owner = True

    if isinstance(error, app_commands.CommandNotFound):
        user_message = "❌ Command not found."
        should_notify_owner = False
    elif isinstance(error, app_commands.MissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        user_message = f"❌ You don't have permission to use this command. Required permissions: {missing_perms}"
        should_notify_owner = False
    elif isinstance(error, app_commands.BotMissingPermissions):
        missing_perms = ", ".join(error.missing_permissions)
        user_message = f"❌ I don't have the required permissions to execute this command. Missing permissions: {missing_perms}"
        should_notify_owner = False
    elif isinstance(error, app_commands.NoPrivateMessage):
        user_message = "❌ This command cannot be used in private messages."
        should_notify_owner = False
    elif isinstance(error, app_commands.CommandOnCooldown):
        user_message = f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds."
        should_notify_owner = False
    elif isinstance(error, app_commands.CheckFailure):
        user_message = "❌ You don't have permission to use this command."
        should_notify_owner = False
    elif isinstance(error, app_commands.TransformerError):
        user_message = f"❌ Invalid input provided: {str(error)}"
        should_notify_owner = False
    elif isinstance(error, commands.MissingRequiredArgument):
        user_message = f"❌ Missing required argument: `{error.param.name}`."
        should_notify_owner = False
    elif isinstance(error, commands.BadArgument):
        user_message = "❌ Invalid argument provided."
        should_notify_owner = False
    elif isinstance(error, commands.NotOwner):
        user_message = "❌ This command can only be used by the bot owner."
        should_notify_owner = False

    # Send user-friendly message or generic error message
    try:
        if user_message:
            if not interaction.response.is_done():
                await interaction.response.send_message(user_message, ephemeral=True)
            else:
                await interaction.followup.send(user_message, ephemeral=True)
        else:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while executing the command. The bot owner has been notified.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while executing the command. The bot owner has been notified.", ephemeral=True)
    except:
        pass

    # Only notify owner for unexpected errors
    if should_notify_owner:
        tb_string = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        command_name = interaction.command.name if interaction.command else "Unknown"
        print(f"App command error in {command_name}:")
        print(tb_string)

        context = f"Command: {command_name}, Author: {interaction.user} ({interaction.user.id}), Guild: {interaction.guild.name if interaction.guild else 'DM'} ({interaction.guild.id if interaction.guild else 'N/A'}), Channel: {interaction.channel}"

        await send_error_dm(
            error_type=type(error).__name__,
            error_message=str(error),
            error_traceback=tb_string,
            context_info=context
        )

@bot.event
async def on_ready():
    try:
        # Initialize database connection
        print("Initializing database connection...")
        db_success = await initialize_database()
        if db_success:
            print("Database initialized successfully!")
        else:
            print("Warning: Database initialization failed!")

        await bot.tree.sync()
        print("Commands synced successfully!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

        tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        await send_error_dm(
            error_type=type(e).__name__,
            error_message=str(e),
            error_traceback=tb_string,
            context_info="Error occurred during command sync in on_ready event"
        )

    print(f"Logged in as {bot.user}")
    print(f"Global error handling is active - errors will be sent to user ID: {ERROR_NOTIFICATION_USER_ID}")

@bot.command(name="testerror")
async def test_error(ctx):
    await ctx.send(f"Testing error handling in {ctx.command}...")
    raise ValueError("This is a test error to verify error handling")

@bot.tree.command(name="testerror", description="Test slash command to verify error handling")
async def test_error_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Testing error handling in slash command...")
    raise ValueError("This is a test error to verify slash command error handling")

async def main():
    try:
        async with bot:
            await load_cogs()
            await bot.start(discord_token)
    finally:
        # Clean up database connections
        print("Closing database connections...")
        await close_pool()
        print("Database connections closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Critical error during bot startup: {e}")
        tb_string = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        print(tb_string)

        print(f"Could not send error notification to user ID {ERROR_NOTIFICATION_USER_ID} - bot not running")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"Traceback: {tb_string}")
    finally:
        if 'log_file' in locals() and not log_file.closed:
            log_file.close()

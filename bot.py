"""
Blindy2 - Discord Blind Test Bot

Main entry point for the bot.
This file:
1. Loads the bot token from .env
2. Creates the Discord bot client
3. Enables required intents
4. Loads all cogs
5. Syncs slash commands
6. Starts the bot
"""

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio


def main():
    """Main function to start the bot."""

    # Load token from .env file
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env file!")
        print("Please create a .env file with your bot token.")
        print("Example: DISCORD_TOKEN=your_token_here")
        return

    # Create bot with required intents
    intents = discord.Intents.default()
    intents.message_content = True  # CRITICAL: Lets bot read messages
    intents.guilds = True  # Lets bot see server info
    intents.members = True  # Lets bot see member info

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        """Called when the bot successfully connects to Discord."""
        print(f"{bot.user.name} is online!")
        print(f"Connected to {len(bot.guilds)} server(s)")

        # Sync slash commands with Discord
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    @bot.event
    async def on_command_error(ctx, error):
        """Handle command errors gracefully."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands silently
        print(f"Error: {error}")

    async def load_extensions():
        """Load all cogs."""
        try:
            await bot.load_extension("cogs.admin")
            print("Loaded cog: admin")
        except Exception as e:
            print(f"Failed to load admin cog: {e}")

        try:
            await bot.load_extension("cogs.game")
            print("Loaded cog: game")
        except Exception as e:
            print(f"Failed to load game cog: {e}")

    async def start_bot():
        """Load extensions and start the bot."""
        async with bot:
            await load_extensions()
            await bot.start(TOKEN)

    # Run the bot
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Error running bot: {e}")


if __name__ == "__main__":
    main()

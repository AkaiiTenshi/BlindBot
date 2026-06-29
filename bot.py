"""
Blindy2 - Discord Blind Test Bot

Main entry point. Loads the bot token, creates the client,
loads all cogs, syncs slash commands, and starts the bot.
"""

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio


def main():
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env file!")
        print("Please create a .env file with your bot token.")
        print("Example: DISCORD_TOKEN=your_token_here")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"{bot.user.name} is online!")
        print(f"Connected to {len(bot.guilds)} server(s)")
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        print(f"Error: {error}")

    async def load_extensions():
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
        async with bot:
            await load_extensions()
            await bot.start(TOKEN)

    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Error running bot: {e}")


if __name__ == "__main__":
    main()

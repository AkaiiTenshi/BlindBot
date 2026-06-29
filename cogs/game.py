"""
Game logic and user commands for Blindy2 blind test bot.

This module handles:
- Game state (active round, locked status, winner)
- Processing player guesses
- User commands (/scores, /current)
"""

import discord
import asyncio
from discord import app_commands, Interaction
from discord.ext import commands
from datetime import datetime

from utils.answer_checker import check_answer
from utils.data_manager import DataManager


class GameCog(commands.Cog):
    """Cog for game logic and user-facing commands."""

    def __init__(self, bot):
        """
        Initialize the game cog.

        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.data_manager = DataManager()

        # Game state (in-memory, lost on restart)
        self.active = False  # Is a round currently running?
        self.artist = None  # Correct artist (lowercase)
        self.title = None  # Correct title (lowercase)
        self.locked = False  # Has someone answered correctly?
        self.winner_id = None  # Discord user ID of winner
        self.winner_name = None  # Display name of winner
        self.points_awarded = 0  # How many points awarded (1 or 2)
        self.started_at = None  # When round started (for elapsed time)
        self.round_number = 0  # Current round number
        self.game_channel_id = None  # Where to listen for guesses

        # Multi-round game state
        self.game_data = None  # Loaded game with multiple rounds

        # Batch round input mode
        self.batch_input_mode = False  # Is admin in batch input mode?
        self.batch_input_user_id = None  # User ID who started batch mode
        self.batch_input_channel_id = None  # Channel where batch mode was started
        self.batch_input_count = 0  # How many rounds to expect
        self.batch_input_received = 0  # How many rounds received so far

        # Load game channel from config
        config = self.data_manager.load_config()
        self.game_channel_id = config.get("game_channel_id")

        # Load any existing game
        self.game_data = self.data_manager.load_game()

    def begin_round(self, artist: str, title: str) -> int:
        """Start a new round. Returns the new round number."""
        self.active = True
        self.artist = artist
        self.title = title
        self.locked = False
        self.winner_id = None
        self.winner_name = None
        self.points_awarded = 0
        self.started_at = datetime.now()
        self.round_number += 1
        return self.round_number

    def finish_round(self) -> dict:
        """End the active round. Returns a summary dict for announcements."""
        info = {
            "round_number": self.round_number,
            "answer": f"{self.artist} - {self.title}",
            "locked": self.locked,
            "winner_name": self.winner_name,
            "points_awarded": self.points_awarded,
        }
        self.active = False
        return info

    def update_answer(self, artist: str, title: str):
        """Update the answer mid-round."""
        self.artist = artist
        self.title = title

    def set_game_channel(self, channel_id: int):
        """Set the channel ID where guesses are accepted."""
        self.game_channel_id = channel_id

    def start_batch_input(self, user_id: int, channel_id: int, count: int):
        """Enter batch input mode for a given user in a given channel."""
        self.batch_input_mode = True
        self.batch_input_user_id = user_id
        self.batch_input_channel_id = channel_id
        self.batch_input_count = count
        self.batch_input_received = 0

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Called every time someone sends a message in Discord.
        Processes guesses if the message is in the game channel.
        Also handles batch round input from admins.

        Args:
            message: Discord message object
        """
        # Ignore messages from bots (including ourselves)
        if message.author.bot:
            return

        # Check for batch input mode first
        if self.batch_input_mode and message.author.id == self.batch_input_user_id:
            # Only intercept messages from the channel where batch mode was started
            if message.channel.id != self.batch_input_channel_id:
                return

            # Parse the message as "artist - title"
            content = message.content.strip()

            # Check if user wants to cancel
            if content.lower() in ["cancel", "stop", "quit"]:
                self.batch_input_mode = False
                self.batch_input_user_id = None
                self.batch_input_channel_id = None
                await message.channel.send(
                    f"❌ Batch input cancelled. Added {self.batch_input_received} rounds."
                )
                return

            # Try to parse artist and title
            if " - " in content:
                parts = content.split(" - ", 1)
                artist = parts[0].strip().lower()
                title = parts[1].strip().lower()

                if artist and title:
                    # Add round to game
                    self.game_data["rounds"].append({"artist": artist, "title": title})
                    self.batch_input_received += 1

                    # Save to file
                    self.data_manager.save_game(self.game_data)

                    remaining = self.batch_input_count - self.batch_input_received
                    if remaining > 0:
                        await message.add_reaction("✅")
                    else:
                        # All rounds received
                        self.batch_input_mode = False
                        self.batch_input_user_id = None
                        self.batch_input_channel_id = None
                        await message.add_reaction("✅")
                        await message.channel.send(
                            f"✅ All {self.batch_input_received} rounds added to **{self.game_data['name']}**!\n"
                            f"Use `/next_round` to start playing."
                        )
                    return
                else:
                    await message.channel.send(
                        "❌ Invalid format. Use: `artist - title` or type `cancel` to stop."
                    )
                    return
            else:
                await message.channel.send(
                    "❌ Invalid format. Use: `artist - title` (with space-dash-space) or type `cancel` to stop."
                )
                return

        # Only process messages in the game channel
        if self.game_channel_id is None or message.channel.id != self.game_channel_id:
            return

        # Only process if round is active and not locked
        if not self.active or self.locked:
            return

        # Validate the answer
        is_correct, points, match_type = check_answer(
            message.content, self.artist, self.title
        )

        # If correct, lock the round and award points
        if is_correct:
            self.locked = True
            self.winner_id = message.author.id
            self.winner_name = message.author.display_name
            self.points_awarded = points

            # Save to persistent storage
            self.data_manager.add_score(
                str(message.author.id), message.author.display_name, points, match_type
            )

            # Announce the win
            if match_type == "both":
                await message.channel.send(
                    f"✅ {message.author.display_name} got both! (+{points} points)\n"
                    f"🔒 Question locked!"
                )
            elif match_type == "artist":
                await message.channel.send(
                    f"✅ {message.author.display_name} got the artist! (+{points} point)\n"
                    f"🔒 Question locked!"
                )
            elif match_type == "title":
                await message.channel.send(
                    f"✅ {message.author.display_name} got the title! (+{points} point)\n"
                    f"🔒 Question locked!"
                )

            # Auto-end the round after a short delay (3 seconds)

            round_num_snapshot = self.round_number
            await asyncio.sleep(3)

            if not self.active or self.round_number != round_num_snapshot: return
            info = self.finish_round()

            await message.channel.send(
                f"📊 **Round {info['round_number']} ended!**\n"
                f"Answer: {info['answer']}\n"
                f"Winner: {info['winner_name']} (+{info['points_awarded']} points)"
            )

        # If incorrect, do nothing (silent rejection)

    @app_commands.command(name="scores", description="Show top 10 leaderboard")
    async def scores(self, interaction: Interaction):
        """Display the leaderboard."""
        leaderboard = self.data_manager.get_leaderboard(limit=10)

        if not leaderboard:
            await interaction.response.send_message("No scores yet!")
            return

        # Create a nice embed (colored box with formatted text)
        embed = discord.Embed(
            title="🏆 Top 10 Leaderboard",
            color=0xFFD700,  # Gold color
        )

        for rank, (user_id, data) in enumerate(leaderboard, start=1):
            embed.add_field(
                name=f"{rank}. {data['username']}",
                value=f"{data['total_points']} points ({data['rounds_won']} wins)",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="current", description="Show current round status")
    async def current(self, interaction: Interaction):
        """Show info about the active round."""
        if not self.active:
            await interaction.response.send_message("No active round.")
            return

        # Calculate elapsed time
        elapsed = datetime.now() - self.started_at
        elapsed_str = str(elapsed).split(".")[0]  # Remove microseconds

        # Format status
        status = "🔒 Locked" if self.locked else "🟢 Active"

        embed = discord.Embed(
            title=f"Round {self.round_number}",
            color=0x00FF00,  # Green
        )
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Time Elapsed", value=elapsed_str, inline=True)

        if self.locked:
            embed.add_field(
                name="Winner",
                value=f"{self.winner_name} (+{self.points_awarded} points)",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    """
    Required function to load this cog.

    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(GameCog(bot))

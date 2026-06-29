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

TEAM_ROLES = {"Heapsters", "Stackos"}


class GameCog(commands.Cog):
    """Cog for game logic and user-facing commands."""

    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()

        self.active = False
        self.artist = None
        self.title = None
        self.locked = False
        self.winner_id = None
        self.winner_name = None
        self.points_awarded = 0
        self.started_at = None
        self.round_number = 0
        self.game_channel_id = None

        self.game_data = None

        self.game_scores = {}
        self.team_scores = {"Heapsters": 0, "Stackos": 0}

        self.batch_input_mode = False
        self.batch_input_user_id = None
        self.batch_input_channel_id = None
        self.batch_input_count = 0
        self.batch_input_received = 0

        config = self.data_manager.load_config()
        self.game_channel_id = config.get("game_channel_id")
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

    def reset_game_scores(self):
        """Reset per-game scores and team totals. Called when a new game is created."""
        self.game_scores = {}
        self.team_scores = {"Heapsters": 0, "Stackos": 0}

    def is_game_complete(self) -> bool:
        """Return True if all rounds of the current game have been played."""
        return (
            self.game_data is not None
            and self.game_data["current_round_index"] >= len(self.game_data["rounds"])
        )

    def build_game_leaderboard_embed(self) -> discord.Embed:
        """Build an embed showing team standings and top individual players."""
        heapsters = self.team_scores.get("Heapsters", 0)
        stackos = self.team_scores.get("Stackos", 0)

        if heapsters > stackos:
            title = "🏆 Game Over! Heapsters win!"
            color = 0xE74C3C
        elif stackos > heapsters:
            title = "🏆 Game Over! Stackos win!"
            color = 0x3498DB
        else:
            title = "🏆 Game Over! It's a tie!"
            color = 0x95A5A6

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Heapsters", value=f"{heapsters} pts", inline=True)
        embed.add_field(name="Stackos", value=f"{stackos} pts", inline=True)

        sorted_players = sorted(
            self.game_scores.values(), key=lambda x: -x["points"]
        )
        if sorted_players:
            lines = [
                f"{i}. {p['username']} ({p['team'] or 'No team'}) — {p['points']} pts"
                for i, p in enumerate(sorted_players[:10], 1)
            ]
            embed.add_field(name="Top Players", value="\n".join(lines), inline=False)

        return embed

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if self.batch_input_mode and message.author.id == self.batch_input_user_id:
            if message.channel.id != self.batch_input_channel_id:
                return

            content = message.content.strip()

            if content.lower() in ["cancel", "stop", "quit"]:
                self.batch_input_mode = False
                self.batch_input_user_id = None
                self.batch_input_channel_id = None
                await message.channel.send(
                    f"❌ Batch input cancelled. Added {self.batch_input_received} rounds."
                )
                return

            if " - " in content:
                parts = content.split(" - ", 1)
                artist = parts[0].strip().lower()
                title = parts[1].strip().lower()

                if artist and title:
                    self.game_data["rounds"].append({"artist": artist, "title": title})
                    self.batch_input_received += 1
                    self.data_manager.save_game(self.game_data)

                    remaining = self.batch_input_count - self.batch_input_received
                    if remaining > 0:
                        await message.add_reaction("✅")
                    else:
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

        if self.game_channel_id is None or message.channel.id != self.game_channel_id:
            return

        if not self.active or self.locked:
            return

        is_correct, points, match_type = check_answer(
            message.content, self.artist, self.title
        )

        if is_correct:
            self.locked = True
            self.winner_id = message.author.id
            self.winner_name = message.author.display_name
            self.points_awarded = points

            self.data_manager.add_score(
                str(message.author.id), message.author.display_name, points, match_type
            )

            team = next(
                (role.name for role in message.author.roles if role.name in TEAM_ROLES),
                None,
            )
            user_id_str = str(message.author.id)
            if user_id_str not in self.game_scores:
                self.game_scores[user_id_str] = {
                    "username": message.author.display_name,
                    "points": 0,
                    "team": team,
                }
            self.game_scores[user_id_str]["points"] += points
            if team:
                self.team_scores[team] += points

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

            round_num_snapshot = self.round_number
            await asyncio.sleep(3)

            if not self.active or self.round_number != round_num_snapshot:
                return
            info = self.finish_round()

            await message.channel.send(
                f"📊 **Round {info['round_number']} ended!**\n"
                f"Answer: {info['answer']}\n"
                f"Winner: {info['winner_name']} (+{info['points_awarded']} points)"
            )

            if self.is_game_complete():
                await message.channel.send(embed=self.build_game_leaderboard_embed())

    @app_commands.command(name="scores", description="Show top 10 leaderboard")
    async def scores(self, interaction: Interaction):
        """Display the all-time leaderboard."""
        leaderboard = self.data_manager.get_leaderboard(limit=10)

        if not leaderboard:
            await interaction.response.send_message("No scores yet!")
            return

        embed = discord.Embed(title="🏆 Top 10 Leaderboard", color=0xFFD700)

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

        elapsed = datetime.now() - self.started_at
        elapsed_str = str(elapsed).split(".")[0]
        status = "🔒 Locked" if self.locked else "🟢 Active"

        embed = discord.Embed(title=f"Round {self.round_number}", color=0x00FF00)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Time Elapsed", value=elapsed_str, inline=True)

        if self.locked:
            embed.add_field(
                name="Winner",
                value=f"{self.winner_name} (+{self.points_awarded} points)",
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="game_scores", description="Show current game team standings and top players")
    async def game_scores(self, interaction: Interaction):
        """Display team scores and individual standings for the current game."""
        if not self.game_data:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return
        await interaction.response.send_message(embed=self.build_game_leaderboard_embed())


async def setup(bot):
    await bot.add_cog(GameCog(bot))

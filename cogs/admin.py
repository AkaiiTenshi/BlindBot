"""
Admin commands for Blindy2 blind test bot.

This module provides commands for game administrators:
- Set game channel
- Start/end rounds
- Update answers
- Reveal answers
- Reset scores
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Optional

from utils.checks import has_manage_channels
from utils.data_manager import DataManager


class AdminCog(commands.Cog):
    """Cog for admin-only commands."""

    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()

    @app_commands.command(name="set_channel", description="Set current channel as game channel")
    @app_commands.check(has_manage_channels)
    async def set_channel(self, interaction: Interaction):
        """Configure which channel to use for the game."""
        channel_id = interaction.channel.id

        config = self.data_manager.load_config()
        config["game_channel_id"] = channel_id
        self.data_manager.save_config(config)

        game_cog = self.bot.get_cog("GameCog")
        if game_cog:
            game_cog.set_game_channel(channel_id)

        await interaction.response.send_message(
            f"✅ Game channel set to {interaction.channel.mention}", ephemeral=True
        )

    @app_commands.command(name="start_round", description="Start a new blind test round")
    @app_commands.describe(
        artist="Artist name (lowercase recommended)",
        title="Song title (lowercase recommended)",
    )
    @app_commands.check(has_manage_channels)
    async def start_round(self, interaction: Interaction, artist: str, title: str):
        """Start a new round with the given answer."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if game_cog.game_channel_id is None:
            await interaction.response.send_message(
                "❌ Game channel not set! Use `/set_channel` first.", ephemeral=True
            )
            return

        if game_cog.active:
            await interaction.response.send_message(
                "❌ Round already active! Use `/end_round` first.", ephemeral=True
            )
            return

        artist = " ".join(artist.strip().split()).lower()
        title = " ".join(title.strip().split()).lower()

        if not artist or not title:
            await interaction.response.send_message(
                "❌ Artist and title cannot be empty.", ephemeral=True
            )
            return

        round_num = game_cog.begin_round(artist, title)

        game_channel = self.bot.get_channel(game_cog.game_channel_id)
        await game_channel.send(f"🎵 **Round {round_num} started!** Start guessing!")

        await interaction.response.send_message(
            f"✅ Round {round_num} started!\nAnswer: {artist} - {title}", ephemeral=True
        )

    @app_commands.command(name="end_round", description="End the current round")
    @app_commands.check(has_manage_channels)
    async def end_round(self, interaction: Interaction):
        """End the active round and show results."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.active:
            await interaction.response.send_message("❌ No active round.", ephemeral=True)
            return

        info = game_cog.finish_round()
        game_channel = self.bot.get_channel(game_cog.game_channel_id)

        if info["locked"]:
            await game_channel.send(
                f"📊 **Round {info['round_number']} ended!**\n"
                f"Answer: {info['answer']}\n"
                f"Winner: {info['winner_name']} (+{info['points_awarded']} points)"
            )
        else:
            await game_channel.send(
                f"📊 **Round {info['round_number']} ended!**\n"
                f"Answer: {info['answer']}\n"
                f"No one guessed correctly."
            )

        if game_cog.is_game_complete():
            await game_channel.send(embed=game_cog.build_game_leaderboard_embed())

        await interaction.response.send_message("✅ Round ended.", ephemeral=True)

    @app_commands.command(name="set_answer", description="Correct the answer if you made a typo")
    @app_commands.describe(artist="Correct artist name", title="Correct song title")
    @app_commands.check(has_manage_channels)
    async def set_answer(self, interaction: Interaction, artist: str, title: str):
        """Update the answer mid-round."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.active:
            await interaction.response.send_message("❌ No active round.", ephemeral=True)
            return

        artist = " ".join(artist.strip().split()).lower()
        title = " ".join(title.strip().split()).lower()

        game_cog.update_answer(artist, title)

        await interaction.response.send_message(
            f"✅ Answer updated to: {artist} - {title}", ephemeral=True
        )

    @app_commands.command(name="show_answer", description="Reveal the answer without ending")
    @app_commands.check(has_manage_channels)
    async def show_answer(self, interaction: Interaction):
        """Show the answer in the game channel (for skipping)."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.active:
            await interaction.response.send_message("❌ No active round.", ephemeral=True)
            return

        game_channel = self.bot.get_channel(game_cog.game_channel_id)
        await game_channel.send(f"💡 Answer: {game_cog.artist} - {game_cog.title}")

        await interaction.response.send_message("✅ Answer revealed.", ephemeral=True)

    @app_commands.command(name="reset_scores", description="Reset scores")
    @app_commands.describe(user="User to reset (leave empty for all)")
    @app_commands.check(has_manage_channels)
    async def reset_scores(self, interaction: Interaction, user: Optional[discord.User] = None):
        """Reset all scores or a specific user's score."""
        if user:
            scores = self.data_manager.load_scores()
            user_id = str(user.id)

            if user_id in scores:
                del scores[user_id]
                self.data_manager.save_scores(scores)
                await interaction.response.send_message(
                    f"✅ Reset scores for {user.display_name}", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ No scores found for {user.display_name}", ephemeral=True
                )
        else:
            self.data_manager.save_scores({})
            await interaction.response.send_message("✅ All scores reset!", ephemeral=True)

    @app_commands.command(name="create_game", description="Create a new multi-round game")
    @app_commands.describe(
        name="Name of the game (e.g., '80s Classics')",
        rounds="Number of rounds to add (optional - for batch input)",
    )
    @app_commands.check(has_manage_channels)
    async def create_game(self, interaction: Interaction, name: str, rounds: int = 0):
        """Create a new game with multiple rounds."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if game_cog.active:
            await interaction.response.send_message(
                "❌ Please end the current round first with `/end_round`.", ephemeral=True
            )
            return

        game_cog.game_data = {"name": name, "rounds": [], "current_round_index": 0}
        game_cog.reset_game_scores()
        self.data_manager.save_game(game_cog.game_data)

        if rounds > 0:
            game_cog.start_batch_input(interaction.user.id, interaction.channel.id, rounds)
            await interaction.response.send_message(
                f"✅ Created game: **{name}**\n"
                f"📝 Batch input mode active! Send {rounds} messages in the format:\n"
                f"`artist - title`\n"
                f"Type `cancel` to stop early.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"✅ Created game: **{name}**\n"
                f"Add rounds using `/add_round` or use `/create_game` with the `rounds` parameter for batch input.",
                ephemeral=True,
            )

    @app_commands.command(name="add_round", description="Add a round to the current game")
    @app_commands.describe(artist="Artist name", title="Song title")
    @app_commands.check(has_manage_channels)
    async def add_round(self, interaction: Interaction, artist: str, title: str):
        """Add a round to the current game."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.game_data:
            await interaction.response.send_message(
                "❌ No game exists! Create one first with `/create_game`.", ephemeral=True
            )
            return

        artist = " ".join(artist.strip().split()).lower()
        title = " ".join(title.strip().split()).lower()

        if not artist or not title:
            await interaction.response.send_message(
                "❌ Artist and title cannot be empty.", ephemeral=True
            )
            return

        game_cog.game_data["rounds"].append({"artist": artist, "title": title})
        self.data_manager.save_game(game_cog.game_data)

        round_count = len(game_cog.game_data["rounds"])
        await interaction.response.send_message(
            f"✅ Added round {round_count}: {artist} - {title}\n"
            f"Game: **{game_cog.game_data['name']}** ({round_count} rounds)",
            ephemeral=True,
        )

    @app_commands.command(name="next_round", description="Start the next round from the current game")
    @app_commands.check(has_manage_channels)
    async def next_round(self, interaction: Interaction):
        """Start the next round from the current game."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.game_data:
            await interaction.response.send_message(
                "❌ No game exists! Create one first with `/create_game` and add rounds.",
                ephemeral=True,
            )
            return

        if not game_cog.game_data["rounds"]:
            await interaction.response.send_message(
                "❌ No rounds in game! Add rounds with `/add_round`.", ephemeral=True
            )
            return

        if game_cog.active:
            await interaction.response.send_message(
                "❌ Round already active! Use `/end_round` first.", ephemeral=True
            )
            return

        current_index = game_cog.game_data["current_round_index"]

        if current_index >= len(game_cog.game_data["rounds"]):
            await interaction.response.send_message(
                f"✅ Game **{game_cog.game_data['name']}** complete!\n"
                f"All {len(game_cog.game_data['rounds'])} rounds finished.\n"
                f"Use `/create_game` to start a new game.",
                ephemeral=True,
            )
            return

        if game_cog.game_channel_id is None:
            await interaction.response.send_message(
                "❌ Game channel not set! Use `/set_channel` first.", ephemeral=True
            )
            return

        current_round = game_cog.game_data["rounds"][current_index]
        artist = current_round["artist"]
        title = current_round["title"]

        game_cog.begin_round(artist, title)

        game_cog.game_data["current_round_index"] = current_index + 1
        self.data_manager.save_game(game_cog.game_data)

        game_channel = self.bot.get_channel(game_cog.game_channel_id)
        rounds_total = len(game_cog.game_data["rounds"])
        await game_channel.send(
            f"🎵 **Round {current_index + 1}/{rounds_total}** "
            f"(Game: {game_cog.game_data['name']}) - Start guessing!"
        )

        await interaction.response.send_message(
            f"✅ Started round {current_index + 1}/{rounds_total}\n"
            f"Answer: {artist} - {title}",
            ephemeral=True,
        )

    @app_commands.command(name="show_game", description="Show current game info")
    @app_commands.check(has_manage_channels)
    async def show_game(self, interaction: Interaction):
        """Show information about the current game."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.game_data:
            await interaction.response.send_message(
                "❌ No game exists! Create one with `/create_game`.", ephemeral=True
            )
            return

        game = game_cog.game_data
        current_idx = game["current_round_index"]
        total_rounds = len(game["rounds"])

        rounds_list = []
        for i, round_data in enumerate(game["rounds"], start=1):
            status = "✅" if i <= current_idx else "⏳"
            if i == current_idx + 1 and game_cog.active:
                status = "🎵"
            rounds_list.append(
                f"{status} Round {i}: {round_data['artist']} - {round_data['title']}"
            )

        rounds_text = "\n".join(rounds_list) if rounds_list else "No rounds added yet"

        await interaction.response.send_message(
            f"**Game: {game['name']}**\n"
            f"Progress: {current_idx}/{total_rounds} rounds completed\n\n"
            f"{rounds_text}",
            ephemeral=True,
        )

    @app_commands.command(name="delete_game", description="Delete the current game")
    @app_commands.check(has_manage_channels)
    async def delete_game(self, interaction: Interaction):
        """Delete the current game."""
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.game_data:
            await interaction.response.send_message("❌ No game exists!", ephemeral=True)
            return

        if game_cog.active:
            await interaction.response.send_message(
                "❌ Please end the current round first with `/end_round`.", ephemeral=True
            )
            return

        game_name = game_cog.game_data["name"]
        game_cog.game_data = None
        self.data_manager.save_game(None)

        await interaction.response.send_message(
            f"✅ Deleted game: **{game_name}**", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

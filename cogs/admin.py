import asyncio
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Optional

from utils.checks import has_admin_role
from utils.data_manager import DataManager


class AdminCog(commands.Cog):
    """Cog for admin-only commands."""

    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()

    @app_commands.command(name="set_admin_role", description="Set the role that can use admin commands")
    @app_commands.describe(role="The role to grant admin access")
    async def set_admin_role(self, interaction: Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ You need 'Manage Channels' permission to set the admin role.", ephemeral=True
            )
            return
        config = self.data_manager.load_config()
        config["admin_role_id"] = role.id
        self.data_manager.save_config(config)
        await interaction.response.send_message(
            f"✅ Admin role set to {role.mention}", ephemeral=True
        )

    @app_commands.command(name="set_team_roles", description="Set the roles used for team scoring")
    @app_commands.describe(team1="First team role", team2="Second team role (optional)")
    @app_commands.check(has_admin_role)
    async def set_team_roles(self, interaction: Interaction, team1: discord.Role, team2: Optional[discord.Role] = None):
        config = self.data_manager.load_config()
        ids = [team1.id]
        if team2:
            ids.append(team2.id)
        config["team_role_ids"] = ids
        self.data_manager.save_config(config)
        names = team1.name + (f", {team2.name}" if team2 else "")
        await interaction.response.send_message(f"✅ Team roles set: {names}", ephemeral=True)

    @app_commands.command(name="set_channel", description="Set current channel as game channel")
    @app_commands.check(has_admin_role)
    async def set_channel(self, interaction: Interaction):
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
        artist="Artist name",
        title="Song title",
    )
    @app_commands.check(has_admin_role)
    async def start_round(self, interaction: Interaction, artist: str, title: str):
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
    @app_commands.check(has_admin_role)
    async def end_round(self, interaction: Interaction):
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.active:
            await interaction.response.send_message("❌ No active round.", ephemeral=True)
            return

        info = game_cog.finish_round()
        game_channel = self.bot.get_channel(game_cog.game_channel_id)

        artist_by = info.get("artist_found_by") or "Nobody"
        title_by = info.get("title_found_by") or "Nobody"
        if info["artist_found"] or info["title_found"]:
            if artist_by == title_by:
                result = f"🏆 Both found by: {artist_by}"
            else:
                result = f"🎵 Artist: {artist_by}\n🎸 Title: {title_by}"
        else:
            result = "No one guessed correctly."

        await game_channel.send(
            f"📊 **Round {info['round_number']} ended!**\n"
            f"Answer: {info['answer']}\n{result}"
        )

        if game_cog.is_game_complete():
            await game_channel.send(embed=game_cog.build_game_leaderboard_embed())

        await interaction.response.send_message("✅ Round ended.", ephemeral=True)

    @app_commands.command(name="set_answer", description="Correct the answer if you made a typo")
    @app_commands.describe(artist="Correct artist name", title="Correct song title")
    @app_commands.check(has_admin_role)
    async def set_answer(self, interaction: Interaction, artist: str, title: str):
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
    @app_commands.check(has_admin_role)
    async def show_answer(self, interaction: Interaction):
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
    @app_commands.check(has_admin_role)
    async def reset_scores(self, interaction: Interaction, user: Optional[discord.User] = None):
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
    @app_commands.check(has_admin_role)
    async def create_game(self, interaction: Interaction, name: str, rounds: int = 0):
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
    @app_commands.check(has_admin_role)
    async def add_round(self, interaction: Interaction, artist: str, title: str):
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

        game_cog.game_data["rounds"].append({
            "artist": {"name": artist, "user_id_answer": 0},
            "title": {"name": title, "user_id_answer": 0},
        })
        self.data_manager.save_game(game_cog.game_data)

        round_count = len(game_cog.game_data["rounds"])
        await interaction.response.send_message(
            f"✅ Added round {round_count}: {artist} - {title}\n"
            f"Game: **{game_cog.game_data['name']}** ({round_count} rounds)",
            ephemeral=True,
        )

    @app_commands.command(name="start_game", description="Start the game and auto-advance rounds after each correct answer")
    @app_commands.check(has_admin_role)
    async def start_game(self, interaction: Interaction):
        game_cog = self.bot.get_cog("GameCog")

        if not game_cog:
            await interaction.response.send_message("❌ Game system not loaded!", ephemeral=True)
            return

        if not game_cog.game_data:
            await interaction.response.send_message(
                "❌ No game exists! Create one first with `/create_game` and add rounds.", ephemeral=True
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

        if game_cog.game_channel_id is None:
            await interaction.response.send_message(
                "❌ Game channel not set! Use `/set_channel` first.", ephemeral=True
            )
            return

        current_index = game_cog.game_data["current_round_index"]

        if current_index >= len(game_cog.game_data["rounds"]):
            await interaction.response.send_message(
                f"❌ Game **{game_cog.game_data['name']}** is already complete! Use `/create_game` to start a new one.",
                ephemeral=True,
            )
            return

        game_cog.auto_game_mode = True

        current_round = game_cog.game_data["rounds"][current_index]
        game_cog.begin_round(current_round["artist"]["name"], current_round["title"]["name"])
        game_cog.game_data["current_round_index"] = current_index + 1
        self.data_manager.save_game(game_cog.game_data)

        game_channel = self.bot.get_channel(game_cog.game_channel_id)
        rounds_total = len(game_cog.game_data["rounds"])
        await game_channel.send(
            f"🎵 **Round {current_index + 1}/{rounds_total}** "
            f"(Game: {game_cog.game_data['name']}) - Start guessing!"
        )

        await interaction.response.send_message(
            f"✅ Auto-game started! **{game_cog.game_data['name']}** ({rounds_total} rounds)\n"
            f"Rounds will auto-advance 5 seconds after each correct answer.",
            ephemeral=True,
        )

    @app_commands.command(name="next_round", description="Start the next round from the current game")
    @app_commands.check(has_admin_role)
    async def next_round(self, interaction: Interaction):
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
        artist = current_round["artist"]["name"]
        title = current_round["title"]["name"]

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
    @app_commands.check(has_admin_role)
    async def show_game(self, interaction: Interaction):
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
                f"{status} Round {i}: {round_data['artist']['name']} - {round_data['title']['name']}"
            )

        rounds_text = "\n".join(rounds_list) if rounds_list else "No rounds added yet"

        await interaction.response.send_message(
            f"**Game: {game['name']}**\n"
            f"Progress: {current_idx}/{total_rounds} rounds completed\n\n"
            f"{rounds_text}",
            ephemeral=True,
        )

    @app_commands.command(name="delete_game", description="Delete the current game")
    @app_commands.check(has_admin_role)
    async def delete_game(self, interaction: Interaction):
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

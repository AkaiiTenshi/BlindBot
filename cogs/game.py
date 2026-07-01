import discord
import asyncio
from discord import app_commands, Interaction
from discord.ext import commands
from datetime import datetime

from utils.answer_checker import check_answer
from utils.data_manager import DataManager


def _user_cooldown(interaction: Interaction) -> app_commands.Cooldown | None:
    if interaction.user.guild_permissions.manage_channels:
        return None
    config = DataManager().load_config()
    admin_role_id = config.get("admin_role_id")
    if admin_role_id and any(r.id == admin_role_id for r in interaction.user.roles):
        return None
    return app_commands.Cooldown(1, 30.0)


class GameCog(commands.Cog):
    """Cog for game logic and user-facing commands."""

    def __init__(self, bot):
        self.bot = bot
        self.data_manager = DataManager()

        self.active = False
        self.artist = None
        self.title = None
        self.locked = False
        self.artist_found = False
        self.artist_found_by_id = None
        self.artist_found_by_name = None
        self.title_found = False
        self.title_found_by_id = None
        self.title_found_by_name = None
        self.started_at = None
        self.round_number = 0
        self.game_channel_id = None

        self.game_data = None

        self.game_scores = {}
        self.team_scores = {}
        self.auto_game_mode = False

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
        self.artist_found = False
        self.artist_found_by_id = None
        self.artist_found_by_name = None
        self.title_found = False
        self.title_found_by_id = None
        self.title_found_by_name = None
        self.started_at = datetime.now()
        self.round_number += 1
        return self.round_number

    def finish_round(self) -> dict:
        """End the active round. Returns a summary dict for announcements."""
        info = {
            "round_number": self.round_number,
            "answer": f"{self.artist} - {self.title}",
            "artist_found": self.artist_found,
            "artist_found_by": self.artist_found_by_name,
            "title_found": self.title_found,
            "title_found_by": self.title_found_by_name,
        }
        self.active = False
        self.locked = False
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
        """Reset per-game scores, team totals, and auto-game mode."""
        self.game_scores = {}
        self.team_scores = {}
        self.auto_game_mode = False

    def is_game_complete(self) -> bool:
        """Return True if all rounds of the current game have been played."""
        return (
            self.game_data is not None
            and self.game_data["current_round_index"] >= len(self.game_data["rounds"])
        )

    def build_game_leaderboard_embed(self) -> discord.Embed:
        """Build an embed showing team standings and top individual players."""
        sorted_teams = sorted(self.team_scores.items(), key=lambda x: -x[1])

        if len(sorted_teams) >= 2 and sorted_teams[0][1] == sorted_teams[1][1]:
            title_str = "🏆 Game Over! It's a tie!"
            color = 0x95A5A6
        elif sorted_teams:
            title_str = f"🏆 Game Over! {sorted_teams[0][0]} win!"
            color = 0xFFD700
        else:
            title_str = "🏆 Game Over!"
            color = 0xFFD700

        embed = discord.Embed(title=title_str, color=color)
        for team_name, pts in sorted_teams:
            embed.add_field(name=team_name, value=f"{pts} pts", inline=True)

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

    async def _advance_game(self):
        """Wait 5 seconds then start the next round automatically."""
        await asyncio.sleep(5)

        if not self.auto_game_mode or not self.game_data:
            return

        if self.is_game_complete():
            self.auto_game_mode = False
            return

        current_index = self.game_data["current_round_index"]
        current_round = self.game_data["rounds"][current_index]

        self.begin_round(current_round["artist"]["name"], current_round["title"]["name"])
        self.game_data["current_round_index"] = current_index + 1
        self.data_manager.save_game(self.game_data)

        game_channel = self.bot.get_channel(self.game_channel_id)
        rounds_total = len(self.game_data["rounds"])
        await game_channel.send(
            f"🎵 **Round {current_index + 1}/{rounds_total}** "
            f"(Game: {self.game_data['name']}) - Start guessing!"
        )

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
                    self.game_data["rounds"].append({
                        "artist": {"name": artist, "user_id_answer": 0},
                        "title": {"name": title, "user_id_answer": 0},
                    })
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

        if not is_correct:
            return

        award_artist = (match_type in ("artist", "both")) and not self.artist_found
        award_title = (match_type in ("title", "both")) and not self.title_found

        if not award_artist and not award_title:
            return

        actual_points = (1 if award_artist else 0) + (1 if award_title else 0)

        config = self.data_manager.load_config()
        team_role_ids = config.get("team_role_ids", [])
        team_role = next((r for r in message.author.roles if r.id in team_role_ids), None)
        team = team_role.name if team_role else None

        self.data_manager.add_score(
            str(message.author.id), message.author.display_name, actual_points, match_type
        )
        user_id_str = str(message.author.id)
        if user_id_str not in self.game_scores:
            self.game_scores[user_id_str] = {
                "username": message.author.display_name,
                "points": 0,
                "team": team,
            }
        self.game_scores[user_id_str]["points"] += actual_points
        if team:
            self.team_scores[team] = self.team_scores.get(team, 0) + actual_points

        if award_artist:
            self.artist_found = True
            self.artist_found_by_id = message.author.id
            self.artist_found_by_name = message.author.display_name
        if award_title:
            self.title_found = True
            self.title_found_by_id = message.author.id
            self.title_found_by_name = message.author.display_name

        if award_artist and award_title:
            await message.channel.send(
                f"✅ {message.author.display_name} got both! (+{actual_points} points)"
            )
        elif award_artist:
            suffix = "🔒 Round locked!" if self.title_found else "🎵 Title still open!"
            await message.channel.send(
                f"✅ {message.author.display_name} got the artist! (+1 point)\n{suffix}"
            )
        elif award_title:
            suffix = "🔒 Round locked!" if self.artist_found else "🎵 Artist still open!"
            await message.channel.send(
                f"✅ {message.author.display_name} got the title! (+1 point)\n{suffix}"
            )

        if self.artist_found and self.title_found:
            self.locked = True
            round_num_snapshot = self.round_number
            await asyncio.sleep(3)

            if not self.active or self.round_number != round_num_snapshot:
                return
            info = self.finish_round()

            if info["artist_found_by"] == info["title_found_by"]:
                result_line = f"🏆 Both found by: {info['artist_found_by']}"
            else:
                result_line = (
                    f"🎵 Artist: {info['artist_found_by'] or 'Nobody'}\n"
                    f"🎸 Title: {info['title_found_by'] or 'Nobody'}"
                )
            await message.channel.send(
                f"📊 **Round {info['round_number']} ended!**\n"
                f"Answer: {info['answer']}\n{result_line}"
            )

            if self.is_game_complete():
                self.auto_game_mode = False
                await message.channel.send(embed=self.build_game_leaderboard_embed())
            elif self.auto_game_mode:
                asyncio.create_task(self._advance_game())

    @app_commands.checks.dynamic_cooldown(_user_cooldown, key=lambda i: i.user.id)
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

    @app_commands.checks.dynamic_cooldown(_user_cooldown, key=lambda i: i.user.id)
    @app_commands.command(name="current", description="Show current round status")
    async def current(self, interaction: Interaction):
        """Show info about the active round."""
        if not self.active:
            await interaction.response.send_message("No active round.")
            return

        elapsed = datetime.now() - self.started_at
        elapsed_str = str(elapsed).split(".")[0]

        embed = discord.Embed(title=f"Round {self.round_number}", color=0x00FF00)
        embed.add_field(name="Time Elapsed", value=elapsed_str, inline=False)

        if self.artist_found:
            embed.add_field(name="Artist", value=f"✅ Found by {self.artist_found_by_name}", inline=True)
        else:
            embed.add_field(name="Artist", value="⏳ Not found yet", inline=True)

        if self.title_found:
            embed.add_field(name="Title", value=f"✅ Found by {self.title_found_by_name}", inline=True)
        else:
            embed.add_field(name="Title", value="⏳ Not found yet", inline=True)

        await interaction.response.send_message(embed=embed)

    async def cog_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Wait {error.retry_after:.0f}s before using this command again.",
                ephemeral=True,
            )

    @app_commands.checks.dynamic_cooldown(_user_cooldown, key=lambda i: i.user.id)
    @app_commands.command(name="rules", description="Show the blind test rules")
    async def rules(self, interaction: Interaction):
        channel_mention = f"<#{self.game_channel_id}>" if self.game_channel_id else "#events"

        embed = discord.Embed(title="Règles / Rules", color=0x3498DB)

        embed.add_field(
            name="🇫🇷 Règles",
            value=(
                f"Envoyez le nom de l'artiste et/ou du titre dans {channel_mention}\n\n"
                "**Exemple :** abba - Gimme! Gimme! Gimme!\n\n"
                "✅ **Messages acceptés :**\n"
                "`abba` → 1 point\n"
                "`Gimme! Gimme! Gimme!` → 1 point\n"
                "`abba Gimme! Gimme! Gimme!` → 2 points\n\n"
                "❌ **Fautes (0 points) :**\n"
                "`Gimme! Gimme! Gimme` ← ponctuation manquante\n"
                "`abbba` ← faute de frappe"
            ),
            inline=False,
        )

        embed.add_field(
            name="🇬🇧 Rules",
            value=(
                f"Write the artist's name and/or the song title in {channel_mention}\n\n"
                "**Example:** abba - Gimme! Gimme! Gimme!\n\n"
                "✅ **Accepted answers:**\n"
                "`abba` → 1 point\n"
                "`Gimme! Gimme! Gimme!` → 1 point\n"
                "`abba Gimme! Gimme! Gimme!` → 2 points\n\n"
                "❌ **Wrong answers (0 points):**\n"
                "`Gimme! Gimme! Gimme` ← missing punctuation\n"
                "`abbba` ← typo"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.checks.dynamic_cooldown(_user_cooldown, key=lambda i: i.user.id)
    @app_commands.command(name="game_scores", description="Show current game team standings and top players")
    async def game_scores(self, interaction: Interaction):
        """Display team scores and individual standings for the current game."""
        if not self.game_data:
            await interaction.response.send_message("No active game.", ephemeral=True)
            return
        await interaction.response.send_message(embed=self.build_game_leaderboard_embed())


async def setup(bot):
    await bot.add_cog(GameCog(bot))

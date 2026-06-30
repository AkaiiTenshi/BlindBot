"""
Data management for Blindy2 blind test bot.

Handles persistent storage of configuration, player scores, and game state
using JSON files with atomic writes to prevent data corruption.
"""

import json
from pathlib import Path


class DataManager:
    """Manages reading and writing data to JSON files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.config_file = self.data_dir / "config.json"
        self.scores_file = self.data_dir / "scores.json"
        self.game_file = self.data_dir / "current_game.json"
        self.data_dir.mkdir(exist_ok=True)

    def load_config(self) -> dict:
        """Load configuration from config.json, returning defaults if missing."""
        if not self.config_file.exists():
            return {"game_channel_id": None, "admin_role_id": None, "team_role_ids": []}

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config.json: {e}")
            return {"game_channel_id": None, "admin_role_id": None, "team_role_ids": []}

    def save_config(self, config: dict):
        """Save configuration to config.json using an atomic write."""
        temp_file = self.config_file.with_suffix(".json.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            temp_file.replace(self.config_file)
        except IOError as e:
            print(f"Error saving config.json: {e}")
            if temp_file.exists():
                temp_file.unlink()

    def load_scores(self) -> dict:
        """Load scores from scores.json, returning an empty dict if missing."""
        if not self.scores_file.exists():
            return {}

        try:
            with open(self.scores_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading scores.json: {e}")
            return {}

    def save_scores(self, scores: dict):
        """Save scores to scores.json using an atomic write."""
        temp_file = self.scores_file.with_suffix(".json.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(scores, f, indent=2)
            temp_file.replace(self.scores_file)
        except IOError as e:
            print(f"Error saving scores.json: {e}")
            if temp_file.exists():
                temp_file.unlink()

    def add_score(self, user_id: str, username: str, points: int, match_type: str):
        """Add points to a user's all-time score."""
        scores = self.load_scores()

        if user_id not in scores:
            scores[user_id] = {
                "username": username,
                "total_points": 0,
                "rounds_won": 0,
                "full_answers": 0,
                "partial_answers": 0,
            }

        scores[user_id]["username"] = username
        scores[user_id]["total_points"] += points
        scores[user_id]["rounds_won"] += 1

        if match_type == "both":
            scores[user_id]["full_answers"] += 1
        else:
            scores[user_id]["partial_answers"] += 1

        self.save_scores(scores)

    def get_leaderboard(self, limit: int = 10) -> list[tuple[str, dict]]:
        """Return the top N players sorted by total points descending."""
        scores = self.load_scores()
        sorted_scores = sorted(
            scores.items(),
            key=lambda x: (-x[1]["total_points"], x[1]["username"].lower()),
        )
        return sorted_scores[:limit]

    def load_game(self) -> dict | None:
        """Load the current game from current_game.json, returning None if missing."""
        if not self.game_file.exists():
            return None

        try:
            with open(self.game_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading current_game.json: {e}")
            return None

    def save_game(self, game: dict | None):
        """Save the current game to current_game.json, or delete it if game is None."""
        if game is None:
            if self.game_file.exists():
                self.game_file.unlink()
            return

        temp_file = self.game_file.with_suffix(".json.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(game, f, indent=2)
            temp_file.replace(self.game_file)
        except IOError as e:
            print(f"Error saving current_game.json: {e}")
            if temp_file.exists():
                temp_file.unlink()

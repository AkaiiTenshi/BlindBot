"""
Data management for Blindy2 blind test bot.

This module handles persistent storage of:
- Configuration (game channel ID, settings)
- Player scores (points, wins, stats)

Uses JSON files for simple, human-readable storage.
"""

import json
import os
from pathlib import Path


class DataManager:
    """Manages reading and writing data to JSON files."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize the data manager.

        Args:
            data_dir: Directory where data files are stored
        """
        self.data_dir = Path(data_dir)
        self.config_file = self.data_dir / "config.json"
        self.scores_file = self.data_dir / "scores.json"
        self.game_file = self.data_dir / "current_game.json"

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

    def load_config(self) -> dict:
        """
        Load configuration from config.json.

        Returns:
            Configuration dictionary with defaults if file doesn't exist
        """
        if not self.config_file.exists():
            # Return default config
            return {"game_channel_id": None, "admin_permission": "manage_channels"}

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config.json: {e}")
            print("Using default configuration.")
            return {"game_channel_id": None, "admin_permission": "manage_channels"}

    def save_config(self, config: dict):
        """
        Save configuration to config.json (atomic write).

        Args:
            config: Configuration dictionary to save
        """
        # Atomic write: write to temp file first, then rename
        temp_file = self.config_file.with_suffix(".json.tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            # Rename temp file to actual file (atomic operation)
            temp_file.replace(self.config_file)
        except IOError as e:
            print(f"Error saving config.json: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()

    def load_scores(self) -> dict:
        """
        Load scores from scores.json.

        Returns:
            Scores dictionary (user_id -> stats) or empty dict if file doesn't exist
        """
        if not self.scores_file.exists():
            return {}

        try:
            with open(self.scores_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading scores.json: {e}")
            print("Starting with empty scores.")
            return {}

    def save_scores(self, scores: dict):
        """
        Save scores to scores.json (atomic write).

        Args:
            scores: Scores dictionary to save
        """
        # Atomic write: write to temp file first, then rename
        temp_file = self.scores_file.with_suffix(".json.tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(scores, f, indent=2)

            # Rename temp file to actual file (atomic operation)
            temp_file.replace(self.scores_file)
        except IOError as e:
            print(f"Error saving scores.json: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()

    def add_score(self, user_id: str, username: str, points: int, match_type: str):
        """
        Add points to a user's score.

        Args:
            user_id: Discord user ID (as string)
            username: User's display name
            points: Points to add (1 or 2)
            match_type: "artist", "title", or "both"
        """
        scores = self.load_scores()

        # Initialize user entry if doesn't exist
        if user_id not in scores:
            scores[user_id] = {
                "username": username,
                "total_points": 0,
                "rounds_won": 0,
                "full_answers": 0,
                "partial_answers": 0,
            }

        # Update stats
        scores[user_id]["username"] = username  # Update name in case it changed
        scores[user_id]["total_points"] += points
        scores[user_id]["rounds_won"] += 1

        if match_type == "both":
            scores[user_id]["full_answers"] += 1
        else:
            scores[user_id]["partial_answers"] += 1

        # Save updated scores
        self.save_scores(scores)

    def get_leaderboard(self, limit: int = 10) -> list[tuple[str, dict]]:
        """
        Get top N players sorted by score.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of (user_id, stats_dict) tuples, sorted by score (descending)
        """
        scores = self.load_scores()

        # Sort by total_points (descending), then by username (ascending)
        sorted_scores = sorted(
            scores.items(),
            key=lambda x: (-x[1]["total_points"], x[1]["username"].lower()),
        )

        return sorted_scores[:limit]

    def load_game(self) -> dict | None:
        """
        Load the current game from current_game.json.

        Returns:
            Game dictionary or None if no game exists

        Game structure:
        {
            "name": "Game Name",
            "rounds": [
                {"artist": "artist1", "title": "title1"},
                {"artist": "artist2", "title": "title2"}
            ],
            "current_round_index": 0
        }
        """
        if not self.game_file.exists():
            return None

        try:
            with open(self.game_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading current_game.json: {e}")
            return None

    def save_game(self, game: dict | None):
        """
        Save the current game to current_game.json (atomic write).

        Args:
            game: Game dictionary to save, or None to delete the game
        """
        if game is None:
            # Delete the game file
            if self.game_file.exists():
                self.game_file.unlink()
            return

        # Atomic write: write to temp file first, then rename
        temp_file = self.game_file.with_suffix(".json.tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(game, f, indent=2)

            # Rename temp file to actual file (atomic operation)
            temp_file.replace(self.game_file)
        except IOError as e:
            print(f"Error saving current_game.json: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                temp_file.unlink()

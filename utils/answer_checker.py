"""
Answer validation for Blindy2 blind test bot.

This module implements strict validation:
- Must be lowercase only (uppercase rejected silently)
- Whitespace is normalized
- Exact artist match → 1 point
- Exact title match → 1 point
- Exact "<artist> <title>" (in that order) → 2 points
- Partial matches: artist exact + title partial → 1 point (artist only)
- Partial matches: artist partial + title exact → 1 point (title only)
- Any other format (wrong order, extra words) → 0 points
"""


def check_answer(message: str, artist: str, title: str) -> tuple[bool, int, str | None]:
    """
    Check if a player's guess is correct.

    Args:
        message: The player's guess (from Discord message)
        artist: The correct artist name
        title: The correct song title

    Returns:
        A tuple of (is_correct, points, match_type):
        - is_correct: True if the guess matches validation rules
        - points: 0, 1, or 2 points to award
        - match_type: "artist", "title", "both", or None

    Examples:
        >>> check_answer("sniper", "Sniper", "Grave dans la roche")
        (True, 1, "artist")

        >>> check_answer("grave dans la roche", "Sniper", "Grave dans la roche")
        (True, 1, "title")

        >>> check_answer("sniper grave dans la roche", "Sniper", "Grave dans la roche")
        (True, 2, "both")

        >>> check_answer("grave dans la roche sniper", "Sniper", "Grave dans la roche")
        (False, 0, None)  # Wrong order

        >>> check_answer("sniper grave dans la", "Sniper", "Grave dans la roche")
        (True, 1, "artist")  # Artist exact, title partial

        >>> check_answer("snipe grave dans la roche", "Sniper", "Grave dans la roche")
        (True, 1, "title")  # Artist partial, title exact
    """
    # Step 1: Normalize whitespace (collapse multiple spaces into one)
    guess = " ".join(message.strip().split())
    artist_normalized = " ".join(artist.strip().split())
    title_normalized = " ".join(title.strip().split())

    # Step 2: Check for uppercase letters (reject if found)
    if guess != guess.lower():
        return (False, 0, None)

    # Step 3: Convert everything to lowercase for comparison
    guess = guess.lower()
    artist_lower = artist_normalized.lower()
    title_lower = title_normalized.lower()

    # Step 4: Check exact matches first
    # Just artist
    if guess == artist_lower:
        return (True, 1, "artist")

    # Just title
    if guess == title_lower:
        return (True, 1, "title")

    # Both in correct order: "<artist> <title>"
    both_correct_order = f"{artist_lower} {title_lower}"
    if guess == both_correct_order:
        return (True, 2, "both")

    # Step 5: Check partial matches
    # Case: guess starts with exact artist, but title is partial
    if guess.startswith(artist_lower + " "):
        remaining = guess[len(artist_lower) + 1 :]  # +1 for the space
        # Check if remaining is a partial match of title (starts with it)
        if title_lower.startswith(remaining):
            return (True, 1, "artist")  # Only artist is complete

    # Case: guess ends with exact title, but artist is partial
    if guess.endswith(" " + title_lower):
        remaining = guess[: -(len(title_lower) + 1)]  # +1 for the space
        # Check if remaining is a partial match of artist (artist starts with it)
        if artist_lower.startswith(remaining):
            return (True, 1, "title")  # Only title is complete

    # No valid match
    return (False, 0, None)

"""
Answer validation for Blindy2 blind test bot.

Validation rules:
- Must be lowercase only (uppercase rejected silently)
- Whitespace is normalized
- Exact artist match → 1 point
- Exact title match → 1 point
- Exact artist + title (any order) → 2 points
- Exact one + partial other (any order) → 1 point for the exact one
- Anything else → 0 points
"""


def check_answer(message: str, artist: str, title: str) -> tuple[bool, int, str | None]:
    """
    Check if a player's guess is correct.

    Returns a tuple of (is_correct, points, match_type)
    where match_type is "artist", "title", "both", or None.
    """
    guess = " ".join(message.strip().split())
    artist_normalized = " ".join(artist.strip().split())
    title_normalized = " ".join(title.strip().split())

    if guess != guess.lower():
        return (False, 0, None)

    guess = guess.lower()
    artist_lower = artist_normalized.lower()
    title_lower = title_normalized.lower()

    if guess == artist_lower:
        return (True, 1, "artist")

    if guess == title_lower:
        return (True, 1, "title")

    if guess == f"{artist_lower} {title_lower}":
        return (True, 2, "both")

    if guess == f"{title_lower} {artist_lower}":
        return (True, 2, "both")

    if guess.startswith(artist_lower + " "):
        remaining = guess[len(artist_lower) + 1:]
        if title_lower.startswith(remaining):
            return (True, 1, "artist")

    if guess.endswith(" " + title_lower):
        remaining = guess[:-(len(title_lower) + 1)]
        if artist_lower.startswith(remaining):
            return (True, 1, "title")

    if guess.startswith(title_lower + " "):
        remaining = guess[len(title_lower) + 1:]
        if artist_lower.startswith(remaining):
            return (True, 1, "title")

    if guess.endswith(" " + artist_lower):
        remaining = guess[:-(len(artist_lower) + 1)]
        if title_lower.startswith(remaining):
            return (True, 1, "artist")

    return (False, 0, None)

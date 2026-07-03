def check_answer(message: str, artist: str, title: str) -> tuple[bool, int, str | None]:
    """
    Check if a player's guess is correct.

    Returns a tuple of (is_correct, points, match_type)
    where match_type is "artist", "title", "both", or None.
    """
    guess = " ".join(message.strip().split()).lower()
    artist_lower = " ".join(artist.strip().split()).lower()
    title_lower = " ".join(title.strip().split()).lower()

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

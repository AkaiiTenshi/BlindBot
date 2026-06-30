def check_answer(message: str, artist: str, title: str) -> tuple[bool, int, str | None]:
    """
    Check if a player's guess is correct.

    Returns a tuple of (is_correct, points, match_type)
    where match_type is "artist", "title", "both", or None.

    Words with more than 1 uppercase letter are stripped from the guess before
    matching, so bad-casing parts don't block valid parts from scoring.
    """
    raw_words = message.strip().split()
    valid_words = [w for w in raw_words if sum(1 for c in w if c.isupper()) <= 1]

    if not valid_words:
        return (False, 0, None)

    guess = " ".join(valid_words).lower()
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

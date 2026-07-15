def check_answer(message: str, artist: str | None, title: str | None) -> tuple[bool, int, str | None]:
    """
    Check if a player's guess is correct.

    Returns a tuple of (is_correct, points, match_type)
    where match_type is "artist", "title", or None.
    artist and/or title can be None for single-part rounds.
    """
    guess = " ".join(message.strip().split()).lower()

    if artist is not None:
        if guess == " ".join(artist.strip().split()).lower():
            return (True, 1, "artist")

    if title is not None:
        if guess == " ".join(title.strip().split()).lower():
            return (True, 1, "title")

    return (False, 0, None)

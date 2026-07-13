import pytest

from utils.answer_checker import check_answer


@pytest.mark.parametrize(
    "message, artist, title, expected",
    [
        ("artist", "artist", "title", (True, 1, "artist")),
        ("title", "artist", "title", (True, 1, "title")),
        ("artist title", "artist", "title", (False, 0, None)),
        ("title artist", "artist", "title", (False, 0, None)),
        ("!   artist   ", "artist", "title", (False, 0, None)),
        ("The   title   ", "artist", "title", (False, 0, None)),
        ("wRong", "artist", "title", (False, 0, None)),
        ("wrong_title", "artist", "title", (False, 0, None)),
        ("wrong_artist", "artist", "title", (False, 0, None)),
        ("michael jacks", "michael jackson", "beat it", (False, 0, None)),
        ("michael jackSon", "michael jackson", "beat it", (True, 1, "artist")),
        ("Beat IT", "michael jackson", "beat it", (True, 1, "title")),
        ("artist", "artist", "title", (True, 1, "artist")),
        ("title", "artist", "title", (True, 1, "title")),
        ("michael", "michael jackson", "beat it", (False, 0, None)),
        ("michael jackson1", "michael jackson", "beat it", (False, 0, None)),
        (".michael jackson", "michael jackson", "beat it", (False, 0, None)),
        ("michael_jackson", "michael jackson", "beat it", (False, 0, None)),
        ("michael jackson                       1", "michael jackson", "beat it", (False, 0, None)),
        ("ArtIst", "artist", "title", (True, 1, "artist")),
        ("ARTIST", "artist", "title", (True, 1, "artist")),
        ("artisT", "artist", "title", (True, 1, "artist")),
        ("TiTle", "artist", "title", (True, 1, "title")),
        ("TITLE", "artist", "title", (True, 1, "title")),
        ("title", "artist", "title", (True, 1, "title")),
    ],
)
def test_check_answer_basic_cases(message, artist, title, expected):
    assert check_answer(message, artist, title) == expected

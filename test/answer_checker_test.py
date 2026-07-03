import pytest

from utils.answer_checker import check_answer


@pytest.mark.parametrize(
    "message, artist, title, expected",
    [
        ("artist", "artist", "title", (True, 1, "artist")),
        ("title", "artist", "title", (True, 1, "title")),
        ("artist title", "artist", "title", (True, 2, "both")),
        ("title artist", "artist", "title", (True, 2, "both")),
        ("   artist   ", "artist", "title", (True, 1, "artist")),
        ("   title   ", "artist", "title", (True, 1, "title")),
        ("wrong", "artist", "title", (False, 0, None)),
        ("wrong title", "artist", "title", (False, 0, None)),
        ("wrong artist", "artist", "title", (False, 0, None)),
        ("Artist", "artist", "title", (True, 1, "artist")),
        ("ARTIST", "artist", "title", (True, 1, "artist")),
        ("Linkin Park", "linkin park", "heavy is the crown", (True, 1, "artist")),
        ("LINKIN PARK", "linkin park", "heavy is the crown", (True, 1, "artist")),
        ("Heavy Is The Crown", "linkin park", "heavy is the crown", (True, 1, "title")),
        ("NF hope", "nf", "hope", (True, 2, "both")),
        ("nf HOPE", "nf", "hope", (True, 2, "both")),
        ("NF HOPE", "nf", "hope", (True, 2, "both")),
        ("Gimme! Gimme! Gimme!", "abba", "Gimme! Gimme! Gimme!", (True, 1, "title")),
        ("Gimme! Gimme! Gimme", "abba", "Gimme! Gimme! Gimme!", (False, 0, None)),
        ("abbba", "abba", "Gimme! Gimme! Gimme!", (False, 0, None))
    ],
)
def test_check_answer_basic_cases(message, artist, title, expected):
    assert check_answer(message, artist, title) == expected
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
        ("Artist", "artist", "title", (False, 1, None)),
        ("ARTIST", "artist", "title", (False, 1, None)),
    ],
)
def test_check_answer_basic_cases(message, artist, title, expected):
    assert check_answer(message, artist, title) == expected
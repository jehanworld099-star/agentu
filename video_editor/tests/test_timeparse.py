import pytest

from core.timeparse import parse_time_to_seconds, validate_against_duration


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1:05", 65),
        ("01:05:30", 3930),
        ("65s", 65),
        ("65", 65),
        ("1 minute 5 seconds", 65),
        ("1 min 5 sec", 65),
        ("1 minute 5 second se", 65),
    ],
)
def test_parse_time_to_seconds(text, expected):
    assert parse_time_to_seconds(text) == expected


def test_parse_time_rejects_garbage():
    with pytest.raises(ValueError):
        parse_time_to_seconds("not a time")


def test_parse_time_rejects_empty():
    with pytest.raises(ValueError):
        parse_time_to_seconds("")
    with pytest.raises(ValueError):
        parse_time_to_seconds(None)


def test_validate_against_duration_ok():
    validate_against_duration(10, 20)


def test_validate_against_duration_negative():
    with pytest.raises(ValueError):
        validate_against_duration(-1, 20)


def test_validate_against_duration_beyond_end():
    with pytest.raises(ValueError):
        validate_against_duration(25, 20)

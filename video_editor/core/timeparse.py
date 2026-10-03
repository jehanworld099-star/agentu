"""Parse human-entered time strings into seconds.

Supports:
    "1:05"                      -> mm:ss
    "01:05:30"                  -> hh:mm:ss
    "65s" / "65"                -> plain seconds
    "1 minute 5 seconds"
    "1 min 5 sec"
    "1 minute 5 second se"      -> tolerant of trailing junk/typos
"""
from __future__ import annotations

import re

_COLON_RE = re.compile(r"\d+(:\d+){1,2}(\.\d+)?")
_PLAIN_NUMBER_RE = re.compile(r"\d+(\.\d+)?s?")
_UNIT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\b"
)

_UNIT_SECONDS = {
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
}


def parse_time_to_seconds(text: str) -> float:
    """Parse a human time string into seconds. Raises ValueError if unparseable."""
    if text is None:
        raise ValueError("Time string is empty.")
    original = text
    text = text.strip().lower()
    if not text:
        raise ValueError("Time string is empty.")

    if _COLON_RE.fullmatch(text):
        parts = [float(p) for p in text.split(":")]
        if len(parts) == 2:
            minutes, seconds = parts
            return minutes * 60 + seconds
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds

    if _PLAIN_NUMBER_RE.fullmatch(text):
        return float(text[:-1]) if text.endswith("s") else float(text)

    matches = list(_UNIT_RE.finditer(text))
    if matches:
        total = 0.0
        for match in matches:
            value = float(match.group(1))
            unit = match.group(2)
            total += value * _UNIT_SECONDS[unit]
        return total

    raise ValueError(f"Could not parse time string: {original!r}")


def validate_against_duration(seconds: float, duration: float, *, label: str = "timestamp") -> None:
    """Raise ValueError with a readable message if seconds is outside [0, duration]."""
    if seconds < 0:
        raise ValueError(f"{label} cannot be negative (got {seconds}s).")
    if seconds > duration:
        raise ValueError(
            f"{label} ({seconds}s) is beyond the video's duration ({duration:.2f}s)."
        )

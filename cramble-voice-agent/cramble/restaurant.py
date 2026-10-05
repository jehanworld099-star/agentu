"""Loads restaurant_data.json and answers questions about hours, slots and rules."""

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ---------------------------------------------------------------------------
# Parsing and formatting helpers
# ---------------------------------------------------------------------------

def parse_date(value) -> date:
    """Accepts '2026-10-09', '09/10/2026', '2026/10/09' or a date object."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Could not understand the date '{value}'. Use YYYY-MM-DD.")


def parse_time(value) -> time:
    """Accepts '20:00', '8 PM', '8:30pm', '20.30', '2000' or a time object."""
    if isinstance(value, time):
        return value
    text = str(value).strip().lower().replace(".", ":").replace(" ", "")
    text = text.replace("a:m:", "am").replace("p:m:", "pm").replace("a:m", "am").replace("p:m", "pm")
    match = re.fullmatch(r"(\d{1,2})(?::?(\d{2}))?(?::\d{2})?(am|pm)?", text)
    if not match:
        raise ValueError(f"Could not understand the time '{value}'. Use HH:MM (24-hour).")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = match.group(3)
    if suffix == "pm" and hour < 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        raise ValueError(f"'{value}' is not a valid time.")
    return time(hour, minute)


def time_to_str(t: time) -> str:
    return t.strftime("%H:%M")


def spoken_time(t: time) -> str:
    """20:00 -> '8 PM', 20:30 -> '8:30 PM', 12:00 -> '12 PM'."""
    hour12 = t.hour % 12 or 12
    suffix = "AM" if t.hour < 12 else "PM"
    if t.minute == 0:
        return f"{hour12} {suffix}"
    return f"{hour12}:{t.minute:02d} {suffix}"


def short_date(d: date) -> str:
    """2026-10-10 -> 'Sat 10 Oct'."""
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}"


def long_date(d: date) -> str:
    """2026-10-10 -> 'Saturday 10 October 2026'."""
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}"


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _from_minutes(m: int) -> time:
    return time(m // 60, m % 60)


@dataclass
class CheckResult:
    ok: bool
    reason: str = ""  # machine code, e.g. "closed", "past", "too_many_guests"
    message: str = ""  # plain English for the LLM


# ---------------------------------------------------------------------------
# Restaurant
# ---------------------------------------------------------------------------

class Restaurant:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        with open(self.path, encoding="utf-8") as f:
            self.data = json.load(f)
        self.tz = ZoneInfo(self.data.get("timezone", "UTC"))
        tb = self.data.get("table_booking", {})
        self.tables_per_slot = int(tb.get("tables_per_time_slot", 10))
        self.slot_minutes = int(tb.get("time_slot_minutes", 60))
        self.interval_minutes = int(tb.get("booking_interval_minutes", 30))
        self.last_booking_before_close = int(tb.get("last_booking_minutes_before_close", 60))
        self.max_group_size = int(tb.get("max_group_size", 8))
        self.max_days_ahead = int(tb.get("max_days_in_advance", 90))
        self.closed_dates = {parse_date(d) for d in self.data.get("closed_dates", [])}

    @property
    def name(self) -> str:
        return self.data.get("name", "Cramble Restaurant")

    def now(self) -> datetime:
        return datetime.now(self.tz)

    # --- opening hours -----------------------------------------------------

    def hours_for(self, d: date):
        """Returns (open_time, close_time) or None if closed that day."""
        if d in self.closed_dates:
            return None
        entry = self.data.get("opening_hours", {}).get(WEEKDAYS[d.weekday()], "closed")
        if not isinstance(entry, dict):
            return None
        return parse_time(entry["open"]), parse_time(entry["close"])

    def bookable_times(self, d: date) -> list[time]:
        """All start times guests may book on a given day (ignores capacity)."""
        hours = self.hours_for(d)
        if not hours:
            return []
        start = _minutes(hours[0])
        last = _minutes(hours[1]) - self.last_booking_before_close
        return [_from_minutes(m) for m in range(start, last + 1, self.interval_minutes)]

    def slot_key(self, t: time) -> int:
        """Which capacity bucket a time belongs to (e.g. 20:00 and 20:30 share the 20:00 slot)."""
        return _minutes(t) // self.slot_minutes

    # --- validation --------------------------------------------------------

    def check_request(self, d: date, t: time, guests: int) -> CheckResult:
        now = self.now()
        if guests < 1:
            return CheckResult(False, "invalid_guests", "The number of guests must be at least 1.")
        if guests > self.max_group_size:
            return CheckResult(
                False,
                "too_many_guests",
                f"Groups larger than {self.max_group_size} are handled as event bookings. "
                "Offer to take an event booking instead.",
            )
        if datetime.combine(d, t, tzinfo=self.tz) <= now:
            return CheckResult(False, "past", "That date and time is in the past. Ask for a future time.")
        if (d - now.date()).days > self.max_days_ahead:
            return CheckResult(
                False, "too_far_ahead", f"Bookings can only be made up to {self.max_days_ahead} days ahead."
            )
        hours = self.hours_for(d)
        if not hours:
            return CheckResult(False, "closed", f"The restaurant is closed on {long_date(d)}.")
        times = self.bookable_times(d)
        if t not in times:
            if times and times[0] <= t <= times[-1]:
                return CheckResult(
                    False,
                    "bad_interval",
                    f"Bookings start every {self.interval_minutes} minutes, e.g. {spoken_time(times[0])}.",
                )
            return CheckResult(
                False,
                "outside_hours",
                f"On {long_date(d)} we're open {spoken_time(hours[0])} to {spoken_time(hours[1])}; "
                f"the last table booking is at {spoken_time(times[-1]) if times else 'n/a'}.",
            )
        return CheckResult(True)

    def find_free_slots(self, d: date, wanted: time, booked_counts: dict, limit: int = 3) -> list[time]:
        """Nearest bookable times on day d whose slot still has room. booked_counts: slot_key -> count."""
        now = self.now()
        candidates = []
        for t in self.bookable_times(d):
            if datetime.combine(d, t, tzinfo=self.tz) <= now:
                continue
            if booked_counts.get(self.slot_key(t), 0) >= self.tables_per_slot:
                continue
            if t == wanted:
                continue
            candidates.append(t)
        candidates.sort(key=lambda t: abs(_minutes(t) - _minutes(wanted)))
        return sorted(candidates[:limit])

    def next_open_days(self, after: date, count: int = 1) -> list[date]:
        days, d = [], after
        for _ in range(30):
            d += timedelta(days=1)
            if self.hours_for(d):
                days.append(d)
                if len(days) >= count:
                    break
        return days

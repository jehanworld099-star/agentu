"""Builds Emma's system prompt from system_prompt.txt + restaurant_data.json."""

from datetime import timedelta
from pathlib import Path

from .restaurant import WEEKDAYS, Restaurant, long_date, parse_date, spoken_time

GREETING = "Hi, thanks for calling Cramble Restaurant, this is Emma. How can I help you today?"


def _opening_hours(r: Restaurant) -> str:
    lines = []
    for day in WEEKDAYS:
        entry = r.data.get("opening_hours", {}).get(day, "closed")
        if isinstance(entry, dict):
            lines.append(f"{day.title()}: {entry['open']} to {entry['close']}")
        else:
            lines.append(f"{day.title()}: closed")
    closed = r.data.get("closed_dates", [])
    if closed:
        lines.append("Also closed on: " + ", ".join(long_date(parse_date(d)) for d in closed))
    return "\n".join(lines)


def _menu(r: Restaurant) -> str:
    out = []
    for category, dishes in r.data.get("menu", {}).items():
        out.append(f"{category}:")
        for dish in dishes:
            tags = ", ".join(dish.get("tags", []))
            out.append(f"- {dish['name']} — {dish['price']} — {dish.get('description', '')}"
                       + (f" [{tags}]" if tags else ""))
    return "\n".join(out)


def _events(r: Restaurant) -> str:
    ev = r.data.get("events", {})
    out = [
        f"Private hall: {ev.get('private_hall_name', 'Private hall')}, up to {ev.get('private_hall_capacity')} guests.",
        f"Deposit: {ev.get('deposit_percent')} percent. {ev.get('deposit_note', '')}".strip(),
    ]
    if ev.get("minimum_guests"):
        out.append(f"Event packages are for groups of {ev['minimum_guests']} or more.")
    out.append("Packages (price per person):")
    for p in ev.get("packages", []):
        out.append(f"- {p['name']} — {p['price_per_person']} per person — {p['includes']}")
    if ev.get("extras"):
        out.append("Extras:")
        for x in ev["extras"]:
            out.append(f"- {x['name']} — {x['price']}" + (f" ({x['note']})" if x.get("note") else ""))
    return "\n".join(out)


def _info(r: Restaurant) -> str:
    d = r.data
    lines = [f"Name: {d.get('name')}", f"Address: {d.get('address')}", f"Phone: {d.get('phone')}"]
    for key, label in (("email", "Email"), ("website", "Website"), ("parking", "Parking"),
                       ("dress_code", "Dress code")):
        if d.get(key):
            lines.append(f"{label}: {d[key]}")
    for extra in d.get("other_info", []):
        lines.append(f"- {extra}")
    return "\n".join(lines)


def _booking_rules(r: Restaurant) -> str:
    return (
        f"Tables can be booked every {r.interval_minutes} minutes, from opening time until "
        f"{r.last_booking_before_close} minutes before closing.\n"
        f"Maximum {r.max_group_size} guests per table booking; bigger groups are event bookings.\n"
        f"Bookings can be made up to {r.max_days_ahead} days ahead.\n"
        "Availability depends on how full each hour is: ALWAYS use check_availability, never guess."
    )


def _calendar(r: Restaurant) -> str:
    today = r.now().date()
    lines = []
    for i in range(15):
        d = today + timedelta(days=i)
        label = "today" if i == 0 else "tomorrow" if i == 1 else ""
        hours = r.hours_for(d)
        status = f"open {spoken_time(hours[0])} to {spoken_time(hours[1])}" if hours else "CLOSED"
        lines.append(f"{d.isoformat()} = {long_date(d)}{' (' + label + ')' if label else ''} — {status}")
    return "\n".join(lines)


def build_system_prompt(r: Restaurant, template_path: Path) -> str:
    template = Path(template_path).read_text(encoding="utf-8")
    now = r.now()
    replacements = {
        "{{NOW}}": f"{long_date(now.date())}, {spoken_time(now.time())}",
        "{{CALENDAR}}": _calendar(r),
        "{{MAX_GROUP_SIZE}}": str(r.max_group_size),
        "{{RESTAURANT_INFO}}": _info(r),
        "{{OPENING_HOURS}}": _opening_hours(r),
        "{{BOOKING_RULES}}": _booking_rules(r),
        "{{EVENTS}}": _events(r),
        "{{CURRENCY}}": r.data.get("currency_word", "dollars"),
        "{{MENU}}": _menu(r),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template

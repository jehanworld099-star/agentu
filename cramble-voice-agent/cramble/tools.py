"""The tools (functions) Emma can call during a conversation.

TOOL_SCHEMAS describes each tool to the LLM. AgentTools holds the actual logic.
Nothing in here depends on Pipecat, so it can be tested on its own.
"""

import logging
import re
from collections import Counter

from .notifications import notify_owner
from .restaurant import (CheckResult, Restaurant, long_date, parse_date, parse_time, short_date,
                         spoken_time, time_to_str)
from .storage import CALLBACK, EVENT, TABLE, BaseStore, FailsafeLog

log = logging.getLogger("cramble.tools")

FALLBACK_SAY = "I've taken your details, our team will call you shortly to confirm."

TOOL_SCHEMAS = [
    {
        "name": "check_availability",
        "description": "Check if a table is free for a date, time and party size. Call this BEFORE "
                       "repeating the booking back to the guest.",
        "properties": {
            "date": {"type": "string", "description": "Booking date in YYYY-MM-DD format."},
            "time": {"type": "string", "description": "Booking time in 24-hour HH:MM format, e.g. 20:00."},
            "guests": {"type": "integer", "description": "Number of guests."},
        },
        "required": ["date", "time", "guests"],
    },
    {
        "name": "save_table_booking",
        "description": "Save a table booking. Only call AFTER the guest has confirmed all details are correct.",
        "properties": {
            "guest_name": {"type": "string", "description": "Name the booking is under."},
            "phone": {"type": "string", "description": "Guest phone number, digits only (may start with +)."},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "time": {"type": "string", "description": "24-hour HH:MM"},
            "guests": {"type": "integer", "description": "Number of guests."},
            "special_request": {"type": "string",
                                "description": "Birthday, high chair, window seat, allergies, etc. "
                                               "Use 'None' if there is nothing."},
        },
        "required": ["guest_name", "phone", "date", "time", "guests"],
    },
    {
        "name": "save_event_booking",
        "description": "Save an event booking request (birthday, anniversary, corporate dinner, party, or any "
                       "group bigger than the max table size). Only call AFTER the guest confirmed the details.",
        "properties": {
            "guest_name": {"type": "string"},
            "phone": {"type": "string", "description": "Digits only (may start with +)."},
            "email": {"type": "string", "description": "Email address written normally, e.g. sarah@gmail.com"},
            "event_type": {"type": "string", "description": "e.g. Birthday, Anniversary, Corporate dinner"},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "time": {"type": "string", "description": "24-hour HH:MM"},
            "guests": {"type": "integer"},
            "budget_per_person": {"type": "string", "description": "e.g. '50 dollars' or 'not sure'"},
            "food_preference": {"type": "string", "description": "Set menu, a la carte, or a package name."},
            "decoration_or_cake": {"type": "string", "description": "What decoration or cake they want, or 'None'."},
            "notes": {"type": "string", "description": "Anything else: allergies, dietary needs, timing, etc."},
        },
        "required": ["guest_name", "phone", "event_type", "date", "time", "guests"],
    },
    {
        "name": "save_callback_request",
        "description": "Ask a manager or team member to call the guest back: complaints, questions you can't "
                       "answer, or anything you cannot handle.",
        "properties": {
            "guest_name": {"type": "string"},
            "phone": {"type": "string", "description": "Digits only (may start with +)."},
            "reason": {"type": "string", "description": "Short summary of why they need a call back."},
        },
        "required": ["guest_name", "phone", "reason"],
    },
]


def clean_phone(value) -> str:
    text = str(value or "").strip()
    plus = text.startswith("+")
    digits = re.sub(r"\D", "", text)
    return ("+" if plus else "") + digits


def _clean(value, default="") -> str:
    text = str(value if value is not None else "").strip()
    return text or default


def _slot(t) -> dict:
    return {"time": time_to_str(t), "say": spoken_time(t)}


class AgentTools:
    def __init__(self, restaurant: Restaurant, store: BaseStore, failsafe: FailsafeLog):
        self.restaurant = restaurant
        self.store = store
        self.failsafe = failsafe

    # ------------------------------------------------------------------ helpers

    async def _counts_for(self, d) -> Counter:
        rows = await self.store.rows(TABLE)
        counts = Counter()
        for r in rows:
            if str(r.get("Status", "")).strip().lower() in ("cancelled", "canceled"):
                continue
            try:
                if parse_date(r.get("Date", "")) != d:
                    continue
                counts[self.restaurant.slot_key(parse_time(r.get("Time", "")))] += 1
            except ValueError:
                continue  # ignore rows the team typed in an odd format
        return counts

    def _suggest_other_days(self, after) -> list:
        out = []
        for day in self.restaurant.next_open_days(after, count=2):
            times = self.restaurant.bookable_times(day)
            if times:
                out.append({"date": day.isoformat(), "day": long_date(day),
                            "hours": f"{spoken_time(times[0])} to {spoken_time(times[-1])} (last booking)"})
        return out

    async def _save(self, kind: str, fields: dict, subject: str, intro: str) -> dict:
        now = self.restaurant.now()
        try:
            row = await self.store.add(kind, fields, now)
        except Exception as e:
            log.exception("Saving %s failed, writing failsafe log", kind)
            ref = self.failsafe.write(kind, fields, str(e), now)
            await notify_owner(
                "ACTION NEEDED - not saved to sheet: " + subject,
                {"Reference": ref, **fields, "Error": str(e)},
                "The booking system had a problem, so this request was NOT added to the Google Sheet. "
                "Please add it manually and call the guest to confirm.",
            )
            return {"success": False, "saved_for_follow_up": True,
                    "instruction": f"Tell the guest exactly: \"{FALLBACK_SAY}\""}
        await notify_owner(subject, row, intro)
        return {"success": True, "id": row.get("Booking ID") or row.get("ID"), "status": "Pending"}

    def _validate(self, date, time, guests):
        """Returns (date, time, guests, error_dict_or_None)."""
        try:
            d = parse_date(date)
            t = parse_time(time)
            g = int(guests)
        except (ValueError, TypeError) as e:
            return None, None, None, {"error": str(e)}
        check: CheckResult = self.restaurant.check_request(d, t, g)
        if not check.ok:
            result = {"reason": check.reason, "message": check.message}
            if check.reason in ("closed", "outside_hours", "bad_interval"):
                same_day = self.restaurant.bookable_times(d)
                if same_day and check.reason != "closed":
                    result["bookable_times_that_day"] = f"{spoken_time(same_day[0])} to {spoken_time(same_day[-1])}"
                else:
                    result["next_open_days"] = self._suggest_other_days(d)
            return d, t, g, result
        return d, t, g, None

    # ------------------------------------------------------------------ tools

    async def check_availability(self, date, time, guests, **_) -> dict:
        d, t, g, error = self._validate(date, time, guests)
        if error:
            return {"available": False, **error}
        try:
            counts = await self._counts_for(d)
        except Exception as e:
            log.exception("Could not read bookings")
            return {"available": None, "reason": "system_unavailable",
                    "message": "The booking system can't be checked right now. You may still take the details "
                               f"and call save_table_booking; it will be confirmed by the team. ({e})"}
        free = counts.get(self.restaurant.slot_key(t), 0) < self.restaurant.tables_per_slot
        result = {"available": free, "date": d.isoformat(), "day": long_date(d), "time": time_to_str(t),
                  "say_time": spoken_time(t), "guests": g}
        if not free:
            alternatives = self.restaurant.find_free_slots(d, t, counts)
            if alternatives:
                result["nearest_free_times_same_day"] = [_slot(x) for x in alternatives]
            else:
                result["message"] = "That whole day is fully booked."
                result["next_open_days"] = self._suggest_other_days(d)
        return result

    async def save_table_booking(self, guest_name, phone, date, time, guests, special_request="", **_) -> dict:
        d, t, g, error = self._validate(date, time, guests)
        if error:
            return {"success": False, **error}
        phone = clean_phone(phone)
        if len(phone.lstrip("+")) < 7:
            return {"success": False, "reason": "bad_phone",
                    "message": "That phone number looks too short. Ask the guest to repeat it."}
        try:
            counts = await self._counts_for(d)
            if counts.get(self.restaurant.slot_key(t), 0) >= self.restaurant.tables_per_slot:
                alternatives = self.restaurant.find_free_slots(d, t, counts)
                return {"success": False, "reason": "full",
                        "message": "That time just filled up.",
                        "nearest_free_times_same_day": [_slot(x) for x in alternatives]}
        except Exception:
            log.exception("Availability re-check failed; trying to save anyway")
        name = _clean(guest_name, "Guest")
        fields = {"Name": name, "Phone": phone, "Date": d.isoformat(), "Time": time_to_str(t), "Guests": g,
                  "Special Request": _clean(special_request, "None")}
        subject = f"New Table Booking — {name}, {g} guest{'s' if g != 1 else ''}, {short_date(d)} {spoken_time(t)}"
        return await self._save(TABLE, fields, subject, "A new table booking was just made over the phone.")

    async def save_event_booking(self, guest_name, phone, date, time, guests, event_type, email="",
                                 budget_per_person="", food_preference="", decoration_or_cake="", notes="",
                                 **_) -> dict:
        try:
            d = parse_date(date)
        except ValueError as e:
            return {"success": False, "error": str(e)}
        try:
            time_value = time_to_str(parse_time(time))
            say_time = spoken_time(parse_time(time))
        except ValueError:
            time_value = say_time = _clean(time, "TBC")
        if d < self.restaurant.now().date():
            return {"success": False, "reason": "past", "message": "That date is in the past."}
        if not self.restaurant.hours_for(d):
            note = f"Note: the restaurant is normally closed on {long_date(d)}. "
            notes = note + _clean(notes)
        phone = clean_phone(phone)
        if len(phone.lstrip("+")) < 7:
            return {"success": False, "reason": "bad_phone",
                    "message": "That phone number looks too short. Ask the guest to repeat it."}
        try:
            g = int(guests)
        except (TypeError, ValueError):
            g = _clean(guests, "TBC")
        name = _clean(guest_name, "Guest")
        event_type = _clean(event_type, "Event")
        fields = {"Name": name, "Phone": phone, "Email": _clean(email, "Not given"), "Event Type": event_type,
                  "Date": d.isoformat(), "Time": time_value, "Guests": g,
                  "Budget/Person": _clean(budget_per_person, "Not given"),
                  "Food Preference": _clean(food_preference, "Not decided"),
                  "Decoration/Cake": _clean(decoration_or_cake, "None"), "Notes": _clean(notes, "None")}
        subject = f"New Event Booking — {event_type}, {name}, {g} guests, {short_date(d)} {say_time}"
        return await self._save(EVENT, fields, subject,
                                 "A new event enquiry came in. Please call the guest within 24 hours to confirm.")

    async def save_callback_request(self, guest_name, phone, reason, **_) -> dict:
        phone = clean_phone(phone)
        if len(phone.lstrip("+")) < 7:
            return {"success": False, "reason": "bad_phone",
                    "message": "That phone number looks too short. Ask the guest to repeat it."}
        name = _clean(guest_name, "Guest")
        reason = _clean(reason, "Not specified")
        fields = {"Name": name, "Phone": phone, "Reason": reason}
        short_reason = reason if len(reason) <= 60 else reason[:57] + "..."
        subject = f"Callback Request — {name}: {short_reason}"
        return await self._save(CALLBACK, fields, subject, "A guest asked for someone from the team to call them back.")

    async def call(self, name: str, arguments: dict) -> dict:
        """Runs a tool by name. Never raises (the LLM always gets an answer)."""
        func = getattr(self, name, None)
        if name not in {s["name"] for s in TOOL_SCHEMAS} or func is None:
            return {"error": f"Unknown tool {name}"}
        try:
            result = await func(**(arguments or {}))
        except TypeError as e:
            result = {"success": False, "error": f"Missing or wrong details: {e}"}
        except Exception as e:
            log.exception("Tool %s crashed", name)
            result = {"success": False, "error": str(e), "instruction": f"Tell the guest exactly: \"{FALLBACK_SAY}\""}
        log.info("Tool %s(%s) -> %s", name, arguments, result)
        return result

"""Tests for the booking logic. Run with:  python -m unittest discover tests"""

import asyncio
import csv
import sys
import tempfile
import unittest
from datetime import datetime, time
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cramble import backup, config, notifications  # noqa: E402
from cramble.prompt import build_system_prompt  # noqa: E402
from cramble.restaurant import Restaurant, parse_time, spoken_time  # noqa: E402
from cramble.storage import TABLE, FailsafeLog, LocalCSVStore  # noqa: E402
from cramble.tools import AgentTools  # noqa: E402


def run(coro):
    return asyncio.run(coro)


class BrokenStore(LocalCSVStore):
    def _append_row(self, kind, values):
        raise ConnectionError("Google Sheets is down")


class LogicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.r = Restaurant(ROOT / "restaurant_data.json")
        # Pretend it's Monday 5 Oct 2026, 10:00 in the restaurant's timezone.
        self.r.now = lambda: datetime(2026, 10, 5, 10, 0, tzinfo=self.r.tz)
        self.store = LocalCSVStore(self.tmp / "bookings")
        self.store.setup()
        self.tools = AgentTools(self.r, self.store, FailsafeLog(self.tmp))
        self.sent = []

        async def fake_notify(subject, fields, intro=""):
            self.sent.append((subject, fields))
            return True

        patcher = mock.patch("cramble.tools.notify_owner", fake_notify)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_time_parsing(self):
        self.assertEqual(parse_time("8 PM"), time(20, 0))
        self.assertEqual(parse_time("8:30pm"), time(20, 30))
        self.assertEqual(parse_time("20:00"), time(20, 0))
        self.assertEqual(parse_time("12 am"), time(0, 0))
        self.assertEqual(spoken_time(time(20, 30)), "8:30 PM")
        self.assertEqual(spoken_time(time(12, 0)), "12 PM")

    def test_rules(self):
        c = self.tools.check_availability
        self.assertEqual(run(c("2026-10-05", "19:00", 2))["reason"], "closed")          # Monday
        self.assertEqual(run(c("2026-10-01", "19:00", 2))["reason"], "past")
        self.assertEqual(run(c("2026-10-09", "19:00", 12))["reason"], "too_many_guests")
        self.assertEqual(run(c("2026-10-09", "23:00", 2))["reason"], "outside_hours")   # Fri closes 23:00
        self.assertEqual(run(c("2026-10-09", "19:15", 2))["reason"], "bad_interval")
        self.assertEqual(run(c("2026-12-25", "19:00", 2))["reason"], "closed")          # holiday
        self.assertTrue(run(c("2026-10-09", "22:00", 2))["available"])                  # last booking ok

    def test_booking_flow_ids_email_and_capacity(self):
        res = run(self.tools.save_table_booking("Sarah", "+1 555-123-4567", "2026-10-09", "8 PM", 4, "Birthday"))
        self.assertTrue(res["success"])
        self.assertEqual(res["id"], "CR-T-0001")
        subject, fields = self.sent[-1]
        self.assertEqual(subject, "New Table Booking — Sarah, 4 guests, Fri 9 Oct 8 PM")
        self.assertEqual(fields["Phone"], "+15551234567")
        self.assertEqual(fields["Status"], "Pending")

        # Fill the 8 PM hour (10 tables; 20:30 shares the same hour slot).
        for i in range(9):
            run(self.tools.save_table_booking(f"G{i}", "5551112222", "2026-10-09", "20:30", 2))
        full = run(self.tools.check_availability("2026-10-09", "20:00", 2))
        self.assertFalse(full["available"])
        alts = [a["time"] for a in full["nearest_free_times_same_day"]]
        self.assertEqual(alts, ["19:00", "19:30", "21:00"])
        self.assertEqual(run(self.tools.save_table_booking("Late", "5551112222", "2026-10-09", "20:00", 2))["reason"],
                         "full")
        # Other days unaffected; next ID continues.
        self.assertEqual(run(self.tools.save_table_booking("Tom", "5551112222", "2026-10-10", "20:00", 2))["id"],
                         "CR-T-0011")

    def test_cancelled_rows_free_up_space(self):
        for i in range(10):
            run(self.tools.save_table_booking(f"G{i}", "5551112222", "2026-10-09", "20:00", 2))
        path = self.store._path(TABLE)
        rows = list(csv.reader(open(path)))
        rows[1][7] = "Cancelled"
        with open(path, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        self.assertTrue(run(self.tools.check_availability("2026-10-09", "20:00", 2))["available"])

    def test_event_and_callback(self):
        res = run(self.tools.save_event_booking(
            guest_name="Priya", phone="555 222 3333", email="priya@gmail.com", event_type="Birthday",
            date="2026-10-24", time="19:00", guests=25, budget_per_person="50 dollars",
            food_preference="Premium Party", decoration_or_cake="Cake and balloons", notes="One nut allergy"))
        self.assertEqual(res["id"], "CR-E-0001")
        self.assertEqual(self.sent[-1][0], "New Event Booking — Birthday, Priya, 25 guests, Sat 24 Oct 7 PM")
        res = run(self.tools.save_callback_request("Mark", "5559998888", "Complaint about cold food"))
        self.assertEqual(res["id"], "CR-C-0001")
        self.assertEqual(self.sent[-1][0], "Callback Request — Mark: Complaint about cold food")

    def test_sheet_failure_uses_failsafe(self):
        broken = BrokenStore(self.tmp / "b2")
        broken.setup()
        tools = AgentTools(self.r, broken, FailsafeLog(self.tmp))
        res = run(tools.save_table_booking("Sarah", "5551234567", "2026-10-09", "20:00", 4))
        self.assertFalse(res["success"])
        self.assertIn("our team will call you shortly", res["instruction"])
        log_text = (self.tmp / "unsaved_bookings_failsafe.csv").read_text()
        self.assertIn("Sarah", log_text)
        self.assertTrue(self.sent[-1][0].startswith("ACTION NEEDED"))

    def test_unknown_tool_and_bad_args_never_raise(self):
        self.assertIn("error", run(self.tools.call("delete_everything", {})))
        self.assertFalse(run(self.tools.call("save_table_booking", {"guest_name": "x"}))["success"])
        self.assertIn("error", run(self.tools.call("check_availability",
                                                   {"date": "someday", "time": "20:00", "guests": 2})))

    def test_prompt_contains_data_and_dates(self):
        prompt = build_system_prompt(self.r, ROOT / "system_prompt.txt")
        self.assertNotIn("{{", prompt)
        self.assertIn("Grilled Lamb Chops — 24", prompt)
        self.assertIn("2026-10-09 = Friday 9 October 2026", prompt)
        self.assertIn("Monday 5 October 2026 (today)", prompt)
        self.assertIn("groups larger than 8 guests", prompt)
        self.assertIn("The Garden Room", prompt)

    def test_daily_backup(self):
        run(self.tools.save_table_booking("Sarah", "5551234567", "2026-10-09", "20:00", 4))
        folder = run(backup.backup_now(self.store, self.tmp / "backups", self.r.now()))
        self.assertIn("Sarah", (folder / "table_bookings.csv").read_text())
        self.assertTrue((folder / "callbacks.csv").exists())

    def test_email_skipped_when_not_configured(self):
        with mock.patch.object(config, "OWNER_EMAIL", ""):
            self.assertFalse(run(notifications.notify_owner("x", {"a": 1})))


if __name__ == "__main__":
    unittest.main()

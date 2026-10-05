"""Where bookings are saved.

- SheetsStore: the real Google Sheet (used when GOOGLE_SHEET_ID + credentials are set).
- LocalCSVStore: CSV files in the data/ folder (used for testing before Google is set up).
- FailsafeLog: if saving to the sheet fails mid-call, details are written here so nothing is lost.
"""

import asyncio
import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from . import config

log = logging.getLogger("cramble.storage")

TABLE, EVENT, CALLBACK = "table", "event", "callback"

TABS = {
    TABLE: {
        "title": "Table Bookings",
        "prefix": "CR-T",
        "headers": ["Booking ID", "Name", "Phone", "Date", "Time", "Guests", "Special Request", "Status", "Booked At"],
        "time_header": "Booked At",
    },
    EVENT: {
        "title": "Event Bookings",
        "prefix": "CR-E",
        "headers": [
            "Booking ID", "Name", "Phone", "Email", "Event Type", "Date", "Time", "Guests",
            "Budget/Person", "Food Preference", "Decoration/Cake", "Notes", "Status", "Booked At",
        ],
        "time_header": "Booked At",
    },
    CALLBACK: {
        "title": "Callbacks",
        "prefix": "CR-C",
        "headers": ["ID", "Name", "Phone", "Reason", "Status", "Created At"],
        "time_header": "Created At",
    },
}
STATUS_OPTIONS = ["Pending", "Ready", "Done", "Cancelled"]


def _next_id(prefix: str, existing_ids) -> str:
    highest = 0
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    for value in existing_ids:
        m = pattern.match(str(value).strip())
        if m:
            highest = max(highest, int(m.group(1)))
    return f"{prefix}-{highest + 1:04d}"


class BaseStore:
    """Shared logic. Subclasses implement _read_rows / _append_row (blocking)."""

    name = "base"

    def __init__(self):
        self._lock = asyncio.Lock()

    def setup(self):  # create tabs / files
        pass

    def _read_rows(self, kind: str) -> list[dict]:
        raise NotImplementedError

    def _append_row(self, kind: str, values: list):
        raise NotImplementedError

    async def rows(self, kind: str) -> list[dict]:
        return await asyncio.to_thread(self._read_rows, kind)

    async def add(self, kind: str, fields: dict, now: datetime) -> dict:
        """Adds a row. `fields` uses the tab's header names (without ID/Status/timestamp)."""
        tab = TABS[kind]
        id_header = tab["headers"][0]
        async with self._lock:
            existing = await self.rows(kind)
            row = dict(fields)
            row[id_header] = _next_id(tab["prefix"], (r.get(id_header, "") for r in existing))
            row["Status"] = "Pending"
            row[tab["time_header"]] = now.strftime("%Y-%m-%d %H:%M")
            values = [str(row.get(h, "")) for h in tab["headers"]]
            await asyncio.to_thread(self._append_row, kind, values)
        return row

    async def export_all(self) -> dict:
        return {kind: await self.rows(kind) for kind in TABS}


class LocalCSVStore(BaseStore):
    name = "local CSV files"

    def __init__(self, folder: Path):
        super().__init__()
        self.folder = Path(folder)

    def _path(self, kind):
        return self.folder / (TABS[kind]["title"].lower().replace(" ", "_") + ".csv")

    def setup(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        for kind, tab in TABS.items():
            path = self._path(kind)
            if not path.exists():
                with open(path, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(tab["headers"])

    def _read_rows(self, kind):
        path = self._path(kind)
        if not path.exists():
            return []
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _append_row(self, kind, values):
        self.setup()
        with open(self._path(kind), "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(values)


class SheetsStore(BaseStore):
    name = "Google Sheets"

    def __init__(self, sheet_id: str):
        super().__init__()
        self.sheet_id = sheet_id
        self._spreadsheet = None
        self._worksheets = {}

    def _client(self):
        import gspread

        if config.GOOGLE_SERVICE_ACCOUNT_JSON:
            return gspread.service_account_from_dict(json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON))
        path = Path(config.GOOGLE_SERVICE_ACCOUNT_FILE)
        if not path.is_absolute():
            path = config.PROJECT_ROOT / path
        return gspread.service_account(filename=str(path))

    def _sheet(self):
        if self._spreadsheet is None:
            self._spreadsheet = self._client().open_by_key(self.sheet_id)
        return self._spreadsheet

    def _ws(self, kind):
        if kind not in self._worksheets:
            self._worksheets[kind] = self._ensure_tab(kind)
        return self._worksheets[kind]

    def _ensure_tab(self, kind):
        """Creates the tab and header row if they don't exist yet."""
        import gspread

        tab = TABS[kind]
        sh = self._sheet()
        try:
            ws = sh.worksheet(tab["title"])
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab["title"], rows=1000, cols=len(tab["headers"]))
            log.info("Created tab '%s'", tab["title"])
        first_row = ws.row_values(1)
        if not any(first_row):
            ws.update(range_name="A1", values=[tab["headers"]])
            self._decorate(ws, tab)
        return ws

    def _decorate(self, ws, tab):
        """Bold header, frozen first row, and a Pending/Ready/Done dropdown in Status."""
        try:
            ws.freeze(rows=1)
            ws.format("1:1", {"textFormat": {"bold": True}})
            col = tab["headers"].index("Status")
            self._sheet().batch_update({"requests": [{
                "setDataValidation": {
                    "range": {"sheetId": ws.id, "startRowIndex": 1, "startColumnIndex": col,
                              "endColumnIndex": col + 1},
                    "rule": {
                        "condition": {"type": "ONE_OF_LIST",
                                      "values": [{"userEnteredValue": s} for s in STATUS_OPTIONS]},
                        "showCustomUi": True,
                        "strict": False,
                    },
                }
            }]})
        except Exception as e:  # cosmetic only, never fatal
            log.warning("Could not format tab %s: %s", tab["title"], e)

    def setup(self):
        for kind in TABS:
            self._ws(kind)
        # Remove the empty default "Sheet1" tab if it's still there and blank.
        try:
            sh = self._sheet()
            if len(sh.worksheets()) > len(TABS):
                default = sh.worksheet("Sheet1")
                if not any(default.get_all_values()):
                    sh.del_worksheet(default)
        except Exception:
            pass

    def _read_rows(self, kind):
        values = self._ws(kind).get_all_values()
        if not values:
            return []
        headers = values[0]
        return [dict(zip(headers, row + [""] * (len(headers) - len(row)))) for row in values[1:] if any(row)]

    def _append_row(self, kind, values):
        # RAW keeps phone numbers like +1555... and dates exactly as written.
        self._ws(kind).append_row(values, value_input_option="RAW", table_range="A1")


class FailsafeLog:
    """Last-resort local log used when the main store fails during a call."""

    def __init__(self, folder: Path):
        self.path = Path(folder) / "unsaved_bookings_failsafe.csv"

    def write(self, kind: str, fields: dict, error: str, now: datetime) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        ref = f"{TABS[kind]['prefix']}-L{now.strftime('%m%d%H%M%S')}"
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["Reference", "Type", "Logged At", "Details (JSON)", "Error"])
            w.writerow([ref, TABS[kind]["title"], now.strftime("%Y-%m-%d %H:%M"),
                        json.dumps(fields, ensure_ascii=False), error])
        return ref


def create_store() -> BaseStore:
    if config.sheets_configured():
        store = SheetsStore(config.GOOGLE_SHEET_ID)
    else:
        log.warning("Google Sheets is not set up yet -> saving bookings to local CSV files in %s",
                    config.DATA_DIR / "bookings")
        store = LocalCSVStore(config.DATA_DIR / "bookings")
    return store

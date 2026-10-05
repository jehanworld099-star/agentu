"""Saves a copy of every tab to local CSV files once a day (in case Google Sheets is down)."""

import asyncio
import csv
import logging
from datetime import datetime
from pathlib import Path

from .storage import TABS, BaseStore

log = logging.getLogger("cramble.backup")


async def backup_now(store: BaseStore, folder: Path, now: datetime) -> Path:
    target = Path(folder) / now.strftime("%Y-%m-%d")
    target.mkdir(parents=True, exist_ok=True)
    data = await store.export_all()
    for kind, rows in data.items():
        tab = TABS[kind]
        path = target / (tab["title"].lower().replace(" ", "_") + ".csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=tab["headers"], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    log.info("Daily backup saved to %s", target)
    return target


async def daily_backup_loop(store: BaseStore, folder: Path, now_fn, check_every_seconds: int = 3600):
    """Runs forever: makes one backup per calendar day (checks every hour)."""
    while True:
        try:
            now = now_fn()
            if not (Path(folder) / now.strftime("%Y-%m-%d")).exists():
                await backup_now(store, folder, now)
        except Exception as e:
            log.error("Daily backup failed (will retry in an hour): %s", e)
        await asyncio.sleep(check_every_seconds)

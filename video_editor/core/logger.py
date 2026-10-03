"""Shared logging setup.

Every module should call get_logger(__name__) instead of configuring
logging itself, so output is consistent and always readable.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def get_logger(name: str = "video_editor") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(_LOG_DIR / "app.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning(
            "Could not create log file in %s; logging to console only.", _LOG_DIR
        )

    return logger

"""Reads settings from the .env file (or from Railway's Variables)."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else default


# --- AI services ---
GROQ_API_KEY = env("GROQ_API_KEY")
GROQ_LLM_MODEL = env("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
GROQ_STT_MODEL = env("GROQ_STT_MODEL", "whisper-large-v3-turbo")
CARTESIA_API_KEY = env("CARTESIA_API_KEY")
# Default voice: a warm, friendly female voice. Change it in .env if you prefer another.
CARTESIA_VOICE_ID = env("CARTESIA_VOICE_ID", "156fb8d2-335b-4950-9cb3-a2d33befec77")

# --- Google Sheets ---
GOOGLE_SHEET_ID = env("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_FILE = env("GOOGLE_SERVICE_ACCOUNT_FILE", "google-credentials.json")
GOOGLE_SERVICE_ACCOUNT_JSON = env("GOOGLE_SERVICE_ACCOUNT_JSON")  # whole JSON pasted (used on Railway)

# --- Email alerts ---
OWNER_EMAIL = env("OWNER_EMAIL")
GMAIL_ADDRESS = env("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD").replace(" ", "")

# --- Twilio (optional) ---
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
PUBLIC_URL = env("PUBLIC_URL").rstrip("/")  # e.g. https://cramble.up.railway.app

# --- Files & server ---
RESTAURANT_DATA_FILE = Path(env("RESTAURANT_DATA_FILE", str(PROJECT_ROOT / "restaurant_data.json")))
SYSTEM_PROMPT_FILE = Path(env("SYSTEM_PROMPT_FILE", str(PROJECT_ROOT / "system_prompt.txt")))
DATA_DIR = Path(env("DATA_DIR", str(PROJECT_ROOT / "data")))
PORT = int(env("PORT", "7860"))
HOST = env("HOST", "0.0.0.0")


def sheets_configured() -> bool:
    has_creds = bool(GOOGLE_SERVICE_ACCOUNT_JSON) or (PROJECT_ROOT / GOOGLE_SERVICE_ACCOUNT_FILE).exists() \
        or Path(GOOGLE_SERVICE_ACCOUNT_FILE).exists()
    return bool(GOOGLE_SHEET_ID) and has_creds


def email_configured() -> bool:
    return bool(OWNER_EMAIL and GMAIL_ADDRESS and GMAIL_APP_PASSWORD)


def twilio_configured() -> bool:
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)

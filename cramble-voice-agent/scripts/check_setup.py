"""Checks every key in your .env file and tells you what works.

Run:  python scripts/check_setup.py
Add --email to also send yourself a test email.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _http import request  # noqa: E402

from cramble import config  # noqa: E402
from cramble.notifications import notify_owner  # noqa: E402
from cramble.restaurant import Restaurant  # noqa: E402

OK, BAD, SKIP = "  [OK]  ", "  [!!]  ", "  [--]  "
problems = 0


def report(ok, label, detail=""):
    global problems
    if ok is None:
        print(f"{SKIP}{label} {detail}")
    elif ok:
        print(f"{OK}{label} {detail}")
    else:
        problems += 1
        print(f"{BAD}{label} {detail}")


def main():
    print("\nChecking your Cramble voice agent setup...\n")
    env_file = config.PROJECT_ROOT / ".env"
    report(env_file.exists(), ".env file", "found" if env_file.exists() else
           "NOT found. Copy .env.example to .env and fill it in.")

    try:
        r = Restaurant(config.RESTAURANT_DATA_FILE)
        dishes = sum(len(v) for v in r.data.get("menu", {}).values())
        report(True, "restaurant_data.json", f"loaded ({dishes} dishes, timezone {r.data.get('timezone')})")
    except Exception as e:
        report(False, "restaurant_data.json", f"has a mistake: {e}\n          Tip: paste it into jsonlint.com to find it.")

    # Groq
    if not config.GROQ_API_KEY:
        report(False, "Groq", "GROQ_API_KEY is empty")
    else:
        status, data = request("https://api.groq.com/openai/v1/models",
                               headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"})
        if status == 200:
            ids = {m["id"] for m in data.get("data", [])}
            for model in (config.GROQ_LLM_MODEL, config.GROQ_STT_MODEL):
                report(model in ids, f"Groq model {model}", "available" if model in ids else "NOT available on your account")
        else:
            report(False, "Groq", f"key rejected ({status}). Copy the key again from console.groq.com/keys")

    # Cartesia
    if not config.CARTESIA_API_KEY:
        report(False, "Cartesia", "CARTESIA_API_KEY is empty")
    else:
        status, data = request(f"https://api.cartesia.ai/voices/{config.CARTESIA_VOICE_ID}",
                               headers={"X-API-Key": config.CARTESIA_API_KEY, "Cartesia-Version": "2025-04-16"})
        if status == 200:
            report(True, "Cartesia", f"key works, voice = {data.get('name', config.CARTESIA_VOICE_ID)}")
        elif status in (401, 403):
            report(False, "Cartesia", f"key rejected ({status}). Copy it again from play.cartesia.ai")
        else:
            report(False, "Cartesia voice", f"voice id {config.CARTESIA_VOICE_ID} not found ({status})")

    # Google Sheets
    if not config.sheets_configured():
        report(None, "Google Sheets", "not set up yet -> bookings go to data/bookings/*.csv (fine for testing)")
    else:
        try:
            from cramble.storage import SheetsStore

            s = SheetsStore(config.GOOGLE_SHEET_ID)
            s.setup()
            report(True, "Google Sheets", f"connected to '{s._sheet().title}', tabs ready")
        except Exception as e:
            msg = str(e) or type(e).__name__
            if "403" in msg or "PERMISSION" in msg.upper():
                msg += "\n          Tip: share the sheet with the client_email from your credentials file (Editor)."
            report(False, "Google Sheets", msg)

    # Email
    if not config.email_configured():
        report(None, "Owner email", "not set up yet (OWNER_EMAIL / GMAIL_ADDRESS / GMAIL_APP_PASSWORD)")
    elif "--email" in sys.argv:
        sent = asyncio.run(notify_owner("Test alert from Emma", {"Message": "Email alerts are working!"}))
        report(sent, "Owner email", f"test email sent to {config.OWNER_EMAIL}" if sent else
               "failed. Check the app password (16 letters) and that 2-Step Verification is on.")
    else:
        report(None, "Owner email", "configured. Run with --email to send a test email.")

    # Twilio
    report(None if not config.twilio_configured() else True, "Twilio",
           "configured" if config.twilio_configured() else "not set up (optional, only for real phone calls)")

    print("\nAll good! Run:  python server.py\n" if problems == 0 else f"\n{problems} thing(s) to fix above.\n")


if __name__ == "__main__":
    main()

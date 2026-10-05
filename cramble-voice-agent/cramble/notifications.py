"""Emails the owner about every new booking / callback (Gmail SMTP + app password)."""

import asyncio
import html
import logging
import smtplib
import ssl
from email.message import EmailMessage

from . import config

log = logging.getLogger("cramble.email")


def _send_sync(subject: str, fields: dict, intro: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"Emma at Cramble <{config.GMAIL_ADDRESS}>"
    msg["To"] = config.OWNER_EMAIL

    width = max(len(k) for k in fields) if fields else 0
    text_lines = [intro, ""] + [f"{k.ljust(width)} : {v}" for k, v in fields.items()]
    text_lines += ["", "Update the Status column in the Google Sheet when it's handled."]
    msg.set_content("\n".join(text_lines))

    rows = "".join(
        f"<tr><td style='padding:6px 12px;color:#666;white-space:nowrap'>{html.escape(str(k))}</td>"
        f"<td style='padding:6px 12px;font-weight:600'>{html.escape(str(v)) or '&mdash;'}</td></tr>"
        for k, v in fields.items()
    )
    msg.add_alternative(
        f"""<div style="font-family:Arial,sans-serif;max-width:560px">
<h2 style="color:#7a3e1d;margin-bottom:4px">{html.escape(subject)}</h2>
<p style="color:#333">{html.escape(intro)}</p>
<table style="border-collapse:collapse;background:#faf6f2;border-radius:8px">{rows}</table>
<p style="color:#888;font-size:12px">Update the Status column in the Google Sheet when it's handled.</p>
</div>""",
        subtype="html",
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=20) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.send_message(msg)


async def notify_owner(subject: str, fields: dict, intro: str = "") -> bool:
    """Never raises: a failed email must not break the phone call."""
    if not config.email_configured():
        log.info("Email not set up yet, skipping alert: %s", subject)
        return False
    try:
        await asyncio.to_thread(_send_sync, subject, fields, intro or "A new request just came in from the voice agent.")
        log.info("Owner alert sent: %s", subject)
        return True
    except Exception as e:
        log.error("Could not send owner email (%s): %s", subject, e)
        return False

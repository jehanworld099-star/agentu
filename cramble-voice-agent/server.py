"""Cramble voice agent server.

Run:  python server.py     then open http://localhost:7860 and click "Start Call".

Routes
  GET  /                 browser test page (talk to Emma with your microphone)
  POST /api/offer        WebRTC handshake for the browser page
  POST /twilio/incoming  Twilio "A call comes in" webhook (returns TwiML)
  WS   /twilio/ws        Twilio Media Stream (the actual phone audio)
  GET  /health           health check for Railway
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from xml.sax.saxutils import escape

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request, WebSocket
from fastapi.responses import FileResponse, JSONResponse, Response

from cramble import config
from cramble.backup import daily_backup_loop
from cramble.restaurant import Restaurant
from cramble.storage import FailsafeLog, create_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("cramble.server")

store = create_store()
failsafe = FailsafeLog(config.DATA_DIR)
webrtc_connections = {}


def _check_keys():
    missing = [k for k in ("GROQ_API_KEY", "CARTESIA_API_KEY") if not getattr(config, k)]
    if missing:
        log.error("Missing in .env: %s — Emma can't talk until you add them.", ", ".join(missing))
    log.info("Bookings will be saved to: %s", store.name)
    log.info("Owner email alerts: %s", "ON" if config.email_configured() else "OFF (not set up yet)")
    log.info("Twilio phone calls: %s", "ON" if config.twilio_configured() else "OFF (optional)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_keys()
    try:
        await asyncio.to_thread(store.setup)  # creates the sheet tabs + headers on first run
        log.info("Storage ready (%s)", store.name)
    except Exception as e:
        log.error("Could not set up %s: %s. Bookings will go to the failsafe log until fixed.", store.name, e)
    restaurant = Restaurant(config.RESTAURANT_DATA_FILE)
    backup_task = asyncio.create_task(daily_backup_loop(store, config.DATA_DIR / "backups", restaurant.now))
    yield
    backup_task.cancel()
    for conn in list(webrtc_connections.values()):
        await conn.disconnect()


app = FastAPI(title="Cramble Voice Agent", lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(config.PROJECT_ROOT / "static" / "index.html")


@app.get("/health")
async def health():
    return {"ok": True, "storage": store.name}


# ---------------------------------------------------------------------------
# Browser calls (WebRTC)
# ---------------------------------------------------------------------------

def _webrtc_imports():
    try:
        from pipecat.transports.smallwebrtc.connection import IceServer, SmallWebRTCConnection
        from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
    except ImportError:  # older Pipecat
        from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
        from pipecat.transports.network.webrtc_connection import IceServer, SmallWebRTCConnection
    return IceServer, SmallWebRTCConnection, SmallWebRTCTransport


async def run_browser_call(connection):
    from pipecat.transports.base_transport import TransportParams

    from cramble.bot import run_conversation, vad

    _, _, SmallWebRTCTransport = _webrtc_imports()
    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True, vad_analyzer=vad()),
    )
    try:
        await run_conversation(transport, store, failsafe)
    except Exception:
        log.exception("Browser call crashed")


@app.post("/api/offer")
async def offer(request: Request, background_tasks: BackgroundTasks):
    IceServer, SmallWebRTCConnection, _ = _webrtc_imports()
    body = await request.json()
    pc_id = body.get("pc_id")
    if pc_id and pc_id in webrtc_connections:
        connection = webrtc_connections[pc_id]
        await connection.renegotiate(sdp=body["sdp"], type=body["type"], restart_pc=body.get("restart_pc", False))
    else:
        connection = SmallWebRTCConnection(ice_servers=[IceServer(urls="stun:stun.l.google.com:19302")])
        await connection.initialize(sdp=body["sdp"], type=body["type"])

        @connection.event_handler("closed")
        async def on_closed(conn):
            webrtc_connections.pop(conn.pc_id, None)

        background_tasks.add_task(run_browser_call, connection)
    answer = connection.get_answer()
    webrtc_connections[answer["pc_id"]] = connection
    return JSONResponse(answer)


# ---------------------------------------------------------------------------
# Phone calls (Twilio) — optional
# ---------------------------------------------------------------------------

@app.post("/twilio/incoming")
async def twilio_incoming(request: Request):
    """Twilio calls this when someone dials your number. We tell Twilio to stream the audio to us."""
    if config.PUBLIC_URL:
        ws_url = config.PUBLIC_URL.replace("https://", "wss://").replace("http://", "ws://") + "/twilio/ws"
    else:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        ws_url = f"wss://{host}/twilio/ws"
    twiml = (f'<?xml version="1.0" encoding="UTF-8"?><Response><Connect>'
             f'<Stream url="{escape(ws_url)}"/></Connect></Response>')
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/twilio/ws")
async def twilio_ws(websocket: WebSocket):
    from pipecat.serializers.twilio import TwilioFrameSerializer

    try:
        from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport
    except ImportError:  # older Pipecat
        from pipecat.transports.network.fastapi_websocket import FastAPIWebsocketParams, FastAPIWebsocketTransport

    from cramble.bot import run_conversation, vad

    await websocket.accept()
    # Twilio first sends a "connected" message, then a "start" message with the call IDs.
    stream_sid = call_sid = None
    async for raw in websocket.iter_text():
        msg = json.loads(raw)
        if msg.get("event") == "start":
            stream_sid = msg["start"]["streamSid"]
            call_sid = msg["start"].get("callSid")
            break
    if not stream_sid:
        return
    log.info("Phone call started (call %s)", call_sid)

    if config.twilio_configured():
        serializer = TwilioFrameSerializer(stream_sid=stream_sid, call_sid=call_sid,
                                           account_sid=config.TWILIO_ACCOUNT_SID,
                                           auth_token=config.TWILIO_AUTH_TOKEN)
    else:  # can't hang up automatically without credentials
        serializer = TwilioFrameSerializer(stream_sid=stream_sid,
                                           params=TwilioFrameSerializer.InputParams(auto_hang_up=False))

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(audio_in_enabled=True, audio_out_enabled=True, add_wav_header=False,
                                      vad_analyzer=vad(), serializer=serializer),
    )
    try:
        await run_conversation(transport, store, failsafe, phone=True)
    except Exception:
        log.exception("Phone call crashed")


if __name__ == "__main__":
    print(f"\n  Cramble voice agent running.  Open  http://localhost:{config.PORT}  in Chrome and click Start Call.\n")
    uvicorn.run(app, host=config.HOST, port=config.PORT)

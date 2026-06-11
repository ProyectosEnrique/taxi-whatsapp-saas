"""
Taxi WhatsApp Gateway — Meta Cloud API + Twilio fallback
Receives webhooks from Meta WhatsApp Cloud API, calls TaxiFSM, responds via Meta Graph API.
"""
import os
import time
import logging
import xml.etree.ElementTree as ET
from fastapi import FastAPI, Form, Header, Request, Query
from fastapi.responses import Response, PlainTextResponse
import httpx

from .stt_client import get_stt_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Taxi WhatsApp Gateway")

# Dedup cache: {message_id: timestamp} — prevents double-processing Meta retries
_seen: dict[str, float] = {}
_DEDUP_TTL = 300  # seconds


def _is_duplicate(msg_id: str) -> bool:
    now = time.time()
    # Purge old entries
    expired = [k for k, t in _seen.items() if now - t > _DEDUP_TTL]
    for k in expired:
        del _seen[k]
    if msg_id in _seen:
        return True
    _seen[msg_id] = now
    return False

SALES_AGENT_URL      = os.getenv("SALES_AGENT_URL", "http://taxi-agent:5000")
META_VERIFY_TOKEN    = os.getenv("META_VERIFY_TOKEN", "taxi2026")
META_ACCESS_TOKEN    = os.getenv("META_ACCESS_TOKEN", "")
META_PHONE_ID        = os.getenv("META_PHONE_NUMBER_ID", "988164724391332")
TWILIO_ACCOUNT_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WA_NUMBER     = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+16204077336")
WHATSAPP_SECRET      = os.getenv("WHATSAPP_SECRET", "")


# ─── FSM caller ───────────────────────────────────────────────────────────────

async def _call_fsm(phone: str, message: str, customer_name: str) -> list[str]:
    url = f"{SALES_AGENT_URL}/api/v1/sales/message"
    payload = {
        "session_id": phone,
        "message": message,
        "channel": "whatsapp",
        "context": {"tenant_id": "taxi", "phone": phone, "customer_name": customer_name},
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response") or data.get("text") or ""
            messages = data.get("messages", [])
            if messages:
                return [m if isinstance(m, str) else m.get("text", "") for m in messages]
            return [text] if text else []
    except Exception as e:
        logger.error(f"[TaxiGW] FSM error for {phone}: {e}")
        return ["Servicio temporalmente no disponible. Por favor intenta de nuevo."]


# ─── Send via Twilio (primary for Twilio-managed WhatsApp numbers) ────────────

def _send_twilio(to: str, body: str) -> None:
    """Send WhatsApp message via Twilio API."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.error("[TaxiGW] Twilio credentials not set")
        return
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        wa_to = f"whatsapp:+{to}" if not to.startswith("whatsapp:") else to
        client.messages.create(body=body, from_=TWILIO_WA_NUMBER, to=wa_to)
        logger.info(f"[TaxiGW] Twilio sent to {to}: {body[:60]}...")
    except Exception as e:
        logger.error(f"[TaxiGW] Twilio send error: {e}")


# ─── Send via Meta (fallback) ─────────────────────────────────────────────────

async def _send_meta(to: str, body: str) -> None:
    if not META_ACCESS_TOKEN:
        logger.error("[TaxiGW] META_ACCESS_TOKEN not set")
        return
    url = f"https://graph.facebook.com/v18.0/{META_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body}}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                logger.info(f"[TaxiGW] Meta sent to {to}: {body[:60]}...")
            else:
                logger.error(f"[TaxiGW] Meta API error {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"[TaxiGW] Meta send error: {e}")


# ─── Twilio TwiML send (fallback) ─────────────────────────────────────────────

def _twiml(*messages: str) -> Response:
    root = ET.Element("Response")
    for msg in messages:
        if msg:
            ET.SubElement(root, "Message").text = msg
    xml_str = ET.tostring(root, encoding="unicode")
    return Response(
        content=f'<?xml version="1.0" encoding="UTF-8"?>{xml_str}',
        media_type="application/xml",
    )


# ─── Meta media downloader (for audio messages) ──────────────────────────────

async def _download_meta_media(media_id: str) -> bytes | None:
    """Resolve Meta media_id → URL → download bytes."""
    if not META_ACCESS_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {META_ACCESS_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"https://graph.facebook.com/v18.0/{media_id}",
                headers=headers,
            )
            if resp.status_code != 200:
                logger.error(f"[TaxiGW] Meta media metadata {resp.status_code}: {resp.text[:100]}")
                return None
            media_url = resp.json().get("url")
            if not media_url:
                return None
            resp = await client.get(media_url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"[TaxiGW] Meta media download {resp.status_code}")
                return None
            return resp.content
    except Exception as e:
        logger.error(f"[TaxiGW] _download_meta_media error: {e}")
        return None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "taxi-whatsapp-gateway"}


# ─── Proactive customer notification (called by taxi-api driver actions) ──────

@app.post("/notify/customer")
async def notify_customer(
    request: Request,
    x_taxi_internal_key: str = Header(...),
):
    if WHATSAPP_SECRET and x_taxi_internal_key != WHATSAPP_SECRET:
        return Response(status_code=403)
    data = await request.json()
    phone   = (data.get("phone") or "").strip()
    message = (data.get("message") or "").strip()
    if not phone or not message:
        return {"status": "ignored"}
    logger.info(f"[TaxiGW] Proactive → {phone}: {message[:60]}...")
    _send_twilio(phone, message)
    return {"status": "sent"}


# ── Meta webhook verification (GET) ───────────────────────────────────────────

@app.get("/webhook/meta")
async def meta_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == META_VERIFY_TOKEN:
        logger.info("[TaxiGW] Meta webhook verified")
        return PlainTextResponse(hub_challenge)
    logger.warning(f"[TaxiGW] Meta verification failed: mode={hub_mode} token={hub_verify_token}")
    return Response(status_code=403)


# ── Meta incoming messages (POST) ─────────────────────────────────────────────

@app.post("/webhook/meta")
async def meta_webhook(request: Request):
    data = await request.json()
    logger.info(f"[TaxiGW] Meta webhook received")

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            # Only handle messages for this gateway's phone number
            metadata = value.get("metadata", {})
            incoming_phone_id = metadata.get("phone_number_id", "")
            if incoming_phone_id and incoming_phone_id != META_PHONE_ID:
                logger.info(f"[TaxiGW] Ignoring message for other number ({incoming_phone_id})")
                continue
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            for msg in messages:
                msg_type = msg.get("type")
                if msg_type not in ("text", "location", "audio"):
                    continue
                msg_id = msg.get("id", "")
                if msg_id and _is_duplicate(msg_id):
                    logger.info(f"[TaxiGW] Duplicate msg {msg_id} — skipping")
                    continue
                phone = msg["from"]
                name  = contacts[0]["profile"]["name"] if contacts else "Cliente"

                if msg_type == "location":
                    loc = msg.get("location", {})
                    lat = loc.get("latitude", "")
                    lon = loc.get("longitude", "")
                    label = loc.get("name") or loc.get("address") or "Ubicación compartida"
                    text = f"[GPS:{lat},{lon}:{label}]"

                elif msg_type == "audio":
                    stt = get_stt_client()
                    if not stt.is_available:
                        _send_twilio(phone, "Por el momento no puedo procesar notas de voz. Por favor escríbeme tu mensaje.")
                        continue
                    media_id = (msg.get("audio") or {}).get("id")
                    if not media_id:
                        continue
                    audio_bytes = await _download_meta_media(media_id)
                    if not audio_bytes:
                        # Token expired or unavailable — skip silently; Twilio webhook handles the same message
                        logger.warning(f"[TaxiGW] Meta audio download failed for {phone} — skipping (token expired?)")
                        continue
                    text = await stt.transcribe_bytes(audio_bytes)
                    if not text:
                        _send_twilio(phone, "No entendí tu nota de voz. Por favor escríbeme tu mensaje.")
                        continue
                    logger.info(f"[TaxiGW] Meta audio transcribed for {phone}: {text[:80]}")

                else:
                    text = msg.get("text", {}).get("body", "")

                logger.info(f"[TaxiGW] Meta {msg_type} from {phone} ({name}): {text[:80]}")
                responses = await _call_fsm(phone, text, name)
                for reply in responses:
                    if reply:
                        _send_twilio(phone, reply)

    return {"status": "ok"}


# ── Twilio incoming messages (POST) — kept as fallback ────────────────────────

@app.post("/webhook/twilio")
async def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    ProfileName: str = Form(None),
    NumMedia: str = Form("0"),
    MediaContentType0: str = Form(None),
    MediaUrl0: str = Form(None),
    Latitude: str = Form(None),
    Longitude: str = Form(None),
):
    phone         = From.replace("whatsapp:", "").strip()
    customer_name = ProfileName or "Cliente"

    # Location share via Twilio
    if Latitude and Longitude:
        label = Body.strip() or "Ubicación compartida"
        text = f"[GPS:{Latitude},{Longitude}:{label}]"
        logger.info(f"[TaxiGW] Twilio location from {phone}: {text}")
        responses = await _call_fsm(phone, text, customer_name)
        return _twiml(*responses)

    if int(NumMedia) > 0 and MediaContentType0 and "audio" in MediaContentType0:
        stt = get_stt_client()
        if not stt.is_available:
            return _twiml("Por el momento no puedo procesar notas de voz. Por favor escríbeme tu mensaje.")
        transcript = await stt.transcribe_audio_url(
            MediaUrl0,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None,
        )
        if not transcript:
            return _twiml("No entendí tu nota de voz. Por favor escríbeme tu mensaje.")
        logger.info(f"[TaxiGW] Twilio audio transcribed for {phone}: {transcript[:80]}")
        responses = await _call_fsm(phone, transcript, customer_name)
        return _twiml(*responses)

    if not Body.strip():
        return _twiml()

    logger.info(f"[TaxiGW] Twilio msg from {phone} ({customer_name}): {Body[:80]}")
    responses = await _call_fsm(phone, Body, customer_name)
    return _twiml(*responses)

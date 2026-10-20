"""
app/server.py
FastAPI REST API server and static asset host.
"""

import json
import os
import wave
import struct
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api

from app.config import settings
from app.db import (
    init_db,
    get_db_connection,
    list_calls,
    get_call_by_id,
    get_call_by_session_id,
    create_call,
    get_transcripts_for_call,
    get_all_products,
    create_or_update_product
)

app = FastAPI(title="AI Voice Sales Bot API", version="1.0.0")

# CORS policy for WebRTC web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ensure_sample_wav():
    """Generates a brief 2-second silent/chime WAV file if no sample exists."""
    os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)
    sample_path = os.path.join(settings.RECORDINGS_DIR, "sample_call.wav")
    if not os.path.exists(sample_path):
        sample_rate = 16000
        duration = 2.0  # seconds
        num_frames = int(sample_rate * duration)
        with wave.open(sample_path, "w") as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            # Subtle audible beep/tone for demonstration
            import math
            audio_bytes = bytearray()
            for i in range(num_frames):
                # 440 Hz gentle tone fading out
                val = int(3000 * math.sin(2 * math.pi * 440 * (i / sample_rate)) * max(0.0, 1.0 - i / num_frames))
                audio_bytes.extend(struct.pack("<h", val))
            wav_file.writeframes(audio_bytes)


@app.on_event("startup")
async def on_startup():
    await init_db()
    os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)
    ensure_sample_wav()


# ── Pydantic Request / Response Models ──

class TokenRequest(BaseModel):
    product_name: str = "CloudScale CRM"
    language: str = "en-US"
    customer_name: str = "Prospect"
    disclose_consent: bool = True
    custom_system_prompt: Optional[str] = None
    custom_product_data: Optional[Dict[str, Any]] = None

class TokenResponse(BaseModel):
    token: str
    room_name: str
    livekit_url: str
    call_id: Optional[str] = None

class ProductCreateRequest(BaseModel):
    name: str
    tagline: str
    description: str
    pricing_monthly: float = 49.0
    pricing_annual: float = 39.0
    key_features: List[str] = []
    target_audience: str = "Target customers"
    common_objections: Dict[str, str] = {}
    custom_system_prompt: Optional[str] = None


# ── LiveKit Room Token Dispatcher ──

@app.post("/api/token", response_model=TokenResponse)
async def generate_livekit_token(req: TokenRequest):
    """
    Issues a signed JWT token granting a browser client permission to join
    a dedicated LiveKit room for a new sales voice call with custom prompt/product metadata.
    """
    room_name = f"sales-call-{os.urandom(4).hex()}"
    participant_identity = f"customer-{os.urandom(3).hex()}"

    grant = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True
    )

    metadata_payload = {
        "product_name": req.product_name,
        "language": req.language,
        "customer_name": req.customer_name,
        "disclose_consent": req.disclose_consent,
        "custom_system_prompt": req.custom_system_prompt,
        "custom_product_data": req.custom_product_data
    }

    # If LiveKit key/secret are missing, use dummy token for local dev test
    api_key = settings.LIVEKIT_API_KEY or "devkey"
    api_secret = settings.LIVEKIT_API_SECRET or "secret"
    livekit_url = settings.LIVEKIT_URL or "wss://placeholder.livekit.cloud"

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(participant_identity)
        .with_name(req.customer_name)
        .with_grants(grant)
        .with_metadata(json.dumps(metadata_payload))
        .to_jwt()
    )

    # Pre-create room on LiveKit Cloud and dispatch sales agent worker
    if settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET and settings.LIVEKIT_URL:
        try:
            lk_client = api.LiveKitAPI(livekit_url, api_key, api_secret)
            await lk_client.room.create_room(
                api.CreateRoomRequest(
                    name=room_name,
                    metadata=json.dumps(metadata_payload),
                    empty_timeout=300
                )
            )
            # Dispatch LiveKit Agent Worker to the room specifically for sales-bot-agent
            await lk_client.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="sales-bot-agent",
                    room=room_name,
                    metadata=json.dumps(metadata_payload)
                )
            )
            await lk_client.aclose()
        except Exception as e:
            logger.warning(f"Could not pre-create room or dispatch: {e}")

    # Ensure call record is created in DB immediately so live transcript polling & analysis find it
    call_id = await create_call(
        session_id=room_name,
        product_name=req.product_name,
        language=req.language,
        customer_name=req.customer_name
    )

    return TokenResponse(
        token=token,
        room_name=room_name,
        livekit_url=livekit_url,
        call_id=call_id
    )


# ── Calls History & Analytics Endpoints ──

@app.get("/api/calls/by-session/{session_id}")
async def get_call_by_session_endpoint(session_id: str):
    """Returns active call record and chronological transcripts by LiveKit room name."""
    call = await get_call_by_session_id(session_id)
    if not call:
        return {"call": None, "transcripts": []}
    transcripts = await get_transcripts_for_call(call["id"])
    return {"call": call, "transcripts": transcripts}


@app.get("/api/calls")
async def get_calls_history(
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None)
):
    """Returns list of previous call sessions with summaries and final sales statuses."""
    calls = await list_calls(limit=limit, status_filter=status)
    return {"calls": calls}


@app.get("/api/calls/{call_id}")
async def get_call_detail(call_id: str):
    """Returns comprehensive call record including full chronological transcript."""
    call = await get_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call session not found")

    transcripts = await get_transcripts_for_call(call_id)
    call["transcripts"] = transcripts
    return call


@app.post("/api/calls/by-session/{session_id}/recording")
async def upload_call_recording(session_id: str, file: UploadFile = File(...)):
    """Receives real audio recording from the browser client and updates the call record."""
    call = await get_call_by_session_id(session_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call session not found")

    call_id = call["id"]
    filename = f"call_{call_id}.webm"
    filepath = os.path.join(settings.RECORDINGS_DIR, filename)
    rec_url = f"/api/calls/{call_id}/recording"

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    async with get_db_connection() as conn:
        await conn.execute(
            "UPDATE calls SET recording_url = ?, recording_file_path = ? WHERE id = ?",
            (rec_url, filepath, call_id)
        )
        await conn.commit()

    return {"status": "success", "recording_url": rec_url, "size_bytes": len(content)}


@app.get("/api/calls/{call_id}/recording")
async def get_call_recording(call_id: str):
    """Streams the recorded audio file for playback in the web player."""
    call = await get_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")

    # 1. Check webm file in recordings dir (real dual-channel mixer audio from browser)
    webm_path = os.path.join(settings.RECORDINGS_DIR, f"call_{call_id}.webm")
    if os.path.exists(webm_path):
        return FileResponse(webm_path, media_type="audio/webm")

    # 2. Check direct recording file path
    filepath = call.get("recording_file_path")
    if filepath and os.path.exists(filepath):
        media_type = "audio/webm" if filepath.endswith(".webm") else "audio/wav"
        return FileResponse(filepath, media_type=media_type)

    # 3. Check wav file in recordings dir
    wav_path = os.path.join(settings.RECORDINGS_DIR, f"call_{call_id}.wav")
    if os.path.exists(wav_path):
        return FileResponse(wav_path, media_type="audio/wav")

    # 4. Return fallback recording
    fallback_path = os.path.join(settings.RECORDINGS_DIR, "sample_call.wav")
    if os.path.exists(fallback_path):
        return FileResponse(fallback_path, media_type="audio/wav")

    raise HTTPException(status_code=404, detail="Audio recording not available for this call")


# ── SaaS Products & Custom Task Endpoints ──

@app.get("/api/products")
async def get_products():
    """Returns available SaaS products and user-customized tasks."""
    products = await get_all_products()
    return {"products": products}


@app.post("/api/products")
async def create_product_endpoint(product: ProductCreateRequest):
    """
    Saves a user-defined SaaS product or tasker configuration from the UI Customizer Studio.
    Persists to the database and makes it immediately selectable for voice calls.
    """
    product_id = await create_or_update_product(product.model_dump())
    return {"status": "success", "product_id": product_id, "name": product.name}


# ── Health Check ──

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "livekit_configured": bool(settings.LIVEKIT_URL and settings.LIVEKIT_API_KEY),
        "gemini_configured": bool(settings.GOOGLE_API_KEY)
    }

# ── Mount Web Client ──
app.mount("/", StaticFiles(directory="static", html=True), name="static")

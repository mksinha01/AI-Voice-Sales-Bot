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
from pydantic import BaseModel, Field, ConfigDict
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
    create_or_update_product,
    list_agents,
    get_agent_by_id,
    create_agent,
    list_agent_versions,
    get_agent_version,
    get_active_agent_version,
    create_agent_version,
    update_agent_version,
    publish_agent_version,
    activate_agent_version,
    duplicate_agent_version,
    rollback_agent_version,
    delete_agent_version,
    compare_agent_versions,
    create_sales_session,
    get_sales_session,
    record_sales_event,
    list_sales_events,
)
from app.tools import list_registered_tools
from app.prompts import compile_agent_system_prompt, generate_agent_config_from_prompt

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
    language: str = "auto"
    customer_name: str = "Prospect"
    disclose_consent: bool = True
    custom_system_prompt: Optional[str] = None
    custom_product_data: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = None
    version_id: Optional[str] = None

class TokenResponse(BaseModel):
    token: str
    room_name: str
    livekit_url: str
    call_id: Optional[str] = None
    version_id: Optional[str] = None
    version_tag: Optional[str] = None

class AgentCreateRequest(BaseModel):
    name: str
    description: str = ""
    owner_id: str = "default_org"

class VersionCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version_tag: Optional[str] = None
    system_prompt: Optional[str] = None
    persona: Dict[str, Any] = {}
    sales_objective: str = "Drive sales and qualify leads"
    customer_profile: Dict[str, Any] = {}
    sales_workflow: Dict[str, Any] = {}
    knowledge_config: Dict[str, Any] = {}
    tool_permissions: List[str] = []
    model_settings: Dict[str, Any] = Field(default_factory=dict, alias="model_config")
    as_draft: bool = True

class VersionUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version_tag: Optional[str] = None
    system_prompt: Optional[str] = None
    persona: Optional[Dict[str, Any]] = None
    sales_objective: Optional[str] = None
    customer_profile: Optional[Dict[str, Any]] = None
    sales_workflow: Optional[Dict[str, Any]] = None
    knowledge_config: Optional[Dict[str, Any]] = None
    tool_permissions: Optional[List[str]] = None
    model_settings: Optional[Dict[str, Any]] = Field(default=None, alias="model_config")

class NaturalLanguageGenRequest(BaseModel):
    instruction: str

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
    a dedicated LiveKit room for a new sales voice call with exact pinned version configuration.
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

    # 1. Resolve active/requested agent version from database
    active_version = None
    agent_id = req.agent_id or "agent-alex-closer"
    if req.version_id:
        active_version = await get_agent_version(req.version_id)
    if not active_version:
        active_version = await get_active_agent_version(agent_id)

    # 2. Compile system prompt and tool permissions from pinned version
    compiled_prompt = None
    allowed_tools = None
    version_id = None
    version_tag = None

    if active_version:
        version_id = active_version["id"]
        version_tag = active_version.get("version_tag", f"v{active_version.get('version_number', 1)}")
        compiled_prompt = compile_agent_system_prompt(active_version)
        allowed_tools = active_version.get("tool_permissions", [])
        # Record pinned sales session for auditing and immutability
        try:
            await create_sales_session(
                agent_id=agent_id,
                pinned_version_id=version_id,
                customer_name=req.customer_name,
                config_snapshot=active_version
            )
        except Exception as e:
            pass
    else:
        compiled_prompt = req.custom_system_prompt

    metadata_payload = {
        "product_name": req.product_name,
        "language": req.language,
        "customer_name": req.customer_name,
        "disclose_consent": req.disclose_consent,
        "custom_system_prompt": compiled_prompt,
        "custom_product_data": req.custom_product_data,
        "agent_id": agent_id,
        "version_id": version_id,
        "version_tag": version_tag,
        "allowed_tools": allowed_tools
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
            await lk_client.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="sales-bot-agent",
                    room=room_name,
                    metadata=json.dumps(metadata_payload)
                )
            )
            await lk_client.aclose()
        except Exception as e:
            pass

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
        call_id=call_id,
        version_id=version_id,
        version_tag=version_tag
    )


# ── Agent Persona & Version Control Endpoints ──

@app.get("/api/agents")
async def get_agents_endpoint():
    """Lists all configured sales agents."""
    agents = await list_agents()
    for a in agents:
        if a.get("active_version_id"):
            v = await get_agent_version(a["active_version_id"])
            a["active_version"] = v
    return {"agents": agents}


@app.post("/api/agents")
async def create_agent_endpoint(req: AgentCreateRequest):
    """Creates a new sales agent."""
    agent = await create_agent(name=req.name, description=req.description, owner_id=req.owner_id)
    return {"status": "success", "agent": agent}


@app.get("/api/agents/{agent_id}")
async def get_agent_endpoint(agent_id: str):
    """Retrieves an agent along with its active version."""
    agent = await get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent": agent}


@app.get("/api/agents/{agent_id}/versions")
async def get_agent_versions_endpoint(agent_id: str):
    """Lists all versions belonging to a sales agent."""
    versions = await list_agent_versions(agent_id)
    return {"versions": versions}


@app.post("/api/agents/{agent_id}/versions")
async def create_version_endpoint(agent_id: str, req: VersionCreateRequest):
    """Creates a new draft version for an agent."""
    agent = await get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    version = await create_agent_version(agent_id, req.model_dump(by_alias=True), as_draft=req.as_draft)
    return {"status": "success", "version": version}


@app.get("/api/agents/{agent_id}/versions/compare")
async def compare_versions_endpoint(agent_id: str, v1: str = Query(...), v2: str = Query(...)):
    """Computes a structured diff between any two versions."""
    try:
        comparison = await compare_agent_versions(v1, v2)
        return {"comparison": comparison}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/agents/{agent_id}/versions/{version_id}")
async def get_version_endpoint(agent_id: str, version_id: str):
    """Retrieves a single version with preview of compiled prompt."""
    version = await get_agent_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    version["compiled_prompt_preview"] = compile_agent_system_prompt(version)
    return {"version": version}


@app.put("/api/agents/{agent_id}/versions/{version_id}")
async def update_version_endpoint(agent_id: str, version_id: str, req: VersionUpdateRequest):
    """Updates a draft version. Enforces immutability on published and active versions."""
    try:
        updated = await update_agent_version(version_id, req.model_dump(by_alias=True, exclude_unset=True))
        updated["compiled_prompt_preview"] = compile_agent_system_prompt(updated)
        return {"status": "success", "version": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/agents/{agent_id}/versions/{version_id}/publish")
async def publish_version_endpoint(agent_id: str, version_id: str):
    """Publishes a draft version, making it immutable."""
    try:
        published = await publish_agent_version(version_id)
        return {"status": "success", "version": published}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/agents/{agent_id}/versions/{version_id}/activate")
async def activate_version_endpoint(agent_id: str, version_id: str):
    """Activates a version for live voice sessions."""
    try:
        activated = await activate_agent_version(agent_id, version_id)
        return {"status": "success", "version": activated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/agents/{agent_id}/versions/{version_id}/duplicate")
async def duplicate_version_endpoint(agent_id: str, version_id: str):
    """Duplicates an existing version as a new editable draft."""
    try:
        duplicated = await duplicate_agent_version(version_id)
        return {"status": "success", "version": duplicated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/agents/{agent_id}/versions/{version_id}/rollback")
async def rollback_version_endpoint(agent_id: str, version_id: str):
    """Creates a new draft version copied from a historical version."""
    try:
        new_draft = await rollback_agent_version(agent_id, version_id)
        return {"status": "success", "version": new_draft}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/agents/{agent_id}/versions/{version_id}")
async def delete_version_endpoint(agent_id: str, version_id: str):
    """Deletes an agent version. Active live versions cannot be deleted."""
    try:
        await delete_agent_version(agent_id, version_id)
        return {"status": "success", "message": f"Version {version_id} deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ai/generate-config")
async def generate_config_endpoint(req: NaturalLanguageGenRequest):
    """Generates structured agent configuration from natural language prompt."""
    try:
        config = await generate_agent_config_from_prompt(req.instruction)
        return {"status": "success", "generated_config": config}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Generation error: {str(e)}")


@app.get("/api/tools")
async def get_tools_endpoint():
    """Lists registered tools and permissions."""
    return {"tools": list_registered_tools()}


@app.get("/api/sessions/{session_id}")
async def get_session_endpoint(session_id: str):
    """Retrieves pinned session snapshot and audit events."""
    sess = await get_sales_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    events = await list_sales_events(session_id)
    sess["events"] = events
    return {"session": sess}



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

# ── Dedicated Route Endpoints for Persona Control Studio & Settings ──

@app.get("/persona-control")
async def get_persona_control_view():
    """Serves the AI Sales Agent Persona and Version Control Studio."""
    return FileResponse("static/persona-control.html")


@app.get("/settings")
async def get_settings_view():
    """Serves the AI Agent Configuration & Persona Studio directly from Settings."""
    return FileResponse("static/persona-control.html")


# ── Mount Web Client ──
app.mount("/", StaticFiles(directory="static", html=True), name="static")

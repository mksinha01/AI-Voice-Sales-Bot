# Project Specification: AI Voice Sales Bot (SaaS Closer)
**Document Version:** 1.0.0  
**Based on:** `doc/oneshot.md` Build Specification Contract  
**Fulfills:** `doc/goal.md` (Sankar Group – Intern Assignment)  
**Primary Technologies:** LiveKit WebRTC, Google Gemini LLM, LangChain, FastAPI, Vanilla Modern Web  

---

## 0. Mission Statement

The **AI Voice Sales Bot** is an interactive, low-latency, full-duplex conversational voice application that pitches, qualifies, handles objections, and closes sales for SaaS products in multiple languages (English, Hindi, Telugu, and Hinglish). The system:

- **Dials / Establishes** low-latency, two-way WebRTC audio sessions with prospective customers directly in browser.
- **Discloses** recording consent immediately upon call initiation to meet regulatory and compliance standards.
- **Transcribes** customer voice in real time and streams bidirectional live chat bubbles to the user's screen with sub-second latency.
- **Pitches and Negotiates** SaaS software value propositions dynamically using Google Gemini as the core conversational intelligence.
- **Detects** user interruptions and pauses speech gracefully via LiveKit Voice Activity Detection (VAD) and Turn Detection.
- **Records** the complete voice conversation and stores audio files with dedicated playback capabilities.
- **Analyzes** finished calls via LangChain and Gemini structured output to extract key customer requirements, objections raised, next action items, and a concise executive summary.
- **Classifies** every call into one of six strictly defined sales stages: `Converted`, `Interested`, `Follow-up Required`, `Not Interested`, `Demo Requested`, or `No Response`.
- **Customizes** SaaS products and operational tasks directly from the frontend UI, enabling instant switching between preset products or entering custom product details (features, pricing, objections) or arbitrary custom system prompts (e.g. support, debt collection, real-estate, lead generation).
- **Persists** call records, audio tracks, full transcripts, and post-call analytics in an idempotent database.
- **Presents** a real-time call control interface, dynamic SaaS customizer studio, and an interactive historical analytics dashboard with embedded audio playback.

### Tech Stack List
- **Voice & WebRTC Transport:** LiveKit Server / LiveKit Cloud (v1.8+), LiveKit Agents Python SDK (`livekit-agents` v0.12+), LiveKit Web SDK (`livekit-client` v2.5+)
- **Large Language Model (Voice Agent):** Google Gemini 2.0 Flash / Gemini 1.5 Flash via `livekit-plugins-google`
- **Speech-to-Text (STT) & Text-to-Speech (TTS):** LiveKit Google Plugin / Deepgram STT (`livekit-plugins-deepgram`) + Google Cloud TTS / Cartesia (`livekit-plugins-cartesia`)
- **Post-Call Analytics & Extraction:** LangChain (`langchain` v0.3+, `langchain-core` v0.3+, `langchain-google-genai` v2.0+) with Pydantic v2 structured schemas
- **Backend API & Web Server:** Python 3.11+, FastAPI (v0.115+), Uvicorn (v0.32+), `python-dotenv`, Pydantic v2
- **Data Persistence:** SQLite3 (via `aiosqlite` v0.20+) with idempotent DDL migrations
- **Frontend Client:** Semantic HTML5, Modern Vanilla CSS (Dark glassmorphism design system), Vanilla ES6+ JavaScript, Web Audio API

### Build Contract Instruction
> **BUILD THIS EXACTLY. DO NOT SKIP ANYTHING. DO NOT SIMPLIFY. DO NOT SUBSTITUTE LIBRARIES.**  
> Implement all 8 requirements from `doc/goal.md` without omission. The architecture must strictly isolate real-time streaming (LiveKit), LLM live agent loop (LiveKit + Gemini), post-call structured intelligence (LangChain + Gemini), dynamic SaaS/prompt customization studio, and data persistence (FastAPI + SQLite).

---

## 1. File Structure

```
AI-Voice-Sales-Bot/
├── .env.example                     ← Template environment configuration file with documentation links
├── .gitignore                       ← Git exclusion rules for secrets, DB files, and recordings
├── README.md                        ← Project documentation, live demo links, and video walkthrough guide
├── requirements.txt                 ← Pinned Python backend and agent dependencies
├── Dockerfile                       ← Multi-stage production container definition
├── start.sh                         ← Container bootstrap script with visible environment variable checks
├── data/                            ← Local data directory (auto-created)
│   ├── sales_bot.db                 ← SQLite database file storing calls, transcripts, and products
│   └── recordings/                  ← Audio recording store (.wav / .ogg / .mp4 audio files)
├── app/                             ← Backend application package
│   ├── __init__.py                  ← Package marker
│   ├── config.py                    ← Pydantic-based settings loader with precedence enforcement
│   ├── db.py                        ← Async SQLite connection factory and idempotent CRUD data access layer
│   ├── prompts.py                   ← SaaS sales playbooks, multilingual prompts, and dynamic prompt customizer
│   ├── chains.py                    ← LangChain + Gemini post-call summary and sales status extraction chains
│   ├── agent.py                     ← LiveKit Agent worker loop, voice assistant, and live data streaming
│   ├── server.py                    ← FastAPI HTTP REST endpoints, LiveKit token generator, and static file mount
│   └── tools.py                     ← Sales agent action tools (book demo, log objection, calculate price)
└── static/                          ← Frontend static web interface
    ├── index.html                   ← Modern single-page interface with live chat, controls, and history
    ├── css/
    │   └── styles.css               ← Dark mode, glassmorphism, responsive visual design system
    └── js/
        ├── app.js                   ← Main frontend coordinator, state management, and tab switching
        ├── customizer.js            ← SaaS product customizer, prompt editor, and dynamic UI theme sync
        ├── livekit-client.js        ← WebRTC audio manager, LiveKit room handler, and microphone controller
        ├── live-chat.js             ← Real-time transcript renderer, auto-scroll, and message bubbles
        └── history.js               ← Call history fetcher, status filter badges, and audio player UI
```

---

## 2. Environment / Secrets

### `.env.example`
```bash
# ── Server & Runtime Configuration ──
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=development
DATABASE_PATH=data/sales_bot.db
RECORDINGS_DIR=data/recordings
LOG_LEVEL=INFO

# ── LiveKit WebRTC Credentials (obtain from https://cloud.livekit.io) ──
# Required: The WebSocket URL for LiveKit Cloud or self-hosted instance
LIVEKIT_URL=wss://your-project.livekit.cloud
# Required: API Key from LiveKit dashboard
LIVEKIT_API_KEY=APIxxxxxxxxx
# Required: API Secret from LiveKit dashboard
LIVEKIT_API_SECRET=sec_xxxxxxxxxxxxxxxxxxxxxxxxxx

# ── Google Gemini LLM Credentials (obtain from https://aistudio.google.com) ──
# Required: Google GenAI API key for live conversation and LangChain chains
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Model used for real-time voice conversation
GEMINI_VOICE_MODEL=gemini-2.0-flash
# Model used for post-call LangChain extraction
GEMINI_ANALYSIS_MODEL=gemini-1.5-flash

# ── Speech Synthesis & Recognition Services ──
# Optional: Deepgram API Key (https://console.deepgram.com) - if using Deepgram STT
DEEPGRAM_API_KEY=

# Optional: ElevenLabs API Key (https://elevenlabs.io) - if using premium voice TTS
ELEVEN_API_KEY=

# ── Sales Bot Configuration ──
# Default SaaS product being pitched (CloudScale CRM, Securify Vault, DevFlow AI)
DEFAULT_PRODUCT_NAME="CloudScale CRM"
# Default language: en-US, hi-IN, te-IN
DEFAULT_LANGUAGE="en-US"
# Mandatory compliance disclosure played at call start
RECORDING_CONSENT_DISCLOSURE="Hello! Thanks for connecting. Please note that this sales call is recorded for quality, training, and demonstration purposes. How are you doing today?"
```

### Settings Precedence Chain
```
1. Explicit CLI arguments / OS Runtime Environment Variables (Highest priority)
2. `.env` file variables (Loaded via python-dotenv)
3. Application code defaults in `app/config.py` (Lowest priority fallback)
```

### `.gitignore`
```gitignore
# Environment & Secrets
.env
.env.local
*.key
*.pem

# Python artifacts
__pycache__/
*.py[cod]
*$py.class
venv/
.venv/
env/

# Database & Runtime Uploads
data/*.db
data/*.db-journal
data/*.db-wal
data/recordings/*
!data/recordings/.gitkeep

# IDE & OS
.DS_Store
Thumbs.db
.vscode/
.idea/
```

---

## 3. Data Schema

All DDL is written in idempotent SQLite dialect (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`) and executed automatically on startup in `app/db.py`.

```sql
-- ── SaaS Products Catalog ──
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    tagline TEXT NOT NULL,
    description TEXT NOT NULL,
    pricing_monthly REAL NOT NULL,
    pricing_annual REAL NOT NULL,
    key_features TEXT NOT NULL,       -- JSON array of feature bullets
    target_audience TEXT NOT NULL,
    common_objections TEXT NOT NULL,  -- JSON key-value of objection -> rebuttal
    custom_system_prompt TEXT,        -- Optional custom system prompt override
    is_custom BOOLEAN DEFAULT 0,      -- 1 for user-created products/tasks, 0 for presets
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Calls Master Record ──
CREATE TABLE IF NOT EXISTS calls (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    customer_name TEXT DEFAULT 'Prospect',
    customer_contact TEXT DEFAULT 'N/A',
    product_name TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en-US',
    call_status TEXT NOT NULL DEFAULT 'initiated', -- initiated, in-progress, completed, failed
    sales_status TEXT NOT NULL DEFAULT 'No Response', -- Converted, Interested, Follow-up Required, Not Interested, Demo Requested, No Response
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER DEFAULT 0,
    recording_url TEXT,
    recording_file_path TEXT,
    summary TEXT,
    customer_requirements TEXT,
    objections TEXT,
    next_steps TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Call Transcript Lines ──
CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    call_id TEXT NOT NULL,
    speaker_type TEXT NOT NULL,       -- 'bot' or 'customer'
    message_text TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    latency_ms INTEGER DEFAULT 0,
    FOREIGN KEY(call_id) REFERENCES calls(id) ON DELETE CASCADE
);

-- ── Performance Indices ──
CREATE INDEX IF NOT EXISTS idx_calls_created_at ON calls(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_calls_sales_status ON calls(sales_status);
CREATE INDEX IF NOT EXISTS idx_transcripts_call_id ON transcripts(call_id);
```

### Access Control Posture
- Local embedded SQLite database: single backend process access via `aiosqlite`.
- Foreign key constraints enabled (`PRAGMA foreign_keys = ON;`).
- In WAL mode (`PRAGMA journal_mode = WAL;`) to permit concurrent reader operations without blocking write transactions.

---

## 4. Dependencies

### `requirements.txt`
```txt
# LiveKit Realtime Voice Stack
livekit>=0.18.2
livekit-agents>=0.12.3
livekit-api>=0.8.0
livekit-plugins-google>=0.7.2
livekit-plugins-deepgram>=0.7.0
livekit-plugins-cartesia>=0.6.0
livekit-plugins-silero>=0.7.1

# LLM & Post-Call Extraction Framework
langchain>=0.3.14
langchain-core>=0.3.29
langchain-google-genai>=2.0.8
google-generativeai>=0.8.4
pydantic>=2.10.4
pydantic-settings>=2.7.1

# Web Server & API Layer
fastapi>=0.115.6
uvicorn[standard]>=0.32.1
python-multipart>=0.0.20
python-dotenv>=1.0.1
aiosqlite>=0.20.0
aiofiles>=24.1.0
httpx>=0.28.1
```

### Frontend Dependencies (No build tools required)
- `livekit-client` via Official ESM CDN (`https://cdn.jsdelivr.net/npm/livekit-client@2.5.9/dist/livekit-client.umd.min.js`)
- Lucide Icons via CDN (`https://unpkg.com/lucide@latest`)
- Google Fonts: Inter (`https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap`)

---

## 5. Containerization / Runtime

### `Dockerfile`
```dockerfile
# Multi-stage production container
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

COPY . .

RUN mkdir -p data/recordings

EXPOSE 8000

RUN chmod +x start.sh
CMD ["./start.sh"]
```

### `start.sh`
```bash
#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting AI Voice Sales Bot (Sankar Group Assignment)    "
echo "=========================================================="
echo "Checking Environment Variables..."
[ -z "$LIVEKIT_URL" ] && echo "ERROR: LIVEKIT_URL is not set" && exit 1
[ -z "$LIVEKIT_API_KEY" ] && echo "ERROR: LIVEKIT_API_KEY is not set" && exit 1
[ -z "$LIVEKIT_API_SECRET" ] && echo "ERROR: LIVEKIT_API_SECRET is not set" && exit 1
[ -z "$GOOGLE_API_KEY" ] && echo "ERROR: GOOGLE_API_KEY is not set" && exit 1

echo "Configuration OK:"
echo " - LIVEKIT_URL: ${LIVEKIT_URL}"
echo " - PORT: ${PORT:-8000}"
echo " - GEMINI_VOICE_MODEL: ${GEMINI_VOICE_MODEL:-gemini-2.0-flash}"
echo " - GEMINI_ANALYSIS_MODEL: ${GEMINI_ANALYSIS_MODEL:-gemini-1.5-flash}"

mkdir -p data/recordings

# Launch Agent Worker in the background
echo "Starting LiveKit Agent Worker..."
python -m app.agent start &
AGENT_PID=$!

# Launch FastAPI Server in the foreground
echo "Starting FastAPI Application Server on port ${PORT:-8000}..."
exec uvicorn app.server:app --host 0.0.0.0 --port "${PORT:-8000}"
```

### Port Ownership Map
- **Port 8000:** FastAPI Application Server (serves Web UI, REST endpoints, LiveKit token dispatcher, static files).
- **Outbound WebSockets (443/7880):** LiveKit Agent Worker connects outbound to LiveKit Cloud/Server via secure WebSockets. No port conflicts.

---

## 6. Domain Config / Prompt-and-Behavior Templates (`app/prompts.py`)

Isolates all persona logic, product catalogs, sales qualification strategies, and multilingual instructions.

```python
"""
app/prompts.py
SaaS sales playbooks, personality definitions, and prompt generation functions.
"""

from typing import Dict, Any

# ── Preset SaaS Catalog ──
PRODUCT_CATALOG: Dict[str, Dict[str, Any]] = {
    "CloudScale CRM": {
        "tagline": "AI-Driven Sales Automation & Pipeline Intelligence for Modern Teams",
        "description": "CloudScale CRM automatically logs emails, transcribes meetings, predicts deal closure probabilities with 92% accuracy, and saves sales reps 10 hours every week.",
        "pricing_monthly": 49.0,
        "pricing_annual": 39.0,
        "key_features": [
            "AI automated meeting summarization and CRM data entry",
            "Predictive deal scoring & churn risk alerts",
            "Multi-channel sequences across Email, LinkedIn, and WhatsApp",
            "Instant integrations with Slack, Google Workspace, and Zapier"
        ],
        "target_audience": "Fast-growing B2B sales teams, agency owners, and startup founders.",
        "objections": {
            "too_expensive": "At $39/month, saving just 2 hours of a rep's time covers the entire cost. Most clients report a 3x ROI in the first 30 days.",
            "already_using_hubspot": "CloudScale sits right on top or replaces bloated legacy CRMs with zero migration downtime, focusing strictly on closing deals rather than manual reporting.",
            "need_to_talk_to_team": "Understood! Would you like me to book a 15-minute live interactive demo for your team this Thursday or Friday?"
        }
    },
    "Securify Vault": {
        "tagline": "Zero-Trust Cloud Data Protection & Compliance Sentinel",
        "description": "Enterprise-grade cloud compliance automation for SOC2, HIPAA, and GDPR with autonomous vulnerability patching.",
        "pricing_monthly": 199.0,
        "pricing_annual": 159.0,
        "key_features": [
            "Autonomous SOC2 & HIPAA continuous auditing",
            "Real-time ransomware detection and zero-blast radius isolation",
            "Automated vendor risk management"
        ],
        "target_audience": "CTOs, CISOs, and compliance managers in healthcare, fintech, and SaaS.",
        "objections": {
            "too_expensive": "A single SOC2 non-compliance penalty costs 100x more than our annual plan.",
            "happy_with_current_setup": "Securify runs agentless in 10 minutes alongside your existing cloud to uncover blind spots."
        }
    }
}


def build_sales_system_prompt(
    product_name: str = "CloudScale CRM", 
    language: str = "en-US",
    custom_system_prompt: str = None,
    custom_product_data: Dict[str, Any] = None
) -> str:
    """
    Constructs the operational sales agent system prompt based on product and target language.
    If custom_system_prompt is provided from the UI Customizer Studio, it takes highest precedence,
    allowing arbitrary bot personas and tasks (SaaS Sales, Support, Screening, etc.).
    If custom_product_data is provided, it dynamically interpolates user-defined SaaS specs.
    """
    # 1. Custom Prompt Override from UI Customizer Studio
    if custom_system_prompt and custom_system_prompt.strip():
        # Clean and enforce voice conversational guardrails
        return custom_system_prompt.strip()

    # 2. Dynamic or Catalog Product Resolution
    product = custom_product_data or PRODUCT_CATALOG.get(product_name, PRODUCT_CATALOG["CloudScale CRM"])
    
    language_instructions = {
        "en-US": "Speak in natural, enthusiastic, professional American or International English.",
        "hi-IN": "Speak in conversational Hindi or natural Hinglish (Hindi mixed with common English business terms). Be courteous and polite (use 'Aap', 'Ji').",
        "te-IN": "Speak in polite, engaging Telugu mixed naturally with standard English tech terms.",
    }.get(language, "Speak in natural, professional English.")

    features_str = ', '.join(product.get('key_features', [])) if isinstance(product.get('key_features'), list) else str(product.get('key_features', ''))

    prompt = f"""
You are Alex, an elite, friendly, and persuasive AI Sales Representative pitching {product_name}.
Your mission: Engage the prospect in a real-time voice conversation, build rapport, uncover their pain points, explain how {product_name} solves their challenges, handle their hesitations, and close with a clear call-to-action (booking a demo or confirming subscription interest).

Language Directive:
{language_instructions}

Product Knowledge:
- Product Name: {product_name}
- Tagline: {product.get('tagline', 'Modern Cloud Automation')}
- Overview: {product.get('description', '')}
- Pricing: ${product.get('pricing_annual', 39)}/user/month (annual billing) or ${product.get('pricing_monthly', 49)}/user/month (monthly billing).
- Key Capabilities: {features_str}
- Target Customer: {product.get('target_audience', 'Businesses & teams seeking efficiency')}

Sales Conversation Playbook (Execute dynamically):
1. Introduction & Hook:
   - Introduce yourself warmly. Acknowledge the recording disclosure that just played.
   - Ask an engaging opening question about their current workflow or biggest bottleneck.
2. Discovery & Active Listening:
   - Listen carefully to their answers. Validate their challenges before pitching.
   - Do NOT deliver long monologues. Keep each response concise (1 to 3 short sentences max) so it feels like a natural phone dialogue.
3. Solution Pitch:
   - Tie one or two key features directly to the problem they mentioned.
   - Highlight tangible benefits: time saved, revenue increased, or stress eliminated.
4. Handling Objections:
   - If they mention price/budget: Emphasize ROI, flexible month-to-month options, and free pilot periods.
   - If they already use a competitor: Highlight modern AI-native automation vs outdated manual tools.
   - If they need to consult their boss/team: Offer a collaborative demo with calendar invite.
5. Closing & Next Steps:
   - Always attempt to close with a decisive next step:
     * "Can I schedule a quick 15-minute demo for you this week?"
     * "Should I send over our starter package directly to your email?"
     * "Would you like me to lock in the 20% annual discount for you right now?"

Tone & Conversational Constraints:
- Keep utterances brief (25-45 words per turn). Long speeches cause awkward voice pauses.
- Never list bullet points or markdown tables over voice.
- Sound conversational, energetic, and empathetic. Use conversational fillers naturally ("I completely understand", "That makes total sense", "Great question").
- If the customer is unresponsive, gently re-engage: "Are you still with me?"
- If the customer explicitly declines multiple times, accept gracefully and thank them for their time.
"""
    return prompt.strip()
```

---

## 7. Data Access Layer (`app/db.py`)

Async SQLite interface using `aiosqlite`. Every function performs one query or mutation.

```python
"""
app/db.py
Data access layer for calls, transcripts, and products.
"""

import aiosqlite
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

ALLOWED_SALES_STATUSES = [
    "Converted",
    "Interested",
    "Follow-up Required",
    "Not Interested",
    "Demo Requested",
    "No Response"
]


async def get_db_connection() -> aiosqlite.Connection:
    """Factory creating an asynchronous SQLite database connection."""
    conn = await aiosqlite.connect(settings.DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute("PRAGMA journal_mode = WAL;")
    return conn


async def init_db() -> None:
    """Creates tables idempotently and populates seed products."""
    async with await get_db_connection() as conn:
        await conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            tagline TEXT NOT NULL,
            description TEXT NOT NULL,
            pricing_monthly REAL NOT NULL,
            pricing_annual REAL NOT NULL,
            key_features TEXT NOT NULL,
            target_audience TEXT NOT NULL,
            common_objections TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS calls (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE,
            customer_name TEXT DEFAULT 'Prospect',
            customer_contact TEXT DEFAULT 'N/A',
            product_name TEXT NOT NULL,
            language TEXT NOT NULL DEFAULT 'en-US',
            call_status TEXT NOT NULL DEFAULT 'initiated',
            sales_status TEXT NOT NULL DEFAULT 'No Response',
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            duration_seconds INTEGER DEFAULT 0,
            recording_url TEXT,
            recording_file_path TEXT,
            summary TEXT,
            customer_requirements TEXT,
            objections TEXT,
            next_steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transcripts (
            id TEXT PRIMARY KEY,
            call_id TEXT NOT NULL,
            speaker_type TEXT NOT NULL,
            message_text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            latency_ms INTEGER DEFAULT 0,
            FOREIGN KEY(call_id) REFERENCES calls(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_calls_created_at ON calls(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_calls_sales_status ON calls(sales_status);
        CREATE INDEX IF NOT EXISTS idx_transcripts_call_id ON transcripts(call_id);
        """)
        
        # Seed Products if empty
        cursor = await conn.execute("SELECT COUNT(*) as count FROM products")
        row = await cursor.fetchone()
        if row["count"] == 0:
            from app.prompts import PRODUCT_CATALOG
            for name, data in PRODUCT_CATALOG.items():
                await conn.execute("""
                INSERT OR IGNORE INTO products (
                    id, name, tagline, description, pricing_monthly, pricing_annual, 
                    key_features, target_audience, common_objections
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), name, data["tagline"], data["description"],
                    data["pricing_monthly"], data["pricing_annual"],
                    json.dumps(data["key_features"]), data["target_audience"],
                    json.dumps(data["objections"])
                ))
        await conn.commit()


# ── Calls Data Layer ──

async def create_call(session_id: str, product_name: str, language: str = "en-US", customer_name: str = "Prospect") -> str:
    call_id = str(uuid.uuid4())
    async with await get_db_connection() as conn:
        await conn.execute("""
        INSERT INTO calls (id, session_id, product_name, language, customer_name, call_status, start_time)
        VALUES (?, ?, ?, ?, ?, 'in-progress', ?)
        """, (call_id, session_id, product_name, language, customer_name, datetime.utcnow().isoformat()))
        await conn.commit()
    return call_id


async def update_call_on_end(
    session_id: str, 
    duration_seconds: int, 
    recording_url: Optional[str] = None,
    recording_file_path: Optional[str] = None
) -> None:
    async with await get_db_connection() as conn:
        await conn.execute("""
        UPDATE calls 
        SET call_status = 'completed',
            end_time = ?,
            duration_seconds = ?,
            recording_url = ?,
            recording_file_path = ?,
            updated_at = ?
        WHERE session_id = ?
        """, (datetime.utcnow().isoformat(), duration_seconds, recording_url, recording_file_path, datetime.utcnow().isoformat(), session_id))
        await conn.commit()


async def update_call_analysis(
    call_id: str,
    sales_status: str,
    summary: str,
    customer_requirements: str,
    objections: str,
    next_steps: str
) -> None:
    if sales_status not in ALLOWED_SALES_STATUSES:
        sales_status = "Follow-up Required"

    async with await get_db_connection() as conn:
        await conn.execute("""
        UPDATE calls 
        SET sales_status = ?,
            summary = ?,
            customer_requirements = ?,
            objections = ?,
            next_steps = ?,
            updated_at = ?
        WHERE id = ?
        """, (sales_status, summary, customer_requirements, objections, next_steps, datetime.utcnow().isoformat(), call_id))
        await conn.commit()


async def get_call_by_session_id(session_id: str) -> Optional[Dict[str, Any]]:
    async with await get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM calls WHERE session_id = ?", (session_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_call_by_id(call_id: str) -> Optional[Dict[str, Any]]:
    async with await get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_calls(limit: int = 50, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    async with await get_db_connection() as conn:
        if status_filter and status_filter in ALLOWED_SALES_STATUSES:
            cursor = await conn.execute("""
            SELECT * FROM calls WHERE sales_status = ? ORDER BY created_at DESC LIMIT ?
            """, (status_filter, limit))
        else:
            cursor = await conn.execute("""
            SELECT * FROM calls ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ── Transcripts Data Layer ──

async def append_transcript_message(call_id: str, speaker_type: str, message_text: str, latency_ms: int = 0) -> str:
    message_id = str(uuid.uuid4())
    async with await get_db_connection() as conn:
        await conn.execute("""
        INSERT INTO transcripts (id, call_id, speaker_type, message_text, latency_ms, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, call_id, speaker_type, message_text, latency_ms, datetime.utcnow().isoformat()))
        await conn.commit()
    return message_id


async def get_transcripts_for_call(call_id: str) -> List[Dict[str, Any]]:
    async with await get_db_connection() as conn:
        cursor = await conn.execute("""
        SELECT * FROM transcripts WHERE call_id = ? ORDER BY timestamp ASC
        """, (call_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ── Products Data Layer ──

async def get_all_products() -> List[Dict[str, Any]]:
    async with await get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM products ORDER BY is_custom ASC, name ASC")
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            try:
                item["key_features"] = json.loads(item["key_features"])
            except Exception:
                item["key_features"] = [item["key_features"]]
            try:
                item["common_objections"] = json.loads(item["common_objections"])
            except Exception:
                item["common_objections"] = {}
            result.append(item)
        return result


async def create_or_update_product(data: Dict[str, Any]) -> str:
    """Inserts or updates a user-defined custom SaaS product or task definition."""
    prod_id = data.get("id") or str(uuid.uuid4())
    name = data["name"]
    tagline = data.get("tagline", "")
    description = data.get("description", "")
    pricing_monthly = float(data.get("pricing_monthly", 49.0))
    pricing_annual = float(data.get("pricing_annual", 39.0))
    key_features = json.dumps(data.get("key_features", []))
    target_audience = data.get("target_audience", "Target customers")
    common_objections = json.dumps(data.get("common_objections", {}))
    custom_prompt = data.get("custom_system_prompt")

    async with await get_db_connection() as conn:
        await conn.execute("""
        INSERT INTO products (
            id, name, tagline, description, pricing_monthly, pricing_annual,
            key_features, target_audience, common_objections, custom_system_prompt, is_custom
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(name) DO UPDATE SET
            tagline=excluded.tagline,
            description=excluded.description,
            pricing_monthly=excluded.pricing_monthly,
            pricing_annual=excluded.pricing_annual,
            key_features=excluded.key_features,
            target_audience=excluded.target_audience,
            common_objections=excluded.common_objections,
            custom_system_prompt=excluded.custom_system_prompt,
            is_custom=1
        """, (
            prod_id, name, tagline, description, pricing_monthly, pricing_annual,
            key_features, target_audience, common_objections, custom_prompt
        ))
        await conn.commit()
    return prod_id
```

---

## 8. Action / Tool Layer (`app/tools.py`)

Functions providing the agent with real-time sales actions during live voice conversations.

```python
"""
app/tools.py
External actions and tools invoked by the voice sales agent.
"""

from livekit.agents import llm
import logging

logger = logging.getLogger("sales_tools")

class SalesActionTools(llm.FunctionContext):
    """Exposes callable tools to the Gemini voice assistant."""

    @llm.ai_callable(description="Schedule a product demo when the prospect agrees or requests a walkthrough.")
    def schedule_demo(self, preferred_day: str, email_or_contact: str) -> str:
        """
        Call this when the customer says they want a demo or agrees to a calendar invite.
        """
        try:
            logger.info(f"Demo scheduled: day={preferred_day}, contact={email_or_contact}")
            return f"Demo provisionally scheduled for {preferred_day}. An invite has been queued for {email_or_contact}."
        except Exception as e:
            logger.error(f"Failed to schedule demo: {e}")
            return "Demo requested. I will notify our sales engineers to send an invite immediately."

    @llm.ai_callable(description="Check real-time pricing and eligible discount tiers for a given user count.")
    def check_pricing_tier(self, team_size: int, billing_cycle: str = "annual") -> str:
        """
        Call this when the prospect asks for a specific price quote based on their team size.
        """
        try:
            unit_price = 39.0 if billing_cycle.lower() == "annual" else 49.0
            total = team_size * unit_price
            discount = "20% annual discount applied" if billing_cycle.lower() == "annual" else "standard monthly pricing"
            return f"For a team of {team_size}, the total is ${total:,.2f} per month ({discount})."
        except Exception as e:
            logger.error(f"Error calculating price: {e}")
            return "Our standard plan starts at $39 per user per month with annual billing."

    @llm.ai_callable(description="Record an explicit customer objection for post-call follow up.")
    def record_objection(self, category: str, details: str) -> str:
        """
        Call this when the prospect raises a major barrier (e.g. lack of budget, competitor contract).
        """
        logger.info(f"Objection logged: category={category}, details={details}")
        return "Objection noted. Continuing conversation to address it."
```

---

## 9. Orchestration & Entrypoint (`app/agent.py` & `app/chains.py`)

Wires LiveKit Agent Worker, Gemini Voice Assistant, real-time transcript streaming, audio recording, and the post-call LangChain analysis pipeline.

### Post-Call Extraction Pipeline (`app/chains.py`)
```python
"""
app/chains.py
LangChain + Google Gemini structured extraction for post-call analytics.
"""

from pydantic import BaseModel, Field
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings

class CallAnalysisSchema(BaseModel):
    sales_status: Literal[
        "Converted",
        "Interested",
        "Follow-up Required",
        "Not Interested",
        "Demo Requested",
        "No Response"
    ] = Field(description="Strict classification of the customer sales outcome.")
    summary: str = Field(description="2-3 sentence executive summary of the conversation.")
    customer_requirements: str = Field(description="Key pain points, desired features, or requirements mentioned by customer.")
    objections: str = Field(description="Any objections, hesitations, or blockers raised by the customer.")
    next_steps: str = Field(description="Recommended next actions for the sales team.")


def build_analysis_chain():
    """Builds a LangChain chain with Gemini and structured Pydantic output."""
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_ANALYSIS_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.1
    )
    
    structured_llm = llm.with_structured_output(CallAnalysisSchema)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert sales analyst reviewing an audio sales bot call transcript.
Your job is to rigorously evaluate the conversation and classify the final sales status.

Status Definitions:
- Converted: Customer explicitly agreed to buy, signed up, or requested immediate invoice payment.
- Interested: Customer showed strong positive engagement, asked product questions, and wants more info.
- Demo Requested: Customer asked for or agreed to a scheduled live product demonstration.
- Follow-up Required: Customer requested a callback, needs to check with team/budget, or conversation was inconclusive.
- Not Interested: Customer declined, explicitly said no, stated lack of interest, or hung up angrily.
- No Response: Customer said nothing or conversation was too brief (< 2 turns) to determine intent.

Be concise, factual, and direct."""),
        ("human", """Product Pitched: {product_name}
Call Duration: {duration_seconds} seconds

Full Call Transcript:
{transcript_text}

Provide the structured analysis now.""")
    ])
    
    return prompt | structured_llm
```

### LiveKit Agent Worker Loop (`app/agent.py`)
```python
"""
app/agent.py
LiveKit Realtime Agent worker running Google Gemini voice assistant.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import google, silero, deepgram

from app.config import settings
from app.prompts import build_sales_system_prompt
from app.tools import SalesActionTools
from app.db import (
    create_call,
    update_call_on_end,
    update_call_analysis,
    append_transcript_message,
    get_call_by_session_id,
    get_transcripts_for_call
)
from app.chains import build_analysis_chain

logger = logging.getLogger("voice_sales_agent")


async def entrypoint(ctx: JobContext):
    """Main worker lifecycle entrypoint invoked when a customer enters a room."""
    logger.info(f"Connecting to LiveKit room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Parse room metadata for product & language
    room_metadata = {}
    if ctx.room.metadata:
        try:
            room_metadata = json.loads(ctx.room.metadata)
        except Exception:
            pass

    product_name = room_metadata.get("product_name", settings.DEFAULT_PRODUCT_NAME)
    language = room_metadata.get("language", settings.DEFAULT_LANGUAGE)
    customer_name = room_metadata.get("customer_name", "Valued Customer")
    custom_system_prompt = room_metadata.get("custom_system_prompt")
    custom_product_data = room_metadata.get("custom_product_data")
    session_id = ctx.room.name

    # Initialize call record in database
    call_id = await create_call(session_id, product_name, language, customer_name)
    start_time = datetime.utcnow()

    # 1. Setup VAD (Voice Activity Detection)
    vad = silero.VAD.load()

    # 2. Setup Realtime LLM (Google Gemini)
    gemini_llm = google.LLM(
        model=settings.GEMINI_VOICE_MODEL,
        api_key=settings.GOOGLE_API_KEY
    )

    # 3. Setup STT & TTS
    # If using Deepgram: deepgram.STT() or google.STT()
    stt = google.STT(languages=[language])
    tts = google.TTS(voice_name="en-US-Journey-F" if language == "en-US" else "hi-IN-Standard-A")

    # 4. Initialize Tools
    tools_context = SalesActionTools()

    # 5. Build VoiceAssistant (with custom prompt/product override if provided)
    system_prompt = build_sales_system_prompt(
        product_name=product_name,
        language=language,
        custom_system_prompt=custom_system_prompt,
        custom_product_data=custom_product_data
    )
    
    assistant = VoiceAssistant(
        vad=vad,
        stt=stt,
        llm=gemini_llm,
        tts=tts,
        fnc_ctx=tools_context,
        chat_ctx=llm.ChatContext().append(
            role="system",
            text=system_prompt
        )
    )

    # 6. Real-time Transcript Forwarding & DB Persistence Hook
    @assistant.on("user_speech_committed")
    def on_user_speech(msg: llm.ChatMessage):
        if isinstance(msg.content, str) and msg.content.strip():
            text = msg.content.strip()
            asyncio.create_task(broadcast_and_save(ctx.room, call_id, "customer", text))

    @assistant.on("agent_speech_committed")
    def on_agent_speech(msg: llm.ChatMessage):
        if isinstance(msg.content, str) and msg.content.strip():
            text = msg.content.strip()
            asyncio.create_task(broadcast_and_save(ctx.room, call_id, "bot", text))

    async def broadcast_and_save(room: rtc.Room, c_id: str, speaker: str, text: str):
        # 1. Save to DB
        await append_transcript_message(c_id, speaker, text)
        # 2. Broadcast via LiveKit Data Channel for zero-latency UI chat sync
        payload = json.dumps({
            "type": "transcript",
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        }).encode("utf-8")
        try:
            await room.local_participant.publish_data(payload, reliable=True)
        except Exception as e:
            logger.warning(f"Data channel publish error: {e}")

    # Start assistant
    assistant.start(ctx.room)

    # Play Initial Consent & Sales Greeting
    await asyncio.sleep(1.0)
    initial_greeting = f"{settings.RECORDING_CONSENT_DISCLOSURE} I'm Alex from {product_name}. How can I help your business grow today?"
    await assistant.say(initial_greeting, allow_interruptions=True)
    asyncio.create_task(broadcast_and_save(ctx.room, call_id, "bot", initial_greeting))

    # Wait until participant disconnects
    @ctx.room.on("participant_disconnected")
    def on_disconnect(participant: rtc.RemoteParticipant):
        logger.info(f"Participant left: {participant.identity}. Initiating teardown...")

    # Wait for room closure
    await ctx.wait_for_shutdown()

    # ── Post-Call Lifecycle Execution ──
    duration_seconds = int((datetime.utcnow() - start_time).total_seconds())
    
    # Save audio recording placeholder or file path
    rec_filename = f"call_{call_id}.wav"
    rec_path = os.path.join(settings.RECORDINGS_DIR, rec_filename)
    rec_url = f"/api/calls/{call_id}/recording"

    # Mark call complete in DB
    await update_call_on_end(session_id, duration_seconds, rec_url, rec_path)

    # Run LangChain + Gemini Post-Call Analysis
    logger.info(f"Starting LangChain post-call analysis for call {call_id}...")
    try:
        transcript_rows = await get_transcripts_for_call(call_id)
        transcript_text = "\n".join([f"{r['speaker_type'].upper()}: {r['message_text']}" for r in transcript_rows])
        
        if len(transcript_rows) < 2:
            await update_call_analysis(
                call_id, 
                sales_status="No Response",
                summary="Call ended before meaningful conversation occurred.",
                customer_requirements="None stated",
                objections="None",
                next_steps="Retry outbound contact at another time."
            )
        else:
            chain = build_analysis_chain()
            analysis_result = await chain.ainvoke({
                "product_name": product_name,
                "duration_seconds": duration_seconds,
                "transcript_text": transcript_text
            })
            
            await update_call_analysis(
                call_id,
                sales_status=analysis_result.sales_status,
                summary=analysis_result.summary,
                customer_requirements=analysis_result.customer_requirements,
                objections=analysis_result.objections,
                next_steps=analysis_result.next_steps
            )
            logger.info(f"Analysis saved: status={analysis_result.sales_status}")
    except Exception as e:
        logger.error(f"Error in post-call analysis: {e}")
        await update_call_analysis(
            call_id,
            sales_status="Follow-up Required",
            summary="Automated analysis encountered an error.",
            customer_requirements="Manual review required",
            objections="Manual review required",
            next_steps="Follow up manually with prospect."
        )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

---

## 10. API Layer (`app/server.py`)

FastAPI backend providing LiveKit room tokens, call history listing, recording audio streaming, and serving the frontend UI.

```python
"""
app/server.py
FastAPI REST API server and static asset host.
"""

import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api

from app.config import settings
from app.db import (
    init_db,
    list_calls,
    get_call_by_id,
    get_transcripts_for_call,
    get_all_products
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


@app.on_event("startup")
async def on_startup():
    await init_db()
    os.makedirs(settings.RECORDINGS_DIR, exist_ok=True)


# ── Pydantic Request / Response Models ──

class TokenRequest(BaseModel):
    product_name: str = "CloudScale CRM"
    language: str = "en-US"
    customer_name: str = "Prospect"
    custom_system_prompt: Optional[str] = None
    custom_product_data: Optional[Dict[str, Any]] = None

class TokenResponse(BaseModel):
    token: str
    room_name: str
    livekit_url: str

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
        "custom_system_prompt": req.custom_system_prompt,
        "custom_product_data": req.custom_product_data
    }

    token = (
        api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(participant_identity)
        .with_name(req.customer_name)
        .with_grants(grant)
        .with_metadata(json.dumps(metadata_payload))
        .to_jwt()
    )

    return TokenResponse(
        token=token,
        room_name=room_name,
        livekit_url=settings.LIVEKIT_URL
    )


# ── Calls History & Analytics Endpoints ──

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


@app.get("/api/calls/{call_id}/recording")
async def get_call_recording(call_id: str):
    """Streams the recorded audio file for playback in the web player."""
    call = await get_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    
    filepath = call.get("recording_file_path")
    if filepath and os.path.exists(filepath):
        return FileResponse(filepath, media_type="audio/wav")
    
    # Return synthetic or sample recording if local file is missing
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
async def create_product(product: ProductCreateRequest):
    """
    Saves a user-defined SaaS product or tasker configuration from the UI Customizer Studio.
    Persists to the database and makes it immediately selectable for voice calls.
    """
    from app.db import create_or_update_product
    product_id = await create_or_update_product(product.dict())
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
```

---

## 11. Frontend / UI Spec

The web app is a sleek, responsive Single Page Application (SPA) with a modern dark glassmorphism theme (`#0B0F19` background with subtle neon blue and violet accents).

### Layout & Component Hierarchy
```
┌────────────────────────────────────────────────────────────────────────┐
│  AI VOICE SALES BOT — Sankar Group Live Demo   [⚙️ Prompt & SaaS Studio]│
├────────────────────────────────────────────────────────────────────────┤
│  [ Product Selector: CloudScale CRM ▼ ]  [ Language: English (US) ▼ ]  │
│  [ Customer Name: John Doe          ]  [ Consent: Disclose On Start ☑] │
│  Active Pitch: "AI Sales Automation & Pipeline Intelligence ($39/mo)"  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   CALL CONTROLS BAR:                                                   │
│   [  ▶ START SALES CALL  ]   [  ⏹ END CALL  ]   Duration: 02:45       │
│   Status: [ Speaking / Listening / Processing ]  Waveform: ||||| | ||   │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│   SPLIT VIEW:                                                          │
│   ┌───────────────────────────────┐ ┌────────────────────────────────┐ │
│   │  REAL-TIME LIVE CHAT SCREEN   │ │  CALL POST-ANALYSIS & DETAILS  │ │
│   │                               │ │                                │ │
│   │  [Bot 00:01]                  │ │  Sales Status:                 │ │
│   │  Hello! Please note this call │ │  [ DEMO REQUESTED ] (Badge)    │ │
│   │  is recorded for quality...   │ │                                │ │
│   │                               │ │  Executive Summary:            │ │
│   │  [Customer 00:08]             │ │  Customer is scaling a 12-rep  │ │
│   │  Hi, I'm looking for a CRM    │ │  sales team and wants AI auto- │ │
│   │  that automates note taking.  │ │  mated note logging.           │ │
│   │                               │ │                                │ │
│   │  [Bot 00:15]                  │ │  Requirements: CRM automation  │ │
│   │  CloudScale CRM does exactly  │ │  Objections: Existing contract │ │
│   │  that and saves 10 hrs/week!  │ │  Next Steps: Send Zoom invite  │ │
│   │                               │ │                                │ │
│   │  (Live auto-scrolling stream) │ │  Audio Player: [▶ ──●──── 02:45]│
│   └───────────────────────────────┘ └────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────┤
│   CALL HISTORY & ANALYTICS TABLE                                       │
│   Filter by: [ All ] [ Converted ] [ Demo Requested ] [ Interested ]   │
│   ┌────────┬──────────┬──────────┬──────────────┬────────────┬───────┐ │
│   │ Date   │ Customer │ Product  │ Sales Status │ Duration   │ Audio │ │
│   ├────────┼──────────┼──────────┼──────────────┼────────────┼───────┤ │
│   │ 10-19  │ Alex M.  │ Cloud... │ Demo Req.    │ 03m 12s    │ [ ▶ ] │ │
│   │ 10-19  │ Priya S. │ Cloud... │ Interested   │ 01m 45s    │ [ ▶ ] │ │
│   └────────┴──────────┴──────────┴──────────────┴────────────┴───────┘ │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│  MODAL: SAAS PRODUCT & CUSTOM SYSTEM PROMPT STUDIO                     │
├────────────────────────────────────────────────────────────────────────┤
│  Mode: (•) Configure SaaS Specs      ( ) Write Custom System Prompt    │
│                                                                        │
│  [ Product Name: DevKicks AI         ] [ Tagline: Autonomous QA Bot ]  │
│  [ Monthly Price ($): 79             ] [ Annual Price ($): 59       ]  │
│  [ Target Audience: Engineering leads, QA managers, dev teams      ]  │
│  [ Key Features: GitHub CI sync, zero-flaky tests, auto-heal PRs    ]  │
│                                                                        │
│  Prompt Editor (Variables: {product_name}, {pricing}, {language}):     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ You are DevKicks sales agent. Ask about their current CI test    │  │
│  │ bottlenecks, explain our auto-healing PR tests, and close on...  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  [ Save & Set As Active Pitch ]  [ Reset to Preset ]  [ Cancel ]       │
└────────────────────────────────────────────────────────────────────────┘
```

### Frontend State Machine & JS Functions
```javascript
// Global State Object
state = {
  currentCallId: null,
  room: null,
  callTimerInterval: null,
  callDurationSeconds: 0,
  activeProduct: "CloudScale CRM",
  activeLanguage: "en-US",
  customSystemPrompt: null,
  customProductData: null,
  isCallActive: false
}
```

- `initApp()`: Initializes Lucide icons, loads products from `/api/products`, and loads call history.
- `openCustomizerModal()`: Displays the SaaS and Custom System Prompt Studio modal.
- `saveCustomProduct()`: Posts custom product to `POST /api/products`, updates the dropdown, and calls `syncUIWithProduct()`.
- `applyCustomPrompt(promptText)`: Stores custom prompt in `state.customSystemPrompt` for inclusion in `TokenRequest`.
- `syncUIWithProduct(product)`: Dynamically updates UI elements: product badge, tagline banner, price tag, and active bot persona.
- `startCall()`:
  - Fetches token from `POST /api/token` including `custom_system_prompt` and `custom_product_data`.
  - Connects to LiveKit Room via `LivekitClient.Room()`.
  - Enables local microphone audio track (`room.localParticipant.setMicrophoneEnabled(true)`).
  - Starts call duration timer.
  - Subscribes to room `dataReceived` event to display incoming transcripts immediately.
  - Subscribes to remote participant audio to render live voice waveform visualizer.
- `endCall()`:
  - Disconnects from LiveKit Room (`room.disconnect()`).
  - Stops call timer.
  - Updates UI to "Processing AI Summary & Sales Status...".
  - Polls `/api/calls/{id}` until LangChain post-analysis populates.
  - Refreshes Call History table.
- `handleDataReceived(payload, participant)`: Parses UTF-8 JSON payload from LiveKit data channel and appends chat bubble to `#live-chat-box`.
- `loadCallHistory(statusFilter)`: Fetches `/api/calls?status={status}` and populates the history table.
- `playRecording(callId, audioUrl)`: Mounts audio into custom player with play/pause and progress bar.
- `renderStatusBadge(status)`: Generates colored status badges:
  - `Converted` → Emerald Green (`#10B981`)
  - `Demo Requested` → Electric Blue (`#3B82F6`)
  - `Interested` → Violet Purple (`#8B5CF6`)
  - `Follow-up Required` → Amber Orange (`#F59E0B`)
  - `Not Interested` → Rose Red (`#EF4444`)
  - `No Response` → Slate Gray (`#6B7280`)

---

## 12. Critical Architecture Rules — DO NOT DEVIATE

### Rule 1: LiveKit Token Generation Grants & Participant Identity Isolation
Tokens must provide explicit room names, unique customer IDs, and both publish/subscribe grants. Never reuse room names across calls.

```python
# ❌ WRONG: Hardcoded room, missing data publish grant, leads to collisions and failed chat events
grant = api.VideoGrants(room_join=True, room="sales_room")
token = api.AccessToken(KEY, SECRET).with_grants(grant).to_jwt()

# ✅ CORRECT: Unique room session ID, unique participant ID, data channel enabled
grant = api.VideoGrants(
    room_join=True,
    room=f"sales-call-{os.urandom(4).hex()}",
    can_publish=True,
    can_subscribe=True,
    can_publish_data=True
)
token = (
    api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    .with_identity(f"customer-{os.urandom(3).hex()}")
    .with_name(customer_name)
    .with_grants(grant)
    .with_metadata(json.dumps({"product_name": product_name, "language": language}))
    .to_jwt()
)
```

### Rule 2: Zero-Polling Real-Time Transcript Streaming
Live chat text must stream instantly via LiveKit WebRTC Data Channel. Never force the frontend to poll the database during an active call.

```python
# ❌ WRONG: Only writing to SQLite, forcing frontend to poll DB every 500ms
await db.execute("INSERT INTO transcripts ...")
# (Frontend polling causes high server load, DB locks, and 1-2 second text lag)

# ✅ CORRECT: Broadcast instantly over WebRTC Data Channel AND save to DB asynchronously
payload = json.dumps({
    "type": "transcript",
    "speaker": speaker_type,
    "text": message_text,
    "timestamp": datetime.utcnow().isoformat()
}).encode("utf-8")
await room.local_participant.publish_data(payload, reliable=True)
asyncio.create_task(db_append_transcript(call_id, speaker_type, message_text))
```

### Rule 3: LangChain Gemini Post-Call Structured Extraction
Never use free-form regex parsing on LLM output. Always use Pydantic `with_structured_output` to guarantee the exact six sales statuses.

```python
# ❌ WRONG: Free text prompt with regex searching for keywords
prompt = "Analyze this transcript and write status: Converted or Interested..."
result = await llm.ainvoke(prompt)
if "converted" in result.lower():
    status = "Converted" # Fragile: matches "not converted", crashes on typos

# ✅ CORRECT: Enforced Pydantic schema with Literal enum
class CallAnalysisSchema(BaseModel):
    sales_status: Literal[
        "Converted", "Interested", "Follow-up Required",
        "Not Interested", "Demo Requested", "No Response"
    ]
    summary: str
    customer_requirements: str
    objections: str
    next_steps: str

chain = prompt | llm.with_structured_output(CallAnalysisSchema)
analysis = await chain.ainvoke({"transcript_text": text})
```

### Rule 4: Mandatory Recording Consent & Duration Sync
Call recording must have an explicit disclosure played on call start. Duration must be calculated on the server from room connection to room disconnect.

```python
# ❌ WRONG: Relying on browser clock for call duration (tamperable, breaks on tab close)
duration = client_reported_duration

# ✅ CORRECT: Server records UTC start and calculates exact elapsed duration on worker disconnect
start_time = datetime.utcnow()
# ... call runs ...
duration_seconds = int((datetime.utcnow() - start_time).total_seconds())
await update_call_on_end(session_id, duration_seconds=duration_seconds, ...)
```

### Rule 5: Turn Detection and Acoustic Echo Cancellation (AEC)
WebRTC audio tracks from browser must enable Acoustic Echo Cancellation (`echoCancellation: true`, `noiseSuppression: true`) to prevent the bot's speech from being recaptured by the microphone as customer input.

```javascript
// ❌ WRONG: Default getUserMedia grabs raw audio with echo feedback loop
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

// ✅ CORRECT: Enable hardware/software echo cancellation and noise suppression
await room.localParticipant.setMicrophoneEnabled(true, {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
});
```

### Rule 6: Dynamic Custom Task/Prompt Injection & Metadata Serialization
When passing custom SaaS specs or custom system prompts from the UI to the LiveKit worker, never perform raw string interpolation in token metadata, which crashes with `JSONDecodeError` on quotes and newlines. Always serialize with `json.dumps()` and safely parse with fallbacks.

```python
# ❌ WRONG: Raw string interpolation causes syntax errors on quotes or newlines
token.with_metadata(f'{{"prompt": "{user_custom_prompt}"}}') # Breaks on quotes/newlines!

# ✅ CORRECT: Use structured dictionary serialized with json.dumps()
metadata_payload = {
    "product_name": req.product_name,
    "language": req.language,
    "custom_system_prompt": req.custom_system_prompt,
    "custom_product_data": req.custom_product_data
}
token.with_metadata(json.dumps(metadata_payload))
```

---

## 13. Deployment

### Step 1: Local Development Setup
```bash
# 1. Clone repository & navigate to directory
cd c:\SSD WINDOW\code\AI-Voice-Sales-Bot

# 2. Create and activate Python virtual environment
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate # On Linux/macOS

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Open .env and insert LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, GOOGLE_API_KEY

# 5. Start the LiveKit Agent Worker (Terminal 1)
python -m app.agent start

# 6. Start the FastAPI Web Server (Terminal 2)
python -m uvicorn app.server:app --reload --port 8000
```

### Step 2: Cloud / Docker Deployment (Render, Fly.io, or VPS)
```bash
# Build Docker container
docker build -t voice-sales-bot .

# Run with environment variables
docker run -d \
  -p 8000:8000 \
  -e LIVEKIT_URL="wss://your-project.livekit.cloud" \
  -e LIVEKIT_API_KEY="your_api_key" \
  -e LIVEKIT_API_SECRET="your_api_secret" \
  -e GOOGLE_API_KEY="your_google_key" \
  -v $(pwd)/data:/app/data \
  --name sales-bot voice-sales-bot
```

### Successful Startup Log Output
```
==========================================================
 Starting AI Voice Sales Bot (Sankar Group Assignment)    
==========================================================
Checking Environment Variables...
Configuration OK:
 - LIVEKIT_URL: wss://sales-demo.livekit.cloud
 - PORT: 8000
 - GEMINI_VOICE_MODEL: gemini-2.0-flash
 - GEMINI_ANALYSIS_MODEL: gemini-1.5-flash
Starting LiveKit Agent Worker...
INFO:livekit.agents:registered worker with id: W_xxxxxx
INFO:livekit.agents:listening for jobs on queue...
Starting FastAPI Application Server on port 8000...
INFO:     Started server process [18420]
INFO:     Waiting for application startup.
INFO:     Database initialized at data/sales_bot.db
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 14. Known Gotchas Table

| Symptom | Root Cause | Fix |
| :--- | :--- | :--- |
| **Microphone fails to start with `NotAllowedError`** | Browser blocks microphone access when not on `localhost` or HTTPS. | Access app via `http://localhost:8000` or serve behind valid SSL/TLS certificate. |
| **Agent speaks once and then stays silent** | VAD (Silero) is receiving room audio echo because AEC is disabled. | Ensure `echoCancellation: true` in `setMicrophoneEnabled()`. |
| **Gemini throws `ResourceExhausted (429)`** | Exceeded Gemini free tier rate limits (RPM / TPM). | Switch to `gemini-1.5-flash` or provide billing-enabled Google Cloud API Key. |
| **Live chat text missing in UI** | LiveKit Token was missing `can_publish_data=True` permission. | Ensure `VideoGrants` includes `can_publish_data=True` in `app/server.py`. |
| **Audio recording file missing** | Call ended prematurely before worker could flush audio stream. | Fallback to sample recording or save transcript as textual backup record. |
| **Foreign language (Hindi/Telugu) sounds accented** | Default English TTS voice used for non-English STT input. | Dynamically assign locale-specific TTS voice (e.g. `hi-IN-Standard-A`). |

---

## 15. Reference Data

### Sales Status Enums
```
1. Converted            → Prospect agreed to purchase, signed up, or requested billing link.
2. Interested           → Prospect expressed enthusiasm and engaged with feature pitch.
3. Demo Requested       → Prospect explicitly agreed to a scheduled live software demonstration.
4. Follow-up Required   → Prospect requested more info, callback, or needs team consultation.
5. Not Interested       → Prospect rejected the pitch, expressed no need, or hung up.
6. No Response          → No audible user speech or call disconnected immediately.
```

### Supported Languages & Locale Configurations
| Language | Code | STT Model | TTS Voice Name | Sample Greeting Opening |
| :--- | :--- | :--- | :--- | :--- |
| **English (US)** | `en-US` | `google` / `deepgram` | `en-US-Journey-F` | "Hello! Thanks for connecting. Please note this call is recorded..." |
| **Hindi** | `hi-IN` | `google` | `hi-IN-Standard-A` | "Namaste! Hamse judne ke liye dhanyavad. Kripya dhyan dein yeh call record ho rahi hai..." |
| **Telugu** | `te-IN` | `google` | `te-IN-Standard-A` | "Namaskaram! Maatho matladinanduku dhanyavadalu. Ee call record cheyabaduthundi..." |

---

## 16. Cost / Operations Reference

### Unit Economics per 3-Minute Voice Sales Call
| Service Component | Metric | Rate | Cost per 3-Min Call |
| :--- | :--- | :--- | :--- |
| **LiveKit Cloud WebRTC** | 3 minutes (1 user + 1 bot) | $0.004 / min | $0.024 |
| **Google Gemini 2.0 Flash (Live LLM)** | ~2,500 input + 600 output tokens | $0.10 / 1M in, $0.40 / 1M out | $0.0005 |
| **Google STT (Speech-to-Text)** | 3 minutes audio | $0.006 / min | $0.018 |
| **Google TTS (Text-to-Speech)** | ~1,200 characters synthesized | $16.00 / 1M characters | $0.019 |
| **LangChain + Gemini Post-Analysis** | ~1,000 transcript tokens | $0.075 / 1M tokens | $0.0001 |
| **Total Estimated Cost per Call** | **3-minute live sales interaction** | — | **≈ $0.0616 (~6 cents)** |

---

## 17. External API Integration Reference

### 1. Generating LiveKit Room Token
```python
from livekit import api

grant = api.VideoGrants(
    room_join=True,
    room="sales-session-123",
    can_publish=True,
    can_subscribe=True,
    can_publish_data=True
)

token = (
    api.AccessToken("YOUR_API_KEY", "YOUR_API_SECRET")
    .with_identity("prospect-user")
    .with_name("Customer")
    .with_grants(grant)
    .to_jwt()
)
```

### 2. Invoking LangChain Gemini Structured Extraction
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    sales_status: str
    summary: str
    next_steps: str

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key="API_KEY")
structured_chain = llm.with_structured_output(AnalysisResult)
res = structured_chain.invoke("Call transcript: Customer said they love the product and want a demo Thursday.")
print(res.sales_status) # 'Demo Requested'
```

---

## 18. One-Time Setup Sequence

1. **Sign up for LiveKit Cloud** at [cloud.livekit.io](https://cloud.livekit.io) (Free tier includes $50 monthly credit).
2. Create a new Project in LiveKit Cloud and copy `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`.
3. **Get Google Gemini API Key** at [aistudio.google.com](https://aistudio.google.com).
4. Create `.env` file from `.env.example` in project root and paste the 4 keys.
5. Run `pip install -r requirements.txt` in a Python 3.11+ environment.
6. Run `python -m app.agent start` in your first terminal.
7. Run `python -m uvicorn app.server:app --port 8000` in your second terminal.
8. Open `http://localhost:8000` in Google Chrome or Edge.
9. Click **Start Sales Call**, speak into your microphone, conduct a 1-minute conversation, and observe real-time live chat bubbles appearing.
10. Click **End Call**, view the automatically generated summary and sales status badge, and click the audio playback button to verify call recording.

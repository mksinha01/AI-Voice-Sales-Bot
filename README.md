# AI Voice Sales Bot (SaaS Closer)

An interactive, low-latency, full-duplex conversational voice application that pitches, qualifies, handles objections, and closes sales for SaaS products in multiple languages (English, Hindi, Telugu, and Hinglish).

Built for **Sankar Group – Intern Assignment** based on `doc/goal.md` and `proj.md`.

---

## 🔗 Live Links & Repository

- 🌐 **Live Production Application:** [https://65.20.68.250.sslip.io/](https://65.20.68.250.sslip.io/)
- 📦 **GitHub Repository:** [https://github.com/mksinha01/AI-Voice-Sales-Bot](https://github.com/mksinha01/AI-Voice-Sales-Bot)
- 📑 **Assignment Specification:** [doc/goal.md](doc/goal.md)

---

## 🌟 Key Capabilities

- **Real-Time Voice Conversation:** Low-latency WebRTC bidirectional voice dialogue powered by LiveKit and Google Gemini 2.0 Flash.
- **Multilingual Support:** English (`en-US`), Hindi / Hinglish (`hi-IN`), and Telugu (`te-IN`).
- **Real-Time Live Chat Screen:** Zero-polling instant transcript streaming to the browser over LiveKit WebRTC Data Channels.
- **Call Controls & Timer:** Instant Start/End call buttons, active duration timer, and audio waveform visualizer.
- **Call Recording & Playback:** Automated call recording and web audio player with mandatory consent disclosure at call initiation.
- **LangChain Structured Intelligence:** Post-call extraction with Gemini to parse Executive Summary, Customer Requirements, Objections, and Actionable Next Steps.
- **Sales Status Classification:** Strict assignment of one of 6 outcomes:
  - `Converted`
  - `Interested`
  - `Demo Requested`
  - `Follow-up Required`
  - `Not Interested`
  - `No Response`
- **SaaS Studio & Customizer:** In-app modal to create custom SaaS products, pricing tiers, and arbitrary system prompts (Sales, Support, Screening, etc.).
- **Call History Dashboard:** Interactive persistent log of calls with filtering by sales status, transcript inspection, and audio playback.

---

## 🛠️ Architecture & Tech Stack

```
┌────────────────────────────────────────────────────────┐
│                   Browser Web Client                   │
│ (LiveKit Web SDK, Web Audio, Responsive Dark Theme UI) │
└──────────▲────────────────────────────────▲────────────┘
           │ WebRTC Audio & Data Channels   │ HTTP REST
           ▼                                ▼
┌────────────────────────┐      ┌────────────────────────┐
│  LiveKit Agent Worker  │      │   FastAPI Web Server   │
│ (VoiceAssistant + VAD  │      │ (Token Dispatcher, DB  │
│  + Gemini + STT/TTS)   │      │  CRUD, Static UI Host) │
└──────────┬─────────────┘      └──────────┬─────────────┘
           │ Post-Call Triggers            │
           ▼                               │
┌────────────────────────┐                 │
│ LangChain + Gemini LLM │                 │
│  (Structured Pydantic) │                 │
└──────────┬─────────────┘                 │
           │ Saves Analysis                │
           ▼                               ▼
     ┌───────────────────────────────────────────┐
     │      SQLite3 Database (Idempotent)        │
     └───────────────────────────────────────────┘
```

- **Voice Transport:** LiveKit Cloud / Server (`livekit-agents`, `livekit-client`)
- **Core Intelligence:** Google Gemini (`gemini-2.0-flash` for live dialogue, `gemini-1.5-flash` for post-call analysis)
- **Speech Stack:** Silero VAD + Google Cloud STT & TTS
- **Extraction:** LangChain Core (`ChatGoogleGenerativeAI`) with Pydantic v2 schemas
- **Backend API:** FastAPI, Uvicorn, aiosqlite
- **Frontend:** Modern Vanilla HTML5/CSS3/ES6+ (Dark glassmorphism design system)

---

## 🚀 Quickstart Guide

### 1. Clone & Configure
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Add your API credentials in .env:
# LIVEKIT_URL=wss://your-project.livekit.cloud
# LIVEKIT_API_KEY=your_key
# LIVEKIT_API_SECRET=your_secret
# GOOGLE_API_KEY=your_gemini_api_key
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
Open two terminals:

**Terminal 1 (LiveKit Agent Worker):**
```bash
python -m app.agent start
```

**Terminal 2 (FastAPI Web Server):**
```bash
uvicorn app.server:app --reload --port 8000
```

Open your browser at `http://localhost:8000`.

---

## 🐳 Production Deployment (Vultr Cloud Compute)

### 1. Launch a Vultr VPS
- **Product:** Vultr Cloud Compute (Shared CPU or High Performance)
- **OS:** Ubuntu 24.04 LTS (x64)
- **Specs:** 1 vCPU, 2GB RAM, 50GB NVMe SSD ($10–$12/month)
- **Networking:** In Vultr DNS, point an **A Record** (e.g., `salesbot.yourdomain.com`) to your VPS public IPv4 address.

### 2. Deploy via Bootstrap Script
SSH into your Vultr server and run:

```bash
# 1. Clone repository
git clone https://github.com/mksinha01/AI-Voice-Sales-Bot.git
cd AI-Voice-Sales-Bot

# 2. Configure production environment
cp .env.production.example .env
nano .env   # Add LIVEKIT credentials, GOOGLE_API_KEY, and your DOMAIN

# 3. Run automated setup script
chmod +x deploy/setup-vultr.sh
sudo ./deploy/setup-vultr.sh
```

The script configures UFW firewall (22/SSH, 80/HTTP, 443/HTTPS), installs Docker, and boots the Docker Compose stack with Caddy automated Let's Encrypt SSL.

### 3. Management Commands
```bash
# View live logs (FastAPI + LiveKit Agent + Caddy)
docker compose logs -f

# Restart application
docker compose restart

# Verify health status
curl -k https://localhost/api/health
```

---

## 📝 Assignment Verification Checklist

- [x] 1. Voice Conversation with customer understanding & objection handling.
- [x] 2. Multilingual capabilities (English, Hindi, Telugu).
- [x] 3. Live chat screen with sub-second real-time streaming bubbles.
- [x] 4. Start/End controls, duration timer, and status indicators.
- [x] 5. Call recording, web player, and regulatory consent disclosure.
- [x] 6. Automated post-call summary, requirements, objections, next steps.
- [x] 7. Automated classification into the 6 strictly defined sales statuses.
- [x] 8. Persistent call history with search/filter, playback, and transcripts.

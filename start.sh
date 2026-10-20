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

# Launch Agent Worker in background
echo "Starting LiveKit Agent Worker..."
python -m app.agent start &
AGENT_PID=$!

# Launch FastAPI Server in foreground
echo "Starting FastAPI Application Server on port ${PORT:-8000}..."
exec uvicorn app.server:app --host 0.0.0.0 --port "${PORT:-8000}"

"""
app/agent.py
LiveKit Realtime Agent worker running Google Gemini voice assistant.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import edge_tts
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    tts,
    utils,
    voice,
)
from livekit.agents.tts import AudioEmitter, ChunkedStream
from livekit.agents.tts.tts import DEFAULT_API_CONNECT_OPTIONS
from livekit.plugins import cartesia, google, silero
from livekit.plugins.google.beta import GeminiSTT

from app.config import settings
from app.prompts import build_sales_system_prompt, build_initial_sales_greeting, compile_agent_system_prompt
from app.tools import sales_tools, set_call_terminator, get_tools_for_permissions
from app.db import (
    create_call,
    get_call_by_session_id,
    update_call_on_end,
    update_call_analysis,
    append_transcript_message,
    get_transcripts_for_call,
    get_agent_version,
    get_active_agent_version,
    record_sales_event,
)
from app.chains import build_analysis_chain

logger = logging.getLogger("voice_sales_agent")


class EdgeTTSChunkedStream(ChunkedStream):
    async def _run(self, output_emitter: AudioEmitter) -> None:
        voice = getattr(self._tts, "_voice", "en-US-GuyNeural")
        if voice == "auto":
            voice = "en-US-GuyNeural"
            for ch in self._input_text:
                if "\u0c00" <= ch <= "\u0c7f":
                    voice = "te-IN-MohanNeural"
                    break
                if "\u0900" <= ch <= "\u097f":
                    voice = "hi-IN-MadhurNeural"
                    break
        communicate = edge_tts.Communicate(self._input_text, voice)
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=24000,
            num_channels=1,
            mime_type="audio/mpeg",
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                output_emitter.push(chunk["data"])


class EdgeTTS(tts.TTS):
    """High-quality Microsoft Neural TTS wrapper - 100% free with unlimited quota."""
    def __init__(self, voice: str = "en-US-GuyNeural"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1,
        )
        self._voice = voice

    def synthesize(self, text: str, *, conn_options=DEFAULT_API_CONNECT_OPTIONS) -> ChunkedStream:
        return EdgeTTSChunkedStream(tts=self, input_text=text, conn_options=conn_options)


def get_cartesia_voice(language: str) -> str:
    """Returns Cartesia Sonic voice ID for the given language."""
    mapping = {
        "auto": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
        "en-US": "f786b574-daa5-4673-aa0c-cbe3e8534c02",  # Professional Conversational Male
        "hi-IN": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
        "te-IN": "f786b574-daa5-4673-aa0c-cbe3e8534c02",
    }
    return mapping.get(language, "f786b574-daa5-4673-aa0c-cbe3e8534c02")


def get_tts_voice(language: str) -> str:
    """Returns free Microsoft Neural TTS voice without rate limits."""
    mapping = {
        "auto": "auto",
        "hi-IN": "hi-IN-MadhurNeural",
        "te-IN": "te-IN-MohanNeural",
        "en-US": "en-US-GuyNeural",
    }
    return mapping.get(language, "auto" if language == "auto" else "en-US-GuyNeural")


def prewarm(proc: JobProcess):
    """Prewarm heavy models and SSL/genai contexts before accepting calls to eliminate event loop stalls."""
    logger.info("Prewarming Silero VAD and Gemini LLM...")
    proc.userdata["vad"] = silero.VAD.load()
    if settings.GOOGLE_API_KEY:
        try:
            proc.userdata["llm"] = google.LLM(
                model=settings.GEMINI_VOICE_MODEL,
                api_key=settings.GOOGLE_API_KEY,
            )
        except Exception as e:
            logger.warning(f"Error during prewarm: {e}")


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
    disclose_consent = room_metadata.get("disclose_consent", True)
    custom_system_prompt = room_metadata.get("custom_system_prompt")
    custom_product_data = room_metadata.get("custom_product_data")
    session_id = ctx.room.name

    # Initialize call record in database (reuse if pre-created by server token dispatcher)
    existing_call = await get_call_by_session_id(session_id)
    if existing_call:
        call_id = existing_call["id"]
    else:
        call_id = await create_call(session_id, product_name, language, customer_name)
    start_time = datetime.now(timezone.utc)

    # 1. Setup VAD (reuse prewarmed instance to eliminate event loop freeze)
    vad = ctx.proc.userdata.get("vad") if hasattr(ctx, "proc") and ctx.proc else None
    if vad is None:
        vad = silero.VAD.load()

    # 2. Setup Realtime LLM (Google Gemini - reuse prewarmed instance)
    gemini_llm = ctx.proc.userdata.get("llm") if hasattr(ctx, "proc") and ctx.proc else None
    if gemini_llm is None:
        gemini_llm = google.LLM(
            model=settings.GEMINI_VOICE_MODEL,
            api_key=settings.GOOGLE_API_KEY,
        )

    # 3. Setup STT (Gemini) & TTS (Cartesia Sonic with EdgeTTS fallback)
    if language == "auto":
        stt = GeminiSTT(
            language=None,
            language_codes=["en-US", "hi-IN", "te-IN"],
            api_key=settings.GOOGLE_API_KEY,
        )
    else:
        stt = GeminiSTT(language=language, api_key=settings.GOOGLE_API_KEY)

    cartesia_api_key = settings.CARTESIA_API_KEY or os.environ.get("CARTESIA_API_KEY")
    tts_engine = None
    if cartesia_api_key:
        try:
            cartesia_lang = None if language == "auto" else (language.split("-")[0] if language else "en")
            tts_engine = cartesia.TTS(
                api_key=cartesia_api_key,
                model="sonic-3.5",
                language=cartesia_lang,
                voice=get_cartesia_voice(language),
                word_timestamps=(cartesia_lang in ["en", "de", "es", "fr"]) if cartesia_lang else False,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Cartesia TTS, falling back to EdgeTTS: {e}")
            tts_engine = None

    if tts_engine is None:
        voice_name = get_tts_voice(language)
        tts_engine = EdgeTTS(voice=voice_name)

    # 4. Resolve pinned version, system prompt, and permitted tools
    agent_id = room_metadata.get("agent_id")
    version_id = room_metadata.get("version_id")
    allowed_tools_meta = room_metadata.get("allowed_tools")

    active_version = None
    if version_id:
        active_version = await get_agent_version(version_id)
    if not active_version:
        active_version = await get_active_agent_version(agent_id)

    if active_version:
        system_prompt = compile_agent_system_prompt(active_version)
        tools = get_tools_for_permissions(active_version.get("tool_permissions"))
        logger.info(f"Loaded pinned version {active_version.get('version_tag')} with {len(tools)} permitted tools.")
    elif custom_system_prompt:
        system_prompt = custom_system_prompt
        tools = get_tools_for_permissions(allowed_tools_meta)
    else:
        system_prompt = build_sales_system_prompt(
            product_name=product_name,
            language=language,
            custom_product_data=custom_product_data,
        )
        tools = get_tools_for_permissions(allowed_tools_meta)

    # 5. Initialize Voice Session & Agent with dynamic tools
    session = voice.AgentSession(
        vad=vad,
        stt=stt,
        llm=gemini_llm,
        tts=tts_engine,
        tools=tools,
    )

    last_spoken_text = None
    seen_bot_texts = set()

    class SalesAgent(voice.Agent):
        def transcription_node(self, text, model_settings):
            async def _intercept():
                accumulated = []
                async for chunk in text:
                    accumulated.append(str(chunk))
                    yield chunk
                full_text = "".join(accumulated).strip()
                if full_text:
                    nonlocal last_spoken_text
                    if full_text != last_spoken_text:
                        last_spoken_text = full_text
                        asyncio.create_task(broadcast_and_save(ctx.room, call_id, "bot", full_text))
            return _intercept()

    agent = SalesAgent(
        instructions=system_prompt,
        tools=tools,
    )

    async def broadcast_and_save(room: rtc.Room, c_id: str, speaker: str, text: str):
        if speaker == "bot":
            norm_key = " ".join(text.split())
            if norm_key in seen_bot_texts:
                return
            seen_bot_texts.add(norm_key)

        # 1. Save to DB
        await append_transcript_message(c_id, speaker, text)
        # 2. Broadcast via LiveKit Data Channel for zero-latency UI chat sync
        payload = json.dumps({
            "type": "transcript",
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).encode("utf-8")
        try:
            if room.local_participant:
                await room.local_participant.publish_data(payload, reliable=True)
        except Exception as e:
            logger.warning(f"Data channel publish error: {e}")

    async def broadcast_typing(room: rtc.Room, speaker: str = "bot"):
        payload = json.dumps({
            "type": "typing",
            "speaker": speaker
        }).encode("utf-8")
        try:
            if room.local_participant:
                await room.local_participant.publish_data(payload, reliable=True)
        except Exception as e:
            logger.debug(f"Data channel typing publish error: {e}")

    # Real-time Customer Speech Hook
    @session.on("user_input_transcribed")
    def on_user_input(ev: voice.UserInputTranscribedEvent):
        try:
            if ev.is_final and ev.transcript and ev.transcript.strip():
                detected_lang = getattr(ev, "language", None)
                if detected_lang:
                    logger.info(f"Customer speech language detected: {detected_lang}")
                asyncio.create_task(broadcast_and_save(ctx.room, call_id, "customer", ev.transcript.strip()))
                asyncio.create_task(broadcast_typing(ctx.room, "bot"))
        except Exception as err:
            logger.warning(f"Error handling customer transcription: {err}")

    # Fallback Agent and User Speech Hook
    @session.on("conversation_item_added")
    def on_conversation_item(ev: voice.ConversationItemAddedEvent):
        nonlocal last_spoken_text
        try:
            item = ev.item
            role = getattr(item, "role", "")
            text = getattr(item, "text_content", None) or getattr(item, "raw_text_content", None)
            if role == "assistant" and text and text.strip():
                clean_text = text.strip()
                if clean_text != last_spoken_text:
                    last_spoken_text = clean_text
                    asyncio.create_task(broadcast_and_save(ctx.room, call_id, "bot", clean_text))
            elif role == "user" and text and text.strip():
                clean_text = text.strip()
                asyncio.create_task(broadcast_and_save(ctx.room, call_id, "customer", clean_text))
        except Exception as err:
            logger.warning(f"Error handling conversation item: {err}")

    # Real-time Agent State Hook (Typing indicator when thinking/speaking)
    @session.on("agent_state_changed")
    def on_agent_state(ev: voice.AgentStateChangedEvent):
        try:
            state = getattr(ev, "new_state", "")
            if state in ("thinking", "speaking"):
                asyncio.create_task(broadcast_typing(ctx.room, "bot"))
        except Exception:
            pass

    # Disconnect signaling
    disconnect_event = asyncio.Event()

    async def _handle_end_call(reason: str):
        logger.info(f"Auto-ending call: reason={reason}")
        payload = json.dumps({"type": "end_call", "reason": reason}).encode("utf-8")
        try:
            if ctx.room.local_participant:
                await ctx.room.local_participant.publish_data(payload, reliable=True)
        except Exception as e:
            logger.warning(f"Failed to publish end_call data: {e}")

        # Wait briefly for the bot's farewell speech to finish playing
        try:
            await asyncio.sleep(1.0)
            await asyncio.wait_for(session.wait_for_idle(), timeout=4.0)
        except Exception:
            await asyncio.sleep(2.0)

        disconnect_event.set()
        try:
            await ctx.delete_room()
        except Exception:
            pass

    def trigger_end_call(reason: str = "Customer requested to end call"):
        asyncio.create_task(_handle_end_call(reason))

    set_call_terminator(trigger_end_call)

    @ctx.room.on("disconnected")
    def on_disconnected():
        logger.info("Room disconnected.")
        disconnect_event.set()

    @ctx.room.on("participant_disconnected")
    def on_part_disconnected(part):
        logger.info(f"Participant disconnected: {part.identity}")
        if not part.identity.startswith("agent-"):
            disconnect_event.set()

    async def _on_shutdown(reason=None):
        logger.info(f"Shutdown callback invoked: {reason}")
        set_call_terminator(None)
        disconnect_event.set()

    ctx.add_shutdown_callback(_on_shutdown)

    # Start voice session with LiveKit room
    await session.start(agent, room=ctx.room)

    # If customer is not yet in room, wait briefly
    if not ctx.room.remote_participants:
        try:
            await asyncio.wait_for(ctx.wait_for_participant(), timeout=4.0)
        except Exception:
            pass

    # Initial Sales Pitch - broadcast immediately so live chat receives it with zero delay
    await asyncio.sleep(0.3)
    initial_greeting = build_initial_sales_greeting(
        product_name=product_name,
        language=language,
        product_data=custom_product_data,
        customer_name=customer_name,
        disclose_consent=disclose_consent
    )
    last_spoken_text = initial_greeting.strip()
    speech = session.say(initial_greeting, allow_interruptions=False)
    asyncio.create_task(broadcast_and_save(ctx.room, call_id, "bot", last_spoken_text))
    try:
        await speech.wait_for_playout()
    except Exception:
        pass

    # Wait for call to conclude
    await disconnect_event.wait()
    set_call_terminator(None)

    # Gracefully shut down active session to prevent dangling socket retries
    try:
        await session.aclose()
    except Exception:
        pass

    # ── Post-Call Lifecycle Execution ──
    duration_seconds = max(1, int((datetime.now(timezone.utc) - start_time).total_seconds()))

    webm_filename = f"call_{call_id}.webm"
    webm_path = os.path.join(settings.RECORDINGS_DIR, webm_filename)
    rec_filename = f"call_{call_id}.wav"
    rec_path = os.path.join(settings.RECORDINGS_DIR, rec_filename)
    rec_url = f"/api/calls/{call_id}/recording"

    if os.path.exists(webm_path):
        rec_path = webm_path
    elif not os.path.exists(rec_path):
        sample_path = os.path.join(settings.RECORDINGS_DIR, "sample_call.wav")
        if os.path.exists(sample_path):
            import shutil
            shutil.copyfile(sample_path, rec_path)

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
            summary="Automated analysis encountered an error or key limit.",
            customer_requirements="Manual review required",
            objections="Manual review required",
            next_steps="Follow up manually with prospect."
        )


if __name__ == "__main__":
    # Populate os.environ so all sub-processes inherit credentials
    if settings.LIVEKIT_URL:
        os.environ["LIVEKIT_URL"] = settings.LIVEKIT_URL
    if settings.LIVEKIT_API_KEY:
        os.environ["LIVEKIT_API_KEY"] = settings.LIVEKIT_API_KEY
    if settings.LIVEKIT_API_SECRET:
        os.environ["LIVEKIT_API_SECRET"] = settings.LIVEKIT_API_SECRET
    if settings.GOOGLE_API_KEY:
        os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY
    if settings.CARTESIA_API_KEY:
        os.environ["CARTESIA_API_KEY"] = settings.CARTESIA_API_KEY

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="sales-bot-agent",
            ws_url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            load_threshold=0.98,
        )
    )

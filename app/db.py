"""
app/db.py
Data access layer for calls, transcripts, and products using async SQLite.
"""

from contextlib import asynccontextmanager
import aiosqlite
import json
import os
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


@asynccontextmanager
async def get_db_connection():
    """Context manager creating and cleanly closing an asynchronous SQLite connection."""
    db_dir = os.path.dirname(settings.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute("PRAGMA journal_mode = WAL;")
        yield conn


async def init_db() -> None:
    """Creates tables idempotently and populates seed products."""
    async with get_db_connection() as conn:
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
            custom_system_prompt TEXT,
            is_custom BOOLEAN DEFAULT 0,
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
        if row and row["count"] == 0:
            from app.prompts import PRODUCT_CATALOG
            for name, data in PRODUCT_CATALOG.items():
                await conn.execute("""
                INSERT OR IGNORE INTO products (
                    id, name, tagline, description, pricing_monthly, pricing_annual, 
                    key_features, target_audience, common_objections, is_custom
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    str(uuid.uuid4()), name, data["tagline"], data["description"],
                    data["pricing_monthly"], data["pricing_annual"],
                    json.dumps(data["key_features"]), data["target_audience"],
                    json.dumps(data.get("objections", {}))
                ))
        await conn.commit()


# ── Calls Data Layer ──

async def create_call(session_id: str, product_name: str, language: str = "en-US", customer_name: str = "Prospect") -> str:
    call_id = str(uuid.uuid4())
    async with get_db_connection() as conn:
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
    async with get_db_connection() as conn:
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

    async with get_db_connection() as conn:
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
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM calls WHERE session_id = ?", (session_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_call_by_id(call_id: str) -> Optional[Dict[str, Any]]:
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_calls(limit: int = 50, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    async with get_db_connection() as conn:
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
    message_text = (message_text or "").strip()
    if not message_text:
        return ""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT message_text FROM transcripts WHERE call_id = ? AND speaker_type = ? ORDER BY timestamp DESC LIMIT 1",
            (call_id, speaker_type)
        )
        last_row = await cursor.fetchone()
        if last_row and last_row["message_text"] == message_text:
            return ""

        message_id = str(uuid.uuid4())
        await conn.execute("""
        INSERT INTO transcripts (id, call_id, speaker_type, message_text, latency_ms, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, call_id, speaker_type, message_text, latency_ms, datetime.utcnow().isoformat()))
        await conn.commit()
    return message_id


async def get_transcripts_for_call(call_id: str) -> List[Dict[str, Any]]:
    async with get_db_connection() as conn:
        cursor = await conn.execute("""
        SELECT * FROM transcripts WHERE call_id = ? ORDER BY timestamp ASC
        """, (call_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


# ── Products Data Layer ──

async def get_all_products() -> List[Dict[str, Any]]:
    async with get_db_connection() as conn:
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

    async with get_db_connection() as conn:
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

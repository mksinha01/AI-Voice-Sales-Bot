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

        -- ── Agent Persona & Version Control Tables ──
        CREATE TABLE IF NOT EXISTS sales_agents (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL DEFAULT 'default_org',
            name TEXT NOT NULL,
            description TEXT,
            active_version_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sales_agent_versions (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            version_tag TEXT NOT NULL,
            system_prompt TEXT,
            persona TEXT NOT NULL,
            sales_objective TEXT NOT NULL,
            customer_profile TEXT NOT NULL,
            sales_workflow TEXT NOT NULL,
            knowledge_config TEXT NOT NULL,
            tool_permissions TEXT NOT NULL,
            model_config TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(agent_id) REFERENCES sales_agents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sales_sessions (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            pinned_version_id TEXT NOT NULL,
            customer_name TEXT DEFAULT 'Prospect',
            customer_contact TEXT DEFAULT 'N/A',
            session_status TEXT NOT NULL DEFAULT 'initiated',
            config_snapshot TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(agent_id) REFERENCES sales_agents(id),
            FOREIGN KEY(pinned_version_id) REFERENCES sales_agent_versions(id)
        );

        CREATE TABLE IF NOT EXISTS sales_events (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sales_sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_calls_created_at ON calls(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_calls_sales_status ON calls(sales_status);
        CREATE INDEX IF NOT EXISTS idx_transcripts_call_id ON transcripts(call_id);
        CREATE INDEX IF NOT EXISTS idx_versions_agent_id ON sales_agent_versions(agent_id);
        CREATE INDEX IF NOT EXISTS idx_versions_status ON sales_agent_versions(status);
        CREATE INDEX IF NOT EXISTS idx_sessions_pinned_version ON sales_sessions(pinned_version_id);
        CREATE INDEX IF NOT EXISTS idx_events_session_id ON sales_events(session_id);
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

        # Seed Default Sales Agent & Versions if empty
        cursor = await conn.execute("SELECT COUNT(*) as count FROM sales_agents")
        agent_row = await cursor.fetchone()
        if agent_row and agent_row["count"] == 0:
            agent_id = "agent-alex-closer"
            v2_id = "ver-v2-product-closer"

            await conn.execute("""
            INSERT INTO sales_agents (id, owner_id, name, description, active_version_id)
            VALUES (?, 'default_org', 'Alex Closer — Enterprise Sales Suite', 'Dynamic AI sales engine with real-time persona version control, objection handling, and CRM automation.', ?)
            """, (agent_id, v2_id))

            seed_versions = [
                {
                    "id": "ver-v1-lead-qualification",
                    "agent_id": agent_id,
                    "version_number": 1,
                    "version_tag": "v1 — Lead Qualification Specialist",
                    "status": "published",
                    "sales_objective": "Qualify inbound and outbound prospects against BANT (Budget, Authority, Need, Timeline) before routing to account executives.",
                    "persona": {
                        "name": "Alex Closer",
                        "role": "Lead Qualification Specialist",
                        "tone": "Inquisitive, empathetic, professional",
                        "language": "en-US",
                        "greeting": "Hello! Thanks for connecting. I am Alex with CloudScale CRM. What key challenges are you experiencing with your sales workflow today?"
                    },
                    "customer_profile": {
                        "icp": "Mid-market B2B SaaS Sales Leaders & RevOps managers",
                        "company_size": "25-250 reps",
                        "pain_points": "Disorganized CRM data, slow lead response times, lost deal attribution"
                    },
                    "sales_workflow": {
                        "stages": ["Greeting & Consent", "Identify Pipeline Bottlenecks", "Ask 4 BANT Qualification Questions", "Score Lead Fit", "Schedule Discovery Call"],
                        "qualification_questions": [
                            "What is your current team size and monthly pipeline volume?",
                            "Who besides yourself would evaluate this decision?",
                            "What timeline are you targeting to solve this?",
                            "Have you allocated budget for sales automation this quarter?"
                        ],
                        "closing_strategy": "Secure provisional 15-minute qualification review call with Solutions Specialist",
                        "escalation_rules": "Escalate to Human Account Executive if prospect requests custom security review or enterprise SLA"
                    },
                    "knowledge_config": {
                        "products": ["CloudScale CRM Starter", "CloudScale CRM Growth"],
                        "pricing_monthly": 49,
                        "pricing_annual": 39,
                        "approved_offers": ["14-day free pilot for teams over 10 reps", "Free CRM data migration"],
                        "faqs": {
                            "Can it connect to HubSpot?": "Yes, two-way sync in under 5 minutes.",
                            "Is it SOC-2 compliant?": "Yes, SOC-2 Type II and GDPR certified."
                        }
                    },
                    "tool_permissions": ["lookup_crm_lead", "create_sales_opportunity", "record_objection", "escalate_human_handoff", "end_call"],
                    "model_config": {
                        "provider": "google",
                        "model_name": "gemini-2.0-flash",
                        "temperature": 0.4,
                        "voice_id": "en-US-GuyNeural",
                        "speech_rate": 1.0
                    }
                },
                {
                    "id": v2_id,
                    "agent_id": agent_id,
                    "version_number": 2,
                    "version_tag": "v2 — Product Sales Closer",
                    "status": "active",
                    "sales_objective": "Directly pitch CloudScale CRM, demonstrate revenue ROI, handle objections, and secure commitment for a live product demonstration.",
                    "persona": {
                        "name": "Alex Closer",
                        "role": "Senior SaaS Account Executive",
                        "tone": "High-conviction, consultative, persuasive",
                        "language": "en-US",
                        "greeting": "Hello! Alex here from CloudScale CRM. We help sales teams automate 80% of CRM data entry and boost win-rates. What sales bottlenecks are slowing down your team today?"
                    },
                    "customer_profile": {
                        "icp": "VP of Sales, CROs, Revenue Leaders",
                        "company_size": "10-500 employees",
                        "pain_points": "Reps wasting 6 hours a week logging calls, inaccurate forecasting, deal slippage"
                    },
                    "sales_workflow": {
                        "stages": ["Consultative Greeting", "Discovery on Deal Flow", "ROI Demonstration & Pitch", "Objection Handling", "Live Demo Commitment"],
                        "qualification_questions": [
                            "How many sales reps are manually logging calls?",
                            "What CRM system are you using today?",
                            "How much time is lost each week to manual data entry?"
                        ],
                        "closing_strategy": "Lock in product walkthrough with Senior Solutions Architect this Friday at 2:00 PM",
                        "escalation_rules": "Offer customized enterprise billing discount if team exceeds 50 seats"
                    },
                    "knowledge_config": {
                        "products": ["CloudScale CRM Enterprise", "Securify Vault", "DevFlow AI"],
                        "pricing_monthly": 49,
                        "pricing_annual": 39,
                        "approved_offers": ["20% annual discount applied instantly", "Zero onboarding setup fee for annual commitments"],
                        "faqs": {
                            "How long does onboarding take?": "Most teams are fully onboarded in under 48 hours.",
                            "Does it integrate with Slack?": "Yes, real-time deal alerts and win celebrations post automatically."
                        }
                    },
                    "tool_permissions": ["lookup_crm_lead", "create_sales_opportunity", "schedule_demo", "check_pricing_tier", "record_objection", "escalate_human_handoff", "end_call"],
                    "model_config": {
                        "provider": "google",
                        "model_name": "gemini-2.0-flash",
                        "temperature": 0.3,
                        "voice_id": "en-US-GuyNeural",
                        "speech_rate": 1.05
                    }
                },
                {
                    "id": "ver-v3-appointment-booking",
                    "agent_id": agent_id,
                    "version_number": 3,
                    "version_tag": "v3 — Appointment Booking Agent",
                    "status": "published",
                    "sales_objective": "Streamlined calendar coordination: check prospect availability and book qualified meetings directly into sales reps' calendars.",
                    "persona": {
                        "name": "Alex Closer",
                        "role": "Calendar Scheduling Concierge",
                        "tone": "Efficient, courteous, organized",
                        "language": "en-US",
                        "greeting": "Hi there! Alex from CloudScale. I am reaching out to lock in your personalized walkthrough with our solution engineer. Do mornings or afternoons work better for you this week?"
                    },
                    "customer_profile": {
                        "icp": "Busy executives who requested info via web form or email",
                        "company_size": "Any",
                        "pain_points": "Calendar back-and-forth, time constraints"
                    },
                    "sales_workflow": {
                        "stages": ["Greeting", "Confirm Interest", "Identify Preferred Day & Time", "Capture Email/Phone", "Send Calendar Invite"],
                        "qualification_questions": ["What day this week has the clearest 20-minute window for you?"],
                        "closing_strategy": "Confirm calendar invite sent and offer SMS reminder",
                        "escalation_rules": "If prospect is busy all week, schedule next Tuesday or offer asynchronous video link"
                    },
                    "knowledge_config": {
                        "products": ["CloudScale CRM"],
                        "pricing_monthly": 49,
                        "pricing_annual": 39,
                        "approved_offers": ["Priority VIP Demo Slot"],
                        "faqs": {
                            "Who will lead the demo?": "A Senior Solutions Architect tailored to your industry."
                        }
                    },
                    "tool_permissions": ["schedule_demo", "lookup_crm_lead", "end_call"],
                    "model_config": {
                        "provider": "google",
                        "model_name": "gemini-2.0-flash",
                        "temperature": 0.2,
                        "voice_id": "en-US-GuyNeural",
                        "speech_rate": 1.0
                    }
                },
                {
                    "id": "ver-v4-customer-followup",
                    "agent_id": agent_id,
                    "version_number": 4,
                    "version_tag": "v4 — Customer Follow-up Agent",
                    "status": "published",
                    "sales_objective": "Re-engage warm prospects who received a proposal or attended a demo, answer outstanding questions, and close the contract.",
                    "persona": {
                        "name": "Alex Closer",
                        "role": "Customer Success & Deal Closer",
                        "tone": "Friendly, attentive, reassuring",
                        "language": "en-US",
                        "greeting": "Hello! Alex following up from CloudScale CRM. I wanted to see how your team is feeling about the demonstration and proposal we sent over yesterday."
                    },
                    "customer_profile": {
                        "icp": "Prospects in post-demo evaluation stage",
                        "company_size": "10-250 seats",
                        "pain_points": "Procurement delays, competitor evaluations, budget sign-off"
                    },
                    "sales_workflow": {
                        "stages": ["Warm Follow-up Greeting", "Ask for Reaction to Demo/Proposal", "Identify Lingering Questions/Concerns", "Offer Contract Acceleration Incentive", "Sign-off Confirmation"],
                        "qualification_questions": [
                            "Did your executive team have a chance to review the pricing sheet?",
                            "Are there any technical criteria remaining to test?"
                        ],
                        "closing_strategy": "Secure verbal agreement or schedule signature review with decision maker",
                        "escalation_rules": "Transfer directly to Account Director if competitor pricing match is requested"
                    },
                    "knowledge_config": {
                        "products": ["CloudScale CRM Enterprise"],
                        "pricing_monthly": 49,
                        "pricing_annual": 39,
                        "approved_offers": ["Quarter-end acceleration: 25% discount if signed by end of month"],
                        "faqs": {
                            "What are the payment terms?": "Net 30 with annual invoicing or monthly credit card."
                        }
                    },
                    "tool_permissions": ["lookup_crm_lead", "create_sales_opportunity", "check_pricing_tier", "record_objection", "escalate_human_handoff", "end_call"],
                    "model_config": {
                        "provider": "google",
                        "model_name": "gemini-2.0-flash",
                        "temperature": 0.35,
                        "voice_id": "en-US-GuyNeural",
                        "speech_rate": 1.0
                    }
                },
                {
                    "id": "ver-v5-custom-agent",
                    "agent_id": agent_id,
                    "version_number": 5,
                    "version_tag": "v5 — Custom Enterprise Sales Agent",
                    "status": "draft",
                    "sales_objective": "Bespoke enterprise sales persona customizable in real-time through the frontend version editor.",
                    "persona": {
                        "name": "Jordan Vance",
                        "role": "Strategic Enterprise Director",
                        "tone": "Executive, consultative, sharp",
                        "language": "en-US",
                        "greeting": "Good day. Jordan Vance here with CloudScale Enterprise Solutions. I understand you are leading digital transformation across your revenue operations."
                    },
                    "customer_profile": {
                        "icp": "Global 2000 CIOs and Chief Commercial Officers",
                        "company_size": "1,000+ employees",
                        "pain_points": "Legacy CRM migration, global data residency, multi-currency revenue ops"
                    },
                    "sales_workflow": {
                        "stages": ["Executive Introduction", "Strategic Discovery", "Architecture Overview", "Custom Commercial Proposal", "Executive Steering Committee Alignment"],
                        "qualification_questions": [
                            "What is your global sales headcount across EMEA and APAC?",
                            "What enterprise ERP and CRM systems must we integrate with?"
                        ],
                        "closing_strategy": "Initiate proof-of-concept statement of work",
                        "escalation_rules": "Connect directly with Chief Technology Officer"
                    },
                    "knowledge_config": {
                        "products": ["CloudScale CRM Global Enterprise"],
                        "pricing_monthly": 120,
                        "pricing_annual": 99,
                        "approved_offers": ["Custom proof-of-concept milestone billing", "Dedicated Solutions Engineering Pod"],
                        "faqs": {
                            "Can you deploy on our private VPC?": "Yes, we support AWS GovCloud and dedicated private VPC deployments."
                        }
                    },
                    "tool_permissions": ["lookup_crm_lead", "create_sales_opportunity", "schedule_demo", "check_pricing_tier", "record_objection", "escalate_human_handoff", "end_call"],
                    "model_config": {
                        "provider": "google",
                        "model_name": "gemini-2.0-flash",
                        "temperature": 0.3,
                        "voice_id": "en-US-GuyNeural",
                        "speech_rate": 1.0
                    }
                }
            ]

            for v in seed_versions:
                await conn.execute("""
                INSERT INTO sales_agent_versions (
                    id, agent_id, version_number, version_tag, system_prompt, persona,
                    sales_objective, customer_profile, sales_workflow, knowledge_config,
                    tool_permissions, model_config, status
                ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    v["id"], v["agent_id"], v["version_number"], v["version_tag"],
                    json.dumps(v["persona"]), v["sales_objective"],
                    json.dumps(v["customer_profile"]), json.dumps(v["sales_workflow"]),
                    json.dumps(v["knowledge_config"]), json.dumps(v["tool_permissions"]),
                    json.dumps(v["model_config"]), v["status"]
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


# ── Agent Persona & Version Control Data Layer ──

def _format_version_dict(row: Any) -> Dict[str, Any]:
    """Helper to deserialize JSON text fields into Python dicts/lists."""
    item = dict(row)
    for field in ["persona", "customer_profile", "sales_workflow", "knowledge_config", "tool_permissions", "model_config"]:
        val = item.get(field)
        if isinstance(val, str):
            try:
                item[field] = json.loads(val)
            except Exception:
                item[field] = {} if field != "tool_permissions" else []
    return item


async def list_agents(owner_id: str = "default_org") -> List[Dict[str, Any]]:
    """Lists all configured sales agents."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM sales_agents WHERE owner_id = ? ORDER BY created_at ASC",
            (owner_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_agent_by_id(agent_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an agent and its currently active version."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM sales_agents WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        agent = dict(row)
        if agent.get("active_version_id"):
            v_cursor = await conn.execute("SELECT * FROM sales_agent_versions WHERE id = ?", (agent["active_version_id"],))
            v_row = await v_cursor.fetchone()
            if v_row:
                agent["active_version"] = _format_version_dict(v_row)
        return agent


async def create_agent(name: str, description: str = "", owner_id: str = "default_org") -> Dict[str, Any]:
    """Creates a new sales agent root record."""
    agent_id = f"agent-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    async with get_db_connection() as conn:
        await conn.execute("""
        INSERT INTO sales_agents (id, owner_id, name, description, active_version_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, NULL, ?, ?)
        """, (agent_id, owner_id, name, description, now, now))
        await conn.commit()
    return {"id": agent_id, "name": name, "description": description, "owner_id": owner_id}


async def list_agent_versions(agent_id: str) -> List[Dict[str, Any]]:
    """Lists all versions belonging to a sales agent in descending order."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM sales_agent_versions WHERE agent_id = ? ORDER BY version_number DESC",
            (agent_id,)
        )
        rows = await cursor.fetchall()
        return [_format_version_dict(r) for r in rows]


async def get_agent_version(version_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single version with deserialized configuration fields."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM sales_agent_versions WHERE id = ?", (version_id,))
        row = await cursor.fetchone()
        return _format_version_dict(row) if row else None


async def get_active_agent_version(agent_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns the currently active live version for an agent or fallback active version."""
    async with get_db_connection() as conn:
        if agent_id:
            cursor = await conn.execute("""
            SELECT v.* FROM sales_agent_versions v
            JOIN sales_agents a ON a.active_version_id = v.id
            WHERE a.id = ?
            """, (agent_id,))
        else:
            cursor = await conn.execute("""
            SELECT * FROM sales_agent_versions WHERE status = 'active' ORDER BY updated_at DESC LIMIT 1
            """)
        row = await cursor.fetchone()
        if not row:
            # Fallback to the highest published version if no version is marked active
            cursor = await conn.execute("SELECT * FROM sales_agent_versions ORDER BY version_number DESC LIMIT 1")
            row = await cursor.fetchone()
        return _format_version_dict(row) if row else None


async def create_agent_version(agent_id: str, data: Dict[str, Any], as_draft: bool = True) -> Dict[str, Any]:
    """Creates a new version for a sales agent with next auto-incremented version number."""
    version_id = f"ver-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()

    async with get_db_connection() as conn:
        # Determine next version number
        cursor = await conn.execute(
            "SELECT MAX(version_number) as max_v FROM sales_agent_versions WHERE agent_id = ?",
            (agent_id,)
        )
        row = await cursor.fetchone()
        next_v = (row["max_v"] or 0) + 1 if row else 1

        version_tag = data.get("version_tag") or f"v{next_v} — {data.get('persona', {}).get('role', 'Sales Persona')}"
        status = "draft" if as_draft else data.get("status", "draft")

        await conn.execute("""
        INSERT INTO sales_agent_versions (
            id, agent_id, version_number, version_tag, system_prompt, persona,
            sales_objective, customer_profile, sales_workflow, knowledge_config,
            tool_permissions, model_config, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            version_id, agent_id, next_v, version_tag,
            data.get("system_prompt"),
            json.dumps(data.get("persona", {})),
            data.get("sales_objective", "Drive qualified meetings and product sales conversions"),
            json.dumps(data.get("customer_profile", {})),
            json.dumps(data.get("sales_workflow", {})),
            json.dumps(data.get("knowledge_config", {})),
            json.dumps(data.get("tool_permissions", ["schedule_demo", "check_pricing_tier", "record_objection", "end_call"])),
            json.dumps(data.get("model_config", {"provider": "google", "model_name": "gemini-2.0-flash", "temperature": 0.3})),
            status, now, now
        ))
        await conn.commit()

    return await get_agent_version(version_id)


async def update_agent_version(version_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates a version configuration.
    Enforces immutability: published and active versions cannot be mutated directly!
    """
    existing = await get_agent_version(version_id)
    if not existing:
        raise ValueError("Version not found")

    if existing["status"] in ("published", "active"):
        raise ValueError("Immutable version: Published or Active versions cannot be edited directly. Create a new draft or duplicate this version to make changes.")

    now = datetime.utcnow().isoformat()
    version_tag = data.get("version_tag", existing["version_tag"])
    system_prompt = data.get("system_prompt", existing.get("system_prompt"))
    persona = json.dumps(data.get("persona", existing.get("persona", {})))
    sales_objective = data.get("sales_objective", existing.get("sales_objective", ""))
    customer_profile = json.dumps(data.get("customer_profile", existing.get("customer_profile", {})))
    sales_workflow = json.dumps(data.get("sales_workflow", existing.get("sales_workflow", {})))
    knowledge_config = json.dumps(data.get("knowledge_config", existing.get("knowledge_config", {})))
    tool_permissions = json.dumps(data.get("tool_permissions", existing.get("tool_permissions", [])))
    model_config = json.dumps(data.get("model_config", existing.get("model_config", {})))

    async with get_db_connection() as conn:
        await conn.execute("""
        UPDATE sales_agent_versions
        SET version_tag = ?, system_prompt = ?, persona = ?, sales_objective = ?,
            customer_profile = ?, sales_workflow = ?, knowledge_config = ?,
            tool_permissions = ?, model_config = ?, updated_at = ?
        WHERE id = ?
        """, (
            version_tag, system_prompt, persona, sales_objective,
            customer_profile, sales_workflow, knowledge_config,
            tool_permissions, model_config, now, version_id
        ))
        await conn.commit()

    return await get_agent_version(version_id)


async def publish_agent_version(version_id: str) -> Dict[str, Any]:
    """Marks a draft version as published and immutable."""
    existing = await get_agent_version(version_id)
    if not existing:
        raise ValueError("Version not found")

    now = datetime.utcnow().isoformat()
    async with get_db_connection() as conn:
        await conn.execute(
            "UPDATE sales_agent_versions SET status = 'published', updated_at = ? WHERE id = ?",
            (now, version_id)
        )
        await conn.commit()

    return await get_agent_version(version_id)


async def activate_agent_version(agent_id: str, version_id: str) -> Dict[str, Any]:
    """
    Sets the active live version for an agent.
    Updates the agent's active_version_id and marks this version as 'active'.
    Demotes the previously active version to 'published'.
    """
    target = await get_agent_version(version_id)
    if not target:
        raise ValueError("Target version not found")

    now = datetime.utcnow().isoformat()
    async with get_db_connection() as conn:
        # Demote current active version(s) for this agent to published
        await conn.execute(
            "UPDATE sales_agent_versions SET status = 'published', updated_at = ? WHERE agent_id = ? AND status = 'active'",
            (now, agent_id)
        )
        # Mark target version as active
        await conn.execute(
            "UPDATE sales_agent_versions SET status = 'active', updated_at = ? WHERE id = ?",
            (now, version_id)
        )
        # Update agent pointer
        await conn.execute(
            "UPDATE sales_agents SET active_version_id = ?, updated_at = ? WHERE id = ?",
            (version_id, now, agent_id)
        )
        await conn.commit()

    return await get_agent_version(version_id)


async def duplicate_agent_version(version_id: str, new_tag: Optional[str] = None) -> Dict[str, Any]:
    """Duplicates an existing version as a brand new draft version."""
    source = await get_agent_version(version_id)
    if not source:
        raise ValueError("Source version not found")

    payload = {
        "version_tag": new_tag or f"Copy of {source['version_tag']}",
        "system_prompt": source.get("system_prompt"),
        "persona": source.get("persona", {}),
        "sales_objective": source.get("sales_objective", ""),
        "customer_profile": source.get("customer_profile", {}),
        "sales_workflow": source.get("sales_workflow", {}),
        "knowledge_config": source.get("knowledge_config", {}),
        "tool_permissions": source.get("tool_permissions", []),
        "model_config": source.get("model_config", {})
    }
    return await create_agent_version(source["agent_id"], payload, as_draft=True)


async def rollback_agent_version(agent_id: str, target_version_id: str) -> Dict[str, Any]:
    """
    Rolls back to a previous version by creating a new draft copy of that historical configuration.
    Leaves the historical version intact and provides an editable new draft for immediate activation.
    """
    source = await get_agent_version(target_version_id)
    if not source:
        raise ValueError("Target rollback version not found")

    new_tag = f"Rollback to v{source['version_number']} ({source['version_tag']})"
    return await duplicate_agent_version(target_version_id, new_tag=new_tag)


async def delete_agent_version(agent_id: str, version_id: str) -> bool:
    """
    Permanently deletes a version.
    Safety constraint: Cannot delete the currently active live version.
    """
    target = await get_agent_version(version_id)
    if not target:
        raise ValueError("Version not found")

    if target.get("agent_id") != agent_id:
        raise ValueError("Version does not belong to this agent")

    if target.get("status") == "active":
        raise ValueError("Cannot delete the active live version. Please activate another version first.")

    async with get_db_connection() as conn:
        # Cascade clean any sessions referencing this specific version
        await conn.execute("DELETE FROM sales_sessions WHERE pinned_version_id = ?", (version_id,))
        await conn.execute("DELETE FROM sales_agent_versions WHERE id = ?", (version_id,))
        await conn.commit()

    return True


async def compare_agent_versions(version_a_id: str, version_b_id: str) -> Dict[str, Any]:
    """Computes a structured diff between any two versions."""
    va = await get_agent_version(version_a_id)
    vb = await get_agent_version(version_b_id)
    if not va or not vb:
        raise ValueError("One or both versions not found")

    diff = {}
    keys = ["version_tag", "sales_objective", "system_prompt", "persona", "customer_profile", "sales_workflow", "knowledge_config", "tool_permissions", "model_config"]
    for k in keys:
        val_a = va.get(k)
        val_b = vb.get(k)
        diff[k] = {
            "version_a": val_a,
            "version_b": val_b,
            "is_different": val_a != val_b
        }

    return {
        "version_a": {"id": va["id"], "version_number": va["version_number"], "tag": va["version_tag"], "status": va["status"]},
        "version_b": {"id": vb["id"], "version_number": vb["version_number"], "tag": vb["version_tag"], "status": vb["status"]},
        "differences": diff
    }


# ── Pinned Sessions & Event Auditing Data Layer ──

async def create_sales_session(
    agent_id: str,
    pinned_version_id: str,
    customer_name: str = "Prospect",
    customer_contact: str = "N/A",
    config_snapshot: Optional[Dict[str, Any]] = None
) -> str:
    """Creates a sales session pinned to an immutable configuration snapshot."""
    session_id = f"sess-{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow().isoformat()
    if not config_snapshot:
        v = await get_agent_version(pinned_version_id)
        config_snapshot = v or {}

    async with get_db_connection() as conn:
        await conn.execute("""
        INSERT INTO sales_sessions (
            id, agent_id, pinned_version_id, customer_name, customer_contact,
            session_status, config_snapshot, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
        """, (session_id, agent_id, pinned_version_id, customer_name, customer_contact, json.dumps(config_snapshot), now, now))
        await conn.commit()

    return session_id


async def get_sales_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves session record with pinned configuration snapshot."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM sales_sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        sess = dict(row)
        try:
            sess["config_snapshot"] = json.loads(sess["config_snapshot"])
        except Exception:
            pass
        return sess


async def record_sales_event(session_id: str, event_type: str, metadata: Dict[str, Any]) -> str:
    """Appends an audit event to a sales session."""
    event_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    async with get_db_connection() as conn:
        await conn.execute("""
        INSERT INTO sales_events (id, session_id, event_type, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """, (event_id, session_id, event_type, json.dumps(metadata), now))
        await conn.commit()
    return event_id


async def list_sales_events(session_id: str) -> List[Dict[str, Any]]:
    """Lists audit events for a session."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM sales_events WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            item = dict(r)
            try:
                item["metadata_json"] = json.loads(item["metadata_json"])
            except Exception:
                pass
            result.append(item)
        return result


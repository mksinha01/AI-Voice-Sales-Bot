"""
tests/test_versioning.py
Unit and integration tests for Sales Agent Persona Version Control System.
"""

import pytest
import asyncio
import os
import json

# Setup test DB environment before importing app modules
os.environ["DATABASE_PATH"] = "data/test_sales_bot.db"
os.environ["ENVIRONMENT"] = "testing"

from app.db import (
    init_db,
    list_agents,
    get_agent_by_id,
    create_agent,
    list_agent_versions,
    get_agent_version,
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
)
from app.tools import get_tools_for_permissions, list_registered_tools
from app.prompts import compile_agent_system_prompt, generate_agent_config_from_prompt


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    asyncio.run(init_db())
    yield
    # Cleanup test db
    test_db = "data/test_sales_bot.db"
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_seed_agent_and_versions():
    """Verify default agent and 5 seed versions are initialized."""
    agents = await list_agents()
    assert len(agents) >= 1
    default_agent = agents[0]
    assert default_agent["name"] == "Alex Closer — Enterprise Sales Suite"
    assert default_agent["active_version_id"] is not None

    versions = await list_agent_versions(default_agent["id"])
    assert len(versions) >= 5
    version_tags = [v["version_tag"] for v in versions]
    assert any("Lead Qualification" in t for t in version_tags)
    assert any("Product Sales Closer" in t for t in version_tags)
    assert any("Appointment Booking" in t for t in version_tags)
    assert any("Customer Follow-up" in t for t in version_tags)
    assert any("Custom Enterprise" in t for t in version_tags)


@pytest.mark.asyncio
async def test_draft_version_lifecycle():
    """Verify creating, editing, and publishing a draft version."""
    agents = await list_agents()
    agent_id = agents[0]["id"]

    # 1. Create a draft version
    draft_payload = {
        "version_tag": "v6 — Test Cold Outbound Closer",
        "sales_objective": "Test objective: schedule enterprise walkthroughs",
        "persona": {
            "name": "Sarah Connor",
            "role": "Cybersecurity Sales Specialist",
            "tone": "Direct, authoritative, high-energy",
            "language": "en-US"
        },
        "customer_profile": {
            "icp": "CISOs and Security Directors",
            "pain_points": "Ransomware threats and compliance audits"
        },
        "sales_workflow": {
            "stages": ["Greeting", "Urgency Hook", "Pitch", "Close"],
            "qualification_questions": ["What is your current endpoint security solution?"],
            "closing_strategy": "Book a 15-minute vulnerability assessment"
        },
        "knowledge_config": {
            "products": ["Securify Vault Enterprise"],
            "pricing_monthly": 199,
            "pricing_annual": 159
        },
        "tool_permissions": ["schedule_demo", "check_pricing_tier", "end_call"]
    }

    new_ver = await create_agent_version(agent_id, draft_payload, as_draft=True)
    assert new_ver["status"] == "draft"
    assert new_ver["persona"]["name"] == "Sarah Connor"
    version_id = new_ver["id"]

    # 2. Update the draft
    update_payload = {
        "sales_objective": "Updated objective: test draft mutations",
        "persona": {
            "name": "Sarah Connor",
            "role": "Chief Revenue Closer",
            "tone": "Hyper-consultative",
            "language": "en-US"
        }
    }
    updated = await update_agent_version(version_id, update_payload)
    assert updated["sales_objective"] == "Updated objective: test draft mutations"
    assert updated["persona"]["role"] == "Chief Revenue Closer"

    # 3. Publish the version
    published = await publish_agent_version(version_id)
    assert published["status"] == "published"

    # 4. Immutability enforcement: editing a published version MUST fail
    with pytest.raises(ValueError, match="Immutable version"):
        await update_agent_version(version_id, {"sales_objective": "Should fail"})


@pytest.mark.asyncio
async def test_activate_version():
    """Verify activating a version updates agent pointer and demotes previous active."""
    agents = await list_agents()
    agent_id = agents[0]["id"]
    versions = await list_agent_versions(agent_id)

    # Pick a published version (v1)
    v1 = next(v for v in versions if v["version_number"] == 1)
    activated_v1 = await activate_agent_version(agent_id, v1["id"])
    assert activated_v1["status"] == "active"

    # Check agent's active version is updated
    refreshed_agent = await get_agent_by_id(agent_id)
    assert refreshed_agent["active_version_id"] == v1["id"]

    # Re-activate v2
    v2 = next(v for v in versions if v["version_number"] == 2)
    activated_v2 = await activate_agent_version(agent_id, v2["id"])
    assert activated_v2["status"] == "active"

    # Verify previous v1 is now published (not active)
    refreshed_v1 = await get_agent_version(v1["id"])
    assert refreshed_v1["status"] == "published"


@pytest.mark.asyncio
async def test_compare_versions():
    """Verify comparing two versions returns structured diff."""
    agents = await list_agents()
    agent_id = agents[0]["id"]
    versions = await list_agent_versions(agent_id)

    v1 = next(v for v in versions if v["version_number"] == 1)
    v2 = next(v for v in versions if v["version_number"] == 2)

    diff = await compare_agent_versions(v1["id"], v2["id"])
    assert "version_a" in diff
    assert "version_b" in diff
    assert "differences" in diff
    assert diff["differences"]["sales_objective"]["is_different"] is True


@pytest.mark.asyncio
async def test_duplicate_and_rollback():
    """Verify duplicating and rolling back creates clean new editable drafts."""
    agents = await list_agents()
    agent_id = agents[0]["id"]
    versions = await list_agent_versions(agent_id)
    v1 = next(v for v in versions if v["version_number"] == 1)

    # Duplicate
    dupe = await duplicate_agent_version(v1["id"])
    assert dupe["status"] == "draft"
    assert dupe["version_number"] > v1["version_number"]
    assert "Copy of" in dupe["version_tag"]

    # Rollback
    rollback = await rollback_agent_version(agent_id, v1["id"])
    assert rollback["status"] == "draft"
    assert "Rollback to v1" in rollback["version_tag"]


@pytest.mark.asyncio
async def test_tool_permissions_filtering():
    """Verify get_tools_for_permissions dynamically restricts available LLM tools."""
    # Empty permissions should at least retain end_call for safety
    minimal_tools = get_tools_for_permissions([])
    assert len(minimal_tools) == 1
    assert any("end_call" in t.info.name for t in minimal_tools)

    # Specific permissions
    allowed = ["schedule_demo", "check_pricing_tier"]
    active = get_tools_for_permissions(allowed)
    tool_names = [t.info.name for t in active]
    assert "schedule_demo" in tool_names
    assert "check_pricing_tier" in tool_names
    # Unpermitted tool should NOT be present
    assert "create_sales_opportunity" not in tool_names
    assert "escalate_human_handoff" not in tool_names


@pytest.mark.asyncio
async def test_compile_agent_system_prompt():
    """Verify compile_agent_system_prompt composes all required sections."""
    sample_ver = {
        "persona": {
            "name": "Marcus Vance",
            "role": "Strategic AE",
            "tone": "Warm, consultative",
            "language": "en-US"
        },
        "sales_objective": "Lock in 20-min calendar demos",
        "customer_profile": {
            "icp": "VP of Revenue",
            "pain_points": "Rep turnover and missed quota"
        },
        "knowledge_config": {
            "products": ["DevFlow Pro"],
            "pricing_monthly": 89,
            "pricing_annual": 69,
            "approved_offers": ["15% inaugural discount"]
        },
        "sales_workflow": {
            "stages": ["Greeting", "Discover", "Pitch", "Close"],
            "qualification_questions": ["What is your dev team size?"],
            "closing_strategy": "Ask for Thursday 10am demo",
            "escalation_rules": "Escalate if custom API SLA is demanded"
        },
        "tool_permissions": ["schedule_demo", "check_pricing_tier", "end_call"]
    }

    prompt = compile_agent_system_prompt(sample_ver)
    assert "Marcus Vance" in prompt
    assert "Strategic AE" in prompt
    assert "Lock in 20-min calendar demos" in prompt
    assert "DevFlow Pro" in prompt
    assert "$69/user/month" in prompt
    assert "NEVER invent or hallucinate unauthorized discounts" in prompt
    assert "end_call" in prompt


@pytest.mark.asyncio
async def test_session_pinning_and_events():
    """Verify a sales session is pinned to an immutable version snapshot."""
    agents = await list_agents()
    agent_id = agents[0]["id"]
    versions = await list_agent_versions(agent_id)
    v2 = next(v for v in versions if v["version_number"] == 2)

    sess_id = await create_sales_session(
        agent_id=agent_id,
        pinned_version_id=v2["id"],
        customer_name="John Doe",
        customer_contact="john@example.com",
        config_snapshot=v2
    )

    sess = await get_sales_session(sess_id)
    assert sess is not None
    assert sess["agent_id"] == agent_id
    assert sess["pinned_version_id"] == v2["id"]
    assert sess["customer_name"] == "John Doe"
    assert sess["config_snapshot"]["version_tag"] == v2["version_tag"]


@pytest.mark.asyncio
async def test_delete_version():
    """Verify draft versions can be deleted, while active live versions cannot."""
    agents = await list_agents()
    agent_id = agents[0]["id"]

    # 1. Create a draft version
    draft = await create_agent_version(agent_id, {
        "version_tag": "Temporary Test Draft",
        "system_prompt": "Temporary prompt",
        "persona": {"name": "Test Temp"},
        "sales_objective": "Test temporary deletion",
        "customer_profile": {},
        "sales_workflow": {},
        "knowledge_config": {},
        "tool_permissions": ["end_call"],
        "model_config": {}
    }, as_draft=True)

    draft_id = draft["id"]
    assert await get_agent_version(draft_id) is not None

    # 2. Deleting draft version succeeds
    deleted = await delete_agent_version(agent_id, draft_id)
    assert deleted is True
    assert await get_agent_version(draft_id) is None

    # 3. Deleting active live version must raise ValueError
    active_ver = await list_agent_versions(agent_id)
    live_v = next(v for v in active_ver if v["status"] == "active")
    with pytest.raises(ValueError, match="Cannot delete the active live version"):
        await delete_agent_version(agent_id, live_v["id"])


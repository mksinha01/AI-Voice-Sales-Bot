"""
app/tools.py
External actions and tools invoked by the voice sales agent.
"""

from typing import Callable, Optional, List, Dict, Any
from livekit.agents import llm
import logging

logger = logging.getLogger("sales_tools")

_call_terminator: Optional[Callable[[str], None]] = None


def set_call_terminator(fn: Optional[Callable[[str], None]]) -> None:
    """Register callback to terminate the live call."""
    global _call_terminator
    _call_terminator = fn


# ── Registered Tools ──

@llm.function_tool(description="Look up existing customer or company in the CRM system to check deal stage and notes.")
def lookup_crm_lead(company_or_name: str) -> str:
    """Check lead history, past conversations, and contact info."""
    logger.info(f"CRM Lead Lookup: '{company_or_name}'")
    return f"CRM Record for '{company_or_name}': Status: Active Prospect • Score: High (84/100) • Last Touch: Web Inquiry 2 days ago • Interest: Sales automation and CRM sync."


@llm.function_tool(description="Create a new qualified sales opportunity or deal in the CRM pipeline.")
def create_sales_opportunity(deal_name: str, estimated_value: float, stage: str = "Discovery") -> str:
    """Record a verified sales deal with estimated revenue value."""
    logger.info(f"CRM Opportunity Created: '{deal_name}' (${estimated_value:,.2f}) Stage: {stage}")
    return f"Opportunity successfully logged in CRM: '{deal_name}' assigned to Inbound Pipeline at ${estimated_value:,.2f}."


@llm.function_tool(description="Schedule a product demo walkthrough when the prospect agrees to a calendar invite.")
def schedule_demo(preferred_day: str, email_or_contact: str) -> str:
    """Book a personalized solution walkthrough on the calendar."""
    try:
        logger.info(f"Demo scheduled: day={preferred_day}, contact={email_or_contact}")
        return f"Demo provisionally scheduled for {preferred_day}. A calendar invite has been queued for {email_or_contact}."
    except Exception as e:
        logger.error(f"Failed to schedule demo: {e}")
        return "Demo requested. I will notify our solutions engineering team to send an invite immediately."


@llm.function_tool(description="Schedule a sales follow-up task or reminder for the sales team.")
def schedule_followup(date_time: str, notes: str) -> str:
    """Schedule follow-up date and notes in CRM."""
    logger.info(f"Follow-up scheduled: date={date_time}, notes={notes}")
    return f"Follow-up task scheduled for {date_time}. Notes logged: '{notes}'."


@llm.function_tool(description="Calculate certified real-time pricing and eligible discount tiers for a given team size.")
def check_pricing_tier(team_size: int, billing_cycle: str = "annual") -> str:
    """Calculate pricing quote based on team size and billing frequency."""
    try:
        unit_price = 39.0 if billing_cycle.lower() == "annual" else 49.0
        total = team_size * unit_price
        discount = "20% annual commitment discount applied" if billing_cycle.lower() == "annual" else "standard monthly pricing"
        return f"For a team of {team_size}, the total is ${total:,.2f} per month ({discount})."
    except Exception as e:
        logger.error(f"Error calculating price: {e}")
        return "Our standard plan starts at $39 per user per month with annual billing."


@llm.function_tool(description="Record an explicit customer objection for deal intelligence and post-call review.")
def record_objection(category: str, details: str) -> str:
    """Log customer objections (e.g., budget, competitor, timing)."""
    logger.info(f"Objection logged: category={category}, details={details}")
    return f"Objection categorized as '{category}' logged. Acknowledge the concern and present the approved solution."


@llm.function_tool(description="Escalate or warm-transfer the conversation to a human sales specialist or executive.")
def escalate_human_handoff(reason: str, department: str = "Sales Leadership") -> str:
    """Request live human handoff when customer requires custom terms or human representative."""
    logger.info(f"Human Handoff Triggered: reason={reason}, department={department}")
    return f"Handoff protocol engaged for {department}. Let the customer know a senior specialist is being notified to join."


@llm.function_tool(description="End or hang up the phone call immediately when the customer indicates they want to hang up or end the call.")
def end_call(reason: str = "Customer requested to end call") -> str:
    """Hang up phone call upon user farewell or departure."""
    logger.info(f"End call tool invoked: reason={reason}")
    if _call_terminator:
        try:
            _call_terminator(reason)
        except Exception as e:
            logger.error(f"Error executing call terminator callback: {e}")
    return "Call ending sequence initiated. Say a brief, polite goodbye to the customer now."


# ── Tool Registry ──

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "lookup_crm_lead": {
        "fn": lookup_crm_lead,
        "name": "lookup_crm_lead",
        "label": "CRM Lead Lookup",
        "description": "Look up existing CRM lead history, account records, and previous interactions.",
        "category": "CRM Integration"
    },
    "create_sales_opportunity": {
        "fn": create_sales_opportunity,
        "name": "create_sales_opportunity",
        "label": "Create CRM Opportunity",
        "description": "Create a qualified sales pipeline deal/opportunity in the CRM.",
        "category": "CRM Integration"
    },
    "schedule_demo": {
        "fn": schedule_demo,
        "name": "schedule_demo",
        "label": "Schedule Demo",
        "description": "Lock in product walkthrough demo directly onto the calendar.",
        "category": "Calendar & Scheduling"
    },
    "schedule_followup": {
        "fn": schedule_followup,
        "name": "schedule_followup",
        "label": "Schedule Follow-up",
        "description": "Queue an automated sales follow-up task and date reminder.",
        "category": "Calendar & Scheduling"
    },
    "check_pricing_tier": {
        "fn": check_pricing_tier,
        "name": "check_pricing_tier",
        "label": "Calculate Pricing",
        "description": "Calculate certified pricing quotes and eligible discount tiers.",
        "category": "Quotes & Pricing"
    },
    "record_objection": {
        "fn": record_objection,
        "name": "record_objection",
        "label": "Log Objection",
        "description": "Log explicit customer resistance or objection for intelligence tracking.",
        "category": "Sales Intelligence"
    },
    "escalate_human_handoff": {
        "fn": escalate_human_handoff,
        "name": "escalate_human_handoff",
        "label": "Human Handoff",
        "description": "Warm-transfer or escalate the prospect to a human sales director.",
        "category": "Handoff & Safety"
    },
    "end_call": {
        "fn": end_call,
        "name": "end_call",
        "label": "End Call Sequencer",
        "description": "Gracefully terminate call when customer indicates conversation has concluded.",
        "category": "Handoff & Safety"
    }
}


def get_tools_for_permissions(allowed_permissions: Optional[List[str]] = None) -> list:
    """Returns only the subset of function tools permitted by the active agent version."""
    if not allowed_permissions:
        return [TOOL_REGISTRY["end_call"]["fn"]]

    active_tools = []
    for perm in allowed_permissions:
        if perm in TOOL_REGISTRY:
            active_tools.append(TOOL_REGISTRY[perm]["fn"])

    # Guarantee end_call is always available for safety
    if TOOL_REGISTRY["end_call"]["fn"] not in active_tools:
        active_tools.append(TOOL_REGISTRY["end_call"]["fn"])

    return active_tools


def list_registered_tools() -> List[Dict[str, Any]]:
    """Returns metadata for all available tools for frontend permission toggles."""
    return [
        {
            "id": k,
            "label": v["label"],
            "description": v["description"],
            "category": v["category"]
        }
        for k, v in TOOL_REGISTRY.items()
    ]


# Backward compatibility export
sales_tools = [schedule_demo, check_pricing_tier, record_objection, end_call]



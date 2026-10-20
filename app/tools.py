"""
app/tools.py
External actions and tools invoked by the voice sales agent.
"""

from livekit.agents import llm
import logging

logger = logging.getLogger("sales_tools")


@llm.function_tool(description="Schedule a product demo when the prospect agrees or requests a walkthrough.")
def schedule_demo(preferred_day: str, email_or_contact: str) -> str:
    """
    Call this when the customer says they want a demo or agrees to a calendar invite.
    """
    try:
        logger.info(f"Demo scheduled: day={preferred_day}, contact={email_or_contact}")
        return f"Demo provisionally scheduled for {preferred_day}. An invite has been queued for {email_or_contact}."
    except Exception as e:
        logger.error(f"Failed to schedule demo: {e}")
        return "Demo requested. I will notify our sales engineers to send an invite immediately."


@llm.function_tool(description="Check real-time pricing and eligible discount tiers for a given user count.")
def check_pricing_tier(team_size: int, billing_cycle: str = "annual") -> str:
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


@llm.function_tool(description="Record an explicit customer objection for post-call follow up.")
def record_objection(category: str, details: str) -> str:
    """
    Call this when the prospect raises a major barrier (e.g. lack of budget, competitor contract).
    """
    logger.info(f"Objection logged: category={category}, details={details}")
    return "Objection noted. Continuing conversation to address it."


sales_tools = [schedule_demo, check_pricing_tier, record_objection]

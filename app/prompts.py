"""
app/prompts.py
SaaS sales playbooks, personality definitions, and prompt generation functions.
"""

from typing import Dict, Any, Optional

# Preset SaaS Catalog
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
    },
    "DevFlow AI": {
        "tagline": "Autonomous Pull Request Review & Zero-Flaky Test Engine",
        "description": "Accelerates developer velocity by auto-reviewing PRs, synthesizing integration tests, and catching breaking API changes before production.",
        "pricing_monthly": 79.0,
        "pricing_annual": 59.0,
        "key_features": [
            "Automated GitHub & GitLab PR code review bots",
            "Flaky test self-healing and instant root-cause logs",
            "Security vulnerability linting and auto-fix pull requests"
        ],
        "target_audience": "Software engineering teams, DevOps managers, and tech leads.",
        "objections": {
            "too_expensive": "Catching one production outage pays for 5 years of DevFlow AI.",
            "security_concerns": "We operate with zero-data-retention and run entirely in your VPC if requested."
        }
    },
    "LeadPulse AI": {
        "tagline": "Autonomous Outbound Voice & Multi-Channel Sales Prospecting Agent",
        "description": "LeadPulse AI automatically discovers B2B buyer intent, dials verified prospects with human-parity voice, qualifies leads, and books qualified demos straight into your AE calendar.",
        "pricing_monthly": 89.0,
        "pricing_annual": 69.0,
        "key_features": [
            "Autonomous multi-lingual outbound & inbound sales voice calling",
            "Real-time CRM sync with automated objection handling and live transcripts",
            "Smart calendar scheduling with Google Meet & Outlook integration",
            "99.4% intent recognition accuracy with zero robotic latency"
        ],
        "target_audience": "B2B SaaS companies, SDR teams, agencies, and high-velocity sales organizations.",
        "objections": {
            "too_expensive": "At $69/month, booking just one qualified meeting pays for 6 months of LeadPulse AI. It replaces an entire $4,000/month SDR headcount.",
            "will_prospects_know_its_ai": "LeadPulse speaks with natural cadence, sub-second latency, and emotional intelligence so customers feel respected and understood.",
            "want_to_try_first": "Absolutely! I can set up a 14-day zero-risk trial or book a 15-minute live walkthrough right now."
        }
    }
}


def build_initial_sales_greeting(
    product_name: str,
    language: str = "en-US",
    product_data: Optional[Dict[str, Any]] = None,
    customer_name: str = "there",
    disclose_consent: bool = False
) -> str:
    """
    Builds a real, high-converting B2B SaaS sales opening pitch without any test/demonstration wording.
    Immediately hooks the prospect on core value and asks a discovery question.
    """
    product = product_data or PRODUCT_CATALOG.get(product_name, PRODUCT_CATALOG.get("CloudScale CRM", {}))
    consent_prefix = "Quick note, our call is recorded for quality assurance. " if disclose_consent else ""
    first_name = customer_name.strip() if customer_name and customer_name != "Prospect" and customer_name != "Valued Customer" else "there"

    if language == "hi-IN":
        return f"Namaste {first_name}! Main Alex bol raha hoon {product_name} se. {consent_prefix}Hum modern businesses ko AI automation provide karte hain taaki aapka sales pipeline aur revenue expand ho sake. Aapki team currently sales outreach aur lead generation ko kaise manage kar rahi hai?"
    elif language == "te-IN":
        return f"Namaskaram {first_name}! Nenu Alex, {product_name} sales team nunchi. {consent_prefix}Mee business workflow automate chesi revenue penchadaniki maa platform chala baaga use avthundi. Mee team ippudu sales pipeline ni ela handle chestondi?"

    # Product-specific value hooks
    taglines = {
        "LeadPulse AI": "We help B2B sales teams automate outbound prospecting and book 3 times more qualified demos straight into your calendar.",
        "CloudScale CRM": "We help fast-growing teams automate pipeline forecasting and eliminate manual CRM data entry for reps.",
        "Securify Vault": "We help cloud and SaaS companies automate continuous SOC2 and HIPAA compliance audits in under 10 minutes.",
        "DevFlow AI": "We help engineering teams auto-review pull requests and eliminate flaky tests before production."
    }
    hook = taglines.get(product_name, product.get("tagline", "We help modern teams automate mission-critical workflows and accelerate revenue growth."))

    return f"Hello {first_name}! My name is Alex, and I am calling from {product_name}. {consent_prefix}{hook} How is your team currently approaching this in your business?"


def build_sales_system_prompt(
    product_name: str = "CloudScale CRM",
    language: str = "en-US",
    custom_system_prompt: Optional[str] = None,
    custom_product_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Constructs the operational sales agent system prompt based on product and target language.
    If custom_system_prompt is provided from the UI Customizer Studio, it takes highest precedence.
    """
    # 1. Custom Prompt Override from UI Customizer Studio
    if custom_system_prompt and custom_system_prompt.strip():
        return custom_system_prompt.strip()

    # 2. Dynamic or Catalog Product Resolution
    product = custom_product_data or PRODUCT_CATALOG.get(product_name, PRODUCT_CATALOG.get("CloudScale CRM", {}))

    language_instructions = {
        "en-US": "Speak in natural, enthusiastic, professional American or International English.",
        "hi-IN": "Speak in conversational Hindi or natural Hinglish (Hindi mixed with common English business terms). Be courteous and polite (use 'Aap', 'Ji').",
        "te-IN": "Speak in polite, engaging Telugu mixed naturally with standard English tech terms.",
    }.get(language, "Speak in natural, professional English.")

    features = product.get("key_features", [])
    features_str = ", ".join(features) if isinstance(features, list) else str(features)

    prompt = f"""You are Alex, an elite, persuasive, and empathetic B2B SaaS Account Executive at {product_name}.
You are in a live voice phone call with a prospect. You are NOT a demonstration bot, student project, or test script. You are a real software sales professional whose goal is to uncover their pain points, demonstrate why {product_name} is the best solution on the market, handle objections, and close them on scheduling a demo or starting a subscription.

Language Directive:
{language_instructions}

Product Knowledge:
- Product Name: {product_name}
- Tagline: {product.get('tagline', 'Modern Cloud Automation')}
- Overview: {product.get('description', '')}
- Pricing: ${product.get('pricing_annual', 39)}/user/month (annual billing - 20% discount) or ${product.get('pricing_monthly', 49)}/user/month (standard monthly billing).
- Key Capabilities: {features_str}
- Target Customer: {product.get('target_audience', 'Businesses & teams seeking efficiency')}

Core Selling Rules:
1. Act like a top 1% SaaS Account Executive. Speak naturally, confidently, and warmly.
2. Keep your turns CONCISE (1 to 3 short sentences max). Never monologue or overwhelm the customer. Real phone calls are dynamic, back-and-forth dialogue.
3. When the customer mentions team size or asks about price, quote the exact pricing tier or invoke the check_pricing_tier tool.
4. When the customer raises an objection (price, competitor, timing), acknowledge it with empathy, re-frame the value and ROI, and invoke record_objection.
5. When the customer shows interest or agrees to a meeting, lock in a date/time and invoke schedule_demo.
6. Always steer the conversation toward closing: "Would this Thursday at 2 PM work for a quick 15-minute walkthrough for your team?"
7. Never use markdown, bullet points, asterisks, or robotic phrases. Never say "As an AI" or "In this demonstration". You are Alex from {product_name}.
"""
    return prompt.strip()

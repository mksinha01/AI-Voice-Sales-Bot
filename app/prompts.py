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

    # Product-specific value hooks
    taglines = {
        "LeadPulse AI": "We help B2B sales teams automate outbound prospecting and book 3 times more qualified demos straight into your calendar.",
        "CloudScale CRM": "We help fast-growing teams automate pipeline forecasting and eliminate manual CRM data entry for reps.",
        "Securify Vault": "We help cloud and SaaS companies automate continuous SOC2 and HIPAA compliance audits in under 10 minutes.",
        "DevFlow AI": "We help engineering teams auto-review pull requests and eliminate flaky tests before production."
    }
    hook = taglines.get(product_name, product.get("tagline", "We help modern teams automate mission-critical workflows and accelerate revenue growth."))

    if language == "auto":
        return f"Hello {first_name}! My name is Alex, and I am calling from {product_name}. {consent_prefix}{hook} How is your team currently approaching this in your business? You can speak with me in English, Hindi, or Telugu."
    elif language == "hi-IN":
        return f"Namaste {first_name}! Main Alex bol raha hoon {product_name} se. {consent_prefix}Hum modern businesses ko AI automation provide karte hain taaki aapka sales pipeline aur revenue expand ho sake. Aapki team currently sales outreach aur lead generation ko kaise manage kar rahi hai?"
    elif language == "te-IN":
        return f"Namaskaram {first_name}! Nenu Alex, {product_name} sales team nunchi. {consent_prefix}Mee business workflow automate chesi revenue penchadaniki maa platform chala baaga use avthundi. Mee team ippudu sales pipeline ni ela handle chestondi?"

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
        p = custom_system_prompt.strip()
        if "end_call" not in p:
            p += (
                "\n\nCall Termination Directive:"
                "\nWhen the customer says goodbye, asks to hang up, or wants to end the call (e.g. 'bye', 'goodbye', 'end call', 'hang up', 'cut the call', 'have to go'), immediately invoke the end_call tool and say a brief polite farewell."
            )
        return p

    # 2. Dynamic or Catalog Product Resolution
    product = custom_product_data or PRODUCT_CATALOG.get(product_name, PRODUCT_CATALOG.get("CloudScale CRM", {}))

    language_instructions = {
        "auto": (
            "CRITICAL MULTILINGUAL AUTO-DETECT DIRECTIVE:\n"
            "You are fluent in English, Hindi (and Hinglish), and Telugu.\n"
            "- Automatically detect the language used by the customer in each utterance (English, Hindi, or Telugu).\n"
            "- ALWAYS respond in the exact same language the customer speaks:\n"
            "  * If the customer speaks English -> Respond in natural, professional English.\n"
            "  * If the customer speaks Hindi or Hinglish -> Respond in natural, conversational Hindi or Hinglish (courteous with 'Aap', 'Ji').\n"
            "  * If the customer speaks Telugu -> Respond in polite, natural Telugu (mixed naturally with standard English tech terms).\n"
            "- Seamless Language Switching: If the customer switches languages mid-call (e.g., switches between English, Hindi, and Telugu), immediately switch your response language to match them without comment.\n"
            "- Never ask the customer to pick a language; detect and adapt autonomously."
        ),
        "en-US": "Speak in natural, enthusiastic, professional American or International English.",
        "hi-IN": "Speak in conversational Hindi or natural Hinglish (Hindi mixed with common English business terms). Be courteous and polite (use 'Aap', 'Ji').",
        "te-IN": "Speak in polite, engaging Telugu mixed naturally with standard English tech terms.",
    }.get(language, (
        "CRITICAL MULTILINGUAL AUTO-DETECT DIRECTIVE:\n"
        "Detect whether the customer speaks English, Hindi, or Telugu, and respond in that exact language."
    ))

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
8. When the customer indicates they want to hang up, leave, or end the call (e.g., says "bye", "goodbye", "end call", "hang up", "cut the call", "call disconnect kar do", "phone rakh do", "alvida", "call cut cheyyandi", "phone petteyandi", "have to go", "not interested, bye"), immediately invoke the end_call tool and say a polite, warm farewell in one short sentence matching the conversation's language."""
    return prompt.strip()


def compile_agent_system_prompt(version: Dict[str, Any]) -> str:
    """
    Compiles an immutable runtime system prompt from a Sales Agent Version configuration snapshot.
    Combines persona, ICP, knowledge base, qualification criteria, objection rules, closing strategy,
    permitted tools, and safety guardrails.
    """
    raw_prompt = version.get("system_prompt")
    if raw_prompt and raw_prompt.strip():
        p = raw_prompt.strip()
        if "end_call" not in p:
            p += (
                "\n\nCall Termination Directive:\n"
                "When the customer says goodbye or asks to end the call, invoke the end_call tool immediately."
            )
        return p

    persona = version.get("persona") or {}
    name = persona.get("name", "Alex Closer")
    role = persona.get("role", "Senior SaaS Sales Specialist")
    tone = persona.get("tone", "Consultative, persuasive, professional")
    language = persona.get("language", "en-US")
    objective = version.get("sales_objective", "Drive qualified demos and closed revenue")

    customer_profile = version.get("customer_profile") or {}
    icp = customer_profile.get("icp", "B2B Decision Makers and Revenue Leaders")
    pain_points = customer_profile.get("pain_points", "Operational inefficiency and pipeline bottlenecks")

    knowledge = version.get("knowledge_config") or {}
    products = knowledge.get("products", ["CloudScale CRM"])
    prods_str = ", ".join(products) if isinstance(products, list) else str(products)
    p_monthly = knowledge.get("pricing_monthly", 49)
    p_annual = knowledge.get("pricing_annual", 39)
    approved_offers = knowledge.get("approved_offers", ["20% annual discount applied instantly"])
    offers_str = "; ".join(approved_offers) if isinstance(approved_offers, list) else str(approved_offers)
    faqs = knowledge.get("faqs", {})
    faq_str = "\n".join([f"- Q: {q} -> A: {a}" for q, a in faqs.items()]) if isinstance(faqs, dict) else ""

    workflow = version.get("sales_workflow") or {}
    stages = workflow.get("stages", ["Greeting", "Discovery", "Value Pitch", "Objection Handling", "Closing"])
    stages_str = " -> ".join(stages) if isinstance(stages, list) else str(stages)
    qual_questions = workflow.get("qualification_questions", ["What is your current team size and pipeline volume?"])
    qual_str = "\n".join([f"- {q}" for q in qual_questions]) if isinstance(qual_questions, list) else str(qual_questions)
    closing_strategy = workflow.get("closing_strategy", "Lock in a 15-minute product demonstration")
    escalation_rules = workflow.get("escalation_rules", "Transfer to human sales leadership if requested")

    tools = version.get("tool_permissions") or ["schedule_demo", "check_pricing_tier", "record_objection", "end_call"]
    tools_str = ", ".join(tools) if isinstance(tools, list) else str(tools)

    lang_instruction = {
        "auto": "Detect whether the customer speaks English, Hindi, or Telugu, and autonomously respond in their exact language without asking.",
        "en-US": "Speak in natural, confident American or International English.",
        "hi-IN": "Speak in natural, courteous Hindi or Hinglish (use 'Aap', 'Ji').",
        "te-IN": "Speak in polite Telugu mixed naturally with standard English tech terms.",
    }.get(language, "Speak in clear, professional English.")

    faq_section = f"Approved FAQs:\n{faq_str}\n" if faq_str else ""

    compiled = f"""You are {name}, an elite {role}.
Primary Sales Objective: {objective}

Persona & Speaking Style:
- Tone: {tone}
- Language Guidance: {lang_instruction}
- Conversational Cadence: Keep each spoken turn CONCISE (1 to 3 short sentences max). Never monologue or lecture. Speak like a real human on a live phone call.

Target Customer & ICP:
- Target Customer: {icp}
- Core Pain Points: {pain_points}

Approved Knowledge & Commercials:
- Approved Solutions: {prods_str}
- Standard Pricing: ${p_annual}/user/month (annual billing) or ${p_monthly}/user/month (monthly billing).
- Approved Special Offers: {offers_str}
{faq_section}
Sales Workflow:
- Execution Flow: {stages_str}
- Core Qualification Questions:
{qual_str}
- Closing Directive: {closing_strategy}
- Escalation & Handoff Rules: {escalation_rules}

Permitted Integration Tools:
You are authorized to use the following tools: {tools_str}.
Only invoke tools that are on this authorized list.

Strict Commercial Guardrails:
1. NEVER invent or hallucinate unauthorized discounts, features, inventory, or contractual guarantees beyond what is explicitly listed above.
2. If pricing or features requested by the customer are not covered, be transparent and offer to escalate to an Account Director using escalate_human_handoff or schedule_followup.
3. When the customer confirms a meeting or walkthrough, invoke schedule_demo.
4. When the customer asks about specific seat pricing, invoke check_pricing_tier.
5. When the customer raises an objection, acknowledge it empathetically and invoke record_objection.
6. When the customer indicates they want to hang up, leave, or end the call (e.g. says 'bye', 'goodbye', 'end call', 'hang up', 'cut the call', 'have to go'), immediately invoke the end_call tool and say a polite, warm farewell in one sentence."""

    return compiled.strip()


async def generate_agent_config_from_prompt(user_instruction: str) -> Dict[str, Any]:
    """
    Uses Google Gemini (or heuristic extraction if unavailable) to translate
    a free-form natural language sales strategy into a validated Agent Version configuration.
    """
    user_instruction = (user_instruction or "").strip()
    if not user_instruction:
        raise ValueError("Instruction cannot be empty")

    prompt = f"""You are an expert AI sales agent architect.
Convert the user's natural language instructions into a production-grade, structured AI Sales Agent Version configuration JSON.

User Instructions:
"{user_instruction}"

Respond ONLY with a valid JSON object matching this schema:
{{
  "version_tag": "short name for this strategy (e.g. Inbound SaaS Closer)",
  "sales_objective": "1-2 sentences on core goal",
  "persona": {{
    "name": "Agent name (e.g. Alex Closer)",
    "role": "Title (e.g. Senior B2B Account Executive)",
    "tone": "Tone description (e.g. Assertive, consultative, energetic)",
    "language": "en-US",
    "greeting": "Opening hook line"
  }},
  "customer_profile": {{
    "icp": "Target persona and industry",
    "company_size": "e.g. 20-500 reps",
    "pain_points": "Top problems they face"
  }},
  "sales_workflow": {{
    "stages": ["Greeting", "Discovery", "Pitch", "Objection Handling", "Closing"],
    "qualification_questions": ["Question 1", "Question 2", "Question 3"],
    "closing_strategy": "Concrete closing action",
    "escalation_rules": "When to transfer to human"
  }},
  "knowledge_config": {{
    "products": ["Primary Product Name"],
    "pricing_monthly": 49,
    "pricing_annual": 39,
    "approved_offers": ["Approved promotional offer"],
    "faqs": {{"Common question": "Approved answer"}}
  }},
  "tool_permissions": ["schedule_demo", "check_pricing_tier", "record_objection", "lookup_crm_lead", "create_sales_opportunity", "escalate_human_handoff", "end_call"],
  "model_config": {{
    "provider": "google",
    "model_name": "gemini-2.0-flash",
    "temperature": 0.3,
    "voice_id": "en-US-GuyNeural",
    "speech_rate": 1.0
  }}
}}
Do not include markdown or backticks."""

    from app.config import settings
    import json
    import re

    if settings.GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = await model.generate_content_async(prompt)
            clean_text = response.text.strip()
            clean_text = re.sub(r"^```json\s*", "", clean_text)
            clean_text = re.sub(r"^```\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)
            parsed = json.loads(clean_text)
            return parsed
        except Exception as e:
            import logging
            logging.getLogger("prompts").warning(f"LLM config generation failed, falling back to heuristic: {e}")

    return {
        "version_tag": f"AI Strategy — {user_instruction[:30]}",
        "sales_objective": f"Execute sales strategy: {user_instruction[:120]}",
        "persona": {
            "name": "Alex Closer",
            "role": "Strategic Sales Executive",
            "tone": "Consultative, persuasive, professional",
            "language": "en-US",
            "greeting": "Hello! Alex here. I noticed you are exploring ways to improve your sales performance. How can I help today?"
        },
        "customer_profile": {
            "icp": "High-growth B2B decision makers",
            "company_size": "20-500 employees",
            "pain_points": user_instruction[:160]
        },
        "sales_workflow": {
            "stages": ["Greeting", "Discovery", "Value Pitch", "Objection Handling", "Closing Demo"],
            "qualification_questions": [
                "What is your current team size and pipeline volume?",
                "What timeline are you looking at to implement a solution?",
                "Who besides yourself evaluates this decision?"
            ],
            "closing_strategy": "Secure provisional 15-minute walkthrough demo with solutions engineer",
            "escalation_rules": "Transfer to human sales leadership if custom enterprise terms are requested"
        },
        "knowledge_config": {
            "products": ["CloudScale CRM Enterprise"],
            "pricing_monthly": 49,
            "pricing_annual": 39,
            "approved_offers": ["20% annual discount applied instantly"],
            "faqs": {
                "How fast can we onboard?": "Complete onboarding in under 48 hours with full data migration."
            }
        },
        "tool_permissions": ["schedule_demo", "check_pricing_tier", "record_objection", "lookup_crm_lead", "create_sales_opportunity", "end_call"],
        "model_config": {
            "provider": "google",
            "model_name": "gemini-2.0-flash",
            "temperature": 0.3,
            "voice_id": "en-US-GuyNeural",
            "speech_rate": 1.0
        }
    }


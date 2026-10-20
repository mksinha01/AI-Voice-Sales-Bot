"""
app/chains.py
LangChain + Google Gemini structured extraction for post-call analytics.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings


class CallAnalysisSchema(BaseModel):
    sales_status: Literal[
        "Converted",
        "Interested",
        "Follow-up Required",
        "Not Interested",
        "Demo Requested",
        "No Response"
    ] = Field(description="Strict classification of the customer sales outcome.")
    summary: str = Field(description="2-3 sentence executive summary of the conversation.")
    customer_requirements: str = Field(description="Key pain points, desired features, or requirements mentioned by customer.")
    objections: str = Field(description="Any objections, hesitations, or blockers raised by the customer.")
    next_steps: str = Field(description="Recommended next actions for the sales team.")


def build_analysis_chain():
    """Builds a LangChain chain with Gemini and structured Pydantic output."""
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_ANALYSIS_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.1
    )

    structured_llm = llm.with_structured_output(CallAnalysisSchema)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert sales analyst reviewing an audio sales bot call transcript.
Your job is to rigorously evaluate the conversation and classify the final sales status.

Status Definitions:
- Converted: Customer explicitly agreed to buy, signed up, or requested immediate invoice payment.
- Interested: Customer showed strong positive engagement, asked product questions, and wants more info.
- Demo Requested: Customer asked for or agreed to a scheduled live product demonstration.
- Follow-up Required: Customer requested a callback, needs to check with team/budget, or conversation was inconclusive.
- Not Interested: Customer declined, explicitly said no, stated lack of interest, or hung up angrily.
- No Response: Customer said nothing or conversation was too brief (< 2 turns) to determine intent.

Be concise, factual, and direct."""),
        ("human", """Product Pitched: {product_name}
Call Duration: {duration_seconds} seconds

Full Call Transcript:
{transcript_text}

Provide the structured analysis now.""")
    ])

    return prompt | structured_llm

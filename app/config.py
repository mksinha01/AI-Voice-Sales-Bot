"""
app/config.py
Configuration settings loaded from environment and .env file with precedence enforcement.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "development"
    DATABASE_PATH: str = "data/sales_bot.db"
    RECORDINGS_DIR: str = "data/recordings"
    LOG_LEVEL: str = "INFO"

    # LiveKit credentials
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""

    # Google Gemini credentials
    GOOGLE_API_KEY: str = ""
    GEMINI_VOICE_MODEL: str = "gemini-3.5-flash"
    GEMINI_ANALYSIS_MODEL: str = "gemini-3.5-flash"

    # Speech Synthesis & Recognition Services
    CARTESIA_API_KEY: str = ""
    DEEPGRAM_API_KEY: str = ""
    ELEVEN_API_KEY: str = ""

    # Sales Bot defaults
    DEFAULT_PRODUCT_NAME: str = "CloudScale CRM"
    DEFAULT_LANGUAGE: str = "auto"
    RECORDING_CONSENT_DISCLOSURE: str = (
        "Quick note, our call is recorded for quality assurance."
    )


settings = Settings()

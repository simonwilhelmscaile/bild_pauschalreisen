"""Centralized environment variable loading.

All env vars are loaded once via the Settings class. Use get_settings()
to obtain a cached singleton.
"""
import os
from functools import lru_cache
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""

    # Supabase
    beurer_supabase_url: str
    beurer_supabase_key: str

    # Gemini
    gemini_api_key: str

    # Crawlers
    firecrawl_api_key: Optional[str]
    apify_api_token: Optional[str]
    serper_api_key: Optional[str]

    def __init__(self):
        self.beurer_supabase_url = os.getenv("BEURER_SUPABASE_URL", "")
        self.beurer_supabase_key = os.getenv("BEURER_SUPABASE_KEY", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        self.apify_api_token = os.getenv("APIFY_API_TOKEN")
        self.serper_api_key = os.getenv("SERPER_API_KEY")


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()

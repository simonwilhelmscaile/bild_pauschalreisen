"""Unified Gemini API client.

Provides centralized configuration and access to Google Gemini models
for embeddings and text generation.
"""
import os
from typing import Optional

import google.generativeai as genai
from google.generativeai import GenerativeModel

# Model constants
EMBEDDING_MODEL = "models/gemini-embedding-001"
CLASSIFICATION_MODEL = "gemini-2.0-flash"
REPORT_MODEL = "gemini-2.5-pro"

# Embedding dimensions (for reference)
EMBEDDING_DIMENSION = 768

_configured = False


def _ensure_configured() -> None:
    """Configure Gemini API with API key (idempotent)."""
    global _configured
    if _configured:
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be set")

    genai.configure(api_key=api_key)
    _configured = True


def get_embedding_client():
    """Get configured genai module for embeddings.

    Returns:
        The configured google.generativeai module

    Usage:
        client = get_embedding_client()
        result = client.embed_content(
            model=EMBEDDING_MODEL,
            content="text",
            task_type="retrieval_document"
        )
    """
    _ensure_configured()
    return genai


def get_generative_model(model_name: Optional[str] = None) -> GenerativeModel:
    """Get a GenerativeModel for text generation.

    Args:
        model_name: Model to use. Defaults to CLASSIFICATION_MODEL.

    Returns:
        Configured GenerativeModel instance

    Usage:
        model = get_generative_model()
        response = model.generate_content("prompt")
    """
    _ensure_configured()
    return GenerativeModel(model_name or CLASSIFICATION_MODEL)


def get_classification_model() -> GenerativeModel:
    """Get the model configured for classification tasks."""
    return get_generative_model(CLASSIFICATION_MODEL)


def get_report_model() -> GenerativeModel:
    """Get the model configured for report generation."""
    return get_generative_model(REPORT_MODEL)

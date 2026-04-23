"""
Shared components for openblog-neo pipeline.

- ArticleOutput: Structured blog article schema
- Constants: Shared configuration
- Field Utils: Derive field categories from ArticleOutput (DRY)

Note: GeminiClient moved to core/gemini_client.py (unified client for all services)
"""

from .models import ArticleOutput, Source, ComparisonTable
from .constants import GEMINI_MODEL, MAX_SITEMAP_URLS
from .field_utils import (
    get_content_fields,
    get_html_content_fields,
    get_url_extraction_fields,
    iter_content_fields,
    iter_html_fields,
    iter_url_fields,
)
from .article_exporter import ArticleExporter
from .html_renderer import HTMLRenderer

# Re-export GeminiClient from core for backwards compatibility
try:
    from core.gemini_client import GeminiClient
except ImportError:
    GeminiClient = None

__all__ = [
    "GeminiClient",
    "ArticleOutput",
    "Source",
    "ComparisonTable",
    "ArticleExporter",
    "HTMLRenderer",
    "GEMINI_MODEL",
    "MAX_SITEMAP_URLS",
    # Field utilities
    "get_content_fields",
    "get_html_content_fields",
    "get_url_extraction_fields",
    "iter_content_fields",
    "iter_html_fields",
    "iter_url_fields",
]

"""
Pydantic models for blog service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


VALID_EXPORT_FORMATS = {"html", "markdown", "json", "csv", "xlsx", "pdf"}


class KeywordConfig(BaseModel):
    """Per-keyword configuration for batch processing."""

    keyword: str = Field(..., min_length=1, description="The keyword")
    word_count: Optional[int] = Field(default=None, ge=500, le=10000, description="Override word count")
    instructions: Optional[str] = Field(default=None, description="Keyword-specific instructions")


class CompanyContextInput(BaseModel):
    """Pre-provided company context from frontend."""

    company_name: Optional[str] = None
    company_url: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    products: Optional[List[str]] = None
    services: Optional[List[str]] = None
    target_audience: Optional[str] = None
    tone: Optional[str] = None
    competitors: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    value_propositions: Optional[List[str]] = None
    use_cases: Optional[List[str]] = None
    # Use Dict[str, Any] for flexible nested structures from frontend
    voice_persona: Optional[Dict[str, Any]] = None
    visual_identity: Optional[Dict[str, Any]] = None
    authors: Optional[List[Dict[str, Any]]] = None
    # Research files with extracted content
    research_files: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Research documents with name, content, labels, summary",
    )


class BlogRequest(BaseModel):
    """Request model for blog generation."""

    keywords: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of keywords to generate articles for (1-20)",
        examples=[["AI in healthcare", "Machine learning basics"]],
    )
    company_url: Optional[HttpUrl] = Field(
        default=None,
        description="Company website URL for context (optional)",
        examples=["https://example.com"],
    )
    language: str = Field(
        default="en",
        max_length=10,
        # Relaxed pattern: accepts lowercase codes (en), uppercase (EN), or mixed (en-US, en-GB)
        # Previous strict pattern was rejecting valid inputs from frontend
        pattern=r"^[a-zA-Z]{2}(-[a-zA-Z]{2})?$",
        description="Target language code (ISO 639-1)",
    )
    market: str = Field(
        default="US",
        max_length=10,
        # Relaxed pattern: accepts 2-3 letter codes, case-insensitive
        pattern=r"^[a-zA-Z]{2,3}$",
        description="Target market code",
    )
    skip_images: bool = Field(
        default=False,
        description="Skip image generation to speed up processing",
    )
    max_parallel: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Max concurrent articles (1-10, None = unlimited)",
    )
    export_formats: List[str] = Field(
        default=["html", "json"],
        description="Export formats: html, markdown, json, csv, xlsx, pdf",
    )
    # New fields for frontend integration
    word_count: int = Field(
        default=1500,
        ge=500,
        le=10000,
        description="Target word count for articles (500-10000)",
    )
    tone: Optional[str] = Field(
        default=None,
        description="Writing tone (e.g., professional, casual, technical)",
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="Batch-level custom instructions for content generation",
    )
    keyword_configs: Optional[List[KeywordConfig]] = Field(
        default=None,
        description="Per-keyword configurations with word_count and instructions overrides",
    )
    # Pre-provided company context (skips Stage 1 context extraction)
    company_context: Optional[CompanyContextInput] = Field(
        default=None,
        description="Pre-extracted company context from frontend. If provided, skips Stage 1 extraction.",
    )

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        validated = [kw.strip() for kw in v if kw and kw.strip()]
        if not validated:
            raise ValueError("At least one non-empty keyword is required")
        if len(validated) > 20:
            raise ValueError("Maximum 20 keywords allowed")
        return validated

    @field_validator("export_formats")
    @classmethod
    def validate_export_formats(cls, v: List[str]) -> List[str]:
        invalid = set(v) - VALID_EXPORT_FORMATS
        if invalid:
            raise ValueError(f"Invalid export formats: {invalid}. Valid: {VALID_EXPORT_FORMATS}")
        return v


class ArticleResult(BaseModel):
    """Individual article result."""

    keyword: str
    headline: Optional[str] = None
    meta_description: Optional[str] = None
    word_count: Optional[int] = None
    status: str = "pending"
    html_path: Optional[str] = None
    markdown_path: Optional[str] = None


class BlogResponse(BaseModel):
    """Response model for blog generation."""

    articles: List[ArticleResult]
    total_keywords: int
    completed: int
    failed: int
    processing_time_seconds: float

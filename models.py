"""Pydantic models for social listening."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class CrawlerStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SocialItemCreate(BaseModel):
    """Model for creating a social item."""
    source: str
    source_url: str
    source_id: Optional[str] = None
    title: Optional[str] = None
    content: str
    author: Optional[str] = None
    posted_at: Optional[str] = None  # YYYY-MM-DD format
    crawler_tool: str
    raw_data: Optional[Dict[str, Any]] = None
    collection_type: Optional[str] = "brand"


class SocialItem(SocialItemCreate):
    """Full social item with DB fields."""
    id: str
    content_hash: Optional[str] = None
    crawled_at: datetime
    category: Optional[str] = None
    product_mentions: Optional[List[str]] = None
    sentiment: Optional[str] = None
    relevance_score: Optional[float] = None
    device_relevance_score: Optional[float] = None
    keywords: Optional[List[str]] = None
    journey_stage: Optional[str] = None
    pain_category: Optional[str] = None
    solutions_mentioned: Optional[List[str]] = None
    beurer_opportunity: Optional[str] = None
    # Q&A fields
    question_content: Optional[str] = None
    has_answers: bool = False
    answer_count: int = 0
    # Enrichment fields
    emotion: Optional[str] = None
    intent: Optional[str] = None
    sentiment_intensity: Optional[int] = None
    engagement_score: Optional[float] = None
    language: Optional[str] = "de"
    resolved_source: Optional[str] = None
    # Deep insights fields
    pain_location: Optional[str] = None
    pain_severity: Optional[str] = None
    pain_duration: Optional[str] = None
    bp_concern_type: Optional[str] = None
    bp_severity: Optional[str] = None
    coping_strategies: Optional[List[str]] = None
    medications_mentioned: Optional[List[str]] = None
    life_situation: Optional[str] = None
    user_segment: Optional[str] = None
    problem_category: Optional[str] = None
    solution_frustrations: Optional[List[str]] = None
    negative_root_cause: Optional[str] = None
    key_insight: Optional[str] = None
    content_opportunity: Optional[str] = None
    bridge_moment: Optional[str] = None


class SocialItemAnswer(BaseModel):
    """Answer/reply to a social item."""
    id: Optional[str] = None
    social_item_id: str
    content: str
    author: Optional[str] = None
    position: int = 0
    votes: int = 0
    is_accepted: bool = False
    posted_at: Optional[str] = None
    source_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class CrawlerRunCreate(BaseModel):
    """Model for creating a crawler run."""
    crawler_name: str
    tool: str
    config: Optional[Dict[str, Any]] = None


class CrawlerRun(CrawlerRunCreate):
    """Full crawler run with DB fields."""
    id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: CrawlerStatus = CrawlerStatus.RUNNING
    items_crawled: int = 0
    items_new: int = 0
    error_message: Optional[str] = None


class CrawlRequest(BaseModel):
    """Request to run a crawler."""
    crawler: str = Field(
        ...,
        description=(
            "Crawler name. Options:\n"
            "- Firecrawl: 'gutefrage', 'health_forums', 'diabetes_forum', 'endometriose', 'rheuma_liga', 'onmeda'\n"
            "- Apify: 'amazon', 'reddit', 'youtube', 'tiktok', 'instagram'\n"
            "- Serper: 'serper_discovery', 'serper_brand'"
        )
    )
    max_pages: int = Field(default=5, ge=1, le=50, description="Max pages/items to crawl")
    weekly_mode: bool = Field(
        default=False,
        description="If True, auto-sets date_from to 7 days ago for weekly cron jobs"
    )
    date_from: Optional[str] = Field(
        default=None,
        description="Filter start date (YYYY-MM-DD). Items before this date are excluded."
    )
    date_to: Optional[str] = Field(
        default=None,
        description="Filter end date (YYYY-MM-DD). Items after this date are excluded."
    )
    deep_crawl: Optional[bool] = Field(
        default=None,
        description="Enable Firecrawl deep crawl for serper results (default: True for serper crawlers)"
    )
    max_deep_crawl: Optional[int] = Field(
        default=None,
        ge=1,
        le=200,
        description="Max items to deep crawl (default: 50)"
    )
    queries: Optional[List[str]] = Field(
        default=None,
        description="Custom search queries (Serper crawlers only). Overrides default query list."
    )


class CrawlResponse(BaseModel):
    """Response from crawler run."""
    run_id: str
    status: str
    items_crawled: int
    items_new: int


class GenerateArticleRequest(BaseModel):
    """Request to generate a blog article from a content opportunity."""
    source_item_id: UUID
    keyword: str
    language: str = "de"
    word_count: int = Field(default=1500, ge=500, le=5000)
    social_context: Optional[Dict[str, Any]] = None


class RegenerateArticleRequest(BaseModel):
    """Request to regenerate an existing blog article with optional feedback."""
    feedback: Optional[str] = None
    from_scratch: bool = False


class InlineEdit(BaseModel):
    """A single inline edit: selected passage + user comment."""
    passage_text: str
    comment: str


class InlineEditRequest(BaseModel):
    """Request to apply targeted inline edits to an article's HTML."""
    edits: List[InlineEdit]


class ReviewStatusRequest(BaseModel):
    """Request to update an article's review status."""
    review_status: str = Field(
        ...,
        description="Review status: draft, review, approved, published"
    )


class CommentRequest(BaseModel):
    """Request to add a comment to an article."""
    author: str = Field(..., description="Comment author name")
    comment_text: str = Field(..., description="Comment text")


class SaveHtmlRequest(BaseModel):
    """Request to save manually edited article HTML."""
    article_html: str = Field(..., description="Full article HTML content")


class ServiceCaseImportResult(BaseModel):
    """Response from service case file import."""
    imported: int = Field(description="Number of new cases imported")
    skipped: int = Field(description="Number of duplicate cases skipped")
    errors: int = Field(description="Number of rows that failed to parse")
    batch_id: str = Field(description="UUID grouping all rows from this import")

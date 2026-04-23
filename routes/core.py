"""Core routes — health, crawl, items, runs, search, stats."""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models import CrawlRequest, CrawlResponse
from crawlers import (
    GutefrageCrawler,
    AmazonCrawler,
    HealthForumsCrawler,
    RedditCrawler,
    YouTubeCrawler,
    TikTokCrawler,
    InstagramCrawler,
    TwitterCrawler,
    SerperDiscoveryCrawler,
    SerperBrandMentionsCrawler,
    ExaNewsCrawler,
)
from db.client import (
    get_beurer_supabase,
    search_by_embedding,
    get_item_count,
    get_embedding_count,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """Health check."""
    return {
        "service": "social-listening",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/crawl", response_model=CrawlResponse)
async def run_crawler(request: CrawlRequest):
    """Run a crawler synchronously (for testing).

    Supports weekly_mode for cron jobs - when enabled, filters items to past 7 days.
    For Serper crawlers, this uses API-level time filtering for efficiency.
    For other crawlers, post-fetch filtering is applied based on posted_at dates.
    """
    # Base config with date filtering params
    base_config = {
        "weekly_mode": request.weekly_mode,
        "date_from": request.date_from,
        "date_to": request.date_to,
    }

    if request.crawler == "gutefrage":
        crawler = GutefrageCrawler()
        result = await crawler.run({**base_config, "max_pages": request.max_pages})
    elif request.crawler == "amazon":
        crawler = AmazonCrawler()
        result = await crawler.run({
            **base_config,
            "max_products": request.max_pages,  # Reuse max_pages for products
            "max_reviews": 50
        })
    elif request.crawler == "health_forums":
        crawler = HealthForumsCrawler()
        result = await crawler.run({**base_config, "max_pages": request.max_pages})
    elif request.crawler in ["diabetes_forum", "endometriose", "rheuma_liga", "onmeda"]:
        crawler = HealthForumsCrawler(forum_key=request.crawler)
        result = await crawler.run({**base_config, "max_pages": request.max_pages, "forum": request.crawler})
    elif request.crawler == "reddit":
        crawler = RedditCrawler()
        result = await crawler.run({**base_config, "max_posts": request.max_pages * 10})
    elif request.crawler == "youtube":
        crawler = YouTubeCrawler()
        result = await crawler.run({**base_config, "max_comments": request.max_pages * 20})
    elif request.crawler == "tiktok":
        crawler = TikTokCrawler()
        result = await crawler.run({**base_config, "max_videos": request.max_pages * 10})
    elif request.crawler == "instagram":
        crawler = InstagramCrawler()
        result = await crawler.run({**base_config, "max_posts": request.max_pages * 10})
    elif request.crawler == "twitter":
        crawler = TwitterCrawler()
        result = await crawler.run({**base_config, "max_tweets": request.max_pages * 10})
    elif request.crawler == "serper_discovery":
        config = {**base_config, "max_queries": request.max_pages or 15}
        if request.deep_crawl is not None:
            config["deep_crawl"] = request.deep_crawl
        if request.max_deep_crawl is not None:
            config["max_deep_crawl"] = request.max_deep_crawl
        if request.queries:
            config["queries"] = request.queries
        crawler = SerperDiscoveryCrawler()
        result = await crawler.run(config)
    elif request.crawler == "serper_brand":
        config = {**base_config, "max_queries": request.max_pages or 12}
        if request.deep_crawl is not None:
            config["deep_crawl"] = request.deep_crawl
        if request.max_deep_crawl is not None:
            config["max_deep_crawl"] = request.max_deep_crawl
        if request.queries:
            config["queries"] = request.queries
        crawler = SerperBrandMentionsCrawler()
        result = await crawler.run(config)
    elif request.crawler == "exa_news":
        crawler = ExaNewsCrawler()
        result = await crawler.run({**base_config, "max_queries": request.max_pages or 10})
    else:
        raise HTTPException(400, f"Unknown crawler: {request.crawler}")

    return CrawlResponse(
        run_id=result["run_id"],
        status="success",
        items_crawled=result["items_crawled"],
        items_new=result["items_new"]
    )


@router.get("/items")
async def list_items(limit: int = 50, source: str = None):
    """List social items."""
    client = get_beurer_supabase()
    query = client.table("social_items").select("*").order("crawled_at", desc=True).limit(limit)
    if source:
        query = query.eq("source", source)
    result = query.execute()
    return {"items": result.data, "count": len(result.data)}


@router.get("/runs")
async def list_runs(limit: int = 20):
    """List crawler runs."""
    client = get_beurer_supabase()
    result = client.table("crawler_runs").select("*").order("started_at", desc=True).limit(limit).execute()
    return {"runs": result.data, "count": len(result.data)}


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str
    category: Optional[str] = None
    limit: int = 10


class SearchResult(BaseModel):
    """Single search result."""
    id: str
    source: str
    title: Optional[str]
    content: str
    category: Optional[str]
    similarity: float


@router.post("/search")
async def semantic_search(request: SearchRequest):
    """Semantic search over social items."""
    from services.embedding import embed_text_for_search

    try:
        query_embedding = embed_text_for_search(request.query)
        client = get_beurer_supabase()
        results = search_by_embedding(
            client,
            query_embedding,
            match_count=request.limit,
            filter_category=request.category
        )
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except ValueError as e:
        raise HTTPException(500, f"Embedding service error: {str(e)}")
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(500, f"Search failed: {str(e)}")


@router.get("/stats")
async def get_stats():
    """Get statistics about the social listening data."""
    client = get_beurer_supabase()

    total_items = get_item_count(client)
    items_with_embeddings = get_embedding_count(client)

    # Category breakdown
    categories = {}
    for cat in ["blood_pressure", "pain_tens", "infrarot", "menstrual", "other"]:
        result = client.table("social_items") \
            .select("id", count="exact") \
            .eq("category", cat) \
            .execute()
        categories[cat] = result.count or 0

    # Unclassified count
    unclassified = client.table("social_items") \
        .select("id", count="exact") \
        .is_("category", "null") \
        .execute()

    return {
        "total_items": total_items,
        "items_with_embeddings": items_with_embeddings,
        "items_without_embeddings": total_items - items_with_embeddings,
        "categories": categories,
        "unclassified": unclassified.count or 0
    }


@router.get("/stats/noise")
async def noise_stats():
    """Report noise statistics — how many items fall below relevance thresholds."""
    client = get_beurer_supabase()

    result = client.table("social_items") \
        .select("relevance_score, category, source") \
        .not_.is_("relevance_score", "null") \
        .execute()

    items = result.data or []
    total = len(items)
    if total == 0:
        return {"total_classified_items": 0, "message": "No items with relevance scores"}

    other_count = sum(1 for i in items if i.get("category") == "other")

    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]
    by_threshold = {}
    for t in thresholds:
        below = [i for i in items if (i.get("relevance_score") or 0) < t]
        by_cat = {}
        by_src = {}
        for i in below:
            cat = i.get("category") or "unclassified"
            src = i.get("source") or "unknown"
            by_cat[cat] = by_cat.get(cat, 0) + 1
            by_src[src] = by_src.get(src, 0) + 1
        by_threshold[str(t)] = {
            "total_below": len(below),
            "percentage": round(len(below) / total * 100, 1),
            "by_category": dict(sorted(by_cat.items(), key=lambda x: x[1], reverse=True)),
            "by_source": dict(sorted(by_src.items(), key=lambda x: x[1], reverse=True)),
        }

    return {
        "total_classified_items": total,
        "other_category_count": other_count,
        "other_category_pct": round(other_count / total * 100, 1),
        "by_threshold": by_threshold,
    }

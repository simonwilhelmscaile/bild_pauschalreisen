"""Blog article and author endpoints."""
import logging
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from models import GenerateArticleRequest, RegenerateArticleRequest, InlineEditRequest, ReviewStatusRequest, CommentRequest, SaveHtmlRequest
from db.client import get_beurer_supabase

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# BLOG ARTICLE GENERATION
# =============================================================================

async def _run_article_generation(article_id: str, request: GenerateArticleRequest):
    """Background task wrapper for article generation."""
    from blog.article_service import generate_article
    await generate_article(
        article_id=article_id,
        source_item_id=str(request.source_item_id),
        keyword=request.keyword,
        language=request.language,
        word_count=request.word_count,
        social_context=request.social_context,
    )


@router.post("/generate-article")
async def generate_article_endpoint(
    request: GenerateArticleRequest,
    background_tasks: BackgroundTasks,
):
    """Generate a blog article from a content opportunity (async)."""
    supabase = get_beurer_supabase()
    source_id = str(request.source_item_id)

    existing = (
        supabase.table("blog_articles")
        .select("id, status, headline")
        .eq("source_item_id", source_id)
        .limit(1)
        .execute()
    )
    if existing.data:
        row = existing.data[0]
        if row["status"] in ("completed", "generating"):
            return {"id": row["id"], "status": row["status"], "headline": row.get("headline")}
        supabase.table("blog_articles").delete().eq("id", row["id"]).execute()

    insert_result = supabase.table("blog_articles").insert({
        "source_item_id": source_id,
        "keyword": request.keyword,
        "language": request.language,
        "status": "generating",
        "social_context": request.social_context,
    }).execute()

    article_id = insert_result.data[0]["id"]
    background_tasks.add_task(_run_article_generation, article_id, request)
    return {"id": article_id, "status": "generating"}


@router.get("/blog-articles")
async def list_blog_articles(
    status: Optional[str] = None,
    source_item_id: Optional[str] = None,
    limit: int = 20,
):
    """List blog articles."""
    supabase = get_beurer_supabase()
    query = (
        supabase.table("blog_articles")
        .select("id, source_item_id, keyword, headline, meta_description, language, word_count, status, review_status, error_message, social_context, created_at, updated_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if source_item_id:
        query = query.eq("source_item_id", source_item_id)
    result = query.execute()
    return {"articles": result.data}


@router.get("/blog-articles/{article_id}")
async def get_blog_article(article_id: str):
    """Get a single blog article with full content.

    Renders article_html on-the-fly from article_json so that
    template/style changes apply to all articles immediately.
    """
    supabase = get_beurer_supabase()
    result = (
        supabase.table("blog_articles")
        .select("*")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Article not found")

    article = result.data[0]

    # Re-render HTML from stored JSON so style updates apply instantly
    # Skip re-rendering if the user has manually edited the HTML (html_custom flag)
    article_json = article.get("article_json")
    if article_json and isinstance(article_json, dict) and not article.get("html_custom"):
        from blog.shared.html_renderer import HTMLRenderer
        ctx = article.get("social_context") or {}
        # Fetch author if assigned
        author_data = None
        author_id = article.get("author_id")
        if author_id:
            try:
                author_result = supabase.table("blog_authors").select(
                    "name, title, bio, image_url, credentials, linkedin_url"
                ).eq("id", author_id).limit(1).execute()
                author_data = author_result.data[0] if author_result.data else None
            except Exception:
                pass
        article["article_html"] = HTMLRenderer.render(
            article_json,
            company_name="Beurer",
            language="de",
            category=ctx.get("category", ""),
            author=author_data,
        )

    return article


async def _run_article_regeneration(article_id: str, request: RegenerateArticleRequest):
    """Background task wrapper for article regeneration."""
    from blog.article_service import regenerate_article
    await regenerate_article(
        article_id=article_id,
        feedback=request.feedback,
        from_scratch=request.from_scratch,
    )


@router.post("/blog-articles/{article_id}/regenerate")
async def regenerate_article_endpoint(
    article_id: str,
    request: RegenerateArticleRequest,
    background_tasks: BackgroundTasks,
):
    """Regenerate a blog article with optional feedback (async)."""
    supabase = get_beurer_supabase()

    existing = (
        supabase.table("blog_articles")
        .select("id, status")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Article not found")

    if existing.data[0]["status"] == "regenerating":
        return {"id": article_id, "status": "regenerating"}

    supabase.table("blog_articles").update({
        "status": "regenerating",
    }).eq("id", article_id).execute()

    background_tasks.add_task(_run_article_regeneration, article_id, request)
    return {"id": article_id, "status": "regenerating"}


@router.post("/blog-articles/{article_id}/inline-edit")
async def inline_edit_article(article_id: str, request: InlineEditRequest):
    """Apply targeted inline edits to an article's HTML (synchronous)."""
    supabase = get_beurer_supabase()

    existing = (
        supabase.table("blog_articles")
        .select("id, status")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Article not found")

    status = existing.data[0]["status"]
    if status not in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Article is currently '{status}'. Inline edits require a completed article.",
        )

    from blog.article_service import apply_inline_edits

    result = await apply_inline_edits(
        article_id=article_id,
        edits=[e.model_dump() for e in request.edits],
    )

    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error_message", "Inline edit failed"))

    return result


@router.patch("/blog-articles/{article_id}/save-html")
async def save_article_html(article_id: str, request: SaveHtmlRequest):
    """Save manually edited article HTML and set html_custom flag."""
    supabase = get_beurer_supabase()
    result = (
        supabase.table("blog_articles")
        .select("id")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Article not found")

    supabase.table("blog_articles").update({
        "article_html": request.article_html,
        "html_custom": True,
    }).eq("id", article_id).execute()

    return {"id": article_id, "saved": True}


async def _run_review_agent(article_id: str):
    """Background task wrapper for review agent."""
    try:
        from blog.review_agent import run_review
        await run_review(article_id)
    except Exception as e:
        logger.error("Review agent failed for article %s: %s", article_id, e)


@router.patch("/blog-articles/{article_id}/review-status")
async def update_review_status(
    article_id: str,
    request: ReviewStatusRequest,
    background_tasks: BackgroundTasks,
):
    """Update the review status of a blog article."""
    valid = ("draft", "review", "approved", "published")
    if request.review_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid review_status. Must be one of: {valid}")

    supabase = get_beurer_supabase()
    existing = (
        supabase.table("blog_articles")
        .select("id")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Article not found")

    supabase.table("blog_articles").update({
        "review_status": request.review_status,
    }).eq("id", article_id).execute()

    if request.review_status == "approved":
        background_tasks.add_task(_run_review_agent, article_id)

    return {"id": article_id, "review_status": request.review_status}


@router.post("/blog-articles/{article_id}/comments")
async def add_article_comment(article_id: str, request: CommentRequest):
    """Add a comment to a blog article."""
    supabase = get_beurer_supabase()
    existing = (
        supabase.table("blog_articles")
        .select("id")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Article not found")

    result = supabase.table("article_comments").insert({
        "article_id": article_id,
        "author": request.author,
        "comment_text": request.comment_text,
    }).execute()

    return result.data[0]


@router.get("/blog-articles/{article_id}/comments")
async def get_article_comments(article_id: str):
    """Get all comments for a blog article."""
    supabase = get_beurer_supabase()
    result = (
        supabase.table("article_comments")
        .select("*")
        .eq("article_id", article_id)
        .order("created_at", desc=False)
        .execute()
    )
    return {"comments": result.data}


@router.delete("/blog-articles/{article_id}/comments/{comment_id}")
async def delete_article_comment(article_id: str, comment_id: str):
    """Delete a comment from a blog article."""
    supabase = get_beurer_supabase()
    existing = (
        supabase.table("article_comments")
        .select("id")
        .eq("id", comment_id)
        .eq("article_id", article_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Comment not found")

    supabase.table("article_comments").delete().eq("id", comment_id).execute()
    return {"deleted": True, "id": comment_id}


# ---------------------------------------------------------------------------
# Blog Authors CRUD
# ---------------------------------------------------------------------------

@router.get("/blog-authors")
async def list_blog_authors():
    """List all blog authors."""
    supabase = get_beurer_supabase()
    result = supabase.table("blog_authors").select("*").order("name").execute()
    return {"authors": result.data}


@router.post("/blog-authors")
async def create_blog_author(request: Request):
    """Create a new blog author."""
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    supabase = get_beurer_supabase()
    result = supabase.table("blog_authors").insert({
        "name": name,
        "title": body.get("title", ""),
        "bio": body.get("bio", ""),
        "image_url": body.get("image_url", ""),
        "credentials": body.get("credentials", []),
        "linkedin_url": body.get("linkedin_url", ""),
        "twitter_url": body.get("twitter_url", ""),
    }).execute()
    return result.data[0] if result.data else {"status": "created"}


@router.patch("/blog-authors/{author_id}")
async def update_blog_author(author_id: str, request: Request):
    """Update a blog author."""
    body = await request.json()
    supabase = get_beurer_supabase()

    update_fields = {}
    for field in ("name", "title", "bio", "image_url", "credentials", "linkedin_url", "twitter_url"):
        if field in body:
            update_fields[field] = body[field]

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        supabase.table("blog_authors")
        .update(update_fields)
        .eq("id", author_id)
        .execute()
    )
    return result.data[0] if result.data else {"status": "updated"}


@router.delete("/blog-authors/{author_id}")
async def delete_blog_author(author_id: str):
    """Delete a blog author."""
    supabase = get_beurer_supabase()
    supabase.table("blog_authors").delete().eq("id", author_id).execute()
    return {"deleted": True, "id": author_id}


@router.patch("/blog-articles/{article_id}/author")
async def assign_article_author(article_id: str, request: Request):
    """Assign an author to a blog article."""
    body = await request.json()
    author_id = body.get("author_id")

    supabase = get_beurer_supabase()
    supabase.table("blog_articles").update({
        "author_id": author_id,
    }).eq("id", article_id).execute()

    return {"status": "updated", "article_id": article_id, "author_id": author_id}

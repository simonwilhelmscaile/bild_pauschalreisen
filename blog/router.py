"""
Blog service router.
"""

import uuid
import asyncio
import logging
import base64
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from typing import Dict, Any, List

from core.job_store import job_store, JobStatus
from core.config import ServiceType
from .models import BlogRequest


class RefreshRequest(BaseModel):
    """Request model for content refresh."""
    article: Dict[str, Any] = Field(..., description="Article content to refresh")
    keyword: str = Field(..., description="Original keyword for the article")


class DocumentParseRequest(BaseModel):
    """Request model for document parsing (base64 encoded)."""
    file_content: str = Field(..., description="Base64 encoded file content")
    filename: str = Field(..., description="Original filename")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blog", tags=["Blog"])


@router.get("/health")
async def health():
    """Health check for blog service."""
    return {
        "service": "blog",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/jobs")
async def create_job(
    request: BlogRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create a blog generation job (async).

    Returns immediately with job_id, processes in background.
    """
    job_id = str(uuid.uuid4())

    job = job_store.create(
        job_id=job_id,
        service_type=ServiceType.BLOG,
        request=request.model_dump(mode="json"),
    )

    background_tasks.add_task(run_blog_pipeline, job_id, request)

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Blog generation job created for {len(request.keywords)} keywords",
        "created_at": job["created_at"],
    }


@router.get("/jobs")
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=100),
    status: Optional[str] = None,
):
    """List blog generation jobs."""
    status_filter = JobStatus(status) if status else None
    jobs = job_store.list_all(
        service_type=ServiceType.BLOG,
        status=status_filter,
        limit=limit,
    )
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status and results."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["service_type"] != ServiceType.BLOG.value:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/jobs/{job_id}/articles")
async def get_articles(job_id: str):
    """Get article previews for a job."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["service_type"] != ServiceType.BLOG.value:
        raise HTTPException(status_code=404, detail="Job not found")

    result = job.get("result", {})
    articles = result.get("articles", [])

    return {
        "job_id": job_id,
        "articles": articles,
        "count": len(articles),
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["service_type"] != ServiceType.BLOG.value:
        raise HTTPException(status_code=404, detail="Job not found")

    job_store.delete(job_id)
    return {"message": "Job deleted", "job_id": job_id}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running or pending job."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["service_type"] != ServiceType.BLOG.value:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if job can be cancelled
    if job["status"] not in ["pending", "running"]:
        return {
            "message": f"Job cannot be cancelled (status: {job['status']})",
            "job_id": job_id,
            "status": job["status"],
            "cancelled": False,
        }

    cancelled_job = job_store.cancel(job_id)
    
    return {
        "message": "Job cancelled",
        "job_id": job_id,
        "status": cancelled_job["status"] if cancelled_job else "unknown",
        "cancelled": True,
    }


async def run_blog_pipeline(job_id: str, request: BlogRequest):
    """
    Run the blog generation pipeline.

    Uses the actual 5-stage openblog pipeline.
    """
    try:
        job_store.update(job_id, status=JobStatus.RUNNING)
        logger.info(f"[Blog] Running pipeline for {len(request.keywords)} keywords")

        # Import and run actual pipeline
        from .pipeline import run_pipeline

        # Build keyword configs dict for per-keyword settings
        keyword_configs = {}
        if request.keyword_configs:
            for kc in request.keyword_configs:
                keyword_configs[kc.keyword] = {
                    "word_count": kc.word_count,
                    "instructions": kc.instructions,
                }

        result = await run_pipeline(
            keywords=request.keywords,
            company_url=str(request.company_url),
            language=request.language or "en",
            market=request.market or "US",
            skip_images=request.skip_images or False,
            max_parallel=request.max_parallel,
            word_count=request.word_count,
            tone=request.tone,
            custom_instructions=request.custom_instructions,
            keyword_configs=keyword_configs,
            job_id=job_id,
            company_context=request.company_context.model_dump() if request.company_context else None,
        )

        job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            result=result,
        )

        logger.info(f"[Blog] Pipeline completed: {job_id}")

    except Exception as e:
        logger.error(f"[Blog] Pipeline failed: {e}")
        job_store.update(
            job_id,
            status=JobStatus.FAILED,
            error=str(e),
        )


class ArticleRequest(BaseModel):
    """Request model for single-article generation from dashboard."""
    keyword: str = Field(..., min_length=1, description="SEO keyword for the article")
    source_item_id: Optional[str] = Field(default=None, description="FK to social_items")
    language: str = Field(default="de", description="Article language")
    word_count: int = Field(default=1500, ge=500, le=10000, description="Target word count")
    social_context: Optional[Dict[str, Any]] = Field(default=None, description="Context from content opportunity")


class RegenerateRequest(BaseModel):
    """Request model for article regeneration."""
    article_id: str = Field(..., description="Existing blog_articles row ID")
    feedback: Optional[str] = Field(default=None, description="User feedback to incorporate")
    from_scratch: bool = Field(default=False, description="Ignore previous article and regenerate fresh")


class InlineEditRequest(BaseModel):
    """Request model for inline edits."""
    article_id: str = Field(..., description="Existing blog_articles row ID")
    edits: List[Dict[str, str]] = Field(..., description="List of {passage_text, comment} edits")


@router.post("/articles")
async def create_article(
    request: ArticleRequest,
    background_tasks: BackgroundTasks,
):
    """Create and generate a single blog article using the full pipeline."""
    try:
        return await _create_article_inner(request, background_tasks)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Article creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:500])


async def _create_article_inner(request: ArticleRequest, background_tasks: BackgroundTasks):
    from db.client import get_beurer_supabase

    supabase = get_beurer_supabase()

    # Check for existing article with same source_item_id
    if request.source_item_id:
        try:
            existing = (
                supabase.table("blog_articles")
                .select("id, status, headline")
                .eq("source_item_id", request.source_item_id)
                .limit(1)
                .execute()
            )
            if existing.data:
                return {
                    "id": existing.data[0]["id"],
                    "status": existing.data[0]["status"],
                    "headline": existing.data[0].get("headline"),
                    "message": "Article already exists for this source item",
                }
        except Exception:
            pass

    # Create the article row (use Prefer header for returning data,
    # compatible with older supabase-py that lacks .select() on insert)
    insert_result = (
        supabase.table("blog_articles")
        .insert({
            "source_item_id": request.source_item_id,
            "keyword": request.keyword,
            "language": request.language,
            "word_count": request.word_count,
            "social_context": request.social_context,
            "status": "generating",
        })
        .execute()
    )

    article_id = insert_result.data[0]["id"]

    # Run full pipeline in background
    try:
        from .article_service import generate_article as _generate_article
    except Exception as import_err:
        logger.error(f"Failed to import article_service: {import_err}", exc_info=True)
        supabase.table("blog_articles").update({
            "status": "failed",
            "error_message": f"Pipeline import error: {import_err}",
        }).eq("id", article_id).execute()
        raise HTTPException(status_code=500, detail=f"Pipeline unavailable: {import_err}")

    background_tasks.add_task(
        _generate_article,
        article_id=article_id,
        source_item_id=request.source_item_id or article_id,
        keyword=request.keyword,
        language=request.language,
        word_count=request.word_count,
        social_context=request.social_context,
    )

    return {
        "id": article_id,
        "status": "generating",
        "message": "Article generation started (full pipeline)",
    }


@router.put("/articles")
async def regenerate_article(
    request: RegenerateRequest,
    background_tasks: BackgroundTasks,
):
    """Regenerate article with feedback using the full pipeline."""
    from db.client import get_beurer_supabase

    supabase = get_beurer_supabase()

    # Verify article exists
    existing = (
        supabase.table("blog_articles")
        .select("id, status")
        .eq("id", request.article_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Article not found")

    # Set status to regenerating
    supabase.table("blog_articles").update({
        "status": "regenerating",
    }).eq("id", request.article_id).execute()

    # Run regeneration in background
    try:
        from .article_service import regenerate_article as _regenerate_article
    except Exception as import_err:
        logger.error(f"Failed to import article_service: {import_err}", exc_info=True)
        supabase.table("blog_articles").update({
            "status": "failed",
            "error_message": f"Pipeline import error: {import_err}",
        }).eq("id", request.article_id).execute()
        raise HTTPException(status_code=500, detail=f"Pipeline unavailable: {import_err}")

    background_tasks.add_task(
        _regenerate_article,
        article_id=request.article_id,
        feedback=request.feedback,
        from_scratch=request.from_scratch,
    )

    return {
        "id": request.article_id,
        "status": "regenerating",
        "message": "Article regeneration started (full pipeline)",
    }


@router.post("/articles/inline-edits")
async def inline_edits(request: InlineEditRequest):
    """Apply inline edits to article HTML."""
    from .article_service import apply_inline_edits

    result = await apply_inline_edits(
        article_id=request.article_id,
        edits=request.edits,
    )
    return result


@router.post("/articles/regenerate-batch")
async def regenerate_batch(background_tasks: BackgroundTasks):
    """
    Regenerate all completed articles with fresh content and images.

    Snapshots current state before regenerating each article.
    Runs sequentially in background — returns immediately with article count.
    """
    from db.client import get_beurer_supabase

    supabase = get_beurer_supabase()

    # Fetch all completed articles (client-facing = visible in dashboard)
    result = (
        supabase.table("blog_articles")
        .select("id, keyword, review_status, status")
        .eq("status", "completed")
        .execute()
    )

    articles = result.data or []
    if not articles:
        return {"total": 0, "message": "No completed articles found"}

    article_ids = [a["id"] for a in articles]
    logger.info(f"Batch regeneration: {len(article_ids)} articles queued")

    background_tasks.add_task(_run_batch_regeneration, article_ids)

    return {
        "total": len(article_ids),
        "article_ids": article_ids,
        "status": "started",
        "message": f"Regenerating {len(article_ids)} articles in background",
    }


@router.get("/articles/{article_id}")
async def get_article(article_id: str):
    """Get article by ID (for polling status)."""
    from db.client import get_beurer_supabase

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
    from .stage_tracker import get_generation_stage
    stage = get_generation_stage(article_id)
    if stage:
        article["generation_stage"] = stage
    return article


@router.post("/articles/{article_id}/generate-hero-image")
async def generate_hero_image(article_id: str):
    """
    Generate and attach a Beurer-themed hero image to an article.

    Uses Imagen 4.0 with health-theme-specific prompts.
    Uploads to Supabase Storage and re-renders article HTML.
    """
    from db.client import get_beurer_supabase
    from .stage2.image_prompts import detect_theme, build_beurer_hero_prompt, select_lifestyle_reference
    from .stage2.image_creator import ImageCreator
    from .shared.html_renderer import HTMLRenderer

    supabase = get_beurer_supabase()

    # 1. Fetch article
    result = (
        supabase.table("blog_articles")
        .select("*")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Article not found")

    row = result.data[0]
    article_json = row.get("article_json")
    if not article_json:
        raise HTTPException(status_code=400, detail="Article has no article_json")

    # 2. Detect theme and build atmospheric hero prompt (no product rendering)
    theme = detect_theme(article_json)
    style_ref = select_lifestyle_reference(article_json, theme)
    prompt = build_beurer_hero_prompt(article_json, style_ref=style_ref)
    logger.info(f"Generating hero image for article {article_id} — theme: {theme}")

    # 3. Generate image via Imagen 4.0 (one retry on failure)
    import asyncio as _aio
    creator = ImageCreator()
    image_url = await creator.generate_async(prompt, aspect_ratio="16:9")

    if not image_url:
        logger.warning(f"Hero image attempt 1 failed for '{article_id}', retrying in 2s...")
        await _aio.sleep(2)
        image_url = await creator.generate_async(prompt, aspect_ratio="16:9")

    if not image_url:
        raise HTTPException(status_code=502, detail="Image generation failed after retry")

    logger.info(f"Hero image generated: {image_url[:100]}")

    # 4. Update article_json with image URL
    headline = article_json.get("Headline", "") or article_json.get("headline", "")
    alt_text = f"Beurer Magazin: {headline}"
    if len(alt_text) > 125:
        alt_text = alt_text[:122] + "..."

    article_json["image_01_url"] = image_url
    article_json["image_01_alt_text"] = alt_text

    # 5. Re-render article HTML
    # Fetch author if assigned
    author_data = None
    author_id = row.get("author_id")
    if author_id:
        try:
            author_result = (
                supabase.table("blog_authors")
                .select("name, title, bio, image_url, credentials, linkedin_url")
                .eq("id", author_id)
                .limit(1)
                .execute()
            )
            if author_result.data:
                author_data = author_result.data[0]
        except Exception:
            pass

    article_category = (row.get("social_context") or {}).get("category", "")
    article_html = HTMLRenderer.render(
        article=article_json,
        company_name="Beurer",
        company_url="https://www.beurer.com",
        language=row.get("language", "de"),
        category=article_category,
        author=author_data,
    )

    # 6. Save to DB
    supabase.table("blog_articles").update({
        "article_json": article_json,
        "article_html": article_html,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", article_id).execute()

    return {
        "article_id": article_id,
        "theme": theme,
        "image_url": image_url,
        "alt_text": alt_text,
    }


@router.post("/articles/{article_id}/attach-product-images")
async def attach_product_images(article_id: str):
    """
    Find and attach matching Beurer product cutout images to an article.

    Scans article for product model mentions (BM 27, EM 59, IL 50, etc.)
    and sets matching product cutout URLs as image_02/image_03.
    Re-renders article HTML with inline product images.
    """
    from db.client import get_beurer_supabase
    from .stage2.image_prompts import find_product_images
    from .shared.html_renderer import HTMLRenderer

    supabase = get_beurer_supabase()

    # 1. Fetch article
    result = (
        supabase.table("blog_articles")
        .select("*")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Article not found")

    row = result.data[0]
    article_json = row.get("article_json")
    if not article_json:
        raise HTTPException(status_code=400, detail="Article has no article_json")

    # 2. Find matching product images
    matches = find_product_images(article_json)
    if not matches:
        return {"article_id": article_id, "product_images": [], "message": "No matching products found"}

    # 3. Attach matched product images (URLs come from Supabase Storage)
    attached = []
    for i, match in enumerate(matches[:2]):  # Max 2 product images (image_02, image_03)
        slot = f"image_0{i + 2}"
        article_json[f"{slot}_url"] = match["url"]
        article_json[f"{slot}_alt_text"] = f"Beurer {match['model']}"
        attached.append({"model": match["model"], "slot": slot, "url": match["url"]})

    logger.info(f"Attached {len(attached)} product images to article {article_id}")

    # 4. Re-render article HTML
    author_data = None
    author_id = row.get("author_id")
    if author_id:
        try:
            author_result = (
                supabase.table("blog_authors")
                .select("name, title, bio, image_url, credentials, linkedin_url")
                .eq("id", author_id)
                .limit(1)
                .execute()
            )
            if author_result.data:
                author_data = author_result.data[0]
        except Exception:
            pass

    article_category = (row.get("social_context") or {}).get("category", "")
    article_html = HTMLRenderer.render(
        article=article_json,
        company_name="Beurer",
        company_url="https://www.beurer.com",
        language=row.get("language", "de"),
        category=article_category,
        author=author_data,
    )

    # 5. Save to DB
    supabase.table("blog_articles").update({
        "article_json": article_json,
        "article_html": article_html,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", article_id).execute()

    return {
        "article_id": article_id,
        "product_images": attached,
    }


async def _run_batch_regeneration(article_ids: list):
    """Process batch regeneration with parallel workers (3 concurrent)."""
    import asyncio
    from db.client import get_beurer_supabase
    from .article_service import regenerate_article as _regenerate

    semaphore = asyncio.Semaphore(3)
    results = {"succeeded": 0, "failed": 0}

    async def _regen_one(article_id: str):
        async with semaphore:
            supabase = get_beurer_supabase()
            try:
                # Snapshot current state into feedback_history
                row = (
                    supabase.table("blog_articles")
                    .select("article_json, article_html, headline, feedback_history")
                    .eq("id", article_id)
                    .limit(1)
                    .execute()
                )
                if not row.data:
                    results["failed"] += 1
                    return

                article = row.data[0]
                history = article.get("feedback_history") or []
                history.append({
                    "type": "snapshot",
                    "headline": article.get("headline", ""),
                    "article_html": article.get("article_html", ""),
                    "article_json": article.get("article_json", {}),
                    "created_at": datetime.utcnow().isoformat(),
                    "version": len(history) + 1,
                    "reason": "batch_regeneration",
                })
                supabase.table("blog_articles").update({
                    "feedback_history": history,
                }).eq("id", article_id).execute()

                # Regenerate (from scratch, no feedback)
                result = await _regenerate(article_id=article_id, feedback=None, from_scratch=True)
                if result.get("status") == "completed":
                    results["succeeded"] += 1
                    logger.info(f"Batch regen: {article_id} completed ({results['succeeded']}/{len(article_ids)})")
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                logger.error(f"Batch regen failed for {article_id}: {e}")

    await asyncio.gather(*[_regen_one(aid) for aid in article_ids])
    logger.info(f"Batch regeneration complete: {results['succeeded']} succeeded, {results['failed']} failed out of {len(article_ids)}")


@router.post("/refresh")
async def refresh_content(request: RefreshRequest):
    """
    Refresh article content using AI + Google Search.

    Identifies and updates outdated facts with verified current data.
    """
    try:
        logger.info(f"[Blog] Refreshing content for: {request.keyword}")

        from .stage_refresh.stage_refresh import run_stage_refresh
        from .stage_refresh.refresh_models import RefreshInput

        refresh_input = RefreshInput(
            article=request.article,
            keyword=request.keyword,
        )

        result = await run_stage_refresh(refresh_input)

        return {
            "article": result.article,
            "fixes_applied": result.fixes_applied,
            "fixes": [fix.model_dump() for fix in result.fixes],
            "ai_calls": result.ai_calls,
        }

    except Exception as e:
        logger.error(f"[Blog] Refresh failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/parse-document")
async def parse_document_endpoint(request: DocumentParseRequest):
    """
    Parse a PDF or Word document and extract content for blog refresh.
    
    Accepts base64 encoded file content and returns extracted text,
    title, and suggested keyword.
    """
    try:
        logger.info(f"[Blog] Parsing document: {request.filename}")
        
        from .document_parser import parse_document
        
        # Decode base64 content
        try:
            file_bytes = base64.b64decode(request.file_content)
        except Exception as decode_error:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 encoding: {str(decode_error)}"
            )
        
        # Parse the document
        result = parse_document(file_bytes, request.filename)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to parse document")
            )
        
        logger.info(f"[Blog] Document parsed: {result.get('word_count', 0)} words extracted")
        
        return {
            "success": True,
            "content": result.get("content", ""),
            "title": result.get("title", ""),
            "keyword": result.get("keyword", ""),
            "word_count": result.get("word_count", 0),
            "filename": result.get("filename", request.filename),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Blog] Document parsing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/parse-document-upload")
async def parse_document_upload(file: UploadFile = File(...)):
    """
    Parse an uploaded PDF or Word document.
    
    Alternative endpoint that accepts file upload directly.
    """
    try:
        logger.info(f"[Blog] Parsing uploaded document: {file.filename}")
        
        from .document_parser import parse_document
        
        # Read file content
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Parse the document
        result = parse_document(file_bytes, file.filename or "document")
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to parse document")
            )
        
        logger.info(f"[Blog] Document parsed: {result.get('word_count', 0)} words extracted")
        
        return {
            "success": True,
            "content": result.get("content", ""),
            "title": result.get("title", ""),
            "keyword": result.get("keyword", ""),
            "word_count": result.get("word_count", 0),
            "filename": result.get("filename", file.filename),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Blog] Document upload parsing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

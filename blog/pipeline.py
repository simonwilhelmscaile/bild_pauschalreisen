#!/usr/bin/env python3
"""
OpenBlog Neo - Main Pipeline Orchestrator

Runs the 5-stage blog generation pipeline:
- Stage 1: Set Context (runs once per batch)
- Stages 2-5: Run per article, all articles in parallel

Usage:
    python run_pipeline.py --url https://example.com --keywords "keyword 1" "keyword 2"
    python run_pipeline.py --input batch.json --output results/

Architecture:
    Stage 1 (once)
         ↓
    ┌────┴────┬─────────┐
    ▼         ▼         ▼
  [Art 1]  [Art 2]  [Art 3]  ← parallel
    │         │         │
    ▼         ▼         ▼
  Stage 2   Stage 2   Stage 2
    │         │         │
    ▼         ▼         ▼
  Stage 3   Stage 3   Stage 3  ← sequential per article
    │         │         │
    ▼         ▼         ▼
  Stage 4   Stage 4   Stage 4
    │         │         │
    ▼         ▼         ▼
  Stage 5   Stage 5   Stage 5
    │         │         │
    ▼         ▼         ▼
  [Out 1]  [Out 2]  [Out 3]
"""

import asyncio
import argparse
import copy
import importlib.util
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

from core.job_store import job_store


def update_job_progress(job_id: str, stage: str, percent: int, message: str = ""):
    """Helper to update job progress in the store."""
    if job_id:
        job_store.update(job_id, progress={
            "stage": stage,
            "percent": percent,
            "message": message,
        })


def is_job_cancelled(job_id: str) -> bool:
    """Check if job has been cancelled."""
    if not job_id:
        return False
    job = job_store.get(job_id)
    return job is not None and job.get("status") == "cancelled"

# Load .env from mono-python-service root
_BASE_PATH = Path(__file__).parent
_ROOT_PATH = _BASE_PATH.parent.parent
load_dotenv(_ROOT_PATH / ".env")

# =============================================================================
# Module Loading - Done ONCE at import time for thread safety
# =============================================================================

# Add base path for imports (services/blog directory)
if str(_BASE_PATH) not in sys.path:
    sys.path.insert(0, str(_BASE_PATH))

# Also add python-backend root for absolute imports
if str(_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(_ROOT_PATH))

# Import shared modules - try multiple approaches for compatibility
try:
    # First try relative import (when imported as package)
    from .shared.models import ArticleOutput
    from .shared.html_renderer import HTMLRenderer
    from .shared.article_exporter import ArticleExporter
except ImportError:
    try:
        # Fallback: absolute import from services.blog
        from services.blog.shared.models import ArticleOutput
        from services.blog.shared.html_renderer import HTMLRenderer
        from services.blog.shared.article_exporter import ArticleExporter
    except ImportError:
        # Last fallback: direct import (for standalone script execution)
        from shared.models import ArticleOutput
        from shared.html_renderer import HTMLRenderer
        from shared.article_exporter import ArticleExporter


def _load_module_from_path(module_name: str, file_path: Path):
    """Load a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Pre-load all stage modules at import time (thread-safe)
# Stage 2
_stage2_path = _BASE_PATH / "stage2"
if str(_stage2_path) not in sys.path:
    sys.path.insert(0, str(_stage2_path))
from stage_2 import run_stage_2, Stage2Input, CompanyContext, VisualIdentity

# Stage 3 - uniquely named models file, no collision risk
_stage3_path = _BASE_PATH / "stage3"
if str(_stage3_path) not in sys.path:
    sys.path.insert(0, str(_stage3_path))
_stage3_models = _load_module_from_path("stage3_models", _stage3_path / "stage3_models.py")
Stage3Input = _stage3_models.Stage3Input
_stage3_module = _load_module_from_path("stage_3_module", _stage3_path / "stage_3.py")
run_stage_3 = _stage3_module.run_stage_3

# Stage 4 - uniquely named models file, no collision risk
_stage4_path = _BASE_PATH / "stage4"
if str(_stage4_path) not in sys.path:
    sys.path.insert(0, str(_stage4_path))
_stage4_models = _load_module_from_path("stage4_models", _stage4_path / "stage4_models.py")
Stage4Input = _stage4_models.Stage4Input
_stage4_module = _load_module_from_path("stage_4_module", _stage4_path / "stage_4.py")
run_stage_4 = _stage4_module.run_stage_4

# Stage 5 - uniquely named models file, no collision risk
_stage5_path = _BASE_PATH / "stage5"
if str(_stage5_path) not in sys.path:
    sys.path.insert(0, str(_stage5_path))
_stage5_models = _load_module_from_path("stage5_models", _stage5_path / "stage5_models.py")
_stage5_module = _load_module_from_path("stage_5_module", _stage5_path / "stage_5.py")
run_stage_5 = _stage5_module.run_stage_5

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Orchestration
# =============================================================================

async def process_single_article(
    context,
    article,
    skip_images: bool = False,
    output_dir: Optional[Path] = None,
    export_formats: Optional[List[str]] = None,
    word_count: int = 1500,
    tone: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    keyword_instructions: Optional[str] = None,
    job_id: Optional[str] = None,
    article_index: int = 0,
    total_articles: int = 1,
) -> dict:
    """
    Process one article through stages 2-5 sequentially.

    Uses pre-loaded stage modules (loaded at import time for thread safety).

    Args:
        context: Stage1Output with company context, sitemap, etc.
        article: ArticleJob with keyword, slug, href
        word_count: Target word count for the article
        tone: Writing tone (added to custom_instructions if provided)
        custom_instructions: Batch-level custom instructions
        keyword_instructions: Keyword-specific instructions
        skip_images: Skip image generation in Stage 2
        output_dir: Directory for exported files
        export_formats: List of export formats (html, markdown, json, csv, xlsx, pdf)

    Returns:
        Dict with article output and metadata
    """
    # Check for cancellation before starting
    if is_job_cancelled(job_id):
        logger.info(f"  Skipping article (job cancelled): {article.keyword}")
        return {
            "keyword": article.keyword,
            "slug": article.slug,
            "href": article.href,
            "article": None,
            "images": [],
            "reports": {},
            "exported_files": {},
            "error": "Job cancelled",
        }

    logger.info(f"  Processing article: {article.keyword}")

    result = {
        "keyword": article.keyword,
        "slug": article.slug,
        "href": article.href,
        "article": None,
        "images": [],
        "reports": {},
        "exported_files": {},
        "error": None,
    }

    try:
        # Calculate base progress for this article (each article gets equal share of 10-90%)
        base_progress = 10 + (article_index * 80 // total_articles)
        progress_per_stage = 80 // (total_articles * 4)  # 4 main stages per article

        # -----------------------------------------
        # Stage 2: Blog Gen + Image Gen
        # -----------------------------------------
        logger.info(f"    [Stage 2] Generating article...")
        update_job_progress(job_id, "content_generation", base_progress, f"Generating content for: {article.keyword}")

        # Extract visual_identity from company_context
        company_ctx = context.company_context.model_dump()
        visual_identity_data = company_ctx.pop("visual_identity", None)

        # Build combined instructions (tone + custom_instructions)
        combined_instructions = custom_instructions or ""
        if tone:
            tone_instruction = f"Write in a {tone} tone."
            combined_instructions = f"{tone_instruction}\n{combined_instructions}".strip() if combined_instructions else tone_instruction

        stage2_input = Stage2Input(
            keyword=article.keyword,
            company_context=CompanyContext(**company_ctx),
            visual_identity=VisualIdentity(**visual_identity_data) if visual_identity_data else None,
            language=context.language,
            job_id=context.job_id,
            skip_images=skip_images,
            word_count=word_count,
            custom_instructions=combined_instructions if combined_instructions else None,
            keyword_instructions=keyword_instructions,
        )

        stage2_output = await run_stage_2(stage2_input)
        # Deep copy to prevent mutation side effects between stages
        article_dict = copy.deepcopy(stage2_output.article.model_dump())
        result["images"] = [img.model_dump() for img in stage2_output.images]
        result["reports"]["stage2"] = {
            "ai_calls": stage2_output.ai_calls,
            "images_generated": stage2_output.images_generated,
        }
        logger.info(f"    [Stage 2] ✓ Generated: {stage2_output.article.Headline[:50]}...")
        update_job_progress(job_id, "quality_check", base_progress + progress_per_stage, f"Quality check: {article.keyword}")

        # -----------------------------------------
        # Stage 3: Quality Check
        # -----------------------------------------
        logger.info(f"    [Stage 3] Quality check...")

        # Build voice context from Stage 1 for brand-aligned quality fixes
        voice_context = None
        voice_persona = context.company_context.voice_persona
        if voice_persona:
            # Extract key voice fields for quality checking
            voice_data = voice_persona if isinstance(voice_persona, dict) else voice_persona.model_dump()
            lang_style = voice_data.get("language_style", {})
            if isinstance(lang_style, dict):
                formality = lang_style.get("formality", "")
            else:
                formality = getattr(lang_style, "formality", "")

            voice_context = {
                "tone": context.company_context.tone,
                "banned_words": voice_data.get("banned_words", []),
                "do_list": voice_data.get("do_list", []),
                "dont_list": voice_data.get("dont_list", []),
                "example_phrases": voice_data.get("example_phrases", []),
                "formality": formality,
                "first_person_usage": voice_data.get("first_person_usage", ""),
            }

        stage3_output = await run_stage_3({
            "article": article_dict,
            "keyword": article.keyword,
            "language": context.language,
            "voice_context": voice_context,
        })

        # Deep copy to prevent mutation side effects
        article_dict = copy.deepcopy(stage3_output["article"])
        result["reports"]["stage3"] = {
            "fixes_applied": stage3_output["fixes_applied"],
            "ai_calls": stage3_output["ai_calls"],
        }
        logger.info(f"    [Stage 3] ✓ Applied {stage3_output['fixes_applied']} fixes")
        update_job_progress(job_id, "url_verification", base_progress + progress_per_stage * 2, f"Verifying URLs: {article.keyword}")

        # -----------------------------------------
        # Stage 4: URL Verification
        # -----------------------------------------
        logger.info(f"    [Stage 4] URL verification...")

        stage4_input = Stage4Input(
            article=article_dict,
            keyword=article.keyword,
            company_name=context.company_context.company_name,
        )

        stage4_output = await run_stage_4(stage4_input)
        # Deep copy to prevent mutation side effects
        article_dict = copy.deepcopy(stage4_output.article)
        result["reports"]["stage4"] = {
            "total_urls": stage4_output.total_urls,
            "valid_urls": stage4_output.valid_urls,
            "dead_urls": stage4_output.dead_urls,
            "replaced_urls": stage4_output.replaced_urls,
            "ai_calls": stage4_output.ai_calls,
        }
        logger.info(f"    [Stage 4] ✓ Verified {stage4_output.total_urls} URLs, replaced {stage4_output.replaced_urls}")
        update_job_progress(job_id, "internal_links", base_progress + progress_per_stage * 3, f"Adding internal links: {article.keyword}")

        # -----------------------------------------
        # Stage 5: Internal Links
        # -----------------------------------------
        logger.info(f"    [Stage 5] Internal links...")

        # Build batch siblings (other articles in this batch)
        batch_siblings = [
            {"keyword": a.keyword, "slug": a.slug, "href": a.href}
            for a in context.articles
            if a.keyword != article.keyword
        ]

        # Collect sitemap URLs with truncation warnings if needed
        blog_urls = context.sitemap.blog_urls if context.sitemap else []
        resource_urls = context.sitemap.resource_urls if context.sitemap else []
        tool_urls = context.sitemap.tool_urls if context.sitemap else []
        product_urls = context.sitemap.product_urls if context.sitemap else []
        service_urls = context.sitemap.service_urls if context.sitemap else []

        if len(blog_urls) > 50:
            logger.debug(f"    Truncating {len(blog_urls)} blog URLs to 50 for internal linking")
        if len(resource_urls) > 20:
            logger.debug(f"    Truncating {len(resource_urls)} resource URLs to 20 for internal linking")

        # Load catalog once for Stage 5 + Stage 5.5
        _catalog = None
        try:
            from product_catalog import load_catalog as _load_catalog, apply_product_validation
            _catalog = _load_catalog()
        except Exception:
            pass

        _catalog_category_urls = list(_catalog.get_category_urls().values()) if _catalog else []
        _catalog_product_urls = list(_catalog.get_product_urls().values()) if _catalog else []

        stage5_output = await run_stage_5({
            "article": article_dict,
            "current_href": article.href,
            "company_url": context.company_context.company_url,
            "batch_siblings": batch_siblings,
            "sitemap_blog_urls": blog_urls[:50],
            "sitemap_resource_urls": resource_urls[:20],
            "sitemap_tool_urls": tool_urls[:10],
            "sitemap_product_urls": _catalog_product_urls or product_urls[:10],
            "sitemap_service_urls": service_urls[:5],
            "sitemap_category_urls": _catalog_category_urls,
        })

        # Deep copy to prevent mutation side effects
        article_dict = copy.deepcopy(stage5_output["article"])
        result["reports"]["stage5"] = {
            "links_added": stage5_output["links_added"],
        }
        logger.info(f"    [Stage 5] ✓ Added {stage5_output['links_added']} internal links")
        update_job_progress(job_id, "finalizing", base_progress + progress_per_stage * 4, f"Finalizing: {article.keyword}")

        # -----------------------------------------
        # Stage 5.5: Product Validation
        # -----------------------------------------
        logger.info(f"    [Stage 5.5] Product validation...")

        try:
            if _catalog:
                validation_report = apply_product_validation(article_dict, _catalog)
                result["reports"]["product_validation"] = validation_report
                logger.info(
                    f"    [Stage 5.5] Validated — {validation_report['replacements_made']} replacements, "
                    f"{validation_report['links_rewritten']} links rewritten"
                )
        except Exception as e:
            logger.warning(f"    [Stage 5.5] Product validation failed (non-blocking): {e}")
            result["reports"]["product_validation"] = {"error": str(e)}

        # -----------------------------------------
        # Stage Cleanup: HTML Cleanup and Validation
        # -----------------------------------------
        logger.info(f"    [Cleanup] HTML cleanup and validation...")

        try:
            from services.blog.stage_cleanup import run_cleanup

            cleanup_result = run_cleanup(article_dict)

            result["reports"]["cleanup"] = {
                "fields_cleaned": cleanup_result.fields_cleaned,
                "valid": cleanup_result.valid,
                "warnings": cleanup_result.warnings,
                "total_sections": cleanup_result.stats.total_sections,
                "total_faqs": cleanup_result.stats.total_faqs,
                "total_paas": cleanup_result.stats.total_paas,
            }

            if cleanup_result.warnings:
                logger.warning(f"    [Cleanup] ⚠️ Validation warnings: {len(cleanup_result.warnings)}")
            else:
                logger.info(f"    [Cleanup] ✓ Cleaned {cleanup_result.fields_cleaned} fields")
        except Exception as e:
            logger.warning(f"    [Cleanup] Could not run cleanup: {e}")

        # -----------------------------------------
        # Stage Similarity: Content Similarity Check (non-blocking)
        # -----------------------------------------
        logger.info(f"    [Similarity] Content similarity check...")

        try:
            from services.blog.stage_similarity import run_similarity_check

            similarity_report = run_similarity_check(
                job_id=f"{context.job_id}_{article.slug}",
                article_data=article_dict,
                add_to_memory=True,
            )

            if similarity_report:
                result["reports"]["similarity"] = {
                    "similarity_score": similarity_report.similarity_score,
                    "is_too_similar": similarity_report.is_too_similar,
                    "similar_articles": [
                        {"job_id": s.job_id, "similarity": s.similarity}
                        for s in similarity_report.similar_articles
                    ],
                    "check_method": similarity_report.check_method,
                }
                if similarity_report.is_too_similar:
                    logger.warning(f"    [Similarity] ⚠️ Content similarity: {similarity_report.similarity_score * 100:.1f}%")
                else:
                    logger.info(f"    [Similarity] ✓ Content is unique ({similarity_report.similarity_score * 100:.1f}%)")
        except Exception as e:
            # Non-blocking: log error but continue
            logger.warning(f"    [Similarity] Could not check similarity: {e}")

        # -----------------------------------------
        # Render HTML (always, for API responses)
        # -----------------------------------------
        html_content = HTMLRenderer.render(
            article=article_dict,
            company_name=context.company_context.company_name,
            company_url=context.company_context.company_url,
            language=context.language,
        )
        article_dict["html_content"] = html_content

        # -----------------------------------------
        # Export (if output_dir provided)
        # -----------------------------------------
        if output_dir:
            logger.info(f"    [Export] Exporting article...")

            # Export all formats
            formats = export_formats or ["html", "json"]
            article_output_dir = output_dir / article.slug
            exported = ArticleExporter.export_all(
                article=article_dict,
                html_content=html_content,
                output_dir=article_output_dir,
                formats=formats,
            )

            result["exported_files"] = exported
            logger.info(f"    [Export] ✓ Exported to {article_output_dir}")

        result["article"] = article_dict
        logger.info(f"  ✓ Article complete: {article.keyword}")

    except Exception as e:
        logger.error(f"  ✗ Article failed: {article.keyword} - {type(e).__name__}: {e}")
        # Log exception details at debug level (avoid exposing sensitive data in production logs)
        logger.debug(f"Full exception for {article.keyword}:", exc_info=True)
        result["error"] = str(e)

    return result


async def run_pipeline(
    keywords: List[str],
    company_url: str,
    language: str = "en",
    market: str = "US",
    skip_images: bool = False,
    max_parallel: Optional[int] = None,
    output_dir: Optional[Path] = None,
    export_formats: Optional[List[str]] = None,
    word_count: int = 1500,
    tone: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    keyword_configs: Optional[Dict[str, Dict]] = None,
    job_id: Optional[str] = None,
    company_context: Optional[Dict] = None,
) -> dict:
    """
    Run full pipeline: Stage 1 once, then Stages 2-5 for each article in parallel.

    Args:
        keywords: List of keywords to generate articles for
        company_url: Company website URL
        language: Target language code
        market: Target market code
        skip_images: Skip image generation
        max_parallel: Limit concurrent article processing (None = unlimited)
        output_dir: Directory for exported files
        export_formats: List of export formats (html, markdown, json, csv, xlsx, pdf)
        word_count: Target word count for articles (default 1500)
        tone: Writing tone (e.g., professional, casual)
        custom_instructions: Batch-level custom instructions
        keyword_configs: Per-keyword configurations {keyword: {word_count, instructions}}
        job_id: Job ID for progress tracking
        company_context: Pre-provided company context dict (skips Stage 1 if provided)

    Returns:
        Dict with pipeline results
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("OpenBlog Neo Pipeline")
    logger.info("=" * 60)
    logger.info(f"Keywords: {len(keywords)}")
    logger.info(f"Company: {company_url}")
    logger.info(f"Language: {language}, Market: {market}")
    logger.info("=" * 60)

    # Initial progress update
    update_job_progress(job_id, "initializing", 0, "Starting blog generation pipeline")

    # Import Stage 1 models and functions
    sys.path.insert(0, str(Path(__file__).parent / "stage1"))
    from stage_1 import run_stage_1
    from stage1_models import Stage1Input, Stage1Output, CompanyContext, ArticleJob, SitemapData, generate_slug

    # -----------------------------------------
    # Stage 1: Set Context (runs once)
    # -----------------------------------------
    if company_context:
        # Use pre-provided context from frontend (skips OpenContext extraction)
        logger.info("\n[Stage 1] Using pre-provided company context (skipping extraction)")
        update_job_progress(job_id, "context_extraction", 5, "Using pre-provided company context")

        # Build CompanyContext from provided dict
        ctx_data = CompanyContext.from_dict(company_context)

        # Build ArticleJob list from keywords
        articles = []
        for kw in keywords:
            slug = generate_slug(kw)
            articles.append(ArticleJob(
                keyword=kw,
                slug=slug,
                href=f"/blog/{slug}",
            ))

        # Create Stage1Output with pre-provided context
        context = Stage1Output(
            articles=articles,
            language=language,
            market=market,
            company_context=ctx_data,
            sitemap=SitemapData(),  # Empty sitemap when using pre-provided context
            opencontext_called=False,
            ai_calls=0,
        )

        # Include research files in custom_instructions if provided
        research_files = company_context.get("research_files", [])
        if research_files:
            research_text = "\n\n## Research Documents for Reference:\n"
            for f in research_files[:5]:  # Limit to 5 files
                name = f.get("name", "Document")
                summary = f.get("aiAnalysis") or f.get("summary") or ""
                content = f.get("fullTextContent") or f.get("content", "")[:2000]
                labels = ", ".join(f.get("aiLabels", []) or f.get("labels", []))
                research_text += f"\n### {name}"
                if labels:
                    research_text += f" [{labels}]"
                research_text += f"\n{summary}\n"
                if content:
                    research_text += f"\nContent excerpt:\n{content[:2000]}\n"

            if custom_instructions:
                custom_instructions = f"{custom_instructions}\n{research_text}"
            else:
                custom_instructions = research_text
            logger.info(f"  Added {len(research_files)} research files to custom instructions")

        logger.info(f"  Company: {context.company_context.company_name or 'Not specified'}")
        logger.info(f"  Articles: {len(context.articles)}")
    else:
        # Run Stage 1 to extract context from company_url
        logger.info("\n[Stage 1] Set Context")
        update_job_progress(job_id, "context_extraction", 5, "Extracting company context and sitemap")

        input_data = Stage1Input(
            keywords=keywords,
            company_url=company_url,
            language=language,
            market=market,
        )

        context = await run_stage_1(input_data)

        logger.info(f"  Company: {context.company_context.company_name}")
        logger.info(f"  Articles: {len(context.articles)}")
        logger.info(f"  Sitemap: {context.sitemap.total_pages} pages")

    update_job_progress(job_id, "context_complete", 10, f"Context ready. Processing {len(context.articles)} article(s)")

    # -----------------------------------------
    # Stages 2-5: Per article (parallel)
    # -----------------------------------------
    logger.info("\n[Stages 2-5] Article Processing (parallel)")

    # Create tasks for each article
    keyword_configs = keyword_configs or {}
    total_articles = len(context.articles)
    tasks = [
        process_single_article(
            context,
            article,
            skip_images=skip_images,
            output_dir=output_dir,
            export_formats=export_formats,
            word_count=keyword_configs.get(article.keyword, {}).get("word_count") or word_count,
            tone=tone,
            custom_instructions=custom_instructions,
            keyword_instructions=keyword_configs.get(article.keyword, {}).get("instructions"),
            job_id=job_id,
            article_index=idx,
            total_articles=total_articles,
        )
        for idx, article in enumerate(context.articles)
    ]

    # Run with optional concurrency limit
    # Use return_exceptions=True to prevent one failed article from stopping all processing
    if max_parallel and max_parallel > 0:
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_parallel)

        async def limited_task(task):
            async with semaphore:
                return await task

        results = await asyncio.gather(*[limited_task(t) for t in tasks], return_exceptions=True)
    else:
        # Unlimited parallelism
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle any exceptions that were returned
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            keyword = context.articles[i].keyword if i < len(context.articles) else f"article_{i}"
            logger.error(f"  ✗ Article failed with exception: {keyword} - {result}")
            processed_results.append({
                "keyword": keyword,
                "article": None,
                "error": str(result),
            })
        else:
            processed_results.append(result)
    results = processed_results

    # -----------------------------------------
    # Collect Results
    # -----------------------------------------
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    successful = sum(1 for r in results if r.get("article") and not r.get("error"))
    failed = sum(1 for r in results if r.get("error"))

    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Complete")
    logger.info("=" * 60)
    logger.info(f"Duration: {duration:.1f}s")
    logger.info(f"Articles: {successful} successful, {failed} failed")
    logger.info("=" * 60)
    update_job_progress(job_id, "complete", 100, f"Generated {successful} article(s) in {duration:.1f}s")

    # -----------------------------------------
    # Transform to frontend-expected structure
    # -----------------------------------------
    # Frontend expects flat "articles" array with specific fields
    articles = []
    total_word_count = 0
    total_aeo_score = 0

    for r in results:
        article = r.get("article")
        if article and not r.get("error"):
            # Extract fields expected by frontend (BlogArticle interface)
            transformed = {
                "keyword": article.get("Keyword", r.get("keyword", "")),
                "headline": article.get("Headline", ""),
                "slug": article.get("Slug", ""),
                "meta_title": article.get("Meta_Title", ""),
                "meta_description": article.get("Meta_Description", ""),
                "html_content": article.get("html_content", ""),
                "word_count": article.get("Word_Count", 0),
                "read_time": article.get("Read_Time", ""),
                "aeo_score": article.get("AEO_Score", 0),
                "sources": article.get("Sources", ""),
            }
            articles.append(transformed)
            total_word_count += transformed["word_count"]
            total_aeo_score += transformed["aeo_score"]

    avg_word_count = total_word_count / len(articles) if articles else 0
    avg_aeo_score = total_aeo_score / len(articles) if articles else 0

    return {
        "job_id": job_id or context.job_id,
        "company": context.company_context.company_name,
        "language": language,
        "market": market,
        "duration_seconds": duration,
        "articles_total": len(results),
        "articles_successful": successful,
        "articles_failed": failed,
        # Frontend-expected structure
        "articles": articles,
        "statistics": {
            "total_articles": len(articles),
            "avg_word_count": avg_word_count,
            "avg_aeo_score": avg_aeo_score,
            "duration_seconds": duration,
        },
        # Keep original data for debugging/advanced use
        "context": context.model_dump(),
        "results": results,
        "created_at": start_time.isoformat(),
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="OpenBlog Neo - AI Blog Generation Pipeline"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Company URL"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="+",
        help="Keywords for blog generation"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input JSON file with batch configuration"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory or file path"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Target language code (default: en)"
    )
    parser.add_argument(
        "--market",
        type=str,
        default="US",
        help="Target market code (default: US)"
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip image generation"
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=None,
        help="Max concurrent articles (default: unlimited)"
    )
    parser.add_argument(
        "--export-formats",
        type=str,
        nargs="+",
        default=["html", "json"],
        help="Export formats: html, markdown, json, csv, xlsx, pdf (default: html json)"
    )

    args = parser.parse_args()

    # Get input from file or CLI args
    if args.input:
        with open(args.input, "r") as f:
            config = json.load(f)
        keywords = config.get("keywords", [])
        company_url = config.get("company_url", "")
        language = config.get("language", args.language)
        market = config.get("market", args.market)
    elif args.url and args.keywords:
        keywords = args.keywords
        company_url = args.url
        language = args.language
        market = args.market
    else:
        parser.print_help()
        sys.exit(1)

    # Determine output directory
    output_dir = None
    if args.output:
        output_path = Path(args.output)
        if output_path.is_dir() or args.output.endswith("/"):
            output_dir = output_path
        else:
            output_dir = output_path.parent

    # Run pipeline
    results = asyncio.run(run_pipeline(
        keywords=keywords,
        company_url=company_url,
        language=language,
        market=market,
        skip_images=args.skip_images,
        max_parallel=args.max_parallel,
        output_dir=output_dir,
        export_formats=args.export_formats,
    ))

    # Save output
    if args.output:
        output_path = Path(args.output)
        if output_path.is_dir() or args.output.endswith("/"):
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = output_path / f"pipeline_{results['job_id']}.json"
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_file = output_path

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nOutput saved to: {output_file}")
    else:
        # Print summary to stdout
        print(json.dumps({
            "job_id": results["job_id"],
            "company": results["company"],
            "articles_total": results["articles_total"],
            "articles_successful": results["articles_successful"],
            "duration_seconds": results["duration_seconds"],
        }, indent=2))


if __name__ == "__main__":
    main()

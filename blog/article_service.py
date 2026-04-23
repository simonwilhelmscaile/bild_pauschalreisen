"""Blog article generation service.

Generates blog articles from content opportunities using the full 5-stage
OpenBlog Neo pipeline: write → quality check → URL verification →
internal linking → cleanup/similarity, then renders to HTML.
"""
import copy
import importlib.util
import json
import logging
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional

from db.client import get_beurer_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory generation stage tracking (per article_id)
# Shared dict lives in blog.stage_tracker (lightweight, no heavy imports)
# ---------------------------------------------------------------------------
from .stage_tracker import _active_stages, _set_stage, get_generation_stage


# ---------------------------------------------------------------------------
# Load blog stage modules using importlib (same pattern as blog/pipeline.py)
# The blog stages use sys.path manipulation for sibling imports, so we need
# to add their directories to sys.path before loading them.
# ---------------------------------------------------------------------------
_BLOG_DIR = Path(__file__).parent
_STAGE2_DIR = _BLOG_DIR / "stage2"
_STAGE3_DIR = _BLOG_DIR / "stage3"
_STAGE4_DIR = _BLOG_DIR / "stage4"
_STAGE5_DIR = _BLOG_DIR / "stage5"

for _dir in [_BLOG_DIR, _STAGE2_DIR, _STAGE3_DIR, _STAGE4_DIR, _STAGE5_DIR]:
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_blog_writer = _load_module("blog_writer_mod", _STAGE2_DIR / "blog_writer.py")
_stage_3 = _load_module("stage_3_mod", _STAGE3_DIR / "stage_3.py")
_stage4_models = _load_module("stage4_models_mod", _STAGE4_DIR / "stage4_models.py")
_stage_4 = _load_module("stage_4_mod", _STAGE4_DIR / "stage_4.py")
_stage_5 = _load_module("stage_5_mod", _STAGE5_DIR / "stage_5.py")

# HTML renderer can be imported normally since shared/ is a proper package
from .shared.html_renderer import HTMLRenderer
from .beurer_context import get_beurer_company_context, get_beurer_sitemap_urls, get_existing_article_siblings
from blog.product_catalog import get_product_service_insights


_RELATIVE_LINK_RE = re.compile(r'href="(/(?:web/|de/)[^"]*)"')

_MIN_SECTIONS = 3  # Minimum non-empty sections for a valid article


def _count_sections(article_dict: Dict[str, Any]) -> int:
    """Count non-empty content sections in an article dict."""
    count = 0
    for i in range(1, 10):
        content = article_dict.get(f"section_{i:02d}_content", "")
        if content and len(content.strip()) > 20:
            count += 1
    return count


# Known typo corrections
_TYPO_FIXES = {
    "letzen": "letzten",
}


def _post_pipeline_safety(article: Dict[str, Any], keyword: str) -> Dict[str, Any]:
    """Catch hallucinations that leak through despite category-scoped context.

    Handles issues that can't be fully prevented upstream:
    - Unicode garbage from grounding (zero-width chars)
    - EM 89 wrong specs in prose (grounding can override structured injection)
    - Unknown product SKUs not in the filtered catalog
    - HealthManager Pro / app claims that leak via grounding in TENS articles
    - EM 50/55 mentions that leak via grounding in non-menstrual articles
    - Known typos
    """
    from blog.product_catalog import detect_article_category, get_products_for_category

    category = detect_article_category(keyword)
    logger.info(f"Post-pipeline safety: running for '{keyword}' (category={category})")
    allowed_skus = {p.sku for p in get_products_for_category(category)}

    warnings = []

    # Collect all text fields to scan
    text_fields = ["Intro", "Direct_Answer", "Headline", "Teaser", "Meta_Title", "Meta_Description"]
    for i in range(1, 10):
        text_fields.append(f"section_{i:02d}_title")
        text_fields.append(f"section_{i:02d}_content")
    for i in range(1, 4):
        text_fields.append(f"key_takeaway_{i:02d}")
    for i in range(1, 5):
        text_fields.append(f"paa_{i:02d}_question")
        text_fields.append(f"paa_{i:02d}_answer")
    for i in range(1, 7):
        text_fields.append(f"faq_{i:02d}_question")
        text_fields.append(f"faq_{i:02d}_answer")

    for field_name in text_fields:
        content = article.get(field_name)
        if not isinstance(content, str) or not content:
            continue

        original = content

        # 1. Unicode cleanup: strip zero-width chars
        content = re.sub(r'[\u200b\ufeff\u200c\u200d\u2060\ufffe]', '', content)

        # 2. EM 89 spec corrections in prose
        if "EM 89" in content:
            content = re.sub(r'[Üü]ber 70 Programme', '64 Programme', content)
            content = re.sub(r'70\+?\s*Programme', '64 Programme', content)
            content = re.sub(r'2 (getrennt regelbare?\s*)?Kan[äa]le', '4 Kanäle', content)

        # 3. Typo fixes
        for typo, fix in _TYPO_FIXES.items():
            if typo in content:
                content = content.replace(typo, fix)

        if content != original:
            article[field_name] = content

    # 4. EM 89 spec corrections in tables
    tables = article.get("tables", [])
    if isinstance(tables, list):
        for table in tables:
            if not isinstance(table, dict):
                continue
            rows = table.get("rows", [])
            for row in rows:
                if not isinstance(row, list):
                    continue
                row_text = " ".join(str(c) for c in row)
                if "EM 89" in row_text:
                    for i, cell in enumerate(row):
                        if not isinstance(cell, str):
                            continue
                        cell = re.sub(r'[Üü]ber 70 Programme', '64 Programme', cell)
                        cell = re.sub(r'70\+?\s*Programme', '64 Programme', cell)
                        cell = re.sub(r'2 (getrennt regelbare?\s*)?Kan[äa]le', '4 Kanäle', cell)
                        row[i] = cell

    # 5. Category-specific leak-through checks

    is_pain = category == "pain_therapy"
    is_menstrual = category == "menstrual"
    # App claims should be removed from any non-BP category
    # (pain therapy devices and menstrual devices have no app connectivity)
    _no_app_category = is_pain or is_menstrual

    if _no_app_category:
        # 5a. HealthManager Pro / app claims in non-BP articles
        _app_claims = ["App-Anbindung", "App-Support", "HealthManager Pro",
                       "Bluetooth / App", "Bluetooth/App"]

        # Tables: remove entire rows where a header/label cell contains an app claim
        for table in (article.get("tables") or []):
            if not isinstance(table, dict):
                continue
            original_rows = table.get("rows", [])
            filtered_rows = []
            for row in original_rows:
                if not isinstance(row, list):
                    filtered_rows.append(row)
                    continue
                row_text = " ".join(str(c) for c in row)
                if any(claim in row_text for claim in _app_claims):
                    logger.info(f"Safety: removed table row with app claim in TENS article")
                    continue
                filtered_rows.append(row)
            table["rows"] = filtered_rows

        # List items: remove <li> containing app claims
        for field_name in text_fields:
            content = article.get(field_name)
            if not isinstance(content, str) or "<li>" not in content:
                continue
            for claim in _app_claims:
                if claim in content:
                    content = re.sub(
                        rf'<li>[^<]*{re.escape(claim)}[^<]*</li>',
                        '', content, flags=re.IGNORECASE
                    )
            article[field_name] = content

        # FAQ/PAA: clear entire Q+A pair if either contains app claims
        for i in range(1, 7):
            q_field = f"faq_{i:02d}_question"
            a_field = f"faq_{i:02d}_answer"
            qa_text = (article.get(q_field, "") or "") + (article.get(a_field, "") or "")
            if any(claim in qa_text for claim in _app_claims):
                article[q_field] = ""
                article[a_field] = ""
                logger.info(f"Safety: cleared {q_field}/{a_field} (app claim in TENS FAQ)")
        for i in range(1, 5):
            q_field = f"paa_{i:02d}_question"
            a_field = f"paa_{i:02d}_answer"
            qa_text = (article.get(q_field, "") or "") + (article.get(a_field, "") or "")
            if any(claim in qa_text for claim in _app_claims):
                article[q_field] = ""
                article[a_field] = ""
                logger.info(f"Safety: cleared {q_field}/{a_field} (app claim in TENS PAA)")

        # Key takeaways: clear if contains app claims
        for i in range(1, 4):
            field = f"key_takeaway_{i:02d}"
            if any(claim in (article.get(field, "") or "") for claim in _app_claims):
                article[field] = ""
                logger.info(f"Safety: cleared {field} (app claim in TENS takeaway)")

        # Section/Intro prose: remove sentences/paragraphs containing app claims
        _prose_fields = ["Intro", "Direct_Answer"] + [f"section_{i:02d}_content" for i in range(1, 10)]
        for field_name in _prose_fields:
            content = article.get(field_name)
            if not isinstance(content, str) or not content:
                continue
            original_content = content
            for claim in _app_claims:
                if claim not in content:
                    continue
                # Remove <a> links containing the claim first
                content = re.sub(
                    rf'<a[^>]*>[^<]*{re.escape(claim)}[^<]*</a>',
                    '', content, flags=re.IGNORECASE
                )
                # Remove whole <p> blocks containing the claim
                if claim in content:
                    content = re.sub(
                        rf'<p>(?:[^<]|<(?!/p>))*{re.escape(claim)}(?:[^<]|<(?!/p>))*</p>',
                        '', content, flags=re.IGNORECASE
                    )
                # Remove standalone sentences containing the claim
                if claim in content:
                    content = re.sub(
                        rf'[^.!?]*{re.escape(claim)}[^.!?]*[.!?]\s*',
                        '', content
                    )
            if content != original_content:
                content = re.sub(r'<p>\s*</p>', '', content)
                content = re.sub(r'<ul>\s*</ul>', '', content)
                article[field_name] = content
                logger.info(f"Safety: removed app claim content from {field_name}")
            if any(claim in content for claim in _app_claims):
                warnings.append(f"App claim still in {field_name} after removal attempt")

    if is_pain and not is_menstrual:
        # 5b. EM 50/EM 55 in non-menstrual TENS articles
        _menstrual_skus = ["EM 50", "EM 55"]

        # Tables: remove rows containing EM 50/55
        for table in (article.get("tables") or []):
            if not isinstance(table, dict):
                continue
            original_rows = table.get("rows", [])
            filtered_rows = []
            for row in original_rows:
                if not isinstance(row, list):
                    filtered_rows.append(row)
                    continue
                row_text = " ".join(str(c) for c in row)
                if any(sku in row_text for sku in _menstrual_skus):
                    logger.info(f"Safety: removed table row containing menstrual device in TENS article")
                    continue
                filtered_rows.append(row)
            table["rows"] = filtered_rows

        # Images: clear EM 50/55 product images
        for slot in ["image_02", "image_03"]:
            alt = (article.get(f"{slot}_alt_text") or "").lower()
            if any(sku.lower().replace(" ", "") in alt.replace(" ", "") for sku in _menstrual_skus):
                logger.info(f"Safety: cleared {slot} (menstrual device in TENS article)")
                article[f"{slot}_url"] = ""
                article[f"{slot}_alt_text"] = ""

        # List items: remove <li> containing EM 50/55
        for field_name in text_fields:
            content = article.get(field_name)
            if not isinstance(content, str) or "<li>" not in content:
                continue
            for sku in _menstrual_skus:
                if sku in content:
                    content = re.sub(
                        rf'<li>[^<]*{re.escape(sku)}[^<]*</li>',
                        '', content, flags=re.IGNORECASE
                    )
            article[field_name] = content

        # Prose: flag as warning
        for field_name in text_fields:
            content = article.get(field_name)
            if not isinstance(content, str):
                continue
            for sku in _menstrual_skus:
                if sku in content:
                    warnings.append(f"'{sku}' found in {field_name} (non-menstrual TENS article)")

    # 6. Clear product images from wrong category
    for slot in ["image_02", "image_03"]:
        alt = (article.get(f"{slot}_alt_text") or "")
        for match in re.finditer(r'\b(BM|BC|EM|IL)\s?(\d{2,3})\b', alt):
            sku = f"{match.group(1)} {match.group(2)}"
            if sku not in allowed_skus:
                logger.info(f"Safety: cleared {slot} (cross-category product {sku})")
                article[f"{slot}_url"] = ""
                article[f"{slot}_alt_text"] = ""
                break

    # 6b. Cross-category product removal in prose
    # Remove sentences mentioning products from the wrong category
    if category != "general":
        _wrong_prefixes = {"blood_pressure": ["EM", "IL", "BR"], "pain_therapy": ["BM", "BC", "BR"], "menstrual": ["BM", "BC", "IL", "BR"]}.get(category, [])
        if _wrong_prefixes:
            _prose_fields = ["Intro", "Direct_Answer"] + [f"section_{i:02d}_content" for i in range(1, 10)]
            for field_name in _prose_fields:
                content = article.get(field_name)
                if not isinstance(content, str) or not content:
                    continue
                original_content = content
                for prefix in _wrong_prefixes:
                    # Remove <strong> wrapped wrong SKUs
                    content = re.sub(
                        rf'<strong>[^<]*\b{prefix}\s*\d{{2,3}}\b[^<]*</strong>',
                        '', content, flags=re.IGNORECASE
                    )
                    # Remove sentences mentioning wrong-category SKUs
                    content = re.sub(
                        rf'[^.!?<]*\b{prefix}\s*\d{{2,3}}\b[^.!?<]*[.!?]\s*',
                        '', content
                    )
                # Also remove sentences mentioning Insektenstichheiler
                # Allow HTML tags within the sentence (e.g. <strong>Insektenstichheiler</strong>)
                if re.search(r'insektenstich', content, re.IGNORECASE):
                    content = re.sub(
                        r'(?:[^.!?]|<[^>]*>)*[Ii]nsektenstich(?:[^.!?]|<[^>]*>)*[.!?]\s*',
                        '', content
                    )
                if content != original_content:
                    content = re.sub(r'<p>\s*</p>', '', content)
                    content = re.sub(r'\s{2,}', ' ', content)
                    article[field_name] = content
                    logger.info(f"Safety: removed cross-category product mention from {field_name}")

    # 7. Unknown product SKU check
    all_text = json.dumps(article, ensure_ascii=False)
    for match in re.finditer(r'\b(BM|BC|EM|IL)\s?(\d{2,3})\b', all_text):
        sku = f"{match.group(1)} {match.group(2)}"
        if sku not in allowed_skus:
            warnings.append(f"Unknown product '{sku}' found (not in {category} catalog)")

    # 7. Source quality gate — drop generic descriptions and own-site URLs
    _generic_src_re = re.compile(r"^Source:\s+.+\s+.{1,3}\s+relevant to\s+", re.IGNORECASE)
    sources = article.get("Sources", [])
    if isinstance(sources, list) and sources:
        good_sources = [
            s for s in sources
            if isinstance(s, dict)
            and not _generic_src_re.match(s.get("description", ""))
            and "beurer.com" not in (s.get("url", "") or "").lower()
        ]
        # Keep all non-generic sources (description length already checked upstream)
        if good_sources:
            sources = good_sources
        elif sources:
            sources = sources[:1]  # Keep first source as fallback
        if len(sources) < len(article.get("Sources", [])):
            logger.info(f"Safety: dropped {len(article['Sources']) - len(sources)} sources with generic descriptions")
        article["Sources"] = sources

    # 8. Final blanket sweep: remove any remaining HealthManager/app traces in non-BP articles
    #    Google Search grounding keeps injecting these despite all targeted fixes.
    if _no_app_category:
        _hm_patterns = [
            # <a> links to HealthManager Pro page
            re.compile(r'<a[^>]*healthmanager[^>]*>[^<]*</a>', re.IGNORECASE),
            # <strong>beurer HealthManager Pro</strong> inline
            re.compile(r'<strong>[^<]*HealthManager[^<]*</strong>', re.IGNORECASE),
            # Standalone mentions: "beurer HealthManager Pro", "HealthManager Pro App"
            re.compile(r'(?:beurer\s+)?HealthManager\s*Pro(?:\s+App)?', re.IGNORECASE),
            # Whole sentences mentioning HealthManager (catches proactive disclaimers)
            re.compile(r'[^.!?<]*HealthManager[^.!?<]*[.!?]\s*', re.IGNORECASE),
        ]
        all_fields = list(article.keys())
        for field_name in all_fields:
            val = article.get(field_name)
            if not isinstance(val, str) or not re.search(r'HealthManager', val, re.IGNORECASE):
                continue
            original = val
            for pat in _hm_patterns:
                val = pat.sub('', val)
            # Clean up leftover artifacts
            val = re.sub(r',\s*,', ',', val)  # double commas
            val = re.sub(r'\s{2,}', ' ', val)  # double spaces
            val = re.sub(r'<p>\s*</p>', '', val)  # empty paragraphs
            val = re.sub(r'<li>\s*</li>', '', val)  # empty list items
            if val != original:
                article[field_name] = val
                logger.info(f"Safety: blanket-removed HealthManager reference from {field_name}")

    # Log warnings
    for w in warnings:
        logger.warning(f"Post-pipeline safety: {w}")

    return article


def _rewrite_relative_links(article_dict: Dict[str, Any], base_url: str):
    """Rewrite relative href paths to absolute URLs in article content.

    Stage 5 normalizes sitemap URLs to relative paths (e.g. /de/...).
    Since articles are served from the dashboard, not beurer.com, these
    relative links resolve against the wrong domain. This rewrites them
    to absolute URLs pointing to the correct site.

    Also fixes LLM-injected spaces in URLs (e.g. 'https://www. beurer. com/')
    so that spaced URLs are cleaned before being stored in the database.
    """
    _repl = lambda m: f'href="{base_url}{m.group(1)}"'

    # Handle Sections array format
    for section in article_dict.get("Sections", article_dict.get("sections", [])):
        for key in ("Body", "body"):
            if key in section and section[key]:
                section[key] = _fix_spaced_urls(section[key])
                section[key] = _RELATIVE_LINK_RE.sub(_repl, section[key])

    # Handle flat section_NN_content format
    for key in list(article_dict.keys()):
        if key.startswith("section_") and key.endswith("_content"):
            val = article_dict[key]
            if val and isinstance(val, str):
                val = _fix_spaced_urls(val)
                article_dict[key] = _RELATIVE_LINK_RE.sub(_repl, val)

    # Also handle Intro, TLDR, Direct_Answer which may contain links
    for key in ("Intro", "intro", "TLDR", "Direct_Answer"):
        if key in article_dict and isinstance(article_dict[key], str):
            article_dict[key] = _fix_spaced_urls(article_dict[key])
            article_dict[key] = _RELATIVE_LINK_RE.sub(_repl, article_dict[key])

    # Fix spaced URLs in Sources list (Gemini hallucinates spaces in domains)
    for src in article_dict.get("Sources", []):
        if isinstance(src, dict) and src.get("url"):
            url = src["url"]
            if " " in url:
                url = re.sub(r"\s+", "", url)
            for wrong in ("Beurer.Com", "Beurer.com", "beurer.Com"):
                url = url.replace(wrong, "beurer.com")
            src["url"] = url

    # Fix spaced URLs in FAQ/PAA answers which may also contain links
    for prefix in ("faq_", "paa_"):
        for i in range(1, 7):
            key = f"{prefix}{i:02d}_answer"
            if key in article_dict and isinstance(article_dict[key], str):
                article_dict[key] = _fix_spaced_urls(article_dict[key])
                article_dict[key] = _RELATIVE_LINK_RE.sub(_repl, article_dict[key])


def _fix_spaced_urls(html: str) -> str:
    """Fix URLs with spaces injected by LLM (e.g. 'https://www. Beurer. Com/')."""
    def _clean_href(m):
        url = m.group(1)
        changed = False
        if " " in url:
            url = re.sub(r"\s+", "", url)
            changed = True
        # Fix wrong domain casing (e.g. Beurer.Com → beurer.com)
        if "Beurer.Com" in url or "Beurer.com" in url or "beurer.Com" in url:
            url = url.replace("Beurer.Com", "beurer.com").replace("Beurer.com", "beurer.com").replace("beurer.Com", "beurer.com")
            changed = True
        if changed:
            return 'href="' + url + '"'
        return m.group(0)
    return re.sub(r'href="([^"]+)"', _clean_href, html)


def _rewrite_html_links(html: str, base_url: str) -> str:
    """Rewrite relative links and fix spaced URLs in final rendered HTML."""
    html = _fix_spaced_urls(html)
    return _RELATIVE_LINK_RE.sub(
        lambda m: f'href="{base_url}{m.group(1)}"', html
    )


def _fetch_author(supabase, author_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch author from blog_authors table. Returns None if not found or table missing."""
    if not author_id:
        return None
    try:
        result = (
            supabase.table("blog_authors")
            .select("name, title, bio, image_url, credentials, linkedin_url")
            .eq("id", author_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


async def _run_stages_4_5_cleanup(
    article_dict: Dict[str, Any],
    keyword: str,
    article_id: str,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Run pipeline stages 4, 5, cleanup, and similarity on an article.

    Returns (final_article_dict, pipeline_reports).
    """
    pipeline_reports: Dict[str, Any] = {}

    # Stage 4: URL verification
    _set_stage(article_id, "url_verification")
    logger.info(f"Stage 4: Verifying URLs for '{keyword}'")
    try:
        stage4_input = _stage4_models.Stage4Input(
            article=copy.deepcopy(article_dict),
            keyword=keyword,
            company_name="Beurer",
        )
        stage4_output = await _stage_4.run_stage_4(stage4_input)
        article_dict = copy.deepcopy(stage4_output.article)
        pipeline_reports["stage4"] = {
            "total_urls": stage4_output.total_urls,
            "valid_urls": stage4_output.valid_urls,
            "dead_urls": stage4_output.dead_urls,
            "replaced_urls": stage4_output.replaced_urls,
        }
        logger.info(
            f"Stage 4: Verified {stage4_output.total_urls} URLs, "
            f"replaced {stage4_output.replaced_urls}"
        )
    except Exception as e:
        logger.warning(f"Stage 4 failed (non-blocking): {e}")
        pipeline_reports["stage4"] = {"error": str(e)}

    # Post-Stage-4 source recovery: if sources dropped below 3, supplement
    sources = article_dict.get("Sources", [])
    if isinstance(sources, list) and len(sources) < 3:
        logger.info(f"Post-Stage-4: only {len(sources)} sources remain, supplementing...")
        try:
            from .stage2.blog_writer import _build_verified_sources
            from core.gemini_client import GeminiClient as _GC
            from core.config import ServiceType as _ST
            _client = _GC(service_type=_ST.BLOG)

            recovered = await _build_verified_sources(
                client=_client,
                keyword=keyword,
                headline=article_dict.get("Headline", keyword),
                ai_sources=sources,
                grounding_sources=[],
            )
            if len(recovered) > len(sources):
                article_dict["Sources"] = recovered
                logger.info(f"Post-Stage-4: recovered to {len(recovered)} sources")
                pipeline_reports["source_recovery"] = {
                    "before": len(sources),
                    "after": len(recovered),
                }
        except Exception as e:
            logger.warning(f"Post-Stage-4 source recovery failed (non-blocking): {e}")

    # Filter non-professional sources (Reddit, forums, social media)
    _BLOCKED_SOURCE_DOMAINS = [
        "reddit.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
        "tiktok.com", "youtube.com", "quora.com", "gutefrage.net", "stackoverflow.com",
        "forum.", "community.", "discuss.",
    ]
    sources = article_dict.get("Sources", [])
    if isinstance(sources, list):
        filtered = [
            s for s in sources
            if isinstance(s, dict) and not any(
                blocked in (s.get("url", "") or "").lower()
                for blocked in _BLOCKED_SOURCE_DOMAINS
            )
        ]
        if len(filtered) < len(sources):
            removed = len(sources) - len(filtered)
            logger.info(f"Removed {removed} non-professional source(s) (Reddit/forums/social)")
            article_dict["Sources"] = filtered

    # Stage 5: Internal linking
    _set_stage(article_id, "internal_linking")
    logger.info(f"Stage 5: Adding internal links for '{keyword}'")
    try:
        from blog.product_catalog import detect_article_category as _detect_cat
        _category = _detect_cat(keyword)
        sitemap = get_beurer_sitemap_urls(category=_category)
        siblings = get_existing_article_siblings(keyword, limit=10)
        logger.info(f"  Found {len(siblings)} sibling articles for internal linking")

        # Load catalog once for Stage 5 + Stage 5.5
        _catalog = None
        try:
            from .product_catalog import load_catalog, apply_product_validation
            _catalog = load_catalog()
        except Exception:
            pass

        # Category overview URL filtered to the article's category.
        # Briefing rule: internal links default to the category overview page,
        # not individual products. Only pass the ONE matching category URL.
        _category_overview = (
            _catalog.get_category_overview_url(_category, keyword=keyword) if _catalog else None
        )
        _catalog_category_urls = [_category_overview] if _category_overview else []
        # Only include product URLs from the article's category (prevents cross-category links)
        if _catalog:
            from .product_catalog import get_products_for_category as _get_prods
            _category_products = _get_prods(_category, _catalog)
            _catalog_product_urls = [p.url for p in _category_products if p.url]
        else:
            _catalog_product_urls = []

        import asyncio as _asyncio
        stage5_output = await _asyncio.wait_for(_stage_5.run_stage_5({
            "article": copy.deepcopy(article_dict),
            "current_href": f"/blog/{keyword.lower().replace(' ', '-')}",
            "company_url": "https://www.beurer.com",
            "keyword": keyword,
            "batch_siblings": siblings,
            "sitemap_blog_urls": sitemap.get("blog_urls", [])[:50],
            "sitemap_resource_urls": sitemap.get("resource_urls", [])[:20],
            "sitemap_tool_urls": sitemap.get("tool_urls", []),
            "sitemap_product_urls": _catalog_product_urls or sitemap.get("product_urls", [])[:10],
            "sitemap_service_urls": sitemap.get("service_urls", [])[:5],
            "sitemap_category_urls": _catalog_category_urls,
        }), timeout=120)  # 2 minute timeout for internal linking
        article_dict = copy.deepcopy(stage5_output["article"])
        # Stage 5 normalizes URLs to relative paths (/web/de/...) which
        # resolve against the dashboard domain instead of beurer.com.
        # Rewrite them to absolute URLs.
        _rewrite_relative_links(article_dict, "https://www.beurer.com")
        pipeline_reports["stage5"] = {
            "links_added": stage5_output.get("links_added", 0),
        }
        logger.info(f"Stage 5: Added {stage5_output.get('links_added', 0)} internal links")
    except Exception as e:
        logger.warning(f"Stage 5 failed (non-blocking): {e}")
        pipeline_reports["stage5"] = {"error": str(e)}

    # Always fix spaced URLs and rewrite relative links, even if Stage 5 failed.
    # Gemini's Stage 2 output often has broken URLs like "www. Beurer. Com".
    _rewrite_relative_links(article_dict, "https://www.beurer.com")

    # Strip cross-category product links that Stage 5 may have injected.
    # The LLM sometimes picks product URLs from the wrong category despite instructions.
    try:
        from .product_catalog import detect_article_category as _det_cat, get_products_for_category as _get_cat_prods, load_catalog as _load_cat_links
        _link_category = _det_cat(keyword)
        _link_catalog = _load_cat_links()
        if _link_catalog and _link_category != "general":
            _allowed_product_urls = {p.url.rstrip('/') for p in _get_cat_prods(_link_category, _link_catalog) if p.url}
            _all_product_urls = {p.url.rstrip('/') for p in _link_catalog.products.values() if p.url}
            _wrong_urls = _all_product_urls - _allowed_product_urls
            if _wrong_urls:
                _link_fields = ["Intro", "Direct_Answer"] + [f"section_{i:02d}_content" for i in range(1, 10)]
                _links_removed = 0
                for _field in _link_fields:
                    content = article_dict.get(_field)
                    if not isinstance(content, str) or '<a ' not in content:
                        continue
                    original = content
                    for _wrong_url in _wrong_urls:
                        # Remove <a href="...wrong_url...">anchor text</a> but keep the anchor text
                        content = re.sub(
                            rf'<a[^>]*href="[^"]*{re.escape(_wrong_url.split("/de/")[-1])}[^"]*"[^>]*>(.*?)</a>',
                            r'\1', content, flags=re.DOTALL
                        )
                    if content != original:
                        article_dict[_field] = content
                        _links_removed += 1
                if _links_removed:
                    logger.info(f"Post-Stage-5: removed cross-category product links from {_links_removed} fields")
    except Exception as e:
        logger.warning(f"Cross-category link cleanup failed (non-blocking): {e}")

    # Fallback: if Stage 5 failed or added 0 links, inject the category overview link
    # directly. This ensures Bug 12's "default to category page" rule is always met.
    try:
        from blog.product_catalog import detect_article_category as _detect_cat2, load_catalog as _load_cat2
        _cat2 = _detect_cat2(keyword)
        _cat2_catalog = _load_cat2()
        _cat2_url = _cat2_catalog.get_category_overview_url(_cat2, keyword=keyword) if _cat2_catalog else None
        if _cat2_url:
            from urllib.parse import urlparse as _urlparse
            _cat2_path = _urlparse(_cat2_url).path
            # Check if any link already points to the category
            all_text = " ".join(str(v) for v in article_dict.values() if isinstance(v, str))
            if _cat2_path not in all_text:
                from blog.stage5.stage_5 import InternalLinker
                _tmp_linker = InternalLinker.__new__(InternalLinker)
                if _tmp_linker._inject_category_link(article_dict, _cat2_path, keyword=keyword):
                    _rewrite_relative_links(article_dict, "https://www.beurer.com")
                    logger.info(f"Fallback: injected category overview link {_cat2_path}")
    except Exception as e2:
        logger.warning(f"Fallback category link failed: {e2}")

    # Fallback: if fewer than 3 internal links, inject product links deterministically
    try:
        all_html = " ".join(str(v) for v in article_dict.values() if isinstance(v, str))
        existing_beurer_links = len(re.findall(r'href="[^"]*beurer\.com[^"]*"', all_html))
        if existing_beurer_links < 3 and _catalog:
            from .product_catalog import get_products_for_category as _get_fallback_prods
            _fb_prods = _get_fallback_prods(_category, _catalog)
            _fb_urls_used = set(re.findall(r'href="[^"]*(beurer\.com[^"]*)"', all_html))
            _fb_candidates = [p for p in _fb_prods if p.url and not any(p.url.rstrip('/') in u for u in _fb_urls_used)]
            _fb_candidates.sort(key=lambda p: p.priority or 99)
            _fb_added = 0
            _prose_fields = ["Intro"] + [f"section_{i:02d}_content" for i in range(1, 7)]
            for p in _fb_candidates[:3]:
                if existing_beurer_links + _fb_added >= 3:
                    break
                # Find a mention of the product SKU in the article text and wrap it
                for field in _prose_fields:
                    content = article_dict.get(field)
                    if not isinstance(content, str) or p.sku not in content:
                        continue
                    # Skip if already wrapped in an <a> tag
                    if f'>{p.sku}</a>' in content:
                        continue
                    abs_url = f"https://www.beurer.com{p.url}" if p.url.startswith('/') else p.url
                    article_dict[field] = content.replace(
                        p.sku,
                        f'<a href="{abs_url}">{p.sku}</a>',
                        1  # Only first occurrence
                    )
                    _fb_added += 1
                    logger.info(f"Link fallback: wrapped {p.sku} with product link in {field}")
                    break
            if _fb_added:
                _rewrite_relative_links(article_dict, "https://www.beurer.com")
                logger.info(f"Link fallback: injected {_fb_added} additional product links (total now {existing_beurer_links + _fb_added})")
    except Exception as e:
        logger.warning(f"Link fallback failed (non-blocking): {e}")

    # Stage 5.5: Product validation (deterministic, no LLM)
    _set_stage(article_id, "product_validation")
    try:
        if _catalog:
            validation_report = apply_product_validation(article_dict, _catalog)
            pipeline_reports["product_validation"] = validation_report
            logger.info(
                f"Stage 5.5: Validated products — "
                f"{validation_report['replacements_made']} replacements, "
                f"{validation_report['links_rewritten']} links rewritten"
            )
    except Exception as e:
        logger.warning(f"Stage 5.5 product validation failed (non-blocking): {e}")
        pipeline_reports["product_validation"] = {"error": str(e)}

    # Cleanup: HTML cleanup and validation
    _set_stage(article_id, "cleanup")
    try:
        from .stage_cleanup import run_cleanup

        cleanup_result = run_cleanup(article_dict)
        pipeline_reports["cleanup"] = {
            "fields_cleaned": cleanup_result.fields_cleaned,
            "valid": cleanup_result.valid,
            "warnings": cleanup_result.warnings,
        }
        logger.info(f"Cleanup: Cleaned {cleanup_result.fields_cleaned} fields")
    except Exception as e:
        logger.warning(f"Cleanup failed (non-blocking): {e}")

    # Similarity: Content similarity check
    try:
        from .stage_similarity import run_similarity_check

        similarity_report = run_similarity_check(
            job_id=f"article_{article_id}",
            article_data=article_dict,
            add_to_memory=True,
        )
        if similarity_report:
            pipeline_reports["similarity"] = {
                "similarity_score": similarity_report.similarity_score,
                "is_too_similar": similarity_report.is_too_similar,
            }
            if similarity_report.is_too_similar:
                logger.warning(
                    f"Similarity: Content similarity {similarity_report.similarity_score * 100:.1f}%"
                )
    except Exception as e:
        logger.warning(f"Similarity check failed (non-blocking): {e}")

    return article_dict, pipeline_reports


async def _generate_article_images(article: dict, article_id: str) -> dict:
    """Generate hero image and map product images inline in the pipeline.

    Modifies article dict in-place with image URLs.
    Hero image: Imagen 4.0 with one retry on failure.
    Product images: Supabase Storage URL lookup.
    """
    import asyncio as _aio
    from .stage_tracker import _set_stage

    _set_stage(article_id, "images")

    # Hero image generation with one retry
    try:
        from .stage2.image_prompts import build_beurer_hero_prompt, detect_theme, select_lifestyle_reference
        from .stage2.image_creator import ImageCreator

        theme = detect_theme(article)
        style_ref = select_lifestyle_reference(article, theme)
        prompt = build_beurer_hero_prompt(article, style_ref=style_ref)
        logger.info(f"Generating hero image for '{article_id}' — theme: {theme}")

        creator = ImageCreator()
        image_url = await creator.generate_async(prompt, aspect_ratio="16:9")

        if not image_url:
            logger.warning(f"Hero image attempt 1 failed for '{article_id}', retrying in 2s...")
            await _aio.sleep(2)
            image_url = await creator.generate_async(prompt, aspect_ratio="16:9")

        if image_url:
            headline = article.get("Headline", "") or article.get("headline", "")
            alt_text = f"Beurer Magazin: {headline}"
            if len(alt_text) > 125:
                alt_text = alt_text[:122] + "..."
            article["image_01_url"] = image_url
            article["image_01_alt_text"] = alt_text
            logger.info(f"Hero image set for '{article_id}': {image_url[:80]}...")
        else:
            logger.warning(f"Hero image generation failed after retry for '{article_id}'")
    except Exception as e:
        logger.error(f"Hero image generation error for '{article_id}': {e}")

    # Product image mapping
    try:
        from .stage2.image_prompts import find_product_images
        matches = find_product_images(article)
        for i, match in enumerate(matches[:2]):
            slot = f"image_0{i + 2}"
            article[f"{slot}_url"] = match["url"]
            article[f"{slot}_alt_text"] = f"Beurer {match['model']}"
            logger.info(f"Product image {slot} set: {match['model']}")
    except Exception as e:
        logger.error(f"Product image mapping error for '{article_id}': {e}")

    return article


async def generate_article(
    article_id: str,
    source_item_id: str,
    keyword: str,
    language: str = "de",
    word_count: int = 1500,
    social_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a blog article using the full 5-stage pipeline and update the DB row.

    Called as a background task — the row with article_id already exists
    with status='generating'.

    Args:
        article_id: Pre-created blog_articles row ID.
        source_item_id: FK to social_items.
        keyword: SEO keyword for the article.
        language: Article language ('de' or 'en').
        word_count: Target word count.
        social_context: Optional context from the content opportunity.

    Returns:
        Updated article dict.
    """
    supabase = get_beurer_supabase()

    try:
        # Auto-link with sibling articles in other languages (same keyword)
        from uuid import uuid4
        article_group_id = None
        try:
            sibling_result = supabase.table("blog_articles") \
                .select("id, article_group_id") \
                .eq("keyword", keyword) \
                .neq("language", language) \
                .limit(1).execute()
            if sibling_result.data:
                sib = sibling_result.data[0]
                article_group_id = sib.get("article_group_id")
                if not article_group_id:
                    article_group_id = str(uuid4())
                    supabase.table("blog_articles") \
                        .update({"article_group_id": article_group_id}) \
                        .eq("id", sib["id"]).execute()
        except Exception as e:
            logger.warning(f"Article group linking failed (non-blocking): {e}")

        # Build company context
        company_context = get_beurer_company_context(language, keyword=keyword)

        # Build keyword instructions from social context
        keyword_instructions = _build_instructions_from_context(
            social_context, language
        )

        # Inject known product issues if the keyword references a product
        from blog.product_catalog import find_product_for_keyword, get_product_known_issues
        product_model = find_product_for_keyword(keyword)
        if product_model:
            known_issues = get_product_known_issues(product_model)
            if known_issues:
                is_de = language.startswith("de")
                issues_lines = [f"- [{i['severity'].upper()}] {i['issue']}" for i in known_issues]
                issues_block = "\n".join(issues_lines)
                if is_de:
                    issues_section = (
                        f"\n\n## Bekannte Produkt-Hinweise (interne Quelle)\n{issues_block}\n"
                        "Berücksichtige diese Information im Artikel: erwähne das Problem sachlich, "
                        "biete Workarounds an falls bekannt, und vermeide Heilversprechen."
                    )
                else:
                    issues_section = (
                        f"\n\n## Known Product Issues (internal source)\n{issues_block}\n"
                        "Consider this information in the article: mention the issue factually, "
                        "offer workarounds if known, and avoid healing promises."
                    )
                keyword_instructions = (keyword_instructions or "") + issues_section

        # Enrich with service case insights if available
        product_model = (social_context or {}).get("matched_products", [""])[0] if social_context else ""
        if product_model:
            service_insights = get_product_service_insights(product_model)
            if service_insights:
                keyword_instructions = (keyword_instructions or "") + "\n\n" + service_insights

        # Fetch global rules and sibling articles for Stage 2 awareness
        from .beurer_context import get_global_rules, get_existing_article_siblings as _get_siblings
        _global_rules = get_global_rules()
        _sibling_articles = _get_siblings(keyword, limit=10)
        if _global_rules:
            logger.info(f"Injecting {len(_global_rules)} global rules into Stage 2")
        if _sibling_articles:
            logger.info(f"Injecting {len(_sibling_articles)} sibling articles into Stage 2")

        # Stage 2: Write article (with retry on truncated output)
        _set_stage(article_id, "writing")
        logger.info(f"Stage 2: Writing article for keyword '{keyword}'")
        is_de = language.startswith("de")
        country = "Germany" if is_de else "United Kingdom"

        # Enforce language in keyword instructions when language != keyword language
        if not is_de:
            lang_enforce = (
                "\n\nCRITICAL: Write the ENTIRE article in English. "
                "Even if the keyword is in German, ALL output — headline, meta title, "
                "meta description, intro, sections, FAQs, PAAs — MUST be in English. "
                "Do NOT write in German."
            )
            keyword_instructions = (keyword_instructions or "") + lang_enforce

        article_output = await _blog_writer.write_article(
            keyword=keyword,
            company_context=company_context,
            word_count=word_count,
            language=language,
            country=country,
            keyword_instructions=keyword_instructions,
            global_rules=_global_rules,
            sibling_articles=_sibling_articles,
        )
        article_dict = article_output.model_dump()

        sections_count = _count_sections(article_dict)
        if sections_count < _MIN_SECTIONS:
            logger.warning(
                f"Stage 2 returned only {sections_count} sections (min {_MIN_SECTIONS}), retrying..."
            )
            article_output = await _blog_writer.write_article(
                keyword=keyword,
                company_context=company_context,
                word_count=word_count,
                language=language,
                country=country,
                keyword_instructions=keyword_instructions,
                global_rules=_global_rules,
                sibling_articles=_sibling_articles,
            )
            article_dict = article_output.model_dump()
            sections_count = _count_sections(article_dict)
            logger.info(f"Stage 2 retry: {sections_count} sections")

        # Stage 3: Quality check and fixes
        _set_stage(article_id, "quality_check")
        logger.info(f"Stage 3: Quality checking article for '{keyword}'")
        import asyncio as _asyncio
        try:
            stage3_result = await _asyncio.wait_for(_stage_3.run_stage_3({
                "article": article_dict,
                "keyword": keyword,
                "language": language,
            }), timeout=120)
        except Exception as e:
            logger.warning(f"Stage 3 failed (non-blocking): {e}")
            stage3_result = {"article": article_dict, "fixes_applied": 0}
        fixed_article = stage3_result.get("article", article_dict)
        pipeline_reports: Dict[str, Any] = {
            "stage3": {
                "fixes_applied": stage3_result.get("fixes_applied", 0),
            },
        }

        # Stages 4, 5, cleanup, similarity
        fixed_article, extra_reports = await _run_stages_4_5_cleanup(
            fixed_article, keyword, article_id
        )
        pipeline_reports.update(extra_reports)

        # Post-pipeline safety: strip known-bad content
        fixed_article = _post_pipeline_safety(fixed_article, keyword)

        # Generate images (hero + product) inline
        fixed_article = await _generate_article_images(fixed_article, article_id)

        # Fetch author if assigned
        author_data = None
        try:
            article_row = supabase.table("blog_articles").select("author_id").eq("id", article_id).limit(1).execute()
            author_id = article_row.data[0].get("author_id") if article_row.data else None
            author_data = _fetch_author(supabase, author_id)
        except Exception:
            pass  # author_id column may not exist yet

        # Fetch hreflang siblings for HTML rendering
        hreflang_siblings = []
        if article_group_id:
            try:
                siblings_result = supabase.table("blog_articles") \
                    .select("language, publish_url") \
                    .eq("article_group_id", article_group_id) \
                    .not_.is_("publish_url", "null") \
                    .execute()
                hreflang_siblings = [
                    {"language": s["language"], "url": s["publish_url"]}
                    for s in (siblings_result.data or [])
                    if s.get("publish_url")
                ]
            except Exception as e:
                logger.warning(f"hreflang sibling lookup failed: {e}")

        # Render to HTML
        _set_stage(article_id, "rendering")
        logger.info(f"Rendering HTML for '{keyword}'")
        article_category = (social_context or {}).get("category", "")
        article_html = HTMLRenderer.render(
            article=fixed_article,
            company_name="Beurer",
            company_url="https://www.beurer.com",
            language=language,
            category=article_category,
            author=author_data,
            hreflang_siblings=hreflang_siblings,
        )
        # Safety net: rewrite any remaining relative links in rendered HTML
        article_html = _rewrite_html_links(article_html, "https://www.beurer.com")

        # Extract metadata
        headline = fixed_article.get("Headline", "") or fixed_article.get("headline", "")
        meta_title = (
            fixed_article.get("Meta_Title", "")
            or fixed_article.get("meta_title", "")
        )
        meta_description = (
            fixed_article.get("Meta_Description", "")
            or fixed_article.get("meta_description", "")
        )
        actual_word_count = len(article_html.split())

        # Final URL cleanup: ensure no spaced URLs survive in article_json
        _rewrite_relative_links(fixed_article, "https://www.beurer.com")

        # Store pipeline reports in article_json for transparency
        fixed_article["_pipeline_reports"] = pipeline_reports

        # Update row as completed
        supabase.table("blog_articles").update({
            "status": "completed",
            "headline": headline,
            "meta_title": meta_title,
            "meta_description": meta_description,
            "article_html": article_html,
            "article_json": fixed_article,
            "word_count": actual_word_count,
            "error_message": None,
            "html_custom": False,
            **({"article_group_id": article_group_id} if article_group_id else {}),
        }).eq("id", article_id).execute()

        logger.info(f"Article '{keyword}' completed: {headline}")
        return {"id": article_id, "status": "completed", "headline": headline}

    except Exception as e:
        logger.error(f"Article generation failed for '{keyword}': {e}", exc_info=True)
        supabase.table("blog_articles").update({
            "status": "failed",
            "error_message": str(e)[:2000],
        }).eq("id", article_id).execute()
        return {"id": article_id, "status": "failed", "error_message": str(e)}
    finally:
        _active_stages.pop(article_id, None)


def _build_instructions_from_context(
    social_context: Optional[Dict[str, Any]],
    language: str = "de",
) -> Optional[str]:
    """Build keyword-level instructions from social listening context."""
    if not social_context:
        return None

    is_de = language.startswith("de")
    lines = []

    if is_de:
        lines.append(
            "Dieser Artikel basiert auf echten Nutzerfragen aus dem Social Listening."
        )
    else:
        lines.append(
            "This article is based on real user questions from social listening."
        )
        lines.append(
            "IMPORTANT: Use only English-language sources. Prioritise UK/US health "
            "authorities (NHS, NICE, Mayo Clinic), English-language review sites "
            "(Which?, Trusted Reviews, Healthline), and English forums. "
            "Do NOT cite or translate German-language sources."
        )

    emotion = social_context.get("emotion")
    if emotion:
        if is_de:
            lines.append(f"- Nutzer-Emotion: {emotion} — gehe einfühlsam darauf ein.")
        else:
            lines.append(f"- User emotion: {emotion} — address this empathetically.")

    intent = social_context.get("intent")
    if intent:
        if is_de:
            lines.append(f"- Nutzer-Intention: {intent}")
        else:
            lines.append(f"- User intent: {intent}")

    key_insight = social_context.get("key_insight")
    if key_insight:
        if is_de:
            lines.append(f"- Zentrale Erkenntnis: {key_insight}")
        else:
            lines.append(f"- Key insight: {key_insight}")

    llm_opp = social_context.get("llm_opportunity")
    if llm_opp:
        if is_de:
            lines.append(f"- Content-Chance: {llm_opp}")
        else:
            lines.append(f"- Content opportunity: {llm_opp}")

    snippet = social_context.get("content_snippet")
    if snippet:
        if is_de:
            lines.append(f'- Originale Nutzerfrage: "{snippet[:200]}"')
        else:
            lines.append(f'- Original user question: "{snippet[:200]}"')

    return "\n".join(lines) if len(lines) > 1 else None


async def regenerate_article(
    article_id: str,
    feedback: Optional[str] = None,
    from_scratch: bool = False,
) -> Dict[str, Any]:
    """Regenerate an existing blog article, optionally incorporating feedback.

    Args:
        article_id: Existing blog_articles row ID.
        feedback: User feedback to incorporate into the regenerated article.
        from_scratch: If True, ignore previous article and regenerate fresh.

    Returns:
        Updated article dict.
    """
    import asyncio as _asyncio
    supabase = get_beurer_supabase()

    try:
        # Fetch existing article
        result = (
            supabase.table("blog_articles")
            .select("*")
            .eq("id", article_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return {"id": article_id, "status": "failed", "error_message": "Article not found"}

        article = result.data[0]
        keyword = article["keyword"]
        language = article.get("language", "de")
        social_context = article.get("social_context")
        word_count = article.get("word_count") or 1500

        # Update feedback history
        history: List[Dict] = article.get("feedback_history") or []
        old_article_html = article.get("article_html") or ""
        if feedback:
            history.append({
                "type": "feedback",
                "comment": feedback,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": len(history) + 1,
                "old_article_html": old_article_html,
            })

        # Set status to regenerating + save feedback history
        supabase.table("blog_articles").update({
            "status": "regenerating",
            "feedback_history": history,
        }).eq("id", article_id).execute()

        # Build keyword instructions
        base_instructions = _build_instructions_from_context(social_context, language)

        if not from_scratch and feedback:
            revision_block = (
                f"\n\nREVISION INSTRUCTIONS: The previous article had these issues: "
                f"{feedback}. Please address them in the new version."
            )
            keyword_instructions = (base_instructions or "") + revision_block
        else:
            keyword_instructions = base_instructions

        # Build company context
        company_context = get_beurer_company_context(language, keyword=keyword)

        # Fetch global rules and sibling articles for Stage 2 awareness
        from .beurer_context import get_global_rules, get_existing_article_siblings as _get_siblings
        _global_rules = get_global_rules()
        _sibling_articles = _get_siblings(keyword, limit=10)

        # Stage 2: Write article (with retry on truncated output)
        _set_stage(article_id, "writing")
        logger.info(f"Regenerating article for keyword '{keyword}' (from_scratch={from_scratch})")
        article_output = await _blog_writer.write_article(
            keyword=keyword,
            company_context=company_context,
            word_count=word_count,
            language=language,
            country="Germany",
            keyword_instructions=keyword_instructions,
            global_rules=_global_rules,
            sibling_articles=_sibling_articles,
        )
        article_dict = article_output.model_dump()

        sections_count = _count_sections(article_dict)
        if sections_count < _MIN_SECTIONS:
            logger.warning(
                f"Stage 2 returned only {sections_count} sections (min {_MIN_SECTIONS}), retrying..."
            )
            article_output = await _blog_writer.write_article(
                keyword=keyword,
                company_context=company_context,
                word_count=word_count,
                language=language,
                country="Germany",
                keyword_instructions=keyword_instructions,
                global_rules=_global_rules,
                sibling_articles=_sibling_articles,
            )
            article_dict = article_output.model_dump()
            sections_count = _count_sections(article_dict)
            logger.info(f"Stage 2 retry: {sections_count} sections")

        # Stage 3: Quality check
        _set_stage(article_id, "quality_check")
        logger.info(f"Stage 3: Quality checking regenerated article for '{keyword}'")
        try:
            stage3_result = await _asyncio.wait_for(_stage_3.run_stage_3({
                "article": article_dict,
                "keyword": keyword,
                "language": language,
            }), timeout=120)
        except Exception as e:
            logger.warning(f"Stage 3 failed (non-blocking): {e}")
            stage3_result = {"article": article_dict, "fixes_applied": 0}
        fixed_article = stage3_result.get("article", article_dict)

        # Stages 4, 5, cleanup, similarity
        fixed_article, pipeline_reports = await _run_stages_4_5_cleanup(
            fixed_article, keyword, article_id
        )
        pipeline_reports["stage3"] = {
            "fixes_applied": stage3_result.get("fixes_applied", 0),
        }

        # Post-pipeline safety: strip known-bad content
        try:
            logger.info(f"Running post-pipeline safety for '{keyword}'")
            fixed_article = _post_pipeline_safety(fixed_article, keyword)
            logger.info(f"Post-pipeline safety completed for '{keyword}'")
        except Exception as safety_err:
            logger.error(f"Post-pipeline safety FAILED for '{keyword}': {safety_err}", exc_info=True)

        # Generate images (hero + product) inline
        fixed_article = await _generate_article_images(fixed_article, article_id)

        # Fetch author if assigned
        author_data = _fetch_author(supabase, article.get("author_id"))

        # Render to HTML
        _set_stage(article_id, "rendering")
        regen_category = (social_context or {}).get("category", "")
        article_html = HTMLRenderer.render(
            article=fixed_article,
            company_name="Beurer",
            company_url="https://www.beurer.com",
            language=language,
            category=regen_category,
            author=author_data,
        )
        # Safety net: rewrite any remaining relative links in rendered HTML
        article_html = _rewrite_html_links(article_html, "https://www.beurer.com")

        headline = fixed_article.get("Headline", "") or fixed_article.get("headline", "")
        actual_word_count = len(article_html.split())

        # Final URL cleanup: ensure no spaced URLs survive in article_json
        _rewrite_relative_links(fixed_article, "https://www.beurer.com")

        # Store pipeline reports in article_json
        fixed_article["_pipeline_reports"] = pipeline_reports

        # Update row as completed
        supabase.table("blog_articles").update({
            "status": "completed",
            "headline": headline,
            "meta_title": (
                fixed_article.get("Meta_Title", "")
                or fixed_article.get("meta_title", "")
            ),
            "meta_description": (
                fixed_article.get("Meta_Description", "")
                or fixed_article.get("meta_description", "")
            ),
            "article_html": article_html,
            "article_json": fixed_article,
            "word_count": actual_word_count,
            "error_message": None,
            "html_custom": False,
        }).eq("id", article_id).execute()

        logger.info(f"Article '{keyword}' regenerated: {headline}")
        return {"id": article_id, "status": "completed", "headline": headline}

    except Exception as e:
        logger.error(f"Article regeneration failed for '{article_id}': {e}", exc_info=True)
        supabase.table("blog_articles").update({
            "status": "failed",
            "error_message": str(e)[:2000],
        }).eq("id", article_id).execute()
        return {"id": article_id, "status": "failed", "error_message": str(e)}
    finally:
        _active_stages.pop(article_id, None)


# ---------------------------------------------------------------------------
# Inline edits — targeted passage replacement
# ---------------------------------------------------------------------------

class _TagStripper(HTMLParser):
    """Strip HTML tags, building a char-level mapping from plain->HTML indices."""

    _SKIP_TAGS = frozenset(('style', 'script', 'noscript', 'svg', 'head'))
    # Block-level tags that produce whitespace breaks in rendered text
    _BLOCK_TAGS = frozenset((
        'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'section', 'article', 'header', 'footer', 'tr', 'td', 'th',
    ))

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.plain_chars: List[str] = []
        self.plain_to_html: List[int] = []  # plain index -> HTML offset
        self._html_offset = 0
        self._skip_depth = 0  # > 0 means inside a skipped tag

    def feed(self, data: str):
        self._raw = data
        super().feed(data)

    def _inject_space(self):
        """Insert a whitespace separator between block elements."""
        if self.plain_chars and self.plain_chars[-1] != ' ':
            self.plain_chars.append(' ')
            # Map to the same HTML offset as the tag boundary
            self.plain_to_html.append(self._html_offset)

    def handle_starttag(self, tag, attrs):
        self._html_offset = self.getpos_offset()
        tag_lower = tag.lower()
        if tag_lower in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag_lower in self._BLOCK_TAGS and self._skip_depth == 0:
            self._inject_space()

    def handle_endtag(self, tag):
        self._html_offset = self.getpos_offset()
        tag_lower = tag.lower()
        if tag_lower in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag_lower in self._BLOCK_TAGS and self._skip_depth == 0:
            self._inject_space()

    def handle_data(self, data):
        start = self._raw.find(data, self._html_offset)
        if start == -1:
            start = self._html_offset
        self._html_offset = start + len(data)
        # Skip text inside style/script/head/svg tags
        if self._skip_depth > 0:
            return
        for i, ch in enumerate(data):
            self.plain_chars.append(ch)
            self.plain_to_html.append(start + i)

    def getpos_offset(self):
        line, col = self.getpos()
        offset = 0
        for i, ln in enumerate(self._raw.split('\n')):
            if i == line - 1:
                offset += col
                break
            offset += len(ln) + 1  # +1 for newline
        return offset


def find_html_passage(html: str, plain_text: str) -> Optional[str]:
    """Find the HTML substring that corresponds to *plain_text* after tag stripping.

    The user selects plain text in an iframe, but the underlying HTML may
    contain inline tags (<strong>, <em>, <a>).  We strip tags, locate the
    plain text, then map back to the original HTML to get the tagged version.

    Falls back to a direct substring search if the mapping approach fails.
    """
    if not plain_text or not html:
        return None

    # Normalise whitespace for matching
    needle = re.sub(r'\s+', ' ', plain_text.strip())

    # Fast path: exact match (no inline tags around the passage)
    if needle in html:
        return needle

    # Slow path: strip tags, find in plain text, map back to HTML
    try:
        stripper = _TagStripper()
        stripper.feed(html)
        plain = ''.join(stripper.plain_chars)
        plain_norm = re.sub(r'\s+', ' ', plain)

        idx = plain_norm.find(needle)
        if idx == -1:
            logger.debug(f"Needle not in stripped text. Needle[:80]={needle[:80]!r} "
                         f"plain_norm[:200]={plain_norm[:200]!r}")
            return None

        # Map plain_norm indices back to plain_chars indices (they differ only
        # where multiple whitespace chars were collapsed).
        norm_to_plain: List[int] = []
        pi = 0
        for ch in plain_norm:
            if ch == ' ':
                while pi < len(plain) and plain[pi] not in (' ', '\t', '\n', '\r'):
                    pi += 1
            if pi < len(plain):
                norm_to_plain.append(pi)
                pi += 1
            else:
                norm_to_plain.append(len(plain) - 1)

        start_plain = norm_to_plain[idx]
        end_plain = norm_to_plain[idx + len(needle) - 1]

        start_html = stripper.plain_to_html[start_plain]
        end_html = stripper.plain_to_html[end_plain] + 1

        # Extend end_html to include any closing tags immediately after
        rest = html[end_html:]
        m = re.match(r'((?:</\w+>)+)', rest)
        if m:
            end_html += len(m.group(1))

        return html[start_html:end_html]
    except Exception:
        logger.debug("Tag-stripping passage lookup failed, trying direct search", exc_info=True)

    return None


async def apply_inline_edits(
    article_id: str,
    edits: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Apply targeted inline edits to an article's HTML.

    Each edit is ``{passage_text, comment}``.  A single Gemini call produces
    revised text for every passage; the revisions are applied via string
    replacement on ``article_html``.  ``article_json`` is NOT modified.

    Returns the updated article dict.
    """
    from services.gemini import get_generative_model, CLASSIFICATION_MODEL

    supabase = get_beurer_supabase()

    # Fetch article
    result = (
        supabase.table("blog_articles")
        .select("*")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return {"id": article_id, "status": "failed", "error_message": "Article not found"}

    article = result.data[0]
    article_html = article.get("article_html") or ""
    language = article.get("language", "de")

    # Resolve HTML passages for each edit
    resolved: List[Dict[str, str]] = []
    for edit in edits:
        plain = edit["passage_text"]
        html_passage = find_html_passage(article_html, plain)
        if html_passage:
            resolved.append({
                "original_html": html_passage,
                "plain_text": plain,
                "comment": edit["comment"],
            })
        else:
            logger.warning(f"Could not find passage in HTML: {plain[:80]!r}")

    if not resolved:
        return {
            "id": article_id,
            "status": "completed",
            "article_html": article_html,
            "feedback_history": article.get("feedback_history") or [],
            "edits_applied": 0,
            "changes": [],
        }

    # Build Gemini prompt — always send original_html so Gemini preserves structure
    edits_block = ""
    for i, r in enumerate(resolved, 1):
        edits_block += (
            f"Edit {i}:\n"
            f"  Original HTML: {r['original_html']}\n"
            f"  Comment: {r['comment']}\n\n"
        )

    lang_instruction = (
        "Write the revised text in German." if language.startswith("de")
        else "Write the revised text in English."
    )

    prompt = f"""You are editing specific passages in a blog article based on user feedback.
For each edit below, produce a revised version of the passage that addresses the user's comment.
{lang_instruction}

RULES:
- PRESERVE the exact HTML structure: keep all tags like <h2>, <h3>, <p>, <ul>, <li>, <strong>, <a>, <em>, etc.
- If the original has a heading (<h2>, <h3>), the revised version MUST keep the heading tag.
- If the original has paragraph tags (<p>), keep them in the revision.
- Revised text must be approximately the same length as the original (within 30%). Do not truncate or drastically shorten.
- Revised text must be grammatically complete and connect naturally to the surrounding content.
- Never return a truncated or partial sentence as the revision.
- Keep the same tone and style.
- When asked to change a URL or link, modify the href attribute value in the <a> tag.
- Return valid HTML that can directly replace the original HTML.

{edits_block}
Return ONLY a JSON array (no markdown fences) where each element is an object with "edit_number" (int) and "revised" (string containing HTML).
Example: [{{"edit_number": 1, "revised": "<p>The revised passage text.</p>"}}]"""

    try:
        model = get_generative_model(CLASSIFICATION_MODEL)
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
        revisions = json.loads(raw)
    except Exception as e:
        logger.error(f"Gemini inline-edit call failed: {e}", exc_info=True)
        return {"id": article_id, "status": "failed", "error_message": f"LLM edit failed: {e}"}

    # Import validator
    try:
        from .shared.replacement_validator import validate_replacement as _validate
    except ImportError:
        _validate = None

    # Apply replacements
    edits_applied = 0
    changes = []
    updated_html = article_html
    for rev in revisions:
        idx = rev.get("edit_number")
        revised_text = rev.get("revised", "")
        if idx is None or idx < 1 or idx > len(resolved):
            continue
        original_html = resolved[idx - 1]["original_html"]
        if original_html in updated_html:
            # Validate before applying
            if _validate is not None:
                pos = updated_html.index(original_html)
                ctx_before = updated_html[max(0, pos - 80):pos]
                ctx_after = updated_html[pos + len(original_html):pos + len(original_html) + 80]
                # Only enforce HTML tag balance for inline-tag edits (links),
                # not for multi-paragraph passages which naturally span block boundaries
                spans_blocks = bool(re.search(r'</(?:p|div|li|h[1-6])>', original_html))
                is_html = bool(re.search(r'<a\s', original_html)) and not spans_blocks
                ok, reason = _validate(original_html, revised_text, ctx_before, ctx_after, is_html=is_html)
                if not ok:
                    logger.warning(f"Rejected inline edit {idx}: {reason}")
                    continue
            updated_html = updated_html.replace(original_html, revised_text, 1)
            edits_applied += 1
            changes.append({
                "edit_number": idx,
                "original_snippet": original_html[:200],
                "revised_snippet": revised_text[:200],
            })

    # Update feedback history
    history: List[Dict] = article.get("feedback_history") or []
    edit_summary_parts = [
        f'"{e["plain_text"][:60]}..." \u2192 {e["comment"]}'
        for e in resolved
    ]
    history.append({
        "type": "inline_edit",
        "comment": f"Inline edits ({len(resolved)}): " + "; ".join(edit_summary_parts),
        "edits_applied": edits_applied,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": len(history) + 1,
        "changes": changes,
    })

    # Save to DB
    supabase.table("blog_articles").update({
        "article_html": updated_html,
        "feedback_history": history,
        "html_custom": True,
    }).eq("id", article_id).execute()

    return {
        "id": article_id,
        "status": "completed",
        "article_html": updated_html,
        "feedback_history": history,
        "edits_applied": edits_applied,
        "changes": changes,
    }

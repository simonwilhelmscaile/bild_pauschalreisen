"""
Blog Writer - Calls Gemini to generate the article.

Uses core GeminiClient for consistency across all stages:
- Gemini 3 Flash Preview
- URL Context + Google Search grounding
- Structured JSON output

Prompts are externalized to prompts/ folder for easy iteration.

Requires:
- GEMINI_API_KEY environment variable
"""

import asyncio
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent to path for shared imports
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

# Add python-backend root for absolute imports
_root = _parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from article_schema import ArticleOutput

# Import from core module (unified GeminiClient with retry)
try:
    from core.gemini_client import GeminiClient
    from core.config import ServiceType
except ImportError:
    GeminiClient = None
    ServiceType = None

logger = logging.getLogger(__name__)

# Blocked source domains — these are user-generated content, not professional sources
_BLOCKED_SOURCE_DOMAINS = [
    "reddit.com", "gutefrage.net", "facebook.com", "tiktok.com",
    "instagram.com", "twitter.com", "x.com", "youtube.com",
    "beurer.com",  # own site is not an external source
]

# Pattern matching the generic fallback description template
_GENERIC_DESC_RE = re.compile(r"^Source:\s+.+\s+—\s+relevant to\s+", re.IGNORECASE)


def _normalize_source_url(url: str) -> str:
    """Fix LLM-hallucinated URL issues before HTTP verification.

    Gemini frequently outputs URLs with spaces in the domain
    (e.g. 'https://www. Beurer. Com/de/p/123') and wrong casing.
    These fail HTTP checks and kill the source pipeline.
    """
    if not url or not isinstance(url, str):
        return url
    # Strip spaces (most common LLM artifact)
    if " " in url:
        url = re.sub(r"\s+", "", url)
    # Fix domain casing variants
    for wrong in ("Beurer.Com", "Beurer.com", "beurer.Com", "BEURER.COM"):
        if wrong in url:
            url = url.replace(wrong, "beurer.com")
    return url

# Prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"


# =============================================================================
# Prompt Loading
# =============================================================================

def _load_prompt(filename: str, fallback: str = "") -> str:
    """Load prompt from external file, with fallback."""
    path = PROMPTS_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    logger.warning(f"Prompt file not found: {path}, using fallback")
    return fallback


# Fallback prompts (used if files don't exist)
_FALLBACK_SYSTEM = '''You are an expert content writer. Write like a skilled human, not AI.

HARD RULES:
- Use Google Search for all stats/facts - NEVER invent them
- Only use exact URLs from search results - NEVER guess URLs
- NEVER mention competitors by name
- NO em-dashes (—), NO "Here's how", "Key points:", or robotic phrases

FRESH DATA:
- Today is {current_date}
- Use current year data. Say "2025 report" not "recent report"

VOICE:
- Match the company's tone and voice persona exactly

CONTENT QUALITY:
- Be direct - no filler like "In today's rapidly evolving..."
- Vary section lengths (some long 500+ words, some shorter)
- Include 2+ of: decision frameworks, concrete scenarios, common mistakes, strong opinions
- Cite stats naturally inline: "According to [Source]'s report..." not boring lists

FORMATTING:
- HTML: <p>, <ul>, <li>, <ol>, <strong>
- Lists are encouraged - use them for any set of 3+ related points'''


def get_system_instruction() -> str:
    """Get system instruction with current date injected."""
    template = _load_prompt("system_instruction.txt", _FALLBACK_SYSTEM)
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        return template.format(current_date=current_date)
    except KeyError as e:
        logger.error(f"System instruction template has unknown placeholder: {e}")
        # Fall back to template with manual date substitution
        return _FALLBACK_SYSTEM.format(current_date=current_date)


_FALLBACK_USER_PROMPT = '''Write a comprehensive, engaging blog article.

TOPIC: {keyword}

COMPANY CONTEXT:
{company_context}

LOCALIZATION:
- Language: {language}
- Country/Region: {country}

PARAMETERS:
- Word count: {word_count}
- Sections: 4-6 content sections
- PAA: 4 People Also Ask questions with answers
- FAQ: 5-6 FAQ questions with answers
- Takeaways: 3 key takeaways

{custom_instructions_section}

Return valid JSON with: Headline, Teaser, Direct_Answer, Intro, Meta_Title, Meta_Description,
section_01_title, section_01_content, ... (up to section_09), key_takeaway_01-03,
paa_01_question, paa_01_answer, ... (4 PAAs), faq_01_question, faq_01_answer, ... (up to 6 FAQs),
Sources (list of {{title, url, description}} - MANDATORY, 2-3 sources with descriptions), Search_Queries.
'''


def get_user_prompt() -> str:
    """Get user prompt template."""
    prompt = _load_prompt("user_prompt.txt", _FALLBACK_USER_PROMPT)
    if not prompt or not prompt.strip():
        logger.warning("Empty user_prompt.txt, using fallback")
        return _FALLBACK_USER_PROMPT
    return prompt


# =============================================================================
# Source Verification
# =============================================================================

async def _resolve_grounding_redirects(candidates: list, logger) -> list:
    """Resolve vertexaisearch.cloud.google.com redirect URLs to real destinations.

    Grounding sources from Gemini return proxy redirect URLs. This resolves
    them to the actual target URL via async HTTP HEAD + follow_redirects.
    Also filters out google.com/search results (not real sources).
    """
    import httpx as _httpx

    redirect_candidates = [c for c in candidates if "vertexaisearch.cloud.google.com/grounding-api-redirect/" in c.get("url", "")]
    if redirect_candidates:
        async with _httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
            for c in redirect_candidates:
                url = c["url"]
                try:
                    resp = await client.head(url)
                    real_url = str(resp.url)
                    if real_url != url and "google.com/search" not in real_url:
                        logger.info(f"Resolved grounding redirect: {c.get('title', '?')[:30]} -> {real_url[:60]}")
                        c["url"] = real_url
                    else:
                        c["url"] = ""
                except Exception:
                    c["url"] = ""

    # Filter out invalid/google URLs and deduplicate
    seen = set()
    result = []
    for c in candidates:
        url = c.get("url", "").strip()
        if (url and "google.com/search" not in url
                and "vertexaisearch.cloud.google.com" not in url
                and url not in seen):
            seen.add(url)
            result.append(c)
    return result


async def _build_verified_sources(
    client,
    keyword: str,
    headline: str,
    ai_sources: list,
    grounding_sources: list,
) -> list:
    """Build a verified source list using grounding URLs as primary.

    Strategy:
    1. Merge grounding URLs (real) + AI-generated URLs (may be hallucinated)
    2. HTTP-check all URLs
    3. Keep only alive ones
    4. Enrich grounding sources with AI-written descriptions if missing
    5. If < 3 sources, make a supplementary Gemini call for more

    Returns list of Source dicts with title, url, description.
    """
    import sys
    from pathlib import Path
    _stage4_dir = Path(__file__).parent.parent / "stage4"
    if str(_stage4_dir) not in sys.path:
        sys.path.insert(0, str(_stage4_dir))
    from http_checker import check_source_urls

    # Deduplicate by URL, preferring AI sources (have better titles/descriptions)
    seen_urls = set()
    candidates = []

    # AI sources first (have descriptions)
    for src in (ai_sources or []):
        if not isinstance(src, dict) or not src.get("url"):
            continue
        src["url"] = _normalize_source_url(src["url"].strip())
        url = src["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            candidates.append(src)

    # Add grounding sources not already covered
    for src in (grounding_sources or []):
        if not isinstance(src, dict) or not src.get("url"):
            continue
        src["url"] = _normalize_source_url(src["url"].strip())
        url = src["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            candidates.append(src)

    if not candidates:
        logger.warning("No source candidates at all (AI + grounding both empty) — will try supplement search")

    # Resolve Google grounding redirect URLs to actual destinations
    candidates = await _resolve_grounding_redirects(candidates, logger)

    logger.info(f"Source candidates after resolution: {len(candidates)}")

    # HTTP-verify all candidate URLs
    all_urls = [c["url"] for c in candidates]
    alive_urls, dead_urls = await check_source_urls(all_urls, timeout=3.0)
    alive_set = set(alive_urls)

    if dead_urls:
        logger.info(f"Source verification: {len(alive_urls)} alive, {len(dead_urls)} dead")

    verified = [c for c in candidates if c["url"] in alive_set]

    # Filter out blocked domains (user-generated content, social media)
    pre_filter_count = len(verified)
    verified = [
        c for c in verified
        if not any(domain in c["url"].lower() for domain in _BLOCKED_SOURCE_DOMAINS)
    ]
    if len(verified) < pre_filter_count:
        logger.info(f"Source filtering: removed {pre_filter_count - len(verified)} blocked-domain sources")

    # Enrich sources missing descriptions (common for grounding sources)
    needs_enrichment = [s for s in verified if not s.get("description", "").strip() or len(s.get("description", "")) < 10]
    if needs_enrichment:
        logger.info(f"Enriching {len(needs_enrichment)} sources with descriptions")
        try:
            src_list = "\n".join(f"- {s.get('title', 'Unknown')}: {s['url']}" for s in needs_enrichment)
            enrich_prompt = (
                f"Article topic: {keyword}\n"
                f"Article headline: {headline}\n\n"
                f"For each source below, write a 1-2 sentence German description explaining what "
                f"specific information, data, or guidance this source provides for the article topic. "
                f"Be specific about the content, not generic.\n\n{src_list}\n\n"
                f'Return JSON: {{"descriptions": ["desc for source 1", "desc for source 2", ...]}}'
            )
            enrich_result = await client.generate(
                prompt=enrich_prompt,
                use_url_context=True,
                json_output=True,
                temperature=0.2,
                max_tokens=1024,
            )
            descriptions = enrich_result.get("descriptions", [])
            for i, src in enumerate(needs_enrichment):
                if i < len(descriptions) and descriptions[i]:
                    src["description"] = descriptions[i]
                elif not src.get("description"):
                    src["description"] = ""
        except Exception as e:
            logger.warning(f"Source enrichment failed: {e}")
            for src in needs_enrichment:
                if not src.get("description"):
                    src["description"] = ""

    # Quality gate: drop sources with generic/placeholder descriptions
    pre_quality_count = len(verified)
    verified = [
        c for c in verified
        if not _GENERIC_DESC_RE.match(c.get("description", ""))
        and len(c.get("description", "")) >= 30
    ]
    if len(verified) < pre_quality_count:
        logger.info(f"Source quality gate: dropped {pre_quality_count - len(verified)} sources with generic descriptions")

    # Supplementary calls if under 3 verified sources (retry up to 3 times)
    # Only track verified URLs for dedup (dead URLs should not block new candidates)
    seen_verified = {c["url"] for c in verified}
    for attempt in range(3):
        if len(verified) >= 3:
            break
        needed = 3 - len(verified)
        logger.info(f"Only {len(verified)} verified sources (attempt {attempt + 1}) — searching for {needed} more")
        try:
            existing_text = "\n".join(f"- {s.get('title', '?')} ({s['url']})" for s in verified)
            supplement_prompt = (
                f"Article topic: {keyword}\n"
                f"Article headline: {headline}\n\n"
                f"I need {needed} additional authoritative sources for this article.\n"
                f"Existing sources (do NOT repeat):\n{existing_text}\n\n"
                f"Use Google Search to find REAL, currently accessible URLs from authoritative sources "
                f"(e.g. medical journals, health organizations, university hospitals, major health portals).\n\n"
                f"Return ONLY valid JSON:\n"
                f'{{"Sources": [{{"title": "Name", "url": "https://...", "description": "1-2 sentences"}}]}}'
            )
            supp_result = await client.generate(
                prompt=supplement_prompt,
                system_instruction="Find real, authoritative sources using Google Search. Each source MUST have title, url, and description. Only return URLs you are confident are currently accessible.",
                use_google_search=True,
                json_output=True,
                extract_sources=True,
                temperature=0.2,
                max_tokens=2048,
            )

            # Grounding URLs first (real Google Search results), then AI-generated
            supp_grounding = supp_result.get("_grounding_sources", [])
            supp_ai = supp_result.get("Sources", [])
            logger.info(f"  Supplement returned {len(supp_ai)} AI + {len(supp_grounding)} grounding sources")

            supp_candidates = []
            for src in supp_grounding + supp_ai:  # grounding first — more reliable
                if isinstance(src, dict) and src.get("url"):
                    src["url"] = _normalize_source_url(src["url"].strip())
                    supp_candidates.append(src)

            # Resolve grounding redirect URLs to real destinations
            supp_candidates = await _resolve_grounding_redirects(supp_candidates, logger)
            supp_candidates = [c for c in supp_candidates if c["url"] not in seen_verified]

            if supp_candidates:
                supp_urls = [c["url"] for c in supp_candidates]
                supp_alive, supp_dead = await check_source_urls(supp_urls, timeout=4.0)
                logger.info(f"  Supplement verification: {len(supp_alive)} alive, {len(supp_dead)} dead")
                supp_alive_set = set(supp_alive)
                needs_desc = []  # grounding sources accepted without description
                for c in supp_candidates:
                    if c["url"] in supp_alive_set:
                        if any(domain in c["url"].lower() for domain in _BLOCKED_SOURCE_DOMAINS):
                            continue
                        if not c.get("description") or len(c.get("description", "")) < 10:
                            needs_desc.append(c)  # accept now, enrich later
                        else:
                            verified.append(c)
                            seen_verified.add(c["url"])
                        if len(verified) + len(needs_desc) >= 3:
                            break
                # Enrich grounding sources that lack descriptions
                if needs_desc and len(verified) < 3:
                    needed_count = min(len(needs_desc), 3 - len(verified))
                    to_enrich = needs_desc[:needed_count]
                    try:
                        src_list = "\n".join(f"- {s.get('title', 'Unknown')}: {s['url']}" for s in to_enrich)
                        enrich_prompt = (
                            f"Article topic: {keyword}\n"
                            f"Article headline: {headline}\n\n"
                            f"For each source below, write a 1-2 sentence German description explaining what "
                            f"specific information this source provides for the article topic.\n\n{src_list}\n\n"
                            f'Return JSON: {{"descriptions": ["desc for source 1", ...]}}'
                        )
                        enrich_result = await client.generate(
                            prompt=enrich_prompt,
                            json_output=True,
                            temperature=0.2,
                            max_tokens=1024,
                        )
                        descs = enrich_result.get("descriptions", [])
                        for i, src in enumerate(to_enrich):
                            if i < len(descs) and descs[i] and len(descs[i]) >= 10:
                                src["description"] = descs[i]
                                verified.append(src)
                                seen_verified.add(src["url"])
                            if len(verified) >= 3:
                                break
                    except Exception as e:
                        logger.warning(f"  Supplement enrichment failed: {e}")
                logger.info(f"  After supplement attempt {attempt + 1}: {len(verified)} verified sources")
        except Exception as e:
            logger.warning(f"Supplementary source search failed: {e}", exc_info=True)

    logger.info(f"_build_verified_sources returning {len(verified)} sources")
    return verified[:3]


# =============================================================================
# Article Generation
# =============================================================================

async def write_article(
    keyword: str,
    company_context: Dict[str, Any],
    word_count: int = 2000,
    language: str = "en",
    country: str = "United States",
    batch_instructions: Optional[str] = None,
    keyword_instructions: Optional[str] = None,
    global_rules: Optional[List[str]] = None,
    sibling_articles: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None,
) -> ArticleOutput:
    """
    Generate a complete blog article using Gemini.

    Uses core GeminiClient for consistency.

    Args:
        keyword: Primary SEO keyword
        company_context: Company info dict (from Stage 1)
        word_count: Target word count
        language: Article language code (e.g., "en", "de", "es")
        country: Target country/region for localization (e.g., "United States", "Germany")
        batch_instructions: Batch-level instructions (applies to all articles)
        keyword_instructions: Keyword-level instructions (adds to batch instructions)
        api_key: Gemini API key (falls back to env var)

    Returns:
        ArticleOutput with all fields populated

    Raises:
        ValueError: If no API key
        Exception: If Gemini call fails
    """
    logger.info(f"Writing article for: {keyword} ({language}/{country})")

    try:
        # Use core GeminiClient
        if GeminiClient is None:
            raise ImportError("core.gemini_client not available")

        if ServiceType is not None:
            client = GeminiClient(service_type=ServiceType.BLOG, api_key=api_key)
        else:
            client = GeminiClient(api_key=api_key)

        # Load prompts
        system_instruction = get_system_instruction()
        user_prompt_template = get_user_prompt()

        # Build company context string
        company_str = _format_company_context(company_context, keyword=keyword, language=language)

        # Build custom instructions section (batch + keyword combined)
        custom_instructions_section = _build_custom_instructions(
            batch_instructions, keyword_instructions,
            global_rules=global_rules,
            sibling_articles=sibling_articles,
        )

        # Build prompt with KeyError handling
        try:
            prompt = user_prompt_template.format(
                keyword=keyword,
                company_context=company_str,
                word_count=word_count,
                language=language,
                country=country,
                custom_instructions_section=custom_instructions_section,
            )
        except KeyError as e:
            logger.error(f"Prompt template missing placeholder: {e}. Using fallback.")
            prompt = _FALLBACK_USER_PROMPT.format(
                keyword=keyword,
                company_context=company_str,
                word_count=word_count,
                language=language,
                country=country,
                custom_instructions_section=custom_instructions_section,
            )

        # Call with Google Search grounding + URL Context + source extraction
        # Use 65536 tokens to avoid truncation of full articles (sections + FAQ + PAA + sources)
        result = await client.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            use_url_context=True,
            use_google_search=True,
            json_output=True,
            extract_sources=True,  # Extract real URLs from grounding metadata
            temperature=0.3,
            max_tokens=65536,
        )

        # Guard: if Gemini returns a list instead of a dict, unwrap it
        if isinstance(result, list):
            result = result[0] if len(result) == 1 and isinstance(result[0], dict) else {"Sections": result}

        # Detect truncated article and retry once with higher temperature
        _filled_sections = sum(
            1 for i in range(1, 10)
            if result.get(f"section_{i:02d}_content") and len(str(result[f"section_{i:02d}_content"]).strip()) > 20
        )
        if _filled_sections < 3:
            logger.warning(
                f"Article appears truncated ({_filled_sections} sections). Retrying..."
            )
            result = await client.generate(
                prompt=prompt,
                system_instruction=system_instruction,
                use_url_context=True,
                use_google_search=True,
                json_output=True,
                extract_sources=True,
                temperature=0.5,
                max_tokens=65536,
            )
            if isinstance(result, list):
                result = result[0] if len(result) == 1 and isinstance(result[0], dict) else {"Sections": result}

        # --- Verified source pipeline ---
        ai_sources = result.get("Sources", [])
        grounding_sources = result.pop("_grounding_sources", []) or []

        logger.info(f"Raw sources: {len(ai_sources)} AI-generated, {len(grounding_sources)} grounding")

        verified_sources = await _build_verified_sources(
            client=client,
            keyword=keyword,
            headline=result.get("Headline", keyword),
            ai_sources=ai_sources,
            grounding_sources=grounding_sources,
        )

        result["Sources"] = verified_sources
        logger.info(f"Final verified sources: {len(verified_sources)}")

        article = ArticleOutput(**result)

        return article

    except Exception as e:
        logger.error(f"Blog generation failed: {e}")
        raise


def _format_company_context(
    context: Dict[str, Any],
    keyword: str = "",
    language: str = "de",
) -> str:
    """
    Format company context dict into readable string for Gemini prompt.

    Includes full voice persona, pain points, value propositions, and competitors
    to guide content generation aligned with brand voice.
    """
    # Warn about missing critical fields
    if not context.get('company_name'):
        logger.warning("Missing company_name in context - using 'Unknown'")
    if not context.get('industry'):
        logger.debug("Missing industry in context")
    if not context.get('target_audience'):
        logger.debug("Missing target_audience in context")

    lines = [
        f"Company: {context.get('company_name', 'Unknown')}",
        f"Industry: {context.get('industry', '')}",
        f"Target Audience: {context.get('target_audience', '')}",
        f"Tone: {context.get('tone', 'professional')}",
    ]

    # Add company description if available
    description = context.get('description', '')
    if description:
        lines.append(f"About: {description}")

    # Use structured product specs if available (category-scoped)
    product_specs_block = context.get('_product_specs_block')
    if product_specs_block:
        lines.append("")
        lines.append(product_specs_block)
    else:
        # Fallback: flat product list (non-Beurer or no keyword context)
        products = context.get('products', [])
        if products:
            if isinstance(products, list):
                lines.append(f"Products/Services: {', '.join(str(p) for p in products)}")
            else:
                lines.append(f"Products/Services: {products}")

    # Add pain points - helps content address real customer problems
    pain_points = context.get('pain_points', [])
    if pain_points:
        if isinstance(pain_points, list):
            lines.append(f"Customer Pain Points: {'; '.join(str(p) for p in pain_points)}")
        else:
            lines.append(f"Customer Pain Points: {pain_points}")

    # Add value propositions - helps frame solutions and CTAs
    value_props = context.get('value_propositions', [])
    if value_props:
        if isinstance(value_props, list):
            lines.append(f"Value Propositions: {'; '.join(str(v) for v in value_props)}")
        else:
            lines.append(f"Value Propositions: {value_props}")

    # Add competitors to AVOID mentioning
    competitors = context.get('competitors', [])
    if competitors:
        if isinstance(competitors, list):
            lines.append(f"COMPETITORS (NEVER mention these): {', '.join(str(c) for c in competitors)}")
        else:
            lines.append(f"COMPETITORS (NEVER mention these): {competitors}")

    # Add use cases if available
    use_cases = context.get('use_cases', [])
    if use_cases:
        if isinstance(use_cases, list):
            lines.append(f"Common Use Cases: {'; '.join(str(u) for u in use_cases)}")
        else:
            lines.append(f"Common Use Cases: {use_cases}")

    # Full voice persona section
    voice = context.get('voice_persona', {})
    if voice:
        lines.append("")
        lines.append("=== VOICE & WRITING STYLE ===")

        # ICP profile - who we're writing for
        icp = voice.get('icp_profile', '')
        if icp:
            lines.append(f"Ideal Reader: {icp}")

        voice_style = voice.get('voice_style', '')
        if voice_style:
            lines.append(f"Voice Style: {voice_style}")

        # Language style details
        lang_style = voice.get('language_style', {})
        if lang_style:
            style_parts = []
            if lang_style.get('formality'):
                style_parts.append(f"Formality: {lang_style['formality']}")
            if lang_style.get('complexity'):
                style_parts.append(f"Complexity: {lang_style['complexity']}")
            if lang_style.get('perspective'):
                style_parts.append(f"Perspective: {lang_style['perspective']}")
            if lang_style.get('sentence_length'):
                style_parts.append(f"Sentences: {lang_style['sentence_length']}")
            if style_parts:
                lines.append(f"Language Style: {', '.join(style_parts)}")

        # DO list - behaviors that resonate
        do_list = voice.get('do_list', [])
        if do_list:
            lines.append(f"DO: {'; '.join(str(d) for d in do_list[:5])}")

        # DON'T list - anti-patterns to avoid
        dont_list = voice.get('dont_list', [])
        if dont_list:
            lines.append(f"DON'T: {'; '.join(str(d) for d in dont_list[:5])}")

        # Banned words - critical for avoiding AI-sounding phrases
        banned = voice.get('banned_words', [])
        if banned:
            lines.append(f"BANNED WORDS (never use): {', '.join(str(b) for b in banned[:10])}")

        # Technical terms to use correctly
        tech_terms = voice.get('technical_terms', [])
        if tech_terms:
            lines.append(f"Technical Terms (use correctly): {', '.join(str(t) for t in tech_terms[:8])}")

        # Power words that resonate
        power_words = voice.get('power_words', [])
        if power_words:
            lines.append(f"Power Words: {', '.join(str(p) for p in power_words[:8])}")

        # Example phrases for tone reference
        examples = voice.get('example_phrases', [])
        if examples:
            examples_str = '"; "'.join(str(e) for e in examples[:3])
            lines.append(f'Example Phrases: "{examples_str}"')

        # CTA phrases
        cta_phrases = voice.get('cta_phrases', [])
        if cta_phrases:
            lines.append(f"CTA Style: {'; '.join(str(c) for c in cta_phrases[:3])}")

        # Headline patterns
        headline_patterns = voice.get('headline_patterns', [])
        if headline_patterns:
            lines.append(f"Headline Patterns: {'; '.join(str(h) for h in headline_patterns[:3])}")

        # Content structure hints
        structure = voice.get('content_structure_pattern', '')
        if structure:
            lines.append(f"Preferred Structure: {structure}")

        # Formatting preferences
        format_hints = []
        if voice.get('uses_questions'):
            format_hints.append("Use rhetorical questions")
        if voice.get('uses_lists'):
            format_hints.append("Use bullet/numbered lists")
        if voice.get('uses_statistics'):
            format_hints.append("Include data/statistics")
        if voice.get('first_person_usage'):
            format_hints.append(f"First person: {voice['first_person_usage']}")
        if format_hints:
            lines.append(f"Formatting: {', '.join(format_hints)}")

    # Add authors if available (for byline/credibility)
    authors = context.get('authors', [])
    if authors:
        author_names = []
        for author in authors:
            if isinstance(author, dict):
                name = author.get('name', '')
                title = author.get('title', '')
                if name:
                    author_names.append(f"{name} ({title})" if title else name)
            elif hasattr(author, 'name'):
                author_names.append(f"{author.name} ({author.title})" if author.title else author.name)
        if author_names:
            lines.append(f"Authors: {', '.join(author_names)}")

    # Official terminology from Beurer termbase
    if keyword:
        try:
            from blog.termbase import get_relevant_terms
            termbase_terms = get_relevant_terms(keyword, language)
            if termbase_terms:
                lines.append("")
                lines.append("=== MANDATORY TERMINOLOGY (use these exact terms) ===")

                product_terms = [t for t in termbase_terms if t["is_product_name"]]
                glossary_terms = [t for t in termbase_terms if not t["is_product_name"]]

                if product_terms:
                    lines.append("Product names (use verbatim, never paraphrase):")
                    for t in product_terms:
                        lines.append(f"  - {t['de']}")

                if glossary_terms:
                    is_en = language.startswith("en")
                    if is_en:
                        lines.append("Glossary (use these exact English translations):")
                        for t in glossary_terms:
                            lines.append(f"  - {t['de']} \u2192 {t['target']}")
                    else:
                        lines.append("Glossary (use these exact German terms):")
                        for t in glossary_terms:
                            lines.append(f"  - {t['target']}")
        except Exception as e:
            logger.warning(f"Failed to load termbase terms: {e}")

    return "\n".join(lines)


def _build_custom_instructions(
    batch_instructions: Optional[str],
    keyword_instructions: Optional[str],
    global_rules: Optional[List[str]] = None,
    sibling_articles: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Build combined custom instructions section.

    Includes (in priority order):
    1. Global customer rules (highest priority)
    2. Sibling article awareness (cross-article dedup)
    3. Batch instructions
    4. Keyword instructions

    Returns:
        Formatted instructions section, or empty string if none provided.
    """
    parts = []

    # Global rules (highest priority)
    if global_rules:
        rules_text = "\n".join(f"- {r}" for r in global_rules)
        parts.append(
            f"KUNDENREGELN (vom Kunden vorgegeben — hoechste Prioritaet):\n{rules_text}"
        )

    # Sibling article awareness
    if sibling_articles:
        sibling_lines = []
        for s in sibling_articles:
            summary = s.get("summary", "")
            summary_text = f" — {summary}" if summary else ""
            sibling_lines.append(f'- "{s["keyword"]}" ({s["href"]}){summary_text}')
        parts.append(
            "EXISTING ARTICLES (already published — do not repeat their content in detail):\n"
            + "\n".join(sibling_lines)
            + '\nIf any of these topics overlap with your article, write a brief cross-reference '
            + 'instead of a full explanation. Example: "Mehr dazu in unserem Ratgeber zu '
            + '[Thema](/blog/thema)."'
        )

    # Batch instructions
    if batch_instructions:
        parts.append(batch_instructions.strip())

    # Keyword instructions
    if keyword_instructions:
        if batch_instructions:
            parts.append(f"Additional for this article: {keyword_instructions.strip()}")
        else:
            parts.append(keyword_instructions.strip())

    if not parts:
        return ""

    return (
        "MANDATORY CUSTOM INSTRUCTIONS (follow these with highest priority, "
        "they override default behaviors):\n\n"
        + "\n\n".join(parts)
    )


# =============================================================================
# BlogWriter Class (wrapper for compatibility)
# =============================================================================

class BlogWriter:
    """
    Wrapper class for write_article function.

    Provides class-based interface for compatibility with stage_2.py.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("No Gemini API key. Set GEMINI_API_KEY environment variable.")
        logger.info("BlogWriter initialized (using core GeminiClient)")

    async def write_article(
        self,
        keyword: str,
        company_context: Dict[str, Any],
        word_count: int = 2000,
        language: str = "en",
        country: str = "United States",
        batch_instructions: Optional[str] = None,
        keyword_instructions: Optional[str] = None,
        global_rules: Optional[List[str]] = None,
        sibling_articles: Optional[List[Dict[str, str]]] = None,
    ) -> ArticleOutput:
        """Generate article using write_article function."""
        return await write_article(
            keyword=keyword,
            company_context=company_context,
            word_count=word_count,
            language=language,
            country=country,
            batch_instructions=batch_instructions,
            keyword_instructions=keyword_instructions,
            global_rules=global_rules,
            sibling_articles=sibling_articles,
            api_key=self.api_key,
        )


# =============================================================================
# CLI for standalone testing
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python blog_writer.py <keyword> [company_url]")
        sys.exit(1)

    # Check for API key first
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: No API key. Set GEMINI_API_KEY environment variable.")
        sys.exit(1)

    keyword = sys.argv[1]
    company_url = sys.argv[2] if len(sys.argv) > 2 else "https://example.com"

    # Minimal company context
    company = {
        "company_name": company_url.replace("https://", "").replace("http://", "").split("/")[0],
        "company_url": company_url,
        "industry": "",
        "tone": "professional",
    }

    async def main():
        try:
            article = await write_article(keyword, company, word_count=1000)
            print(f"\nHeadline: {article.Headline}")
            print(f"Sections: {article.count_sections()}")
            print(f"FAQs: {article.count_faqs()}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    asyncio.run(main())

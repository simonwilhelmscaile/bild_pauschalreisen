"""Beurer company context for blog article generation.

Reads context.md and persona.md, injects products/competitors from
report/constants.py. Falls back to hardcoded defaults if files are missing.
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from report.constants import (
    BEURER_PRODUCT_CATALOG,
    COMPETITOR_PRODUCT_CATALOG,
    CATEGORY_LABELS_DE,
    PAIN_CATEGORY_LABELS_DE,
)

_BLOG_DIR = Path(__file__).parent


def _read_md(filename: str) -> Optional[str]:
    """Read a markdown file from the blog directory. Returns None if missing/empty."""
    path = _BLOG_DIR / filename
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def _get_section(text: str, header: str) -> str:
    """Extract content under a ## header, up to the next ## or EOF."""
    pattern = rf"^## {re.escape(header)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _parse_list_section(text: str, header: str) -> List[str]:
    """Parse a section of bullet points into a list of strings."""
    section = _get_section(text, header)
    if not section:
        return []
    return [line.lstrip("- ").strip() for line in section.splitlines() if line.strip().startswith("-")]


def _parse_kv_section(text: str, header: str) -> Dict[str, str]:
    """Parse a section of `- key: value` lines into a dict."""
    items = _parse_list_section(text, header)
    result = {}
    for item in items:
        if ": " in item:
            k, v = item.split(": ", 1)
            result[k.strip()] = v.strip()
    return result


def _parse_context_md(text: str) -> Dict[str, Any]:
    """Parse context.md into a partial context dict."""
    company_kvs = _parse_kv_section(text, "Company")
    description = _get_section(text, "Description")
    target_audience = _get_section(text, "Target Audience")
    value_props = _parse_list_section(text, "Value Propositions")
    use_cases = _parse_list_section(text, "Use Cases")
    learnings = _parse_list_section(text, "Learnings")

    return {
        "company_name": company_kvs.get("company_name", "Beurer"),
        "company_url": company_kvs.get("company_url", "https://www.beurer.com"),
        "industry_de": company_kvs.get("industry_de", "Gesundheit & Medizintechnik"),
        "industry_en": company_kvs.get("industry_en", "Health & Medical Technology"),
        "description": description,
        "target_audience": target_audience,
        "value_propositions": value_props,
        "use_cases": use_cases,
        "learnings": learnings,
    }


def _parse_persona_md(text: str) -> Dict[str, Any]:
    """Parse persona.md into a voice_persona dict."""
    icp = _get_section(text, "ICP Profile")
    voice_style = _get_section(text, "Voice Style")
    lang_style = _parse_kv_section(text, "Language Style")
    vocab = _get_section(text, "Vocabulary Level")
    authority = _parse_list_section(text, "Authority Signals")
    do_list = _parse_list_section(text, "Do")
    dont_list = _parse_list_section(text, "Don't")
    banned = _parse_list_section(text, "Banned Words")
    formatting = _parse_kv_section(text, "Formatting")
    tone_refinements = _parse_list_section(text, "Tone Refinements")

    return {
        "icp_profile": icp,
        "voice_style": voice_style,
        "language_style": lang_style or {
            "formality": "formal",
            "complexity": "accessible",
            "perspective": "second_person_formal",
            "sentence_length": "medium",
        },
        "vocabulary_level": vocab or "accessible_medical",
        "authority_signals": authority,
        "do_list": do_list,
        "dont_list": dont_list,
        "banned_words": banned,
        "sentence_patterns": [],
        "example_phrases": [],
        "opening_styles": [],
        "transition_phrases": [],
        "closing_styles": [],
        "headline_patterns": [],
        "subheading_styles": [],
        "cta_phrases": [],
        "technical_terms": [],
        "power_words": [],
        "paragraph_length": "",
        "uses_questions": formatting.get("uses_questions", "true").lower() == "true",
        "uses_lists": formatting.get("uses_lists", "true").lower() == "true",
        "uses_statistics": formatting.get("uses_statistics", "true").lower() == "true",
        "first_person_usage": formatting.get("first_person_usage", "none"),
        "content_structure_pattern": "",
        "tone_refinements": tone_refinements,
    }


# ---------------------------------------------------------------------------
# Hardcoded fallback (original values)
# ---------------------------------------------------------------------------

_FALLBACK_CONTEXT = {
    "company_name": "Beurer",
    "company_url": "https://www.beurer.com",
    "industry_de": "Gesundheit & Medizintechnik",
    "industry_en": "Health & Medical Technology",
    "description": (
        "Beurer ist ein traditionsreiches deutsches Unternehmen für Gesundheits- und "
        "Wohlbefinden-Produkte. Das Sortiment umfasst Blutdruckmessgeräte, TENS/EMS-Geräte "
        "zur Schmerztherapie und Infrarotlampen."
    ),
    "target_audience": (
        "Gesundheitsbewusste Verbraucher in Deutschland, die nach zuverlässigen "
        "Gesundheitsgeräten für den Heimgebrauch suchen"
    ),
    "value_propositions": [
        "Über 100 Jahre Erfahrung in der Gesundheitsbranche",
        "Deutsche Qualität und Präzision",
        "Klinisch validierte Messgenauigkeit",
        "Einfache Bedienung für alle Altersgruppen",
        "Umfangreiches Sortiment für verschiedene Gesundheitsbedürfnisse",
    ],
    "use_cases": [
        "Blutdrucküberwachung zu Hause",
        "Schmerztherapie mit TENS/EMS",
        "Wärmetherapie mit Infrarot",
        "Menstruationsschmerzlinderung",
    ],
}

_FALLBACK_PERSONA = {
    "icp_profile": "Gesundheitsbewusste Erwachsene 35-65, die Gesundheitsthemen online recherchieren",
    "voice_style": (
        "Professionell, einfühlsam und vertrauenswürdig. Verwendet die Du-Form. "
        "Verbindet medizinisches Fachwissen mit verständlicher Sprache."
    ),
    "language_style": {
        "formality": "conversational_professional",
        "complexity": "accessible",
        "perspective": "second_person_informal",
        "sentence_length": "medium",
    },
    "vocabulary_level": "accessible_medical",
    "authority_signals": [
        "Klinische Studien",
        "Medizinische Leitlinien",
        "Ärztliche Empfehlungen",
        "Validierte Messverfahren",
    ],
    "do_list": [
        "Medizinische Fachbegriffe erklären",
        "Quellenangaben und Studien zitieren",
        "Praktische Tipps geben",
        "Empathisch auf Schmerzthemen eingehen",
        "Du-Form konsequent verwenden",
        "Strukturierte Informationen mit Zwischenüberschriften",
    ],
    "dont_list": [
        "Keine medizinischen Diagnosen stellen",
        "Keine reißerischen Gesundheitsversprechen",
        "Keine Sie-Form verwenden (NIEMALS 'Sie', 'Ihnen', 'Ihr' als Anrede)",
        "Keine unbelegten Behauptungen",
        "Keine Verharmlosung von Symptomen",
    ],
    "banned_words": [
        "Wundermittel", "garantiert heilen", "sofort schmerzfrei",
        "100% sicher", "Ärzte hassen diesen Trick",
    ],
}


def get_beurer_sitemap_urls(category: str = "general") -> Dict[str, List[str]]:
    """Return Beurer website URLs for Stage 5 internal linking.

    These replace the dynamic sitemap crawl that Stage 1 normally does,
    since we skip Stage 1 with pre-provided Beurer context.
    """
    # All URLs verified against beurer.com sitemap — only include URLs that return 200
    urls = {
        "blog_urls": [
            # Verified landing pages from sitemap
            "https://www.beurer.com/de/l/blutdruckmessgeraete/",
            "https://www.beurer.com/de/l/tens-ems/",
            "https://www.beurer.com/de/l/em-50-menstrual-relax-pad/",
            "https://www.beurer.com/de/l/waerme/",
            "https://www.beurer.com/de/l/gesund-bleiben-im-winter/",
            "https://www.beurer.com/de/l/massage-guns/",
            "https://www.beurer.com/de/l/insektenstichheiler/",
            "https://www.beurer.com/de/l/maremed/",
            "https://www.beurer.com/de/blog/",
        ],
        "product_urls": [
            # Verified category codes from sitemap (all return 200)
            "https://www.beurer.com/de/c/0010101/",  # Oberarm-Blutdruckmessgeräte
            "https://www.beurer.com/de/c/0010102/",  # Handgelenk-Blutdruckmessgeräte
            "https://www.beurer.com/de/c/0010401/",  # TENS-Geräte
            "https://www.beurer.com/de/c/0010402/",  # EMS-Geräte
            "https://www.beurer.com/de/c/00201/",    # Wärme-Therapie
            "https://www.beurer.com/de/c/0010302/",  # Infrarotlampen
            "https://www.beurer.com/de/c/0010301/",  # Tageslichtlampen
        ],
        "resource_urls": [
            "https://www.beurer.com/de/blog/",
            "https://www.beurer.com/de/service/connect/healthmanager-pro/",
        ],
        "tool_urls": [],
        "service_urls": [
            "https://www.beurer.com/de/kontakt/",
            "https://www.beurer.com/de/service/faq/",
            "https://www.beurer.com/de/service/newsletter/",
        ],
    }

    # Category-scoped URL filtering
    if category in ("pain_therapy", "menstrual"):
        # Remove HealthManager Pro URL (BP-only app)
        urls["resource_urls"] = [
            u for u in urls["resource_urls"]
            if "healthmanager-pro" not in u
        ]
        # Remove BP category URLs
        urls["product_urls"] = [
            u for u in urls["product_urls"]
            if "0010101" not in u and "0010102" not in u  # Oberarm, Handgelenk
        ]
    elif category == "blood_pressure":
        # Remove TENS/EMS/infrarot/warming category URLs
        urls["product_urls"] = [
            u for u in urls["product_urls"]
            if "0010401" not in u and "0010402" not in u  # TENS, EMS
            and "0010302" not in u and "00201" not in u  # Infrarot, Wärme
        ]

    return urls


def get_existing_article_siblings(
    current_keyword: str,
    limit: int = 10,
) -> List[Dict[str, str]]:
    """Fetch published blog articles from Supabase to use as internal link siblings.

    Only includes articles that have a real publish_url — we never generate
    fake URLs because they'd 404 on beurer.com.

    Returns list of {keyword, href, summary} dicts. The summary is the
    Direct_Answer from the article (used by Stage 2 for cross-article
    awareness). Stage 5 only uses keyword and href, so this is backwards-compatible.
    """
    try:
        from db.client import get_beurer_supabase
        supabase = get_beurer_supabase()
        result = (
            supabase.table("blog_articles")
            .select("keyword, publish_url, article_json")
            .eq("status", "completed")
            .not_.is_("publish_url", "null")
            .order("created_at", desc=True)
            .limit(limit + 1)
            .execute()
        )
        siblings = []
        current_lower = current_keyword.lower().strip()
        for row in (result.data or []):
            kw = row.get("keyword", "")
            href = (row.get("publish_url") or "").strip()
            if not href or kw.lower().strip() == current_lower:
                continue
            # Extract Direct_Answer as topic summary for cross-article awareness
            article_json = row.get("article_json") or {}
            if isinstance(article_json, str):
                import json as _json
                try:
                    article_json = _json.loads(article_json)
                except (ValueError, TypeError):
                    article_json = {}
            summary = (article_json.get("Direct_Answer") or "").strip()
            siblings.append({"keyword": kw, "href": href, "summary": summary})
            if len(siblings) >= limit:
                break
        return siblings
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to fetch article siblings: %s", e)
        return []


def get_global_rules() -> List[str]:
    """Fetch active global content rules from Supabase.

    These are reviewer-submitted rules that apply to all articles,
    e.g., 'Immer Du-Form verwenden' or 'Keine Heilungsversprechen'.

    Returns list of rule text strings, ordered by creation date.
    """
    try:
        from db.client import get_beurer_supabase
        supabase = get_beurer_supabase()
        result = (
            supabase.table("blog_global_rules")
            .select("rule_text")
            .eq("active", True)
            .order("created_at")
            .execute()
        )
        return [row["rule_text"] for row in (result.data or []) if row.get("rule_text")]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to fetch global rules: %s", e)
        return []


def get_beurer_company_context(language: str = "de", keyword: Optional[str] = None) -> Dict[str, Any]:
    """Build a CompanyContext-shaped dict for Beurer.

    Reads from context.md and persona.md. Falls back to hardcoded defaults
    if files are missing. Products/competitors injected from report/constants.py.
    """
    # Category-scoped products: only pass relevant products for this keyword
    if keyword:
        from blog.product_catalog import detect_article_category, get_products_for_category, format_product_specs
        _article_category = detect_article_category(keyword)
        _filtered_products = get_products_for_category(_article_category)
        products = [p.sku for p in _filtered_products]
        _product_specs_block = format_product_specs(_filtered_products, language)
    else:
        products = list(BEURER_PRODUCT_CATALOG.keys())
        _article_category = "general"
        _product_specs_block = None
    competitors = list(COMPETITOR_PRODUCT_CATALOG.keys())
    content_themes = list(CATEGORY_LABELS_DE.values())
    pain_points = list(PAIN_CATEGORY_LABELS_DE.values())

    is_de = language.startswith("de")

    # Parse markdown files (or use fallbacks)
    context_text = _read_md("context.md")
    if context_text:
        ctx = _parse_context_md(context_text)
    else:
        ctx = _FALLBACK_CONTEXT

    persona_text = _read_md("persona.md")
    if persona_text:
        persona = _parse_persona_md(persona_text)
    else:
        persona = {**_FALLBACK_PERSONA, "sentence_patterns": [], "example_phrases": [],
                    "opening_styles": [], "transition_phrases": [], "closing_styles": [],
                    "headline_patterns": [], "subheading_styles": [], "cta_phrases": [],
                    "technical_terms": [], "power_words": [], "paragraph_length": "",
                    "uses_questions": True, "uses_lists": True, "uses_statistics": True,
                    "first_person_usage": "none", "content_structure_pattern": "",
                    "tone_refinements": []}

    # Language-specific overrides
    if not is_de:
        description = (
            "Beurer is a German health technology company with over 100 years of experience, "
            "specialising in clinically validated blood pressure monitors, TENS/EMS pain therapy "
            "devices, and infrared lamps. Known for German engineering quality and precision."
        )
        target_audience = (
            "Health-conscious adults aged 35-65 in the UK and US who research health topics "
            "online before purchasing medical devices for home use."
        )
        value_props = [
            "Over 100 years of German health technology expertise",
            "Clinically validated measurement accuracy",
            "Easy-to-use devices for all age groups",
            "Comprehensive range for different health needs",
            "Trusted by healthcare professionals across Europe",
        ]
        use_cases_list = [
            "Home blood pressure monitoring",
            "Pain therapy with TENS/EMS",
            "Heat therapy with infrared lamps",
            "Menstrual pain relief",
        ]
    else:
        description = ctx.get("description", _FALLBACK_CONTEXT["description"])
        target_audience = ctx.get("target_audience", _FALLBACK_CONTEXT["target_audience"])
        value_props = ctx.get("value_propositions", _FALLBACK_CONTEXT["value_propositions"])
        use_cases_list = ctx.get("use_cases", _FALLBACK_CONTEXT["use_cases"])

    result = {
        "company_name": ctx.get("company_name", "Beurer"),
        "company_url": ctx.get("company_url", "https://www.beurer.com"),
        "industry": ctx.get("industry_de" if is_de else "industry_en",
                            "Gesundheit & Medizintechnik" if is_de else "Health & Medical Technology"),
        "description": description,
        "products": products,
        "target_audience": target_audience,
        "competitors": competitors,
        "tone": "professional",
        "pain_points": pain_points,
        "value_propositions": value_props,
        "use_cases": use_cases_list,
        "content_themes": content_themes,
        "voice_persona": persona,
        "visual_identity": {
            "primary_color": "#C60050",
            "secondary_colors": [],
            "image_style": "",
            "preferred_formats": [],
        },
        "authors": [],
    }
    result["_product_specs_block"] = _product_specs_block
    result["_article_category"] = _article_category
    return result

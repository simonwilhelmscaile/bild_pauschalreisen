"""
HTML Renderer - Pure viewer for ArticleOutput.

Renders article dict to semantic HTML5 page.
No content manipulation - content should already be correct from stages 2-5.
"""

import base64
import logging
import re
from html import escape, unescape
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_GERMAN_MONTHS = [
    "", "Januar", "Februar", "M\u00e4rz", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

_ENGLISH_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_ARTICLE_LABELS = {
    "de": {
        "toc": "Inhaltsverzeichnis",
        "takeaways": "Das Wichtigste in K\u00fcrze",
        "faq": "H\u00e4ufig gestellte Fragen",
        "paa": "Weitere Fragen",
        "sources": "Quellen",
        "direct_answer": "Das Wichtigste in K\u00fcrze:",
        "reading_time": "Min. Lesezeit",
        "last_updated": "Zuletzt aktualisiert:",
        "medical_review": "Medizinisch gepr\u00fcft von:",
        "image_placeholder": "Bild-Platzhalter",
    },
    "en": {
        "toc": "Table of Contents",
        "takeaways": "Key Takeaways",
        "faq": "Frequently Asked Questions",
        "paa": "Related Questions",
        "sources": "Sources",
        "direct_answer": "Short Answer:",
        "reading_time": "min read",
        "last_updated": "Last updated:",
        "medical_review": "Medically reviewed by:",
        "image_placeholder": "Image placeholder",
    },
}


def _label(language: str, key: str) -> str:
    return _ARTICLE_LABELS.get(language, _ARTICLE_LABELS["de"]).get(key, _ARTICLE_LABELS["de"][key])

# Inline SVG icons for meta bar (feather-icon style, 14px)
_ICON_CALENDAR = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="4" width="18" height="18" rx="2"/>'
    '<line x1="16" y1="2" x2="16" y2="6"/>'
    '<line x1="8" y1="2" x2="8" y2="6"/>'
    '<line x1="3" y1="10" x2="21" y2="10"/></svg>'
)
_ICON_CLOCK = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<polyline points="12 6 12 12 16 14"/></svg>'
)
_ICON_AUTHOR = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 20h9"/>'
    '<path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>'
)


def _image_path_to_data_url(image_path: str) -> Optional[str]:
    """
    Convert a local image path to a base64 data URL.

    Args:
        image_path: Path to image file (can be absolute or relative)

    Returns:
        Base64 data URL string, or None if conversion fails
    """
    if not image_path:
        return None

    # Skip if already a URL or data URL
    if image_path.startswith(('http://', 'https://', 'data:')):
        return image_path

    try:
        path = Path(image_path)
        if not path.exists():
            logger.debug(f"Image file not found: {image_path}")
            return None

        # Read image bytes
        img_data = path.read_bytes()
        if not img_data:
            logger.debug(f"Image file is empty: {image_path}")
            return None

        # Determine MIME type from extension
        ext = path.suffix.lower()
        mime_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
        }.get(ext, 'image/png')

        # Create base64 data URL
        b64_data = base64.b64encode(img_data).decode('utf-8')
        data_url = f"data:{mime_type};base64,{b64_data}"

        logger.debug(f"Converted image to data URL: {image_path} ({len(img_data)} bytes)")
        return data_url

    except Exception as e:
        logger.warning(f"Failed to convert image to data URL: {image_path} - {e}")
        return None


class HTMLRenderer:
    """Simple HTML renderer - no content manipulation."""

    @staticmethod
    def _estimate_reading_time(article: Dict[str, Any]) -> int:
        """Estimate reading time in minutes from article word count."""
        text_parts = []
        text_parts.append(article.get("Intro", ""))
        text_parts.append(article.get("Direct_Answer", ""))
        for i in range(1, 10):
            text_parts.append(article.get(f"section_{i:02d}_content", ""))
        for i in range(1, 4):
            text_parts.append(article.get(f"key_takeaway_{i:02d}", ""))
        for i in range(1, 7):
            text_parts.append(article.get(f"faq_{i:02d}_answer", ""))
        for i in range(1, 5):
            text_parts.append(article.get(f"paa_{i:02d}_answer", ""))

        combined = " ".join(t for t in text_parts if t)
        # Strip HTML tags for word count
        plain = re.sub(r'<[^>]+>', '', combined)
        word_count = len(plain.split())
        # ~200 words per minute, minimum 1
        return max(1, round(word_count / 200))

    @staticmethod
    def _render_hreflang_tags(
        current_language: str,
        siblings: list,
    ) -> str:
        """Generate hreflang <link> tags for alternate language versions."""
        if not siblings:
            return ""

        HREFLANG_MAP = {
            "de": "de",
            "en": "en",
            "en-us": "en-US",
        }

        tags = []
        for sib in siblings:
            lang = sib.get("language", "")
            url = sib.get("url", "")
            if not url:
                continue
            hreflang = HREFLANG_MAP.get(lang, lang)
            tags.append(
                f'<link rel="alternate" hreflang="{escape(hreflang)}" href="{escape(url)}">'
            )

        de_url = next((s["url"] for s in siblings if s.get("language") == "de" and s.get("url")), None)
        if de_url:
            tags.append(f'<link rel="alternate" hreflang="x-default" href="{escape(de_url)}">')

        return "\n    ".join(tags)

    @staticmethod
    def render(
        article: Dict[str, Any],
        company_name: str = "",
        company_url: str = "",
        author_name: str = "",
        language: str = "de",
        category: str = "",
        author: Optional[Dict[str, Any]] = None,
        last_updated: Optional[str] = None,
        hreflang_siblings: Optional[list] = None,
    ) -> str:
        """
        Render article to production HTML.

        Args:
            article: ArticleOutput dict
            company_name: Company name for meta
            company_url: Company URL for links
            author_name: Author name (defaults to company_name)
            language: Language code for HTML lang attribute (default: "en")
            category: Category key (e.g. "blood_pressure") for badge above title
            author: Author dict with keys: name, title, bio, image_url, credentials, linkedin_url
            last_updated: ISO date string for "last updated" display (defaults to now)

        Returns:
            Complete HTML document string
        """
        # Extract fields
        headline = HTMLRenderer._strip_html(article.get("Headline", "Untitled"))
        teaser = HTMLRenderer._strip_html(article.get("Teaser", ""))
        intro = article.get("Intro", "")
        meta_title = HTMLRenderer._strip_html(article.get("Meta_Title", headline))
        meta_desc = HTMLRenderer._strip_html(article.get("Meta_Description", teaser))
        direct_answer = article.get("Direct_Answer", "")
        sources = article.get("Sources", "")

        # Author
        author_display = author_name or (author or {}).get("name", "") or company_name or "Author"

        # Images - convert local paths to base64 data URLs for browser/PDF compatibility
        hero_image_raw = article.get("image_01_url", "")
        logger.info(f"HTMLRenderer: hero_image_raw = {hero_image_raw[:100] if hero_image_raw else 'EMPTY'}...")
        hero_image = _image_path_to_data_url(hero_image_raw) or hero_image_raw
        logger.info(f"HTMLRenderer: hero_image final = {hero_image[:100] if hero_image else 'EMPTY'}...")
        # Limit default alt text to 125 chars
        default_alt = f"Image for {headline}"
        if len(default_alt) > 125:
            default_alt = default_alt[:122] + "..."
        hero_alt = article.get("image_01_alt_text") or default_alt

        mid_image_raw = article.get("image_02_url", "")
        mid_image = _image_path_to_data_url(mid_image_raw) or mid_image_raw
        mid_alt = article.get("image_02_alt_text", "")

        bottom_image_raw = article.get("image_03_url", "")
        bottom_image = _image_path_to_data_url(bottom_image_raw) or bottom_image_raw
        bottom_alt = article.get("image_03_alt_text", "")

        # Date (timezone-aware)
        months = _GERMAN_MONTHS if language == "de" else _ENGLISH_MONTHS
        now = datetime.now(timezone.utc)
        pub_date = now.strftime("%Y-%m-%d")
        if language == "de":
            display_date = f"{now.day}. {months[now.month]} {now.year}"
        else:
            display_date = f"{months[now.month]} {now.day}, {now.year}"

        # Last updated date
        if last_updated:
            try:
                lu = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                if language == "de":
                    last_updated_display = f"{lu.day}. {months[lu.month]} {lu.year}"
                else:
                    last_updated_display = f"{months[lu.month]} {lu.day}, {lu.year}"
            except (ValueError, IndexError):
                last_updated_display = last_updated
        else:
            last_updated_display = display_date

        # Reading time
        reading_min = HTMLRenderer._estimate_reading_time(article)

        # Category badge above headline
        _CATEGORY_LABELS = {
            "blood_pressure": "Blutdruck",
            "pain_tens": "Schmerz/TENS",
            "infrarot": "Infrarot/Wärme",
            "menstrual": "Menstruation",
            "other": "Sonstige",
        }
        category_label = _CATEGORY_LABELS.get(category, "")
        category_html = f'<span class="category-badge">{escape(category_label)}</span>' if category_label else ""

        # Render sections (with mid-article image after section 3)
        sections_html = HTMLRenderer._render_sections(article, mid_image, mid_alt, mid_image_raw)

        # Bottom image HTML (with placeholder if alt text exists but no image)
        bottom_image_html = ""
        if bottom_image:
            cap = f'<figcaption>{escape(bottom_alt)}</figcaption>' if bottom_alt else ""
            bottom_image_html = f'<figure><img src="{escape(bottom_image)}" alt="{escape(bottom_alt or default_alt)}" class="inline-image">{cap}</figure>'
        elif bottom_image_raw or bottom_alt:
            bottom_image_html = HTMLRenderer._render_image_placeholder(bottom_alt or "Bild 3")

        # Render intro (sanitize HTML to prevent XSS while preserving structure)
        intro_html = f'<div class="intro">{HTMLRenderer._sanitize_html(intro)}</div>' if intro else ""

        # Render direct answer as plain text (no card) - sanitize HTML
        direct_html = ""
        if direct_answer:
            direct_html = f'<div class="direct-answer"><strong>{_label(language, "direct_answer")}</strong> {HTMLRenderer._sanitize_html(direct_answer)}</div>'

        # Render TOC
        toc_html = HTMLRenderer._render_toc(article, language)

        # Render key takeaways
        takeaways_html = HTMLRenderer._render_takeaways(article, language)

        # Render FAQ
        faq_html = HTMLRenderer._render_faq(article, language)

        # Render PAA
        paa_html = HTMLRenderer._render_paa(article, language)

        # Render sources
        sources_html = HTMLRenderer._render_sources(sources, language)

        # Render tables
        tables_html = HTMLRenderer._render_tables(article.get("tables", []))

        # Hero image with figcaption (placeholder if no image yet)
        hero_figure = ""
        if hero_image:
            cap = f'<figcaption>{escape(hero_alt)}</figcaption>' if hero_alt and hero_alt != default_alt else ""
            hero_figure = f'<figure><img src="{escape(hero_image)}" alt="{escape(hero_alt)}" class="hero-image">{cap}</figure>'
        else:
            hero_figure = HTMLRenderer._render_image_placeholder(hero_alt or headline, is_hero=True)

        # Meta bar with SVG icons
        meta_html = (
            f'<div class="meta">'
            f'<span class="meta-item">{_ICON_CALENDAR} {display_date}</span>'
            f'<span class="meta-item">{_ICON_CLOCK} {reading_min} {_label(language, "reading_time")}</span>'
            f'<span class="meta-item">{_ICON_AUTHOR} {escape(author_display)}</span>'
            f'</div>'
        )

        # Last updated bar
        last_updated_html = (
            f'<div class="last-updated">'
            f'<strong>{_label(language, "last_updated")}</strong> {last_updated_display}'
        )
        if author and author.get("name"):
            last_updated_html += f' &middot; <strong>{_label(language, "medical_review")}</strong> {escape(author["name"])}'
        last_updated_html += '</div>'

        # Author card
        author_card_html = HTMLRenderer._render_author_card(author)

        # Build HTML - layout order matches Beurer blog:
        # H1 → Direct Answer → Hero Image → Takeaways → Meta → TOC → Intro → Sections
        html = f"""<!DOCTYPE html>
<html lang="{escape(language)}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(meta_title)}</title>
    <meta name="description" content="{escape(meta_desc)}">
    <meta name="author" content="{escape(author_display)}">

    <!-- Open Graph -->
    <meta property="og:title" content="{escape(meta_title)}">
    <meta property="og:description" content="{escape(meta_desc)}">
    <meta property="og:type" content="article">
    {f'<meta property="og:image" content="{escape(hero_image)}">' if hero_image else ''}

    {HTMLRenderer._render_hreflang_tags(language, hreflang_siblings or []) if hreflang_siblings else '<!-- no hreflang siblings -->'}

    <!-- Nexa font (Beurer CI) -->
    <link href="https://fonts.cdnfonts.com/css/nexa-bold" rel="stylesheet">

    <style>
        :root {{
            --primary: #C50050;
            --text: #212529;
            --text-light: #737373;
            --bg: #ffffff;
            --bg-light: #F7F7F7;
            --border: #E5E5E5;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: "Nexa", "Inter", "Helvetica Neue", Arial, system-ui, sans-serif;
            font-weight: 300;
            font-size: 17px;
            line-height: 1.7;
            color: var(--text);
            background: var(--bg);
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        strong, b {{ font-weight: 700; }}
        a {{ color: inherit; }}
        .container {{ max-width: 820px; margin: 0 auto; padding: clamp(24px, 4vw, 48px) 20px; }}

        /* --- Header / Typography --- */
        .category-badge {{
            display: inline-block;
            color: #C50050;
            font-size: .8rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .03em;
            margin-bottom: 8px;
        }}
        h1 {{
            font-size: clamp(2.2rem, 3vw + 1rem, 3.2rem);
            font-weight: 700;
            line-height: 1.1;
            letter-spacing: -0.02em;
            margin-bottom: 20px;
        }}

        /* --- Direct Answer (plain text below h1, not a card) --- */
        .direct-answer {{
            font-size: 1.05em;
            line-height: 1.7;
            margin-bottom: 32px;
        }}
        .direct-answer p {{ margin-bottom: 0; display: inline; }}

        /* --- Hero Image --- */
        figure {{ margin: 0 0 32px; }}
        figure img {{ width: 100%; height: auto; display: block; }}
        .hero-image {{ border-radius: var(--radius-md); }}
        figcaption {{
            font-size: 0.85em;
            color: var(--text-light);
            margin-top: 10px;
            line-height: 1.4;
        }}

        /* --- Key Takeaways (gray bullets, uppercase heading) --- */
        .takeaways {{
            margin: 32px 0;
            padding: 28px 32px;
            background: var(--bg-light);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
        }}
        .takeaways h2 {{
            font-size: 0.8em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 20px;
        }}
        .takeaways ul {{ list-style: none; }}
        .takeaways li {{
            margin: 14px 0;
            padding-left: 22px;
            position: relative;
            line-height: 1.6;
        }}
        .takeaways li::before {{
            content: "";
            position: absolute;
            left: 0;
            top: 10px;
            width: 8px;
            height: 8px;
            background: var(--text-light);
            border-radius: 50%;
        }}

        /* --- Meta Bar (with SVG icons) --- */
        .meta {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
            padding: 16px 0;
            border-top: 1px solid var(--border);
            border-bottom: 1px solid var(--border);
            margin: 32px 0;
            font-size: 0.88em;
            color: var(--text-light);
        }}
        .meta-item {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .meta-item svg {{ flex-shrink: 0; opacity: 0.7; }}

        /* --- TOC (clean list, no card background) --- */
        .toc {{
            margin: 0 0 40px;
            padding-bottom: 32px;
            border-bottom: 1px solid var(--border);
        }}
        .toc h2 {{
            font-size: 1em;
            font-weight: 700;
            font-style: italic;
            margin-bottom: 16px;
        }}
        .toc ol {{
            list-style: decimal;
            padding-left: 24px;
            margin: 0;
        }}
        .toc li {{
            padding: 5px 0;
            font-size: 1.05em;
            font-weight: 600;
        }}
        .toc li::marker {{ font-weight: 700; }}
        .toc a {{ color: var(--text); text-decoration: none; }}

        /* --- Intro block --- */
        .intro {{
            font-size: 1.05em;
            margin-bottom: 32px;
            padding: 24px 28px;
            background: var(--bg-light);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
        }}
        .intro p {{ margin-bottom: 12px; }}
        .intro p:last-child {{ margin-bottom: 0; }}

        /* --- Article sections --- */
        article {{ margin-top: 0; }}
        article h2 {{
            font-size: clamp(1.7rem, 1.5vw + 1rem, 2.2rem);
            font-weight: 700;
            line-height: 1.15;
            letter-spacing: -0.01em;
            margin: 48px 0 12px;
        }}
        article h2:first-child {{ margin-top: 0; }}
        article h3 {{
            font-size: clamp(1.15rem, 0.8vw + 0.9rem, 1.45rem);
            font-weight: 700;
            margin: 28px 0 8px;
        }}
        article p {{ margin-bottom: 12px; }}
        article ul, article ol {{ margin: 12px 0 12px 24px; }}
        article li {{ margin: 6px 0; line-height: 1.6; }}
        article li::marker {{ color: var(--text); }}
        article a {{
            color: var(--primary);
            text-decoration: underline;
            text-underline-offset: 2px;
            text-decoration-color: rgba(197, 0, 80, 0.3);
            text-decoration-thickness: 1px;
            transition: text-decoration-color 0.15s;
        }}
        article a:hover {{
            text-decoration-color: var(--primary);
        }}
        article sup {{
            font-size: 0.7em;
            line-height: 0;
            position: relative;
            top: -0.4em;
            vertical-align: baseline;
        }}
        .inline-image {{ width: 100%; height: auto; border-radius: var(--radius-md); }}

        /* --- Blockquote / Callout --- */
        blockquote {{
            margin: 24px 0;
            padding: 20px 24px;
            background: var(--bg-light);
            border-left: 4px solid var(--primary);
            border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
        }}
        blockquote p {{ margin-bottom: 8px; }}
        blockquote p:last-child {{ margin-bottom: 0; }}

        /* --- Sources --- */
        .sources {{
            margin: 48px 0 0;
            padding-top: 24px;
            border-top: 1px solid var(--border);
        }}
        .sources h2 {{ font-size: 1em; font-weight: 700; margin-bottom: 12px; }}
        .sources ol {{ margin: 0 0 0 20px; font-size: 0.88em; color: var(--text-light); }}
        .sources li {{ margin: 8px 0; line-height: 1.5; }}
        .sources a {{
            color: var(--text-light);
            text-decoration: underline;
            text-underline-offset: 2px;
        }}
        .source-description {{ color: var(--text-light); font-size: 0.92em; margin-top: 2px; }}

        /* --- FAQ / PAA --- */
        .faq, .paa {{ margin: 40px 0; }}
        .faq h2, .paa h2 {{ font-size: 1.4em; font-weight: 700; margin-bottom: 20px; }}
        .faq-item, .paa-item {{
            margin: 12px 0;
            padding: 20px 24px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
        }}
        .faq-item h3, .paa-item h3 {{
            font-size: 1.02em;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--text);
        }}
        .faq-item p, .paa-item p {{ color: var(--text-light); font-size: 0.95em; line-height: 1.6; }}

        /* --- Image Placeholder --- */
        .image-placeholder {{
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 12px;
            background: var(--bg-light);
            border: 2px dashed var(--border);
            border-radius: var(--radius-md);
            padding: 48px 24px;
            margin: 0 0 32px;
            color: var(--text-light);
            font-size: 0.9em;
            min-height: 200px;
        }}
        .image-placeholder.hero {{
            min-height: 320px;
            border-radius: var(--radius-lg);
        }}
        .image-placeholder svg {{ opacity: 0.4; }}
        .image-placeholder span {{ max-width: 400px; text-align: center; line-height: 1.4; }}

        /* --- Last Updated Bar --- */
        .last-updated {{
            font-size: 0.85em;
            color: var(--text-light);
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }}

        /* --- Author Card --- */
        .author-card {{
            display: flex;
            gap: 20px;
            margin: 48px 0 0;
            padding: 28px;
            background: var(--bg-light);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
        }}
        .author-card-image {{
            flex-shrink: 0;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            overflow: hidden;
            background: var(--border);
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .author-card-image img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .author-card-image svg {{ opacity: 0.4; }}
        .author-card-info {{ flex: 1; min-width: 0; }}
        .author-card-info h4 {{
            font-size: 1.05em;
            font-weight: 700;
            margin-bottom: 2px;
        }}
        .author-card-title {{
            font-size: 0.88em;
            color: var(--text-light);
            margin-bottom: 8px;
        }}
        .author-card-bio {{
            font-size: 0.92em;
            line-height: 1.5;
            color: var(--text);
            margin-bottom: 12px;
        }}
        .author-credentials {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .credential-badge {{
            display: inline-block;
            font-size: 0.78em;
            font-weight: 600;
            padding: 4px 10px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 20px;
            color: var(--text-light);
        }}
        .author-card-links {{
            display: flex;
            gap: 12px;
            margin-top: 8px;
        }}
        .author-card-links a {{
            color: var(--text-light);
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 0.85em;
        }}

        /* --- Comparison Tables --- */
        .comparison-table {{
            margin: 32px 0;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            overflow: hidden;
        }}
        .comparison-table h3 {{ font-size: 1.05em; font-weight: 700; padding: 16px 20px 8px; }}
        .comparison-table table {{ width: 100%; border-collapse: collapse; font-size: 0.92em; }}
        .comparison-table th, .comparison-table td {{ padding: 12px 16px; text-align: left; }}
        .comparison-table th {{ background: #FAFAFA; font-weight: 700; border-bottom: 2px solid var(--border); }}
        .comparison-table td {{ border-bottom: 1px solid var(--border); }}
        .comparison-table tr:last-child td {{ border-bottom: none; }}
    </style>
</head>
<body>
    <header class="container">
        {category_html}
        <h1>{escape(headline)}</h1>
        {direct_html}
    </header>

    <main class="container">
        {hero_figure}

        {takeaways_html}

        {meta_html}

        {last_updated_html}

        {toc_html}

        {intro_html}

        <article>
            {sections_html}
        </article>

        {bottom_image_html}

        {tables_html}
        {paa_html}
        {faq_html}
        {sources_html}
        {author_card_html}
    </main>
</body>
</html>"""

        return html

    @staticmethod
    def _sanitize_html(html: str) -> str:
        """Sanitize HTML content by removing dangerous elements."""
        if not html:
            return ""

        # Remove script tags and content
        sanitized = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        # Remove style tags and content
        sanitized = re.sub(r'<style[^>]*>.*?</style>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        # Remove iframe tags (can embed malicious content)
        sanitized = re.sub(r'<iframe[^>]*>.*?</iframe>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'<iframe[^>]*/>', '', sanitized, flags=re.IGNORECASE)
        # Remove object/embed tags (can embed Flash/plugins)
        sanitized = re.sub(r'<object[^>]*>.*?</object>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r'<embed[^>]*/?>', '', sanitized, flags=re.IGNORECASE)
        # Remove form tags (prevent phishing)
        sanitized = re.sub(r'<form[^>]*>.*?</form>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
        # Remove event handlers (onclick, onload, onerror, etc.)
        sanitized = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'\s*on\w+\s*=\s*\S+', '', sanitized, flags=re.IGNORECASE)
        # Remove javascript: URLs
        sanitized = re.sub(r'href\s*=\s*["\']javascript:[^"\']*["\']', 'href="#"', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'src\s*=\s*["\']javascript:[^"\']*["\']', 'src=""', sanitized, flags=re.IGNORECASE)
        # Remove data: URLs (can contain executable content)
        sanitized = re.sub(r'href\s*=\s*["\']data:[^"\']*["\']', 'href="#"', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'src\s*=\s*["\']data:(?!image/)[^"\']*["\']', 'src=""', sanitized, flags=re.IGNORECASE)
        # Remove base tags (can hijack relative URLs)
        sanitized = re.sub(r'<base[^>]*/?>', '', sanitized, flags=re.IGNORECASE)
        # Remove meta refresh (can redirect)
        sanitized = re.sub(r'<meta[^>]*http-equiv\s*=\s*["\']refresh["\'][^>]*/?>', '', sanitized, flags=re.IGNORECASE)

        return sanitized

    @staticmethod
    def _render_sections(article: Dict[str, Any], mid_image: str, mid_alt: str, mid_image_raw: str = "") -> str:
        """Render article sections."""
        parts = []

        for i in range(1, 10):
            title = article.get(f"section_{i:02d}_title", "")
            content = article.get(f"section_{i:02d}_content", "")

            if not title and not content:
                continue

            anchor = f"section-{i}"
            if title:
                clean_title = HTMLRenderer._strip_html(title)
                parts.append(f'<h2 id="{anchor}">{escape(clean_title)}</h2>')

            if content and content.strip():
                # Sanitize HTML content to prevent XSS
                sanitized = HTMLRenderer._sanitize_html(content)
                # Wrap bare <table> elements in .comparison-table for styling
                sanitized = re.sub(
                    r'(?<!comparison-table">)(<table[\s>].*?</table>)',
                    r'<div class="comparison-table">\1</div>',
                    sanitized,
                    flags=re.DOTALL,
                )
                parts.append(sanitized)

            # Mid-article image after section 3
            if i == 3:
                if mid_image:
                    cap = f'<figcaption>{escape(mid_alt)}</figcaption>' if mid_alt else ""
                    parts.append(f'<figure><img src="{escape(mid_image)}" alt="{escape(mid_alt)}" class="inline-image">{cap}</figure>')
                elif mid_image_raw or mid_alt:
                    parts.append(HTMLRenderer._render_image_placeholder(mid_alt or "Bild 2"))

        return '\n'.join(parts)

    @staticmethod
    def _render_toc(article: Dict[str, Any], language: str = "de") -> str:
        """Render table of contents."""
        items = []

        for i in range(1, 10):
            title = article.get(f"section_{i:02d}_title", "")
            if title:
                anchor = f"section-{i}"
                clean_title = HTMLRenderer._strip_html(title)
                # Shorten for TOC (max 8 words for better readability)
                words = clean_title.split()[:8]
                short_title = ' '.join(words)
                if len(words) < len(clean_title.split()):
                    short_title += " ..."
                items.append(f'<li><a href="#{anchor}">{escape(short_title)}</a></li>')

        if not items:
            return ""

        return f"""<nav class="toc">
            <h2>{_label(language, "toc")}</h2>
            <ol>
                {''.join(items)}
            </ol>
        </nav>"""

    @staticmethod
    def _render_takeaways(article: Dict[str, Any], language: str = "de") -> str:
        """Render key takeaways."""
        items = []
        for i in range(1, 4):
            takeaway = article.get(f"key_takeaway_{i:02d}", "")
            if takeaway:
                items.append(f"<li>{escape(takeaway)}</li>")

        if not items:
            return ""

        return f"""<section class="takeaways">
            <h2>{_label(language, "takeaways")}</h2>
            <ul>{''.join(items)}</ul>
        </section>"""

    @staticmethod
    def _render_faq(article: Dict[str, Any], language: str = "de") -> str:
        """Render FAQ section."""
        items = []
        for i in range(1, 7):
            q = article.get(f"faq_{i:02d}_question", "")
            a = article.get(f"faq_{i:02d}_answer", "")
            if q and a:
                # Escape answer to prevent XSS (FAQ answers should be plain text)
                items.append(f'<div class="faq-item"><h3>{escape(q)}</h3><p>{escape(a)}</p></div>')

        if not items:
            return ""

        return f"""<section class="faq">
            <h2>{_label(language, "faq")}</h2>
            {''.join(items)}
        </section>"""

    @staticmethod
    def _render_paa(article: Dict[str, Any], language: str = "de") -> str:
        """Render People Also Ask section."""
        items = []
        for i in range(1, 5):
            q = article.get(f"paa_{i:02d}_question", "")
            a = article.get(f"paa_{i:02d}_answer", "")
            if q and a:
                # Escape answer to prevent XSS (PAA answers should be plain text)
                items.append(f'<div class="paa-item"><h3>{escape(q)}</h3><p>{escape(a)}</p></div>')

        if not items:
            return ""

        return f"""<section class="paa">
            <h2>{_label(language, "paa")}</h2>
            {''.join(items)}
        </section>"""

    @staticmethod
    def _render_sources(sources, language: str = "de") -> str:
        """Render sources section."""
        if not sources:
            return ""

        # New format: list of Source objects or dicts
        if isinstance(sources, list):
            items = []
            for s in sources:
                if hasattr(s, 'title') or isinstance(s, dict):
                    # Extract values
                    if hasattr(s, 'title'):
                        title = getattr(s, 'title', "") or ""
                        url = getattr(s, 'url', "") or ""
                        desc = getattr(s, 'description', "") or ""
                    else:
                        title = s.get("title") or ""
                        url = s.get("url") or ""
                        desc = s.get("description") or ""

                    if url:
                        display_title = title if title and len(title) > 2 else url
                        desc_html = f'<div class="source-description">{escape(desc)}</div>' if desc else ""

                        items.append(
                            f'<li>'
                            f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">'
                            f'{escape(display_title)}'
                            f'</a>'
                            f'{desc_html}'
                            f'</li>'
                        )

            if not items:
                return ""
            return f"""<section class="sources">
                <h2>{_label(language, "sources")}</h2>
                <ol class="sources-list" type="A">{"".join(items)}</ol>
            </section>"""

        # Fallback for plain string format
        return f"""<section class="sources">
            <h2>{_label(language, "sources")}</h2>
            <ol class="sources-list" type="A"><li>{escape(str(sources))}</li></ol>
        </section>"""

    @staticmethod
    def _render_tables(tables) -> str:
        """Render comparison tables."""
        if not tables:
            return ""

        parts = []
        for table in tables:
            # Handle both dict and Pydantic model
            if hasattr(table, 'title'):
                title = table.title
                headers = table.headers
                rows = table.rows
            else:
                title = table.get('title', '')
                headers = table.get('headers', [])
                rows = table.get('rows', [])

            if not headers or not rows:
                continue

            header_html = ''.join(f'<th>{escape(h)}</th>' for h in headers)
            rows_html = ''
            for row in rows:
                cells = ''.join(f'<td>{escape(str(c))}</td>' for c in row)
                rows_html += f'<tr>{cells}</tr>'

            parts.append(f'''<div class="comparison-table">
                <h3>{escape(title)}</h3>
                <table>
                    <thead><tr>{header_html}</tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>''')

        return '\n'.join(parts)

    @staticmethod
    def _render_image_placeholder(alt_text: str, is_hero: bool = False) -> str:
        """Render a placeholder box where an image will go."""
        hero_class = " hero" if is_hero else ""
        icon = (
            '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="3" y="3" width="18" height="18" rx="2"/>'
            '<circle cx="8.5" cy="8.5" r="1.5"/>'
            '<path d="m21 15-5-5L5 21"/></svg>'
        )
        label = escape(alt_text) if alt_text else "Bild-Platzhalter"
        return (
            f'<div class="image-placeholder{hero_class}">'
            f'{icon}'
            f'<span>{label}</span>'
            f'</div>'
        )

    @staticmethod
    def _render_author_card(author: Optional[Dict[str, Any]]) -> str:
        """Render author card at bottom of article (Beurer blog style)."""
        if not author or not author.get("name"):
            return ""

        name = escape(author["name"])
        title = escape(author.get("title", ""))
        bio = escape(author.get("bio", ""))
        image_url = author.get("image_url", "")
        credentials = author.get("credentials", [])
        linkedin_url = author.get("linkedin_url", "")

        # Author image or placeholder
        if image_url:
            image_html = f'<img src="{escape(image_url)}" alt="{name}">'
        else:
            image_html = (
                '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" '
                'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
                '<circle cx="12" cy="7" r="4"/></svg>'
            )

        title_html = f'<div class="author-card-title">{title}</div>' if title else ""
        bio_html = f'<p class="author-card-bio">{bio}</p>' if bio else ""

        # Credentials badges
        creds_html = ""
        if credentials:
            badges = "".join(f'<span class="credential-badge">{escape(c)}</span>' for c in credentials)
            creds_html = f'<div class="author-credentials">{badges}</div>'

        # Social links
        links_html = ""
        if linkedin_url:
            links_html = (
                '<div class="author-card-links">'
                f'<a href="{escape(linkedin_url)}" target="_blank" rel="noopener noreferrer">LinkedIn</a>'
                '</div>'
            )

        return (
            '<div class="author-card">'
            f'<div class="author-card-image">{image_html}</div>'
            '<div class="author-card-info">'
            f'<h4>{name}</h4>'
            f'{title_html}'
            f'{bio_html}'
            f'{creds_html}'
            f'{links_html}'
            '</div>'
            '</div>'
        )

    @staticmethod
    def _is_just_domain(title: str, url: str) -> bool:
        """Check if title is just the domain name from the URL."""
        if not title or not url: return False
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower().replace('www.', '')
            title_clean = title.lower().strip().replace('www.', '')
            return domain == title_clean or domain.split('.')[0] == title_clean
        except:
            return False

    @staticmethod
    def _strip_html(text: str) -> str:
        """Strip HTML tags and decode entities."""
        if not text:
            return ""
        clean = re.sub(r'<[^>]+>', '', str(text))
        return unescape(clean).strip()

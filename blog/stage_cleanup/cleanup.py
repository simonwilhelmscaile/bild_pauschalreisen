"""
HTML Cleanup Stage - Clean and validate article content.

Matches TypeScript stage-08-cleanup.ts functionality:
- Remove empty HTML tags (paragraphs, divs, spans, headings, lists)
- Fix unclosed tags
- Normalize quotes and whitespace
- Remove control characters
- Validate article structure
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationStats:
    """Article validation statistics."""
    total_sections: int = 0
    total_faqs: int = 0
    total_paas: int = 0
    has_intro: bool = False
    has_direct_answer: bool = False


@dataclass
class CleanupResult:
    """Result of cleanup operation."""
    valid: bool = True
    warnings: List[str] = field(default_factory=list)
    stats: ValidationStats = field(default_factory=ValidationStats)
    fields_cleaned: int = 0


def _sync_footnotes_with_sources(article: Dict[str, Any]) -> int:
    """Remove orphaned footnote markers and re-letter remaining ones to match sources.

    When Stage 4 removes a source (e.g. due to 404), the corresponding
    <sup>X</sup> marker in the body text becomes orphaned. This function:
    1. Identifies which footnote letters still have a corresponding source
    2. Removes orphaned <sup>X</sup> markers from all content fields
    3. Re-letters remaining footnotes sequentially (A, B, C, ...)

    Returns the number of orphaned footnotes removed.
    """
    sources = article.get("Sources", [])
    source_count = len(sources) if isinstance(sources, list) else 0

    content_fields = ["Intro", "Direct_Answer"]
    for i in range(1, 10):
        content_fields.append(f"section_{i:02d}_content")

    # Collect all footnote letters used across content fields
    all_letters = set()
    for field_name in content_fields:
        content = article.get(field_name, "")
        if isinstance(content, str):
            for m in re.finditer(r'<sup>([A-Z])</sup>', content):
                all_letters.add(m.group(1))

    if not all_letters:
        return 0

    # Valid letters are A..{source_count} (A=first source, B=second, etc.)
    valid_letters = {chr(ord('A') + i) for i in range(source_count)}
    orphaned_letters = all_letters - valid_letters

    if not orphaned_letters:
        return 0  # No sources were removed, nothing to sync

    # Build re-letter mapping: keep only letters that have a source,
    # then re-assign sequentially starting from A
    sorted_valid = sorted(all_letters & valid_letters)
    remap = {}
    for new_idx, old_letter in enumerate(sorted_valid):
        new_letter = chr(ord('A') + new_idx)
        if old_letter != new_letter:
            remap[old_letter] = new_letter

    for field_name in content_fields:
        content = article.get(field_name, "")
        if not isinstance(content, str) or '<sup>' not in content:
            continue

        original = content

        # Remove orphaned footnotes (strip the <sup>X</sup> entirely)
        for letter in orphaned_letters:
            content = content.replace(f'<sup>{letter}</sup>', '')

        # Re-letter remaining footnotes if needed
        if remap:
            # Use placeholder to avoid collisions: <sup>C</sup> -> <sup>__66__</sup>
            temp_map = {}
            for old_letter, new_letter in remap.items():
                placeholder = f'__{ord(new_letter)}__'
                content = content.replace(f'<sup>{old_letter}</sup>', f'<sup>{placeholder}</sup>')
                temp_map[placeholder] = new_letter
            for placeholder, new_letter in temp_map.items():
                content = content.replace(f'<sup>{placeholder}</sup>', f'<sup>{new_letter}</sup>')

        if content != original:
            article[field_name] = content

    return len(orphaned_letters)


def _capitalize_sentence_starts(html: str) -> str:
    """Ensure the first letter after sentence-ending punctuation is uppercase.

    After Sie→Du conversion, 'du/dir/dein/deine' may be left lowercase at
    sentence start. This deterministic pass capitalizes any lowercase letter
    that follows a sentence boundary (`. `, `! `, `? `) or an HTML block-open
    tag (`<p>`, `<li>`).

    Only touches the very first alphabetic character after the boundary;
    leaves everything else intact.
    """
    if not html:
        return html

    # Pattern: sentence-ending punctuation + whitespace + lowercase letter
    # Also handle after HTML block tags that start a new visual sentence
    result = re.sub(
        r'([.!?]\s+|<(?:p|li)>\s*)([a-zäöü])',
        lambda m: m.group(1) + m.group(2).upper(),
        html,
    )
    return result


def _check_sie_form(article: Dict[str, Any]) -> List[str]:
    """Detect formal 'Sie' (formal you) in article content.

    After the Du-form switch, 'Sie/Ihnen/Ihr/Ihre' as formal address should
    never appear. Returns list of warnings with field name and match context.

    Note: May produce false positives for third-person plural 'Sie' (they)
    at sentence start, since German capitalizes the first word. These are
    warnings for human review, not auto-corrections.
    """
    # Patterns that indicate formal address (not third-person 'sie' = they/she)
    # Match 'Sie' followed by verb or at sentence boundaries typical of formal address
    # Also catch 'Ihnen', 'Ihr/Ihre/Ihrem/Ihres' (possessive formal)
    formal_patterns = [
        # "Sie" as formal you — preceded by sentence-start or comma, followed by verb-like word
        r'(?:^|[.!?]\s+|,\s+)Sie\s+(?:können|sollten|müssen|haben|sind|werden|möchten|finden|messen|nutzen|verwenden|erhalten|brauchen)',
        # Formal possessive pronouns (always capitalized mid-sentence = formal)
        r'(?<!\. )(?<=\s)Ihren?\b',
        r'(?<=\s)Ihrem\b',
        r'(?<=\s)Ihres\b',
        r'(?<=\s)Ihnen\b',
        # "mit Ihrem Arzt" / "an Ihren Arzt" patterns
        r'(?:mit|an|von|für|bei)\s+Ihr(?:em|en|er)\b',
    ]

    content_fields = ["Intro", "Direct_Answer"]
    for i in range(1, 10):
        content_fields.append(f"section_{i:02d}_content")
    for i in range(1, 7):
        content_fields.append(f"faq_{i:02d}_answer")
    for i in range(1, 5):
        content_fields.append(f"paa_{i:02d}_answer")

    warnings = []
    for field_name in content_fields:
        content = article.get(field_name, "")
        if not isinstance(content, str) or not content:
            continue
        # Strip HTML tags for text analysis
        plain = re.sub(r'<[^>]+>', '', content)
        for pattern in formal_patterns:
            matches = re.findall(pattern, plain)
            if matches:
                warnings.append(
                    f"Formal 'Sie' detected in {field_name}: "
                    f"found {len(matches)} occurrence(s) — should use Du-Form"
                )
                break  # One warning per field is enough

    return warnings


def _check_footnote_count(article: Dict[str, Any]) -> Optional[str]:
    """Check if superscript letter count matches source count. Returns warning or None."""
    sources = article.get("Sources", [])
    if not sources or not isinstance(sources, list):
        return None

    source_count = len(sources)
    seen_letters = set()

    # Check all content fields for <sup> tags
    content_fields = ["Intro", "Direct_Answer"]
    for i in range(1, 10):
        content_fields.append(f"section_{i:02d}_content")

    for field_name in content_fields:
        content = article.get(field_name, "")
        if isinstance(content, str):
            for m in re.finditer(r'<sup>([A-Z])</sup>', content):
                seen_letters.add(m.group(1))

    if seen_letters and len(seen_letters) != source_count:
        return (
            f"Footnote/source count mismatch: {len(seen_letters)} unique footnote letters "
            f"but {source_count} sources"
        )
    return None


def run_cleanup(article: Dict[str, Any]) -> CleanupResult:
    """
    Clean HTML content and validate article structure.

    Args:
        article: Article dictionary to clean (modified in place)

    Returns:
        CleanupResult with validation info and stats
    """
    logger.info("[Cleanup] Starting HTML cleanup stage...")

    result = CleanupResult()

    # Fields to clean
    fields_to_clean = [
        "Intro",
        "Direct_Answer",
    ]

    # Add section content fields
    for i in range(1, 10):
        fields_to_clean.append(f"section_{i:02d}_content")

    # Add FAQ answer fields
    for i in range(1, 7):
        fields_to_clean.append(f"faq_{i:02d}_answer")

    # Add PAA answer fields
    for i in range(1, 5):
        fields_to_clean.append(f"paa_{i:02d}_answer")

    # Clean each field
    for field_name in fields_to_clean:
        original = article.get(field_name, "")
        if isinstance(original, str) and original:
            cleaned = _clean_html(original)
            if cleaned != original:
                article[field_name] = cleaned
                result.fields_cleaned += 1

    logger.info(f"[Cleanup] Cleaned {result.fields_cleaned} fields")

    # Fix sentence-start capitalization (catches lowercase du/dir/dein after Sie→Du conversion)
    for field_name in fields_to_clean:
        content = article.get(field_name, "")
        if isinstance(content, str) and content:
            fixed = _capitalize_sentence_starts(content)
            if fixed != content:
                article[field_name] = fixed
                logger.debug(f"[Cleanup] Capitalized sentence start(s) in {field_name}")

    # Validate article structure
    validation = _validate_article_structure(article)
    result.valid = len(validation["warnings"]) == 0
    result.warnings = validation["warnings"]
    result.stats = validation["stats"]

    # Sync footnotes with sources (remove orphaned markers, re-letter)
    orphaned = _sync_footnotes_with_sources(article)
    if orphaned:
        logger.info(f"[Cleanup] Removed {orphaned} orphaned footnote marker(s)")

    # Check footnote/source count (should pass after sync)
    fn_warning = _check_footnote_count(article)
    if fn_warning:
        result.warnings.append(fn_warning)

    # Check for formal Sie-Form (should be Du-Form)
    sie_warnings = _check_sie_form(article)
    result.warnings.extend(sie_warnings)

    if result.warnings:
        logger.warning(f"[Cleanup] Validation warnings: {result.warnings}")

    logger.info("[Cleanup] Cleanup stage completed")
    return result


def _normalize_whitespace(html: str) -> str:
    """Fix common spacing issues around punctuation, parentheses, and HTML tags.

    Fixes LLM-generated spacing errors like:
    - "TENS (Transkutane...)ist" -> "TENS (Transkutane...) ist"
    - "</strong>text" -> "</strong> text"
    - "text<strong>" -> "text <strong>"
    """
    if not html:
        return html

    result = html

    # Space before ( unless preceded by whitespace or > (tag close)
    result = re.sub(r'(?<=[^\s>])\(', ' (', result)

    # Space after ) unless followed by punctuation or < (tag open)
    result = re.sub(r'\)(?=[^\s,.:;!?<)])', ') ', result)

    # Space after sentence-ending punctuation unless followed by </ (closing tag) or end
    result = re.sub(r'([.:;])(?=[A-Za-z\u00C0-\u024F])', r'\1 ', result)

    # Space at tag-text boundaries: </tag>text -> </tag> text
    result = re.sub(r'(</(?:strong|em|a|b|i|span)>)(?=[A-Za-z\u00C0-\u024F0-9])', r'\1 ', result)

    # Space at tag-text boundaries: text<tag> -> text <tag>
    result = re.sub(r'([A-Za-z\u00C0-\u024F0-9])(<(?:strong|em|a\s|b>|i>|span))', r'\1 \2', result)

    return result


def _clean_html(html: str) -> str:
    """
    Clean HTML content.

    Removes:
    - Empty paragraphs, divs, spans, headings, list items, lists
    - Multiple consecutive spaces/line breaks
    - Leading/trailing whitespace in tags
    - Control characters

    Fixes:
    - Unclosed tags (basic fix)
    - Quote normalization
    """
    if not html:
        return ""

    cleaned = html

    # 1. Remove empty paragraphs
    cleaned = re.sub(r'<p>\s*</p>', '', cleaned, flags=re.IGNORECASE)

    # 2. Remove empty divs
    cleaned = re.sub(r'<div>\s*</div>', '', cleaned, flags=re.IGNORECASE)

    # 3. Remove empty spans
    cleaned = re.sub(r'<span>\s*</span>', '', cleaned, flags=re.IGNORECASE)

    # 4. Remove empty headings
    cleaned = re.sub(r'<h[1-6]>\s*</h[1-6]>', '', cleaned, flags=re.IGNORECASE)

    # 5. Remove empty list items
    cleaned = re.sub(r'<li>\s*</li>', '', cleaned, flags=re.IGNORECASE)

    # 6. Remove empty lists
    cleaned = re.sub(r'<ul>\s*</ul>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<ol>\s*</ol>', '', cleaned, flags=re.IGNORECASE)

    # 7. Fix multiple consecutive spaces
    cleaned = re.sub(r' {2,}', ' ', cleaned)

    # 8. Fix multiple consecutive line breaks
    cleaned = re.sub(r'(\n\s*){3,}', '\n\n', cleaned)

    # 9. Remove whitespace between block-level tags only (preserve spaces between inline tags)
    cleaned = re.sub(r'>([ \t]*\n\s*)<', '><', cleaned)

    # 10. Fix unclosed tags (basic)
    cleaned = _fix_unclosed_tags(cleaned)

    # 11. Normalize quotes
    cleaned = cleaned.replace('"', '"').replace('"', '"')
    cleaned = cleaned.replace(''', "'").replace(''', "'")

    # 12. Remove control characters
    cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', cleaned)

    # 13. Strip zero-width and invisible Unicode characters
    # U+200B zero-width space, U+FEFF BOM, U+200C zero-width non-joiner,
    # U+200D zero-width joiner, U+2060 word joiner, U+FFFE non-character
    cleaned = re.sub(r'[\u200b\ufeff\u200c\u200d\u2060\ufffe]', '', cleaned)

    # 14. Normalize whitespace around punctuation and tags
    cleaned = _normalize_whitespace(cleaned)

    return cleaned.strip()


def _fix_unclosed_tags(html: str) -> str:
    """
    Fix basic unclosed tag issues.

    Counts opening and closing tags for common elements
    and adds missing closing tags at the end.
    """
    tags = ['p', 'div', 'span', 'strong', 'em', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4']

    for tag in tags:
        # Count opening tags (with or without attributes)
        open_pattern = rf'<{tag}(?:\s[^>]*)?>'.lower()
        open_count = len(re.findall(open_pattern, html.lower()))

        # Count closing tags
        close_pattern = rf'</{tag}>'.lower()
        close_count = len(re.findall(close_pattern, html.lower()))

        # If more opens than closes, add closing tags at the end
        if open_count > close_count:
            diff = open_count - close_count
            html += f'</{tag}>' * diff

    return html


def _validate_article_structure(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate article structure.

    Checks:
    - Required fields (meta_title, Intro, Direct_Answer)
    - Meta title length (max 60 chars)
    - Section count
    - FAQ/PAA count
    """
    warnings = []
    stats = ValidationStats()

    # Check meta_title
    meta_title = article.get("Meta_Title", "")
    if not meta_title:
        warnings.append("Missing Meta_Title")
    elif len(meta_title) > 60:
        warnings.append(f"Meta_Title too long: {len(meta_title)} chars (max 60)")

    # Check Intro
    intro = article.get("Intro", "")
    stats.has_intro = bool(intro and intro.strip())
    if not stats.has_intro:
        warnings.append("Missing or empty Intro")

    # Check Direct_Answer
    direct_answer = article.get("Direct_Answer", "")
    stats.has_direct_answer = bool(direct_answer and direct_answer.strip())
    if not stats.has_direct_answer:
        warnings.append("Missing or empty Direct_Answer")

    # Count sections
    for i in range(1, 10):
        title = article.get(f"section_{i:02d}_title", "")
        content = article.get(f"section_{i:02d}_content", "")
        if title and content and content.strip():
            stats.total_sections += 1

    if stats.total_sections == 0:
        warnings.append("No sections with content found")

    # Count FAQs
    for i in range(1, 7):
        question = article.get(f"faq_{i:02d}_question", "")
        answer = article.get(f"faq_{i:02d}_answer", "")
        if question and answer and answer.strip():
            stats.total_faqs += 1

    # Count PAAs
    for i in range(1, 5):
        question = article.get(f"paa_{i:02d}_question", "")
        answer = article.get(f"paa_{i:02d}_answer", "")
        if question and answer and answer.strip():
            stats.total_paas += 1

    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "stats": stats,
    }

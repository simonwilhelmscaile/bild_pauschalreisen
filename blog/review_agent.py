"""Review agent — analyzes article feedback and updates context/persona files.

Triggered as a background task when an article is approved. Extracts
generalizable learnings from feedback_history and article_comments,
then appends them to blog/context.md (## Learnings) and
blog/persona.md (## Tone Refinements).
"""
import json
import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from db.client import get_beurer_supabase
from services.gemini import get_generative_model

logger = logging.getLogger(__name__)

_BLOG_DIR = Path(__file__).parent
_file_lock = threading.Lock()


async def run_review(article_id: str) -> None:
    """Main entry point. Fetch article + feedback, analyze, update files."""
    supabase = get_beurer_supabase()

    # Fetch article
    result = (
        supabase.table("blog_articles")
        .select("id, keyword, headline, feedback_history")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning("Review agent: article %s not found", article_id)
        return

    article = result.data[0]

    # Fetch comments
    comments_result = (
        supabase.table("article_comments")
        .select("author, comment_text, created_at")
        .eq("article_id", article_id)
        .order("created_at", desc=False)
        .execute()
    )
    comments = comments_result.data or []

    # Compile feedback
    feedback_text = _compile_feedback(article, comments)
    if not feedback_text:
        logger.info("Review agent: no feedback for article %s, skipping", article_id)
        return

    # Read current learnings sections
    context_md = _read_file("context.md")
    persona_md = _read_file("persona.md")
    current_learnings = _get_section_content(context_md, "Learnings") if context_md else ""
    current_refinements = _get_section_content(persona_md, "Tone Refinements") if persona_md else ""

    # Analyze with LLM
    analysis = await _analyze_feedback(
        article, feedback_text, current_learnings, current_refinements
    )
    if not analysis:
        return

    # Append learnings to files
    if analysis.get("context_learnings"):
        _append_to_section(
            _BLOG_DIR / "context.md", "Learnings", analysis["context_learnings"]
        )
        logger.info("Review agent: appended %d context learnings", len(analysis["context_learnings"]))

    if analysis.get("persona_learnings"):
        _append_to_section(
            _BLOG_DIR / "persona.md", "Tone Refinements", analysis["persona_learnings"]
        )
        logger.info("Review agent: appended %d persona learnings", len(analysis["persona_learnings"]))

    # Save review result to feedback_history
    _save_review_result(supabase, article_id, analysis)
    logger.info("Review agent: completed for article %s", article_id)


def _compile_feedback(article: Dict[str, Any], comments: List[Dict]) -> str:
    """Build a text summary from feedback_history and article_comments."""
    parts = []

    feedback_history = article.get("feedback_history") or []
    for entry in feedback_history:
        entry_type = entry.get("type", "")
        if entry_type == "feedback":
            parts.append(f"[Regeneration feedback] {entry.get('feedback', '')}")
        elif entry_type == "inline_edit":
            original = entry.get("original_text", "")
            replacement = entry.get("replacement_text", "")
            reason = entry.get("reason", "")
            parts.append(
                f"[Inline edit] Changed: \"{original}\" → \"{replacement}\""
                + (f" (Reason: {reason})" if reason else "")
            )

    for comment in comments:
        author = comment.get("author", "reviewer")
        text = comment.get("comment_text", "")
        parts.append(f"[Comment by {author}] {text}")

    return "\n".join(parts)


def _read_file(filename: str) -> Optional[str]:
    """Read a file from the blog directory."""
    path = _BLOG_DIR / filename
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _get_section_content(text: str, header: str) -> str:
    """Extract content under a ## header."""
    pattern = rf"^## {re.escape(header)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


async def _analyze_feedback(
    article: Dict[str, Any],
    feedback_text: str,
    current_learnings: str,
    current_refinements: str,
) -> Optional[Dict[str, Any]]:
    """Call Gemini to extract generalizable learnings from feedback."""
    prompt = f"""You are a content strategy analyst. An article was reviewed and approved with feedback.
Extract ONLY generalizable learnings — patterns that should apply to ALL future articles, not fixes specific to this one article.

Article keyword: {article.get('keyword', 'unknown')}
Article headline: {article.get('headline', 'unknown')}

All feedback received:
{feedback_text}

Current content strategy learnings (avoid duplicating these):
{current_learnings or '(none yet)'}

Current tone/voice refinements (avoid duplicating these):
{current_refinements or '(none yet)'}

Return a JSON object with exactly these keys:
- "context_learnings": array of strings — generalizable content strategy insights (e.g., "Always include a practical checklist at the end of how-to articles"). Empty array if none.
- "persona_learnings": array of strings — generalizable voice/tone refinements (e.g., "Avoid starting paragraphs with questions — use statements instead"). Empty array if none.
- "summary": string — one-sentence summary of what was learned.

Rules:
- Only include learnings that apply broadly, not article-specific corrections
- Do not repeat anything already in the current learnings/refinements
- Each learning should be a concise, actionable bullet point in German
- If no generalizable learnings exist, return empty arrays
- Return ONLY valid JSON, no markdown fencing"""

    try:
        model = get_generative_model("gemini-2.0-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        return json.loads(text)
    except Exception as e:
        logger.error("Review agent: LLM analysis failed: %s", e)
        return None


def _append_to_section(file_path: Path, section_name: str, items: List[str]) -> None:
    """Append bullet points to a ## section in a markdown file. Thread-safe."""
    if not items:
        return

    with _file_lock:
        text = file_path.read_text(encoding="utf-8")

        # Find the section header
        pattern = rf"(^## {re.escape(section_name)}\s*\n)"
        m = re.search(pattern, text, re.MULTILINE)
        if not m:
            logger.warning("Review agent: section '%s' not found in %s", section_name, file_path)
            return

        # Find where the section ends (next ## or EOF)
        section_start = m.end()
        next_header = re.search(r"^## ", text[section_start:], re.MULTILINE)
        insert_pos = section_start + next_header.start() if next_header else len(text)

        # Build new bullet points
        new_lines = "\n".join(f"- {item}" for item in items) + "\n"

        # Ensure there's a newline before we insert
        if insert_pos > 0 and text[insert_pos - 1] != "\n":
            new_lines = "\n" + new_lines

        text = text[:insert_pos] + new_lines + text[insert_pos:]
        file_path.write_text(text, encoding="utf-8")


def _save_review_result(
    supabase, article_id: str, analysis: Dict[str, Any]
) -> None:
    """Append a review_agent entry to the article's feedback_history."""
    result = (
        supabase.table("blog_articles")
        .select("feedback_history")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return

    history = result.data[0].get("feedback_history") or []
    history.append({
        "type": "review_agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": analysis.get("summary", ""),
        "context_learnings": analysis.get("context_learnings", []),
        "persona_learnings": analysis.get("persona_learnings", []),
    })

    supabase.table("blog_articles").update({
        "feedback_history": history,
    }).eq("id", article_id).execute()

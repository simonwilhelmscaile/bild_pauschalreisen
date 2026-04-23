"""Regenerate blog articles created before 2026-03-10.

These articles predate critical compliance and tone updates:
- No-healing-promises compliance rules
- Expanded banned words list
- Replacement validator in Stage 3
- Quality check safety rules

Usage:
    python scripts/regenerate_old_articles.py --dry-run
    python scripts/regenerate_old_articles.py --limit 1
    python scripts/regenerate_old_articles.py --after-id <uuid>
    python scripts/regenerate_old_articles.py
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from db.client import get_beurer_supabase
from blog.article_service import regenerate_article

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CUTOFF_DATE = "2026-03-10T00:00:00Z"

TONE_FEEDBACK = (
    "Regenerate this article from scratch applying all current brand voice and compliance rules:\n"
    "- Use formal Sie-Form throughout\n"
    "- NO healing promises: never claim products \"stop pain\", \"eliminate symptoms\", or match clinical equipment\n"
    "- Use softened language: \"kann unterstützen\", \"kann zur Linderung beitragen\", \"kann helfen\"\n"
    "- Always add medical context: \"in Absprache mit Ihrem Arzt\", \"als ergänzende Maßnahme\"\n"
    "- For TENS/EMS: \"kann zur Schmerzlinderung beitragen\", never \"stoppt Schmerzen\"\n"
    "- For blood pressure: \"unterstützt zuverlässiges Monitoring zuhause\", never \"so genau wie beim Arzt\"\n"
    "- Cite medical sources and studies where possible\n"
    "- Follow all banned word rules from voice persona\n"
    "- Banned words: \"Schmerzen stoppen\", \"Schmerzen beseitigen\", \"klinische Präzision\", \"genauso genau wie beim Arzt\"\n"
    "- Professional, empathetic, trustworthy tone throughout"
)

# Graceful shutdown
_shutdown = False


def _handle_sigint(sig, frame):
    global _shutdown
    if _shutdown:
        logger.warning("Force quit.")
        sys.exit(1)
    _shutdown = True
    logger.info("Ctrl+C received — finishing current article then stopping.")


signal.signal(signal.SIGINT, _handle_sigint)


def fetch_articles(after_id: str | None = None) -> list[dict]:
    """Fetch completed/failed articles created before the cutoff date."""
    supabase = get_beurer_supabase()

    query = (
        supabase.table("blog_articles")
        .select("id, keyword, status, created_at, language")
        .in_("status", ["completed", "failed"])
        .lt("created_at", CUTOFF_DATE)
        .order("created_at", desc=False)
    )

    results = query.execute()
    articles = results.data or []

    # Filter to after_id if specified
    if after_id:
        found = False
        filtered = []
        for a in articles:
            if found:
                filtered.append(a)
            if a["id"] == after_id:
                found = True
        if not found:
            logger.warning(f"--after-id {after_id} not found in results, processing all.")
        else:
            articles = filtered

    return articles


async def run(args: argparse.Namespace):
    articles = fetch_articles(after_id=args.after_id)

    if args.limit:
        articles = articles[: args.limit]

    total = len(articles)

    if total == 0:
        logger.info("No articles found matching criteria.")
        return

    if args.dry_run:
        logger.info(f"DRY RUN — {total} article(s) would be regenerated:\n")
        for i, a in enumerate(articles, 1):
            print(f"  {i}. [{a['status']}] {a['keyword']!r}  (id={a['id']}, created={a['created_at']})")
        return

    logger.info(f"Starting regeneration of {total} article(s).")
    succeeded = 0
    failed = 0

    for i, article in enumerate(articles, 1):
        if _shutdown:
            logger.info(f"Stopped after {i - 1}/{total}. Succeeded: {succeeded}, Failed: {failed}")
            return

        aid = article["id"]
        keyword = article["keyword"]
        logger.info(f"[{i}/{total}] Regenerating '{keyword}' (id={aid}, created={article['created_at']})")

        try:
            result = await regenerate_article(
                article_id=aid,
                feedback=TONE_FEEDBACK,
                from_scratch=True,
            )
            status = result.get("status", "unknown")
            if status == "completed":
                succeeded += 1
                logger.info(f"  -> completed")
            else:
                failed += 1
                err = result.get("error_message", "")
                logger.warning(f"  -> {status}: {err}")
        except Exception as e:
            failed += 1
            logger.error(f"  -> exception: {e}")

        # Rate limit buffer between articles
        if i < total and not _shutdown:
            time.sleep(2)

    logger.info(f"Done. {succeeded}/{total} succeeded, {failed}/{total} failed.")


def main():
    parser = argparse.ArgumentParser(description="Regenerate pre-March-10 blog articles with updated compliance rules.")
    parser.add_argument("--dry-run", action="store_true", help="List articles without regenerating")
    parser.add_argument("--limit", type=int, default=None, help="Max number of articles to process")
    parser.add_argument("--after-id", type=str, default=None, help="Resume after this article ID")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

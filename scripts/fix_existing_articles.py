"""One-time migration: fix existing articles for briefing bugs.

Fixes:
1. Spaced URLs in article_json content fields
2. Trim sources to max 3, sync footnotes
3. Remove EM 50 links from non-menstrual articles

Usage: python scripts/fix_existing_articles.py [--dry-run]
"""
import json
import os
import re
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ.get("BEURER_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("BEURER_SUPABASE_KEY")

DRY_RUN = "--dry-run" in sys.argv

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

CONTENT_FIELDS = ["Intro", "Direct_Answer", "TLDR"]
for i in range(1, 10):
    CONTENT_FIELDS.append(f"section_{i:02d}_content")
for i in range(1, 7):
    CONTENT_FIELDS.append(f"faq_{i:02d}_answer")
for i in range(1, 5):
    CONTENT_FIELDS.append(f"paa_{i:02d}_answer")


def fix_spaced_urls(article: dict) -> int:
    """Fix URLs with spaces in href attributes. Returns count of fixes."""
    fixes = 0
    for field in CONTENT_FIELDS:
        val = article.get(field)
        if not isinstance(val, str) or "href" not in val:
            continue
        fixed = re.sub(
            r'href="([^"]+)"',
            lambda m: (
                f'href="{m.group(1).replace(" ", "")}"'
                if " " in m.group(1)
                else m.group(0)
            ),
            val,
        )
        if fixed != val:
            article[field] = fixed
            fixes += 1
    return fixes


def trim_sources(article: dict, max_sources: int = 3) -> int:
    """Trim sources to max_sources. Returns number removed."""
    sources = article.get("Sources", [])
    if not isinstance(sources, list) or len(sources) <= max_sources:
        return 0
    removed_count = len(sources) - max_sources
    article["Sources"] = sources[:max_sources]

    # Re-sync footnotes: remove markers beyond max_sources
    valid_letters = {chr(65 + i) for i in range(max_sources)}
    for field in CONTENT_FIELDS:
        val = article.get(field)
        if not isinstance(val, str) or "<sup>" not in val:
            continue
        original = val
        # Remove orphaned sup tags
        for m in re.finditer(r"<sup>([A-Z])</sup>", val):
            letter = m.group(1)
            if letter not in valid_letters:
                val = val.replace(f"<sup>{letter}</sup>", "")
        if val != original:
            article[field] = val
    return removed_count


def fix_em50_links(article: dict, keyword: str) -> int:
    """Remove EM 50 menstrual links from non-menstrual articles. Returns count."""
    kw_lower = keyword.lower()
    menstrual_keywords = ["menstrual", "menstruation", "regel", "periode", "periodenschmerz"]
    if any(mk in kw_lower for mk in menstrual_keywords):
        return 0  # Article IS about menstruation, keep EM 50 links

    fixes = 0
    em50_pattern = re.compile(
        r'<a\s+[^>]*href="[^"]*em-50[^"]*"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    for field in CONTENT_FIELDS:
        val = article.get(field)
        if not isinstance(val, str):
            continue
        fixed = em50_pattern.sub(r"\1", val)  # Keep link text, remove <a> tag
        if fixed != val:
            article[field] = fixed
            fixes += 1
    return fixes


def main():
    print(f"{'DRY RUN — ' if DRY_RUN else ''}Fetching completed articles...")
    result = (
        supabase.table("blog_articles")
        .select("id,keyword,article_json")
        .eq("status", "completed")
        .execute()
    )
    articles = result.data
    print(f"Found {len(articles)} completed articles\n")

    total_url_fixes = 0
    total_source_trims = 0
    total_em50_fixes = 0

    for a in articles:
        aid = a["id"][:8]
        keyword = a["keyword"]
        art = a["article_json"]
        changes = []

        url_fixes = fix_spaced_urls(art)
        if url_fixes:
            changes.append(f"{url_fixes} URL fixes")
            total_url_fixes += url_fixes

        source_trims = trim_sources(art)
        if source_trims:
            changes.append(f"{source_trims} sources trimmed")
            total_source_trims += source_trims

        em50_fixes = fix_em50_links(art, keyword)
        if em50_fixes:
            changes.append(f"{em50_fixes} EM 50 links removed")
            total_em50_fixes += em50_fixes

        if changes:
            print(f"  [{aid}] {keyword[:50]}: {', '.join(changes)}")
            if not DRY_RUN:
                supabase.table("blog_articles").update(
                    {"article_json": art}
                ).eq("id", a["id"]).execute()
        else:
            print(f"  [{aid}] {keyword[:50]}: no changes needed")

    print(f"\n{'DRY RUN ' if DRY_RUN else ''}Summary:")
    print(f"  URL fixes: {total_url_fixes}")
    print(f"  Sources trimmed: {total_source_trims}")
    print(f"  EM 50 links removed: {total_em50_fixes}")


if __name__ == "__main__":
    main()

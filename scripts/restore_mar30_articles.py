#!/usr/bin/env python3
"""
Restore 11 original blog articles to their Mar 30 "99%" state.
Delete duplicate/typo articles created Mar 31 - Apr 2.

Usage:
    python scripts/restore_mar30_articles.py           # Dry run (default)
    python scripts/restore_mar30_articles.py --apply   # Execute changes
"""

import argparse
import json
import logging
import re as _re
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from db.client import get_beurer_supabase

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def parse_dt(s):
    """Parse a datetime string, ensuring it's always timezone-aware (UTC)."""
    if not s:
        return None
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# The 11 original articles were created between Mar 4-17, 2026.
ORIGINAL_CUTOFF = datetime(2026, 3, 28, tzinfo=timezone.utc)
# The Apr 7 batch regen started at 09:09 UTC.
APR7_REGEN_START = datetime(2026, 4, 7, 9, 9, 0, tzinfo=timezone.utc)

# Keywords to KEEP from the extras (unique topics worth regenerating fresh)
KEEP_KEYWORDS = {
    "Blutdruck richtig messen Oberarm",
    "Blutdruck senken ohne Medikamente",
    "Blutdruck messen Oberarm Handgelenk",
    "Blutdruck richtig messen zu Hause",
    "Infrarotlampe Anwendung Erkaeltung",
    "Infrarotlampe Wirkung Gesundheit",
    "Regelschmerzen lindern TENS",
}


def fetch_all_articles(supabase):
    """Fetch all blog articles with feedback_history."""
    resp = supabase.table("blog_articles").select(
        "id, keyword, headline, status, created_at, feedback_history, article_html, article_json, source_item_id, word_count"
    ).execute()
    return resp.data or []


def categorize_articles(articles):
    """Split articles into originals, delete, and keep lists.

    For keep-keywords that appear more than once, keep the oldest and delete the rest.
    """
    originals = []
    to_delete = []
    to_keep = []
    seen_keep_keywords = {}  # keyword -> article (oldest)

    for a in sorted(articles, key=lambda x: x["created_at"]):
        created = parse_dt(a["created_at"])
        if created < ORIGINAL_CUTOFF:
            originals.append(a)
        elif a["keyword"] in KEEP_KEYWORDS:
            if a["keyword"] not in seen_keep_keywords:
                seen_keep_keywords[a["keyword"]] = a
                to_keep.append(a)
            else:
                to_delete.append(a)  # duplicate of a keep keyword
        else:
            to_delete.append(a)

    return originals, to_delete, to_keep


def find_mar30_snapshot(article):
    """Find the snapshot entry containing the Mar 30 article content.

    The Apr 7 batch regen created snapshots before overwriting.
    We want the first snapshot taken on Apr 7 (contains pre-Apr-7 content = Mar 30 version).
    """
    history = article.get("feedback_history") or []
    snapshots = [e for e in history if e.get("type") == "snapshot"]

    # Find snapshots created on Apr 7 (these contain the pre-Apr-7 content = Mar 30 version)
    candidates = []
    for s in snapshots:
        created = s.get("created_at", "")
        if not created:
            continue
        dt = parse_dt(created)
        if datetime(2026, 4, 7, tzinfo=timezone.utc) <= dt <= datetime(2026, 4, 8, tzinfo=timezone.utc):
            candidates.append((dt, s))

    if not candidates:
        # Fallback: latest snapshot before Apr 7
        for s in snapshots:
            created = s.get("created_at", "")
            if not created:
                continue
            dt = parse_dt(created)
            if dt < APR7_REGEN_START:
                candidates.append((dt, s))

    if not candidates:
        return None

    # Sort by timestamp, take the first (earliest Apr 7 snapshot)
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def restore_article(supabase, article, snapshot, dry_run=True):
    """Restore an article to its Mar 30 snapshot content."""
    article_id = article["id"]
    keyword = article["keyword"]

    old_html = snapshot.get("article_html")
    old_json = snapshot.get("article_json")

    if not old_html:
        logger.warning(f"  [{article_id[:8]}] {keyword}: snapshot has no article_html, skipping")
        return False

    if dry_run:
        logger.info(f"  [{article_id[:8]}] {keyword}: WOULD restore (snapshot from {snapshot.get('created_at', 'unknown')})")
        return True

    # Snapshot current state before overwriting
    current_snapshot = {
        "type": "snapshot",
        "version": len([e for e in (article.get("feedback_history") or []) if e.get("type") == "snapshot"]) + 1,
        "headline": article.get("headline", ""),
        "article_html": article.get("article_html", ""),
        "article_json": article.get("article_json"),
        "word_count": article.get("word_count"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": "pre_restore_to_mar30",
    }

    updated_history = list(article.get("feedback_history") or [])
    updated_history.append(current_snapshot)

    # Calculate word count from restored HTML
    text = _re.sub(r'<[^>]+>', '', old_html or '')
    word_count = len(text.split())

    update_data = {
        "article_html": old_html,
        "article_json": old_json if old_json else article.get("article_json"),
        "html_custom": False,
        "word_count": word_count,
        "feedback_history": updated_history,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    supabase.table("blog_articles").update(update_data).eq("id", article_id).execute()
    logger.info(f"  [{article_id[:8]}] {keyword}: RESTORED from snapshot {snapshot.get('created_at', 'unknown')}")
    return True


def delete_article(supabase, article, dry_run=True):
    """Delete a duplicate/typo article."""
    article_id = article["id"]
    keyword = article["keyword"]

    if dry_run:
        logger.info(f"  [{article_id[:8]}] {keyword}: WOULD delete")
        return True

    # Delete comments first (FK constraint)
    supabase.table("article_comments").delete().eq("article_id", article_id).execute()
    supabase.table("blog_articles").delete().eq("id", article_id).execute()
    logger.info(f"  [{article_id[:8]}] {keyword}: DELETED")
    return True


def run_safety_passes(supabase, article_id, keyword, article_json, dry_run=True):
    """Run non-destructive safety passes on restored content.

    Fixes residual issues without regenerating prose:
    - HealthManager Pro claims in non-BP articles
    - EM 89 wrong specs
    - Cross-category product leaks
    - HTML cleanup (Sie detection, footnote sync)
    - Product catalog validation
    """
    if dry_run:
        logger.info(f"  [{article_id[:8]}] {keyword}: WOULD run safety passes")
        return article_json

    from blog.article_service import _post_pipeline_safety
    from blog.product_catalog import load_catalog, apply_product_validation, apply_claim_validation
    from blog.stage_cleanup import run_cleanup
    from blog.shared.html_renderer import HTMLRenderer

    article_dict = dict(article_json) if article_json else {}

    # 1. Post-pipeline safety (HealthManager Pro, EM 89 specs, cross-category)
    article_dict = _post_pipeline_safety(article_dict, keyword)

    # 2. Product catalog validation
    catalog = load_catalog()
    if catalog:
        validation_report = apply_product_validation(article_dict, catalog)
        claim_report = apply_claim_validation(article_dict, catalog)
        logger.info(
            f"  [{article_id[:8]}] Product validation: "
            f"{validation_report.get('replacements_made', 0)} replacements, "
            f"{claim_report.get('claims_removed', 0)} claims removed"
        )
        reports = article_dict.get("_pipeline_reports", {})
        reports["product_validation"] = validation_report
        reports["claim_validation"] = claim_report
        article_dict["_pipeline_reports"] = reports

    # 3. HTML cleanup (Sie detection, footnote sync, whitespace)
    cleanup_result = run_cleanup(article_dict)
    reports = article_dict.get("_pipeline_reports", {})
    reports["cleanup"] = {
        "fields_cleaned": cleanup_result.fields_cleaned,
        "valid": cleanup_result.valid,
        "warnings": cleanup_result.warnings,
        "sie_detected": getattr(cleanup_result, 'sie_detected', False),
    }
    article_dict["_pipeline_reports"] = reports

    # 4. Re-render HTML from the cleaned article_json
    renderer = HTMLRenderer()
    new_html = renderer.render(
        article=article_dict,
        company_name="Beurer",
        company_url="https://www.beurer.com",
        language="de",
    )

    # Update in DB
    text = _re.sub(r'<[^>]+>', '', new_html)
    word_count = len(text.split())

    supabase.table("blog_articles").update({
        "article_json": article_dict,
        "article_html": new_html,
        "word_count": word_count,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", article_id).execute()

    logger.info(f"  [{article_id[:8]}] {keyword}: safety passes applied, HTML re-rendered")
    return article_dict


def main():
    parser = argparse.ArgumentParser(description="Restore Mar 30 articles")
    parser.add_argument("--apply", action="store_true", help="Execute changes (default: dry run)")
    parser.add_argument("--test-one", type=str, help="Restore only this article ID (prefix match)")
    args = parser.parse_args()

    supabase = get_beurer_supabase()
    articles = fetch_all_articles(supabase)
    logger.info(f"Fetched {len(articles)} total articles")

    originals, to_delete, to_keep = categorize_articles(articles)
    logger.info(f"Originals to restore: {len(originals)}")
    logger.info(f"Extras to delete: {len(to_delete)}")
    logger.info(f"Extras to keep: {len(to_keep)}")

    print("\n=== ORIGINALS (will restore to Mar 30 snapshot) ===")
    for a in originals:
        snap = find_mar30_snapshot(a)
        snap_date = snap.get("created_at", "none") if snap else "NO SNAPSHOT FOUND"
        print(f"  [{a['id'][:8]}] {a['keyword']} — snapshot: {snap_date}")

    print("\n=== DELETE (duplicates/typos/overlap) ===")
    for a in to_delete:
        print(f"  [{a['id'][:8]}] {a['keyword']} (source_item_id={'SET' if a.get('source_item_id') else 'null'})")

    print("\n=== KEEP (unique topics, regenerate later) ===")
    for a in to_keep:
        print(f"  [{a['id'][:8]}] {a['keyword']}")

    if not args.apply and not args.test_one:
        print("\n--- DRY RUN --- Pass --apply to execute changes.")
        return

    # --- Single article test mode ---
    if args.test_one:
        target = [a for a in originals if a["id"].startswith(args.test_one)]
        if not target:
            print(f"ERROR: No original article found matching ID prefix '{args.test_one}'")
            return
        a = target[0]
        snapshot = find_mar30_snapshot(a)
        if not snapshot:
            print(f"ERROR: No Mar 30 snapshot found for [{a['id'][:8]}] {a['keyword']}")
            return
        print(f"\n=== TEST: Restoring single article [{a['id'][:8]}] {a['keyword']} ===")
        if restore_article(supabase, a, snapshot, dry_run=False):
            print("  Restore OK. Running safety passes...")
            refetched = supabase.table("blog_articles").select(
                "id, keyword, article_json"
            ).eq("id", a["id"]).single().execute()
            if refetched.data:
                run_safety_passes(
                    supabase, refetched.data["id"], refetched.data["keyword"],
                    refetched.data["article_json"], dry_run=False
                )
            print("  Done. Check the article in the dashboard.")
        else:
            print("  Restore FAILED.")
        return

    # --- Restore originals ---
    print("\n=== RESTORING ORIGINALS ===")
    restored = 0
    failed = 0
    restored_ids = []
    for a in originals:
        snapshot = find_mar30_snapshot(a)
        if snapshot:
            if restore_article(supabase, a, snapshot, dry_run=False):
                restored += 1
                restored_ids.append(a["id"])
            else:
                failed += 1
        else:
            logger.warning(f"  [{a['id'][:8]}] {a['keyword']}: NO Mar 30 snapshot found, skipping")
            failed += 1

    # --- Run safety passes on restored articles only ---
    if restored_ids:
        print("\n=== RUNNING SAFETY PASSES ===")
        for aid in restored_ids:
            refetched = supabase.table("blog_articles").select(
                "id, keyword, article_json"
            ).eq("id", aid).single().execute()
            if refetched.data:
                run_safety_passes(
                    supabase, refetched.data["id"], refetched.data["keyword"],
                    refetched.data["article_json"], dry_run=False
                )

    # --- Delete extras ---
    print("\n=== DELETING DUPLICATES/TYPOS ===")
    deleted = 0
    for a in to_delete:
        if delete_article(supabase, a, dry_run=False):
            deleted += 1

    # --- Summary ---
    print(f"\n=== SUMMARY ===")
    print(f"  Restored: {restored}")
    print(f"  Failed to restore: {failed}")
    print(f"  Deleted: {deleted}")
    print(f"  Kept (for fresh regen): {len(to_keep)}")


if __name__ == "__main__":
    main()

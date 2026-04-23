# Article Restore & Version Quality Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore 11 original articles to their Mar 30 "99%" state, clean up duplicate/typo extras, and add golden version markers + quality indicators to the content tab.

**Architecture:** Two workstreams. WS1 is a standalone Python script querying Supabase directly — no API changes. WS2 adds a `golden_version` JSONB column, 3 new PATCH actions in the blog-article API, and client-side UI in the dashboard template (version bar golden styling, quality badges in list and modal).

**Tech Stack:** Python 3.11 (Supabase client, existing `blog/` modules), Next.js API routes (TypeScript), vanilla JS in dashboard HTML template, Supabase PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-04-13-article-restore-and-version-quality-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `scripts/restore_mar30_articles.py` | **NEW** — One-time restore script. Queries Supabase, finds Mar 30 snapshots, restores originals, deletes duplicates. Dry-run by default. |
| `migrations/012_golden_version.sql` | **NEW** — Adds `golden_version JSONB DEFAULT NULL` to `blog_articles`. |
| `dashboard/app/api/blog-article/route.ts` | **MODIFY** — Add 3 PATCH actions: `set_golden_version`, `restore_golden_version`, `clear_golden_version`. |
| `styles/dashboard_template.html` | **MODIFY** — Golden version UI in version bar + modal sidebar. Quality indicators in article list table + modal sidebar. |

---

## Task 1: Restore Script — Query & Categorize Articles

**Files:**
- Create: `scripts/restore_mar30_articles.py`

This task builds the script skeleton: connect to Supabase, fetch all blog articles, categorize them into originals (restore), duplicates (delete), and keepers (regenerate later).

- [ ] **Step 1: Create script with argument parsing and Supabase connection**

```python
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

# The 11 original articles were created between Mar 4-17, 2026.
# The 14 extras were created Mar 31 - Apr 2, 2026.
ORIGINAL_CUTOFF = datetime(2026, 3, 28, tzinfo=timezone.utc)
# The Apr 7 batch regen started at 09:09 UTC — snapshots taken just before contain Mar 30 content.
APR7_REGEN_START = datetime(2026, 4, 7, 9, 9, 0, tzinfo=timezone.utc)

# Keywords to KEEP from the extras (unique topics worth regenerating fresh)
KEEP_KEYWORDS = {
    "Blutdruck richtig messen Oberarm",
    "Blutdruck senken ohne Medikamente",
    "Blutdruck messen Oberarm Handgelenk",
    "Infrarotlampe Anwendung Erkaeltung",
    "Infrarotlampe Wirkung Gesundheit",
}


def fetch_all_articles(supabase):
    """Fetch all blog articles with feedback_history."""
    resp = supabase.table("blog_articles").select(
        "id, keyword, headline, status, created_at, feedback_history, article_html, article_json, source_item_id"
    ).execute()
    return resp.data or []


def categorize_articles(articles):
    """Split articles into originals, delete, and keep lists."""
    originals = []
    to_delete = []
    to_keep = []

    for a in articles:
        created = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00"))
        if created < ORIGINAL_CUTOFF:
            originals.append(a)
        elif a["keyword"] in KEEP_KEYWORDS:
            to_keep.append(a)
        else:
            to_delete.append(a)

    return originals, to_delete, to_keep


def main():
    parser = argparse.ArgumentParser(description="Restore Mar 30 articles")
    parser.add_argument("--apply", action="store_true", help="Execute changes (default: dry run)")
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
        print(f"  [{a['id'][:8]}] {a['keyword']}")

    print("\n=== DELETE (duplicates/typos/overlap) ===")
    for a in to_delete:
        print(f"  [{a['id'][:8]}] {a['keyword']} (source_item_id={'SET' if a.get('source_item_id') else 'null'})")

    print("\n=== KEEP (unique topics, regenerate later) ===")
    for a in to_keep:
        print(f"  [{a['id'][:8]}] {a['keyword']}")

    if not args.apply:
        print("\n--- DRY RUN --- Pass --apply to execute changes.")
        return

    # Execution continues in Task 2...


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run script in dry-run mode to verify categorization**

Run: `python scripts/restore_mar30_articles.py`

Expected: Lists all articles in 3 categories. Originals should be ~11, delete ~9, keep ~5. Review the output manually — if any article is miscategorized, adjust `KEEP_KEYWORDS` or `ORIGINAL_CUTOFF`.

- [ ] **Step 3: Commit**

```bash
git add scripts/restore_mar30_articles.py
git commit -m "feat: add article restore script with dry-run categorization"
```

---

## Task 2: Restore Script — Snapshot Recovery & Restore Logic

**Files:**
- Modify: `scripts/restore_mar30_articles.py`

Add the core restore logic: find the Mar 30 snapshot in `feedback_history`, snapshot the current state, then write the Mar 30 content back.

- [ ] **Step 1: Add snapshot finder function**

Add after `categorize_articles`:

```python
def find_mar30_snapshot(article):
    """Find the snapshot entry containing the Mar 30 article content.

    The Apr 7 batch regen created snapshots before overwriting.
    We want the last snapshot taken before Apr 7 09:09 UTC.
    """
    history = article.get("feedback_history") or []
    snapshots = [e for e in history if e.get("type") == "snapshot"]

    # Find snapshots created around Apr 7 (these contain the pre-Apr-7 content = Mar 30 version)
    candidates = []
    for s in snapshots:
        created = s.get("created_at", "")
        if not created:
            continue
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        # The batch regen snapshots the current content just before overwriting.
        # Look for snapshots created on Apr 7 (the first pass started at 09:09).
        if datetime(2026, 4, 7, tzinfo=timezone.utc) <= dt <= datetime(2026, 4, 8, tzinfo=timezone.utc):
            candidates.append((dt, s))

    if not candidates:
        # Fallback: if no Apr 7 snapshot, try the latest snapshot before Apr 7
        for s in snapshots:
            created = s.get("created_at", "")
            if not created:
                continue
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt < APR7_REGEN_START:
                candidates.append((dt, s))

    if not candidates:
        return None

    # Sort by timestamp, take the first Apr 7 snapshot (contains Mar 30 content)
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]
```

- [ ] **Step 2: Add restore function**

Add after `find_mar30_snapshot`:

```python
def restore_article(supabase, article, snapshot, dry_run=True):
    """Restore an article to its Mar 30 snapshot content."""
    article_id = article["id"]
    keyword = article["keyword"]

    old_html = snapshot.get("article_html")
    old_json = snapshot.get("article_json")

    if not old_html:
        logger.warning(f"  [{article_id[:8]}] {keyword}: snapshot has no article_html, skipping")
        return False

    # Build a snapshot of the CURRENT state before overwriting
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

    # Append the current-state snapshot to feedback_history
    updated_history = list(article.get("feedback_history") or [])
    updated_history.append(current_snapshot)

    # Calculate word count from restored HTML
    import re as _re
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

    if dry_run:
        logger.info(f"  [{article_id[:8]}] {keyword}: WOULD restore (snapshot from {snapshot.get('created_at', 'unknown')})")
        return True

    supabase.table("blog_articles").update(update_data).eq("id", article_id).execute()
    logger.info(f"  [{article_id[:8]}] {keyword}: RESTORED from snapshot {snapshot.get('created_at', 'unknown')}")
    return True
```

- [ ] **Step 3: Add delete function**

Add after `restore_article`:

```python
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
```

- [ ] **Step 4: Wire into main()**

Replace the `# Execution continues in Task 2...` comment in `main()` with:

```python
    # --- Restore originals ---
    print("\n=== RESTORING ORIGINALS ===")
    restored = 0
    failed = 0
    for a in originals:
        snapshot = find_mar30_snapshot(a)
        if snapshot:
            if restore_article(supabase, a, snapshot, dry_run=not args.apply):
                restored += 1
            else:
                failed += 1
        else:
            logger.warning(f"  [{a['id'][:8]}] {a['keyword']}: NO Mar 30 snapshot found, skipping")
            failed += 1

    # --- Delete extras ---
    print("\n=== DELETING DUPLICATES/TYPOS ===")
    deleted = 0
    for a in to_delete:
        if delete_article(supabase, a, dry_run=not args.apply):
            deleted += 1

    # --- Summary ---
    print(f"\n=== SUMMARY ===")
    print(f"  Restored: {restored}")
    print(f"  Failed to restore: {failed}")
    print(f"  Deleted: {deleted}")
    print(f"  Kept (for fresh regen): {len(to_keep)}")
```

- [ ] **Step 5: Run dry-run again to verify restore logic**

Run: `python scripts/restore_mar30_articles.py`

Expected: Each original shows "WOULD restore (snapshot from 2026-04-07T09:XX)" — confirming Mar 30 snapshots exist. Each duplicate shows "WOULD delete". If any original shows "NO Mar 30 snapshot found", investigate that article's `feedback_history` manually.

- [ ] **Step 6: Commit**

```bash
git add scripts/restore_mar30_articles.py
git commit -m "feat: add restore and delete logic to article restore script"
```

---

## Task 3: Restore Script — Post-Restore Safety Passes

**Files:**
- Modify: `scripts/restore_mar30_articles.py`

After restoring Mar 30 content, run non-destructive safety passes to fix the 3 known residual bugs (Sie remnants, dead URLs, Produktberater links) without regenerating prose.

- [ ] **Step 1: Add safety pass function**

Add after `delete_article`:

```python
def run_safety_passes(supabase, article_id, keyword, article_json, dry_run=True):
    """Run non-destructive safety passes on restored content.

    Fixes:
    - HealthManager Pro claims in non-BP articles
    - EM 89 wrong specs
    - Cross-category product leaks
    - HTML cleanup (Sie detection, footnote sync)
    - Product catalog validation

    Does NOT regenerate prose or call Gemini for content.
    """
    if dry_run:
        logger.info(f"  [{article_id[:8]}] {keyword}: WOULD run safety passes")
        return article_json

    from blog.article_service import _post_pipeline_safety
    from blog.product_catalog import load_catalog, apply_product_validation, apply_claim_validation
    from blog.stage_cleanup import run_cleanup

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
        # Store reports for quality indicators
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
        "sie_detected": cleanup_result.sie_detected if hasattr(cleanup_result, 'sie_detected') else False,
    }
    article_dict["_pipeline_reports"] = reports

    # 4. Re-render HTML from the cleaned article_json
    from blog.shared.html_renderer import HTMLRenderer

    renderer = HTMLRenderer()
    new_html = renderer.render(
        article=article_dict,
        company_name="Beurer",
        company_url="https://www.beurer.com",
        language="de",
    )

    # Update in DB
    import re as _re
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
```

- [ ] **Step 2: Wire safety passes into main(), after restore loop**

Add after the `=== RESTORING ORIGINALS ===` loop, before the delete section:

```python
    # --- Run safety passes on restored articles ---
    if args.apply and restored > 0:
        print("\n=== RUNNING SAFETY PASSES ===")
        # Re-fetch restored articles to get updated article_json
        for a in originals:
            refetched = supabase.table("blog_articles").select(
                "id, keyword, article_json"
            ).eq("id", a["id"]).single().execute()
            if refetched.data:
                run_safety_passes(
                    supabase, refetched.data["id"], refetched.data["keyword"],
                    refetched.data["article_json"], dry_run=not args.apply
                )
```

- [ ] **Step 3: Run dry-run to verify**

Run: `python scripts/restore_mar30_articles.py`

Expected: Each original shows "WOULD run safety passes" after "WOULD restore".

- [ ] **Step 4: Commit**

```bash
git add scripts/restore_mar30_articles.py
git commit -m "feat: add post-restore safety passes to article restore script"
```

---

## Task 4: Golden Version — Database Migration

**Files:**
- Create: `migrations/012_golden_version.sql`

- [ ] **Step 1: Create migration file**

```sql
-- Migration: 012_golden_version.sql
-- Add golden_version column to blog_articles for marking approved baseline versions.
-- golden_version stores a self-contained snapshot: {version, marked_at, marked_by, article_html, article_json, word_count}

ALTER TABLE blog_articles ADD COLUMN IF NOT EXISTS golden_version JSONB DEFAULT NULL;

COMMENT ON COLUMN blog_articles.golden_version IS 'Self-contained snapshot of the reviewer-approved baseline version';
```

- [ ] **Step 2: Apply migration to Supabase**

Run the SQL in the Supabase SQL editor (dashboard > SQL Editor > paste > Run), or via CLI:
```bash
# If using supabase CLI:
# supabase db push
# Otherwise, apply manually in the Supabase dashboard SQL editor.
```

Expected: Column `golden_version` appears on `blog_articles` table, all rows have `null`.

- [ ] **Step 3: Commit**

```bash
git add migrations/012_golden_version.sql
git commit -m "feat: add golden_version column to blog_articles"
```

---

## Task 5: Golden Version — API Actions

**Files:**
- Modify: `dashboard/app/api/blog-article/route.ts` (insert after line ~505, after `remove_image` action block)

- [ ] **Step 1: Add `set_golden_version` action**

Insert after the closing `}` of the `remove_image` block (around line 505), before the inline-edits fallthrough:

```typescript
    // Set golden version — mark a specific version (or current) as the approved baseline
    if (action === "set_golden_version") {
      const { version_index, marked_by } = body;
      // version_index: index into feedback_history snapshots, or -1 for current article
      if (version_index === undefined) {
        return NextResponse.json({ error: "version_index is required" }, { status: 400 });
      }

      const { data: article, error: fetchErr } = await supabase
        .from("blog_articles")
        .select("article_html, article_json, word_count, headline, feedback_history")
        .eq("id", article_id)
        .single();
      if (fetchErr || !article) {
        return NextResponse.json({ error: "Article not found" }, { status: 404 });
      }

      let goldenHtml: string;
      let goldenJson: Record<string, unknown> | null;
      let goldenWordCount: number;
      let goldenVersion: number;

      if (version_index === -1) {
        // Current article
        goldenHtml = article.article_html;
        goldenJson = article.article_json;
        goldenWordCount = article.word_count || 0;
        const snapshots = (article.feedback_history || []).filter(
          (e: { type: string }) => e.type === "snapshot"
        );
        goldenVersion = snapshots.length + 1;
      } else {
        // Historical snapshot
        const snapshots = (article.feedback_history || []).filter(
          (e: { type: string }) => e.type === "snapshot"
        );
        const snap = snapshots[version_index];
        if (!snap || !snap.article_html) {
          return NextResponse.json({ error: "Snapshot not found or has no HTML" }, { status: 400 });
        }
        goldenHtml = snap.article_html;
        goldenJson = snap.article_json || null;
        goldenWordCount = snap.word_count || 0;
        goldenVersion = snap.version || version_index + 1;
      }

      const goldenData = {
        version: goldenVersion,
        marked_at: new Date().toISOString(),
        marked_by: marked_by || "Reviewer",
        article_html: goldenHtml,
        article_json: goldenJson,
        word_count: goldenWordCount,
      };

      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          golden_version: goldenData,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }
```

- [ ] **Step 2: Add `restore_golden_version` action**

Insert immediately after `set_golden_version`:

```typescript
    // Restore golden version — revert article to the approved baseline
    if (action === "restore_golden_version") {
      const { data: article, error: fetchErr } = await supabase
        .from("blog_articles")
        .select("golden_version, article_html, article_json, headline, word_count, feedback_history")
        .eq("id", article_id)
        .single();
      if (fetchErr || !article) {
        return NextResponse.json({ error: "Article not found" }, { status: 404 });
      }
      if (!article.golden_version) {
        return NextResponse.json({ error: "No golden version set" }, { status: 400 });
      }

      // Snapshot current state before restoring
      const history = article.feedback_history || [];
      const snapshots = history.filter((e: { type: string }) => e.type === "snapshot");
      const currentSnapshot = {
        type: "snapshot",
        version: snapshots.length + 1,
        headline: article.headline || "",
        article_html: article.article_html,
        article_json: article.article_json,
        word_count: article.word_count,
        created_at: new Date().toISOString(),
        reason: "pre_golden_restore",
      };
      const updatedHistory = [...history, currentSnapshot];

      const golden = article.golden_version;
      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          article_html: golden.article_html,
          article_json: golden.article_json || article.article_json,
          word_count: golden.word_count || article.word_count,
          html_custom: false,
          feedback_history: updatedHistory,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }
```

- [ ] **Step 3: Add `clear_golden_version` action**

Insert immediately after `restore_golden_version`:

```typescript
    // Clear golden version marker
    if (action === "clear_golden_version") {
      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          golden_version: null,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/api/blog-article/route.ts
git commit -m "feat: add golden version PATCH actions (set, restore, clear)"
```

---

## Task 6: Golden Version — Version Bar UI

**Files:**
- Modify: `styles/dashboard_template.html` (version bar area, ~lines 7393-7403 and viewArticleVersion ~line 8067)

- [ ] **Step 1: Add golden pill styling**

Find the `<style>` section containing `.version-pill` styles (search for `.version-pill`). Add after the existing `.version-pill` styles:

```css
.version-pill.golden {
    border: 2px solid #D97706;
    background: #FFFBEB;
    color: #92400E;
}
.version-pill.golden::before {
    content: '\2605 ';
    color: #D97706;
}
.golden-actions {
    display: inline-flex;
    gap: 6px;
    margin-left: 8px;
    align-items: center;
}
.golden-actions button {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    border: 1px solid #D1D5DB;
    background: white;
    cursor: pointer;
    color: #374151;
}
.golden-actions button:hover {
    background: #F9FAFB;
}
.golden-actions button.restore-golden {
    border-color: #D97706;
    color: #92400E;
}
.golden-actions button.restore-golden:hover {
    background: #FFFBEB;
}
```

- [ ] **Step 2: Update version bar pill rendering to mark golden version**

Find the version bar construction code (~line 7393). Replace the pill-building block:

```javascript
// Build version bar HTML
const _snapshots = feedbackHistory.filter(function(e) { return e.type === 'snapshot'; });
let _versionBarHtml = '';
if (_snapshots.length > 0) {
    const goldenVersion = article.golden_version ? article.golden_version.version : null;
    const _pills = _snapshots.map(function(s, i) {
        var d = s.created_at ? new Date(s.created_at).toLocaleDateString() : '';
        var vNum = s.version || i + 1;
        var isGolden = goldenVersion !== null && vNum === goldenVersion;
        var goldenClass = isGolden ? ' golden' : '';
        return '<button class="version-pill' + goldenClass + '" data-version-idx="' + i + '" onclick="viewArticleVersion(\'' + articleId + '\', ' + i + ')" title="' + esc(s.headline || '') + '">V' + vNum + ' <span class="pill-meta">' + d + '</span></button>';
    }).join('');
    var currentVNum = _snapshots.length + 1;
    var isCurrentGolden = goldenVersion !== null && currentVNum === goldenVersion;
    var currentGoldenClass = isCurrentGolden ? ' golden' : '';
    var _currentPill = '<button class="version-pill active' + currentGoldenClass + '" data-version-idx="current" onclick="viewArticleVersion(\'' + articleId + '\', -1)">' + (t('version_current') || 'Current') + ' <span class="pill-meta">V' + currentVNum + '</span></button>';

    // Golden action buttons
    var goldenActionsHtml = '<span class="golden-actions">';
    goldenActionsHtml += '<button onclick="setGoldenVersion(\'' + articleId + '\', -1)" title="Mark current version as golden">Set Golden</button>';
    if (article.golden_version && !isCurrentGolden) {
        goldenActionsHtml += '<button class="restore-golden" onclick="restoreGoldenVersion(\'' + articleId + '\')" title="Restore to golden version">Restore Golden</button>';
    }
    goldenActionsHtml += '</span>';

    _versionBarHtml = '<div class="article-version-bar" id="article-version-bar"><span class="version-bar-label">' + (t('version_history') || 'Versions') + ':</span>' + _pills + _currentPill + goldenActionsHtml + '<span class="version-viewing-badge" id="version-viewing-badge">' + (t('version_viewing_old') || 'Viewing older version') + '</span></div>';
}
```

- [ ] **Step 3: Add setGoldenVersion and restoreGoldenVersion functions**

Find the `viewArticleVersion` function (~line 8067). Add these functions after it:

```javascript
async function setGoldenVersion(articleId, versionIdx) {
    if (!confirm('Mark this version as the approved golden baseline?')) return;
    try {
        const resp = await fetch('/api/blog-article', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                article_id: articleId,
                action: 'set_golden_version',
                version_index: versionIdx,
                marked_by: window._currentCommentAuthor || 'Reviewer',
            }),
        });
        if (!resp.ok) throw new Error((await resp.json()).error);
        // Refresh the modal to show updated golden state
        const data = await resp.json();
        openArticleModal(data);
    } catch (e) {
        alert('Failed to set golden version: ' + e.message);
    }
}

async function restoreGoldenVersion(articleId) {
    if (!confirm('Restore this article to the golden (approved) version? The current version will be saved as a snapshot.')) return;
    try {
        const resp = await fetch('/api/blog-article', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                article_id: articleId,
                action: 'restore_golden_version',
            }),
        });
        if (!resp.ok) throw new Error((await resp.json()).error);
        const data = await resp.json();
        openArticleModal(data);
    } catch (e) {
        alert('Failed to restore golden version: ' + e.message);
    }
}

async function clearGoldenVersion(articleId) {
    if (!confirm('Remove the golden version marker?')) return;
    try {
        const resp = await fetch('/api/blog-article', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                article_id: articleId,
                action: 'clear_golden_version',
            }),
        });
        if (!resp.ok) throw new Error((await resp.json()).error);
        const data = await resp.json();
        openArticleModal(data);
    } catch (e) {
        alert('Failed to clear golden version: ' + e.message);
    }
}
```

- [ ] **Step 4: Verify in browser**

Run: `cd dashboard && npm run dev`

Open a completed article in the modal. The version bar should show version pills. The "Set Golden" button should appear. Click it — the selected pill should get a gold border and star. Clicking "Restore Golden" when on a different version should restore and refresh.

- [ ] **Step 5: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add golden version UI to version bar (set, restore, star styling)"
```

---

## Task 7: Golden Version — Sidebar Status

**Files:**
- Modify: `styles/dashboard_template.html` (~line 7490, between review-status-row and image-section)

- [ ] **Step 1: Add golden version status section in sidebar**

Find the `review-status-row` closing `</div>` (~line 7490), insert immediately after it and before the `image-section` div:

```html
<div class="golden-version-status" id="golden-version-status" style="padding:12px 16px;border-bottom:1px solid var(--gray-100);">
    ${(() => {
        const gv = article.golden_version;
        if (!gv) return '<span style="font-size:12px;color:#9CA3AF;">No golden version set</span>';
        const markedDate = gv.marked_at ? new Date(gv.marked_at).toLocaleDateString() : '';
        return '<div style="display:flex;align-items:center;gap:8px;font-size:12px;">'
            + '<span style="color:#D97706;font-size:14px;">&#9733;</span>'
            + '<span style="font-weight:600;color:#92400E;">Golden: V' + gv.version + '</span>'
            + '<span style="color:#9CA3AF;">(by ' + esc(gv.marked_by || 'Reviewer') + ', ' + markedDate + ')</span>'
            + '<button onclick="clearGoldenVersion(\'' + articleId + '\')" style="margin-left:auto;font-size:11px;color:#9CA3AF;background:none;border:none;cursor:pointer;text-decoration:underline;">Clear</button>'
            + '</div>';
    })()}
</div>
```

- [ ] **Step 2: Verify in browser**

Open an article modal. Below the review status, confirm the golden version status shows. Set a golden version — the sidebar should update to show "Golden: V3 (by Reviewer, 4/13/2026)" with a Clear link.

- [ ] **Step 3: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add golden version status to article modal sidebar"
```

---

## Task 8: Quality Indicators — Client-Side Computation

**Files:**
- Modify: `styles/dashboard_template.html`

- [ ] **Step 1: Add quality computation function**

Find a suitable location in the `<script>` section (near the other utility functions). Add:

```javascript
function computeQualityIndicators(articleJson) {
    const reports = (articleJson || {})._pipeline_reports;
    if (!reports) return null;

    const checks = [];

    // Sources check
    const s4 = reports.stage4;
    if (s4 && !s4.error) {
        const total = s4.total_urls || 0;
        const dead = s4.dead_urls || 0;
        const valid = s4.valid_urls || total - dead;
        let status = 'pass';
        if (dead >= 3 || total < 2) status = 'fail';
        else if (dead >= 1) status = 'warn';
        checks.push({ name: 'Sources', status, detail: valid + '/' + total + ' valid' });
    }

    // Products check
    const pv = reports.product_validation;
    if (pv && !pv.error) {
        const unknown = pv.unknown_products || 0;
        const claims = pv.claims_flagged || 0;
        const replacements = pv.replacements_made || 0;
        let status = 'pass';
        if (unknown > 0 || claims > 0) status = 'fail';
        else if (replacements > 0) status = 'warn';
        checks.push({ name: 'Products', status, detail: unknown > 0 ? unknown + ' unknown' : (replacements > 0 ? replacements + ' replaced' : 'All valid') });
    }

    // Category isolation
    const cv = reports.claim_validation;
    if (cv && !cv.error) {
        const removed = cv.claims_removed || 0;
        checks.push({ name: 'Category', status: removed > 0 ? 'fail' : 'pass', detail: removed > 0 ? removed + ' cross-category claims' : 'Clean' });
    }

    // Sie-form check
    const cl = reports.cleanup;
    if (cl && !cl.error) {
        const sie = cl.sie_detected || false;
        checks.push({ name: 'Sie-Form', status: sie ? 'fail' : 'pass', detail: sie ? 'Sie detected' : 'Du-Form OK' });
    }

    // Overall status
    const hasAnyFail = checks.some(c => c.status === 'fail');
    const hasAnyWarn = checks.some(c => c.status === 'warn');
    const overall = hasAnyFail ? 'fail' : (hasAnyWarn ? 'warn' : 'pass');

    return { overall, checks };
}

function renderQualityBadge(quality) {
    if (!quality) return '<span style="font-size:11px;color:#9CA3AF;" title="No quality data">—</span>';
    const icons = { pass: '&#10003;', warn: '&#9888;', fail: '&#10007;' };
    const colors = { pass: '#059669', warn: '#D97706', fail: '#DC2626' };
    const bgs = { pass: '#ECFDF5', warn: '#FFFBEB', fail: '#FEF2F2' };
    const tooltip = quality.checks.map(c => c.name + ': ' + c.detail).join('\n');
    return '<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:' + bgs[quality.overall] + ';color:' + colors[quality.overall] + ';font-size:13px;cursor:help;" title="' + esc(tooltip) + '">' + icons[quality.overall] + '</span>';
}
```

- [ ] **Step 2: Add quality column to article list table**

Find the `buildTopicTable` function's header row (~line 9654). Add a "Quality" column after "Review":

Change:
```javascript
  html += '<th>Review</th>';
  html += '<th>Reviewers</th>';
```

To:
```javascript
  html += '<th>Review</th>';
  html += '<th style="width:50px;text-align:center;">Quality</th>';
  html += '<th>Reviewers</th>';
```

Then find where the row cells are built for each article in `buildTopicTable`. Find the cell that outputs the review badge — it will look something like:

```javascript
html += '<td>' + reviewBadge + '</td>';
```

Add after it:

```javascript
// Quality indicator
var quality = showArticleColumns ? computeQualityIndicators(cachedArticle ? cachedArticle.article_json : null) : null;
html += '<td style="text-align:center;">' + renderQualityBadge(quality) + '</td>';
```

Note: The exact variable names for `cachedArticle` depend on how the existing code accesses the article data for each row. Find the pattern used for the review badge column and follow it — it likely uses `window._cachedArticles` to look up the full article by ID.

- [ ] **Step 3: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add quality indicator badges to article list table"
```

---

## Task 9: Quality Indicators — Modal Sidebar Report Card

**Files:**
- Modify: `styles/dashboard_template.html`

- [ ] **Step 1: Add quality report card in modal sidebar**

Find the golden version status section added in Task 7 (`golden-version-status`). Insert immediately after it:

```html
<div class="quality-report-card" id="quality-report-card" style="padding:12px 16px;border-bottom:1px solid var(--gray-100);">
    ${(() => {
        const quality = computeQualityIndicators(article.article_json);
        if (!quality) return '<div style="font-size:12px;color:#9CA3AF;">No quality data — regenerate to generate report</div>';
        const icons = { pass: '&#10003;', warn: '&#9888;', fail: '&#10007;' };
        const colors = { pass: '#059669', warn: '#D97706', fail: '#DC2626' };
        let html = '<div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:8px;">Quality Report</div>';
        quality.checks.forEach(function(c) {
            html += '<div style="display:flex;align-items:center;gap:8px;font-size:12px;padding:3px 0;">'
                + '<span style="color:' + colors[c.status] + ';width:16px;text-align:center;">' + icons[c.status] + '</span>'
                + '<span style="color:#374151;">' + esc(c.name) + '</span>'
                + '<span style="margin-left:auto;color:#6B7280;">' + esc(c.detail) + '</span>'
                + '</div>';
        });
        return html;
    })()}
</div>
```

- [ ] **Step 2: Verify in browser**

Open an article modal. Below the golden version status, the quality report card should show. Articles with `_pipeline_reports` data should display individual check rows with pass/warn/fail icons. Articles without it should show the muted "No quality data" message.

- [ ] **Step 3: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add quality report card to article modal sidebar"
```

---

## Task 10: Integration Test & Final Commit

- [ ] **Step 1: Run the restore script in dry-run mode one final time**

Run: `python scripts/restore_mar30_articles.py`

Verify: All 11 originals found, snapshots located, ~9 marked for deletion, 5 marked as keepers. No errors.

- [ ] **Step 2: Start dashboard and verify all UI features**

Run: `cd dashboard && npm run dev`

Test checklist:
- Open an article with version history — version pills render, golden actions visible
- Click "Set Golden" — pill gets gold star, sidebar shows golden status
- Navigate to a different version, click "Restore Golden" — article restores, confirmation dialog works
- Click "Clear" in sidebar — golden marker removed
- Article list table shows Quality column with colored badges
- Hover quality badge — tooltip shows individual checks
- Open modal — quality report card visible in sidebar
- Article without `_pipeline_reports` — shows "No quality data" gracefully

- [ ] **Step 3: Final commit with all remaining changes**

```bash
git add -A
git commit -m "feat: complete article restore script + golden version + quality indicators"
```

- [ ] **Step 4: Execute the restore script for real**

This is the destructive step — only run after verifying all the above.

Run: `python scripts/restore_mar30_articles.py --apply`

Verify in dashboard: 11 restored articles show Mar 30 content, duplicates gone, 5 keepers remain.

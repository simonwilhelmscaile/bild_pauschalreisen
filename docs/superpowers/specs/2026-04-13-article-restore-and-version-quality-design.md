# Article Restore & Version Quality Management — Design Spec

**Date:** 2026-04-13
**Context:** Articles peaked at "99%" on Mar 30. Apr 7 batch regeneration through a rearchitected pipeline introduced systematic hallucinations. Post-audit fixes (Apr 9-13) addressed root causes. This spec covers restoring the originals and preventing recurrence.

---

## Scope

Two workstreams, executed sequentially:

1. **Immediate: Restore 11 originals + clean up 14 extras** — script-based, no UI changes
2. **This sprint: Golden Version + Quality Indicators** — UI features in the content tab

Out of scope: version timeline metadata (6.1), side-by-side arbitrary version comparison (6.4), version grouping (6.5) from the analysis doc.

---

## Workstream 1: Article Restore Script

### Goal
Restore the 11 original articles to their Mar 30 "99%" state (the last version Beurer approved). Clean up the 14 extra articles added Mar 31 – Apr 2.

### How restoration works

The Apr 7 batch regeneration (`blog/router.py` lines 655-680) created `type: "snapshot"` entries in `feedback_history` with full `article_html` and `article_json` before overwriting each article. The snapshot taken immediately before the first Apr 7 regeneration pass (09:09 UTC) contains the Mar 30 content.

**Restore logic per article:**
1. Query `feedback_history` JSONB array
2. Find the snapshot entry with `created_at` closest to (but before) `2026-04-07T09:09:00Z` — this is the Mar 30 version
3. Write `snapshot.article_html` back to `article_html` and `snapshot.article_json` back to `article_json`
4. Append a new `type: "snapshot"` entry preserving the current (Apr 9) state before overwriting, with `reason: "restore_to_mar30"`
5. Reset `html_custom` to `false`
6. Recalculate `word_count` from restored HTML

**Post-restore safety passes (non-destructive, text-preserving):**
After restoring, run these passes on the restored content. These fix the 3 known Mar 30 residual bugs (Sie in inline edits, Produktberater links, 404 sources) without regenerating prose:
- `_post_pipeline_safety()` — strips HealthManager Pro claims from non-BP, fixes EM 89 specs, removes cross-category products
- Stage 4 URL verification — checks all external links, strips dead ones
- `stage_cleanup` — HTML hygiene, footnote sync, Sie detection
- `product_catalog.apply_product_validation()` + `apply_claim_validation()`

These passes modify HTML in-place (link removal, text cleanup) but never call Gemini for content generation. The article prose stays exactly as Mar 30.

### Handling the 14 extras

The script identifies articles by database UUID (queried at runtime). Selection criteria:

| Action | Selection criteria | Expected count |
|--------|-------------------|----------------|
| **Delete** | Articles created Mar 31 – Apr 2 that match ANY of: (a) `source_item_id IS NOT NULL` (topic list dupes), (b) duplicate keyword matching another article in the set, (c) keyword is a typo ("Bludtruck"), (d) keyword overlaps heavily with an original (e.g., "TENS Geraet Rueckenschmerzen" vs original "TENS Geraet bei Rueckenschmerzen") | ~9 |
| **Keep, regenerate fresh** | Articles created Mar 31 – Apr 2 with unique, non-overlapping keywords: "Blutdruck richtig messen Oberarm", "Blutdruck senken ohne Medikamente", "Blutdruck messen Oberarm Handgelenk", "Infrarotlampe Anwendung Erkaeltung", "Infrarotlampe Wirkung Gesundheit" | 5 |

The script runs in dry-run mode first and prints the full categorization for manual review before any deletions.

After deletion: 11 restored originals + 5 kept articles = **16 total articles**.

The 5 kept articles will be regenerated through the current (fixed) pipeline as fresh generations, clearly distinguishable from the restored originals by their `created_at` date.

### Script location
`scripts/restore_mar30_articles.py` — standalone script using `db/client.py`'s `get_beurer_supabase()`. Dry-run mode by default (`--apply` flag to execute). Logs every action with article ID, headline, and before/after state.

### Verification
After running the script:
1. Spot-check 3 restored articles in the dashboard — content should match Mar 30 versions visible in the version bar
2. Confirm deleted articles no longer appear
3. Confirm 5 kept articles show as ready for regeneration

---

## Workstream 2: Golden Version + Quality Indicators

### 2A: Golden Version Marker

**Purpose:** Let reviewers mark a specific version as "approved baseline." Future regenerations compare against this golden version, and a one-click restore returns to it.

#### Data model

Add one column to `blog_articles`:

```sql
ALTER TABLE blog_articles ADD COLUMN golden_version JSONB DEFAULT NULL;
```

When a reviewer marks a version as golden, store:
```json
{
  "version": 3,
  "marked_at": "2026-04-13T...",
  "marked_by": "Anika",
  "article_html": "<full HTML>",
  "article_json": { ... },
  "word_count": 1540
}
```

Storing the full content (not just a version index) avoids fragility — the `feedback_history` array can grow and reindex, but the golden snapshot is self-contained.

#### API changes

New PATCH actions in `dashboard/app/api/blog-article/route.ts`:

**`action: "set_golden_version"`**
- Body: `{ article_id, version_index, marked_by }` — `version_index` is the snapshot index in `feedback_history` (or `-1` for current)
- Reads the snapshot's `article_html`/`article_json` (or current article fields if `-1`)
- Writes to `golden_version` column
- Returns updated article

**`action: "restore_golden_version"`**
- Body: `{ article_id }`
- Reads `golden_version`, fails if null
- Snapshots current state into `feedback_history` with `reason: "pre_golden_restore"`
- Writes golden's `article_html`, `article_json`, `word_count` back to the article
- Sets `html_custom: false`
- Returns updated article

**`action: "clear_golden_version"`**
- Body: `{ article_id }`
- Sets `golden_version` to null
- Returns updated article

#### UI changes in dashboard template

**Version bar:**
- Golden version pill gets a distinct style (gold border/star icon) to stand out from other version pills
- When viewing any version (including current), show a "Set as Golden" button if it's not already golden
- When a golden version exists and current differs from it, show a "Restore Golden Version" button with a confirmation dialog

**Article modal sidebar:**
- Below the review status section, show a "Golden Version" status line:
  - If set: "Golden: V3 (set by Anika, Apr 13)" with a small "Clear" link
  - If not set: "No golden version set"

### 2B: Quality Indicators

**Purpose:** Show at-a-glance quality signals per article so reviewers don't need to read every article to spot problems.

#### Data source

The pipeline already stores `_pipeline_reports` inside `article_json` with:
- `stage4.total_urls`, `stage4.valid_urls`, `stage4.dead_urls`, `stage4.replaced_urls`
- `product_validation.replacements_made`, `product_validation.claims_flagged`, `product_validation.unknown_products`
- `cleanup.valid`, `cleanup.warnings`, `cleanup.sie_detected`

For articles restored from Mar 30 snapshots (which predate `_pipeline_reports`), the post-restore safety passes will generate fresh reports.

#### Quality checks displayed

| Check | Source | Pass | Warn | Fail |
|-------|--------|------|------|------|
| Sources | `stage4` | All URLs valid | 1-2 dead | 3+ dead or <2 total |
| Products | `product_validation` | 0 unknown, 0 claims | 1 replacement | Unknown products or claims flagged |
| Category | `product_validation.claims_flagged` | 0 cross-category | — | Any cross-category product |
| App Claims | `_post_pipeline_safety` log | No HealthManager Pro in non-BP | — | HealthManager Pro found |
| Sie-Form | `cleanup.sie_detected` | false | — | true |

#### UI: Article list table

Add a "Quality" column to the articles table in the content pipeline view. Shows a composite badge:
- Green checkmark: all checks pass
- Yellow warning: 1+ warnings, 0 fails
- Red alert: 1+ fails

Hovering the badge shows a tooltip with the individual check results.

#### UI: Article modal

Add a "Quality Report" collapsible card in the right sidebar, below the review status. Shows each check as a row with pass/warn/fail icon and a one-line detail (e.g., "Sources: 3/3 valid", "Products: 1 unknown replaced (BC 87 -> BM 87)").

For articles without `_pipeline_reports` data (e.g., very old articles), show "No quality data — regenerate to generate report" in muted text.

#### Computing quality indicators

Quality indicators are computed client-side from `article_json._pipeline_reports` — no new API endpoint needed. Add a `computeQualityIndicators(articleJson)` function in the dashboard template that reads the reports and returns the check results.

---

## Files Modified

### Workstream 1 (restore script)
| File | Change |
|------|--------|
| `scripts/restore_mar30_articles.py` | **NEW** — restore script |

### Workstream 2 (golden version + quality indicators)
| File | Change |
|------|--------|
| `migrations/012_golden_version.sql` | **NEW** — add `golden_version` JSONB column |
| `dashboard/app/api/blog-article/route.ts` | Add `set_golden_version`, `restore_golden_version`, `clear_golden_version` PATCH actions |
| `styles/dashboard_template.html` | Version bar golden styling, "Set as Golden" / "Restore Golden" buttons, quality indicators in list table and modal sidebar |

---

## What This Does NOT Cover

- **Version timeline metadata** (trigger labels, pipeline version tags, change summaries) — deferred; golden version + quality indicators provide more value with less complexity
- **Arbitrary side-by-side version comparison** — the existing diff view (most recent change) suffices; golden-vs-current comparison is covered by the restore flow
- **Version grouping by sprint/batch** — retrospective forensics; the golden marker prevents the need for this
- **Partial regeneration** (section-level) — Beurer feature request, separate workstream
- **"New article" badge** — would help distinguish originals from new articles in the list; worth adding but not in this spec's scope

# Article Change Visibility — Design Spec

**Date:** 2026-03-30
**Status:** Approved

## Problem

When articles are regenerated with feedback or edited via inline comments, there is no way to see what changed. The backend already returns a `changes` array for inline edits (since commit `46eebb6`) but the frontend ignores it. Full regeneration overwrites the article entirely with no snapshot of the previous version.

## Solution

Three complementary features:

1. **Diff overlay modal** — accessible from feedback history cards, shows old vs new comparison
2. **Iframe highlights** — changed passages highlighted directly in the article preview after edits/regeneration
3. **Backend snapshots** — store previous article HTML in `feedback_history` entries to enable comparison

## Backend Changes

### File: `blog/article_service.py`

**`regenerate_article()` (~line 623):**
- Before updating status to `regenerating`, capture `article["article_html"]` as `old_html`
- When appending to `feedback_history`, include `"old_article_html": old_html` in the entry
- Add `"type": "feedback"` to the entry (currently missing, needed to distinguish from inline edits)

Updated feedback entry shape for regeneration:
```json
{
  "type": "feedback",
  "comment": "user feedback text",
  "version": 3,
  "created_at": "2026-03-30T12:00:00Z",
  "old_article_html": "<full previous article HTML>"
}
```

**`apply_inline_edits()` (~line 1025):**
- When appending to `feedback_history`, include the `changes` array in the entry (currently only returned in the API response, not persisted)

Updated feedback entry shape for inline edits:
```json
{
  "type": "inline_edit",
  "comment": "Inline edits (2): ...",
  "edits_applied": 2,
  "version": 4,
  "created_at": "2026-03-30T12:00:00Z",
  "changes": [
    { "edit_number": 1, "original_snippet": "...", "revised_snippet": "..." },
    { "edit_number": 2, "original_snippet": "...", "revised_snippet": "..." }
  ]
}
```

No new DB columns, migrations, or API endpoints required.

## Frontend — Diff Algorithm

### `computeWordDiff(oldText, newText)`

A lightweight word-level diff function in the template `<script>`. No external library.

- Splits both strings on whitespace into word token arrays
- Runs longest-common-subsequence (LCS) to identify equal/added/removed segments
- Returns array of `{ type: 'equal' | 'add' | 'remove', text: string }` segments
- Operates on visible text content (HTML tags stripped before diffing) to avoid noisy diffs from tag changes

## Frontend — Diff Overlay Modal

### Trigger

Each feedback history card gets a **"View changes"** button, shown only when diff data is available:
- Regeneration entries: shown when `fb.old_article_html` exists
- Inline edit entries: shown when `fb.changes` array exists and is non-empty

Button badge text: "Side-by-side" for regen, "{N} edits" for inline.

### Full Regeneration — Side-by-Side View

- Near-fullscreen overlay (~96vw x 94vh), matching existing article modal sizing
- Two panels: "Previous Version" (left), "Current Version" (right)
- Both panels scrollable, scroll-synced (scrolling one scrolls the other)
- Changed words highlighted: red background (`#fee2e2`) on old side, green background (`#dcfce7`) on new side
- Header shows the feedback comment that triggered regeneration
- Close button top-right (same pattern as article modal)

### Inline Edits — Unified View

- Centered modal (~700px wide, max 80vh tall, scrollable)
- One card per edit showing:
  - The user's comment
  - Unified diff: red strikethrough for removed words, green for added words
- Header shows `edits_applied` count

### Function: `showDiffOverlay(fb, currentHtml)`

- Reads `fb.type` to determine which view to render
- For `"feedback"`: strips tags from `fb.old_article_html` and `currentHtml`, runs `computeWordDiff()`, renders side-by-side panels
- For `"inline_edit"`: iterates `fb.changes`, runs `computeWordDiff()` on each `original_snippet` / `revised_snippet` pair, renders unified cards

## Frontend — Iframe Highlights

After regeneration or inline edit completes, changed passages are highlighted directly in the article iframe.

### Mechanism

A small script + style block is injected into `iframe.srcdoc`:
- `<style>` for `.change-highlight` (word-level green background, used for inline edits) and `.section-changed` (green left border, used for full regen sections)
- `<script>` with `window.addEventListener('message', ...)` to handle `highlight-changes` and `clear-highlights` messages

### For Inline Edits

After `handleApplyEdits()` updates the iframe:
- Send `postMessage({ type: 'highlight-changes', changes: data.changes })` to the iframe
- Iframe script finds each `revised_snippet` in the DOM and wraps it in `<mark class="change-highlight">`

### For Full Regeneration

After polling detects `status: completed`:
- Compute section-level diff between old HTML (from the feedback entry just saved) and new HTML by matching H2 headings
- Send `postMessage({ type: 'highlight-sections', changedHeadings: [...] })` to the iframe
- Iframe script finds matching H2 sections and applies `.section-changed` left-border highlight
- New sections (H2 not present in old version) get a small "New" badge

### Dismiss

- A floating **"Clear highlights"** pill button appears at the top of the iframe when highlights are active
- Clicking it removes all `<mark>` tags and section borders via `postMessage({ type: 'clear-highlights' })`
- Highlights also cleared on modal close/reopen (transient to current edit session)

## CSS Additions

```
/* Diff overlay */
.diff-overlay { ... }                    /* Full-screen backdrop */
.diff-modal { ... }                      /* Modal container */
.diff-panels { ... }                     /* Flex container for side-by-side */
.diff-panel { ... }                      /* Each side panel */
.diff-panel-header { ... }               /* "Previous" / "Current" labels */
.diff-word-add { background: #dcfce7; }  /* Green highlight for additions */
.diff-word-remove { background: #fee2e2; text-decoration: line-through; }
.diff-edit-card { ... }                  /* Card per inline edit in unified view */

/* Iframe highlights */
.change-highlight { background: #bbf7d0; border-radius: 2px; }
.section-changed { border-left: 3px solid #22c55e; padding-left: 8px; }
.clear-highlights-btn { ... }            /* Floating dismiss pill */
```

## i18n Keys

| Key | DE | EN |
|-----|----|----|
| `view_changes` | Änderungen anzeigen | View changes |
| `previous_version` | Vorherige Version | Previous Version |
| `current_version` | Aktuelle Version | Current Version |
| `clear_highlights` | Markierungen entfernen | Clear highlights |
| `changes_count` | {n} Änderungen | {n} changes |
| `new_section` | Neu | New |

## Updated Feedback Card

`buildFeedbackCardHTML(fb, index)` updated to render a "View changes" button:
- If `fb.type === 'feedback'` and `fb.old_article_html` exists: show button with "Side-by-side" badge
- If `fb.type === 'inline_edit'` and `fb.changes?.length > 0`: show button with "{N} edits" badge
- Button calls `showDiffOverlay(fb, currentArticleHtml)` where `currentArticleHtml` is read from the iframe's current `srcdoc`

## Updated Handlers

**`handleApplyEdits()`:** After successful response, send highlight message to iframe with `data.changes`.

**`handleRegenerate()` polling:** After `status: completed`, compute changed sections from old vs new HTML, send section highlight message to iframe. The `old_article_html` is available from the feedback history entry that was just saved (returned in the polling response via `article.feedback_history`).

## Scope Exclusions

- No version browsing or rollback — view-only comparison
- No diff for manual HTML edits (save button) — only LLM-driven changes tracked
- No persistent highlight state across sessions
- No diff for the initial article generation (no "previous" to compare against)

## Files Modified

| File | Changes |
|------|---------|
| `blog/article_service.py` | Snapshot `old_article_html` in regen history; persist `changes` in inline edit history |
| `styles/dashboard_template.html` | Diff algorithm, overlay modal, iframe highlights, updated feedback cards, CSS, i18n |
| `dashboard/template/dashboard_template.html` | Synced copy of styles template |

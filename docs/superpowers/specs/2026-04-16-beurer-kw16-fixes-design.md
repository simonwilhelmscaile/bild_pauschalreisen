# Beurer KW16 Feedback Fixes — Design

**Date:** 2026-04-16
**Source feedback:** Email from Anika Honold (Beurer) — `AW: AEO PoC KW16 Update // Beurer x scaile`, 2026-04-16 08:31 UTC. CI PDF saved to `docs/CI_Beurer_010825.pdf`; Bildsprache extract at `docs/beurer_bildsprache.md`.

## Goal

Apply targeted fixes to the ~11 client-facing Beurer articles **without regenerating content**. The prose quality is considered good; only link hygiene, citation ordering, and table-of-contents rendering need correction. Image-related feedback is out of scope and handled by a separate agent.

**Client-facing scope:** the `blog_articles` table currently contains exactly 11 completed articles, all of which Beurer sees on the content page. The SQL filter throughout this spec is `status = 'completed'`. (Verified 2026-04-16: 9 rows have `review_status = 'approved'`, 2 have `review_status = 'review'`, none are `draft` or `published`.) If future articles are added in `pending` / `generating` / `failed` status, the filter automatically excludes them.

## Scope

### In scope

1. **ToC truncation** — full section titles in the rendered table of contents
2. **Landing-page links** — strip `<a>` tags whose href contains `beurer.com/.../l/...`, keep anchor text
3. **Citation ordering** — realign `<sup>A/B/C>` letters and `Sources[]` array so first-cited source is A
4. **External overview-page sources** — detect sources whose URL resolves to a category/overview page and drop both the entry and its inline footnote

### Out of scope (explicit)

- Product-image context mismatch, Beurer Academy hero photos, Bildsprache prompt tuning — delegated to a separate image-focused agent
- Dashboard UI for manual link editing (Anika's request) — future UI work; will also cover the "wrong internal product link within correct category" case that this spec does not address
- PIM integration (STIBO GraphQL) and magazine-article update workflow — separate workstreams

## Architecture

| # | Fix | Language | Home | Artifact |
|---|-----|----------|------|----------|
| 1 | ToC full titles | TS | `dashboard/lib/html-renderer.ts` | 1-line change |
| 4a | External-source audit | Python | `scripts/` | `audit_external_sources.py` → `docs/kw16_external_sources_audit.csv` |
| 2 + 3 + 4b | Apply all mutations + re-render + version snapshot | TS | `dashboard/scripts/` | `apply-kw16-fixes.ts` (orchestrator) |
| helpers | Pure mutation functions | TS | `dashboard/lib/kw16-fixes/` | `landing-page-links.ts`, `citations.ts`, `external-sources.ts` |

### Why a language split

- The audit is read-only and benefits from the existing Firecrawl Python client already used across `crawlers/` and `services/`.
- The orchestrator must re-render `article_html` from the mutated `article_json` after any change (the dashboard serves the pre-baked HTML from `blog-article/route.ts:517`). The renderer is TypeScript in `dashboard/lib/html-renderer.ts`; calling it natively from a Node script avoids a Python-to-TS bridge and keeps the renderer as the single source of truth.
- The pure helpers are TypeScript for the same reason (co-located with the renderer) and are testable with fixture JSON.

### Version-snapshot contract (matches existing edit flow)

The dashboard already versions articles via `feedback_history` (see `article-generator.ts:511-521`). Every edit pushes an entry of shape:

```ts
{ type: "snapshot", version: N, headline, article_html, word_count, created_at }
```

before overwriting. The version modal filters `feedback_history` by `type === "snapshot"` to populate the version browser.

The orchestrator follows the same contract, but uses **one snapshot per batch run per article** (not one per mutation), so the modal shows a single "KW16 fixes" entry rather than three adjacent ones. Per-article flow:

1. Snapshot current state to `feedback_history` (pre-mutation) — only if at least one mutation is about to change something
2. Apply mutations in sequence in memory: landing-page strip → external-source drop → citation realign
3. Re-render `article_html` from the mutated `article_json` using `renderArticleHTML`
4. Push a single `{type: "feedback", comment: "KW16 batch fix: <summary>", ...}` entry summarising what changed
5. Write `article_json`, `article_html`, `word_count`, `feedback_history` in one Supabase `update`

### Flow

```
audit_external_sources.py
    └─► docs/kw16_external_sources_audit.csv
         │  (human triages `keep_or_drop` column)
         ▼
apply-kw16-fixes.ts --flagged-csv=...
    1. Fetch each client-facing article
       (status = 'completed')
    2. Snapshot pre-mutation state → feedback_history
    3. stripLandingPageLinks(article_json)
    4. dropExternalSources(article_json, dropUrls)
    5. realignCitations(article_json)
    6. renderArticleHTML(article_json) → new article_html
    7. Append feedback summary → feedback_history
    8. Update row (article_json + article_html + word_count + feedback_history)
```

## Per-item design

### Item 1 — ToC full titles

**File:** `dashboard/lib/html-renderer.ts:251-265`

**Current:**
```ts
const cleanTitle = stripHtml(title);
const words = cleanTitle.split(/\s+/).slice(0, 8);
let shortTitle = words.join(" ");
if (words.length < cleanTitle.split(/\s+/).length) shortTitle += " ...";
tocItems.push(`<li><a href="#section-${i}">${esc(shortTitle)}</a></li>`);
```

**Fix:**
```ts
const cleanTitle = stripHtml(title);
tocItems.push(`<li><a href="#section-${i}">${esc(cleanTitle)}</a></li>`);
```

No cap, no CSS changes. If long titles wrap awkwardly in narrow layouts, CSS `line-clamp` can be added later — Beurer's complaint is specifically about truncated sentences, so the least-opinionated fix ships first.

**Important propagation note:** the dashboard serves the pre-baked `article_html` column from the database (see `blog-article/route.ts:517`). A code-only renderer change therefore only affects *future* renders — it does not update any article's stored HTML. To propagate the new ToC to all ~11 client-facing articles, the orchestrator (item 5 below) must re-render every article's `article_html`, not only the ones that received data mutations.

### Item 2 — Strip `/l/` landing-page links

**Helper:** `dashboard/lib/kw16-fixes/landing-page-links.ts`

**Target fields (citation- and link-bearing content):**
- `Intro`, `Direct_Answer`, `TLDR`
- `section_01_content` … `section_09_content`
- `faq_01_answer` … `faq_06_answer`
- `paa_01_answer` … `paa_04_answer`

(Full list matches `CONTENT_FIELDS` in `scripts/fix_existing_articles.py`.)

**Match pattern:**
```
<a\s+[^>]*href="[^"]*\/\/([^"]*beurer\.com[^"]*)\/l\/[^"]*"[^>]*>([\s\S]*?)<\/a>
```

Case-insensitive host match. Scoped to `beurer.com` hosts only — a third-party URL that happens to contain `/l/` is not touched.

**Replacement:** keep capture group 2 (the anchor text) as plain text. The surrounding prose is unchanged.

**Return value:**
```ts
{
  articleJson,
  fixesApplied: number,
  affectedFields: string[],
  warnings: Array<{ article_id: string; message: string }>
}
```

**Post-strip warning:** if stripping leaves the article with fewer than 3 internal links, the orchestrator logs a warning line to stdout. Per the brainstorm decision (no link replacement, drop-only), this is accepted; no fallback insertion.

### Item 3 — Citation re-alignment

**Helper:** `dashboard/lib/kw16-fixes/citations.ts`

**Canonical reading order** (derived from `html-renderer.ts:461-475`):
1. `Direct_Answer`
2. `Intro`
3. `section_01_content` → `section_02_content` → … → `section_09_content`

PAA and FAQ answers are `esc()`-rendered at render time (lines 283, 295), so any inline HTML in those fields is escaped to entities. Stage 5 does not place citations there; excluded from the citation-extraction pass.

**Algorithm:**
1. Concatenate the citation-bearing fields in reading order into one string
2. Extract all `<sup>[A-Z]</sup>` occurrences in order → letter list
3. Compute unique first-appearance order: `firstAppearance = [...new Set(letters)]`
4. If `firstAppearance` is already `['A', 'B', 'C', ...]`, return unchanged
5. Build remap: `firstAppearance[i] → String.fromCharCode(65 + i)`
6. Apply remap via two-phase rewrite to every citation-bearing field:
   - Phase 1: replace each `<sup>X</sup>` with a unique placeholder `<sup>__${index}__</sup>`
   - Phase 2: replace each placeholder with the final letter
   (Prevents cascade bugs where `A→B` then `B→A` produces `A→A`.)
7. Rebuild `Sources[]` in the same order as `firstAppearance`: `newSources[i] = oldSources[letterToIndex(firstAppearance[i])]`

**Edge cases:**
- **Orphan `<sup>X</sup>`** (letter with no matching `Sources[]` entry): drop the orphan `<sup>` from content; log warning
- **Orphan `Sources[]` entry** (entry with no matching inline `<sup>`): keep the source at its current position, append its letter to `firstAppearance` after the cited letters. Never silently drop a source
- **No citations at all** in the article: return unchanged
- **Sources array empty**: return unchanged

**Return value:**
```ts
{
  articleJson,
  changed: boolean,
  remap: Record<string, string> | null,
  droppedOrphanSups: string[],
  warnings: Array<{ article_id: string; message: string }>
}
```

### Item 4a — External-source audit (read-only)

**Script:** `scripts/audit_external_sources.py`

**Inputs:** Supabase env vars (existing `.env`), Firecrawl env var (existing).

**Logic:**
1. Fetch all `blog_articles` rows where `status = 'completed'` (client-facing scope; see Scope section above)
2. For each row, iterate `article_json.Sources[]`
3. Skip entries where host is `beurer.com` (internal links are out of scope for this audit)
4. For each external URL, fetch via Firecrawl, extract:
   - `body_word_count` — visible text length, stripping nav/footer/aside markup via the existing `content_utils` helpers
   - `article_link_count` — count of same-host `<a>` links within the body
   - `h1_text` — first `<h1>` text content
   - `og_type` — `<meta property="og:type">` content attribute, if present
5. Apply heuristic verdict:
   - `specific_article` if `og_type == "article"` **or** (`body_word_count > 400` **and** `article_link_count < 10`)
   - `likely_overview` if `body_word_count < 200` **or** `article_link_count > 30` **or** `h1_text` matches `/^(Ratgeber|Übersicht|Themen|Kategorie|Magazin|News|Blog)\b/i`
   - `unclear` otherwise
6. Write `docs/kw16_external_sources_audit.csv` with columns: `article_id, article_keyword, source_letter, source_title, source_url, body_word_count, article_link_count, h1_text, og_type, verdict, keep_or_drop`

**`keep_or_drop` pre-fill:**
- `drop` when verdict = `likely_overview`
- `keep` when verdict = `specific_article`
- **empty** when verdict = `unclear` (forces human decision)

**Rate limiting:** ~60 external URLs expected across ~11 client-facing articles. 2s delay between Firecrawl requests (matches existing crawlers).

**Flags:** `--dry-run` — fetch and classify but do not write CSV; print summary to stdout.

**Human triage step:** open the CSV, review each row, edit `keep_or_drop` as appropriate, save.

### Item 4b — External-source drop

**Helper:** `dashboard/lib/kw16-fixes/external-sources.ts`

**Input:**
- `article_json`
- `dropUrls: Set<string>` — compiled from CSV rows with `keep_or_drop == 'drop'` matching the article's id

**Logic:**
1. For each URL in `dropUrls`:
   1. Find the index in `Sources[]` by URL equality (normalise trailing slashes)
   2. Compute the letter: `String.fromCharCode(65 + index)`
   3. Remove the entry from `Sources[]`
   4. Remove every `<sup>LETTER</sup>` occurrence from the citation-bearing fields (same list as item 3)
2. Does **not** renumber remaining letters — that is item 3's job. The orchestrator invokes item 3 after item 4b precisely so the shifted letter space re-aligns cleanly.

**Return value:**
```ts
{
  articleJson,
  droppedSources: Array<{ letter: string; url: string; title: string }>,
  warnings: Array<{ article_id: string; message: string }>
}
```

**Edge cases:**
- `Sources[]` goes to 0 after drops: log warning (Beurer's 2-3 source minimum is a soft target, not a hard post-hoc invariant); continue
- CSV URL not found in any article's `Sources[]`: log warning, skip
- CSV row with empty `keep_or_drop`: treated as `keep`. Dropping only happens on explicit `drop` value

## Orchestrator (`dashboard/scripts/apply-kw16-fixes.ts`)

**Runner:** the dashboard currently has no CLI-script pattern (`enrich-topics.ts` is library code imported by routes, not a standalone script). The orchestrator adds `tsx` as a dev dependency and a `"fix:kw16"` script entry in `dashboard/package.json`.

**CLI:**
```
cd dashboard
npm run fix:kw16 -- --flagged-csv=../docs/kw16_external_sources_audit.csv [--dry-run] [--article-id=<uuid>]
```
which under the hood runs `tsx scripts/apply-kw16-fixes.ts "$@"`.

**Flags:**
- `--flagged-csv=PATH` (required) — the triaged CSV from item 4a
- `--dry-run` — compute mutations, print per-article diff summaries, no Supabase writes
- `--article-id=UUID` — limit to one article (for targeted debugging)

**Execution per article:**
1. Fetch row, load `article_json` and current `article_html`
2. Compute mutations on a working copy of `article_json`:
   - `landingPageResult = stripLandingPageLinks(working)`
   - `sourceDropResult = dropExternalSources(working, dropUrls for this article)`
   - `citationResult = realignCitations(working)`
3. `mutationsChanged = landingPageResult.fixesApplied > 0 || sourceDropResult.droppedSources.length > 0 || citationResult.changed`
4. Always re-render: `newHtml = renderArticleHTML(working, language)` (uses the new renderer with the ToC fix)
5. `htmlChanged = newHtml !== currentHtml`
6. Branch:
   - **If `mutationsChanged == false && htmlChanged == false`**: skip entirely (nothing to do)
   - **If `mutationsChanged == false && htmlChanged == true`**: renderer-only refresh. Update `article_html` alone. No snapshot, no `feedback_history` entry (it's not a meaningful edit — just propagating a renderer bugfix)
   - **If `mutationsChanged == true`**: full fix path
     1. Snapshot pre-mutation state (`{type: "snapshot", version, headline, article_html: currentHtml, word_count, created_at}`) — exactly matches the existing edit-flow contract at `article-generator.ts:511-521`
     2. Append `{type: "feedback", comment: "KW16 batch fix: N /l/ links stripped, M sources dropped, citations realigned", ...}`
     3. Compute new `word_count` via the same helper the edit flow uses
     4. In `--dry-run`: print diff summary only. Otherwise: Supabase `update` with `article_json`, `article_html`, `word_count`, `feedback_history`
7. Print a per-article summary line on stdout: `[id8] keyword — <html-only-refresh | N links stripped, M sources dropped, citations realigned | skipped>`

**Rollback:** each touched article has a KW16-tagged snapshot in its `feedback_history`. The existing dashboard version-restore flow restores any article individually. A one-off `scripts/rollback_kw16_batch.py` (bundled in the same PR) iterates all articles, finds snapshots where the immediately-following feedback entry matches `"KW16 batch fix:"`, and restores them.

## Testing

### Unit tests (TS helpers with fixture JSON)

- **`landing-page-links.test.ts`**:
  - Fixture with beurer `/l/waerme/` link → stripped, text preserved
  - Fixture with beurer `/p/product-slug/` link → untouched
  - Fixture with `third-party.com/l/foo/` link → untouched
  - Fixture with nested HTML in anchor text (e.g. `<a href=".../l/"><strong>X</strong></a>`) → stripped, inner `<strong>` preserved
  - Fixture with multiple `/l/` links across multiple content fields → all stripped, counters match
- **`citations.test.ts`**:
  - Fixture: first `<sup>B</sup>`, second `<sup>A</sup>` → remapped to A, B; `Sources[]` swapped
  - Fixture: orphan `<sup>C</sup>` with only 2 sources → orphan dropped, warning recorded, remaining citations stable
  - Fixture: orphan `Sources[2]` with only `<sup>A</sup>` and `<sup>B</sup>` used → Source kept, placed after cited ones in the rebuilt array
  - Fixture already in `A, B, C` order → no-op, `changed: false`
  - Fixture with no `<sup>` tags anywhere → no-op
- **`external-sources.test.ts`**:
  - Fixture with 3 sources → drop middle (letter B) → `Sources[]` shortened; all `<sup>B</sup>` removed from content; `<sup>A</sup>` and `<sup>C</sup>` untouched at this stage (item 3 renumbers afterwards)
  - Drop URL that does not exist in `Sources[]` → warning, no other change

### End-to-end smoke test

1. Run audit script against the live DB — verify CSV is produced, spot-check 3-4 rows
2. Triage a minimal CSV (e.g. mark 1-2 rows as `drop`)
3. Run orchestrator with `--dry-run` and `--article-id=<one article>` — inspect printed diff
4. Remove `--dry-run` for that single article; open dashboard, confirm rendered article shows fixes and the version modal shows a new snapshot
5. Only after spot-check passes, run without `--article-id` for the full batch

## Rollout

1. Merge ToC renderer fix (`html-renderer.ts` one-line change) to `master`. Dashboard deploys via Vercel; future renders use the fixed ToC, but existing stored `article_html` rows still carry the truncated version until step 6 runs
2. Land the audit script, orchestrator, helpers, and unit tests as a second PR. Do not run yet
3. Run `python scripts/audit_external_sources.py` → produces `docs/kw16_external_sources_audit.csv`
4. Triage CSV manually (edit `keep_or_drop` column, save)
5. Dry-run orchestrator, review printed diffs for all ~11 client-facing articles
6. Real run. The orchestrator re-renders every article with the fixed ToC renderer; articles with `/l/` links, out-of-order citations, or flagged external sources additionally get a snapshot + feedback entry
7. Spot-check 3-4 articles in the dashboard; verify the ToC shows full titles and the version modal shows the KW16 snapshot for mutated articles

No further steps.

## Open questions and known gaps

- **"Wrong internal product link within correct category"** is not addressed by this spec. Deferred to future dashboard UI work.
- **Firecrawl classification accuracy** for borderline overview pages. Mitigation: the `unclear` verdict forces human decision rather than silently defaulting.
- **FAQ/PAA citation fields**: the current renderer escapes HTML in those fields, so Stage 5 cannot place citations there. If that changes in the future, the citation-realign helper's field list needs updating.

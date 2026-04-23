# Global Rules & Cross-Article Awareness — Design Spec

**Date:** 2026-03-26
**Status:** Approved
**Context:** Anika doesn't know where to submit feedback that applies to all articles. Cross-article redundancy needs to be reduced by making Stage 2 aware of existing articles.

---

## 1. Global Feedback / Manual Rules

### Problem

The content engine has an automated learning mechanism (review agent extracts learnings from approved articles into `blog/context.md` and `blog/persona.md`). But there is no way for Beurer reviewers to directly submit rules that apply across all articles (e.g., "always use Du-form", "never make healing promises"). Anika was told to use a "general feedback field" that doesn't exist.

### Design

**Storage:** New Supabase table `blog_global_rules`:

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid (PK) | Auto-generated |
| `rule_text` | text | The rule, e.g., "Immer Du-Form verwenden" |
| `author` | text | Who submitted the rule |
| `created_at` | timestamptz | Auto-generated |
| `active` | bool | Default `true`. Soft-delete sets to `false` |

**API:** New route file `dashboard/app/api/blog-rules/route.ts`:

- `GET /api/blog-rules` — returns all active rules, ordered by `created_at`
- `POST /api/blog-rules` — creates a rule: `{rule_text, author}`
- `DELETE /api/blog-rules?id=<uuid>` — soft-delete: sets `active = false`. ID passed as query parameter (not body), consistent with REST conventions.

Auth: covered by existing `dashboard/middleware.ts` cookie-based authentication — the `/api/blog-rules` path is under `/api/` which the middleware already protects.

**Injection into pipeline:** New function in `blog/beurer_context.py`:

```python
def get_global_rules() -> List[str]:
    """Fetch active global rules from Supabase for prompt injection."""
```

Called during article generation in **both** `generate_article()` and `regenerate_article()` paths in `article_service.py`. To avoid missing one path, inject rules inside `_build_custom_instructions()` in `blog/stage2/blog_writer.py` (line 479) so it applies automatically to all article generation calls.

**Injection point:** Rules are prepended to the `{custom_instructions_section}` in `blog/stage2/prompts/user_prompt.txt` (line 31). This is the existing dynamic injection point for per-generation context. Global rules appear first (highest priority), followed by any article-specific custom instructions.

```
KUNDENREGELN (vom Kunden vorgegeben — hoechste Prioritaet):
- Immer Du-Form verwenden
- Keine Heilungsversprechen
- ...
```

This coexists with auto-learned rules from `## Learnings` in `context.md`. Both feed into the prompt but are clearly separated:
- **Manual rules** (`blog_global_rules` table) — submitted directly by Beurer reviewers
- **Auto-learned rules** (`context.md` Learnings section) — extracted by review agent from approved article feedback

Manual rules take precedence in the prompt (listed first, marked as "hoechste Prioritaet").

### Files Modified

| File | Changes |
|------|---------|
| `dashboard/app/api/blog-rules/route.ts` | **NEW** — GET/POST/DELETE endpoints |
| `blog/beurer_context.py` | Add `get_global_rules()` function |
| `blog/stage2/blog_writer.py` | Inject global rules in `_build_custom_instructions()` — applies to both generate and regenerate paths |

---

## 2. Cross-Article Awareness in Stage 2

### Problem

Stage 5 already links to sibling articles, but Stage 2 (article writing) has no awareness of what other articles exist. This means the LLM may write full explanations of topics that are already covered in other published articles, instead of writing a brief mention with a cross-link.

### Design

**Fetch sibling context:** In `blog/article_service.py`, during article generation (before Stage 2), fetch published sibling articles using the existing `get_existing_article_siblings()` function from `beurer_context.py`. Extend the query to also return the `Direct_Answer` field from `article_json` as a topic summary.

**Updated query in `beurer_context.py`:**

Current `get_existing_article_siblings()` returns `{keyword, href}`. Extend to:

```python
def get_existing_article_siblings(keyword: str, limit: int = 10) -> List[Dict[str, str]]:
    """Fetch published articles for cross-linking and content awareness."""
    # Returns: [{keyword, href, summary}]
    # summary = Direct_Answer from article_json (first 200 chars)
```

The query changes from `select("keyword, publish_url")` to `select("keyword, publish_url, article_json")`, then extracts `article_json["Direct_Answer"]` as the summary in Python. This fetches the full `article_json` blob (~20-50 KB each) but article generation is a low-frequency operation (not a hot path), so the overhead is acceptable. Use the full `Direct_Answer` text (typically 40-60 words) rather than truncating — it's already concise by design.

**Edge case:** When there are zero published siblings (e.g., first article ever generated), the EXISTING ARTICLES section is omitted entirely from the prompt rather than injecting an empty section.

**Inject into Stage 2 prompt:** Pass sibling list to `_build_custom_instructions()` in `blog/stage2/blog_writer.py`, same injection point as global rules. Sibling context appears after global rules in the `{custom_instructions_section}`:

```
EXISTING ARTICLES (already published — do not repeat their content in detail):
- "Blutdruck richtig messen" (/blog/blutdruck-richtig-messen) — covers correct measurement technique, cuff positioning, timing
- "BM 27 im Test" (/blog/bm-27-im-test) — covers BM 27 review, features, comparison
If any of these topics overlap with your article, write a brief cross-reference instead of a full explanation. Example: "Mehr dazu in unserem Ratgeber zu [Blutdruck richtig messen](/blog/blutdruck-richtig-messen)."
```

**No new tables needed.** Just a richer query of `blog_articles` and a prompt section in Stage 2.

### Files Modified

| File | Changes |
|------|---------|
| `blog/beurer_context.py` | Extend `get_existing_article_siblings()` to return `summary` |
| `blog/stage2/blog_writer.py` | Inject sibling context in `_build_custom_instructions()` alongside global rules |

---

## 3. Grammar Test Cases (Item 3)

### Status

No implementation needed. The whitespace normalization mechanism (`_normalize_whitespace` in `blog/stage_cleanup/cleanup.py`) is already in place from the previous sprint.

**When Anika sends specific grammar examples from the JFX meeting:**
1. Add each example as an input/expected pair to a verification script
2. Run through `_normalize_whitespace()` to confirm they're fixed
3. If any fail, extend the regex rules to cover the new patterns

This is a test-and-fix task, not a design task. Tracked here for awareness.

---

## Execution Plan

| Task | Depends On | Complexity |
|------|-----------|------------|
| 1. Create `blog_global_rules` Supabase table | None | Trivial (manual in Supabase dashboard) |
| 2. Create `blog-rules/route.ts` API | Task 1 | Small |
| 3. Add `get_global_rules()` to `beurer_context.py` | Task 1 | Small |
| 4. Inject global rules into Stage 2 prompt | Tasks 2, 3 | Small |
| 5. Extend `get_existing_article_siblings()` with summary | None | Small |
| 6. Pass sibling context to Stage 2 prompt | Task 5 | Small |

Tasks 1-4 (global rules) and 5-6 (cross-article awareness) are independent workstreams.

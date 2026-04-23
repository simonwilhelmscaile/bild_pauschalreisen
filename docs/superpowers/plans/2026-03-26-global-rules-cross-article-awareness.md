# Global Rules & Cross-Article Awareness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a global rules API for reviewer-submitted content rules and make Stage 2 aware of existing articles to reduce cross-article redundancy.

**Architecture:** Global rules stored in a new Supabase table, fetched during article generation, injected into the Stage 2 prompt via `_build_custom_instructions()`. Sibling articles extended with summaries and also injected into Stage 2 for cross-article awareness. Both features use the existing `{custom_instructions_section}` placeholder.

**Tech Stack:** Python 3.11, Next.js 15 (API routes), Supabase (PostgREST), Gemini API

**Spec:** `docs/superpowers/specs/2026-03-26-global-rules-cross-article-awareness-design.md`

**Important context:** No test framework (no pytest). Verify via inline Python scripts or curl. The blog pipeline's Stage 2 writer lives in `blog/stage2/blog_writer.py`. The dashboard is API-only Next.js.

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `dashboard/app/api/blog-rules/route.ts` | GET/POST/DELETE API for global content rules |

### Modified Files
| File | Changes |
|------|---------|
| `blog/beurer_context.py` | Add `get_global_rules()`, extend `get_existing_article_siblings()` with summaries |
| `blog/stage2/blog_writer.py` | Extend `_build_custom_instructions()` to accept and inject global rules + sibling context |

---

## Task 1: Create Supabase Table + API Route

**Files:**
- Create: `dashboard/app/api/blog-rules/route.ts`

- [ ] **Step 1: Create the `blog_global_rules` table in Supabase**

This is a manual step in the Supabase dashboard. Create the table with:

```sql
CREATE TABLE blog_global_rules (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  rule_text text NOT NULL,
  author text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now(),
  active boolean DEFAULT true
);
```

- [ ] **Step 2: Create the API route**

Create `dashboard/app/api/blog-rules/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const supabase = getSupabase();
    const { data, error } = await supabase
      .from("blog_global_rules")
      .select("*")
      .eq("active", true)
      .order("created_at", { ascending: true });

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }
    return NextResponse.json({ rules: data });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const supabase = getSupabase();
    const body = await request.json();
    const { rule_text, author } = body;

    if (!rule_text || !rule_text.trim()) {
      return NextResponse.json({ error: "rule_text is required" }, { status: 400 });
    }

    const { data, error } = await supabase
      .from("blog_global_rules")
      .insert({ rule_text: rule_text.trim(), author: author || "Unknown" })
      .select()
      .single();

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }
    return NextResponse.json({ rule: data }, { status: 201 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const supabase = getSupabase();
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");

    if (!id) {
      return NextResponse.json({ error: "id query parameter is required" }, { status: 400 });
    }

    const { error } = await supabase
      .from("blog_global_rules")
      .update({ active: false })
      .eq("id", id);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }
    return NextResponse.json({ success: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
```

- [ ] **Step 3: Verify the API**

Start the dashboard dev server and test:
```bash
# Create a rule
curl -s -X POST http://localhost:3000/api/blog-rules \
  -H "Content-Type: application/json" \
  -d '{"rule_text": "Immer Du-Form verwenden", "author": "Anika"}' | python -m json.tool

# List rules
curl -s http://localhost:3000/api/blog-rules | python -m json.tool

# Deactivate (use the id from the create response)
curl -s -X DELETE "http://localhost:3000/api/blog-rules?id=<uuid>"
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/api/blog-rules/route.ts
git commit -m "feat: add global content rules API (GET/POST/DELETE)

New Supabase table blog_global_rules stores reviewer-submitted rules
that apply across all articles. Soft-delete via active flag.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Add `get_global_rules()` to beurer_context.py

**Files:**
- Modify: `blog/beurer_context.py` (add new function after `get_existing_article_siblings` at line 281)

- [ ] **Step 1: Add the function**

In `blog/beurer_context.py`, add after `get_existing_article_siblings()` (after line 281):

```python
def get_global_rules() -> List[str]:
    """Fetch active global content rules from Supabase.

    These are reviewer-submitted rules that apply to all articles,
    e.g., 'Immer Du-Form verwenden' or 'Keine Heilungsversprechen'.

    Returns list of rule text strings, ordered by creation date.
    """
    try:
        from db.client import get_beurer_supabase
        supabase = get_beurer_supabase()
        result = (
            supabase.table("blog_global_rules")
            .select("rule_text")
            .eq("active", True)
            .order("created_at")
            .execute()
        )
        return [row["rule_text"] for row in (result.data or []) if row.get("rule_text")]
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to fetch global rules: %s", e)
        return []
```

- [ ] **Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '.'); from blog.beurer_context import get_global_rules; rules = get_global_rules(); print(f'{len(rules)} rules: {rules}')"
```

Expected: `0 rules: []` (or the test rule if you created one in Task 1).

- [ ] **Step 3: Commit**

```bash
git add blog/beurer_context.py
git commit -m "feat: add get_global_rules() to fetch reviewer content rules

Queries blog_global_rules table for active rules.
Returns list of rule text strings for prompt injection.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Extend `get_existing_article_siblings()` with Summaries

**Files:**
- Modify: `blog/beurer_context.py:242-281` (extend existing function)

- [ ] **Step 1: Update the query and return format**

In `blog/beurer_context.py`, modify `get_existing_article_siblings()`:

Change the select from:
```python
            .select("keyword, publish_url")
```
to:
```python
            .select("keyword, publish_url, article_json")
```

Change the sibling construction loop (lines 266-275) to also extract a summary:

```python
        for row in (result.data or []):
            kw = row.get("keyword", "")
            href = (row.get("publish_url") or "").strip()
            if not href or kw.lower().strip() == current_lower:
                continue
            # Extract Direct_Answer as topic summary
            article_json = row.get("article_json") or {}
            if isinstance(article_json, str):
                import json as _json
                try:
                    article_json = _json.loads(article_json)
                except (ValueError, TypeError):
                    article_json = {}
            summary = (article_json.get("Direct_Answer") or "").strip()
            siblings.append({"keyword": kw, "href": href, "summary": summary})
            if len(siblings) >= limit:
                break
```

The existing callers (Stage 5 in `article_service.py` and `pipeline.py`) only use `keyword` and `href` keys, so adding `summary` is backwards-compatible.

- [ ] **Step 2: Verify**

```bash
python -c "import sys; sys.path.insert(0, '.'); from blog.beurer_context import get_existing_article_siblings; sibs = get_existing_article_siblings('test', limit=3); print(f'{len(sibs)} siblings'); [print(f'  {s[\"keyword\"]}: {s.get(\"summary\",\"\")[:80]}') for s in sibs]"
```

- [ ] **Step 3: Commit**

```bash
git add blog/beurer_context.py
git commit -m "feat: extend article siblings with Direct_Answer summaries

get_existing_article_siblings() now returns {keyword, href, summary}
for cross-article awareness in Stage 2 prompt.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Inject Global Rules + Sibling Context into Stage 2

**Files:**
- Modify: `blog/stage2/blog_writer.py:479-511` (extend `_build_custom_instructions`)
- Modify: `blog/stage2/blog_writer.py:141-214` (pass new params through `write_article`)

- [ ] **Step 1: Extend `_build_custom_instructions` signature and logic**

In `blog/stage2/blog_writer.py`, modify `_build_custom_instructions()` (line 479):

```python
def _build_custom_instructions(
    batch_instructions: Optional[str],
    keyword_instructions: Optional[str],
    global_rules: Optional[List[str]] = None,
    sibling_articles: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Build combined custom instructions section.

    Includes (in priority order):
    1. Global customer rules (highest priority)
    2. Sibling article awareness (cross-article dedup)
    3. Batch instructions
    4. Keyword instructions
    """
    parts = []

    # Global rules (highest priority)
    if global_rules:
        rules_text = "\n".join(f"- {r}" for r in global_rules)
        parts.append(
            f"KUNDENREGELN (vom Kunden vorgegeben — hoechste Prioritaet):\n{rules_text}"
        )

    # Sibling article awareness
    if sibling_articles:
        sibling_lines = []
        for s in sibling_articles:
            summary = s.get("summary", "")
            summary_text = f" — {summary}" if summary else ""
            sibling_lines.append(f'- "{s["keyword"]}" ({s["href"]}){summary_text}')
        parts.append(
            "EXISTING ARTICLES (already published — do not repeat their content in detail):\n"
            + "\n".join(sibling_lines)
            + '\nIf any of these topics overlap with your article, write a brief cross-reference '
            + 'instead of a full explanation. Example: "Mehr dazu in unserem Ratgeber zu '
            + '[Thema](/blog/thema)."'
        )

    # Batch instructions
    if batch_instructions:
        parts.append(batch_instructions.strip())

    # Keyword instructions
    if keyword_instructions:
        if batch_instructions:
            parts.append(f"Additional for this article: {keyword_instructions.strip()}")
        else:
            parts.append(keyword_instructions.strip())

    if not parts:
        return ""

    return "MANDATORY CUSTOM INSTRUCTIONS (follow these with highest priority, they override default behaviors):\n\n" + "\n\n".join(parts)
```

Add `from typing import List, Dict` to the imports at the top of the file if `List` and `Dict` are not already imported.

- [ ] **Step 2: Update `write_article` to accept and pass new params**

In `blog/stage2/blog_writer.py`, update the `write_article()` function signature (line 141) to add two new optional params:

```python
async def write_article(
    keyword: str,
    company_context: Dict[str, Any],
    word_count: int = 2000,
    language: str = "en",
    country: str = "United States",
    batch_instructions: Optional[str] = None,
    keyword_instructions: Optional[str] = None,
    global_rules: Optional[List[str]] = None,
    sibling_articles: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None,
) -> ArticleOutput:
```

Then at line 193, update the `_build_custom_instructions` call:

```python
        custom_instructions_section = _build_custom_instructions(
            batch_instructions, keyword_instructions,
            global_rules=global_rules,
            sibling_articles=sibling_articles,
        )
```

Also update the `BlogWriter.write_article` method (the wrapper class) to pass through the new params. Find the wrapper method and add `global_rules` and `sibling_articles` to its signature and the inner `write_article()` call.

- [ ] **Step 3: Pass global rules and siblings from article_service.py**

In `blog/article_service.py`, find `generate_article()` where it calls `_blog_writer.write_article()` or `write_article()`. Before the call, fetch global rules and siblings:

```python
    # Fetch global rules and sibling articles for Stage 2 awareness
    from .beurer_context import get_global_rules, get_existing_article_siblings
    _global_rules = get_global_rules()
    _sibling_articles = get_existing_article_siblings(keyword, limit=10)
    if _global_rules:
        logger.info(f"Injecting {len(_global_rules)} global rules into Stage 2")
    if _sibling_articles:
        logger.info(f"Injecting {len(_sibling_articles)} sibling articles into Stage 2")
```

Then pass to the `write_article` call:
```python
    global_rules=_global_rules,
    sibling_articles=_sibling_articles,
```

Do the same in `regenerate_article()` if it has a separate `write_article()` call.

- [ ] **Step 4: Verify end-to-end**

Create a test rule, then generate a test article and check the logs:

```bash
# Add a test rule (if not done already)
curl -s -X POST http://localhost:3000/api/blog-rules \
  -H "Content-Type: application/json" \
  -d '{"rule_text": "Immer Du-Form verwenden", "author": "Test"}'

# Generate an article and check server logs for:
# "Injecting N global rules into Stage 2"
# "Injecting N sibling articles into Stage 2"
```

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/blog_writer.py blog/article_service.py
git commit -m "feat: inject global rules and sibling context into Stage 2 prompt

_build_custom_instructions() now accepts global_rules and sibling_articles.
Global rules appear first (highest priority). Sibling articles enable
cross-references instead of content repetition.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Dependency Map

```
Task 1 (API route)        ─── independent
Task 2 (get_global_rules) ─── depends on Task 1 (needs table)
Task 3 (sibling summaries)─── independent
Task 4 (inject into Stage 2) ── depends on Tasks 2 + 3
```

Tasks 1 and 3 can run in parallel. Task 2 needs the Supabase table from Task 1. Task 4 ties everything together.

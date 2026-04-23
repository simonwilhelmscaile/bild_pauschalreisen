# Article Source Enforcement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee every generated article has at least 3 verified sources by making the Python backend the sole generation path and adding minimum source count enforcement.

**Architecture:** Remove the TS generator fallback from the dashboard API route so all article generation goes through the Python 5-stage pipeline. Add a supplementary source fetch in Python Stage 2 when fewer than 3 sources are returned.

**Tech Stack:** TypeScript (Next.js API route), Python (FastAPI + Gemini API)

**Spec:** `docs/superpowers/specs/2026-04-02-article-source-enforcement-design.md`

---

### Task 1: Remove TS fallback from POST (create article)

**Files:**
- Modify: `dashboard/app/api/blog-article/route.ts:127-209`

- [ ] **Step 1: Replace the POST handler to require BACKEND_URL and remove TS fallback**

Replace lines 127-209 with:

```typescript
export async function POST(request: NextRequest) {
  try {
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Article generation backend not configured" },
        { status: 503 }
      );
    }

    const body = await request.json();
    const { source_item_id, keyword, language, word_count, social_context } = body;

    if (!keyword) {
      return NextResponse.json({ error: "keyword is required" }, { status: 400 });
    }

    try {
      const backendRes = await proxyToBackend("/articles", "POST", {
        keyword,
        source_item_id: source_item_id || null,
        language: language || "de",
        word_count: word_count || 1500,
        social_context: social_context || null,
      });
      const data = await backendRes.json();
      return NextResponse.json(data, { status: backendRes.status });
    } catch (proxyErr) {
      console.error("Backend proxy failed:", proxyErr);
      return NextResponse.json(
        { error: "Article generation backend unavailable" },
        { status: 503 }
      );
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
```

- [ ] **Step 2: Verify the change compiles**

Run: `cd dashboard && npx tsc --noEmit`
Expected: No errors related to `route.ts`

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/api/blog-article/route.ts
git commit -m "fix: remove TS fallback from POST article creation, require BACKEND_URL"
```

---

### Task 2: Remove TS fallback from PUT (regenerate article)

**Files:**
- Modify: `dashboard/app/api/blog-article/route.ts:211-254`

- [ ] **Step 1: Replace the PUT handler to require BACKEND_URL and remove TS fallback**

Replace the PUT handler (lines 211-254 after Task 1's edits — locate the `export async function PUT` block) with:

```typescript
export async function PUT(request: NextRequest) {
  try {
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Article generation backend not configured" },
        { status: 503 }
      );
    }

    const body = await request.json();
    const { article_id, feedback, from_scratch } = body;

    if (!article_id) {
      return NextResponse.json({ error: "article_id is required" }, { status: 400 });
    }

    try {
      const backendRes = await proxyToBackend("/articles", "PUT", {
        article_id,
        feedback: feedback || null,
        from_scratch: from_scratch || false,
      });
      const data = await backendRes.json();
      return NextResponse.json(data, { status: backendRes.status });
    } catch (proxyErr) {
      console.error("Backend proxy failed:", proxyErr);
      return NextResponse.json(
        { error: "Article generation backend unavailable" },
        { status: 503 }
      );
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
```

- [ ] **Step 2: Verify the change compiles**

Run: `cd dashboard && npx tsc --noEmit`
Expected: No errors related to `route.ts`

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/api/blog-article/route.ts
git commit -m "fix: remove TS fallback from PUT article regeneration, require BACKEND_URL"
```

---

### Task 3: Remove TS fallback from inline edits

**Files:**
- Modify: `dashboard/app/api/blog-article/route.ts:458-486`

- [ ] **Step 1: Replace the inline edits section to require BACKEND_URL and remove TS fallback**

Find this block inside the `PATCH` handler (after the review_status and other PATCH actions, starting at the `// Inline edits` comment):

```typescript
    // Inline edits
    const { edits } = body;
    if (!edits || !Array.isArray(edits) || edits.length === 0) {
      return NextResponse.json({ error: "edits array is required" }, { status: 400 });
    }

    // If BACKEND_URL is set, proxy inline edits to Python backend
    if (BACKEND_URL) {
      try {
        const backendRes = await proxyToBackend("/articles/inline-edits", "POST", {
          article_id,
          edits,
        });
        const data = await backendRes.json();
        return NextResponse.json(data, { status: backendRes.status });
      } catch (proxyErr) {
        console.error("Backend proxy failed for inline edits, falling back to TS:", proxyErr);
        // Fall through to TS inline edit
      }
    }

    // Fallback: TS inline edit
    const result = await applyInlineEdits({ articleId: article_id, edits });
    return NextResponse.json(result);
```

Replace with:

```typescript
    // Inline edits
    const { edits } = body;
    if (!edits || !Array.isArray(edits) || edits.length === 0) {
      return NextResponse.json({ error: "edits array is required" }, { status: 400 });
    }

    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Article generation backend not configured" },
        { status: 503 }
      );
    }

    try {
      const backendRes = await proxyToBackend("/articles/inline-edits", "POST", {
        article_id,
        edits,
      });
      const data = await backendRes.json();
      return NextResponse.json(data, { status: backendRes.status });
    } catch (proxyErr) {
      console.error("Backend proxy failed for inline edits:", proxyErr);
      return NextResponse.json(
        { error: "Article generation backend unavailable" },
        { status: 503 }
      );
    }
```

- [ ] **Step 2: Remove unused TS generator imports**

At the top of the file (line 3), change:

```typescript
import { generateArticle, regenerateArticle, applyInlineEdits } from "@/lib/article-generator";
```

to:

```typescript
// TS article-generator kept for reference but no longer used as fallback.
// All generation proxies to Python backend via BACKEND_URL.
```

- [ ] **Step 3: Verify the change compiles**

Run: `cd dashboard && npx tsc --noEmit`
Expected: No errors. If `renderArticleHtml` import (line 4) is also now unused, remove it too.

- [ ] **Step 4: Commit**

```bash
git add dashboard/app/api/blog-article/route.ts
git commit -m "fix: remove TS fallback from inline edits, remove unused generator imports"
```

---

### Task 4: Add minimum source count enforcement in Python Stage 2

**Files:**
- Modify: `blog/stage2/blog_writer.py:258-309`

- [ ] **Step 1: Add source supplement logic after the existing fallback chain**

In `blog/stage2/blog_writer.py`, find the block that ends with (around line 307-309):

```python
                except Exception as e:
                    logger.warning(f"Follow-up sources call failed: {e}")
        
        return article
```

Replace `return article` (the last line before `except Exception as e: logger.error`) with:

```python
        # Enforce minimum 3 sources — supplement if needed
        if len(article.Sources) > 0 and len(article.Sources) < 3:
            needed = 3 - len(article.Sources)
            existing_urls = [s.url for s in article.Sources]
            existing_titles = [s.title for s in article.Sources]
            logger.info(f"Article has {len(article.Sources)} sources, need {needed} more — making supplementary call")
            try:
                supplement_prompt = (
                    f"Article topic: {keyword}\n"
                    f"Article headline: {result.get('Headline', keyword)}\n\n"
                    f"I already have these sources:\n"
                    + "\n".join(f"- {t} ({u})" for t, u in zip(existing_titles, existing_urls))
                    + f"\n\nFind {needed} ADDITIONAL high-quality, authoritative sources that support this article. "
                    f"Do NOT repeat any of the existing sources above.\n"
                    f"Use Google Search to find REAL URLs.\n\n"
                    f"Return ONLY valid JSON:\n"
                    f'{{"Sources": [{{"title": "Source Name", "url": "https://...", "description": "1-2 sentences explaining what this source provides"}}]}}'
                )
                supplement_result = await client.generate(
                    prompt=supplement_prompt,
                    system_instruction="You are a research assistant. Find and return real, authoritative sources using Google Search. Each source MUST have title, url, and description fields. Do NOT return sources the user already has.",
                    use_url_context=False,
                    use_google_search=True,
                    json_output=True,
                    extract_sources=True,
                    temperature=0.2,
                    max_tokens=2048,
                )

                new_sources = supplement_result.get("Sources", [])
                if not new_sources:
                    new_sources = supplement_result.get("_grounding_sources", [])

                if isinstance(new_sources, list) and len(new_sources) > 0:
                    # Deduplicate by domain+path
                    from urllib.parse import urlparse
                    existing_keys = set()
                    for u in existing_urls:
                        parsed = urlparse(u)
                        existing_keys.add(parsed.netloc + parsed.path.rstrip("/"))

                    merged = list(result.get("Sources", []))
                    for src in new_sources:
                        if not isinstance(src, dict) or not src.get("url"):
                            continue
                        parsed = urlparse(src["url"])
                        key = parsed.netloc + parsed.path.rstrip("/")
                        if key not in existing_keys:
                            merged.append(src)
                            existing_keys.add(key)
                            if len(merged) >= 5:
                                break

                    result["Sources"] = merged
                    article = ArticleOutput(**result)
                    logger.info(f"After supplement: {len(article.Sources)} total sources")
                else:
                    logger.warning("Supplementary sources call returned nothing")

            except Exception as e:
                logger.warning(f"Supplementary sources call failed: {e}")

        return article
```

- [ ] **Step 2: Verify the change loads correctly**

Run: `python -c "from blog.stage2.blog_writer import write_article; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add blog/stage2/blog_writer.py
git commit -m "feat: enforce minimum 3 sources per article with supplementary Gemini call"
```

---

### Task 5: End-to-end verification

- [ ] **Step 1: Start the Python backend**

Run: `python -m uvicorn app:app --port 8004`
Expected: Server starts on port 8004

- [ ] **Step 2: Test article generation through the Python backend directly**

Run:
```bash
curl -s -X POST http://localhost:8004/api/v1/blog/articles \
  -H "Content-Type: application/json" \
  -d '{"keyword": "TENS Gerät Rückenschmerzen", "language": "de", "word_count": 800}'
```

Expected: Returns `{"id": "...", "status": "generating", ...}`

- [ ] **Step 3: Poll until completed and verify source count**

Wait ~3 minutes for the pipeline, then:

```bash
curl -s http://localhost:8004/api/v1/blog/articles/<ID> | python -c "
import json, sys
data = json.load(sys.stdin)
sources = (data.get('article_json') or {}).get('Sources', [])
print(f'Status: {data[\"status\"]}')
print(f'Sources: {len(sources)}')
assert len(sources) >= 3, f'Expected >=3 sources, got {len(sources)}'
print('PASS: 3+ sources')
"
```

Expected: `PASS: 3+ sources`

- [ ] **Step 4: Test dashboard proxy returns 503 when backend is down**

Stop the Python backend, then:

```bash
curl -s -X POST http://localhost:3000/api/blog-article \
  -H "Content-Type: application/json" \
  -d '{"keyword": "test"}' | python -c "
import json, sys
data = json.load(sys.stdin)
print(f'Error: {data.get(\"error\")}')
assert data.get('error') == 'Article generation backend unavailable'
print('PASS: 503 on backend down')
"
```

Expected: `PASS: 503 on backend down`

- [ ] **Step 5: Commit all changes**

```bash
git add -A
git commit -m "test: verify article source enforcement end-to-end"
```

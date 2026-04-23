# Reliable Article Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make article sources 100% reliable by using Google Search grounding URLs as the primary source (they're real), enriching them with Gemini-written descriptions, HTTP-verifying before acceptance, and fixing the broken Stage 4 replacement pipeline.

**Architecture:** Three changes: (1) Fix `generate_with_schema()` to support `extract_sources` so Stage 4 replacements work again. (2) Rewrite Stage 2 source collection to prefer grounding URLs over AI-generated URLs, with immediate HTTP verification. (3) Add a post-verification supplementary call that runs when sources drop below 3 after Stage 4.

**Tech Stack:** Python, Gemini API (google.genai), httpx (async HTTP), existing `core/gemini_client.py`, `blog/stage2/blog_writer.py`, `blog/stage4/stage_4.py`, `blog/stage4/http_checker.py`

---

### Task 1: Fix `generate_with_schema()` missing `extract_sources` parameter

The `url_verifier.py` calls `generate_with_schema(extract_sources=True)` but that method doesn't accept the parameter, causing ALL Stage 4 replacement searches to fail silently.

**Files:**
- Modify: `core/gemini_client.py:151-199` (add `extract_sources` param + grounding extraction)

- [ ] **Step 1: Add `extract_sources` parameter to `generate_with_schema()`**

In `core/gemini_client.py`, update the method signature and add grounding extraction logic:

```python
async def generate_with_schema(
    self,
    prompt: str,
    response_schema: Any,
    use_url_context: bool = False,
    use_google_search: bool = False,
    extract_sources: bool = False,
    temperature: float = 0.7,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
```

And after parsing the JSON result (around line 199), before the `return`, add:

```python
    # Extract grounding sources if requested
    if extract_sources and response.candidates:
        grounding_sources = self._extract_grounding_sources(response.candidates)
        if grounding_sources:
            result["_grounding_sources"] = grounding_sources

    return result
```

- [ ] **Step 2: Verify the fix compiles**

Run: `python -c "import ast; ast.parse(open('core/gemini_client.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add core/gemini_client.py
git commit -m "fix: add extract_sources to generate_with_schema — unblocks Stage 4 replacements"
```

---

### Task 2: Add HTTP verification helper for source URLs

Create a lightweight helper that checks a list of source URLs and returns only the alive ones. This will be reused by Stage 2 (pre-verification) and the post-Stage-4 supplementary step.

**Files:**
- Modify: `blog/stage4/http_checker.py` (add `check_source_urls()` convenience function)

- [ ] **Step 1: Add `check_source_urls()` to `http_checker.py`**

Add this at module level, after the `HTTPChecker` class:

```python
async def check_source_urls(
    urls: List[str],
    timeout: float = 3.0,
    max_concurrent: int = 10,
) -> Tuple[List[str], List[str]]:
    """Quick check which URLs are alive. Returns (alive_urls, dead_urls)."""
    if not urls:
        return [], []
    checker = HTTPChecker(timeout=timeout, max_concurrent=max_concurrent)
    results = await checker.check_urls(set(urls))
    alive, dead = checker.categorize_results(results)
    # Also treat homepage redirects as dead
    homepage_redirects = {r.url for r in results if r.is_homepage_redirect}
    alive = [u for u in alive if u not in homepage_redirects]
    dead = dead + list(homepage_redirects)
    return alive, dead
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('blog/stage4/http_checker.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add blog/stage4/http_checker.py
git commit -m "feat: add check_source_urls convenience function for source verification"
```

---

### Task 3: Rewrite Stage 2 source collection — grounding-first with HTTP verification

Replace the current "trust AI sources, fall back to grounding" approach with "use grounding URLs as primary, enrich with AI descriptions, HTTP-verify before accepting."

**Files:**
- Modify: `blog/stage2/blog_writer.py:238-370` (rewrite source handling after article generation)

- [ ] **Step 1: Add source verification + enrichment helper**

Add this function above `write_article()` in `blog_writer.py` (around line 138):

```python
async def _build_verified_sources(
    client,
    keyword: str,
    headline: str,
    ai_sources: list,
    grounding_sources: list,
) -> list:
    """Build a verified source list using grounding URLs as primary.

    Strategy:
    1. Merge grounding URLs (real) + AI-generated URLs (may be hallucinated)
    2. HTTP-check all URLs
    3. Keep only alive ones
    4. Enrich grounding sources with AI-written descriptions if missing
    5. If < 3 sources, make a supplementary Gemini call for more

    Returns list of Source dicts with title, url, description.
    """
    import sys
    from pathlib import Path
    _stage4_dir = Path(__file__).parent.parent / "stage4"
    if str(_stage4_dir) not in sys.path:
        sys.path.insert(0, str(_stage4_dir))
    from http_checker import check_source_urls

    # Deduplicate by URL, preferring AI sources (have better titles/descriptions)
    seen_urls = set()
    candidates = []

    # AI sources first (have descriptions)
    for src in (ai_sources or []):
        if not isinstance(src, dict) or not src.get("url"):
            continue
        url = src["url"].strip()
        if url not in seen_urls:
            seen_urls.add(url)
            candidates.append(src)

    # Add grounding sources not already covered
    for src in (grounding_sources or []):
        if not isinstance(src, dict) or not src.get("url"):
            continue
        url = src["url"].strip()
        if url not in seen_urls:
            seen_urls.add(url)
            candidates.append(src)

    if not candidates:
        return []

    # HTTP-verify all candidate URLs
    all_urls = [c["url"] for c in candidates]
    alive_urls, dead_urls = await check_source_urls(all_urls, timeout=3.0)
    alive_set = set(alive_urls)

    if dead_urls:
        logger.info(f"Source verification: {len(alive_urls)} alive, {len(dead_urls)} dead")

    verified = [c for c in candidates if c["url"] in alive_set]

    # Enrich sources missing descriptions (common for grounding sources)
    needs_enrichment = [s for s in verified if not s.get("description", "").strip() or len(s.get("description", "")) < 10]
    if needs_enrichment:
        logger.info(f"Enriching {len(needs_enrichment)} sources with descriptions")
        try:
            src_list = "\n".join(f"- {s.get('title', 'Unknown')}: {s['url']}" for s in needs_enrichment)
            enrich_prompt = (
                f"Article topic: {keyword}\n"
                f"Article headline: {headline}\n\n"
                f"Write a 1-2 sentence description for each source explaining what it provides:\n{src_list}\n\n"
                f"Return JSON: {{\"descriptions\": [\"desc for source 1\", \"desc for source 2\", ...]}}"
            )
            enrich_result = await client.generate(
                prompt=enrich_prompt,
                json_output=True,
                temperature=0.2,
                max_tokens=1024,
            )
            descriptions = enrich_result.get("descriptions", [])
            for i, src in enumerate(needs_enrichment):
                if i < len(descriptions) and descriptions[i]:
                    src["description"] = descriptions[i]
                elif not src.get("description"):
                    src["description"] = f"Source: {src.get('title', 'Reference')} — relevant to {keyword}"
        except Exception as e:
            logger.warning(f"Source enrichment failed: {e}")
            for src in needs_enrichment:
                if not src.get("description"):
                    src["description"] = f"Source: {src.get('title', 'Reference')} — relevant to {keyword}"

    # Supplementary call if under 3 verified sources
    if len(verified) < 3:
        needed = 3 - len(verified)
        logger.info(f"Only {len(verified)} verified sources — searching for {needed} more")
        try:
            existing_text = "\n".join(f"- {s.get('title', '?')} ({s['url']})" for s in verified)
            supplement_prompt = (
                f"Article topic: {keyword}\n"
                f"Article headline: {headline}\n\n"
                f"I need {needed} additional authoritative sources for this article.\n"
                f"Existing sources (do NOT repeat):\n{existing_text}\n\n"
                f"Use Google Search to find REAL URLs from authoritative health sources "
                f"(e.g. medical journals, health organizations, university hospitals).\n\n"
                f"Return ONLY valid JSON:\n"
                f'{{\"Sources\": [{{\"title\": \"Name\", \"url\": \"https://...\", \"description\": \"1-2 sentences\"}}]}}'
            )
            supp_result = await client.generate(
                prompt=supplement_prompt,
                system_instruction="Find real, authoritative sources using Google Search. Each source MUST have title, url, and description.",
                use_google_search=True,
                json_output=True,
                extract_sources=True,
                temperature=0.2,
                max_tokens=2048,
            )

            # Prefer grounding URLs from supplementary call (most reliable)
            supp_grounding = supp_result.get("_grounding_sources", [])
            supp_ai = supp_result.get("Sources", [])
            supp_candidates = []
            for src in supp_ai + supp_grounding:
                if isinstance(src, dict) and src.get("url") and src["url"] not in seen_urls:
                    supp_candidates.append(src)
                    seen_urls.add(src["url"])

            if supp_candidates:
                supp_urls = [c["url"] for c in supp_candidates]
                supp_alive, _ = await check_source_urls(supp_urls, timeout=3.0)
                supp_alive_set = set(supp_alive)
                for c in supp_candidates:
                    if c["url"] in supp_alive_set:
                        if not c.get("description") or len(c.get("description", "")) < 10:
                            c["description"] = f"Source: {c.get('title', 'Reference')} — relevant to {keyword}"
                        verified.append(c)
                        if len(verified) >= 5:
                            break
                logger.info(f"After supplement: {len(verified)} verified sources")
        except Exception as e:
            logger.warning(f"Supplementary source search failed: {e}")

    return verified[:5]
```

- [ ] **Step 2: Replace source handling in `write_article()`**

In `blog_writer.py`, replace the entire source handling block (from `# Use ONLY AI-generated sources` around line 238, through the end of the supplementary call around line 369) with:

```python
        # --- Verified source pipeline ---
        ai_sources = result.get("Sources", [])
        grounding_sources = result.pop("_grounding_sources", []) or []

        logger.info(f"Raw sources: {len(ai_sources)} AI-generated, {len(grounding_sources)} grounding")

        verified_sources = await _build_verified_sources(
            client=client,
            keyword=keyword,
            headline=result.get("Headline", keyword),
            ai_sources=ai_sources,
            grounding_sources=grounding_sources,
        )

        result["Sources"] = verified_sources
        logger.info(f"Final verified sources: {len(verified_sources)}")

        article = ArticleOutput(**result)
```

This replaces all the old source recovery logic (grounding fallback, follow-up call, supplementary call) with the single `_build_verified_sources()` function.

- [ ] **Step 3: Verify syntax**

Run: `python -c "import ast; ast.parse(open('blog/stage2/blog_writer.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add blog/stage2/blog_writer.py
git commit -m "feat: grounding-first source pipeline with HTTP verification in Stage 2"
```

---

### Task 4: Add post-Stage-4 source recovery

After Stage 4 removes dead sources, check if we're below 3. If so, run a supplementary Gemini call to find replacements — now that `generate_with_schema` supports `extract_sources`, this should work.

**Files:**
- Modify: `blog/article_service.py:155-178` (add source recovery after Stage 4)

- [ ] **Step 1: Add source recovery after Stage 4 in `_run_stages_4_5_cleanup()`**

In `blog/article_service.py`, after the Stage 4 try/except block (around line 178, after `pipeline_reports["stage4"] = ...`), add:

```python
    # Post-Stage-4 source recovery: if sources dropped below 3, supplement
    sources = article_dict.get("Sources", [])
    if isinstance(sources, list) and 0 < len(sources) < 3:
        logger.info(f"Post-Stage-4: only {len(sources)} sources remain, supplementing...")
        try:
            from .stage2.blog_writer import _build_verified_sources

            if GeminiClient is None:
                from core.gemini_client import GeminiClient as _GC
            else:
                _GC = GeminiClient
            from core.config import ServiceType as _ST
            _client = _GC(service_type=_ST.BLOG) if _ST else _GC()

            recovered = await _build_verified_sources(
                client=_client,
                keyword=keyword,
                headline=article_dict.get("Headline", keyword),
                ai_sources=sources,  # Keep existing verified sources
                grounding_sources=[],
            )
            if len(recovered) > len(sources):
                article_dict["Sources"] = recovered
                logger.info(f"Post-Stage-4: recovered to {len(recovered)} sources")
                pipeline_reports["source_recovery"] = {
                    "before": len(sources),
                    "after": len(recovered),
                }
        except Exception as e:
            logger.warning(f"Post-Stage-4 source recovery failed (non-blocking): {e}")
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('blog/article_service.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add blog/article_service.py
git commit -m "feat: post-Stage-4 source recovery when sources drop below 3"
```

---

### Task 5: Update Stage 4 to keep dead sources when no replacement found

Revert the aggressive source removal from Bug 2 fix. Instead: remove dead sources only when a replacement was found. When no replacement exists, keep the source (with its footnote) but mark the URL as broken. The footnote sync in cleanup still handles any orphans from *replaced* sources.

**Files:**
- Modify: `blog/stage4/stage_4.py:609-619` (revert to keep-with-warning for unreplaceable dead URLs)

- [ ] **Step 1: Update unreplaceable URL handling for Sources**

In `blog/stage4/stage_4.py`, replace the source removal block (around line 609-619):

```python
                for field in fields:
                    # For unreplaceable dead Sources: keep the entry so footnotes
                    # stay valid. The post-Stage-4 recovery will supplement with
                    # new verified sources. Only replaced sources get removed.
                    if field == "Sources":
                        logger.info(f"    Keeping source with dead URL (no replacement): {bad_url[:60]}...")
                        continue
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('blog/stage4/stage_4.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add blog/stage4/stage_4.py
git commit -m "fix: keep dead sources when no replacement found — post-Stage-4 recovery handles supplementing"
```

---

### Task 6: End-to-end test

Generate a fresh article and verify sources are all alive with 3+ count.

**Files:** None (manual test)

- [ ] **Step 1: Generate a test article**

```bash
curl -s -X POST http://localhost:8000/api/v1/blog/articles \
  -H "Content-Type: application/json" \
  -d '{"keyword": "TENS Gerät gegen Rückenschmerzen", "language": "de", "word_count": 1200}'
```

- [ ] **Step 2: Wait for completion and validate**

Poll the article status until completed, then check:
1. Sources count >= 3
2. All source URLs return HTTP 200
3. All sources have descriptions (>= 10 chars)
4. Footnotes in body text match source count (no orphans)
5. No formal "Sie" in content (Du-Form)

```python
import json, re, httpx

# Load article from API response
# For each source: httpx.get(url).status_code == 200
# Count <sup> letters, compare with source count
# Grep for Sie-Form patterns
```

- [ ] **Step 3: Commit all remaining changes**

```bash
git add -A
git commit -m "test: verify reliable sources pipeline end-to-end"
```

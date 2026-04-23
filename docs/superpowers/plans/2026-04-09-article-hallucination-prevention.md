# Article Hallucination Prevention — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent recurring Gemini hallucinations in blog articles by controlling what data enters the prompt (category-scoped context) and catching leak-through with a post-generation safety net.

**Architecture:** Category detection maps keywords to product categories. The context builder filters products, specs, and sitemap URLs to only what's relevant. A slimmed-down safety net catches anything that leaks through Google Search grounding. No new dependencies or API calls — all changes are deterministic filtering and regex-based scrubbing.

**Tech Stack:** Python, regex, existing `product_catalog.json` data

**Spec:** `docs/superpowers/specs/2026-04-09-article-hallucination-prevention-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `blog/product_catalog.py` | Modify | Add `detect_article_category()`, `get_products_for_category()`, `format_product_specs()` |
| `blog/beurer_context.py` | Modify | Filter products/URLs by category in `get_beurer_company_context()` and `get_beurer_sitemap_urls()` |
| `blog/stage2/blog_writer.py` | Modify | Use structured product specs in `_format_company_context()`, tighten source quality in `_build_verified_sources()` |
| `blog/shared/models.py` | Modify | Remove `video_url` and `video_title` fields from `ArticleOutput` |
| `blog/stage2/prompts/user_prompt.txt` | Modify | Remove video_url/video_title from output spec and examples |
| `blog/stage2/prompts/system_instruction.txt` | Modify | Remove video URL instruction (field no longer exists) |
| `blog/stage2/stage_2.py` | Modify | Remove video URL validation code (field no longer exists) |
| `blog/article_service.py` | Modify | Rewrite `_post_pipeline_safety()` with full-scope safety net, pass keyword to context builder |
| `blog/stage_cleanup/cleanup.py` | Modify | Add unicode zero-width character stripping |

---

### Task 1: Category Detection

**Files:**
- Modify: `blog/product_catalog.py` (add after `_CATEGORY_GENERIC_NAMES` dict, ~line 28)

- [ ] **Step 1: Add `_CATEGORY_KEYWORDS` dict and `detect_article_category()` function**

Add after the `_CATEGORY_GENERIC_NAMES` dict (line 28) in `blog/product_catalog.py`:

```python
# Keyword-to-category mapping for article context scoping
_CATEGORY_KEYWORDS = {
    "menstrual": ["menstrual", "regel", "periode", "menstruation", "periodenschmerz"],
    "tens_ems": ["tens", "ems", "reizstrom", "elektroden", "schmerztherapie", "muskelstimulation"],
    "blood_pressure": ["blutdruck", "blutdruckmess", "oberarm", "handgelenk", "hypertonie", "blood pressure"],
    "infrarot": ["infrarot", "rotlicht", "wärmelampe", "infrared"],
}
# Priority order: menstrual > tens_ems > blood_pressure > infrarot > general
_CATEGORY_PRIORITY = ["menstrual", "tens_ems", "blood_pressure", "infrarot"]


def detect_article_category(keyword: str) -> str:
    """Detect article category from keyword for context scoping.

    Returns one of: 'tens_ems', 'blood_pressure', 'menstrual', 'infrarot', 'general'.
    Priority order handles ambiguous keywords (e.g. 'TENS bei Regelschmerzen' → 'menstrual').
    """
    kw_lower = keyword.lower()
    for category in _CATEGORY_PRIORITY:
        if any(term in kw_lower for term in _CATEGORY_KEYWORDS[category]):
            return category
    return "general"
```

- [ ] **Step 2: Verify detection works for known keywords**

Run in Python REPL or a quick script:
```bash
python -c "
import sys; sys.path.insert(0, 'blog')
from product_catalog import detect_article_category
tests = [
    ('TENS Gerät Vergleich', 'tens_ems'),
    ('Blutdruck richtig messen', 'blood_pressure'),
    ('TENS bei Regelschmerzen', 'menstrual'),
    ('Infrarotlampe Anwendung', 'infrarot'),
    ('Beurer Gesundheitsratgeber', 'general'),
    ('Reizstromgeräte Test', 'tens_ems'),
    ('Menstruationsschmerzen lindern', 'menstrual'),
    ('Handgelenk Blutdruckmessgerät', 'blood_pressure'),
]
for keyword, expected in tests:
    result = detect_article_category(keyword)
    status = 'OK' if result == expected else f'FAIL (got {result})'
    print(f'  {keyword:40s} → {result:15s} {status}')
"
```

Expected: All should print `OK`.

- [ ] **Step 3: Commit**

```bash
git add blog/product_catalog.py
git commit -m "feat: add detect_article_category() for context scoping"
```

---

### Task 2: Category-Scoped Product Filtering

**Files:**
- Modify: `blog/product_catalog.py` (add after `detect_article_category`, add `format_product_specs`)

- [ ] **Step 1: Add `get_products_for_category()` function**

Add after `detect_article_category()` in `blog/product_catalog.py`:

```python
def get_products_for_category(category: str, catalog: Optional['ProductCatalog'] = None) -> List['Product']:
    """Return only products relevant to the given article category.

    Args:
        category: One of 'tens_ems', 'blood_pressure', 'menstrual', 'infrarot', 'general'.
        catalog: Optional pre-loaded catalog. Loads from disk if not provided.

    Returns:
        Filtered list of Product objects.
    """
    if catalog is None:
        catalog = load_catalog()

    if category == "general":
        return list(catalog.products.values())

    products = []
    for p in catalog.products.values():
        if category == "tens_ems":
            # TENS/EMS devices, but NOT menstrual-only
            if p.type == "tens_ems" and p.usage_restriction != "menstrual_only":
                products.append(p)
        elif category == "blood_pressure":
            if p.category == "blood_pressure":
                products.append(p)
        elif category == "menstrual":
            # Menstrual-only devices PLUS general TENS (for comparison)
            if p.type == "tens_ems":
                products.append(p)
        elif category == "infrarot":
            if p.category == "infrarot":
                products.append(p)

    return products
```

- [ ] **Step 2: Add `format_product_specs()` function**

Add after `get_products_for_category()`:

```python
def format_product_specs(products: List['Product'], language: str = "de") -> str:
    """Format product list with specs for injection into Gemini prompt.

    Includes key specs (programs, channels, electrodes, connectivity) from
    catalog data so Gemini uses correct values instead of hallucinating.
    """
    if not products:
        return ""

    is_de = language.startswith("de")
    lines = []

    if is_de:
        lines.append("=== PRODUKTE FÜR DIESEN ARTIKEL (NUR diese verwenden, mit GENAU diesen Spezifikationen) ===")
    else:
        lines.append("=== PRODUCTS FOR THIS ARTICLE (use ONLY these, with EXACTLY these specs) ===")

    for p in sorted(products, key=lambda x: (x.priority or 99, x.sku)):
        parts = [p.sku]

        # Type info
        if p.type == "oberarm":
            parts.append("Oberarm" if is_de else "Upper arm")
        elif p.type == "handgelenk":
            parts.append("Handgelenk" if is_de else "Wrist")
        elif p.type == "tens_ems":
            funcs = [f.upper() for f in p.functions if f in ("tens", "ems", "massage")]
            if funcs:
                parts.append("/".join(funcs))
        elif p.type == "infrarotlampe":
            parts.append("Infrarotlampe" if is_de else "Infrared lamp")

        # Specs from catalog (programs, channels, electrodes)
        # These are stored as extra keys in the JSON, accessed via the raw catalog
        _raw = _load_raw_product(p.sku)
        if _raw:
            if "programs" in _raw:
                parts.append(f"{_raw['programs']} Programme" if is_de else f"{_raw['programs']} programs")
            if "channels" in _raw:
                parts.append(f"{_raw['channels']} Kanäle" if is_de else f"{_raw['channels']} channels")
            if "electrodes" in _raw:
                parts.append(f"{_raw['electrodes']} Elektroden" if is_de else f"{_raw['electrodes']} electrodes")

        # Heat
        if p.has_heat:
            parts.append("Wärmefunktion" if is_de else "Heat function")

        # Usage restriction
        if p.usage_restriction == "menstrual_only":
            parts.append("NUR für Menstruationsschmerzen" if is_de else "Menstrual pain ONLY")

        # Connectivity (always explicit)
        if p.app_compatible:
            parts.append("Bluetooth, HealthManager Pro kompatibel" if is_de else "Bluetooth, HealthManager Pro compatible")
        else:
            parts.append("kein Bluetooth, keine App" if is_de else "no Bluetooth, no app")

        lines.append(f"- {', '.join(parts)}")

    if is_de:
        lines.append("")
        lines.append("Erwähne KEINE Produkte, die nicht oben aufgelistet sind. Ändere KEINE dieser Spezifikationen.")
    else:
        lines.append("")
        lines.append("DO NOT mention any product not listed above. DO NOT modify these specifications.")

    return "\n".join(lines)


def _load_raw_product(sku: str) -> Optional[Dict[str, Any]]:
    """Load raw product data from JSON (includes extra fields like programs, channels)."""
    try:
        data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        return data.get("products", {}).get(sku)
    except Exception:
        return None
```

- [ ] **Step 3: Verify filtering and formatting**

```bash
python -c "
import sys; sys.path.insert(0, 'blog')
from product_catalog import detect_article_category, get_products_for_category, format_product_specs, load_catalog

catalog = load_catalog()

# TENS article should NOT include EM 50, EM 55, or any BM/BC/IL
tens_products = get_products_for_category('tens_ems', catalog)
tens_skus = {p.sku for p in tens_products}
assert 'EM 49' in tens_skus, 'EM 49 missing from tens_ems'
assert 'EM 59' in tens_skus, 'EM 59 missing from tens_ems'
assert 'EM 89' in tens_skus, 'EM 89 missing from tens_ems'
assert 'EM 50' not in tens_skus, 'EM 50 should not be in tens_ems'
assert 'EM 55' not in tens_skus, 'EM 55 should not be in tens_ems'
assert not any(s.startswith('BM') for s in tens_skus), 'BM products should not be in tens_ems'
print(f'tens_ems: {sorted(tens_skus)}')

# Blood pressure should NOT include EM or IL
bp_products = get_products_for_category('blood_pressure', catalog)
bp_skus = {p.sku for p in bp_products}
assert not any(s.startswith('EM') for s in bp_skus), 'EM products should not be in blood_pressure'
assert not any(s.startswith('IL') for s in bp_skus), 'IL products should not be in blood_pressure'
print(f'blood_pressure: {len(bp_skus)} products')

# Menstrual should include EM 50, EM 55, AND general TENS
menstrual_products = get_products_for_category('menstrual', catalog)
menstrual_skus = {p.sku for p in menstrual_products}
assert 'EM 50' in menstrual_skus, 'EM 50 missing from menstrual'
assert 'EM 55' in menstrual_skus, 'EM 55 missing from menstrual'
assert 'EM 89' in menstrual_skus, 'EM 89 missing from menstrual (general TENS should be included)'
print(f'menstrual: {sorted(menstrual_skus)}')

# Format check
print()
print(format_product_specs(tens_products, 'de'))
print()
print('All assertions passed.')
"
```

Expected: All assertions pass. Formatted output shows each product with specs, `kein Bluetooth, keine App` for all TENS devices.

- [ ] **Step 4: Commit**

```bash
git add blog/product_catalog.py
git commit -m "feat: add category-scoped product filtering and spec formatting"
```

---

### Task 3: Category-Scoped Context Builder

**Files:**
- Modify: `blog/beurer_context.py` — `get_beurer_company_context()` (line 318) and `get_beurer_sitemap_urls()` (line 199)

- [ ] **Step 1: Add `keyword` parameter to `get_beurer_company_context()`**

In `blog/beurer_context.py`, change the function signature and product list construction.

Change line 318:
```python
def get_beurer_company_context(language: str = "de") -> Dict[str, Any]:
```
to:
```python
def get_beurer_company_context(language: str = "de", keyword: Optional[str] = None) -> Dict[str, Any]:
```

Add `Optional` to the imports at the top if not already there (it's used elsewhere in the file via `typing`).

Then replace the product list construction (line 324):
```python
    products = list(BEURER_PRODUCT_CATALOG.keys())
```
with:
```python
    # Category-scoped products: only pass relevant products for this keyword
    if keyword:
        from blog.product_catalog import detect_article_category, get_products_for_category, format_product_specs
        _article_category = detect_article_category(keyword)
        _filtered_products = get_products_for_category(_article_category)
        products = [p.sku for p in _filtered_products]
        _product_specs_block = format_product_specs(_filtered_products, language)
    else:
        products = list(BEURER_PRODUCT_CATALOG.keys())
        _article_category = "general"
        _product_specs_block = None
```

Then at the end of the returned dict (before the `return` on line 380), add the product specs block so it's available to `_format_company_context()`:
```python
    context["_product_specs_block"] = _product_specs_block
    context["_article_category"] = _article_category
```

- [ ] **Step 2: Add `category` parameter to `get_beurer_sitemap_urls()`**

Change line 199:
```python
def get_beurer_sitemap_urls() -> Dict[str, List[str]]:
```
to:
```python
def get_beurer_sitemap_urls(category: str = "general") -> Dict[str, List[str]]:
```

After the existing `return` dict is built (before `return`), add category filtering:

```python
    urls = {
        "blog_urls": [ ... ],  # existing
        "product_urls": [ ... ],  # existing
        "resource_urls": [ ... ],  # existing
        "tool_urls": [],
        "service_urls": [ ... ],  # existing
    }

    # Category-scoped URL filtering
    if category in ("tens_ems", "menstrual"):
        # Remove HealthManager Pro URL (BP-only app)
        urls["resource_urls"] = [
            u for u in urls["resource_urls"]
            if "healthmanager-pro" not in u
        ]
        # Remove BP category URLs
        urls["product_urls"] = [
            u for u in urls["product_urls"]
            if "0010101" not in u and "0010102" not in u  # Oberarm, Handgelenk
        ]
    elif category == "blood_pressure":
        # Remove TENS/EMS/infrarot category URLs
        urls["product_urls"] = [
            u for u in urls["product_urls"]
            if "0010401" not in u and "0010402" not in u  # TENS, EMS
            and "0010302" not in u and "00201" not in u  # Infrarot, Wärme
        ]

    return urls
```

- [ ] **Step 3: Update callers in `article_service.py`**

In `blog/article_service.py`, update the two calls to `get_beurer_company_context()`:

Line 527 — change:
```python
        company_context = get_beurer_company_context(language)
```
to:
```python
        company_context = get_beurer_company_context(language, keyword=keyword)
```

Line 868 — change:
```python
        company_context = get_beurer_company_context(language)
```
to:
```python
        company_context = get_beurer_company_context(language, keyword=keyword)
```

Update the call to `get_beurer_sitemap_urls()` at line 326 — change:
```python
        sitemap = get_beurer_sitemap_urls()
```
to:
```python
        _category = company_context.get("_article_category", "general")
        sitemap = get_beurer_sitemap_urls(category=_category)
```

- [ ] **Step 4: Verify context scoping**

```bash
python -c "
import sys; sys.path.insert(0, '.')
from blog.beurer_context import get_beurer_company_context, get_beurer_sitemap_urls

# TENS article should NOT have EM 50, EM 55, or BM products
ctx = get_beurer_company_context('de', keyword='TENS Gerät Vergleich')
products = ctx.get('products', [])
print(f'TENS products: {products}')
assert 'EM 50' not in products, 'EM 50 leaked into TENS context'
assert 'EM 55' not in products, 'EM 55 leaked into TENS context'
assert not any(p.startswith('BM') for p in products), 'BM products leaked into TENS context'
print(f'Category: {ctx.get(\"_article_category\")}')
print(f'Has specs block: {bool(ctx.get(\"_product_specs_block\"))}')

# Sitemap for TENS should NOT have HealthManager Pro
sitemap = get_beurer_sitemap_urls(category='tens_ems')
all_urls = ' '.join(str(v) for v in sitemap.values())
assert 'healthmanager-pro' not in all_urls, 'HealthManager Pro URL leaked into TENS sitemap'
print(f'TENS sitemap URLs: no HealthManager Pro - OK')

print('All assertions passed.')
"
```

- [ ] **Step 5: Commit**

```bash
git add blog/beurer_context.py blog/article_service.py
git commit -m "feat: category-scoped context and sitemap filtering"
```

---

### Task 4: Structured Product Specs in Prompt

**Files:**
- Modify: `blog/stage2/blog_writer.py` — `_format_company_context()` (~line 493)

- [ ] **Step 1: Replace flat product list with structured specs**

In `blog/stage2/blog_writer.py`, find the product formatting block in `_format_company_context()` (lines 524-529):

```python
    products = context.get('products', [])
    if products:
        if isinstance(products, list):
            lines.append(f"Products/Services: {', '.join(str(p) for p in products)}")
        else:
            lines.append(f"Products/Services: {products}")
```

Replace with:

```python
    # Use structured product specs if available (category-scoped)
    product_specs_block = context.get('_product_specs_block')
    if product_specs_block:
        lines.append("")
        lines.append(product_specs_block)
    else:
        # Fallback: flat product list (non-Beurer or no keyword context)
        products = context.get('products', [])
        if products:
            if isinstance(products, list):
                lines.append(f"Products/Services: {', '.join(str(p) for p in products)}")
            else:
                lines.append(f"Products/Services: {products}")
```

- [ ] **Step 2: Verify the prompt contains structured specs**

```bash
python -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'blog/stage2')
from blog.beurer_context import get_beurer_company_context
from blog_writer import _format_company_context

ctx = get_beurer_company_context('de', keyword='TENS Gerät Vergleich')
formatted = _format_company_context(ctx, keyword='TENS Gerät Vergleich', language='de')

# Should contain structured specs, not flat list
assert 'PRODUKTE FÜR DIESEN ARTIKEL' in formatted, 'Missing structured specs header'
assert 'kein Bluetooth' in formatted, 'Missing connectivity info'
assert 'EM 50' not in formatted, 'EM 50 leaked into TENS prompt'
print('Structured specs present in prompt - OK')
# Print a snippet
for line in formatted.split('\n'):
    if 'EM' in line or 'PRODUKTE' in line or 'Erwähne' in line:
        print(f'  {line}')
"
```

- [ ] **Step 3: Commit**

```bash
git add blog/stage2/blog_writer.py
git commit -m "feat: inject structured product specs into Gemini prompt"
```

---

### Task 5: Remove Video URL from Schema

**Files:**
- Modify: `blog/shared/models.py` (~line 266-267)
- Modify: `blog/stage2/prompts/user_prompt.txt` (lines 27, 96-97)
- Modify: `blog/stage2/prompts/system_instruction.txt` (line 9)
- Modify: `blog/stage2/stage_2.py` (~lines 205-210)

- [ ] **Step 1: Remove `video_url` and `video_title` from `ArticleOutput` model**

In `blog/shared/models.py`, remove lines 266-267:

```python
    video_url: Optional[str] = Field(default="", description="YouTube video URL (prefer company's own channel)")
    video_title: Optional[str] = Field(default="", description="Video title for embed")
```

- [ ] **Step 2: Remove video URL from user prompt template**

In `blog/stage2/prompts/user_prompt.txt`, remove line 27:
```
- video_url + video_title: ONLY if you find a REAL YouTube video via search - prioritize company's own channel, leave EMPTY if unsure or none found
```

And remove lines 96-97 from the JSON example:
```
  "video_url": "https://youtube.com/watch?v=... (prefer company channel)",
  "video_title": "Video title for embed",
```

- [ ] **Step 3: Remove video URL instruction from system instruction**

In `blog/stage2/prompts/system_instruction.txt`, remove line 9:
```
- NEVER invent YouTube video URLs - only use real URLs you found via Google Search. If you cannot find a real video, leave video_url empty.
```

- [ ] **Step 4: Remove video URL validation from `stage_2.py`**

In `blog/stage2/stage_2.py`, remove the video URL validation block (~lines 205-210):

```python
    # Validate video_url - clear if not a valid YouTube URL
    if article.video_url:
        if not YOUTUBE_URL_PATTERN.match(article.video_url):
            logger.info(f"  Clearing invalid video_url: {article.video_url[:50]}...")
            article.video_url = ""
            article.video_title = ""
```

Also remove the `YOUTUBE_URL_PATTERN` constant if it's only used for this check (grep to confirm).

- [ ] **Step 5: Remove video URL stripping from `_post_pipeline_safety()`**

In `blog/article_service.py`, remove the video URL section from `_post_pipeline_safety()` (the rickroll/fake video check, lines ~98-104):

```python
    # 1. Strip rickroll, known-fake, and pattern-fake video URLs
    video_url = article.get("video_url", "") or ""
    if (any(vid_id in video_url for vid_id in _RICKROLL_IDS)
            or _FAKE_VIDEO_RE.search(video_url)):
        logger.info(f"Safety: stripped fabricated video URL")
        article["video_url"] = ""
        article["video_title"] = ""
```

Also remove `_RICKROLL_IDS` and `_FAKE_VIDEO_RE` constants (~lines 79-81) since they're now dead code.

- [ ] **Step 6: Verify schema no longer includes video fields**

```bash
python -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'blog')
from blog.shared.models import ArticleOutput
fields = ArticleOutput.model_fields
assert 'video_url' not in fields, 'video_url still in schema'
assert 'video_title' not in fields, 'video_title still in schema'
print('video_url and video_title removed from ArticleOutput - OK')
"
```

- [ ] **Step 7: Commit**

```bash
git add blog/shared/models.py blog/stage2/prompts/user_prompt.txt blog/stage2/prompts/system_instruction.txt blog/stage2/stage_2.py blog/article_service.py
git commit -m "feat: remove video_url from article schema to prevent fabricated URLs"
```

---

### Task 6: Source Quality Gate

**Files:**
- Modify: `blog/stage2/blog_writer.py` — `_build_verified_sources()` (~line 179)

- [ ] **Step 1: Add blocked domain list and generic description pattern**

Near the top of `blog/stage2/blog_writer.py` (after the existing imports/constants), add:

```python
# Blocked source domains — these are user-generated content, not professional sources
_BLOCKED_SOURCE_DOMAINS = [
    "reddit.com", "gutefrage.net", "facebook.com", "tiktok.com",
    "instagram.com", "twitter.com", "x.com", "youtube.com",
]

# Pattern matching the generic fallback description template
_GENERIC_DESC_RE = re.compile(r"^Source:\s+.+\s+—\s+relevant to\s+", re.IGNORECASE)
```

Add `import re` at the top if not already imported.

- [ ] **Step 2: Add source filtering in `_build_verified_sources()`**

After the URL verification step (line ~243, after `verified = [c for c in candidates if c["url"] in alive_set]`), add domain filtering:

```python
    # Filter out blocked domains (user-generated content, social media)
    pre_filter_count = len(verified)
    verified = [
        c for c in verified
        if not any(domain in c["url"].lower() for domain in _BLOCKED_SOURCE_DOMAINS)
    ]
    if len(verified) < pre_filter_count:
        logger.info(f"Source filtering: removed {pre_filter_count - len(verified)} blocked-domain sources")
```

- [ ] **Step 3: Add description quality gate after enrichment**

After the enrichment block (line ~276, after the `for src in needs_enrichment` fallback loop), add a quality gate:

```python
    # Quality gate: drop sources with generic/placeholder descriptions
    pre_quality_count = len(verified)
    verified = [
        c for c in verified
        if not _GENERIC_DESC_RE.match(c.get("description", ""))
        and len(c.get("description", "")) >= 30
    ]
    if len(verified) < pre_quality_count:
        logger.info(f"Source quality gate: dropped {pre_quality_count - len(verified)} sources with generic descriptions")
```

- [ ] **Step 4: Update the fallback description in enrichment to not use the generic template**

In the enrichment fallback (lines ~271 and ~276), change the generic template:

Replace both occurrences of:
```python
                    src["description"] = f"Source: {src.get('title', 'Reference')} — relevant to {keyword}"
```
with:
```python
                    # Don't set a generic description — source will be dropped by quality gate
                    src["description"] = ""
```

This ensures sources that fail enrichment are dropped rather than kept with a placeholder.

- [ ] **Step 5: Also apply the domain filter and quality gate in the supplementary source loop**

In the supplementary source loop (~line 329-331), after checking `if not c.get("description")`, change:

```python
                        if not c.get("description") or len(c.get("description", "")) < 10:
                            c["description"] = f"Source: {c.get('title', 'Reference')} — relevant to {keyword}"
```

to:

```python
                        if not c.get("description") or len(c.get("description", "")) < 30:
                            continue  # Skip sources without real descriptions
```

And add domain filtering before appending supplementary sources — wrap the append in a domain check:

```python
                    if any(domain in c["url"].lower() for domain in _BLOCKED_SOURCE_DOMAINS):
                        continue
```

- [ ] **Step 6: Commit**

```bash
git add blog/stage2/blog_writer.py
git commit -m "feat: add source quality gate — drop generic descriptions and blocked domains"
```

---

### Task 7: Unicode Cleanup in Stage Cleanup

**Files:**
- Modify: `blog/stage_cleanup/cleanup.py` — `_clean_html()` (~line 326)

- [ ] **Step 1: Add zero-width character stripping to `_clean_html()`**

In `blog/stage_cleanup/cleanup.py`, in the `_clean_html()` function, add after the control character removal (line ~381, after step 12):

```python
    # 13. Strip zero-width and invisible Unicode characters
    # U+200B zero-width space, U+FEFF BOM, U+200C zero-width non-joiner,
    # U+200D zero-width joiner, U+2060 word joiner, U+FFFE non-character
    cleaned = re.sub(r'[\u200b\ufeff\u200c\u200d\u2060\ufffe]', '', cleaned)
```

Renumber the existing step 13 (normalize whitespace) to step 14.

- [ ] **Step 2: Verify cleanup strips garbage characters**

```bash
python -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'blog/stage_cleanup')
from cleanup import _clean_html

# Test: EM 89 Heat with BOM garbage (from audit issue 7)
dirty = 'EM 89 Heat – \ufeff1\ufeff\ufeff2\ufeffDigital TENS/EMS'
cleaned = _clean_html(dirty)
assert '\ufeff' not in cleaned, 'BOM not stripped'
assert 'EM 89 Heat' in cleaned, 'Content lost'
print(f'Input:  {repr(dirty)}')
print(f'Output: {repr(cleaned)}')
print('Zero-width cleanup working - OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add blog/stage_cleanup/cleanup.py
git commit -m "feat: strip zero-width unicode characters in HTML cleanup"
```

---

### Task 8: Rewrite Post-Pipeline Safety Net

**Files:**
- Modify: `blog/article_service.py` — `_post_pipeline_safety()` (~line 84)

- [ ] **Step 1: Rewrite `_post_pipeline_safety()` with full scope**

Replace the entire `_post_pipeline_safety()` function (lines 84-158) with:

```python
# Known typo corrections
_TYPO_FIXES = {
    "letzen": "letzten",
}


def _post_pipeline_safety(article: Dict[str, Any], keyword: str) -> Dict[str, Any]:
    """Catch hallucinations that leak through despite category-scoped context.

    Handles issues that can't be fully prevented upstream:
    - Unicode garbage from grounding (zero-width chars)
    - EM 89 wrong specs in prose (grounding can override structured injection)
    - Unknown product SKUs not in the filtered catalog
    - HealthManager Pro / app claims that leak via grounding in TENS articles
    - EM 50/55 mentions that leak via grounding in non-menstrual articles
    - Known typos
    """
    from blog.product_catalog import detect_article_category, get_products_for_category

    category = detect_article_category(keyword)
    allowed_skus = {p.sku for p in get_products_for_category(category)}

    warnings = []

    # Collect all text fields to scan
    text_fields = ["Intro", "Direct_Answer", "Headline", "Teaser", "Meta_Title", "Meta_Description"]
    for i in range(1, 10):
        text_fields.append(f"section_{i:02d}_title")
        text_fields.append(f"section_{i:02d}_content")
    for i in range(1, 4):
        text_fields.append(f"key_takeaway_{i:02d}")
    for i in range(1, 5):
        text_fields.append(f"paa_{i:02d}_question")
        text_fields.append(f"paa_{i:02d}_answer")
    for i in range(1, 7):
        text_fields.append(f"faq_{i:02d}_question")
        text_fields.append(f"faq_{i:02d}_answer")

    for field_name in text_fields:
        content = article.get(field_name)
        if not isinstance(content, str) or not content:
            continue

        original = content

        # 1. Unicode cleanup: strip zero-width chars
        content = re.sub(r'[\u200b\ufeff\u200c\u200d\u2060\ufffe]', '', content)

        # 2. EM 89 spec corrections in prose
        if "EM 89" in content:
            content = re.sub(r'[Üü]ber 70 Programme', '64 Programme', content)
            content = re.sub(r'70\+?\s*Programme', '64 Programme', content)
            content = re.sub(r'2 (getrennt regelbare?\s*)?Kan[äa]le', '4 Kanäle', content)

        # 3. Typo fixes
        for typo, fix in _TYPO_FIXES.items():
            if typo in content:
                content = content.replace(typo, fix)

        if content != original:
            article[field_name] = content

    # 4. EM 89 spec corrections in tables (existing logic, expanded)
    tables = article.get("tables", [])
    if isinstance(tables, list):
        for table in tables:
            if not isinstance(table, dict):
                continue
            rows = table.get("rows", [])
            for row in rows:
                if not isinstance(row, list):
                    continue
                row_text = " ".join(str(c) for c in row)
                if "EM 89" in row_text:
                    for i, cell in enumerate(row):
                        if not isinstance(cell, str):
                            continue
                        cell = re.sub(r'[Üü]ber 70 Programme', '64 Programme', cell)
                        cell = re.sub(r'70\+?\s*Programme', '64 Programme', cell)
                        cell = re.sub(r'2 (getrennt regelbare?\s*)?Kan[äa]le', '4 Kanäle', cell)
                        row[i] = cell

    # 5. Category-specific leak-through checks

    is_tens = category == "tens_ems"
    is_menstrual = category == "menstrual"

    if is_tens:
        # 5a. HealthManager Pro / app claims in TENS articles
        _app_claims = ["App-Anbindung", "App-Support", "HealthManager Pro",
                       "Bluetooth / App", "Bluetooth/App"]

        # Tables: remove false claims from cells
        for table in (article.get("tables") or []):
            if not isinstance(table, dict):
                continue
            for row in table.get("rows", []):
                if not isinstance(row, list):
                    continue
                for i, cell in enumerate(row):
                    if not isinstance(cell, str):
                        continue
                    for claim in _app_claims:
                        if claim in cell:
                            row[i] = cell.replace(claim, "").strip().strip(",").strip()
                            logger.info(f"Safety: removed '{claim}' from TENS table cell")
                            cell = row[i]

        # Prose: flag as warning (don't auto-remove from flowing text)
        for field_name in text_fields:
            content = article.get(field_name)
            if not isinstance(content, str):
                continue
            for claim in _app_claims:
                if claim in content:
                    warnings.append(f"⚠️ '{claim}' found in {field_name} (TENS article)")

        # List items: remove <li> containing app claims
        for field_name in text_fields:
            content = article.get(field_name)
            if not isinstance(content, str) or "<li>" not in content:
                continue
            for claim in _app_claims:
                if claim in content:
                    content = re.sub(
                        rf'<li>[^<]*{re.escape(claim)}[^<]*</li>',
                        '', content, flags=re.IGNORECASE
                    )
            article[field_name] = content

    if is_tens and not is_menstrual:
        # 5b. EM 50/EM 55 in non-menstrual TENS articles
        _menstrual_skus = ["EM 50", "EM 55"]

        # Tables: remove rows containing EM 50/55
        for table in (article.get("tables") or []):
            if not isinstance(table, dict):
                continue
            original_rows = table.get("rows", [])
            filtered_rows = []
            for row in original_rows:
                if not isinstance(row, list):
                    filtered_rows.append(row)
                    continue
                row_text = " ".join(str(c) for c in row)
                if any(sku in row_text for sku in _menstrual_skus):
                    logger.info(f"Safety: removed table row containing menstrual device in TENS article")
                    continue
                filtered_rows.append(row)
            table["rows"] = filtered_rows

        # Images: clear EM 50/55 product images
        for slot in ["image_02", "image_03"]:
            alt = (article.get(f"{slot}_alt_text") or "").lower()
            if any(sku.lower().replace(" ", "") in alt.replace(" ", "") for sku in _menstrual_skus):
                logger.info(f"Safety: cleared {slot} (menstrual device in TENS article)")
                article[f"{slot}_url"] = ""
                article[f"{slot}_alt_text"] = ""

        # List items: remove <li> containing EM 50/55
        for field_name in text_fields:
            content = article.get(field_name)
            if not isinstance(content, str) or "<li>" not in content:
                continue
            for sku in _menstrual_skus:
                if sku in content:
                    content = re.sub(
                        rf'<li>[^<]*{re.escape(sku)}[^<]*</li>',
                        '', content, flags=re.IGNORECASE
                    )
            article[field_name] = content

        # Prose: flag as warning
        for field_name in text_fields:
            content = article.get(field_name)
            if not isinstance(content, str):
                continue
            for sku in _menstrual_skus:
                if sku in content:
                    warnings.append(f"⚠️ '{sku}' found in {field_name} (non-menstrual TENS article)")

    # 6. Unknown product SKU check
    all_text = json.dumps(article, ensure_ascii=False)
    for match in re.finditer(r'\b(BM|BC|EM|IL)\s?(\d{2,3})\b', all_text):
        sku = f"{match.group(1)} {match.group(2)}"
        if sku not in allowed_skus:
            warnings.append(f"⚠️ Unknown product '{sku}' found (not in {category} catalog)")

    # Log warnings
    for w in warnings:
        logger.warning(f"Post-pipeline safety: {w}")

    return article
```

- [ ] **Step 2: Also remove the old constants that are now dead code**

Remove `_RICKROLL_IDS` and `_FAKE_VIDEO_RE` (lines ~79-81) from `article_service.py` since video URL handling was removed in Task 5.

- [ ] **Step 3: Verify safety net works**

```bash
python -c "
import sys, json; sys.path.insert(0, '.')
from blog.article_service import _post_pipeline_safety

# Test 1: EM 89 spec correction in prose
article = {'section_01_content': 'Das EM 89 hat über 70 Programme und 2 Kanäle.'}
result = _post_pipeline_safety(article, 'TENS Gerät Vergleich')
assert '64 Programme' in result['section_01_content'], 'EM 89 programs not corrected'
assert '4 Kanäle' in result['section_01_content'], 'EM 89 channels not corrected'
print('Test 1 (EM 89 specs): OK')

# Test 2: Unicode cleanup
article = {'Intro': 'EM 89 Heat – \ufeff1\ufeff\ufeff2\ufeffDigital TENS/EMS'}
result = _post_pipeline_safety(article, 'TENS Gerät Vergleich')
assert '\ufeff' not in result['Intro'], 'BOM not stripped'
print('Test 2 (Unicode): OK')

# Test 3: Typo fix
article = {'section_01_content': 'der letzen 7 Tage'}
result = _post_pipeline_safety(article, 'Blutdruck messen')
assert 'letzten' in result['section_01_content'], 'Typo not fixed'
print('Test 3 (Typo): OK')

# Test 4: EM 50 table row removal in TENS article
article = {'tables': [{'rows': [['EM 49', '64 Programme'], ['EM 50', '15 Programme'], ['EM 89', '64 Programme']]}]}
result = _post_pipeline_safety(article, 'TENS Gerät Vergleich')
row_texts = [' '.join(r) for r in result['tables'][0]['rows']]
assert not any('EM 50' in t for t in row_texts), 'EM 50 row not removed'
assert any('EM 49' in t for t in row_texts), 'EM 49 row should remain'
print('Test 4 (EM 50 table removal): OK')

print('All safety net tests passed.')
"
```

- [ ] **Step 4: Commit**

```bash
git add blog/article_service.py
git commit -m "feat: rewrite _post_pipeline_safety() with full-scope safety net"
```

---

### Task 9: Update Fallback User Prompt Source Count

**Files:**
- Modify: `blog/stage2/blog_writer.py` — `_FALLBACK_USER_PROMPT` (~line 101)

- [ ] **Step 1: Fix source count in fallback prompt**

In `blog/stage2/blog_writer.py`, the `_FALLBACK_USER_PROMPT` (line ~124) says "3-5 sources". Change:

```python
Sources (list of {{title, url, description}} - MANDATORY, 3-5 sources with descriptions), Search_Queries.
```

to:

```python
Sources (list of {{title, url, description}} - MANDATORY, 2-3 sources with descriptions), Search_Queries.
```

- [ ] **Step 2: Commit**

```bash
git add blog/stage2/blog_writer.py
git commit -m "fix: align fallback prompt source count to 2-3 (matches system instruction)"
```

---

### Task 10: Integration Verification

- [ ] **Step 1: End-to-end dry run**

Run a quick check that the full call chain works without errors:

```bash
python -c "
import sys; sys.path.insert(0, '.')
from blog.beurer_context import get_beurer_company_context, get_beurer_sitemap_urls
from blog.product_catalog import detect_article_category, get_products_for_category, format_product_specs

keywords = [
    'TENS Gerät Vergleich',
    'Blutdruck richtig messen',
    'TENS bei Regelschmerzen',
    'Infrarotlampe Rückenschmerzen',
    'Beurer Gesundheitsratgeber',
]

for kw in keywords:
    cat = detect_article_category(kw)
    products = get_products_for_category(cat)
    ctx = get_beurer_company_context('de', keyword=kw)
    sitemap = get_beurer_sitemap_urls(category=cat)
    specs = format_product_specs(products, 'de')

    print(f'{kw:40s} → {cat:15s} | {len(products):2d} products | specs: {len(specs):4d} chars | sitemap URLs: {sum(len(v) for v in sitemap.values())}')

    # Verify no cross-contamination
    product_skus = {p.sku for p in products}
    if cat == 'tens_ems':
        assert 'EM 50' not in product_skus, f'EM 50 in tens_ems for: {kw}'
        assert not any(s.startswith('BM') for s in product_skus), f'BM in tens_ems for: {kw}'
    elif cat == 'blood_pressure':
        assert not any(s.startswith('EM') for s in product_skus), f'EM in blood_pressure for: {kw}'

print()
print('All integration checks passed.')
"
```

- [ ] **Step 2: Final commit (if any fixups needed)**

Only if Step 1 revealed issues that needed fixing:

```bash
git add -u
git commit -m "fix: integration fixups from end-to-end verification"
```

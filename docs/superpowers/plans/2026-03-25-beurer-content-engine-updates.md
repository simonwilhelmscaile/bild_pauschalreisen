# Beurer Content Engine Updates — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add product catalog validation, fix content engine issues (footnotes, labels, grammar, linking, URL validation, repetition), and fix dashboard inline edit reliability — all before March 28 article regeneration.

**Architecture:** Three independent workstreams: (A) Product catalog + validation gate as new pipeline stage, (B) Content engine fixes across existing stages, (C) Dashboard inline edit fixes. A and B must land before March 28; C has no deadline.

**Tech Stack:** Python 3.11, FastAPI, Gemini API, Pydantic, Next.js 15 (API-only dashboard), httpx

**Spec:** `docs/superpowers/specs/2026-03-25-beurer-content-engine-updates-design.md`

**Important context:** This project has NO test framework (no pytest, no ruff). Tests are manual scripts. "Run test" steps use inline Python scripts or manual verification. The blog pipeline lives in `blog/` with stages as subdirectories. The dashboard is API-only Next.js in `dashboard/`.

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `blog/product_catalog.json` | Product catalog data (33 products, 5 categories, URLs null until confirmed) |
| `blog/product_catalog.py` | Catalog loader, product validation, SKU matching — PIM-ready interface |

### Modified Files
| File | Changes |
|------|---------|
| `blog/shared/html_renderer.py` | Lettered footnotes (line 918), label rename (line 35) |
| `dashboard/lib/html-renderer.ts` | Lettered footnotes, label rename (mirror Python changes) |
| `blog/stage_cleanup/cleanup.py` | Whitespace normalization function, footnote count warning |
| `blog/stage2/prompts/system_instruction.txt` | Lettered footnote format, dedup instruction |
| `blog/stage4/stage4_models.py` | New `REDIRECTED_TO_HOMEPAGE` enum value |
| `blog/stage4/http_checker.py` | Homepage redirect detection in `_do_check()` |
| `blog/stage4/stage_4.py` | Handle new homepage redirect status |
| `blog/stage5/stage5_models.py` | New `sitemap_category_urls` field |
| `blog/stage5/stage_5.py` | Blocklist in `_build_link_pool()`, category emphasis in prompt |
| `blog/beurer_context.py` | Filter App Welt/Produktberater from `get_beurer_sitemap_urls()` |
| `blog/pipeline.py` | Wire Stage 5.5, pass catalog category URLs to Stage 5 |
| `blog/article_service.py` | Wire Stage 5.5 in `_run_stages_4_5_cleanup()`, catalog URLs to Stage 5, URL-edit detection |

---

## Task 1: Product Catalog JSON + Loader Module

**Files:**
- Create: `blog/product_catalog.json`
- Create: `blog/product_catalog.py`

- [ ] **Step 1: Create the product catalog JSON**

Create `blog/product_catalog.json` with all 33 products from Anika's Excel. URLs are `null` until Beurer confirms working links.

```json
{
  "products": {
    "BC 21": {"url": null, "priority": null, "category": "blood_pressure", "type": "handgelenk"},
    "BC 27": {"url": null, "priority": 2, "category": "blood_pressure", "type": "handgelenk"},
    "BC 28": {"url": null, "priority": null, "category": "blood_pressure", "type": "handgelenk"},
    "BC 44": {"url": null, "priority": null, "category": "blood_pressure", "type": "handgelenk"},
    "BC 51": {"url": null, "priority": null, "category": "blood_pressure", "type": "handgelenk"},
    "BC 54": {"url": null, "priority": null, "category": "blood_pressure", "type": "handgelenk"},
    "BC 87": {"url": null, "priority": null, "category": "blood_pressure", "type": "handgelenk"},
    "BM 25": {"url": null, "priority": 1, "category": "blood_pressure", "type": "oberarm"},
    "BM 27": {"url": null, "priority": 1, "category": "blood_pressure", "type": "oberarm"},
    "BM 28": {"url": null, "priority": null, "category": "blood_pressure", "type": "oberarm"},
    "BM 38": {"url": null, "priority": null, "category": "blood_pressure", "type": "oberarm"},
    "BM 40": {"url": null, "priority": null, "category": "blood_pressure", "type": "oberarm"},
    "BM 45": {"url": null, "priority": null, "category": "blood_pressure", "type": "oberarm"},
    "BM 48": {"url": null, "priority": null, "category": "blood_pressure", "type": "oberarm"},
    "BM 49": {"url": null, "priority": null, "category": "blood_pressure", "type": "oberarm"},
    "BM 51": {"url": null, "priority": null, "category": "blood_pressure", "type": "oberarm"},
    "BM 53": {"url": null, "priority": 2, "category": "blood_pressure", "type": "oberarm"},
    "BM 54": {"url": null, "priority": 3, "category": "blood_pressure", "type": "oberarm"},
    "BM 58": {"url": null, "priority": null, "category": "blood_pressure", "type": "oberarm"},
    "BM 59": {"url": null, "priority": 3, "category": "blood_pressure", "type": "oberarm"},
    "BM 64": {"url": null, "priority": 2, "category": "blood_pressure", "type": "oberarm"},
    "BM 81": {"url": null, "priority": 1, "category": "blood_pressure", "type": "oberarm"},
    "BM 96": {"url": null, "priority": 3, "category": "blood_pressure", "type": "oberarm"},
    "EM 49": {"url": null, "priority": null, "category": "pain_tens", "type": "tens_ems"},
    "EM 50": {"url": null, "priority": 1, "category": "pain_tens", "type": "tens_ems"},
    "EM 55": {"url": null, "priority": 1, "category": "pain_tens", "type": "tens_ems"},
    "EM 59": {"url": null, "priority": 1, "category": "pain_tens", "type": "tens_ems"},
    "EM 89": {"url": null, "priority": 1, "category": "pain_tens", "type": "tens_ems"},
    "IL 11": {"url": null, "priority": null, "category": "infrarot", "type": "infrarotlampe"},
    "IL 21": {"url": null, "priority": null, "category": "infrarot", "type": "infrarotlampe"},
    "IL 35": {"url": null, "priority": null, "category": "infrarot", "type": "infrarotlampe"},
    "IL 50": {"url": null, "priority": 1, "category": "infrarot", "type": "infrarotlampe"},
    "IL 60": {"url": null, "priority": 1, "category": "infrarot", "type": "infrarotlampe"}
  },
  "categories": {
    "blutdruckmessgeraete": null,
    "oberarm": null,
    "handgelenk": null,
    "tens": null,
    "infrarotlampen": null
  },
  "meta": {
    "source": "excel",
    "updated": "2026-03-25",
    "note": "URLs pending confirmation from Beurer — populate once confirmed"
  }
}
```

- [ ] **Step 2: Create the catalog loader module**

Create `blog/product_catalog.py`:

```python
"""
Beurer product catalog for blog article validation.

Loads product/category data from JSON (PIM-ready: swap loader for API later).
Validates product mentions in article HTML against the catalog.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).parent / "product_catalog.json"

# Only match known Beurer prefixes to avoid false positives (e.g., "EU 27")
_PRODUCT_PATTERN = re.compile(r'\b(BM|BC|EM|IL)\s?(\d{2,3})\b')

# Category-level generic names for fallback replacement
_CATEGORY_GENERIC_NAMES = {
    ("blood_pressure", "oberarm"): "Beurer Oberarm-Blutdruckmessgeraet",
    ("blood_pressure", "handgelenk"): "Beurer Handgelenk-Blutdruckmessgeraet",
    ("pain_tens", "tens_ems"): "Beurer TENS/EMS-Geraet",
    ("infrarot", "infrarotlampe"): "Beurer Infrarotlampe",
}


@dataclass
class Product:
    sku: str
    url: Optional[str]
    priority: Optional[int]
    category: str
    type: str


@dataclass
class ValidationIssue:
    sku: str
    replacement_sku: Optional[str]
    replacement_text: Optional[str]
    reason: str


@dataclass
class ValidationResult:
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    products_found: List[str] = field(default_factory=list)


@dataclass
class ProductCatalog:
    products: Dict[str, Product]
    categories: Dict[str, Optional[str]]
    meta: Dict[str, str]

    def get_product_url(self, sku: str) -> Optional[str]:
        """Return webshop URL for a product SKU, or None if not populated."""
        product = self.products.get(sku)
        return product.url if product else None

    def get_priority_products(self, max_priority: int = 1) -> List[Product]:
        """Return products at or above the given priority level (1 = highest)."""
        return [
            p for p in self.products.values()
            if p.priority is not None and p.priority <= max_priority
        ]

    def get_category_urls(self) -> Dict[str, str]:
        """Return category URLs that are non-null."""
        return {k: v for k, v in self.categories.items() if v is not None}

    def get_product_urls(self) -> Dict[str, str]:
        """Return product SKU -> URL for products with non-null URLs."""
        return {sku: p.url for sku, p in self.products.items() if p.url is not None}


def load_catalog(path: Optional[Path] = None) -> ProductCatalog:
    """Load product catalog from JSON file.

    Args:
        path: Override path to catalog JSON. Defaults to blog/product_catalog.json.

    Returns:
        ProductCatalog with all products and categories.
    """
    catalog_path = path or _CATALOG_PATH
    data = json.loads(catalog_path.read_text(encoding="utf-8"))

    products = {}
    for sku, info in data.get("products", {}).items():
        # Normalize SKU: ensure space between prefix and number
        normalized = _normalize_sku(sku)
        products[normalized] = Product(
            sku=normalized,
            url=info.get("url"),
            priority=info.get("priority"),
            category=info.get("category", ""),
            type=info.get("type", ""),
        )

    categories = data.get("categories", {})
    meta = data.get("meta", {})

    logger.info(f"Loaded product catalog: {len(products)} products, {len(categories)} categories")
    return ProductCatalog(products=products, categories=categories, meta=meta)


def _normalize_sku(sku: str) -> str:
    """Normalize SKU to 'XX NN' format (prefix space number)."""
    m = _PRODUCT_PATTERN.search(sku)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return sku.strip()


def validate_product_mentions(html: str, catalog: ProductCatalog) -> ValidationResult:
    """Scan HTML for Beurer product mentions and validate against catalog.

    Args:
        html: Article HTML content.
        catalog: Loaded product catalog.

    Returns:
        ValidationResult with issues for any products not in catalog.
    """
    result = ValidationResult(valid=True)

    for match in _PRODUCT_PATTERN.finditer(html):
        sku = f"{match.group(1)} {match.group(2)}"
        result.products_found.append(sku)

        if sku not in catalog.products:
            # Find replacement: highest-priority product in same category+type
            replacement = _find_replacement(sku, catalog)
            result.valid = False
            result.issues.append(ValidationIssue(
                sku=sku,
                replacement_sku=replacement.sku if replacement else None,
                replacement_text=replacement.sku if replacement else _get_generic_name(sku),
                reason=f"Product {sku} not in German webshop catalog",
            ))

    return result


def _find_replacement(sku: str, catalog: ProductCatalog) -> Optional[Product]:
    """Find the best replacement product for an invalid SKU.

    Heuristic: same category + type, highest priority (lowest number).
    """
    # Guess category from prefix
    prefix = sku.split()[0] if " " in sku else sku[:2]
    prefix_category = {
        "BM": ("blood_pressure", "oberarm"),
        "BC": ("blood_pressure", "handgelenk"),
        "EM": ("pain_tens", "tens_ems"),
        "IL": ("infrarot", "infrarotlampe"),
    }.get(prefix)

    if not prefix_category:
        return None

    cat, typ = prefix_category
    candidates = [
        p for p in catalog.products.values()
        if p.category == cat and p.type == typ and p.priority is not None
    ]
    if not candidates:
        # Fallback: same category, any type
        candidates = [
            p for p in catalog.products.values()
            if p.category == cat and p.priority is not None
        ]
    if not candidates:
        return None

    # Sort by priority (1 = best), return top
    candidates.sort(key=lambda p: p.priority)
    return candidates[0]


def _get_generic_name(sku: str) -> Optional[str]:
    """Get a category-level generic product name for an invalid SKU."""
    prefix = sku.split()[0] if " " in sku else sku[:2]
    prefix_to_key = {
        "BM": ("blood_pressure", "oberarm"),
        "BC": ("blood_pressure", "handgelenk"),
        "EM": ("pain_tens", "tens_ems"),
        "IL": ("infrarot", "infrarotlampe"),
    }
    key = prefix_to_key.get(prefix)
    return _CATEGORY_GENERIC_NAMES.get(key) if key else None


def apply_product_validation(article: Dict, catalog: ProductCatalog) -> Dict:
    """Run product validation on all HTML content fields and fix invalid mentions.

    Modifies article dict in place. Returns dict with validation report.
    """
    from typing import Any
    fields_checked = 0
    replacements_made = 0

    # Fields that can contain product mentions
    content_fields = ["Intro", "Direct_Answer"]
    for i in range(1, 10):
        content_fields.append(f"section_{i:02d}_content")

    for field_name in content_fields:
        content = article.get(field_name, "")
        if not isinstance(content, str) or not content:
            continue

        fields_checked += 1
        result = validate_product_mentions(content, catalog)

        if not result.valid:
            for issue in result.issues:
                if issue.replacement_text:
                    # Replace invalid SKU with replacement
                    # Use word-boundary-aware replacement
                    pattern = re.compile(
                        rf'\b{re.escape(issue.sku)}\b'
                    )
                    new_content = pattern.sub(issue.replacement_text, content)
                    if new_content != content:
                        content = new_content
                        replacements_made += 1
                        logger.info(
                            f"Replaced '{issue.sku}' with '{issue.replacement_text}' "
                            f"in {field_name}"
                        )

            article[field_name] = content

    # Rewrite product links to use catalog URLs
    links_rewritten = _rewrite_product_links(article, catalog, content_fields)

    return {
        "fields_checked": fields_checked,
        "replacements_made": replacements_made,
        "links_rewritten": links_rewritten,
    }


def _rewrite_product_links(
    article: Dict, catalog: ProductCatalog, fields: List[str]
) -> int:
    """Rewrite <a href> tags that reference Beurer products to use catalog URLs."""
    rewritten = 0
    product_urls = catalog.get_product_urls()
    if not product_urls:
        return 0  # No URLs populated yet

    for field_name in fields:
        content = article.get(field_name, "")
        if not isinstance(content, str) or not content:
            continue

        for sku, url in product_urls.items():
            # Find anchor tags whose text mentions this SKU
            pattern = re.compile(
                rf'<a\s+([^>]*?)href=["\'][^"\']*["\']([^>]*)>'
                rf'([^<]*\b{re.escape(sku)}\b[^<]*)</a>',
                re.IGNORECASE,
            )
            def _replace_href(m, _url=url):
                attrs_before = m.group(1)
                attrs_after = m.group(2)
                text = m.group(3)
                return (
                    f'<a {attrs_before}href="{_url}"{attrs_after}>'
                    f'{text}</a>'
                )

            new_content = pattern.sub(_replace_href, content)
            if new_content != content:
                content = new_content
                rewritten += 1

        article[field_name] = content

    return rewritten
```

- [ ] **Step 3: Verify the module loads correctly**

Run: `python -c "import sys; sys.path.insert(0, '.'); from blog.product_catalog import load_catalog; c = load_catalog(); print(f'{len(c.products)} products, prio1: {[p.sku for p in c.get_priority_products(1)]}')"` from project root.

Expected: `33 products, prio1: ['BM 25', 'BM 27', 'BM 81', 'EM 50', 'EM 55', 'EM 59', 'EM 89', 'IL 50', 'IL 60']`

- [ ] **Step 4: Commit**

```bash
git add blog/product_catalog.json blog/product_catalog.py
git commit -m "feat: add Beurer product catalog and validation module

33 products from Anika's German webshop catalog with priority tiers.
URLs null until confirmed by Beurer. PIM-ready loader interface."
```

---

## Task 2: Label Rename + Lettered Footnotes (2a + 2b)

**Files:**
- Modify: `blog/shared/html_renderer.py:35` (label), `blog/shared/html_renderer.py:918` (footnotes)
- Modify: `dashboard/lib/html-renderer.ts` (mirror both changes)
- Modify: `blog/stage2/prompts/system_instruction.txt` (footnote format)
- Modify: `blog/stage_cleanup/cleanup.py` (footnote count warning)

- [ ] **Step 1: Change "Kurze Antwort" label in Python renderer**

In `blog/shared/html_renderer.py` line 35, change:
```python
"direct_answer": "Kurze Antwort:",
```
to:
```python
"direct_answer": "Das Wichtigste in K\u00fcrze:",
```

- [ ] **Step 2: Change sources list to lettered in Python renderer**

In `blog/shared/html_renderer.py` line 920 (inside `_render_sources`), change:
```python
<ol class="sources-list">{"".join(items)}</ol>
```
to:
```python
<ol class="sources-list" type="A">{"".join(items)}</ol>
```

- [ ] **Step 3: Mirror both changes in TypeScript renderer**

In `dashboard/lib/html-renderer.ts`:
- Line 24: change `direct_answer: "Kurze Antwort:",` to `direct_answer: "Das Wichtigste in Kürze:",`
- Line 304: change `<ol class="sources-list">` to `<ol class="sources-list" type="A">`

- [ ] **Step 4: Update Stage 2 prompt for lettered footnotes**

In `blog/stage2/prompts/system_instruction.txt`, find the SOURCE QUALITY section and add after the existing source instructions:

```
FOOTNOTE FORMAT:
- When referencing a source in article text, use LETTERED superscripts: <sup>A</sup>, <sup>B</sup>, <sup>C</sup> etc.
- Do NOT use numbered superscripts (<sup>1</sup>, <sup>2</sup>) — Beurer uses numbers for campaigns.
- Letter A corresponds to the first source in the Sources list, B to the second, etc.
- Place the superscript immediately after the claim it supports, before any punctuation.
```

- [ ] **Step 5: Add footnote count warning to cleanup stage**

In `blog/stage_cleanup/cleanup.py`, add a function and call it from `run_cleanup()` before the return statement (after line 91):

```python
def _check_footnote_count(article: Dict[str, Any]) -> Optional[str]:
    """Check if superscript letter count matches source count. Returns warning or None."""
    sources = article.get("Sources", [])
    if not sources or not isinstance(sources, list):
        return None

    source_count = len(sources)

    # Count <sup> tags across all section content fields
    sup_count = 0
    seen_letters = set()
    for i in range(1, 10):
        content = article.get(f"section_{i:02d}_content", "")
        if isinstance(content, str):
            for m in re.finditer(r'<sup>([A-Z])</sup>', content):
                seen_letters.add(m.group(1))
            sup_count += len(re.findall(r'<sup>[A-Z]</sup>', content))

    # Also check Intro and Direct_Answer
    for field_name in ("Intro", "Direct_Answer"):
        content = article.get(field_name, "")
        if isinstance(content, str):
            for m in re.finditer(r'<sup>([A-Z])</sup>', content):
                seen_letters.add(m.group(1))

    if seen_letters and len(seen_letters) != source_count:
        return (
            f"Footnote/source count mismatch: {len(seen_letters)} unique footnote letters "
            f"but {source_count} sources"
        )
    return None
```

In `run_cleanup()`, add after line 86 (`result.warnings = validation["warnings"]`):

```python
    # Check footnote/source count
    fn_warning = _check_footnote_count(article)
    if fn_warning:
        result.warnings.append(fn_warning)
```

- [ ] **Step 6: Verify the label change renders correctly**

Run: `python -c "from blog.shared.html_renderer import HTMLRenderer; print(HTMLRenderer._ARTICLE_LABELS if hasattr(HTMLRenderer, '_ARTICLE_LABELS') else 'Check _ARTICLE_LABELS dict')"` — or just read the file and confirm the label says "Das Wichtigste in Kuerze:".

- [ ] **Step 7: Commit**

```bash
git add blog/shared/html_renderer.py dashboard/lib/html-renderer.ts blog/stage2/prompts/system_instruction.txt blog/stage_cleanup/cleanup.py
git commit -m "feat: lettered footnotes (A,B,C) and rename 'Kurze Antwort' to 'Das Wichtigste in Kuerze'

Beurer uses numbers for campaigns, so footnotes switch to letters.
Label rename: 'Kurze Antwort' implied headline is a question.
Cleanup stage warns on footnote/source count mismatch (non-blocking)."
```

---

## Task 3: Whitespace Normalization (2c)

**Files:**
- Modify: `blog/stage_cleanup/cleanup.py:95` (add normalization to `_clean_html`)

- [ ] **Step 1: Add whitespace normalization function**

Add this function in `blog/stage_cleanup/cleanup.py` before `_clean_html`:

```python
def _normalize_whitespace(html: str) -> str:
    """Fix common spacing issues around punctuation, parentheses, and HTML tags.

    Fixes LLM-generated spacing errors like:
    - "TENS (Transkutane...)ist" -> "TENS (Transkutane...) ist"
    - "</strong>text" -> "</strong> text"
    - "text<strong>" -> "text <strong>"
    """
    if not html:
        return html

    result = html

    # Space before ( unless preceded by > (tag close), newline, or start of string
    result = re.sub(r'(?<=[^\s>])\(', ' (', result)

    # Space after ) unless followed by punctuation or < (tag open)
    result = re.sub(r'\)(?=[^\s,.:;!?<)])', ') ', result)

    # Space after sentence-ending punctuation unless followed by </ (closing tag) or end
    result = re.sub(r'([.:;])(?=[A-Za-z\u00C0-\u024F])', r'\1 ', result)

    # Space at tag-text boundaries: </tag>text -> </tag> text
    result = re.sub(r'(</(?:strong|em|a|b|i|span)>)(?=[A-Za-z\u00C0-\u024F0-9])', r'\1 ', result)

    # Space at tag-text boundaries: text<tag> -> text <tag>
    result = re.sub(r'([A-Za-z\u00C0-\u024F0-9])(<(?:strong|em|a\s|b>|i>|span))', r'\1 \2', result)

    return result
```

- [ ] **Step 2: Wire into `_clean_html`**

In `blog/stage_cleanup/cleanup.py`, in the `_clean_html` function, add the normalization call after the existing cleaning steps but BEFORE the `return cleaned.strip()` at line 153. Add it after step 12 (remove control characters):

```python
    # 13. Normalize whitespace around punctuation and tags
    cleaned = _normalize_whitespace(cleaned)
```

- [ ] **Step 3: Verify with a test string**

Run:
```bash
python -c "
from blog.stage_cleanup.cleanup import _normalize_whitespace
tests = [
    ('TENS (Transkutane Elektrische Nervenstimulation)ist eine', 'TENS (Transkutane Elektrische Nervenstimulation) ist eine'),
    ('</strong>text', '</strong> text'),
    ('word<strong>bold', 'word <strong>bold'),
    ('normal (parenthetical) text', 'normal (parenthetical) text'),
    ('Ende.</p>', 'Ende.</p>'),
]
for inp, expected in tests:
    result = _normalize_whitespace(inp)
    status = 'PASS' if result == expected else 'FAIL'
    print(f'{status}: {inp!r} -> {result!r} (expected {expected!r})')
"
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add blog/stage_cleanup/cleanup.py
git commit -m "feat: whitespace normalization in cleanup stage

Fixes LLM-generated spacing issues around parentheses, punctuation,
and HTML tag boundaries. Runs deterministically on every article."
```

---

## Task 4: Homepage Redirect Detection (2e)

**Files:**
- Modify: `blog/stage4/stage4_models.py:18-24` (new enum value)
- Modify: `blog/stage4/http_checker.py:105-143` (detection logic)
- Modify: `blog/stage4/stage_4.py` (handle new status)

- [ ] **Step 1: Add new URLStatus enum value**

In `blog/stage4/stage4_models.py`, add to the `URLStatus` enum after `REMOVED`:

```python
    HOMEPAGE_REDIRECT = "homepage_redirect"  # Redirected to site homepage
```

- [ ] **Step 2: Add homepage detection in HTTPChecker**

In `blog/stage4/http_checker.py`, add a helper function before `_do_check`:

```python
def _is_homepage_path(path: str) -> bool:
    """Check if a URL path looks like a homepage (root or shallow locale path)."""
    # Normalize: strip trailing slashes
    clean = path.rstrip("/")
    if not clean:
        return True  # Root path
    # Common homepage patterns: /en, /de, /fr, /en-us, etc.
    segments = [s for s in clean.split("/") if s]
    if len(segments) <= 1 and re.match(r'^[a-z]{2}(-[a-z]{2})?$', segments[0] if segments else ''):
        return True
    return False
```

Add `import re` at the top of the file if not already imported.

- [ ] **Step 3: Add redirect-to-homepage detection in `_do_check`**

In `blog/stage4/http_checker.py`, in the `_do_check` method, after the `final_url` is captured (around line 132) and before the return statement, add:

```python
            # Detect homepage redirects
            is_homepage_redirect = False
            if final_url and is_alive:
                from urllib.parse import urlparse
                is_homepage_redirect = _is_homepage_path(urlparse(final_url).path)
```

Add `is_homepage_redirect` to the `HTTPCheckResult` dataclass:

```python
    is_homepage_redirect: bool = False
```

Then update the return statement in `_do_check` (around line 137) to include the new field:

```python
            return HTTPCheckResult(
                url=url,
                is_alive=is_alive,
                status_code=response.status_code,
                final_url=final_url,
                response_time_ms=elapsed,
                is_homepage_redirect=is_homepage_redirect,
            )
```

Note: the fallback return statements in the exception handlers (lines ~145-169) can rely on the default `False` value.

- [ ] **Step 4: Handle homepage redirects in Stage 4 main logic**

In `blog/stage4/stage_4.py` line 415, the status assignment reads:

```python
                status=URLStatus.VALID if http_result.is_alive else URLStatus.DEAD,
```

Replace with:

```python
                status=(
                    URLStatus.DEAD if not http_result.is_alive
                    else URLStatus.HOMEPAGE_REDIRECT if getattr(http_result, 'is_homepage_redirect', False)
                    else URLStatus.VALID
                ),
```

Then in the replacement logic later in the file, wherever `URLStatus.DEAD` triggers a replacement search, also include `URLStatus.HOMEPAGE_REDIRECT`. Search for:
```python
if result.status == URLStatus.DEAD
```
and change to:
```python
if result.status in (URLStatus.DEAD, URLStatus.HOMEPAGE_REDIRECT)
```

- [ ] **Step 5: Commit**

```bash
git add blog/stage4/stage4_models.py blog/stage4/http_checker.py blog/stage4/stage_4.py
git commit -m "feat: detect homepage redirects in Stage 4 URL verification

URLs that 200 but redirect to a homepage path (/, /de/, etc.) are
now treated as dead and trigger replacement search."
```

---

## Task 5: Priority Products in Stage 2 Prompt

**Files:**
- Modify: `blog/stage2/prompts/system_instruction.txt`

- [ ] **Step 1: Add priority product instruction**

In `blog/stage2/prompts/system_instruction.txt`, in the section where Beurer products are described or near the product mention instructions, add:

```
FOCUS PRODUCTS (Priorität 1 — bevorzugt erwaehnen):
- Blutdruck Oberarm: BM 25, BM 27, BM 81
- TENS/EMS: EM 50, EM 55, EM 59, EM 89
- Infrarot: IL 50, IL 60
When the article topic is relevant to any of these products, prefer mentioning them over non-priority products. These are Beurer's current strategic focus products for the German market.
```

- [ ] **Step 2: Commit**

```bash
git add blog/stage2/prompts/system_instruction.txt
git commit -m "feat: add priority product list to Stage 2 prompt

Prio 1 products from Beurer's German catalog get preferential
mention when relevant to the article topic."
```

---

## Task 6: Repetition Reduction Prompt (2f)

> Note: Old Task 5 is now Task 5 (priority products) + Task 6 (repetition). Tasks after this are renumbered +1.

**Files:**
- Modify: `blog/stage2/prompts/system_instruction.txt`

- [ ] **Step 1: Add deduplication instruction to Stage 2 prompt**

In `blog/stage2/prompts/system_instruction.txt`, add a new section (after the SOURCE QUALITY section or near the article structure instructions):

```
CONTENT DEDUPLICATION:
- NEVER repeat the same fact, claim, statistic, or piece of advice in multiple sections.
- Each piece of information must appear exactly ONCE, in the most relevant section.
- If a fact is relevant to multiple sections, place it in the section where it is most directly applicable and reference it briefly from other sections if needed (e.g., "Wie bereits erwaehnt..." or "Siehe Abschnitt X").
- This applies across ALL content: sections, FAQ answers, PAA answers, and Direct_Answer.
```

- [ ] **Step 2: Commit**

```bash
git add blog/stage2/prompts/system_instruction.txt
git commit -m "feat: add dedup instruction to Stage 2 prompt

Prevents repetition of facts across article sections.
Prompt-level enforcement; Stage 3 check to be added if needed."
```

---

## Task 7: Internal Linking Rules (2d)

**Files:**
- Modify: `blog/stage5/stage5_models.py:25-42` (new field)
- Modify: `blog/stage5/stage_5.py:246-323` (blocklist + category emphasis)
- Modify: `blog/beurer_context.py:199-246` (remove App Welt/Produktberater)
- Modify: `blog/article_service.py:167-196` (pass catalog URLs)
- Modify: `blog/pipeline.py:325-366` (pass catalog URLs)

- [ ] **Step 1: Add `sitemap_category_urls` field to Stage5Input**

In `blog/stage5/stage5_models.py`, add after `sitemap_service_urls` (line 36):

```python
    sitemap_category_urls: List[str] = Field(default_factory=list, description="Category overview page URLs (prioritized for linking)")
```

- [ ] **Step 2: Add URL blocklist to `_build_link_pool`**

In `blog/stage5/stage_5.py`, at the top of `_build_link_pool()` (line 247), add:

```python
    # Blocklist: URLs that should never appear in articles
    _BLOCKED_PATTERNS = ['/app-welt/', '/produktberater']

    def _is_blocked(url: str) -> bool:
        return any(pat in url.lower() for pat in _BLOCKED_PATTERNS)
```

Then wrap every `candidates.append(...)` call in `_build_link_pool` with a check:

```python
    if rel_path and rel_path not in seen_paths and not self._is_current_article(url, current_href) and not _is_blocked(url):
```

- [ ] **Step 3: Add category URLs to link pool with priority**

In `_build_link_pool()`, add category URL handling BEFORE the blog URLs section (so they appear first — higher priority):

```python
    # Add category overview URLs first (highest priority per Anika's feedback)
    for url in input_data.sitemap_category_urls:
        rel_path = self._normalize_to_path(url)
        if rel_path and rel_path not in seen_paths and not _is_blocked(url):
            candidates.append(LinkCandidate(
                url=rel_path,
                title=self._url_to_title(url) + " (Kategorie-Uebersicht)",
                source="category"
            ))
            seen_paths.add(rel_path)
```

- [ ] **Step 4: Update prompt to emphasize category links**

In `blog/stage5/stage_5.py`, in the fallback prompt (line 116 area) or in the prompt template, update the RULES to include:

```
- Include at least 1-2 links to category overview pages (marked with "Kategorie-Uebersicht"), especially in introductions and section conclusions
- Category overview links help readers find the full product range
```

- [ ] **Step 5: Remove App Welt / Produktberater from `get_beurer_sitemap_urls()`**

In `blog/beurer_context.py`, in the `get_beurer_sitemap_urls()` function (lines 199-246):

Remove from `resource_urls`:
```python
"https://www.beurer.com/de/service/app-welt/",
```

Remove from `tool_urls`:
```python
"https://www.beurer.com/de/l/produktberater-blutdruck/",
"https://www.beurer.com/de/l/produktberater-tens-ems/",
"https://www.beurer.com/de/l/produktberater-waerme/",
"https://www.beurer.com/de/l/produktberater-massage/",
```

- [ ] **Step 6: Pass catalog URLs at call sites**

In `blog/article_service.py`, in `_run_stages_4_5_cleanup()` (around line 174), add catalog import and pass category URLs:

```python
    # Load catalog for category URLs
    try:
        from .product_catalog import load_catalog
        catalog = load_catalog()
        catalog_category_urls = list(catalog.get_category_urls().values())
        catalog_product_urls = list(catalog.get_product_urls().values())
    except Exception:
        catalog_category_urls = []
        catalog_product_urls = []
```

Update the Stage 5 call dict (line 174-184) to include:
```python
    "sitemap_category_urls": catalog_category_urls,
    "sitemap_product_urls": catalog_product_urls or sitemap.get("product_urls", [])[:10],
```

> **Note:** Until Beurer confirms working URLs, `catalog_product_urls` and `catalog_category_urls` will both be empty lists (all URLs are `null` in the JSON). The fallback to sitemap URLs is intentional for this transition period. Once URLs are populated, the catalog takes precedence.

Apply the same pattern in `blog/pipeline.py` at the Stage 5 call site (lines 337-355).

- [ ] **Step 7: Commit**

```bash
git add blog/stage5/stage5_models.py blog/stage5/stage_5.py blog/beurer_context.py blog/article_service.py blog/pipeline.py
git commit -m "feat: catalog-driven internal linking with blocklist and category emphasis

Stage 5 now uses product catalog URLs, blocks App Welt/Produktberater
links, and prioritizes category overview page links per Anika's feedback."
```

---

## Task 8: Wire Stage 5.5 Product Validation

**Files:**
- Modify: `blog/article_service.py:196-199` (insert Stage 5.5)
- Modify: `blog/pipeline.py:366-370` (insert Stage 5.5)

- [ ] **Step 1: Wire Stage 5.5 in `article_service.py`**

In `blog/article_service.py`, in `_run_stages_4_5_cleanup()`, after the Stage 5 block (line 196) and before the cleanup block (line 198-199), add:

```python
    # Stage 5.5: Product validation (deterministic, no LLM)
    _set_stage(article_id, "product_validation")
    try:
        from .product_catalog import load_catalog, apply_product_validation

        catalog = load_catalog()
        validation_report = apply_product_validation(article_dict, catalog)
        pipeline_reports["product_validation"] = validation_report
        logger.info(
            f"Stage 5.5: Validated products — "
            f"{validation_report['replacements_made']} replacements, "
            f"{validation_report['links_rewritten']} links rewritten"
        )
    except Exception as e:
        logger.warning(f"Stage 5.5 product validation failed (non-blocking): {e}")
        pipeline_reports["product_validation"] = {"error": str(e)}
```

- [ ] **Step 2: Wire Stage 5.5 in `pipeline.py`**

In `blog/pipeline.py`, after the Stage 5 block and before the Cleanup block (between lines ~366-370), add the same pattern:

```python
    # -----------------------------------------
    # Stage 5.5: Product Validation
    # -----------------------------------------
    logger.info(f"    [Stage 5.5] Product validation...")

    try:
        from services.blog.product_catalog import load_catalog, apply_product_validation

        catalog = load_catalog()
        validation_report = apply_product_validation(article_dict, catalog)
        result["reports"]["product_validation"] = validation_report
        logger.info(
            f"    [Stage 5.5] ✓ {validation_report['replacements_made']} replacements, "
            f"{validation_report['links_rewritten']} links rewritten"
        )
    except Exception as e:
        logger.warning(f"    [Stage 5.5] Product validation failed (non-blocking): {e}")
        result["reports"]["product_validation"] = {"error": str(e)}
```

Note: import path differs between the two files (`from .product_catalog` in article_service vs `from services.blog.product_catalog` in pipeline) — follow the existing import pattern in each file.

- [ ] **Step 3: Verify Stage 5.5 import works from both paths**

Run:
```bash
python -c "from blog.product_catalog import load_catalog, apply_product_validation; print('article_service import OK')"
python -c "from services.blog.product_catalog import load_catalog, apply_product_validation; print('pipeline import OK')" 2>/dev/null || echo "pipeline import path may differ — check existing import patterns in pipeline.py"
```

- [ ] **Step 4: Commit**

```bash
git add blog/article_service.py blog/pipeline.py
git commit -m "feat: wire Stage 5.5 product validation into both pipeline paths

Validates product mentions against catalog, replaces invalid SKUs,
rewrites product links to webshop URLs. Non-blocking (logs warning on failure)."
```

---

## Task 9: Inline URL Edit Fix (3a)

**Files:**
- Modify: `blog/article_service.py:745-795` (URL-edit detection + HTML-aware prompt)

- [ ] **Step 1: Add URL-edit detection to `apply_inline_edits`**

In `blog/article_service.py`, in the `apply_inline_edits` function, after the passage resolution loop (around line 755 where `resolved` list is built), modify the prompt construction loop (lines 769-773) to detect URL edits and use HTML:

Replace the existing `edits_block` construction loop with:

```python
    edits_block = ""
    has_url_edits = False
    for i, r in enumerate(resolved, 1):
        comment = r['comment']
        is_url_edit = bool(re.search(r'https?://|link|url|verlinkung', comment, re.IGNORECASE))
        # For URL edits, send the full HTML so Gemini can see/modify href attributes
        passage = r['original_html'] if is_url_edit else r['plain_text']
        if is_url_edit:
            has_url_edits = True
        edits_block += (
            f"Edit {i}:\n"
            f"  Original: {passage}\n"
            f"  Comment: {comment}\n\n"
        )
```

- [ ] **Step 2: Add URL-edit prompt rule**

After the `edits_block` construction, add a conditional rule to the prompt (before the existing `prompt = f"""...`):

```python
    url_edit_rule = ""
    if has_url_edits:
        url_edit_rule = (
            "\n- When asked to change a URL or link, modify the href attribute value "
            "in the <a> tag. Preserve the anchor text unless explicitly asked to change it."
            "\n- Return the complete HTML including the <a> tag with the updated href."
        )
```

Then insert `{url_edit_rule}` into the RULES section of the existing prompt string (after the "Keep the same tone and style." line).

- [ ] **Step 3: Handle validation for URL edits**

In the replacement application loop (around line 826-833), add URL-edit awareness to the validator call:

```python
            if _validate is not None:
                # For URL edits, both original and replacement are HTML
                is_html = bool(re.search(r'<a\s', original_html))
                ok, reason = _validate(original_html, revised_text, ctx_before, ctx_after, is_html=is_html)
```

- [ ] **Step 4: Commit**

```bash
git add blog/article_service.py
git commit -m "fix: inline URL edits now send HTML with href to Gemini

URL-edit detection heuristic checks comment for URL/link/verlinkung
keywords. When detected, sends original_html (with <a href>) instead
of plain text, so Gemini can modify the href attribute."
```

---

## Task 10: Change Visibility After Edit (3b)

**Files:**
- Modify: `blog/article_service.py:816-850` (add changes array to return)
- Note: Frontend component changes needed but must be identified in the blog platform UI (not in this repo's dashboard)

- [ ] **Step 1: Build changes array in `apply_inline_edits`**

In `blog/article_service.py`, in the replacement application loop, build a `changes` list:

Before the loop (around line 816), add:
```python
    changes = []
```

Inside the loop, after a successful replacement (after `edits_applied += 1`), add:
```python
            changes.append({
                "edit_number": idx,
                "original_snippet": original_html[:200],
                "revised_snippet": revised_text[:200],
            })
```

- [ ] **Step 2: Include changes in return payload**

In the return dict at the end of `apply_inline_edits` (around line 860), add `"changes": changes`:

```python
    # Save updated article
    # ... existing save logic ...

    return {
        "id": article_id,
        "status": "completed",
        "article_html": updated_html,
        "feedback_history": history,
        "edits_applied": edits_applied,
        "changes": changes,  # NEW: diff details for frontend
    }
```

- [ ] **Step 3: Commit**

```bash
git add blog/article_service.py
git commit -m "feat: return change details from inline edits for frontend diff display

apply_inline_edits now returns a 'changes' array with original/revised
snippets for each applied edit. Frontend can render diff highlights."
```

---

## Task 11: Text Selection for Normal Comments (3c)

**Files:**
- Modify: `dashboard/app/api/blog-article/route.ts` (accept `selected_text` in comment payload)

- [ ] **Step 1: Add `selected_text` to comment creation**

In `dashboard/app/api/blog-article/route.ts`, find the `add_comment` action handler. Add `selected_text` as an optional field:

```typescript
// In the add_comment handler, extract selected_text from body
const selected_text = body.selected_text || null;

// Include in the Supabase insert
const { error } = await supabase
  .from('article_comments')
  .insert({
    article_id,
    author,
    comment_text,
    selected_text,  // NEW: optional text anchor
  });
```

- [ ] **Step 2: Return `selected_text` in comment fetch**

In the GET handler for comments, ensure `selected_text` is included in the select query (it should come through automatically if the column exists in the table, but verify the select statement).

- [ ] **Step 3: Commit**

```bash
git add dashboard/app/api/blog-article/route.ts
git commit -m "feat: support selected_text in article comments

Comments can now include a text passage anchor. Frontend changes
for text selection capture and hover highlighting are separate."
```

**Note:** The Supabase `article_comments` table needs a `selected_text` column (nullable text). This may need to be added via the Supabase dashboard or a migration. The frontend changes (text selection capture, hover highlighting) need to be implemented in the blog platform UI, which is outside this repo.

---

## Dependency Map

```
Task 1 (Catalog) ──┬──> Task 7 (Internal Linking) ──> Task 8 (Wire Stage 5.5)
                    │
Task 2 (Labels/Footnotes)  ─── independent
Task 3 (Whitespace)        ─── independent
Task 4 (Homepage Redirect) ─── independent
Task 5 (Priority Products) ─── independent
Task 6 (Dedup Prompt)      ─── independent
Task 9  (URL Edit Fix)     ─── independent (Workstream C)
Task 10 (Change Visibility)─── independent (Workstream C)
Task 11 (Comment Text Sel) ─── independent (Workstream C)
```

Tasks 2-6 and 9-11 can all run in parallel. Tasks 7 and 8 depend on Task 1.

> **Note:** Existing articles with numbered footnotes are NOT retroactively fixed. All changes only apply to newly generated/regenerated articles. The March 28+ full regeneration of all 15 articles is the migration event.

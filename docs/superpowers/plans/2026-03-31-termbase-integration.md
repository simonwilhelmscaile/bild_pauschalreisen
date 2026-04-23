# Termbase Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inject official Beurer terminology from an xlsx termbase into the blog article generation prompt so the LLM uses canonical product terms and translations.

**Architecture:** One-time conversion script turns the xlsx into a JSON file (`blog/termbase.json`). A service module (`blog/termbase.py`) loads and filters relevant terms by keyword. The blog writer (`blog/stage2/blog_writer.py`) injects filtered terms into the LLM prompt via `_format_company_context()`.

**Tech Stack:** Python 3.11, openpyxl (already in requirements), JSON, existing Gemini-based blog pipeline

**Spec:** `docs/superpowers/specs/2026-03-31-termbase-integration-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `blog/convert_termbase.py` | Create | One-time xlsx to JSON converter |
| `blog/termbase.json` | Create (generated) | Static JSON termbase (de + en, ~1,295 terms) |
| `blog/termbase.py` | Create | Load JSON, filter by keyword, return relevant terms |
| `blog/stage2/blog_writer.py` | Modify | Pass keyword/language to `_format_company_context()`, add terminology prompt section |

---

### Task 1: Convert xlsx to JSON

**Files:**
- Create: `blog/convert_termbase.py`
- Create: `blog/termbase.json` (generated output)

- [ ] **Step 1: Create the conversion script**

```python
#!/usr/bin/env python3
"""One-time converter: Beurer termbase xlsx -> JSON.

Usage:
    python blog/convert_termbase.py
"""
import json
import re
from datetime import date
from pathlib import Path

import openpyxl

XLSX_PATH = Path(__file__).parent.parent / "Beurer GmbH_Termbase_all_languages_30032026.xlsx"
OUTPUT_PATH = Path(__file__).parent / "termbase.json"

# Model number pattern: 1-3 uppercase letters followed by optional space and 2-3 digits
_MODEL_PATTERN = re.compile(r'\b[A-Z]{1,3}\s?\d{2,3}\b')


def _is_product_name(term: str) -> bool:
    """Detect product names by presence of (R) symbol or model number patterns."""
    if "\u00ae" in term:  # ® symbol
        return True
    if _MODEL_PATTERN.search(term):
        return True
    return False


def convert():
    wb = openpyxl.load_workbook(str(XLSX_PATH), read_only=True)
    ws = wb["Beurer GmbH"]

    terms = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # skip header

        entry_id = row[0]
        de_term = row[1]
        en_term = row[2]

        if not de_term:
            continue

        term = {
            "id": entry_id,
            "de": str(de_term).strip(),
            "is_product_name": _is_product_name(str(de_term)),
        }

        if en_term:
            term["en"] = str(en_term).strip()

        terms.append(term)

    output = {
        "meta": {
            "source": XLSX_PATH.name,
            "term_count": len(terms),
            "generated_at": str(date.today()),
        },
        "terms": terms,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(terms)} terms to {OUTPUT_PATH}")

    # Print stats
    product_names = sum(1 for t in terms if t["is_product_name"])
    with_en = sum(1 for t in terms if "en" in t)
    print(f"  Product names: {product_names}")
    print(f"  With English translation: {with_en}")


if __name__ == "__main__":
    convert()
```

- [ ] **Step 2: Run the conversion script**

Run: `python blog/convert_termbase.py`
Expected: prints term count, creates `blog/termbase.json` with ~1,295 terms.

- [ ] **Step 3: Verify the generated JSON**

Run: `python -c "import json; d=json.load(open('blog/termbase.json',encoding='utf-8')); print(f'Terms: {len(d[\"terms\"])}'); print(f'Product names: {sum(1 for t in d[\"terms\"] if t[\"is_product_name\"])}'); print('Sample:', json.dumps(d['terms'][:3], ensure_ascii=False, indent=2))"`
Expected: ~1,295 terms, product names flagged correctly, sample terms look right.

- [ ] **Step 4: Commit**

```bash
git add blog/convert_termbase.py blog/termbase.json
git commit -m "feat: convert Beurer termbase xlsx to JSON (de + en)"
```

---

### Task 2: Termbase service module

**Files:**
- Create: `blog/termbase.py`

- [ ] **Step 1: Create the termbase service**

```python
"""Beurer termbase for enforcing official terminology in blog articles.

Loads blog/termbase.json (generated from xlsx) and filters terms relevant
to a given article keyword. Follows the same pattern as blog/product_catalog.py
(static JSON, loaded once, cached in module variable).
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_TERMBASE_PATH = Path(__file__).parent / "termbase.json"
_cache: Optional[List[Dict]] = None


def _load_terms() -> List[Dict]:
    """Load termbase JSON, cache on first call."""
    global _cache
    if _cache is not None:
        return _cache

    if not _TERMBASE_PATH.exists():
        logger.warning(f"Termbase not found: {_TERMBASE_PATH}")
        _cache = []
        return _cache

    data = json.loads(_TERMBASE_PATH.read_text(encoding="utf-8"))
    _cache = data.get("terms", [])
    logger.info(f"Loaded termbase: {len(_cache)} terms")
    return _cache


def get_relevant_terms(
    keyword: str,
    language: str = "de",
    max_terms: int = 50,
) -> List[Dict[str, str]]:
    """Filter termbase to terms relevant to the article keyword.

    Always includes product names (model numbers, (R) marks).
    Additionally includes terms matching any word from the keyword.

    Args:
        keyword: Article keyword, e.g. "Blutdruckmessgeraet Oberarm"
        language: "de" or "en" — determines which translation to return
        max_terms: Maximum number of terms to return

    Returns:
        List of {"de": str, "target": str, "is_product_name": bool}
    """
    terms = _load_terms()
    if not terms:
        return []

    is_en = language.startswith("en")

    # Split keyword into individual words for matching (min 3 chars to avoid noise)
    keyword_words = [
        w.lower() for w in keyword.split() if len(w) >= 3
    ]

    product_matches = []
    keyword_matches = []

    for term in terms:
        de_val = term.get("de", "")
        if not de_val:
            continue

        # Resolve target language value
        if is_en:
            target = term.get("en")
            if not target:
                continue  # skip terms without English translation
        else:
            target = de_val

        entry = {
            "de": de_val,
            "target": target,
            "is_product_name": term.get("is_product_name", False),
        }

        if term.get("is_product_name", False):
            product_matches.append(entry)
        elif keyword_words:
            de_lower = de_val.lower()
            if any(word in de_lower for word in keyword_words):
                keyword_matches.append(entry)

    # Product names first, then keyword matches, capped
    result = product_matches + keyword_matches
    return result[:max_terms]
```

- [ ] **Step 2: Verify the module loads correctly**

Run: `python -c "from blog.termbase import get_relevant_terms; terms = get_relevant_terms('Blutdruckmessgeraet Oberarm', 'de'); print(f'{len(terms)} terms'); [print(f'  {t[\"de\"]} -> {t[\"target\"]} (product={t[\"is_product_name\"]})') for t in terms[:5]]"`
Expected: prints matching terms including product names and keyword matches like "Blutdruckmessgerät".

- [ ] **Step 3: Test English language mode**

Run: `python -c "from blog.termbase import get_relevant_terms; terms = get_relevant_terms('Schmerztherapie TENS', 'en'); print(f'{len(terms)} terms'); [print(f'  {t[\"de\"]} -> {t[\"target\"]} (product={t[\"is_product_name\"]})') for t in terms[:5]]"`
Expected: `target` values are English translations (e.g. "Schmerztherapie" -> "Pain therapy").

- [ ] **Step 4: Commit**

```bash
git add blog/termbase.py
git commit -m "feat: add termbase service for keyword-filtered terminology lookup"
```

---

### Task 3: Inject terminology into blog writer prompt

**Files:**
- Modify: `blog/stage2/blog_writer.py:141-200` (write_article function)
- Modify: `blog/stage2/blog_writer.py:316-486` (_format_company_context function)

- [ ] **Step 1: Modify `_format_company_context()` to accept keyword and language, and append terminology section**

In `blog/stage2/blog_writer.py`, change the `_format_company_context` function signature (line 316) from:

```python
def _format_company_context(context: Dict[str, Any]) -> str:
```

to:

```python
def _format_company_context(
    context: Dict[str, Any],
    keyword: str = "",
    language: str = "de",
) -> str:
```

Then, at the end of the function, just before the final `return "\n".join(lines)` (line 486), add the terminology section:

```python
    # Official terminology from Beurer termbase
    if keyword:
        try:
            from blog.termbase import get_relevant_terms
            termbase_terms = get_relevant_terms(keyword, language)
            if termbase_terms:
                lines.append("")
                lines.append("=== MANDATORY TERMINOLOGY (use these exact terms) ===")

                product_terms = [t for t in termbase_terms if t["is_product_name"]]
                glossary_terms = [t for t in termbase_terms if not t["is_product_name"]]

                if product_terms:
                    lines.append("Product names (use verbatim, never paraphrase):")
                    for t in product_terms:
                        lines.append(f"  - {t['de']}")

                if glossary_terms:
                    is_en = language.startswith("en")
                    if is_en:
                        lines.append("Glossary (use these exact English translations):")
                        for t in glossary_terms:
                            lines.append(f"  - {t['de']} \u2192 {t['target']}")
                    else:
                        lines.append("Glossary (use these exact German terms):")
                        for t in glossary_terms:
                            lines.append(f"  - {t['target']}")
        except Exception as e:
            logger.warning(f"Failed to load termbase terms: {e}")
```

- [ ] **Step 2: Update `write_article()` to pass keyword and language to `_format_company_context()`**

In `blog/stage2/blog_writer.py`, change line 192 from:

```python
        company_str = _format_company_context(company_context)
```

to:

```python
        company_str = _format_company_context(company_context, keyword=keyword, language=language)
```

- [ ] **Step 3: Verify the prompt includes terminology**

Run: `python -c "
from blog.stage2.blog_writer import _format_company_context
from blog.beurer_context import get_beurer_company_context
ctx = get_beurer_company_context('de')
result = _format_company_context(ctx, keyword='Blutdruckmessgeraet Oberarm', language='de')
# Find the terminology section
idx = result.find('MANDATORY TERMINOLOGY')
if idx >= 0:
    print(result[idx:idx+500])
else:
    print('ERROR: Terminology section not found!')
"`
Expected: prints the MANDATORY TERMINOLOGY section with product names and glossary terms related to blood pressure.

- [ ] **Step 4: Verify English mode**

Run: `python -c "
from blog.stage2.blog_writer import _format_company_context
from blog.beurer_context import get_beurer_company_context
ctx = get_beurer_company_context('en')
result = _format_company_context(ctx, keyword='TENS pain therapy', language='en')
idx = result.find('MANDATORY TERMINOLOGY')
if idx >= 0:
    print(result[idx:idx+500])
else:
    print('ERROR: Terminology section not found!')
"`
Expected: prints terminology with English translations (arrows: de -> en).

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/blog_writer.py
git commit -m "feat: inject termbase terminology into article generation prompt"
```

---

### Task 4: End-to-end verification

- [ ] **Step 1: Verify no import errors in article_service**

The `write_article()` call sites in `article_service.py` are unchanged (the signature change is only to `_format_company_context`, an internal function). Verify imports work:

Run: `python -c "from blog.article_service import generate_article; print('OK')"`
Expected: prints "OK" with no import errors.

- [ ] **Step 2: Spot-check term counts for different keywords**

Run: `python -c "
from blog.termbase import get_relevant_terms
for kw in ['Blutdruckmessgeraet', 'TENS EMS Schmerztherapie', 'Infrarotlampe', 'random unrelated topic']:
    terms = get_relevant_terms(kw, 'de')
    products = sum(1 for t in terms if t['is_product_name'])
    glossary = len(terms) - products
    print(f'{kw}: {len(terms)} total ({products} products, {glossary} glossary)')
"`
Expected: relevant keywords return product names + glossary matches; "random unrelated topic" returns only product names (always included).

- [ ] **Step 3: Commit any fixes if needed, then final commit**

```bash
git add -A
git commit -m "feat: termbase integration complete — Beurer terminology enforced in blog articles"
```

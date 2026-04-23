# Termbase Integration for Blog Article Generation

## Problem

Beurer provides an official termbase (xlsx, ~1,295 terms) with canonical product terminology and translations. When the blog pipeline generates articles, the LLM invents its own phrasing instead of using official Beurer terms. Examples:
- German: LLM writes "Blutdruck-Messgerät für den Oberarm" instead of "Oberarm-Blutdruckmessgerät"
- English: LLM writes "pain treatment" instead of "pain therapy" (the official Beurer term is "Pain therapy")
- Product names like "OT 30 Bluetooth®" get paraphrased or partially dropped

## Decisions

- **Enforce correct terminology** in both German and English articles using the termbase as single source of truth.
- **Product names stay verbatim** in all languages — model names with ®, model numbers, etc. are never paraphrased.
- **General terms use official form** — German articles use canonical German spelling, English articles use the official en-GB translation.
- **File-based storage** — xlsx converted to JSON, committed to repo alongside existing `blog/product_catalog.json`.
- **Keyword-filtered injection** — ~30-50 relevant terms injected per article via substring matching, not the full 1,295.

## Data Layer

### Conversion Script

`blog/convert_termbase.py` — one-time script that reads the xlsx and outputs JSON.

**Product name detection heuristic** (sets `is_product_name: true`):
- Contains ® symbol
- Matches model number patterns: uppercase letters followed by space and digits (e.g. "BM 58", "OT 30", "EM 49", "IL 50")

### JSON Structure

`blog/termbase.json`:

```json
{
  "meta": {
    "source": "Beurer GmbH_Termbase_all_languages_30032026.xlsx",
    "term_count": 1295,
    "generated_at": "2026-03-31"
  },
  "terms": [
    {
      "id": 7236461,
      "de": "Schmerzlinderung",
      "en": "pain relief",
      "is_product_name": false
    },
    {
      "id": 7236457,
      "de": "OT 30 Bluetooth\u00ae \u2013 Basalthermometer",
      "en": "Ovulation Thermometer OT 30 Bluetooth\u00ae",
      "is_product_name": true
    }
  ]
}
```

- Only `de` and `en` (from `de-DE` and `en-GB` columns) — the two languages currently used for article generation.
- Other languages remain in the xlsx for future use.
- Only terms with a non-null value in the relevant column are included.

## Termbase Service

### Module

`blog/termbase.py` — follows the pattern of `blog/product_catalog.py` (static JSON file loaded on first access).

### Function

```python
def get_relevant_terms(keyword: str, language: str = "de", max_terms: int = 50) -> list[dict]
```

Returns a list of `{"de": str, "target": str, "is_product_name": bool}`.

### Algorithm

1. **Load** `termbase.json` on first call, cache in module-level variable.
2. **Always include** all terms where `is_product_name=True`.
3. **Keyword match**: split the article keyword into individual words, case-insensitive substring match each word against the German term (`de` field).
4. **Resolve target**: for `language="de"`, `target` = the `de` value (enforces canonical spelling). For `language="en"`, `target` = the `en` value.
5. **Rank**: product names first, then keyword matches.
6. **Cap** at `max_terms`.

## Prompt Injection

### Location

`blog/stage2/blog_writer.py` in `_format_company_context()` (line 316), added after the existing `Technical Terms` block (around line 430).

### Format

```
=== MANDATORY TERMINOLOGY (use these exact terms) ===
Product names (use verbatim, never paraphrase):
  - OT 30 Bluetooth® – Basalthermometer
  - BM 58

Glossary (use these exact translations, not your own):
  - Schmerzlinderung → pain relief
  - Basalthermometer → Ovulation thermometer
  - Überhitzungsschutz → overheating protection
```

Two sub-sections so the LLM treats product names (verbatim, never change) differently from general vocabulary (use this specific translation/spelling).

For German articles, the glossary section shows only the canonical German term (no arrow):
```
Glossary (use these exact terms):
  - Schmerzlinderung
  - Oberarm-Blutdruckmessgerät
```

### Wiring

`_format_company_context()` gains two new parameters: `keyword` and `language`. It calls `get_relevant_terms(keyword, language)` internally and appends the terminology section to the prompt output. This avoids changing the `write_article()` signature or any of its 4+ call sites in `article_service.py`.

`write_article()` already has `keyword` and `language` as parameters — it just passes them through to `_format_company_context()`.

## Files Changed/Created

| File | Action | Description |
|------|--------|-------------|
| `blog/convert_termbase.py` | Create | One-time xlsx to JSON converter |
| `blog/termbase.json` | Create | Generated JSON termbase (de + en, ~1,295 terms) |
| `blog/termbase.py` | Create | Load JSON, filter by keyword, return relevant terms |
| `blog/stage2/blog_writer.py` | Modify | Pass `keyword` + `language` to `_format_company_context()`, add terminology prompt section |

## What This Does NOT Change

- `beurer_context.py` — termbase is injected at Stage 2 prompt level, not at context construction time.
- `product_catalog.json` — kept as-is; it tracks product metadata (category, priority, URLs), not terminology translations.
- `VoicePersona` / `persona.md` — termbase is a separate concern from voice/style.
- Existing `technical_terms` field in the prompt — kept as-is (voice-derived). Termbase is additive.
- `article_service.py` call sites — no signature changes needed.

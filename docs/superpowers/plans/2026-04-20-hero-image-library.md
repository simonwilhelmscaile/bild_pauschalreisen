# Hero Image Library — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace AI-generated hero images with real photos from the Beurer Academy App library (41 product-use + 22 lifestyle shots), keeping AI generation behind a feature flag.

**Architecture:** Two-branch selector — if headline names a SKU and that SKU has a library photo, pick a product-in-use shot; otherwise pick a mood/lifestyle shot matched by theme. Metadata extends the existing `lifestyle_images.json`. Image binaries live in Supabase Storage `blog-images/library/`. Article text is never rewritten — only `image_01_url` + `image_01_alt_text` change on an article, and `article_html` is re-rendered.

**Tech Stack:** Python 3.11, FastAPI, Supabase Storage, Gemini 2.0 Flash (vision for captioning, text for optional DE translation). Tests: lightweight `assert`-based scripts in `scripts/` (project has no pytest).

**Spec:** `docs/superpowers/specs/2026-04-20-hero-image-library-design.md`

---

## File Structure

**New files:**
- `scripts/ingest_hero_library.py` — one-shot directory ingestion (parse filenames, upload binaries, caption, upsert JSON)
- `scripts/test_hero_library.py` — assertion-based tests (matches `scripts/test_tools.py` pattern)
- `docs/beurer_asset_licensing.md` — summary of `_Beurer_Marketing Assets_Nutzungsbedingungen.pdf` (licensing gate)

**Modified files:**
- `blog/stage2/image_prompts.py` — add filename parser, SKU-theme seed map, first-SKU-in-headline extractor, `select_hero_image()`, alt-text builder. Keep all existing functions for the AI fallback path.
- `blog/stage2/lifestyle_images.json` — extended schema (adds `sku`, `type`, `gender`, `location`); migrates 22 existing entries; ingests 41 new product-use entries.
- `blog/router.py:453-554` — call `select_hero_image()` first; fall through to existing Imagen path only if `HERO_AI_FALLBACK=true`.
- `blog/article_service.py:911-922` — same wiring change in the initial article-generation pipeline.

---

## Task 1: Licensing gate — write summary doc

**Why first:** the spec calls this a blocker. We document it now, Simon/Anika sign off, *then* Task 11 runs the ingestion that uploads to public storage.

**Files:**
- Create: `docs/beurer_asset_licensing.md`

- [ ] **Step 1: Read the licensing PDF**

Run: `ls "../client-beurer/02_CLIENT_INPUT/2026-04-19_academy_app_assets/_Beurer_Marketing Assets_Nutzungsbedingungen.pdf"`
Expected: file exists. Then read it with the Read tool (pages parameter if > 10 pages).

- [ ] **Step 2: Write the summary doc**

Template (fill in from PDF content):

```markdown
# Beurer Asset Licensing — Summary

**Source:** `_Beurer_Marketing Assets_Nutzungsbedingungen.pdf` (Academy App delivery, 2026-04-19)
**Summarized:** <date> by <name>
**Status:** <awaiting sign-off | signed off by <name> on <date>>

## Permitted uses

- <bullet list from PDF>

## Restrictions

- <bullet list from PDF>

## Attribution

- <required? what format?>

## Retention / deletion

- <any obligation to delete on contract end?>

## Public CDN serving (Supabase Storage)

- <explicitly permitted? infer from permitted uses>
- <risks / mitigations>

## Sign-off

- [ ] Simon reviewed <date>
- [ ] Anika confirmed public-CDN serving is within scope <date>
```

- [ ] **Step 3: Commit**

```bash
git add docs/beurer_asset_licensing.md
git commit -m "docs: Beurer asset licensing summary (hero image library gate)"
```

---

## Task 2: Filename parser

Pure function. Extracts `sku`, `type`, `gender`, `location` from an Academy App filename. No filesystem access, no network.

**Files:**
- Modify: `blog/stage2/image_prompts.py` (append new function)
- Create: `scripts/test_hero_library.py`

- [ ] **Step 1: Write the failing test**

Create `scripts/test_hero_library.py`:

```python
"""Lightweight assertion-based tests for the hero image library.

Run: python scripts/test_hero_library.py
Exits non-zero on first failure.
"""
import sys
from pathlib import Path

# Make the repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blog.stage2.image_prompts import parse_library_filename


def test_parse_product_use_with_location():
    r = parse_library_filename("bm49-use-female-kitchen-447-beurer.jpg")
    assert r == {
        "filename": "bm49-use-female-kitchen-447-beurer.jpg",
        "type": "product_use",
        "sku": "BM 49",
        "gender": "female",
        "location": "kitchen",
    }, r


def test_parse_product_use_no_location():
    r = parse_library_filename("bm27-use-male-024-beurer.jpg")
    assert r["sku"] == "BM 27" and r["gender"] == "male" and r["location"] is None, r


def test_parse_product_use_multi_gender():
    r = parse_library_filename("bm49-use-female-male-kitchen-369-beurer.jpg")
    assert r["sku"] == "BM 49" and r["location"] == "kitchen", r
    # gender may be "female" or "female-male" — pick "female" (first token)
    assert r["gender"] == "female", r


def test_parse_product_use_uppercase_sku():
    r = parse_library_filename("BM96-use-male-0183-beurer.jpg")
    assert r["sku"] == "BM 96", r


def test_parse_product_use_with_lang_suffix():
    # BC 54 has _de and _en variants — language suffix is ignored, treat as same shot
    r = parse_library_filename("bc54-use-female-239-beurer_de.jpg")
    assert r["sku"] == "BC 54" and r["gender"] == "female", r


def test_parse_lifestyle():
    r = parse_library_filename("lifestyle-female-pain-kitchen-9659-beurer.jpg")
    assert r == {
        "filename": "lifestyle-female-pain-kitchen-9659-beurer.jpg",
        "type": "lifestyle",
        "sku": None,
        "gender": "female",
        "location": "kitchen",
    }, r


def test_parse_skip_br_range():
    # BR range is baby monitors, out of scope
    r = parse_library_filename("br-range-520-2-beurer.jpg")
    assert r is None, r


def test_parse_skip_unknown_sku():
    r = parse_library_filename("xy99-use-male-001-beurer.jpg")
    assert r is None, r


if __name__ == "__main__":
    tests = [f for name, f in globals().items() if name.startswith("test_") and callable(f)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
            failed += 1
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python scripts/test_hero_library.py`
Expected: `ImportError: cannot import name 'parse_library_filename'`

- [ ] **Step 3: Implement `parse_library_filename` in `blog/stage2/image_prompts.py`**

Append to the end of the file:

```python
import re

# Known location tokens in Academy App filenames
_LOCATION_TOKENS = frozenset({
    "kitchen", "livingroom", "bedroom", "outdoor", "indoor",
    "yoga", "bathroom", "office", "garden",
})

# SKU prefixes we accept (must match PRODUCT_IMAGE_MAP keys stripped to prefix)
_VALID_SKU_PREFIXES = frozenset({
    "bm25", "bm27", "bm28", "bm35", "bm49", "bm51", "bm53", "bm54",
    "bm59", "bm64", "bm67", "bm81", "bm85", "bm96",
    "bc21", "bc27", "bc28", "bc54",
    "em39", "em49", "em50", "em55", "em59", "em80", "em89",
    "il50", "il60",
})


def _normalize_sku(raw: str) -> str | None:
    """Convert 'bm49' or 'BM49' to 'BM 49' if valid, else None."""
    raw = raw.lower()
    if raw not in _VALID_SKU_PREFIXES:
        return None
    # Split letters/digits: bm49 -> "BM 49"
    m = re.match(r"^([a-z]+)(\d+)$", raw)
    if not m:
        return None
    return f"{m.group(1).upper()} {m.group(2)}"


def parse_library_filename(filename: str) -> dict | None:
    """
    Parse an Academy App filename into structured metadata.

    Returns None for out-of-scope files (br-range, unknown SKU, unparseable).

    Filename patterns:
      - {sku}-use-{gender}[-{location}]-{id}-beurer.jpg           → product_use
      - {sku}-use-{gender}[-{gender2}]-{location}-{id}-beurer.jpg → product_use
      - lifestyle-{...context tokens...}-{id}-beurer.jpg          → lifestyle
      - br-range-*                                                 → None (out of scope)
    """
    name = filename.rsplit(".", 1)[0]  # drop extension
    # Drop optional language suffix (_de, _en) — treat as same shot
    name = re.sub(r"_(de|en)$", "", name)

    parts = name.split("-")
    if not parts:
        return None

    # Out of scope: baby monitor range
    if parts[0].lower() == "br":
        return None

    if parts[0] == "lifestyle":
        # Tokens after "lifestyle" up to the numeric id describe the scene.
        # Extract gender and location if present; everything else is context.
        gender = None
        location = None
        for tok in parts[1:]:
            if tok in ("female", "male") and gender is None:
                gender = tok
            elif tok in _LOCATION_TOKENS and location is None:
                location = tok
        return {
            "filename": filename,
            "type": "lifestyle",
            "sku": None,
            "gender": gender,
            "location": location,
        }

    # Product-use pattern: starts with SKU, then "use"
    sku = _normalize_sku(parts[0])
    if sku is None:
        return None
    if len(parts) < 2 or parts[1].lower() != "use":
        return None

    gender = None
    location = None
    for tok in parts[2:]:
        t = tok.lower()
        if t in ("female", "male") and gender is None:
            gender = t
        elif t in _LOCATION_TOKENS and location is None:
            location = t

    return {
        "filename": filename,
        "type": "product_use",
        "sku": sku,
        "gender": gender,
        "location": location,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python scripts/test_hero_library.py`
Expected: all 8 tests pass, exit 0.

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/image_prompts.py scripts/test_hero_library.py
git commit -m "feat(hero): filename parser for Academy App library"
```

---

## Task 3: SKU → theme seed map

When we ingest a product-use shot, we auto-tag it with the theme(s) it belongs to. This replaces vision-model theme guessing for product shots (where we already know the theme from the SKU).

**Files:**
- Modify: `blog/stage2/image_prompts.py`
- Modify: `scripts/test_hero_library.py`

- [ ] **Step 1: Append failing tests to `scripts/test_hero_library.py`**

```python
from blog.stage2.image_prompts import themes_for_sku


def test_themes_for_bm_sku():
    assert themes_for_sku("BM 27") == ["blutdruck"]
    assert themes_for_sku("BM 96") == ["blutdruck"]


def test_themes_for_bc_sku():
    assert themes_for_sku("BC 54") == ["blutdruck"]


def test_themes_for_em_menstrual():
    assert themes_for_sku("EM 50") == ["regelschmerzen"]
    assert themes_for_sku("EM 55") == ["regelschmerzen"]


def test_themes_for_em_tens():
    assert themes_for_sku("EM 59") == ["tens_ems"]
    assert themes_for_sku("EM 89") == ["tens_ems"]


def test_themes_for_il_sku():
    assert themes_for_sku("IL 50") == ["infrarot"]


def test_themes_for_unknown_sku():
    assert themes_for_sku("XY 99") == []


def test_themes_for_none_sku():
    assert themes_for_sku(None) == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python scripts/test_hero_library.py`
Expected: `ImportError: cannot import name 'themes_for_sku'`

- [ ] **Step 3: Implement `themes_for_sku`**

Append to `blog/stage2/image_prompts.py`:

```python
# SKU → theme seed. When we ingest a product-use shot for one of these SKUs,
# this is the theme tag assigned automatically (replaces vision-model guessing
# since the SKU already pins the category).
_SKU_THEMES = {
    # Blood pressure — arm + wrist cuffs
    ("bm", None): ["blutdruck"],
    ("bc", None): ["blutdruck"],
    # Menstrual TENS
    ("em", "50"): ["regelschmerzen"],
    ("em", "55"): ["regelschmerzen"],
    # Classic TENS/EMS
    ("em", "39"): ["tens_ems"],
    ("em", "49"): ["tens_ems"],
    ("em", "59"): ["tens_ems"],
    ("em", "80"): ["tens_ems"],
    ("em", "89"): ["tens_ems"],
    # Infrared lamps
    ("il", None): ["infrarot"],
}


def themes_for_sku(sku: str | None) -> list[str]:
    """Return the list of theme tags for a SKU (e.g. 'BM 27' → ['blutdruck'])."""
    if not sku:
        return []
    parts = sku.lower().split()
    if len(parts) != 2:
        return []
    prefix, number = parts[0], parts[1]
    # Try exact (prefix, number) first
    if (prefix, number) in _SKU_THEMES:
        return list(_SKU_THEMES[(prefix, number)])
    # Fall back to prefix-only
    if (prefix, None) in _SKU_THEMES:
        return list(_SKU_THEMES[(prefix, None)])
    return []
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python scripts/test_hero_library.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/image_prompts.py scripts/test_hero_library.py
git commit -m "feat(hero): SKU→theme seed map"
```

---

## Task 4: First-SKU-in-headline extractor

Scans the article headline (then primary_keyword) and returns the SKU that appears *first in reading order*. Drives Branch A of the selector.

**Files:**
- Modify: `blog/stage2/image_prompts.py`
- Modify: `scripts/test_hero_library.py`

- [ ] **Step 1: Append failing tests**

```python
from blog.stage2.image_prompts import first_sku_in_article


def test_first_sku_single():
    assert first_sku_in_article({"Headline": "BM 27 im Test"}) == "BM 27"


def test_first_sku_earliest_in_headline():
    # "BM 35" appears before "BM 27" in reading order → BM 35 wins
    assert first_sku_in_article({"Headline": "BM 35 vs BM 27: Welches Gerät?"}) == "BM 35"


def test_first_sku_tolerates_missing_space():
    assert first_sku_in_article({"Headline": "BM27 Anleitung"}) == "BM 27"


def test_first_sku_case_insensitive():
    assert first_sku_in_article({"Headline": "bm 49 für die Küche"}) == "BM 49"


def test_first_sku_falls_back_to_keyword():
    article = {"Headline": "Bluthochdruck senken", "primary_keyword": "BM 96 EKG Messung"}
    assert first_sku_in_article(article) == "BM 96"


def test_first_sku_none_when_absent():
    article = {"Headline": "Regelschmerzen lindern", "primary_keyword": "Menstruation Tipps"}
    assert first_sku_in_article(article) is None


def test_first_sku_ignores_body_content():
    # Body may mention SKUs but we only look at headline + keyword
    article = {"Headline": "Gesunde Ernährung", "primary_keyword": "", "section_1_content": "BM 27 ist toll"}
    assert first_sku_in_article(article) is None
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python scripts/test_hero_library.py`
Expected: ImportError for `first_sku_in_article`.

- [ ] **Step 3: Implement `first_sku_in_article`**

Append to `blog/stage2/image_prompts.py`:

```python
# Precompiled SKU regex: matches "BM 27", "BM27", "bm 27", "bm27", etc.
# Uses _VALID_SKU_PREFIXES from earlier. Alternation sorted by length desc
# so that e.g. BM 51 SL doesn't get partially matched (not currently in
# _VALID_SKU_PREFIXES but future-proof).
def _build_sku_regex() -> "re.Pattern":
    # Each prefix entry becomes e.g. bm \s* 27
    patterns = []
    for p in sorted(_VALID_SKU_PREFIXES, key=len, reverse=True):
        m = re.match(r"^([a-z]+)(\d+)$", p)
        if m:
            patterns.append(rf"{m.group(1)}\s*{m.group(2)}")
    alt = "|".join(patterns)
    return re.compile(rf"\b({alt})\b", re.IGNORECASE)


_SKU_REGEX = _build_sku_regex()


def _first_sku_in_text(text: str) -> str | None:
    """Find the SKU that appears earliest in `text`. Returns 'BM 27' format."""
    if not text:
        return None
    m = _SKU_REGEX.search(text)
    if not m:
        return None
    raw = m.group(1).lower().replace(" ", "")
    return _normalize_sku(raw)


def first_sku_in_article(article: dict) -> str | None:
    """
    Return the first SKU mentioned in the article's headline (reading order);
    if none, search primary_keyword. Returns None if no SKU is named.
    Ignores body content — headline/keyword only.
    """
    headline = article.get("Headline") or article.get("headline") or ""
    hit = _first_sku_in_text(headline)
    if hit:
        return hit
    keyword = article.get("primary_keyword") or article.get("keyword") or ""
    return _first_sku_in_text(keyword)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `python scripts/test_hero_library.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/image_prompts.py scripts/test_hero_library.py
git commit -m "feat(hero): first-SKU-in-headline extractor"
```

---

## Task 5: Migrate existing 22 lifestyle entries to new schema

Add `sku: null`, `type: "lifestyle"`, `gender`, `location` to each existing entry. Keep everything else (scene, mood, themes) unchanged.

**Files:**
- Modify: `blog/stage2/lifestyle_images.json`

- [ ] **Step 1: Write a migration helper and run it**

Create `scripts/migrate_lifestyle_schema.py`:

```python
"""One-shot migration: add sku/type/gender/location fields to existing entries.

Re-runnable — entries that already have the fields are skipped.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blog.stage2.image_prompts import parse_library_filename

JSON_PATH = Path(__file__).resolve().parent.parent / "blog" / "stage2" / "lifestyle_images.json"


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)

    changed = 0
    for e in entries:
        if "type" in e and "sku" in e:
            continue  # already migrated
        parsed = parse_library_filename(e["filename"])
        if parsed is None:
            # Unparseable: mark as lifestyle with unknowns
            e.setdefault("type", "lifestyle")
            e.setdefault("sku", None)
            e.setdefault("gender", None)
            e.setdefault("location", None)
        else:
            e.setdefault("type", parsed["type"])
            e.setdefault("sku", parsed["sku"])
            e.setdefault("gender", parsed["gender"])
            e.setdefault("location", parsed["location"])
        changed += 1

    # Sort by filename for stable diffs
    entries.sort(key=lambda e: e["filename"])

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Migrated {changed} entries ({len(entries)} total)")


if __name__ == "__main__":
    main()
```

Run: `python scripts/migrate_lifestyle_schema.py`
Expected: `Migrated 22 entries (22 total)` (or similar if the count has drifted).

- [ ] **Step 2: Spot-check the diff**

Run: `git diff blog/stage2/lifestyle_images.json | head -60`
Expected: every entry now has `type`, `sku`, `gender`, `location` fields; scene/mood/themes unchanged.

- [ ] **Step 3: Commit**

```bash
git add blog/stage2/lifestyle_images.json scripts/migrate_lifestyle_schema.py
git commit -m "refactor(hero): extend lifestyle_images.json schema with sku/type/gender/location"
```

---

## Task 6: Library loader update

The existing `load_lifestyle_images()` returns a list of dicts. No functional change needed — it already reads whatever's in the JSON. This task adds a filtered helper so later tasks don't each re-implement "give me all product_use entries for SKU X."

**Files:**
- Modify: `blog/stage2/image_prompts.py`
- Modify: `scripts/test_hero_library.py`

- [ ] **Step 1: Append failing tests**

```python
from blog.stage2.image_prompts import library_candidates


def test_library_candidates_by_sku():
    # SKU filter returns only product_use entries with matching sku
    results = library_candidates(sku="BM 27")
    # Either 0 (JSON not yet ingested) or all entries have sku=="BM 27" and type=="product_use"
    for r in results:
        assert r["sku"] == "BM 27", r
        assert r["type"] == "product_use", r


def test_library_candidates_by_theme():
    # Theme filter returns only lifestyle entries tagged with that theme
    results = library_candidates(theme="regelschmerzen")
    for r in results:
        assert r["type"] == "lifestyle", r
        assert "regelschmerzen" in r.get("themes", []), r
```

- [ ] **Step 2: Run tests**

Run: `python scripts/test_hero_library.py`
Expected: `ImportError: cannot import name 'library_candidates'`

- [ ] **Step 3: Implement `library_candidates`**

Append to `blog/stage2/image_prompts.py`:

```python
def library_candidates(sku: str | None = None, theme: str | None = None) -> list[dict]:
    """
    Filter the hero image library.

    - sku given → return product_use entries for that SKU
    - theme given → return lifestyle entries tagged with that theme
    - both None → empty list
    """
    if not sku and not theme:
        return []
    entries = load_lifestyle_images()
    if sku:
        return [e for e in entries if e.get("type") == "product_use" and e.get("sku") == sku]
    return [e for e in entries if e.get("type") == "lifestyle" and theme in (e.get("themes") or [])]
```

- [ ] **Step 4: Run tests**

Run: `python scripts/test_hero_library.py`
Expected: all tests pass (results may be empty — that's fine, the assertion is a no-op over empty iterables).

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/image_prompts.py scripts/test_hero_library.py
git commit -m "feat(hero): library_candidates filter helper"
```

---

## Task 7: Scorer extracted into a reusable helper

`select_lifestyle_reference` already contains keyword-overlap scoring with hash tiebreak. Refactor the scoring body into a pure helper that `select_hero_image` can call directly.

**Files:**
- Modify: `blog/stage2/image_prompts.py`
- Modify: `scripts/test_hero_library.py`

- [ ] **Step 1: Append failing test**

```python
from blog.stage2.image_prompts import pick_best_candidate


def test_pick_best_candidate_single():
    candidates = [{"filename": "a.jpg", "scene": "woman in kitchen", "mood": "pained", "setting": "kitchen"}]
    article = {"Headline": "Regelschmerzen in der Küche"}
    r = pick_best_candidate(candidates, article)
    assert r["filename"] == "a.jpg"


def test_pick_best_candidate_scores_keyword_overlap():
    candidates = [
        {"filename": "a.jpg", "scene": "outdoor yoga", "mood": "happy", "setting": "outdoor"},
        {"filename": "b.jpg", "scene": "kitchen pain", "mood": "unwell", "setting": "kitchen"},
    ]
    article = {"Headline": "Kitchen pain relief"}
    r = pick_best_candidate(candidates, article)
    assert r["filename"] == "b.jpg", r


def test_pick_best_candidate_deterministic_tie_break():
    # Two candidates tied on score → hash-based pick is stable for same headline
    candidates = [
        {"filename": "a.jpg", "scene": "x", "mood": "", "setting": ""},
        {"filename": "b.jpg", "scene": "x", "mood": "", "setting": ""},
    ]
    article = {"Headline": "Totally unrelated"}
    r1 = pick_best_candidate(candidates, article)
    r2 = pick_best_candidate(candidates, article)
    assert r1["filename"] == r2["filename"], "non-deterministic tiebreak"


def test_pick_best_candidate_empty():
    assert pick_best_candidate([], {"Headline": "x"}) is None
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python scripts/test_hero_library.py`
Expected: `ImportError: cannot import name 'pick_best_candidate'`

- [ ] **Step 3: Extract `pick_best_candidate` and refactor `select_lifestyle_reference` to use it**

Locate `select_lifestyle_reference` in `blog/stage2/image_prompts.py`. Replace its body with a call to the new helper. Add the helper above it:

```python
def pick_best_candidate(candidates: list[dict], article: dict) -> dict | None:
    """
    Score candidates by keyword overlap against article headline+keyword,
    break ties with headline hash. Returns the best candidate or None if
    candidates is empty.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    headline = (article.get("Headline", "") or article.get("headline", "") or "").lower()
    keyword = (article.get("primary_keyword", "") or article.get("keyword", "") or "").lower()
    article_tokens = set(
        w for w in f"{headline} {keyword}".split()
        if len(w) > 2 and w not in _STOPWORDS
    )

    if not article_tokens:
        topic = headline or keyword or "default"
        idx = int(hashlib.md5(topic.encode()).hexdigest(), 16) % len(candidates)
        return candidates[idx]

    scored = []
    for img in candidates:
        img_text = f"{img.get('scene', '')} {img.get('mood', '')} {img.get('setting', '')}".lower()
        score = sum(1 for token in article_tokens if token in img_text)
        scored.append((score, img))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]
    tied = [img for score, img in scored if score == top_score]
    topic = headline or keyword or "default"
    idx = int(hashlib.md5(topic.encode()).hexdigest(), 16) % len(tied)
    return tied[idx]
```

Then change `select_lifestyle_reference` to delegate — replace its body (keep the signature and logging) with:

```python
def select_lifestyle_reference(article: dict, theme: str) -> Optional[dict]:
    images = load_lifestyle_images()
    if not images:
        return None
    candidates = [img for img in images if theme in img.get("themes", [])]
    if not candidates:
        candidates = [img for img in images if "default" in img.get("themes", [])]
    selected = pick_best_candidate(candidates, article)
    if selected:
        logger.info(f"Selected lifestyle reference: {selected['filename']}")
    return selected
```

- [ ] **Step 4: Run tests**

Run: `python scripts/test_hero_library.py`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/image_prompts.py scripts/test_hero_library.py
git commit -m "refactor(hero): extract pick_best_candidate from select_lifestyle_reference"
```

---

## Task 8: Library URL builder + alt-text builder

Returns the public URL for a filename in `blog-images/library/`. Alt text is the caption's `scene`, translated to German if the article language is `"de"`. Translation falls back to English on failure.

**Files:**
- Modify: `blog/stage2/image_prompts.py`
- Modify: `scripts/test_hero_library.py`

- [ ] **Step 1: Append failing tests**

```python
from blog.stage2.image_prompts import library_image_url, build_hero_alt_text


def test_library_image_url_returns_string_for_valid_filename():
    # Requires BEURER_SUPABASE_URL + KEY in env — if not configured returns "" (logged)
    url = library_image_url("bm27-use-male-024-beurer.jpg")
    assert isinstance(url, str)
    if url:
        assert "bm27-use-male-024-beurer.jpg" in url
        assert "library" in url


def test_build_hero_alt_text_en_passthrough():
    entry = {"scene": "A woman relaxes on a sofa with tea"}
    alt = build_hero_alt_text(entry, language="en")
    assert alt == "A woman relaxes on a sofa with tea"


def test_build_hero_alt_text_de_translates_or_falls_back():
    entry = {"scene": "A woman relaxes on a sofa with tea"}
    alt = build_hero_alt_text(entry, language="de")
    # Either a German translation or the original English string (fallback)
    assert len(alt) > 0
    assert isinstance(alt, str)


def test_build_hero_alt_text_empty_scene():
    alt = build_hero_alt_text({}, language="en")
    assert alt == ""
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python scripts/test_hero_library.py`
Expected: ImportError for `library_image_url` / `build_hero_alt_text`.

- [ ] **Step 3: Implement both functions**

Append to `blog/stage2/image_prompts.py`:

```python
# Supabase Storage folder for real-photo library
_LIBRARY_BUCKET = "blog-images"
_LIBRARY_FOLDER = "library"


def library_image_url(filename: str) -> str:
    """Public URL for a file in blog-images/library/. Returns '' on failure."""
    try:
        from db.client import get_beurer_supabase
        sb = get_beurer_supabase()
        return sb.storage.from_(_LIBRARY_BUCKET).get_public_url(f"{_LIBRARY_FOLDER}/{filename}")
    except Exception as e:
        logger.warning(f"Could not build library URL for {filename}: {e}")
        return ""


# Cache for alt-text translations: key = (filename, language) → translated string
_ALT_TEXT_CACHE: dict[tuple[str, str], str] = {}


def build_hero_alt_text(entry: dict, language: str = "de") -> str:
    """
    Build accessibility alt text for a hero image.

    - English scene from the captioner passes through for language='en'.
    - For 'de', translate via Gemini 2.0 Flash, cached by (filename, language).
    - On translation failure, fall back to the English scene (never return empty
      when scene is non-empty — accessibility requirement).
    """
    scene = (entry.get("scene") or "").strip()
    if not scene:
        return ""
    if language != "de":
        return scene

    filename = entry.get("filename") or ""
    key = (filename, language)
    if key in _ALT_TEXT_CACHE:
        return _ALT_TEXT_CACHE[key]

    try:
        from google import genai
        import os
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        prompt = (
            "Translate the following English image description to German. "
            "Return ONLY the translation, no quotes, no explanation, no prefix.\n\n"
            f"English: {scene}"
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"temperature": 0.1, "max_output_tokens": 256},
        )
        translated = (response.text or "").strip().strip('"').strip()
        if translated:
            _ALT_TEXT_CACHE[key] = translated
            return translated
    except Exception as e:
        logger.warning(f"Alt-text DE translation failed for {filename}: {e}; using English fallback")

    # Fallback: English scene rather than empty alt
    _ALT_TEXT_CACHE[key] = scene
    return scene
```

- [ ] **Step 4: Run tests**

Run: `python scripts/test_hero_library.py`
Expected: all tests pass. `test_library_image_url_returns_string_for_valid_filename` may log a warning if Supabase isn't configured in the test env — that's acceptable (returns `""`, test still asserts `isinstance(str)`).

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/image_prompts.py scripts/test_hero_library.py
git commit -m "feat(hero): library URL + alt-text builder with DE translation"
```

---

## Task 9: `select_hero_image()` orchestration

Ties it all together. Branch A (SKU) → Branch B (mood) → None. Returns `{filename, url, alt_text, source}` or None.

**Files:**
- Modify: `blog/stage2/image_prompts.py`
- Modify: `scripts/test_hero_library.py`

- [ ] **Step 1: Append failing tests**

```python
from blog.stage2.image_prompts import select_hero_image
import json
from pathlib import Path


def _stub_library_with(entries):
    """Helper: temporarily replace the cached library with test entries."""
    import blog.stage2.image_prompts as mod
    mod._lifestyle_images_cache = entries


def _clear_library_cache():
    import blog.stage2.image_prompts as mod
    mod._lifestyle_images_cache = None


def test_select_branch_a_hit():
    _stub_library_with([
        {"filename": "bm27-use-male-024-beurer.jpg", "type": "product_use", "sku": "BM 27",
         "gender": "male", "location": None, "scene": "Man measures BP in bright living room",
         "mood": "calm", "lighting": "", "colors": "", "composition": "", "setting": "livingroom",
         "themes": ["blutdruck"]},
    ])
    try:
        r = select_hero_image({"Headline": "BM 27 Testbericht", "language": "de"})
        assert r is not None
        assert r["filename"] == "bm27-use-male-024-beurer.jpg"
        assert r["source"] == "product_use"
        assert r["alt_text"]  # non-empty
    finally:
        _clear_library_cache()


def test_select_branch_a_miss_falls_through_to_mood():
    # SKU named but no product_use entry for it → fall through to mood lifestyle
    _stub_library_with([
        {"filename": "lifestyle-female-pain-livingroom-0217-beurer.jpg", "type": "lifestyle",
         "sku": None, "gender": "female", "location": "livingroom",
         "scene": "Woman resting on sofa with tea", "mood": "unwell", "lighting": "",
         "colors": "", "composition": "", "setting": "livingroom",
         "themes": ["regelschmerzen", "default"]},
    ])
    try:
        # BM 81 has no product_use entry in the stubbed library; theme=blutdruck has no lifestyle match either → None
        r = select_hero_image({"Headline": "BM 81 Testbericht", "language": "de"})
        assert r is None  # no blutdruck lifestyle entry stubbed
    finally:
        _clear_library_cache()


def test_select_branch_b_mood():
    _stub_library_with([
        {"filename": "lifestyle-female-pain-livingroom-0217-beurer.jpg", "type": "lifestyle",
         "sku": None, "gender": "female", "location": "livingroom",
         "scene": "Woman on sofa", "mood": "unwell", "lighting": "", "colors": "",
         "composition": "", "setting": "livingroom",
         "themes": ["regelschmerzen"]},
    ])
    try:
        r = select_hero_image({"Headline": "Regelschmerzen lindern", "language": "de"})
        assert r is not None
        assert r["source"] == "lifestyle"
        assert r["filename"].startswith("lifestyle-")
    finally:
        _clear_library_cache()


def test_select_none_when_both_branches_empty():
    _stub_library_with([])
    try:
        r = select_hero_image({"Headline": "Gesundheit allgemein", "language": "de"})
        assert r is None
    finally:
        _clear_library_cache()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python scripts/test_hero_library.py`
Expected: ImportError for `select_hero_image`.

- [ ] **Step 3: Implement `select_hero_image`**

Append to `blog/stage2/image_prompts.py`:

```python
def select_hero_image(article: dict) -> dict | None:
    """
    Select a real photo hero for an article.

    Returns {filename, url, alt_text, source} or None if no match.
    source is 'product_use' | 'lifestyle'.

    Branch A: if headline/keyword names a SKU with a product_use photo → use it.
    Branch B: else pick a lifestyle shot matching the detected theme.
    Otherwise: None (caller decides whether to fall through to AI).
    """
    language = article.get("language", "de")

    # Branch A
    sku = first_sku_in_article(article)
    if sku:
        candidates = library_candidates(sku=sku)
        if candidates:
            chosen = pick_best_candidate(candidates, article)
            if chosen:
                url = library_image_url(chosen["filename"])
                if url:
                    logger.info(f"Hero select (product_use): sku={sku} file={chosen['filename']}")
                    return {
                        "filename": chosen["filename"],
                        "url": url,
                        "alt_text": build_hero_alt_text(chosen, language=language),
                        "source": "product_use",
                    }

    # Branch B
    theme = detect_theme(article)
    candidates = library_candidates(theme=theme)
    if not candidates:
        candidates = library_candidates(theme="default")
    if candidates:
        chosen = pick_best_candidate(candidates, article)
        if chosen:
            url = library_image_url(chosen["filename"])
            if url:
                logger.info(f"Hero select (lifestyle): theme={theme} file={chosen['filename']}")
                return {
                    "filename": chosen["filename"],
                    "url": url,
                    "alt_text": build_hero_alt_text(chosen, language=language),
                    "source": "lifestyle",
                }

    logger.info("Hero select: no match")
    return None
```

- [ ] **Step 4: Run tests**

Run: `python scripts/test_hero_library.py`
Expected: all tests pass. The `url` assertion may be falsy if Supabase isn't configured — in that case `select_hero_image` returns None and the first test will fail. Work around by monkeypatching `library_image_url` in the test (see below if this trips).

If the test fails due to empty URL, add this shim at the top of the test module:

```python
import blog.stage2.image_prompts as _ip
_ip.library_image_url = lambda f: f"https://stub.example/{f}"
```

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/image_prompts.py scripts/test_hero_library.py
git commit -m "feat(hero): select_hero_image orchestration (Branch A → Branch B → None)"
```

---

## Task 10: Ingestion script

Walks a source directory, parses filenames, uploads binaries to Supabase Storage, runs the vision captioner on each, upserts into `lifestyle_images.json`. Idempotent.

**Files:**
- Create: `scripts/ingest_hero_library.py`

- [ ] **Step 1: Write the ingestion script**

```python
"""Ingest an image pack into the hero image library.

Usage:
  python scripts/ingest_hero_library.py --source-dir <path> [--dry-run]

Idempotent: files already in lifestyle_images.json are skipped.
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blog.stage2.image_prompts import parse_library_filename, themes_for_sku

JSON_PATH = Path(__file__).resolve().parent.parent / "blog" / "stage2" / "lifestyle_images.json"
BUCKET = "blog-images"
FOLDER = "library"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("ingest")


def caption_image(image_bytes: bytes) -> dict:
    """Return a dict with scene/mood/lighting/colors/composition/setting."""
    from google import genai
    from google.genai import types
    import os
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = (
        "Describe this photograph as JSON with these exact fields:\n"
        '{"scene": "one sentence describing the main subject and action",\n'
        ' "mood": "comma-separated adjectives describing the emotional tone",\n'
        ' "lighting": "one sentence about light quality and direction",\n'
        ' "colors": "comma-separated dominant colors",\n'
        ' "composition": "one sentence about framing and perspective",\n'
        ' "setting": "one sentence about the environment"}\n'
        "Return only the JSON object, no code fences, no prose."
    )
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")],
        config={"temperature": 0.2, "max_output_tokens": 512},
    )
    text = (response.text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    return json.loads(text)


def upload_to_storage(image_bytes: bytes, filename: str, dry_run: bool) -> None:
    if dry_run:
        log.info(f"[dry-run] would upload {filename} ({len(image_bytes)} bytes)")
        return
    from db.client import get_beurer_supabase
    sb = get_beurer_supabase()
    sb.storage.from_(BUCKET).upload(
        path=f"{FOLDER}/{filename}",
        file=image_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "true"},
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.source_dir.is_dir():
        log.error(f"Not a directory: {args.source_dir}")
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)
    by_filename = {e["filename"]: e for e in entries}

    added = skipped_existing = skipped_out_of_scope = 0
    for img_path in sorted(args.source_dir.glob("*.jpg")) + sorted(args.source_dir.glob("*.JPG")):
        filename = img_path.name
        if filename in by_filename:
            skipped_existing += 1
            continue
        parsed = parse_library_filename(filename)
        if parsed is None:
            log.info(f"skip (out of scope): {filename}")
            skipped_out_of_scope += 1
            continue

        log.info(f"ingest: {filename} → sku={parsed['sku']} type={parsed['type']}")

        image_bytes = img_path.read_bytes()
        upload_to_storage(image_bytes, filename, args.dry_run)

        if args.dry_run:
            caption = {"scene": "(dry-run stub)", "mood": "", "lighting": "",
                       "colors": "", "composition": "", "setting": ""}
        else:
            try:
                caption = caption_image(image_bytes)
            except Exception as e:
                log.error(f"caption failed for {filename}: {e}")
                continue

        themes = themes_for_sku(parsed["sku"]) if parsed["type"] == "product_use" else []

        entry = {
            "filename": filename,
            "type": parsed["type"],
            "sku": parsed["sku"],
            "gender": parsed["gender"],
            "location": parsed["location"],
            "scene": caption.get("scene", ""),
            "mood": caption.get("mood", ""),
            "lighting": caption.get("lighting", ""),
            "colors": caption.get("colors", ""),
            "composition": caption.get("composition", ""),
            "setting": caption.get("setting", ""),
            "themes": themes,
        }
        by_filename[filename] = entry
        added += 1

    # Rewrite JSON, sorted by filename
    out = sorted(by_filename.values(), key=lambda e: e["filename"])
    if args.dry_run:
        log.info(f"[dry-run] would write {len(out)} entries to {JSON_PATH}")
    else:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
            f.write("\n")

    log.info(f"Summary: added={added} skipped_existing={skipped_existing} skipped_oos={skipped_out_of_scope}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run the script to verify parsing**

Run: `python scripts/ingest_hero_library.py --source-dir "../client-beurer/02_CLIENT_INPUT/2026-04-19_academy_app_assets" --dry-run`
Expected:
- `[dry-run] would upload bc54-use-...` for 41 product-use shots
- `skip (out of scope): br-range-...` for 3 BR files
- `skipped_existing=22` for the lifestyle files already in JSON
- No tracebacks

- [ ] **Step 3: Commit**

```bash
git add scripts/ingest_hero_library.py
git commit -m "feat(hero): ingestion script for Academy App library"
```

---

## Task 11: Run ingestion (manual, one-shot, gated on licensing)

**Gate:** Task 1 licensing sign-off must be complete before this step runs.

**Files:**
- Modify: `blog/stage2/lifestyle_images.json` (regenerated by the script)

- [ ] **Step 1: Confirm licensing sign-off**

Open `docs/beurer_asset_licensing.md` and verify both sign-off checkboxes are checked. If not, stop and return to Task 1.

- [ ] **Step 2: Run the ingestion for real**

Run: `python scripts/ingest_hero_library.py --source-dir "../client-beurer/02_CLIENT_INPUT/2026-04-19_academy_app_assets"`
Expected log line at end: `Summary: added=41 skipped_existing=22 skipped_oos=3`

- [ ] **Step 3: Sanity-check the JSON**

Run: `python -c "import json; d=json.load(open('blog/stage2/lifestyle_images.json')); print('total:', len(d)); print('product_use:', sum(1 for e in d if e['type']=='product_use')); print('skus:', sorted({e['sku'] for e in d if e['sku']}))"`
Expected: `total: 63`, `product_use: 41`, skus list: `['BC 54', 'BM 27', 'BM 35', 'BM 49', 'BM 96', 'EM 50', 'EM 55', 'EM 89']`

- [ ] **Step 4: Spot-check one uploaded image**

Pick one filename from the JSON (`bm27-use-male-024-beurer.jpg`). Open `https://<supabase-project>.supabase.co/storage/v1/object/public/blog-images/library/bm27-use-male-024-beurer.jpg` in a browser. Expected: the image loads.

- [ ] **Step 5: Commit**

```bash
git add blog/stage2/lifestyle_images.json
git commit -m "chore(hero): ingest 41 Academy App product-use shots"
```

---

## Task 12: Wire `select_hero_image` into the endpoint

`POST /api/v1/blog/articles/{id}/generate-hero-image` calls `select_hero_image` first. On hit, skips Imagen entirely. On miss, falls back to Imagen only if `HERO_AI_FALLBACK=true`; otherwise clears the hero and re-renders the HTML without it.

**Files:**
- Modify: `blog/router.py:453-554`

- [ ] **Step 1: Rewrite the endpoint**

Replace lines 453-554 of `blog/router.py` with:

```python
@router.post("/articles/{article_id}/generate-hero-image")
async def generate_hero_image(article_id: str):
    """
    Attach a hero image to an article.

    Strategy:
      1. Try real-photo library (Academy App + future PostAP) via select_hero_image.
      2. On miss, fall back to Imagen 4.0 only if HERO_AI_FALLBACK=true.
      3. Otherwise clear the hero and re-render HTML without one.

    Article text is never rewritten — only image_01_url, image_01_alt_text,
    and article_html change.
    """
    import os
    from db.client import get_beurer_supabase
    from .stage2.image_prompts import (
        select_hero_image,
        detect_theme,
        build_beurer_hero_prompt,
        select_lifestyle_reference,
    )
    from .stage2.image_creator import ImageCreator
    from .shared.html_renderer import HTMLRenderer

    supabase = get_beurer_supabase()

    # 1. Fetch article
    result = (
        supabase.table("blog_articles")
        .select("*")
        .eq("id", article_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Article not found")

    row = result.data[0]
    article_json = row.get("article_json")
    if not article_json:
        raise HTTPException(status_code=400, detail="Article has no article_json")

    # 2. Try library first
    selection = select_hero_image(article_json)
    if selection:
        source = selection["source"]  # 'product_use' | 'lifestyle'
        image_url = selection["url"]
        alt_text = selection["alt_text"]
        logger.info(f"Hero from library: article={article_id} source={source} file={selection['filename']}")
    else:
        # 3. Library miss — AI fallback only if enabled
        if os.getenv("HERO_AI_FALLBACK", "false").lower() == "true":
            theme = detect_theme(article_json)
            style_ref = select_lifestyle_reference(article_json, theme)
            prompt = build_beurer_hero_prompt(article_json, style_ref=style_ref)
            logger.info(f"Hero AI fallback for article={article_id} theme={theme}")

            import asyncio as _aio
            creator = ImageCreator()
            image_url = await creator.generate_async(prompt, aspect_ratio="16:9")
            if not image_url:
                logger.warning(f"Hero AI attempt 1 failed for {article_id}, retrying...")
                await _aio.sleep(2)
                image_url = await creator.generate_async(prompt, aspect_ratio="16:9")
            if not image_url:
                raise HTTPException(status_code=502, detail="AI hero generation failed after retry")

            headline = article_json.get("Headline", "") or article_json.get("headline", "")
            alt_text = f"Beurer Magazin: {headline}"[:125]
            source = "ai"
        else:
            # 4. No library match, AI disabled → render without hero
            image_url = ""
            alt_text = ""
            source = "none"
            logger.info(f"Hero omitted for article={article_id} (no library match, AI fallback disabled)")

    # 5. Update article_json
    article_json["image_01_url"] = image_url
    article_json["image_01_alt_text"] = alt_text

    # 6. Re-render HTML (article text unchanged)
    author_data = None
    author_id = row.get("author_id")
    if author_id:
        try:
            author_result = (
                supabase.table("blog_authors")
                .select("name, title, bio, image_url, credentials, linkedin_url")
                .eq("id", author_id)
                .limit(1)
                .execute()
            )
            if author_result.data:
                author_data = author_result.data[0]
        except Exception:
            pass

    article_category = (row.get("social_context") or {}).get("category", "")
    article_html = HTMLRenderer.render(
        article=article_json,
        company_name="Beurer",
        company_url="https://www.beurer.com",
        language=row.get("language", "de"),
        category=article_category,
        author=author_data,
    )

    # 7. Save
    supabase.table("blog_articles").update({
        "article_json": article_json,
        "article_html": article_html,
        "updated_at": datetime.utcnow().isoformat(),
    }).eq("id", article_id).execute()

    return {
        "article_id": article_id,
        "source": source,
        "image_url": image_url,
        "alt_text": alt_text,
    }
```

- [ ] **Step 2: Restart the dev server and smoke-test against a known article**

Run in one terminal: `python dev.py` (auto-kills any process on port 8000 per `CLAUDE.md`)

In another terminal, pick a recent article ID from the DB:
```bash
curl -s -X POST http://localhost:8000/api/v1/blog/articles/<article-id>/generate-hero-image | python -m json.tool
```
Expected JSON response with `source: "product_use"` or `"lifestyle"` or `"none"` (never `"ai"` unless `HERO_AI_FALLBACK=true` is set).

- [ ] **Step 3: Verify the HTML renders without a hero when source=="none"**

Use a test article whose headline has no SKU and whose theme has no lifestyle matches (force if needed). Confirm the dashboard iframe renders the article without a broken `<img>` element.

- [ ] **Step 4: Commit**

```bash
git add blog/router.py
git commit -m "feat(hero): library-first hero selection in generate-hero-image endpoint"
```

---

## Task 13: Wire `select_hero_image` into the initial pipeline

`blog/article_service.py:911-922` generates heroes during initial article creation. Same library-first logic.

**Files:**
- Modify: `blog/article_service.py:911-922` (and any surrounding lines needed)

- [ ] **Step 1: Read the current block**

Run: open `blog/article_service.py`, navigate to line ~911, read the hero-generation block (~50 lines of context).

- [ ] **Step 2: Replace the hero block**

Change the existing `try:` block (approx lines 913-940) that imports `build_beurer_hero_prompt` to:

```python
    # Hero image — library first, AI fallback behind flag
    try:
        import os as _os
        from .stage2.image_prompts import (
            select_hero_image,
            detect_theme,
            build_beurer_hero_prompt,
            select_lifestyle_reference,
        )
        from .stage2.image_creator import ImageCreator

        selection = select_hero_image(article)
        if selection:
            article["image_01_url"] = selection["url"]
            article["image_01_alt_text"] = selection["alt_text"]
            logger.info(f"Hero from library: id={article_id} source={selection['source']} file={selection['filename']}")
        elif _os.getenv("HERO_AI_FALLBACK", "false").lower() == "true":
            theme = detect_theme(article)
            style_ref = select_lifestyle_reference(article, theme)
            prompt = build_beurer_hero_prompt(article, style_ref=style_ref)
            logger.info(f"Hero AI fallback: id={article_id} theme={theme}")
            creator = ImageCreator()
            image_url = await creator.generate_async(prompt, aspect_ratio="16:9")
            if not image_url:
                await asyncio.sleep(2)
                image_url = await creator.generate_async(prompt, aspect_ratio="16:9")
            if image_url:
                article["image_01_url"] = image_url
                headline = article.get("Headline", "") or article.get("headline", "")
                article["image_01_alt_text"] = f"Beurer Magazin: {headline}"[:125]
        else:
            logger.info(f"Hero omitted: id={article_id} (no library match, AI fallback disabled)")
            article["image_01_url"] = ""
            article["image_01_alt_text"] = ""
    except Exception as e:
        logger.exception(f"Hero image step failed for {article_id}: {e}")
```

Verify `asyncio` and `logger` are already imported at the top of the file (they should be — grep first).

- [ ] **Step 3: Smoke-test the pipeline**

Trigger a fresh article generation via whatever admin endpoint exists (`POST /api/v1/blog/articles` or similar — check `routes/blog` for the exact route used by the dashboard "create article" button). Verify the created article has `image_01_url` pointing to a `blog-images/library/...` URL when the topic has a SKU match, or empty otherwise.

- [ ] **Step 4: Commit**

```bash
git add blog/article_service.py
git commit -m "feat(hero): library-first hero selection in article generation pipeline"
```

---

## Task 14: Manual acceptance matrix (6 articles)

Documented verification on the three branches. This is a manual review, not an automated test.

**Files:**
- Create: `docs/hero_image_acceptance_2026-04-20.md`

- [ ] **Step 1: Pick 6 articles from the DB**

Use `dashboard/` or SQL to find one article for each of these buckets:

| # | Bucket | Example criterion |
|---|--------|-------------------|
| 1 | SKU with photo — blutdruck | Headline mentions BM 27, BM 35, BM 49, BM 96, or BC 54 |
| 2 | SKU with photo — TENS/regel | Headline mentions EM 50, EM 55, or EM 89 |
| 3 | SKU without photo — blutdruck | Headline mentions e.g. BM 81 |
| 4 | SKU without photo — infrarot | Headline mentions IL 50 or IL 60 |
| 5 | No SKU — regel/rueckenschmerzen | e.g. "Regelschmerzen lindern" |
| 6 | No SKU — blutdruck | e.g. "Bluthochdruck senken" |

- [ ] **Step 2: Regenerate each hero and record the outcome**

For each article ID:
```bash
curl -s -X POST http://localhost:8000/api/v1/blog/articles/<id>/generate-hero-image | python -m json.tool
```

Then open the dashboard article preview iframe for that article.

Record in `docs/hero_image_acceptance_2026-04-20.md`:

```markdown
# Hero Image Acceptance — 2026-04-20

Six-article acceptance matrix for the library-first hero pipeline.

| # | Article ID | Headline | Expected source | Actual source | File | Visual OK? | Alt text OK? |
|---|-----------|----------|-----------------|---------------|------|------------|--------------|
| 1 | ... | ... | product_use | ... | ... | Y/N | Y/N |
| 2 | ... | ... | product_use | ... | ... | Y/N | Y/N |
| 3 | ... | ... | lifestyle (fallback) | ... | ... | Y/N | Y/N |
| 4 | ... | ... | lifestyle or none | ... | ... | Y/N | Y/N |
| 5 | ... | ... | lifestyle | ... | ... | Y/N | Y/N |
| 6 | ... | ... | lifestyle | ... | ... | Y/N | Y/N |

## Notes / issues spotted

- ...
```

- [ ] **Step 3: Verify no-hero rendering looks clean**

If any row has `source: "none"` (or we forced one), open it in the dashboard iframe and confirm the article layout is not broken (no empty `<img>` element, no gap, author card + intro flow correctly).

- [ ] **Step 4: Commit the acceptance doc**

```bash
git add docs/hero_image_acceptance_2026-04-20.md
git commit -m "docs(hero): acceptance matrix for library-first hero pipeline"
```

---

## Done criteria

- All 14 tasks committed.
- `python scripts/test_hero_library.py` passes.
- `lifestyle_images.json` has 63 entries (22 lifestyle + 41 product_use).
- Supabase `blog-images/library/` contains all 41 new JPEGs (22 lifestyle already live under the legacy path — optional to move, out of scope here if they work as-is).
- `HERO_AI_FALLBACK` defaults to `false`; no AI calls made by either the endpoint or the pipeline on happy-path articles.
- Acceptance matrix fully green or issues triaged.
- `docs/beurer_asset_licensing.md` signed off.

## Out of scope (reaffirmed)

- Paragraph-scoped inline product images (briefing #6) — follow-up plan.
- PostAP library ingestion — rerun Task 10 + 11 with a different `--source-dir` when the download arrives.
- Editor UI for manual hero override — briefing #8 follow-up.
- Retiring the AI hero path entirely — stays behind `HERO_AI_FALLBACK`.
- Retiring `PRODUCT_IMAGE_MAP` — still used for inline cutouts.

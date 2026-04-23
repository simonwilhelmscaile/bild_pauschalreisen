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

    Always includes product names (model numbers, ® marks).
    Additionally includes terms matching any word from the keyword.

    Args:
        keyword: Article keyword, e.g. "Blutdruckmessgerät Oberarm"
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

        # Only include terms that match the keyword (both products and glossary)
        if not keyword_words:
            continue

        de_lower = de_val.lower()
        if not any(word in de_lower for word in keyword_words):
            continue

        entry = {
            "de": de_val,
            "target": target,
            "is_product_name": term.get("is_product_name", False),
        }

        if term.get("is_product_name", False):
            product_matches.append(entry)
        else:
            keyword_matches.append(entry)

    # Product names first, then glossary matches, capped
    result = product_matches + keyword_matches
    return result[:max_terms]

"""Seed the entities table from product catalogs and brand names.

Run standalone: python seed_entities.py

Reads BEURER_PRODUCT_CATALOG, COMPETITOR_PRODUCT_CATALOG, and BRAND_NAMES
from report/constants.py, generates aliases, and upserts into the entities table.
Idempotent — safe to re-run.
"""
import os
import sys
import re
import logging

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))

from db.client import get_beurer_supabase
from report.constants import (
    BEURER_PRODUCT_CATALOG,
    COMPETITOR_PRODUCT_CATALOG,
    BRAND_NAMES,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Regex for Beurer model pattern: 2-3 uppercase letters + space + 2-3 digits
BEURER_MODEL_RE = re.compile(r"^([A-Z]{2,3})\s+(\d{2,3})$")

# Regex for competitor model number embedded in name (e.g. "Omron M500" → "M500")
COMPETITOR_MODEL_RE = re.compile(r"\b([A-Z]{1,3}\s*\d{2,4})\b")


def generate_beurer_aliases(canonical: str) -> list[str]:
    """Generate aliases for a Beurer product like 'BM 27'."""
    m = BEURER_MODEL_RE.match(canonical)
    if not m:
        # Fallback: just lowercase
        return [canonical.lower()] if canonical.lower() != canonical else []

    prefix, number = m.group(1), m.group(2)
    aliases = set()

    # Without space: "BM27"
    no_space = f"{prefix}{number}"
    aliases.add(no_space)

    # Hyphenated: "BM-27"
    hyphen = f"{prefix}-{number}"
    aliases.add(hyphen)

    # With brand prefix: "Beurer BM 27", "Beurer BM27"
    aliases.add(f"Beurer {canonical}")
    aliases.add(f"Beurer {no_space}")

    # Lowercase variants of all above
    lowercase_extras = {a.lower() for a in aliases}
    aliases.update(lowercase_extras)

    # Also add canonical lowercase if different
    if canonical.lower() != canonical:
        aliases.add(canonical.lower())

    # Remove canonical itself if present
    aliases.discard(canonical)

    return sorted(aliases)


def generate_competitor_aliases(canonical: str, brand: str) -> list[str]:
    """Generate aliases for a competitor product like 'Omron M500'."""
    aliases = set()

    # Lowercase of canonical
    aliases.add(canonical.lower())

    # Extract model number if present
    model_match = COMPETITOR_MODEL_RE.search(canonical)
    if model_match:
        model = model_match.group(1)
        # Without brand: "M500"
        aliases.add(model)
        aliases.add(model.lower())

        # Variant with space in model if it doesn't have one (M500 → M 500)
        model_no_space = re.sub(r"\s+", "", model)
        if model_no_space != model:
            aliases.add(model_no_space)
            aliases.add(model_no_space.lower())
        else:
            # Add spaced version: "M500" → "M 500"
            spaced = re.sub(r"([A-Za-z])(\d)", r"\1 \2", model)
            if spaced != model:
                aliases.add(spaced)
                aliases.add(spaced.lower())

        # Hyphenated: "M-500"
        hyphenated = re.sub(r"([A-Za-z])\s*(\d)", r"\1-\2", model)
        if hyphenated != model:
            aliases.add(hyphenated)
            aliases.add(hyphenated.lower())

        # Without brand prefix: "M500" already added above
        # With brand + model variants
        aliases.add(f"{brand} {model_no_space}".lower())

    # Without brand prefix if canonical starts with brand
    if canonical.startswith(brand):
        without_brand = canonical[len(brand):].strip()
        if without_brand:
            aliases.add(without_brand)
            aliases.add(without_brand.lower())

    # Remove canonical itself
    aliases.discard(canonical)

    return sorted(aliases)


def generate_brand_aliases(brand: str) -> list[str]:
    """Generate aliases for a brand name like 'beurer'."""
    aliases = set()

    # Title case
    aliases.add(brand.title())
    # Uppercase
    aliases.add(brand.upper())
    # Lowercase
    aliases.add(brand.lower())

    # Remove the canonical form
    aliases.discard(brand)

    return sorted(aliases)


def build_entity_rows() -> list[dict]:
    """Build all entity rows from constants."""
    rows = []

    # Beurer products
    for product_name, meta in BEURER_PRODUCT_CATALOG.items():
        aliases = generate_beurer_aliases(product_name)
        rows.append({
            "canonical_name": product_name,
            "entity_type": "beurer_product",
            "category": meta["category"],
            "brand": "Beurer",
            "aliases": aliases,
            "priority": meta["priority"],
            "metadata": {},
        })

    # Competitor products
    for product_name, meta in COMPETITOR_PRODUCT_CATALOG.items():
        brand = meta.get("brand", "")
        aliases = generate_competitor_aliases(product_name, brand)
        rows.append({
            "canonical_name": product_name,
            "entity_type": "competitor_product",
            "category": meta["category"],
            "brand": brand,
            "aliases": aliases,
            "priority": 3,
            "metadata": {},
        })

    # Brands
    for brand_name in BRAND_NAMES:
        aliases = generate_brand_aliases(brand_name)
        rows.append({
            "canonical_name": brand_name,
            "entity_type": "brand",
            "category": None,
            "brand": brand_name,
            "aliases": aliases,
            "priority": 3,
            "metadata": {},
        })

    return rows


def seed_entities():
    """Seed the entities table. Upserts on canonical_name (idempotent)."""
    client = get_beurer_supabase()
    rows = build_entity_rows()

    stats = {"total": 0, "upserted": 0, "failed": 0, "by_type": {}}

    for row in rows:
        stats["total"] += 1
        entity_type = row["entity_type"]
        stats["by_type"].setdefault(entity_type, 0)

        try:
            client.table("entities").upsert(
                row, on_conflict="canonical_name"
            ).execute()
            stats["upserted"] += 1
            stats["by_type"][entity_type] += 1
            logger.info(
                f"  {row['canonical_name']} ({entity_type}) — "
                f"{len(row['aliases'])} aliases"
            )
        except Exception as e:
            stats["failed"] += 1
            logger.error(f"  FAILED {row['canonical_name']}: {e}")

    return stats


if __name__ == "__main__":
    logger.info("Seeding entities table from product catalogs and brand names...")
    logger.info(f"  Beurer products: {len(BEURER_PRODUCT_CATALOG)}")
    logger.info(f"  Competitor products: {len(COMPETITOR_PRODUCT_CATALOG)}")
    logger.info(f"  Brand names: {len(BRAND_NAMES)}")
    logger.info("")

    stats = seed_entities()

    logger.info("")
    logger.info("=== Seed Summary ===")
    logger.info(f"Total entities: {stats['total']}")
    logger.info(f"Upserted: {stats['upserted']}")
    logger.info(f"Failed: {stats['failed']}")
    for etype, count in stats["by_type"].items():
        logger.info(f"  {etype}: {count}")

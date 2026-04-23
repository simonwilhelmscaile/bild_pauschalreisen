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
    """Detect product names by presence of ® symbol or model number patterns."""
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

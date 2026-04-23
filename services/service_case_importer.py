"""Parse and import Salesforce service case exports (CSV or HTML-XLS)."""

import csv
import io
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup

from report.constants import BEURER_PRODUCT_CATALOG

logger = logging.getLogger(__name__)

# Broad regex: extract any two-letter + 2-3 digit model code
_MODEL_PATTERN = re.compile(r'([A-Z]{2})\s?(\d{2,3})')

# Expected column names from Salesforce export
_COLUMN_MAP = {
    "Case Reason Number": "case_id",
    "Product: Product Name": "product_raw",
    "Reason": "reason",
    "Created Date": "case_date",
}

# Known reason values (for validation warnings only — unknown reasons still imported)
KNOWN_REASONS = {
    "Label", "Anfrage Produkt", "Beschwerde Produkt", "Ersatzteilanfrage",
    "Beschwerde Software", "Widerruf", "Anfrage zur Bestellung/Lieferung",
    "Statusanfrage", "interne Weiterleitung", "Gutschrift", "Anrufbeantworter",
    "Adressprüfung", "Anfrage Software", "Reklamation Versanddienstleister",
    "Datenschutz",
}


def extract_product_model(raw: str) -> Optional[str]:
    """Extract model code from raw product string. Returns 'XX NN' format or None."""
    match = _MODEL_PATTERN.search(raw.upper())
    if not match:
        return None
    prefix, number = match.group(1), match.group(2)
    return f"{prefix} {number}"


def get_product_category(model: Optional[str]) -> Optional[str]:
    """Look up product category from BEURER_PRODUCT_CATALOG. Returns None if not found."""
    if not model:
        return None
    info = BEURER_PRODUCT_CATALOG.get(model)
    return info["category"] if info else None


def _detect_encoding(raw_bytes: bytes) -> str:
    """Detect file encoding: utf-8-bom first, then cp1252 fallback."""
    if raw_bytes[:3] == b'\xef\xbb\xbf':
        return "utf-8-sig"
    try:
        raw_bytes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def _detect_delimiter(first_line: str) -> str:
    """Detect CSV delimiter: semicolon vs comma. Semicolon wins ties (German default)."""
    semicolons = first_line.count(";")
    commas = first_line.count(",")
    return "," if commas > semicolons else ";"


def _is_html(content: str) -> bool:
    """Check if content looks like an HTML file."""
    stripped = content.strip()[:500].lower()
    return "<html" in stripped or "<table" in stripped


def _parse_html_xls(content: str) -> List[Dict[str, str]]:
    """Parse Salesforce HTML-table-as-XLS export."""
    soup = BeautifulSoup(content, "html.parser")
    table = soup.find("table")
    if not table:
        raise ValueError("No <table> found in HTML-XLS file")

    rows = table.find_all("tr")
    if len(rows) < 2:
        raise ValueError("HTML table has no data rows")

    # First row = headers
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th", "td"])]
    data = []
    for row in rows[1:]:
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) == len(headers):
            data.append(dict(zip(headers, cells)))
    return data


def _parse_csv(content: str) -> List[Dict[str, str]]:
    """Parse CSV content with auto-detected delimiter."""
    lines = content.splitlines()
    if not lines:
        raise ValueError("CSV file is empty")

    delimiter = _detect_delimiter(lines[0])
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    return list(reader)


def _normalize_row(
    raw: Dict[str, str], client_id: str, batch_id: str
) -> Optional[Dict[str, Any]]:
    """Normalize a raw row dict into a service_cases record. Returns None on error."""
    try:
        # Map column names
        mapped = {}
        for src_col, dest_col in _COLUMN_MAP.items():
            val = raw.get(src_col, "").strip()
            if not val:
                # Try with dest_col directly (in case file already uses our names)
                val = raw.get(dest_col, "").strip()
            mapped[dest_col] = val

        if not mapped["case_id"] or not mapped["reason"]:
            return None

        # Parse date (DD.MM.YYYY)
        case_date = datetime.strptime(mapped["case_date"], "%d.%m.%Y").strftime("%Y-%m-%d")

        # Extract product model
        product_raw = mapped.get("product_raw", "")
        product_model = extract_product_model(product_raw) if product_raw else None
        product_category = get_product_category(product_model)

        # Warn on unknown reason
        reason = mapped["reason"]
        if reason not in KNOWN_REASONS:
            logger.warning(f"Unknown reason value: '{reason}' in case {mapped['case_id']}")

        return {
            "client_id": client_id,
            "case_id": mapped["case_id"],
            "product_raw": product_raw,
            "product_model": product_model,
            "product_category": product_category,
            "reason": reason,
            "case_date": case_date,
            "import_batch_id": batch_id,
        }
    except (ValueError, KeyError) as e:
        logger.warning(f"Failed to parse row: {e}")
        return None


def parse_file(file_bytes: bytes, filename: str) -> Tuple[List[Dict[str, str]], str]:
    """Parse uploaded file into raw row dicts. Returns (rows, format_detected)."""
    encoding = _detect_encoding(file_bytes)
    content = file_bytes.decode(encoding)

    if filename.endswith(".xls") or _is_html(content):
        return _parse_html_xls(content), "html-xls"
    else:
        return _parse_csv(content), "csv"


def import_service_cases(
    file_bytes: bytes,
    filename: str,
    client_id: str,
    db_client,
) -> Dict[str, Any]:
    """Full import pipeline: parse -> normalize -> dedup -> insert.

    Returns: { imported, skipped, errors, batch_id }
    """
    from db.client import get_existing_case_ids, save_service_cases

    batch_id = str(uuid.uuid4())

    # 1. Parse
    raw_rows, fmt = parse_file(file_bytes, filename)
    logger.info(f"Parsed {len(raw_rows)} rows from {filename} (format: {fmt})")

    # 2. Normalize
    normalized = []
    errors = 0
    for raw in raw_rows:
        row = _normalize_row(raw, client_id, batch_id)
        if row is None:
            errors += 1
        else:
            normalized.append(row)

    # 3. Dedup against existing data
    case_ids = [r["case_id"] for r in normalized]
    existing = get_existing_case_ids(db_client, client_id, case_ids)
    new_cases = [r for r in normalized if r["case_id"] not in existing]
    skipped = len(normalized) - len(new_cases)

    # 4. Insert
    imported = 0
    if new_cases:
        imported = save_service_cases(db_client, new_cases)

    logger.info(
        f"Import complete: {imported} imported, {skipped} skipped, {errors} errors "
        f"(batch {batch_id})"
    )

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "batch_id": batch_id,
    }

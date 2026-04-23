# Salesforce Service Cases Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import Salesforce customer service case CSV/XLS files, store in Supabase, display in a new dashboard tab with heatmap/trends/alerts, and feed insights into the content engine.

**Architecture:** New `service_cases` Supabase table with FastAPI upload endpoint. TypeScript aggregator modules compute heatmap, trends, and anomaly alerts for a new "Kundendienst-Insights" dashboard tab (#11). Alerts also appear in the news tab. Content engine gets product-level service case summaries for article generation context.

**Tech Stack:** Python 3.11 / FastAPI (backend), Next.js 15 / TypeScript (dashboard), Supabase (DB), BeautifulSoup (HTML-XLS parsing), Chart.js (trend chart)

**Spec:** `docs/superpowers/specs/2026-03-26-salesforce-service-cases-design.md`

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `migrations/009_service_cases.sql` | DB table, indexes, unique constraint |
| `services/service_case_importer.py` | Parse CSV/HTML-XLS, extract product models, normalize rows |
| `routes/imports.py` | FastAPI upload endpoint |
| `dashboard/lib/aggregator/service-cases/types.ts` | TypeScript interfaces for service case data |
| `dashboard/lib/aggregator/service-cases/fetch.ts` | Supabase query for service_cases table |
| `dashboard/lib/aggregator/service-cases/heatmap.ts` | Product x reason matrix computation |
| `dashboard/lib/aggregator/service-cases/trends.ts` | Weekly case counts by reason |
| `dashboard/lib/aggregator/service-cases/utils.ts` | Shared utilities (getISOWeek) |
| `dashboard/lib/aggregator/service-cases/alerts.ts` | Anomaly detection (4-week avg comparison) |
| `dashboard/lib/aggregator/service-cases/index.ts` | Main entry: aggregateServiceCaseData() |
| `docs/service-case-import.md` | Operator documentation |

### Modified files
| File | Change |
|------|--------|
| `routes/__init__.py:1-13` | Include imports router in the shared social-listening router |
| `models.py` | Add `ServiceCaseImportResult` Pydantic model |
| `db/client.py` | Add 5 new functions for service_cases table |
| `dashboard/lib/aggregator/types.ts:90-151` | Add `kundendienstInsights` to `DashboardData` |
| `dashboard/lib/aggregator/index.ts:307-357` | Add `kundendienstInsights` to return object |
| `dashboard/app/api/dynamic-report/route.ts:57-86` | Fetch service cases, pass to aggregator |
| `dashboard/app/api/dashboard/route.ts:121-172` | Fetch service cases in dynamic mode |
| `blog/product_catalog.py:1-20` | Add `get_product_service_insights()` wrapper |
| `blog/article_service.py` | Pass service case context to Stage 2 |
| `styles/dashboard_template.html` | Add tab #11 nav + Kundendienst section + news "Interne Signale" |

---

## Task 1: Database Migration

**Files:**
- Create: `migrations/009_service_cases.sql`

- [ ] **Step 1: Write the migration SQL**

```sql
-- Service cases imported from Salesforce customer service exports
CREATE TABLE IF NOT EXISTS service_cases (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    client_id text NOT NULL DEFAULT 'beurer',
    case_id text NOT NULL,
    product_raw text NOT NULL,
    product_model text,
    product_category text,
    reason text NOT NULL,
    case_date date NOT NULL,
    imported_at timestamptz DEFAULT now(),
    import_batch_id uuid NOT NULL
);

-- Deduplication: one case per client
CREATE UNIQUE INDEX IF NOT EXISTS service_cases_client_case_idx
    ON service_cases(client_id, case_id);

-- Date range queries
CREATE INDEX IF NOT EXISTS service_cases_client_date_idx
    ON service_cases(client_id, case_date);

-- Product lookups
CREATE INDEX IF NOT EXISTS service_cases_client_product_idx
    ON service_cases(client_id, product_model);
```

- [ ] **Step 2: Run migration in Supabase**

Go to Supabase SQL Editor and execute the migration. Verify the table exists:
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'service_cases' ORDER BY ordinal_position;
```

- [ ] **Step 3: Commit**

```bash
git add migrations/009_service_cases.sql
git commit -m "feat: add service_cases table migration"
```

---

## Task 2: Pydantic Response Model

**Files:**
- Modify: `models.py`

- [ ] **Step 1: Add ServiceCaseImportResult model**

Add at the end of `models.py`:

```python
class ServiceCaseImportResult(BaseModel):
    """Response from service case file import."""
    imported: int = Field(description="Number of new cases imported")
    skipped: int = Field(description="Number of duplicate cases skipped")
    errors: int = Field(description="Number of rows that failed to parse")
    batch_id: str = Field(description="UUID grouping all rows from this import")
```

- [ ] **Step 2: Commit**

```bash
git add models.py
git commit -m "feat: add ServiceCaseImportResult pydantic model"
```

---

## Task 3: DB Operations for Service Cases

**Files:**
- Modify: `db/client.py`

- [ ] **Step 1: Add service case DB functions**

Add at the end of `db/client.py`:

```python
def get_existing_case_ids(client: Client, client_id: str, case_ids: List[str]) -> set:
    """Return set of case_ids that already exist for this client."""
    if not case_ids:
        return set()
    existing = set()
    # Query in chunks of 500 to avoid URL length limits
    for i in range(0, len(case_ids), 500):
        chunk = case_ids[i:i+500]
        result = client.table("service_cases").select("case_id").eq("client_id", client_id).in_("case_id", chunk).execute()
        existing.update(row["case_id"] for row in result.data)
    return existing


def save_service_cases(client: Client, cases: List[Dict[str, Any]]) -> int:
    """Bulk insert service cases in batches of 1000. Returns count inserted."""
    total = 0
    for i in range(0, len(cases), 1000):
        batch = cases[i:i+1000]
        result = client.table("service_cases").insert(batch).execute()
        total += len(result.data)
    return total


def get_service_cases(client: Client, client_id: str, start_date: str, end_date: str) -> List[Dict]:
    """Fetch service cases for a client within a date range."""
    result = (
        client.table("service_cases")
        .select("*")
        .eq("client_id", client_id)
        .gte("case_date", start_date)
        .lte("case_date", end_date)
        .execute()
    )
    return result.data


def get_service_case_summary(client: Client, client_id: str, product_model: str, days: int = 90) -> Optional[Dict]:
    """Get top 5 reasons + counts for a product over the last N days.

    Returns: { product, total_cases, top_reasons: [{ reason, count, percent }] }
    or None if no data.
    """
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    result = (
        client.table("service_cases")
        .select("reason")
        .eq("client_id", client_id)
        .eq("product_model", product_model)
        .gte("case_date", cutoff)
        .execute()
    )
    if not result.data:
        return None
    # Count by reason
    counts: Dict[str, int] = {}
    for row in result.data:
        counts[row["reason"]] = counts.get(row["reason"], 0) + 1
    total = sum(counts.values())
    top_reasons = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "product": product_model,
        "total_cases": total,
        "top_reasons": [
            {"reason": r, "count": c, "percent": round(c / total * 100)}
            for r, c in top_reasons
        ],
    }
```

- [ ] **Step 2: Verify imports are present**

Ensure `List`, `Dict`, `Any`, `Optional` are already imported at the top of `db/client.py` (they are — line 5).

- [ ] **Step 3: Commit**

```bash
git add db/client.py
git commit -m "feat: add service case DB operations"
```

---

## Task 4: Service Case Importer

**Files:**
- Create: `services/service_case_importer.py`

- [ ] **Step 1: Create the importer module**

```python
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
    """Full import pipeline: parse → normalize → dedup → insert.

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
```

- [ ] **Step 2: Ensure beautifulsoup4 is in requirements.txt**

Check if `beautifulsoup4` is already in `requirements.txt`. If not, add it:

```
beautifulsoup4>=4.12.0
```

Run `pip install -r requirements.txt` to verify.

- [ ] **Step 3: Commit**

```bash
git add services/service_case_importer.py requirements.txt
git commit -m "feat: add service case file parser and importer"
```

---

## Task 5: FastAPI Upload Endpoint

**Files:**
- Create: `routes/imports.py`
- Modify: `routes/__init__.py:1-13`

- [ ] **Step 1: Create the imports router**

```python
"""Import endpoints for external data sources."""

import logging
from fastapi import APIRouter, File, Query, UploadFile
from db.client import get_beurer_supabase
from models import ServiceCaseImportResult
from services.service_case_importer import import_service_cases

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/import/service-cases",
    response_model=ServiceCaseImportResult,
    summary="Import Salesforce service case CSV or HTML-XLS file",
)
async def upload_service_cases(
    file: UploadFile = File(...),
    client_id: str = Query("beurer", description="Client identifier"),
):
    """Upload and import a Salesforce service case export file.

    Accepts CSV (semicolon or comma delimited) or HTML-table-as-XLS format.
    Deduplicates by case_id — existing cases are skipped.
    """
    try:
        contents = await file.read()
        db_client = get_beurer_supabase()
        result = import_service_cases(
            file_bytes=contents,
            filename=file.filename or "upload.csv",
            client_id=client_id,
            db_client=db_client,
        )
        return ServiceCaseImportResult(**result)
    except Exception as e:
        logger.exception(f"Service case import failed: {e}")
        raise
```

- [ ] **Step 2: Include the router in routes/__init__.py**

In `routes/__init__.py`, add the import and include:

```python
"""Route modules — assembled into a single router."""
from fastapi import APIRouter

from .core import router as core_router
from .backfill import router as backfill_router
from .reports import router as reports_router
from .imports import router as imports_router

router = APIRouter(prefix="/social-listening", tags=["Social Listening"])
router.include_router(core_router)
router.include_router(backfill_router)
router.include_router(reports_router)
router.include_router(imports_router)

__all__ = ["router"]
```

This follows the existing pattern where all social-listening routes are assembled through `routes/__init__.py`. The endpoint path in `routes/imports.py` should be `/import/service-cases` (without the `/social-listening` prefix, since that's added by the parent router).

- [ ] **Step 3: Test manually**

Start the server and test with curl:
```bash
python app.py
# In another terminal:
curl -X POST http://localhost:8000/api/v1/social-listening/import/service-cases \
  -F "file=@test_data.csv" \
  -F "client_id=beurer"
```

Verify the endpoint appears in the Swagger docs at `http://localhost:8000/docs`.

- [ ] **Step 4: Commit**

```bash
git add routes/imports.py routes/__init__.py
git commit -m "feat: add service case upload endpoint"
```

---

## Task 6: TypeScript Types and Fetch

**Files:**
- Create: `dashboard/lib/aggregator/service-cases/types.ts`
- Create: `dashboard/lib/aggregator/service-cases/fetch.ts`
- Modify: `dashboard/lib/aggregator/types.ts:150`

- [ ] **Step 1: Create TypeScript interfaces**

Create `dashboard/lib/aggregator/service-cases/types.ts`:

```typescript
/** Raw service case row from Supabase */
export interface ServiceCase {
  id: string;
  client_id: string;
  case_id: string;
  product_raw: string;
  product_model: string | null;
  product_category: string | null;
  reason: string;
  case_date: string; // YYYY-MM-DD
  imported_at: string;
  import_batch_id: string;
}

/** Product row in the heatmap */
export interface HeatmapProduct {
  model: string;
  category: string | null;
  reasons: Record<string, number>;
  total: number;
}

/** Heatmap data (View A) */
export interface HeatmapData {
  products: HeatmapProduct[];
  allReasons: string[];
  totalCases: number;
}

/** Single week in the trend chart */
export interface TrendWeek {
  week: string; // ISO week, e.g. "2026-W04"
  total: number;
  byReason: Record<string, number>;
}

/** Trend data (View B) */
export interface TrendData {
  weeks: TrendWeek[];
  allReasons: string[];
}

/** Single risk alert */
export interface ServiceCaseAlert {
  product: string;
  reason: string;
  currentCount: number;
  avgCount: number;
  changePercent: number;
  severity: "warning" | "critical";
}

/** Combined output for the Kundendienst tab */
export interface KundendienstInsights {
  heatmap: HeatmapData;
  trends: TrendData;
  alerts: ServiceCaseAlert[];
  summary: {
    totalCases: number;
    topProduct: { model: string; count: number } | null;
    topReason: { reason: string; count: number } | null;
    alertCount: number;
  };
}
```

- [ ] **Step 2: Create fetch module**

Create `dashboard/lib/aggregator/service-cases/fetch.ts`:

```typescript
import { SupabaseClient } from "@supabase/supabase-js";
import { ServiceCase } from "./types";

/**
 * Fetch service cases for a date range.
 * Returns empty array if the table doesn't exist (graceful degradation).
 */
export async function fetchServiceCases(
  supabase: SupabaseClient,
  startDate: string,
  endDate: string,
  clientId: string = "beurer"
): Promise<ServiceCase[]> {
  try {
    const { data, error } = await supabase
      .from("service_cases")
      .select("*")
      .eq("client_id", clientId)
      .gte("case_date", startDate)
      .lte("case_date", endDate);

    if (error) {
      // Table may not exist yet — degrade gracefully
      console.warn("service_cases fetch error (non-blocking):", error.message);
      return [];
    }
    return (data || []) as ServiceCase[];
  } catch (e) {
    console.warn("service_cases fetch failed (non-blocking):", e);
    return [];
  }
}
```

- [ ] **Step 3: Create shared utils module**

Create `dashboard/lib/aggregator/service-cases/utils.ts`:

```typescript
/** Get ISO week string (e.g. "2026-W04") for a YYYY-MM-DD date. */
export function getISOWeek(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00Z");
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  const year = d.getUTCFullYear();
  return `${year}-W${String(weekNo).padStart(2, "0")}`;
}
```

- [ ] **Step 4: Add KundendienstInsights to DashboardData**

In `dashboard/lib/aggregator/types.ts`, after the `news?` field (line 149), add before the closing `}`:

```typescript
  kundendienstInsights?: {
    heatmap: {
      products: Array<{ model: string; category: string | null; reasons: Record<string, number>; total: number }>;
      allReasons: string[];
      totalCases: number;
    };
    trends: {
      weeks: Array<{ week: string; total: number; byReason: Record<string, number> }>;
      allReasons: string[];
    };
    alerts: Array<{
      product: string;
      reason: string;
      currentCount: number;
      avgCount: number;
      changePercent: number;
      severity: "warning" | "critical";
    }>;
    summary: {
      totalCases: number;
      topProduct: { model: string; count: number } | null;
      topReason: { reason: string; count: number } | null;
      alertCount: number;
    };
  };
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/lib/aggregator/service-cases/types.ts dashboard/lib/aggregator/service-cases/fetch.ts dashboard/lib/aggregator/service-cases/utils.ts dashboard/lib/aggregator/types.ts
git commit -m "feat: add service case TS types, utils, and Supabase fetch"
```

---

## Task 7: Heatmap Aggregation

**Files:**
- Create: `dashboard/lib/aggregator/service-cases/heatmap.ts`

- [ ] **Step 1: Implement heatmap builder**

```typescript
import { ServiceCase, HeatmapData, HeatmapProduct } from "./types";

/**
 * Build product x reason heatmap matrix.
 * Default: only products with a known category (health devices).
 */
export function buildHeatmap(cases: ServiceCase[], includeUncategorized = false): HeatmapData {
  const filtered = includeUncategorized
    ? cases.filter((c) => c.product_model)
    : cases.filter((c) => c.product_model && c.product_category);

  // Collect all reasons
  const reasonSet = new Set<string>();

  // Group by product
  const productMap = new Map<string, { category: string | null; reasons: Map<string, number> }>();
  for (const c of filtered) {
    const model = c.product_model!;
    reasonSet.add(c.reason);
    if (!productMap.has(model)) {
      productMap.set(model, { category: c.product_category, reasons: new Map() });
    }
    const entry = productMap.get(model)!;
    entry.reasons.set(c.reason, (entry.reasons.get(c.reason) || 0) + 1);
  }

  // Build sorted product list
  const products: HeatmapProduct[] = [];
  for (const [model, data] of productMap) {
    const reasons: Record<string, number> = {};
    let total = 0;
    for (const [reason, count] of data.reasons) {
      reasons[reason] = count;
      total += count;
    }
    products.push({ model, category: data.category, reasons, total });
  }
  products.sort((a, b) => b.total - a.total);

  const allReasons = [...reasonSet].sort();

  return {
    products,
    allReasons,
    totalCases: filtered.length,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/lib/aggregator/service-cases/heatmap.ts
git commit -m "feat: add service case heatmap aggregation"
```

---

## Task 8: Trends Aggregation

**Files:**
- Create: `dashboard/lib/aggregator/service-cases/trends.ts`

- [ ] **Step 1: Implement trends builder**

```typescript
import { ServiceCase, TrendData, TrendWeek } from "./types";
import { getISOWeek } from "./utils";

/**
 * Bucket service cases by ISO week, broken down by reason.
 */
export function buildTrends(cases: ServiceCase[]): TrendData {
  const reasonSet = new Set<string>();
  const weekMap = new Map<string, Map<string, number>>();

  for (const c of cases) {
    const week = getISOWeek(c.case_date);
    reasonSet.add(c.reason);
    if (!weekMap.has(week)) {
      weekMap.set(week, new Map());
    }
    const wk = weekMap.get(week)!;
    wk.set(c.reason, (wk.get(c.reason) || 0) + 1);
  }

  // Sort weeks chronologically
  const sortedWeeks = [...weekMap.keys()].sort();
  const weeks: TrendWeek[] = sortedWeeks.map((week) => {
    const byReason: Record<string, number> = {};
    let total = 0;
    for (const [reason, count] of weekMap.get(week)!) {
      byReason[reason] = count;
      total += count;
    }
    return { week, total, byReason };
  });

  return { weeks, allReasons: [...reasonSet].sort() };
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/lib/aggregator/service-cases/trends.ts
git commit -m "feat: add service case trend aggregation"
```

---

## Task 9: Alerts Aggregation

**Files:**
- Create: `dashboard/lib/aggregator/service-cases/alerts.ts`

- [ ] **Step 1: Implement alert detection**

```typescript
import { ServiceCase, ServiceCaseAlert } from "./types";
import { getISOWeek } from "./utils";

/**
 * Detect anomalies: compare most recent week's per-product reason counts
 * against the previous 4-week average.
 *
 * Thresholds: >30% deviation AND >=5 cases in current week.
 * Severity: warning (30-60%), critical (>60%).
 */
export function buildAlerts(cases: ServiceCase[]): ServiceCaseAlert[] {
  if (cases.length === 0) return [];

  // Group by week → product → reason → count
  const weekProductReason = new Map<string, Map<string, Map<string, number>>>();
  for (const c of cases) {
    if (!c.product_model) continue;
    const week = getISOWeek(c.case_date);
    if (!weekProductReason.has(week)) weekProductReason.set(week, new Map());
    const products = weekProductReason.get(week)!;
    if (!products.has(c.product_model)) products.set(c.product_model, new Map());
    const reasons = products.get(c.product_model)!;
    reasons.set(c.reason, (reasons.get(c.reason) || 0) + 1);
  }

  const sortedWeeks = [...weekProductReason.keys()].sort();
  if (sortedWeeks.length < 2) return []; // Need at least 2 weeks for comparison

  const currentWeek = sortedWeeks[sortedWeeks.length - 1];
  // Previous 4 weeks (or however many are available, excluding current)
  const prevWeeks = sortedWeeks.slice(Math.max(0, sortedWeeks.length - 5), sortedWeeks.length - 1);
  if (prevWeeks.length === 0) return [];

  const currentData = weekProductReason.get(currentWeek)!;
  const alerts: ServiceCaseAlert[] = [];

  for (const [product, reasons] of currentData) {
    for (const [reason, currentCount] of reasons) {
      if (currentCount < 5) continue; // Noise filter

      // Compute average from previous weeks
      let total = 0;
      for (const pw of prevWeeks) {
        const pwData = weekProductReason.get(pw);
        total += pwData?.get(product)?.get(reason) || 0;
      }
      const avgCount = total / prevWeeks.length;

      if (avgCount === 0) continue; // No baseline to compare

      const changePercent = Math.round(((currentCount - avgCount) / avgCount) * 100);
      if (changePercent < 30) continue; // Below threshold

      alerts.push({
        product,
        reason,
        currentCount,
        avgCount: Math.round(avgCount * 10) / 10,
        changePercent,
        severity: changePercent > 60 ? "critical" : "warning",
      });
    }
  }

  // Sort: critical first, then by changePercent descending
  alerts.sort((a, b) => {
    if (a.severity !== b.severity) return a.severity === "critical" ? -1 : 1;
    return b.changePercent - a.changePercent;
  });

  return alerts;
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/lib/aggregator/service-cases/alerts.ts
git commit -m "feat: add service case anomaly alert detection"
```

---

## Task 10: Service Case Aggregator Entry Point

**Files:**
- Create: `dashboard/lib/aggregator/service-cases/index.ts`
- Modify: `dashboard/lib/aggregator/index.ts:307-357`
- Modify: `dashboard/app/api/dynamic-report/route.ts:57-86`
- Modify: `dashboard/app/api/dashboard/route.ts:121-172`

- [ ] **Step 1: Create the aggregator entry point**

Create `dashboard/lib/aggregator/service-cases/index.ts`:

```typescript
import { ServiceCase, KundendienstInsights } from "./types";
import { buildHeatmap } from "./heatmap";
import { buildTrends } from "./trends";
import { buildAlerts } from "./alerts";

/**
 * Aggregate all service case data for the Kundendienst-Insights dashboard tab.
 * Returns null if no cases are available (tab can hide gracefully).
 */
export function aggregateServiceCaseData(cases: ServiceCase[]): KundendienstInsights | null {
  if (cases.length === 0) return null;

  const heatmap = buildHeatmap(cases);
  const trends = buildTrends(cases);
  const alerts = buildAlerts(cases);

  // Summary stats
  const productCounts = new Map<string, number>();
  const reasonCounts = new Map<string, number>();
  for (const c of cases) {
    if (c.product_model) {
      productCounts.set(c.product_model, (productCounts.get(c.product_model) || 0) + 1);
    }
    reasonCounts.set(c.reason, (reasonCounts.get(c.reason) || 0) + 1);
  }

  let topProduct: { model: string; count: number } | null = null;
  let topReason: { reason: string; count: number } | null = null;
  for (const [model, count] of productCounts) {
    if (!topProduct || count > topProduct.count) topProduct = { model, count };
  }
  for (const [reason, count] of reasonCounts) {
    if (!topReason || count > topReason.count) topReason = { reason, count };
  }

  return {
    heatmap,
    trends,
    alerts,
    summary: {
      totalCases: cases.length,
      topProduct,
      topReason,
      alertCount: alerts.length,
    },
  };
}

export { fetchServiceCases } from "./fetch";
export type { KundendienstInsights, ServiceCase, ServiceCaseAlert } from "./types";
```

- [ ] **Step 2: Wire into main aggregator**

In `dashboard/lib/aggregator/index.ts`, add to the return object (around line 356, before the closing `};`):

```typescript
    // kundendienstInsights is injected by the route handler, not computed here
    // (it comes from a separate table, not social_items)
```

This is a no-op comment — the actual data injection happens in the route handlers (next steps). The `aggregateReportData` function only processes `social_items` data; service case data is fetched and merged separately by the route handlers.

- [ ] **Step 3: Wire into dynamic-report route**

In `dashboard/app/api/dynamic-report/route.ts`, add the import at the top (after line 4):

```typescript
import { fetchServiceCases, aggregateServiceCaseData } from "@/lib/aggregator/service-cases";
```

Inside the `fetchPromise` async block (after line 72 where `aggregateReportData` is called), add:

```typescript
      // Fetch and aggregate service case data
      const serviceCases = await fetchServiceCases(supabase, startDate, endDate);
      const kundendienstInsights = aggregateServiceCaseData(serviceCases);
      if (kundendienstInsights) {
        (data as any).kundendienstInsights = kundendienstInsights;
      }
```

- [ ] **Step 4: Wire into dashboard HTML route**

In `dashboard/app/api/dashboard/route.ts`, add the import at the top:

```typescript
import { fetchServiceCases, aggregateServiceCaseData } from "@/lib/aggregator/service-cases";
```

In the dynamic mode block (after line 145 where `aggregateReportData` is called), add:

```typescript
      // Fetch and aggregate service case data
      const serviceCases = await fetchServiceCases(supabase, startDate, endDate);
      const kundendienstInsights = aggregateServiceCaseData(serviceCases);
      if (kundendienstInsights) {
        (data as any).kundendienstInsights = kundendienstInsights;
      }
```

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/aggregator/service-cases/index.ts dashboard/lib/aggregator/index.ts dashboard/app/api/dynamic-report/route.ts dashboard/app/api/dashboard/route.ts
git commit -m "feat: wire service case aggregation into dashboard routes"
```

---

## Task 11: Dashboard Template — Tab Navigation and Kundendienst Section

**Files:**
- Modify: `styles/dashboard_template.html`

This is the largest task. The template is a single HTML file with embedded JS. We need to add:
1. Tab #11 nav item
2. The full Kundendienst-Insights section
3. The "Interne Signale" section in the news tab

- [ ] **Step 1: Add nav item for Kundendienst tab**

Find the last `sidebar-nav-item` in the navigation (the one for `tab-seo` / GSC). Add after it:

```html
<div class="sidebar-nav-item" data-tab="tab-kundendienst" title="Kundendienst-Insights">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
    <span class="nav-label">Kundendienst</span>
</div>
```

- [ ] **Step 2: Add the Kundendienst-Insights tab section**

Add a new section in the template body (after the last tab section, before the closing scripts). The section should have `id="tab-kundendienst"` and `style="display:none"`.

The section contains:
- Date filter buttons (7d, 30d, 90d, All) — client-side filtering via JS
- Summary cards row (Total Cases, Top Product, Top Reason, Alerts count)
- **View A: Heatmap table** — product rows x reason columns, background color intensity. Category filter buttons. Sortable column headers.
- **View B: Trend chart** — Chart.js line chart with weekly case counts by reason. Product multi-select filter.
- **View C: Alert cards** — styled warning/critical cards

This is a large block of HTML + JS. The implementer should follow the existing template patterns:
- Use `window.reportData.kundendienstInsights` as the data source
- Use the same card/section styling as other tabs
- Use Chart.js for the trend chart (already loaded in template)
- Color palette: use existing CSS variables from the template
- The `initKundendienstTab()` function should be called from the main `initDashboard()` function

**Key JS functions to implement:**
- `initKundendienstTab()` — main init, reads data, renders all three views
- `renderHeatmap(data, filters)` — builds the HTML table with color-coded cells
- `renderTrendChart(data, productFilter)` — creates/updates Chart.js line chart
- `renderAlerts(alerts)` — renders alert cards
- `filterKundendienstByDate(days)` — client-side date filter (filters `cases` by `case_date`)

**Important:** The heatmap should default to showing only categorized products (health devices). An "Alle Produkte" toggle shows all.

- [ ] **Step 3: Add "Interne Signale" section to news tab**

In the `tab-news` section, add at the very top (before the existing news articles list):

```html
<div id="internal-signals" class="internal-signals-section" style="display:none">
    <h3 style="margin-bottom:12px;font-size:14px;font-weight:600;color:var(--text-primary)">
        Interne Signale — Kundendienst
    </h3>
    <div id="internal-signals-list"></div>
</div>
```

In the news tab initialization JS, add logic to check `reportData.kundendienstInsights?.alerts` and render them:

```javascript
function renderInternalSignals() {
    const alerts = window.reportData?.kundendienstInsights?.alerts;
    const container = document.getElementById('internal-signals');
    const list = document.getElementById('internal-signals-list');
    if (!alerts || alerts.length === 0 || !container || !list) return;

    container.style.display = 'block';
    list.innerHTML = alerts.map(a => `
        <div style="padding:10px 14px;margin-bottom:8px;border-radius:8px;
            background:${a.severity === 'critical' ? 'rgba(239,68,68,0.08)' : 'rgba(234,179,8,0.08)'};
            border-left:3px solid ${a.severity === 'critical' ? '#ef4444' : '#eab308'}">
            <span style="font-weight:600">${a.product}</span>:
            ${a.reason} <span style="color:${a.severity === 'critical' ? '#ef4444' : '#eab308'}">
            +${a.changePercent}%</span> vs. 4-Wochen-Durchschnitt
            <span style="opacity:0.6;font-size:12px">(${a.currentCount} Fälle, Ø ${a.avgCount})</span>
        </div>
    `).join('');
}
```

- [ ] **Step 4: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add Kundendienst-Insights tab and internal signals in news"
```

---

## Task 12: Content Engine Integration

**Files:**
- Modify: `blog/product_catalog.py`
- Modify: `blog/article_service.py`

- [ ] **Step 1: Add service case lookup to product_catalog.py**

Add at the end of `blog/product_catalog.py`:

```python
def get_product_service_insights(product_model: str, client_id: str = "beurer") -> Optional[str]:
    """Get formatted service case summary for article generation context.

    Returns a prompt-ready German string, or None if no data available.
    """
    try:
        from db.client import get_beurer_supabase, get_service_case_summary
        client = get_beurer_supabase()
        summary = get_service_case_summary(client, client_id, product_model)
        if not summary or summary["total_cases"] == 0:
            return None

        lines = [f"## Kundendienst-Daten (letzte 90 Tage)"]
        lines.append(f"{summary['product']}: {summary['total_cases']} Fälle")
        for r in summary["top_reasons"]:
            lines.append(f"- {r['reason']}: {r['count']} ({r['percent']}%)")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Service case lookup failed for {product_model}: {e}")
        return None
```

- [ ] **Step 2: Inject into article generation**

In `blog/article_service.py`, the `generate_article()` function (line 265) builds context at lines 293-298:

```python
        company_context = get_beurer_company_context(language)
        keyword_instructions = _build_instructions_from_context(social_context, language)
```

Then passes them to `write_article()` at lines 303-310. The `keyword_instructions` string is the right place to inject service case data — it already contains contextual instructions for the writer.

At the top of `blog/article_service.py`, add the import:

```python
from blog.product_catalog import get_product_service_insights
```

After line 298 (`keyword_instructions = _build_instructions_from_context(...)`), add:

```python
        # Enrich with service case insights if available
        product_model = (social_context or {}).get("matched_products", [""])[0] if social_context else ""
        if product_model:
            service_insights = get_product_service_insights(product_model)
            if service_insights:
                keyword_instructions = (keyword_instructions or "") + "\n\n" + service_insights
```

This extracts the product model from the `social_context.matched_products` array (already available from the content opportunity), looks up service case data, and appends it to the writer instructions. If no product or no data, nothing changes. The writer prompt will see the Kundendienst section alongside other keyword instructions.

- [ ] **Step 3: Commit**

```bash
git add blog/product_catalog.py blog/article_service.py
git commit -m "feat: add service case insights to content engine context"
```

---

## Task 13: Documentation

**Files:**
- Create: `docs/service-case-import.md`

- [ ] **Step 1: Write operator documentation**

Create `docs/service-case-import.md` covering:

1. **Overview** — what this feature does, where data comes from
2. **File format** — expected columns, CSV vs HTML-XLS, encoding notes
3. **How to import** — endpoint URL, curl example, response format
4. **Product matching** — regex pattern, catalog lookup, what happens with unknown products
5. **Dashboard** — where to find the data, what the three views show
6. **Adding a new client** — step-by-step: new client_id, product catalog, that's it
7. **Troubleshooting** — common issues (wrong encoding, missing columns, duplicate imports)

- [ ] **Step 2: Commit**

```bash
git add docs/service-case-import.md
git commit -m "docs: add service case import operator guide"
```

---

## Task 14: Final Integration Test

- [ ] **Step 1: Create a small test CSV**

Create a test file with ~20 rows covering: known products (BM 27, EM 59), unknown products (KS 19), all the common reasons, various date formats.

- [ ] **Step 2: Run the full pipeline**

1. Start the server: `python app.py`
2. Upload test file: `curl -X POST .../import/service-cases -F file=@test.csv`
3. Verify response shows correct imported/skipped counts
4. Open dashboard: `http://localhost:3000/api/dashboard?days=30`
5. Verify the Kundendienst tab appears and shows data
6. Verify the news tab shows "Interne Signale" if any alerts triggered
7. Upload same file again — verify all rows are skipped (dedup works)

- [ ] **Step 3: Commit any fixes**

Stage and commit only the specific files that were fixed:
```bash
git add <changed-files>
git commit -m "fix: integration test fixes for service case pipeline"
```

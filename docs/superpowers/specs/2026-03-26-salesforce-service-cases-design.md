# Salesforce Customer Service Cases Integration

**Date:** 2026-03-26
**Status:** Draft
**Scope:** Import pipeline, dashboard tab, content engine integration for Salesforce customer service case data

## Context

Beurer will send weekly CSV exports from Salesforce containing customer service cases. First batch: 29,754 cases from January 2026. No API — file-based export only. File format is currently HTML-table disguised as `.xls` (standard Salesforce export); CSV transition requested.

This feature adds a new data source to the existing social listening dashboard, giving visibility into customer service patterns alongside the social/forum data already tracked.

## Data Model

### New table: `service_cases`

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid (PK) | Auto-generated |
| `client_id` | text | `"beurer"` for now. Multi-client ready. |
| `case_id` | text | Salesforce case ID, e.g. `CR-533216`. Dedup key. |
| `product_raw` | text | Original value from file, e.g. "Beurer BM 27" |
| `product_model` | text, nullable | Regex-extracted model code, e.g. "BM 27". Null if no pattern match. |
| `product_category` | text, nullable | Mapped from product catalog: `blood_pressure`, `pain_tens`, `infrarot`. Null if unknown product. |
| `reason` | text | Original reason string from Salesforce |
| `case_date` | date | Parsed from DD.MM.YYYY format |
| `imported_at` | timestamptz | Row creation timestamp |
| `import_batch_id` | uuid | Groups rows from the same file upload |

### Indexes

- **Unique constraint** on `(client_id, case_id)` — deduplication
- **Index** on `(client_id, case_date)` — date range queries
- **Index** on `(client_id, product_model)` — product lookups

### Migration

File: `migrations/009_service_cases.sql`

### Known Salesforce reason values

`Label`, `Anfrage Produkt`, `Beschwerde Produkt`, `Ersatzteilanfrage`, `Beschwerde Software`, `Widerruf`, `Anfrage zur Bestellung/Lieferung`, `Statusanfrage`, `interne Weiterleitung`, `Gutschrift`, `Anrufbeantworter`, `Adressprüfung`, `Anfrage Software`, `Reklamation Versanddienstleister`, `Datenschutz`

These are stored as-is. Unknown reasons are imported with a warning logged.

## Import Pipeline

### Endpoint

`POST /api/v1/social-listening/import/service-cases`

- **Input:** Multipart file upload (`file`) + query param `client_id` (default: `"beurer"`)
- **Output:** `ServiceCaseImportResult` (Pydantic model in `models.py`): `{ imported: 245, skipped: 12, errors: 0, batch_id: "uuid" }`

### Route location

New file: `routes/imports.py`, mounted in `app.py` alongside existing routers.

### Importer module

New file: `services/service_case_importer.py`

### Parsing logic

1. **Format detection:** Check file extension + sniff content for HTML tags. If HTML found, parse as HTML table. Otherwise parse as CSV.
2. **HTML-XLS parser:** BeautifulSoup extracts `<table>` rows, maps column headers to fields. Expected columns: `Case Reason Number`, `Product: Product Name`, `Reason`, `Created Date`.
3. **CSV parser:** `csv.DictReader`. Encoding detection: try `utf-8-bom` first, fall back to `cp1252` (German Excel default). Delimiter detection: count semicolons vs commas in the first non-empty line; use whichever is more frequent, default to semicolon on tie. Same column names.
4. **Row normalization:**
   - `case_id` — strip whitespace
   - `product_raw` — preserve original string
   - `product_model` — broad regex `r'([A-Z]{2})\s?(\d{2,3})'` extracts model code, normalize to `"XX NN"` with space. First match wins. Null if no match. All products are stored regardless of catalog membership.
   - `product_category` — lookup `product_model` against `BEURER_PRODUCTS` in `report/constants.py`. Null if not in catalog.
   - `reason` — strip whitespace, warn on unknown values (still import)
   - `case_date` — `datetime.strptime(value, "%d.%m.%Y")`
5. **Deduplication:** Batch-fetch existing `case_id` values for this `client_id` from Supabase. Skip any that already exist.
6. **Bulk insert:** Insert in batches of 1,000 rows (Supabase/PostgREST body size limit). All batches share the same `import_batch_id`.

### Product model extraction

Regex pattern: `r'([A-Z]{2})\s?(\d{2,3})'` (broad — extracts any two-letter + 2-3 digit model code)

Examples:
- `"BM 27"` → `"BM 27"` → category: `blood_pressure`
- `"BM27"` → `"BM 27"` → category: `blood_pressure`
- `"Beurer BM 27"` → `"BM 27"` → category: `blood_pressure`
- `"Beurer Blutdruckmessgerät BM 27"` → `"BM 27"` → category: `blood_pressure`
- `"Küchenwaage KS 19"` → `"KS 19"` → category: null (not in health catalog)

**Dashboard filtering:** The heatmap and trend views default to showing only rows where `product_category IS NOT NULL` (i.e. health-device products in the catalog). An "Alle Produkte" toggle shows all products including uncategorized ones.

### DB operations

New functions in `db/client.py`:
- `save_service_cases(cases: list[dict]) -> int` — bulk insert, returns count
- `get_existing_case_ids(client_id: str, case_ids: list[str]) -> set[str]` — for dedup check
- `get_service_cases(client_id: str, start_date: date, end_date: date) -> list[dict]` — for dashboard aggregation
- `get_service_case_summary(client_id: str, product_model: str, days: int) -> dict` — for content engine (top 5 reasons + counts)

## Dashboard Aggregation (TypeScript)

### Module structure

```
dashboard/lib/aggregator/service-cases/
  index.ts          — main entry: aggregateServiceCaseData()
  fetch.ts          — Supabase query for service_cases table
  heatmap.ts        — View A: product x reason matrix
  trends.ts         — View B: weekly case counts by reason
  alerts.ts         — View C: anomaly detection + risk alerts
  types.ts          — TypeScript interfaces
```

### Integration

The service case data lives in a separate Supabase table from `social_items`, so it requires its own fetch path:

1. `dashboard/lib/aggregator/service-cases/fetch.ts` queries the `service_cases` table directly from Supabase (date-bounded to match the dashboard's `days` parameter).
2. `dashboard/lib/aggregator/index.ts` calls `aggregateServiceCaseData(serviceCases)` alongside existing aggregation. Output is added as `kundendienstInsights` key to the `DashboardData` type in `dashboard/lib/aggregator/types.ts`.
3. `dashboard/app/api/dynamic-report/route.ts` calls the service case fetch before aggregation and passes the results through.
4. `dashboard/app/api/dashboard/route.ts` does the same when serving the HTML template.

The service case fetch is date-bounded to match the dashboard's `days` parameter (7/14/30), ensuring consistent date ranges with social listening data. The "All" option in the Kundendienst tab's own date filter works within whatever date range was fetched.

### View A — Product Issue Heatmap (`heatmap.ts`)

- Groups cases by `product_model` x `reason`
- Output: `{ products: [{ model, category, reasons: { [reason]: count }, total }] }`
- Pre-sorted by total volume descending
- Includes category metadata for client-side filtering

### View B — Trend Chart (`trends.ts`)

- Buckets cases by ISO week, broken down by reason
- Output: `{ weeks: [{ week: "2026-W04", total, byReason: { [reason]: count } }] }`
- Covers full date range in data

### View C — Product Risk Alerts (`alerts.ts`)

- For each product: compare last 1-week reason counts against previous 4-week average
- **Threshold:** >30% deviation AND minimum 5 cases in current week (avoids noise on low-volume products)
- Output: `{ alerts: [{ product, reason, currentCount, avgCount, changePercent, severity }] }`
- Severity levels: `warning` (30-60% deviation), `critical` (>60% deviation)

### News tab integration

The `kundendienstInsights.alerts` array is read directly by the template's news tab rendering logic (no separate data key needed — the template JS reads from `reportData.kundendienstInsights.alerts`). The template renders these in a dedicated "Interne Signale" section at the top of `tab-news`, styled distinctly from external news (bordered card, muted background). No changes needed to `dashboard/lib/aggregator/news.ts` — this is purely a template-side concern.

### Python aggregator

Not mirrored in the Python `report/aggregator/` for now. Service case data is most valuable as live/dynamic dashboard data. Weekly report storage of service case summaries can be added later if needed.

## Dashboard Template

### Tab structure

New tab `tab-kundendienst` added to `styles/dashboard_template.html` navigation, positioned after the news tab (tab #11).

### Layout

```
+---------------------------------------------------+
| Kundendienst-Insights                             |
| Date filter: [7d] [30d] [90d] [All]              |
+---------------------------------------------------+
| Summary cards:                                    |
| [Total Cases] [Top Product] [Top Reason] [Alerts] |
+---------------------------------------------------+
| View A: Product Issue Heatmap                     |
| Category filter: [All] [Blutdruck] [TENS] [IR]   |
| Sort: [Total] [by column click]                   |
| Table: product rows x reason columns, color-coded |
+---------------------------------------------------+
| View B: Trend Chart                               |
| Product filter: [All / multi-select]              |
| Line chart: cases/week by reason (Chart.js)       |
+---------------------------------------------------+
| View C: Product Risk Alerts                       |
| Alert cards with severity indicators              |
+---------------------------------------------------+
```

### Rendering

- Pure JS/HTML reading from `window.reportData.kundendienstInsights`
- Date filter is client-side (JSON contains full date-range data, JS filters on render)
- Category filter and sort are client-side
- Heatmap color intensity: CSS background-color with opacity scaled to max value in matrix
- Trend chart: Chart.js (already used in existing template)

### News tab "Interne Signale" section

New section at top of `tab-news` rendering alerts from `kundendienstInsights.alerts`. Styled with bordered card and muted background to distinguish from external news items.

## Content Engine Integration

### DB function

New function in `db/client.py`:

```python
get_service_case_summary(product_model: str, client_id: str = "beurer", days: int = 90) -> dict | None
```

- Queries `service_cases` for the given product, last `days` days
- Returns: `{ product: "BM 81", total_cases: 187, top_reasons: [{ reason: "Label", count: 77, percent: 41 }, ...] }`
- Returns `None` if no data or query fails
- Top 5 reasons, sorted by count descending

### Lookup wrapper

`blog/product_catalog.py` gets a thin wrapper `get_product_service_insights(product_model)` that calls `db.client.get_service_case_summary()` and formats the result as a prompt-ready string. This keeps the Supabase query in `db/client.py` (where all DB operations live) while giving `product_catalog.py` a clean interface for the article pipeline.

### Integration point

`blog/article_service.py` assembles product context before calling Stage 2 writer. Service case summary is added to the context dict. Stage 2 prompt receives an optional section:

```
## Kundendienst-Daten (letzte 90 Tage)
BM 81: 187 Falle
- Label: 77 (41%)
- Beschwerde Software: 41 (22%)
- Anfrage Produkt: 30 (16%)
- Ersatzteilanfrage: 20 (11%)
- Beschwerde Produkt: 19 (10%)
```

### Fail-safe

If the query fails or returns no data, the article generates normally without service case context. No hard dependency on this data source.

## File Manifest

| Component | File | Action |
|-----------|------|--------|
| DB migration | `migrations/009_service_cases.sql` | New |
| Importer service | `services/service_case_importer.py` | New |
| Upload route | `routes/imports.py` | New |
| App mounting | `app.py` | Modify (mount new router) |
| DB operations | `db/client.py` | Modify (add 4 functions: save_service_cases, get_existing_case_ids, get_service_cases, get_service_case_summary) |
| Pydantic models | `models.py` | Modify (add `ServiceCaseImportResult` response model) |
| TS aggregator entry | `dashboard/lib/aggregator/service-cases/index.ts` | New |
| TS fetch | `dashboard/lib/aggregator/service-cases/fetch.ts` | New |
| TS heatmap | `dashboard/lib/aggregator/service-cases/heatmap.ts` | New |
| TS trends | `dashboard/lib/aggregator/service-cases/trends.ts` | New |
| TS alerts | `dashboard/lib/aggregator/service-cases/alerts.ts` | New |
| TS types | `dashboard/lib/aggregator/service-cases/types.ts` | New |
| TS main aggregator | `dashboard/lib/aggregator/index.ts` | Modify (call new module) |
| TS DashboardData type | `dashboard/lib/aggregator/types.ts` | Modify (add `kundendienstInsights` to `DashboardData`) |
| Dashboard route | `dashboard/app/api/dashboard/route.ts` | Modify (fetch service_cases, pass to aggregator) |
| Dynamic report route | `dashboard/app/api/dynamic-report/route.ts` | Modify (fetch service_cases, pass to aggregator) |
| Dashboard template | `styles/dashboard_template.html` | Modify (add tab #11 + news "Interne Signale" section) |
| Content engine wrapper | `blog/product_catalog.py` | Modify (add `get_product_service_insights()` wrapper) |
| Article service | `blog/article_service.py` | Modify (pass service case context to Stage 2) |
| Documentation | `docs/service-case-import.md` | New |

## Out of Scope

- Automated email/SFTP file pickup (manual upload only)
- Python aggregator mirror (TypeScript dynamic mode only)
- Editing/deleting individual cases (import-only)
- Salesforce API integration
- Upsert/update of existing cases (insert-only, dedup by case_id)

## Multi-Client Design

The `client_id` column is the sole multi-tenancy mechanism. To onboard a new client:

1. Use a new `client_id` value in the upload endpoint call
2. Add their product catalog to `report/constants.py` (new dict alongside `BEURER_PRODUCTS`)
3. All other components (regex extractor, aggregator, template) work unchanged — parameterized by table contents

## Test Data

Priority products from first Beurer batch (January 2026, 29,754 total cases):

| Product | Cases | Top Reasons |
|---------|-------|-------------|
| EM 59 | 381 | 31% Label, 26% Anfrage, 21% Beschwerde |
| BM 27 | 271 | 41% Label, 16% Ersatzteil, 15% Anfrage |
| BM 81 | 187 | 41% Label, 22% Beschwerde Software (unusually high) |
| IL 50 | 146 | 28% Anfrage, 25% Ersatzteil |
| IL 60 | 133 | 23% Beschwerde (highest complaint rate) |
| EM 89 | 71 | 39% Anfrage (user confusion indicator) |
| EM 55 | 55 | — |
| EM 50 | 54 | 63% Label |
| BM 25 | 53 | — |

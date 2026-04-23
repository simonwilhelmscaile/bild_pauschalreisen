# Service Case Import — Operator Guide

## Overview

This pipeline imports Salesforce customer service case data into the social listening service. Weekly CSV exports from Salesforce containing customer service cases are uploaded via a REST endpoint, parsed, and stored in the `service_cases` Supabase table. The data is displayed in the dashboard's **Kundendienst-Insights** tab alongside forum and review data, providing a direct signal from the support queue.

The import is additive and idempotent: cases with an existing `case_id` are skipped automatically, so the same file can be re-uploaded without creating duplicates.

---

## File Format

### Expected Columns

| Column | Description | Example |
|---|---|---|
| `Case Reason Number` | Unique case identifier from Salesforce | `CS-00012345` |
| `Product: Product Name` | Free-text product name field | `Beurer BM 27 Oberarm-Blutdruckmessgerät` |
| `Reason` | Reason category (see Known Reason Values below) | `Technischer Defekt` |
| `Created Date` | Case creation date in DD.MM.YYYY format | `15.03.2026` |

Additional columns present in the export are ignored.

### Supported File Formats

- **CSV** — semicolon (`;`) or comma (`,`) delimited. Delimiter is auto-detected. No manual configuration required.
- **HTML-table-as-XLS** — the standard Salesforce "Export to Excel" format, which is actually an HTML table with an `.xls` extension. The parser detects and handles this automatically.

### Encoding

The importer accepts UTF-8, UTF-8 with BOM, and cp1252 (German Windows default). Encoding is detected automatically. If umlauts appear garbled in the import response or in the dashboard, see the Troubleshooting section.

---

## How to Import

### Endpoint

```
POST /api/v1/social-listening/import/service-cases
```

**Query parameters:**

| Parameter | Default | Description |
|---|---|---|
| `client_id` | `beurer` | Client identifier, used to select the matching product catalog |

### curl Example

```bash
curl -X POST http://localhost:8000/api/v1/social-listening/import/service-cases \
  -F "file=@export.csv" \
  -F "client_id=beurer"
```

For HTML-as-XLS exports:

```bash
curl -X POST http://localhost:8000/api/v1/social-listening/import/service-cases \
  -F "file=@salesforce_export.xls" \
  -F "client_id=beurer"
```

### Response

```json
{
  "imported": 245,
  "skipped": 12,
  "errors": 0,
  "batch_id": "3f7a1c2e-8b4d-4e9a-b6f0-1d2e3f4a5b6c"
}
```

| Field | Description |
|---|---|
| `imported` | Number of new cases written to `service_cases` |
| `skipped` | Cases already present (matched by `case_id`), not re-imported |
| `errors` | Rows that could not be parsed (logged server-side) |
| `batch_id` | UUID identifying this import run; use for debugging or audit |

### Deduplication

Cases are deduplicated by the `case_id` field (`Case Reason Number` column). If a case with that ID already exists in the `service_cases` table, the row is skipped and counted in `skipped`. The `batch_id` from the original import is preserved.

---

## Product Matching

### Model Code Extraction

The importer extracts product model codes from the `Product: Product Name` field using the regex:

```
[A-Z]{2}\s?\d{2,3}
```

This matches patterns like `BM 27`, `EM59`, `BM 44`, `IL 50`. The optional space between the letter prefix and the number is handled automatically.

Examples:

| Raw product name | Extracted model code |
|---|---|
| `Beurer BM 27 Oberarm-Blutdruckmessgerät` | `BM 27` |
| `Beurer EM 59 TENS/EMS-Gerät` | `EM 59` |
| `Beurer IL 50 Infrarotlampe` | `IL 50` |
| `Beurer Handgelenkblutdruckmessgerät` | _(no match)_ |

### Category Assignment

Extracted model codes are matched against `BEURER_PRODUCT_CATALOG` in `report/constants.py` to assign a category:

| Category | Examples |
|---|---|
| `blood_pressure` | BM 27, BM 44, BM 54, BC 57 |
| `pain_tens` | EM 49, EM 59, EM 95 |
| `infrarot` | IL 21, IL 50 |

Products that do not match any catalog entry are stored with `category = null`. The dashboard's Kundendienst-Insights tab defaults to displaying only categorized (health) products. Uncategorized cases remain in the `service_cases` table and can be queried directly if needed.

---

## Dashboard Views

The Kundendienst-Insights tab provides three views, all filterable by date range and product category.

### View A — Product Issue Heatmap

A grid of **products × reasons** with color-coded intensity indicating case volume. High-frequency product/reason combinations are immediately visible. Useful for identifying which products generate the most support load and for which reasons.

### View B — Trend Chart

Weekly case counts broken down by reason, with an optional product filter. Shows whether a particular issue is growing, stable, or declining over time. The x-axis represents calendar weeks; each reason is a separate line or bar series.

### View C — Product Risk Alerts

Automated anomaly detection. An alert is raised when a product + reason combination in the current week deviates more than **30% above** its 4-week rolling average. Alerts surface in the Kundendienst-Insights tab and also appear in the main **News** tab under the **"Interne Signale"** section, alongside forum-derived signals.

---

## Adding a New Client

The import pipeline is client-agnostic. To onboard a new customer:

1. Use a new `client_id` value in the upload call (e.g., `client_id=acme`).
2. Add the corresponding product catalog to `report/constants.py` — follow the existing `BEURER_PRODUCT_CATALOG` structure, mapping model codes to category strings.
3. Everything else (parsing, deduplication, dashboard rendering) works unchanged.

No code changes are required beyond adding the catalog entry.

---

## Known Salesforce Reason Values

The following 15 reason categories are used in Beurer's Salesforce instance. The importer stores the `Reason` field verbatim; these values are not validated on import.

1. Technischer Defekt
2. Fehlbedienung
3. Lieferung unvollständig
4. Falsches Produkt geliefert
5. Produkt nicht wie beschrieben
6. Manschette / Elektroden defekt
7. Display-/Anzeigeproblem
8. App-Verbindungsproblem
9. Akku / Batterie defekt
10. Garantieantrag
11. Ersatzteilanfrage
12. Bedienungsanleitung / Dokumentation
13. Messwertunsicherheit
14. Hautreaktion / Verträglichkeit
15. Sonstiges

---

## Troubleshooting

### Garbled umlauts (ä, ö, ü appear as â€™ or similar)

The file encoding was not detected correctly. Re-save the CSV from Excel as **UTF-8** (not the default "CSV" which uses cp1252 on German Windows), or save with BOM. Alternatively, open the file in Notepad++, verify the encoding shown in the status bar, and convert explicitly before uploading.

### Missing columns error

The importer expects the exact column headers listed in the File Format section. Common causes:
- Salesforce report layout was changed and columns were renamed or reordered.
- A different report view was exported (e.g., account-level rather than case-level).

Check that all four required columns (`Case Reason Number`, `Product: Product Name`, `Reason`, `Created Date`) are present with exactly those names.

### All rows skipped (`skipped` equals total row count, `imported` is 0)

All cases in the file have already been imported. This is expected behavior for re-uploads. Check the `batch_id` from the original import run to confirm when the data was first loaded. If the file is genuinely new, verify that the `Case Reason Number` values differ from the previously imported set.

### File not parsed (500 error or 0 rows detected)

The file type was not recognized. Confirm whether the export is a true CSV or an HTML-table-as-XLS (the standard Salesforce "Export" button produces the latter). Both are supported, but if the file extension is `.csv` and the content is actually HTML, rename it to `.xls` before uploading, or contact the developer to add explicit content-sniffing for that case.

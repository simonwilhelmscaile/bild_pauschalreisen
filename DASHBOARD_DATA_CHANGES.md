# Dashboard Data Changes — February 2026

This document describes all backend data changes that affect the dashboard. Use this to update `styles/dashboard_template.html` and `dashboard/template/dashboard_template.html`.

## Overview

The report JSON (stored in `weekly_reports.report_data`) now includes several new keys and modified structures. The dashboard template reads this JSON via `__DASHBOARD_DATA__` and should be updated to display the new data.

---

## 1. New Fields on Social Items (available in report data)

### Per-Item Enrichment Fields
Items now carry these additional fields (populated by classification):

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `emotion` | string | `frustration`, `relief`, `anxiety`, `satisfaction`, `confusion`, `anger`, `hope`, `resignation` | Dominant emotion expressed |
| `intent` | string | `purchase_question`, `troubleshooting`, `experience_sharing`, `recommendation_request`, `comparison`, `general_question`, `complaint`, `advocacy` | User's posting intent |
| `sentiment_intensity` | int | 1-5 | How strongly sentiment is expressed |
| `engagement_score` | float | varies | Platform-specific engagement metric |
| `language` | string | `de`, `en`, `other` | Detected language (default: `de`) |
| `resolved_source` | string | domain name | Actual domain for serper-crawled items |
| `question_content` | text | — | Full question text (from deep-crawled Q&A) |
| `has_answers` | bool | — | Whether answers/comments were collected |
| `answer_count` | int | — | Number of answers/comments stored |

### German Labels (from `report/constants.py`)
```python
EMOTION_LABELS_DE = {
    "frustration": "Frustration", "relief": "Erleichterung",
    "anxiety": "Angst/Sorge", "satisfaction": "Zufriedenheit",
    "confusion": "Verwirrung", "anger": "Ärger/Wut",
    "hope": "Hoffnung", "resignation": "Resignation"
}

INTENT_LABELS_DE = {
    "purchase_question": "Kaufberatung", "troubleshooting": "Fehlerbehebung",
    "experience_sharing": "Erfahrungsbericht", "recommendation_request": "Empfehlungssuche",
    "comparison": "Produktvergleich", "general_question": "Allgemeine Frage",
    "complaint": "Beschwerde", "advocacy": "Empfehlung/Lob"
}

ASPECT_LABELS_DE = {
    "messgenauigkeit": "Messgenauigkeit", "bedienbarkeit": "Bedienbarkeit",
    "verarbeitung": "Verarbeitung", "preis_leistung": "Preis-Leistung",
    "app_konnektivitaet": "App & Konnektivität",
    "manschette_elektroden": "Manschette/Elektroden",
    "display_anzeige": "Display & Anzeige", "schmerzlinderung": "Schmerzlinderung",
    "akku_batterie": "Akku & Batterie", "kundenservice": "Kundenservice"
}
```

---

## 2. New Report JSON Keys

### 2.1 `volume_by_source_category` (NEW)
Groups sources into business-meaningful categories instead of raw source names.

```json
{
    "volume_by_source_category": {
        "Foren": 450,
        "Shops & Bewertungen": 380,
        "Testberichte & Medien": 120,
        "Video": 95,
        "Gesundheitsportale": 60,
        "Sonstige": 23
    }
}
```

**Dashboard suggestion:** Add a donut/pie chart or horizontal bar chart showing source category distribution. This replaces the confusing `serper_brand`/`serper_discovery` labels with user-friendly categories.

### 2.2 `volume_by_source` (CHANGED)
Now uses resolved domain names instead of internal crawler names. For example:
- Before: `{"serper_brand": 120, "serper_discovery": 95, "gutefrage": 80, ...}`
- After: `{"gutefrage.net": 80, "amazon.de": 65, "chip.de": 30, "otto.de": 25, ...}`

**Dashboard impact:** Source breakdown charts will now show actual domains. No code change needed if the template just iterates the keys — the values are now more meaningful.

### 2.3 `journey_intelligence.journey_spine` (NEW)
The key new data structure. Cross-dimensional analysis anchored to each journey stage.

```json
{
    "journey_spine": {
        "total": 1200,
        "stages": [
            {
                "stage": "awareness",
                "label_de": "Bewusstwerdung",
                "count": 520,
                "percentage": 43,
                "pain_breakdown": [
                    {"pain_category": "ruecken_schmerzen", "label_de": "Rückenschmerzen", "count": 45, "quote": "Seit 5 Jahren..."}
                ],
                "coping_strategies": [
                    {"strategy": "arztbesuch", "label_de": "Arztbesuch", "count": 45, "positive_pct": 6,
                     "top_frustration": "Arzt nimmt nicht ernst", "frustration_count": 18}
                ],
                "life_situations": [
                    {"life_situation": "chronisch_krank", "label_de": "Chronisch krank", "count": 31,
                     "top_pain": "Rückenschmerzen", "quote": "Seit Jahren chronische LWS..."}
                ],
                "frustrations": [
                    {"frustration": "arzt_nimmt_nicht_ernst", "label_de": "Arzt nimmt nicht ernst",
                     "count": 18, "quote": "Mein Arzt meinte einfach..."}
                ],
                "bridge_to_next": [
                    {"bridge_type": "arzt_empfiehlt_geraet", "label_de": "Arzt empfiehlt → Gerätekauf", "count": 14}
                ],
                "representative_quotes": [
                    {"text": "Beim Arzt war mein BD 160/100...", "source": "onmeda", "url": "..."}
                ],
                "emotion_distribution": {"frustration": 45, "anxiety": 30, "confusion": 15, "hope": 10},
                "intent_distribution": {"general_question": 40, "recommendation_request": 25, "troubleshooting": 20}
            }
            // ... more stages: consideration, comparison, purchase, advocacy
        ]
    }
}
```

**Dashboard suggestion:** This is the centerpiece. Build a vertical journey flow/timeline where each stage expands to show:
- Pain breakdown (what hurts)
- Coping strategies (what they try) with effectiveness %
- Frustrations (what blocks them) with real quotes
- Life situations (who they are)
- Bridge moments (what triggers the next stage)
- Emotion & intent distributions (small bar charts)
- Representative quotes with source attribution

This addresses Simon's feedback P4 (no quotes), P5 (life situations lack detail), P6 (frustrations all "—"), P7 (journey sections siloed), P10 (bridge moments lack percentages).

### 2.4 `journey_intelligence.pain_breakdown` (NEW)
Resolves the "Sonstige Schmerzen" problem (Simon's P3).

```json
{
    "pain_breakdown": {
        "total": 800,
        "sonstige_count": 250,
        "sonstige_resolved_pct": 72,
        "categories": [
            {"pain_category": "ruecken_schmerzen", "label_de": "Rückenschmerzen", "count": 180, "percentage": 23},
            {"pain_category": "sonstige_schmerzen", "label_de": "Sonstige Schmerzen", "count": 250, "percentage": 31}
        ],
        "resolved_sonstige": [
            {"pain_location": "unterer_ruecken", "label_de": "Unterer Rücken", "count": 80},
            {"pain_location": "nacken", "label_de": "Nacken/HWS", "count": 45},
            {"pain_location": "knie", "label_de": "Knie", "count": 30},
            {"pain_location": "unresolved", "label_de": "Nicht zugeordnet", "count": 70}
        ]
    }
}
```

**Dashboard suggestion:** Show pain categories with a "drill-down" for Sonstige Schmerzen that reveals the specific pain locations. A stacked bar or treemap works well.

### 2.5 `deep_insights.aspect_analysis` (NEW)
Aspect-based sentiment — shows how users feel about specific product dimensions.

```json
{
    "aspect_analysis": {
        "total_items_with_aspects": 120,
        "aspects": [
            {
                "aspect": "messgenauigkeit",
                "label_de": "Messgenauigkeit",
                "total_mentions": 45,
                "positive_pct": 20,
                "neutral_pct": 15,
                "negative_pct": 65,
                "avg_intensity": 4.2,
                "evidence_snippets": ["Völlig hanebüchende Messungen...", "Sehr genau und zuverlässig"]
            },
            {
                "aspect": "bedienbarkeit",
                "label_de": "Bedienbarkeit",
                "total_mentions": 38,
                "positive_pct": 75,
                "neutral_pct": 15,
                "negative_pct": 10,
                "avg_intensity": 3.8,
                "evidence_snippets": ["Die einknopfige Variante ist vollkommen ausreichend"]
            }
        ]
    }
}
```

**Dashboard suggestion:** A horizontal bar chart with positive/negative split per aspect (like a diverging bar chart). Include avg_intensity as a secondary metric. This gives the CMO a clear picture of product strengths vs weaknesses by specific dimension.

### 2.6 `deep_insights.medication_breakdown` (CHANGED)
Now includes medication class grouping and pain cross-reference.

```json
{
    "medication_breakdown": {
        "by_category": {
            "blood_pressure": [
                {"medication": "Ramipril", "count": 15, "context_label": "Blutdruck", "top_pain": null}
            ],
            "pain_tens": [
                {"medication": "Ibuprofen", "count": 22, "context_label": "Schmerz/TENS", "top_pain": "Rückenschmerzen"}
            ]
        },
        "by_class": {
            "Schmerzmittel": {
                "total": 45,
                "medications": [{"medication": "Ibuprofen", "count": 22}, {"medication": "Paracetamol", "count": 12}]
            },
            "Blutdruck-Medikamente": {
                "total": 30,
                "medications": [{"medication": "Ramipril", "count": 15}, {"medication": "Metoprolol", "count": 8}]
            }
        }
    }
}
```

**Dashboard suggestion:** Group by medication class with expandable details. Show which pain category each medication is most associated with.

### 2.7 `product_intelligence` (ENHANCED)
Now includes entity-based data with richer sentiment and mention type breakdown.

```json
{
    "product_intelligence": {
        "beurer": {
            "BM 27": {
                "count": 35,
                "sentiment": {"positive": 15, "neutral": 12, "negative": 8},
                "mention_types": {"direct": 25, "comparison": 7, "recommendation": 3},
                "top_issues": ["Messgenauigkeit", "Manschette/Elektroden"],
                "top_praise": ["Bedienbarkeit", "Preis-Leistung", "Display & Anzeige"]
            }
        }
    }
}
```

**Changes from before:**
- `top_issues` and `top_praise` now use aspect labels (e.g., "Messgenauigkeit") instead of raw keywords ("ungenau")
- New `mention_types` field shows how products are mentioned (direct, comparison, recommendation, complaint)
- Products are matched via canonical entity names (no more "BM27" vs "BM 27" duplicates)

**Dashboard suggestion:** Product cards or a table with sentiment bars per product. Add mention_type breakdown as small badges or a tooltip.

### 2.8 `competitive_intelligence` (ENHANCED)
Now uses entity-based mention types for richer context classification.

**Changes:** The `context_breakdown` per competitor brand now reflects entity-level `mention_type` data when available, giving more accurate classification of why competitors are mentioned.

---

## 3. Source Display Changes (Simon's P1)

Throughout the report data, sources are now resolved:
- `serper_brand` / `serper_discovery` → actual domain names (e.g., `chip.de`, `otto.de`, `testberichte.de`)
- Items have `_display_source` set during data fetching
- `volume_by_source` uses resolved names
- Source highlights use resolved names
- Bridge moments use resolved names

**Dashboard impact:** Any place showing source names will now show actual domains. The `volume_by_source_category` key provides a grouped view (Foren, Shops, Testberichte, Video).

---

## 4. Language Filtering

Reports now filter to `language='de'` by default. English posts (like Reddit) are excluded from the German-market analysis. This addresses Simon's P12 feedback.

The report endpoint accepts `?language=en` for an English-only view or the fetch layer accepts `language='all'` for everything.

---

## 5. Existing Keys Unchanged

These report keys are unchanged and the dashboard sections using them need no updates:
- `period`, `generated_at`
- `executive_summary`, `executive_dashboard`
- `alerts` (critical/monitor/opportunity)
- `volume_by_category`, `sentiment_by_category`
- `trending_topics`
- `user_voice` (top_questions, questions_by_category, pain_points)
- `content_opportunities`
- `top_posts`
- `source_highlights` (though source names are now resolved)
- `appendices` (device_questions, negative_experiences, positive_experiences)
- `key_actions`
- `sentiment_deepdive`
- `wow_metrics`
- `journey_intelligence.journey_funnel` (still present alongside journey_spine)
- `journey_intelligence.pain_landscape`
- `journey_intelligence.solution_distribution`
- `journey_intelligence.bridge_moments`
- `journey_intelligence.bridge_taxonomy`
- `journey_intelligence.opportunity_map`
- `category_journeys`
- `deep_insights.coping_analysis`
- `deep_insights.life_situations`
- `deep_insights.frustration_map`
- `deep_insights.pain_sub`
- `deep_insights.bp_sub`

---

## 6. Dashboard Update Priority

### High Priority (new data, high value)
1. **Journey Spine visualization** — `journey_intelligence.journey_spine` — the centerpiece, addresses 5 of Simon's feedback points
2. **Aspect-based sentiment** — `deep_insights.aspect_analysis` — product strength/weakness radar
3. **Source category grouping** — `volume_by_source_category` — cleaner source display

### Medium Priority (enhanced existing)
4. **Resolved source names** — update source displays to show domains not crawler names
5. **Pain breakdown drill-down** — `journey_intelligence.pain_breakdown` — resolve "Sonstige"
6. **Enhanced product intelligence** — show mention_types and aspect-based issues/praise

### Lower Priority (nice to have)
7. **Emotion/intent distributions** — available per journey stage, could add small charts
8. **Medication class grouping** — `deep_insights.medication_breakdown.by_class`
9. **Engagement scores** — available on items for sorting/highlighting high-engagement posts

---

## 7. File References

| File | Purpose |
|------|---------|
| `report/data_aggregator.py` | Builds all report data structures |
| `report/constants.py` | All German labels, aspect/emotion/intent values, source category map |
| `report/text_generator.py` | LLM prose generation (unchanged) |
| `report/dashboard_renderer.py` | Injects JSON into HTML template |
| `styles/dashboard_template.html` | Python-served dashboard template |
| `dashboard/template/dashboard_template.html` | Vercel-served dashboard template (must stay in sync) |
| `beurer_social_listening_dashboard_KW6.html` | Reference dashboard from before changes |

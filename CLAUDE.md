# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Social listening service for Beurer (German health device company). Crawls German health forums and review platforms to extract user questions/discussions about blood pressure monitors, TENS devices, and pain management.

**Three-tier system:**
1. **Python backend** (FastAPI) — crawlers, classification pipeline, data aggregation, LLM enrichment
2. **Next.js dashboard** (`dashboard/`) — reads report data from Supabase, injects into HTML template, deployed on Vercel at `social-listening-service.vercel.app`
3. **GitHub Actions** (`.github/workflows/weekly-pipeline.yml`) — weekly cron (Monday 06:00 UTC) runs the full crawl → classify → report pipeline

Developed on Windows. Python 3.11. The `report/` package provides data aggregation and LLM enrichment; the `dashboard/` Next.js 15 app (API-only, no UI pages) serves the interactive HTML dashboard.

## Development Commands

```bash
# Backend setup
pip install -r requirements.txt
cp .env.example .env  # Then edit with your API keys

# Test API connections
python scripts/test_tools.py

# Test Reddit crawler (no API keys required)
python scripts/test_reddit.py

# Run the backend server
python app.py
# Or with hot reload (auto-kills existing process on port 8000, Windows-aware):
python dev.py
# Or manually:
uvicorn app:app --reload --port 8000

# Dashboard setup (Next.js)
cd dashboard
npm install
cp .env.example .env.local  # Add SUPABASE_URL + SUPABASE_SERVICE_KEY + DASHBOARD_PASSWORD
npm run dev  # Starts on port 3000
```

**No linting/formatting/test frameworks configured.** Tests are manual scripts in `scripts/` (`test_tools.py`, `test_reddit.py`, `run_serper_test.py`) that test API connections and crawlers directly. No pytest, ruff, or similar tooling.

## Environment Variables

**Backend** (`.env`): `BEURER_SUPABASE_URL`, `BEURER_SUPABASE_KEY`, `FIRECRAWL_API_KEY`, `APIFY_API_TOKEN`, `GEMINI_API_KEY`, `SERPER_API_KEY`

**Dashboard** (`dashboard/.env.local`): `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `DASHBOARD_PASSWORD`, `GEMINI_API_KEY` (for article generation)

## Architecture

**Key Packages:**
- `app.py` → FastAPI entry point (mounts router at `/api/v1`)
- `models.py` → Pydantic models (`CrawlRequest`, `CrawlResponse`, `SocialItemCreate`, `CrawlerRun`)
- `config/` → Centralized configuration (`settings.py` with `Settings` class, `logging.py` with `setup_logging()`)
- `routes/` → API endpoints split by concern:
  - `routes/core.py` → health, crawl, items, runs, search, stats
  - `routes/backfill.py` → 13 backfill endpoints with DRY `_run_backfill()` helper
  - `routes/reports.py` → weekly/initial/backtest reports + enrichment pipeline
- `db/client.py` → Supabase client + dedup helpers (`save_social_item`, `item_exists`, `get_beurer_supabase`)
- `classification/` → LLM classification pipeline split by concern:
  - `core.py` → `classify_item()`, `backfill_classifications()`
  - `journey.py` → `classify_journey_stage()`, `backfill_journey_stages()`
  - `deep_insights.py` → `classify_deep_insights()`, `backfill_deep_insights()`
  - `entity_sentiment.py` → `classify_entity_sentiments()`, `backfill_entity_sentiments()`
  - `medication.py`, `language.py`, `source_resolution.py`, `engagement.py`
- `services/` → Shared services:
  - `services/gemini.py` → Shared Gemini API client; models: `gemini-embedding-001`, `gemini-2.0-flash`, `gemini-2.5-pro`
  - `services/embedding.py` → Gemini gemini-embedding-001 (768 dims) for vector embeddings
  - `services/entity_matching.py` → Deterministic entity matching (product/brand alias scanning, no LLM)
  - `services/answer_backfill.py` → Re-crawls source pages to populate `social_item_answers` table
  - `services/report_store.py` → DB operations for saving/retrieving weekly reports
- `utils/dates.py` → Date parsing (ISO, Unix, German relative "vor 2 Tagen", German format "01.01.2024")
- `scripts/` → Utility/test scripts (`run_reclassify.py`, `seed_entities.py`, `test_tools.py`, etc.)
- `crawlers/base_crawler.py` → ABC with run lifecycle (create run → fetch → save → update), health relevance filtering, weekly mode date filtering

**Crawlers by Tool:**
- `crawlers/firecrawl_runner.py` → GutefrageCrawler, HealthForumsCrawler (+ individual forum crawlers)
- `crawlers/apify_runner.py` → AmazonCrawler, RedditCrawler, YouTubeCrawler, TikTokCrawler, InstagramCrawler
- `crawlers/serper_runner.py` → SerperDiscoveryCrawler, SerperBrandMentionsCrawler
- `crawlers/content_utils.py` → Shared content extraction/cleaning (used by HealthForumsCrawler + Serper crawlers for deep crawling)

**Data Flow:**
1. `POST /crawl` instantiates crawler by name from `routes/core.py`
2. `BaseCrawler.run()` creates `crawler_runs` record, calls subclass `fetch_items()`
3. Each item deduped by `source_url`, saved to `social_items`
4. `/backfill/embeddings` → Gemini gemini-embedding-001 (768 dimensions)
5. `/backfill/language-detection` → deterministic German/English/other heuristic (no LLM)
6. `/backfill/sources` → resolve serper domain names + populate `resolved_source`
7. `/backfill/engagement-scores` → compute engagement scores from raw_data (no LLM)
8. `/backfill/entities` → deterministic entity matching via alias scanning (no LLM)
9. `/backfill/classifications` → Gemini 2.0 Flash (category, sentiment, keywords, relevance, emotion, intent, sentiment_intensity)
10. `/backfill/journey-stages` → classify journey stage, pain category, solutions
11. `/backfill/deep-insights` → granular sub-classifications + aspect-based sentiment extraction
12. `/backfill/entity-sentiment` → LLM-based per-entity sentiment from item_entities junction
13. `/backfill/dates` → parse and normalize posted_at dates
14. `/backfill/date-extraction` → re-crawl health forum source URLs via Firecrawl to extract actual post dates (not in weekly CI)
15. `/backfill/normalize-medications` → standardize medication name mentions (not in weekly CI)
16. `/backfill/answers` → re-crawl source pages to extract Q&A answers into `social_item_answers` (not in weekly CI)

**Report Data Pipeline:** The `report/` package provides data aggregation and LLM enrichment for the dashboard:
- `report/constants.py` → Brand colors, product catalogs (28 Beurer + 13 competitor), category labels, score definitions, journey/pain constants, emotion/intent/aspect values, source category mapping
- `report/aggregator/` → Deterministic data aggregation split into modular components:
  - `main.py` → `aggregate_report_data()`, `aggregate_initial_report_data()`, executive dashboard
  - `fetch.py` → `fetch_items_for_period()`, `fetch_all_items()`, WoW metrics
  - `utils.py` → Shared helpers (categorization, scoring, quote extraction)
  - `alerts.py`, `product_intelligence.py`, `appendices.py`, `sentiment.py`, `competitive.py` → Section builders
  - `journey.py` → All journey functions (funnel, spine, bridges, Q&A, pain, solutions)
  - `deep_insights.py` → Coping, personas, frustrations, aspects, medications
  - `enrichment.py` → All `enrich_*` LLM wrapper functions
- `report/text_generator.py` → LLM prose generation (German) via Gemini 2.5 Pro
- `report/prompts/weekly_report.txt` → German prompt template for weekly reports
- `report/prompts/initial_report.txt` → German prompt template for initial baseline reports

- `report/dashboard_renderer.py` → `render_dashboard()` reads `styles/dashboard_template.html`, injects data as JSON, returns self-contained HTML

**Dashboard Frontend (Next.js):**
- `dashboard/app/api/dashboard/route.ts` → Serves stored weekly report or dynamic data. Supports `?lang=de|en`, `?week=YYYY-MM-DD`, and `?days=7|14|30` (dynamic mode)
- `dashboard/app/api/dynamic-report/route.ts` → JSON API for live data: queries `social_items` → TypeScript aggregator → returns JSON. 5-min in-memory cache keyed by `days+lang`
- `dashboard/app/api/report/route.ts` → JSON API for raw report data
- `dashboard/app/api/auth/route.ts` → Password authentication
- `dashboard/middleware.ts` → Cookie-based auth; shows login page if `DASHBOARD_PASSWORD` is set and no valid `dashboard_token` cookie
- `dashboard/lib/supabase.ts` → Server-side Supabase client
- `dashboard/lib/constants.ts` → TypeScript port of `report/constants.py` (product catalogs, label maps, patterns)
- `dashboard/lib/aggregator/` → TypeScript port of `report/aggregator/` (~30 modules). Main entry: `aggregateReportData(items, startDate, endDate)` → `DashboardData`. Sub-modules: `fetch.ts` (Supabase queries), `volume.ts`, `alerts.ts`, `product-intelligence.ts`, `sentiment-deepdive.ts`, `competitive-intelligence.ts`, `journey/*.ts` (11 modules), `deep-insights/*.ts` (8 modules)
- `dashboard/template/dashboard_template.html` → Auto-copied from `styles/dashboard_template.html` at build time (via `npm run copy-template`). **Only edit `styles/dashboard_template.html`** — the dashboard copy is gitignored and regenerated.

Public API in `report/__init__.py`:
```
fetch_items_for_period() → aggregate_report_data() → [enrich_appendices_with_actions()] → render_dashboard()
```

**Report Types & Enrichment:** `routes/reports.py` runs 9 LLM enrichment stages per report (each wrapped in try-except — if any fails, data stays unmodified): `enrich_alerts_with_analysis`, `enrich_dashboard_with_insights`, `enrich_content_opportunities_data`, `enrich_competitive_intelligence_data`, `enrich_sentiment_deepdive_data`, `enrich_journey_intelligence`, `enrich_qa_threads`, `enrich_deep_insights`, `enrich_category_journeys`.

- **Weekly Report** (`POST /report/weekly`): Standard weekly analysis for ongoing monitoring
- **Initial Report** (`POST /report/initial`): Baseline report with full database history + recent week comparison (for client onboarding)
- **Backtest** (`POST /report/backtest`): Generate reports for successive past weeks to build Week-over-Week history
- All support `?format=json|markdown|full|dashboard` and `language=de|en` (default: `de`)

## Crawlers

Crawler classes live in `crawlers/firecrawl_runner.py`, `crawlers/apify_runner.py`, and `crawlers/serper_runner.py`. Crawler names are mapped to classes in `routes/core.py`'s `run_crawler()` function.

**Crawler Name → Class Mapping:**
| Name | Class | Notes |
|------|-------|-------|
| `gutefrage` | GutefrageCrawler | |
| `amazon` | AmazonCrawler | |
| `health_forums` | HealthForumsCrawler | All forums |
| `diabetes_forum`, `endometriose`, `rheuma_liga`, `onmeda` | HealthForumsCrawler | Single forum via `forum_key` |
| `reddit` | RedditCrawler | |
| `youtube` | YouTubeCrawler | Three-step: search videos (with subtitles) → extract transcripts (`youtube_transcript`) → scrape comments (`youtube`) |
| `tiktok` | TikTokCrawler | |
| `instagram` | InstagramCrawler | |
| `serper_discovery` | SerperDiscoveryCrawler | Supports `deep_crawl` option |
| `serper_brand` | SerperBrandMentionsCrawler | Supports `deep_crawl` option |

**Adding a New Crawler:**
1. Create class in `crawlers/firecrawl_runner.py`, `crawlers/apify_runner.py`, or `crawlers/serper_runner.py`
2. Extend `BaseCrawler`, set `name` and `tool` class attributes
3. Implement `async def fetch_items(self, config: Dict) -> List[Dict]`
4. Return dicts with: `source`, `source_url`, `title`, `content`, `posted_at`, `crawler_tool`, `raw_data`
5. Use `parse_to_yyyy_mm_dd()` from `utils.dates` for all dates
6. Add to exports in `crawlers/__init__.py`
7. Add route handling in `routes/core.py` `run_crawler()` function

**Weekly Mode:** Crawlers support `weekly_mode=True` in config for cron jobs. Serper crawlers use API-level time filtering; others use post-fetch filtering on `posted_at` via `BaseCrawler._filter_items_by_date()`.

## Database (Supabase)

**Tables:**
- `social_items` → Crawled content (deduped by `source_url`). Min content: 30 chars (10 for TikTok/Instagram). Includes Q&A fields (`question_content`, `has_answers`, `answer_count`) and enrichment fields (`emotion`, `intent`, `sentiment_intensity`, `engagement_score`, `language`, `resolved_source`)
- `social_item_answers` → Individual answers/comments per social_item (Q&A structure)
- `entities` → Product/brand registry with aliases for deterministic matching
- `item_entities` → Junction table: social_item ↔ entity with per-entity sentiment and mention_type
- `item_aspects` → Aspect-based sentiment per social_item (10 aspect categories)
- `crawler_runs` → Audit log with `crawler_run_id` foreign key
- `weekly_reports` → Optional, report service handles missing table gracefully

**Semantic search:** `POST /search` uses Gemini embeddings + Supabase RPC function `search_social_items` for vector similarity.

## Classification Schema

**Categories:** `blood_pressure`, `pain_tens`, `infrarot`, `menstrual`, `other`

**Core Fields:** `category`, `sentiment` (positive/neutral/negative), `keywords` (3-5 German), `relevance_score` (0.0-1.0), `product_mentions` (array), `device_relevance_score` (0.0-1.0), `emotion` (8 values), `intent` (8 values), `sentiment_intensity` (1-5)

**Journey Intelligence Fields:** `journey_stage` (awareness/consideration/comparison/purchase/advocacy), `pain_category` (7 categories in `report/constants.py`), `solutions_mentioned` (array of solution types), `beurer_opportunity` (text), `collection_type` (brand/journey)

**Deep Insight Fields:** `pain_location`, `pain_severity`, `pain_duration`, `bp_concern_type`, `bp_severity`, `coping_strategies` (array), `medications_mentioned` (array), `life_situation`, `solution_frustrations` (array), `negative_root_cause`, `key_insight`, `content_opportunity`, `bridge_moment`

**Aspect Categories (10):** `messgenauigkeit`, `bedienbarkeit`, `verarbeitung`, `preis_leistung`, `app_konnektivitaet`, `manschette_elektroden`, `display_anzeige`, `schmerzlinderung`, `akku_batterie`, `kundenservice`

## Operational Notes

**Typical workflow:** Crawl → Embed → Language Detection → Sources → Engagement Scores → Entities → Classify → Journey Stages → Deep Insights → Entity Sentiment → Dates → Generate Dashboard Data (see Data Flow above for full endpoint list and order)

**Rate Limits:**
- Gemini API (free tier): 60 RPM → classification adds 1.1s delay per item
- Firecrawl: 2s delay between requests

**Content Minimums:** 30 chars default, 10 chars for TikTok/Instagram

**Embedding Dimensions:** 768 (Gemini gemini-embedding-001) → DB column is `vector(768)`

## CI/CD

**GitHub Actions** (`.github/workflows/weekly-pipeline.yml`): Runs every Monday 06:00 UTC (also manually triggerable via `workflow_dispatch`). Steps:
1. Starts the FastAPI server on the runner
2. Crawls all sources with `weekly_mode: true` (gutefrage, health_forums, reddit, amazon, youtube, serper_discovery, serper_brand)
3. Runs the backfill pipeline (embeddings → language-detection → sources → engagement-scores → entities → classifications → journey-stages → deep-insights → entity-sentiment → dates)
4. Generates weekly report with `format=full` (saves to `weekly_reports` table in Supabase)

**Vercel** auto-deploys the `dashboard/` directory. The Next.js app defaults to live dynamic data (TypeScript aggregator queries `social_items` directly). Stored weekly reports are available via `?week=YYYY-MM-DD`.

## Debugging

**Check crawler run status:**
```bash
curl http://localhost:8000/api/v1/social-listening/runs
```

**Check stats:**
```bash
curl http://localhost:8000/api/v1/social-listening/stats
```

**Common issues:**
- "Embedding service error" → Check `GEMINI_API_KEY` in `.env`
- "Firecrawl failed" → Check `FIRECRAWL_API_KEY`, may be rate limited
- Items not saving → Check `source_url` uniqueness (dedup by URL)
- Classification stuck → Gemini rate limit, wait or reduce batch size

**Logs:** FastAPI logs to stdout. Crawlers use `logging.getLogger(__name__)`.

**Bulk Re-classification:** `scripts/run_reclassify.py` runs classifications directly (no HTTP) with exponential backoff. Supports `--phase 1|2|3` (classify, journey-stages, deep-insights), `--batch`, `--after-id`. Logs to `reclassify.log`.

## API Reference

All endpoints under `/api/v1/social-listening/`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/items` | List crawled items (paginated) |
| GET | `/runs` | Crawler run audit records |
| GET | `/stats` | DB statistics (counts, classification coverage) |
| GET | `/stats/noise` | Noise/irrelevant item statistics |
| POST | `/crawl` | Run a crawler by name |
| POST | `/search` | Semantic vector similarity search |
| POST | `/report/weekly` | Weekly report (`?format=json\|markdown\|full\|dashboard`, `?language=de\|en`) |
| GET | `/report/weekly` | Retrieve stored weekly report |
| POST | `/report/initial` | Baseline report (full DB history + recent week) |
| POST | `/report/backtest` | Generate reports for past N weeks (`?weeks=4`) |
| POST | `/backfill/*` | 13 backfill endpoints (see Data Flow above) |

## Key Design Decisions

**Hybrid deterministic + LLM**: `report/aggregator/` is fully deterministic (counting, grouping, sorting). `text_generator.py` adds prose/insights on top. Each LLM enrichment stage fails independently without corrupting base data.

**Self-contained dashboard**: The HTML dashboard has no runtime API dependencies. Weekly reports embed all data as JSON at build time. Dynamic mode queries Supabase via a TypeScript aggregator that mirrors the Python aggregator — same JSON structure, same template, but without LLM enrichment.

**Deterministic entity matching**: Product/brand detection uses alias scanning against a curated catalog (`report/constants.py`), not LLM extraction. Consistent, reproducible results.

**Journey-as-spine**: Items tagged with `collection_type` (brand vs journey) at crawl time, then classified into journey stages as a separate backfill phase. Journey tab exists independently of category-based analysis.

## Reference

- `SOCIAL_LISTENING_ENGINEERING_BRIEF.md` — Complete database schema, all URLs to crawl, and acceptance criteria. Note: the brief references OpenAI embeddings (1536 dims) which were replaced with Gemini gemini-embedding-001 (768 dims) during implementation.
- `DASHBOARD_DATA_CHANGES.md` — Documents all new and changed report JSON keys for the dashboard template. Key reference when modifying `styles/dashboard_template.html` or `dashboard/template/dashboard_template.html`.

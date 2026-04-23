# Social Listening Engineering Brief v3.0

**Date:** January 29, 2026  
**Project:** Beurer Content PoC  
**Client Deadline:** Thursday, February 6, 2026 (Weekly Sync #2)  
**Priority:** CRITICAL - First deliverable to client

---

## 🎯 PROJECT CONTEXT (Read This First)

### What is Beurer?
Beurer is a German health device manufacturer. They make:
- **Blood pressure monitors** (BM series): Devices people use at home to measure blood pressure
- **TENS/EMS devices** (EM series): Pain therapy devices that use electrical stimulation
- **Infrared lamps** (IL series): Heat therapy devices

### What are we building?
A **Social Listening system** that:
1. Crawls German health forums and Q&A platforms using multiple tools
2. Extracts real user questions and problems
3. Stores data in Supabase with vector embeddings for semantic search (RAG)
4. Runs on automated schedules via Supabase Cron Jobs
5. Feeds data into our Content Engine and weekly reports

### Why does this matter?
Beurer wants to create content that answers REAL user questions. We need to find out:
- What questions do people ask about blood pressure measurement?
- What problems do TENS device users have?
- What do Amazon reviewers complain about?

### Target Audience
- **Age:** 50+ years (elderly, not tech-savvy)
- **Language:** German only
- **Topics:** Blood pressure, chronic pain, menstrual pain

---

## 🏗️ SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SUPABASE CRON JOBS (Scheduler)                  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
        ┌──────────┬───────────────┼───────────────┬──────────┐
        ▼          ▼               ▼               ▼          ▼
   ┌─────────┐ ┌─────────┐ ┌────────────┐ ┌─────────┐ ┌────────────┐
   │  Apify  │ │Firecrawl│ │  Gemini    │ │ Serper  │ │ BrowserUse │
   │ Actors  │ │   API   │ │ Grounding  │ │ Search  │ │            │
   └────┬────┘ └────┬────┘ └─────┬──────┘ └────┬────┘ └─────┬──────┘
        │          │             │             │            │
        └──────────┴─────────────┴─────────────┴────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │   Supabase Edge Function │
                    │   (ETL + Embedding)      │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
     ┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐
     │   PostgreSQL    │ │  pgvector   │ │ Supabase Storage │
     │   (Raw Data)    │ │ (Embeddings)│ │   (Raw HTML)     │
     └────────┬────────┘ └──────┬──────┘ └──────────────────┘
              │                 │
              └────────┬────────┘
                       ▼
         ┌─────────────────────────────┐
         │         RAG API             │
         │   (Semantic Retrieval)      │
         └──────────────┬──────────────┘
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
   ┌───────────────┐      ┌──────────────────┐
   │Content Engine │      │  Weekly Reports  │
   │(Article Gen)  │      │  (PDF for Beurer)│
   └───────────────┘      └──────────────────┘
```

---

## 🔧 CRAWLER TOOL SELECTION

| Platform | Tool | Why | Schedule |
|----------|------|-----|----------|
| **gutefrage.net** | Firecrawl | Simple HTML, good markdown extraction | Daily 02:00 |
| **Amazon Reviews** | Apify (`epctex/amazon-reviews-scraper`) | Complex anti-bot protection | Daily 04:00 |
| **Reddit** | Apify (`trudax/reddit-scraper-lite`) | API limits, Actor handles pagination | Every 6h |
| **Health Forums** | Firecrawl | Static HTML pages | Weekly Sun 03:00 |
| **YouTube Comments** | Apify (`streamers/youtube-comment-scraper`) | Handles YouTube auth | Weekly |
| **TikTok** | Apify (`clockworks/tiktok-scraper`) | Complex JS rendering | Weekly (low prio) |
| **Instagram** | Apify (`apify/instagram-scraper`) | Login walls | Weekly (low prio) |
| **New Source Discovery** | Serper + Gemini Grounding | Find forums we don't know about | Daily |
| **Interactive Sites** | BrowserUse | Sites requiring clicks/auth | As needed |

**Note:** TikTok/Instagram are lower priority - target audience is 50+, likely less active there.

---

## 📅 MILESTONES & DEADLINES

| Milestone | Deadline | Deliverable | Status |
|-----------|----------|-------------|--------|
| **M1: Infrastructure** | Mon Feb 3 | Supabase + pgvector + first crawler | 🔲 |
| **M2: Multi-Crawler Pipeline** | Wed Feb 5 | 500+ rows in database, RAG working | 🔲 |
| **M3: Client Report Ready** | Thu Feb 6 | Weekly report PDF for client meeting | 🔲 |
| **M4: Full Automation** | Mon Feb 10 | All cron jobs running, semantic search API | 🔲 |

---

## 🗄️ SUPABASE DATABASE SCHEMA

### Setup Instructions

1. Create a new Supabase project at https://supabase.com
2. Enable the pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Run the migration below

### Database Tables

```sql
-- Enable pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Main social listening data
CREATE TABLE social_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,           -- 'gutefrage', 'amazon', 'reddit', etc.
    source_url TEXT UNIQUE NOT NULL,
    source_id TEXT,                 -- Platform-specific ID
    title TEXT,
    content TEXT NOT NULL,
    content_hash TEXT,              -- MD5 for deduplication
    author TEXT,
    posted_at TIMESTAMPTZ,
    crawled_at TIMESTAMPTZ DEFAULT NOW(),
    crawler_tool TEXT,              -- 'firecrawl', 'apify', 'browseruse', etc.
    raw_data JSONB,
    
    -- Classification (filled by Gemini/Claude)
    category TEXT,                  -- 'blood_pressure', 'pain_tens', 'menstrual', 'other'
    product_mentions TEXT[],        -- ['BM 27', 'EM 59']
    sentiment TEXT,                 -- 'positive', 'neutral', 'negative'
    relevance_score FLOAT,          -- 0.0 to 1.0
    keywords TEXT[],
    
    -- Vector embedding for RAG (1536 = OpenAI text-embedding-3-small)
    embedding vector(1536)
);

-- Indexes
CREATE INDEX idx_social_items_source ON social_items(source);
CREATE INDEX idx_social_items_category ON social_items(category);
CREATE INDEX idx_social_items_posted ON social_items(posted_at DESC);
CREATE INDEX idx_social_items_hash ON social_items(content_hash);

-- Vector similarity search (IVFFlat for speed)
CREATE INDEX idx_social_items_embedding ON social_items 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Crawler run logs
CREATE TABLE crawler_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crawler_name TEXT NOT NULL,
    tool TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',  -- 'running', 'success', 'failed'
    items_crawled INT DEFAULT 0,
    items_new INT DEFAULT 0,
    error_message TEXT,
    config JSONB
);

-- Weekly report cache
CREATE TABLE weekly_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    report_data JSONB,
    pdf_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Semantic Search Function

```sql
-- Function to search by semantic similarity
CREATE OR REPLACE FUNCTION search_social_items(
    query_embedding vector(1536),
    match_count INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    source TEXT,
    title TEXT,
    content TEXT,
    category TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id,
        s.source,
        s.title,
        s.content,
        s.category,
        1 - (s.embedding <=> query_embedding) AS similarity
    FROM social_items s
    WHERE 
        s.embedding IS NOT NULL
        AND (filter_category IS NULL OR s.category = filter_category)
    ORDER BY s.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

---

## ✅ ACCEPTANCE TESTS (Definition of Done)

### Quick Test - Verify Each Tool Works

```python
# test_tools.py - Run this to verify all crawler tools are accessible

import os

def test_firecrawl():
    """Test Firecrawl API"""
    import requests
    response = requests.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {os.environ['FIRECRAWL_API_KEY']}"},
        json={"url": "https://www.gutefrage.net/tag/blutdruck/1", "formats": ["markdown"]}
    )
    assert response.json().get("success"), "Firecrawl failed"
    print("✅ Firecrawl works")

def test_apify():
    """Test Apify API"""
    from apify_client import ApifyClient
    client = ApifyClient(os.environ['APIFY_API_TOKEN'])
    # Just verify connection
    user = client.user().get()
    assert user, "Apify connection failed"
    print("✅ Apify works")

def test_supabase():
    """Test Supabase connection"""
    from supabase import create_client
    client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])
    result = client.table('social_items').select('id').limit(1).execute()
    print("✅ Supabase works")

def test_serper():
    """Test Serper API"""
    import requests
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": os.environ['SERPER_API_KEY']},
        json={"q": "Blutdruck messen site:gutefrage.net", "gl": "de", "hl": "de"}
    )
    assert response.status_code == 200, "Serper failed"
    print("✅ Serper works")

if __name__ == "__main__":
    test_firecrawl()
    test_apify()
    test_supabase()
    test_serper()
    print("\n🎉 All tools working!")
```

### Expected Test Results

| Test | Expected Result | Pass Criteria |
|------|-----------------|---------------|
| Firecrawl - gutefrage.net | ✅ Success | Returns markdown content |
| Apify - Connection | ✅ Success | API token valid |
| Supabase - Connection | ✅ Success | Can query table |
| Serper - Search | ✅ Success | Returns search results |

---

## 🔧 EXACT URLs TO CRAWL

### Priority 1A: gutefrage.net (Q&A Platform)

**What is gutefrage.net?** Germany's largest Q&A platform (like Yahoo Answers but German). Users ask health questions and get community answers.

**EXACT URLs - Copy/paste these:**

```
# BLOOD PRESSURE (Blutdruck)
https://www.gutefrage.net/tag/blutdruck/1
https://www.gutefrage.net/tag/blutdruck/2
https://www.gutefrage.net/tag/blutdruck/3
https://www.gutefrage.net/tag/blutdruck/4
https://www.gutefrage.net/tag/blutdruck/5

https://www.gutefrage.net/tag/blutdruckmessgeraet/1
https://www.gutefrage.net/tag/blutdruckmessgeraet/2

https://www.gutefrage.net/tag/bluthochdruck/1
https://www.gutefrage.net/tag/bluthochdruck/2
https://www.gutefrage.net/tag/bluthochdruck/3

# PAIN THERAPY (TENS devices)
https://www.gutefrage.net/tag/tens/1
https://www.gutefrage.net/tag/tens/2

https://www.gutefrage.net/tag/ems/1

# MENSTRUAL PAIN (for EM 59 device)
https://www.gutefrage.net/tag/regelschmerzen/1
https://www.gutefrage.net/tag/regelschmerzen/2
https://www.gutefrage.net/tag/regelschmerzen/3

https://www.gutefrage.net/tag/periodenschmerzen/1
https://www.gutefrage.net/tag/periodenschmerzen/2

https://www.gutefrage.net/tag/menstruationsschmerzen/1

# BACK/NECK PAIN (for EM 89 device)
https://www.gutefrage.net/tag/rueckenschmerzen/1
https://www.gutefrage.net/tag/rueckenschmerzen/2
https://www.gutefrage.net/tag/rueckenschmerzen/3

https://www.gutefrage.net/tag/nackenschmerzen/1
https://www.gutefrage.net/tag/nackenschmerzen/2

# CHRONIC PAIN
https://www.gutefrage.net/tag/chronische-schmerzen/1
```

**Total: ~30 URLs to crawl**

### Priority 1B: Amazon.de Reviews

**EXACT ASINs - These are real Beurer products:**

```
# Beurer Blood Pressure Monitors
B01LXBGPRI - Beurer BM 27 (bestseller, ~5000 reviews)
B07WZJFZ5X - Beurer BM 54
B07X3JTQSH - Beurer BM 58

# Beurer TENS/EMS Devices
B01M0QXWVP - Beurer EM 59 (menstrual pain, ~1000 reviews)
B07WKCWJ8P - Beurer EM 49

# Competitor (for comparison)
B07N1BWLHB - Omron M500

# URL Pattern:
https://www.amazon.de/product-reviews/{ASIN}?pageNumber=1
https://www.amazon.de/product-reviews/{ASIN}?pageNumber=2
... continue until no more reviews
```

**Example URLs:**
```
https://www.amazon.de/product-reviews/B01LXBGPRI?pageNumber=1
https://www.amazon.de/product-reviews/B01LXBGPRI?pageNumber=2
https://www.amazon.de/product-reviews/B01LXBGPRI?pageNumber=3
```

### Priority 2: Health Forums

```
# Diabetes Forum - blood pressure overlap
https://www.diabetes-forum.de/

# Endometriose (menstrual pain community) - EM 59 target
https://www.endometriose-vereinigung.de/

# Rheuma Liga (chronic pain) - TENS target
https://www.rheuma-liga.de/

# Onmeda (general health Q&A)
https://www.onmeda.de/
https://www.onmeda.de/forum/
```

---

## 📊 REQUIRED OUTPUT FORMAT (CSV)

### Milestone 2 Deliverable: social_listening_export.csv

**EXACT COLUMNS REQUIRED:**

```csv
id,source,url,title,content,date,category,product_relevance,keywords
```

**Column Definitions:**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| id | int | Unique row ID | 1, 2, 3... |
| source | string | Platform name | "gutefrage.net", "amazon.de" |
| url | string | Original URL | "https://www.gutefrage.net/frage/..." |
| title | string | Question title or review headline | "Blutdruck schwankt stark - normal?" |
| content | string | Full text (truncate to 2000 chars) | "Ich habe seit Wochen..." |
| date | string | Date in YYYY-MM-DD format | "2024-01-15" |
| category | string | One of: blood_pressure, pain_tens, menstrual, other | "blood_pressure" |
| product_relevance | string | Mentioned products or "none" | "BM 27", "EM 59", "none" |
| keywords | string | Comma-separated extracted keywords | "blutdruck,messung,schwankt" |

**Example Rows:**

```csv
id,source,url,title,content,date,category,product_relevance,keywords
1,gutefrage.net,https://www.gutefrage.net/frage/blutdruck-messen-morgens,"Blutdruck morgens immer hoch?","Hallo, ich messe jeden Morgen meinen Blutdruck und er ist immer über 140. Ist das normal? Ich nehme schon Tabletten...",2024-01-20,blood_pressure,none,"blutdruck,morgens,hoch,tabletten"
2,amazon.de,https://www.amazon.de/review/R3ABC123,"Gutes Gerät aber Manschette zu klein","Nach 2 Wochen Nutzung: Das Beurer BM 27 misst genau, aber die mitgelieferte Manschette ist für meinen Oberarm zu klein...",2024-01-18,blood_pressure,BM 27,"manschette,klein,genau,beurer"
3,gutefrage.net,https://www.gutefrage.net/frage/tens-geraet-gegen-regelschmerzen,"TENS gegen Regelschmerzen - Erfahrungen?","Hat jemand Erfahrung mit TENS-Geräten gegen Regelschmerzen? Lohnt sich die Anschaffung?",2024-01-15,menstrual,none,"tens,regelschmerzen,erfahrung"
```

**MINIMUM REQUIREMENTS FOR M2:**
- At least 500 rows
- At least 300 from gutefrage.net
- At least 100 from Amazon
- At least 50 from other sources
- No duplicate URLs

---

## 🔑 API CREDENTIALS & ENVIRONMENT VARIABLES

```bash
# .env file - ALL REQUIRED

# Firecrawl - Web Scraping (gutefrage, forums)
FIRECRAWL_API_KEY=your-firecrawl-api-key  # Get from https://firecrawl.dev

# Apify - Complex scrapers (Amazon, Reddit, TikTok)
APIFY_API_TOKEN=your-apify-api-token  # Get from https://console.apify.com/account/integrations

# Supabase - Database + Auth
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-supabase-service-key  # Service role key for backend

# Serper - Google Search API
SERPER_API_KEY=your-serper-api-key  # Get from https://serper.dev

# Gemini - Classification + Grounding
GEMINI_API_KEY=your-gemini-api-key  # Get from https://aistudio.google.com

# OpenAI - Embeddings (text-embedding-3-small)
OPENAI_API_KEY=your-openai-api-key  # For vector embeddings

# Optional: BrowserUse (for interactive sites)
BROWSERUSE_API_KEY=your-browseruse-key  # Only if needed
```

---

## 🔍 RAG API - SEMANTIC RETRIEVAL

### Purpose
The RAG (Retrieval-Augmented Generation) system allows:
1. **Content Engine**: Find relevant user questions when writing articles
2. **Weekly Reports**: Surface trending topics and pain points
3. **Future**: Answer "What do users say about X?" queries

### Usage Examples

```python
from supabase import create_client
import openai

# Initialize
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = openai.OpenAI()

def semantic_search(query: str, category: str = None, limit: int = 10):
    """
    Search social listening data by meaning, not keywords.
    
    Examples:
        semantic_search("Probleme beim Blutdruck messen morgens")
        semantic_search("TENS Gerät hilft nicht", category="pain_tens")
    """
    # 1. Generate embedding for query
    embedding = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding
    
    # 2. Search by vector similarity
    result = supabase.rpc(
        'search_social_items',
        {
            'query_embedding': embedding,
            'match_count': limit,
            'filter_category': category
        }
    ).execute()
    
    return result.data

# Example: Find what users say about blood pressure fluctuation
results = semantic_search("Warum schwankt mein Blutdruck so stark?")
for r in results:
    print(f"[{r['source']}] {r['title']}")
    print(f"  Similarity: {r['similarity']:.2f}")
```

### API Endpoint (Supabase Edge Function)

```typescript
// supabase/functions/semantic-search/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  const { query, category, limit = 10 } = await req.json()
  
  // Get embedding from OpenAI
  const embeddingResponse = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'text-embedding-3-small',
      input: query
    })
  })
  const { data } = await embeddingResponse.json()
  
  // Search Supabase
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_KEY')!
  )
  
  const { data: results } = await supabase.rpc('search_social_items', {
    query_embedding: data[0].embedding,
    match_count: limit,
    filter_category: category
  })
  
  return new Response(JSON.stringify(results), {
    headers: { 'Content-Type': 'application/json' }
  })
})
```

---

## ⏰ SUPABASE CRON JOBS - SCHEDULING

### Setup pg_cron Extension

```sql
-- Enable pg_cron (run in Supabase SQL Editor)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Grant usage
GRANT USAGE ON SCHEMA cron TO postgres;
```

### Cron Job Schedules

| Crawler | Cron Expression | Schedule | Edge Function |
|---------|-----------------|----------|---------------|
| gutefrage.net | `0 2 * * *` | Daily 02:00 UTC | `run-firecrawl` |
| Amazon Reviews | `0 4 * * *` | Daily 04:00 UTC | `run-apify-amazon` |
| Reddit | `0 */6 * * *` | Every 6 hours | `run-apify-reddit` |
| Health Forums | `0 3 * * 0` | Sunday 03:00 UTC | `run-firecrawl` |
| Source Discovery | `0 6 * * *` | Daily 06:00 UTC | `run-serper-discovery` |
| Weekly Report | `0 8 * * 1` | Monday 08:00 UTC | `generate-weekly-report` |

### Register Cron Jobs

```sql
-- Daily: gutefrage.net via Firecrawl
SELECT cron.schedule(
    'crawl-gutefrage',
    '0 2 * * *',
    $$SELECT net.http_post(
        url := 'https://YOUR_PROJECT.supabase.co/functions/v1/run-crawler',
        headers := '{"Authorization": "Bearer YOUR_SERVICE_KEY"}'::jsonb,
        body := '{"crawler": "gutefrage", "tool": "firecrawl"}'::jsonb
    )$$
);

-- Daily: Amazon via Apify
SELECT cron.schedule(
    'crawl-amazon',
    '0 4 * * *',
    $$SELECT net.http_post(
        url := 'https://YOUR_PROJECT.supabase.co/functions/v1/run-crawler',
        headers := '{"Authorization": "Bearer YOUR_SERVICE_KEY"}'::jsonb,
        body := '{"crawler": "amazon", "tool": "apify"}'::jsonb
    )$$
);

-- Every 6 hours: Reddit via Apify
SELECT cron.schedule(
    'crawl-reddit',
    '0 */6 * * *',
    $$SELECT net.http_post(
        url := 'https://YOUR_PROJECT.supabase.co/functions/v1/run-crawler',
        headers := '{"Authorization": "Bearer YOUR_SERVICE_KEY"}'::jsonb,
        body := '{"crawler": "reddit", "tool": "apify"}'::jsonb
    )$$
);

-- Monday: Weekly Report
SELECT cron.schedule(
    'weekly-report',
    '0 8 * * 1',
    $$SELECT net.http_post(
        url := 'https://YOUR_PROJECT.supabase.co/functions/v1/generate-weekly-report',
        headers := '{"Authorization": "Bearer YOUR_SERVICE_KEY"}'::jsonb,
        body := '{}'::jsonb
    )$$
);
```

### Monitor Cron Jobs

```sql
-- View scheduled jobs
SELECT * FROM cron.job;

-- View recent job runs
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;
```

---

## 🏗️ IMPLEMENTATION STEPS

### Phase 1: Infrastructure (Day 1-2)

1. **Create Supabase Project**
   - Enable pgvector extension
   - Run database migration (schema above)
   - Get API keys

2. **Set Up Environment**
```bash
mkdir beurer-social-listening
cd beurer-social-listening
python -m venv venv
   source venv/bin/activate
   pip install requests pandas supabase openai apify-client
   ```

3. **Test All Connections**
   - Run `test_tools.py` from acceptance tests

### Phase 2: Crawlers (Day 2-4)

Create modular crawler files:

```
scripts/crawlers/
├── base_crawler.py      # Shared logic (save to Supabase, dedup)
├── firecrawl_runner.py  # gutefrage, forums
├── apify_runner.py      # Amazon, Reddit, TikTok
├── serper_discovery.py  # Find new sources
└── orchestrator.py      # Called by cron, routes to correct crawler
```

### Phase 3: ETL Pipeline (Day 4-5)

Each crawler run should:
1. Fetch raw data
2. Deduplicate (check `content_hash`)
3. Classify with Gemini (category, sentiment)
4. Generate embedding (OpenAI)
5. Save to Supabase

### Phase 4: RAG + Reports (Day 5-6)

1. Deploy Supabase Edge Functions
2. Test semantic search
3. Build weekly report generator

---

## ⚠️ KNOWN ISSUES & SOLUTIONS

### Issue 1: Rate Limiting
**Problem:** Firecrawl has rate limits (check your plan)
**Solution:** Add 2-3 second delay between requests

```python
import time

for url in urls:
    result = scrape_url(url)
    time.sleep(2)  # Wait 2 seconds
```

### Issue 2: German Date Parsing
**Problem:** Dates are in German format ("vor 2 Tagen", "01.01.2024")
**Solution:** Convert to YYYY-MM-DD format

```python
from datetime import datetime, timedelta
import re

def parse_german_date(text):
    # "vor 2 Tagen" -> calculate date
    match = re.search(r'vor (\d+) (Tagen?|Stunden?|Minuten?)', text)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if 'Tag' in unit:
            return (datetime.now() - timedelta(days=num)).strftime('%Y-%m-%d')
        # ... handle other units
    
    # "01.01.2024" -> parse directly
    match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    
    return datetime.now().strftime('%Y-%m-%d')  # fallback
```

### Issue 3: Content Too Long
**Problem:** Some content is very long
**Solution:** Truncate to 2000 characters

```python
content = content[:2000] if len(content) > 2000 else content
```

---

## 📊 WEEKLY REPORT AUTOMATION

### Report Structure

Weekly reports are generated automatically every Monday and include:

1. **Summary Stats**
   - Total new items this week
   - Items by source/category
   - Sentiment breakdown

2. **Trending Topics**
   - Top 10 most discussed themes
   - Emerging questions

3. **Product Mentions**
   - Beurer product mentions
   - Competitor mentions (Omron, Withings)

4. **Content Opportunities**
   - Unanswered questions (high relevance, no good answers)
   - Pain points / complaints

5. **Top 20 Most Relevant Posts**
   - Full content with source links

### Report Generator (Edge Function)

```typescript
// supabase/functions/generate-weekly-report/index.ts
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_KEY')!
  )
  
  // Get last week's data
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
  
  const { data: items } = await supabase
    .from('social_items')
    .select('*')
    .gte('crawled_at', weekAgo)
    .order('relevance_score', { ascending: false })
  
  // Generate stats
  const report = {
    period: { start: weekAgo, end: new Date().toISOString() },
    total_items: items.length,
    by_source: groupBy(items, 'source'),
    by_category: groupBy(items, 'category'),
    by_sentiment: groupBy(items, 'sentiment'),
    top_items: items.slice(0, 20),
    product_mentions: extractProductMentions(items),
  }
  
  // Save report
  await supabase.from('weekly_reports').insert({
    week_start: weekAgo,
    week_end: new Date().toISOString(),
    report_data: report
  })
  
  return new Response(JSON.stringify(report))
})
```

### Output Format

Reports are delivered as:
- **Excel (.xlsx)** for data analysis
- **PDF** in Beurer Corporate Design (Magenta #C60050) for presentations

---

## 📝 REPORTING PROGRESS

### Daily Standup Format (Slack/Email)

```
Date: [YYYY-MM-DD]

DONE:
- [List what you completed]

BLOCKERS:
- [Any issues preventing progress]

NEXT:
- [What you'll work on next]

METRICS:
- Items in database: X
- New items today: X
- RAG queries tested: X
```

### Example:

```
Date: 2026-02-03

DONE:
- Firecrawl crawler deployed (gutefrage, forums)
- Apify Amazon actor configured
- 450 items in Supabase with embeddings

BLOCKERS:
- None

NEXT:
- Set up cron jobs
- Test semantic search

METRICS:
- Items in database: 450
- New items today: 450
- Crawlers working: 2/4
```

---

## 📞 CONTACTS

**Project Lead:** Simon Leander Wilhelm (simon@scaile.io)

**Questions?**
- Technical issues: Create GitHub issue or message Simon
- Deadline concerns: Message immediately, don't wait

---

## 🔗 RESOURCES

- **Firecrawl Docs:** https://docs.firecrawl.dev/
- **HyperNiche Repo:** https://github.com/clients-scaile/hyperniche
- **Client Data:** See `02_CLIENT_INPUT/` folder in this repo

---

## CHECKLIST BEFORE MARKING MILESTONE COMPLETE

### M1: Infrastructure ✓
- [ ] Supabase project created
- [ ] pgvector extension enabled
- [ ] Database schema deployed
- [ ] All API keys in .env and tested
- [ ] First Firecrawl test successful

### M2: Multi-Crawler Pipeline ✓
- [ ] Firecrawl crawler working (gutefrage, forums)
- [ ] Apify crawler working (Amazon, Reddit)
- [ ] At least 500 items in `social_items` table
- [ ] Embeddings generated for all items
- [ ] Semantic search tested and working

### M3: Client Report Ready ✓
- [ ] Weekly report generator deployed
- [ ] First report generated with real data
- [ ] PDF in Beurer Corporate Design
- [ ] Ready for Thursday Feb 6 meeting

### M4: Full Automation ✓
- [ ] All cron jobs registered and running
- [ ] Semantic search Edge Function deployed
- [ ] No manual intervention needed for daily crawls
- [ ] Monitoring/alerting set up

---

**START HERE:** 
1. Create Supabase project and run the database migration
2. Set up all API keys in `.env`
3. Run `test_tools.py` to verify connections
4. Build Firecrawl crawler first (simplest)
5. Add Apify crawlers
6. Deploy Edge Functions and cron jobs

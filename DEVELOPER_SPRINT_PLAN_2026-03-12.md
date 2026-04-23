# Developer Sprint Plan: News Feed, Peec AI Integration, Analytics & Author Profiles

**For:** Dharmay (Developer), Chandine (Product)
**CC:** Yousif (Developer — Social Listening Service)
**From:** Simon (SCAILE)
**Date:** March 12, 2026
**Supersedes:** Sprint Plan March 10 (which superseded Sprint Plan March 5)
**Context:** Two meetings with Beurer on March 10. Key changes: (1) News feed deadline moved up — Simon promised it by Monday March 16, (2) Peec AI API integration for media visibility tab, (3) two doctors confirmed as article authors — author profile display needed, (4) Dilyana (not Diana) is the Sistrix/GA contact — only available after SMX trade show, (5) magazine goes live early April — we need publishing workflow ready.

---

## EXECUTIVE SUMMARY: WHAT CHANGED SINCE LAST SPRINT

Content delivery is DONE (15 articles live). Comment author attribution and publish status are the same as last sprint (P1/P2). **What's new:**

- **News Feed is URGENT** — Simon promised Beurer it would be ready by Monday March 16
- **Peec AI API** should be integrated for the media visibility tab (replaces manual CSV import)
- **Author profiles** needed — two Beurer doctors will be displayed as article authors
- **Analytics (GSC/GA/Sistrix/Salesforce)** — NEW: research each API and write a requirements document for Beurer. They need a clear checklist of what to set up. Then build UI shell with mock data.

```
P1: Comment system — author attribution (dropdown)              -> by Mar 14  [SAME]
P2: Publish status field + tracking                             -> by Mar 14  [SAME]
P3: AI Commerce News Feed (URGENT — deadline moved up!)         -> by Mar 16  [MOVED UP]
P4: Peec AI API integration — Media Visibility tab              -> by Mar 19  [NEW]
P5: Author profiles display on articles                         -> by Mar 19  [NEW]
P6: Analytics research — write requirements doc for Beurer team  -> by Mar 19  [NEW]
P7: Performance tab — UI shell with mock data (GSC+GA4+Sistrix) -> by Mar 21  [ADJUSTED]
P8: Email notifications on feedback updates                     -> by Mar 21  [SAME]
P9: Image/infographic prototypes                                -> by Mar 21  [SAME]
P10: Source link validation                                     -> ongoing    [SAME]
```

### What's Working Well (keep as-is)
- Article display in dashboard ✅
- Feedback/comment functionality ✅
- HTML export for CMS upload ✅
- Article generation via admin page ✅
- Review status workflow (draft → approved) ✅

---

## P1: COMMENT SYSTEM — AUTHOR ATTRIBUTION (HIGH PRIORITY)

*No changes from last sprint — see Sprint Plan March 10 for full spec.*

### Quick Summary
- Add name dropdown before comment field: `Anika Honold`, `Kerstin Glanzer`, `Kevin Schlotz`, `Simon Schwörer`, `Simon Wilhelm (SCAILE)`
- New DB column: `commenter_name` on comments table
- Display: `"Anika Honold: This section needs revision" — 2 hours ago`
- Existing comments: show without author (don't break)

### Acceptance Criteria
- [ ] Dropdown with reviewer names visible before comment submission
- [ ] Comment displays author name + timestamp
- [ ] Existing comments not broken (show without author)
- [ ] Each article shows which reviewers have commented (summary badge)

---

## P2: PUBLISH STATUS FIELD (HIGH PRIORITY)

*No changes from last sprint — see Sprint Plan March 10 for full spec.*

### Quick Summary
- New field: `publish_status` → `unpublished` | `scheduled` | `published`
- Additional fields: `publish_date` (datetime), `publish_url` (text)
- Color-coded badges on article cards
- Kevin/admin can update via dropdown

### Acceptance Criteria
- [ ] Publish status dropdown on article detail/modal
- [ ] Visual badge on article list (unpublished/scheduled/published)
- [ ] Date picker for publish date
- [ ] URL field for live article link

---

## P3: AI COMMERCE NEWS FEED (🔴 URGENT — DEADLINE MARCH 16)

### Workflow
1. **Chandine (Product)** reviews this spec first — decides how information should be best aggregated, evaluated, and presented with Beurer relevance. Briefs Dharmay on the implementation approach.
2. **Dharmay (Developer)** builds it based on Chandine's direction.
3. Goal: Information must be **daily-current**, with Beurer context, and actionable for the client.

### Context
Simon promised Beurer this would be ready by end of this week / Monday March 16. This was discussed in two separate meetings and is a key deliverable for the KW 12 meeting. The client wants to see curated, relevant AI commerce news directly in the dashboard.

### Why It Matters
Beurer is evaluating ChatGPT Ads (Target + OpenAI partnership, US-only for now), UGC/avatar strategies (BMW "Lily" as benchmark), and AI-driven e-commerce trends. They want a central place to stay on top of these fast-moving developments. This news feed should make Beurer the best-informed MedTech company on AI commerce trends.

### Requirements

**New Dashboard Tab: "AI Commerce News" or "News"**

**Data Sources — ALL MUST BE CRAWLED DAILY:**

**🔴 Tier 1: Must-have sources (crawl every 6 hours)**

| Source | Type | Why Critical | What to Crawl |
|--------|------|-------------|---------------|
| **X / Twitter** | Social | **Strongest source for breaking AI commerce news.** Real-time updates from key people. | Accounts + hashtags below |
| **Google News** | Aggregator | Catches news from all publishers | AI commerce + health tech keywords |
| **Peec AI Blog** | Industry | Our own AI visibility tool — their blog covers exactly our space | https://peec.ai/blog — full RSS/crawl |
| **Graphite "Five Percent"** | Newsletter | High-signal AI SEO newsletter by a top player | https://graphite.io/five-percent — new posts |
| **SEO Südwest** | German SEO | #1 German SEO news source, covers AI Overviews, Google updates | https://www.seo-suedwest.de/ — daily articles |

**🟡 Tier 2: Important sources (crawl daily)**

| Source | Type | Why Important | What to Crawl |
|--------|------|--------------|---------------|
| **YouTube** | Video | Long-form analysis, tutorials, product reviews | Channels + keyword searches |
| **Search Engine Land** | Industry | AI search advertising, Google AI updates | RSS feed |
| **TechCrunch** | Tech news | AI commerce partnerships, startup funding | RSS feed, AI commerce section |
| **The Verge** | Tech news | Consumer AI product launches | RSS feed |

**🟢 Tier 3: Nice-to-have (crawl daily if capacity allows)**

| Source | Type | What to Crawl |
|--------|------|---------------|
| LinkedIn posts | Professional | Key thought leaders (see below) |
| Reddit | Community | r/SEO, r/artificial, r/ecommerce |
| Industry blogs | Various | Ahrefs blog, Moz blog, HubSpot AI |

### X / Twitter — KEY ACCOUNTS TO TRACK

**X is the most important source for this feed.** Breaking news, hot takes, and industry signals appear here first. Daily crawling is essential.

**Must-follow accounts:**
```
AI Commerce / Search:
- @OpenAI — product launches, API updates, shopping features
- @Google — AI Overviews, shopping ads, search updates
- @searchliaison — Google Search official communications
- @peraborgen — AI commerce / commerce protocol expert
- @GaryIllyes — Google Search Relations (technical updates)

AI SEO / Visibility:
- @liloray (Lily Ray) — AI SEO expert, E-E-A-T specialist, health content authority
  LinkedIn: https://www.linkedin.com/in/lily-ray-44755615/
  → One of THE most important voices for AI visibility in health/medical content
- @aaborrell — AI search expert
- @rustybrick — Barry Schwartz, Search Engine Roundtable
- @JohnMu — John Mueller, Google Search

AI Health Tech:
- @peabordy — health tech AI
- Relevant health tech startup accounts (identify dynamically)

Hashtags to monitor:
#AIcommerce #AIshopping #ChatGPTads #AIOverviews #SGE #AIvisibility
#KIcommerce #AIhealth #commerceprotocol #AISearch #LLMOptimization
```

### LinkedIn — KEY THOUGHT LEADERS

**Lily Ray** is particularly important — she is one of the most-cited experts on E-E-A-T, AI visibility, and health content quality:
- LinkedIn: https://www.linkedin.com/in/lily-ray-44755615/
- Her posts about health content, AI search quality, and E-E-A-T are directly relevant to Beurer's strategy
- Track her posts for insights on how health brands should approach AI visibility

### Keywords to monitor (across all sources):
```
English:
- "AI commerce", "AI shopping", "ChatGPT ads", "commerce protocol"
- "AI health tech", "AI medical devices", "OpenAI shopping"
- "AI product recommendations", "AI search ads"
- "Perplexity shopping", "Google AI shopping"
- "AI Overviews", "SGE", "AI visibility", "LLM optimization"
- "E-E-A-T", "AI citations", "AI brand visibility"
- "AI health content", "medical AI search"

German:
- "KI E-Commerce", "KI Gesundheit", "ChatGPT Werbung"
- "KI Sichtbarkeit", "AI Visibility", "KI Produktempfehlung"
- "Google AI Übersichten", "KI Suche", "SEO KI"
```

### Data Model

**Each news item:**
```json
{
  "id": "uuid",
  "title": "OpenAI launches shopping ads in partnership with Target",
  "source": "TechCrunch",
  "source_type": "news",        // news | youtube | twitter | blog | linkedin
  "source_url": "https://peec.ai/blog/...",
  "author": "Lily Ray",         // if identifiable
  "published_at": "2026-03-10T14:00:00Z",
  "summary": "2-3 sentence summary — auto-generated or extracted",
  "beurer_context": "Relevant because: AI shopping ads could affect how Beurer products appear in ChatGPT responses. Currently US-only, EU expected in 3-6 months.",
  "relevance_tags": ["chatgpt-ads", "retail", "us-market"],
  "beurer_relevance": "high",   // high | medium | low
  "fetched_at": "2026-03-10T16:00:00Z"
}
```

**Key field: `beurer_context`** — This is what makes our feed valuable. Every item should have a 1-2 sentence explanation of WHY this matters for Beurer specifically. This is what Chandine should help define: How do we automatically or semi-automatically generate this Beurer-specific context?

Options:
1. **AI-generated:** Use an LLM to generate the `beurer_context` based on the article content + Beurer's profile (health devices, AI visibility, E-E-A-T)
2. **Rule-based:** Keyword matching with predefined context templates
3. **Manual:** Simon/SCAILE team adds context for high-relevance items

### Display

```
AI COMMERCE & VISIBILITY NEWS
===============================

📅 Today (March 12, 2026) — 4 new items

🔴 HIGH RELEVANCE
[2h ago] X/@liloray — "Google just confirmed: health content without clear author
credentials will be demoted in AI Overviews. E-E-A-T is not optional."
⟶ Beurer context: Directly validates our author profile strategy. Having two
doctors as named authors with LinkedIn profiles = competitive advantage.
Tags: #E-E-A-T #health-content #AI-Overviews
→ View on X

🔴 HIGH RELEVANCE
[6h ago] Peec AI Blog — "How AI Citations Changed in Q1 2026"
⟶ Beurer context: May contain updated citation data for health devices sector.
Check if Beurer/Omron visibility share has shifted.
Tags: #ai-citations #visibility #tracking
→ Read on peec.ai

🟡 MEDIUM RELEVANCE
[Yesterday] Graphite — "The Five Percent: AI Shopping Ads Are Coming to Europe"
⟶ Beurer context: EU launch timeline for ChatGPT Ads. Beurer should prepare
product feed strategy now. Estimated EU availability: Q3-Q4 2026.
Tags: #chatgpt-ads #eu-market
→ Read on graphite.io

🟢 GENERAL
[Yesterday] SEO Südwest — "Google testet neue AI Overview Features in Deutschland"
⟶ Beurer context: German AI Overviews may show product carousels. Monitor if
Beurer devices appear.
Tags: #google #ai-overviews #germany
→ Read on seo-suedwest.de
```

### Filtering & Sorting
- Filter by: relevance (high/medium/low), source type (news/youtube/twitter/blog/linkedin), date range
- Default sort: newest first, with high-relevance items pinned at top
- Search within news items
- **Daily digest view:** Summary of today's most important items
- **Weekly rollup:** Top 5 items of the week with Beurer impact summary

### Relevance Classification
- **High:** Mentions health tech, medical devices, Beurer competitors, E-E-A-T health content, AI commerce policy changes, AI shopping features in EU
- **Medium:** General AI commerce trends, new platform features, SEO algorithm updates
- **Low:** Tangentially related (general AI news, tech industry, non-health verticals)
- Implementation: Keyword matching + source priority first (MVP), then AI classification

### Implementation Approach

**Chandine to review and brief Dharmay on:**
1. How should information be aggregated and presented for maximum Beurer relevance?
2. What's the best UX for a daily-current news feed? (chronological vs. relevance-sorted vs. daily digest?)
3. How do we generate the `beurer_context` field? (AI-generated, rule-based, or manual?)
4. Should there be a weekly summary/rollup feature?

**Dharmay to build:**
1. **Day 1 (Thu Mar 13):** Set up crawlers — X/Twitter API (highest priority!), Google News RSS, Peec AI blog RSS, Graphite RSS, SEO Südwest RSS. Create `news_items` DB table. Basic API endpoint. Set up daily cron job.
2. **Day 2 (Fri Mar 14):** Build the tab UI — list view with filters, relevance badges, Beurer context display. Auto-fetch on schedule.
3. **Day 3 (Mon Mar 16):** Polish — relevance tagging, pinned items, search, daily digest view. Deploy.

### Acceptance Criteria
- [ ] New "News" or "AI Commerce News" tab in dashboard navigation
- [ ] **All Tier 1 sources crawled daily** (X/Twitter, Google News, Peec AI Blog, Graphite, SEO Südwest)
- [ ] At least 3 data sources working at launch
- [ ] X/Twitter integration with key accounts tracked (see list above)
- [ ] Each item shows: title, source, date, summary, **Beurer context**, relevance tag, link
- [ ] Filter by relevance level (high/medium/low)
- [ ] Filter by source type (news/twitter/youtube/blog/linkedin)
- [ ] Auto-refresh on schedule (every 6 hours for Tier 1, daily for Tier 2)
- [ ] Search within news items
- [ ] Works with real data (not mock) by March 16
- [ ] Chandine has reviewed and approved the information architecture before launch

---

## P4: PEEC AI API INTEGRATION — MEDIA VISIBILITY TAB (NEW)

### Context
We've been manually exporting CSV files from Peec AI weekly. Peec AI now has an API (beta, Enterprise tier) that we should integrate directly into the dashboard. This replaces the manual CSV workflow and enables real-time media visibility tracking.

### API Documentation

**Base URL:** `https://api.peec.ai/` (refer to https://docs.peec.ai/api/introduction)
**Auth:** API key-based. Generate key at https://app.peec.ai/api-keys
**Format:** JSON responses

**Available Endpoints:**

| Endpoint | Purpose | What We Need It For |
|----------|---------|---------------------|
| `GET /projects` | List company projects | Get project ID for Beurer |
| `GET /projects/{id}/brands` | Get tracked brands | Beurer vs Omron brand data |
| `GET /projects/{id}/brands/report` | Brand performance report | **PRIMARY** — Visibility %, Position, Sentiment, Share of Voice |
| `GET /projects/{id}/domains/report` | Source domains report | **PRIMARY** — Which domains cite Beurer, citation counts, trends |
| `GET /projects/{id}/urls/report` | Source URLs report | Specific URLs citing Beurer products |
| `GET /projects/{id}/models` | AI models tracked | Which AI models (ChatGPT, Gemini, Perplexity, etc.) |
| `GET /projects/{id}/prompts` | Tracked prompts | 25 prompts we monitor |
| `GET /projects/{id}/chats` | Chat/response data | Individual AI responses with citations |
| `GET /projects/{id}/topics` | Topic groupings | Topic-level aggregation |

### Data We Currently Track (from manual CSV exports)

**Key Metrics:**
- **Visibility:** Beurer 45% vs Omron 55% (baseline from Feb 2026)
- **AI Position:** Ø #2.4 (goal: #1.8)
- **Total Citations:** 3,235 (across 7 AI models, 25 prompts, 7 days)
- **Top Sources:** nih.gov (57%), youtube.com (29%), saneostore.de (26%), chip.de (18%)

**Current CSV Structure (from `08_EXTERNAL_DATA/PEEC/`):**
```
Domain | Type | Used (%) | Avg. Citations
nih.gov | Reference | 57% | 1.8
youtube.com | UGC | 29% | 1.4
chip.de | Editorial | 18% | 2.4
beurer.com | Corporate | 8% | 2.0
```

### Dashboard Widget: "Mediensichtbarkeit" / "AI Visibility"

**New tab or section with three views:**

**View 1: Brand Overview**
```
AI VISIBILITY OVERVIEW
======================

Beurer vs Omron (KW 11/2026)
┌─────────────────────────────────┐
│  Beurer: 45%  ████████░░░░░░░  │
│  Omron:  55%  ██████████░░░░░  │
└─────────────────────────────────┘

Ø AI Position: #2.4 (target: #1.8)
Total Citations: 3,235
Sentiment: 72% positive

Trend: ↑ +2% vs last week
```

**View 2: Source Domain Table**
```
MEDIA SOURCES CITING BEURER (KW 11)
====================================

| Source          | Citations | Used % | Trend  | Tier   | Type      |
|-----------------|-----------|--------|--------|--------|-----------|
| nih.gov         | 1,843     | 57%    | → 0%   | —      | Reference |
| youtube.com     | 937       | 29%    | ↑ +3%  | —      | UGC       |
| saneostore.de   | 841       | 26%    | ↑ +1%  | —      | Competitor|
| chip.de         | 582       | 18%    | ↑ +2%  | Tier 1 | Editorial |
| axion.shop      | 517       | 16%    | → 0%   | —      | Competitor|
| orthomechanik.de| 453       | 14%    | ↓ -1%  | —      | Competitor|
| testsieger.de   | 291       | 9%     | ↑ +4%  | Tier 1 | Review    |
| beurer.com      | 259       | 8%     | ↑ +1%  | Own    | Corporate |
```

**View 3: Time-Series Chart**
```
CITATION TREND (12 weeks)
==========================

Citations
  ^
  |          ___
  |    ___--/   \___
  |___/              \___
  |                      \___
  +---+---+---+---+---+---+-->
  KW1 KW2 KW3 KW4 KW5 KW6    (Weeks)

Lines: beurer.com (pink), chip.de (blue), saneostore.de (red), omron (gray)
Toggle: Show/hide individual sources
Period: 4w | 8w | 12w | 26w
```

### Tier Classification (hardcoded, from SCAILE report)

```javascript
const TIER_MAP = {
  // Tier 1 — Highest AI visibility impact
  'chip.de': 'Tier 1',
  'which.co.uk': 'Tier 1',
  'testsieger.de': 'Tier 1',
  // Tier 2
  'altroconsumo.it': 'Tier 2',
  'ocu.org': 'Tier 2',
  'quechoisir.org': 'Tier 2',
  'faz.net': 'Tier 2',
  'welt.de': 'Tier 2',
  'stern.de': 'Tier 2',
  // Tier 3
  'konsument.at': 'Tier 3',
  'consumentenbond.nl': 'Tier 3',
  'ktipp.ch': 'Tier 3',
  'test.de': 'Tier 3',  // Stiftung Warentest
};
```

### Implementation

1. **Environment Variables:**
   ```
   PEEC_AI_API_KEY=<from Simon>
   PEEC_AI_ORG=<organization name>
   PEEC_AI_PROJECT_ID=<Beurer project ID>
   ```

2. **Data Fetching Strategy:**
   - Fetch fresh data from Peec AI API daily (or every 6 hours)
   - Store snapshots in a `peec_ai_snapshots` table for trend visualization
   - Each snapshot: `{ date, brand_visibility, brand_position, brand_sentiment, source_domains: [...] }`
   - Keep at least 26 weeks of history for trend charts

3. **Fallback:** If API is unavailable or rate-limited, continue supporting manual CSV upload as backup. Add a small "Upload CSV" button in the admin panel.

4. **API Key:** Simon will provide the API key. Add to Vercel environment variables.

### Acceptance Criteria
- [ ] Peec AI API connected and fetching data automatically
- [ ] Brand overview widget (Beurer vs Omron visibility, position, sentiment)
- [ ] Source domain table with citations, percentages, trends, tier classification
- [ ] Time-series chart with weekly data points (configurable period)
- [ ] Auto-refresh on schedule (daily minimum)
- [ ] CSV upload fallback in admin panel
- [ ] Environment variables for API credentials

---

## P5: AUTHOR PROFILES ON ARTICLES (NEW)

### Context
Beurer has confirmed two internal doctors as article authors:
1. **Doctor #1:** PhD in Linguistics — content/editorial expertise
2. **Doctor #2:** Head of Technical Development (Entwicklungsleiter) — product/technical expertise

Author profiles with LinkedIn links will be displayed on the website. Profiles are updated quarterly. This adds E-E-A-T credibility (Experience, Expertise, Authoritativeness, Trustworthiness) — critical for health content in Google and AI search.

### Requirements

**Author data model:**
```json
{
  "id": "uuid",
  "name": "Dr. [Name]",
  "title": "PhD in Linguistics",
  "role": "Content Editor",
  "bio": "Short bio (2-3 sentences about their expertise)",
  "linkedin_url": "https://linkedin.com/in/...",
  "photo_url": "/authors/dr-name.webp",  // optional
  "updated_at": "2026-03-12"
}
```

**Author box on article detail view:**
```
┌─────────────────────────────────────────────────┐
│  👤  Dr. [Name]                                 │
│      PhD in Linguistics | Content Editor        │
│      [Short bio about expertise and background] │
│      🔗 LinkedIn                                │
│      Zuletzt aktualisiert: März 2026            │
└─────────────────────────────────────────────────┘
```

**Implementation:**
- New `authors` table/collection with the fields above
- `article.author_id` foreign key (nullable — existing articles get author assigned later)
- Author selector in admin panel when creating/editing articles
- Author box rendered below the article content (before sources section)
- Author profile page (optional/later) — list of all articles by this author

### Article-Author Assignment
- Each article should have an `author_id` field
- Dropdown in admin panel to assign an author
- Default: null (show no author box if unassigned)
- Bulk assign: ability to set author for multiple articles at once

### Acceptance Criteria
- [ ] Authors table/collection with name, title, bio, LinkedIn URL
- [ ] Author box displayed below article content
- [ ] Author selector dropdown in admin panel (article edit)
- [ ] LinkedIn link opens in new tab
- [ ] Existing articles work without author (graceful fallback)
- [ ] Admin can edit author profiles (quarterly updates)

---

## P6: ANALYTICS INTEGRATION RESEARCH + REQUIREMENTS DOC (MEDIUM-HIGH PRIORITY)

### Context
We need GSC, GA4, Sistrix, and Salesforce integrated into the dashboard. But before we can build anything, we need the RIGHT credentials and permissions from Beurer. **Dilyana** is the contact for GSC/GA/Sistrix (available after SMX trade show mid-March). **Leana + Arthur** are the contacts for Salesforce.

**The problem:** We don't yet have a clear, specific list of what Beurer needs to set up on their side. Dharmay — your job is to research each API and write a requirements document that Simon can send directly to the Beurer team. This saves us back-and-forth and makes it easy for non-technical people to follow.

### Task 6.1: Research & Write Requirements Document

**Deliverable:** A markdown document `ANALYTICS_INTEGRATION_REQUIREMENTS.md` in `04_DEV_WORKSPACE/docs/` that Simon can forward to Beurer. It should be clear enough for a non-developer (Dilyana, Anika, Leana) to follow.

**For each integration (GSC, GA4, Sistrix, Salesforce), document:**

1. **What we need from Beurer** — exact permissions, credentials, access levels
2. **Step-by-step setup instructions** — what they need to click/configure on their side
3. **What data we'll pull** — so they understand what they're granting access to
4. **Security/privacy notes** — read-only access, no personal data, etc.
5. **Estimated setup time** — "this takes 10 minutes" vs "this needs IT approval"

**Structure the document like this:**

```markdown
# Analytics Integration Requirements for Beurer Team

## 1. Google Search Console (GSC)

### What we need
- [specific credentials / service account / OAuth scope]

### Setup steps (for Beurer)
1. Go to [URL]...
2. Click [button]...
3. Add [email] as [role]...

### What data we'll access
- [list of data points, e.g. impressions, clicks, CTR per URL]

### Security
- Read-only access, no changes to your GSC settings
- [other assurances]

### Setup time: ~X minutes

---

## 2. Google Analytics 4 (GA4)
[same structure]

## 3. Sistrix API
[same structure]

## 4. Salesforce
[same structure]
```

### Research Areas per Integration

**Google Search Console:**
- Research: Service account vs. OAuth vs. domain-level verification
- Which API scopes are needed? (`https://www.googleapis.com/auth/webmasters.readonly`?)
- Can Beurer add our service account email as a read-only user?
- API: `searchanalytics.query` — what dimensions/metrics are available?
- Rate limits?
- Docs: https://developers.google.com/webmaster-tools/v1/api_reference_index

**Google Analytics 4:**
- Research: GA4 Data API vs. Admin API — which do we need?
- Service account setup in Google Cloud Console
- Which GA4 property ID do we need from Beurer?
- Required role: `Viewer` on the GA4 property?
- API: `runReport` — available dimensions (page path, date) and metrics (sessions, pageviews, bounceRate, avgSessionDuration)
- Rate limits?
- Docs: https://developers.google.com/analytics/devguides/reporting/data/v1

**Sistrix:**
- Research: API key generation process — does Beurer generate it, or do we?
- Is API access included in their Sistrix plan, or is it an add-on?
- Which endpoints do we need? (`domain.sichtbarkeitsindex`, `domain.kwcount.seo`, `keyword.seo`)
- Rate limits and credit costs per API call?
- Can we use a sub-account or restricted API key?
- Docs: https://www.sistrix.com/api/

**Salesforce:**
- Research: Which Salesforce edition does Beurer use? (Enterprise/Professional/etc.)
- Is REST API access available in their edition?
- Can they create a Connected App with limited read-only scope?
- Which objects do we need? (Case, Account — anonymized)
- Can we get a Salesforce Flow that exports aggregated data automatically?
- GDPR: No personal data — only aggregated categories (product, issue type, resolution)
- Alternative: Regular CSV/Excel export to shared folder
- Contact: Leana + Arthur (Beurer IT)

### Acceptance Criteria
- [ ] `ANALYTICS_INTEGRATION_REQUIREMENTS.md` written and ready for Simon to send to Beurer
- [ ] Covers all 4 integrations: GSC, GA4, Sistrix, Salesforce
- [ ] Each section has: what we need, setup steps, data accessed, security notes, setup time
- [ ] Language: Clear enough for non-developers (Dilyana, Anika, Leana)
- [ ] Includes links to relevant documentation for each API
- [ ] Lists exact environment variables we'll need for each integration

---

## P7: PERFORMANCE TAB — UI SHELL WITH MOCK DATA (MEDIUM PRIORITY)

### Context
While we wait for Beurer to set up API access (based on the requirements doc from P6), build the Performance tab UI with mock/placeholder data. This lets us show Beurer the layout in the KW 12 meeting and gets buy-in on the design before real data flows in.

### What to Build Now
1. **New "Performance" tab** in dashboard navigation
2. **Per-article view** with placeholder metrics:
   ```
   Article: "Blutdruck richtig messen"
   Published: [date] on beurer.com/...

   GSC (last 28 days):          GA4 (last 28 days):
   - Impressions: —             - Pageviews: —
   - Clicks: —                  - Avg. Time: —
   - CTR: —                     - Bounce Rate: —
   - Avg Position: —

   Sistrix:
   - Visibility Index: —
   - Keyword Rankings: —
   ```
3. **Aggregate overview** (total clicks, impressions, top articles) — with mock data
4. **Time period filter** (7d, 28d, 90d)
5. **"Awaiting API access" banner** — clear visual indicator that real data is coming

### What to Integrate Later (when Beurer provides access per P6 requirements doc)
- Google Search Console API (service account)
- Google Analytics 4 Data API
- Sistrix API
- Map published article URLs to GSC/GA data

### Acceptance Criteria
- [ ] New "Performance" tab visible in dashboard navigation
- [ ] Per-article metrics layout (GSC + GA4 + Sistrix columns)
- [ ] Aggregate overview section with mock data
- [ ] Time period filter (7d, 28d, 90d)
- [ ] Clear "awaiting credentials" placeholder/banner where real data will go
- [ ] Environment variables scaffolded for all API keys
- [ ] Sistrix section: placeholder for visibility index + trend chart + keyword rankings

---

## P8: EMAIL NOTIFICATIONS (MEDIUM PRIORITY)

*No changes from last sprint — see Sprint Plan March 10 for full spec.*

### Quick Summary
- **Trigger 1:** New comment added → notify other reviewers
- **Trigger 2:** Review status changed → notify Kevin (CMS uploader)
- **Trigger 3:** Article edited → notify reviewers
- Use SendGrid/Resend or daily digest for MVP
- Recipient list from P1 dropdown names

### Acceptance Criteria
- [ ] Email sent when new comment is added
- [ ] Email sent when review status changes
- [ ] Email contains article title, commenter name, comment text, dashboard link
- [ ] Configurable recipient list

---

## P9: IMAGE/INFOGRAPHIC PROTOTYPES (LOWER PRIORITY)

*No changes from last sprint — see Sprint Plan March 10 for full spec.*

### Quick Summary
- Create 2-3 prototypes: 1 KI-generated hero image, 1 infographic, 1 step-by-step visual
- Format: WebP, under 500KB each
- Show to Simon for review before client presentation

---

## P10: SOURCE LINK VALIDATION (ONGOING)

*No changes from last sprint — see Sprint Plan March 10 for full spec.*

### Quick Summary
- Automated link checker on article save/approval
- Flag dead links (404/500) and competitor domains (Omron, Withings, AUVON etc.)
- ALLOWED: Apothekenumschau, FAZ Kaufkompass, PubMed, RKI
- Show warning badge on articles

---

## TIMELINE OVERVIEW

```
Thu Mar 13:
├── P1: Comment author attribution (finish)
├── P2: Publish status field (finish)
└── P3: News feed — backend + data sources (START)

Fri Mar 14:
├── P1 + P2: Done ✅
├── P3: News feed — UI + tab
└── P4: Peec AI API — connect + first data fetch

Mon Mar 16:
├── P3: News feed — SHIP IT 🚀 (Simon promised this date!)
└── P4: Peec AI — media visibility widget

Tue-Wed Mar 17-18:
├── P4: Peec AI — trend charts + domain table
├── P5: Author profiles — data model + UI
├── P6: Research + write ANALYTICS_INTEGRATION_REQUIREMENTS.md
└── P7: Performance tab — UI shell with mock data

Thu-Fri Mar 19-21:
├── P5: Author profiles — admin editing
├── P6: Requirements doc DONE → Simon sends to Beurer
├── P7: Performance tab — finalize structure
├── P8: Email notifications MVP
└── P9: Image prototypes (2-3 examples)

Week of Mar 24:
├── Polish all features based on Beurer feedback
├── P10: Link validation automated
├── P7: Real API integration (if Beurer provides credentials per P6 doc)
└── Prepare for magazine migration (early April)

Early April:
└── Magazine migration → articles go live on beurer.com
```

---

## KEY DECISIONS FROM MEETINGS (March 10)

| Decision | Detail |
|----------|--------|
| **Two doctors as article authors** | Linguistics PhD + Head of Technical Development. Author profiles with LinkedIn on website. Quarterly updates. |
| **Dilyana = Sistrix/GA contact** | Not Diana. Available after SMX trade show (mid-March). |
| **Magazine launch early April** | Confirmed by Beurer IT. Gradual article publishing to observe impact. |
| **UGC/Avatar strategy** | BMW "Lily" as benchmark. Beurer creating KI avatar models. Separate project from PoC — led by Kerstin. |
| **ChatGPT Ads** | Target + OpenAI partnership (US only). EU 3-6 months behind. Monitor via news feed. |
| **Infographics > KI-Images** | Anika sees infographics as more valuable for readers. |
| **Feedback → Training data** | Recurring feedback points get incorporated into article generation prompts. |

---

## API KEYS & ENVIRONMENT VARIABLES

```bash
# Peec AI (Simon will provide)
PEEC_AI_API_KEY=
PEEC_AI_ORG=
PEEC_AI_PROJECT_ID=

# Sistrix (from Dilyana — after SMX)
SISTRIX_API_KEY=

# Google Search Console (from Dilyana — after SMX)
GSC_SERVICE_ACCOUNT_JSON=

# Google Analytics 4 (from Dilyana — after SMX)
GA4_PROPERTY_ID=
GA4_SERVICE_ACCOUNT_JSON=

# Email notifications (choose one)
SENDGRID_API_KEY=
# or
RESEND_API_KEY=

# News feed sources
YOUTUBE_API_KEY=
# X/Twitter API (optional for MVP)
TWITTER_BEARER_TOKEN=
```

---

## QUESTIONS

### For Chandine (Product):
1. **P3 (News Feed):** Please review the spec above and brief Dharmay on how the information should be best aggregated, evaluated, and displayed with Beurer relevance. Key questions:
   - How should we generate the `beurer_context` field? (AI-generated summary, rule-based templates, or manual curation?)
   - What's the best UX: chronological feed, relevance-sorted, or daily digest format?
   - Should we include a weekly rollup / "Top 5 of the week" summary?
   - How do we handle information volume? (could be 50+ items/day — need smart filtering)
2. **Timeline:** Can you review the spec and brief Dharmay by end of Thursday March 13, so he can start building Friday?

### For Dharmay (Developer):
1. **P3 (News Feed):** After Chandine briefs you — can you realistically ship a basic version by Monday March 16? X/Twitter API is the highest-priority source. What's your experience with the X API v2?
2. **P4 (Peec AI):** Have you worked with REST APIs that require API key auth? The Peec AI API is in beta — documentation at https://docs.peec.ai/api/introduction. I'll get the API key to you today.
3. **P5 (Author Profiles):** Should authors be a separate collection/table, or can we add author fields directly to the article model? Separate table is cleaner but more work.
4. **P6 (Requirements Doc):** This is a research task, not coding. Read the API docs for GSC, GA4, Sistrix, and Salesforce and write down exactly what Beurer needs to set up on their side. Think of it as a checklist we can email to non-technical people. Can you deliver this by Wednesday March 19?
5. **P7 (Performance Tab):** Can you build the UI shell with mock data, so we can show Beurer the layout in the KW 12 meeting?
6. **General:** What's your capacity this week? I need to know if P1+P2+P3 by Monday is realistic, or if we should cut scope somewhere.

### For Yousif (Developer — Social Listening):
1. Existing tasks from previous sprints remain the same for you. Focus on Social Listening dashboard improvements.

---

## REFERENCE FILES

| File | Purpose |
|------|---------|
| Previous sprint plan (Mar 10) | `04_DEV_WORKSPACE/docs/DEVELOPER_SPRINT_PLAN_2026-03-10.md` |
| Previous sprint plan (Mar 5) | `04_DEV_WORKSPACE/docs/DEVELOPER_SPRINT_PLAN_2026-03-05.md` |
| Peec AI channel insights | `04_DEV_WORKSPACE/docs/PEEC_AI_CHANNEL_INSIGHTS_FOR_ENGINEER_2026-02-09.md` |
| Article flow diagram | `04_DEV_WORKSPACE/docs/ARTICLE_FLOW.md` |
| HTML template v2 | `03_SCAILE_DELIVERABLES/templates/Best_Practice_Magazinartikel_v2.html` |
| Peec AI raw data | `08_EXTERNAL_DATA/PEEC/` |
| KI-Relevanz Report | `03_SCAILE_DELIVERABLES/reports/2026-03-02_KI_Relevanz_Testmagazine_Report.pdf` |
| Project status | `00_PROJECT_HUB/PROJECT_STATUS.md` |
| Dashboard URL | `https://social-listening-service.vercel.app/api/dashboard` |
| Admin URL | `https://social-listening-service.vercel.app/api/admin` |
| Peec AI API Docs | `https://docs.peec.ai/api/introduction` |

---

**PRIORITY SUMMARY:**
1. 🔴 P1+P2 by Friday — comment attribution + publish status
2. 🔴 P3 by Monday — news feed (Simon promised this to Beurer!)
3. 🟡 P4+P5 by Wednesday next week — Peec AI + author profiles
4. 🟡 P6 by Wednesday next week — research + requirements doc (so Simon can send to Beurer!)
5. 🟢 P7-P10 by end of next week — analytics UI shell, notifications, images, link validation

Simon

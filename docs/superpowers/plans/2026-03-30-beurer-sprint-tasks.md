# Formmed Sprint KW14/15 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 6 client-requested features: SERP preview in article modal, AI visibility dashboard visualization, Salesforce CSV import + Kundendienst tab, known issues per product, multi-language article generation, and hreflang tags.

**Architecture:** Each task is independent except Task 5 (multi-language) which benefits from Task 6 (hreflang) for article group linking. Tasks modify the dashboard template (`styles/dashboard_template.html`), article generation pipeline (`blog/`), and API routes (`dashboard/app/api/`). No new frameworks — extends existing patterns.

**Tech Stack:** Python 3.11 (FastAPI), Next.js (TypeScript), Supabase (PostgreSQL), Chart.js, Gemini API, Peekaboo API

**Spec:** `docs/superpowers/specs/2026-03-30-formmed-sprint-tasks-design.md`
**Existing Salesforce spec:** `docs/superpowers/specs/2026-03-26-salesforce-service-cases-design.md`

---

## Task 1: Meta Title + Description — SERP Preview

**Files:**
- Modify: `blog/shared/models.py:294-312` (validators)
- Modify: `blog/stage_cleanup/cleanup.py:265-266` (validation)
- Modify: `blog/article_service.py:408-417` (generate save)
- Modify: `blog/article_service.py:637-649` (regenerate save)
- Create: `migrations/010_blog_article_meta_title.sql`
- Modify: `styles/dashboard_template.html:6460-6474` (SERP preview card)

### Step 1.1: Update Meta_Title validator to 60 chars

- [ ] **Edit `blog/shared/models.py`**

Change line 106 field description:
```python
Meta_Title: str = Field(..., description="≤60 character SEO title with primary keyword")
```

Change validator at lines 294-304:
```python
    @field_validator("Meta_Title")
    @classmethod
    def meta_title_length(cls, v):
        if len(v) > 60:
            logger.warning(f"Meta Title exceeds 60 chars: {len(v)} chars, truncating...")
            truncated = v[:57]
            last_space = truncated.rfind(' ')
            if last_space > 40:
                truncated = v[:last_space]
            return truncated + "..."
        return v
```

### Step 1.2: Update Meta_Description validator to 155 chars

- [ ] **Edit `blog/shared/models.py`**

Change line 107 field description:
```python
Meta_Description: str = Field(..., description="≤155 character SEO description with CTA")
```

Change validator at lines 306-312:
```python
    @field_validator("Meta_Description")
    @classmethod
    def meta_description_length(cls, v):
        if len(v) > 155:
            logger.warning(f"Meta Description exceeds 155 chars: {len(v)} chars, truncating...")
            return v[:152] + "..."
        return v
```

### Step 1.3: Update cleanup validation

- [ ] **Edit `blog/stage_cleanup/cleanup.py`**

Change lines 254-266:
```python
    - Required fields (meta_title, Intro, Direct_Answer)
    - Meta title length (max 60 chars)
    - Section count
    - FAQ/PAA count
    """
    warnings = []
    stats = ValidationStats()

    # Check meta_title
    meta_title = article.get("Meta_Title", "")
    if not meta_title:
        warnings.append("Missing Meta_Title")
    elif len(meta_title) > 60:
        warnings.append(f"Meta_Title too long: {len(meta_title)} chars (max 60)")
```

### Step 1.4: Create migration for meta_title column

- [ ] **Create `migrations/010_blog_article_meta_title.sql`**

```sql
-- Add dedicated meta_title column (meta_description already exists)
ALTER TABLE blog_articles ADD COLUMN IF NOT EXISTS meta_title TEXT;

-- Backfill from article_json for existing articles
UPDATE blog_articles
SET meta_title = article_json->>'Meta_Title'
WHERE meta_title IS NULL
  AND article_json IS NOT NULL
  AND article_json->>'Meta_Title' IS NOT NULL;
```

- [ ] **Run migration against Supabase**

### Step 1.5: Save meta_title to DB in generate_article

- [ ] **Edit `blog/article_service.py`**

At lines 396-417, add `meta_title` extraction and save it alongside `meta_description`:

```python
        # Extract metadata
        headline = fixed_article.get("Headline", "") or fixed_article.get("headline", "")
        meta_title = (
            fixed_article.get("Meta_Title", "")
            or fixed_article.get("meta_title", "")
        )
        meta_description = (
            fixed_article.get("Meta_Description", "")
            or fixed_article.get("meta_description", "")
        )
        actual_word_count = len(article_html.split())

        # Store pipeline reports in article_json for transparency
        fixed_article["_pipeline_reports"] = pipeline_reports

        # Update row as completed
        supabase.table("blog_articles").update({
            "status": "completed",
            "headline": headline,
            "meta_title": meta_title,
            "meta_description": meta_description,
            "article_html": article_html,
            "article_json": fixed_article,
            "word_count": actual_word_count,
            "error_message": None,
            "html_custom": False,
        }).eq("id", article_id).execute()
```

### Step 1.6: Save meta_title to DB in regenerate_article

- [ ] **Edit `blog/article_service.py`**

At lines 637-649, add `meta_title` to the update dict:

```python
        supabase.table("blog_articles").update({
            "status": "completed",
            "headline": headline,
            "meta_title": (
                fixed_article.get("Meta_Title", "")
                or fixed_article.get("meta_title", "")
            ),
            "meta_description": (
                fixed_article.get("Meta_Description", "")
                or fixed_article.get("meta_description", "")
            ),
            "article_html": article_html,
            "article_json": fixed_article,
            "word_count": actual_word_count,
            "error_message": None,
            "html_custom": False,
        }).eq("id", article_id).execute()
```

### Step 1.7: Add SERP preview card to article modal

- [ ] **Edit `styles/dashboard_template.html`**

Add CSS for the SERP preview card. Find the article modal CSS section (around line 1176) and add:

```css
.serp-preview {
    margin: 0 20px 12px;
    padding: 16px 20px;
    background: #fff;
    border: 1px solid var(--gray-200);
    border-radius: 10px;
    font-family: arial, sans-serif;
}
.serp-preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
}
.serp-preview-header span {
    font-size: 11px;
    font-weight: 600;
    color: var(--gray-400);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.serp-preview-url {
    font-size: 14px;
    color: #202124;
    line-height: 1.3;
    margin-bottom: 4px;
}
.serp-preview-url cite {
    color: #4d5156;
    font-style: normal;
    font-size: 12px;
}
.serp-preview-title {
    font-size: 20px;
    color: #1a0dab;
    line-height: 1.3;
    margin-bottom: 4px;
    cursor: default;
}
.serp-preview-desc {
    font-size: 14px;
    color: #4d5156;
    line-height: 1.58;
}
.serp-field {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
}
.serp-field-text { flex: 1; }
.serp-char-count {
    font-size: 11px;
    color: var(--gray-400);
    margin-top: 2px;
}
.serp-char-count.warn { color: var(--error); }
.serp-copy-btn {
    flex-shrink: 0;
    background: none;
    border: 1px solid var(--gray-200);
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    color: var(--gray-500);
    cursor: pointer;
    transition: all 0.15s;
}
.serp-copy-btn:hover { border-color: var(--gray-400); color: var(--gray-700); }
.serp-copy-btn.copied { border-color: var(--success); color: var(--success); }
```

- [ ] **Add SERP preview HTML to the article modal**

In `openArticleModal()`, insert the SERP preview card between the context badges div (line 6471) and the `.article-modal-panels` div (line 6472). The SERP card should only render for completed articles.

Find this exact line (6471-6472):
```javascript
                </div>` : ''}
                <div class="article-modal-panels viewer-mode" id="article-modal-panels">
```

Replace with:
```javascript
                </div>` : ''}
                ${['completed','review','approved','published'].includes(article.status) ? (() => {
                    const aj = article.article_json || {};
                    const mt = aj.Meta_Title || article.meta_title || article.headline || '';
                    const md = aj.Meta_Description || article.meta_description || '';
                    const mtMax = 60, mdMax = 155;
                    return `<div class="serp-preview" id="serp-preview-card">
                        <div class="serp-preview-header">
                            <span>Google Search Preview</span>
                            <button class="serp-copy-btn" onclick="copySerpAll(this)">${t('copy_all') || 'Copy All'}</button>
                        </div>
                        <div class="serp-preview-url"><cite>beurer.com &rsaquo; ratgeber</cite></div>
                        <div class="serp-field">
                            <div class="serp-field-text">
                                <div class="serp-preview-title" id="serp-meta-title">${esc(mt)}</div>
                                <div class="serp-char-count${mt.length > mtMax ? ' warn' : ''}">${mt.length}/${mtMax}</div>
                            </div>
                            <button class="serp-copy-btn" onclick="copySerpField(this, 'serp-meta-title')">Copy</button>
                        </div>
                        <div class="serp-field" style="margin-top:8px;">
                            <div class="serp-field-text">
                                <div class="serp-preview-desc" id="serp-meta-desc">${esc(md)}</div>
                                <div class="serp-char-count${md.length > mdMax ? ' warn' : ''}">${md.length}/${mdMax}</div>
                            </div>
                            <button class="serp-copy-btn" onclick="copySerpField(this, 'serp-meta-desc')">Copy</button>
                        </div>
                    </div>`;
                })() : ''}
                <div class="article-modal-panels viewer-mode" id="article-modal-panels">
```

- [ ] **Add copy helper functions**

Add these functions near the other article modal helpers (around line 6400):

```javascript
function copySerpField(btn, elementId) {
    const text = document.getElementById(elementId)?.textContent || '';
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '✓';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1500);
    });
}
function copySerpAll(btn) {
    const mt = document.getElementById('serp-meta-title')?.textContent || '';
    const md = document.getElementById('serp-meta-desc')?.textContent || '';
    navigator.clipboard.writeText(`Meta Title: ${mt}\nMeta Description: ${md}`).then(() => {
        btn.textContent = '✓ Copied';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Copy All'; btn.classList.remove('copied'); }, 1500);
    });
}
```

### Step 1.8: Commit

- [ ] **Commit all Task 1 changes**

```bash
git add blog/shared/models.py blog/stage_cleanup/cleanup.py blog/article_service.py \
    migrations/010_blog_article_meta_title.sql styles/dashboard_template.html
git commit -m "feat: add SERP preview card with copy buttons to article modal

Update meta title limit to 60 chars, meta description to 155 chars.
Add meta_title DB column with backfill migration.
Google-style preview card in article modal for easy copy to CMS."
```

---

## Task 2: AI Visibility Dashboard — Peekaboo Visualization

**Files:**
- Modify: `styles/dashboard_template.html` (rewrite `renderMediaTabFromData()` and add AI model badges/filter)

> **Note:** The existing `renderMediaTabFromData()` at lines 7128-7251 already has a solid 5-section structure with KPI cards, competitor chart, prompts table, sources table, and suggestions. The main additions are: AI model filter on prompts, AI model colored dots, and enhanced source visualization. This is primarily a template enhancement — no backend changes needed.

### Step 2.1: Add localization strings for AI model filtering

- [ ] **Edit `styles/dashboard_template.html`**

Find the German localization object (around line 1880 where `media_` keys are defined) and add:

```javascript
media_filter_all: 'Alle',
media_filter_model: 'KI-Modell Filter',
media_model_label: 'KI-Modelle',
media_no_data: 'Keine Daten verfügbar.',
media_loading: 'Lade AI-Sichtbarkeit...',
```

Find the English localization object (around line 2540) and add matching English keys:

```javascript
media_filter_all: 'All',
media_filter_model: 'AI Model Filter',
media_model_label: 'AI Models',
media_no_data: 'No data available.',
media_loading: 'Loading AI visibility...',
```

### Step 2.2: Add AI model color mapping

- [ ] **Edit `styles/dashboard_template.html`**

Add a constant near the top of the `<script>` section (around where other constants like `reasonColors` are defined, before `renderMediaTabFromData`):

```javascript
const AI_MODEL_COLORS = {
    'ChatGPT': '#10A37F',
    'Perplexity': '#4A90D9',
    'Gemini': '#8E24AA',
    'Claude': '#D4A574',
    'AI Mode': '#FF9500',
    'Copilot': '#0078D4',
};
function aiModelDot(model) {
    const color = AI_MODEL_COLORS[model] || '#8E8E93';
    return `<span title="${esc(model)}" style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:3px;"></span>`;
}
function aiModelBadge(model) {
    const color = AI_MODEL_COLORS[model] || '#8E8E93';
    return `<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:12px;font-size:11px;background:${color}15;color:${color};border:1px solid ${color}30;">${aiModelDot(model)}${esc(model)}</span>`;
}
```

### Step 2.3: Enhance prompts table with AI model filter and badges

- [ ] **Edit `styles/dashboard_template.html`**

Replace the existing `renderMediaPromptTable()` function (find it after `renderMediaTabFromData`) with an enhanced version that adds AI model filtering and badges:

```javascript
function renderMediaPromptTable() {
    const wrap = document.getElementById('mediaPromptTableWrap');
    if (!wrap) return;
    const prompts = (mediaVisibilityData?.prompts || []);
    if (!prompts.length) return;

    // Collect unique AI models across all prompts
    const allModels = new Set();
    prompts.forEach(p => (p.aiModels || []).forEach(m => allModels.add(m)));
    const modelList = [...allModels].sort();

    let activeFilter = 'all';
    const PAGE_SIZE = 10;
    let currentPage = 0;

    function render() {
        const filtered = activeFilter === 'all'
            ? prompts
            : prompts.filter(p => (p.aiModels || []).includes(activeFilter));
        const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
        const page = filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE);

        let html = `<div style="padding:12px 16px;display:flex;flex-wrap:wrap;gap:6px;border-bottom:1px solid var(--gray-100);">
            <button class="filter-btn${activeFilter === 'all' ? ' active' : ''}" onclick="this.closest('#mediaPromptTableWrap').__filterModel('all')">${t('media_filter_all')}</button>
            ${modelList.map(m => `<button class="filter-btn${activeFilter === m ? ' active' : ''}" onclick="this.closest('#mediaPromptTableWrap').__filterModel('${esc(m)}')">${aiModelDot(m)} ${esc(m)}</button>`).join('')}
        </div>`;

        html += `<table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="background:var(--gray-50);border-bottom:1px solid var(--gray-100);">
                <th style="padding:10px 16px;text-align:left;font-weight:600;">Prompt</th>
                <th style="padding:10px 12px;text-align:center;font-weight:600;width:70px;">Score</th>
                <th style="padding:10px 12px;text-align:center;font-weight:600;width:90px;">Mentions</th>
                <th style="padding:10px 16px;text-align:left;font-weight:600;width:180px;">${t('media_model_label')}</th>
            </tr></thead><tbody>`;

        page.forEach(p => {
            const models = (p.aiModels || []);
            html += `<tr style="border-bottom:1px solid var(--gray-50);">
                <td style="padding:10px 16px;line-height:1.4;">${esc(p.text)}</td>
                <td style="padding:10px 12px;text-align:center;font-weight:600;">${p.score}</td>
                <td style="padding:10px 12px;text-align:center;">${p.mentions}</td>
                <td style="padding:10px 16px;"><div style="display:flex;flex-wrap:wrap;gap:4px;">${models.map(m => aiModelBadge(m)).join('')}</div></td>
            </tr>`;
        });

        html += `</tbody></table>`;

        if (totalPages > 1) {
            html += `<div style="padding:12px 16px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid var(--gray-100);">
                <span style="font-size:12px;color:var(--gray-400);">${filtered.length} prompts</span>
                <div style="display:flex;gap:6px;">
                    <button class="filter-btn" ${currentPage === 0 ? 'disabled' : ''} onclick="this.closest('#mediaPromptTableWrap').__prevPage()">← Prev</button>
                    <span style="font-size:12px;color:var(--gray-500);padding:6px;">${currentPage + 1}/${totalPages}</span>
                    <button class="filter-btn" ${currentPage >= totalPages - 1 ? 'disabled' : ''} onclick="this.closest('#mediaPromptTableWrap').__nextPage()">Next →</button>
                </div>
            </div>`;
        }

        wrap.innerHTML = html;
    }

    wrap.__filterModel = (m) => { activeFilter = m; currentPage = 0; render(); };
    wrap.__prevPage = () => { currentPage = Math.max(0, currentPage - 1); render(); };
    wrap.__nextPage = () => { currentPage++; render(); };
    render();
}
```

### Step 2.4: Enhance source table with horizontal bars

- [ ] **Edit `styles/dashboard_template.html`**

Replace the existing `renderMediaSourceTable()` function with an enhanced version that adds horizontal bar visualization:

```javascript
function renderMediaSourceTable() {
    const wrap = document.getElementById('mediaSourceTableWrap');
    if (!wrap) return;
    const sources = (mediaVisibilityData?.sources || []).sort((a, b) => b.mentions - a.mentions);
    if (!sources.length) return;

    const maxMentions = sources[0]?.mentions || 1;
    const PAGE_SIZE = 15;
    let showAll = false;

    function render() {
        const visible = showAll ? sources : sources.slice(0, PAGE_SIZE);
        let html = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="background:var(--gray-50);border-bottom:1px solid var(--gray-100);">
                <th style="padding:10px 16px;text-align:left;font-weight:600;">Domain</th>
                <th style="padding:10px 16px;text-align:left;font-weight:600;width:50%;">Mentions</th>
                <th style="padding:10px 16px;text-align:left;font-weight:600;width:180px;">${t('media_model_label')}</th>
            </tr></thead><tbody>`;

        visible.forEach(s => {
            const barWidth = Math.max(4, (s.mentions / maxMentions) * 100);
            const models = (s.aiModels || []);
            html += `<tr style="border-bottom:1px solid var(--gray-50);">
                <td style="padding:10px 16px;font-weight:500;">${esc(s.domain)}</td>
                <td style="padding:10px 16px;">
                    <div style="display:flex;align-items:center;gap:10px;">
                        <div style="flex:1;height:8px;background:var(--gray-100);border-radius:4px;overflow:hidden;">
                            <div style="height:100%;width:${barWidth}%;background:#C60050;border-radius:4px;"></div>
                        </div>
                        <span style="font-weight:600;min-width:30px;text-align:right;">${s.mentions}</span>
                    </div>
                </td>
                <td style="padding:10px 16px;"><div style="display:flex;flex-wrap:wrap;gap:2px;">${models.map(m => aiModelDot(m)).join('')}</div></td>
            </tr>`;
        });

        html += `</tbody></table>`;

        if (!showAll && sources.length > PAGE_SIZE) {
            html += `<div style="padding:12px 16px;text-align:center;border-top:1px solid var(--gray-100);">
                <button class="filter-btn" onclick="this.closest('#mediaSourceTableWrap').__showAll()">${sources.length - PAGE_SIZE} weitere anzeigen</button>
            </div>`;
        }

        wrap.innerHTML = html;
    }

    wrap.__showAll = () => { showAll = true; render(); };
    render();
}
```

### Step 2.5: Commit

- [ ] **Commit Task 2 changes**

```bash
git add styles/dashboard_template.html
git commit -m "feat: enhance AI visibility tab with model filters and source bars

Add AI model color-coded badges and filter bar to prompts table.
Add horizontal bar visualization to source citations table.
Add localization strings for AI model filtering."
```

---

## Task 3: Salesforce Import — Dashboard Upload + Executive Overview KPI

**Files:**
- Create: `dashboard/app/api/kundendienst/route.ts`
- Modify: `styles/dashboard_template.html` (upload button + Executive Overview KPI card)

> **Note:** The full Salesforce import pipeline (Python backend, DB schema, TypeScript aggregator) is covered by the existing spec at `docs/superpowers/specs/2026-03-26-salesforce-service-cases-design.md`. This task covers only the two additions to that spec: dashboard upload UI and Executive Overview KPI card.

### Step 3.1: Create Kundendienst API route for CSV upload

- [ ] **Create `dashboard/app/api/kundendienst/route.ts`**

```typescript
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL;

export async function POST(request: NextRequest) {
  try {
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "BACKEND_URL not configured — cannot proxy upload" },
        { status: 503 }
      );
    }

    const formData = await request.formData();
    const file = formData.get("file");
    if (!file || !(file instanceof File)) {
      return NextResponse.json({ error: "No file provided" }, { status: 400 });
    }

    // Proxy the file to the Python backend
    const backendForm = new FormData();
    backendForm.append("file", file);

    const clientId = formData.get("client_id") || "beurer";
    const backendRes = await fetch(
      `${BACKEND_URL}/api/v1/social-listening/import/service-cases?client_id=${clientId}`,
      { method: "POST", body: backendForm }
    );

    if (!backendRes.ok) {
      const err = await backendRes.text();
      return NextResponse.json(
        { error: `Backend error: ${err}` },
        { status: backendRes.status }
      );
    }

    const result = await backendRes.json();
    return NextResponse.json(result);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
```

### Step 3.2: Add CSV upload button to Kundendienst tab

- [ ] **Edit `styles/dashboard_template.html`**

In `renderKundendienstTab()` (line 9080), modify the section header to include an upload button. Replace the existing header:

```javascript
    let html = `
    <div class="section-header" style="margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
        <div class="section-title">${t('tab_kundendienst')}</div>
        ${isOnlineMode() ? `<label class="gen-article-btn" style="cursor:pointer;font-size:12px;">
            ${t('kd_upload_csv') || 'CSV hochladen'}
            <input type="file" accept=".csv,.xls,.xlsx" style="display:none;" onchange="handleKdCsvUpload(this)">
        </label>` : ''}
    </div>
```

- [ ] **Add upload handler function**

Add near the other Kundendienst functions (after `renderKundendienstTab`):

```javascript
async function handleKdCsvUpload(input) {
    const file = input.files?.[0];
    if (!file) return;
    input.value = '';

    const label = input.parentElement;
    const origText = label.textContent.trim();
    label.textContent = '⏳ Uploading...';
    label.style.pointerEvents = 'none';

    try {
        const form = new FormData();
        form.append('file', file);
        const res = await fetch('/api/kundendienst', { method: 'POST', body: form });
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        showToast(`Import: ${data.imported} imported, ${data.skipped} skipped`);
        // Re-fetch and re-render the tab
        setTimeout(() => location.reload(), 1500);
    } catch (err) {
        showToast('Upload failed: ' + err.message, 'error');
    } finally {
        label.innerHTML = `${origText}<input type="file" accept=".csv,.xls,.xlsx" style="display:none;" onchange="handleKdCsvUpload(this)">`;
        label.style.pointerEvents = '';
    }
}
```

### Step 3.3: Add Executive Overview KPI card for service cases

- [ ] **Edit `styles/dashboard_template.html`**

In `renderOverviewContent()` (around line 4210, after the existing KPI grid closing `</div>`), add a conditional service case KPI card to the grid. Find the end of the KPI grid and add this card before the closing `</div>`:

```javascript
// Add service case KPI card (inside the kpi-grid, after the last existing card)
const kdData = DASHBOARD_DATA.kundendienstInsights;
if (kdData && kdData.summary) {
    html += `<div class="kpi-card" style="cursor:pointer;" onclick="switchTab('kundendienst')">
        <div class="kpi-label">${t('kd_total_cases') || 'Service Cases'} ↗</div>
        <div class="kpi-value">${(kdData.summary.totalCases || 0).toLocaleString()}</div>
        <div class="kpi-delta neutral" style="font-size:11px;">${esc((kdData.summary.topReason || {}).reason || '')}</div>
    </div>`;
}
```

Add a localization string for the German label:
```javascript
kd_upload_csv: 'CSV hochladen',
```

### Step 3.4: Commit

- [ ] **Commit Task 3 changes**

```bash
git add dashboard/app/api/kundendienst/route.ts styles/dashboard_template.html
git commit -m "feat: add CSV upload UI for Kundendienst and service case KPI in overview

Dashboard upload button proxies to Python backend import endpoint.
Executive Overview shows service case count with link to Kundendienst tab."
```

---

## Task 4: Known Issues per Product

**Files:**
- Modify: `blog/product_catalog.json` (add known_issues to sample products)
- Modify: `blog/product_catalog.py` (add `get_product_known_issues()` and `find_product_for_keyword()`)
- Modify: `blog/article_service.py:290-300` (inject known issues into article context)

### Step 4.1: Add known_issues structure to product_catalog.json

- [ ] **Edit `blog/product_catalog.json`**

Add `known_issues` arrays to the products that have known issues. For now, add empty arrays as placeholders that Anika can fill in later. Add one example to EM 59:

Find the EM 59 entry:
```json
"EM 59": {"url": null, "priority": 1, "category": "pain_tens", "type": "tens_ems"},
```

Replace with:
```json
"EM 59": {"url": null, "priority": 1, "category": "pain_tens", "type": "tens_ems", "known_issues": []},
```

Also add empty `known_issues` to BM 81 (known software complaints from Salesforce data):
```json
"BM 81": {"url": null, "priority": 1, "category": "blood_pressure", "type": "oberarm", "known_issues": []},
```

> **Note:** Actual known issues will be populated once Anika provides the Health Manager Pro information. The structure is ready.

### Step 4.2: Add `find_product_for_keyword` and `get_product_known_issues` to product_catalog.py

- [ ] **Edit `blog/product_catalog.py`**

Add these two functions after the `load_catalog()` function (after line 110):

```python
def find_product_for_keyword(keyword: str) -> Optional[str]:
    """Extract a Beurer product model code from a keyword string.

    Examples:
        "Beurer EM 59 Erfahrung" → "EM 59"
        "BM27 Test" → "BM 27"
        "Blutdruck messen" → None
    """
    m = _PRODUCT_PATTERN.search(keyword)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return None


def get_product_known_issues(model_code: str) -> Optional[list]:
    """Return unresolved known issues for a product from the catalog JSON.

    Args:
        model_code: Normalized product code, e.g. "EM 59".

    Returns:
        List of issue dicts with keys: issue, severity, source, date_reported.
        None if no unresolved issues exist.
    """
    data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    product = data.get("products", {}).get(model_code, {})
    issues = product.get("known_issues", [])
    active = [i for i in issues if not i.get("resolved", False)]
    return active or None
```

### Step 4.3: Inject known issues into article generation context

- [ ] **Edit `blog/article_service.py`**

In `generate_article()`, after building `keyword_instructions` (around line 300), add known issues injection:

Find this code block (around lines 296-300):
```python
        # Build keyword instructions from social context
        keyword_instructions = _build_instructions_from_context(
            social_context, language
        )
```

Add after it:
```python
        # Inject known product issues if the keyword references a product
        from blog.product_catalog import find_product_for_keyword, get_product_known_issues
        product_model = find_product_for_keyword(keyword)
        if product_model:
            known_issues = get_product_known_issues(product_model)
            if known_issues:
                is_de = language.startswith("de")
                issues_lines = [f"- [{i['severity'].upper()}] {i['issue']}" for i in known_issues]
                issues_block = "\n".join(issues_lines)
                if is_de:
                    issues_section = (
                        f"\n\n## Bekannte Produkt-Hinweise (interne Quelle)\n{issues_block}\n"
                        "Berücksichtige diese Information im Artikel: erwähne das Problem sachlich, "
                        "biete Workarounds an falls bekannt, und vermeide Heilversprechen."
                    )
                else:
                    issues_section = (
                        f"\n\n## Known Product Issues (internal source)\n{issues_block}\n"
                        "Consider this information in the article: mention the issue factually, "
                        "offer workarounds if known, and avoid healing promises."
                    )
                keyword_instructions = (keyword_instructions or "") + issues_section
```

### Step 4.4: Commit

- [ ] **Commit Task 4 changes**

```bash
git add blog/product_catalog.json blog/product_catalog.py blog/article_service.py
git commit -m "feat: add known issues per product for article generation context

Structured known_issues field in product_catalog.json (issue, severity,
source, date_reported, resolved). Injected into article generation
prompt when keyword matches a product with active issues."
```

---

## Task 5: Multi-Language Article Generation (English)

**Files:**
- Modify: `blog/beurer_context.py:350-372` (add English-specific context)
- Modify: `blog/article_service.py:433-488` (add English source guidance)
- Modify: `styles/dashboard_template.html:5962-5972` (add language selector)

### Step 5.1: Add English context to beurer_context.py

- [ ] **Edit `blog/beurer_context.py`**

In `get_beurer_company_context()`, the function already branches on `is_de` for the `industry` field (line 353). Extend the language handling for additional fields. Find the return dict (lines 350-372) and replace it:

```python
    # English-specific overrides
    if not is_de:
        description = (
            "Beurer is a German health technology company with over 100 years of experience, "
            "specialising in clinically validated blood pressure monitors, TENS/EMS pain therapy "
            "devices, and infrared lamps. Known for German engineering quality and precision."
        )
        target_audience = (
            "Health-conscious adults aged 35-65 in the UK and US who research health topics "
            "online before purchasing medical devices for home use."
        )
        value_props = [
            "Over 100 years of German health technology expertise",
            "Clinically validated measurement accuracy",
            "Easy-to-use devices for all age groups",
            "Comprehensive range for different health needs",
            "Trusted by healthcare professionals across Europe",
        ]
        use_cases_en = [
            "Home blood pressure monitoring",
            "Pain therapy with TENS/EMS",
            "Heat therapy with infrared lamps",
            "Menstrual pain relief",
        ]
    else:
        description = ctx.get("description", _FALLBACK_CONTEXT["description"])
        target_audience = ctx.get("target_audience", _FALLBACK_CONTEXT["target_audience"])
        value_props = ctx.get("value_propositions", _FALLBACK_CONTEXT["value_propositions"])
        use_cases_en = ctx.get("use_cases", _FALLBACK_CONTEXT["use_cases"])

    return {
        "company_name": ctx.get("company_name", "Beurer"),
        "company_url": ctx.get("company_url", "https://www.beurer.com"),
        "industry": ctx.get("industry_de" if is_de else "industry_en",
                            "Gesundheit & Medizintechnik" if is_de else "Health & Medical Technology"),
        "description": description,
        "products": products,
        "target_audience": target_audience,
        "competitors": competitors,
        "tone": "professional",
        "pain_points": pain_points,
        "value_propositions": value_props,
        "use_cases": use_cases_en,
        "content_themes": content_themes,
        "voice_persona": persona,
        "visual_identity": {
            "primary_color": "#C60050",
            "secondary_colors": [],
            "image_style": "",
            "preferred_formats": [],
        },
        "authors": [],
    }
```

### Step 5.2: Add English source guidance to _build_instructions_from_context

- [ ] **Edit `blog/article_service.py`**

In `_build_instructions_from_context()`, add English-specific source guidance after the opening language check. Find lines 444-451 and extend:

```python
    is_de = language.startswith("de")
    lines = []

    if is_de:
        lines.append(
            "Dieser Artikel basiert auf echten Nutzerfragen aus dem Social Listening."
        )
    else:
        lines.append(
            "This article is based on real user questions from social listening."
        )
        lines.append(
            "IMPORTANT: Use only English-language sources. Prioritise UK/US health "
            "authorities (NHS, NICE, Mayo Clinic), English-language review sites "
            "(Which?, Trusted Reviews, Healthline), and English forums. "
            "Do NOT cite or translate German-language sources."
        )
```

### Step 5.3: Add language selector to article generation

- [ ] **Edit `styles/dashboard_template.html`**

In `handleGenerateArticle()` at line 5968, the language is currently hardcoded to `currentLang` (the dashboard's display language). This needs to be read from a per-article dropdown instead.

First, modify the article generation button in `renderContentOpportunitiesTable()` (around line 7775) to include a language dropdown. Find:

```javascript
${isOnlineMode() && o.source_item_id ? `<button class="gen-article-btn" onclick="handleGenerateArticle(this)" data-source-item-id="${o.source_item_id}" data-keyword="${articleKeyword}" data-context="${articleCtx}">${t('generate_article')}</button>` : ''}
```

Replace with:

```javascript
${isOnlineMode() && o.source_item_id ? `<span style="display:inline-flex;align-items:center;gap:4px;">
    <select class="article-lang-select" style="padding:4px 6px;border:1px solid var(--gray-200);border-radius:4px;font-size:12px;background:#fff;">
        <option value="de"${currentLang === 'de' ? ' selected' : ''}>DE</option>
        <option value="en"${currentLang === 'en' ? ' selected' : ''}>EN</option>
    </select>
    <button class="gen-article-btn" onclick="handleGenerateArticle(this)" data-source-item-id="${o.source_item_id}" data-keyword="${articleKeyword}" data-context="${articleCtx}">${t('generate_article')}</button>
</span>` : ''}
```

Then modify `handleGenerateArticle()` to read the language from the sibling dropdown. Find line 5968:

```javascript
                language: currentLang,
```

Replace with:

```javascript
                language: btn.parentElement.querySelector('.article-lang-select')?.value || currentLang,
```

### Step 5.4: Commit

- [ ] **Commit Task 5 changes**

```bash
git add blog/beurer_context.py blog/article_service.py styles/dashboard_template.html
git commit -m "feat: add English article generation with market-specific context

English company context, buyer personas, and value propositions.
English source selection guidance (NHS, UK review sites, no German sources).
Language dropdown per article in Content Planung tab."
```

---

## Task 6: hreflang Implementation

**Files:**
- Create: `migrations/011_blog_article_groups.sql`
- Modify: `blog/shared/html_renderer.py:159-168,320-333` (add hreflang param + tag injection)
- Modify: `blog/article_service.py:290-300` (auto-link articles by keyword+language)
- Create: `docs/hreflang-recommendation.md`

### Step 6.1: Create migration for article_group_id

- [ ] **Create `migrations/011_blog_article_groups.sql`**

```sql
-- Group articles by topic across languages for hreflang linking
ALTER TABLE blog_articles
ADD COLUMN IF NOT EXISTS article_group_id UUID;

-- Index for finding sibling articles in the same group
CREATE INDEX IF NOT EXISTS idx_blog_articles_group
ON blog_articles (article_group_id)
WHERE article_group_id IS NOT NULL;
```

- [ ] **Run migration against Supabase**

### Step 6.2: Add hreflang rendering to HTMLRenderer

- [ ] **Edit `blog/shared/html_renderer.py`**

Add the hreflang rendering method. Place it before the `render()` method (around line 155):

```python
    @staticmethod
    def _render_hreflang_tags(
        current_language: str,
        siblings: list,
    ) -> str:
        """Generate hreflang <link> tags for alternate language versions.

        Args:
            current_language: Language of the current article (e.g., "de", "en").
            siblings: List of dicts with keys 'language' and 'url' for all
                      versions (including self).

        Returns:
            HTML string of <link> tags, or empty string if no siblings.
        """
        if not siblings:
            return ""

        HREFLANG_MAP = {
            "de": "de",
            "en": "en",
            "en-us": "en-US",
        }

        tags = []
        for sib in siblings:
            lang = sib.get("language", "")
            url = sib.get("url", "")
            if not url:
                continue
            hreflang = HREFLANG_MAP.get(lang, lang)
            tags.append(
                f'<link rel="alternate" hreflang="{escape(hreflang)}" href="{escape(url)}">'
            )

        # x-default points to German (primary market)
        de_url = next((s["url"] for s in siblings if s.get("language") == "de" and s.get("url")), None)
        if de_url:
            tags.append(f'<link rel="alternate" hreflang="x-default" href="{escape(de_url)}">')

        return "\n    ".join(tags)
```

### Step 6.3: Add hreflang_siblings parameter to render()

- [ ] **Edit `blog/shared/html_renderer.py`**

Update the `render()` method signature (lines 159-168) to accept hreflang siblings:

```python
    def render(
        article: Dict[str, Any],
        company_name: str = "",
        company_url: str = "",
        author_name: str = "",
        language: str = "de",
        category: str = "",
        author: Optional[Dict[str, Any]] = None,
        last_updated: Optional[str] = None,
        hreflang_siblings: Optional[list] = None,
    ) -> str:
```

Then inject the hreflang tags into the HTML `<head>`. Find the Open Graph section (lines 329-333):

```python
    <!-- Open Graph -->
    <meta property="og:title" content="{escape(meta_title)}">
    <meta property="og:description" content="{escape(meta_desc)}">
    <meta property="og:type" content="article">
    {f'<meta property="og:image" content="{escape(hero_image)}">' if hero_image else ''}
```

Add after the OG image line:

```python
    {f'<meta property="og:image" content="{escape(hero_image)}">' if hero_image else ''}

    {HTMLRenderer._render_hreflang_tags(language, hreflang_siblings or []) if hreflang_siblings else '<!-- no hreflang siblings -->'}
```

### Step 6.4: Auto-link articles by keyword + language in article_service.py

- [ ] **Edit `blog/article_service.py`**

In `generate_article()`, after building the company context (around line 294), add article group linking logic. Find:

```python
        # Build company context
        company_context = get_beurer_company_context(language)
```

Add before it (so the group_id is available for the DB save):

```python
        # Auto-link with sibling articles in other languages (same keyword)
        from uuid import uuid4
        article_group_id = None
        try:
            sibling_result = supabase.table("blog_articles") \
                .select("id, article_group_id") \
                .eq("keyword", keyword) \
                .neq("language", language) \
                .limit(1).execute()
            if sibling_result.data:
                sib = sibling_result.data[0]
                article_group_id = sib.get("article_group_id")
                if not article_group_id:
                    article_group_id = str(uuid4())
                    supabase.table("blog_articles") \
                        .update({"article_group_id": article_group_id}) \
                        .eq("id", sib["id"]).execute()
        except Exception as e:
            logger.warning(f"Article group linking failed (non-blocking): {e}")
```

Then in the DB update at line 408, add `article_group_id`:

```python
        supabase.table("blog_articles").update({
            "status": "completed",
            "headline": headline,
            "meta_title": meta_title,
            "meta_description": meta_description,
            "article_html": article_html,
            "article_json": fixed_article,
            "word_count": actual_word_count,
            "error_message": None,
            "html_custom": False,
            **({"article_group_id": article_group_id} if article_group_id else {}),
        }).eq("id", article_id).execute()
```

### Step 6.5: Pass hreflang siblings when rendering HTML

- [ ] **Edit `blog/article_service.py`**

Before the `HTMLRenderer.render()` call (around line 385), fetch sibling articles for hreflang:

```python
        # Fetch hreflang siblings for HTML rendering
        hreflang_siblings = []
        if article_group_id:
            try:
                siblings_result = supabase.table("blog_articles") \
                    .select("language, publish_url") \
                    .eq("article_group_id", article_group_id) \
                    .not_.is_("publish_url", "null") \
                    .execute()
                hreflang_siblings = [
                    {"language": s["language"], "url": s["publish_url"]}
                    for s in (siblings_result.data or [])
                    if s.get("publish_url")
                ]
            except Exception as e:
                logger.warning(f"hreflang sibling lookup failed: {e}")
```

Then pass `hreflang_siblings` to the render call. Find the `HTMLRenderer.render(` call and add the parameter:

```python
        article_html = HTMLRenderer.render(
            article=fixed_article,
            company_name=company_context.get("company_name", ""),
            company_url=company_context.get("company_url", ""),
            language=language,
            category=article_category,
            author=author_data,
            hreflang_siblings=hreflang_siblings,
        )
```

### Step 6.6: Create CMS recommendation document

- [ ] **Create `docs/hreflang-recommendation.md`**

```markdown
# hreflang Implementation Recommendation for Beurer CMS (Makaria)

## What is hreflang?

hreflang tags tell Google which language/region version of a page exists, preventing duplicate content penalties when the same content appears on multiple domains or language paths.

## Our Pipeline Output

When articles are generated in multiple languages (DE + EN), our pipeline outputs hreflang `<link>` tags in the article HTML `<head>`:

```html
<link rel="alternate" hreflang="de" href="https://www.beurer.com/de/ratgeber/article-slug">
<link rel="alternate" hreflang="en" href="https://www.beurer.com/en/ratgeber/article-slug">
<link rel="alternate" hreflang="en-US" href="https://www.beurer-us.com/ratgeber/article-slug">
<link rel="alternate" hreflang="x-default" href="https://www.beurer.com/de/ratgeber/article-slug">
```

## CMS Implementation Options

### Option A: Preserve pipeline hreflang tags (recommended)
If Makaria can preserve the `<head>` content from our HTML output, the hreflang tags will be included automatically. No CMS-side changes needed.

### Option B: CMS-managed hreflang
If Makaria strips custom `<head>` tags, implement hreflang server-side:
1. Create a mapping table: `article_slug` → `{de_url, en_url, us_url}`
2. On each page render, inject hreflang tags from this mapping
3. Each language version must reference ALL other versions (including itself)

## Key Rules

1. **Self-referencing:** Each page must include an hreflang tag pointing to itself
2. **Bidirectional:** If page A links to page B, page B must link back to page A
3. **x-default:** Points to the "fallback" version (German, as primary market)
4. **Canonical:** Each language version uses its own URL as canonical (no cross-domain canonicals)
5. **URL format:** Use absolute URLs with protocol (https://)

## US Site

For the US subsidiary domain:
- Use `hreflang="en-US"` with the full US domain URL
- The US page should also include hreflang tags pointing to the DE and EN versions
- If content is identical to the EN version, still use separate hreflang values (`en` vs `en-US`)

## Testing

Verify implementation with:
- [Google Search Console](https://search.google.com/search-console/) → International Targeting
- [Ahrefs Site Audit](https://ahrefs.com/site-audit) → hreflang report
- Manual check: view page source and verify all hreflang tags are present and bidirectional
```

### Step 6.7: Commit

- [ ] **Commit Task 6 changes**

```bash
git add migrations/011_blog_article_groups.sql blog/shared/html_renderer.py \
    blog/article_service.py docs/hreflang-recommendation.md
git commit -m "feat: implement hreflang tags for multi-language article linking

Add article_group_id column for cross-language article grouping.
Auto-link articles by keyword when generating in different languages.
Inject hreflang <link> tags into article HTML <head>.
Add CMS recommendation document for Beurer's Makaria team."
```

---

## Summary

| Task | Steps | Files Changed | Key Risk |
|------|-------|---------------|----------|
| 1. SERP Preview | 1.1–1.8 | 5 files + 1 migration | Modal HTML injection must preserve existing structure |
| 2. AI Visibility | 2.1–2.5 | 1 file (template) | Chart.js already loaded; just rendering changes |
| 3. Salesforce Upload | 3.1–3.4 | 2 files | Depends on Python backend import endpoint existing |
| 4. Known Issues | 4.1–4.4 | 3 files | No issues will be populated until Anika provides data |
| 5. Multi-Language | 5.1–5.4 | 3 files | English product names may differ (deferred) |
| 6. hreflang | 6.1–6.7 | 3 files + 1 migration + 1 doc | hreflang only works when publish_url is set |

# Peekaboo UI Layout Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the AI Visibility (media) tab to match the Peekaboo dashboard layout — brand summary strip, side-by-side visibility chart + competitors table, source types donut + top domains table, and recent chats grid.

**Architecture:** Two files change: (1) `dashboard/app/api/media-visibility/route.ts` — pass through additional fields from the Peekaboo API (competitor sentiment/position, source type/usedPct, chats data); (2) `styles/dashboard_template.html` — rewrite the media tab rendering functions to match Peekaboo's layout structure while keeping existing card/font/color styling.

**Tech Stack:** Vanilla JS (inline in HTML template), Chart.js (already loaded), Next.js API route (TypeScript)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `dashboard/app/api/media-visibility/route.ts` | Modify (lines 81-163) | Extract additional fields from Peekaboo API: competitor `sentiment`/`position`, source `type`/`usedPct`, and `chats` array from snapshot |
| `styles/dashboard_template.html` | Modify (lines 2704-2727, 3394-3417, 8292-8808) | Rewrite media tab: brand summary strip, competitors table, source types donut, top domains table, recent chats grid |

---

### Task 1: Update API transform to pass through additional Peekaboo fields

**Files:**
- Modify: `dashboard/app/api/media-visibility/route.ts:81-163`

The Peekaboo snapshot API returns more fields per competitor (sentiment, averagePosition/position) and per source (type, usedPct) than we currently extract. We also need to pass through the `chats` array and source type summary if present.

- [ ] **Step 1: Update competitor mapping in transform()**

In `dashboard/app/api/media-visibility/route.ts`, find the `competitors` mapping (lines 115-124) and add `sentiment`, `position`, and `isTracked` fields:

```typescript
    competitors: competitors.map((c: any) => {
      const extra = compExtras[c?.name] ?? {};
      return {
        name: c?.name ?? "",
        score: c?.score ?? 0,
        url: c?.url ?? "",
        change: extra?.change ?? c?.change ?? null,
        monthlyVisits: extra?.monthlyVisits ?? c?.monthlyVisits ?? null,
        sentiment: extra?.sentiment ?? c?.sentiment ?? null,
        position: extra?.averagePosition ?? extra?.position ?? c?.averagePosition ?? c?.position ?? null,
        isTracked: extra?.isTracked ?? c?.isTracked ?? false,
      };
    }),
```

- [ ] **Step 2: Update sources mapping to include type and usedPct**

Find the `sources` mapping (lines 145-149) and add `type` and `usedPct`:

```typescript
    sources: sources.map((s: any) => ({
      domain: s?.domain ?? "",
      mentions: s?.mentions ?? s?.citations ?? 0,
      usedPct: s?.usedPct ?? s?.used ?? null,
      type: s?.type ?? null,
      aiModels: s?.aiModels ?? [],
    })),
```

- [ ] **Step 3: Add chats array and sourceTypes summary to transform output**

Add these new top-level fields to the return object (after `traffic`):

```typescript
    chats: Array.isArray(snap?.chats ?? snap?.recentChats)
      ? (snap.chats ?? snap.recentChats).map((c: any) => ({
          id: c?.id ?? "",
          prompt: c?.prompt ?? c?.query ?? c?.promptText ?? "",
          answer: c?.answer ?? c?.snippet ?? c?.response ?? "",
          aiModel: c?.aiModel ?? c?.model ?? "",
          date: c?.date ?? c?.createdAt ?? "",
          mentioned: c?.mentioned ?? c?.brandMentioned ?? false,
          mentionCount: c?.mentionCount ?? c?.mentions ?? 0,
        }))
      : [],
    sourceTypes: snap?.sourceTypes ?? snap?.sourceSummary ?? null,
```

- [ ] **Step 4: Add brand overview fields for sentiment and position**

Update the `overview` object (lines 108-114) to include sentiment and avgPosition:

```typescript
    overview: {
      score: vis?.score ?? 0,
      rank: vis?.rank ?? 0,
      totalCitations: vis?.totalCitations ?? 0,
      totalChats: vis?.totalChatsAnalyzed ?? 0,
      trend: brandMeta?.trend ?? null,
      sentiment: vis?.sentiment ?? brandMeta?.sentiment ?? null,
      avgPosition: vis?.averagePosition ?? brandMeta?.averagePosition ?? vis?.avgPosition ?? null,
    },
```

- [ ] **Step 5: Verify the API still works**

Run: `cd dashboard && npm run dev`
Open: `http://localhost:3000/api/media-visibility`
Expected: JSON response with new fields (values may be null if Peekaboo doesn't return them — that's fine, frontend will handle gracefully)

---

### Task 2: Add new localization keys

**Files:**
- Modify: `styles/dashboard_template.html:2704-2727` (German strings)
- Modify: `styles/dashboard_template.html:3394-3417` (English strings)

- [ ] **Step 1: Add German localization keys**

After line 2727 (`media_no_history`), add:

```javascript
        media_visibility: 'Sichtbarkeit',
        media_sentiment: 'Stimmung',
        media_avg_position: 'Ø Position',
        media_all_models: 'Alle Modelle',
        media_last_7_days: 'Letzte 7 Tage',
        media_your_brand: 'Ihre Marke',
        media_brand: 'Marke',
        media_position: 'Position',
        media_top_sources: 'Top-Quellen',
        media_top_sources_subtitle: 'Quellen über aktive Modelle',
        media_source_types: 'Quellentypen',
        media_top_domains: 'Top Domains',
        media_domain_col: 'DOMAIN',
        media_used: 'GENUTZT',
        media_cites: 'ZITATE',
        media_type: 'TYP',
        media_recent_chats: 'Aktuelle Chats',
        media_brand_mentioned: 'Marke erwähnt',
        media_mentioned: 'Erwähnt',
        media_competitors_subtitle: 'Marken mit höchster Sichtbarkeit',
        media_visibility_subtitle: '% der KI-Chats, die Marke erwähnen',
        media_untracked: 'untracked',
        media_you: 'Sie',
```

- [ ] **Step 2: Add English localization keys**

After line 3417 (`media_no_history`), add the same keys in English:

```javascript
        media_visibility: 'Visibility',
        media_sentiment: 'Sentiment',
        media_avg_position: 'Avg Position',
        media_all_models: 'All Models',
        media_last_7_days: 'Last 7 days',
        media_your_brand: 'Your brand',
        media_brand: 'Brand',
        media_position: 'Position',
        media_top_sources: 'Top Sources',
        media_top_sources_subtitle: 'Sources across active models',
        media_source_types: 'Source Types',
        media_top_domains: 'Top Domains',
        media_domain_col: 'DOMAIN',
        media_used: 'USED',
        media_cites: 'CITES',
        media_type: 'TYPE',
        media_recent_chats: 'Recent Chats',
        media_brand_mentioned: 'Brand mentioned',
        media_mentioned: 'Mentioned',
        media_competitors_subtitle: 'Brands with highest visibility',
        media_visibility_subtitle: '% of AI chats mentioning brand',
        media_untracked: 'untracked',
        media_you: 'You',
```

---

### Task 3: Rewrite brand summary strip (replaces KPI cards)

**Files:**
- Modify: `styles/dashboard_template.html` — `renderMediaTabFromData()` function (line 8356)

The Peekaboo layout has a horizontal brand summary bar at the top showing: brand name + "Your brand" label, then Visibility %, Sentiment %, Avg Position as inline metrics, then filter dropdowns on the right.

- [ ] **Step 1: Replace the KPI cards section**

In `renderMediaTabFromData()`, replace the section header + KPI grid (lines 8369-8409) with:

```javascript
    // ── Brand summary strip ──
    const visPct = overview.score != null ? overview.score + '%' : '–';
    const sentPct = overview.sentiment != null ? overview.sentiment + '%' : '–';
    const avgPos = overview.avgPosition != null ? overview.avgPosition : '–';

    html += `<div class="section">
    <div class="card" style="margin-bottom:20px;">
        <div class="card-body" style="padding:16px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;">
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="width:40px;height:40px;border-radius:10px;background:#C60050;display:flex;align-items:center;justify-content:center;">
                    <span style="color:white;font-weight:700;font-size:18px;">b</span>
                </div>
                <div>
                    <div style="font-family:var(--font-display);font-weight:700;font-size:16px;">Beurer</div>
                    <div style="font-size:11px;color:var(--gray-400);">${t('media_your_brand')}</div>
                </div>
                <div style="display:flex;gap:24px;margin-left:24px;">
                    <div>
                        <span style="font-size:12px;color:var(--gray-500);">${t('media_visibility')}</span>
                        <span style="font-weight:700;margin-left:4px;">${visPct}</span>
                    </div>
                    <div>
                        <span style="font-size:12px;color:var(--gray-500);">${t('media_sentiment')}</span>
                        <span style="font-weight:700;margin-left:4px;">${sentPct}</span>
                    </div>
                    <div>
                        <span style="font-size:12px;color:var(--gray-500);">${t('media_avg_position')}</span>
                        <span style="font-weight:700;margin-left:4px;">${avgPos}</span>
                    </div>
                </div>
            </div>
            <div style="display:flex;gap:8px;">
                <div class="filter-btn" style="display:inline-flex;align-items:center;gap:4px;cursor:default;">${t('media_all_models')} &#9662;</div>
                <div class="filter-btn" style="display:inline-flex;align-items:center;gap:4px;cursor:default;">${t('media_last_7_days')} &#9662;</div>
            </div>
        </div>
    </div>`;
```

Note: The dropdowns are display-only for now (Peekaboo API doesn't support model/date filtering client-side). They match the visual layout.

---

### Task 4: Rewrite visibility chart + competitors as side-by-side layout

**Files:**
- Modify: `styles/dashboard_template.html` — `renderMediaTabFromData()` (replace lines 8411-8459)

Peekaboo layout: two-column grid — Visibility line chart on left, Competitors ranked table on right.

- [ ] **Step 1: Replace the chart + competitors section**

Replace the full-width trend chart card AND the 2-column grid (competitors bar chart + sources) with a single 2-column grid:

```javascript
    // ── 2-column: Visibility chart (left) + Competitors table (right) ──
    html += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">`;

    // Left: Visibility trend chart
    html += `<div class="card">
        <div class="card-header" style="display:flex;align-items:center;justify-content:space-between;">
            <div>
                <h3>${t('media_trend_title')}</h3>
                <p style="font-size:12px;color:var(--gray-400);">${t('media_visibility_subtitle')}</p>
            </div>
        </div>
        <div class="card-body" style="padding:12px 20px 16px;">
            <div id="mediaTrendChartWrap" style="height:320px;position:relative;">
                <div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--gray-400);font-size:13px;">
                    <div class="loading-spinner" style="margin-right:10px;"></div> ${t('media_loading')}
                </div>
            </div>
        </div>
    </div>`;

    // Right: Competitors ranked table
    html += `<div class="card">
        <div class="card-header" style="display:flex;align-items:center;justify-content:space-between;">
            <div>
                <h3>${t('media_competitors_title')}</h3>
                <p style="font-size:12px;color:var(--gray-400);">${t('media_competitors_subtitle')}</p>
            </div>
            <div id="mediaCompetitorPagination" style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--gray-400);"></div>
        </div>
        <div class="card-body no-pad" id="mediaCompetitorTableWrap"></div>
    </div>`;

    html += `</div>`; // close 2-col grid
```

- [ ] **Step 2: Replace `_initCompetitorChart()` with `renderMediaCompetitorTable()`**

Delete the entire `_initCompetitorChart()` function (lines 8517-8579) and replace with:

```javascript
function renderMediaCompetitorTable() {
    const wrap = document.getElementById('mediaCompetitorTableWrap');
    if (!wrap) return;
    const data = mediaVisibilityData;
    if (!data) return;

    const overview = data.overview || {};
    const competitors = data.competitors || [];

    // Build list: Beurer first (highlighted), then competitors sorted by score desc
    const beurer = { name: 'Beurer', score: overview.score, sentiment: overview.sentiment, position: overview.avgPosition, isBrand: true, isTracked: true };
    const allBrands = [beurer, ...competitors].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

    const PAGE_SIZE = 8;
    let currentPage = 0;
    const totalPages = Math.ceil(allBrands.length / PAGE_SIZE);

    function render() {
        const start = currentPage * PAGE_SIZE;
        const page = allBrands.slice(start, start + PAGE_SIZE);

        // Update pagination header
        const pagWrap = document.getElementById('mediaCompetitorPagination');
        if (pagWrap && totalPages > 1) {
            const rangeEnd = Math.min(start + PAGE_SIZE, allBrands.length);
            pagWrap.innerHTML = `
                <button class="filter-btn" style="padding:3px 8px;font-size:11px;" ${currentPage === 0 ? 'disabled style="opacity:0.3;padding:3px 8px;font-size:11px;"' : ''} onclick="document.getElementById('mediaCompetitorTableWrap').__prevPage()">&#8249;</button>
                <span>${start + 1}-${rangeEnd} of ${allBrands.length}</span>
                <button class="filter-btn" style="padding:3px 8px;font-size:11px;" ${currentPage >= totalPages - 1 ? 'disabled style="opacity:0.3;padding:3px 8px;font-size:11px;"' : ''} onclick="document.getElementById('mediaCompetitorTableWrap').__nextPage()">&#8250;</button>
            `;
        }

        // Table header
        let html = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="border-bottom:1px solid var(--gray-100);">
                <th style="padding:10px 12px;text-align:left;font-weight:600;width:30px;color:var(--gray-400);">#</th>
                <th style="padding:10px 12px;text-align:left;font-weight:600;">${t('media_brand')}</th>
                <th style="padding:10px 12px;text-align:right;font-weight:600;">${t('media_visibility')}</th>
                <th style="padding:10px 12px;text-align:right;font-weight:600;">${t('media_sentiment')}</th>
                <th style="padding:10px 12px;text-align:right;font-weight:600;">${t('media_position')}</th>
            </tr></thead><tbody>`;

        page.forEach((b, idx) => {
            const rank = start + idx + 1;
            const isBrand = b.isBrand || b.name === 'Beurer';
            const rowBg = isBrand ? 'background:rgba(198,0,80,0.04);' : '';
            const leftBorder = isBrand ? 'border-left:3px solid #C60050;' : 'border-left:3px solid transparent;';
            const badge = isBrand
                ? `<span style="font-size:10px;padding:1px 6px;border-radius:4px;background:#C60050;color:white;margin-left:6px;">${t('media_you')}</span>`
                : (b.isTracked === false ? `<span style="font-size:10px;padding:1px 6px;border-radius:4px;background:var(--gray-100);color:var(--gray-400);margin-left:6px;">${t('media_untracked')}</span>` : '');

            const visBar = b.score != null ? `<div style="display:inline-flex;align-items:center;gap:6px;">
                <div style="width:40px;height:6px;background:var(--gray-100);border-radius:3px;overflow:hidden;">
                    <div style="height:100%;width:${Math.min(100, b.score ?? 0)}%;background:${isBrand ? '#C60050' : 'var(--gray-400)'};border-radius:3px;"></div>
                </div>
                <span>${b.score}%</span>
            </div>` : '–';

            const sent = b.sentiment != null ? b.sentiment + '%' : '–';
            const pos = b.position != null ? b.position : '–';

            html += `<tr style="border-bottom:1px solid var(--gray-50);${rowBg}${leftBorder}">
                <td style="padding:10px 12px;color:var(--gray-400);font-size:12px;">${rank}</td>
                <td style="padding:10px 12px;font-weight:${isBrand ? '700' : '500'};">${esc(b.name)}${badge}</td>
                <td style="padding:10px 12px;text-align:right;">${visBar}</td>
                <td style="padding:10px 12px;text-align:right;">${sent}</td>
                <td style="padding:10px 12px;text-align:right;">${pos}</td>
            </tr>`;
        });

        html += `</tbody></table>`;
        wrap.innerHTML = html;
    }

    wrap.__prevPage = () => { currentPage = Math.max(0, currentPage - 1); render(); };
    wrap.__nextPage = () => { if (currentPage < totalPages - 1) { currentPage++; render(); } };
    render();
}
```

---

### Task 5: Rewrite Top Sources section (donut + domains table)

**Files:**
- Modify: `styles/dashboard_template.html` — `renderMediaTabFromData()` and `renderMediaSourceTable()`

Peekaboo has a "Top Sources" section header, then a 2-column grid: Source Types donut chart (left) showing total citations in center with type breakdown, and Top Domains table (right) with domain, used %, cites, type badge.

- [ ] **Step 1: Add the Top Sources 2-column layout in renderMediaTabFromData()**

After the visibility+competitors 2-column grid, add:

```javascript
    // ── Top Sources section ──
    if (sources.length > 0) {
        html += `<div style="margin-bottom:20px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="font-size:16px;">&#127760;</span>
                <div>
                    <span style="font-family:var(--font-display);font-weight:700;font-size:15px;">${t('media_top_sources')}</span>
                    <span style="font-size:12px;color:var(--gray-400);margin-left:8px;">${t('media_top_sources_subtitle')}</span>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                <div class="card">
                    <div class="card-header"><h3>${t('media_source_types')}</h3></div>
                    <div class="card-body" style="padding:20px;display:flex;align-items:center;justify-content:center;">
                        <div id="mediaSourceDonutWrap" style="width:220px;height:220px;position:relative;">
                            <canvas id="mediaSourceDonut"></canvas>
                        </div>
                        <div id="mediaSourceDonutLegend" style="margin-left:20px;"></div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header" style="display:flex;align-items:center;justify-content:space-between;">
                        <h3>${t('media_top_domains')}</h3>
                        <div id="mediaDomainPagination" style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--gray-400);"></div>
                    </div>
                    <div class="card-body no-pad" id="mediaSourceTableWrap" style="max-height:400px;overflow-y:auto;"></div>
                </div>
            </div>
        </div>`;
    }
```

- [ ] **Step 2: Add `_initSourceDonut()` function**

Add a new function after the `_initTrendChart()` function:

```javascript
function _initSourceDonut() {
    if (typeof Chart === 'undefined' || !mediaVisibilityData) return;
    _destroyChartById('mediaSourceDonut');

    const el = document.getElementById('mediaSourceDonut');
    if (!el) return;

    const sources = mediaVisibilityData.sources || [];
    const sourceTypes = mediaVisibilityData.sourceTypes || null;

    // Aggregate by type from source data, or use sourceTypes summary
    const typeCounts = {};
    if (sourceTypes && typeof sourceTypes === 'object') {
        Object.assign(typeCounts, sourceTypes);
    } else {
        sources.forEach(s => {
            const t = s.type || 'Other';
            typeCounts[t] = (typeCounts[t] || 0) + (s.mentions || 0);
        });
    }

    const typeLabels = Object.keys(typeCounts);
    const typeValues = typeLabels.map(l => typeCounts[l]);
    const totalCitations = typeValues.reduce((a, b) => a + b, 0);

    const typeColors = {
        'Corporate': '#E74C6F',
        'Articles': '#4A90D9',
        'Social': '#34C759',
        'Academic': '#10A37F',
        'Other': '#B0B0B8',
    };
    const colors = typeLabels.map(l => typeColors[l] || '#B0B0B8');

    const chart = new Chart(el, {
        type: 'doughnut',
        data: {
            labels: typeLabels,
            datasets: [{
                data: typeValues,
                backgroundColor: colors,
                borderWidth: 0,
                hoverOffset: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '65%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.label}: ${ctx.parsed} citations`
                    }
                }
            }
        },
        plugins: [{
            id: 'centerText',
            afterDraw(chart) {
                const { ctx, width, height } = chart;
                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.font = 'bold 28px system-ui';
                ctx.fillStyle = '#1a1a1a';
                ctx.fillText(totalCitations.toLocaleString(), width / 2, height / 2 - 8);
                ctx.font = '11px system-ui';
                ctx.fillStyle = '#C60050';
                ctx.fillText('CITATIONS', width / 2, height / 2 + 16);
                ctx.restore();
            }
        }]
    });
    chartInstances.push(chart);

    // Render legend
    const legendWrap = document.getElementById('mediaSourceDonutLegend');
    if (legendWrap) {
        legendWrap.innerHTML = typeLabels.map((l, i) => `
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${colors[i]};"></span>
                <span style="font-size:12px;color:var(--gray-600);">${l}</span>
            </div>
        `).join('');
    }
}
```

- [ ] **Step 3: Rewrite `renderMediaSourceTable()` to match Top Domains layout**

Replace the entire `renderMediaSourceTable()` function with:

```javascript
function renderMediaSourceTable() {
    const wrap = document.getElementById('mediaSourceTableWrap');
    if (!wrap) return;
    const sources = (mediaVisibilityData?.sources || []).sort((a, b) => (b.mentions || 0) - (a.mentions || 0));
    if (!sources.length) return;

    const PAGE_SIZE = 6;
    let currentPage = 0;
    const totalPages = Math.ceil(sources.length / PAGE_SIZE);

    const typeBadgeColors = {
        'Corporate': { bg: '#FDE8ED', color: '#C60050' },
        'Articles': { bg: '#E8F0FD', color: '#4A90D9' },
        'Social': { bg: '#E8FDE8', color: '#34C759' },
        'Academic': { bg: '#E8FDF5', color: '#10A37F' },
        'Other': { bg: 'var(--gray-100)', color: 'var(--gray-500)' },
    };

    function render() {
        const start = currentPage * PAGE_SIZE;
        const page = sources.slice(start, start + PAGE_SIZE);
        const rangeEnd = Math.min(start + PAGE_SIZE, sources.length);

        // Update pagination
        const pagWrap = document.getElementById('mediaDomainPagination');
        if (pagWrap && totalPages > 1) {
            pagWrap.innerHTML = `
                <button class="filter-btn" style="padding:3px 8px;font-size:11px;" ${currentPage === 0 ? 'disabled style="opacity:0.3;padding:3px 8px;font-size:11px;"' : ''} onclick="document.getElementById('mediaSourceTableWrap').__prevPage()">&#8249;</button>
                <span>${start + 1}-${rangeEnd} of ${sources.length}</span>
                <button class="filter-btn" style="padding:3px 8px;font-size:11px;" ${currentPage >= totalPages - 1 ? 'disabled style="opacity:0.3;padding:3px 8px;font-size:11px;"' : ''} onclick="document.getElementById('mediaSourceTableWrap').__nextPage()">&#8250;</button>
            `;
        }

        let html = `<table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="border-bottom:1px solid var(--gray-100);">
                <th style="padding:10px 16px;text-align:left;font-weight:600;font-size:11px;color:var(--gray-400);text-transform:uppercase;letter-spacing:0.5px;">${t('media_domain_col')}</th>
                <th style="padding:10px 12px;text-align:right;font-weight:600;font-size:11px;color:var(--gray-400);text-transform:uppercase;letter-spacing:0.5px;">${t('media_used')}</th>
                <th style="padding:10px 12px;text-align:right;font-weight:600;font-size:11px;color:var(--gray-400);text-transform:uppercase;letter-spacing:0.5px;">${t('media_cites')}</th>
                <th style="padding:10px 16px;text-align:right;font-weight:600;font-size:11px;color:var(--gray-400);text-transform:uppercase;letter-spacing:0.5px;">${t('media_type')}</th>
            </tr></thead><tbody>`;

        page.forEach(s => {
            const typeStyle = typeBadgeColors[s.type] || typeBadgeColors['Other'];
            const typeLabel = s.type || 'Other';
            const usedVal = s.usedPct != null ? s.usedPct + '%' : (s.mentions > 0 ? ((s.mentions / (mediaVisibilityData?.overview?.totalCitations || 1)) * 100).toFixed(1) + '%' : '–');

            html += `<tr style="border-bottom:1px solid var(--gray-50);">
                <td style="padding:10px 16px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <img src="https://www.google.com/s2/favicons?domain=${encodeURIComponent(s.domain)}&sz=16" width="16" height="16" style="border-radius:2px;" onerror="this.style.display='none'">
                        <span style="font-weight:500;">${esc(s.domain)}</span>
                    </div>
                </td>
                <td style="padding:10px 12px;text-align:right;">${usedVal}</td>
                <td style="padding:10px 12px;text-align:right;font-weight:600;">${s.mentions}</td>
                <td style="padding:10px 16px;text-align:right;">
                    <span style="font-size:11px;padding:2px 8px;border-radius:4px;background:${typeStyle.bg};color:${typeStyle.color};">${typeLabel}</span>
                </td>
            </tr>`;
        });

        html += `</tbody></table>`;
        wrap.innerHTML = html;
    }

    wrap.__prevPage = () => { currentPage = Math.max(0, currentPage - 1); render(); };
    wrap.__nextPage = () => { if (currentPage < totalPages - 1) { currentPage++; render(); } };
    render();
}
```

---

### Task 6: Replace Prompts table with Recent Chats grid

**Files:**
- Modify: `styles/dashboard_template.html` — `renderMediaTabFromData()` and `renderMediaPromptTable()`

Peekaboo shows "Recent Chats" as a 2-column grid of cards. Each card shows: AI model icon + name, date, "Mentioned (N)" badge, prompt text, and answer snippet. There's a "Brand mentioned" toggle and pagination.

- [ ] **Step 1: Replace prompts section HTML in renderMediaTabFromData()**

Replace the prompts table card (current code) with:

```javascript
    // ── Recent Chats ──
    const chats = data.chats || [];
    const hasChats = chats.length > 0;
    const hasPrompts = prompts.length > 0;

    if (hasChats || hasPrompts) {
        html += `<div class="card" style="margin-bottom:20px;">
            <div class="card-header" style="display:flex;align-items:center;justify-content:space-between;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:16px;">&#128172;</span>
                    <h3>${t('media_recent_chats')}</h3>
                    <span style="font-size:12px;color:var(--gray-400);">(${hasChats ? chats.length : prompts.length})</span>
                </div>
                <div style="display:flex;align-items:center;gap:12px;">
                    <label style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--gray-500);cursor:pointer;">
                        ${t('media_brand_mentioned')}
                        <input type="checkbox" id="mediaChatBrandFilter" onchange="renderMediaChats()" style="cursor:pointer;">
                    </label>
                    <div id="mediaChatPagination" style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--gray-400);"></div>
                </div>
            </div>
            <div class="card-body" id="mediaChatsWrap" style="padding:16px;"></div>
        </div>`;
    }
```

- [ ] **Step 2: Add `renderMediaChats()` function**

Replace the entire `renderMediaPromptTable()` function with `renderMediaChats()`:

```javascript
function renderMediaChats() {
    const wrap = document.getElementById('mediaChatsWrap');
    if (!wrap) return;
    const data = mediaVisibilityData;
    if (!data) return;

    const chats = data.chats || [];
    const prompts = data.prompts || [];
    const brandFilter = document.getElementById('mediaChatBrandFilter')?.checked || false;

    // Use chats if available, otherwise fall back to prompts formatted as chat cards
    let items;
    if (chats.length > 0) {
        items = brandFilter ? chats.filter(c => c.mentioned) : chats;
    } else {
        items = prompts.map(p => ({
            prompt: p.text,
            answer: '',
            aiModel: (p.aiModels || [])[0] || '',
            date: '',
            mentioned: true,
            mentionCount: p.mentions || p.score || 0,
        }));
        if (brandFilter) items = items.filter(c => c.mentioned);
    }

    const PAGE_SIZE = 10;
    let currentPage = parseInt(wrap.dataset.page || '0', 10);
    const totalPages = Math.ceil(items.length / PAGE_SIZE);
    if (currentPage >= totalPages) currentPage = 0;
    const start = currentPage * PAGE_SIZE;
    const page = items.slice(start, start + PAGE_SIZE);
    const rangeEnd = Math.min(start + PAGE_SIZE, items.length);

    // Pagination
    const pagWrap = document.getElementById('mediaChatPagination');
    if (pagWrap && totalPages > 1) {
        pagWrap.innerHTML = `
            <button class="filter-btn" style="padding:3px 8px;font-size:11px;" ${currentPage === 0 ? 'disabled style="opacity:0.3;padding:3px 8px;font-size:11px;"' : ''} onclick="document.getElementById('mediaChatsWrap').dataset.page=${currentPage - 1};renderMediaChats()">&#8249;</button>
            <span>${start + 1}-${rangeEnd} of ${items.length}</span>
            <button class="filter-btn" style="padding:3px 8px;font-size:11px;" ${currentPage >= totalPages - 1 ? 'disabled style="opacity:0.3;padding:3px 8px;font-size:11px;"' : ''} onclick="document.getElementById('mediaChatsWrap').dataset.page=${currentPage + 1};renderMediaChats()">&#8250;</button>
        `;
    } else if (pagWrap) {
        pagWrap.innerHTML = '';
    }

    // Render 2-column grid of chat cards
    let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">`;
    page.forEach(c => {
        const model = c.aiModel || '';
        const color = AI_MODEL_COLORS[model] || '#8E8E93';
        const dateStr = c.date ? formatDate(typeof c.date === 'string' ? c.date.split('T')[0] : c.date) : '';
        const mentionBadge = c.mentionCount > 0
            ? `<span style="font-size:11px;padding:1px 8px;border-radius:4px;background:#34C75920;color:#34C759;font-weight:600;">${t('media_mentioned')} (${c.mentionCount})</span>`
            : '';

        html += `<div style="border:1px solid var(--gray-100);border-radius:10px;padding:14px 16px;background:var(--pure-white);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                ${aiModelDot(model)}
                <span style="font-size:12px;font-weight:600;color:var(--gray-700);">${esc(model)}</span>
                ${dateStr ? `<span style="font-size:11px;color:var(--gray-400);margin-left:auto;">${dateStr}</span>` : ''}
                ${mentionBadge ? `<span style="margin-left:${dateStr ? '8px' : 'auto'};">${mentionBadge}</span>` : ''}
            </div>
            <div style="font-size:13px;font-weight:600;line-height:1.4;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${esc(c.prompt)}</div>
            ${c.answer ? `<div style="font-size:12px;color:var(--gray-500);line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${esc(c.answer)}</div>` : ''}
        </div>`;
    });
    html += `</div>`;

    wrap.innerHTML = html;
}
```

---

### Task 7: Wire up initialization calls and remove dead code

**Files:**
- Modify: `styles/dashboard_template.html` — bottom of `renderMediaTabFromData()` + cleanup

- [ ] **Step 1: Update the initialization block at bottom of renderMediaTabFromData()**

Replace the current init block (lines 8488-8514) with:

```javascript
    html += `</div>`; // close section

    document.getElementById('tab-media').innerHTML = html;

    // Initialize components
    renderMediaCompetitorTable();
    if (sources.length > 0) {
        renderMediaSourceTable();
        setTimeout(() => _initSourceDonut(), 50);
    }
    renderMediaChats();

    // Fetch trend history and render chart
    fetch('/api/media-visibility?history=true')
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            const wrap = document.getElementById('mediaTrendChartWrap');
            if (!wrap) return;
            const history = data?.history || [];
            if (history.length < 2) {
                wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--gray-400);font-size:13px;">${t('media_no_history')}</div>`;
                return;
            }
            wrap.innerHTML = `<canvas id="mediaTrendChart"></canvas>`;
            _initTrendChart(history);
        })
        .catch(() => {
            const wrap = document.getElementById('mediaTrendChartWrap');
            if (wrap) wrap.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--gray-400);font-size:13px;">${t('media_no_history')}</div>`;
        });
```

- [ ] **Step 2: Remove dead code**

Delete these now-unused functions and variables:
- `sortMediaPrompts()` function (line 8654)
- `goMediaPromptPage()` function (line 8661)
- `sortMediaSources()` function (line 8733)
- `goMediaPage()` function (line 8740)
- `mediaSourcePage` variable (line 8294)
- `MEDIA_PAGE_SIZE` variable (line 8295)
- `mediaSortCol` / `mediaSortAsc` variables (lines 8296-8297)
- `mediaPromptPage` / `MEDIA_PROMPT_PAGE_SIZE` / `mediaPromptSortCol` / `mediaPromptSortAsc` variables (lines 8298-8301)

Keep only:
```javascript
let mediaVisibilityData = null;
```

- [ ] **Step 3: Keep the suggestions section unchanged**

The AI Suggestions grid at the bottom stays as-is (it's already clean and not in the Peekaboo screenshot, but provides value).

- [ ] **Step 4: Verify end-to-end**

Run: `cd dashboard && npm run dev`
Open the dashboard → AI Visibility tab
Expected layout (top to bottom):
1. Brand summary strip: Beurer logo, Visibility %, Sentiment %, Avg Position, filter pills
2. Two columns: Visibility line chart (left) | Competitors ranked table (right)
3. Top Sources header, then two columns: Source Types donut (left) | Top Domains table (right)
4. Recent Chats: 2-column grid of chat cards with model icon, date, mention badge, prompt, answer
5. AI Suggestions (unchanged)

---

### Task 8: Commit

- [ ] **Step 1: Commit all changes**

```bash
git add dashboard/app/api/media-visibility/route.ts styles/dashboard_template.html
git commit -m "feat: restructure AI visibility tab to match Peekaboo dashboard layout

- Replace KPI cards with brand summary strip (visibility %, sentiment, avg position)
- Replace competitor bar chart with ranked table (#, brand, visibility, sentiment, position)
- Add source types donut chart alongside top domains table with type badges
- Replace prompts table with Recent Chats 2-column card grid
- Pass through additional Peekaboo API fields (competitor sentiment/position, source types)
- Add German/English localization keys for new UI elements"
```

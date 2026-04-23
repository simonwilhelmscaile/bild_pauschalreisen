# Article Change Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show users what changed when articles are regenerated with feedback or edited inline — via diff overlay modals and iframe highlights.

**Architecture:** Backend stores old article HTML in `feedback_history` entries and persists inline edit `changes` arrays. Frontend renders a word-level diff algorithm, two overlay modal variants (side-by-side for regeneration, unified for inline edits), and injects highlight scripts into the article iframe via `postMessage`.

**Tech Stack:** Python (FastAPI), vanilla JS in HTML template, no external diff library.

**Spec:** `docs/superpowers/specs/2026-03-30-article-change-visibility-design.md`

---

### Task 1: Backend — Snapshot old HTML in regeneration history

**Files:**
- Modify: `blog/article_service.py:620-636`

- [ ] **Step 1: Capture old HTML before regeneration starts**

In `regenerate_article()`, capture the existing article HTML before the pipeline runs, and include it plus a `type` field in the feedback history entry. Edit lines 623-636:

```python
        # Update feedback history
        history: List[Dict] = article.get("feedback_history") or []
        old_article_html = article.get("article_html") or ""
        if feedback:
            history.append({
                "type": "feedback",
                "comment": feedback,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": len(history) + 1,
                "old_article_html": old_article_html,
            })

        # Set status to regenerating + save feedback history
        supabase.table("blog_articles").update({
            "status": "regenerating",
            "feedback_history": history,
        }).eq("id", article_id).execute()
```

The key changes from the original:
- Added `old_article_html = article.get("article_html") or ""` to capture the snapshot
- Added `"type": "feedback"` to the history entry (was missing — needed to distinguish from inline edits)
- Added `"old_article_html": old_article_html` to the history entry

- [ ] **Step 2: Verify by reading the updated code**

Read `blog/article_service.py` lines 620-640 to confirm the edit applied correctly. The history entry should now have `type`, `comment`, `created_at`, `version`, and `old_article_html`.

- [ ] **Step 3: Commit**

```bash
git add blog/article_service.py
git commit -m "feat: snapshot old article HTML in regeneration feedback history"
```

---

### Task 2: Backend — Persist changes array in inline edit history

**Files:**
- Modify: `blog/article_service.py:1025-1031`

- [ ] **Step 1: Add changes array to the inline edit feedback history entry**

In `apply_inline_edits()`, add the `changes` list to the history entry at line 1025:

```python
    history.append({
        "type": "inline_edit",
        "comment": f"Inline edits ({len(resolved)}): " + "; ".join(edit_summary_parts),
        "edits_applied": edits_applied,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": len(history) + 1,
        "changes": changes,
    })
```

The only change from the original is adding `"changes": changes` to the dict. The `changes` variable is already computed earlier in the function (line 992) — it's just not being persisted.

- [ ] **Step 2: Verify by reading the updated code**

Read `blog/article_service.py` lines 1019-1035 to confirm the `changes` key is present in the history entry.

- [ ] **Step 3: Commit**

```bash
git add blog/article_service.py
git commit -m "feat: persist inline edit changes array in feedback history"
```

---

### Task 3: Frontend — i18n keys

**Files:**
- Modify: `styles/dashboard_template.html:2302-2323` (DE block)
- Modify: `styles/dashboard_template.html:2974-2995` (EN block)

- [ ] **Step 1: Add German translation keys**

Find the DE translation block near line 2323 (after `edits_failed`). Add these keys immediately after the `edits_failed` line:

```javascript
        view_changes: 'Änderungen anzeigen',
        previous_version: 'Vorherige Version',
        current_version: 'Aktuelle Version',
        clear_highlights: 'Markierungen entfernen',
        changes_count: 'Änderungen',
        new_section: 'Neu',
        side_by_side: 'Seite an Seite',
        edits_count: 'Bearbeitungen',
```

- [ ] **Step 2: Add English translation keys**

Find the EN translation block near line 2995 (after `edits_failed`). Add these keys immediately after:

```javascript
        view_changes: 'View changes',
        previous_version: 'Previous Version',
        current_version: 'Current Version',
        clear_highlights: 'Clear highlights',
        changes_count: 'changes',
        new_section: 'New',
        side_by_side: 'Side-by-side',
        edits_count: 'edits',
```

- [ ] **Step 3: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add i18n keys for article change visibility"
```

---

### Task 4: Frontend — CSS for diff overlay and iframe highlights

**Files:**
- Modify: `styles/dashboard_template.html:1481` (after `.feedback-card-body` rule)

- [ ] **Step 1: Add CSS rules**

Insert the following CSS immediately after the `.feedback-card-body` rule (line 1481):

```css
        .feedback-card-actions { padding: 6px 12px 10px; }
        .feedback-view-changes-btn {
            background: none; border: 1px solid #d1d5db; border-radius: 6px;
            padding: 3px 10px; font-size: 11px; color: #374151; cursor: pointer;
            display: inline-flex; align-items: center; gap: 4px;
            transition: background .15s;
        }
        .feedback-view-changes-btn:hover { background: #f3f4f6; }
        .feedback-view-changes-btn .badge {
            background: #e5e7eb; color: #6b7280; padding: 1px 6px;
            border-radius: 999px; font-size: 9px; font-weight: 600;
        }

        /* Diff overlay */
        .diff-overlay {
            position: fixed; inset: 0; background: rgba(0,0,0,.6);
            z-index: 10001; display: flex; align-items: center; justify-content: center;
            animation: statusFadeIn 0.2s ease;
        }
        .diff-modal {
            background: #fff; border-radius: 12px; overflow: hidden;
            display: flex; flex-direction: column; box-shadow: 0 25px 60px rgba(0,0,0,.3);
        }
        .diff-modal.side-by-side {
            width: 96vw; height: 94vh;
        }
        .diff-modal.unified {
            width: 700px; max-height: 80vh;
        }
        .diff-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 16px 20px; border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
        }
        .diff-header h3 { margin: 0; font-size: 16px; color: #111827; }
        .diff-header .diff-comment {
            font-size: 12px; color: #6b7280; margin-top: 4px; max-width: 80%;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .diff-close-btn {
            background: none; border: none; font-size: 24px; cursor: pointer;
            color: #6b7280; padding: 4px 8px; line-height: 1;
        }
        .diff-close-btn:hover { color: #111827; }
        .diff-panels {
            display: flex; flex: 1; overflow: hidden;
        }
        .diff-panel {
            flex: 1; overflow-y: auto; padding: 20px;
            font-size: 14px; line-height: 1.7; color: #374151;
        }
        .diff-panel + .diff-panel { border-left: 1px solid #e5e7eb; }
        .diff-panel-label {
            font-size: 11px; font-weight: 700; text-transform: uppercase;
            letter-spacing: .05em; color: #6b7280; margin-bottom: 12px;
        }
        .diff-word-add { background: #dcfce7; border-radius: 2px; padding: 0 1px; }
        .diff-word-remove { background: #fee2e2; text-decoration: line-through; border-radius: 2px; padding: 0 1px; }

        /* Unified diff (inline edits) */
        .diff-unified-body { padding: 16px 20px; overflow-y: auto; flex: 1; }
        .diff-edit-card {
            border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 12px;
            overflow: hidden;
        }
        .diff-edit-card-header {
            padding: 8px 12px; background: #f9fafb; border-bottom: 1px solid #e5e7eb;
            font-size: 12px; color: #6b7280;
        }
        .diff-edit-card-body {
            padding: 12px; font-size: 13px; line-height: 1.6; color: #374151;
        }
```

- [ ] **Step 2: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add CSS for diff overlay modal and iframe highlights"
```

---

### Task 5: Frontend — Word diff algorithm

**Files:**
- Modify: `styles/dashboard_template.html` (insert before `buildFeedbackCardHTML` function at line 7042)

- [ ] **Step 1: Add `stripHtmlTags` and `computeWordDiff` functions**

Insert immediately before the `function buildFeedbackCardHTML(fb, index)` line:

```javascript
/* ── DIFF UTILITIES ── */
function stripHtmlTags(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return (tmp.textContent || tmp.innerText || '').replace(/\s+/g, ' ').trim();
}

function computeWordDiff(oldText, newText) {
    const oldWords = oldText.split(/\s+/).filter(Boolean);
    const newWords = newText.split(/\s+/).filter(Boolean);
    const m = oldWords.length, n = newWords.length;

    // LCS table (space-optimized with two rows)
    const prev = new Array(n + 1).fill(0);
    const curr = new Array(n + 1).fill(0);
    // Full table needed for backtracking
    const dp = [];
    for (let i = 0; i <= m; i++) {
        dp[i] = new Array(n + 1).fill(0);
    }
    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (oldWords[i - 1] === newWords[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    // Backtrack to build diff
    const result = [];
    let i = m, j = n;
    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && oldWords[i - 1] === newWords[j - 1]) {
            result.unshift({ type: 'equal', text: oldWords[i - 1] });
            i--; j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            result.unshift({ type: 'add', text: newWords[j - 1] });
            j--;
        } else {
            result.unshift({ type: 'remove', text: oldWords[i - 1] });
            i--;
        }
    }
    return result;
}

function renderDiffHtml(diffSegments, side) {
    // side: 'old' (show removes, hide adds), 'new' (show adds, hide removes), 'unified' (show both)
    return diffSegments.map(seg => {
        if (seg.type === 'equal') return esc(seg.text);
        if (seg.type === 'remove' && (side === 'old' || side === 'unified'))
            return '<span class="diff-word-remove">' + esc(seg.text) + '</span>';
        if (seg.type === 'add' && (side === 'new' || side === 'unified'))
            return '<span class="diff-word-add">' + esc(seg.text) + '</span>';
        return '';
    }).filter(Boolean).join(' ');
}

```

- [ ] **Step 2: Verify the functions are syntactically correct**

Read the inserted code region to confirm no syntax issues. The `esc()` function already exists in the template (used throughout for HTML escaping).

- [ ] **Step 3: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add word-level diff algorithm for article change visibility"
```

---

### Task 6: Frontend — Diff overlay modal (`showDiffOverlay`)

**Files:**
- Modify: `styles/dashboard_template.html` (insert after the `renderDiffHtml` function from Task 5)

- [ ] **Step 1: Add `showDiffOverlay` function**

Insert after the `renderDiffHtml` function (before `buildFeedbackCardHTML`):

```javascript
function showDiffOverlay(fb, currentHtml) {
    // Remove existing diff overlay
    const existing = document.getElementById('diff-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'diff-overlay';
    overlay.className = 'diff-overlay';

    if (fb.type === 'inline_edit' && fb.changes && fb.changes.length > 0) {
        // Unified view for inline edits
        const editCards = fb.changes.map((ch, i) => {
            const oldText = stripHtmlTags(ch.original_snippet || '');
            const newText = stripHtmlTags(ch.revised_snippet || '');
            const diff = computeWordDiff(oldText, newText);
            const unifiedHtml = renderDiffHtml(diff, 'unified');
            return `<div class="diff-edit-card">
                <div class="diff-edit-card-header">Edit ${ch.edit_number || (i + 1)}</div>
                <div class="diff-edit-card-body">${unifiedHtml}</div>
            </div>`;
        }).join('');

        overlay.innerHTML = `
            <div class="diff-modal unified">
                <div class="diff-header">
                    <div>
                        <h3>${t('view_changes')}</h3>
                        <div class="diff-comment">${fb.edits_applied || fb.changes.length} ${t('edits_count')}</div>
                    </div>
                    <button class="diff-close-btn" onclick="document.getElementById('diff-overlay').remove()">&times;</button>
                </div>
                <div class="diff-unified-body">${editCards}</div>
            </div>`;
    } else if (fb.old_article_html) {
        // Side-by-side view for full regeneration
        const oldText = stripHtmlTags(fb.old_article_html);
        const newText = stripHtmlTags(currentHtml);
        const diff = computeWordDiff(oldText, newText);
        const oldHtml = renderDiffHtml(diff, 'old');
        const newHtml = renderDiffHtml(diff, 'new');

        overlay.innerHTML = `
            <div class="diff-modal side-by-side">
                <div class="diff-header">
                    <div>
                        <h3>${t('view_changes')}</h3>
                        <div class="diff-comment">${esc(fb.comment || '').substring(0, 200)}</div>
                    </div>
                    <button class="diff-close-btn" onclick="document.getElementById('diff-overlay').remove()">&times;</button>
                </div>
                <div class="diff-panels">
                    <div class="diff-panel" id="diff-panel-old">
                        <div class="diff-panel-label">${t('previous_version')}</div>
                        <div>${oldHtml}</div>
                    </div>
                    <div class="diff-panel" id="diff-panel-new">
                        <div class="diff-panel-label">${t('current_version')}</div>
                        <div>${newHtml}</div>
                    </div>
                </div>
            </div>`;
    }

    document.body.appendChild(overlay);

    // Close on backdrop click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });

    // Scroll sync for side-by-side panels
    const oldPanel = document.getElementById('diff-panel-old');
    const newPanel = document.getElementById('diff-panel-new');
    if (oldPanel && newPanel) {
        let syncing = false;
        oldPanel.addEventListener('scroll', () => {
            if (syncing) return;
            syncing = true;
            newPanel.scrollTop = oldPanel.scrollTop;
            syncing = false;
        });
        newPanel.addEventListener('scroll', () => {
            if (syncing) return;
            syncing = true;
            oldPanel.scrollTop = newPanel.scrollTop;
            syncing = false;
        });
    }
}

```

- [ ] **Step 2: Verify the function is inserted correctly**

Read the region to confirm `showDiffOverlay` is defined between `renderDiffHtml` and `buildFeedbackCardHTML`.

- [ ] **Step 3: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add diff overlay modal for article change visibility"
```

---

### Task 7: Frontend — Update `buildFeedbackCardHTML` with "View changes" button

**Files:**
- Modify: `styles/dashboard_template.html:7042-7052`

- [ ] **Step 1: Replace the `buildFeedbackCardHTML` function**

Replace the existing function (lines 7042-7052) with:

```javascript
function buildFeedbackCardHTML(fb, index) {
    const date = fb.created_at ? new Date(fb.created_at).toLocaleString() : '';
    const version = fb.version || (index + 1);
    const hasRegenDiff = fb.type === 'feedback' && fb.old_article_html;
    const hasInlineDiff = fb.type === 'inline_edit' && fb.changes && fb.changes.length > 0;
    const showChangesBtn = hasRegenDiff || hasInlineDiff;

    let badgeText = '';
    if (hasRegenDiff) badgeText = t('side_by_side');
    else if (hasInlineDiff) badgeText = fb.changes.length + ' ' + t('edits_count');

    return `<div class="feedback-card">
        <div class="feedback-card-header">
            <span class="version-badge">${t('feedback_version')} ${version}</span>
            <span>${date}</span>
        </div>
        <div class="feedback-card-body">${esc(fb.comment || '')}</div>
        ${showChangesBtn ? `<div class="feedback-card-actions">
            <button class="feedback-view-changes-btn" onclick="showDiffOverlay(_feedbackEntries[${index}], _currentArticleHtml)">
                ${t('view_changes')}
                <span class="badge">${badgeText}</span>
            </button>
        </div>` : ''}
    </div>`;
}
```

- [ ] **Step 2: Add state variables for feedback entries and current HTML**

The `buildFeedbackCardHTML` now references `_feedbackEntries` and `_currentArticleHtml`. These need to be set when the modal opens. Insert right before the `/* ── FEEDBACK DRAFT PERSISTENCE ── */` comment (around line 7054):

```javascript
let _feedbackEntries = [];
let _currentArticleHtml = '';
```

- [ ] **Step 3: Populate state variables when modal opens**

In the `openArticleModal` function, after `const feedbackHistory = article.feedback_history || [];` (line 6783), add:

```javascript
        _feedbackEntries = feedbackHistory;
        _currentArticleHtml = article.article_html || '';
```

- [ ] **Step 4: Update state after regeneration completes**

In the `handleRegenerate` polling success block (around line 7358-7365), after the feedback history list is refreshed, update the state variables. Find the block that updates `historyList.innerHTML` and add after `historyList.scrollTop = historyList.scrollHeight;`:

```javascript
                                _feedbackEntries = history;
                                _currentArticleHtml = article.article_html || '';
```

- [ ] **Step 5: Update state after inline edits applied**

In `handleApplyEdits`, after the feedback history refresh block (around line 7444-7450), add after `historyList.scrollTop = historyList.scrollHeight;`:

```javascript
            _feedbackEntries = data.feedback_history;
            _currentArticleHtml = data.article_html || '';
```

- [ ] **Step 6: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: add View changes button to feedback history cards"
```

---

### Task 8: Frontend — Iframe highlight injection

**Files:**
- Modify: `styles/dashboard_template.html`

This task adds a helper that wraps `iframe.srcdoc` with a highlight script+style, and functions to send highlight/clear messages to the iframe.

- [ ] **Step 1: Add iframe highlight helper functions**

Insert before the `/* ── DIFF UTILITIES ── */` comment (added in Task 5):

```javascript
/* ── IFRAME HIGHLIGHT INJECTION ── */
function injectHighlightSupport(html) {
    if (!html || html.includes('__highlight_injected__')) return html;
    const highlightStyle = `<style id="__highlight_injected__">
        .change-highlight { background: #bbf7d0; border-radius: 2px; padding: 0 1px; }
        .section-changed { border-left: 3px solid #22c55e; padding-left: 8px; transition: border-color .3s; }
        .section-new-badge {
            display: inline-block; background: #22c55e; color: #fff; font-size: 10px;
            font-weight: 700; padding: 1px 6px; border-radius: 4px; margin-left: 8px;
            vertical-align: middle;
        }
        .clear-highlights-btn {
            position: fixed; top: 12px; right: 12px; z-index: 9999;
            background: #fff; border: 1px solid #d1d5db; border-radius: 999px;
            padding: 6px 14px; font-size: 12px; font-weight: 600; color: #374151;
            cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.1);
            display: none; animation: statusFadeIn 0.3s ease;
        }
        .clear-highlights-btn:hover { background: #f3f4f6; }
        @keyframes statusFadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
    </style>`;
    const highlightScript = `<script>
        (function() {
            var clearBtn = document.createElement('button');
            clearBtn.className = 'clear-highlights-btn';
            clearBtn.textContent = '${t("clear_highlights")}';
            clearBtn.onclick = function() { clearAllHighlights(); };
            document.body.appendChild(clearBtn);

            function showClearBtn() { clearBtn.style.display = 'block'; }

            function clearAllHighlights() {
                document.querySelectorAll('.change-highlight').forEach(function(el) {
                    el.replaceWith(document.createTextNode(el.textContent));
                });
                document.querySelectorAll('.section-changed').forEach(function(el) {
                    el.classList.remove('section-changed');
                });
                document.querySelectorAll('.section-new-badge').forEach(function(el) {
                    el.remove();
                });
                clearBtn.style.display = 'none';
            }

            window.addEventListener('message', function(e) {
                var d = e.data;
                if (!d || !d.type) return;

                if (d.type === 'highlight-changes' && d.changes) {
                    d.changes.forEach(function(ch) {
                        if (!ch.revised_snippet) return;
                        var snippet = ch.revised_snippet;
                        // Walk text nodes to find and wrap the snippet
                        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                        var node;
                        while (node = walker.nextNode()) {
                            var idx = node.textContent.indexOf(snippet.replace(/<[^>]*>/g, '').substring(0, 60));
                            if (idx !== -1) {
                                var mark = document.createElement('mark');
                                mark.className = 'change-highlight';
                                var range = document.createRange();
                                range.setStart(node, idx);
                                range.setEnd(node, Math.min(idx + node.textContent.length - idx, node.textContent.length));
                                range.surroundContents(mark);
                                break;
                            }
                        }
                    });
                    if (d.changes.length > 0) showClearBtn();
                }

                if (d.type === 'highlight-sections' && d.changedHeadings) {
                    var headings = document.querySelectorAll('h2');
                    headings.forEach(function(h2) {
                        var text = h2.textContent.trim();
                        var match = d.changedHeadings.find(function(ch) { return ch.heading === text; });
                        if (match) {
                            // Find the section container (next siblings until next h2)
                            var el = h2;
                            h2.parentElement && h2.parentElement.classList ? h2.parentElement.classList.add('section-changed') : h2.classList.add('section-changed');
                            if (match.isNew) {
                                var badge = document.createElement('span');
                                badge.className = 'section-new-badge';
                                badge.textContent = match.newLabel || 'New';
                                h2.appendChild(badge);
                            }
                        }
                    });
                    if (d.changedHeadings.length > 0) showClearBtn();
                }

                if (d.type === 'clear-highlights') {
                    clearAllHighlights();
                }
            });
        })();
    <\\/script>`;
    // Inject before </head> or at start of HTML
    if (html.includes('</head>')) {
        return html.replace('</head>', highlightStyle + '</head>').replace('</body>', highlightScript + '</body>');
    }
    return highlightStyle + highlightScript + html;
}

function sendHighlightMessage(iframe, messageData) {
    if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage(messageData, '*');
    }
}

function computeChangedSections(oldHtml, newHtml) {
    // Extract H2 headings and their following text content from both versions
    const extractSections = (html) => {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        const sections = {};
        const h2s = tmp.querySelectorAll('h2');
        h2s.forEach(h2 => {
            const heading = h2.textContent.trim();
            let text = '';
            let el = h2.nextElementSibling;
            while (el && el.tagName !== 'H2') {
                text += (el.textContent || '') + ' ';
                el = el.nextElementSibling;
            }
            sections[heading] = text.trim().substring(0, 500);
        });
        return sections;
    };
    const oldSections = extractSections(oldHtml);
    const newSections = extractSections(newHtml);
    const changed = [];
    for (const [heading, text] of Object.entries(newSections)) {
        if (!(heading in oldSections)) {
            changed.push({ heading, isNew: true, newLabel: t('new_section') });
        } else if (oldSections[heading] !== text) {
            changed.push({ heading, isNew: false });
        }
    }
    return changed;
}

```

- [ ] **Step 2: Inject highlight support when setting iframe srcdoc**

Find all places where `iframe.srcdoc` is set to article HTML and wrap with `injectHighlightSupport()`. There are 4 locations:

**Location 1** — `openArticleModal` (line 6999): Change:
```javascript
                iframe.srcdoc = html;
```
to:
```javascript
                iframe.srcdoc = injectHighlightSupport(html);
```

**Location 2** — content planning article preview (line 6666): Change:
```javascript
            iframe.srcdoc = data.article_html;
```
to:
```javascript
            iframe.srcdoc = injectHighlightSupport(data.article_html);
```

**Location 3** — `handleRegenerate` polling success (line 7337): Change:
```javascript
                            if (iframe && article.article_html) iframe.srcdoc = article.article_html;
```
to:
```javascript
                            if (iframe && article.article_html) iframe.srcdoc = injectHighlightSupport(article.article_html);
```

**Location 4** — `handleApplyEdits` success (line 7438): Change:
```javascript
            if (iframe) iframe.srcdoc = data.article_html;
```
to:
```javascript
            if (iframe) iframe.srcdoc = injectHighlightSupport(data.article_html);
```

- [ ] **Step 3: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: inject highlight support script into article iframe"
```

---

### Task 9: Frontend — Send highlight messages after edits/regeneration

**Files:**
- Modify: `styles/dashboard_template.html`

- [ ] **Step 1: Send highlight message after inline edits**

In `handleApplyEdits`, after the iframe srcdoc is updated (after the `injectHighlightSupport` line from Task 8, Location 4), add a small delay to let the iframe load, then send the highlight message. Find the block around line 7438 and after the srcdoc assignment add:

```javascript
            // Highlight changes in iframe after load
            if (iframe && data.changes && data.changes.length > 0) {
                iframe.addEventListener('load', function onLoad() {
                    iframe.removeEventListener('load', onLoad);
                    sendHighlightMessage(iframe, { type: 'highlight-changes', changes: data.changes });
                });
            }
```

- [ ] **Step 2: Send highlight message after full regeneration**

In `handleRegenerate` polling success, after the iframe srcdoc is updated (after the `injectHighlightSupport` line from Task 8, Location 3), add section-level highlights. Find the block and after `iframe.srcdoc = injectHighlightSupport(article.article_html);` add:

```javascript
                            // Highlight changed sections
                            const lastFb = (article.feedback_history || []).slice(-1)[0];
                            if (lastFb && lastFb.old_article_html) {
                                iframe.addEventListener('load', function onLoad() {
                                    iframe.removeEventListener('load', onLoad);
                                    const changedHeadings = computeChangedSections(lastFb.old_article_html, article.article_html);
                                    sendHighlightMessage(iframe, { type: 'highlight-sections', changedHeadings });
                                });
                            }
```

- [ ] **Step 3: Commit**

```bash
git add styles/dashboard_template.html
git commit -m "feat: send highlight messages to iframe after edits and regeneration"
```

---

### Task 10: Sync dashboard template copy

**Files:**
- Modify: `dashboard/template/dashboard_template.html`

- [ ] **Step 1: Copy the styles template to the dashboard template**

The dashboard template at `dashboard/template/dashboard_template.html` is a synced copy of `styles/dashboard_template.html`. Copy it:

```bash
cp styles/dashboard_template.html dashboard/template/dashboard_template.html
```

- [ ] **Step 2: Verify the copy is identical**

```bash
diff styles/dashboard_template.html dashboard/template/dashboard_template.html
```

Expected: no output (files are identical).

- [ ] **Step 3: Commit**

```bash
git add dashboard/template/dashboard_template.html
git commit -m "chore: sync dashboard template copy with styles source"
```

---

### Task 11: Manual smoke test

No code changes. Verify the feature end-to-end.

- [ ] **Step 1: Start the backend**

```bash
python dev.py
```

- [ ] **Step 2: Start the dashboard**

```bash
cd dashboard && npm run dev
```

- [ ] **Step 3: Test inline edit change visibility**

1. Open an article in the modal
2. Select a passage, add an inline comment, click "Apply Edits"
3. Verify: green highlights appear on changed text in the iframe
4. Verify: "Clear highlights" button appears in the iframe, clicking it removes highlights
5. Verify: feedback history card shows "View changes" button with unified diff badge
6. Click "View changes" — verify unified diff modal opens with red/green word-level diff

- [ ] **Step 4: Test regeneration change visibility**

1. Type feedback in the textarea, click "Regenerate with Feedback"
2. Wait for regeneration to complete
3. Verify: section-level green left-border highlights appear on changed sections
4. Verify: feedback history card shows "View changes" button with "Side-by-side" badge
5. Click "View changes" — verify side-by-side diff modal opens with scroll-synced panels
6. Verify: old version on left has red highlights, new version on right has green highlights

- [ ] **Step 5: Test edge cases**

1. Verify old feedback cards (before this feature) don't show "View changes" button
2. Verify "Clear highlights" button dismisses highlights
3. Verify closing and reopening the modal clears highlights
4. Verify the diff overlay closes on backdrop click and X button

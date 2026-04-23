import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";
import { GoogleGenerativeAI } from "@google/generative-ai";

const MAX_APPROVED = 10;

function getAdminPassword(): string | undefined {
  return process.env.ADMIN_PASSWORD;
}

function isAuthenticated(request: NextRequest): boolean {
  const password = getAdminPassword();
  if (!password) return false;
  return request.cookies.get("admin_token")?.value === password;
}

// ── Login page HTML ──────────────────────────────────────────────────
const LOGIN_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scaile Admin — Login</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%23222' width='100' height='100' rx='20'/%3E%3Ctext x='50' y='70' font-size='60' text-anchor='middle' fill='white' font-family='Inter,sans-serif' font-weight='700'%3ES%3C/text%3E%3C/svg%3E">
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:Inter,-apple-system,sans-serif;background:#f5f5f7}
    .card{background:#fff;border-radius:16px;padding:48px 40px;box-shadow:0 4px 24px rgba(0,0,0,.08);width:100%;max-width:380px}
    .logo{width:48px;height:48px;background:linear-gradient(135deg,#222,#444);border-radius:12px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:24px;margin-bottom:24px}
    h1{font-size:20px;color:#1d1d1f;margin-bottom:4px}
    .subtitle{font-size:14px;color:#86868b;margin-bottom:32px}
    input[type="password"]{width:100%;padding:12px 16px;border:1.5px solid #e8e8ed;border-radius:10px;font-size:15px;outline:none;transition:border-color .2s}
    input[type="password"]:focus{border-color:#222}
    button{width:100%;padding:12px;background:linear-gradient(135deg,#222,#444);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;margin-top:16px;transition:opacity .2s}
    button:hover{opacity:.9}
    .error{color:#ff3b30;font-size:13px;margin-top:12px;display:none;text-align:center}
    .error.show{display:block}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">S</div>
    <h1>Scaile Admin</h1>
    <p class="subtitle">Content approval portal</p>
    <form method="POST" action="/api/admin">
      <input type="hidden" name="action" value="login" />
      <input type="password" name="password" placeholder="Admin password" autofocus required />
      <button type="submit">Sign in</button>
      <p class="error __ERROR_CLASS__">Incorrect password</p>
    </form>
  </div>
</body>
</html>`;

// ── Admin dashboard HTML ─────────────────────────────────────────────
function adminPageHtml(opportunities: any[], approvedUrls: Set<string>, editorialArticles: any[] = []): string {
  const approvedCount = approvedUrls.size;

  const rows = opportunities.map((o: any, i: number) => {
    const isApproved = approvedUrls.has(o.url);
    const canApprove = approvedCount < MAX_APPROVED;
    const escapedUrl = (o.url || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;");
    const escapedTopic = (o.topic || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const escapedTitle = (o.suggested_title || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const escapedCategory = (o.category || "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
    const escapedSource = (o.source || "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
    const escapedItemId = (o.source_item_id || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;");

    return `<tr data-url="${escapedUrl}" data-item-id="${escapedItemId}" class="${isApproved ? "approved-row" : ""}">
      <td style="text-align:center;font-size:13px;color:#86868b">${i + 1}</td>
      <td>
        <div style="font-weight:500;margin-bottom:2px;font-size:14px">${escapedTopic}</div>
        ${escapedTitle ? `<div style="font-size:12px;color:#86868b">${escapedTitle}</div>` : ""}
      </td>
      <td><span class="cat-badge">${escapedCategory}</span></td>
      <td style="text-align:center;font-weight:600">${o.gap_score}</td>
      <td style="font-size:13px">${escapedSource}</td>
      <td style="text-align:center">
        <button class="approve-btn ${isApproved ? "approved" : ""}"
                onclick="toggleApproval(this)"
                ${!isApproved && !canApprove ? "disabled" : ""}>
          ${isApproved ? "Approved" : "Approve"}
        </button>
      </td>
    </tr>`;
  }).join("\n");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scaile Admin — Content Approval</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect fill='%23222' width='100' height='100' rx='20'/%3E%3Ctext x='50' y='70' font-size='60' text-anchor='middle' fill='white' font-family='Inter,sans-serif' font-weight='700'%3ES%3C/text%3E%3C/svg%3E">
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:Inter,-apple-system,sans-serif;background:#f5f5f7;color:#1d1d1f;padding:32px 24px}
    .container{max-width:1100px;margin:0 auto}
    .header{display:flex;align-items:center;justify-content:space-between;margin-bottom:32px}
    .header h1{font-size:24px;font-weight:700}
    .counter{font-size:15px;font-weight:600;padding:8px 16px;border-radius:10px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.06)}
    .counter .num{color:#C60050}
    .card{background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,.06);overflow:hidden}
    table{width:100%;border-collapse:collapse}
    th{text-align:left;padding:14px 16px;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:#86868b;border-bottom:1px solid #f0f0f0;background:#fafafa}
    td{padding:12px 16px;border-bottom:1px solid #f5f5f5;font-size:14px}
    tr:last-child td{border-bottom:none}
    tr.approved-row{background:#f0fdf4}
    .cat-badge{display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#f0f0f5;color:#555}
    .approve-btn{padding:6px 16px;border-radius:8px;border:1.5px solid #d1d1d6;background:#fff;font-size:13px;font-weight:600;cursor:pointer;transition:all .15s}
    .approve-btn:hover:not(:disabled){border-color:#222;background:#fafafa}
    .approve-btn.approved{background:#222;color:#fff;border-color:#222}
    .approve-btn.approved:hover{background:#444;border-color:#444}
    .approve-btn:disabled{opacity:.4;cursor:not-allowed}
    .approve-btn.loading{opacity:.6;pointer-events:none}
    .logout{font-size:13px;color:#86868b;text-decoration:none;border:1px solid #e8e8ed;padding:6px 14px;border-radius:8px;transition:all .15s}
    .logout:hover{border-color:#bbb;color:#555}
    .empty{padding:60px 32px;text-align:center;color:#86868b}
    .suggest-card{background:#fff;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,.06);padding:24px 28px;margin-bottom:24px}
    .suggest-card h2{font-size:18px;font-weight:700;margin-bottom:4px}
    .suggest-card .subtitle{font-size:13px;color:#86868b;margin-bottom:16px}
    .suggest-row{display:flex;gap:10px;align-items:flex-end}
    .suggest-row .field{display:flex;flex-direction:column;gap:4px}
    .suggest-row .field label{font-size:12px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:.3px}
    .suggest-row .field input,.suggest-row .field select{padding:9px 14px;border:1.5px solid #e8e8ed;border-radius:10px;font-size:14px;outline:none;transition:border-color .2s;font-family:inherit}
    .suggest-row .field input:focus,.suggest-row .field select:focus{border-color:#222}
    .suggest-btn{padding:9px 20px;border-radius:10px;border:none;background:linear-gradient(135deg,#222,#444);color:#fff;font-size:14px;font-weight:600;cursor:pointer;transition:all .15s;white-space:nowrap;position:relative}
    .suggest-btn:hover:not(:disabled){opacity:.9}
    .suggest-btn:disabled{opacity:.5;cursor:not-allowed}
    .suggest-btn.loading{pointer-events:none;opacity:.7}
    .suggest-btn.loading::after{content:'';display:inline-block;width:14px;height:14px;margin-left:8px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle}
    @keyframes spin{to{transform:rotate(360deg)}}
    .suggest-btn.secondary{background:#fff;color:#222;border:1.5px solid #d1d1d6}
    .suggest-btn.secondary:hover{border-color:#222;background:#fafafa}
    .enrichment-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}
    .enrichment-grid .field{display:flex;flex-direction:column;gap:4px}
    .enrichment-grid .field.full{grid-column:1/-1}
    .enrichment-grid .field label{font-size:12px;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:.3px}
    .enrichment-grid .field input,.enrichment-grid .field select,.enrichment-grid .field textarea{padding:9px 14px;border:1.5px solid #e8e8ed;border-radius:10px;font-size:14px;outline:none;transition:border-color .2s;font-family:inherit}
    .enrichment-grid .field textarea{resize:vertical;min-height:60px}
    .enrichment-grid .field input:focus,.enrichment-grid .field select:focus,.enrichment-grid .field textarea:focus{border-color:#222}
    .enrichment-actions{display:flex;gap:10px;margin-top:16px}
    /* Article Modal */
    #article-modal-overlay{position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.5);backdrop-filter:blur(2px);display:flex;align-items:center;justify-content:center}
    .article-modal{background:#fff;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.3);width:96vw;height:94vh;display:flex;flex-direction:column;overflow:hidden}
    .article-modal-header{padding:16px 20px;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-shrink:0}
    .article-modal-header h2{margin:0;font-size:18px;color:#111;flex:1}
    .article-modal-status{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:600}
    .article-modal-status.completed{background:#dcfce7;color:#166534}
    .article-modal-status.regenerating,.article-modal-status.generating{background:#fef3c7;color:#92400e}
    .article-modal-status.failed{background:#fee2e2;color:#991b1b}
    .article-modal-close{background:none;border:none;font-size:22px;cursor:pointer;color:#666;padding:0 4px;line-height:1;width:auto}
    .article-modal-close:hover{color:#111}
    .am-actions{display:flex;align-items:center;gap:8px;flex-shrink:0}
    .am-actions button{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid #d1d5db;background:#fff;color:#374151;transition:all .15s;white-space:nowrap;width:auto;margin:0}
    .am-actions button:hover{background:#f3f4f6;border-color:#9ca3af}
    .am-actions button.active{background:#eff6ff;border-color:#3b82f6;color:#1d4ed8}
    .am-actions .save-btn{background:#16a34a;color:#fff;border-color:#16a34a}
    .am-actions .save-btn:hover{background:#15803d}
    .am-actions .save-btn:disabled{opacity:.5;cursor:default}
    .am-actions .save-btn.saved{background:#dcfce7;color:#166534;border-color:#bbf7d0}
    .am-dirty{width:8px;height:8px;border-radius:50%;background:#f59e0b;display:none;flex-shrink:0}
    .am-dirty.visible{display:block}
    .article-modal-meta{display:flex;gap:12px;align-items:center;font-size:12px;color:#666;margin-top:4px}
    .article-modal-meta span{background:#f3f4f6;padding:2px 8px;border-radius:4px}
    .am-panels{display:flex;flex-direction:row;flex:1;min-height:0;overflow:hidden}
    .am-content{flex:1;min-width:0;overflow:hidden}
    .am-content iframe{width:100%;height:100%;border:none}
    .am-sidebar{width:380px;flex-shrink:0;border-left:1px solid #e5e7eb;display:flex;flex-direction:column;overflow:hidden;background:#fafafa;transition:width .2s}
    .am-panels.viewer-mode .am-sidebar{display:none}
    .am-actions .editor-only{display:none}
    .article-modal.editor-active .am-actions .editor-only{display:inline-flex}
    .article-modal.editor-active .am-actions .viewer-only{display:none}
    .am-sidebar-scroll{flex:1;overflow-y:auto;min-height:0}
    .am-section-title{padding:14px 16px 10px;font-size:13px;font-weight:700;color:#374151;border-bottom:1px solid #e5e7eb;background:#fff;flex-shrink:0}
    .fb-card{border:1px solid #e5e7eb;border-radius:8px;margin-bottom:10px;background:#fff;overflow:hidden}
    .fb-card-header{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:#fffbeb;border-bottom:1px solid #fef3c7;font-size:11px;color:#92400e}
    .fb-card-header .v-badge{background:#fbbf24;color:#78350f;padding:1px 8px;border-radius:999px;font-weight:700;font-size:10px}
    .fb-card-body{padding:10px 12px;font-size:13px;color:#374151;line-height:1.5}
    .fb-empty{padding:24px 16px;text-align:center;color:#9ca3af;font-size:13px}
    .fb-input-area{border-top:1px solid #e5e7eb;padding:12px 16px;background:#fff;flex-shrink:0}
    .fb-textarea{width:100%;min-height:80px;border:1px solid #d1d5db;border-radius:8px;padding:10px 12px;font-size:13px;font-family:inherit;resize:vertical;line-height:1.5;box-sizing:border-box}
    .fb-textarea:focus{outline:none;border-color:#0070f3;box-shadow:0 0 0 3px rgba(0,112,243,.1)}
    .fb-actions{display:flex;flex-direction:column;gap:8px;margin-top:10px}
    .fb-btn{padding:9px 14px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;text-align:center;transition:all .15s;width:auto;margin:0}
    .fb-btn.primary{background:#0070f3;color:#fff;border:none}
    .fb-btn.primary:hover{background:#005bc4}
    .fb-btn.primary:disabled{background:#93c5fd;cursor:not-allowed}
    .fb-btn.secondary{background:#fff;color:#374151;border:1px solid #d1d5db}
    .fb-btn.secondary:hover{background:#f3f4f6}
    .fb-btn.secondary:disabled{color:#9ca3af;cursor:not-allowed}
    .fb-btn.accent{background:#f59e0b;color:#fff;border:none}
    .fb-btn.accent:hover{background:#d97706}
    .fb-btn.accent:disabled{background:#fcd34d;cursor:not-allowed}
    .fb-status{padding:10px 14px;font-size:13px;font-weight:600;text-align:center;display:none;flex-shrink:0;border-radius:8px;margin:8px 12px;animation:statusFadeIn .3s ease}
    @keyframes statusFadeIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
    .fb-status.success{display:flex;align-items:center;justify-content:center;gap:8px;background:#dcfce7;color:#166534;border:1px solid #86efac}
    .fb-status.success::before{content:'\\2713';font-size:16px;font-weight:700}
    .fb-status.error{display:block;background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}
    .fb-status.loading{display:flex;align-items:center;justify-content:center;gap:8px;background:#fef3c7;color:#92400e;border:1px solid #fde68a}
    .fb-status.loading::before{content:'';width:14px;height:14px;border:2px solid #92400e;border-top-color:transparent;border-radius:50%;animation:spin .8s linear infinite}
    .inline-comment-popover{position:fixed;z-index:10001;background:#fff;border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.18),0 0 0 1px rgba(0,0,0,.05);padding:12px;width:280px}
    .inline-comment-popover .sel-preview{font-size:11px;color:#6b7280;font-style:italic;max-height:44px;overflow:hidden;border-left:3px solid #eab308;padding-left:8px;margin-bottom:8px;line-height:1.4}
    .inline-comment-popover .pop-textarea{width:100%;min-height:48px;border:1px solid #d1d5db;border-radius:6px;padding:8px;font-size:12px;font-family:inherit;resize:none;box-sizing:border-box;margin-bottom:8px}
    .inline-comment-popover .pop-textarea:focus{outline:none;border-color:#0070f3;box-shadow:0 0 0 2px rgba(0,112,243,.1)}
    .inline-comment-popover .pop-actions{display:flex;gap:6px;justify-content:flex-end}
    .inline-comment-popover .pop-btn{padding:5px 12px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;width:auto;margin:0}
    .inline-comment-popover .pop-btn.add{background:#0070f3;color:#fff;border:none}
    .inline-comment-popover .pop-btn.add:hover{background:#005bc4}
    .inline-comment-popover .pop-btn.cancel{background:transparent;color:#6b7280;border:1px solid #d1d5db}
    .inline-comment-popover .pop-btn.cancel:hover{background:#f3f4f6}
    .ic-section{display:flex;flex-direction:column;flex-shrink:0}
    .ic-header{padding:10px 16px;font-size:12px;font-weight:700;color:#374151;display:flex;justify-content:space-between;align-items:center;border-top:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb;background:#fff}
    .ic-count{background:#0070f3;color:#fff;padding:1px 7px;border-radius:999px;font-size:10px;font-weight:700;min-width:16px;text-align:center}
    .ic-list{max-height:180px;overflow-y:auto;padding:8px 12px}
    .ic-card{border:1px solid #e5e7eb;border-radius:8px;margin-bottom:8px;background:#fff;overflow:hidden}
    .ic-card .ic-quote{padding:6px 10px;background:#fefce8;border-bottom:1px solid #fef3c7;font-size:11px;color:#854d0e;font-style:italic;line-height:1.4;border-left:3px solid #eab308}
    .ic-card .ic-body{padding:8px 10px;font-size:12px;color:#374151;line-height:1.4;display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
    .ic-card .ic-remove{background:none;border:none;color:#9ca3af;cursor:pointer;font-size:16px;padding:0;line-height:1;flex-shrink:0;width:auto;margin:0}
    .ic-card .ic-remove:hover{color:#ef4444}
    .view-btn{padding:4px 12px;border-radius:6px;border:1px solid #d1d5db;background:#fff;font-size:12px;font-weight:600;cursor:pointer;transition:all .15s;color:#374151}
    .view-btn:hover{background:#f3f4f6;border-color:#9ca3af}
    .review-select{padding:4px 8px;border:1px solid #d1d5db;border-radius:6px;font-size:12px;background:#fff;cursor:pointer}
    @media(max-width:900px){.article-modal{width:100vw;height:100vh;border-radius:0}.am-panels{flex-direction:column}.am-sidebar{width:100%;border-left:none;border-top:1px solid #e5e7eb;max-height:40vh}.am-content{min-height:50vh}}
    .toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#222;color:#fff;padding:10px 24px;border-radius:8px;font-size:13px;font-weight:600;z-index:10002;animation:toastIn .3s ease}
    @keyframes toastIn{from{opacity:0;transform:translateX(-50%) translateY(10px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Content Approval</h1>
      <div style="display:flex;align-items:center;gap:16px">
        <div class="counter"><span class="num" id="approved-count">${approvedCount}</span> / ${MAX_APPROVED} approved</div>
        <a href="/api/admin?logout=1" class="logout">Logout</a>
      </div>
    </div>

    <!-- Suggest a Topic -->
    <div class="suggest-card">
      <h2>Suggest a Topic</h2>
      <p class="subtitle">Enter a topic to get SEO-enriched metadata, then generate an article.</p>
      <div id="suggest-input">
        <div class="suggest-row">
          <div class="field" style="flex:1">
            <label>Topic</label>
            <input type="text" id="topic-input" placeholder="e.g. Blutdruck richtig messen" onkeydown="if(event.key==='Enter'){event.preventDefault();suggestTopic();}" />
          </div>
          <div class="field">
            <label>Language</label>
            <select id="topic-lang">
              <option value="de">DE</option>
              <option value="en">EN</option>
            </select>
          </div>
          <button type="button" class="suggest-btn" id="suggest-btn" onclick="suggestTopic()">Suggest</button>
        </div>
      </div>
      <div id="suggest-preview" style="display:none">
        <div class="enrichment-grid">
          <div class="field full">
            <label>Suggested Title / Keyword</label>
            <input type="text" id="enrich-keyword" />
          </div>
          <div class="field full">
            <label>SEO Keywords (comma-separated)</label>
            <input type="text" id="enrich-keywords" />
          </div>
          <div class="field">
            <label>Search Intent</label>
            <select id="enrich-intent">
              <option value="Informational">Informational</option>
              <option value="Navigational">Navigational</option>
              <option value="Transactional">Transactional</option>
              <option value="Comparison">Comparison</option>
            </select>
          </div>
          <div class="field">
            <label>Language</label>
            <select id="enrich-lang">
              <option value="de">DE</option>
              <option value="en">EN</option>
            </select>
          </div>
          <div class="field full">
            <label>Content Brief</label>
            <textarea id="enrich-brief" rows="3"></textarea>
          </div>
        </div>
        <div class="enrichment-actions">
          <button type="button" class="suggest-btn" id="generate-btn" onclick="generateFromSuggestion()">Generate Article</button>
          <button type="button" class="suggest-btn secondary" onclick="cancelSuggestion()">Cancel</button>
        </div>
      </div>
      <div id="suggest-status" style="display:none;margin-top:12px;font-size:13px;padding:10px 14px;border-radius:8px"></div>
    </div>

    <div class="card">
      ${opportunities.length === 0
        ? `<div class="empty"><p>No content opportunities found.</p><p style="margin-top:8px;font-size:13px">Run the weekly pipeline first to generate opportunities.</p></div>`
        : `<table>
        <thead>
          <tr>
            <th style="width:40px">#</th>
            <th>Topic</th>
            <th>Category</th>
            <th style="text-align:center">Score</th>
            <th>Source</th>
            <th style="text-align:center;width:120px">Action</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>`}
    </div>

    <!-- Editorial Articles Section -->
    <div style="margin-top:32px">
      <h2 style="font-size:20px;font-weight:700;margin-bottom:16px">Editorial Articles</h2>
      <p style="font-size:13px;color:#86868b;margin-bottom:16px">Standalone articles not linked to social listening data. Approve to make visible in the dashboard.</p>
      <div class="card">
        ${editorialArticles.length === 0
          ? `<div class="empty"><p>No editorial articles found.</p><p style="margin-top:8px;font-size:13px">Create articles via the dashboard Blog tab.</p></div>`
          : `<table>
          <thead>
            <tr>
              <th style="width:40px">#</th>
              <th>Title / Keyword</th>
              <th>Status</th>
              <th style="text-align:center">Review</th>
              <th style="text-align:center;width:120px">Action</th>
            </tr>
          </thead>
          <tbody>
            ${editorialArticles.map((a: any, i: number) => {
              const escapedTitle = (a.headline || a.keyword || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
              const escapedKeyword = (a.keyword || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
              const isApproved = a.review_status === "approved";
              const statusBadge = a.status === "completed"
                ? '<span style="display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#dcfce7;color:#166534">Completed</span>'
                : a.status === "generating" || a.status === "regenerating"
                ? '<span style="display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#fef3c7;color:#92400e">Generating</span>'
                : a.status === "failed"
                ? '<span style="display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#fee2e2;color:#991b1b">Failed</span>'
                : '<span style="display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#f3f4f6;color:#6b7280">Pending</span>';
              const reviewBadge = isApproved
                ? '<span style="display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#dcfce7;color:#166534">Approved</span>'
                : '<span style="display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#f3f4f6;color:#6b7280">Draft</span>';
              return `<tr data-article-id="${a.id}" class="${isApproved ? "approved-row" : ""}">
                <td style="text-align:center;font-size:13px;color:#86868b">${i + 1}</td>
                <td>
                  <div style="font-weight:500;margin-bottom:2px;font-size:14px">${escapedTitle}</div>
                  ${a.headline && escapedKeyword ? `<div style="font-size:12px;color:#86868b">${escapedKeyword}</div>` : ""}
                </td>
                <td>${statusBadge}</td>
                <td style="text-align:center">${reviewBadge}</td>
                <td style="text-align:center">
                  <div style="display:flex;gap:6px;justify-content:center">
                    ${a.status === "completed" ? `<button type="button" class="view-btn" onclick="openArticleModal('${a.id}')">View</button>` : ""}
                    <button class="approve-btn ${isApproved ? "approved" : ""}"
                            onclick="toggleEditorialApproval(this)">
                      ${isApproved ? "Approved" : "Approve"}
                    </button>
                  </div>
                </td>
              </tr>`;
            }).join("\n")}
          </tbody>
        </table>`}
      </div>
    </div>
  </div>
  <script>
    const MAX = ${MAX_APPROVED};
    let approvedCount = ${approvedCount};

    function updateCounter() {
      document.getElementById('approved-count').textContent = approvedCount;
      document.querySelectorAll('.approve-btn').forEach(btn => {
        const isApproved = btn.classList.contains('approved');
        if (!isApproved && approvedCount >= MAX) {
          btn.disabled = true;
        } else {
          btn.disabled = false;
        }
      });
    }

    async function toggleApproval(btn) {
      const row = btn.closest('tr');
      const url = row.dataset.url;
      const itemId = row.dataset.itemId;
      const isApproved = btn.classList.contains('approved');
      const action = isApproved ? 'unapprove' : 'approve';

      btn.classList.add('loading');
      btn.textContent = '...';

      try {
        const res = await fetch('/api/admin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, source_url: url, source_item_id: itemId })
        });
        const data = await res.json();

        if (data.ok) {
          if (action === 'approve') {
            btn.classList.add('approved');
            btn.textContent = 'Approved';
            row.classList.add('approved-row');
            approvedCount++;
          } else {
            btn.classList.remove('approved');
            btn.textContent = 'Approve';
            row.classList.remove('approved-row');
            approvedCount--;
          }
          updateCounter();
        } else {
          alert(data.error || 'Action failed');
          btn.textContent = isApproved ? 'Approved' : 'Approve';
        }
      } catch (err) {
        alert('Network error: ' + err.message);
        btn.textContent = isApproved ? 'Approved' : 'Approve';
      } finally {
        btn.classList.remove('loading');
      }
    }
    async function suggestTopic() {
      const topicInput = document.getElementById('topic-input');
      const topic = topicInput.value.trim();
      const language = document.getElementById('topic-lang').value;
      const btn = document.getElementById('suggest-btn');
      const statusEl = document.getElementById('suggest-status');

      if (!topic) {
        topicInput.style.borderColor = '#ff3b30';
        topicInput.focus();
        setTimeout(function() { topicInput.style.borderColor = ''; }, 2000);
        return;
      }

      btn.disabled = true;
      btn.classList.add('loading');
      btn.textContent = 'Enriching';
      statusEl.style.display = 'none';

      try {
        const res = await fetch('/api/admin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'enrich_topic', topic: topic, language: language })
        });
        const data = await res.json();

        if (data.ok) {
          document.getElementById('enrich-keyword').value = data.suggested_title || topic;
          document.getElementById('enrich-keywords').value = (data.keywords || []).join(', ');
          document.getElementById('enrich-intent').value = data.search_intent || 'Informational';
          document.getElementById('enrich-lang').value = language;
          document.getElementById('enrich-brief').value = data.content_brief || '';
          document.getElementById('suggest-input').style.display = 'none';
          document.getElementById('suggest-preview').style.display = 'block';
        } else {
          statusEl.textContent = data.error || 'Enrichment failed';
          statusEl.style.display = 'block';
          statusEl.style.background = '#fee2e2';
          statusEl.style.color = '#991b1b';
        }
      } catch (err) {
        statusEl.textContent = 'Network error: ' + err.message;
        statusEl.style.display = 'block';
        statusEl.style.background = '#fee2e2';
        statusEl.style.color = '#991b1b';
      } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = 'Suggest';
      }
    }

    function cancelSuggestion() {
      document.getElementById('suggest-input').style.display = 'block';
      document.getElementById('suggest-preview').style.display = 'none';
      document.getElementById('suggest-status').style.display = 'none';
    }

    async function generateFromSuggestion() {
      var keyword = document.getElementById('enrich-keyword').value.trim();
      var language = document.getElementById('enrich-lang').value;
      if (!keyword) return;

      var btn = document.getElementById('generate-btn');
      var statusEl = document.getElementById('suggest-status');
      btn.disabled = true;
      btn.classList.add('loading');
      btn.textContent = 'Creating';

      try {
        var res = await fetch('/api/admin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'suggest_topic', keyword: keyword, language: language })
        });
        var data = await res.json();

        if (data.ok) {
          statusEl.textContent = 'Article generation started! It will appear in the Editorial Articles section below.';
          statusEl.style.display = 'block';
          statusEl.style.background = '#dcfce7';
          statusEl.style.color = '#166534';
          document.getElementById('suggest-preview').style.display = 'none';
          document.getElementById('suggest-input').style.display = 'block';
          document.getElementById('topic-input').value = '';
          setTimeout(function() { location.reload(); }, 2000);
        } else {
          statusEl.textContent = data.error || 'Article creation failed';
          statusEl.style.display = 'block';
          statusEl.style.background = '#fee2e2';
          statusEl.style.color = '#991b1b';
        }
      } catch (err) {
        statusEl.textContent = 'Network error: ' + err.message;
        statusEl.style.display = 'block';
        statusEl.style.background = '#fee2e2';
        statusEl.style.color = '#991b1b';
      } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = 'Generate Article';
      }
    }

    /* ── Article Modal System ── */
    function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
    function showToast(msg) { var t=document.createElement('div');t.className='toast';t.textContent=msg;document.body.appendChild(t);setTimeout(function(){t.remove();},3000); }

    var _articleEditMode = false, _articleDirty = false, _articleInputListener = null, _articlePanelOpen = false;
    var _inlineComments = [], _commentIdCounter = 0, _activePopover = null;
    var _feedbackDrafts = new Map();

    async function openArticleModal(articleId) {
      try {
        var res = await fetch('/api/blog-article?id=' + articleId);
        var article = await res.json();
        if (!article || article.error) { alert('Article not found'); return; }

        var existing = document.getElementById('article-modal-overlay');
        if (existing) existing.remove();

        var feedbackHistory = article.feedback_history || [];
        var overlay = document.createElement('div');
        overlay.id = 'article-modal-overlay';
        overlay.dataset.articleId = articleId;

        var statusClass = article.status || 'completed';
        var statusLabel = article.status === 'regenerating' ? 'Regenerating...' : article.status === 'failed' ? 'Failed' : article.status === 'generating' ? 'Generating...' : 'Completed';

        var fbHistoryHtml = feedbackHistory.length === 0
          ? '<div class="fb-empty">No feedback yet</div>'
          : feedbackHistory.map(function(fb,i){ return buildFeedbackCardHTML(fb,i); }).join('');

        overlay.innerHTML = '<div class="article-modal" id="article-modal-main">'
          + '<div class="article-modal-header"><div>'
          + '<h2>' + esc(article.headline || article.keyword || '') + '</h2>'
          + '<div class="article-modal-meta">'
          + (article.word_count ? '<span>' + article.word_count + ' words</span>' : '')
          + '<span>' + (article.language || 'de').toUpperCase() + '</span>'
          + '<span>' + esc(article.keyword || '') + '</span>'
          + '<span class="article-modal-status ' + statusClass + '">' + statusLabel + '</span>'
          + '</div></div>'
          + '<div class="am-actions">'
          + '<button type="button" class="viewer-only" onclick="saveArticleAsMarkdown(\\'' + articleId + '\\',\\'' + esc(article.headline || article.keyword || 'article').replace(/'/g,"\\\\'") + '\\')">&#128196; Markdown</button>'
          + '<button type="button" class="viewer-only" id="btn-copy-html" onclick="copyArticleHtml(\\'' + articleId + '\\')">&#128203; Copy HTML</button>'
          + '<button type="button" class="viewer-only" id="btn-download-modal" onclick="downloadArticleFromModal(\\'' + articleId + '\\',\\'' + esc(article.headline || article.keyword || 'article').replace(/'/g,"\\\\'") + '\\')">&#8615; Download</button>'
          + '<button type="button" class="editor-only" id="btn-toggle-edit" onclick="toggleArticleEditMode(\\'' + articleId + '\\')">&#9998; Edit HTML</button>'
          + '<div class="editor-only am-dirty" id="article-dirty-dot"></div>'
          + '<button type="button" class="editor-only save-btn" id="btn-save-html" style="display:none" onclick="handleSaveArticleHtml(\\'' + articleId + '\\')">Save</button>'
          + '<button type="button" class="editor-only" id="btn-reset-edits" onclick="handleResetEdits(\\'' + articleId + '\\')" style="' + (article.html_custom ? '' : 'display:none') + '" title="Reset Edits">&#8634; Reset</button>'
          + '<button type="button" id="btn-toggle-panel" onclick="toggleArticlePanel()">&#9998; Edit</button>'
          + '<button type="button" class="article-modal-close">&times;</button>'
          + '</div></div>'
          + '<div class="am-panels viewer-mode" id="article-modal-panels">'
          + '<div class="am-content"><iframe sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"></iframe></div>'
          + '<div class="am-sidebar"><div class="am-sidebar-scroll">'
          + '<div style="padding:12px 16px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;gap:8px">'
          + '<span style="font-size:12px;font-weight:600;color:#374151">Review:</span>'
          + '<select class="review-select" id="review-status-select" onchange="handleReviewChange(\\'' + articleId + '\\')">'
          + '<option value="draft"' + (article.review_status==='draft'?' selected':'') + '>Draft</option>'
          + '<option value="review"' + (article.review_status==='review'?' selected':'') + '>In Review</option>'
          + '<option value="approved"' + (article.review_status==='approved'?' selected':'') + '>Approved</option>'
          + '<option value="published"' + (article.review_status==='published'?' selected':'') + '>Published</option>'
          + '</select></div>'
          + '<div class="am-section-title">Feedback History</div>'
          + '<div class="feedback-history-list" id="feedback-history-list">' + fbHistoryHtml + '</div>'
          + '<div class="ic-section" id="inline-comments-section">'
          + '<div class="ic-header"><span>Inline Comments</span><span class="ic-count" id="inline-comments-count">0</span></div>'
          + '<div class="ic-list" id="inline-comments-list"><div class="fb-empty" id="inline-comments-empty">Select text in the article to add inline comments</div></div>'
          + '<div style="padding:8px 12px"><button type="button" class="fb-btn accent" id="btn-apply-edits" onclick="handleApplyEdits(\\'' + articleId + '\\')" style="width:100%;display:none">Apply Inline Edits</button></div>'
          + '</div>'
          + '<div class="fb-status" id="feedback-status-bar"></div>'
          + '</div>'
          + '<div class="fb-input-area">'
          + '<textarea class="fb-textarea" id="feedback-textarea" placeholder="Enter feedback for regeneration..."></textarea>'
          + '<div class="fb-actions">'
          + '<button type="button" class="fb-btn primary" id="btn-regen-feedback" onclick="handleRegenerate(\\'' + articleId + '\\',false)">Regenerate with Feedback</button>'
          + '<button type="button" class="fb-btn secondary" id="btn-regen-scratch" onclick="handleRegenerate(\\'' + articleId + '\\',true)">Regenerate from Scratch</button>'
          + '</div></div></div></div></div>';

        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden';

        dismissCommentPopover();
        _restoreFeedbackDraft(articleId);

        var iframe = overlay.querySelector('iframe');
        if (iframe) {
          setupIframeSelection(iframe);
          var html = article.article_html || '';
          if (html && (html.includes('__DASHBOARD_DATA__') || html.includes('Social Listening Dashboard'))) html = '';
          if (html) { iframe.srcdoc = html; }
          else { iframe.srcdoc = '<html><body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;color:#6b7280"><div style="text-align:center"><p style="font-size:18px;margin-bottom:8px">No content available</p><p style="font-size:13px">Article may still be generating.</p></div></body></html>'; }
        }

        var popoverDismissHandler = function(e) { if (_activePopover && !_activePopover.contains(e.target)) dismissCommentPopover(); };
        document.addEventListener('mousedown', popoverDismissHandler);

        function closeModal() {
          if (_articleDirty && !confirm('You have unsaved changes. Close anyway?')) return;
          _saveFeedbackDraft(articleId);
          dismissCommentPopover();
          _resetArticleEditState();
          overlay.remove();
          document.body.style.overflow = '';
          document.removeEventListener('keydown', escHandler);
          document.removeEventListener('mousedown', popoverDismissHandler);
        }

        overlay.querySelector('.article-modal-close').onclick = closeModal;
        overlay.addEventListener('click', function(e) { if (e.target === overlay) closeModal(); });
        var escHandler = function(e) { if (e.key === 'Escape') closeModal(); };
        document.addEventListener('keydown', escHandler);
      } catch (err) { alert('Failed to load article: ' + (err.message || '')); }
    }

    function toggleArticlePanel() {
      _articlePanelOpen = !_articlePanelOpen;
      var panels = document.getElementById('article-modal-panels');
      var modal = document.getElementById('article-modal-main');
      var btn = document.getElementById('btn-toggle-panel');
      if (_articlePanelOpen) {
        if (panels) { panels.classList.remove('viewer-mode'); panels.classList.add('editor-mode'); }
        if (modal) modal.classList.add('editor-active');
        if (btn) btn.textContent = '\\u2714 Done';
      } else {
        if (_articleEditMode) {
          var ov = document.getElementById('article-modal-overlay');
          if (ov) { var ifr = ov.querySelector('iframe'); if (ifr && ifr.contentDocument) { ifr.contentDocument.body.contentEditable = 'false'; ifr.contentDocument.body.style.outline = 'none'; if (_articleInputListener) { ifr.contentDocument.body.removeEventListener('input', _articleInputListener); _articleInputListener = null; } } }
          _articleEditMode = false;
          var eb = document.getElementById('btn-toggle-edit'); if (eb) eb.classList.remove('active');
          var sb = document.getElementById('btn-save-html'); if (sb) sb.style.display = 'none';
        }
        if (panels) { panels.classList.remove('editor-mode'); panels.classList.add('viewer-mode'); }
        if (modal) modal.classList.remove('editor-active');
        if (btn) btn.textContent = '\\u270E Edit';
      }
    }

    function toggleArticleEditMode(articleId) {
      var overlay = document.getElementById('article-modal-overlay');
      if (!overlay) return;
      var iframe = overlay.querySelector('iframe');
      var btn = document.getElementById('btn-toggle-edit');
      var saveBtn = document.getElementById('btn-save-html');
      if (!iframe || !iframe.contentDocument) return;
      _articleEditMode = !_articleEditMode;
      iframe.contentDocument.body.contentEditable = _articleEditMode ? 'true' : 'false';
      iframe.contentDocument.body.style.outline = _articleEditMode ? '2px solid #3b82f6' : 'none';
      if (btn) btn.classList.toggle('active', _articleEditMode);
      if (saveBtn) saveBtn.style.display = _articleEditMode ? '' : 'none';
      if (_articleEditMode) {
        _articleInputListener = function() { _onArticleInput(); };
        iframe.contentDocument.body.addEventListener('input', _articleInputListener);
      } else if (_articleInputListener) {
        iframe.contentDocument.body.removeEventListener('input', _articleInputListener);
        _articleInputListener = null;
      }
    }

    function _onArticleInput() {
      if (!_articleDirty) {
        _articleDirty = true;
        var dot = document.getElementById('article-dirty-dot'); if (dot) dot.classList.add('visible');
        var saveBtn = document.getElementById('btn-save-html');
        if (saveBtn) { saveBtn.classList.remove('saved'); saveBtn.textContent = 'Save'; saveBtn.disabled = false; }
      }
    }

    function _resetArticleEditState() {
      _articlePanelOpen = false; _articleEditMode = false; _articleDirty = false; _articleInputListener = null;
      var btn = document.getElementById('btn-toggle-edit');
      var saveBtn = document.getElementById('btn-save-html');
      var dot = document.getElementById('article-dirty-dot');
      if (btn) btn.classList.remove('active');
      if (saveBtn) { saveBtn.style.display = 'none'; saveBtn.classList.remove('saved'); saveBtn.textContent = 'Save'; }
      if (dot) dot.classList.remove('visible');
    }

    async function handleSaveArticleHtml(articleId) {
      var overlay = document.getElementById('article-modal-overlay'); if (!overlay) return;
      var iframe = overlay.querySelector('iframe');
      var saveBtn = document.getElementById('btn-save-html');
      if (!iframe || !iframe.contentDocument) return;
      if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Saving...'; }
      try {
        var html = '<!DOCTYPE html>' + iframe.contentDocument.documentElement.outerHTML;
        var r = await fetch('/api/blog-article', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ article_id: articleId, action: 'save_html', article_html: html }) });
        var data = await r.json(); if (!r.ok) throw new Error(data.error || 'Save failed');
        _articleDirty = false;
        var dot = document.getElementById('article-dirty-dot'); if (dot) dot.classList.remove('visible');
        if (saveBtn) { saveBtn.classList.add('saved'); saveBtn.textContent = 'Saved'; saveBtn.disabled = true; }
        var resetBtn = document.getElementById('btn-reset-edits'); if (resetBtn) resetBtn.style.display = '';
        showToast('HTML saved');
      } catch (err) {
        if (saveBtn) { saveBtn.textContent = 'Save failed'; saveBtn.disabled = false; }
        setTimeout(function(){ if(saveBtn) saveBtn.textContent = 'Save'; }, 3000);
      }
    }

    async function handleResetEdits(articleId) {
      if (!confirm('Reset all HTML edits to the original generated version?')) return;
      var btn = document.getElementById('btn-reset-edits'); if (btn) { btn.disabled = true; btn.textContent = 'Resetting...'; }
      try {
        var r = await fetch('/api/blog-article', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ article_id: articleId, action: 'reset_html' }) });
        var data = await r.json(); if (!r.ok) throw new Error(data.error || 'Reset failed');
        var iframe = document.querySelector('#article-modal-overlay iframe');
        if (iframe && data.article_html) { iframe.srcdoc = data.article_html; setupIframeSelection(iframe); }
        if (btn) btn.style.display = 'none';
        _articleDirty = false;
        var dot = document.getElementById('article-dirty-dot'); if (dot) dot.classList.remove('visible');
        var saveBtn = document.getElementById('btn-save-html'); if (saveBtn) { saveBtn.style.display = 'none'; saveBtn.classList.remove('saved'); }
        if (_articleEditMode) toggleArticleEditMode(articleId);
        showToast('Edits reset');
      } catch (err) { if (btn) { btn.disabled = false; btn.textContent = 'Reset'; } showToast(err.message || 'Reset failed'); }
    }

    async function handleReviewChange(articleId) {
      var sel = document.getElementById('review-status-select'); if (!sel) return;
      try {
        var r = await fetch('/api/blog-article', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ article_id: articleId, action: 'review_status', review_status: sel.value }) });
        if (!r.ok) throw new Error('Failed');
        showToast('Review status updated to ' + sel.value);
      } catch (err) { showToast('Failed to update review status'); }
    }

    function downloadArticleFromModal(articleId, filename) {
      var overlay = document.getElementById('article-modal-overlay'); if (!overlay) return;
      var iframe = overlay.querySelector('iframe'); if (!iframe || !iframe.contentDocument) return;
      var doc = iframe.contentDocument.cloneNode(true);
      doc.querySelectorAll('script, nav, header, footer, .breadcrumb, .category-badge').forEach(function(el){el.remove();});
      doc.querySelectorAll('.inline-comment-highlight').forEach(function(el){ var p=el.parentNode; while(el.firstChild) p.insertBefore(el.firstChild,el); p.removeChild(el); });
      var styles = Array.from(doc.querySelectorAll('style')).map(function(s){return s.outerHTML;}).join('\\n');
      var articleEl = doc.querySelector('article');
      var content = articleEl ? articleEl.outerHTML : doc.body.innerHTML;
      var cleanHtml = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>' + esc(filename) + '</title>' + styles + '</head><body>' + content + '</body></html>';
      var blob = new Blob([cleanHtml], { type: 'text/html;charset=utf-8;' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = filename.replace(/[^a-zA-Z0-9\\u00e4\\u00f6\\u00fc\\u00c4\\u00d6\\u00dc\\u00df\\-_ ]/g,'').replace(/\\s+/g,'-').slice(0,60) + '.html';
      document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    }

    async function copyArticleHtml(articleId) {
      var overlay = document.getElementById('article-modal-overlay'); if (!overlay) return;
      var iframe = overlay.querySelector('iframe'); if (!iframe || !iframe.contentDocument) return;
      var html = '<!DOCTYPE html>' + iframe.contentDocument.documentElement.outerHTML;
      try {
        await navigator.clipboard.writeText(html);
        var btn = document.getElementById('btn-copy-html');
        if (btn) { var orig = btn.innerHTML; btn.innerHTML = '&#10003; Copied'; setTimeout(function(){ btn.innerHTML = orig; }, 2000); }
      } catch (e) { console.error('Copy failed:', e); }
    }

    function saveArticleAsMarkdown(articleId, filename) {
      var overlay = document.getElementById('article-modal-overlay'); if (!overlay) return;
      var iframe = overlay.querySelector('iframe'); if (!iframe || !iframe.contentDocument) return;
      var doc = iframe.contentDocument.cloneNode(true);
      doc.querySelectorAll('script, nav, header, footer, .breadcrumb, .category-badge').forEach(function(el){el.remove();});
      doc.querySelectorAll('.inline-comment-highlight').forEach(function(el){ var p=el.parentNode; while(el.firstChild) p.insertBefore(el.firstChild,el); p.removeChild(el); });
      var articleEl = doc.querySelector('article') || doc.body;
      var md = _htmlToMarkdown(articleEl);
      var blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = filename.replace(/[^a-zA-Z0-9\\u00e4\\u00f6\\u00fc\\u00c4\\u00d6\\u00dc\\u00df\\-_ ]/g,'').replace(/\\s+/g,'-').slice(0,60) + '.md';
      document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    }

    function _htmlToMarkdown(el) {
      var md = '';
      for (var node of el.childNodes) {
        if (node.nodeType === Node.TEXT_NODE) { md += node.textContent; continue; }
        if (node.nodeType !== Node.ELEMENT_NODE) continue;
        var tag = node.tagName.toLowerCase();
        if (['style','script','nav','footer'].includes(tag)) continue;
        if (/^h([1-4])$/.test(tag)) { md += '\\n' + '#'.repeat(parseInt(tag[1])) + ' ' + _mdInline(node) + '\\n\\n'; }
        else if (tag === 'p') { md += _mdInline(node) + '\\n\\n'; }
        else if (tag === 'ul') { for (var li of node.children) { if (li.tagName.toLowerCase()==='li') md += '- ' + _mdInline(li) + '\\n'; } md += '\\n'; }
        else if (tag === 'ol') { var n=1; for (var li of node.children) { if (li.tagName.toLowerCase()==='li') { md += n + '. ' + _mdInline(li) + '\\n'; n++; } } md += '\\n'; }
        else if (tag === 'blockquote') { md += _htmlToMarkdown(node).trim().split('\\n').map(function(l){return '> '+l;}).join('\\n') + '\\n\\n'; }
        else if (tag === 'hr') { md += '---\\n\\n'; }
        else if (tag === 'br') { md += '\\n'; }
        else if (['div','section','article','main','figure','figcaption'].includes(tag)) { md += _htmlToMarkdown(node); }
        else { md += _mdInline(node); }
      }
      return md;
    }

    function _mdInline(el) {
      var out = '';
      for (var node of el.childNodes) {
        if (node.nodeType === Node.TEXT_NODE) { out += node.textContent; continue; }
        if (node.nodeType !== Node.ELEMENT_NODE) continue;
        var tag = node.tagName.toLowerCase();
        var inner = _mdInline(node);
        if (tag==='strong'||tag==='b') out += '**'+inner+'**';
        else if (tag==='em'||tag==='i') out += '*'+inner+'*';
        else if (tag==='code') out += '\`'+inner+'\`';
        else if (tag==='a') out += '['+inner+']('+( node.getAttribute('href')||'')+')';
        else if (tag==='br') out += '\\n';
        else out += inner;
      }
      return out;
    }

    function buildFeedbackCardHTML(fb, index) {
      var date = fb.created_at ? new Date(fb.created_at).toLocaleString() : '';
      var version = fb.version || (index + 1);
      return '<div class="fb-card"><div class="fb-card-header"><span class="v-badge">V' + version + '</span><span>' + date + '</span></div><div class="fb-card-body">' + esc(fb.comment || '') + '</div></div>';
    }

    function _saveFeedbackDraft(articleId) {
      var textarea = document.getElementById('feedback-textarea');
      _feedbackDrafts.set(articleId, { inlineComments: _inlineComments.slice(), commentIdCounter: _commentIdCounter, textareaValue: textarea ? textarea.value : '' });
    }

    function _restoreFeedbackDraft(articleId) {
      var draft = _feedbackDrafts.get(articleId);
      if (!draft) { _inlineComments = []; _commentIdCounter = 0; return; }
      _inlineComments = draft.inlineComments.slice();
      _commentIdCounter = draft.commentIdCounter;
      var textarea = document.getElementById('feedback-textarea');
      if (textarea) textarea.value = draft.textareaValue;
      renderInlineComments();
    }

    function setupIframeSelection(iframe) {
      iframe.addEventListener('load', function() {
        var iframeDoc = iframe.contentDocument; if (!iframeDoc) return;
        if (iframeDoc.body) iframeDoc.body.contentEditable = 'false';
        iframeDoc.addEventListener('click', function(e) {
          if (_articleEditMode) return;
          var link = e.target.closest('a[href]');
          if (link) { e.preventDefault(); var href = link.getAttribute('href'); if (href && href !== '#' && !href.startsWith('#')) window.open(href, '_blank', 'noopener,noreferrer'); else if (href && href.startsWith('#')) { var target = iframeDoc.querySelector(href); if (target) target.scrollIntoView({ behavior: 'smooth' }); } }
        });
        var style = iframeDoc.createElement('style');
        style.textContent = '.inline-highlight{background:#fef9c3;border-bottom:2px solid #eab308;transition:background .2s}.inline-highlight:hover{background:#fde68a}article,.intro,.direct-answer{cursor:text;position:relative}article::selection,.intro::selection,.direct-answer::selection,article *::selection,.intro *::selection,.direct-answer *::selection{background:#bae6fd}header,.toc,.sources,.faq,.paa,.meta,.last-updated,.author-card{position:relative}header::selection,.toc::selection,.sources::selection,.faq::selection,.paa::selection,.meta::selection,.last-updated::selection,.author-card::selection,header *::selection,.toc *::selection,.sources *::selection,.faq *::selection,.paa *::selection,.meta *::selection,.last-updated *::selection,.author-card *::selection{background:transparent}';
        iframeDoc.head.appendChild(style);
        iframeDoc.addEventListener('mousedown', function() { dismissCommentPopover(); });
        iframeDoc.addEventListener('mouseup', function() {
          setTimeout(function() {
            var selection = iframeDoc.getSelection();
            if (!selection || selection.isCollapsed || !selection.toString().trim()) return;
            var selectedText = selection.toString().trim();
            if (selectedText.length < 3) return;
            var range = selection.getRangeAt(0);
            var node = range.commonAncestorContainer;
            var el = node.nodeType === 3 ? node.parentElement : node;
            if (el && el.closest('header,.toc,.sources,.faq,.paa,.meta,.last-updated,.author-card,.image-placeholder')) return;
            var rect = range.getBoundingClientRect();
            var iframeRect = iframe.getBoundingClientRect();
            showCommentPopover({ top: iframeRect.top + rect.bottom, left: iframeRect.left + rect.left, width: rect.width }, selectedText, range, iframeDoc);
          }, 10);
        });
      });
    }

    function showCommentPopover(pos, selectedText, range, iframeDoc) {
      dismissCommentPopover();
      var popover = document.createElement('div');
      popover.className = 'inline-comment-popover';
      var preview = selectedText.length > 100 ? selectedText.substring(0, 100) + '\\u2026' : selectedText;
      popover.innerHTML = '<div class="sel-preview">\\u201C' + esc(preview) + '\\u201D</div><textarea class="pop-textarea" placeholder="Your comment..." rows="2"></textarea><div class="pop-actions"><button type="button" class="pop-btn cancel">Cancel</button><button type="button" class="pop-btn add">Add</button></div>';
      var gap = 8, popWidth = 280, popHeight = 160;
      var top = pos.top + gap, left = pos.left;
      if (top + popHeight > window.innerHeight) top = pos.top - popHeight - gap;
      if (left + popWidth > window.innerWidth) left = window.innerWidth - popWidth - 16;
      if (left < 16) left = 16;
      popover.style.top = top + 'px'; popover.style.left = left + 'px';
      var cancelBtn = popover.querySelector('.pop-btn.cancel');
      var addBtn = popover.querySelector('.pop-btn.add');
      var textarea = popover.querySelector('.pop-textarea');
      cancelBtn.addEventListener('click', function() { dismissCommentPopover(); });
      addBtn.addEventListener('click', function() {
        var comment = textarea.value.trim();
        if (!comment) { textarea.style.borderColor = '#ef4444'; textarea.focus(); return; }
        addInlineComment(selectedText, comment, range, iframeDoc);
        dismissCommentPopover();
        iframeDoc.getSelection().removeAllRanges();
      });
      textarea.addEventListener('keydown', function(e) { if (e.key==='Enter'&&(e.ctrlKey||e.metaKey)) addBtn.click(); if (e.key==='Escape') dismissCommentPopover(); });
      popover.addEventListener('click', function(e){e.stopPropagation();}); popover.addEventListener('mousedown', function(e){e.stopPropagation();});
      var overlay = document.getElementById('article-modal-overlay');
      if (overlay) overlay.appendChild(popover);
      _activePopover = popover;
      setTimeout(function(){ textarea.focus(); }, 50);
    }

    function dismissCommentPopover() { if (_activePopover) { _activePopover.remove(); _activePopover = null; } }

    function addInlineComment(text, comment, range, iframeDoc) {
      var id = _commentIdCounter++;
      var highlighted = false;
      try { var mark = iframeDoc.createElement('mark'); mark.className = 'inline-highlight'; mark.dataset.commentId = id; range.surroundContents(mark); highlighted = true; } catch(e) {}
      _inlineComments.push({ id: id, text: text, comment: comment, highlighted: highlighted });
      renderInlineComments();
    }

    function removeInlineComment(id) {
      var overlay = document.getElementById('article-modal-overlay');
      if (overlay) { var iframe = overlay.querySelector('iframe'); if (iframe && iframe.contentDocument) { var mark = iframe.contentDocument.querySelector('mark[data-comment-id="'+id+'"]'); if (mark) { var parent = mark.parentNode; while(mark.firstChild) parent.insertBefore(mark.firstChild, mark); parent.removeChild(mark); parent.normalize(); } } }
      _inlineComments = _inlineComments.filter(function(c){return c.id !== id;});
      renderInlineComments();
    }

    function renderInlineComments() {
      var list = document.getElementById('inline-comments-list');
      var count = document.getElementById('inline-comments-count');
      var applyBtn = document.getElementById('btn-apply-edits');
      if (!list) return;
      if (count) count.textContent = _inlineComments.length;
      if (_inlineComments.length === 0) {
        list.innerHTML = '<div class="fb-empty" id="inline-comments-empty">Select text in the article to add inline comments</div>';
        if (applyBtn) applyBtn.style.display = 'none'; return;
      }
      if (applyBtn) applyBtn.style.display = '';
      list.innerHTML = _inlineComments.map(function(ic) {
        var preview = ic.text.length > 80 ? ic.text.substring(0, 80) + '\\u2026' : ic.text;
        return '<div class="ic-card"><div class="ic-quote">\\u201C' + esc(preview) + '\\u201D</div><div class="ic-body"><span>' + esc(ic.comment) + '</span><button type="button" class="ic-remove" onclick="removeInlineComment(' + ic.id + ')" title="Remove">&times;</button></div></div>';
      }).join('');
    }

    async function handleRegenerate(articleId, fromScratch) {
      var textarea = document.getElementById('feedback-textarea');
      var statusBar = document.getElementById('feedback-status-bar');
      var btnFeedback = document.getElementById('btn-regen-feedback');
      var btnScratch = document.getElementById('btn-regen-scratch');
      var feedback = textarea ? textarea.value.trim() : '';
      if (!fromScratch && !feedback) {
        statusBar.className = 'fb-status error'; statusBar.textContent = 'Please enter feedback first';
        setTimeout(function(){ statusBar.className = 'fb-status'; statusBar.textContent = ''; }, 3000); return;
      }
      if (btnFeedback) btnFeedback.disabled = true; if (btnScratch) btnScratch.disabled = true;
      statusBar.className = 'fb-status loading'; statusBar.textContent = 'Regenerating...';
      try {
        var r = await fetch('/api/blog-article', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ article_id: articleId, feedback: feedback || null, from_scratch: fromScratch }) });
        var data = await r.json();
        if (data.status === 'regenerating' || data.status === 'completed') {
          var polls = 0, maxPolls = 40;
          var pollInterval = setInterval(async function() {
            polls++;
            if (polls > maxPolls) { clearInterval(pollInterval); statusBar.className = 'fb-status error'; statusBar.textContent = 'Generation timed out'; if(btnFeedback) btnFeedback.disabled=false; if(btnScratch) btnScratch.disabled=false; return; }
            try {
              var pr = await fetch('/api/blog-article?id=' + articleId);
              var article = await pr.json();
              if (article.status === 'completed') {
                clearInterval(pollInterval);
                statusBar.className = 'fb-status success'; statusBar.textContent = 'Regeneration complete';
                if (textarea) textarea.value = '';
                if (btnFeedback) btnFeedback.disabled = false; if (btnScratch) btnScratch.disabled = false;
                var overlay = document.getElementById('article-modal-overlay');
                if (overlay) {
                  var iframe = overlay.querySelector('iframe');
                  if (iframe && article.article_html) iframe.srcdoc = article.article_html;
                  _resetArticleEditState();
                  var h2 = overlay.querySelector('.article-modal-header h2');
                  if (h2) h2.textContent = article.headline || article.keyword || '';
                  var metaSpans = overlay.querySelectorAll('.article-modal-meta span');
                  if (metaSpans.length > 0 && article.word_count) metaSpans[0].textContent = article.word_count + ' words';
                  var statusBadge = overlay.querySelector('.article-modal-status');
                  if (statusBadge) { statusBadge.className = 'article-modal-status completed'; statusBadge.textContent = 'Completed'; }
                  var historyList = document.getElementById('feedback-history-list');
                  if (historyList) { var history = article.feedback_history || []; historyList.innerHTML = history.length === 0 ? '<div class="fb-empty">No feedback yet</div>' : history.map(function(fb,i){return buildFeedbackCardHTML(fb,i);}).join(''); historyList.scrollTop = historyList.scrollHeight; }
                  _inlineComments = []; _commentIdCounter = 0; renderInlineComments(); _feedbackDrafts.delete(articleId);
                }
                setTimeout(function(){ statusBar.className = 'fb-status'; statusBar.textContent = ''; }, 8000);
              } else if (article.status === 'failed') {
                clearInterval(pollInterval); statusBar.className = 'fb-status error'; statusBar.textContent = article.error_message || 'Generation failed';
                if(btnFeedback) btnFeedback.disabled=false; if(btnScratch) btnScratch.disabled=false;
              }
            } catch(e) {}
          }, 3000);
        } else { throw new Error(data.error || 'Unknown error'); }
      } catch (err) {
        statusBar.className = 'fb-status error'; statusBar.textContent = err.message || 'Generation failed';
        if(btnFeedback) btnFeedback.disabled=false; if(btnScratch) btnScratch.disabled=false;
      }
    }

    async function handleApplyEdits(articleId) {
      if (_inlineComments.length === 0) return;
      var statusBar = document.getElementById('feedback-status-bar');
      var btnApply = document.getElementById('btn-apply-edits');
      var btnFeedback = document.getElementById('btn-regen-feedback');
      var btnScratch = document.getElementById('btn-regen-scratch');
      var edits = _inlineComments.map(function(ic){ return { passage_text: ic.text, comment: ic.comment }; });
      if (btnApply) btnApply.disabled = true; if (btnFeedback) btnFeedback.disabled = true; if (btnScratch) btnScratch.disabled = true;
      statusBar.className = 'fb-status loading'; statusBar.textContent = 'Applying edits...';
      try {
        var r = await fetch('/api/blog-article', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ article_id: articleId, edits: edits }) });
        var data = await r.json(); if (!r.ok) throw new Error(data.error || 'Unknown error');
        statusBar.className = 'fb-status success'; statusBar.textContent = 'Edits applied (' + (data.edits_applied || 0) + ')';
        var overlay = document.getElementById('article-modal-overlay');
        if (overlay && data.article_html) { var iframe = overlay.querySelector('iframe'); if (iframe) iframe.srcdoc = data.article_html; _resetArticleEditState(); }
        var historyList = document.getElementById('feedback-history-list');
        if (historyList && data.feedback_history) { var history = data.feedback_history; historyList.innerHTML = history.length === 0 ? '<div class="fb-empty">No feedback yet</div>' : history.map(function(fb,i){return buildFeedbackCardHTML(fb,i);}).join(''); historyList.scrollTop = historyList.scrollHeight; }
        _inlineComments = []; _commentIdCounter = 0; renderInlineComments(); _feedbackDrafts.delete(articleId);
        setTimeout(function(){ statusBar.className = 'fb-status'; statusBar.textContent = ''; }, 8000);
      } catch (err) {
        statusBar.className = 'fb-status error'; statusBar.textContent = 'Edit failed: ' + (err.message || '');
        setTimeout(function(){ statusBar.className = 'fb-status'; statusBar.textContent = ''; }, 8000);
      } finally { if(btnApply) btnApply.disabled=false; if(btnFeedback) btnFeedback.disabled=false; if(btnScratch) btnScratch.disabled=false; }
    }

    async function toggleEditorialApproval(btn) {
      const row = btn.closest('tr');
      const articleId = row.dataset.articleId;
      const isApproved = btn.classList.contains('approved');
      const newStatus = isApproved ? 'draft' : 'approved';

      btn.classList.add('loading');
      btn.textContent = '...';

      try {
        const res = await fetch('/api/blog-article', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ article_id: articleId, action: 'review_status', review_status: newStatus })
        });
        const data = await res.json();

        if (res.ok) {
          if (newStatus === 'approved') {
            btn.classList.add('approved');
            btn.textContent = 'Approved';
            row.classList.add('approved-row');
            // Update review badge
            row.querySelectorAll('td')[3].innerHTML = '<span style="display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#dcfce7;color:#166534">Approved</span>';
          } else {
            btn.classList.remove('approved');
            btn.textContent = 'Approve';
            row.classList.remove('approved-row');
            row.querySelectorAll('td')[3].innerHTML = '<span style="display:inline-block;padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500;background:#f3f4f6;color:#6b7280">Draft</span>';
          }
        } else {
          alert(data.error || 'Action failed');
          btn.textContent = isApproved ? 'Approved' : 'Approve';
        }
      } catch (err) {
        alert('Network error: ' + err.message);
        btn.textContent = isApproved ? 'Approved' : 'Approve';
      } finally {
        btn.classList.remove('loading');
      }
    }
  </script>
</body>
</html>`;
}

// ── GET: serve login or admin page ───────────────────────────────────
export async function GET(request: NextRequest) {
  const adminPassword = getAdminPassword();
  if (!adminPassword) {
    return new NextResponse("Admin not configured", { status: 403 });
  }

  // Handle logout
  if (request.nextUrl.searchParams.get("logout") === "1") {
    const res = NextResponse.redirect(new URL("/api/admin", request.url));
    res.cookies.set("admin_token", "", { maxAge: 0, path: "/" });
    return res;
  }

  if (!isAuthenticated(request)) {
    const showError = request.nextUrl.searchParams.get("error") === "1";
    const html = LOGIN_HTML.replace("__ERROR_CLASS__", showError ? "show" : "");
    return new NextResponse(html, {
      status: 401,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }

  // Fetch all opportunities via content-planning endpoint (server-side, bypass middleware)
  let opportunities: any[] = [];
  try {
    const baseUrl = request.nextUrl.origin;
    const cpRes = await fetch(`${baseUrl}/api/content-planning`, {
      headers: {
        Cookie: `dashboard_token=${process.env.DASHBOARD_PASSWORD || ""}`,
      },
    });
    if (cpRes.ok) {
      const cpData = await cpRes.json();
      opportunities = cpData.opportunities || [];
    }
  } catch (err) {
    console.error("Admin: failed to fetch content-planning:", err);
  }

  // Fetch approved URLs
  const supabase = getSupabase();
  let approvedUrls = new Set<string>();
  try {
    const { data } = await supabase
      .from("approved_opportunities")
      .select("source_url");
    if (data) {
      approvedUrls = new Set(data.map((r: any) => r.source_url));
    }
  } catch { /* table may not exist */ }

  // Fetch editorial articles (no source_item_id)
  let editorialArticles: any[] = [];
  try {
    const baseUrl = request.nextUrl.origin;
    const artRes = await fetch(`${baseUrl}/api/blog-article`, {
      headers: {
        Cookie: `dashboard_token=${process.env.DASHBOARD_PASSWORD || ""}`,
      },
    });
    if (artRes.ok) {
      const artData = await artRes.json();
      editorialArticles = (artData.articles || []).filter(
        (a: any) => !a.source_item_id
      );
    }
  } catch (err) {
    console.error("Admin: failed to fetch editorial articles:", err);
  }

  const html = adminPageHtml(opportunities, approvedUrls, editorialArticles);
  return new NextResponse(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

// ── POST: login, approve, unapprove ──────────────────────────────────
export async function POST(request: NextRequest) {
  const adminPassword = getAdminPassword();
  if (!adminPassword) {
    return NextResponse.json({ error: "Admin not configured" }, { status: 403 });
  }

  const contentType = request.headers.get("content-type") || "";

  // Handle form-encoded login
  if (contentType.includes("application/x-www-form-urlencoded")) {
    const formData = await request.formData();
    const action = formData.get("action") as string;

    if (action === "login") {
      const password = formData.get("password") as string;
      if (password === adminPassword) {
        const res = NextResponse.redirect(new URL("/api/admin", request.url), 303);
        res.cookies.set("admin_token", adminPassword, {
          httpOnly: true,
          sameSite: "lax",
          path: "/",
          maxAge: 60 * 60 * 24 * 7, // 7 days
        });
        return res;
      }
      return NextResponse.redirect(new URL("/api/admin?error=1", request.url), 303);
    }
  }

  // Handle JSON approve/unapprove actions
  if (!isAuthenticated(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const { action } = body;

  // ── Enrich topic via Gemini ──
  if (action === "enrich_topic") {
    const { topic, language } = body;
    if (!topic) {
      return NextResponse.json({ error: "Missing topic" }, { status: 400 });
    }
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: "GEMINI_API_KEY not configured" }, { status: 500 });
    }
    try {
      const genAI = new GoogleGenerativeAI(apiKey);
      const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });
      const lang = language === "en" ? "English" : "German";
      const prompt = `You are an SEO content strategist. Given the topic below, generate SEO metadata for a blog article in ${lang}.

Topic: "${topic}"

Respond with ONLY a JSON object (no markdown, no code fences) with these fields:
- "suggested_title": A compelling, SEO-optimized article title in ${lang}
- "keywords": An array of 5-8 relevant SEO keywords/phrases in ${lang}
- "search_intent": One of "Informational", "Navigational", "Transactional", or "Comparison"
- "content_brief": A 2-3 sentence content brief describing what the article should cover, in ${lang}`;

      const result = await model.generateContent(prompt);
      const text = result.response.text().trim();
      // Parse JSON from response (strip code fences if present)
      const jsonStr = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
      const parsed = JSON.parse(jsonStr);
      return NextResponse.json({
        ok: true,
        suggested_title: parsed.suggested_title || "",
        keywords: parsed.keywords || [],
        search_intent: parsed.search_intent || "Informational",
        content_brief: parsed.content_brief || "",
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Enrichment failed";
      console.error("Admin enrich_topic error:", err);
      return NextResponse.json({ ok: false, error: message }, { status: 500 });
    }
  }

  // ── Generate article from suggested topic ──
  if (action === "suggest_topic") {
    const { keyword, language } = body;
    if (!keyword) {
      return NextResponse.json({ error: "Missing keyword" }, { status: 400 });
    }
    try {
      const baseUrl = request.nextUrl.origin;
      const res = await fetch(`${baseUrl}/api/blog-article`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: `dashboard_token=${process.env.DASHBOARD_PASSWORD || ""}`,
        },
        body: JSON.stringify({ keyword, language: language || "de" }),
      });
      const data = await res.json();
      if (!res.ok) {
        return NextResponse.json({ ok: false, error: data.error || "Article creation failed" }, { status: res.status });
      }
      return NextResponse.json({ ok: true, article_id: data.id, status: data.status });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      return NextResponse.json({ ok: false, error: message }, { status: 500 });
    }
  }

  // ── Approve / Unapprove ──
  const { source_url, source_item_id } = body;

  if (!source_url) {
    return NextResponse.json({ error: "Missing source_url" }, { status: 400 });
  }

  const supabase = getSupabase();

  if (action === "approve") {
    // Check current count
    const { data: existing } = await supabase
      .from("approved_opportunities")
      .select("id");
    const currentCount = existing?.length || 0;

    if (currentCount >= MAX_APPROVED) {
      return NextResponse.json(
        { ok: false, error: `Maximum ${MAX_APPROVED} approvals reached` },
        { status: 400 }
      );
    }

    const { error } = await supabase
      .from("approved_opportunities")
      .upsert(
        { source_url, source_item_id: source_item_id || null },
        { onConflict: "source_url" }
      );

    if (error) {
      console.error("Admin approve error:", error);
      return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({ ok: true, action: "approved" });
  }

  if (action === "unapprove") {
    const { error } = await supabase
      .from("approved_opportunities")
      .delete()
      .eq("source_url", source_url);

    if (error) {
      console.error("Admin unapprove error:", error);
      return NextResponse.json({ ok: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({ ok: true, action: "unapproved" });
  }

  return NextResponse.json({ error: "Invalid action" }, { status: 400 });
}

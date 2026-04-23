# How Articles Flow from Admin to Dashboard

## The Short Version

Articles created on the admin page are **invisible** on the public dashboard until their `review_status` is set to `approved`. The dashboard fetches articles with `?approved_only=true`, which filters to only `review_status === "approved"` rows.

## Step-by-Step Flow

```
 ADMIN PAGE (/api/admin)                         DATABASE                        DASHBOARD
 ─────────────────────                           ────────                        ─────────

 1. Suggest a Topic                               blog_articles
    → Gemini enriches SEO metadata                ┌──────────────────┐
                                                  │ status: pending  │
 2. Click "Generate Article"  ──── POST ────────▶ │ review: draft    │
    → Row created, generation starts async        │ keyword: "..."   │
                                                  └────────┬─────────┘
                                                           │ background
                                                           ▼
                                                  ┌──────────────────┐
                                                  │ status: completed│
 3. Click "View" on completed article             │ review: draft    │  ◀── NOT visible
    → Article modal opens with full content       │ article_html: ...│      on dashboard
                                                  └────────┬─────────┘
                                                           │
 4. Review, edit, regenerate as needed                     │
    → Inline comments, feedback, HTML edits                │
                                                           │
 5. Set review status to "Approved"               ┌──────────────────┐
    → Via modal dropdown or table button  ──────▶ │ status: completed│
                                                  │ review: approved │  ◀── NOW visible
                                                  │ article_html: ...│      on dashboard
                                                  └────────┬─────────┘
                                                           │
                                              GET /api/blog-article
                                              ?approved_only=true
                                                           │
                                                           ▼
                                                  Dashboard "Articles" tab
                                                  renders article cards
```

## Key Mechanism

The dashboard's Articles tab calls:

```
GET /api/blog-article?approved_only=true
```

The API handler filters the response:

```typescript
if (approvedOnly) {
  articles = articles.filter(a => a.review_status === "approved");
}
```

Only articles with `review_status === "approved"` are returned. All other statuses (`draft`, `review`, `published`) are excluded from the public dashboard view.

## Review Status Lifecycle

| Status | Where visible | Meaning |
|--------|--------------|---------|
| `draft` | Admin only | Default. Article created but not reviewed. |
| `review` | Admin only | Marked for team review. |
| `approved` | Admin + Dashboard | Approved for public display. |
| `published` | Admin only | Future use (not currently filtered for in dashboard). |

## Files Involved

| File | Role |
|------|------|
| `dashboard/app/api/admin/route.ts` | Admin UI: topic suggestion, article creation, review status changes |
| `dashboard/app/api/blog-article/route.ts` | Article CRUD + `approved_only` filter (lines 53–67) |
| `dashboard/lib/article-generator.ts` | Gemini generation, regeneration, inline edits |
| `styles/dashboard_template.html` | Dashboard Articles tab fetches with `?approved_only=true` (line 7149) |
| `blog_articles` table | Stores `review_status` column that gates visibility |

import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";
import { renderArticleHtml } from "@/lib/html-renderer";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL;

async function proxyToBackend(path: string, method: string, body: any): Promise<Response> {
  return fetch(`${BACKEND_URL}/api/v1/blog${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function GET(request: NextRequest) {
  try {
    const supabase = getSupabase();
    const { searchParams } = new URL(request.url);
    const id = searchParams.get("id");
    const comments = searchParams.get("comments");
    const sourceItemId = searchParams.get("source_item_id");

    if (id && comments === "true") {
      const { data, error } = await supabase
        .from("article_comments")
        .select("*")
        .eq("article_id", id)
        .order("created_at", { ascending: true });
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json({ comments: data || [] });
    }

    if (id) {
      // Proxy to Python backend when available (includes generation_stage)
      if (BACKEND_URL) {
        try {
          const backendRes = await fetch(`${BACKEND_URL}/api/v1/blog/articles/${id}`);
          if (backendRes.ok) {
            const data = await backendRes.json();
            return NextResponse.json(data);
          }
        } catch { /* fall through to direct Supabase */ }
      }
      const { data, error } = await supabase
        .from("blog_articles")
        .select("*")
        .eq("id", id)
        .single();
      if (error) return NextResponse.json({ error: "Article not found" }, { status: 404 });
      return NextResponse.json(data, {
        headers: { "Cache-Control": "private, no-cache, no-store" },
      });
    }

    if (sourceItemId) {
      const { data } = await supabase
        .from("blog_articles")
        .select("id, status, headline")
        .eq("source_item_id", sourceItemId)
        .limit(1);
      const articles = data || [];
      if (articles.length > 0) {
        return NextResponse.json({
          exists: true,
          id: articles[0].id,
          status: articles[0].status,
          headline: articles[0].headline,
        });
      }
      return NextResponse.json({ exists: false });
    }

    // List articles
    const approvedOnly = searchParams.get("approved_only") === "true";
    const { data, error } = await supabase
      .from("blog_articles")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(50);
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });

    let articles = data || [];

    if (approvedOnly) {
      articles = articles.filter(
        (a: any) => a.review_status === "approved"
      );
    }

    // Fetch distinct comment authors per article
    const articleIds = articles.map((a: any) => a.id);
    let commentAuthorsMap: Record<string, string[]> = {};
    if (articleIds.length > 0) {
      const { data: comments } = await supabase
        .from("article_comments")
        .select("article_id, author")
        .in("article_id", articleIds);
      if (comments) {
        for (const c of comments) {
          if (!c.author) continue;
          if (!commentAuthorsMap[c.article_id]) commentAuthorsMap[c.article_id] = [];
          if (!commentAuthorsMap[c.article_id].includes(c.author)) {
            commentAuthorsMap[c.article_id].push(c.author);
          }
        }
      }
    }

    articles = articles.map((a: any) => ({
      ...a,
      comment_authors: commentAuthorsMap[a.id] || [],
    }));

    return NextResponse.json({ articles }, {
      status: 200,
      headers: { "Cache-Control": "private, no-cache, no-store" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Article generation backend not configured" },
        { status: 503 }
      );
    }

    const body = await request.json();
    const { action } = body;

    // Action-based routing for image and batch operations
    if (action === "generate_hero_image") {
      if (!body.article_id) {
        return NextResponse.json({ error: "article_id is required" }, { status: 400 });
      }
      const res = await fetch(
        `${BACKEND_URL}/api/v1/blog/articles/${body.article_id}/generate-hero-image`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) return NextResponse.json(data, { status: res.status });
      return NextResponse.json(data);
    }

    if (action === "attach_product_images") {
      if (!body.article_id) {
        return NextResponse.json({ error: "article_id is required" }, { status: 400 });
      }
      const res = await fetch(
        `${BACKEND_URL}/api/v1/blog/articles/${body.article_id}/attach-product-images`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) return NextResponse.json(data, { status: res.status });
      return NextResponse.json(data);
    }

    if (action === "regenerate_batch") {
      const res = await fetch(
        `${BACKEND_URL}/api/v1/blog/articles/regenerate-batch`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) return NextResponse.json(data, { status: res.status });
      return NextResponse.json(data);
    }

    // Default: article creation
    const { source_item_id, keyword, language, word_count, social_context } = body;

    if (!keyword) {
      return NextResponse.json({ error: "keyword is required" }, { status: 400 });
    }

    try {
      const backendRes = await proxyToBackend("/articles", "POST", {
        keyword,
        source_item_id: source_item_id || null,
        language: language || "de",
        word_count: word_count || 1500,
        social_context: social_context || null,
      });
      const data = await backendRes.json();
      return NextResponse.json(data, { status: backendRes.status });
    } catch (proxyErr) {
      console.error("Backend proxy failed:", proxyErr);
      return NextResponse.json(
        { error: "Article generation backend unavailable" },
        { status: 503 }
      );
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PUT(request: NextRequest) {
  try {
    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Article generation backend not configured" },
        { status: 503 }
      );
    }

    const body = await request.json();
    const { article_id, feedback, from_scratch } = body;

    if (!article_id) {
      return NextResponse.json({ error: "article_id is required" }, { status: 400 });
    }

    try {
      const backendRes = await proxyToBackend("/articles", "PUT", {
        article_id,
        feedback: feedback || null,
        from_scratch: from_scratch || false,
      });
      const data = await backendRes.json();
      return NextResponse.json(data, { status: backendRes.status });
    } catch (proxyErr) {
      console.error("Backend proxy failed:", proxyErr);
      return NextResponse.json(
        { error: "Article generation backend unavailable" },
        { status: 503 }
      );
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const supabase = getSupabase();
    const body = await request.json();
    const { article_id, action } = body;

    if (!article_id) {
      return NextResponse.json({ error: "article_id is required" }, { status: 400 });
    }

    // Review status
    if (action === "review_status") {
      const { review_status } = body;
      const validStatuses = ["draft", "review", "approved", "published"];
      if (!validStatuses.includes(review_status)) {
        return NextResponse.json(
          { error: `Invalid review_status. Must be one of: ${validStatuses.join(", ")}` },
          { status: 400 }
        );
      }

      // If approving and backend is available, proxy to Python backend
      // so the review agent gets triggered to extract learnings
      if (review_status === "approved" && BACKEND_URL) {
        try {
          const backendRes = await fetch(
            `${BACKEND_URL}/api/v1/social-listening/blog-articles/${article_id}/review-status`,
            {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ review_status }),
            }
          );
          if (backendRes.ok) {
            const backendData = await backendRes.json();
            // Fetch the full updated article to return consistent shape
            const { data } = await supabase
              .from("blog_articles")
              .select("*")
              .eq("id", article_id)
              .single();
            return NextResponse.json({
              ...(data || backendData),
              review_agent_triggered: true,
            });
          }
          // Fall through to direct Supabase update if backend fails
        } catch {
          // Fall through to direct Supabase update
        }
      }

      const { data, error } = await supabase
        .from("blog_articles")
        .update({ review_status, updated_at: new Date().toISOString() })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json({ ...data, review_agent_triggered: false });
    }

    // Publish status
    if (action === "publish_status") {
      const { publish_status, publish_date, publish_url } = body;
      const validStatuses = ["unpublished", "scheduled", "published"];
      if (!validStatuses.includes(publish_status)) {
        return NextResponse.json(
          { error: `Invalid publish_status. Must be one of: ${validStatuses.join(", ")}` },
          { status: 400 }
        );
      }
      const updateFields: Record<string, any> = {
        publish_status,
        updated_at: new Date().toISOString(),
      };
      if (publish_date !== undefined) updateFields.publish_date = publish_date || null;
      if (publish_url !== undefined) updateFields.publish_url = publish_url || null;
      const { data, error } = await supabase
        .from("blog_articles")
        .update(updateFields)
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Reset HTML — re-render from article_json, clear html_custom
    if (action === "reset_html") {
      const { data: article, error: fetchErr } = await supabase
        .from("blog_articles")
        .select("article_json, language, social_context, author_id")
        .eq("id", article_id)
        .single();
      if (fetchErr || !article) {
        return NextResponse.json({ error: "Article not found" }, { status: 404 });
      }
      if (!article.article_json) {
        return NextResponse.json({ error: "No article data to render from" }, { status: 400 });
      }

      // Fetch author if assigned
      let author = null;
      if (article.author_id) {
        const { data: authorData } = await supabase
          .from("blog_authors")
          .select("name, title, bio, image_url, credentials, linkedin_url")
          .eq("id", article.author_id)
          .single();
        author = authorData;
      }

      const articleHtml = renderArticleHtml({
        article: article.article_json,
        companyName: "Beurer",
        companyUrl: "https://www.beurer.com",
        language: article.language || "de",
        category: article.social_context?.category || "",
        author,
      });

      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          article_html: articleHtml,
          html_custom: false,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Add comment
    // Note: article_comments table requires a selected_text column (nullable text)
    // to support anchoring comments to a specific text passage.
    if (action === "add_comment") {
      const { author, comment_text } = body;
      const selected_text = body.selected_text || null;
      if (!comment_text) {
        return NextResponse.json({ error: "comment_text is required" }, { status: 400 });
      }
      const { data, error } = await supabase
        .from("article_comments")
        .insert({ article_id, author: author || "Reviewer", comment_text, selected_text })
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Delete comment
    if (action === "delete_comment") {
      const { comment_id } = body;
      if (!comment_id) {
        return NextResponse.json({ error: "comment_id is required" }, { status: 400 });
      }
      const { error } = await supabase
        .from("article_comments")
        .delete()
        .eq("id", comment_id)
        .eq("article_id", article_id);
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json({ success: true });
    }

    // Assign author
    if (action === "assign_author") {
      const { author_id } = body;
      const { data, error } = await supabase
        .from("blog_articles")
        .update({ author_id: author_id || null, updated_at: new Date().toISOString() })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Save HTML
    if (action === "save_html") {
      const { article_html } = body;
      if (!article_html) {
        return NextResponse.json({ error: "article_html is required" }, { status: 400 });
      }
      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          article_html,
          html_custom: true,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Remove image — detach from article_json, re-render HTML
    if (action === "remove_image") {
      const { slot } = body;
      const validSlots = ["image_01", "image_02", "image_03"];
      if (!validSlots.includes(slot)) {
        return NextResponse.json(
          { error: `Invalid slot. Must be one of: ${validSlots.join(", ")}` },
          { status: 400 }
        );
      }

      const { data: article, error: fetchErr } = await supabase
        .from("blog_articles")
        .select("article_json, language, social_context, author_id")
        .eq("id", article_id)
        .single();
      if (fetchErr || !article) {
        return NextResponse.json({ error: "Article not found" }, { status: 404 });
      }
      if (!article.article_json) {
        return NextResponse.json({ error: "No article data" }, { status: 400 });
      }

      // Clear the image fields
      const updatedJson = { ...article.article_json };
      updatedJson[`${slot}_url`] = "";
      updatedJson[`${slot}_alt_text`] = "";

      // Fetch author if assigned
      let author = null;
      if (article.author_id) {
        const { data: authorData } = await supabase
          .from("blog_authors")
          .select("name, title, bio, image_url, credentials, linkedin_url")
          .eq("id", article.author_id)
          .single();
        author = authorData;
      }

      // Re-render HTML
      const articleHtml = renderArticleHtml({
        article: updatedJson,
        companyName: "Beurer",
        companyUrl: "https://www.beurer.com",
        language: article.language || "de",
        category: article.social_context?.category || "",
        author,
      });

      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          article_json: updatedJson,
          article_html: articleHtml,
          html_custom: false,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Set golden version — mark a specific version (or current) as the approved baseline
    if (action === "set_golden_version") {
      const { version_index, marked_by } = body;
      if (version_index === undefined) {
        return NextResponse.json({ error: "version_index is required" }, { status: 400 });
      }

      const { data: article, error: fetchErr } = await supabase
        .from("blog_articles")
        .select("article_html, article_json, word_count, headline, feedback_history")
        .eq("id", article_id)
        .single();
      if (fetchErr || !article) {
        return NextResponse.json({ error: "Article not found" }, { status: 404 });
      }

      let goldenHtml: string;
      let goldenJson: Record<string, unknown> | null;
      let goldenWordCount: number;
      let goldenVersion: number;

      if (version_index === -1) {
        goldenHtml = article.article_html;
        goldenJson = article.article_json;
        goldenWordCount = article.word_count || 0;
        const snapshots = (article.feedback_history || []).filter(
          (e: { type: string }) => e.type === "snapshot"
        );
        goldenVersion = snapshots.length + 1;
      } else {
        const snapshots = (article.feedback_history || []).filter(
          (e: { type: string }) => e.type === "snapshot"
        );
        const snap = snapshots[version_index];
        if (!snap || !snap.article_html) {
          return NextResponse.json({ error: "Snapshot not found or has no HTML" }, { status: 400 });
        }
        goldenHtml = snap.article_html;
        goldenJson = snap.article_json || null;
        goldenWordCount = snap.word_count || 0;
        goldenVersion = snap.version || version_index + 1;
      }

      const goldenData = {
        version: goldenVersion,
        marked_at: new Date().toISOString(),
        marked_by: marked_by || "Reviewer",
        article_html: goldenHtml,
        article_json: goldenJson,
        word_count: goldenWordCount,
      };

      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          golden_version: goldenData,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Restore golden version — revert article to the approved baseline
    if (action === "restore_golden_version") {
      const { data: article, error: fetchErr } = await supabase
        .from("blog_articles")
        .select("golden_version, article_html, article_json, headline, word_count, feedback_history")
        .eq("id", article_id)
        .single();
      if (fetchErr || !article) {
        return NextResponse.json({ error: "Article not found" }, { status: 404 });
      }
      if (!article.golden_version) {
        return NextResponse.json({ error: "No golden version set" }, { status: 400 });
      }

      const history = article.feedback_history || [];
      const snapshots = history.filter((e: { type: string }) => e.type === "snapshot");
      const currentSnapshot = {
        type: "snapshot",
        version: snapshots.length + 1,
        headline: article.headline || "",
        article_html: article.article_html,
        article_json: article.article_json,
        word_count: article.word_count,
        created_at: new Date().toISOString(),
        reason: "pre_golden_restore",
      };
      const updatedHistory = [...history, currentSnapshot];

      const golden = article.golden_version;
      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          article_html: golden.article_html,
          article_json: golden.article_json || article.article_json,
          word_count: golden.word_count || article.word_count,
          html_custom: false,
          feedback_history: updatedHistory,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Clear golden version marker
    if (action === "clear_golden_version") {
      const { data, error } = await supabase
        .from("blog_articles")
        .update({
          golden_version: null,
          updated_at: new Date().toISOString(),
        })
        .eq("id", article_id)
        .select()
        .single();
      if (error) return NextResponse.json({ error: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    // Inline edits
    const { edits } = body;
    if (!edits || !Array.isArray(edits) || edits.length === 0) {
      return NextResponse.json({ error: "edits array is required" }, { status: 400 });
    }

    if (!BACKEND_URL) {
      return NextResponse.json(
        { error: "Article generation backend not configured" },
        { status: 503 }
      );
    }

    try {
      const backendRes = await proxyToBackend("/articles/inline-edits", "POST", {
        article_id,
        edits,
      });
      const data = await backendRes.json();
      return NextResponse.json(data, { status: backendRes.status });
    } catch (proxyErr) {
      console.error("Backend proxy failed for inline edits:", proxyErr);
      return NextResponse.json(
        { error: "Article generation backend unavailable" },
        { status: 503 }
      );
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest) {
  const supabase = getSupabase();
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return NextResponse.json({ error: "id parameter required" }, { status: 400 });
  }

  // Fetch the article to validate it's a pending custom topic
  const { data: article, error: fetchError } = await supabase
    .from("blog_articles")
    .select("id, source_item_id, status")
    .eq("id", id)
    .single();

  if (fetchError || !article) {
    return NextResponse.json({ error: "Article not found" }, { status: 404 });
  }

  if (article.source_item_id !== null) {
    return NextResponse.json(
      { error: "Cannot delete system-detected topics" },
      { status: 403 }
    );
  }

  if (article.status !== "pending") {
    return NextResponse.json(
      { error: "Cannot delete topics that have been generated" },
      { status: 403 }
    );
  }

  const { error: deleteError } = await supabase
    .from("blog_articles")
    .delete()
    .eq("id", id);

  if (deleteError) {
    return NextResponse.json({ error: deleteError.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}

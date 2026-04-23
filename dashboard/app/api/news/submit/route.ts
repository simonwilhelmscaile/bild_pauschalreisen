import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";
import { GoogleGenerativeAI } from "@google/generative-ai";

const GEMINI_MODEL = "gemini-2.0-flash";

function getGeminiKey(): string {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new Error("GEMINI_API_KEY not set");
  return key;
}

/** Scrape a URL and extract text content, title, author, date. */
async function scrapeUrl(url: string): Promise<{
  title: string;
  content: string;
  author: string | null;
  publishedDate: string | null;
}> {
  const res = await fetch(url, {
    headers: {
      "User-Agent":
        "Mozilla/5.0 (compatible; SCAILEBot/1.0; +https://scaile.tech)",
      Accept: "text/html,application/xhtml+xml",
    },
    signal: AbortSignal.timeout(15000),
  });

  if (!res.ok) throw new Error(`Failed to fetch URL: ${res.status}`);

  const html = await res.text();

  // Extract title from <title> or og:title
  const titleMatch =
    html.match(/<meta[^>]*property="og:title"[^>]*content="([^"]*)"/) ||
    html.match(/<title[^>]*>([^<]*)<\/title>/);
  const title = titleMatch?.[1]?.trim() || url;

  // Extract author
  const authorMatch =
    html.match(/<meta[^>]*name="author"[^>]*content="([^"]*)"/) ||
    html.match(/<meta[^>]*property="article:author"[^>]*content="([^"]*)"/) ||
    html.match(/"author":\s*"([^"]*)"/);
  const author = authorMatch?.[1]?.trim() || null;

  // Extract publish date
  const dateMatch =
    html.match(
      /<meta[^>]*property="article:published_time"[^>]*content="([^"]*)"/
    ) ||
    html.match(/<time[^>]*datetime="([^"]*)"/) ||
    html.match(/"datePublished":\s*"([^"]*)"/);
  const publishedDate = dateMatch?.[1]?.trim() || null;

  // Strip HTML to text
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  const bodyHtml = bodyMatch?.[1] || html;
  const text = bodyHtml
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<nav[\s\S]*?<\/nav>/gi, "")
    .replace(/<footer[\s\S]*?<\/footer>/gi, "")
    .replace(/<header[\s\S]*?<\/header>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#?\w+;/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  // Take first ~4000 chars for summarization
  const content = text.slice(0, 4000);

  return { title, content, author, publishedDate };
}

/** Use Gemini to summarize the article content. */
async function summarizeArticle(
  title: string,
  content: string
): Promise<{ summary: string; topics: string[] }> {
  const genAI = new GoogleGenerativeAI(getGeminiKey());
  const model = genAI.getGenerativeModel({ model: GEMINI_MODEL });

  const prompt = `Summarize this article in 2-3 sentences (max 280 characters). Also extract up to 5 topic tags relevant to SEO, marketing, digital commerce, or the health/wellness industry.

Title: ${title}

Content: ${content.slice(0, 3000)}

Respond in JSON format:
{"summary": "...", "topics": ["tag1", "tag2"]}`;

  const result = await model.generateContent(prompt);
  const text = result.response.text();

  try {
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        summary: parsed.summary || content.slice(0, 280),
        topics: Array.isArray(parsed.topics) ? parsed.topics.slice(0, 5) : [],
      };
    }
  } catch {
    // fallback
  }

  return { summary: content.slice(0, 280), topics: [] };
}

/**
 * POST /api/news/submit
 *
 * Body: { url: string, submitted_by?: string }
 *
 * Scrapes the URL, summarizes with Gemini, saves to social_items
 * with crawler_tool="curated".
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const url: string = body.url;
    const submittedBy: string = body.submitted_by || "Team";

    if (!url || typeof url !== "string") {
      return NextResponse.json(
        { error: "URL is required" },
        { status: 400 }
      );
    }

    // Validate URL format
    try {
      new URL(url);
    } catch {
      return NextResponse.json(
        { error: "Invalid URL format" },
        { status: 400 }
      );
    }

    // Check for duplicate
    const supabase = getSupabase();
    const { data: existing } = await supabase
      .from("social_items")
      .select("id")
      .eq("source_url", url)
      .limit(1);

    if (existing && existing.length > 0) {
      return NextResponse.json(
        { error: "This URL has already been submitted" },
        { status: 409 }
      );
    }

    // Scrape
    const scraped = await scrapeUrl(url);

    // Summarize
    const { summary, topics } = await summarizeArticle(
      scraped.title,
      scraped.content
    );

    // Extract domain as source name
    const domain = new URL(url).hostname.replace("www.", "");

    // Save to social_items
    const now = new Date().toISOString();
    const { data: saved, error: saveError } = await supabase
      .from("social_items")
      .insert({
        source: domain,
        source_url: url,
        title: scraped.title,
        content: summary,
        posted_at: scraped.publishedDate || now.split("T")[0],
        crawler_tool: "curated",
        raw_data: {
          curated: true,
          submitted_by: submittedBy,
          submitted_at: now,
          original_author: scraped.author,
          full_content: scraped.content.slice(0, 2000),
          topic_tags: topics,
          exa_query: null,
        },
        keywords: topics,
        // Use the dev tenant_id (Beurer)
        tenant_id: "81f64a00-4668-4f59-9056-d9d9615d3fbb",
      })
      .select("id, title, source, source_url, posted_at")
      .single();

    if (saveError) {
      console.error("Save error:", saveError.message);
      return NextResponse.json(
        { error: saveError.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      article: {
        id: saved.id,
        title: saved.title,
        source: saved.source,
        url: saved.source_url,
        posted_at: saved.posted_at,
        summary,
        topics,
        submitted_by: submittedBy,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("News submit error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

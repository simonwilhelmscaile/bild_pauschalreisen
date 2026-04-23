import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";
import { buildNewsData } from "@/lib/aggregator/news";
import type { SocialItem } from "@/lib/aggregator/types";

// Simple in-memory cache (15-min TTL)
const cache = new Map<string, { data: any; ts: number }>();
const CACHE_TTL = 15 * 60 * 1000;

/**
 * GET /api/news?days=7
 *
 * Standalone news endpoint — fetches Exa-crawled articles,
 * scores them, and returns tiered results.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const days = parseInt(searchParams.get("days") || "7", 10);

    const cacheKey = `news-${days}`;
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      return NextResponse.json(cached.data, {
        headers: { "Cache-Control": "private, max-age=300" },
      });
    }

    const supabase = getSupabase();

    // Date range
    const now = new Date();
    const start = new Date(now);
    start.setDate(start.getDate() - days);
    const startDate = start.toISOString().split("T")[0];

    // Fetch Exa-crawled + curated items (include NULL posted_at — many Exa articles lack dates)
    const { data: items, error } = await supabase
      .from("social_items")
      .select("id, source, source_url, title, content, posted_at, raw_data, relevance_score, keywords, crawler_tool")
      .in("crawler_tool", ["exa", "curated"])
      .or(`posted_at.gte.${startDate},posted_at.is.null`)
      .order("posted_at", { ascending: false, nullsFirst: false })
      .limit(200);

    if (error) {
      console.error("News query error:", error.message);
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    console.log(`News: fetched ${(items || []).length} items from DB`);
    const newsData = buildNewsData((items || []) as SocialItem[]);
    console.log(`News: buildNewsData produced ${newsData.total} articles`);

    cache.set(cacheKey, { data: newsData, ts: Date.now() });

    return NextResponse.json(newsData, {
      headers: { "Cache-Control": "private, max-age=300" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("News API error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

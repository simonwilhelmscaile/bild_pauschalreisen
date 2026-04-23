import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

const EXA_API_URL = "https://api.exa.ai/search";

const NEWS_QUERIES = [
  "SEO latest developments and algorithm updates",
  "AEO answer engine optimization strategies",
  "GEO generative engine optimization research",
  "Google AI Overviews impact on search",
  "AI search optimization for brands",
  "zero-click searches AI overviews",
  "SEO content strategy AI era",
  "Beurer news latest developments",
  "Beurer product launch announcement",
  "health devices wellness market trends news",
  "blood pressure monitor TENS device market trends consumer news",
];

const CURATED_DOMAINS = [
  "searchengineland.com",
  "searchenginejournal.com",
  "seroundtable.com",
  "developers.google.com",
  "blog.google",
  "semrush.com",
  "ahrefs.com",
  "moz.com",
  "firstpagesage.com",
  "evergreen.media",
  "seo-suedwest.de",
  "sistrix.com",
  "backlinko.com",
  "t3n.de",
  "marketingdive.com",
  "fatjoe.com",
  "usercentrics.com",
  "conductor.com",
];

const SOURCE_NAMES: Record<string, string> = {
  "searchengineland.com": "Search Engine Land",
  "searchenginejournal.com": "Search Engine Journal",
  "seroundtable.com": "Search Engine Roundtable",
  "developers.google.com": "Google Search Central",
  "blog.google": "Google Blog",
  "semrush.com": "Semrush",
  "ahrefs.com": "Ahrefs",
  "moz.com": "Moz",
  "firstpagesage.com": "First Page Sage",
  "evergreen.media": "Evergreen Media",
  "seo-suedwest.de": "SEO Südwest",
  "sistrix.com": "SISTRIX",
  "backlinko.com": "Backlinko",
  "t3n.de": "t3n",
  "marketingdive.com": "Marketing Dive",
  "fatjoe.com": "FatJoe",
  "usercentrics.com": "Usercentrics",
  "conductor.com": "Conductor",
  "research.google": "Google Research",
  "ai.google": "Google AI",
};

/** Generic SEO queries get domain-restricted; tenant-specific ones search broadly. */
const GENERIC_PREFIXES = ["seo ", "aeo ", "geo ", "google ai", "zero-click", "ai search"];
function isGenericQuery(q: string): boolean {
  const lower = q.toLowerCase();
  return GENERIC_PREFIXES.some((p) => lower.startsWith(p));
}

function resolveSource(url: string): string {
  try {
    const domain = new URL(url).hostname.replace("www.", "");
    return SOURCE_NAMES[domain] || domain;
  } catch {
    return "unknown";
  }
}

/**
 * POST /api/news/fetch-exa
 *
 * Fetches news from Exa.ai and saves to social_items.
 * Body: { api_key?: string, days_back?: number, max_queries?: number }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}));
    const apiKey = body.api_key || process.env.EXA_API_KEY;
    const daysBack = body.days_back || 7;
    const maxQueries = body.max_queries || NEWS_QUERIES.length;

    if (!apiKey) {
      return NextResponse.json(
        { error: "No EXA_API_KEY provided" },
        { status: 400 }
      );
    }

    const supabase = getSupabase();

    // Date range
    const now = new Date();
    const start = new Date(now);
    start.setDate(start.getDate() - daysBack);
    const startStr = start.toISOString();
    const endStr = now.toISOString();

    const queries = NEWS_QUERIES.slice(0, maxQueries);
    const seenUrls = new Set<string>();
    const allItems: any[] = [];
    const errors: string[] = [];

    for (const query of queries) {
      try {
        const domains = isGenericQuery(query) ? CURATED_DOMAINS : undefined;

        const payload: any = {
          query,
          numResults: 10,
          type: "auto",
          startPublishedDate: startStr,
          endPublishedDate: endStr,
          contents: {
            text: { maxCharacters: 3000 },
            summary: true,
          },
        };
        if (domains) {
          payload.includeDomains = domains;
        }

        const res = await fetch(EXA_API_URL, {
          method: "POST",
          headers: {
            "x-api-key": apiKey,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
          signal: AbortSignal.timeout(30000),
        });

        if (!res.ok) {
          const errText = await res.text().catch(() => "");
          errors.push(`Query "${query}": ${res.status} ${errText.slice(0, 200)}`);
          continue;
        }

        const data = await res.json();
        const results = data.results || [];

        for (const result of results) {
          const url = result.url;
          if (!url || seenUrls.has(url)) continue;
          seenUrls.add(url);

          const text = result.text || "";
          if (text.length < 50) continue;

          const published = result.publishedDate || "";
          const postedAt = published ? published.split("T")[0] : null;
          const source = resolveSource(url);

          allItems.push({
            source,
            source_url: url,
            title: result.title || "",
            content: text,
            posted_at: postedAt,
            crawler_tool: "exa",
            raw_data: {
              exa_score: result.score || null,
              exa_query: query,
              exa_summary: result.summary || null,
              author: result.author || null,
              published_date: published,
            },
          });
        }
      } catch (e) {
        errors.push(
          `Query "${query}": ${e instanceof Error ? e.message : "unknown"}`
        );
      }
    }

    // Save to Supabase (skip duplicates by source_url)
    let saved = 0;
    let skipped = 0;

    for (const item of allItems) {
      // Check duplicate
      const { data: existing } = await supabase
        .from("social_items")
        .select("id")
        .eq("source_url", item.source_url)
        .limit(1);

      if (existing && existing.length > 0) {
        skipped++;
        continue;
      }

      const { error: saveErr } = await supabase
        .from("social_items")
        .insert(item);

      if (saveErr) {
        errors.push(`Save "${item.title?.slice(0, 40)}": ${saveErr.message}`);
      } else {
        saved++;
      }
    }

    return NextResponse.json({
      success: true,
      queries_run: queries.length,
      items_found: allItems.length,
      saved,
      skipped_duplicates: skipped,
      errors: errors.length > 0 ? errors : undefined,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Exa fetch error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

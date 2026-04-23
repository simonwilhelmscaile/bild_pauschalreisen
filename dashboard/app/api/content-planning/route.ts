import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";
import { INTENT_OPP_WEIGHTS } from "@/lib/constants";

// 5-minute in-memory cache
let cached: { data: any; ts: number } | null = null;
const CACHE_TTL = 5 * 60 * 1000;

// Same constants as content-opportunities.ts
const PREFERRED_SOURCES = new Set([
  "gutefrage", "reddit", "health_forums", "diabetes_forum",
  "endometriose", "rheuma_liga", "onmeda",
]);
const EMOTION_BOOST_SET = new Set(["frustration", "confusion", "anxiety"]);

const ITEM_FIELDS = [
  "id", "title", "content", "source", "source_url", "category",
  "relevance_score", "device_relevance_score", "content_opportunity",
  "intent", "emotion", "answer_count", "keywords", "key_insight",
  "product_mentions", "raw_data", "resolved_source",
].join(", ");

/** Score an item using the same 0-10 formula as the TS aggregator. */
function scoreItem(item: any): number {
  const relevance = item.relevance_score || 0;
  const deviceRelevance = item.device_relevance_score || 0;
  const llmSignal = item.content_opportunity ? 1.0 : 0;
  const intentWeight = INTENT_OPP_WEIGHTS[item.intent || ""] ?? 0;
  const answerCount = item.answer_count || 0;
  const unansweredBoost = answerCount === 0 ? 1.0 : answerCount === 1 ? 0.5 : 0;
  const emotionBoost = EMOTION_BOOST_SET.has(item.emotion || "") ? 0.7 : 0;
  const sourceBoost = PREFERRED_SOURCES.has(item.source || "") ? 0.5 : 0;

  const raw = item.raw_data || {};
  const src = item.source || "";
  let engagementRaw = 0;
  if (src === "reddit") engagementRaw = (raw.score || 0) + (raw.num_comments || 0);
  else if (src === "youtube") engagementRaw = raw.likes ?? 0;
  else if (src === "youtube_transcript") engagementRaw = raw.views ?? raw.likes ?? 0;
  else if (src === "tiktok" || src === "instagram") engagementRaw = raw.likes ?? raw.plays ?? 0;
  const engagementBoost = Math.min(engagementRaw / 50, 1.0);

  return Math.round((
    llmSignal * 3.0 +
    intentWeight * 2.0 +
    relevance * 1.5 +
    deviceRelevance * 1.0 +
    unansweredBoost * 1.0 +
    emotionBoost * 0.5 +
    sourceBoost * 0.5 +
    engagementBoost * 0.5
  ) * 10) / 10;
}

function displaySource(item: any): string {
  return item.resolved_source || item.source || "";
}

const MIN_GAP_SCORE = 2.0;
const MAX_OPPORTUNITIES = 50;

export async function GET(request: NextRequest) {
  try {
    const approvedOnly = request.nextUrl.searchParams.get("approved_only") === "true";

    // Only use cache when not filtering by approved_only
    if (!approvedOnly && cached && Date.now() - cached.ts < CACHE_TTL) {
      return NextResponse.json(cached.data, {
        headers: { "Cache-Control": "private, max-age=300" },
      });
    }

    const supabase = getSupabase();

    // 1. Fetch all weekly reports
    const reportsRes = await supabase
      .from("weekly_reports")
      .select("report_data, week_start")
      .order("week_start", { ascending: false });

    const reports = reportsRes.data || [];

    // Fetch blog articles separately (table may not exist)
    let articles: any[] = [];
    try {
      const articlesRes = await supabase
        .from("blog_articles")
        .select("id, source_item_id, status, headline, created_at");
      articles = articlesRes.data || [];
    } catch { /* table may not exist */ }

    // 2. Collect unique opportunities from reports, dedup by url
    //    Most-recent-report wins (iterating week_start DESC)
    const urlWeekMap = new Map<string, string>(); // url → week_start
    const enrichmentByUrl = new Map<string, any>();
    let weeksCovered = 0;

    for (const report of reports) {
      const opps = report.report_data?.content_opportunities;
      if (!Array.isArray(opps) || opps.length === 0) continue;
      weeksCovered++;

      for (const opp of opps) {
        const url = opp.url || opp.source_url || "";
        if (!url) continue;
        if (urlWeekMap.has(url)) continue;

        urlWeekMap.set(url, report.week_start);
        // Save LLM-enriched fields from stored report
        if (opp.suggested_title || opp.content_brief || opp.search_intent) {
          enrichmentByUrl.set(url, {
            suggested_title: opp.suggested_title || null,
            content_brief: opp.content_brief || null,
            search_intent: opp.search_intent || null,
          });
        }
      }
    }

    const urls = [...urlWeekMap.keys()];
    console.log(`Content planning: ${urls.length} unique URLs from ${weeksCovered} weeks`);

    // 3. Fetch social_items by source_url to re-score with the TS formula
    const itemByUrl = new Map<string, any>();
    if (urls.length > 0) {
      // Batch in chunks of 100 (Supabase .in() has limits)
      for (let i = 0; i < urls.length; i += 100) {
        const batch = urls.slice(i, i + 100);
        const { data } = await supabase
          .from("social_items")
          .select(ITEM_FIELDS)
          .in("source_url", batch) as { data: any[] | null };
        if (data) {
          for (const item of data) {
            itemByUrl.set(item.source_url, item);
          }
        }
      }
    }
    console.log(`Content planning: ${itemByUrl.size}/${urls.length} matched in social_items`);

    // 4. Build article lookup (by source_item_id)
    const articleByItemId = new Map<string, any>();
    for (const a of articles) {
      if (!a.source_item_id || articleByItemId.has(a.source_item_id)) continue;
      articleByItemId.set(a.source_item_id, {
        article_id: a.id,
        article_status: a.status,
        article_headline: a.headline || "",
      });
    }

    // 5. Re-score each opportunity
    const opportunities: any[] = [];
    let belowThreshold = 0;

    for (const [url, weekStart] of urlWeekMap) {
      const item = itemByUrl.get(url);
      if (!item) continue;

      const gapScore = scoreItem(item);
      if (gapScore < MIN_GAP_SCORE) { belowThreshold++; continue; }

      const enrichment = enrichmentByUrl.get(url) || {};
      const articleInfo = item.id ? articleByItemId.get(item.id) : undefined;

      opportunities.push({
        source_item_id: item.id,
        topic: (item.title || "").slice(0, 120) || (item.content || "").slice(0, 120),
        category: item.category,
        gap_score: gapScore,
        source: displaySource(item),
        url: item.source_url || "",
        content_snippet: (item.content || "").slice(0, 300),
        keywords: item.keywords || [],
        llm_opportunity: item.content_opportunity || null,
        intent: item.intent || null,
        emotion: item.emotion || null,
        answer_count: item.answer_count || 0,
        key_insight: item.key_insight || null,
        device_relevance_score: item.device_relevance_score || 0,
        product_mentions: item.product_mentions || [],
        discovered_week: weekStart,
        suggested_title: enrichment.suggested_title || null,
        content_brief: enrichment.content_brief || null,
        search_intent: enrichment.search_intent || null,
        article_id: articleInfo?.article_id || null,
        article_status: articleInfo?.article_status || null,
        article_headline: articleInfo?.article_headline || null,
      });
    }

    console.log(`Content planning: ${opportunities.length} above threshold, ${belowThreshold} below ${MIN_GAP_SCORE}`);

    // Fetch custom topics (blog_articles with no source_item_id and status=pending)
    try {
      const { data: customTopics } = await supabase
        .from("blog_articles")
        .select("id, keyword, social_context, status, created_at")
        .is("source_item_id", null)
        .eq("status", "pending")
        .order("created_at", { ascending: false });

      if (customTopics && customTopics.length > 0) {
        for (const ct of customTopics) {
          const ctx = ct.social_context || {};
          opportunities.push({
            source_item_id: null,
            topic: ct.keyword || "Custom Topic",
            category: ctx.category || "other",
            gap_score: 0,
            source: "Custom",
            url: null,
            content_snippet: ctx.custom_notes || "",
            keywords: [],
            llm_opportunity: null,
            intent: null,
            emotion: null,
            answer_count: 0,
            key_insight: ctx.custom_notes || null,
            device_relevance_score: 0,
            product_mentions: ctx.products || [],
            discovered_week: null,
            suggested_title: null,
            content_brief: null,
            search_intent: null,
            article_id: ct.id,
            article_status: ct.status,
            article_headline: null,
            custom: true,
            custom_topic_id: ct.id,
          });
        }
      }
    } catch (e) {
      // blog_articles table may not exist, ignore
    }

    // Separate custom topics (they should not be clipped by MAX_OPPORTUNITIES)
    const customTopics = opportunities.filter((o: any) => o.custom === true);
    const systemTopics = opportunities.filter((o: any) => o.custom !== true);

    // Sort system topics by gap_score descending, cap at MAX_OPPORTUNITIES, then append custom
    systemTopics.sort((a, b) => b.gap_score - a.gap_score);
    let limited = [...systemTopics.slice(0, MAX_OPPORTUNITIES), ...customTopics];

    // Filter to approved-only if requested (Beurer dashboard view)
    if (approvedOnly) {
      try {
        const { data: approved } = await supabase
          .from("approved_opportunities")
          .select("source_url");
        if (approved && approved.length > 0) {
          const approvedUrls = new Set(approved.map((a: any) => a.source_url));
          limited = limited.filter((o: any) => approvedUrls.has(o.url));
        } else {
          limited = [];
        }
      } catch {
        // Table may not exist yet — return empty
        limited = [];
      }
    }

    const result = {
      opportunities: limited,
      total: limited.length,
      weeks_covered: weeksCovered,
    };

    if (!approvedOnly) {
      cached = { data: result, ts: Date.now() };
    }

    return NextResponse.json(result, {
      headers: {
        "Cache-Control": approvedOnly
          ? "private, no-cache, no-store"
          : "private, max-age=300",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Content planning error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";
import { fetchItemsForRange, enrichWithRelatedData, fetchPreviousPeriodItems } from "@/lib/aggregator/fetch";
import { aggregateReportData } from "@/lib/aggregator/index";
import { buildNewsData } from "@/lib/aggregator/news";
import { enrichTopics } from "@/lib/enrich-topics";
import type { SocialItem } from "@/lib/aggregator/types";
import { fetchServiceCases, aggregateServiceCaseData } from "@/lib/aggregator/service-cases";

// Import template at build time via webpack asset/source rule
// @ts-ignore — webpack asset/source import
import templateRaw from "../../../template/dashboard_template.html";

function getTemplate(): string {
  return templateRaw as unknown as string;
}

/** Fetch news articles from social_items (exa + curated). */
async function fetchNewsData(supabase: ReturnType<typeof getSupabase>, startDate?: string) {
  try {
    let query = supabase
      .from("social_items")
      .select("id, source, source_url, title, content, posted_at, raw_data, relevance_score, keywords, crawler_tool")
      .in("crawler_tool", ["exa", "curated"])
      .order("posted_at", { ascending: false, nullsFirst: false })
      .limit(200);

    if (startDate) {
      query = query.or(`posted_at.gte.${startDate},posted_at.is.null`);
    }

    const { data: items, error } = await query;
    if (error) {
      console.error("News fetch error:", error.message);
      return null;
    }
    if (items && items.length > 0) {
      const news = buildNewsData(items as SocialItem[]);
      console.log(`News: ${items.length} items → ${news.total} articles`);
      return news;
    }
    return null;
  } catch (e) {
    console.error("News fetch threw:", e instanceof Error ? e.message : e);
    return null;
  }
}

/** Fallback: load news from latest stored weekly report. */
async function fetchNewsFromStoredReport(supabase: ReturnType<typeof getSupabase>) {
  try {
    const { data } = await supabase
      .from("weekly_reports")
      .select("report_data")
      .order("created_at", { ascending: false })
      .limit(1)
      .single();
    const news = data?.report_data?.news;
    if (news && news.total > 0) {
      console.log(`News fallback: ${news.total} articles from stored report`);
      return news;
    }
    return null;
  } catch (e) {
    console.error("News fallback threw:", e instanceof Error ? e.message : e);
    return null;
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    // Debug endpoint: check template version
    if (searchParams.get("debug") === "template") {
      const tpl = getTemplate();
      return NextResponse.json({
        templateLength: tpl.length,
        first200: tpl.slice(0, 200),
        hasVersionBar: tpl.includes("version-bar-label"),
        hasCollapse: tpl.includes("header-collapsed"),
        hasVersionMarker: tpl.includes("template-version"),
        method: "webpack-import",
      });
    }

    const lang = searchParams.get("lang") || "de";
    const week = searchParams.get("week");
    const days = searchParams.get("days");

    const supabase = getSupabase();

    let reportData: any;

    if (week) {
      // Stored report mode: fetch a specific week from weekly_reports table
      const { data, error } = await supabase
        .from("weekly_reports")
        .select("report_data, week_start, week_end, created_at")
        .eq("week_start", week)
        .order("created_at", { ascending: false })
        .limit(1)
        .single();

      if (error || !data) {
        return new NextResponse(
          `<html><body style="font-family:sans-serif;padding:40px">
            <h1>No dashboard data available</h1>
            <p>No weekly report found for week starting ${week}.</p>
            <p>Run the pipeline first: <code>POST /report/weekly?format=full</code></p>
          </body></html>`,
          {
            status: 404,
            headers: { "Content-Type": "text/html; charset=utf-8" },
          }
        );
      }

      const { data: weeks } = await supabase
        .from("weekly_reports")
        .select("week_start, week_end")
        .order("week_start", { ascending: false });

      reportData = { ...data.report_data, available_weeks: weeks || [] };

      // Supplement stored report with live news if not already present
      if (!reportData.news || !reportData.news.total) {
        const news = await fetchNewsData(supabase);
        if (news) {
          reportData.news = news;
        }
      }
    } else {
      // Dynamic mode (default): aggregate live data from social_items
      const numDays = (days && [7, 14, 30].includes(parseInt(days, 10)))
        ? parseInt(days, 10)
        : 7;
      const now = new Date();
      const start = new Date(now);
      start.setDate(start.getDate() - numDays);
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      const startDate = start.toISOString().split("T")[0];
      const endDate = tomorrow.toISOString().split("T")[0];

      // Always fetch all languages — lang param is for UI labels only
      let items = await fetchItemsForRange(supabase, startDate, endDate, "all");
      let previousItems = await fetchPreviousPeriodItems(supabase, startDate, endDate, "all")
        .catch(e => {
          console.warn("Previous period fetch failed (non-blocking):", e);
          return [] as Awaited<ReturnType<typeof fetchPreviousPeriodItems>>;
        });
      [items, previousItems] = await Promise.all([
        enrichWithRelatedData(supabase, items),
        enrichWithRelatedData(supabase, previousItems),
      ]);
      const data = aggregateReportData(items, startDate, endDate, previousItems);

      // Fetch and aggregate service case data
      const serviceCases = await fetchServiceCases(supabase, startDate, endDate);
      const kundendienstInsights = aggregateServiceCaseData(serviceCases);
      if (kundendienstInsights) {
        (data as any).kundendienstInsights = kundendienstInsights;
      }

      // Fetch Exa + curated news
      const news = await fetchNewsData(supabase, startDate);
      if (news) {
        (data as any).news = news;
      }

      // Fallback: load from stored report if live query returned nothing
      if (!(data as any).news || !(data as any).news.total) {
        const fallbackNews = await fetchNewsFromStoredReport(supabase);
        if (fallbackNews) {
          (data as any).news = fallbackNews;
        }
      }

      // Enrich content opportunity topics via LLM
      if (data.content_opportunities?.length) {
        data.content_opportunities = await enrichTopics(data.content_opportunities, lang);
      }

      const { data: weeks } = await supabase
        .from("weekly_reports")
        .select("week_start, week_end")
        .order("week_start", { ascending: false });

      reportData = { ...data, available_weeks: weeks || [] };
    }

    const template = getTemplate();
    const dataJson = JSON.stringify(reportData);
    const html = template
      .replace("__DASHBOARD_DATA__", dataJson)
      .replace("__DEFAULT_LANG__", lang);

    return new NextResponse(html, {
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "public, s-maxage=0, must-revalidate",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

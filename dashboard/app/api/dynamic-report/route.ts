import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";
import { fetchItemsForRange, enrichWithRelatedData, fetchPreviousPeriodItems } from "@/lib/aggregator/fetch";
import { aggregateReportData } from "@/lib/aggregator/index";
import { enrichTopics } from "@/lib/enrich-topics";
import { fetchServiceCases, aggregateServiceCaseData } from "@/lib/aggregator/service-cases";

// Simple in-memory cache (5-min TTL)
// Key includes the computed date range so cache auto-invalidates at day boundaries
const cache = new Map<string, { data: any; ts: number }>();
const CACHE_TTL = 5 * 60 * 1000;
// Track in-flight requests to deduplicate concurrent calls
const inflight = new Map<string, Promise<any>>();

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const days = parseInt(searchParams.get("days") || "7", 10);
    const lang = searchParams.get("lang") || "de";
    const noCache = searchParams.get("nocache") === "1";

    if (![7, 14, 30].includes(days)) {
      return NextResponse.json({ error: "days must be 7, 14, or 30" }, { status: 400 });
    }

    const supabase = getSupabase();
    const now = new Date();
    const start = new Date(now);
    start.setDate(start.getDate() - days);
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const startDate = start.toISOString().split("T")[0];
    const endDate = tomorrow.toISOString().split("T")[0];

    // Cache key includes actual date range so it auto-invalidates at day boundaries
    // lang is excluded — data is always fetched for all languages (lang only affects UI labels)
    const cacheKey = `${days}-${startDate}-${endDate}`;

    // Check cache (skip if nocache=1)
    if (!noCache) {
      const cached = cache.get(cacheKey);
      if (cached && Date.now() - cached.ts < CACHE_TTL) {
        return NextResponse.json(cached.data, {
          headers: { "Cache-Control": "no-store" },
        });
      }
    }

    // Deduplicate concurrent requests for the same key
    if (inflight.has(cacheKey)) {
      const result = await inflight.get(cacheKey);
      return NextResponse.json(result, {
        headers: { "Cache-Control": "no-store" },
      });
    }

    // Register inflight promise so concurrent requests deduplicate
    const fetchPromise = (async () => {
      // Always fetch all languages — lang param is for UI labels only.
      // The data is predominantly German; filtering by lang=en would drop most items.
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

      // Aggregate
      const data = aggregateReportData(items, startDate, endDate, previousItems);

      // Fetch and aggregate service case data
      const serviceCases = await fetchServiceCases(supabase, startDate, endDate);
      const kundendienstInsights = aggregateServiceCaseData(serviceCases);
      if (kundendienstInsights) {
        (data as any).kundendienstInsights = kundendienstInsights;
      }

      // Enrich content opportunity topics via LLM
      if (data.content_opportunities?.length) {
        data.content_opportunities = await enrichTopics(data.content_opportunities, lang);
      }

      // Fetch available weeks for the week picker
      const { data: weeks } = await supabase
        .from("weekly_reports")
        .select("week_start, week_end")
        .order("week_start", { ascending: false });

      return { ...data, available_weeks: weeks || [] };
    })();

    inflight.set(cacheKey, fetchPromise);
    let result: any;
    try {
      result = await fetchPromise;
    } finally {
      inflight.delete(cacheKey);
    }

    // Cache all results (empty periods get shorter TTL to allow retry)
    const totalMentions = result.executive_summary?.total_mentions ?? 0;
    const ttl = totalMentions > 0 ? CACHE_TTL : 60 * 1000; // 1 min for empty
    cache.set(cacheKey, { data: result, ts: Date.now() - (CACHE_TTL - ttl) });

    return NextResponse.json(result, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Dynamic report error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

const BRAND_ID = "cada9f51-a17d-4e0b-9ba7-d8083f29d162";
const API_BASE = "https://www.aipeekaboo.com/api/v1";

// 60-minute in-memory cache (data updates daily, rate limits: 5 req/min, 100/day)
let cached: { data: any; ts: number } | null = null;
const CACHE_TTL = 60 * 60 * 1000;

// Fix double-encoded UTF-8 from Peekaboo API (e.g., "Ã¤" → "ä")
function fixEncoding(text: string): string {
  if (!text || typeof text !== "string") return text;
  try {
    // Detect double-encoding: UTF-8 bytes interpreted as Latin-1
    if (/[\u00c0-\u00c3][\u0080-\u00bf]/.test(text)) {
      const bytes = new Uint8Array([...text].map((c) => c.charCodeAt(0)));
      const decoded = new TextDecoder("utf-8").decode(bytes);
      if (!decoded.includes("\ufffd")) return decoded;
    }
  } catch {}
  return text;
}

function fixEncodingDeep(obj: any): any {
  if (typeof obj === "string") return fixEncoding(obj);
  if (Array.isArray(obj)) return obj.map(fixEncodingDeep);
  if (obj && typeof obj === "object") {
    const out: any = {};
    for (const [k, v] of Object.entries(obj)) out[k] = fixEncodingDeep(v);
    return out;
  }
  return obj;
}

async function apiFetch(path: string, apiKey: string) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "X-API-Key": apiKey },
  });
  if (!res.ok) return null;
  const json = await res.json();
  if (!json?.success) return null;
  return fixEncodingDeep(json.data);
}

export async function GET(request: Request) {
  try {
    const apiKey = process.env.PEEKABOO_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: "PEEKABOO_API_KEY not configured" },
        { status: 503 }
      );
    }

    // If ?history=true, return stored snapshots for trend chart
    const url = new URL(request.url);
    if (url.searchParams.get("history") === "true") {
      const days = parseInt(url.searchParams.get("days") || "90", 10);
      const supabase = getSupabase();
      const since = new Date();
      since.setDate(since.getDate() - days);
      const { data: snapshots } = await supabase
        .from("peekaboo_snapshots")
        .select("snapshot_date, brand_score, brand_rank, total_citations, total_chats, competitors")
        .gte("snapshot_date", since.toISOString().split("T")[0])
        .order("snapshot_date", { ascending: true });
      return NextResponse.json({ history: snapshots || [] });
    }

    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      return NextResponse.json(cached.data, {
        headers: { "Cache-Control": "private, max-age=3600" },
      });
    }

    // Fetch all 3 endpoints in parallel (3 of 5/min rate limit)
    const [snapshot, promptsDetail, competitorsDetail] = await Promise.all([
      apiFetch(`/brands/${BRAND_ID}/snapshot`, apiKey),
      apiFetch(`/brands/${BRAND_ID}/prompts`, apiKey),
      apiFetch(`/brands/${BRAND_ID}/competitors`, apiKey),
    ]);

    if (!snapshot) {
      throw new Error("Peekaboo API: snapshot request failed");
    }

    const result = transform(snapshot, promptsDetail, competitorsDetail);

    // Store daily snapshot for trend chart (fire-and-forget, don't block response)
    storeSnapshot(result).catch((e) =>
      console.error("Snapshot storage failed (non-blocking):", e)
    );

    cached = { data: result, ts: Date.now() };

    return NextResponse.json(result, {
      headers: { "Cache-Control": "private, max-age=3600" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Media visibility error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

function transform(snap: any, promptsDetail: any, competitorsDetail: any) {
  const vis = snap?.visibility ?? {};
  const competitors = snap?.competitors ?? [];
  const prompts = snap?.prompts ?? [];
  const sources = snap?.sources ?? [];
  const suggestions = snap?.aiSuggestions ?? snap?.suggestions ?? [];
  const traffic = snap?.traffic ?? {};

  // Build lookup from /prompts endpoint for extra fields (trend, bestScore, worstScore, totalRuns)
  const promptExtras: Record<string, any> = {};
  if (Array.isArray(promptsDetail)) {
    for (const p of promptsDetail) {
      const key = p?.promptText ?? "";
      if (key) promptExtras[key] = p;
    }
  }

  // Build lookup from /competitors endpoint for extra fields (monthlyVisits, change)
  const compExtras: Record<string, any> = {};
  const brandMeta = competitorsDetail?.brand ?? {};
  if (Array.isArray(competitorsDetail?.competitors)) {
    for (const c of competitorsDetail.competitors) {
      if (c?.name) compExtras[c.name] = c;
    }
  }

  return {
    overview: {
      score: vis?.score ?? 0,
      rank: vis?.rank ?? 0,
      totalCitations: vis?.totalCitations ?? 0,
      totalChats: vis?.totalChatsAnalyzed ?? 0,
      trend: brandMeta?.trend ?? null,
    },
    competitors: competitors.map((c: any) => {
      const extra = compExtras[c?.name] ?? {};
      return {
        name: c?.name ?? "",
        score: c?.score ?? 0,
        url: c?.url ?? "",
        change: extra?.change ?? c?.change ?? null,
        monthlyVisits: extra?.monthlyVisits ?? c?.monthlyVisits ?? null,
        rank: c?.rank ?? null,
      };
    }),
    competitorSummary: {
      totalCompetitors: competitorsDetail?.summary?.totalCompetitors ?? competitors.length,
      brandRank: competitorsDetail?.summary?.brandRankAmongCompetitors ?? null,
      avgCompetitorScore: competitorsDetail?.summary?.averageCompetitorScore ?? null,
    },
    prompts: prompts.map((p: any) => {
      const key = p?.promptText ?? p?.text ?? "";
      const extra = promptExtras[key] ?? {};
      return {
        promptId: extra?.promptId ?? p?.promptId ?? null,
        text: key,
        category: p?.category ?? "",
        mentions: p?.mentions ?? 0,
        score: p?.averageScore ?? p?.score ?? 0,
        aiModels: p?.aiModels ?? [],
        trend: extra?.trend ?? null,
        bestScore: extra?.bestScore ?? null,
        worstScore: extra?.worstScore ?? null,
        totalRuns: extra?.totalRuns ?? null,
      };
    }),
    sources: sources.map((s: any) => ({
      domain: s?.domain ?? "",
      mentions: s?.mentions ?? s?.citations ?? 0,
      aiModels: s?.aiModels ?? [],
    })),
    suggestions: Array.isArray(suggestions)
      ? suggestions.map((s: any) => (typeof s === "string" ? s : s?.text ?? "")).filter(Boolean)
      : [],
    traffic: {
      monthlyVisits: traffic?.monthlyVisits ?? 0,
      globalRank: traffic?.globalRank ?? 0,
      countryRank: traffic?.countryRank ?? 0,
      bounceRate: traffic?.bounceRate ?? 0,
      pagesPerVisit: traffic?.pagesPerVisit ?? 0,
      avgTimeOnSite: traffic?.avgTimeOnSite ?? 0,
    },
    snapshotDate: snap?.snapshotDate ?? new Date().toISOString(),
  };
}

async function storeSnapshot(data: any) {
  try {
    const supabase = getSupabase();
    const today = new Date().toISOString().split("T")[0];
    const overview = data.overview || {};

    await supabase.from("peekaboo_snapshots").upsert(
      {
        snapshot_date: today,
        brand_score: overview.score ?? 0,
        brand_rank: overview.rank ?? 0,
        total_citations: overview.totalCitations ?? 0,
        total_chats: overview.totalChats ?? 0,
        competitors: data.competitors ?? [],
        raw_snapshot: data,
      },
      { onConflict: "snapshot_date" }
    );
  } catch (e) {
    console.error("storeSnapshot error:", e);
  }
}

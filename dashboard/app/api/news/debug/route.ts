import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

export async function GET() {
  const supabase = getSupabase();
  const results: Record<string, any> = {};

  // 1. Count all exa items
  const { count: exaCount, error: e1 } = await supabase
    .from("social_items")
    .select("id", { count: "exact", head: true })
    .eq("crawler_tool", "exa");
  results.exa_count = exaCount;
  results.exa_error = e1?.message || null;

  // 2. Count all curated items
  const { count: curatedCount, error: e2 } = await supabase
    .from("social_items")
    .select("id", { count: "exact", head: true })
    .eq("crawler_tool", "curated");
  results.curated_count = curatedCount;
  results.curated_error = e2?.message || null;

  // 3. Try the .in() query
  const { data: inItems, error: e3 } = await supabase
    .from("social_items")
    .select("id, source, crawler_tool")
    .in("crawler_tool", ["exa", "curated"])
    .limit(5);
  results.in_query_count = inItems?.length ?? null;
  results.in_query_error = e3?.message || null;
  results.in_query_sample = inItems?.slice(0, 2) || null;

  // 4. Check weekly_reports news
  const { data: report, error: e4 } = await supabase
    .from("weekly_reports")
    .select("report_data")
    .order("created_at", { ascending: false })
    .limit(1)
    .single();
  results.report_error = e4?.message || null;
  results.report_has_news = !!report?.report_data?.news;
  results.report_news_total = report?.report_data?.news?.total ?? 0;

  // 5. All distinct crawler_tool values
  const { data: tools, error: e5 } = await supabase
    .from("social_items")
    .select("crawler_tool")
    .not("crawler_tool", "is", null)
    .limit(1000);
  const toolCounts: Record<string, number> = {};
  (tools || []).forEach((r: any) => {
    toolCounts[r.crawler_tool] = (toolCounts[r.crawler_tool] || 0) + 1;
  });
  results.crawler_tool_distribution = toolCounts;
  results.tools_error = e5?.message || null;

  return NextResponse.json(results, {
    headers: { "Cache-Control": "no-store" },
  });
}

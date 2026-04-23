import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = Math.min(parseInt(searchParams.get("limit") || "1"), 50);
    const week = searchParams.get("week");

    const supabase = getSupabase();

    let query = supabase
      .from("weekly_reports")
      .select("id, week_start, week_end, report_data, created_at")
      .order("created_at", { ascending: false });

    if (week) {
      query = query.eq("week_start", week);
    }

    const { data, error } = await query.limit(limit);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({
      count: data?.length || 0,
      reports: data || [],
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

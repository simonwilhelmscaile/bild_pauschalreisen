import { NextRequest, NextResponse } from "next/server";

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;

interface GscTokenData {
  site_url: string;
  access_token: string;
  refresh_token: string;
  token_expiry: string;
  email: string;
}

async function loadGscTokens(): Promise<GscTokenData | null> {
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_KEY;
  if (!supabaseUrl || !supabaseKey) return null;

  try {
    const res = await fetch(
      `${supabaseUrl}/storage/v1/object/config/gsc-tokens.json`,
      { headers: { apikey: supabaseKey, Authorization: `Bearer ${supabaseKey}` } }
    );
    if (!res.ok) return null;
    return (await res.json()) as GscTokenData;
  } catch {
    return null;
  }
}

async function refreshAccessToken(refreshToken: string): Promise<string | null> {
  if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) return null;
  try {
    const res = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        client_id: GOOGLE_CLIENT_ID,
        client_secret: GOOGLE_CLIENT_SECRET,
        refresh_token: refreshToken,
        grant_type: "refresh_token",
      }),
    });
    const data = await res.json();
    return data.access_token || null;
  } catch {
    return null;
  }
}

interface GSCRow {
  query?: string;
  page?: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const days = parseInt(searchParams.get("days") || "28", 10);
  const type = searchParams.get("type") || "query";

  // Load tokens from Supabase Storage
  const tokens = await loadGscTokens();

  if (!tokens) {
    return NextResponse.json(
      { error: "GSC not connected. Use /api/gsc/auth to connect.", connected: false },
      { status: 404 }
    );
  }

  // Refresh access token
  const accessToken = await refreshAccessToken(tokens.refresh_token);
  if (!accessToken) {
    return NextResponse.json(
      { error: "Failed to refresh access token. Re-connect GSC.", connected: false },
      { status: 401 }
    );
  }

  // Update stored tokens with fresh access token
  const updated = { ...tokens, access_token: accessToken, token_expiry: new Date(Date.now() + 3600 * 1000).toISOString() };
  await fetch(
    `${process.env.SUPABASE_URL}/storage/v1/object/config/gsc-tokens.json`,
    {
      method: "POST",
      headers: {
        apikey: process.env.SUPABASE_SERVICE_KEY!,
        Authorization: `Bearer ${process.env.SUPABASE_SERVICE_KEY}`,
        "Content-Type": "application/json",
        "x-upsert": "true",
      },
      body: JSON.stringify(updated),
    }
  );

  // Build date range
  const endDate = new Date();
  endDate.setDate(endDate.getDate() - 3); // GSC data has 3-day delay
  const startDate = new Date(endDate);
  startDate.setDate(startDate.getDate() - days);

  const formatDate = (d: Date) => d.toISOString().split("T")[0];

  // Query GSC API
  try {
    const dimension = type === "page" ? "page" : "query";
    const gscRes = await fetch(
      `https://www.googleapis.com/webmasters/v3/sites/${encodeURIComponent(tokens.site_url)}/searchAnalytics/query`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          startDate: formatDate(startDate),
          endDate: formatDate(endDate),
          dimensions: [dimension],
          rowLimit: 100,
          dataState: "final",
        }),
      }
    );

    const gscData = await gscRes.json();

    if (!gscRes.ok) {
      return NextResponse.json(
        { error: gscData.error?.message || "GSC API error", connected: true },
        { status: gscRes.status }
      );
    }

    // Process rows
    const rows = (gscData.rows || []).map((row: { keys: string[]; clicks: number; impressions: number; ctr: number; position: number }) => ({
      [dimension]: row.keys[0],
      clicks: row.clicks,
      impressions: row.impressions,
      ctr: Math.round(row.ctr * 10000) / 100,
      position: Math.round(row.position * 10) / 10,
    }));

    // Totals
    const totals = rows.reduce(
      (acc: { clicks: number; impressions: number }, r: GSCRow) => ({
        clicks: acc.clicks + r.clicks,
        impressions: acc.impressions + r.impressions,
      }),
      { clicks: 0, impressions: 0 }
    );

    // Fetch date-level data for chart
    let dateRows: { date: string; clicks: number; impressions: number }[] = [];
    try {
      const dateRes = await fetch(
        `https://www.googleapis.com/webmasters/v3/sites/${encodeURIComponent(tokens.site_url)}/searchAnalytics/query`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            startDate: formatDate(startDate),
            endDate: formatDate(endDate),
            dimensions: ["date"],
            dataState: "final",
          }),
        }
      );
      const dateData = await dateRes.json();
      dateRows = (dateData.rows || []).map((row: { keys: string[]; clicks: number; impressions: number }) => ({
        date: row.keys[0],
        clicks: row.clicks,
        impressions: row.impressions,
      }));
    } catch {
      // ignore date chart errors
    }

    return NextResponse.json({
      connected: true,
      site_url: tokens.site_url,
      email: tokens.email,
      period: { start: formatDate(startDate), end: formatDate(endDate), days },
      totals,
      rows,
      date_chart: dateRows,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: msg, connected: true }, { status: 500 });
  }
}

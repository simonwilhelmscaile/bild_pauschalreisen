import { NextRequest, NextResponse } from "next/server";

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const stateParam = searchParams.get("state");
  const error = searchParams.get("error");

  if (error) {
    return new NextResponse(renderResult("Google OAuth Error", error, false), {
      headers: { "Content-Type": "text/html" },
    });
  }

  if (!code || !GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) {
    return new NextResponse(
      renderResult("Configuration Error", "Missing code or credentials", false),
      { headers: { "Content-Type": "text/html" } }
    );
  }

  // Parse state
  let siteUrl = "";
  try {
    const state = JSON.parse(Buffer.from(stateParam || "", "base64").toString());
    siteUrl = state.site_url || "";
  } catch {
    // ignore
  }

  // Build redirect URI
  const host = request.headers.get("host") || "localhost:3000";
  const protocol = host.includes("localhost") ? "http" : "https";
  const redirectUri = `${protocol}://${host}/api/gsc/callback`;

  // Exchange code for tokens
  try {
    const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code,
        client_id: GOOGLE_CLIENT_ID,
        client_secret: GOOGLE_CLIENT_SECRET,
        redirect_uri: redirectUri,
        grant_type: "authorization_code",
      }),
    });

    const tokens = await tokenRes.json();
    if (!tokenRes.ok || !tokens.refresh_token) {
      return new NextResponse(
        renderResult("Token Error", tokens.error_description || "Failed to get refresh token", false),
        { headers: { "Content-Type": "text/html" } }
      );
    }

    // Get user email
    let email = "";
    try {
      const userRes = await fetch(
        `https://www.googleapis.com/oauth2/v2/userinfo?access_token=${tokens.access_token}`
      );
      const user = await userRes.json();
      email = user.email || "";
    } catch {
      // ignore
    }

    // If no site_url provided, fetch list of sites
    if (!siteUrl) {
      try {
        const sitesRes = await fetch(
          "https://www.googleapis.com/webmasters/v3/sites",
          { headers: { Authorization: `Bearer ${tokens.access_token}` } }
        );
        const sitesData = await sitesRes.json();
        const sites = (sitesData.siteEntry || []) as { siteUrl: string; permissionLevel: string }[];

        if (sites.length > 1) {
          // Multiple sites — show picker
          return new NextResponse(
            renderSitePicker(sites, tokens, email, request),
            { headers: { "Content-Type": "text/html" } }
          );
        } else if (sites.length === 1) {
          siteUrl = sites[0].siteUrl;
        }
      } catch {
        // ignore
      }
    }

    if (!siteUrl) {
      siteUrl = "unknown";
    }

    // Store tokens via Supabase Storage REST API (bypasses PostgREST entirely)
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_KEY;
    const tokenData = JSON.stringify({
      site_url: siteUrl,
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      token_expiry: new Date(Date.now() + (tokens.expires_in || 3600) * 1000).toISOString(),
      email,
      updated_at: new Date().toISOString(),
    });

    // Ensure config bucket exists
    await fetch(`${supabaseUrl}/storage/v1/bucket`, {
      method: "POST",
      headers: {
        "apikey": supabaseKey!,
        "Authorization": `Bearer ${supabaseKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id: "config", name: "config", public: false }),
    });

    // Upload as JSON file (upsert via x-upsert header)
    const uploadRes = await fetch(
      `${supabaseUrl}/storage/v1/object/config/gsc-tokens.json`,
      {
        method: "POST",
        headers: {
          "apikey": supabaseKey!,
          "Authorization": `Bearer ${supabaseKey}`,
          "Content-Type": "application/json",
          "x-upsert": "true",
        },
        body: tokenData,
      }
    );

    if (!uploadRes.ok) {
      const errBody = await uploadRes.text();
      return new NextResponse(
        renderResult("Storage Error", `${uploadRes.status}: ${errBody}`, false),
        { headers: { "Content-Type": "text/html", "Cache-Control": "no-store" } }
      );
    }

    return new NextResponse(
      renderResult(
        "GSC Connected!",
        `Successfully connected Google Search Console for ${siteUrl} (${email}). You can close this window.`,
        true
      ),
      { headers: { "Content-Type": "text/html" } }
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return new NextResponse(renderResult("Error", msg, false), {
      headers: { "Content-Type": "text/html" },
    });
  }
}

// Handle site selection from the picker form
export async function POST(request: NextRequest) {
  try {
    const form = await request.formData();
    const siteUrl = form.get("site_url") as string;
    const accessToken = form.get("access_token") as string;
    const refreshToken = form.get("refresh_token") as string;
    const expiresIn = parseInt(form.get("expires_in") as string || "3600", 10);
    const email = form.get("email") as string || "";

    if (!siteUrl || !refreshToken) {
      return new NextResponse(
        renderResult("Error", "Missing site or tokens", false),
        { headers: { "Content-Type": "text/html" } }
      );
    }

    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_KEY;
    const tokenData = JSON.stringify({
      site_url: siteUrl,
      access_token: accessToken,
      refresh_token: refreshToken,
      token_expiry: new Date(Date.now() + expiresIn * 1000).toISOString(),
      email,
      updated_at: new Date().toISOString(),
    });

    // Ensure config bucket exists
    await fetch(`${supabaseUrl}/storage/v1/bucket`, {
      method: "POST",
      headers: {
        "apikey": supabaseKey!,
        "Authorization": `Bearer ${supabaseKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id: "config", name: "config", public: false }),
    });

    const uploadRes = await fetch(
      `${supabaseUrl}/storage/v1/object/config/gsc-tokens.json`,
      {
        method: "POST",
        headers: {
          "apikey": supabaseKey!,
          "Authorization": `Bearer ${supabaseKey}`,
          "Content-Type": "application/json",
          "x-upsert": "true",
        },
        body: tokenData,
      }
    );

    if (!uploadRes.ok) {
      const errBody = await uploadRes.text();
      return new NextResponse(
        renderResult("Storage Error", `${uploadRes.status}: ${errBody}`, false),
        { headers: { "Content-Type": "text/html", "Cache-Control": "no-store" } }
      );
    }

    return new NextResponse(
      renderResult(
        "GSC Connected!",
        `Successfully connected Google Search Console for ${siteUrl} (${email}). You can close this window.`,
        true
      ),
      { headers: { "Content-Type": "text/html" } }
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return new NextResponse(renderResult("Error", msg, false), {
      headers: { "Content-Type": "text/html" },
    });
  }
}

function renderSitePicker(
  sites: { siteUrl: string; permissionLevel: string }[],
  tokens: { access_token: string; refresh_token: string; expires_in?: number },
  email: string,
  request: NextRequest
): string {
  const host = request.headers.get("host") || "localhost:3000";
  const protocol = host.includes("localhost") ? "http" : "https";
  const actionUrl = `${protocol}://${host}/api/gsc/callback`;

  const siteButtons = sites.map(s => {
    const displayUrl = s.siteUrl.replace(/^sc-domain:/, "").replace(/\/$/, "");
    const permLabel = s.permissionLevel === "siteOwner" ? "Owner" : s.permissionLevel === "siteFullUser" ? "Full" : s.permissionLevel;
    return `<button type="submit" name="site_url" value="${s.siteUrl.replace(/"/g, "&quot;")}" style="display:flex;align-items:center;justify-content:space-between;width:100%;padding:14px 18px;margin-bottom:10px;background:#fff;border:1.5px solid #e8e8ed;border-radius:10px;font-size:14px;cursor:pointer;transition:all 0.15s;text-align:left" onmouseover="this.style.borderColor='#c60050';this.style.background='#fef2f6'" onmouseout="this.style.borderColor='#e8e8ed';this.style.background='#fff'">
      <span style="font-weight:500;color:#1d1d1f">${displayUrl}</span>
      <span style="font-size:11px;color:#86868b;background:#f5f5f7;padding:2px 8px;border-radius:4px">${permLabel}</span>
    </button>`;
  }).join("");

  return `<!DOCTYPE html>
<html><head><title>Select GSC Property</title>
<style>
  body { font-family: Inter, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f5f5f7; }
  .card { background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); max-width: 460px; width: 100%; }
  h1 { font-size: 20px; color: #1d1d1f; margin: 0 0 4px; }
  .sub { font-size: 13px; color: #86868b; margin-bottom: 24px; }
</style></head>
<body><div class="card">
  <h1>Select GSC Property</h1>
  <div class="sub">Connected as ${email}. Choose which property to use:</div>
  <form method="POST" action="${actionUrl}">
    <input type="hidden" name="access_token" value="${tokens.access_token}">
    <input type="hidden" name="refresh_token" value="${tokens.refresh_token}">
    <input type="hidden" name="expires_in" value="${tokens.expires_in || 3600}">
    <input type="hidden" name="email" value="${email}">
    ${siteButtons}
  </form>
</div></body></html>`;
}

function renderResult(title: string, message: string, success: boolean): string {
  const color = success ? "#16a34a" : "#dc2626";
  const icon = success ? "&#10003;" : "&#10007;";
  const backLink = success
    ? `<a href="/" style="display:inline-block;margin-top:20px;padding:10px 24px;background:#c60050;color:#fff;border-radius:8px;text-decoration:none;font-weight:500;font-size:14px">Back to Dashboard</a>`
    : `<a href="/api/gsc/auth" style="display:inline-block;margin-top:20px;padding:10px 24px;background:#c60050;color:#fff;border-radius:8px;text-decoration:none;font-weight:500;font-size:14px">Try Again</a>`;
  return `<!DOCTYPE html>
<html><head><title>${title}</title>
<style>
  body { font-family: Inter, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f5f5f7; }
  .card { background: white; border-radius: 16px; padding: 48px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); text-align: center; max-width: 420px; }
  .icon { font-size: 48px; color: ${color}; margin-bottom: 16px; }
  h1 { font-size: 20px; color: #1d1d1f; margin: 0 0 8px; }
  p { font-size: 14px; color: #86868b; line-height: 1.5; }
</style></head>
<body><div class="card">
  <div class="icon">${icon}</div>
  <h1>${title}</h1>
  <p>${message}</p>
  ${backLink}
</div></body></html>`;
}

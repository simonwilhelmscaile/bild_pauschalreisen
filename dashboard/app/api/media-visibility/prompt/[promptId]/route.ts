import { NextResponse } from "next/server";

const BRAND_ID = "cada9f51-a17d-4e0b-9ba7-d8083f29d162";
const API_BASE = "https://www.aipeekaboo.com/api/v1";

// Simple in-memory cache per prompt (10 min TTL)
const promptCache = new Map<string, { data: any; ts: number }>();
const CACHE_TTL = 10 * 60 * 1000;

// Fix double-encoded UTF-8 from Peekaboo API (e.g., "Ã¤" → "ä")
function fixEncoding(text: string): string {
  if (!text || typeof text !== "string") return text;
  try {
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

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ promptId: string }> }
) {
  try {
    const apiKey = process.env.PEEKABOO_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: "PEEKABOO_API_KEY not configured" },
        { status: 503 }
      );
    }

    const { promptId } = await params;
    if (!promptId || promptId.length < 10) {
      return NextResponse.json({ error: "Invalid promptId" }, { status: 400 });
    }

    // Check cache
    const cached = promptCache.get(promptId);
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      return NextResponse.json(cached.data, {
        headers: { "Cache-Control": "private, max-age=600" },
      });
    }

    const res = await fetch(
      `${API_BASE}/brands/${BRAND_ID}/prompts/${promptId}`,
      { headers: { "X-API-Key": apiKey } }
    );

    if (!res.ok) {
      return NextResponse.json(
        { error: `Peekaboo API returned ${res.status}` },
        { status: 502 }
      );
    }

    const json = await res.json();
    if (!json?.success) {
      return NextResponse.json(
        { error: "Peekaboo API error" },
        { status: 502 }
      );
    }

    const raw = fixEncodingDeep(json.data);
    const result = {
      promptId: raw.promptId,
      promptText: raw.promptText,
      category: raw.category,
      summary: raw.summary,
      runs: (raw.history || []).map((r: any) => ({
        runId: r.runId,
        date: r.date,
        aiModel: r.aiModel,
        score: r.score,
        rank: r.rank,
        mentioned: r.mentioned,
        sentiment: r.sentiment,
        responseSnippet: r.responseSnippet,
        mentionSummary: r.mentionSummary,
        sources: (r.sources || []).map((s: any) => ({
          domain: s.domain,
          url: s.url,
          title: s.title,
        })),
        brandMentions: (r.brandMentions || []).map((b: any) => ({
          name: b.entityName,
          type: b.type,
          rank: b.rank,
          score: b.score,
          sentiment: b.sentiment,
          summary: b.mentionSummary,
        })),
      })),
    };

    promptCache.set(promptId, { data: result, ts: Date.now() });

    return NextResponse.json(result, {
      headers: { "Cache-Control": "private, max-age=600" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("Prompt detail error:", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

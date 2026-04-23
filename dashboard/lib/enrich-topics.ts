/**
 * Enrich content opportunity topics via Gemini.
 *
 * Takes the top-10 content opportunities (which have raw crawled titles)
 * and generates concise, descriptive topic titles via a single LLM call.
 * Results are cached in-memory for 15 minutes.
 */

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";
const GEMINI_MODEL = "gemini-2.0-flash";
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

// In-memory cache: hash of source_item_ids → enriched topics
const topicCache = new Map<string, { topics: string[]; ts: number }>();
const CACHE_TTL = 15 * 60 * 1000;

function cacheKey(opps: any[]): string {
  return opps.map((o) => o.source_item_id || o.topic || "").join("|");
}

export async function enrichTopics(
  opportunities: any[],
  lang: string = "de"
): Promise<any[]> {
  if (!GEMINI_API_KEY || opportunities.length === 0) return opportunities;

  // Check cache
  const key = cacheKey(opportunities);
  const cached = topicCache.get(key);
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return opportunities.map((o, i) => ({
      ...o,
      topic: cached.topics[i] || o.topic,
    }));
  }

  const isDE = lang.startsWith("de");

  const itemList = opportunities
    .map((o, i) => {
      const kw = (o.keywords || []).slice(0, 3).join(", ");
      const snippet = (o.content_snippet || "").slice(0, 150);
      return `${i + 1}. Title: "${o.topic || ""}"${kw ? ` | Keywords: ${kw}` : ""}${o.category ? ` | Category: ${o.category}` : ""}${snippet ? `\n   Snippet: "${snippet}"` : ""}`;
    })
    .join("\n");

  const prompt = isDE
    ? `Du erhältst ${opportunities.length} Social-Listening-Einträge mit Rohtiteln von Foren und Webseiten. Generiere für jeden einen kurzen, beschreibenden Themantitel (max 60 Zeichen, Deutsch), der das Kernthema erfasst. Kein Marketing-Sprech, sachlich und klar.

Einträge:
${itemList}

Antworte NUR mit einem JSON-Array von ${opportunities.length} Strings, in derselben Reihenfolge. Beispiel: ["Blutdruckmessgerät für Senioren", "TENS-Gerät bei Rückenschmerzen"]`
    : `You receive ${opportunities.length} social listening items with raw titles from forums and websites. Generate a short, descriptive topic title (max 60 chars, English) for each that captures the core subject. No marketing language, factual and clear.

Items:
${itemList}

Respond ONLY with a JSON array of ${opportunities.length} strings, in the same order. Example: ["Blood Pressure Monitor for Seniors", "TENS Device for Back Pain"]`;

  try {
    const res = await fetch(GEMINI_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.3,
          responseMimeType: "application/json",
        },
      }),
    });

    if (!res.ok) {
      console.error(`Gemini topic enrichment failed: ${res.status}`);
      return opportunities;
    }

    const data = await res.json();
    const text =
      data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    const topics: string[] = JSON.parse(text);

    if (Array.isArray(topics) && topics.length === opportunities.length) {
      // Update cache
      topicCache.set(key, { topics, ts: Date.now() });

      return opportunities.map((o, i) => ({
        ...o,
        topic: topics[i] || o.topic,
      }));
    }

    return opportunities;
  } catch (err) {
    console.error("Topic enrichment error:", err);
    return opportunities;
  }
}

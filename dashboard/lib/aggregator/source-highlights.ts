import type { SocialItem } from "./types";

export function buildSourceHighlights(items: SocialItem[]) {
  const groups: Record<string, SocialItem[]> = {};
  for (const item of items) {
    const source = item._display_source || item.source || "unknown";
    if (!groups[source]) groups[source] = [];
    groups[source].push(item);
  }
  const highlights: any[] = [];
  for (const [source, sourceItems] of Object.entries(groups)) {
    const ranked = [...sourceItems].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
    const top = ranked.slice(0, 3).map(it => {
      const content = it.content || "";
      const snippet = content.slice(0, 120).trimEnd() + (content.length > 120 ? "\u2026" : "");
      return {
        title: (it.title || "").slice(0, 150),
        content_snippet: snippet,
        url: it.source_url || "",
        sentiment: it.sentiment || "neutral",
        category: it.category || "unclassified",
        relevance_score: it.relevance_score || 0,
        product_mentions: it.product_mentions || [],
      };
    });
    highlights.push({ source, count: sourceItems.length, items: top });
  }
  highlights.sort((a, b) => b.count - a.count);
  return highlights;
}

import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { PAIN_CATEGORY_LABELS_DE } from "../../constants";

export function buildPainLandscape(items: SocialItem[]) {
  const prePurchase = items.filter(i =>
    ["awareness", "consideration", "comparison"].includes(i.journey_stage || "") && i.pain_category
  );
  const byCategory: Record<string, { items: SocialItem[]; keywords: string[] }> = {};
  for (const item of prePurchase) {
    const cat = item.pain_category!;
    if (!byCategory[cat]) byCategory[cat] = { items: [], keywords: [] };
    byCategory[cat].items.push(item);
    byCategory[cat].keywords.push(...(item.keywords || []));
  }
  const landscape: any[] = [];
  for (const [cat, data] of Object.entries(byCategory)) {
    const kwCounts = new Counter<string>();
    for (const kw of data.keywords) kwCounts.increment(kw);
    const topThemes = kwCounts.mostCommon(5).map(([kw]) => kw);
    let topQuestion: string | null = null;
    for (const item of data.items) {
      if ((item.title || "").includes("?")) { topQuestion = (item.title || "").slice(0, 120); break; }
    }
    landscape.push({
      category: cat, label_de: PAIN_CATEGORY_LABELS_DE[cat] || cat,
      count: data.items.length, top_themes: topThemes, top_question: topQuestion,
    });
  }
  landscape.sort((a, b) => b.count - a.count);
  return landscape;
}

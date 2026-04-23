import type { SocialItem } from "./types";
import { BEURER_PRODUCTS, COMPETITOR_PRODUCTS, COMPETITOR_BRANDS, ASPECT_LABELS_DE, KEYWORD_TO_ASPECT } from "../constants";
import { Counter } from "./utils";

export function buildProductIntelligence(items: SocialItem[]) {
  const beurerData: Record<string, any> = {};
  const competitorData: Record<string, any> = {};
  const hasEntities = items.some(item => item._entities && item._entities.length > 0);
  // Track unique items that mention any competitor (product or brand)
  const uniqueCompetitorItemIds = new Set<string>();
  const competitorBrandKeys = new Set(Object.keys(COMPETITOR_BRANDS).map(k => k.toLowerCase()));

  if (hasEntities) {
    for (const item of items) {
      const itemSentiment = item.sentiment || "neutral";
      const content = ((item.content || "") + " " + (item.title || "")).toLowerCase();
      // P0 #8: Dedup — track which products we've already counted for this item
      const seenForItem = new Set<string>();
      for (const entityRow of item._entities || []) {
        const entityInfo = entityRow.entities || {};
        const entityType = entityInfo.entity_type || "";
        const canonical = entityInfo.canonical_name || "";
        if (!canonical) continue;
        // Track unique items with any competitor entity (product or brand)
        if (entityType === "competitor_product" || (entityType === "brand" && competitorBrandKeys.has((entityInfo.brand || "").toLowerCase()))) {
          const itemKey = item.id || item.source_url || "";
          if (itemKey) uniqueCompetitorItemIds.add(itemKey);
        }
        const sentiment = entityRow.sentiment || itemSentiment;
        const mentionType = entityRow.mention_type || "direct";
        let dataDict: Record<string, any>;
        if (entityType === "beurer_product") dataDict = beurerData;
        else if (entityType === "competitor_product") dataDict = competitorData;
        else continue;
        // Skip if we already counted this product for this item
        const dedupKey = `${entityType}:${canonical}`;
        if (seenForItem.has(dedupKey)) continue;
        seenForItem.add(dedupKey);
        if (!dataDict[canonical]) {
          dataDict[canonical] = { count: 0, sentiment: { positive: 0, neutral: 0, negative: 0 }, mention_types: {} as Record<string, number>, top_issues: [] as string[], top_praise: [] as string[], aspects: [] };
        }
        dataDict[canonical].count++;
        dataDict[canonical].sentiment[sentiment] = (dataDict[canonical].sentiment[sentiment] || 0) + 1;
        dataDict[canonical].mention_types[mentionType] = (dataDict[canonical].mention_types[mentionType] || 0) + 1;
        const aspects = item._aspects || [];
        if (aspects.length > 0) {
          for (const asp of aspects) {
            const aspKey = asp.aspect || "";
            const aspSent = asp.sentiment || "";
            if (aspSent === "negative" && aspKey && !dataDict[canonical].top_issues.includes(aspKey)) {
              dataDict[canonical].top_issues.push(aspKey);
            } else if (aspSent === "positive" && aspKey && !dataDict[canonical].top_praise.includes(ASPECT_LABELS_DE[aspKey] || aspKey)) {
              dataDict[canonical].top_praise.push(ASPECT_LABELS_DE[aspKey] || aspKey);
            }
          }
        } else {
          if (sentiment === "negative") {
            for (const kw of ["ungenau", "fehler", "defekt", "batterie", "manschette", "app", "teuer", "display", "kompliziert", "support"]) {
              const mapped = KEYWORD_TO_ASPECT[kw];
              if (mapped && content.includes(kw) && !dataDict[canonical].top_issues.includes(mapped)) dataDict[canonical].top_issues.push(mapped);
            }
          }
          if (sentiment === "positive") {
            for (const kw of ["genau", "einfach", "zuverlässig", "empfehlen", "gut", "app", "display"]) {
              if (content.includes(kw) && !dataDict[canonical].top_praise.includes(kw)) dataDict[canonical].top_praise.push(kw);
            }
          }
        }
      }
    }
  } else {
    for (const item of items) {
      const mentions = item.product_mentions || [];
      const sentiment = item.sentiment || "neutral";
      const content = ((item.content || "") + " " + (item.title || "")).toLowerCase();
      for (const product of mentions) {
        let dataDict: Record<string, any>;
        if (BEURER_PRODUCTS.includes(product)) dataDict = beurerData;
        else if (COMPETITOR_PRODUCTS.some(cp => cp.toUpperCase().includes(product.toUpperCase()) || product.toUpperCase().includes(cp.toUpperCase()))) {
          dataDict = competitorData;
          const itemKey = item.id || item.source_url || "";
          if (itemKey) uniqueCompetitorItemIds.add(itemKey);
        }
        else continue;
        if (!dataDict[product]) {
          dataDict[product] = { count: 0, sentiment: { positive: 0, neutral: 0, negative: 0 }, top_issues: [] as string[], top_praise: [] as string[] };
        }
        dataDict[product].count++;
        dataDict[product].sentiment[sentiment] = (dataDict[product].sentiment[sentiment] || 0) + 1;
        if (sentiment === "negative") {
          for (const kw of ["ungenau", "fehler", "defekt", "batterie", "manschette", "app", "teuer", "display", "kompliziert", "support"]) {
            const mapped = KEYWORD_TO_ASPECT[kw];
            if (mapped && content.includes(kw) && !dataDict[product].top_issues.includes(mapped)) dataDict[product].top_issues.push(mapped);
          }
        }
        if (sentiment === "positive") {
          for (const kw of ["genau", "einfach", "zuverlässig", "empfehlen", "gut", "app", "display"]) {
            if (content.includes(kw) && !dataDict[product].top_praise.includes(kw)) dataDict[product].top_praise.push(kw);
          }
        }
      }
    }
  }

  for (const dataDict of [beurerData, competitorData]) {
    for (const product of Object.keys(dataDict)) {
      dataDict[product].top_issues = dataDict[product].top_issues.slice(0, 5);
      dataDict[product].top_praise = dataDict[product].top_praise.slice(0, 5);
    }
  }

  const totalBeurer = Object.values(beurerData).reduce((s: number, p: any) => s + p.count, 0);
  const totalCompetitor = Object.values(competitorData).reduce((s: number, p: any) => s + p.count, 0);
  return {
    beurer: beurerData,
    beurer_total: totalBeurer,
    competitors: competitorData,
    competitors_total: totalCompetitor,
    competitor_mention_count: uniqueCompetitorItemIds.size,
  };
}

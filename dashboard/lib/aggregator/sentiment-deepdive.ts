import type { SocialItem } from "./types";
import { BEURER_PRODUCTS, SENTIMENT_CAUSES, ASPECT_LABELS_DE } from "../constants";
import { Counter, extractRepresentativeQuote } from "./utils";

export function buildSentimentDeepdive(items: SocialItem[]) {
  const negativeItems = items.filter(i => i.sentiment === "negative");
  const totalNegative = negativeItems.length;

  // Part 1: By cause (first-match-wins, sonstiges = catchall)
  const causeKeysOrdered = Object.keys(SENTIMENT_CAUSES).filter(k => k !== "sonstiges");
  const causeData: Record<string, { count: number; items: SocialItem[]; affectedProducts: Set<string> }> = {};
  for (const key of Object.keys(SENTIMENT_CAUSES)) {
    causeData[key] = { count: 0, items: [], affectedProducts: new Set() };
  }

  for (const item of negativeItems) {
    const combined = ((item.title || "") + " " + (item.content || "")).toLowerCase();
    let matched = false;
    for (const causeKey of causeKeysOrdered) {
      const causeInfo = SENTIMENT_CAUSES[causeKey];
      if (causeInfo.keywords.some(kw => combined.includes(kw))) {
        causeData[causeKey].count++;
        causeData[causeKey].items.push(item);
        for (const p of item.product_mentions || []) {
          if (BEURER_PRODUCTS.includes(p)) causeData[causeKey].affectedProducts.add(p);
        }
        matched = true;
        break;
      }
    }
    if (!matched) {
      causeData.sonstiges.count++;
      causeData.sonstiges.items.push(item);
    }
  }

  const byCause: any[] = [];
  for (const [causeKey, causeInfo] of Object.entries(SENTIMENT_CAUSES)) {
    const count = causeData[causeKey].count;
    const pct = totalNegative > 0 ? Math.round((count / totalNegative) * 100) : 0;
    const categoryItems = causeData[causeKey].items;
    let representativeQuote = "";
    if (categoryItems.length > 0) {
      const bestItem = categoryItems.reduce((a, b) => ((b.relevance_score || 0) > (a.relevance_score || 0) ? b : a));
      const title = bestItem.title || "";
      const content = bestItem.content || "";
      const quoteSource = title.length >= 20 ? title : (content || title);
      representativeQuote = extractRepresentativeQuote(quoteSource);
    }
    byCause.push({
      cause_key: causeKey,
      label_de: causeInfo.label_de,
      count,
      percentage: pct,
      affected_products: [...causeData[causeKey].affectedProducts].sort(),
      representative_quote: representativeQuote,
      action: causeInfo.action_default,
      is_actionable: causeInfo.is_actionable,
    });
  }
  byCause.sort((a, b) => b.count - a.count);

  // Part 2: By product (Beurer only)
  const productSentiment: Record<string, any> = {};
  for (const item of items) {
    const itemSentiment = item.sentiment || "neutral";
    const hasEntities = (item._entities || []).length > 0;
    if (hasEntities) {
      for (const entityRow of item._entities || []) {
        const entityInfo = entityRow.entities || {};
        if (entityInfo.entity_type !== "beurer_product") continue;
        const product = entityInfo.canonical_name || "";
        if (!product) continue;
        const sentiment = entityRow.sentiment || itemSentiment;
        if (!productSentiment[product]) {
          productSentiment[product] = { product, total: 0, positive: 0, neutral: 0, negative: 0 };
        }
        productSentiment[product].total++;
        productSentiment[product][sentiment] = (productSentiment[product][sentiment] || 0) + 1;
      }
    } else {
      for (const product of item.product_mentions || []) {
        if (!BEURER_PRODUCTS.includes(product)) continue;
        if (!productSentiment[product]) {
          productSentiment[product] = { product, total: 0, positive: 0, neutral: 0, negative: 0 };
        }
        productSentiment[product].total++;
        productSentiment[product][itemSentiment] = (productSentiment[product][itemSentiment] || 0) + 1;
      }
    }
  }

  const byProduct: any[] = [];
  for (const data of Object.values(productSentiment)) {
    const total = data.total;
    if (total > 0) {
      data.positive_pct = Math.round((data.positive / total) * 100);
      data.neutral_pct = Math.round((data.neutral / total) * 100);
      data.negative_pct = Math.round((data.negative / total) * 100);
      data.needs_attention = data.negative_pct > 20;
    } else {
      data.positive_pct = 0; data.neutral_pct = 0; data.negative_pct = 0; data.needs_attention = false;
    }
    byProduct.push(data);
  }
  byProduct.sort((a, b) => b.total - a.total);

  return {
    by_cause: byCause,
    by_product: byProduct.slice(0, 10),
    total_negative: totalNegative,
    summary: "",
  };
}

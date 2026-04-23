/**
 * Volume aggregation: by source, category, sentiment breakdown, trending topics.
 */
import type { SocialItem } from "./types";
import { Counter, getSourceCategory, roundPercentages } from "./utils";
import { CATEGORY_LABELS_DE, BEURER_PRODUCTS, OTHER_SUBCATEGORIES } from "../constants";

export function buildVolumeData(items: SocialItem[]) {
  // source counts (use _display_source)
  const sources = new Counter();
  const sourceCategories = new Counter();
  const volumeBySourceByCategory: Record<string, Record<string, number>> = {};
  const categories = new Counter();
  const sentiments = new Counter();

  for (const item of items) {
    const src = item._display_source || item.source || "unknown";
    sources.increment(src);
    const srcCat = getSourceCategory(src);
    sourceCategories.increment(srcCat);
    
    const cat = item.category || "unclassified";
    categories.increment(cat);
    sentiments.increment(item.sentiment || "unknown");

    if (!volumeBySourceByCategory[cat]) volumeBySourceByCategory[cat] = {};
    volumeBySourceByCategory[cat][srcCat] = (volumeBySourceByCategory[cat][srcCat] || 0) + 1;
  }

  const total = items.length;

  // Sentiment by category
  const sentimentByCategory: Record<string, any> = {};
  for (const cat of ["blood_pressure", "pain_tens", "infrarot", "menstrual", "other"]) {
    const catItems = items.filter(i => i.category === cat);
    if (catItems.length > 0) {
      const cs = new Counter();
      for (const i of catItems) cs.increment(i.sentiment || "unknown");
      const tc = catItems.length;
      const sentCounts: Record<string, number> = {
        positive: cs.get("positive"),
        neutral: cs.get("neutral"),
        negative: cs.get("negative"),
      };
      const pct = roundPercentages(sentCounts, tc);
      sentimentByCategory[cat] = { ...pct, count: tc };
    }
  }

  // Trending topics
  const allKeywords = new Counter();
  for (const item of items) {
    for (const kw of item.keywords || []) allKeywords.increment(kw);
  }
  const trendingTopics = allKeywords.mostCommon(15).map(([topic, count]) => ({ topic, count }));

  return {
    volume_by_source: sources.toRecord(),
    volume_by_source_category: sourceCategories.toRecord(),
    volume_by_source_by_category: volumeBySourceByCategory,
    volume_by_category: categories.toRecord(),
    sentiment_by_category: sentimentByCategory,
    trending_topics: trendingTopics,
    total_items: total,
    sentiments,
    categories,
  };
}

/** Check if an item has Beurer entity matches or product_mentions containing a Beurer product. */
function isBeurerBrandItem(item: SocialItem): boolean {
  // Check _entities for beurer_product entity_type
  const entities = item._entities || [];
  for (const entityRow of entities) {
    const entityInfo = entityRow.entities || {};
    if (entityInfo.entity_type === "beurer_product") return true;
  }
  // Check product_mentions against BEURER_PRODUCTS
  const mentions = item.product_mentions || [];
  for (const mention of mentions) {
    if (BEURER_PRODUCTS.includes(mention)) return true;
  }
  return false;
}

/** Split items into brand (Beurer-related) and topic (health topics) sentiment. */
export function buildBrandTopicSentiment(items: SocialItem[]): {
  brand_sentiment: { positive: number; neutral: number; negative: number; total: number; note: string };
  topic_sentiment: { positive: number; neutral: number; negative: number; total: number; note: string };
} {
  const brandItems: SocialItem[] = [];
  const topicItems: SocialItem[] = [];

  for (const item of items) {
    if (isBeurerBrandItem(item)) {
      brandItems.push(item);
    } else {
      topicItems.push(item);
    }
  }

  const computePct = (subset: SocialItem[]) => {
    const total = subset.length;
    if (total === 0) return { positive: 0, neutral: 0, negative: 0 };
    const sentCounts = { positive: 0, neutral: 0, negative: 0 };
    for (const item of subset) {
      const s = item.sentiment;
      if (s === "positive") sentCounts.positive++;
      else if (s === "negative") sentCounts.negative++;
      else sentCounts.neutral++;
    }
    return roundPercentages(sentCounts, total);
  };

  const brandPct = computePct(brandItems);
  const topicPct = computePct(topicItems);

  return {
    brand_sentiment: {
      positive: brandPct.positive,
      neutral: brandPct.neutral,
      negative: brandPct.negative,
      total: brandItems.length,
      note: "Sentiment toward Beurer products specifically",
    },
    topic_sentiment: {
      positive: topicPct.positive,
      neutral: topicPct.neutral,
      negative: topicPct.negative,
      total: topicItems.length,
      note: "Sentiment about health topics (pain, BP, etc.)",
    },
  };
}

/** Classify "other" items into subcategories using keyword matching. */
export function buildOtherBreakdown(items: SocialItem[]): Record<string, number> {
  const otherItems = items.filter(item => item.category === "other");
  const breakdown: Record<string, number> = {};

  // Initialize all subcategories to 0
  for (const key of Object.keys(OTHER_SUBCATEGORIES)) {
    breakdown[key] = 0;
  }

  for (const item of otherItems) {
    const combined = ((item.title || "") + " " + (item.content || "")).toLowerCase();
    let matched = false;

    // Check each subcategory (except unrelated) for keyword matches
    for (const [subKey, subInfo] of Object.entries(OTHER_SUBCATEGORIES)) {
      if (subKey === "unrelated") continue;
      if (subInfo.keywords.some(kw => combined.includes(kw))) {
        breakdown[subKey]++;
        matched = true;
        break; // first-match-wins
      }
    }

    if (!matched) {
      breakdown.unrelated++;
    }
  }

  return breakdown;
}

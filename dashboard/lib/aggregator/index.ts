/**
 * Main aggregator entry point — assembles the full DashboardData object.
 * Ported from aggregate_report_data() in data_aggregator.py (line 3061).
 */
import type { SocialItem, DashboardData } from "./types";
import {
  Counter, getSourceCategory, applyRelevanceFloor, getTopQualityPosts,
  categorizeQuestion, isDeviceQuestion, isCompetitorSpecificQuestion,
  scoreDeviceRelevance, isBeurerOwn, isRetailerListing, roundPercentages,
} from "./utils";
import { CATEGORY_LABELS_DE, BEURER_PRODUCTS, BEURER_PRODUCT_CATALOG, PURCHASE_INTENT_PATTERNS, DEVICE_KEYWORDS, BRAND_NAMES, COMPETITOR_BRANDS } from "../constants";

import { buildVolumeData, buildBrandTopicSentiment, buildOtherBreakdown } from "./volume";
import { buildAlerts } from "./alerts";
import { buildProductIntelligence } from "./product-intelligence";
import { buildAppendices } from "./appendices";
import { buildSourceHighlights } from "./source-highlights";
import { buildKeyActions } from "./key-actions";
import { buildExecutiveDashboard } from "./executive-dashboard";
import { buildContentOpportunities } from "./content-opportunities";
import { buildUserVoice } from "./user-voice";
import { buildSentimentDeepdive } from "./sentiment-deepdive";
import { buildCompetitiveIntelligence } from "./competitive-intelligence";
import { aggregateJourneyData } from "./journey/index";
import { aggregateDeepInsights } from "./deep-insights/index";
import { aggregateDeepInsightsByCategory } from "./deep-insights/by-category";
import { aggregateCategoryJourneys } from "./journey/category-journeys";
import { buildNewsData } from "./news";

/** Match Beurer products from product_mentions and entity data. */
function matchBeurerProducts(item: SocialItem): string[] {
  const matched = new Set<string>();

  // Check product_mentions
  for (const mention of item.product_mentions || []) {
    if (BEURER_PRODUCTS.includes(mention)) {
      matched.add(mention);
    }
  }

  // Check entities
  for (const entityRow of item._entities || []) {
    const entityInfo = entityRow.entities || {};
    if (entityInfo.entity_type === "beurer_product" && entityInfo.canonical_name) {
      matched.add(entityInfo.canonical_name);
    }
  }

  return [...matched];
}

/** Build purchase intent feed from items. */
function buildPurchaseIntentFeed(items: SocialItem[]): Array<{
  title: string;
  source: string;
  source_url: string;
  category: string;
  intent_signal: string;
  reach_estimate: number;
  posted_at: string;
  matched_products: string[];
  device_relevance_score: number;
}> {
  const feed: Array<{
    title: string;
    source: string;
    source_url: string;
    category: string;
    intent_signal: string;
    reach_estimate: number;
    posted_at: string;
    matched_products: string[];
    device_relevance_score: number;
  }> = [];

  for (const item of items) {
    const isPurchaseIntent = item.intent === "purchase_question";
    let isImplicitPurchase = false;
    const combined = ((item.title || "") + " " + (item.content || "")).toLowerCase();

    if (!isPurchaseIntent) {
      isImplicitPurchase = PURCHASE_INTENT_PATTERNS.some(p => combined.includes(p));
    }

    if (!isPurchaseIntent && !isImplicitPurchase) continue;

    // Exclude items not in Beurer's device categories
    const cat = item.category || "other";
    if (cat === "other" || cat === "unclassified") continue;

    // Relevance floor: skip low-relevance items unless they mention specific products
    const relevance = item.relevance_score || 0;
    if (relevance < 0.3 && !(item.product_mentions && item.product_mentions.length > 0)) continue;

    // Skip purchase-intent items that aren't device-related
    const deviceRel = item.device_relevance_score || 0;
    const hasProducts = (item.product_mentions || []).length > 0;
    const hasEntities = (item._entities || []).length > 0;
    if (deviceRel < 0.4 && !hasProducts && !hasEntities) continue;

    // For implicit purchase (pattern-matched, not LLM-classified), additionally
    // require device/brand context in the text to avoid generic health posts
    if (!isPurchaseIntent && isImplicitPurchase) {
      const hasDeviceContext =
        DEVICE_KEYWORDS.some(kw => combined.includes(kw)) ||
        BRAND_NAMES.some(b => combined.includes(b));
      if (!hasDeviceContext && !hasProducts && !hasEntities) continue;
    }

    feed.push({
      title: (item.title || "").slice(0, 150),
      source: item._display_source || item.source || "unknown",
      source_url: item.source_url || "",
      category: item.category || "other",
      intent_signal: isPurchaseIntent ? "direct_purchase" : "implicit_purchase",
      reach_estimate: item.engagement_score || 0,
      posted_at: item.posted_at || "",
      matched_products: matchBeurerProducts(item),
      device_relevance_score: item.device_relevance_score || 0,
    });
  }

  // Sort by reach_estimate descending, limit to 20
  feed.sort((a, b) => b.reach_estimate - a.reach_estimate);
  return feed.slice(0, 20);
}

/** Compute WoW metrics from current and previous period items. */
function computeWowMetrics(
  currentItems: SocialItem[],
  previousItems: SocialItem[],
  currentTotal: number,
  currentSentimentPct: Record<string, number>,
  currentCompetitorMentions: number,
): Record<string, any> {
  const prevTotal = previousItems.length;
  if (prevTotal === 0) return { available: false };

  const mentionsDelta = currentTotal - prevTotal;
  const mentionsPct = prevTotal > 0 ? Math.round((mentionsDelta / prevTotal) * 1000) / 10 : null;

  let mentionsChange: string;
  if (mentionsDelta > 0) {
    mentionsChange = `+${mentionsDelta}`;
    if (mentionsPct !== null) mentionsChange += ` (+${mentionsPct}%)`;
  } else if (mentionsDelta < 0) {
    mentionsChange = `${mentionsDelta}`;
    if (mentionsPct !== null) mentionsChange += ` (${mentionsPct}%)`;
  } else {
    mentionsChange = "\u00b10";
  }

  // Previous period sentiment
  const prevSentiments = new Counter();
  for (const item of previousItems) prevSentiments.increment(item.sentiment || "unknown");
  const prevPositivePct = prevTotal > 0 ? Math.round((prevSentiments.get("positive") / prevTotal) * 100) : 0;
  const prevNegativePct = prevTotal > 0 ? Math.round((prevSentiments.get("negative") / prevTotal) * 100) : 0;

  // Previous competitor mentions (count unique items with any competitor entity)
  const competitorBrandKeys = new Set(Object.keys(COMPETITOR_BRANDS).map(k => k.toLowerCase()));
  let prevCompetitorMentions = 0;
  for (const item of previousItems) {
    const entities = item._entities || [];
    const hasCompetitorEntity = entities.some(e => {
      const eType = e.entities?.entity_type;
      if (eType === "competitor_product") return true;
      if (eType === "brand" && competitorBrandKeys.has((e.entities?.brand || "").toLowerCase())) return true;
      return false;
    });
    if (hasCompetitorEntity) {
      prevCompetitorMentions++;
    }
  }

  return {
    available: true,
    mentions_change: mentionsChange,
    mentions_change_pct: mentionsPct,
    mentions_delta: mentionsDelta,
    positive_pct_change: Math.round(((currentSentimentPct.positive || 0) - prevPositivePct) * 10) / 10,
    negative_pct_change: Math.round(((currentSentimentPct.negative || 0) - prevNegativePct) * 10) / 10,
    competitor_change: currentCompetitorMentions - prevCompetitorMentions,
    prev_mentions: prevTotal,
    prev_positive_pct: prevPositivePct,
    prev_negative_pct: prevNegativePct,
  };
}

export function aggregateReportData(
  rawItems: SocialItem[],
  startDate: string,
  endDate: string,
  previousItems?: SocialItem[],
): DashboardData {
  // Exclude Beurer's own domains
  const items = rawItems.filter(item => !isBeurerOwn(item) && !isRetailerListing(item));
  const totalItems = items.length;

  // Volume data
  const vol = buildVolumeData(items);
  const { sentiments, categories } = vol;

  // Product intelligence
  const productIntelligence = buildProductIntelligence(items);
  const totalBeurer = productIntelligence.beurer_total;
  const totalCompetitor = productIntelligence.competitors_total;
  const competitorMentionCount = productIntelligence.competitor_mention_count;

  // Filtered items (relevance floor)
  const filteredItems = applyRelevanceFloor(items);

  // Alerts & appendices
  const alerts = buildAlerts(filteredItems);
  const appendices = buildAppendices(filteredItems);

  // Top quality posts
  const topQuality = getTopQualityPosts(filteredItems, 20);
  const topPosts = topQuality.map(item => ({
    id: item.id,
    source: item.source || "Unbekannt",
    resolved_source: item.resolved_source || item.source || "",
    title: (item.title || "Ohne Titel").slice(0, 150),
    content: (item.content || "").slice(0, 500),
    url: item.source_url || "",
    category: item.category || "unclassified",
    sentiment: item.sentiment || "neutral",
    relevance_score: item.relevance_score || 0,
    device_relevance_score: item.device_relevance_score || 0,
    posted_at: item.posted_at || "",
    keywords: item.keywords || [],
    product_mentions: item.product_mentions || [],
    engagement_score: item.engagement_score || 0,
    emotion: item.emotion || "",
    journey_stage: item.journey_stage || "",
  }));

  // User voice (top questions + pain points)
  const { user_voice, device_questions_count } = buildUserVoice(items, filteredItems);

  // Content opportunities
  const contentOpportunities = buildContentOpportunities(items);

  // Executive summary
  const topCategory = categories.mostCommon(1).length > 0 ? categories.mostCommon(1)[0][0] : "unknown";
  const negativePct = totalItems > 0 ? Math.round((sentiments.get("negative") / totalItems) * 100) : 0;
  const topCategoryDe = CATEGORY_LABELS_DE[topCategory] || topCategory.replace(/_/g, " ");
  const topCategoryCount = categories.get(topCategory);

  let keyInsight = `${topCategoryDe}-Diskussionen dominieren mit ${topCategoryCount} Erwähnungen. `;
  if (negativePct > 30) {
    keyInsight += `Sentiment-Warnung: ${negativePct}% negative Stimmung erfordert Aufmerksamkeit.`;
  } else {
    keyInsight += `Das Gesamtsentiment ist ausgeglichen mit ${negativePct}% negativen Erwähnungen.`;
  }

  // #4: Sentiment math with unclassified + largest-remainder rounding
  const knownSentiments = sentiments.get("positive") + sentiments.get("neutral") + sentiments.get("negative");
  const unclassifiedCount = totalItems - knownSentiments;
  const sentimentCounts = {
    positive: sentiments.get("positive"),
    neutral: sentiments.get("neutral"),
    negative: sentiments.get("negative"),
    unclassified: Math.max(0, unclassifiedCount),
  };
  const overallSentimentPct = roundPercentages(sentimentCounts, totalItems);

  const executiveSummary = {
    total_mentions: totalItems,
    overall_sentiment: {
      positive: sentiments.get("positive"),
      neutral: sentiments.get("neutral"),
      negative: sentiments.get("negative"),
    },
    overall_sentiment_pct: overallSentimentPct,
    key_insight: keyInsight,
    top_category: topCategory,
    top_category_count: topCategoryCount,
    negative_pct: negativePct,
    competitor_mention_count: competitorMentionCount,
    device_questions_count: device_questions_count,
  };

  // #5: Brand vs Topic sentiment
  const { brand_sentiment, topic_sentiment } = buildBrandTopicSentiment(items);

  // #1: Other breakdown
  const other_breakdown = buildOtherBreakdown(items);

  // #11: Purchase intent feed
  const purchase_intent_feed = buildPurchaseIntentFeed(items);

  // Competitive intelligence
  const competitive_intelligence = buildCompetitiveIntelligence(filteredItems, productIntelligence);

  // #6: WoW metrics
  const wowMetrics = previousItems
    ? computeWowMetrics(items, previousItems.filter(item => !isBeurerOwn(item) && !isRetailerListing(item)), totalItems, overallSentimentPct, competitorMentionCount)
    : { available: false };

  // Compute ISO week from start date
  const startD = new Date(startDate);
  const dt = new Date(Date.UTC(startD.getFullYear(), startD.getMonth(), startD.getDate()));
  dt.setUTCDate(dt.getUTCDate() + 4 - (dt.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(dt.getUTCFullYear(), 0, 1));
  const weekNumber = Math.ceil((((dt.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);

  return {
    _source: "dynamic",
    period: { start: startDate, end: endDate, week_number: weekNumber },
    generated_at: new Date().toISOString(),

    executive_summary: executiveSummary,
    alerts,
    volume_by_source: vol.volume_by_source,
    volume_by_source_category: vol.volume_by_source_category,
    volume_by_source_by_category: vol.volume_by_source_by_category,
    volume_by_category: vol.volume_by_category,
    sentiment_by_category: vol.sentiment_by_category,
    trending_topics: vol.trending_topics,
    product_intelligence: productIntelligence,
    product_mentions: {
      beurer: Object.fromEntries(
        Object.entries(productIntelligence.beurer).map(([p, d]: [string, any]) => [p, d.count])
      ),
      beurer_total: totalBeurer,
      competitors: Object.fromEntries(
        Object.entries(productIntelligence.competitors).map(([p, d]: [string, any]) => [p, d.count])
      ),
      competitors_total: totalCompetitor,
      competitor_mention_count: competitorMentionCount,
    },
    user_voice,
    content_opportunities: contentOpportunities,
    top_posts: topPosts,
    source_highlights: buildSourceHighlights(filteredItems),
    appendices,
    // #7: Executive dashboard with deterministic insights/actions
    executive_dashboard: buildExecutiveDashboard(executiveSummary, {
      volume_by_category: vol.volume_by_category,
      alerts,
      competitive_intelligence,
      wow_metrics: wowMetrics,
    }),
    key_actions: buildKeyActions(alerts, appendices),
    sentiment_deepdive: buildSentimentDeepdive(filteredItems),
    competitive_intelligence,
    journey_intelligence: aggregateJourneyData(filteredItems),
    deep_insights: aggregateDeepInsights(filteredItems),
    category_deep_insights: aggregateDeepInsightsByCategory(filteredItems),
    category_journeys: aggregateCategoryJourneys(filteredItems),
    wow_metrics: wowMetrics,
    brand_sentiment,
    topic_sentiment,
    other_breakdown,
    purchase_intent_feed,
    news: buildNewsData(items),
  };
}

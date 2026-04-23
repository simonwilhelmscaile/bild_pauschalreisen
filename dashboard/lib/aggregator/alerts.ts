import type { SocialItem } from "./types";
import { getEngagementCount, buildContentPreview } from "./utils";
import { EMOTION_WEIGHTS, INTENT_ALERT_MULTIPLIERS } from "../constants";

/**
 * Compute a composite alert score (0-100) for an item using multiple signals:
 * sentiment_intensity, emotion, intent, relevance, device relevance,
 * engagement, entity negative %, and aspect clustering.
 */
function computeCompositeScore(item: SocialItem): number {
  // sentiment_intensity (1-5) → normalise to 0-1
  const intensity = (item.sentiment_intensity ?? 3) / 5;

  // emotion weight
  const emotionScore = EMOTION_WEIGHTS[item.emotion || ""] ?? 0.3;

  // intent weight (normalise by max multiplier of 1.5)
  const intentScore = (INTENT_ALERT_MULTIPLIERS[item.intent || ""] ?? 0.5) / 1.5;

  // relevance scores (already 0-1)
  const relevance = item.relevance_score || 0;
  const deviceRelevance = item.device_relevance_score || 0;

  // engagement normalised
  const engagementRaw = getEngagementCount(item) || 0;
  const engagementNorm = Math.min(engagementRaw, 100) / 100;

  // entity negative percentage
  const entities = item._entities || [];
  let entityNegPct = 0;
  if (entities.length > 0) {
    const negCount = entities.filter(e => e.sentiment === "negative").length;
    entityNegPct = negCount / entities.length;
  }

  // aspect clustering: 2+ negative aspects on same item → 1
  const aspects = item._aspects || [];
  const negAspectCount = aspects.filter(a => a.sentiment === "negative").length;
  const aspectCluster = negAspectCount >= 2 ? 1 : 0;

  return (
    intensity * 15 +
    emotionScore * 15 +
    intentScore * 10 +
    relevance * 15 +
    deviceRelevance * 10 +
    engagementNorm * 10 +
    entityNegPct * 15 +
    aspectCluster * 10
  );
}

function getSeverity(score: number): string {
  if (score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}

export function buildAlerts(items: SocialItem[]) {
  const alerts: { critical: any[]; monitor: any[]; opportunity: any[] } = {
    critical: [], monitor: [], opportunity: [],
  };

  // Track negative aspects per product for systemic detection
  const productAspectNeg: Record<string, Record<string, number>> = {};

  for (const item of items) {
    // P2 #9: Skip low-relevance items with no product/entity associations
    const deviceRel = item.device_relevance_score || 0;
    const productMentions = item.product_mentions || [];
    const entities = item._entities || [];
    if (deviceRel < 0.5 && productMentions.length === 0 && entities.length === 0) continue;

    const sentiment = item.sentiment;
    const compositeScore = computeCompositeScore(item);
    const title = (item.title || "").slice(0, 200);
    const content = (item.question_content || item.content || "").slice(0, 500);
    const aspects = item._aspects || [];

    // Entity-derived fields
    const involvedEntities = entities
      .map(e => e.entities?.canonical_name)
      .filter((n): n is string => !!n);
    const uniqueEntities = [...new Set(involvedEntities)];

    const entityNegPct = entities.length > 0
      ? entities.filter(e => e.sentiment === "negative").length / entities.length
      : 0;

    const negativeAspects = aspects
      .filter(a => a.sentiment === "negative")
      .map(a => a.aspect)
      .filter((a): a is string => !!a);

    // Accumulate per-product negative aspects for systemic detection
    if (sentiment === "negative") {
      for (const ent of entities) {
        const name = ent.entities?.canonical_name;
        if (!name) continue;
        for (const asp of negativeAspects) {
          if (!productAspectNeg[name]) productAspectNeg[name] = {};
          productAspectNeg[name][asp] = (productAspectNeg[name][asp] || 0) + 1;
        }
      }
    }

    // Description: prefer key_insight, fall back to content preview
    const description = item.key_insight || buildContentPreview(item) || "";

    // Shared fields for all alert types (backward-compatible)
    const base = {
      title, content,
      content_preview: buildContentPreview(item),
      source: item._display_source || item.source,
      url: item.source_url,
      category: item.category,
      emotion: item.emotion,
      intent: item.intent,
      sentiment_intensity: item.sentiment_intensity,
      answer_count: item.answer_count || 0,
      // New composite fields
      alert_score: Math.round(compositeScore * 10) / 10,
      severity: getSeverity(compositeScore),
      root_cause: item.negative_root_cause || null,
      involved_entities: uniqueEntities,
      negative_aspects: negativeAspects,
      description,
    };

    // Critical: negative + score >= 50 + (product mentions OR complaint intent OR entity neg > 50%)
    if (
      sentiment === "negative" &&
      compositeScore >= 50 &&
      (productMentions.length > 0 || item.intent === "complaint" || entityNegPct > 0.5)
    ) {
      alerts.critical.push({
        ...base,
        type: "negative_product_mention",
        product: productMentions[0] || null,
        all_products: productMentions,
        relevance_score: item.relevance_score || 0,
        device_relevance_score: item.device_relevance_score || 0,
        engagement_count: getEngagementCount(item),
        sentiment_context: `Negative - score ${compositeScore.toFixed(0)}`,
        topic_summary: null,
        problem_description: null,
        recommendation: null,
      });
    }
    // Monitor: neutral/negative + score >= 30
    else if (
      (sentiment === "neutral" || sentiment === "negative") &&
      compositeScore >= 30
    ) {
      alerts.monitor.push({
        ...base,
        type: "device_discussion",
        device_relevance_score: item.device_relevance_score || 0,
        topic_summary: null,
        context: null,
      });
    }
    // Opportunity: positive + score >= 25
    // Skip purchase-intent items that aren't device-related (e.g. buying cigarettes)
    else if (
      sentiment === "positive" &&
      compositeScore >= 25 &&
      !(item.intent === "purchase_question" && deviceRel < 0.5 && productMentions.length === 0 && entities.length === 0)
    ) {
      alerts.opportunity.push({
        ...base,
        type: "positive_mention",
        product: productMentions[0] || null,
        all_products: productMentions,
        device_relevance_score: item.device_relevance_score || 0,
        topic_summary: null,
        opportunity_description: null,
        recommendation: null,
      });
    }
  }

  // Systemic product issue detection: if a single aspect has 3+ negative
  // mentions for one product, emit a synthetic critical alert
  for (const [product, aspectCounts] of Object.entries(productAspectNeg)) {
    for (const [aspect, count] of Object.entries(aspectCounts)) {
      if (count >= 3) {
        alerts.critical.push({
          type: "systemic_product_issue",
          title: `Systematisches Problem: ${aspect} bei ${product}`,
          content: `${count} negative Erwähnungen des Aspekts "${aspect}" für ${product}`,
          content_preview: `${count}x negativ: ${aspect}`,
          source: "aggregated",
          url: "",
          category: null,
          emotion: null,
          intent: null,
          sentiment_intensity: null,
          answer_count: 0,
          alert_score: Math.min(100, 50 + count * 5),
          severity: count >= 5 ? "high" : "medium",
          root_cause: null,
          involved_entities: [product],
          negative_aspects: [aspect],
          description: `${count} Nutzer berichten über Probleme mit "${aspect}" bei ${product}`,
          product,
          all_products: [product],
          relevance_score: 1.0,
          device_relevance_score: 1.0,
          engagement_count: null,
          sentiment_context: `Systemic - ${count} mentions`,
          topic_summary: `${aspect} issue for ${product}`,
          problem_description: null,
          recommendation: `Aspekt "${aspect}" bei ${product} prüfen (${count} negative Erwähnungen)`,
        });
      }
    }
  }

  // Sort all buckets by alert_score descending, cap at 5
  alerts.critical.sort((a, b) => (b.alert_score || 0) - (a.alert_score || 0));
  alerts.critical = alerts.critical.slice(0, 5);
  alerts.monitor.sort((a, b) => (b.alert_score || 0) - (a.alert_score || 0));
  alerts.monitor = alerts.monitor.slice(0, 5);
  alerts.opportunity.sort((a, b) => (b.alert_score || 0) - (a.alert_score || 0));
  alerts.opportunity = alerts.opportunity.slice(0, 5);

  return alerts;
}

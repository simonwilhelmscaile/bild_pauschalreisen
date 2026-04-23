import type { SocialItem } from "../types";
import { Counter, extractRepresentativeQuote, buildContentPreview } from "../utils";
import {
  JOURNEY_STAGES, JOURNEY_STAGE_LABELS_DE, LIFE_SITUATION_LABELS_DE,
  COPING_STRATEGY_LABELS_DE, FRUSTRATION_LABELS_DE, PAIN_CATEGORY_LABELS_DE,
  BRIDGE_MOMENT_TYPES, CATEGORY_PAIN_CATEGORIES,
} from "../../constants";
import { buildJourneyFunnel } from "./funnel";
import { buildPainBreakdown } from "./pain-breakdown";
import { buildBpProfile } from "./bp-profile";
import { buildBridgeMoments } from "./bridge-moments";

function countFieldDist(items: SocialItem[], field: keyof SocialItem, labelsDe: Record<string, string>, limit = 5) {
  const counts = new Counter<string>();
  for (const i of items) { const v = i[field]; if (v && typeof v === "string") counts.increment(v); }
  const total = counts.total() || 1;
  return counts.mostCommon(limit).map(([k, c]) => ({ key: k, label_de: labelsDe[k] || k, count: c, pct: Math.round((c / total) * 100) }));
}

function countArrayDist(items: SocialItem[], field: keyof SocialItem, labelsDe: Record<string, string>, limit = 5) {
  const counts = new Counter<string>();
  for (const item of items) {
    const arr = item[field] as string[] | undefined;
    if (Array.isArray(arr)) for (const v of arr) counts.increment(v);
  }
  const total = counts.total() || 1;
  return counts.mostCommon(limit).map(([k, c]) => ({ key: k, label_de: labelsDe[k] || k, count: c, pct: Math.round((c / total) * 100) }));
}

function getSentimentPcts(items: SocialItem[]) {
  const total = items.length || 1;
  const s = new Counter<string>();
  for (const i of items) s.increment(i.sentiment || "neutral");
  return {
    positive: Math.round((s.get("positive") / total) * 100),
    neutral: Math.round((s.get("neutral") / total) * 100),
    negative: Math.round((s.get("negative") / total) * 100),
  };
}

function extractTopQuestions(items: SocialItem[], limit = 3) {
  const questions: any[] = [];
  for (const item of items) {
    if ((item.title || "").includes("?")) {
      questions.push({ title: (item.title || "").slice(0, 150), source: item.source || "", url: item.source_url || "" });
      if (questions.length >= limit) break;
    }
  }
  return questions;
}

function extractKeyInsights(items: SocialItem[], limit = 2) {
  const insights: any[] = [];
  for (const item of items) {
    if (item.key_insight) {
      insights.push({ insight: String(item.key_insight).slice(0, 200), source: item.source || "" });
      if (insights.length >= limit) break;
    }
  }
  return insights;
}

/** Build per-stage pain breakdown, filtered to only pain categories relevant to catKey. */
function buildStagePainBreakdown(stageItems: SocialItem[], catKey: string | null) {
  const allowed = catKey ? CATEGORY_PAIN_CATEGORIES[catKey] : null;
  const painCounts = new Counter<string>();
  for (const i of stageItems) {
    if (!i.pain_category) continue;
    if (allowed && !allowed.includes(i.pain_category)) continue;
    painCounts.increment(i.pain_category);
  }
  return painCounts.mostCommon(5).map(([pk, pc]) => {
    const painItems = stageItems.filter(i => i.pain_category === pk);
    const quoteItem = painItems.find(i => (i.title || "").includes("?"));
    let quote = "";
    if (quoteItem) quote = extractRepresentativeQuote(quoteItem.title || "");
    else if (painItems.length > 0) quote = extractRepresentativeQuote(painItems[0].question_content || painItems[0].content || "");
    return { pain_category: pk, label_de: PAIN_CATEGORY_LABELS_DE[pk] || pk, count: pc, quote };
  });
}

/** Build per-stage bridge moments. */
function buildStageBridgeMoments(stageItems: SocialItem[]) {
  const bridgeCounts = new Counter<string>();
  for (const i of stageItems) {
    if (i.bridge_moment && i.bridge_moment !== "none_identified") bridgeCounts.increment(i.bridge_moment);
  }
  return bridgeCounts.mostCommon(3).map(([k, c]) => ({
    bridge_type: k, label_de: BRIDGE_MOMENT_TYPES[k] || k, count: c,
  }));
}

/** Build per-stage representative quotes. */
function buildStageQuotes(stageItems: SocialItem[], limit = 3) {
  const sorted = [...stageItems].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
  const quotes: any[] = [];
  for (const item of sorted.slice(0, limit)) {
    const text = item.question_content || item.content || "";
    const quote = extractRepresentativeQuote(text);
    if (quote) quotes.push({
      text: quote, source: item._display_source || item.source || "unknown", url: item.source_url || "",
    });
  }
  return quotes;
}

function buildEmotionIntentDist(stageItems: SocialItem[]) {
  const emotionCounts = new Counter<string>();
  const intentCounts = new Counter<string>();
  for (const i of stageItems) {
    if (i.emotion) emotionCounts.increment(i.emotion);
    if (i.intent) intentCounts.increment(i.intent);
  }
  const emotionTotal = emotionCounts.total() || 1;
  const intentTotal = intentCounts.total() || 1;
  const emotionDist: Record<string, number> = {};
  for (const [k, c] of emotionCounts.mostCommon(4)) emotionDist[k] = Math.round((c / emotionTotal) * 100);
  const intentDist: Record<string, number> = {};
  for (const [k, c] of intentCounts.mostCommon(4)) intentDist[k] = Math.round((c / intentTotal) * 100);
  return { emotion_distribution: emotionDist, intent_distribution: intentDist };
}

function buildCategoryStages(catItems: SocialItem[], catKey: string | null = null) {
  const totalCat = catItems.length;
  return JOURNEY_STAGES.map(stage => {
    const stageItems = catItems.filter(i => i.journey_stage === stage);
    const count = stageItems.length;
    const sorted = [...stageItems].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
    const { emotion_distribution, intent_distribution } = buildEmotionIntentDist(stageItems);
    return {
      stage, label_de: JOURNEY_STAGE_LABELS_DE[stage] || stage,
      count, percentage: totalCat > 0 ? Math.round((count / totalCat) * 100) : 0,
      life_situations: countFieldDist(stageItems, "life_situation", LIFE_SITUATION_LABELS_DE, 5),
      coping_strategies: countArrayDist(stageItems, "coping_strategies", COPING_STRATEGY_LABELS_DE, 5),
      frustrations: countFieldDist(stageItems, "negative_root_cause", FRUSTRATION_LABELS_DE, 5),
      emotional_state: getSentimentPcts(stageItems),
      emotion_distribution, intent_distribution,
      top_questions: extractTopQuestions(stageItems, 3),
      key_insights: extractKeyInsights(stageItems, 2),
      pain_breakdown: buildStagePainBreakdown(stageItems, catKey),
      bridge_to_next: buildStageBridgeMoments(stageItems),
      representative_quotes: buildStageQuotes(stageItems),
      all_posts: sorted.map(i => ({
        title: (i.title || "").slice(0, 150),
        source: i._display_source || i.source || "",
        url: i.source_url || "", sentiment: i.sentiment || "",
        posted_at: i.posted_at || "", content_preview: buildContentPreview(i),
        device_relevance_score: i.device_relevance_score || 0,
      })),
    };
  });
}

/** Filter pain_breakdown output to only include pain categories relevant to catKey. */
function filterPainBreakdown(pb: Record<string, any>, catKey: string): Record<string, any> {
  const allowed = CATEGORY_PAIN_CATEGORIES[catKey];
  if (!allowed) return pb;
  const filteredTotal = (pb.categories || [])
    .filter((c: any) => allowed.includes(c.pain_category))
    .reduce((s: number, c: any) => s + (c.count || 0), 0);
  const filtered = (pb.categories || [])
    .filter((c: any) => allowed.includes(c.pain_category))
    .map((c: any) => ({
      ...c,
      percentage: filteredTotal > 0 ? Math.round(((c.count || 0) / filteredTotal) * 100) : 0,
    }));
  return {
    ...pb,
    categories: filtered,
    total: filteredTotal,
    resolved_sonstige: allowed.includes("sonstige_schmerzen") ? pb.resolved_sonstige : [],
  };
}

export function aggregateCategoryJourneys(items: SocialItem[]) {
  const TARGET: Record<string, string> = { blood_pressure: "Blutdruck", pain_tens: "Schmerz/TENS", menstrual: "Menstruation" };
  const result: Record<string, any> = {};

  for (const [catKey, catLabel] of Object.entries(TARGET)) {
    const catItems = items.filter(i => i.journey_stage && i.category === catKey);
    if (catItems.length === 0) continue;
    result[catKey] = {
      label_de: catLabel, total_items: catItems.length,
      stages: buildCategoryStages(catItems, catKey),
      funnel: buildJourneyFunnel(catItems),
      pain_breakdown: filterPainBreakdown(buildPainBreakdown(catItems), catKey),
      bp_profile: buildBpProfile(catItems),
      bridge_moments: buildBridgeMoments(catItems),
      narrative: "",
    };
  }

  const allJourney = items.filter(i => i.journey_stage);
  if (allJourney.length > 0) {
    result.all = {
      label_de: "Alle Kategorien", total_items: allJourney.length,
      stages: buildCategoryStages(allJourney),
      funnel: buildJourneyFunnel(allJourney),
      pain_breakdown: buildPainBreakdown(allJourney),
      bp_profile: buildBpProfile(allJourney),
      bridge_moments: buildBridgeMoments(allJourney),
      narrative: "",
    };
  }
  return result;
}

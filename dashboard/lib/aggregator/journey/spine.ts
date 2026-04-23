import type { SocialItem } from "../types";
import { Counter, extractRepresentativeQuote } from "../utils";
import {
  JOURNEY_STAGES, JOURNEY_STAGE_LABELS_DE, PAIN_CATEGORY_LABELS_DE,
  COPING_STRATEGY_LABELS_DE, FRUSTRATION_LABELS_DE, LIFE_SITUATION_LABELS_DE,
  BRIDGE_MOMENT_TYPES,
} from "../../constants";

export function buildJourneySpine(items: SocialItem[]) {
  const journeyItems = items.filter(i => i.journey_stage);
  if (journeyItems.length === 0) return { stages: [], total: 0 };
  const total = journeyItems.length;
  const stagesData: any[] = [];

  for (const stage of JOURNEY_STAGES) {
    const stageItems = journeyItems.filter(i => i.journey_stage === stage);
    const count = stageItems.length;
    if (count === 0) {
      stagesData.push({
        stage, label_de: JOURNEY_STAGE_LABELS_DE[stage] || stage,
        count: 0, percentage: 0, pain_breakdown: [], coping_strategies: [],
        life_situations: [], frustrations: [], bridge_to_next: [],
        representative_quotes: [], emotion_distribution: {}, intent_distribution: {},
      });
      continue;
    }

    // Pain breakdown
    const painCounts = new Counter<string>();
    for (const i of stageItems) if (i.pain_category) painCounts.increment(i.pain_category);
    const painBreakdown = painCounts.mostCommon(5).map(([pk, pc]) => {
      const painItems = stageItems.filter(i => i.pain_category === pk);
      const quoteItem = painItems.find(i => (i.title || "").includes("?"));
      let quote = "";
      if (quoteItem) quote = extractRepresentativeQuote(quoteItem.title || "");
      else if (painItems.length > 0) quote = extractRepresentativeQuote(painItems[0].question_content || painItems[0].content || "");
      return { pain_category: pk, label_de: PAIN_CATEGORY_LABELS_DE[pk] || pk, count: pc, quote };
    });

    // Coping strategies
    const copingCounter = new Counter<string>();
    const copingSentiment: Record<string, Counter<string>> = {};
    for (const item of stageItems) {
      for (const s of item.coping_strategies || []) {
        copingCounter.increment(s);
        if (!copingSentiment[s]) copingSentiment[s] = new Counter();
        copingSentiment[s].increment(item.sentiment || "neutral");
      }
    }
    const copingStrategies = copingCounter.mostCommon(5).map(([strat, stratCount]) => {
      const sents = copingSentiment[strat] || new Counter();
      const totalS = sents.total() || 1;
      const stratItems = stageItems.filter(i => (i.coping_strategies || []).includes(strat));
      const frustCounter = new Counter<string>();
      for (const si of stratItems) for (const f of si.solution_frustrations || []) frustCounter.increment(f);
      const topFrust = frustCounter.mostCommon(1);
      return {
        strategy: strat, label_de: COPING_STRATEGY_LABELS_DE[strat] || strat,
        count: stratCount,
        positive_pct: Math.round((sents.get("positive") / totalS) * 100),
        top_frustration: topFrust.length > 0 ? (FRUSTRATION_LABELS_DE[topFrust[0][0]] || topFrust[0][0]) : null,
        frustration_count: topFrust.length > 0 ? topFrust[0][1] : 0,
      };
    });

    // Life situations
    const lsCounts = new Counter<string>();
    for (const i of stageItems) if (i.life_situation) lsCounts.increment(i.life_situation);
    const lifeSituations = lsCounts.mostCommon(5).map(([lsKey, lsCount]) => {
      const lsItems = stageItems.filter(i => i.life_situation === lsKey);
      const topPainC = new Counter<string>();
      for (const i of lsItems) if (i.pain_category) topPainC.increment(i.pain_category);
      const topPain = topPainC.mostCommon(1);
      const quoteItem = lsItems.find(i => i.question_content || i.content);
      const quote = quoteItem ? extractRepresentativeQuote(quoteItem.question_content || quoteItem.content || "") : "";
      return {
        life_situation: lsKey, label_de: LIFE_SITUATION_LABELS_DE[lsKey] || lsKey,
        count: lsCount,
        top_pain: topPain.length > 0 ? (PAIN_CATEGORY_LABELS_DE[topPain[0][0]] || topPain[0][0]) : null,
        quote,
      };
    });

    // Frustrations
    const frustCounts = new Counter<string>();
    for (const item of stageItems) for (const f of item.solution_frustrations || []) frustCounts.increment(f);
    const frustrations = frustCounts.mostCommon(5).map(([fk, fc]) => {
      const fItems = stageItems.filter(i => (i.solution_frustrations || []).includes(fk));
      const qi = fItems.find(i => i.question_content || i.content);
      const quote = qi ? extractRepresentativeQuote(qi.question_content || qi.content || "") : "";
      return { frustration: fk, label_de: FRUSTRATION_LABELS_DE[fk] || fk, count: fc, quote };
    });

    // Bridge moments
    const bridgeCounts = new Counter<string>();
    for (const i of stageItems) {
      if (i.bridge_moment && i.bridge_moment !== "none_identified") bridgeCounts.increment(i.bridge_moment);
    }
    const bridgeToNext = bridgeCounts.mostCommon(3).map(([k, c]) => ({
      bridge_type: k, label_de: BRIDGE_MOMENT_TYPES[k] || k, count: c,
    }));

    // Representative quotes
    const sortedItems = [...stageItems].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
    const representativeQuotes: any[] = [];
    for (const item of sortedItems.slice(0, 3)) {
      const text = item.question_content || item.content || "";
      const quote = extractRepresentativeQuote(text);
      if (quote) representativeQuotes.push({
        text: quote, source: item._display_source || item.source || "unknown", url: item.source_url || "",
      });
    }

    // Emotion/intent distribution
    const emotionCounts = new Counter<string>();
    for (const i of stageItems) if (i.emotion) emotionCounts.increment(i.emotion);
    const emotionTotal = emotionCounts.total() || 1;
    const emotionDist: Record<string, number> = {};
    for (const [k, c] of emotionCounts.mostCommon(4)) emotionDist[k] = Math.round((c / emotionTotal) * 100);

    const intentCounts = new Counter<string>();
    for (const i of stageItems) if (i.intent) intentCounts.increment(i.intent);
    const intentTotal = intentCounts.total() || 1;
    const intentDist: Record<string, number> = {};
    for (const [k, c] of intentCounts.mostCommon(4)) intentDist[k] = Math.round((c / intentTotal) * 100);

    stagesData.push({
      stage, label_de: JOURNEY_STAGE_LABELS_DE[stage] || stage,
      count, percentage: total > 0 ? Math.round((count / total) * 100) : 0,
      pain_breakdown: painBreakdown, coping_strategies: copingStrategies,
      life_situations: lifeSituations, frustrations,
      bridge_to_next: bridgeToNext, representative_quotes: representativeQuotes,
      emotion_distribution: emotionDist, intent_distribution: intentDist,
    });
  }

  return { stages: stagesData, total };
}

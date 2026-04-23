import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { BRIDGE_MOMENT_TYPES } from "../../constants";
import { buildJourneyFunnel } from "./funnel";
import { buildPainLandscape } from "./pain-landscape";
import { buildSolutionDistribution } from "./solution-distribution";
import { buildBridgeMoments } from "./bridge-moments";
import { buildOpportunityMap } from "./opportunity-map";
import { buildJourneySpine } from "./spine";
import { buildPainBreakdown } from "./pain-breakdown";
import { buildQaThreads, tagQaThreadsWithBridges, buildBridgeSummaryFromQa } from "./qa-threads";

export function aggregateJourneyData(items: SocialItem[]) {
  const journeyItems = items.filter(i => i.journey_stage);
  if (journeyItems.length === 0) {
    return {
      journey_funnel: { stages: [], total: 0 },
      pain_landscape: [], solution_distribution: [],
      bridge_moments: { total_detected: 0, patterns: [] },
      bridge_taxonomy: [],
      bridge_summary: { total_detected: 0, patterns: [] },
      opportunity_map: [],
      journey_spine: { stages: [], total: 0 },
      pain_breakdown: { categories: [], resolved_sonstige: [], total: 0 },
      qa_threads: [],
      kpis: { total_journey_mentions: 0, top_pain_category: null, top_solution: null, bridge_rate: 0 },
    };
  }
  const prePurchase = journeyItems.filter(i => ["awareness", "consideration", "comparison"].includes(i.journey_stage!));
  const funnel = buildJourneyFunnel(journeyItems);
  const painLandscape = buildPainLandscape(journeyItems);
  const solutionDist = buildSolutionDistribution(journeyItems);
  const bridgeMoments = buildBridgeMoments(journeyItems);
  const opportunityMap = buildOpportunityMap(painLandscape, solutionDist, bridgeMoments);
  const journeySpine = buildJourneySpine(items);
  const painBreakdown = buildPainBreakdown(items);
  const topPain = painLandscape.length > 0 ? painLandscape[0].label_de : null;
  const topSol = solutionDist.length > 0 ? solutionDist[0].label_de : null;
  const bridgeRate = prePurchase.length > 0 ? Math.round((bridgeMoments.total_detected / prePurchase.length) * 100) : 0;
  // Bridge taxonomy
  const bmCounts = new Counter<string>();
  for (const i of journeyItems) {
    if (i.bridge_moment && i.bridge_moment !== "none_identified") bmCounts.increment(i.bridge_moment);
  }
  const bridgeTaxonomy = bmCounts.mostCommon().map(([k, c]) => ({
    key: k, label_de: BRIDGE_MOMENT_TYPES[k] || k, count: c,
  }));
  const qaThreads = buildQaThreads(items);
  tagQaThreadsWithBridges(qaThreads, items);
  const bridgeSummary = buildBridgeSummaryFromQa(qaThreads);
  return {
    journey_funnel: funnel, pain_landscape: painLandscape,
    solution_distribution: solutionDist, bridge_moments: bridgeMoments,
    bridge_taxonomy: bridgeTaxonomy, bridge_summary: bridgeSummary,
    opportunity_map: opportunityMap, journey_spine: journeySpine,
    pain_breakdown: painBreakdown, qa_threads: qaThreads,
    kpis: { total_journey_mentions: funnel.total, top_pain_category: topPain, top_solution: topSol, bridge_rate: bridgeRate },
  };
}

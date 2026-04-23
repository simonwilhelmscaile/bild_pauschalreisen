import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { SOLUTION_LABELS_DE, HIGH_BEURER_RELEVANCE_SOLUTIONS } from "../../constants";

export function buildSolutionDistribution(items: SocialItem[]) {
  const solutionData: Record<string, { count: number; sentiments: Counter<string> }> = {};
  for (const item of items) {
    for (const sol of item.solutions_mentioned || []) {
      if (!solutionData[sol]) solutionData[sol] = { count: 0, sentiments: new Counter() };
      solutionData[sol].count++;
      solutionData[sol].sentiments.increment(item.sentiment || "neutral");
    }
  }
  const totalItems = items.length || 1;
  const distribution: any[] = [];
  for (const [sol, data] of Object.entries(solutionData)) {
    const totalSents = data.sentiments.total() || 1;
    distribution.push({
      solution: sol, label_de: SOLUTION_LABELS_DE[sol] || sol,
      count: data.count,
      percentage: Math.round((data.count / totalItems) * 1000) / 10,
      sentiment: {
        positive_pct: Math.round((data.sentiments.get("positive") / totalSents) * 100),
        neutral_pct: Math.round((data.sentiments.get("neutral") / totalSents) * 100),
        negative_pct: Math.round((data.sentiments.get("negative") / totalSents) * 100),
      },
      beurer_relevant: HIGH_BEURER_RELEVANCE_SOLUTIONS.includes(sol),
    });
  }
  distribution.sort((a, b) => b.count - a.count);
  return distribution;
}

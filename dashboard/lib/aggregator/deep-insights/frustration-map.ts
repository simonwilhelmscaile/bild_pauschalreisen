import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { FRUSTRATION_LABELS_DE, JOURNEY_STAGE_LABELS_DE } from "../../constants";

export function buildFrustrationMap(items: SocialItem[]) {
  const frustData: Record<string, { count: number; stages: Counter<string>; contentOpps: Counter<string> }> = {};
  for (const item of items) {
    for (const f of item.solution_frustrations || []) {
      if (!frustData[f]) frustData[f] = { count: 0, stages: new Counter(), contentOpps: new Counter() };
      frustData[f].count++;
      frustData[f].stages.increment(item.journey_stage || "unknown");
      if (item.content_opportunity) frustData[f].contentOpps.increment(item.content_opportunity);
    }
  }
  const result: any[] = [];
  for (const [f, data] of Object.entries(frustData)) {
    const topStage = data.stages.mostCommon(1);
    const stageKey = topStage.length > 0 ? topStage[0][0] : "unknown";
    const topContent = data.contentOpps.mostCommon(1);
    result.push({
      frustration: f, label_de: FRUSTRATION_LABELS_DE[f] || f,
      count: data.count,
      top_journey_stage: JOURNEY_STAGE_LABELS_DE[stageKey] || stageKey,
      content_solution: topContent.length > 0 ? topContent[0][0] : null,
    });
  }
  result.sort((a, b) => b.count - a.count);
  const itemsWithFrust = items.filter(i => (i.solution_frustrations || []).length > 0).length;
  return {
    frustrations: result,
    total: result.reduce((s, d) => s + d.count, 0),
    items_with_data: itemsWithFrust,
    total_items: items.length,
    coverage_pct: items.length > 0 ? Math.round((itemsWithFrust / items.length) * 100) : 0,
  };
}

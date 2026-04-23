import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { JOURNEY_STAGES, JOURNEY_STAGE_LABELS_DE } from "../../constants";

export function buildJourneyFunnel(items: SocialItem[]) {
  const stageCounts = new Counter<string>();
  for (const item of items) {
    if (item.journey_stage) stageCounts.increment(item.journey_stage);
  }
  const total = stageCounts.total();
  const stages = JOURNEY_STAGES.map(stage => ({
    stage,
    label_de: JOURNEY_STAGE_LABELS_DE[stage] || stage,
    count: stageCounts.get(stage),
    percentage: total > 0 ? Math.round((stageCounts.get(stage) / total) * 100) : 0,
  }));
  return { stages, total };
}

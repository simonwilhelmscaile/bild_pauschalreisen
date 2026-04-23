import type { SocialItem } from "../types";
import { buildCopingStrategyAnalysis } from "./coping";
import { buildLifeSituationPersonas, buildUserSegmentAnalysis, buildProblemCategoryAnalysis, buildSegmentProblemCrosstab } from "./life-situations";
import { buildFrustrationMap } from "./frustration-map";
import { buildPainSubClassification, buildBpSubClassification } from "./pain-sub";
import { buildMedicationBreakdown } from "./medication";
import { buildAspectAnalysis } from "./aspect-analysis";

export function aggregateDeepInsights(items: SocialItem[]): Record<string, any> {
  const deepItems = items.filter(i => i.key_insight);
  if (deepItems.length === 0) {
    return {
      coping_analysis: { strategies: [], total: 0, top_strategy: null },
      life_situations: { personas: [], total: 0 },
      user_segments: { segments: [], total: 0 },
      problem_categories: { categories: [], total: 0 },
      segment_problem_crosstab: { pairs: [] },
      frustration_map: { frustrations: [], total: 0 },
      pain_sub: { by_location: [], by_severity: [], by_duration: [] },
      bp_sub: { by_concern: [], by_severity: [] },
      total_items: 0, kpis: {},
    };
  }
  const coping = buildCopingStrategyAnalysis(deepItems);
  const lifeSit = buildLifeSituationPersonas(deepItems);
  const userSegments = buildUserSegmentAnalysis(deepItems);
  const problemCategories = buildProblemCategoryAnalysis(deepItems);
  const segmentProblemCrosstab = buildSegmentProblemCrosstab(deepItems);
  const frustrations = buildFrustrationMap(deepItems);
  const painSub = buildPainSubClassification(deepItems);
  const bpSub = buildBpSubClassification(deepItems);
  const medicationBreakdown = buildMedicationBreakdown(deepItems);
  const aspectAnalysis = buildAspectAnalysis(deepItems);
  return {
    coping_analysis: coping, life_situations: lifeSit,
    user_segments: userSegments, problem_categories: problemCategories,
    segment_problem_crosstab: segmentProblemCrosstab,
    frustration_map: frustrations, pain_sub: painSub, bp_sub: bpSub,
    medication_breakdown: medicationBreakdown, aspect_analysis: aspectAnalysis,
    total_items: deepItems.length,
    kpis: {
      total_deep_items: deepItems.length,
      top_coping: coping.top_strategy,
      top_persona: lifeSit.personas.length > 0 ? lifeSit.personas[0].label_de : null,
      top_frustration: frustrations.frustrations.length > 0 ? frustrations.frustrations[0].label_de : null,
      top_pain_location: painSub.by_location.length > 0 ? painSub.by_location[0].label_de : null,
      top_bp_concern: bpSub.by_concern.length > 0 ? bpSub.by_concern[0].label_de : null,
    },
  };
}

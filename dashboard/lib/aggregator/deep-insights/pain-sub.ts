import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { PAIN_LOCATION_LABELS_DE, PAIN_SEVERITY_LABELS_DE, PAIN_DURATION_LABELS_DE, BP_CONCERN_LABELS_DE, BP_SEVERITY_LABELS_DE } from "../../constants";

function countField(items: SocialItem[], field: keyof SocialItem, labels: Record<string, string>) {
  const counts = new Counter<string>();
  for (const i of items) { const v = i[field]; if (v && typeof v === "string") counts.increment(v); }
  return counts.mostCommon().map(([k, c]) => ({ key: k, label_de: labels[k] || k, count: c }));
}

export function buildPainSubClassification(items: SocialItem[]) {
  const painItems = items.filter(i => i.category === "pain_tens" || i.category === "menstrual");
  const totalPain = painItems.length;
  const itemsWithData = painItems.filter(i => i.pain_location || i.pain_severity).length;
  return {
    by_location: countField(painItems, "pain_location", PAIN_LOCATION_LABELS_DE),
    by_severity: countField(painItems, "pain_severity", PAIN_SEVERITY_LABELS_DE),
    by_duration: countField(painItems, "pain_duration", PAIN_DURATION_LABELS_DE),
    total_items: totalPain, items_with_data: itemsWithData,
    coverage_pct: totalPain > 0 ? Math.round((itemsWithData / totalPain) * 100) : 0,
  };
}

export function buildBpSubClassification(items: SocialItem[]) {
  const bpItems = items.filter(i => i.category === "blood_pressure");
  const totalBp = bpItems.length;
  const itemsWithData = bpItems.filter(i => i.bp_concern_type || i.bp_severity).length;
  return {
    by_concern: countField(bpItems, "bp_concern_type", BP_CONCERN_LABELS_DE),
    by_severity: countField(bpItems, "bp_severity", BP_SEVERITY_LABELS_DE),
    total_items: totalBp, items_with_data: itemsWithData,
    coverage_pct: totalBp > 0 ? Math.round((itemsWithData / totalBp) * 100) : 0,
  };
}

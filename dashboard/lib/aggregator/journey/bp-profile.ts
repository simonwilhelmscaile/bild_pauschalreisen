import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { BP_CONCERN_LABELS_DE, BP_SEVERITY_LABELS_DE } from "../../constants";

export function buildBpProfile(items: SocialItem[]) {
  const withConcern = items.filter(i => i.bp_concern_type);
  const withSeverity = items.filter(i => i.bp_severity);
  const itemsWithData = items.filter(i => i.bp_concern_type || i.bp_severity).length;

  const concernCounts = new Counter<string>();
  for (const i of withConcern) concernCounts.increment(i.bp_concern_type!);
  const concernTotal = concernCounts.total() || 1;
  const concerns = concernCounts.mostCommon().map(([k, c]) => ({
    key: k, label_de: BP_CONCERN_LABELS_DE[k] || k,
    count: c, percentage: Math.round((c / concernTotal) * 100),
  }));

  const sevCounts = new Counter<string>();
  for (const i of withSeverity) sevCounts.increment(i.bp_severity!);
  const sevTotal = sevCounts.total() || 1;
  const severities = sevCounts.mostCommon().map(([k, c]) => ({
    key: k, label_de: BP_SEVERITY_LABELS_DE[k] || k,
    count: c, percentage: Math.round((c / sevTotal) * 100),
  }));

  return {
    concerns, severities, total: items.length,
    items_with_data: itemsWithData,
    coverage_pct: items.length > 0 ? Math.round((itemsWithData / items.length) * 100) : 0,
  };
}

import { ServiceCase, ServiceCaseAlert } from "./types";
import { getISOWeek } from "./utils";

/**
 * Detect anomalies: compare most recent week's per-product reason counts
 * against the previous 4-week average.
 *
 * Thresholds: >30% deviation AND >=5 cases in current week.
 * Severity: warning (30-60%), critical (>60%).
 */
export function buildAlerts(cases: ServiceCase[]): ServiceCaseAlert[] {
  if (cases.length === 0) return [];

  // Group by week → product → reason → count
  const weekProductReason = new Map<string, Map<string, Map<string, number>>>();
  for (const c of cases) {
    if (!c.product_model) continue;
    const week = getISOWeek(c.case_date);
    if (!weekProductReason.has(week)) weekProductReason.set(week, new Map());
    const products = weekProductReason.get(week)!;
    if (!products.has(c.product_model)) products.set(c.product_model, new Map());
    const reasons = products.get(c.product_model)!;
    reasons.set(c.reason, (reasons.get(c.reason) || 0) + 1);
  }

  const sortedWeeks = [...weekProductReason.keys()].sort();
  if (sortedWeeks.length < 2) return []; // Need at least 2 weeks for comparison

  const currentWeek = sortedWeeks[sortedWeeks.length - 1];
  // Previous 4 weeks (or however many are available, excluding current)
  const prevWeeks = sortedWeeks.slice(Math.max(0, sortedWeeks.length - 5), sortedWeeks.length - 1);
  if (prevWeeks.length === 0) return [];

  const currentData = weekProductReason.get(currentWeek)!;
  const alerts: ServiceCaseAlert[] = [];

  for (const [product, reasons] of currentData) {
    for (const [reason, currentCount] of reasons) {
      if (currentCount < 5) continue; // Noise filter

      // Compute average from previous weeks
      let total = 0;
      for (const pw of prevWeeks) {
        const pwData = weekProductReason.get(pw);
        total += pwData?.get(product)?.get(reason) || 0;
      }
      const avgCount = total / prevWeeks.length;

      if (avgCount === 0) continue; // No baseline to compare

      const changePercent = Math.round(((currentCount - avgCount) / avgCount) * 100);
      if (changePercent < 30) continue; // Below threshold

      alerts.push({
        product,
        reason,
        currentCount,
        avgCount: Math.round(avgCount * 10) / 10,
        changePercent,
        severity: changePercent > 60 ? "critical" : "warning",
      });
    }
  }

  // Sort: critical first, then by changePercent descending
  alerts.sort((a, b) => {
    if (a.severity !== b.severity) return a.severity === "critical" ? -1 : 1;
    return b.changePercent - a.changePercent;
  });

  return alerts;
}

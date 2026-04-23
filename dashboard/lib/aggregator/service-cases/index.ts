import { ServiceCase, KundendienstInsights } from "./types";
import { buildHeatmap } from "./heatmap";
import { buildTrends } from "./trends";
import { buildAlerts } from "./alerts";

/**
 * Aggregate all service case data for the Kundendienst-Insights dashboard tab.
 * Returns null if no cases are available (tab can hide gracefully).
 */
export function aggregateServiceCaseData(cases: ServiceCase[]): KundendienstInsights | null {
  if (cases.length === 0) return null;

  const heatmap = buildHeatmap(cases);
  const trends = buildTrends(cases);
  const alerts = buildAlerts(cases);

  // Summary stats
  const productCounts = new Map<string, number>();
  const reasonCounts = new Map<string, number>();
  for (const c of cases) {
    if (c.product_model) {
      productCounts.set(c.product_model, (productCounts.get(c.product_model) || 0) + 1);
    }
    reasonCounts.set(c.reason, (reasonCounts.get(c.reason) || 0) + 1);
  }

  let topProduct: { model: string; count: number } | null = null;
  let topReason: { reason: string; count: number } | null = null;
  for (const [model, count] of productCounts) {
    if (!topProduct || count > topProduct.count) topProduct = { model, count };
  }
  for (const [reason, count] of reasonCounts) {
    if (!topReason || count > topReason.count) topReason = { reason, count };
  }

  return {
    heatmap,
    trends,
    alerts,
    summary: {
      totalCases: cases.length,
      topProduct,
      topReason,
      alertCount: alerts.length,
    },
  };
}

export { fetchServiceCases } from "./fetch";
export type { KundendienstInsights, ServiceCase, ServiceCaseAlert } from "./types";

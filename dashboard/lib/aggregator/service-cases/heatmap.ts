import { ServiceCase, HeatmapData, HeatmapProduct } from "./types";

/**
 * Build product x reason heatmap matrix.
 * Default: only products with a known category (health devices).
 */
export function buildHeatmap(cases: ServiceCase[], includeUncategorized = false): HeatmapData {
  const filtered = includeUncategorized
    ? cases.filter((c) => c.product_model)
    : cases.filter((c) => c.product_model && c.product_category);

  // Collect all reasons
  const reasonSet = new Set<string>();

  // Group by product
  const productMap = new Map<string, { category: string | null; reasons: Map<string, number> }>();
  for (const c of filtered) {
    const model = c.product_model!;
    reasonSet.add(c.reason);
    if (!productMap.has(model)) {
      productMap.set(model, { category: c.product_category, reasons: new Map() });
    }
    const entry = productMap.get(model)!;
    entry.reasons.set(c.reason, (entry.reasons.get(c.reason) || 0) + 1);
  }

  // Build sorted product list
  const products: HeatmapProduct[] = [];
  for (const [model, data] of productMap) {
    const reasons: Record<string, number> = {};
    let total = 0;
    for (const [reason, count] of data.reasons) {
      reasons[reason] = count;
      total += count;
    }
    products.push({ model, category: data.category, reasons, total });
  }
  products.sort((a, b) => b.total - a.total);

  const allReasons = [...reasonSet].sort();

  return {
    products,
    allReasons,
    totalCases: filtered.length,
  };
}

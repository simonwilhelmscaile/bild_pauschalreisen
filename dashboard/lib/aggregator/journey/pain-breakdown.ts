import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { PAIN_CATEGORY_LABELS_DE, PAIN_LOCATION_LABELS_DE } from "../../constants";

export function buildPainBreakdown(items: SocialItem[]) {
  const journeyItems = items.filter(i => i.pain_category);
  if (journeyItems.length === 0) return { categories: [], resolved_sonstige: [], total: 0 };
  const catCounts = new Counter<string>();
  for (const i of journeyItems) catCounts.increment(i.pain_category!);

  const sonstigeItems = journeyItems.filter(i => i.pain_category === "sonstige_schmerzen");
  const resolvedLocations = new Counter<string>();
  let unresolvable = 0;
  for (const item of sonstigeItems) {
    if (item.pain_location) resolvedLocations.increment(item.pain_location);
    else unresolvable++;
  }
  const resolvedSonstige: any[] = resolvedLocations.mostCommon().map(([loc, c]) => ({
    pain_location: loc, label_de: PAIN_LOCATION_LABELS_DE[loc] || loc, count: c,
  }));
  if (unresolvable > 0) resolvedSonstige.push({ pain_location: "unresolved", label_de: "Nicht zugeordnet", count: unresolvable });

  const categories = catCounts.mostCommon().map(([cat, c]) => ({
    pain_category: cat, label_de: PAIN_CATEGORY_LABELS_DE[cat] || cat,
    count: c, percentage: journeyItems.length > 0 ? Math.round((c / journeyItems.length) * 100) : 0,
  }));

  return {
    categories, resolved_sonstige: resolvedSonstige, total: journeyItems.length,
    sonstige_count: sonstigeItems.length,
    sonstige_resolved_pct: sonstigeItems.length > 0 ? Math.round(((sonstigeItems.length - unresolvable) / sonstigeItems.length) * 100) : 0,
  };
}

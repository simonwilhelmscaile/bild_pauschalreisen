import type { SocialItem } from "../types";
import { Counter } from "../utils";
import { CATEGORY_LABELS_DE, PAIN_CATEGORY_LABELS_DE, GENERIC_MEDICATION_TERMS, MEDICATION_CLASSES } from "../../constants";

export function buildMedicationBreakdown(items: SocialItem[]) {
  const categoryMeds: Record<string, Counter<string>> = {};
  const medPainCross: Record<string, Counter<string>> = {};

  for (const item of items) {
    const meds = item.medications_mentioned || [];
    if (meds.length === 0) continue;
    const cat = item.category || "other";
    const painCat = item.pain_category;
    if (!categoryMeds[cat]) categoryMeds[cat] = new Counter();
    for (const med of meds) {
      const medStr = String(med).trim();
      if (medStr && !GENERIC_MEDICATION_TERMS.has(medStr)) {
        categoryMeds[cat].increment(medStr);
        if (painCat) {
          if (!medPainCross[medStr]) medPainCross[medStr] = new Counter();
          medPainCross[medStr].increment(painCat);
        }
      }
    }
  }

  const byCategory: Record<string, any[]> = {};
  for (const [cat, counter] of Object.entries(categoryMeds)) {
    const catLabel = CATEGORY_LABELS_DE[cat] || cat;
    byCategory[cat] = counter.mostCommon(15).map(([med, count]) => {
      const topPainEntries = (medPainCross[med] || new Counter()).mostCommon(1);
      return {
        medication: med, count, context_label: catLabel,
        top_pain: topPainEntries.length > 0 ? (PAIN_CATEGORY_LABELS_DE[topPainEntries[0][0]] || "") : null,
      };
    });
  }

  // By class
  const allMeds = new Counter<string>();
  for (const counter of Object.values(categoryMeds)) allMeds.update(counter);
  const byClass: Record<string, any> = {};
  const classifiedMeds = new Set<string>();
  for (const [medClass, classKeywords] of Object.entries(MEDICATION_CLASSES)) {
    const classMeds: any[] = [];
    for (const [med, count] of allMeds.mostCommon()) {
      if (classKeywords.some(kw => med.toLowerCase().includes(kw))) {
        classMeds.push({ medication: med, count });
        classifiedMeds.add(med);
      }
    }
    if (classMeds.length > 0) {
      byClass[medClass] = { medications: classMeds, total: classMeds.reduce((s, m) => s + m.count, 0) };
    }
  }
  const unclassified = allMeds.mostCommon().filter(([med]) => !classifiedMeds.has(med)).map(([med, count]) => ({ medication: med, count }));
  if (unclassified.length > 0) {
    byClass["Sonstige"] = { medications: unclassified.slice(0, 10), total: unclassified.reduce((s, m) => s + m.count, 0) };
  }
  return { by_category: byCategory, by_class: byClass };
}

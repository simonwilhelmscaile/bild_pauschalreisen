import type { SocialItem } from "../types";
import { aggregateDeepInsights } from "./index";
import { CATEGORY_PAIN_CATEGORIES, CATEGORY_EXCLUDED_MED_CLASSES } from "../../constants";

export function aggregateDeepInsightsByCategory(items: SocialItem[]) {
  const TARGET: Record<string, string> = { blood_pressure: "Blutdruck", pain_tens: "Schmerz/TENS", menstrual: "Menstruation" };
  const result: Record<string, any> = {};
  for (const [catKey, catLabel] of Object.entries(TARGET)) {
    const catItems = items.filter(i => i.category === catKey);
    if (catItems.length === 0) continue;
    const catDi = aggregateDeepInsights(catItems);
    catDi.label_de = catLabel;
    stripCrossCategoryData(catDi, catKey);
    result[catKey] = catDi;
  }
  const allDi = aggregateDeepInsights(items);
  allDi.label_de = "Alle Kategorien";
  result.all = allDi;
  return result;
}

/** Remove data that belongs to a different category to prevent cross-category bleed. */
function stripCrossCategoryData(di: Record<string, any>, category: string) {
  if (category === "blood_pressure") {
    // BP should not show pain sub-classification
    if (di.pain_sub) {
      di.pain_sub = { by_location: [], by_severity: [], by_duration: [], total_items: 0, items_with_data: 0, coverage_pct: 0 };
    }
    // Strip pain_profile from each coping strategy
    if (di.coping_analysis?.strategies) {
      for (const s of di.coping_analysis.strategies) {
        s.pain_profile = [];
      }
    }
  } else if (category === "pain_tens" || category === "menstrual") {
    // Pain/menstrual should not show BP sub-classification
    if (di.bp_sub) {
      di.bp_sub = { by_concern: [], by_severity: [], total_items: 0, items_with_data: 0, coverage_pct: 0 };
    }
    // Filter out "bluthochdruck" entries from coping strategy pain_profile
    if (di.coping_analysis?.strategies) {
      for (const s of di.coping_analysis.strategies) {
        if (s.pain_profile) {
          s.pain_profile = s.pain_profile.filter((p: any) => p.pain_category !== "bluthochdruck");
        }
      }
    }
  }

  // Strip medication classes that don't belong to this category
  const excludedMedClasses = CATEGORY_EXCLUDED_MED_CLASSES[category];
  if (excludedMedClasses && di.medication_breakdown?.by_class) {
    for (const cls of excludedMedClasses) {
      delete di.medication_breakdown.by_class[cls];
    }
  }

  // Filter problem_categories to remove cross-category entries
  if (di.problem_categories?.categories) {
    const crossCatProblems = getCrossCategoryProblems(category);
    if (crossCatProblems.length > 0) {
      di.problem_categories.categories = di.problem_categories.categories.filter(
        (pc: any) => !crossCatProblems.includes(pc.category)
      );
      di.problem_categories.total = di.problem_categories.categories.reduce(
        (s: number, c: any) => s + c.count, 0
      );
    }
  }
}

/** Return problem_category values that are semantically irrelevant to the given item category. */
function getCrossCategoryProblems(category: string): string[] {
  if (category === "blood_pressure") {
    return ["fibromyalgie_patient", "migraene_patient", "endometriose"];
  }
  // No BP-specific problem categories exist in the current enum
  return [];
}

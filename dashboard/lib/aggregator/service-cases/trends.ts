import { ServiceCase, TrendData, TrendWeek } from "./types";
import { getISOWeek } from "./utils";

/**
 * Bucket service cases by ISO week, broken down by reason.
 */
export function buildTrends(cases: ServiceCase[]): TrendData {
  const reasonSet = new Set<string>();
  const weekMap = new Map<string, Map<string, number>>();

  for (const c of cases) {
    const week = getISOWeek(c.case_date);
    reasonSet.add(c.reason);
    if (!weekMap.has(week)) {
      weekMap.set(week, new Map());
    }
    const wk = weekMap.get(week)!;
    wk.set(c.reason, (wk.get(c.reason) || 0) + 1);
  }

  // Sort weeks chronologically
  const sortedWeeks = [...weekMap.keys()].sort();
  const weeks: TrendWeek[] = sortedWeeks.map((week) => {
    const byReason: Record<string, number> = {};
    let total = 0;
    for (const [reason, count] of weekMap.get(week)!) {
      byReason[reason] = count;
      total += count;
    }
    return { week, total, byReason };
  });

  return { weeks, allReasons: [...reasonSet].sort() };
}

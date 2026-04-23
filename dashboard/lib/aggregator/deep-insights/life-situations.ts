import type { SocialItem } from "../types";
import { Counter, buildContentPreview } from "../utils";
import {
  LIFE_SITUATION_LABELS_DE, COPING_STRATEGY_LABELS_DE, FRUSTRATION_LABELS_DE,
  BRIDGE_MOMENT_TYPES, USER_SEGMENT_LABELS_DE, PROBLEM_CATEGORY_LABELS_DE,
} from "../../constants";

export function buildLifeSituationPersonas(items: SocialItem[]) {
  const personaData: Record<string, {
    count: number; coping: Counter<string>; frustrations: Counter<string>;
    bridgeMoments: Counter<string>; contentOpps: Counter<string>; items: SocialItem[];
  }> = {};

  for (const item of items) {
    const ls = item.life_situation;
    if (!ls) continue;
    if (!personaData[ls]) {
      personaData[ls] = { count: 0, coping: new Counter(), frustrations: new Counter(), bridgeMoments: new Counter(), contentOpps: new Counter(), items: [] };
    }
    personaData[ls].count++;
    personaData[ls].items.push(item);
    for (const c of item.coping_strategies || []) personaData[ls].coping.increment(c);
    for (const f of item.solution_frustrations || []) personaData[ls].frustrations.increment(f);
    if (item.bridge_moment && item.bridge_moment !== "none_identified") personaData[ls].bridgeMoments.increment(item.bridge_moment);
    if (item.content_opportunity) personaData[ls].contentOpps.increment(item.content_opportunity);
  }

  const result: any[] = [];
  for (const [ls, data] of Object.entries(personaData)) {
    const topCoping = data.coping.mostCommon(1);
    const topFrust = data.frustrations.mostCommon(1);
    const topBridge = data.bridgeMoments.mostCommon(1);
    const topContent = data.contentOpps.mostCommon(1);
    const sortedItems = [...data.items].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
    const allPosts = sortedItems.filter(qi => qi.title).map(qi => ({
      title: (qi.title || "").slice(0, 150), url: qi.source_url || "",
      source: qi._display_source || qi.source || "", sentiment: qi.sentiment || "",
      content_preview: buildContentPreview(qi),
      device_relevance_score: qi.device_relevance_score || 0,
      posted_at: qi.posted_at || "",
    }));
    result.push({
      life_situation: ls, label_de: LIFE_SITUATION_LABELS_DE[ls] || ls,
      count: data.count,
      top_coping: topCoping.length > 0 ? (COPING_STRATEGY_LABELS_DE[topCoping[0][0]] || topCoping[0][0]) : null,
      top_frustration: topFrust.length > 0 ? (FRUSTRATION_LABELS_DE[topFrust[0][0]] || topFrust[0][0]) : null,
      top_bridge_moment: topBridge.length > 0 ? (BRIDGE_MOMENT_TYPES[topBridge[0][0]] || topBridge[0][0]) : null,
      top_content_opportunity: topContent.length > 0 ? topContent[0][0] : null,
      all_posts: allPosts,
    });
  }

  result.sort((a, b) => b.count - a.count);
  const totalWithLs = result.reduce((s, d) => s + d.count, 0);
  return {
    personas: result, total: totalWithLs,
    total_items: items.length,
    coverage_pct: items.length > 0 ? Math.round((totalWithLs / items.length) * 100) : 0,
  };
}

export function buildUserSegmentAnalysis(items: SocialItem[]) {
  const groupData: Record<string, {
    count: number; coping: Counter<string>; frustrations: Counter<string>;
    bridgeMoments: Counter<string>; contentOpps: Counter<string>; items: SocialItem[];
  }> = {};

  for (const item of items) {
    const seg = item.user_segment;
    if (!seg) continue;
    if (!groupData[seg]) {
      groupData[seg] = { count: 0, coping: new Counter(), frustrations: new Counter(), bridgeMoments: new Counter(), contentOpps: new Counter(), items: [] };
    }
    groupData[seg].count++;
    groupData[seg].items.push(item);
    for (const c of item.coping_strategies || []) groupData[seg].coping.increment(c);
    for (const f of item.solution_frustrations || []) groupData[seg].frustrations.increment(f);
    if (item.bridge_moment && item.bridge_moment !== "none_identified") groupData[seg].bridgeMoments.increment(item.bridge_moment);
    if (item.content_opportunity) groupData[seg].contentOpps.increment(item.content_opportunity);
  }

  const segments: any[] = [];
  for (const [seg, data] of Object.entries(groupData)) {
    const topCoping = data.coping.mostCommon(1);
    const topFrust = data.frustrations.mostCommon(1);
    const topBridge = data.bridgeMoments.mostCommon(1);
    const topContent = data.contentOpps.mostCommon(1);
    const sortedItems = [...data.items].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
    const allPosts = sortedItems.filter(qi => qi.title).map(qi => ({
      title: (qi.title || "").slice(0, 150), url: qi.source_url || "",
      source: qi._display_source || qi.source || "", sentiment: qi.sentiment || "",
      content_preview: buildContentPreview(qi),
      device_relevance_score: qi.device_relevance_score || 0,
      posted_at: qi.posted_at || "",
    }));
    segments.push({
      segment: seg, label_de: USER_SEGMENT_LABELS_DE[seg] || seg,
      count: data.count,
      top_coping: topCoping.length > 0 ? (COPING_STRATEGY_LABELS_DE[topCoping[0][0]] || topCoping[0][0]) : null,
      top_frustration: topFrust.length > 0 ? (FRUSTRATION_LABELS_DE[topFrust[0][0]] || topFrust[0][0]) : null,
      top_bridge_moment: topBridge.length > 0 ? (BRIDGE_MOMENT_TYPES[topBridge[0][0]] || topBridge[0][0]) : null,
      top_content_opportunity: topContent.length > 0 ? topContent[0][0] : null,
      all_posts: allPosts,
    });
  }
  segments.sort((a, b) => b.count - a.count);
  const total = segments.reduce((s, d) => s + d.count, 0);
  return {
    segments, total, total_items: items.length,
    coverage_pct: items.length > 0 ? Math.round((total / items.length) * 100) : 0,
  };
}

export function buildProblemCategoryAnalysis(items: SocialItem[]) {
  const groupData: Record<string, {
    count: number; coping: Counter<string>; frustrations: Counter<string>;
    bridgeMoments: Counter<string>; contentOpps: Counter<string>; items: SocialItem[];
  }> = {};

  for (const item of items) {
    const pc = item.problem_category;
    if (!pc) continue;
    if (!groupData[pc]) {
      groupData[pc] = { count: 0, coping: new Counter(), frustrations: new Counter(), bridgeMoments: new Counter(), contentOpps: new Counter(), items: [] };
    }
    groupData[pc].count++;
    groupData[pc].items.push(item);
    for (const c of item.coping_strategies || []) groupData[pc].coping.increment(c);
    for (const f of item.solution_frustrations || []) groupData[pc].frustrations.increment(f);
    if (item.bridge_moment && item.bridge_moment !== "none_identified") groupData[pc].bridgeMoments.increment(item.bridge_moment);
    if (item.content_opportunity) groupData[pc].contentOpps.increment(item.content_opportunity);
  }

  const categories: any[] = [];
  for (const [pc, data] of Object.entries(groupData)) {
    const topCoping = data.coping.mostCommon(1);
    const topFrust = data.frustrations.mostCommon(1);
    const topBridge = data.bridgeMoments.mostCommon(1);
    const topContent = data.contentOpps.mostCommon(1);
    const sortedItems = [...data.items].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
    const allPosts = sortedItems.filter(qi => qi.title).map(qi => ({
      title: (qi.title || "").slice(0, 150), url: qi.source_url || "",
      source: qi._display_source || qi.source || "", sentiment: qi.sentiment || "",
      content_preview: buildContentPreview(qi),
      device_relevance_score: qi.device_relevance_score || 0,
      posted_at: qi.posted_at || "",
    }));
    categories.push({
      category: pc, label_de: PROBLEM_CATEGORY_LABELS_DE[pc] || pc,
      count: data.count,
      top_coping: topCoping.length > 0 ? (COPING_STRATEGY_LABELS_DE[topCoping[0][0]] || topCoping[0][0]) : null,
      top_frustration: topFrust.length > 0 ? (FRUSTRATION_LABELS_DE[topFrust[0][0]] || topFrust[0][0]) : null,
      top_bridge_moment: topBridge.length > 0 ? (BRIDGE_MOMENT_TYPES[topBridge[0][0]] || topBridge[0][0]) : null,
      top_content_opportunity: topContent.length > 0 ? topContent[0][0] : null,
      all_posts: allPosts,
    });
  }
  categories.sort((a, b) => b.count - a.count);
  const total = categories.reduce((s, d) => s + d.count, 0);
  return {
    categories, total, total_items: items.length,
    coverage_pct: items.length > 0 ? Math.round((total / items.length) * 100) : 0,
  };
}

export function buildSegmentProblemCrosstab(items: SocialItem[]) {
  const pairs = new Counter<string>();
  for (const item of items) {
    const seg = item.user_segment;
    const pc = item.problem_category;
    if (seg && pc) pairs.increment(`${seg}|||${pc}`);
  }
  const result = pairs.mostCommon().map(([key, count]) => {
    const [seg, pc] = key.split("|||");
    return {
      segment: seg,
      segment_label: USER_SEGMENT_LABELS_DE[seg] || seg,
      problem: pc,
      problem_label: PROBLEM_CATEGORY_LABELS_DE[pc] || pc,
      count,
    };
  });
  return { pairs: result };
}

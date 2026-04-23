import type { SocialItem } from "../types";
import { Counter, extractRepresentativeQuote, buildContentPreview } from "../utils";
import {
  COPING_STRATEGY_LABELS_DE, CATEGORY_LABELS_DE, PAIN_CATEGORY_LABELS_DE,
  FRUSTRATION_LABELS_DE, JOURNEY_STAGE_LABELS_DE,
} from "../../constants";

export function buildCopingStrategyAnalysis(items: SocialItem[]) {
  const strategyData: Record<string, {
    count: number; sentiments: Counter<string>; categories: Counter<string>;
    contentOppsByCat: Record<string, Counter<string>>; painCategories: Counter<string>;
    frustrations: Counter<string>; journeyStages: Counter<string>; items: SocialItem[];
  }> = {};

  for (const item of items) {
    for (const s of item.coping_strategies || []) {
      if (!strategyData[s]) {
        strategyData[s] = {
          count: 0, sentiments: new Counter(), categories: new Counter(),
          contentOppsByCat: {}, painCategories: new Counter(),
          frustrations: new Counter(), journeyStages: new Counter(), items: [],
        };
      }
      const d = strategyData[s];
      d.count++;
      d.sentiments.increment(item.sentiment || "neutral");
      d.categories.increment(item.category || "other");
      if (item.pain_category) d.painCategories.increment(item.pain_category);
      for (const f of item.solution_frustrations || []) d.frustrations.increment(f);
      if (item.journey_stage) d.journeyStages.increment(item.journey_stage);
      d.items.push(item);
      if (item.content_opportunity) {
        const cat = item.category || "other";
        if (!d.contentOppsByCat[cat]) d.contentOppsByCat[cat] = new Counter();
        d.contentOppsByCat[cat].increment(item.content_opportunity);
      }
    }
  }

  const result: any[] = [];
  for (const [strategy, data] of Object.entries(strategyData)) {
    const totalS = data.sentiments.total() || 1;
    const pos = data.sentiments.get("positive");
    const neg = data.sentiments.get("negative");
    const neu = data.sentiments.get("neutral");
    const topCatEntries = data.categories.mostCommon(1);
    const topCat = topCatEntries.length > 0 ? topCatEntries[0][0] : "other";
    let catOpps = data.contentOppsByCat[topCat] || new Counter();
    if (catOpps.total() === 0) {
      catOpps = new Counter();
      for (const c of Object.values(data.contentOppsByCat)) catOpps.update(c);
    }
    const topContent = catOpps.mostCommon(1);
    const catDist = data.categories.mostCommon(5).map(([cat, cnt]) => ({
      category: cat, label_de: CATEGORY_LABELS_DE[cat] || cat, count: cnt,
    }));
    const painDist = data.painCategories.mostCommon(5).map(([pc, cnt]) => ({
      pain_category: pc, label_de: PAIN_CATEGORY_LABELS_DE[pc] || pc, count: cnt,
    }));
    const frustDist = data.frustrations.mostCommon(5).map(([fk, cnt]) => ({
      key: fk, label_de: FRUSTRATION_LABELS_DE[fk] || fk, count: cnt,
    }));
    const stageDist = data.journeyStages.mostCommon().map(([stg, cnt]) => ({
      stage: stg, label_de: JOURNEY_STAGE_LABELS_DE[stg] || stg, count: cnt,
    }));

    const sortedItems = [...data.items].sort((a, b) =>
      ((b.key_insight ? 1 : 0) - (a.key_insight ? 1 : 0)) || ((b.relevance_score || 0) - (a.relevance_score || 0))
    );
    const quotes = sortedItems.slice(0, 3).map(qi => {
      const text = qi.key_insight || (qi.title || "").slice(0, 120);
      return text ? { text, source: qi._display_source || qi.source || "", url: qi.source_url || "", sentiment: qi.sentiment || "", posted_at: qi.posted_at || "" } : null;
    }).filter(Boolean);

    const allPosts = sortedItems.filter(qi => qi.title).map(qi => ({
      title: (qi.title || "").slice(0, 150),
      url: qi.source_url || "",
      source: qi._display_source || qi.source || "",
      sentiment: qi.sentiment || "",
      content_preview: buildContentPreview(qi),
      device_relevance_score: qi.device_relevance_score || 0,
      posted_at: qi.posted_at || "",
    }));

    result.push({
      strategy, label_de: COPING_STRATEGY_LABELS_DE[strategy] || strategy,
      count: data.count,
      effectiveness_pct: Math.round((pos / totalS) * 100),
      sentiment: {
        positive: pos, neutral: neu, negative: neg,
        positive_pct: Math.round((pos / totalS) * 100),
        neutral_pct: Math.round((neu / totalS) * 100),
        negative_pct: Math.round((neg / totalS) * 100),
      },
      top_category: CATEGORY_LABELS_DE[topCat] || topCat,
      category_distribution: catDist,
      pain_profile: painDist,
      frustrations: frustDist,
      journey_stages: stageDist,
      quotes,
      content_angle: topContent.length > 0 ? topContent[0][0] : null,
      all_posts: allPosts,
    });
  }

  result.sort((a, b) => b.count - a.count);
  const itemsWithCoping = items.filter(i => (i.coping_strategies || []).length > 0).length;
  return {
    strategies: result,
    total: result.reduce((s, d) => s + d.count, 0),
    top_strategy: result.length > 0 ? result[0].label_de : null,
    items_with_data: itemsWithCoping,
    total_items: items.length,
    coverage_pct: items.length > 0 ? Math.round((itemsWithCoping / items.length) * 100) : 0,
  };
}

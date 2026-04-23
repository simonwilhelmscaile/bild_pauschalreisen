import type { SocialItem } from "./types";
import { COMPETITOR_BRANDS, BRAND_CATEGORY_MAP, ASPECT_LABELS_DE, KEYWORD_TO_ASPECT, ASPECT_ADVANTAGE_MAP, ASPECT_CATEGORIES } from "../constants";
import { Counter, extractRepresentativeQuote } from "./utils";

const CONTEXT_KEYWORDS: Record<string, string[]> = {
  comparison: ["besser als", "im vergleich", "versus", "vs", "genauer als", "statt", "verglichen mit", "unterschied"],
  recommendation: ["empfehle", "empfehlung", "würde.*kaufen", "tipp", "vorschlag", "raten zu", "empfohlen"],
  complaint: ["problem", "fehler", "defekt", "unzufrieden", "schlecht", "kaputt", "reklamation", "mangelhaft"],
  switch_ctx: ["gewechselt", "umgestiegen", "ersetzt", "stattdessen", "vorher.*jetzt", "umstieg", "wechsel"],
};

function classifyContext(text: string): string {
  const lower = text.toLowerCase();
  for (const [contextType, patterns] of Object.entries(CONTEXT_KEYWORDS)) {
    for (const pattern of patterns) {
      if (pattern.includes(".*")) {
        if (new RegExp(pattern).test(lower)) return contextType === "switch_ctx" ? "switch" : contextType;
      } else {
        if (lower.includes(pattern)) return contextType === "switch_ctx" ? "switch" : contextType;
      }
    }
  }
  return "general";
}

export function buildCompetitiveIntelligence(items: SocialItem[], productIntelligence: Record<string, any>) {
  const hasEntities = items.some(item => (item._entities || []).length > 0);
  const brandData: Record<string, any> = {};
  for (const [, brandName] of Object.entries(COMPETITOR_BRANDS)) {
    if (!brandData[brandName]) {
      brandData[brandName] = {
        brand: brandName, total_mentions: 0,
        context_breakdown: { comparison: 0, recommendation: 0, complaint: 0, switch: 0, general: 0 },
        sample_snippets: [] as string[], items: [] as any[],
        strategic_implication: "", recommended_action: "",
      };
    }
  }

  if (hasEntities) {
    for (const item of items) {
      for (const entityRow of item._entities || []) {
        const entityInfo = entityRow.entities || {};
        const entityType = entityInfo.entity_type || "";
        const brand = entityInfo.brand || "";
        if (!["competitor_product", "brand"].includes(entityType) || !brand) continue;
        const brandLower = brand.toLowerCase();
        let matchedBrand: string | null = null;
        for (const [bKey, bName] of Object.entries(COMPETITOR_BRANDS)) {
          if (bKey === brandLower || bName.toLowerCase() === brandLower) { matchedBrand = bName; break; }
        }
        if (!matchedBrand || !brandData[matchedBrand]) continue;
        brandData[matchedBrand].total_mentions++;
        const mentionType = entityRow.mention_type || "direct";
        const contextMap: Record<string, string> = { comparison: "comparison", recommendation: "recommendation", complaint: "complaint", direct: "general" };
        const context = contextMap[mentionType] || "general";
        brandData[matchedBrand].context_breakdown[context]++;
        if (brandData[matchedBrand].sample_snippets.length < 3) {
          const snippet = entityRow.context_snippet || (item.title || "").slice(0, 150);
          if (snippet) brandData[matchedBrand].sample_snippets.push(snippet);
        }
        if (brandData[matchedBrand].items.length < 20) {
          brandData[matchedBrand].items.push({
            title: (item.title || "").slice(0, 120), url: item.source_url || "",
            source: item._display_source || item.source || "", context,
            sentiment: entityRow.sentiment || item.sentiment || "",
            posted_at: item.posted_at || "",
          });
        }
      }
    }
  } else {
    for (const item of items) {
      const combined = ((item.title || "") + " " + (item.content || "")).toLowerCase();
      for (const [brandKey, brandName] of Object.entries(COMPETITOR_BRANDS)) {
        if (!combined.includes(brandKey)) continue;
        if (!brandData[brandName]) continue;
        brandData[brandName].total_mentions++;
        const context = classifyContext(combined);
        brandData[brandName].context_breakdown[context]++;
        if (brandData[brandName].sample_snippets.length < 3) {
          const snippet = (item.title || item.content || "").slice(0, 150);
          if (snippet) brandData[brandName].sample_snippets.push(snippet);
        }
        if (brandData[brandName].items.length < 20) {
          brandData[brandName].items.push({
            title: (item.title || "").slice(0, 120), url: item.source_url || "",
            source: item._display_source || item.source || "", context,
            sentiment: item.sentiment || "",
            posted_at: item.posted_at || "",
          });
        }
      }
    }
  }

  const competitorMentions = Object.values(brandData).filter((d: any) => d.total_mentions > 0);
  competitorMentions.sort((a: any, b: any) => b.total_mentions - a.total_mentions);

  // Competitor weaknesses from product intelligence
  const competitorWeaknesses: any[] = [];
  const competitorsData = productIntelligence.competitors || {};
  const usedAdvantages = new Set<string>();
  // Track which advantage variant index was used per product (for gaps dedup)
  const weaknessVariantIdx: Record<string, number> = {};

  for (const [product, data] of Object.entries(competitorsData)) {
    if (typeof data !== "object") continue;
    const d = data as any;
    const issues: string[] = d.top_issues || [];
    const negCount = d.sentiment?.negative || 0;
    if (issues.length === 0 && negCount === 0) continue;

    // Normalize issues to aspect keys (should already be keys after product-intelligence fix,
    // but handle legacy raw keywords too)
    const aspectKeys: string[] = [];
    for (const issue of issues) {
      if (ASPECT_ADVANTAGE_MAP[issue]) {
        if (!aspectKeys.includes(issue)) aspectKeys.push(issue);
      } else if (KEYWORD_TO_ASPECT[issue]) {
        const mapped = KEYWORD_TO_ASPECT[issue];
        if (!aspectKeys.includes(mapped)) aspectKeys.push(mapped);
      }
    }

    const primaryAspect = aspectKeys[0] || null;
    let beurerAdvantage = "";
    let contentIdea = "";

    if (primaryAspect && ASPECT_ADVANTAGE_MAP[primaryAspect]) {
      const mapping = ASPECT_ADVANTAGE_MAP[primaryAspect];
      // Stable variant index from competitor name
      const nameHash = product.split("").reduce((s, c) => s + c.charCodeAt(0), 0) % mapping.advantages.length;
      // Dedup: pick first unused variant, fallback to nameHash if all used
      let chosenIdx = nameHash;
      for (let offset = 0; offset < mapping.advantages.length; offset++) {
        const idx = (nameHash + offset) % mapping.advantages.length;
        if (!usedAdvantages.has(mapping.advantages[idx])) {
          chosenIdx = idx;
          break;
        }
      }
      beurerAdvantage = mapping.advantages[chosenIdx];
      usedAdvantages.add(beurerAdvantage);
      weaknessVariantIdx[product] = chosenIdx;
      contentIdea = mapping.content_ideas[chosenIdx].replace(/\{competitor\}/g, product);
    } else {
      beurerAdvantage = `Gezielte Differenzierung vs. ${product}`;
      contentIdea = `Beurer-Vorteile vs. ${product} kommunizieren`;
    }

    // Build issue label from aspect keys
    const issueLabels = aspectKeys.slice(0, 3).map(k => ASPECT_LABELS_DE[k] || k);
    const issueStr = issueLabels.length > 0 ? issueLabels.join(", ") : "Negative Erwähnungen";

    competitorWeaknesses.push({
      competitor: product, issue: issueStr, count: negCount,
      beurer_advantage: beurerAdvantage, content_idea: contentIdea,
    });
  }
  competitorWeaknesses.sort((a, b) => b.count - a.count);

  // Per-category
  const TARGET_CATS: Record<string, string> = { blood_pressure: "Blutdruck", pain_tens: "Schmerz/TENS", menstrual: "Menstruation" };
  const byCategory: Record<string, any> = {};
  for (const [catKey, catLabel] of Object.entries(TARGET_CATS)) {
    const catBrands = new Set<string>();
    for (const [brand, cats] of Object.entries(BRAND_CATEGORY_MAP)) {
      if (cats.has(catKey)) catBrands.add(brand);
    }
    const catMentions = competitorMentions.filter((m: any) => catBrands.has(m.brand));
    const catWeaknesses = competitorWeaknesses.filter(w =>
      [...catBrands].some(brand => w.competitor.startsWith(brand) || w.competitor.includes(brand))
    );
    const catContext: Record<string, number> = { comparison: 0, recommendation: 0, complaint: 0, switch: 0, general: 0 };
    for (const m of catMentions as any[]) {
      for (const [ctxKey, ctxVal] of Object.entries(m.context_breakdown || {})) {
        catContext[ctxKey] = (catContext[ctxKey] || 0) + (ctxVal as number);
      }
    }
    byCategory[catKey] = {
      label_de: catLabel, competitor_mentions: catMentions,
      competitor_weaknesses: catWeaknesses.slice(0, 5), context_breakdown: catContext,
      total_competitor_mentions: catMentions.reduce((s: number, m: any) => s + m.total_mentions, 0),
    };
  }

  const allContext: Record<string, number> = { comparison: 0, recommendation: 0, complaint: 0, switch: 0, general: 0 };
  for (const m of competitorMentions as any[]) {
    for (const [ctxKey, ctxVal] of Object.entries(m.context_breakdown || {})) {
      allContext[ctxKey] = (allContext[ctxKey] || 0) + (ctxVal as number);
    }
  }

  // Build competitor_gaps from competitor weaknesses + product intelligence
  const competitorGaps: any[] = [];
  const totalCompetitorMentions = competitorMentions.reduce((s: number, m: any) => s + m.total_mentions, 0);

  for (const weakness of competitorWeaknesses) {
    const product = weakness.competitor;
    const productData = competitorsData[product] as any;
    if (!productData) continue;

    const negCount = productData.sentiment?.negative || 0;
    if (negCount === 0) continue;

    // Find an evidence quote from competitor items
    let evidenceQuote = "";
    for (const item of items) {
      if (!item._entities || item._entities.length === 0) {
        if ((item.product_mentions || []).some(p => p === product) && item.sentiment === "negative") {
          evidenceQuote = extractRepresentativeQuote(item.content || item.title || "", 150);
          break;
        }
        continue;
      }
      const hasProduct = item._entities.some(e => e.entities?.canonical_name === product);
      if (hasProduct && item.sentiment === "negative") {
        evidenceQuote = extractRepresentativeQuote(item.content || item.title || "", 150);
        break;
      }
    }

    // Build weakness label from ALL aspect issues (up to 3)
    const issues: string[] = productData.top_issues || [];
    const aspectKeys: string[] = [];
    for (const issue of issues) {
      if (ASPECT_ADVANTAGE_MAP[issue]) {
        if (!aspectKeys.includes(issue)) aspectKeys.push(issue);
      } else if (KEYWORD_TO_ASPECT[issue]) {
        const mapped = KEYWORD_TO_ASPECT[issue];
        if (!aspectKeys.includes(mapped)) aspectKeys.push(mapped);
      }
    }
    const weaknessLabels = aspectKeys.slice(0, 3).map(k => ASPECT_LABELS_DE[k] || k);
    const weaknessLabel = weaknessLabels.length > 0 ? weaknessLabels.join(" / ") : "Negative Erwähnungen";

    // Pick a DIFFERENT advantage variant than was used for the weakness row
    let gapAdvantage = weakness.beurer_advantage || "";
    const primaryAspect = aspectKeys[0] || null;
    if (primaryAspect && ASPECT_ADVANTAGE_MAP[primaryAspect]) {
      const mapping = ASPECT_ADVANTAGE_MAP[primaryAspect];
      const usedIdx = weaknessVariantIdx[product] ?? 0;
      const altIdx = (usedIdx + 1) % mapping.advantages.length;
      gapAdvantage = mapping.advantages[altIdx];
    }

    competitorGaps.push({
      competitor: product,
      weakness: weaknessLabel,
      evidence_count: negCount,
      evidence_quote: evidenceQuote,
      beurer_advantage: gapAdvantage,
      opportunity_score: totalCompetitorMentions > 0
        ? Math.round((negCount / totalCompetitorMentions) * 100) / 100
        : 0,
    });
  }
  competitorGaps.sort((a, b) => b.opportunity_score - a.opportunity_score);

  const aspectComparison = buildAspectComparison(items);

  return {
    competitor_mentions: competitorMentions,
    competitor_weaknesses: competitorWeaknesses.slice(0, 5),
    context_breakdown: allContext,
    by_category: byCategory,
    competitor_gaps: competitorGaps.slice(0, 10),
    aspect_comparison: aspectComparison,
  };
}

function buildAspectComparison(items: SocialItem[]) {
  const MIN_MENTIONS = 5;
  const beurerAspects: Record<string, Record<string, number>> = {};
  const competitorAspects: Record<string, Record<string, number>> = {};

  for (const item of items) {
    const aspects = item._aspects || [];
    const entities = item._entities || [];
    if (aspects.length === 0 || entities.length === 0) continue;

    const isBeurer = entities.some(e => (e.entities?.entity_type) === "beurer_product");
    const isCompetitor = entities.some(e => {
      const eType = e.entities?.entity_type || "";
      const brand = (e.entities?.brand || "").toLowerCase();
      return ["competitor_product", "brand"].includes(eType) && brand in COMPETITOR_BRANDS;
    });

    for (const asp of aspects) {
      const aspectKey = asp.aspect;
      const sentiment = asp.sentiment;
      if (!aspectKey || !sentiment) continue;
      if (isBeurer) {
        if (!beurerAspects[aspectKey]) beurerAspects[aspectKey] = { positive: 0, neutral: 0, negative: 0 };
        beurerAspects[aspectKey][sentiment] = (beurerAspects[aspectKey][sentiment] || 0) + 1;
      }
      if (isCompetitor) {
        if (!competitorAspects[aspectKey]) competitorAspects[aspectKey] = { positive: 0, neutral: 0, negative: 0 };
        competitorAspects[aspectKey][sentiment] = (competitorAspects[aspectKey][sentiment] || 0) + 1;
      }
    }
  }

  const comparisons: any[] = [];
  for (const aspectKey of ASPECT_CATEGORIES) {
    const b = beurerAspects[aspectKey] || { positive: 0, neutral: 0, negative: 0 };
    const c = competitorAspects[aspectKey] || { positive: 0, neutral: 0, negative: 0 };
    const bTotal = b.positive + b.neutral + b.negative;
    const cTotal = c.positive + c.neutral + c.negative;

    const bPosPct = bTotal > 0 ? Math.round(b.positive / bTotal * 100) : 0;
    const cPosPct = cTotal > 0 ? Math.round(c.positive / cTotal * 100) : 0;
    const delta = bPosPct - cPosPct;
    const isSignificant = bTotal >= MIN_MENTIONS && cTotal >= MIN_MENTIONS;

    comparisons.push({
      aspect: aspectKey,
      label_de: ASPECT_LABELS_DE[aspectKey] || aspectKey,
      beurer: {
        positive_pct: bPosPct,
        neutral_pct: bTotal > 0 ? Math.round(b.neutral / bTotal * 100) : 0,
        negative_pct: bTotal > 0 ? Math.round(b.negative / bTotal * 100) : 0,
        total: bTotal,
      },
      competitor: {
        positive_pct: cPosPct,
        neutral_pct: cTotal > 0 ? Math.round(c.neutral / cTotal * 100) : 0,
        negative_pct: cTotal > 0 ? Math.round(c.negative / cTotal * 100) : 0,
        total: cTotal,
      },
      advantage_delta: delta,
      is_significant: isSignificant,
    });
  }

  const beurerAdvantages = comparisons
    .filter(c => c.is_significant && c.advantage_delta > 10)
    .map(c => ({
      aspect: c.aspect,
      label_de: c.label_de,
      delta: c.advantage_delta,
      beurer_total: c.beurer.total,
      competitor_total: c.competitor.total,
      advantage_text: ASPECT_ADVANTAGE_MAP[c.aspect]?.advantages?.[0] || "",
    }))
    .sort((a, b) => b.delta - a.delta);

  return {
    comparisons,
    beurer_advantages: beurerAdvantages,
    min_sample_threshold: MIN_MENTIONS,
  };
}

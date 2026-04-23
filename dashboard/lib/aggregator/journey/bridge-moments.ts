import type { SocialItem } from "../types";
import { BRIDGE_PATTERNS, PAIN_CATEGORY_LABELS_DE, STORED_BRIDGE_TO_PATTERN } from "../../constants";

const QA_SOURCES = new Set(["gutefrage", "reddit", "health_forums", "diabetes_forum", "endometriose", "rheuma_liga", "onmeda", "fragen.onmeda.de"]);

function resolveDisplaySource(item: SocialItem): string {
  let displaySource = item.source || "unknown";
  if (displaySource === "serper_brand" || displaySource === "serper_discovery") {
    if (item.source_url) {
      try { displaySource = new URL(item.source_url).hostname.replace(/^www\./, ""); } catch {}
    }
  }
  return displaySource;
}

function buildItemDict(item: SocialItem, detectionMethod: "llm" | "keyword"): any {
  const displaySource = resolveDisplaySource(item);
  const entities = item._entities || [];
  const involvedProducts = entities
    .map(e => e.entities?.canonical_name)
    .filter((n): n is string => !!n);

  const itemDict: any = {
    id: item.id,
    title: (item.title || "").slice(0, 120),
    source: displaySource,
    url: item.source_url || "",
    trigger_context: item.key_insight || "",
    from_stage: item.journey_stage || "",
    category: PAIN_CATEGORY_LABELS_DE[item.pain_category || ""] || "",
    // Enhanced fields
    detection_method: detectionMethod,
    beurer_opportunity: item.beurer_opportunity || null,
    involved_products: [...new Set(involvedProducts)],
    bridge_moment_raw: item.bridge_moment || null,
  };

  const topAnswers = item._top_answers || [];
  if (topAnswers.length > 0) {
    itemDict.question = (item.question_content || item.title || "").slice(0, 200);
    itemDict.answers = topAnswers.slice(0, 2).map(a => ({
      content: (a.content || "").slice(0, 200), author: a.author || "",
      votes: a.votes || 0, is_accepted: a.is_accepted || false,
    }));
    itemDict.answer_count = item._answer_count || item.answer_count || 0;
    itemDict.has_qa = true;
  } else {
    itemDict.has_qa = false;
  }

  return itemDict;
}

export function buildBridgeMoments(items: SocialItem[]) {
  const candidates: Record<string, Array<{ score: number; itemDict: any; rawItem: SocialItem }>> = {};
  for (const patKey of Object.keys(BRIDGE_PATTERNS)) candidates[patKey] = [];

  // Track items assigned in Pass 1 to skip in Pass 2
  const llmAssignedIds = new Set<string | undefined>();

  // ── Pass 1: LLM-detected bridge moments ──
  for (const item of items) {
    const bridgeValue = item.bridge_moment;
    if (!bridgeValue || bridgeValue === "none_identified") continue;

    const patKey = STORED_BRIDGE_TO_PATTERN[bridgeValue];
    if (!patKey || !candidates[patKey]) continue;

    llmAssignedIds.add(item.id);

    // Base score = 5 (higher than typical keyword matches of 1-3)
    let score = 5;
    const source = (item.source || "unknown").toLowerCase();
    const answerCount = item._answer_count || item.answer_count || 0;

    if (item.key_insight) score++;
    if (QA_SOURCES.has(source)) score++;
    if (answerCount > 0) { score += 2; if (answerCount >= 3) score++; }
    if ((item._entities || []).length > 0) score++;
    if (item.beurer_opportunity) score++;

    const itemDict = buildItemDict(item, "llm");
    candidates[patKey].push({ score, itemDict, rawItem: item });
  }

  // ── Pass 2: Keyword fallback (remaining items only) ──
  for (const item of items) {
    if (llmAssignedIds.has(item.id)) continue;

    const stage = item.journey_stage;
    if (!stage) continue;

    const searchable = ((item.title || "") + " " + (item.content || "")).toLowerCase();
    const coping = item.coping_strategies || [];
    const category = item.category || "";
    const source = (item.source || "unknown").toLowerCase();

    for (const [patKey, pat] of Object.entries(BRIDGE_PATTERNS)) {
      if (pat.stages && !pat.stages.includes(stage)) continue;
      if (pat.categories && !pat.categories.includes(category)) continue;
      const keywordHits = pat.keywords.filter(kw => searchable.includes(kw)).length;
      if (keywordHits === 0) continue;

      let score = keywordHits;
      const copingSignals = pat.coping_signal || [];
      score += copingSignals.filter(cs => coping.includes(cs)).length * 2;
      if (item.key_insight) score++;
      if (QA_SOURCES.has(source)) score++;
      const answerCount = item._answer_count || item.answer_count || 0;
      if (answerCount > 0) { score += 2; if (answerCount >= 3) score++; }

      const itemDict = buildItemDict(item, "keyword");
      candidates[patKey].push({ score, itemDict, rawItem: item });
    }
  }

  // ── Build output patterns ──
  const totalDetected = Object.values(candidates).reduce((s, c) => s + c.length, 0);
  const patterns: any[] = [];

  for (const [patKey, pat] of Object.entries(BRIDGE_PATTERNS)) {
    const cands = candidates[patKey];
    if (cands.length === 0) continue;
    const count = cands.length;
    const percentage = totalDetected > 0 ? Math.round((count / totalDetected) * 100) : 0;
    cands.sort((a, b) => b.score - a.score);
    const topRaw = cands[0].rawItem;
    let representativeQuote = topRaw.key_insight || "";
    if (!representativeQuote) {
      const raw = (topRaw.content || "").slice(0, 150).trim();
      if (raw.length > 80) {
        const lastSpace = raw.lastIndexOf(" ", 150);
        representativeQuote = lastSpace > 80 ? raw.slice(0, lastSpace) + "..." : raw;
      } else {
        representativeQuote = raw;
      }
    }

    let qaThread = null;
    for (const c of cands.slice(0, 5)) {
      if (c.itemDict.has_qa && c.itemDict.answers?.length > 0) {
        qaThread = { question: c.itemDict.question, answers: c.itemDict.answers, answer_count: c.itemDict.answer_count, source: c.itemDict.source };
        break;
      }
    }

    patterns.push({
      bridge_type: patKey, label_de: pat.label_de, label_en: pat.label_en,
      flow_de: pat.flow_de || pat.label_de, flow_en: pat.flow_en || pat.label_en,
      count, percentage, representative_quote: representativeQuote,
      quote_source: cands[0].itemDict.source,
      items: cands.slice(0, 5).map(c => c.itemDict),
      all_item_ids: cands.map(c => c.itemDict.id).filter(Boolean),
      qa_thread: qaThread,
    });
  }

  patterns.sort((a, b) => b.count - a.count);
  return { total_detected: totalDetected, patterns };
}

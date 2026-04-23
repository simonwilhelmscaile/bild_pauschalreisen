import type { SocialItem } from "./types";
import { getEngagementCount } from "./utils";
import { INTENT_OPP_WEIGHTS } from "../constants";

const QUESTION_KEYWORDS = ["wie", "warum", "was", "welch", "hilft", "empfehl"];
const PREFERRED_SOURCES = new Set([
  "gutefrage", "reddit", "health_forums", "diabetes_forum",
  "endometriose", "rheuma_liga", "onmeda",
]);
const EMOTION_BOOST_SET = new Set(["frustration", "confusion", "anxiety"]);

export function buildContentOpportunities(items: SocialItem[]) {
  const opportunities: any[] = [];

  for (const item of items) {
    const source = item.source || "";
    if (source === "amazon" || source === "amazon.de") continue;

    const content = (item.content || "").toLowerCase();
    const title = (item.title || "").toLowerCase();
    const combined = title + " " + content;
    const hasQuestionMark = (item.title || "").includes("?");
    const relevance = item.relevance_score || 0;
    const deviceRelevance = item.device_relevance_score || 0;

    // Three-tier detection: at least one must fire
    const hasLlmSignal = !!item.content_opportunity;
    const intentWeight = INTENT_OPP_WEIGHTS[item.intent || ""] ?? 0;
    const hasIntentSignal = intentWeight > 0;
    const hasKeywordSignal = QUESTION_KEYWORDS.some(kw => combined.includes(kw)) ||
      hasQuestionMark;

    if (!hasLlmSignal && !hasIntentSignal && !hasKeywordSignal) continue;

    // Minimum relevance gate (relaxed for LLM-detected)
    if (!hasLlmSignal && relevance < 0.3) continue;
    if (!hasLlmSignal && !hasIntentSignal && deviceRelevance < 0.5 && !hasQuestionMark) continue;

    // Determine detection method (strongest signal wins)
    let detectionMethod: string;
    if (hasLlmSignal) detectionMethod = "llm";
    else if (hasIntentSignal) detectionMethod = "intent";
    else detectionMethod = "keyword";

    // Scoring formula (0-10 scale)
    const llmSignal = hasLlmSignal ? 1.0 : 0;
    const intentSignal = intentWeight;

    const answerCount = item.answer_count || 0;
    const unansweredBoost = answerCount === 0 ? 1.0 : answerCount === 1 ? 0.5 : 0;

    const emotionBoost = EMOTION_BOOST_SET.has(item.emotion || "") ? 0.7 : 0;
    const sourceBoost = PREFERRED_SOURCES.has(source) ? 0.5 : 0;

    const engagementRaw = getEngagementCount(item) || 0;
    const engagementBoost = Math.min(engagementRaw / 50, 1.0);

    const gapScore = Math.round((
      llmSignal * 3.0 +
      intentSignal * 2.0 +
      relevance * 1.5 +
      deviceRelevance * 1.0 +
      unansweredBoost * 1.0 +
      emotionBoost * 0.5 +
      sourceBoost * 0.5 +
      engagementBoost * 0.5
    ) * 10) / 10;

    opportunities.push({
      source_item_id: item.id || null,
      topic: (item.title || "").slice(0, 120) || (item.content || "").slice(0, 120),
      category: item.category,
      gap_score: gapScore,
      source: item._display_source || source,
      url: item.source_url || "",
      content_snippet: (item.content || "").slice(0, 300),
      keywords: item.keywords || [],
      llm_opportunity: item.content_opportunity || null,
      detection_method: detectionMethod,
      intent: item.intent || null,
      emotion: item.emotion || null,
      answer_count: answerCount,
      key_insight: item.key_insight || null,
      device_relevance_score: deviceRelevance,
      product_mentions: item.product_mentions || [],
    });
  }

  opportunities.sort((a, b) => b.gap_score - a.gap_score);
  return opportunities.slice(0, 10);
}

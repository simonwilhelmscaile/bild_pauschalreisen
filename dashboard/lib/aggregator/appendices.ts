import type { SocialItem } from "./types";
import { categorizeQuestion, suggestResponseAngle, buildContentPreview, getProductType, isCompetitorSpecificQuestion } from "./utils";

export function buildAppendices(items: SocialItem[]) {
  const appendices: { device_questions: any[]; negative_experiences: any[]; positive_experiences: any[] } = {
    device_questions: [], negative_experiences: [], positive_experiences: [],
  };

  for (const item of items) {
    const deviceRelevance = item.device_relevance_score || 0;
    const sentiment = item.sentiment;
    const title = item.title || "";
    const hasQuestion = title.includes("?");
    const productMentions = item.product_mentions || [];

    if (hasQuestion && deviceRelevance >= 0.7 && !isCompetitorSpecificQuestion(item)) {
      const questionCategory = categorizeQuestion(item);
      appendices.device_questions.push({
        question: title.slice(0, 150),
        source: item.source,
        url: item.source_url,
        category: questionCategory,
        device_relevance_score: deviceRelevance,
        response_angle: suggestResponseAngle(item, questionCategory),
        content_preview: buildContentPreview(item),
      });
    }

    if (sentiment === "negative" && (productMentions.length > 0 || deviceRelevance >= 0.5)) {
      const productType = productMentions.length > 0 ? getProductType(productMentions) : "unknown";
      if (productType === "competitor") continue;
      if (isCompetitorSpecificQuestion(item)) continue;
      const severity = productType === "beurer" ? "high" : "medium";
      const defaultAction = productType === "beurer" ? "An QA eskalieren" : "Beobachten";
      appendices.negative_experiences.push({
        issue: title || (item.content || "").slice(0, 100),
        product: productMentions[0] || null,
        source: item.source,
        url: item.source_url,
        severity,
        action: defaultAction,
        content_preview: buildContentPreview(item),
        device_relevance_score: deviceRelevance,
      });
    }

    if (sentiment === "positive" && (productMentions.length > 0 || deviceRelevance >= 0.5)) {
      const productType = productMentions.length > 0 ? getProductType(productMentions) : "unknown";
      if (productType === "competitor") continue;
      if (isCompetitorSpecificQuestion(item)) continue;
      const defaultAmplification = productMentions.length > 0 ? "Als Testimonial nutzen" : "Social Media teilen";
      appendices.positive_experiences.push({
        praise: title || (item.content || "").slice(0, 100),
        product: productMentions[0] || null,
        source: item.source,
        url: item.source_url,
        amplification_idea: defaultAmplification,
        content_preview: buildContentPreview(item),
        device_relevance_score: deviceRelevance,
      });
    }
  }

  appendices.device_questions.sort((a, b) => (b.device_relevance_score || 0) - (a.device_relevance_score || 0));
  appendices.negative_experiences.sort((a, b) => (a.severity === "high" ? 1 : 0) - (b.severity === "high" ? 1 : 0)).reverse();
  return appendices;
}

import type { SocialItem } from "./types";
import { categorizeQuestion, isDeviceQuestion, isCompetitorSpecificQuestion, scoreDeviceRelevance } from "./utils";

const QUESTION_STARTERS = [
  "wie ", "was ", "warum ", "welch", "wer ", "wo ", "wann ",
  "kann ", "ist ", "hat ", "soll ", "gibt ", "kennt ", "hilft ",
  "lohnt ", "taugt ", "stimmt ", "braucht ", "empfiehlt ",
];

export function buildUserVoice(allItems: SocialItem[], filteredItems: SocialItem[]) {
  const deviceQuestions: Array<{ item: SocialItem; score: number }> = [];

  for (const item of allItems) {
    const title = item.title || "";
    if (!title) continue;
    const titleLower = title.toLowerCase().trim();
    const isQuestion = title.includes("?") || QUESTION_STARTERS.some(q => titleLower.startsWith(q));
    if (!isQuestion) continue;
    let score = item.device_relevance_score ?? null;
    if (score === null) score = scoreDeviceRelevance(item) / 100;
    if (score >= 0.7 && isDeviceQuestion(item) && !isCompetitorSpecificQuestion(item)) {
      deviceQuestions.push({ item, score });
    }
  }

  deviceQuestions.sort((a, b) => b.score - a.score);

  const seenTitles = new Set<string>();
  const topQuestions: any[] = [];
  for (const { item, score } of deviceQuestions) {
    const titleNorm = (item.title || "").trim().toLowerCase();
    if (seenTitles.has(titleNorm)) continue;
    seenTitles.add(titleNorm);
    topQuestions.push({
      question: (item.title || "").slice(0, 150),
      source: item.source,
      topic_category: item.category,
      question_category: categorizeQuestion(item),
      url: item.source_url,
      device_relevance_score: score,
    });
    if (topQuestions.length >= 10) break;
  }

  const questionsByCategory = {
    purchase_intent: topQuestions.filter(q => q.question_category === "purchase_intent"),
    troubleshooting: topQuestions.filter(q => q.question_category === "troubleshooting"),
    usage: topQuestions.filter(q => q.question_category === "usage"),
  };

  const painPoints = filteredItems
    .filter(i => i.sentiment === "negative")
    .slice(0, 10)
    .map(item => ({
      issue: item.title || (item.content || "").slice(0, 100),
      source: item.source,
      category: item.category,
    }));

  return {
    user_voice: { top_questions: topQuestions, questions_by_category: questionsByCategory, pain_points: painPoints },
    device_questions_count: topQuestions.length,
  };
}

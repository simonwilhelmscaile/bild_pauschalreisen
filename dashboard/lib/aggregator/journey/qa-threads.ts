import type { SocialItem } from "../types";
import { BRIDGE_PATTERNS, QA_BRIDGE_OVERRIDES } from "../../constants";
import { Counter } from "../utils";

function buildYoutubeThreads(items: SocialItem[]) {
  const videos: Record<string, any> = {};
  for (const item of items) {
    const raw = item.raw_data || {};
    const videoId = raw.video_id;
    if (!videoId) continue;
    if (!videos[videoId]) {
      videos[videoId] = {
        video_id: videoId, title: raw.video_title || item.title || "",
        url: `https://www.youtube.com/watch?v=${videoId}`,
        comments: [], transcript: null, category: item.category || "",
        journey_stage: item.journey_stage || "", relevance: item.relevance_score || 0,
        device_rel: item.device_relevance_score || 0, sentiment: item.sentiment || "",
        posted_at: item.posted_at || "", id: item.id,
      };
    }
    if (item.source === "youtube") {
      const content = (item.content || "").trim();
      if (content && content.length > 10) {
        videos[videoId].comments.push({ content: content.slice(0, 400), author: "", votes: raw.likes || 0, is_accepted: false });
      }
    } else if (item.source === "youtube_transcript") {
      videos[videoId].transcript = (item.content || "").slice(0, 1000);
      videos[videoId].relevance = Math.max(videos[videoId].relevance, item.relevance_score || 0);
    }
  }
  const threads: any[] = [];
  for (const data of Object.values(videos)) {
    if (data.comments.length === 0) continue;
    let question = data.title;
    if (data.transcript) question += "\n\n" + data.transcript;
    data.comments.sort((a: any, b: any) => b.votes - a.votes);
    const score = data.comments.length + data.relevance * 3 + data.device_rel * 5;
    threads.push({
      id: data.id, question, source: "youtube", url: data.url,
      category: data.category, journey_stage: data.journey_stage,
      sentiment: data.sentiment, posted_at: data.posted_at,
      answer_count: data.comments.length, answers: data.comments.slice(0, 3),
      entities: [], score: Math.round(score * 10) / 10,
      analysis: null, action: null,
      device_relevance_score: data.device_rel,
    });
  }
  threads.sort((a, b) => b.score - a.score);
  return threads;
}

export function buildQaThreads(items: SocialItem[]) {
  const threads: any[] = [];
  for (const item of items) {
    const answers = item._top_answers || [];
    if (answers.length === 0) continue;
    const question = item.question_content || item.title || "";
    if (!question) continue;
    const answerCount = item._answer_count || item.answer_count || answers.length;
    const hasAccepted = answers.some(a => a.is_accepted);
    const voteSum = answers.reduce((s, a) => s + (a.votes || 0), 0);
    const relevance = item.relevance_score || 0;
    const deviceRel = item.device_relevance_score || 0;
    const score = answerCount + (hasAccepted ? 3 : 0) + Math.min(voteSum / 5, 5) + relevance * 3 + deviceRel * 5;
    const entities = (item._entities || [])
      .map(e => e.entities?.canonical_name || "").filter(Boolean).slice(0, 3);
    threads.push({
      id: item.id, question, source: item._display_source || item.source || "",
      url: item.source_url || "", category: item.category || "",
      journey_stage: item.journey_stage || "", sentiment: item.sentiment || "",
      posted_at: item.posted_at || "", answer_count: answerCount,
      answers: answers.slice(0, 3).map(a => ({
        content: (a.content || "").slice(0, 400), author: a.author || "",
        votes: a.votes || 0, is_accepted: a.is_accepted || false,
      })),
      entities, score: Math.round(score * 10) / 10, analysis: null, action: null,
      device_relevance_score: deviceRel,
    });
  }
  // Add YouTube threads
  threads.push(...buildYoutubeThreads(items));
  threads.sort((a, b) => b.score - a.score);
  // Source diversity: cap any single source at 60%
  const maxThreads = 30;
  const maxPerSource = Math.floor(maxThreads * 0.6);
  const sourceCounts: Record<string, number> = {};
  const diverse: any[] = [];
  const overflow: any[] = [];
  for (const t of threads) {
    const src = t.source;
    if ((sourceCounts[src] || 0) < maxPerSource) {
      diverse.push(t);
      sourceCounts[src] = (sourceCounts[src] || 0) + 1;
    } else {
      overflow.push(t);
    }
    if (diverse.length >= maxThreads) break;
  }
  for (const t of overflow) {
    if (diverse.length >= maxThreads) break;
    diverse.push(t);
  }
  return diverse;
}

export function tagQaThreadsWithBridges(qaThreads: any[], items: SocialItem[]) {
  const itemsById: Record<string, SocialItem> = {};
  for (const i of items) if (i.id) itemsById[i.id] = i;

  for (const thread of qaThreads) {
    const parts = [thread.question || ""];
    for (const ans of thread.answers || []) parts.push(ans.content || "");
    const searchable = parts.join(" ").toLowerCase();
    const fullItem = itemsById[thread.id] || {};
    const stage = (fullItem as SocialItem).journey_stage || thread.journey_stage || "";
    const category = (fullItem as SocialItem).category || thread.category || "";
    const matched: string[] = [];
    for (const [patKey, pat] of Object.entries(BRIDGE_PATTERNS)) {
      if (pat.stages && !pat.stages.includes(stage)) continue;
      if (pat.categories && !pat.categories.includes(category)) continue;
      const override = QA_BRIDGE_OVERRIDES[patKey];
      const keywordsDe = override ? override.keywords : pat.keywords;
      const keywordsEn = (override || pat).keywords_en || [];
      if (keywordsDe.some(kw => searchable.includes(kw)) || keywordsEn.some(kw => searchable.includes(kw))) {
        matched.push(patKey);
      }
    }
    thread.bridge_types = matched;
  }
}

export function buildBridgeSummaryFromQa(qaThreads: any[]) {
  const taggedThreads = qaThreads.filter(t => (t.bridge_types || []).length > 0);
  const totalDetected = taggedThreads.length;
  const typeCounts = new Counter<string>();
  for (const thread of taggedThreads) {
    for (const bt of thread.bridge_types) typeCounts.increment(bt);
  }
  const patterns: any[] = [];
  for (const [patKey, pat] of Object.entries(BRIDGE_PATTERNS)) {
    const count = typeCounts.get(patKey);
    if (count === 0) continue;
    patterns.push({
      bridge_type: patKey, label_de: pat.label_de, label_en: pat.label_en,
      count, percentage: totalDetected > 0 ? Math.round((count / totalDetected) * 100) : 0,
    });
  }
  patterns.sort((a, b) => b.count - a.count);
  return { total_detected: totalDetected, patterns };
}

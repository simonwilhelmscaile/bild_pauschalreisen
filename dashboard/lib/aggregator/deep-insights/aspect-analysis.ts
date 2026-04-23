import type { SocialItem } from "../types";
import { ASPECT_LABELS_DE } from "../../constants";
import { Counter } from "../utils";

export function buildAspectAnalysis(items: SocialItem[]) {
  const aspectData: Record<string, {
    sentiments: Counter<string>; intensities: number[];
    evidence: string[]; mentions: any[];
  }> = {};

  for (const item of items) {
    for (const asp of item._aspects || []) {
      const aspect = asp.aspect || "";
      if (!aspect) continue;
      if (!aspectData[aspect]) aspectData[aspect] = { sentiments: new Counter(), intensities: [], evidence: [], mentions: [] };
      const sent = asp.sentiment || "neutral";
      aspectData[aspect].sentiments.increment(sent);
      if (asp.intensity != null) aspectData[aspect].intensities.push(asp.intensity);
      if (asp.evidence_snippet && aspectData[aspect].evidence.length < 2) {
        aspectData[aspect].evidence.push(asp.evidence_snippet.slice(0, 100));
      }
      if (aspectData[aspect].mentions.length < 25) {
        const src = item._display_source || item.source || "";
        const url = item.source_url || "";
        let ctype = "";
        if (src === "youtube" || src === "youtube_transcript") ctype = src === "youtube_transcript" ? "transcript" : (url.includes("&lc=") ? "comment" : "video");
        else if (["gutefrage", "onmeda", "diabetes_forum", "rheuma_liga", "endometriose"].includes(src)) ctype = "forum";
        else if (src === "reddit") ctype = "post";
        else if (src === "amazon") ctype = "review";
        aspectData[aspect].mentions.push({
          text: (asp.evidence_snippet || item.title || "").slice(0, 150),
          source: src, url, sentiment: sent, type: ctype,
          posted_at: item.posted_at || "",
        });
      }
    }
  }

  const result: any[] = [];
  for (const [aspect, data] of Object.entries(aspectData)) {
    const total = data.sentiments.total() || 1;
    const intensities = data.intensities;
    result.push({
      aspect, label_de: ASPECT_LABELS_DE[aspect] || aspect,
      total_mentions: total,
      positive_pct: Math.round((data.sentiments.get("positive") / total) * 100),
      neutral_pct: Math.round((data.sentiments.get("neutral") / total) * 100),
      negative_pct: Math.round((data.sentiments.get("negative") / total) * 100),
      avg_intensity: intensities.length > 0 ? Math.round((intensities.reduce((a, b) => a + b, 0) / intensities.length) * 10) / 10 : null,
      evidence_snippets: data.evidence,
      mentions: data.mentions,
    });
  }
  result.sort((a, b) => b.total_mentions - a.total_mentions);
  return { aspects: result, total_items_with_aspects: items.filter(i => (i._aspects || []).length > 0).length };
}

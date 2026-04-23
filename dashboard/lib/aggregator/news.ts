/**
 * News aggregation module — scores + tiers Exa-crawled articles.
 *
 * Scale: 0–30.  Real articles routinely hit 25-30 for top relevance.
 */
import type { SocialItem } from "./types";
import { COMPETITOR_BRANDS, BEURER_PRODUCTS } from "../constants";

// ─── Source tiers ───

const TIER1_SOURCES = new Set([
  "Search Engine Land",
  "Search Engine Journal",
  "Google Search Central",
  "Google Blog",
  "Ars Technica",
  "The Verge",
  "TechCrunch",
  "Wired",
  "Reuters",
  "Bloomberg",
]);
const TIER2_SOURCES = new Set([
  "Search Engine Roundtable",
  "Semrush",
  "Ahrefs",
  "Moz",
  "Backlinko",
  "HubSpot",
  "Content Marketing Institute",
  "SEO Südwest",
  "Forbes",
  "Business Insider",
]);

const HOT_TOPICS: { pattern: RegExp; tag: string }[] = [
  { pattern: /\bAI\s*Overviews?\b/i, tag: "AI Overviews" },
  { pattern: /\bSGE\b/i, tag: "SGE" },
  { pattern: /\bAEO\b/i, tag: "AEO" },
  { pattern: /\bGEO\b/i, tag: "GEO" },
  { pattern: /\bzero[\s-]*click/i, tag: "Zero-Click" },
  { pattern: /\bGoogle\s+(Discover|AI\s+Mode)/i, tag: "Google AI" },
];

const COMPANY_NAME = "Beurer";
const COMPETITOR_BRAND_NAMES = Object.values(COMPETITOR_BRANDS);
const PRODUCT_NAMES = BEURER_PRODUCTS;

// ─── Scoring (out of 30) ───

export interface NewsArticle {
  title: string;
  url: string;
  source: string;
  posted_at: string;
  summary: string;
  author: string | null;
  score: number;
  tier: "must_read" | "interesting" | "worth_reading";
  topic_tags: string[];
  is_competitor: boolean;
  news_category: "industry" | "company" | "competitor" | "curated";
  submitted_by?: string;
}

export interface NewsData {
  articles: NewsArticle[];
  by_topic: Record<string, number>;
  by_source: Record<string, number>;
  total: number;
}

function scoreArticle(item: SocialItem): { score: number; tags: string[] } {
  let score = 0;
  const tags: string[] = [];
  const text = `${item.title || ""} ${item.content || ""}`;

  // 1. Exa relevance (0–10)
  const exaScore = item.raw_data?.exa_score ?? 0;
  score += Math.min(Math.round(exaScore * 30), 10);

  // 2. Source tier (0–8)
  const source = item.source || "";
  if (TIER1_SOURCES.has(source)) score += 8;
  else if (TIER2_SOURCES.has(source)) score += 5;
  else score += 1;

  // 3. Recency (0–8)
  if (item.posted_at) {
    const daysOld = (Date.now() - new Date(item.posted_at).getTime()) / 86400000;
    if (daysOld <= 1) score += 8;
    else if (daysOld <= 3) score += 6;
    else if (daysOld <= 7) score += 4;
    else if (daysOld <= 14) score += 2;
  }

  // 4. Hot topic (+5)
  for (const { pattern, tag } of HOT_TOPICS) {
    if (pattern.test(text)) {
      tags.push(tag);
    }
  }
  if (tags.length > 0) score += 5;

  // 5. Tenant relevance (max +9)
  const textLower = text.toLowerCase();
  const companyLower = COMPANY_NAME.toLowerCase();
  if (textLower.includes(companyLower)) {
    score += 9;
    tags.push(COMPANY_NAME);
  } else {
    for (const brand of COMPETITOR_BRAND_NAMES) {
      if (textLower.includes(brand.toLowerCase())) {
        score += 5;
        tags.push(brand);
        break;
      }
    }
    if (!tags.some((t) => COMPETITOR_BRAND_NAMES.includes(t))) {
      for (const prod of PRODUCT_NAMES.slice(0, 5)) {
        if (textLower.includes(prod.toLowerCase())) {
          score += 6;
          tags.push(prod);
          break;
        }
      }
    }
  }

  return { score: Math.min(score, 30), tags };
}

function tierFromScore(score: number): "must_read" | "interesting" | "worth_reading" {
  if (score >= 12) return "must_read";
  if (score >= 7) return "interesting";
  return "worth_reading";
}

// ─── Summary extraction ───

function extractSummary(content: string, maxChars = 280): string {
  if (!content) return "";
  const clean = content.replace(/\s+/g, " ").trim();
  const sentences = clean.split(/(?<=[.!?])\s+/);
  let summary = "";
  for (const s of sentences) {
    const trimmed = s.trim();
    if (trimmed.length < 35) continue;
    if (/^[A-Z][a-zA-Z\s&|/–-]{0,40}$/.test(trimmed)) continue;
    const candidate = summary ? summary + " " + trimmed : trimmed;
    if (candidate.length > maxChars) break;
    summary = candidate;
    if (summary.split(/[.!?]/).length - 1 >= 2) break;
  }
  if (!summary) {
    for (const seg of clean.split(/\s{2,}/)) {
      if (seg.trim().length >= 60) {
        summary = seg.trim().slice(0, maxChars);
        const lastSpace = summary.lastIndexOf(" ");
        if (lastSpace > 60) summary = summary.slice(0, lastSpace);
        break;
      }
    }
  }
  return summary;
}

// ─── Main aggregation ───

export function buildNewsData(allItems: SocialItem[]): NewsData {
  // Include exa-crawled and curated items
  const newsItems = allItems.filter(
    (i) => i.raw_data?.exa_query != null || i.source === "exa" || i.raw_data?.curated === true
  );

  if (newsItems.length === 0) {
    return { articles: [], by_topic: {}, by_source: {}, total: 0 };
  }

  const articles: NewsArticle[] = [];
  const byTopic: Record<string, number> = {};
  const bySource: Record<string, number> = {};

  for (const item of newsItems) {
    const isCurated = item.raw_data?.curated === true;

    if (isCurated) {
      // Curated items always rank as must_read
      const topics: string[] = item.raw_data?.topic_tags || item.keywords || [];
      articles.push({
        title: item.title || "Untitled",
        url: item.source_url || "",
        source: item.source || "Unknown",
        posted_at: item.posted_at || "",
        summary: item.content || "",
        author: item.raw_data?.original_author ?? null,
        score: 30,
        tier: "must_read",
        topic_tags: topics,
        is_competitor: false,
        news_category: "curated",
        submitted_by: item.raw_data?.submitted_by || "Team",
      });

      for (const tag of topics) {
        byTopic[tag] = (byTopic[tag] || 0) + 1;
      }
      const src = item.source || "Unknown";
      bySource[src] = (bySource[src] || 0) + 1;
      continue;
    }

    const { score, tags } = scoreArticle(item);

    // Determine news_category
    let news_category: "industry" | "company" | "competitor" = "industry";
    const textLower = `${item.title || ""} ${item.content || ""}`.toLowerCase();
    if (textLower.includes(COMPANY_NAME.toLowerCase())) {
      news_category = "company";
    } else if (tags.some(tag => COMPETITOR_BRAND_NAMES.some(b => b.toLowerCase() === tag.toLowerCase()))) {
      news_category = "competitor";
    }

    articles.push({
      title: item.title || "Untitled",
      url: item.source_url || "",
      source: item.source || "Unknown",
      posted_at: item.posted_at || "",
      summary: item.raw_data?.exa_summary || extractSummary(item.content || ""),
      author: item.raw_data?.author ?? null,
      score,
      tier: tierFromScore(score),
      topic_tags: tags,
      is_competitor: news_category === "competitor",
      news_category,
    });

    for (const tag of tags) {
      byTopic[tag] = (byTopic[tag] || 0) + 1;
    }

    const src = item.source || "Unknown";
    bySource[src] = (bySource[src] || 0) + 1;
  }

  // Curated items first, then sort by score
  articles.sort((a, b) => {
    if (a.news_category === "curated" && b.news_category !== "curated") return -1;
    if (b.news_category === "curated" && a.news_category !== "curated") return 1;
    return b.score - a.score;
  });

  return {
    articles,
    by_topic: byTopic,
    by_source: bySource,
    total: articles.length,
  };
}

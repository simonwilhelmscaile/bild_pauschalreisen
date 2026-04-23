/**
 * Shared utility helpers — ported from data_aggregator.py utility functions.
 */
import type { SocialItem } from "./types";
import {
  BEURER_PRODUCTS, COMPETITOR_PRODUCTS, HEALTH_ONLY_PATTERNS,
  PURCHASE_INTENT_PATTERNS, TROUBLESHOOTING_PATTERNS, USAGE_PATTERNS,
  DEVICE_KEYWORDS, BRAND_NAMES, SOURCE_CATEGORY_MAP, REPORT_RELEVANCE_FLOOR,
  RETAILER_LISTING_DOMAINS,
} from "../constants";

/** Simple Counter class mimicking Python's collections.Counter */
export class Counter<T extends string | number = string> {
  private map = new Map<T, number>();

  increment(key: T, by = 1) {
    this.map.set(key, (this.map.get(key) || 0) + by);
  }

  get(key: T): number {
    return this.map.get(key) || 0;
  }

  set(key: T, val: number) {
    this.map.set(key, val);
  }

  entries(): [T, number][] {
    return [...this.map.entries()];
  }

  /** Return entries sorted by count descending, optionally limited. */
  mostCommon(n?: number): [T, number][] {
    const sorted = [...this.map.entries()].sort((a, b) => b[1] - a[1]);
    return n !== undefined ? sorted.slice(0, n) : sorted;
  }

  values(): number[] {
    return [...this.map.values()];
  }

  total(): number {
    let s = 0;
    for (const v of this.map.values()) s += v;
    return s;
  }

  toRecord(): Record<string, number> {
    const r: Record<string, number> = {};
    for (const [k, v] of this.map.entries()) r[String(k)] = v;
    return r;
  }

  update(other: Counter<T>) {
    for (const [k, v] of other.entries()) this.increment(k, v);
  }
}

export function countField<T extends string>(items: SocialItem[], field: keyof SocialItem): Counter<T> {
  const c = new Counter<T>();
  for (const item of items) {
    const val = item[field];
    if (val != null && typeof val === "string") c.increment(val as unknown as T);
  }
  return c;
}

export function countArrayField<T extends string>(items: SocialItem[], field: keyof SocialItem): Counter<T> {
  const c = new Counter<T>();
  for (const item of items) {
    const arr = item[field] as unknown as string[] | undefined;
    if (Array.isArray(arr)) {
      for (const v of arr) c.increment(v as unknown as T);
    }
  }
  return c;
}

/** Largest-remainder rounding so percentages sum to exactly 100. */
export function roundPercentages(counts: Record<string, number>, total: number): Record<string, number> {
  if (total === 0) return Object.fromEntries(Object.keys(counts).map(k => [k, 0]));
  const raw: Record<string, number> = {};
  for (const [k, v] of Object.entries(counts)) raw[k] = (v / total) * 100;
  const floored: Record<string, number> = {};
  for (const [k, v] of Object.entries(raw)) floored[k] = Math.floor(v);
  const remainders: Record<string, number> = {};
  for (const k of Object.keys(raw)) remainders[k] = raw[k] - floored[k];
  let diff = 100 - Object.values(floored).reduce((a, b) => a + b, 0);
  const sorted = Object.keys(remainders).sort((a, b) => remainders[b] - remainders[a]);
  for (let i = 0; i < diff && i < sorted.length; i++) floored[sorted[i]]++;
  return floored;
}

/** Clean raw quote text for display */
function cleanQuoteText(text: string): string {
  return text
    .replace(/<[^>]*>/g, "")           // strip HTML
    .replace(/[\n\r\t]+/g, " ")        // newlines → space
    .replace(/\s{2,}/g, " ")           // collapse whitespace
    .replace(/^[\s}{>\-|]+/, "")       // strip leading junk
    .replace(/\u2019/g, "'")
    .replace(/[\u201c\u201d]/g, '"')
    .replace(/[\u201e\u201f]/g, '"')
    .trim();
}

/** Extract a meaningful quote of up to max_len chars, breaking at sentence boundaries. */
export function extractRepresentativeQuote(text: string, maxLen = 100): string {
  if (!text) return "";
  text = cleanQuoteText(text);
  if (!text) return "";
  if (text.length <= maxLen) return text;

  // Try to find first complete sentence within maxLen
  const sentenceRe = /[.!?]\s/g;
  let match;
  let lastGoodEnd = -1;
  while ((match = sentenceRe.exec(text.slice(0, maxLen + 1))) !== null) {
    const endPos = match.index + 1;
    if (endPos >= 40) lastGoodEnd = endPos;
  }
  if (lastGoodEnd > 0) return text.slice(0, lastGoodEnd);

  // Try natural break points
  for (const sep of [" \u2013 ", " \u2014 ", " - ", "; ", ", "]) {
    const idx = text.lastIndexOf(sep, maxLen);
    if (idx >= 40) return text.slice(0, idx) + "\u2026";
  }

  // Word boundary truncation
  let truncated = text.slice(0, maxLen);
  const lastSpace = truncated.lastIndexOf(" ");
  if (lastSpace >= 40) truncated = truncated.slice(0, lastSpace);
  return truncated.replace(/[.,;:!?\s]+$/, "") + "\u2026";
}

/** Build a short content preview for display in post lists. */
export function buildContentPreview(item: SocialItem, maxLen = 120): string {
  const source = item.source || "";
  const title = (item.title || "").trim();
  const content = (item.content || "").trim();
  if (!content) return "";

  if (source === "youtube" || source === "youtube_transcript") {
    return extractRepresentativeQuote(content, maxLen);
  }

  if (title && content.toLowerCase().startsWith(title.toLowerCase().slice(0, 30))) {
    return "";
  }

  return extractRepresentativeQuote(content, maxLen);
}

/** Apply relevance floor filter.
 *
 * Item passes if ANY of:
 * - relevance_score is null (not yet classified)
 * - relevance_score >= floor
 * - Has product_mentions
 * - Has _entities
 * - device_relevance_score >= 0.4
 */
export function applyRelevanceFloor(items: SocialItem[], floor = REPORT_RELEVANCE_FLOOR): SocialItem[] {
  return items.filter(item =>
    item.relevance_score == null ||
    (item.relevance_score || 0) >= floor ||
    (item.product_mentions && item.product_mentions.length > 0) ||
    (item._entities && item._entities.length > 0) ||
    (item.device_relevance_score || 0) >= 0.4
  );
}

/** Categorize a question into purchase_intent, troubleshooting, or usage. */
export function categorizeQuestion(item: SocialItem): string {
  const combined = ((item.title || "") + " " + (item.content || "")).toLowerCase();
  const purchase = PURCHASE_INTENT_PATTERNS.filter(p => combined.includes(p)).length;
  const troubleshooting = TROUBLESHOOTING_PATTERNS.filter(p => combined.includes(p)).length;
  const usage = USAGE_PATTERNS.filter(p => combined.includes(p)).length;

  const scores = { purchase_intent: purchase, troubleshooting, usage };
  const max = Object.entries(scores).reduce((a, b) => b[1] > a[1] ? b : a);
  return max[1] > 0 ? max[0] : "usage";
}

/** Map a source name to its display category. */
export function getSourceCategory(source: string): string {
  const lower = source.toLowerCase();
  for (const [category, sources] of Object.entries(SOURCE_CATEGORY_MAP)) {
    if (sources.some(s => lower.includes(s))) return category;
  }
  return "Sonstige";
}

/** Get ISO week number. */
export function getISOWeekNumber(d: Date): number {
  const dt = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  dt.setUTCDate(dt.getUTCDate() + 4 - (dt.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(dt.getUTCFullYear(), 0, 1));
  return Math.ceil((((dt.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}

/** Check if a question is about devices (not just health). */
export function isDeviceQuestion(item: SocialItem): boolean {
  const combined = ((item.title || "") + " " + (item.content || "")).toLowerCase();
  for (const pattern of HEALTH_ONLY_PATTERNS) {
    if (combined.includes(pattern)) return false;
  }
  if (item.product_mentions && item.product_mentions.length > 0) return true;
  const deviceTerms = [
    "gerät", "messgerät", "tens-gerät", "ems-gerät", "manschette",
    "modell", "kaufen", "empfehlung", "vergleich", "sensor",
    "app", "bluetooth", "anzeige", "display", "batterie",
    "blutdruckmessgerät", "blutdruckmesser",
  ];
  return deviceTerms.some(term => combined.includes(term));
}

/** Determine if product mentions are Beurer, competitor, or unknown. */
export function getProductType(productMentions: string[]): string {
  for (const p of productMentions) {
    const upper = p.toUpperCase();
    if (BEURER_PRODUCTS.some(bp => bp.toUpperCase() === upper)) return "beurer";
    if (COMPETITOR_PRODUCTS.some(cp => cp.toUpperCase().includes(upper) || upper.includes(cp.toUpperCase()))) return "competitor";
  }
  return "unknown";
}

/** Check if a question is specifically about a competitor product. */
export function isCompetitorSpecificQuestion(item: SocialItem): boolean {
  const title = (item.title || "").toLowerCase();
  const content = (item.content || "").toLowerCase();
  const combined = title + " " + content;
  const productMentions = item.product_mentions || [];
  const productType = getProductType(productMentions);
  const competitorBrands = ["omron", "withings", "sanitas", "medisana", "braun"];
  const titleMentionsCompetitor = competitorBrands.some(b => title.includes(b));
  const contentMentionsCompetitor = competitorBrands.some(b => content.includes(b));
  const mentionsBeurer = combined.includes("beurer");
  if (mentionsBeurer && (titleMentionsCompetitor || contentMentionsCompetitor)) return false;
  if (titleMentionsCompetitor) return true;
  if (productType === "competitor") return true;
  if (contentMentionsCompetitor && !mentionsBeurer) return true;
  return false;
}

/** Score an item's device relevance (0-100). */
export function scoreDeviceRelevance(item: SocialItem): number {
  let score = 0;
  const combined = ((item.title || "") + " " + (item.content || "")).toLowerCase();
  for (const pattern of HEALTH_ONLY_PATTERNS) {
    if (combined.includes(pattern)) return 0;
  }
  if (item.product_mentions && item.product_mentions.length > 0) score += 50;
  for (const brand of BRAND_NAMES) {
    if (combined.includes(brand)) { score += 30; break; }
  }
  const keywordMatches = DEVICE_KEYWORDS.filter(kw => combined.includes(kw)).length;
  if (keywordMatches > 0) score += Math.min(20, keywordMatches * 5);
  return score;
}

/** Extract engagement count from raw_data based on source. */
export function getEngagementCount(item: SocialItem): number | null {
  const raw = item.raw_data || {};
  const source = item.source || "";
  if (source === "amazon" || source === "amazon.de") return raw.helpful_votes ?? null;
  if (source === "reddit") {
    const s = raw.score || 0;
    const c = raw.num_comments || 0;
    return (s || c) ? s + c : null;
  }
  if (source === "youtube") return raw.likes ?? null;
  if (source === "youtube_transcript") return raw.views ?? raw.likes ?? null;
  if (source === "tiktok" || source === "instagram") return raw.likes ?? raw.plays ?? null;
  return null;
}

/** Get top quality posts with quality gate. */
export function getTopQualityPosts(items: SocialItem[], limit = 20): SocialItem[] {
  const quality = items.filter(item =>
    item.category != null && item.category !== "other" && item.category !== "unclassified" &&
    item.sentiment != null && item.sentiment !== "" &&
    (item.relevance_score || 0) > 0.3
  );
  quality.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
  if (quality.length < 5) {
    const fallback = [...items].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
    return fallback.slice(0, limit);
  }
  return quality.slice(0, limit);
}

/** Suggest a response angle. */
export function suggestResponseAngle(item: SocialItem, questionCategory: string): string {
  if (questionCategory === "purchase_intent") {
    const products = item.product_mentions || [];
    if (products.length > 0) return `Vergleich ${products[0]} Funktionen und Vorteile`;
    return "Passendes Beurer-Modell empfehlen";
  }
  if (questionCategory === "troubleshooting") return "Fehlerbehebungsschritte oder Support-Kontakt";
  return "Verweis auf Bedienungsanleitung oder Tutorial";
}

/** Check if URL belongs to Beurer's own domains. */
export function isBeurerOwn(item: SocialItem): boolean {
  const url = item.source_url || "";
  if (!url) return false;
  try {
    const hostname = new URL(url).hostname.toLowerCase();
    return ["beurer.com", "www.beurer.com", "beurer.de", "www.beurer.de"].includes(hostname);
  } catch { return false; }
}

/** Check if item is a retailer product listing with no user reviews. */
export function isRetailerListing(item: SocialItem): boolean {
  let source = ((item as any)._display_source || item.resolved_source || "").toLowerCase().replace(/^www\./, "");
  if (!source && item.source_url) {
    try {
      source = new URL(item.source_url).hostname.toLowerCase().replace(/^www\./, "");
    } catch { return false; }
  }
  return RETAILER_LISTING_DOMAINS.has(source) && !item.has_answers && !item.answer_count;
}

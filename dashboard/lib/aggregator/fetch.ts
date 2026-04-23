/**
 * Supabase queries with pagination — ported from fetch_items_for_period + _enrich_items_with_related_data.
 *
 * Performance: enrichment queries are parallelized both across types (entities/aspects/answers)
 * and within each type (all batches fire concurrently via Promise.all).
 */
import type { SupabaseClient } from "@supabase/supabase-js";
import type { SocialItem, EntityRow, AspectRow, AnswerRow } from "./types";

const PAGE_SIZE = 1000;
const ENTITY_BATCH = 100;
const ASPECT_BATCH = 100;
const ANSWER_BATCH = 200;

/** Split an array into chunks of the given size. */
function chunk<T>(arr: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size));
  }
  return chunks;
}

/** Fetch social items for a date range with language filter and pagination. */
export async function fetchItemsForRange(
  supabase: SupabaseClient,
  startDate: string,
  endDate: string,
  lang = "de",
  limit = 2000,
): Promise<SocialItem[]> {
  // Build the main items query (paginated)
  const fetchMain = async (): Promise<SocialItem[]> => {
    const items: SocialItem[] = [];
    let offset = 0;
    while (items.length < limit) {
      let query = supabase
        .from("social_items")
        .select("*")
        .gte("posted_at", startDate)
        .lt("posted_at", endDate)
        .order("relevance_score", { ascending: false });

      if (lang && lang !== "all") {
        query = query.or(`language.eq.${lang},language.is.null`);
      }

      const { data, error } = await query.range(offset, offset + PAGE_SIZE - 1);
      if (error) throw new Error(`Supabase fetch error: ${error.message}`);
      const batch = data || [];
      if (batch.length === 0) break;
      items.push(...batch);
      offset += PAGE_SIZE;
      if (batch.length < PAGE_SIZE) break;
    }
    return items;
  };

  // Build the QA items query (wider lookback, has_answers=true)
  // Cap at 60 days to avoid slow queries on wide date ranges (30-day view
  // was producing a 93-day lookback that caused timeouts/failures)
  const periodDays = Math.max(1, Math.round((new Date(endDate).getTime() - new Date(startDate).getTime()) / 86400000));
  const qaLookbackDays = Math.min(60, Math.max(30, periodDays * 3));
  const qaStart = new Date(new Date(endDate).getTime() - qaLookbackDays * 86400000)
    .toISOString().split("T")[0];

  const fetchQA = async (): Promise<SocialItem[]> => {
    const qaItems: SocialItem[] = [];
    let qaOffset = 0;
    while (qaItems.length < 200) {
      let qaQuery = supabase
        .from("social_items")
        .select("*")
        .eq("has_answers", true)
        .gte("posted_at", qaStart)
        .lt("posted_at", endDate)
        .order("relevance_score", { ascending: false });
      if (lang && lang !== "all") {
        qaQuery = qaQuery.or(`language.eq.${lang},language.is.null`);
      }
      const { data, error: qaError } = await qaQuery.range(qaOffset, qaOffset + PAGE_SIZE - 1);
      if (qaError) throw new Error(`Supabase QA fetch error: ${qaError.message}`);
      const batch = data || [];
      if (batch.length === 0) break;
      qaItems.push(...batch);
      qaOffset += PAGE_SIZE;
      if (batch.length < PAGE_SIZE) break;
    }
    return qaItems;
  };

  // Run main + QA fetches in parallel (QA is non-blocking — its failure must not
  // kill the main fetch, especially for 30-day views where qaLookbackDays=93)
  const [mainItems, rawQaItems] = await Promise.all([
    fetchMain(),
    fetchQA().catch(e => {
      console.warn(`QA fetch failed (non-blocking, lookback=${qaLookbackDays}d):`, e);
      return [] as SocialItem[];
    }),
  ]);

  // Dedup QA items against main results
  const existingIds = new Set(mainItems.map(i => i.id).filter(Boolean));
  const items = [...mainItems];
  for (const qi of rawQaItems) {
    if (qi.id && !existingIds.has(qi.id)) {
      existingIds.add(qi.id);
      items.push(qi);
    }
  }

  return items.slice(0, limit + 200); // Allow QA overflow
}

/** Fetch items for the previous period (same duration, immediately before currentStartDate). */
export async function fetchPreviousPeriodItems(
  supabase: SupabaseClient,
  currentStartDate: string,
  currentEndDate: string,
  lang = "de",
): Promise<SocialItem[]> {
  const startMs = new Date(currentStartDate).getTime();
  const endMs = new Date(currentEndDate).getTime();
  const durationMs = endMs - startMs;
  const prevStartDate = new Date(startMs - durationMs).toISOString().split("T")[0];
  const prevEndDate = currentStartDate; // previous period ends where current starts

  return fetchItemsForRange(supabase, prevStartDate, prevEndDate, lang, 2000);
}

/** Batch-fetch entities, aspects, answers and attach to items. */
export async function enrichWithRelatedData(
  supabase: SupabaseClient,
  items: SocialItem[],
): Promise<SocialItem[]> {
  const itemIds = items.map(i => i.id).filter(Boolean) as string[];
  if (itemIds.length === 0) return items;

  // --- Parallel batch fetchers ---

  const fetchEntities = async (): Promise<Record<string, EntityRow[]>> => {
    const map: Record<string, EntityRow[]> = {};
    const batches = chunk(itemIds, ENTITY_BATCH);
    const results = await Promise.all(
      batches.map(batch =>
        supabase
          .from("item_entities")
          .select("social_item_id, entity_id, mention_type, sentiment, confidence, context_snippet, entities(canonical_name, entity_type, category, brand)")
          .in("social_item_id", batch)
      ),
    );
    for (const { data } of results) {
      for (const row of data || []) {
        const sid = row.social_item_id;
        if (!map[sid]) map[sid] = [];
        const normalized = { ...row, entities: Array.isArray(row.entities) ? row.entities[0] : row.entities };
        map[sid].push(normalized as EntityRow);
      }
    }
    return map;
  };

  const fetchAspects = async (): Promise<Record<string, AspectRow[]>> => {
    const map: Record<string, AspectRow[]> = {};
    const batches = chunk(itemIds, ASPECT_BATCH);
    const results = await Promise.all(
      batches.map(batch =>
        supabase
          .from("item_aspects")
          .select("social_item_id, aspect, sentiment, intensity, evidence_snippet")
          .in("social_item_id", batch)
      ),
    );
    for (const { data } of results) {
      for (const row of data || []) {
        const sid = row.social_item_id;
        if (!map[sid]) map[sid] = [];
        map[sid].push(row);
      }
    }
    return map;
  };

  // Single-pass answer fetch: get content directly, derive counts from results
  const fetchAnswers = async (): Promise<{ counts: Record<string, number>; answers: Record<string, AnswerRow[]> }> => {
    const counts: Record<string, number> = {};
    const answers: Record<string, AnswerRow[]> = {};
    const batches = chunk(itemIds, ANSWER_BATCH);
    const results = await Promise.all(
      batches.map(batch =>
        supabase
          .from("social_item_answers")
          .select("social_item_id, content, author, votes, is_accepted, position")
          .in("social_item_id", batch)
          .order("votes", { ascending: false })
          .order("position", { ascending: true })
      ),
    );
    for (const { data } of results) {
      for (const row of data || []) {
        const sid = row.social_item_id;
        counts[sid] = (counts[sid] || 0) + 1;
        if (!answers[sid]) answers[sid] = [];
        if (answers[sid].length < 3) answers[sid].push(row);
      }
    }
    return { counts, answers };
  };

  // --- Run all three enrichment types in parallel ---
  const [entitiesByItem, aspectsByItem, { counts: answerCounts, answers: answersByItem }] = await Promise.all([
    fetchEntities().catch(e => { console.warn("Could not fetch entities:", e); return {} as Record<string, EntityRow[]>; }),
    fetchAspects().catch(e => { console.warn("Could not fetch aspects:", e); return {} as Record<string, AspectRow[]>; }),
    fetchAnswers().catch(e => { console.warn("Could not fetch answers:", e); return { counts: {} as Record<string, number>, answers: {} as Record<string, AnswerRow[]> }; }),
  ]);

  // Attach to items
  for (const item of items) {
    const id = item.id;
    if (!id) continue;
    item._entities = entitiesByItem[id] || [];
    item._aspects = aspectsByItem[id] || [];
    item._answer_count = answerCounts[id] || 0;
    item._top_answers = answersByItem[id] || [];

    // Resolve display source for serper items
    const source = item.source || "";
    if (source === "serper_brand" || source === "serper_discovery") {
      if (item.resolved_source) {
        item._display_source = item.resolved_source;
      } else if (item.source_url) {
        try {
          const hostname = new URL(item.source_url).hostname;
          item._display_source = hostname.replace(/^www\./, "") || source;
        } catch { item._display_source = source; }
      } else {
        item._display_source = source;
      }
    } else {
      item._display_source = source;
    }
  }

  return items;
}

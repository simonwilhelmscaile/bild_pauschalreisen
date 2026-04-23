#!/usr/bin/env bash
# =============================================================================
#  Social Listening Pipeline Runner
#  Starts the FastAPI server, runs the full crawl→backfill→report pipeline
#  for one or all active tenants, then exits.
#
#  Environment variables:
#    TENANT          - (optional) specific tenant slug; empty = all active
#    SUPABASE_URL    - required
#    SUPABASE_KEY    - required
#    GEMINI_API_KEY  - required
#    FIRECRAWL_API_KEY, APIFY_API_TOKEN, SERPER_API_KEY, EXA_API_KEY - optional
# =============================================================================
set -euo pipefail

BASE="http://localhost:8000/api/v1/social-listening"
TENANT_API="http://localhost:8000/api/v1/tenants"
SB_URL="${SUPABASE_URL:?SUPABASE_URL is required}"
SB_KEY="${SUPABASE_KEY:?SUPABASE_KEY is required}"

# ── Start FastAPI server in background ──
echo "Starting FastAPI server..."
python app.py &
SERVER_PID=$!

# Wait for server to be ready
echo "Waiting for server to start..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/v1/social-listening/stats > /dev/null 2>&1; then
    echo "Server is ready!"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "ERROR: Server failed to start within 60 seconds"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
  fi
  sleep 2
done

# ── Cleanup on exit ──
cleanup() {
  echo "Shutting down server..."
  kill $SERVER_PID 2>/dev/null || true
  wait $SERVER_PID 2>/dev/null || true
  echo "Done."
}
trap cleanup EXIT

# ── Helper: update tenant status in Supabase ──
update_status() {
  local slug="$1" status="$2"
  curl -sf -X PATCH \
    "${SB_URL}/rest/v1/tenant_configs?slug=eq.${slug}" \
    -H "apikey: ${SB_KEY}" \
    -H "Authorization: Bearer ${SB_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"status\": \"${status}\"}" || echo "Warning: failed to set status=${status} for ${slug}"
}

# ── Helper: run a crawler ──
crawl() {
  local name="$1" payload="$2" tenant="$3"
  echo "--- Crawling $name ---"
  RESULT=$(curl -sf -X POST "$BASE/crawl?tenant=$tenant" \
    -H "Content-Type: application/json" \
    -d "$payload" 2>&1) && echo "$RESULT" || echo "$name failed"
}

# ── Helper: loop a backfill endpoint until done ──
run_backfill() {
  local name="$1" url="$2" max_loops="${3:-20}"
  local i=0 last_id="" processed=999
  echo "--- Backfill: $name ---"
  while [ $i -lt $max_loops ] && [ $processed -gt 0 ]; do
    i=$((i+1))
    PARAMS="$url"
    [ -n "$last_id" ] && PARAMS="${PARAMS}&after_id=${last_id}"
    RESP=$(curl -sf -X POST "$PARAMS" 2>/dev/null) || { echo "  [$name] failed on loop $i"; break; }
    processed=$(echo "$RESP" | python3 -c "import sys,json; s=json.load(sys.stdin).get('stats',{}); print(s.get('processed', s.get('classified',0)))" 2>/dev/null || echo 0)
    new_last=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stats',{}).get('last_id',''))" 2>/dev/null || echo "")
    echo "  [$name] loop $i: processed=$processed last_id=${new_last:-none}"
    [ -n "$new_last" ] && last_id="$new_last"
  done
  echo "  [$name] done after $i loops"
}

# ── Resolve tenant list ──
TENANT_INPUT="${TENANT:-}"
if [ -n "$TENANT_INPUT" ]; then
  SLUGS="[\"$TENANT_INPUT\"]"
  echo "Running for single tenant: $TENANT_INPUT"
else
  SLUGS=$(curl -sf "$TENANT_API?status=active" | python3 -c "
import sys, json
tenants = json.load(sys.stdin)
slugs = [t['slug'] for t in tenants]
print(json.dumps(slugs))
")
  echo "Running for active tenants: $SLUGS"
fi

# ── Process each tenant ──
echo "$SLUGS" | python3 -c "import sys,json; slugs=json.load(sys.stdin); [print(s) for s in slugs]" | while read -r SLUG; do
  echo ""
  echo "======================================================="
  echo "  TENANT: $SLUG"
  echo "======================================================="
  echo ""
  T="tenant=$SLUG"

  # Mark as processing
  update_status "$SLUG" "processing"

  # ── Fetch tenant config to determine which crawlers to run ──
  TCONF=$(curl -sf "$TENANT_API/$SLUG/config" 2>/dev/null) || TCONF="{}"
  has_source() {
    echo "$TCONF" | python3 -c "import sys,json; cs=json.load(sys.stdin).get('crawler_sources',{}); print('yes' if cs.get('$1',[]) else 'no')" 2>/dev/null || echo "no"
  }

  HAS_FORUMS=$(has_source "forum_urls")
  HAS_REDDIT_SUBS=$(has_source "reddit_subreddits")
  HAS_REDDIT_Q=$(has_source "reddit_search_queries")
  HAS_AMAZON_ASINS=$(has_source "amazon_asins")
  HAS_AMAZON_Q=$(has_source "amazon_search_queries")
  HAS_AMAZON="no"
  [ "$HAS_AMAZON_ASINS" = "yes" ] || [ "$HAS_AMAZON_Q" = "yes" ] && HAS_AMAZON="yes"
  HAS_REDDIT="no"
  [ "$HAS_REDDIT_SUBS" = "yes" ] || [ "$HAS_REDDIT_Q" = "yes" ] && HAS_REDDIT="yes"
  echo "Tenant sources: forums=$HAS_FORUMS reddit=$HAS_REDDIT amazon=$HAS_AMAZON"

  # ══════════════════════════════════════════════════════════
  #  PARALLEL CRAWLERS
  # ══════════════════════════════════════════════════════════

  # Group 1: Firecrawl (sequential pair)
  (
    crawl "gutefrage" '{"crawler":"gutefrage","max_pages":5}' "$SLUG"
    if [ "$HAS_FORUMS" = "yes" ]; then
      crawl "health_forums" '{"crawler":"health_forums","max_pages":3}' "$SLUG"
    else
      echo "--- Skipping health_forums (no forum_urls configured) ---"
    fi
  ) &

  # Group 2: Reddit
  if [ "$HAS_REDDIT" = "yes" ]; then
    crawl "reddit" '{"crawler":"reddit","max_pages":3}' "$SLUG" &
  else
    echo "--- Skipping reddit (no subreddits configured) ---"
  fi

  # Group 3: YouTube
  crawl "youtube" '{"crawler":"youtube","max_pages":2}' "$SLUG" &

  # Group 4: Amazon
  if [ "$HAS_AMAZON" = "yes" ]; then
    crawl "amazon" '{"crawler":"amazon","max_pages":3}' "$SLUG" &
  else
    echo "--- Skipping amazon (no ASINs/queries configured) ---"
  fi

  # Group 5: Serper (sequential pair)
  (
    crawl "serper_discovery" '{"crawler":"serper_discovery","max_pages":15,"deep_crawl":true}' "$SLUG"
    crawl "serper_brand" '{"crawler":"serper_brand","max_pages":12,"deep_crawl":true}' "$SLUG"
  ) &

  # Group 6: Exa news
  if [ -n "${EXA_API_KEY:-}" ]; then
    crawl "exa_news" '{"crawler":"exa_news","max_pages":10}' "$SLUG" &
  else
    echo "--- Skipping exa_news (EXA_API_KEY not set) ---"
  fi

  # Group 7: RSS news
  crawl "rss_news" '{"crawler":"rss_news","max_pages":20,"days_back":7}' "$SLUG" &

  echo "Waiting for all crawlers to complete..."
  wait
  echo "All crawlers finished."

  # ══════════════════════════════════════════════════════════
  #  TIER 0: PARALLEL DETERMINISTIC BACKFILLS
  # ══════════════════════════════════════════════════════════
  BFILL="$BASE/backfill"

  run_backfill "embeddings" "$BFILL/embeddings?batch_size=500&$T" &
  run_backfill "language-detection" "$BFILL/language-detection?batch_size=500&$T" 5 &
  run_backfill "engagement-scores" "$BFILL/engagement-scores?batch_size=500&$T" 5 &
  run_backfill "entities" "$BFILL/entities?batch_size=500&$T" 5 &
  (echo "--- Backfill: sources ---" && curl -sf -X POST "$BFILL/sources?$T" || echo "sources failed") &
  run_backfill "dates" "$BFILL/dates?batch_size=500&$T" 5 &
  run_backfill "normalize-medications" "$BFILL/normalize-medications?batch_size=500&$T" 5 &

  echo "Waiting for Tier 0 backfills..."
  wait
  echo "Tier 0 backfills complete."

  # ══════════════════════════════════════════════════════════
  #  TIER 1: SEQUENTIAL LLM BACKFILLS (Gemini rate-limited)
  # ══════════════════════════════════════════════════════════
  run_backfill "classifications" "$BFILL/classifications?batch_size=50&$T"
  sleep 5
  run_backfill "journey-stages" "$BFILL/journey-stages?batch_size=50&$T"
  sleep 5
  run_backfill "deep-insights" "$BFILL/deep-insights?batch_size=50&$T"
  sleep 5

  # ══════════════════════════════════════════════════════════
  #  TIER 2: POST-LLM STEPS
  # ══════════════════════════════════════════════════════════
  run_backfill "entity-sentiment" "$BFILL/entity-sentiment?batch_size=100&$T"
  run_backfill "answers" "$BFILL/answers?batch_size=50&$T"

  # ── Generate weekly report ──
  echo "--- Generating weekly report ---"
  curl -sf -X POST \
    "$BASE/report/weekly?format=full&$T" \
    -H "Content-Type: application/json" | python3 -c "
import sys, json
data = json.load(sys.stdin)
period = data.get('period', {})
print(f'Report generated: {period.get(\"start\", \"?\")} to {period.get(\"end\", \"?\")}')
print(f'DB record ID: {data.get(\"report_id\", \"not saved\")}')
" || echo "report generation failed"

  # ── Mark tenant as active ──
  update_status "$SLUG" "active"

  echo ""
  echo "=== Completed tenant: $SLUG ==="
  echo ""
done

# ── Final verification ──
echo "=== Pipeline complete ==="
curl -sf "http://localhost:8000/api/v1/social-listening/stats" | python3 -m json.tool || true

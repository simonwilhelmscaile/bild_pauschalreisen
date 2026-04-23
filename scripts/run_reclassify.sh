#!/bin/bash
# Full re-classification script with pagination
# Processes all 2,428 items through 3 stages:
# 1. Classifications (emotion/intent/intensity) - force=true with after_id pagination
# 2. Journey Stages - NULL items only, loop until done
# 3. Deep Insights + Aspects - force=true with after_id pagination

BASE="http://localhost:8000/api/v1/social-listening/backfill"

echo "=== Full Re-Classification Script ==="
echo "Started at $(date)"
echo ""

# 1. Classifications with pagination
echo "=== 1/3: Classifications (emotion/intent/intensity) ==="
TOTAL_PROCESSED=0
TOTAL_FAILED=0
LAST_ID=""
BATCH=0
while true; do
    BATCH=$((BATCH + 1))
    URL="${BASE}/classifications?batch_size=50&force=true"
    if [ -n "$LAST_ID" ]; then
        URL="${URL}&after_id=${LAST_ID}"
    fi
    RESULT=$(curl -sf -X POST "$URL" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "  ERROR: curl failed on batch $BATCH"
        break
    fi
    PROCESSED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats']['processed'])" 2>/dev/null)
    FAILED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats']['failed'])" 2>/dev/null)
    NEW_LAST_ID=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats'].get('last_id','') or '')" 2>/dev/null)

    if [ "$PROCESSED" = "0" ] || [ -z "$PROCESSED" ]; then
        echo "  Batch $BATCH: no more items to process"
        break
    fi

    TOTAL_PROCESSED=$((TOTAL_PROCESSED + PROCESSED))
    TOTAL_FAILED=$((TOTAL_FAILED + FAILED))
    LAST_ID="$NEW_LAST_ID"
    echo "  Batch $BATCH: processed=$PROCESSED, failed=$FAILED, total=$TOTAL_PROCESSED"
done
echo "Classifications DONE: $TOTAL_PROCESSED processed, $TOTAL_FAILED failed"
echo ""

# 2. Journey stages (processes NULL items, loop until done)
echo "=== 2/3: Journey Stages ==="
TOTAL_PROCESSED=0
TOTAL_FAILED=0
BATCH=0
while true; do
    BATCH=$((BATCH + 1))
    RESULT=$(curl -sf -X POST "${BASE}/journey-stages?batch_size=50" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "  ERROR: curl failed on batch $BATCH"
        break
    fi
    PROCESSED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats']['processed'])" 2>/dev/null)
    FAILED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats']['failed'])" 2>/dev/null)

    if [ "$PROCESSED" = "0" ] || [ -z "$PROCESSED" ]; then
        echo "  Batch $BATCH: no more items to process"
        break
    fi

    TOTAL_PROCESSED=$((TOTAL_PROCESSED + PROCESSED))
    TOTAL_FAILED=$((TOTAL_FAILED + FAILED))
    echo "  Batch $BATCH: processed=$PROCESSED, failed=$FAILED, total=$TOTAL_PROCESSED"
done
echo "Journey Stages DONE: $TOTAL_PROCESSED processed, $TOTAL_FAILED failed"
echo ""

# 3. Deep insights with pagination
echo "=== 3/3: Deep Insights + Aspects ==="
TOTAL_PROCESSED=0
TOTAL_FAILED=0
TOTAL_ASPECTS=0
LAST_ID=""
BATCH=0
while true; do
    BATCH=$((BATCH + 1))
    URL="${BASE}/deep-insights?batch_size=50&force=true"
    if [ -n "$LAST_ID" ]; then
        URL="${URL}&after_id=${LAST_ID}"
    fi
    RESULT=$(curl -sf -X POST "$URL" 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo "  ERROR: curl failed on batch $BATCH"
        break
    fi
    PROCESSED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats']['processed'])" 2>/dev/null)
    FAILED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats']['failed'])" 2>/dev/null)
    ASPECTS=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats'].get('aspects_saved',0))" 2>/dev/null)
    NEW_LAST_ID=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); print(d['stats'].get('last_id','') or '')" 2>/dev/null)

    if [ "$PROCESSED" = "0" ] || [ -z "$PROCESSED" ]; then
        echo "  Batch $BATCH: no more items to process"
        break
    fi

    TOTAL_PROCESSED=$((TOTAL_PROCESSED + PROCESSED))
    TOTAL_FAILED=$((TOTAL_FAILED + FAILED))
    TOTAL_ASPECTS=$((TOTAL_ASPECTS + ASPECTS))
    LAST_ID="$NEW_LAST_ID"
    echo "  Batch $BATCH: processed=$PROCESSED, failed=$FAILED, aspects=$ASPECTS, total=$TOTAL_PROCESSED"
done
echo "Deep Insights DONE: $TOTAL_PROCESSED processed, $TOTAL_FAILED failed, $TOTAL_ASPECTS aspects"
echo ""

echo "=== ALL DONE at $(date) ==="

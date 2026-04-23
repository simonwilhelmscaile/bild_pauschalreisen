"""Run answer backfills for all Q&A-capable sources."""
import urllib.request
import json
import time

BASE = "http://127.0.0.1:8000/api/v1/social-listening"

sources = [
    ("gutefrage", 20),
    ("reddit", 20),
    ("diabetes_forum", 10),
    ("onmeda", 10),
]

for source, batch in sources:
    print(f"\n--- Backfilling {source} (batch={batch}) ---", flush=True)
    try:
        url = f"{BASE}/backfill/answers?batch_size={batch}&source={source}"
        req = urllib.request.Request(url, method="POST", data=b"", headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=600)
        result = json.loads(r.read().decode())
        print(json.dumps(result, indent=2), flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)
    time.sleep(1)

print("\n=== All answer backfills complete ===", flush=True)

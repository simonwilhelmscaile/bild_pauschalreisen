"""Railway startup script with error logging."""
import os
import sys
import traceback

port = int(os.environ.get("PORT", 8000))
print(f"[startup] Python {sys.version}", flush=True)
print(f"[startup] PORT={port}", flush=True)
print(f"[startup] CWD={os.getcwd()}", flush=True)
print(f"[startup] Files: {os.listdir('.')[:20]}", flush=True)

try:
    print("[startup] Importing app...", flush=True)
    from app import app
    print("[startup] App imported OK", flush=True)
except Exception as e:
    print(f"[startup] IMPORT FAILED: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    print(f"[startup] Starting uvicorn on 0.0.0.0:{port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)

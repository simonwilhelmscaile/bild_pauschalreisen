#!/usr/bin/env python
"""Development server with auto-reload.

Usage: python dev.py

Automatically reloads when code changes - no manual restart needed.
"""
import subprocess
import sys


def kill_server_on_port(port: int = 8000) -> None:
    """Kill any existing server on the specified port (Windows)."""
    if sys.platform != "win32":
        return

    try:
        # Find PID using netstat
        result = subprocess.run(
            f"netstat -ano | findstr :{port} | findstr LISTENING",
            shell=True,
            capture_output=True,
            text=True
        )

        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit():
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                        print(f"Killed existing server (PID {pid})")
    except Exception:
        pass  # Ignore errors, server will fail to bind if port is in use


if __name__ == "__main__":
    # Kill any existing server on port 8000
    kill_server_on_port(8000)

    # Start uvicorn with reload
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app:app",
        "--reload",
        "--port", "8000",
        "--reload-dir", ".",
        "--reload-exclude", "__pycache__,*.pyc,.git"
    ])

"""
Quick start runner for Home Credit LAP AI Voice Agent.
Usage:
  python run.py
  python run.py --dev
"""

import sys
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    reload = "--dev" in sys.argv or os.environ.get("DEBUG", "false").lower() == "true"

    print("=" * 65)
    print("🚀 Home Credit LAP AI Voice Agent — Starting Server")
    print(f"📡 Host: http://localhost:{port}")
    print(f"📖 Docs: http://localhost:{port}/docs")
    print("🎯 Target Repo: REDDIPALLIPHANIKOUSHIK/Voice_Agent_Design")
    print("=" * 65)

    uvicorn.run("src.main:app", host=host, port=port, reload=reload)

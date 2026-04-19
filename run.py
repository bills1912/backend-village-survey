#!/usr/bin/env python3
"""
run.py – Jalankan server FastAPI dengan uvicorn
Usage:
    python run.py              # default port 8000
    python run.py --port 9000  # port custom
    python run.py --reload     # auto-reload saat development
"""
import uvicorn
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    print(f"🚀  Menjalankan server di http://{args.host}:{args.port}")
    print(f"📄  Dokumentasi API: http://localhost:{args.port}/docs\n")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )

#!/usr/bin/env python3
"""
Turium AI Knowledge Inbox - One-Click Launcher
Runs the FastAPI production server with automatic reloading, SQLite vector store, and interactive React UI.
"""

import sys
import uvicorn
from app.core.config import get_settings


def main():
    settings = get_settings()
    print("=" * 65)
    print(f"  🚀  {settings.APP_NAME} v{settings.VERSION}")
    print("=" * 65)
    print(f"  • Web UI:        http://{settings.HOST}:{settings.PORT}")
    print(f"  • Swagger Docs:  http://{settings.HOST}:{settings.PORT}/docs")
    print(f"  • Health Check:  http://{settings.HOST}:{settings.PORT}/health")
    print(f"  • Active AI:     {settings.resolve_provider().upper()}")
    print(f"  • Database:      {settings.DATABASE_PATH}")
    print("=" * 65)
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )


if __name__ == "__main__":
    main()

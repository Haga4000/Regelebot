import os

# Set env vars BEFORE any imports from the project happen
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("TMDB_API_KEY", "test-tmdb")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("BOT_NAME", "Regelebot")

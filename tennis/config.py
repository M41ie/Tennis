from __future__ import annotations

from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv is optional; ignore if not installed
    pass

# Repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
# Default database location
DB_FILE = REPO_ROOT / "tennis.db"


def get_database_url() -> str:
    """Return the configured database connection string."""
    return os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE}")


def get_redis_url() -> str | None:
    """Return the Redis connection string if set."""
    return os.getenv("REDIS_URL")


def get_cache_ttl() -> int:
    """Return the cache TTL in seconds."""
    return int(os.getenv("CACHE_TTL", "300"))


def get_wechat_appid() -> str:
    """Return the WeChat mini program AppID."""
    return os.getenv("WECHAT_APPID", "")


def get_wechat_secret() -> str:
    """Return the WeChat mini program secret."""
    return os.getenv("WECHAT_SECRET", "")

__all__ = [
    "DB_FILE",
    "get_database_url",
    "get_redis_url",
    "get_cache_ttl",
    "get_wechat_appid",
    "get_wechat_secret",
]

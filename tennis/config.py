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


class BaseConfig:
    """Base settings shared across environments."""

    DB_USER = os.getenv("DB_USER", "tennis_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "3112565tennis")
    DB_HOST = os.getenv("DB_HOST", "localhost")


class ProductionConfig(BaseConfig):
    DB_NAME = "tennis_prod"


class TrialConfig(BaseConfig):
    DB_NAME = "tennis_trial"


class DevelopmentConfig(BaseConfig):
    DB_NAME = "tennis_dev"


_CONFIGS = {
    "production": ProductionConfig,
    "trial": TrialConfig,
    "development": DevelopmentConfig,
}

# Current active configuration determined by the ``APP_ENV`` environment
# variable. Defaults to development.
APP_ENV = os.getenv("APP_ENV", "development")
ActiveConfig = _CONFIGS.get(APP_ENV, DevelopmentConfig)


def get_database_url() -> str:
    """Return the configured database connection string."""
    return (
        f"postgresql://{ActiveConfig.DB_USER}:{ActiveConfig.DB_PASSWORD}"
        f"@{ActiveConfig.DB_HOST}/{ActiveConfig.DB_NAME}"
    )


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

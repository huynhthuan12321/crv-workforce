from typing import Any
from source.config import settings


def cors_settings() -> dict[str, Any]:
    """
    CORS settings for FastAPI.
    Restricts access to Telegram WebApp domains only.
    """
    allowed_origins = [
        f"https://{settings.app.domain}",
        "http://localhost:3000",
        "https://web.telegram.org",
        "https://webk.telegram.org",
        "https://webz.telegram.org",
    ]

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Authorization", "Content-Type"],
        "max_age": 600,
    }

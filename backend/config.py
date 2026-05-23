"""Onyx backend configuration."""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    host: str = os.getenv("ONYX_HOST", "0.0.0.0")
    port: int = int(os.getenv("ONYX_PORT", "8000"))
    debug: bool = os.getenv("ONYX_DEBUG", "false").lower() == "true"

    # DeepSeek backend
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
    )
    deepseek_model: str = os.getenv(
        "ONYX_MODEL", "deepseek-v4-flash"
    )

    # Database
    database_url: str = os.getenv(
        "ONYX_DATABASE_URL", "sqlite+aiosqlite:///data/onyx.db"
    )

    # Auth — simple API key for cli clients
    api_key: str = os.getenv("ONYX_API_KEY", "change-me")

    # Model mapping: public name -> actual DeepSeek model
    # When rotation is enabled, this is populated dynamically from model_rotator.
    @property
    def model_map(self) -> dict:
        try:
            from .model_rotator import get_catalog
            return get_catalog().model_map
        except Exception:
            pass
        return _FALLBACK_MODEL_MAP

    @property
    def public_models(self) -> list[dict]:
        """Return exposed model list for /v1/models.
        Strips internal fields like _backend."""
        try:
            from .model_rotator import get_catalog
            return [{k: v for k, v in m.items() if not k.startswith("_")}
                    for m in get_catalog().models]
        except Exception:
            pass
        return [
            {
                "id": name,
                "object": "model",
                "created": 1700000000,
                "owned_by": "onyx",
            }
            for name in _FALLBACK_MODEL_MAP
        ]

    def deepseek_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }

    def resolve_model(self, model: str) -> str:
        """Resolve public model name to actual DeepSeek model.
        Unknown names pass through unchanged."""
        return self.model_map.get(model, model)


_FALLBACK_MODEL_MAP = {
    "onyx-flash": "deepseek-v4-flash",
    "onyx-sonnet": "deepseek-v4-flash",
    "onyx-pro": "deepseek-v4-pro",
    "onyx-opus": "deepseek-v4-pro",
}


settings = Settings()

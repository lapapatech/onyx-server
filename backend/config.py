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
        "ONYX_MODEL", "deepseek-chat"
    )

    # Database
    database_url: str = os.getenv(
        "ONYX_DATABASE_URL", "sqlite+aiosqlite:///data/onyx.db"
    )

    # Model mapping: public name -> actual DeepSeek model
    model_map: dict = field(default_factory=lambda: {
        "onyx-premium": "deepseek-chat",
        "onyx-flash": "deepseek-v4-flash",
    })

    # Auth — simple API key for cli clients
    api_key: str = os.getenv("ONYX_API_KEY", "change-me")

    def deepseek_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json",
        }

    def resolve_model(self, model: str) -> str:
        """Resolve public model name to actual DeepSeek model.
        Unknown names pass through unchanged."""
        return self.model_map.get(model, model)

    @property
    def public_models(self) -> list[dict]:
        """Return exposed model list for /v1/models."""
        return [
            {
                "id": name,
                "object": "model",
                "created": 1700000000,
                "owned_by": "onyx",
            }
            for name in self.model_map
        ]


settings = Settings()

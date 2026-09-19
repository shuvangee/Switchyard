"""Centralized model registry and provider factory.

This is the one place model names/config live — no other module should
hard-code a model or provider name.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.time import utcnow
from app.models.model_config import ModelConfigORM
from app.providers.base import Provider
from app.providers.gemini_provider import GeminiProvider
from app.providers.mock import MockProvider
from app.providers.openai_provider import OpenAIProvider


@dataclass(frozen=True)
class ModelConfig:
    id: str
    provider: str
    model_id: str
    display_name: str
    enabled: bool
    input_cost_per_1k: float
    output_cost_per_1k: float
    capabilities: dict[str, Any] = field(default_factory=dict)


def get_model_registry(settings: Settings | None = None) -> list[ModelConfig]:
    """Build the list of configured models.

    A function rather than a module-level constant so enabling/disabling
    real providers reflects current settings (useful in tests, which
    construct their own Settings rather than relying on process env vars).
    """
    settings = settings or get_settings()
    return [
        ModelConfig(
            id="mock-fast-v1",
            provider="mock",
            model_id="mock-fast-v1",
            display_name="Mock Fast",
            enabled=True,
            input_cost_per_1k=0.0001,
            output_cost_per_1k=0.0002,
            capabilities={"notes": "Simulated small/cheap model: basic skill level, low latency."},
        ),
        ModelConfig(
            id="mock-accurate-v1",
            provider="mock",
            model_id="mock-accurate-v1",
            display_name="Mock Accurate",
            enabled=True,
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.006,
            capabilities={"notes": "Simulated large/capable model: higher latency and cost."},
        ),
        ModelConfig(
            id="mock-flaky-v1",
            provider="mock",
            model_id="mock-flaky-v1",
            display_name="Mock Flaky",
            enabled=True,
            input_cost_per_1k=0.0002,
            output_cost_per_1k=0.0004,
            capabilities={"notes": "Simulated unreliable endpoint: ~25% simulated error rate."},
        ),
        ModelConfig(
            id="openai-gpt-4o-mini",
            provider="openai",
            model_id="gpt-4o-mini",
            display_name="GPT-4o mini",
            enabled=bool(settings.openai_api_key),
            input_cost_per_1k=0.00015,
            output_cost_per_1k=0.0006,
            capabilities={"notes": "Real provider; disabled unless OPENAI_API_KEY is set."},
        ),
        ModelConfig(
            id="gemini-2.0-flash",
            provider="gemini",
            model_id="gemini-2.0-flash",
            display_name="Gemini 2.0 Flash",
            enabled=bool(settings.google_api_key),
            input_cost_per_1k=0.0001,
            output_cost_per_1k=0.0004,
            capabilities={
                "notes": (
                    "Real provider; disabled unless GOOGLE_API_KEY is set. "
                    "Pricing is Google's published per-1M-token rate converted to "
                    "per-1k and not yet verified against a real invoice — treat as "
                    "provisional until a real experiment run confirms actual cost."
                )
            },
        ),
    ]


def get_provider(name: str, settings: Settings | None = None) -> Provider:
    settings = settings or get_settings()
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIProvider(settings.openai_api_key)
    if name == "gemini":
        return GeminiProvider(settings.google_api_key)
    raise ValueError(f"unknown provider: {name!r}")


def sync_model_configs(session: Session, settings: Settings | None = None) -> None:
    """Upsert the code-defined model registry into the model_configs table."""
    now = utcnow()
    for model in get_model_registry(settings):
        existing = session.get(ModelConfigORM, model.id)
        if existing is None:
            existing = ModelConfigORM(id=model.id)
            session.add(existing)
        existing.provider = model.provider
        existing.model_id = model.model_id
        existing.display_name = model.display_name
        existing.enabled = model.enabled
        existing.input_cost_per_1k = model.input_cost_per_1k
        existing.output_cost_per_1k = model.output_cost_per_1k
        existing.capabilities = model.capabilities
        existing.updated_at = now
    session.commit()

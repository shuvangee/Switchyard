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
from app.providers.grok_provider import GrokProvider
from app.providers.groq_provider import GroqProvider
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
            id="gemini-3.6-flash",
            provider="gemini",
            model_id="gemini-3.6-flash",
            display_name="Gemini 3.6 Flash",
            enabled=bool(settings.google_api_key),
            input_cost_per_1k=0.00075,
            output_cost_per_1k=0.00375,
            capabilities={
                "notes": (
                    "Real provider; disabled unless GOOGLE_API_KEY is set. "
                    "Two prior model ids (gemini-2.0-flash, gemini-2.5-flash) "
                    "both 404'd against the live API — Google's own error message "
                    "for the second named gemini-3.6-flash as the current "
                    "replacement, which is what's registered here. Pricing is "
                    "sourced from third-party aggregators (ai.google.dev is "
                    "blocked by this environment's network policy) — introductory "
                    "rate through 2026-12-31, rising after. Treat as provisional "
                    "until verified against a real invoice or Google's own pricing "
                    "page directly. Thinking tokens (this is a reasoning-capable "
                    "model) bill at the output rate and count against "
                    "maxOutputTokens, confirmed 2026-09-21 to actually truncate "
                    "responses at the adapter's original 512-token cap (raised to "
                    "2048) — see docs/case-study/FAILURES_AND_LESSONS.md. Free "
                    "tier is capped at 20 requests/day for this model "
                    "(GenerateRequestsPerDayPerProjectPerModel-FreeTier), a hard "
                    "daily quota, not just a per-minute rate limit."
                )
            },
        ),
        ModelConfig(
            id="gemini-3.1-pro-preview",
            provider="gemini",
            model_id="gemini-3.1-pro-preview",
            display_name="Gemini 3.1 Pro (preview)",
            enabled=bool(settings.google_api_key),
            input_cost_per_1k=0.002,
            output_cost_per_1k=0.012,
            capabilities={
                "notes": (
                    "Real provider; disabled unless GOOGLE_API_KEY is set (the "
                    "same key already used for gemini-3.6-flash). Added "
                    "2026-09-23 as the V2.6 routing-opportunity experiment's "
                    "proposed 'stronger model' - a genuinely different capability "
                    "tier from both gemini-3.6-flash and the Groq gpt-oss models "
                    "(Pro vs Flash/open-weight), reusing GeminiProvider as-is: no "
                    "new provider code, no new key. Model id and pricing sourced "
                    "from third-party aggregators and Google's own docs pages "
                    "found via search (ai.google.dev is blocked by this "
                    "environment's network policy, so the id was not directly "
                    "verified against a live call) — UNVERIFIED until a real "
                    "call confirms it, same caution as grok-4.1-fast before its "
                    "first real run. Under 200K context: $2.00/$12.00 per 1M "
                    "input/output tokens (rising above that threshold). "
                    "Reasoning-capable like gemini-3.6-flash - the same "
                    "thinking-token-inflates-cost risk documented for that model "
                    "applies here too; the adapter's 2048-token output cap bounds "
                    "the worst case. NO LIVE CALL MADE YET - registered only, "
                    "pending explicit cost approval for the actual experiment."
                )
            },
        ),
        ModelConfig(
            id="grok-4.1-fast",
            provider="grok",
            model_id="grok-4.1-fast",
            display_name="Grok 4.1 Fast",
            enabled=bool(settings.xai_api_key),
            input_cost_per_1k=0.0002,
            output_cost_per_1k=0.0005,
            capabilities={
                "notes": (
                    "Real provider; disabled unless XAI_API_KEY is set. "
                    "Model id and pricing are UNVERIFIED — sourced from "
                    "third-party aggregators (docs.x.ai was not directly "
                    "checked), which disagreed with each other on xAI's "
                    "current flagship model name. Given how often "
                    "gemini-*'s model ids 404'd this same week, treat this "
                    "id as a best guess pending a live API call the moment "
                    "a real XAI_API_KEY exists — do not trust it as fact "
                    "until then."
                )
            },
        ),
        ModelConfig(
            id="groq-gpt-oss-20b",
            provider="groq",
            model_id="openai/gpt-oss-20b",
            display_name="Groq GPT-OSS 20B",
            enabled=bool(settings.groq_api_key),
            input_cost_per_1k=0.000075,
            output_cost_per_1k=0.0003,
            capabilities={
                "notes": (
                    "Real provider; disabled unless GROQ_API_KEY is set. "
                    "Model id and pricing sourced from Groq's own docs URL "
                    "structure (console.groq.com/docs/model/openai/gpt-oss-20b, "
                    "found via search) plus third-party aggregators that agree "
                    "with each other — direct fetch of console.groq.com is "
                    "blocked by this environment's network policy, so neither "
                    "was verified against a live page load. Free tier: 30 RPM, "
                    "1,000 RPD, 8K TPM, 200K TPD (same caveat)."
                )
            },
        ),
        ModelConfig(
            id="groq-gpt-oss-120b",
            provider="groq",
            model_id="openai/gpt-oss-120b",
            display_name="Groq GPT-OSS 120B",
            enabled=bool(settings.groq_api_key),
            input_cost_per_1k=0.00015,
            output_cost_per_1k=0.0006,
            capabilities={
                "notes": (
                    "Real provider; disabled unless GROQ_API_KEY is set. "
                    "Model id and pricing sourced from Groq's own docs URL "
                    "structure (console.groq.com/docs/model/openai/gpt-oss-120b, "
                    "found via search) plus third-party aggregators that agree "
                    "with each other — direct fetch of console.groq.com is "
                    "blocked by this environment's network policy, so neither "
                    "was verified against a live page load. Free tier: 30 RPM, "
                    "1,000 RPD, 8K TPM, 200K TPD (same caveat)."
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
    if name == "grok":
        return GrokProvider(settings.xai_api_key)
    if name == "groq":
        return GroqProvider(settings.groq_api_key)
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

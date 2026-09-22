"""Cost estimation from configured per-1k-token pricing.

Pricing lives on the model config, not the provider, since it is not
something a provider API returns — it is set by whoever configures the
model registry (see app/providers/registry.py).
"""


def estimate_cost_usd(
    *,
    input_cost_per_1k: float,
    output_cost_per_1k: float,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    """Return None when token usage is unknown rather than guessing."""
    if input_tokens is None or output_tokens is None:
        return None
    return (input_tokens / 1000) * input_cost_per_1k + (output_tokens / 1000) * output_cost_per_1k

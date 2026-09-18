import pytest

from app.providers.pricing import estimate_cost_usd


def test_cost_computed_from_tokens():
    cost = estimate_cost_usd(
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.006,
        input_tokens=1000,
        output_tokens=500,
    )
    assert cost == pytest.approx(0.003 + 0.003)


def test_cost_none_when_tokens_unknown():
    assert (
        estimate_cost_usd(
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.006,
            input_tokens=None,
            output_tokens=100,
        )
        is None
    )
    assert (
        estimate_cost_usd(
            input_cost_per_1k=0.003,
            output_cost_per_1k=0.006,
            input_tokens=100,
            output_tokens=None,
        )
        is None
    )

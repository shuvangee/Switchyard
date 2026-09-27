from app.experiments.results_reader import evaluation_coverage, model_benchmark_performance


def test_groq_20b_matches_the_published_headline_numbers():
    """Regression check against the actual committed groq-gpt-oss-
    expansion.json - these exact numbers are already published in
    docs/case-study/EXPERIMENTS.md and METRICS.md (2026-09-27); this
    guards against silent drift between the two."""
    result = model_benchmark_performance("groq-gpt-oss-20b")
    assert result["n_graded"] == 92
    assert result["n_correct"] == 81
    assert result["accuracy"] == 81 / 92
    assert round(result["avg_latency_ms"]) == 646
    assert round(result["nominal_cost_usd"], 6) == 0.008108


def test_groq_120b_matches_the_published_headline_numbers():
    result = model_benchmark_performance("groq-gpt-oss-120b")
    assert result["n_graded"] == 92
    assert result["n_correct"] == 83
    assert result["accuracy"] == 83 / 92
    assert round(result["avg_latency_ms"]) == 927
    assert round(result["nominal_cost_usd"], 6) == 0.015020


def test_model_with_no_executions_returns_none():
    assert model_benchmark_performance("mock-fast-v1") is None
    assert model_benchmark_performance("not-a-real-model") is None


def test_evaluation_coverage_matches_the_published_breakdown():
    coverage = evaluation_coverage()
    assert coverage["total_tasks"] == 104
    assert coverage["auto_graded"] == 92
    assert coverage["manual_only"] == 12
    assert coverage["ungraded"] == 0
    assert coverage["automated_pct"] == 92 / 104


def test_evaluation_coverage_by_category_sums_to_totals():
    coverage = evaluation_coverage()
    by_category = coverage["by_category"]
    assert sum(c["total"] for c in by_category.values()) == coverage["total_tasks"]
    assert sum(c["auto_graded"] for c in by_category.values()) == coverage["auto_graded"]
    assert sum(c["manual_only"] for c in by_category.values()) == coverage["manual_only"]
    assert sum(c["ungraded"] for c in by_category.values()) == coverage["ungraded"]
    for counts in by_category.values():
        assert counts["auto_graded"] + counts["manual_only"] + counts["ungraded"] == counts["total"]


def test_evaluation_coverage_debugging_and_summarization_have_manual_only_tasks():
    """The real, documented reasons these stay manual (debugging-007's
    genuine ambiguity, summarization's attribution/paraphrase tasks) are
    the product's own honest limitations, not a bug to hide."""
    coverage = evaluation_coverage()
    assert coverage["by_category"]["debugging"]["manual_only"] == 1
    assert coverage["by_category"]["summarization"]["manual_only"] == 7
    assert coverage["by_category"]["reasoning"]["manual_only"] == 4

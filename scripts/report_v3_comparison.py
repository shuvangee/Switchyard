"""Renders the V3 training manifest's baseline comparison as a readable
markdown table — no charts, just the numbers, per CLAUDE.md's design
rules. Reads the artifact already produced by
`python -m app.routing.learned.train`; makes no new calls or predictions.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "backend/app/routing/learned/artifacts/learned-v1.manifest.json"
OUTPUT_PATH = REPO_ROOT / "experiments/results/learned-v1-comparison.md"

_LABELS = {
    "learned-v1": "learned-v1 (this V3 model)",
    "always-cheapest": "always-cheapest (mock-fast-v1)",
    "always-strongest": "always-strongest (mock-accurate-v1)",
    "v2": "V1/V2 rule-based router",
    "random": "random (expected value)",
}


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    comparison = manifest["comparison"]

    lines = [
        "# V3 routing strategy comparison",
        "",
        f"Generated from `{MANIFEST_PATH.relative_to(REPO_ROOT)}`, trained "
        f"{manifest['trained_at']}. Evaluated via "
        f"{manifest['evaluation_method']} against the {manifest['n_training_rows']} "
        "real (mock + one real-provider) task outcomes that exist in this repo — "
        "not simulated, not projected. See docs/case-study/EXPERIMENTS.md "
        "(2026-09-22) for the full interpretation.",
        "",
        "| Strategy | Accuracy (evaluable) | Avg cost/task | Total cost | Unevaluable |",
        "|---|---:|---:|---:|---:|",
    ]
    for entry in comparison:
        label = _LABELS.get(entry["strategy"], entry["strategy"])
        acc = entry["accuracy_on_evaluable"]
        acc_str = f"{acc:.1%}" if acc is not None else "n/a"
        avg_cost = entry["avg_cost_usd_on_evaluable"]
        avg_cost_str = f"${avg_cost:.6f}" if avg_cost is not None else "n/a"
        total_cost_str = f"${entry['total_cost_usd_on_evaluable']:.6f}"
        lines.append(
            f"| {label} | {acc_str} | {avg_cost_str} | {total_cost_str} | "
            f"{entry['n_unknown_outcome']}/{entry['n_rows']} |"
        )

    lines += [
        "",
        "**Unevaluable** = the strategy picked a model with no recorded outcome for "
        "that task (never guessed as correct/incorrect — reported as unknown).",
        "",
        "## Headline finding",
        "",
        "`learned-v1` is dominated by `always-cheapest` — worse accuracy at higher "
        "cost. It also loses to random selection and to the V1/V2 rule-based "
        "router. At n=24 training rows, this decision tree has not learned a "
        "useful pattern; it has fit noise. Not recommended for real use. Full "
        "root-cause discussion in `docs/case-study/EXPERIMENTS.md`.",
    ]

    OUTPUT_PATH.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Static guard for Rule 12 positive-int budget/count bool boundaries."""

from __future__ import annotations

import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]

SURFACE_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "support/recording/contracts.py": (
        "def require_positive_int(",
        "if isinstance(value, bool):",
        "bool is not admitted",
    ),
    "support/operator/auto_repair_replay.py": (
        "from support.recording.contracts import require_positive_int",
        "return require_positive_int(value, label)",
    ),
    "support/operator/route_materialization.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "return require_positive_int(value, label)",
    ),
    "support/operator/assembly.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "require_positive_int(\n            count,\n            \"back() count\",",
        "require_positive_int(\n        budget,\n        \"reroute() budget\",",
        "require_positive_int(\n                    budget,\n                    f\"closure policy target_ref budget {target_ref}\",",
    ),
    "support/operator/composition_route_policy.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "require_positive_int(raw_value, f\"{source_label} node_reroute_budgets value\"",
        "require_positive_int(\n            budget,\n            \"reroute defaults default_node_reroute_budget\",",
        "require_positive_int(\n                raw_budget,\n                f\"composition node_reroute_budget {brick_ref}\",",
    ),
    "support/operator/plan_expansion.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "require_positive_int(value, f\"expansion_node_budgets.{key}\"",
    ),
    "support/operator/run_chat_session.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "require_positive_int(\n            attempt_index,\n            \"attempt_index\",",
    ),
    "support/operator/walker_frontier_driver.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "return require_positive_int(raw_value, \"fanout_dispatch_pool_size\")",
    ),
    "support/recording/claims_carry_budget.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "return require_positive_int(value, label)",
    ),
    "support/recording/step_outputs.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "attempt_index = require_positive_int(attempt_index, \"attempt_index\", allow_decimal_text=False)",
    ),
}

MUTATION_PROBES: dict[str, tuple[str, str]] = {
    "support/recording/contracts.py": (
        "if isinstance(value, bool):",
        "if False and isinstance(value, bool):",
    ),
    "support/operator/auto_repair_replay.py": (
        "return require_positive_int(value, label)",
        "if isinstance(value, int) and value > 0:\n        return value",
    ),
    "support/operator/route_materialization.py": (
        "return require_positive_int(value, label)",
        "if isinstance(value, int) and value > 0:\n        return value",
    ),
    "support/operator/assembly.py": (
        "require_positive_int(\n            count,\n            \"back() count\",",
        "legacy_positive_int(\n            count,\n            \"back() count\",",
    ),
    "support/operator/composition_route_policy.py": (
        "require_positive_int(\n                raw_budget,\n                f\"composition node_reroute_budget {brick_ref}\",",
        "legacy_positive_int(\n                raw_budget,\n                f\"composition node_reroute_budget {brick_ref}\",",
    ),
    "support/operator/plan_expansion.py": (
        "require_positive_int(value, f\"expansion_node_budgets.{key}\"",
        "legacy_positive_int(value, f\"expansion_node_budgets.{key}\"",
    ),
    "support/operator/run_chat_session.py": (
        "require_positive_int(\n            attempt_index,\n            \"attempt_index\",",
        "legacy_positive_int(\n            attempt_index,\n            \"attempt_index\",",
    ),
    "support/operator/walker_frontier_driver.py": (
        "return require_positive_int(raw_value, \"fanout_dispatch_pool_size\")",
        "return int(raw_value)",
    ),
    "support/recording/claims_carry_budget.py": (
        "return require_positive_int(value, label)",
        "if isinstance(value, int) and value > 0:\n        return value",
    ),
    "support/recording/step_outputs.py": (
        "attempt_index = require_positive_int(attempt_index, \"attempt_index\", allow_decimal_text=False)",
        "if attempt_index <= 0:\n        raise ValueError(\"attempt_index must be positive\")",
    ),
}


def _read_live_sources() -> dict[str, str]:
    return {
        relpath: (REPO / relpath).read_text(encoding="utf-8")
        for relpath in SURFACE_EXPECTATIONS
    }


def _violations(sources: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for relpath, expected_texts in SURFACE_EXPECTATIONS.items():
        text = sources.get(relpath, "")
        if not text:
            problems.append(f"{relpath}: missing source")
            continue
        for expected in expected_texts:
            if expected not in text:
                problems.append(f"{relpath}: missing bool-boundary guard text: {expected!r}")
    return problems


def _mutation_probe_violations(sources: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for relpath, (needle, replacement) in MUTATION_PROBES.items():
        text = sources[relpath]
        if needle not in text:
            problems.append(f"{relpath}: mutation fixture source text not found")
            continue
        mutated = dict(sources)
        mutated[relpath] = text.replace(needle, replacement, 1)
        if not _violations(mutated):
            problems.append(f"{relpath}: mutation fixture did not produce rc!=0")
    return problems


def main() -> int:
    sources = _read_live_sources()
    problems = _violations(sources)
    problems.extend(_mutation_probe_violations(sources))
    if problems:
        for problem in problems:
            print(problem)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

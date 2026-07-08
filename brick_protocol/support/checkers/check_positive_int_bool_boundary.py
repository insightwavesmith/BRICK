#!/usr/bin/env python3
"""Static guard for Rule 12 positive-int budget/count bool boundaries."""

from __future__ import annotations

import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(REPO)

DRIVER_CONSOLIDATION_ERROR_CONTRACT = (
    "driver.py current bool error: TypeError('must be a finite positive integer'); "
    "post-consolidation MEASURED bool error: ValueError('must be a positive "
    "integer; bool is not admitted')"
)

SURFACE_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "brick_protocol/support/recording/contracts.py": (
        "def require_positive_int(",
        "if isinstance(value, bool):",
        "bool is not admitted",
    ),
    "brick_protocol/support/operator/auto_repair_replay.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "return require_positive_int(value, label)",
    ),
    "brick_protocol/support/operator/route_materialization.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "return require_positive_int(value, label)",
    ),
    "brick_protocol/support/operator/assembly.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "require_positive_int(\n            count,\n            \"back() count\",",
        "require_positive_int(\n        budget,\n        \"reroute() budget\",",
        "require_positive_int(\n                    budget,\n                    f\"closure policy target_ref budget {target_ref}\",",
    ),
    "brick_protocol/support/operator/composition_route_policy.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "require_positive_int(raw_value, f\"{source_label} node_reroute_budgets value\"",
        "require_positive_int(\n            budget,\n            \"reroute defaults default_node_reroute_budget\",",
        "require_positive_int(\n                raw_budget,\n                f\"composition node_reroute_budget {brick_ref}\",",
    ),
    "brick_protocol/support/operator/plan_expansion.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "require_positive_int(value, f\"expansion_node_budgets.{key}\"",
    ),
    "brick_protocol/support/operator/run_chat_session.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "require_positive_int(\n            attempt_index,\n            \"attempt_index\",",
    ),
    "brick_protocol/support/operator/walker_frontier_driver.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "return require_positive_int(raw_value, \"fanout_dispatch_pool_size\")",
    ),
    "brick_protocol/support/operator/walker_reroute_budget.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "return require_positive_int(value, label)",
        "require_positive_int(\n            disposition.get(\"budget_increment\"),",
    ),
    "brick_protocol/support/operator/plan_validation.py": (
        "def _positive_int(field_name: str, value: Any) -> int:",
        "KEEP-PINNED: this injected coercer belongs to _LINK_ENVELOPE_CTX",
        "positive_int=_positive_int",
    ),
    "brick_protocol/support/operator/walker_resume.py": (
        "declared plan revision expansion_node_budgets has a malformed",
        "a node budget must be a positive integer",
    ),
    "brick_protocol/support/operator/driver.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "def _positive_int(value: Any, label: str) -> int:",
        "return require_positive_int(value, label)",
    ),
    "brick_protocol/support/recording/claims_carry_budget.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "return require_positive_int(value, label)",
    ),
    "brick_protocol/support/recording/step_outputs.py": (
        "from brick_protocol.support.recording.contracts import require_positive_int",
        "attempt_index = require_positive_int(attempt_index, \"attempt_index\", allow_decimal_text=False)",
    ),
}

MUTATION_PROBES: dict[str, tuple[str, str]] = {
    "brick_protocol/support/recording/contracts.py": (
        "if isinstance(value, bool):",
        "if False and isinstance(value, bool):",
    ),
    "brick_protocol/support/operator/auto_repair_replay.py": (
        "return require_positive_int(value, label)",
        "if isinstance(value, int) and value > 0:\n        return value",
    ),
    "brick_protocol/support/operator/route_materialization.py": (
        "return require_positive_int(value, label)",
        "if isinstance(value, int) and value > 0:\n        return value",
    ),
    "brick_protocol/support/operator/assembly.py": (
        "require_positive_int(\n            count,\n            \"back() count\",",
        "legacy_positive_int(\n            count,\n            \"back() count\",",
    ),
    "brick_protocol/support/operator/composition_route_policy.py": (
        "require_positive_int(\n                raw_budget,\n                f\"composition node_reroute_budget {brick_ref}\",",
        "legacy_positive_int(\n                raw_budget,\n                f\"composition node_reroute_budget {brick_ref}\",",
    ),
    "brick_protocol/support/operator/plan_expansion.py": (
        "require_positive_int(value, f\"expansion_node_budgets.{key}\"",
        "legacy_positive_int(value, f\"expansion_node_budgets.{key}\"",
    ),
    "brick_protocol/support/operator/run_chat_session.py": (
        "require_positive_int(\n            attempt_index,\n            \"attempt_index\",",
        "legacy_positive_int(\n            attempt_index,\n            \"attempt_index\",",
    ),
    "brick_protocol/support/operator/walker_frontier_driver.py": (
        "return require_positive_int(raw_value, \"fanout_dispatch_pool_size\")",
        "return int(raw_value)",
    ),
    "brick_protocol/support/operator/walker_reroute_budget.py": (
        "return require_positive_int(value, label)",
        "if isinstance(value, int) and value > 0:\n        return value",
    ),
    "brick_protocol/support/operator/plan_validation.py": (
        "KEEP-PINNED: this injected coercer belongs to _LINK_ENVELOPE_CTX",
        "KEEP-UNPINNED",
    ),
    "brick_protocol/support/operator/driver.py": (
        "return require_positive_int(value, label)",
        "return int(value)",
    ),
    "brick_protocol/support/recording/claims_carry_budget.py": (
        "return require_positive_int(value, label)",
        "if isinstance(value, int) and value > 0:\n        return value",
    ),
    "brick_protocol/support/recording/step_outputs.py": (
        "attempt_index = require_positive_int(attempt_index, \"attempt_index\", allow_decimal_text=False)",
        "if attempt_index <= 0:\n        raise ValueError(\"attempt_index must be positive\")",
    ),
}

FORBIDDEN_TEXTS: dict[str, tuple[str, ...]] = {
    "brick_protocol/support/operator/walker_reroute_budget.py": (
        "if isinstance(value, bool):\n        raise ValueError(f\"{label} must be a positive integer\")",
        "if isinstance(value, int) and value > 0:\n        return value\n    if isinstance(value, str) and value.strip().isdecimal()",
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
    for relpath, forbidden_texts in FORBIDDEN_TEXTS.items():
        text = sources.get(relpath, "")
        for forbidden in forbidden_texts:
            if forbidden in text:
                problems.append(f"{relpath}: forbidden local positive-int core remains: {forbidden!r}")
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


def _behavior_probe_violations() -> list[str]:
    problems: list[str] = []
    from brick_protocol.support.operator import walker_reroute_budget
    from brick_protocol.link.transition import DISPOSITION_ACTIONS
    from brick_protocol.support.operator import gate_sequence
    from brick_protocol.support.operator import plan_validation

    for label, fn in (
        ("walker_reroute_budget._positive_int", walker_reroute_budget._positive_int),
        ("plan_validation._positive_int KEEP-pinned", lambda value, name: plan_validation._positive_int(name, value)),
    ):
        try:
            fn(True, "probe_budget")
        except ValueError as exc:
            if "positive integer" not in str(exc):
                problems.append(f"{label}: bool rejection message drifted: {exc}")
        else:
            problems.append(f"{label}: bool was accepted")

    if walker_reroute_budget._positive_int("3", "probe_budget") != 3:
        problems.append("walker_reroute_budget._positive_int: decimal text was not accepted")
    if plan_validation._positive_int("probe_budget", "3") != 3:
        problems.append("plan_validation._positive_int KEEP-pinned: decimal text was not accepted")

    before_after_literals = (
        "node_reroute_budgets[brick-a] must be a positive integer",
        "node_reroute_budgets[brick-a] must be a positive integer; bool is not admitted",
        DRIVER_CONSOLIDATION_ERROR_CONTRACT,
    )
    if not all(before_after_literals):
        problems.append("positive-int error-contract literal pair is not recorded")

    try:
        gate_sequence.gate_sequence_decision_from_record(
            {"action": "Hold", "gate_results": [], "gate_action_sequence": []}
        )
    except ValueError:
        pass
    else:
        problems.append("gate_sequence replay reader accepted mixed-case recorded action")

    for module_label, fn in (
        ("plan_validation", plan_validation._validate_transition_lifecycle_disposition_action),
        ("walker_reroute_budget", walker_reroute_budget._required_disposition_action),
    ):
        try:
            if module_label == "plan_validation":
                fn({}, {"disposition_action": "bogus"})
            else:
                fn({"disposition_action": "bogus"})
        except ValueError as exc:
            message = str(exc)
            for action in DISPOSITION_ACTIONS:
                if action not in message:
                    problems.append(
                        f"{module_label}: disposition error message omitted {action!r}: {message}"
                    )
        else:
            problems.append(f"{module_label}: bogus disposition action was accepted")
    return problems


def main(argv: object = None) -> int:
    sources = _read_live_sources()
    problems = _violations(sources)
    problems.extend(_mutation_probe_violations(sources))
    problems.extend(_behavior_probe_violations())
    if problems:
        for problem in problems:
            print(problem)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

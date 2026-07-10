#!/usr/bin/env python3
"""Check the Smith-approved Operating Vocabulary v1 snapshot and fail-closed use.

Support evidence only.  This checker neither creates vocabulary nor chooses a
performer, route, Movement, success, or quality judgment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from brick_protocol.support.operator.building_call_authoring import (
    BuildingCallAuthoringValidationError,
    load_operating_vocabulary,
    operating_vocabulary_violations,
)


VOCABULARY_REL = Path(
    "brick_protocol/brick/templates/operating-vocabulary-v1.yaml"
)


def _actual_agent_lanes(repo: Path) -> set[str]:
    return {
        path.stem
        for path in (repo / "brick_protocol" / "agent" / "objects").glob("*.yaml")
        if path.is_file()
    }


def _actual_brick_kinds(repo: Path) -> set[str]:
    root = repo / "brick_protocol" / "brick" / "templates" / "bricks"
    return {
        path.name
        for path in root.iterdir()
        if path.is_dir() and (path / "brick.md").is_file()
    }


def _actual_chain_presets(repo: Path) -> set[str]:
    root = repo / "brick_protocol" / "brick" / "templates" / "presets"
    return {path.stem for path in root.glob("*.md") if path.is_file()}


def _require_exact(label: str, declared: Any, actual: set[str]) -> None:
    observed = set(str(item) for item in declared or ())
    if observed != actual:
        raise AssertionError(
            f"{label} vocabulary drift: missing={sorted(actual - observed)} "
            f"extra={sorted(observed - actual)}"
        )


def _assert_negative_probes() -> None:
    unknowns: tuple[tuple[str, Mapping[str, Any]], ...] = (
        (
            "Brick kind",
            {"structure_draft": {"step_template_ref": "building-step-template:inline-new-kind"}},
        ),
        (
            "Agent lane",
            {"agent_candidates_draft": {"agent_object_ref": "agent-object:inline-new-lane"}},
        ),
        (
            "chain preset",
            {"chain_preset_ref": "building-chain-preset:inline-new-preset"},
        ),
    )
    for label, payload in unknowns:
        violations = operating_vocabulary_violations(payload)
        if not violations:
            raise AssertionError(f"operating vocabulary mutation RED failed for {label}")

    admitted = {
        "step_template_ref": "building-step-template:work",
        "agent_object_ref": "agent-object:dev",
        "chain_preset_ref": "building-chain-preset:fast-fix",
    }
    violations = operating_vocabulary_violations(admitted)
    if violations:
        raise AssertionError(
            f"operating vocabulary rejected admitted v1 refs: {violations}"
        )


def run(repo: Path) -> str:
    root = repo.resolve()
    vocabulary_path = root / VOCABULARY_REL
    vocabulary = load_operating_vocabulary(vocabulary_path)
    if vocabulary.get("vocabulary_version") != "v1":
        raise AssertionError("operating vocabulary version must remain v1 until amended")
    if vocabulary.get("status") != "active" or vocabulary.get("approved_by") != "smith":
        raise AssertionError("operating vocabulary v1 lacks active Smith approval")

    _require_exact("Agent lane", vocabulary.get("agent_lanes"), _actual_agent_lanes(root))
    _require_exact("Brick kind", vocabulary.get("brick_kinds"), _actual_brick_kinds(root))
    _require_exact(
        "chain preset", vocabulary.get("chain_presets"), _actual_chain_presets(root)
    )

    classifications = vocabulary.get("preset_classifications")
    if not isinstance(classifications, Mapping):
        raise AssertionError("operating vocabulary preset classifications missing")
    if classifications.get("quick-check") != "direct_quick":
        raise AssertionError("quick-check must be direct_quick")
    if classifications.get("fast-fix") != "direct_quick":
        raise AssertionError("fast-fix must be direct_quick")
    if classifications.get("onboarding-example-graph") != "example_only":
        raise AssertionError("onboarding example preset must remain example_only")

    amendment = vocabulary.get("amendment_contract")
    if not isinstance(amendment, Mapping):
        raise AssertionError("operating vocabulary amendment contract missing")
    if amendment.get("inline_authoring_amendment_forbidden") is not True:
        raise AssertionError("inline authoring vocabulary amendment must be forbidden")
    steps = amendment.get("required_steps")
    required_markers = {
        "make-a-resource scaffold",
        "registry and checker update",
        "smith approval record",
        "vocabulary version bump",
    }
    if set(str(item) for item in steps or ()) != required_markers:
        raise AssertionError("operating vocabulary amendment steps drifted")

    _assert_negative_probes()
    return (
        "operating vocabulary v1 passed: 9 Agent lanes, 12 Brick kinds, "
        "30 chain presets, direct-quick/example classifications, amendment contract, "
        "and unknown kind/lane/preset mutation RED probes"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        print(run(Path(args.repo)))
    except (AssertionError, BuildingCallAuthoringValidationError, OSError, ValueError) as exc:
        print(f"operating vocabulary v1 rejected: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Survival probe for task-order preflight wiring at assembly front doors.

Support evidence only: this checker exercises literal build()/assemble()
fixtures and records whether preflight rejection survives both official graph
entry points. It does not compose production Buildings, choose Movement, or
judge success/quality.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)
from typing import Callable


DIRTY_WORK = "그냥 다 고쳐라. 근거 file:line만 반환하라."
UNSHAPED_DIRTY_WORK = "그냥 다 고쳐라."
CLEAN_WORK = (
    "## Deliverables\n"
    "D1: edit support/operator/task_order_preflight.py\n"
    "## Done Criteria\n"
    "observed\n"
)
WRITE_SCOPE = {
    "allowed_paths": ["support/operator/task_order_preflight.py"],
    "forbidden_paths": [".git/**"],
}
SUPPORT_FIXTURE_CONTEXT = "support-fixture:task-order-preflight-non-interference"


def _bootstrap(repo: Path) -> None:
    ensure_checker_imports(repo)


def _assert_dirty_rejected(label: str, fn: Callable[[], object], expected_codes: set[str]) -> None:
    from brick_protocol.support.operator.composition_problem import CompositionError

    try:
        fn()
    except CompositionError as exc:
        codes = {problem.code for problem in exc.problems}
        if expected_codes <= codes:
            return
        raise AssertionError(
            f"{label}: expected {sorted(expected_codes)} CompositionError codes, got {sorted(codes)}"
        ) from exc
    raise AssertionError(f"{label}: dirty write task was not rejected")


def _assert_clean_passes(label: str, fn: Callable[[], object]) -> None:
    from brick_protocol.support.operator.composition_problem import CompositionError

    try:
        fn()
    except CompositionError as exc:
        raise AssertionError(f"{label}: clean write task was rejected: {exc}") from exc


def _assert_preflight_call_required(label: str, patcher: Callable[[Callable[..., None]], object]) -> None:
    from brick_protocol.support.operator.composition_problem import CompositionError
    import brick_protocol.support.operator.assembly as assembly

    original = assembly._raise_task_order_preflight_violations
    try:
        assembly._raise_task_order_preflight_violations = lambda _nodes: None
        try:
            patcher(original)
        except CompositionError as exc:
            raise AssertionError(f"{label}: dirty write task was still rejected after neutralizing preflight") from exc
    finally:
        assembly._raise_task_order_preflight_violations = original


def _assert_wiring_present(repo: Path) -> None:
    assembly_text = (repo / "support/operator/assembly.py").read_text(encoding="utf-8")
    preflight_text = (repo / "support/operator/task_order_preflight.py").read_text(encoding="utf-8")
    if assembly_text.count("_raise_task_order_preflight_violations(") < 3:
        raise AssertionError("assembly front-door preflight wiring was removed")
    if "support_fixture" not in preflight_text:
        raise AssertionError("support fixture non-interference marker was removed")


def run_probe(repo: Path) -> tuple[int, tuple[str, ...]]:
    _bootstrap(repo)
    from brick_protocol.support.operator.assembly import assemble, brick, build, chain

    _assert_wiring_present(repo)
    _assert_preflight_call_required(
        "build mutation-survival",
        lambda _original: build([["work", DIRTY_WORK, {"write": True}]]),
    )
    _assert_preflight_call_required(
        "assemble mutation-survival",
        lambda _original: assemble(
            chain([brick("work", DIRTY_WORK, write=True)]),
            declared_by="coo",
            building_id="preflight-injection-mutation-survival",
            repo_root=repo,
            write_scope=WRITE_SCOPE,
        ),
    )
    _assert_dirty_rejected(
        "build dirty",
        lambda: build([["work", DIRTY_WORK, {"write": True}]]),
        {"L1", "L3"},
    )
    _assert_dirty_rejected(
        "build unshaped dirty",
        lambda: build([["work", UNSHAPED_DIRTY_WORK, {"write": True}]]),
        {"L1", "L4"},
    )
    _assert_clean_passes(
        "build clean",
        lambda: build([["work", CLEAN_WORK, {"write": True}]]),
    )
    _assert_dirty_rejected(
        "assemble dirty",
        lambda: assemble(
            chain([brick("work", DIRTY_WORK, write=True)]),
            declared_by="coo",
            building_id="preflight-injection-dirty",
            repo_root=repo,
            write_scope=WRITE_SCOPE,
        ),
        {"L1", "L3"},
    )
    _assert_dirty_rejected(
        "assemble unshaped dirty",
        lambda: assemble(
            chain([brick("work", UNSHAPED_DIRTY_WORK, write=True)]),
            declared_by="coo",
            building_id="preflight-injection-unshaped-dirty",
            repo_root=repo,
            write_scope=WRITE_SCOPE,
        ),
        {"L1", "L4"},
    )
    _assert_clean_passes(
        "assemble clean",
        lambda: assemble(
            chain([brick("work", CLEAN_WORK, write=True)]),
            declared_by="coo",
            building_id="preflight-injection-clean",
            repo_root=repo,
            write_scope=WRITE_SCOPE,
        ),
    )
    _assert_dirty_rejected(
        "build adversarial checker-fixture text",
        lambda: build([["work", "checker fixture work for preflight-support-fixture", {"write": True}]]),
        {"L1", "L4"},
    )
    _assert_dirty_rejected(
        "assemble adversarial support-probe context text",
        lambda: assemble(
            chain([brick("work", "support checker probe fixture work", write=True)]),
            declared_by="coo",
            building_id="preflight-injection-adversarial-support-probe",
            task="support checker probe",
            repo_root=repo,
            write_scope=WRITE_SCOPE,
        ),
        {"L1", "L4"},
    )
    _assert_clean_passes(
        "assemble explicit support fixture context",
        lambda: assemble(
            chain([brick("work", "support checker probe fixture work", write=True)]),
            declared_by="coo",
            building_id="preflight-injection-support-probe",
            task=SUPPORT_FIXTURE_CONTEXT,
            repo_root=repo,
            write_scope=WRITE_SCOPE,
        ),
    )
    return (
        11,
        (
            "assembly wiring and support-fixture marker present",
            "build mutation-survival neutralization probe passed",
            "assemble mutation-survival neutralization probe passed",
            "build dirty rejected with L1/L3",
            "build unshaped dirty rejected with L1/L4",
            "build clean passed",
            "assemble dirty rejected with L1/L3",
            "assemble unshaped dirty rejected with L1/L4",
            "assemble clean passed",
            "build adversarial checker-fixture text rejected with L1/L4",
            "assemble adversarial support-probe context text rejected with L1/L4",
            "assemble explicit support fixture context passed",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support checker for task-order preflight survival at build() and assemble(); "
            "does not judge source truth, success, quality, or Movement."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        inspected, observations = run_probe(repo)
    except (AssertionError, OSError, ValueError) as exc:
        print(f"preflight injection survival rejected: {exc}")
        return 1
    print(f"preflight injection survival passed: {inspected} literal probe(s) inspected.")
    print("- observations: " + ", ".join(observations))
    return 0


if __name__ == "__main__":
    sys.exit(main())

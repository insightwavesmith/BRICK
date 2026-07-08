"""deliverable_crosscheck completion-gate consumer check.

Support checker mechanics only: this observes closure return evidence shape
against the Brick-owned closure template rule. It authors no Link gate row,
chooses no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.checkers.lib.yaml_subset import KernelResult, ProfileError

CHECK_ID = "deliverable_crosscheck_gate"
_IMPLEMENTED_STATUSES_WITHOUT_GAP = {"implemented", "not_applicable_read_only"}
_REQUIRED_TEMPLATE_RULE = (
    "an implementation deliverable row with empty diff_artifact_refs must be "
    "accompanied by transition_concern_evidence (implementation_gap), never by "
    "a complete-style return."
)
_LEDGER_CONSUMER_TEXT = (
    "Consumed by brick_protocol/support/checkers/lib/deliverable_crosscheck_gate_check.py "
    "kernel check deliverable_crosscheck_gate; runtime Link completion-gate "
    "placement remains outside this non-walker slice."
)


def run_deliverable_crosscheck_gate(repo: Path) -> KernelResult:
    """Pin complete-style closure returns against deliverable_crosscheck gaps."""

    _assert_contract_anchors(repo)

    red_complete_with_unimplemented = {
        "observed_evidence": ["observation:red-complete-unimplemented"],
        "narrowly_proven": [],
        "not_proven": [],
        "remaining_delta": [],
        "parent_goal_delta_status": {"open_delta_refs": []},
        "next_target_candidates": [],
        "deferred_smith_review_queue": [],
        "deliverable_crosscheck": [
            {
                "deliverable_ref": "D1",
                "implementation_status": "not_implemented",
                "diff_artifact_refs": [],
                "evidence_refs": ["observation:red-d1"],
            }
        ],
    }
    red_complete_with_empty_diff = {
        "observed_evidence": ["observation:red-complete-empty-diff"],
        "narrowly_proven": [],
        "not_proven": [],
        "remaining_delta": [],
        "parent_goal_delta_status": {"open_delta_refs": []},
        "next_target_candidates": [],
        "deferred_smith_review_queue": [],
        "deliverable_crosscheck": [
            {
                "deliverable_ref": "D2",
                "implementation_status": "implemented",
                "diff_artifact_refs": [],
                "evidence_refs": ["observation:red-d2"],
            }
        ],
    }
    valid_completed_vessel = {
        "observed_evidence": ["observation:valid-complete"],
        "narrowly_proven": ["D1 has diff artifact refs"],
        "not_proven": [],
        "remaining_delta": [],
        "parent_goal_delta_status": {"closed_delta_refs": ["D1"]},
        "next_target_candidates": [],
        "deferred_smith_review_queue": [],
        "deliverable_crosscheck": [
            {
                "deliverable_ref": "D1",
                "implementation_status": "implemented",
                "diff_artifact_refs": ["brick_protocol/support/checkers/lib/example.py:10"],
                "evidence_refs": ["observation:valid-d1"],
            },
            {
                "deliverable_ref": "D2",
                "implementation_status": "not_applicable_read_only",
                "diff_artifact_refs": [],
                "evidence_refs": ["observation:valid-read-only"],
            },
        ],
    }
    valid_gap_vessel = {
        "observed_evidence": ["observation:valid-gap"],
        "narrowly_proven": [],
        "not_proven": ["D3 implementation remains open"],
        "remaining_delta": ["D3"],
        "parent_goal_delta_status": {"open_delta_refs": ["D3"]},
        "next_target_candidates": ["brick-followup-work"],
        "deferred_smith_review_queue": [],
        "transition_concern_evidence": {
            "concern_kind": "implementation_gap",
            "reason_refs": ["observation:valid-gap-d3"],
            "related_boundary_refs": ["brick-followup-work"],
        },
        "deliverable_crosscheck": [
            {
                "deliverable_ref": "D3",
                "implementation_status": "partial",
                "diff_artifact_refs": [],
                "evidence_refs": ["observation:valid-gap-row"],
            }
        ],
    }

    _assert_rejects(red_complete_with_unimplemented, "not_implemented complete-style row")
    _assert_rejects(red_complete_with_empty_diff, "implemented row without diff refs")
    _assert_accepts(valid_completed_vessel, "valid completed vessel")
    _assert_accepts(valid_gap_vessel, "valid implementation_gap vessel")

    return KernelResult(
        check_id=CHECK_ID,
        inspected=6,
        output=(
            "deliverable_crosscheck_gate passed: closure template rule and "
            "enforcement-ledger consumer coordinates inspected; RED complete-style "
            "unimplemented/empty-diff fixtures rejected; valid completed and "
            "implementation_gap vessels accepted."
        ),
    )


def validate_deliverable_crosscheck_return(returned: Mapping[str, Any]) -> list[str]:
    """Return support-observation violations for complete-style crosscheck gaps."""

    rows = returned.get("deliverable_crosscheck")
    if rows is None:
        return []
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return ["deliverable_crosscheck must be a list of per-deliverable rows"]

    has_implementation_gap = _has_implementation_gap(returned.get("transition_concern_evidence"))
    violations: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            violations.append(f"deliverable_crosscheck[{index}] is not a mapping")
            continue
        status = row.get("implementation_status")
        diff_refs = row.get("diff_artifact_refs")
        diff_ref_count = (
            len(diff_refs)
            if isinstance(diff_refs, Sequence) and not isinstance(diff_refs, (str, bytes))
            else 0
        )
        has_gap = status not in _IMPLEMENTED_STATUSES_WITHOUT_GAP or (
            status == "implemented" and diff_ref_count == 0
        )
        if has_gap and not has_implementation_gap:
            deliverable_ref = row.get("deliverable_ref", f"index:{index}")
            violations.append(
                f"deliverable_crosscheck row {deliverable_ref!r} is complete-style "
                "without implementation_gap transition_concern_evidence"
            )
    return violations


def _has_implementation_gap(concern: Any) -> bool:
    return isinstance(concern, Mapping) and concern.get("concern_kind") == "implementation_gap"


def _assert_rejects(returned: Mapping[str, Any], label: str) -> None:
    violations = validate_deliverable_crosscheck_return(returned)
    if not violations:
        raise ProfileError(f"{CHECK_ID} RED fixture did not reject: {label}")


def _assert_accepts(returned: Mapping[str, Any], label: str) -> None:
    violations = validate_deliverable_crosscheck_return(returned)
    if violations:
        raise ProfileError(f"{CHECK_ID} valid fixture rejected {label}: {violations!r}")


def _assert_contract_anchors(repo: Path) -> None:
    closure_return = repo / "brick_protocol" / "brick" / "templates" / "bricks" / "closure" / "return.yaml"
    closure_text = closure_return.read_text(encoding="utf-8")
    if _REQUIRED_TEMPLATE_RULE not in closure_text:
        raise ProfileError(
            f"{CHECK_ID} closure return rule anchor missing from {closure_return}"
        )
    ledger = repo / "brick_protocol" / "brick" / "templates" / "enforcement-ledger.yaml"
    ledger_text = ledger.read_text(encoding="utf-8")
    if ledger_text.count(_LEDGER_CONSUMER_TEXT) != 2:
        raise ProfileError(
            f"{CHECK_ID} enforcement ledger must name this consumer exactly twice"
        )


def _run_building_operator_driver0_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "brick_protocol/support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "building_operator_driver0",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_deliverable_crosscheck_gate(repo: Path) -> KernelResult:"
    poisoned = "def run_deliverable_crosscheck_gate_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError(f"{CHECK_ID} mutation probe could not find entrypoint")

    backup = tempfile.NamedTemporaryFile(
        prefix=".deliverable-crosscheck-gate-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_building_operator_driver0_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                f"{CHECK_ID} mutation probe did not turn building_operator_driver0 RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_building_operator_driver0_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            f"{CHECK_ID} mutation probe restored source but profile stayed RED:\n{excerpt}"
        )

    return [
        "deliverable_crosscheck_gate mutation RED probe passed: disabling the "
        "run_deliverable_crosscheck_gate entrypoint made building_operator_driver0 "
        "exit non-zero, then restoring the temp-backed self file returned it to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker for closure deliverable_crosscheck gaps."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's run_deliverable_crosscheck_gate "
            "entrypoint, assert building_operator_driver0 exits RED, restore, "
            "then assert building_operator_driver0 GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = (
            probe_mutation_red(repo)
            if args.probe_mutation_red
            else [run_deliverable_crosscheck_gate(repo).output]
        )
    except ProfileError as exc:
        print("deliverable_crosscheck_gate check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

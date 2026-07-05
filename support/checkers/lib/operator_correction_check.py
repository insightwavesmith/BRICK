"""Operator-correction behavioral profile runner.

Support-evidence checker only. It writes temp fixtures and verifies that
correction rows re-present a measured frontier without creating Movement,
success, or quality authority.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import ProfileError, require_mapping, rule_items


def run_operator_correction_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "operator_correction_case")
    if not items:
        return 0

    from brick_protocol.support.operator.frontier_observation import (
        observe_building_frontier,
    )
    from brick_protocol.support.recording.operator_correction import (
        ERROR_GROUNDLESS_CORRECTION,
        ERROR_RETURN_FORGING_CORRECTION,
        author_correction_observation,
        measure_correction_tail,
    )

    count = 0
    for item in items:
        mapping = require_mapping(item, "operator_correction_case item")
        scenario = str(mapping.get("scenario") or "").strip()
        with tempfile.TemporaryDirectory(prefix="bp-operator-correction-") as tmp:
            tmp_root = Path(tmp)
            if scenario == "returnless-death":
                root = tmp_root / "returnless-death"
                _write_returnless_death_fixture(root)
                before = observe_building_frontier(root, repo_root=repo)
                if before.get("frontier_kind") != "evidence_incomplete":
                    raise ProfileError(
                        "operator_correction_case returnless-death expected "
                        f"evidence_incomplete before correction, got {before.get('frontier_kind')!r}"
                    )
                measured = measure_correction_tail(root, repo_root=repo)
                result = author_correction_observation(
                    root,
                    author_ref="coo:checker",
                    grounds_refs=["observation:returnless-death-tail"],
                    declared_tail_snapshot=measured,
                    repo_root=repo,
                )
                if result.get("ok") is not True:
                    raise ProfileError(f"operator correction was refused: {result}")
                after = observe_building_frontier(root, repo_root=repo)
                _assert_corrected_link_pause(after, label="returnless-death")
            elif scenario == "receipts-file-absent":
                root = tmp_root / "receipts-file-absent"
                _write_receipts_file_absent_fixture(root)
                before = observe_building_frontier(root, repo_root=repo)
                if before.get("frontier_kind") != "evidence_incomplete":
                    raise ProfileError(
                        "operator_correction_case receipts-file-absent expected "
                        f"evidence_incomplete before correction, got {before.get('frontier_kind')!r}"
                    )
                result = author_correction_observation(
                    root,
                    author_ref="human:checker",
                    grounds_refs=["observation:receipts-file-absent-tail"],
                    repo_root=repo,
                )
                if result.get("ok") is not True:
                    raise ProfileError(f"operator correction was refused: {result}")
                after = observe_building_frontier(root, repo_root=repo)
                _assert_corrected_link_pause(after, label="receipts-file-absent")
            elif scenario == "refusals":
                root = tmp_root / "refusals"
                _write_complete_fixture(root)
                groundless = author_correction_observation(
                    root,
                    author_ref="coo:checker",
                    grounds_refs=["observation:no-tail"],
                    repo_root=repo,
                )
                if groundless.get("error_kind") != ERROR_GROUNDLESS_CORRECTION:
                    raise ProfileError(
                        "operator correction groundless refusal did not expose "
                        f"{ERROR_GROUNDLESS_CORRECTION!r}: {groundless}"
                    )
                _write_returnless_death_fixture(root)
                measured = dict(measure_correction_tail(root, repo_root=repo))
                forged = dict(measured)
                forged["agent_return_count"] = int(forged["agent_return_count"]) + 1
                forging = author_correction_observation(
                    root,
                    author_ref="human:checker",
                    grounds_refs=["observation:forged-tail"],
                    declared_tail_snapshot=forged,
                    repo_root=repo,
                )
                if forging.get("error_kind") != ERROR_RETURN_FORGING_CORRECTION:
                    raise ProfileError(
                        "operator correction forged-tail refusal did not expose "
                        f"{ERROR_RETURN_FORGING_CORRECTION!r}: {forging}"
                    )
            else:
                raise ProfileError(
                    f"operator_correction_case unknown scenario {scenario!r}"
                )
        count += 1
    return count


def _assert_corrected_link_pause(observation: Mapping[str, Any], *, label: str) -> None:
    if observation.get("frontier_kind") != "link_paused":
        raise ProfileError(
            f"operator_correction_case {label}: expected corrected link_paused, "
            f"got {observation.get('frontier_kind')!r}"
        )
    if observation.get("frontier_kind_uncorrected") != "evidence_incomplete":
        raise ProfileError(
            f"operator_correction_case {label}: missing uncorrected frontier audit"
        )
    refs = observation.get("correction_observation_refs")
    if not isinstance(refs, list) or not refs:
        raise ProfileError(
            f"operator_correction_case {label}: correction refs not exposed"
        )
    if observation.get("correction_applied") is not True:
        raise ProfileError(
            f"operator_correction_case {label}: correction_applied was not true"
        )


def _write_returnless_death_fixture(root: Path) -> None:
    _reset_root(root)
    _write_jsonl(root / "raw" / "agent-received.jsonl", [{"step_ref": "qa"}])
    _write_jsonl(root / "raw" / "adapter-error.jsonl", [{"step_ref": "qa"}])
    _write_jsonl(root / "raw" / "link.jsonl", [_paused_link_row(root.name)])
    _write_json(root / "work" / "building-map.json", {"link_edges": []})
    _write_json(root / "evidence" / "claim_trace" / "agent" / "receipt_trace.json", {})


def _write_receipts_file_absent_fixture(root: Path) -> None:
    _reset_root(root)
    _write_jsonl(root / "raw" / "agent-return.jsonl", [{"step_ref": "work"}])
    _write_jsonl(root / "raw" / "link.jsonl", [_paused_link_row(root.name)])
    _write_json(root / "work" / "building-map.json", {"link_edges": []})
    _write_json(root / "evidence" / "claim_trace" / "agent" / "returned_claims.json", {})


def _write_complete_fixture(root: Path) -> None:
    _reset_root(root)
    for rel in (
        "capture/events.jsonl",
        "raw/raw-manifest.json",
        "raw/brick-work.jsonl",
        "raw/agent-return.jsonl",
        "raw/link.jsonl",
        "evidence/evidence-manifest.json",
        "evidence/claim_trace/brick/work_contract.json",
        "evidence/claim_trace/agent/returned_claims.json",
        "evidence/claim_trace/link/transfer_trace.json",
        "evidence/claim_trace/link/carry_trace.json",
        "evidence/claim_trace/link/sufficiency_trace.json",
        "evidence/claim_trace/link/movement_trace.json",
        "work/building-work.json",
        "work/building-map.json",
    ):
        path = root / rel
        if path.suffix == ".jsonl":
            _write_jsonl(path, [{"step_ref": "work"}])
        else:
            _write_json(path, {})


def _paused_link_row(building_id: str) -> dict[str, Any]:
    return {
        "raw_ref": "raw:link:pause:01",
        "building_id": building_id,
        "step_ref": "pause",
        "transition_lifecycle_state": "paused",
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_paused_at_ref": "raw:link:pause:01",
        "transition_lifecycle_pending_target_ref": "brick-next",
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "hold_reason": "human_or_coo_gate_pause",
    }


def _reset_root(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    root.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )

#!/usr/bin/env python3
"""Fixture verifier for held-node direct expansion safety.

Support evidence only. This checker builds a temporary held Building vessel,
uses ``expand()`` only as a dry-run revision candidate, persists the candidate
through the append-only declaration packet writer, and verifies that prior
step-output, spine, and route/reroute evidence bytes remain unchanged.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PROOF_LIMIT = (
    "proof limit: held-node expansion verifier support check only; not source truth, "
    "success judgment, quality judgment, Movement authority, or direct-connect adoption."
)
EXPECTED_VERIFICATION_GAP_TARGET_ERROR = (
    "verification_gap must not name a reroute-capable Brick boundary"
)
MUTATIONS = ("prior-bytes", "approval-bypass", "route-history", "verification-gap-target")


class HeldNodeExpansionVerifierError(RuntimeError):
    """Checker-local failure."""


def _ensure_imports(repo: Path) -> None:
    for entry in (repo / "support" / "import_identity", repo):
        text = str(entry)
        if text not in sys.path:
            sys.path.insert(0, text)


def _canonical(data: Mapping[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_step(step_ref: str, completion_edge_ref: str) -> dict[str, Any]:
    suffix = step_ref.removeprefix("brick-")
    return {
        "step_ref": step_ref,
        "completion_edge_ref": completion_edge_ref,
        "rows": [
            {
                "axis": "Brick",
                "row_ref": f"brick-row:{suffix}",
                "brick_instance_ref": f"brick-fixture-{suffix}",
            },
            {
                "axis": "Agent",
                "row_ref": f"agent-row:{suffix}",
                "agent_object_ref": "agent-object:dev",
            },
        ],
    }


def _terminal_edge(edge_ref: str, source_step_ref: str) -> dict[str, Any]:
    return {
        "edge_ref": edge_ref,
        "source_step_ref": source_step_ref,
        "rows": [
            {
                "axis": "Link",
                "row_ref": f"link-row:{edge_ref}",
                "movement": "forward",
                "target": "building-boundary:held-expansion-fixture",
                "declared_gate_refs": ["link-gate:coo"],
                "gate_sequence_policy": [
                    {
                        "gate_ref": "link-gate:coo",
                        "on_missing_required_facts": {
                            "action": "hold",
                            "pending_target_basis": "source_brick",
                            "reason_refs": ["observation:held-fixture-coo-gate"],
                            "required_disposition_owner": "caller-or-coo",
                        },
                        "on_sufficient": {"action": "forward"},
                    }
                ],
                "transition_lifecycle": {
                    "state": "paused",
                    "progress_state": "in_progress",
                    "paused_at_ref": "link-transition:held-fixture",
                    "from_brick_ref": "brick-held",
                    "required_disposition_owner": "caller-or-coo",
                    "pending_target_ref": "brick-held",
                    "reason_refs": ["observation:held-fixture-transition"],
                },
            }
        ],
    }


def _base_plan() -> dict[str, Any]:
    return {
        "building_id": "heldnode-expansion-verifier-fixture",
        "plan_ref": "heldnode-expansion-verifier-fixture-plan",
        "plan_shape": "graph",
        "expansion_budget": 1,
        "brick_steps": [_base_step("brick-held", "edge-held-boundary")],
        "link_edges": [_terminal_edge("edge-held-boundary", "brick-held")],
        "execution_order": ["brick-held"],
        "groups": [],
    }


def _write_base_packet(root: Path, plan: Mapping[str, Any]) -> None:
    from support.recording.declaration_packets import (  # noqa: PLC0415
        _canonical_json_text,
        _declared_building_plan_packet,
    )

    work = root / "work"
    work.mkdir(parents=True, exist_ok=True)
    packet = _declared_building_plan_packet(
        building_id="heldnode-expansion-verifier-fixture",
        plan_ref="heldnode-expansion-verifier-fixture-plan",
        plan=plan,
    )
    (work / "declared-building-plan.json").write_text(
        _canonical_json_text(packet),
        encoding="utf-8",
    )


def _write_held_fixture(root: Path, plan: Mapping[str, Any]) -> tuple[Path, ...]:
    from brick_protocol.agent.return_fact import validate_transition_concern_evidence  # noqa: PLC0415

    work = root / "work"
    evidence = root / "evidence"
    step_output = work / "step-outputs" / "brick-held" / "step-output.json"
    spine_event = evidence / "spine" / "events" / "0001-held-frontier.json"
    route_history = work / "route-history.json"
    held_frontier = work / "held-frontier.json"
    for parent in (step_output.parent, spine_event.parent):
        parent.mkdir(parents=True, exist_ok=True)
    transition_concern = {
        "concern_ref": "transition-concern:heldnode-expansion-verifier-fixture",
        "concern_kind": "verification_gap",
        "binding": False,
        "reason_refs": ["observation:held-fixture"],
        "related_boundary_refs": ["building-boundary:held-expansion-fixture"],
    }
    validate_transition_concern_evidence(transition_concern)
    step_output.write_text(
        _canonical(
            {
                "step_ref": "brick-held",
                "agent_return": {"observed_evidence": ["fixture prior output"]},
                "transition_concern_evidence": transition_concern,
            }
        ),
        encoding="utf-8",
    )
    spine_event.write_text(
        _canonical(
            {
                "event_type": "HeldFrontier",
                "sequence_index": 1,
                "step_ref": "brick-held",
                "source_fact_ref": "observation:held-fixture-spine",
            }
        ),
        encoding="utf-8",
    )
    route_history.write_text(
        _canonical(
            {
                "route_rows": [
                    {
                        "edge_ref": "edge-held-boundary",
                        "movement": "forward",
                        "target_ref": "building-boundary:held-expansion-fixture",
                        "route_replay_plan": {
                            "replay_source": "fixture-existing-reroute-history",
                            "reroute_count": 1,
                        },
                    }
                ],
                "reroute_rows": [
                    {
                        "paused_at_ref": "link-transition:held-fixture",
                        "pending_target_ref": "brick-held",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    held_frontier.write_text(
        _canonical(
            {
                "frontier_kind": "held",
                "held_step_ref": "brick-held",
                "pending_target_ref": "brick-held",
                "disposition_required": True,
            }
        ),
        encoding="utf-8",
    )
    return (step_output, spine_event, route_history, held_frontier)


def _write_approval(root: Path) -> None:
    row = {
        "approval_evidence_ref": "approval:heldnode-expansion-verifier",
        "gate_ref": "link-gate:expansion-approval",
        "hold_class": "human_or_coo_gate_pause",
        "hold_paused_at_ref": "hold:heldnode-expansion-verifier",
    }
    (root / "work" / "expansion-approvals.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")


def _make_vessel(tmp: Path) -> tuple[Path, dict[str, Any], tuple[Path, ...]]:
    root = tmp / "project" / "brick-protocol" / "buildings" / "heldnode-expansion-verifier-fixture"
    plan = _base_plan()
    _write_base_packet(root, plan)
    observed_paths = _write_held_fixture(root, plan)
    _write_approval(root)
    return root, plan, observed_paths


def _expand_candidate(repo: Path, parent_plan: Mapping[str, Any]) -> Mapping[str, Any]:
    from support.operator.assembly import Authority, Gate, expand  # noqa: PLC0415

    work_statement = (
        "## Deliverables\n"
        "D1: edit support/checkers/check_heldnode_expansion_verifier.py fixture evidence.\n"
        "종료선: D1 evidence returned."
    )
    candidate = dict(expand(
        "heldnode-expansion-verifier",
        [
            ["work", work_statement, {"write": True}],
            ["closure", "held-node direct expansion verifier closure"],
        ],
        parent_plan=parent_plan,
        completed_frontier=("brick-held",),
        declared_by="coo-heldnode-expansion-verifier",
        authority=Authority.COO,
        adapter="codex-local",
        repo_root=repo,
        write_scope={
            "allowed_paths": ["support/checkers/**"],
            "forbidden_paths": [".git/**"],
        },
        gates=(Gate.STRICT_EVIDENCE,),
    ).as_revision_candidate())
    metadata = dict(candidate["expansion_metadata"])
    metadata["hold_paused_at_ref"] = "hold:heldnode-expansion-verifier"
    candidate["expansion_metadata"] = metadata
    return candidate


def _route_snapshot(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return copy.deepcopy(list(plan.get("link_edges") or []))


def _assert_rejects_without_disposition(
    root: Path,
    candidate: Mapping[str, Any],
    violations: list[str],
) -> None:
    from support.recording.declaration_packets import write_declared_plan_revision  # noqa: PLC0415

    approval_path = root / "work" / "expansion-approvals.jsonl"
    saved = approval_path.read_text(encoding="utf-8")
    approval_path.unlink()
    try:
        try:
            write_declared_plan_revision(
                root,
                candidate["expanded_plan"],
                candidate["expansion_metadata"],
                "approval:heldnode-expansion-verifier",
            )
        except ValueError:
            return
        violations.append("RED disposition-consumption probe did not reject missing approval evidence")
    finally:
        approval_path.write_text(saved, encoding="utf-8")


def _apply_revision(root: Path, candidate: Mapping[str, Any]) -> Path:
    from support.recording.declaration_packets import write_declared_plan_revision  # noqa: PLC0415

    return write_declared_plan_revision(
        root,
        candidate["expanded_plan"],
        candidate["expansion_metadata"],
        "approval:heldnode-expansion-verifier",
    )


def _verify_green(repo: Path, mutate: str | None = None) -> list[str]:
    from brick_protocol.agent.return_fact import validate_transition_concern_evidence  # noqa: PLC0415
    from support.recording.declaration_packets import latest_valid_declared_plan  # noqa: PLC0415

    violations: list[str] = []
    with tempfile.TemporaryDirectory(prefix="heldnode-expansion-verifier-") as raw:
        root, parent_plan, observed_paths = _make_vessel(Path(raw))
        before_hashes = {path: _hash(path) for path in observed_paths}
        before_route_rows = _route_snapshot(parent_plan)
        candidate = _expand_candidate(repo, parent_plan)
        dry_run_stages = {
            str(item.get("stage") or "")
            for item in candidate.get("dry_run_results") or []
            if isinstance(item, Mapping)
        }
        expected_stages = {
            "schema_fragment_compatibility",
            "parent_plan_append_only",
            "write_scope_inheritance",
            "gate_required_observation",
        }
        if dry_run_stages != expected_stages:
            violations.append(f"expand() dry-run stages drifted: {sorted(dry_run_stages)}")
        if mutate == "approval-bypass":
            before = list(violations)
            _assert_rejects_without_disposition(root, candidate, violations)
            if violations == before:
                return ["mutation approval-bypass RED observed: missing approval evidence was rejected"]
            return violations

        _assert_rejects_without_disposition(root, candidate, violations)
        revision = _apply_revision(root, candidate)
        if revision.name != "declared-building-plan.rev-1.json":
            violations.append(f"append-only revision used unexpected filename: {revision.name}")
        if mutate == "prior-bytes":
            target = observed_paths[0]
            body = json.loads(target.read_text(encoding="utf-8"))
            body["mutated_after_revision"] = True
            target.write_text(_canonical(body), encoding="utf-8")
        if mutate == "route-history":
            target = root / "work" / "route-history.json"
            body = json.loads(target.read_text(encoding="utf-8"))
            body["route_rows"][0]["movement"] = "reroute"
            target.write_text(_canonical(body), encoding="utf-8")
        if mutate == "verification-gap-target":
            target = observed_paths[0]
            body = json.loads(target.read_text(encoding="utf-8"))
            body["transition_concern_evidence"]["related_boundary_refs"] = ["brick-held"]
            target.write_text(_canonical(body), encoding="utf-8")

        for path, before_hash in before_hashes.items():
            if _hash(path) != before_hash:
                violations.append(f"prior evidence bytes changed after expansion append: {path.relative_to(root)}")
        concern = json.loads(observed_paths[0].read_text(encoding="utf-8"))["transition_concern_evidence"]
        try:
            validate_transition_concern_evidence(concern)
        except ValueError as exc:
            if mutate == "verification-gap-target" and EXPECTED_VERIFICATION_GAP_TARGET_ERROR not in str(exc):
                violations.append(f"verification-gap-target mutation raised unexpected validator error: {exc}")
            violations.append(f"prior transition_concern_evidence rejected by current Agent return contract: {exc}")
        latest = latest_valid_declared_plan(root)
        if latest.get("execution_order", [])[-2:] != [
            "heldnode-expansion-verifier-expansion-work",
            "heldnode-expansion-verifier-expansion-closure",
        ]:
            violations.append("latest revision did not expose the two appended expansion steps")
        latest_route_prefix = _route_snapshot(latest)[: len(before_route_rows)]
        if latest_route_prefix != before_route_rows:
            violations.append("existing route/reroute link history changed in the expanded plan prefix")
        if "expansion_node_budgets" in latest:
            violations.append("expansion node budgets leaked into the declared plan body")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--mutate", choices=MUTATIONS)
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    _ensure_imports(repo)

    violations = _verify_green(repo, mutate=args.mutate)
    if args.mutate:
        if violations:
            print(f"heldnode expansion mutation RED observed: {args.mutate}")
            for violation in violations:
                print(f"- {violation}")
            print(PROOF_LIMIT)
            return 1
        print(f"heldnode expansion mutation probe did not turn RED: {args.mutate}")
        print(PROOF_LIMIT)
        return 0
    if violations:
        print("heldnode expansion verifier violations:")
        for violation in violations:
            print(f"- {violation}")
        print(PROOF_LIMIT)
        return 1
    print("heldnode expansion verifier passed: fixture append-only criteria and RED probes checked.")
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

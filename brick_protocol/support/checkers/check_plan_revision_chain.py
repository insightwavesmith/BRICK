#!/usr/bin/env python3
"""Validate declared Building Plan revision packets.

This checker covers the T10-S2 birth-certificate revision surface. It verifies
that any persisted ``work/declared-building-plan.rev-N.json`` packets form an
append-only hash chain over the original birth-certificate and that the writer
rejects the six high-risk mutation classes at author time.

Support evidence only: this does not prove source truth, success judgment,
quality judgment, Movement authority, or plan semantic correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)

from brick_protocol.support.recording.declaration_packets import (  # noqa: E402
    _canonical_json_text,
    _declared_building_plan_packet,
    _declared_plan_hash,
    _write_exclusive_json_packet,
    declared_plan_revision_reader_disposition_rows,
    latest_valid_declared_plan,
    write_declared_plan_revision,
)
from brick_protocol.support.operator.plan_expansion import assemble_expanded_graph_plan  # noqa: E402
from brick_protocol.support.operator.gate_sequence import gate_sequence_decision_from_record  # noqa: E402


PROJECT_ROOT = "project"
BUILDINGS_SEGMENT = "buildings"
PROOF_LIMIT = (
    "proof limit: plan-revision-chain support check only; not source truth, "
    "success judgment, quality judgment, Movement authority, or semantic coverage proof."
)


def _base_plan() -> dict[str, Any]:
    return {
        "building_id": "fixture-building",
        "plan_ref": "fixture-plan",
        "plan_shape": "graph",
        "expansion_budget": 1,
        "brick_steps": [
            {"step_ref": "brick-a", "rows": [{"axis": "Brick", "row_ref": "brick-row:a"}]},
        ],
        "link_edges": [],
        "execution_order": ["brick-a"],
        "groups": [],
    }


def _base_plan_with_budget(expansion_budget: int) -> dict[str, Any]:
    plan = _base_plan()
    plan["expansion_budget"] = expansion_budget
    return plan


def _expanded_plan() -> dict[str, Any]:
    plan = json.loads(json.dumps(_base_plan()))
    plan["brick_steps"].append(
        {"step_ref": "brick-b", "rows": [{"axis": "Brick", "row_ref": "brick-row:b"}]}
    )
    plan["link_edges"].append(
        {
            "edge_ref": "edge-a-b",
            "source_step_ref": "brick-a",
            "target_step_ref": "brick-b",
            "rows": [{"axis": "Link", "row_ref": "link-row:a-b"}],
        }
    )
    plan["execution_order"].append("brick-b")
    return plan


def _expanded_plan_with_next_step(parent: Mapping[str, Any], step_ref: str) -> dict[str, Any]:
    plan = json.loads(json.dumps(parent))
    previous_step_ref = plan["execution_order"][-1]
    suffix = step_ref.removeprefix("brick-")
    plan["brick_steps"].append(
        {"step_ref": step_ref, "rows": [{"axis": "Brick", "row_ref": f"brick-row:{suffix}"}]}
    )
    plan["link_edges"].append(
        {
            "edge_ref": f"edge-{previous_step_ref}-{step_ref}",
            "source_step_ref": previous_step_ref,
            "target_step_ref": step_ref,
            "rows": [{"axis": "Link", "row_ref": f"link-row:{previous_step_ref}-{step_ref}"}],
        }
    )
    plan["execution_order"].append(step_ref)
    return plan


def _fragment_for_step(parent: Mapping[str, Any], step_ref: str) -> dict[str, Any]:
    previous_step_ref = parent["execution_order"][-1]
    suffix = step_ref.removeprefix("brick-")
    return {
        "brick_steps": [
            {"step_ref": step_ref, "rows": [{"axis": "Brick", "row_ref": f"brick-row:{suffix}"}]}
        ],
        "link_edges": [
            {
                "edge_ref": f"edge-{previous_step_ref}-{step_ref}",
                "source_step_ref": previous_step_ref,
                "target_step_ref": step_ref,
                "rows": [{"axis": "Link", "row_ref": f"link-row:{previous_step_ref}-{step_ref}"}],
            }
        ],
        "execution_order": [step_ref],
        "groups": [],
        "expansion_node_budgets": {step_ref: 1},
    }


def _fragment() -> dict[str, Any]:
    return _fragment_for_step(_base_plan(), "brick-b")


def _valid_graph_brick_step(step_ref: str, completion_edge_ref: str) -> dict[str, Any]:
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


def _valid_graph_link_edge(
    edge_ref: str,
    source_step_ref: str,
    target_step_ref: str,
    target_brick_ref: str,
) -> dict[str, Any]:
    return {
        "edge_ref": edge_ref,
        "source_step_ref": source_step_ref,
        "target_step_ref": target_step_ref,
        "rows": [
            {
                "axis": "Link",
                "row_ref": f"link-row:{edge_ref}",
                "movement": "forward",
                "target": target_brick_ref,
            }
        ],
    }


def _valid_graph_terminal_edge(edge_ref: str, source_step_ref: str) -> dict[str, Any]:
    return {
        "edge_ref": edge_ref,
        "source_step_ref": source_step_ref,
        "rows": [
            {
                "axis": "Link",
                "row_ref": f"link-row:{edge_ref}",
                "movement": "forward",
                "target": "building-boundary:fixture",
            }
        ],
    }


def _valid_graph_base_plan() -> dict[str, Any]:
    return {
        "building_id": "fixture-building",
        "plan_ref": "fixture-plan",
        "plan_shape": "graph",
        "expansion_budget": 1,
        "brick_steps": [_valid_graph_brick_step("brick-a", "edge-a-boundary")],
        "link_edges": [_valid_graph_terminal_edge("edge-a-boundary", "brick-a")],
        "execution_order": ["brick-a"],
        "groups": [],
    }


def _valid_graph_fragment(step_ref: str) -> dict[str, Any]:
    return {
        "brick_steps": [_valid_graph_brick_step(step_ref, f"edge-{step_ref}-boundary")],
        "link_edges": [
            _valid_graph_link_edge(
                f"edge-a-{step_ref}",
                "brick-a",
                step_ref,
                f"brick-fixture-{step_ref.removeprefix('brick-')}",
            ),
            _valid_graph_terminal_edge(f"edge-{step_ref}-boundary", step_ref),
        ],
        "execution_order": [step_ref],
        "groups": [],
        "expansion_node_budgets": {step_ref: 1},
    }


def _metadata(parent_plan: Mapping[str, Any] | None = None, step_ref: str = "brick-b") -> dict[str, Any]:
    parent = parent_plan or _base_plan()
    return {
        "extends_plan_hash": _declared_plan_hash(parent),
        "extends_plan_hash_algorithm": "sha256",
        "extends_plan_hash_basis": (
            "canonical sorted-key JSON of the pure declared-building-plan copy "
            "(runtime walker state excluded)"
        ),
        "expansion_fragment": _fragment_for_step(parent, step_ref),
        "expansion_node_budgets": {step_ref: 1},
        "hold_paused_at_ref": "hold:fixture",
    }


def _write_base(root: Path, plan: Mapping[str, Any] | None = None) -> None:
    work = root / "work"
    work.mkdir(parents=True, exist_ok=True)
    packet = _declared_building_plan_packet(
        building_id="fixture-building",
        plan_ref="fixture-plan",
        plan=plan or _base_plan(),
    )
    (work / "declared-building-plan.json").write_text(_canonical_json_text(packet), encoding="utf-8")


def _write_approval(
    root: Path,
    *,
    approval_evidence_ref: str = "approval:fixture",
    hold_class: str = "human_or_coo_gate_pause",
    hold_paused_at_ref: str = "hold:fixture",
) -> None:
    row = {
        "approval_evidence_ref": approval_evidence_ref,
        "gate_ref": "link-gate:expansion-approval",
        "hold_class": hold_class,
        "hold_paused_at_ref": hold_paused_at_ref,
    }
    (root / "work" / "expansion-approvals.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")


def _fixture_root(tmp: Path) -> Path:
    root = tmp / "project" / "brick-protocol" / "buildings" / "fixture-building"
    _write_base(root)
    _write_approval(root)
    return root


def _expect_reject(label: str, fn: Callable[[], object], violations: list[str]) -> None:
    try:
        fn()
    except ValueError:
        return
    violations.append(f"RED probe did not reject: {label}")


def _write_corrupt_revision(root: Path, number: int, packet: Mapping[str, Any]) -> Path:
    path = root / "work" / f"declared-building-plan.rev-{number}.json"
    body = dict(packet)
    body["extends_plan_hash"] = hashlib.sha256(b"broken-latest").hexdigest()
    path.write_text(_canonical_json_text(body), encoding="utf-8")
    return path


def _write_revision_packet(root: Path, number: int, packet: Mapping[str, Any]) -> Path:
    path = root / "work" / f"declared-building-plan.rev-{number}.json"
    path.write_text(_canonical_json_text(packet), encoding="utf-8")
    return path


def _revision_packet(
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    extends_plan_hash: str,
    expansion_node_budgets: Mapping[str, int] | None = None,
    approval_evidence_ref: str = "approval:fixture",
    approval_hold_ref: str = "hold:fixture",
) -> dict[str, Any]:
    return {
        "kind": "declared_building_plan_provenance",
        "building_id": building_id,
        "plan_ref": plan_ref,
        "plan_hash": _declared_plan_hash(plan),
        "plan_hash_algorithm": "sha256",
        "plan_hash_basis": (
            "canonical sorted-key JSON of the pure declared-building-plan copy "
            "(runtime walker state excluded)"
        ),
        "declared_plan_copy": dict(plan),
        "extends_plan_hash": extends_plan_hash,
        "extends_plan_hash_algorithm": "sha256",
        "extends_plan_hash_basis": (
            "canonical sorted-key JSON of the pure declared-building-plan copy "
            "(runtime walker state excluded)"
        ),
        "expansion_fragment": {},
        "expansion_node_budgets": dict(expansion_node_budgets or {}),
        "approval_evidence_ref": approval_evidence_ref,
        "approval_hold_ref": approval_hold_ref,
    }


def _exclusive_write_durability_probes(tmp: Path) -> list[str]:
    violations: list[str] = []
    root = tmp / "exclusive-write-durability"
    work = root / "work"
    work.mkdir(parents=True, exist_ok=True)
    target = work / "declared-building-plan.rev-1.json"
    first_packet = {
        "kind": "declared_building_plan_provenance",
        "plan_hash": "first",
        "declared_plan_copy": {"step_ref": "first"},
    }
    second_packet = {
        "kind": "declared_building_plan_provenance",
        "plan_hash": "second",
        "declared_plan_copy": {"step_ref": "second"},
    }
    _write_exclusive_json_packet(target, first_packet)
    first_body = target.read_text(encoding="utf-8")
    _expect_reject(
        "same-path exclusive revision create",
        lambda: _write_exclusive_json_packet(target, second_packet),
        violations,
    )
    if target.read_text(encoding="utf-8") != first_body:
        violations.append("GREEN same-path collision probe did not preserve the first revision body")

    partial_root = tmp / "partial-temp-litter"
    _write_base(partial_root)
    partial_target = partial_root / "work" / "declared-building-plan.rev-1.json"
    partial_tmp = partial_target.with_name(partial_target.name + f".tmp-{os.getpid()}")
    partial_tmp.write_text("{", encoding="utf-8")
    partial_latest = latest_valid_declared_plan(partial_root)
    if partial_latest.get("brick_steps", [])[-1].get("step_ref") != "brick-a":
        violations.append("GREEN partial-temp probe did not leave readers on the base declaration")
    if partial_target.exists():
        violations.append("GREEN partial-temp probe exposed a revision target before recovery")
    _write_approval(partial_root)
    rev = write_declared_plan_revision(
        partial_root,
        _expanded_plan(),
        _metadata(),
        "approval:fixture",
    )
    if rev.name != "declared-building-plan.rev-1.json":
        violations.append("GREEN partial-temp probe did not recover by writing rev-1")
    return violations


def _strict_revision_chain_errors(building_root: Path) -> list[str]:
    work_dir = building_root / "work"
    base_path = work_dir / "declared-building-plan.json"
    errors: list[str] = []
    try:
        base_packet = json.loads(base_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{base_path}: unreadable base declared plan packet: {exc}"]
    if not isinstance(base_packet, Mapping):
        return [f"{base_path}: base declared plan packet is not a JSON object"]
    expected_hash = str(base_packet.get("plan_hash") or "")
    for rev_path in sorted(work_dir.glob("declared-building-plan.rev-*.json"), key=_revision_sort_key):
        try:
            packet = json.loads(rev_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{rev_path}: unreadable revision packet: {exc}")
            continue
        if not isinstance(packet, Mapping):
            errors.append(f"{rev_path}: revision packet is not a JSON object")
            continue
        observed_parent = str(packet.get("extends_plan_hash") or "")
        if observed_parent != expected_hash:
            errors.append(
                f"{rev_path}: extends_plan_hash {observed_parent!r} does not match "
                f"previous plan_hash {expected_hash!r}"
            )
            continue
        plan = packet.get("declared_plan_copy")
        if not isinstance(plan, Mapping):
            errors.append(f"{rev_path}: declared_plan_copy is not a JSON object")
            continue
        observed_hash = _declared_plan_hash(plan)
        packet_hash = str(packet.get("plan_hash") or "")
        if packet_hash != observed_hash:
            errors.append(f"{rev_path}: plan_hash does not match declared_plan_copy")
            continue
        expected_hash = packet_hash
    return errors


def _revision_sort_key(path: Path) -> tuple[int, str]:
    raw = path.name.removeprefix("declared-building-plan.rev-").removesuffix(".json")
    if raw.isdigit():
        return (int(raw), path.name)
    return (10**9, path.name)


def run_fixture_probes() -> list[str]:
    violations: list[str] = []
    with tempfile.TemporaryDirectory(prefix="plan-revision-chain-") as raw:
        tmp = Path(raw)

        green = _fixture_root(tmp / "green")
        rev = write_declared_plan_revision(green, _expanded_plan(), _metadata(), "approval:fixture")
        latest = latest_valid_declared_plan(green)
        if rev.name != "declared-building-plan.rev-1.json":
            violations.append("GREEN probe wrote an unexpected revision filename")
        if latest.get("brick_steps", [])[-1].get("step_ref") != "brick-b":
            violations.append("GREEN probe did not read rev-1 as the latest valid plan")

        root = _fixture_root(tmp / "approval-only-retry")
        retry_rev = write_declared_plan_revision(root, _expanded_plan(), _metadata(), "approval:fixture")
        if retry_rev.name != "declared-building-plan.rev-1.json":
            violations.append("GREEN retry probe did not create rev-1 after approval-only intermediate state")

        root = _fixture_root(tmp / "broken-latest-fallback")
        first = write_declared_plan_revision(root, _expanded_plan(), _metadata(), "approval:fixture")
        _write_corrupt_revision(root, 2, json.loads(first.read_text(encoding="utf-8")))
        fallback = latest_valid_declared_plan(root)
        if fallback.get("brick_steps", [])[-1].get("step_ref") != "brick-b":
            violations.append("GREEN fallback probe did not retreat to the prior valid revision")
        hold_log = root / "work" / "declared-building-plan.revision-holds.jsonl"
        if not hold_log.is_file() or "declared_plan_revision_hold" not in hold_log.read_text(
            encoding="utf-8"
        ):
            violations.append("GREEN fallback probe did not record broken-latest revision HOLD evidence")
        if not _strict_revision_chain_errors(root):
            violations.append("RED broken-latest probe was not visible to strict checker validation")

        root = _fixture_root(tmp / "forged-valid-hash-changed-existing-node")
        changed = _expanded_plan()
        changed["brick_steps"][0]["rows"][0]["row_ref"] = "brick-row:forged"
        _write_revision_packet(
            root,
            1,
            _revision_packet(
                building_id="fixture-building",
                plan_ref="fixture-plan",
                plan=changed,
                extends_plan_hash=_declared_plan_hash(_base_plan()),
                expansion_node_budgets={"brick-b": 1},
            ),
        )
        forged_latest = latest_valid_declared_plan(root)
        if forged_latest.get("brick_steps", [])[-1].get("step_ref") != "brick-a":
            violations.append(
                "RED forged valid-hash reader probe did not reject changed existing node"
            )

        root = _fixture_root(tmp / "torn-litter-budget")
        _write_corrupt_revision(
            root,
            1,
            {
                "kind": "declared_building_plan_provenance",
                "plan_hash": "not-a-real-plan-hash",
                "declared_plan_copy": _expanded_plan(),
                "extends_plan_hash": "wrong",
            },
        )
        litter_rev = write_declared_plan_revision(root, _expanded_plan(), _metadata(), "approval:fixture")
        if litter_rev.name != "declared-building-plan.rev-2.json":
            violations.append("GREEN torn-litter probe did not create the next non-overwriting rev file")
        litter_latest = latest_valid_declared_plan(root)
        if litter_latest.get("brick_steps", [])[-1].get("step_ref") != "brick-b":
            violations.append("GREEN torn-litter probe counted corrupt rev files instead of valid chain length")

        violations.extend(_exclusive_write_durability_probes(tmp))

        root = _fixture_root(tmp / "changed-node")
        changed = _expanded_plan()
        changed["brick_steps"][0]["rows"][0]["row_ref"] = "brick-row:changed"
        _expect_reject(
            "existing node mutation",
            lambda: write_declared_plan_revision(root, changed, _metadata(), "approval:fixture"),
            violations,
        )

        root = _fixture_root(tmp / "deleted-node")
        deleted = _expanded_plan()
        deleted["brick_steps"] = deleted["brick_steps"][1:]
        _expect_reject(
            "existing node deletion",
            lambda: write_declared_plan_revision(root, deleted, _metadata(), "approval:fixture"),
            violations,
        )

        root = _fixture_root(tmp / "bad-chain")
        bad_meta = _metadata()
        bad_meta["extends_plan_hash"] = hashlib.sha256(b"wrong").hexdigest()
        _expect_reject(
            "extends_plan_hash mismatch",
            lambda: write_declared_plan_revision(root, _expanded_plan(), bad_meta, "approval:fixture"),
            violations,
        )

        root = _fixture_root(tmp / "missing-approval")
        (root / "work" / "expansion-approvals.jsonl").unlink()
        _expect_reject(
            "missing approval evidence",
            lambda: write_declared_plan_revision(root, _expanded_plan(), _metadata(), "approval:fixture"),
            violations,
        )

        root = _fixture_root(tmp / "stale-approval")
        _write_approval(root, hold_paused_at_ref="hold:stale")
        _expect_reject(
            "stale approval hold identity",
            lambda: write_declared_plan_revision(root, _expanded_plan(), _metadata(), "approval:fixture"),
            violations,
        )

        root = _fixture_root(tmp / "approval-reuse")
        base_with_budget = _base_plan_with_budget(2)
        _write_base(root, base_with_budget)
        first_expansion = _expanded_plan_with_next_step(base_with_budget, "brick-b")
        write_declared_plan_revision(
            root,
            first_expansion,
            _metadata(base_with_budget, step_ref="brick-b"),
            "approval:fixture",
        )
        second_expansion = _expanded_plan_with_next_step(first_expansion, "brick-c")
        _expect_reject(
            "same approval evidence reuse across chained revisions",
            lambda: write_declared_plan_revision(
                root,
                second_expansion,
                _metadata(first_expansion, step_ref="brick-c"),
                "approval:fixture",
            ),
            violations,
        )

        root = _fixture_root(tmp / "same-hold-new-approval-reuse")
        base_with_budget = _base_plan_with_budget(2)
        _write_base(root, base_with_budget)
        first_expansion = _expanded_plan_with_next_step(base_with_budget, "brick-b")
        write_declared_plan_revision(
            root,
            first_expansion,
            _metadata(base_with_budget, step_ref="brick-b"),
            "approval:fixture",
        )
        _write_approval(root, approval_evidence_ref="approval:second")
        second_expansion = _expanded_plan_with_next_step(first_expansion, "brick-c")
        _expect_reject(
            "same hold identity reuse with a new approval evidence ref",
            lambda: write_declared_plan_revision(
                root,
                second_expansion,
                _metadata(first_expansion, step_ref="brick-c"),
                "approval:second",
            ),
            violations,
        )

        root = _fixture_root(tmp / "budget-exhausted")
        base = _base_plan()
        base["expansion_budget"] = 0
        _write_base(root, base)
        _expect_reject(
            "expansion_budget exhausted",
            lambda: write_declared_plan_revision(root, _expanded_plan(), _metadata(base), "approval:fixture"),
            violations,
        )

        root = _fixture_root(tmp / "bool-base-budget")
        base = _base_plan()
        base["expansion_budget"] = True
        _write_base(root, base)
        _expect_reject(
            "bool base expansion_budget",
            lambda: write_declared_plan_revision(root, _expanded_plan(), _metadata(base), "approval:fixture"),
            violations,
        )

        root = _fixture_root(tmp / "bool-node-budget")
        bool_metadata = _metadata()
        bool_metadata["expansion_node_budgets"] = {"brick-b": True}
        _expect_reject(
            "bool expansion_node_budgets revision packet",
            lambda: write_declared_plan_revision(root, _expanded_plan(), bool_metadata, "approval:fixture"),
            violations,
        )
        bool_fragment = _valid_graph_fragment("brick-b")
        bool_fragment["expansion_node_budgets"] = {"brick-b": True}
        _expect_reject(
            "bool expansion_node_budgets expansion fragment",
            lambda: assemble_expanded_graph_plan(
                _valid_graph_base_plan(),
                bool_fragment,
                completed_frontier=["brick-a"],
            ),
            violations,
        )

        root = _fixture_root(tmp / "budget-mutated")
        mutated = _expanded_plan()
        mutated["node_reroute_budgets"] = {"brick-a": 2}
        _expect_reject(
            "node_reroute_budgets reuse",
            lambda: write_declared_plan_revision(root, mutated, _metadata(), "approval:fixture"),
            violations,
        )

        root = _fixture_root(tmp / "bad-hold-class")
        _write_approval(root, hold_class="unlisted_hold_class")
        _expect_reject(
            "hold class whitelist",
            lambda: write_declared_plan_revision(root, _expanded_plan(), _metadata(), "approval:fixture"),
            violations,
        )

        _expect_reject(
            "gate sequence replay record sideways top-level action",
            lambda: gate_sequence_decision_from_record(
                {
                    "action": "sideways",
                    "gate_results": [],
                    "gate_action_sequence": [],
                }
            ),
            violations,
        )
        _expect_reject(
            "gate sequence replay record sideways sequence action",
            lambda: gate_sequence_decision_from_record(
                {
                    "action": "hold",
                    "gate_results": [],
                    "gate_action_sequence": [
                        {
                            "gate_ref": "link-gate:strict",
                            "action": "sideways",
                        }
                    ],
                }
            ),
            violations,
        )

    return violations


def validate_reader_disposition_rows() -> list[str]:
    violations: list[str] = []
    rows = declared_plan_revision_reader_disposition_rows()
    if not rows:
        return ["D6 reader disposition table is empty"]
    required_paths = {
        "brick_protocol/support/operator/walker_resume.py",
        "brick_protocol/support/recording/spine_projection.py",
        "brick_protocol/support/checkers/check_evidence_spine_projection.py",
        "brick_protocol/support/operator/evidence_assembly.py",
        "brick_protocol/support/recording/adapter_error_frontier.py",
        "brick_protocol/support/operator/walker_carry.py",
        "brick_protocol/support/operator/run.py",
        "brick_protocol/support/operator/reporter.py",
        "brick_protocol/support/operator/onboard.py",
        "brick_protocol/support/operator/cli.py",
        "brick_protocol/support/operator/driver.py",
        "brick_protocol/support/operator/native_dispatch.py",
        "brick_protocol/support/operator/evidence_status.py",
    }
    allowed_dispositions = {
        "converted",
        "base_preserved_by_callee",
        "deferred_write_scope_forbidden",
        "deferred_output_contract",
        "deferred_different_surface",
        "deferred_no_active_reader_change",
        "base_marker_preserved",
    }
    observed_paths: set[str] = set()
    converted_paths: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            violations.append(f"D6 reader disposition row {index} is not a mapping")
            continue
        path = row.get("path")
        reader = row.get("reader")
        disposition = row.get("disposition")
        reason = row.get("reason")
        if not all(isinstance(value, str) and value for value in (path, reader, disposition, reason)):
            violations.append(f"D6 reader disposition row {index} must carry path/reader/disposition/reason")
            continue
        if disposition not in allowed_dispositions:
            violations.append(f"D6 reader disposition row {index} has unrecognized disposition {disposition!r}")
        observed_paths.add(path)
        if disposition == "converted":
            converted_paths.add(path)
    missing_paths = sorted(required_paths - observed_paths)
    if missing_paths:
        violations.append("D6 reader disposition table is missing path(s): " + ", ".join(missing_paths))
    for path in (
        "brick_protocol/support/operator/walker_resume.py",
        "brick_protocol/support/recording/spine_projection.py",
        "brick_protocol/support/checkers/check_evidence_spine_projection.py",
    ):
        if path not in converted_paths:
            violations.append(f"D6 required revision-aware reader was not marked converted: {path}")
    return violations


def validate_live_revision_chains(repo: Path) -> list[str]:
    violations: list[str] = []
    buildings_root = repo / PROJECT_ROOT / "brick-protocol" / BUILDINGS_SEGMENT
    if not buildings_root.is_dir():
        return violations
    for rev_path in sorted(buildings_root.glob("*/work/declared-building-plan.rev-*.json")):
        building_root = rev_path.parents[1]
        for error in _strict_revision_chain_errors(building_root):
            violations.append(f"{rev_path}: invalid declared plan revision chain: {error}")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    violations = []
    violations.extend(run_fixture_probes())
    violations.extend(validate_reader_disposition_rows())
    violations.extend(validate_live_revision_chains(repo))
    if violations:
        print("plan revision chain violations:")
        for violation in violations:
            print(f"- {violation}")
        print(PROOF_LIMIT)
        return 1
    print("plan revision chain passed: fixture RED/GREEN probes and live revision chains checked.")
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Building frontier observation (P3d concern module).

Static read over already-written evidence that reports the current frontier_kind
(complete / incomplete / paused / waiting / agent_incomplete / closure_pending).
It inspects no process liveness, chooses no Movement or target, and judges no
success or quality. Reaches no axis (reads recorded link.jsonl lifecycle records
by field name)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.building_operation_common import (
    REPO_ROOT,
    _jsonl_records,
    _list_count,
    _read_json_mapping,
    _rel,
    _repo_path,
)
from brick_protocol.support.operator.evidence_status import evidence_status


# SINGLE SOURCE of the frontier_kind vocabulary. Each literal is written ONCE
# here as a named constant; observe_building_frontier assigns frontier_kind to one
# of these (and only these), and FRONTIER_KINDS is BUILT FROM the same constants
# (not a parallel re-listing) so a branch literal can never drift out of the
# published set. Any consumer that must enumerate the legal frontier kinds (e.g.
# the U5.5 spine value-guard) imports FRONTIER_KINDS instead of re-listing strings,
# so the observer and the guard agree by construction.
_FRONTIER_COMPLETE = "complete"
_FRONTIER_CLOSURE_PENDING = "closure_pending"
_FRONTIER_EVIDENCE_INCOMPLETE = "evidence_incomplete"
_FRONTIER_AGENT_INCOMPLETE = "agent_incomplete"
_FRONTIER_LINK_PAUSED = "link_paused"
_FRONTIER_HUMAN_REVIEW_WAITING = "human_review_waiting"
FRONTIER_KINDS: tuple[str, ...] = (
    _FRONTIER_COMPLETE,
    _FRONTIER_CLOSURE_PENDING,
    _FRONTIER_EVIDENCE_INCOMPLETE,
    _FRONTIER_AGENT_INCOMPLETE,
    _FRONTIER_LINK_PAUSED,
    _FRONTIER_HUMAN_REVIEW_WAITING,
)


def observe_building_frontier(
    building_root: str | Path,
    *,
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Observe the current evidence frontier for one Building root.

    This is a static support view over already-written files. It does not
    inspect process liveness, choose Movement, choose targets, resume, retry,
    pause, close, or judge success/quality.
    """

    repo = Path(repo_root).resolve()
    root = _repo_path(repo, building_root)
    status = evidence_status(root, repo_root=repo)
    link_records = _jsonl_records(root / "raw" / "link.jsonl")
    agent_received_records = _jsonl_records(root / "raw" / "agent-received.jsonl")
    agent_return_records = _jsonl_records(root / "raw" / "agent-return.jsonl")
    if not agent_return_records:
        agent_return_records = _jsonl_records(root / "raw" / "agent-returns.jsonl")
    adapter_error_records = _jsonl_records(root / "raw" / "adapter-error.jsonl")
    building_map = _read_json_mapping(root / "work" / "building-map.json")

    frontier_kind = _FRONTIER_CLOSURE_PENDING
    frontier_reason = "evidence root has returned Agent facts and no closed boundary observation"
    latest_lifecycle = _latest_transition_lifecycle_record(link_records)
    if status.missing_files:
        frontier_kind = _FRONTIER_EVIDENCE_INCOMPLETE
        frontier_reason = "required evidence files are missing"
    elif len(agent_received_records) > len(agent_return_records):
        frontier_kind = _FRONTIER_AGENT_INCOMPLETE
        frontier_reason = (
            "adapter error evidence exists after Agent receipt and before returned AgentFact"
            if adapter_error_records
            else "agent received evidence exists without matching returned evidence"
        )
    elif latest_lifecycle.get("transition_lifecycle_state") == "paused":
        frontier_kind = _FRONTIER_LINK_PAUSED
        frontier_reason = "declared Link transition_lifecycle.state is paused"
    elif _latest_building_lifecycle_state(link_records) == "waiting":
        frontier_kind = _FRONTIER_HUMAN_REVIEW_WAITING
        frontier_reason = "declared building_lifecycle.state is waiting"
    elif _closed_boundary_observed(link_records, building_map):
        frontier_kind = _FRONTIER_COMPLETE
        frontier_reason = "declared closed boundary observed in Link evidence"

    return {
        "kind": "building_frontier_observation",
        "schema_version": "frontier-observation-0",
        "building_root": _rel(repo, root),
        "frontier_kind": frontier_kind,
        "frontier_reason": frontier_reason,
        "observed_counts": {
            "agent_received_records": len(agent_received_records),
            "agent_return_records": len(agent_return_records),
            "adapter_error_records": len(adapter_error_records),
            "link_records": len(link_records),
            "building_map_link_edges": _list_count(building_map.get("link_edges")),
        },
        "latest_transition_lifecycle": latest_lifecycle,
        "missing_required_files": list(status.missing_files),
        "proof_limits": [
            "support frontier observation only",
            "static evidence files only",
            "not process liveness",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
            "not route target choice",
            "not pause/resume authority",
        ],
        "not_proven": [
            "whether a provider process is currently alive",
            "semantic correctness of current frontier",
            "whether caller/COO should resume, reroute, or close",
            "future Building outcome",
        ],
    }


def _latest_transition_lifecycle_record(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    for record in reversed(records):
        if record.get("transition_lifecycle_state") in {"paused", "resumed"}:
            return {
                key: record.get(key, "")
                for key in (
                    "step_ref",
                    "source_brick_instance_ref",
                    "target_brick_instance_ref",
                    "transition_lifecycle_state",
                    "transition_lifecycle_progress_state",
                    "transition_lifecycle_paused_at_ref",
                    "transition_lifecycle_resumed_from_ref",
                    "transition_lifecycle_from_brick_ref",
                    "transition_lifecycle_pending_target_ref",
                    "transition_lifecycle_required_disposition_owner",
                    "transition_lifecycle_disposition_action",
                    "transition_lifecycle_budget_increment",
                    "transition_lifecycle_reason_refs",
                    "transition_lifecycle_carry_budget_evidence_ref",
                )
                if record.get(key) not in (None, "")
            }
    return {}


def _latest_building_lifecycle_state(records: Sequence[Mapping[str, Any]]) -> str:
    for record in reversed(records):
        state = record.get("building_lifecycle_state")
        if isinstance(state, str) and state.strip():
            return state.strip()
    return ""


def _closed_boundary_observed(
    link_records: Sequence[Mapping[str, Any]],
    building_map: Mapping[str, Any],
) -> bool:
    for record in reversed(link_records):
        target = str(
            record.get("target_brick_instance_ref")
            or record.get("target")
            or ""
        )
        if _is_closed_boundary_ref(target):
            return True
    link_edges = building_map.get("link_edges")
    if isinstance(link_edges, list):
        for edge in link_edges:
            if not isinstance(edge, Mapping):
                continue
            target = str(edge.get("target_brick_instance_ref") or "")
            if _is_closed_boundary_ref(target):
                return True
    return False


def _is_closed_boundary_ref(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        normalized.startswith("building-boundary:")
        or normalized.startswith("building-boundary-")
    ) and normalized.endswith("closed")

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

from brick_protocol.link.spec import (
    FrontierSufficiencyFacts,
    FrontierSufficiencyVocab,
    frontier_sufficiency_verdict,
)
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
_FRONTIER_CHAT_SESSION_PARKED = "chat_session_parked"
_FRONTIER_LINK_PAUSED = "link_paused"
_FRONTIER_HUMAN_REVIEW_WAITING = "human_review_waiting"
FRONTIER_KINDS: tuple[str, ...] = (
    _FRONTIER_COMPLETE,
    _FRONTIER_CLOSURE_PENDING,
    _FRONTIER_EVIDENCE_INCOMPLETE,
    _FRONTIER_CHAT_SESSION_PARKED,
    _FRONTIER_AGENT_INCOMPLETE,
    _FRONTIER_LINK_PAUSED,
    _FRONTIER_HUMAN_REVIEW_WAITING,
)

# J6 (E2/S10): the frontier_kind VOCABULARY stays support-owned (these literals
# are facts support records + publishes). The SUFFICIENCY VERDICT — which kind the
# recorded evidence has reached, in what precedence — is a Link decision
# (link.spec.frontier_sufficiency_verdict). This bundle passes the support-owned
# literals into the Link ladder so the vocabulary keeps its single source here
# while Link owns only the precedence logic. Built from the SAME named constants
# as FRONTIER_KINDS so a literal can never drift between the two.
_FRONTIER_SUFFICIENCY_VOCAB = FrontierSufficiencyVocab(
    closure_pending=_FRONTIER_CLOSURE_PENDING,
    evidence_incomplete=_FRONTIER_EVIDENCE_INCOMPLETE,
    chat_session_parked=_FRONTIER_CHAT_SESSION_PARKED,
    complete=_FRONTIER_COMPLETE,
    agent_incomplete=_FRONTIER_AGENT_INCOMPLETE,
    link_paused=_FRONTIER_LINK_PAUSED,
    human_review_waiting=_FRONTIER_HUMAN_REVIEW_WAITING,
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
    chat_session_park_records = _jsonl_records(root / "raw" / "chat-session-park.jsonl")
    parked_step_output_count = _parked_step_output_count(root)
    work_envelope_count = _work_envelope_count(root)
    building_map = _read_json_mapping(root / "work" / "building-map.json")

    latest_lifecycle = _latest_transition_lifecycle_record(link_records)
    # J6 (E2/S10): support GATHERS the facts (counts, lifecycle-state strings,
    # missing-file presence, closed-boundary observations) and hands them to the
    # Link SUFFICIENCY verdict, which owns the precedence ladder (which frontier_kind
    # the evidence has reached). The kind literals ride along via the support-owned
    # vocab bundle, so the vocabulary keeps its single source here. The verdict is
    # behavior-identical to the prior inline ladder.
    facts = FrontierSufficiencyFacts(
        has_missing_files=bool(status.missing_files),
        agent_return_count=len(agent_return_records),
        agent_received_count=len(agent_received_records),
        has_chat_session_park=bool(chat_session_park_records),
        has_parked_step_output=bool(parked_step_output_count),
        has_adapter_error=bool(adapter_error_records),
        closed_boundary_after_latest_pause=_closed_boundary_raw_record_after_latest_pause(
            link_records
        ),
        latest_transition_lifecycle_state=str(
            latest_lifecycle.get("transition_lifecycle_state") or ""
        ),
        latest_building_lifecycle_state=_latest_building_lifecycle_state(link_records),
        closed_boundary_observed=_closed_boundary_observed(link_records, building_map),
    )
    verdict = frontier_sufficiency_verdict(facts, _FRONTIER_SUFFICIENCY_VOCAB)
    frontier_kind = verdict.frontier_kind
    frontier_reason = verdict.frontier_reason
    if (
        frontier_kind == _FRONTIER_LINK_PAUSED
        and _latest_hold_reason(link_records)
        in {
            "fake_landing_write_scope_diff_absent",
            "write_scope_forbidden_diff_present",
        }
    ):
        frontier_kind = _FRONTIER_HUMAN_REVIEW_WAITING
        frontier_reason = _latest_hold_reason(link_records)

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
            "chat_session_park_records": len(chat_session_park_records),
            "parked_step_output_records": parked_step_output_count,
            "work_envelope_records": work_envelope_count,
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


def _latest_hold_reason(records: Sequence[Mapping[str, Any]]) -> str:
    for record in reversed(records):
        reason = record.get("hold_reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return ""


def _closed_boundary_raw_record_after_latest_pause(records: Sequence[Mapping[str, Any]]) -> bool:
    latest_pause_index = -1
    for index, record in enumerate(records):
        if record.get("transition_lifecycle_state") == "paused":
            latest_pause_index = index
    for record in reversed(records[latest_pause_index + 1 :]):
        if not _is_executed_link_record(record):
            continue
        target = str(
            record.get("target_brick_instance_ref")
            or record.get("target")
            or ""
        )
        if _is_closed_boundary_ref(target):
            return True
    return False


def _parked_step_output_count(root: Path) -> int:
    return sum(
        1
        for path in (root / "work" / "step-outputs").glob("*/parked.json")
        if path.is_file()
    )


def _work_envelope_count(root: Path) -> int:
    return sum(
        1
        for path in (root / "work" / "step-outputs").glob("*/work-envelope.json")
        if path.is_file()
    )


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
    """Return whether executed Link evidence reached a closed boundary.

    ``building_map`` is retained for the public helper signature, but declared
    map edges are not execution evidence. A mid-walk Building can already carry
    its declared terminal edge in the map; only raw Link records can close the
    read-side frontier.
    """

    _ = building_map
    for record in reversed(link_records):
        if not _is_executed_link_record(record):
            continue
        target = str(
            record.get("target_brick_instance_ref")
            or record.get("target")
            or ""
        )
        if _is_closed_boundary_ref(target):
            return True
    return False


def _is_executed_link_record(record: Mapping[str, Any]) -> bool:
    raw_ref = str(record.get("raw_ref") or "")
    return raw_ref.startswith("raw:link:")


def _is_closed_boundary_ref(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        normalized.startswith("building-boundary:")
        or normalized.startswith("building-boundary-")
    ) and normalized.endswith("closed")

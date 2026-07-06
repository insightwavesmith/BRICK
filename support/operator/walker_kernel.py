"""Forward step-walk kernel for the bounded agent-proposed dynamic graph walker.

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
thin one-step-crossing FORWARD walk kernel of the dynamic_walker god-module. It
walks the declared graph over the existing execution_order linearization, and
after a node completes inspects the Agent return for a NON-BINDING reroute
proposal; if the declared gate adopts and the target node budget is available it
appends the target (+ declared replay scope) to the live attempt queue. On a
human/coo gate, an unbudgeted target, or budget exhaustion it HOLDs. The
separable concerns (reroute budget / HOLD / fan-in / transition-concern / step
fixtures / frontier) live in their own collaborator modules; this kernel
orchestrates them.

ζ7 boundary preserved: the Agent PROPOSES (binding:false); the DECLARED Link gate
ADOPTS or PAUSEs; support WALKS the adopted route and RECORDS. Support authors no
route or Movement, judges no success or quality, schedules nothing, retries
nothing, and calls no provider.

Support mechanics only. Homes NO axis crossing (the reroute-adoption record is
built from the recording contract field-spec).
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import TimeoutError as FutureTimeoutError
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

# Brick-axis canonical symbol crossing the Brick->Agent (work dispatch) seam.
# The carry seam reads the UPSTREAM kind's HANDOFF subset off the brick_row (the
# SAME row surface as required_return_shape) and parses it with this canonical
# parser to FILTER the forwarded summary. Registered under crossing_id
# `brick_work` canonical_symbols (crossing_registry.yaml); support does NOT read
# the return.yaml form directly -- it reads the value off the Brick row.
from brick_protocol.brick.work import parse_carries_forward_fields
from brick_protocol.support.connection.adapter_validation import (
    safe_source_fact_body,
)
from brick_protocol.support.connection.agent_adapter import (
    AgentBrainCallable,
    CommandRunner,
)
from brick_protocol.support.operator.contracts import (
    BuildingPlanSupportResult,
    BuildingRunSupportResult,
    PLAN_RESULT_SIDE_CHANNEL_FIELDS,
)
from brick_protocol.support.operator.gate_sequence import (
    GateSequenceDecision,
    run_gate_sequence_policy,
)
from brick_protocol.support.operator.plan_graph import (
    _graph_fan_in_sources_by_target_step_ref,
    _graph_fan_out_targets_by_source_step_ref,
    _linear_plan_from_graph_plan,
)
from brick_protocol.support.operator.plan_validation import (
    _incoming_link_handoff_refs,
    _plan_building_id,
    _step_fixture_from_plan_step,
    _task_source_ref_from_plan,
    validate_declared_building_plan,
)
from brick_protocol.support.operator.primitives import (
    _REPO_ROOT,
    _merge_texts,
    _optional_text_from_mapping,
    _optional_text_value,
)
from brick_protocol.support.operator.reporter import (
    building_event_kind_from_frontier,
    emit_building_event_for_policy,
    report_event_policy_from_plan,
)
from brick_protocol.support.recording.declaration_packets import (
    _write_declaration_work_evidence,
)
from brick_protocol.support.recording.capture import (
    graph_ready_json_object,
    graph_ready_timestamp,
    project_ref_for_building_root,
)
from brick_protocol.support.recording.step_outputs import _step_output_manifest_ref
from brick_protocol.support.recording.walker_evidence import build_hold_record
from brick_protocol.support.operator.walker_common import (
    FAN_TOPOLOGY_NOT_PROVEN,
    FAN_TOPOLOGY_PROOF_LIMITS,
    NOT_PROVEN,
    PROOF_LIMITS,
    RESUME_NOT_PROVEN,
)
from brick_protocol.support.operator.walker_fan_in import (
    _build_fan_in_wait_all_hold,
    _fan_in_cohort_replay_plan,
    _fan_in_wait_all_observations_for_held_source,
    _fan_in_wait_all_state,
    _graph_has_fan_groups,
    _graph_root_step_refs,
    _graph_successor_step_refs_by_source_step_ref,
    _splice_declared_successors,
)
from brick_protocol.support.operator.walker_frontier import (
    _write_dynamic_chat_session_park_frontier,
    _write_dynamic_adapter_error_frontier,
)
from brick_protocol.support.operator.walker_hold import (
    _build_hold,
    _hold_paused_at_ref,
    _inject_fan_in_paused_link,
    _inject_hold_paused_link,
    _replace_held_source_with_lifecycle,
    _resumed_lifecycle_from_hold,
)
from brick_protocol.support.operator.walker_reroute_budget import (
    _carry_budget_evidence_ref,
    _node_reroute_budgets,
)
from brick_protocol.support.operator.walker_step_fixture import (
    _adopted_by_ref,
    _brick_instance_ref_from_linear_step,
    _declared_replay_scope_step_refs,
    _gate_disposition_for_step,
    _structured_field_observation_for_step,
)
from brick_protocol.support.operator.walker_transition_concern import (
    _build_invalid_transition_concern_hold,
    _classify_reroute_target,
    _RerouteTargetClassification,
    _transition_concern_observation_from_step_result,
)
from brick_protocol.support.recording.walker_evidence import (
    build_reroute_adoption_record,
    build_resume_observation,
)


from brick_protocol.support.operator.walker_frontier_driver import (
    _FANOUT_AUTO_POOL,
    _FrontierDriver,
    _ReadyItemsResult,
    _fanout_dispatch_pool_size,
    _has_explicit_fanout_pool_override,
)
from brick_protocol.support.operator.walker_carry import (
    _WIKI_CARRY_NOTE,
    _WIKI_CARRY_VIEW_HEADER,
    _brick_source_facts,
    _carry_fact_observation,
    _carry_gate_observation,
    _carries_forward_fields_for_result,
    _clear_overwrite_claim_trace_manifest,
    _fan_in_observation_from_carry_observation,
    _latest_completed_step_index,
    _latest_completed_step_index_any_depth,
    _matching_step_output_index,
    _materialize_initial_declaration_evidence,
    _preflight_step_output_building_root,
    _returned_summary_for_carry,
    _root_holds_only_intake_plan_artifact,
    _source_fact_body_carry_for_step,
    _step_output_body_from_file,
    _step_output_wiki_carry_body,
    _step_ref_from_step_output_ref,
    _step_result_attempt_indices,
    _wiki_carry_view,
    wiki_carry_path_text,
    wiki_carry_summary_text,
)
from brick_protocol.support.operator.walker_runtime_mail import (
    _runtime_concern_handoff_from_ledger,
    _runtime_handoff_unresolved_address,
    _step_output_address_escapes_ledger,
)
from brick_protocol.support.operator.walker_resume_seed import (
    ResumeSeed,
    _build_resume_disposition_observation,
    _has_pending_recorded_returns,
    _next_recorded_return,
    _replay_gate_record_requests_live_compute,
    _resume_observation_for_hold,
    _resume_observations_for_frontier,
    _stamp_resumed_lifecycle_on_held_source,
    _step_declares_gate_sequence_policy,
    replay_gate_compute_live_record,
)
from brick_protocol.support.operator.walker_report_events import (
    _brick_grain_gate_note,
    _brick_grain_next_work_kind,
    _brick_grain_step_context,
    _brick_grain_step_received_context,
    _brick_grain_work_kind_for_step_ref,
    _brick_grain_work_kind_from_step,
    _emit_brick_grain_completion_step_events,
    _emit_brick_received_step_event,
    _emit_building_event_best_effort,
    _emit_disposition_applied_event,
    _report_policy_uses_brick_grain,
    _report_repo_root_for_building_root,
)

@dataclasses.dataclass(frozen=True)
class NodeProcessingOutcome:
    """Support-only result for one dynamic-walker node execution."""

    step_result: BuildingRunSupportResult | None
    attempt_index: int
    gate_sequence_decision: GateSequenceDecision
    source_fact_body_carry_observation: Mapping[str, Any] | None
    report_events: tuple[Mapping[str, Any], ...]
    is_replay: bool
    recorded_gate_record: Any = None
    failure_reason: str = ""
    adapter_frontier: Mapping[str, Any] | None = None
    park_frontier: Mapping[str, Any] | None = None
    raised_exception: BaseException | None = None
    fan_in_hold_record: Mapping[str, Any] | None = None
    fan_dispatch_child_timeout_record: Mapping[str, Any] | None = None
    step_result_event: Mapping[str, Any] | None = None
    step_output_recorded: bool = True
    adapter_dispatch_timing: Mapping[str, Any] | None = None


_STEP_OUTPUT_HANDOFF_PROOF_LIMITS = (
    "support carry metadata only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)


_ADAPTER_USAGE_RAW_STREAM = "raw/adapter-usage.jsonl"
_DISPATCH_CHILD_TIMEOUT_RAW_STREAM = "raw/dispatch-child-timeout.jsonl"
_ADAPTER_TIMEOUT_JOIN_MARGIN_FLOOR_SECONDS = 30.0
_ADAPTER_TIMEOUT_JOIN_MARGIN_RATIO = 0.10


def _adapter_timeout_join_seconds(adapter_timeout_seconds: int) -> float:
    adapter_timeout = max(0.0, float(adapter_timeout_seconds))
    margin = max(
        _ADAPTER_TIMEOUT_JOIN_MARGIN_FLOOR_SECONDS,
        adapter_timeout * _ADAPTER_TIMEOUT_JOIN_MARGIN_RATIO,
    )
    return adapter_timeout + margin


class _DispatchChildTimeout(RuntimeError):
    """Support-only fan child timeout signal before an AgentFact can exist."""

    def __init__(
        self,
        *,
        prepared: Any,
        adapter_request: Any,
        adapter_error: Mapping[str, Any],
    ) -> None:
        super().__init__(
            "fan dispatch child did not return before adapter_timeout_seconds"
        )
        self.prepared = prepared
        self.adapter_request = adapter_request
        self.adapter_error = adapter_error


def _require_undisposed_concern_hold(resume_seed, hold_record, step_ref):
    """Fail loud for concern-style hold sites that are still mirror-unsupported.

    The main concern adoption path mirrors prior forward/reroute dispositions
    below. Sites that still call this helper intentionally remain loud instead
    of silently re-parking a previously-disposed hold.
    """
    if resume_seed is None:
        return
    previous = _resume_observation_for_hold(resume_seed, hold_record)
    if previous is not None:
        raise ValueError(
            "resume replay reached a previously-disposed concern-path HOLD "
            f"for {step_ref!r} with prior disposition "
            f"{previous.get('disposition_action')!r}; concern-path mirroring "
            "is not implemented in this slice — use a fresh re-issue or "
            "extend the mirror (t7b-replay-mirror-design-final-0706 D1.11)"
        )


def _previous_concern_hold_disposition(resume_seed, hold_record, step_ref):
    """Return a prior disposition for a re-reached concern-path hold.

    The caller has already built the prospective hold and consumed its
    adoption-sequence slot. A mirrored forward/reroute rolls that slot back so
    the replayed action reuses the sequence shape of the original resume.
    """
    if resume_seed is None:
        return "", ""
    previous = _resume_observation_for_hold(resume_seed, hold_record)
    if previous is None:
        return "", ""
    prior_action = str(previous.get("disposition_action") or "")
    if prior_action == "forward":
        return "forward", ""
    if prior_action == "reroute":
        target = str(previous.get("pending_target_ref") or "")
        if not target:
            raise ValueError(
                "resume replay cannot mirror a prior concern-path reroute "
                f"disposition for {step_ref!r}: the recorded observation "
                "carries no pending_target_ref"
            )
        return "reroute", target
    raise ValueError(
        "resume replay reached a previously-disposed concern-path HOLD "
        f"for {step_ref!r} with unsupported prior disposition "
        f"{prior_action!r}"
    )


def _adapter_dispatch_timing_record(
    *,
    building_id: str,
    step_ref: str,
    step_result: BuildingRunSupportResult,
    attempt_index: int,
    adapter_dispatch_timing: Mapping[str, Any],
    record_index: int,
) -> Mapping[str, Any]:
    adapter_result = step_result.adapter_result
    request = adapter_result.request
    raw_ref = f"raw:adapter-dispatch-timing:{step_ref}:attempt-{attempt_index}"
    recorded_at = _optional_text_value(
        adapter_dispatch_timing.get("dispatch_ended_at")
    ) or graph_ready_timestamp()
    return graph_ready_json_object(
        {
            "adapter_usage_ref": f"adapter-dispatch-timing:{step_ref}:attempt-{attempt_index}",
            "building_id": building_id,
            "step_ref": step_ref,
            "attempt_index": attempt_index,
            "adapter_ref": request.adapter_ref,
            "selected_model_ref": request.selected_model_ref,
            "usage_present": False,
            "usage": {
                "input_tokens": None,
                "output_tokens": None,
                "cache_read_input_tokens": None,
            },
            "reasoning_output_tokens": None,
            "raw_ref": raw_ref,
            "support_record_role": "adapter-dispatch-timing",
            "adapter_dispatch_timing": dict(adapter_dispatch_timing),
            "proof_limits": [
                "adapter dispatch timing support evidence only",
                "not Agent returned payload",
                "not AgentFact",
                "not Link field",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "provider internal execution phases",
                "network latency attribution",
                "semantic quality of returned work",
            ],
        },
        building_id=building_id,
        local_id=f"{_ADAPTER_USAGE_RAW_STREAM}#{record_index}",
        recorded_at=recorded_at,
        event_type="bp.raw.adapter_usage",
        subject=step_ref,
    )


def _jsonl_nonempty_line_count(path: Path) -> int:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return 0
    return sum(1 for line in data.splitlines() if line.strip())


def _append_jsonl_record(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    needs_separator = path.exists() and path.stat().st_size > 0
    with path.open("a+b") as handle:
        if needs_separator:
            handle.seek(0, os.SEEK_END)
            handle.seek(handle.tell() - 1)
            if handle.read(1) != b"\n":
                handle.write(b"\n")
        handle.write(encoded + b"\n")


def _prepared_timeout_exception_for_item(
    item: Mapping[str, Any],
    *,
    step: Mapping[str, Any],
    linear_plan: Mapping[str, Any],
    linear_steps: Sequence[Mapping[str, Any]],
    forward_order: Sequence[str],
    building_id: str,
    building_root: Path,
    repo_root_path: Path,
    adapter_timeout_seconds: int,
    checked_proof_limits: tuple[str, ...],
) -> _DispatchChildTimeout:
    from brick_protocol.support.operator.run import (
        _adapter_request_from_prepared,
        prepare_agent_run_from_step_rows,
    )

    step_ref = str(item["step_ref"])
    step_fixture = _step_fixture_from_plan_step(
        linear_plan,
        step,
        0,
        building_id=building_id,
        incoming_link_handoff_refs=_incoming_link_handoff_refs(
            linear_steps, forward_order.index(step_ref)
        )
        if step_ref in forward_order
        else {},
    )
    step_project_ref = project_ref_for_building_root(
        building_root,
        repo_root=repo_root_path,
    )
    if step_project_ref:
        step_fixture = dict(step_fixture)
        step_fixture["project_ref"] = step_project_ref
    prepared = prepare_agent_run_from_step_rows(
        step_fixture,
        proof_limits=checked_proof_limits,
    )
    adapter_request = _adapter_request_from_prepared(step_fixture, prepared)
    adapter_error = {
        "error_kind": "dispatch_child_timeout",
        "exception_type": "TimeoutError",
        "message_excerpt": (
            "fan dispatch child did not return before adapter_timeout_seconds"
        ),
        "adapter_timeout_seconds": adapter_timeout_seconds,
        "proof_limits": [
            "fan child timeout support evidence only",
            "not Agent returned payload",
            "not AgentFact",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "provider or command_runner behavior after the timeout observation",
            "semantic correctness of the unreturned child work",
            "caller/COO disposition after frontier observation",
        ],
    }
    return _DispatchChildTimeout(
        prepared=prepared,
        adapter_request=adapter_request,
        adapter_error=adapter_error,
    )


def _record_dispatch_child_timeout_evidence(
    *,
    building_root: Path,
    building_id: str,
    item: Mapping[str, Any],
    timeout_seconds: int,
) -> Mapping[str, Any]:
    raw_path = building_root / _DISPATCH_CHILD_TIMEOUT_RAW_STREAM
    record_index = _jsonl_nonempty_line_count(raw_path) + 1
    step_ref = str(item.get("step_ref", ""))
    record = graph_ready_json_object(
        {
            "raw_ref": f"raw:dispatch-child-timeout:{step_ref}:attempt-{record_index}",
            "support_record_role": "dispatch_child_timeout",
            "building_id": building_id,
            "step_ref": step_ref,
            "cascade_depth": int(item.get("cascade_depth", 0)),
            "adapter_timeout_seconds": timeout_seconds,
            "hold_reason": "fan_dispatch_child_unresponsive",
            "required_disposition_owner": "coo",
            "proof_limits": [
                "raw fan child timeout support evidence only",
                "not AgentFact",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "provider or command_runner behavior after the timeout observation",
                "semantic correctness of the unreturned child work",
            ],
        },
        building_id=building_id,
        local_id=f"{_DISPATCH_CHILD_TIMEOUT_RAW_STREAM}#{record_index}",
        recorded_at=graph_ready_timestamp(),
        event_type="bp.raw.dispatch_child_timeout",
        subject=step_ref,
    )
    _append_jsonl_record(raw_path, record)
    return record


def _dispatch_child_timeout_hold_record(
    *,
    building_id: str,
    completed_step_results: list[BuildingRunSupportResult],
    failed_preparation: Any,
    reroute_records: list[Mapping[str, Any]],
    node_budget: Mapping[str, int],
    cascade_depth: int,
    parent_reroute_ref: str,
) -> Mapping[str, Any]:
    step_ref = failed_preparation.step_rows.step_ref
    target_brick = failed_preparation.brick_instance_ref
    step_slug = step_ref.replace(":", "-")
    attempt_number = 1 + sum(
        1
        for result in completed_step_results
        if result.preparation.step_rows.step_ref == step_ref
    )
    return build_hold_record(
        reroute_ref=f"reroute-hold:{building_id}:dispatch-child-timeout:{step_slug}",
        adoption_sequence_number=len(reroute_records) + 1,
        cascade_depth=cascade_depth,
        parent_reroute_ref=parent_reroute_ref,
        source_step_ref=step_ref,
        source_brick_ref=target_brick,
        source_transition_concern_ref=f"observation:dispatch-child-timeout:{step_slug}",
        transition_concern_binding=False,
        immediate_target_ref=target_brick,
        target_brick=target_brick,
        pending_target_ref=target_brick,
        attempt_number=attempt_number,
        node_budget=int(node_budget.get(target_brick, 0)),
        budget_exhausted=False,
        disposition_required=True,
        hold_reason="fan_dispatch_child_unresponsive",
        required_disposition_owner="coo",
        transition_lifecycle_state="paused",
        proof_limits=list(PROOF_LIMITS),
        not_proven=list(RESUME_NOT_PROVEN),
    )


def _enrich_step_output_with_adapter_dispatch_timing(
    *,
    building_root: Path,
    step_ref: str,
    attempt_index: int,
    adapter_dispatch_timing: Mapping[str, Any],
    raw_ref: str,
) -> None:
    output_path = building_root / _step_output_manifest_ref(step_ref, attempt_index)
    try:
        packet = json.loads(output_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    if not isinstance(packet, dict):
        return
    packet["adapter_dispatch_timing"] = dict(adapter_dispatch_timing)
    evidence_refs = packet.get("evidence_refs")
    if isinstance(evidence_refs, dict):
        evidence_refs["adapter_dispatch_timing_raw_ref"] = raw_ref
    else:
        packet["evidence_refs"] = {"adapter_dispatch_timing_raw_ref": raw_ref}
    output_path.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _record_adapter_dispatch_timing_evidence(
    *,
    building_root: Path,
    building_id: str,
    step_ref: str,
    step_result: BuildingRunSupportResult,
    attempt_index: int,
    adapter_dispatch_timing: Mapping[str, Any] | None,
) -> None:
    if not adapter_dispatch_timing:
        return
    raw_path = building_root / _ADAPTER_USAGE_RAW_STREAM
    record = _adapter_dispatch_timing_record(
        building_id=building_id,
        step_ref=step_ref,
        step_result=step_result,
        attempt_index=attempt_index,
        adapter_dispatch_timing=adapter_dispatch_timing,
        record_index=_jsonl_nonempty_line_count(raw_path) + 1,
    )
    _append_jsonl_record(raw_path, record)
    raw_ref = _optional_text_value(record.get("raw_ref")) or ""
    _enrich_step_output_with_adapter_dispatch_timing(
        building_root=building_root,
        step_ref=step_ref,
        attempt_index=attempt_index,
        adapter_dispatch_timing=adapter_dispatch_timing,
        raw_ref=raw_ref,
    )


_FAN_IN_SOURCE_ADVISORY_STEP_TEMPLATE_REFS = frozenset(
    {
        "building-step-template:code-attack-qa",
        "building-step-template:axis-attack-qa",
        "building-step-template:evidence-integrity",
        "building-step-template:inspect",
    }
)


def _completed_step_output_refs_by_step(
    building_root: Path,
    step_results_snapshot: Sequence[BuildingRunSupportResult],
) -> Mapping[str, str]:
    """Return latest already-written step-output ref by completed step_ref."""

    attempts_by_step: dict[str, int] = {}
    refs_by_step: dict[str, str] = {}
    for result in step_results_snapshot:
        step_ref = result.preparation.step_rows.step_ref
        attempts_by_step[step_ref] = attempts_by_step.get(step_ref, 0) + 1
        output_ref = _step_output_manifest_ref(step_ref, attempts_by_step[step_ref])
        if (building_root / output_ref).is_file():
            refs_by_step[step_ref] = output_ref
    return refs_by_step


def _incoming_handoffs_with_completed_step_output_refs(
    handoff_refs: Mapping[str, Any],
    *,
    building_root: Path,
    repo_root: Path,
    building_id: str,
    step_results_snapshot: Sequence[BuildingRunSupportResult],
) -> Mapping[str, Any]:
    """Add support evidence addresses for completed upstream incoming steps."""

    incoming = handoff_refs.get("incoming")
    if not isinstance(incoming, list):
        return handoff_refs
    refs_by_step = _completed_step_output_refs_by_step(
        building_root,
        step_results_snapshot,
    )
    if not refs_by_step:
        return handoff_refs

    changed = False
    enriched_incoming: list[Any] = []
    building_root_ref = _repo_relative_building_root_ref(
        building_root,
        repo_root=repo_root,
        building_id=building_id,
    )
    for entry in incoming:
        if not isinstance(entry, Mapping):
            enriched_incoming.append(entry)
            continue
        from_step_ref = _optional_text_from_mapping(entry, "from_step_ref")
        output_ref = refs_by_step.get(from_step_ref or "")
        if not output_ref:
            enriched_incoming.append(entry)
            continue
        enriched_entry = dict(entry)
        enriched_entry["from_step_output_ref"] = output_ref
        if building_root_ref is not None:
            enriched_entry["building_root_ref"] = building_root_ref
        enriched_entry.setdefault("proof_limits", list(_STEP_OUTPUT_HANDOFF_PROOF_LIMITS))
        enriched_incoming.append(enriched_entry)
        changed = True
    if not changed:
        return handoff_refs

    enriched_handoffs = dict(handoff_refs)
    enriched_handoffs["incoming"] = enriched_incoming
    return enriched_handoffs


def _repo_relative_building_root_ref(
    building_root: Path,
    *,
    repo_root: Path,
    building_id: str,
) -> str | None:
    project_ref = project_ref_for_building_root(building_root, repo_root=repo_root)
    if not project_ref:
        return None
    prefix = "project:"
    if not project_ref.startswith(prefix):
        return None
    return f"project/{project_ref[len(prefix):]}/buildings/{building_id}"


def _fan_in_source_step_refs(
    fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
) -> frozenset[str]:
    """Return fan-in source step refs from declared topology."""

    return frozenset(
        source
        for sources in fan_in_sources_by_target.values()
        for source in sources
        if source
    )


def _step_declares_fan_in_source_advisory_concern(step: Mapping[str, Any]) -> bool:
    return (
        _optional_text_value(step.get("step_template_ref"))
        in _FAN_IN_SOURCE_ADVISORY_STEP_TEMPLATE_REFS
    )


def _source_lane_transition_concern_observation(
    *,
    step_ref: str,
    source_brick_ref: str,
    concern_observation: Any,
) -> Mapping[str, Any]:
    """Record fan-in source concern evidence without making it Movement input."""

    concern = getattr(concern_observation, "concern", None)
    invalid_reason = str(getattr(concern_observation, "invalid_reason", "") or "")
    raw_concern = getattr(concern_observation, "raw_concern", None)
    record: dict[str, Any] = {
        "kind": "fan_in_source_transition_concern_observation",
        "source_step_ref": step_ref,
        "source_brick_ref": source_brick_ref,
        "transition_concern_adoption": "advisory",
        "policy_scope": "fan_in_source",
        "adopted_as_movement": False,
        "proof_limits": [
            "source-lane Agent evidence observation only",
            "fan-in closure remains the Link-facing transition concern source",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of source-lane transition_concern_evidence",
        ],
    }
    if invalid_reason:
        record["concern_state"] = "malformed"
        record["invalid_reason"] = invalid_reason
        if isinstance(raw_concern, Mapping):
            record["observed_concern_keys"] = sorted(
                str(key) for key in raw_concern if isinstance(key, str)
            )
        return record
    if isinstance(concern, Mapping):
        record["concern_state"] = "valid"
        concern_ref = _optional_text_value(concern.get("concern_ref"))
        concern_kind = _optional_text_value(concern.get("concern_kind"))
        if concern_ref:
            record["concern_ref"] = concern_ref
        if concern_kind:
            record["concern_kind"] = concern_kind
        reason_refs = concern.get("reason_refs")
        if isinstance(reason_refs, list):
            record["reason_refs"] = [
                text for ref in reason_refs if (text := _optional_text_value(ref))
            ]
        related_refs = concern.get("related_boundary_refs")
        if isinstance(related_refs, list):
            record["related_boundary_refs"] = [
                text for ref in related_refs if (text := _optional_text_value(ref))
            ]
        return record
    record["concern_state"] = "absent"
    return record


def process_one_node(
    node_id: str,
    step: Mapping[str, Any],
    *,
    linear_plan: Mapping[str, Any],
    linear_steps: Sequence[Mapping[str, Any]],
    forward_order: Sequence[str],
    building_root: Path,
    building_id: str,
    plan_ref: str,
    task_source_ref: str,
    graph_context: Mapping[str, Any],
    declaration_plan: Mapping[str, Any],
    output_root: Path | str,
    overwrite_existing: bool,
    cascade_depth: int,
    parent_reroute_ref: str,
    runtime_handoffs: Sequence[Mapping[str, Any]],
    has_fan_groups: bool,
    fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
    cohort_skip_carry_forward: set[tuple[str, int]],
    brick_ref_by_step: Mapping[str, str],
    step_results_snapshot: list[BuildingRunSupportResult],
    step_result_events_snapshot: list[Mapping[str, Any]],
    resume_seed: "ResumeSeed | None",
    replay_consumed: dict[str, int],
    disposition_applied: bool,
    reroute_records: list[Mapping[str, Any]],
    node_budget: Mapping[str, int],
    node_landings: Mapping[str, int],
    fan_in_wait_all_observations: list[Mapping[str, Any]],
    local_callables: Mapping[str, AgentBrainCallable] | None,
    command_runner: CommandRunner | None,
    adapter_cwd: Path | str | None,
    adapter_timeout_seconds: int,
    checked_proof_limits: tuple[str, ...],
    run_step: Callable[..., BuildingRunSupportResult],
    record_step_output: Callable[..., BuildingRunSupportResult],
    write_adapter_error_frontier: Callable[..., Any],
    write_chat_session_park_frontier: Callable[..., Any],
    chat_session_park_frontier_exception,
    adapter_frontier_exception,
    report_event_policy: Mapping[str, Any] | None,
    repo_root_path: Path,
    report_env: Mapping[str, str] | None,
    report_slack_sender: Any | None,
    record_step_output_immediately: bool = True,
    defer_frontier_writes: bool = False,
) -> NodeProcessingOutcome:
    """Process one node without mutating queue/reroute scheduling state."""

    step_ref = node_id
    index = len(step_results_snapshot)
    step_fixture = _step_fixture_from_plan_step(
        linear_plan,
        step,
        index,
        building_id=building_id,
        incoming_link_handoff_refs=_incoming_link_handoff_refs(
            linear_steps, forward_order.index(step_ref)
        )
        if step_ref in forward_order
        else {},
    )
    # CHARTER-INJECT (0618): stamp the vessel project_ref onto the step packet
    # from the building_root PATH (the canonical inverse seam). A building under
    # project/<id>/buildings/ -> 'project:<id>'; a default-root / legacy / tmp
    # building -> None (loudly nothing). _adapter_request_from_prepared reads
    # this to inject that project's README charter into every role's packet.
    step_project_ref = project_ref_for_building_root(building_root, repo_root=repo_root_path)
    if step_project_ref:
        step_fixture = dict(step_fixture)
        step_fixture["project_ref"] = step_project_ref
    # MAIL-REPAIR (0611) -- the ONE assembler widening: a redo step scheduled
    # by an ADOPTED runtime reroute carries the eligible runtime rows' mail
    # (B3: the gate-adopted concern + this resume's disposition row) into its
    # handoff packet as ADDRESSES with recorded provenance. Items without
    # runtime mail (the whole declared path) take the EXACT prior branch --
    # the declared-refs mailbox stays byte-identical (regression guard).
    if runtime_handoffs:
        widened_handoff_refs = dict(step_fixture.get("link_handoff_refs") or {})
        widened_handoff_refs.setdefault(
            "target_brick_instance_ref", brick_ref_by_step[step_ref]
        )
        widened_handoff_refs["runtime_handoffs"] = [
            dict(entry) for entry in runtime_handoffs
        ]
        step_fixture = dict(step_fixture)
        step_fixture["link_handoff_refs"] = widened_handoff_refs
    current_handoff_refs = step_fixture.get("link_handoff_refs") or {}
    enriched_handoff_refs = _incoming_handoffs_with_completed_step_output_refs(
        current_handoff_refs,
        building_root=building_root,
        repo_root=repo_root_path,
        building_id=building_id,
        step_results_snapshot=step_results_snapshot,
    )
    if enriched_handoff_refs is not current_handoff_refs:
        step_fixture = dict(step_fixture)
        step_fixture["link_handoff_refs"] = enriched_handoff_refs
    source_fact_body_carry = _source_fact_body_carry_for_step(
        building_root=building_root,
        building_id=building_id,
        target_step_ref=step_ref,
        cascade_depth=cascade_depth,
        step=step,
        step_results=step_results_snapshot,
        step_result_events=step_result_events_snapshot,
        fan_in_sources_by_target=fan_in_sources_by_target,
        cohort_skip_carry_forward=cohort_skip_carry_forward,
    )
    source_fact_body_carry_observation = source_fact_body_carry["observation"]
    if source_fact_body_carry["source_fact_bodies"]:
        step_fixture = dict(step_fixture)
        step_fixture["source_fact_bodies"] = dict(
            source_fact_body_carry["source_fact_bodies"]
        )
    if source_fact_body_carry_observation is not None and source_fact_body_carry_observation.get("body_absent"):
        missing = source_fact_body_carry_observation.get(
            "missing_source_fact_refs",
            [],
        )
        if has_fan_groups and step_ref in fan_in_sources_by_target:
            return NodeProcessingOutcome(
                step_result=None,
                attempt_index=0,
                gate_sequence_decision=GateSequenceDecision(),
                source_fact_body_carry_observation=source_fact_body_carry_observation,
                report_events=(),
                is_replay=False,
                fan_in_hold_record=_build_fan_in_wait_all_hold(
                    building_id=building_id,
                    plan_ref=plan_ref,
                    target_step_ref=step_ref,
                    target_brick=brick_ref_by_step[step_ref],
                    cascade_depth=cascade_depth,
                    observation=_fan_in_observation_from_carry_observation(
                        source_fact_body_carry_observation,
                        required_sources=fan_in_sources_by_target.get(step_ref, ()),
                    ),
                    step_results=step_results_snapshot,
                ),
            )
        raise ValueError(
            "missing step-output source_fact body/evidence: "
            + ", ".join(str(item) for item in missing)
        )
    # RESUME replay-or-live decision: if resume seeded a recorded return for
    # this step occurrence, REPLAY it (no provider call); otherwise run LIVE.
    # The k-th visit to step_ref consumes the k-th recorded return (realized
    # order). A replayed step READS its recorded AT-TIME gate decision back;
    # a live step computes it (forward parity). Default (no seed) => live.
    recorded_return, recorded_gate_record, recorded_at, is_replay = _next_recorded_return(
        resume_seed, step_ref, replay_consumed
    )
    # ④ RE-INSTRUCTION stamp: when the human/COO disposition carried a corrected
    # how-to, stamp it onto the LIVE retried target's step packet so the redo
    # prompt delivers it as its own labeled section. Gated on (a) a live run
    # (NOT a replay -- a replayed pre-HOLD occurrence replays its recorded return
    # and never builds a prompt, so it must NEVER carry the correction; risk #6),
    # and (b) this occurrence being the disposition's pending_target_ref (the
    # redo landing / re-adopted held node -- the retried target; risk #5). This
    # is INDEPENDENT of the disposition_reason_refs address truck, so a correction
    # rides even when the disposition carries no reason_refs. The fixture is
    # copied before mutation so the shared plan step is untouched.
    if (
        not is_replay
        and resume_seed is not None
        and resume_seed.re_instruction
        and brick_ref_by_step.get(step_ref) == resume_seed.pending_target_ref
    ):
        step_fixture = dict(step_fixture)
        step_fixture["re_instruction"] = resume_seed.re_instruction
    pre_step_report_events: tuple[Mapping[str, Any], ...] = ()
    if not is_replay:
        pre_step_report_events = _emit_brick_received_step_event(
            report_event_policy,
            linear_plan=linear_plan,
            building_id=building_id,
            building_root=building_root,
            repo_root=repo_root_path,
            current_brick_ref=brick_ref_by_step[step_ref],
            step_ref=step_ref,
            step_index=index + 1,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
            overwrite_existing=overwrite_existing,
        )
    adapter_dispatch_timing: Mapping[str, Any] | None = None
    try:
        if is_replay:
            # gap-6: preserve the ORIGINAL recorded_at through the replay path
            # (evidence fidelity) instead of stamping a fresh timestamp.
            step_result = resume_seed.replay_step(  # type: ignore[union-attr]
                step_fixture,
                returned_value=recorded_return,
                recorded_at=recorded_at,
                gate_sequence_decision_record=recorded_gate_record,
                proof_limits=checked_proof_limits,
            )
        else:
            dispatch_started_at = graph_ready_timestamp()
            dispatch_started_perf = time.perf_counter()
            step_result = run_step(
                step_fixture,
                local_callables=local_callables,
                command_runner=command_runner,
                adapter_cwd=adapter_cwd,
                adapter_timeout_seconds=adapter_timeout_seconds,
                proof_limits=checked_proof_limits,
            )
            dispatch_ended_at = graph_ready_timestamp()
            adapter_dispatch_timing = {
                "dispatch_started_at": dispatch_started_at,
                "dispatch_ended_at": dispatch_ended_at,
                "duration_ms": round(
                    max(0.0, time.perf_counter() - dispatch_started_perf) * 1000,
                    3,
                ),
                "timing_source": "support/operator/walker_kernel.py:process_one_node",
                "timing_scope": "adapter_dispatch",
            }
    except Exception as exc:  # noqa: BLE001 - distinguish adapter frontier below
        if getattr(exc, "parked", None) is not None:
            if defer_frontier_writes:
                return NodeProcessingOutcome(
                    step_result=None,
                    attempt_index=0,
                    gate_sequence_decision=GateSequenceDecision(),
                    source_fact_body_carry_observation=source_fact_body_carry_observation,
                    report_events=pre_step_report_events,
                    is_replay=is_replay,
                    failure_reason="chat_session_park_frontier_deferred",
                    raised_exception=exc,
                    step_output_recorded=True,
                )
            evidence_write = _write_dynamic_chat_session_park_frontier(
                exc,
                building_id=building_id,
                plan_ref=plan_ref,
                linear_plan=linear_plan,
                completed_step_results=step_results_snapshot,
                output_root=output_root,
                overwrite_existing=overwrite_existing or bool(step_results_snapshot),
                checked_proof_limits=checked_proof_limits,
                graph_context=graph_context,
                reroute_records=reroute_records,
                node_budget=node_budget,
                node_landings=node_landings,
                held=False,
                hold_record=None,
                cascade_depth=cascade_depth,
                parent_reroute_ref=parent_reroute_ref,
                fan_in_wait_all_observations=fan_in_wait_all_observations,
                has_fan_groups=has_fan_groups,
                write_chat_session_park_frontier=write_chat_session_park_frontier,
                declaration_plan=declaration_plan,
                resume_observations=_resume_observations_for_frontier(
                    resume_seed,
                    disposition_applied=disposition_applied,
                    node_budget=node_budget,
                    node_landings=node_landings,
                ),
            )
            if report_event_policy:
                terminal_event_kind = building_event_kind_from_frontier(
                    evidence_write.lifecycle_write.root,
                    repo_root=repo_root_path,
                )
                _emit_building_event_best_effort(
                    report_event_policy,
                    event_kind=terminal_event_kind,
                    building_id=building_id,
                    building_root=evidence_write.lifecycle_write.root,
                    repo_root=repo_root_path,
                    report_env=report_env,
                    report_slack_sender=report_slack_sender,
                    overwrite_existing=overwrite_existing,
                )
            raise chat_session_park_frontier_exception(
                "chat-session park frontier evidence written before AgentFact returned",
                building_id=building_id,
                building_root=evidence_write.lifecycle_write.root,
                written_files=evidence_write.written_files,
            ) from exc
        if defer_frontier_writes:
            return NodeProcessingOutcome(
                step_result=None,
                attempt_index=0,
                gate_sequence_decision=GateSequenceDecision(),
                source_fact_body_carry_observation=source_fact_body_carry_observation,
                report_events=pre_step_report_events,
                is_replay=is_replay,
                failure_reason="adapter_error_frontier_deferred",
                raised_exception=exc,
                step_output_recorded=True,
            )
        _write_dynamic_adapter_error_frontier(
            exc,
            building_id=building_id,
            plan_ref=plan_ref,
            linear_plan=linear_plan,
            completed_step_results=step_results_snapshot,
            output_root=output_root,
            overwrite_existing=overwrite_existing or bool(step_results_snapshot),
            checked_proof_limits=checked_proof_limits,
            graph_context=graph_context,
            reroute_records=reroute_records,
            node_budget=node_budget,
            node_landings=node_landings,
            held=False,
            hold_record=None,
            cascade_depth=cascade_depth,
            parent_reroute_ref=parent_reroute_ref,
            fan_in_wait_all_observations=fan_in_wait_all_observations,
            has_fan_groups=has_fan_groups,
            write_adapter_error_frontier=write_adapter_error_frontier,
            adapter_frontier_exception=adapter_frontier_exception,
            declaration_plan=declaration_plan,
            resume_observations=_resume_observations_for_frontier(
                resume_seed,
                disposition_applied=disposition_applied,
                node_budget=node_budget,
                node_landings=node_landings,
            ),
        )
        raise AssertionError("unreachable after dynamic adapter frontier write")
    # E1 (U5.5 slice-3) + RESUME-GATE-RECORD -- DYNAMIC-WALKER parity with run.py.
    # Compute the live gate-sequence disposition and attach it to the step result
    # BEFORE the step-output write so the AT-TIME step-output.json persists the
    # gate_sequence_decision_record (which resume reads back without recompute).
    # This is a PURE computation over the already-completed step_result + step; it
    # does NOT depend on the step-output file. The loop control below reads
    # gate_sequence_decision exactly as before -- hold / reroute / fan-in / next /
    # break behaviour is unchanged, and the field survives the only later mutation
    # of an existing step_results entry (_inject_hold_paused_link /
    # _inject_fan_in_paused_link via _step_result_with_paused_lifecycle uses a
    # partial dataclasses.replace). Recording carry only.
    # On a REPLAYED step the gate decision was already RECONSTRUCTED from the
    # recorded AT-TIME record by replay_step (read-back, no recompute); keep it.
    # A no-policy replayed step has gate_sequence_decision None -- normalize to a
    # no-action GateSequenceDecision so the loop control reads it like the
    # forward walk's run_gate_sequence_policy() no-policy result.
    if is_replay:
        if _replay_gate_record_requests_live_compute(recorded_gate_record):
            gate_sequence_decision = run_gate_sequence_policy(
                step=step,
                step_result=step_result,
                source_brick_ref=brick_ref_by_step[step_ref],
                target_brick_ref=step_result.preparation.next_brick_instance_ref,
            )
            step_result = dataclasses.replace(
                step_result, gate_sequence_decision=gate_sequence_decision
            )
        # FAIL-CLOSED gap-5: a replayed step that DECLARED a non-empty
        # gate_sequence_policy MUST have a recorded gate decision to read back.
        # If it is absent (None) the policy's AT-TIME decision was lost, and
        # normalizing to a no-action GateSequenceDecision() would SILENTLY treat
        # a policy step as no-policy (divergence: a recorded HOLD/forward gate
        # decision would vanish). Raise instead -- only a genuinely no-policy
        # step legitimately has a None recorded decision.
        elif (
            step_result.gate_sequence_decision is None
            and _step_declares_gate_sequence_policy(step)
        ):
            raise ValueError(
                f"resume corrupt evidence: replayed step {step_ref!r} declares a "
                "gate_sequence_policy but its step-output carries NO recorded gate "
                "decision to read back; refusing to silently treat a policy step as "
                "no-action (would drop the recorded gate decision and diverge)"
            )
        else:
            gate_sequence_decision = (
                step_result.gate_sequence_decision
                if step_result.gate_sequence_decision is not None
                else GateSequenceDecision()
            )
    else:
        gate_sequence_decision = run_gate_sequence_policy(
            step=step,
            step_result=step_result,
            source_brick_ref=brick_ref_by_step[step_ref],
            target_brick_ref=step_result.preparation.next_brick_instance_ref,
        )
        step_result = dataclasses.replace(
            step_result, gate_sequence_decision=gate_sequence_decision
        )
    if record_step_output_immediately:
        attempt_index = 1 + sum(
            1
            for completed in step_results_snapshot
            if completed.preparation.step_rows.step_ref == step_ref
        )
        step_result = record_step_output(
            building_root=building_root,
            building_id=building_id,
            step_result=step_result,
            completed_step_results=step_results_snapshot,
            proof_limits=checked_proof_limits,
            task_source_ref=task_source_ref,
            overwrite_existing=overwrite_existing,
        )
        _record_adapter_dispatch_timing_evidence(
            building_root=building_root,
            building_id=building_id,
            step_ref=step_ref,
            step_result=step_result,
            attempt_index=attempt_index,
            adapter_dispatch_timing=adapter_dispatch_timing,
        )
        report_events = pre_step_report_events + tuple(
            _emit_brick_grain_completion_step_events(
                report_event_policy,
                linear_plan=linear_plan,
                building_id=building_id,
                building_root=building_root,
                repo_root=repo_root_path,
                step_result=step_result,
                step_index=len(step_results_snapshot) + 1,
                attempt_index=attempt_index,
                gate_sequence_decision=gate_sequence_decision,
                report_env=report_env,
                report_slack_sender=report_slack_sender,
                overwrite_existing=overwrite_existing,
            )
        )
    else:
        attempt_index = 0
        report_events = pre_step_report_events
    return NodeProcessingOutcome(
        step_result=step_result,
        attempt_index=attempt_index,
        gate_sequence_decision=gate_sequence_decision,
        source_fact_body_carry_observation=source_fact_body_carry_observation,
        report_events=report_events,
        is_replay=is_replay,
        recorded_gate_record=recorded_gate_record,
        step_result_event={
            "step_ref": step_ref,
            "cascade_depth": cascade_depth,
        },
        step_output_recorded=record_step_output_immediately,
        adapter_dispatch_timing=adapter_dispatch_timing,
    )


def _run_dynamic_graph_walker(
    plan: Mapping[str, Any],
    *,
    output_root: Path | str,
    overwrite_existing: bool,
    local_callables: Mapping[str, AgentBrainCallable] | None,
    command_runner: CommandRunner | None,
    adapter_cwd: Path | str | None,
    adapter_timeout_seconds: int,
    checked_proof_limits: tuple[str, ...],
    run_step,
    record_step_output,
    write_accumulated,
    write_adapter_error_frontier,
    write_chat_session_park_frontier,
    chat_session_park_frontier_exception,
    adapter_frontier_exception=None,
    repo_root: Path | str = _REPO_ROOT,
    resume_seed: "ResumeSeed | None" = None,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
) -> BuildingPlanSupportResult:
    """Walk a declared graph plan with runtime, gate-adopted, budgeted reroute.

    ``run_step`` is the existing step executor
    (``_run_building_step_without_writing``); ``write_accumulated`` is the
    existing accumulated-evidence writer. They are injected by ``run.py`` so this
    module reuses the exact same step + writer surfaces as the linear walker (no
    duplicate execution path, no new BAL fact class).

    ``resume_seed`` is the OPTIONAL seeded-initial-state used ONLY by the resume
    verb (``walker_resume._resume_dynamic_graph_walker``). When ``None`` (the
    default) the walk runs from scratch, byte-for-byte as before -- the forward
    path is unchanged. When present the SAME loop runs but REPLAYS the recorded
    Agent returns for already-completed steps (no provider call), applies the
    human/COO disposition at the held step occurrence, and continues with full
    forward fidelity. See ``ResumeSeed``.
    """

    if _optional_text_from_mapping(plan, "plan_shape") != "graph":
        raise ValueError("walker_mode='dynamic' requires a plan_shape: graph Building Plan")
    repo_root_path = Path(repo_root).resolve()

    # FORWARD path reuses the existing graph -> execution_order linearization.
    # LIVE RUN ADMISSION is STRICT about write grants (require_write_need_marker,
    # parity with run.py's linear admission): a brick row carrying write_scope
    # must EXPLICITLY declare its write NEED (requires_brick_write_scope: true).
    # The resume verb delegates back into this same loop, so a resumed walk is
    # re-admitted under the same strict gate.
    linear_plan, graph_context = _linear_plan_from_graph_plan(plan)
    validate_declared_building_plan(
        linear_plan,
        repo_root=repo_root_path,
        require_write_need_marker=True,
    )

    plan_ref = _optional_text_from_mapping(linear_plan, "plan_ref") or "building-plan:anonymous"
    building_id = _plan_building_id(linear_plan, plan_ref)
    building_root = _preflight_step_output_building_root(
        output_root,
        building_id,
        overwrite_existing=overwrite_existing,
    )
    task_source_ref = _task_source_ref_from_plan(linear_plan)
    if overwrite_existing:
        _clear_overwrite_claim_trace_manifest(building_root)
    _materialize_initial_declaration_evidence(
        building_root,
        building_id=building_id,
        plan_ref=plan_ref,
        plan=linear_plan,
        declaration_plan=plan,
        graph_context=graph_context,
        task_source_ref=task_source_ref,
        proof_limits=checked_proof_limits,
    )

    linear_steps = linear_plan["steps"]
    if not isinstance(linear_steps, list) or not linear_steps:
        raise ValueError("graph Building Plan projected to an empty steps list")
    steps_by_ref: dict[str, Mapping[str, Any]] = {}
    forward_order: list[str] = []
    for step in linear_steps:
        step_ref = _optional_text_from_mapping(step, "step_ref")
        if not step_ref:
            raise ValueError("projected graph step missing step_ref")
        steps_by_ref[step_ref] = step
        forward_order.append(step_ref)
    brick_ref_by_step = {
        step_ref: _brick_instance_ref_from_linear_step(step)
        for step_ref, step in steps_by_ref.items()
    }
    step_ref_by_brick = {brick: step for step, brick in brick_ref_by_step.items()}
    report_event_policy = report_event_policy_from_plan(linear_plan)
    report_event_observations: list[Mapping[str, Any]] = []
    # On RESUME the building already started; do NOT re-emit building_started (the
    # forward walk emits it once at first run). Only the terminal event is emitted
    # below after the resumed walk reaches completion / the next HOLD.
    if resume_seed is None:
        started_event = _emit_building_event_best_effort(
            report_event_policy,
            event_kind="building_started",
            building_id=building_id,
            building_root=building_root,
            current_brick_ref=brick_ref_by_step.get(forward_order[0], ""),
            repo_root=repo_root_path,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
            overwrite_existing=overwrite_existing,
        )
        if started_event is not None:
            report_event_observations.append(started_event)
    has_fan_groups = _graph_has_fan_groups(graph_context)
    fan_successors_by_source = (
        _graph_successor_step_refs_by_source_step_ref(graph_context)
        if has_fan_groups
        else {}
    )
    fan_in_sources_by_target = (
        _graph_fan_in_sources_by_target_step_ref(graph_context)
        if has_fan_groups
        else {}
    )
    fan_in_source_steps = _fan_in_source_step_refs(fan_in_sources_by_target)

    # Per-TARGET-node budget (Link-assigned, keyed by target Brick node ref,
    # SHARED across all reroute-landings on that node). Source = the Link-owned
    # node_reroute_budgets map declared on the graph plan. Each value is the
    # number of reroute-landings admitted on that node before HOLD.
    node_budget = _node_reroute_budgets(plan, declared_bricks=set(step_ref_by_brick))
    # RESUME raise disposition: the human/COO raised the held node's budget by a
    # declared budget_increment. The forward loop then adopts the held landing
    # naturally on the bigger budget -- raise is just "more budget" (verified:
    # byte-identical to a fresh forward walk with the bumped budget). The default
    # (forward) path has an empty budget_delta, so node_budget is unchanged.
    if resume_seed is not None:
        for target_brick, delta in resume_seed.budget_delta.items():
            if delta:
                node_budget[target_brick] = node_budget.get(target_brick, 0) + int(delta)
    # Live per-node consumed counter; consumed once per ADOPTED reroute-landing.
    node_landings: dict[str, int] = {brick: 0 for brick in node_budget}

    # The mutable attempt sequence (the live queue). Serial graphs keep the exact
    # execution_order seed. Fan graphs seed root node(s) and let completed nodes
    # splice declared successors into the live queue.
    if has_fan_groups:
        root_order = _graph_root_step_refs(forward_order, graph_context)
        initial_attempt_queue: list[dict[str, Any]] = [
            {
                "step_ref": step_ref,
                "cascade_depth": 0,
                "parent_reroute_ref": "",
                "is_reroute_landing": False,
            }
            for step_ref in root_order
        ]
        initial_scheduled_fan_steps: set[tuple[str, int]] = {
            (step_ref, 0) for step_ref in root_order
        }
    else:
        initial_attempt_queue = [
            {"step_ref": step_ref, "cascade_depth": 0, "parent_reroute_ref": "", "is_reroute_landing": False}
            for step_ref in forward_order
        ]
        initial_scheduled_fan_steps = set()
    frontier_driver = _FrontierDriver(
        initial_attempt_queue,
        scheduled_fan_steps=initial_scheduled_fan_steps,
    )

    step_results: list[BuildingRunSupportResult] = []
    reroute_records: list[Mapping[str, Any]] = []
    fan_in_wait_all_observations: list[Mapping[str, Any]] = []
    fan_in_cohort_records: list[Mapping[str, Any]] = []
    source_lane_transition_concern_observations: list[Mapping[str, Any]] = []
    source_fact_body_carry_observations: list[Mapping[str, Any]] = []
    adoption_sequence_number = 0
    hold_record: Mapping[str, Any] | None = None
    fan_in_hold_record: Mapping[str, Any] | None = None
    completed_fan_steps: set[tuple[str, int]] = set()
    running_fan_steps: set[tuple[str, int]] = set()
    held_fan_steps: set[tuple[str, int]] = set()
    fan_in_deferrals: dict[tuple[str, int], int] = {}
    # (skipped_source_step_ref, reroute_cascade_depth) pairs for HUMAN-vouched
    # (sibling_independence) cohort siblings whose PRIOR pass carries forward.
    cohort_skip_carry_forward: set[tuple[str, int]] = set()
    step_result_events: list[Mapping[str, Any]] = []
    # RESUME replay state (no-op when resume_seed is None). Per step_ref FIFO
    # cursor over the recorded returns: the k-th loop visit to step_ref REPLAYS
    # the k-th recorded return; once exhausted the step runs LIVE (a continued /
    # post-HOLD step). disposition_applied flips once the held step occurrence has
    # been resolved by the disposition (so a later genuine HOLD is a real HOLD).
    replay_consumed: dict[str, int] = {}
    disposition_applied = False
    # FAIL-CLOSED gap-3: the EXACT step_results index of the held occurrence,
    # captured when the disposition is applied, so the resumed-lifecycle stamp lands
    # on the held occurrence (not a later same-step_ref occurrence a raise re-adopts).
    held_occurrence_index: int | None = None
    resume_body_carry_observations: list[Mapping[str, Any]] = []
    dispatch_pool_size = _fanout_dispatch_pool_size(linear_plan)
    if not has_fan_groups:
        dispatch_pool_size = 1
    elif not _has_explicit_fanout_pool_override(linear_plan):
        # A drawn fan IS the parallel declaration -> run concurrent by default.
        # HOLD-safe (joins batch-terminal) + record stays canonical (FIFO drain).
        # Explicit override above still wins. Resume replays to the current HOLD
        # serially, then recovers this declared pool for the live continuation.
        dispatch_pool_size = _FANOUT_AUTO_POOL
    pending_outcomes: list[tuple[dict[str, Any], NodeProcessingOutcome]] = []

    def _active_dispatch_pool_size() -> int:
        # Resume rehydrates completed evidence deterministically up to the current
        # held occurrence. Once the disposition has been applied, remaining work
        # is live continuation and should preserve the declared fan-out behavior.
        if resume_seed is not None and not disposition_applied:
            return 1
        return dispatch_pool_size

    def _process_item(
        item: dict[str, Any],
        *,
        record_step_output_immediately: bool,
        defer_frontier_writes: bool = False,
    ) -> NodeProcessingOutcome:
        step_ref = str(item["step_ref"])
        cascade_depth = int(item.get("cascade_depth", 0))
        return process_one_node(
            step_ref,
            steps_by_ref[step_ref],
            linear_plan=linear_plan,
            linear_steps=linear_steps,
            forward_order=forward_order,
            building_root=building_root,
            building_id=building_id,
            plan_ref=plan_ref,
            task_source_ref=task_source_ref,
            graph_context=graph_context,
            declaration_plan=plan,
            output_root=output_root,
            overwrite_existing=overwrite_existing,
            cascade_depth=cascade_depth,
            parent_reroute_ref=item["parent_reroute_ref"],
            runtime_handoffs=item.get("runtime_handoffs") or (),
            has_fan_groups=has_fan_groups,
            fan_in_sources_by_target=fan_in_sources_by_target,
            cohort_skip_carry_forward=cohort_skip_carry_forward,
            brick_ref_by_step=brick_ref_by_step,
            step_results_snapshot=step_results,
            step_result_events_snapshot=step_result_events,
            resume_seed=resume_seed,
            replay_consumed=replay_consumed,
            disposition_applied=disposition_applied,
            reroute_records=reroute_records,
            node_budget=node_budget,
            node_landings=node_landings,
            fan_in_wait_all_observations=fan_in_wait_all_observations,
            local_callables=local_callables,
            command_runner=command_runner,
            adapter_cwd=adapter_cwd,
            adapter_timeout_seconds=adapter_timeout_seconds,
            checked_proof_limits=checked_proof_limits,
            run_step=run_step,
            record_step_output=record_step_output,
            write_adapter_error_frontier=write_adapter_error_frontier,
            write_chat_session_park_frontier=write_chat_session_park_frontier,
            chat_session_park_frontier_exception=chat_session_park_frontier_exception,
            adapter_frontier_exception=adapter_frontier_exception,
            report_event_policy=report_event_policy,
            repo_root_path=repo_root_path,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
            record_step_output_immediately=record_step_output_immediately,
            defer_frontier_writes=defer_frontier_writes,
        )

    def _clear_running(items: Sequence[Mapping[str, Any]]) -> None:
        for item in items:
            running_fan_steps.discard(
                (str(item.get("step_ref", "")), int(item.get("cascade_depth", 0)))
            )

    def _dispatch_ready_batch(
        items: Sequence[dict[str, Any]],
        *,
        pool_size: int,
    ) -> list[tuple[dict[str, Any], NodeProcessingOutcome]]:
        try:
            if len(items) == 1:
                single_item = items[0]
                executor = ThreadPoolExecutor(max_workers=1)
                try:
                    future = executor.submit(
                        _process_item,
                        single_item,
                        record_step_output_immediately=False,
                        defer_frontier_writes=True,
                    )
                    try:
                        return [
                            (
                                single_item,
                                future.result(
                                    timeout=_adapter_timeout_join_seconds(
                                        adapter_timeout_seconds
                                    )
                                ),
                            )
                        ]
                    except FutureTimeoutError:
                        timeout_record = _record_dispatch_child_timeout_evidence(
                            building_root=building_root,
                            building_id=building_id,
                            item=single_item,
                            timeout_seconds=adapter_timeout_seconds,
                        )
                        future.cancel()
                        timeout_exc = _prepared_timeout_exception_for_item(
                            single_item,
                            step=steps_by_ref[str(single_item["step_ref"])],
                            linear_plan=linear_plan,
                            linear_steps=linear_steps,
                            forward_order=forward_order,
                            building_id=building_id,
                            building_root=building_root,
                            repo_root_path=repo_root_path,
                            adapter_timeout_seconds=adapter_timeout_seconds,
                            checked_proof_limits=checked_proof_limits,
                        )
                        return [
                            (
                                single_item,
                                NodeProcessingOutcome(
                                    step_result=None,
                                    attempt_index=0,
                                    gate_sequence_decision=GateSequenceDecision(),
                                    source_fact_body_carry_observation=None,
                                    report_events=(),
                                    is_replay=False,
                                    failure_reason="dispatch_child_timeout_deferred",
                                    raised_exception=timeout_exc,
                                    step_output_recorded=True,
                                    fan_dispatch_child_timeout_record=timeout_record,
                                ),
                            )
                        ]
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            worker_count = min(pool_size, len(items))
            executor = ThreadPoolExecutor(max_workers=worker_count)
            try:
                futures = [
                    (
                        item,
                        executor.submit(
                            _process_item,
                            item,
                            record_step_output_immediately=False,
                            defer_frontier_writes=True,
                        ),
                    )
                    for item in items
                ]
                outcomes: list[tuple[dict[str, Any], NodeProcessingOutcome]] = []
                for item, future in futures:
                    try:
                        outcomes.append(
                            (
                                item,
                                future.result(
                                    timeout=_adapter_timeout_join_seconds(
                                        adapter_timeout_seconds
                                    )
                                ),
                            )
                        )
                    except FutureTimeoutError:
                        timeout_record = _record_dispatch_child_timeout_evidence(
                            building_root=building_root,
                            building_id=building_id,
                            item=item,
                            timeout_seconds=adapter_timeout_seconds,
                        )
                        future.cancel()
                        timeout_exc = _prepared_timeout_exception_for_item(
                            item,
                            step=steps_by_ref[str(item["step_ref"])],
                            linear_plan=linear_plan,
                            linear_steps=linear_steps,
                            forward_order=forward_order,
                            building_id=building_id,
                            building_root=building_root,
                            repo_root_path=repo_root_path,
                            adapter_timeout_seconds=adapter_timeout_seconds,
                            checked_proof_limits=checked_proof_limits,
                        )
                        outcomes.append(
                            (
                                item,
                                NodeProcessingOutcome(
                                    step_result=None,
                                    attempt_index=0,
                                    gate_sequence_decision=GateSequenceDecision(),
                                    source_fact_body_carry_observation=None,
                                    report_events=(),
                                    is_replay=False,
                                    failure_reason="dispatch_child_timeout_deferred",
                                    raised_exception=timeout_exc,
                                    step_output_recorded=True,
                                    fan_dispatch_child_timeout_record=timeout_record,
                                ),
                            )
                        )
                        break
                return outcomes
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
        finally:
            _clear_running(items)

    def _record_deferred_step_output(
        item: dict[str, Any],
        outcome: NodeProcessingOutcome,
    ) -> NodeProcessingOutcome:
        if outcome.step_output_recorded:
            return outcome
        if outcome.step_result is None:
            return outcome
        step_ref = str(item["step_ref"])
        attempt_index = 1 + sum(
            1
            for completed in step_results
            if completed.preparation.step_rows.step_ref == step_ref
        )
        step_result = record_step_output(
            building_root=building_root,
            building_id=building_id,
            step_result=outcome.step_result,
            completed_step_results=step_results,
            proof_limits=checked_proof_limits,
            task_source_ref=task_source_ref,
            overwrite_existing=overwrite_existing,
        )
        _record_adapter_dispatch_timing_evidence(
            building_root=building_root,
            building_id=building_id,
            step_ref=step_ref,
            step_result=step_result,
            attempt_index=attempt_index,
            adapter_dispatch_timing=outcome.adapter_dispatch_timing,
        )
        report_events = outcome.report_events + tuple(
            _emit_brick_grain_completion_step_events(
                report_event_policy,
                linear_plan=linear_plan,
                building_id=building_id,
                building_root=building_root,
                repo_root=repo_root_path,
                step_result=step_result,
                step_index=len(step_results) + 1,
                attempt_index=attempt_index,
                gate_sequence_decision=outcome.gate_sequence_decision,
                report_env=report_env,
                report_slack_sender=report_slack_sender,
                overwrite_existing=overwrite_existing,
            )
        )
        return dataclasses.replace(
            outcome,
            step_result=step_result,
            attempt_index=attempt_index,
            report_events=report_events,
            step_output_recorded=True,
        )

    def _append_recorded_sibling_outcome(
        item: dict[str, Any],
        outcome: NodeProcessingOutcome,
    ) -> None:
        nonlocal fan_in_hold_record
        if outcome.source_fact_body_carry_observation is not None:
            source_fact_body_carry_observations.append(
                outcome.source_fact_body_carry_observation
            )
        if outcome.fan_in_hold_record is not None:
            fan_in_hold_record = outcome.fan_in_hold_record
            return
        if outcome.raised_exception is not None:
            return
        if outcome.step_result is None or outcome.step_result_event is None:
            raise AssertionError("process_one_node returned no step result")
        step_ref = str(item["step_ref"])
        cascade_depth = int(item.get("cascade_depth", 0))
        step_results.append(outcome.step_result)
        step_result_events.append(outcome.step_result_event)
        report_event_observations.extend(outcome.report_events)
        if has_fan_groups:
            completed_fan_steps.add((step_ref, cascade_depth))

    def _drain_pending_outcomes_before_terminal() -> None:
        while pending_outcomes:
            pending_item, pending_outcome = pending_outcomes.pop(0)
            pending_outcome = _record_deferred_step_output(
                pending_item,
                pending_outcome,
            )
            if pending_outcome.raised_exception is not None:
                pending_outcomes.insert(0, (pending_item, pending_outcome))
                return
            _append_recorded_sibling_outcome(pending_item, pending_outcome)

    def _write_deferred_frontier(
        item: dict[str, Any],
        outcome: NodeProcessingOutcome,
    ) -> None:
        exc = outcome.raised_exception
        if exc is None:
            return
        if getattr(exc, "parked", None) is not None:
            evidence_write = _write_dynamic_chat_session_park_frontier(
                exc,
                building_id=building_id,
                plan_ref=plan_ref,
                linear_plan=linear_plan,
                completed_step_results=step_results,
                output_root=output_root,
                overwrite_existing=overwrite_existing or bool(step_results),
                checked_proof_limits=checked_proof_limits,
                graph_context=graph_context,
                reroute_records=reroute_records,
                node_budget=node_budget,
                node_landings=node_landings,
                held=False,
                hold_record=None,
                cascade_depth=int(item.get("cascade_depth", 0)),
                parent_reroute_ref=item["parent_reroute_ref"],
                fan_in_wait_all_observations=fan_in_wait_all_observations,
                has_fan_groups=has_fan_groups,
                write_chat_session_park_frontier=write_chat_session_park_frontier,
                declaration_plan=plan,
                resume_observations=_resume_observations_for_frontier(
                    resume_seed,
                    disposition_applied=disposition_applied,
                    node_budget=node_budget,
                    node_landings=node_landings,
                ),
            )
            if report_event_policy:
                terminal_event_kind = building_event_kind_from_frontier(
                    evidence_write.lifecycle_write.root,
                    repo_root=repo_root_path,
                )
                _emit_building_event_best_effort(
                    report_event_policy,
                    event_kind=terminal_event_kind,
                    building_id=building_id,
                    building_root=evidence_write.lifecycle_write.root,
                    repo_root=repo_root_path,
                    report_env=report_env,
                    report_slack_sender=report_slack_sender,
                    overwrite_existing=overwrite_existing,
                )
            raise chat_session_park_frontier_exception(
                "chat-session park frontier evidence written before AgentFact returned",
                building_id=building_id,
                building_root=evidence_write.lifecycle_write.root,
                written_files=evidence_write.written_files,
            ) from exc
        _write_dynamic_adapter_error_frontier(
            exc,
            building_id=building_id,
            plan_ref=plan_ref,
            linear_plan=linear_plan,
            completed_step_results=step_results,
            output_root=output_root,
            overwrite_existing=overwrite_existing or bool(step_results),
            checked_proof_limits=checked_proof_limits,
            graph_context=graph_context,
            reroute_records=reroute_records,
            node_budget=node_budget,
            node_landings=node_landings,
            held=outcome.fan_dispatch_child_timeout_record is not None,
            hold_record=(
                _dispatch_child_timeout_hold_record(
                    building_id=building_id,
                    completed_step_results=step_results,
                    failed_preparation=exc.prepared,
                    reroute_records=reroute_records,
                    node_budget=node_budget,
                    cascade_depth=int(item.get("cascade_depth", 0)),
                    parent_reroute_ref=item["parent_reroute_ref"],
                )
                if outcome.fan_dispatch_child_timeout_record is not None
                and hasattr(exc, "prepared")
                else None
            ),
            cascade_depth=int(item.get("cascade_depth", 0)),
            parent_reroute_ref=item["parent_reroute_ref"],
            fan_in_wait_all_observations=fan_in_wait_all_observations,
            has_fan_groups=has_fan_groups,
            write_adapter_error_frontier=write_adapter_error_frontier,
            adapter_frontier_exception=adapter_frontier_exception,
            declaration_plan=plan,
            resume_observations=_resume_observations_for_frontier(
                resume_seed,
                disposition_applied=disposition_applied,
                node_budget=node_budget,
                node_landings=node_landings,
            ),
        )
        raise AssertionError("unreachable after dynamic adapter frontier write")

    while True:
        if pending_outcomes:
            item, outcome = pending_outcomes.pop(0)
            outcome = _record_deferred_step_output(item, outcome)
        else:
            active_dispatch_pool_size = _active_dispatch_pool_size()
            if active_dispatch_pool_size > 1:
                ready_result = frontier_driver.ready_items(
                    max_items=active_dispatch_pool_size,
                    has_fan_groups=has_fan_groups,
                    fan_in_sources_by_target=fan_in_sources_by_target,
                    completed_fan_steps=completed_fan_steps,
                    running_fan_steps=running_fan_steps,
                    held_fan_steps=held_fan_steps,
                    fan_in_deferrals=fan_in_deferrals,
                )
                if ready_result.hold_item is not None:
                    hold_step_ref = str(ready_result.hold_item["step_ref"])
                    hold_cascade_depth = int(
                        ready_result.hold_item.get("cascade_depth", 0)
                    )
                    if ready_result.hold_observation is not None:
                        fan_in_wait_all_observations.append(
                            ready_result.hold_observation
                        )
                    fan_in_hold_record = _build_fan_in_wait_all_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        target_step_ref=hold_step_ref,
                        target_brick=brick_ref_by_step[hold_step_ref],
                        cascade_depth=hold_cascade_depth,
                        observation=ready_result.hold_observation or {},
                        step_results=step_results,
                    )
                    _drain_pending_outcomes_before_terminal()
                    break
                if not ready_result.items:
                    break
                pending_outcomes.extend(
                    _dispatch_ready_batch(
                        ready_result.items,
                        pool_size=active_dispatch_pool_size,
                    )
                )
                continue

            item = frontier_driver.next_item()
            if item is None:
                break
            step_ref = str(item["step_ref"])
            cascade_depth = int(item.get("cascade_depth", 0))
            if has_fan_groups:
                wait_state, wait_observation = _fan_in_wait_all_state(
                    step_ref=step_ref,
                    cascade_depth=cascade_depth,
                    fan_in_sources_by_target=fan_in_sources_by_target,
                    completed_fan_steps=completed_fan_steps,
                    running_fan_steps=running_fan_steps,
                    held_fan_steps=held_fan_steps,
                    pending_queue=frontier_driver.pending_items(),
                    fan_in_deferrals=fan_in_deferrals,
                )
                if wait_observation is not None and wait_state == "hold":
                    fan_in_wait_all_observations.append(wait_observation)
                if wait_state == "defer":
                    frontier_driver.defer(item)
                    continue
                if wait_state == "hold":
                    fan_in_hold_record = _build_fan_in_wait_all_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        target_step_ref=step_ref,
                        target_brick=brick_ref_by_step[step_ref],
                        cascade_depth=cascade_depth,
                        observation=wait_observation or {},
                        step_results=step_results,
                    )
                    _drain_pending_outcomes_before_terminal()
                    break
                running_fan_steps.add((step_ref, cascade_depth))
            try:
                outcome = _process_item(
                    item,
                    record_step_output_immediately=True,
                )
            finally:
                if has_fan_groups:
                    running_fan_steps.discard((step_ref, cascade_depth))

        step_ref = str(item["step_ref"])
        cascade_depth = int(item.get("cascade_depth", 0))
        step = steps_by_ref[step_ref]
        # MAIL-REPAIR (0611, B3 lane 2): the resume disposition row's mail entry,
        # set ONLY in this iteration's disposition hook (raise lane) and consumed
        # ONLY by this iteration's adoption (the held landing re-adoption).
        # Iteration-local so it can never leak onto a later unrelated adoption.
        disposition_runtime_handoff: dict[str, Any] | None = None
        if outcome.source_fact_body_carry_observation is not None:
            source_fact_body_carry_observations.append(
                outcome.source_fact_body_carry_observation
            )
        if outcome.fan_in_hold_record is not None:
            fan_in_hold_record = outcome.fan_in_hold_record
            _drain_pending_outcomes_before_terminal()
            break
        if outcome.raised_exception is not None:
            _drain_pending_outcomes_before_terminal()
            _write_deferred_frontier(item, outcome)
        if outcome.step_result is None or outcome.step_result_event is None:
            raise AssertionError("process_one_node returned no step result")
        step_result = outcome.step_result
        gate_sequence_decision = outcome.gate_sequence_decision
        report_event_observations.extend(outcome.report_events)
        step_results.append(step_result)
        step_result_events.append(outcome.step_result_event)
        if has_fan_groups:
            completed_fan_steps.add((step_ref, cascade_depth))
        human_disposition_reroute_target = ""
        replaying_prior_reroute_mirror = False
        replaying_prior_concern_reroute_mirror = False
        # RESUME disposition application at the held step occurrence. The held step
        # is the LAST recorded step (the original walk broke there); on replay this
        # is the occurrence that just exhausted its recorded returns at the held
        # (step_ref, cascade_depth) identity. raise was already applied as a budget
        # bump (the landing adopts naturally below). reroute carries a human-selected
        # target into the existing adoption path. forward => WALK ON past the held
        # concern/gate (treat as no actionable reroute). stop => close.
        if (
            resume_seed is not None
            and not disposition_applied
            and step_ref == resume_seed.held_source_step_ref
            and cascade_depth == resume_seed.held_cascade_depth
            and not _has_pending_recorded_returns(resume_seed, step_ref, replay_consumed)
        ):
            disposition_applied = True
            # gap-3: the held occurrence is the step_result just appended above.
            held_occurrence_index = len(step_results) - 1
            disposition_event = _emit_disposition_applied_event(
                report_event_policy,
                building_id=building_id,
                building_root=building_root,
                repo_root=repo_root_path,
                current_brick_ref=brick_ref_by_step[step_ref],
                resume_seed=resume_seed,
                report_env=report_env,
                report_slack_sender=report_slack_sender,
                overwrite_existing=overwrite_existing,
            )
            if disposition_event is not None:
                report_event_observations.append(disposition_event)
            if resume_seed.disposition_action == "stop":
                # Human/COO ended the building at the held gate. Replace the held
                # source's Link row with a resumed->closed lifecycle and stop.
                step_results = _stamp_resumed_lifecycle_on_held_source(
                    step_results,
                    resume_seed=resume_seed,
                    disposition_action="stop",
                    building_id=building_id,
                    replay_step=resume_seed.replay_step,
                    checked_proof_limits=checked_proof_limits,
                    held_occurrence_index=held_occurrence_index,
                )
                _drain_pending_outcomes_before_terminal()
                break
            if resume_seed.disposition_action == "forward":
                # Walk ON past the held gate without a reroute landing: splice the
                # held step's declared successors (fan graph) or fall through to the
                # next queued step (serial), exactly like the kernel's no-actionable-
                # concern walk-on. The held concern/gate is NOT re-evaluated here.
                if has_fan_groups:
                    frontier_driver.splice_declared_successors_after_current(
                        source_step_ref=step_ref,
                        cascade_depth=cascade_depth,
                        parent_reroute_ref=item["parent_reroute_ref"],
                        successors_by_source=fan_successors_by_source,
                    )
                continue
            if resume_seed.disposition_action == "reroute":
                # Human/COO selected a declared non-source Brick node while resolving
                # this HOLD. The resume seed carries the already-validated target; the
                # concern adoption block below reuses the existing reroute landing /
                # replay machinery instead of introducing a second reroute engine.
                human_disposition_reroute_target = resume_seed.pending_target_ref
                if gate_sequence_decision.action == "hold":
                    gate_sequence_decision = GateSequenceDecision(
                        action="reroute",
                        gate_ref=gate_sequence_decision.gate_ref,
                        target_brick_ref=human_disposition_reroute_target,
                        hold_reason=gate_sequence_decision.hold_reason,
                        evidence_ref=resume_seed.paused_at_ref,
                        reason_refs=(
                            resume_seed.disposition_reason_refs
                            or gate_sequence_decision.reason_refs
                        ),
                        gate_results=gate_sequence_decision.gate_results,
                        gate_action_sequence=gate_sequence_decision.gate_action_sequence,
                    )
            # raise: fall through to the normal branches; the bumped budget lets the
            # held landing ADOPT below (no special-casing needed).
            # MAIL-REPAIR (0611, B3 lane 2): THIS resume's disposition row is a
            # truck-eligible runtime row -- when the human/COO disposition carries
            # reason_refs, those ADDRESSES ride to the re-adopted redo landing in
            # the same iteration. The row was READ FROM the ledger (raw/link.jsonl
            # via walker_resume._read_disposition_row) and its step-output-form
            # addresses were B1-checked fail-closed at seed build. Data only.
            if resume_seed.disposition_reason_refs:
                disposition_runtime_handoff = {
                    "from_step_ref": step_ref,
                    "from_brick_instance_ref": brick_ref_by_step[step_ref],
                    "row_kind": "resume_disposition",
                    "row_ref": (
                        "transition-lifecycle:resumed:"
                        + resume_seed.pending_target_ref
                    ),
                    "reason_refs": list(resume_seed.disposition_reason_refs),
                    "provenance": {
                        "runtime_row_ref": resume_seed.paused_at_ref,
                        "row_kind": "resume_disposition",
                        "recorded_in": "raw/link.jsonl",
                        "author_ref": resume_seed.author_ref,
                        # FIX 3 (0611): the SPECIFIC selected row, not just the
                        # file -- hold identity + row raw_ref + 1-based index
                        # among same-hold rows (file order; selected = last),
                        # so replaying the selection rule lands on this row.
                        **resume_seed.disposition_row_provenance,
                    },
                }
        if gate_sequence_decision.action == "hold":
            target_brick = (
                gate_sequence_decision.pending_target_ref
                or step_result.preparation.next_brick_instance_ref
            )
            adoption_sequence_number += 1
            prospective_hold = _build_hold(
                building_id=building_id,
                plan_ref=plan_ref,
                source_step_ref=step_ref,
                source_brick_ref=brick_ref_by_step[step_ref],
                target_brick=target_brick,
                concern={"concern_ref": gate_sequence_decision.evidence_ref},
                cascade_depth=item["cascade_depth"],
                parent_reroute_ref=item["parent_reroute_ref"],
                adoption_sequence_number=adoption_sequence_number,
                node_budget=node_budget.get(target_brick, 0),
                attempt_number=node_landings.get(target_brick, 0),
                budget_exhausted=False,
                hold_reason=gate_sequence_decision.hold_reason
                or "gate_sequence_policy_hold",
                required_disposition_owner=(
                    gate_sequence_decision.required_disposition_owner
                    or "caller-or-coo"
                ),
                step=step,
                step_result=step_result,
            )
            previous_disposition = _resume_observation_for_hold(
                resume_seed,
                prospective_hold,
            )
            if previous_disposition is not None:
                prior_action = str(
                    previous_disposition.get("disposition_action") or ""
                )
                if prior_action == "forward":
                    # Mirror a prior human/COO forward: walk on exactly as the
                    # original resume did. The prospective-hold increment above
                    # is rolled back — the original live forward (mode-1)
                    # consumed no adoption sequence number, so a replayed
                    # forward must not skew later hold/reroute identities
                    # across generations (generation parity, walker_hold
                    # identity contract).
                    adoption_sequence_number -= 1
                    if has_fan_groups:
                        frontier_driver.splice_declared_successors_after_current(
                            source_step_ref=step_ref,
                            cascade_depth=cascade_depth,
                            parent_reroute_ref=item["parent_reroute_ref"],
                            successors_by_source=fan_successors_by_source,
                        )
                    continue
                if prior_action != "reroute":
                    raise ValueError(
                        "resume replay encountered an already-disposed recorded HOLD "
                        f"for {step_ref!r} with unsupported prior disposition "
                        f"{prior_action!r}"
                    )
                mirrored_target = str(
                    previous_disposition.get("pending_target_ref") or ""
                )
                if not mirrored_target:
                    raise ValueError(
                        "resume replay cannot mirror a prior reroute disposition "
                        f"for {step_ref!r}: the recorded observation carries no "
                        "pending_target_ref"
                    )
                # Mirror a prior human/COO reroute through the SAME adoption
                # machinery the live disposition uses (decision mutation ->
                # the reroute branch below): one implementation replays splice,
                # adoption record, and landings bookkeeping. Sequence REUSE:
                # the prospective-hold increment above is rolled back and the
                # adoption branch re-increments, so the mirrored adoption lands
                # on the same adoption_sequence_number (and therefore the same
                # reroute_ref string) the original adoption consumed.
                adoption_sequence_number -= 1
                replaying_prior_reroute_mirror = True
                human_disposition_reroute_target = mirrored_target
                gate_sequence_decision = GateSequenceDecision(
                    action="reroute",
                    gate_ref=gate_sequence_decision.gate_ref,
                    target_brick_ref=mirrored_target,
                    hold_reason=gate_sequence_decision.hold_reason,
                    evidence_ref=(
                        str(previous_disposition.get("paused_at_ref") or "")
                        or gate_sequence_decision.evidence_ref
                    ),
                    reason_refs=gate_sequence_decision.reason_refs,
                    gate_results=gate_sequence_decision.gate_results,
                    gate_action_sequence=gate_sequence_decision.gate_action_sequence,
                )
                # No hold is persisted and no report is re-emitted for a
                # mirrored disposition; control falls through to the reroute
                # adoption branch below.
            else:
                hold_record = prospective_hold
                reroute_records.append(hold_record)
                _drain_pending_outcomes_before_terminal()
                if has_fan_groups:
                    held_fan_steps.add((step_ref, cascade_depth))
                    fan_in_wait_all_observations.extend(
                        _fan_in_wait_all_observations_for_held_source(
                            held_source_step_ref=step_ref,
                            cascade_depth=cascade_depth,
                            fan_in_sources_by_target=fan_in_sources_by_target,
                            completed_fan_steps=completed_fan_steps,
                            held_fan_steps=held_fan_steps,
                        )
                    )
                break
        if gate_sequence_decision.action == "reroute":
            target_brick = gate_sequence_decision.target_brick_ref
            budget = node_budget.get(target_brick)
            if budget is None or node_landings.get(target_brick, 0) >= budget:
                if replaying_prior_reroute_mirror:
                    # Under generation parity a mirrored adoption replays a
                    # landing the original walk already afforded; exhaustion
                    # here means the replayed state diverged — fail loud, never
                    # park a silent hold on a mirror (t7b design edge case 7).
                    raise ValueError(
                        "resume replay mirror hit an unbudgeted/exhausted "
                        f"target {target_brick!r} for {step_ref!r}; mirrored "
                        "adoptions must replay within the originally afforded "
                        "budget (generation parity violated)"
                    )
                adoption_sequence_number += 1
                hold_record = _build_hold(
                    building_id=building_id,
                    plan_ref=plan_ref,
                    source_step_ref=step_ref,
                    source_brick_ref=brick_ref_by_step[step_ref],
                    target_brick=target_brick,
                    concern={"concern_ref": gate_sequence_decision.evidence_ref},
                    cascade_depth=item["cascade_depth"],
                    parent_reroute_ref=item["parent_reroute_ref"],
                    adoption_sequence_number=adoption_sequence_number,
                    node_budget=budget or 0,
                    attempt_number=node_landings.get(target_brick, 0),
                    budget_exhausted=True,
                    hold_reason=(
                        "gate_sequence_reroute_target_unbudgeted"
                        if budget is None
                        else "gate_sequence_reroute_budget_exhausted"
                    ),
                    step=step,
                    step_result=step_result,
                )
                _require_undisposed_concern_hold(resume_seed, hold_record, step_ref)
                reroute_records.append(hold_record)
                _drain_pending_outcomes_before_terminal()
                if has_fan_groups:
                    held_fan_steps.add((step_ref, cascade_depth))
                    fan_in_wait_all_observations.extend(
                        _fan_in_wait_all_observations_for_held_source(
                            held_source_step_ref=step_ref,
                            cascade_depth=cascade_depth,
                            fan_in_sources_by_target=fan_in_sources_by_target,
                            completed_fan_steps=completed_fan_steps,
                            held_fan_steps=held_fan_steps,
                        )
                    )
                break
            node_landings[target_brick] = node_landings.get(target_brick, 0) + 1
            adoption_sequence_number += 1
            attempt_number = node_landings[target_brick]
            target_step_ref = step_ref_by_brick[target_brick]
            reroute_ref = (
                f"reroute-adoption:{building_id}:{adoption_sequence_number:02d}:"
                f"{target_brick.replace(':', '-')}"
            )
            reroute_cascade_depth = item["cascade_depth"] + 1
            frontier_driver.splice_after_current(
                [
                    {
                        "step_ref": target_step_ref,
                        "cascade_depth": reroute_cascade_depth,
                        "parent_reroute_ref": reroute_ref,
                        "is_reroute_landing": True,
                    }
                ]
            )
            reroute_records.append(
                build_reroute_adoption_record(
                    reroute_ref=reroute_ref,
                    adoption_sequence_number=adoption_sequence_number,
                    cascade_depth=reroute_cascade_depth,
                    parent_reroute_ref=item["parent_reroute_ref"],
                    source_step_ref=step_ref,
                    source_brick_ref=brick_ref_by_step[step_ref],
                    source_transition_concern_ref=gate_sequence_decision.evidence_ref,
                    transition_concern_binding=False,
                    adopted_by="link-policy:gate-sequence",
                    immediate_target_ref=target_brick,
                    target_brick=target_brick,
                    target_step_ref=target_step_ref,
                    replay_segment_refs=[],
                    attempt_number=attempt_number,
                    node_budget=budget,
                    budget_exhausted=False,
                    disposition_required=False,
                    carry_budget_evidence_ref=_carry_budget_evidence_ref(
                        building_id,
                        target_brick,
                    ),
                    proof_limits=list(PROOF_LIMITS),
                    not_proven=list(NOT_PROVEN),
                    structured_field_observation=_structured_field_observation_for_step(
                        step, step_result
                    ),
                )
            )
            continue

        # ζ7: inspect the Agent return for a NON-BINDING reroute proposal.
        concern_observation = _transition_concern_observation_from_step_result(step_result)
        concern_is_from_fan_in_source = (
            step_ref in fan_in_source_steps
            and _step_declares_fan_in_source_advisory_concern(step)
            and not human_disposition_reroute_target
        )
        if concern_is_from_fan_in_source and (
            concern_observation.invalid_reason or concern_observation.concern is not None
        ):
            source_lane_transition_concern_observations.append(
                _source_lane_transition_concern_observation(
                    step_ref=step_ref,
                    source_brick_ref=brick_ref_by_step[step_ref],
                    concern_observation=concern_observation,
                )
            )
            concern = None
            adopted_reroute = False
            target_classification = None
            human_disposition_adopted_by = ""
            if not has_fan_groups:
                continue
            reroute_insert_width = 0
            if has_fan_groups and not adopted_reroute:
                frontier_driver.splice_declared_successors_after_current(
                    source_step_ref=step_ref,
                    cascade_depth=cascade_depth,
                    parent_reroute_ref=item["parent_reroute_ref"],
                    successors_by_source=fan_successors_by_source,
                    offset=reroute_insert_width,
                )
            continue
        if concern_observation.invalid_reason:
            adoption_sequence_number += 1
            hold_record = _build_invalid_transition_concern_hold(
                building_id=building_id,
                plan_ref=plan_ref,
                source_step_ref=step_ref,
                source_brick_ref=brick_ref_by_step[step_ref],
                concern_observation=concern_observation,
                declared_bricks=set(step_ref_by_brick),
                cascade_depth=item["cascade_depth"],
                parent_reroute_ref=item["parent_reroute_ref"],
                adoption_sequence_number=adoption_sequence_number,
                node_budget=node_budget,
                node_landings=node_landings,
                step=step,
                step_result=step_result,
            )
            reroute_records.append(hold_record)
            _drain_pending_outcomes_before_terminal()
            if has_fan_groups:
                held_fan_steps.add((step_ref, cascade_depth))
                fan_in_wait_all_observations.extend(
                    _fan_in_wait_all_observations_for_held_source(
                        held_source_step_ref=step_ref,
                        cascade_depth=cascade_depth,
                        fan_in_sources_by_target=fan_in_sources_by_target,
                        completed_fan_steps=completed_fan_steps,
                        held_fan_steps=held_fan_steps,
                    )
                )
            break
        concern = concern_observation.concern
        adopted_reroute = False
        target_classification = (
            _classify_reroute_target(
                concern,
                declared_bricks=set(step_ref_by_brick),
                source_brick_ref=brick_ref_by_step[step_ref],
            )
            if concern is not None
            else None
        )
        human_disposition_adopted_by = ""
        if human_disposition_reroute_target:
            target_classification = _RerouteTargetClassification(
                kind="single",
                target=human_disposition_reroute_target,
                resolved=(human_disposition_reroute_target,),
            )
            human_disposition_adopted_by = "link-policy:human-disposition"
        if target_classification is not None and target_classification.kind in (
            "ambiguous",
            "none",
        ) and not (
            concern is not None
            and plan.get("transition_concern_adoption") == "advisory"
            and not human_disposition_reroute_target
        ):
            hold_target = brick_ref_by_step[step_ref]
            hold_reason = target_classification.hold_reason or (
                "multiple_reroute_addresses_no_single_owner"
                if target_classification.kind == "ambiguous"
                else "no_resolving_reroute_address"
            )
            adoption_sequence_number += 1
            prospective_hold = _build_hold(
                building_id=building_id,
                plan_ref=plan_ref,
                source_step_ref=step_ref,
                source_brick_ref=brick_ref_by_step[step_ref],
                target_brick=hold_target,
                concern=concern,
                cascade_depth=item["cascade_depth"],
                parent_reroute_ref=item["parent_reroute_ref"],
                adoption_sequence_number=adoption_sequence_number,
                node_budget=0,
                attempt_number=0,
                budget_exhausted=False,
                hold_reason=hold_reason,
                step=step,
                step_result=step_result,
            )
            prior_action, prior_target = _previous_concern_hold_disposition(
                resume_seed,
                prospective_hold,
                step_ref,
            )
            if prior_action == "forward":
                adoption_sequence_number -= 1
                if has_fan_groups:
                    frontier_driver.splice_declared_successors_after_current(
                        source_step_ref=step_ref,
                        cascade_depth=cascade_depth,
                        parent_reroute_ref=item["parent_reroute_ref"],
                        successors_by_source=fan_successors_by_source,
                    )
                continue
            if prior_action == "reroute":
                adoption_sequence_number -= 1
                replaying_prior_concern_reroute_mirror = True
                target_classification = _RerouteTargetClassification(
                    kind="single",
                    target=prior_target,
                    resolved=(prior_target,),
                )
                human_disposition_adopted_by = "link-policy:human-disposition"
            else:
                hold_record = prospective_hold
                reroute_records.append(hold_record)
                _drain_pending_outcomes_before_terminal()
                if has_fan_groups:
                    held_fan_steps.add((step_ref, cascade_depth))
                    fan_in_wait_all_observations.extend(
                        _fan_in_wait_all_observations_for_held_source(
                            held_source_step_ref=step_ref,
                            cascade_depth=cascade_depth,
                            fan_in_sources_by_target=fan_in_sources_by_target,
                            completed_fan_steps=completed_fan_steps,
                            held_fan_steps=held_fan_steps,
                        )
                    )
                break
        # WALK ON (carry forward to closure, no HOLD, no reroute landing) when
        # there is NO concern, the plan declares concerns advisory, OR the concern
        # is an EXPLICIT non-reroute concern: either building-boundary: sentinels
        # name no Brick node, or the only resolved Brick node is the source node
        # itself. That is not an actionable reroute, so it must NOT HOLD.
        # BUDGET-FREE: node_landings / node_budget untouched.
        if (concern is None and not human_disposition_reroute_target) or (
            concern is not None
            and plan.get("transition_concern_adoption") == "advisory"
            and not human_disposition_reroute_target
        ) or (
            target_classification is not None
            and target_classification.kind == "non_reroute"
            and not human_disposition_reroute_target
        ):
            if not has_fan_groups:
                continue
            reroute_insert_width = 0
        else:
            if target_classification.kind in ("ambiguous", "none"):
                raise AssertionError("unreachable after concern hold mirror pre-check")
            else:
                target_brick = target_classification.target
                gate = _gate_disposition_for_step(step)
                if gate == "pause":
                    # human:/coo: gate on the reroute -> PAUSE (transition_lifecycle paused).
                    adoption_sequence_number += 1
                    prospective_hold = _build_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        source_step_ref=step_ref,
                        source_brick_ref=brick_ref_by_step[step_ref],
                        target_brick=target_brick,
                        concern=concern,
                        cascade_depth=item["cascade_depth"],
                        parent_reroute_ref=item["parent_reroute_ref"],
                        adoption_sequence_number=adoption_sequence_number,
                        node_budget=node_budget.get(target_brick, 0),
                        attempt_number=node_landings.get(target_brick, 0),
                        budget_exhausted=False,
                        hold_reason="human_or_coo_gate_pause",
                        step=step,
                        step_result=step_result,
                    )
                    prior_action, prior_target = _previous_concern_hold_disposition(
                        resume_seed,
                        prospective_hold,
                        step_ref,
                    )
                    if prior_action == "forward":
                        adoption_sequence_number -= 1
                        if has_fan_groups:
                            frontier_driver.splice_declared_successors_after_current(
                                source_step_ref=step_ref,
                                cascade_depth=cascade_depth,
                                parent_reroute_ref=item["parent_reroute_ref"],
                                successors_by_source=fan_successors_by_source,
                            )
                        continue
                    if prior_action == "reroute":
                        adoption_sequence_number -= 1
                        replaying_prior_concern_reroute_mirror = True
                        target_brick = prior_target
                        gate = ""
                        human_disposition_adopted_by = "link-policy:human-disposition"
                    else:
                        hold_record = prospective_hold
                        reroute_records.append(hold_record)
                        _drain_pending_outcomes_before_terminal()
                        if has_fan_groups:
                            held_fan_steps.add((step_ref, cascade_depth))
                            fan_in_wait_all_observations.extend(
                                _fan_in_wait_all_observations_for_held_source(
                                    held_source_step_ref=step_ref,
                                    cascade_depth=cascade_depth,
                                    fan_in_sources_by_target=fan_in_sources_by_target,
                                    completed_fan_steps=completed_fan_steps,
                                    held_fan_steps=held_fan_steps,
                                )
                            )
                        break

                # Default/template gate -> auto-adopt IF the target node budget is available.
                budget = node_budget.get(target_brick)
                if budget is None:
                    # A reroute target with no Link-assigned budget cannot be adopted; the
                    # bound depends on every target having a finite budget. HOLD.
                    adoption_sequence_number += 1
                    prospective_hold = _build_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        source_step_ref=step_ref,
                        source_brick_ref=brick_ref_by_step[step_ref],
                        target_brick=target_brick,
                        concern=concern,
                        cascade_depth=item["cascade_depth"],
                        parent_reroute_ref=item["parent_reroute_ref"],
                        adoption_sequence_number=adoption_sequence_number,
                        node_budget=0,
                        attempt_number=0,
                        budget_exhausted=True,
                        hold_reason="target_node_has_no_link_assigned_budget",
                        step=step,
                        step_result=step_result,
                    )
                    prior_action, prior_target = _previous_concern_hold_disposition(
                        resume_seed,
                        prospective_hold,
                        step_ref,
                    )
                    if prior_action == "forward":
                        adoption_sequence_number -= 1
                        if has_fan_groups:
                            frontier_driver.splice_declared_successors_after_current(
                                source_step_ref=step_ref,
                                cascade_depth=cascade_depth,
                                parent_reroute_ref=item["parent_reroute_ref"],
                                successors_by_source=fan_successors_by_source,
                            )
                        continue
                    if prior_action == "reroute":
                        adoption_sequence_number -= 1
                        replaying_prior_concern_reroute_mirror = True
                        target_brick = prior_target
                        budget = node_budget.get(target_brick)
                        human_disposition_adopted_by = "link-policy:human-disposition"
                    if budget is None:
                        hold_record = prospective_hold
                        reroute_records.append(hold_record)
                        _drain_pending_outcomes_before_terminal()
                        if has_fan_groups:
                            held_fan_steps.add((step_ref, cascade_depth))
                            fan_in_wait_all_observations.extend(
                                _fan_in_wait_all_observations_for_held_source(
                                    held_source_step_ref=step_ref,
                                    cascade_depth=cascade_depth,
                                    fan_in_sources_by_target=fan_in_sources_by_target,
                                    completed_fan_steps=completed_fan_steps,
                                    held_fan_steps=held_fan_steps,
                                )
                            )
                        break

                if node_landings[target_brick] >= budget:
                    # Budget EXHAUSTED -> the next reroute landing is NOT adopted. HOLD.
                    adoption_sequence_number += 1
                    prospective_hold = _build_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        source_step_ref=step_ref,
                        source_brick_ref=brick_ref_by_step[step_ref],
                        target_brick=target_brick,
                        concern=concern,
                        cascade_depth=item["cascade_depth"],
                        parent_reroute_ref=item["parent_reroute_ref"],
                        adoption_sequence_number=adoption_sequence_number,
                        node_budget=budget,
                        attempt_number=node_landings[target_brick],
                        budget_exhausted=True,
                        hold_reason="target_node_budget_exhausted",
                        step=step,
                        step_result=step_result,
                    )
                    prior_action, prior_target = _previous_concern_hold_disposition(
                        resume_seed,
                        prospective_hold,
                        step_ref,
                    )
                    if prior_action == "forward":
                        adoption_sequence_number -= 1
                        if has_fan_groups:
                            frontier_driver.splice_declared_successors_after_current(
                                source_step_ref=step_ref,
                                cascade_depth=cascade_depth,
                                parent_reroute_ref=item["parent_reroute_ref"],
                                successors_by_source=fan_successors_by_source,
                            )
                        continue
                    if prior_action == "reroute":
                        adoption_sequence_number -= 1
                        replaying_prior_concern_reroute_mirror = True
                        target_brick = prior_target
                        budget = node_budget.get(target_brick)
                        human_disposition_adopted_by = "link-policy:human-disposition"
                    if budget is None or node_landings[target_brick] >= budget:
                        hold_record = prospective_hold
                        reroute_records.append(hold_record)
                        _drain_pending_outcomes_before_terminal()
                        if has_fan_groups:
                            held_fan_steps.add((step_ref, cascade_depth))
                            fan_in_wait_all_observations.extend(
                                _fan_in_wait_all_observations_for_held_source(
                                    held_source_step_ref=step_ref,
                                    cascade_depth=cascade_depth,
                                    fan_in_sources_by_target=fan_in_sources_by_target,
                                    completed_fan_steps=completed_fan_steps,
                                    held_fan_steps=held_fan_steps,
                                )
                            )
                        break

                # MAIL-REPAIR (0611, B3 lane 1): the gate ADOPTED this concern for
                # THIS reroute, so its mandatory reason_refs are truck-eligible.
                # Build the mail entry by READING THE RECORDED ROW BACK FROM THE
                # LEDGER (the just-written transition-concern.json document) --
                # delivery reads the recorded fact, never memory. B1 fail-closed:
                # a missing/mismatched recorded residence or an address that does
                # not resolve in the ledger HOLDs LOUDLY via the existing hold
                # machinery (no silent delivery) BEFORE any budget is consumed.
                source_attempt_index = sum(
                    1
                    for completed in step_results
                    if completed.preparation.step_rows.step_ref == step_ref
                )
                concern_runtime_handoff, broken_mail_reason = (
                    _runtime_concern_handoff_from_ledger(
                        building_root=building_root,
                        source_step_ref=step_ref,
                        source_brick_ref=brick_ref_by_step[step_ref],
                        source_attempt_index=source_attempt_index,
                        adopted_concern=concern,
                    )
                )
                if concern_runtime_handoff is None:
                    adoption_sequence_number += 1
                    hold_record = _build_hold(
                        building_id=building_id,
                        plan_ref=plan_ref,
                        source_step_ref=step_ref,
                        source_brick_ref=brick_ref_by_step[step_ref],
                        target_brick=target_brick,
                        concern=concern,
                        cascade_depth=item["cascade_depth"],
                        parent_reroute_ref=item["parent_reroute_ref"],
                        adoption_sequence_number=adoption_sequence_number,
                        node_budget=node_budget.get(target_brick, 0),
                        attempt_number=node_landings.get(target_brick, 0),
                        budget_exhausted=False,
                        hold_reason=broken_mail_reason,
                        step=step,
                        step_result=step_result,
                    )
                    prior_action, _prior_target = _previous_concern_hold_disposition(
                        resume_seed,
                        hold_record,
                        step_ref,
                    )
                    if prior_action == "forward":
                        adoption_sequence_number -= 1
                        if has_fan_groups:
                            frontier_driver.splice_declared_successors_after_current(
                                source_step_ref=step_ref,
                                cascade_depth=cascade_depth,
                                parent_reroute_ref=item["parent_reroute_ref"],
                                successors_by_source=fan_successors_by_source,
                            )
                        continue
                    reroute_records.append(hold_record)
                    _drain_pending_outcomes_before_terminal()
                    if has_fan_groups:
                        held_fan_steps.add((step_ref, cascade_depth))
                        fan_in_wait_all_observations.extend(
                            _fan_in_wait_all_observations_for_held_source(
                                held_source_step_ref=step_ref,
                                cascade_depth=cascade_depth,
                                fan_in_sources_by_target=fan_in_sources_by_target,
                                completed_fan_steps=completed_fan_steps,
                                held_fan_steps=held_fan_steps,
                            )
                        )
                    break

                # ADOPT: consume one from the TARGET node's SHARED budget (per landing),
                # append the target (+ declared replay scope) to the live queue, record.
                node_landings[target_brick] += 1
                adoption_sequence_number += 1
                attempt_number = node_landings[target_brick]
                target_step_ref = step_ref_by_brick[target_brick]
                reroute_ref = (
                    f"reroute-adoption:{building_id}:{adoption_sequence_number:02d}:"
                    f"{target_brick.replace(':', '-')}"
                )
                reroute_cascade_depth = item["cascade_depth"] + 1
                # MAIL-REPAIR (0611): every redo item THIS adoption schedules
                # (target landing + declared replay scope + cohort re-verify)
                # carries the eligible runtime mail: the adopted concern's
                # recorded entry, plus -- on a raise resume -- THIS resume's
                # disposition row entry (consumed here, iteration-local).
                runtime_mail: list[dict[str, Any]] = [
                    {**concern_runtime_handoff, "reroute_ref": reroute_ref}
                ]
                if disposition_runtime_handoff is not None:
                    runtime_mail.append(
                        {**disposition_runtime_handoff, "reroute_ref": reroute_ref}
                    )
                    disposition_runtime_handoff = None
                # Append the target landing, then its declared replay scope (forward
                # replay executions THROUGH downstream nodes; those do NOT consume budget).
                appended: list[dict[str, Any]] = [
                    {
                        "step_ref": target_step_ref,
                        "cascade_depth": reroute_cascade_depth,
                        "parent_reroute_ref": reroute_ref,
                        "is_reroute_landing": True,
                        "runtime_handoffs": tuple(runtime_mail),
                    }
                ]
                replay_scope = _declared_replay_scope_step_refs(
                    step, target_brick=target_brick, step_ref_by_brick=step_ref_by_brick
                )
                for replay_step_ref in replay_scope:
                    appended.append(
                        {
                            "step_ref": replay_step_ref,
                            "cascade_depth": reroute_cascade_depth,
                            "parent_reroute_ref": reroute_ref,
                            "is_reroute_landing": False,
                            "runtime_handoffs": tuple(runtime_mail),
                        }
                    )
                # COHORT RE-VERIFICATION (knot ③ stale-pass): if this landing
                # targets a node that is a fan-in SOURCE, re-verify its sibling
                # fan-in sources too (a fix in one lane can stale a sibling's
                # prior PASS). Cohort siblings replay FORWARD (is_reroute_landing:
                # False => BUDGET-FREE; node_landings untouched). A sibling is
                # skipped only on a HUMAN sibling_independence vouch; absent =>
                # re-verify all (conservative).
                (
                    cohort_replay_refs,
                    cohort_skipped_refs,
                    cohort_records,
                ) = _fan_in_cohort_replay_plan(
                    target_step_ref=target_step_ref,
                    graph_context=graph_context,
                    step_ref_by_brick=step_ref_by_brick,
                    already_scoped_step_refs=[target_step_ref, *replay_scope],
                )
                for cohort_step_ref in cohort_replay_refs:
                    appended.append(
                        {
                            "step_ref": cohort_step_ref,
                            "cascade_depth": reroute_cascade_depth,
                            "parent_reroute_ref": reroute_ref,
                            "is_reroute_landing": False,
                            "runtime_handoffs": tuple(runtime_mail),
                        }
                    )
                # A vouched-skipped sibling is NOT re-walked; carry its PRIOR pass
                # forward at the reroute cascade-depth so the shared fan-in
                # target's wait-all AND its carry gate are satisfied without
                # re-running it.
                for skipped_step_ref in cohort_skipped_refs:
                    completed_fan_steps.add(
                        (skipped_step_ref, reroute_cascade_depth)
                    )
                    cohort_skip_carry_forward.add(
                        (skipped_step_ref, reroute_cascade_depth)
                    )
                fan_in_cohort_records.extend(cohort_records)
                mirror_insert_offset = 0
                if replaying_prior_concern_reroute_mirror and has_fan_groups:
                    for pending_item in frontier_driver.pending_items():
                        pending_step_ref = str(pending_item.get("step_ref") or "")
                        if pending_step_ref in fan_in_sources_by_target:
                            break
                        if int(pending_item.get("cascade_depth", 0)) != cascade_depth:
                            break
                        if (
                            str(pending_item.get("parent_reroute_ref") or "")
                            != str(item.get("parent_reroute_ref") or "")
                        ):
                            break
                        mirror_insert_offset += 1
                frontier_driver.splice_after_current(
                    appended,
                    offset=mirror_insert_offset,
                )
                reroute_insert_width = len(appended)
                # CONTRACT-DERIVED emission (ζ6): build the record FROM the recording
                # contract field-spec (support/recording/walker_evidence.py iterates
                # support/recording/contracts.py). No inline dict literal: the shape can
                # no longer drift silently from a feature impl change.
                adoption_record = build_reroute_adoption_record(
                    reroute_ref=reroute_ref,
                    adoption_sequence_number=adoption_sequence_number,
                    cascade_depth=reroute_cascade_depth,
                    parent_reroute_ref=item["parent_reroute_ref"],
                    source_step_ref=step_ref,
                    source_brick_ref=brick_ref_by_step[step_ref],
                    source_transition_concern_ref=_optional_text_value(
                        concern.get("concern_ref")
                    )
                    or "",
                    transition_concern_binding=False,
                    adopted_by=human_disposition_adopted_by or _adopted_by_ref(step),
                    immediate_target_ref=target_brick,
                    target_brick=target_brick,
                    target_step_ref=target_step_ref,
                    replay_segment_refs=list(replay_scope),
                    attempt_number=attempt_number,
                    node_budget=budget,
                    budget_exhausted=False,
                    disposition_required=False,
                    proof_limits=list(PROOF_LIMITS),
                    not_proven=list(NOT_PROVEN),
                    # Structured field-set observation (no judgment): the field SETS at
                    # this reroute boundary as FACTS (Brick declared / Agent observed /
                    # gate required) + set deltas. NO failing_axis / fault / success.
                    structured_field_observation=_structured_field_observation_for_step(
                        step, step_result
                    ),
                    carry_budget_evidence_ref=_carry_budget_evidence_ref(
                        building_id,
                        target_brick,
                    ),
                    # PERSIST the cohort plan so a HOLD-then-resume reconstruction
                    # rebuilds the SAME pending state (re-verify siblings + carry
                    # vouched-skipped sibling bodies). BUDGET-FREE (forward replay).
                    cohort_replay_segment_refs=list(cohort_replay_refs),
                    cohort_skipped_segment_refs=list(cohort_skipped_refs),
                )
                reroute_records.append(adoption_record)
                adopted_reroute = True
        if has_fan_groups and not adopted_reroute:
            frontier_driver.splice_declared_successors_after_current(
                source_step_ref=step_ref,
                cascade_depth=cascade_depth,
                parent_reroute_ref=item["parent_reroute_ref"],
                successors_by_source=fan_successors_by_source,
                offset=reroute_insert_width,
            )

    # RESUME: stamp the human/COO-authored resumed transition_lifecycle on the held
    # source for raise/forward/reroute (stop already stamped + closed in the loop hook), and
    # build the resume_observation recording the applied disposition. Mirrors the
    # prior resume verb so the resumed Building's evidence shows the disposition was
    # human/COO-authored (ζ7: support reads it, never authors it).
    resume_observations: list[Mapping[str, Any]] = []
    if resume_seed is not None:
        # FAIL-CLOSED gap-2: assert the held occurrence was actually reached and the
        # disposition applied. The in-loop hook sets disposition_applied=True exactly
        # when (held_source_step_ref, held_cascade_depth) is hit as its held
        # occurrence and the raise/forward/stop/reroute action is applied. If the seeded
        # walk finished WITHOUT applying the disposition (the held occurrence was
        # never reached -- e.g. corrupt held identity, a divergent earlier HOLD, or
        # a replay that never reached it), a silent return would falsely claim the
        # disposition was applied. Raise instead of stamping a resumed lifecycle on a
        # disposition that never fired.
        if not disposition_applied:
            raise ValueError(
                "resume divergence: the seeded walk completed WITHOUT applying the "
                f"human/COO disposition ({resume_seed.disposition_action!r}) at the held "
                f"occurrence (source_step_ref={resume_seed.held_source_step_ref!r}, "
                f"cascade_depth={resume_seed.held_cascade_depth}); the held occurrence was "
                "never reached -- refusing to silently claim the disposition was applied"
            )
        resume_observations = list(resume_seed.existing_resume_observations)
        if (
            resume_seed.disposition_action in {"raise", "forward", "reroute"}
            and not resume_seed.skip_lifecycle_stamp
        ):
            step_results = _stamp_resumed_lifecycle_on_held_source(
                step_results,
                resume_seed=resume_seed,
                disposition_action=resume_seed.disposition_action,
                building_id=building_id,
                replay_step=resume_seed.replay_step,
                checked_proof_limits=checked_proof_limits,
                held_occurrence_index=held_occurrence_index,
            )
        resume_observations.append(
            _build_resume_disposition_observation(
                resume_seed=resume_seed,
                node_budget=node_budget,
                node_landings=node_landings,
            )
        )
        resume_body_carry_observations = list(source_fact_body_carry_observations)

    # Thread the dynamic-walker evidence (reroute adoption records + HOLD) onto
    # the plan so the accumulated writer carries it in the link evidence (a NESTED
    # record, NOT a new BAL fact class). On HOLD we also inject a paused
    # transition_lifecycle Link row onto the source step so observe_building_frontier
    # reports link_paused (disposition_required).
    write_plan = dict(linear_plan)
    held = hold_record is not None or fan_in_hold_record is not None
    write_plan["dynamic_walker_evidence"] = {
        "kind": "dynamic_walker_evidence",
        "walker_mode": "dynamic",
        "reroute_adoption_records": list(reroute_records),
        "node_reroute_budgets": dict(node_budget),
        "node_reroute_landings": dict(node_landings),
        "held": held,
        "hold": hold_record or fan_in_hold_record or {},
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    if source_fact_body_carry_observations:
        write_plan["dynamic_walker_evidence"]["source_fact_body_carry_observations"] = list(
            source_fact_body_carry_observations
        )
    if source_lane_transition_concern_observations:
        write_plan["dynamic_walker_evidence"][
            "source_lane_transition_concern_observations"
        ] = list(source_lane_transition_concern_observations)
    if resume_seed is not None:
        # RESUME evidence: carry the resume_observations so the rewritten
        # dynamic_walker_evidence matches the prior resume verb's shape. The
        # RESUME_NOT_PROVEN merge is applied AFTER the fan block below so it wins
        # for a resumed graph (the prior resume verb's not_proven shape).
        write_plan["dynamic_walker_evidence"]["resume_observations"] = list(
            resume_observations
        )
    if has_fan_groups:
        write_plan["dynamic_walker_evidence"]["fan_in_wait_all_observations"] = list(
            fan_in_wait_all_observations
        )
        if fan_in_cohort_records:
            write_plan["dynamic_walker_evidence"]["fan_in_cohort_records"] = list(
                fan_in_cohort_records
            )
        write_plan["dynamic_walker_evidence"]["proof_limits"] = list(
            _merge_texts(PROOF_LIMITS, FAN_TOPOLOGY_PROOF_LIMITS)
        )
        write_plan["dynamic_walker_evidence"]["not_proven"] = list(
            _merge_texts(NOT_PROVEN, FAN_TOPOLOGY_NOT_PROVEN)
        )
    if resume_seed is not None:
        # RESUME not_proven wins (prior resume verb shape) over the fan-topology
        # variant for a resumed graph.
        write_plan["dynamic_walker_evidence"]["not_proven"] = list(
            _merge_texts(NOT_PROVEN, RESUME_NOT_PROVEN)
        )
    if hold_record is not None:
        step_results = _inject_hold_paused_link(step_results, hold_record)
    elif fan_in_hold_record is not None:
        step_results = _inject_fan_in_paused_link(step_results, fan_in_hold_record)

    evidence_write = write_accumulated(
        building_id=building_id,
        plan_ref=plan_ref,
        plan=write_plan,
        step_results=tuple(step_results),
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        proof_limits=checked_proof_limits,
        graph_context=graph_context,
        declaration_plan=plan,
        step_outputs_already_written=bool(step_results),
    )
    if report_event_policy:
        terminal_event_kind = building_event_kind_from_frontier(
            evidence_write.lifecycle_write.root,
            repo_root=repo_root_path,
        )
        terminal_event = _emit_building_event_best_effort(
            report_event_policy,
            event_kind=terminal_event_kind,
            building_id=building_id,
            building_root=evidence_write.lifecycle_write.root,
            repo_root=repo_root_path,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
            overwrite_existing=overwrite_existing,
        )
        if terminal_event is not None:
            report_event_observations.append(terminal_event)
    result = BuildingPlanSupportResult(
        building_id=building_id,
        plan_ref=plan_ref,
        step_results=tuple(step_results),
        lifecycle_write=evidence_write.lifecycle_write,
        building_map_write=evidence_write.building_map_write,
        written_files=evidence_write.written_files,
        capture_event_types=evidence_write.capture_event_types,
        building_map_packet=evidence_write.building_map_packet,
        proof_limits=_merge_texts(
            checked_proof_limits,
            PROOF_LIMITS,
            FAN_TOPOLOGY_PROOF_LIMITS if has_fan_groups else (),
            RESUME_NOT_PROVEN if resume_seed is not None else (),
            *(r.proof_limits for r in step_results),
        ),
        not_proven=_merge_texts(
            plan.get("not_proven"),
            NOT_PROVEN,
            FAN_TOPOLOGY_NOT_PROVEN if has_fan_groups and resume_seed is None else (),
            RESUME_NOT_PROVEN if resume_seed is not None else (),
            *(r.not_proven for r in step_results),
        ),
    )
    # In-memory side channel: the NESTED RerouteAdoptionRecords (NOT a new BAL
    # fact class, NOT a frozen dataclass field) for callers/checkers that walk the
    # dynamic walk in-process. The persistent HOLD signal is the paused
    # transition_lifecycle injected into link.jsonl (observe_building_frontier).
    # D1 single-source: PLAN_RESULT_SIDE_CHANNEL_FIELDS owns the field-name
    # literals; this attach block references those names (index 0/1/2) rather than
    # re-typing them, so the carry helper and the attach site cannot drift.
    reroute_field, evidence_field, report_field = PLAN_RESULT_SIDE_CHANNEL_FIELDS
    object.__setattr__(result, reroute_field, tuple(reroute_records))
    object.__setattr__(
        result,
        evidence_field,
        write_plan["dynamic_walker_evidence"],
    )
    if report_event_observations:
        object.__setattr__(
            result,
            report_field,
            tuple(report_event_observations),
        )
    return result

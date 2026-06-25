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
from collections.abc import Mapping, Sequence
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
    graph_ready_timestamp,
    project_ref_for_building_root,
)
from brick_protocol.support.recording.step_outputs import _step_output_manifest_ref
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


@dataclasses.dataclass(frozen=True)
class _ReadyItemsResult:
    """Support-only ready batch returned by the live frontier driver."""

    items: tuple[dict[str, Any], ...]
    hold_item: Mapping[str, Any] | None = None
    hold_observation: Mapping[str, Any] | None = None


class _FrontierDriver:
    """Own the live frontier queue and cursor."""

    def __init__(
        self,
        items: Sequence[dict[str, Any]],
        *,
        scheduled_fan_steps: set[tuple[str, int]] | None = None,
    ) -> None:
        self._items = list(items)
        self._cursor = 0
        self._scheduled_fan_steps = (
            scheduled_fan_steps if scheduled_fan_steps is not None else set()
        )

    def next_item(self) -> dict[str, Any] | None:
        # Serial/default mode returns exactly one cursor-front item. P6-C's
        # opt-in pool path uses ready_items() and leaves this path byte-stable.
        if self._cursor >= len(self._items):
            return None
        item = self._items[self._cursor]
        self._cursor += 1
        return item

    def ready_items(
        self,
        *,
        max_items: int,
        has_fan_groups: bool,
        fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
        completed_fan_steps: set[tuple[str, int]],
        running_fan_steps: set[tuple[str, int]],
        held_fan_steps: set[tuple[str, int]],
        fan_in_deferrals: dict[tuple[str, int], int],
    ) -> _ReadyItemsResult:
        if max_items <= 0:
            raise ValueError("frontier ready max_items must be positive")
        ready: list[dict[str, Any]] = []
        while self._cursor < len(self._items) and len(ready) < max_items:
            item = self._items[self._cursor]
            step_ref = str(item.get("step_ref", ""))
            cascade_depth = int(item.get("cascade_depth", 0))
            if has_fan_groups:
                wait_state, wait_observation = _fan_in_wait_all_state(
                    step_ref=step_ref,
                    cascade_depth=cascade_depth,
                    fan_in_sources_by_target=fan_in_sources_by_target,
                    completed_fan_steps=completed_fan_steps,
                    running_fan_steps=running_fan_steps,
                    held_fan_steps=held_fan_steps,
                    pending_queue=self._items[self._cursor + 1 :],
                    fan_in_deferrals=fan_in_deferrals,
                )
                if wait_state == "defer":
                    self._cursor += 1
                    self.defer(item)
                    continue
                if wait_state == "hold":
                    if ready:
                        break
                    self._cursor += 1
                    return _ReadyItemsResult(
                        items=(),
                        hold_item=item,
                        hold_observation=wait_observation,
                    )
            # HOLD-SAFE PARALLEL: a fan-in TARGET (join) dispatches ALONE, never batched
            # with siblings/sources. A reroute/HOLD only emerges AFTER a node RUNS, and
            # ready_items cannot foresee it; batching a join alongside a node about to
            # reroute/HOLD lets the join BODY run before the HOLD applies (the knot3-cohort-g
            # break). So joins are batch-terminal: this item either starts a fresh batch
            # alone (ready empty -> append + break) or waits for the next batch (ready
            # non-empty -> break WITHOUT advancing). Independent fan-out lanes still batch.
            is_fan_in_target = bool(fan_in_sources_by_target.get(step_ref))
            if is_fan_in_target and ready:
                break
            self._cursor += 1
            ready.append(item)
            if has_fan_groups:
                running_fan_steps.add((step_ref, cascade_depth))
            if is_fan_in_target:
                break
        return _ReadyItemsResult(items=tuple(ready))

    def pending_items(self) -> list[dict[str, Any]]:
        return self._items[self._cursor :]

    def append(self, items: Sequence[dict[str, Any]]) -> None:
        self._items.extend(items)

    def defer(self, item: dict[str, Any]) -> None:
        self.append([item])

    def splice_after_current(
        self,
        items: Sequence[dict[str, Any]],
        *,
        offset: int = 0,
    ) -> None:
        if not items:
            return
        insert_at = self._cursor + offset
        self._items[insert_at:insert_at] = list(items)

    def splice_declared_successors_after_current(
        self,
        *,
        source_step_ref: str,
        cascade_depth: int,
        parent_reroute_ref: str,
        successors_by_source: Mapping[str, tuple[str, ...]],
        offset: int = 0,
    ) -> None:
        successor_items: list[dict[str, Any]] = []
        _splice_declared_successors(
            successor_items,
            insert_at=0,
            source_step_ref=source_step_ref,
            cascade_depth=cascade_depth,
            parent_reroute_ref=parent_reroute_ref,
            successors_by_source=successors_by_source,
            scheduled_fan_steps=self._scheduled_fan_steps,
        )
        self.splice_after_current(successor_items, offset=offset)


def _fanout_dispatch_pool_size(plan: Mapping[str, Any]) -> int:
    raw_value = os.environ.get(
        "BRICK_FANOUT_DISPATCH_POOL_SIZE",
        plan.get("fanout_dispatch_pool_size", 1),
    )
    if raw_value is None or raw_value == "":
        return 1
    if isinstance(raw_value, bool):
        raise ValueError("fanout_dispatch_pool_size must be a positive integer")
    if isinstance(raw_value, int):
        value = raw_value
    elif isinstance(raw_value, str) and raw_value.strip().isdecimal():
        value = int(raw_value.strip())
    else:
        raise ValueError("fanout_dispatch_pool_size must be a positive integer")
    if value < 1:
        raise ValueError("fanout_dispatch_pool_size must be a positive integer")
    return value


# AUTO-PARALLEL default: a drawn fan() IS the parallel declaration. When the plan has fan
# groups and NO explicit pool override is set, default the dispatch pool to this cap so
# fan-out runs concurrent BY DEFAULT. HOLD-safe because ready_items forces fan-in TARGETS
# (joins) to dispatch alone (batch-terminal), so a sibling's data-dependent reroute/HOLD is
# applied before any join body runs. Record order stays canonical (the drain pops
# pending_outcomes FIFO = submission/frontier order, independent of completion timing).
# Resume/replay stays serial via the resume guard. An explicit env/plan override still wins.
_FANOUT_AUTO_POOL = 8


def _has_explicit_fanout_pool_override(plan: Mapping[str, Any]) -> bool:
    env = os.environ.get("BRICK_FANOUT_DISPATCH_POOL_SIZE")
    if env not in (None, ""):
        return True
    return "fanout_dispatch_pool_size" in plan


def _carries_forward_fields_for_result(
    result: BuildingRunSupportResult,
) -> tuple[str, ...]:
    """The UPSTREAM step's declared carries_forward_fields (the HANDOFF subset).

    Read off ``result.preparation.step_rows.brick_row`` -- the SAME Brick row
    surface that carries ``required_return_shape`` -- and parsed with the
    canonical Brick parser ``parse_carries_forward_fields``. Returns ``()`` when
    the row omits the key (a kind with no declared carry-set) OR when the
    preparation/row is missing, which the carry filter reads as "no filter"
    (full-summary carry, backward-safe). Support reads the VALUE off the row; it
    never reads the return.yaml form directly.
    """

    preparation = getattr(result, "preparation", None)
    step_rows = getattr(preparation, "step_rows", None)
    brick_row = getattr(step_rows, "brick_row", None)
    if not isinstance(brick_row, Mapping):
        return ()
    return parse_carries_forward_fields(brick_row.get("carries_forward_fields"))


def _source_fact_body_carry_for_step(
    *,
    building_root: Path,
    building_id: str,
    target_step_ref: str,
    cascade_depth: int,
    step: Mapping[str, Any],
    step_results: list[BuildingRunSupportResult],
    step_result_events: list[Mapping[str, Any]],
    fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
    cohort_skip_carry_forward: set[tuple[str, int]] | None = None,
) -> Mapping[str, Any]:
    source_facts = _brick_source_facts(step)
    skip_carry_forward = cohort_skip_carry_forward or set()
    attempts = _step_result_attempt_indices(step_results)
    result_refs: dict[int, str] = {}
    for index, result in enumerate(step_results):
        attempt_index = attempts[index]
        step_ref = result.preparation.step_rows.step_ref
        result_refs[index] = _step_output_manifest_ref(step_ref, attempt_index)

    # The UPSTREAM kind's HANDOFF subset, keyed by the carried result index. Read
    # off result.preparation.step_rows.brick_row -- the SAME row carrying
    # required_return_shape -- and parsed with the canonical Brick parser. Empty
    # => no filter (full-summary carry). This is what FILTERS the forwarded
    # summary down to the upstream kind's declared carries_forward_fields.
    forward_fields_by_index: dict[int, tuple[str, ...]] = {}
    for index, result in enumerate(step_results):
        forward_fields_by_index[index] = _carries_forward_fields_for_result(result)

    bodies: dict[str, str] = {}
    carried_step_output_refs: list[str] = []
    missing_source_fact_refs: list[str] = []
    carried_result_indices: set[int] = set()
    observed_source_step_refs: list[str] = []
    missing_source_step_refs: list[str] = []

    for source_fact in source_facts:
        match = _matching_step_output_index(
            source_fact,
            cascade_depth=cascade_depth,
            result_refs=result_refs,
            step_result_events=step_result_events,
        )
        if match is None:
            if "step-output" in source_fact:
                missing_source_fact_refs.append(source_fact)
            continue
        body = _step_output_wiki_carry_body(
            building_root,
            result_refs[match],
            forward_fields_by_index.get(match, ()),
        )
        if body is None:
            missing_source_fact_refs.append(source_fact)
            source_step_ref = _step_ref_from_step_output_ref(result_refs[match])
            if source_step_ref:
                missing_source_step_refs.append(source_step_ref)
            continue
        bodies[source_fact] = body
        carried_result_indices.add(match)
        carried_step_output_refs.append(result_refs[match])
        source_step_ref = _step_ref_from_step_output_ref(result_refs[match])
        if source_step_ref:
            observed_source_step_refs.append(source_step_ref)

    for source_step_ref in fan_in_sources_by_target.get(target_step_ref, ()):
        match = _latest_completed_step_index(
            source_step_ref,
            cascade_depth=cascade_depth,
            step_result_events=step_result_events,
        )
        if match is None and (source_step_ref, cascade_depth) in skip_carry_forward:
            # A HUMAN-vouched (sibling_independence) skipped sibling is not
            # re-walked at this reroute cascade-depth; carry its PRIOR PASS
            # (its most recent completion at an earlier depth) forward so the
            # fan-in target's carry gate is satisfied without re-running it.
            match = _latest_completed_step_index_any_depth(
                source_step_ref,
                step_result_events=step_result_events,
            )
        if match is None:
            missing_source_fact_refs.append(
                f"fan-in-source:{source_step_ref}:cascade-{cascade_depth}"
            )
            missing_source_step_refs.append(source_step_ref)
            continue
        if match in carried_result_indices:
            continue
        body = _step_output_wiki_carry_body(
            building_root,
            result_refs[match],
            forward_fields_by_index.get(match, ()),
        )
        if body is None:
            missing_source_fact_refs.append(
                f"fan-in-source:{source_step_ref}:step-output-body-missing:"
                f"cascade-{cascade_depth}"
            )
            missing_source_step_refs.append(source_step_ref)
            continue
        bodies.setdefault(result_refs[match], body)
        carried_result_indices.add(match)
        carried_step_output_refs.append(result_refs[match])
        observed_source_step_refs.append(source_step_ref)

    if not source_facts and target_step_ref not in fan_in_sources_by_target:
        return {"source_fact_bodies": bodies, "observation": None}

    carried_unique = list(dict.fromkeys(carried_step_output_refs))
    missing_unique = list(dict.fromkeys(missing_source_fact_refs))
    observation = {
        "kind": "source_fact_body_carry_observation",
        "target_step_ref": target_step_ref,
        "cascade_depth": cascade_depth,
        "declared_source_fact_refs": list(source_facts),
        "fan_in_source_step_refs": list(fan_in_sources_by_target.get(target_step_ref, ())),
        "observed_source_step_refs": list(dict.fromkeys(observed_source_step_refs)),
        "missing_source_step_refs": list(dict.fromkeys(missing_source_step_refs)),
        "carried_step_output_refs": carried_unique,
        "supplied_source_fact_body_refs": list(bodies),
        "missing_source_fact_refs": missing_unique,
        "body_absent": bool(missing_unique),
        "carry_gate_observation": _carry_gate_observation(
            target_step_ref=target_step_ref,
            carried_step_output_refs=carried_unique,
            missing_source_fact_refs=missing_unique,
        ),
        "carry_fact_observation": _carry_fact_observation(
            target_step_ref=target_step_ref,
            carried_step_output_refs=carried_unique,
        ),
        "proof_limits": [
            "Link carry/gate observation over declared step-output refs only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic sufficiency of carried bodies",
            "partial QA reuse",
        ],
    }
    return {"source_fact_bodies": bodies, "observation": observation}


def _carry_gate_observation(
    *,
    target_step_ref: str,
    carried_step_output_refs: list[str],
    missing_source_fact_refs: list[str],
) -> Mapping[str, Any]:
    required = tuple(dict.fromkeys([*carried_step_output_refs, *missing_source_fact_refs]))
    missing = tuple(dict.fromkeys(missing_source_fact_refs))
    return {
        "kind": "link_carry_gate_observation",
        "stage": "carry",
        "sufficiency": "missing_required_facts" if missing else "sufficient",
        "checked_public_fact": f"step-output-carry:{target_step_ref}",
        "required_public_facts": list(required),
        "missing_required_facts": list(missing),
        "reason": (
            "declared Link fan-in carry gate over already-written step-output evidence"
        ),
        "proof_limits": [
            "support records Link carry gate observation only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def _carry_fact_observation(
    *,
    target_step_ref: str,
    carried_step_output_refs: list[str],
) -> Mapping[str, Any] | None:
    carried = tuple(dict.fromkeys(carried_step_output_refs))
    if not carried:
        return None
    return {
        "kind": "link_carry_fact_observation",
        "carried_fact_refs": list(carried),
        "source_owner_axis": "Agent",
        "target_boundary_ref": target_step_ref,
        "evidence_reference": f"step-output-carry:{target_step_ref}",
        "proof_limits": [
            "support records Link carry observation only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def _fan_in_observation_from_carry_observation(
    observation: Mapping[str, Any],
    *,
    required_sources: tuple[str, ...],
) -> Mapping[str, Any]:
    observed_sources = tuple(
        str(ref)
        for ref in observation.get("observed_source_step_refs", ())
        if str(ref)
    )
    missing_sources = tuple(
        str(ref)
        for ref in observation.get("missing_source_step_refs", ())
        if str(ref)
    )
    carry_gate = observation.get("carry_gate_observation")
    missing_required_facts: list[str] = []
    if isinstance(carry_gate, Mapping):
        missing_required_facts = [
            str(ref)
            for ref in carry_gate.get("missing_required_facts", ())
            if str(ref)
        ]
    return {
        "kind": "fan_in_wait_all_observation",
        "target_step_ref": observation.get("target_step_ref", ""),
        "cascade_depth": observation.get("cascade_depth", 0),
        "required_source_step_refs": list(required_sources),
        "observed_source_step_refs": list(dict.fromkeys(observed_sources)),
        "missing_source_step_refs": list(dict.fromkeys(missing_sources)),
        "pending_source_step_refs": [],
        "carry_gate_observation": dict(carry_gate) if isinstance(carry_gate, Mapping) else {},
        "missing_required_facts": list(dict.fromkeys(missing_required_facts)),
        "proof_limits": list(observation.get("proof_limits", ())),
        "not_proven": list(observation.get("not_proven", ())),
    }


# run_building_intake (support/operator/driver.py) writes its materialized
# INPUT plan to <building_root>/declared-building-plan.json and then
# immediately walks it; without an admission for exactly that artifact, the
# first defaults use always self-collided here (FileExistsError). The
# admission is fail-closed and EXACT: a pre-existing root is admitted IFF it
# holds ONLY regular non-symlink file(s) named in this set -- any other name,
# any subdirectory, any symlink, or an EMPTY root still rejects. (The run's
# own work/declared-building-plan.json declaration packet lives under work/
# and is a different file.) This PRE-ADAPTER predicate intentionally remains
# narrower than support.recording.adapter_error_frontier's POST-ADAPTER
# declaration-chain/root-state handling, which may preserve report/declaration
# artifacts or mark partial roots after an adapter interruption. Parity copy
# lives in run.py.
_PREEXISTING_ROOT_INTAKE_ARTIFACTS: frozenset[str] = frozenset(
    {"declared-building-plan.json"}
)


def _root_holds_only_intake_plan_artifact(root: Path) -> bool:
    entries = list(root.iterdir())
    if not entries:
        return False
    for entry in entries:
        if entry.name not in _PREEXISTING_ROOT_INTAKE_ARTIFACTS:
            return False
        if entry.is_symlink() or not entry.is_file():
            return False
    return True


def _preflight_step_output_building_root(
    output_root: Path | str,
    building_id: str,
    *,
    overwrite_existing: bool,
) -> Path:
    root = Path(output_root) / building_id
    if root.exists():
        if not root.is_dir():
            raise NotADirectoryError(f"Building lifecycle root is not a directory: {root}")
        if not overwrite_existing and not _root_holds_only_intake_plan_artifact(root):
            raise FileExistsError(
                "Building lifecycle root already exists; choose a new building_id "
                "or pass overwrite_existing=True"
            )
    return root


def _clear_overwrite_claim_trace_manifest(root: Path) -> None:
    if not root.exists() or not root.is_dir():
        return
    claim_trace = root / "evidence" / "claim_trace"
    if claim_trace.exists():
        if claim_trace.is_symlink() or claim_trace.is_file():
            claim_trace.unlink()
        else:
            shutil.rmtree(claim_trace)
    raw_manifest = root / "raw" / "raw-manifest.json"
    if raw_manifest.exists():
        raw_manifest.unlink()


def _materialize_initial_declaration_evidence(
    building_root: Path,
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    declaration_plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
    proof_limits: tuple[str, ...],
) -> None:
    building_root.mkdir(parents=True, exist_ok=True)
    _write_declaration_work_evidence(
        building_root,
        building_id=building_id,
        plan_ref=plan_ref,
        plan=plan,
        declaration_plan=declaration_plan,
        graph_context=graph_context,
        task_source_ref=task_source_ref,
        proof_limits=proof_limits,
        not_proven=_merge_texts(plan.get("not_proven")),
    )


def _brick_source_facts(step: Mapping[str, Any]) -> tuple[str, ...]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        return ()
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == "Brick":
            raw = row.get("source_facts", ())
            if not isinstance(raw, list):
                return ()
            return tuple(str(item).strip() for item in raw if str(item).strip())
    return ()


def _step_result_attempt_indices(
    step_results: list[BuildingRunSupportResult],
) -> tuple[int, ...]:
    counts: dict[str, int] = {}
    attempts: list[int] = []
    for result in step_results:
        step_ref = result.preparation.step_rows.step_ref
        counts[step_ref] = counts.get(step_ref, 0) + 1
        attempts.append(counts[step_ref])
    return tuple(attempts)


def _matching_step_output_index(
    source_fact: str,
    *,
    cascade_depth: int,
    result_refs: Mapping[int, str],
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    normalized = str(source_fact).strip()
    if not normalized:
        return None
    for index, ref in result_refs.items():
        if int(step_result_events[index].get("cascade_depth", 0)) != cascade_depth:
            continue
        if normalized == ref or normalized.endswith("/" + ref):
            return index
    return None


def _latest_completed_step_index(
    step_ref: str,
    *,
    cascade_depth: int,
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    for index in range(len(step_result_events) - 1, -1, -1):
        event = step_result_events[index]
        if event.get("step_ref") == step_ref and int(event.get("cascade_depth", 0)) == cascade_depth:
            return index
    return None


def _latest_completed_step_index_any_depth(
    step_ref: str,
    *,
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    """Latest completion of step_ref at ANY cascade-depth (prior-pass carry).

    Used only for a HUMAN-vouched (sibling_independence) skipped fan-in source:
    the sibling is not re-walked at the reroute depth, so its most recent prior
    completion carries forward to satisfy the fan-in target's carry gate.
    """

    for index in range(len(step_result_events) - 1, -1, -1):
        if step_result_events[index].get("step_ref") == step_ref:
            return index
    return None


def _step_ref_from_step_output_ref(step_output_ref: str) -> str:
    parts = str(step_output_ref).replace("\\", "/").split("/")
    if len(parts) < 3:
        return ""
    slug = parts[-2]
    marker = "-attempt-"
    if marker not in slug:
        return slug
    return slug[: slug.rindex(marker)]


def _step_output_body_from_file(building_root: Path, step_output_ref: str) -> str | None:
    try:
        return (building_root / step_output_ref).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


# ---------------------------------------------------------------------------
# WIKI-CARRY (Kaparthy wiki pattern): the walker carries a COMPACT wiki VIEW
# between steps -- NOT the full step-output.json body. Carrying the full body
# (envelope + evidence_refs + proof_limits + graph metadata + returned) made
# the carried context blow up step over step (token amplification). The wiki
# view carries only:
#   * SUMMARY  = the step-output's ``returned`` field (the agent's CURATED
#                output), serialized compactly and floored by
#                ``safe_source_fact_body`` (runaway-returned backstop / secret
#                redaction). No envelope, no evidence_refs, no proof_limits.
#   * PATH     = the ABSOLUTE path of the real step-output.json on disk, so the
#                worker can "go look" with its own file-read tool when the
#                summary is not enough (codex --sandbox read-only reads
#                ~/.brick absolute paths -- WIKI_READ_PROOF).
#   * NOTE     = a plain-text instruction telling the worker the body is a
#                summary and where the full output lives.
# The on-disk step-output.json / raw/ are NEVER touched -- the path merely
# points at them. ``source_fact_bodies`` rides ONLY as text context in the
# agent prompt (agent_adapter._source_fact_bodies_for_prompt -> prompt JSON);
# no runtime program parses it (the checker simulators that parse it read the
# SUMMARY section back via ``wiki_carry_summary_text``).
#
# VIEW ORDER (load-bearing): PATH + NOTE come FIRST, the SUMMARY comes LAST.
# The view is floored by ``safe_source_fact_body`` here, and the agent adapter
# floors it AGAIN downstream (``_clean_source_fact_bodies`` and
# ``_source_fact_bodies_for_prompt``, limit 12000 / gemini 4000). All of those
# floors truncate the TAIL (``body[:limit]``). A large ``returned`` can push the
# whole view past a downstream limit; if the PATH/NOTE were in the tail they
# would be silently amputated and the worker would lose the "go look" address.
# By placing the absolute PATH and the NOTE BEFORE the summary, any tail-
# truncate (whichever limit fires) eats only the END of the summary and ALWAYS
# preserves the load-bearing path + note. This is adapter-agnostic: it does not
# matter which floor cuts -- the head is preserved.
# ---------------------------------------------------------------------------

_WIKI_CARRY_VIEW_HEADER = "[BRICK WIKI CARRY VIEW]"
_WIKI_CARRY_SUMMARY_PREFIX = "summary (this step's returned -- agent's curated output):"
_WIKI_CARRY_PATH_PREFIX = "full step output path:"
_WIKI_CARRY_NOTE = (
    "note: the summary below is THIS step's returned (the agent's curated "
    "output) only. The FULL step output (the whole step-output document with "
    "its evidence pointers, proof limits, and metadata) is NOT inline here -- "
    "it lives in the file at the path above. If the summary is not enough, "
    "read that file with your own file-read tool."
)


def _returned_summary_for_carry(
    body: str, forward_fields: tuple[str, ...] = ()
) -> str:
    """The compact wiki SUMMARY = the step-output's ``returned`` field.

    ``returned`` is the agent's CURATED output. We serialize ONLY it (never the
    surrounding step-output envelope) and floor it through
    ``safe_source_fact_body`` so a runaway ``returned`` is still truncated and
    raw secrets are redacted. Fallbacks (missing/oversize/non-JSON file) keep a
    safe, non-empty summary so the carry never silently drops the worker's
    context.

    CARRY FILTER: when ``forward_fields`` is non-empty it is the UPSTREAM kind's
    declared ``carries_forward_fields`` (the HANDOFF subset). The serialized
    ``returned`` is then narrowed to JUST those fields (PRESENT ones --
    ``if k in returned`` -- a real step-output may omit a declared field) before
    the dump, so the COMMON ENVELOPE (observed_evidence, not_proven, ...) and any
    adapter cruft never cross inline. Empty ``forward_fields`` => no filter
    (full ``returned`` carried, the pre-filter behavior). The full step-output
    stays reachable at the PATH the wiki view prepends -- filtering narrows the
    INLINE summary only, it never removes reachability.
    """

    try:
        packet = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return safe_source_fact_body(body)
    if not isinstance(packet, Mapping) or "returned" not in packet:
        return safe_source_fact_body(body)
    returned = packet.get("returned")
    if forward_fields and isinstance(returned, Mapping):
        returned = {
            key: returned[key] for key in forward_fields if key in returned
        }
    try:
        rendered = json.dumps(returned, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return safe_source_fact_body(body)
    return safe_source_fact_body(rendered)


def _wiki_carry_view(
    building_root: Path,
    step_output_ref: str,
    body: str,
    forward_fields: tuple[str, ...] = (),
) -> str:
    """Build the compact wiki VIEW carried in place of the full step-output body.

    ``forward_fields`` (the upstream kind's carries_forward_fields) narrows the
    INLINE summary; the PATH + NOTE pointing at the full step-output are always
    emitted unchanged, so a filtered field stays reachable via the file.
    """

    absolute_path = str((building_root / step_output_ref).resolve())
    summary = _returned_summary_for_carry(body, forward_fields)
    # PATH + NOTE FIRST, SUMMARY LAST: downstream re-truncation
    # (safe_source_fact_body, limit 12000 / gemini 4000) cuts the TAIL, so the
    # load-bearing absolute path and note always survive while only the END of an
    # oversize summary is trimmed. See the VIEW ORDER note above.
    return (
        f"{_WIKI_CARRY_VIEW_HEADER}\n"
        f"{_WIKI_CARRY_PATH_PREFIX} {absolute_path}\n"
        f"{_WIKI_CARRY_NOTE}\n"
        f"{_WIKI_CARRY_SUMMARY_PREFIX}\n"
        f"{summary}"
    )


def _step_output_wiki_carry_body(
    building_root: Path,
    step_output_ref: str,
    forward_fields: tuple[str, ...] = (),
) -> str | None:
    """Read the step-output and return its compact wiki VIEW (or None if absent).

    ``forward_fields`` is the UPSTREAM step's declared carries_forward_fields;
    when non-empty the inline summary is FILTERED to that handoff subset.
    """

    body = _step_output_body_from_file(building_root, step_output_ref)
    if body is None:
        return None
    return _wiki_carry_view(building_root, step_output_ref, body, forward_fields)


def wiki_carry_summary_text(view: str) -> str | None:
    """Recover the SUMMARY section from a carried wiki view (checker/consumer aid).

    Returns the summary text (the serialized ``returned``) when ``view`` is a
    wiki-carry view, else None. Consumers that need the structured ``returned``
    JSON parse this summary; they MUST NOT expect the full step-output envelope
    to be inline.

    ORDER-INDEPENDENT: this scans for the SUMMARY_PREFIX line and captures every
    line AFTER it. In the current layout the SUMMARY is LAST (PATH + NOTE lead),
    so capture runs to the end of the view; the ``startswith(PATH_PREFIX)`` break
    is a defensive guard kept so an older layout (summary before path) is parsed
    identically. Either way the summary is delimited by its own PREFIX line, not
    by position.
    """

    if not view.startswith(_WIKI_CARRY_VIEW_HEADER):
        return None
    lines = view.splitlines()
    summary_lines: list[str] = []
    capturing = False
    for line in lines:
        if not capturing:
            if line == _WIKI_CARRY_SUMMARY_PREFIX:
                capturing = True
            continue
        if line.startswith(_WIKI_CARRY_PATH_PREFIX):
            break
        summary_lines.append(line)
    if not summary_lines:
        return None
    return "\n".join(summary_lines).strip()


def wiki_carry_path_text(view: str) -> str | None:
    """Recover the absolute step-output PATH from a carried wiki view."""

    if not view.startswith(_WIKI_CARRY_VIEW_HEADER):
        return None
    for line in view.splitlines():
        if line.startswith(_WIKI_CARRY_PATH_PREFIX):
            return line[len(_WIKI_CARRY_PATH_PREFIX):].strip()
    return None


# ---------------------------------------------------------------------------
# MAIL-REPAIR (Smith rulings 0611, B1/B2/B3): runtime rows ride the mail.
#
# The mailbox assembler previously read PLAN-DECLARED rows only
# (_incoming_link_handoff_refs); runtime rows -- the transition concern the
# gate ADOPTED for a reroute, and the human/COO disposition row of a resume --
# never reached the redo workers' agent inputs (b5b measured RED: runtime
# concern.reason_refs markers arrived in 0/10 redo inputs while declared refs
# arrived in all). The repair is ONE assembler widening: an adopted reroute's
# appended queue items carry a ``runtime_handoffs`` packet section built by
# READING THE RECORDED ROW BACK FROM THE LEDGER (the written
# transition-concern.json step-output document), never from memory, so replay
# reads the recorded fact and the packet stamps provenance (which runtime row
# fed it: row ref + kind + recorded residence). ADDRESSES ONLY ride (refs; no
# bodies, no free text).
#
# B3 (narrow, fail-closed): ONLY two runtime rows are truck-eligible --
#   (1) the transition concern ADOPTED by the gate for THIS reroute (its
#       mandatory reason_refs), and
#   (2) the disposition row of THIS resume (its reason_refs, raise lane).
# Nothing else rides (no speculative/unadopted rows; the gate-sequence
# reroute adopts a DECLARED policy action row, not a runtime row, so it
# carries no runtime mail).
#
# B1 (broken ticket, fails-closed): an address that claims a ledger residence
# (step-output form) but has no document, or an adopted concern row whose
# recorded ledger document is missing/mismatched, must NOT be silently
# delivered -> the walk HOLDs via the EXISTING hold machinery (loud
# hold_reason; no new Movement vocabulary).
#
# ζ7 unchanged: support delivers recorded addresses and records; it authors no
# route, Movement, success, or quality.
# ---------------------------------------------------------------------------


def _runtime_handoff_unresolved_address(
    building_root: Path,
    reason_refs: Sequence[Any],
) -> str:
    """The FIRST runtime address claiming a ledger residence with no document.

    B1: a reason_ref of step-output FORM (a filesystem-path-shaped ref or a
    ``step-output:<slug>:attempt-N`` manifest ref) addresses a DOCUMENT in the
    Building ledger; a missing document is a broken ticket -> the caller HOLDs.
    Opaque refs (observation:/brick-comparison:/...) have their recorded
    residence in the runtime row document itself, which the ledger reader
    verifies separately. Returns "" when every address resolves. (run.py
    ``_is_step_output_source_fact_ref`` is a contiguous-marker predicate on a
    DIFFERENT surface -- declared Brick-row source_fact bodies, repo-root
    contained via ``_readable_source_fact_path`` -- runtime mail never routes
    through it, so it is intentionally NOT mirrored here since FIX 1c.)

    FIX 1 (0611 path traversal / cross-building smuggling): the ONLY ledger
    residence a step-output-form address may name is THIS Building's
    ``work/step-outputs/`` subtree. A mere existence probe is NOT containment:
    ``work/step-outputs/../../../other-building/raw/secret.json`` exists and
    would have been silently delivered. Therefore an address is UNRESOLVED
    (-> the caller HOLDs loudly; never delivered) when it
      - starts with ``/`` (an absolute path is never a building-relative
        ledger address),
      - carries a ``..`` (or empty/``.``) path segment, or
      - does not ``resolve()`` to a file STRICTLY INSIDE
        ``<building_root>/work/step-outputs/`` (symlink escapes fail too).

    FIX 1c (0611 spelling-independence, codex round-3 STILL-OPEN): the path
    FORM is no longer detected by how the ``work/step-outputs/`` MARKER is
    SPELLED -- it is decided by WHERE the ref RESOLVES. Prior rounds detected
    the marker as a CONTIGUOUS string (FIX 1 exact-case, FIX 1b casefolded),
    so a ref that RESOLVES into (then out of) the subtree but is SPELLED
    non-contiguously -- ``work/./step-outputs/../../escape/x.json``,
    ``work//step-outputs/../../escape/x.json`` -- bypassed detection entirely,
    fell through as an "opaque" ref, and was DELIVERED (operator-verified
    0611: returned ""). That is the SAME CLASS recurring; the spelling match
    was the root cause, so it is gone. The branching is now:

      - ``step-output:<slug>:attempt-N`` MANIFEST refs (a scheme, no ``/``)
        keep their existing handling: shape-validated, then containment.
      - ANY remaining ref carrying a ``/`` is filesystem-path-shaped. The only
        ledger residence a path-form runtime ref may name is THIS Building's
        ``work/step-outputs/`` subtree, so EVERY such ref must ``resolve()``
        (under ``building_root``) to a document strictly inside it. Absolute
        paths are never building-relative ledger addresses -> UNRESOLVED.
        Whatever the spelling (``work/./step-outputs``, ``work//step-outputs``,
        ``Work/Step-Outputs`` on a case-insensitive filesystem), an in-subtree
        resolution delivers and an out-of-subtree resolution is UNRESOLVED ->
        the caller HOLDs (fail-closed). FIX 1d (0611, codex round-4
        trusted-intermediate symlink): containment is anchored on the RESOLVED
        BUILDING ROOT, never on a resolved ledger subtree -- see
        ``_step_output_address_escapes_ledger``.
      - Refs with NO ``/`` and no manifest scheme are the opaque scheme tokens
        (observation:/brick-comparison:/...) verified elsewhere, unchanged.
    """

    for ref in reason_refs:
        text = str(ref).replace("\\", "/")
        if text.casefold().startswith("step-output:"):
            parts = text.split(":")
            if (
                len(parts) != 3
                or not parts[1]
                or not parts[2].casefold().startswith("attempt-")
            ):
                return str(ref)
            relative = f"work/step-outputs/{parts[1]}-{parts[2]}/step-output.json"
            if _step_output_address_escapes_ledger(building_root, relative):
                return str(ref)
            continue
        if "/" not in text:
            # Opaque scheme token (observation:, brick-comparison:, ...):
            # its recorded residence is verified by the ledger reader.
            continue
        if text.startswith("/"):
            return str(ref)
        if _step_output_address_escapes_ledger(building_root, text):
            return str(ref)
    return ""


def _step_output_address_escapes_ledger(
    building_root: Path,
    relative: str,
) -> bool:
    """True when a step-output-form address must NOT be delivered (fail-closed).

    FIX 1 (0611): containment, not just existence. FIX 1c (0611): containment
    by RESOLUTION, not by segment spelling. FIX 1d (0611, codex round-4
    trusted-intermediate symlink): containment is anchored on the RESOLVED
    BUILDING ROOT, never on a resolved ledger subtree. The prior round
    ``resolve()``d ``<building_root>/work/step-outputs`` FIRST and trusted
    that inode as the containment root (``samestat`` ancestry), so when
    ``work/step-outputs`` ITSELF was a symlink pointing OUTSIDE the building,
    the symlink TARGET became the trusted root and
    ``work/step-outputs/x.json`` was DELIVERED while resolving outside the
    building (operator-reproduced 0611). Deriving the containment root by
    following a symlink is the root cause, so no intermediate path is ever
    resolved into a trusted root any more. The rule is now:

      - ``real_root = building_root.resolve(strict=True)`` is the ONLY
        trusted anchor (resolving the root cannot be redirected by ledger
        content -- the building root is operator-supplied, not
        address-supplied);
      - the candidate ``(building_root / relative).resolve()`` (collapsing
        ``.``/``..``/doubled separators and following EVERY symlink) must be
        a FILE whose resolved path lies under ``real_root`` -- an escape
        outside the building rejects; AND
      - the candidate's path RELATIVE TO ``real_root`` must begin with the
        literal ``("work", "step-outputs")`` components and name a document
        STRICTLY BELOW them (lexical prefix on the POST-resolve relative
        path).

    A ledger directory that symlinks elsewhere therefore always fails: the
    candidate either resolves outside ``real_root`` (first guard) or resolves
    inside but its post-resolve relative path no longer starts with
    ``work/step-outputs`` (second guard). That closes the whole
    trusted-intermediate-symlink CLASS, not one spelling of it. A ``..`` that
    climbs out, an in-building symlink detour, or a missing root/document all
    reject; a weirdly-spelled ref (dot segments, doubled ``/``) that resolves
    to a real document strictly inside ``real_root/work/step-outputs`` is
    contained.
    """

    try:
        real_root = building_root.resolve(strict=True)
    except OSError:
        return True
    try:
        candidate = (building_root / relative).resolve()
    except OSError:
        return True
    if not candidate.is_file():
        return True
    try:
        candidate_in_root = candidate.relative_to(real_root)
    except ValueError:
        return True
    return (
        len(candidate_in_root.parts) <= 2
        or candidate_in_root.parts[:2] != ("work", "step-outputs")
    )


def _runtime_concern_handoff_from_ledger(
    *,
    building_root: Path,
    source_step_ref: str,
    source_brick_ref: str,
    source_attempt_index: int,
    adopted_concern: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    """Build the adopted-concern runtime mail entry FROM THE RECORDED FACT.

    Reads the source occurrence's written transition-concern.json (the runtime
    row's formal residence in the ledger; written by record_step_output BEFORE
    adoption) and delivers the RECORDED reason_refs -- never the in-memory
    values -- with provenance (row ref + kind + recorded residence) so replay
    reads the recorded fact. Returns ``(entry, "")`` on success, or
    ``(None, hold_reason)`` fail-closed (B1) when the recorded residence is
    missing/unreadable, the recorded row is not the adopted row, the mandatory
    recorded reason_refs are empty, or a recorded address does not resolve in
    the ledger. ADDRESSES ONLY: the entry carries refs and provenance data, no
    bodies and no free-text fields.
    """

    manifest_ref = _step_output_manifest_ref(source_step_ref, source_attempt_index)
    concern_doc_ref = (
        manifest_ref[: -len("step-output.json")] + "transition-concern.json"
        if manifest_ref.endswith("step-output.json")
        else manifest_ref
    )
    body = _step_output_body_from_file(building_root, concern_doc_ref)
    if body is None:
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    try:
        document = json.loads(body)
    except ValueError:
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    if not isinstance(document, Mapping):
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    recorded = document.get("transition_concern_returned")
    if not isinstance(recorded, Mapping):
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    recorded_row_ref = _optional_text_value(recorded.get("concern_ref")) or ""
    adopted_row_ref = _optional_text_value(adopted_concern.get("concern_ref")) or ""
    if not recorded_row_ref or recorded_row_ref != adopted_row_ref:
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    raw_reason_refs = recorded.get("reason_refs")
    reason_refs = [
        text
        for text in (
            _optional_text_value(ref)
            for ref in (raw_reason_refs if isinstance(raw_reason_refs, list) else [])
        )
        if text
    ]
    if not reason_refs:
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    unresolved = _runtime_handoff_unresolved_address(building_root, reason_refs)
    if unresolved:
        return None, f"runtime_handoff_address_unresolved_in_ledger:{unresolved}"
    return (
        {
            "from_step_ref": source_step_ref,
            "from_brick_instance_ref": source_brick_ref,
            "row_kind": "transition_concern",
            "row_ref": recorded_row_ref,
            "reason_refs": list(reason_refs),
            "provenance": {
                "runtime_row_ref": _optional_text_value(
                    document.get("transition_concern_ref")
                )
                or recorded_row_ref,
                "row_kind": "transition_concern",
                "recorded_in": concern_doc_ref,
            },
        },
        "",
    )


@dataclasses.dataclass(frozen=True)
class ResumeSeed:
    """Optional seeded-initial-state for the FORWARD walk, used ONLY by resume.

    When this is ``None`` (the default), ``_run_dynamic_graph_walker`` runs from
    scratch exactly as before (zero forward-path change). When present, resume
    REHYDRATES the forward walk by handing it the recorded Agent returns +
    declared budget delta + the human/COO disposition, then DELEGATES to the SAME
    forward loop so every forward behaviour (all HOLDs, fan-in join queueing,
    nested handling, body_absent, ambiguous/none, cohort re-verify) is inherited.

    The forward walk is DETERMINISTIC over (graph topology, Agent returns, gates,
    budgets): re-running it while REPLAYING the recorded returns (instead of
    calling the provider) reproduces the exact same path up to the original HOLD.
    At the held step occurrence the disposition is applied INLINE (raise = the
    budget delta below already lets the landing adopt; reroute = the human/COO
    selected target enters the existing adoption path; forward = the held
    concern/gate HOLD is walked-on once; stop = the building is closed) and the
    loop continues to completion / the next HOLD with full forward fidelity.

    Fields:
      ``replay_returns`` -- per ``step_ref`` FIFO of recorded ``returned`` values
        (realized order). The k-th time the loop reaches ``step_ref`` it pops the
        next recorded return and REPLAYS it; once exhausted the loop runs the step
        LIVE (a continued / post-HOLD step the provider must run).
      ``gate_records`` -- per ``step_ref`` FIFO of the recorded AT-TIME
        gate_sequence_decision_record (or None), aligned 1:1 with
        ``replay_returns`` so a replayed step READS its recorded gate decision back
        (never recomputed).
      ``replay_step`` -- the recorded-return replay executor
        (``_replay_building_step_from_returned``); no provider call.
      ``budget_delta`` -- per target Brick ref budget increment to ADD to the
        declared node budget before the walk (raise disposition; empty otherwise).
      ``disposition_action`` -- ``raise`` / ``forward`` / ``stop`` / ``reroute``.
      ``held_source_step_ref`` / ``held_cascade_depth`` / ``pending_target_ref``
        -- identify the held step occurrence the disposition resolves.
      ``author_ref`` / ``paused_at_ref`` / ``hold_record`` -- carry the resume
        evidence (resumed transition_lifecycle stamping + resume_observations).
    """

    replay_returns: dict[str, list[Any]]
    gate_records: dict[str, list[Any]]
    replay_step: Callable[..., BuildingRunSupportResult]
    budget_delta: Mapping[str, int]
    disposition_action: str
    held_source_step_ref: str
    held_cascade_depth: int
    pending_target_ref: str
    author_ref: str
    paused_at_ref: str
    hold_record: Mapping[str, Any]
    existing_resume_observations: tuple[Mapping[str, Any], ...] = ()
    # FAIL-CLOSED gap-1: per step_ref the count of occurrences that COMPLETED
    # BEFORE the HOLD (the recorded completed-step frontier, derived INDEPENDENTLY
    # from the on-disk step-output ledger -- NOT from replay_returns). The k-th
    # visit to step_ref is an EXPECTED replay iff k <= this count; an expected
    # replay whose recorded return is MISSING is corrupt evidence -> fail-closed
    # (do NOT run live). Visits BEYOND this count are genuine continued/post-HOLD
    # steps that legitimately run live. Empty => no guard (forward path / no seed).
    expected_replay_counts: Mapping[str, int] = dataclasses.field(default_factory=dict)
    # Per step_ref FIFO of the original recorded_at timestamps (realized order),
    # aligned 1:1 with replay_returns, so a replayed step preserves its ORIGINAL
    # recorded_at instead of being stamped with a fresh one (gap-6 evidence
    # fidelity). Empty => no seed (forward path stamps recorded_at as before).
    replay_recorded_at: Mapping[str, list[str]] = dataclasses.field(default_factory=dict)
    # MAIL-REPAIR (0611, B3 lane 2): the reason_refs the human/COO disposition
    # row carries (read FROM raw/link.jsonl by walker_resume; B1-checked there
    # fail-closed). On a raise disposition these ADDRESSES ride to the
    # re-adopted redo landing's handoff packet. Empty => nothing rides.
    disposition_reason_refs: tuple[str, ...] = ()
    # ④ RE-INSTRUCTION: the corrected how-to the human/COO disposition row
    # carries (read FROM raw/link.jsonl by walker_resume off the SAME
    # transition_lifecycle row as the disposition_action). When non-empty it is
    # stamped onto the LIVE retried target step packet (the pending_target_ref
    # redo landing) so the redo prompt carries a fixed instruction as its own
    # labeled section. Empty => the target runs its original plan work unchanged.
    # Rides INDEPENDENTLY of disposition_reason_refs (it is not an address truck)
    # and NEVER onto a replayed pre-HOLD occurrence (gated on the live target).
    re_instruction: str = ""
    # FIX 3 (0611 replay provenance): the SELECTED disposition row's
    # discriminator from walker_resume._read_disposition_row -- the current
    # hold identity (disposition_row_paused_at_ref), the row's own raw_ref
    # (disposition_row_raw_ref), and its 1-based index among rows matching the
    # selection rule in file order (disposition_row_same_hold_index) -- so the
    # runtime-mail provenance names the SPECIFIC raw/link.jsonl row, not just
    # the file. Data only (refs + an int); empty on the forward path.
    disposition_row_provenance: Mapping[str, Any] = dataclasses.field(
        default_factory=dict
    )
    # Chat-session S2/S3 uses the same replay machinery to consume a validated
    # passive submission at the parked step, but that authority is the
    # claim+submission admission key, not a human/COO Link disposition row.
    # Default False preserves generic resume behavior.
    skip_lifecycle_stamp: bool = False
    resume_authority_ref: str = ""


_REPLAY_GATE_COMPUTE_LIVE = "__brick_protocol_compute_live_gate_at_reentry__"


def replay_gate_compute_live_record() -> Mapping[str, Any]:
    """Sentinel gate record for a submitted parked step.

    The record is in-memory only. It tells the resume seed to validate the
    submitted return through replay, then compute the gate at re-entry instead
    of reading an at-time gate record that cannot exist for a parked step.
    """

    return {"support_replay_gate": _REPLAY_GATE_COMPUTE_LIVE}


def _replay_gate_record_requests_live_compute(value: Any) -> bool:
    return isinstance(value, Mapping) and value.get("support_replay_gate") == _REPLAY_GATE_COMPUTE_LIVE


def _step_declares_gate_sequence_policy(step: Mapping[str, Any]) -> bool:
    """True iff the step's Link row declares a NON-EMPTY gate_sequence_policy.

    FAIL-CLOSED gap-5 support. Mirrors gate_sequence.run_gate_sequence_policy's own
    declaration check (a policy is a non-empty list on the Link row), so the resume
    replay path uses the SAME definition of "declares a policy" the forward walk
    used. A step with no Link row / no policy / an empty policy declares none.
    """

    rows = step.get("rows")
    if not isinstance(rows, list):
        return False
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == "Link":
            policy = row.get("gate_sequence_policy")
            return isinstance(policy, list) and len(policy) > 0
    return False


def _next_recorded_return(
    resume_seed: "ResumeSeed | None",
    step_ref: str,
    replay_consumed: dict[str, int],
) -> tuple[Any, Any, str, bool]:
    """The next recorded return + gate record + recorded_at for this occurrence.

    Returns ``(returned_value, gate_record, recorded_at, is_replay)``. When there
    is no ``resume_seed`` (forward path) or this occurrence is a genuine continued
    / post-HOLD step (its index is BEYOND the recorded completed-step frontier),
    returns ``(None, None, "", False)`` so the caller runs the step LIVE. The
    per-step FIFO cursor advances only on a replay so the k-th loop visit consumes
    the k-th recorded return.

    FAIL-CLOSED (gap-1): an occurrence at/before the recorded completed-step
    frontier (``index < expected_replay_counts[step_ref]``) is an EXPECTED replay.
    If its recorded return is MISSING (the per-step FIFO is shorter than the
    frontier says it should be), the written evidence is CORRUPT -- raise rather
    than silently run the step LIVE (which would call a provider and diverge from
    the original walk). The frontier is derived INDEPENDENTLY of replay_returns
    (the on-disk step-output ledger), so a dropped/short recorded return cannot
    masquerade as a continued step.
    """

    if resume_seed is None:
        return None, None, "", False
    index = replay_consumed.get(step_ref, 0)
    recorded = resume_seed.replay_returns.get(step_ref) or []
    expected = int(resume_seed.expected_replay_counts.get(step_ref, 0))
    if index >= expected:
        # Beyond the recorded completed-step frontier: a genuine continued /
        # post-HOLD step the provider must run live.
        return None, None, "", False
    # index < expected: this occurrence completed BEFORE the HOLD and MUST replay.
    if index >= len(recorded):
        raise ValueError(
            f"resume corrupt evidence: step {step_ref!r} occurrence {index + 1} "
            f"completed before the HOLD (recorded completed-step frontier = {expected}) "
            "but has no recorded Agent return to replay; refusing to silently run it "
            "live (would call a provider and diverge from the original walk)"
        )
    replay_consumed[step_ref] = index + 1
    gate_records = resume_seed.gate_records.get(step_ref, [])
    gate_record = gate_records[index] if index < len(gate_records) else None
    recorded_at_list = resume_seed.replay_recorded_at.get(step_ref, [])
    recorded_at = recorded_at_list[index] if index < len(recorded_at_list) else ""
    return recorded[index], gate_record, str(recorded_at or ""), True


def _has_pending_recorded_returns(
    resume_seed: "ResumeSeed",
    step_ref: str,
    replay_consumed: dict[str, int],
) -> bool:
    """True iff this step still has UNconsumed recorded returns (more replays).

    The held step occurrence is the one that consumed the LAST recorded return for
    its step_ref (the original walk broke there). When more recorded returns remain
    for this step_ref it is NOT the held occurrence yet, so the disposition must not
    fire early.
    """

    recorded = resume_seed.replay_returns.get(step_ref) or []
    return replay_consumed.get(step_ref, 0) < len(recorded)


def _resume_observation_for_hold(
    resume_seed: "ResumeSeed | None",
    hold_record: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    if resume_seed is None:
        return None
    hold_ref = _hold_paused_at_ref(hold_record)
    for observation in resume_seed.existing_resume_observations:
        if not isinstance(observation, Mapping):
            continue
        refs = {
            _optional_text_value(observation.get("paused_at_ref")),
            _optional_text_value(observation.get("resumed_from")),
        }
        provenance = observation.get("disposition_row_provenance")
        if isinstance(provenance, Mapping):
            refs.add(_optional_text_value(provenance.get("disposition_row_paused_at_ref")))
        if hold_ref in refs:
            return observation
    return None


def _resume_observations_for_frontier(
    resume_seed: "ResumeSeed | None",
    *,
    disposition_applied: bool,
    node_budget: Mapping[str, int],
    node_landings: Mapping[str, int],
) -> list[Mapping[str, Any]] | None:
    if resume_seed is None:
        return None
    observations = list(resume_seed.existing_resume_observations)
    if disposition_applied:
        observations.append(
            _build_resume_disposition_observation(
                resume_seed=resume_seed,
                node_budget=node_budget,
                node_landings=node_landings,
            )
        )
    return observations


def _stamp_resumed_lifecycle_on_held_source(
    step_results: list[BuildingRunSupportResult],
    *,
    resume_seed: "ResumeSeed",
    disposition_action: str,
    building_id: str,
    replay_step,
    checked_proof_limits: tuple[str, ...],
    held_occurrence_index: int | None = None,
) -> list[BuildingRunSupportResult]:
    """Stamp the human/COO-authored resumed transition_lifecycle on the held source.

    Mirrors the prior resume verb's ``_replace_held_source_with_lifecycle`` so the
    resumed Building's evidence shows the disposition was authored by the human/COO
    (not support). For ``stop`` it also closes the Building lifecycle. Support reads
    the disposition row; it never authors the disposition (ζ7).

    FAIL-CLOSED gap-3: ``held_occurrence_index`` pins the EXACT held step_results
    occurrence (captured in the loop when the disposition was applied). A raise
    re-adoption can run the held ``step_ref`` AGAIN at a deeper cascade AFTER the
    held occurrence, so ``_replace_held_source_with_lifecycle``'s reverse-scan
    (first same-``step_ref`` match from the end) would stamp the LATER occurrence.
    We restrict the reverse-scan to ``step_results[:index+1]`` so it lands on the
    held occurrence, then re-attach the untouched tail. When the index is unknown
    (legacy callers) we fall back to the prior whole-list behaviour.
    """

    budget_increment = None
    if disposition_action == "raise":
        budget_increment = resume_seed.budget_delta.get(resume_seed.pending_target_ref)
    building_lifecycle = None
    boundary_ref = None
    if disposition_action == "stop":
        building_lifecycle = {
            "state": "closed",
            "reason": "ended-by-disposition",
            "not_proven": ["ended-by-disposition"],
            "proof_limits": list(PROOF_LIMITS),
        }
        boundary_ref = f"building-boundary:{building_id}-ended-by-disposition-closed"
    lifecycle = _resumed_lifecycle_from_hold(
        resume_seed.hold_record,
        paused_at_ref=resume_seed.paused_at_ref,
        disposition_action=disposition_action,
        budget_increment=budget_increment,
    )
    if held_occurrence_index is not None and 0 <= held_occurrence_index < len(step_results):
        # Pin the EXACT held occurrence: scope the reverse-scan to the prefix that
        # ENDS at the held occurrence, then re-attach the untouched tail (any deeper
        # same-step_ref occurrence a raise re-adoption created stays untouched).
        head = _replace_held_source_with_lifecycle(
            step_results[: held_occurrence_index + 1],
            hold_record=resume_seed.hold_record,
            lifecycle=lifecycle,
            building_lifecycle=building_lifecycle,
            boundary_ref=boundary_ref,
            author_ref=resume_seed.author_ref or "human:unknown",
            replay_step=replay_step,
            checked_proof_limits=checked_proof_limits,
        )
        return list(head) + step_results[held_occurrence_index + 1 :]
    return _replace_held_source_with_lifecycle(
        step_results,
        hold_record=resume_seed.hold_record,
        lifecycle=lifecycle,
        building_lifecycle=building_lifecycle,
        boundary_ref=boundary_ref,
        author_ref=resume_seed.author_ref or "human:unknown",
        replay_step=replay_step,
        checked_proof_limits=checked_proof_limits,
    )


def _build_resume_disposition_observation(
    *,
    resume_seed: "ResumeSeed",
    node_budget: Mapping[str, int],
    node_landings: Mapping[str, int],
) -> Mapping[str, Any]:
    """The resume_observation recording the applied disposition (FACTS only).

    Same shape/``applied`` vocabulary the prior resume verb emitted, so the
    rewritten dynamic_walker_evidence carries an equivalent disposition record.
    """

    action = resume_seed.disposition_action
    target = resume_seed.pending_target_ref
    if resume_seed.skip_lifecycle_stamp and action == "forward":
        applied = "chat_session_submission_consumed_and_walk_continued"
    else:
        applied = {
            "raise": "budget_raised_and_held_landing_reentered",
            "forward": "forwarded_past_held_gate_without_reroute_landing",
            "stop": "closed_by_human_or_coo_disposition",
            "reroute": "rerouted_to_human_or_coo_selected_target",
        }[action]
    increment = (
        int(resume_seed.budget_delta.get(target, 0)) if action == "raise" else 0
    )
    not_proven = (
        ["ended-by-disposition", *RESUME_NOT_PROVEN]
        if action == "stop"
        else list(
            _merge_texts(
                RESUME_NOT_PROVEN,
                (
                    "chat-session claim/submission semantic correctness",
                    "chat-session performer quality",
                )
                if resume_seed.skip_lifecycle_stamp
                else (),
            )
        )
    )
    return build_resume_observation(
        resumed_from=resume_seed.paused_at_ref,
        paused_at_ref=resume_seed.paused_at_ref,
        pending_target_ref=target,
        disposition_action=action,
        applied=applied,
        budget_increment=increment,
        node_budget=int(node_budget.get(target, 0)),
        node_landings=int(node_landings.get(target, 0)),
        proof_limits=list(PROOF_LIMITS),
        not_proven=not_proven,
        # FIX 3 (0611): PERSIST the selected disposition row's discriminator
        # (generation-unique hold identity + the row's own raw_ref + the
        # pre-resume-snapshot match index) into the written resume
        # observation. The transient ResumeSeed provenance alone dangles on a
        # later replay because the resume REWRITES raw/link.jsonl
        # (raw_claim_trace._write_jsonl uses write_text, not append).
        disposition_row_provenance=(
            dict(resume_seed.disposition_row_provenance)
            if resume_seed.disposition_row_provenance
            else None
        ),
    )


def _report_policy_uses_brick_grain(policy: Mapping[str, Any] | None) -> bool:
    return bool(policy and policy.get("report_event_grain") == "brick")


def _emit_brick_received_step_event(
    policy: Mapping[str, Any] | None,
    *,
    linear_plan: Mapping[str, Any],
    building_id: str,
    building_root: Path | str,
    repo_root: Path,
    current_brick_ref: str,
    step_ref: str,
    step_index: int,
    report_env: Mapping[str, str] | None,
    report_slack_sender: Any | None,
    overwrite_existing: bool,
) -> tuple[Mapping[str, Any], ...]:
    if not _report_policy_uses_brick_grain(policy):
        return ()
    context = _brick_grain_step_received_context(
        linear_plan=linear_plan,
        step_ref=step_ref,
        step_index=step_index,
        received_at=graph_ready_timestamp(),
    )
    event = _emit_building_event_best_effort(
        policy,
        event_kind="brick_received",
        building_id=building_id,
        building_root=building_root,
        repo_root=repo_root,
        current_brick_ref=current_brick_ref,
        overwrite_existing=overwrite_existing,
        report_env=report_env,
        report_slack_sender=report_slack_sender,
        event_context={**context, "event_stage": "brick_received"},
    )
    return (event,) if event is not None else ()


def _emit_brick_grain_completion_step_events(
    policy: Mapping[str, Any] | None,
    *,
    linear_plan: Mapping[str, Any],
    building_id: str,
    building_root: Path | str,
    repo_root: Path,
    step_result: BuildingRunSupportResult,
    step_index: int,
    attempt_index: int,
    gate_sequence_decision: GateSequenceDecision,
    report_env: Mapping[str, str] | None,
    report_slack_sender: Any | None,
    overwrite_existing: bool,
) -> tuple[Mapping[str, Any], ...]:
    if not _report_policy_uses_brick_grain(policy):
        return ()
    step_ref = step_result.preparation.step_rows.step_ref
    context = _brick_grain_step_context(
        step_result,
        linear_plan=linear_plan,
        step_index=step_index,
        gate_sequence_decision=gate_sequence_decision,
    )
    last_completed_step_ref = _step_output_manifest_ref(step_ref, attempt_index)
    observations: list[Mapping[str, Any]] = []
    for event_kind in ("brick_returned", "gate_passed"):
        event = _emit_building_event_best_effort(
            policy,
            event_kind=event_kind,
            building_id=building_id,
            building_root=building_root,
            repo_root=repo_root,
            current_brick_ref=step_result.preparation.brick_instance_ref,
            overwrite_existing=overwrite_existing,
            report_env=report_env,
            report_slack_sender=report_slack_sender,
            last_completed_step_ref=last_completed_step_ref,
            event_context={**context, "event_stage": event_kind},
        )
        if event is not None:
            observations.append(event)
    return tuple(observations)


def _brick_grain_step_received_context(
    *,
    linear_plan: Mapping[str, Any],
    step_ref: str,
    step_index: int,
    received_at: str,
) -> Mapping[str, Any]:
    return {
        "step_ref": step_ref,
        "sequence_index": step_index,
        "work_kind": _brick_grain_work_kind_for_step_ref(linear_plan, step_ref),
        "received_at": received_at,
    }


def _brick_grain_step_context(
    step_result: BuildingRunSupportResult,
    *,
    linear_plan: Mapping[str, Any],
    step_index: int,
    gate_sequence_decision: GateSequenceDecision,
) -> Mapping[str, Any]:
    recorded_at = step_result.recorded_at or ""
    next_brick_ref = step_result.preparation.next_brick_instance_ref
    step_ref = step_result.preparation.step_rows.step_ref
    return {
        "step_ref": step_ref,
        "sequence_index": step_index,
        "work_kind": _brick_grain_work_kind_for_step_ref(linear_plan, step_ref),
        "received_at": recorded_at,
        "returned_at": recorded_at,
        "returned_summary": "반환 기록됨",
        "gate_note": _brick_grain_gate_note(gate_sequence_decision),
        "next_brick_instance_ref": next_brick_ref,
        "next_work_kind": _brick_grain_next_work_kind(linear_plan, next_brick_ref),
    }


def _brick_grain_work_kind_for_step_ref(linear_plan: Mapping[str, Any], step_ref: str) -> str:
    if not step_ref:
        return ""
    steps = linear_plan.get("steps")
    if not isinstance(steps, list):
        return ""
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        if str(step.get("step_ref") or "").strip() != step_ref:
            continue
        return _brick_grain_work_kind_from_step(step)
    return ""


def _brick_grain_next_work_kind(linear_plan: Mapping[str, Any], next_brick_ref: str) -> str:
    if not next_brick_ref or next_brick_ref.startswith("building-boundary"):
        return ""
    steps = linear_plan.get("steps")
    if not isinstance(steps, list):
        return ""
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        try:
            brick_ref = _brick_instance_ref_from_linear_step(step)
        except ValueError:
            continue
        if brick_ref != next_brick_ref:
            continue
        return _brick_grain_work_kind_from_step(step)
    return ""


def _brick_grain_work_kind_from_step(step: Mapping[str, Any]) -> str:
    step_template_ref = str(step.get("step_template_ref") or "").strip()
    prefix = "building-step-template:"
    return step_template_ref.removeprefix(prefix) if step_template_ref.startswith(prefix) else ""


def _brick_grain_gate_note(gate_sequence_decision: GateSequenceDecision) -> str:
    if gate_sequence_decision.action == "hold":
        return "홀드"
    if gate_sequence_decision.action == "reroute":
        return "통과→다음스텝"
    return "통과→다음스텝"


def _emit_disposition_applied_event(
    policy: Mapping[str, Any] | None,
    *,
    building_id: str,
    building_root: Path | str,
    repo_root: Path,
    current_brick_ref: str,
    resume_seed: ResumeSeed,
    report_env: Mapping[str, str] | None,
    report_slack_sender: Any | None,
    overwrite_existing: bool,
) -> Mapping[str, Any] | None:
    if not _report_policy_uses_brick_grain(policy) or resume_seed.skip_lifecycle_stamp:
        return None
    return _emit_building_event_best_effort(
        policy,
        event_kind="disposition_applied",
        building_id=building_id,
        building_root=building_root,
        repo_root=repo_root,
        current_brick_ref=current_brick_ref,
        overwrite_existing=overwrite_existing,
        report_env=report_env,
        report_slack_sender=report_slack_sender,
        event_context={
            "disposition_action": resume_seed.disposition_action,
            "disposition_author_ref": resume_seed.author_ref,
            "applied_at": "",
        },
    )


def _emit_building_event_best_effort(
    policy: Mapping[str, Any] | None,
    *,
    event_kind: str,
    building_id: str,
    building_root: Path | str,
    repo_root: Path,
    current_brick_ref: str = "",
    last_completed_step_ref: str = "",
    overwrite_existing: bool,
    report_env: Mapping[str, str] | None = None,
    report_slack_sender: Any | None = None,
    event_context: Mapping[str, Any] | None = None,
) -> Mapping[str, Any] | None:
    if not event_kind:
        return None
    try:
        return emit_building_event_for_policy(
            policy,
            event_kind=event_kind,
            building_id=building_id,
            building_root=building_root,
            current_brick_ref=current_brick_ref,
            last_completed_step_ref=last_completed_step_ref,
            repo_root=_report_repo_root_for_building_root(building_root, fallback_repo=repo_root),
            overwrite_existing=overwrite_existing,
            slack_env=report_env,
            slack_sender=report_slack_sender,
            dashboard_env=report_env,
            event_context=event_context,
        )
    except Exception as exc:  # noqa: BLE001 - notification must never break evidence write.
        return {
            "report_event_observation": "delivery_exception_observed",
            "event_kind": event_kind,
            "building_id": building_id,
            "delivery_status_class": "exception_observed",
            "provider_response_status_class": exc.__class__.__name__,
            "reason": str(exc),
            "source_truth": False,
            "proof_limits": [
                "support notification observation only",
                "notification exception was not allowed to break Building evidence write",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "event delivery reliability",
                "reader noticed event notification",
            ],
        }


def _report_repo_root_for_building_root(
    building_root: Path | str,
    *,
    fallback_repo: Path,
) -> Path:
    root = Path(building_root).resolve()
    try:
        root.relative_to(fallback_repo)
        return fallback_repo
    except ValueError:
        pass
    parts = root.parts
    for index, part in enumerate(parts):
        if part == "project" and index + 2 < len(parts) and parts[index + 2] == "buildings":
            return Path(*parts[:index]) if index else Path(".").resolve()
    if root.parent.name == "buildings":
        return root.parent.parent
    return root.parent


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
    step_result_event: Mapping[str, Any] | None = None
    step_output_recorded: bool = True


_STEP_OUTPUT_HANDOFF_PROOF_LIMITS = (
    "support carry metadata only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
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
    building_root_path = str(building_root.resolve())
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
        enriched_entry["building_root_path"] = building_root_path
        enriched_entry.setdefault("proof_limits", list(_STEP_OUTPUT_HANDOFF_PROOF_LIMITS))
        enriched_incoming.append(enriched_entry)
        changed = True
    if not changed:
        return handoff_refs

    enriched_handoffs = dict(handoff_refs)
    enriched_handoffs["incoming"] = enriched_incoming
    return enriched_handoffs


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
            step_result = run_step(
                step_fixture,
                local_callables=local_callables,
                command_runner=command_runner,
                adapter_cwd=adapter_cwd,
                adapter_timeout_seconds=adapter_timeout_seconds,
                proof_limits=checked_proof_limits,
            )
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
    if resume_seed is not None or not has_fan_groups:
        dispatch_pool_size = 1
    elif not _has_explicit_fanout_pool_override(linear_plan):
        # A drawn fan IS the parallel declaration -> run concurrent by default.
        # HOLD-safe (joins batch-terminal) + record stays canonical (FIFO drain).
        # Explicit override above still wins; resume stays serial.
        dispatch_pool_size = _FANOUT_AUTO_POOL
    pending_outcomes: list[tuple[dict[str, Any], NodeProcessingOutcome]] = []

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
    ) -> list[tuple[dict[str, Any], NodeProcessingOutcome]]:
        try:
            if len(items) == 1:
                return [
                    (
                        items[0],
                        _process_item(
                            items[0],
                            record_step_output_immediately=False,
                            defer_frontier_writes=True,
                        ),
                    )
                ]
            worker_count = min(dispatch_pool_size, len(items))
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
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
                return [(item, future.result()) for item, future in futures]
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
            held=False,
            hold_record=None,
            cascade_depth=int(item.get("cascade_depth", 0)),
            parent_reroute_ref=item["parent_reroute_ref"],
            fan_in_wait_all_observations=fan_in_wait_all_observations,
            has_fan_groups=has_fan_groups,
            write_adapter_error_frontier=write_adapter_error_frontier,
            adapter_frontier_exception=adapter_frontier_exception,
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
            if dispatch_pool_size > 1:
                ready_result = frontier_driver.ready_items(
                    max_items=dispatch_pool_size,
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
                pending_outcomes.extend(_dispatch_ready_batch(ready_result.items))
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
                if previous_disposition.get("disposition_action") != "forward":
                    raise ValueError(
                        "resume replay encountered an already-disposed recorded HOLD "
                        f"for {step_ref!r} with unsupported prior disposition "
                        f"{previous_disposition.get('disposition_action')!r}"
                    )
                if has_fan_groups:
                    frontier_driver.splice_declared_successors_after_current(
                        source_step_ref=step_ref,
                        cascade_depth=cascade_depth,
                        parent_reroute_ref=item["parent_reroute_ref"],
                        successors_by_source=fan_successors_by_source,
                    )
                continue
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
                # An Agent named EITHER several resolving nodes (ambiguous: no single
                # owner) OR none that resolve while a concern IS present (none: an
                # unaddressable concern). The machine must NOT pick one and must NOT
                # silently drop the concern -> HOLD (BUDGET-FREE: no node_landings /
                # node_budget touched; this is a pause, not a reroute LANDING). The
                # human/COO authors the disposition (caller-or-coo).
                hold_target = brick_ref_by_step[step_ref]
                # The classifier may stamp a SPECIFIC hold_reason (e.g. an
                # unresolvable brick-targeting address co-occurring with a valid
                # one -> unresolvable_reroute_address); otherwise derive the reason
                # from the kind (ambiguous vs none).
                hold_reason = target_classification.hold_reason or (
                    "multiple_reroute_addresses_no_single_owner"
                    if target_classification.kind == "ambiguous"
                    else "no_resolving_reroute_address"
                )
                adoption_sequence_number += 1
                hold_record = _build_hold(
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
            else:
                target_brick = target_classification.target
                gate = _gate_disposition_for_step(step)
                if gate == "pause":
                    # human:/coo: gate on the reroute -> PAUSE (transition_lifecycle paused).
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
                        hold_reason="human_or_coo_gate_pause",
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

                # Default/template gate -> auto-adopt IF the target node budget is available.
                budget = node_budget.get(target_brick)
                if budget is None:
                    # A reroute target with no Link-assigned budget cannot be adopted; the
                    # bound depends on every target having a finite budget. HOLD.
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
                        node_budget=0,
                        attempt_number=0,
                        budget_exhausted=True,
                        hold_reason="target_node_has_no_link_assigned_budget",
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

                if node_landings[target_brick] >= budget:
                    # Budget EXHAUSTED -> the next reroute landing is NOT adopted. HOLD.
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
                        node_budget=budget,
                        attempt_number=node_landings[target_brick],
                        budget_exhausted=True,
                        hold_reason="target_node_budget_exhausted",
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
                frontier_driver.splice_after_current(appended)
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
    object.__setattr__(result, "_dynamic_walker_reroute_records", tuple(reroute_records))
    object.__setattr__(
        result,
        "_dynamic_walker_evidence",
        write_plan["dynamic_walker_evidence"],
    )
    if report_event_observations:
        object.__setattr__(
            result,
            "_report_event_observations",
            tuple(report_event_observations),
        )
    return result

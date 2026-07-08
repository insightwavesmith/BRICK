"""Step-output drain behavioral profile runners.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.fixture_graph_helpers import (
    fixture_agent_row,
    fixture_brick_row,
    fixture_graph_brick_step,
    fixture_graph_link_edge,
    fixture_proof_limits,
)
from brick_protocol.support.checkers.lib.plan_fixture_helpers import _graph_test_plan_from_linear
from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)
from brick_protocol.support.recording.capture import project_ref_for_building_root


def run_step_output_drain_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "step_output_drain_case")
    if not items:
        return 0
    from brick_protocol.support.operator.run import run_building_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "step_output_drain_case item")
        label = require_string(mapping.get("label"), "step_output_drain_case.label")
        case_kind = require_string(mapping.get("case_kind"), f"{label}: case_kind")
        plan, _walker_mode = _step_output_drain_plan(case_kind, missing=False)
        if case_kind == "live_dynamic_full_replay_n3":
            _check_dynamic_full_replay_policy(plan, label=label)
        expected = require_mapping(mapping.get("expected", {}), f"{label}: expected")
        with tempfile.TemporaryDirectory(prefix="bp-step-output-drain-") as tmpdir:
            output_root = Path(tmpdir)
            observed = _StepOutputDrainObserved(
                output_root=output_root,
                reroute_once_from_brick=(
                    "brick-replay-closure-a"
                    if case_kind == "live_dynamic_full_replay_n3"
                    else "brick-qa-reroute-code-attack-qa"
                    if case_kind == "live_qa_reroute_to_work_n2"
                    else ""
                ),
                reroute_target_brick=(
                    "brick-replay-work-b"
                    if case_kind == "live_dynamic_full_replay_n3"
                    else "brick-qa-reroute-work"
                    if case_kind == "live_qa_reroute_to_work_n2"
                    else ""
                ),
                source_lane_concerns_by_brick=(
                    _source_lane_transition_concern_fixture()
                    if case_kind == "live_dynamic_fan_in_source_concerns_n4"
                    else None
                ),
            )
            result, batch_step_output_write_calls = _run_step_output_drain_plan(
                plan,
                output_root=output_root,
                observed=observed,
                repo=repo,
            )
            if batch_step_output_write_calls:
                raise ProfileError(
                    f"step_output_drain_case rejected {label}: accumulated "
                    "evidence batch touched step-output persistence after "
                    "per-event drain"
                )
            if case_kind == "live_dynamic_full_replay_n3":
                _check_dynamic_full_replay_expected(
                    result,
                    observed,
                    expected,
                    label=label,
                )
            elif case_kind == "live_qa_reroute_to_work_n2":
                _check_qa_reroute_expected(
                    result,
                    expected,
                    label=label,
                )
            elif case_kind == "live_dynamic_fan_in_source_concerns_n4":
                _check_source_lane_transition_concerns_expected(
                    result,
                    expected,
                    label=label,
                )
            else:
                _check_step_output_drain_expected(
                    result,
                    result.lifecycle_write.root,
                    observed,
                    expected,
                    label=label,
                )
        count += 1
    return count


def _run_step_output_drain_plan(
    plan: Mapping[str, Any],
    *,
    output_root: Path,
    observed: "_StepOutputDrainObserved",
    repo: Path,
) -> tuple[Any, int]:
    from brick_protocol.support.operator import evidence_assembly
    from brick_protocol.support.operator.run import run_building_plan

    calls = 0
    original_write_step_outputs = evidence_assembly.write_step_outputs

    def _observed_batch_write_step_outputs(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return original_write_step_outputs(*args, **kwargs)

    evidence_assembly.write_step_outputs = _observed_batch_write_step_outputs
    try:
        result = run_building_plan(
            plan,
            output_root=output_root,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": observed.callable},
            adapter_cwd=repo,
            adapter_timeout_seconds=10,
        )
    finally:
        evidence_assembly.write_step_outputs = original_write_step_outputs
    return result, calls


def run_step_output_drain_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "step_output_drain_rejects")
    if not items:
        return 0
    from brick_protocol.support.operator.run import _source_fact_bodies, run_building_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "step_output_drain_rejects item")
        label = require_string(mapping.get("label"), "step_output_drain_rejects.label")
        case_kind = require_string(mapping.get("case_kind"), f"{label}: case_kind")
        expected_message = require_string(
            mapping.get("expected_message"),
            f"{label}: expected_message",
        )
        try:
            if case_kind == "step_output_source_fact_disk_fallback_rejected":
                _source_fact_bodies(("work/step-outputs/missing-attempt-1/step-output.json",))
            elif case_kind == "live_dynamic_partial_replay_rejected":
                plan, _walker_mode = _step_output_drain_plan(case_kind, missing=True)
                try:
                    _check_dynamic_full_replay_policy(plan, label=label)
                except ProfileError as exc:
                    if expected_message not in str(exc):
                        raise ProfileError(
                            f"step_output_drain_rejects rejected {label}: "
                            f"expected message {expected_message!r}, observed {str(exc)!r}"
                        ) from exc
                    count += 1
                    continue
            elif case_kind == "live_dynamic_missing_step_output_body":
                plan, _walker_mode = _step_output_drain_plan(case_kind, missing=True)
                with tempfile.TemporaryDirectory(prefix="bp-step-output-drain-red-") as tmpdir:
                    observed = _StepOutputDrainObserved(output_root=Path(tmpdir))
                    result = run_building_plan(
                        plan,
                        output_root=Path(tmpdir),
                        overwrite_existing=True,
                        local_callables={
                            "callable:local:agent-invoke0-smoke": observed.callable
                        },
                        adapter_cwd=repo,
                        adapter_timeout_seconds=10,
                    )
                    _check_step_output_drain_dynamic_hold(
                        result,
                        observed,
                        mapping,
                        label=label,
                    )
                count += 1
                continue
            else:
                plan, _walker_mode = _step_output_drain_plan(case_kind, missing=True)
                with tempfile.TemporaryDirectory(prefix="bp-step-output-drain-red-") as tmpdir:
                    observed = _StepOutputDrainObserved(output_root=Path(tmpdir))
                    run_building_plan(
                        plan,
                        output_root=Path(tmpdir),
                        overwrite_existing=True,
                        local_callables={
                            "callable:local:agent-invoke0-smoke": observed.callable
                        },
                        adapter_cwd=repo,
                        adapter_timeout_seconds=10,
                    )
        except (TypeError, ValueError) as exc:
            if expected_message not in str(exc):
                raise ProfileError(
                    f"step_output_drain_rejects rejected {label}: "
                    f"expected message {expected_message!r}, observed {str(exc)!r}"
                ) from exc
            count += 1
            continue
        raise ProfileError(f"step_output_drain_rejects expected rejection but passed: {label}")
    return count


@dataclass
class _StepOutputDrainObserved:
    output_root: Path
    reroute_once_from_brick: str = ""
    reroute_target_brick: str = ""
    source_lane_concerns_by_brick: Mapping[str, Any] | None = None
    events: list[Mapping[str, Any]] | None = None
    body_text_at_call: dict[str, str] | None = None
    _reroute_emitted: bool = False

    def __post_init__(self) -> None:
        if self.events is None:
            self.events = []
        if self.body_text_at_call is None:
            self.body_text_at_call = {}

    def callable(self, request: Any) -> Mapping[str, Any]:
        refs = list(request.source_fact_bodies)
        file_exists: dict[str, bool] = {}
        markers: list[str] = []
        from brick_protocol.support.operator.walker_kernel import wiki_carry_summary_text

        for ref, body in request.source_fact_bodies.items():
            relative_ref = _checker_step_output_relative_ref(ref)
            path = self.output_root / request.building_id / relative_ref
            file_exists[ref] = path.is_file()
            if path.is_file():
                self.body_text_at_call[ref] = path.read_text(encoding="utf-8")
            # WIKI-CARRY: the carried body is a compact wiki view; the worker's
            # curated `returned` rides in the summary section, not the full
            # step-output JSON. Recover the summary and parse it back.
            summary = wiki_carry_summary_text(body)
            if summary is None:
                markers.append("")
                continue
            try:
                returned = json.loads(summary)
            except json.JSONDecodeError:
                markers.append("")
                continue
            markers.append(
                str(returned.get("body_marker"))
                if isinstance(returned, Mapping) and returned.get("body_marker") is not None
                else ""
            )
        assert self.events is not None
        self.events.append(
            {
                "brick_instance_ref": request.brick_instance_ref,
                "source_fact_body_refs": refs,
                "carried_markers": markers,
                "source_fact_files_existed_at_call": file_exists,
                "link_handoff_refs": dict(request.link_handoff_refs),
            }
        )
        returned: dict[str, Any] = {
            "body_marker": request.brick_instance_ref,
            "source_fact_body_refs": refs,
            "carried_markers": markers,
            "not_proven": ["checker live runner proof only"],
        }
        if (
            self.reroute_once_from_brick
            and self.reroute_target_brick
            and request.brick_instance_ref == self.reroute_once_from_brick
            and not self._reroute_emitted
        ):
            self._reroute_emitted = True
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": [self.reroute_target_brick],
            }
        if (
            self.source_lane_concerns_by_brick
            and request.brick_instance_ref in self.source_lane_concerns_by_brick
        ):
            returned["transition_concern_evidence"] = self.source_lane_concerns_by_brick[
                request.brick_instance_ref
            ]
        return returned


def _check_step_output_drain_expected(
    result: Any,
    building_root: Path,
    observed: _StepOutputDrainObserved,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    consumer_brick = require_string(
        expected.get("consumer_brick_instance_ref"),
        f"{label}: expected.consumer_brick_instance_ref",
    )
    expected_refs = require_string_list(
        expected.get("source_fact_body_refs", []),
        f"{label}: expected.source_fact_body_refs",
    )
    expected_markers = require_string_list(
        expected.get("carried_markers", []),
        f"{label}: expected.carried_markers",
    )
    events = observed.events or []
    consumer_events = [
        event for event in events if event.get("brick_instance_ref") == consumer_brick
    ]
    if len(consumer_events) != 1:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: consumer event count "
            f"expected 1, observed {len(consumer_events)}"
        )
    consumer_event = consumer_events[0]
    if consumer_event.get("source_fact_body_refs") != expected_refs:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source_fact_body_refs mismatch"
        )
    if consumer_event.get("carried_markers") != expected_markers:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: carried_markers mismatch"
        )
    file_exists = require_mapping(
        consumer_event.get("source_fact_files_existed_at_call"),
        f"{label}: source_fact_files_existed_at_call",
    )
    for ref in expected_refs:
        if not file_exists.get(ref):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {ref} was not on disk at consumer call"
            )
        final_text = (building_root / _checker_step_output_relative_ref(ref)).read_text(
            encoding="utf-8"
        )
        observed_text = (observed.body_text_at_call or {}).get(ref)
        if observed_text != final_text:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: final step-output rewrote {ref}"
            )
    if expected.get("carry_gate_sufficiency") is not None:
        dynamic_evidence = require_mapping(
            getattr(result, "_dynamic_walker_evidence", {}),
            f"{label}: _dynamic_walker_evidence",
        )
        observations = dynamic_evidence.get("source_fact_body_carry_observations")
        if not isinstance(observations, list):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: dynamic carry observations missing"
            )
        matching = [
            item
            for item in observations
            if isinstance(item, Mapping)
            and item.get("target_step_ref") == expected.get("consumer_step_ref")
        ]
        if len(matching) != 1:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: carry observation count "
                f"expected 1, observed {len(matching)}"
            )
        carry_gate = require_mapping(
            matching[0].get("carry_gate_observation"),
            f"{label}: carry_gate_observation",
        )
        expected_sufficiency = require_string(
            expected.get("carry_gate_sufficiency"),
            f"{label}: expected.carry_gate_sufficiency",
        )
        if carry_gate.get("sufficiency") != expected_sufficiency:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: carry gate sufficiency mismatch"
            )
        if carry_gate.get("missing_required_facts") != expected.get(
            "carry_gate_missing_required_facts",
            [],
        ):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: carry gate missing facts mismatch"
            )
    if expected.get("incoming_step_output_refs") is not None:
        expected_step_output_refs = require_string_list(
            expected.get("incoming_step_output_refs", []),
            f"{label}: expected.incoming_step_output_refs",
        )
        handoff_refs = require_mapping(
            consumer_event.get("link_handoff_refs"),
            f"{label}: link_handoff_refs",
        )
        incoming = handoff_refs.get("incoming")
        if not isinstance(incoming, list):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: incoming handoff refs missing"
            )
        observed_step_output_refs = [
            item.get("from_step_output_ref")
            for item in incoming
            if isinstance(item, Mapping) and item.get("from_step_output_ref") is not None
        ]
        if observed_step_output_refs != expected_step_output_refs:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: incoming step-output refs mismatch"
            )
        project_ref = project_ref_for_building_root(building_root)
        expected_root_ref = (
            f"project/{project_ref[len('project:'):]}/buildings/{building_root.name}"
            if project_ref
            else None
        )
        observed_roots = [
            item.get("building_root_ref")
            for item in incoming
            if isinstance(item, Mapping) and item.get("from_step_output_ref") is not None
        ]
        if expected_root_ref is None:
            expected_roots: list[str | None] = [None for _ in expected_step_output_refs]
        else:
            expected_roots = [expected_root_ref for _ in expected_step_output_refs]
        if observed_roots != expected_roots:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: incoming building_root_ref mismatch"
            )
    if expected.get("receipt_handoff_refs") is not None:
        expected_receipt_refs = require_string_list(
            expected.get("receipt_handoff_refs", []),
            f"{label}: expected.receipt_handoff_refs",
        )
        consumer_results = [
            step_result
            for step_result in getattr(result, "step_results", ())
            if step_result.preparation.brick_instance_ref == consumer_brick
        ]
        if len(consumer_results) != 1:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: consumer receipt count "
                f"expected 1, observed {len(consumer_results)}"
            )
        observed_receipt_refs = list(
            consumer_results[0].preparation.receipt_fact.received_handoff_refs
        )
        if observed_receipt_refs != expected_receipt_refs:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: receipt handoff refs mismatch"
            )


def _check_step_output_drain_dynamic_hold(
    result: Any,
    observed: _StepOutputDrainObserved,
    mapping: Mapping[str, Any],
    *,
    label: str,
) -> None:
    expected_hold_reason = require_string(
        mapping.get("expected_hold_reason"),
        f"{label}: expected_hold_reason",
    )
    dynamic_evidence = require_mapping(
        getattr(result, "_dynamic_walker_evidence", {}),
        f"{label}: _dynamic_walker_evidence",
    )
    if dynamic_evidence.get("held") is not True:
        raise ProfileError(f"step_output_drain_rejects rejected {label}: dynamic run did not HOLD")
    hold = require_mapping(dynamic_evidence.get("hold"), f"{label}: dynamic hold")
    if hold.get("hold_reason") != expected_hold_reason:
        raise ProfileError(
            f"step_output_drain_rejects rejected {label}: hold_reason mismatch"
        )
    observation = require_mapping(
        hold.get("fan_in_wait_all_observation"),
        f"{label}: fan_in_wait_all_observation",
    )
    carry_gate = require_mapping(
        observation.get("carry_gate_observation"),
        f"{label}: carry_gate_observation",
    )
    if carry_gate.get("sufficiency") != "missing_required_facts":
        raise ProfileError(
            f"step_output_drain_rejects rejected {label}: carry gate was not missing_required_facts"
        )
    if not carry_gate.get("missing_required_facts"):
        raise ProfileError(
            f"step_output_drain_rejects rejected {label}: missing_required_facts empty"
        )
    closure_events = [
        event
        for event in (observed.events or [])
        if event.get("brick_instance_ref") == "brick-fan-closure"
    ]
    if closure_events:
        raise ProfileError(
            f"step_output_drain_rejects rejected {label}: closure was called despite HOLD"
        )


def _check_dynamic_full_replay_policy(plan: Mapping[str, Any], *, label: str) -> None:
    from brick_protocol.support.operator.plan_graph import (
        _graph_fan_in_sources_by_target_step_ref,
        _graph_fan_out_targets_by_source_step_ref,
        _linear_plan_from_graph_plan,
    )

    linear_plan, graph_context = _linear_plan_from_graph_plan(plan)
    fan_out_targets = _graph_fan_out_targets_by_source_step_ref(graph_context)
    fan_in_sources = _graph_fan_in_sources_by_target_step_ref(graph_context)
    brick_by_step = _brick_ref_by_step(linear_plan)
    step_by_brick = {brick_ref: step_ref for step_ref, brick_ref in brick_by_step.items()}
    for step in linear_plan.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        link_row = _axis_row(step, "Link")
        route_plan = link_row.get("route_replay_plan")
        if not isinstance(route_plan, Mapping):
            continue
        immediate_target = require_string(
            route_plan.get("immediate_target_ref"),
            f"{label}: route_replay_plan.immediate_target_ref",
        )
        target_step = step_by_brick.get(immediate_target)
        if target_step is None:
            continue
        target_fan_out = list(fan_out_targets.get(target_step, ()))
        if len(target_fan_out) < 2:
            continue
        closure_targets = [
            candidate
            for candidate, sources in fan_in_sources.items()
            if set(sources) == set(target_fan_out)
        ]
        if len(closure_targets) != 1:
            raise ProfileError(
                f"dynamic_full_replay_policy rejected {label}: "
                "replay fan-in closure target was not uniquely declared"
            )
        observed = require_string_list(
            route_plan.get("replay_segment_refs", []),
            f"{label}: route_replay_plan.replay_segment_refs",
        )
        if observed:
            raise ProfileError(
                f"dynamic_full_replay_policy rejected {label}: "
                "partial QA reuse is not admitted; graph fan-in full replay must "
                "reroute to the work target and let the declared fan-out/fan-in "
                "segment replay the QA cohort plus closure"
            )


def _check_dynamic_full_replay_expected(
    result: Any,
    observed: _StepOutputDrainObserved,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    events = observed.events or []
    source_brick = require_string(
        expected.get("reroute_source_brick_instance_ref"),
        f"{label}: expected.reroute_source_brick_instance_ref",
    )
    consumer_brick = require_string(
        expected.get("consumer_brick_instance_ref"),
        f"{label}: expected.consumer_brick_instance_ref",
    )
    replay_window = require_string_list(
        expected.get("replay_window_brick_instance_refs", []),
        f"{label}: expected.replay_window_brick_instance_refs",
    )
    # CANONICAL-ORDER ORACLE (P6-C parallel fix): the ORDERED replay window is
    # asserted on the RECORDED ledger (result.step_results), NOT on
    # observed.events. observed.events is appended INSIDE the agent callable at
    # invocation time, so under pool>1 the fan-out siblings (code/axis/evidence
    # QA) append in thread-COMPLETION order -- a race that has nothing to do with
    # what BRICK persisted. The drain (walker_kernel._drain_pending_outcomes_
    # before_terminal) records step_results in canonical frontier/declaration
    # order, byte-identical for pool=1 and pool=N. So derive the window from the
    # persisted ledger; the events hook stays the source of truth only for the
    # ORDER-INDEPENDENT carry/marker/source-fact assertions below.
    recorded = [
        str(step_result.preparation.brick_instance_ref)
        for step_result in result.step_results
    ]
    try:
        # LAST occurrence of the reroute source: it is the step the human reroute
        # fired from; the replay segment is everything recorded AFTER it.
        source_index = max(
            index for index, ref in enumerate(recorded) if ref == source_brick
        )
    except ValueError as exc:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: reroute source was not recorded"
        ) from exc
    try:
        # FIRST occurrence of the consumer (fan-in closure) AFTER the source.
        closure_index = next(
            index
            for index, ref in enumerate(recorded)
            if ref == consumer_brick and index > source_index
        )
    except StopIteration as exc:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: replay closure was not recorded"
        ) from exc
    recorded_slice = recorded[source_index + 1 : closure_index + 1]
    if recorded_slice != replay_window:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: full replay window mismatch "
            f"(got={recorded_slice}, expected={replay_window})"
        )
    # Order-independent: the consumer event must still carry the full QA cohort
    # (set/membership + marker check), unaffected by sibling completion order.
    _check_replay_closure_carry(events, expected, label=label)
    dynamic_evidence = require_mapping(
        getattr(result, "_dynamic_walker_evidence", {}),
        f"{label}: _dynamic_walker_evidence",
    )
    records = getattr(result, "_dynamic_walker_reroute_records", ())
    adopted = [
        record
        for record in records
        if isinstance(record, Mapping) and not record.get("disposition_required")
    ]
    if len(adopted) != 1:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: expected one adopted reroute, observed {len(adopted)}"
        )
    expected_replay_steps = require_string_list(
        expected.get("replay_segment_step_refs", []),
        f"{label}: expected.replay_segment_step_refs",
    )
    if adopted[0].get("replay_segment_refs") != expected_replay_steps:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: adopted replay_segment_refs mismatch"
        )
    if dynamic_evidence.get("held") is True:
        raise ProfileError(f"step_output_drain_case rejected {label}: dynamic replay held")


def _check_qa_reroute_expected(
    result: Any,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    recorded = [
        str(step_result.preparation.brick_instance_ref)
        for step_result in result.step_results
    ]
    expected_recorded = require_string_list(
        expected.get("recorded_brick_instance_refs", []),
        f"{label}: expected.recorded_brick_instance_refs",
    )
    if recorded != expected_recorded:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: recorded reroute sequence mismatch "
            f"(got={recorded}, expected={expected_recorded})"
        )
    records = getattr(result, "_dynamic_walker_reroute_records", ())
    adopted = [
        record
        for record in records
        if isinstance(record, Mapping) and not record.get("disposition_required")
    ]
    if len(adopted) != 1:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: expected one adopted QA reroute, observed {len(adopted)}"
        )
    expected_target = require_string(
        expected.get("adopted_target_ref"),
        f"{label}: expected.adopted_target_ref",
    )
    observed_target = str(
        adopted[0].get("target_ref")
        or adopted[0].get("target_brick_ref")
        or adopted[0].get("pending_target_ref")
        or ""
    )
    if observed_target and observed_target != expected_target:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: adopted target mismatch "
            f"(got={observed_target!r}, expected={expected_target!r})"
        )
    dynamic_evidence = require_mapping(
        getattr(result, "_dynamic_walker_evidence", {}),
        f"{label}: _dynamic_walker_evidence",
    )
    if dynamic_evidence.get("held") is True:
        raise ProfileError(f"step_output_drain_case rejected {label}: QA reroute proof held")


def _source_lane_transition_concern_fixture() -> Mapping[str, Any]:
    concerns: dict[str, Any] = {}
    for brick_ref in (
        "brick-source-concern-code-attack-qa",
        "brick-source-concern-axis-attack-qa",
        "brick-source-concern-evidence-integrity",
    ):
        concerns[brick_ref] = {
            "concern_ref": f"transition-concern:{brick_ref}",
            "concern_kind": "implementation_gap",
            "binding": False,
            "reason_refs": [f"observation:{brick_ref}:source-lane"],
            "related_boundary_refs": ["brick-source-concern-work"],
        }
    concerns["brick-source-concern-inspect"] = {
        "concern_ref": "transition-concern:brick-source-concern-inspect",
        "concern_kind": "implementation_gap",
        "binding": False,
        "reason_refs": [],
        "related_boundary_refs": ["brick-source-concern-work"],
    }
    return concerns


def _check_source_lane_transition_concerns_expected(
    result: Any,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    dynamic_evidence = require_mapping(
        getattr(result, "_dynamic_walker_evidence", {}),
        f"{label}: _dynamic_walker_evidence",
    )
    if dynamic_evidence.get("held") is True:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source-lane concern proof held"
        )
    records = getattr(result, "_dynamic_walker_reroute_records", ())
    adopted = [
        record
        for record in records
        if isinstance(record, Mapping) and not record.get("disposition_required")
    ]
    if adopted:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source-lane concern adopted reroute"
        )
    observations = dynamic_evidence.get("source_lane_transition_concern_observations")
    if not isinstance(observations, list):
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source-lane observations missing"
        )
    expected_bricks = require_string_list(
        expected.get("observed_source_brick_refs", []),
        f"{label}: expected.observed_source_brick_refs",
    )
    by_brick = {
        str(item.get("source_brick_ref")): item
        for item in observations
        if isinstance(item, Mapping)
    }
    if sorted(by_brick) != sorted(expected_bricks):
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source-lane observation refs mismatch "
            f"(got={sorted(by_brick)}, expected={sorted(expected_bricks)})"
        )
    malformed = require_string_list(
        expected.get("malformed_source_brick_refs", []),
        f"{label}: expected.malformed_source_brick_refs",
    )
    for brick_ref in expected_bricks:
        observation = require_mapping(
            by_brick.get(brick_ref),
            f"{label}: source observation {brick_ref}",
        )
        if observation.get("transition_concern_adoption") != "advisory":
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {brick_ref} did not record advisory policy"
            )
        if observation.get("adopted_as_movement") is not False:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {brick_ref} was recorded as Movement"
            )
        if brick_ref in malformed:
            if observation.get("concern_state") != "malformed":
                raise ProfileError(
                    f"step_output_drain_case rejected {label}: {brick_ref} was not malformed evidence"
                )
            if not observation.get("invalid_reason"):
                raise ProfileError(
                    f"step_output_drain_case rejected {label}: malformed source lacked invalid_reason"
                )
            continue
        if observation.get("concern_state") != "valid":
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {brick_ref} was not valid evidence"
            )
        if not observation.get("reason_refs") or not observation.get("related_boundary_refs"):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {brick_ref} lacked reason/related refs"
            )


def _check_replay_closure_carry(
    events: Sequence[Mapping[str, Any]],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> int:
    consumer_brick = require_string(
        expected.get("consumer_brick_instance_ref"),
        f"{label}: expected.consumer_brick_instance_ref",
    )
    expected_refs = require_string_list(
        expected.get("source_fact_body_refs", []),
        f"{label}: expected.source_fact_body_refs",
    )
    expected_markers = require_string_list(
        expected.get("carried_markers", []),
        f"{label}: expected.carried_markers",
    )
    matching = [
        (index, event)
        for index, event in enumerate(events)
        if event.get("brick_instance_ref") == consumer_brick
        and event.get("source_fact_body_refs") == expected_refs
    ]
    if not matching:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: replay closure did not receive full QA carry"
        )
    index, event = matching[0]
    if event.get("carried_markers") != expected_markers:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: replay closure carried markers mismatch"
        )
    return index


def _step_output_drain_plan(case_kind: str, *, missing: bool) -> tuple[Mapping[str, Any], str]:
    if case_kind == "live_linear_n1":
        return _linear_step_output_drain_plan(missing=missing), "dynamic"
    if case_kind in {"live_dynamic_fan_in_n2", "live_dynamic_fan_in_n3"}:
        return _dynamic_step_output_drain_plan(missing=missing), "dynamic"
    if case_kind == "live_dynamic_full_replay_n3":
        return _dynamic_full_replay_drain_plan(partial=False), "dynamic"
    if case_kind == "live_qa_reroute_to_work_n2":
        return _qa_reroute_to_work_drain_plan(), "dynamic"
    if case_kind == "live_dynamic_fan_in_source_concerns_n4":
        return _dynamic_source_lane_transition_concern_plan(), "dynamic"
    if case_kind == "live_dynamic_partial_replay_rejected":
        return _dynamic_full_replay_drain_plan(partial=True), "dynamic"
    if case_kind == "live_linear_missing_step_output_body":
        return _linear_step_output_drain_plan(missing=True), "dynamic"
    if case_kind == "live_dynamic_missing_step_output_body":
        return _dynamic_step_output_drain_plan(missing=True), "dynamic"
    raise ProfileError(f"unknown step_output_drain case_kind: {case_kind}")


def _linear_step_output_drain_plan(*, missing: bool) -> Mapping[str, Any]:
    source_ref = (
        "work/step-outputs/missing-producer-attempt-1/step-output.json"
        if missing
        else "work/step-outputs/linear-producer-attempt-1/step-output.json"
    )
    linear_plan = {
        "plan_ref": "building-plan:checker-live-linear-step-output-drain",
        "building_id": "checker-live-linear-step-output-drain",
        "plan_shape": "linear",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "steps": [
            _linear_step(
                "linear-producer",
                "brick-linear-producer",
                "brick-linear-consumer",
            ),
            _linear_step(
                "linear-consumer",
                "brick-linear-consumer",
                "building-boundary:checker-live-linear-step-output-drain-closed",
                source_facts=[source_ref],
                closed=True,
            ),
        ],
    }
    return _graph_test_plan_from_linear(linear_plan)


def _linear_step(
    step_ref: str,
    brick_ref: str,
    target_ref: str,
    *,
    source_facts: Sequence[str] | None = None,
    closed: bool = False,
) -> Mapping[str, Any]:
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": f"link-row:{step_ref}",
        "movement": "forward",
        "target_ref": target_ref,
        "next_brick_instance_ref": target_ref,
        "declared_gate_refs": ["link-gate:default-transition"],
    }
    if closed:
        link_row["building_lifecycle"] = {
            "state": "closed",
            "reason": "checker live step-output drain close",
        }
    return {
        "step_ref": step_ref,
        "step_template_ref": "",
        "selected_adapter_ref": "adapter:local",
        "rows": [
            _brick_row(step_ref, brick_ref, source_facts=source_facts),
            _agent_row(step_ref),
            link_row,
        ],
    }


def _dynamic_step_output_drain_plan(*, missing: bool) -> Mapping[str, Any]:
    closure_source_facts = (
        ["work/step-outputs/missing-qa-attempt-1/step-output.json"] if missing else []
    )
    return {
        "plan_ref": "building-plan:checker-live-dynamic-step-output-drain",
        "building_id": "checker-live-dynamic-step-output-drain",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "execution_order": [
            "fan-work",
            "fan-code-qa",
            "fan-axis-qa",
            "fan-evidence-qa",
            "fan-closure",
        ],
        "brick_steps": [
            _graph_brick_step("fan-work", "brick-fan-work", "edge:work-to-code"),
            _graph_brick_step("fan-code-qa", "brick-fan-code-qa", "edge:code-to-closure"),
            _graph_brick_step("fan-axis-qa", "brick-fan-axis-qa", "edge:axis-to-closure"),
            _graph_brick_step(
                "fan-evidence-qa",
                "brick-fan-evidence-qa",
                "edge:evidence-to-closure",
            ),
            _graph_brick_step(
                "fan-closure",
                "brick-fan-closure",
                "edge:closure-to-boundary",
                source_facts=closure_source_facts,
            ),
        ],
        "link_edges": [
            _graph_link_edge("edge:work-to-code", "fan-work", "fan-code-qa", "brick-fan-code-qa"),
            _graph_link_edge("edge:work-to-axis", "fan-work", "fan-axis-qa", "brick-fan-axis-qa"),
            _graph_link_edge(
                "edge:work-to-evidence",
                "fan-work",
                "fan-evidence-qa",
                "brick-fan-evidence-qa",
            ),
            _graph_link_edge("edge:code-to-closure", "fan-code-qa", "fan-closure", "brick-fan-closure"),
            _graph_link_edge("edge:axis-to-closure", "fan-axis-qa", "fan-closure", "brick-fan-closure"),
            _graph_link_edge(
                "edge:evidence-to-closure",
                "fan-evidence-qa",
                "fan-closure",
                "brick-fan-closure",
            ),
            _graph_link_edge(
                "edge:closure-to-boundary",
                "fan-closure",
                "",
                "building-boundary:checker-live-dynamic-step-output-drain-closed",
            ),
        ],
        "groups": [
            {
                "group_id": "group:checker-step-output-drain-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:work-to-code",
                    "edge:work-to-axis",
                    "edge:work-to-evidence",
                ],
            },
            {
                "group_id": "group:checker-step-output-drain-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:code-to-closure",
                    "edge:axis-to-closure",
                    "edge:evidence-to-closure",
                ],
            },
        ],
    }


def _qa_reroute_to_work_drain_plan() -> Mapping[str, Any]:
    """Small graph proving a QA-emitted concern is not decorative.

    work -> code-attack-qa -> closure. The observed callable emits one
    implementation_gap transition_concern_evidence from the QA brick targeting
    the upstream work brick. The dynamic walker should adopt the valid concern
    under default-transition, consume the work node's reroute budget, and record
    a second work attempt before closure. This is support evidence only: it does
    not make QA a Movement authority and does not judge success/quality.
    """

    return {
        "plan_ref": "building-plan:checker-live-qa-reroute-to-work",
        "building_id": "checker-live-qa-reroute-to-work",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "execution_order": [
            "qa-reroute-work",
            "qa-reroute-code-attack-qa",
            "qa-reroute-closure",
        ],
        "brick_steps": [
            _graph_brick_step(
                "qa-reroute-work",
                "brick-qa-reroute-work",
                "edge:qa-reroute-work-to-code-attack-qa",
            ),
            _graph_brick_step(
                "qa-reroute-code-attack-qa",
                "brick-qa-reroute-code-attack-qa",
                "edge:qa-reroute-code-attack-qa-to-closure",
            ),
            _graph_brick_step(
                "qa-reroute-closure",
                "brick-qa-reroute-closure",
                "edge:qa-reroute-closure-to-boundary",
            ),
        ],
        "link_edges": [
            _graph_link_edge(
                "edge:qa-reroute-work-to-code-attack-qa",
                "qa-reroute-work",
                "qa-reroute-code-attack-qa",
                "brick-qa-reroute-code-attack-qa",
            ),
            _graph_link_edge(
                "edge:qa-reroute-code-attack-qa-to-closure",
                "qa-reroute-code-attack-qa",
                "qa-reroute-closure",
                "brick-qa-reroute-closure",
            ),
            _graph_link_edge(
                "edge:qa-reroute-closure-to-boundary",
                "qa-reroute-closure",
                "",
                "building-boundary:checker-live-qa-reroute-to-work-closed",
            ),
        ],
        "node_reroute_budgets": {"brick-qa-reroute-work": 1},
    }


def _dynamic_source_lane_transition_concern_plan() -> Mapping[str, Any]:
    return {
        "plan_ref": "building-plan:checker-live-fan-in-source-concerns",
        "building_id": "checker-live-fan-in-source-concerns",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "execution_order": [
            "source-concern-work",
            "source-concern-code-attack-qa",
            "source-concern-axis-attack-qa",
            "source-concern-evidence-integrity",
            "source-concern-inspect",
            "source-concern-closure",
        ],
        "brick_steps": [
            _graph_brick_step(
                "source-concern-work",
                "brick-source-concern-work",
                "edge:source-concern-work-to-code",
            ),
            _graph_brick_step(
                "source-concern-code-attack-qa",
                "brick-source-concern-code-attack-qa",
                "edge:source-concern-code-to-closure",
                step_template_ref="building-step-template:code-attack-qa",
            ),
            _graph_brick_step(
                "source-concern-axis-attack-qa",
                "brick-source-concern-axis-attack-qa",
                "edge:source-concern-axis-to-closure",
                step_template_ref="building-step-template:axis-attack-qa",
            ),
            _graph_brick_step(
                "source-concern-evidence-integrity",
                "brick-source-concern-evidence-integrity",
                "edge:source-concern-evidence-to-closure",
                step_template_ref="building-step-template:evidence-integrity",
            ),
            _graph_brick_step(
                "source-concern-inspect",
                "brick-source-concern-inspect",
                "edge:source-concern-inspect-to-closure",
                step_template_ref="building-step-template:inspect",
            ),
            _graph_brick_step(
                "source-concern-closure",
                "brick-source-concern-closure",
                "edge:source-concern-closure-to-boundary",
            ),
        ],
        "link_edges": [
            _graph_link_edge(
                "edge:source-concern-work-to-code",
                "source-concern-work",
                "source-concern-code-attack-qa",
                "brick-source-concern-code-attack-qa",
            ),
            _graph_link_edge(
                "edge:source-concern-work-to-axis",
                "source-concern-work",
                "source-concern-axis-attack-qa",
                "brick-source-concern-axis-attack-qa",
            ),
            _graph_link_edge(
                "edge:source-concern-work-to-evidence",
                "source-concern-work",
                "source-concern-evidence-integrity",
                "brick-source-concern-evidence-integrity",
            ),
            _graph_link_edge(
                "edge:source-concern-work-to-inspect",
                "source-concern-work",
                "source-concern-inspect",
                "brick-source-concern-inspect",
            ),
            _graph_link_edge(
                "edge:source-concern-code-to-closure",
                "source-concern-code-attack-qa",
                "source-concern-closure",
                "brick-source-concern-closure",
            ),
            _graph_link_edge(
                "edge:source-concern-axis-to-closure",
                "source-concern-axis-attack-qa",
                "source-concern-closure",
                "brick-source-concern-closure",
            ),
            _graph_link_edge(
                "edge:source-concern-evidence-to-closure",
                "source-concern-evidence-integrity",
                "source-concern-closure",
                "brick-source-concern-closure",
            ),
            _graph_link_edge(
                "edge:source-concern-inspect-to-closure",
                "source-concern-inspect",
                "source-concern-closure",
                "brick-source-concern-closure",
            ),
            _graph_link_edge(
                "edge:source-concern-closure-to-boundary",
                "source-concern-closure",
                "",
                "building-boundary:checker-live-fan-in-source-concerns-closed",
            ),
        ],
        "groups": [
            {
                "group_id": "group:checker-source-concern-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:source-concern-work-to-code",
                    "edge:source-concern-work-to-axis",
                    "edge:source-concern-work-to-evidence",
                    "edge:source-concern-work-to-inspect",
                ],
            },
            {
                "group_id": "group:checker-source-concern-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:source-concern-code-to-closure",
                    "edge:source-concern-axis-to-closure",
                    "edge:source-concern-evidence-to-closure",
                    "edge:source-concern-inspect-to-closure",
                ],
            },
        ],
    }


def _dynamic_full_replay_drain_plan(*, partial: bool) -> Mapping[str, Any]:
    route_plan = {
        "route_replay_ref": "route-replay:checker-p6-full-replay",
        "author_ref": "coo:checker-p6-full-replay",
        "authoring_basis_refs": ["observation:checker-p6-closure-implementation-gap"],
        "immediate_target_ref": "brick-replay-work-b",
        "source_brick_refs": ["brick-replay-closure-a"],
        "route_reason_refs": ["transition-concern:brick-replay-closure-a"],
        "affected_downstream_refs": [
            "brick-replay-after-b",
        ],
        "replay_segment_refs": (
            ["brick-replay-code-qa-b", "brick-replay-closure-b"]
            if partial
            else []
        ),
        "max_attempts": 1,
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["semantic correctness of closure concern"],
    }
    return {
        "plan_ref": "building-plan:checker-p6-dynamic-full-replay",
        "building_id": "checker-p6-dynamic-full-replay",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "execution_order": [
            "replay-work-a",
            "replay-code-qa-a",
            "replay-axis-qa-a",
            "replay-evidence-qa-a",
            "replay-closure-a",
            "replay-work-b",
            "replay-code-qa-b",
            "replay-axis-qa-b",
            "replay-evidence-qa-b",
            "replay-closure-b",
            "replay-after-b",
        ],
        "brick_steps": [
            _graph_brick_step("replay-work-a", "brick-replay-work-a", "edge:replay-work-a-to-code-a"),
            _graph_brick_step("replay-code-qa-a", "brick-replay-code-qa-a", "edge:replay-code-a-to-axis-a"),
            _graph_brick_step("replay-axis-qa-a", "brick-replay-axis-qa-a", "edge:replay-axis-a-to-evidence-a"),
            _graph_brick_step("replay-evidence-qa-a", "brick-replay-evidence-qa-a", "edge:replay-evidence-a-to-closure-a"),
            _graph_brick_step("replay-closure-a", "brick-replay-closure-a", "edge:replay-closure-a-to-work-b"),
            _graph_brick_step("replay-work-b", "brick-replay-work-b", "edge:replay-work-b-to-code-b"),
            _graph_brick_step("replay-code-qa-b", "brick-replay-code-qa-b", "edge:replay-code-b-to-axis-b"),
            _graph_brick_step("replay-axis-qa-b", "brick-replay-axis-qa-b", "edge:replay-axis-b-to-evidence-b"),
            _graph_brick_step("replay-evidence-qa-b", "brick-replay-evidence-qa-b", "edge:replay-evidence-b-to-closure-b"),
            _graph_brick_step("replay-closure-b", "brick-replay-closure-b", "edge:replay-closure-b-to-after-b"),
            _graph_brick_step("replay-after-b", "brick-replay-after-b", "edge:replay-after-b-to-boundary"),
        ],
        "link_edges": [
            _graph_link_edge("edge:replay-work-a-to-code-a", "replay-work-a", "replay-code-qa-a", "brick-replay-code-qa-a"),
            _graph_link_edge("edge:replay-work-a-to-axis-a", "replay-work-a", "replay-axis-qa-a", "brick-replay-axis-qa-a"),
            _graph_link_edge("edge:replay-work-a-to-evidence-a", "replay-work-a", "replay-evidence-qa-a", "brick-replay-evidence-qa-a"),
            _graph_link_edge("edge:replay-code-a-to-axis-a", "replay-code-qa-a", "replay-axis-qa-a", "brick-replay-axis-qa-a"),
            _graph_link_edge("edge:replay-code-a-to-closure-a", "replay-code-qa-a", "replay-closure-a", "brick-replay-closure-a"),
            _graph_link_edge("edge:replay-axis-a-to-evidence-a", "replay-axis-qa-a", "replay-evidence-qa-a", "brick-replay-evidence-qa-a"),
            _graph_link_edge("edge:replay-axis-a-to-closure-a", "replay-axis-qa-a", "replay-closure-a", "brick-replay-closure-a"),
            _graph_link_edge("edge:replay-evidence-a-to-closure-a", "replay-evidence-qa-a", "replay-closure-a", "brick-replay-closure-a"),
            _graph_link_edge(
                "edge:replay-closure-a-to-work-b",
                "replay-closure-a",
                "replay-work-b",
                "brick-replay-work-b",
                movement="reroute",
                route_replay_plan=route_plan,
                declared_gate_refs=["link-gate:default-transition"],
            ),
            _graph_link_edge("edge:replay-work-b-to-code-b", "replay-work-b", "replay-code-qa-b", "brick-replay-code-qa-b"),
            _graph_link_edge("edge:replay-work-b-to-axis-b", "replay-work-b", "replay-axis-qa-b", "brick-replay-axis-qa-b"),
            _graph_link_edge("edge:replay-work-b-to-evidence-b", "replay-work-b", "replay-evidence-qa-b", "brick-replay-evidence-qa-b"),
            _graph_link_edge("edge:replay-code-b-to-axis-b", "replay-code-qa-b", "replay-axis-qa-b", "brick-replay-axis-qa-b"),
            _graph_link_edge("edge:replay-code-b-to-closure-b", "replay-code-qa-b", "replay-closure-b", "brick-replay-closure-b"),
            _graph_link_edge("edge:replay-axis-b-to-evidence-b", "replay-axis-qa-b", "replay-evidence-qa-b", "brick-replay-evidence-qa-b"),
            _graph_link_edge("edge:replay-axis-b-to-closure-b", "replay-axis-qa-b", "replay-closure-b", "brick-replay-closure-b"),
            _graph_link_edge("edge:replay-evidence-b-to-closure-b", "replay-evidence-qa-b", "replay-closure-b", "brick-replay-closure-b"),
            _graph_link_edge("edge:replay-closure-b-to-after-b", "replay-closure-b", "replay-after-b", "brick-replay-after-b"),
            _graph_link_edge(
                "edge:replay-after-b-to-boundary",
                "replay-after-b",
                "",
                "building-boundary:checker-p6-dynamic-full-replay-closed",
            ),
        ],
        "groups": [
            {
                "group_id": "group:p6-replay-fan-out-a",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:replay-work-a-to-code-a",
                    "edge:replay-work-a-to-axis-a",
                    "edge:replay-work-a-to-evidence-a",
                ],
            },
            {
                "group_id": "group:p6-replay-fan-in-a",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:replay-code-a-to-closure-a",
                    "edge:replay-axis-a-to-closure-a",
                    "edge:replay-evidence-a-to-closure-a",
                ],
            },
            {
                "group_id": "group:p6-replay-fan-out-b",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:replay-work-b-to-code-b",
                    "edge:replay-work-b-to-axis-b",
                    "edge:replay-work-b-to-evidence-b",
                ],
            },
            {
                "group_id": "group:p6-replay-fan-in-b",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:replay-code-b-to-closure-b",
                    "edge:replay-axis-b-to-closure-b",
                    "edge:replay-evidence-b-to-closure-b",
                ],
            },
        ],
        "node_reroute_budgets": {"brick-replay-work-b": 1},
    }


def _graph_brick_step(
    step_ref: str,
    brick_ref: str,
    completion_edge_ref: str,
    *,
    source_facts: Sequence[str] | None = None,
    step_template_ref: str = "",
) -> Mapping[str, Any]:
    return fixture_graph_brick_step(
        step_ref,
        brick_ref,
        completion_edge_ref,
        agent_object_ref="agent-object:coo",
        work_statement=f"Run checker live step-output drain step {step_ref}.",
        required_return_shape="body_marker, source_fact_body_refs, carried_markers, not_proven",
        source_facts=source_facts,
        selected_adapter_ref="adapter:local",
        step_template_ref=step_template_ref,
    )


def _graph_link_edge(
    edge_ref: str,
    source_step_ref: str,
    target_step_ref: str,
    target_ref: str,
    *,
    movement: str = "forward",
    route_replay_plan: Mapping[str, Any] | None = None,
    declared_gate_refs: Sequence[str] | None = None,
) -> Mapping[str, Any]:
    return fixture_graph_link_edge(
        edge_ref,
        source_step_ref,
        target_ref,
        target_step_ref=target_step_ref,
        movement=movement,
        route_replay_plan=route_replay_plan,
        declared_gate_refs=declared_gate_refs,
        close_reason="checker live step-output drain close",
    )


def _axis_row(step: Mapping[str, Any], axis: str) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == axis:
            return row
    return {}


def _brick_ref_by_step(plan: Mapping[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    for step in plan.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        step_ref = str(step.get("step_ref", "")).strip()
        brick_row = _axis_row(step, "Brick")
        brick_ref = str(brick_row.get("brick_instance_ref", "")).strip()
        if step_ref and brick_ref:
            refs[step_ref] = brick_ref
    return refs


def _brick_row(
    step_ref: str,
    brick_ref: str,
    *,
    source_facts: Sequence[str] | None,
) -> Mapping[str, Any]:
    return fixture_brick_row(
        step_ref,
        brick_ref,
        work_statement=f"Run checker live step-output drain step {step_ref}.",
        required_return_shape="body_marker, source_fact_body_refs, carried_markers, not_proven",
        source_facts=source_facts,
    )


def _agent_row(step_ref: str) -> Mapping[str, Any]:
    return fixture_agent_row(step_ref, agent_object_ref="agent-object:coo")


def _step_output_drain_proof_limits() -> list[str]:
    return fixture_proof_limits()


def _checker_step_output_relative_ref(ref: str) -> str:
    marker = "work/step-outputs/"
    normalized = str(ref).replace("\\", "/")
    if marker not in normalized:
        return normalized
    return normalized[normalized.index(marker) :]

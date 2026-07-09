"""Brick-grain report event helpers for the dynamic graph walker."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.gate_sequence import GateSequenceDecision
from brick_protocol.support.operator.progress_projection import (
    refresh_project_progress_for_building_event,
)
from brick_protocol.support.operator.reporter import emit_building_event_for_policy
from brick_protocol.support.operator.walker_resume_seed import ResumeSeed
from brick_protocol.support.operator.walker_step_fixture import (
    _brick_instance_ref_from_linear_step,
)
from brick_protocol.support.recording.capture import graph_ready_timestamp
from brick_protocol.support.recording.step_outputs import _step_output_manifest_ref

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
    step_ref = step_result.preparation.step_rows.step_ref
    last_completed_step_ref = _step_output_manifest_ref(step_ref, attempt_index)
    _refresh_project_progress_for_completed_step_best_effort(
        building_root=building_root,
        repo_root=repo_root,
        last_completed_step_ref=last_completed_step_ref,
    )
    if not _report_policy_uses_brick_grain(policy):
        return ()
    context = _brick_grain_step_context(
        step_result,
        linear_plan=linear_plan,
        step_index=step_index,
        gate_sequence_decision=gate_sequence_decision,
    )
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


def _refresh_project_progress_for_completed_step_best_effort(
    *,
    building_root: Path | str,
    repo_root: Path,
    last_completed_step_ref: str,
) -> Mapping[str, Any]:
    try:
        return refresh_project_progress_for_building_event(
            building_root=building_root,
            event_kind="walker_step_completed",
            repo_root=repo_root,
            last_completed_step_ref=last_completed_step_ref,
        )
    except Exception as exc:  # noqa: BLE001 - progress projection must not break the walker.
        return {
            "kind": "project-progress-refresh-observation",
            "schema_version": "project-progress-refresh-0",
            "event_kind": "walker_step_completed",
            "progress_refresh_observation": "refresh_exception_observed",
            "changed": False,
            "delivery_status_class": "exception_observed",
            "provider_response_status_class": exc.__class__.__name__,
            "reason": str(exc),
            "source_truth": False,
            "proof_limits": [
                "support projection refresh observation only",
                "progress refresh exception was not allowed to break walker step events",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                "project progress projection refreshed for this event",
                "semantic correctness of the projected Building work",
            ],
        }


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


def progress_autorefresh_probe_observations() -> tuple[Mapping[str, Any], ...]:
    """Exercise the walker-step-completed -> PROGRESS refresh wiring.

    This is a support fixture: it writes no files and uses a monkeypatched
    refresh callable to prove the completion seam invokes the progress hook even
    when brick-grain notification reporting is disabled.
    """

    observations: list[Mapping[str, Any]] = []
    original_refresh = refresh_project_progress_for_building_event
    calls: list[Mapping[str, Any]] = []

    def observed_refresh(**kwargs: Any) -> Mapping[str, Any]:
        calls.append(dict(kwargs))
        return {
            "kind": "project-progress-refresh-observation",
            "progress_refresh_observation": "probe_refresh_called",
            "source_truth": False,
        }

    step_result = SimpleNamespace(
        preparation=SimpleNamespace(
            step_rows=SimpleNamespace(step_ref="probe-step"),
            brick_instance_ref="brick-probe",
            next_brick_instance_ref="building-boundary:complete",
        ),
        recorded_at="",
    )
    gate_sequence_decision = SimpleNamespace(action="forward")
    try:
        globals()["refresh_project_progress_for_building_event"] = observed_refresh
        report_observations = _emit_brick_grain_completion_step_events(
            None,
            linear_plan={"steps": [{"step_ref": "probe-step"}]},
            building_id="probe-building",
            building_root=Path("project/probe-vessel/buildings/probe-building"),
            repo_root=Path("."),
            step_result=step_result,
            step_index=1,
            attempt_index=3,
            gate_sequence_decision=gate_sequence_decision,
            report_env=None,
            report_slack_sender=None,
            overwrite_existing=True,
        )
        called = len(calls) == 1
        no_report_drift = report_observations == ()
        last_ref = str(calls[0].get("last_completed_step_ref") or "") if calls else ""
        manifest_ref_ok = (
            last_ref
            == "work/step-outputs/probe-step-attempt-3/step-output.json"
        )
        observations.append(
            {
                "probe_ref": "progress-autorefresh:completion-call",
                "passed": called and no_report_drift and manifest_ref_ok,
                "call_count": len(calls),
                "report_observation_count": len(report_observations),
                "last_completed_step_ref": last_ref,
                "proof_limits": ["support fixture only"],
            }
        )

        class _RefreshSentinel(RuntimeError):
            pass

        def raising_refresh(**kwargs: Any) -> Mapping[str, Any]:
            del kwargs
            raise _RefreshSentinel("progress refresh hook reached")

        globals()["refresh_project_progress_for_building_event"] = raising_refresh
        sentinel_contained = False
        try:
            report_observations = _emit_brick_grain_completion_step_events(
                None,
                linear_plan={"steps": [{"step_ref": "probe-step"}]},
                building_id="probe-building",
                building_root=Path("project/probe-vessel/buildings/probe-building"),
                repo_root=Path("."),
                step_result=step_result,
                step_index=1,
                attempt_index=1,
                gate_sequence_decision=gate_sequence_decision,
                report_env=None,
                report_slack_sender=None,
                overwrite_existing=True,
            )
        except _RefreshSentinel:
            sentinel_contained = False
        else:
            sentinel_contained = report_observations == ()
        observations.append(
            {
                "probe_ref": "progress-autorefresh:exception-containment",
                "passed": sentinel_contained,
                "proof_limits": [
                    "support fixture only",
                    "if the completion-to-refresh call is unguarded, this probe goes RED",
                ],
            }
        )
    finally:
        globals()["refresh_project_progress_for_building_event"] = original_refresh

    failed = [item for item in observations if not item.get("passed")]
    if failed:
        raise AssertionError(f"progress autorefresh probe rejected: {failed!r}")
    return tuple(observations)

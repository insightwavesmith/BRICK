"""Support-only report packet renderer and local inbox coordinator."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brick_protocol.link.transition import TRANSITION_LIFECYCLE_DISPOSITION_OWNERS
from brick_protocol.support.operator.building_operation import observe_building_frontier
from brick_protocol.support.recording.capture import (
    REPO_ROOT as _CAPTURE_REPO_ROOT,
    buildings_root_for,
    is_project_id_slug,
    project_ref_for_building_root,
)
from brick_protocol.support.operator.report_sinks import (
    ADMITTED_SINK_REFS,
    LOCAL_INBOX_SINK_REF,
    OPERATOR_WAKE_LOCAL_SINK_REF,
    SLACK_SINK_REF,
    deliver_report_packet,
    dry_run_report_packet as dry_run_sink_report_packet,
    validate_operator_wake_targets,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_KIND_VALUES = frozenset(
    {
        "building_frontier",
        "portfolio_frontier",
        "checker_observation",
        "delivery_observation",
    }
)
OBSERVED_BOARD_STATES = frozenset(
    {
        "observed_started",
        "observed_running",
        "observed_closed_boundary",
        "observed_paused",
        "observed_human_gate",
        "needs_disposition",
        "observed_checker_failed",
        "observed_reporter_delivery_failed",
    }
)
FORBIDDEN_REPORT_PACKET_FIELDS = frozenset(
    {
        "access_token",
        "success",
        "failure",
        "approved",
        "auth",
        "auth_body",
        "authorization",
        "bearer_token",
        "bot_token",
        "channel",
        "channel_id",
        "credential",
        "credential_body",
        "quality",
        "complete",
        "complete_as_movement",
        "movement_choice",
        "target_choice",
        "route_target",
        "adopted_by_reporter",
        "resume_route",
        "driver_input",
        "headers",
        "message_text",
        "queue",
        "retry",
        "raw_secret",
        "refresh_token",
        "response_body",
        "scheduler",
        "secret",
        "setup_token",
        "setup_token_body",
        "slack_bot_token",
        "slack_channel_id",
        "slack_response",
        "token",
    }
)
REQUIRED_REPORT_PACKET_FIELDS = (
    "report_id",
    "report_kind",
    "building_id",
    "portfolio_id",
    "observed_board_state",
    "trigger_event_ref",
    "current_brick_ref",
    "last_completed_step_ref",
    "frontier_ref",
    "evidence_root_refs",
    "evidence_refs_present",
    "checker_summary_ref",
    "required_disposition_owner",
    "sink_refs",
    "generated_at",
    "source_truth",
    "not_proven",
    "proof_limits",
)
REPORTER_PROOF_LIMITS: tuple[str, ...] = (
    "support projection only",
    "reads existing Building or portfolio evidence only",
    "report packet is not AgentFact",
    "report packet is not Link transfer / carry / Movement",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route target choice",
    "not driver input",
    "operator wake target is provider-neutral local projection only",
)
REPORTER_NOT_PROVEN: tuple[str, ...] = (
    "delivery reliability",
    "stale evidence snapshot behavior",
    "semantic correctness of observed frontier",
    "whether caller or COO should act on disposition evidence",
    "external notification behavior",
    "real provider thread wake behavior",
    "production readiness",
)
_FRONTIER_TO_OBSERVED_STATE = {
    "complete": "observed_closed_boundary",
    "link_paused": "observed_paused",
    "human_review_waiting": "observed_human_gate",
    "chat_session_parked": "needs_disposition",
    "agent_incomplete": "observed_running",
    "closure_pending": "observed_running",
    "evidence_incomplete": "observed_running",
}
BUILDING_EVENT_KINDS = frozenset(
    {"building_started", "intervention_required", "building_finished"}
)
BUILDING_EVENT_OBSERVED_STATES = {
    "building_started": "observed_started",
    "intervention_required": "observed_paused",
    "building_finished": "observed_closed_boundary",
}
BUILDING_EVENT_FRONTIER_KINDS = {
    "complete": "building_finished",
    "link_paused": "intervention_required",
    "human_review_waiting": "intervention_required",
    "chat_session_parked": "intervention_required",
}
BUILDING_EVENT_PROOF_LIMITS: tuple[str, ...] = (
    "opt-in Building event notification support hook only",
    "not global default delivery",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route target choice",
    "not scheduler / queue / retry runtime",
)
BUILDING_EVENT_NOT_PROVEN: tuple[str, ...] = (
    "event delivery reliability",
    "reader noticed event notification",
    "parallel runtime timing",
    "production readiness",
)


def report_event_policy_from_plan(plan: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return a validated opt-in event policy, or None when undeclared/disabled."""

    raw_policy = plan.get("report_event_policy")
    if raw_policy is None:
        return None
    if not isinstance(raw_policy, Mapping):
        raise ValueError("report_event_policy must be a mapping when supplied")
    forbidden = sorted(set(_nested_keys(raw_policy)) & FORBIDDEN_REPORT_PACKET_FIELDS)
    if forbidden:
        raise ValueError(f"report_event_policy includes forbidden field(s): {forbidden}")
    enabled = raw_policy.get("enabled")
    if enabled is False or enabled is None:
        return None
    if enabled is not True:
        raise ValueError("report_event_policy.enabled must be true or false")

    event_kinds = _policy_text_tuple(
        raw_policy.get("event_kinds"),
        "report_event_policy.event_kinds",
        default=tuple(sorted(BUILDING_EVENT_KINDS)),
    )
    unadmitted_events = sorted(set(event_kinds) - BUILDING_EVENT_KINDS)
    if unadmitted_events:
        raise ValueError(f"unadmitted Building event kind(s): {unadmitted_events}")

    sink_refs = _policy_text_tuple(
        raw_policy.get("sink_refs"),
        "report_event_policy.sink_refs",
        default=(LOCAL_INBOX_SINK_REF,),
    )
    unadmitted_sinks = sorted(set(sink_refs) - ADMITTED_SINK_REFS)
    if unadmitted_sinks:
        raise ValueError(f"unadmitted report event sink ref(s): {unadmitted_sinks}")

    allow_real_slack_delivery = raw_policy.get("allow_real_slack_delivery", False)
    if not isinstance(allow_real_slack_delivery, bool):
        raise ValueError("report_event_policy.allow_real_slack_delivery must be a boolean")

    return {
        "enabled": True,
        "event_kinds": list(event_kinds),
        "sink_refs": list(sink_refs),
        "allow_real_slack_delivery": allow_real_slack_delivery,
        "proof_limits": list(
            _merge_texts(
                BUILDING_EVENT_PROOF_LIMITS,
                _policy_text_tuple(
                    raw_policy.get("proof_limits"),
                    "report_event_policy.proof_limits",
                    default=(),
                ),
            )
        ),
        "not_proven": list(
            _merge_texts(
                BUILDING_EVENT_NOT_PROVEN,
                _policy_text_tuple(
                    raw_policy.get("not_proven"),
                    "report_event_policy.not_proven",
                    default=(),
                ),
            )
        ),
    }


def building_event_kind_from_frontier(
    building_root: str | Path,
    *,
    repo_root: Path | str = REPO_ROOT,
) -> str:
    """Project a persisted frontier into the admitted terminal event kind."""

    repo = Path(repo_root).resolve()
    root = _building_event_root(repo, building_root)
    frontier = observe_building_frontier(root, repo_root=repo)
    frontier_kind = str(frontier.get("frontier_kind") or "")
    return BUILDING_EVENT_FRONTIER_KINDS.get(frontier_kind, "")


def render_building_event_report_packet(
    *,
    event_kind: str,
    building_id: str,
    building_root: str | Path,
    current_brick_ref: str = "",
    last_completed_step_ref: str = "",
    trigger_event_ref: str = "",
    checker_summary_ref: str = "",
    required_disposition_owner: str = "",
    sink_refs: Iterable[str] | None = None,
    repo_root: Path | str = REPO_ROOT,
    generated_at: str | None = None,
    proof_limits: Iterable[str] | str | None = None,
    not_proven: Iterable[str] | str | None = None,
) -> Mapping[str, Any]:
    """Render one support-only Building event notification packet."""

    if event_kind not in BUILDING_EVENT_KINDS:
        raise ValueError(f"unadmitted Building event kind: {event_kind}")
    repo = Path(repo_root).resolve()
    root = _building_event_root(repo, building_root)
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    refs = tuple(sink_refs or (LOCAL_INBOX_SINK_REF,))
    building_map = _read_json_mapping(root / "work" / "building-map.json")
    frontier: Mapping[str, Any] = {}
    if root.exists():
        frontier = observe_building_frontier(root, repo_root=repo)
    frontier_kind = str(frontier.get("frontier_kind") or "")
    missing_files = tuple(str(item) for item in frontier.get("missing_required_files", ()))
    source_id = _required_text(building_id or _building_id(root, building_map), "building_id")
    # DECISIONS-WIRE AUTO-ON (Smith 0611): Building event packets derive the
    # vessel from the building root PATH too — same inverse seam, same
    # legacy-unchanged behavior for non-vessel roots.
    project_ref, vessel_segment = _resolved_vessel(repo, root, None)
    packet = {
        "report_id": _building_event_report_id(
            f"{vessel_segment}{source_id}", event_kind, timestamp
        ),
        "report_kind": "building_frontier",
        "building_id": source_id,
        "portfolio_id": "",
        "observed_board_state": BUILDING_EVENT_OBSERVED_STATES[event_kind],
        "trigger_event_ref": trigger_event_ref
        or f"building-event:{event_kind}:{source_id}",
        "current_brick_ref": current_brick_ref
        or _current_brick_ref(building_map, frontier_kind),
        "last_completed_step_ref": last_completed_step_ref
        or _last_completed_step_ref(building_map),
        "frontier_ref": _building_event_frontier_ref(
            repo,
            root,
            event_kind=event_kind,
            frontier_kind=frontier_kind,
        ),
        "evidence_root_refs": [_rel(repo, root)],
        "evidence_refs_present": bool(building_map) and not missing_files,
        "checker_summary_ref": checker_summary_ref,
        "required_disposition_owner": _canonical_required_disposition_owner(
            required_disposition_owner
        )
        or _required_disposition_owner(frontier),
        "sink_refs": list(refs),
        "generated_at": timestamp,
        "source_truth": False,
        "not_proven": list(
            _merge_texts(
                REPORTER_NOT_PROVEN,
                BUILDING_EVENT_NOT_PROVEN,
                frontier.get("not_proven"),
                not_proven,
                (f"missing evidence ref: {item}" for item in missing_files),
            )
        ),
        "proof_limits": list(
            _merge_texts(
                REPORTER_PROOF_LIMITS,
                BUILDING_EVENT_PROOF_LIMITS,
                frontier.get("proof_limits"),
                proof_limits,
            )
        ),
    }
    if project_ref is not None:
        packet["project_ref"] = project_ref
    validate_report_packet(packet)
    return packet


def emit_building_event_report_packet(
    *,
    event_kind: str,
    building_id: str,
    building_root: str | Path,
    current_brick_ref: str = "",
    last_completed_step_ref: str = "",
    trigger_event_ref: str = "",
    checker_summary_ref: str = "",
    required_disposition_owner: str = "",
    sink_refs: Iterable[str] | None = None,
    repo_root: Path | str = REPO_ROOT,
    inbox_root: str | Path | None = None,
    generated_at: str | None = None,
    overwrite_existing: bool = False,
    allow_real_slack_delivery: bool = False,
    slack_timeout_seconds: float = 10.0,
    proof_limits: Iterable[str] | str | None = None,
    not_proven: Iterable[str] | str | None = None,
) -> Mapping[str, Any]:
    """Render and fan out one opt-in Building event notification packet."""

    repo = Path(repo_root).resolve()
    packet = render_building_event_report_packet(
        event_kind=event_kind,
        building_id=building_id,
        building_root=building_root,
        current_brick_ref=current_brick_ref,
        last_completed_step_ref=last_completed_step_ref,
        trigger_event_ref=trigger_event_ref,
        checker_summary_ref=checker_summary_ref,
        required_disposition_owner=required_disposition_owner,
        sink_refs=sink_refs,
        repo_root=repo,
        generated_at=generated_at,
        proof_limits=proof_limits,
        not_proven=not_proven,
    )
    observations = deliver_report_packet(
        packet,
        sink_refs=sink_refs,
        repo_root=repo,
        inbox_root=inbox_root,
        overwrite_existing=overwrite_existing,
        allow_real_slack_delivery=allow_real_slack_delivery,
        slack_timeout_seconds=slack_timeout_seconds,
    )
    return {
        "report_packet": dict(packet),
        "sink_observations": [observation.to_packet() for observation in observations],
        "proof_limits": list(_merge_texts(REPORTER_PROOF_LIMITS, BUILDING_EVENT_PROOF_LIMITS)),
        "not_proven": list(_merge_texts(REPORTER_NOT_PROVEN, BUILDING_EVENT_NOT_PROVEN)),
    }


def emit_building_event_for_policy(
    policy: Mapping[str, Any] | None,
    *,
    event_kind: str,
    building_id: str,
    building_root: str | Path,
    current_brick_ref: str = "",
    last_completed_step_ref: str = "",
    repo_root: Path | str = REPO_ROOT,
    inbox_root: str | Path | None = None,
    overwrite_existing: bool = False,
) -> Mapping[str, Any] | None:
    """Emit an event only when the caller-declared policy admits that kind."""

    if not policy:
        return None
    event_kinds = tuple(str(item) for item in policy.get("event_kinds", ()))
    if event_kind not in event_kinds:
        return None
    return emit_building_event_report_packet(
        event_kind=event_kind,
        building_id=building_id,
        building_root=building_root,
        current_brick_ref=current_brick_ref,
        last_completed_step_ref=last_completed_step_ref,
        sink_refs=policy.get("sink_refs"),
        repo_root=repo_root,
        inbox_root=inbox_root,
        overwrite_existing=overwrite_existing,
        allow_real_slack_delivery=bool(policy.get("allow_real_slack_delivery")),
        proof_limits=policy.get("proof_limits"),
        not_proven=policy.get("not_proven"),
    )



def render_report_packet(
    *,
    building_root: str | Path | None = None,
    portfolio_projection_path: str | Path | None = None,
    report_kind: str | None = None,
    trigger_event_ref: str = "",
    checker_summary_ref: str = "",
    sink_refs: Iterable[str] | None = None,
    operator_wake_targets: Iterable[Mapping[str, Any]] | None = None,
    repo_root: Path | str = REPO_ROOT,
    generated_at: str | None = None,
    project_ref: str | None = None,
) -> Mapping[str, Any]:
    """Render one report packet from persisted evidence.

    ``project_ref`` (PROJECT-0 S5-FIX, additive opt-in): when the caller
    declares the vessel of a building report, the packet records it and the
    report_id gains the vessel segment (multi-project inbox disambiguation).
    Legacy callers that omit it get byte-identical packets to before.
    """

    repo = Path(repo_root).resolve()
    if (building_root is None) == (portfolio_projection_path is None):
        raise ValueError("provide exactly one evidence source")
    if project_ref is not None and building_root is None:
        raise ValueError("project_ref is only meaningful with building_root")
    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    refs = tuple(sink_refs or (LOCAL_INBOX_SINK_REF,))
    wake_targets = _operator_wake_targets_or_none(operator_wake_targets)
    if building_root is not None:
        packet = _building_report_packet(
            repo,
            building_root,
            report_kind=report_kind or "building_frontier",
            trigger_event_ref=trigger_event_ref or "observation:building-frontier",
            checker_summary_ref=checker_summary_ref,
            sink_refs=refs,
            operator_wake_targets=wake_targets,
            generated_at=timestamp,
            project_ref=project_ref,
        )
    else:
        packet = _portfolio_report_packet(
            repo,
            portfolio_projection_path,
            report_kind=report_kind or "portfolio_frontier",
            trigger_event_ref=trigger_event_ref or "observation:portfolio-frontier",
            checker_summary_ref=checker_summary_ref,
            sink_refs=refs,
            operator_wake_targets=wake_targets,
            generated_at=timestamp,
        )
    validate_report_packet(packet)
    return packet


def emit_report_packet(
    *,
    building_root: str | Path | None = None,
    portfolio_projection_path: str | Path | None = None,
    report_kind: str | None = None,
    trigger_event_ref: str = "",
    checker_summary_ref: str = "",
    sink_refs: Iterable[str] | None = None,
    operator_wake_targets: Iterable[Mapping[str, Any]] | None = None,
    repo_root: Path | str = REPO_ROOT,
    inbox_root: str | Path | None = None,
    generated_at: str | None = None,
    overwrite_existing: bool = False,
    allow_real_slack_delivery: bool = False,
    slack_timeout_seconds: float = 10.0,
    project_ref: str | None = None,
) -> Mapping[str, Any]:
    """Render and fan out one report packet to admitted sinks."""

    repo = Path(repo_root).resolve()
    packet = render_report_packet(
        building_root=building_root,
        portfolio_projection_path=portfolio_projection_path,
        report_kind=report_kind,
        trigger_event_ref=trigger_event_ref,
        checker_summary_ref=checker_summary_ref,
        sink_refs=sink_refs,
        operator_wake_targets=operator_wake_targets,
        repo_root=repo,
        generated_at=generated_at,
        project_ref=project_ref,
    )
    observations = deliver_report_packet(
        packet,
        sink_refs=sink_refs,
        repo_root=repo,
        inbox_root=inbox_root,
        overwrite_existing=overwrite_existing,
        allow_real_slack_delivery=allow_real_slack_delivery,
        slack_timeout_seconds=slack_timeout_seconds,
    )
    return {
        "report_packet": dict(packet),
        "sink_observations": [observation.to_packet() for observation in observations],
        "proof_limits": list(REPORTER_PROOF_LIMITS),
        "not_proven": list(REPORTER_NOT_PROVEN),
    }


def dry_run_report_delivery_packet(
    packet: Mapping[str, Any],
    *,
    sink_refs: Iterable[str] | None = None,
    repo_root: Path | str = REPO_ROOT,
) -> Mapping[str, Any]:
    """Validate provider-neutral report delivery without writing sink packets."""

    validate_report_packet(packet)
    observations = dry_run_sink_report_packet(
        packet,
        sink_refs=sink_refs,
        repo_root=repo_root,
    )
    return {
        "report_packet": dict(packet),
        "sink_observations": [observation.to_packet() for observation in observations],
        "proof_limits": list(
            _merge_texts(
                REPORTER_PROOF_LIMITS,
                (
                    "report delivery pre-surface dry-run only",
                    "does not write project/brick-protocol/status/inbox",
                    "not real Slack delivery",
                    "not provider delivery",
                ),
            )
        ),
        "not_proven": list(
            _merge_texts(
                REPORTER_NOT_PROVEN,
                (
                    "real Slack delivery",
                    "external delivery",
                    "network delivery",
                    "reader noticed packet",
                    "operator noticed wake packet",
                ),
            )
        ),
    }


def validate_report_packet(packet: Mapping[str, Any]) -> None:
    """Reject report packet authority leakage and structural gaps."""

    if not isinstance(packet, Mapping):
        raise ValueError("report packet must be a mapping")
    missing = [field for field in REQUIRED_REPORT_PACKET_FIELDS if field not in packet]
    if missing:
        raise ValueError(f"report packet missing required field(s): {missing}")
    forbidden = sorted(set(_nested_keys(packet)) & FORBIDDEN_REPORT_PACKET_FIELDS)
    if forbidden:
        raise ValueError(f"report packet includes forbidden authority field(s): {forbidden}")
    if packet.get("source_truth") is not False:
        raise ValueError("report packet source_truth must be false")
    report_kind = _required_text(packet.get("report_kind"), "report_kind")
    if report_kind not in REPORT_KIND_VALUES:
        raise ValueError(f"unadmitted report_kind: {report_kind}")
    observed_board_state = _required_text(packet.get("observed_board_state"), "observed_board_state")
    if observed_board_state not in OBSERVED_BOARD_STATES:
        raise ValueError(f"unadmitted observed_board_state: {observed_board_state}")
    owner = str(packet.get("required_disposition_owner") or "").strip()
    if owner and owner not in TRANSITION_LIFECYCLE_DISPOSITION_OWNERS:
        raise ValueError(
            "report packet required_disposition_owner must be caller, coo, or caller-or-coo"
        )
    if "operator_wake_targets" in packet:
        validate_operator_wake_targets(packet.get("operator_wake_targets"))
    if "project_ref" in packet:
        # PROJECT-0 S5-FIX: additive vessel fact — when present it must be a
        # well-formed 'project:<slug>' ref (the same single slug law every
        # vessel seam enforces), never free text.
        raw_project_ref = packet.get("project_ref")
        if (
            not isinstance(raw_project_ref, str)
            or not raw_project_ref.startswith("project:")
            or not is_project_id_slug(raw_project_ref[len("project:") :])
        ):
            raise ValueError(
                "report packet project_ref must look like 'project:<id>' with a "
                f"[-_a-z0-9] slug id when present, got {raw_project_ref!r}"
            )
    _required_text(packet.get("report_id"), "report_id")
    _require_list(packet.get("evidence_root_refs"), "evidence_root_refs")
    _require_list(packet.get("sink_refs"), "sink_refs")
    _require_list(packet.get("proof_limits"), "proof_limits")
    _require_list(packet.get("not_proven"), "not_proven")
    if not isinstance(packet.get("evidence_refs_present"), bool):
        raise ValueError("evidence_refs_present must be a boolean")


def reporter_negative_probe_observations() -> tuple[Mapping[str, Any], ...]:
    """Return observations that invalid report packet probes are rejected."""

    base = _minimal_valid_probe_packet()
    probes: tuple[tuple[str, Mapping[str, Any]], ...] = (
        ("bad_source_truth_true", {**base, "source_truth": True}),
        ("bad_movement_choice_field", {**base, "movement_choice": "forward"}),
        ("bad_target_choice_field", {**base, "target_choice": "brick:anything"}),
        ("bad_success_field", {**base, "success": True}),
        ("bad_complete_field", {**base, "complete": True}),
        ("bad_complete_state", {**base, "observed_board_state": "complete"}),
        ("bad_driver_input_field", {**base, "driver_input": {"candidate": "brick:anything"}}),
        ("bad_required_disposition_owner_human", {**base, "required_disposition_owner": "human"}),
        ("bad_resume_route_field", {**base, "resume_route": True}),
        ("bad_raw_secret_field", {**base, "raw_secret": "redacted-probe"}),
        # PROJECT-0 S5-FIX: a malformed vessel ref (non-slug id) must reject —
        # the additive project_ref field obeys the single slug law.
        ("bad_project_ref_form", {**base, "project_ref": "project:ABC"}),
    )
    observations: list[Mapping[str, Any]] = []
    for label, candidate in probes:
        rejected = False
        reason = ""
        try:
            validate_report_packet(candidate)
        except ValueError as exc:
            rejected = True
            reason = str(exc)
        observations.append(
            {
                "probe_ref": f"reporter-negative-probe:{label}",
                "rejected": rejected,
                "reason": reason,
                "proof_limits": ["negative probe support evidence only"],
            }
        )
    return tuple(observations)


def reporter_delivery_wake_probe_observations() -> tuple[Mapping[str, Any], ...]:
    """Return observations for the local operator wake and delivery dry-run boundary."""

    base = {
        **_minimal_valid_probe_packet(),
        "sink_refs": [LOCAL_INBOX_SINK_REF, OPERATOR_WAKE_LOCAL_SINK_REF],
        "operator_wake_targets": [_minimal_operator_wake_target()],
    }
    probes: tuple[tuple[str, Mapping[str, Any], bool], ...] = (
        ("valid_operator_wake_target", base, True),
        (
            "bad_operator_wake_secret",
            {
                **base,
                "operator_wake_targets": [
                    {**_minimal_operator_wake_target(), "raw_secret": "redacted-probe"}
                ],
            },
            False,
        ),
        (
            "bad_operator_wake_resume_route",
            {
                **base,
                "operator_wake_targets": [
                    {**_minimal_operator_wake_target(), "resume_route": True}
                ],
            },
            False,
        ),
        (
            "bad_operator_wake_target_kind",
            {
                **base,
                "operator_wake_targets": [
                    {**_minimal_operator_wake_target(), "target_kind": "provider_thread"}
                ],
            },
            False,
        ),
    )
    observations: list[Mapping[str, Any]] = []
    for label, candidate, should_pass in probes:
        passed = False
        reason = ""
        try:
            validate_report_packet(candidate)
            passed = True
        except ValueError as exc:
            reason = str(exc)
        observations.append(
            {
                "probe_ref": f"reporter-delivery-wake-probe:{label}",
                "passed": passed is should_pass,
                "accepted": passed,
                "reason": reason,
                "proof_limits": ["delivery wake probe support evidence only"],
            }
        )
    observations.extend(reporter_delivery_pre_surface_probe_observations())
    return tuple(observations)


def reporter_delivery_pre_surface_probe_observations() -> tuple[Mapping[str, Any], ...]:
    """Return observations for provider-neutral no-write delivery dry-runs."""

    base = {
        **_minimal_valid_probe_packet(),
        "report_id": "report-delivery-pre-surface-probe",
        "report_kind": "delivery_observation",
        "trigger_event_ref": "observation:report-delivery-pre-surface",
        "checker_summary_ref": "support/checkers/profiles/reporter_notification_projection.yaml",
    }
    probes: tuple[tuple[str, Mapping[str, Any], Iterable[str] | None, bool], ...] = (
        ("valid_local_inbox_dry_run", base, None, True),
        (
            "valid_operator_wake_dry_run",
            {
                **base,
                "sink_refs": [LOCAL_INBOX_SINK_REF, OPERATOR_WAKE_LOCAL_SINK_REF],
                "operator_wake_targets": [_minimal_operator_wake_target()],
            },
            None,
            True,
        ),
        (
            "valid_slack_dry_run",
            {
                **base,
                "sink_refs": [SLACK_SINK_REF],
            },
            None,
            True,
        ),
        ("bad_unadmitted_sink_ref", base, ("report-sink:unadmitted",), False),
        ("bad_raw_secret_field", {**base, "raw_secret": "redacted-probe"}, None, False),
        ("bad_route_target_field", {**base, "route_target": "brick:anything"}, None, False),
        ("bad_slack_channel_id_field", {**base, "channel_id": "redacted-probe"}, None, False),
        ("bad_slack_bot_token_field", {**base, "slack_bot_token": "redacted-probe"}, None, False),
    )
    observations: list[Mapping[str, Any]] = []
    for label, candidate, override_sink_refs, should_pass in probes:
        accepted = False
        reason = ""
        wrote_packet = False
        try:
            result = dry_run_report_delivery_packet(
                candidate,
                sink_refs=override_sink_refs,
            )
            accepted = True
            wrote_packet = any(
                bool(observation.get("written_path"))
                for observation in result.get("sink_observations", ())
                if isinstance(observation, Mapping)
            )
        except ValueError as exc:
            reason = str(exc)
        observations.append(
            {
                "probe_ref": f"reporter-delivery-pre-surface-probe:{label}",
                "passed": (accepted is should_pass) and not wrote_packet,
                "accepted": accepted,
                "wrote_packet": wrote_packet,
                "reason": reason,
                "proof_limits": ["delivery pre-surface dry-run probe support evidence only"],
            }
        )
    return tuple(observations)


def reporter_owner_vocabulary_probe_observations() -> tuple[Mapping[str, Any], ...]:
    """Return observations that reporter owner emission stays Link-vocabulary only."""

    probes: tuple[tuple[str, Mapping[str, Any], str], ...] = (
        (
            "human_review_waiting_fallback",
            {"frontier_kind": "human_review_waiting"},
            "caller-or-coo",
        ),
        (
            "human_review_waiting_valid_lifecycle_owner",
            {
                "frontier_kind": "human_review_waiting",
                "latest_transition_lifecycle": {"required_disposition_owner": "coo"},
            },
            "coo",
        ),
        (
            "human_review_waiting_invalid_lifecycle_human",
            {
                "frontier_kind": "human_review_waiting",
                "latest_transition_lifecycle": {"required_disposition_owner": "human"},
            },
            "caller-or-coo",
        ),
    )
    observations: list[Mapping[str, Any]] = []
    for label, frontier, expected_owner in probes:
        emitted_owner = _required_disposition_owner(frontier)
        observations.append(
            {
                "probe_ref": f"reporter-owner-vocab-probe:{label}",
                "passed": emitted_owner == expected_owner,
                "emitted_owner": emitted_owner,
                "expected_owner": expected_owner,
                "proof_limits": ["owner vocabulary probe support evidence only"],
            }
        )
    return tuple(observations)


def reporter_event_hook_probe_observations() -> tuple[Mapping[str, Any], ...]:
    """Return observations for the opt-in Building event notification boundary."""

    observations: list[Mapping[str, Any]] = []

    def append(label: str, *, passed: bool, accepted: bool, reason: str = "") -> None:
        observations.append(
            {
                "probe_ref": f"reporter-event-hook-probe:{label}",
                "passed": passed,
                "accepted": accepted,
                "reason": reason,
                "proof_limits": ["Building event hook probe support evidence only"],
            }
        )

    append(
        "no_policy_no_event",
        passed=report_event_policy_from_plan({}) is None,
        accepted=False,
    )
    append(
        "disabled_policy_no_event",
        passed=report_event_policy_from_plan({"report_event_policy": {"enabled": False}})
        is None,
        accepted=False,
    )

    try:
        policy = report_event_policy_from_plan(
            {
                "report_event_policy": {
                    "enabled": True,
                    "sink_refs": [SLACK_SINK_REF],
                    "event_kinds": [
                        "building_started",
                        "intervention_required",
                        "building_finished",
                    ],
                    "allow_real_slack_delivery": True,
                    "proof_limits": ["support event notification only"],
                }
            }
        )
        append(
            "valid_opt_in_policy",
            passed=(
                isinstance(policy, Mapping)
                and policy.get("event_kinds")
                == ["building_started", "intervention_required", "building_finished"]
                and policy.get("sink_refs") == [SLACK_SINK_REF]
                and policy.get("allow_real_slack_delivery") is True
            ),
            accepted=True,
        )
    except ValueError as exc:
        append("valid_opt_in_policy", passed=False, accepted=False, reason=str(exc))

    try:
        report_event_policy_from_plan(
            {
                "report_event_policy": {
                    "enabled": True,
                    "event_kinds": ["step_completed"],
                }
            }
        )
        append("bad_step_completed_event", passed=False, accepted=True)
    except ValueError as exc:
        append(
            "bad_step_completed_event",
            passed="step_completed" in str(exc),
            accepted=False,
            reason=str(exc),
        )

    for event_kind, expected_state in BUILDING_EVENT_OBSERVED_STATES.items():
        try:
            packet = render_building_event_report_packet(
                event_kind=event_kind,
                building_id="probe-building",
                building_root="project/brick-protocol/buildings/probe-building",
                current_brick_ref="brick-probe",
                sink_refs=[SLACK_SINK_REF],
                generated_at="2026-06-03T00:00:00+00:00",
                proof_limits=["support event notification only"],
            )
            validate_report_packet(packet)
            forbidden = sorted(set(_nested_keys(packet)) & FORBIDDEN_REPORT_PACKET_FIELDS)
            append(
                f"render_{event_kind}",
                passed=(
                    packet.get("observed_board_state") == expected_state
                    and packet.get("source_truth") is False
                    and packet.get("trigger_event_ref")
                    == f"building-event:{event_kind}:probe-building"
                    and not forbidden
                ),
                accepted=True,
            )
        except ValueError as exc:
            append(f"render_{event_kind}", passed=False, accepted=False, reason=str(exc))

    observations.extend(reporter_vessel_auto_derivation_probe_observations())
    return tuple(observations)


def reporter_vessel_auto_derivation_probe_observations() -> tuple[Mapping[str, Any], ...]:
    """Return observations pinning the AUTO vessel derivation (Smith 0611).

    DECISIONS-WIRE AUTO-ON: a report packet for a building under a project
    vessel must carry project_ref + the vessel-segmented report_id WITHOUT the
    caller passing project_ref (the vessel is a PATH fact, derived through THE
    single inverse seam). Non-vessel roots must stay byte-identical legacy
    packets, and an explicit mismatched project_ref must still reject loudly.
    These probes pin the AUTO form, not just the S5-FIX opt-in form: sabotage
    the derivation (e.g. project_ref_for_building_root returning None always)
    and auto_vessel_* probes go red, driving the kernel check red.
    """

    import tempfile

    observations: list[Mapping[str, Any]] = []

    def append(label: str, *, passed: bool, reason: str = "") -> None:
        observations.append(
            {
                "probe_ref": f"reporter-vessel-auto-probe:{label}",
                "passed": passed,
                "reason": reason,
                "proof_limits": ["vessel auto-derivation probe support evidence only"],
            }
        )

    with tempfile.TemporaryDirectory(prefix="reporter-vessel-auto-probe-") as tmp:
        tmp_repo = Path(tmp)
        vessel_root = tmp_repo / "project" / "probe-vessel" / "buildings" / "probe-building"
        legacy_root = tmp_repo / "legacy-buildings" / "probe-building"
        for root in (vessel_root, legacy_root):
            (root / "work").mkdir(parents=True)
            (root / "work" / "building-map.json").write_text("{}\n", encoding="utf-8")

        try:
            packet = render_report_packet(
                building_root=vessel_root,
                repo_root=tmp_repo,
                generated_at="2026-06-11T00:00:00+00:00",
            )
            append(
                "auto_vessel_project_ref",
                passed=(
                    packet.get("project_ref") == "project:probe-vessel"
                    and packet.get("report_id") == "probe-vessel-probe-building-building-frontier"
                ),
                reason=f"report_id={packet.get('report_id')!r} project_ref={packet.get('project_ref')!r}",
            )
        except ValueError as exc:
            append("auto_vessel_project_ref", passed=False, reason=str(exc))

        try:
            event_packet = render_building_event_report_packet(
                event_kind="building_finished",
                building_id="probe-building",
                building_root=vessel_root,
                repo_root=tmp_repo,
                generated_at="2026-06-11T00:00:00+00:00",
            )
            append(
                "auto_vessel_event_report_id",
                passed=(
                    event_packet.get("project_ref") == "project:probe-vessel"
                    and str(event_packet.get("report_id")).startswith(
                        "probe-vessel-probe-building-building-finished-event-"
                    )
                ),
                reason=f"report_id={event_packet.get('report_id')!r}",
            )
        except ValueError as exc:
            append("auto_vessel_event_report_id", passed=False, reason=str(exc))

        try:
            legacy_packet = render_report_packet(
                building_root=legacy_root,
                repo_root=tmp_repo,
                generated_at="2026-06-11T00:00:00+00:00",
            )
            append(
                "non_vessel_legacy_id_unchanged",
                passed=(
                    "project_ref" not in legacy_packet
                    and legacy_packet.get("report_id") == "probe-building-building-frontier"
                ),
                reason=f"report_id={legacy_packet.get('report_id')!r}",
            )
        except ValueError as exc:
            append("non_vessel_legacy_id_unchanged", passed=False, reason=str(exc))

        try:
            render_report_packet(
                building_root=legacy_root,
                repo_root=tmp_repo,
                generated_at="2026-06-11T00:00:00+00:00",
                project_ref="project:probe-vessel",
            )
            append("explicit_mismatch_rejected", passed=False, reason="mismatch accepted")
        except ValueError as exc:
            append(
                "explicit_mismatch_rejected",
                passed="does not match the building root" in str(exc),
                reason=str(exc),
            )

    return tuple(observations)


def _resolved_vessel(
    repo: Path, root: Path, project_ref: str | None
) -> tuple[str | None, str]:
    """Resolve a building's vessel: (project_ref or None, report-id segment).

    PROJECT-0 S5-FIX made project_ref an opt-in caller declaration;
    DECISIONS-WIRE AUTO-ON (Smith 0611) turns derivation on: the vessel is a
    PATH fact, so when no explicit project_ref is passed it is derived from
    the building root through THE single inverse seam
    (capture.project_ref_for_building_root — no scattered path-parsing here).
    An EXPLICIT project_ref still wins and still fail-closes loudly when it
    does not match the seam-derived vessel root. Non-vessel roots (legacy/tmp)
    derive None: the packet stays byte-identical legacy (no project_ref field,
    un-segmented report_id).
    """

    if project_ref is not None and str(project_ref).strip():
        project_ref = str(project_ref).strip()
        vessel_root = buildings_root_for(project_ref)  # form fail-closed, THE seam
        expected_root = repo / vessel_root.relative_to(_CAPTURE_REPO_ROOT)
        if not root.is_relative_to(expected_root):
            raise ValueError(
                f"project_ref {project_ref!r} does not match the building root: "
                f"{root} is not under the seam-derived vessel root {expected_root}"
            )
        return project_ref, f"{vessel_root.parent.name}-"
    derived = project_ref_for_building_root(root, repo_root=repo)
    if derived is None:
        return None, ""
    vessel_root = buildings_root_for(derived)
    return derived, f"{vessel_root.parent.name}-"


def _building_report_packet(
    repo: Path,
    building_root: str | Path,
    *,
    report_kind: str,
    trigger_event_ref: str,
    checker_summary_ref: str,
    sink_refs: tuple[str, ...],
    operator_wake_targets: tuple[Mapping[str, Any], ...] | None,
    generated_at: str,
    project_ref: str | None = None,
) -> Mapping[str, Any]:
    root = _repo_path(repo, building_root)
    frontier = observe_building_frontier(root, repo_root=repo)
    building_map = _read_json_mapping(root / "work" / "building-map.json")
    building_id = _building_id(root, building_map)
    # PROJECT-0 S5-FIX introduced the opt-in vessel fact; DECISIONS-WIRE
    # AUTO-ON (Smith 0611) flips derivation on: when the caller passes no
    # project_ref, the vessel is derived from the building root PATH through
    # THE single inverse seam (see _resolved_vessel). Explicit refs still win
    # and still fail-close on mismatch; non-vessel roots stay legacy packets.
    project_ref, vessel_segment = _resolved_vessel(repo, root, project_ref)
    frontier_kind = str(frontier.get("frontier_kind") or "unknown")
    missing_files = tuple(str(item) for item in frontier.get("missing_required_files", ()))
    evidence_refs_present = not missing_files and bool(building_map)
    not_proven = _merge_texts(
        REPORTER_NOT_PROVEN,
        frontier.get("not_proven"),
        (f"missing evidence ref: {item}" for item in missing_files),
    )
    packet = {
        "report_id": _report_id(f"{vessel_segment}{building_id}", report_kind),
        "report_kind": report_kind,
        "building_id": building_id,
        "portfolio_id": "",
        "observed_board_state": _FRONTIER_TO_OBSERVED_STATE.get(frontier_kind, "observed_running"),
        "trigger_event_ref": trigger_event_ref,
        "current_brick_ref": _current_brick_ref(building_map, frontier_kind),
        "last_completed_step_ref": _last_completed_step_ref(building_map),
        "frontier_ref": f"{_rel(repo, root)}#frontier:{frontier_kind}",
        "evidence_root_refs": [_rel(repo, root)],
        "evidence_refs_present": evidence_refs_present,
        "checker_summary_ref": checker_summary_ref,
        "required_disposition_owner": _required_disposition_owner(frontier),
        "sink_refs": list(sink_refs),
        "generated_at": generated_at,
        "source_truth": False,
        "not_proven": list(not_proven),
        "proof_limits": list(_merge_texts(REPORTER_PROOF_LIMITS, frontier.get("proof_limits"))),
    }
    if project_ref is not None:
        packet["project_ref"] = project_ref
    if operator_wake_targets is not None:
        packet["operator_wake_targets"] = [dict(target) for target in operator_wake_targets]
    return packet


def _portfolio_report_packet(
    repo: Path,
    portfolio_projection_path: str | Path,
    *,
    report_kind: str,
    trigger_event_ref: str,
    checker_summary_ref: str,
    sink_refs: tuple[str, ...],
    operator_wake_targets: tuple[Mapping[str, Any], ...] | None,
    generated_at: str,
) -> Mapping[str, Any]:
    path = _repo_path(repo, portfolio_projection_path)
    projection = _read_json_mapping(path)
    portfolio_id = str(projection.get("portfolio_ref") or path.stem)
    frontier = projection.get("frontier")
    frontier_map = frontier if isinstance(frontier, Mapping) else {}
    frontier_kind = str(frontier_map.get("frontier_kind") or projection.get("frontier_kind") or "unknown")
    packet = {
        "report_id": _report_id(portfolio_id, report_kind),
        "report_kind": report_kind,
        "building_id": "",
        "portfolio_id": portfolio_id,
        "observed_board_state": _FRONTIER_TO_OBSERVED_STATE.get(frontier_kind, "observed_running"),
        "trigger_event_ref": trigger_event_ref,
        "current_brick_ref": "",
        "last_completed_step_ref": "",
        "frontier_ref": f"{_rel(repo, path)}#frontier:{frontier_kind}",
        "evidence_root_refs": [_rel(repo, path)],
        "evidence_refs_present": bool(projection),
        "checker_summary_ref": checker_summary_ref,
        "required_disposition_owner": _required_disposition_owner(frontier_map),
        "sink_refs": list(sink_refs),
        "generated_at": generated_at,
        "source_truth": False,
        "not_proven": list(_merge_texts(REPORTER_NOT_PROVEN, projection.get("not_proven"))),
        "proof_limits": list(_merge_texts(REPORTER_PROOF_LIMITS, projection.get("proof_limits"))),
    }
    if operator_wake_targets is not None:
        packet["operator_wake_targets"] = [dict(target) for target in operator_wake_targets]
    return packet


def _minimal_valid_probe_packet() -> Mapping[str, Any]:
    return {
        "report_id": "reporter-negative-probe-valid",
        "report_kind": "building_frontier",
        "building_id": "probe-building",
        "portfolio_id": "",
        "observed_board_state": "observed_running",
        "trigger_event_ref": "observation:probe",
        "current_brick_ref": "brick:probe",
        "last_completed_step_ref": "",
        "frontier_ref": "project/brick-protocol/buildings/probe#frontier:closure_pending",
        "evidence_root_refs": ["project/brick-protocol/buildings/probe"],
        "evidence_refs_present": False,
        "checker_summary_ref": "",
        "required_disposition_owner": "",
        "sink_refs": [LOCAL_INBOX_SINK_REF],
        "generated_at": "2026-05-31T00:00:00+00:00",
        "source_truth": False,
        "not_proven": ["negative probe"],
        "proof_limits": ["negative probe support evidence only"],
    }


def _minimal_operator_wake_target() -> Mapping[str, Any]:
    return {
        "target_ref": "operator-wake-target:local-active-operator",
        "target_kind": "operator_wake_local",
        "sink_ref": OPERATOR_WAKE_LOCAL_SINK_REF,
        "delivery_mode": "local_projection",
        "side_effect_state": "none",
        "proof_limits": ["provider-neutral local wake target reference only"],
        "not_proven": [
            "operator noticed wake packet",
            "real provider thread wake behavior",
            "external side effect behavior",
        ],
    }


def _nested_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _nested_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_keys(child)


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, Mapping) else {}


def _building_id(root: Path, building_map: Mapping[str, Any]) -> str:
    value = building_map.get("building_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return root.name


def _current_brick_ref(building_map: Mapping[str, Any], frontier_kind: str) -> str:
    edges = _mapping_list(building_map.get("link_edges"))
    if edges:
        key = "target_brick_instance_ref" if frontier_kind == "complete" else "source_brick_instance_ref"
        value = edges[-1].get(key)
        if isinstance(value, str):
            return value
    bricks = _mapping_list(building_map.get("brick_instances"))
    if bricks:
        value = bricks[-1].get("brick_instance_id")
        if isinstance(value, str):
            return value
    return ""


def _last_completed_step_ref(building_map: Mapping[str, Any]) -> str:
    edges = _mapping_list(building_map.get("link_edges"))
    if edges:
        value = edges[-1].get("step_output_ref")
        if isinstance(value, str):
            return value
    return ""


def _required_disposition_owner(frontier: Mapping[str, Any]) -> str:
    lifecycle = frontier.get("latest_transition_lifecycle")
    if isinstance(lifecycle, Mapping):
        owner = _canonical_required_disposition_owner(lifecycle.get("required_disposition_owner"))
        if not owner:
            owner = _canonical_required_disposition_owner(
                lifecycle.get("transition_lifecycle_required_disposition_owner")
            )
        if owner:
            return owner
    owner = _canonical_required_disposition_owner(frontier.get("required_disposition_owner"))
    if owner:
        return owner
    if frontier.get("frontier_kind") == "human_review_waiting":
        return "caller-or-coo"
    if frontier.get("frontier_kind") == "chat_session_parked":
        return "caller-or-coo"
    if frontier.get("frontier_kind") == "link_paused":
        return "coo"
    return ""


def _canonical_required_disposition_owner(value: Any) -> str:
    if isinstance(value, str):
        owner = value.strip()
        if owner in TRANSITION_LIFECYCLE_DISPOSITION_OWNERS:
            return owner
    return ""


def _mapping_list(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _operator_wake_targets_or_none(
    value: Iterable[Mapping[str, Any]] | None,
) -> tuple[Mapping[str, Any], ...] | None:
    if value is None:
        return None
    return tuple(validate_operator_wake_targets(list(value)))


def _repo_path(repo: Path, value: Path | str) -> Path:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo / candidate).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"path escapes repo: {value}") from exc
    return resolved


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _require_list(value: Any, label: str) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")


def _report_id(source_id: str, report_kind: str) -> str:
    return f"{source_id}-{report_kind.replace('_', '-')}"


def _building_event_report_id(source_id: str, event_kind: str, generated_at: str) -> str:
    timestamp = "".join(
        char if char.isalnum() else "-"
        for char in generated_at.strip()
    ).strip("-")
    return f"{source_id}-{event_kind.replace('_', '-')}-event-{timestamp}"


def _building_event_frontier_ref(
    repo: Path,
    root: Path,
    *,
    event_kind: str,
    frontier_kind: str,
) -> str:
    if frontier_kind:
        return f"{_rel(repo, root)}#frontier:{frontier_kind}:event:{event_kind}"
    return f"{_rel(repo, root)}#building-event:{event_kind}"


def _building_event_root(repo: Path, value: Path | str) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (repo / candidate).resolve()


def _policy_text_tuple(
    value: Any,
    label: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")
    texts = tuple(item.strip() for item in value if item.strip())
    return texts or default


def _merge_texts(*values: Any) -> tuple[str, ...]:
    merged: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            candidates = (value,)
        else:
            candidates = tuple(value)
        for item in candidates:
            if isinstance(item, str) and item.strip() and item.strip() not in merged:
                merged.append(item.strip())
    return tuple(merged)


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return path.resolve().as_posix()

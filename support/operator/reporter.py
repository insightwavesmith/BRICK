"""Support-only report packet renderer and local inbox coordinator."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brick_protocol.link.transition import TRANSITION_LIFECYCLE_DISPOSITION_OWNERS
from brick_protocol.support.connection.agent_resources import (
    AgentResourceError,
    resolve_agent_object,
)
from brick_protocol.support.operator.building_operation import observe_building_frontier
from brick_protocol.support.recording.capture import (
    BRICK_EVIDENCE_HOME,
    REPO_ROOT as _CAPTURE_REPO_ROOT,
    buildings_root_for,
    is_project_id_slug,
    project_ref_for_building_root,
)
from brick_protocol.support.operator.report_sinks import (
    ADMITTED_SINK_REFS,
    DASHBOARD_INGEST_SECRET_ENV,
    DASHBOARD_INGEST_URL_ENV,
    DASHBOARD_SINK_REF,
    LOCAL_INBOX_SINK_REF,
    OPERATOR_WAKE_LOCAL_SINK_REF,
    SLACK_BOT_TOKEN_ENV,
    SLACK_CHANNEL_ID_ENV,
    SLACK_SINK_REF,
    SlackSender,
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
    "current_work_kind",
    "current_lane",
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
REPORT_GRAIN_ENV = "BRICK_REPORT_GRAIN"
REPORT_EVENT_GRAINS = frozenset({"building", "brick"})
BRICK_GRAIN_EVENT_KINDS: tuple[str, ...] = (
    "brick_received",
    "brick_returned",
    "gate_passed",
    "disposition_applied",
)
BUILDING_EVENT_KINDS = frozenset(
    {
        "building_started",
        "intervention_required",
        "building_finished",
        *BRICK_GRAIN_EVENT_KINDS,
    }
)
REPORT_EVENT_MODES = frozenset({"basic", "verbose"})
BUILDING_EVENT_OBSERVED_STATES = {
    "building_started": "observed_started",
    "intervention_required": "observed_paused",
    "building_finished": "observed_closed_boundary",
    "brick_received": "observed_running",
    "brick_returned": "observed_running",
    "gate_passed": "observed_running",
    "disposition_applied": "observed_running",
}
BUILDING_EVENT_FRONTIER_KINDS = {
    "complete": "building_finished",
    "link_paused": "intervention_required",
    "human_review_waiting": "intervention_required",
    "chat_session_parked": "intervention_required",
}
BUILDING_EVENT_PROOF_LIMITS: tuple[str, ...] = (
    "Building event notification support projection only",
    "default delivery is synchronous and best-effort",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route target choice",
    "not scheduler / queue / retry runtime",
)
DEFAULT_BUILDING_EVENT_KINDS: tuple[str, ...] = (
    "building_started",
    "intervention_required",
    "building_finished",
)
EXTERNAL_BUILDING_EVENT_SINK_REFS = frozenset({SLACK_SINK_REF, DASHBOARD_SINK_REF})
DEFAULT_BUILDING_EVENT_SINK_REFS: tuple[str, ...] = (
    LOCAL_INBOX_SINK_REF,
    SLACK_SINK_REF,
    DASHBOARD_SINK_REF,
)
BUILDING_EVENT_NOT_PROVEN: tuple[str, ...] = (
    "event delivery reliability",
    "reader noticed event notification",
    "parallel runtime timing",
    "production readiness",
)


def report_event_policy_from_plan(plan: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return a validated event policy.

    An absent policy defaults to local inbox plus env-gated external sinks.
    A declared disabled policy remains an explicit no-event declaration.
    """

    raw_policy = plan.get("report_event_policy")
    if raw_policy is None:
        return _default_report_event_policy()
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

    mode = str(raw_policy.get("mode") or "basic").strip()
    if mode not in REPORT_EVENT_MODES:
        raise ValueError(f"unadmitted report_event_policy.mode: {mode}")
    grain = _report_event_grain(
        raw_policy.get("grain", raw_policy.get("report_event_grain"))
    )

    event_kinds = _policy_text_tuple(
        raw_policy.get("event_kinds"),
        "report_event_policy.event_kinds",
        default=DEFAULT_BUILDING_EVENT_KINDS,
    )
    if grain == "brick":
        event_kinds = _merge_texts(event_kinds, BRICK_GRAIN_EVENT_KINDS)
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
    allow_real_dashboard_delivery = raw_policy.get("allow_real_dashboard_delivery", False)
    if not isinstance(allow_real_dashboard_delivery, bool):
        raise ValueError("report_event_policy.allow_real_dashboard_delivery must be a boolean")

    policy = {
        "enabled": True,
        "mode": mode,
        "event_kinds": list(event_kinds),
        "sink_refs": list(sink_refs),
        "allow_real_slack_delivery": allow_real_slack_delivery,
        "allow_real_dashboard_delivery": allow_real_dashboard_delivery,
        "environment_gated_sink_refs": [],
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
    if grain == "brick":
        policy["report_event_grain"] = "brick"
    return policy


def _default_report_event_policy() -> Mapping[str, Any]:
    grain = _report_event_grain(None)
    event_kinds = DEFAULT_BUILDING_EVENT_KINDS
    if grain == "brick":
        event_kinds = _merge_texts(event_kinds, BRICK_GRAIN_EVENT_KINDS)
    policy = {
        "enabled": True,
        "mode": "basic",
        "event_kinds": list(event_kinds),
        "sink_refs": list(DEFAULT_BUILDING_EVENT_SINK_REFS),
        "allow_real_slack_delivery": True,
        "allow_real_dashboard_delivery": True,
        "environment_gated_sink_refs": [SLACK_SINK_REF, DASHBOARD_SINK_REF],
        "defaulted_from_absent_policy": True,
        "proof_limits": list(BUILDING_EVENT_PROOF_LIMITS),
        "not_proven": list(BUILDING_EVENT_NOT_PROVEN),
    }
    if grain == "brick":
        policy["report_event_grain"] = "brick"
    return policy


def _event_policy_sink_refs(
    policy: Mapping[str, Any],
    *,
    slack_env: Mapping[str, str] | None = None,
    dashboard_env: Mapping[str, str] | None = None,
) -> list[str]:
    refs = [str(item).strip() for item in policy.get("sink_refs", ()) if str(item).strip()]
    if not refs:
        refs = [LOCAL_INBOX_SINK_REF]
    gated = {str(item).strip() for item in policy.get("environment_gated_sink_refs", ())}
    if SLACK_SINK_REF in refs and SLACK_SINK_REF in gated and not _slack_environment_ready(slack_env):
        refs = [ref for ref in refs if ref != SLACK_SINK_REF]
    if (
        DASHBOARD_SINK_REF in refs
        and DASHBOARD_SINK_REF in gated
        and not _dashboard_environment_ready(dashboard_env)
    ):
        refs = [ref for ref in refs if ref != DASHBOARD_SINK_REF]
    return refs or [LOCAL_INBOX_SINK_REF]


def _slack_environment_ready(env: Mapping[str, str] | None = None) -> bool:
    env_map = os.environ if env is None else env
    return bool(env_map.get(SLACK_BOT_TOKEN_ENV) and env_map.get(SLACK_CHANNEL_ID_ENV))


def _dashboard_environment_ready(env: Mapping[str, str] | None = None) -> bool:
    env_map = os.environ if env is None else env
    return bool(env_map.get(DASHBOARD_INGEST_URL_ENV) and env_map.get(DASHBOARD_INGEST_SECRET_ENV))


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
    stage_mode: str = "basic",
    generated_at: str | None = None,
    report_event_grain: str = "",
    event_context: Mapping[str, Any] | None = None,
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
    checked_stage_mode = _report_event_mode(stage_mode)
    building_map = _read_json_mapping(root / "work" / "building-map.json")
    frontier: Mapping[str, Any] = {}
    if root.exists():
        frontier = observe_building_frontier(root, repo_root=repo)
    frontier_kind = str(frontier.get("frontier_kind") or "")
    missing_files = tuple(str(item) for item in frontier.get("missing_required_files", ()))
    source_id = _required_text(building_id or _building_id(root, building_map), "building_id")
    projected_current_brick_ref = current_brick_ref or _current_brick_ref(
        building_map, frontier_kind
    )
    projected_last_completed_step_ref = (
        last_completed_step_ref or _last_completed_step_ref(building_map)
    )
    projected_facts = _current_declared_projection(
        repo,
        root,
        building_map,
        frontier_kind=frontier_kind,
        current_brick_ref=projected_current_brick_ref,
        last_completed_step_ref=projected_last_completed_step_ref,
    )
    # DECISIONS-WIRE AUTO-ON (Smith 0611): Building event packets derive the
    # vessel from the building root PATH too — same inverse seam, same
    # legacy-unchanged behavior for non-vessel roots.
    project_ref, vessel_segment = _resolved_vessel(repo, root, None)
    external_delivery_allowed = _building_root_is_real_vessel(repo, root)
    packet = {
        "report_id": _building_event_report_id(
            f"{vessel_segment}{source_id}", event_kind, timestamp
        ),
        "report_kind": "building_frontier",
        "building_id": source_id,
        "portfolio_id": "",
        "human_title": _human_title(root, source_id),
        "report_event_mode": checked_stage_mode,
        "external_delivery_allowed": external_delivery_allowed,
        "observed_board_state": BUILDING_EVENT_OBSERVED_STATES[event_kind],
        "trigger_event_ref": trigger_event_ref
        or f"building-event:{event_kind}:{source_id}",
        "current_brick_ref": projected_current_brick_ref,
        "current_work_kind": str(projected_facts.get("current_work_kind") or ""),
        "current_lane": str(projected_facts.get("current_lane") or ""),
        "current_agent_object_ref": str(
            projected_facts.get("current_agent_object_ref") or ""
        ),
        "current_adapter_ref": str(projected_facts.get("current_adapter_ref") or ""),
        "current_model_ref": str(projected_facts.get("current_model_ref") or ""),
        "last_completed_step_ref": projected_last_completed_step_ref,
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
                projected_facts.get("not_proven"),
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
    if event_kind in BRICK_GRAIN_EVENT_KINDS or report_event_grain == "brick":
        packet["report_event_grain"] = "brick"
    if event_context:
        packet["event_context"] = _report_event_context(event_context)
    if event_kind == "building_started":
        diagram = _structure_diagram_text(repo, root, building_map)
        if diagram:
            packet["structure_diagram"] = diagram
    if checked_stage_mode == "verbose":
        packet["completed_step_kinds"] = list(_completed_step_kinds(root, building_map))
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
    slack_env: Mapping[str, str] | None = None,
    slack_sender: SlackSender | None = None,
    allow_real_dashboard_delivery: bool = False,
    dashboard_timeout_seconds: float = 10.0,
    dashboard_env: Mapping[str, str] | None = None,
    stage_mode: str = "basic",
    report_event_grain: str = "",
    event_context: Mapping[str, Any] | None = None,
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
        stage_mode=stage_mode,
        generated_at=generated_at,
        report_event_grain=report_event_grain,
        event_context=event_context,
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
        slack_env=slack_env,
        slack_sender=slack_sender,
        allow_real_dashboard_delivery=allow_real_dashboard_delivery,
        dashboard_timeout_seconds=dashboard_timeout_seconds,
        dashboard_env=dashboard_env,
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
    slack_env: Mapping[str, str] | None = None,
    slack_sender: SlackSender | None = None,
    dashboard_env: Mapping[str, str] | None = None,
    event_context: Mapping[str, Any] | None = None,
) -> Mapping[str, Any] | None:
    """Emit an event only when the caller-declared policy admits that kind."""

    if not policy:
        return None
    event_kinds = tuple(str(item) for item in policy.get("event_kinds", ()))
    if event_kind not in event_kinds:
        return None
    repo = Path(repo_root).resolve()
    root = _building_event_root(repo, building_root)
    sink_refs = _event_policy_sink_refs(
        policy,
        slack_env=slack_env,
        dashboard_env=dashboard_env,
    )
    sink_refs = _sink_refs_for_building_event_root(sink_refs, repo=repo, root=root)
    if not sink_refs:
        return None
    return emit_building_event_report_packet(
        event_kind=event_kind,
        building_id=building_id,
        building_root=building_root,
        current_brick_ref=current_brick_ref,
        last_completed_step_ref=last_completed_step_ref,
        sink_refs=sink_refs,
        repo_root=repo,
        inbox_root=inbox_root,
        overwrite_existing=overwrite_existing,
        allow_real_slack_delivery=bool(policy.get("allow_real_slack_delivery")),
        slack_env=slack_env,
        slack_sender=slack_sender,
        allow_real_dashboard_delivery=bool(policy.get("allow_real_dashboard_delivery")),
        dashboard_env=dashboard_env,
        stage_mode=str(policy.get("mode") or "basic"),
        report_event_grain=str(policy.get("report_event_grain") or ""),
        event_context=event_context,
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
    for projected_field in (
        "current_work_kind",
        "current_lane",
        "current_agent_object_ref",
        "current_adapter_ref",
        "current_model_ref",
    ):
        if packet.get(projected_field) is not None and not isinstance(
            packet.get(projected_field), str
        ):
            raise ValueError(f"report packet {projected_field} must be a string")
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

    previous_grain = os.environ.pop(REPORT_GRAIN_ENV, None)
    try:
        default_policy = report_event_policy_from_plan({})
    finally:
        if previous_grain is not None:
            os.environ[REPORT_GRAIN_ENV] = previous_grain
    expected_default_events = list(
        _merge_texts(DEFAULT_BUILDING_EVENT_KINDS, BRICK_GRAIN_EVENT_KINDS)
    )
    append(
        "absent_policy_defaults_to_local_env_gated_sinks",
        passed=(
            isinstance(default_policy, Mapping)
            and default_policy.get("event_kinds")
            == expected_default_events
            and default_policy.get("sink_refs")
            == [LOCAL_INBOX_SINK_REF, SLACK_SINK_REF, DASHBOARD_SINK_REF]
            and default_policy.get("environment_gated_sink_refs")
            == [SLACK_SINK_REF, DASHBOARD_SINK_REF]
            and default_policy.get("mode") == "basic"
            and default_policy.get("report_event_grain") == "brick"
        ),
        accepted=True,
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
                    "grain": "building",
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


def _building_root_is_real_vessel(repo: Path, root: Path) -> bool:
    # EVROOT2 RECONCILIATION (slack-wiring-gap 0619): the building's evidence
    # root no longer has to live under the SOURCE worktree REPO_ROOT. Under the
    # EVROOT2 relocation the evidence home is decoupled to ~/.brick (or
    # $BRICK_HOME), so ``repo`` derived by _report_repo_root_for_building_root is
    # the evidence home, not REPO_ROOT. The pre-fix guard ``repo != REPO_ROOT ->
    # not-a-vessel`` mis-classified EVERY ~/.brick-rooted building as a non-vessel
    # and silently stripped slack+dashboard to inbox-only (the live bug).
    #
    # The fix accepts a real vessel under EITHER recognized home -- the source
    # REPO_ROOT *or* the EVROOT2 evidence home (BRICK_EVIDENCE_HOME() = $BRICK_HOME
    # or ~/.brick) -- and STILL rejects an arbitrary ``repo`` that merely happens to
    # carry the project/<id>/buildings path shape (e.g. a throwaway temp dir). This
    # keeps the property the original equality guard protected: a non-home repo is
    # not a real vessel, so its external (slack/dashboard) sinks stay stripped. The
    # vessel fact is then a PATH fact under a recognized home:
    # project_ref_for_building_root(root, repo_root=repo) returns None for any path
    # not under the GIVEN repo's project/<id>/buildings layout, so a garbage path or
    # a repo/root mismatch is still rejected. The slack creds were independently
    # confirmed present by the env gate, so this does NOT widen credential exposure.
    #
    # SLACK VESSEL-GATE MIN-FIX (slack-wiring-gap 0619, codex adversarial review):
    # the recognized-home + path-shape checks alone are NOT enough. The evidence
    # home (BRICK_EVIDENCE_HOME() = $BRICK_HOME) is CALLER-controlled, and
    # project_ref_for_building_root only verifies the project/<id>/buildings PATH
    # SHAPE -- it never looks at whether a real building actually lives there. So a
    # caller can point $BRICK_HOME at a throwaway tree, ``mkdir -p`` an empty
    # project/<slug>/buildings/<id> path, and that empty mimic would pass every
    # check above and fire slack/dashboard -- a test or foreign-project building
    # could spam the real Slack, defeating the whole reason the vessel gate exists.
    #
    # The narrowing requires ONE MORE proof before an external (slack/dashboard)
    # sink survives: the root must carry REAL building-spine evidence -- a declared
    # building plan (root/declared-building-plan.json or root/work/..., the same
    # spine _declared_plan_for_building consumes). An empty path-shape mkdir has no
    # plan and is rejected; the genuine EVROOT2 ~/.brick building (which always
    # writes its declared plan) still passes, so its slack stays alive.
    recognized_homes = {REPO_ROOT.resolve(), BRICK_EVIDENCE_HOME().resolve()}
    if repo.resolve() not in recognized_homes:
        return False
    project_ref = project_ref_for_building_root(root, repo_root=repo)
    if project_ref is None:
        return False
    vessel_root = repo / buildings_root_for(project_ref).relative_to(_CAPTURE_REPO_ROOT)
    try:
        root.resolve().relative_to(vessel_root.resolve())
    except ValueError:
        return False
    if not _building_root_has_declared_spine(root):
        return False
    return True


def _building_root_has_declared_spine(root: Path) -> bool:
    """True iff ``root`` carries a real building's declared-plan spine.

    This is the EVIDENCE-EXISTENCE proof the vessel gate requires before an
    external (slack/dashboard) sink survives: a real building writes its declared
    building plan at the building root (or under work/); an empty path-shape mkdir
    -- the exact mimic a caller could conjure under a caller-controlled
    $BRICK_HOME -- has no such plan. Mirrors the on-disk spine locations
    _declared_plan_for_building reads (the declaration-provenance copy carried on
    the building-map is NOT accepted here on purpose: the on-disk spine FILE is
    the hard evidence-existence fact, not a map field a mimic could fabricate).
    """

    for path in (
        root / "declared-building-plan.json",
        root / "work" / "declared-building-plan.json",
    ):
        if _declared_steps(_declared_plan_packet(path)):
            return True
    return False


def _declared_plan_packet(path: Path) -> Mapping[str, Any]:
    packet = _read_json_mapping(path)
    plan = packet.get("declared_plan_copy")
    return plan if isinstance(plan, Mapping) else packet


def _sink_refs_for_building_event_root(
    sink_refs: Iterable[str],
    *,
    repo: Path,
    root: Path,
) -> list[str]:
    refs = [str(ref).strip() for ref in sink_refs if str(ref).strip()]
    if _building_root_is_real_vessel(repo, root):
        return refs
    return [ref for ref in refs if ref not in EXTERNAL_BUILDING_EVENT_SINK_REFS]


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
    external_delivery_allowed = _building_root_is_real_vessel(repo, root)
    frontier_kind = str(frontier.get("frontier_kind") or "unknown")
    missing_files = tuple(str(item) for item in frontier.get("missing_required_files", ()))
    evidence_refs_present = not missing_files and bool(building_map)
    current_brick_ref = _current_brick_ref(building_map, frontier_kind)
    last_completed_step_ref = _last_completed_step_ref(building_map)
    projected_facts = _current_declared_projection(
        repo,
        root,
        building_map,
        frontier_kind=frontier_kind,
        current_brick_ref=current_brick_ref,
        last_completed_step_ref=last_completed_step_ref,
    )
    not_proven = _merge_texts(
        REPORTER_NOT_PROVEN,
        frontier.get("not_proven"),
        projected_facts.get("not_proven"),
        (f"missing evidence ref: {item}" for item in missing_files),
    )
    packet = {
        "report_id": _report_id(f"{vessel_segment}{building_id}", report_kind),
        "report_kind": report_kind,
        "building_id": building_id,
        "portfolio_id": "",
        "human_title": _human_title(root, building_id),
        "external_delivery_allowed": external_delivery_allowed,
        "observed_board_state": _FRONTIER_TO_OBSERVED_STATE.get(frontier_kind, "observed_running"),
        "trigger_event_ref": trigger_event_ref,
        "current_brick_ref": current_brick_ref,
        "current_work_kind": str(projected_facts.get("current_work_kind") or ""),
        "current_lane": str(projected_facts.get("current_lane") or ""),
        "current_agent_object_ref": str(
            projected_facts.get("current_agent_object_ref") or ""
        ),
        "current_adapter_ref": str(projected_facts.get("current_adapter_ref") or ""),
        "current_model_ref": str(projected_facts.get("current_model_ref") or ""),
        "last_completed_step_ref": last_completed_step_ref,
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
        "current_work_kind": "",
        "current_lane": "",
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
        "current_work_kind": "work",
        "current_lane": "worker",
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


def _current_declared_projection(
    repo: Path,
    root: Path,
    building_map: Mapping[str, Any],
    *,
    frontier_kind: str,
    current_brick_ref: str,
    last_completed_step_ref: str,
) -> Mapping[str, Any]:
    plan = _declared_plan_for_building(root, building_map)
    if not plan:
        return {
            "current_work_kind": "",
            "current_lane": "",
            "current_agent_object_ref": "",
            "current_adapter_ref": "",
            "current_model_ref": "",
            "not_proven": ["declared plan evidence for notification labels was not readable"],
        }
    work_brick_ref = _current_work_brick_ref(building_map, frontier_kind, current_brick_ref)
    step = _declared_step_for_brick_ref(plan, work_brick_ref)
    if step is None:
        step_ref = _step_ref_from_step_output_ref(last_completed_step_ref)
        step = _declared_step_for_step_ref(plan, step_ref)
    if step is None:
        return {
            "current_work_kind": "",
            "current_lane": "",
            "current_agent_object_ref": "",
            "current_adapter_ref": "",
            "current_model_ref": "",
            "not_proven": ["declared step for notification labels was not resolved"],
        }
    work_kind = _step_template_kind(str(step.get("step_template_ref") or ""))
    agent_object_ref = _agent_object_ref_from_step(step)
    lane, lane_not_proven = _agent_lane_for_ref(agent_object_ref, repo)
    not_proven = []
    if not work_kind:
        not_proven.append("declared step_template_ref for notification label was not resolved")
    if lane_not_proven:
        not_proven.extend(lane_not_proven)
    return {
        "current_work_kind": work_kind,
        "current_lane": lane,
        "current_agent_object_ref": agent_object_ref,
        "current_adapter_ref": str(step.get("selected_adapter_ref") or "").strip(),
        "current_model_ref": str(step.get("selected_model_ref") or "").strip(),
        "not_proven": not_proven,
    }


def _completed_step_kinds(root: Path, building_map: Mapping[str, Any]) -> tuple[str, ...]:
    plan = _declared_plan_for_building(root, building_map)
    if not plan:
        return ()
    kinds: list[str] = []
    for edge in _mapping_list(building_map.get("link_edges")):
        step_ref = str(edge.get("source_step_ref") or "").strip()
        if not step_ref:
            step_ref = _step_ref_from_step_output_ref(str(edge.get("step_output_ref") or ""))
        step = _declared_step_for_step_ref(plan, step_ref)
        if step is None:
            continue
        kind = _step_template_kind(str(step.get("step_template_ref") or ""))
        if kind:
            kinds.append(kind)
    return tuple(kinds)


def _structure_diagram_text(repo: Path, root: Path, building_map: Mapping[str, Any]) -> str:
    """Render a customer-facing Building structure diagram from declared plan evidence."""

    try:
        plan = _declared_plan_for_building(root, building_map)
        steps = _ordered_declared_steps(plan)
        if not steps:
            return ""
        step_by_ref = {
            step_ref: step
            for step in steps
            if (step_ref := str(step.get("step_ref") or "").strip())
        }
        if not step_by_ref:
            return ""
        order = [str(step.get("step_ref") or "").strip() for step in steps]
        labels = {
            step_ref: _structure_step_label(repo, step)
            for step_ref, step in step_by_ref.items()
        }
        edges = _mapping_list(plan.get("link_edges"))
        if not edges:
            return _linear_structure_diagram(order, labels, _linear_plan_has_terminal(steps))

        adjacency: dict[str, list[str]] = {}
        reverse: dict[str, list[str]] = {}
        terminal_sources: set[str] = set()
        for edge in edges:
            source_ref = str(edge.get("source_step_ref") or "").strip()
            target_ref = str(edge.get("target_step_ref") or "").strip()
            if not source_ref or source_ref not in step_by_ref:
                continue
            if target_ref and target_ref in step_by_ref:
                adjacency.setdefault(source_ref, []).append(target_ref)
                reverse.setdefault(target_ref, []).append(source_ref)
                continue
            if _link_edge_points_to_terminal(edge):
                terminal_sources.add(source_ref)

        groups = _mapping_list(plan.get("groups"))
        fan_diagram = _fan_structure_diagram(
            groups,
            edges,
            order=order,
            labels=labels,
            adjacency=adjacency,
            reverse=reverse,
            terminal_sources=terminal_sources,
        )
        if fan_diagram:
            return fan_diagram
        if all(len(targets) <= 1 for targets in adjacency.values()) and all(
            len(sources) <= 1 for sources in reverse.values()
        ):
            start_ref = next((ref for ref in order if not reverse.get(ref)), order[0])
            path, terminal = _linear_path_from(start_ref, adjacency, terminal_sources)
            return _linear_structure_diagram(path, labels, terminal)
        return _linear_structure_diagram(order, labels, order[-1] in terminal_sources)
    except Exception:
        return ""


def _ordered_declared_steps(plan: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    steps = _declared_steps(plan)
    order = plan.get("execution_order")
    if not isinstance(order, list):
        return steps
    step_by_ref = {
        str(step.get("step_ref") or "").strip(): step
        for step in steps
        if str(step.get("step_ref") or "").strip()
    }
    ordered: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for raw_ref in order:
        step_ref = str(raw_ref or "").strip()
        step = step_by_ref.get(step_ref)
        if step is not None:
            ordered.append(step)
            seen.add(step_ref)
    ordered.extend(
        step
        for step in steps
        if str(step.get("step_ref") or "").strip() not in seen
    )
    return tuple(ordered)


def _structure_step_label(repo: Path, step: Mapping[str, Any]) -> str:
    kind = _step_template_kind(str(step.get("step_template_ref") or ""))
    kind_label = _report_label_value(repo, "brick_kinds", kind, field="ko") or kind or "작업"
    lane, _lane_not_proven = _agent_lane_for_ref(_agent_object_ref_from_step(step), repo)
    lane_label = _report_label_value(repo, "lanes", lane) or lane or "담당자"
    return f"[{kind_label}·{lane_label}]"


def _report_label_value(
    repo: Path,
    section: str,
    key: str,
    *,
    field: str | None = None,
) -> str:
    key = str(key or "").strip()
    if not key:
        return ""
    label_map = _read_json_mapping(repo / "support" / "operator" / "label_map.json")
    raw_section = label_map.get(section)
    if not isinstance(raw_section, Mapping):
        return ""
    item = raw_section.get(key)
    if isinstance(item, str):
        return item
    if isinstance(item, Mapping) and field:
        value = item.get(field)
        if isinstance(value, str):
            return value
    return ""


def _link_edge_points_to_terminal(edge: Mapping[str, Any]) -> bool:
    if str(edge.get("target_step_ref") or "").strip():
        return False
    link_row = _axis_row(edge, "Link")
    target_ref = str(link_row.get("target_ref") or "").strip()
    return not target_ref or target_ref.startswith("building-boundary")


def _linear_plan_has_terminal(steps: tuple[Mapping[str, Any], ...]) -> bool:
    if not steps:
        return False
    link_row = _axis_row(steps[-1], "Link")
    target_ref = str(link_row.get("target_ref") or "").strip()
    return not target_ref or target_ref.startswith("building-boundary")


def _linear_structure_diagram(
    step_refs: Iterable[str],
    labels: Mapping[str, str],
    terminal: bool,
) -> str:
    parts = [labels[step_ref] for step_ref in step_refs if labels.get(step_ref)]
    if terminal:
        parts.append("(완료)")
    return " ──▶ ".join(parts)


def _linear_path_from(
    start_ref: str,
    adjacency: Mapping[str, list[str]],
    terminal_sources: set[str],
) -> tuple[list[str], bool]:
    path: list[str] = []
    seen: set[str] = set()
    current = start_ref
    terminal = False
    while current and current not in seen:
        path.append(current)
        seen.add(current)
        if current in terminal_sources:
            terminal = True
            break
        targets = adjacency.get(current) or []
        if len(targets) != 1:
            break
        current = targets[0]
    return path, terminal


def _fan_structure_diagram(
    groups: Iterable[Mapping[str, Any]],
    edges: Iterable[Mapping[str, Any]],
    *,
    order: list[str],
    labels: Mapping[str, str],
    adjacency: Mapping[str, list[str]],
    reverse: Mapping[str, list[str]],
    terminal_sources: set[str],
) -> str:
    edge_by_ref = {
        str(edge.get("edge_ref") or "").strip(): edge
        for edge in edges
        if str(edge.get("edge_ref") or "").strip()
    }
    fan_out_refs: list[str] = []
    fan_in_refs: list[str] = []
    for group in groups:
        role = str(group.get("group_role") or "").strip()
        member_refs = group.get("member_refs")
        if not isinstance(member_refs, list):
            continue
        refs = [str(ref or "").strip() for ref in member_refs if str(ref or "").strip()]
        if role == "fan_out" and not fan_out_refs:
            fan_out_refs = refs
        elif role == "fan_in" and not fan_in_refs:
            fan_in_refs = refs
    if not fan_out_refs or not fan_in_refs:
        return ""

    fan_out_edges = [edge_by_ref[ref] for ref in fan_out_refs if ref in edge_by_ref]
    fan_in_edges = [edge_by_ref[ref] for ref in fan_in_refs if ref in edge_by_ref]
    sources = {
        str(edge.get("source_step_ref") or "").strip()
        for edge in fan_out_edges
        if str(edge.get("source_step_ref") or "").strip()
    }
    fan_in_targets = {
        str(edge.get("target_step_ref") or "").strip()
        for edge in fan_in_edges
        if str(edge.get("target_step_ref") or "").strip()
    }
    if len(sources) != 1 or len(fan_in_targets) != 1:
        return ""
    fan_source = next(iter(sources))
    fan_in_target = next(iter(fan_in_targets))
    order_index = {step_ref: index for index, step_ref in enumerate(order)}
    branch_refs = [
        str(edge.get("target_step_ref") or "").strip()
        for edge in fan_out_edges
        if str(edge.get("target_step_ref") or "").strip()
    ]
    branch_refs = sorted(
        [ref for ref in branch_refs if labels.get(ref)],
        key=lambda ref: order_index.get(ref, len(order_index)),
    )
    if not branch_refs or not labels.get(fan_source) or not labels.get(fan_in_target):
        return ""

    prefix_refs = _linear_prefix_to(fan_source, reverse, order)
    prefix = _linear_structure_diagram(prefix_refs, labels, terminal=False)
    suffix_refs, suffix_terminal = _linear_path_from(fan_in_target, adjacency, terminal_sources)
    suffix = _linear_structure_diagram(suffix_refs, labels, suffix_terminal)
    branch_labels = [labels[ref] for ref in branch_refs]
    if len(branch_labels) > 3 or any(len(label) > 16 for label in branch_labels):
        branch_lines = [
            f"{'└' if index == len(branch_labels) - 1 else '├'}─ {label}"
            for index, label in enumerate(branch_labels)
        ]
        return "\n".join([prefix, *branch_lines, "▼", suffix])

    widths = [max(len(label), 3) for label in branch_labels]
    top = "┌" + "┼".join("─" * width for width in widths) + "┐"
    arrows = " ".join("▼".center(width) for width in widths)
    middle = " ".join(label.center(width) for label, width in zip(branch_labels, widths))
    bottom = "└" + "┼".join("─" * width for width in widths) + "┘"
    return "\n".join([prefix, top, arrows, middle, bottom, "▼", suffix])


def _linear_prefix_to(
    target_ref: str,
    reverse: Mapping[str, list[str]],
    order: list[str],
) -> list[str]:
    path = [target_ref]
    seen = {target_ref}
    current = target_ref
    while True:
        sources = reverse.get(current) or []
        if len(sources) != 1 or sources[0] in seen:
            break
        current = sources[0]
        path.insert(0, current)
        seen.add(current)
    order_index = {step_ref: index for index, step_ref in enumerate(order)}
    return sorted(path, key=lambda ref: order_index.get(ref, len(order_index)))


def _declared_plan_for_building(
    root: Path,
    building_map: Mapping[str, Any],
) -> Mapping[str, Any]:
    for path in (
        root / "work" / "declared-building-plan.json",
        root / "declared-building-plan.json",
    ):
        packet = _read_json_mapping(path)
        plan = packet.get("declared_plan_copy") if isinstance(packet.get("declared_plan_copy"), Mapping) else packet
        if _declared_steps(plan):
            return plan
    provenance = building_map.get("declaration_provenance")
    if isinstance(provenance, Mapping):
        plan = provenance.get("declared_plan_copy")
        if isinstance(plan, Mapping) and _declared_steps(plan):
            return plan
    return {}


def _declared_steps(plan: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw_steps = plan.get("steps")
    if not isinstance(raw_steps, list):
        raw_steps = plan.get("brick_steps")
    if not isinstance(raw_steps, list):
        return ()
    return tuple(step for step in raw_steps if isinstance(step, Mapping))


def _current_work_brick_ref(
    building_map: Mapping[str, Any],
    frontier_kind: str,
    current_brick_ref: str,
) -> str:
    edges = _mapping_list(building_map.get("link_edges"))
    if edges and frontier_kind == "complete":
        value = edges[-1].get("source_brick_instance_ref")
        if isinstance(value, str) and value.strip():
            return value.strip()
    if current_brick_ref.strip():
        return current_brick_ref.strip()
    if edges:
        value = edges[-1].get("source_brick_instance_ref")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _declared_step_for_brick_ref(
    plan: Mapping[str, Any],
    brick_ref: str,
) -> Mapping[str, Any] | None:
    if not brick_ref:
        return None
    for step in _declared_steps(plan):
        brick_row = _axis_row(step, "Brick")
        if str(brick_row.get("brick_instance_ref") or "").strip() == brick_ref:
            return step
    return None


def _declared_step_for_step_ref(
    plan: Mapping[str, Any],
    step_ref: str,
) -> Mapping[str, Any] | None:
    if not step_ref:
        return None
    for step in _declared_steps(plan):
        if str(step.get("step_ref") or "").strip() == step_ref:
            return step
    return None


def _axis_row(step: Mapping[str, Any], axis: str) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, Mapping) and str(row.get("axis") or "").strip() == axis:
            return row
    return {}


def _step_template_kind(step_template_ref: str) -> str:
    prefix = "building-step-template:"
    return step_template_ref.removeprefix(prefix).strip() if step_template_ref.startswith(prefix) else ""


def _agent_object_ref_from_step(step: Mapping[str, Any]) -> str:
    agent_row = _axis_row(step, "Agent")
    return str(agent_row.get("agent_object_ref") or "").strip()


def _agent_lane_for_ref(agent_object_ref: str, repo: Path) -> tuple[str, tuple[str, ...]]:
    if not agent_object_ref:
        return "", ("declared Agent Object ref for notification lane was not resolved",)
    try:
        packet = resolve_agent_object(agent_object_ref, repo_root=repo)
    except AgentResourceError as exc:
        return "", (f"Agent Object lane projection unresolved: {exc}",)
    agent_object = packet.get("agent_object")
    if isinstance(agent_object, Mapping):
        lane = agent_object.get("lane")
        if isinstance(lane, str) and lane.strip():
            return lane.strip(), ()
    return "", ("Agent Object lane projection returned no lane",)


def _human_title(root: Path, fallback: str) -> str:
    title_path = root / "work" / "task.md"
    try:
        first_line = title_path.read_text(encoding="utf-8").splitlines()[0]
    except (IndexError, OSError):
        return fallback
    title = first_line.strip()
    while title.startswith("#"):
        title = title[1:].strip()
    if title == "Building Task Source Evidence":
        return fallback
    return title or fallback


def _report_event_mode(value: Any) -> str:
    mode = str(value or "basic").strip()
    if mode not in REPORT_EVENT_MODES:
        raise ValueError(f"unadmitted report event mode: {mode}")
    return mode


def _report_event_grain(value: Any) -> str:
    raw = value if value is not None else os.environ.get(REPORT_GRAIN_ENV)
    grain = str(raw or "brick").strip().lower()
    if grain not in REPORT_EVENT_GRAINS:
        raise ValueError(
            f"{REPORT_GRAIN_ENV} / report_event_policy.grain must be 'building' or 'brick'"
        )
    return grain


def _report_event_context(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("event_context must be a mapping")
    forbidden = sorted(set(_nested_keys(value)) & FORBIDDEN_REPORT_PACKET_FIELDS)
    if forbidden:
        raise ValueError(f"event_context includes forbidden field(s): {forbidden}")
    cleaned: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip()
        if not key:
            continue
        if raw_value is None:
            continue
        if isinstance(raw_value, (str, int, bool)):
            cleaned[key] = raw_value
            continue
        if isinstance(raw_value, list) and all(
            isinstance(item, (str, int, bool)) for item in raw_value
        ):
            cleaned[key] = list(raw_value)
    return cleaned


def _step_ref_from_step_output_ref(step_output_ref: str) -> str:
    if not step_output_ref:
        return ""
    parent_name = Path(step_output_ref).parent.name
    if "-attempt-" in parent_name:
        return parent_name.rsplit("-attempt-", 1)[0]
    return parent_name


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

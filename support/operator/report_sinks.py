"""One-shot report sink fan-out for support-only report packets."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INBOX_ROOT = REPO_ROOT / "project" / "brick-protocol" / "status" / "inbox"
LOCAL_INBOX_SINK_REF = "report-sink:local-inbox"
OPERATOR_WAKE_LOCAL_SINK_REF = "report-sink:operator-wake-local"
SLACK_SINK_REF = "report-sink:slack"
SLACK_BOT_TOKEN_ENV = "BRICK_REPORT_SLACK_BOT_TOKEN"
SLACK_CHANNEL_ID_ENV = "BRICK_REPORT_SLACK_CHANNEL_ID"
SLACK_API_URL = "https://slack.com/api/chat.postMessage"
DASHBOARD_SINK_REF = "report-sink:dashboard"
DASHBOARD_INGEST_URL_ENV = "BRICK_DASHBOARD_INGEST_URL"
DASHBOARD_INGEST_SECRET_ENV = "BRICK_DASHBOARD_INGEST_SECRET"
ADMITTED_SINK_REFS = frozenset(
    {LOCAL_INBOX_SINK_REF, OPERATOR_WAKE_LOCAL_SINK_REF, SLACK_SINK_REF, DASHBOARD_SINK_REF}
)
OPERATOR_WAKE_TARGET_KINDS = frozenset({"operator_wake_local"})
OPERATOR_WAKE_DELIVERY_MODES = frozenset({"local_projection"})
OPERATOR_WAKE_SIDE_EFFECT_STATES = frozenset({"none"})
SLACK_REQUIRED_PACKET_FIELDS = (
    "report_id",
    "report_kind",
    "observed_board_state",
    "trigger_event_ref",
    "frontier_ref",
    "evidence_root_refs",
    "evidence_refs_present",
    "sink_refs",
    "source_truth",
    "not_proven",
    "proof_limits",
)
OPERATOR_WAKE_TARGET_REQUIRED_FIELDS = (
    "target_ref",
    "target_kind",
    "sink_ref",
    "delivery_mode",
    "side_effect_state",
    "proof_limits",
    "not_proven",
)
OPERATOR_WAKE_TARGET_ALLOWED_FIELDS = frozenset(OPERATOR_WAKE_TARGET_REQUIRED_FIELDS)
SINK_FORBIDDEN_PACKET_FIELDS = frozenset(
    {
        "access_token",
        "success",
        "failure",
        "approved",
        "auth",
        "auth_body",
        "credential",
        "credential_body",
        "quality",
        "complete",
        "complete_as_movement",
        "movement_choice",
        "target_choice",
        "route_target",
        "adopted_by_reporter",
        "authorization",
        "bearer_token",
        "bot_token",
        "channel",
        "channel_id",
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
SINK_PROOF_LIMITS: tuple[str, ...] = (
    "support projection sink only",
    "writes local status inbox packets only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route input",
)
DRY_RUN_SINK_PROOF_LIMITS: tuple[str, ...] = (
    "support projection sink dry-run only",
    "validates admitted sink refs without writing local status inbox packets",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route input",
    "not provider delivery",
)
DRY_RUN_SINK_NOT_PROVEN: tuple[str, ...] = (
    "delivery reliability",
    "reader noticed packet",
    "operator noticed wake packet",
    "real provider thread wake behavior",
    "external notification behavior",
    "stale evidence race behavior",
)
SLACK_DRY_RUN_PROOF_LIMITS: tuple[str, ...] = (
    "Slack sink dry-run only",
    "validates Slack packet shape without reading Slack credentials",
    "does not call Slack",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route input",
    "not scheduler / queue / retry runtime",
)
SLACK_REAL_DELIVERY_PROOF_LIMITS: tuple[str, ...] = (
    "Slack sink support observation only",
    "reads Slack credential values from environment only when explicitly allowed",
    "records only environment presence and status classes",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route input",
    "not scheduler / queue / retry runtime",
)
DASHBOARD_DRY_RUN_PROOF_LIMITS: tuple[str, ...] = (
    "dashboard sink dry-run only",
    "validates report packet without computing or posting a delta/seed projection",
    "does not call the dashboard server",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route input",
)
SLACK_NOT_PROVEN: tuple[str, ...] = (
    "long-term Slack delivery reliability",
    "reader noticed Slack message",
    "network/provider reliability",
    "Slack credential correctness",
    "production readiness",
)
DASHBOARD_DELTA_REAL_DELIVERY_PROOF_LIMITS: tuple[str, ...] = (
    "dashboard sink support observation only",
    "posts a read-side single-building delta projection to the dashboard ingest endpoint",
    "single-building delta event (subset of the full snapshot shape), not a full board snapshot",
    "reads dashboard endpoint url/secret from environment only when explicitly allowed",
    "records only environment presence and status classes",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route input",
)
DASHBOARD_SEED_REAL_DELIVERY_PROOF_LIMITS: tuple[str, ...] = (
    "dashboard sink support observation only",
    "posts a read-side full-snapshot SEED projection to the dashboard ingest endpoint",
    "initial connect-time seed only; per-building deltas carry incremental updates",
    "reads dashboard endpoint url/secret from environment only when explicitly allowed",
    "records only environment presence and status classes",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route input",
)
DASHBOARD_SINK_NOT_PROVEN: tuple[str, ...] = (
    "dashboard delivery reliability",
    "reader noticed dashboard update",
    "network/provider reliability",
    "dashboard credential correctness",
    "real-time freshness beyond post moment",
    "production readiness",
)
OPERATOR_WAKE_PROOF_LIMITS: tuple[str, ...] = (
    "provider-neutral operator wake projection only",
    "writes local status inbox wake packets only",
    "not provider mutation",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not route input",
    "not automatic resume",
)
OPERATOR_WAKE_NOT_PROVEN: tuple[str, ...] = (
    "operator noticed wake packet",
    "delivery reliability",
    "real provider thread wake behavior",
    "external side effect behavior",
    "stale evidence race behavior",
)


@dataclass(frozen=True)
class ReportSinkObservation:
    """Support-only observation of one sink write."""

    sink_ref: str
    delivered: bool
    packet_ref: str
    written_path: str
    proof_limits: tuple[str, ...]
    not_proven: tuple[str, ...]
    delivery_status_class: str = ""
    provider_response_status_class: str = ""
    environment_presence: Mapping[str, str] | None = None
    dry_run_validated: bool = False

    def to_packet(self) -> Mapping[str, Any]:
        packet: dict[str, Any] = {
            "sink_ref": self.sink_ref,
            "delivered": self.delivered,
            "packet_ref": self.packet_ref,
            "written_path": self.written_path,
            "proof_limits": list(self.proof_limits),
            "not_proven": list(self.not_proven),
        }
        if self.delivery_status_class:
            packet["delivery_status_class"] = self.delivery_status_class
        if self.provider_response_status_class:
            packet["provider_response_status_class"] = self.provider_response_status_class
        if self.environment_presence is not None:
            packet["environment_presence"] = dict(self.environment_presence)
        if self.dry_run_validated:
            packet["dry_run_validated"] = True
        return packet


def deliver_report_packet(
    packet: Mapping[str, Any],
    *,
    sink_refs: Iterable[str] | None = None,
    repo_root: Path | str = REPO_ROOT,
    inbox_root: Path | str | None = None,
    overwrite_existing: bool = False,
    allow_real_slack_delivery: bool = False,
    slack_timeout_seconds: float = 10.0,
    allow_real_dashboard_delivery: bool = False,
    dashboard_timeout_seconds: float = 10.0,
) -> tuple[ReportSinkObservation, ...]:
    """Fan out one already-rendered report packet to admitted sinks."""

    repo = Path(repo_root).resolve()
    _validate_packet_for_sink(packet)
    refs = _sink_refs(packet, sink_refs)
    observations: list[ReportSinkObservation] = []
    for sink_ref in refs:
        if sink_ref == LOCAL_INBOX_SINK_REF:
            observations.append(
                write_local_inbox_packet(
                    packet,
                    repo_root=repo,
                    inbox_root=inbox_root,
                    overwrite_existing=overwrite_existing,
                )
            )
            continue
        if sink_ref == OPERATOR_WAKE_LOCAL_SINK_REF:
            observations.append(
                write_operator_wake_packet(
                    packet,
                    repo_root=repo,
                    inbox_root=inbox_root,
                    overwrite_existing=overwrite_existing,
                )
            )
            continue
        if sink_ref == SLACK_SINK_REF:
            observations.append(
                send_slack_report_packet(
                    packet,
                    allow_real_delivery=allow_real_slack_delivery,
                    timeout_seconds=slack_timeout_seconds,
                )
            )
            continue
        if sink_ref == DASHBOARD_SINK_REF:
            # Fan-out delivers the connect-time SEED (full snapshot). Per-building
            # delta events are published directly via send_dashboard_building_delta
            # by the (separate) per-event trigger wiring.
            building_id = str(packet.get("building_id") or "").strip()
            if building_id:
                # PROJECT-0 S4-B: an OPTIONAL packet project_ref narrows the
                # delta to one vessel (building_id uniqueness is per-vessel);
                # without it an id living in 2+ vessels fails closed downstream.
                packet_project_ref = str(packet.get("project_ref") or "").strip() or None
                observations.append(
                    send_dashboard_building_delta(
                        building_id,
                        project_ref=packet_project_ref,
                        repo_root=repo,
                        allow_real_delivery=allow_real_dashboard_delivery,
                        timeout_seconds=dashboard_timeout_seconds,
                    )
                )
            else:
                observations.append(
                    send_dashboard_seed(
                        repo_root=repo,
                        allow_real_delivery=allow_real_dashboard_delivery,
                        timeout_seconds=dashboard_timeout_seconds,
                    )
                )
            continue
        raise ValueError(f"unadmitted report sink ref: {sink_ref}")
    return tuple(observations)


def dry_run_report_packet(
    packet: Mapping[str, Any],
    *,
    sink_refs: Iterable[str] | None = None,
    repo_root: Path | str = REPO_ROOT,
) -> tuple[ReportSinkObservation, ...]:
    """Validate sink fan-out without writing projection packets."""

    repo = Path(repo_root).resolve()
    if not repo.is_dir():
        raise ValueError("repo_root must be a directory")
    _validate_packet_for_sink(packet)
    refs = _sink_refs(packet, sink_refs)
    packet_ref = _required_text(packet.get("report_id"), "report_id")
    observations: list[ReportSinkObservation] = []
    for sink_ref in refs:
        if sink_ref == OPERATOR_WAKE_LOCAL_SINK_REF:
            _operator_wake_targets(packet)
        if sink_ref == SLACK_SINK_REF:
            _validate_slack_packet(packet)
            observations.append(
                ReportSinkObservation(
                    sink_ref=sink_ref,
                    delivered=False,
                    packet_ref=packet_ref,
                    written_path="",
                    proof_limits=_merge_texts(DRY_RUN_SINK_PROOF_LIMITS, SLACK_DRY_RUN_PROOF_LIMITS),
                    not_proven=_merge_texts(DRY_RUN_SINK_NOT_PROVEN, SLACK_NOT_PROVEN),
                    delivery_status_class="dry_run_validated",
                    provider_response_status_class="not_attempted",
                    dry_run_validated=True,
                )
            )
            continue
        if sink_ref == DASHBOARD_SINK_REF:
            observations.append(
                ReportSinkObservation(
                    sink_ref=sink_ref,
                    delivered=False,
                    packet_ref=packet_ref,
                    written_path="",
                    proof_limits=_merge_texts(DRY_RUN_SINK_PROOF_LIMITS, DASHBOARD_DRY_RUN_PROOF_LIMITS),
                    not_proven=_merge_texts(DRY_RUN_SINK_NOT_PROVEN, DASHBOARD_SINK_NOT_PROVEN),
                    delivery_status_class="dry_run_validated",
                    provider_response_status_class="not_attempted",
                    dry_run_validated=True,
                )
            )
            continue
        observations.append(
            ReportSinkObservation(
                sink_ref=sink_ref,
                delivered=False,
                packet_ref=packet_ref,
                written_path="",
                proof_limits=DRY_RUN_SINK_PROOF_LIMITS,
                not_proven=DRY_RUN_SINK_NOT_PROVEN,
            )
        )
    return tuple(observations)


def send_slack_report_packet(
    packet: Mapping[str, Any],
    *,
    allow_real_delivery: bool = False,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float = 10.0,
) -> ReportSinkObservation:
    """Post one report packet to Slack only after explicit caller admission."""

    _validate_packet_for_sink(packet)
    _validate_slack_packet(packet)
    packet_ref = _required_text(packet.get("report_id"), "report_id")
    if not allow_real_delivery:
        raise ValueError("real Slack delivery requires allow_real_slack_delivery=True")

    env_map = os.environ if env is None else env
    environment_presence = _slack_environment_presence(env_map)
    bot_token = str(env_map.get(SLACK_BOT_TOKEN_ENV) or "")
    channel_id = str(env_map.get(SLACK_CHANNEL_ID_ENV) or "")
    if not bot_token or not channel_id:
        return ReportSinkObservation(
            sink_ref=SLACK_SINK_REF,
            delivered=False,
            packet_ref=packet_ref,
            written_path="",
            proof_limits=SLACK_REAL_DELIVERY_PROOF_LIMITS,
            not_proven=_merge_texts(SLACK_NOT_PROVEN, ("Slack delivery not attempted",)),
            delivery_status_class="not_attempted_missing_environment",
            provider_response_status_class="not_attempted",
            environment_presence=environment_presence,
        )

    body = json.dumps(
        {"channel": channel_id, "text": _slack_message_text(packet)},
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        SLACK_API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_status = int(response.status)
            response_body = response.read(65536)
    except urllib.error.HTTPError as exc:
        response_status = int(exc.code)
        response_body = exc.read(65536)
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        return ReportSinkObservation(
            sink_ref=SLACK_SINK_REF,
            delivered=False,
            packet_ref=packet_ref,
            written_path="",
            proof_limits=SLACK_REAL_DELIVERY_PROOF_LIMITS,
            not_proven=_merge_texts(SLACK_NOT_PROVEN, ("Slack network/provider status remains not_proven",)),
            delivery_status_class="network_exception_observed",
            provider_response_status_class=exc.__class__.__name__,
            environment_presence=environment_presence,
        )

    http_status_class = _http_status_class(response_status)
    provider_status_class, provider_ok = _slack_provider_status_class(response_body)
    return ReportSinkObservation(
        sink_ref=SLACK_SINK_REF,
        delivered=http_status_class == "http_2xx" and provider_ok is True,
        packet_ref=packet_ref,
        written_path="",
        proof_limits=SLACK_REAL_DELIVERY_PROOF_LIMITS,
        not_proven=SLACK_NOT_PROVEN,
        delivery_status_class=http_status_class,
        provider_response_status_class=provider_status_class,
        environment_presence=environment_presence,
    )


def send_dashboard_building_delta(
    building_id: str,
    *,
    project_ref: str | None = None,
    repo_root: Path | str = REPO_ROOT,
    allow_real_delivery: bool = False,
    stale_days: int | None = None,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float = 10.0,
) -> ReportSinkObservation:
    """Project ONE building and POST it as a delta event to the dashboard ingest endpoint.

    EVENT-DELTA publisher: instead of pushing the whole board snapshot on every
    change, this posts a single building's delta (a strict subset of the snapshot
    shape) as the building changes. The dashboard splices the delta in.

    Same discipline as the Slack sink: GATED (no delivery without explicit
    ``allow_real_delivery``), env-ONLY creds (url/secret read from the
    environment only when allowed; we record only presence + status classes,
    never the secret or the body).
    """

    if not isinstance(building_id, str) or not building_id.strip():
        raise ValueError("building_id must be a non-empty string")
    packet_ref = building_id.strip()
    if not allow_real_delivery:
        raise ValueError("real dashboard delivery requires allow_real_delivery=True")

    env_map = os.environ if env is None else env
    environment_presence = _dashboard_environment_presence(env_map)
    url = str(env_map.get(DASHBOARD_INGEST_URL_ENV) or "")
    secret = str(env_map.get(DASHBOARD_INGEST_SECRET_ENV) or "")
    if not url or not secret:
        return ReportSinkObservation(
            sink_ref=DASHBOARD_SINK_REF,
            delivered=False,
            packet_ref=packet_ref,
            written_path="",
            proof_limits=DASHBOARD_DELTA_REAL_DELIVERY_PROOF_LIMITS,
            not_proven=_merge_texts(DASHBOARD_SINK_NOT_PROVEN, ("dashboard delivery not attempted",)),
            delivery_status_class="not_attempted_missing_environment",
            provider_response_status_class="not_attempted",
            environment_presence=environment_presence,
        )

    # delta 는 한 빌딩만 투영한 읽기-side projection(비밀 없음, source_truth false).
    from brick_protocol.support.operator.dashboard_export import dashboard_building_delta

    kwargs: dict[str, Any] = {"repo_root": repo_root}
    if project_ref is not None:
        kwargs["project_ref"] = project_ref
    if stale_days is not None:
        kwargs["stale_days"] = stale_days
    delta = dashboard_building_delta(packet_ref, **kwargs)
    if delta.get("source_truth") is not False:
        raise ValueError("dashboard delta must declare source_truth false")
    if delta.get("delta_kind") != "building":
        raise ValueError("dashboard delta must declare delta_kind building")
    return _post_dashboard_projection(
        delta,
        url=url,
        secret=secret,
        packet_ref=packet_ref,
        proof_limits=DASHBOARD_DELTA_REAL_DELIVERY_PROOF_LIMITS,
        environment_presence=environment_presence,
        timeout_seconds=timeout_seconds,
    )


def send_dashboard_seed(
    *,
    repo_root: Path | str = REPO_ROOT,
    allow_real_delivery: bool = False,
    stale_days: int | None = None,
    env: Mapping[str, str] | None = None,
    timeout_seconds: float = 10.0,
) -> ReportSinkObservation:
    """Compute the full read-side snapshot and POST it once as a connect-time SEED.

    EVENT-DELTA model: the dashboard seeds its state with this full snapshot on
    connect, then receives per-building deltas via ``send_dashboard_building_delta``.

    Same discipline as the Slack sink: GATED, env-ONLY creds, status-class
    observation only.
    """

    packet_ref = "dashboard-seed"
    if not allow_real_delivery:
        raise ValueError("real dashboard delivery requires allow_real_delivery=True")

    env_map = os.environ if env is None else env
    environment_presence = _dashboard_environment_presence(env_map)
    url = str(env_map.get(DASHBOARD_INGEST_URL_ENV) or "")
    secret = str(env_map.get(DASHBOARD_INGEST_SECRET_ENV) or "")
    if not url or not secret:
        return ReportSinkObservation(
            sink_ref=DASHBOARD_SINK_REF,
            delivered=False,
            packet_ref=packet_ref,
            written_path="",
            proof_limits=DASHBOARD_SEED_REAL_DELIVERY_PROOF_LIMITS,
            not_proven=_merge_texts(DASHBOARD_SINK_NOT_PROVEN, ("dashboard delivery not attempted",)),
            delivery_status_class="not_attempted_missing_environment",
            provider_response_status_class="not_attempted",
            environment_presence=environment_presence,
        )

    # snapshot 은 읽기-side 투영(비밀 없음, source_truth false). 초기 connect 시드.
    from brick_protocol.support.operator.dashboard_export import dashboard_export_packet

    kwargs: dict[str, Any] = {"repo_root": repo_root}
    if stale_days is not None:
        kwargs["stale_days"] = stale_days
    snapshot = dashboard_export_packet(**kwargs)
    if snapshot.get("source_truth") is not False:
        raise ValueError("dashboard snapshot must declare source_truth false")
    return _post_dashboard_projection(
        snapshot,
        url=url,
        secret=secret,
        packet_ref=packet_ref,
        proof_limits=DASHBOARD_SEED_REAL_DELIVERY_PROOF_LIMITS,
        environment_presence=environment_presence,
        timeout_seconds=timeout_seconds,
    )


def _post_dashboard_projection(
    projection: Mapping[str, Any],
    *,
    url: str,
    secret: str,
    packet_ref: str,
    proof_limits: tuple[str, ...],
    environment_presence: Mapping[str, str],
    timeout_seconds: float,
) -> ReportSinkObservation:
    """POST one read-side dashboard projection (delta or seed); record status class only.

    Mirrors the Slack sink transport discipline: urllib only, secret carried in a
    header (never logged), only HTTP status CLASS recorded (never the body or the
    secret).
    """

    body = json.dumps(projection, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "x-ingest-secret": secret,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_status = int(response.status)
            response.read(4096)
    except urllib.error.HTTPError as exc:
        response_status = int(exc.code)
        exc.read(4096)
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        return ReportSinkObservation(
            sink_ref=DASHBOARD_SINK_REF,
            delivered=False,
            packet_ref=packet_ref,
            written_path="",
            proof_limits=proof_limits,
            not_proven=_merge_texts(
                DASHBOARD_SINK_NOT_PROVEN,
                ("dashboard network/provider status remains not_proven",),
            ),
            delivery_status_class="network_exception_observed",
            provider_response_status_class=exc.__class__.__name__,
            environment_presence=environment_presence,
        )

    http_status_class = _http_status_class(response_status)
    return ReportSinkObservation(
        sink_ref=DASHBOARD_SINK_REF,
        delivered=http_status_class == "http_2xx",
        packet_ref=packet_ref,
        written_path="",
        proof_limits=proof_limits,
        not_proven=DASHBOARD_SINK_NOT_PROVEN,
        delivery_status_class=http_status_class,
        provider_response_status_class=http_status_class,
        environment_presence=environment_presence,
    )


def _dashboard_environment_presence(env: Mapping[str, str]) -> Mapping[str, str]:
    return {
        DASHBOARD_INGEST_URL_ENV: "present" if env.get(DASHBOARD_INGEST_URL_ENV) else "absent",
        DASHBOARD_INGEST_SECRET_ENV: "present" if env.get(DASHBOARD_INGEST_SECRET_ENV) else "absent",
    }


def validate_dashboard_delivery_environment(
    env: Mapping[str, str] | None = None,
) -> Mapping[str, str]:
    """Return dashboard ingest environment variable presence only, never values."""

    return _dashboard_environment_presence(os.environ if env is None else env)


def validate_slack_delivery_environment(
    env: Mapping[str, str] | None = None,
) -> Mapping[str, str]:
    """Return Slack environment variable presence only, never values."""

    return _slack_environment_presence(os.environ if env is None else env)


def write_local_inbox_packet(
    packet: Mapping[str, Any],
    *,
    repo_root: Path | str = REPO_ROOT,
    inbox_root: Path | str | None = None,
    overwrite_existing: bool = False,
) -> ReportSinkObservation:
    """Write a projection packet under the local status inbox."""

    repo = Path(repo_root).resolve()
    _validate_packet_for_sink(packet)
    inbox = (
        _repo_path(repo, inbox_root)
        if inbox_root is not None
        else DEFAULT_INBOX_ROOT
        if repo == REPO_ROOT
        else repo / "project" / "brick-protocol" / "status" / "inbox"
    )
    expected_root = repo / "project" / "brick-protocol" / "status" / "inbox"
    if inbox.resolve() != expected_root.resolve():
        raise ValueError("local inbox sink must write under project/brick-protocol/status/inbox")
    report_id = _path_segment(_required_text(packet.get("report_id"), "report_id"))
    packet_ref = _required_text(packet.get("report_id"), "report_id")
    inbox.mkdir(parents=True, exist_ok=True)
    output = inbox / f"{report_id}.json"
    if output.exists() and not overwrite_existing:
        raise FileExistsError(f"local inbox packet already exists: {_rel(repo, output)}")
    output.write_text(
        json.dumps(dict(packet), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ReportSinkObservation(
        sink_ref=LOCAL_INBOX_SINK_REF,
        delivered=True,
        packet_ref=packet_ref,
        written_path=_rel(repo, output),
        proof_limits=SINK_PROOF_LIMITS,
        not_proven=(
            "reader noticed packet",
            "delivery reliability",
            "stale evidence race behavior",
        ),
    )


def write_operator_wake_packet(
    packet: Mapping[str, Any],
    *,
    repo_root: Path | str = REPO_ROOT,
    inbox_root: Path | str | None = None,
    overwrite_existing: bool = False,
) -> ReportSinkObservation:
    """Write a provider-neutral local wake projection under the status inbox."""

    repo = Path(repo_root).resolve()
    _validate_packet_for_sink(packet)
    targets = _operator_wake_targets(packet)
    inbox = (
        _repo_path(repo, inbox_root)
        if inbox_root is not None
        else DEFAULT_INBOX_ROOT
        if repo == REPO_ROOT
        else repo / "project" / "brick-protocol" / "status" / "inbox"
    )
    expected_root = repo / "project" / "brick-protocol" / "status" / "inbox"
    if inbox.resolve() != expected_root.resolve():
        raise ValueError("operator wake sink must write under project/brick-protocol/status/inbox")
    report_id = _required_text(packet.get("report_id"), "report_id")
    wake_packet_id = f"{report_id}-operator-wake"
    inbox.mkdir(parents=True, exist_ok=True)
    output = inbox / f"{_path_segment(wake_packet_id)}.json"
    if output.exists() and not overwrite_existing:
        raise FileExistsError(f"operator wake packet already exists: {_rel(repo, output)}")
    wake_packet = {
        "wake_packet_id": wake_packet_id,
        "report_id": report_id,
        "report_kind": _required_text(packet.get("report_kind"), "report_kind"),
        "building_id": str(packet.get("building_id") or ""),
        "portfolio_id": str(packet.get("portfolio_id") or ""),
        "observed_board_state": str(packet.get("observed_board_state") or ""),
        "frontier_ref": str(packet.get("frontier_ref") or ""),
        "required_disposition_owner": str(packet.get("required_disposition_owner") or ""),
        "evidence_root_refs": list(_string_list(packet.get("evidence_root_refs"), "evidence_root_refs")),
        "operator_wake_targets": [dict(target) for target in targets],
        "source_truth": False,
        "proof_limits": list(OPERATOR_WAKE_PROOF_LIMITS),
        "not_proven": list(OPERATOR_WAKE_NOT_PROVEN),
    }
    _validate_packet_for_sink(wake_packet)
    output.write_text(
        json.dumps(wake_packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ReportSinkObservation(
        sink_ref=OPERATOR_WAKE_LOCAL_SINK_REF,
        delivered=True,
        packet_ref=wake_packet_id,
        written_path=_rel(repo, output),
        proof_limits=OPERATOR_WAKE_PROOF_LIMITS,
        not_proven=OPERATOR_WAKE_NOT_PROVEN,
    )


def validate_operator_wake_targets(value: Any) -> tuple[Mapping[str, Any], ...]:
    """Validate provider-neutral operator wake target declarations."""

    return _operator_wake_targets({"operator_wake_targets": value})


def _sink_refs(packet: Mapping[str, Any], refs: Iterable[str] | None) -> tuple[str, ...]:
    raw_refs = refs if refs is not None else packet.get("sink_refs", (LOCAL_INBOX_SINK_REF,))
    if isinstance(raw_refs, str):
        values = (raw_refs,)
    else:
        values = tuple(str(item).strip() for item in raw_refs or ())
    if not values:
        values = (LOCAL_INBOX_SINK_REF,)
    unadmitted = sorted(set(values) - ADMITTED_SINK_REFS)
    if unadmitted:
        raise ValueError(f"unadmitted report sink ref(s): {unadmitted}")
    return values


def _validate_packet_for_sink(packet: Mapping[str, Any]) -> None:
    if not isinstance(packet, Mapping):
        raise ValueError("report sink packet must be a mapping")
    if packet.get("source_truth") is not False:
        raise ValueError("report sink packet source_truth must be false")
    forbidden = sorted(set(_nested_keys(packet)) & SINK_FORBIDDEN_PACKET_FIELDS)
    if forbidden:
        raise ValueError(f"report sink packet includes forbidden field(s): {forbidden}")
    if "operator_wake_targets" in packet:
        _operator_wake_targets(packet)


def _validate_slack_packet(packet: Mapping[str, Any]) -> None:
    missing = [field for field in SLACK_REQUIRED_PACKET_FIELDS if field not in packet]
    if missing:
        raise ValueError(f"Slack report packet missing required field(s): {missing}")
    _required_text(packet.get("report_id"), "report_id")
    _required_text(packet.get("report_kind"), "report_kind")
    _required_text(packet.get("observed_board_state"), "observed_board_state")
    _required_text(packet.get("trigger_event_ref"), "trigger_event_ref")
    _required_text(packet.get("frontier_ref"), "frontier_ref")
    _string_list(packet.get("evidence_root_refs"), "evidence_root_refs")
    _string_list(packet.get("sink_refs"), "sink_refs")
    _string_list(packet.get("not_proven"), "not_proven")
    _string_list(packet.get("proof_limits"), "proof_limits")
    if not isinstance(packet.get("evidence_refs_present"), bool):
        raise ValueError("evidence_refs_present must be a boolean")


def _operator_wake_targets(packet: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw_targets = packet.get("operator_wake_targets")
    if raw_targets is None:
        return (_default_operator_wake_target(),)
    if not isinstance(raw_targets, list):
        raise ValueError("operator_wake_targets must be a list")
    targets: list[Mapping[str, Any]] = []
    for index, raw_target in enumerate(raw_targets):
        if not isinstance(raw_target, Mapping):
            raise ValueError(f"operator_wake_targets[{index}] must be a mapping")
        forbidden = sorted(set(_nested_keys(raw_target)) & SINK_FORBIDDEN_PACKET_FIELDS)
        if forbidden:
            raise ValueError(
                f"operator_wake_targets[{index}] includes forbidden field(s): {forbidden}"
            )
        extra = sorted(set(str(key) for key in raw_target) - OPERATOR_WAKE_TARGET_ALLOWED_FIELDS)
        if extra:
            raise ValueError(f"operator_wake_targets[{index}] includes unadmitted field(s): {extra}")
        missing = [field for field in OPERATOR_WAKE_TARGET_REQUIRED_FIELDS if field not in raw_target]
        if missing:
            raise ValueError(f"operator_wake_targets[{index}] missing required field(s): {missing}")
        target_ref = _required_text(raw_target.get("target_ref"), f"operator_wake_targets[{index}].target_ref")
        target_kind = _required_text(raw_target.get("target_kind"), f"operator_wake_targets[{index}].target_kind")
        sink_ref = _required_text(raw_target.get("sink_ref"), f"operator_wake_targets[{index}].sink_ref")
        delivery_mode = _required_text(
            raw_target.get("delivery_mode"),
            f"operator_wake_targets[{index}].delivery_mode",
        )
        side_effect_state = _required_text(
            raw_target.get("side_effect_state"),
            f"operator_wake_targets[{index}].side_effect_state",
        )
        if target_kind not in OPERATOR_WAKE_TARGET_KINDS:
            raise ValueError(f"operator_wake_targets[{index}].target_kind is not admitted")
        if sink_ref != OPERATOR_WAKE_LOCAL_SINK_REF:
            raise ValueError(f"operator_wake_targets[{index}].sink_ref is not admitted for wake")
        if delivery_mode not in OPERATOR_WAKE_DELIVERY_MODES:
            raise ValueError(f"operator_wake_targets[{index}].delivery_mode is not admitted")
        if side_effect_state not in OPERATOR_WAKE_SIDE_EFFECT_STATES:
            raise ValueError(f"operator_wake_targets[{index}].side_effect_state is not admitted")
        targets.append(
            {
                "target_ref": target_ref,
                "target_kind": target_kind,
                "sink_ref": sink_ref,
                "delivery_mode": delivery_mode,
                "side_effect_state": side_effect_state,
                "proof_limits": list(_string_list(raw_target.get("proof_limits"), f"operator_wake_targets[{index}].proof_limits")),
                "not_proven": list(_string_list(raw_target.get("not_proven"), f"operator_wake_targets[{index}].not_proven")),
            }
        )
    return tuple(targets)


def _default_operator_wake_target() -> Mapping[str, Any]:
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


def _string_list(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of strings")
    return tuple(item.strip() for item in value if item.strip())


def _slack_environment_presence(env: Mapping[str, str]) -> Mapping[str, str]:
    return {
        SLACK_BOT_TOKEN_ENV: "present" if env.get(SLACK_BOT_TOKEN_ENV) else "absent",
        SLACK_CHANNEL_ID_ENV: "present" if env.get(SLACK_CHANNEL_ID_ENV) else "absent",
    }


def _slack_message_text(packet: Mapping[str, Any]) -> str:
    source_ref = str(packet.get("building_id") or packet.get("portfolio_id") or "").strip()
    if not source_ref:
        source_ref = _required_text(packet.get("report_id"), "report_id")
    event_label = _slack_event_label(packet)
    brick_line = _slack_brick_line(packet, source_ref)
    agent_line = _slack_agent_line(packet)
    link_line = _slack_link_line(packet)
    return "\n".join(
        (
            "브릭 빌딩 알림",
            f"상태: {event_label}",
            f"빌딩: {source_ref}",
            f"Brick: {brick_line}",
            f"Agent: {agent_line}",
            f"Link: {link_line}",
            "한계: support 알림이며 source truth / 성공판정 / 품질판정 / Movement 권한이 아님",
        )
    )


def _slack_event_label(packet: Mapping[str, Any]) -> str:
    trigger = str(packet.get("trigger_event_ref") or "")
    if "building_started" in trigger:
        return "시작"
    if "intervention_required" in trigger:
        return "개입 필요"
    if "building_finished" in trigger:
        return "종료"
    state = str(packet.get("observed_board_state") or "")
    if state == "observed_started":
        return "시작"
    if state in {"observed_paused", "observed_human_gate", "needs_disposition"}:
        return "개입 필요"
    if state == "observed_closed_boundary":
        return "종료"
    return "상태 관찰"


def _slack_brick_line(packet: Mapping[str, Any], source_ref: str) -> str:
    current_brick = str(packet.get("current_brick_ref") or "").strip()
    if current_brick:
        return current_brick
    return source_ref


def _slack_agent_line(packet: Mapping[str, Any]) -> str:
    last_completed = str(packet.get("last_completed_step_ref") or "").strip()
    if last_completed:
        return f"마지막 완료 step {last_completed}"
    return "아직 완료 step 없음"


def _slack_link_line(packet: Mapping[str, Any]) -> str:
    state = str(packet.get("observed_board_state") or "").strip()
    owner = str(packet.get("required_disposition_owner") or "").strip()
    frontier_ref = _required_text(packet.get("frontier_ref"), "frontier_ref")
    if state in {"observed_paused", "observed_human_gate", "needs_disposition"}:
        if owner:
            return f"HOLD; 판단 주체 {owner}; {frontier_ref}"
        return f"HOLD; {frontier_ref}"
    if state == "observed_closed_boundary":
        return f"닫힌 경계 관찰; {frontier_ref}"
    if state == "observed_started":
        return f"시작 이후 아직 다음 상태 없음; {frontier_ref}"
    return frontier_ref


def _http_status_class(status_code: int) -> str:
    if 200 <= status_code <= 299:
        return "http_2xx"
    if 300 <= status_code <= 399:
        return "http_3xx"
    if 400 <= status_code <= 499:
        return "http_4xx"
    if 500 <= status_code <= 599:
        return "http_5xx"
    return "http_other"


def _slack_provider_status_class(response_body: bytes) -> tuple[str, bool | None]:
    try:
        decoded = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ("json_unreadable", None)
    if not isinstance(decoded, Mapping):
        return ("json_not_mapping", None)
    provider_ok = decoded.get("ok")
    if provider_ok is True:
        return ("slack_ok_true", True)
    if provider_ok is False:
        return ("slack_ok_false", False)
    return ("slack_ok_missing", None)


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


def _nested_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _nested_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_keys(child)


def _repo_path(repo: Path, value: Path | str) -> Path:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo / candidate).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"path escapes repo: {value}") from exc
    return resolved


def _path_segment(value: str) -> str:
    cleaned = value.strip().replace(":", "-").replace("/", "-")
    cleaned = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in cleaned)
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError("report_id cannot be used as a path segment")
    return cleaned


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return path.resolve().as_posix()

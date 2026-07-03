"""Reporter notification projection kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes the support-only reporter notification projection guard; it owns no
axis crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.yaml_subset import KernelResult, ProfileError, _ensure_import_identity


@contextlib.contextmanager
def _without_report_grain_env() -> Any:
    previous = os.environ.pop("BRICK_REPORT_GRAIN", None)
    try:
        yield
    finally:
        if previous is not None:
            os.environ["BRICK_REPORT_GRAIN"] = previous


def _minimal_reporter_packet() -> Mapping[str, Any]:
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
        "checker_summary_ref": "support/checkers/profiles/reporter_notification_projection.yaml",
        "required_disposition_owner": "",
        "sink_refs": ["report-sink:local-inbox"],
        "generated_at": "2026-05-31T00:00:00+00:00",
        "source_truth": False,
        "not_proven": ["negative probe"],
        "proof_limits": ["negative probe support evidence only"],
    }


def _minimal_operator_wake_target() -> Mapping[str, Any]:
    return {
        "target_ref": "operator-wake-target:local-active-operator",
        "target_kind": "operator_wake_local",
        "sink_ref": "report-sink:operator-wake-local",
        "delivery_mode": "local_projection",
        "side_effect_state": "none",
        "proof_limits": ["provider-neutral local wake target reference only"],
        "not_proven": [
            "operator noticed wake packet",
            "real provider thread wake behavior",
            "external side effect behavior",
        ],
    }


# Inbox-packet property tables, migrated 1:1 from the retired standing-packet
# pins of read_side_projection_boundary.yaml (json_required_paths +
# json_value_paths on the 3 dogfood status/inbox packets).
_INBOX_FRONTIER_PACKET_REQUIRED_KEYS = (
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
_OPERATOR_WAKE_PACKET_REQUIRED_KEYS = (
    "wake_packet_id",
    "report_id",
    "report_kind",
    "building_id",
    "observed_board_state",
    "evidence_root_refs",
    "operator_wake_targets",
    "source_truth",
    "not_proven",
    "proof_limits",
)


def _reporter_inbox_packet_shape_fold(
    reporter: Any,
    *,
    local_inbox_packet: Mapping[str, Any],
    wake_bus_frontier_packet: Mapping[str, Any],
    operator_wake_packet: Mapping[str, Any],
) -> None:
    """Assert the written inbox/wake packets carry the retired pins' shape."""

    for packet_label, packet in (
        ("local-inbox frontier packet", local_inbox_packet),
        ("wake-bus frontier packet", wake_bus_frontier_packet),
    ):
        for key in _INBOX_FRONTIER_PACKET_REQUIRED_KEYS:
            if key not in packet:
                raise ProfileError(f"{packet_label} is missing required key {key!r}")
        if not (isinstance(packet.get("evidence_root_refs"), list) and packet["evidence_root_refs"]):
            raise ProfileError(f"{packet_label} evidence_root_refs must be a non-empty list")
        if packet.get("observed_board_state") not in set(reporter.OBSERVED_BOARD_STATES):
            raise ProfileError(
                f"{packet_label} observed_board_state {packet.get('observed_board_state')!r} "
                "is not an admitted OBSERVED_BOARD_STATES member"
            )
        if "report-sink:local-inbox" not in (packet.get("sink_refs") or []):
            raise ProfileError(f"{packet_label} sink_refs does not name report-sink:local-inbox")
    if "report-sink:operator-wake-local" not in (
        wake_bus_frontier_packet.get("sink_refs") or []
    ):
        raise ProfileError(
            "wake-bus frontier packet sink_refs does not name report-sink:operator-wake-local"
        )
    wake_bus_targets = wake_bus_frontier_packet.get("operator_wake_targets")
    if not (isinstance(wake_bus_targets, list) and wake_bus_targets):
        raise ProfileError("wake-bus frontier packet operator_wake_targets must be non-empty")
    if any(
        target.get("sink_ref") != "report-sink:operator-wake-local"
        for target in wake_bus_targets
        if isinstance(target, Mapping)
    ):
        raise ProfileError(
            "wake-bus frontier packet operator_wake_targets[].sink_ref must be "
            "report-sink:operator-wake-local"
        )
    for key in _OPERATOR_WAKE_PACKET_REQUIRED_KEYS:
        if key not in operator_wake_packet:
            raise ProfileError(f"operator wake packet is missing required key {key!r}")
    wake_targets = operator_wake_packet.get("operator_wake_targets")
    if not (isinstance(wake_targets, list) and wake_targets):
        raise ProfileError("operator wake packet operator_wake_targets must be non-empty")
    for target in wake_targets:
        if not isinstance(target, Mapping) or target.get("delivery_mode") != "local_projection":
            raise ProfileError(
                "operator wake packet operator_wake_targets[].delivery_mode must be "
                "local_projection"
            )


def _assert_reporter_label_parity(repo: Path) -> int:
    canonical_path = repo / "support" / "operator" / "label_map.json"
    labels_js_path = repo / "support" / "dashboard" / "src" / "data" / "labels.js"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    if not isinstance(canonical, Mapping):
        raise ProfileError("label_map.json did not parse as a mapping")
    labels_js = labels_js_path.read_text(encoding="utf-8")
    checks = {
        "BRICK": "brick_kinds",
        "LANE": "lanes",
        "TOOL": "tool_policies",
        "MOVEMENT": "movements",
        "STATE": "states",
        "DISP": "display_states",
        "OWNER": "disposition_owners",
        "EVENT": "events",
        "OBSERVED": "observed_board_states",
        "ACTION": "actions",
    }
    inspected = 0
    for const_name, section in checks.items():
        observed = _extract_js_const_object(labels_js, const_name)
        expected = canonical.get(section)
        if observed != expected:
            raise ProfileError(
                f"label parity mismatch for {const_name}/{section}: "
                f"observed={observed!r} expected={expected!r}"
            )
        inspected += 1
    return inspected


def _assert_reporter_agent_incomplete_event_mapping(reporter: Any) -> int:
    original_observer = reporter.observe_building_frontier

    def _fake_agent_incomplete_frontier(*_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
        return {
            "frontier_kind": "agent_incomplete",
            "not_proven": ["probe frontier only"],
            "proof_limits": ["support projection probe only"],
        }

    reporter.observe_building_frontier = _fake_agent_incomplete_frontier
    try:
        event_kind = reporter.building_event_kind_from_frontier(
            Path("agent-incomplete-frontier-probe"),
            repo_root=Path.cwd(),
        )
    finally:
        reporter.observe_building_frontier = original_observer
    if event_kind != "intervention_required":
        raise ProfileError(
            "reporter agent_incomplete frontier must emit intervention_required, "
            f"got {event_kind!r}"
        )
    owner = reporter._required_disposition_owner({"frontier_kind": "agent_incomplete"})
    if owner != "caller-or-coo":
        raise ProfileError(
            "reporter agent_incomplete frontier must project caller-or-coo owner, "
            f"got {owner!r}"
        )
    return 2


def _extract_js_const_object(source: str, const_name: str) -> Mapping[str, Any]:
    marker = f"export const {const_name} ="
    marker_index = source.find(marker)
    if marker_index < 0:
        raise ProfileError(f"labels.js missing export const {const_name}")
    start = source.find("{", marker_index)
    if start < 0:
        raise ProfileError(f"labels.js export const {const_name} has no object literal")
    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                literal = source[start : index + 1]
                break
    else:
        raise ProfileError(f"labels.js export const {const_name} object did not close")
    literal = re.sub(r"//.*", "", literal)
    literal = re.sub(r"([,{]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r"\1'\2':", literal)
    try:
        parsed = ast.literal_eval(literal)
    except (SyntaxError, ValueError) as exc:
        raise ProfileError(f"labels.js export const {const_name} did not parse: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ProfileError(f"labels.js export const {const_name} is not a mapping")
    return dict(parsed)


def _assert_reporter_message_shape(report_sinks: Any) -> tuple[str, int]:
    packet = {
        **_minimal_reporter_packet(),
        "report_id": "reporter-message-shape-probe",
        "building_id": "customer-language-probe",
        "human_title": "알림 말투 점검",
        "observed_board_state": "observed_closed_boundary",
        "trigger_event_ref": "building-event:building_finished:customer-language-probe",
        "current_brick_ref": "brick-work",
        "current_work_kind": "work",
        "current_lane": "worker",
        "last_completed_step_ref": "work/step-outputs/customer-language-probe-work-attempt-1/step-output.json",
        "frontier_ref": "project/brick-protocol/buildings/customer-language-probe#frontier:complete:event:building_finished",
        "sink_refs": ["report-sink:slack"],
    }
    finished_text = report_sinks._slack_message_text(packet)
    finished_top_level_text = report_sinks._slack_message_text(packet, force_top_level=True)
    intervention_packet = {
        **packet,
        "observed_board_state": "needs_disposition",
        "trigger_event_ref": "building-event:intervention_required:customer-language-probe",
        "frontier_ref": (
            "project/brick-protocol/buildings/customer-language-probe"
            "#frontier:human_review_waiting:event:intervention_required"
        ),
        "required_disposition_owner": "caller-or-coo",
    }
    intervention_text = report_sinks._slack_message_text(intervention_packet)
    intervention_top_level_text = report_sinks._slack_message_text(
        intervention_packet,
        force_top_level=True,
    )
    started_text = report_sinks._slack_message_text(
        {
            **packet,
            "trigger_event_ref": "building-event:building_started:customer-language-probe",
            "observed_board_state": "observed_started",
            "structure_diagram": "[작업·워커] ──▶ (완료)",
        }
    )
    text = "\n---\n".join(
        (
            started_text,
            finished_text,
            intervention_text,
            finished_top_level_text,
            intervention_top_level_text,
        )
    )
    required_fragments = (
        "알림 말투 점검",
        "시작했어요.",
        "진행되는 대로 여기 댓글로 알려드릴게요.",
        "```",
        "[작업·워커] ──▶ (완료)",
        "✅ 다 됐어요!",
        "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)",
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise ProfileError(f"Slack message shape missing fragment {fragment!r}:\n{text}")
    if finished_text != "✅ 다 됐어요!":
        raise ProfileError(f"building_finished reply text was not clean:\n{finished_text}")
    if intervention_text != "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)":
        raise ProfileError(f"intervention_required reply text was not clean:\n{intervention_text}")
    if not finished_top_level_text.startswith("🧱 알림 말투 점검\n"):
        raise ProfileError(
            f"building_finished fallback text was not top-level titled:\n{finished_top_level_text}"
        )
    if not intervention_top_level_text.startswith("🧱 알림 말투 점검\n"):
        raise ProfileError(
            "intervention_required fallback text was not top-level titled:\n"
            f"{intervention_top_level_text}"
        )
    forbidden_fragments = (
        "ref:",
        "brick=",
        "step=",
        "frontier=",
        "※",
        "누구:",
        "다음:",
    )
    for fragment in forbidden_fragments:
        if fragment in text:
            raise ProfileError(f"Slack message leaked customer-facing jargon {fragment!r}:\n{text}")
    forbidden_legacy_fragments = (
        "Brick:",
        "Agent:",
        "Link:",
        "work/step-outputs",
        "마지막 완료 step",
        "step=-",
        "brick=-",
        "운영 refs:",
    )
    for fragment in forbidden_legacy_fragments:
        if fragment in text:
            raise ProfileError(f"Slack message leaked legacy wording {fragment!r}:\n{text}")
    empty_probe = report_sinks._slack_message_text(
        {
            **packet,
            "report_id": "reporter-message-empty-field-probe",
            "current_brick_ref": "",
            "last_completed_step_ref": "",
            "frontier_ref": "project/brick-protocol/buildings/customer-language-probe#frontier:complete",
        }
    )
    for fragment in (*forbidden_fragments, "step=-", "brick=-"):
        if fragment in empty_probe:
            raise ProfileError(f"Slack empty-field probe leaked {fragment!r}:\n{empty_probe}")
    return text, len(required_fragments) + len(forbidden_fragments) + len(forbidden_legacy_fragments) + 1


# EXPLICIT NO-CREDS REPORT ENV (footgun-fix robustness). An EMPTY report_env
# ({}) now AUTO-LOADS ~/.brick/report.env at the run.py engine seam (so a caller
# passing {} can never silently close the Slack gate). That means a literal {}
# no longer reliably exercises the "no Slack creds -> env-gated sink drops"
# coverage on a developer machine that HAS report.env. To keep that coverage
# EXPLICIT (and decoupled from the vessel gate), the no-env probes thread this
# NON-EMPTY mapping that deliberately carries NO BRICK_REPORT_*/BRICK_DASHBOARD_*
# credential key: it is truthy (so it bypasses the empty==auto-load branch) yet
# leaves _slack_environment_ready/_dashboard_environment_ready False on purpose.
_NO_CREDS_REPORT_ENV: dict[str, str] = {"BRICK_REPORT_PROBE_NO_CREDS": "1"}


def _assert_reporter_auto_wiring(repo: Path, reporter: Any, report_sinks: Any) -> tuple[str, str, str, int]:
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.brick.work import parse_required_return_shape
    from support.checkers.lib.case_runners import _preset_completion_command_runner

    inspected = 0
    command_runner = _preset_completion_command_runner(LocalCliCompleted)

    def _brain(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {}
        for label in parse_required_return_shape(request.required_return_shape):
            if label == "made_changes":
                returned[label] = ["notification auto-wire probe change"]
            elif label == "observed_evidence":
                returned[label] = ["notification auto-wire probe evidence"]
            elif label == "not_proven":
                returned[label] = ["semantic correctness of notification probe work"]
            else:
                returned[label] = f"probe value for {label}"
        return returned

    with tempfile.TemporaryDirectory(prefix="bp-reporter-auto-wire-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        no_env_plan = _reporter_auto_wire_plan("reporter-auto-wire-no-env")
        with _without_report_grain_env():
            result = run_building_plan(
                no_env_plan,
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                # EXPLICIT no-creds env (not {}): {} now auto-loads, so an empty
                # dict would no longer prove the "no Slack env -> env-gated sink
                # drops" coverage on a machine WITH ~/.brick/report.env. This
                # truthy, credential-free mapping suppresses the env-gated sinks
                # ON PURPOSE and bypasses the empty==auto-load branch.
                report_env=_NO_CREDS_REPORT_ENV,
            )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 5:
            raise ProfileError(
                "basic auto-wiring without Slack env should emit start, brick, and terminal observations"
            )
        for observation in observations:
            sink_refs = observation.get("report_packet", {}).get("sink_refs", [])
            if sink_refs != ["report-sink:local-inbox"]:
                raise ProfileError(
                    f"auto-wiring without Slack env attempted unexpected sinks: {sink_refs}"
                )
        inbox_packets = sorted((temp_repo / "project" / "brick-protocol" / "status" / "inbox").glob("*.json"))
        if len(inbox_packets) != 5:
            raise ProfileError("basic auto-wiring without Slack env did not write five local inbox packets")
        local_inbox_text = inbox_packets[0].read_text(encoding="utf-8")
        inspected += 4

    temp_sent_messages: list[str] = []

    def _fake_temp_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        temp_sent_messages.append(str(payload.get("text") or ""))
        return 200, b'{"ok":true}'

    with tempfile.TemporaryDirectory(prefix="bp-reporter-auto-wire-slack-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        repo_inbox = repo / "project" / "brick-protocol" / "status" / "inbox"
        repo_inbox_before = sorted(path.name for path in repo_inbox.glob("*.json")) if repo_inbox.is_dir() else []
        fake_env = {
            "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
            "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
        }
        with _without_report_grain_env():
            result = run_building_plan(
                _reporter_auto_wire_plan("reporter-auto-wire-fake-slack"),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_temp_slack_sender,
            )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 5:
            raise ProfileError("temp-root auto-wiring with fake Slack env emitted wrong event count")
        for observation in observations:
            sink_refs = observation.get("report_packet", {}).get("sink_refs", [])
            if sink_refs != ["report-sink:local-inbox"]:
                raise ProfileError(f"temp-root auto-wiring used external sinks: {sink_refs}")
        if temp_sent_messages:
            raise ProfileError(f"temp-root fake Slack sender was invoked: {len(temp_sent_messages)}")
        repo_inbox_after = sorted(path.name for path in repo_inbox.glob("*.json")) if repo_inbox.is_dir() else []
        if repo_inbox_after != repo_inbox_before:
            raise ProfileError("temp-root auto-wiring touched the real repo inbox")
        inspected += 5

    real_sent_messages: list[str] = []

    def _fake_real_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        real_sent_messages.append(str(payload.get("text") or ""))
        return 200, b'{"ok":true}'

    with tempfile.TemporaryDirectory(prefix="bp-reporter-real-vessel-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        fake_env = {
            "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
            "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
        }
        original_reporter_root = reporter.REPO_ROOT
        try:
            reporter.REPO_ROOT = temp_repo
            result = run_building_plan(
                _reporter_auto_wire_plan(
                    "reporter-auto-wire-real-vessel",
                    report_event_policy={
                        "enabled": True,
                        "mode": "basic",
                        "grain": "building",
                        "event_kinds": ["building_finished"],
                        "sink_refs": ["report-sink:local-inbox", "report-sink:slack"],
                        "allow_real_slack_delivery": True,
                    },
                ),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_real_slack_sender,
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 1:
            raise ProfileError("real-vessel completion emitted wrong event count")
        sink_refs = observations[0].get("report_packet", {}).get("sink_refs", [])
        if sink_refs != ["report-sink:local-inbox", "report-sink:slack"]:
            raise ProfileError(f"real-vessel completion used wrong sinks: {sink_refs}")
        if len(real_sent_messages) != 1:
            raise ProfileError(
                f"real-vessel fake Slack sender count expected 1, observed {len(real_sent_messages)}"
            )
        inspected += 4

    verbose_text = ""
    with tempfile.TemporaryDirectory(prefix="bp-reporter-verbose-mode-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        result = run_building_plan(
            _reporter_auto_wire_plan(
                "reporter-verbose-mode",
                step_kinds=("design", "work"),
                report_event_policy={
                    "enabled": True,
                    "mode": "verbose",
                    "grain": "building",
                    "event_kinds": ["building_finished"],
                    "sink_refs": ["report-sink:local-inbox"],
                },
            ),
            output_root=output_root,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _brain},
            command_runner=command_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=10,
            # EXPLICIT no-creds env (not {}): keep this probe credential-free and
            # off the empty==auto-load path (the policy only declares local-inbox,
            # so Slack delivery never applies; this just avoids pulling real
            # ~/.brick/report.env creds into a render-only test).
            report_env=_NO_CREDS_REPORT_ENV,
        )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 1:
            raise ProfileError("verbose-mode temp drive emitted wrong event count")
        packet = observations[0].get("report_packet", {})
        verbose_text = report_sinks._slack_message_text(packet)
        if "✅ 다 됐어요!" not in verbose_text:
            raise ProfileError(f"verbose-mode message did not render plain completion:\n{verbose_text}")
        for fragment in ("단계: ", "ref:", "누구:", "다음:"):
            if fragment in verbose_text:
                raise ProfileError(f"verbose-mode message leaked old Slack fragment {fragment!r}:\n{verbose_text}")
        inspected += 3

    return real_sent_messages[0], local_inbox_text, verbose_text, inspected


def _assert_reporter_brick_grain_threading(
    repo: Path,
    reporter: Any,
    report_sinks: Any,
) -> tuple[str, str, int]:
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.brick.work import parse_required_return_shape
    from support.checkers.lib.case_runners import _preset_completion_command_runner

    inspected = 0
    command_runner = _preset_completion_command_runner(LocalCliCompleted)

    sent_payloads: list[Mapping[str, Any]] = []

    def _brain(request: Any) -> Mapping[str, Any]:
        thread_payloads_during_work = [payload for payload in sent_payloads if payload.get("thread_ts")]
        received_during_work = [
            payload
            for payload in thread_payloads_during_work
            if "시작했어요." in str(payload.get("text") or "")
            and "진행되는 대로" not in str(payload.get("text") or "")
        ]
        returned_or_gate_during_work = [
            payload
            for payload in thread_payloads_during_work
            if "단계 끝났어요" in str(payload.get("text") or "")
            or "마무리예요" in str(payload.get("text") or "")
        ]
        if len(received_during_work) != 1:
            raise ProfileError(
                "brick grain work-time probe expected brick_received before Agent work, "
                f"got {len(received_during_work)}"
            )
        if returned_or_gate_during_work:
            raise ProfileError(
                "brick grain work-time probe observed brick_returned/gate_passed before Agent work"
            )
        returned: dict[str, Any] = {}
        for label in parse_required_return_shape(request.required_return_shape):
            if label == "made_changes":
                returned[label] = ["brick grain probe change"]
            elif label == "observed_evidence":
                returned[label] = ["brick grain probe evidence"]
            elif label == "not_proven":
                returned[label] = ["semantic correctness of brick grain probe work"]
            else:
                returned[label] = f"probe value for {label}"
        return returned

    building_policy = reporter.report_event_policy_from_plan(
        {
            "report_event_policy": {
                "enabled": True,
                "grain": "building",
            }
        }
    )
    if building_policy.get("event_kinds") != [
        "building_started",
        "intervention_required",
        "building_finished",
    ]:
        raise ProfileError("building grain policy did not preserve the three existing event kinds")
    default_policy = reporter.report_event_policy_from_plan({})
    brick_policy = reporter.report_event_policy_from_plan(
        {
            "report_event_policy": {
                "enabled": True,
                "grain": "brick",
            }
        }
    )
    expected_brick_events = [
        "building_started",
        "intervention_required",
        "building_finished",
        "brick_received",
        "brick_returned",
        "gate_passed",
        "disposition_applied",
    ]
    if brick_policy.get("event_kinds") != expected_brick_events:
        raise ProfileError(
            "brick grain policy did not extend event kinds additively: "
            f"{brick_policy.get('event_kinds')!r}"
        )
    if (
        default_policy.get("event_kinds") != expected_brick_events
        or default_policy.get("report_event_grain") != "brick"
    ):
        raise ProfileError(
            "absent report policy did not default to brick grain: "
            f"{default_policy!r}"
        )
    inspected += 6

    def _fake_thread_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        sent_payloads.append(payload)
        if payload.get("thread_ts"):
            return 200, b'{"ok":true}'
        return 200, b'{"ok":true,"ts":"1718200000.000100","channel":"CREDPROBE"}'

    fake_env = {
        "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
        "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
    }
    brick_reply_text = ""
    received_reply_text = ""
    gate_reply_text = ""
    nonterminal_gate_text = ""
    disposition_reply_text = ""
    intervention_reply_text = ""
    finished_reply_text = ""
    fallback_intervention_text = ""
    fallback_finished_text = ""
    with tempfile.TemporaryDirectory(prefix="bp-reporter-brick-grain-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        original_reporter_root = reporter.REPO_ROOT
        try:
            reporter.REPO_ROOT = temp_repo
            result = run_building_plan(
                _reporter_auto_wire_plan("reporter-brick-grain-thread"),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_thread_slack_sender,
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root

        root = output_root / "reporter-brick-grain-thread"
        thread_path = root / "raw" / "report-thread.jsonl"
        if not thread_path.is_file():
            raise ProfileError("brick grain parent Slack ts was not recorded in raw/report-thread.jsonl")
        thread_text = thread_path.read_text(encoding="utf-8")
        if "1718200000.000100" not in thread_text or "CREDPROBE" not in thread_text:
            raise ProfileError("brick grain thread record did not preserve ts + channel ref")

        observations = tuple(getattr(result, "_report_event_observations", ()))
        trigger_refs = [
            str(observation.get("report_packet", {}).get("trigger_event_ref") or "")
            for observation in observations
            if isinstance(observation, Mapping)
        ]
        for event_kind in ("brick_received", "brick_returned", "gate_passed"):
            if not any(event_kind in trigger for trigger in trigger_refs):
                raise ProfileError(f"brick grain did not emit {event_kind} support event")
        delivery_path = root / "raw" / "report-delivery.jsonl"
        if not delivery_path.is_file():
            raise ProfileError("brick grain delivery timing was not recorded in raw/report-delivery.jsonl")
        delivery_records: list[Mapping[str, Any]] = []
        for line in delivery_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProfileError("raw/report-delivery.jsonl contained invalid JSON") from exc
            if not isinstance(record, Mapping):
                raise ProfileError("raw/report-delivery.jsonl contained a non-mapping record")
            if record.get("kind") == "report_delivery_observation":
                delivery_records.append(record)
        if not delivery_records:
            raise ProfileError("raw/report-delivery.jsonl contained no report delivery observations")

        def _delivery_timestamp(record: Mapping[str, Any]) -> datetime:
            delivered_at = str(record.get("delivered_at") or "").strip()
            if not delivered_at:
                raise ProfileError(f"report delivery record missing delivered_at: {record!r}")
            try:
                return datetime.fromisoformat(delivered_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ProfileError(
                    f"report delivery record delivered_at is not ISO datetime: {delivered_at!r}"
                ) from exc

        active_sink_refs = {
            str(record.get("sink_ref") or "")
            for record in delivery_records
            if str(record.get("event_kind") or "") == "brick_received"
        }
        active_sink_refs.discard("")
        if active_sink_refs != {"report-sink:local-inbox", "report-sink:slack"}:
            raise ProfileError(
                "brick grain expected local-inbox and Slack brick_received delivery records, "
                f"got {sorted(active_sink_refs)!r}"
            )
        by_event_and_sink: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for record in delivery_records:
            if record.get("source_truth") is not False:
                raise ProfileError("report delivery record source_truth is not false")
            key = (
                str(record.get("event_kind") or ""),
                str(record.get("sink_ref") or ""),
            )
            by_event_and_sink.setdefault(key, []).append(record)
        for sink_ref in sorted(active_sink_refs):
            received_records = by_event_and_sink.get(("brick_received", sink_ref), [])
            if len(received_records) != 1:
                raise ProfileError(
                    f"brick grain expected one brick_received delivery record for {sink_ref}, "
                    f"got {len(received_records)}"
                )
            received_at = _delivery_timestamp(received_records[0])
            for later_event in ("brick_returned", "gate_passed", "building_finished"):
                later_records = by_event_and_sink.get((later_event, sink_ref), [])
                if len(later_records) != 1:
                    raise ProfileError(
                        f"brick grain expected one {later_event} delivery record for {sink_ref}, "
                        f"got {len(later_records)}"
                    )
                later_at = _delivery_timestamp(later_records[0])
                if not received_at < later_at:
                    raise ProfileError(
                        "brick_received delivery was not earlier than completion delivery "
                        f"for {sink_ref}/{later_event}: {received_at.isoformat()} >= "
                        f"{later_at.isoformat()}"
                    )

        thread_payloads = [payload for payload in sent_payloads if payload.get("thread_ts")]
        if len(thread_payloads) != 4:
            raise ProfileError(
                "brick grain expected brick_received, brick_returned, gate_passed, "
                f"and completion Slack thread replies, got {len(thread_payloads)}"
            )
        for payload in thread_payloads:
            if payload.get("thread_ts") != "1718200000.000100":
                raise ProfileError(f"brick grain reply carried wrong thread_ts: {payload!r}")
        received_payloads = [
            payload
            for payload in thread_payloads
            if "시작했어요." in str(payload.get("text") or "")
            and "진행되는 대로" not in str(payload.get("text") or "")
        ]
        returned_payloads = [
            payload
            for payload in thread_payloads
            if "단계 끝났어요" in str(payload.get("text") or "")
        ]
        gate_payloads = [
            payload
            for payload in thread_payloads
            if "마무리예요" in str(payload.get("text") or "")
        ]
        if len(received_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one brick_received Slack thread reply, "
                f"got {len(received_payloads)}"
            )
        if len(returned_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one brick_returned Slack thread reply, "
                f"got {len(returned_payloads)}"
            )
        if len(gate_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one terminal gate_passed Slack thread reply, "
                f"got {len(gate_payloads)}"
            )
        received_reply_text = str(received_payloads[0].get("text") or "")
        brick_reply_text = str(returned_payloads[0].get("text") or "")
        gate_reply_text = str(gate_payloads[0].get("text") or "")
        for fragment in ("①", "작업", "시작했어요.", "담당: Codex Local", "("):
            if fragment not in received_reply_text:
                raise ProfileError(
                    f"brick_received Slack reply missing fragment {fragment!r}:\n{received_reply_text}"
                )
        for fragment in ("①", "작업", "단계 끝났어요", "담당: Codex Local", "("):
            if fragment not in brick_reply_text:
                raise ProfileError(
                    f"brick grain Slack reply missing fragment {fragment!r}:\n{brick_reply_text}"
                )
        for fragment in ("①", "작업", "확인했어요.", "마무리예요", "("):
            if fragment not in gate_reply_text:
                raise ProfileError(
                    f"gate_passed Slack reply missing fragment {fragment!r}:\n{gate_reply_text}"
                )
        for label, reply_text in (
            ("brick_received", received_reply_text),
            ("brick_returned", brick_reply_text),
            ("gate_passed", gate_reply_text),
        ):
            if not re.search(r"\(\d{2}:\d{2}\)", reply_text):
                raise ProfileError(
                    f"{label} Slack reply did not render KST HH:MM times:\n{reply_text}"
                )
            for fragment in ("ref:", "brick=", "frontier=", "※", "누구:", "다음:"):
                if fragment in reply_text:
                    raise ProfileError(
                        f"{label} Slack reply leaked forbidden fragment {fragment!r}:\n{reply_text}"
                    )
        nonterminal_gate_text = report_sinks._slack_message_text(
            {
                **_minimal_reporter_packet(),
                "report_id": "reporter-gate-nonterminal-probe",
                "building_id": "reporter-brick-grain-thread",
                "trigger_event_ref": "building-event:gate_passed:reporter-brick-grain-thread",
                "current_work_kind": "work",
                "current_lane": "worker",
                "event_context": {
                    "sequence_index": 1,
                    "returned_at": "2026-06-12T00:01:00+00:00",
                    "next_brick_instance_ref": "brick-review",
                    "next_work_kind": "review",
                },
            }
        )
        for fragment in ("①", "작업", "다음 단계(검수)", "넘어가요", "(09:01)"):
            if fragment not in nonterminal_gate_text:
                raise ProfileError(
                    f"nonterminal gate_passed Slack reply missing fragment {fragment!r}:\n"
                    f"{nonterminal_gate_text}"
                )
        finished_payloads = [
            payload
            for payload in thread_payloads
            if "✅ 다 됐어요!" in str(payload.get("text") or "")
        ]
        if len(finished_payloads) != 1:
            raise ProfileError(
                "brick grain expected one completion Slack thread reply, "
                f"got {len(finished_payloads)}"
            )
        finished_reply_text = str(finished_payloads[0].get("text") or "")
        if finished_reply_text != "✅ 다 됐어요!":
            raise ProfileError(
                f"building_finished Slack reply was not a clean comment:\n{finished_reply_text}"
            )
        if "🧱" in finished_reply_text:
            raise ProfileError(
                f"building_finished Slack reply leaked parent title marker:\n{finished_reply_text}"
            )
        inspected += 21

        intervention_payloads: list[Mapping[str, Any]] = []

        def _fake_intervention_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
            intervention_payloads.append(payload)
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        try:
            intervention_packet = reporter.render_building_event_report_packet(
                event_kind="intervention_required",
                building_id="reporter-brick-grain-thread",
                building_root=root,
                current_brick_ref="brick-work",
                last_completed_step_ref="work/step-outputs/reporter-brick-grain-thread-work-attempt-1/step-output.json",
                required_disposition_owner="caller-or-coo",
                sink_refs=["report-sink:slack"],
                repo_root=temp_repo,
                generated_at="2026-06-12T00:03:00+00:00",
                report_event_grain="brick",
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        intervention_observation = report_sinks.send_slack_report_packet(
            intervention_packet,
            repo_root=temp_repo,
            allow_real_delivery=True,
            env=fake_env,
            sender=_fake_intervention_sender,
        )
        if intervention_observation.delivered is not True or len(intervention_payloads) != 1:
            raise ProfileError("intervention_required probe did not send exactly one thread reply")
        if intervention_payloads[0].get("thread_ts") != "1718200000.000100":
            raise ProfileError("intervention_required reply did not carry recorded thread_ts")
        intervention_reply_text = str(intervention_payloads[0].get("text") or "")
        if intervention_reply_text != "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)":
            raise ProfileError(
                "intervention_required Slack reply was not a clean owner-labeled comment:\n"
                f"{intervention_reply_text}"
            )
        if "🧱" in intervention_reply_text:
            raise ProfileError(
                f"intervention_required Slack reply leaked parent title marker:\n{intervention_reply_text}"
            )
        inspected += 4

        missing_thread_payloads: list[Mapping[str, Any]] = []
        fallback_payloads: list[Mapping[str, Any]] = []

        def _should_not_send(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            missing_thread_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true}'

        def _fallback_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            fallback_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        missing_thread_root = output_root / "missing-thread-case"
        missing_thread_root.mkdir(parents=True)
        # SLACK VESSEL-GATE narrowing (slack-wiring-gap 0619): the vessel
        # predicate now requires a REAL declared-building-plan spine (not just the
        # project/<id>/buildings path shape) before external Slack delivery is
        # allowed. This synthetic root models a genuine building that simply has
        # NOT recorded a Slack thread parent yet -- so it must carry a real spine,
        # otherwise external_delivery_allowed would be stripped by the vessel gate
        # and the missing-thread / fallback probes below would observe
        # not_attempted_non_real_vessel instead of the thread-status classes they
        # are pinning.
        (missing_thread_root / "declared-building-plan.json").write_text(
            json.dumps(
                {
                    "brick_steps": [
                        {
                            "completion_edge_ref": "edge:missing-thread-design-to-work",
                            "rows": [
                                {
                                    "axis": "Brick",
                                    "brick_instance_ref": "brick-missing-thread-design",
                                    "brick_work_ref": "work:missing-thread-design",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        try:
            missing_observations = []
            for event_kind in ("brick_received", "brick_returned", "gate_passed"):
                missing_packet = reporter.render_building_event_report_packet(
                    event_kind=event_kind,
                    building_id="missing-thread-case",
                    building_root=missing_thread_root,
                    current_brick_ref="brick-work",
                    last_completed_step_ref="work/step-outputs/missing-thread-case-work-attempt-1/step-output.json",
                    sink_refs=["report-sink:slack"],
                    repo_root=temp_repo,
                    generated_at="2026-06-12T00:00:00+00:00",
                    event_context={
                        "step_ref": "missing-thread-case-work",
                        "sequence_index": 1,
                        "received_at": "2026-06-12T00:00:00+00:00",
                        "returned_at": "2026-06-12T00:01:00+00:00",
                        "gate_note": "통과→다음스텝",
                        "next_brick_instance_ref": "brick-review",
                        "next_work_kind": "review",
                    },
                )
                missing_observations.append(
                    report_sinks.send_slack_report_packet(
                        missing_packet,
                        repo_root=temp_repo,
                        allow_real_delivery=True,
                        env=fake_env,
                        sender=_should_not_send,
                    )
                )
            fallback_observations = []
            for event_kind in ("intervention_required", "building_finished"):
                fallback_packet = reporter.render_building_event_report_packet(
                    event_kind=event_kind,
                    building_id="missing-thread-case",
                    building_root=missing_thread_root,
                    current_brick_ref="brick-work",
                    last_completed_step_ref=(
                        "work/step-outputs/missing-thread-case-work-attempt-1/"
                        "step-output.json"
                    ),
                    required_disposition_owner="caller-or-coo",
                    sink_refs=["report-sink:slack"],
                    repo_root=temp_repo,
                    generated_at="2026-06-12T00:04:00+00:00",
                    report_event_grain="brick",
                )
                fallback_observations.append(
                    report_sinks.send_slack_report_packet(
                        fallback_packet,
                        repo_root=temp_repo,
                        allow_real_delivery=True,
                        env=fake_env,
                        sender=_fallback_sender,
                    )
                )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        if any(
            observation.delivery_status_class != "not_attempted_missing_thread_ts"
            for observation in missing_observations
        ):
            raise ProfileError("brick grain missing-thread Slack sends did not all fail closed")
        if missing_thread_payloads:
            raise ProfileError("brick grain missing-thread probe still called Slack sender")
        if any(observation.delivered is not True for observation in fallback_observations):
            raise ProfileError("HOLD/FINISH missing-thread fallback did not send")
        if len(fallback_payloads) != 2:
            raise ProfileError(
                f"HOLD/FINISH missing-thread fallback sent {len(fallback_payloads)} payload(s)"
            )
        for payload in fallback_payloads:
            if payload.get("thread_ts"):
                raise ProfileError(f"missing-thread fallback unexpectedly carried thread_ts: {payload!r}")
        fallback_intervention_text = str(fallback_payloads[0].get("text") or "")
        fallback_finished_text = str(fallback_payloads[1].get("text") or "")
        if fallback_intervention_text != (
            "🧱 missing-thread-case\n"
            "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)"
        ):
            raise ProfileError(
                "intervention_required missing-thread fallback did not preserve titled form:\n"
                f"{fallback_intervention_text}"
            )
        if fallback_finished_text != "🧱 missing-thread-case\n✅ 다 됐어요!":
            raise ProfileError(
                "building_finished missing-thread fallback did not preserve titled form:\n"
                f"{fallback_finished_text}"
            )
        inspected += 5

        disposition_payloads: list[Mapping[str, Any]] = []

        def _fake_disposition_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
            disposition_payloads.append(payload)
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        try:
            disposition_packet = reporter.render_building_event_report_packet(
                event_kind="disposition_applied",
                building_id="reporter-brick-grain-thread",
                building_root=root,
                current_brick_ref="brick-work",
                last_completed_step_ref="work/step-outputs/reporter-brick-grain-thread-work-attempt-1/step-output.json",
                sink_refs=["report-sink:slack"],
                repo_root=temp_repo,
                generated_at="2026-06-12T00:02:00+00:00",
                event_context={
                    "disposition_action": "forward",
                    "disposition_author_ref": "coo:checker",
                    "applied_at": "2026-06-12T00:02:00+00:00",
                },
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        disposition_observation = report_sinks.send_slack_report_packet(
            disposition_packet,
            repo_root=temp_repo,
            allow_real_delivery=True,
            env=fake_env,
            sender=_fake_disposition_sender,
        )
        if disposition_observation.delivered is not True or len(disposition_payloads) != 1:
            raise ProfileError("disposition_applied probe did not send exactly one thread reply")
        if disposition_payloads[0].get("thread_ts") != "1718200000.000100":
            raise ProfileError("disposition_applied reply did not carry recorded thread_ts")
        disposition_reply_text = str(disposition_payloads[0].get("text") or "")
        if "⤷ COO 확인" not in disposition_reply_text:
            raise ProfileError(
                f"disposition_applied reply did not render coo stamp:\n{disposition_reply_text}"
            )
        if "다음 단계로 진행" not in disposition_reply_text:
            raise ProfileError(
                "explicit-forward disposition_applied reply did not preserve the forward label:\n"
                f"{disposition_reply_text}"
            )
        missing_action_disposition_text = report_sinks._slack_message_text(
            {
                **_minimal_reporter_packet(),
                "report_id": "reporter-disposition-missing-action-probe",
                "building_id": "reporter-brick-grain-thread",
                "trigger_event_ref": (
                    "building-event:disposition_applied:reporter-brick-grain-thread"
                ),
                "current_work_kind": "work",
                "current_lane": "worker",
                "generated_at": "2026-06-12T00:02:00+00:00",
                "event_context": {
                    "disposition_author_ref": "coo:checker",
                    "applied_at": "2026-06-12T00:02:00+00:00",
                },
            }
        )
        for fragment in ("forward", "다음 단계로 진행"):
            if fragment in missing_action_disposition_text:
                raise ProfileError(
                    "missing-action disposition_applied reply rendered Movement-shaped "
                    f"default {fragment!r}:\n{missing_action_disposition_text}"
                )
        inspected += 5

        temp_root_payloads: list[Mapping[str, Any]] = []

        def _temp_root_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            temp_root_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true,"ts":"1718200000.000200","channel":"CREDPROBE"}'

        non_vessel_root = Path(tmpdir) / "non-vessel-building-root"
        non_vessel_root.mkdir()
        temp_root_policy = reporter.report_event_policy_from_plan(
            {
                "report_event_policy": {
                    "enabled": True,
                    "grain": "brick",
                    "sink_refs": ["report-sink:slack"],
                    "allow_real_slack_delivery": True,
                }
            }
        )
        for event_kind in (
            "brick_received",
            "brick_returned",
            "gate_passed",
            "disposition_applied",
        ):
            observation = reporter.emit_building_event_for_policy(
                temp_root_policy,
                event_kind=event_kind,
                building_id=f"temp-root-{event_kind}",
                building_root=non_vessel_root,
                current_brick_ref="brick-work",
                last_completed_step_ref=f"work/step-outputs/temp-root-{event_kind}/step-output.json",
                repo_root=temp_repo,
                slack_env=fake_env,
                slack_sender=_temp_root_sender,
                event_context={"sequence_index": 1},
            )
            if observation is not None:
                raise ProfileError(
                    f"brick grain F12 vessel guard leaked external sink for {event_kind}"
                )
        if temp_root_payloads:
            raise ProfileError(
                "brick grain F12 vessel guard invoked Slack sender for temp-root building"
            )
        inspected += 4

    return (
        "\n".join(
            text
            for text in (
                received_reply_text,
                brick_reply_text,
                gate_reply_text,
                nonterminal_gate_text,
                intervention_reply_text,
                finished_reply_text,
                fallback_intervention_text,
                fallback_finished_text,
            )
            if text
        ),
        disposition_reply_text,
        inspected,
    )


def _copy_reporter_probe_agent_resources(repo: Path, temp_repo: Path) -> None:
    source = repo / "agent"
    target = temp_repo / "agent"
    shutil.copytree(source, target)


def _reporter_auto_wire_plan(
    building_id: str,
    *,
    step_kinds: Sequence[str] = ("work",),
    report_event_policy: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    from support.checkers.lib.case_runners import _graph_test_plan_from_linear

    steps: list[Mapping[str, Any]] = []
    for index, kind in enumerate(step_kinds):
        step_ref = f"{building_id}-{kind}"
        brick_instance_ref = f"brick-{kind}"
        next_target = (
            f"brick-{step_kinds[index + 1]}"
            if index + 1 < len(step_kinds)
            else f"building-boundary:{building_id}-closed"
        )
        step: dict[str, Any] = {
            "step_ref": step_ref,
            "step_template_ref": f"building-step-template:{kind}",
        }
        step["rows"] = [
            {
                "axis": "Brick",
                "row_ref": f"brick-row:{step_ref}",
                "brick_work_ref": f"work:{step_ref}",
                "brick_instance_ref": brick_instance_ref,
                "work_statement": "Exercise reporter auto-wire notification projection.",
                "comparison_rule": "Support observes notification projection only.",
                "required_return_shape": "made_changes, observed_evidence, not_proven",
            },
            {
                "axis": "Agent",
                "row_ref": f"agent-row:{step_ref}",
                "agent_object_ref": {
                    "design": "agent-object:design-lead",
                    "work": "agent-object:dev",
                }.get(kind, "agent-object:dev"),
            },
            {
                "axis": "Link",
                "row_ref": f"link-row:{step_ref}",
                "movement": "forward",
                "target_ref": next_target,
                "declared_gate_refs": ["link-gate:default-transition"],
                "building_lifecycle": {
                    "state": "closed",
                    "reason": "reporter auto-wire probe closed boundary",
                },
            },
        ]
        steps.append(step)
    plan: dict[str, Any] = {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "linear",
        "selected_adapter_ref": "adapter:codex-local",
        "task_source_ref": "task-source:inline-statement",
        "task_statement": f"# {building_id}\n\nExercise reporter auto-wire notification projection.",
        "steps": steps,
    }
    if report_event_policy is not None:
        plan["report_event_policy"] = dict(report_event_policy)
    return _graph_test_plan_from_linear(plan)


def _assert_no_scheduler_constructs(repo: Path) -> int:
    inspected = 0
    files = (
        repo / "support" / "operator" / "reporter.py",
        repo / "support" / "operator" / "report_sinks.py",
        repo / "support" / "operator" / "run.py",
        repo / "support" / "operator" / "walker_kernel.py",
    )
    forbidden_imports = {"threading", "sched", "queue", "asyncio"}
    forbidden_name_calls = {"sleep", "Thread", "Timer", "Queue"}
    forbidden_attr_calls = {
        ("time", "sleep"),
        ("threading", "Thread"),
        ("threading", "Timer"),
        ("queue", "Queue"),
        ("asyncio", "create_task"),
    }
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in forbidden_imports:
                        raise ProfileError(f"no-scheduler pin rejected import {alias.name} in {path}")
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".", 1)[0]
                if module in forbidden_imports:
                    raise ProfileError(f"no-scheduler pin rejected import from {node.module} in {path}")
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in forbidden_name_calls:
                    raise ProfileError(f"no-scheduler pin rejected call {func.id} in {path}")
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if (func.value.id, func.attr) in forbidden_attr_calls:
                        raise ProfileError(
                            f"no-scheduler pin rejected call {func.value.id}.{func.attr} in {path}"
                        )
        inspected += 1
    return inspected


def _assert_reporter_dashboard_project_ref_guard(report_sinks: Any) -> str:
    calls: list[tuple[str, str | None]] = []
    original = report_sinks.send_dashboard_building_delta

    def fake_delta_sender(
        building_id: str,
        *,
        project_ref: str | None = None,
        **_: Any,
    ) -> Any:
        calls.append((building_id, project_ref))
        return report_sinks.ReportSinkObservation(
            sink_ref=report_sinks.DASHBOARD_SINK_REF,
            delivered=True,
            packet_ref=building_id,
            written_path="",
            proof_limits=("dashboard project_ref probe support evidence only",),
            not_proven=("real dashboard delivery",),
            delivery_status_class="http_2xx",
            provider_response_status_class="http_2xx",
        )

    base_packet = {
        **_minimal_reporter_packet(),
        "report_id": "reporter-dashboard-project-ref-probe",
        "building_id": "probe-building",
        "external_delivery_allowed": True,
        "sink_refs": [report_sinks.DASHBOARD_SINK_REF],
    }
    try:
        report_sinks.send_dashboard_building_delta = fake_delta_sender
        with tempfile.TemporaryDirectory(prefix="bp-dashboard-project-ref-probe-") as tmp:
            missing_observations = report_sinks.deliver_report_packet(
                base_packet,
                repo_root=Path(tmp),
                allow_real_dashboard_delivery=True,
            )
        if calls:
            raise ProfileError(
                "dashboard project_ref guard mutation-RED failed: missing project_ref "
                "still called send_dashboard_building_delta"
            )
        if len(missing_observations) != 1:
            raise ProfileError("dashboard project_ref guard did not return one observation")
        missing = missing_observations[0]
        if missing.delivered is not False:
            raise ProfileError("dashboard project_ref guard marked missing-project-ref delivered")
        if missing.delivery_status_class != "not_attempted_missing_project_ref":
            raise ProfileError(
                "dashboard project_ref guard returned wrong status class: "
                f"{missing.delivery_status_class!r}"
            )

        with tempfile.TemporaryDirectory(prefix="bp-dashboard-project-ref-probe-") as tmp:
            present_observations = report_sinks.deliver_report_packet(
                {**base_packet, "project_ref": "project:brick-protocol"},
                repo_root=Path(tmp),
                allow_real_dashboard_delivery=True,
            )
        if calls != [("probe-building", "project:brick-protocol")]:
            raise ProfileError(
                "dashboard project_ref guard did not pass packet project_ref into delta delivery"
            )
        if len(present_observations) != 1 or present_observations[0].delivered is not True:
            raise ProfileError("dashboard project_ref positive probe did not return delivered observation")
    finally:
        report_sinks.send_dashboard_building_delta = original
    return "dashboard project_ref guard observed: missing project_ref records non-delivery; present project_ref reaches delta sender; mutation-RED would call the sender on missing project_ref."


def _assert_reporter_structure_diagram_branch_rendering(reporter: Any) -> str:
    order = ["plan", "design-a", "design-b", "join", "work-a", "work-b", "done"]
    labels = {
        "plan": "[계획·PM]",
        "design-a": "[긴 설계 형제 A·Design]",
        "design-b": "[긴 설계 형제 B·Design]",
        "join": "[취합·PM]",
        "work-a": "[구현 형제 A·Dev]",
        "work-b": "[구현 형제 B·Dev]",
        "done": "[검수·QA]",
    }
    adjacency = {
        "plan": ["design-a", "design-b"],
        "design-a": ["join"],
        "design-b": ["join"],
        "join": ["work-a", "work-b"],
        "work-a": ["done"],
        "work-b": ["done"],
    }
    reverse = {
        "design-a": ["plan"],
        "design-b": ["plan"],
        "join": ["design-a", "design-b"],
        "work-a": ["join"],
        "work-b": ["join"],
        "done": ["work-a", "work-b"],
    }
    expected = "\n".join(
        [
            "[계획·PM]",
            "  │",
            "  ├─ [긴 설계 형제 A·Design]",
            "  └─ [긴 설계 형제 B·Design]",
            "  │",
            "[취합·PM]",
            "  │",
            "  ├─ [구현 형제 A·Dev]",
            "  └─ [구현 형제 B·Dev]",
            "  │",
            "[검수·QA]",
            "  │",
            "(완료)",
        ]
    )
    rendered = reporter._layered_structure_diagram(  # noqa: SLF001
        order,
        labels,
        adjacency=adjacency,
        reverse=reverse,
        terminal_sources={"done"},
    )
    if rendered != expected:
        raise ProfileError(
            "layered fan structure diagram changed unexpectedly:\n"
            f"expected:\n{expected}\nactual:\n{rendered}"
        )
    branch_lines = reporter._branch_structure_lines(  # noqa: SLF001
        ("[긴 설계 형제 A·Design]", "[긴 설계 형제 B·Design]"),
        prefix="  ",
    )
    mutated = "\n".join(
        line.replace("  └─", "    └─", 1) for line in branch_lines
    )
    if "\n".join(branch_lines) == mutated:
        raise ProfileError("structure diagram mutation-RED fixture did not alter branch indentation")
    if mutated in rendered:
        raise ProfileError(
            "structure diagram mutation-RED failed: accumulated branch indentation was accepted"
        )
    return "structure diagram branch rendering observed: layered fan siblings keep exact two-space branch prefix and mutation-RED indentation is absent."


def run_reporter_notification_projection(repo: Path) -> KernelResult:
    _ensure_import_identity(repo)
    reporter = importlib.import_module("brick_protocol.support.operator.reporter")
    report_sinks = importlib.import_module("brick_protocol.support.operator.report_sinks")
    label_parity_count = _assert_reporter_label_parity(repo)
    agent_incomplete_event_count = _assert_reporter_agent_incomplete_event_mapping(reporter)
    message_text, message_shape_count = _assert_reporter_message_shape(report_sinks)
    (
        auto_wire_message,
        auto_wire_inbox_text,
        verbose_mode_text,
        auto_wire_count,
    ) = _assert_reporter_auto_wiring(repo, reporter, report_sinks)
    (
        brick_grain_text,
        disposition_text,
        brick_grain_count,
    ) = _assert_reporter_brick_grain_threading(repo, reporter, report_sinks)
    no_scheduler_count = _assert_no_scheduler_constructs(repo)
    dashboard_project_ref_text = _assert_reporter_dashboard_project_ref_guard(report_sinks)
    structure_diagram_text = _assert_reporter_structure_diagram_branch_rendering(reporter)

    observations = tuple(reporter.reporter_negative_probe_observations())
    if not observations:
        raise ProfileError("reporter negative probes did not return observations")
    not_rejected = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in observations
        if observation.get("rejected") is not True
    ]
    if not_rejected:
        raise ProfileError(
            "reporter negative probe(s) were not rejected: " + ", ".join(not_rejected)
        )
    owner_observations = tuple(reporter.reporter_owner_vocabulary_probe_observations())
    if not owner_observations:
        raise ProfileError("reporter owner vocabulary probes did not return observations")
    owner_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in owner_observations
        if observation.get("passed") is not True
    ]
    if owner_not_passed:
        raise ProfileError(
            "reporter owner vocabulary probe(s) did not pass: "
            + ", ".join(owner_not_passed)
        )
    delivery_wake_observations = tuple(reporter.reporter_delivery_wake_probe_observations())
    if not delivery_wake_observations:
        raise ProfileError("reporter delivery wake probes did not return observations")
    delivery_wake_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in delivery_wake_observations
        if observation.get("passed") is not True
    ]
    if delivery_wake_not_passed:
        raise ProfileError(
            "reporter delivery wake probe(s) did not pass: "
            + ", ".join(delivery_wake_not_passed)
        )
    event_hook_observations = tuple(reporter.reporter_event_hook_probe_observations())
    if not event_hook_observations:
        raise ProfileError("reporter event hook probes did not return observations")
    event_hook_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in event_hook_observations
        if observation.get("passed") is not True
    ]
    if event_hook_not_passed:
        raise ProfileError(
            "reporter event hook probe(s) did not pass: "
            + ", ".join(event_hook_not_passed)
        )

    packet = _minimal_reporter_packet()
    reporter.validate_report_packet(packet)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_repo = Path(tmp)
        sink_observations = report_sinks.deliver_report_packet(
            packet,
            repo_root=tmp_repo,
            overwrite_existing=False,
        )
        if len(sink_observations) != 1:
            raise ProfileError("local inbox sink did not return exactly one observation")
        sink_observation = sink_observations[0]
        if sink_observation.delivered is not True:
            raise ProfileError("local inbox sink observation did not mark delivered")
        written = tmp_repo / sink_observation.written_path
        if not written.is_file():
            raise ProfileError(f"local inbox sink did not write packet: {written}")
        written_packet = json.loads(written.read_text(encoding="utf-8"))
        if written_packet.get("source_truth") is not False:
            raise ProfileError("written local inbox packet source_truth is not false")

        wake_packet = {
            **packet,
            "sink_refs": ["report-sink:local-inbox", "report-sink:operator-wake-local"],
            "operator_wake_targets": [_minimal_operator_wake_target()],
        }
        wake_observations = report_sinks.deliver_report_packet(
            wake_packet,
            repo_root=tmp_repo,
            overwrite_existing=True,
        )
        if len(wake_observations) != 2:
            raise ProfileError("delivery wake bus did not emit two local observations")
        operator_wake_observations = [
            observation
            for observation in wake_observations
            if observation.sink_ref == "report-sink:operator-wake-local"
        ]
        if len(operator_wake_observations) != 1:
            raise ProfileError("operator wake local sink observation was not emitted")
        wake_written = tmp_repo / operator_wake_observations[0].written_path
        if not wake_written.is_file():
            raise ProfileError(f"operator wake sink did not write packet: {wake_written}")
        wake_written_packet = json.loads(wake_written.read_text(encoding="utf-8"))
        if wake_written_packet.get("source_truth") is not False:
            raise ProfileError("operator wake packet source_truth is not false")
        if not wake_written_packet.get("operator_wake_targets"):
            raise ProfileError("operator wake packet did not preserve wake target refs")

        # CLEAN-YARD v3 (Smith 0611): the 3 standing dogfood inbox packets
        # (run-surface-authority-boundary-0529 / reporter-delivery-wake-bus-0531)
        # left for the frozen museum; their json_required_paths/json_value_paths
        # pin properties are EXECUTED here 1:1 over the packets the REAL sinks
        # just wrote into the temp inbox.
        local_inbox_wake_bus = [
            observation
            for observation in wake_observations
            if observation.sink_ref == "report-sink:local-inbox"
        ]
        if len(local_inbox_wake_bus) != 1:
            raise ProfileError("wake-bus local inbox sink observation was not emitted")
        wake_bus_frontier_packet = json.loads(
            (tmp_repo / local_inbox_wake_bus[0].written_path).read_text(encoding="utf-8")
        )
        _reporter_inbox_packet_shape_fold(
            reporter,
            local_inbox_packet=written_packet,
            wake_bus_frontier_packet=wake_bus_frontier_packet,
            operator_wake_packet=wake_written_packet,
        )

        sink_rejected_complete = False
        try:
            report_sinks.deliver_report_packet(
                {**packet, "complete": True},
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_complete = True
        if not sink_rejected_complete:
            raise ProfileError("local inbox sink accepted forbidden complete field")

        sink_rejected_raw_secret = False
        try:
            report_sinks.deliver_report_packet(
                {**packet, "raw_secret": "redacted-probe"},
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_raw_secret = True
        if not sink_rejected_raw_secret:
            raise ProfileError("local inbox sink accepted raw secret shaped field")

        sink_rejected_unadmitted = False
        try:
            report_sinks.deliver_report_packet(
                packet,
                sink_refs=["report-sink:unadmitted"],
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_unadmitted = True
        if not sink_rejected_unadmitted:
            raise ProfileError("local inbox sink accepted unadmitted sink ref")

    # G6 sink ceiling — re-ratified at FOUR by Smith (0611): report_sinks owns
    # the dispatch seam + exactly these four sinks. The dashboard sink
    # (B-DASH/B-DASH-WIRE) made the set 4 de facto; Smith ratified 4 with the
    # explicit condition that a 5th sink requires the report_bus + sinks/<name>
    # split FIRST (blueprint 3.1) — never a 5th sibling in this module.
    ratified_sink_refs = frozenset(
        {
            "report-sink:local-inbox",
            "report-sink:operator-wake-local",
            "report-sink:slack",
            "report-sink:dashboard",
        }
    )
    admitted_sink_refs = frozenset(report_sinks.ADMITTED_SINK_REFS)
    if admitted_sink_refs != ratified_sink_refs:
        unexpected = sorted(admitted_sink_refs - ratified_sink_refs)
        missing = sorted(ratified_sink_refs - admitted_sink_refs)
        raise ProfileError(
            "G6 sink ceiling violated: ADMITTED_SINK_REFS must be exactly the "
            f"FOUR Smith-ratified (0611) sinks {sorted(ratified_sink_refs)} "
            f"(unexpected={unexpected}, missing={missing}); "
            "a 5th sink requires the report_bus split — never a 5th sibling"
        )

    return KernelResult(
        check_id="reporter_notification_projection",
        inspected=(
            len(observations)
            + len(owner_observations)
            + len(delivery_wake_observations)
            + len(event_hook_observations)
            + label_parity_count
            + agent_incomplete_event_count
            + message_shape_count
            + auto_wire_count
            + brick_grain_count
            + no_scheduler_count
            + 8
        ),
        output=(
            "reporter notification projection passed: "
            f"{len(observations)} reporter negative probe(s), "
            f"{len(owner_observations)} owner vocabulary probe(s), "
            f"{len(delivery_wake_observations)} delivery wake probe(s), "
            f"{len(event_hook_observations)} event hook probe(s), "
            f"{label_parity_count} label parity map(s), "
            f"{agent_incomplete_event_count} agent-incomplete event assertion(s), "
            f"{message_shape_count} Slack message shape assertion(s), "
            f"{auto_wire_count} auto-wire assertion(s), "
            f"{brick_grain_count} brick-grain thread assertion(s), "
            f"{no_scheduler_count} no-scheduler source file(s), "
            "local inbox write, operator wake write, forbidden field rejects, "
            "unadmitted sink reject, and the G6 sink ceiling (4 ratified sinks: "
            "local-inbox, operator-wake-local, slack, dashboard — Smith 0611; "
            "a 5th sink requires the report_bus split, never a 5th sibling) inspected. "
            f"Specimen after renderer: {message_text!r}. "
            f"Temp auto-wire Slack text: {auto_wire_message!r}. "
            f"Verbose-mode temp Slack text: {verbose_mode_text!r}. "
            f"Brick-grain Slack text: {brick_grain_text!r}. "
            f"Disposition Slack text: {disposition_text!r}. "
            f"{dashboard_project_ref_text} "
            f"{structure_diagram_text} "
            f"Temp local inbox packet bytes: {len(auto_wire_inbox_text.encode('utf-8'))}."
        ),
    )


def _run_reporter_notification_projection_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "read_side_projection_boundary",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_reporter_notification_projection(repo: Path) -> KernelResult:"
    poisoned = "def run_reporter_notification_projection_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError("reporter_notification_projection mutation probe could not find entrypoint")

    backup = tempfile.NamedTemporaryFile(
        prefix=".reporter-notification-projection-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_reporter_notification_projection_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "reporter_notification_projection mutation probe did not turn profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_reporter_notification_projection_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "reporter_notification_projection mutation probe restored source but "
            f"read_side_projection_boundary remained RED:\n{excerpt}"
        )

    return [
        "reporter notification projection mutation RED probe passed: disabling "
        "the moved run_reporter_notification_projection entrypoint made "
        "check_profile.py --profile read_side_projection_boundary exit non-zero, "
        "then restoring the temp-backed self file returned "
        "read_side_projection_boundary to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for reporter notification projection."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved "
            "run_reporter_notification_projection entrypoint, assert "
            "read_side_projection_boundary profile exits RED, restore from a "
            "temp backup, then assert read_side_projection_boundary GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = (
            probe_mutation_red(repo)
            if args.probe_mutation_red
            else [run_reporter_notification_projection(repo).output]
        )
    except ProfileError as exc:
        print("reporter notification projection rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

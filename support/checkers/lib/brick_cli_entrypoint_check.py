"""Brick CLI entrypoint kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes customer-facing CLI entrypoint behavior; it owns no axis crossing,
decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import contextlib
import inspect
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
)

_BRICK_CLI_ENTRYPOINT_TIMEOUT_SECONDS = 30


def _assert_brick_cli_probe(
    label: str, completed: subprocess.CompletedProcess[str]
) -> dict[str, Any]:
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if "Traceback" in stderr or "ModuleNotFoundError" in stderr:
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} crashed at startup:\n"
            + stderr.strip()
        )
    if completed.returncode != 0:
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} exited {completed.returncode}.\n"
            f"stdout:\n{stdout.strip()}\nstderr:\n{stderr.strip()}"
        )
    try:
        packet = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} did not emit JSON status evidence.\n"
            f"stdout:\n{stdout.strip()}\nstderr:\n{stderr.strip()}"
        ) from exc
    if not isinstance(packet, dict) or packet.get("command") != "status":
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} emitted unexpected packet: {packet!r}"
        )
    return packet


def _assert_brick_cli_customer_task_intent(cli: Any, repo: Path) -> int:
    from brick_protocol.support.operator.composition_intent import materialize_building_intent

    parser = cli.build_parser()
    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    if len(subparser_actions) != 1:
        raise ProfileError("brick_cli_entrypoint_smoke: CLI parser lost its public subparser action")
    public_commands = set(subparser_actions[0].choices)
    for forbidden_route in ("onboard", "onboard-module", "run_building_plan", "new-engine"):
        if forbidden_route in public_commands:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: internal/onboard route became public "
                f"CLI command {forbidden_route!r}"
            )

    with tempfile.TemporaryDirectory(prefix="bp-cli-status-home-") as home_tmp:
        old_home = os.environ.get("HOME")
        old_brick_home = os.environ.get("BRICK_HOME")
        try:
            os.environ["HOME"] = home_tmp
            os.environ.pop("BRICK_HOME", None)
            status_args = parser.parse_args(["status", "--json"])
            status_packet = cli._status_packet(status_args)
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home
            if old_brick_home is None:
                os.environ.pop("BRICK_HOME", None)
            else:
                os.environ["BRICK_HOME"] = old_brick_home
        expected_status_root = str(
            Path(home_tmp) / ".brick" / "project" / "brick-protocol" / "buildings"
        )
        legacy_status_root = str(Path(home_tmp) / ".brick" / "builds")
        if status_packet.get("default_evidence_root") != expected_status_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: status default_evidence_root must match "
                f"brick build default {expected_status_root}, got {status_packet!r}"
            )
        if status_packet.get("default_builds_root") != expected_status_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: status default_builds_root must stay "
                "classified as the same active build evidence root"
            )
        if status_packet.get("default_builds_root") == legacy_status_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: status revived legacy ~/.brick/builds"
            )

    # Retired raw-graph CLI coverage: the old positive dispatch test also
    # checked "customer graph_packet may not author Brick template-owned field"
    # and "plain CLI error leaked raw operator detail" paths. Those remain
    # internal driver/DSL concerns; the public CLI invariant is rejection.
    for retired_graph_flag in ("--graph-packet", "--graph"):
        graph_stderr = io.StringIO()
        try:
            with contextlib.redirect_stderr(graph_stderr):
                parser.parse_args(["build", retired_graph_flag, "graph.json"])
        except SystemExit:
            pass
        else:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: retired raw graph packet flag "
                f"{retired_graph_flag} is still accepted"
            )
        if "unrecognized arguments" not in graph_stderr.getvalue():
            raise ProfileError(
                "brick_cli_entrypoint_smoke: retired raw graph packet flag "
                f"{retired_graph_flag} was rejected with unexpected argparse output: "
                f"{graph_stderr.getvalue()!r}"
            )

    local_args = parser.parse_args(["build", "--task", "make x"])
    local_intent = cli._build_intent(local_args)
    if local_intent.get("selected_adapter_ref") != "adapter:local":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: local task default changed adapter "
            f"unexpectedly: {local_intent!r}"
        )
    if local_intent.get("chain_preset_ref") != cli.DEFAULT_LOCAL_PRESET_REF:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: local task default must keep onboarding "
            f"graph preset, got {local_intent!r}"
        )
    if "write_scope" in local_intent:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: local task default must not declare write_scope"
        )

    original_preflight_provider = cli.preflight_provider

    def set_preflight(rows_by_adapter: Mapping[str, Mapping[str, Any]]) -> None:
        def fake_preflight(adapter_ref: str) -> dict[str, Any]:
            row = dict(rows_by_adapter.get(adapter_ref, {}))
            row.setdefault("adapter_ref", adapter_ref)
            row.setdefault("installed", bool(row.get("ok")))
            row.setdefault("authed", "unknown")
            row.setdefault("message_ko", "checker synthetic readiness")
            return row

        cli.preflight_provider = fake_preflight

    try:
        set_preflight(
            {
                "adapter:claude-local": {"ok": True},
                "adapter:codex-local": {"ok": True},
                "adapter:gemini-local": {"ok": True},
            }
        )
        real_args = parser.parse_args(["build", "--task", "make x", "--real-provider"])
        real_intent = cli._build_intent(real_args)
        if real_intent.get("selected_adapter_ref") != "adapter:claude-local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: --real-provider omitted --adapter must "
                f"select first ready provider in declared order, got {real_intent!r}"
            )

        set_preflight(
            {
                "adapter:claude-local": {"ok": False, "installed": False},
                "adapter:codex-local": {"ok": False, "installed": False},
                "adapter:gemini-local": {
                    "ok": True,
                    "api_key_env_present": True,
                    "credential_validity": "not_proven",
                    "raw_secret": "SHOULD_NOT_APPEAR",
                },
            }
        )
        gemini_args = parser.parse_args(["build", "--task", "make x", "--real-provider"])
        gemini_intent = cli._build_intent(gemini_args)
        if gemini_intent.get("selected_adapter_ref") != "adapter:gemini-local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: --real-provider must select ready "
                f"adapter:gemini-local when it is the first ready provider, got {gemini_intent!r}"
            )
        if "adapter:gemini-api" in json.dumps(gemini_intent, sort_keys=True):
            raise ProfileError("brick_cli_entrypoint_smoke: gemini-api appeared in first-ready evidence")
        readiness_text = json.dumps(
            gemini_intent.get("provider_readiness_observations", []), sort_keys=True
        )
        if "SHOULD_NOT_APPEAR" in readiness_text or "raw_secret" in readiness_text:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: provider readiness evidence leaked raw credential data"
            )
        gemini_plan = materialize_building_intent(gemini_intent, repo_root=repo)
        gemini_step_adapters = {
            str(step.get("selected_adapter_ref") or "")
            for step in gemini_plan.get("brick_steps", [])
            if isinstance(step, Mapping)
        }
        if "adapter:gemini-local" not in gemini_step_adapters:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: selected adapter:gemini-local did not "
                f"flow into materialized work Brick rows: {gemini_step_adapters!r}"
            )

        set_preflight(
            {
                "adapter:claude-local": {"ok": True},
                "adapter:codex-local": {"ok": True},
                "adapter:gemini-local": {"ok": True},
            }
        )
        explicit_real_args = parser.parse_args(
            ["build", "--task", "make x", "--real-provider", "--adapter", "adapter:codex-local"]
        )
        explicit_real_intent = cli._build_intent(explicit_real_args)
        if explicit_real_intent.get("selected_adapter_ref") != "adapter:codex-local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit --adapter must win over "
                f"first-ready selection, got {explicit_real_intent!r}"
            )
        if explicit_real_intent.get("provider_readiness_observations"):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit --adapter must not record "
                "first-ready readiness observations"
            )

        set_preflight(
            {
                "adapter:claude-local": {"ok": False, "installed": False},
                "adapter:codex-local": {"ok": False, "installed": False},
                "adapter:gemini-local": {
                    "ok": False,
                    "installed": True,
                    "api_key_env_present": False,
                    "credential_validity": "not_proven",
                },
            }
        )
        no_ready_args = parser.parse_args(["build", "--task", "make x", "--real-provider"])
        no_ready_intent = cli._build_intent(no_ready_args)
        if no_ready_intent.get("selected_adapter_ref") != "adapter:local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: no ready real provider must fall back "
                f"to adapter:local, got {no_ready_intent!r}"
            )
        if "write_scope" in no_ready_intent:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: no-ready adapter:local fallback must not declare write_scope"
            )
    finally:
        cli.preflight_provider = original_preflight_provider

    real_intent = explicit_real_intent
    if real_intent.get("chain_preset_ref") != cli.DEFAULT_REAL_TASK_PRESET_REF:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: explicit real-provider task must default to "
            f"fast-fix, got {real_intent!r}"
        )
    write_scope = real_intent.get("write_scope")
    if not isinstance(write_scope, Mapping):
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --real-provider task must carry Brick write_scope"
        )
    if write_scope.get("allowed_paths") != ["."] or write_scope.get("forbidden_paths") != [".git/**"]:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --real-provider task write_scope must stay "
            f"worktree-bounded, got {write_scope!r}"
        )

    plan = materialize_building_intent(real_intent, repo_root=repo)
    work_rows = _brick_cli_work_brick_rows(plan)
    if not work_rows:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --real-provider task fast-fix plan emitted no work Brick"
        )
    scoped_rows = [
        row
        for row in work_rows
        if row.get("write_scope") == write_scope
        and row.get("requires_brick_write_scope") is True
    ]
    if not scoped_rows:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --real-provider task write_scope did not land "
            f"on a requires_brick_write_scope work Brick row: {work_rows!r}"
        )

    with tempfile.TemporaryDirectory(prefix="bp-cli-task-home-") as home_tmp:
        expected_root = str(Path(home_tmp) / ".brick" / "project" / "brick-protocol" / "buildings")
        task_call: dict[str, Any] = {}

        class FakeTaskResult:
            building_id = "cli-task-wrapper"
            isolation_mode = "worktree"
            isolation_reason = "checker synthetic"
            base_sha = "abc123"
            worktree_path = "/tmp/checker-task-worktree"
            evidence_root = expected_root + "/cli-task-wrapper"
            frontier_kind = "agent_incomplete"
            commit_sha = ""
            worktree_disposed = True
            intake_result = None

        original_task_runner = cli.run_customer_building_in_sandbox
        old_home = os.environ.get("HOME")
        try:
            os.environ["HOME"] = home_tmp

            def fake_task_runner(intent: Mapping[str, Any], **kwargs: Any) -> FakeTaskResult:
                task_call["intent"] = dict(intent)
                task_call["kwargs"] = dict(kwargs)
                return FakeTaskResult()

            cli.run_customer_building_in_sandbox = fake_task_runner
            task_build_args = parser.parse_args(
                [
                    "build",
                    "--task",
                    "task wrapper fixture",
                    "--preset",
                    cli.DEFAULT_LOCAL_PRESET_REF,
                    "--building-id",
                    "cli-task-wrapper",
                    "--json",
                ]
            )
            task_result = cli._run_build(task_build_args)
        finally:
            cli.run_customer_building_in_sandbox = original_task_runner
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

        legacy_home_root = str(Path(home_tmp) / ".brick" / "builds")
        if task_result.get("build_input_mode") != "preset_task":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task build did not expose "
                "build_input_mode=preset_task"
            )
        if task_result.get("output_root") != expected_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task default output_root must be "
                f"caller-local {expected_root}, got {task_result.get('output_root')!r}"
            )
        if task_result.get("output_root") == legacy_home_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task default revived legacy ~/.brick/builds"
            )
        if str(task_call.get("kwargs", {}).get("output_root")) != expected_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task wrapper dispatch did not "
                "receive the active Slack-facing vessel root"
            )
        if task_call.get("kwargs", {}).get("customer_repo_root") != repo:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task wrapper dispatch did not receive repo root"
            )
        if task_call.get("intent", {}).get("chain_preset_ref") != cli.DEFAULT_LOCAL_PRESET_REF:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task wrapper dispatch changed "
                f"the local preset intent: {task_call.get('intent')!r}"
            )

    with tempfile.TemporaryDirectory(prefix="bp-cli-task-explicit-") as tmp:
        explicit_root = Path(tmp) / "declared-output-root"
        explicit_call: dict[str, Any] = {}

        class FakeExplicitTaskResult:
            building_id = "cli-task-explicit"
            isolation_mode = "worktree"
            isolation_reason = "checker synthetic"
            base_sha = "abc123"
            worktree_path = "/tmp/checker-task-explicit-worktree"
            evidence_root = str(explicit_root / "cli-task-explicit")
            frontier_kind = "agent_incomplete"
            commit_sha = ""
            worktree_disposed = True
            intake_result = None

        original_task_runner = cli.run_customer_building_in_sandbox
        try:

            def fake_explicit_task_runner(
                intent: Mapping[str, Any],
                **kwargs: Any,
            ) -> FakeExplicitTaskResult:
                explicit_call["intent"] = dict(intent)
                explicit_call["kwargs"] = dict(kwargs)
                return FakeExplicitTaskResult()

            cli.run_customer_building_in_sandbox = fake_explicit_task_runner
            explicit_args = parser.parse_args(
                [
                    "build",
                    "--task",
                    "task explicit fixture",
                    "--building-id",
                    "cli-task-explicit",
                    "--output-root",
                    str(explicit_root),
                    "--json",
                ]
            )
            explicit_result = cli._run_build(explicit_args)
        finally:
            cli.run_customer_building_in_sandbox = original_task_runner

        if explicit_result.get("output_root") != str(explicit_root.resolve()):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit preset/task --output-root "
                f"did not win, got {explicit_result.get('output_root')!r}"
            )
        if str(explicit_call.get("kwargs", {}).get("output_root")) != str(explicit_root.resolve()):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit preset/task wrapper dispatch "
                "did not receive declared --output-root"
            )

    api_args = parser.parse_args(["build", "--task", "make x", "--adapter", "adapter:gemini-api"])
    try:
        cli._build_intent(api_args)
    except ValueError as exc:
        if "adapter_ref is not admitted" not in str(exc):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: retired adapter:gemini-api rejected "
                "with wrong reason"
            ) from exc
    else:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: retired adapter:gemini-api was accepted"
        )

    incomplete_packet = {
        "repo_root": str(repo),
        "building_id": "cli-frontier-not-ready-probe",
        "adapter_ref": "adapter:gemini-local",
        "chain_preset_ref": cli.DEFAULT_REAL_TASK_PRESET_REF,
        "isolation_mode": "worktree",
        "evidence_root": str(repo / "project" / "brick-protocol" / "buildings" / "probe"),
        "frontier_kind": "agent_incomplete",
        "customer_visible_frontier_state": cli._customer_visible_frontier_state("agent_incomplete"),
        "customer_visible_not_ready": True,
        "customer_visible_frontier_message": cli._customer_visible_frontier_message(
            "agent_incomplete"
        ),
        "proof_limits": list(cli.PROOF_LIMITS),
        "not_proven": list(cli.NOT_PROVEN),
    }
    rendered = cli._render_build(incomplete_packet)
    for required in (
        "frontier_kind: agent_incomplete",
        "customer_visible_frontier_state: not_ready",
        "customer_visible_not_ready: yes",
        "frontier_message: not ready:",
        "evidence_root",
    ):
        if required not in rendered:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: build render did not surface "
                f"non-ready frontier evidence fragment {required!r}; rendered={rendered!r}"
            )
    if cli._customer_visible_frontier_state("complete") != "frontier_complete":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: complete frontier must render frontier_complete"
        )
    if cli._customer_visible_frontier_state("agent_incomplete") != "not_ready":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: non-complete frontier must render not_ready"
        )

    large_stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(large_stderr):
            parser.parse_args(["build", "--large", "--task", "large fixture task"])
    except SystemExit:
        pass
    else:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --large became a public official build mode"
        )

    dev_lanes_stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(dev_lanes_stderr):
            parser.parse_args(["build", "--dev-lanes", "--task", "lane fixture task"])
    except SystemExit:
        pass
    else:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --dev-lanes became a public official build mode"
        )

    large_packet_builder = getattr(cli, "_p3_easy_large_graph_packet", None)
    if large_packet_builder is not None:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: hidden _p3_easy_large_graph_packet helper "
            "must stay absent/fail-closed; official input mode is preset_task"
        )

    lane_return_builder = getattr(cli, "lane_return", None)
    if lane_return_builder is not None:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: lane_return helper must stay absent/fail-closed; "
            "customer output is support evidence from brick build"
        )

    status_probe_args = parser.parse_args(["status", "--json"])
    status_probe = cli._status_packet(status_probe_args)
    boundary_matrix = status_probe.get("adapter_boundary_matrix")
    if not isinstance(boundary_matrix, Mapping):
        raise ProfileError(
            "brick_cli_entrypoint_smoke: status packet omitted adapter_boundary_matrix"
        )
    boundary_rows = boundary_matrix.get("rows")
    if not isinstance(boundary_rows, list) or len(boundary_rows) != len(cli.ALLOWED_ADAPTER_REFS):
        raise ProfileError(
            "brick_cli_entrypoint_smoke: adapter_boundary_matrix did not report "
            f"one row per admitted adapter: {boundary_matrix!r}"
        )
    boundary_text = json.dumps(boundary_matrix, sort_keys=True)
    for required_fragment in (
        "boundary_strength",
        "credential_path_class",
        "write_boundary",
        "adapter identity is not write authority",
        "not Movement authority",
    ):
        if required_fragment not in boundary_text:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: adapter_boundary_matrix lost "
                f"{required_fragment!r}: {boundary_matrix!r}"
            )
    rendered_status = cli._render_status(status_probe)
    if "adapter_boundary_matrix_rows:" not in rendered_status:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: status render omitted adapter boundary row count"
        )
    doctor_render = cli._render_doctor({"rows": [], "symptom_table": [], "adapter_boundary_matrix": boundary_matrix})
    if "adapter_boundary_matrix:" not in doctor_render:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: doctor render omitted adapter boundary matrix"
        )
    for observation_key in (
        "readiness_blocker_observation",
        "protocol_compliance_observation",
    ):
        observation = status_probe.get(observation_key)
        if not isinstance(observation, Mapping):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: status packet omitted support-only "
                f"{observation_key}"
            )
        observation_text = json.dumps(observation, sort_keys=True)
        for authority_fragment in (
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ):
            if authority_fragment not in observation_text:
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: support-only observation lost proof limit "
                    f"{authority_fragment!r}: {observation!r}"
                )

    bare_json_stdout = io.StringIO()
    with contextlib.redirect_stdout(bare_json_stdout):
        bare_json_exit = cli.main(["--json"])
    if bare_json_exit != 0:
        raise ProfileError("brick_cli_entrypoint_smoke: bare brick --json did not default to status")
    try:
        bare_json_packet = json.loads(bare_json_stdout.getvalue())
    except json.JSONDecodeError as exc:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: bare brick --json did not emit JSON status evidence"
        ) from exc
    if bare_json_packet.get("command") != "status":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: bare brick --json did not emit status packet: "
            f"{bare_json_packet!r}"
        )

    return 15


def _brick_cli_work_brick_rows(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    containers: list[Any] = []
    if isinstance(plan.get("steps"), list):
        containers.extend(plan.get("steps", []))
    if isinstance(plan.get("brick_steps"), list):
        containers.extend(plan.get("brick_steps", []))
    for container in containers:
        if not isinstance(container, Mapping):
            continue
        step_template_ref = container.get("step_template_ref")
        for row in container.get("rows", []):
            if (
                isinstance(row, Mapping)
                and row.get("axis") == "Brick"
                and step_template_ref == "building-step-template:work"
            ):
                rows.append(row)
    return rows


def _captured_verify_argv(cli: Any, args: argparse.Namespace) -> list[str]:
    captured: list[list[str]] = []
    original_main = cli.check_profile.main

    def fake_main(argv: Sequence[str] | None = None) -> int:
        captured.append(list(argv or []))
        return 0

    cli.check_profile.main = fake_main
    try:
        exit_code = cli._cmd_verify(args)
    finally:
        cli.check_profile.main = original_main
    if exit_code != 0 or len(captured) != 1:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: verify argv observation did not run "
            f"exactly once, exit={exit_code}, captured={captured!r}"
        )
    return captured[0]


def _assert_verify_argv(
    label: str,
    actual: Sequence[str],
    expected: Sequence[str],
) -> None:
    if list(actual) != list(expected):
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} verify argv drifted; "
            f"expected {list(expected)!r}, got {list(actual)!r}"
        )


def _assert_brick_cli_verify_layering(cli: Any, repo: Path) -> int:
    parser = cli.build_parser()
    expected_default = ["--repo", str(repo), "--profile", "core"]
    expected_all = ["--repo", str(repo), "--all"]

    default_args = parser.parse_args(["verify", "--repo", str(repo)])
    _assert_verify_argv(
        "plain brick verify",
        _captured_verify_argv(cli, default_args),
        expected_default,
    )

    alias_args = parser.parse_args(["check", "--repo", str(repo)])
    _assert_verify_argv(
        "brick check alias",
        _captured_verify_argv(cli, alias_args),
        expected_default,
    )

    all_args = parser.parse_args(["verify", "--repo", str(repo), "--all"])
    _assert_verify_argv(
        "explicit brick verify --all",
        _captured_verify_argv(cli, all_args),
        expected_all,
    )

    profile_args = parser.parse_args(["verify", "--repo", str(repo), "--profile", "core"])
    _assert_verify_argv(
        "explicit brick verify --profile",
        _captured_verify_argv(cli, profile_args),
        expected_default,
    )

    json_args = parser.parse_args(["verify", "--repo", str(repo), "--json"])
    json_stdout = io.StringIO()
    with contextlib.redirect_stdout(json_stdout):
        json_argv = _captured_verify_argv(cli, json_args)
    _assert_verify_argv("brick verify --json", json_argv, expected_default)
    try:
        json_packet = json.loads(json_stdout.getvalue())
    except json.JSONDecodeError as exc:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: brick verify --json did not emit JSON "
            f"while observing hermetic argv: {json_stdout.getvalue()!r}"
        ) from exc
    if json_packet.get("checker_argv") != expected_default:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: brick verify --json packet did not "
            f"carry hermetic checker_argv: {json_packet!r}"
        )

    helper = getattr(cli, "_hermetic_verify_argv", None)
    if not callable(helper) or helper(repo) != expected_default:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: _hermetic_verify_argv is missing or "
            f"not single-sourcing the default argv: {helper!r}"
        )
    init_source = inspect.getsource(cli._cmd_init)
    if "verify_argv = _hermetic_verify_argv(repo)" not in init_source:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: _cmd_init VERIFY step is not using "
            "the shared hermetic verify argv helper"
        )

    return 6


def run_brick_cli_entrypoint_smoke(repo: Path) -> KernelResult:
    """Bare-entrypoint smoke for the customer-facing ``brick`` CLI.

    The R1 trap is a console-script/import context launched from outside the repo
    with PYTHONPATH unset: the import-identity router can expose
    ``brick_protocol.*``, but existing transitive modules may still import bare
    ``support.*``. ``support/operator/cli.py`` must therefore insert BOTH the repo
    root and ``support/import_identity`` before importing support seams.
    """

    script = repo / "support" / "operator" / "cli.py"
    if not script.is_file():
        raise ProfileError(f"brick_cli_entrypoint_smoke could not find CLI script: {script}")

    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)
    clean_env["BRICK_CLI_ENTRYPOINT_REPO"] = str(repo)

    with tempfile.TemporaryDirectory(prefix="bp-cli-entrypoint-cwd-") as cwd:
        direct = subprocess.run(
            [
                sys.executable,
                str(script),
                "status",
                "--json",
                "--repo",
                str(repo),
            ],
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=cwd,
            timeout=_BRICK_CLI_ENTRYPOINT_TIMEOUT_SECONDS,
        )
        _assert_brick_cli_probe("direct script launch", direct)

        import_code = """
import os
import sys
from pathlib import Path

repo = Path(os.environ["BRICK_CLI_ENTRYPOINT_REPO"])
sys.path.insert(0, str(repo / "support" / "import_identity"))
import brick_protocol.support.operator.cli as cli
import support.operator.coo_operating_chain
raise SystemExit(cli.main(["status", "--json", "--repo", str(repo)]))
"""
        imported = subprocess.run(
            [sys.executable, "-c", import_code],
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=cwd,
            timeout=_BRICK_CLI_ENTRYPOINT_TIMEOUT_SECONDS,
        )
        _assert_brick_cli_probe("import-identity console-script simulation", imported)

    _ensure_import_identity(repo)
    cli = importlib.import_module("brick_protocol.support.operator.cli")
    inspected = (
        2
        + _assert_brick_cli_customer_task_intent(cli, repo)
        + _assert_brick_cli_verify_layering(cli, repo)
    )

    return KernelResult(
        check_id="brick_cli_entrypoint_smoke",
        inspected=inspected,
        output=(
            "brick CLI entrypoint smoke passed: direct script and import-identity "
            "console-script simulation ran from outside the repo with PYTHONPATH "
            "unset and emitted status JSON without ModuleNotFoundError; customer "
            "task intent defaults keep local runs read-only while --real-provider "
            "tasks materialize fast-fix with worktree-bounded Brick write_scope; "
            "plain verify/check and verify --json use the provider-free core "
            "profile while explicit --all preserves the full profile sweep"
        ),
    )


def _run_brick_cli_entrypoint_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "brick_cli_entrypoint",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _probe_verify_default_mutation_red(repo: Path) -> str:
    source = repo / "support" / "operator" / "cli.py"
    original = source.read_text(encoding="utf-8")
    needle = "verify_argv = _hermetic_verify_argv(repo)"
    poisoned = 'verify_argv = ["--repo", str(repo), "--all"]'
    if needle not in original:
        raise ProfileError(
            "brick_cli_entrypoint verify layering mutation probe could not find "
            "the hermetic verify default"
        )

    backup = tempfile.NamedTemporaryFile(
        prefix=".brick-cli-verify-layering.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_brick_cli_entrypoint_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "brick_cli_entrypoint verify layering mutation probe did not "
                "turn brick_cli_entrypoint profile RED after restoring the old "
                "--all default"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_brick_cli_entrypoint_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "brick_cli_entrypoint verify layering mutation probe restored "
            f"source but brick_cli_entrypoint remained RED:\n{excerpt}"
        )
    return (
        "brick CLI verify layering mutation RED probe passed: reintroducing "
        "the old plain-verify --all default made check_profile.py --profile "
        "brick_cli_entrypoint exit non-zero, then restoring the temp-backed "
        "CLI file returned brick_cli_entrypoint to exit 0."
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_brick_cli_entrypoint_smoke(repo: Path) -> KernelResult:"
    poisoned = "def run_brick_cli_entrypoint_smoke_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError(
            "brick_cli_entrypoint mutation probe could not find CLI entrypoint"
        )

    backup = tempfile.NamedTemporaryFile(
        prefix=".brick-cli-entrypoint-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_brick_cli_entrypoint_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "brick_cli_entrypoint mutation probe did not turn "
                "brick_cli_entrypoint profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_brick_cli_entrypoint_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "brick_cli_entrypoint mutation probe restored source but "
            f"brick_cli_entrypoint remained RED:\n{excerpt}"
        )

    return [
        "brick CLI entrypoint mutation RED probe passed: disabling the moved "
        "run_brick_cli_entrypoint_smoke entrypoint made check_profile.py "
        "--profile brick_cli_entrypoint exit non-zero, then restoring the "
        "temp-backed self file returned brick_cli_entrypoint to exit 0.",
        _probe_verify_default_mutation_red(repo),
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for the Brick CLI entrypoint."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved "
            "run_brick_cli_entrypoint_smoke entrypoint, assert "
            "brick_cli_entrypoint profile exits RED, restore from a temp "
            "backup, then assert brick_cli_entrypoint GREEN"
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
            else [run_brick_cli_entrypoint_smoke(repo).output]
        )
    except ProfileError as exc:
        print("brick CLI entrypoint check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

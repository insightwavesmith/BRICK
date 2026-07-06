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
        # build-unify #12 D2 (표17 casting convergence): the CLI no longer
        # synthesizes per-node casting. The selected adapter flows to the
        # PLAN-LEVEL selected_adapter_ref (the building default), and per-step
        # casting is interpreted at the SINGLE interpretation point (the
        # agent-object ladder), identically to a bare intent that carried no CLI
        # override. Pin: (1) no step_selection_overrides survive on the CLI
        # intent, (2) the selected adapter lands on the plan-level default, and
        # (3) the materialized step casting equals what the SAME intent WITHOUT
        # any CLI-authored casting produces (drift would mean the CLI is still
        # deciding the performer).
        if "step_selection_overrides" in gemini_intent:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: CLI intent must not synthesize "
                f"step_selection_overrides (표17 casting convergence): {gemini_intent!r}"
            )
        gemini_plan = materialize_building_intent(gemini_intent, repo_root=repo)
        if gemini_plan.get("selected_adapter_ref") != "adapter:gemini-local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: selected adapter:gemini-local did not "
                f"flow to the plan-level default: {gemini_plan.get('selected_adapter_ref')!r}"
            )
        gemini_step_casting = [
            (
                str(step.get("step_template_ref") or ""),
                str(step.get("selected_adapter_ref") or ""),
                str(step.get("selected_model_ref") or ""),
            )
            for step in gemini_plan.get("brick_steps", [])
            if isinstance(step, Mapping)
        ]
        ladder_only_intent = {
            key: value
            for key, value in gemini_intent.items()
            if key not in ("adapter_choice_basis", "provider_readiness_observations")
        }
        ladder_only_intent["building_id"] = "gemini-ladder-parity-probe"
        ladder_plan = materialize_building_intent(ladder_only_intent, repo_root=repo)
        ladder_step_casting = [
            (
                str(step.get("step_template_ref") or ""),
                str(step.get("selected_adapter_ref") or ""),
                str(step.get("selected_model_ref") or ""),
            )
            for step in ladder_plan.get("brick_steps", [])
            if isinstance(step, Mapping)
        ]
        if gemini_step_casting != ladder_step_casting:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: CLI --real-provider casting drifted from "
                "the single agent-object ladder interpretation point: "
                f"cli={gemini_step_casting!r} ladder={ladder_step_casting!r}"
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

    _assert_brick_cli_launch_repo_root_line(cli)
    _assert_brick_cli_casting_convergence(cli, repo)
    _assert_brick_cli_model_alias_loud()

    return 18


def _assert_brick_cli_launch_repo_root_line(cli: Any) -> None:
    """build-unify #12 D4 (표16): repo_root is the FIRST launch line + stale refusal."""

    parser = cli.build_parser()
    args = parser.parse_args(["build", "--task", "x"])
    # Behind-upstream without --allow-stale-repo -> refuse (non-zero) before walk.
    behind_stderr = io.StringIO()
    with contextlib.redirect_stderr(behind_stderr):
        refused = cli._emit_launch_repo_root_observation(
            args,
            {
                "repo_root": "/tmp/checker-repo",
                "repo_root_warnings": ["repo_root HEAD is behind origin/main by 2 commit(s)"],
                "repo_root_behind_count": "2",
                "repo_root_upstream_ref": "origin/main",
            },
        )
    if refused is None or refused == 0:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: behind-upstream launch must refuse without "
            "--allow-stale-repo (표16 stale-tree guard)"
        )
    if "refusing to launch" not in behind_stderr.getvalue():
        raise ProfileError(
            "brick_cli_entrypoint_smoke: stale-repo refusal did not name the refusal"
        )
    # --allow-stale-repo overrides the refusal and still prints repo_root first.
    allow_args = parser.parse_args(["build", "--task", "x", "--allow-stale-repo"])
    allow_stdout = io.StringIO()
    with contextlib.redirect_stdout(allow_stdout):
        allowed = cli._emit_launch_repo_root_observation(
            allow_args,
            {
                "repo_root": "/tmp/checker-repo",
                "repo_root_warnings": [],
                "repo_root_behind_count": "2",
            },
        )
    if allowed is not None:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --allow-stale-repo must let a behind launch proceed"
        )
    first_line = allow_stdout.getvalue().splitlines()[0] if allow_stdout.getvalue() else ""
    if not first_line.startswith("repo_root: "):
        raise ProfileError(
            "brick_cli_entrypoint_smoke: resolved repo_root must be the FIRST launch line, "
            f"got {first_line!r}"
        )
    # A fresh (not-behind) launch prints repo_root first and does not refuse.
    fresh_stdout = io.StringIO()
    with contextlib.redirect_stdout(fresh_stdout):
        fresh = cli._emit_launch_repo_root_observation(
            args,
            {"repo_root": "/tmp/checker-repo", "repo_root_warnings": [], "repo_root_behind_count": "0"},
        )
    if fresh is not None:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: up-to-date launch must not be refused"
        )
    if not fresh_stdout.getvalue().splitlines()[0].startswith("repo_root: "):
        raise ProfileError(
            "brick_cli_entrypoint_smoke: up-to-date launch lost its first repo_root line"
        )


def _assert_brick_cli_casting_convergence(cli: Any, repo: Path) -> None:
    """build-unify #12 D1/D2 (표17): CLI --preset intent = build_preset_intent, no override."""

    from brick_protocol.support.operator import onboard
    from brick_protocol.support.operator.composition_intent import materialize_building_intent

    parser = cli.build_parser()
    args = parser.parse_args(
        ["build", "--task", "converge x", "--adapter", "adapter:claude-local", "--building-id", "conv"]
    )
    cli_intent = cli._build_intent(args)
    if "step_selection_overrides" in cli_intent:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: CLI intent must not synthesize step_selection_overrides "
            f"(표17 casting convergence): {cli_intent!r}"
        )
    # D1: the shared builder produces the SAME confirmed intent as the CLI path.
    shared_intent = onboard.build_preset_intent(
        declared_by=args.declared_by,
        selected_adapter_ref="adapter:claude-local",
        chain_preset_ref=cli_intent["chain_preset_ref"],
        task_statement="converge x",
        building_id="conv",
        write_scope=cli_intent.get("write_scope"),
    )
    if cli_intent != shared_intent:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: CLI --preset intent drifted from the shared "
            f"build_preset_intent builder: cli={cli_intent!r} shared={shared_intent!r}"
        )
    # D2: per-step casting is the agent-object ladder, NOT the plan-level adapter.
    plan = materialize_building_intent(cli_intent, repo_root=repo)
    if plan.get("selected_adapter_ref") != "adapter:claude-local":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: CLI adapter must land on the plan-level default"
        )
    work_adapters = {
        str(step.get("selected_adapter_ref") or "")
        for step in plan.get("brick_steps", [])
        if isinstance(step, Mapping)
        and step.get("step_template_ref") == "building-step-template:work"
    }
    if work_adapters != {"adapter:codex-local"}:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: fast-fix work casting must resolve via the "
            f"agent-object ladder (dev->codex), not the CLI adapter: {work_adapters!r}"
        )


def _assert_brick_cli_model_alias_loud() -> None:
    """build-unify #12 D5 (표18): unadmitted model alias dies LOUDLY at normalization."""

    from brick_protocol.support.connection.adapter_model_casting import (
        _normalize_selected_model_ref,
    )

    # An admitted alias is PRESERVED (declared-alias observability contract intact).
    if _normalize_selected_model_ref("adapter:claude-local", "model:claude:sonnet") != "model:claude:sonnet":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: admitted model alias must be preserved on the "
            "declared ref (alias-vs-dispatched observability contract)"
        )
    # An unadmitted alias is rejected loudly (no silent account-default fallback).
    try:
        _normalize_selected_model_ref("adapter:claude-local", "model:claude:notareal")
    except ValueError:
        return
    raise ProfileError(
        "brick_cli_entrypoint_smoke: unadmitted model alias must be rejected loudly "
        "at normalization (표18 silent-evaporation guard)"
    )


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


def _source_replace_mutation_red(
    repo: Path,
    *,
    label: str,
    rel_path: str,
    needle: str,
    poisoned: str,
) -> str:
    """Poison ``needle`` -> ``poisoned`` in ``rel_path``, assert the profile goes RED, restore, GREEN.

    build-unify #12 D6 shared mutation-RED harness: a temp-backed edit to a
    source file must drive check_profile --profile brick_cli_entrypoint RED, then
    restoring the file must return it GREEN. Support evidence only.
    """

    source = repo / rel_path
    original = source.read_text(encoding="utf-8")
    if needle not in original:
        raise ProfileError(f"{label}: mutation needle not found in {rel_path}")
    backup = tempfile.NamedTemporaryFile(
        prefix=".brick-build-unify-mut.",
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
                f"{label}: mutation did not turn brick_cli_entrypoint profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)
    green = _run_brick_cli_entrypoint_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            f"{label}: restored source but brick_cli_entrypoint remained RED:\n{excerpt}"
        )
    return (
        f"{label} mutation RED probe passed: the mutation made "
        "check_profile.py --profile brick_cli_entrypoint exit non-zero, then "
        "restoring the temp-backed source returned it to exit 0."
    )


def probe_build_unify_mutation_red(repo: Path) -> list[str]:
    """build-unify #12 D6: the three declared mutation-RED probes.

    (1) 표17 casting convergence: re-introduce a per-node CLI casting override on
        the confirmed intent -> the convergence assertion + build_preset_intent
        parity go RED.
    (2) 표16 first launch line: neuter the first-line repo_root emit -> the D4
        launch-line assertion goes RED.
    (3) 표18 silent alias fallback: restore the quiet accept of an unadmitted
        alias at normalization -> the D5 loud-rejection assertion goes RED.
    """

    outputs = [
        _source_replace_mutation_red(
            repo,
            label="build-unify D2 casting convergence (표17)",
            rel_path="support/operator/onboard.py",
            needle='    if write_scope is not None:\n'
            '        intent["write_scope"] = dict(write_scope)',
            poisoned='    if write_scope is not None:\n'
            '        intent["write_scope"] = dict(write_scope)\n'
            '        intent["step_selection_overrides"] = {\n'
            '            "building-step-template:work": {\n'
            '                "selected_adapter_ref": selected_adapter_ref,\n'
            '                "selected_model_ref": "model:default",\n'
            "            }\n"
            "        }  # mutation: 표17 per-node casting synthesis reintroduced",
        ),
        _source_replace_mutation_red(
            repo,
            label="build-unify D4 first launch line (표16)",
            rel_path="support/operator/cli.py",
            needle='    print(f"repo_root: {repo_observation.get(\'repo_root\', \'\')}", file=stream)',
            poisoned='    pass  # mutation: first repo_root launch line removed',
        ),
        _source_replace_mutation_red(
            repo,
            label="build-unify D5 model-alias loud rejection (표18)",
            rel_path="support/connection/adapter_model_casting.py",
            needle="    resolve_model_alias_ref(adapter_ref, selected_model_ref)\n"
            "    return selected_model_ref",
            poisoned="    return selected_model_ref  # mutation: quiet alias fallback restored",
        ),
    ]
    return outputs


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
        *probe_build_unify_mutation_red(repo),
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

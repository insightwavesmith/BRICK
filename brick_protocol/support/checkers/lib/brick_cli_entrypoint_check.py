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

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.checkers.lib.yaml_subset import (
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


def _assert_brick_cli_authoring_funnel(cli: Any, repo: Path) -> int:
    """Pin task triage, direct quick cases, authoring, and confirmed-call dispatch."""

    parser = cli.build_parser()
    untriaged = parser.parse_args(
        ["build", "--task", "untriaged write task", "--adapter", "adapter:codex-local"]
    )
    try:
        cli._build_request(untriaged)
    except ValueError as exc:
        error_text = str(exc)
        if "explicit --preset" not in error_text or "--building-case" not in error_text:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: untriaged task refusal omitted explicit "
                f"preset/triage advisory: {error_text!r}"
            ) from exc
        public_error = cli._public_error_packet(untriaged, exc)
        if public_error.get("public_error_code") != "build_triage_required":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: untriaged refusal lost its public error code"
            )
        advisory = public_error.get("advisory")
        if not isinstance(advisory, Mapping) or advisory.get("selection_rule") != (
            "caller_or_coo_declared_only"
        ):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: untriaged refusal lost caller/COO advisory evidence"
            )
    else:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: task without --preset or explicit triage "
            "did not fail closed"
        )

    explicit_preset = parser.parse_args(
        [
            "build",
            "--task",
            "explicit preset task",
            "--preset",
            "building-chain-preset:fast-fix",
            "--fast-confirm",
        ]
    )
    explicit_intent, explicit_route = cli._build_request(explicit_preset)
    if explicit_route.get("build_input_mode") != "direct_preset":
        raise ProfileError("brick_cli_entrypoint_smoke: confirmed quick --preset lost direct_preset mode")
    if explicit_intent.get("chain_preset_ref") != "building-chain-preset:fast-fix":
        raise ProfileError("brick_cli_entrypoint_smoke: explicit --preset was not preserved")

    missing_quick_confirmation = parser.parse_args(
        [
            "build",
            "--task",
            "unconfirmed quick preset",
            "--preset",
            "building-chain-preset:quick-check",
        ]
    )
    try:
        cli._build_request(missing_quick_confirmation)
    except ValueError as exc:
        if "--fast-confirm" not in str(exc):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: unconfirmed quick preset refusal lost "
                "its explicit confirmation instruction"
            ) from exc
    else:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: quick preset launched without --fast-confirm"
        )

    non_quick_preset = parser.parse_args(
        [
            "build",
            "--task",
            "non-quick preset must be reviewed",
            "--preset",
            "building-chain-preset:app-feature-basic",
        ]
    )
    non_quick_intent, non_quick_route = cli._build_request(non_quick_preset)
    if non_quick_route.get("build_input_mode") != "building_call_authoring":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: non-quick explicit preset bypassed order authoring"
        )
    if non_quick_intent.get("chain_preset_ref") != cli.BUILDING_CALL_AUTHORING_PRESET_REF:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: non-quick explicit preset did not lower to "
            "building-call-authoring"
        )
    if non_quick_route.get("requested_preset_ref") != "building-chain-preset:app-feature-basic":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: authoring redirect lost requested preset evidence"
        )

    direct_cases = (
        ("quick_fix", "building-chain-preset:fast-fix", False),
        ("quick_check", "building-chain-preset:quick-check", False),
    )
    for building_case, expected_preset, expect_write_scope in direct_cases:
        direct_args = parser.parse_args(
            [
                "build",
                "--task",
                f"direct {building_case} fixture",
                "--building-case",
                building_case,
                "--intensity",
                "easy",
                "--direct-preset",
                "--fast-confirm",
            ]
        )
        direct_intent, direct_route = cli._build_request(direct_args)
        if direct_route.get("build_input_mode") != "direct_preset":
            raise ProfileError(
                f"brick_cli_entrypoint_smoke: {building_case} did not use direct_preset mode"
            )
        if direct_intent.get("chain_preset_ref") != expected_preset:
            raise ProfileError(
                f"brick_cli_entrypoint_smoke: {building_case} lowered to wrong preset: "
                f"{direct_intent!r}"
            )
        has_write_scope = isinstance(direct_intent.get("write_scope"), Mapping)
        if has_write_scope is not expect_write_scope:
            raise ProfileError(
                f"brick_cli_entrypoint_smoke: {building_case} write_scope admission drifted: "
                f"{direct_intent!r}"
            )

    forbidden_direct = parser.parse_args(
        [
            "build",
            "--task",
            "standard delivery cannot bypass authoring",
            "--building-case",
            "standard_delivery",
            "--intensity",
            "normal",
            "--direct-preset",
            "--fast-confirm",
        ]
    )
    try:
        cli._build_request(forbidden_direct)
    except ValueError:
        pass
    else:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: non-quick building_case bypassed authoring via direct_preset"
        )

    rejected_cli_shapes = (
        ["build", "--task", "missing intensity", "--building-case", "quick_fix"],
        [
            "build",
            "--task",
            "missing fast confirm",
            "--building-case",
            "quick_fix",
            "--intensity",
            "easy",
            "--direct-preset",
        ],
        [
            "build",
            "--task",
            "conflicting authoring forms",
            "--preset",
            "building-chain-preset:fast-fix",
            "--building-case",
            "quick_fix",
            "--intensity",
            "easy",
        ],
    )
    for argv in rejected_cli_shapes:
        try:
            cli._build_request(parser.parse_args(argv))
        except ValueError:
            continue
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: ambiguous/incomplete authoring shape was accepted: {argv!r}"
        )

    dispatch_calls: list[dict[str, Any]] = []

    class FakeBuildResult:
        building_id = "cli-authoring-funnel"
        isolation_mode = "worktree"
        isolation_reason = "checker synthetic"
        base_sha = "abc123"
        worktree_path = "/tmp/checker-authoring-funnel"
        evidence_root = "/tmp/checker-authoring-funnel/evidence"
        frontier_kind = "agent_incomplete"
        commit_sha = ""
        worktree_disposed = False
        intake_result = None

    original_runner = cli.run_customer_building_in_sandbox
    try:
        def fake_runner(intent: Mapping[str, Any], **kwargs: Any) -> FakeBuildResult:
            dispatch_calls.append({"intent": dict(intent), "kwargs": dict(kwargs)})
            return FakeBuildResult()

        cli.run_customer_building_in_sandbox = fake_runner
        for intensity in ("normal", "complex", "critical"):
            authoring_args = parser.parse_args(
                [
                    "build",
                    "--task",
                    f"{intensity} authoring fixture",
                    "--building-case",
                    "standard_delivery",
                    "--intensity",
                    intensity,
                    "--timeout",
                    "900",
                ]
            )
            authoring_packet = cli._run_build(authoring_args)
            if authoring_packet.get("build_input_mode") != "building_call_authoring":
                raise ProfileError(
                    f"brick_cli_entrypoint_smoke: {intensity} triage did not run authoring Building"
                )
            if dispatch_calls[-1]["intent"].get("chain_preset_ref") != (
                "building-chain-preset:building-call-authoring"
            ):
                raise ProfileError(
                    f"brick_cli_entrypoint_smoke: {intensity} triage did not dispatch "
                    "building-call-authoring preset"
                )

        confirmed_path = (
            repo
            / "brick_protocol/support/checkers/fixtures/building_call_lowering/positive_confirmed_request.json"
        )
        confirmed_args = parser.parse_args(
            [
                "build",
                "--building-call",
                str(confirmed_path),
                "--timeout",
                "900",
            ]
        )
        confirmed_packet = cli._run_build(confirmed_args)
    finally:
        cli.run_customer_building_in_sandbox = original_runner
    if confirmed_packet.get("build_input_mode") != "confirmed_building_call":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: confirmed Building Call did not expose its input mode"
        )
    confirmed_intent = dispatch_calls[-1]["intent"]
    if confirmed_intent.get("chain_preset_ref") != "building-chain-preset:app-feature-inspected":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: confirmed Building Call was not canonically lowered"
        )
    if confirmed_intent.get("selected_adapter_ref") != "adapter:local":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: confirmed Building Call lost the CLI-declared adapter binding"
        )
    if len(dispatch_calls) != 4:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: authoring/confirmed modes did not converge on one "
            f"sandbox dispatch seam: {dispatch_calls!r}"
        )
    graph_compat = parser.parse_args(["build", "--graph-decl", "compat-graph.yaml"])
    if graph_compat.graph_decl != "compat-graph.yaml":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --graph-decl compatibility transport was removed"
        )
    return 17


def _assert_brick_cli_recovery_handle_lift(cli: Any, repo: Path) -> int:
    """Pin preset/graph/resume recovery handles through their CLI packets.

    The provider/approval bodies are replaced with deterministic checker facts;
    packet construction and resume-result lowering remain the production code.
    Every filesystem path and HOME used here belongs to the isolated fixture.
    """

    from types import SimpleNamespace

    schema = {
        "ref",
        "sha",
        "base",
        "resume_command",
        "worktree_path",
        "preservation_state",
    }

    def assert_lift(label: str, packet: Mapping[str, Any], expected: Mapping[str, str]) -> None:
        raw = packet.get("recovery_handle")
        if not isinstance(raw, Mapping):
            raise ProfileError(
                f"brick_cli_entrypoint_smoke: {label} omitted recovery_handle mapping"
            )
        lifted = dict(raw)
        if set(lifted) != schema:
            raise ProfileError(
                f"brick_cli_entrypoint_smoke: {label} recovery_handle schema drifted: "
                f"{sorted(lifted)}"
            )
        if lifted != dict(expected):
            raise ProfileError(
                f"brick_cli_entrypoint_smoke: {label} recovery_handle changed while "
                f"lifting into the CLI packet: expected={dict(expected)!r} got={lifted!r}"
            )

    with tempfile.TemporaryDirectory(prefix="bp-cli-recovery-handle-") as raw:
        root = Path(raw)
        customer = root / "customer"
        customer.mkdir()
        (customer / "tracked.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(customer), "init", "-q"], check=True, timeout=30)
        subprocess.run(["git", "-C", str(customer), "add", "tracked.txt"], check=True, timeout=30)
        subprocess.run(
            [
                "git",
                "-C",
                str(customer),
                "-c",
                "user.name=cli-recovery-checker",
                "-c",
                "user.email=cli-recovery@brick.local",
                "commit",
                "-q",
                "-m",
                "seed recovery CLI fixture",
            ],
            check=True,
            timeout=30,
        )
        base = subprocess.run(
            ["git", "-C", str(customer), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        output_root = root / "buildings"
        home = root / "home"
        home.mkdir()
        parser = cli.build_parser()
        old_home = os.environ.get("HOME")
        try:
            os.environ["HOME"] = str(home)

            # Preset packet lifts the exact handle attached to the shared
            # CustomerSandboxRunResult.
            preset_handle = {
                "ref": "refs/brick/wip/cli-r8-preset",
                "sha": "1" * 40,
                "base": base,
                "resume_command": "brick resume --decl preset-resume.json",
                "worktree_path": "",
                "preservation_state": "wip_commit_verified",
            }
            preset_result = SimpleNamespace(
                building_id="cli-r8-preset",
                isolation_mode="worktree",
                isolation_reason="checker synthetic result",
                base_sha=base,
                worktree_path="",
                evidence_root=str(output_root / "cli-r8-preset"),
                frontier_kind="agent_incomplete",
                commit_sha="",
                wip_anchor_ref=preset_handle["ref"],
                wip_commit_sha=preset_handle["sha"],
                recovery_handle=preset_handle,
                worktree_disposed=True,
                intake_result=None,
            )
            original_runner = cli.run_customer_building_in_sandbox
            try:
                cli.run_customer_building_in_sandbox = (
                    lambda _intent, **_kwargs: preset_result
                )
                preset_args = parser.parse_args(
                    [
                        "build",
                        "--task",
                        "recovery handle preset fixture",
                        "--preset",
                        cli.QUICK_CHECK_PRESET_REF,
                        "--fast-confirm",
                        "--building-id",
                        "cli-r8-preset",
                        "--repo",
                        str(customer),
                        "--output-root",
                        str(output_root),
                        "--json",
                    ]
                )
                preset_packet = cli._run_build(preset_args)
            finally:
                cli.run_customer_building_in_sandbox = original_runner
            assert_lift("preset packet", preset_packet, preset_handle)

            # Graph-declaration packet must lift the same handle from the
            # approval result; approval_result remains a byte-for-value witness.
            graph_handle = {
                "ref": "refs/brick/wip/cli-r8-graph",
                "sha": "2" * 40,
                "base": base,
                "resume_command": "brick resume --decl graph-resume.json",
                "worktree_path": "",
                "preservation_state": "wip_commit_verified",
            }
            graph_decl = root / "graph-declaration.json"
            graph_decl.write_text("{}\n", encoding="utf-8")
            proposal = output_root / "cli-r8-graph" / "declared-building-plan.json"
            proposal.parent.mkdir(parents=True)
            proposal.write_text('{"brick_steps": []}\n', encoding="utf-8")
            approval = {
                "ok": False,
                "ran": True,
                "evidence_root": str(output_root / "cli-r8-graph"),
                "frontier_kind": "agent_incomplete",
                "isolation_mode": "worktree",
                "isolation_reason": "checker synthetic approval",
                "base_sha": base,
                "worktree_path": "",
                "worktree_disposed": True,
                "commit_sha": "",
                "wip_anchor_ref": graph_handle["ref"],
                "wip_commit_sha": graph_handle["sha"],
                "recovery_handle": graph_handle,
            }
            composed = SimpleNamespace(
                building_id="cli-r8-graph",
                declared_by="coo:cli-recovery-checker",
                selected_adapter_ref="adapter:local",
                selected_model_ref="model:default",
                composed_plan={"plan_shape": "graph"},
            )
            graph_patches = {
                "load_graph_declaration": cli.load_graph_declaration,
                "assemble_graph_declaration": cli.assemble_graph_declaration,
                "graph_declaration_output_root": cli.graph_declaration_output_root,
                "persist_proposed_building_graph": cli.persist_proposed_building_graph,
                "resolve_build_action": cli.resolve_build_action,
                "graph_declaration_timeout": cli.graph_declaration_timeout,
                "graph_declaration_author_ref": cli.graph_declaration_author_ref,
                "run_goal_approve_entry": cli.run_goal_approve_entry,
            }
            try:
                cli.load_graph_declaration = lambda _path: {"checker": True}
                cli.assemble_graph_declaration = lambda _decl, **_kwargs: composed
                cli.graph_declaration_output_root = lambda _decl: str(output_root)
                cli.persist_proposed_building_graph = (
                    lambda _composed, _output, **_kwargs: proposal
                )
                cli.resolve_build_action = lambda **_kwargs: {
                    "action": "stop",
                    "basis": "checker-declared",
                }
                cli.graph_declaration_timeout = lambda _decl, _timeout: 30
                cli.graph_declaration_author_ref = (
                    lambda _decl: "coo:cli-recovery-checker"
                )
                cli.run_goal_approve_entry = lambda *_args, **_kwargs: dict(approval)
                graph_args = parser.parse_args(
                    [
                        "build",
                        "--graph-decl",
                        str(graph_decl),
                        "--repo",
                        str(customer),
                        "--output-root",
                        str(output_root),
                        "--json",
                    ]
                )
                graph_packet = cli._run_build(graph_args)
            finally:
                for name, original in graph_patches.items():
                    setattr(cli, name, original)
            assert_lift("graph packet", graph_packet, graph_handle)
            if graph_packet.get("approval_result", {}).get("recovery_handle") != graph_handle:
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: graph packet disagreed with its "
                    "underlying approval_result recovery_handle"
                )

            # Resume result lowering is production run_resume_declaration; only
            # its preflight and already-authorized approval body are fixture facts.
            resume_module = cli.resume_declaration
            resume_handle = {
                "ref": "",
                "sha": "3" * 40,
                "base": "2" * 40,
                "resume_command": "",
                "worktree_path": "",
                "preservation_state": "landed_commit_verified",
            }
            resume_decl = root / "resume-declaration.json"
            resume_decl_payload = {
                "building_ref": str(output_root / "cli-r8-resume"),
                "dispositions": [{"on": "agent_incomplete", "action": "forward"}],
                "chain": "single",
                "author_ref": "coo:cli-recovery-checker",
            }
            resume_decl.write_text(
                json.dumps(resume_decl_payload, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            original_preflight = resume_module.preflight_resume_declaration
            original_approve = resume_module._run_approve_entry
            try:
                resume_module.preflight_resume_declaration = lambda *_args, **_kwargs: {
                    "frontier_kind": "agent_incomplete",
                    "frontier_reason": "checker hold",
                    "paused_at_ref": "link-transition:cli-r8-resume",
                    "matched": True,
                    "selected_disposition": {
                        "on": "agent_incomplete",
                        "action": "forward",
                    },
                }
                resume_module._run_approve_entry = lambda *_args, **_kwargs: {
                    "ok": True,
                    "ran": True,
                    "frontier_kind": "complete",
                    "recovery_handle": dict(resume_handle),
                }
                resume_result = resume_module.run_resume_declaration(
                    resume_decl_payload,
                    repo_root=customer,
                )
            finally:
                resume_module.preflight_resume_declaration = original_preflight
                resume_module._run_approve_entry = original_approve
            assert_lift("resume result", resume_result, resume_handle)
            rounds = resume_result.get("rounds")
            if not isinstance(rounds, list) or not rounds or (
                rounds[0].get("recovery_handle") != resume_handle
            ):
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: resume result disagreed with its "
                    "underlying approval round recovery_handle"
                )

            original_run_resume = resume_module.run_resume_declaration
            original_emit = cli._emit_launch_repo_root_observation
            try:
                resume_module.run_resume_declaration = (
                    lambda *_args, **_kwargs: dict(resume_result)
                )
                cli._emit_launch_repo_root_observation = lambda *_args, **_kwargs: None
                resume_args = parser.parse_args(
                    [
                        "resume",
                        "--decl",
                        str(resume_decl),
                        "--repo",
                        str(customer),
                        "--json",
                    ]
                )
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    resume_exit = cli._cmd_resume(resume_args)
                resume_packet = json.loads(stdout.getvalue())
            finally:
                resume_module.run_resume_declaration = original_run_resume
                cli._emit_launch_repo_root_observation = original_emit
            if resume_exit != 0:
                raise ProfileError(
                    f"brick_cli_entrypoint_smoke: resume recovery fixture exited {resume_exit}"
                )
            assert_lift("resume CLI packet", resume_packet, resume_handle)
        finally:
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home
    return 4


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

    local_args = parser.parse_args(
        [
            "build",
            "--task",
            "make x",
            "--preset",
            cli.FAST_FIX_PRESET_REF,
            "--fast-confirm",
        ]
    )
    local_intent = cli._build_intent(local_args)
    if local_intent.get("selected_adapter_ref") != "adapter:local":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: local task default changed adapter "
            f"unexpectedly: {local_intent!r}"
        )
    if local_intent.get("chain_preset_ref") != cli.FAST_FIX_PRESET_REF:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: confirmed local quick task changed preset, "
            f"got {local_intent!r}"
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
        missing_declaration_args = parser.parse_args(
            [
                "build",
                "--task",
                "make x",
                "--preset",
                cli.FAST_FIX_PRESET_REF,
                "--fast-confirm",
                "--real-provider",
            ]
        )
        try:
            cli._build_intent(missing_declaration_args)
        except cli.ProviderReadinessStopError as exc:
            missing_packet = cli._public_error_packet(missing_declaration_args, exc)
            stop = missing_packet.get("provider_readiness_stop", {})
            if (
                missing_packet.get("public_error_code") != "provider_readiness_stop"
                or stop.get("reason") != "explicit_adapter_required"
                or stop.get("execution_started") is not False
                or stop.get("substitution_performed") is not False
            ):
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: missing real-provider declaration "
                    f"lost typed pre-dispatch stop evidence: {missing_packet!r}"
                )
        else:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: --real-provider without --adapter did not fail closed"
            )

        set_preflight({"adapter:codex-local": {"ok": True}})
        explicit_real_args = parser.parse_args(
            [
                "build",
                "--task",
                "make x",
                "--preset",
                cli.FAST_FIX_PRESET_REF,
                "--fast-confirm",
                "--real-provider",
                "--adapter",
                "adapter:codex-local",
            ]
        )
        explicit_real_intent = cli._build_intent(explicit_real_args)
        if explicit_real_intent.get("selected_adapter_ref") != "adapter:codex-local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit provider declaration changed, "
                f"got {explicit_real_intent!r}"
            )
        observations = explicit_real_intent.get("provider_readiness_observations")
        if not isinstance(observations, list) or not observations or (
            observations[0].get("adapter_ref") != "adapter:codex-local"
        ):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: declared provider readiness evidence was omitted"
            )

        set_preflight(
            {
                "adapter:codex-local": {"ok": False, "installed": False},
                "adapter:gemini-local": {
                    "ok": True,
                    "installed": True,
                    "api_key_env_present": True,
                    "credential_validity": "not_proven",
                    "raw_secret": "SHOULD_NOT_APPEAR",
                },
            }
        )
        try:
            cli._build_intent(explicit_real_args)
        except cli.ProviderReadinessStopError as exc:
            no_ready_packet = cli._public_error_packet(explicit_real_args, exc)
        else:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: unready declared adapter was silently "
                "replaced by another ready provider"
            )
        readiness_text = json.dumps(no_ready_packet, sort_keys=True)
        stop = no_ready_packet.get("provider_readiness_stop", {})
        if (
            stop.get("adapter_ref") != "adapter:codex-local"
            or stop.get("reason") != "declared_adapter_not_ready"
            or stop.get("execution_started") is not False
            or stop.get("substitution_performed") is not False
            or "adapter:gemini-local" in readiness_text
        ):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: unready declared adapter typed stop drifted: "
                f"{no_ready_packet!r}"
            )
        if "SHOULD_NOT_APPEAR" in readiness_text or "raw_secret" in readiness_text:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: provider readiness stop leaked raw credential data"
            )
    finally:
        cli.preflight_provider = original_preflight_provider

    real_intent = explicit_real_intent
    if real_intent.get("chain_preset_ref") != cli.FAST_FIX_PRESET_REF:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: explicit real-provider preset must preserve "
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
                    cli.FAST_FIX_PRESET_REF,
                    "--fast-confirm",
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
        if task_result.get("build_input_mode") != "direct_preset":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: confirmed quick preset/task build did not "
                "expose build_input_mode=direct_preset"
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
        if task_call.get("intent", {}).get("chain_preset_ref") != cli.FAST_FIX_PRESET_REF:
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
                    "--preset",
                    cli.FAST_FIX_PRESET_REF,
                    "--fast-confirm",
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

    api_args = parser.parse_args(
        [
            "build",
            "--task",
            "make x",
            "--preset",
            cli.FAST_FIX_PRESET_REF,
            "--fast-confirm",
            "--adapter",
            "adapter:gemini-api",
        ]
    )
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
        "chain_preset_ref": cli.FAST_FIX_PRESET_REF,
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
        [
            "build",
            "--task",
            "converge x",
            "--preset",
            cli.FAST_FIX_PRESET_REF,
            "--fast-confirm",
            "--adapter",
            "adapter:claude-local",
            "--building-id",
            "conv",
        ]
    )
    original_preflight = cli.preflight_provider
    try:
        cli.preflight_provider = lambda adapter_ref: {
            "adapter_ref": adapter_ref,
            "ok": True,
            "installed": True,
            "authed": "checker-synthetic",
        }
        cli_intent = cli._build_intent(args)
    finally:
        cli.preflight_provider = original_preflight
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
        adapter_choice_basis=cli_intent.get("adapter_choice_basis", ""),
        provider_readiness_observations=cli_intent.get(
            "provider_readiness_observations"
        ),
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


def _assert_brick_cli_timeout_and_review_packet(cli: Any, repo: Path) -> int:
    """Pin visible timeout resolution, pre-dispatch stops, and casting review rows."""

    from types import SimpleNamespace
    from brick_protocol.support.operator.plan_rendering import (
        DeclaredPerformerUnavailableError,
    )

    parser = cli.build_parser()
    calls: list[dict[str, Any]] = []
    original_runner = cli.run_customer_building_in_sandbox
    original_preflight = cli.preflight_provider

    default_init = parser.parse_args(["init"])
    if default_init.example_adapter != cli.onboard.EXAMPLE_DECLARED_ADAPTER_REF:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: init did not expose the bundled example's "
            "stable adapter declaration"
        )
    explicit_init = parser.parse_args(
        ["init", "--example-adapter", "adapter:codex-local"]
    )
    if explicit_init.example_adapter != "adapter:codex-local":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: init rewrote the explicit example adapter"
        )

    with tempfile.TemporaryDirectory(prefix="bp-cli-timeout-review-") as raw:
        root = Path(raw)
        plan_path = root / "declared-building-plan.json"
        casting_row = {
            "step_ref": "building-step:timeout-review-work",
            "step_template_ref": "building-step-template:work",
            "selected_adapter_ref": "adapter:codex-local",
            "selected_model_ref": "model:codex:default",
            "selected_reasoning_effort_ref": "effort:xhigh",
        }
        plan_path.write_text(
            json.dumps({"brick_steps": [casting_row]}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        intake = SimpleNamespace(
            plan_path=plan_path,
            plan_shape="chain",
            walker_mode="single",
            walker_mode_basis="checker synthetic",
        )

        class FakeResult:
            building_id = "cli-timeout-review"
            isolation_mode = "worktree"
            isolation_reason = "checker synthetic"
            base_sha = "a" * 40
            worktree_path = str(root / "worktree")
            evidence_root = str(root / "evidence")
            frontier_kind = "agent_incomplete"
            commit_sha = ""
            worktree_disposed = False
            intake_result = intake

        def fake_runner(intent: Mapping[str, Any], **kwargs: Any) -> FakeResult:
            calls.append({"intent": dict(intent), "kwargs": dict(kwargs)})
            return FakeResult()

        try:
            cli.run_customer_building_in_sandbox = fake_runner
            cli.preflight_provider = lambda adapter_ref: {
                "adapter_ref": adapter_ref,
                "ok": True,
                "installed": True,
                "authed": "checker-synthetic",
            }

            quick_args = parser.parse_args(
                [
                    "build",
                    "--task",
                    "quick timeout fixture",
                    "--preset",
                    cli.QUICK_CHECK_PRESET_REF,
                    "--fast-confirm",
                    "--output-root",
                    str(root / "quick-output"),
                ]
            )
            quick_packet = cli._run_build(quick_args)
            if (
                calls[-1]["kwargs"].get("adapter_timeout_seconds") != 120
                or quick_packet.get("resolved_timeout_seconds") != 120
                or quick_packet.get("timeout_basis") != "local_default"
            ):
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: local/quick timeout did not resolve "
                    f"visibly to 120 seconds: {quick_packet!r} calls={calls!r}"
                )
            if quick_packet.get("resolved_casting_table") != [casting_row]:
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: review packet omitted resolved node "
                    f"casting table: {quick_packet!r}"
                )

            non_quick_argv = [
                "build",
                "--task",
                "non-quick provider timeout fixture",
                "--building-case",
                "standard_delivery",
                "--intensity",
                "normal",
                "--adapter",
                "adapter:codex-local",
                "--output-root",
                str(root / "provider-output"),
            ]
            non_quick_args = parser.parse_args(non_quick_argv)
            call_count = len(calls)
            try:
                cli._run_build(non_quick_args)
            except cli.BuildTimeoutRequiredError as exc:
                timeout_packet = cli._public_error_packet(non_quick_args, exc)
            else:
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: non-quick provider work inherited "
                    "a silent timeout instead of stopping"
                )
            if len(calls) != call_count:
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: timeout-required stop reached dispatch"
                )
            if (
                timeout_packet.get("public_error_code") != "build_timeout_required"
                or timeout_packet.get("timeout_stop", {}).get("execution_started")
                is not False
                or timeout_packet.get("timeout_stop", {}).get("silent_default_applied")
                is not False
            ):
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: timeout-required typed stop drifted: "
                    f"{timeout_packet!r}"
                )

            explicit_timeout_args = parser.parse_args(
                [*non_quick_argv, "--timeout", "900"]
            )
            explicit_packet = cli._run_build(explicit_timeout_args)
            if (
                calls[-1]["kwargs"].get("adapter_timeout_seconds") != 900
                or explicit_packet.get("resolved_timeout_seconds") != 900
                or explicit_packet.get("timeout_basis") != "cli_explicit"
            ):
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: explicit non-quick timeout was not "
                    f"preserved in dispatch and packet: {explicit_packet!r}"
                )

            performer_exc = DeclaredPerformerUnavailableError(
                label="steps[0]",
                agent_object_ref="agent-object:dev",
                adapter_ref="adapter:codex-local",
            )
            performer_packet = cli._public_error_packet(explicit_timeout_args, performer_exc)
            performer_stop = performer_packet.get("declared_performer_unavailable", {})
            if (
                performer_packet.get("public_error_code")
                != "declared_performer_unavailable"
                or performer_stop.get("step_label") != "steps[0]"
                or performer_stop.get("agent_object_ref") != "agent-object:dev"
                or performer_stop.get("adapter_ref") != "adapter:codex-local"
                or performer_stop.get("execution_started") is not False
                or performer_stop.get("readiness_observation", {}).get("ready")
                is not False
            ):
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: declared performer typed stop was "
                    f"not safely projected: {performer_packet!r}"
                )
        finally:
            cli.run_customer_building_in_sandbox = original_runner
            cli.preflight_provider = original_preflight
    return 7


def _assert_identical_proposal_reentry(repo: Path) -> int:
    """Pin stop -> forward reuse for identical proposals and mismatch refusal."""

    del repo
    from brick_protocol.support.operator import assembly

    plan = {
        "schema": "declared-building-plan/v1",
        "building_id": "cli-proposal-reentry",
        "brick_steps": [],
    }

    def composed(composed_plan: Mapping[str, Any]) -> Any:
        return assembly.ComposedGraph(
            nodes=(),
            edges=(),
            groups=(),
            composed_plan=dict(composed_plan),
            ungated_write_node_warnings=(),
            building_id="cli-proposal-reentry",
            declared_by="coo:checker",
            selected_adapter_ref="adapter:local",
            selected_model_ref="model:default",
            selected_shape_ref="building-shape:chain",
            transition_concern_adoption="advisory",
        )

    with tempfile.TemporaryDirectory(prefix="bp-cli-proposal-reentry-") as raw:
        output_root = Path(raw)
        proposal = assembly.persist_proposed_building_graph(
            composed(plan),
            output_root,
        )
        first_bytes = proposal.read_bytes()
        reused = assembly.persist_proposed_building_graph(
            composed(plan),
            output_root,
        )
        if reused != proposal or proposal.read_bytes() != first_bytes:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: identical proposal re-entry did not "
                "reuse the frozen proposal byte-for-byte"
            )

        changed = dict(plan)
        changed["declared_by"] = "coo:different"
        try:
            assembly.persist_proposed_building_graph(
                composed(changed),
                output_root,
            )
        except FileExistsError as exc:
            if "different canonical content" not in str(exc):
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: mismatched proposal refusal lost its "
                    f"canonical-content reason: {exc}"
                ) from exc
        else:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: mismatched proposal silently reused or overwrote"
            )
        if proposal.read_bytes() != first_bytes:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: mismatched proposal refusal changed frozen bytes"
            )
    return 2


def run_brick_cli_entrypoint_smoke(repo: Path) -> KernelResult:
    """Bare-entrypoint smoke for the customer-facing ``brick`` CLI.

    The R1 trap is a console-script/import context launched from outside the repo
    with PYTHONPATH unset: the import-identity router can expose
    ``brick_protocol.*``, but existing transitive modules may still import bare
    ``support.*``. ``brick_protocol/support/operator/cli.py`` must therefore insert BOTH the repo
    root and ``brick_protocol/support/import_identity`` before importing support seams.
    """

    script = repo / "brick_protocol" / "support" / "operator" / "cli.py"
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
sys.path.insert(0, str(repo))
import brick_protocol.support.operator.cli as cli
import brick_protocol.support.operator.coo_operating_chain
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
        + _assert_brick_cli_authoring_funnel(cli, repo)
        + _assert_brick_cli_recovery_handle_lift(cli, repo)
        + _assert_brick_cli_customer_task_intent(cli, repo)
        + _assert_brick_cli_verify_layering(cli, repo)
        + _assert_brick_cli_timeout_and_review_packet(cli, repo)
        + _assert_identical_proposal_reentry(repo)
    )

    return KernelResult(
        check_id="brick_cli_entrypoint_smoke",
        inspected=inspected,
        output=(
            "brick CLI entrypoint smoke passed: direct script and import-identity "
            "console-script simulation ran from outside the repo with PYTHONPATH "
            "unset and emitted status JSON without ModuleNotFoundError; untriaged "
            "tasks fail closed without preset auto-selection; quick_check/quick_fix "
            "direct lowering requires explicit direct_preset + fast_confirm; normal, "
            "complex, and critical triage runs the building-call-authoring preset; "
            "confirmed Building Call JSON lowers into the same sandbox dispatch; "
            "preset, graph-declaration, and resume packets preserve the shared "
            "recovery-handle schema and exact underlying values; "
            "non-quick provider work requires a visible timeout while local/quick "
            "defaults and the resolved casting table are packeted; identical "
            "stop-to-forward proposals reuse frozen bytes while mismatches refuse; "
            "plain verify/check and verify --json use the provider-free core "
            "profile while explicit --all preserves the full profile sweep"
        ),
    )


def _file_snapshot(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _call_cli_json(cli: Any, argv: list[str]) -> tuple[int, dict[str, Any], str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = cli.main(argv)
    text = stdout.getvalue()
    packet: dict[str, Any] = {}
    if text.strip():
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ProfileError(f"customer_project_progress_cli emitted non-object JSON: {parsed!r}")
        packet = parsed
    return exit_code, packet, stderr.getvalue()


def run_customer_project_progress_cli(repo: Path) -> KernelResult:
    """Behavioral customer project/progress CLI check over a temp repo.

    Support checker mechanics only: this observes the customer CLI wrapper over
    project_creation/progress_projection, records no source truth, and does not
    judge success, quality, or Movement.
    """

    _ensure_import_identity(repo)
    cli = importlib.import_module("brick_protocol.support.operator.cli")
    parser = cli.build_parser()
    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    if len(subparser_actions) != 1:
        raise ProfileError("customer_project_progress_cli: CLI parser lost public subparser action")
    public_commands = set(subparser_actions[0].choices)
    if not {"project", "progress"}.issubset(public_commands):
        raise ProfileError(
            "customer_project_progress_cli: parser does not expose project/progress commands"
        )
    project_parser = subparser_actions[0].choices["project"]
    project_subparsers = [
        action
        for action in project_parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    if len(project_subparsers) != 1:
        raise ProfileError("customer_project_progress_cli: project parser lost subcommands")
    if set(project_subparsers[0].choices) != {"new", "list", "show"}:
        raise ProfileError(
            "customer_project_progress_cli: project parser must expose exactly new/list/show"
        )

    source = inspect.getsource(cli)
    for needle in (
        "from brick_protocol.support.operator.project_creation import create_project",
        "from brick_protocol.support.operator.progress_projection import (",
        "render_project_progress",
        "generate_project_progress",
    ):
        if needle not in source:
            raise ProfileError(
                f"customer_project_progress_cli: cli.py lost backend import needle {needle!r}"
            )
    forbidden_needles = (
        "movement_choice",
        "route_target",
        "success_judgment",
        "quality_judgment",
        "scheduler",
        "queue",
        "retry runtime",
    )
    for needle in forbidden_needles:
        if needle in source:
            raise ProfileError(
                f"customer_project_progress_cli: cli.py introduced forbidden boundary text {needle!r}"
            )

    with tempfile.TemporaryDirectory(prefix="bp-customer-project-cli-") as tmp:
        temp_repo = Path(tmp)
        project_root = temp_repo / "project"
        project_root.mkdir()

        refused_exit, _packet, _stderr = _call_cli_json(
            cli,
            [
                "project",
                "new",
                "--json",
                "--repo",
                str(temp_repo),
            ],
        )
        if refused_exit == 0:
            raise ProfileError(
                "customer_project_progress_cli: non-TTY project new without explicit "
                "charter fields was accepted"
            )
        if any(project_root.iterdir()):
            raise ProfileError(
                "customer_project_progress_cli: rejected non-TTY project new created files"
            )

        secret_text = "direction token=SHOULD_NOT_APPEAR123456"
        raw_needles = ("token=SHOULD_NOT_APPEAR123456", "SHOULD_NOT_APPEAR")
        create_argv = [
            "project",
            "new",
            "--json",
            "--non-interactive",
            "--repo",
            str(temp_repo),
            "--id",
            "checker-cli-vessel",
            "--label",
            "Checker CLI Vessel",
            "--why-exists",
            "checker fixture for customer project CLI",
            "--why-now",
            "created inside a temporary checker repo",
            "--direction",
            secret_text,
            "--done-means",
            "checker assertions observed the wrapper",
            "--out-of-scope",
            "real customer work",
            "--manager",
            "checker-human",
        ]
        create_exit, create_packet, _stderr = _call_cli_json(cli, create_argv)
        if create_exit != 0:
            raise ProfileError(
                f"customer_project_progress_cli: full non-interactive project new rejected: {create_packet!r}"
            )
        create_text = json.dumps(create_packet, sort_keys=True)
        if any(needle in create_text for needle in raw_needles):
            raise ProfileError(
                "customer_project_progress_cli: project new leaked secret-shaped declaration text"
            )
        vessel = project_root / "checker-cli-vessel"
        before_list = _file_snapshot(vessel)
        list_exit, list_packet, _stderr = _call_cli_json(
            cli, ["project", "list", "--json", "--repo", str(temp_repo)]
        )
        if list_exit != 0 or list_packet.get("command") != "project-list":
            raise ProfileError(
                f"customer_project_progress_cli: project list rejected or emitted wrong packet: {list_packet!r}"
            )
        if _file_snapshot(vessel) != before_list:
            raise ProfileError("customer_project_progress_cli: project list mutated the vessel")
        if any(needle in json.dumps(list_packet, sort_keys=True) for needle in raw_needles):
            raise ProfileError("customer_project_progress_cli: project list leaked secret-shaped text")

        before_show = _file_snapshot(vessel)
        show_exit, show_packet, _stderr = _call_cli_json(
            cli,
            [
                "project",
                "show",
                "checker-cli-vessel",
                "--json",
                "--repo",
                str(temp_repo),
            ],
        )
        if show_exit != 0 or show_packet.get("command") != "project-show":
            raise ProfileError(
                f"customer_project_progress_cli: project show rejected or emitted wrong packet: {show_packet!r}"
            )
        if _file_snapshot(vessel) != before_show:
            raise ProfileError("customer_project_progress_cli: project show mutated the vessel")
        if any(needle in json.dumps(show_packet, sort_keys=True) for needle in raw_needles):
            raise ProfileError("customer_project_progress_cli: project show leaked secret-shaped text")

        original_render = cli.render_project_progress
        original_generate = cli.generate_project_progress
        calls = {"render": 0, "generate": 0}

        def observed_render(project_ref: str, *, repo_root: Path | str = repo) -> str:
            calls["render"] += 1
            return original_render(project_ref, repo_root=repo_root)

        def observed_generate(project_ref: str, *, repo_root: Path | str = repo) -> dict[str, Any]:
            calls["generate"] += 1
            return original_generate(project_ref, repo_root=repo_root)

        cli.render_project_progress = observed_render
        cli.generate_project_progress = observed_generate
        try:
            before_progress = _file_snapshot(vessel)
            progress_exit, progress_packet, _stderr = _call_cli_json(
                cli,
                [
                    "progress",
                    "checker-cli-vessel",
                    "--json",
                    "--repo",
                    str(temp_repo),
                ],
            )
            if progress_exit != 0 or progress_packet.get("command") != "progress":
                raise ProfileError(
                    "customer_project_progress_cli: progress default rejected or emitted "
                    f"wrong packet: {progress_packet!r}"
                )
            if calls["render"] != 1 or calls["generate"] != 0:
                raise ProfileError(
                    "customer_project_progress_cli: progress default did not call only "
                    f"render_project_progress, calls={calls!r}"
                )
            if _file_snapshot(vessel) != before_progress:
                raise ProfileError("customer_project_progress_cli: progress default mutated the vessel")
            if any(needle in json.dumps(progress_packet, sort_keys=True) for needle in raw_needles):
                raise ProfileError("customer_project_progress_cli: progress default leaked secret-shaped text")

            write_exit, write_packet, _stderr = _call_cli_json(
                cli,
                [
                    "progress",
                    "checker-cli-vessel",
                    "--write",
                    "--json",
                    "--repo",
                    str(temp_repo),
                ],
            )
            if write_exit != 0 or write_packet.get("command") != "progress-write":
                raise ProfileError(
                    "customer_project_progress_cli: progress --write rejected or emitted "
                    f"wrong packet: {write_packet!r}"
                )
            if calls["generate"] != 1:
                raise ProfileError(
                    "customer_project_progress_cli: progress --write did not call "
                    f"generate_project_progress, calls={calls!r}"
                )
            if not (vessel / "PROGRESS.md").is_file():
                raise ProfileError("customer_project_progress_cli: progress --write wrote no PROGRESS.md")
            progress_record = write_packet.get("progress", {})
            if not isinstance(progress_record, dict) or progress_record.get("progress_path") != (
                "project/checker-cli-vessel/PROGRESS.md"
            ):
                raise ProfileError(
                    "customer_project_progress_cli: progress --write packet did not report "
                    f"the backend progress path: {write_packet!r}"
                )
            progress_body = (vessel / "PROGRESS.md").read_text(encoding="utf-8")
            if any(needle in progress_body for needle in raw_needles):
                raise ProfileError(
                    "customer_project_progress_cli: generated PROGRESS.md leaked secret-shaped declaration text"
                )
            if "[redacted]" not in progress_body:
                raise ProfileError(
                    "customer_project_progress_cli: generated PROGRESS.md did not "
                    "redact the secret-shaped declaration probe"
                )
            if any(needle in json.dumps(write_packet, sort_keys=True) for needle in raw_needles):
                raise ProfileError("customer_project_progress_cli: progress --write leaked secret-shaped text")
        finally:
            cli.render_project_progress = original_render
            cli.generate_project_progress = original_generate

    return KernelResult(
        check_id="customer_project_progress_cli",
        inspected=10,
        output=(
            "customer project/progress CLI passed: parser exposes project new/list/show "
            "and progress; non-TTY default project creation refuses without a vessel; "
            "full non-interactive creation uses create_project; list/show/default "
            "progress are read-only; progress --write calls generate_project_progress; "
            "secret-shaped declaration text is redacted from customer packets and "
            "generated PROGRESS.md; no "
            "success/quality/Movement authority was observed"
        ),
    )


def _run_brick_cli_entrypoint_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "brick_protocol/support/checkers/check_profile.py",
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
    source = repo / "brick_protocol" / "support" / "operator" / "cli.py"
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
            rel_path="brick_protocol/support/operator/onboard.py",
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
            rel_path="brick_protocol/support/operator/cli.py",
            needle='    print(f"repo_root: {repo_observation.get(\'repo_root\', \'\')}", file=stream)',
            poisoned='    pass  # mutation: first repo_root launch line removed',
        ),
        _source_replace_mutation_red(
            repo,
            label="build-unify D5 model-alias loud rejection (표18)",
            rel_path="brick_protocol/support/connection/adapter_model_casting.py",
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

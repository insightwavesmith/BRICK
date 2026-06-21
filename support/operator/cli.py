"""Customer-facing Brick CLI support entrypoint.

This is a support wrapper over existing operator/checker seams. It bootstraps
the checkout import identity before importing repo-local support modules so the
console script works from outside the repo with PYTHONPATH unset.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_IMPORT_IDENTITY_ROOT = _REPO_ROOT / "support" / "import_identity"
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_IMPORT_IDENTITY_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPORT_IDENTITY_ROOT))

import argparse
import contextlib
import io
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from support.checkers import check_profile
from support.operator.first_use import FIRST_USE_FILENAME, write_first_use
from support.operator import onboard
from support.operator.driver import run_customer_building_in_sandbox


ADAPTER_LOCAL = "adapter:local"
REAL_PROVIDER_ADAPTER = "adapter:codex-local"
DEFAULT_EXAMPLE_BUILDING_ID = "brick-cli-example"
DEFAULT_EXAMPLE_TASK_SOURCE_REF = "brick/templates/tasks/source-template.md"
DEFAULT_LOCAL_PRESET_REF = "building-chain-preset:onboarding-example-graph"
DEFAULT_DECLARED_BY = "coo"

PROOF_LIMITS = (
    "support CLI wrapper only",
    "existing seams own run/checker behavior",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
NOT_PROVEN = (
    "provider reliability",
    "future Building correctness",
    "semantic quality of Agent returns",
    "real-provider credential readiness",
    "production runtime behavior",
)


def _json_dump(packet: Any) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)


def _repo_from_args(args: argparse.Namespace) -> Path:
    raw_repo = getattr(args, "repo", None)
    if raw_repo:
        return Path(raw_repo).resolve()
    return _REPO_ROOT


def _default_builds_root() -> Path:
    return Path.home() / ".brick" / "builds"


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _task_building_id() -> str:
    return f"brick-cli-task-{_utc_stamp()}-{uuid4().hex[:8]}"


def _build_intent(args: argparse.Namespace) -> dict[str, Any]:
    # --real-provider is friendly sugar: when the customer opts into a real
    # provider but left --adapter at the local-stub default, upgrade to the
    # primary real adapter. An explicit --adapter always wins.
    adapter = args.adapter
    if getattr(args, "real_provider", False) and adapter == ADAPTER_LOCAL:
        adapter = REAL_PROVIDER_ADAPTER
    task = (args.task or "").strip()
    if task:
        building_id = args.building_id or _task_building_id()
        return {
            "declared_by": args.declared_by,
            "task_statement": task,
            "chain_preset_ref": args.preset,
            "selected_adapter_ref": adapter,
            "building_id": building_id,
        }
    return {
        "declared_by": args.declared_by,
        "task_source_ref": args.task_source_ref,
        "chain_preset_ref": args.preset,
        "selected_adapter_ref": adapter,
        "building_id": args.building_id or DEFAULT_EXAMPLE_BUILDING_ID,
    }


def _run_build(args: argparse.Namespace) -> dict[str, Any]:
    repo = _repo_from_args(args)
    output_root = Path(args.output_root).expanduser() if args.output_root else _default_builds_root()
    output_root.mkdir(parents=True, exist_ok=True)
    intent = _build_intent(args)
    overwrite_existing = bool(args.overwrite_existing or not args.task)
    result = run_customer_building_in_sandbox(
        intent,
        customer_repo_root=repo,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        adapter_timeout_seconds=args.timeout,
        proof_limits=PROOF_LIMITS,
    )
    intake = result.intake_result
    packet: dict[str, Any] = {
        "command": "build",
        "repo_root": str(repo),
        "output_root": str(output_root),
        "building_id": result.building_id,
        "declared_by": intent["declared_by"],
        "task_source_basis": "task_statement" if args.task else "task_source_ref",
        "chain_preset_ref": intent["chain_preset_ref"],
        "adapter_ref": intent["selected_adapter_ref"],
        "isolation_mode": result.isolation_mode,
        "isolation_reason": result.isolation_reason,
        "base_sha": result.base_sha,
        "worktree_path": result.worktree_path,
        "evidence_root": result.evidence_root,
        "frontier_kind": result.frontier_kind,
        "commit_sha": result.commit_sha,
        "worktree_disposed": result.worktree_disposed,
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    if intake is not None:
        packet.update(
            {
                "plan_path": str(intake.plan_path),
                "plan_shape": intake.plan_shape,
                "walker_mode": intake.walker_mode,
                "walker_mode_basis": intake.walker_mode_basis,
            }
        )
    return packet


def _render_build(packet: dict[str, Any]) -> str:
    lines = [
        "Brick build support evidence",
        f"repo_root: {packet['repo_root']}",
        f"building_id: {packet['building_id']}",
        f"adapter_ref: {packet['adapter_ref']}",
        f"chain_preset_ref: {packet['chain_preset_ref']}",
        f"isolation_mode: {packet['isolation_mode']}",
        f"evidence_root: {packet['evidence_root']}",
        f"frontier_kind: {packet['frontier_kind']}",
    ]
    if packet.get("plan_path"):
        lines.append(f"plan_path: {packet['plan_path']}")
    if packet.get("worktree_path"):
        lines.append(f"worktree_path: {packet['worktree_path']}")
    if packet.get("commit_sha"):
        lines.append(f"commit_sha: {packet['commit_sha']}")
    lines.append("proof_limits: " + "; ".join(packet["proof_limits"]))
    lines.append("not_proven: " + "; ".join(packet["not_proven"]))
    return "\n".join(lines)


def _render_doctor(packet: dict[str, Any]) -> str:
    lines = ["Brick doctor support evidence", "rows:"]
    for row in packet.get("rows", []):
        observed = "yes" if row.get("ok") else "no"
        lines.append(f"- {row.get('target', '')}: observed_ok={observed}; {row.get('message_ko', '')}")
    lines.append("symptom_table:")
    for symptom, prescription in packet.get("symptom_table", []):
        lines.append(f"- {symptom} -> {prescription}")
    lines.append("proof_limits: diagnosis record only; no source truth, success, quality, or Movement authority")
    return "\n".join(lines)


def _status_packet(args: argparse.Namespace) -> dict[str, Any]:
    repo = _repo_from_args(args)
    builds_root = _default_builds_root()
    return {
        "command": "status",
        "repo_root": str(repo),
        "cwd": str(Path.cwd().resolve()),
        "entrypoint_file": str(Path(__file__).resolve()),
        "python_executable": sys.executable,
        "brick_home": str(Path.home() / ".brick"),
        "default_builds_root": str(builds_root),
        "default_builds_root_exists": builds_root.exists(),
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }


def _render_status(packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Brick status support evidence",
            f"repo_root: {packet['repo_root']}",
            f"cwd: {packet['cwd']}",
            f"entrypoint_file: {packet['entrypoint_file']}",
            f"python_executable: {packet['python_executable']}",
            f"brick_home: {packet['brick_home']}",
            f"default_builds_root: {packet['default_builds_root']}",
            f"default_builds_root_exists: {packet['default_builds_root_exists']}",
            "proof_limits: " + "; ".join(packet["proof_limits"]),
            "not_proven: " + "; ".join(packet["not_proven"]),
        ]
    )


def _cmd_doctor(args: argparse.Namespace) -> int:
    packet = onboard.run_doctor()
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_doctor(packet))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    packet = _status_packet(args)
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_status(packet))
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    packet = _run_build(args)
    if args.json:
        print(_json_dump(packet))
    else:
        print(_render_build(packet))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    repo = _repo_from_args(args)
    if args.self_test:
        verify_argv = ["--self-test"]
    elif args.profile:
        verify_argv = ["--repo", str(repo), "--profile", args.profile]
    else:
        verify_argv = ["--repo", str(repo), "--all"]
    if not args.json:
        return check_profile.main(verify_argv)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = check_profile.main(verify_argv)
    print(
        _json_dump(
            {
                "command": "verify",
                "repo_root": str(repo),
                "checker_argv": verify_argv,
                "checker_exit_code": exit_code,
                "stdout": stdout.getvalue(),
                "stderr": stderr.getvalue(),
                "proof_limits": list(PROOF_LIMITS),
                "not_proven": list(NOT_PROVEN),
            }
        )
    )
    return exit_code


def _cmd_init(args: argparse.Namespace) -> int:
    doctor_packet = onboard.run_doctor()
    build_packet = None
    build_error = None
    first_use_packet = None
    if not args.skip_build:
        build_args = argparse.Namespace(
            repo=args.repo,
            output_root=args.output_root,
            task="",
            task_source_ref=DEFAULT_EXAMPLE_TASK_SOURCE_REF,
            preset=DEFAULT_LOCAL_PRESET_REF,
            adapter=ADAPTER_LOCAL,
            real_provider=False,
            building_id=DEFAULT_EXAMPLE_BUILDING_ID,
            declared_by=DEFAULT_DECLARED_BY,
            overwrite_existing=True,
            timeout=args.timeout,
        )
        try:
            build_packet = _run_build(build_args)
            first_use_packet = write_first_use(
                build_packet["output_root"],
                doctor_packet=doctor_packet,
                build_packet=build_packet,
            )
        except Exception as exc:  # noqa: BLE001 -- init reports friendly evidence
            build_error = {
                "error_kind": type(exc).__name__,
                "error_message": str(exc),
            }
    status_packet = _status_packet(args)
    packet = {
        "command": "init",
        "non_interactive": bool(args.non_interactive),
        "doctor": doctor_packet,
        "build": build_packet,
        "build_error": build_error,
        "status": status_packet,
        "proof_limits": list(PROOF_LIMITS),
        "not_proven": list(NOT_PROVEN),
    }
    if first_use_packet is not None:
        packet["first_use"] = first_use_packet
    if args.json:
        print(_json_dump(packet))
    else:
        print("Brick init support evidence")
        print(_render_doctor(doctor_packet))
        if build_packet is not None:
            print("")
            print(_render_build(build_packet))
        if build_error is not None:
            print("")
            print(f"build_error: {build_error['error_kind']}: {build_error['error_message']}")
        if first_use_packet is not None:
            print("")
            print(f"next: read {FIRST_USE_FILENAME}")
            print(f"first_use_path: {first_use_packet['path']}")
        print("")
        print(_render_status(status_packet))
    return 0 if build_error is None else 1


def _cmd_auth_login(args: argparse.Namespace) -> int:
    # Guided readiness funnel. This NEVER enters credentials -- it observes
    # provider readiness (doctor) and prints per-provider login guidance so the
    # customer runs the provider-native login themselves.
    doctor_packet = onboard.run_doctor()
    guidance = [
        "codex  -> codex login",
        "claude -> claude  (실행 후 안내에 따라 로그인 / run it, then follow the prompt)",
        "gemini -> gemini  (또는 GEMINI_API_KEY 설정 / or set GEMINI_API_KEY)",
        "local  -> 설치/로그인 불필요 / no install or login needed",
    ]
    next_step = 'brick build --task "..." --real-provider'
    if args.json:
        print(
            _json_dump(
                {
                    "command": "auth-login",
                    "doctor": doctor_packet,
                    "login_guidance": guidance,
                    "next": next_step,
                    "proof_limits": list(PROOF_LIMITS),
                    "not_proven": list(NOT_PROVEN),
                }
            )
        )
        return 0
    print("Brick auth login support evidence")
    print(_render_doctor(doctor_packet))
    print("")
    print("로그인 안내 / Login guidance:")
    for line in guidance:
        print(f"  {line}")
    print("")
    print(f"준비되면 / When ready:  {next_step}")
    print(f"proof_limits: {', '.join(PROOF_LIMITS)}")
    return 0


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Emit JSON support evidence.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt for input; current P1 commands never prompt.",
    )
    parser.add_argument("--repo", default=None, help="Repo root override.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brick",
        description="Brick Protocol support CLI entrypoint.",
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Run non-interactive first-use support checks.")
    _add_common(init_parser)
    init_parser.add_argument("--skip-build", action="store_true", help="Skip the local example build.")
    init_parser.add_argument("--output-root", default=None, help="Evidence output root.")
    init_parser.add_argument("--timeout", type=int, default=120, help="Adapter timeout seconds.")
    init_parser.set_defaults(func=_cmd_init)

    build = subparsers.add_parser("build", help="Run a declared Building through the existing driver seam.")
    _add_common(build)
    build.add_argument("--task", default="", help="Inline task statement. Omit for the bundled example.")
    build.add_argument(
        "--task-source-ref",
        default=DEFAULT_EXAMPLE_TASK_SOURCE_REF,
        help="Repo-relative task source for the bundled/file-flow build.",
    )
    build.add_argument("--preset", default=DEFAULT_LOCAL_PRESET_REF, help="Declared chain preset ref.")
    build.add_argument("--adapter", default=ADAPTER_LOCAL, help="Declared adapter ref.")
    build.add_argument(
        "--real-provider",
        action="store_true",
        help=(
            "Use a real provider-backed adapter (default adapter:codex-local) instead of "
            "the local example stub. Run `brick auth login` first to confirm readiness."
        ),
    )
    build.add_argument("--building-id", default="", help="Optional explicit Building id.")
    build.add_argument("--declared-by", default=DEFAULT_DECLARED_BY, help="Caller/COO declaration ref.")
    build.add_argument("--output-root", default=None, help="Evidence output root.")
    build.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Allow overwriting an existing Building evidence root.",
    )
    build.add_argument("--timeout", type=int, default=120, help="Adapter timeout seconds.")
    build.set_defaults(func=_cmd_build)

    verify = subparsers.add_parser("verify", aliases=["check"], help="Run check_profile over this checkout.")
    _add_common(verify)
    verify.add_argument("--profile", default="", help="Profile name or YAML path. Defaults to --all.")
    verify.add_argument("--self-test", action="store_true", help="Run the profile runner self-test.")
    verify.set_defaults(func=_cmd_verify)

    doctor = subparsers.add_parser("doctor", help="Run the existing onboard doctor.")
    _add_common(doctor)
    doctor.set_defaults(func=_cmd_doctor)

    status = subparsers.add_parser("status", help="Print local support status evidence.")
    _add_common(status)
    status.set_defaults(func=_cmd_status)

    auth = subparsers.add_parser("auth", help="Provider auth readiness + login guidance.")
    _add_common(auth)
    auth_sub = auth.add_subparsers(dest="auth_command")
    auth_login = auth_sub.add_parser("login", help="Show provider login guidance and readiness.")
    _add_common(auth_login)
    auth_login.set_defaults(func=_cmd_auth_login)
    auth.set_defaults(func=_cmd_auth_login)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if not args_list:
        args_list = ["status"]
    parser = build_parser()
    args = parser.parse_args(args_list)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 -- CLI should report, not traceback
        packet = {
            "command": getattr(args, "command", ""),
            "error_kind": type(exc).__name__,
            "error_message": str(exc),
            "proof_limits": list(PROOF_LIMITS),
            "not_proven": list(NOT_PROVEN),
        }
        if getattr(args, "json", False):
            print(_json_dump(packet), file=sys.stderr)
        else:
            print(f"brick command rejected evidence: {type(exc).__name__}: {exc}", file=sys.stderr)
            print("proof_limits: " + "; ".join(PROOF_LIMITS), file=sys.stderr)
        return 1


__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())

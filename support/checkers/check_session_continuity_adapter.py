#!/usr/bin/env python3
"""Pin same-Building adapter session continuity wiring.

This checker is fixture-only support evidence. It does not call providers,
does not store raw provider session ids, and does not judge source truth,
success, quality, or Movement.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "support" / "import_identity") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "support" / "import_identity"))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.connection.agent_adapter import (  # noqa: E402
    AgentAdapterRequest,
    LocalCliCompleted,
    connect_agent_brain,
)
from brick_protocol.support.connection.adapter_constants import (  # noqa: E402
    ADAPTER_CLAUDE_LOCAL,
    ADAPTER_CODEX_LOCAL,
    READ_WRITE_TOOL_POLICY_REF,
)
from brick_protocol.support.connection.adapter_local_cli import (  # noqa: E402
    _CLAUDE_CONTINUITY_SESSION_IDS,
    _cleanup_codex_continuity_home_for_request,
    _codex_continuity_home_for_request,
)


PROOF_LIMIT = (
    "proof limit: session-continuity adapter checker support evidence only; "
    "fixture command runners do not prove live provider save/resume behavior, "
    "provider credential validity, source truth, success judgment, quality "
    "judgment, or Movement authority."
)


class SessionContinuityAdapterError(ValueError):
    """Raised when fixture-observed adapter continuity wiring drifts."""


@contextlib.contextmanager
def _codex_default_env():
    saved = {
        "BRICK_CODEX_EPHEMERAL": os.environ.get("BRICK_CODEX_EPHEMERAL"),
        "BRICK_CODEX_SERVICE_TIER": os.environ.get("BRICK_CODEX_SERVICE_TIER"),
    }
    os.environ.pop("BRICK_CODEX_EPHEMERAL", None)
    os.environ.pop("BRICK_CODEX_SERVICE_TIER", None)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class FixtureRunner:
    def __init__(self, *, fail_resume_once: bool = False) -> None:
        self.calls: list[tuple[tuple[str, ...], Mapping[str, str] | None]] = []
        self.fail_resume_once = fail_resume_once
        self.failed_resume_rc = 0
        self.failed_resume_stderr = ""

    def __call__(
        self,
        args: Sequence[str],
        cwd: Path,
        timeout_seconds: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> LocalCliCompleted:
        del cwd, timeout_seconds
        captured = tuple(str(arg) for arg in args)
        self.calls.append((captured, dict(env or {})))
        if captured[-1:] == ("--version",):
            return LocalCliCompleted(captured, 0, "fixture-version", "")
        if self.fail_resume_once and ("resume" in captured or "--resume" in captured):
            self.fail_resume_once = False
            self.failed_resume_rc = 7
            self.failed_resume_stderr = "fixture resume failed"
            return LocalCliCompleted(captured, 7, "", self.failed_resume_stderr)
        if "--output-last-message" in captured:
            index = captured.index("--output-last-message")
            Path(captured[index + 1]).write_text("fixture adapter output", encoding="utf-8")
        if captured[:2] == ("claude", "-p"):
            return LocalCliCompleted(
                captured,
                0,
                '{"response":"fixture adapter output","session_id":"redacted"}',
                "",
            )
        return LocalCliCompleted(captured, 0, "", "")


def _request(adapter_ref: str, mode: str, *, next_ref: str | None = None) -> AgentAdapterRequest:
    return AgentAdapterRequest(
        building_id="session-continuity-fixture",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_ref,
        brick_instance_ref="brick:session-continuity-fixture:work",
        next_brick_instance_ref=next_ref or "building-boundary:session-continuity-fixture-closed",
        tool_policy_refs=(READ_WRITE_TOOL_POLICY_REF,),
        required_return_shape="observed_evidence,commands_run,not_proven",
        session_continuity_mode=mode,
        building_session_ref="building-session:session-continuity-fixture",
        session_scope_ref="building-session-scope:session-continuity-fixture",
    )


def _actual_dispatch_calls(runner: FixtureRunner) -> list[tuple[str, ...]]:
    return [args for args, _env in runner.calls if args[-1:] != ("--version",)]


def _assert_none_codex_unchanged(repo: Path) -> str:
    runner = FixtureRunner()
    request = _request(ADAPTER_CODEX_LOCAL, "none")
    connect_agent_brain(request, cwd=repo, command_runner=runner)
    calls = _actual_dispatch_calls(runner)
    if len(calls) != 1:
        raise SessionContinuityAdapterError("codex none fixture expected one dispatch call")
    args = calls[0]
    if "resume" in args:
        raise SessionContinuityAdapterError("codex none unexpectedly issued resume")
    if "--ephemeral" not in args:
        raise SessionContinuityAdapterError("codex none did not retain --ephemeral")
    if "--cd" not in args or "--sandbox" not in args:
        raise SessionContinuityAdapterError("codex none lost normal exec cwd/sandbox args")
    if 'service_tier="priority"' not in args:
        raise SessionContinuityAdapterError("codex none lost default service_tier priority argv")
    return "codex none mode retained non-resume ephemeral exec argv with service_tier priority"


def _seed_codex_session_home(request: AgentAdapterRequest) -> Path:
    home = _codex_continuity_home_for_request(request)
    if home.exists():
        shutil.rmtree(home)
    session_file = home / ".codex" / "sessions" / "fixture.jsonl"
    session_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    return home


def _assert_continue_codex_home_and_resume(repo: Path) -> str:
    runner = FixtureRunner()
    request = _request(ADAPTER_CODEX_LOCAL, "continue_if_available")
    home = _seed_codex_session_home(request)
    try:
        result = connect_agent_brain(request, cwd=repo, command_runner=runner)
    finally:
        if home.exists():
            shutil.rmtree(home)
    calls = _actual_dispatch_calls(runner)
    if len(calls) != 1:
        raise SessionContinuityAdapterError("codex continue fixture expected one dispatch call")
    args = calls[0]
    if args[:4] != ("codex", "exec", "resume", "--last"):
        raise SessionContinuityAdapterError(
            "codex continue with observed session state did not issue exec resume --last"
        )
    if "--skip-git-repo-check" not in args:
        raise SessionContinuityAdapterError("codex resume lost non-git cwd trust args")
    if "--cd" in args:
        raise SessionContinuityAdapterError(
            "codex resume pinned CLI-rejected --cd instead of process cwd"
        )
    if "--ephemeral" in args:
        raise SessionContinuityAdapterError("codex continue unexpectedly retained --ephemeral")
    if 'service_tier="priority"' not in args:
        raise SessionContinuityAdapterError("codex resume lost default service_tier priority argv")
    env = runner.calls[-1][1] or {}
    if env.get("HOME") != str(home) or env.get("CODEX_HOME") != str(home / ".codex"):
        raise SessionContinuityAdapterError("codex continue did not use building-scoped home env")
    raw = result.adapter_raw_observations
    if raw.get("codex_resume_last_requested") is not True:
        raise SessionContinuityAdapterError("codex continue raw observation did not note resume")
    return "codex continue mode reused building-scoped home and issued exec resume --last"


def _assert_codex_resume_failure_falls_back(repo: Path) -> str:
    runner = FixtureRunner(fail_resume_once=True)
    request = _request(ADAPTER_CODEX_LOCAL, "continue_if_available")
    home = _seed_codex_session_home(request)
    try:
        result = connect_agent_brain(request, cwd=repo, command_runner=runner)
    finally:
        if home.exists():
            shutil.rmtree(home)
    calls = _actual_dispatch_calls(runner)
    if len(calls) != 2:
        raise SessionContinuityAdapterError("codex failed resume did not retry exactly once")
    if calls[0][:4] != ("codex", "exec", "resume", "--last"):
        raise SessionContinuityAdapterError("codex fallback probe first call was not resume")
    if calls[1][:2] != ("codex", "exec") or "resume" in calls[1]:
        raise SessionContinuityAdapterError("codex fallback probe second call was not fresh exec")
    if 'service_tier="priority"' not in calls[1]:
        raise SessionContinuityAdapterError(
            "codex fallback fresh exec lost default service_tier priority argv"
        )
    if result.adapter_raw_observations.get("codex_resume_fallback_to_fresh") is not True:
        raise SessionContinuityAdapterError("codex fallback observation missing")
    if result.adapter_raw_observations.get("codex_resume_fallback_original_return_code") != 7:
        raise SessionContinuityAdapterError("codex fallback original rc observation missing")
    if (
        result.adapter_raw_observations.get("codex_resume_fallback_original_stderr_excerpt")
        != runner.failed_resume_stderr
    ):
        raise SessionContinuityAdapterError("codex fallback original stderr observation missing")
    return (
        "codex failed resume fell back to fresh exec once "
        f"(resume_rc={runner.failed_resume_rc}, stderr={runner.failed_resume_stderr})"
    )


def _assert_codex_continuity_home_cleanup() -> str:
    runner = FixtureRunner()
    seed_request = _request(ADAPTER_CODEX_LOCAL, "continue_if_available")
    home = _seed_codex_session_home(seed_request)
    if not home.exists():
        raise SessionContinuityAdapterError("codex cleanup fixture home was not seeded")
    terminal_request = _request(ADAPTER_CLAUDE_LOCAL, "none")
    result = connect_agent_brain(terminal_request, cwd=_REPO_ROOT, command_runner=runner)
    if home.exists():
        raise SessionContinuityAdapterError(
            "codex continuity home was not cleaned through cross-adapter terminal path"
        )
    if result.adapter_raw_observations.get("codex_continuity_home_cleanup_requested") is not True:
        raise SessionContinuityAdapterError("codex terminal cleanup observation missing")
    if result.adapter_raw_observations.get("codex_continuity_home_cleanup_removed_count") != 1:
        raise SessionContinuityAdapterError("codex terminal cleanup removal count missing")
    removed_again = _cleanup_codex_continuity_home_for_request(seed_request)
    if removed_again is not False:
        raise SessionContinuityAdapterError("codex continuity cleanup was not idempotent")

    nonterminal_home = _seed_codex_session_home(seed_request)
    nonterminal_request = _request(
        ADAPTER_CLAUDE_LOCAL,
        "none",
        next_ref="brick:session-continuity-fixture:not-closed",
    )
    try:
        nonterminal_result = connect_agent_brain(
            nonterminal_request,
            cwd=_REPO_ROOT,
            command_runner=runner,
        )
        if not nonterminal_home.exists():
            raise SessionContinuityAdapterError(
                "codex cleanup treated a non-boundary *-closed suffix as terminal"
            )
        if "codex_continuity_home_cleanup_requested" in nonterminal_result.adapter_raw_observations:
            raise SessionContinuityAdapterError(
                "codex cleanup observation appeared for a non-boundary next ref"
            )
    finally:
        if nonterminal_home.exists():
            shutil.rmtree(nonterminal_home)
    return (
        "cross-adapter terminal connect_agent_brain path cleaned Codex continuity home "
        "through declared closed boundary only"
    )


def _assert_codex_unwired_modes_stay_ephemeral(repo: Path) -> str:
    for mode in ("start_or_continue", "fork_from_available"):
        runner = FixtureRunner()
        connect_agent_brain(_request(ADAPTER_CODEX_LOCAL, mode), cwd=repo, command_runner=runner)
        calls = _actual_dispatch_calls(runner)
        if len(calls) != 1:
            raise SessionContinuityAdapterError(f"codex {mode} expected one dispatch call")
        args = calls[0]
        if "resume" in args:
            raise SessionContinuityAdapterError(f"codex {mode} unexpectedly issued resume")
        if "--ephemeral" not in args:
            raise SessionContinuityAdapterError(f"codex {mode} did not retain --ephemeral")
        if 'service_tier="priority"' not in args:
            raise SessionContinuityAdapterError(
                f"codex {mode} lost default service_tier priority argv"
            )
    return "codex start_or_continue/fork_from_available remain unwired ephemeral modes"


def _assert_claude_mode_wiring(repo: Path) -> str:
    none_runner = FixtureRunner()
    connect_agent_brain(
        _request(ADAPTER_CLAUDE_LOCAL, "none"),
        cwd=repo,
        command_runner=none_runner,
    )
    none_args = _actual_dispatch_calls(none_runner)[0]
    if "--no-session-persistence" not in none_args:
        raise SessionContinuityAdapterError("claude none lost --no-session-persistence")

    _CLAUDE_CONTINUITY_SESSION_IDS.clear()
    first_continue_runner = FixtureRunner()
    first_result = connect_agent_brain(
        _request(ADAPTER_CLAUDE_LOCAL, "continue_if_available"),
        cwd=repo,
        command_runner=first_continue_runner,
    )
    first_continue_args = _actual_dispatch_calls(first_continue_runner)[0]
    if "--resume" in first_continue_args:
        raise SessionContinuityAdapterError("claude first continue unexpectedly issued --resume")
    if "--no-session-persistence" in first_continue_args:
        raise SessionContinuityAdapterError(
            "claude continue still issued --no-session-persistence"
        )
    if first_result.adapter_raw_observations.get("claude_session_id_present") is not True:
        raise SessionContinuityAdapterError(
            "claude session-id presence was not observed from fixture JSON"
        )
    if first_result.adapter_raw_observations.get("claude_resume_requested") is not False:
        raise SessionContinuityAdapterError("claude first continue did not record fresh-session fallback")

    second_continue_runner = FixtureRunner()
    second_result = connect_agent_brain(
        _request(ADAPTER_CLAUDE_LOCAL, "continue_if_available"),
        cwd=repo,
        command_runner=second_continue_runner,
    )
    second_continue_args = _actual_dispatch_calls(second_continue_runner)[0]
    if "--resume" not in second_continue_args:
        raise SessionContinuityAdapterError("claude second continue did not issue --resume")
    resume_index = second_continue_args.index("--resume")
    if second_continue_args[resume_index + 1] != "redacted":
        raise SessionContinuityAdapterError("claude second continue did not use observed fixture id")
    if second_result.adapter_raw_observations.get("claude_resume_requested") is not True:
        raise SessionContinuityAdapterError("claude second continue did not record resume request")

    for mode in ("start_or_continue", "fork_from_available"):
        mode_runner = FixtureRunner()
        connect_agent_brain(
            _request(ADAPTER_CLAUDE_LOCAL, mode),
            cwd=repo,
            command_runner=mode_runner,
        )
        mode_args = _actual_dispatch_calls(mode_runner)[0]
        if "--resume" in mode_args:
            raise SessionContinuityAdapterError(f"claude {mode} unexpectedly issued --resume")
        if "--no-session-persistence" in mode_args:
            raise SessionContinuityAdapterError(
                f"claude {mode} unexpectedly issued --no-session-persistence"
            )

    if "redacted" in str(first_result.adapter_raw_observations):
        raise SessionContinuityAdapterError("claude raw session id leaked into observations")
    if "redacted" in str(second_result.adapter_raw_observations):
        raise SessionContinuityAdapterError("claude raw session id leaked into observations")
    return (
        "claude continue mode recorded id presence, then issued --resume without observation leak; "
        "claude start_or_continue/fork_from_available remain unwired modes"
    )


def _assert_claude_resume_failure_falls_back(repo: Path) -> str:
    _CLAUDE_CONTINUITY_SESSION_IDS.clear()
    seed_runner = FixtureRunner()
    seed_request = _request(ADAPTER_CLAUDE_LOCAL, "continue_if_available")
    connect_agent_brain(seed_request, cwd=repo, command_runner=seed_runner)

    fallback_runner = FixtureRunner(fail_resume_once=True)
    result = connect_agent_brain(
        seed_request,
        cwd=repo,
        command_runner=fallback_runner,
    )
    calls = _actual_dispatch_calls(fallback_runner)
    if len(calls) != 2:
        raise SessionContinuityAdapterError("claude failed resume did not retry exactly once")
    if "--resume" not in calls[0]:
        raise SessionContinuityAdapterError("claude fallback probe first call did not resume")
    if "--resume" in calls[1]:
        raise SessionContinuityAdapterError("claude fallback probe second call was not fresh")
    raw = result.adapter_raw_observations
    if raw.get("claude_resume_fallback_to_fresh") is not True:
        raise SessionContinuityAdapterError("claude fallback observation missing")
    if raw.get("claude_resume_fallback_original_return_code") != 7:
        raise SessionContinuityAdapterError("claude fallback original rc observation missing")
    if raw.get("claude_resume_fallback_original_stderr_excerpt") != fallback_runner.failed_resume_stderr:
        raise SessionContinuityAdapterError("claude fallback original stderr observation missing")
    if "redacted" in str(raw):
        raise SessionContinuityAdapterError("claude raw session id leaked into fallback observations")
    return (
        "claude failed resume fell back to fresh once "
        f"(resume_rc={fallback_runner.failed_resume_rc}, stderr={fallback_runner.failed_resume_stderr})"
    )


def _assert_local_cli_adapter_return_annotation() -> str:
    source = (_REPO_ROOT / "support" / "connection" / "adapter_local_cli.py").read_text(
        encoding="utf-8"
    )
    annotation_start = source.index("def _invoke_local_cli_adapter(")
    annotation_end = source.index(":\n    from .agent_adapter", annotation_start)
    annotation = source[annotation_start:annotation_end]
    required_fragments = (
        (
            annotation,
            "Mapping[str, Any],\n    tuple[str, ...],\n    tuple[str, ...],\n    "
            "Mapping[str, Any] | None,\n    tuple[str, ...],\n    Mapping[str, Any],\n    str,",
        ),
        (source, "completed.adapter_raw_observations,\n        output_text,"),
    )
    for haystack, fragment in required_fragments:
        if fragment not in haystack:
            raise SessionContinuityAdapterError(
                "_invoke_local_cli_adapter return annotation no longer pins the seven-element side channel"
            )
    return "_invoke_local_cli_adapter return annotation pins seven returned elements"


def check(repo: Path) -> list[str]:
    with _codex_default_env():
        return [
            _assert_none_codex_unchanged(repo),
            _assert_continue_codex_home_and_resume(repo),
            _assert_codex_resume_failure_falls_back(repo),
            _assert_codex_continuity_home_cleanup(),
            _assert_codex_unwired_modes_stay_ephemeral(repo),
            _assert_claude_mode_wiring(repo),
            _assert_claude_resume_failure_falls_back(repo),
            _assert_local_cli_adapter_return_annotation(),
            PROOF_LIMIT,
        ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fixture pin for adapter session continuity.")
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except SessionContinuityAdapterError as exc:
        print("session-continuity adapter rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Subprocess runner + codex connect-stall watchdog + spawn journal + token/text
meter + provider preflight for the Agent Adapter support surface.

This is a PURE relocation out of ``support/connection/agent_adapter.py``: the
cohesive subprocess/watchdog/meter/preflight cluster lives here while
``agent_adapter`` STAYS A FACADE that explicitly re-exports every moved symbol
(public AND underscore-private) so late-bound ``agent_adapter.<sym>`` access
never breaks. Support mechanics only -- it owns no Agent meaning, chooses no Link
Movement, judges no success/quality, and runs no tools/hooks.

Cycle rule: this module imports siblings DIRECTLY (adapter_constants) and NEVER
imports ``support.connection.agent_adapter`` at top level. The few stay-behind
symbols it needs at runtime (``LocalCliCompleted`` and the preflight provider
specs/hints) are pulled in via LAZY in-function imports.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .adapter_constants import (
    ADAPTER_CHAT_SESSION,
    ADAPTER_GEMINI_LOCAL,
    ADAPTER_LOCAL,
)
from .adapter_validation import _reject_secret_text


_CODEX_STALL_WATCHDOG_THRESHOLD_ENV = "BRICK_CODEX_STALL_THRESHOLD_SECONDS"
_CODEX_STALL_WATCHDOG_POLL_ENV = "BRICK_CODEX_STALL_POLL_SECONDS"
# CONNECT-STALL FAST-FAIL (TrackB 0619): a dead-connection codex worker (process
# alive, 0 children, 0 established sockets, cpu_seconds frozen) must be reaped and
# surfaced to a human within the 90-180s band, not after ~20 minutes. The 150s
# default sits inside that band, but the EFFECTIVE threshold is clamped to
# (adapter timeout - 2*poll) so it always fires BEFORE the subprocess deadline with
# room for the 2-sample dead-signature (codex-review F1): at the 120s production
# default the effective threshold is 60s (fires at ~90s, before the 120s deadline).
# BRICK_CODEX_STALL_THRESHOLD_SECONDS still overrides the default but is clamped the
# same way and must be > 0 (NaN/inf/negative/ZERO all rejected -> default; F2). This
# is the DEAD-worker (connect-stall) watchdog ONLY -- it never touches a live worker.
_CODEX_STALL_WATCHDOG_DEFAULT_THRESHOLD_SECONDS = 150
_CODEX_STALL_WATCHDOG_DEFAULT_POLL_SECONDS = 30
_CODEX_STALL_WATCHDOG_PROBE_TIMEOUT_SECONDS = 2
_CODEX_STALL_WATCHDOG_SIGTERM_GRACE_SECONDS = 5
_TIMEOUT_REAP_REASON_ATTR = "_brick_protocol_reap_reason"
# SUPPORT FACTS ONLY: raw dead-connection observation carried on a stall
# TimeoutExpired so the reap journal can record the last health-sample triple +
# how long the dead signature persisted. Never an Agent-fault label or a Link
# decision -- just the numbers the watchdog saw at reap time.
_STALL_DEAD_SIGNATURE_ATTR = "_brick_protocol_stall_dead_signature"
_TIMEOUT_PARTIAL_STDOUT_ATTR = "_brick_protocol_timeout_partial_stdout"
_TIMEOUT_PARTIAL_STDERR_ATTR = "_brick_protocol_timeout_partial_stderr"


@dataclass(frozen=True)
class _CodexStallWatchdogConfig:
    threshold_seconds: float
    poll_seconds: float


@dataclass(frozen=True)
class _CodexCliHealth:
    process_running: bool
    child_count: int
    established_socket_count: int
    cpu_seconds: float


@dataclass(frozen=True)
class _ProcessSnapshotRow:
    ppid: int
    pgid: int
    cpu_seconds: float


def preflight_provider(
    adapter_ref: str,
    *,
    command_runner: Any | None = None,
) -> dict[str, Any]:
    """Friendly, never-raising provider readiness preflight (onboarding "login").

    Returns a structured status dict and NEVER raises. A missing or unauthed
    provider CLI becomes a plain-Korean message (message_ko), not a stack-trace,
    so an AI-never-used beginner can self-fix. This is support mechanics only: it
    proves no provider availability, judges no success/quality, and chooses no
    Movement. It never runs a real (cost-incurring) provider call -- only a cheap
    --version probe with a short timeout.

    Status shape:
      adapter_ref, cli, installed (bool), authed ("yes"|"no"|"unknown"),
      ok (bool), message_ko (non-empty plain Korean).
      Gemini API-key paths also carry api_key_env_present and
      credential_validity. A preflight never proves key validity because it never
      makes a live provider call.
    """

    from support.connection.agent_adapter import (
        _GEMINI_API_KEY_ENV_VARS,
        _LOCAL_CLI_SPECS,
        _PROVIDER_INSTALL_HINT_KO,
        _PROVIDER_LOGIN_HINT_KO,
        probe_local_cli_adapter,
    )

    ref = adapter_ref.strip() if isinstance(adapter_ref, str) else ""

    # adapter:local is in-process: no CLI, always ready.
    if ref == ADAPTER_LOCAL:
        return {
            "adapter_ref": ADAPTER_LOCAL,
            "cli": "",
            "installed": True,
            "authed": "yes",
            "ok": True,
            "message_ko": "준비 완료 ✅ (별도 설치/로그인이 필요 없어요)",
        }
    if ref == ADAPTER_CHAT_SESSION:
        return {
            "adapter_ref": ADAPTER_CHAT_SESSION,
            "cli": "",
            "installed": True,
            "authed": "unknown",
            "ok": True,
            "message_ko": "chat-session은 CLI를 실행하지 않고 작업 봉투를 parked로 기록해요.",
        }
    # Retired or unknown adapter refs: clear message, no raise.
    spec = _LOCAL_CLI_SPECS.get(ref)
    if spec is None:
        return {
            "adapter_ref": ref,
            "cli": "",
            "installed": False,
            "authed": "unknown",
            "ok": False,
            "message_ko": (
                "알 수 없는 provider예요. 지원하는 것: adapter:local, "
                "adapter:codex-local, adapter:claude-local, adapter:gemini-local, "
                "adapter:codex-fugu-local, adapter:chat-session"
            ),
        }

    cli = spec.executable_name
    installed = True if command_runner is not None else shutil.which(cli) is not None
    gemini_local_key_present = False
    if ref == ADAPTER_GEMINI_LOCAL:
        gemini_local_key_present = any(
            (os.environ.get(env_var) or "").strip() for env_var in _GEMINI_API_KEY_ENV_VARS
        )
    if not installed:
        status = {
            "adapter_ref": ref,
            "cli": cli,
            "installed": False,
            "authed": "unknown",
            "ok": False,
            "message_ko": _PROVIDER_INSTALL_HINT_KO.get(
                ref, f"{cli}가 설치돼 있지 않아요. {cli}를 먼저 설치하세요."
            ),
        }
        if ref == ADAPTER_GEMINI_LOCAL:
            status.update(
                {
                    "api_key_env_present": gemini_local_key_present,
                    "credential_validity": "not_proven",
                }
            )
        return status

    # Installed: run only the cheap --version probe (short timeout). This proves
    # the CLI runs but NOT that an OAuth login is present. Gemini's API-key path
    # is different: a present API-key env var is enough to classify the adapter as
    # ready while credential_validity stays explicitly not_proven because no live
    # provider call happens here.
    authed = "unknown"
    version_ok = False
    try:
        probe_local_cli_adapter(ref, timeout_seconds=8, command_runner=command_runner)
        version_ok = True
    except Exception:
        # Any failure (CLI errored, timed out, redaction tripped) -> stay
        # best-effort. We do NOT raise; missing/broken auth must never crash.
        version_ok = False

    if version_ok:
        if ref == ADAPTER_GEMINI_LOCAL:
            if gemini_local_key_present:
                return {
                    "adapter_ref": ref,
                    "cli": cli,
                    "installed": True,
                    "authed": "yes",
                    "ok": True,
                    "api_key_env_present": True,
                    "credential_validity": "not_proven",
                    "message_ko": (
                        "준비 일부 확인 ✅ (gemini CLI 설치 + API key 환경변수 존재). "
                        "단, 키 유효성은 doctor가 실호출 없이 증명하지 않아요; "
                        "실행 중 API_KEY_INVALID가 나오면 새 Gemini API 키를 설정하세요."
                    ),
                }
            return {
                "adapter_ref": ref,
                "cli": cli,
                "installed": True,
                "authed": "no",
                "ok": False,
                "api_key_env_present": False,
                "credential_validity": "not_proven",
                "message_ko": (
                    "gemini CLI는 설치됐지만 API key 환경변수가 없어요 → "
                    "GEMINI_API_KEY 또는 GOOGLE_API_KEY 를 설정하세요."
                ),
            }
        return {
            "adapter_ref": ref,
            "cli": cli,
            "installed": True,
            "authed": authed,
            "ok": True,
            "message_ko": (
                f"준비 완료 ✅ ({cli} 설치됨). 로그인이 안 돼 있으면 → "
                f"{_PROVIDER_LOGIN_HINT_KO.get(ref, cli + ' login')}"
            ),
        }

    # Installed but the cheap probe did not succeed: most often a login is
    # needed. Give the friendly login line, never a stack-trace.
    status = {
        "adapter_ref": ref,
        "cli": cli,
        "installed": True,
        "authed": "unknown",
        "ok": False,
        "message_ko": (
            f"{cli} 로그인이 필요해요 → "
            f"{_PROVIDER_LOGIN_HINT_KO.get(ref, cli + ' login')}"
        ),
    }
    if ref == ADAPTER_GEMINI_LOCAL:
        status.update(
            {
                "api_key_env_present": gemini_local_key_present,
                "credential_validity": "not_proven",
                "message_ko": (
                    "gemini CLI/API key 상태를 확인해야 해요 → "
                    "GEMINI_API_KEY 또는 GOOGLE_API_KEY 를 설정하고 gemini --version 을 확인하세요. "
                    "키 유효성은 doctor가 실호출 없이 증명하지 않아요."
                ),
            }
        )
    return status


# TrackA-A1 METER (codex token usage): `codex exec --json` emits one JSONL event
# per line on stdout, ending each turn with
#   {"type":"turn.completed","usage":{"input_tokens","cached_input_tokens",
#    "output_tokens","reasoning_output_tokens"}}
# We parse the LAST turn.completed.usage and expose the four counters under a
# STABLE codex-vocabulary key set. These are SUPPORT FACTS only -- the meter
# writer (support/recording/adapter_usage_meter.py) maps the subset that overlaps
# the WORKFLOW_IMPORT_USAGE_METRIC_KEYS allowlist; nothing here is a verdict.
CODEX_TURN_COMPLETED_USAGE_KEYS: tuple[str, ...] = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)


def codex_usage_from_json_stdout(stdout: str) -> Mapping[str, Any] | None:
    """Parse the LAST ``turn.completed`` usage from ``codex exec --json`` stdout.

    Returns a mapping carrying ONLY the codex usage counter keys, or ``None`` when
    the stdout is empty / not JSONL / has no ``turn.completed`` with a ``usage``
    block (older codex without ``--json``). Per the graceful-fallback contract,
    absent is ``None`` and a missing individual counter is recorded as ``None``;
    this function NEVER fabricates a count and NEVER raises on malformed input.
    """

    if not isinstance(stdout, str) or not stdout.strip():
        return None
    last_usage: Mapping[str, Any] | None = None
    for line in stdout.splitlines():
        text = line.strip()
        if not text or text[0] != "{":
            continue
        try:
            event = json.loads(text)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, Mapping):
            continue
        if event.get("type") != "turn.completed":
            continue
        usage = event.get("usage")
        if isinstance(usage, Mapping):
            last_usage = usage
    if last_usage is None:
        return None
    parsed: dict[str, Any] = {}
    for key in CODEX_TURN_COMPLETED_USAGE_KEYS:
        value = last_usage.get(key)
        parsed[key] = value if isinstance(value, int) and not isinstance(value, bool) else None
    return parsed


# TrackA-A1 ROOT FIX (TEXT SAFETY + GATE-NO-MEASURE): the assistant message TEXT
# keys codex emits inside its `--json` JSONL events. When the --output-last-message
# file is empty/unwritten under --json, we recover the assistant text from THESE
# event fields ONLY -- never by handing raw JSONL back as the assistant text. The
# raw JSONL must never become output_text (it would leak the event structure into
# output_excerpt and, worse, let a JSONL "usage" key be lifted into
# AgentFact.returned via _extract_required_return_fields -- a gate-no-measure
# violation). Tolerant of the known codex item/message event shapes; on no match
# returns "" (treated as no-text), NEVER the raw JSONL stdout.
_CODEX_ASSISTANT_MESSAGE_EVENT_TYPES: frozenset[str] = frozenset(
    {"item.completed", "agent_message", "assistant_message", "response.completed"}
)
_CODEX_ASSISTANT_MESSAGE_ITEM_TYPES: frozenset[str] = frozenset(
    {"agent_message", "assistant_message", "message"}
)
_CODEX_ASSISTANT_TEXT_KEYS: tuple[str, ...] = ("text", "message", "content")


def codex_assistant_text_from_json_stdout(stdout: str) -> str:
    """Recover the LAST assistant message TEXT from ``codex exec --json`` stdout.

    Returns the assistant's text content drawn from the JSONL event fields, or the
    empty string when no assistant-message event/text is present. It NEVER returns
    the raw JSONL and NEVER raises on malformed input. This is the safe replacement
    for the old ``completed.stdout`` fallback: under ``--json`` the stdout is raw
    JSONL events, so the previous fallback leaked event structure (and any embedded
    ``usage`` key) into the assistant-text path. Here only real message text is ever
    returned; absence is the empty string, treated downstream as no-text.
    """

    if not isinstance(stdout, str) or not stdout.strip():
        return ""
    last_text = ""
    for line in stdout.splitlines():
        text = line.strip()
        if not text or text[0] != "{":
            continue
        try:
            event = json.loads(text)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, Mapping):
            continue
        if event.get("type") not in _CODEX_ASSISTANT_MESSAGE_EVENT_TYPES:
            continue
        candidate = _codex_event_assistant_text(event)
        if candidate:
            last_text = candidate
    return last_text


def _codex_event_assistant_text(event: Mapping[str, Any]) -> str:
    """Pull assistant text out of one codex JSONL event mapping (best-effort)."""

    # Newer codex nests the message under an "item" with its own type/text.
    item = event.get("item")
    if isinstance(item, Mapping):
        item_type = item.get("type")
        if item_type is None or item_type in _CODEX_ASSISTANT_MESSAGE_ITEM_TYPES:
            nested = _codex_text_from_keys(item)
            if nested:
                return nested
    return _codex_text_from_keys(event)


def _codex_text_from_keys(source: Mapping[str, Any]) -> str:
    for key in _CODEX_ASSISTANT_TEXT_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
        # codex content can be a list of {type:"text"/"output_text", text:...} parts.
        if isinstance(value, list):
            joined = "".join(
                part.get("text", "")
                for part in value
                if isinstance(part, Mapping) and isinstance(part.get("text"), str)
            )
            if joined.strip():
                return joined
    return ""


# TrackA-A1 MAJOR FIX (graceful older-codex --json): a codex binary that does not
# understand ``--json`` exits NONZERO with an "unrecognized/unknown --json"-shaped
# diagnostic. The meter is INSTRUMENTATION; it must NEVER break a build. So when a
# ``--json`` invocation fails with this signature we retry ONCE without ``--json``
# (the meter just records absent usage). Any OTHER nonzero failure is a real build
# error and is returned untouched for the normal nonzero path.
_CODEX_JSON_UNSUPPORTED_MARKERS: tuple[str, ...] = (
    "unrecognized",
    "unknown option",
    "unexpected argument",
    "no such option",
    "invalid option",
    "unknown flag",
    "unknown argument",
)


def _codex_json_unsupported(completed: LocalCliCompleted) -> bool:
    """True when a nonzero codex result looks like ``--json`` is unsupported."""

    if completed.return_code == 0:
        return False
    haystack = f"{completed.stderr}\n{completed.stdout}".lower()
    if "--json" not in haystack and "json" not in haystack:
        return False
    return any(marker in haystack for marker in _CODEX_JSON_UNSUPPORTED_MARKERS)


def _run_or_delegate(
    args: Sequence[str],
    cwd: Path,
    timeout_seconds: int,
    command_runner: CommandRunner | None,
    *,
    env: Mapping[str, str] | None = None,
) -> LocalCliCompleted:
    if command_runner is not None:
        if env is not None and _command_runner_accepts_env(command_runner):
            return command_runner(args, cwd, timeout_seconds, env=env)
        return command_runner(args, cwd, timeout_seconds)
    return _run_command(args, cwd=cwd, timeout_seconds=timeout_seconds, env=env)


def _command_runner_accepts_env(command_runner: CommandRunner) -> bool:
    call = getattr(command_runner, "__call__", None)
    candidates = (command_runner, call) if call is not None else (command_runner,)
    for candidate in candidates:
        code = getattr(candidate, "__code__", None)
        if code is None:
            continue
        arg_names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
        if "env" in arg_names:
            return True
    return False


def _codex_stall_watchdog_config(timeout_seconds: int | float) -> _CodexStallWatchdogConfig | None:
    # CONNECT-STALL THRESHOLD COUPLING (TrackB 0619, codex-review F1/F2): the
    # watchdog threshold is COUPLED to the adapter timeout. The subprocess
    # communicate(timeout=timeout_seconds) raises a PLAIN (untagged) TimeoutExpired
    # at the adapter deadline; if the dead-signature threshold is >= that deadline
    # the watchdog can NEVER fire and a connect-stall is mislabeled
    # local_cli_timeout. At the production default (adapter_timeout_seconds=120 in
    # driver.py / run.py) the unclamped 150s default was pure dead code. So the
    # EFFECTIVE threshold is clamped to (timeout_seconds - 2*poll): the dead-signature
    # needs TWO samples to confirm (it anchors at the FIRST dead poll, ~poll seconds
    # in), so the watchdog can only confirm-and-fire before the adapter deadline when
    # it has two polls of room (timeout-poll alone fires AT the deadline = still dead
    # code, proven by execution). The env override is clamped the SAME way so an
    # operator-set env can never reintroduce the inversion.
    # Reject non-finite timeouts (NaN/inf) as well as <= 0 (codex re-review): a NaN
    # timeout slips past a bare <=0 check (nan comparisons are False) and would yield
    # an unclamped active watchdog. Same idiom as _float_env_or_default below.
    if (
        timeout_seconds != timeout_seconds
        or timeout_seconds in {float("inf"), float("-inf")}
        or timeout_seconds <= 0
    ):
        return None
    poll = _float_env_or_default(
        _CODEX_STALL_WATCHDOG_POLL_ENV,
        float(_CODEX_STALL_WATCHDOG_DEFAULT_POLL_SECONDS),
    )
    if poll is None or poll <= 0:
        return None
    # F2: reject env values <= 0 (and NaN/inf via _float_env_or_default) -> fall
    # back to the 150 default. The chosen threshold is then F1-clamped below.
    env_threshold = _float_env_or_default(_CODEX_STALL_WATCHDOG_THRESHOLD_ENV, None)
    if env_threshold is not None and env_threshold > 0:
        chosen_threshold = env_threshold
    else:
        chosen_threshold = float(_CODEX_STALL_WATCHDOG_DEFAULT_THRESHOLD_SECONDS)
    # F1: cap the chosen threshold so it fires BEFORE the adapter deadline. Two polls
    # of room (not one): the dead-signature needs 2 samples, anchored at the first
    # dead poll, so timeout-poll would only confirm AT the deadline (dead code).
    effective_threshold = min(chosen_threshold, float(timeout_seconds) - 2 * poll)
    # Require room for at least 2 health samples before the deadline; otherwise the
    # run is too short to sample a dead-signature, so the adapter timeout is itself
    # the fast-fail -> watchdog OFF.
    if effective_threshold < 2 * poll:
        return None
    return _CodexStallWatchdogConfig(threshold_seconds=effective_threshold, poll_seconds=poll)


def _float_env_or_default(name: str, default: float | None) -> float | None:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return None
    if parsed != parsed or parsed in {float("inf"), float("-inf")}:
        return None
    return parsed


def _codex_cli_watchdog_applies(args: Sequence[str]) -> bool:
    return bool(args) and Path(str(args[0])).name == "codex"


def _communicate_with_optional_codex_stall_watchdog(
    proc: "subprocess.Popen[str]",
    args: Sequence[str],
    *,
    timeout_seconds: int | float,
    watchdog_config: _CodexStallWatchdogConfig | None = None,
    health_probe: Callable[["subprocess.Popen[str]"], _CodexCliHealth | None] | None = None,
    clock: Callable[[], float] | None = None,
) -> tuple[str | None, str | None]:
    if not _codex_cli_watchdog_applies(args):
        return proc.communicate(timeout=timeout_seconds)
    config = watchdog_config
    if config is None:
        config = _codex_stall_watchdog_config(timeout_seconds)
    if config is None:
        return proc.communicate(timeout=timeout_seconds)

    health = health_probe or _codex_cli_health_sample
    monotonic = clock or time.monotonic
    deadline = monotonic() + float(timeout_seconds)
    previous_sample = health(proc)
    dead_signature_since: float | None = None

    while True:
        now = monotonic()
        remaining = deadline - now
        if remaining <= 0:
            raise subprocess.TimeoutExpired(cmd=tuple(str(part) for part in args), timeout=timeout_seconds)
        try:
            return proc.communicate(timeout=min(config.poll_seconds, remaining))
        except subprocess.TimeoutExpired as exc:
            now = monotonic()
            if now >= deadline:
                raise
            current_sample = health(proc)
            if _codex_dead_connection_signature(previous_sample, current_sample):
                if dead_signature_since is None:
                    dead_signature_since = now
                if now - dead_signature_since >= config.threshold_seconds:
                    stall_exc = subprocess.TimeoutExpired(
                        cmd=_safe_timeout_cmd(args),
                        timeout=config.threshold_seconds,
                    )
                    setattr(stall_exc, _TIMEOUT_REAP_REASON_ATTR, "stall")
                    # SUPPORT FACTS ONLY (TrackB 0619 step E): carry the last
                    # health-sample triple + how long the dead-connection signature
                    # persisted so the reap journal can record WHY this was reaped as
                    # a connect-stall. No Agent-fault label, no Link decision -- these
                    # are raw observations of the dead worker at reap time.
                    setattr(
                        stall_exc,
                        _STALL_DEAD_SIGNATURE_ATTR,
                        _stall_dead_signature_facts(current_sample, now - dead_signature_since),
                    )
                    raise stall_exc from exc
            else:
                dead_signature_since = None
            previous_sample = current_sample


def _safe_timeout_cmd(args: Sequence[str]) -> tuple[str, ...]:
    executable = Path(str(args[0])).name if args else "codex"
    if executable == "codex":
        return ("codex", "exec")
    return (executable,)


def _codex_dead_connection_signature(
    previous_sample: _CodexCliHealth | None,
    current_sample: _CodexCliHealth | None,
) -> bool:
    if previous_sample is None or current_sample is None:
        return False
    if not previous_sample.process_running or not current_sample.process_running:
        return False
    if previous_sample.child_count != 0 or current_sample.child_count != 0:
        return False
    if previous_sample.established_socket_count != 0 or current_sample.established_socket_count != 0:
        return False
    if current_sample.cpu_seconds != previous_sample.cpu_seconds:
        return False
    return True


def _codex_cli_health_sample(proc: "subprocess.Popen[str]") -> _CodexCliHealth | None:
    if proc.poll() is not None:
        return _CodexCliHealth(
            process_running=False,
            child_count=0,
            established_socket_count=0,
            cpu_seconds=0.0,
        )
    rows = _process_snapshot_rows()
    if rows is None:
        return None
    root_pid = int(proc.pid)
    root_row = rows.get(root_pid)
    if root_row is None:
        return None
    related_pids = _related_process_ids(root_pid, root_row.pgid, rows)
    if not related_pids:
        return None
    established_sockets = _established_tcp_socket_count(related_pids)
    if established_sockets is None:
        return None
    cpu_seconds = sum(rows[pid].cpu_seconds for pid in related_pids if pid in rows)
    return _CodexCliHealth(
        process_running=True,
        child_count=len(related_pids - {root_pid}),
        established_socket_count=established_sockets,
        cpu_seconds=cpu_seconds,
    )


def _process_snapshot_rows() -> dict[int, _ProcessSnapshotRow] | None:
    try:
        completed = subprocess.run(
            ["ps", "-axo", "pid=,ppid=,pgid=,time="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=_CODEX_STALL_WATCHDOG_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    rows: dict[int, _ProcessSnapshotRow] = {}
    for line in completed.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) != 4:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
            pgid = int(parts[2])
        except ValueError:
            continue
        cpu_seconds = _parse_ps_cpu_seconds(parts[3])
        if cpu_seconds is None:
            continue
        rows[pid] = _ProcessSnapshotRow(ppid=ppid, pgid=pgid, cpu_seconds=cpu_seconds)
    return rows


def _parse_ps_cpu_seconds(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    days = 0
    if "-" in text:
        day_text, text = text.split("-", 1)
        try:
            days = int(day_text)
        except ValueError:
            return None
    parts = text.split(":")
    try:
        if len(parts) == 2:
            hours = 0
            minutes = int(parts[0])
            seconds = float(parts[1])
        elif len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
        else:
            return None
    except ValueError:
        return None
    return float((days * 24 * 60 * 60) + (hours * 60 * 60) + (minutes * 60)) + seconds


def _related_process_ids(
    root_pid: int,
    root_pgid: int,
    rows: Mapping[int, _ProcessSnapshotRow],
) -> set[int]:
    related = {pid for pid, row in rows.items() if row.pgid == root_pgid}
    related.add(root_pid)
    frontier = [root_pid]
    while frontier:
        parent = frontier.pop()
        for pid, row in rows.items():
            if row.ppid == parent and pid not in related:
                related.add(pid)
                frontier.append(pid)
    return {pid for pid in related if pid in rows}


def _established_tcp_socket_count(pids: set[int]) -> int | None:
    if not pids:
        return None
    try:
        completed = subprocess.run(
            [
                "lsof",
                "-nP",
                "-a",
                "-p",
                ",".join(str(pid) for pid in sorted(pids)),
                "-iTCP",
                "-sTCP:ESTABLISHED",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=_CODEX_STALL_WATCHDOG_PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode not in {0, 1}:
        return None
    if not completed.stdout.strip():
        if completed.stderr.strip():
            return None
        return 0
    return sum(
        1
        for line in completed.stdout.splitlines()[1:]
        if "TCP" in line and "ESTABLISHED" in line
    )


def _timeout_expired_reap_reason(exc: subprocess.TimeoutExpired) -> str:
    reason = getattr(exc, _TIMEOUT_REAP_REASON_ATTR, "")
    return reason if reason == "stall" else "timeout"


def _stall_dead_signature_facts(
    last_sample: _CodexCliHealth | None,
    dead_signature_seconds: float,
) -> dict[str, Any]:
    """Raw dead-connection observation for the reap journal (SUPPORT FACTS ONLY).

    Records the last health-sample triple (child_count, established_socket_count,
    cpu_seconds) the watchdog saw plus how long the dead-connection signature
    persisted before the threshold tripped. No fault attribution, no Movement
    decision -- only the numbers, so an operator can see the dead worker forensics.
    """

    facts: dict[str, Any] = {
        "dead_signature_seconds": round(float(dead_signature_seconds), 3),
    }
    if last_sample is not None:
        facts["child_count"] = last_sample.child_count
        facts["established_socket_count"] = last_sample.established_socket_count
        facts["cpu_seconds"] = last_sample.cpu_seconds
    return facts


def _timeout_expired_stall_dead_signature(
    exc: subprocess.TimeoutExpired,
) -> Mapping[str, Any] | None:
    facts = getattr(exc, _STALL_DEAD_SIGNATURE_ATTR, None)
    if isinstance(facts, Mapping):
        return facts
    return None


def _timeout_stream_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return ""


def _merge_timeout_streams(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        text = _timeout_stream_text(value)
        if text and text not in parts:
            parts.append(text)
    return "\n".join(parts)


def _drain_timeout_process_output(
    proc: "subprocess.Popen[str]",
) -> tuple[str, str]:
    try:
        stdout, stderr = proc.communicate(timeout=1)
    except Exception:
        return "", ""
    return stdout or "", stderr or ""


def _attach_timeout_partial_output(
    exc: subprocess.TimeoutExpired,
    *,
    proc: "subprocess.Popen[str]",
) -> None:
    drained_stdout, drained_stderr = _drain_timeout_process_output(proc)
    stdout = _merge_timeout_streams(getattr(exc, "output", None), drained_stdout)
    stderr = _merge_timeout_streams(getattr(exc, "stderr", None), drained_stderr)
    if stdout:
        setattr(exc, _TIMEOUT_PARTIAL_STDOUT_ATTR, stdout)
    if stderr:
        setattr(exc, _TIMEOUT_PARTIAL_STDERR_ATTR, stderr)


def _timeout_expired_partial_output(exc: subprocess.TimeoutExpired) -> Mapping[str, str]:
    """Return support-only partial stdout/stderr captured from a timed-out CLI.

    The values are raw process streams. Callers that persist them must redact and
    excerpt first; this helper only preserves otherwise-lost timeout diagnostics.
    """

    partial: dict[str, str] = {}
    stdout = getattr(exc, _TIMEOUT_PARTIAL_STDOUT_ATTR, "")
    stderr = getattr(exc, _TIMEOUT_PARTIAL_STDERR_ATTR, "")
    if isinstance(stdout, str) and stdout:
        partial["stdout"] = stdout
    if isinstance(stderr, str) and stderr:
        partial["stderr"] = stderr
    return partial


def _reap_timeout_process_group(proc: "subprocess.Popen[str]", *, reason: str) -> None:
    if reason == "stall":
        _signal_process_group(proc, signal.SIGTERM)
        try:
            proc.wait(timeout=_CODEX_STALL_WATCHDOG_SIGTERM_GRACE_SECONDS)
            return
        except subprocess.TimeoutExpired:
            pass
    _signal_process_group(proc, signal.SIGKILL)
    proc.wait()


def _signal_process_group(proc: "subprocess.Popen[str]", sig: signal.Signals) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except (ProcessLookupError, PermissionError):
        pass


def _run_text_cli_command(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> LocalCliCompleted:
    from support.connection.agent_adapter import LocalCliCompleted

    proc = subprocess.Popen(
        list(args),
        cwd=str(cwd),
        text=True,
        # stdin=DEVNULL gives the child an IMMEDIATE EOF on fd 0. codex/claude/gemini
        # `exec` unconditionally read() stdin at startup; if BRICK inherited a pipe/FIFO
        # whose write-end is held open with no data and no EOF, that startup read blocks
        # FOREVER (0 CPU, 0 sockets) to the adapter timeout -- the "connect-stall". BRICK
        # passes the prompt as a positional/flag argv item (never via stdin), so DEVNULL
        # cannot break any input path. This is the PRIMARY structural cure; the watchdog
        # stays as defense-in-depth for genuine network hangs.
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    _journal_spawn(proc, args, cwd)
    try:
        stdout, stderr = _communicate_with_optional_codex_stall_watchdog(
            proc,
            args,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        reason = _timeout_expired_reap_reason(exc)
        _reap_timeout_process_group(proc, reason=reason)
        _attach_timeout_partial_output(exc, proc=proc)
        _journal_reap(
            proc,
            reason=reason,
            dead_signature=_timeout_expired_stall_dead_signature(exc),
        )
        raise
    _journal_reap(proc, reason="exit")
    return LocalCliCompleted(
        args=tuple(str(part) for part in args),
        return_code=proc.returncode,
        stdout=stdout or "",
        stderr=stderr or "",
    )


# Fixed path for the append-only adapter spawn journal. The env override exists
# ONLY so a test/probe can redirect it off the shared default; live use leaves it
# unset. Mirrors the native-dispatch context-path seam (single fixed /tmp default
# + BRICK_*_PATH override). RECORD-ONLY: this is a forensic trace of spawn/reap so
# an orphaned provider grandchild is traceable -- it is NOT a reaper.
_ADAPTER_SPAWN_JOURNAL_DEFAULT_PATH = os.path.join("/tmp", "brick-adapter-spawn-journal.jsonl")


def _adapter_spawn_journal_path() -> str:
    """Resolve the adapter spawn-journal file path (env-overridable seam)."""
    override = os.environ.get("BRICK_ADAPTER_SPAWN_JOURNAL_PATH")
    return override if override else _ADAPTER_SPAWN_JOURNAL_DEFAULT_PATH


def _journal_write(record: Mapping[str, Any]) -> None:
    """Append one JSONL record. Best-effort: NEVER raises into the adapter path."""
    try:
        line = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        path = _adapter_spawn_journal_path()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
    except Exception:
        # Forensic journal only -- a journal IO failure must not break a spawn.
        return


def _journal_spawn(proc: "subprocess.Popen[str]", args: Sequence[str], cwd: Path) -> None:
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = -1
    _journal_write(
        {
            "event": "spawn",
            "pid": proc.pid,
            "pgid": pgid,
            "argv0": Path(str(args[0])).name if args else "",
            "cwd": str(cwd),
            "started_at": time.time(),
        }
    )


def _journal_reap(
    proc: "subprocess.Popen[str]",
    *,
    reason: str,
    dead_signature: Mapping[str, Any] | None = None,
) -> None:
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = -1
    record: dict[str, Any] = {
        "event": "reap",
        "pid": proc.pid,
        "pgid": pgid,
        "reason": reason,
        "return_code": proc.returncode,
        "reaped_at": time.time(),
    }
    if dead_signature is not None:
        # SUPPORT FACTS ONLY: last health triple + dead-signature duration the
        # connect-stall watchdog observed. Forensic trace, not a fault label.
        record["dead_signature"] = dict(dead_signature)
    _journal_write(record)


def _run_command(
    args: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
    env: Mapping[str, str] | None = None,
) -> LocalCliCompleted:
    from support.connection.agent_adapter import LocalCliCompleted

    _validate_command_args(args)
    proc = subprocess.Popen(
        list(args),
        cwd=str(cwd),
        env=dict(env) if env is not None else None,
        text=True,
        # stdin=DEVNULL gives the child an IMMEDIATE EOF on fd 0. codex/claude/gemini
        # `exec` unconditionally read() stdin at startup; if BRICK inherited a pipe/FIFO
        # whose write-end is held open with no data and no EOF, that startup read blocks
        # FOREVER (0 CPU, 0 sockets) to the adapter timeout -- the "connect-stall". BRICK
        # passes the prompt as a positional/flag argv item (never via stdin), so DEVNULL
        # cannot break any input path. This is the PRIMARY structural cure; the watchdog
        # stays as defense-in-depth for genuine network hangs.
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,  # proc becomes its own process-group leader (setsid)
    )
    _journal_spawn(proc, args, cwd)  # best-effort; never raises
    try:
        stdout, stderr = _communicate_with_optional_codex_stall_watchdog(
            proc,
            args,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        reason = _timeout_expired_reap_reason(exc)
        _reap_timeout_process_group(proc, reason=reason)
        _attach_timeout_partial_output(exc, proc=proc)
        _journal_reap(
            proc,
            reason=reason,
            dead_signature=_timeout_expired_stall_dead_signature(exc),
        )
        # SAME TimeoutExpired re-raised. run.py _adapter_error_kind reads the
        # reap_reason tag: a 'stall' reap -> 'local_cli_connect_stall', a plain
        # timeout -> 'local_cli_timeout' (both route to the same adapter-error HOLD).
        raise
    _journal_reap(proc, reason="exit")
    return LocalCliCompleted(
        args=tuple(str(part) for part in args),
        return_code=proc.returncode,
        stdout=stdout or "",
        stderr=stderr or "",
    )


def _validate_command_args(args: Sequence[str]) -> None:
    if not args:
        raise ValueError("local CLI args must not be empty")
    executable = Path(str(args[0])).name
    if executable not in {"codex", "claude", "gemini"}:
        raise ValueError("local CLI executable is not allowlisted")
    for item in args:
        text = str(item)
        if "\x00" in text or "\n" in text:
            raise ValueError("local CLI arg contains unsupported control text")
        _reject_secret_text("local_cli_arg", text)

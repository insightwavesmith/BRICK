"""design_ai_text_seams checker-lib leaf.

Support checker mechanics only. This module observes mocked provider text seams;
it authors no axis crossing and decides no Movement, success, or quality.
"""

from __future__ import annotations

import importlib
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import KernelResult, ProfileError, _ensure_import_identity


def run_design_ai_text_seams(repo: Path) -> KernelResult:
    """DESIGN-AI-TEXT-SEAM-0616 checker for Claude/Codex prompt -> text wrappers.

    FIREs, IN-PROCESS with mock command_runners only:
      (a) normal text returns byte-matching raw text and emits the declared CLI
          shapes.
      (b) command_runner FileNotFoundError propagates cleanly.
      (c) command_runner TimeoutExpired propagates unchanged.
      (d) blank/whitespace output raises clean ValueError.
      (e) secret-looking output is rejected by the adapter secret scrub.
      (f) codex stall watchdog fires only on the conservative dead-connection
          signature, while slow-but-live / unavailable-health probes keep the
          existing wait behavior.

    Mutation-RED: removing any raise/parse/scrub behavior above turns this check
    red without invoking a live provider CLI.
    """
    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    adapter_gemini_http = importlib.import_module("brick_protocol.support.connection.adapter_gemini_http")
    adapter_subprocess = importlib.import_module("brick_protocol.support.connection.adapter_subprocess")
    run_module = importlib.import_module("brick_protocol.support.operator.run")
    walker_resume = importlib.import_module("brick_protocol.support.operator.walker_resume")
    inspected = 0

    claude_prompt = "Design prompt\nwith two lines"
    claude_captured: dict[str, Any] = {}

    def _claude_ok_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        claude_captured["args"] = tuple(args)
        claude_captured["cwd"] = cwd
        claude_captured["timeout"] = timeout
        return adapter.LocalCliCompleted(
            args=tuple(args),
            return_code=0,
            stdout="CLAUDE raw text\n",
            stderr="",
        )

    claude_text = adapter_gemini_http.invoke_claude_text(
        claude_prompt,
        model_name="claude-test-model",
        timeout_seconds=41,
        command_runner=_claude_ok_runner,
    )
    if claude_text != "CLAUDE raw text\n":
        raise ProfileError("design_ai_text_seams: claude raw text was not returned byte-matching")
    expected_claude_args = (
        "claude",
        "-p",
        claude_prompt,
        "--output-format",
        "text",
        "--model",
        "claude-test-model",
    )
    if claude_captured.get("args") != expected_claude_args:
        raise ProfileError(
            f"design_ai_text_seams: claude args drifted: {claude_captured.get('args')!r}"
        )
    if claude_captured.get("cwd") != repo or claude_captured.get("timeout") != 41:
        raise ProfileError("design_ai_text_seams: claude cwd/timeout was not carried")
    inspected += 1

    codex_prompt = "Compose a short graph proposal."
    codex_captured: dict[str, Any] = {}

    def _codex_ok_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        codex_captured["args"] = tuple(args)
        codex_captured["cwd"] = cwd
        codex_captured["timeout"] = timeout
        output_path = Path(args[args.index("--output-last-message") + 1])
        codex_captured["output_path"] = output_path
        output_path.write_text("CODEX raw text\n", encoding="utf-8")
        return adapter.LocalCliCompleted(
            args=tuple(args),
            return_code=0,
            stdout="ignored stdout\n",
            stderr="",
        )

    codex_text = adapter_gemini_http.invoke_codex_text(
        codex_prompt,
        model_name="codex-test-model",
        timeout_seconds=53,
        command_runner=_codex_ok_runner,
    )
    if codex_text != "CODEX raw text\n":
        raise ProfileError("design_ai_text_seams: codex temp-file text was not returned")
    codex_args = codex_captured.get("args")
    if not isinstance(codex_args, tuple):
        raise ProfileError("design_ai_text_seams: codex args were not captured")
    if codex_args[:4] != ("codex", "exec", "--sandbox", "read-only"):
        raise ProfileError(f"design_ai_text_seams: codex command prefix drifted: {codex_args!r}")
    if ("-m", "codex-test-model") != codex_args[4:6]:
        raise ProfileError("design_ai_text_seams: codex model arg was not carried")
    if "--output-last-message" not in codex_args or codex_args[-1] != codex_prompt:
        raise ProfileError("design_ai_text_seams: codex output-last-message/prompt shape drifted")
    output_path = codex_captured.get("output_path")
    if not isinstance(output_path, Path):
        raise ProfileError("design_ai_text_seams: codex output path was not captured")
    if output_path.exists():
        raise ProfileError("design_ai_text_seams: codex temp output file was not cleaned up")
    if codex_captured.get("cwd") != repo or codex_captured.get("timeout") != 53:
        raise ProfileError("design_ai_text_seams: codex cwd/timeout was not carried")
    inspected += 1

    def _expect_error(thunk: Callable[[], Any], error_type: type[BaseException], label: str) -> None:
        try:
            thunk()
        except error_type:
            return
        except Exception as exc:  # noqa: BLE001
            raise ProfileError(
                f"design_ai_text_seams: {label} raised {type(exc).__name__}, "
                f"expected {error_type.__name__}"
            ) from exc
        raise ProfileError(
            f"design_ai_text_seams: {label} did not raise {error_type.__name__} "
            "(mutation-RED guard)"
        )

    def _missing_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        raise FileNotFoundError(f"{Path(str(args[0])).name} missing")

    _expect_error(
        lambda: adapter_gemini_http.invoke_claude_text("p", command_runner=_missing_runner),
        FileNotFoundError,
        "claude missing executable",
    )
    _expect_error(
        lambda: adapter_gemini_http.invoke_codex_text("p", command_runner=_missing_runner),
        FileNotFoundError,
        "codex missing executable",
    )
    inspected += 1

    def _timeout_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        raise subprocess.TimeoutExpired(cmd=tuple(args), timeout=timeout)

    _expect_error(
        lambda: adapter_gemini_http.invoke_claude_text("p", timeout_seconds=7, command_runner=_timeout_runner),
        subprocess.TimeoutExpired,
        "claude timeout propagation",
    )
    _expect_error(
        lambda: adapter_gemini_http.invoke_codex_text("p", timeout_seconds=11, command_runner=_timeout_runner),
        subprocess.TimeoutExpired,
        "codex timeout propagation",
    )
    inspected += 1

    class _FakeCodexProc:
        pid = 982451653
        returncode: int | None = None

        def __init__(self, *, timeouts_before_return: int, clock_state: dict[str, float]) -> None:
            self.timeouts_before_return = timeouts_before_return
            self.clock_state = clock_state
            self.communicate_timeouts: list[float] = []

        def poll(self) -> int | None:
            return self.returncode

        def communicate(self, *, timeout: float) -> tuple[str, str]:
            self.communicate_timeouts.append(float(timeout))
            self.clock_state["now"] += float(timeout)
            if self.timeouts_before_return > 0:
                self.timeouts_before_return -= 1
                raise subprocess.TimeoutExpired(cmd=("codex", "exec"), timeout=timeout)
            self.returncode = 0
            return ("CODEX buffered final text\n", "")

    watchdog_config = adapter_subprocess._CodexStallWatchdogConfig(
        threshold_seconds=0.2,
        poll_seconds=0.1,
    )

    dead_clock = {"now": 0.0}
    dead_proc = _FakeCodexProc(timeouts_before_return=10, clock_state=dead_clock)
    dead_health = adapter_subprocess._CodexCliHealth(
        process_running=True,
        child_count=0,
        established_socket_count=0,
        cpu_seconds=12.0,
    )

    def _dead_health_probe(proc: Any) -> Any:
        del proc
        return dead_health

    try:
        adapter_subprocess._communicate_with_optional_codex_stall_watchdog(
            dead_proc,
            ("codex", "exec", "--output-last-message", "/tmp/ignored", "buffered prompt"),
            timeout_seconds=5,
            watchdog_config=watchdog_config,
            health_probe=_dead_health_probe,
            clock=lambda: dead_clock["now"],
        )
    except subprocess.TimeoutExpired as exc:
        if adapter_subprocess._timeout_expired_reap_reason(exc) != "stall":
            raise ProfileError("design_ai_text_seams: codex dead-connection timeout was not typed as stall")
        # CONNECT-STALL LABEL SPLIT (TrackB 0619): a stall-tagged timeout now maps to
        # the DISTINCT local_cli_connect_stall kind (no longer flattened into the
        # generic local_cli_timeout). The dedicated codex_connect_stall_classification
        # checker pins the full A/B contract; here we only keep design-AI-seam's stall
        # path tracking the new label so it does not assert the retired flattening.
        if run_module._adapter_error_kind(exc) != "local_cli_connect_stall":
            raise ProfileError("design_ai_text_seams: codex stall did not map to local_cli_connect_stall")
        if not walker_resume._adapter_error_hold_without_return({"hold_reason": "adapter_error_frontier"}):
            raise ProfileError("design_ai_text_seams: adapter-error HOLD seam no longer recognizes the frontier")
    else:
        raise ProfileError("design_ai_text_seams: codex dead-connection watchdog did not fire")
    if max(dead_proc.communicate_timeouts) > watchdog_config.poll_seconds:
        raise ProfileError("design_ai_text_seams: codex watchdog fell back to one full communicate wait")
    if dead_clock["now"] >= 5:
        raise ProfileError("design_ai_text_seams: codex watchdog waited until the full adapter timeout")

    live_clock = {"now": 0.0}
    live_proc = _FakeCodexProc(timeouts_before_return=3, clock_state=live_clock)
    live_samples = [
        adapter_subprocess._CodexCliHealth(True, 1, 0, 20.0),
        adapter_subprocess._CodexCliHealth(True, 1, 0, 20.0),
        adapter_subprocess._CodexCliHealth(True, 0, 1, 20.0),
        adapter_subprocess._CodexCliHealth(True, 0, 0, 20.5),
    ]

    def _live_health_probe(proc: Any) -> Any:
        del proc
        return live_samples.pop(0)

    live_stdout, live_stderr = adapter_subprocess._communicate_with_optional_codex_stall_watchdog(
        live_proc,
        ("codex", "exec", "--output-last-message", "/tmp/ignored", "buffered prompt"),
        timeout_seconds=5,
        watchdog_config=adapter_subprocess._CodexStallWatchdogConfig(
            threshold_seconds=0.0,
            poll_seconds=0.1,
        ),
        health_probe=_live_health_probe,
        clock=lambda: live_clock["now"],
    )
    if (live_stdout, live_stderr) != ("CODEX buffered final text\n", ""):
        raise ProfileError("design_ai_text_seams: codex slow-live fixture did not preserve final output")
    if live_proc.returncode != 0:
        raise ProfileError("design_ai_text_seams: codex slow-live fixture was killed")

    unknown_clock = {"now": 0.0}
    unknown_proc = _FakeCodexProc(timeouts_before_return=2, clock_state=unknown_clock)
    unknown_stdout, unknown_stderr = adapter_subprocess._communicate_with_optional_codex_stall_watchdog(
        unknown_proc,
        ("codex", "exec", "--output-last-message", "/tmp/ignored", "buffered prompt"),
        timeout_seconds=5,
        watchdog_config=adapter_subprocess._CodexStallWatchdogConfig(
            threshold_seconds=0.0,
            poll_seconds=0.1,
        ),
        health_probe=lambda proc: None,
        clock=lambda: unknown_clock["now"],
    )
    if (unknown_stdout, unknown_stderr) != ("CODEX buffered final text\n", ""):
        raise ProfileError("design_ai_text_seams: codex unknown-health fixture did not degrade to waiting")
    inspected += 1

    def _claude_blank_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        return adapter.LocalCliCompleted(args=tuple(args), return_code=0, stdout=" \n\t", stderr="")

    def _codex_blank_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        Path(args[args.index("--output-last-message") + 1]).write_text(" \n\t", encoding="utf-8")
        return adapter.LocalCliCompleted(args=tuple(args), return_code=0, stdout="", stderr="")

    _expect_error(
        lambda: adapter_gemini_http.invoke_claude_text("p", command_runner=_claude_blank_runner),
        ValueError,
        "claude blank output",
    )
    _expect_error(
        lambda: adapter_gemini_http.invoke_codex_text("p", command_runner=_codex_blank_runner),
        ValueError,
        "codex blank output",
    )
    inspected += 1

    fake_secret = "sk-ABCDEFGHIJKLMNOP"

    def _claude_secret_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        return adapter.LocalCliCompleted(args=tuple(args), return_code=0, stdout=fake_secret, stderr="")

    def _codex_secret_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        Path(args[args.index("--output-last-message") + 1]).write_text(fake_secret, encoding="utf-8")
        return adapter.LocalCliCompleted(args=tuple(args), return_code=0, stdout="", stderr="")

    _expect_error(
        lambda: adapter_gemini_http.invoke_claude_text("p", command_runner=_claude_secret_runner),
        ValueError,
        "claude secret output",
    )
    _expect_error(
        lambda: adapter_gemini_http.invoke_codex_text("p", command_runner=_codex_secret_runner),
        ValueError,
        "codex secret output",
    )
    inspected += 1

    return KernelResult(
        check_id="design_ai_text_seams",
        inspected=inspected,
        output=(
            "design-AI text seams passed: claude/codex prompt-to-text wrappers "
            "returned mocked raw text, preserved CLI shape/cwd/timeout, propagated "
            "FileNotFoundError and TimeoutExpired, rejected blank output, rejected "
            "secret-looking output, pinned codex dead-connection fast-fail without "
            "killing slow-live/unknown-health fixtures, and called NO live provider CLI "
            f"({inspected} group(s) inspected)."
        ),
    )

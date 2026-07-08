#!/usr/bin/env python3
"""Interactive provider intake checker.

Uses only temp ``BRICK_HOME`` fixtures and injected prompt/command functions. It
never reads stdin or the caller's live ``~/.brick/providers.yaml``.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)


class InteractiveProviderIntakeError(RuntimeError):
    pass


@contextmanager
def _temp_brick_home() -> Iterator[Path]:
    previous_home = os.environ.get("BRICK_HOME")
    with tempfile.TemporaryDirectory(prefix="bp-interactive-provider-intake-") as tmp:
        os.environ["BRICK_HOME"] = tmp
        try:
            yield Path(tmp)
        finally:
            if previous_home is None:
                os.environ.pop("BRICK_HOME", None)
            else:
                os.environ["BRICK_HOME"] = previous_home


def _scripted_prompt(responses: Sequence[str]) -> Any:
    iterator = iter(responses)

    def prompt_func(_prompt: str) -> str:
        try:
            return next(iterator)
        except StopIteration as exc:
            raise InteractiveProviderIntakeError("scripted prompt exhausted") from exc

    return prompt_func


def _ready_command_runner(args: Sequence[str], _cwd: Path, _timeout_seconds: int, **_kwargs: Any) -> Any:
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

    return LocalCliCompleted(
        args=tuple(str(arg) for arg in args),
        return_code=0,
        stdout="fixture version\n",
        stderr="",
    )


def _assert_registry_model(home: Path, *, adapter_ref: str, model_ref: str) -> None:
    import yaml

    path = home / "providers.yaml"
    if not path.is_file():
        raise InteractiveProviderIntakeError("fixture providers.yaml was not written")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = loaded.get("providers")
    if not isinstance(rows, list):
        raise InteractiveProviderIntakeError("fixture providers.yaml providers row missing")
    matches = [
        row for row in rows
        if isinstance(row, dict) and row.get("adapter_ref") == adapter_ref
    ]
    if len(matches) != 1:
        raise InteractiveProviderIntakeError(f"expected one provider row for {adapter_ref}")
    if matches[0].get("model_ref") != model_ref:
        raise InteractiveProviderIntakeError(
            f"expected model_ref {model_ref}, got {matches[0].get('model_ref')}"
        )


def _fixture_args() -> Any:
    import argparse as _argparse

    return _argparse.Namespace(
        repo=".",
        host="codex",
        output_root=None,
        skip_build=True,
        skip_plugin=True,
        skip_recording=True,
        skip_verify=True,
        slack_bot_token=None,
        slack_channel_id=None,
        non_interactive=True,
        json=True,
    )


def run(repo: Path) -> None:
    from brick_protocol.support.operator import cli, onboard

    intake = onboard.run_interactive_provider_intake(
        prompt_func=_scripted_prompt(["codex", "model:codex:gpt-5"]),
        host_default="claude",
    )
    if intake.get("host") != "codex":
        raise InteractiveProviderIntakeError("scripted provider alias was not collected")
    if intake.get("model_ref") != "model:codex:gpt-5":
        raise InteractiveProviderIntakeError("scripted model_ref was not collected")

    fallback = onboard.run_interactive_provider_intake(
        prompt_func=_scripted_prompt(["codex", "model:gemini:default"]),
        host_default="codex",
    )
    if fallback.get("model_ref") != "model:codex:default":
        raise InteractiveProviderIntakeError("invalid model_ref did not fall back to adapter default")

    skipped = onboard.run_interactive_provider_intake(
        prompt_func=_scripted_prompt(["skip"]),
        host_default="codex",
    )
    if skipped.get("skipped") is not True:
        raise InteractiveProviderIntakeError("scripted skip was not recorded")

    with _temp_brick_home() as home:
        result = onboard.run_provider_register_step(
            "codex",
            model_ref=str(intake["model_ref"]),
            command_runner=_ready_command_runner,
        )
        if result.get("action") != "registered":
            raise InteractiveProviderIntakeError(f"provider fixture was not registered: {result!r}")
        _assert_registry_model(
            home,
            adapter_ref="adapter:codex-local",
            model_ref="model:codex:gpt-5",
        )

    original_intake = cli.onboard.run_interactive_provider_intake
    original_wizard = cli.onboard.run_install_wizard
    observed: dict[str, Any] = {}

    def raising_intake(**_kwargs: Any) -> dict[str, Any]:
        raise InteractiveProviderIntakeError("non-interactive init called prompt collector")

    def fixture_wizard(**kwargs: Any) -> dict[str, Any]:
        observed.update(kwargs)
        return {
            "steps": {"present": {}, "provider_register": {}, "slack": {}, "onboard": {}},
            "ordered_steps": ["present", "provider_register", "slack", "onboard"],
            "ok": True,
        }

    try:
        cli.onboard.run_interactive_provider_intake = raising_intake
        cli.onboard.run_install_wizard = fixture_wizard
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            if cli._cmd_init(_fixture_args()) != 0:
                raise InteractiveProviderIntakeError("non-interactive fixture init returned non-zero")
    finally:
        cli.onboard.run_interactive_provider_intake = original_intake
        cli.onboard.run_install_wizard = original_wizard
    packet_stdout = stdout.getvalue()
    if '"interactive_provider_intake"' in packet_stdout:
        raise InteractiveProviderIntakeError("non-interactive JSON grew interactive_provider_intake field")
    if observed.get("host") != "codex":
        raise InteractiveProviderIntakeError("non-interactive init did not preserve default host")
    if observed.get("provider_model_ref") is not None:
        raise InteractiveProviderIntakeError("non-interactive init supplied an interactive model_ref")

    original_stdin = cli.sys.stdin
    original_input = cli.input if hasattr(cli, "input") else None
    observed_skip: dict[str, Any] = {}

    class _Tty:
        def isatty(self) -> bool:
            return True

    def skip_intake(**_kwargs: Any) -> dict[str, Any]:
        return dict(skipped)

    def fixture_skip_wizard(**kwargs: Any) -> dict[str, Any]:
        observed_skip.update(kwargs)
        return {
            "steps": {"present": {}, "provider_register": {}, "slack": {}, "onboard": {}},
            "ordered_steps": ["present", "provider_register", "slack", "onboard"],
            "ok": True,
        }

    try:
        cli.sys.stdin = _Tty()
        cli.onboard.run_interactive_provider_intake = skip_intake
        cli.onboard.run_install_wizard = fixture_skip_wizard
        with contextlib.redirect_stdout(io.StringIO()):
            if cli._cmd_init(_fixture_args()) != 0:
                raise InteractiveProviderIntakeError("interactive skip fixture init returned non-zero")
    finally:
        cli.sys.stdin = original_stdin
        cli.onboard.run_interactive_provider_intake = original_intake
        cli.onboard.run_install_wizard = original_wizard
        if original_input is not None:
            cli.input = original_input
    if observed_skip.get("host") != "codex":
        raise InteractiveProviderIntakeError("non_interactive=True should override TTY prompt gate")

    interactive_args = _fixture_args()
    interactive_args.non_interactive = False
    try:
        cli.sys.stdin = _Tty()
        cli.onboard.run_interactive_provider_intake = skip_intake
        cli.onboard.run_install_wizard = fixture_skip_wizard
        with contextlib.redirect_stdout(io.StringIO()):
            if cli._cmd_init(interactive_args) != 0:
                raise InteractiveProviderIntakeError("interactive skip fixture init returned non-zero")
    finally:
        cli.sys.stdin = original_stdin
        cli.onboard.run_interactive_provider_intake = original_intake
        cli.onboard.run_install_wizard = original_wizard
    if observed_skip.get("host") != "local":
        raise InteractiveProviderIntakeError("interactive skip did not choose local no-registration host")
    if repo.name == "":
        raise InteractiveProviderIntakeError("repo path fixture was empty")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repo root to inspect")
    args = parser.parse_args(argv)
    try:
        run(Path(args.repo).resolve())
    except InteractiveProviderIntakeError as exc:
        print(f"interactive_provider_intake rejected evidence: {exc}")
        return 1
    print(
        "interactive_provider_intake green: scripted intake, temp registry model "
        "pin, and non-interactive no-prompt fixture passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

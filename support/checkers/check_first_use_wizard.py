#!/usr/bin/env python3
"""Check the FIRST_USE.md generation branch of ``brick init``.

Support evidence only: this checker drives simulated CLI packets in temp
output roots. It does not call providers, choose Movement, or judge quality.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
from support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)


FIRST_USE_FILENAME = "FIRST_USE.md"
EXPECTED_DISCLAIMER = "이건 예제입니다 -- 실제 빌딩은 `brick auth login` 후 `--real-provider`."
REQUIRED_TEXTS = (
    EXPECTED_DISCLAIMER,
    "brick auth login",
    "--real-provider",
    "first ready provider-backed observed-write adapter",
    "falls back to `adapter:local`",
    "adapter:local",
    "customer_visible_frontier_state",
    "frontier_complete",
    "customer_visible_not_ready",
    "`brick build` returning exit 0 means the CLI returned support evidence",
    "It is not a phase PASS",
    "`frontier_kind` is `complete`",
    "renders as `not_ready`",
    "inspect `evidence_root`",
    "Agent adapter evidence",
    "materialized-step",
    "Provider readiness evidence",
    "target=gemini",
    "api_key_env_present=yes",
    "credential_validity=not_proven",
    "not source truth",
    "not Movement authority",
)


class FirstUseWizardError(ValueError):
    """Raised when FIRST_USE.md support evidence is missing or drifted."""


def _fake_doctor_packet() -> dict[str, Any]:
    return {
        "rows": [
            {
                "target": "python",
                "ok": True,
                "message_ko": "python observed for first-use checker fixture",
            },
            {
                "target": "repo",
                "ok": True,
                "message_ko": "repo observed for first-use checker fixture",
            },
            {
                "target": "gemini",
                "adapter_ref": "adapter:gemini-local",
                "ok": True,
                "installed": True,
                "authed": "unknown",
                "api_key_env_present": True,
                "credential_validity": "not_proven",
                "message_ko": (
                    "gemini fixture observed API-key presence; credential validity "
                    "is not proven without a live provider call"
                ),
            },
        ],
        "symptom_table": [],
    }


def _fake_wizard_packet(*, example_ok: bool) -> dict[str, Any]:
    """The install-wizard packet shape ``_cmd_init`` reads to decide FIRST_USE.md.

    INSTALL-WIZARD-0623: ``brick init`` now routes through
    ``onboard.run_install_wizard`` (doctor + plugin + slack + onboard example),
    NOT the old ``cli._run_build``. So the checker patches THIS seam: a controlled
    packet whose ``steps.present`` is the fake doctor and whose
    ``steps.onboard.example_result`` drives the success / build_error branch. The
    behavior under test (FIRST_USE.md generated on a good example, none on a
    failure) is unchanged -- only the internal seam name moved."""

    example_result: dict[str, Any] = (
        {
            "ok": True,
            "ran": True,
            "building_id": "first-use-checker-fixture",
            "adapter_ref": "adapter:local",
            "chain_preset_ref": "building-chain-preset:onboarding-example-graph",
            "evidence_root": "",
            "frontier_kind": "complete",
            "customer_visible_frontier_state": "frontier_complete",
            "customer_visible_not_ready": False,
            "customer_visible_frontier_message": (
                "frontier complete: evidence closed for this Building. "
                "This remains support evidence, not source truth or quality judgment."
            ),
            "materialized_step_adapters": [
                {
                    "step_ref": "materialized-step",
                    "selected_adapter_ref": "adapter:codex-local",
                    "selected_model_ref": "model:codex:default",
                }
            ],
        }
        if example_ok
        else {
            "ok": False,
            "ran": True,
            "error_kind": "RuntimeError",
            "error_message": "checker simulated build_error",
        }
    )
    # The fixture mirrors the REAL wizard shape (run_install_wizard): ordered_steps
    # is the actual steps-dict key order (so steps[key] always resolves), the 6-phase
    # human story lives in phase_narrative, and the hard gate ``ok`` is fail-closed
    # (explicit True only). _cmd_init reads steps.present + steps.onboard.example_result.
    steps = {
        "present": _fake_doctor_packet(),
        "onboard": {"example_result": example_result},
    }
    return {
        "kind": "install-wizard",
        "ordered_steps": list(steps.keys()),
        "phase_narrative": ["present", "plugin", "slack", "onboard", "verify"],
        "steps": steps,
        "ok": example_ok is True,
        "advisory_step_ok": {},
        "not_proven": [],
        "verify_note": "step 6 (verify) is skipped under the checker drive",
    }


@contextlib.contextmanager
def _patched_init_dependencies(
    cli: Any,
    *,
    wizard_func: Callable[..., Mapping[str, Any]],
) -> Iterator[None]:
    # INSTALL-WIZARD-0623: ``_cmd_init`` routes through ``onboard.run_install_wizard``
    # (doctor + plugin install + slack + onboard example), so patch THAT seam to a
    # controlled packet. Patching it also keeps the checker hermetic: the real wizard
    # would shell out (``claude mcp add``), write ~/.claude / ~/.codex / ~/.brick, and
    # run a live example build -- none of which a support checker may cause.
    original_run_install_wizard = cli.onboard.run_install_wizard
    cli.onboard.run_install_wizard = wizard_func
    try:
        yield
    finally:
        cli.onboard.run_install_wizard = original_run_install_wizard


def _run_cli_init(cli: Any, repo: Path, output_root: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    # --skip-verify: the wizard's step-6 runs ``check_profile --all``; a checker that
    # drives ``init`` WITHOUT this would recurse into the whole suite (init -> --all ->
    # first_use_wizard -> init -> ...). The FIRST_USE.md branch under test does not need
    # the verify step. --skip-plugin / --skip-recording belt-and-suspenders the hermetic
    # drive even though the wizard seam itself is patched out above.
    argv = [
        "init",
        "--repo",
        str(repo),
        "--output-root",
        str(output_root),
        "--timeout",
        "1",
        "--skip-verify",
        "--skip-plugin",
        "--skip-recording",
    ]
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = int(cli.main(argv))
    return code, stdout.getvalue(), stderr.getvalue()


def _assert_first_use_document(path: Path) -> str:
    if not path.is_file():
        raise FirstUseWizardError(f"FIRST_USE.md was not generated at {path}")
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in REQUIRED_TEXTS if needle not in text]
    if missing:
        raise FirstUseWizardError(f"FIRST_USE.md missing required text: {missing}")
    return text


def _assert_disclaimer_mutation_red(path: Path, original_text: str) -> None:
    mutated = "\n".join(
        line for line in original_text.splitlines() if line.strip() != EXPECTED_DISCLAIMER
    )
    path.write_text(mutated + "\n", encoding="utf-8")
    try:
        _assert_first_use_document(path)
    except FirstUseWizardError:
        return
    raise FirstUseWizardError("removing the example-stub disclaimer did not drive RED")


def _assert_referenced_commands_resolve(cli: Any) -> None:
    # FIRST_USE.md's funnel tells the customer to run `brick auth login` and a
    # `--real-provider` build. Pin that those are REAL CLI commands, not just
    # text in the doc -- a phantom command in the funnel silently breaks the
    # onboarding spine (the string check above passes while the command errors).
    parser = cli.build_parser()
    for argv in (["auth", "login"], ["build", "--real-provider", "--task", "x"]):
        try:
            parser.parse_args(argv)
        except SystemExit as exc:
            raise FirstUseWizardError(
                "FIRST_USE.md references `brick "
                + " ".join(argv)
                + "` but the CLI does not resolve it (argparse exited "
                + f"{exc.code}); the onboarding funnel points at a phantom command"
            ) from exc


def run_check(repo: Path) -> str:
    import brick_protocol.support.operator.cli as cli

    _assert_referenced_commands_resolve(cli)

    with tempfile.TemporaryDirectory(prefix="bp-first-use-success-") as raw:
        output_root = Path(raw) / "builds"

        def wizard_ok(*_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
            return _fake_wizard_packet(example_ok=True)

        with _patched_init_dependencies(cli, wizard_func=wizard_ok):
            code, stdout, stderr = _run_cli_init(cli, repo, output_root)
        if code != 0:
            raise FirstUseWizardError(
                f"simulated init returned {code}; stdout={stdout!r}; stderr={stderr!r}"
            )
        if f"next: read {FIRST_USE_FILENAME}" not in stdout:
            raise FirstUseWizardError("init output did not print the FIRST_USE.md funnel line")
        first_use_path = output_root / FIRST_USE_FILENAME
        text = _assert_first_use_document(first_use_path)
        _assert_disclaimer_mutation_red(first_use_path, text)

    with tempfile.TemporaryDirectory(prefix="bp-first-use-failure-") as raw:
        output_root = Path(raw) / "builds"

        def wizard_failed(*_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
            return _fake_wizard_packet(example_ok=False)

        with _patched_init_dependencies(cli, wizard_func=wizard_failed):
            code, stdout, stderr = _run_cli_init(cli, repo, output_root)
        if code != 1:
            raise FirstUseWizardError(
                f"simulated failing init returned {code}; stdout={stdout!r}; stderr={stderr!r}"
            )
        if (output_root / FIRST_USE_FILENAME).exists():
            raise FirstUseWizardError("FIRST_USE.md was generated on build_error")
        if f"next: read {FIRST_USE_FILENAME}" in stdout:
            raise FirstUseWizardError("build_error output printed the FIRST_USE.md funnel line")

    return (
        "first_use_wizard observed: simulated init generated FIRST_USE.md with "
        "example-stub disclaimer and next-step funnel; disclaimer-removal probe "
        "rejected; simulated build_error wrote no FIRST_USE.md."
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        repo = Path(args.repo).resolve()
        if not repo.is_dir():
            raise FirstUseWizardError(f"--repo must be a directory: {repo}")
        print(run_check(repo))
        print(
            "proof limit: support checker evidence only; not source truth, "
            "success judgment, quality judgment, or Movement authority."
        )
        return 0
    except FirstUseWizardError as exc:
        print(f"first_use_wizard rejected evidence: {exc}")
        print(
            "proof limit: support checker evidence only; not source truth, "
            "success judgment, quality judgment, or Movement authority."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

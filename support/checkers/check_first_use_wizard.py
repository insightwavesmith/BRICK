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
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_IMPORT_IDENTITY_ROOT = _REPO_ROOT / "support" / "import_identity"
if str(_IMPORT_IDENTITY_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPORT_IDENTITY_ROOT))


FIRST_USE_FILENAME = "FIRST_USE.md"
EXPECTED_DISCLAIMER = "이건 예제입니다 -- 실제 빌딩은 `brick auth login` 후 `--real-provider`."
REQUIRED_TEXTS = (
    EXPECTED_DISCLAIMER,
    "brick auth login",
    "--real-provider",
    "adapter:local",
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
        ],
        "symptom_table": [],
    }


def _fake_build_packet(repo: Path, output_root: Path) -> dict[str, Any]:
    return {
        "command": "build",
        "repo_root": str(repo),
        "output_root": str(output_root),
        "building_id": "first-use-checker-fixture",
        "declared_by": "coo",
        "task_source_basis": "task_source_ref",
        "chain_preset_ref": "building-chain-preset:onboarding-example-graph",
        "adapter_ref": "adapter:local",
        "isolation_mode": "checker-simulated",
        "isolation_reason": "checker fixture avoids live provider calls",
        "base_sha": "checker-fixture",
        "worktree_path": "",
        "evidence_root": str(output_root / "first-use-checker-fixture"),
        "frontier_kind": "complete",
        "commit_sha": "",
        "worktree_disposed": True,
        "proof_limits": ["support evidence only"],
        "not_proven": ["real provider behavior"],
    }


@contextlib.contextmanager
def _patched_init_dependencies(
    cli: Any,
    *,
    build_func: Callable[[Any], Mapping[str, Any]],
) -> Iterator[None]:
    original_run_build = cli._run_build
    original_run_doctor = cli.onboard.run_doctor
    cli._run_build = build_func
    cli.onboard.run_doctor = _fake_doctor_packet
    try:
        yield
    finally:
        cli._run_build = original_run_build
        cli.onboard.run_doctor = original_run_doctor


def _run_cli_init(cli: Any, repo: Path, output_root: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    argv = [
        "init",
        "--repo",
        str(repo),
        "--output-root",
        str(output_root),
        "--timeout",
        "1",
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


def run_check(repo: Path) -> str:
    import brick_protocol.support.operator.cli as cli

    with tempfile.TemporaryDirectory(prefix="bp-first-use-success-") as raw:
        output_root = Path(raw) / "builds"

        def build_ok(_args: Any) -> Mapping[str, Any]:
            return _fake_build_packet(repo, output_root)

        with _patched_init_dependencies(cli, build_func=build_ok):
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

        def build_raises(_args: Any) -> Mapping[str, Any]:
            raise RuntimeError("checker simulated build_error")

        with _patched_init_dependencies(cli, build_func=build_raises):
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

"""Stale-build masking RED probe for run_wheel_smoke (checker companion).

Support evidence only. This probe proves that ``run_wheel_smoke`` cannot be
MASKED by a stale in-tree setuptools ``build/`` intermediate: even when a
previous build's ``build/lib`` operator files are present in the source tree,
shrinking the pyproject packages list so operator is no longer declared must
still turn the wheel smoke RED (operator=0 in the wheel), because the checker
builds from an isolated copy that omits the stale ``build/``.

Two fixture cases run over a throwaway copy of the real repo (the real repo
working tree is never mutated):

  * ``stale_build_shrunk_packages_red`` -- seed a stale build/lib operator tree
    AND remove operator from the declared packages. EXPECT RED (ProfileError
    naming operator missing). If run_wheel_smoke reused the stale build/, this
    would falsely pass -- the RED here is the masking-impossible proof.
  * ``stale_build_full_packages_green`` -- seed the same stale build/lib but
    keep the full packages list. EXPECT green (operator>0), proving the build
    itself works from the isolated copy and the RED above is caused by the
    declared-packages shrink, not a broken build.

This probe authors no axis crossing, decides nothing, and judges no quality.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPORT_IDENTITY_ROOT = REPO_ROOT / "support" / "import_identity"
for _import_root in (REPO_ROOT, IMPORT_IDENTITY_ROOT):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))

from support.checkers.lib.install_release_export_lint_check import run_wheel_smoke
from support.checkers.lib.yaml_subset import KernelResult, ProfileError

# Stale artifact seeded into the fixture's in-tree build/ before the smoke runs.
# It is intentionally a file that does NOT exist in the real operator source, so
# if the checker ever reused the stale build/ the leak would be unmistakable.
_STALE_OPERATOR_REL = (
    "build/lib/brick_protocol/support/operator/STALE_MASK_SENTINEL.py"
)
_STALE_OPERATOR_EXTRA_REL = (
    "build/lib/brick_protocol/support/operator/cli.py"
)

_COPY_IGNORE_NAMES = frozenset(
    {
        ".git",
        "build",
        "dist",
        "__pycache__",
        ".venv",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "project",
        ".DS_Store",
    }
)


def _fixture_copy_ignore(_directory: str, names: list[str]) -> list[str]:
    return [
        name
        for name in names
        if name in _COPY_IGNORE_NAMES
        or name.endswith(".egg-info")
        or name.endswith(".pyc")
    ]


def _copy_repo(dest: Path) -> None:
    shutil.copytree(
        REPO_ROOT,
        dest,
        ignore=_fixture_copy_ignore,
        symlinks=False,
        ignore_dangling_symlinks=True,
    )


def _seed_stale_build(fixture_repo: Path) -> list[str]:
    seeded: list[str] = []
    for rel in (_STALE_OPERATOR_REL, _STALE_OPERATOR_EXTRA_REL):
        target = fixture_repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "# stale build/lib intermediate seeded by the masking RED probe\n"
            "STALE_MASK = True\n",
            encoding="utf-8",
        )
        seeded.append(rel)
    return seeded


def _shrink_packages_remove_operator(fixture_repo: Path) -> bool:
    pyproject = fixture_repo / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    before = text
    text = text.replace('  "brick_protocol.support.operator",\n', "", 1)
    text = text.replace(
        '"brick_protocol.support.operator" = "support/operator"\n', "", 1
    )
    pyproject.write_text(text, encoding="utf-8")
    return "support.operator" not in _packages_block(text)


def _packages_block(text: str) -> str:
    start = text.find("packages = [")
    if start == -1:
        return ""
    end = text.find("]", start)
    return text[start : end + 1] if end != -1 else text[start:]


def _run_case(
    *,
    case_id: str,
    shrink_packages: bool,
    expect_red: bool,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"wheel-smoke-mask-{case_id}-") as tmp:
        fixture_repo = Path(tmp) / "repo"
        _copy_repo(fixture_repo)
        seeded = _seed_stale_build(fixture_repo)
        shrunk = False
        if shrink_packages:
            shrunk = _shrink_packages_remove_operator(fixture_repo)

        raised: ProfileError | None = None
        result: KernelResult | None = None
        try:
            result = run_wheel_smoke(fixture_repo)
        except ProfileError as exc:
            raised = exc

        went_red = raised is not None and "operator" in str(raised)
        # An environment report (build backend/venv unavailable) is neither the
        # expected RED nor a real green; surface it honestly.
        environment_report = (
            result is not None
            and "environment report" in (result.output or "")
        )
        passed = (went_red == expect_red) and not environment_report
        return {
            "case_id": case_id,
            "seeded_stale_build": seeded,
            "packages_shrunk_operator_removed": shrunk if shrink_packages else False,
            "expected": "RED" if expect_red else "green",
            "observed_red": went_red,
            "profile_error_message": str(raised) if raised is not None else None,
            "green_output_excerpt": (result.output[:400] if result is not None else None),
            "environment_report": environment_report,
            "passed": bool(passed),
        }


def run_stale_build_masking_probe() -> dict[str, Any]:
    cases = [
        _run_case(
            case_id="stale_build_shrunk_packages_red",
            shrink_packages=True,
            expect_red=True,
        ),
        _run_case(
            case_id="stale_build_full_packages_green",
            shrink_packages=False,
            expect_red=False,
        ),
    ]
    return {
        "schema": "wheel-smoke-stale-build-masking-red-probe/v1",
        "all_passed": all(case["passed"] for case in cases),
        "proof_limits": [
            "support evidence only",
            "proves stale in-tree build/ cannot mask a wheel packages-list "
            "regression; does not prove source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "future setuptools/uv build behavior",
            "real publication behavior",
        ],
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = run_stale_build_masking_probe()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

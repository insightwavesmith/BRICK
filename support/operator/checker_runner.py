"""Allowlisted checker-profile subprocess invocation (P3d concern module).

Runs a forbidden-part-filtered checker profile and records each command's
return code + output excerpt as support evidence. It runs no commit/push, it
is not source truth, success judgment, quality judgment, or Movement
authority. Reaches no axis."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from brick_protocol.support.operator.building_operation_common import (
    DEFAULT_BUILDINGS_ROOT,
    REPO_ROOT,
    _rel,
    _repo_path,
)


DEFAULT_CHECKER_PROFILE: tuple[tuple[str, ...], ...] = (
    ("python3", "support/checkers/check_package_path_admission.py", "--repo", "."),
    ("python3", "support/checkers/check_axis_contract_projection.py", "--repo", "."),
    # CLOSE-1/F5: removed check_simple_run0_one_run_surface.py and
    # check_agent_adapter0_single_surface.py — both deleted in earlier surface
    # work; they made run_checker_profile() return code 2. Remaining entries all
    # reference existing checker files.
    ("python3", "support/checkers/check_building_lifecycle_path_shape.py", "--repo", "."),
    ("git", "diff", "--check"),
)


FORBIDDEN_COMMAND_PARTS = frozenset(
    {
        "commit",
        "push",
        "reset",
        "checkout",
        "credential",
        "secret",
        "token",
        "auth",
    }
)


@dataclass(frozen=True)
class BuildingPreflight:
    """Support-only preflight observation for a declared Building Plan."""

    plan_path: str
    plan_exists: bool
    evidence_root: str
    evidence_root_exists: bool
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CheckerRun:
    """One checker command observation."""

    command: tuple[str, ...]
    return_code: int
    stdout_excerpt: str
    stderr_excerpt: str
    proof_limits: tuple[str, ...] = field(default_factory=tuple)


def open_preflight(
    plan_path: str | Path,
    *,
    repo_root: Path | str = REPO_ROOT,
    building_id: str = "",
    buildings_root: Path | str | None = None,
) -> BuildingPreflight:
    """Observe plan/evidence paths before a Building run.

    This does not create, edit, or classify the Building Plan.
    """

    repo = Path(repo_root).resolve()
    plan = _repo_path(repo, plan_path)
    root = Path(buildings_root).resolve() if buildings_root is not None else DEFAULT_BUILDINGS_ROOT
    evidence_root = root / (building_id or plan.stem)
    return BuildingPreflight(
        plan_path=_rel(repo, plan),
        plan_exists=plan.is_file(),
        evidence_root=_rel(repo, evidence_root),
        evidence_root_exists=evidence_root.is_dir(),
        proof_limits=(
            "support preflight only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ),
        not_proven=(
            "Building semantic correctness",
            "future run success",
            "checker result meaning",
        ),
    )


def checker_profile() -> tuple[tuple[str, ...], ...]:
    """Return the default support checker profile commands."""

    return DEFAULT_CHECKER_PROFILE


def run_checker_profile(
    commands: Iterable[Sequence[str]] | None = None,
    *,
    repo_root: Path | str = REPO_ROOT,
    timeout_seconds: int = 120,
) -> tuple[CheckerRun, ...]:
    """Run an allowlisted checker profile and return support observations."""

    repo = Path(repo_root).resolve()
    profile = tuple(commands or DEFAULT_CHECKER_PROFILE)
    results: list[CheckerRun] = []
    for raw_command in profile:
        command = _validate_checker_command(raw_command)
        completed = subprocess.run(
            _normalize_repo_args(command),
            cwd=str(repo),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        results.append(
            CheckerRun(
                command=command,
                return_code=completed.returncode,
                stdout_excerpt=_excerpt(completed.stdout),
                stderr_excerpt=_excerpt(completed.stderr),
                proof_limits=("checker run support evidence only",),
            )
        )
    return tuple(results)


def _validate_checker_command(command: Sequence[str]) -> tuple[str, ...]:
    parts = tuple(str(part).strip() for part in command)
    if not parts or any(not part for part in parts):
        raise ValueError("checker command parts must be non-empty")
    lowered = tuple(part.lower() for part in parts)
    if any(part in FORBIDDEN_COMMAND_PARTS for part in lowered):
        raise ValueError("operator helper must not run forbidden git/credential commands")
    if lowered[:2] == ("git", "diff") and tuple(lowered[2:]) == ("--check",):
        return parts
    if parts[0] == "python3" and len(parts) >= 2:
        checker = parts[1].replace("\\", "/")
        if checker.startswith("support/checkers/check_") and checker.endswith(".py"):
            return parts
    raise ValueError("operator helper checker profile only admits python3 support/checkers/check_*.py or git diff --check")


def _normalize_repo_args(command: Sequence[str]) -> list[str]:
    return ["." if part == str(REPO_ROOT) else str(part) for part in command]


def _excerpt(value: str, *, limit: int = 700) -> str:
    text = " ".join((value or "").replace("\r", " ").replace("\n", " ").split())
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text

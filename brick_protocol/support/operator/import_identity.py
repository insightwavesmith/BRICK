"""Operator import identity helper for checkout and wheel contexts.

Support mechanics only: this module observes whether the operator is running
from a source checkout or an installed distribution. It does not own Brick,
Agent, Link, source truth, success, quality, or Movement authority.
"""

from __future__ import annotations

import sys
import tomllib
from contextvars import ContextVar, Token
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any


PROJECT_DISTRIBUTION_NAME = "brick-protocol"
SOURCE_MARKER_REL = Path("pyproject.toml")
IMPORT_IDENTITY_REL = Path(".")
SOURCE_IMPORT_PACKAGE_REL = Path("brick_protocol/__init__.py")
_OFFICIAL_LAUNCH_TOKEN: ContextVar[object | None] = ContextVar(
    "brick_protocol_official_launch_token",
    default=None,
)


@dataclass(frozen=True)
class OperatorImportIdentity:
    mode: str
    repo_root: Path
    import_identity_root: Path | None
    distribution_name: str
    distribution_version: str


def _declared_project_name(pyproject_path: Path) -> str:
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(
            f"repo identity marker mismatch: unreadable {pyproject_path}"
        ) from exc
    project = data.get("project")
    if not isinstance(project, dict):
        return ""
    name = project.get("name")
    return name if isinstance(name, str) else ""


def _installed_distribution_version() -> str:
    try:
        return metadata.version(PROJECT_DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return ""


def resolve_operator_identity(anchor_file: str | Path) -> OperatorImportIdentity:
    """Resolve source-checkout or installed-wheel identity for an operator file.

    Source mode is admitted only when the expected checkout marker exists and
    declares ``project.name = "brick-protocol"``. If that marker is absent, the
    helper switches to installed mode and relies on ``importlib.metadata``;
    installed mode deliberately does not require a repo-root marker under
    site-packages.
    """

    anchor = Path(anchor_file).resolve()
    candidate_repo = anchor.parents[3]
    pyproject_path = candidate_repo / SOURCE_MARKER_REL
    if pyproject_path.exists():
        declared_name = _declared_project_name(pyproject_path)
        if declared_name != PROJECT_DISTRIBUTION_NAME:
            raise RuntimeError(
                "repo identity marker mismatch: "
                f"{pyproject_path} declares project.name={declared_name!r}"
            )
        import_identity_root = candidate_repo / IMPORT_IDENTITY_REL
        if not (candidate_repo / SOURCE_IMPORT_PACKAGE_REL).is_file():
            raise RuntimeError(
                "repo identity marker mismatch: missing "
                f"{candidate_repo / SOURCE_IMPORT_PACKAGE_REL}"
            )
        return OperatorImportIdentity(
            mode="source",
            repo_root=candidate_repo,
            import_identity_root=import_identity_root,
            distribution_name=PROJECT_DISTRIBUTION_NAME,
            distribution_version=_installed_distribution_version(),
        )

    version = _installed_distribution_version()
    if not version:
        raise RuntimeError(
            "installed Brick Protocol identity unavailable: "
            f"importlib.metadata could not find {PROJECT_DISTRIBUTION_NAME!r}"
        )
    return OperatorImportIdentity(
        mode="installed",
        repo_root=candidate_repo,
        import_identity_root=None,
        distribution_name=PROJECT_DISTRIBUTION_NAME,
        distribution_version=version,
    )


def install_source_import_paths(identity: OperatorImportIdentity) -> None:
    """Insert checkout import paths only for source mode."""

    if identity.mode != "source":
        return
    for entry in (identity.repo_root, identity.import_identity_root):
        if entry is None:
            continue
        entry_text = str(entry)
        if entry_text not in sys.path:
            sys.path.insert(0, entry_text)


def mint_official_launch_token() -> Token[object | None]:
    """Mint a process-local official-launch token for one CLI dispatch."""

    return _OFFICIAL_LAUNCH_TOKEN.set(object())


def reset_official_launch_token(token: Token[object | None]) -> None:
    """Reset the process-local official-launch token after CLI dispatch."""

    _OFFICIAL_LAUNCH_TOKEN.reset(token)


def suppress_official_launch_token_for_probe() -> Token[object | None]:
    """Temporarily shadow any inherited launch token for direct-call probes."""

    return _OFFICIAL_LAUNCH_TOKEN.set(None)


def official_launch_token_observation() -> dict[str, Any]:
    """Observe token presence without authorizing or rejecting the walk."""

    present = _OFFICIAL_LAUNCH_TOKEN.get() is not None
    return {
        "kind": "official_launch_token_observation",
        "token_present": present,
        "observation_mode": "observe_only",
        "absence_action": "record_only_no_raise",
        "token_source": "brick_protocol.support.operator.cli.main",
        "proof_limits": [
            "process-scoped contextvars.ContextVar observation only",
            "not packet-supplied",
            "not credential or secret evidence",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "complete runtime process integrity outside this Python context",
            "future launcher behavior",
        ],
    }

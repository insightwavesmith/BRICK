"""Operator import identity helper for checkout and wheel contexts.

Support mechanics only: this module observes whether the operator is running
from a source checkout or an installed distribution. It does not own Brick,
Agent, Link, source truth, success, quality, or Movement authority.
"""

from __future__ import annotations

import inspect
import secrets
import sys
import tomllib
from contextvars import ContextVar, Token
from dataclasses import InitVar, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Mapping


PROJECT_DISTRIBUTION_NAME = "brick-protocol"
SOURCE_MARKER_REL = Path("pyproject.toml")
IMPORT_IDENTITY_REL = Path(".")
SOURCE_IMPORT_PACKAGE_REL = Path("brick_protocol/__init__.py")
PURE_DEV_D3_BUILDING_ID = "pure-dev-d3-r7-body-reland-0709c"
_OFFICIAL_LAUNCH_MINT_MODULES: frozenset[str] = frozenset(
    {
        "brick_protocol.support.operator.cli",
        "brick_protocol.support.operator.import_identity",
        "__main__",
    }
)
_OFFICIAL_LAUNCH_TOKEN: ContextVar[object | None] = ContextVar(
    "brick_protocol_official_launch_token",
    default=None,
)
_OFFICIAL_LAUNCH_MINT_KEY = object()
_MINTED_OFFICIAL_LAUNCH_NONCES: set[str] = set()


@dataclass(frozen=True)
class OfficialLaunchProof:
    """Process-local typed proof minted only by ``mint_official_launch_token``."""

    nonce: str
    minter_module: str
    _mint_key: InitVar[object | None] = None

    def __post_init__(self, _mint_key: object | None) -> None:
        if _mint_key is not _OFFICIAL_LAUNCH_MINT_KEY:
            raise RuntimeError(
                "official launch proof construction refused: "
                "mint only via mint_official_launch_token"
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


def _caller_frame() -> inspect.FrameInfo | None:
    frame = inspect.currentframe()
    if (
        frame is None
        or frame.f_back is None
        or frame.f_back.f_back is None
        or frame.f_back.f_back.f_back is None
    ):
        return None
    return inspect.getframeinfo(frame.f_back.f_back.f_back)


def _caller_module_name() -> str:
    frame = inspect.currentframe()
    if frame is None or frame.f_back is None or frame.f_back.f_back is None:
        return ""
    caller = frame.f_back.f_back
    return str(caller.f_globals.get("__name__") or "")


def _main_module_is_cli() -> bool:
    frame_info = _caller_frame()
    if frame_info is None or frame_info.function != "main":
        return False
    return Path(frame_info.filename).as_posix().endswith(
        "brick_protocol/support/operator/cli.py"
    )


def mint_official_launch_token() -> Token[object | None]:
    """Mint a process-local official-launch proof for one CLI dispatch.

    Mint is restricted to the CLI and checker fixture modules. Walker enforce
    still re-observes the live ContextVar via ``official_launch_token_observation``.
    """

    minter = _caller_module_name()
    admitted_main_cli = minter == "__main__" and _main_module_is_cli()
    admitted_module = minter in _OFFICIAL_LAUNCH_MINT_MODULES and minter != "__main__"
    admitted_checker = minter.endswith(".check_import_identity_modes")
    if not (admitted_module or admitted_main_cli or admitted_checker):
        raise RuntimeError(
            "official launch mint refused: caller module is not allowlisted "
            f"({minter or 'unknown'}); mint only from brick CLI / admitted probes"
        )
    proof = OfficialLaunchProof(
        nonce=secrets.token_hex(16),
        minter_module=minter or "unknown",
        _mint_key=_OFFICIAL_LAUNCH_MINT_KEY,
    )
    _MINTED_OFFICIAL_LAUNCH_NONCES.add(proof.nonce)
    return _OFFICIAL_LAUNCH_TOKEN.set(proof)


def reset_official_launch_token(token: Token[object | None]) -> None:
    """Reset the process-local official-launch token after CLI dispatch."""

    _OFFICIAL_LAUNCH_TOKEN.reset(token)


def suppress_official_launch_token_for_probe() -> Token[object | None]:
    """Temporarily shadow any inherited launch token for direct-call probes."""

    return _OFFICIAL_LAUNCH_TOKEN.set(None)


def official_launch_token_observation() -> dict[str, Any]:
    """Observe process-local official-launch token presence (support fact only).

    Stage 3b plus D3 typed-proof hardening: token presence requires a live,
    module-minted ``OfficialLaunchProof``. Bare ContextVar values and unminted
    proofs are refused by ``enforce_official_launch_token``.
    """

    value = _OFFICIAL_LAUNCH_TOKEN.get()
    typed_proof = type(value) is OfficialLaunchProof
    present = typed_proof and value.nonce in _MINTED_OFFICIAL_LAUNCH_NONCES
    forged_non_proof = value is not None and not typed_proof
    forged_unminted_proof = typed_proof and not present
    return {
        "kind": "official_launch_token_observation",
        "token_present": present,
        "forged_non_proof_observed": forged_non_proof,
        "forged_unminted_proof_observed": forged_unminted_proof,
        "observation_mode": "gate_lethal",
        "absence_action": "raise_runtime_error",
        "token_source": "brick_protocol.support.operator.cli.main",
        "pure_dev_d3_building_id": PURE_DEV_D3_BUILDING_ID,
        "harden_ref": "official_launch_typed_proof_v1",
        "proof_limits": [
            "process-scoped contextvars.ContextVar observation only",
            "typed OfficialLaunchProof with module-minted nonce required for presence",
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
            "complete protection against deliberate private module-state mutation",
            "process-attested or cryptographic mint beyond module nonce registry",
            "public mint_official_launch_token export is callable by allowlisted in-process callers",
        ],
    }


def enforce_official_launch_token(
    observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage 3b lethal gate: refuse walker entry without a typed launch proof.

    Support mechanics only: always re-observes the live ContextVar through
    ``official_launch_token_observation``. Caller-supplied observation mappings
    are cross-check evidence only, never authority. Non-proof ContextVar values
    raise a distinct forge refusal. Does not judge success/quality/Movement.
    """

    live = official_launch_token_observation()
    if (
        live.get("forged_non_proof_observed") is True
        or live.get("forged_unminted_proof_observed") is True
    ):
        raise RuntimeError(
            "official launch proof forged: live process token is not a minted OfficialLaunchProof "
            "(L3-3b/R7-D1)"
        )
    if live.get("token_present") is True:
        if isinstance(observation, Mapping) and (
            observation.get("token_present") != live.get("token_present")
            or observation.get("forged_non_proof_observed")
            != live.get("forged_non_proof_observed")
            or observation.get("forged_unminted_proof_observed")
            != live.get("forged_unminted_proof_observed")
        ):
            raise RuntimeError(
                "official launch proof forged: caller-supplied observation disagrees "
                "with live process token (L3-3b/R7-D1)"
            )
        return live
    raise RuntimeError(
        "official launch token absent: walk only via brick CLI "
        "(brick build / brick resume / python -m brick_protocol.support.operator.cli). "
        "Direct in-process walker/run imports without cli.main mint are refused (L3-3b)."
    )

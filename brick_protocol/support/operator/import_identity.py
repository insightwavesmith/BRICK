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
_OFFICIAL_LAUNCH_MINT_BINDINGS: tuple[tuple[str, str, str], ...] = (
    (
        "brick_protocol/support/operator/cli.py",
        "brick_protocol.support.operator.cli",
        "main",
    ),
    (
        "brick_protocol/support/checkers/check_import_identity_modes.py",
        "brick_protocol.support.checkers.check_import_identity_modes",
        "_assert_official_launch_token_fixture",
    ),
    (
        "brick_protocol/support/checkers/check_route_v2_views.py",
        "brick_protocol.support.checkers.check_route_v2_views",
        "run",
    ),
    (
        "brick_protocol/support/checkers/check_building_operator_driver0.py",
        "brick_protocol.support.checkers.check_building_operator_driver0",
        "main",
    ),
    (
        "brick_protocol/support/checkers/check_assembly_equivalence.py",
        "brick_protocol.support.checkers.check_assembly_equivalence",
        "main",
    ),
    (
        "brick_protocol/support/checkers/lib/case_runners.py",
        "brick_protocol.support.checkers.lib.case_runners",
        "run_link_route_evidence_case",
    ),
    (
        "brick_protocol/support/checkers/lib/onboard_seam_check.py",
        "brick_protocol.support.checkers.lib.onboard_seam_check",
        "run_onboard_seam_case",
    ),
    (
        "brick_protocol/support/checkers/lib/onboard_smoke_check.py",
        "brick_protocol.support.checkers.lib.onboard_smoke_check",
        "run_onboard_smoke",
    ),
    (
        "brick_protocol/support/checkers/lib/step_output_drain_check.py",
        "brick_protocol.support.checkers.lib.step_output_drain_check",
        "_run_step_output_drain_plan",
    ),
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
    minter_file: str
    minter_function: str
    identity_mode: str
    identity_root: str
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


def _official_launch_binding(
    *,
    module_name: str,
    function_name: str,
    caller_file: Path,
    identity: OperatorImportIdentity,
) -> tuple[str, str, str] | None:
    """Return the exact admitted binding for one caller in this import identity.

    A module suffix or a bare ``__main__`` name is never enough. Source and wheel
    callers must execute the exact admitted relative file from the same checkout /
    installed distribution root that supplied this helper. ``__main__`` is accepted
    only when that exact admitted file is the executed script.
    """

    try:
        relative_file = caller_file.resolve().relative_to(identity.repo_root.resolve()).as_posix()
    except (OSError, ValueError):
        return None
    try:
        caller_global_file = caller_file.resolve()
    except OSError:
        return None
    if not caller_global_file.is_file():
        return None
    for admitted_file, admitted_module, admitted_function in _OFFICIAL_LAUNCH_MINT_BINDINGS:
        if relative_file != admitted_file or function_name != admitted_function:
            continue
        if module_name not in {admitted_module, "__main__"}:
            continue
        return admitted_file, admitted_module, admitted_function
    return None


def _official_launch_proof_binding_is_current(proof: OfficialLaunchProof) -> bool:
    """Whether ``proof`` is still bound to this exact import identity and file."""

    try:
        identity = resolve_operator_identity(__file__)
        identity_root = identity.repo_root.resolve()
        minter_path = (identity_root / proof.minter_file).resolve()
    except (OSError, RuntimeError):
        return False
    if proof.identity_mode != identity.mode or proof.identity_root != str(identity_root):
        return False
    binding = _official_launch_binding(
        module_name=proof.minter_module,
        function_name=proof.minter_function,
        caller_file=minter_path,
        identity=identity,
    )
    return binding is not None and binding[0] == proof.minter_file


def mint_official_launch_token() -> Token[object | None]:
    """Mint a process-local official-launch proof for one CLI dispatch.

    Mint is restricted to exact CLI/checker file + module + function bindings in
    the same checkout or installed distribution as this helper. Walker enforce
    still re-observes the live ContextVar via ``official_launch_token_observation``.
    """

    frame = inspect.currentframe()
    caller = frame.f_back if frame is not None else None
    minter = str(caller.f_globals.get("__name__") or "") if caller is not None else ""
    caller_global_file = str(caller.f_globals.get("__file__") or "") if caller is not None else ""
    caller_code_file = str(caller.f_code.co_filename or "") if caller is not None else ""
    function_name = str(caller.f_code.co_name or "") if caller is not None else ""
    try:
        identity = resolve_operator_identity(__file__)
        global_file = Path(caller_global_file).resolve()
        code_file = Path(caller_code_file).resolve()
    except (OSError, RuntimeError):
        identity = None
        global_file = Path()
        code_file = Path()
    binding = None
    if identity is not None and caller_global_file and caller_code_file and global_file == code_file:
        binding = _official_launch_binding(
            module_name=minter,
            function_name=function_name,
            caller_file=code_file,
            identity=identity,
        )
    if binding is None or identity is None:
        raise RuntimeError(
            "official launch mint refused: caller is not an exact admitted checkout binding "
            f"(module={minter or 'unknown'}, function={function_name or 'unknown'}, "
            f"file={caller_code_file or 'unknown'}); mint only from brick CLI / admitted probes"
        )
    admitted_file, admitted_module, _admitted_function = binding
    proof = OfficialLaunchProof(
        nonce=secrets.token_hex(16),
        minter_module=admitted_module,
        minter_file=admitted_file,
        minter_function=function_name,
        identity_mode=identity.mode,
        identity_root=str(identity.repo_root.resolve()),
        _mint_key=_OFFICIAL_LAUNCH_MINT_KEY,
    )
    _MINTED_OFFICIAL_LAUNCH_NONCES.add(proof.nonce)
    return _OFFICIAL_LAUNCH_TOKEN.set(proof)


def reset_official_launch_token(token: Token[object | None]) -> None:
    """Reset the process-local token and retire the just-closed proof nonce."""

    live = _OFFICIAL_LAUNCH_TOKEN.get()
    _OFFICIAL_LAUNCH_TOKEN.reset(token)
    if type(live) is OfficialLaunchProof:
        _MINTED_OFFICIAL_LAUNCH_NONCES.discard(live.nonce)


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
    nonce_minted = typed_proof and value.nonce in _MINTED_OFFICIAL_LAUNCH_NONCES
    binding_current = typed_proof and _official_launch_proof_binding_is_current(value)
    present = nonce_minted and binding_current
    forged_non_proof = value is not None and not typed_proof
    forged_unminted_proof = typed_proof and not nonce_minted
    forged_binding_mismatch = typed_proof and nonce_minted and not binding_current
    return {
        "kind": "official_launch_token_observation",
        "token_present": present,
        "forged_non_proof_observed": forged_non_proof,
        "forged_unminted_proof_observed": forged_unminted_proof,
        "forged_binding_mismatch_observed": forged_binding_mismatch,
        "observation_mode": "gate_lethal",
        "absence_action": "raise_runtime_error",
        "token_source": (
            f"{value.minter_module}.{value.minter_function}" if typed_proof else ""
        ),
        "token_source_file": value.minter_file if typed_proof else "",
        "token_identity_mode": value.identity_mode if typed_proof else "",
        "pure_dev_d3_building_id": PURE_DEV_D3_BUILDING_ID,
        "harden_ref": "official_launch_typed_proof_v1",
        "proof_limits": [
            "process-scoped contextvars.ContextVar observation only",
            "typed OfficialLaunchProof with module-minted nonce required for presence",
            "proof minter file/module/function must match this exact checkout identity",
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
        or live.get("forged_binding_mismatch_observed") is True
    ):
        raise RuntimeError(
            "official launch proof forged: live process token is not a minted OfficialLaunchProof "
            "(L3-3b/R7-D1)"
        )
    if live.get("token_present") is True:
        crosscheck_fields = (
            "token_present",
            "forged_non_proof_observed",
            "forged_unminted_proof_observed",
            "forged_binding_mismatch_observed",
            "token_source",
            "token_source_file",
            "token_identity_mode",
        )
        if isinstance(observation, Mapping) and any(
            observation.get(field) != live.get(field) for field in crosscheck_fields
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

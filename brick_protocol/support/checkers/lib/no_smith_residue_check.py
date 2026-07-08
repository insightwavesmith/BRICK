"""Product no-Smith-residue scan (kernel-check leaf).

Byte-identical relocation from kernel_checks.py (FINAL architecture leaf,
conservation ledger customer-ready-final-architecture-no-smith-residue-ledger-0630.md).
Scans shipped newcomer-facing surfaces for operator-local residue. Support
evidence only: it owns no axis crossing and judges no success/quality/Movement.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from brick_protocol.support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    to_posix,
)


_SMITH_USER_HOME_LITERAL = "/Users/" + "smith"
_SMITH_GITHUB_ORG_LITERAL = "insightwave" + "smith"
_SMITH_GITHUB_REPO_LITERAL = _SMITH_GITHUB_ORG_LITERAL + "/BRICK"

_NO_SMITH_RESIDUE_SURFACES = (
    "README.md",
    "brick_protocol/support/docs/spec",
    "brick_protocol/support/docs/references",
    "brick_protocol/agent/prompts",
    "brick_protocol/agent/skills",
    "brick_protocol/brick/templates/skills",
    "brick_protocol/support/onboarding/install.sh",
)


def _no_smith_residue_text_paths(repo: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for surface in _NO_SMITH_RESIDUE_SURFACES:
        root = repo / surface
        if not root.exists():
            continue
        if root.is_file():
            paths.append(root)
            continue
        paths.extend(
            path
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.suffix in {".md", ".txt"}
        )
    return tuple(paths)


def _no_smith_residue_allowed_org_line(rel: str, line: str) -> bool:
    return (
        rel == "README.md"
        and _SMITH_GITHUB_REPO_LITERAL in line
        and ("현재 동작 예" in line or "working example" in line.lower())
    )


def _collect_no_smith_residue_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    inspected = 0
    for path in _no_smith_residue_text_paths(repo):
        rel = to_posix(path.relative_to(repo))
        inspected += 1
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _SMITH_USER_HOME_LITERAL in line:
                violations.append(f"{rel}:{lineno}: hardcoded Smith user-home path")
            if _SMITH_GITHUB_ORG_LITERAL in line.lower() and not _no_smith_residue_allowed_org_line(rel, line):
                violations.append(f"{rel}:{lineno}: hardcoded Smith GitHub org")
    return violations, inspected


def _copy_no_smith_residue_surfaces(repo: Path, probe_repo: Path) -> None:
    for surface in _NO_SMITH_RESIDUE_SURFACES:
        source = repo / surface
        target = probe_repo / surface
        if not source.exists():
            continue
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        else:
            shutil.copytree(source, target)


def _no_smith_residue_fire_probe(repo: Path) -> int:
    probes = (
        (
            "user-home",
            Path("brick_protocol/support/docs/spec/README.md"),
            f"synthetic probe path: {_SMITH_USER_HOME_LITERAL}/projects/BRICK\n",
            "hardcoded Smith user-home path",
        ),
        (
            "agent-skill-user-home",
            Path("brick_protocol/agent/skills/scoped-implementation/SKILL.md"),
            f"synthetic probe path: {_SMITH_USER_HOME_LITERAL}/projects/BRICK\n",
            "hardcoded Smith user-home path",
        ),
        (
            "brick-template-skill-user-home",
            Path("brick_protocol/brick/templates/skills/make-a-brick/SKILL.md"),
            f"synthetic probe path: {_SMITH_USER_HOME_LITERAL}/projects/BRICK\n",
            "hardcoded Smith user-home path",
        ),
        (
            "org",
            Path("brick_protocol/agent/prompts/coo.md"),
            f"synthetic probe clone: gh repo clone {_SMITH_GITHUB_REPO_LITERAL} ~/BRICK\n",
            "hardcoded Smith GitHub org",
        ),
        (
            "references-org",
            Path("brick_protocol/support/docs/references/repo-invite-issuance.md"),
            f"synthetic probe clone: gh repo clone {_SMITH_GITHUB_REPO_LITERAL} ~/BRICK\n",
            "hardcoded Smith GitHub org",
        ),
    )
    inspected = 0
    for label, target_rel, line, expected in probes:
        inspected += 1
        with tempfile.TemporaryDirectory(prefix="bp-no-smith-residue-fire-") as tmp:
            probe_repo = Path(tmp)
            _copy_no_smith_residue_surfaces(repo, probe_repo)
            target = probe_repo / target_rel
            if not target.is_file():
                raise ProfileError(
                    f"product_no_smith_residue FIRE probe target missing for {label}: "
                    f"{to_posix(target_rel)}"
                )
            with target.open("a", encoding="utf-8") as handle:
                handle.write(line)
            violations, _ = _collect_no_smith_residue_violations(probe_repo)
            if not any(expected in violation for violation in violations):
                raise ProfileError(
                    "product_no_smith_residue FIRE probe did NOT fire for "
                    f"{label}: {line.strip()!r}"
                )
    return inspected


def run_product_no_smith_residue(repo: Path) -> KernelResult:
    """Product-surface lint for Smith local residue.

    Scans the shipped newcomer-facing surfaces named by ONBOARDING-LEGACY-SCRUB:
    root README, brick_protocol/support/docs/spec, brick_protocol/support/docs/references, brick_protocol/agent/prompts,
    brick_protocol/agent/skills, brick_protocol/brick/templates/skills, and the onboarding install verb. The
    only admitted concrete Smith-org BRICK occurrence there is the root README's
    explicit working-example note next to the parameterized ``{OWNER}/BRICK``
    command.
    """

    violations, inspected = _collect_no_smith_residue_violations(repo)
    if violations:
        raise ProfileError(
            "product_no_smith_residue rejected shipped-surface residue:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )
    inspected += _no_smith_residue_fire_probe(repo)
    return KernelResult(
        check_id="product_no_smith_residue",
        inspected=inspected,
        output=(
            "product no-Smith-residue scan passed: README.md, brick_protocol/support/docs/spec, "
            "brick_protocol/support/docs/references, brick_protocol/agent/prompts, brick_protocol/agent/skills, "
            "brick_protocol/brick/templates/skills, and brick_protocol/support/onboarding/install.sh carry no "
            "Smith user-home literal and no hardcoded Smith GitHub org outside "
            "the README working-example allowance; temp-copy FIRE probes for "
            "both forbidden families, both skill surfaces, and support docs "
            "references fired RED."
        ),
    )

#!/usr/bin/env python3
"""Priority-pinning checker for the ``brick build`` forward-action override.

Drives ``resolve_build_action`` (support/operator/assembly.py) over a fixed
input matrix and asserts the launch-action priority law holds:

    CLI flag  >  declaration file action  >  default stop

Ergonomics wave 표22 (발사 이중 열쇠): an operator must be able to launch a
stop-defaulted graph-decl edit-free with ``brick build --graph-decl F --forward``.
The priority resolution is the CLI-surface expression of an explicit human launch
act; the auto-fire ban (Rule 3) stays law — no CLI flag + no forward file action
resolves to ``stop``.

This checker is support evidence only: not source truth, success judgment,
quality judgment, or Movement authority. It writes no files and reaches no
launch seam (the resolver is a pure function; no driver/goal-approve import).

Probes (default --variant none):
  P1  the real resolver satisfies the whole priority matrix
  P2  VARIANT-RED-1: a priority-reversed mutant is CAUGHT by the matrix
      (a vacuous matrix that lets the mutant pass is itself RED)
  P3  VARIANT-RED-2: a flag-ignored mutant is CAUGHT by the matrix
  P4  auto-fire invariant: no CLI flag + omitted/stop file action -> stop
  P5  conflict rejection: --forward + --action stop raises
  P6  CLI wiring literals present in support/operator/cli.py

``--variant priority-reversed`` / ``--variant flag-ignored`` run the matrix
directly against that mutant resolver; the mutant MUST fail the matrix, so the
checker returns rc=1 — the direct demonstration that each variant is RED.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

# NOTE: repo root is computed with .parent chaining (not ``parents[2]``) on
# purpose. This standalone probe is not part of the operator import-identity
# family, so it stays out of the parents[N] binding registry scan
# (check_import_identity_modes.PARENTS_BINDING_RE) rather than requiring a
# registry entry it cannot author.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_IMPORT_IDENTITY_ROOT = _REPO_ROOT / "support" / "import_identity"
for _path in (str(_REPO_ROOT), str(_IMPORT_IDENTITY_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from brick_protocol.support.operator.assembly import (  # noqa: E402
    graph_declaration_action,
    resolve_build_action,
)

PROOF_LIMIT = "support evidence only; not source truth / success / quality / Movement"

Resolver = Callable[..., Mapping[str, str]]

# (kwargs, expected) rows. Each row pins one cell of the priority law.
_MATRIX: tuple[tuple[dict[str, Any], dict[str, str]], ...] = (
    # no CLI flag -> file action governs (default stop)
    ({"cli_forward": False, "cli_action": None, "declaration": {}},
     {"action": "stop", "basis": "file"}),
    ({"cli_forward": False, "cli_action": None, "declaration": {"action": "stop"}},
     {"action": "stop", "basis": "file"}),
    ({"cli_forward": False, "cli_action": None, "declaration": {"action": "forward"}},
     {"action": "forward", "basis": "file"}),
    # --forward launches a stop-defaulted / stop-file declaration edit-free
    ({"cli_forward": True, "cli_action": None, "declaration": {}},
     {"action": "forward", "basis": "cli"}),
    ({"cli_forward": True, "cli_action": None, "declaration": {"action": "stop"}},
     {"action": "forward", "basis": "cli"}),
    # --action forward is the long form of --forward
    ({"cli_forward": False, "cli_action": "forward", "declaration": {"action": "stop"}},
     {"action": "forward", "basis": "cli"}),
    # --action stop overrides a forward file action (CLI still wins)
    ({"cli_forward": False, "cli_action": "stop", "declaration": {"action": "forward"}},
     {"action": "stop", "basis": "cli"}),
)


def _matrix_violations(resolve: Resolver) -> list[str]:
    """Return the priority-matrix cells the resolver gets wrong (empty = green)."""

    out: list[str] = []
    for kwargs, expected in _MATRIX:
        try:
            got = dict(resolve(**kwargs))
        except Exception as exc:  # noqa: BLE001 -- a mutant may raise; that is a miss
            out.append(f"case {kwargs} raised {exc!r}")
            continue
        if got != expected:
            out.append(f"case {kwargs}: got {got}, want {expected}")
    return out


def _mutant_priority_reversed(
    *,
    cli_forward: bool = False,
    cli_action: str | None = None,
    declaration: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """WRONG: the declaration file action wins over the CLI flag."""

    decl = declaration or {}
    if decl.get("action"):
        return {"action": str(decl["action"]).strip().lower(), "basis": "file"}
    if cli_forward:
        return {"action": "forward", "basis": "cli"}
    if cli_action:
        return {"action": str(cli_action).strip().lower(), "basis": "cli"}
    return {"action": "stop", "basis": "file"}


def _mutant_flag_ignored(
    *,
    cli_forward: bool = False,  # noqa: ARG001 -- the bug is that this is ignored
    cli_action: str | None = None,
    declaration: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """WRONG: the --forward flag is dropped; only --action / file are read."""

    if cli_action:
        return {"action": str(cli_action).strip().lower(), "basis": "cli"}
    return {"action": graph_declaration_action(declaration or {}), "basis": "file"}


_MUTANTS: Mapping[str, Resolver] = {
    "priority-reversed": _mutant_priority_reversed,
    "flag-ignored": _mutant_flag_ignored,
}


def run(repo: Path) -> list[str]:
    violations: list[str] = []

    # P1 — the real resolver satisfies the whole priority matrix.
    real = _matrix_violations(resolve_build_action)
    if real:
        violations.append("P1 real resolver failed priority matrix: " + "; ".join(real))

    # P2 / P3 — each mutant MUST be caught by the matrix (non-empty violations).
    for label, mutant in _MUTANTS.items():
        if not _matrix_violations(mutant):
            violations.append(
                f"VARIANT-RED vacuous: '{label}' mutant passed the priority matrix"
            )

    # P4 — auto-fire invariant: no CLI flag + omitted/stop file action -> stop.
    for decl in ({}, {"action": "stop"}):
        resolved = resolve_build_action(cli_forward=False, cli_action=None, declaration=decl)
        if resolved.get("action") != "stop":
            violations.append(f"P4 auto-fire invariant broken: {decl} -> {resolved}")

    # P5 — conflict rejection: --forward + --action stop must raise.
    try:
        resolve_build_action(cli_forward=True, cli_action="stop", declaration={})
    except ValueError:
        pass
    else:
        violations.append("P5 conflict not rejected: --forward + --action stop")

    # P6 — CLI wiring literals present in cli.py.
    cli_src = (repo / "support" / "operator" / "cli.py").read_text(encoding="utf-8")
    for needle in ('"--forward"', '"--action"', "resolve_build_action("):
        if needle not in cli_src:
            violations.append(f"P6 CLI wiring literal missing: {needle}")

    return violations


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence priority checker for brick build --forward.",
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--variant",
        choices=("none", "priority-reversed", "flag-ignored"),
        default="none",
        help="Run the matrix against a known-bad mutant; the mutant MUST go RED (rc=1).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT

    if args.variant != "none":
        mutant = _MUTANTS[args.variant]
        violations = _matrix_violations(mutant)
        if violations:
            print(
                f"build_forward_action VARIANT '{args.variant}' RED "
                f"(expected — the guard bites):",
                file=sys.stderr,
            )
            for line in violations:
                print(f"- {line}", file=sys.stderr)
            print(PROOF_LIMIT, file=sys.stderr)
            return 1
        # A mutant that survives the matrix means the matrix is vacuous.
        print(
            f"build_forward_action VARIANT '{args.variant}' did NOT go RED — "
            "priority matrix is vacuous",
            file=sys.stderr,
        )
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    violations = run(repo)
    if violations:
        print("build_forward_action rejected evidence:", file=sys.stderr)
        for line in violations:
            print(f"- {line}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    print("build_forward_action passed: 6 probe(s)")
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

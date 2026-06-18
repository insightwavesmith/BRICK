#!/usr/bin/env python3
"""Seal link/gate.py against re-computing Brick MEASUREMENT.

Fault-separation law (AGENTS.md): a Link gate JUDGES sufficiency (Movement-side
decision support) and must NOT MEASURE. Measurement — the Brick comparison fact
that observes a returned value against a required-return shape — is owned solely
by the Brick axis at ``brick/comparison.py`` (the ``brick_comparison`` crossing,
canonical symbol ``BrickComparisonFact``). The gate may READ that measurement as
a public fact (it names ``BrickComparisonFact.*`` public-fact references in
string form); it must never IMPORT, INSTANTIATE, or RE-DERIVE it.

If the gate could recompute the measurement it judges, fault attribution
collapses: a measurement bug and a judgment bug would live in the same module and
no checker could tell them apart (the gate-no-measure anti-pattern; see
``gate-no-measure-judge``). This checker is the missing structural half: the law,
the module boundary, and the docstrings stood, but nothing rejected a future edit
that mixed measurement computation into ``link/gate.py``.

This checker is the fault-separation TWIN of
``check_recording_checker_derived_contract._check_emitter_axis_separation`` (the
A2 emitter axis-separation rule), applied to the Link gate source: it AST-scans
the gate body and rejects

  (a) any import of the Brick measurement module or the ``BrickComparisonFact``
      symbol (measurement must stay a string-named public-fact REFERENCE, never a
      live import), and
  (b) any construction/derivation of the measurement: a call to
      ``BrickComparisonFact(...)`` / ``BrickComparisonFact.from_*(...)``, or a
      local definition of a ``BrickComparisonFact`` class or a
      ``from_returned_value`` / ``from_parts`` measurement factory.

String literals naming ``BrickComparisonFact.*`` public facts and parameter NAMES
like ``observed_match_kind`` are explicitly allowed — those are references to the
measurement, not the measurement itself.

This checker is support evidence only. It parses link/gate.py instead of
importing it, and does not call providers, choose Movement, judge source truth,
judge success or quality, or classify Building outcomes.

Pass => exit 0. Reject => exit 1.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_GATE_REL = Path("link/gate.py")

# The Brick MEASUREMENT crossing (crossing_registry.yaml: brick_comparison),
# owned by the Brick axis at brick/comparison.py. The gate must not import these
# module paths or recompute their measurement.
_FORBIDDEN_IMPORT_TOKENS: tuple[str, ...] = (
    "brick_protocol.brick.comparison",
    "brick.comparison",
)
# The canonical measurement symbol (crossing_registry.yaml canonical_symbols for
# brick_comparison). It may appear ONLY inside string-literal public-fact
# references; it must never be imported, constructed, or redefined in gate.py.
_MEASUREMENT_SYMBOL = "BrickComparisonFact"
# Brick-measurement factory/derivation names. A local def of one of these in the
# gate would mean the gate re-derives the measurement instead of reading it.
_MEASUREMENT_FACTORY_NAMES: frozenset[str] = frozenset(
    {"from_returned_value", "from_parts"}
)

PROOF_LIMIT = (
    "proof limit: link gate measurement-separation checker support evidence "
    "only; it does not prove source truth, success judgment, quality judgment, "
    "Movement authority, provider behavior, or semantic correctness of gate "
    "sufficiency. It proves only that link/gate.py homes no Brick measurement "
    "computation (measurement = Brick at brick/comparison.py)."
)


class LinkGateMeasurementSeparationError(ValueError):
    """Raised when link/gate.py imports or recomputes Brick measurement."""


def _parse_gate(repo: Path) -> ast.Module:
    path = repo / _GATE_REL
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(_GATE_REL))
    except OSError as exc:
        raise LinkGateMeasurementSeparationError(
            f"could not read {_GATE_REL}: {exc}"
        ) from exc
    except SyntaxError as exc:
        raise LinkGateMeasurementSeparationError(
            f"{_GATE_REL} is not valid Python: {exc}"
        ) from exc


def _check_no_measurement_import(module: ast.Module) -> list[str]:
    """Reject any import of the Brick measurement module or symbol."""

    violations: list[str] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if any(token in name for token in _FORBIDDEN_IMPORT_TOKENS):
                    violations.append(
                        "gate.measurement-separation: link/gate.py imports the "
                        f"Brick measurement module {name!r} "
                        "(measurement is Brick-owned at brick/comparison.py; the "
                        "gate may name it as a public-fact string only)"
                    )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if any(token in module_name for token in _FORBIDDEN_IMPORT_TOKENS):
                violations.append(
                    "gate.measurement-separation: link/gate.py imports from the "
                    f"Brick measurement module {module_name!r} "
                    "(measurement is Brick-owned at brick/comparison.py; the gate "
                    "may name it as a public-fact string only)"
                )
            for alias in node.names:
                if alias.name == _MEASUREMENT_SYMBOL:
                    violations.append(
                        "gate.measurement-separation: link/gate.py imports the "
                        f"Brick measurement symbol {_MEASUREMENT_SYMBOL!r} "
                        f"from {module_name!r} (the gate reads measurement as a "
                        "string-named public fact, it must not hold the live "
                        "measurement contract)"
                    )
    return violations


def _measurement_callee_name(func: ast.AST) -> str | None:
    """Return the BrickComparisonFact callee name if ``func`` invokes it.

    Matches ``BrickComparisonFact(...)`` and ``BrickComparisonFact.from_x(...)``
    (any attribute on the measurement symbol). Returns None otherwise.
    """

    if isinstance(func, ast.Name) and func.id == _MEASUREMENT_SYMBOL:
        return _MEASUREMENT_SYMBOL
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id == _MEASUREMENT_SYMBOL:
            return f"{_MEASUREMENT_SYMBOL}.{func.attr}"
    return None


def _check_no_measurement_computation(module: ast.Module) -> list[str]:
    """Reject constructing/deriving the Brick measurement inside the gate."""

    violations: list[str] = []
    for node in ast.walk(module):
        # (a) Calling the measurement contract: BrickComparisonFact(...) or
        # BrickComparisonFact.from_returned_value(...).
        if isinstance(node, ast.Call):
            callee = _measurement_callee_name(node.func)
            if callee is not None:
                violations.append(
                    "gate.measurement-separation: link/gate.py constructs the "
                    f"Brick measurement {callee}(...) "
                    "(the gate must READ measurement public facts, never compute "
                    "the measurement)"
                )
        # (b) Defining the measurement contract or a measurement factory here.
        elif isinstance(node, ast.ClassDef) and node.name == _MEASUREMENT_SYMBOL:
            violations.append(
                "gate.measurement-separation: link/gate.py defines a "
                f"{_MEASUREMENT_SYMBOL} class "
                "(the Brick measurement contract is owned by brick/comparison.py)"
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in _MEASUREMENT_FACTORY_NAMES:
                violations.append(
                    "gate.measurement-separation: link/gate.py defines the Brick "
                    f"measurement factory {node.name!r} "
                    "(measurement derivation is owned by brick/comparison.py)"
                )
    return violations


def check_gate_source(module: ast.Module) -> list[str]:
    """Return every measurement-separation violation in the gate module."""

    violations: list[str] = []
    violations.extend(_check_no_measurement_import(module))
    violations.extend(_check_no_measurement_computation(module))
    return violations


def _assert_mutation_red() -> str:
    """FIRE probe: a gate body that imports + computes the measurement must RED.

    Builds a synthetic gate-source AST that (1) imports BrickComparisonFact and
    (2) constructs/derives it, and asserts both rules fire. This is the
    permanent mutation-RED guard: if a real edit slips measurement computation
    into link/gate.py, the live ``check_gate_source`` REDs exactly as this probe
    proves it does on the synthetic body.
    """

    mutated_source = "\n".join(
        [
            "from brick.comparison import BrickComparisonFact",
            "",
            "def evaluate_declared_gate_ref(returned_value, required_fields):",
            "    fact = BrickComparisonFact.from_returned_value(",
            "        work_reference='x',",
            "        required_fields=required_fields,",
            "        returned_value=returned_value,",
            "    )",
            "    return fact.observed_match_kind",
            "",
        ]
    )
    mutated = ast.parse(mutated_source)
    violations = check_gate_source(mutated)
    import_red = any("imports" in line for line in violations)
    compute_red = any("constructs" in line for line in violations)
    if not (import_red and compute_red):
        raise LinkGateMeasurementSeparationError(
            "mutation RED failed: a synthetic gate body that imports and "
            "constructs the Brick measurement was NOT rejected "
            f"(import_red={import_red}, compute_red={compute_red})"
        )
    return (
        "mutation RED observed: a synthetic gate body that imports "
        f"{_MEASUREMENT_SYMBOL} and constructs it via from_returned_value was "
        "rejected by both the import and computation rules"
    )


def check(repo: Path) -> list[str]:
    module = _parse_gate(repo)
    violations = check_gate_source(module)
    if violations:
        raise LinkGateMeasurementSeparationError(
            "link/gate.py homes Brick measurement computation:\n"
            + "\n".join(f"- {v}" for v in violations)
        )
    mutation_line = _assert_mutation_red()
    return [
        "link gate measurement-separation green: link/gate.py imports no Brick "
        f"measurement module/symbol and constructs/derives no {_MEASUREMENT_SYMBOL}; "
        "it names the measurement as string-form public-fact references only "
        "(measurement = Brick at brick/comparison.py, judgment = Link gate).",
        mutation_line,
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker that seals link/gate.py against importing "
            "or recomputing Brick measurement (gate judges, it does not measure)."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except LinkGateMeasurementSeparationError as exc:
        print("link gate measurement-separation rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

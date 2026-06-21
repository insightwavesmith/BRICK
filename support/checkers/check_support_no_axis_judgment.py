#!/usr/bin/env python3
"""Judgment-guard: support must not re-make a relocated axis VERDICT.

E2 / S10 (STRUCTURE-DESIGN.md §7 guard 2 + §8 S10 row). support is TRANSPORT +
DERIVE only; it gathers FACTS and threads them, but the requirement / completeness
/ validity VERDICT on an axis's fields is the AXIS's to make (design erosion path
①: "judge-in-support"). §4 relocated each judgment family (J1..J10) to its owning
axis module; this guard makes the relocation PERMANENT by REDding if a support
module re-inlines a relocated verdict.

WHAT IT GUARDS
--------------
judgment_home.yaml maps each relocated judgment family to (a) its owning axis
module + symbol, (b) the axis VERDICT FIELD it decides, (c) the family's verdict
VALUE literals, and (d) the support modules allowed to CONSUME the verdict (gather
the facts + call the axis). The guard AST-scans every module under support/ and
REDs when a module OUTSIDE a family's ``allowed_consumers`` contains the relocated
VERDICT SHAPE: a CONDITIONAL assignment / keyword binding the family's verdict
FIELD to one of its verdict VALUE literals. "Conditional" means either an
``ast.IfExp`` ternary value (``field = "missing" if ... else ...``) or an
assignment that lexically sits inside an ``if`` / ``elif`` branch body (the
frontier ladder shape ``frontier_kind = "complete"`` under an ``elif``). That
conditional-literal-on-an-axis-field shape is exactly the downgrade / ladder §4
moved to the axis.

WHAT IS NOT A JUDGMENT (never RED)
----------------------------------
- An UNCONDITIONAL construction default — e.g. ``from_parts(...,
  observed_match_kind="unknown")`` — is a neutral fact default, not gated on any
  axis condition, and "unknown" is not a registered verdict value: not flagged.
- Pure TRANSPORT — re-emitting an already-decided ``frontier_kind`` *variable*
  read from an observation record (reporter / driver / building_map_emit) threads a
  value; the guard fires only on a CONDITIONAL assignment to a registered verdict
  VALUE LITERAL, never on a variable.
- A single field-by-name READ (``record.get("frontier_kind")``) is an ordinary
  access, not a verdict.

GUARD-FIRST
-----------
Every registered family is already relocated on the CURRENT tree (J6->Link,
J10->Brick, J3->Agent generic resolver, J5->Brick), so support contains NONE of
these verdict shapes today -> GREEN now, RED on a regression (re-inlining a
relocated verdict into support).

Mutation-RED: re-add ``observed_match_kind = "missing" if missing else ...`` to a
support module (the J10 downgrade), or an ``elif ...: frontier_kind = "complete"``
ladder branch to a support module other than frontier_observation (the J6 ladder),
or move the J5 write-need ``raise`` back into run.py -> guard RED.

Support evidence only: this checker decides no Movement and judges no source
truth, success, or quality. It is an independent AST oracle; it imports no axis
module.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


REGISTRY_REL = "support/checkers/judgment_home.yaml"
SUPPORT_DIR = "support"
REGISTRY_SCHEMA = "judgment-home/v1"


def _load_registry(repo: Path) -> list[dict]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ValueError("support no-axis-judgment guard requires PyYAML") from exc
    path = repo / REGISTRY_REL
    if not path.is_file():
        raise ValueError(f"{REGISTRY_REL} must exist")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{REGISTRY_REL} must be a mapping")
    if doc.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"{REGISTRY_REL} schema must be {REGISTRY_SCHEMA!r}")
    rows = doc.get("judgment_families")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{REGISTRY_REL} judgment_families must be a non-empty list")
    registry: list[dict] = []
    seen_families: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{REGISTRY_REL} judgment_families[{index}] must be a mapping")
        family = row.get("family")
        axis_module = row.get("axis_module")
        verdict_field = row.get("verdict_field")
        verdict_values = row.get("verdict_values")
        allowed_consumers = row.get("allowed_consumers", [])
        if not isinstance(family, str) or not family:
            raise ValueError(f"{REGISTRY_REL} family[{index}].family must be non-empty text")
        if family in seen_families:
            raise ValueError(f"{REGISTRY_REL} duplicate family: {family}")
        seen_families.add(family)
        if not isinstance(axis_module, str) or not axis_module:
            raise ValueError(f"{REGISTRY_REL} {family}.axis_module must be non-empty text")
        if axis_module.startswith(SUPPORT_DIR + "/"):
            raise ValueError(
                f"{REGISTRY_REL} {family}.axis_module must be an AXIS module (not under "
                f"support/); a relocated verdict's home is its owning axis"
            )
        if not isinstance(verdict_field, str) or not verdict_field:
            raise ValueError(f"{REGISTRY_REL} {family}.verdict_field must be non-empty text")
        if not isinstance(verdict_values, list) or not verdict_values:
            raise ValueError(
                f"{REGISTRY_REL} {family}.verdict_values must be a non-empty list of literals"
            )
        value_set: set[str] = set()
        for value in verdict_values:
            if not isinstance(value, str) or not value:
                raise ValueError(f"{REGISTRY_REL} {family}.verdict_values entries must be non-empty text")
            value_set.add(value)
        if not isinstance(allowed_consumers, list):
            raise ValueError(f"{REGISTRY_REL} {family}.allowed_consumers must be a list")
        consumers: set[str] = set()
        for consumer in allowed_consumers:
            if not isinstance(consumer, str) or not consumer:
                raise ValueError(f"{REGISTRY_REL} {family}.allowed_consumers entries must be non-empty text")
            if not consumer.startswith(SUPPORT_DIR + "/"):
                raise ValueError(
                    f"{REGISTRY_REL} {family}.allowed_consumers must be support/ modules: {consumer}"
                )
            consumers.add(consumer)
        registry.append(
            {
                "family": family,
                "axis_module": axis_module,
                "verdict_field": verdict_field,
                "verdict_values": frozenset(value_set),
                "allowed_consumers": frozenset(consumers),
            }
        )
    return registry


def _string_constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _conditional_verdict_value(value: ast.AST, verdict_values: frozenset[str]) -> str | None:
    """Return the registered verdict-value literal IFF ``value`` is a CONDITIONAL
    bind of one (an ``ast.IfExp`` ternary whose body or orelse is such a literal).

    An unconditional plain string constant returns None here — branch-context
    detection (assignment inside an ``if``/``elif`` body) is handled by the caller's
    lexical scan, so this covers only the ternary form.
    """

    if isinstance(value, ast.IfExp):
        for branch in (value.body, value.orelse):
            text = _string_constant(branch)
            if text is not None and text in verdict_values:
                return text
    return None


def _assignment_targets_field(stmt: ast.stmt, verdict_field: str) -> ast.AST | None:
    """If ``stmt`` assigns/keyword-binds ``verdict_field``, return its value node."""

    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            if isinstance(target, ast.Name) and target.id == verdict_field:
                return stmt.value
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        if stmt.target.id == verdict_field and stmt.value is not None:
            return stmt.value
    return None


def _branch_value_literals(body: list[ast.stmt], verdict_field: str) -> list[ast.AST]:
    """Top-level value nodes of ``verdict_field`` assignments directly in ``body``."""

    values: list[ast.AST] = []
    for stmt in body:
        value = _assignment_targets_field(stmt, verdict_field)
        if value is not None:
            values.append(value)
    return values


def _iter_support_modules(repo: Path) -> list[tuple[str, Path]]:
    support_root = repo / SUPPORT_DIR
    if not support_root.is_dir():
        raise ValueError(f"{SUPPORT_DIR}/ must exist")
    modules: list[tuple[str, Path]] = []
    for path in sorted(support_root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        modules.append((path.relative_to(repo).as_posix(), path))
    return modules


def find_violations(repo: Path) -> tuple[list[str], int]:
    registry = _load_registry(repo)
    violations: list[str] = []
    scanned = 0
    for rel, path in _iter_support_modules(repo):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, ValueError) as exc:
            violations.append(f"{rel}: could not parse for axis-judgment scan: {exc}")
            continue
        scanned += 1

        # The guard is the checkers' own AST oracle source; it (and this module)
        # legitimately NAME the verdict fields/values to detect them. Never scan a
        # checker for the verdict shape — only operator/connection/etc. support
        # modules carry the relocated logic.
        if rel.startswith("support/checkers/"):
            continue

        for row in registry:
            if rel in row["allowed_consumers"]:
                continue
            field = row["verdict_field"]
            values = row["verdict_values"]

            # (a) ternary form: ``field = "missing" if ... else ...`` anywhere.
            for node in ast.walk(tree):
                value = _assignment_targets_field(node, field) if isinstance(node, ast.stmt) else None
                if value is None:
                    continue
                literal = _conditional_verdict_value(value, values)
                if literal is not None:
                    violations.append(
                        f"{rel}: conditionally assigns axis verdict field {field!r} to the "
                        f"relocated verdict value {literal!r} (ternary); family {row['family']!r}'s "
                        f"verdict lives on the {row['axis_module']} axis "
                        "(judgment-guard: gather the facts in support, read the axis verdict)"
                    )

            # (b) ladder form: a ``field = <verdict literal>`` assignment that sits
            #     directly inside an ``if`` / ``elif`` branch body.
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue
                for branch_body in (node.body, node.orelse):
                    for value in _branch_value_literals(branch_body, field):
                        text = _string_constant(value)
                        if text is not None and text in values:
                            violations.append(
                                f"{rel}: assigns axis verdict field {field!r} to the relocated "
                                f"verdict value {text!r} inside an if/elif branch (ladder); family "
                                f"{row['family']!r}'s verdict lives on the {row['axis_module']} axis "
                                "(judgment-guard: gather the facts in support, read the axis verdict)"
                            )

    return sorted(set(violations)), scanned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence judgment-guard: a relocated axis VERDICT (a "
            "conditional assignment of a registered verdict field to a registered "
            "verdict value literal) must not live in a support module outside the "
            "family's declared consumer set. Does not prove source truth, success, "
            "quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    try:
        violations, scanned = find_violations(repo)
    except (OSError, ValueError) as exc:
        print(f"support no-axis-judgment rejected: {exc}")
        return 1

    if violations:
        print("support no-axis-judgment rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only that no support module outside a "
            "judgment family's declared consumer set re-makes the relocated axis "
            "verdict; it does not prove source truth, success, quality, or Movement "
            "authority."
        )
        return 1

    print(
        "support no-axis-judgment passed: "
        f"{scanned} support module(s) scanned; no relocated axis verdict is "
        "re-made in support outside its declared consumer set."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""General invariant: axis YAML declared fields/enums == the python surface.

For each Brick/Agent/Link contract projection YAML:
  - the declared public field set (allowed_public_fields / public_fact.fields /
    fields) must equal the fields of the python @dataclass in the paired module;
  - each declared enum literal set must equal its python constant (excluding a
    documented empty-allowed meta-token such as ``blank``).

This catches the contract-vs-code drift class (a YAML promising a field/value the
code does not have, or the code having one the YAML omits) as ONE general check
instead of a per-contract fixture. It is ast-based: it imports NO axis module, so
it is an independent oracle, not a re-export of the code it inspects.

Support evidence only: proves field/enum-name parity, not source truth, success,
quality, or Movement authority.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


AXES = ("brick", "agent", "link")

# Documented meta-tokens that mean "empty string is allowed", NOT a literal enum
# value. comparison.yaml lists ``blank`` to document that observed_match_kind may
# be empty; comparison.py allows the empty string and keeps only the 4 real kinds.
ENUM_META_TOKENS = {"blank", "empty"}

# Enum parity pairs are declared explicitly (deterministic — no fuzzy matching):
# (yaml relpath, yaml literal-list key, item prefix to strip, py relpath, py const)
ENUM_PAIRS = [
    ("brick_protocol/brick/comparison.yaml", "allowed_observed_match_kind", "",
     "brick_protocol/brick/comparison.py", "_OBSERVED_MATCH_KINDS"),
    # NOTE: brick_protocol/link/movement.yaml movement_literals is intentionally NOT listed here.
    # movement.py MOVEMENT_LITERALS is computed from ADMITTED_MOVEMENT_* dicts
    # (subscript expressions, not string literals this ast oracle can read), and
    # the forward/reroute set is already pinned by check_axis_contract_projection
    # (ENGLISH_MOVEMENT_LITERALS) + the core profile yaml_literal_set rule.
    ("brick_protocol/link/gate.yaml", "stage_literals", "",
     "brick_protocol/link/gate.py", "GATE_STAGE_LITERALS"),
    ("brick_protocol/link/gate.yaml", "sufficiency_literals", "",
     "brick_protocol/link/gate.py", "GATE_SUFFICIENCY_LITERALS"),
    ("brick_protocol/link/carry.yaml", "source_owner_axis_literals", "",
     "brick_protocol/link/carry.py", "SOURCE_OWNER_AXIS_LITERALS"),
]

# Field-list keys a contract YAML may use to declare its public fields.
_FIELD_LIST_KEYS = ("allowed_public_fields", "fields")

# Constraint parity: a field whose python __post_init__ runs it through
# _brick_boundary_ref (value must start brick:/brick-/building-boundary:) must be
# declared in the YAML field_rules with this token, and vice versa. Closes the P0
# drift where the YAML said only ``required_text_ref`` for a field the code in fact
# constrains to a Brick boundary.
BRICK_BOUNDARY_RULE = "required_brick_boundary_ref"
BOUNDARY_CONSTRAINT_MODULES = (
    ("brick_protocol/link/transfer.yaml", "brick_protocol/link/transfer.py"),
    ("brick_protocol/link/carry.yaml", "brick_protocol/link/carry.py"),
)


def _py_dataclasses(pyfile: Path) -> dict[str, list[str]]:
    tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and any(
            (isinstance(d, ast.Name) and d.id == "dataclass")
            or (isinstance(d, ast.Call) and getattr(d.func, "id", "") == "dataclass")
            for d in node.decorator_list
        ):
            out[node.name] = [
                s.target.id
                for s in node.body
                if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)
            ]
    return out


def _py_str_sequence(pyfile: Path, name: str) -> list[str] | None:
    tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    for node in tree.body:
        targets: list[str] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Tuple, ast.List)):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, (ast.Tuple, ast.List))
        ):
            targets = [node.target.id]
            value = node.value
        if value is not None and name in targets:
            return [
                e.value
                for e in value.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            ]
    return None


def _yaml_list_under(lines: list[str], key: str) -> list[str]:
    out: list[str] = []
    block_indent: int | None = None
    for raw in lines:
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if block_indent is None:
            if stripped == f"{key}:":
                block_indent = indent
            continue
        if stripped.startswith("-") and indent > block_indent:
            out.append(stripped[1:].strip())
        elif indent <= block_indent:
            break
    return out


def _yaml_scalar(lines: list[str], key: str) -> str | None:
    for raw in lines:
        match = re.match(rf"\s*{re.escape(key)}:\s*(\S+)\s*$", raw.split("#", 1)[0])
        if match:
            return match.group(1)
    return None


def _field_parity_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    inspected = 0
    for axis in AXES:
        for yaml_path in sorted((repo / axis).glob("*.yaml")):
            lines = yaml_path.read_text(encoding="utf-8").splitlines()
            declared: list[str] = []
            for key in _FIELD_LIST_KEYS:
                declared = _yaml_list_under(lines, key)
                if declared:
                    break
            if not declared:
                continue  # presence-schema contracts (e.g. return_fact) — covered elsewhere
            py_path = yaml_path.with_suffix(".py")
            rel = yaml_path.relative_to(repo)
            if not py_path.is_file():
                violations.append(f"{rel}: declares fields but no paired module {py_path.name}")
                continue
            classes = _py_dataclasses(py_path)
            if not classes:
                violations.append(f"{rel}: paired {py_path.name} has no @dataclass to compare")
                continue
            if len(classes) == 1:
                py_fields = next(iter(classes.values()))
            else:
                wanted = _yaml_scalar(lines, "contract") or _yaml_scalar(lines, "name")
                if wanted not in classes:
                    violations.append(
                        f"{rel}: cannot resolve which @dataclass to compare "
                        f"(classes={sorted(classes)}, declared={wanted!r})"
                    )
                    continue
                py_fields = classes[wanted]
            inspected += 1
            missing = [f for f in py_fields if f not in declared]
            extra = [f for f in declared if f not in py_fields]
            if missing:
                violations.append(
                    f"{rel}: YAML field list missing python field(s): {', '.join(missing)}"
                )
            if extra:
                violations.append(
                    f"{rel}: YAML field list has field(s) absent from python @dataclass: "
                    f"{', '.join(extra)}"
                )
    return violations, inspected


def _enum_parity_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    inspected = 0
    for yaml_rel, yaml_key, prefix, py_rel, py_const in ENUM_PAIRS:
        yaml_path = repo / yaml_rel
        py_path = repo / py_rel
        if not yaml_path.is_file() or not py_path.is_file():
            violations.append(f"{yaml_rel} / {py_rel}: enum-pair target missing")
            continue
        raw_items = _yaml_list_under(yaml_path.read_text(encoding="utf-8").splitlines(), yaml_key)
        items: list[str] = []
        for item in raw_items:
            if prefix and item.startswith(prefix):
                item = item[len(prefix):].strip()
            items.append(item)
        declared = {i for i in items if i not in ENUM_META_TOKENS}
        py_values = _py_str_sequence(py_path, py_const)
        if py_values is None:
            violations.append(f"{py_rel}: enum constant {py_const} not found")
            continue
        inspected += 1
        py_set = set(py_values)
        missing = sorted(py_set - declared)
        extra = sorted(declared - py_set)
        if missing:
            violations.append(
                f"{yaml_rel}:{yaml_key} missing python {py_const} value(s): {', '.join(missing)}"
            )
        if extra:
            violations.append(
                f"{yaml_rel}:{yaml_key} has value(s) absent from python {py_const}: "
                f"{', '.join(extra)}"
            )
    return violations, inspected


def _yaml_mapping_under(lines: list[str], key: str) -> dict[str, str]:
    out: dict[str, str] = {}
    block_indent: int | None = None
    for raw in lines:
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if block_indent is None:
            if stripped == f"{key}:":
                block_indent = indent
            continue
        if indent > block_indent and ":" in stripped and not stripped.startswith("-"):
            field_key, _, value = stripped.partition(":")
            out[field_key.strip()] = value.strip()
        elif indent <= block_indent:
            break
    return out


def _py_brick_boundary_fields(pyfile: Path) -> set[str]:
    fields: set[str] = set()
    tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_brick_boundary_ref"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            fields.add(node.args[0].value)
    return fields


def _constraint_parity_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    inspected = 0
    for yaml_rel, py_rel in BOUNDARY_CONSTRAINT_MODULES:
        yaml_path = repo / yaml_rel
        py_path = repo / py_rel
        if not yaml_path.is_file() or not py_path.is_file():
            violations.append(f"{yaml_rel} / {py_rel}: constraint-pair target missing")
            continue
        rules = _yaml_mapping_under(
            yaml_path.read_text(encoding="utf-8").splitlines(), "field_rules"
        )
        yaml_boundary = {f for f, rule in rules.items() if rule == BRICK_BOUNDARY_RULE}
        code_boundary = _py_brick_boundary_fields(py_path)
        inspected += 1
        undeclared = sorted(code_boundary - yaml_boundary)
        unenforced = sorted(yaml_boundary - code_boundary)
        if undeclared:
            violations.append(
                f"{yaml_rel}: code enforces a Brick-boundary prefix on field(s) "
                f"{', '.join(undeclared)} but field_rules does not declare them "
                f"'{BRICK_BOUNDARY_RULE}'"
            )
        if unenforced:
            violations.append(
                f"{yaml_rel}: field_rules declares '{BRICK_BOUNDARY_RULE}' for field(s) "
                f"{', '.join(unenforced)} but {py_rel} does not enforce it"
            )
    return violations, inspected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: axis YAML declared fields/enums must equal "
            "the python dataclass fields / enum constants. Does not prove source "
            "truth, success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    field_v, field_n = _field_parity_violations(repo)
    enum_v, enum_n = _enum_parity_violations(repo)
    constraint_v, constraint_n = _constraint_parity_violations(repo)
    violations = field_v + enum_v + constraint_v
    if violations:
        print("axis field/enum parity rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only YAML/python field & enum name "
            "parity; it does not prove source truth, success, quality, or Movement "
            "authority."
        )
        return 1

    print(
        "axis field/enum parity passed: "
        f"{field_n} contract field set(s), {enum_n} enum literal set(s), and "
        f"{constraint_n} boundary-ref constraint set(s) match their python surface."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

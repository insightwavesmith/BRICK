#!/usr/bin/env python3
"""Mirror-guard + scatter-guard: a registered AXIS field-set is enumerated in exactly ONE place.

E2 / S0 (STRUCTURE-DESIGN.md §7 item 1 + item 3, §8 S0 row). This generalizes the
casting-only drift-meta guard (check_agent_resource_resolution._casting_field_registry_violations)
into a registry-driven, all-of-support AST scan.

WHAT IT GUARDS
--------------
support is TRANSPORT + DERIVE only; it must NOT ②MIRROR an axis field-set (the design's
erosion path ②). A *mirror* is a hardcoded copy of an axis field-set's member-set — a
``frozenset`` / ``set`` / ``tuple`` / ``list`` literal of strings, or a whole
``@dataclass`` whose complete named-field set equals the registered member-set — living
anywhere other than the ONE registered single source. The guard AST-scans every module
under support/ and REDs if it finds such an enumeration outside the registered
``(defining_module, source_symbol)``.

SCATTER-GUARD (folded in, §7 item 3): each registered field-set has exactly ONE
``defining_module``. A second enumeration anywhere is the same RED — there is never a
legitimate second definition of a registered set.

WHAT IS NOT A MIRROR (never RED)
--------------------------------
- A *single-field-by-name* read — ``agent_object.get("preferred_adapter_ref")``,
  ``obj.preferred_model_ref``, an annotated dataclass scalar interleaved among other
  fields — is an ordinary field access, NOT a field-SET enumeration. The guard fires
  ONLY on a literal collection (or a whole dataclass) whose member-set EQUALS a
  registered member-set; a partial overlap or a lone field name is ignored.
- WHITELIST — the single explicit-adapter invariant (design §3 / §7.1): the
  ``selected_adapter_ref`` / ``preferred_adapter_ref`` fail-close presence checks read
  the adapter field BY NAME on purpose ("adapter never defaults"). That is an invariant,
  not a mirror. Because a single field name can never equal a (≥2-member) registered
  member-set, those by-name reads are structurally outside this guard already; this
  docstring records the intent so the invariant is not mistaken for a gap.

GUARD-FIRST
-----------
field_set_registry.yaml lists only field-sets that are single-source on the CURRENT tree,
so this guard is GREEN now and turns RED on a regression (a re-added duplicate literal /
dataclass mirror). Field-sets still mirrored in many places are registered later as
S1-S12 collapse them.

Mutation-RED: add a second ``frozenset({"preferred_adapter_ref", "preferred_model_ref"})``
(or a ``@dataclass`` with exactly those two fields) in any support module -> guard RED.

Support evidence only: this checker decides no Movement and judges no source truth,
success, or quality. It is an independent AST oracle; it imports no axis module.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


REGISTRY_REL = "support/checkers/field_set_registry.yaml"
SUPPORT_DIR = "support"
REGISTRY_SCHEMA = "field-set-registry/v1"


def _load_registry(repo: Path) -> list[dict]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ValueError("axis field-set single-source guard requires PyYAML") from exc
    path = repo / REGISTRY_REL
    if not path.is_file():
        raise ValueError(f"{REGISTRY_REL} must exist")
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{REGISTRY_REL} must be a mapping")
    if doc.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"{REGISTRY_REL} schema must be {REGISTRY_SCHEMA!r}")
    rows = doc.get("field_sets")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{REGISTRY_REL} field_sets must be a non-empty list")
    registry: list[dict] = []
    seen_names: set[str] = set()
    seen_member_sets: dict[frozenset[str], str] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{REGISTRY_REL} field_sets[{index}] must be a mapping")
        name = row.get("name")
        defining_module = row.get("defining_module")
        source_symbol = row.get("source_symbol")
        members = row.get("members")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{REGISTRY_REL} field_sets[{index}].name must be non-empty text")
        if name in seen_names:
            raise ValueError(f"{REGISTRY_REL} duplicate field_sets name: {name}")
        seen_names.add(name)
        if not isinstance(defining_module, str) or not defining_module:
            raise ValueError(f"{REGISTRY_REL} {name}.defining_module must be non-empty text")
        if not isinstance(source_symbol, str) or not source_symbol:
            raise ValueError(f"{REGISTRY_REL} {name}.source_symbol must be non-empty text")
        if not isinstance(members, list) or len(members) < 2:
            raise ValueError(
                f"{REGISTRY_REL} {name}.members must be a list of at least two field "
                "names (a single field name is a by-name read, not a field-set)"
            )
        member_set: set[str] = set()
        for member in members:
            if not isinstance(member, str) or not member:
                raise ValueError(f"{REGISTRY_REL} {name}.members entries must be non-empty text")
            if member in member_set:
                raise ValueError(f"{REGISTRY_REL} {name}.members has a duplicate: {member}")
            member_set.add(member)
        frozen = frozenset(member_set)
        prior = seen_member_sets.get(frozen)
        if prior is not None:
            raise ValueError(
                f"{REGISTRY_REL} field-sets {prior!r} and {name!r} declare the same "
                "member-set; a member-set has exactly one registered home"
            )
        seen_member_sets[frozen] = name
        registry.append(
            {
                "name": name,
                "defining_module": defining_module,
                "source_symbol": source_symbol,
                "members": frozen,
            }
        )
    return registry


def _string_constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _all_string_members(elements: list[ast.expr]) -> frozenset[str] | None:
    """The set of string literals in ``elements`` iff EVERY element is a string literal.

    Returns None when the collection is empty or holds any non-string-literal element
    (e.g. a tuple of ``CastingField(...)`` descriptor calls is NOT a string set, so the
    casting single source is never self-flagged), or when two literals collide (a real
    set/tuple of strings with a duplicate is malformed and not a clean member-set).
    """

    names: list[str] = []
    for element in elements:
        text = _string_constant(element)
        if text is None:
            return None
        names.append(text)
    if not names:
        return None
    if len(set(names)) != len(names):
        return None
    return frozenset(names)


def _literal_member_set(node: ast.AST) -> frozenset[str] | None:
    """Member-set of a string-collection literal node, else None.

    Covers ``{...}`` / ``[...]`` / ``(...)`` of string constants and the
    ``frozenset({...})`` / ``set([...])`` / ``frozenset([...])`` call wrappers.
    """

    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        return _all_string_members(list(node.elts))
    if isinstance(node, ast.Call):
        func = node.func
        builder = getattr(func, "id", None) or getattr(func, "attr", None)
        if builder in {"frozenset", "set"} and len(node.args) == 1 and not node.keywords:
            inner = node.args[0]
            if isinstance(inner, (ast.Set, ast.List, ast.Tuple)):
                return _all_string_members(list(inner.elts))
    return None


def _dataclass_field_names(node: ast.ClassDef) -> frozenset[str] | None:
    """Complete named-field set of an ``@dataclass`` class, else None.

    Only annotated assignments (``name: type`` / ``name: type = default``) at class
    body level count as fields. ClassVar-style or method members are ignored. Returns
    None when the class is not decorated as a dataclass or declares no fields.
    """

    is_dataclass = False
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        deco_name = getattr(target, "id", None) or getattr(target, "attr", None)
        if deco_name == "dataclass":
            is_dataclass = True
            break
    if not is_dataclass:
        return None
    names: list[str] = []
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names.append(stmt.target.id)
    if not names:
        return None
    return frozenset(names)


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


def _assigned_symbol(stmt: ast.stmt) -> str | None:
    """The single top-level name a literal is bound to (for source-symbol whitelist)."""

    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
        target = stmt.targets[0]
        if isinstance(target, ast.Name):
            return target.id
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return stmt.target.id
    return None


def find_violations(repo: Path) -> tuple[list[str], int]:
    registry = _load_registry(repo)
    by_members: dict[frozenset[str], dict] = {row["members"]: row for row in registry}

    violations: list[str] = []
    scanned = 0
    for rel, path in _iter_support_modules(repo):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except (SyntaxError, ValueError) as exc:
            violations.append(f"{rel}: could not parse for field-set scan: {exc}")
            continue
        scanned += 1

        # Map each literal-collection node that is the DIRECT right-hand side of a
        # module/class-level binding to its bound symbol, so the registered single
        # source can be whitelisted by (module, symbol). A literal nested inside an
        # expression carries no bound symbol (symbol is None) and is judged purely by
        # its member-set.
        symbol_by_node: dict[int, str] = {}
        for stmt in ast.walk(tree):
            symbol = _assigned_symbol(stmt) if isinstance(stmt, ast.stmt) else None
            if symbol is None:
                continue
            value = getattr(stmt, "value", None)
            if value is not None:
                symbol_by_node[id(value)] = symbol

        # 1) literal string-collections (frozenset/set/tuple/list, incl. frozenset(...) /
        #    set(...) wrappers) anywhere in the module.
        for sub in ast.walk(tree):
            member_set = _literal_member_set(sub)
            if member_set is None:
                continue
            row = by_members.get(member_set)
            if row is None:
                continue
            symbol = symbol_by_node.get(id(sub))
            if rel == row["defining_module"] and symbol == row["source_symbol"]:
                continue
            violations.append(
                f"{rel}: enumerates registered axis field-set "
                f"{row['name']!r} ({sorted(member_set)}) as a literal collection; "
                f"its single source is {row['source_symbol']} in {row['defining_module']} "
                "(mirror/scatter guard: derive from the source, do not re-enumerate)"
            )

        # 2) whole-@dataclass field-set mirrors.
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            field_names = _dataclass_field_names(node)
            if field_names is None:
                continue
            row = by_members.get(field_names)
            if row is None:
                continue
            if rel == row["defining_module"] and node.name == row["source_symbol"]:
                continue
            violations.append(
                f"{rel}: @dataclass {node.name!r} field-set equals registered axis "
                f"field-set {row['name']!r} ({sorted(field_names)}); its single source is "
                f"{row['source_symbol']} in {row['defining_module']} (mirror guard: carry an "
                "opaque casting/ref bag, do not name the field-set as dataclass fields)"
            )

    return sorted(set(violations)), scanned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence mirror-guard + scatter-guard: each registered AXIS "
            "field-set is enumerated in exactly ONE single source; any second "
            "enumeration (literal collection or whole @dataclass) anywhere under "
            "support/ is rejected. Does not prove source truth, success, quality, "
            "or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    try:
        violations, scanned = find_violations(repo)
    except (OSError, ValueError) as exc:
        print(f"axis field-set single source rejected: {exc}")
        return 1

    if violations:
        print("axis field-set single source rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only that each registered axis "
            "field-set is enumerated in exactly one single source; it does not "
            "prove source truth, success, quality, or Movement authority."
        )
        return 1

    print(
        "axis field-set single source passed: "
        f"{scanned} support module(s) scanned; every registered axis field-set "
        "has exactly one enumeration (its single source)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

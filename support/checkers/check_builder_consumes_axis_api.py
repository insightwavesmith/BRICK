#!/usr/bin/env python3
"""Builder-bypass-guard: the builder CONSUMES the 3-axis APIs, re-encodes nothing.

E2 / S8 (STRUCTURE-DESIGN.md §7 guard 4 + §6 builder-ingests). The HEART builder
(``support/operator/assembly.py`` + the onboard/driver/cli entrypoints) used to be a
PARALLEL re-encoding of all three axes: a per-node ``adapter``/``model`` scalar set that
drifted from ``CASTING_FIELDS``, and ``Gate``/``Concern``/``Adoption`` enums whose
``.value``s re-stated the Link/Agent axis vocab as literals. S6/S7 collapsed the casting
scalars into the opaque ``casting`` bag (keyed by ``CASTING_FIELDS``); S8 derives the
three enums from the axis vocab. This guard LOCKS both so the builder can never again
hand-wire an axis field-set instead of consuming the API.

WHAT IT GUARDS
--------------
AST-scans ``assembly.py``, the relocated axis homes ``brick/spec.py`` /
``agent/spec.py`` (where the per-node carriers are now DEFINED — E2/S1-S3 moved
them off ``assembly.py``, which re-exports), and the onboard/driver/cli
entrypoints, and REDs if the builder:

(a) HAND-NAMES A CASTING FIELD-SET MEMBER on a PER-NODE casting carrier instead of
    consuming the casting bag. The per-node/per-lane casting carriers are the
    ``AgentSpec``/``BrickSpec`` dataclasses and the ``brick()``/``agent()`` builder
    functions: each must carry the opaque ``casting`` ``Mapping`` bag (built once from
    ``CASTING_FIELDS`` via ``_build_casting_bag``) and must NOT declare any casting
    field-set member (``preferred_*`` source name or its ``selected_*`` projection, both
    derived from ``CASTING_FIELDS``) as a named dataclass FIELD or function PARAMETER.
    Naming such a scalar field is the bypass: a new dial (effort) would then need a new
    field, re-blurring the API. (The building-WIDE selection envelope —
    ``ComposedGraph``/``assemble()``/the rendered intent dict — is NOT a per-node casting
    carrier; it is the legitimate explicit building-wide intake surface the design keeps,
    so a single building-wide ``selected_adapter_ref`` scalar there is not flagged. This
    guard fires ONLY on the per-node carriers naming a casting member.)

(b) HARDCODES A GATE/CONCERN/ADOPTION ``.value`` that is NOT derived from the axis vocab.
    The builder ``Gate``/``Concern``/``Adoption`` enums must DERIVE their member values
    from ``link.spec.GATE_CONCEPT_TOKENS`` / ``agent.return_fact.TRANSITION_CONCERN_KINDS``
    / ``link.spec.ADOPTION_LITERALS`` (the ``_axis_enum`` generated-enum path carries NO
    token literals). The guard REDs on any ``Enum`` class body — or functional
    ``Enum(name, {...})`` call — whose string-constant member values re-state (>=2 of) one
    axis vocabulary as literals.

WHAT IS NOT A BYPASS (never RED)
--------------------------------
- A single building-wide ``selected_adapter_ref`` / ``selected_model_ref`` scalar on the
  ``ComposedGraph`` envelope / ``assemble()`` intake / the rendered intent dict: that is
  the explicit building-wide selection surface (design §3 keeps adapter explicit-required),
  not a per-node casting carrier. The guard scopes check (a) to the per-node carriers.
- The friendly base-word casting kwargs (``adapter=`` / ``model=`` / ``reasoning_effort=``)
  on ``brick()``/``agent()``/``assemble()``: those flow THROUGH the bag (they key into
  ``_CASTING_KWARG_BY_NAME``, generic over ``CASTING_FIELDS``); they are bag consumption,
  not a named field-set member. They are bare base words, not ``preferred_*``/``selected_*``
  field-set names, so they are structurally outside check (a).
- An enum that names <2 axis tokens, or whose values are not string literals (the derived
  ``_axis_enum`` reads an imported vocab name, not literals): not an axis re-encoding.

GUARD-FIRST
-----------
On the current tree the per-node carriers carry only the ``casting`` bag and the three
enums are axis-derived, so this guard is GREEN now and turns RED on a NEW bypass.

Mutation-RED:
  * re-add a named ``adapter``/``model`` (or ``selected_model_ref``) scalar FIELD to
    ``AgentSpec`` / ``BrickSpec`` (or as a ``brick()``/``agent()`` parameter) -> RED;
  * re-add ``class Gate(Enum): STRICT_EVIDENCE = "strict-evidence"; COO_REVIEW =
    "coo-review"`` (hardcoded gate ``.value``s) -> RED.

Support evidence only: this checker decides no Movement and judges no source truth,
success, or quality. It is an independent AST oracle over the casting field-set names +
the three axis vocabularies; it imports the axis vocab read-only to derive the member-sets
it scans for, authoring nothing.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


# The builder entrypoints this guard scans. E2/S1-S3 relocated the per-node
# casting carriers (``BrickSpec``/``brick()`` and ``AgentSpec``/``agent()``) out of
# ``assembly.py`` to their axis homes (``brick/spec.py`` / ``agent/spec.py``);
# ``assembly.py`` now RE-EXPORTS them, so the carrier DEFINITIONS this guard checks
# live on the axes. Both axis files are scanned here so a re-add of a named casting
# scalar on the relocated carrier is still caught (re-export alone would let the
# carrier slip the scan). ``assembly.py`` stays scanned for check (b): the
# Gate/Concern/Adoption enums (``_axis_enum``) still live there and must stay
# axis-derived. onboard/driver/cli remain scanned for both checks.
BUILDER_ENTRYPOINTS: tuple[str, ...] = (
    "support/operator/assembly.py",
    "brick/spec.py",
    "agent/spec.py",
    "support/operator/onboard.py",
    "support/operator/driver.py",
    "support/operator/cli.py",
)

# The PER-NODE casting carriers (check (a) scope). Each must carry the opaque
# ``casting`` bag and name NO casting field-set member. After E2/S1-S3 these are
# DEFINED on their axes (``BrickSpec``/``brick()`` in ``brick/spec.py``,
# ``AgentSpec``/``agent()`` in ``agent/spec.py``) and merely re-exported by
# ``assembly.py``; the guard catches the carrier wherever it is DEFINED among the
# scanned entrypoints. The building-wide selection envelope (ComposedGraph/assemble/
# intent dict) is deliberately NOT listed: it is the explicit building-wide intake
# surface, not a per-node carrier.
PER_NODE_CASTING_CARRIER_CLASSES: frozenset[str] = frozenset({"AgentSpec", "BrickSpec"})
PER_NODE_CASTING_CARRIER_FUNCS: frozenset[str] = frozenset({"brick", "agent"})


def _axis_member_sets(repo: Path) -> dict[str, frozenset[str]]:
    """Derive the field-set / vocab member-sets this guard scans for (read-only).

    Imports the axis single sources so the guard never re-states them: the casting
    field-set names + their ``selected_*`` projection (Agent axis ``CASTING_FIELDS``),
    and the three builder-enum vocabularies (gate concepts / concern kinds / adoption
    literals). A new casting dial or vocab token flows in automatically.
    """

    sys.path.insert(0, str(repo / "support" / "import_identity"))
    try:
        from brick_protocol.agent.return_fact import (  # noqa: PLC0415
            TRANSITION_CONCERN_KINDS,
        )
        from brick_protocol.agent.spec import (  # noqa: PLC0415
            CASTING_FIELDS,
            NODE_CASTING_FIELDS,
        )
        from brick_protocol.link.spec import (  # noqa: PLC0415
            ADOPTION_LITERALS,
            GATE_CONCEPT_TOKENS,
        )
    except ImportError as exc:  # pragma: no cover - import wiring failure
        raise ValueError(f"builder-bypass guard could not import axis vocab: {exc}") from exc

    casting_member_names = frozenset(
        {descriptor.field_name for descriptor in CASTING_FIELDS} | set(NODE_CASTING_FIELDS)
    )
    return {
        "casting_members": casting_member_names,
        "gate": frozenset(GATE_CONCEPT_TOKENS),
        "concern": frozenset(TRANSITION_CONCERN_KINDS),
        "adoption": frozenset(ADOPTION_LITERALS),
    }


def _is_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        deco_name = getattr(target, "id", None) or getattr(target, "attr", None)
        if deco_name == "dataclass":
            return True
    return False


def _is_enum_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        base_name = getattr(base, "id", None) or getattr(base, "attr", None)
        if base_name in {"Enum", "IntEnum", "StrEnum"}:
            return True
    return False


def _string_constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _enum_class_literal_values(node: ast.ClassDef) -> set[str]:
    """String-constant member values assigned in an ``Enum`` class body."""

    values: set[str] = set()
    for stmt in node.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            text = _string_constant(stmt.value)
            if text is not None:
                values.add(text)
        elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            text = _string_constant(stmt.value)
            if text is not None:
                values.add(text)
    return values


def _functional_enum_literal_values(node: ast.Call) -> set[str]:
    """String-constant member values of a functional ``Enum(name, {...}/[...])`` call.

    Reads the second positional arg (the members container): a dict of
    ``name -> "value"`` literals, or a list/tuple of ``("name", "value")`` pairs or
    bare ``"value"`` strings. Returns the set of literal VALUES (empty when the members
    are computed, e.g. a comprehension over an imported vocab — the derived path).
    """

    func = node.func
    func_name = getattr(func, "id", None) or getattr(func, "attr", None)
    if func_name not in {"Enum", "IntEnum", "StrEnum"}:
        return set()
    if len(node.args) < 2:
        return set()
    members = node.args[1]
    values: set[str] = set()
    if isinstance(members, ast.Dict):
        for value in members.values:
            text = _string_constant(value)
            if text is not None:
                values.add(text)
    elif isinstance(members, (ast.List, ast.Tuple)):
        for element in members.elts:
            text = _string_constant(element)
            if text is not None:
                values.add(text)
            elif isinstance(element, (ast.Tuple, ast.List)) and len(element.elts) == 2:
                pair_value = _string_constant(element.elts[1])
                if pair_value is not None:
                    values.add(pair_value)
    return values


def _carrier_casting_member_violations(
    rel: str,
    tree: ast.AST,
    casting_members: frozenset[str],
) -> list[str]:
    """Check (a): per-node casting carriers must name no casting field-set member."""

    out: list[str] = []
    for node in ast.walk(tree):
        # PER-NODE carrier dataclasses: AgentSpec / BrickSpec.
        if isinstance(node, ast.ClassDef) and node.name in PER_NODE_CASTING_CARRIER_CLASSES:
            if not _is_dataclass(node):
                continue
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    field = stmt.target.id
                    if field in casting_members:
                        out.append(
                            f"{rel}: per-node casting carrier @dataclass {node.name!r} names "
                            f"casting field-set member {field!r} as a scalar field; carry the "
                            "opaque `casting` bag (keyed by CASTING_FIELDS) instead — naming a "
                            "dial bypasses the bag (a new dial would need a new field)"
                        )
        # PER-NODE builder functions: brick() / agent().
        if isinstance(node, ast.FunctionDef) and node.name in PER_NODE_CASTING_CARRIER_FUNCS:
            params = list(node.args.args) + list(node.args.kwonlyargs)
            for arg in params:
                if arg.arg in casting_members:
                    out.append(
                        f"{rel}: per-node builder {node.name}() names casting field-set member "
                        f"{arg.arg!r} as a parameter; accept casting via the generic `**casting` "
                        "(validated against CASTING_FIELDS) and thread the bag — a named dial "
                        "parameter bypasses the API"
                    )
    return out


def _enum_hardcode_violations(
    rel: str,
    tree: ast.AST,
    axis_vocabs: dict[str, frozenset[str]],
) -> list[str]:
    """Check (b): Gate/Concern/Adoption enums must derive .values, not hardcode them."""

    out: list[str] = []
    vocab_by_label = {
        "Gate": axis_vocabs["gate"],
        "Concern": axis_vocabs["concern"],
        "Adoption": axis_vocabs["adoption"],
    }

    def _judge(where: str, values: set[str]) -> None:
        for label, vocab in vocab_by_label.items():
            overlap = values & vocab
            if len(overlap) >= 2:
                out.append(
                    f"{rel}: {where} hardcodes {sorted(overlap)} — these are {label} axis "
                    f"vocabulary tokens; derive the enum from the axis vocab "
                    f"({_axis_source_hint(label)}) instead of re-stating literals "
                    "(builder re-encodes no axis vocabulary)"
                )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_enum_class(node):
            _judge(f"Enum class {node.name!r}", _enum_class_literal_values(node))
        if isinstance(node, ast.Call):
            values = _functional_enum_literal_values(node)
            if values:
                _judge("functional Enum() call", values)
    return out


def _axis_source_hint(label: str) -> str:
    return {
        "Gate": "link.spec.GATE_CONCEPT_TOKENS",
        "Concern": "agent.return_fact.TRANSITION_CONCERN_KINDS",
        "Adoption": "link.spec.ADOPTION_LITERALS",
    }[label]


def find_violations(repo: Path) -> tuple[list[str], int]:
    axis_vocabs = _axis_member_sets(repo)
    casting_members = axis_vocabs["casting_members"]

    violations: list[str] = []
    scanned = 0
    for rel in BUILDER_ENTRYPOINTS:
        path = repo / rel
        if not path.is_file():
            raise ValueError(f"builder entrypoint missing: {rel}")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            violations.append(f"{rel}: could not parse for builder-bypass scan: {exc}")
            continue
        scanned += 1
        violations.extend(_carrier_casting_member_violations(rel, tree, casting_members))
        violations.extend(_enum_hardcode_violations(rel, tree, axis_vocabs))

    return sorted(set(violations)), scanned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Builder-bypass-guard: the HEART builder consumes the 3-axis APIs and "
            "re-encodes nothing — per-node casting carriers thread the opaque casting "
            "bag (no named dial field), and the Gate/Concern/Adoption enums derive "
            "their values from the axis vocab (no hardcoded token literals). Does not "
            "prove source truth, success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    try:
        violations, scanned = find_violations(repo)
    except (OSError, ValueError) as exc:
        print(f"builder consumes axis api rejected: {exc}")
        return 1

    if violations:
        print("builder consumes axis api rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only that the builder consumes the casting "
            "bag + axis-derived enums (re-encodes no axis field-set); it does not prove "
            "source truth, success, quality, or Movement authority."
        )
        return 1

    print(
        "builder consumes axis api passed: "
        f"{scanned} builder entrypoint(s) scanned; per-node casting carriers thread the "
        "opaque casting bag and the Gate/Concern/Adoption enums derive from the axis vocab "
        "(no hand-named casting field-set member, no hardcoded enum token)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

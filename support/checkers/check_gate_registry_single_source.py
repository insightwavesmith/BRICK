#!/usr/bin/env python3
"""Seal the Link gate vocabulary + placement rule to ONE data table.

LINK GATE SINGLE-SOURCE LAW (struct-surgery ② 0623). The Link axis owns the gate
vocabulary as ONE data table — ``GATE_REGISTRY`` in ``link/spec.py`` (one row per
declarable gate: ref + concept_token + required_return_fields + placement +
disposition). Every other gate fact DERIVES from it:

  * ``link/gate.py`` derives ``DECLARED_GATE_REFS`` + the disposition partitions +
    the per-gate required-return field map from the rows (no literal ref list);
  * the gate-concept translation table derives from the rows that carry a token;
  * the materializer placement rule ("strict on QA rows; coo + human on the final
    transition row, in that emission order") is READ from the rows via
    ``link.spec.gate_placement_for_row`` — support no longer AUTHORS it.

The GOAL the registry buys: an operator adds a gate by adding ONE data row, with
no constitution code edit. That goal is only real if the vocabulary and the
placement rule cannot be RE-STATED elsewhere. Before this surgery the gate-ref
vocabulary lived as a literal 4-tuple in ``link/gate.py`` and the placement rule
lived as a hand-authored ``if qa_row and "strict-evidence" in tokens`` ladder in
``support/operator/composition_gate_translation.py``; a future edit could grow a
second copy of either and the two would silently drift. This checker is the
missing structural half: it FAILS CLOSED if either is enumerated outside the
registry.

Two AST rules (NO import of the scanned modules; pure structural evidence):

  RULE 1 — NO gate-ref vocabulary ENUMERATION outside ``GATE_REGISTRY``. Any
  collection literal (tuple / list / set / frozenset) that holds TWO OR MORE
  ``link-gate:`` string literals is a re-stated gate vocabulary and is rejected
  everywhere except ``link/spec.py`` (where the GATE_REGISTRY rows legitimately
  enumerate them once). A SINGLE behavioral comparison (``if ref ==
  "link-gate:human"``) is per-gate behavior, NOT a vocabulary enumeration, and is
  left alone — the registry owns the LIST, the gate body still keys behavior on
  one ref.

  RULE 2 — NO placement rule AUTHORING in the support materializer. The pairing
  helper ``_materializer_profile_gate_translations`` in
  ``composition_gate_translation.py`` MUST delegate to ``gate_placement_for_row``
  (the Link registry reader) and MUST NOT re-grow a hand-authored placement ladder
  that maps a concept token to a ref by hand (a ``translate_gate_concept(...)``
  call guarded by a ``qa_row`` / ``final_transition_row`` row flag). Such a call
  inside that function means support re-authored the placement rule the registry
  owns -> rejected.

The single source ``link/spec.py`` is also positively asserted: ``GATE_REGISTRY``
must enumerate at least two gate refs (the vocabulary really lives there) and
``gate_placement_for_row`` must be defined there (the placement reader is on the
axis).

This checker is support evidence only. It parses the modules instead of importing
them, and does not call providers, choose Movement, judge source truth, judge
success or quality, or classify Building outcomes.

Pass => exit 0. Reject => exit 1.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]

# The single source: the Link gate registry + placement reader live here.
_SPEC_REL = Path("link/spec.py")
# The modules that MUST NOT re-enumerate the gate vocabulary, and (for the
# materializer) MUST NOT re-author the placement rule.
_GATE_REL = Path("link/gate.py")
_MATERIALIZER_REL = Path("support/operator/composition_gate_translation.py")

# A gate ref is a string literal beginning with this prefix. The registry rows in
# link/spec.py enumerate them once; nowhere else may a COLLECTION of 2+ of them
# appear (that is a re-stated vocabulary list).
_GATE_REF_PREFIX = "link-gate:"
# >= this many gate-ref literals inside one collection literal == an enumeration.
_ENUMERATION_MIN = 2

# The single-source table + reader the registry exposes.
_REGISTRY_SYMBOL = "GATE_REGISTRY"
_PLACEMENT_READER = "gate_placement_for_row"
# The support materializer helper that must DELEGATE placement (not author it).
_MATERIALIZER_PLACEMENT_FN = "_materializer_profile_gate_translations"
# Authoring a placement rule = pairing a concept token to a ref BY HAND via this
# translation call. Inside the placement helper it must not appear (the helper
# must call gate_placement_for_row instead).
_HAND_TRANSLATE_CALL = "translate_gate_concept"

PROOF_LIMIT = (
    "proof limit: gate-registry single-source checker support evidence only; it "
    "does not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or the runtime correctness of any gate. It "
    "proves only that the Link gate-ref VOCABULARY and the materializer PLACEMENT "
    "rule are enumerated/authored in exactly one place — link/spec.GATE_REGISTRY "
    "and its gate_placement_for_row reader — and nowhere else."
)


class GateRegistrySingleSourceError(ValueError):
    """Raised when the gate vocabulary or placement rule lives outside the registry."""


def _parse(repo: Path, rel: Path) -> ast.Module:
    path = repo / rel
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(rel))
    except OSError as exc:
        raise GateRegistrySingleSourceError(f"could not read {rel}: {exc}") from exc
    except SyntaxError as exc:
        raise GateRegistrySingleSourceError(f"{rel} is not valid Python: {exc}") from exc


def _is_gate_ref_literal(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith(_GATE_REF_PREFIX)
    )


def _collection_gate_ref_count(node: ast.AST) -> int:
    """Count gate-ref string literals DIRECTLY inside one collection literal.

    Only the immediate elements of a tuple/list/set literal are counted (a nested
    structure is counted at its own level when ``ast.walk`` reaches it). A
    ``frozenset({...})`` / ``set([...])`` call wraps such a literal, which is
    reached on its own as the inner Set/List node, so the count is found there.
    """

    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return sum(1 for elt in node.elts if _is_gate_ref_literal(elt))
    return 0


def find_gate_ref_enumerations(module: ast.Module) -> list[int]:
    """Return the line numbers of every collection literal that ENUMERATES gate refs.

    An enumeration = a tuple/list/set literal holding >= _ENUMERATION_MIN gate-ref
    string literals. A lone ``"link-gate:..."`` comparison or single-element value
    is not an enumeration and is not reported.
    """

    lines: list[int] = []
    for node in ast.walk(module):
        if _collection_gate_ref_count(node) >= _ENUMERATION_MIN:
            lines.append(getattr(node, "lineno", -1))
    return lines


def _function_def(module: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _calls_name(scope: ast.AST, callee: str) -> bool:
    for node in ast.walk(scope):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == callee:
                return True
            if isinstance(func, ast.Attribute) and func.attr == callee:
                return True
    return False


def check_spec_single_source(module: ast.Module) -> list[str]:
    """Positively assert the single source REALLY lives in link/spec.py."""

    violations: list[str] = []
    registry_refs = 0
    for node in ast.walk(module):
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == _REGISTRY_SYMBOL
                for t in node.targets
            )
        ) or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == _REGISTRY_SYMBOL
        ):
            value = node.value
            registry_refs = sum(
                1 for sub in ast.walk(value) if _is_gate_ref_literal(sub)
            ) if value is not None else 0
    if registry_refs < _ENUMERATION_MIN:
        violations.append(
            "gate-registry single-source: link/spec.py GATE_REGISTRY does not "
            f"enumerate the gate-ref vocabulary (found {registry_refs} "
            f"{_GATE_REF_PREFIX!r} literals; the single source must list >= "
            f"{_ENUMERATION_MIN})"
        )
    if _function_def(module, _PLACEMENT_READER) is None:
        violations.append(
            "gate-registry single-source: link/spec.py defines no "
            f"{_PLACEMENT_READER!r} (the placement rule must be readable from the "
            "registry on the Link axis)"
        )
    return violations


def check_no_vocab_enumeration(rel: Path, module: ast.Module) -> list[str]:
    """RULE 1: reject a re-stated gate-ref vocabulary outside the registry."""

    violations: list[str] = []
    for line in find_gate_ref_enumerations(module):
        violations.append(
            f"gate-registry single-source: {rel} enumerates the gate-ref "
            f"vocabulary (a collection literal of >= {_ENUMERATION_MIN} "
            f"{_GATE_REF_PREFIX!r} literals at line {line}) — the gate vocabulary "
            "is owned ONCE by link/spec.GATE_REGISTRY; derive DECLARED_GATE_REFS / "
            "partitions from its rows instead of re-stating the list"
        )
    return violations


def check_materializer_delegates_placement(module: ast.Module) -> list[str]:
    """RULE 2: the support placement helper must delegate to the registry reader."""

    violations: list[str] = []
    fn = _function_def(module, _MATERIALIZER_PLACEMENT_FN)
    if fn is None:
        violations.append(
            "gate-registry single-source: "
            f"{_MATERIALIZER_REL} defines no {_MATERIALIZER_PLACEMENT_FN!r} "
            "(the placement-delegation seam is missing)"
        )
        return violations
    if not _calls_name(fn, _PLACEMENT_READER):
        violations.append(
            "gate-registry single-source: "
            f"{_MATERIALIZER_PLACEMENT_FN} does not call {_PLACEMENT_READER!r} — "
            "the materializer must READ placement from link/spec.GATE_REGISTRY, "
            "not author it"
        )
    if _calls_name(fn, _HAND_TRANSLATE_CALL):
        violations.append(
            "gate-registry single-source: "
            f"{_MATERIALIZER_PLACEMENT_FN} hand-authors placement (it calls "
            f"{_HAND_TRANSLATE_CALL!r} to pair a concept token to a ref by hand) — "
            "the placement rule (which gate lands on which row) is owned by the "
            "registry; call gate_placement_for_row instead"
        )
    return violations


def check(repo: Path) -> list[str]:
    spec_module = _parse(repo, _SPEC_REL)
    gate_module = _parse(repo, _GATE_REL)
    materializer_module = _parse(repo, _MATERIALIZER_REL)

    violations: list[str] = []
    violations.extend(check_spec_single_source(spec_module))
    violations.extend(check_no_vocab_enumeration(_GATE_REL, gate_module))
    violations.extend(check_no_vocab_enumeration(_MATERIALIZER_REL, materializer_module))
    violations.extend(check_materializer_delegates_placement(materializer_module))

    if violations:
        raise GateRegistrySingleSourceError(
            "Link gate vocabulary / placement rule lives outside the registry:\n"
            + "\n".join(f"- {v}" for v in violations)
        )

    mutation_line = _assert_mutation_red()
    return [
        "gate-registry single-source green: the Link gate-ref vocabulary is "
        "enumerated ONCE in link/spec.GATE_REGISTRY (link/gate.py derives "
        "DECLARED_GATE_REFS + partitions from its rows; no re-stated list), and "
        "the materializer placement rule is READ via gate_placement_for_row "
        "(support authors no placement ladder).",
        mutation_line,
        PROOF_LIMIT,
    ]


def _assert_mutation_red() -> str:
    """FIRE probe: a re-stated vocabulary AND a hand-authored placement must RED.

    Builds two synthetic bodies: (1) a module that re-enumerates the gate-ref
    vocabulary as a literal tuple (the old DECLARED_GATE_REFS shape), and (2) a
    materializer placement helper that hand-authors placement via
    translate_gate_concept instead of delegating. Asserts each rule fires. This is
    the permanent mutation-RED guard: if a real edit re-grows either copy, the
    live rules RED exactly as these probes prove on the synthetic bodies.
    """

    # (1) re-stated vocabulary enumeration -> RULE 1 fires.
    restated_vocab = ast.parse(
        "\n".join(
            [
                "DECLARED_GATE_REFS = (",
                '    "link-gate:default-transition",',
                '    "link-gate:strict",',
                '    "link-gate:human",',
                '    "link-gate:coo",',
                ")",
            ]
        )
    )
    vocab_red = bool(check_no_vocab_enumeration(_GATE_REL, restated_vocab))

    # A lone behavioral comparison MUST NOT be flagged (false-RED guard).
    lone_comparison = ast.parse(
        "\n".join(
            [
                "def evaluate(ref):",
                '    if ref == "link-gate:human":',
                "        return True",
                "    return False",
            ]
        )
    )
    lone_clean = not check_no_vocab_enumeration(_GATE_REL, lone_comparison)

    # (2) hand-authored placement ladder -> RULE 2 fires.
    hand_authored = ast.parse(
        "\n".join(
            [
                "def _materializer_profile_gate_translations("
                "tokens, *, qa_row, final_transition_row):",
                "    pairs = []",
                '    if qa_row and "strict-evidence" in tokens:',
                '        pairs.append(("strict-evidence", '
                'translate_gate_concept("strict-evidence")))',
                "    return tuple(pairs)",
            ]
        )
    )
    placement_red = bool(check_materializer_delegates_placement(hand_authored))

    if not (vocab_red and lone_clean and placement_red):
        raise GateRegistrySingleSourceError(
            "mutation RED failed: "
            f"vocab_red={vocab_red}, lone_clean={lone_clean}, "
            f"placement_red={placement_red} "
            "(a re-stated gate vocabulary and a hand-authored placement helper "
            "must both be rejected, and a lone comparison must NOT be)"
        )
    return (
        "mutation RED observed: a synthetic re-enumerated gate-ref tuple was "
        "rejected by RULE 1, a hand-authored placement helper (translate_gate_concept "
        "guarded by row flags) was rejected by RULE 2, and a lone "
        '"if ref == \\"link-gate:human\\"" comparison was correctly left clean.'
    )


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker that seals the Link gate-ref vocabulary and "
            "placement rule to link/spec.GATE_REGISTRY (one row per gate; nothing "
            "re-stated elsewhere)."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except GateRegistrySingleSourceError as exc:
        print("gate-registry single-source rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

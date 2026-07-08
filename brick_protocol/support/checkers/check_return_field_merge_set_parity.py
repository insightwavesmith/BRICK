#!/usr/bin/env python3
"""Pin the structured-return merge-set to be a subset of ``_RETURN_LIST_FIELDS``.

F1 COVERAGE-GAP REGRESSION PIN (return-LANDING binds to the brick contract): the
adapter return-assembly merges a small set of structured-return fields into the
``returned`` dict by routing each through ``_merge_texts`` (a strict text-sequence
gauntlet). That merge-set lives as a literal ``{...}`` membership test inside
``_merge_structured_return_fields`` in brick_protocol/support/connection/adapter_grant_policy.py.
Every field in that merge-set MUST also be in ``_RETURN_LIST_FIELDS``
(brick_protocol/support/connection/agent_adapter.py) so the upstream normalizer
``_clean_return_field_value`` list-normalizes (and dict-flattens) it BEFORE the
merge -- otherwise the agent can return that field as a bare Mapping and the merge
raises (``TypeError: text value must be text or text sequence``) INSIDE building the
return dict, BEFORE the AgentFact is written -> the step records zero evidence.

That is exactly how ``evidence_refs`` failed F1: it was in the merge-set but absent
from ``_RETURN_LIST_FIELDS``. This checker makes that coverage gap structurally
un-reopenable: it AST-parses both real modules (NO import), extracts the merge-set
string literals and the ``_RETURN_LIST_FIELDS`` member strings, and FAILS CLOSED if
any merge-set field is missing from ``_RETURN_LIST_FIELDS``. Both adapter paths
(adapter_local_cli + adapter_gemini_http) call the SAME merge function, so one pin
covers both.

This checker is support evidence only. It does NOT call providers, run a CLI, choose
Movement, judge source truth, judge success or quality, or classify Building outcomes.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]

# The two real modules this pin binds together. The merge-set lives in the
# adapter_grant_policy merge function; the list-normalization set lives in
# agent_adapter. Both are reached AST-only (no import) so the pin is pure
# structural evidence.
_AGENT_ADAPTER_REL = Path("brick_protocol/support/connection/agent_adapter.py")
_GRANT_POLICY_REL = Path("brick_protocol/support/connection/adapter_grant_policy.py")

_LIST_FIELDS_SYMBOL = "_RETURN_LIST_FIELDS"
_MERGE_FUNCTION = "_merge_structured_return_fields"

PROOF_LIMIT = (
    "proof limit: return-field merge-set parity checker support evidence only; it "
    "does not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or the runtime correctness of the merge -- only "
    "that every structured-return merge-set field is normalized by _RETURN_LIST_FIELDS "
    "before it reaches _merge_texts (the F1 coverage-gap regression pin)."
)


class ReturnFieldMergeSetParityError(ValueError):
    """Raised when a merge-set field is missing from ``_RETURN_LIST_FIELDS``."""


def _parse(repo: Path, rel: Path) -> ast.Module:
    path = repo / rel
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(rel))
    except OSError as exc:
        raise ReturnFieldMergeSetParityError(f"could not read {rel}: {exc}") from exc
    except SyntaxError as exc:
        raise ReturnFieldMergeSetParityError(f"{rel} is not valid Python: {exc}") from exc


def _string_constants(node: ast.AST) -> frozenset[str]:
    """All string-constant elements directly inside a set/frozenset literal node."""
    elements: list[ast.expr] = []
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        elements = list(node.elts)
    elif isinstance(node, ast.Call):  # frozenset({...}) / frozenset([...])
        for arg in node.args:
            if isinstance(arg, (ast.Set, ast.List, ast.Tuple)):
                elements.extend(arg.elts)
    values: list[str] = []
    for element in elements:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            values.append(element.value)
    return frozenset(values)


def _list_fields_members(module: ast.Module, rel: Path) -> frozenset[str]:
    """Extract the member strings of the ``_RETURN_LIST_FIELDS`` assignment."""
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if _LIST_FIELDS_SYMBOL not in names:
            continue
        members = _string_constants(node.value)
        if not members:
            raise ReturnFieldMergeSetParityError(
                f"{rel}: {_LIST_FIELDS_SYMBOL} carries no string members "
                "(its literal shape changed; re-pin this checker deliberately)"
            )
        return members
    raise ReturnFieldMergeSetParityError(
        f"{rel}: missing required assignment {_LIST_FIELDS_SYMBOL}"
    )


def _merge_set_members(module: ast.Module, rel: Path) -> frozenset[str]:
    """Extract the structured-return merge-set literal from ``_merge_structured_return_fields``.

    The merge-set is the ``{...}`` set literal on the right of a ``key in {...}``
    membership test inside the merge function -- the exact set whose members get
    routed through ``_merge_texts``.
    """
    func_node: ast.FunctionDef | None = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == _MERGE_FUNCTION:
            func_node = node
            break
    if func_node is None:
        raise ReturnFieldMergeSetParityError(
            f"{rel}: missing required function {_MERGE_FUNCTION}"
        )
    members: set[str] = set()
    found = False
    for inner in ast.walk(func_node):
        if not isinstance(inner, ast.Compare):
            continue
        for op, comparator in zip(inner.ops, inner.comparators):
            if isinstance(op, ast.In) and isinstance(comparator, ast.Set):
                literal = _string_constants(comparator)
                if literal:
                    members.update(literal)
                    found = True
    if not found:
        raise ReturnFieldMergeSetParityError(
            f"{rel}: {_MERGE_FUNCTION} has no `key in {{...}}` string set-literal "
            "(the merge-set shape changed; re-pin this checker deliberately)"
        )
    return frozenset(members)


def _assert_parity(merge_set: frozenset[str], list_fields: frozenset[str]) -> str:
    missing = sorted(merge_set - list_fields)
    if missing:
        raise ReturnFieldMergeSetParityError(
            f"structured-return merge-set field(s) {missing} are NOT in "
            f"{_LIST_FIELDS_SYMBOL} -- the adapter merges them through _merge_texts "
            "without list-normalization, so an agent returning that field as a bare "
            "Mapping crashes the return-assembly BEFORE the AgentFact is written "
            "(the F1 coverage gap). Add the field(s) to "
            f"{_LIST_FIELDS_SYMBOL}."
        )
    return (
        f"merge-set parity green: every merge-set field {sorted(merge_set)} is in "
        f"{_LIST_FIELDS_SYMBOL}."
    )


def _assert_mutation_red(merge_set: frozenset[str], list_fields: frozenset[str]) -> str:
    """A ``_RETURN_LIST_FIELDS`` missing a merge-set field must be rejected.

    Drops one real merge-set field from an in-memory copy of the list-fields set
    and confirms the same parity assertion REJECTS it -- so the checker is not
    vacuously green if the real source ever loses a normalization entry.
    """
    if not merge_set:
        raise ReturnFieldMergeSetParityError(
            "mutation RED failed: merge-set is empty, nothing to drop"
        )
    victim = sorted(merge_set)[0]
    mutated_list_fields = frozenset(list_fields - {victim})
    try:
        _assert_parity(merge_set, mutated_list_fields)
    except ReturnFieldMergeSetParityError:
        return (
            f"mutation RED observed: dropping {victim!r} from {_LIST_FIELDS_SYMBOL} "
            "is rejected by the parity assertion."
        )
    raise ReturnFieldMergeSetParityError(
        f"mutation RED failed: dropping {victim!r} from {_LIST_FIELDS_SYMBOL} "
        "was still accepted as green"
    )


def check(repo: Path) -> list[str]:
    list_fields = _list_fields_members(_parse(repo, _AGENT_ADAPTER_REL), _AGENT_ADAPTER_REL)
    merge_set = _merge_set_members(_parse(repo, _GRANT_POLICY_REL), _GRANT_POLICY_REL)
    parity_line = _assert_parity(merge_set, list_fields)
    mutation_line = _assert_mutation_red(merge_set, list_fields)
    return [
        "return-field merge-set parity green: "
        f"merge_set={sorted(merge_set)} is a subset of {_LIST_FIELDS_SYMBOL}.",
        parity_line,
        mutation_line,
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: every structured-return merge-set field is "
            "in _RETURN_LIST_FIELDS so the return-LANDING normalizes it before the "
            "merge (the F1 coverage-gap regression pin)."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except ReturnFieldMergeSetParityError as exc:
        print("return-field merge-set parity rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Pin step-output evidence packet fields to one writer-owned shape."""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
STEP_OUTPUTS_REL = Path("brick_protocol/support/recording/step_outputs.py")
SINGLE_SOURCE_SYMBOL = "EVIDENCE_SHAPE_FIELDS"
EVIDENCE_SHAPE_HELPER = "_evidence_shape_fields"

PACKET_BUILDERS: dict[str, str] = {
    "write_step_output": "list-coercion step-output manifest",
    "write_adapter_error_outputs": "merge-set adapter-error record",
    "write_chat_session_park_outputs": "merge-set chat-session park record",
}

_ANCHOR_KEYS = frozenset({"proof_limits", "not_proven"})
_OPTIONAL_MIRROR_KEYS = frozenset({"task_source_ref"})

PROOF_LIMIT = (
    "proof limit: step-output evidence field-set parity checker support evidence "
    "only; it does not prove source truth, success judgment, quality judgment, "
    "Movement authority, provider behavior, or runtime evidence correctness -- "
    "only that the three step-output-family builders carry the same "
    "single-sourced evidence-shape field set."
)


class StepOutputEvidenceFieldSetParityError(ValueError):
    """Raised when a step-output evidence packet drifts from the single source."""


def _parse(repo: Path) -> ast.Module:
    path = repo / STEP_OUTPUTS_REL
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(STEP_OUTPUTS_REL))
    except OSError as exc:
        raise StepOutputEvidenceFieldSetParityError(
            f"could not read {STEP_OUTPUTS_REL}: {exc}"
        ) from exc
    except SyntaxError as exc:
        raise StepOutputEvidenceFieldSetParityError(
            f"{STEP_OUTPUTS_REL} is not valid Python: {exc}"
        ) from exc


def _string_constant(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _frozenset_string_members(node: ast.AST) -> frozenset[str] | None:
    if not isinstance(node, ast.Call):
        return None
    builder = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
    if builder not in {"frozenset", "set"} or len(node.args) != 1 or node.keywords:
        return None
    inner = node.args[0]
    if not isinstance(inner, (ast.Set, ast.List, ast.Tuple)):
        return None
    members: list[str] = []
    for element in inner.elts:
        text = _string_constant(element)
        if text is None:
            return None
        members.append(text)
    return frozenset(members) if members else None


def _read_single_source(tree: ast.Module) -> frozenset[str]:
    for stmt in tree.body:
        target_name: str | None = None
        value: ast.AST | None = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name):
                target_name = target.id
                value = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            target_name = stmt.target.id
            value = stmt.value
        if target_name != SINGLE_SOURCE_SYMBOL or value is None:
            continue
        members = _frozenset_string_members(value)
        if members is None:
            break
        if not (_ANCHOR_KEYS <= members):
            raise StepOutputEvidenceFieldSetParityError(
                f"{SINGLE_SOURCE_SYMBOL} must contain the evidence-triple anchor "
                f"keys {sorted(_ANCHOR_KEYS)}; got {sorted(members)}"
            )
        return members
    raise StepOutputEvidenceFieldSetParityError(
        f"{STEP_OUTPUTS_REL} must declare {SINGLE_SOURCE_SYMBOL} as a frozenset "
        "of string literals"
    )


def _is_evidence_shape_helper_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == EVIDENCE_SHAPE_HELPER
    )


def _dict_key_set(node: ast.Dict, expected: frozenset[str]) -> frozenset[str] | None:
    keys: set[str] = set()
    for key, value in zip(node.keys, node.values):
        text = _string_constant(key)
        if text is not None:
            keys.add(text)
            continue
        if key is None and _is_evidence_shape_helper_call(value):
            keys.update(expected)
            continue
        return None
    return frozenset(keys)


def _evidence_like_keys(keys: frozenset[str], expected: frozenset[str]) -> frozenset[str]:
    return frozenset(
        key
        for key in keys
        if key in expected
        or key in _OPTIONAL_MIRROR_KEYS
        or key.startswith("evidence_")
    )


def _evidence_packet_keys(
    func: ast.FunctionDef,
    expected: frozenset[str],
) -> frozenset[str] | None:
    for node in ast.walk(func):
        if not isinstance(node, ast.Dict):
            continue
        key_set = _dict_key_set(node, expected)
        if key_set is None:
            continue
        if _ANCHOR_KEYS <= key_set:
            return key_set
    return None


def _assert_parity(tree: ast.Module, expected: frozenset[str]) -> list[str]:
    funcs: dict[str, ast.FunctionDef] = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    violations: list[str] = []
    for func_name, label in PACKET_BUILDERS.items():
        func = funcs.get(func_name)
        if func is None:
            violations.append(
                f"{STEP_OUTPUTS_REL}: expected packet builder {func_name!r} "
                f"({label}) is absent"
            )
            continue
        packet_keys = _evidence_packet_keys(func, expected)
        if packet_keys is None:
            violations.append(
                f"{STEP_OUTPUTS_REL}: {func_name!r} ({label}) builds no evidence "
                f"packet dict carrying the anchor keys {sorted(_ANCHOR_KEYS)}"
            )
            continue
        candidate = _evidence_like_keys(packet_keys, expected) - _OPTIONAL_MIRROR_KEYS
        if candidate != expected:
            missing = sorted(expected - candidate)
            extra = sorted(candidate - expected)
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if extra:
                detail.append(f"extra {extra}")
            violations.append(
                f"{STEP_OUTPUTS_REL}: {func_name!r} ({label}) evidence-shape field "
                f"set {sorted(candidate)} != {SINGLE_SOURCE_SYMBOL} "
                f"{sorted(expected)} ({'; '.join(detail)})"
            )
    return sorted(set(violations))


def _drop_first_helper_spread(tree: ast.Module) -> ast.Module:
    mutated = ast.fix_missing_locations(ast.parse(ast.unparse(tree)))
    for func in [node for node in mutated.body if isinstance(node, ast.FunctionDef)]:
        if func.name != "write_adapter_error_outputs":
            continue
        for node in ast.walk(func):
            if not isinstance(node, ast.Dict):
                continue
            for index, (key, value) in enumerate(zip(node.keys, node.values)):
                if key is None and _is_evidence_shape_helper_call(value):
                    del node.keys[index]
                    del node.values[index]
                    return mutated
    raise StepOutputEvidenceFieldSetParityError(
        "mutation RED setup failed: no evidence-shape helper spread found to drop"
    )


def _assert_mutation_red(tree: ast.Module, expected: frozenset[str]) -> str:
    mutated = _drop_first_helper_spread(tree)
    violations = _assert_parity(mutated, expected)
    if violations:
        return (
            "mutation RED observed: dropping the evidence-shape helper spread from "
            "write_adapter_error_outputs is rejected by the parity assertion."
        )
    raise StepOutputEvidenceFieldSetParityError(
        "mutation RED failed: dropping the evidence-shape helper spread was still accepted"
    )


def check(repo: Path) -> list[str]:
    tree = _parse(repo)
    expected = _read_single_source(tree)
    violations = _assert_parity(tree, expected)
    if violations:
        raise StepOutputEvidenceFieldSetParityError("\n- ".join(violations))
    mutation_line = _assert_mutation_red(tree, expected)
    return [
        "step-output evidence field-set parity green: every step-output-family "
        f"packet carries {sorted(expected)} from {SINGLE_SOURCE_SYMBOL}.",
        mutation_line,
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: the three step-output-family packet "
            "builders carry the same evidence-shape field set, single-sourced "
            "from EVIDENCE_SHAPE_FIELDS in brick_protocol/support/recording/step_outputs.py."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except StepOutputEvidenceFieldSetParityError as exc:
        print("step-output evidence field-set parity rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Seal gate-sequence policy action vocabulary to brick_protocol/link/gate.py.

Link owns the gate-sequence policy action vocabulary:

* ADMITTED_POLICY_ACTIONS
* ON_MISSING_REQUIRED_FACTS_ACTIONS
* ON_SUFFICIENT_ACTIONS
* normalize_gate_policy_action

Support may import or re-export those names, but must not re-state the member
sets. This checker is support evidence only. It parses Python source with AST,
does not import operator modules, and does not choose Movement or judge quality.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_LINK_GATE_REL = Path("brick_protocol/link/gate.py")
_CHECKER_REL = Path("brick_protocol/support/checkers/check_gate_policy_action_single_source.py")
_SCAN_ROOTS = (Path("brick_protocol/brick"), Path("brick_protocol/agent"), Path("brick_protocol/link"), Path("brick_protocol/support"))
_ACTION_LITERALS = frozenset(("forward", "hold", "next", "reroute"))
_PARTITION_LITERALS = (
    frozenset(("reroute", "hold")),
    frozenset(("next", "forward")),
)
_REQUIRED_LINK_SYMBOLS = (
    "ADMITTED_POLICY_ACTIONS",
    "ON_MISSING_REQUIRED_FACTS_ACTIONS",
    "ON_SUFFICIENT_ACTIONS",
    "normalize_gate_policy_action",
)
_NORMALIZER_CONSUMER_FUNCTIONS = {
    Path("brick_protocol/support/operator/gate_sequence.py"): "_action_literal",
    Path("brick_protocol/support/operator/plan_validation.py"): "_gate_sequence_action_literal",
}

PROOF_LIMIT = (
    "proof limit: gate-policy-action single-source checker support evidence only; "
    "it proves only that Python source does not re-state the Link-owned policy "
    "action member sets outside brick_protocol/link/gate.py. It does not prove source truth, "
    "success judgment, quality judgment, Movement authority, provider behavior, "
    "or runtime gate correctness."
)


class GatePolicyActionSingleSourceError(ValueError):
    """Raised when gate policy action vocabulary is re-stated outside brick_protocol/link/gate.py."""


def _parse(repo: Path, rel: Path) -> ast.Module:
    path = repo / rel
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(rel))
    except OSError as exc:
        raise GatePolicyActionSingleSourceError(f"could not read {rel}: {exc}") from exc
    except SyntaxError as exc:
        raise GatePolicyActionSingleSourceError(f"{rel} is not valid Python: {exc}") from exc


def _assigned_names(module: ast.Module) -> frozenset[str]:
    names: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef):
            names.add(node.name)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return frozenset(names)


def _collection_text_members(node: ast.AST) -> frozenset[str]:
    if not isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return frozenset()
    values: set[str] = set()
    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            values.add(element.value)
    return frozenset(values)


def find_policy_action_restatements(module: ast.Module) -> list[tuple[int, frozenset[str]]]:
    restatements: list[tuple[int, frozenset[str]]] = []
    for node in ast.walk(module):
        members = _collection_text_members(node)
        if len(members) < 2:
            continue
        if members == _ACTION_LITERALS or members in _PARTITION_LITERALS:
            restatements.append((getattr(node, "lineno", -1), members))
    return restatements


def find_normalization_reimplementations(
    module: ast.Module,
    function_name: str,
) -> list[str]:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            calls = [
                call
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr in {"lower", "upper", "casefold"}
            ]
            delegated = any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "normalize_gate_policy_action"
                for call in ast.walk(node)
            )
            if calls or not delegated:
                return [
                    f"{function_name} must delegate case normalization to "
                    "brick_protocol/link/gate.py normalize_gate_policy_action"
                ]
            return []
    return [f"{function_name} not found"]


def check_link_gate_home(module: ast.Module) -> list[str]:
    present = _assigned_names(module)
    missing = [name for name in _REQUIRED_LINK_SYMBOLS if name not in present]
    if not missing:
        return []
    return [
        "gate-policy-action single-source: brick_protocol/link/gate.py is missing required "
        f"Link-owned symbol(s): {', '.join(missing)}"
    ]


def _iter_python_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for root in _SCAN_ROOTS:
        base = repo / root
        if not base.exists():
            continue
        files.extend(path.relative_to(repo) for path in base.rglob("*.py"))
    return sorted(files)


def check(repo: Path) -> list[str]:
    violations: list[str] = []
    violations.extend(check_link_gate_home(_parse(repo, _LINK_GATE_REL)))

    for rel in _iter_python_files(repo):
        if rel in (_LINK_GATE_REL, _CHECKER_REL):
            continue
        module = _parse(repo, rel)
        for line, members in find_policy_action_restatements(module):
            violations.append(
                "gate-policy-action single-source: "
                f"{rel}:{line} re-states Link-owned policy action set "
                f"{tuple(sorted(members))}; import from brick_protocol/link/gate.py instead"
            )
        if rel in _NORMALIZER_CONSUMER_FUNCTIONS:
            for problem in find_normalization_reimplementations(
                module,
                _NORMALIZER_CONSUMER_FUNCTIONS[rel],
            ):
                violations.append(
                    "gate-policy-action single-source: " f"{rel}: {problem}"
                )

    if violations:
        raise GatePolicyActionSingleSourceError(
            "gate policy action vocabulary lives outside brick_protocol/link/gate.py:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )

    mutation_line = _assert_mutation_red()
    return [
        "gate-policy-action single-source green: gate-sequence policy action "
        "vocabulary and partition subsets are declared in brick_protocol/link/gate.py, with no "
        "Python re-statement outside the Link home.",
        mutation_line,
        PROOF_LIMIT,
    ]


def _assert_mutation_red() -> str:
    restated_all = ast.parse(
        'ADMITTED_POLICY_ACTIONS = ("forward", "hold", "next", "reroute")\n'
    )
    restated_missing = ast.parse(
        'ON_MISSING_REQUIRED_FACTS_ACTIONS = {"reroute", "hold"}\n'
    )
    lone_literal = ast.parse(
        "\n".join(
            [
                "def is_forward(action):",
                '    return action == "forward"',
            ]
        )
    )
    local_normalizer = ast.parse(
        "\n".join(
            [
                "def _action_literal(value):",
                "    return value.strip().lower()",
            ]
        )
    )

    all_red = bool(find_policy_action_restatements(restated_all))
    subset_red = bool(find_policy_action_restatements(restated_missing))
    lone_clean = not find_policy_action_restatements(lone_literal)
    local_normalizer_red = bool(
        find_normalization_reimplementations(local_normalizer, "_action_literal")
    )

    if not (all_red and subset_red and lone_clean and local_normalizer_red):
        raise GatePolicyActionSingleSourceError(
            "mutation RED failed: "
            f"all_red={all_red}, subset_red={subset_red}, "
            f"lone_clean={lone_clean}, "
            f"local_normalizer_red={local_normalizer_red}"
        )
    return (
        "mutation RED observed: synthetic re-stated all-action and partition "
        "member sets and local case-normalization core were rejected, while a "
        "lone action comparison was left clean."
    )


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker for Link-owned gate policy action vocabulary."
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except GatePolicyActionSingleSourceError as exc:
        print("gate-policy-action single-source rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

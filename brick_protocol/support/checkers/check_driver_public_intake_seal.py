#!/usr/bin/env python3
"""Seal brick_protocol/support/operator/driver.py public Building-making intake exports.

This checker is support evidence only. It parses driver.py instead of importing
it, and does not call providers, choose Movement, judge source truth, judge
success or quality, or classify Building outcomes. The assemble public branch is
owned by brick_protocol/support/operator/assembly.py and is outside this checker scope.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_DRIVER_REL = Path("brick_protocol/support/operator/driver.py")
_OPERATOR_INIT_REL = Path("brick_protocol/support/operator/__init__.py")
_ONBOARD_REL = Path("brick_protocol/support/operator/onboard.py")
PUBLIC_BUILDING_MAKING_INTAKES = frozenset({"run_building_intake"})
SEALED_INTERNAL_INTAKES = frozenset({"run_composed_graph_intake"})
SEALED_HELPER_EXPORTS = frozenset({"launch_assembled_building"})
ASSEMBLE_PUBLIC_SURFACE_OUT_OF_SCOPE = "brick_protocol/support/operator/assembly.py::assemble"
PROOF_LIMIT = (
    "proof limit: driver public-intake seal checker support evidence only; it "
    "does not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or semantic correctness of future Building "
    "authoring."
)


class DriverPublicIntakeSealError(ValueError):
    """Raised when driver.py leaks a public Building-making intake."""


def _parse_driver(repo: Path) -> tuple[ast.Module, str]:
    return _parse_python(repo, _DRIVER_REL)


def _parse_python(repo: Path, relative: Path) -> tuple[ast.Module, str]:
    path = repo / relative
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(relative)), text
    except OSError as exc:
        raise DriverPublicIntakeSealError(f"could not read {relative}: {exc}") from exc
    except SyntaxError as exc:
        raise DriverPublicIntakeSealError(f"{relative} is not valid Python: {exc}") from exc


def _literal_string_sequence(node: ast.AST, label: str) -> tuple[str, ...]:
    if not isinstance(node, (ast.List, ast.Tuple)):
        raise DriverPublicIntakeSealError(f"{label} must be a literal list/tuple")
    values: list[str] = []
    for item in node.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            raise DriverPublicIntakeSealError(f"{label} must contain only literal strings")
        values.append(item.value)
    return tuple(values)


def _all_exports(module: ast.Module, label: str) -> tuple[str, ...]:
    exports: tuple[str, ...] | None = None
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ):
            if exports is not None:
                raise DriverPublicIntakeSealError(f"{label} has multiple __all__ assignments")
            exports = _literal_string_sequence(node.value, f"{label}.__all__")
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "__all__":
            if exports is not None:
                raise DriverPublicIntakeSealError(f"{label} has multiple __all__ assignments")
            if node.value is None:
                raise DriverPublicIntakeSealError(f"{label}.__all__ annotation has no value")
            exports = _literal_string_sequence(node.value, f"{label}.__all__")
    if exports is None:
        raise DriverPublicIntakeSealError(f"{label} has no __all__ assignment")
    duplicates = sorted({name for name in exports if exports.count(name) > 1})
    if duplicates:
        raise DriverPublicIntakeSealError(f"{label}.__all__ has duplicate export(s): {duplicates}")
    return exports


def _driver_all_exports(module: ast.Module) -> tuple[str, ...]:
    return _all_exports(module, "driver.py")


def _defined_functions(module: ast.Module) -> frozenset[str]:
    return frozenset(
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _function_node(module: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise DriverPublicIntakeSealError(f"driver.py missing required function {name}")


def _building_making_intake_exports(exports: Sequence[str]) -> frozenset[str]:
    return frozenset(
        name
        for name in exports
        if name.startswith("run_") and name.endswith("_intake")
    )


def _assert_docstring_seal(module: ast.Module) -> None:
    node = _function_node(module, "run_composed_graph_intake")
    docstring = ast.get_docstring(node) or ""
    first_line = docstring.strip().splitlines()[0].strip() if docstring.strip() else ""
    required = (
        "Internal/checker-only seam, not a public ordering surface; "
        "main AI uses run_building_intake or assemble."
    )
    if first_line != required:
        raise DriverPublicIntakeSealError(
            "run_composed_graph_intake docstring must open with the internal/checker-only seal line"
        )


def _assert_export_seal(exports: Sequence[str], defined_functions: frozenset[str]) -> None:
    missing_functions = sorted((PUBLIC_BUILDING_MAKING_INTAKES | SEALED_INTERNAL_INTAKES) - defined_functions)
    if missing_functions:
        raise DriverPublicIntakeSealError(f"driver.py missing required intake function(s): {missing_functions}")
    if "run_building_intake" not in exports:
        raise DriverPublicIntakeSealError("run_building_intake must remain in driver.py __all__")
    leaked_internal = sorted(SEALED_INTERNAL_INTAKES & set(exports))
    if leaked_internal:
        raise DriverPublicIntakeSealError(f"internal/checker-only intake leaked through __all__: {leaked_internal}")
    observed_making = _building_making_intake_exports(exports)
    if observed_making != PUBLIC_BUILDING_MAKING_INTAKES:
        raise DriverPublicIntakeSealError(
            "driver.py __all__ building-making intake exports must be exactly "
            f"{sorted(PUBLIC_BUILDING_MAKING_INTAKES)}, observed {sorted(observed_making)}"
        )


def _assert_mutation_red(exports: tuple[str, ...], defined_functions: frozenset[str]) -> str:
    mutated = tuple([*exports, "run_composed_graph_intake"])
    try:
        _assert_export_seal(mutated, defined_functions)
    except DriverPublicIntakeSealError:
        return "mutation RED observed: run_composed_graph_intake in __all__ rejected"
    raise DriverPublicIntakeSealError(
        "mutation RED failed: run_composed_graph_intake in __all__ was accepted"
    )


def _assert_no_helper_public_export(repo: Path) -> str:
    init_module, init_text = _parse_python(repo, _OPERATOR_INIT_REL)
    onboard_module, onboard_text = _parse_python(repo, _ONBOARD_REL)
    leaked_operator_exports = sorted(SEALED_HELPER_EXPORTS & set(_all_exports(init_module, "brick_protocol/support/operator/__init__.py")))
    leaked_onboard_exports = sorted(SEALED_HELPER_EXPORTS & set(_all_exports(onboard_module, "brick_protocol/support/operator/onboard.py")))
    leaked_reexport_defs = sorted(
        helper for helper in SEALED_HELPER_EXPORTS if f"def {helper}" in init_text
    )
    if leaked_operator_exports or leaked_onboard_exports or leaked_reexport_defs:
        raise DriverPublicIntakeSealError(
            "customer route helper leaked as public export: "
            f"operator_exports={leaked_operator_exports}, "
            f"onboard_exports={leaked_onboard_exports}, "
            f"operator_reexport_defs={leaked_reexport_defs}"
        )
    required_onboard_marker = "Internal/non-customer helper for an already-``assemble()``-d graph."
    if required_onboard_marker not in onboard_text:
        raise DriverPublicIntakeSealError(
            "onboard.launch_assembled_building must be classified as an internal/non-customer helper"
        )
    return "mutation RED observed: launch_assembled_building public export remains sealed"


def check(repo: Path) -> list[str]:
    module, _text = _parse_driver(repo)
    exports = _driver_all_exports(module)
    functions = _defined_functions(module)
    _assert_docstring_seal(module)
    _assert_export_seal(exports, functions)
    mutation_line = _assert_mutation_red(exports, functions)
    helper_export_line = _assert_no_helper_public_export(repo)
    return [
        "driver public-intake seal green: "
        f"making_intake_exports={sorted(_building_making_intake_exports(exports))}; "
        "run_composed_graph_intake not in __all__; "
        "launch_assembled_building not public-exported as a customer route; "
        f"assembly_scope={ASSEMBLE_PUBLIC_SURFACE_OUT_OF_SCOPE}.",
        mutation_line,
        helper_export_line,
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker for the driver public Building-making intake seal."
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except DriverPublicIntakeSealError as exc:
        print("driver public-intake seal rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

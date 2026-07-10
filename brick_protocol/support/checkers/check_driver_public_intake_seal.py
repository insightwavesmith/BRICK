#!/usr/bin/env python3
"""Seal the public customer Building-entry surface.

This checker is support evidence only. It parses operator and projection
surfaces instead of importing or invoking them, and does not call providers,
choose Movement, judge source truth, judge success or quality, or classify
Building outcomes. Builder lowering and declared route-family executors remain
internal mechanics behind the official customer entry contract.
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
_BUILDING_OPERATION_REL = Path("brick_protocol/support/operator/building_operation.py")
_ORCHESTRATION_PACKET_REL = Path("brick_protocol/support/operator/orchestration_packet.py")
_MCP_PROJECTION_REL = Path("brick_protocol/support/connection/mcp_projection.py")
_COO_PROMPT_REL = Path("brick_protocol/agent/prompts/coo.md")
_BUILDING_COORDINATION_RELS = (
    Path("brick_protocol/agent/skills/building-coordination/SKILL.md"),
    Path("brick_protocol/brick/templates/skills/building-coordination/SKILL.md"),
)
_TASK_INTAKE_RELS = (
    Path("brick_protocol/agent/skills/task_intake/SKILL.md"),
    Path("brick_protocol/brick/templates/skills/task_intake/SKILL.md"),
)
PUBLIC_BUILDING_MAKING_INTAKES = frozenset({"run_building_intake"})
SEALED_INTERNAL_INTAKES = frozenset({"run_composed_graph_intake"})
SEALED_HELPER_EXPORTS = frozenset({"launch_assembled_building"})
SEALED_BUILDER_INTERNAL_HELPERS = frozenset({"coo_run_orchestration_packet"})
INTERNAL_ROUTE_FAMILY_EXECUTORS = (
    "brick_protocol.support.operator.driver.run_declared_portfolio",
    "brick_protocol.support.operator.auto_repair_replay.run_declared_auto_repair_replay_case",
)
OFFICIAL_CUSTOMER_ENTRY_MARKER = "Official customer execution entrances"
INTERNAL_ROUTE_FAMILY_MARKER = (
    "Builder-internal declared route-family executors (not customer/startup entrances)"
)
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


def _read_text(repo: Path, relative: Path) -> str:
    try:
        return (repo / relative).read_text(encoding="utf-8")
    except OSError as exc:
        raise DriverPublicIntakeSealError(f"could not read {relative}: {exc}") from exc


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


def _assert_orchestration_packet_internal(repo: Path) -> str:
    facade_module, facade_text = _parse_python(repo, _BUILDING_OPERATION_REL)
    packet_module, packet_text = _parse_python(repo, _ORCHESTRATION_PACKET_REL)
    facade_exports = set(_all_exports(facade_module, str(_BUILDING_OPERATION_REL)))
    facade_imports = {
        alias.name
        for node in facade_module.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "brick_protocol.support.operator.orchestration_packet"
        for alias in node.names
    }

    def assert_no_facade_leak(exports: set[str], imports: set[str]) -> None:
        leaked_exports = sorted(SEALED_BUILDER_INTERNAL_HELPERS & exports)
        leaked_imports = sorted(SEALED_BUILDER_INTERNAL_HELPERS & imports)
        if leaked_exports or leaked_imports:
            raise DriverPublicIntakeSealError(
                "Builder-internal orchestration helper leaked through building_operation: "
                f"exports={leaked_exports}, imports={leaked_imports}"
            )

    assert_no_facade_leak(facade_exports, facade_imports)
    functions = _defined_functions(packet_module)
    if "coo_run_orchestration_packet" in functions:
        raise DriverPublicIntakeSealError(
            "orchestration_packet retains public coo_run_orchestration_packet; "
            "the Builder-internal helper must be underscore-sealed"
        )
    internal_name = "_coo_run_orchestration_packet"
    if internal_name not in functions:
        raise DriverPublicIntakeSealError(
            f"orchestration_packet missing sealed Builder-internal helper {internal_name}"
        )
    node = next(
        item
        for item in packet_module.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == internal_name
    )
    docstring = ast.get_docstring(node) or ""
    required_doc = "Builder-internal read/run material for an already-declared Building Plan."
    if not docstring.strip().startswith(required_doc):
        raise DriverPublicIntakeSealError(
            "_coo_run_orchestration_packet must open with the Builder-internal seal"
        )
    if "coo_run_orchestration_packet" in facade_text:
        raise DriverPublicIntakeSealError(
            "building_operation must not advertise coo_run_orchestration_packet"
        )
    if "customer/startup entrance" not in packet_text:
        raise DriverPublicIntakeSealError(
            "orchestration_packet module must state it is not a customer/startup entrance"
        )
    try:
        assert_no_facade_leak(
            facade_exports | SEALED_BUILDER_INTERNAL_HELPERS,
            facade_imports,
        )
    except DriverPublicIntakeSealError:
        return "mutation RED observed: coo_run_orchestration_packet facade re-export remains sealed"
    raise DriverPublicIntakeSealError(
        "mutation RED failed: coo_run_orchestration_packet facade export was accepted"
    )


def _literal_assignment_in_function(
    module: ast.Module,
    *,
    function_name: str,
    variable_name: str,
) -> tuple[str, ...]:
    function = next(
        (
            node
            for node in module.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ),
        None,
    )
    if function is None:
        raise DriverPublicIntakeSealError(f"missing function {function_name}")
    assignments = [
        node
        for node in function.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and (
            (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == variable_name
                    for target in node.targets
                )
            )
            or (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == variable_name
            )
        )
    ]
    if len(assignments) != 1:
        raise DriverPublicIntakeSealError(
            f"{function_name}.{variable_name} must have exactly one literal assignment"
        )
    value = assignments[0].value
    if value is None:
        raise DriverPublicIntakeSealError(f"{function_name}.{variable_name} has no value")
    return _literal_string_sequence(value, f"{function_name}.{variable_name}")


def _assert_mcp_route_family_executor_classification(repo: Path) -> None:
    module, _text = _parse_python(repo, _MCP_PROJECTION_REL)
    startup_refs = _literal_assignment_in_function(
        module,
        function_name="render_coo_operating_chain_context",
        variable_name="startup_surface_refs",
    )
    internal_refs = _literal_assignment_in_function(
        module,
        function_name="render_coo_operating_chain_context",
        variable_name="internal_support_surface_refs",
    )
    leaked = sorted(set(INTERNAL_ROUTE_FAMILY_EXECUTORS) & set(startup_refs))
    missing = sorted(set(INTERNAL_ROUTE_FAMILY_EXECUTORS) - set(internal_refs))
    if leaked or missing:
        raise DriverPublicIntakeSealError(
            "MCP route-family executor classification drifted: "
            f"startup_leaks={leaked}, missing_internal_refs={missing}"
        )


def _assert_entry_document(relative: Path, text: str) -> None:
    legacy_header = "Startup / handoff path candidates:"
    legacy_rows = tuple(
        f"{label}: {ref}"
        for label, ref in zip(("E", "F"), INTERNAL_ROUTE_FAMILY_EXECUTORS, strict=True)
    )
    missing_markers = [
        marker
        for marker in (OFFICIAL_CUSTOMER_ENTRY_MARKER, INTERNAL_ROUTE_FAMILY_MARKER)
        if marker not in text
    ]
    legacy_hits = [marker for marker in (legacy_header, *legacy_rows) if marker in text]
    missing_executor_refs = [
        ref for ref in INTERNAL_ROUTE_FAMILY_EXECUTORS if ref not in text
    ]
    if missing_markers or legacy_hits or missing_executor_refs:
        raise DriverPublicIntakeSealError(
            f"{relative} entry classification drifted: "
            f"missing_markers={missing_markers}, legacy_startup_advertisements={legacy_hits}, "
            f"missing_internal_executor_refs={missing_executor_refs}"
        )


def _assert_skill_entry_contract(repo: Path) -> str:
    rels = (*_BUILDING_COORDINATION_RELS, *_TASK_INTAKE_RELS, _COO_PROMPT_REL)
    for relative in rels:
        text = _read_text(repo, relative)
        _assert_entry_document(relative, text)
    _assert_mcp_route_family_executor_classification(repo)
    sample_rel = _BUILDING_COORDINATION_RELS[0]
    sample = _read_text(repo, sample_rel)
    mutated = sample.replace(
        INTERNAL_ROUTE_FAMILY_MARKER,
        "Startup / handoff path candidates:",
        1,
    )
    try:
        _assert_entry_document(sample_rel, mutated)
    except DriverPublicIntakeSealError:
        return (
            "mutation RED observed: declared portfolio and repair/replay executors "
            "remain excluded from customer startup surfaces"
        )
    raise DriverPublicIntakeSealError(
        "mutation RED failed: route-family executors were accepted as startup paths"
    )


def check(repo: Path) -> list[str]:
    module, _text = _parse_driver(repo)
    exports = _driver_all_exports(module)
    functions = _defined_functions(module)
    _assert_docstring_seal(module)
    _assert_export_seal(exports, functions)
    mutation_line = _assert_mutation_red(exports, functions)
    helper_export_line = _assert_no_helper_public_export(repo)
    orchestration_line = _assert_orchestration_packet_internal(repo)
    entry_contract_line = _assert_skill_entry_contract(repo)
    return [
        "driver public-intake seal green: "
        f"making_intake_exports={sorted(_building_making_intake_exports(exports))}; "
        "run_composed_graph_intake not in __all__; "
        "launch_assembled_building not public-exported as a customer route; "
        f"assembly_scope={ASSEMBLE_PUBLIC_SURFACE_OUT_OF_SCOPE}.",
        mutation_line,
        helper_export_line,
        orchestration_line,
        entry_contract_line,
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

"""In-process kernel-check bodies + axis-vocab drift scan + subprocess shim.

Lifted verbatim from check_profile.py (P3a behavior-preserving decomposition).
Holds the kernel-check implementations the profile runner's run_kernel_check
dispatches to (axis_vocab_drift, building_map_graph, agent_adapter_return_shape,
reporter_notification_projection) plus the in-process call_main shim. Support
checker mechanics only: it derives/observes evidence shapes; it authors no axis
crossing and decides nothing.
"""

from __future__ import annotations

import argparse
import ast
import base64
import contextlib
import hashlib
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    to_posix,
    to_repo_path,
)


_AXIS_VOCAB_EXPECTED_MOVEMENT = ("forward", "reroute")


_AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS = ("raise", "forward", "stop")


_AXIS_VOCAB_EXPECTED_DISPOSITION_OWNERS = ("caller", "coo", "caller-or-coo")


_AXIS_VOCAB_EXPECTED_PROGRESS_STATES = ("in_progress",)


_AXIS_VOCAB_EXPECTED_AUTHOR_PREFIXES = ("human:", "coo:")


_AXIS_VOCAB_REQUIRED_TRANSITION_KEYS = (
    "disposition_action",
    "budget_increment",
    "progress_state",
)


_AXIS_VOCAB_EXPECTED_ADAPTER_REFS = (
    "adapter:local",
    "adapter:codex-local",
    "adapter:claude-local",
    "adapter:gemini-local",
    # B6 (ADDITIVE): direct Gemini HTTP API adapter, sibling of gemini-local.
    "adapter:gemini-api",
    "adapter:chat-session",
)


_AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS = (
    "adapter:codex-write-local",
    "adapter:claude-write-local",
)


# W2 DOC-DECOUPLE (0611): the 0531 operating packet (stamped HISTORICAL 0610)
# was dropped from this scan; AGENTS.md carries the identical required
# transition-lifecycle texts (pinned core.yaml) and the enum truth is parsed
# from link/transition.py + link/movement.py in _axis_vocab_check_link_sources.
_AXIS_VOCAB_DOC_PATHS = (
    "AGENTS.md",
)


_AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST = {
    "link/movement.py",
    "support/checkers/check_axis_contract_projection.py",
    "support/checkers/check_profile.py",
    # ELEGANT-REFACTOR P3a: the axis-vocab drift check (with its re-encoded enum
    # literals) moved here from check_profile.py; the self-allowlist follows the
    # rehome (checker-pin-follows-rehome standard).
    "support/checkers/lib/kernel_checks.py",
}


_AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST = {
    "link/transition.py",
    "support/checkers/check_building_operator_driver0.py",
    "support/checkers/check_profile.py",
    "support/checkers/lib/kernel_checks.py",
}


_AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST = {
    "support/connection/agent_adapter.py",
    "support/checkers/check_profile.py",
    "support/checkers/lib/kernel_checks.py",
}


_AXIS_VOCAB_TRANSITION_AUTHOR_PREFIX_CONSUMERS = (
    "support/operator/plan_validation.py",
    "support/operator/walker_resume.py",
    "support/operator/walker_step_fixture.py",
)


_AXIS_VOCAB_PYTHON_SCAN_ROOTS = ("brick", "agent", "link", "support")


def _axis_vocab_parse_python(repo: Path, relative: str) -> tuple[ast.Module, str]:
    path = to_repo_path(repo, relative)
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=relative), text
    except SyntaxError as exc:
        raise ProfileError(f"axis_vocab_drift rejected {relative}: invalid Python: {exc}") from exc


def _axis_vocab_read_literal(node: ast.AST, env: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List)):
        values = [_axis_vocab_read_literal(item, env) for item in node.elts]
        return tuple(values) if isinstance(node, ast.Tuple) else values
    if isinstance(node, ast.Set):
        values = [_axis_vocab_read_literal(item, env) for item in node.elts]
        if all(isinstance(item, str) for item in values):
            return frozenset(values)
        return None
    if isinstance(node, ast.Dict):
        keys = [_axis_vocab_read_literal(item, env) for item in node.keys]
        values = [_axis_vocab_read_literal(item, env) for item in node.values]
        if all(isinstance(key, str) for key in keys):
            return dict(zip(keys, values, strict=True))
        return None
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        source = env.get(node.value.id)
        key = _axis_vocab_read_literal(node.slice, env)
        if isinstance(source, Mapping) and isinstance(key, str):
            return source.get(key)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1:
        value = _axis_vocab_read_literal(node.args[0], env)
        if node.func.id == "frozenset" and _axis_vocab_all_strings(value):
            return frozenset(value)
        if node.func.id == "set" and _axis_vocab_all_strings(value):
            return set(value)
        if node.func.id == "tuple" and _axis_vocab_all_strings(value):
            return tuple(value)
        if node.func.id == "list" and _axis_vocab_all_strings(value):
            return list(value)
    return None


def _axis_vocab_all_strings(value: Any) -> bool:
    return isinstance(value, (tuple, list, set, frozenset)) and all(
        isinstance(item, str) for item in value
    )


def _axis_vocab_module_env(tree: ast.Module) -> dict[str, Any]:
    env: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            value = _axis_vocab_read_literal(node.value, env)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    env[target.id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            env[node.target.id] = _axis_vocab_read_literal(node.value, env) if node.value else None
    return env


def _axis_vocab_sequence(env: Mapping[str, Any], name: str, label: str) -> tuple[str, ...]:
    value = env.get(name)
    if not _axis_vocab_all_strings(value):
        raise ProfileError(f"axis_vocab_drift rejected {label}: {name} must be a string sequence")
    return tuple(value)


def _axis_vocab_set(env: Mapping[str, Any], name: str, label: str) -> frozenset[str]:
    value = env.get(name)
    if not _axis_vocab_all_strings(value):
        raise ProfileError(f"axis_vocab_drift rejected {label}: {name} must be a string set")
    return frozenset(value)


def _axis_vocab_literal_string_set(node: ast.AST) -> frozenset[str] | None:
    if not isinstance(node, (ast.Set, ast.Tuple, ast.List)):
        return None
    values: list[str] = []
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        values.append(element.value)
    if not values:
        return None
    return frozenset(values)


def _axis_vocab_import_aliases(tree: ast.Module, module_name: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        is_relative = node.level == 1 and node.module == module_name
        is_absolute = node.level == 0 and node.module == f"support.connection.{module_name}"
        if not (is_relative or is_absolute):
            continue
        for alias in node.names:
            aliases[alias.name] = alias.asname or alias.name
    return aliases


def _axis_vocab_absolute_import_aliases(tree: ast.Module, module_name: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level != 0 or node.module != module_name:
            continue
        for alias in node.names:
            aliases[alias.name] = alias.asname or alias.name
    return aliases


def _axis_vocab_assigned_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
        elif isinstance(node, (ast.AugAssign, ast.For)):
            targets.append(node.target)
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _axis_vocab_name_used(tree: ast.Module, name: str) -> bool:
    return any(isinstance(node, ast.Name) and node.id == name for node in ast.walk(tree))


def _axis_vocab_python_files(repo: Path) -> list[Path]:
    paths: list[Path] = []
    for root_name in _AXIS_VOCAB_PYTHON_SCAN_ROOTS:
        root = repo / root_name
        if not root.is_dir():
            continue
        paths.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(paths)


def _axis_vocab_scan_exact_enum_redefinitions(repo: Path, violations: list[str]) -> int:
    movement_set = frozenset(_AXIS_VOCAB_EXPECTED_MOVEMENT)
    disposition_set = frozenset(_AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS)
    adapter_set = frozenset(_AXIS_VOCAB_EXPECTED_ADAPTER_REFS)
    inspected = 0
    for path in _axis_vocab_python_files(repo):
        relative = to_posix(path.relative_to(repo))
        tree, _text = _axis_vocab_parse_python(repo, relative)
        inspected += 1
        for node in ast.walk(tree):
            values = _axis_vocab_literal_string_set(node)
            if values is None:
                continue
            if values == movement_set and relative not in _AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST:
                violations.append(
                    f"{relative}:{getattr(node, 'lineno', '?')}: exact Movement enum "
                    "literal must import/read Link-owned MOVEMENT_LITERALS"
                )
            if values == disposition_set and relative not in _AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST:
                violations.append(
                    f"{relative}:{getattr(node, 'lineno', '?')}: exact disposition_action "
                    "enum literal must import/read link/transition.py DISPOSITION_ACTIONS"
                )
            if values == adapter_set and relative not in _AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST:
                violations.append(
                    f"{relative}:{getattr(node, 'lineno', '?')}: exact adapter ref enum "
                    "literal must import/read support/connection/agent_adapter.py ALLOWED_ADAPTER_REFS"
                )
    return inspected


def _axis_vocab_check_link_sources(repo: Path, violations: list[str]) -> None:
    movement_tree, _movement_text = _axis_vocab_parse_python(repo, "link/movement.py")
    transition_tree, _transition_text = _axis_vocab_parse_python(repo, "link/transition.py")
    movement_env = _axis_vocab_module_env(movement_tree)
    transition_env = _axis_vocab_module_env(transition_tree)

    movement_literals = _axis_vocab_sequence(movement_env, "MOVEMENT_LITERALS", "link/movement.py")
    if movement_literals != _AXIS_VOCAB_EXPECTED_MOVEMENT:
        violations.append(
            "link/movement.py: MOVEMENT_LITERALS must equal "
            f"{list(_AXIS_VOCAB_EXPECTED_MOVEMENT)}, observed {list(movement_literals)}"
        )

    disposition_actions = _axis_vocab_sequence(
        transition_env,
        "DISPOSITION_ACTIONS",
        "link/transition.py",
    )
    if disposition_actions != _AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS:
        violations.append(
            "link/transition.py: DISPOSITION_ACTIONS must equal "
            f"{list(_AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS)}, observed {list(disposition_actions)}"
        )

    owners = _axis_vocab_set(
        transition_env,
        "TRANSITION_LIFECYCLE_DISPOSITION_OWNERS",
        "link/transition.py",
    )
    expected_owners = frozenset(_AXIS_VOCAB_EXPECTED_DISPOSITION_OWNERS)
    if owners != expected_owners:
        violations.append(
            "link/transition.py: TRANSITION_LIFECYCLE_DISPOSITION_OWNERS must equal "
            f"{sorted(expected_owners)}, observed {sorted(owners)}"
        )
    if "human" in owners:
        violations.append("link/transition.py: human must not be a required_disposition_owner")

    progress_states = _axis_vocab_set(
        transition_env,
        "TRANSITION_LIFECYCLE_PROGRESS_STATES",
        "link/transition.py",
    )
    expected_progress = frozenset(_AXIS_VOCAB_EXPECTED_PROGRESS_STATES)
    if progress_states != expected_progress:
        violations.append(
            "link/transition.py: TRANSITION_LIFECYCLE_PROGRESS_STATES must equal "
            f"{sorted(expected_progress)}, observed {sorted(progress_states)}"
        )

    allowed_keys = _axis_vocab_set(
        transition_env,
        "TRANSITION_LIFECYCLE_ALLOWED_KEYS",
        "link/transition.py",
    )
    missing_keys = sorted(set(_AXIS_VOCAB_REQUIRED_TRANSITION_KEYS) - set(allowed_keys))
    if missing_keys:
        violations.append(
            "link/transition.py: TRANSITION_LIFECYCLE_ALLOWED_KEYS missing "
            f"{missing_keys}"
        )

    author_prefixes = _axis_vocab_sequence(
        transition_env,
        "TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES",
        "link/transition.py",
    )
    if author_prefixes != _AXIS_VOCAB_EXPECTED_AUTHOR_PREFIXES:
        violations.append(
            "link/transition.py: TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES must equal "
            f"{list(_AXIS_VOCAB_EXPECTED_AUTHOR_PREFIXES)}, observed {list(author_prefixes)}"
        )
    if "caller:" in author_prefixes:
        violations.append("link/transition.py: caller: is not an admitted transition disposition author prefix")


def _axis_vocab_check_transition_author_prefix_consumers(repo: Path, violations: list[str]) -> None:
    source_name = "TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES"
    for relative in _AXIS_VOCAB_TRANSITION_AUTHOR_PREFIX_CONSUMERS:
        tree, _text = _axis_vocab_parse_python(repo, relative)
        imports = _axis_vocab_absolute_import_aliases(tree, "brick_protocol.link.transition")
        alias = imports.get(source_name)
        if not alias:
            violations.append(
                f"{relative}: transition disposition author prefixes must import "
                f"{source_name} from brick_protocol.link.transition"
            )
        elif not _axis_vocab_name_used(tree, alias):
            violations.append(
                f"{relative}: imported transition disposition author-prefix alias "
                f"{alias!r} is not read"
            )


def _axis_vocab_check_docs(repo: Path, violations: list[str]) -> None:
    required = [
        "progress_state: in_progress",
        "required_disposition_owner: caller | coo | caller-or-coo",
        "disposition_action: raise | forward | stop",
        "budget_increment: <finite positive integer, required only for raise>",
        "`human:/coo:/caller:` are author prefixes, not owner values",
        "admits `human:` and `coo:` author prefixes only",
        "finite positive `budget_increment`",
        "`forward` and `stop` must not carry",
    ]
    for relative in _AXIS_VOCAB_DOC_PATHS:
        text = to_repo_path(repo, relative).read_text(encoding="utf-8")
        compact_text = " ".join(text.split())
        for needle in required:
            if needle not in compact_text:
                violations.append(f"{relative}: missing transition lifecycle text {needle!r}")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if "required_disposition_owner" in line and "human" in line:
                violations.append(
                    f"{relative}:{line_no}: human must not appear as required_disposition_owner"
                )


def _axis_vocab_check_agent_adapter_refs(repo: Path, violations: list[str]) -> None:
    adapter_tree, _adapter_text = _axis_vocab_parse_python(repo, "support/connection/agent_adapter.py")
    adapter_env = _axis_vocab_module_env(adapter_tree)
    adapter_refs = _axis_vocab_set(
        adapter_env,
        "ALLOWED_ADAPTER_REFS",
        "support/connection/agent_adapter.py",
    )
    expected_adapter_refs = frozenset(_AXIS_VOCAB_EXPECTED_ADAPTER_REFS)
    if adapter_refs != expected_adapter_refs:
        violations.append(
            "support/connection/agent_adapter.py: ALLOWED_ADAPTER_REFS must equal "
            f"{sorted(expected_adapter_refs)}, observed {sorted(adapter_refs)}"
        )
    retired_adapter_refs = sorted(set(_AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS) & set(adapter_refs))
    if retired_adapter_refs:
        violations.append(
            "support/connection/agent_adapter.py: retired write adapter refs must not be "
            f"admitted active adapters: {retired_adapter_refs}"
        )

    resources_tree, _resources_text = _axis_vocab_parse_python(
        repo,
        "support/connection/agent_resources.py",
    )
    imports = _axis_vocab_import_aliases(resources_tree, "agent_adapter")
    allowed_alias = imports.get("ALLOWED_ADAPTER_REFS")
    write_capability_alias = imports.get("adapter_is_write_capable")
    if not allowed_alias:
        violations.append(
            "support/connection/agent_resources.py: must import ALLOWED_ADAPTER_REFS "
            "from .agent_adapter"
        )
    elif not _axis_vocab_name_used(resources_tree, allowed_alias):
        violations.append(
            "support/connection/agent_resources.py: imported ALLOWED_ADAPTER_REFS "
            f"alias {allowed_alias!r} is not read"
        )
    if not write_capability_alias:
        violations.append(
            "support/connection/agent_resources.py: must import adapter_is_write_capable "
            "from .agent_adapter"
        )
    elif not _axis_vocab_name_used(resources_tree, write_capability_alias):
        violations.append(
            "support/connection/agent_resources.py: imported adapter_is_write_capable "
            f"alias {write_capability_alias!r} is not read"
        )

    assigned = _axis_vocab_assigned_names(resources_tree)
    for forbidden_name in {"ALLOWED_ADAPTER_REFS", "_ALLOWED_ADAPTER_REFS"} & assigned:
        violations.append(
            "support/connection/agent_resources.py: must not assign duplicate adapter "
            f"ref object {forbidden_name}"
        )
    for node in ast.walk(resources_tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if all(adapter_ref in node.value for adapter_ref in _AXIS_VOCAB_EXPECTED_ADAPTER_REFS):
                violations.append(
                    "support/connection/agent_resources.py:"
                    f"{getattr(node, 'lineno', '?')}: must not redefine adapter refs as a string"
                )


def run_axis_vocab_drift(repo: Path) -> KernelResult:
    violations: list[str] = []
    _axis_vocab_check_link_sources(repo, violations)
    _axis_vocab_check_transition_author_prefix_consumers(repo, violations)
    _axis_vocab_check_docs(repo, violations)
    _axis_vocab_check_agent_adapter_refs(repo, violations)
    scanned = _axis_vocab_scan_exact_enum_redefinitions(repo, violations)
    if violations:
        detail = "\n".join(f"- {violation}" for violation in violations)
        raise ProfileError(f"kernel check axis_vocab_drift rejected evidence:\n{detail}")
    return KernelResult(
        check_id="axis_vocab_drift",
        inspected=scanned + 5,
        output=(
            "axis vocab drift passed: parsed Link Movement/transition sources, "
            "transition author-prefix consumers, AGENTS/current packet text, "
            "Agent adapter refs, and scanned "
            f"{scanned} active Python file(s) for competing full enum literals."
        ),
    )


@contextlib.contextmanager
def captured_output() -> Any:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        yield out, err


@contextlib.contextmanager
def patched_argv(argv: list[str]) -> Any:
    previous = sys.argv[:]
    sys.argv = argv
    try:
        yield
    finally:
        sys.argv = previous


@contextlib.contextmanager
def _without_report_grain_env() -> Any:
    previous = os.environ.pop("BRICK_REPORT_GRAIN", None)
    try:
        yield
    finally:
        if previous is not None:
            os.environ["BRICK_REPORT_GRAIN"] = previous


def call_main(check_id: str, module_name: str, argv: list[str] | None) -> KernelResult:
    module = importlib.import_module(module_name)
    with captured_output() as (out, err):
        if argv is None:
            with patched_argv([check_id]):
                code = int(module.main())
        elif check_id == "package_path_admission":
            with patched_argv([check_id] + argv):
                code = int(module.main())
        else:
            code = int(module.main(argv))
    output = (out.getvalue() + err.getvalue()).strip()
    if code != 0:
        raise ProfileError(f"kernel check {check_id} rejected evidence:\n{output}")
    return KernelResult(check_id=check_id, inspected=1, output=output)


def run_building_map_graph(repo: Path) -> KernelResult:
    module = importlib.import_module("support.checkers.check_building_map_graph")
    map_paths = sorted(repo.glob("project/*/buildings/*/work/building-map.json"))
    if not map_paths:
        return KernelResult(
            check_id="building_map_graph",
            inspected=0,
            output="building map graph skipped: no project/*/buildings/*/work/building-map.json maps present.",
        )
    all_violations: list[str] = []
    historical = 0
    for map_path in map_paths:
        _, violations, historical_map = module.check_one(map_path, fixture_mode=False)
        if historical_map:
            historical += 1
        all_violations.extend(violations)
    if all_violations:
        detail = "\n".join(f"- {violation}" for violation in all_violations)
        raise ProfileError(f"kernel check building_map_graph rejected evidence:\n{detail}")
    return KernelResult(
        check_id="building_map_graph",
        inspected=len(map_paths),
        output=(
            "building map graph passed: "
            f"{len(map_paths)} map(s) inspected, {historical} historical support map(s) preserved."
        ),
    )


def _ensure_import_identity(repo: Path) -> None:
    support_import_identity = str((repo / "support" / "import_identity").resolve())
    if support_import_identity not in sys.path:
        sys.path.insert(0, support_import_identity)


def _minimal_reporter_packet() -> Mapping[str, Any]:
    return {
        "report_id": "reporter-negative-probe-valid",
        "report_kind": "building_frontier",
        "building_id": "probe-building",
        "portfolio_id": "",
        "observed_board_state": "observed_running",
        "trigger_event_ref": "observation:probe",
        "current_brick_ref": "brick:probe",
        "current_work_kind": "work",
        "current_lane": "worker",
        "last_completed_step_ref": "",
        "frontier_ref": "project/brick-protocol/buildings/probe#frontier:closure_pending",
        "evidence_root_refs": ["project/brick-protocol/buildings/probe"],
        "evidence_refs_present": False,
        "checker_summary_ref": "support/checkers/profiles/reporter_notification_projection.yaml",
        "required_disposition_owner": "",
        "sink_refs": ["report-sink:local-inbox"],
        "generated_at": "2026-05-31T00:00:00+00:00",
        "source_truth": False,
        "not_proven": ["negative probe"],
        "proof_limits": ["negative probe support evidence only"],
    }


def run_building_plans_boundary_sweep(repo: Path) -> KernelResult:
    """Global building-plan boundary sweep (checker consolidation, pass-1).

    REHOME target: the per-profile ``building_plan_boundary`` pins (bar_v2,
    real_route_repair, provider_json_return_smoke, current_context_prune, ...)
    each pinned ONE frozen/live plan because no global walk existed. This sweep
    runs the SAME ``validate_building_plan_boundary`` over EVERY linear plan in
    brick/building_plans/, so those single-sourced per-plan structural guards
    survive as one general kernel-check and the per-profile pins can retire.

    Graph / stepless plans are skipped (they have their own validation path);
    their count is reported, never silently absorbed. A real boundary violation
    on any linear plan raises ProfileError -> --all RED.

    HARDENED (guard-before-retire): when the linear yaml-subset parser fails on a
    plan, fall back to PyYAML (yaml.safe_load). If PyYAML yields a dict with a
    non-empty ``steps`` list, the plan is a real LINEAR plan that the subset
    parser merely could not read, so it is validated via the SAME
    ``validate_building_plan_boundary`` (no silent skip). Only truly graph/stepless
    plans (no ``steps``) are skipped. A now-included plan that genuinely fails
    validation is surfaced (--all RED), never hidden. The number of PyYAML-
    recovered plans is reported separately.
    """
    plans_dir = repo / "brick" / "building_plans"
    if not plans_dir.is_dir():
        raise ProfileError("brick/building_plans must exist for the boundary sweep")
    import yaml
    from support.checkers.lib.yaml_subset import load_yaml_subset_file
    from support.checkers.lib.rule_runners import (
        validate_building_plan_boundary,
        _admitted_agent_object_refs,
    )

    admitted = _admitted_agent_object_refs(repo)
    validated = 0
    skipped = 0
    pyyaml_recovered = 0
    for path in sorted(plans_dir.glob("*.yaml")):
        rel = to_posix(path.relative_to(repo))
        try:
            plan = load_yaml_subset_file(repo, rel)
        except Exception:
            # Subset parser could not read it. Fall back to PyYAML: a real LINEAR
            # plan (dict with non-empty steps) must still be covered, not skipped.
            recovered = yaml.safe_load(path.read_text(encoding="utf-8"))
            recovered_steps = recovered.get("steps") if isinstance(recovered, Mapping) else None
            if not (isinstance(recovered_steps, list) and recovered_steps):
                skipped += 1  # graph / stepless plan -> own validation path
                continue
            # Real linear plan the subset parser missed; validate it (surface any
            # genuine failure rather than hiding it). This is STRUCTURAL validation
            # of historical plans, so retired write-adapter refs are tolerated here
            # (adapter activeness is enforced at run time, not in the boundary sweep).
            validate_building_plan_boundary(
                recovered, rel, admitted, repo, allow_retired_write_adapter_refs=True
            )
            validated += 1
            pyyaml_recovered += 1
            continue
        steps = plan.get("steps")
        if not (isinstance(steps, list) and steps):
            skipped += 1  # stepless / graph plan -> own validation path
            continue
        # Reuses the EXACT per-profile boundary validator; a violation raises
        # ProfileError, which fails the check (no swallowing of real failures).
        # Structural sweep over historical plans: retired write-adapter refs are
        # tolerated here (adapter activeness is enforced at run time, not here).
        validate_building_plan_boundary(
            plan, rel, admitted, repo, allow_retired_write_adapter_refs=True
        )
        validated += 1
    return KernelResult(
        check_id="building_plans_boundary_sweep",
        inspected=validated,
        output=(
            f"building plans boundary sweep passed: {validated} linear building "
            f"plan(s) validated (Brick owner_axis + plan_ref + non-empty steps + "
            f"declared-plan validation + per-step rows; {pyyaml_recovered} "
            f"PyYAML-recovered from subset-parse failure); {skipped} graph/stepless "
            f"plan(s) skipped (own validation path)."
        ),
    )


def _agent_instruction_packet_probe(repo: Path) -> Mapping[str, Any]:
    resources = importlib.import_module("brick_protocol.support.connection.agent_resources")
    packet = resources.render_agent_instruction_packet("dev", repo_root=repo)
    if not isinstance(packet, Mapping):
        raise ProfileError("agent instruction packet renderer did not return a mapping")
    required_keys = {
        "kind",
        "agent_object_ref",
        "role",
        "prompt_resources",
        "skill_resources",
        "hook_resources",
        "tool_policy_resources",
        "discipline_resources",
        "adapter_refs",
        "proof_limits",
        "not_proven",
    }
    missing = sorted(required_keys - set(packet))
    if missing:
        raise ProfileError(f"agent instruction packet missing required keys: {missing}")
    projection_keys = {"projection_target", "projection_status", "rendered_instruction_text"}
    leaked = sorted(projection_keys & set(packet))
    if leaked:
        raise ProfileError(f"agent instruction packet leaked projection-seed keys: {leaked}")
    if packet.get("kind") != "agent-instruction-packet":
        raise ProfileError("agent instruction packet kind drifted")
    if packet.get("agent_object_ref") != "agent-object:dev" or packet.get("role") != "dev":
        raise ProfileError("agent instruction packet did not preserve dev Agent Object identity")
    for key in (
        "prompt_resources",
        "skill_resources",
        "tool_policy_resources",
        "discipline_resources",
        "adapter_refs",
        "proof_limits",
        "not_proven",
    ):
        if not isinstance(packet.get(key), list) or not packet[key]:
            raise ProfileError(f"agent instruction packet {key} must be a non-empty list")
    hook_resources = packet.get("hook_resources")
    if not isinstance(hook_resources, Mapping) or "selected" not in hook_resources:
        raise ProfileError("agent instruction packet hook_resources must preserve selected hooks")
    return packet


def _agent_instruction_packet_for_role(repo: Path, role: str) -> Mapping[str, Any]:
    resources = importlib.import_module("brick_protocol.support.connection.agent_resources")
    packet = resources.render_agent_instruction_packet(role, repo_root=repo)
    expected_ref = f"agent-object:{role}"
    if not isinstance(packet, Mapping):
        raise ProfileError(f"{role} instruction packet renderer did not return a mapping")
    if packet.get("kind") != "agent-instruction-packet":
        raise ProfileError(f"{role} instruction packet kind drifted")
    if packet.get("agent_object_ref") != expected_ref or packet.get("role") != role:
        raise ProfileError(f"{role} instruction packet did not preserve Agent Object identity")
    return packet


def _agent_adapter_request_instruction_packet_probe(
    adapter: Any,
    instruction_packet: Mapping[str, Any],
    required_shape: str,
) -> object:
    request_fields = {field.name for field in fields(adapter.AgentAdapterRequest)}
    if "agent_instruction_packet" not in request_fields:
        raise ProfileError("AgentAdapterRequest must admit agent_instruction_packet")
    request = adapter.AgentAdapterRequest(
        building_id="agent-adapter-return-shape-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        required_return_shape=required_shape,
        agent_instruction_packet=instruction_packet,
    )
    observed = getattr(request, "agent_instruction_packet")
    if not isinstance(observed, Mapping):
        raise ProfileError("AgentAdapterRequest did not preserve agent_instruction_packet")
    for key in ("kind", "agent_object_ref", "role"):
        if observed.get(key) != instruction_packet.get(key):
            raise ProfileError(f"AgentAdapterRequest agent_instruction_packet lost {key}")
    return request


def _agent_effective_write_probe(
    repo: Path,
    adapter: Any,
    instruction_packet: Mapping[str, Any],
) -> int:
    write_scope = {
        "allowed_paths": ["support/connection/agent_adapter.py"],
        "forbidden_paths": [".git/**", ".env"],
        "commit_allowed": False,
        "push_allowed": False,
    }
    write_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if not adapter.agent_request_effective_write(write_request):
        raise ProfileError("codex-local write_scope request did not become effective_write")
    if adapter._codex_sandbox_for_request(write_request) != "workspace-write":
        raise ProfileError("effective_write request did not select workspace-write sandbox")
    write_prompt = json.loads(
        adapter._build_prompt(
            write_request,
            adapter._LOCAL_CLI_SPECS[adapter.ADAPTER_CODEX_LOCAL],
        )
    )
    if "You may edit files only inside the Brick-declared write_scope.allowed_paths." not in write_prompt.get(
        "rules",
        [],
    ):
        raise ProfileError("effective_write prompt did not expose scoped write rules")
    if write_prompt.get("agent_instruction_packet", {}).get("kind") != "agent-instruction-packet":
        raise ProfileError("effective_write prompt did not carry Agent instruction packet")

    non_dev_packet = dict(instruction_packet)
    non_dev_packet["agent_object_ref"] = "agent-object:cto-lead"
    non_dev_packet["role"] = "cto-lead"
    non_dev_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-non-dev-probe",
        agent_object_ref="agent-object:cto-lead",
        adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=non_dev_packet,
    )
    if not adapter.agent_request_effective_write(non_dev_request):
        raise ProfileError("effective_write was incorrectly tied to agent-object:dev")

    try:
        adapter.connect_agent_brain(
            non_dev_request,
            command_runner=lambda _args, _cwd, _timeout: (_ for _ in ()).throw(
                AssertionError("effective write reached command runner without observation")
            ),
            cwd=repo,
        )
    except ValueError as exc:
        if "effective write requires write observation before adapter execution" not in str(exc):
            raise ProfileError("effective_write without observation rejected with wrong reason") from exc
    else:
        raise ProfileError("effective_write reached adapter execution without observation marker")

    adapter._mark_effective_write_observation_path(non_dev_request, repo)
    try:
        adapter.connect_agent_brain(
            non_dev_request,
            command_runner=lambda _args, _cwd, _timeout: (_ for _ in ()).throw(
                AssertionError("effective write reached command runner after cwd mismatch")
            ),
            cwd=repo / "support",
        )
    except ValueError as exc:
        if "effective write observation cwd must match adapter execution cwd" not in str(exc):
            raise ProfileError("effective_write cwd mismatch rejected with wrong reason") from exc
    else:
        raise ProfileError("effective_write observation marker accepted mismatched cwd")

    try:
        adapter.AgentAdapterRequest(
            building_id="agent-effective-write-negative-no-policy",
            agent_object_ref="agent-object:dev",
            adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
            brick_instance_ref="brick-work",
            next_brick_instance_ref="brick-closure",
            write_scope=write_scope,
            agent_instruction_packet=instruction_packet,
        )
    except ValueError as exc:
        if "write_scope requires tool-policy:read-write-scoped" not in str(exc):
            raise ProfileError("write_scope without tool policy rejected with wrong reason") from exc
    else:
        raise ProfileError("write_scope without read-write tool policy was not rejected")

    try:
        adapter.AgentAdapterRequest(
            building_id="agent-effective-write-negative-unsupported-adapter",
            agent_object_ref="agent-object:dev",
            # gemini-local (read + review, NOT observed-write) is the non-observed-write
            # example now; claude-local is write-capable after the claude-write rehome.
            adapter_ref=adapter.ADAPTER_GEMINI_LOCAL,
            brick_instance_ref="brick-work",
            next_brick_instance_ref="brick-closure",
            tool_policy_refs=(adapter.READ_WRITE_TOOL_POLICY_REF,),
            write_scope=write_scope,
            agent_instruction_packet=instruction_packet,
        )
    except ValueError as exc:
        if "supports observed workspace write" not in str(exc):
            raise ProfileError("unsupported observed-write adapter rejected with wrong reason") from exc
    else:
        raise ProfileError("unsupported adapter with write_scope was not rejected")

    for retired_adapter_ref in _AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS:
        try:
            adapter.AgentAdapterRequest(
                building_id="agent-effective-write-negative-retired-adapter",
                agent_object_ref="agent-object:dev",
                adapter_ref=retired_adapter_ref,
                brick_instance_ref="brick-work",
                next_brick_instance_ref="brick-closure",
                tool_policy_refs=(adapter.READ_WRITE_TOOL_POLICY_REF,),
                write_scope=write_scope,
                agent_instruction_packet=instruction_packet,
            )
        except ValueError as exc:
            message = str(exc)
            if "retired" not in message and "not admitted" not in message:
                raise ProfileError(
                    f"retired write adapter {retired_adapter_ref} rejected with wrong reason"
                ) from exc
        else:
            raise ProfileError(f"retired write adapter {retired_adapter_ref} was not rejected")

    bad_packet = dict(instruction_packet)
    bad_packet["agent_object_ref"] = "agent-object:qa"
    try:
        adapter.AgentAdapterRequest(
            building_id="agent-instruction-packet-negative-mismatch",
            agent_object_ref="agent-object:dev",
            adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
            brick_instance_ref="brick-work",
            next_brick_instance_ref="brick-closure",
            agent_instruction_packet=bad_packet,
        )
    except ValueError as exc:
        if "agent_instruction_packet.agent_object_ref must match" not in str(exc):
            raise ProfileError("instruction packet mismatch rejected with wrong reason") from exc
    else:
        raise ProfileError("mismatched instruction packet was not rejected")

    # claude-local is now write-capable (same observed-write 3-gate as codex).
    # A claude write request must select scoped write CLI knobs; a claude read
    # request must keep the EXACT prior read-only shape. Live in-scope/out-of-scope
    # claude writes remain NOT-PROVEN (no OS sandbox); these assert the knobs only.
    claude_write_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-claude-positive",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if not adapter.agent_request_effective_write(claude_write_request):
        raise ProfileError("claude-local write_scope request did not become effective_write")
    knobs = adapter._claude_cli_invocation(claude_write_request)
    if knobs["permission_mode"] != "acceptEdits":
        raise ProfileError("claude effective_write did not select acceptEdits")
    write_tools = (
        [t.strip() for t in knobs["tools"].split(",") if t.strip()]
        if knobs["tools"]
        else []
    )
    if set(write_tools) != {"Read", "Grep", "Glob", "Edit", "Write", "Bash"}:
        raise ProfileError(
            "claude effective_write did not expose the exact comma-separated scoped "
            f"write tool set; observed {knobs['tools']!r}"
        )
    if knobs["system_prompt"] != adapter._CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT:
        raise ProfileError("claude effective_write did not use the scoped-write system prompt")

    claude_read_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-claude-read",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        agent_instruction_packet=instruction_packet,
    )
    if adapter.agent_request_effective_write(claude_read_request):
        raise ProfileError("claude read request became effective_write")
    knobs_read = adapter._claude_cli_invocation(claude_read_request)
    if knobs_read["permission_mode"] != "plan":
        raise ProfileError("claude read request did not stay in plan mode")
    if knobs_read["tools"] != "":
        raise ProfileError("claude read request exposed tools")
    if knobs_read["system_prompt"] != adapter._CLAUDE_NONINTERACTIVE_SYSTEM_PROMPT:
        raise ProfileError("claude read request did not use the read-only system prompt")

    return 11


def _agent_read_tier_probe(repo: Path, adapter: Any) -> int:
    qa_packet = _agent_instruction_packet_for_role(repo, "qa")
    cto_packet = _agent_instruction_packet_for_role(repo, "cto-lead")
    dev_packet = _agent_instruction_packet_for_role(repo, "dev")
    expected_known_policies = {
        adapter.LEADER_COORDINATION_TOOL_POLICY_REF,
        adapter.READ_WRITE_TOOL_POLICY_REF,
        adapter.REVIEWER_READONLY_TOOL_POLICY_REF,
    }
    if set(adapter.KNOWN_TOOL_POLICY_REFS) != expected_known_policies:
        raise ProfileError(
            "read-tier known tool-policy vocabulary drifted; observed "
            f"{sorted(adapter.KNOWN_TOOL_POLICY_REFS)!r}"
        )

    reviewer_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-reviewer-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter.REVIEWER_READONLY_TOOL_POLICY_REF,),
        required_return_shape="observed_evidence, evidence_used, not_proven",
        agent_instruction_packet=qa_packet,
    )
    if not adapter.agent_request_read_tier(reviewer_request):
        raise ProfileError("reviewer-readonly non-write codex request did not enter read tier")
    reviewer_prompt = json.loads(
        adapter._build_prompt(
            reviewer_request,
            adapter._LOCAL_CLI_SPECS[adapter.ADAPTER_CODEX_LOCAL],
        )
    )
    reviewer_rules = list(reviewer_prompt.get("rules", []))
    if "Do not use tools or hooks." in reviewer_rules:
        raise ProfileError("read-tier codex reviewer prompt still rendered the none-tier no-tools rule")
    expected_read_rule = (
        "You may use read-only repository inspection tools only: read files, inspect diffs, "
        "search with grep/glob, and run checker commands."
    )
    if expected_read_rule not in reviewer_rules:
        raise ProfileError("read-tier codex reviewer prompt did not expose repository inspection rule")
    forbidden_write_permission_phrases = (
        "You may edit files only inside",
        "write_scope.allowed_paths",
        "Read, Grep, Glob, Edit, Write, Bash",
        "Bash",
    )
    for phrase in forbidden_write_permission_phrases:
        if any(phrase in rule for rule in reviewer_rules):
            raise ProfileError(
                "read-tier codex reviewer prompt leaked write-tier permission phrase "
                f"{phrase!r}"
            )

    unknown_policy_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-unknown-policy-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter.REVIEWER_READONLY_TOOL_POLICY_REF, "tool-policy:unknown"),
        required_return_shape="observed_evidence, evidence_used, not_proven",
        agent_instruction_packet=qa_packet,
    )
    if adapter.agent_request_read_tier(unknown_policy_request):
        raise ProfileError("reviewer-readonly plus unknown tool policy entered read tier")
    unknown_policy_prompt = json.loads(
        adapter._build_prompt(
            unknown_policy_request,
            adapter._LOCAL_CLI_SPECS[adapter.ADAPTER_CODEX_LOCAL],
        )
    )
    if "Do not use tools or hooks." not in unknown_policy_prompt.get("rules", []):
        raise ProfileError("unknown tool policy request did not fail closed to none tier")
    if expected_read_rule in unknown_policy_prompt.get("rules", []):
        raise ProfileError("unknown tool policy request still rendered read-tier inspection rule")

    leader_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-leader-probe",
        agent_object_ref="agent-object:cto-lead",
        adapter_ref=adapter.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-design",
        next_brick_instance_ref="brick-work",
        tool_policy_refs=(
            adapter.LEADER_COORDINATION_TOOL_POLICY_REF,
            adapter.READ_WRITE_TOOL_POLICY_REF,
        ),
        required_return_shape="observed_evidence, evidence_refs, not_proven",
        agent_instruction_packet=cto_packet,
    )
    if not adapter.agent_request_read_tier(leader_request):
        raise ProfileError("leader-coordination non-write claude request did not enter read tier")
    leader_knobs = adapter._claude_cli_invocation(leader_request)
    if leader_knobs["permission_mode"] != "plan":
        raise ProfileError("read-tier claude request must stay in plan permission mode")
    leader_tools = [tool.strip() for tool in leader_knobs["tools"].split(",") if tool.strip()]
    if leader_tools != ["Read", "Grep", "Glob"]:
        raise ProfileError(f"read-tier claude tools must be Read/Grep/Glob only, got {leader_tools}")
    if "Edit" in leader_tools or "Write" in leader_tools or "Bash" in leader_tools:
        raise ProfileError("read-tier claude request leaked Edit/Write/Bash tools")
    if leader_knobs["system_prompt"] != adapter._CLAUDE_READ_ONLY_SYSTEM_PROMPT:
        raise ProfileError("read-tier claude request did not use the read-only system prompt")

    dev_nonwrite_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-dev-none-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-readonly-worker",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter.READ_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=dev_packet,
    )
    if adapter.agent_request_read_tier(dev_nonwrite_request):
        raise ProfileError("read-write-scoped alone must not enter the read tier without write_scope")
    dev_prompt = json.loads(
        adapter._build_prompt(
            dev_nonwrite_request,
            adapter._LOCAL_CLI_SPECS[adapter.ADAPTER_CODEX_LOCAL],
        )
    )
    if "Do not use tools or hooks." not in dev_prompt.get("rules", []):
        raise ProfileError("ambiguous non-write worker request did not fail closed to none tier")

    gemini_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-gemini-limit-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter.REVIEWER_READONLY_TOOL_POLICY_REF,),
        agent_instruction_packet=qa_packet,
    )
    if adapter.agent_request_read_tier(gemini_request):
        raise ProfileError("gemini-local must not enter read tier until read-only tools are expressible")
    gemini_prompt = json.loads(
        adapter._build_prompt(
            gemini_request,
            adapter._LOCAL_CLI_SPECS[adapter.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_rules = list(gemini_prompt.get("rules", []))
    if "Do not use tools or hooks." not in gemini_rules:
        raise ProfileError("gemini-local documented limit must stay in none-tier no-tools prompt")
    if not any("adapter:gemini-local remains in the none tier" in rule for rule in gemini_rules):
        raise ProfileError("gemini-local read-tier limit was not documented in the prompt")

    gemini_cli_capture: dict[str, Any] = {}

    def _gemini_no_live_runner(args: Sequence[str], cwd: Path, timeout_seconds: int) -> Any:
        del cwd, timeout_seconds
        call = tuple(str(arg) for arg in args)
        gemini_cli_capture["args"] = call
        if "--admin-policy" in call:
            policy_path = Path(call[call.index("--admin-policy") + 1])
            gemini_cli_capture["policy_text"] = policy_path.read_text(encoding="utf-8")
        return adapter.LocalCliCompleted(call, 0, '{"response": "mocked"}', "")

    adapter._invoke_local_cli(
        adapter._LOCAL_CLI_SPECS[adapter.ADAPTER_GEMINI_LOCAL],
        gemini_request,
        "prompt",
        cwd=repo,
        timeout_seconds=5,
        command_runner=_gemini_no_live_runner,
    )
    gemini_args = tuple(gemini_cli_capture.get("args", ()))
    if "--approval-mode" not in gemini_args:
        raise ProfileError("gemini-local CLI projection dropped --approval-mode")
    if gemini_args[gemini_args.index("--approval-mode") + 1] != "plan":
        raise ProfileError(f"gemini-local CLI projection stopped fail-closing to plan mode: {gemini_args!r}")
    if "--yolo" in gemini_args or "auto_edit" in gemini_args or "yolo" in gemini_args:
        raise ProfileError(f"gemini-local CLI projection exposed write/auto-approve mode: {gemini_args!r}")
    if "--admin-policy" not in gemini_args:
        raise ProfileError("gemini-local CLI projection dropped no-tools admin policy")
    policy_text = str(gemini_cli_capture.get("policy_text", ""))
    for required_deny in ("run_shell_command", "write_file", "replace", 'decision = "deny"'):
        if required_deny not in policy_text:
            raise ProfileError(
                "gemini-local no-tools admin policy stopped denying write/command "
                f"tooling token {required_deny!r}"
            )

    return 14


def _artifact_grounding_probe(repo: Path) -> int:
    from brick_protocol.support.connection.agent_adapter import (
        ADAPTER_LOCAL,
        AgentAdapterRequest,
        AgentAdapterResult,
    )
    from brick_protocol.link.movement import make_movement_fact
    from brick_protocol.link.transition import make_transition_fact
    from brick_protocol.support.operator.contracts import BuildingRunSupportResult
    from brick_protocol.support.operator.gate_sequence import (
        gate_sequence_decision_to_record,
        run_gate_sequence_policy,
    )
    from brick_protocol.support.operator.plan_validation import (
        _artifact_grounding_required_return_fields,
    )
    from brick_protocol.support.operator.run import (
        complete_agent_run_from_prepared,
        prepare_agent_run_from_step_rows,
    )
    from brick_protocol.support.recording.claims_link import (
        _gate_fact_claim_body,
        _gate_receipt_claim_body,
    )
    from brick_protocol.support.recording.building_map import BuildingMapWriteResult
    from brick_protocol.support.recording.capture import BuildingLifecycleWriteResult

    returned_field_prefix = "BrickComparisonFact.comparison_evidence.returned_field."

    def gate_returned_fields(required_public_facts: Sequence[str]) -> tuple[str, ...]:
        return tuple(
            item.removeprefix(returned_field_prefix)
            for item in required_public_facts
            if item.startswith(returned_field_prefix)
        )

    def assert_gate_fields_match_helper(
        *,
        kind: str,
        label: str,
        required_public_facts: Sequence[str],
        missing_required_facts: Sequence[str],
        expected_required_fields: Sequence[str],
        expected_missing_fields: Sequence[str],
    ) -> None:
        observed_required = gate_returned_fields(required_public_facts)
        observed_missing = gate_returned_fields(missing_required_facts)
        if observed_required != tuple(expected_required_fields):
            raise ProfileError(
                f"artifact grounding probe {kind} {label}: gate required fields "
                f"drifted from shared helper: observed {observed_required!r}, "
                f"expected {tuple(expected_required_fields)!r}"
            )
        if observed_missing != tuple(expected_missing_fields):
            raise ProfileError(
                f"artifact grounding probe {kind} {label}: gate missing fields "
                f"drifted from shared helper: observed {observed_missing!r}, "
                f"expected {tuple(expected_missing_fields)!r}"
            )

    def assert_recorded_claim_grounding_refs(
        *,
        kind: str,
        label: str,
        claim_body: Mapping[str, Any],
        grounding_field: str,
        expected_action: str,
    ) -> None:
        required_public_facts = tuple(claim_body.get("required_public_facts", ()))
        missing_required_facts = tuple(claim_body.get("missing_required_facts", ()))
        if not grounding_field:
            leaked = tuple(
                fact
                for fact in (*required_public_facts, *missing_required_facts)
                if fact.endswith(".repository_artifact_ref")
            )
            if leaked:
                raise ProfileError(
                    f"artifact grounding probe {kind} {label}: non-review claim "
                    f"recorded repository artifact ref(s) {leaked!r}"
                )
            return
        expected_public_fact = f"{returned_field_prefix}{grounding_field}"
        if expected_action == "hold":
            if expected_public_fact in required_public_facts:
                raise ProfileError(
                    f"artifact grounding probe {kind} {label}: missing repository "
                    f"artifact selector was recorded as resolvable required fact "
                    f"{expected_public_fact}"
                )
            if expected_public_fact not in missing_required_facts:
                raise ProfileError(
                    f"artifact grounding probe {kind} {label}: missing repository "
                    f"artifact selector was not recorded as demanded missing fact "
                    f"{expected_public_fact}"
                )
            return
        if expected_public_fact not in required_public_facts:
            raise ProfileError(
                f"artifact grounding probe {kind} {label}: grounded repository "
                f"artifact selector was not recorded as required fact {expected_public_fact}"
            )
        if expected_public_fact in missing_required_facts:
            raise ProfileError(
                f"artifact grounding probe {kind} {label}: grounded repository "
                f"artifact selector was also recorded missing {expected_public_fact}"
            )

    def gate_sequence_decision(
        *,
        step: Mapping[str, Any],
        prepared: Any,
        completion: Any,
        returned_value: Any,
    ) -> Any:
        adapter_request = AgentAdapterRequest(
            building_id=prepared.building_id,
            agent_object_ref=prepared.agent_object.object_ref,
            adapter_ref=ADAPTER_LOCAL,
            brick_instance_ref=prepared.brick_instance_ref,
            next_brick_instance_ref=prepared.next_brick_instance_ref,
            tool_policy_refs=prepared.agent_object.tool_policy_refs,
        )
        adapter_result = AgentAdapterResult(
            request=adapter_request,
            returned_value=returned_value,
        )
        step_result = BuildingRunSupportResult(
            building_id=prepared.building_id,
            preparation=prepared,
            adapter_result=adapter_result,
            completion=completion,
            lifecycle_write=BuildingLifecycleWriteResult(root=Path(), written_files=()),
            building_map_write=BuildingMapWriteResult(
                root=Path(),
                path=Path(),
                written_files=(),
            ),
            written_files=(),
            capture_event_types=(),
            building_map_packet=completion.building_map_packet,
            proof_limits=(),
            not_proven=(),
        )
        return run_gate_sequence_policy(
            step=step,
            step_result=step_result,
            source_brick_ref=prepared.brick_instance_ref,
            target_brick_ref=prepared.next_brick_instance_ref,
        )

    def assert_completion_and_gate_sequence(
        *,
        kind: str,
        grounding_field: str,
        expected_action: str,
        prepared: Any,
        completion: Any,
        returned_value: Any,
        step: Mapping[str, Any],
    ) -> None:
        expected_required_fields = _artifact_grounding_required_return_fields(
            completion.brick_comparison.required_return_shape_evidence,
            completion.brick_comparison.required_return_fields(),
        )
        expected_missing_fields = tuple(
            field
            for field in completion.brick_comparison.missing_return_fields()
            if field in expected_required_fields
        )
        movement_gate = completion.crossing_record.movement_gate_fact
        if movement_gate is None:
            raise ProfileError(f"artifact grounding probe {kind}: missing movement gate")
        assert_gate_fields_match_helper(
            kind=kind,
            label="movement-gate",
            required_public_facts=movement_gate.required_public_facts,
            missing_required_facts=movement_gate.missing_required_facts,
            expected_required_fields=expected_required_fields,
            expected_missing_fields=expected_missing_fields,
        )
        assert_recorded_claim_grounding_refs(
            kind=kind,
            label="movement-claim",
            claim_body=_gate_fact_claim_body(movement_gate),
            grounding_field=grounding_field,
            expected_action=expected_action,
        )
        decision = gate_sequence_decision(
            step=step,
            prepared=prepared,
            completion=completion,
            returned_value=returned_value,
        )
        if decision.action != expected_action:
            raise ProfileError(
                f"artifact grounding probe {kind}: gate sequence action "
                f"{decision.action!r}, expected {expected_action!r}"
            )
        record = gate_sequence_decision_to_record(decision)
        if not isinstance(record, Mapping):
            raise ProfileError(f"artifact grounding probe {kind}: missing gate sequence record")
        gate_results = record.get("gate_results")
        if not isinstance(gate_results, list) or len(gate_results) != 1:
            raise ProfileError(
                f"artifact grounding probe {kind}: expected one gate sequence result, "
                f"observed {gate_results!r}"
            )
        gate_record = gate_results[0]
        if not isinstance(gate_record, Mapping):
            raise ProfileError(
                f"artifact grounding probe {kind}: gate sequence result is not a mapping"
            )
        gate_ref, gate_fact = decision.gate_results[0]
        assert_gate_fields_match_helper(
            kind=kind,
            label="gate-sequence-record",
            required_public_facts=tuple(gate_record.get("required_public_facts", ())),
            missing_required_facts=tuple(gate_record.get("missing_required_facts", ())),
            expected_required_fields=expected_required_fields,
            expected_missing_fields=expected_missing_fields,
        )
        assert_recorded_claim_grounding_refs(
            kind=kind,
            label="gate-receipt-claim",
            claim_body=_gate_receipt_claim_body(gate_ref, 1, gate_fact),
            grounding_field=grounding_field,
            expected_action=expected_action,
        )
        if grounding_field:
            expected_public_fact = f"{returned_field_prefix}{grounding_field}"
            required_public_facts = tuple(gate_record.get("required_public_facts", ()))
            missing_required_facts = tuple(gate_record.get("missing_required_facts", ()))
            if expected_action == "hold" and expected_public_fact not in missing_required_facts:
                raise ProfileError(
                    f"artifact grounding probe {kind}: missing artifact did not demand "
                    f"{expected_public_fact}"
                )
            if expected_action == "forward" and (
                expected_public_fact not in required_public_facts
                or expected_public_fact in missing_required_facts
            ):
                raise ProfileError(
                    f"artifact grounding probe {kind}: grounded artifact record did not "
                    f"carry resolved {expected_public_fact}"
                )
        elif any(
            field.endswith(".repository_artifact_ref")
            for field in (*expected_required_fields, *expected_missing_fields)
        ):
            raise ProfileError(
                f"artifact grounding probe {kind}: non-review shape demanded "
                "repository artifact grounding"
            )

    cases = (
        (
            "code-attack-qa",
            "agent-object:qa",
            "observed_evidence, attacked_work, checked_sources, regression_risks, "
            "negative_probe_observations, failing_or_missing_probes, boundary_violations, "
            "evidence_used, not_proven",
            {
                "observed_evidence": ["packet-only review observed"],
                "attacked_work": ["prior packet"],
                "checked_sources": ["support-packet:prior-output"],
                "regression_risks": [],
                "negative_probe_observations": [],
                "failing_or_missing_probes": [],
                "boundary_violations": [],
                "evidence_used": ["support-packet:prior-output"],
                "not_proven": [],
            },
            {
                "observed_evidence": ["repository artifact read"],
                "attacked_work": ["prior packet"],
                "checked_sources": ["support/connection/agent_adapter.py:1087"],
                "regression_risks": [],
                "negative_probe_observations": [],
                "failing_or_missing_probes": [],
                "boundary_violations": [],
                "evidence_used": ["support/connection/agent_adapter.py:1087"],
                "not_proven": [],
            },
            "evidence_used.repository_artifact_ref",
        ),
        (
            "design",
            "agent-object:design-lead",
            "observed_evidence, design_summary, relevant_current_structure, proposed_changes, "
            "unchanged_surfaces, axis_responsibility, invariants, edge_cases, "
            "checker_or_verifier_plan, candidate_file_changes, evidence_refs, not_proven",
            {
                "observed_evidence": ["packet-only design observed"],
                "design_summary": "probe design",
                "relevant_current_structure": ["support packet only"],
                "proposed_changes": [],
                "unchanged_surfaces": [],
                "axis_responsibility": [],
                "invariants": [],
                "edge_cases": [],
                "checker_or_verifier_plan": [],
                "candidate_file_changes": [],
                "evidence_refs": ["support-packet:design-intake"],
                "not_proven": [],
            },
            {
                "observed_evidence": ["repository artifact read"],
                "design_summary": "probe design",
                "relevant_current_structure": ["brick/templates/bricks/design/brick.md:20"],
                "proposed_changes": [],
                "unchanged_surfaces": [],
                "axis_responsibility": [],
                "invariants": [],
                "edge_cases": [],
                "checker_or_verifier_plan": [],
                "candidate_file_changes": [],
                "evidence_refs": ["brick/templates/bricks/design/brick.md:20"],
                "not_proven": [],
            },
            "evidence_refs.repository_artifact_ref",
        ),
        (
            "non-review-evidence-used",
            "agent-object:dev",
            "observed_evidence, evidence_used, not_proven",
            {
                "observed_evidence": ["ordinary evidence observed"],
                "evidence_used": ["support-packet:ordinary"],
                "not_proven": [],
            },
            {
                "observed_evidence": ["ordinary evidence observed"],
                "evidence_used": ["support/connection/agent_adapter.py:1087"],
                "not_proven": [],
            },
            "",
        ),
    )

    inspected = 0
    for kind, agent_ref, required_shape, missing_return, grounded_return, grounding_field in cases:
        step_ref = f"artifact-grounding-{kind}"
        rows = [
            {
                "axis": "Brick",
                "row_ref": f"brick-row:artifact-grounding-{kind}",
                "brick_instance_ref": f"brick-artifact-grounding-{kind}",
                "brick_work_ref": f"work:artifact-grounding-{kind}",
                "work_statement": f"{kind} Brick artifact grounding probe",
                "comparison_rule": "Repo artifact grounding is required for review/design evidence.",
                "required_return_shape": required_shape,
            },
            {
                "axis": "Agent",
                "row_ref": f"agent-row:artifact-grounding-{kind}",
                "agent_object_ref": agent_ref,
            },
            {
                "axis": "Link",
                "row_ref": f"link-row:artifact-grounding-{kind}",
                "movement": "forward",
                "target_ref": f"brick-artifact-grounding-{kind}-closure",
                "declared_gate_refs": ["link-gate:default-transition"],
                "gate_sequence_policy": [
                    {
                        "gate_ref": "link-gate:default-transition",
                        "on_missing_required_facts": {
                            "action": "HOLD",
                            "required_disposition_owner": "caller-or-coo",
                            "pending_target_basis": "target_brick",
                        },
                        "on_sufficient": {"action": "forward"},
                    }
                ],
            },
        ]
        step = {"step_ref": step_ref, "rows": rows}
        fixture = {
            "building_id": step_ref,
            "step_rows": {
                "step_ref": step_ref,
                "rows": rows,
            },
        }
        prepared = prepare_agent_run_from_step_rows(fixture)
        link_fact = make_movement_fact(
            "forward",
            reason="artifact grounding checker probe",
            handoff_target_fact=f"brick:{prepared.next_brick_instance_ref}",
        )
        transition_fact = make_transition_fact(
            "forward",
            target_fact=f"brick:{prepared.next_brick_instance_ref}",
            handoff_reference=f"checker:artifact-grounding:{kind}",
        )
        missing_completion = complete_agent_run_from_prepared(
            prepared,
            returned_value=missing_return,
            link_fact=link_fact,
            transition_fact=transition_fact,
        )
        if grounding_field not in missing_completion.brick_comparison.missing_return_fields():
            if grounding_field:
                raise ProfileError(
                    f"artifact grounding probe {kind}: packet-only return did not mark "
                    f"{grounding_field} missing"
                )
        expected_missing_action = "hold" if grounding_field else "forward"
        assert_completion_and_gate_sequence(
            kind=f"{kind}:missing-return",
            grounding_field=grounding_field,
            expected_action=expected_missing_action,
            prepared=prepared,
            completion=missing_completion,
            returned_value=missing_return,
            step=step,
        )
        movement_gate = missing_completion.crossing_record.movement_gate_fact
        expected_missing_fact = (
            "BrickComparisonFact.comparison_evidence.returned_field."
            f"{grounding_field}"
        )
        if grounding_field and (
            movement_gate is None or expected_missing_fact not in movement_gate.missing_required_facts
        ):
            raise ProfileError(
                f"artifact grounding probe {kind}: Link gate did not observe missing "
                f"required fact {expected_missing_fact}"
            )

        grounded_completion = complete_agent_run_from_prepared(
            prepared,
            returned_value=grounded_return,
            link_fact=link_fact,
            transition_fact=transition_fact,
        )
        if grounding_field and grounding_field in grounded_completion.brick_comparison.missing_return_fields():
            raise ProfileError(
                f"artifact grounding probe {kind}: repository artifact ref still "
                f"marked {grounding_field} missing"
            )
        assert_completion_and_gate_sequence(
            kind=f"{kind}:grounded-return",
            grounding_field=grounding_field,
            expected_action="forward",
            prepared=prepared,
            completion=grounded_completion,
            returned_value=grounded_return,
            step=step,
        )
        grounded_gate = grounded_completion.crossing_record.movement_gate_fact
        if grounded_gate is None or grounded_gate.missing_required_facts:
            raise ProfileError(
                f"artifact grounding probe {kind}: grounded return still produced "
                f"missing_required_facts {getattr(grounded_gate, 'missing_required_facts', None)!r}"
            )
        inspected += 2
    return inspected


def run_agent_adapter_return_shape(repo: Path) -> KernelResult:
    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    comparison = importlib.import_module("brick_protocol.brick.comparison")
    instruction_packet = _agent_instruction_packet_probe(repo)

    required_shape = (
        "made_changes, observed_evidence, blocked_or_missing_evidence, "
        "not_proven, remaining_delta"
    )
    output_text = json.dumps(
        {
            "no_changes_reason": "probe made no file changes",
            "observed_evidence": ["probe observed adapter return extraction"],
            "blocked_or_missing_evidence": [],
            "not_proven": ["semantic correctness"],
            "remaining_delta": [],
        },
        sort_keys=True,
    )
    extracted = adapter._extract_required_return_fields(output_text, required_shape)
    if extracted.get("no_changes_reason") != "probe made no file changes":
        raise ProfileError("agent adapter did not preserve made_changes waiver field")

    brick_comparison = comparison.BrickComparisonFact.from_returned_value(
        work_reference="work:agent-adapter-return-shape-probe",
        required_fields=adapter._required_return_shape_fields(required_shape),
        returned_value=extracted,
        comparison_rule="Probe made_changes waiver preservation only.",
        required_return_shape_evidence=required_shape,
    )
    if "made_changes via no_changes_reason" not in brick_comparison.waived_return_fields():
        raise ProfileError("Brick comparison did not observe no_changes_reason waiver")

    request = _agent_adapter_request_instruction_packet_probe(
        adapter,
        instruction_packet,
        required_shape,
    )
    prompt = json.loads(
        adapter._build_prompt(
            request,
            adapter._LOCAL_CLI_SPECS[adapter.ADAPTER_CODEX_LOCAL],
        )
    )
    if prompt.get("return_field_waivers") != ["no_changes_reason"]:
        raise ProfileError("adapter prompt did not expose no_changes_reason waiver")
    if prompt.get("agent_instruction_packet", {}).get("kind") != "agent-instruction-packet":
        raise ProfileError("adapter prompt did not carry Agent instruction packet")
    effective_write_inspected = _agent_effective_write_probe(repo, adapter, instruction_packet)
    read_tier_inspected = _agent_read_tier_probe(repo, adapter)
    artifact_grounding_inspected = _artifact_grounding_probe(repo)

    # REHOME (checker consolidation): assert the FULL return-field vocabulary the
    # retiring provider_json_return_smoke profile single-sourced (several tokens
    # were pinned only there). The Agent return label/JSON field constants live in
    # support/connection/agent_adapter.py; the forbidden return keys live in
    # agent/return_fact.py and are re-exported into the adapter. An absent guard
    # fires nothing, so verify the constants directly instead of leaving the
    # vocabulary text-pinned in one retiring profile.
    return_fact = importlib.import_module("brick_protocol.agent.return_fact")
    _EXPECTED_RETURN_LABEL_FIELDS = (
        "blocked_or_missing_evidence",
        "made_changes",
        "not_proven",
        "observed_evidence",
        "open_questions",
        "remaining_delta",
        "review_needed",
        "transition_concern_evidence",
    )
    _EXPECTED_RETURN_JSON_FIELDS = ("transition_concern_evidence",)
    _EXPECTED_RETURNED_FORBIDDEN_KEYS = ("movement_choice", "route_target", "target_ref")
    missing_label_fields = sorted(
        set(_EXPECTED_RETURN_LABEL_FIELDS) - set(adapter._RETURN_LABEL_FIELDS)
    )
    if missing_label_fields:
        raise ProfileError(
            "agent adapter _RETURN_LABEL_FIELDS missing return label field(s): "
            + ", ".join(missing_label_fields)
        )
    missing_json_fields = sorted(
        set(_EXPECTED_RETURN_JSON_FIELDS) - set(adapter._RETURN_JSON_FIELDS)
    )
    if missing_json_fields:
        raise ProfileError(
            "agent adapter _RETURN_JSON_FIELDS missing JSON return field(s): "
            + ", ".join(missing_json_fields)
        )
    missing_forbidden_keys = sorted(
        set(_EXPECTED_RETURNED_FORBIDDEN_KEYS) - set(return_fact.RETURNED_FORBIDDEN_KEYS)
    )
    if missing_forbidden_keys:
        raise ProfileError(
            "return_fact RETURNED_FORBIDDEN_KEYS missing forbidden return key(s): "
            + ", ".join(missing_forbidden_keys)
        )
    if set(adapter._RETURN_FORBIDDEN_KEYS) != set(return_fact.RETURNED_FORBIDDEN_KEYS):
        raise ProfileError(
            "agent adapter _RETURN_FORBIDDEN_KEYS drifted from "
            "return_fact RETURNED_FORBIDDEN_KEYS"
        )

    return KernelResult(
        check_id="agent_adapter_return_shape",
        inspected=6
        + effective_write_inspected
        + read_tier_inspected
        + artifact_grounding_inspected,
        output=(
            "agent adapter return shape passed: no_changes_reason waiver "
            "extraction, Brick comparison waiver, prompt projection, runtime "
            "Agent instruction packet rendering, and AgentAdapterRequest "
            "injection plus effective_write, read-tier rendering, tier-safety, "
            "and artifact-grounding probes inspected."
        ),
    )


_PROVIDER_PREFLIGHT_REQUIRED_KEYS = (
    "adapter_ref",
    "cli",
    "installed",
    "authed",
    "ok",
    "message_ko",
)
_PROVIDER_PREFLIGHT_AUTHED_LITERALS = ("yes", "no", "unknown")


def _provider_preflight_assert_shape(label: str, status: Any) -> None:
    if not isinstance(status, Mapping):
        raise ProfileError(
            f"provider_preflight: {label} must return a status mapping, got {type(status).__name__}"
        )
    missing = [key for key in _PROVIDER_PREFLIGHT_REQUIRED_KEYS if key not in status]
    if missing:
        raise ProfileError(
            f"provider_preflight: {label} status missing required key(s): {', '.join(missing)}"
        )
    if not isinstance(status["installed"], bool):
        raise ProfileError(f"provider_preflight: {label} 'installed' must be a bool")
    if not isinstance(status["ok"], bool):
        raise ProfileError(f"provider_preflight: {label} 'ok' must be a bool")
    if status["authed"] not in _PROVIDER_PREFLIGHT_AUTHED_LITERALS:
        raise ProfileError(
            f"provider_preflight: {label} 'authed' must be one of "
            f"{_PROVIDER_PREFLIGHT_AUTHED_LITERALS}, got {status['authed']!r}"
        )
    message = status["message_ko"]
    if not isinstance(message, str) or not message.strip():
        raise ProfileError(f"provider_preflight: {label} 'message_ko' must be non-empty text")


def run_provider_preflight(repo: Path) -> KernelResult:
    """ONBOARDING-PROVIDER-PREFLIGHT-0 execution checker.

    Imports preflight_provider from the Agent Adapter and asserts it (a) returns a
    status dict with the required keys for an ACTIVE adapter and adapter:local,
    (b) NEVER raises -- including for a deliberately bogus/retired adapter ref,
    where it must return ok False with a friendly message instead of raising, and
    (c) always carries a non-empty message_ko. This is the no-raise guard: if
    preflight_provider EVER raises (e.g. on a missing CLI), this checker goes RED.
    """

    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")

    inspected = 0

    # (a) Active local CLI adapter + in-process adapter:local must each return a
    #     well-shaped status. preflight_provider must NOT raise for either.
    for label in (adapter.ADAPTER_CODEX_LOCAL, adapter.ADAPTER_LOCAL):
        try:
            status = adapter.preflight_provider(label)
        except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
            raise ProfileError(
                f"provider_preflight: preflight_provider({label!r}) raised {type(exc).__name__}: {exc}"
            ) from exc
        _provider_preflight_assert_shape(label, status)
        if status["adapter_ref"] != label:
            raise ProfileError(
                f"provider_preflight: {label} status adapter_ref must echo the input"
            )
        inspected += 1

    # adapter:local has no CLI: it must report ready.
    local_status = adapter.preflight_provider(adapter.ADAPTER_LOCAL)
    if not (local_status["installed"] and local_status["ok"] and local_status["authed"] == "yes"):
        raise ProfileError(
            "provider_preflight: adapter:local must report installed/authed/ok ready"
        )

    # (b) Deliberately bogus + retired refs must return ok False WITHOUT raising.
    for bogus_ref in (
        "adapter:bogus-not-a-real-provider",
        "adapter:codex-write-local",  # retired write adapter
        "",
    ):
        try:
            status = adapter.preflight_provider(bogus_ref)
        except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
            raise ProfileError(
                "provider_preflight: preflight_provider must not raise for a bogus/retired "
                f"ref {bogus_ref!r}; raised {type(exc).__name__}: {exc}"
            ) from exc
        _provider_preflight_assert_shape(f"bogus={bogus_ref!r}", status)
        if status["ok"] is not False:
            raise ProfileError(
                f"provider_preflight: bogus/retired ref {bogus_ref!r} must return ok False"
            )
        inspected += 1

    return KernelResult(
        check_id="provider_preflight",
        inspected=inspected,
        output=(
            "provider preflight passed: preflight_provider returns a well-shaped "
            "status dict for active + in-process adapters, reports adapter:local "
            "ready, and returns ok False (never raises) for bogus/retired refs "
            f"({inspected} ref(s) inspected)."
        ),
    )


def _gemini_api_classify_error_kind(exc: Exception) -> str:
    """Read-only mirror of run.py._adapter_error_kind (we cannot edit run.py).

    The B2-hardened hold path classifies adapter exceptions by type/message. We
    replicate the mapping here ONLY to assert (in-process) that a gemini-api
    no-key error flows the SAME clean typed adapter-error path, never a crash.
    Kept structurally identical to support/operator/run.py:_adapter_error_kind.
    """
    message = str(exc).lower()
    if isinstance(exc, FileNotFoundError):
        return "local_cli_missing"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "local_cli_timeout"
    if "non-zero" in message or "returned non-zero" in message:
        return "local_cli_nonzero"
    if "returned payload" in message or "forbidden returned" in message:
        return "adapter_return_shape_rejected"
    return "adapter_exception"


def run_design_ai_text_seams(repo: Path) -> KernelResult:
    """DESIGN-AI-TEXT-SEAM-0616 checker for Claude/Codex prompt -> text wrappers.

    FIREs, IN-PROCESS with mock command_runners only:
      (a) normal text returns byte-matching raw text and emits the declared CLI
          shapes.
      (b) command_runner FileNotFoundError propagates cleanly.
      (c) command_runner TimeoutExpired propagates unchanged.
      (d) blank/whitespace output raises clean ValueError.
      (e) secret-looking output is rejected by the adapter secret scrub.

    Mutation-RED: removing any raise/parse/scrub behavior above turns this check
    red without invoking a live provider CLI.
    """
    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    inspected = 0

    claude_prompt = "Design prompt\nwith two lines"
    claude_captured: dict[str, Any] = {}

    def _claude_ok_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        claude_captured["args"] = tuple(args)
        claude_captured["cwd"] = cwd
        claude_captured["timeout"] = timeout
        return adapter.LocalCliCompleted(
            args=tuple(args),
            return_code=0,
            stdout="CLAUDE raw text\n",
            stderr="",
        )

    claude_text = adapter.invoke_claude_text(
        claude_prompt,
        model_name="claude-test-model",
        timeout_seconds=41,
        command_runner=_claude_ok_runner,
    )
    if claude_text != "CLAUDE raw text\n":
        raise ProfileError("design_ai_text_seams: claude raw text was not returned byte-matching")
    expected_claude_args = (
        "claude",
        "-p",
        claude_prompt,
        "--output-format",
        "text",
        "--model",
        "claude-test-model",
    )
    if claude_captured.get("args") != expected_claude_args:
        raise ProfileError(
            f"design_ai_text_seams: claude args drifted: {claude_captured.get('args')!r}"
        )
    if claude_captured.get("cwd") != repo or claude_captured.get("timeout") != 41:
        raise ProfileError("design_ai_text_seams: claude cwd/timeout was not carried")
    inspected += 1

    codex_prompt = "Compose a short graph proposal."
    codex_captured: dict[str, Any] = {}

    def _codex_ok_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        codex_captured["args"] = tuple(args)
        codex_captured["cwd"] = cwd
        codex_captured["timeout"] = timeout
        output_path = Path(args[args.index("--output-last-message") + 1])
        codex_captured["output_path"] = output_path
        output_path.write_text("CODEX raw text\n", encoding="utf-8")
        return adapter.LocalCliCompleted(
            args=tuple(args),
            return_code=0,
            stdout="ignored stdout\n",
            stderr="",
        )

    codex_text = adapter.invoke_codex_text(
        codex_prompt,
        model_name="codex-test-model",
        timeout_seconds=53,
        command_runner=_codex_ok_runner,
    )
    if codex_text != "CODEX raw text\n":
        raise ProfileError("design_ai_text_seams: codex temp-file text was not returned")
    codex_args = codex_captured.get("args")
    if not isinstance(codex_args, tuple):
        raise ProfileError("design_ai_text_seams: codex args were not captured")
    if codex_args[:4] != ("codex", "exec", "--sandbox", "read-only"):
        raise ProfileError(f"design_ai_text_seams: codex command prefix drifted: {codex_args!r}")
    if ("-m", "codex-test-model") != codex_args[4:6]:
        raise ProfileError("design_ai_text_seams: codex model arg was not carried")
    if "--output-last-message" not in codex_args or codex_args[-1] != codex_prompt:
        raise ProfileError("design_ai_text_seams: codex output-last-message/prompt shape drifted")
    output_path = codex_captured.get("output_path")
    if not isinstance(output_path, Path):
        raise ProfileError("design_ai_text_seams: codex output path was not captured")
    if output_path.exists():
        raise ProfileError("design_ai_text_seams: codex temp output file was not cleaned up")
    if codex_captured.get("cwd") != repo or codex_captured.get("timeout") != 53:
        raise ProfileError("design_ai_text_seams: codex cwd/timeout was not carried")
    inspected += 1

    def _expect_error(thunk: Callable[[], Any], error_type: type[BaseException], label: str) -> None:
        try:
            thunk()
        except error_type:
            return
        except Exception as exc:  # noqa: BLE001
            raise ProfileError(
                f"design_ai_text_seams: {label} raised {type(exc).__name__}, "
                f"expected {error_type.__name__}"
            ) from exc
        raise ProfileError(
            f"design_ai_text_seams: {label} did not raise {error_type.__name__} "
            "(mutation-RED guard)"
        )

    def _missing_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        raise FileNotFoundError(f"{Path(str(args[0])).name} missing")

    _expect_error(
        lambda: adapter.invoke_claude_text("p", command_runner=_missing_runner),
        FileNotFoundError,
        "claude missing executable",
    )
    _expect_error(
        lambda: adapter.invoke_codex_text("p", command_runner=_missing_runner),
        FileNotFoundError,
        "codex missing executable",
    )
    inspected += 1

    def _timeout_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        raise subprocess.TimeoutExpired(cmd=tuple(args), timeout=timeout)

    _expect_error(
        lambda: adapter.invoke_claude_text("p", timeout_seconds=7, command_runner=_timeout_runner),
        subprocess.TimeoutExpired,
        "claude timeout propagation",
    )
    _expect_error(
        lambda: adapter.invoke_codex_text("p", timeout_seconds=11, command_runner=_timeout_runner),
        subprocess.TimeoutExpired,
        "codex timeout propagation",
    )
    inspected += 1

    def _claude_blank_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        return adapter.LocalCliCompleted(args=tuple(args), return_code=0, stdout=" \n\t", stderr="")

    def _codex_blank_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        Path(args[args.index("--output-last-message") + 1]).write_text(" \n\t", encoding="utf-8")
        return adapter.LocalCliCompleted(args=tuple(args), return_code=0, stdout="", stderr="")

    _expect_error(
        lambda: adapter.invoke_claude_text("p", command_runner=_claude_blank_runner),
        ValueError,
        "claude blank output",
    )
    _expect_error(
        lambda: adapter.invoke_codex_text("p", command_runner=_codex_blank_runner),
        ValueError,
        "codex blank output",
    )
    inspected += 1

    fake_secret = "sk-ABCDEFGHIJKLMNOP"

    def _claude_secret_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        return adapter.LocalCliCompleted(args=tuple(args), return_code=0, stdout=fake_secret, stderr="")

    def _codex_secret_runner(args: Sequence[str], cwd: Path, timeout: int) -> Any:
        Path(args[args.index("--output-last-message") + 1]).write_text(fake_secret, encoding="utf-8")
        return adapter.LocalCliCompleted(args=tuple(args), return_code=0, stdout="", stderr="")

    _expect_error(
        lambda: adapter.invoke_claude_text("p", command_runner=_claude_secret_runner),
        ValueError,
        "claude secret output",
    )
    _expect_error(
        lambda: adapter.invoke_codex_text("p", command_runner=_codex_secret_runner),
        ValueError,
        "codex secret output",
    )
    inspected += 1

    return KernelResult(
        check_id="design_ai_text_seams",
        inspected=inspected,
        output=(
            "design-AI text seams passed: claude/codex prompt-to-text wrappers "
            "returned mocked raw text, preserved CLI shape/cwd/timeout, propagated "
            "FileNotFoundError and TimeoutExpired, rejected blank output, rejected "
            "secret-looking output, and called NO live provider CLI "
            f"({inspected} group(s) inspected)."
        ),
    )


def run_gemini_api_adapter(repo: Path) -> KernelResult:
    """B6 gemini-api adapter execution checker (ADDITIVE, no new profile).

    FIREs, IN-PROCESS:
      (a) adapter:gemini-api is admitted with READ+REVIEW capability (same brain
          class as gemini-local), is NOT write-capable, and is DELIBERATELY not a
          _LOCAL_CLI_SPECS member (no CLI / no subprocess identity).
      (b) no-key (env unset): connect_agent_brain raises a CLEAN typed
          FileNotFoundError that maps to 'local_cli_missing' (the B2 hold shape),
          NOT a crash, and spawns NO subprocess (subprocess.Popen trip-wire).
      (c) mocked request: the constructed HTTP request targets the documented
          v1beta generateContent endpoint, carries the x-goog-api-key header (key
          NOT in the URL), and the body is {"contents":[{"parts":[{"text":...}]}]};
          a mocked candidates[0].content.parts[0].text is parsed into the
          CLI-mirror returned_value shape.
      (d) HTTP-error / timeout / malformed response all become CLEAN ValueErrors
          (flow the hold path), never a raw urllib/KeyError crash.

    Mutation-RED: if the no-key path stops raising the clean typed error (e.g.
    raises raw / returns), assertion (b) REDs.
    """
    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    gemini_api = adapter.ADAPTER_GEMINI_API
    inspected = 0

    # (a) Admission + capability + not-a-CLI.
    if gemini_api not in adapter.ALLOWED_ADAPTER_REFS:
        raise ProfileError("gemini_api_adapter: adapter:gemini-api is not admitted")
    caps = set(adapter.adapter_capabilities(gemini_api))
    if caps != {adapter.ADAPTER_CAPABILITY_READ, adapter.ADAPTER_CAPABILITY_REVIEW}:
        raise ProfileError(
            f"gemini_api_adapter: gemini-api capabilities must be READ+REVIEW, got {sorted(caps)}"
        )
    if adapter.adapter_is_write_capable(gemini_api):
        raise ProfileError("gemini_api_adapter: gemini-api must NOT be write-capable")
    if gemini_api in adapter._LOCAL_CLI_SPECS:
        raise ProfileError(
            "gemini_api_adapter: gemini-api must NOT be a _LOCAL_CLI_SPECS (CLI) member"
        )
    if gemini_api in adapter.local_cli_adapter_refs():
        raise ProfileError("gemini_api_adapter: gemini-api leaked into local_cli_adapter_refs()")
    inspected += 1

    def _make_request():
        return adapter.AgentAdapterRequest(
            building_id="gemini-api-adapter-probe",
            agent_object_ref="agent-object:inspector",
            adapter_ref=gemini_api,
            brick_instance_ref="brick-review",
            next_brick_instance_ref="brick-closure",
            selected_model_ref=adapter.MODEL_REF_GEMINI_FLASH,
            tool_policy_refs=(adapter.REVIEWER_READONLY_TOOL_POLICY_REF,),
            work_statement="Return support evidence only.",
        )

    # (b) no-key: clean typed adapter-error + NO subprocess.
    saved_env = {
        name: os.environ.pop(name, None) for name in adapter._GEMINI_API_KEY_ENV_VARS
    }
    spawn_count = {"n": 0}
    original_popen = subprocess.Popen

    class _TripPopen(original_popen):  # type: ignore[misc, valid-type]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            spawn_count["n"] += 1
            raise AssertionError("gemini_api_adapter: no-key path spawned a subprocess")

    subprocess.Popen = _TripPopen  # type: ignore[assignment]
    try:
        try:
            adapter.connect_agent_brain(_make_request())
        except FileNotFoundError as exc:
            kind = _gemini_api_classify_error_kind(exc)
            if kind != "local_cli_missing":
                raise ProfileError(
                    f"gemini_api_adapter: no-key error classified as {kind!r}, expected local_cli_missing"
                )
        except Exception as exc:  # noqa: BLE001
            raise ProfileError(
                f"gemini_api_adapter: no-key path raised {type(exc).__name__} "
                f"({exc}); expected a clean FileNotFoundError"
            ) from exc
        else:
            raise ProfileError(
                "gemini_api_adapter: no-key path did not raise -- a clean typed "
                "adapter-error is required (mutation-RED guard)"
            )
        if spawn_count["n"] != 0:
            raise ProfileError(
                f"gemini_api_adapter: no-key path spawned {spawn_count['n']} subprocess(es)"
            )
    finally:
        subprocess.Popen = original_popen  # type: ignore[assignment]
        for name, value in saved_env.items():
            if value is not None:
                os.environ[name] = value
    inspected += 1

    # (c) mocked request: capture URL/header/body, parse mocked response.
    captured: dict[str, Any] = {}

    def _fake_urlopen(http_request: Any, timeout_seconds: int) -> bytes:
        captured["url"] = http_request.full_url
        captured["method"] = http_request.get_method()
        captured["headers"] = {k.lower(): v for k, v in http_request.header_items()}
        captured["timeout"] = timeout_seconds
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        return json.dumps(
            {"candidates": [{"content": {"parts": [{"text": "PROBE gemini evidence"}]}}]}
        ).encode("utf-8")

    fake_key = "PROBE-FAKE-KEY-NOT-A-REAL-CREDENTIAL"
    os.environ["GEMINI_API_KEY"] = fake_key
    try:
        returned, _proof_limits, _not_proven = adapter._invoke_gemini_api(
            _make_request(),
            timeout_seconds=37,
            urlopen=_fake_urlopen,
        )
    finally:
        os.environ.pop("GEMINI_API_KEY", None)
        for name, value in saved_env.items():
            if value is not None:
                os.environ[name] = value

    expected_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash:generateContent"
    )
    if captured.get("url") != expected_url:
        raise ProfileError(
            f"gemini_api_adapter: endpoint URL drifted: {captured.get('url')!r} != {expected_url!r}"
        )
    if captured.get("method") != "POST":
        raise ProfileError("gemini_api_adapter: HTTP method must be POST")
    if captured.get("headers", {}).get("x-goog-api-key") != fake_key:
        raise ProfileError("gemini_api_adapter: x-goog-api-key header missing or wrong")
    if fake_key in captured.get("url", ""):
        raise ProfileError("gemini_api_adapter: API key leaked into the URL")
    body = captured.get("body")
    if not (
        isinstance(body, Mapping)
        and isinstance(body.get("contents"), list)
        and len(body["contents"]) == 1
        and isinstance(body["contents"][0].get("parts"), list)
        and len(body["contents"][0]["parts"]) == 1
        and isinstance(body["contents"][0]["parts"][0].get("text"), str)
        and body["contents"][0]["parts"][0]["text"]
    ):
        raise ProfileError(
            "gemini_api_adapter: request body is not {'contents':[{'parts':[{'text':...}]}]}"
        )
    if captured.get("timeout") != 37:
        raise ProfileError("gemini_api_adapter: adapter timeout was not passed to the HTTP call")
    if returned.get("adapter_ref") != gemini_api:
        raise ProfileError("gemini_api_adapter: returned adapter_ref drifted")
    if returned.get("output_excerpt") != "PROBE gemini evidence":
        raise ProfileError("gemini_api_adapter: mocked response text not parsed into returned shape")
    if returned.get("api_model_name") != "gemini-2.5-flash":
        raise ProfileError("gemini_api_adapter: resolved api_model_name drifted")
    # CLI-mirror shape: same engine-facing keys the CLI path returns.
    for key in ("returned_summary", "adapter_ref", "brain_surface_ref", "evidence_refs",
                "proof_limits", "not_proven"):
        if key not in returned:
            raise ProfileError(f"gemini_api_adapter: returned value missing CLI-mirror key {key!r}")
    inspected += 1

    # (d) HTTP-error / timeout / malformed -> clean ValueError (no crash).
    request_obj = adapter._build_gemini_api_request(fake_key, "gemini-2.5-flash", "p")

    import urllib.error as _urllib_error
    import socket as _socket

    def _expect_value_error(thunk: Callable[[], Any], label: str) -> None:
        try:
            thunk()
        except ValueError:
            return
        except Exception as exc:  # noqa: BLE001
            raise ProfileError(
                f"gemini_api_adapter: {label} raised {type(exc).__name__}, expected clean ValueError"
            ) from exc
        raise ProfileError(f"gemini_api_adapter: {label} did not raise (expected clean ValueError)")

    saved_urlopen = adapter.urllib.request.urlopen

    def _http_error(_req: Any, timeout: Any = None) -> Any:
        raise _urllib_error.HTTPError(request_obj.full_url, 500, "err", {}, None)

    def _timeout(_req: Any, timeout: Any = None) -> Any:
        raise _socket.timeout("timed out")

    adapter.urllib.request.urlopen = _http_error
    try:
        _expect_value_error(
            lambda: adapter._gemini_api_urlopen(request_obj, timeout_seconds=5), "HTTP 500"
        )
    finally:
        adapter.urllib.request.urlopen = saved_urlopen
    adapter.urllib.request.urlopen = _timeout
    try:
        _expect_value_error(
            lambda: adapter._gemini_api_urlopen(request_obj, timeout_seconds=5), "timeout"
        )
    finally:
        adapter.urllib.request.urlopen = saved_urlopen
    _expect_value_error(
        lambda: adapter._parse_gemini_api_response(b'{"candidates": []}'), "malformed response"
    )
    inspected += 1

    return KernelResult(
        check_id="gemini_api_adapter",
        inspected=inspected,
        output=(
            "gemini-api adapter passed: admitted READ+REVIEW (not write-capable, "
            "not a CLI spec); no-key -> clean local_cli_missing typed error with "
            "NO subprocess; mocked request hits the v1beta generateContent endpoint "
            "with the x-goog-api-key header (key not in URL) and the documented "
            "contents/parts/text body, parsed into the CLI-mirror returned shape; "
            "HTTP-error/timeout/malformed all become clean ValueErrors "
            f"({inspected} group(s) inspected)."
        ),
    )


_ONBOARD_SMOKE_REQUIRED_KEYS = (
    "host",
    "preflight",
    "connect_hint",
    "example_result",
    "handoff_message_ko",
    "ok",
)


def run_onboard_smoke(repo: Path) -> KernelResult:
    """ONBOARDING-WIZARD-0 execution checker.

    Drives the real ``support/operator/onboard.run_onboard`` END-TO-END on
    ``adapter:local`` with a TEMP ``output_root`` (never the repo) and asserts:
      (a) it returns the structured dict {host, preflight, connect_hint,
          example_result, handoff_message_ko, ok},
      (b) ok is True and the bundled example actually ran (ran True) with a
          building_id + landed evidence under the temp root,
      (c) it NEVER raises, including for a bogus host (which must return ok False
          with a friendly message, not a stack-trace),
      (d) the bundled example plan is a valid linear Building plan (the
          building_plans_boundary_sweep already covers it; here we assert the
          plan file exists and the run produced evidence).
    If run_onboard EVER raises, this kernel check goes RED and --all EXITs
    non-zero. This is the no-raise guard for the guided onboarding experience.
    """

    _ensure_import_identity(repo)
    onboard = importlib.import_module("brick_protocol.support.operator.onboard")

    # The bundled example plan must exist (boundary sweep validates its shape).
    plan_path = repo / onboard.EXAMPLE_PLAN_REL
    if not plan_path.is_file():
        raise ProfileError(
            f"onboard_smoke: bundled example plan missing: {onboard.EXAMPLE_PLAN_REL}"
        )

    inspected = 0

    # (a)+(b)+(d) Happy path on adapter:local with a TEMP output_root (NOT repo).
    with tempfile.TemporaryDirectory(prefix="bp-onboard-smoke-") as tmp:
        tmp_root = Path(tmp)
        try:
            result = onboard.run_onboard(
                "codex",
                repo_root=repo,
                run_example=True,
                output_root=tmp_root,
            )
        except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
            raise ProfileError(
                "onboard_smoke: run_onboard('codex', run_example=True) raised "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        _onboard_smoke_assert_shape("codex", result)

        if result["ok"] is not True:
            raise ProfileError(
                "onboard_smoke: adapter:local example must make ok True; got "
                f"{result['ok']!r} (example_result={result.get('example_result')})"
            )

        example = result["example_result"]
        if not isinstance(example, Mapping):
            raise ProfileError("onboard_smoke: example_result must be a mapping")
        if example.get("ran") is not True:
            raise ProfileError("onboard_smoke: bundled example did not run (ran != True)")
        building_id = example.get("building_id")
        if not isinstance(building_id, str) or not building_id.strip():
            raise ProfileError("onboard_smoke: example_result missing a building_id")
        evidence_root = example.get("evidence_root")
        if not isinstance(evidence_root, str) or not evidence_root.strip():
            raise ProfileError("onboard_smoke: example_result missing evidence_root")
        evidence_path = Path(evidence_root)
        if not evidence_path.is_dir():
            raise ProfileError(
                f"onboard_smoke: example evidence root is not a directory: {evidence_root}"
            )
        # Evidence MUST land under the temp root, never the repo working tree.
        try:
            evidence_path.resolve().relative_to(tmp_root.resolve())
        except ValueError as exc:
            raise ProfileError(
                "onboard_smoke: example evidence must land under the temp output_root, "
                f"not {evidence_root}"
            ) from exc
        if int(example.get("written_file_count") or 0) <= 0:
            raise ProfileError("onboard_smoke: example produced no written evidence files")
        inspected += 1

    # (c) A bogus host must return ok False WITHOUT raising. Skip the example so
    #     this stays cheap; the never-raise guard is what matters here.
    try:
        bogus = onboard.run_onboard(
            "definitely-not-a-host",
            repo_root=repo,
            run_example=False,
        )
    except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
        raise ProfileError(
            "onboard_smoke: run_onboard must not raise for a bogus host; raised "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    _onboard_smoke_assert_shape("bogus", bogus)
    if bogus["ok"] is not False:
        raise ProfileError("onboard_smoke: bogus host must return ok False")
    inspected += 1

    return KernelResult(
        check_id="onboard_smoke",
        inspected=inspected,
        output=(
            "onboard smoke passed: run_onboard drives the bundled adapter:local "
            "example end-to-end to a TEMP output_root, returns the structured "
            "{preflight, connect_hint, example_result, handoff_message_ko, ok} "
            "dict with ok True + a building_id + landed evidence, and never raises "
            f"(bogus host returns ok False) ({inspected} flow(s) inspected)."
        ),
    )


def _onboard_smoke_assert_shape(label: str, result: Any) -> None:
    if not isinstance(result, Mapping):
        raise ProfileError(
            f"onboard_smoke: {label} must return a dict, got {type(result).__name__}"
        )
    missing = [key for key in _ONBOARD_SMOKE_REQUIRED_KEYS if key not in result]
    if missing:
        raise ProfileError(
            f"onboard_smoke: {label} result missing required key(s): {', '.join(missing)}"
        )
    if not isinstance(result["ok"], bool):
        raise ProfileError(f"onboard_smoke: {label} 'ok' must be a bool")
    handoff = result["handoff_message_ko"]
    if not isinstance(handoff, str) or not handoff.strip():
        raise ProfileError(
            f"onboard_smoke: {label} 'handoff_message_ko' must be non-empty text"
        )
    preflight = result["preflight"]
    if not isinstance(preflight, Mapping) or not str(preflight.get("message_ko") or "").strip():
        raise ProfileError(
            f"onboard_smoke: {label} preflight must carry a non-empty message_ko"
        )


_INSTALL_SCRIPT_REL = "support/onboarding/install.sh"
_RELEASE_EXPORT_REL = "support/onboarding/release_export.sh"
_RELEASE_EXPORT_REQUIRED_EXCLUSIONS = (
    "project",
    "brick_protocol.egg-info",
)

# Secret-shaped patterns the one-line installer must NEVER carry inline. The
# script relies on the teammate's OWN gh/git login as the access grant; nothing
# here may embed a literal credential. These are substring/structure probes, not
# a cryptographic secret scanner.
_INSTALL_SCRIPT_SECRET_PATTERNS = (
    "ghp_",
    "github_pat_",
    "gho_",
    "token=",
    "Bearer ",
    "BRICK_TOKEN=",
    "AWS_SECRET",
    "PRIVATE KEY",
)


def run_install_script_lint(repo: Path) -> KernelResult:
    """ONBOARDING-INSTALL-SCRIPT-0 structural / safety lint.

    Reads ``support/onboarding/install.sh`` (the one-line installer) and asserts
    its STRUCTURE and SAFETY shape:
      (a) the file exists and is non-empty;
      (b) it sets ``set -eu`` (fail-fast, fail-on-unset);
      (c) ALL logic is wrapped in a ``main()`` function AND ``main`` is invoked
          as the LAST non-empty line (anti-truncation: a cut-off download leaves
          main undefined / never called, so a partial file cannot run a
          half-baked install);
      (d) it contains NO ``http://`` (HTTPS only);
      (e) it contains NO ``/Users/`` literal (no hardcoded user-home path);
      (f) it contains NO obvious inline secret pattern (the script relies on the
          teammate's own gh/git login, never an embedded token);
      (g) it references the onboard wizard entry as the next step.

    LIMIT (stated in the output and honestly here): this is a STRUCTURE/SAFETY
    lint. It does NOT prove the script actually installs on a real fresh machine
    (network clone, uv sync, provider auth, etc.) -- that proof is manual /
    Phase-4 infra, not gated here. A violation makes main() return non-zero and
    raises ProfileError, so --all EXITs non-zero.
    """

    script_path = repo / _INSTALL_SCRIPT_REL
    if not script_path.is_file():
        raise ProfileError(
            f"install_script_lint: installer missing: {_INSTALL_SCRIPT_REL}"
        )

    text = script_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ProfileError(
            f"install_script_lint: {_INSTALL_SCRIPT_REL} is empty"
        )

    violations: list[str] = []

    # (b) fail-fast options.
    if "set -eu" not in text:
        violations.append("missing 'set -eu' (fail-fast / fail-on-unset)")

    # (c) main() defined AND invoked as the LAST non-empty line.
    if "main(" not in text:
        violations.append("no main( function defined")
    non_empty_lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    last_line = non_empty_lines[-1] if non_empty_lines else ""
    if last_line.strip() != 'main "$@"':
        violations.append(
            "last non-empty line must be exactly 'main \"$@\"' (anti-truncation), "
            f"got: {last_line.strip()!r}"
        )

    # (d) HTTPS only -- no plaintext http:// scheme anywhere.
    if "http://" in text:
        violations.append("contains 'http://' (HTTPS only)")

    # (e) no hardcoded user-home literal.
    if "/Users/" in text:
        violations.append("contains a hardcoded '/Users/' path (no user-home literal)")

    # (f) no inline secret patterns.
    for pattern in _INSTALL_SCRIPT_SECRET_PATTERNS:
        if pattern in text:
            violations.append(f"contains a secret-shaped pattern: {pattern!r}")

    # (g) references the onboard wizard entry (the next-step pointer).
    if "support.operator.onboard" not in text:
        violations.append(
            "does not reference the onboard wizard entry "
            "(brick_protocol.support.operator.onboard)"
        )

    if violations:
        raise ProfileError(
            "install_script_lint: "
            f"{_INSTALL_SCRIPT_REL} failed structural/safety lint: "
            + "; ".join(violations)
        )

    return KernelResult(
        check_id="install_script_lint",
        inspected=1,
        output=(
            "install script lint passed: "
            f"{_INSTALL_SCRIPT_REL} sets 'set -eu', wraps all logic in main() "
            "invoked as 'main \"$@\"' on the last non-empty line (anti-truncation), "
            "carries no http:// (HTTPS only), no /Users/ literal, no inline "
            "secret pattern, and references the onboard wizard entry. "
            "PROOF LIMIT: this is a STRUCTURE/SAFETY lint only -- it does NOT "
            "prove the script actually installs on a real fresh machine (network "
            "clone, uv sync, provider auth); that is manual / Phase-4 infra, not "
            "gated here."
        ),
    )


def _release_export_exclusions(text: str) -> set[str]:
    match = re.search(r"EXCLUDE_PATHS\s*=\s*\((?P<body>.*?)\)", text, re.DOTALL)
    if not match:
        return set()
    return set(re.findall(r"""["']([^"']+)["']""", match.group("body")))


def _release_export_exclusion_violations(text: str) -> list[str]:
    exclusions = _release_export_exclusions(text)
    violations: list[str] = []
    if not exclusions:
        violations.append("missing literal EXCLUDE_PATHS tuple")
    for required in _RELEASE_EXPORT_REQUIRED_EXCLUSIONS:
        if required not in exclusions:
            violations.append(f"missing required exclusion: {required}/")
    if "git remote add origin git@github.com:{OWNER}/BRICK.git" not in text:
        violations.append("missing placeholder remote follow-up command")
    if "git tag v0.1.0" not in text:
        violations.append("missing v0.1.0 tag follow-up command")
    if "git push -u origin main" not in text or "git push origin v0.1.0" not in text:
        violations.append("missing manual push follow-up commands")
    return violations


def _release_export_exclusion_fire_probe(text: str) -> int:
    mutated = text.replace('    "project",\n', "", 1)
    violations = _release_export_exclusion_violations(mutated)
    if not any("missing required exclusion: project/" in violation for violation in violations):
        raise ProfileError(
            "release_export_exclusion FIRE probe did NOT fire when project/ "
            "was removed from the export exclusion list"
        )
    return 1


def run_release_export_exclusion(repo: Path) -> KernelResult:
    """Pin the clean-repo export verb's local-evidence exclusion list.

    The release export is allowed to prepare a public tree, but it must not ship
    the local project evidence vessel or Python build metadata. This check only
    inspects the support verb's literal exclusion contract and publication
    follow-up shape. It does not push, tag, run the export, judge release
    quality, or prove future operator behavior.
    """

    script_path = repo / _RELEASE_EXPORT_REL
    if not script_path.is_file():
        raise ProfileError(
            f"release_export_exclusion: export verb missing: {_RELEASE_EXPORT_REL}"
        )
    text = script_path.read_text(encoding="utf-8")
    violations = _release_export_exclusion_violations(text)
    if violations:
        raise ProfileError(
            "release_export_exclusion rejected export verb:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )
    inspected = 1 + _release_export_exclusion_fire_probe(text)
    return KernelResult(
        check_id="release_export_exclusion",
        inspected=inspected,
        output=(
            "release export exclusion pin passed: support/onboarding/release_export.sh "
            "carries literal exclusions for project/ and brick_protocol.egg-info/, "
            "prints manual remote/tag/push follow-up commands with {OWNER}, and "
            "the temp mutation removing project/ fired RED. PROOF LIMIT: this is "
            "support evidence only; it does not run publication, choose Movement, "
            "or judge release quality."
        ),
    )


_NO_SMITH_RESIDUE_SURFACES = (
    "README.md",
    "support/docs/spec",
    "agent/prompts",
)


def _no_smith_residue_text_paths(repo: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for surface in _NO_SMITH_RESIDUE_SURFACES:
        root = repo / surface
        if not root.exists():
            continue
        if root.is_file():
            paths.append(root)
            continue
        paths.extend(
            path
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.suffix in {".md", ".txt"}
        )
    return tuple(paths)


def _no_smith_residue_allowed_org_line(rel: str, line: str) -> bool:
    return (
        rel == "README.md"
        and "insightwavesmith/BRICK" in line
        and ("현재 동작 예" in line or "working example" in line.lower())
    )


def _collect_no_smith_residue_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    inspected = 0
    for path in _no_smith_residue_text_paths(repo):
        rel = to_posix(path.relative_to(repo))
        inspected += 1
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "/Users/smith" in line:
                violations.append(f"{rel}:{lineno}: hardcoded Smith user-home path")
            if "insightwavesmith" in line.lower() and not _no_smith_residue_allowed_org_line(rel, line):
                violations.append(f"{rel}:{lineno}: hardcoded Smith GitHub org")
    return violations, inspected


def _copy_no_smith_residue_surfaces(repo: Path, probe_repo: Path) -> None:
    for surface in _NO_SMITH_RESIDUE_SURFACES:
        source = repo / surface
        target = probe_repo / surface
        if not source.exists():
            continue
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        else:
            shutil.copytree(source, target)


def _no_smith_residue_fire_probe(repo: Path) -> int:
    probes = (
        (
            "user-home",
            Path("support/docs/spec/README.md"),
            "synthetic probe path: /Users/smith/projects/BRICK\n",
            "hardcoded Smith user-home path",
        ),
        (
            "org",
            Path("agent/prompts/coo.md"),
            "synthetic probe clone: gh repo clone insightwavesmith/BRICK ~/BRICK\n",
            "hardcoded Smith GitHub org",
        ),
    )
    inspected = 0
    for label, target_rel, line, expected in probes:
        inspected += 1
        with tempfile.TemporaryDirectory(prefix="bp-no-smith-residue-fire-") as tmp:
            probe_repo = Path(tmp)
            _copy_no_smith_residue_surfaces(repo, probe_repo)
            target = probe_repo / target_rel
            if not target.is_file():
                raise ProfileError(
                    f"product_no_smith_residue FIRE probe target missing for {label}: "
                    f"{to_posix(target_rel)}"
                )
            with target.open("a", encoding="utf-8") as handle:
                handle.write(line)
            violations, _ = _collect_no_smith_residue_violations(probe_repo)
            if not any(expected in violation for violation in violations):
                raise ProfileError(
                    "product_no_smith_residue FIRE probe did NOT fire for "
                    f"{label}: {line.strip()!r}"
                )
    return inspected


def run_product_no_smith_residue(repo: Path) -> KernelResult:
    """Product-surface lint for Smith local residue.

    Scans the shipped newcomer-facing surfaces named by ONBOARDING-LEGACY-SCRUB:
    root README, support/docs/spec, and agent/prompts. The only admitted
    ``insightwavesmith/BRICK`` occurrence there is the root README's explicit
    working-example note next to the parameterized ``{OWNER}/BRICK`` command.
    """

    violations, inspected = _collect_no_smith_residue_violations(repo)
    if violations:
        raise ProfileError(
            "product_no_smith_residue rejected shipped-surface residue:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )
    inspected += _no_smith_residue_fire_probe(repo)
    return KernelResult(
        check_id="product_no_smith_residue",
        inspected=inspected,
        output=(
            "product no-Smith-residue scan passed: README.md, support/docs/spec, "
            "and agent/prompts carry no /Users/smith literal and no hardcoded "
            "insightwavesmith org outside the README working-example allowance; "
            "temp-copy FIRE probes for both forbidden families fired RED."
        ),
    )


def _minimal_operator_wake_target() -> Mapping[str, Any]:
    return {
        "target_ref": "operator-wake-target:local-active-operator",
        "target_kind": "operator_wake_local",
        "sink_ref": "report-sink:operator-wake-local",
        "delivery_mode": "local_projection",
        "side_effect_state": "none",
        "proof_limits": ["provider-neutral local wake target reference only"],
        "not_proven": [
            "operator noticed wake packet",
            "real provider thread wake behavior",
            "external side effect behavior",
        ],
    }


# Inbox-packet property tables, migrated 1:1 from the retired standing-packet
# pins of read_side_projection_boundary.yaml (json_required_paths +
# json_value_paths on the 3 dogfood status/inbox packets).
_INBOX_FRONTIER_PACKET_REQUIRED_KEYS = (
    "report_id",
    "report_kind",
    "building_id",
    "portfolio_id",
    "observed_board_state",
    "trigger_event_ref",
    "current_brick_ref",
    "current_work_kind",
    "current_lane",
    "last_completed_step_ref",
    "frontier_ref",
    "evidence_root_refs",
    "evidence_refs_present",
    "checker_summary_ref",
    "required_disposition_owner",
    "sink_refs",
    "generated_at",
    "source_truth",
    "not_proven",
    "proof_limits",
)
_OPERATOR_WAKE_PACKET_REQUIRED_KEYS = (
    "wake_packet_id",
    "report_id",
    "report_kind",
    "building_id",
    "observed_board_state",
    "evidence_root_refs",
    "operator_wake_targets",
    "source_truth",
    "not_proven",
    "proof_limits",
)


def _reporter_inbox_packet_shape_fold(
    reporter: Any,
    *,
    local_inbox_packet: Mapping[str, Any],
    wake_bus_frontier_packet: Mapping[str, Any],
    operator_wake_packet: Mapping[str, Any],
) -> None:
    """Assert the written inbox/wake packets carry the retired pins' shape."""

    for packet_label, packet in (
        ("local-inbox frontier packet", local_inbox_packet),
        ("wake-bus frontier packet", wake_bus_frontier_packet),
    ):
        for key in _INBOX_FRONTIER_PACKET_REQUIRED_KEYS:
            if key not in packet:
                raise ProfileError(f"{packet_label} is missing required key {key!r}")
        if not (isinstance(packet.get("evidence_root_refs"), list) and packet["evidence_root_refs"]):
            raise ProfileError(f"{packet_label} evidence_root_refs must be a non-empty list")
        if packet.get("observed_board_state") not in set(reporter.OBSERVED_BOARD_STATES):
            raise ProfileError(
                f"{packet_label} observed_board_state {packet.get('observed_board_state')!r} "
                "is not an admitted OBSERVED_BOARD_STATES member"
            )
        if "report-sink:local-inbox" not in (packet.get("sink_refs") or []):
            raise ProfileError(f"{packet_label} sink_refs does not name report-sink:local-inbox")
    if "report-sink:operator-wake-local" not in (
        wake_bus_frontier_packet.get("sink_refs") or []
    ):
        raise ProfileError(
            "wake-bus frontier packet sink_refs does not name report-sink:operator-wake-local"
        )
    wake_bus_targets = wake_bus_frontier_packet.get("operator_wake_targets")
    if not (isinstance(wake_bus_targets, list) and wake_bus_targets):
        raise ProfileError("wake-bus frontier packet operator_wake_targets must be non-empty")
    if any(
        target.get("sink_ref") != "report-sink:operator-wake-local"
        for target in wake_bus_targets
        if isinstance(target, Mapping)
    ):
        raise ProfileError(
            "wake-bus frontier packet operator_wake_targets[].sink_ref must be "
            "report-sink:operator-wake-local"
        )
    for key in _OPERATOR_WAKE_PACKET_REQUIRED_KEYS:
        if key not in operator_wake_packet:
            raise ProfileError(f"operator wake packet is missing required key {key!r}")
    wake_targets = operator_wake_packet.get("operator_wake_targets")
    if not (isinstance(wake_targets, list) and wake_targets):
        raise ProfileError("operator wake packet operator_wake_targets must be non-empty")
    for target in wake_targets:
        if not isinstance(target, Mapping) or target.get("delivery_mode") != "local_projection":
            raise ProfileError(
                "operator wake packet operator_wake_targets[].delivery_mode must be "
                "local_projection"
            )


def _assert_reporter_label_parity(repo: Path) -> int:
    canonical_path = repo / "support" / "operator" / "label_map.json"
    labels_js_path = repo / "support" / "dashboard" / "src" / "data" / "labels.js"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    if not isinstance(canonical, Mapping):
        raise ProfileError("label_map.json did not parse as a mapping")
    labels_js = labels_js_path.read_text(encoding="utf-8")
    checks = {
        "BRICK": "brick_kinds",
        "LANE": "lanes",
        "TOOL": "tool_policies",
        "MOVEMENT": "movements",
        "STATE": "states",
        "DISP": "display_states",
        "OWNER": "disposition_owners",
        "EVENT": "events",
        "OBSERVED": "observed_board_states",
        "ACTION": "actions",
    }
    inspected = 0
    for const_name, section in checks.items():
        observed = _extract_js_const_object(labels_js, const_name)
        expected = canonical.get(section)
        if observed != expected:
            raise ProfileError(
                f"label parity mismatch for {const_name}/{section}: "
                f"observed={observed!r} expected={expected!r}"
            )
        inspected += 1
    return inspected


def _extract_js_const_object(source: str, const_name: str) -> Mapping[str, Any]:
    marker = f"export const {const_name} ="
    marker_index = source.find(marker)
    if marker_index < 0:
        raise ProfileError(f"labels.js missing export const {const_name}")
    start = source.find("{", marker_index)
    if start < 0:
        raise ProfileError(f"labels.js export const {const_name} has no object literal")
    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                literal = source[start : index + 1]
                break
    else:
        raise ProfileError(f"labels.js export const {const_name} object did not close")
    literal = re.sub(r"//.*", "", literal)
    literal = re.sub(r"([,{]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r"\1'\2':", literal)
    try:
        parsed = ast.literal_eval(literal)
    except (SyntaxError, ValueError) as exc:
        raise ProfileError(f"labels.js export const {const_name} did not parse: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ProfileError(f"labels.js export const {const_name} is not a mapping")
    return dict(parsed)


def _assert_reporter_message_shape(report_sinks: Any) -> tuple[str, int]:
    packet = {
        **_minimal_reporter_packet(),
        "report_id": "reporter-message-shape-probe",
        "building_id": "customer-language-probe",
        "human_title": "알림 말투 점검",
        "observed_board_state": "observed_closed_boundary",
        "trigger_event_ref": "building-event:building_finished:customer-language-probe",
        "current_brick_ref": "brick-work",
        "current_work_kind": "work",
        "current_lane": "worker",
        "last_completed_step_ref": "work/step-outputs/customer-language-probe-work-attempt-1/step-output.json",
        "frontier_ref": "project/brick-protocol/buildings/customer-language-probe#frontier:complete:event:building_finished",
        "sink_refs": ["report-sink:slack"],
    }
    text = report_sinks._slack_message_text(packet)
    lines = text.splitlines()
    required_fragments = (
        "알림 말투 점검",
        "→ 완료됐어요.",
        "누구: 워커",
        "다음: 알림 확인",
        "ref: customer-language-probe",
        "frontier=complete:event:building_finished",
        "※ 상태 알림일 뿐",
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise ProfileError(f"Slack message shape missing fragment {fragment!r}:\n{text}")
    forbidden_headline_fragments = (
        "Brick:",
        "Agent:",
        "Link:",
        "work/step-outputs",
        "마지막 완료 step",
        "step=-",
        "brick=-",
        "운영 refs:",
    )
    headline = "\n".join(lines[:6])
    for fragment in forbidden_headline_fragments:
        if fragment in headline:
            raise ProfileError(f"Slack message headline leaked {fragment!r}:\n{text}")
    if sum(1 for line in lines if line.startswith("ref: ")) != 1:
        raise ProfileError(f"Slack message must carry exactly one compact ref line:\n{text}")
    empty_probe = report_sinks._slack_message_text(
        {
            **packet,
            "report_id": "reporter-message-empty-field-probe",
            "current_brick_ref": "",
            "last_completed_step_ref": "",
            "frontier_ref": "project/brick-protocol/buildings/customer-language-probe#frontier:complete",
        }
    )
    if "step=-" in empty_probe or "brick=-" in empty_probe:
        raise ProfileError(f"Slack message leaked empty ref fields:\n{empty_probe}")
    if sum(1 for line in empty_probe.splitlines() if line.startswith("ref: ")) != 1:
        raise ProfileError(f"Slack empty-field probe must keep one compact ref line:\n{empty_probe}")
    return text, len(required_fragments) + len(forbidden_headline_fragments) + 3


def _assert_reporter_auto_wiring(repo: Path, reporter: Any, report_sinks: Any) -> tuple[str, str, str, int]:
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.brick.work import parse_required_return_shape

    inspected = 0

    def _brain(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {}
        for label in parse_required_return_shape(request.required_return_shape):
            if label == "made_changes":
                returned[label] = ["notification auto-wire probe change"]
            elif label == "observed_evidence":
                returned[label] = ["notification auto-wire probe evidence"]
            elif label == "not_proven":
                returned[label] = ["semantic correctness of notification probe work"]
            else:
                returned[label] = f"probe value for {label}"
        return returned

    with tempfile.TemporaryDirectory(prefix="bp-reporter-auto-wire-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        no_env_plan = _reporter_auto_wire_plan("reporter-auto-wire-no-env")
        with _without_report_grain_env():
            result = run_building_plan(
                no_env_plan,
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env={},
            )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 2:
            raise ProfileError(
                "basic auto-wiring without Slack env should emit start and terminal observations"
            )
        for observation in observations:
            sink_refs = observation.get("report_packet", {}).get("sink_refs", [])
            if sink_refs != ["report-sink:local-inbox"]:
                raise ProfileError(
                    f"auto-wiring without Slack env attempted unexpected sinks: {sink_refs}"
                )
        inbox_packets = sorted((temp_repo / "project" / "brick-protocol" / "status" / "inbox").glob("*.json"))
        if len(inbox_packets) != 2:
            raise ProfileError("basic auto-wiring without Slack env did not write two local inbox packets")
        local_inbox_text = inbox_packets[0].read_text(encoding="utf-8")
        inspected += 4

    temp_sent_messages: list[str] = []

    def _fake_temp_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        temp_sent_messages.append(str(payload.get("text") or ""))
        return 200, b'{"ok":true}'

    with tempfile.TemporaryDirectory(prefix="bp-reporter-auto-wire-slack-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        repo_inbox = repo / "project" / "brick-protocol" / "status" / "inbox"
        repo_inbox_before = sorted(path.name for path in repo_inbox.glob("*.json")) if repo_inbox.is_dir() else []
        fake_env = {
            "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
            "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
        }
        with _without_report_grain_env():
            result = run_building_plan(
                _reporter_auto_wire_plan("reporter-auto-wire-fake-slack"),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_temp_slack_sender,
            )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 2:
            raise ProfileError("temp-root auto-wiring with fake Slack env emitted wrong event count")
        for observation in observations:
            sink_refs = observation.get("report_packet", {}).get("sink_refs", [])
            if sink_refs != ["report-sink:local-inbox"]:
                raise ProfileError(f"temp-root auto-wiring used external sinks: {sink_refs}")
        if temp_sent_messages:
            raise ProfileError(f"temp-root fake Slack sender was invoked: {len(temp_sent_messages)}")
        repo_inbox_after = sorted(path.name for path in repo_inbox.glob("*.json")) if repo_inbox.is_dir() else []
        if repo_inbox_after != repo_inbox_before:
            raise ProfileError("temp-root auto-wiring touched the real repo inbox")
        inspected += 5

    real_sent_messages: list[str] = []

    def _fake_real_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        real_sent_messages.append(str(payload.get("text") or ""))
        return 200, b'{"ok":true}'

    with tempfile.TemporaryDirectory(prefix="bp-reporter-real-vessel-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        fake_env = {
            "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
            "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
        }
        original_reporter_root = reporter.REPO_ROOT
        try:
            reporter.REPO_ROOT = temp_repo
            result = run_building_plan(
                _reporter_auto_wire_plan(
                    "reporter-auto-wire-real-vessel",
                    report_event_policy={
                        "enabled": True,
                        "mode": "basic",
                        "grain": "building",
                        "event_kinds": ["building_finished"],
                        "sink_refs": ["report-sink:local-inbox", "report-sink:slack"],
                        "allow_real_slack_delivery": True,
                    },
                ),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_real_slack_sender,
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 1:
            raise ProfileError("real-vessel completion emitted wrong event count")
        sink_refs = observations[0].get("report_packet", {}).get("sink_refs", [])
        if sink_refs != ["report-sink:local-inbox", "report-sink:slack"]:
            raise ProfileError(f"real-vessel completion used wrong sinks: {sink_refs}")
        if len(real_sent_messages) != 1:
            raise ProfileError(
                f"real-vessel fake Slack sender count expected 1, observed {len(real_sent_messages)}"
            )
        inspected += 4

    verbose_text = ""
    with tempfile.TemporaryDirectory(prefix="bp-reporter-verbose-mode-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        result = run_building_plan(
            _reporter_auto_wire_plan(
                "reporter-verbose-mode",
                step_kinds=("design", "work"),
                report_event_policy={
                    "enabled": True,
                    "mode": "verbose",
                    "grain": "building",
                    "event_kinds": ["building_finished"],
                    "sink_refs": ["report-sink:local-inbox"],
                },
            ),
            output_root=output_root,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _brain},
            adapter_cwd=repo,
            adapter_timeout_seconds=10,
            report_env={},
        )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 1:
            raise ProfileError("verbose-mode temp drive emitted wrong event count")
        packet = observations[0].get("report_packet", {})
        verbose_text = report_sinks._slack_message_text(packet)
        stage_lines = [line for line in verbose_text.splitlines() if line.startswith("단계: ")]
        if stage_lines != ["단계: 설계", "단계: 작업"]:
            raise ProfileError(f"verbose-mode message did not render per-step lines:\n{verbose_text}")
        inspected += 3

    return real_sent_messages[0], local_inbox_text, verbose_text, inspected


def _assert_reporter_brick_grain_threading(
    repo: Path,
    reporter: Any,
    report_sinks: Any,
) -> tuple[str, str, int]:
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.brick.work import parse_required_return_shape

    inspected = 0

    def _brain(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {}
        for label in parse_required_return_shape(request.required_return_shape):
            if label == "made_changes":
                returned[label] = ["brick grain probe change"]
            elif label == "observed_evidence":
                returned[label] = ["brick grain probe evidence"]
            elif label == "not_proven":
                returned[label] = ["semantic correctness of brick grain probe work"]
            else:
                returned[label] = f"probe value for {label}"
        return returned

    building_policy = reporter.report_event_policy_from_plan(
        {
            "report_event_policy": {
                "enabled": True,
                "grain": "building",
            }
        }
    )
    if building_policy.get("event_kinds") != [
        "building_started",
        "intervention_required",
        "building_finished",
    ]:
        raise ProfileError("building grain policy did not preserve the three existing event kinds")
    brick_policy = reporter.report_event_policy_from_plan(
        {
            "report_event_policy": {
                "enabled": True,
                "grain": "brick",
            }
        }
    )
    expected_brick_events = [
        "building_started",
        "intervention_required",
        "building_finished",
        "brick_received",
        "brick_returned",
        "gate_passed",
        "disposition_applied",
    ]
    if brick_policy.get("event_kinds") != expected_brick_events:
        raise ProfileError(
            "brick grain policy did not extend event kinds additively: "
            f"{brick_policy.get('event_kinds')!r}"
        )
    inspected += 2

    sent_payloads: list[Mapping[str, Any]] = []

    def _fake_thread_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        sent_payloads.append(payload)
        if payload.get("thread_ts"):
            return 200, b'{"ok":true}'
        return 200, b'{"ok":true,"ts":"1718200000.000100","channel":"CREDPROBE"}'

    fake_env = {
        "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
        "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
    }
    brick_reply_text = ""
    disposition_reply_text = ""
    with tempfile.TemporaryDirectory(prefix="bp-reporter-brick-grain-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        original_reporter_root = reporter.REPO_ROOT
        try:
            reporter.REPO_ROOT = temp_repo
            result = run_building_plan(
                _reporter_auto_wire_plan(
                    "reporter-brick-grain-thread",
                    report_event_policy={
                        "enabled": True,
                        "mode": "basic",
                        "grain": "brick",
                        "sink_refs": ["report-sink:slack"],
                        "allow_real_slack_delivery": True,
                    },
                ),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_thread_slack_sender,
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root

        root = output_root / "reporter-brick-grain-thread"
        thread_path = root / "raw" / "report-thread.jsonl"
        if not thread_path.is_file():
            raise ProfileError("brick grain parent Slack ts was not recorded in raw/report-thread.jsonl")
        thread_text = thread_path.read_text(encoding="utf-8")
        if "1718200000.000100" not in thread_text or "CREDPROBE" not in thread_text:
            raise ProfileError("brick grain thread record did not preserve ts + channel ref")

        observations = tuple(getattr(result, "_report_event_observations", ()))
        trigger_refs = [
            str(observation.get("report_packet", {}).get("trigger_event_ref") or "")
            for observation in observations
            if isinstance(observation, Mapping)
        ]
        for event_kind in ("brick_received", "brick_returned", "gate_passed"):
            if not any(event_kind in trigger for trigger in trigger_refs):
                raise ProfileError(f"brick grain did not emit {event_kind} support event")

        thread_payloads = [payload for payload in sent_payloads if payload.get("thread_ts")]
        if len(thread_payloads) != 1:
            raise ProfileError(
                f"brick grain expected exactly one per-step Slack thread reply, got {len(thread_payloads)}"
            )
        reply = thread_payloads[0]
        if reply.get("thread_ts") != "1718200000.000100":
            raise ProfileError(f"brick grain reply carried wrong thread_ts: {reply!r}")
        brick_reply_text = str(reply.get("text") or "")
        for fragment in ("①", "받음(", "반환(", "게이트 결과(", "ref: reporter-brick-grain-thread"):
            if fragment not in brick_reply_text:
                raise ProfileError(
                    f"brick grain Slack reply missing fragment {fragment!r}:\n{brick_reply_text}"
                )
        if not re.search(r"받음\(\d{2}:\d{2}\).*반환\(\d{2}:\d{2}", brick_reply_text):
            raise ProfileError(f"brick grain Slack reply did not render KST HH:MM times:\n{brick_reply_text}")
        inspected += 5

        missing_thread_payloads: list[Mapping[str, Any]] = []

        def _should_not_send(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            missing_thread_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        missing_thread_root = output_root / "missing-thread-case"
        missing_thread_root.mkdir(parents=True)
        try:
            missing_packet = reporter.render_building_event_report_packet(
                event_kind="brick_returned",
                building_id="missing-thread-case",
                building_root=missing_thread_root,
                current_brick_ref="brick-work",
                last_completed_step_ref="work/step-outputs/missing-thread-case-work-attempt-1/step-output.json",
                sink_refs=["report-sink:slack"],
                repo_root=temp_repo,
                generated_at="2026-06-12T00:00:00+00:00",
                event_context={
                    "step_ref": "missing-thread-case-work",
                    "sequence_index": 1,
                    "received_at": "2026-06-12T00:00:00+00:00",
                    "returned_at": "2026-06-12T00:01:00+00:00",
                    "gate_note": "통과→다음스텝",
                },
            )
            missing_observation = report_sinks.send_slack_report_packet(
                missing_packet,
                repo_root=temp_repo,
                allow_real_delivery=True,
                env=fake_env,
                sender=_should_not_send,
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        if missing_observation.delivery_status_class != "not_attempted_missing_thread_ts":
            raise ProfileError(
                "brick grain missing-thread Slack send did not fail closed as not_attempted"
            )
        if missing_thread_payloads:
            raise ProfileError("brick grain missing-thread probe still called Slack sender")

        disposition_payloads: list[Mapping[str, Any]] = []

        def _fake_disposition_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
            disposition_payloads.append(payload)
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        try:
            disposition_packet = reporter.render_building_event_report_packet(
                event_kind="disposition_applied",
                building_id="reporter-brick-grain-thread",
                building_root=root,
                current_brick_ref="brick-work",
                last_completed_step_ref="work/step-outputs/reporter-brick-grain-thread-work-attempt-1/step-output.json",
                sink_refs=["report-sink:slack"],
                repo_root=temp_repo,
                generated_at="2026-06-12T00:02:00+00:00",
                event_context={
                    "disposition_action": "forward",
                    "disposition_author_ref": "coo:checker",
                    "applied_at": "2026-06-12T00:02:00+00:00",
                },
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        disposition_observation = report_sinks.send_slack_report_packet(
            disposition_packet,
            repo_root=temp_repo,
            allow_real_delivery=True,
            env=fake_env,
            sender=_fake_disposition_sender,
        )
        if disposition_observation.delivered is not True or len(disposition_payloads) != 1:
            raise ProfileError("disposition_applied probe did not send exactly one thread reply")
        if disposition_payloads[0].get("thread_ts") != "1718200000.000100":
            raise ProfileError("disposition_applied reply did not carry recorded thread_ts")
        disposition_reply_text = str(disposition_payloads[0].get("text") or "")
        if "⤷ coo 도장" not in disposition_reply_text:
            raise ProfileError(
                f"disposition_applied reply did not render coo stamp:\n{disposition_reply_text}"
            )
        inspected += 4

        temp_root_payloads: list[Mapping[str, Any]] = []

        def _temp_root_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            temp_root_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true,"ts":"1718200000.000200","channel":"CREDPROBE"}'

        non_vessel_root = Path(tmpdir) / "non-vessel-building-root"
        non_vessel_root.mkdir()
        temp_root_policy = reporter.report_event_policy_from_plan(
            {
                "report_event_policy": {
                    "enabled": True,
                    "grain": "brick",
                    "sink_refs": ["report-sink:slack"],
                    "allow_real_slack_delivery": True,
                }
            }
        )
        for event_kind in (
            "brick_received",
            "brick_returned",
            "gate_passed",
            "disposition_applied",
        ):
            observation = reporter.emit_building_event_for_policy(
                temp_root_policy,
                event_kind=event_kind,
                building_id=f"temp-root-{event_kind}",
                building_root=non_vessel_root,
                current_brick_ref="brick-work",
                last_completed_step_ref=f"work/step-outputs/temp-root-{event_kind}/step-output.json",
                repo_root=temp_repo,
                slack_env=fake_env,
                slack_sender=_temp_root_sender,
                event_context={"sequence_index": 1},
            )
            if observation is not None:
                raise ProfileError(
                    f"brick grain F12 vessel guard leaked external sink for {event_kind}"
                )
        if temp_root_payloads:
            raise ProfileError(
                "brick grain F12 vessel guard invoked Slack sender for temp-root building"
            )
        inspected += 4

    return brick_reply_text, disposition_reply_text, inspected


def _copy_reporter_probe_agent_resources(repo: Path, temp_repo: Path) -> None:
    source = repo / "agent"
    target = temp_repo / "agent"
    shutil.copytree(source, target)


def _reporter_auto_wire_plan(
    building_id: str,
    *,
    step_kinds: Sequence[str] = ("work",),
    report_event_policy: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    from support.checkers.lib.case_runners import _graph_test_plan_from_linear

    steps: list[Mapping[str, Any]] = []
    for index, kind in enumerate(step_kinds):
        step_ref = f"{building_id}-{kind}"
        brick_instance_ref = f"brick-{kind}"
        next_target = (
            f"brick-{step_kinds[index + 1]}"
            if index + 1 < len(step_kinds)
            else f"building-boundary:{building_id}-closed"
        )
        steps.append(
            {
                "step_ref": step_ref,
                "step_template_ref": f"building-step-template:{kind}",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": f"brick-row:{step_ref}",
                        "brick_work_ref": f"work:{step_ref}",
                        "brick_instance_ref": brick_instance_ref,
                        "work_statement": "Exercise reporter auto-wire notification projection.",
                        "comparison_rule": "Support observes notification projection only.",
                        "required_return_shape": "made_changes, observed_evidence, not_proven",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": f"agent-row:{step_ref}",
                        "agent_object_ref": "agent-object:dev",
                    },
                    {
                        "axis": "Link",
                        "row_ref": f"link-row:{step_ref}",
                        "movement": "forward",
                        "target_ref": next_target,
                        "building_lifecycle": {
                            "state": "closed",
                            "reason": "reporter auto-wire probe closed boundary",
                        },
                    },
                ],
            }
        )
    plan: dict[str, Any] = {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "linear",
        "selected_adapter_ref": "adapter:local",
        "task_source_ref": "task-source:inline-statement",
        "task_statement": f"# {building_id}\n\nExercise reporter auto-wire notification projection.",
        "steps": steps,
    }
    if report_event_policy is not None:
        plan["report_event_policy"] = dict(report_event_policy)
    return _graph_test_plan_from_linear(plan)


def _assert_no_scheduler_constructs(repo: Path) -> int:
    inspected = 0
    files = (
        repo / "support" / "operator" / "reporter.py",
        repo / "support" / "operator" / "report_sinks.py",
        repo / "support" / "operator" / "run.py",
        repo / "support" / "operator" / "walker_kernel.py",
    )
    forbidden_imports = {"threading", "sched", "queue", "asyncio"}
    forbidden_name_calls = {"sleep", "Thread", "Timer", "Queue"}
    forbidden_attr_calls = {
        ("time", "sleep"),
        ("threading", "Thread"),
        ("threading", "Timer"),
        ("queue", "Queue"),
        ("asyncio", "create_task"),
    }
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in forbidden_imports:
                        raise ProfileError(f"no-scheduler pin rejected import {alias.name} in {path}")
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".", 1)[0]
                if module in forbidden_imports:
                    raise ProfileError(f"no-scheduler pin rejected import from {node.module} in {path}")
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in forbidden_name_calls:
                    raise ProfileError(f"no-scheduler pin rejected call {func.id} in {path}")
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if (func.value.id, func.attr) in forbidden_attr_calls:
                        raise ProfileError(
                            f"no-scheduler pin rejected call {func.value.id}.{func.attr} in {path}"
                        )
        inspected += 1
    return inspected


def run_reporter_notification_projection(repo: Path) -> KernelResult:
    _ensure_import_identity(repo)
    reporter = importlib.import_module("brick_protocol.support.operator.reporter")
    report_sinks = importlib.import_module("brick_protocol.support.operator.report_sinks")
    label_parity_count = _assert_reporter_label_parity(repo)
    message_text, message_shape_count = _assert_reporter_message_shape(report_sinks)
    (
        auto_wire_message,
        auto_wire_inbox_text,
        verbose_mode_text,
        auto_wire_count,
    ) = _assert_reporter_auto_wiring(repo, reporter, report_sinks)
    (
        brick_grain_text,
        disposition_text,
        brick_grain_count,
    ) = _assert_reporter_brick_grain_threading(repo, reporter, report_sinks)
    no_scheduler_count = _assert_no_scheduler_constructs(repo)

    observations = tuple(reporter.reporter_negative_probe_observations())
    if not observations:
        raise ProfileError("reporter negative probes did not return observations")
    not_rejected = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in observations
        if observation.get("rejected") is not True
    ]
    if not_rejected:
        raise ProfileError(
            "reporter negative probe(s) were not rejected: " + ", ".join(not_rejected)
        )
    owner_observations = tuple(reporter.reporter_owner_vocabulary_probe_observations())
    if not owner_observations:
        raise ProfileError("reporter owner vocabulary probes did not return observations")
    owner_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in owner_observations
        if observation.get("passed") is not True
    ]
    if owner_not_passed:
        raise ProfileError(
            "reporter owner vocabulary probe(s) did not pass: "
            + ", ".join(owner_not_passed)
        )
    delivery_wake_observations = tuple(reporter.reporter_delivery_wake_probe_observations())
    if not delivery_wake_observations:
        raise ProfileError("reporter delivery wake probes did not return observations")
    delivery_wake_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in delivery_wake_observations
        if observation.get("passed") is not True
    ]
    if delivery_wake_not_passed:
        raise ProfileError(
            "reporter delivery wake probe(s) did not pass: "
            + ", ".join(delivery_wake_not_passed)
        )
    event_hook_observations = tuple(reporter.reporter_event_hook_probe_observations())
    if not event_hook_observations:
        raise ProfileError("reporter event hook probes did not return observations")
    event_hook_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in event_hook_observations
        if observation.get("passed") is not True
    ]
    if event_hook_not_passed:
        raise ProfileError(
            "reporter event hook probe(s) did not pass: "
            + ", ".join(event_hook_not_passed)
        )

    packet = _minimal_reporter_packet()
    reporter.validate_report_packet(packet)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_repo = Path(tmp)
        sink_observations = report_sinks.deliver_report_packet(
            packet,
            repo_root=tmp_repo,
            overwrite_existing=False,
        )
        if len(sink_observations) != 1:
            raise ProfileError("local inbox sink did not return exactly one observation")
        sink_observation = sink_observations[0]
        if sink_observation.delivered is not True:
            raise ProfileError("local inbox sink observation did not mark delivered")
        written = tmp_repo / sink_observation.written_path
        if not written.is_file():
            raise ProfileError(f"local inbox sink did not write packet: {written}")
        written_packet = json.loads(written.read_text(encoding="utf-8"))
        if written_packet.get("source_truth") is not False:
            raise ProfileError("written local inbox packet source_truth is not false")

        wake_packet = {
            **packet,
            "sink_refs": ["report-sink:local-inbox", "report-sink:operator-wake-local"],
            "operator_wake_targets": [_minimal_operator_wake_target()],
        }
        wake_observations = report_sinks.deliver_report_packet(
            wake_packet,
            repo_root=tmp_repo,
            overwrite_existing=True,
        )
        if len(wake_observations) != 2:
            raise ProfileError("delivery wake bus did not emit two local observations")
        operator_wake_observations = [
            observation
            for observation in wake_observations
            if observation.sink_ref == "report-sink:operator-wake-local"
        ]
        if len(operator_wake_observations) != 1:
            raise ProfileError("operator wake local sink observation was not emitted")
        wake_written = tmp_repo / operator_wake_observations[0].written_path
        if not wake_written.is_file():
            raise ProfileError(f"operator wake sink did not write packet: {wake_written}")
        wake_written_packet = json.loads(wake_written.read_text(encoding="utf-8"))
        if wake_written_packet.get("source_truth") is not False:
            raise ProfileError("operator wake packet source_truth is not false")
        if not wake_written_packet.get("operator_wake_targets"):
            raise ProfileError("operator wake packet did not preserve wake target refs")

        # CLEAN-YARD v3 (Smith 0611): the 3 standing dogfood inbox packets
        # (run-surface-authority-boundary-0529 / reporter-delivery-wake-bus-0531)
        # left for the frozen museum; their json_required_paths/json_value_paths
        # pin properties are EXECUTED here 1:1 over the packets the REAL sinks
        # just wrote into the temp inbox.
        local_inbox_wake_bus = [
            observation
            for observation in wake_observations
            if observation.sink_ref == "report-sink:local-inbox"
        ]
        if len(local_inbox_wake_bus) != 1:
            raise ProfileError("wake-bus local inbox sink observation was not emitted")
        wake_bus_frontier_packet = json.loads(
            (tmp_repo / local_inbox_wake_bus[0].written_path).read_text(encoding="utf-8")
        )
        _reporter_inbox_packet_shape_fold(
            reporter,
            local_inbox_packet=written_packet,
            wake_bus_frontier_packet=wake_bus_frontier_packet,
            operator_wake_packet=wake_written_packet,
        )

        sink_rejected_complete = False
        try:
            report_sinks.deliver_report_packet(
                {**packet, "complete": True},
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_complete = True
        if not sink_rejected_complete:
            raise ProfileError("local inbox sink accepted forbidden complete field")

        sink_rejected_raw_secret = False
        try:
            report_sinks.deliver_report_packet(
                {**packet, "raw_secret": "redacted-probe"},
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_raw_secret = True
        if not sink_rejected_raw_secret:
            raise ProfileError("local inbox sink accepted raw secret shaped field")

        sink_rejected_unadmitted = False
        try:
            report_sinks.deliver_report_packet(
                packet,
                sink_refs=["report-sink:unadmitted"],
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_unadmitted = True
        if not sink_rejected_unadmitted:
            raise ProfileError("local inbox sink accepted unadmitted sink ref")

    # G6 sink ceiling — re-ratified at FOUR by Smith (0611): report_sinks owns
    # the dispatch seam + exactly these four sinks. The dashboard sink
    # (B-DASH/B-DASH-WIRE) made the set 4 de facto; Smith ratified 4 with the
    # explicit condition that a 5th sink requires the report_bus + sinks/<name>
    # split FIRST (blueprint 3.1) — never a 5th sibling in this module.
    ratified_sink_refs = frozenset(
        {
            "report-sink:local-inbox",
            "report-sink:operator-wake-local",
            "report-sink:slack",
            "report-sink:dashboard",
        }
    )
    admitted_sink_refs = frozenset(report_sinks.ADMITTED_SINK_REFS)
    if admitted_sink_refs != ratified_sink_refs:
        unexpected = sorted(admitted_sink_refs - ratified_sink_refs)
        missing = sorted(ratified_sink_refs - admitted_sink_refs)
        raise ProfileError(
            "G6 sink ceiling violated: ADMITTED_SINK_REFS must be exactly the "
            f"FOUR Smith-ratified (0611) sinks {sorted(ratified_sink_refs)} "
            f"(unexpected={unexpected}, missing={missing}); "
            "a 5th sink requires the report_bus split — never a 5th sibling"
        )

    return KernelResult(
        check_id="reporter_notification_projection",
        inspected=(
            len(observations)
            + len(owner_observations)
            + len(delivery_wake_observations)
            + len(event_hook_observations)
            + label_parity_count
            + message_shape_count
            + auto_wire_count
            + brick_grain_count
            + no_scheduler_count
            + 6
        ),
        output=(
            "reporter notification projection passed: "
            f"{len(observations)} reporter negative probe(s), "
            f"{len(owner_observations)} owner vocabulary probe(s), "
            f"{len(delivery_wake_observations)} delivery wake probe(s), "
            f"{len(event_hook_observations)} event hook probe(s), "
            f"{label_parity_count} label parity map(s), "
            f"{message_shape_count} Slack message shape assertion(s), "
            f"{auto_wire_count} auto-wire assertion(s), "
            f"{brick_grain_count} brick-grain thread assertion(s), "
            f"{no_scheduler_count} no-scheduler source file(s), "
            "local inbox write, operator wake write, forbidden field rejects, "
            "unadmitted sink reject, and the G6 sink ceiling (4 ratified sinks: "
            "local-inbox, operator-wake-local, slack, dashboard — Smith 0611; "
            "a 5th sink requires the report_bus split, never a 5th sibling) inspected. "
            f"Specimen after renderer: {message_text!r}. "
            f"Temp auto-wire Slack text: {auto_wire_message!r}. "
            f"Verbose-mode temp Slack text: {verbose_mode_text!r}. "
            f"Brick-grain Slack text: {brick_grain_text!r}. "
            f"Disposition Slack text: {disposition_text!r}. "
            f"Temp local inbox packet bytes: {len(auto_wire_inbox_text.encode('utf-8'))}."
        ),
    )


def run_adapter_error_frontier_manifest_consistency(repo: Path) -> KernelResult:
    """Pin adapter-error frontier raw_ref resolution after final closure rewrite."""

    from support.checkers import check_building_lifecycle_path_shape as lifecycle_shape
    from support.operator import run as run_module
    from support.recording.raw_claim_trace import reconcile_claim_trace_raw_manifest_from_raw

    del repo
    with tempfile.TemporaryDirectory(prefix="bp-adapter-error-frontier-manifest-") as tmp:
        root = Path(tmp) / "adapter-error-frontier-manifest-case"
        _adapter_error_manifest_write_broken_fixture(root)

        red_violations: list[str] = []
        lifecycle_shape.validate_minimal_content(root, red_violations)
        if not any("raw_ref does not resolve through raw manifest" in item for item in red_violations):
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency FIRE did not observe "
                "unresolved claim_trace raw_refs before reconciliation"
            )

        written = reconcile_claim_trace_raw_manifest_from_raw(root)
        green_violations: list[str] = []
        lifecycle_shape.validate_minimal_content(root, green_violations)
        if green_violations:
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency lifecycle checker rejected "
                "reconciled fixture:\n"
                + "\n".join(f"- {violation}" for violation in green_violations)
            )

        manifest = json.loads((root / "raw" / "raw-manifest.json").read_text(encoding="utf-8"))
        refs = {
            str(ref)
            for entry in manifest.get("entries", [])
            if isinstance(entry, Mapping)
            for ref in entry.get("raw_refs", [])
            if isinstance(ref, str)
        }
        for ref in ("raw:agent-received:02", "raw:adapter-error:02", "raw:link-frontier:02"):
            if ref not in refs:
                raise ProfileError(
                    "adapter_error_frontier_manifest_consistency reconciled manifest "
                    f"does not carry {ref}"
                )

        preserve_root = Path(tmp) / "adapter-error-frontier-preserve-case"
        _adapter_error_manifest_write_broken_fixture(preserve_root)
        _adapter_error_manifest_write_jsonl(
            preserve_root / "raw" / "link.jsonl",
            [
                {
                    "raw_ref": "raw:link:01",
                    "raw_refs": ["raw:link:01"],
                    "step_ref": f"{preserve_root.name}-work",
                },
                _adapter_error_manifest_link_frontier_record(preserve_root.name),
            ],
        )
        snapshot = run_module._adapter_error_frontier_history_snapshot(preserve_root)
        _adapter_error_manifest_write_jsonl(
            preserve_root / "raw" / "link.jsonl",
            [
                {
                    "raw_ref": "raw:link:01",
                    "raw_refs": ["raw:link:01"],
                    "step_ref": f"{preserve_root.name}-work",
                }
            ],
        )
        run_module._preserve_adapter_error_frontier_history_after_resume(preserve_root, snapshot)
        preserve_violations: list[str] = []
        lifecycle_shape.validate_minimal_content(preserve_root, preserve_violations)
        if preserve_violations:
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency lifecycle checker rejected "
                "preserved final-writer fixture:\n"
                + "\n".join(f"- {violation}" for violation in preserve_violations)
            )

    return KernelResult(
        check_id="adapter_error_frontier_manifest_consistency",
        inspected=len(written) + 3,
        output=(
            "adapter-error frontier manifest consistency passed: synthetic "
            "adapter-error->closure fixture fired RED before reconciliation and "
            "the same lifecycle raw_ref resolver accepted both the reconciled root "
            "and the final-writer preserve root."
        ),
    )


def run_adapter_error_path_hardening(repo: Path) -> KernelResult:
    """Pin F15/F16/F18/F19 adapter-error hardening invariants."""

    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator import run as run_module
    from brick_protocol.support.operator import walker_kernel
    from brick_protocol.support.operator import walker_resume
    from brick_protocol.support.operator.frontier_observation import observe_building_frontier
    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref
    from support.checkers import check_building_lifecycle_path_shape as lifecycle_shape

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-adapter-error-hardening-") as tmp:
        output_root = Path(tmp) / "buildings"
        error_building_id = "adapter-error-hardening-first-step"
        root = output_root / error_building_id
        cli_calls: list[tuple[str, ...]] = []

        def failing_codex_runner(
            args: Sequence[str],
            cwd: Path,
            timeout_seconds: int,
        ) -> LocalCliCompleted:
            del cwd, timeout_seconds
            call = tuple(str(arg) for arg in args)
            cli_calls.append(call)
            birth_certificate = root / "work" / "declared-building-plan.json"
            if not birth_certificate.is_file():
                raise ProfileError(
                    "adapter_error_path_hardening F15/F17: first adapter boundary "
                    "was reached before work/declared-building-plan.json existed"
                )
            if "--version" in call:
                return LocalCliCompleted(call, 0, "codex test-version", "")
            return LocalCliCompleted(call, 1, "", "adapter boom")

        # B2: a dynamic adapter exception/timeout no longer crashes the public
        # surface with a bare RuntimeError. run_building_plan now CATCHES the typed
        # AdapterFrontierEvidenceWritten and RETURNS a clean HELD result (the
        # adapter-error frontier is already written + resumable on disk). Assert the
        # clean held return -- a bare RuntimeError escaping here REDs the check.
        try:
            held_result = run_module.run_building_plan(
                _adapter_error_hardening_graph_plan(
                    error_building_id,
                    first_adapter_ref="adapter:codex-local",
                ),
                output_root=output_root,
                overwrite_existing=True,
                command_runner=failing_codex_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=5,
            )
        except RuntimeError as exc:
            raise ProfileError(
                "adapter_error_path_hardening B2: a dynamic adapter exception must "
                "return a clean held result, not raise a bare RuntimeError "
                f"({exc!r})"
            ) from exc
        held_frontier = observe_building_frontier(root, repo_root=repo)
        if held_frontier.get("frontier_kind") != "agent_incomplete":
            raise ProfileError(
                "adapter_error_path_hardening B2: a dynamic adapter exception did not "
                f"end in an agent_incomplete held frontier: {held_frontier.get('frontier_kind')!r}"
            )
        if _persisted_adapter_error_hold_reason(root) != "adapter_error_frontier":
            raise ProfileError(
                "adapter_error_path_hardening B2: held frontier did not carry the "
                "adapter_error_frontier hold_reason"
            )
        if held_result.step_results:
            raise ProfileError(
                "adapter_error_path_hardening B2: first-step adapter error held with "
                "completed step results"
            )
        inspected += len(cli_calls) + 1
        if not cli_calls:
            raise ProfileError("adapter_error_path_hardening did not reach codex adapter probe")
        if not (root / "work" / "declared-building-plan.json").is_file():
            raise ProfileError("adapter_error_path_hardening root lacks birth certificate")
        try:
            run_module.resume_building_plan(root, command_runner=failing_codex_runner)
        except ValueError as exc:
            if "birth-certificate" in str(exc):
                raise ProfileError(
                    "adapter_error_path_hardening resume still refused the first-step "
                    "adapter-error root for missing birth certificate"
                ) from exc
        else:
            raise ProfileError("adapter_error_path_hardening resume without disposition did not hold")
        inspected += 1

        _append_adapter_error_stop_disposition(root)
        before_resume_calls = len(cli_calls)
        resumed = run_module.resume_building_plan(
            root,
            command_runner=failing_codex_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=5,
        )
        if len(cli_calls) != before_resume_calls:
            raise ProfileError("adapter_error_path_hardening F16 stop invoked adapter")
        if resumed.step_results:
            raise ProfileError("adapter_error_path_hardening F16 paper stop replayed step results")
        frontier = observe_building_frontier(root, repo_root=repo)
        if frontier.get("frontier_kind") != "complete":
            raise ProfileError(
                "adapter_error_path_hardening F16 paper stop did not observe complete "
                f"frontier: {frontier.get('frontier_kind')!r}"
            )
        inspected += 3

        mutation_root = output_root / "adapter-error-hardening-mutated-stop"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=mutation_root.name,
        )
        _append_adapter_error_stop_disposition(mutation_root)
        original_resume = run_module._resume_dynamic_graph_walker
        mutation_calls: list[tuple[str, ...]] = []

        def mutation_runner(
            args: Sequence[str],
            cwd: Path,
            timeout_seconds: int,
        ) -> LocalCliCompleted:
            del cwd, timeout_seconds
            call = tuple(str(arg) for arg in args)
            mutation_calls.append(call)
            raise RuntimeError("mutated stop path attempted live adapter invocation")

        def mutated_resume(*args: Any, **kwargs: Any) -> Any:
            runner = kwargs.get("command_runner")
            if runner is not None:
                runner(("codex", "exec", "mutated-live-rerun"), Path("."), 1)
            return original_resume(*args, **kwargs)

        try:
            run_module._resume_dynamic_graph_walker = mutated_resume
            try:
                run_module.resume_building_plan(
                    mutation_root,
                    command_runner=mutation_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=5,
                )
            except RuntimeError as exc:
                if "mutated stop path attempted live adapter invocation" not in str(exc):
                    raise
            else:
                raise ProfileError(
                    "adapter_error_path_hardening F16 mutation did not fire RED"
                )
        finally:
            run_module._resume_dynamic_graph_walker = original_resume
        if not mutation_calls:
            raise ProfileError("adapter_error_path_hardening F16 mutation made no adapter call")
        inspected += len(mutation_calls)

        legacy_root = output_root / "adapter-error-hardening-legacy-stop"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=legacy_root.name,
            first_adapter_ref="adapter:local",
            followup_adapter_ref="adapter:codex-local",
            local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
        )
        _rewrite_adapter_error_hold_as_legacy_reason_refs(legacy_root)
        _append_adapter_error_stop_disposition(legacy_root)
        legacy_calls: list[tuple[str, ...]] = []

        def legacy_runner(
            args: Sequence[str],
            cwd: Path,
            timeout_seconds: int,
        ) -> LocalCliCompleted:
            del cwd, timeout_seconds
            call = tuple(str(arg) for arg in args)
            legacy_calls.append(call)
            raise RuntimeError("legacy stop path attempted live adapter invocation")

        legacy_resumed = run_module.resume_building_plan(
            legacy_root,
            local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
            command_runner=legacy_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=5,
        )
        if legacy_calls:
            raise ProfileError("adapter_error_path_hardening F16b legacy stop invoked adapter")
        if legacy_resumed.step_results:
            raise ProfileError("adapter_error_path_hardening F16b legacy paper stop replayed step results")
        legacy_frontier = observe_building_frontier(legacy_root, repo_root=repo)
        if legacy_frontier.get("frontier_kind") != "complete":
            raise ProfileError(
                "adapter_error_path_hardening F16b legacy paper stop did not observe "
                f"complete frontier: {legacy_frontier.get('frontier_kind')!r}"
            )
        inspected += 4

        mutation_legacy_root = output_root / "adapter-error-hardening-legacy-mutated-stop"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=mutation_legacy_root.name,
            first_adapter_ref="adapter:local",
            followup_adapter_ref="adapter:codex-local",
            local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
        )
        _rewrite_adapter_error_hold_as_legacy_reason_refs(mutation_legacy_root)
        _append_adapter_error_stop_disposition(mutation_legacy_root)
        original_adapter_error_predicate = walker_resume._adapter_error_hold_without_return
        mutation_legacy_calls: list[tuple[str, ...]] = []

        def mutation_legacy_runner(
            args: Sequence[str],
            cwd: Path,
            timeout_seconds: int,
        ) -> LocalCliCompleted:
            del cwd, timeout_seconds
            call = tuple(str(arg) for arg in args)
            mutation_legacy_calls.append(call)
            raise RuntimeError("legacy flat-field-only predicate attempted live adapter invocation")

        def flat_field_only_predicate(hold_record: Mapping[str, Any]) -> bool:
            return hold_record.get("hold_reason") == "adapter_error_frontier"

        try:
            walker_resume._adapter_error_hold_without_return = flat_field_only_predicate
            # B2: the broken (flat-field-only) predicate fails to recognize the legacy
            # reason-ref hold, so resume does a LIVE adapter rerun. That live call now
            # ends in a clean held adapter-error frontier instead of a bare RuntimeError
            # crash, so the mutation-RED signal is the live adapter invocation itself
            # (mutation_legacy_calls non-empty), not a propagated exception.
            try:
                run_module.resume_building_plan(
                    mutation_legacy_root,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _hardening_local_brain
                    },
                    command_runner=mutation_legacy_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=5,
                )
            except RuntimeError:
                # A live adapter call may still surface as a non-adapter RuntimeError
                # depending on the failure shape; either way the live call was made.
                pass
        finally:
            walker_resume._adapter_error_hold_without_return = original_adapter_error_predicate
        if not mutation_legacy_calls:
            raise ProfileError(
                "adapter_error_path_hardening F16b legacy flat-field-only "
                "mutation did not fire RED (no live adapter invocation)"
            )
        inspected += len(mutation_legacy_calls)

        _assert_codex_ephemeral_env_dial(repo)
        inspected += 2

        overwrite_root = output_root / "adapter-error-hardening-overwrite"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=overwrite_root.name,
        )
        if not (overwrite_root / "evidence" / "claim_trace" / "link" / "frontier_trace.json").is_file():
            raise ProfileError("adapter_error_path_hardening overwrite seed lacked frontier trace")
        run_module.run_building_plan(
            _adapter_error_hardening_graph_plan(
                overwrite_root.name,
                first_adapter_ref="adapter:local",
            ),
            output_root=output_root,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
            adapter_cwd=repo,
            adapter_timeout_seconds=5,
        )
        if (overwrite_root / "evidence" / "claim_trace" / "link" / "frontier_trace.json").exists():
            raise ProfileError("adapter_error_path_hardening F19 stale frontier_trace survived")
        manifest = json.loads(
            (overwrite_root / "raw" / "raw-manifest.json").read_text(encoding="utf-8")
        )
        manifest_refs = {
            str(ref)
            for ref in manifest.get("raw_refs", [])
            if isinstance(ref, str)
        }
        if any(ref.startswith("raw:link-frontier:") for ref in manifest_refs):
            raise ProfileError("adapter_error_path_hardening F19 stale link-frontier ref survived")
        violations: list[str] = []
        lifecycle_shape.validate_minimal_content(overwrite_root, violations)
        if violations:
            raise ProfileError(
                "adapter_error_path_hardening F19 overwrite root failed lifecycle shape:\n"
                + "\n".join(f"- {violation}" for violation in violations)
            )
        inspected += 4

        mutation_overwrite_root = output_root / "adapter-error-hardening-overwrite-mutated"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=mutation_overwrite_root.name,
        )
        original_clear = walker_kernel._clear_overwrite_claim_trace_manifest
        try:
            walker_kernel._clear_overwrite_claim_trace_manifest = lambda root: None
            run_module.run_building_plan(
                _adapter_error_hardening_graph_plan(
                    mutation_overwrite_root.name,
                    first_adapter_ref="adapter:local",
                ),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
                adapter_cwd=repo,
                adapter_timeout_seconds=5,
            )
        finally:
            walker_kernel._clear_overwrite_claim_trace_manifest = original_clear
        if not (
            mutation_overwrite_root
            / "evidence"
            / "claim_trace"
            / "link"
            / "frontier_trace.json"
        ).exists():
            raise ProfileError("adapter_error_path_hardening F19 mutation did not fire RED")
        inspected += 1

    return KernelResult(
        check_id="adapter_error_path_hardening",
        inspected=inspected,
        output=(
            "adapter-error hardening passed: birth certificate existed before first "
            "codex adapter probe, resume no longer birth-certificate-refuses the "
            "first-step adapter-error root, stop disposition paper-closed without "
            "adapter invocation for flat and legacy reason-ref holds, codex --ephemeral "
            "is env-gated, overwrite cleared stale claim_trace/raw manifest refs, and "
            "F16/F16b/F19 mutation probes fired RED."
        ),
    )


def _adapter_error_hardening_graph_plan(
    building_id: str,
    *,
    first_adapter_ref: str,
    followup_adapter_ref: str = "adapter:local",
) -> Mapping[str, Any]:
    plan = json.loads(json.dumps(_chat_session_park_graph_plan(building_id=building_id)))
    plan.pop("report_event_policy", None)
    first_step = plan["brick_steps"][0]
    first_step["selected_adapter_ref"] = first_adapter_ref
    first_step["step_ref"] = f"{building_id}-work"
    first_step["completion_edge_ref"] = f"edge:{building_id}-work-to-followup"
    for row in first_step["rows"]:
        if row.get("axis") == "Brick":
            row["row_ref"] = f"brick-row:{building_id}-work"
            row["brick_work_ref"] = f"work:{building_id}-work"
            row["brick_instance_ref"] = f"brick-{building_id}-work"
            row["work_statement"] = "Adapter-error hardening fixture first step."
        if row.get("axis") == "Agent":
            row["row_ref"] = f"agent-row:{building_id}-work"
    followup = plan["brick_steps"][1]
    followup["step_ref"] = f"{building_id}-followup"
    followup["selected_adapter_ref"] = followup_adapter_ref
    followup["completion_edge_ref"] = f"edge:{building_id}-followup-to-boundary"
    for row in followup["rows"]:
        if row.get("axis") == "Brick":
            row["row_ref"] = f"brick-row:{building_id}-followup"
            row["brick_work_ref"] = f"work:{building_id}-followup"
            row["brick_instance_ref"] = f"brick-{building_id}-followup"
        if row.get("axis") == "Agent":
            row["row_ref"] = f"agent-row:{building_id}-followup"
    plan["execution_order"] = [first_step["step_ref"], followup["step_ref"]]
    plan["link_edges"] = [
        {
            "edge_ref": first_step["completion_edge_ref"],
            "source_step_ref": first_step["step_ref"],
            "target_step_ref": followup["step_ref"],
            "rows": [
                {
                    "axis": "Link",
                    "row_ref": f"link-row:{building_id}-work",
                    "movement": "forward",
                    "target_ref": f"brick-{building_id}-followup",
                }
            ],
        },
        {
            "edge_ref": followup["completion_edge_ref"],
            "source_step_ref": followup["step_ref"],
            "rows": [
                {
                    "axis": "Link",
                    "row_ref": f"link-row:{building_id}-followup",
                    "movement": "forward",
                    "target_ref": f"building-boundary:{building_id}-closed",
                }
            ],
        },
    ]
    return plan


def _persisted_adapter_error_hold_reason(root: Path) -> str:
    """Read the persisted dynamic_walker_evidence hold_reason from a held root.

    The adapter-error frontier write records the hold inside the evidence manifest
    plan snapshot (same location _rewrite_adapter_error_hold_as_legacy_reason_refs
    reads). This is the on-disk proof that the held frontier carries the
    adapter_error_frontier reason after the B2 typed-signal/return change.
    """

    manifest_path = root / "evidence" / "evidence-manifest.json"
    if not manifest_path.is_file():
        return ""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot = manifest.get("plan_snapshot") if isinstance(manifest, Mapping) else None
    if not isinstance(snapshot, Mapping):
        return ""
    plan_rows_copy = snapshot.get("plan_rows_copy")
    if not isinstance(plan_rows_copy, str):
        return ""
    plan_copy = json.loads(plan_rows_copy)
    if not isinstance(plan_copy, Mapping):
        return ""
    evidence = plan_copy.get("dynamic_walker_evidence")
    if not isinstance(evidence, Mapping):
        return ""
    hold = evidence.get("hold")
    if not isinstance(hold, Mapping):
        return ""
    return str(hold.get("hold_reason") or "")


def _write_adapter_error_frontier_fixture(
    run_module: Any,
    *,
    repo: Path,
    output_root: Path,
    building_id: str,
    first_adapter_ref: str = "adapter:codex-local",
    followup_adapter_ref: str = "adapter:local",
    local_callables: Mapping[str, Any] | None = None,
) -> None:
    root = output_root / building_id

    def failing_runner(
        args: Sequence[str],
        cwd: Path,
        timeout_seconds: int,
    ) -> Any:
        from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

        del cwd, timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        return LocalCliCompleted(call, 1, "", "adapter boom")

    # B2: the dynamic adapter exception now RETURNS a clean held result rather than
    # raising a bare RuntimeError. The seeded fixture root must still be a held
    # adapter-error frontier on disk.
    try:
        run_module.run_building_plan(
            _adapter_error_hardening_graph_plan(
                building_id,
                first_adapter_ref=first_adapter_ref,
                followup_adapter_ref=followup_adapter_ref,
            ),
            output_root=output_root,
            overwrite_existing=True,
            local_callables=local_callables,
            command_runner=failing_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=5,
        )
    except RuntimeError as exc:
        raise ProfileError(
            "adapter_error_path_hardening fixture: a dynamic adapter exception must "
            f"return a clean held result, not raise a bare RuntimeError ({exc!r})"
        ) from exc
    if not root.is_dir():
        raise ProfileError(f"adapter_error_path_hardening fixture root missing: {root}")
    if _persisted_adapter_error_hold_reason(root) != "adapter_error_frontier":
        raise ProfileError(
            "adapter_error_path_hardening fixture root is not a held adapter-error frontier"
        )


def _rewrite_adapter_error_hold_as_legacy_reason_refs(root: Path) -> None:
    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref

    manifest_path = root / "evidence" / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture manifest is not a mapping")
    snapshot_value = manifest.get("plan_snapshot")
    if not isinstance(snapshot_value, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture lacks plan_snapshot")
    snapshot = dict(snapshot_value)
    plan_rows_copy = snapshot.get("plan_rows_copy")
    if not isinstance(plan_rows_copy, str):
        raise ProfileError("adapter_error_path_hardening legacy fixture lacks plan_rows_copy")
    plan_copy = json.loads(plan_rows_copy)
    if not isinstance(plan_copy, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture plan copy is not a mapping")
    plan_dict = dict(plan_copy)
    evidence_value = plan_dict.get("dynamic_walker_evidence")
    if not isinstance(evidence_value, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture lacks dynamic evidence")
    evidence = dict(evidence_value)
    hold_value = evidence.get("hold")
    if not isinstance(hold_value, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture lacks hold record")
    legacy_hold = dict(hold_value)
    if legacy_hold.get("hold_reason") != "adapter_error_frontier":
        raise ProfileError("adapter_error_path_hardening legacy fixture source hold is not adapter-error")

    source_step_ref = str(legacy_hold.get("source_step_ref") or f"{root.name}-work")
    source_brick_ref = str(legacy_hold.get("source_brick_ref") or f"brick-{source_step_ref}")
    pending_target_ref = str(
        legacy_hold.get("pending_target_ref")
        or legacy_hold.get("target_brick")
        or source_brick_ref
    )
    attempt_number = legacy_hold.get("attempt_number")
    attempt = attempt_number if isinstance(attempt_number, int) and not isinstance(attempt_number, bool) else 1
    reason_refs = [
        f"observation:adapter-error-frontier:{source_step_ref}",
        "observation:reroute-hold-reason-adapter_error_frontier",
    ]
    legacy_hold.pop("hold_reason", None)
    legacy_hold["transition_lifecycle_reason_refs"] = list(reason_refs)
    evidence["hold"] = legacy_hold
    plan_dict["dynamic_walker_evidence"] = evidence
    snapshot["plan_rows_copy"] = json.dumps(
        plan_dict,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    manifest["plan_snapshot"] = snapshot
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    legacy_raw_ref = "raw:link-frontier:legacy-01"
    legacy_paused_at_ref = _hold_paused_at_ref(legacy_hold)
    legacy_row = {
        "@context": {
            "bp": "urn:bp:",
            "ce": "https://cloudevents.io/spec/v1.0/",
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@id": f"urn:bp:building:{root.name}::raw/link.jsonl#legacy-01",
        "adapter_error_ref": f"adapter-error:{source_step_ref}:attempt-{attempt}",
        "building_id": root.name,
        "datacontenttype": "application/json",
        "dataschema": "urn:bp:schema:graph-ready-v1",
        "frontier_kind": "agent_incomplete",
        "generatedAtTime": "2026-06-12T04:00:54Z",
        "id": f"urn:bp:building:{root.name}::raw/link.jsonl#legacy-01",
        "observed_boundary_ref": source_brick_ref,
        "raw_ref": legacy_raw_ref,
        "raw_refs": [legacy_raw_ref],
        "recorded_at": "2026-06-12T04:00:54Z",
        "schema_version": "graph-ready-v1",
        "source": f"urn:bp:building:{root.name}",
        "source_brick_instance_ref": source_brick_ref,
        "specversion": "1.0",
        "step_ref": source_step_ref,
        "subject": source_step_ref,
        "target_brick_instance_ref": pending_target_ref,
        "time": "2026-06-12T04:00:54Z",
        "transition_lifecycle_from_brick_ref": source_brick_ref,
        "transition_lifecycle_not_proven": [
            "semantic correctness of the agent-proposed reroute",
            "parallel runtime execution (P-walker-2 fan-in/fan-out out of scope here)",
            "scheduler / queue / retry behavior",
            "caller/COO disposition after a HOLD",
            "adapter:local resume probes only unless caller uses another adapter",
            "parallel runtime execution",
            "full process-integrity across resumed provider processes",
            "semantic correctness of the human/COO disposition",
        ],
        "transition_lifecycle_paused_at_ref": legacy_paused_at_ref,
        "transition_lifecycle_pending_target_ref": pending_target_ref,
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_proof_limits": [
            "support evidence only",
            "dynamic walker walks declared gate-adopted agent-proposed routes only",
            "support authors no route or Movement",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "transition_lifecycle_reason_refs": list(reason_refs),
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_state": "paused",
        "transition_record_created": False,
        "type": "bp.raw.link",
    }
    with (root / "raw" / "link.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(legacy_row, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + "\n"
        )


def _append_adapter_error_stop_disposition(root: Path) -> None:
    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref

    evidence_manifest = json.loads(
        (root / "evidence" / "evidence-manifest.json").read_text(encoding="utf-8")
    )
    plan_copy = json.loads(evidence_manifest["plan_snapshot"]["plan_rows_copy"])
    evidence = plan_copy["dynamic_walker_evidence"]
    hold_record = evidence["hold"]
    paused_at_ref = _hold_paused_at_ref(hold_record)
    raw_ref = "raw:link-disposition:01"
    row = {
        "raw_ref": raw_ref,
        "raw_refs": [raw_ref],
        "transition_author_ref": "human:adapter-error-hardening-checker",
        "transition_lifecycle_state": "resumed",
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_paused_at_ref": paused_at_ref,
        "transition_lifecycle_resumed_from_ref": paused_at_ref,
        "transition_lifecycle_pending_target_ref": hold_record["pending_target_ref"],
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_disposition_action": "stop",
        "transition_lifecycle_reason_refs": [
            f"checker:adapter-error-hardening:{root.name}:stop"
        ],
    }
    link_path = root / "raw" / "link.jsonl"
    with link_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")


def _assert_codex_ephemeral_env_dial(repo: Path) -> None:
    from brick_protocol.support.connection import agent_adapter
    from brick_protocol.support.connection.agent_adapter import (
        AgentAdapterRequest,
        LocalCliCompleted,
    )

    spec = agent_adapter._local_cli_spec("adapter:codex-local")
    request = AgentAdapterRequest(
        building_id="adapter-error-hardening-ephemeral",
        agent_object_ref="agent-object:dev",
        adapter_ref="adapter:codex-local",
        brick_instance_ref="brick-ephemeral",
        next_brick_instance_ref="building-boundary:ephemeral-closed",
        work_statement="Check codex ephemeral argv.",
        required_return_shape="made_changes, observed_evidence, not_proven",
    )

    def runner(args: Sequence[str], cwd: Path, timeout_seconds: int) -> LocalCliCompleted:
        del cwd, timeout_seconds
        call = tuple(str(arg) for arg in args)
        return LocalCliCompleted(
            call,
            0,
            json.dumps(
                {
                    "made_changes": [],
                    "observed_evidence": ["argv captured"],
                    "not_proven": ["provider behavior"],
                }
            ),
            "",
        )

    old = os.environ.get("BRICK_CODEX_EPHEMERAL")
    try:
        os.environ.pop("BRICK_CODEX_EPHEMERAL", None)
        absent = agent_adapter._invoke_local_cli(
            spec,
            request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=runner,
        )
        if "--ephemeral" in absent.args:
            raise ProfileError("BRICK_CODEX_EPHEMERAL absent still emitted --ephemeral")
        os.environ["BRICK_CODEX_EPHEMERAL"] = "1"
        enabled = agent_adapter._invoke_local_cli(
            spec,
            request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=runner,
        )
        if "--ephemeral" not in enabled.args:
            raise ProfileError("BRICK_CODEX_EPHEMERAL=1 did not emit --ephemeral")
    finally:
        if old is None:
            os.environ.pop("BRICK_CODEX_EPHEMERAL", None)
        else:
            os.environ["BRICK_CODEX_EPHEMERAL"] = old


def _hardening_local_brain(request: Any) -> Mapping[str, Any]:
    from brick_protocol.brick.work import parse_required_return_shape

    returned: dict[str, Any] = {}
    for label in parse_required_return_shape(request.required_return_shape):
        if label == "made_changes":
            returned[label] = ["adapter-error hardening local fixture"]
        elif label == "observed_evidence":
            returned[label] = [f"observed {request.brick_instance_ref}"]
        elif label == "not_proven":
            returned[label] = ["semantic correctness of fixture work"]
        elif label == "adapter_ref":
            returned[label] = request.adapter_ref
        elif label == "returned_summary":
            returned[label] = "adapter-error hardening local return"
        else:
            returned[label] = f"fixture value for {label}"
    return returned


def _adapter_error_manifest_write_broken_fixture(root: Path) -> None:
    case_id = root.name
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "brick-work.jsonl",
        [{"raw_ref": "raw:brick:01", "raw_refs": ["raw:brick:01"], "step_ref": f"{case_id}-work"}],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "agent-return.jsonl",
        [{"raw_ref": "raw:agent:01", "raw_refs": ["raw:agent:01"], "step_ref": f"{case_id}-work"}],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "agent-received.jsonl",
        [
            {
                "agent_object_ref": "agent-object:coo",
                "raw_ref": "raw:agent-received:02",
                "raw_refs": ["raw:agent-received:02"],
                "received_work_ref": f"brick-work:02:{case_id}-closure",
                "step_ref": f"{case_id}-closure",
            }
        ],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "adapter-error.jsonl",
        [
            {
                "adapter_error_ref": f"adapter-error:{case_id}-closure:attempt-1",
                "agent_fact_created": False,
                "brick_instance_ref": f"brick-{case_id}-closure",
                "raw_ref": "raw:adapter-error:02",
                "raw_refs": ["raw:adapter-error:02"],
                "step_ref": f"{case_id}-closure",
            }
        ],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "link.jsonl",
        [{"raw_ref": "raw:link:01", "raw_refs": ["raw:link:01"], "step_ref": f"{case_id}-work"}],
    )
    _adapter_error_manifest_write_json(
        root / "raw" / "raw-manifest.json",
        {
            "building_id": case_id,
            "raw_refs": ["raw:brick:01", "raw:agent:01", "raw:link:01"],
            "entries": [
                _adapter_error_manifest_entry("raw/brick-work.jsonl", "Brick", ["raw:brick:01"]),
                _adapter_error_manifest_entry("raw/agent-return.jsonl", "Agent", ["raw:agent:01"]),
                _adapter_error_manifest_entry("raw/link.jsonl", "Link", ["raw:link:01"]),
            ],
        },
    )
    _adapter_error_manifest_write_json(
        root / "evidence" / "evidence-manifest.json",
        {"building_id": case_id, "proof_limits": ["support evidence only"]},
    )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "brick" / "work_contract.json",
        "Brick",
        "brick-work:01",
        "raw:brick:01",
        {"work_statement": "fixture work"},
    )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "agent" / "returned_claims.json",
        "Agent",
        "agent-fact:01",
        "raw:agent:01",
        {"received_work": "brick-work:01", "returned_payload_ref": "fixture:return"},
    )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "agent" / "receipt_trace.json",
        "Agent",
        "agent-receipt:02",
        "raw:agent-received:02",
        {"receipt_role": "Agent received declared work before adapter exception observation"},
    )
    for rel, fact_ref, raw_ref in (
        ("transfer_trace.json", "link-transfer:01", "raw:link:01"),
        ("carry_trace.json", "link-carry:01", "raw:link:01"),
        ("sufficiency_trace.json", "link-sufficiency:01", "raw:link:01"),
        ("movement_trace.json", "link-movement:01", "raw:link:01"),
        ("frontier_trace.json", "link-frontier:02", "raw:link-frontier:02"),
    ):
        _adapter_error_manifest_write_claim(
            root / "evidence" / "claim_trace" / "link" / rel,
            "Link",
            fact_ref,
            raw_ref,
            {"frontier_kind": "agent_incomplete"} if rel == "frontier_trace.json" else {"link_ref": fact_ref},
        )


def _adapter_error_manifest_link_frontier_record(case_id: str) -> dict[str, Any]:
    return {
        "adapter_error_ref": f"adapter-error:{case_id}-closure:attempt-1",
        "frontier_kind": "agent_incomplete",
        "observed_boundary_ref": f"brick-{case_id}-closure",
        "raw_ref": "raw:link-frontier:02",
        "raw_refs": ["raw:link-frontier:02"],
        "step_ref": f"{case_id}-closure",
        "transition_record_created": False,
    }


def _adapter_error_manifest_entry(path: str, axis_owner: str, raw_refs: Sequence[str]) -> dict[str, Any]:
    return {
        "path": path,
        "source": "support/checkers synthetic fixture",
        "content_shape": "jsonl fixture rows",
        "proof_limit": "support evidence only",
        "axis_owner": axis_owner,
        "record_role": "primary",
        "raw_refs": list(raw_refs),
    }


def _adapter_error_manifest_write_claim(
    path: Path,
    axis: str,
    fact_ref: str,
    raw_ref: str,
    fact: Mapping[str, Any],
) -> None:
    _adapter_error_manifest_write_json(
        path,
        {
            "facts": [
                {
                    "axis": axis,
                    "fact": dict(fact),
                    "fact_ref": fact_ref,
                    "raw_refs": [raw_ref],
                    "proof_limits": ["support evidence only"],
                    "not_proven": ["checker fixture only"],
                }
            ]
        },
    )


def _adapter_error_manifest_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _adapter_error_manifest_write_jsonl(path: Path, values: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
            for value in values
        ),
        encoding="utf-8",
    )


def run_chat_session_park_seam(repo: Path) -> KernelResult:
    """Exercise the chat-session PARK/CLAIM/SUBMIT/RESUME seam over temp roots.

    This is support-checker evidence only. It proves the runner writes the
    support records, admits passive claim/submission, and resumes through the
    graph walker; it does not prove provider quality or reader behavior.
    """

    from support.checkers import check_building_lifecycle_path_shape as lifecycle_shape
    from support.checkers import check_package_path_admission as path_admission
    from support.operator import run as run_module
    from support.operator import (
        dashboard_export,
        frontier_observation,
        ledger_projection,
        progress_projection,
    )

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-chat-session-park-seam-") as tmpdir:
        temp_repo = Path(tmpdir) / "repo"
        buildings_root = temp_repo / "project" / "brick-protocol" / "buildings"
        buildings_root.mkdir(parents=True)
        _chat_session_write_temp_project_declaration(temp_repo)
        shutil.copytree(
            repo / "agent",
            temp_repo / "agent",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        _chat_session_assert_declared_adapter_capability(temp_repo)
        _chat_session_assert_undeclared_adapter_rejects(
            run_module,
            buildings_root=buildings_root,
            temp_repo=temp_repo,
        )
        inspected += 2
        _chat_session_assert_non_graph_plan_rejects(
            run_module,
            buildings_root=buildings_root,
            temp_repo=temp_repo,
        )
        inspected += 1
        dynamic_root, dynamic_written = _chat_session_drive_park(
            run_module,
            _chat_session_park_graph_plan(),
            buildings_root=buildings_root,
            temp_repo=temp_repo,
            label="dynamic",
        )
        no_claim_root, _no_claim_written = _chat_session_drive_park(
            run_module,
            _chat_session_park_graph_plan(building_id="chat-session-park-no-claim-case"),
            buildings_root=buildings_root,
            temp_repo=temp_repo,
            label="no-claim",
        )
        inspected += 2
        inspected += _chat_session_assert_park_evidence(
            dynamic_root,
            written_files=dynamic_written,
            temp_repo=temp_repo,
            label="dynamic",
        )
        inspected += _chat_session_assert_park_evidence(
            no_claim_root,
            written_files=_no_claim_written,
            temp_repo=temp_repo,
            label="no-claim",
        )

        _chat_session_assert_resume_rejects(
            run_module,
            no_claim_root,
            temp_repo=temp_repo,
            expected="parked building resume requires active chat-session claim",
            label="parked no claim",
        )
        claim = run_module.claim_chat_session_envelope(
            dynamic_root,
            lane_ref="lane:checker",
        )
        token = str(claim.get("claim_token") or "")
        if not re.fullmatch(r"[a-z]+(?:-[a-z]+){3,7}", token):
            raise ProfileError(f"chat_session_park_seam minted non-word token: {token!r}")
        if _SESSION_ID_UUID_RE.search(token) or _SESSION_ID_ULID_RE.search(token):
            raise ProfileError(f"chat_session_park_seam minted session-shaped token: {token!r}")
        uuid_probe = _chat_session_probe_uuid_text()
        ulid_probe = _chat_session_probe_ulid_text()
        _chat_session_assert_second_claim_rejects(run_module, dynamic_root)
        _chat_session_assert_resume_rejects(
            run_module,
            dynamic_root,
            temp_repo=temp_repo,
            expected="parked building resume requires chat-session submission",
            label="claim no submission",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={"status": "done", "observed_evidence": ["bad"]},
            expected="forbidden key 'status'",
            label="forbidden status key",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token="amber-basil-cedar-copper" if token != "amber-basil-cedar-copper" else "amber-basil-cedar-delta",
            returned={
                "made_changes": ["wrong token"],
                "observed_evidence": ["wrong token"],
                "not_proven": ["not resumed"],
            },
            expected="claim_token does not match",
            label="token mismatch",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                "made_changes": ["uuid negative"],
                "observed_evidence": [uuid_probe],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="uuid-shaped submitted text",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                uuid_probe: "session-shaped key must be rejected",
                "made_changes": ["uuid key negative"],
                "observed_evidence": ["ordinary value"],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="uuid-shaped submitted key",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                ulid_probe: "session-shaped key must be rejected",
                "made_changes": ["ulid key negative"],
                "observed_evidence": ["ordinary value"],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="ulid-shaped submitted key",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                "made_changes": ["nested key negative"],
                "observed_evidence": [{"outer": [{"ordinary": "value"}, {uuid_probe: "blocked"}]}],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="nested submitted key",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                "made_changes": ["nested value negative"],
                "observed_evidence": [{"outer": ["ordinary", {"inner": ulid_probe}]}],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="nested submitted value",
        )
        _chat_session_assert_envelope_session_key_rejects(uuid_probe)
        fire_buildings_root = temp_repo / "project" / "brick-protocol" / "chat-session-fire-buildings"
        fire_buildings_root.mkdir(parents=True)
        _chat_session_assert_key_scan_fire(
            run_module,
            buildings_root=fire_buildings_root,
            temp_repo=temp_repo,
            uuid_probe=uuid_probe,
        )
        submitted = run_module.submit_chat_session_return(
            dynamic_root,
            claim_token=token,
            returned={
                "made_changes": ["checker wrote passive submission"],
                "observed_evidence": ["claim token matched and payload stayed passive"],
                "task-source": "ordinary hyphenated key accepted",
                "not_proven": ["provider quality", "semantic correctness"],
            },
        )
        if submitted.get("returned", {}).get("observed_evidence") != [
            "claim token matched and payload stayed passive"
        ]:
            raise ProfileError("chat_session_park_seam submission returned payload drifted")
        before_resume = frontier_observation.observe_building_frontier(
            dynamic_root,
            repo_root=temp_repo,
        )
        if before_resume.get("frontier_kind") != "chat_session_parked":
            raise ProfileError(
                "chat_session_park_seam passive submission triggered frontier movement: "
                f"{before_resume.get('frontier_kind')!r}"
            )
        if (dynamic_root / "raw" / "agent-return.jsonl").exists():
            raise ProfileError("chat_session_park_seam passive submission wrote agent-return evidence")
        original_runner_repo = run_module._REPO_ROOT
        try:
            run_module._REPO_ROOT = temp_repo
            resumed = run_module.resume_building_plan(dynamic_root, overwrite_existing=True)
        finally:
            run_module._REPO_ROOT = original_runner_repo
        if len(resumed.step_results) != 2:
            raise ProfileError(
                "chat_session_park_seam expected resumed graph to close chat step plus "
                f"follow-up step, observed {len(resumed.step_results)}"
            )
        if resumed.step_results[0].adapter_result.returned_value != submitted.get("returned"):
            raise ProfileError("chat_session_park_seam chat step did not consume submitted return")
        if resumed.step_results[1].adapter_result.request.adapter_ref != "adapter:local":
            raise ProfileError("chat_session_park_seam follow-up step did not run live adapter:local")
        after_resume = frontier_observation.observe_building_frontier(
            dynamic_root,
            repo_root=temp_repo,
        )
        if after_resume.get("frontier_kind") != "complete":
            raise ProfileError(
                "chat_session_park_seam resumed Building did not observe complete frontier: "
                f"{after_resume.get('frontier_kind')!r}"
            )
        inspected += 17

        paths = lifecycle_shape.collect_directory_paths(buildings_root)
        lifecycle_violations = _chat_session_lifecycle_violations(buildings_root)
        if lifecycle_violations:
            raise ProfileError(
                "chat_session_park_seam lifecycle checker rejected generated evidence:\n"
                + "\n".join(f"- {violation}" for violation in lifecycle_violations)
            )
        path_violations = path_admission.check_paths(paths)
        if path_violations:
            raise ProfileError(
                "chat_session_park_seam package path admission rejected generated evidence:\n"
                + "\n".join(f"- {violation}" for violation in path_violations)
            )
        inspected += len(paths)

        board_state = ledger_projection._project_ledger_board_state("chat_session_parked")
        if board_state != "waiting_review":
            raise ProfileError(
                "chat_session_park_seam ledger board_state mapping is not the closed "
                f"waiting-review family: {board_state!r}"
            )
        dashboard = dashboard_export.dashboard_export_packet(repo_root=temp_repo)
        parked_dashboard_rows = [
            row
            for row in dashboard.get("buildings", [])
            if isinstance(row, Mapping) and row.get("frontier") == "chat_session_parked"
        ]
        if len(parked_dashboard_rows) != 1:
            raise ProfileError(
                "chat_session_park_seam dashboard_export did not project the remaining parked "
                f"Buildings, observed {len(parked_dashboard_rows)}"
            )
        for row in parked_dashboard_rows:
            if row.get("state") != "waiting_review" or row.get("disp") != "review":
                raise ProfileError(
                    "chat_session_park_seam dashboard_export did not show parked "
                    f"Building in review/waiting family: state={row.get('state')!r} "
                    f"disp={row.get('disp')!r}"
                )
        progress = progress_projection.render_project_progress(
            "project:brick-protocol",
            repo_root=temp_repo,
        )
        if "- waiting_review: 1" not in progress:
            raise ProfileError(
                "chat_session_park_seam PROGRESS projection did not count parked "
                "Buildings under waiting_review"
            )
        inspected += 3

        _chat_session_assert_mutated_lifecycle_rejects(
            no_claim_root,
            "envelope session-like identifier",
            lambda root: _chat_session_mutate_envelope_uuid(root),
        )
        _chat_session_assert_mutated_lifecycle_rejects(
            no_claim_root,
            "adapter-error-shaped park record",
            lambda root: _chat_session_mutate_park_as_adapter_error(root),
        )
        _chat_session_assert_mutated_lifecycle_rejects(
            no_claim_root,
            "missing work-envelope path",
            lambda root: _chat_session_delete_work_envelope(root),
        )
        _chat_session_assert_mutated_lifecycle_rejects(
            dynamic_root,
            "submission forbidden returned key",
            lambda root: _chat_session_mutate_submission_forbidden_key(root),
        )
        _chat_session_assert_mutated_lifecycle_rejects(
            dynamic_root,
            "submission token mismatch",
            lambda root: _chat_session_mutate_submission_token(root),
        )
        inspected += 5

    return KernelResult(
        check_id="chat_session_park_seam",
        inspected=inspected,
        output=(
            "chat-session S2/S3 seam passed: non-graph plans rejected by the "
            "dynamic graph walker guard, "
            "dynamic graph park wrote work-envelope.json + parked.json + raw park evidence, "
            "atomic claim minted a word-form token and second claim rejected, no-claim/"
            "no-submission/token-mismatch/forbidden-key/session-id value/key/nested "
            "submissions and session-shaped envelope keys rejected "
            "before resume, passive submission did not compute gates, resume consumed "
            "the submitted return, replayed through the graph walker, ran the next "
            "adapter:local step, lifecycle/path checks accepted claim.json and "
            "submission.json, dashboard/PROGRESS kept only the unsubmitted parked "
            "Building in waiting_review, and mutated claim/submission/path negatives fired RED."
        ),
    )


_DASHBOARD_PRODUCTIZATION_TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".mjs",
    ".yml",
    ".yaml",
}
_DASHBOARD_PRODUCTIZATION_SKIP_PARTS = {"dist", "node_modules"}
_DASHBOARD_PRODUCTIZATION_SKIP_RELATIVES = {
    "support/dashboard/package-lock.json",
    "support/dashboard/public/dashboard-data.json",
}
_DASHBOARD_PUBLIC_DATA_RELATIVE = "support/dashboard/public/dashboard-data.json"
_DASHBOARD_ALLOWED_URL_PREFIXES = (
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
    "http://brick_dashboard_upstream",
)
_DASHBOARD_ABSOLUTE_URL_RE = re.compile(r"https?://[^\s`'\"<>]+")
_DASHBOARD_PROJECT_FLAG_RE = re.compile(r"--project(?:=|\s+)(?P<value>[\"']?[^\s\\]+)")
_DASHBOARD_ARTIFACT_IMAGE_RE = re.compile(
    r"\b[A-Za-z0-9-]+-docker\.pkg\.dev/(?P<project>[^/\s`'\"<>]+)/"
)
_DASHBOARD_RESOURCE_PROJECT_RE = re.compile(r"\bprojects/(?P<project>[^/\s`'\"<>]+)/")
_DASHBOARD_ORG_RE = re.compile(r"\borganizations/[0-9]{4,}\b")
_DASHBOARD_USER_HOME_RE = re.compile(r"/Users/[^\s`'\"]+")


def _dashboard_placeholder_value(value: str) -> bool:
    cleaned = value.strip().strip("'\"").strip(",;")
    return (
        not cleaned
        or cleaned.startswith("$")
        or cleaned.startswith("<")
        or cleaned.startswith("{")
        or "${" in cleaned
        or cleaned.isupper()
    )


def _dashboard_url_allowed(value: str) -> bool:
    cleaned = value.strip().rstrip(".,);")
    return cleaned.startswith(_DASHBOARD_ALLOWED_URL_PREFIXES) or "${" in cleaned or "<" in cleaned


def _dashboard_productization_server_violations(text: str) -> list[str]:
    required_snippets = {
        "production env branch": "const IS_PRODUCTION = process.env.NODE_ENV === 'production'",
        "raw env-only ingest value": "const RAW_INGEST_SECRET = process.env.INGEST_SECRET",
        "normalized ingest env": "const NORMALIZED_INGEST_SECRET = RAW_INGEST_SECRET && RAW_INGEST_SECRET.trim()",
        "production dev fallback reject": "IS_PRODUCTION && (!NORMALIZED_INGEST_SECRET || NORMALIZED_INGEST_SECRET === 'dev-secret')",
        "fail-closed helper": "function ingestRefusesInProduction()",
        "POST fail-closed guard": "if (ingestRefusesInProduction())",
        "header comparison": "req.headers['x-ingest-secret'] !== INGEST_SECRET",
    }
    violations = [
        f"server/index.mjs missing {label}: {snippet!r}"
        for label, snippet in required_snippets.items()
        if snippet not in text
    ]
    post_marker = "if (url === '/ingest' && req.method === 'POST')"
    fail_guard = "if (ingestRefusesInProduction())"
    header_guard = "if (req.headers['x-ingest-secret'] !== INGEST_SECRET)"
    try:
        post_idx = text.index(post_marker)
        fail_idx = text.index(fail_guard, post_idx)
        header_idx = text.index(header_guard, post_idx)
    except ValueError:
        return violations
    if not (post_idx < fail_idx < header_idx):
        violations.append("server/index.mjs POST /ingest fail-closed guard must run before header comparison")
    if "process.env.INGEST_SECRET || 'dev-secret'" in text:
        violations.append("server/index.mjs must not default directly from process.env.INGEST_SECRET to dev-secret")
    return violations


def _dashboard_productization_validate_server_text(text: str) -> None:
    violations = _dashboard_productization_server_violations(text)
    if violations:
        raise ProfileError(
            "dashboard_productization_projection server lint rejected evidence:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )


def _dashboard_productization_assert_mutated_server_rejects(text: str) -> int:
    mutations: tuple[tuple[str, Callable[[str], str]], ...] = (
        (
            "missing dev fallback rejection",
            lambda source: source.replace(
                "NORMALIZED_INGEST_SECRET === 'dev-secret'",
                "false",
                1,
            ),
        ),
        (
            "POST guard disabled",
            lambda source: source.replace(
                "if (ingestRefusesInProduction())",
                "if (false)",
                1,
            ),
        ),
    )
    inspected = 0
    for label, mutate in mutations:
        inspected += 1
        mutated = mutate(text)
        if mutated == text:
            raise ProfileError(f"dashboard_productization_projection mutation did not apply: {label}")
        if not _dashboard_productization_server_violations(mutated):
            raise ProfileError(
                "dashboard_productization_projection FIRE probe did NOT fire for "
                f"mutated server copy: {label}"
            )
    return inspected


def _dashboard_productization_text_paths(repo: Path) -> list[Path]:
    root = repo / "support" / "dashboard"
    paths: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = to_posix(path.relative_to(repo))
        if any(part in _DASHBOARD_PRODUCTIZATION_SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        if rel in _DASHBOARD_PRODUCTIZATION_SKIP_RELATIVES:
            continue
        if path.suffix in _DASHBOARD_PRODUCTIZATION_TEXT_SUFFIXES or path.name.startswith("."):
            paths.append(path)
    return paths


def _dashboard_productization_forbidden_literal_violations(repo: Path) -> tuple[list[str], int]:
    violations: list[str] = []
    inspected = 0
    for path in _dashboard_productization_text_paths(repo):
        rel = to_posix(path.relative_to(repo))
        text = path.read_text(encoding="utf-8")
        inspected += 1
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in _DASHBOARD_ABSOLUTE_URL_RE.finditer(line):
                if not _dashboard_url_allowed(match.group(0)):
                    violations.append(f"{rel}:{lineno}: hardcoded absolute URL literal: {match.group(0)!r}")
            for match in _DASHBOARD_PROJECT_FLAG_RE.finditer(line):
                value = match.group("value")
                if not _dashboard_placeholder_value(value):
                    violations.append(f"{rel}:{lineno}: hardcoded --project value: {value!r}")
            for match in _DASHBOARD_ARTIFACT_IMAGE_RE.finditer(line):
                project = match.group("project")
                if not _dashboard_placeholder_value(project):
                    violations.append(f"{rel}:{lineno}: hardcoded Artifact Registry project segment: {project!r}")
            for match in _DASHBOARD_RESOURCE_PROJECT_RE.finditer(line):
                project = match.group("project")
                if not _dashboard_placeholder_value(project):
                    violations.append(f"{rel}:{lineno}: hardcoded resource project segment: {project!r}")
            if _DASHBOARD_ORG_RE.search(line):
                violations.append(f"{rel}:{lineno}: hardcoded organization literal")
            if _DASHBOARD_USER_HOME_RE.search(line):
                violations.append(f"{rel}:{lineno}: hardcoded user-home path literal")
    return violations, inspected


def _dashboard_productization_assert_literal_fire_probe() -> int:
    probe_dir = Path("support/dashboard/DEPLOY.md")
    probe_lines = {
        "absolute-url": "gcloud run services describe --format='value(status.url)' https://service-hash-region.a.run.app",
        "project-flag": "gcloud run deploy service --project hardcoded-project",
        "artifact-project": "IMAGE=us-docker.pkg.dev/hardcoded-project/repo/service:tag",
        "resource-project": "projects/hardcoded-project/locations/region/services/service",
        "organization": "organizations/1234567890",
        "user-home": "/Users/smith/project",
    }
    inspected = 0
    for label, line in probe_lines.items():
        inspected += 1
        with tempfile.TemporaryDirectory(prefix="bp-dashboard-literal-fire-") as tmp:
            probe_repo = Path(tmp)
            target = probe_repo / probe_dir
            target.parent.mkdir(parents=True)
            target.write_text(line + "\n", encoding="utf-8")
            violations, _ = _dashboard_productization_forbidden_literal_violations(probe_repo)
            if not violations:
                raise ProfileError(
                    "dashboard_productization_projection literal FIRE probe did "
                    f"NOT fire for {label}: {line!r}"
                )
    return inspected


def _dashboard_productization_assert_bake_shape_probe(repo: Path) -> int:
    from support.operator import dashboard_export

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-dashboard-bake-") as tmp:
        out_path = Path(tmp) / "dashboard-data.json"
        observation = dashboard_export.bake_dashboard_data_json(repo_root=repo, out_path=out_path)
        packet = json.loads(out_path.read_text(encoding="utf-8"))
        inspected += 1
        if observation.get("source_truth") is not False or packet.get("source_truth") is not False:
            raise ProfileError("dashboard bake probe wrote a source_truth true/non-false packet")
        if not isinstance(packet.get("buildings"), list):
            raise ProfileError("dashboard bake probe wrote a packet without a buildings list")
        if observation.get("buildings") != len(packet.get("buildings", [])):
            raise ProfileError("dashboard bake probe observation did not match written buildings length")

        original = dashboard_export.dashboard_export_packet

        def bad_packet(**_: Any) -> Mapping[str, Any]:
            return {"source_truth": True, "buildings": []}

        dashboard_export.dashboard_export_packet = bad_packet
        try:
            try:
                dashboard_export.bake_dashboard_data_json(repo_root=repo, out_path=out_path)
            except ValueError as exc:
                if "source_truth" not in str(exc):
                    raise ProfileError(
                        "dashboard bake FIRE probe rejected bad packet for the wrong reason: "
                        f"{exc}"
                    ) from exc
            else:
                raise ProfileError(
                    "dashboard bake FIRE probe did NOT reject a mutated source_truth true packet"
                )
        finally:
            dashboard_export.dashboard_export_packet = original
        inspected += 1
    return inspected


def _dashboard_productization_validate_public_seed_packet(packet: Any, *, label: str) -> None:
    if not isinstance(packet, Mapping):
        raise ProfileError(f"dashboard public seed {label} must be a JSON object")
    if packet.get("source_truth") is not False:
        raise ProfileError(f"dashboard public seed {label} source_truth must be false")
    if not isinstance(packet.get("buildings"), list):
        raise ProfileError(f"dashboard public seed {label} must carry a buildings list")


def _dashboard_productization_public_seed_observation(repo: Path) -> tuple[int, str]:
    seed_path = repo / _DASHBOARD_PUBLIC_DATA_RELATIVE
    if not seed_path.exists():
        return (
            0,
            f"{_DASHBOARD_PUBLIC_DATA_RELATIVE} absent; static dashboard seed validation skipped as generated-artifact advisory.",
        )
    try:
        packet = json.loads(seed_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileError(
            f"dashboard public seed {to_posix(seed_path.relative_to(repo))} is invalid JSON: {exc}"
        ) from exc
    _dashboard_productization_validate_public_seed_packet(
        packet,
        label=to_posix(seed_path.relative_to(repo)),
    )
    return (1, f"{_DASHBOARD_PUBLIC_DATA_RELATIVE} present; static dashboard seed shape validated.")


def _dashboard_productization_assert_public_seed_optional_probe() -> int:
    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-dashboard-seed-optional-") as tmp:
        probe_repo = Path(tmp)
        missing_inspected, missing_observation = _dashboard_productization_public_seed_observation(probe_repo)
        inspected += 1
        if missing_inspected != 0 or "absent" not in missing_observation:
            raise ProfileError("dashboard public seed absent probe did not skip as advisory")

        seed_path = probe_repo / _DASHBOARD_PUBLIC_DATA_RELATIVE
        seed_path.parent.mkdir(parents=True)
        seed_path.write_text(
            json.dumps({"source_truth": False, "buildings": []}) + "\n",
            encoding="utf-8",
        )
        present_inspected, _ = _dashboard_productization_public_seed_observation(probe_repo)
        inspected += present_inspected
        if present_inspected != 1:
            raise ProfileError("dashboard public seed present probe did not inspect the seed")

        seed_path.write_text(
            json.dumps({"source_truth": True, "buildings": []}) + "\n",
            encoding="utf-8",
        )
        try:
            _dashboard_productization_public_seed_observation(probe_repo)
        except ProfileError:
            inspected += 1
        else:
            raise ProfileError("dashboard public seed FIRE probe did NOT fire for source_truth true")

        seed_path.write_text(
            json.dumps({"source_truth": False, "buildings": {}}) + "\n",
            encoding="utf-8",
        )
        try:
            _dashboard_productization_public_seed_observation(probe_repo)
        except ProfileError:
            inspected += 1
        else:
            raise ProfileError("dashboard public seed FIRE probe did NOT fire for non-list buildings")
    return inspected


def _dashboard_productization_captured_dashboard_request(
    report_sinks: Any,
    env: Mapping[str, str],
) -> urllib.request.Request:
    captured: list[urllib.request.Request] = []

    def capture_sender(request: urllib.request.Request, timeout_seconds: float) -> tuple[int, bytes]:
        if timeout_seconds <= 0:
            raise ProfileError("dashboard IAP passport probe received non-positive timeout")
        captured.append(request)
        return (200, b'{"ok":true}')

    presence = report_sinks._dashboard_environment_presence(env)
    observation = report_sinks._post_dashboard_projection(
        {"source_truth": False, "probe": "dashboard-iap-passport"},
        url=env[report_sinks.DASHBOARD_INGEST_URL_ENV],
        secret=env[report_sinks.DASHBOARD_INGEST_SECRET_ENV],
        packet_ref="dashboard-iap-passport-probe",
        proof_limits=("dashboard IAP passport offline checker probe only",),
        environment_presence=presence,
        env=env,
        timeout_seconds=1.0,
        sender=capture_sender,
    )
    if observation.delivery_status_class != "http_2xx":
        raise ProfileError("dashboard IAP passport probe did not observe captured http_2xx")
    if observation.environment_presence != presence:
        raise ProfileError("dashboard IAP passport probe did not preserve env presence-only packet")
    if len(captured) != 1:
        raise ProfileError(f"dashboard IAP passport probe expected one captured request, observed {len(captured)}")
    return captured[0]


def _dashboard_productization_request_headers(request: urllib.request.Request) -> Mapping[str, str]:
    return {key.lower(): value for key, value in request.header_items()}


def _dashboard_productization_decode_jwt_segment(segment: str) -> Mapping[str, Any]:
    padding = "=" * (-len(segment) % 4)
    decoded = json.loads(base64.urlsafe_b64decode((segment + padding).encode("ascii")).decode("utf-8"))
    if not isinstance(decoded, Mapping):
        raise ProfileError("dashboard IAP passport JWT segment did not decode to an object")
    return decoded


def _dashboard_productization_assert_authorization_header(
    headers: Mapping[str, str],
    *,
    expected_kid: str,
    expected_audience: str,
) -> None:
    authorization = headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise ProfileError("dashboard IAP passport probe missing Bearer Authorization header")
    token = authorization.removeprefix("Bearer ")
    segments = token.split(".")
    if len(segments) != 3 or any(not segment for segment in segments):
        raise ProfileError("dashboard IAP passport JWT must have three non-empty dot segments")
    header = _dashboard_productization_decode_jwt_segment(segments[0])
    claims = _dashboard_productization_decode_jwt_segment(segments[1])
    if header.get("kid") != expected_kid:
        raise ProfileError("dashboard IAP passport JWT header kid did not match throwaway key id")
    if header.get("alg") != "RS256" or header.get("typ") != "JWT":
        raise ProfileError("dashboard IAP passport JWT header must be RS256 JWT")
    if claims.get("aud") != expected_audience:
        raise ProfileError("dashboard IAP passport JWT audience did not match exact ingest URL")
    if claims.get("iss") != claims.get("sub") or claims.get("iss") != claims.get("email"):
        raise ProfileError("dashboard IAP passport JWT iss/sub/email claims must match")
    if not isinstance(claims.get("iat"), int) or not isinstance(claims.get("exp"), int):
        raise ProfileError("dashboard IAP passport JWT iat/exp claims must be integer seconds")
    if claims["exp"] - claims["iat"] != 600:
        raise ProfileError("dashboard IAP passport JWT expiration must be iat+600")


def _dashboard_productization_assert_absent_passport_headers(headers: Mapping[str, str]) -> None:
    expected = {
        "content-type": "application/json; charset=utf-8",
        "x-ingest-secret": "probe-secret",
    }
    if headers != expected:
        raise ProfileError(
            "dashboard IAP passport absent-env headers drifted from legacy header set: "
            f"{sorted(headers)}"
        )


def _dashboard_productization_throwaway_sa_env(report_sinks: Any, root: Path) -> tuple[Mapping[str, str], str, str]:
    private_key_path = root / "throwaway-dashboard-iap.pem"
    key_json_path = root / "throwaway-dashboard-iap.json"
    generated = subprocess.run(
        ["openssl", "genrsa", "-out", str(private_key_path), "2048"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if generated.returncode != 0:
        raise ProfileError("dashboard IAP passport probe could not generate throwaway RSA key")
    private_key = private_key_path.read_text(encoding="utf-8")
    key_id = "throwaway-dashboard-iap-kid"
    client_email = "dashboard-iap-passport-probe@example.invalid"
    key_json_path.write_text(
        json.dumps(
            {
                "client_email": client_email,
                "private_key_id": key_id,
                "private_key": private_key,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    ingest_url = "https://brick-dashboard-probe.example.invalid/ingest"
    env = {
        report_sinks.DASHBOARD_INGEST_URL_ENV: ingest_url,
        report_sinks.DASHBOARD_INGEST_SECRET_ENV: "probe-secret",
        report_sinks.DASHBOARD_SA_KEY_PATH_ENV: str(key_json_path),
    }
    return env, key_id, ingest_url


def _dashboard_productization_assert_iap_passport_probe() -> int:
    from support.operator import report_sinks

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-dashboard-iap-passport-") as tmp:
        env, key_id, ingest_url = _dashboard_productization_throwaway_sa_env(report_sinks, Path(tmp))

        request = _dashboard_productization_captured_dashboard_request(report_sinks, env)
        headers = _dashboard_productization_request_headers(request)
        _dashboard_productization_assert_authorization_header(
            headers,
            expected_kid=key_id,
            expected_audience=ingest_url,
        )
        inspected += 1

        absent_env = {
            report_sinks.DASHBOARD_INGEST_URL_ENV: ingest_url,
            report_sinks.DASHBOARD_INGEST_SECRET_ENV: "probe-secret",
        }
        absent_request = _dashboard_productization_captured_dashboard_request(report_sinks, absent_env)
        _dashboard_productization_assert_absent_passport_headers(
            _dashboard_productization_request_headers(absent_request)
        )
        inspected += 1

        original_authorization = report_sinks._dashboard_iap_authorization_header

        def removed_authorization(audience: str, env: Mapping[str, str]) -> str:
            return ""

        report_sinks._dashboard_iap_authorization_header = removed_authorization
        try:
            mutated_request = _dashboard_productization_captured_dashboard_request(report_sinks, env)
            mutated_headers = _dashboard_productization_request_headers(mutated_request)
            if mutated_headers.get("authorization") == headers.get("authorization"):
                raise ProfileError("dashboard IAP passport mutation did not alter Authorization attachment")
            try:
                _dashboard_productization_assert_authorization_header(
                    mutated_headers,
                    expected_kid=key_id,
                    expected_audience=ingest_url,
                )
            except ProfileError:
                inspected += 1
            else:
                raise ProfileError("dashboard IAP passport FIRE probe did NOT fire when Authorization was removed")
        finally:
            report_sinks._dashboard_iap_authorization_header = original_authorization
    return inspected


def _dashboard_productization_assert_openssl_subprocess_scope(repo: Path) -> int:
    report_sinks_path = repo / "support/operator/report_sinks.py"
    tree = ast.parse(report_sinks_path.read_text(encoding="utf-8"))
    subprocess_attrs: list[str] = []
    run_calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "subprocess":
            subprocess_attrs.append(node.attr)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ):
            run_calls.append(node)
    unexpected_attrs = sorted(set(subprocess_attrs) - {"PIPE", "run"})
    if unexpected_attrs:
        raise ProfileError(
            "dashboard IAP passport subprocess scope admitted only subprocess.run/PIPE, "
            f"observed {unexpected_attrs}"
        )
    if len(run_calls) != 1:
        raise ProfileError(f"dashboard IAP passport expected exactly one subprocess.run, observed {len(run_calls)}")
    call = run_calls[0]
    command = call.args[0] if call.args else None
    if not isinstance(command, ast.List) or len(command.elts) != 5:
        raise ProfileError("dashboard IAP passport subprocess command must be a five-item argv list")
    expected_prefix = ("openssl", "dgst", "-sha256", "-sign")
    for index, expected in enumerate(expected_prefix):
        item = command.elts[index]
        if not isinstance(item, ast.Constant) or item.value != expected:
            raise ProfileError("dashboard IAP passport subprocess command must be openssl dgst -sha256 -sign")
    if not isinstance(command.elts[4], ast.Name) or command.elts[4].id != "key_file_path":
        raise ProfileError("dashboard IAP passport subprocess key argument must be the local temp key file")
    for keyword in call.keywords:
        if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
            raise ProfileError("dashboard IAP passport subprocess must not use shell=True")
    return 1


_DASHBOARD_STATE_CASE_EXPECTED: Mapping[str, Mapping[str, str]] = {
    "projection-closed": {
        "frontier_kind": "complete",
        "board_state": "closed",
        "disp": "closed",
    },
    "projection-mid-walk": {
        "frontier_kind": "closure_pending",
        "board_state": "observed_running",
        "disp": "running",
    },
    "projection-declared-edge-mid-walk": {
        "frontier_kind": "closure_pending",
        "board_state": "observed_running",
        "disp": "running",
    },
    "projection-adapter-error": {
        "frontier_kind": "agent_incomplete",
        "board_state": "link_paused",
        "disp": "stopped",
    },
    "projection-fossil": {
        "frontier_kind": "closure_pending",
        "board_state": "unknown",
        "disp": "unknown",
    },
    "projection-parked": {
        "frontier_kind": "chat_session_parked",
        "board_state": "waiting_review",
        "disp": "review",
    },
}


def _dashboard_productization_assert_state_projection_cases(
    repo: Path,
) -> tuple[int, str]:
    """Pin non-happy read-side state derivation over generated fixture roots.

    The fixture roots are support-checker inputs only. They exercise already
    admitted ledger/dashboard projections and do not write project evidence.
    """

    from brick_protocol.support.operator import frontier_observation
    from support.operator import dashboard_export, ledger_projection

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-dashboard-state-projection-") as tmp:
        temp_repo = Path(tmp) / "repo"
        buildings_root = temp_repo / "project" / "brick-protocol" / "buildings"
        buildings_root.mkdir(parents=True)
        _chat_session_write_temp_project_declaration(temp_repo)
        for case_id in _DASHBOARD_STATE_CASE_EXPECTED:
            _dashboard_state_write_fixture(buildings_root / case_id, case_id)

        ledger = ledger_projection.project_orchestration_ledger_packet(repo_root=temp_repo)
        dashboard = dashboard_export.dashboard_export_packet(repo_root=temp_repo)
        table = _dashboard_state_projection_table(ledger, dashboard)
        _dashboard_state_assert_expected(table, label="fixture")
        inspected += len(table)

        original_board_state = ledger_projection._project_ledger_board_state
        original_dashboard_packet = dashboard_export.project_orchestration_ledger_packet

        def bad_board_state(frontier_kind: str, *args: Any, **kwargs: Any) -> str:
            if frontier_kind == "agent_incomplete":
                return "observed_running"
            return original_board_state(frontier_kind, *args, **kwargs)

        ledger_projection._project_ledger_board_state = bad_board_state
        try:
            mutated_ledger = ledger_projection.project_orchestration_ledger_packet(
                repo_root=temp_repo
            )
            dashboard_export.project_orchestration_ledger_packet = (
                lambda **_: mutated_ledger
            )
            mutated_dashboard = dashboard_export.dashboard_export_packet(repo_root=temp_repo)
            mutated_table = _dashboard_state_projection_table(
                mutated_ledger,
                mutated_dashboard,
            )
            adapter_row = {
                str(row.get("building_id")): row for row in mutated_table
            }.get("projection-adapter-error")
            if not adapter_row or adapter_row.get("disp") != "running":
                raise ProfileError(
                    "dashboard_productization_projection FIRE mutation did not apply: "
                    f"adapter-error row was {adapter_row!r}"
                )
            try:
                _dashboard_state_assert_expected(mutated_table, label="mutated")
            except ProfileError:
                inspected += 1
            else:
                raise ProfileError(
                    "dashboard_productization_projection FIRE probe did NOT fire "
                    "for breakdown->running board-state mutation"
                )
        finally:
            ledger_projection._project_ledger_board_state = original_board_state
            dashboard_export.project_orchestration_ledger_packet = original_dashboard_packet

        original_closed_boundary_observed = frontier_observation._closed_boundary_observed

        def bad_closed_boundary_observed(
            link_records: Sequence[Mapping[str, Any]],
            building_map: Mapping[str, Any],
        ) -> bool:
            if original_closed_boundary_observed(link_records, building_map):
                return True
            for record in reversed(link_records):
                target = str(
                    record.get("target_brick_instance_ref")
                    or record.get("target")
                    or ""
                )
                if frontier_observation._is_closed_boundary_ref(target):
                    return True
            link_edges = building_map.get("link_edges")
            if isinstance(link_edges, list):
                for edge in link_edges:
                    if not isinstance(edge, Mapping):
                        continue
                    target = str(edge.get("target_brick_instance_ref") or "")
                    if frontier_observation._is_closed_boundary_ref(target):
                        return True
            return False

        frontier_observation._closed_boundary_observed = bad_closed_boundary_observed
        try:
            mutated_ledger = ledger_projection.project_orchestration_ledger_packet(
                repo_root=temp_repo
            )
            dashboard_export.project_orchestration_ledger_packet = (
                lambda **_: mutated_ledger
            )
            mutated_dashboard = dashboard_export.dashboard_export_packet(repo_root=temp_repo)
            mutated_table = _dashboard_state_projection_table(
                mutated_ledger,
                mutated_dashboard,
            )
            mid_walk_row = {
                str(row.get("building_id")): row for row in mutated_table
            }.get("projection-mid-walk")
            if not mid_walk_row or mid_walk_row.get("disp") != "closed":
                raise ProfileError(
                    "dashboard_productization_projection FIRE mutation did not apply: "
                    f"mid-walk row was {mid_walk_row!r}"
                )
            declared_edge_row = {
                str(row.get("building_id")): row for row in mutated_table
            }.get("projection-declared-edge-mid-walk")
            if not declared_edge_row or declared_edge_row.get("disp") != "closed":
                raise ProfileError(
                    "dashboard_productization_projection FIRE mutation did not apply: "
                    f"declared-edge mid-walk row was {declared_edge_row!r}"
                )
            try:
                _dashboard_state_assert_expected(mutated_table, label="closed-boundary-mutated")
            except ProfileError:
                inspected += 1
            else:
                raise ProfileError(
                    "dashboard_productization_projection FIRE probe did NOT fire "
                    "for closed-without-boundary mutation"
                )
        finally:
            frontier_observation._closed_boundary_observed = original_closed_boundary_observed
            dashboard_export.project_orchestration_ledger_packet = original_dashboard_packet

    return inspected, _dashboard_state_format_table(table)


def _dashboard_state_projection_table(
    ledger: Mapping[str, Any],
    dashboard: Mapping[str, Any],
) -> list[Mapping[str, str]]:
    dashboard_rows = {
        str(row.get("id")): row
        for row in dashboard.get("buildings", [])
        if isinstance(row, Mapping)
    }
    table: list[Mapping[str, str]] = []
    for row in ledger.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        building_id = str(row.get("building_id") or "")
        if building_id not in _DASHBOARD_STATE_CASE_EXPECTED:
            continue
        dashboard_row = dashboard_rows.get(building_id, {})
        table.append(
            {
                "building_id": building_id,
                "frontier_kind": str(row.get("frontier_kind") or ""),
                "board_state": str(row.get("board_state") or ""),
                "disp": str(dashboard_row.get("disp") or ""),
            }
        )
    return sorted(table, key=lambda item: item["building_id"])


def _dashboard_state_assert_expected(
    table: Sequence[Mapping[str, str]],
    *,
    label: str,
) -> None:
    rows = {str(row.get("building_id")): row for row in table}
    missing = sorted(set(_DASHBOARD_STATE_CASE_EXPECTED) - set(rows))
    if missing:
        raise ProfileError(
            f"dashboard_productization_projection {label} state table missing "
            f"case(s): {', '.join(missing)}"
        )
    violations: list[str] = []
    for building_id, expected in _DASHBOARD_STATE_CASE_EXPECTED.items():
        row = rows[building_id]
        for key, expected_value in expected.items():
            if row.get(key) != expected_value:
                violations.append(
                    f"{building_id}.{key}: expected {expected_value!r}, "
                    f"observed {row.get(key)!r}"
                )
    if violations:
        raise ProfileError(
            f"dashboard_productization_projection {label} state table rejected:\n"
            + "\n".join(f"- {violation}" for violation in violations)
        )


def _dashboard_state_format_table(table: Sequence[Mapping[str, str]]) -> str:
    lines = ["building_id\tfrontier_kind\tboard_state\tdisp"]
    for row in table:
        lines.append(
            "\t".join(
                str(row.get(key, ""))
                for key in ("building_id", "frontier_kind", "board_state", "disp")
            )
        )
    return "\n".join(lines)


def _dashboard_state_write_fixture(building_root: Path, case_id: str) -> None:
    if case_id == "projection-closed":
        _dashboard_state_write_complete_fixture(
            building_root,
            raw_link_records=[
                _dashboard_state_link_record(
                    case_id,
                    target_ref=f"building-boundary:{case_id}-closed",
                    building_lifecycle_state="closed",
                )
            ],
            map_target_ref=f"building-boundary:{case_id}-closed",
        )
        return
    if case_id == "projection-mid-walk":
        _dashboard_state_write_complete_fixture(
            building_root,
            raw_link_records=[
                _dashboard_state_link_record(
                    case_id,
                    target_ref=f"brick:{case_id}:next",
                )
            ],
            map_target_ref=f"building-boundary:{case_id}-closed",
        )
        return
    if case_id == "projection-declared-edge-mid-walk":
        _dashboard_state_write_complete_fixture(
            building_root,
            raw_link_records=[
                _dashboard_state_link_record(
                    case_id,
                    target_ref=f"brick:{case_id}:next",
                ),
                _dashboard_state_declared_graph_link_record(
                    case_id,
                    target_ref=f"building-boundary:{case_id}-closed",
                ),
            ],
            map_target_ref=f"building-boundary:{case_id}-closed",
        )
        return
    if case_id == "projection-adapter-error":
        _dashboard_state_write_frontier_fixture(building_root, case_id)
        return
    if case_id == "projection-fossil":
        _dashboard_state_write_complete_fixture(
            building_root,
            raw_agent_return_records=[],
            raw_link_records=[],
            map_target_ref=f"brick:{case_id}:unknown-next",
        )
        return
    if case_id == "projection-parked":
        _dashboard_state_write_parked_fixture(building_root, case_id)
        return
    raise ProfileError(f"unknown dashboard state fixture case: {case_id}")


def _dashboard_state_write_complete_fixture(
    building_root: Path,
    *,
    raw_link_records: Sequence[Mapping[str, Any]],
    map_target_ref: str,
    raw_agent_return_records: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    case_id = building_root.name
    _dashboard_state_write_common_files(
        building_root,
        case_id,
        map_target_ref=map_target_ref,
    )
    raw = building_root / "raw"
    agent_returns = (
        raw_agent_return_records
        if raw_agent_return_records is not None
        else [_dashboard_state_agent_return_record(case_id)]
    )
    _dashboard_state_write_jsonl(raw / "agent-return.jsonl", agent_returns)
    _dashboard_state_write_jsonl(raw / "link.jsonl", raw_link_records)
    for rel in (
        "evidence/claim_trace/agent/returned_claims.json",
        "evidence/claim_trace/link/transfer_trace.json",
        "evidence/claim_trace/link/carry_trace.json",
        "evidence/claim_trace/link/sufficiency_trace.json",
        "evidence/claim_trace/link/movement_trace.json",
    ):
        _dashboard_state_write_json(
            building_root / rel,
            {"facts": [{"ref": f"{case_id}:{rel}"}]},
        )


def _dashboard_state_write_frontier_fixture(building_root: Path, case_id: str) -> None:
    _dashboard_state_write_common_files(
        building_root,
        case_id,
        map_target_ref=f"brick:{case_id}:blocked-next",
    )
    raw = building_root / "raw"
    _dashboard_state_write_jsonl(
        raw / "agent-received.jsonl",
        [{"received_work_ref": f"work:{case_id}"}],
    )
    _dashboard_state_write_jsonl(
        raw / "adapter-error.jsonl",
        [{"adapter_error_ref": f"adapter-error:{case_id}"}],
    )
    _dashboard_state_write_jsonl(
        raw / "link.jsonl",
        [
            _dashboard_state_link_record(
                case_id,
                target_ref=f"brick:{case_id}:blocked-next",
            )
        ],
    )
    step_dir = building_root / "work" / "step-outputs" / f"{case_id}-attempt-1"
    _dashboard_state_write_json(
        step_dir / "adapter-error.json",
        {"adapter_error_ref": f"adapter-error:{case_id}"},
    )
    for rel in (
        "evidence/claim_trace/agent/receipt_trace.json",
        "evidence/claim_trace/link/frontier_trace.json",
    ):
        _dashboard_state_write_json(
            building_root / rel,
            {"facts": [{"ref": f"{case_id}:{rel}"}]},
        )


def _dashboard_state_write_parked_fixture(building_root: Path, case_id: str) -> None:
    _dashboard_state_write_common_files(
        building_root,
        case_id,
        map_target_ref=f"brick:{case_id}:parked-next",
    )
    raw = building_root / "raw"
    _dashboard_state_write_jsonl(
        raw / "agent-received.jsonl",
        [{"received_work_ref": f"work:{case_id}"}],
    )
    _dashboard_state_write_jsonl(
        raw / "chat-session-park.jsonl",
        [{"parked_ref": f"parked:{case_id}"}],
    )
    _dashboard_state_write_jsonl(
        raw / "link.jsonl",
        [
            {
                **_dashboard_state_link_record(
                    case_id,
                    target_ref=f"brick:{case_id}:parked-next",
                ),
                "frontier_kind": "chat_session_parked",
                "transition_lifecycle_state": "paused",
                "transition_lifecycle_progress_state": "in_progress",
                "transition_lifecycle_paused_at_ref": f"raw:link:{case_id}:parked",
                "transition_lifecycle_required_disposition_owner": "caller-or-coo",
            }
        ],
    )
    step_dir = building_root / "work" / "step-outputs" / f"{case_id}-attempt-1"
    _dashboard_state_write_json(
        step_dir / "work-envelope.json",
        {"adapter_ref": "adapter:chat-session"},
    )
    _dashboard_state_write_json(step_dir / "parked.json", {"parked_ref": f"parked:{case_id}"})
    for rel in (
        "evidence/claim_trace/agent/receipt_trace.json",
        "evidence/claim_trace/link/frontier_trace.json",
    ):
        _dashboard_state_write_json(
            building_root / rel,
            {"facts": [{"ref": f"{case_id}:{rel}"}]},
        )


def _dashboard_state_write_common_files(
    building_root: Path,
    case_id: str,
    *,
    map_target_ref: str,
) -> None:
    _dashboard_state_write_jsonl(
        building_root / "capture" / "events.jsonl",
        [{"event_ref": f"event:{case_id}:fixture"}],
    )
    _dashboard_state_write_json(
        building_root / "raw" / "raw-manifest.json",
        {"kind": "raw_manifest"},
    )
    _dashboard_state_write_jsonl(
        building_root / "raw" / "brick-work.jsonl",
        [{"brick_work_ref": f"work:{case_id}"}],
    )
    _dashboard_state_write_json(
        building_root / "evidence" / "evidence-manifest.json",
        {"kind": "evidence_manifest"},
    )
    _dashboard_state_write_json(
        building_root / "evidence" / "claim_trace" / "brick" / "work_contract.json",
        {"facts": [{"brick_work_ref": f"work:{case_id}"}]},
    )
    _dashboard_state_write_json(
        building_root / "work" / "building-work.json",
        {
            "plan_ref": f"building-plan:{case_id}",
            "task_source_ref": f"task-source:{case_id}",
        },
    )
    _dashboard_state_write_json(
        building_root / "work" / "building-map.json",
        {
            "kind": "building_map",
            "task_source_ref": f"task-source:{case_id}",
            "brick_instances": [
                {
                    "brick_instance_ref": f"brick:{case_id}:work",
                    "brick_instance_id": f"brick:{case_id}:work",
                    "attempt_index": 1,
                }
            ],
            "agent_bindings": [
                {
                    "agent_binding_id": f"agent-binding:{case_id}",
                    "brick_instance_ref": f"brick:{case_id}:work",
                    "agent_performer_ref": "agent-object:dev",
                    "step_output_ref": f"work/step-outputs/{case_id}-attempt-1/step-output.json",
                }
            ],
            "link_edges": [
                {
                    "link_edge_id": f"link-edge:{case_id}",
                    "source_brick_instance_ref": f"brick:{case_id}:work",
                    "target_brick_instance_ref": map_target_ref,
                    "edge_role": "fixture",
                }
            ],
            "groups": [],
        },
    )


def _dashboard_state_agent_return_record(case_id: str) -> Mapping[str, Any]:
    return {
        "received_work": {"received_work_ref": f"work:{case_id}"},
        "returned": {"observed_evidence": [f"fixture:{case_id}"]},
    }


def _dashboard_state_link_record(
    case_id: str,
    *,
    target_ref: str,
    building_lifecycle_state: str = "",
) -> Mapping[str, Any]:
    record = {
        "raw_ref": f"raw:link:{case_id}",
        "recorded_at": "2026-06-12T00:00:00Z",
        "step_ref": f"step:{case_id}",
        "source_brick_instance_ref": f"brick:{case_id}:work",
        "target_brick_instance_ref": target_ref,
        "movement": "forward",
    }
    if building_lifecycle_state:
        record["building_lifecycle_state"] = building_lifecycle_state
    return record


def _dashboard_state_declared_graph_link_record(
    case_id: str,
    *,
    target_ref: str,
) -> Mapping[str, Any]:
    return {
        "raw_ref": f"raw:link-graph:01:edge-{case_id}-closure-to-boundary",
        "raw_refs": [f"raw:link-graph:01:edge-{case_id}-closure-to-boundary"],
        "recorded_at": "2026-06-12T00:00:00Z",
        "step_ref": f"step:{case_id}:closure",
        "source_step_ref": f"step:{case_id}:closure",
        "source_brick_instance_ref": f"brick:{case_id}:closure",
        "target_brick_instance_ref": target_ref,
        "target": target_ref,
        "movement": "forward",
        "movement_source": "declared graph Building Plan Link edge",
        "declared_graph_edge": True,
        "is_completion_edge": True,
    }


def _dashboard_state_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _dashboard_state_write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(record), sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def run_dashboard_productization_projection(repo: Path) -> KernelResult:
    """Dashboard deploy/env/bake guard for the support-only dashboard surface."""

    required_paths = (
        repo / "support/dashboard/DEPLOY.md",
        repo / "support/dashboard/server/index.mjs",
    )
    missing = [to_posix(path.relative_to(repo)) for path in required_paths if not path.exists()]
    if missing:
        raise ProfileError(
            "dashboard_productization_projection missing required path(s): "
            + ", ".join(missing)
        )

    inspected = 0
    seed_inspected, seed_observation = _dashboard_productization_public_seed_observation(repo)
    inspected += seed_inspected
    inspected += _dashboard_productization_assert_public_seed_optional_probe()

    server_text = (repo / "support/dashboard/server/index.mjs").read_text(encoding="utf-8")
    _dashboard_productization_validate_server_text(server_text)
    inspected += 1
    inspected += _dashboard_productization_assert_mutated_server_rejects(server_text)

    literal_violations, literal_inspected = _dashboard_productization_forbidden_literal_violations(repo)
    inspected += literal_inspected
    if literal_violations:
        raise ProfileError(
            "dashboard_productization_projection hardcoded-literal lint rejected evidence:\n"
            + "\n".join(f"- {violation}" for violation in literal_violations)
        )
    inspected += _dashboard_productization_assert_literal_fire_probe()
    inspected += _dashboard_productization_assert_bake_shape_probe(repo)
    inspected += _dashboard_productization_assert_openssl_subprocess_scope(repo)
    inspected += _dashboard_productization_assert_iap_passport_probe()
    state_inspected, state_table = _dashboard_productization_assert_state_projection_cases(repo)
    inspected += state_inspected

    return KernelResult(
        check_id="dashboard_productization_projection",
        inspected=inspected,
        output=(
            "dashboard productization projection passed: production POST /ingest "
            "fails closed when INGEST_SECRET is missing or dev-secret, static/SSE "
            "routes remain outside that guard, hardcoded deploy URL/project/org "
            "literals are rejected with FIRE probes, and bake_dashboard_data_json "
            "round-tripped a source_truth false packet with buildings list while "
            "a mutated source_truth true packet fired RED. "
            f"{seed_observation} "
            "The dashboard IAP "
            "passport pin observed Authorization only when BRICK_DASHBOARD_SA_KEY_PATH "
            "was present, pinned the subprocess surface to openssl dgst -sha256 -sign, "
            "and fired RED when Authorization attachment was removed. "
            "State projection table:\n"
            f"{state_table}\n"
            "A mutated breakdown->running board-state derivation and a mutated "
            "closed-without-boundary derivation both fired RED."
        ),
    )


def _chat_session_park_plan() -> Mapping[str, Any]:
    return {
        "plan_ref": "building-plan:chat-session-park-seam-case",
        "owner_axis": "Brick",
        "building_id": "chat-session-park-seam-case",
        "plan_shape": "linear",
        "selected_adapter_ref": "adapter:chat-session",
        "report_event_policy": {
            "enabled": True,
            "grain": "building",
            "event_kinds": ["building_started", "intervention_required"],
            "sink_refs": ["report-sink:local-inbox", "report-sink:operator-wake-local"],
        },
        "steps": [
            {
                "step_ref": "chat-session-park-work",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:chat-session-park-work",
                        "brick_work_ref": "work:chat-session-park-work",
                        "brick_instance_ref": "brick-chat-session-park-work",
                        "work_statement": "Exercise chat-session S1 park seam.",
                        "comparison_rule": "Support observes parked evidence shape only.",
                        "required_return_shape": "made_changes, observed_evidence, not_proven",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:chat-session-park-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                    {
                        "axis": "Link",
                        "row_ref": "link-row:chat-session-park-work",
                        "movement": "forward",
                        "target_ref": "brick-chat-session-park-closure",
                    },
                ],
            }
        ],
    }


def _chat_session_park_graph_plan(
    *,
    building_id: str = "chat-session-park-seam-dynamic-case",
) -> Mapping[str, Any]:
    return {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "graph",
        "report_event_policy": {
            "enabled": True,
            "grain": "building",
            "event_kinds": ["building_started", "intervention_required"],
            "sink_refs": ["report-sink:local-inbox", "report-sink:operator-wake-local"],
        },
        "execution_order": ["chat-session-park-dynamic-work", "chat-session-followup-work"],
        "brick_steps": [
            {
                "step_ref": "chat-session-park-dynamic-work",
                "selected_adapter_ref": "adapter:chat-session",
                "completion_edge_ref": "edge:chat-session-park-dynamic-work-to-followup",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:chat-session-park-dynamic-work",
                        "brick_work_ref": "work:chat-session-park-dynamic-work",
                        "brick_instance_ref": "brick-chat-session-park-dynamic-work",
                        "work_statement": "Exercise chat-session S1 park seam on the dynamic graph walker.",
                        "comparison_rule": "Support observes parked evidence shape only.",
                        "required_return_shape": "made_changes, observed_evidence, not_proven",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:chat-session-park-dynamic-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                ],
            },
            {
                "step_ref": "chat-session-followup-work",
                "selected_adapter_ref": "adapter:local",
                "completion_edge_ref": "edge:chat-session-followup-work-to-boundary",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:chat-session-followup-work",
                        "brick_work_ref": "work:chat-session-followup-work",
                        "brick_instance_ref": "brick-chat-session-followup-work",
                        "work_statement": "Exercise live follow-up after chat-session submission.",
                        "comparison_rule": "Support observes follow-up invocation only.",
                        "required_return_shape": "returned_summary, adapter_ref",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:chat-session-followup-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                ],
            }
        ],
        "link_edges": [
            {
                "edge_ref": "edge:chat-session-park-dynamic-work-to-followup",
                "source_step_ref": "chat-session-park-dynamic-work",
                "target_step_ref": "chat-session-followup-work",
                "rows": [
                    {
                        "axis": "Link",
                        "row_ref": "link-row:chat-session-park-dynamic-work",
                        "movement": "forward",
                        "target_ref": "brick-chat-session-followup-work",
                    }
                ],
            },
            {
                "edge_ref": "edge:chat-session-followup-work-to-boundary",
                "source_step_ref": "chat-session-followup-work",
                "rows": [
                    {
                        "axis": "Link",
                        "row_ref": "link-row:chat-session-followup-work",
                        "movement": "forward",
                        "target_ref": "building-boundary:chat-session-park-dynamic-closed",
                    }
                ],
            }
        ],
    }


def _chat_session_assert_declared_adapter_capability(temp_repo: Path) -> None:
    dev = _chat_session_agent_object(temp_repo, "dev")
    qa = _chat_session_agent_object(temp_repo, "qa")
    if "adapter:chat-session" not in dev.get("adapter_refs", []):
        raise ProfileError(
            "chat_session_park_seam expected agent/objects/dev.yaml to declare "
            "adapter:chat-session"
        )
    if "adapter:chat-session" in qa.get("adapter_refs", []):
        raise ProfileError(
            "chat_session_park_seam expected undeclared negative-control "
            "agent/objects/qa.yaml to omit adapter:chat-session"
        )


def _chat_session_agent_object(temp_repo: Path, object_name: str) -> Mapping[str, Any]:
    path = temp_repo / "agent" / "objects" / f"{object_name}.yaml"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"chat_session_park_seam failed to read Agent Object {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ProfileError(f"chat_session_park_seam expected mapping Agent Object at {path}")
    return value


def _chat_session_assert_undeclared_adapter_rejects(
    run_module: Any,
    *,
    buildings_root: Path,
    temp_repo: Path,
) -> None:
    plan = _chat_session_plan_with_agent(
        "agent-object:qa",
        building_id="chat-session-park-undeclared-agent-case",
    )
    original_runner_repo = run_module._REPO_ROOT
    try:
        run_module._REPO_ROOT = temp_repo
        try:
            run_module.run_building_plan(
                plan,
                output_root=buildings_root,
                overwrite_existing=True,
            )
        except run_module.ChatSessionParkFrontierEvidenceWritten as exc:
            raise ProfileError(
                "chat_session_park_seam undeclared Agent Object parked instead "
                f"of rejecting adapter admission: {exc}"
            ) from exc
        except ValueError as exc:
            if "selected adapter must be referenced by Agent Object" not in str(exc):
                raise ProfileError(
                    "chat_session_park_seam undeclared Agent Object rejected with "
                    f"the wrong reason: {exc}"
                ) from exc
            root = buildings_root / "chat-session-park-undeclared-agent-case"
            if (root / "raw" / "chat-session-park.jsonl").exists() or any(
                path.is_file()
                for path in (root / "work" / "step-outputs").glob("*/parked.json")
            ):
                raise ProfileError(
                    "chat_session_park_seam undeclared Agent Object wrote park evidence "
                    "after adapter admission rejected"
                )
            if root.exists():
                shutil.rmtree(root)
            return
        except Exception as exc:  # noqa: BLE001 - checker reports unexpected leak type
            raise ProfileError(
                "chat_session_park_seam undeclared Agent Object should fail closed "
                f"with ValueError, observed {type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError(
            "chat_session_park_seam undeclared Agent Object with selected "
            "adapter:chat-session returned normally instead of rejecting"
        )
    finally:
        run_module._REPO_ROOT = original_runner_repo


def _chat_session_assert_non_graph_plan_rejects(
    run_module: Any,
    *,
    buildings_root: Path,
    temp_repo: Path,
) -> None:
    original_runner_repo = run_module._REPO_ROOT
    try:
        run_module._REPO_ROOT = temp_repo
        try:
            run_module.run_building_plan(
                _chat_session_park_plan(),
                output_root=buildings_root,
                overwrite_existing=True,
            )
        except ValueError as exc:
            if "walker_mode='dynamic' requires a plan_shape: graph Building Plan" not in str(exc):
                raise ProfileError(
                    "chat_session_park_seam non-graph dynamic guard had wrong reason: "
                    f"{exc}"
                ) from exc
            return
        except Exception as exc:  # noqa: BLE001
            raise ProfileError(
                "chat_session_park_seam non-graph dynamic guard expected ValueError, "
                f"observed {type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError("chat_session_park_seam non-graph plan did not reject")
    finally:
        run_module._REPO_ROOT = original_runner_repo


def _chat_session_plan_with_agent(agent_object_ref: str, *, building_id: str) -> Mapping[str, Any]:
    plan = json.loads(json.dumps(_chat_session_park_graph_plan(building_id=building_id)))
    plan["building_id"] = building_id
    plan["plan_ref"] = f"building-plan:{building_id}"
    step = plan["brick_steps"][0]
    step["step_ref"] = f"{building_id}-work"
    for row in step["rows"]:
        if row.get("axis") == "Agent":
            row["agent_object_ref"] = agent_object_ref
            row["row_ref"] = f"agent-row:{building_id}-work"
        elif row.get("axis") == "Brick":
            row["row_ref"] = f"brick-row:{building_id}-work"
            row["brick_work_ref"] = f"work:{building_id}-work"
            row["brick_instance_ref"] = f"brick-{building_id}-work"
    plan["execution_order"][0] = step["step_ref"]
    plan["link_edges"][0]["source_step_ref"] = step["step_ref"]
    plan["link_edges"][0]["rows"][0]["row_ref"] = f"link-row:{building_id}-work"
    return plan


def _chat_session_write_temp_project_declaration(temp_repo: Path) -> None:
    project_root = temp_repo / "project" / "brick-protocol"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "README.md").write_text(
        "# Temp Brick Protocol Project\n\nChecker fixture project declaration.\n",
        encoding="utf-8",
    )
    (project_root / "project.json").write_text(
        json.dumps(
            {
                "project_ref": "project:brick-protocol",
                "label": "Temp Brick Protocol",
                "direction": "Exercise chat-session park projection seams.",
                "done_means": "Checker fixture reaches its closed evidence assertions.",
                "out_of_scope": "External delivery and provider liveness.",
                "managers": ["smith"],
                "declared_by": "smith",
                "declared_at": "2026-06-11T00:00:00+00:00",
                "charter_ref": "project/brick-protocol/README.md",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _chat_session_drive_park(
    run_module: Any,
    plan: Mapping[str, Any],
    *,
    buildings_root: Path,
    temp_repo: Path,
    label: str,
) -> tuple[Path, tuple[str, ...]]:
    original_runner_repo = run_module._REPO_ROOT
    try:
        run_module._REPO_ROOT = temp_repo
        try:
            run_module.run_building_plan(
                plan,
                output_root=buildings_root,
                overwrite_existing=True,
            )
        except run_module.ChatSessionParkFrontierEvidenceWritten as exc:
            return Path(exc.building_root), tuple(str(path) for path in exc.written_files)
        except Exception as exc:  # noqa: BLE001 - assert typed park frontier
            raise ProfileError(
                f"chat_session_park_seam {label} path expected typed "
                "ChatSessionParkFrontierEvidenceWritten, but leaked "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError(
            f"chat_session_park_seam {label} path expected the runner to stop with "
            "ChatSessionParkFrontierEvidenceWritten, but it returned normally"
        )
    finally:
        run_module._REPO_ROOT = original_runner_repo


def _chat_session_assert_second_claim_rejects(run_module: Any, building_root: Path) -> None:
    try:
        run_module.claim_chat_session_envelope(building_root, lane_ref="lane:second-checker")
    except FileExistsError as exc:
        if "already claimed" not in str(exc):
            raise ProfileError(
                "chat_session_park_seam second claim rejected with wrong reason: "
                f"{exc}"
            ) from exc
        return
    raise ProfileError("chat_session_park_seam second claim did not reject")


def _chat_session_probe_uuid_text() -> str:
    return "-".join(("123e4567", "e89b", "42d3", "a456", "426614174000"))


def _chat_session_probe_ulid_text() -> str:
    return "".join(("01ARZ3", "NDEK", "TSV4", "RRFF", "Q69G", "5FAV"))


def _chat_session_assert_envelope_session_key_rejects(uuid_probe: str) -> None:
    from brick_protocol.support.connection.agent_adapter import AgentAdapterRequest
    from support.recording import adapter_error_frontier

    request = AgentAdapterRequest(
        building_id="chat-session-envelope-key-case",
        agent_object_ref="agent-object:dev",
        adapter_ref="adapter:chat-session",
        brick_instance_ref="brick-chat-session-envelope-key-case",
        next_brick_instance_ref="building-boundary:chat-session-envelope-key-case",
        source_fact_bodies={uuid_probe: "ordinary body"},
    )
    try:
        adapter_error_frontier._agent_adapter_request_work_envelope(request)
    except ValueError as exc:
        if "session-id-shaped text" not in str(exc):
            raise ProfileError(
                "chat_session_park_seam envelope session-key rejected with wrong reason: "
                f"{exc}"
            ) from exc
        return
    raise ProfileError("chat_session_park_seam envelope session-shaped key did not reject")


def _chat_session_assert_key_scan_fire(
    run_module: Any,
    *,
    buildings_root: Path,
    temp_repo: Path,
    uuid_probe: str,
) -> None:
    fire_root, _ = _chat_session_drive_park(
        run_module,
        _chat_session_park_graph_plan(building_id="chat-session-key-scan-fire-case"),
        buildings_root=buildings_root,
        temp_repo=temp_repo,
        label="key-scan-fire",
    )
    claim = run_module.claim_chat_session_envelope(
        fire_root,
        lane_ref="lane:key-scan-fire-checker",
    )
    token = str(claim.get("claim_token") or "")
    original_rejector = run_module._reject_session_like_text
    run_module._reject_session_like_text = _chat_session_value_only_session_rejector
    try:
        try:
            run_module.submit_chat_session_return(
                fire_root,
                claim_token=token,
                returned={
                    uuid_probe: "mutated key-skip walker would admit this",
                    "made_changes": ["key-skip FIRE"],
                    "observed_evidence": ["ordinary value"],
                    "not_proven": ["not resumed"],
                },
            )
        except ValueError as exc:
            raise ProfileError(
                "chat_session_park_seam FIRE did not expose key-skip mutation: "
                f"{exc}"
            ) from exc
    finally:
        run_module._reject_session_like_text = original_rejector


def _chat_session_value_only_session_rejector(label: str, value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _chat_session_value_only_session_rejector(f"{label}.{key}", child)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _chat_session_value_only_session_rejector(f"{label}[{index}]", child)
        return
    if isinstance(value, str) and (
        _SESSION_ID_UUID_RE.search(value) or _SESSION_ID_ULID_RE.search(value)
    ):
        raise ValueError(f"{label} contains session-id-shaped text")


def _chat_session_assert_submit_rejects(
    run_module: Any,
    building_root: Path,
    *,
    token: str,
    returned: Mapping[str, Any],
    expected: str,
    label: str,
) -> None:
    before = (building_root / "work" / "step-outputs")
    submission_count = len(list(before.glob("*/submission.json")))
    try:
        run_module.submit_chat_session_return(
            building_root,
            claim_token=token,
            returned=returned,
        )
    except ValueError as exc:
        if expected not in str(exc):
            raise ProfileError(
                f"chat_session_park_seam {label} rejected with wrong reason: {exc}"
            ) from exc
        after_count = len(list(before.glob("*/submission.json")))
        if after_count != submission_count:
            raise ProfileError(
                f"chat_session_park_seam {label} wrote submission evidence after reject"
            )
        return
    raise ProfileError(f"chat_session_park_seam {label} submit did not reject")


def _chat_session_assert_resume_rejects(
    run_module: Any,
    building_root: Path,
    *,
    temp_repo: Path,
    expected: str,
    label: str,
) -> None:
    original_runner_repo = run_module._REPO_ROOT
    try:
        run_module._REPO_ROOT = temp_repo
        try:
            run_module.resume_building_plan(building_root, overwrite_existing=True)
        except ValueError as exc:
            if expected not in str(exc):
                raise ProfileError(
                    f"chat_session_park_seam {label} resume rejected with wrong reason: {exc}"
                ) from exc
            return
        except Exception as exc:  # noqa: BLE001
            raise ProfileError(
                f"chat_session_park_seam {label} resume expected ValueError, "
                f"observed {type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError(f"chat_session_park_seam {label} resume did not reject")
    finally:
        run_module._REPO_ROOT = original_runner_repo


def _chat_session_assert_park_evidence(
    building_root: Path,
    *,
    written_files: tuple[str, ...],
    temp_repo: Path,
    label: str,
) -> int:
    from brick_protocol.support.connection.agent_adapter import AgentAdapterRequest
    from support.operator.frontier_observation import observe_building_frontier
    from support.operator.reporter import (
        OPERATOR_WAKE_LOCAL_SINK_REF,
        building_event_kind_from_frontier,
        render_report_packet,
    )

    if not building_root.is_dir():
        raise ProfileError(f"chat_session_park_seam {label} path did not create a Building root")
    if not written_files:
        raise ProfileError(f"chat_session_park_seam {label} path reported no written evidence files")

    step_dir = _chat_session_single_step_output_dir(building_root)
    envelope_path = step_dir / "work-envelope.json"
    parked_path = step_dir / "parked.json"
    raw_park_path = building_root / "raw" / "chat-session-park.jsonl"
    raw_agent_return_path = building_root / "raw" / "agent-return.jsonl"
    raw_adapter_error_path = building_root / "raw" / "adapter-error.jsonl"
    for required in (envelope_path, parked_path, raw_park_path):
        if not required.is_file():
            raise ProfileError(f"chat_session_park_seam {label} path missing required file: {required}")
    if raw_agent_return_path.exists():
        raise ProfileError(f"chat_session_park_seam {label} path fabricated raw/agent-return.jsonl")
    if raw_adapter_error_path.exists():
        raise ProfileError(
            f"chat_session_park_seam {label} path wrote adapter-error raw evidence for a park"
        )

    envelope = _chat_session_json_object(envelope_path)
    parked = _chat_session_json_object(parked_path)
    expected_envelope_keys = {field.name for field in fields(AgentAdapterRequest)}
    observed_envelope_keys = set(envelope)
    if observed_envelope_keys != expected_envelope_keys:
        raise ProfileError(
            f"chat_session_park_seam {label} path work envelope keys drifted: "
            f"missing={sorted(expected_envelope_keys - observed_envelope_keys)} "
            f"unexpected={sorted(observed_envelope_keys - expected_envelope_keys)}"
        )
    if envelope.get("adapter_ref") != "adapter:chat-session":
        raise ProfileError(
            f"chat_session_park_seam {label} path work envelope did not preserve adapter:chat-session"
        )
    if parked.get("kind") != "chat_session_park_record":
        raise ProfileError(f"chat_session_park_seam {label} path parked.json has the wrong kind")
    if parked.get("schema_version") != "chat-session-park-record-0":
        raise ProfileError(
            f"chat_session_park_seam {label} path parked.json has the wrong schema version"
        )
    if "adapter_error_ref" in parked or "agent_fact_created" in parked:
        raise ProfileError(
            f"chat_session_park_seam {label} path parked.json reused adapter-error shape keys"
        )
    if parked.get("work_envelope_ref") == parked.get("parked_ref"):
        raise ProfileError(
            f"chat_session_park_seam {label} path parked ref and envelope ref are not distinct"
        )

    link_records = [
        json.loads(line)
        for line in (building_root / "raw" / "link.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    park_frontiers = [
        record
        for record in link_records
        if isinstance(record, Mapping) and record.get("frontier_kind") == "chat_session_parked"
    ]
    if not park_frontiers:
        raise ProfileError(
            f"chat_session_park_seam {label} path did not write a chat_session_parked Link frontier row"
        )
    latest_park = park_frontiers[-1]
    if latest_park.get("transition_lifecycle_state") != "paused":
        raise ProfileError(
            f"chat_session_park_seam {label} path did not carry a paused lifecycle row"
        )
    if not latest_park.get("transition_lifecycle_paused_at_ref"):
        raise ProfileError(
            f"chat_session_park_seam {label} path lifecycle row is not hold-addressable"
        )
    if latest_park.get("transition_lifecycle_required_disposition_owner") != "caller-or-coo":
        raise ProfileError(
            f"chat_session_park_seam {label} path lifecycle row has wrong disposition owner"
        )

    frontier = observe_building_frontier(building_root, repo_root=temp_repo)
    if frontier.get("frontier_kind") != "chat_session_parked":
        raise ProfileError(
            f"chat_session_park_seam {label} path frontier branch did not win before incomplete: "
            f"{frontier.get('frontier_kind')!r}"
        )
    event_kind = building_event_kind_from_frontier(building_root, repo_root=temp_repo)
    if event_kind != "intervention_required":
        raise ProfileError(
            f"chat_session_park_seam {label} path reporter event mapping did not ring the bell: "
            f"{event_kind!r}"
        )
    packet = render_report_packet(building_root=building_root, repo_root=temp_repo)
    if packet.get("observed_board_state") != "needs_disposition":
        raise ProfileError(
            f"chat_session_park_seam {label} path report packet did not project needs_disposition"
        )
    inbox = temp_repo / "project" / "brick-protocol" / "status" / "inbox"
    wake_packets = []
    for path in sorted(inbox.glob("*operator-wake*.json")):
        wake_packet = _chat_session_json_object(path)
        if wake_packet.get("building_id") == building_root.name:
            wake_packets.append(wake_packet)
    if not wake_packets:
        raise ProfileError(
            f"chat_session_park_seam {label} path run-surface report_event_policy emitted no operator wake packet"
        )
    wake_targets = wake_packets[-1].get("operator_wake_targets")
    if (
        not isinstance(wake_targets, list)
        or not wake_targets
        or not isinstance(wake_targets[0], Mapping)
        or wake_targets[0].get("sink_ref") != OPERATOR_WAKE_LOCAL_SINK_REF
    ):
        raise ProfileError(f"chat_session_park_seam {label} path wake packet used the wrong sink ref")
    return 13


def _chat_session_lifecycle_violations(target: Path) -> list[str]:
    from support.checkers import check_building_lifecycle_path_shape as lifecycle_shape

    label, paths = lifecycle_shape.collect_paths(target)
    violations = lifecycle_shape.check_paths(
        paths,
        is_u5_5_live=lifecycle_shape.make_u5_5_live_resolver(label),
    )
    if not violations:
        violations.extend(
            lifecycle_shape.collect_content_violations(
                label,
                lifecycle_shape.known_candidates(set(paths)),
            )
        )
    return violations


def _chat_session_single_step_output_dir(building_root: Path) -> Path:
    step_output_root = building_root / "work" / "step-outputs"
    dirs = sorted(path for path in step_output_root.iterdir() if path.is_dir())
    if len(dirs) != 1:
        raise ProfileError(
            "chat_session_park_seam expected exactly one step-output directory, "
            f"observed {len(dirs)}"
        )
    return dirs[0]


def _chat_session_json_object(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"chat_session_park_seam failed to read JSON object {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ProfileError(f"chat_session_park_seam expected JSON object at {path}")
    return value


def _chat_session_write_json_object(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _chat_session_assert_mutated_lifecycle_rejects(
    building_root: Path,
    label: str,
    mutate: Callable[[Path], None],
) -> None:
    mutant = building_root.parent / f"{building_root.name}-mut-{_chat_session_slug(label)}"
    if mutant.exists():
        shutil.rmtree(mutant)
    shutil.copytree(building_root, mutant)
    mutate(mutant)
    violations = _chat_session_lifecycle_violations(mutant)
    if not violations:
        raise ProfileError(f"chat_session_park_seam FIRE did not reject mutated copy: {label}")


def _chat_session_mutate_envelope_uuid(building_root: Path) -> None:
    envelope_path = _chat_session_single_step_output_dir(building_root) / "work-envelope.json"
    envelope = dict(_chat_session_json_object(envelope_path))
    envelope["building_session_ref"] = _chat_session_probe_uuid_text()
    _chat_session_write_json_object(envelope_path, envelope)


def _chat_session_mutate_park_as_adapter_error(building_root: Path) -> None:
    parked_path = _chat_session_single_step_output_dir(building_root) / "parked.json"
    parked = dict(_chat_session_json_object(parked_path))
    parked["adapter_error_ref"] = "adapter-error:mutated"
    parked["agent_fact_created"] = False
    _chat_session_write_json_object(parked_path, parked)


def _chat_session_delete_work_envelope(building_root: Path) -> None:
    envelope_path = _chat_session_single_step_output_dir(building_root) / "work-envelope.json"
    envelope_path.unlink()


def _chat_session_mutate_submission_forbidden_key(building_root: Path) -> None:
    submission_path = _chat_session_submission_path(building_root)
    submission = dict(_chat_session_json_object(submission_path))
    returned = dict(submission.get("returned") or {})
    returned["status"] = "done"
    submission["returned"] = returned
    _chat_session_write_json_object(submission_path, submission)


def _chat_session_mutate_submission_token(building_root: Path) -> None:
    submission_path = _chat_session_submission_path(building_root)
    submission = dict(_chat_session_json_object(submission_path))
    submission["claim_token"] = "amber-basil-cedar-copper"
    claim_path = submission_path.parent / "claim.json"
    claim = _chat_session_json_object(claim_path)
    if claim.get("claim_token") == submission["claim_token"]:
        submission["claim_token"] = "amber-basil-cedar-delta"
    _chat_session_write_json_object(submission_path, submission)


def _chat_session_submission_path(building_root: Path) -> Path:
    matches = sorted((building_root / "work" / "step-outputs").glob("*/submission.json"))
    if len(matches) != 1:
        raise ProfileError(
            "chat_session_park_seam expected exactly one submission.json, "
            f"observed {len(matches)}"
        )
    return matches[0]


def _chat_session_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "mutation"


_MCP_STDIO_SMOKE_TIMEOUT_SECONDS = 30


def run_mcp_stdio_smoke(repo: Path) -> KernelResult:
    """Execution smoke: bare-launch the MCP projection server like a real host.

    A real MCP host launches ``support/connection/mcp_projection.py`` as a plain
    Python script with a CLEAN environment (no PYTHONPATH pointing at the
    import_identity shim). The script's own __file__ bootstrap must therefore put
    everything it needs on sys.path; if it forgets the import_identity shim the
    bare launch crashes at import (ModuleNotFoundError: brick_protocol) before it
    can answer a single JSON-RPC request.

    This check subprocess-launches that script with PYTHONPATH deleted, pipes one
    ``initialize`` JSON-RPC line, and asserts the server did not crash and did
    answer with a JSON-RPC result. subprocess is permitted here in the checker
    layer (it observes the script from the outside, like a host); it must stay out
    of mcp_projection.py itself, which owns no execution surface.
    """
    script = repo / "support" / "connection" / "mcp_projection.py"
    if not script.is_file():
        raise ProfileError(f"mcp_stdio_smoke could not find MCP server script: {script}")

    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)

    request_line = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + "\n"
    )
    try:
        completed = subprocess.run(
            [sys.executable, str(script), "--repo", str(repo)],
            input=request_line,
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=str(repo),
            timeout=_MCP_STDIO_SMOKE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProfileError(
            "mcp_stdio_smoke: bare-launched MCP server timed out "
            f"after {_MCP_STDIO_SMOKE_TIMEOUT_SECONDS}s without responding"
        ) from exc

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if "Traceback" in stderr or "ModuleNotFoundError" in stderr:
        raise ProfileError(
            "mcp_stdio_smoke: bare-launched MCP server (clean env, no PYTHONPATH) "
            "crashed at startup:\n" + stderr.strip()
        )
    if '"result"' not in stdout:
        raise ProfileError(
            "mcp_stdio_smoke: bare-launched MCP server did not emit a JSON-RPC "
            f"'\"result\"' to initialize.\nstdout:\n{stdout.strip()}\n"
            f"stderr:\n{stderr.strip()}"
        )

    return KernelResult(
        check_id="mcp_stdio_smoke",
        inspected=1,
        output=(
            "mcp stdio smoke passed: bare-launched server (clean env, no "
            "PYTHONPATH) responded to initialize"
        ),
    )


_CONNECT_CONFIG_LAUNCH_TIMEOUT_SECONDS = 30


def _parse_codex_mcp_config(config_text: str) -> tuple[str, str, str]:
    """Extract (command, script_path, repo_arg) from the emitted Codex TOML.

    The generator emits exactly:

        [mcp_servers.brick-protocol]
        command = "python3"
        args = ["<script>", "--repo", "<repo>"]

    This parses those three values out of the rendered block so the checker
    launches EXACTLY what the generator told the user to run (not a
    hand-written command). Parsing failure is a ProfileError: a malformed
    generated config is itself a defect.
    """

    command: str | None = None
    args_line: str | None = None
    for raw in config_text.splitlines():
        line = raw.strip()
        if line.startswith("command"):
            _, _, value = line.partition("=")
            command = value.strip().strip('"')
        elif line.startswith("args"):
            args_line = line

    if command is None or args_line is None:
        raise ProfileError(
            "connect_config_launch: generated Codex config missing command/args "
            f"line(s):\n{config_text}"
        )

    _, _, args_value = args_line.partition("=")
    args_value = args_value.strip()
    if not (args_value.startswith("[") and args_value.endswith("]")):
        raise ProfileError(
            f"connect_config_launch: generated args is not a list literal: {args_value!r}"
        )
    items = [
        item.strip().strip('"')
        for item in args_value[1:-1].split(",")
        if item.strip()
    ]
    if len(items) != 3 or items[1] != "--repo":
        raise ProfileError(
            "connect_config_launch: generated args do not match "
            f'["<script>", "--repo", "<repo>"]: {items!r}'
        )
    script_path, _flag, repo_arg = items
    return command, script_path, repo_arg


def run_connect_config_launch(repo: Path) -> KernelResult:
    """Execution proof: the generated Codex connect config yields a working server.

    Imports the read-only connect generator (support/connection/connect.py),
    renders the Codex MCP config for THIS repo, extracts the command + server
    script + ``--repo`` it tells the user to run, and then subprocess-launches
    EXACTLY that command with a CLEAN environment (PYTHONPATH deleted) and one
    piped ``initialize`` JSON-RPC line. The launch must return a JSON-RPC
    ``"result"`` with no Traceback / ModuleNotFoundError. This proves
    "generated config -> actually working connection" end to end, not just that
    the generator emitted a plausible-looking string.

    Also asserts the emitted script path is ``<repo>/support/connection/
    mcp_projection.py`` and exists, the emitted ``--repo`` equals this repo, and
    that connect.py's source carries no hardcoded user-home literal (the path
    must be computed, never baked in).

    subprocess lives here in the checker layer (it observes the generated
    command from the outside, like a real MCP host); the generator itself runs
    no subprocess and owns no execution surface.
    """

    repo_text = str(repo)
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)
    connect = importlib.import_module("support.connection.connect")

    # The generated config must carry no hardcoded absolute user path; the path
    # is computed from the checkout. Guard the source directly.
    connect_source_path = repo / "support" / "connection" / "connect.py"
    if not connect_source_path.is_file():
        raise ProfileError(
            f"connect_config_launch: connect generator missing: {connect_source_path}"
        )
    connect_source = connect_source_path.read_text(encoding="utf-8")
    user_home_literal = "/" + "Users/"
    if user_home_literal in connect_source:
        raise ProfileError(
            "connect_config_launch: connect.py source contains a hardcoded "
            "user-home literal; the repo path must be computed, never baked in."
        )

    config_text = connect.render_codex_mcp_config(repo)
    command, script_path, repo_arg = _parse_codex_mcp_config(config_text)

    expected_script = (repo / "support" / "connection" / "mcp_projection.py").resolve()
    emitted_script = Path(script_path).resolve()
    if emitted_script != expected_script:
        raise ProfileError(
            "connect_config_launch: generated config points at "
            f"{emitted_script}, expected {expected_script}"
        )
    if not emitted_script.is_file():
        raise ProfileError(
            f"connect_config_launch: generated server script does not exist: {emitted_script}"
        )
    if Path(repo_arg).resolve() != repo.resolve():
        raise ProfileError(
            "connect_config_launch: generated --repo "
            f"{repo_arg} does not match this repo {repo}"
        )

    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)

    request_line = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + "\n"
    )
    launch_argv = [command, script_path, "--repo", repo_arg]
    try:
        completed = subprocess.run(
            launch_argv,
            input=request_line,
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=str(repo),
            timeout=_CONNECT_CONFIG_LAUNCH_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise ProfileError(
            "connect_config_launch: generated command could not be launched "
            f"(command not found on PATH): {launch_argv!r}: {exc}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ProfileError(
            "connect_config_launch: generated config server timed out "
            f"after {_CONNECT_CONFIG_LAUNCH_TIMEOUT_SECONDS}s without responding"
        ) from exc

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if "Traceback" in stderr or "ModuleNotFoundError" in stderr:
        raise ProfileError(
            "connect_config_launch: generated config server (clean env, no "
            "PYTHONPATH) crashed at startup:\n" + stderr.strip()
        )
    if '"result"' not in stdout:
        raise ProfileError(
            "connect_config_launch: generated config server did not emit a "
            f"JSON-RPC '\"result\"' to initialize.\nstdout:\n{stdout.strip()}\n"
            f"stderr:\n{stderr.strip()}"
        )

    return KernelResult(
        check_id="connect_config_launch",
        inspected=1,
        output=(
            "connect config launch passed: generated Codex config "
            "(computed repo path, no hardcoded user-home literal) launched the "
            "server with a clean env (no PYTHONPATH) and it answered initialize"
        ),
    )


def run_codex_projection_native(repo: Path) -> KernelResult:
    """Execution proof: the Codex projection is a REAL Codex-native TOML subagent.

    Imports the read-only renderer (support/connection/agent_resources.py) and
    asserts, BY EXECUTION over admitted Agent Objects, that render_codex_subagent_toml:

      (a) parses as VALID TOML (tomllib) and carries the required Codex subagent
          keys name + description + developer_instructions;
      (b) sandbox_mode is "workspace-write" for the dev (read-write-scoped) agent
          and "read-only" for a leader/reviewer agent -- a REAL tool-policy
          mapping, not a constant (this is the load-bearing FIRE pin: making
          sandbox_mode constant must turn this RED);
      (c) the Codex TOML is materially DIFFERENT from the generic/claude seed
          text -- the codex output is valid TOML whereas the claude seed is
          markdown that does NOT parse as a TOML table (real translation, not a
          relabel);
      (d) developer_instructions carries the "enforced by Brick MCP" honesty note
          (return shape / Link / evidence are not native-Codex-expressible).

    This is checker-layer support evidence only: it imports the renderer
    in-process, runs no subprocess, writes no file, and chooses no Movement. The
    renderer it pins is itself read-only (no subprocess in connection/).
    """

    import tomllib

    repo_text = str(repo)
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)
    _ensure_import_identity(repo)
    agent_resources = importlib.import_module("support.connection.agent_resources")

    list_refs = agent_resources.list_agent_object_refs
    render_toml = agent_resources.render_codex_subagent_toml
    render_claude_seed = agent_resources.render_claude_projection_seed
    render_codex_seed = agent_resources.render_codex_projection_seed

    refs = list(list_refs(repo))
    if not refs:
        raise ProfileError(
            "codex_projection_native: no admitted Agent Object refs to project"
        )

    roles = [ref.removeprefix("agent-object:") for ref in refs]

    # (a) + (d): every admitted role must yield valid TOML with the required
    # Codex subagent keys and the Brick-MCP honesty note.
    write_roles: list[str] = []
    read_only_roles: list[str] = []
    inspected = 0
    for role in roles:
        toml_text = render_toml(role, repo_root=repo)
        try:
            parsed = tomllib.loads(toml_text)
        except tomllib.TOMLDecodeError as exc:
            raise ProfileError(
                f"codex_projection_native: render_codex_subagent_toml({role!r}) "
                f"is not valid TOML: {exc}"
            ) from exc
        for required_key in ("name", "description", "developer_instructions"):
            value = parsed.get(required_key)
            if not isinstance(value, str) or not value.strip():
                raise ProfileError(
                    f"codex_projection_native: {role!r} TOML missing required Codex "
                    f"subagent key {required_key!r}"
                )
        if parsed.get("name") != role:
            raise ProfileError(
                f"codex_projection_native: {role!r} TOML name must equal the role"
            )
        sandbox_mode = parsed.get("sandbox_mode")
        if sandbox_mode not in {"workspace-write", "read-only"}:
            raise ProfileError(
                f"codex_projection_native: {role!r} TOML sandbox_mode must be "
                f"workspace-write or read-only, got {sandbox_mode!r}"
            )
        if "enforced by Brick MCP" not in parsed["developer_instructions"]:
            raise ProfileError(
                f"codex_projection_native: {role!r} developer_instructions is "
                "missing the 'enforced by Brick MCP' honesty note (return shape / "
                "Link / evidence are not native-Codex-expressible)"
            )
        if sandbox_mode == "workspace-write":
            write_roles.append(role)
        else:
            read_only_roles.append(role)
        inspected += 1

    # (b) REAL tool-policy mapping, not a constant. The dev agent
    # (tool-policy:read-write-scoped) MUST map to workspace-write; a leader and a
    # reviewer (read-only policies) MUST map to read-only. Making sandbox_mode a
    # constant (ignoring tool policy) is what this FIRE pin catches.
    if "dev" in roles:
        dev_sandbox = tomllib.loads(render_toml("dev", repo_root=repo))["sandbox_mode"]
        if dev_sandbox != "workspace-write":
            raise ProfileError(
                "codex_projection_native: dev (tool-policy:read-write-scoped) must "
                f"map to sandbox_mode workspace-write, got {dev_sandbox!r}"
            )
    if not write_roles:
        raise ProfileError(
            "codex_projection_native: no role mapped to workspace-write; a "
            "constant read-only sandbox_mode would hide the read-write-scoped "
            "worker (mapping is not real)"
        )
    if not read_only_roles:
        raise ProfileError(
            "codex_projection_native: no role mapped to read-only; a constant "
            "workspace-write sandbox_mode would over-grant every leader/reviewer "
            "(mapping is not real)"
        )

    # (e) PER-STEP write_need gate. The per-agent TOML above is the DESCRIPTIVE
    # max-capability projection; the RUN-TIME provider projection FOR A STEP must
    # additionally gate sandbox_mode on the step's Brick write NEED. A
    # write-capable agent (read-write-scoped) on a read-only Brick (write_need
    # False) MUST project read-only sandbox -- the agent's CAPABILITY must never
    # override the Brick NEED. Removing the write_need gate (back to keying on
    # tool_policy alone) turns this RED.
    sandbox_for_policies = agent_resources.codex_sandbox_mode_for_tool_policies
    write_capable_policies = ["tool-policy:leader-coordination", "tool-policy:read-write-scoped"]
    leak_sandbox = sandbox_for_policies(write_capable_policies, write_need=False)
    if leak_sandbox != "read-only":
        raise ProfileError(
            "codex_projection_native: a write-capable agent on a read-only Brick "
            f"(write_need=False) must project sandbox_mode read-only, got "
            f"{leak_sandbox!r} (capability overrode the Brick NEED)"
        )
    write_sandbox = sandbox_for_policies(write_capable_policies, write_need=True)
    if write_sandbox != "workspace-write":
        raise ProfileError(
            "codex_projection_native: a write-capable agent on a write-needed "
            f"Brick (write_need=True) must project sandbox_mode workspace-write, "
            f"got {write_sandbox!r} (over-restricted a legitimate write)"
        )

    # (c) materially DIFFERENT from the generic/claude seed: codex is valid TOML
    # with the subagent keys; the claude seed's rendered_instruction_text is
    # markdown that does NOT parse as a TOML table carrying those keys.
    probe_role = "dev" if "dev" in roles else roles[0]
    claude_text = render_claude_seed(probe_role, repo_root=repo)["rendered_instruction_text"]
    codex_toml = render_toml(probe_role, repo_root=repo)
    if claude_text.strip() == codex_toml.strip():
        raise ProfileError(
            "codex_projection_native: codex TOML is byte-identical to the claude "
            "seed text (relabel, not a real translation)"
        )
    claude_is_toml_subagent = False
    try:
        claude_parsed = tomllib.loads(claude_text)
        claude_is_toml_subagent = isinstance(claude_parsed.get("name"), str) and isinstance(
            claude_parsed.get("developer_instructions"), str
        )
    except tomllib.TOMLDecodeError:
        claude_is_toml_subagent = False
    if claude_is_toml_subagent:
        raise ProfileError(
            "codex_projection_native: the claude seed text also parses as a Codex "
            "subagent TOML; the codex projection is not a materially different form"
        )

    # The wired Codex projection seed must surface the real TOML without dropping
    # the existing generic instruction text other consumers/checkers rely on.
    seed = render_codex_seed(probe_role, repo_root=repo)
    if "rendered_codex_subagent_toml" not in seed:
        raise ProfileError(
            "codex_projection_native: render_codex_projection_seed dropped the "
            "rendered_codex_subagent_toml key"
        )
    if "rendered_instruction_text" not in seed:
        raise ProfileError(
            "codex_projection_native: render_codex_projection_seed dropped the "
            "existing rendered_instruction_text key (would break other consumers)"
        )
    if tomllib.loads(seed["rendered_codex_subagent_toml"])["name"] != probe_role:
        raise ProfileError(
            "codex_projection_native: seed rendered_codex_subagent_toml is not the "
            "role's valid TOML"
        )

    return KernelResult(
        check_id="codex_projection_native",
        inspected=inspected,
        output=(
            "codex projection native passed: "
            f"{inspected} Agent Object(s) rendered valid Codex-native subagent TOML "
            f"(write={sorted(write_roles)}, read-only count={len(read_only_roles)}); "
            "real tool-policy -> sandbox_mode mapping, honesty note present, "
            "materially different from the claude markdown seed"
        ),
    )


def _split_claude_frontmatter(md_text: str) -> tuple[str, str]:
    """Split a Claude subagent .md into (frontmatter_yaml, body).

    The Claude subagent format is ``--- <yaml> --- <body>``. Leading HTML
    comments (the read-only provenance banner this renderer stamps) precede the
    opening fence, so we scan for the first non-blank, non-comment line and
    require it to be the ``---`` fence, then capture up to the closing fence.
    Raises ProfileError if no valid frontmatter block is present.
    """

    lines = md_text.splitlines()
    idx = 0
    # Skip the leading provenance comment banner + blank lines before the fence.
    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped or (stripped.startswith("<!--")):
            idx += 1
            continue
        break
    if idx >= len(lines) or lines[idx].strip() != "---":
        raise ProfileError(
            "claude_projection_native: subagent .md does not open with a '---' "
            "YAML frontmatter fence"
        )
    open_fence = idx
    close_fence = -1
    for j in range(open_fence + 1, len(lines)):
        if lines[j].strip() == "---":
            close_fence = j
            break
    if close_fence == -1:
        raise ProfileError(
            "claude_projection_native: subagent .md frontmatter has no closing "
            "'---' fence"
        )
    frontmatter = "\n".join(lines[open_fence + 1 : close_fence])
    body = "\n".join(lines[close_fence + 1 :])
    return frontmatter, body


def run_claude_projection_native(repo: Path) -> KernelResult:
    """Execution proof: the Claude projection is a REAL Claude-native .md subagent.

    Imports the read-only renderer (support/connection/agent_resources.py) and
    asserts, BY EXECUTION over admitted Agent Objects, that render_claude_subagent_md:

      (a) parses as a real Claude subagent file -- '---' YAML frontmatter '---'
          plus a body -- and the frontmatter carries the required name +
          description + tools keys;
      (b) REAL tool-policy mapping: the dev agent (tool-policy:read-write-scoped)
          tools INCLUDE Edit, Write, and Bash; a leader/reviewer agent (read-only
          policy) tools EXCLUDE Edit/Write/Bash -- so making the tool list a constant
          (ignoring policy) turns this RED (this is the load-bearing FIRE pin);
      (c) materially DIFFERENT from the codex form: the codex render is valid
          TOML; the claude render is markdown-with-frontmatter that does NOT
          parse as a Codex subagent TOML table (real translation, not a relabel);
      (d) the "enforced by Brick MCP" honesty note is present in the body.

    This is checker-layer support evidence only: it imports the renderer
    in-process, runs no subprocess, writes no file, and chooses no Movement. The
    renderer it pins is itself read-only (no subprocess in connection/).
    """

    import tomllib

    from support.checkers.lib.yaml_subset import parse_yaml_subset

    repo_text = str(repo)
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)
    _ensure_import_identity(repo)
    agent_resources = importlib.import_module("support.connection.agent_resources")

    list_refs = agent_resources.list_agent_object_refs
    render_md = agent_resources.render_claude_subagent_md
    render_toml = agent_resources.render_codex_subagent_toml
    render_claude_seed = agent_resources.render_claude_projection_seed

    refs = list(list_refs(repo))
    if not refs:
        raise ProfileError(
            "claude_projection_native: no admitted Agent Object refs to project"
        )

    roles = [ref.removeprefix("agent-object:") for ref in refs]

    def _tool_list(role: str) -> list[str]:
        md_text = render_md(role, repo_root=repo)
        frontmatter, body = _split_claude_frontmatter(md_text)
        parsed = parse_yaml_subset(frontmatter)
        if not isinstance(parsed, Mapping):
            raise ProfileError(
                f"claude_projection_native: {role!r} frontmatter is not a YAML "
                "mapping"
            )
        for required_key in ("name", "description", "tools"):
            value = parsed.get(required_key)
            if not isinstance(value, str) or not value.strip():
                raise ProfileError(
                    f"claude_projection_native: {role!r} frontmatter missing "
                    f"required Claude subagent key {required_key!r}"
                )
        if parsed.get("name") != role:
            raise ProfileError(
                f"claude_projection_native: {role!r} frontmatter name must equal "
                "the role"
            )
        if "enforced by Brick MCP" not in body:
            raise ProfileError(
                f"claude_projection_native: {role!r} body is missing the 'enforced "
                "by Brick MCP' honesty note (return shape / Link / evidence are "
                "not native-Claude-expressible)"
            )
        return [tool.strip() for tool in str(parsed["tools"]).split(",") if tool.strip()]

    # (a) + (d): every admitted role must yield a parseable subagent .md with the
    # required keys and the Brick-MCP honesty note. Split into write/read-only by
    # the REAL tool mapping (Edit + Write + Bash present == write-capable).
    write_tool_names = {"Edit", "Write", "Bash"}
    write_roles: list[str] = []
    read_only_roles: list[str] = []
    inspected = 0
    for role in roles:
        tools = _tool_list(role)
        tool_set = set(tools)
        if write_tool_names.issubset(tool_set):
            write_roles.append(role)
        elif tool_set.isdisjoint(write_tool_names):
            read_only_roles.append(role)
        else:
            raise ProfileError(
                f"claude_projection_native: {role!r} tools list is half-write "
                f"(Edit/Write/Bash must be all present or all absent), got {tools}"
            )
        inspected += 1

    # (b) REAL tool-policy mapping, not a constant. The dev agent
    # (tool-policy:read-write-scoped) MUST include Edit AND Write; a leader and a
    # reviewer (read-only policies) MUST exclude both. Making the tools list a
    # constant (ignoring tool policy) is what this FIRE pin catches.
    if "dev" in roles:
        dev_tools = _tool_list("dev")
        if not write_tool_names.issubset(set(dev_tools)):
            raise ProfileError(
                "claude_projection_native: dev (tool-policy:read-write-scoped) "
                f"tools must INCLUDE Edit, Write, and Bash, got {dev_tools}"
            )
    if not write_roles:
        raise ProfileError(
            "claude_projection_native: no role's tools include Edit/Write/Bash; a "
            "constant read-only tools list would hide the read-write-scoped "
            "worker (mapping is not real)"
        )
    if not read_only_roles:
        raise ProfileError(
            "claude_projection_native: no role's tools exclude Edit/Write/Bash; a "
            "constant write-capable tools list would over-grant every "
            "leader/reviewer (mapping is not real)"
        )

    # (e) PER-STEP write_need gate. The per-agent .md above is the DESCRIPTIVE
    # max-capability projection; the RUN-TIME provider projection FOR A STEP must
    # additionally gate the tool set on the step's Brick write NEED. A
    # write-capable agent (read-write-scoped) on a read-only Brick (write_need
    # False) MUST project a tool set with NO Edit/Write/Bash -- the agent's CAPABILITY
    # must never override the Brick NEED. Removing the write_need gate (back to
    # keying on tool_policy alone) turns this RED.
    tools_for_policies = agent_resources.claude_tools_for_tool_policies
    write_capable_policies = ["tool-policy:leader-coordination", "tool-policy:read-write-scoped"]
    leak_tools = list(tools_for_policies(write_capable_policies, write_need=False)["tools"])
    if not write_tool_names.isdisjoint(set(leak_tools)):
        raise ProfileError(
            "claude_projection_native: a write-capable agent on a read-only Brick "
            f"(write_need=False) must project a tool set with NO Edit/Write/Bash, got "
            f"{leak_tools} (capability overrode the Brick NEED)"
        )
    write_tools = list(tools_for_policies(write_capable_policies, write_need=True)["tools"])
    if not write_tool_names.issubset(set(write_tools)):
        raise ProfileError(
            "claude_projection_native: a write-capable agent on a write-needed "
            f"Brick (write_need=True) must project a tool set INCLUDING Edit, "
            f"Write, and Bash, got {write_tools} (over-restricted a legitimate write)"
        )

    # (c) materially DIFFERENT from the codex form: the claude render is markdown
    # with YAML frontmatter; the codex render is valid TOML. Assert codex != claude
    # shape -- the claude .md must NOT parse as a Codex subagent TOML table, and
    # the two texts must not be byte-identical.
    probe_role = "dev" if "dev" in roles else roles[0]
    claude_md = render_md(probe_role, repo_root=repo)
    codex_toml = render_toml(probe_role, repo_root=repo)
    if claude_md.strip() == codex_toml.strip():
        raise ProfileError(
            "claude_projection_native: claude .md is byte-identical to the codex "
            "TOML (relabel, not a real translation)"
        )
    claude_is_codex_toml = False
    try:
        claude_parsed = tomllib.loads(claude_md)
        claude_is_codex_toml = isinstance(
            claude_parsed.get("name"), str
        ) and isinstance(claude_parsed.get("developer_instructions"), str)
    except tomllib.TOMLDecodeError:
        claude_is_codex_toml = False
    if claude_is_codex_toml:
        raise ProfileError(
            "claude_projection_native: the claude .md also parses as a Codex "
            "subagent TOML; the claude projection is not a materially different "
            "form"
        )

    # The wired Claude projection seed must surface the real .md + tools without
    # dropping the existing generic instruction text other consumers rely on, and
    # without leaking the codex toml key into the claude seed.
    seed = render_claude_seed(probe_role, repo_root=repo)
    if "rendered_claude_subagent_md" not in seed:
        raise ProfileError(
            "claude_projection_native: render_claude_projection_seed dropped the "
            "rendered_claude_subagent_md key"
        )
    if "claude_tools" not in seed:
        raise ProfileError(
            "claude_projection_native: render_claude_projection_seed dropped the "
            "claude_tools key"
        )
    if "rendered_instruction_text" not in seed:
        raise ProfileError(
            "claude_projection_native: render_claude_projection_seed dropped the "
            "existing rendered_instruction_text key (would break other consumers)"
        )
    if "rendered_codex_subagent_toml" in seed:
        raise ProfileError(
            "claude_projection_native: the claude seed leaked the codex "
            "rendered_codex_subagent_toml key (host seeds must not cross-leak)"
        )
    seed_frontmatter, _ = _split_claude_frontmatter(seed["rendered_claude_subagent_md"])
    if parse_yaml_subset(seed_frontmatter).get("name") != probe_role:
        raise ProfileError(
            "claude_projection_native: seed rendered_claude_subagent_md is not the "
            "role's valid subagent .md"
        )

    return KernelResult(
        check_id="claude_projection_native",
        inspected=inspected,
        output=(
            "claude projection native passed: "
            f"{inspected} Agent Object(s) rendered valid Claude-native subagent .md "
            f"(write={sorted(write_roles)}, read-only count={len(read_only_roles)}); "
            "real tool-policy -> tools allow/deny mapping (dev and write-capable "
            "leaders have Edit+Write+Bash, reviewers remain read-only), honesty note "
            "present, materially different from the codex TOML form"
        ),
    )


# ---------------------------------------------------------------------------
# AGENT-SESSION-ID-REDACTION guard (TREASURE PORT 2, 0611). Lifted from the
# never-merged codex/agent-axis-slice-a-0605 branch
# (2d44fc7:support/checkers/lib/kernel_checks.py:1188-1273, regexes + scan
# logic verbatim) and adapted to today's tree: the archive/ museum W2 moved
# frozen history into is now a scan root, and the branch's "zero-tolerance, no
# allowlist" stance (it REDACTED its 45 historical sites) is replaced by the
# 0611 operator policy: frozen building evidence and archived history are NOT
# rewritten; the investigator-verified legacy leaks are carried on an explicit
# per-path allowlist of frozen line-content hashes (codex-review tightening C
# replaced the original line-COUNT budgets, which let a same-count swap
# through), and any NEW leak fails closed.
#
# AGENTS principle: a provider-specific (or runtime) session id must NEVER be
# stored in a support record, projection, or evidence surface. The adapter
# exception frontier scrubs them at the durable boundary
# (support/operator/run.py::_safe_exception_excerpt); this is the STATIC
# counterpart that forbids a raw session id from being committed into the kernel
# status records, building work/evidence, the review dispositions, or the
# archived history.
#
# Detection (layout-robust; the branch's first cut demanded a same-line cue and
# so MISSED the dominant real layouts -- a "Claude session id:" label line above
# a UUID in a fenced ```text block, and "PID / <uuid>" subagent rows). Now:
#   * ANY RFC-4122-shaped UUID (incl. UUIDv7) OR Crockford-base32 ULID, with NO
#     cue requirement. Legit identifiers in these roots are slug ids and 64-hex
#     sha256 hashes, which are never UUID/ULID-shaped, so a bare one here is
#     always a runtime/session/run id (re-verified on today's tree 0611: every
#     hit in the scan roots is one of the 6 allowlisted legacy session-id sites).
#   * keyed forms  session_id / session_token / provider_session / resume_token /
#     conversation_id / continuation_id : <v> (also "key":"<v>" compact JSON and
#     camelCase/prefixed keys via a lazy [\w-]*? prefix; the value must contain a
#     digit, so "session id: unknown" is NOT flagged)
#   * prefixed value tokens  sess_/sess- / provider-session- / resume-token- /
#     chatcmpl- / ya29. (Google OAuth) / JWT (eyJ.x.y)  (the underscore/dash
#     forms require a digit in the value, so prose like "provider-session-looking"
#     is NOT flagged)
# Deliberately OUT of static scope (ACCEPTED RESIDUAL, zero live instances): a
# generic provider OBJECT-id prefix sweep (run_/msg_/resp_/thread_/step_/...) is
# NOT flagged here because it collides with legitimate dev identifiers
# (run_compose0, run_gemini35_flash); and note the run.py error-text redactor
# does NOT sweep those prefixes either, so there is no separate compensating
# control for them. A bare opaque token with no session key and no known shape
# (e.g. a dash-less 32-hex id, which would collide with MD5) is likewise not
# statically detectable without false-positives. The standing guarantee for
# those is that the engine must not STORE provider ids in the first place (the
# run.py exception-frontier redactor scrubs the KNOWN session formats).
_SESSION_ID_VALUE_TOKEN_RES = (
    # sess_ AND sess- (OpenAI emits both underscore and dash session prefixes).
    re.compile(r"(?i)\bsess[_-](?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{6,}"),
    re.compile(r"(?i)\bprovider-session-(?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{6,}"),
    re.compile(r"(?i)\bresume[_-]token[_-](?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{6,}"),
    re.compile(r"(?i)\bchatcmpl-[A-Za-z0-9]{6,}"),
    re.compile(r"\bya29\.[A-Za-z0-9._-]{10,}"),                                    # Google OAuth token
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{4,}"),  # JWT (3 segments)
)
# Bare ULID (Crockford base32, 26 chars, excludes I/L/O/U) -- some providers issue
# ULID session ids. Empirically FP-clean: legit ids in the scan roots are slug URNs
# + 64-hex sha256, neither of which is a 26-char uppercase ULID.
_SESSION_ID_ULID_RE = re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b")
# Quoted-or-bare session key followed by an id-shaped value. Covers the KV form
# (session_id: <uuid>), compact JSON ("session_id":"01HX..."), AND camelCase /
# prefixed keys (providerSessionId, chat_session_id) via the lazy [\w-]*? prefix.
# The value lookahead requires a DIGIT so a real id (UUID/ULID/chatcmpl all carry
# digits) is caught while prose like "session id: unknown" is not; and the value
# class excludes '<', so the "<redacted-session-id>" placeholder is NOT re-flagged.
_SESSION_ID_KEYED_RE = re.compile(
    r"(?i)['\"]?\b[\w-]*?"
    r"(?:session[ _-]?id|session[ _-]?token|provider[ _-]?session|resume[ _-]?token"
    r"|conversation[ _-]?id|continuation[ _-]?id)"
    r"\b['\"]?\s*[:=]\s*['\"]?(?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{6,}"
)
_SESSION_ID_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
# PROJECT-0 S1-C: project scan roots are derived PER VESSEL (every
# project/<id>/buildings + project/<id>/status — a new project must never be a
# silently unscanned landing zone for session-id leaks; widened 0611 from
# project #1's status/kernel to full status/, re-verified 0 offenders). The
# static roots stay literal. The frozen-history allowlist below is keyed by
# exact path and is unchanged by this widening.
_SESSION_ID_STATIC_SCAN_ROOTS = (
    "support/docs/reviews",
    # CLEAN-YARD v3 (0611): the archive/ museum root left for the frozen
    # history repo; the per-vessel project roots + reviews remain the scan
    # surface (a resurrected archive/ would be rejected by path admission
    # before it could become a landing zone).
)


def _session_id_scan_roots(repo: Path) -> tuple[str, ...]:
    project_roots = [
        to_posix(path.relative_to(repo))
        for pattern in ("*/buildings", "*/status")
        for path in sorted((repo / "project").glob(pattern))
        if path.is_dir()
    ]
    return tuple(project_roots) + _SESSION_ID_STATIC_SCAN_ROOTS
_SESSION_ID_SCAN_SUFFIXES = (".md", ".json", ".jsonl", ".txt")
# FROZEN-HISTORY ALLOWLIST — EMPTY in the product repo (REPO-SPLIT seed 0611,
# checker-split-map-0611.md ⚠1): the 6-file/8-line frozen legacy allowlist
# moved to the history repo WITH the files it froze. The one allowlisted file
# that ships product-side (the p9 catalog dogfood work record) had its single
# legacy session-id line REDACTED in the product copy instead of carried as an
# allowlist row, so a new user's evidence tree starts with ZERO tolerated
# session-id lines. Any future entry here requires the same discipline the
# history repo used: path -> tuple of sha256[:16] digests of the EXACT
# offending line content (a ceiling, not a pin — see run_agent_session_id_redaction).
_SESSION_ID_LEGACY_ALLOWLIST: dict[str, tuple[str, ...]] = {
    # 0612 (F11 evidence, frozen): building adapter-30-s2-s3-submit-resume's QA
    # honestly DESCRIBED its negative probe and embedded the RFC example UUID
    # (123e4567-...) in the probe text — not a real session id. The same
    # observation also reports the F11 gap (UUID accepted in dict-KEY position
    # by the submission rejector), queued for repair. Two lines, digest-frozen.
    "project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/evidence/claim_trace/agent/returned_claims.json": ("8cdb07e6a732f184",),
    "project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/work/step-outputs/adapter-30-s2-s3-submit-resume-code-attack-qa-attempt-1/step-output.json": ("d55e8f20f0e2107a",),
    "project/brick-protocol/buildings/adapter-30-s2-s3-submit-resume/raw/agent-return.jsonl": ("be1f92f79aac6848",),
}


def _session_line_digest(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:16]


def _line_carries_session_id(line: str) -> bool:
    if _SESSION_ID_UUID_RE.search(line) or _SESSION_ID_ULID_RE.search(line):
        return True
    if _SESSION_ID_KEYED_RE.search(line):
        return True
    if any(pattern.search(line) for pattern in _SESSION_ID_VALUE_TOKEN_RES):
        return True
    return False


def _session_id_redaction_fire_probe() -> None:
    """Built-in anti-tautological FIRE probe (CLEAN-YARD v3, ⚠ §1-1).

    The product allowlist is EMPTY and the product tree carries zero leaks, so
    without a probe the scan could silently stop matching and stay green. On
    every invocation this builds a TEMP repo with one synthetic vessel whose
    status/kernel record carries a fake provider session id (a bare UUID --
    the dominant real leak layout) and asserts the REAL scan path reports it;
    then asserts the same vessel WITHOUT the leak scans clean. The temp tree
    is removed by the TemporaryDirectory context. A probe that does not fire
    raises ProfileError, so --all EXITs non-zero.
    """

    # One leak line PER detection family, each crafted so only ITS matcher
    # catches it -- disabling any single family (bare UUID / bare ULID /
    # keyed session form / prefixed value token) leaves its line unmatched and
    # the probe RED. A single combined line would let one family die silently
    # behind another.
    family_leaks = {
        "bare-uuid": "subagent row " + _chat_session_probe_uuid_text(),
        "bare-ulid": "subagent row " + _chat_session_probe_ulid_text(),
        "keyed-session": "conversation_id: abc123def456ghi",
        "value-token": "transport sess_a1b2c3d4e5f6g7",
    }
    with tempfile.TemporaryDirectory(prefix="bp-session-id-fire-") as tmp:
        probe_repo = Path(tmp)
        kernel_dir = probe_repo / "project" / "fire-probe-vessel" / "status" / "kernel"
        kernel_dir.mkdir(parents=True)
        leak_doc = kernel_dir / "fire-probe-record.md"
        body_lines = ["# synthetic FIRE probe record", ""]
        family_lineno: dict[str, int] = {}
        for family, leak in family_leaks.items():
            body_lines.append(leak)
            family_lineno[family] = len(body_lines)
        leak_doc.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
        offenders = _collect_session_id_offenders(probe_repo)[0]
        offender_linenos: set[int] = set()
        for entry in offenders:
            tail = entry.rsplit(":", 1)[-1].split(" ")[0]
            if tail.isdigit():
                offender_linenos.add(int(tail))
        for family, lineno in family_lineno.items():
            if lineno not in offender_linenos:
                raise ProfileError(
                    "agent_session_id_redaction FIRE probe did NOT fire for the "
                    f"{family} detection family: a synthetic session-id leak in a "
                    "temp-generated vessel was not reported (that matcher has "
                    "stopped matching; the empty-allowlist green is no longer "
                    "trustworthy)"
                )
        leak_doc.write_text(
            "# synthetic FIRE probe record\n\nno session id here\n", encoding="utf-8"
        )
        clean_offenders = _collect_session_id_offenders(probe_repo)[0]
        if clean_offenders:
            raise ProfileError(
                "agent_session_id_redaction FIRE probe over-fired: a clean "
                f"synthetic vessel reported offenders: {clean_offenders[:3]}"
            )


def _collect_session_id_offenders(repo: Path) -> tuple[list[str], int, dict[str, int]]:
    inspected = 0
    offenders: list[str] = []
    allowlisted_lines: dict[str, int] = {}
    for root_rel in _session_id_scan_roots(repo):
        root = repo / root_rel
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in _SESSION_ID_SCAN_SUFFIXES:
                continue
            inspected += 1
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = to_posix(path.relative_to(repo))
            frozen = _SESSION_ID_LEGACY_ALLOWLIST.get(rel)
            hits = [
                (lineno, line)
                for lineno, line in enumerate(text.splitlines(), start=1)
                if _line_carries_session_id(line)
            ]
            if frozen is None:
                offenders.extend(f"{rel}:{lineno}" for lineno, _line in hits)
                continue
            remaining = Counter(frozen)
            matched = 0
            for lineno, line in hits:
                digest = _session_line_digest(line)
                if remaining.get(digest, 0) > 0:
                    remaining[digest] -= 1
                    matched += 1
                else:
                    offenders.append(
                        f"{rel}:{lineno} (offending line's content hash {digest} is "
                        "not a frozen allowlisted legacy line of this file; a "
                        "same-count replacement, swap, or addition is a NEW leak)"
                    )
            if matched:
                allowlisted_lines[rel] = matched
    return offenders, inspected, allowlisted_lines


def run_agent_session_id_redaction(repo: Path) -> KernelResult:
    # RED-first: prove the scan still fires on a synthetic leak in a
    # temp-generated vessel before trusting the live tree's green.
    _session_id_redaction_fire_probe()
    offenders, inspected, allowlisted_lines = _collect_session_id_offenders(repo)
    if offenders:
        listing = "\n".join(offenders[:25])
        raise ProfileError(
            "provider/runtime session id present in a support record, building "
            "work/evidence, review disposition, or archived history outside the "
            "frozen-history allowlist; it must be redacted per the AGENTS "
            "session-id principle:\n"
            f"{listing}"
        )
    return KernelResult(
        check_id="agent_session_id_redaction",
        inspected=inspected,
        output=(
            "FIRE probe fired (synthetic leak in a temp vessel RED); no NEW "
            "provider/runtime session id in scanned support records, "
            "building work/evidence, review dispositions, or archived history; "
            f"{len(allowlisted_lines)} frozen-history legacy file(s) whose "
            f"{sum(allowlisted_lines.values())} offending line(s) all matched "
            "their frozen content hashes."
        ),
    )

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
    to_posix,
    to_repo_path,
)
from support.checkers.lib.provider_preflight_check import (
    _PROVIDER_PREFLIGHT_AUTHED_LITERALS,
    _PROVIDER_PREFLIGHT_REQUIRED_KEYS,
    _provider_preflight_assert_shape,
    run_provider_preflight,
)
from support.checkers.lib.onboard_smoke_check import (
    _ONBOARD_SMOKE_REQUIRED_KEYS,
    run_onboard_smoke,
    _onboard_smoke_assert_shape,
)


_AXIS_VOCAB_EXPECTED_MOVEMENT = ("forward", "reroute")


_AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS = ("raise", "forward", "stop", "reroute")


_AXIS_VOCAB_EXPECTED_DISPOSITION_OWNERS = ("caller", "coo", "caller-or-coo")


_AXIS_VOCAB_EXPECTED_PROGRESS_STATES = ("in_progress",)


_AXIS_VOCAB_EXPECTED_AUTHOR_PREFIXES = ("human:", "coo:")


_AXIS_VOCAB_REQUIRED_TRANSITION_KEYS = (
    "disposition_action",
    "budget_increment",
    "progress_state",
)


# S-5: concern_kind code<->doc parity. The closed concern_kind vocabulary lives
# in code as agent/return_fact.py:TRANSITION_CONCERN_KINDS (the source of truth)
# and is documented in AGENTS.md under this header line as a fenced ```text```
# block (one value per line). The parity check compares the two directly and
# fails on any divergence in either direction; it hardcodes NO third copy of the
# values, so the values themselves are pinned only at the code surface.
_AXIS_VOCAB_CONCERN_KIND_SOURCE = "agent/return_fact.py"
_AXIS_VOCAB_CONCERN_KIND_CONST = "TRANSITION_CONCERN_KINDS"
_AXIS_VOCAB_CONCERN_KIND_DOC = "AGENTS.md"
_AXIS_VOCAB_CONCERN_KIND_DOC_HEADER = (
    "Agent transition concerns use the closed `concern_kind` vocabulary:"
)


_AXIS_VOCAB_EXPECTED_ADAPTER_REFS = (
    "adapter:local",
    "adapter:codex-local",
    # ADDITIVE: 1:1 Sakana variant of codex-local (same codex executable +
    # codex-exec invocation; provider-routing -c overrides carried as DATA).
    "adapter:codex-fugu-local",
    "adapter:claude-local",
    "adapter:gemini-local",
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
        "disposition_action: raise | forward | stop | reroute",
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
    # MODULE-SEP god-module split: the single-source ALLOWED_ADAPTER_REFS literal
    # relocated from agent_adapter.py into the adapter_constants.py sibling (the
    # agent_adapter facade + agent_resources both re-import it from there via the
    # facade). The literal-set pin follows the moved symbol to its new home; the
    # invariant (the set equals the expected refs and admits no retired write ref)
    # is unchanged.
    adapter_constants_rel = "support/connection/adapter_constants.py"
    adapter_tree, _adapter_text = _axis_vocab_parse_python(repo, adapter_constants_rel)
    adapter_env = _axis_vocab_module_env(adapter_tree)
    adapter_refs = _axis_vocab_set(
        adapter_env,
        "ALLOWED_ADAPTER_REFS",
        adapter_constants_rel,
    )
    expected_adapter_refs = frozenset(_AXIS_VOCAB_EXPECTED_ADAPTER_REFS)
    if adapter_refs != expected_adapter_refs:
        violations.append(
            f"{adapter_constants_rel}: ALLOWED_ADAPTER_REFS must equal "
            f"{sorted(expected_adapter_refs)}, observed {sorted(adapter_refs)}"
        )
    retired_adapter_refs = sorted(set(_AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS) & set(adapter_refs))
    if retired_adapter_refs:
        violations.append(
            f"{adapter_constants_rel}: retired write adapter refs must not be "
            f"admitted active adapters: {retired_adapter_refs}"
        )

    resources_tree, _resources_text = _axis_vocab_parse_python(
        repo,
        "support/connection/agent_resources.py",
    )
    # MODULE-SEP god-module split (route-B, facade removed): ALLOWED_ADAPTER_REFS
    # now lives in the adapter_constants.py leaf, so the import-source pin follows
    # the moved symbol to its real new home; adapter_is_write_capable stays a CORE
    # symbol on agent_adapter. The invariant (resources imports both from their
    # canonical single-source home and reads them) is unchanged.
    constants_imports = _axis_vocab_import_aliases(resources_tree, "adapter_constants")
    adapter_imports = _axis_vocab_import_aliases(resources_tree, "agent_adapter")
    allowed_alias = constants_imports.get("ALLOWED_ADAPTER_REFS")
    write_capability_alias = adapter_imports.get("adapter_is_write_capable")
    if not allowed_alias:
        violations.append(
            "support/connection/agent_resources.py: must import ALLOWED_ADAPTER_REFS "
            "from .adapter_constants"
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


def _axis_vocab_doc_fenced_block(text: str, header: str) -> frozenset[str] | None:
    """Return the values in the first ```text``` fenced block after `header`.

    Reads one bare value per non-empty line inside the fence. Returns None when
    the header or its following fenced block is absent (so the caller can report
    a precise missing-doc-block violation rather than a silent empty match).
    """
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if header in line)
    except StopIteration:
        return None
    fence_open: int | None = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip().startswith("```"):
            fence_open = i
            break
    if fence_open is None:
        return None
    values: set[str] = set()
    for i in range(fence_open + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("```"):
            return frozenset(values)
        if stripped:
            values.add(stripped)
    return None


def _axis_vocab_check_concern_kind_parity(repo: Path, violations: list[str]) -> None:
    return_fact_tree, _return_fact_text = _axis_vocab_parse_python(
        repo, _AXIS_VOCAB_CONCERN_KIND_SOURCE
    )
    return_fact_env = _axis_vocab_module_env(return_fact_tree)
    code_kinds = _axis_vocab_set(
        return_fact_env,
        _AXIS_VOCAB_CONCERN_KIND_CONST,
        _AXIS_VOCAB_CONCERN_KIND_SOURCE,
    )

    doc_text = to_repo_path(repo, _AXIS_VOCAB_CONCERN_KIND_DOC).read_text(encoding="utf-8")
    doc_kinds = _axis_vocab_doc_fenced_block(doc_text, _AXIS_VOCAB_CONCERN_KIND_DOC_HEADER)
    if doc_kinds is None:
        violations.append(
            f"{_AXIS_VOCAB_CONCERN_KIND_DOC}: missing the closed concern_kind vocabulary "
            f"fenced block under header {_AXIS_VOCAB_CONCERN_KIND_DOC_HEADER!r}"
        )
        return

    missing_in_doc = sorted(code_kinds - doc_kinds)
    extra_in_doc = sorted(doc_kinds - code_kinds)
    if missing_in_doc:
        violations.append(
            f"{_AXIS_VOCAB_CONCERN_KIND_DOC}: closed concern_kind vocabulary missing "
            f"{_AXIS_VOCAB_CONCERN_KIND_SOURCE}:{_AXIS_VOCAB_CONCERN_KIND_CONST} value(s): "
            f"{', '.join(missing_in_doc)}"
        )
    if extra_in_doc:
        violations.append(
            f"{_AXIS_VOCAB_CONCERN_KIND_DOC}: closed concern_kind vocabulary lists value(s) "
            f"absent from {_AXIS_VOCAB_CONCERN_KIND_SOURCE}:{_AXIS_VOCAB_CONCERN_KIND_CONST}: "
            f"{', '.join(extra_in_doc)}"
        )


def run_axis_vocab_drift(repo: Path) -> KernelResult:
    violations: list[str] = []
    _axis_vocab_check_link_sources(repo, violations)
    _axis_vocab_check_transition_author_prefix_consumers(repo, violations)
    _axis_vocab_check_docs(repo, violations)
    _axis_vocab_check_concern_kind_parity(repo, violations)
    _axis_vocab_check_agent_adapter_refs(repo, violations)
    scanned = _axis_vocab_scan_exact_enum_redefinitions(repo, violations)
    if violations:
        detail = "\n".join(f"- {violation}" for violation in violations)
        raise ProfileError(f"kernel check axis_vocab_drift rejected evidence:\n{detail}")
    return KernelResult(
        check_id="axis_vocab_drift",
        inspected=scanned + 6,
        output=(
            "axis vocab drift passed: parsed Link Movement/transition sources, "
            "transition author-prefix consumers, AGENTS/current packet text, "
            "Agent concern_kind code<->doc parity, Agent adapter refs, and scanned "
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
    runs the SAME ``validate_building_plan_boundary`` over EVERY linear and
    graph plan in brick/building_plans/, so those single-sourced per-plan
    structural guards survive as one general kernel-check and the per-profile
    pins can retire.

    Stepless / non-Building-plan fixtures are skipped; their count is reported,
    never silently absorbed. A real boundary violation on any linear or graph
    plan raises ProfileError -> --all RED.

    HARDENED (guard-before-retire): when the linear yaml-subset parser fails on a
    plan, fall back to PyYAML (yaml.safe_load). If PyYAML yields a dict with a
    non-empty ``steps`` list or ``plan_shape: graph``, the plan is a real
    Building Plan that the subset parser merely could not read, so it is
    validated via the SAME ``validate_building_plan_boundary`` (no silent skip).
    Only truly stepless / non-Building-plan fixtures are skipped. A now-included
    plan that genuinely fails validation is surfaced (--all RED), never hidden.
    The number of PyYAML-recovered plans is reported separately.
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
    linear_validated = 0
    graph_validated = 0
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
            if not isinstance(recovered, Mapping):
                skipped += 1
                continue
            recovered_steps = recovered.get("steps")
            recovered_is_linear = isinstance(recovered_steps, list) and bool(recovered_steps)
            recovered_is_graph = recovered.get("plan_shape") == "graph"
            if not (recovered_is_linear or recovered_is_graph):
                skipped += 1  # stepless / non-Building-plan fixture
                continue
            # Real linear/graph plan the subset parser missed; validate it
            # (surface any genuine failure rather than hiding it). This is
            # STRUCTURAL validation of historical plans, so retired write-adapter
            # refs are tolerated here (adapter activeness is enforced at run time,
            # not in the boundary sweep).
            validate_building_plan_boundary(
                recovered, rel, admitted, repo, allow_retired_write_adapter_refs=True
            )
            if recovered_is_graph:
                graph_validated += 1
            else:
                linear_validated += 1
            pyyaml_recovered += 1
            continue
        steps = plan.get("steps")
        is_linear = isinstance(steps, list) and bool(steps)
        is_graph = plan.get("plan_shape") == "graph"
        if not (is_linear or is_graph):
            skipped += 1  # stepless / non-Building-plan fixture
            continue
        # Reuses the EXACT per-profile boundary validator; a violation raises
        # ProfileError, which fails the check (no swallowing of real failures).
        # Structural sweep over historical plans: retired write-adapter refs are
        # tolerated here (adapter activeness is enforced at run time, not here).
        validate_building_plan_boundary(
            plan, rel, admitted, repo, allow_retired_write_adapter_refs=True
        )
        if is_graph:
            graph_validated += 1
        else:
            linear_validated += 1
    validated = linear_validated + graph_validated
    return KernelResult(
        check_id="building_plans_boundary_sweep",
        inspected=validated,
        output=(
            f"building plans boundary sweep passed: {validated} building "
            f"plan(s) validated (Brick owner_axis + plan_ref + non-empty steps + "
            f"declared-plan validation + per-step rows; {linear_validated} linear, "
            f"{graph_validated} graph via declared graph projection; {pyyaml_recovered} "
            f"PyYAML-recovered from subset-parse failure); {skipped} stepless / "
            f"non-Building-plan fixture(s) skipped."
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
    # Manifest-shape pin (H4): skill_resources must be a fetch-on-demand MANIFEST
    # (ref + kind=skill-manifest + path), NOT eager inline bodies. A regression that
    # re-inlines the body (a 'body' key) is rejected, and the top-level
    # skill_manifest_refs stamp must mirror the rows so the DECLARED audit stays
    # honest (the OBSERVED fetch is not proven; only the offered set is recorded).
    skill_resources = packet.get("skill_resources")
    for row in skill_resources:  # non-empty list already asserted above
        if not isinstance(row, Mapping):
            raise ProfileError("agent instruction packet skill_resources row must be a mapping")
        if row.get("kind") != "skill-manifest":
            raise ProfileError(
                "agent instruction packet skill_resources row must be a skill-manifest "
                f"item (kind=skill-manifest), got kind={row.get('kind')!r}"
            )
        if not row.get("ref") or not row.get("path"):
            raise ProfileError("agent instruction packet skill-manifest row must carry ref + path")
        if "body" in row:
            raise ProfileError(
                "agent instruction packet skill_resources regressed to an EAGER body "
                "(a manifest row must not inline the SKILL.md body)"
            )
    manifest_refs = packet.get("skill_manifest_refs")
    if not isinstance(manifest_refs, list) or len(manifest_refs) != len(skill_resources):
        raise ProfileError(
            "agent instruction packet skill_manifest_refs stamp must mirror skill_resources "
            f"(got {manifest_refs!r})"
        )
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
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    request_fields = {field.name for field in fields(adapter.AgentAdapterRequest)}
    if "agent_instruction_packet" not in request_fields:
        raise ProfileError("AgentAdapterRequest must admit agent_instruction_packet")
    request = adapter.AgentAdapterRequest(
        building_id="agent-adapter-return-shape-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
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
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    adapter_grant_policy = importlib.import_module("brick_protocol.support.connection.adapter_grant_policy")
    adapter_local_cli = importlib.import_module("brick_protocol.support.connection.adapter_local_cli")
    write_scope = {
        "allowed_paths": ["support/connection/agent_adapter.py"],
        "forbidden_paths": [".git/**", ".env"],
        "commit_allowed": False,
        "push_allowed": False,
    }
    write_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if not adapter.agent_request_effective_write(write_request):
        raise ProfileError("codex-local write_scope request did not become effective_write")
    if adapter_local_cli._codex_sandbox_for_request(write_request) != "workspace-write":
        raise ProfileError("effective_write request did not select workspace-write sandbox")
    write_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            write_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
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
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
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

    # REDO (Smith 0623 struct-surgery): the adapter EXPOSES raw effective-write
    # request inputs and SUPPORT/RECORDING derives the named write-policy facts. The
    # request observer derives nothing and stops nothing.
    from brick_protocol.support.recording.agent_step_observation import (
        derive_effective_write_request_facts as _derive_write_policy_facts,
    )

    def _recorded_write_policy_facts(request: Any) -> tuple[str, ...]:
        return _derive_write_policy_facts(
            **adapter.agent_request_effective_write_raw_inputs(request)
        )

    # A write_scope WITHOUT the read-write tool policy no longer STOPS request
    # construction -- the dev Agent omitting tool-policy:read-write-scoped is RECORDED
    # (by support/recording) as missing_agent_write_policy, and the building continues.
    # Brick recommends, the Agent is free, the worktree isolates, merge-review is the
    # real gate. The probe asserts the request CONSTRUCTS (no raise) AND the recorded
    # fact carries the token.
    no_policy_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-negative-no-policy",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    no_policy_facts = _recorded_write_policy_facts(no_policy_request)
    if not any("missing_agent_write_policy" in fact for fact in no_policy_facts):
        raise ProfileError(
            "write_scope without read-write tool policy must be RECORDED as "
            f"missing_agent_write_policy (move+record only), observed {no_policy_facts!r}"
        )

    # A selected adapter whose mapping does not support observed workspace write
    # no longer STOPS construction
    # -- the disposition is RECORDED (by support/recording) as
    # missing_adapter_write_capability and the building continues. The probe asserts
    # the request CONSTRUCTS (no raise), never becomes effective_write, and the
    # recorded fact carries the token.
    unsupported_adapter_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-negative-unsupported-adapter",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if adapter.agent_request_effective_write(unsupported_adapter_request):
        raise ProfileError("read-only adapter write_scope request became effective_write")
    unsupported_adapter_facts = _recorded_write_policy_facts(unsupported_adapter_request)
    if not any(
        "missing_adapter_write_capability" in fact for fact in unsupported_adapter_facts
    ):
        raise ProfileError(
            "unsupported observed-write adapter with write_scope must be RECORDED as "
            f"missing_adapter_write_capability (move+record only), observed "
            f"{unsupported_adapter_facts!r}"
        )

    # P1 Adapter Authority Repair: gemini-local is a CLI adapter that may project
    # write_file / replace / run_shell_command ONLY through the same effective_write
    # intersection as codex/claude: Brick write_scope NEED + read-write-scoped Agent
    # policy + observed-write adapter mapping. These probes assert the positive and
    # the no-policy negative at the grant/projection layer before any live CLI call.
    gemini_write_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-gemini-local-positive",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if not adapter.agent_request_effective_write(gemini_write_request):
        raise ProfileError("gemini-local write_scope request did not become effective_write")
    gemini_allow, gemini_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(
        gemini_write_request
    )
    for required_tool in ("write_file", "replace", "run_shell_command"):
        if required_tool not in gemini_allow:
            raise ProfileError(
                "gemini-local effective_write did not allow write/shell tool "
                f"{required_tool!r}; allow={gemini_allow!r}"
            )
        if required_tool in gemini_deny:
            raise ProfileError(
                "gemini-local effective_write still denied write/shell tool "
                f"{required_tool!r}; deny={gemini_deny!r}"
            )
    gemini_write_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_write_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_write_rules = list(gemini_write_prompt.get("rules", []))
    if any("write and shell tools remain blocked" in rule for rule in gemini_write_rules):
        raise ProfileError("gemini-local effective_write prompt still says write/shell are blocked")
    if not any("write_file, replace, and run_shell_command" in rule for rule in gemini_write_rules):
        raise ProfileError("gemini-local effective_write prompt did not name scoped write/shell tools")

    inspector_packet = _agent_instruction_packet_for_role(repo, "inspector")
    gemini_probe_write_scope = {
        "allowed_paths": ["support/checkers/generated-probes/**"],
        "forbidden_paths": [".git/**", "agent/**", "brick/**", "link/**"],
        "commit_allowed": False,
        "push_allowed": False,
    }
    gemini_inspector_probe_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-gemini-local-inspector-probe",
        agent_object_ref="agent-object:inspector",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        hook_refs=("hook:reviewer-no-mutation",),
        write_scope=gemini_probe_write_scope,
        agent_instruction_packet=inspector_packet,
    )
    if not adapter.agent_request_effective_write(gemini_inspector_probe_request):
        raise ProfileError(
            "gemini-local inspector probe write_scope request did not become effective_write"
        )
    gemini_probe_allow, gemini_probe_deny = (
        adapter_grant_policy._gemini_admin_policy_partition_for_request(
            gemini_inspector_probe_request
        )
    )
    for required_tool in ("write_file", "replace", "run_shell_command"):
        if required_tool not in gemini_probe_allow:
            raise ProfileError(
                "gemini-local inspector effective probe_write did not allow write/shell tool "
                f"{required_tool!r}; allow={gemini_probe_allow!r}"
            )
        if required_tool in gemini_probe_deny:
            raise ProfileError(
                "gemini-local inspector effective probe_write still denied write/shell tool "
                f"{required_tool!r}; deny={gemini_probe_deny!r}"
            )
    gemini_probe_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_inspector_probe_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_probe_rules = list(gemini_probe_prompt.get("rules", []))
    if not gemini_probe_prompt.get("native_grant", {}).get("write_effective"):
        raise ProfileError("gemini-local inspector probe prompt did not carry write_effective")
    if any("write and shell tools remain blocked" in rule for rule in gemini_probe_rules):
        raise ProfileError(
            "gemini-local inspector effective probe_write prompt still says write/shell are blocked"
        )
    if not any("effective probe_write / verification_write" in rule for rule in gemini_probe_rules):
        raise ProfileError(
            "gemini-local inspector effective probe_write prompt did not name probe/verification write"
        )

    captured_gemini_write: dict[str, Any] = {}

    def _capture_gemini_write_runner(
        args: Sequence[str],
        cwd: Path,
        timeout: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del timeout
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return adapter.LocalCliCompleted(call, 0, "0.46.0", "")
        captured_gemini_write["args"] = call
        captured_gemini_write["cwd"] = cwd
        captured_gemini_write["env_has_api_key"] = bool(
            (env or {}).get("GEMINI_API_KEY") or (env or {}).get("GOOGLE_API_KEY")
        )
        if "--admin-policy" in call:
            policy_path = Path(call[call.index("--admin-policy") + 1])
            captured_gemini_write["policy_text"] = policy_path.read_text(encoding="utf-8")
        return adapter.LocalCliCompleted(
            call,
            0,
            json.dumps(
                {
                    "response": "{}",
                    "stats": {
                        "tools": {
                            "totalCalls": 3,
                            "byName": {
                                "write_file": 1,
                                "replace": 1,
                                "run_shell_command": 1,
                            },
                        }
                    },
                }
            ),
            "",
        )

    saved_env = {name: os.environ.get(name) for name in adapter._GEMINI_API_KEY_ENV_VARS}
    for name in adapter._GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "probe-key"
    adapter._mark_effective_write_observation_path(gemini_write_request, repo)
    try:
        gemini_write_result = adapter.connect_agent_brain(
            gemini_write_request,
            command_runner=_capture_gemini_write_runner,
            cwd=repo,
            timeout_seconds=5,
        )
    finally:
        for name in adapter._GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]
    if captured_gemini_write.get("cwd") != repo:
        raise ProfileError("gemini-local effective_write did not run from adapter cwd")
    if not captured_gemini_write.get("env_has_api_key"):
        raise ProfileError("gemini-local effective_write did not carry API-key env")
    policy_text = str(captured_gemini_write.get("policy_text", ""))
    for required_tool in ("write_file", "replace", "run_shell_command"):
        if required_tool not in policy_text:
            raise ProfileError(
                "gemini-local effective_write admin policy omitted write/shell tool "
                f"{required_tool!r}"
            )
    observed = tuple(
        gemini_write_result.adapter_raw_observations.get(
            "non_granted_gemini_tool_names",
            (),
        )
    )
    for required_tool in ("write_file", "replace", "run_shell_command"):
        if required_tool in observed:
            raise ProfileError(
                "gemini-local effective_write recorded a granted write/shell tool as "
                f"non-granted: {observed!r}"
            )

    gemini_no_policy_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-gemini-local-no-policy",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if adapter.agent_request_effective_write(gemini_no_policy_request):
        raise ProfileError("gemini-local write_scope without read-write policy became effective_write")
    no_policy_allow, no_policy_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(
        gemini_no_policy_request
    )
    for forbidden_tool in ("write_file", "replace", "run_shell_command"):
        if forbidden_tool in no_policy_allow or forbidden_tool not in no_policy_deny:
            raise ProfileError(
                "gemini-local no-policy request did not deny write/shell tool "
                f"{forbidden_tool!r}; allow={no_policy_allow!r} deny={no_policy_deny!r}"
            )

    for retired_adapter_ref in _AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS:
        try:
            adapter.AgentAdapterRequest(
                building_id="agent-effective-write-negative-retired-adapter",
                agent_object_ref="agent-object:dev",
                adapter_ref=retired_adapter_ref,
                brick_instance_ref="brick-work",
                next_brick_instance_ref="brick-closure",
                tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
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
            adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
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
    # A claude write request must select scoped write CLI knobs; an ambiguous
    # no-tool-policy claude read request must fail closed to the no-tool plan
    # shape. The separate read-tier probe covers read-only browse through the
    # declared tool list. Live in-scope/out-of-scope claude writes remain
    # NOT-PROVEN (no OS sandbox); these assert the knobs only.
    claude_write_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-claude-positive",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if not adapter.agent_request_effective_write(claude_write_request):
        raise ProfileError("claude-local write_scope request did not become effective_write")
    knobs = adapter_local_cli._claude_cli_invocation(claude_write_request)
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
    if knobs.get("allowed_tools") != knobs["tools"]:
        raise ProfileError(
            "claude effective_write did not project the scoped tool set into "
            f"allowed_tools; observed {knobs.get('allowed_tools')!r}"
        )
    if knobs["system_prompt"] != adapter._CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT:
        raise ProfileError("claude effective_write did not use the scoped-write system prompt")
    captured_claude_write_args: dict[str, tuple[str, ...]] = {}

    def _capture_claude_write_runner(
        args: Sequence[str],
        cwd: Path,
        timeout: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del cwd, timeout, env
        captured_claude_write_args["args"] = tuple(str(arg) for arg in args)
        return adapter.LocalCliCompleted(
            args=captured_claude_write_args["args"],
            return_code=0,
            stdout='{"result":"{}"}',
            stderr="",
        )

    adapter_local_cli._invoke_local_cli(
        adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CLAUDE_LOCAL],
        claude_write_request,
        "{}",
        cwd=repo,
        timeout_seconds=9,
        command_runner=_capture_claude_write_runner,
    )
    claude_write_args = captured_claude_write_args.get("args", ())
    if "--tools" not in claude_write_args:
        raise ProfileError("claude effective_write argv omitted --tools")
    if "--allowedTools" not in claude_write_args:
        raise ProfileError(
            "claude effective_write argv omitted --allowedTools; Bash/checker "
            "commands would remain provider-approval gated"
        )
    tools_arg = claude_write_args[claude_write_args.index("--tools") + 1]
    allowed_tools_arg = claude_write_args[claude_write_args.index("--allowedTools") + 1]
    if allowed_tools_arg != tools_arg:
        raise ProfileError(
            "claude effective_write argv allowedTools drifted from tools: "
            f"{allowed_tools_arg!r} != {tools_arg!r}"
        )
    if "Bash" not in {tool.strip() for tool in allowed_tools_arg.split(",") if tool.strip()}:
        raise ProfileError("claude effective_write argv did not pre-allow Bash")

    claude_read_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-claude-read",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        agent_instruction_packet=instruction_packet,
    )
    if adapter.agent_request_effective_write(claude_read_request):
        raise ProfileError("claude read request became effective_write")
    knobs_read = adapter_local_cli._claude_cli_invocation(claude_read_request)
    if knobs_read["permission_mode"] != "plan":
        raise ProfileError("claude read request did not stay in plan mode")
    if knobs_read["tools"] != "":
        raise ProfileError("claude read request exposed tools")
    if knobs_read["system_prompt"] != adapter._CLAUDE_NONINTERACTIVE_SYSTEM_PROMPT:
        raise ProfileError("claude read request did not use the read-only system prompt")

    return 15


def _agent_read_tier_probe(repo: Path, adapter: Any) -> int:
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    adapter_grant_policy = importlib.import_module("brick_protocol.support.connection.adapter_grant_policy")
    adapter_local_cli = importlib.import_module("brick_protocol.support.connection.adapter_local_cli")
    resources = importlib.import_module("brick_protocol.support.connection.agent_resources")
    qa_packet = _agent_instruction_packet_for_role(repo, "qa")
    pm_packet = _agent_instruction_packet_for_role(repo, "pm-lead")
    cto_packet = _agent_instruction_packet_for_role(repo, "cto-lead")
    dev_packet = _agent_instruction_packet_for_role(repo, "dev")
    inspector_packet = _agent_instruction_packet_for_role(repo, "inspector")
    expected_known_policies = {
        adapter_constants.LEADER_COORDINATION_TOOL_POLICY_REF,
        adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,
        adapter_constants.READ_WRITE_TOOL_POLICY_REF,
        adapter_constants.REVIEWER_READONLY_TOOL_POLICY_REF,
        adapter_constants.WEB_CAPABLE_TOOL_POLICY_REF,
    }
    if set(adapter_constants.KNOWN_TOOL_POLICY_REFS) != expected_known_policies:
        raise ProfileError(
            "read-tier known tool-policy vocabulary drifted; observed "
            f"{sorted(adapter_constants.KNOWN_TOOL_POLICY_REFS)!r}"
        )
    tool_policy_dir = repo / "agent" / "tool_policies"
    discovered_policy_refs: set[str] = set()
    for path in sorted(tool_policy_dir.glob("*.yaml")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ProfileError(f"{path.relative_to(repo).as_posix()} must load as a JSON object")
        ref = data.get("tool_policy_ref")
        if not isinstance(ref, str):
            raise ProfileError(f"{path.relative_to(repo).as_posix()} missing tool_policy_ref")
        discovered_policy_refs.add(ref)
        resources.resolve_native_grant(
            [
                {
                    "ref": ref,
                    "kind": "tool_policy",
                    "path": path.relative_to(repo).as_posix(),
                    "data": data,
                }
            ],
            tool_policy_refs=[ref],
            write_need=(ref in adapter_constants.WRITE_TIER_TOOL_POLICY_REFS),
        )
    if not expected_known_policies.issubset(discovered_policy_refs):
        raise ProfileError(
            "native_grant discovery missed known tool-policy refs: "
            f"{sorted(expected_known_policies - discovered_policy_refs)!r}"
        )
    web_roles: list[str] = []
    for object_ref in resources.list_agent_object_refs(repo):
        role = object_ref.removeprefix("agent-object:")
        packet = _agent_instruction_packet_for_role(repo, role)
        tool_policy_refs = {
            resource["ref"]
            for resource in packet.get("tool_policy_resources", [])
            if isinstance(resource, Mapping) and isinstance(resource.get("ref"), str)
        }
        if adapter_constants.WEB_CAPABLE_TOOL_POLICY_REF in tool_policy_refs:
            web_roles.append(role)
        for resource in packet.get("tool_policy_resources", []):
            data = resource.get("data") if isinstance(resource, Mapping) else None
            grant = data.get("native_grant") if isinstance(data, Mapping) else None
            if not isinstance(grant, Mapping):
                raise ProfileError(f"{role} tool policy resource missing native_grant")
            if any(key in grant for key in ("model", "credential_body", "provider_session_id")):
                raise ProfileError(f"{role} native_grant leaked forbidden axis/provider key")
    if sorted(web_roles) != ["design-lead", "pm-lead"]:
        raise ProfileError(
            "tool-policy:web-capable must be attached only to pm-lead/design-lead, "
            f"observed {sorted(web_roles)!r}"
        )
    for role in ("qa", "inspector", "qa-lead"):
        packet = _agent_instruction_packet_for_role(repo, role)
        semantic_capability = packet.get("semantic_capability")
        if not isinstance(semantic_capability, Mapping):
            raise ProfileError(f"{role} instruction packet missing semantic_capability")
        declared_classes = semantic_capability.get("declared_policy_semantic_capability_classes")
        max_classes = semantic_capability.get("max_semantic_capability_classes")
        if "source_write" in (declared_classes or ()) or "artifact_write" in (
            declared_classes or ()
        ):
            raise ProfileError(
                f"{role} reviewer-intent policy structurally admits source/artifact write: "
                f"{declared_classes!r}"
            )
        if "source_write" in (max_classes or ()) or "artifact_write" in (max_classes or ()):
            raise ProfileError(
                f"{role} reviewer-intent effective semantic capability leaked source/artifact write: "
                f"{max_classes!r}"
            )
    dev_resolution = resources.resolve_native_grant(
        dev_packet["tool_policy_resources"],
        tool_policy_refs=[
            resource["ref"]
            for resource in dev_packet["tool_policy_resources"]
            if isinstance(resource, Mapping)
        ],
        write_need=False,
    )
    if dev_resolution.get("capabilities") != ["read"]:
        raise ProfileError(
            "read-write-scoped without Brick write NEED must resolve native capabilities to read only"
        )
    dev_write_resolution = resources.resolve_native_grant(
        dev_packet["tool_policy_resources"],
        tool_policy_refs=[
            resource["ref"]
            for resource in dev_packet["tool_policy_resources"]
            if isinstance(resource, Mapping)
        ],
        write_need=True,
    )
    if dev_write_resolution.get("capabilities") != ["read", "write"]:
        raise ProfileError(
            "read-write-scoped with Brick write NEED must resolve native capabilities to read/write"
        )

    reviewer_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-reviewer-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.REVIEWER_READONLY_TOOL_POLICY_REF,),
        required_return_shape="observed_evidence, evidence_used, not_proven",
        agent_instruction_packet=qa_packet,
    )
    if not adapter.agent_request_read_tier(reviewer_request):
        raise ProfileError("reviewer-readonly non-write codex request did not enter read tier")
    reviewer_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            reviewer_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
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
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.REVIEWER_READONLY_TOOL_POLICY_REF, "tool-policy:unknown"),
        required_return_shape="observed_evidence, evidence_used, not_proven",
        agent_instruction_packet=qa_packet,
    )
    if adapter.agent_request_read_tier(unknown_policy_request):
        raise ProfileError("reviewer-readonly plus unknown tool policy entered read tier")
    unknown_policy_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            unknown_policy_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    if "Do not use tools or hooks." not in unknown_policy_prompt.get("rules", []):
        raise ProfileError("unknown tool policy request did not fail closed to none tier")
    if expected_read_rule in unknown_policy_prompt.get("rules", []):
        raise ProfileError("unknown tool policy request still rendered read-tier inspection rule")

    leader_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-leader-probe",
        agent_object_ref="agent-object:cto-lead",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-design",
        next_brick_instance_ref="brick-work",
        tool_policy_refs=(
            adapter_constants.LEADER_COORDINATION_TOOL_POLICY_REF,
            adapter_constants.READ_WRITE_TOOL_POLICY_REF,
        ),
        required_return_shape="observed_evidence, evidence_refs, not_proven",
        agent_instruction_packet=cto_packet,
    )
    if not adapter.agent_request_read_tier(leader_request):
        raise ProfileError("leader-coordination non-write claude request did not enter read tier")
    leader_knobs = adapter_local_cli._claude_cli_invocation(leader_request)
    if leader_knobs["permission_mode"] != "acceptEdits":
        raise ProfileError("read-tier claude request must use acceptEdits with the declared read-only tool list")
    leader_tools = [tool.strip() for tool in leader_knobs["tools"].split(",") if tool.strip()]
    if leader_tools != ["Read", "Grep", "Glob"]:
        raise ProfileError(f"read-tier claude tools must be Read/Grep/Glob only, got {leader_tools}")
    if "Edit" in leader_tools or "Write" in leader_tools or "Bash" in leader_tools:
        raise ProfileError("read-tier claude request leaked Edit/Write/Bash tools")
    if leader_knobs["system_prompt"] != adapter._CLAUDE_READ_ONLY_SYSTEM_PROMPT:
        raise ProfileError("read-tier claude request did not use the read-only system prompt")

    # CLEAN-READTIER-0617 / CLAUDE-READ-FULL-ADAPTER-0624: read/write tier is no
    # longer a support-side authority over the tool-policy label. A read-only Brick
    # (no observed write) paired with a tool-capable Agent browses read-only through
    # declared read tools. Claude uses the normal acceptEdits invocation plane with
    # only Read/Grep/Glob; provider plan mode is not the read boundary. (Write still
    # requires write_scope, which routes through agent_request_effective_write.)
    dev_nonwrite_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-dev-readonly-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-readonly-worker",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=dev_packet,
    )
    if adapter.agent_request_effective_write(dev_nonwrite_request):
        raise ProfileError("read-write-scoped without write_scope must not be effective_write")
    if not adapter.agent_request_read_tier(dev_nonwrite_request):
        raise ProfileError(
            "read-only Brick + tool-capable codex Agent (read-write-scoped, no write_scope) "
            "did not enter the read tier under the uniform CLEAN-READTIER rule"
        )
    dev_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            dev_nonwrite_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    dev_rules = list(dev_prompt.get("rules", []))
    if "Do not use tools or hooks." in dev_rules:
        raise ProfileError("read-tier read-write-scoped codex prompt still rendered the none-tier no-tools rule")
    if expected_read_rule not in dev_rules:
        raise ProfileError("read-tier read-write-scoped codex prompt did not expose repository inspection rule")
    # Read tier must not leak write-tier permission: no edit-allowed phrasing.
    for phrase in ("You may edit files only inside", "write_scope.allowed_paths"):
        if any(phrase in rule for rule in dev_rules):
            raise ProfileError(
                f"read-tier read-write-scoped codex prompt leaked write-tier permission phrase {phrase!r}"
            )

    reviewer_no_mutation_write_scope = {
        "allowed_paths": ["."],
        "forbidden_paths": [".git/**"],
    }
    reviewer_no_mutation_request = adapter.AgentAdapterRequest(
        building_id="agent-reviewer-no-mutation-write-scope-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-code-attack-qa",
        next_brick_instance_ref="brick-closure",
        hook_refs=("hook:reviewer-no-mutation",),
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        required_return_shape="observed_evidence, evidence_used, not_proven",
        agent_instruction_packet=qa_packet,
        write_scope=reviewer_no_mutation_write_scope,
    )
    if not adapter.agent_request_effective_write(reviewer_no_mutation_request):
        raise ProfileError("reviewer-no-mutation probe stopped recording effective_write input")
    reviewer_no_mutation_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            reviewer_no_mutation_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    reviewer_no_mutation_rules = list(reviewer_no_mutation_prompt.get("rules", []))
    required_taxonomy_rules = (
        "hook:reviewer-no-mutation blocks source_write",
        "probe_write / verification_write",
        "disposable work-area",
        "full filesystem-enforced source/probe split is not proven",
    )
    for required in required_taxonomy_rules:
        if not any(required in rule for rule in reviewer_no_mutation_rules):
            raise ProfileError(
                "reviewer-no-mutation prompt did not carry capability-taxonomy rule "
                f"{required!r}"
            )
    if not any("Do not create, edit, delete, or rewrite source files as source truth" in rule for rule in reviewer_no_mutation_rules):
        raise ProfileError("reviewer-no-mutation prompt did not carry the source_write ban")
    if adapter_local_cli._codex_sandbox_for_request(reviewer_no_mutation_request) != "workspace-write":
        raise ProfileError(
            "reviewer-no-mutation codex projection did not preserve declared work-area write sandbox"
        )
    claude_reviewer_no_mutation_request = adapter.AgentAdapterRequest(
        building_id="agent-reviewer-no-mutation-claude-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-code-attack-qa",
        next_brick_instance_ref="brick-closure",
        hook_refs=("hook:reviewer-no-mutation",),
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=qa_packet,
        write_scope=reviewer_no_mutation_write_scope,
    )
    claude_reviewer_knobs = adapter_local_cli._claude_cli_invocation(claude_reviewer_no_mutation_request)
    claude_reviewer_tools = [
        tool.strip()
        for tool in claude_reviewer_knobs["tools"].split(",")
        if tool.strip()
    ]
    for tool_name in ("Read", "Grep", "Glob", "Edit", "Write", "Bash"):
        if tool_name not in claude_reviewer_tools:
            raise ProfileError(
                "reviewer-no-mutation claude projection did not preserve work-area "
                f"tool {tool_name!r}: {claude_reviewer_tools!r}"
            )
    if claude_reviewer_knobs["system_prompt"] != adapter._CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT:
        raise ProfileError(
            "reviewer-no-mutation claude projection did not use scoped-write system prompt"
        )
    gemini_reviewer_no_mutation_request = adapter.AgentAdapterRequest(
        building_id="agent-reviewer-no-mutation-gemini-probe",
        agent_object_ref="agent-object:inspector",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-axis-attack-qa",
        next_brick_instance_ref="brick-closure",
        hook_refs=("hook:reviewer-no-mutation",),
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=inspector_packet,
        write_scope=reviewer_no_mutation_write_scope,
    )
    gemini_reviewer_allow, gemini_reviewer_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(
        gemini_reviewer_no_mutation_request
    )
    for tool_name in ("write_file", "replace", "run_shell_command"):
        if tool_name not in gemini_reviewer_allow or tool_name in gemini_reviewer_deny:
            raise ProfileError(
                "reviewer-no-mutation gemini projection did not preserve work-area probe tool "
                f"{tool_name!r}"
            )
    if "read_file" not in gemini_reviewer_allow:
        raise ProfileError("reviewer-no-mutation gemini projection did not preserve read tools")

    fugu_nonwrite_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-fugu-readonly-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_FUGU_LOCAL,
        brick_instance_ref="brick-readonly-worker",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=dev_packet,
    )
    if adapter.agent_request_effective_write(fugu_nonwrite_request):
        raise ProfileError("fugu read-write-scoped without write_scope must not be effective_write")
    if not adapter.agent_request_read_tier(fugu_nonwrite_request):
        raise ProfileError(
            "read-only Brick + tool-capable fugu Agent (read-write-scoped, no write_scope) "
            "did not enter the read tier"
        )
    fugu_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            fugu_nonwrite_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_FUGU_LOCAL],
        )
    )
    fugu_rules = list(fugu_prompt.get("rules", []))
    if "Do not use tools or hooks." in fugu_rules:
        raise ProfileError("read-tier read-write-scoped fugu prompt still rendered the none-tier no-tools rule")
    if expected_read_rule not in fugu_rules:
        raise ProfileError("read-tier read-write-scoped fugu prompt did not expose repository inspection rule")
    for phrase in ("You may edit files only inside", "write_scope.allowed_paths"):
        if any(phrase in rule for rule in fugu_rules):
            raise ProfileError(
                f"read-tier read-write-scoped fugu prompt leaked write-tier permission phrase {phrase!r}"
            )

    gemini_inspect_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-gemini-inspect-probe",
        agent_object_ref="agent-object:inspector",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-inspect",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=inspector_packet,
    )
    if not adapter.agent_request_read_tier(gemini_inspect_request):
        raise ProfileError("gemini-local read-write-scoped request did not enter read tier")
    gemini_inspect_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_inspect_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_inspect_rules = list(gemini_inspect_prompt.get("rules", []))
    if "Do not use tools or hooks." in gemini_inspect_rules:
        raise ProfileError("gemini-local read-write-scoped prompt still rendered no-tools rule")
    if expected_read_rule not in gemini_inspect_rules:
        raise ProfileError("gemini-local read-write-scoped prompt did not expose repository inspection rule")
    if not any(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF in rule for rule in gemini_inspect_rules):
        raise ProfileError("gemini-local probe-write-scoped prompt omitted its admitted policy ref")
    if not any("Gemini local native grant may use only read_file" in rule for rule in gemini_inspect_rules):
        raise ProfileError("gemini-local read-write-scoped prompt did not pin read-only tool allow-list")

    gemini_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-gemini-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.REVIEWER_READONLY_TOOL_POLICY_REF,),
        agent_instruction_packet=qa_packet,
    )
    if adapter_constants.ADAPTER_GEMINI_LOCAL not in set(qa_packet.get("adapter_refs", ())):
        raise ProfileError("qa instruction packet did not admit adapter:gemini-local")
    if adapter.agent_request_effective_write(gemini_request):
        raise ProfileError("gemini-local reviewer-readonly request opened effective write")
    if not adapter.agent_request_read_tier(gemini_request):
        raise ProfileError("gemini-local reviewer-readonly request did not enter read tier")
    gemini_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_rules = list(gemini_prompt.get("rules", []))
    if "Do not use tools or hooks." in gemini_rules:
        raise ProfileError("read-tier gemini-local prompt still rendered the none-tier no-tools rule")
    if expected_read_rule not in gemini_rules:
        raise ProfileError("read-tier gemini-local prompt did not expose repository inspection rule")
    if any("adapter:gemini-local remains in the none tier" in rule for rule in gemini_rules):
        raise ProfileError("read-tier gemini-local prompt still documented the retired none-tier limit")
    if not any("Gemini local native grant may use only read_file" in rule for rule in gemini_rules):
        raise ProfileError("read-tier gemini-local prompt did not pin its read-only tool allow-list")

    pm_web_request = adapter.AgentAdapterRequest(
        building_id="agent-web-tier-pm-probe",
        agent_object_ref="agent-object:pm-lead",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-live-context",
        next_brick_instance_ref="brick-design",
        tool_policy_refs=(
            adapter_constants.LEADER_COORDINATION_TOOL_POLICY_REF,
            adapter_constants.READ_WRITE_TOOL_POLICY_REF,
            adapter_constants.WEB_CAPABLE_TOOL_POLICY_REF,
        ),
        agent_instruction_packet=pm_packet,
    )
    pm_claude_knobs = adapter_local_cli._claude_cli_invocation(pm_web_request)
    pm_claude_tools = [tool.strip() for tool in pm_claude_knobs["tools"].split(",") if tool.strip()]
    if "WebFetch" not in pm_claude_tools:
        raise ProfileError("claude-local web-capable PM request did not project WebFetch")
    if "WebSearch" not in pm_claude_tools:
        raise ProfileError("claude-local web-capable PM request did not project WebSearch")
    pm_codex_request = adapter.AgentAdapterRequest(
        building_id="agent-web-tier-codex-probe",
        agent_object_ref="agent-object:pm-lead",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-live-context",
        next_brick_instance_ref="brick-design",
        tool_policy_refs=pm_web_request.tool_policy_refs,
        agent_instruction_packet=pm_packet,
    )
    pm_codex_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            pm_codex_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    if not any("Web NOT available on this adapter" in rule for rule in pm_codex_prompt.get("rules", [])):
        raise ProfileError("codex-local web-capable request did not document web as unavailable")
    if pm_codex_prompt.get("native_grant", {}).get("web_requested") is not True:
        raise ProfileError("codex-local web-capable prompt did not preserve web_requested evidence")

    pm_gemini_request = adapter.AgentAdapterRequest(
        building_id="agent-web-tier-gemini-probe",
        agent_object_ref="agent-object:pm-lead",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-live-context",
        next_brick_instance_ref="brick-design",
        tool_policy_refs=pm_web_request.tool_policy_refs,
        agent_instruction_packet=pm_packet,
    )
    gemini_allow, gemini_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(pm_gemini_request)
    if "web_fetch" not in gemini_allow or "google_web_search" not in gemini_allow:
        raise ProfileError("gemini-local web-capable request did not allow web tools")
    if "run_shell_command" not in gemini_deny or "write_file" not in gemini_deny:
        raise ProfileError("gemini-local web-capable request did not deny residual write/shell tools")
    web_tool_payload = json.dumps(
        {
            "response": "web tools accepted",
            "stats": {"tools": {"totalCalls": 1, "byName": {"web_fetch": 1}}},
        }
    )
    # Smith 0623 LOCK (move+record only): a non-granted tool no longer refuses the
    # payload. The read-only fallback returns the real answer AND records web_fetch
    # as an observed non-granted tool.
    fallback_response, fallback_tools = adapter_local_cli._extract_gemini_response(web_tool_payload)
    if fallback_response != "web tools accepted":
        raise ProfileError("gemini-local read-only fallback dropped the real answer for web_fetch")
    if "web_fetch" not in fallback_tools:
        raise ProfileError(
            "gemini-local non-web extraction did not RECORD ungranted web_fetch as an "
            "observed non-granted tool"
        )
    granted_response, granted_tools = adapter_local_cli._extract_gemini_response(
        web_tool_payload,
        allowed_tool_names=adapter_grant_policy._gemini_allowed_tool_names_for_request(pm_gemini_request),
    )
    if granted_response != "web tools accepted":
        raise ProfileError("gemini-local web-capable extraction did not accept request-threaded web_fetch")
    if granted_tools:
        raise ProfileError(
            "gemini-local web-granted request wrongly recorded an observed non-granted "
            f"tool: {granted_tools!r}"
        )

    gemini_cli_capture: dict[str, Any] = {}

    def _gemini_readonly_runner(
        args: Sequence[str],
        cwd: Path,
        timeout_seconds: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del timeout_seconds
        call = tuple(str(arg) for arg in args)
        gemini_cli_capture["args"] = call
        gemini_cli_capture["cwd"] = cwd
        gemini_cli_capture["env_home"] = (env or {}).get("HOME")
        gemini_cli_capture["env_has_api_key"] = bool(
            (env or {}).get("GEMINI_API_KEY") or (env or {}).get("GOOGLE_API_KEY")
        )
        gemini_cli_capture["env_trust_workspace"] = (env or {}).get(
            "GEMINI_CLI_TRUST_WORKSPACE"
        )
        if "--admin-policy" in call:
            policy_path = Path(call[call.index("--admin-policy") + 1])
            gemini_cli_capture["policy_text"] = policy_path.read_text(encoding="utf-8")
        if env and env.get("HOME"):
            settings_path = Path(env["HOME"]) / ".gemini" / "settings.json"
            gemini_cli_capture["settings"] = json.loads(settings_path.read_text(encoding="utf-8"))
        return adapter.LocalCliCompleted(call, 0, '{"response": "mocked"}', "")

    saved_env = {name: os.environ.get(name) for name in adapter._GEMINI_API_KEY_ENV_VARS}
    for name in adapter._GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "probe-key"
    try:
        adapter_local_cli._invoke_local_cli(
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
            gemini_inspect_request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=_gemini_readonly_runner,
        )
    finally:
        for name in adapter._GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]
    gemini_args = tuple(gemini_cli_capture.get("args", ()))
    if "--approval-mode" in gemini_args:
        raise ProfileError(f"gemini-local CLI projection retained OAuth-era approval mode: {gemini_args!r}")
    if "--model" not in gemini_args or gemini_args[gemini_args.index("--model") + 1] != "gemini-3.5-flash":
        raise ProfileError(f"gemini-local read tier did not pin gemini-3.5-flash: {gemini_args!r}")
    if "--yolo" not in gemini_args:
        raise ProfileError(f"gemini-local API-key path did not enable noninteractive --yolo: {gemini_args!r}")
    if "auto_edit" in gemini_args or "yolo" in gemini_args:
        raise ProfileError(f"gemini-local CLI projection used legacy approval-mode value: {gemini_args!r}")
    if "--admin-policy" not in gemini_args:
        raise ProfileError("gemini-local CLI projection dropped read-only admin policy")
    if gemini_cli_capture.get("cwd") != repo:
        raise ProfileError("gemini-local read tier did not run from the dispatch worktree cwd")
    if not gemini_cli_capture.get("env_home"):
        raise ProfileError("gemini-local read tier did not pass a temporary HOME")
    if not gemini_cli_capture.get("env_has_api_key"):
        raise ProfileError("gemini-local read tier did not pass API-key env into subprocess")
    if gemini_cli_capture.get("env_trust_workspace") != "true":
        raise ProfileError("gemini-local read tier did not set GEMINI_CLI_TRUST_WORKSPACE=true")
    if gemini_cli_capture.get("settings") != {
        "security": {"auth": {"selectedType": "gemini-api-key"}}
    }:
        raise ProfileError("gemini-local read tier did not force temp HOME gemini-api-key auth")
    policy_text = str(gemini_cli_capture.get("policy_text", ""))
    for required_allow in (
        "read_file",
        "glob",
        "grep_search",
        "list_directory",
        "search_file_content",
        "read_many_files",
        'decision = "allow"',
        "priority = 998",
    ):
        if required_allow not in policy_text:
            raise ProfileError(
                "gemini-local read-only admin policy stopped allowing read tooling token "
                f"{required_allow!r}"
            )
    for required_deny in (
        "run_shell_command",
        "write_file",
        "replace",
        'decision = "deny"',
        "priority = 999",
    ):
        if required_deny not in policy_text:
            raise ProfileError(
                "gemini-local read-only admin policy stopped denying write/command "
                f"tooling token {required_deny!r}"
            )
    if "priority = 1000" in policy_text:
        raise ProfileError("gemini-local read-only admin policy exceeded priority ceiling")

    read_tool_payload = json.dumps(
        {
            "response": "read tools accepted",
            "stats": {
                "tools": {
                    "totalCalls": 6,
                    "byName": {
                        "read_file": 1,
                        "glob": 1,
                        # CLEAN-READTIER-0617: gemini CLI 0.46 SearchText is named
                        # grep_search (search_file_content is the legacy alias) and
                        # list_directory (ReadFolder) is a read-only browse tool;
                        # both must pass the non-read rejection set or read browse
                        # gets falsely rejected.
                        "grep_search": 1,
                        "list_directory": 1,
                        "search_file_content": 1,
                        "read_many_files": 1,
                    },
                }
            },
        }
    )
    read_response, read_tools = adapter_local_cli._extract_gemini_response(read_tool_payload)
    if read_response != "read tools accepted":
        raise ProfileError("gemini-local read tool byName payload was not accepted")
    if read_tools:
        raise ProfileError(
            f"gemini-local read-only tools wrongly recorded as non-granted: {read_tools!r}"
        )
    # Smith 0623 LOCK (move+record only): a non-read tool no longer refuses the
    # payload -- it is RECORDED as an observed non-granted tool while the answer
    # still returns.
    for forbidden_tool in ("write_file", "run_shell_command", "replace"):
        forbidden_payload = json.dumps(
            {
                "response": "non-read tool should reject",
                "stats": {"tools": {"totalCalls": 1, "byName": {forbidden_tool: 1}}},
            }
        )
        forbidden_response, forbidden_tools = adapter_local_cli._extract_gemini_response(
            forbidden_payload
        )
        if forbidden_response != "non-read tool should reject":
            raise ProfileError(
                f"gemini-local dropped the answer for non-read tool {forbidden_tool!r}"
            )
        if forbidden_tool not in forbidden_tools:
            raise ProfileError(
                f"gemini-local non-read tool record omitted {forbidden_tool!r}: "
                f"{forbidden_tools!r}"
            )

    # GEMINI-CONTROLPLANE-EXEMPT-0622: gemini's own completion/orchestration control
    # plane (complete_task, invoke_agent) has no repo/external side effect and must
    # NEVER produce a false-positive refusal/HOLD, even under the read-only fallback
    # (allowed_tool_names is None). This is the false-positive that the fix removes.
    benign_payload = json.dumps(
        {
            "response": "benign control plane accepted",
            "stats": {
                "tools": {
                    "totalCalls": 3,
                    "byName": {"complete_task": 1, "invoke_agent": 1, "read_file": 1},
                }
            },
        }
    )
    benign_response, benign_tools = adapter_local_cli._extract_gemini_response(benign_payload)
    if benign_response != "benign control plane accepted":
        raise ProfileError(
            "gemini-local benign control-plane tools (complete_task/invoke_agent) "
            "dropped the real answer"
        )
    if benign_tools:
        raise ProfileError(
            "gemini-local benign control-plane tools (complete_task/invoke_agent) "
            f"were falsely recorded as observed non-granted tools: {benign_tools!r}"
        )
    # MUTATION-RED GUARD: the benign exemption must stay BOUNDED -- a real ungranted
    # side-effecting tool bundled WITH benign control tools must STILL trip the refusal,
    # so the exemption cannot silently rot into "accept everything".
    benign_plus_write_payload = json.dumps(
        {
            "response": "benign bundled with real write must still reject",
            "stats": {
                "tools": {
                    "totalCalls": 2,
                    "byName": {"complete_task": 1, "write_file": 1},
                }
            },
        }
    )
    # Smith 0623 LOCK (move+record only): the answer always returns; the guard is
    # now that the RECORDED observed-tool set stays BOUNDED -- write_file is recorded,
    # the benign complete_task is NOT, so the exemption cannot rot into "record
    # nothing" (or "record everything").
    bundled_response, bundled_tools = adapter_local_cli._extract_gemini_response(
        benign_plus_write_payload
    )
    if bundled_response != "benign bundled with real write must still reject":
        raise ProfileError(
            "gemini-local dropped the answer for write_file bundled with benign tools"
        )
    if "write_file" not in bundled_tools:
        raise ProfileError(
            "gemini-local benign exemption widened into NOT recording an ungranted "
            "write_file (mutation-RED guard breached)"
        )
    if "complete_task" in bundled_tools:
        raise ProfileError(
            "gemini-local wrongly recorded the benign complete_task tool"
        )
    # PART 1 consistency: a web tool is a violation under the read-only fallback BUT is
    # accepted once the request's full granted set (web included) is threaded -- the
    # post-hoc must agree with the launch-time admin-policy grant.
    web_search_payload = json.dumps(
        {
            "response": "web tools accepted",
            "stats": {"tools": {"totalCalls": 1, "byName": {"google_web_search": 1}}},
        }
    )
    # Smith 0623 LOCK (move+record only): under the read-only fallback the answer
    # returns and ungranted google_web_search is RECORDED, not refused.
    web_search_response, web_search_tools = adapter_local_cli._extract_gemini_response(
        web_search_payload
    )
    if web_search_response != "web tools accepted":
        raise ProfileError(
            "gemini-local read-only fallback dropped the answer for google_web_search"
        )
    if "google_web_search" not in web_search_tools:
        raise ProfileError(
            "gemini-local ungranted google_web_search record did not name the tool"
        )
    granted_search_response, granted_search_tools = adapter_local_cli._extract_gemini_response(
        web_search_payload,
        allowed_tool_names=adapter_grant_policy._gemini_allowed_tool_names_for_request(
            pm_gemini_request
        ),
    )
    if granted_search_response != "web tools accepted":
        raise ProfileError(
            "gemini-local web-granted request rejected google_web_search the launch "
            "admin-policy allows (post-hoc inconsistent with grant)"
        )
    if granted_search_tools:
        raise ProfileError(
            "gemini-local web-granted request wrongly recorded google_web_search as "
            f"observed non-granted: {granted_search_tools!r}"
        )

    gemini_none_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-gemini-none-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(),
        agent_instruction_packet=qa_packet,
    )
    if adapter.agent_request_read_tier(gemini_none_request):
        raise ProfileError("gemini-local none-tier request entered read tier without read-only policy")
    gemini_none_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_none_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    if "Do not use tools or hooks." not in gemini_none_prompt.get("rules", []):
        raise ProfileError("gemini-local none-tier request stopped rendering no-tools prompt")

    gemini_client_error_path = Path(tempfile.gettempdir()) / "gemini-client-error-probe.json"
    unrelated_file_body = "UNRELATED_FILE_BODY_SHOULD_NOT_ENTER_ADAPTER_ERROR_EVIDENCE"
    gemini_client_error_path.write_text(
        json.dumps(
            {
                "error": {
                    "message": unrelated_file_body,
                    "credential": "probe-credential-body-must-not-leak",
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def _gemini_nonzero_runner(
        args: Sequence[str],
        cwd: Path,
        timeout_seconds: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del cwd, timeout_seconds, env
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return adapter.LocalCliCompleted(call, 0, "0.46.0", "")
        return adapter.LocalCliCompleted(
            call,
            1,
            json.dumps({"error": {"code": 404, "message": "model not found for probe"}}),
            f"Gemini CLI failed; details: {gemini_client_error_path}",
        )

    saved_env = {name: os.environ.get(name) for name in adapter._GEMINI_API_KEY_ENV_VARS}
    for name in adapter._GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "probe-key"
    try:
        try:
            adapter_local_cli._invoke_local_cli_adapter(
                gemini_inspect_request,
                cwd=repo,
                timeout_seconds=5,
                command_runner=_gemini_nonzero_runner,
            )
        except ValueError as exc:
            nonzero_message = str(exc)
        else:
            raise ProfileError("gemini-local non-zero adapter probe did not raise")
    finally:
        gemini_client_error_path.unlink(missing_ok=True)
        for name in adapter._GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]
    for expected_fragment, label in (
        ("local CLI adapter command returned non-zero", "non-zero marker"),
        ("adapter_ref=adapter:gemini-local", "adapter ref"),
        ("return_code=1", "return code"),
        ("stderr_excerpt=Gemini CLI failed", "stderr excerpt"),
        ("stdout_error_excerpt=", "stdout error excerpt"),
        ("model not found for probe", "stdout error detail"),
        (f"stderr_error_path={gemini_client_error_path}", "stderr error path"),
    ):
        if expected_fragment not in nonzero_message:
            raise ProfileError(
                f"gemini-local non-zero adapter error omitted {label}: {nonzero_message!r}"
            )
    for forbidden_fragment, label in (
        ("gemini_client_error_excerpt=", "Gemini client error file excerpt"),
        (unrelated_file_body, "unrelated readable file body"),
        ("probe-credential-body-must-not-leak", "credential-looking diagnostic body"),
    ):
        if forbidden_fragment in nonzero_message:
            raise ProfileError(
                f"gemini-local non-zero adapter error included {label}: {nonzero_message!r}"
            )

    return 39


def _artifact_grounding_probe(repo: Path) -> int:
    from brick_protocol.support.connection.adapter_constants import (
        ADAPTER_LOCAL,
    )
    from brick_protocol.support.connection.agent_adapter import (
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
            "checker_or_verifier_plan, candidate_file_changes, evidence_refs, not_proven, "
            "reading_scope_map",
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
                "reading_scope_map": ["support/operator/walker_kernel.py"],
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
                "reading_scope_map": ["support/operator/walker_kernel.py"],
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
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    adapter_grant_policy = importlib.import_module("brick_protocol.support.connection.adapter_grant_policy")
    adapter_validation = importlib.import_module("brick_protocol.support.connection.adapter_validation")
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
    extracted = adapter_grant_policy._extract_required_return_fields(output_text, required_shape)
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
        adapter_grant_policy._build_prompt(
            request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    if prompt.get("return_field_waivers") != ["no_changes_reason"]:
        raise ProfileError("adapter prompt did not expose no_changes_reason waiver")
    if prompt.get("agent_instruction_packet", {}).get("kind") != "agent-instruction-packet":
        raise ProfileError("adapter prompt did not carry Agent instruction packet")
    transition_required_shape = (
        "observed_evidence, transition_concern_evidence, not_proven"
    )
    transition_request = _agent_adapter_request_instruction_packet_probe(
        adapter,
        instruction_packet,
        transition_required_shape,
    )
    transition_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            transition_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    transition_prompt_text = json.dumps(transition_prompt, sort_keys=True)
    if (
        "never return an empty object {}" not in transition_prompt_text
        or
        "If transition_concern_evidence.concern_kind is verification_gap"
        not in transition_prompt_text
        or "never name a reroute-capable Brick node" not in transition_prompt_text
    ):
        raise ProfileError(
            "adapter prompt did not carry the no-concern/verification_gap transition concern rules"
        )
    no_concern_comparison = comparison.BrickComparisonFact.from_returned_value(
        work_reference="work:agent-adapter-no-concern-probe",
        required_fields=("observed_evidence", "transition_concern_evidence", "not_proven"),
        returned_value={
            "observed_evidence": ["probe observed no concern absence"],
            "not_proven": ["semantic correctness"],
        },
        comparison_rule="Probe absent transition_concern_evidence no-concern waiver only.",
        required_return_shape_evidence=transition_required_shape,
    )
    if (
        "transition_concern_evidence absent means no concern"
        not in no_concern_comparison.waived_return_fields()
    ):
        raise ProfileError(
            "Brick comparison did not waive absent transition_concern_evidence as no concern"
        )
    effective_write_inspected = _agent_effective_write_probe(repo, adapter, instruction_packet)
    read_tier_inspected = _agent_read_tier_probe(repo, adapter)
    artifact_grounding_inspected = _artifact_grounding_probe(repo)

    # REHOME (checker consolidation): assert the FULL return-field vocabulary the
    # retiring provider_json_return_smoke profile single-sourced (several tokens
    # were pinned only there). The Agent return label/JSON field constants live in
    # support/connection/agent_adapter.py; the top-level verdict keys and always
    # recursive secret keys live in agent/return_fact.py and are re-exported into
    # the adapter. An absent guard fires nothing, so verify the constants directly
    # instead of leaving the vocabulary text-pinned in one retiring profile.
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
    _EXPECTED_TOP_LEVEL_VERDICT_KEYS = ("movement_choice", "route_target", "target_ref")
    _EXPECTED_ALWAYS_SECRET_KEYS = ("credential", "secret", "session", "setup_token")
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
    missing_top_level_keys = sorted(
        set(_EXPECTED_TOP_LEVEL_VERDICT_KEYS) - set(return_fact.TOP_LEVEL_VERDICT_KEYS)
    )
    if missing_top_level_keys:
        raise ProfileError(
            "return_fact TOP_LEVEL_VERDICT_KEYS missing forbidden return key(s): "
            + ", ".join(missing_top_level_keys)
        )
    missing_secret_keys = sorted(
        set(_EXPECTED_ALWAYS_SECRET_KEYS) - set(return_fact.ALWAYS_SECRET_KEYS)
    )
    if missing_secret_keys:
        raise ProfileError(
            "return_fact ALWAYS_SECRET_KEYS missing recursive secret key(s): "
            + ", ".join(missing_secret_keys)
        )
    if set(adapter._TOP_LEVEL_VERDICT_KEYS) != set(return_fact.TOP_LEVEL_VERDICT_KEYS):
        raise ProfileError(
            "agent adapter _TOP_LEVEL_VERDICT_KEYS drifted from "
            "return_fact TOP_LEVEL_VERDICT_KEYS"
        )
    if set(adapter._ALWAYS_SECRET_KEYS) != set(return_fact.ALWAYS_SECRET_KEYS):
        raise ProfileError(
            "agent adapter _ALWAYS_SECRET_KEYS drifted from "
            "return_fact ALWAYS_SECRET_KEYS"
        )
    try:
        adapter_validation._validate_returned_payload(
            "returned",
            {"observed_evidence": [{"checker_profile_run_results": {"pass": 5, "fail": 0}}]},
        )
    except ValueError as exc:
        raise ProfileError(
            "agent adapter rejected nested natural evidence keys pass/fail"
        ) from exc
    nested_output_text = (
        "provider preface\n"
        "```json\n"
        + json.dumps(
            {
                "observed_evidence": {
                    "profile": {"checker_profile_run_results": {"pass": 5, "fail": 0}},
                    "nested_list": ["alpha", {"nested": ["beta", {"gamma": "delta"}]}],
                },
                "not_proven": {
                    "runtime": {"provider": "not exercised"},
                },
            },
            sort_keys=True,
        )
        + "\n```"
    )
    nested_extracted = adapter_grant_policy._extract_required_return_fields(
        nested_output_text,
        "observed_evidence, not_proven",
    )
    if nested_extracted.get("observed_evidence") != [
        '["alpha",{"nested":["beta",{"gamma":"delta"}]}]',
        '{"checker_profile_run_results":{"fail":0,"pass":5}}',
    ]:
        raise ProfileError(
            "agent adapter did not preserve nested mapping/list observed_evidence "
            f"as deterministic text, observed {nested_extracted.get('observed_evidence')!r}"
        )
    if nested_extracted.get("not_proven") != ['{"provider":"not exercised"}']:
        raise ProfileError(
            "agent adapter did not preserve nested mapping/list not_proven "
            f"as deterministic text, observed {nested_extracted.get('not_proven')!r}"
        )
    # REDO (Smith 0623 struct-surgery): a top-level verdict key is NO LONGER a HOLD.
    # The payload walker quarantines it -- it must NOT raise and must REPORT the raw
    # key name. connect_agent_brain STRIPS the key (return-shaping) and exposes the
    # raw key name on the adapter side-channel; support/recording records the
    # ignored_forbidden_return_key fact (the adapter records nothing).
    try:
        ignored = adapter_validation._validate_returned_payload("returned", {"success": True})
    except ValueError as exc:
        raise ProfileError(
            "agent adapter halted on a top-level verdict key instead of "
            "quarantining it (move+record only)"
        ) from exc
    if "success" not in ignored:
        raise ProfileError(
            "agent adapter did not quarantine the top-level verdict key 'success' "
            f"as a recorded fact, observed {ignored!r}"
        )
    # KEEP: nested raw secret text STILL hard-raises (credential egress is a real
    # stop the worktree does not soften).
    try:
        adapter_validation._validate_returned_payload(
            "returned",
            {"e": [{"x": "Bearer ghp_fakesecret123"}]},
        )
    except ValueError:
        pass
    else:
        raise ProfileError("agent adapter admitted nested raw secret text")

    return KernelResult(
        check_id="agent_adapter_return_shape",
        inspected=10
        + effective_write_inspected
        + read_tier_inspected
        + artifact_grounding_inspected,
        output=(
            "agent adapter return shape passed: no_changes_reason waiver "
            "extraction, Brick comparison waiver, prompt projection, runtime "
            "Agent instruction packet rendering, and AgentAdapterRequest "
            "injection plus effective_write, read-tier rendering, tier-safety, "
            "artifact-grounding, and deterministic nested list-field "
            "normalization probes inspected."
        ),
    )


def _gemini_api_classify_error_kind(exc: Exception) -> str:
    """Read-only mirror of run.py._adapter_error_kind (we cannot edit run.py).

    The B2-hardened hold path classifies adapter exceptions by type/message. We
    replicate the mapping here ONLY to assert (in-process) that a gemini-api
    no-key error flows the SAME clean typed adapter-error path, never a crash.

    INTENTIONAL DIVERGENCE from run.py._adapter_error_kind (codex-review F4): the
    TimeoutExpired branch here maps to plain 'local_cli_timeout' and is NOT given
    the connect-stall split. Gemini is an HTTP API adapter with no codex
    dead-connection watchdog, so a stall-tagged TimeoutExpired can never reach it
    and 'local_cli_connect_stall' is correctly absent. Every OTHER branch mirrors
    run.py._adapter_error_kind.
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


from support.checkers.lib.design_ai_text_seams_check import run_design_ai_text_seams
from support.checkers.lib.codex_connect_stall_classification_check import (
    run_codex_connect_stall_classification,
)
from support.checkers.lib.gemini_local_only_adapter_check import run_gemini_local_only_adapter


# FINAL architecture leaf (0630): the install_script_lint + release_export_exclusion
# cluster moved VERBATIM into the flat checker-lib sibling
# install_release_export_lint_check.py (conservation ledger
# customer-ready-final-architecture-install-release-export-lint-ledger-0630.md).
# Re-exported here so check_profile imports stay byte-identical.
from support.checkers.lib.install_release_export_lint_check import (
    _INSTALL_SCRIPT_REL,
    _RELEASE_EXPORT_REL,
    _RELEASE_EXPORT_REQUIRED_EXCLUSIONS,
    _INSTALL_SCRIPT_SECRET_PATTERNS,
    run_install_script_lint,
    _release_export_exclusions,
    _release_export_exclusion_violations,
    _release_export_exclusion_fire_probe,
    run_release_export_exclusion,
)


# FINAL architecture leaf (0630): the product no-Smith-residue scan cluster
# moved VERBATIM into the flat checker-lib sibling no_smith_residue_check.py
# (conservation ledger customer-ready-final-architecture-no-smith-residue-ledger-0630.md).
# Re-exported here so check_profile imports and the in-file _SMITH_USER_HOME_LITERAL
# call site stay byte-identical.
from support.checkers.lib.no_smith_residue_check import (
    _SMITH_USER_HOME_LITERAL,
    _SMITH_GITHUB_ORG_LITERAL,
    _SMITH_GITHUB_REPO_LITERAL,
    _NO_SMITH_RESIDUE_SURFACES,
    _no_smith_residue_text_paths,
    _no_smith_residue_allowed_org_line,
    _collect_no_smith_residue_violations,
    _copy_no_smith_residue_surfaces,
    _no_smith_residue_fire_probe,
    run_product_no_smith_residue,
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


def _assert_reporter_agent_incomplete_event_mapping(reporter: Any) -> int:
    original_observer = reporter.observe_building_frontier

    def _fake_agent_incomplete_frontier(*_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
        return {
            "frontier_kind": "agent_incomplete",
            "not_proven": ["probe frontier only"],
            "proof_limits": ["support projection probe only"],
        }

    reporter.observe_building_frontier = _fake_agent_incomplete_frontier
    try:
        event_kind = reporter.building_event_kind_from_frontier(
            Path("agent-incomplete-frontier-probe"),
            repo_root=Path.cwd(),
        )
    finally:
        reporter.observe_building_frontier = original_observer
    if event_kind != "intervention_required":
        raise ProfileError(
            "reporter agent_incomplete frontier must emit intervention_required, "
            f"got {event_kind!r}"
        )
    owner = reporter._required_disposition_owner({"frontier_kind": "agent_incomplete"})
    if owner != "caller-or-coo":
        raise ProfileError(
            "reporter agent_incomplete frontier must project caller-or-coo owner, "
            f"got {owner!r}"
        )
    return 2


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
    finished_text = report_sinks._slack_message_text(packet)
    finished_top_level_text = report_sinks._slack_message_text(packet, force_top_level=True)
    intervention_packet = {
        **packet,
        "observed_board_state": "needs_disposition",
        "trigger_event_ref": "building-event:intervention_required:customer-language-probe",
        "frontier_ref": (
            "project/brick-protocol/buildings/customer-language-probe"
            "#frontier:human_review_waiting:event:intervention_required"
        ),
        "required_disposition_owner": "caller-or-coo",
    }
    intervention_text = report_sinks._slack_message_text(intervention_packet)
    intervention_top_level_text = report_sinks._slack_message_text(
        intervention_packet,
        force_top_level=True,
    )
    started_text = report_sinks._slack_message_text(
        {
            **packet,
            "trigger_event_ref": "building-event:building_started:customer-language-probe",
            "observed_board_state": "observed_started",
            "structure_diagram": "[작업·워커] ──▶ (완료)",
        }
    )
    text = "\n---\n".join(
        (
            started_text,
            finished_text,
            intervention_text,
            finished_top_level_text,
            intervention_top_level_text,
        )
    )
    required_fragments = (
        "알림 말투 점검",
        "시작했어요.",
        "진행되는 대로 여기 댓글로 알려드릴게요.",
        "```",
        "[작업·워커] ──▶ (완료)",
        "✅ 다 됐어요!",
        "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)",
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise ProfileError(f"Slack message shape missing fragment {fragment!r}:\n{text}")
    if finished_text != "✅ 다 됐어요!":
        raise ProfileError(f"building_finished reply text was not clean:\n{finished_text}")
    if intervention_text != "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)":
        raise ProfileError(f"intervention_required reply text was not clean:\n{intervention_text}")
    if not finished_top_level_text.startswith("🧱 알림 말투 점검\n"):
        raise ProfileError(
            f"building_finished fallback text was not top-level titled:\n{finished_top_level_text}"
        )
    if not intervention_top_level_text.startswith("🧱 알림 말투 점검\n"):
        raise ProfileError(
            "intervention_required fallback text was not top-level titled:\n"
            f"{intervention_top_level_text}"
        )
    forbidden_fragments = (
        "ref:",
        "brick=",
        "step=",
        "frontier=",
        "※",
        "누구:",
        "다음:",
    )
    for fragment in forbidden_fragments:
        if fragment in text:
            raise ProfileError(f"Slack message leaked customer-facing jargon {fragment!r}:\n{text}")
    forbidden_legacy_fragments = (
        "Brick:",
        "Agent:",
        "Link:",
        "work/step-outputs",
        "마지막 완료 step",
        "step=-",
        "brick=-",
        "운영 refs:",
    )
    for fragment in forbidden_legacy_fragments:
        if fragment in text:
            raise ProfileError(f"Slack message leaked legacy wording {fragment!r}:\n{text}")
    empty_probe = report_sinks._slack_message_text(
        {
            **packet,
            "report_id": "reporter-message-empty-field-probe",
            "current_brick_ref": "",
            "last_completed_step_ref": "",
            "frontier_ref": "project/brick-protocol/buildings/customer-language-probe#frontier:complete",
        }
    )
    for fragment in (*forbidden_fragments, "step=-", "brick=-"):
        if fragment in empty_probe:
            raise ProfileError(f"Slack empty-field probe leaked {fragment!r}:\n{empty_probe}")
    return text, len(required_fragments) + len(forbidden_fragments) + len(forbidden_legacy_fragments) + 1


# EXPLICIT NO-CREDS REPORT ENV (footgun-fix robustness). An EMPTY report_env
# ({}) now AUTO-LOADS ~/.brick/report.env at the run.py engine seam (so a caller
# passing {} can never silently close the Slack gate). That means a literal {}
# no longer reliably exercises the "no Slack creds -> env-gated sink drops"
# coverage on a developer machine that HAS report.env. To keep that coverage
# EXPLICIT (and decoupled from the vessel gate), the no-env probes thread this
# NON-EMPTY mapping that deliberately carries NO BRICK_REPORT_*/BRICK_DASHBOARD_*
# credential key: it is truthy (so it bypasses the empty==auto-load branch) yet
# leaves _slack_environment_ready/_dashboard_environment_ready False on purpose.
_NO_CREDS_REPORT_ENV: dict[str, str] = {"BRICK_REPORT_PROBE_NO_CREDS": "1"}


def _assert_reporter_auto_wiring(repo: Path, reporter: Any, report_sinks: Any) -> tuple[str, str, str, int]:
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.brick.work import parse_required_return_shape
    from support.checkers.lib.case_runners import _preset_completion_command_runner

    inspected = 0
    command_runner = _preset_completion_command_runner(LocalCliCompleted)

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
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                # EXPLICIT no-creds env (not {}): {} now auto-loads, so an empty
                # dict would no longer prove the "no Slack env -> env-gated sink
                # drops" coverage on a machine WITH ~/.brick/report.env. This
                # truthy, credential-free mapping suppresses the env-gated sinks
                # ON PURPOSE and bypasses the empty==auto-load branch.
                report_env=_NO_CREDS_REPORT_ENV,
            )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 5:
            raise ProfileError(
                "basic auto-wiring without Slack env should emit start, brick, and terminal observations"
            )
        for observation in observations:
            sink_refs = observation.get("report_packet", {}).get("sink_refs", [])
            if sink_refs != ["report-sink:local-inbox"]:
                raise ProfileError(
                    f"auto-wiring without Slack env attempted unexpected sinks: {sink_refs}"
                )
        inbox_packets = sorted((temp_repo / "project" / "brick-protocol" / "status" / "inbox").glob("*.json"))
        if len(inbox_packets) != 5:
            raise ProfileError("basic auto-wiring without Slack env did not write five local inbox packets")
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
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_temp_slack_sender,
            )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 5:
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
                command_runner=command_runner,
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
            command_runner=command_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=10,
            # EXPLICIT no-creds env (not {}): keep this probe credential-free and
            # off the empty==auto-load path (the policy only declares local-inbox,
            # so Slack delivery never applies; this just avoids pulling real
            # ~/.brick/report.env creds into a render-only test).
            report_env=_NO_CREDS_REPORT_ENV,
        )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 1:
            raise ProfileError("verbose-mode temp drive emitted wrong event count")
        packet = observations[0].get("report_packet", {})
        verbose_text = report_sinks._slack_message_text(packet)
        if "✅ 다 됐어요!" not in verbose_text:
            raise ProfileError(f"verbose-mode message did not render plain completion:\n{verbose_text}")
        for fragment in ("단계: ", "ref:", "누구:", "다음:"):
            if fragment in verbose_text:
                raise ProfileError(f"verbose-mode message leaked old Slack fragment {fragment!r}:\n{verbose_text}")
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

    sent_payloads: list[Mapping[str, Any]] = []

    def _brain(request: Any) -> Mapping[str, Any]:
        thread_payloads_during_work = [payload for payload in sent_payloads if payload.get("thread_ts")]
        received_during_work = [
            payload
            for payload in thread_payloads_during_work
            if "시작했어요." in str(payload.get("text") or "")
            and "진행되는 대로" not in str(payload.get("text") or "")
        ]
        returned_or_gate_during_work = [
            payload
            for payload in thread_payloads_during_work
            if "단계 끝났어요" in str(payload.get("text") or "")
            or "마무리예요" in str(payload.get("text") or "")
        ]
        if len(received_during_work) != 1:
            raise ProfileError(
                "brick grain work-time probe expected brick_received before Agent work, "
                f"got {len(received_during_work)}"
            )
        if returned_or_gate_during_work:
            raise ProfileError(
                "brick grain work-time probe observed brick_returned/gate_passed before Agent work"
            )
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
    default_policy = reporter.report_event_policy_from_plan({})
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
    if (
        default_policy.get("event_kinds") != expected_brick_events
        or default_policy.get("report_event_grain") != "brick"
    ):
        raise ProfileError(
            "absent report policy did not default to brick grain: "
            f"{default_policy!r}"
        )
    inspected += 6

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
    received_reply_text = ""
    gate_reply_text = ""
    nonterminal_gate_text = ""
    disposition_reply_text = ""
    intervention_reply_text = ""
    finished_reply_text = ""
    fallback_intervention_text = ""
    fallback_finished_text = ""
    with tempfile.TemporaryDirectory(prefix="bp-reporter-brick-grain-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        original_reporter_root = reporter.REPO_ROOT
        try:
            reporter.REPO_ROOT = temp_repo
            result = run_building_plan(
                _reporter_auto_wire_plan("reporter-brick-grain-thread"),
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
        delivery_path = root / "raw" / "report-delivery.jsonl"
        if not delivery_path.is_file():
            raise ProfileError("brick grain delivery timing was not recorded in raw/report-delivery.jsonl")
        delivery_records: list[Mapping[str, Any]] = []
        for line in delivery_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProfileError("raw/report-delivery.jsonl contained invalid JSON") from exc
            if not isinstance(record, Mapping):
                raise ProfileError("raw/report-delivery.jsonl contained a non-mapping record")
            if record.get("kind") == "report_delivery_observation":
                delivery_records.append(record)
        if not delivery_records:
            raise ProfileError("raw/report-delivery.jsonl contained no report delivery observations")

        def _delivery_timestamp(record: Mapping[str, Any]) -> datetime:
            delivered_at = str(record.get("delivered_at") or "").strip()
            if not delivered_at:
                raise ProfileError(f"report delivery record missing delivered_at: {record!r}")
            try:
                return datetime.fromisoformat(delivered_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ProfileError(
                    f"report delivery record delivered_at is not ISO datetime: {delivered_at!r}"
                ) from exc

        active_sink_refs = {
            str(record.get("sink_ref") or "")
            for record in delivery_records
            if str(record.get("event_kind") or "") == "brick_received"
        }
        active_sink_refs.discard("")
        if active_sink_refs != {"report-sink:local-inbox", "report-sink:slack"}:
            raise ProfileError(
                "brick grain expected local-inbox and Slack brick_received delivery records, "
                f"got {sorted(active_sink_refs)!r}"
            )
        by_event_and_sink: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for record in delivery_records:
            if record.get("source_truth") is not False:
                raise ProfileError("report delivery record source_truth is not false")
            key = (
                str(record.get("event_kind") or ""),
                str(record.get("sink_ref") or ""),
            )
            by_event_and_sink.setdefault(key, []).append(record)
        for sink_ref in sorted(active_sink_refs):
            received_records = by_event_and_sink.get(("brick_received", sink_ref), [])
            if len(received_records) != 1:
                raise ProfileError(
                    f"brick grain expected one brick_received delivery record for {sink_ref}, "
                    f"got {len(received_records)}"
                )
            received_at = _delivery_timestamp(received_records[0])
            for later_event in ("brick_returned", "gate_passed", "building_finished"):
                later_records = by_event_and_sink.get((later_event, sink_ref), [])
                if len(later_records) != 1:
                    raise ProfileError(
                        f"brick grain expected one {later_event} delivery record for {sink_ref}, "
                        f"got {len(later_records)}"
                    )
                later_at = _delivery_timestamp(later_records[0])
                if not received_at < later_at:
                    raise ProfileError(
                        "brick_received delivery was not earlier than completion delivery "
                        f"for {sink_ref}/{later_event}: {received_at.isoformat()} >= "
                        f"{later_at.isoformat()}"
                    )

        thread_payloads = [payload for payload in sent_payloads if payload.get("thread_ts")]
        if len(thread_payloads) != 4:
            raise ProfileError(
                "brick grain expected brick_received, brick_returned, gate_passed, "
                f"and completion Slack thread replies, got {len(thread_payloads)}"
            )
        for payload in thread_payloads:
            if payload.get("thread_ts") != "1718200000.000100":
                raise ProfileError(f"brick grain reply carried wrong thread_ts: {payload!r}")
        received_payloads = [
            payload
            for payload in thread_payloads
            if "시작했어요." in str(payload.get("text") or "")
            and "진행되는 대로" not in str(payload.get("text") or "")
        ]
        returned_payloads = [
            payload
            for payload in thread_payloads
            if "단계 끝났어요" in str(payload.get("text") or "")
        ]
        gate_payloads = [
            payload
            for payload in thread_payloads
            if "마무리예요" in str(payload.get("text") or "")
        ]
        if len(received_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one brick_received Slack thread reply, "
                f"got {len(received_payloads)}"
            )
        if len(returned_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one brick_returned Slack thread reply, "
                f"got {len(returned_payloads)}"
            )
        if len(gate_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one terminal gate_passed Slack thread reply, "
                f"got {len(gate_payloads)}"
            )
        received_reply_text = str(received_payloads[0].get("text") or "")
        brick_reply_text = str(returned_payloads[0].get("text") or "")
        gate_reply_text = str(gate_payloads[0].get("text") or "")
        for fragment in ("①", "작업", "시작했어요.", "담당: 워커", "("):
            if fragment not in received_reply_text:
                raise ProfileError(
                    f"brick_received Slack reply missing fragment {fragment!r}:\n{received_reply_text}"
                )
        for fragment in ("①", "작업", "단계 끝났어요", "담당: 워커", "("):
            if fragment not in brick_reply_text:
                raise ProfileError(
                    f"brick grain Slack reply missing fragment {fragment!r}:\n{brick_reply_text}"
                )
        for fragment in ("①", "작업", "확인했어요.", "마무리예요", "("):
            if fragment not in gate_reply_text:
                raise ProfileError(
                    f"gate_passed Slack reply missing fragment {fragment!r}:\n{gate_reply_text}"
                )
        for label, reply_text in (
            ("brick_received", received_reply_text),
            ("brick_returned", brick_reply_text),
            ("gate_passed", gate_reply_text),
        ):
            if not re.search(r"\(\d{2}:\d{2}\)", reply_text):
                raise ProfileError(
                    f"{label} Slack reply did not render KST HH:MM times:\n{reply_text}"
                )
            for fragment in ("ref:", "brick=", "frontier=", "※", "누구:", "다음:"):
                if fragment in reply_text:
                    raise ProfileError(
                        f"{label} Slack reply leaked forbidden fragment {fragment!r}:\n{reply_text}"
                    )
        nonterminal_gate_text = report_sinks._slack_message_text(
            {
                **_minimal_reporter_packet(),
                "report_id": "reporter-gate-nonterminal-probe",
                "building_id": "reporter-brick-grain-thread",
                "trigger_event_ref": "building-event:gate_passed:reporter-brick-grain-thread",
                "current_work_kind": "work",
                "current_lane": "worker",
                "event_context": {
                    "sequence_index": 1,
                    "returned_at": "2026-06-12T00:01:00+00:00",
                    "next_brick_instance_ref": "brick-review",
                    "next_work_kind": "review",
                },
            }
        )
        for fragment in ("①", "작업", "다음 단계(검수)", "넘어가요", "(09:01)"):
            if fragment not in nonterminal_gate_text:
                raise ProfileError(
                    f"nonterminal gate_passed Slack reply missing fragment {fragment!r}:\n"
                    f"{nonterminal_gate_text}"
                )
        finished_payloads = [
            payload
            for payload in thread_payloads
            if "✅ 다 됐어요!" in str(payload.get("text") or "")
        ]
        if len(finished_payloads) != 1:
            raise ProfileError(
                "brick grain expected one completion Slack thread reply, "
                f"got {len(finished_payloads)}"
            )
        finished_reply_text = str(finished_payloads[0].get("text") or "")
        if finished_reply_text != "✅ 다 됐어요!":
            raise ProfileError(
                f"building_finished Slack reply was not a clean comment:\n{finished_reply_text}"
            )
        if "🧱" in finished_reply_text:
            raise ProfileError(
                f"building_finished Slack reply leaked parent title marker:\n{finished_reply_text}"
            )
        inspected += 21

        intervention_payloads: list[Mapping[str, Any]] = []

        def _fake_intervention_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
            intervention_payloads.append(payload)
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        try:
            intervention_packet = reporter.render_building_event_report_packet(
                event_kind="intervention_required",
                building_id="reporter-brick-grain-thread",
                building_root=root,
                current_brick_ref="brick-work",
                last_completed_step_ref="work/step-outputs/reporter-brick-grain-thread-work-attempt-1/step-output.json",
                required_disposition_owner="caller-or-coo",
                sink_refs=["report-sink:slack"],
                repo_root=temp_repo,
                generated_at="2026-06-12T00:03:00+00:00",
                report_event_grain="brick",
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        intervention_observation = report_sinks.send_slack_report_packet(
            intervention_packet,
            repo_root=temp_repo,
            allow_real_delivery=True,
            env=fake_env,
            sender=_fake_intervention_sender,
        )
        if intervention_observation.delivered is not True or len(intervention_payloads) != 1:
            raise ProfileError("intervention_required probe did not send exactly one thread reply")
        if intervention_payloads[0].get("thread_ts") != "1718200000.000100":
            raise ProfileError("intervention_required reply did not carry recorded thread_ts")
        intervention_reply_text = str(intervention_payloads[0].get("text") or "")
        if intervention_reply_text != "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)":
            raise ProfileError(
                "intervention_required Slack reply was not a clean owner-labeled comment:\n"
                f"{intervention_reply_text}"
            )
        if "🧱" in intervention_reply_text:
            raise ProfileError(
                f"intervention_required Slack reply leaked parent title marker:\n{intervention_reply_text}"
            )
        inspected += 4

        missing_thread_payloads: list[Mapping[str, Any]] = []
        fallback_payloads: list[Mapping[str, Any]] = []

        def _should_not_send(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            missing_thread_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true}'

        def _fallback_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            fallback_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        missing_thread_root = output_root / "missing-thread-case"
        missing_thread_root.mkdir(parents=True)
        # SLACK VESSEL-GATE narrowing (slack-wiring-gap 0619): the vessel
        # predicate now requires a REAL declared-building-plan spine (not just the
        # project/<id>/buildings path shape) before external Slack delivery is
        # allowed. This synthetic root models a genuine building that simply has
        # NOT recorded a Slack thread parent yet -- so it must carry a real spine,
        # otherwise external_delivery_allowed would be stripped by the vessel gate
        # and the missing-thread / fallback probes below would observe
        # not_attempted_non_real_vessel instead of the thread-status classes they
        # are pinning.
        (missing_thread_root / "declared-building-plan.json").write_text(
            json.dumps(
                {
                    "brick_steps": [
                        {
                            "completion_edge_ref": "edge:missing-thread-design-to-work",
                            "rows": [
                                {
                                    "axis": "Brick",
                                    "brick_instance_ref": "brick-missing-thread-design",
                                    "brick_work_ref": "work:missing-thread-design",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        try:
            missing_observations = []
            for event_kind in ("brick_received", "brick_returned", "gate_passed"):
                missing_packet = reporter.render_building_event_report_packet(
                    event_kind=event_kind,
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
                        "next_brick_instance_ref": "brick-review",
                        "next_work_kind": "review",
                    },
                )
                missing_observations.append(
                    report_sinks.send_slack_report_packet(
                        missing_packet,
                        repo_root=temp_repo,
                        allow_real_delivery=True,
                        env=fake_env,
                        sender=_should_not_send,
                    )
                )
            fallback_observations = []
            for event_kind in ("intervention_required", "building_finished"):
                fallback_packet = reporter.render_building_event_report_packet(
                    event_kind=event_kind,
                    building_id="missing-thread-case",
                    building_root=missing_thread_root,
                    current_brick_ref="brick-work",
                    last_completed_step_ref=(
                        "work/step-outputs/missing-thread-case-work-attempt-1/"
                        "step-output.json"
                    ),
                    required_disposition_owner="caller-or-coo",
                    sink_refs=["report-sink:slack"],
                    repo_root=temp_repo,
                    generated_at="2026-06-12T00:04:00+00:00",
                    report_event_grain="brick",
                )
                fallback_observations.append(
                    report_sinks.send_slack_report_packet(
                        fallback_packet,
                        repo_root=temp_repo,
                        allow_real_delivery=True,
                        env=fake_env,
                        sender=_fallback_sender,
                    )
                )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        if any(
            observation.delivery_status_class != "not_attempted_missing_thread_ts"
            for observation in missing_observations
        ):
            raise ProfileError("brick grain missing-thread Slack sends did not all fail closed")
        if missing_thread_payloads:
            raise ProfileError("brick grain missing-thread probe still called Slack sender")
        if any(observation.delivered is not True for observation in fallback_observations):
            raise ProfileError("HOLD/FINISH missing-thread fallback did not send")
        if len(fallback_payloads) != 2:
            raise ProfileError(
                f"HOLD/FINISH missing-thread fallback sent {len(fallback_payloads)} payload(s)"
            )
        for payload in fallback_payloads:
            if payload.get("thread_ts"):
                raise ProfileError(f"missing-thread fallback unexpectedly carried thread_ts: {payload!r}")
        fallback_intervention_text = str(fallback_payloads[0].get("text") or "")
        fallback_finished_text = str(fallback_payloads[1].get("text") or "")
        if fallback_intervention_text != (
            "🧱 missing-thread-case\n"
            "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)"
        ):
            raise ProfileError(
                "intervention_required missing-thread fallback did not preserve titled form:\n"
                f"{fallback_intervention_text}"
            )
        if fallback_finished_text != "🧱 missing-thread-case\n✅ 다 됐어요!":
            raise ProfileError(
                "building_finished missing-thread fallback did not preserve titled form:\n"
                f"{fallback_finished_text}"
            )
        inspected += 5

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
        if "⤷ COO 확인" not in disposition_reply_text:
            raise ProfileError(
                f"disposition_applied reply did not render coo stamp:\n{disposition_reply_text}"
            )
        if "다음 단계로 진행" not in disposition_reply_text:
            raise ProfileError(
                "explicit-forward disposition_applied reply did not preserve the forward label:\n"
                f"{disposition_reply_text}"
            )
        missing_action_disposition_text = report_sinks._slack_message_text(
            {
                **_minimal_reporter_packet(),
                "report_id": "reporter-disposition-missing-action-probe",
                "building_id": "reporter-brick-grain-thread",
                "trigger_event_ref": (
                    "building-event:disposition_applied:reporter-brick-grain-thread"
                ),
                "current_work_kind": "work",
                "current_lane": "worker",
                "generated_at": "2026-06-12T00:02:00+00:00",
                "event_context": {
                    "disposition_author_ref": "coo:checker",
                    "applied_at": "2026-06-12T00:02:00+00:00",
                },
            }
        )
        for fragment in ("forward", "다음 단계로 진행"):
            if fragment in missing_action_disposition_text:
                raise ProfileError(
                    "missing-action disposition_applied reply rendered Movement-shaped "
                    f"default {fragment!r}:\n{missing_action_disposition_text}"
                )
        inspected += 5

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

    return (
        "\n".join(
            text
            for text in (
                received_reply_text,
                brick_reply_text,
                gate_reply_text,
                nonterminal_gate_text,
                intervention_reply_text,
                finished_reply_text,
                fallback_intervention_text,
                fallback_finished_text,
            )
            if text
        ),
        disposition_reply_text,
        inspected,
    )


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
        step: dict[str, Any] = {
            "step_ref": step_ref,
            "step_template_ref": f"building-step-template:{kind}",
        }
        if kind == "work":
            step["selected_adapter_ref"] = "adapter:local"
        step["rows"] = [
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
        ]
        steps.append(step)
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
    agent_incomplete_event_count = _assert_reporter_agent_incomplete_event_mapping(reporter)
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
            + agent_incomplete_event_count
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
            f"{agent_incomplete_event_count} agent-incomplete event assertion(s), "
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
    from support.checkers import check_building_declaration_integrity as declaration_integrity
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
        building_map = json.loads(
            (root / "work" / "building-map.json").read_text(encoding="utf-8")
        )
        if not building_map.get("declaration_provenance"):
            raise ProfileError(
                "adapter_error_path_hardening root lacks declaration_provenance"
            )
        for rel in declaration_integrity.DECLARATION_CHAIN_ARTIFACTS:
            artifact = root / Path(*rel)
            if not artifact.is_file():
                raise ProfileError(
                    "adapter_error_path_hardening declaration_provenance root "
                    f"lacks required chain artifact {artifact.relative_to(root)}"
                )
        declaration_violations = declaration_integrity.validate_building_root(
            root,
            label="adapter-error-hardening-first-step",
        )
        if declaration_violations:
            raise ProfileError(
                "adapter_error_path_hardening declaration-integrity rejected root:\n"
                + "\n".join(f"- {violation}" for violation in declaration_violations)
            )
        diagnostic_root = output_root / "adapter-error-hardening-diagnostics"
        _write_adapter_error_frontier_direct(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=diagnostic_root.name,
            overwrite_existing=True,
        )
        _assert_adapter_error_diagnostics_preserved(diagnostic_root)
        _assert_adapter_error_frontier_report_root_admission(run_module, repo, output_root)
        inspected += 15
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
            "adapter invocation for flat and legacy reason-ref holds, pre-frontier "
            "report raw logs are admitted only for the same Building, codex "
            "--ephemeral is env-gated, overwrite cleared stale claim_trace/raw "
            "manifest refs, and F16/F16b/F19 mutation probes fired RED."
        ),
    )


def _assert_adapter_error_frontier_report_root_admission(
    run_module: Any,
    repo: Path,
    output_root: Path,
) -> None:
    from support.recording import adapter_error_frontier

    base_building_id = "adapter-error-hardening-report-root"
    reroute_building_id = f"{base_building_id}-reroute1"
    root = output_root / base_building_id
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "work").mkdir(parents=True, exist_ok=True)
    (root / "declared-building-plan.json").write_text(
        json.dumps({"building_id": base_building_id}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "work" / "declared-building-plan.json").write_text(
        json.dumps({"building_id": base_building_id}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "raw" / "report-delivery.jsonl").write_text(
        json.dumps(
            {
                "kind": "report_delivery_observation",
                "schema_version": "report-delivery-0",
                "building_id": base_building_id,
                "report_id": f"report:{base_building_id}:building-started",
                "source_truth": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    thread_path = root / "raw" / "report-thread.jsonl"
    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=(
            f"brick-protocol-{base_building_id}-building-started-event-"
            "2026-06-25T00-00-00-00-00"
        ),
    )
    if not adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: declaration root with pre-frontier "
            "live vessel report raw logs was rejected"
        )

    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=f"report:{base_building_id}:building-started",
    )
    if not adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: declaration root with exact "
            "legacy report: report-thread row was rejected"
        )

    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id="report:other-building:building-started",
    )
    if adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: wrong-building report-thread row "
            "was admitted"
        )

    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=(
            f"brick-protocol-{reroute_building_id}-building-started-event-"
            "2026-06-25T00-00-00-00-00"
        ),
    )
    if adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: prefix-related live vessel "
            "report-thread row was admitted"
        )

    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=(
            f"brick-protocol-rogue-prefix-{base_building_id}-building-started-event-"
            "2026-06-25T00-00-00-00-00"
        ),
    )
    if adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: suffix-collision live vessel "
            "report-thread row was admitted"
        )

    embedded_marker_source_id = (
        f"brick-protocol-{base_building_id}-gate-passed-event-evil"
    )
    embedded_marker_report_id = (
        f"{embedded_marker_source_id}-building-started-event-"
        "2026-06-25T00-00-00-00-00"
    )
    if (
        adapter_error_frontier._report_id_source_id(embedded_marker_report_id)
        != embedded_marker_source_id
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: report id source parser did not "
            "right-anchor on the trailing event suffix"
        )
    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=embedded_marker_report_id,
    )
    if adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: embedded event-marker foreign "
            "report-thread row was admitted"
        )

    partial_id = "adapter-error-hardening-partial-root"
    partial_root = output_root / partial_id
    (partial_root / "raw").mkdir(parents=True, exist_ok=True)
    (partial_root / "work").mkdir(parents=True, exist_ok=True)
    (partial_root / "declared-building-plan.json").write_text(
        json.dumps({"building_id": partial_id}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (partial_root / "work" / "declared-building-plan.json").write_text(
        json.dumps({"building_id": partial_id}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (partial_root / "raw" / "partial-write.jsonl").write_text(
        json.dumps(
            {
                "kind": "non_declaration_artifact",
                "building_id": partial_id,
                "source_truth": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if adapter_error_frontier._adapter_error_existing_root_state(
        partial_root,
        building_id=partial_id,
    ) != "partial_write_risk":
        raise ProfileError(
            "adapter_error_path_hardening P0: non-declaration root was not "
            "classified as partial_write_risk"
        )
    partial_result = _write_adapter_error_frontier_direct(
        run_module,
        repo=repo,
        output_root=output_root,
        building_id=partial_id,
        overwrite_existing=True,
    )
    marker_path = partial_root / "adapter-error-frontier-partial-write-risk.json"
    if partial_result.written_files != (marker_path,) or not marker_path.is_file():
        raise ProfileError(
            "adapter_error_path_hardening P0: partial-write-risk marker was not written"
        )
    if not (partial_root / "raw" / "partial-write.jsonl").is_file():
        raise ProfileError(
            "adapter_error_path_hardening P0: partial-write-risk artifact was clobbered"
        )
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker.get("frontier_kind") != "partial_write_risk":
        raise ProfileError(
            "adapter_error_path_hardening P0: partial-write-risk marker lacks "
            "frontier_kind"
        )

    empty_id = "adapter-error-hardening-empty-root"
    empty_root = output_root / empty_id
    empty_root.mkdir(parents=True, exist_ok=True)
    empty_result = _write_adapter_error_frontier_direct(
        run_module,
        repo=repo,
        output_root=output_root,
        building_id=empty_id,
        overwrite_existing=False,
    )
    empty_marker_path = empty_root / "adapter-error-frontier-root-state.json"
    if empty_result.written_files != (empty_marker_path,) or not empty_marker_path.is_file():
        raise ProfileError(
            "adapter_error_path_hardening P0: empty-root marker was not written"
        )
    empty_marker = json.loads(empty_marker_path.read_text(encoding="utf-8"))
    if empty_marker.get("frontier_kind") != "root_exists_without_frontier":
        raise ProfileError(
            "adapter_error_path_hardening P0: empty-root marker lacks "
            "root_exists_without_frontier"
        )

    file_id = "adapter-error-hardening-not-directory"
    (output_root / file_id).write_text("not a directory\n", encoding="utf-8")
    try:
        _write_adapter_error_frontier_direct(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=file_id,
            overwrite_existing=True,
        )
    except NotADirectoryError as exc:
        if "existing_root_state=not_directory" not in str(exc):
            raise ProfileError(
                "adapter_error_path_hardening P0: not-directory error lacked "
                "root-state evidence"
            ) from exc
    else:
        raise ProfileError(
            "adapter_error_path_hardening P0: not-directory root was not rejected"
        )


def _write_adapter_error_report_thread_probe(path: Path, *, report_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "kind": "report_slack_thread_parent_observation",
                "report_id": report_id,
                "source_truth": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_adapter_error_frontier_direct(
    run_module: Any,
    *,
    repo: Path,
    output_root: Path,
    building_id: str,
    overwrite_existing: bool,
) -> Any:
    from support.recording import adapter_error_frontier

    plan = _adapter_error_hardening_graph_plan(
        building_id,
        first_adapter_ref="adapter:codex-local",
    )
    first_step = plan["brick_steps"][0]
    link_row = plan["link_edges"][0]["rows"][0]
    brick_row = next(row for row in first_step["rows"] if row.get("axis") == "Brick")
    agent_row = next(row for row in first_step["rows"] if row.get("axis") == "Agent")
    packet = {
        "building_id": building_id,
        "selected_adapter_ref": "adapter:codex-local",
        "step_rows": {
            "step_ref": first_step["step_ref"],
            "rows": [brick_row, agent_row, link_row],
        },
    }
    prepared = run_module.prepare_agent_run_from_step_rows(
        packet,
        proof_limits=("checker fixture support evidence only",),
    )
    adapter_request = run_module._adapter_request_from_prepared(
        packet,
        prepared,
        project_ref=None,
    )
    return adapter_error_frontier.write_adapter_error_frontier_evidence(
        building_id=building_id,
        plan_ref=f"plan:{building_id}",
        plan=plan,
        completed_step_results=(),
        failed_preparation=prepared,
        adapter_request=adapter_request,
        adapter_error={
            "error_kind": "local_cli_timeout",
            "exception_type": "TimeoutExpired",
            "message_excerpt": "timeout",
            "timeout_reap_reason": "timeout",
            "timeout_stdout_excerpt": "partial stdout before timeout",
            "timeout_stderr_excerpt": "partial stderr before timeout",
            "proof_limits": ("checker fixture support evidence only",),
            "not_proven": ("complete adapter-error lifecycle frontier",),
        },
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        proof_limits=("checker fixture support evidence only",),
    )


def _assert_adapter_error_diagnostics_preserved(root: Path) -> None:
    expected = {
        "timeout_reap_reason": "timeout",
        "timeout_stdout_excerpt": "partial stdout before timeout",
        "timeout_stderr_excerpt": "partial stderr before timeout",
    }
    raw_path = root / "raw" / "adapter-error.jsonl"
    if not raw_path.is_file():
        raise ProfileError("adapter_error_path_hardening diagnostics root lacks raw adapter-error")
    raw_records = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(raw_records) != 1:
        raise ProfileError("adapter_error_path_hardening diagnostics expected one raw row")
    step_paths = sorted((root / "work" / "step-outputs").glob("*/adapter-error.json"))
    if len(step_paths) != 1:
        raise ProfileError("adapter_error_path_hardening diagnostics expected one step-output")
    step_record = json.loads(step_paths[0].read_text(encoding="utf-8"))
    for label, record in (("raw", raw_records[0]), ("step-output", step_record)):
        for key, value in expected.items():
            if record.get(key) != value:
                raise ProfileError(
                    "adapter_error_path_hardening diagnostics dropped "
                    f"{key} from {label}"
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
    from brick_protocol.support.connection import adapter_local_cli
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
        absent = adapter_local_cli._invoke_local_cli(
            spec,
            request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=runner,
        )
        if "--skip-git-repo-check" not in absent.args:
            raise ProfileError("codex-exec-readonly did not emit --skip-git-repo-check")
        # Ephemeral is now the DEFAULT (concurrent-codex shared-state deadlock
        # fix): absent env var must still emit --ephemeral.
        if "--ephemeral" not in absent.args:
            raise ProfileError("BRICK_CODEX_EPHEMERAL absent did not emit --ephemeral (default-on)")
        os.environ["BRICK_CODEX_EPHEMERAL"] = "0"
        optout = adapter_local_cli._invoke_local_cli(
            spec,
            request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=runner,
        )
        if "--skip-git-repo-check" not in optout.args:
            raise ProfileError("codex-exec-readonly dropped --skip-git-repo-check on ephemeral opt-out")
        if "--ephemeral" in optout.args:
            raise ProfileError("BRICK_CODEX_EPHEMERAL=0 still emitted --ephemeral (opt-out broken)")
        os.environ["BRICK_CODEX_EPHEMERAL"] = "1"
        enabled = adapter_local_cli._invoke_local_cli(
            spec,
            request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=runner,
        )
        if "--skip-git-repo-check" not in enabled.args:
            raise ProfileError("codex-exec-readonly dropped --skip-git-repo-check with --ephemeral")
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
            returned={"secret": "done", "observed_evidence": ["bad"]},
            expected="forbidden key 'secret'",
            label="forbidden secret key",
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
        "user-home": _SMITH_USER_HOME_LITERAL + "/project",
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


def _dashboard_state_recent_recorded_at() -> str:
    """Relative-recent fixture timestamp (DETERMINISM FIX 0619).

    Previously hardcoded "2026-06-12T00:00:00Z"; the dashboard staleness
    projection (dashboard_export._disp_state: age_days >= stale_days=7 ->
    archived_stale) compares last-evidence vs now(), so a fixed fixture date
    aged past the 7-day window and flipped projection-mid-walk from the expected
    'running' to 'archived_stale' (a time-bomb that turned --all RED on 0619 = the
    fixture date + 7d). A recent (now - 1 day) timestamp keeps the mid-walk fixture
    inside the live window deterministically -> always 'running'.
    """

    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dashboard_state_link_record(
    case_id: str,
    *,
    target_ref: str,
    building_lifecycle_state: str = "",
) -> Mapping[str, Any]:
    record = {
        "raw_ref": f"raw:link:{case_id}",
        "recorded_at": _dashboard_state_recent_recorded_at(),
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
        "recorded_at": _dashboard_state_recent_recorded_at(),
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
    # The chat-session key-scan lives wherever submit_chat_session_return is
    # DEFINED (S11 relocated it run.py -> run_chat_session.py). Patch the rejector
    # binding on that module so the FIRE mutation reaches the live call path; run's
    # facade re-export points at the same function, so .__module__ tracks the home.
    submit_module = sys.modules[run_module.submit_chat_session_return.__module__]
    original_rejector = submit_module._reject_session_like_text
    submit_module._reject_session_like_text = _chat_session_value_only_session_rejector
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
        submit_module._reject_session_like_text = original_rejector


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
    from support.checkers import check_building_declaration_integrity as declaration_integrity
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
    for rel in declaration_integrity.DECLARATION_CHAIN_ARTIFACTS:
        artifact = building_root / Path(*rel)
        if not artifact.is_file():
            raise ProfileError(
                f"chat_session_park_seam {label} path declaration evidence "
                f"lacks required chain artifact {artifact.relative_to(building_root)}"
            )
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
    building_map = _chat_session_json_object(building_root / "work" / "building-map.json")
    provenance = building_map.get("declaration_provenance")
    if not isinstance(provenance, Mapping):
        raise ProfileError(
            f"chat_session_park_seam {label} path building-map lacks declaration_provenance"
        )
    if provenance.get("building_id") != building_root.name:
        raise ProfileError(
            f"chat_session_park_seam {label} path declaration_provenance names wrong Building"
        )
    proof_limits = provenance.get("proof_limits")
    if not isinstance(proof_limits, list) or "not Movement authority" not in proof_limits:
        raise ProfileError(
            f"chat_session_park_seam {label} path declaration_provenance lacks support proof limits"
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
    return 17


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
    returned["secret"] = "done"
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


_BRICK_CLI_ENTRYPOINT_TIMEOUT_SECONDS = 30


def _assert_brick_cli_probe(label: str, completed: subprocess.CompletedProcess[str]) -> None:
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if "Traceback" in stderr or "ModuleNotFoundError" in stderr:
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} crashed at startup:\n"
            + stderr.strip()
        )
    if completed.returncode != 0:
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} exited {completed.returncode}.\n"
            f"stdout:\n{stdout.strip()}\nstderr:\n{stderr.strip()}"
        )
    try:
        packet = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} did not emit JSON status evidence.\n"
            f"stdout:\n{stdout.strip()}\nstderr:\n{stderr.strip()}"
        ) from exc
    if not isinstance(packet, dict) or packet.get("command") != "status":
        raise ProfileError(
            f"brick_cli_entrypoint_smoke: {label} emitted unexpected packet: {packet!r}"
        )


def _assert_brick_cli_customer_task_intent(cli: Any, repo: Path) -> int:
    from brick_protocol.support.operator.composition_intent import materialize_building_intent

    parser = cli.build_parser()
    graph_args = parser.parse_args(["build", "--graph-packet", "graph.json"])
    if getattr(graph_args, "graph_packet", "") != "graph.json":
        raise ProfileError("brick_cli_entrypoint_smoke: --graph-packet did not bind graph_packet")
    graph_alias_args = parser.parse_args(["build", "--graph", "graph.json"])
    if getattr(graph_alias_args, "graph_packet", "") != "graph.json":
        raise ProfileError("brick_cli_entrypoint_smoke: --graph alias did not bind graph_packet")

    local_args = parser.parse_args(["build", "--task", "make x"])
    local_intent = cli._build_intent(local_args)
    if local_intent.get("selected_adapter_ref") != "adapter:local":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: local task default changed adapter "
            f"unexpectedly: {local_intent!r}"
        )
    if local_intent.get("chain_preset_ref") != cli.DEFAULT_LOCAL_PRESET_REF:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: local task default must keep onboarding "
            f"graph preset, got {local_intent!r}"
        )
    if "write_scope" in local_intent:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: local task default must not declare write_scope"
        )

    original_preflight_provider = cli.preflight_provider

    def set_preflight(rows_by_adapter: Mapping[str, Mapping[str, Any]]) -> None:
        def fake_preflight(adapter_ref: str) -> dict[str, Any]:
            row = dict(rows_by_adapter.get(adapter_ref, {}))
            row.setdefault("adapter_ref", adapter_ref)
            row.setdefault("installed", bool(row.get("ok")))
            row.setdefault("authed", "unknown")
            row.setdefault("message_ko", "checker synthetic readiness")
            return row

        cli.preflight_provider = fake_preflight

    try:
        set_preflight(
            {
                "adapter:claude-local": {"ok": True},
                "adapter:codex-local": {"ok": True},
                "adapter:gemini-local": {"ok": True},
            }
        )
        real_args = parser.parse_args(["build", "--task", "make x", "--real-provider"])
        real_intent = cli._build_intent(real_args)
        if real_intent.get("selected_adapter_ref") != "adapter:claude-local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: --real-provider omitted --adapter must "
                f"select first ready provider in declared order, got {real_intent!r}"
            )

        set_preflight(
            {
                "adapter:claude-local": {"ok": False, "installed": False},
                "adapter:codex-local": {"ok": False, "installed": False},
                "adapter:gemini-local": {
                    "ok": True,
                    "api_key_env_present": True,
                    "credential_validity": "not_proven",
                    "raw_secret": "SHOULD_NOT_APPEAR",
                },
            }
        )
        gemini_args = parser.parse_args(["build", "--task", "make x", "--real-provider"])
        gemini_intent = cli._build_intent(gemini_args)
        if gemini_intent.get("selected_adapter_ref") != "adapter:gemini-local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: --real-provider must select ready "
                f"adapter:gemini-local when it is the first ready provider, got {gemini_intent!r}"
            )
        if "adapter:gemini-api" in json.dumps(gemini_intent, sort_keys=True):
            raise ProfileError("brick_cli_entrypoint_smoke: gemini-api appeared in first-ready evidence")
        readiness_text = json.dumps(
            gemini_intent.get("provider_readiness_observations", []), sort_keys=True
        )
        if "SHOULD_NOT_APPEAR" in readiness_text or "raw_secret" in readiness_text:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: provider readiness evidence leaked raw credential data"
            )
        gemini_plan = materialize_building_intent(gemini_intent, repo_root=repo)
        gemini_step_adapters = {
            str(step.get("selected_adapter_ref") or "")
            for step in gemini_plan.get("brick_steps", [])
            if isinstance(step, Mapping)
        }
        if "adapter:gemini-local" not in gemini_step_adapters:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: selected adapter:gemini-local did not "
                f"flow into materialized work Brick rows: {gemini_step_adapters!r}"
            )

        set_preflight(
            {
                "adapter:claude-local": {"ok": True},
                "adapter:codex-local": {"ok": True},
                "adapter:gemini-local": {"ok": True},
            }
        )
        explicit_real_args = parser.parse_args(
            ["build", "--task", "make x", "--real-provider", "--adapter", "adapter:codex-local"]
        )
        explicit_real_intent = cli._build_intent(explicit_real_args)
        if explicit_real_intent.get("selected_adapter_ref") != "adapter:codex-local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit --adapter must win over "
                f"first-ready selection, got {explicit_real_intent!r}"
            )
        if explicit_real_intent.get("provider_readiness_observations"):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit --adapter must not record "
                "first-ready readiness observations"
            )

        set_preflight(
            {
                "adapter:claude-local": {"ok": False, "installed": False},
                "adapter:codex-local": {"ok": False, "installed": False},
                "adapter:gemini-local": {
                    "ok": False,
                    "installed": True,
                    "api_key_env_present": False,
                    "credential_validity": "not_proven",
                },
            }
        )
        no_ready_args = parser.parse_args(["build", "--task", "make x", "--real-provider"])
        no_ready_intent = cli._build_intent(no_ready_args)
        if no_ready_intent.get("selected_adapter_ref") != "adapter:local":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: no ready real provider must fall back "
                f"to adapter:local, got {no_ready_intent!r}"
            )
        if "write_scope" in no_ready_intent:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: no-ready adapter:local fallback must not declare write_scope"
            )
    finally:
        cli.preflight_provider = original_preflight_provider

    real_intent = explicit_real_intent
    if real_intent.get("chain_preset_ref") != cli.DEFAULT_REAL_TASK_PRESET_REF:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: explicit real-provider task must default to "
            f"fast-fix, got {real_intent!r}"
        )
    write_scope = real_intent.get("write_scope")
    if not isinstance(write_scope, Mapping):
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --real-provider task must carry Brick write_scope"
        )
    if write_scope.get("allowed_paths") != ["."] or write_scope.get("forbidden_paths") != [".git/**"]:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --real-provider task write_scope must stay "
            f"worktree-bounded, got {write_scope!r}"
        )

    plan = materialize_building_intent(real_intent, repo_root=repo)
    work_rows = _brick_cli_work_brick_rows(plan)
    if not work_rows:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --real-provider task fast-fix plan emitted no work Brick"
        )
    scoped_rows = [
        row
        for row in work_rows
        if row.get("write_scope") == write_scope
        and row.get("requires_brick_write_scope") is True
    ]
    if not scoped_rows:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --real-provider task write_scope did not land "
            f"on a requires_brick_write_scope work Brick row: {work_rows!r}"
        )

    with tempfile.TemporaryDirectory(prefix="bp-cli-task-home-") as home_tmp:
        expected_root = str(Path(home_tmp) / ".brick" / "project" / "brick-protocol" / "buildings")
        task_call: dict[str, Any] = {}

        class FakeTaskResult:
            building_id = "cli-task-wrapper"
            isolation_mode = "worktree"
            isolation_reason = "checker synthetic"
            base_sha = "abc123"
            worktree_path = "/tmp/checker-task-worktree"
            evidence_root = expected_root + "/cli-task-wrapper"
            frontier_kind = "agent_incomplete"
            commit_sha = ""
            worktree_disposed = True
            intake_result = None

        original_task_runner = cli.run_customer_building_in_sandbox
        old_home = os.environ.get("HOME")
        try:
            os.environ["HOME"] = home_tmp

            def fake_task_runner(intent: Mapping[str, Any], **kwargs: Any) -> FakeTaskResult:
                task_call["intent"] = dict(intent)
                task_call["kwargs"] = dict(kwargs)
                return FakeTaskResult()

            cli.run_customer_building_in_sandbox = fake_task_runner
            task_build_args = parser.parse_args(
                [
                    "build",
                    "--task",
                    "task wrapper fixture",
                    "--preset",
                    cli.DEFAULT_LOCAL_PRESET_REF,
                    "--building-id",
                    "cli-task-wrapper",
                    "--json",
                ]
            )
            task_result = cli._run_build(task_build_args)
        finally:
            cli.run_customer_building_in_sandbox = original_task_runner
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

        legacy_home_root = str(Path(home_tmp) / ".brick" / "builds")
        if task_result.get("build_input_mode") != "preset_task":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task build did not expose "
                "build_input_mode=preset_task"
            )
        if task_result.get("output_root") != expected_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task default output_root must be "
                f"caller-local {expected_root}, got {task_result.get('output_root')!r}"
            )
        if task_result.get("output_root") == legacy_home_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task default revived legacy ~/.brick/builds"
            )
        if str(task_call.get("kwargs", {}).get("output_root")) != expected_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task wrapper dispatch did not "
                "receive the active Slack-facing vessel root"
            )
        if task_call.get("kwargs", {}).get("customer_repo_root") != repo:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task wrapper dispatch did not receive repo root"
            )
        if task_call.get("intent", {}).get("chain_preset_ref") != cli.DEFAULT_LOCAL_PRESET_REF:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: preset/task wrapper dispatch changed "
                f"the local preset intent: {task_call.get('intent')!r}"
            )

    with tempfile.TemporaryDirectory(prefix="bp-cli-task-explicit-") as tmp:
        explicit_root = Path(tmp) / "declared-output-root"
        explicit_call: dict[str, Any] = {}

        class FakeExplicitTaskResult:
            building_id = "cli-task-explicit"
            isolation_mode = "worktree"
            isolation_reason = "checker synthetic"
            base_sha = "abc123"
            worktree_path = "/tmp/checker-task-explicit-worktree"
            evidence_root = str(explicit_root / "cli-task-explicit")
            frontier_kind = "agent_incomplete"
            commit_sha = ""
            worktree_disposed = True
            intake_result = None

        original_task_runner = cli.run_customer_building_in_sandbox
        try:

            def fake_explicit_task_runner(
                intent: Mapping[str, Any],
                **kwargs: Any,
            ) -> FakeExplicitTaskResult:
                explicit_call["intent"] = dict(intent)
                explicit_call["kwargs"] = dict(kwargs)
                return FakeExplicitTaskResult()

            cli.run_customer_building_in_sandbox = fake_explicit_task_runner
            explicit_args = parser.parse_args(
                [
                    "build",
                    "--task",
                    "task explicit fixture",
                    "--building-id",
                    "cli-task-explicit",
                    "--output-root",
                    str(explicit_root),
                    "--json",
                ]
            )
            explicit_result = cli._run_build(explicit_args)
        finally:
            cli.run_customer_building_in_sandbox = original_task_runner

        if explicit_result.get("output_root") != str(explicit_root.resolve()):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit preset/task --output-root "
                f"did not win, got {explicit_result.get('output_root')!r}"
            )
        if str(explicit_call.get("kwargs", {}).get("output_root")) != str(explicit_root.resolve()):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: explicit preset/task wrapper dispatch "
                "did not receive declared --output-root"
            )

    api_args = parser.parse_args(["build", "--task", "make x", "--adapter", "adapter:gemini-api"])
    try:
        cli._build_intent(api_args)
    except ValueError as exc:
        if "adapter_ref is not admitted" not in str(exc):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: retired adapter:gemini-api rejected "
                "with wrong reason"
            ) from exc
    else:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: retired adapter:gemini-api was accepted"
        )

    incomplete_packet = {
        "repo_root": str(repo),
        "building_id": "cli-frontier-not-ready-probe",
        "adapter_ref": "adapter:gemini-local",
        "chain_preset_ref": cli.DEFAULT_REAL_TASK_PRESET_REF,
        "isolation_mode": "worktree",
        "evidence_root": str(repo / "project" / "brick-protocol" / "buildings" / "probe"),
        "frontier_kind": "agent_incomplete",
        "customer_visible_frontier_state": cli._customer_visible_frontier_state("agent_incomplete"),
        "customer_visible_not_ready": True,
        "customer_visible_frontier_message": cli._customer_visible_frontier_message(
            "agent_incomplete"
        ),
        "proof_limits": list(cli.PROOF_LIMITS),
        "not_proven": list(cli.NOT_PROVEN),
    }
    rendered = cli._render_build(incomplete_packet)
    for required in (
        "frontier_kind: agent_incomplete",
        "customer_visible_frontier_state: not_ready",
        "customer_visible_not_ready: yes",
        "frontier_message: not ready:",
        "evidence_root",
    ):
        if required not in rendered:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: build render did not surface "
                f"non-ready frontier evidence fragment {required!r}; rendered={rendered!r}"
            )
    if cli._customer_visible_frontier_state("complete") != "frontier_complete":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: complete frontier must render frontier_complete"
        )
    if cli._customer_visible_frontier_state("agent_incomplete") != "not_ready":
        raise ProfileError(
            "brick_cli_entrypoint_smoke: non-complete frontier must render not_ready"
        )

    with tempfile.TemporaryDirectory(prefix="bp-cli-graph-invalid-") as tmp:
        tmp_root = Path(tmp)
        invalid_graph = tmp_root / "invalid-graph.json"
        invalid_graph.write_text('{"task_statement": "x"}\n', encoding="utf-8")
        invalid_output = tmp_root / "must-not-exist"
        invalid_args = parser.parse_args(
            [
                "build",
                "--graph-packet",
                str(invalid_graph),
                "--output-root",
                str(invalid_output),
            ]
        )
        try:
            cli._run_build(invalid_args)
        except ValueError as exc:
            if "graph packet requires" not in str(exc):
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: invalid graph packet rejected "
                    f"with wrong reason: {exc}"
                ) from exc
        else:
            raise ProfileError("brick_cli_entrypoint_smoke: invalid graph packet was accepted")
        if invalid_output.exists():
            raise ProfileError(
                "brick_cli_entrypoint_smoke: invalid graph invocation created output_root "
                "before semantic validation"
            )

    graph_packet = {
        "task_statement": "graph fixture task",
        "declared_by": "coo:cli-graph-checker",
        "building_id": "cli-graph-fixture",
        "nodes": [
            {
                "node_ref": "node:work",
                "step_ref": "cli-graph-work",
                "step_template_ref": "building-step-template:work",
            }
        ],
        "edges": [],
        "selected_adapter_ref": "adapter:local",
        "selected_model_ref": "model:default",
        "groups": [],
    }
    with tempfile.TemporaryDirectory(prefix="bp-cli-graph-home-") as home_tmp, tempfile.TemporaryDirectory(
        prefix="bp-cli-graph-packet-"
    ) as packet_tmp:
        expected_graph_root = str(Path(home_tmp) / ".brick" / "project" / "brick-protocol" / "buildings")
        graph_path = Path(packet_tmp) / "graph.json"
        graph_path.write_text(json.dumps(graph_packet, sort_keys=True) + "\n", encoding="utf-8")
        graph_call: dict[str, Any] = {}

        class FakeGraphResult:
            building_id = "cli-graph-fixture"
            isolation_mode = "worktree"
            isolation_reason = "checker synthetic"
            base_sha = "abc123"
            worktree_path = "/tmp/checker-worktree"
            evidence_root = expected_graph_root + "/cli-graph-fixture"
            frontier_kind = "agent_incomplete"
            commit_sha = ""
            worktree_disposed = True
            intake_result = None

        original_graph_runner = cli.run_customer_graph_building_in_sandbox
        old_home = os.environ.get("HOME")
        try:
            os.environ["HOME"] = home_tmp

            def fake_graph_runner(packet: Mapping[str, Any], **kwargs: Any) -> FakeGraphResult:
                graph_call["packet"] = dict(packet)
                graph_call["kwargs"] = dict(kwargs)
                return FakeGraphResult()

            cli.run_customer_graph_building_in_sandbox = fake_graph_runner
            graph_build_args = parser.parse_args(["build", "--graph", str(graph_path), "--json"])
            graph_result = cli._run_build(graph_build_args)
        finally:
            cli.run_customer_graph_building_in_sandbox = original_graph_runner
            if old_home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old_home

        if graph_result.get("build_input_mode") != "graph_packet":
            raise ProfileError(
                "brick_cli_entrypoint_smoke: graph build did not expose build_input_mode=graph_packet"
            )
        if graph_result.get("output_root") != expected_graph_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: graph default output_root must be "
                f"caller-local {expected_graph_root}, got {graph_result.get('output_root')!r}"
            )
        if str(graph_call.get("kwargs", {}).get("output_root")) != expected_graph_root:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: graph wrapper dispatch did not receive "
                "the caller-local active Slack-facing vessel root"
            )
        if graph_call.get("kwargs", {}).get("customer_repo_root") != repo:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: graph wrapper dispatch did not receive repo root"
            )
        if graph_call.get("packet", {}).get("nodes") != graph_packet["nodes"]:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: graph wrapper dispatch did not receive declared nodes"
            )
        rendered_graph = cli._render_build(graph_result)
        if "build_input_mode: graph_packet" not in rendered_graph:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: graph render did not expose build_input_mode"
            )

        forbidden_graph_packet = dict(graph_packet)
        forbidden_graph_packet["nodes"] = [
            {
                "node_ref": "node:work",
                "step_ref": "cli-graph-work",
                "step_template_ref": "building-step-template:work",
                "required_return_shape": "observed_evidence, not_proven",
                "brick": {
                    "work_statement": "forbidden graph fixture",
                    "carries_forward_fields": "observed_evidence",
                },
            }
        ]
        forbidden_graph_path = Path(packet_tmp) / "forbidden-graph.json"
        forbidden_graph_path.write_text(
            json.dumps(forbidden_graph_packet, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        forbidden_graph_args = parser.parse_args(
            ["build", "--graph", str(forbidden_graph_path), "--json"]
        )
        try:
            cli._run_build(forbidden_graph_args)
        except ValueError as exc:
            message = str(exc)
            if "customer graph_packet may not author Brick template-owned field" not in message:
                raise ProfileError(
                    "brick_cli_entrypoint_smoke: forbidden graph return-shape "
                    f"override rejected with wrong reason: {exc}"
                ) from exc
            for required_offender in (
                "cli-graph-work.required_return_shape",
                "cli-graph-work.carries_forward_fields",
            ):
                if required_offender not in message:
                    raise ProfileError(
                        "brick_cli_entrypoint_smoke: forbidden graph override "
                        f"did not report {required_offender!r}: {message}"
                    )
        else:
            raise ProfileError(
                "brick_cli_entrypoint_smoke: graph packet author-required_return_shape "
                "override was accepted"
            )

    large_stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(large_stderr):
            parser.parse_args(["build", "--large", "--task", "large fixture task"])
    except SystemExit:
        pass
    else:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: --large became a public official build mode"
        )

    large_packet_builder = getattr(cli, "_p3_easy_large_graph_packet", None)
    if large_packet_builder is not None:
        raise ProfileError(
            "brick_cli_entrypoint_smoke: hidden _p3_easy_large_graph_packet helper "
            "must stay absent/fail-closed; official input modes are preset_task and graph_packet"
        )

    conflict_args = parser.parse_args(
        ["build", "--graph", str(graph_path), "--task", "also task"]
    )
    try:
        cli._run_build(conflict_args)
    except ValueError as exc:
        if "either graph packet mode or task/task-source mode" not in str(exc):
            raise ProfileError(
                "brick_cli_entrypoint_smoke: graph/task conflict rejected with wrong reason"
            ) from exc
    else:
        raise ProfileError("brick_cli_entrypoint_smoke: graph/task conflict was accepted")

    return 10


def _brick_cli_work_brick_rows(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    containers: list[Any] = []
    if isinstance(plan.get("steps"), list):
        containers.extend(plan.get("steps", []))
    if isinstance(plan.get("brick_steps"), list):
        containers.extend(plan.get("brick_steps", []))
    for container in containers:
        if not isinstance(container, Mapping):
            continue
        step_template_ref = container.get("step_template_ref")
        for row in container.get("rows", []):
            if (
                isinstance(row, Mapping)
                and row.get("axis") == "Brick"
                and step_template_ref == "building-step-template:work"
            ):
                rows.append(row)
    return rows


def run_brick_cli_entrypoint_smoke(repo: Path) -> KernelResult:
    """Bare-entrypoint smoke for the customer-facing ``brick`` CLI.

    The R1 trap is a console-script/import context launched from outside the repo
    with PYTHONPATH unset: the import-identity router can expose
    ``brick_protocol.*``, but existing transitive modules may still import bare
    ``support.*``. ``support/operator/cli.py`` must therefore insert BOTH the repo
    root and ``support/import_identity`` before importing support seams.
    """

    script = repo / "support" / "operator" / "cli.py"
    if not script.is_file():
        raise ProfileError(f"brick_cli_entrypoint_smoke could not find CLI script: {script}")

    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)
    clean_env["BRICK_CLI_ENTRYPOINT_REPO"] = str(repo)

    with tempfile.TemporaryDirectory(prefix="bp-cli-entrypoint-cwd-") as cwd:
        direct = subprocess.run(
            [
                sys.executable,
                str(script),
                "status",
                "--json",
                "--repo",
                str(repo),
            ],
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=cwd,
            timeout=_BRICK_CLI_ENTRYPOINT_TIMEOUT_SECONDS,
        )
        _assert_brick_cli_probe("direct script launch", direct)

        import_code = """
import os
import sys
from pathlib import Path

repo = Path(os.environ["BRICK_CLI_ENTRYPOINT_REPO"])
sys.path.insert(0, str(repo / "support" / "import_identity"))
import brick_protocol.support.operator.cli as cli
import support.operator.coo_operating_chain
raise SystemExit(cli.main(["status", "--json", "--repo", str(repo)]))
"""
        imported = subprocess.run(
            [sys.executable, "-c", import_code],
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=cwd,
            timeout=_BRICK_CLI_ENTRYPOINT_TIMEOUT_SECONDS,
        )
        _assert_brick_cli_probe("import-identity console-script simulation", imported)

    _ensure_import_identity(repo)
    cli = importlib.import_module("brick_protocol.support.operator.cli")
    inspected = 2 + _assert_brick_cli_customer_task_intent(cli, repo)

    return KernelResult(
        check_id="brick_cli_entrypoint_smoke",
        inspected=inspected,
        output=(
            "brick CLI entrypoint smoke passed: direct script and import-identity "
            "console-script simulation ran from outside the repo with PYTHONPATH "
            "unset and emitted status JSON without ModuleNotFoundError; customer "
            "task intent defaults keep local runs read-only while --real-provider "
            "tasks materialize fast-fix with worktree-bounded Brick write_scope"
        ),
    )


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
    render_packet = agent_resources.render_agent_packet
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
    write_probe_role = "pm-lead" if "pm-lead" in roles else "dev"
    write_probe_packet = render_packet(write_probe_role, repo_root=repo)
    write_capable_policies = list(write_probe_packet["agent_object"]["tool_policy_refs"])
    write_capable_resources = list(write_probe_packet["tool_policy_resources"])
    leak_sandbox = sandbox_for_policies(
        write_capable_policies,
        write_need=False,
        native_grant_resources=write_capable_resources,
    )
    if leak_sandbox != "read-only":
        raise ProfileError(
            "codex_projection_native: a write-capable agent on a read-only Brick "
            f"(write_need=False) must project sandbox_mode read-only, got "
            f"{leak_sandbox!r} (capability overrode the Brick NEED)"
        )
    write_sandbox = sandbox_for_policies(
        write_capable_policies,
        write_need=True,
        native_grant_resources=write_capable_resources,
    )
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
    render_packet = agent_resources.render_agent_packet

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
    write_probe_role = "pm-lead" if "pm-lead" in roles else "dev"
    write_probe_packet = render_packet(write_probe_role, repo_root=repo)
    write_capable_policies = list(write_probe_packet["agent_object"]["tool_policy_refs"])
    write_capable_resources = list(write_probe_packet["tool_policy_resources"])
    leak_tools = list(
        tools_for_policies(
            write_capable_policies,
            write_need=False,
            native_grant_resources=write_capable_resources,
        )["tools"]
    )
    if not write_tool_names.isdisjoint(set(leak_tools)):
        raise ProfileError(
            "claude_projection_native: a write-capable agent on a read-only Brick "
            f"(write_need=False) must project a tool set with NO Edit/Write/Bash, got "
            f"{leak_tools} (capability overrode the Brick NEED)"
        )
    write_tools = list(
        tools_for_policies(
            write_capable_policies,
            write_need=True,
            native_grant_resources=write_capable_resources,
        )["tools"]
    )
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

"""Axis-vocab drift kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes axis vocabulary parity and competing enum literal definitions; it owns
no axis crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    to_posix,
    to_repo_path,
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
# in code as brick_protocol/agent/return_fact.py:TRANSITION_CONCERN_KINDS (the source of truth)
# and is documented in AGENTS.md under this header line as a fenced ```text```
# block (one value per line). The parity check compares the two directly and
# fails on any divergence in either direction; it hardcodes NO third copy of the
# values, so the values themselves are pinned only at the code surface.
_AXIS_VOCAB_CONCERN_KIND_SOURCE = "brick_protocol/agent/return_fact.py"
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
# from brick_protocol/link/transition.py + brick_protocol/link/movement.py in _axis_vocab_check_link_sources.
_AXIS_VOCAB_DOC_PATHS = (
    "AGENTS.md",
)


_AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST = {
    "brick_protocol/link/movement.py",
    "brick_protocol/support/checkers/check_axis_contract_projection.py",
    "brick_protocol/support/checkers/check_profile.py",
    # ELEGANT-REFACTOR P3a: the axis-vocab drift check (with its re-encoded enum
    # literals) moved here from check_profile.py; the self-allowlist follows the
    # rehome (checker-pin-follows-rehome standard).
    "brick_protocol/support/checkers/lib/axis_vocab_drift_check.py",
}


_AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST = {
    "brick_protocol/link/transition.py",
    "brick_protocol/support/checkers/check_building_operator_driver0.py",
    "brick_protocol/support/checkers/check_profile.py",
    "brick_protocol/support/checkers/lib/axis_vocab_drift_check.py",
}


_AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST = {
    "brick_protocol/support/connection/agent_adapter.py",
    "brick_protocol/support/checkers/check_profile.py",
    "brick_protocol/support/checkers/lib/axis_vocab_drift_check.py",
}


_AXIS_VOCAB_TRANSITION_AUTHOR_PREFIX_CONSUMERS = (
    "brick_protocol/support/operator/plan_validation.py",
    "brick_protocol/support/operator/walker_resume.py",
    "brick_protocol/support/operator/walker_step_fixture.py",
)


_AXIS_VOCAB_PYTHON_SCAN_ROOTS = ("brick_protocol/brick", "brick_protocol/agent", "brick_protocol/link", "brick_protocol/support")


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
        is_absolute = node.level == 0 and node.module == f"brick_protocol.support.connection.{module_name}"
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
                    "enum literal must import/read brick_protocol/link/transition.py DISPOSITION_ACTIONS"
                )
            if values == adapter_set and relative not in _AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST:
                violations.append(
                    f"{relative}:{getattr(node, 'lineno', '?')}: exact adapter ref enum "
                    "literal must import/read brick_protocol/support/connection/agent_adapter.py ALLOWED_ADAPTER_REFS"
                )
    return inspected


def _axis_vocab_check_link_sources(repo: Path, violations: list[str]) -> None:
    movement_tree, _movement_text = _axis_vocab_parse_python(repo, "brick_protocol/link/movement.py")
    transition_tree, _transition_text = _axis_vocab_parse_python(repo, "brick_protocol/link/transition.py")
    movement_env = _axis_vocab_module_env(movement_tree)
    transition_env = _axis_vocab_module_env(transition_tree)

    movement_literals = _axis_vocab_sequence(movement_env, "MOVEMENT_LITERALS", "brick_protocol/link/movement.py")
    if movement_literals != _AXIS_VOCAB_EXPECTED_MOVEMENT:
        violations.append(
            "brick_protocol/link/movement.py: MOVEMENT_LITERALS must equal "
            f"{list(_AXIS_VOCAB_EXPECTED_MOVEMENT)}, observed {list(movement_literals)}"
        )

    disposition_actions = _axis_vocab_sequence(
        transition_env,
        "DISPOSITION_ACTIONS",
        "brick_protocol/link/transition.py",
    )
    if disposition_actions != _AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS:
        violations.append(
            "brick_protocol/link/transition.py: DISPOSITION_ACTIONS must equal "
            f"{list(_AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS)}, observed {list(disposition_actions)}"
        )

    owners = _axis_vocab_set(
        transition_env,
        "TRANSITION_LIFECYCLE_DISPOSITION_OWNERS",
        "brick_protocol/link/transition.py",
    )
    expected_owners = frozenset(_AXIS_VOCAB_EXPECTED_DISPOSITION_OWNERS)
    if owners != expected_owners:
        violations.append(
            "brick_protocol/link/transition.py: TRANSITION_LIFECYCLE_DISPOSITION_OWNERS must equal "
            f"{sorted(expected_owners)}, observed {sorted(owners)}"
        )
    if "human" in owners:
        violations.append("brick_protocol/link/transition.py: human must not be a required_disposition_owner")

    progress_states = _axis_vocab_set(
        transition_env,
        "TRANSITION_LIFECYCLE_PROGRESS_STATES",
        "brick_protocol/link/transition.py",
    )
    expected_progress = frozenset(_AXIS_VOCAB_EXPECTED_PROGRESS_STATES)
    if progress_states != expected_progress:
        violations.append(
            "brick_protocol/link/transition.py: TRANSITION_LIFECYCLE_PROGRESS_STATES must equal "
            f"{sorted(expected_progress)}, observed {sorted(progress_states)}"
        )

    allowed_keys = _axis_vocab_set(
        transition_env,
        "TRANSITION_LIFECYCLE_ALLOWED_KEYS",
        "brick_protocol/link/transition.py",
    )
    missing_keys = sorted(set(_AXIS_VOCAB_REQUIRED_TRANSITION_KEYS) - set(allowed_keys))
    if missing_keys:
        violations.append(
            "brick_protocol/link/transition.py: TRANSITION_LIFECYCLE_ALLOWED_KEYS missing "
            f"{missing_keys}"
        )

    author_prefixes = _axis_vocab_sequence(
        transition_env,
        "TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES",
        "brick_protocol/link/transition.py",
    )
    if author_prefixes != _AXIS_VOCAB_EXPECTED_AUTHOR_PREFIXES:
        violations.append(
            "brick_protocol/link/transition.py: TRANSITION_LIFECYCLE_DISPOSITION_AUTHOR_PREFIXES must equal "
            f"{list(_AXIS_VOCAB_EXPECTED_AUTHOR_PREFIXES)}, observed {list(author_prefixes)}"
        )
    if "caller:" in author_prefixes:
        violations.append("brick_protocol/link/transition.py: caller: is not an admitted transition disposition author prefix")


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
    adapter_constants_rel = "brick_protocol/support/connection/adapter_constants.py"
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
        "brick_protocol/support/connection/agent_resources.py",
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
            "brick_protocol/support/connection/agent_resources.py: must import ALLOWED_ADAPTER_REFS "
            "from .adapter_constants"
        )
    elif not _axis_vocab_name_used(resources_tree, allowed_alias):
        violations.append(
            "brick_protocol/support/connection/agent_resources.py: imported ALLOWED_ADAPTER_REFS "
            f"alias {allowed_alias!r} is not read"
        )
    if not write_capability_alias:
        violations.append(
            "brick_protocol/support/connection/agent_resources.py: must import adapter_is_write_capable "
            "from .agent_adapter"
        )
    elif not _axis_vocab_name_used(resources_tree, write_capability_alias):
        violations.append(
            "brick_protocol/support/connection/agent_resources.py: imported adapter_is_write_capable "
            f"alias {write_capability_alias!r} is not read"
        )

    assigned = _axis_vocab_assigned_names(resources_tree)
    for forbidden_name in {"ALLOWED_ADAPTER_REFS", "_ALLOWED_ADAPTER_REFS"} & assigned:
        violations.append(
            "brick_protocol/support/connection/agent_resources.py: must not assign duplicate adapter "
            f"ref object {forbidden_name}"
        )
    for node in ast.walk(resources_tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if all(adapter_ref in node.value for adapter_ref in _AXIS_VOCAB_EXPECTED_ADAPTER_REFS):
                violations.append(
                    "brick_protocol/support/connection/agent_resources.py:"
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


def _run_core_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "brick_protocol/support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "core",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = '_AXIS_VOCAB_EXPECTED_MOVEMENT = ("forward", "reroute")'
    poisoned = '_AXIS_VOCAB_EXPECTED_MOVEMENT = ("forward",)'
    if needle not in original:
        raise ProfileError("axis_vocab_drift mutation probe could not find movement tuple")

    backup = tempfile.NamedTemporaryFile(
        prefix=".axis-vocab-drift-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_core_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "axis_vocab_drift mutation probe did not turn core profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_core_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "axis_vocab_drift mutation probe restored source but core profile "
            f"remained RED:\n{excerpt}"
        )

    return [
        "axis-vocab mutation RED probe passed: poisoning the moved Movement tuple "
        "made check_profile.py --profile core exit non-zero, then restoring the "
        "temp-backed self file returned core to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for axis-vocab drift."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily mutate this leaf's consumed Movement tuple, assert core "
            "profile exits RED, restore from a temp backup, then assert core GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = probe_mutation_red(repo) if args.probe_mutation_red else [
            run_axis_vocab_drift(repo).output
        ]
    except ProfileError as exc:
        print("axis-vocab drift rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

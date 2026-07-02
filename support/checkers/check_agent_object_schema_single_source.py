#!/usr/bin/env python3
"""Seal the agent-OBJECT key/ref/forbidden schema to ONE source on the Agent axis.

AGENT-OBJECT SCHEMA SINGLE-SOURCE LAW (③ struct-surgery 0623). The Agent axis owns
the SHAPE of an agent-object record — which keys it may carry (``allowed_keys``),
which file-backed ref fields it lists (``ref_fields``), and which keys it must
NEVER carry (``forbidden_keys`` — provider connectors / credentials / session ids,
and success/failure/quality/movement-authority fields). That schema lives ONCE, at
``agent/spec.AGENT_OBJECT_SCHEMA`` (assembled from the literal ``_AGENT_OBJECT_*``
member tuples on the same axis, with the casting key names DERIVED from
``CASTING_FIELDS``). Every consumer DERIVES from it:

  * the support load path (``agent_resources._load_agent_object``) validates a
    loaded role yaml against it via ``agent.spec.validate_agent_object_keys``;
  * the inline COMPOSE path (``agent.spec.agent("dev", tools=[...], ...)``)
    validates the composed object against the SAME ``validate_agent_object_keys``;
  * ``primitives._AGENT_OBJECT_ALLOWED_KEYS`` / ``_AGENT_OBJECT_REF_FIELDS``,
    ``agent_resources._AGENT_OBJECT_KEYS`` / ``_REF_FIELDS`` /
    ``_FORBIDDEN_AGENT_OBJECT_KEYS``, and
    ``native_dispatch._NATIVE_DISPATCH_FORBIDDEN_AGENT_OBJECT_KEYS`` are now ALIASES
    of the schema fields (attribute reads), not hand copies.

The GOAL the schema buys: the role-yaml path and the compose path admit/reject an
agent-object's key-set IDENTICALLY because they read ONE schema, and a new resource
field or forbidden key is added in ONE place. That goal is only real if the
key/ref/forbidden member-sets cannot be RE-ENUMERATED elsewhere. Before this
surgery the allowed-key set, the 6-name ref-field tuple, and the 16-name
forbidden-key frozenset were COPIED across three support files
(agent_resources.py, primitives.py, native_dispatch.py); a future edit could grow a
fourth copy and the copies would silently drift (one such copy ALREADY omitted the
casting keys and RAISED on a real role — the M8 bug). This checker is the missing
structural half: it FAILS CLOSED if the ref or forbidden member-set is enumerated
as a literal collection anywhere but the single source.

Two AST rules (NO import of the scanned modules; pure structural evidence):

  RULE 1 — the single source REALLY lives in ``agent/spec.py``. The module must
  define ``AGENT_OBJECT_SCHEMA``, the ``_AGENT_OBJECT_REF_FIELDS`` literal (the
  6-name ref tuple), the ``_AGENT_OBJECT_FORBIDDEN_KEYS`` literal (the 16-name
  forbidden frozenset), and the shared ``validate_agent_object_keys`` gate the load
  + compose paths both call. A missing piece means the schema is not actually
  single-sourced on the axis -> reject.

  RULE 2 — NO ref-set or forbidden-set ENUMERATION outside the single source. Any
  collection literal (tuple / list / set / frozenset, incl. the ``frozenset({...})``
  / ``set([...])`` wrappers) whose member-set EQUALS the ref-field member-set OR the
  forbidden-key member-set is a re-stated schema fragment and is rejected in EVERY
  module except ``agent/spec.py``. A single-field-by-name read
  (``agent_object.get("adapter_refs")``) can never equal a (>= 2-member) registered
  set, so it is structurally outside this rule and never flagged.

This is the agent-axis twin of ``check_gate_registry_single_source`` (the Link gate
vocabulary guard) and a focused companion to the registry-driven
``check_axis_field_set_single_source`` (which scans only support/): this guard is
keyed specifically to the agent-object schema and scans the AXIS modules + support,
so a re-enumeration of the ref/forbidden set ANYWHERE — not only under support/ —
REDs.

Support evidence only: this checker parses the modules instead of importing them,
and does not call providers, choose Movement, judge source truth, judge success or
quality, or classify Building outcomes.

Pass => exit 0. Reject => exit 1.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]

# The single source: the agent-object schema + its literal member tuples + the
# shared key-set gate live here, on the Agent axis.
_SPEC_REL = Path("agent/spec.py")

# The schema symbol + the two literal member symbols + the shared gate the single
# source must define (RULE 1 positive assertion).
_SCHEMA_SYMBOL = "AGENT_OBJECT_SCHEMA"
_REF_FIELDS_SYMBOL = "_AGENT_OBJECT_REF_FIELDS"
_HEAD_KEYS_SYMBOL = "_AGENT_OBJECT_HEAD_KEYS"
_FORBIDDEN_KEYS_SYMBOL = "_AGENT_OBJECT_FORBIDDEN_KEYS"
_KEYSET_GATE_FN = "validate_agent_object_keys"

# The two member-sets this guard seals to the single source. These are the EXACT
# member-sets agent/spec.py enumerates once; nowhere else may a collection literal
# enumerate either (RULE 2). Kept here as the checker's independent re-encode (the
# guard imports no axis module), exactly as check_gate_registry encodes the gate
# prefix independently.
_REF_FIELD_MEMBERS: frozenset[str] = frozenset(
    {
        "prompt_refs",
        "skill_refs",
        "hook_refs",
        "tool_policy_refs",
        "discipline_refs",
        "adapter_refs",
    }
)
_HEAD_KEY_MEMBERS: frozenset[str] = frozenset(
    {
        "object_ref",
        "name",
        "lane",
        "callable_performer_refs",
    }
)
_FORBIDDEN_KEY_MEMBERS: frozenset[str] = frozenset(
    {
        "provider_connector_refs",
        "provider_request_body",
        "credential_body",
        "setup_token",
        "setup_token_value",
        "session_id",
        "provider_session_id",
        "agent_fact_shape",
        "agentfact_shape",
        "success",
        "failure",
        "quality",
        "movement_choice",
        "choose_movement",
        "default_gatefact",
        "default_gate_fact",
    }
)
# Named member-set -> its frozenset, for RULE 2 matching + violation text.
_SEALED_MEMBER_SETS: dict[str, frozenset[str]] = {
    "agent-object head-key set": _HEAD_KEY_MEMBERS,
    "agent-object ref-field set": _REF_FIELD_MEMBERS,
    "agent-object forbidden-key set": _FORBIDDEN_KEY_MEMBERS,
}

# Which axis + support trees to scan for a re-enumeration (RULE 2). The single
# source agent/spec.py is excluded — it legitimately enumerates each set once.
_SCAN_DIRS = ("agent", "brick", "link", "support")

# Modules excluded from the RULE 2 re-enumeration scan: the single source
# (agent/spec.py, which owns the literals) and THIS checker itself (an independent
# oracle: it must re-encode the EXPECTED member-sets to make the RULE 1 positive
# assertion, exactly as check_gate_registry encodes the gate prefix independently —
# the oracle's own copy is the verification baseline, not a drifting consumer mirror).
_SCAN_EXCLUDE: frozenset[Path] = frozenset(
    {
        _SPEC_REL,
        Path("support/checkers/check_agent_object_schema_single_source.py"),
    }
)

PROOF_LIMIT = (
    "proof limit: agent-object schema single-source checker support evidence only; "
    "it does not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or the runtime correctness of any agent-object. "
    "It proves only that the agent-object key/ref/forbidden SCHEMA is enumerated in "
    "exactly one place — agent/spec.AGENT_OBJECT_SCHEMA (over its _AGENT_OBJECT_* "
    "member literals) with the validate_agent_object_keys gate — and that the "
    "ref-field and forbidden-key member-sets are re-stated nowhere else."
)


class AgentObjectSchemaSingleSourceError(ValueError):
    """Raised when the agent-object schema or a member-set lives outside the source."""


def _parse(repo: Path, rel: Path) -> ast.Module:
    path = repo / rel
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(rel))
    except OSError as exc:
        raise AgentObjectSchemaSingleSourceError(f"could not read {rel}: {exc}") from exc
    except SyntaxError as exc:
        raise AgentObjectSchemaSingleSourceError(f"{rel} is not valid Python: {exc}") from exc


def _string_constant(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _all_string_members(elements: list[ast.expr]) -> frozenset[str] | None:
    """The set of string literals in ``elements`` iff EVERY element is a string
    literal (and there is no duplicate). None otherwise — so a tuple of descriptor
    calls or a partial overlap is never treated as a clean member-set."""

    names: list[str] = []
    for element in elements:
        text = _string_constant(element)
        if text is None:
            return None
        names.append(text)
    if not names:
        return None
    if len(set(names)) != len(names):
        return None
    return frozenset(names)


def _literal_member_set(node: ast.AST) -> frozenset[str] | None:
    """Member-set of a string-collection literal node, else None.

    Covers ``{...}`` / ``[...]`` / ``(...)`` of string constants and the
    ``frozenset({...})`` / ``set([...])`` / ``frozenset([...])`` call wrappers,
    mirroring check_axis_field_set_single_source._literal_member_set so the two
    guards recognize the same enumeration shapes.
    """

    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        return _all_string_members(list(node.elts))
    if isinstance(node, ast.Call):
        func = node.func
        builder = getattr(func, "id", None) or getattr(func, "attr", None)
        if builder in {"frozenset", "set"} and len(node.args) == 1 and not node.keywords:
            inner = node.args[0]
            if isinstance(inner, (ast.Set, ast.List, ast.Tuple)):
                return _all_string_members(list(inner.elts))
    return None


def _defines_symbol(module: ast.Module, name: str) -> bool:
    for node in ast.walk(module):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return True
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            return True
    return False


def _defines_function(module: ast.Module, name: str) -> bool:
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return True
    return False


def _symbol_member_set(module: ast.Module, name: str) -> frozenset[str] | None:
    """The literal member-set bound to module-level symbol ``name``, else None."""

    for node in ast.walk(module):
        target_name: str | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value = node.value
        if target_name == name and value is not None:
            return _literal_member_set(value)
    return None


def check_spec_single_source(module: ast.Module) -> list[str]:
    """RULE 1: positively assert the single source REALLY lives in agent/spec.py.

    The schema symbol, the two literal member symbols (with the exact member-sets),
    and the shared key-set gate must all be defined here.
    """

    violations: list[str] = []
    if not _defines_symbol(module, _SCHEMA_SYMBOL):
        violations.append(
            f"agent/spec.py defines no {_SCHEMA_SYMBOL} (the agent-object schema "
            "must be the single source on the Agent axis)"
        )
    if not _defines_function(module, _KEYSET_GATE_FN):
        violations.append(
            f"agent/spec.py defines no {_KEYSET_GATE_FN}() (the ONE key-set gate the "
            "load path and the compose path must both call)"
        )
    head_members = _symbol_member_set(module, _HEAD_KEYS_SYMBOL)
    if head_members != _HEAD_KEY_MEMBERS:
        violations.append(
            f"agent/spec.py {_HEAD_KEYS_SYMBOL} does not enumerate the agent-object "
            f"head-key set (found {sorted(head_members) if head_members else None}, "
            f"expected {sorted(_HEAD_KEY_MEMBERS)})"
        )
    ref_members = _symbol_member_set(module, _REF_FIELDS_SYMBOL)
    if ref_members != _REF_FIELD_MEMBERS:
        violations.append(
            f"agent/spec.py {_REF_FIELDS_SYMBOL} does not enumerate the agent-object "
            f"ref-field set (found {sorted(ref_members) if ref_members else None}, "
            f"expected {sorted(_REF_FIELD_MEMBERS)})"
        )
    forbidden_members = _symbol_member_set(module, _FORBIDDEN_KEYS_SYMBOL)
    if forbidden_members != _FORBIDDEN_KEY_MEMBERS:
        violations.append(
            f"agent/spec.py {_FORBIDDEN_KEYS_SYMBOL} does not enumerate the "
            f"agent-object forbidden-key set (found "
            f"{sorted(forbidden_members) if forbidden_members else None}, expected "
            f"{sorted(_FORBIDDEN_KEY_MEMBERS)})"
        )
    return violations


def check_no_member_set_enumeration(rel: Path, module: ast.Module) -> list[str]:
    """RULE 2: reject a re-stated ref-set / forbidden-set outside the single source."""

    violations: list[str] = []
    for node in ast.walk(module):
        member_set = _literal_member_set(node)
        if member_set is None:
            continue
        for label, sealed in _SEALED_MEMBER_SETS.items():
            if member_set == sealed:
                line = getattr(node, "lineno", -1)
                violations.append(
                    f"{rel} enumerates the {label} (a collection literal of its "
                    f"members at line {line}) — this set is owned ONCE by "
                    f"agent/spec.AGENT_OBJECT_SCHEMA (its {_REF_FIELDS_SYMBOL} / "
                    f"{_FORBIDDEN_KEYS_SYMBOL} literals); import the schema and read "
                    "its field instead of re-enumerating the members"
                )
    return violations


def _iter_scan_modules(repo: Path) -> list[tuple[Path, Path]]:
    """Every *.py under the scanned trees EXCEPT the single source agent/spec.py."""

    found: list[tuple[Path, Path]] = []
    for top in _SCAN_DIRS:
        root = repo / top
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            rel = path.relative_to(repo)
            if rel in _SCAN_EXCLUDE:
                continue
            if path.name == "__init__.py":
                continue
            found.append((rel, path))
    return found


def check(repo: Path) -> list[str]:
    spec_module = _parse(repo, _SPEC_REL)

    violations: list[str] = []
    violations.extend(check_spec_single_source(spec_module))

    scanned = 0
    for rel, path in _iter_scan_modules(repo):
        try:
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(rel))
        except (OSError, SyntaxError) as exc:
            violations.append(f"{rel}: could not parse for agent-object schema scan: {exc}")
            continue
        scanned += 1
        violations.extend(check_no_member_set_enumeration(rel, module))

    if violations:
        raise AgentObjectSchemaSingleSourceError(
            "agent-object schema lives outside the single source:\n"
            + "\n".join(f"- {v}" for v in sorted(set(violations)))
        )

    mutation_line = _assert_mutation_red()
    return [
        "agent-object schema single-source green: the agent-object key/ref/forbidden "
        "schema is enumerated ONCE in agent/spec.AGENT_OBJECT_SCHEMA (over its "
        f"{_REF_FIELDS_SYMBOL} / {_FORBIDDEN_KEYS_SYMBOL} literals; allowed_keys "
        "derives the casting names from CASTING_FIELDS), with the "
        f"{_KEYSET_GATE_FN}() gate the load + compose paths both call; the ref-field "
        f"and forbidden-key member-sets are re-stated in none of {scanned} scanned "
        "axis/support module(s).",
        mutation_line,
        PROOF_LIMIT,
    ]


def _assert_mutation_red() -> str:
    """FIRE probe: a re-stated ref-set / forbidden-set must RED, a by-name read must NOT.

    Builds three synthetic bodies: (1) a module that re-enumerates the ref-field set
    as a literal frozenset (the old _REF_FIELDS shape), (2) a module that
    re-enumerates the forbidden-key set, and (3) a lone by-name read of one ref
    field. Asserts RULE 2 fires on (1) and (2) and stays clean on (3). This is the
    permanent mutation-RED guard: a real edit re-growing either copy REDs exactly as
    these probes prove on the synthetic bodies.
    """

    restated_refs = ast.parse(
        "\n".join(
            [
                "_REF_FIELDS = (",
                '    "prompt_refs",',
                '    "skill_refs",',
                '    "hook_refs",',
                '    "tool_policy_refs",',
                '    "discipline_refs",',
                '    "adapter_refs",',
                ")",
            ]
        )
    )
    refs_red = bool(check_no_member_set_enumeration(Path("synthetic_refs.py"), restated_refs))

    restated_heads = ast.parse(
        "HEAD_KEYS = ("
        + ", ".join(f'"{name}"' for name in sorted(_HEAD_KEY_MEMBERS))
        + ")"
    )
    heads_red = bool(check_no_member_set_enumeration(Path("synthetic_heads.py"), restated_heads))

    restated_forbidden = ast.parse(
        "FORBIDDEN = frozenset({"
        + ", ".join(f'"{name}"' for name in sorted(_FORBIDDEN_KEY_MEMBERS))
        + "})"
    )
    forbidden_red = bool(
        check_no_member_set_enumeration(Path("synthetic_forbidden.py"), restated_forbidden)
    )

    # A lone by-name read MUST NOT be flagged (false-RED guard).
    lone_read = ast.parse(
        "\n".join(
            [
                "def f(obj):",
                '    return obj.get("adapter_refs")',
            ]
        )
    )
    lone_clean = not check_no_member_set_enumeration(Path("synthetic_lone.py"), lone_read)

    if not (heads_red and refs_red and forbidden_red and lone_clean):
        raise AgentObjectSchemaSingleSourceError(
            "mutation RED failed: "
            f"heads_red={heads_red}, refs_red={refs_red}, forbidden_red={forbidden_red}, "
            f"lone_clean={lone_clean} (a re-stated head-key set, ref-field set, and "
            "forbidden-key set must be rejected, and a lone by-name read must NOT be)"
        )
    return (
        "mutation RED observed: a synthetic re-enumerated head-key tuple, "
        "ref-field tuple, and forbidden-key frozenset were rejected by RULE 2, "
        'and a lone `obj.get("adapter_refs")` by-name read was correctly left clean.'
    )


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker that seals the agent-object key/ref/forbidden "
            "schema to agent/spec.AGENT_OBJECT_SCHEMA (one source on the Agent axis; "
            "the ref-field and forbidden-key member-sets re-stated nowhere else)."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except AgentObjectSchemaSingleSourceError as exc:
        print("agent-object schema single-source rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

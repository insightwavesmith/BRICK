#!/usr/bin/env python3
"""General invariant: every resource an Agent Object declares resolves to a real target.

Each Agent Object (agent/objects/*.yaml) declares resource refs — prompt_refs,
skill_refs, tool_policy_refs, discipline_refs (file-backed) and adapter_refs
(an admitted vocabulary). The engine resolves the file-backed refs through
agent_resources._resource_path and rejects an adapter ref outside
agent_adapter.ALLOWED_ADAPTER_REFS at request time. Nothing statically asserts
that every *declared* ref actually has a target: agent_resource_boundary checks
profile required/forbidden ref policy, axis_vocab_drift checks the ALLOWED set
*definition*, and package_path_admission admits files that exist (the reverse
direction). So an object can declare skill:gone or adapter:bogus and pass every
checker until it breaks at resolve/request time.

This checker is the Agent twin of declared_verifier_exists: every declared,
file-backed resource ref uses the correct prefix for its field (a skill_refs
entry must be a skill: ref, etc.) and resolves to an existing file (using the
engine's own _resource_path so the checker validates exactly where the engine
looks), and every declared adapter ref is in the engine's current
ALLOWED_ADAPTER_REFS. It
reuses the engine symbols (not a static replica) so it is drift-proof and
adapts to whatever adapter vocabulary the current tree admits (e.g. after an
adapter retirement) — a half-done retirement that drops an adapter from the
ALLOWED set but leaves it on an object REDs here.

hook_refs and callable_performer_refs use a different resolution mechanism
(registry/bindings, performer wiring) and are out of scope.

Support evidence only: proves declared resource refs resolve, not that the
target content is correct, nor source truth, success, quality, or Movement
authority.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import MISSING, fields
from pathlib import Path


# Each file-backed ref field and the ref prefix it MUST use. The engine's
# agent_resources._resource_path resolves by prefix, so a ref placed in the
# wrong field (e.g. a prompt: ref under skill_refs) would resolve to the wrong
# resource kind; the prefix must match the field.
FIELD_PREFIX = {
    "prompt_refs": "prompt:",
    "skill_refs": "skill:",
    "tool_policy_refs": "tool-policy:",
    "discipline_refs": "discipline:",
}
OBJECTS_DIR = Path("agent/objects")
AGENT_OBJECT_HEAD_FIELDS = frozenset(
    {
        "object_ref",
        "name",
        "lane",
        "callable_performer_refs",
    }
)
AGENT_OBJECT_RESOURCE_BLOCK_MARKER = "contain only provider-neutral references:"


def _load_objects(repo: Path) -> list[tuple[str, dict]]:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ValueError("agent resource resolution requires PyYAML") from exc
    objects_dir = repo / OBJECTS_DIR
    if not objects_dir.is_dir():
        raise ValueError(f"{OBJECTS_DIR} must exist")
    loaded: list[tuple[str, dict]] = []
    for path in sorted(objects_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path.relative_to(repo).as_posix()} must contain a mapping")
        loaded.append((path.relative_to(repo).as_posix(), data))
    if not loaded:
        raise ValueError(f"{OBJECTS_DIR} must contain at least one Agent Object")
    return loaded


def _casting_names_from_descriptors(casting_fields: object) -> frozenset[str]:
    names: list[str] = []
    for descriptor in casting_fields:  # type: ignore[union-attr]
        field_name = getattr(descriptor, "field_name", None)
        if not isinstance(field_name, str) or not field_name:
            raise ValueError("CASTING_FIELDS must carry non-empty text field_name values")
        names.append(field_name)
        if not callable(getattr(descriptor, "cli_emit", None)):
            raise ValueError(f"CASTING_FIELDS[{field_name}].cli_emit must be callable")
        scope = getattr(descriptor, "scope", None)
        if not isinstance(scope, frozenset):
            raise ValueError(f"CASTING_FIELDS[{field_name}].scope must be a frozenset")
    if len(set(names)) != len(names):
        raise ValueError("CASTING_FIELDS field_name values must be unique")
    return frozenset(names)


def _agent_object_resource_doc_fields(repo: Path) -> frozenset[str]:
    text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    marker_index = text.find(AGENT_OBJECT_RESOURCE_BLOCK_MARKER)
    if marker_index < 0:
        raise ValueError("AGENTS.md is missing the Agent Object provider-neutral references block")
    block_start = text.find("```text", marker_index)
    if block_start < 0:
        raise ValueError("AGENTS.md Agent Object references block is missing a text fence")
    block_start += len("```text")
    block_end = text.find("```", block_start)
    if block_end < 0:
        raise ValueError("AGENTS.md Agent Object references block fence is not closed")
    return frozenset(
        line.strip()
        for line in text[block_start:block_end].splitlines()
        if line.strip()
    )


def _optional_scalar_contract_fields(contract_type: object) -> frozenset[str]:
    return frozenset(
        field.name
        for field in fields(contract_type)  # type: ignore[arg-type]
        if field.default is not MISSING and field.default == ""
    )


def _allowlist_casting_fields(
    allowed_keys: frozenset[str],
    ref_fields: tuple[str, ...],
) -> frozenset[str]:
    return allowed_keys - AGENT_OBJECT_HEAD_FIELDS - frozenset(ref_fields)


def _casting_field_registry_violations(repo: Path) -> list[str]:
    from brick_protocol.support.connection import agent_resources
    from brick_protocol.support.connection.agent_adapter import (
        ALLOWED_ADAPTER_REFS,
        MODEL_PROVIDER_BY_ADAPTER,
        MODEL_REF_DEFAULT,
    )
    from brick_protocol.support.operator import primitives
    from brick_protocol.support.operator.contracts import AgentObjectContractData

    violations: list[str] = []
    casting_fields = primitives.CASTING_FIELDS
    try:
        casting_names = _casting_names_from_descriptors(casting_fields)
    except ValueError as exc:
        return [str(exc)]

    expected_descriptor_meta = {
        "preferred_adapter_ref": (None, frozenset(ALLOWED_ADAPTER_REFS)),
        "preferred_model_ref": (MODEL_REF_DEFAULT, frozenset(MODEL_PROVIDER_BY_ADAPTER)),
        "preferred_reasoning_effort_ref": ("effort:default", frozenset({"adapter:codex-local", "adapter:claude-local"})),
    }
    for descriptor in casting_fields:
        field_name = descriptor.field_name
        expected = expected_descriptor_meta.get(field_name)
        if expected is None:
            violations.append(f"CASTING_FIELDS carries unadmitted field: {field_name}")
            continue
        expected_default, expected_scope = expected
        if descriptor.default_ref != expected_default:
            violations.append(
                f"CASTING_FIELDS[{field_name}].default_ref drifted: "
                f"observed {descriptor.default_ref!r}, expected {expected_default!r}"
            )
        if descriptor.scope != expected_scope:
            violations.append(
                f"CASTING_FIELDS[{field_name}].scope drifted: "
                f"observed {sorted(descriptor.scope)!r}, expected {sorted(expected_scope)!r}"
            )

    comparisons = {
        "AgentObjectContractData optional scalar str fields": _optional_scalar_contract_fields(
            AgentObjectContractData
        ),
        "operator Agent Object allowlist casting fields": _allowlist_casting_fields(
            primitives._AGENT_OBJECT_ALLOWED_KEYS,
            primitives._AGENT_OBJECT_REF_FIELDS,
        ),
        "agent resource resolver allowlist casting fields": _allowlist_casting_fields(
            agent_resources._AGENT_OBJECT_KEYS,
            agent_resources._REF_FIELDS,
        ),
        "AGENTS.md Agent Object prose casting fields": (
            _agent_object_resource_doc_fields(repo)
            - AGENT_OBJECT_HEAD_FIELDS
            - frozenset(primitives._AGENT_OBJECT_REF_FIELDS)
        ),
    }
    for label, observed in comparisons.items():
        if observed != casting_names:
            violations.append(
                f"{label} drifted from CASTING_FIELDS: "
                f"observed {sorted(observed)!r}, expected {sorted(casting_names)!r}"
            )
    if tuple(agent_resources._REF_FIELDS) != tuple(primitives._AGENT_OBJECT_REF_FIELDS):
        violations.append(
            "Agent Object ref-field registries drifted: "
            f"agent_resources={tuple(agent_resources._REF_FIELDS)!r}, "
            f"operator={tuple(primitives._AGENT_OBJECT_REF_FIELDS)!r}"
        )
    return violations


def find_violations(repo: Path) -> tuple[list[str], int]:
    # Reuse the engine's resolver + admitted adapter set so the checker validates
    # exactly what the engine resolves and adapts to the current adapter vocabulary.
    from brick_protocol.support.connection.agent_resources import _resource_path
    from brick_protocol.support.connection.agent_adapter import ALLOWED_ADAPTER_REFS

    violations: list[str] = []
    refs_checked = 0
    violations.extend(_casting_field_registry_violations(repo))
    objects = _load_objects(repo)
    for rel, obj in objects:
        object_ref = obj.get("object_ref") or rel
        for field, prefix in FIELD_PREFIX.items():
            for ref in obj.get(field, []) or []:
                refs_checked += 1
                if not isinstance(ref, str) or not ref.strip():
                    violations.append(f"{object_ref}: {field} has a blank/non-text ref")
                    continue
                if not ref.startswith(prefix):
                    violations.append(
                        f"{object_ref}: {field} ref {ref!r} must use the {prefix!r} prefix"
                    )
                    continue
                try:
                    target = _resource_path(repo, ref)
                except Exception:  # noqa: BLE001 - unsupported ref prefix for a file field
                    violations.append(
                        f"{object_ref}: {field} ref {ref!r} is not a resolvable resource ref"
                    )
                    continue
                if not target.is_file():
                    violations.append(
                        f"{object_ref}: {field} ref {ref!r} resolves to "
                        f"{target.relative_to(repo).as_posix()} which does not exist"
                    )
        for ref in obj.get("adapter_refs", []) or []:
            refs_checked += 1
            if not isinstance(ref, str):
                violations.append(f"{object_ref}: adapter_ref {ref!r} is not text")
                continue
            if ref not in ALLOWED_ADAPTER_REFS:
                violations.append(
                    f"{object_ref}: adapter_ref {ref!r} is not in ALLOWED_ADAPTER_REFS "
                    f"({sorted(ALLOWED_ADAPTER_REFS)})"
                )
    return sorted(set(violations)), refs_checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: every file-backed resource ref an Agent "
            "Object declares resolves to an existing file, and every adapter ref "
            "is in the engine's ALLOWED_ADAPTER_REFS. Does not prove target "
            "content correctness, source truth, success, quality, or Movement "
            "authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    try:
        violations, refs_checked = find_violations(repo)
    except (OSError, ValueError) as exc:
        print(f"agent resource resolution rejected: {exc}")
        return 1

    if violations:
        print("agent resource resolution rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only that declared Agent Object "
            "resource refs resolve to an existing target; it does not prove the "
            "target content is correct, nor source truth, success, quality, or "
            "Movement authority."
        )
        return 1

    print(
        "agent resource resolution passed: "
        f"{refs_checked} declared Agent Object resource ref(s) resolve."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

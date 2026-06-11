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


def find_violations(repo: Path) -> tuple[list[str], int]:
    # Reuse the engine's resolver + admitted adapter set so the checker validates
    # exactly what the engine resolves and adapts to the current adapter vocabulary.
    from brick_protocol.support.connection.agent_resources import _resource_path
    from brick_protocol.support.connection.agent_adapter import ALLOWED_ADAPTER_REFS

    violations: list[str] = []
    refs_checked = 0
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

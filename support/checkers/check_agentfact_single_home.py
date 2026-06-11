#!/usr/bin/env python3
"""General invariant: AgentFact has a single home module.

The Agent contract projections (agent/receipt.yaml, agent/return_fact.yaml)
declare that a "second AgentFact home" is forbidden ownership — but nothing
enforced it (it was a declared-but-unenforced rule, retracted from the ghost
verifier list in CHECKER-CONSOLIDATION-0 part 1). This closes that gap: the
``AgentFact`` class must be defined in exactly one python module, agent/
return_fact.py, and nowhere else. One general invariant, not a per-file fixture.

Support evidence only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


SOURCE_DIRS = ("brick", "agent", "link", "support")
CANONICAL_HOME = "agent/return_fact.py"
_CLASS_DEF = re.compile(r"class\s+AgentFact\b")


def find_definitions(repo: Path) -> list[str]:
    """Top-level `class AgentFact` definitions across the python source tree."""
    hits: list[str] = []
    for base in SOURCE_DIRS:
        root = repo / base
        if not root.is_dir():
            continue
        for py in sorted(root.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            for line_no, raw in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                # top-level class only (no leading indent) — ignores doc snippets
                if raw and not raw[0].isspace() and _CLASS_DEF.match(raw):
                    hits.append(f"{py.relative_to(repo).as_posix()}:{line_no}")
    return hits


def find_violations(repo: Path) -> list[str]:
    hits = find_definitions(repo)
    homes = sorted({hit.rsplit(":", 1)[0] for hit in hits})
    if not hits:
        return [f"AgentFact class is not defined in any module under {SOURCE_DIRS}"]
    violations: list[str] = []
    if homes != [CANONICAL_HOME]:
        for home in homes:
            if home != CANONICAL_HOME:
                matches = ", ".join(h for h in hits if h.startswith(home + ":"))
                violations.append(
                    f"AgentFact defined outside its single home {CANONICAL_HOME}: {matches}"
                )
        if CANONICAL_HOME not in homes:
            violations.append(
                f"AgentFact is not defined in its canonical home {CANONICAL_HOME}"
            )
    elif len(hits) > 1:
        violations.append(
            f"AgentFact defined more than once in {CANONICAL_HOME}: {', '.join(hits)}"
        )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: AgentFact has a single home module "
            "(agent/return_fact.py). Does not prove correctness, source truth, "
            "success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    violations = find_violations(repo)
    if violations:
        print("AgentFact single-home rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only single-home class definition; "
            "it does not prove correctness, source truth, success, quality, or "
            "Movement authority."
        )
        return 1

    print(
        f"AgentFact single-home passed: defined once in {CANONICAL_HOME}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

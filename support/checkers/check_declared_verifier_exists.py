#!/usr/bin/env python3
"""Support-evidence checker: every declared axis-contract verifier file exists.

The Brick/Agent/Link contract projection YAMLs each declare a ``verifier:`` /
``verifiers:`` list naming the checker file(s) that guard the contract. A name
in that list whose file does NOT exist in ``support/checkers/`` is a pure
decoration: the contract claims a guarantee that nothing enforces. This is the
"declared-but-unenforced" drift class in its sharpest form.

This is a GENERAL invariant (one checker over every axis contract), not a
per-contract fixture. It is support evidence only: it proves a declared verifier
file is present, NOT that the verifier is correct, nor source truth, success,
quality, or Movement authority.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


AXIS_DIRS = ("brick", "agent", "link")
VERIFIER_KEYS = {"verifier", "verifiers"}
_CHECKER_ITEM = re.compile(r"(check_[a-z0-9_]+\.py)\Z")


def _axis_contract_files(repo: Path) -> list[Path]:
    """Top-level Brick/Agent/Link contract projection YAMLs (not subdirs)."""
    files: list[Path] = []
    for axis in AXIS_DIRS:
        axis_dir = repo / axis
        if axis_dir.is_dir():
            files.extend(sorted(axis_dir.glob("*.yaml")))
    return files


def declared_verifiers(path: Path) -> list[tuple[int, str]]:
    """Return (line_no, checker_filename) for every entry under a verifier(s): key.

    Minimal indent-scoped scan: find a ``verifier:`` / ``verifiers:`` key, then
    collect ``- check_*.py`` list items nested under it until the block dedents.
    """
    out: list[tuple[int, str]] = []
    block_indent: int | None = None
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # A non-list line at or left of the block key closes the block.
        if block_indent is not None and indent <= block_indent and not stripped.startswith("-"):
            block_indent = None

        if stripped.endswith(":") and stripped[:-1].strip() in VERIFIER_KEYS:
            block_indent = indent
            continue

        if block_indent is not None and indent > block_indent and stripped.startswith("-"):
            item = stripped[1:].strip()
            match = _CHECKER_ITEM.fullmatch(item)
            if match:
                out.append((line_no, match.group(1)))
    return out


def find_violations(repo: Path) -> tuple[list[str], int, int]:
    checker_dir = repo / "support" / "checkers"
    violations: list[str] = []
    declared = 0
    inspected = 0
    for path in _axis_contract_files(repo):
        entries = declared_verifiers(path)
        if entries:
            inspected += 1
        for line_no, name in entries:
            declared += 1
            if not (checker_dir / name).is_file():
                rel = path.relative_to(repo) if path.is_absolute() else path
                violations.append(
                    f"{rel}:{line_no}: declared verifier file does not exist: "
                    f"support/checkers/{name}"
                )
    return sorted(set(violations)), declared, inspected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: every axis-contract declared verifier "
            "file must exist. Does not prove verifier correctness, source truth, "
            "success, quality, or Movement authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    violations, declared, inspected = find_violations(repo)
    if violations:
        print("declared verifier existence rejected:")
        for violation in violations:
            print(f"- {violation}")
        print(
            "proof limit: this checker proves only that a declared verifier file "
            "is present; it does not prove the verifier is correct, nor source "
            "truth, success, quality, or Movement authority."
        )
        return 1

    print(
        "declared verifier existence passed: "
        f"every declared verifier exists ({declared} declaration(s) across "
        f"{inspected} axis contract(s))."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

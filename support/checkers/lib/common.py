"""Common support helpers for Brick Protocol checkers.

This module is support checker mechanics only. It does not own Brick / Agent /
Link meaning, source truth, success judgment, quality judgment, or Movement
authority.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class CheckError(ValueError):
    """Raised when a support checker rejects evidence."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, Mapping):
            raise CheckError(f"{path}: JSONL row must be an object")
        rows.append(value)
    return rows


def require_file(repo: Path, relative: str) -> str:
    path = repo / relative
    if not path.is_file():
        raise CheckError(f"required file missing: {relative}")
    return path.read_text(encoding="utf-8")


def require_dir(repo: Path, relative: str) -> Path:
    path = repo / relative
    if not path.is_dir():
        raise CheckError(f"required directory missing: {relative}")
    return path


def require_text(label: str, text: str, needles: Sequence[str]) -> None:
    for needle in needles:
        if needle not in text:
            raise CheckError(f"{label} missing required text: {needle!r}")


def reject_text(label: str, text: str, needles: Sequence[str]) -> None:
    for needle in needles:
        if needle in text:
            raise CheckError(f"{label} contains forbidden text: {needle!r}")


def require_building_evidence_files(root: Path, required_files: Sequence[str]) -> None:
    for relative in required_files:
        if not (root / relative).is_file():
            raise CheckError(f"Building root missing evidence file: {relative}")


def require_link_movements(root: Path, expected: Sequence[str]) -> None:
    rows = read_jsonl(root / "raw" / "link.jsonl")
    movements = [row.get("movement") for row in rows]
    if movements != list(expected):
        raise CheckError(f"unexpected Link movement sequence: {movements!r}")


def find_returned_mapping(
    root: Path,
    *,
    key: str,
    value: Any,
    extra_matches: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    rows = read_jsonl(root / "raw" / "agent-return.jsonl")
    for row in rows:
        returned = row.get("returned")
        if (
            isinstance(returned, Mapping)
            and returned.get(key) == value
            and all(
                returned.get(extra_key) == extra_value
                for extra_key, extra_value in (extra_matches or {}).items()
            )
        ):
            return returned
    extra = "" if not extra_matches else f" and {extra_matches!r}"
    raise CheckError(f"closure AgentFact with {key}={value!r}{extra} missing")


def require_non_empty_arrays(mapping: Mapping[str, Any], keys: Sequence[str]) -> None:
    for key in keys:
        if not isinstance(mapping.get(key), list) or not mapping[key]:
            raise CheckError(f"closure {key} must be a non-empty array")


def require_any_contains(items: Any, needle: str, label: str) -> None:
    if not isinstance(items, list):
        raise CheckError(f"{label} must be an array")
    if not any(needle in str(item) for item in items):
        raise CheckError(f"{label} must keep {needle!r}")


def print_rejection(message: str, proof_limit: str) -> int:
    import sys

    print(message, file=sys.stderr)
    print(proof_limit, file=sys.stderr)
    return 1

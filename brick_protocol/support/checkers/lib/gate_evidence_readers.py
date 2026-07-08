"""Gate evidence reader helpers for behavioral checker cases."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import ProfileError


def _assert_no_missing_gate_facts(root: Path, *, label: str) -> None:
    for path in _gate_evidence_paths(root):
        for record in _json_records(path):
            for trail, value in _nested_values_for_key(record, "missing_required_facts"):
                if isinstance(value, list) and value:
                    raise ProfileError(
                        f"preset_building_completion_case rejected {label}: "
                        f"{path.relative_to(root)} {'.'.join(trail)} has missing_required_facts"
                    )


def _assert_missing_gate_fact_present(
    root: Path,
    *,
    expected_missing_fact: str,
    label: str,
) -> None:
    """Assert the written gate evidence records EXACTLY the expected missing fact.

    Companion to _assert_no_missing_gate_facts for declared-HOLD cases: the
    walk paused because a declared review gate's disposition fact is absent,
    so that fact (and only facts naming it) must appear under
    missing_required_facts in the persisted gate evidence.
    """

    observed: set[str] = set()
    for path in _gate_evidence_paths(root):
        for record in _json_records(path):
            for _trail, value in _nested_values_for_key(record, "missing_required_facts"):
                if isinstance(value, list):
                    observed.update(str(item) for item in value)
    if expected_missing_fact not in observed:
        raise ProfileError(
            f"building_intake_seam_case rejected {label}: expected missing fact "
            f"{expected_missing_fact!r} not recorded; observed {sorted(observed)!r}"
        )
    unexpected = {item for item in observed if item != expected_missing_fact}
    if unexpected:
        raise ProfileError(
            f"building_intake_seam_case rejected {label}: hold recorded UNRELATED "
            f"missing facts {sorted(unexpected)!r} (expected only {expected_missing_fact!r})"
        )


def _gate_evidence_paths(root: Path) -> tuple[Path, ...]:
    paths = [root / "raw" / "link.jsonl"]
    paths.extend(sorted((root / "work" / "step-outputs").glob("*/step-output.json")))
    return tuple(path for path in paths if path.is_file())


def _json_records(path: Path) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    if path.suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, Mapping):
                records.append(value)
        return tuple(records)
    value = json.loads(path.read_text(encoding="utf-8"))
    return (value,) if isinstance(value, Mapping) else ()


def _nested_values_for_key(value: Any, key: str, trail: tuple[str, ...] = ()) -> tuple[tuple[tuple[str, ...], Any], ...]:
    found: list[tuple[tuple[str, ...], Any]] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            child_trail = (*trail, str(raw_key))
            if raw_key == key:
                found.append((child_trail, child))
            found.extend(_nested_values_for_key(child, key, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_nested_values_for_key(child, key, (*trail, str(index))))
    return tuple(found)

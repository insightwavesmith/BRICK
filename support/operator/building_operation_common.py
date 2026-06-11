"""Shared support primitives for the Building-operation collaborators (P3d).

Path/JSON/text helpers and shared default refs used by 2+ Building-operation
concern modules behind the building_operation facade. Support mechanics only:
it reads Link-owned gate refs, owns no crossing, chooses no Movement, and
judges no success or quality."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.link.gate import DECLARED_GATE_REFS as _DECLARED_GATE_REFS
from brick_protocol.support.recording.capture import DEFAULT_BUILDINGS_ROOT, REPO_ROOT


DEFAULT_LINK_GATE_REF = _DECLARED_GATE_REFS[0]


COMPACT_LINK_GATE_TOKENS: Mapping[str, str] = {
    "strict": _DECLARED_GATE_REFS[1],
    "human": _DECLARED_GATE_REFS[2],
    "coo": _DECLARED_GATE_REFS[3],
}


def _repo_path(repo: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return repo / path


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return str(path)


def _clean_text(label: str, value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    text = value.strip()
    if not text:
        raise ValueError(f"{label} must not be blank")
    return text


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _jsonl_records(path: Path) -> tuple[Mapping[str, Any], ...]:
    if not path.is_file():
        return ()
    records: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            records.append(payload)
    return tuple(records)


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _text_sequence(label: str, value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError(f"{label} must be a non-empty text array")
    return tuple(_clean_text(f"{label}[]", item) for item in value)


def _mapping_value(label: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value

"""Checker profile YAML-subset parser + shared validation primitives.

Lifted verbatim from check_profile.py (P3a behavior-preserving decomposition,
engine blueprint 0531 §5 / detail-design §D-4 Opt B). Support checker
mechanics only: it parses the flat profile YAML subset and offers the shared
ProfileError/KernelResult types and require_*/path helpers. It owns no axis
crossing, decides nothing, and is not source truth, success/quality judgment,
or Movement authority.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import io
import json
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProfileError(ValueError):
    """Raised when a profile or support check rejects evidence."""


@dataclass(frozen=True)
class KernelResult:
    check_id: str
    inspected: int
    output: str


def _ensure_import_identity(repo: Path) -> None:
    support_import_identity = str((repo / "brick_protocol" / "support" / "import_identity").resolve())
    if support_import_identity not in sys.path:
        sys.path.insert(0, support_import_identity)


def strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(line):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or line[index - 1].isspace():
                return line[:index]
    return line


def yaml_lines(text: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        without_comment = strip_comment(raw_line).rstrip()
        if not without_comment.strip():
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        if indent % 2:
            raise ProfileError(f"line {line_no}: indentation must use two-space steps")
        rows.append((indent, without_comment.lstrip(" ")))
    return rows


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return []
        return [parse_scalar(item.strip()) for item in body.split(",")]
    return value


def split_mapping_item(value: str, line_no: int) -> tuple[str, str | None]:
    # Real-YAML plain-key semantics: the key ends at the first ":" that is
    # followed by whitespace or end-of-line. A ":" glued to the next token is
    # part of the key (e.g. "building-step-template:design: 1" -> key
    # "building-step-template:design"), matching yaml.safe_load. The old
    # first-colon split mangled colon-bearing refs into duplicate truncated
    # keys whose blocks then silently overwrote each other (false-green).
    split_at = -1
    for index, char in enumerate(value):
        if char == ":" and (index + 1 == len(value) or value[index + 1] in " \t"):
            split_at = index
            break
    if split_at < 0:
        raise ProfileError(f"line {line_no}: expected key: value")
    key = value[:split_at].strip()
    if not key:
        raise ProfileError(f"line {line_no}: empty key")
    raw_value = value[split_at + 1 :].strip()
    return key, raw_value if raw_value else None


def looks_like_mapping_item(value: str) -> bool:
    if value.startswith(("'", '"')) or ":" not in value:
        return False
    key, _, after = value.partition(":")
    return bool(key.strip()) and (not after or after[0].isspace())


def parse_yaml_subset(text: str) -> Any:
    rows = yaml_lines(text)
    if not rows:
        return {}

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(rows):
            return {}, index
        current_indent, content = rows[index]
        if current_indent != indent:
            raise ProfileError(f"line {index + 1}: unexpected indentation")
        if content.startswith("- "):
            return parse_list(index, indent)
        return parse_map(index, indent)

    def parse_map(index: int, indent: int) -> tuple[dict[str, Any], int]:
        mapping: dict[str, Any] = {}
        while index < len(rows):
            current_indent, content = rows[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ProfileError(f"line {index + 1}: unexpected nested mapping")
            if content.startswith("- "):
                break
            key, raw_value = split_mapping_item(content, index + 1)
            if key in mapping:
                raise ProfileError(
                    f"line {index + 1}: duplicate mapping key {key!r}; the yaml "
                    "subset hard-rejects duplicate same-key blocks instead of "
                    "silently dropping one (false-green vector)"
                )
            if raw_value is None:
                if index + 1 >= len(rows) or rows[index + 1][0] <= indent:
                    mapping[key] = {}
                    index += 1
                else:
                    mapping[key], index = parse_block(index + 1, rows[index + 1][0])
            else:
                mapping[key] = parse_scalar(raw_value)
                index += 1
        return mapping, index

    def parse_list(index: int, indent: int) -> tuple[list[Any], int]:
        values: list[Any] = []
        while index < len(rows):
            current_indent, content = rows[index]
            if current_indent < indent:
                break
            if current_indent != indent or not content.startswith("- "):
                break
            item = content[2:].strip()
            if not item:
                if index + 1 >= len(rows) or rows[index + 1][0] <= indent:
                    values.append(None)
                    index += 1
                else:
                    child, index = parse_block(index + 1, rows[index + 1][0])
                    values.append(child)
            elif looks_like_mapping_item(item):
                key, raw_value = split_mapping_item(item, index + 1)
                item_map: dict[str, Any] = {}
                if raw_value is None:
                    if index + 1 < len(rows) and rows[index + 1][0] > indent:
                        item_map[key], index = parse_block(index + 1, rows[index + 1][0])
                    else:
                        item_map[key] = {}
                        index += 1
                else:
                    item_map[key] = parse_scalar(raw_value)
                    index += 1
                if index < len(rows) and rows[index][0] > indent:
                    extra, index = parse_map(index, rows[index][0])
                    overlap = sorted(set(extra) & set(item_map))
                    if overlap:
                        raise ProfileError(
                            f"line {index + 1}: duplicate mapping key(s) {overlap} "
                            "in list item; the yaml subset hard-rejects duplicate "
                            "same-key blocks instead of silently dropping one "
                            "(false-green vector)"
                        )
                    item_map.update(extra)
                values.append(item_map)
            else:
                values.append(parse_scalar(item))
                index += 1
        return values, index

    parsed, next_index = parse_block(0, rows[0][0])
    if next_index != len(rows):
        raise ProfileError(f"line {next_index + 1}: unparsed profile content")
    return parsed


def require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProfileError(f"{label} must be a mapping")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{label} must be a non-empty string")
    return value.strip()


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ProfileError(f"{label} must be a list of strings")
    return [item.strip() for item in value]


def to_repo_path(repo: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ProfileError("profile path must be a non-empty string")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ProfileError(f"profile path escapes repo: {relative}")
    return repo / candidate


def to_posix(path: Path) -> str:
    return path.as_posix().lstrip("./")


def rule_items(profile: Mapping[str, Any], key: str) -> list[Any]:
    value = profile.get(key, [])
    return value if isinstance(value, list) else []


def extract_path(value: Any, dotted_path: str) -> list[Any]:
    values = [value]
    for token in dotted_path.split("."):
        next_values: list[Any] = []
        if token.endswith("[]"):
            key = token[:-2]
            for current in values:
                if isinstance(current, Mapping) and isinstance(current.get(key), list):
                    next_values.extend(current[key])
        else:
            for current in values:
                if isinstance(current, Mapping) and token in current:
                    next_values.append(current[token])
        values = next_values
    return values


def json_path_exists(value: Any, dotted_path: str) -> bool:
    return bool(extract_path(value, dotted_path))


def _profile_case_document(repo: Path, mapping: Mapping[str, Any], label: str) -> tuple[Mapping[str, Any], str]:
    if "path" in mapping:
        relative = require_string(mapping.get("path"), f"{label}.path")
        return load_yaml_subset_file(repo, relative), relative
    document = require_mapping(mapping.get("document", mapping.get("case")), f"{label}.document")
    case_label = require_string(mapping.get("label", f"{label}:inline"), f"{label}.label")
    return document, case_label


def load_yaml_subset_file(repo: Path, relative: str) -> Mapping[str, Any]:
    path = to_repo_path(repo, relative)
    return require_mapping(parse_yaml_subset(path.read_text(encoding="utf-8")), relative)

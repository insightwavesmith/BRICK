#!/usr/bin/env python3
"""Pre-launch task-order lint for declared Brick work statements.

Support evidence only: this module reports narrow L1-L4 preflight findings for
caller-supplied order text. It does not compose a Building, choose Movement,
judge success/quality, or wire itself into launch/runtime paths.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


WORK_KINDS = {"work", "development"}
DONE_MARKER_RE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?(?:done(?:\s+criteria)?|DONE(?:\s+Criteria)?|"
    r"종료선|완료선)\s*(?::|\b)"
)
DELIVERABLES_HEADING_RE = re.compile(r"(?im)^\s*#{1,6}\s*Deliverables\b")
DELIVERABLE_ITEM_RE = re.compile(r"(?im)^\s*D\d+\s*[:.]")
PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_`./-])((?:brick|agent|link|support|project)/[-A-Za-z0-9_./*?{}\[\]]+)"
)
REF_COERCION_PATTERNS = (
    re.compile(r"(?is)\breason_refs\b.{0,120}\bfile:line\b"),
    re.compile(r"(?is)\bfile:line\b.{0,120}\breason_refs\b"),
    re.compile(r"(?is)\breason_refs\b.{0,120}파일\s*:\s*줄"),
    re.compile(r"(?is)(?<![A-Za-z0-9_])file:line(?![A-Za-z0-9_])[^\n]{0,80}(?:만\s*반환|(?:return|emit|provide)\s+only|only\s+(?:return|emit|provide))"),
    re.compile(r"(?is)\brelated_boundary_refs\b.{0,160}\bbrick:(?!//)"),
    re.compile(r"(?is)\brelated_boundary_refs\b.{0,160}\bbrick-instance:"),
    re.compile(r"(?is)\brelated_boundary_refs\b.{0,160}\bbrick-boundary:"),
)
READ_FORBIDDEN_PROOF_PATTERNS = (
    re.compile(r"(?i)\bgit\s+commit\b"),
    re.compile(r"(?i)\bgit\s+push\b"),
    re.compile(r"(?i)\b(?:edit|modify|write|delete|create|mutate)\s+(?:source|file|repo|repository)\b"),
    re.compile(r"(?i)(?:소스|파일|저장소).{0,20}(?:수정|삭제|생성|작성)"),
    re.compile(r"(?<!\S)--all(?!\S)"),
)


@dataclass(frozen=True)
class TaskNode:
    label: str
    kind: str | None
    capability_class: str | None
    work_statement: str
    proof_text: str
    write_scope: tuple[str, ...] = field(default_factory=tuple)


def _frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return {}, text
    try:
        import yaml  # type: ignore[import-not-found]

        data = yaml.safe_load(parts[0][len("---") :]) or {}
    except Exception:
        return {}, text
    body = parts[1]
    if body.startswith("\n"):
        body = body[1:]
    return data if isinstance(data, dict) else {}, body


def _load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    fm, body = _frontmatter(text)
    stripped = body.strip()
    data: Any = None
    if stripped:
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            try:
                import yaml  # type: ignore[import-not-found]

                data = yaml.safe_load(stripped)
            except Exception:
                data = None
    if isinstance(data, dict):
        merged = dict(fm)
        merged.update(data)
        return merged
    if fm:
        return fm
    return {"work_statement": body}


def _brick_kind_from_ref(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"brick/templates/bricks/([^/]+)/brick\.md$", value)
    if match:
        return match.group(1)
    if value.startswith("building-step-template:"):
        return value.rsplit(":", 1)[1]
    return None


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(_as_text(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_as_text(item)}" for key, item in value.items())
    return str(value)


def _allowed_paths(scope: Any) -> tuple[str, ...]:
    if isinstance(scope, dict):
        raw = scope.get("allowed_paths") or scope.get("allow") or scope.get("paths")
    else:
        raw = scope
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list):
        return tuple(item for item in raw if isinstance(item, str) and item.strip())
    return ()


def _iter_dict_nodes(data: Any) -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(data, dict):
        if any(key in data for key in ("work_statement", "proof_obligations", "brick_kind", "kind")):
            yield str(data.get("id") or data.get("ref") or data.get("name") or "task-order"), data
        for key in ("nodes", "steps", "bricks"):
            entries = data.get(key)
            if isinstance(entries, dict):
                for label, value in entries.items():
                    if isinstance(value, dict):
                        yield str(label), value
            elif isinstance(entries, list):
                for index, value in enumerate(entries, start=1):
                    if isinstance(value, dict):
                        yield str(value.get("id") or value.get("ref") or f"{key}[{index}]"), value


def _capability_map(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in (repo / "brick/templates/bricks").glob("*/brick.md"):
        fm, _body = _frontmatter(path.read_text(encoding="utf-8"))
        kind = path.parent.name
        capability = fm.get("capability_class")
        if isinstance(capability, str) and capability.strip():
            result[kind] = capability.strip()
    return result


def _nodes_from_document(data: Any, *, repo: Path) -> list[TaskNode]:
    capabilities = _capability_map(repo)
    root_scope = _allowed_paths(data.get("write_scope")) if isinstance(data, dict) else ()
    nodes: list[TaskNode] = []
    for label, raw in _iter_dict_nodes(data):
        kind = (
            raw.get("kind")
            or raw.get("brick_kind")
            or _brick_kind_from_ref(raw.get("brick_spec_ref"))
            or _brick_kind_from_ref(raw.get("step_template_ref"))
        )
        kind_text = kind.strip() if isinstance(kind, str) and kind.strip() else None
        work_statement = _as_text(raw.get("work_statement"))
        proof_text = "\n".join(
            part
            for part in (
                _as_text(raw.get("proof_obligations")),
                _as_text(raw.get("proof_required")),
                _proof_section(work_statement),
            )
            if part.strip()
        )
        nodes.append(
            TaskNode(
                label=label,
                kind=kind_text,
                capability_class=capabilities.get(kind_text or ""),
                work_statement=work_statement,
                proof_text=proof_text,
                write_scope=_allowed_paths(raw.get("write_scope")) or root_scope,
            )
        )
    if not nodes and isinstance(data, dict):
        work_statement = _as_text(data.get("work_statement"))
        if work_statement.strip():
            kind = data.get("kind") or data.get("brick_kind")
            kind_text = kind.strip() if isinstance(kind, str) and kind.strip() else None
            nodes.append(
                TaskNode(
                    label="task-order",
                    kind=kind_text,
                    capability_class=capabilities.get(kind_text or ""),
                    work_statement=work_statement,
                    proof_text=_as_text(data.get("proof_obligations")) or _proof_section(work_statement),
                    write_scope=root_scope,
                )
            )
    return nodes


def _proof_section(text: str) -> str:
    match = re.search(r"(?ims)^\s*#{1,6}\s*Proof(?:\s+required)?\b(.*?)(?=^\s*#{1,6}\s+|\Z)", text)
    if match:
        return match.group(1)
    return ""


def _deliverables_section(text: str) -> str:
    match = re.search(r"(?ims)^\s*#{1,6}\s*Deliverables\b(.*?)(?=^\s*#{1,6}\s+|\Z)", text)
    if match:
        return match.group(1)
    return ""


def _literal_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for match in PATH_TOKEN_RE.finditer(text):
        token = match.group(1).strip("`'\"),.;:")
        if token and not token.endswith("/"):
            paths.add(token)
    return paths


def _covered(path: str, patterns: Iterable[str]) -> bool:
    clean_path = _normalized_write_path(path)
    for pattern in patterns:
        clean_pattern = _normalized_write_path(pattern)
        if clean_pattern in {".", "**", "./**"}:
            return True
        if clean_path == clean_pattern:
            return True
        if clean_pattern.endswith("/**"):
            directory = clean_pattern[:-3].rstrip("/")
            if clean_path == directory or clean_path.startswith(directory + "/"):
                return True
    return False


def _normalized_write_path(path: str) -> str:
    text = str(path).strip().replace("\\", "/")
    if text.startswith("/"):
        raise ValueError("write_scope paths must be repo-relative")
    while text.startswith("./"):
        text = text[2:]
    parts = tuple(part for part in text.rstrip("/").split("/") if part and part != ".")
    if any(part == ".." for part in parts):
        raise ValueError("write_scope paths must not escape the repo root")
    return "/".join(parts) or "."


def lint_nodes(nodes: Iterable[TaskNode]) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    warnings: list[str] = []
    for node in nodes:
        label = node.label
        work_statement = node.work_statement
        normalized_write_scope: list[str] = []
        for scope in node.write_scope:
            try:
                normalized_write_scope.append(_normalized_write_path(scope))
            except ValueError as exc:
                violations.append(f"{label}: L4 invalid write_scope {scope!r}: {exc}")
        if node.kind in WORK_KINDS and work_statement.strip():
            if not DONE_MARKER_RE.search(work_statement):
                violations.append(f"{label}: L1 missing termination marker in {node.kind} work_statement")
            if not DELIVERABLES_HEADING_RE.search(work_statement) or not DELIVERABLE_ITEM_RE.search(work_statement):
                violations.append(f"{label}: L4 missing numbered Deliverables block")
            for pattern in REF_COERCION_PATTERNS:
                if pattern.search(work_statement):
                    violations.append(f"{label}: L3 work_statement coerces closed ref fields toward forbidden forms")
                    break
            deliverables_text = _deliverables_section(work_statement)
            deliverable_paths = _literal_paths(deliverables_text)
            if deliverable_paths or node.write_scope:
                for path in sorted(deliverable_paths):
                    if not _covered(path, normalized_write_scope):
                        violations.append(f"{label}: L4 deliverable path {path} is not covered by write_scope")
                for scope in sorted(normalized_write_scope):
                    if scope.endswith("/"):
                        warnings.append(f"{label}: L4 write_scope {scope} is directory-form; prefer explicit glob")
                        continue
                    if not any(ch in scope for ch in "*?[]"):
                        if not any(path == scope or path.startswith(scope.rstrip("/") + "/") for path in deliverable_paths):
                            warnings.append(f"{label}: L4 write_scope {scope} has no literal Deliverables path")
                    elif deliverable_paths and not any(_covered(path, (scope,)) for path in deliverable_paths):
                        warnings.append(f"{label}: L4 write_scope {scope} covers no literal Deliverables path")
        if node.capability_class == "read" and node.proof_text.strip():
            for pattern in READ_FORBIDDEN_PROOF_PATTERNS:
                match = pattern.search(node.proof_text)
                if match:
                    violations.append(
                        f"{label}: L2 read-capability proof contains forbidden mutation/full-rerun token {match.group(0)!r}"
                    )
                    break
    return sorted(set(violations)), sorted(set(warnings))


def lint_file(path: Path, *, repo: Path) -> tuple[list[str], list[str], int]:
    data = _load_document(path)
    nodes = _nodes_from_document(data, repo=repo)
    violations, warnings = lint_nodes(nodes)
    return violations, warnings, len(nodes)


def _write_fixture(root: Path, name: str, data: dict[str, Any]) -> Path:
    path = root / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _self_test(repo: Path) -> tuple[int, tuple[str, ...]]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        base = {
            "kind": "work",
            "write_scope": {"allowed_paths": ["support/operator/task_order_preflight.py"]},
        }
        dirty_missing_done = _write_fixture(
            root,
            "missing-done.json",
            {
                **base,
                "work_statement": "## Deliverables\nD1: edit support/operator/task_order_preflight.py\n",
            },
        )
        dirty_read_proof = _write_fixture(
            root,
            "read-proof.json",
            {
                "kind": "development",
                "work_statement": "## Deliverables\nD1: inspect support/operator/task_order_preflight.py\n## Done Criteria\nobserved",
                "proof_obligations": "uv run python support/checkers/check_profile.py --all",
                "write_scope": {"allowed_paths": ["support/operator/task_order_preflight.py"]},
            },
        )
        dirty_ref = _write_fixture(
            root,
            "ref-coercion.json",
            {
                **base,
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator/task_order_preflight.py\n"
                    "## Done Criteria\nobserved\nreason_refs must return file:line only"
                ),
            },
        )
        dirty_file_line_only = _write_fixture(
            root,
            "file-line-only-coercion.json",
            {
                **base,
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator/task_order_preflight.py\n"
                    "## Done Criteria\nobserved\n근거 file:line만 반환"
                ),
            },
        )
        dirty_scope_mismatch = _write_fixture(
            root,
            "scope-mismatch.json",
            {
                **base,
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator/not_declared.py\n"
                    "## Done Criteria\nobserved"
                ),
            },
        )
        dirty_scope_prefix = _write_fixture(
            root,
            "scope-prefix.json",
            {
                **base,
                "write_scope": {"allowed_paths": ["support/operator/**"]},
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator_extra.py\n"
                    "## Done Criteria\nobserved"
                ),
            },
        )
        dirty_scope_star = _write_fixture(
            root,
            "unsupported-glob-star.json",
            {
                **base,
                "write_scope": {"allowed_paths": ["support/operator/*.py"]},
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator/new_thing.py\n"
                    "## Done Criteria\nobserved"
                ),
            },
        )
        dirty_scope_question = _write_fixture(
            root,
            "unsupported-glob-question.json",
            {
                **base,
                "write_scope": {"allowed_paths": ["support/operator/a?c.py"]},
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator/abc.py\n"
                    "## Done Criteria\nobserved"
                ),
            },
        )
        dirty_scope_char_class = _write_fixture(
            root,
            "unsupported-glob-char-class.json",
            {
                **base,
                "write_scope": {"allowed_paths": ["support/operator/[ab]bc.py"]},
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator/abc.py\n"
                    "## Done Criteria\nobserved"
                ),
            },
        )
        dirty_scope_absolute = _write_fixture(
            root,
            "absolute-write-scope.json",
            {
                **base,
                "write_scope": {"allowed_paths": ["/etc/shadow"]},
                "work_statement": "## Deliverables\nD1: update checklist text\n## Done Criteria\nobserved",
            },
        )
        dirty_scope_escape = _write_fixture(
            root,
            "escaping-write-scope.json",
            {
                **base,
                "write_scope": {"allowed_paths": ["../../../etc/passwd"]},
                "work_statement": "## Deliverables\nD1: update checklist text\n## Done Criteria\nobserved",
            },
        )
        clean = _write_fixture(
            root,
            "clean.json",
            {
                **base,
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator/task_order_preflight.py\n"
                    "## Done Criteria\nobserved"
                ),
            },
        )
        clean_observed_evidence_guidance = _write_fixture(
            root,
            "clean-observed-evidence-guidance.json",
            {
                **base,
                "work_statement": (
                    "## Deliverables\nD1: edit support/operator/task_order_preflight.py\n"
                    "## Done Criteria\nobserved\nfile:line 인용은 observed_evidence에 기록"
                ),
            },
        )
        results: list[str] = []
        for path in (
            dirty_missing_done,
            dirty_read_proof,
            dirty_ref,
            dirty_file_line_only,
            dirty_scope_mismatch,
            dirty_scope_prefix,
            dirty_scope_star,
            dirty_scope_question,
            dirty_scope_char_class,
            dirty_scope_absolute,
            dirty_scope_escape,
        ):
            violations, _warnings, _count = lint_file(path, repo=repo)
            if not violations:
                raise ValueError(f"self-test fixture did not reject {path.name}")
            results.append(f"{path.name}: rejected")
        violations, _warnings, _count = lint_file(clean, repo=repo)
        if violations:
            raise ValueError(f"self-test clean fixture rejected: {violations}")
        results.append("clean.json: passed")
        violations, _warnings, _count = lint_file(clean_observed_evidence_guidance, repo=repo)
        if violations:
            raise ValueError(f"self-test clean observed-evidence guidance rejected: {violations}")
        results.append("clean-observed-evidence-guidance.json: passed")
    return 11, tuple(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support preflight lint for task orders. Reports L1-L4 violations; "
            "does not prove source truth, success, quality, or Movement."
        )
    )
    parser.add_argument("targets", nargs="*", help="Task-order files to inspect.")
    parser.add_argument("--repo", default=".", help="Repository root.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in dirty/clean fixtures.")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()

    try:
        if args.self_test:
            count, results = _self_test(repo)
            print(f"task order preflight self-test passed: {count} dirty fixture(s) rejected.")
            print("- fixtures: " + ", ".join(results))
        total_nodes = 0
        all_violations: list[str] = []
        all_warnings: list[str] = []
        for target in args.targets:
            violations, warnings, node_count = lint_file(Path(target), repo=repo)
            total_nodes += node_count
            all_violations.extend(f"{target}: {item}" for item in violations)
            all_warnings.extend(f"{target}: {item}" for item in warnings)
    except (OSError, ValueError) as exc:
        print(f"task order preflight rejected: {exc}")
        return 1

    if all_violations:
        print("task order preflight rejected:")
        for violation in all_violations:
            print(f"- {violation}")
        for warning in all_warnings:
            print(f"- warning: {warning}")
        print("proof limit: support evidence only; no success, quality, source-truth, or Movement authority.")
        return 1

    if args.targets:
        print(f"task order preflight passed: {total_nodes} node(s) inspected.")
        for warning in all_warnings:
            print(f"- warning: {warning}")
    elif not args.self_test:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

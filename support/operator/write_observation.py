"""Write-scope observation for effective-write adapter results.

This support helper observes file/git changes and validates them against the
Brick-declared write scope. It does not judge success, quality, or Movement.
"""

from __future__ import annotations

import fnmatch
import hashlib
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.connection.agent_adapter import (
    AgentAdapterRequest,
    AgentAdapterResult,
    _mark_effective_write_observation_path,
    agent_request_effective_write,
)
from brick_protocol.support.operator.primitives import (
    _REPO_ROOT,
    _WRITE_OBSERVATION_DEFAULT_EXCLUDED_DIR_NAMES,
    _WRITE_OBSERVATION_DEFAULT_EXCLUDED_FILE_NAMES,
    _WRITE_OBSERVATION_DEFAULT_EXCLUDED_SUFFIXES,
    _mapping,
    _merge_texts,
)

def _write_scope_from_brick_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    value = row.get("write_scope")
    if value is None:
        return {}
    return _mapping("Brick row write_scope", value)

def _write_adapter_observation_before(
    request: AgentAdapterRequest,
    *,
    adapter_cwd: Path | str | None,
) -> Mapping[str, Any] | None:
    if not agent_request_effective_write(request):
        return None
    cwd = _adapter_cwd_path(adapter_cwd)
    before = {
        "cwd": str(cwd),
        "before_snapshot": _observed_file_snapshot(cwd),
        "before_git_status_paths": _observed_worktree_paths(cwd),
        "before_git_refs": _observed_git_refs(cwd),
    }
    _mark_effective_write_observation_path(request, cwd)
    return before

def _adapter_result_with_write_observation(
    adapter_result: AgentAdapterResult,
    before: Mapping[str, Any] | None,
    *,
    adapter_cwd: Path | str | None,
) -> AgentAdapterResult:
    if before is None:
        if agent_request_effective_write(adapter_result.request):
            raise ValueError("effective write requires write observation before snapshot")
        return adapter_result
    cwd = _adapter_cwd_path(adapter_cwd)
    before_snapshot = {
        str(path): str(digest)
        for path, digest in _mapping("write_observation.before_snapshot", before.get("before_snapshot")).items()
    }
    after_snapshot = _observed_file_snapshot(cwd)
    before_git_status_paths = tuple(
        str(path) for path in before.get("before_git_status_paths", ()) if isinstance(path, str)
    )
    before_git_refs = {
        str(key): str(value)
        for key, value in _mapping("write_observation.before_git_refs", before.get("before_git_refs")).items()
    }
    after_git_status_paths = _observed_worktree_paths(cwd)
    after_git_refs = _observed_git_refs(cwd)
    _validate_git_refs_unchanged(before_git_refs, after_git_refs)
    changed_files = _changed_snapshot_paths(before_snapshot, after_snapshot)
    _validate_observed_write_paths(changed_files, adapter_result.request.write_scope)
    returned_value = adapter_result.returned_value
    if isinstance(returned_value, Mapping):
        returned_mapping = dict(returned_value)
    else:
        returned_mapping = {"returned_excerpt": str(returned_value)}
    returned_mapping["changed_files"] = list(changed_files)
    returned_mapping["worktree_observation"] = {
        "before_path_count": len(before_snapshot),
        "after_path_count": len(after_snapshot),
        "before_git_status_paths": list(before_git_status_paths),
        "after_git_status_paths": list(after_git_status_paths),
        "before_git_refs": dict(before_git_refs),
        "after_git_refs": dict(after_git_refs),
        "observed_changed_files": list(changed_files),
        "write_scope": dict(adapter_result.request.write_scope),
        "proof_limits": [
            "changed files are support evidence only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness of file edits",
            "complete diff attribution for pre-existing dirty paths",
        ],
    }
    return AgentAdapterResult(
        request=adapter_result.request,
        returned_value=returned_mapping,
        proof_limits=_merge_texts(
            adapter_result.proof_limits,
            "write observation support evidence only",
        ),
        not_proven=_merge_texts(
            adapter_result.not_proven,
            "semantic correctness of file edits",
        ),
    )

def _adapter_cwd_path(adapter_cwd: Path | str | None) -> Path:
    return Path(adapter_cwd) if adapter_cwd is not None else _REPO_ROOT

def _observed_worktree_paths(cwd: Path) -> tuple[str, ...]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), "status", "--short", "--untracked-files=all"],
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode != 0:
        return ()
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        path = _git_status_path(line)
        if path:
            paths.append(path)
    return tuple(sorted(dict.fromkeys(paths)))

def _observed_git_refs(cwd: Path) -> Mapping[str, str]:
    refs: dict[str, str] = {}
    for key, args in (
        ("head", ("rev-parse", "HEAD")),
        ("branch", ("rev-parse", "--abbrev-ref", "HEAD")),
        ("upstream", ("rev-parse", "--verify", "@{u}")),
    ):
        value = _git_output(cwd, args)
        if value:
            refs[key] = value
    return refs

def _git_output(cwd: Path, args: tuple[str, ...]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()

def _validate_git_refs_unchanged(
    before_refs: Mapping[str, str],
    after_refs: Mapping[str, str],
) -> None:
    if dict(before_refs) != dict(after_refs):
        raise ValueError("effective write observed forbidden git ref movement")

def _git_status_path(line: str) -> str:
    if len(line) < 4:
        return ""
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path.replace("\\", "/")

def _observed_file_snapshot(cwd: Path) -> Mapping[str, str]:
    if not cwd.exists():
        return {}
    snapshot: dict[str, str] = {}
    for path in _observable_files(cwd):
        rel = path.relative_to(cwd).as_posix()
        digest = _file_digest(path)
        if digest:
            snapshot[rel] = digest
    return snapshot

def _observable_files(cwd: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in cwd.rglob("*"):
        relative = path.relative_to(cwd)
        if ".git" in relative.parts:
            continue
        if _is_write_observation_default_excluded_residue(relative):
            continue
        if path.is_file():
            files.append(path)
    return tuple(sorted(files, key=lambda item: item.relative_to(cwd).as_posix()))

def _is_write_observation_default_excluded_residue(relative_path: Path) -> bool:
    parts = relative_path.parts
    return (
        any(part in _WRITE_OBSERVATION_DEFAULT_EXCLUDED_DIR_NAMES for part in parts)
        or relative_path.name in _WRITE_OBSERVATION_DEFAULT_EXCLUDED_FILE_NAMES
        or relative_path.suffix in _WRITE_OBSERVATION_DEFAULT_EXCLUDED_SUFFIXES
    )

def _is_write_observation_cache_residue(relative_path: Path) -> bool:
    return _is_write_observation_default_excluded_residue(relative_path)

def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()

def _changed_snapshot_paths(
    before_snapshot: Mapping[str, str],
    after_snapshot: Mapping[str, str],
) -> tuple[str, ...]:
    before_keys = set(before_snapshot)
    after_keys = set(after_snapshot)
    changed = before_keys.symmetric_difference(after_keys)
    changed.update(
        path
        for path in before_keys & after_keys
        if before_snapshot[path] != after_snapshot[path]
    )
    return tuple(sorted(changed))

def _validate_observed_write_paths(
    changed_files: Iterable[str],
    write_scope: Mapping[str, Any],
) -> None:
    if "forbidden_paths" not in write_scope:
        raise ValueError("effective write observation requires write_scope.forbidden_paths")
    raw_forbidden = write_scope.get("forbidden_paths")
    if not isinstance(raw_forbidden, list):
        raise TypeError("write_scope.forbidden_paths must be a list")
    allowed = tuple(
        str(item).replace("\\", "/")
        for item in write_scope.get("allowed_paths", ())
        if isinstance(item, str) and item.strip()
    )
    forbidden = tuple(
        str(item).replace("\\", "/")
        for item in raw_forbidden
        if isinstance(item, str) and item.strip()
    )
    if not allowed:
        raise ValueError("effective write observation requires write_scope.allowed_paths")
    for path in changed_files:
        _validate_observed_write_path(path, allowed, forbidden)

def _validate_observed_write_path(
    path: str,
    allowed: tuple[str, ...],
    forbidden: tuple[str, ...],
) -> None:
    clean = path.strip().replace("\\", "/")
    lowered = clean.lower()
    if (
        lowered == ".git"
        or lowered.startswith(".git/")
        or lowered.endswith((".pem", ".key"))
        or _path_has_forbidden_write_segment(lowered)
        or lowered == ".env"
        or lowered.startswith(".env/")
    ):
        raise ValueError(f"effective write observed forbidden path: {clean}")
    if any(_path_matches_scope(clean, pattern) for pattern in forbidden):
        raise ValueError(f"effective write observed forbidden path: {clean}")
    if not any(_path_matches_scope(clean, pattern) for pattern in allowed):
        raise ValueError(f"write_observation_out_of_scope: effective write observed path outside write_scope: {clean}")

def _path_has_forbidden_write_segment(path: str) -> bool:
    segments = [
        segment
        for segment in path.replace("\\", "/").replace(".", "/").replace("-", "/").replace("_", "/").split("/")
        if segment
    ]
    for segment in segments:
        if segment in {"auth", "credential", "credentials", "secret", "secrets", "token", "tokens"}:
            return True
    return False

def _path_matches_scope(path: str, pattern: str) -> bool:
    """Match exact paths or explicit globs; directory-looking entries do not include children."""

    clean_pattern = pattern.strip().replace("\\", "/")
    if not clean_pattern:
        return False
    return fnmatch.fnmatch(path, clean_pattern) or path == clean_pattern.rstrip("/")

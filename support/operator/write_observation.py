"""Write-scope observation for effective-write adapter results.

This support helper observes file/git changes and validates them against the
Brick-declared write scope. It does not judge success, quality, or Movement.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope
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
from brick_protocol.support.recording.agent_step_observation import (
    derive_adapter_raw_observation_facts,
    derive_git_refs_moved,
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
    changed_files = _changed_snapshot_paths(before_snapshot, after_snapshot)

    # RAW worktree observation only (REDO Smith 0623): the support write observer
    # produces "what changed + before/after git refs" and the RAW structural
    # sensitive-path flags. It RAISES NOTHING -- support is carry + record only; the
    # disposable worktree is the integrity boundary. It does NOT classify changed
    # paths against the recommended scope, does NOT derive the write-policy reason
    # tokens, and does NOT record the git-ref delta -- those are the Brick axis
    # (brick.comparison) and support/recording (agent_step_observation).
    observed_sensitive_path_writes = _raw_sensitive_path_writes(changed_files)

    # COMPARE (Brick axis 정보가공): classify the RAW changed paths against the
    # Brick-recommended write_scope.
    write_scope_comparison_facts = compare_changed_paths_to_write_scope(
        changed_files, adapter_result.request.write_scope
    )

    # RECORD (support/recording): derive the named per-step facts from the RAW
    # observations (git-ref delta, adapter raw side-channel) -- the support write
    # observer no longer assembles these itself.
    git_refs_moved = derive_git_refs_moved(before_git_refs, after_git_refs)
    adapter_raw_facts = derive_adapter_raw_observation_facts(
        adapter_result.adapter_raw_observations
    )

    returned_value = adapter_result.returned_value
    if isinstance(returned_value, Mapping):
        returned_mapping = dict(returned_value)
    else:
        returned_mapping = {"returned_excerpt": str(returned_value)}
    returned_mapping["changed_files"] = list(changed_files)
    worktree_observation: dict[str, Any] = {
        "before_path_count": len(before_snapshot),
        "after_path_count": len(after_snapshot),
        "before_git_status_paths": list(before_git_status_paths),
        "after_git_status_paths": list(after_git_status_paths),
        "before_git_refs": dict(before_git_refs),
        "after_git_refs": dict(after_git_refs),
        "observed_changed_files": list(changed_files),
        "write_scope": dict(adapter_result.request.write_scope),
        # RAW structural sensitive-path observation (no scope knowledge); the
        # building is not stopped on it (worktree is disposable; secret read/egress
        # stays hard elsewhere -- adapter_validation). support RAISES NOTHING here.
        # Brick-comparison + support/recording facts land here as NESTED evidence for
        # the merge-review gate; no policy disposition stops the building.
        "git_refs_moved": dict(git_refs_moved),
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
    if observed_sensitive_path_writes:
        worktree_observation["observed_sensitive_path_writes"] = list(
            observed_sensitive_path_writes
        )
    for key, value in write_scope_comparison_facts.items():
        worktree_observation[key] = list(value)
    for key, value in adapter_raw_facts.items():
        worktree_observation[key] = list(value)
    returned_mapping["worktree_observation"] = worktree_observation
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
        # TrackA-A1 METER: carry the support-only token usage through the write-
        # observation rebuild untouched (it never entered returned_value).
        adapter_usage=adapter_result.adapter_usage,
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

def _raw_sensitive_path_writes(changed_files: Iterable[str]) -> tuple[str, ...]:
    """RAW structural sensitive-path observation (REDO Smith 0623).

    This is a RAW structural observation that needs NO scope knowledge: which
    changed paths are .env / *.pem / *.key or carry an auth/credential/secret/token
    / provider-session-like path segment. It is support's own RAW observation; the written-vs-scope
    classification (against the recommended write_scope) is the Brick axis's
    (``brick.comparison.compare_changed_paths_to_write_scope``).

    support RAISES NOTHING here. Every disposition (including a sensitive-path write)
    is RECORDED, not stopped -- the disposable worktree is the integrity boundary and
    secret read/egress stays hard in adapter_validation. (The former ``.git`` floor
    was removed: changed_files is built from the snapshot/status diff, which excludes
    ``.git``, so a ``.git`` path never reached the floor -- it could never fire.)
    """

    observed: list[str] = []
    for raw_path in changed_files:
        clean = str(raw_path).strip().replace("\\", "/")
        if not clean:
            continue
        lowered = clean.lower()
        if (
            lowered.endswith((".pem", ".key"))
            or _path_has_forbidden_write_segment(lowered)
            or _path_has_provider_session_like_segment(lowered)
            or lowered == ".env"
            or lowered.startswith(".env/")
        ):
            observed.append(clean)
    return tuple(observed)

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

def _path_has_provider_session_like_segment(path: str) -> bool:
    segments = [
        segment
        for segment in path.replace("\\", "/").replace(".", "/").replace("-", "/").replace("_", "/").split("/")
        if segment
    ]
    if "session" in segments:
        return True
    return any(
        segment in {"provider", "runtime", "conversation", "transcript"}
        for segment in segments
    ) and any(segment in {"id", "ids", "state", "states", "log", "logs"} for segment in segments)

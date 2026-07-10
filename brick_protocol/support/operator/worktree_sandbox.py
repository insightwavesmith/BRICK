"""Engine-created disposable git-worktree sandbox for customer-facing dispatch.

This is a THIN operator helper (no axis meaning, no Movement, no success/quality
judgment). It exists so a CUSTOMER-FACING building dispatch runs entirely inside
an engine-created, disposable git worktree at a PINNED base SHA -- the live /
customer working tree is NEVER written -- and the building's code output becomes
a COMMIT produced ONLY on genuine completion. The worktree boundary IS the
protection: a QA step (or any provider write) may write freely inside the
worktree without touching the customer's checkout.

It owns ONLY mechanics:

  * probe  -> is ``git`` installed and is ``repo_root`` a git tree with HEAD?
  * BASE   -> the explicitly resolved HEAD SHA (never a bare ``--detach`` race).
  * create -> ``git worktree add --detach <wt> <BASE>`` under ~/.brick/worktrees.
  * reap   -> force-remove STALE engine-created worktrees (crash-safe), gated to
              engine paths only (deny-hook safe -- never a user path).
  * commit -> AFTER the run bracket, ONLY when the caller observed a genuinely
              complete frontier; otherwise no commit (honesty).
  * dispose-> force-remove the engine-created worktree (commit + durable
              evidence survive, both living OUTSIDE the worktree).

It chooses no Movement, judges no success/quality/source-truth, and reads no
axis. The commit gate is supplied BY THE CALLER (the frontier observation), so
this helper never decides completion itself. The probe fail-closes: on ANY git
failure the caller falls back to a disposable temp dir and the live tree is
left untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import threading

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from brick_protocol.support.operator.write_observation import _raw_sensitive_path_writes


# WHERE: a sibling under ~/.brick/worktrees/<building-id>/ -- OUTSIDE any repo
# (mirrors the ~/.brick precedent; never in-repo). The marker file below stamps
# each created worktree so cleanup/reap can be gated to ENGINE-created paths
# only (deny-hook safe -- a stray user directory is never force-removed).
def _engine_worktrees_root() -> Path:
    """The engine-created worktrees root, resolved at CALL time (not module-load
    time) so a per-run HOME is honored. P5: a Building executing under a different
    HOME used to bind this to the load-time HOME, making worktree paths -- and thus
    checks like building_operator_driver0 -- diverge by environment (the dogfood
    building-lifecycle friction root). Lazy resolution removes that divergence."""
    return Path.home() / ".brick" / "worktrees"


def __getattr__(name: str) -> object:
    # Keep ENGINE_WORKTREES_ROOT importable as a module attribute, but resolved
    # lazily (no module-load-time HOME capture). Internal call sites use
    # _engine_worktrees_root() directly.
    if name == "ENGINE_WORKTREES_ROOT":
        return _engine_worktrees_root()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
_ENGINE_WORKTREE_MARKER = ".brick-engine-worktree"
_DEFAULT_STALE_AFTER_SECONDS = 24 * 60 * 60
_ACTIVE_WORKTREE_PATHS: set[str] = set()
_ACTIVE_WORKTREE_PATHS_LOCK = threading.Lock()


class WorktreeSandboxError(RuntimeError):
    """A git worktree sandbox operation failed (probe is separate and quiet)."""


@dataclass(frozen=True)
class WorktreeProbe:
    """Mechanical probe of whether ``repo_root`` can host a worktree sandbox.

    ``ok`` is True ONLY when git is installed AND ``repo_root`` is the top of a
    git work tree at a resolvable HEAD. ANY failure (no git, not a repo,
    unresolved/unborn HEAD) yields ok=False + a recorded reason; the caller then
    falls back to a temp dir and NEVER writes the live tree.
    """

    ok: bool
    reason: str
    base_sha: str = ""


@dataclass(frozen=True)
class WorktreeSandbox:
    """A live engine-created detached worktree at a pinned BASE SHA."""

    path: Path
    base_sha: str
    repo_root: Path
    building_id: str = ""


@dataclass(frozen=True)
class EngineWorktreeMarker:
    """Support-only parsed marker fields; not an authority record."""

    created_at: datetime
    repo_root: str
    building_id: str
    base_sha: str
    owner_pid: int | None = None
    lease_id: str = ""


@dataclass(frozen=True)
class WipRecoveryHandle:
    """Verified recovery address for one canonical WIP generation."""

    ref: str
    sha: str
    base_sha: str
    tree_sha: str
    building_id: str
    backup_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorktreePreservationObservation:
    """Raw byte-preservation facts for an engine/caller worktree."""

    status_readable: bool
    tracked_or_untracked_paths: tuple[str, ...] = ()
    ignored_paths: tuple[str, ...] = ()
    dirty_submodule_paths: tuple[str, ...] = ()

    @property
    def dirty(self) -> bool:
        return bool(
            self.tracked_or_untracked_paths
            or self.ignored_paths
            or self.dirty_submodule_paths
        )

    @property
    def fully_anchorable(self) -> bool:
        return self.status_readable and not self.ignored_paths and not self.dirty_submodule_paths


def probe_worktree_capable(repo_root: Path | str) -> WorktreeProbe:
    """Probe ``repo_root`` for worktree-sandbox capability. NEVER raises.

    Decision-4 mitigation: BEFORE any worktree dispatch we check ``git
    --version`` + ``git rev-parse --is-inside-work-tree`` + a resolvable HEAD.
    On ANY failure we return ok=False with a reason; the caller degrades to a
    temp dir and leaves the live tree untouched.
    """

    repo = Path(repo_root)
    if _git_version() is None:
        return WorktreeProbe(ok=False, reason="git-not-installed")
    if not repo.is_dir():
        return WorktreeProbe(ok=False, reason="repo-root-not-a-directory")
    inside = _git(repo, "rev-parse", "--is-inside-work-tree")
    if inside is None or inside.strip() != "true":
        return WorktreeProbe(ok=False, reason="not-a-git-work-tree")
    base = _git(repo, "rev-parse", "HEAD")
    if base is None or not base.strip():
        return WorktreeProbe(ok=False, reason="head-unresolved")
    return WorktreeProbe(ok=True, reason="git-head-resolved", base_sha=base.strip())


def create_worktree_sandbox(
    repo_root: Path | str,
    *,
    building_id: str,
    base_sha: str,
) -> WorktreeSandbox:
    """Create an engine worktree detached at ``base_sha`` under ~/.brick/worktrees.

    Decision-1 mitigation: the BASE is the EXPLICITLY resolved HEAD SHA passed
    in (never a bare ``--detach`` that races a moving branch). The new worktree
    is stamped with an engine marker so reap/dispose are gated to engine paths.
    """

    repo = Path(repo_root).resolve()
    base = str(base_sha).strip()
    if not base:
        raise WorktreeSandboxError("create_worktree_sandbox requires an explicit base_sha")
    # Reap any stale engine worktrees first (crash-safe): the previous run may
    # have died before dispose. Only ENGINE-created paths are touched.
    reap_stale_worktrees(repo)
    wt_path = _worktree_path_for(building_id)
    if wt_path.exists():
        # Same-building residue is removed only when the marker proves it is
        # stale. A live/young or unparseable marker fails closed so the wrapper
        # can degrade without deleting uncertain work.
        if not _force_remove_stale_worktree(
            repo,
            wt_path,
            stale_after_seconds=_DEFAULT_STALE_AFTER_SECONDS,
        ):
            raise WorktreeSandboxError(
                f"refusing to replace a non-stale engine worktree path: {wt_path}"
            )
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    added = _git(repo, "worktree", "add", "--detach", str(wt_path), base)
    if added is None or not wt_path.is_dir():
        raise WorktreeSandboxError(
            f"git worktree add --detach failed for {wt_path} at {base}"
        )
    # Stamp the engine marker (NOT a tracked file: it lives only in the worktree
    # checkout dir and is removed with it; it never reaches a commit because the
    # commit step adds only real changes relative to BASE... the marker is git-
    # ignored by being added to the worktree's local exclude below).
    _write_engine_marker(wt_path, repo=repo, building_id=building_id, base=base)
    _claim_worktree_lease(wt_path)
    return WorktreeSandbox(
        path=wt_path,
        base_sha=base,
        repo_root=repo,
        building_id=str(building_id),
    )


def commit_sandbox_output(
    sandbox: WorktreeSandbox,
    *,
    message: str,
) -> str:
    """Commit the worktree's changes and return the new commit SHA.

    Decision-3 mitigation: the CALLER invokes this ONLY when it observed a
    genuinely complete frontier, and ONLY AFTER the run bracket (so the
    write-observation HEAD guard, which bans a HEAD move mid-step, is honored --
    this commit moves HEAD only once the adapter bracket has closed). Returns ""
    when there is nothing to commit (no provider write landed).
    """

    wt = sandbox.path
    if not wt.is_dir():
        raise WorktreeSandboxError(f"cannot commit a disposed worktree: {wt}")
    observation = observe_worktree_preservation(wt)
    _require_anchorable_observation(observation, worktree=wt, source="sandbox commit")
    if not observation.tracked_or_untracked_paths:
        return ""
    sensitive_paths = _raw_sensitive_path_writes(observation.tracked_or_untracked_paths)
    if sensitive_paths:
        raise WorktreeSandboxError(
            "observed_sensitive_path_writes block sandbox commit: "
            + ", ".join(sensitive_paths)
        )
    if _git(wt, "add", "--all") is None:
        raise WorktreeSandboxError(f"git add failed in worktree {wt}")
    _unstage_engine_marker(wt)
    committed = _git(
        wt,
        "-c",
        "user.name=brick-engine",
        "-c",
        "user.email=engine@brick.local",
        "commit",
        "--no-verify",
        "-m",
        _landed_commit_message(
            message,
            building_id=sandbox.building_id,
            base_sha=sandbox.base_sha,
        ),
    )
    if committed is None:
        raise WorktreeSandboxError(f"git commit failed in worktree {wt}")
    head = _git(wt, "rev-parse", "HEAD")
    if head is None or not head.strip():
        raise WorktreeSandboxError(f"could not read committed HEAD in worktree {wt}")
    return head.strip()


def anchor_wip_snapshot(
    sandbox: WorktreeSandbox,
    building_id: str,
    *,
    message: str,
    include_clean: bool = False,
) -> str:
    """Pin incomplete provider WIP under ``refs/brick/wip/<building>``.

    This is the non-complete twin of ``commit_sandbox_output``: it snapshots the
    disposable worktree's current tree without moving any branch. The caller owns
    the incomplete-frontier observation; this helper only preserves the bytes so
    disposal does not destroy useful WIP evidence.
    """

    wt = sandbox.path
    if not wt.is_dir():
        raise WorktreeSandboxError(f"cannot anchor a disposed worktree: {wt}")
    observation = observe_worktree_preservation(wt)
    _require_anchorable_observation(observation, worktree=wt, source="sandbox WIP anchor")
    if not observation.tracked_or_untracked_paths and not include_clean:
        return ""
    sensitive_paths = _raw_sensitive_path_writes(observation.tracked_or_untracked_paths)
    if sensitive_paths:
        raise WorktreeSandboxError(
            "observed_sensitive_path_writes block sandbox WIP anchor: "
            + ", ".join(sensitive_paths)
        )
    if _git(wt, "add", "--all") is None:
        raise WorktreeSandboxError(f"git add failed in worktree {wt}")
    _unstage_engine_marker(wt)
    tree = _git(wt, "write-tree")
    if tree is None or not tree.strip():
        raise WorktreeSandboxError(f"git write-tree failed in worktree {wt}")
    commit = _git(
        wt,
        "-c",
        "user.name=brick-engine",
        "-c",
        "user.email=engine@brick.local",
        "commit-tree",
        tree.strip(),
        "-p",
        sandbox.base_sha,
        "-m",
        _wip_commit_message(message, building_id=building_id, base_sha=sandbox.base_sha),
    )
    if commit is None or not commit.strip():
        raise WorktreeSandboxError(f"git commit-tree failed in worktree {wt}")
    return _install_wip_anchor(
        sandbox.repo_root,
        building_id=building_id,
        commit_sha=commit.strip(),
        base_sha=sandbox.base_sha,
    )


def anchor_wip_worktree_snapshot(
    repo_root: Path | str,
    building_id: str,
    *,
    message: str,
    include_clean: bool = False,
) -> tuple[str, str] | None:
    """Pin the current dirty state of an existing git worktree, if any.

    This is the close-time twin for direct ``adapter_cwd`` runs: unlike the
    engine worktree sandbox, the caller owns the worktree lifecycle, so this
    helper only writes ``refs/brick/wip/<building_id>`` and leaves the worktree
    itself in place.
    """

    repo = Path(repo_root).resolve()
    base = _git(repo, "rev-parse", "HEAD")
    if base is None or not base.strip():
        return None
    observation = observe_worktree_preservation(repo)
    _require_anchorable_observation(observation, worktree=repo, source="direct WIP anchor")
    if not observation.tracked_or_untracked_paths and not include_clean:
        return None
    sensitive_paths = _raw_sensitive_path_writes(observation.tracked_or_untracked_paths)
    if sensitive_paths:
        raise WorktreeSandboxError(
            "observed_sensitive_path_writes block direct WIP anchor: "
            + ", ".join(sensitive_paths)
        )
    with tempfile.TemporaryDirectory(prefix="bp-wip-index-") as tmp:
        index_path = str(Path(tmp) / "index")
        env = {**os.environ, "GIT_INDEX_FILE": index_path}
        if _git_env(repo, env, "read-tree", base.strip()) is None:
            raise WorktreeSandboxError(f"git read-tree failed in worktree {repo}")
        if _git_env(repo, env, "add", "--all") is None:
            raise WorktreeSandboxError(f"git add failed in temporary index for {repo}")
        tree = _git_env(repo, env, "write-tree")
    if tree is None or not tree.strip():
        raise WorktreeSandboxError(f"git write-tree failed in temporary index for {repo}")
    commit = _git(
        repo,
        "-c",
        "user.name=brick-engine",
        "-c",
        "user.email=engine@brick.local",
        "commit-tree",
        tree.strip(),
        "-p",
        base.strip(),
        "-m",
        _wip_commit_message(message, building_id=building_id, base_sha=base.strip()),
    )
    if commit is None or not commit.strip():
        raise WorktreeSandboxError(f"git commit-tree failed in worktree {repo}")
    ref = _install_wip_anchor(
        repo,
        building_id=building_id,
        commit_sha=commit.strip(),
        base_sha=base.strip(),
    )
    reclaimed = reclaim_wip_anchor(repo, building_id)
    if reclaimed is None:
        raise WorktreeSandboxError(f"WIP anchor did not resolve after update-ref: {ref}")
    if not reclaimed[0]:
        return None
    return reclaimed


def observe_preexisting_dirty_paths(repo_root: Path | str) -> tuple[str, ...]:
    """Read-only observation of an ``adapter_cwd`` worktree's dirty paths.

    This is the LAUNCH-time twin of ``anchor_wip_worktree_snapshot``: before a
    direct ``adapter_cwd`` dispatch begins, the run surface observes whether the
    caller-owned worktree already carries uncommitted changes so it can WARN the
    operator that a close-time WIP anchor will fold pre-existing dirt into the
    same snapshot. It is purely observational -- it NEVER refuses, mutates, moves
    a branch, raises, or judges Movement/success/quality. A non-git tree, a git
    failure, or a clean tree all yield an empty tuple.
    """

    try:
        repo = Path(repo_root).resolve()
    except OSError:
        return ()
    observation = observe_worktree_preservation(repo)
    if not observation.status_readable:
        return ()
    return tuple(
        sorted(
            dict.fromkeys(
                observation.tracked_or_untracked_paths
                + observation.ignored_paths
                + observation.dirty_submodule_paths
            )
        )
    )


def observe_worktree_preservation(
    repo_root: Path | str,
) -> WorktreePreservationObservation:
    """Observe tracked, ignored-only, and dirty-submodule preservation facts.

    Ignored-only files and dirty submodule worktrees cannot be represented by the
    ordinary parent-repo tree written by ``git write-tree``. They are therefore
    explicit facts, never an empty/clean result.
    """

    try:
        repo = Path(repo_root).resolve()
    except OSError:
        return WorktreePreservationObservation(status_readable=False)
    status = _git(
        repo,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    ignored_status = _git(
        repo,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--ignored=matching",
        "--ignore-submodules=none",
    )
    v2_status = _git(
        repo,
        "status",
        "--porcelain=v2",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    if status is None or ignored_status is None or v2_status is None:
        return WorktreePreservationObservation(status_readable=False)
    ignored_paths = tuple(
        sorted(
            dict.fromkeys(
                path
                for line in ignored_status.splitlines()
                if line.startswith("!! ")
                for path in (_git_status_path(line),)
                if path and path != _ENGINE_WORKTREE_MARKER
            )
        )
    )
    submodule_paths = _dirty_submodule_paths(v2_status)
    return WorktreePreservationObservation(
        status_readable=True,
        tracked_or_untracked_paths=_git_status_paths(status),
        ignored_paths=ignored_paths,
        dirty_submodule_paths=submodule_paths,
    )


def reclaim_wip_anchor(repo_root: Path | str, building_id: str) -> tuple[str, str] | None:
    """Return the canonical WIP ref + commit (legacy-compatible read seam)."""

    repo = Path(repo_root).resolve()
    ref = _wip_anchor_ref(building_id)
    sha = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if sha is None or not sha.strip():
        return None
    return ref, sha.strip()


def reclaim_wip_recovery_handle(
    repo_root: Path | str,
    building_id: str,
    *,
    expected_base_sha: str = "",
) -> WipRecoveryHandle | None:
    """Return a verified ref/sha/base recovery handle for one Building WIP."""

    repo = Path(repo_root).resolve()
    ref = _wip_anchor_ref(building_id)
    sha = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if sha is None or not sha.strip():
        return None
    return _verified_wip_handle(
        repo,
        ref=ref,
        sha=sha.strip(),
        building_id=building_id,
        expected_base_sha=expected_base_sha,
    )


def release_wip_anchor(
    repo_root: Path | str,
    building_id: str,
    *,
    expected_sha: str = "",
) -> bool:
    """Atomically delete the canonical WIP ref, optionally comparing its SHA."""

    repo = Path(repo_root).resolve()
    ref = _wip_anchor_ref(building_id)
    current = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if current is None or not current.strip():
        return False
    current_sha = current.strip()
    expected = str(expected_sha).strip()
    if expected and current_sha != expected:
        raise WorktreeSandboxError(
            f"refusing to release changed WIP anchor {ref}: expected {expected}, observed {current_sha}"
        )
    return _git(repo, "update-ref", "-d", ref, current_sha) is not None


def anchor_landed_output(
    sandbox: WorktreeSandbox,
    building_id: str,
    commit_sha: str,
) -> str:
    """Pin a completed detached-worktree commit before disposal.

    The canonical landed ref is compare-and-swapped, and an older generation is
    retained under ``refs/brick/landed-backup``.  This is mechanical durability;
    it does not merge or move the caller's branch.
    """

    repo = sandbox.repo_root.resolve()
    if sandbox.building_id and sandbox.building_id != str(building_id):
        raise WorktreeSandboxError(
            "landed output Building identity mismatch: "
            f"{sandbox.building_id!r} != {str(building_id)!r}"
        )
    sha = str(commit_sha).strip()
    if not sha:
        raise WorktreeSandboxError("landed output requires a commit SHA")
    object_type = _git(repo, "cat-file", "-t", sha)
    if object_type is None or object_type.strip() != "commit":
        raise WorktreeSandboxError(f"landed output is not a commit: {sha}")
    if _git(repo, "merge-base", "--is-ancestor", sandbox.base_sha, sha) is None:
        raise WorktreeSandboxError(
            f"landed output {sha} does not descend from sandbox base {sandbox.base_sha}"
        )
    owner, declared_base = _landed_commit_identity(repo, sha)
    if sha != sandbox.base_sha and owner != str(building_id):
        raise WorktreeSandboxError(
            f"landed output commit owner mismatch: {owner!r} != {str(building_id)!r}"
        )
    if declared_base and declared_base != sandbox.base_sha:
        raise WorktreeSandboxError(
            f"landed output commit base mismatch: {declared_base} != {sandbox.base_sha}"
        )
    ref = _landed_output_ref(building_id)
    current = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    current_sha = current.strip() if current is not None else ""
    if current_sha:
        current_owner, _ = _landed_commit_identity(repo, current_sha)
        if current_owner and current_owner != str(building_id):
            raise WorktreeSandboxError(
                f"landed ref ownership mismatch at {ref}: {current_owner!r}"
            )
    if current_sha and current_sha != sha:
        backup_ref = _landed_backup_ref(building_id, current_sha)
        backup = _git(repo, "rev-parse", "--verify", f"{backup_ref}^{{commit}}")
        if backup is None:
            if _git(repo, "update-ref", backup_ref, current_sha, "0" * 40) is None:
                raise WorktreeSandboxError(
                    f"could not preserve previous landed generation: {backup_ref}"
                )
        elif backup.strip() != current_sha:
            raise WorktreeSandboxError(
                f"landed generation backup collision at {backup_ref}"
            )
    expected_old = current_sha or "0" * 40
    if current_sha != sha and _git(repo, "update-ref", ref, sha, expected_old) is None:
        raise WorktreeSandboxError(f"could not install landed output ref {ref}")
    verified = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if verified is None or verified.strip() != sha:
        raise WorktreeSandboxError(
            f"landed output ref did not verify after update: {ref} -> {sha}"
        )
    return ref


def reap_stale_wip_anchors(
    repo_root: Path | str,
    *,
    stale_after_seconds: int = _DEFAULT_STALE_AFTER_SECONDS,
) -> tuple[str, ...]:
    """Deprecated fail-closed shim: age alone never releases recovery refs.

    A WIP ref remains until a caller supplies landed/discard evidence to the
    explicit release seam. Keeping this name avoids breaking old imports while
    removing the age-based data-loss primitive.
    """

    _ = (repo_root, stale_after_seconds)
    return ()


def dispose_worktree_sandbox(sandbox: WorktreeSandbox) -> bool:
    """Remove an engine worktree only after its dirty bytes are recoverable.

    Decision-4/CLEANUP mitigation: only the ENGINE-created worktree path is
    force-removed (gated to engine-created paths -- deny-hook safe, never a user
    path). The commit object lives in the SHARED repo object store and the
    evidence lives under output_root OUTSIDE the worktree, so both survive.
    Returns True when the worktree directory is gone afterward.
    """

    _require_active_disposal_recovery(sandbox)
    disposed = _force_remove_active_worktree(sandbox)
    release_worktree_lease(sandbox)
    return disposed


def reap_stale_worktrees(
    repo_root: Path | str,
    *,
    stale_after_seconds: int = _DEFAULT_STALE_AFTER_SECONDS,
) -> tuple[str, ...]:
    """Force-remove stale ENGINE-created worktrees under ~/.brick/worktrees.

    Crash-safety: a run that died before dispose leaves a stale engine worktree.
    The next run reaps only paths whose marker ``created_at`` is older than the
    caller-supplied threshold. ONLY parseable engine-marked paths under
    ENGINE_WORKTREES_ROOT are touched (gated -- never a user path). Missing,
    older-format, or unparseable markers fail closed. Returns the reaped paths.
    """

    repo = Path(repo_root).resolve()
    reaped: list[str] = []
    if not _engine_worktrees_root().is_dir():
        _git(repo, "worktree", "prune")
        return ()
    for child in sorted(_engine_worktrees_root().iterdir()):
        if not child.is_dir():
            continue
        if not _is_engine_worktree(child):
            continue
        if _force_remove_stale_worktree(
            repo,
            child,
            stale_after_seconds=stale_after_seconds,
        ):
            reaped.append(str(child))
    _git(repo, "worktree", "prune")
    return tuple(reaped)


def temp_dir_fallback(prefix: str = "bp-customer-sandbox-") -> tempfile.TemporaryDirectory[str]:
    """A disposable temp dir used when the probe refused a worktree.

    Decision-4 mitigation: on a non-git/no-git/unresolved-HEAD environment the
    caller runs the dispatch with this temp dir as adapter_cwd (the onboard
    precedent), so even a real provider's writes stay under the temp dir and the
    live tree is NEVER written. The caller cleans it up.
    """

    return tempfile.TemporaryDirectory(prefix=prefix)


def reopen_worktree_sandbox(
    repo_root: Path | str,
    building_id: str,
) -> WorktreeSandbox | None:
    """Reopen a still-registered engine worktree after strict ownership checks.

    This does not create, delete, anchor, or choose whether the caller should
    resume it. It only returns the typed sandbox handle needed to route an
    existing same-Building workspace through the normal close bracket.
    """

    repo = Path(repo_root).resolve()
    path = _worktree_path_for(building_id)
    marker = _read_engine_marker(path)
    if marker is None:
        return None
    if not _marker_owned_by_repo(marker, repo):
        raise WorktreeSandboxError(
            f"engine worktree ownership mismatch for {path}: marker repo={marker.repo_root!r}, "
            f"caller repo={str(repo)!r}"
        )
    if marker.building_id != str(building_id):
        raise WorktreeSandboxError(
            f"engine worktree building mismatch for {path}: marker={marker.building_id!r}, "
            f"requested={str(building_id)!r}"
        )
    if not _git_lists_worktree(repo, path):
        raise WorktreeSandboxError(
            f"engine worktree is not registered in its owning repo: {path}"
        )
    if (
        marker.owner_pid is not None
        and marker.owner_pid != os.getpid()
        and _marker_owner_is_live(marker)
    ):
        raise WorktreeSandboxError(
            f"refusing to reopen a worktree owned by live pid {marker.owner_pid}: {path}"
        )
    head = _git(path, "rev-parse", "HEAD")
    if head is None or head.strip() != marker.base_sha:
        raise WorktreeSandboxError(
            "refusing to reopen an engine worktree whose HEAD moved away from "
            f"its marker base: {path}"
        )
    _claim_worktree_lease(path)
    return WorktreeSandbox(
        path=path,
        base_sha=marker.base_sha,
        repo_root=repo,
        building_id=marker.building_id,
    )


def release_worktree_lease(sandbox: WorktreeSandbox | Path | str) -> None:
    """Release this process's in-memory lease without deleting the worktree."""

    path = sandbox.path if isinstance(sandbox, WorktreeSandbox) else Path(sandbox)
    try:
        key = str(path.resolve())
    except OSError:
        key = str(path)
    with _ACTIVE_WORKTREE_PATHS_LOCK:
        _ACTIVE_WORKTREE_PATHS.discard(key)


def verify_worktree_recovery_handle(
    sandbox: WorktreeSandbox,
    handle: WipRecoveryHandle,
) -> None:
    """Fail closed unless a reopened workspace is byte-identical to its WIP ref."""

    if sandbox.building_id != handle.building_id:
        raise WorktreeSandboxError(
            "reopened worktree recovery building mismatch: "
            f"{sandbox.building_id!r} != {handle.building_id!r}"
        )
    if sandbox.base_sha not in {handle.base_sha, handle.sha}:
        raise WorktreeSandboxError(
            "reopened worktree recovery base mismatch: "
            f"{sandbox.base_sha} not in base/WIP {{{handle.base_sha}, {handle.sha}}}"
        )
    observation = observe_worktree_preservation(sandbox.path)
    _require_anchorable_observation(
        observation,
        worktree=sandbox.path,
        source="reopened worktree recovery verification",
    )
    observed_tree = _snapshot_worktree_tree(sandbox.path)
    if observed_tree != handle.tree_sha:
        raise WorktreeSandboxError(
            "reopened worktree bytes do not match the verified WIP generation: "
            f"observed_tree={observed_tree} wip_tree={handle.tree_sha} ref={handle.ref}"
        )


# ---------------------------------------------------------------------------
# internal mechanics
# ---------------------------------------------------------------------------


def _worktree_path_for(building_id: str) -> Path:
    return _engine_worktrees_root() / _slug(building_id)


def _wip_anchor_ref(building_id: str) -> str:
    return f"refs/brick/wip/{_slug(building_id)}"


def _wip_backup_ref(building_id: str, sha: str) -> str:
    return f"refs/brick/wip-backup/{_slug(building_id)}-{sha}"


def _landed_output_ref(building_id: str) -> str:
    identity = hashlib.sha256(str(building_id).encode("utf-8")).hexdigest()[:12]
    return f"refs/brick/landed/{_slug(building_id)}-{identity}"


def _landed_backup_ref(building_id: str, sha: str) -> str:
    identity = hashlib.sha256(str(building_id).encode("utf-8")).hexdigest()[:12]
    return f"refs/brick/landed-backup/{_slug(building_id)}-{identity}-{sha}"


def _landed_commit_message(message: str, *, building_id: str, base_sha: str) -> str:
    return (
        str(message).rstrip()
        + "\n\nbrick-landed-building-id: "
        + json.dumps(str(building_id), ensure_ascii=False)
        + "\nbrick-landed-base-sha: "
        + str(base_sha).strip()
        + "\n"
    )


def _landed_commit_identity(repo: Path, sha: str) -> tuple[str, str]:
    body = _git(repo, "show", "-s", "--format=%B", sha)
    if body is None:
        raise WorktreeSandboxError(f"could not read landed commit message: {sha}")
    building_id = ""
    base_sha = ""
    for line in body.splitlines():
        if line.startswith("brick-landed-building-id: "):
            encoded = line.removeprefix("brick-landed-building-id: ").strip()
            try:
                decoded = json.loads(encoded)
            except json.JSONDecodeError as exc:
                raise WorktreeSandboxError(
                    f"malformed landed Building identity in {sha}"
                ) from exc
            if isinstance(decoded, str):
                building_id = decoded
        elif line.startswith("brick-landed-base-sha: "):
            base_sha = line.removeprefix("brick-landed-base-sha: ").strip()
    return building_id, base_sha


def _unstage_engine_marker(wt_path: Path) -> None:
    # The marker is normally excluded, but keep commit/anchor output clean if the
    # local exclude write was unavailable.
    _git(wt_path, "reset", "-q", "--", _ENGINE_WORKTREE_MARKER)


def _write_engine_marker(wt_path: Path, *, repo: Path, building_id: str, base: str) -> None:
    marker = wt_path / _ENGINE_WORKTREE_MARKER
    stamp = (
        f"engine-created\nrepo_root={repo}\nbuilding_id={building_id}\n"
        f"base_sha={base}\ncreated_at={_recorded_at()}\n"
        f"owner_pid={os.getpid()}\nlease_id={os.urandom(16).hex()}\n"
    )
    marker.write_text(stamp, encoding="utf-8")
    # Keep the marker OUT of the committed output: add it to the worktree's own
    # local exclude so `git add --all` never stages it. (The exclude file lives
    # in the worktree's private git dir, not the shared tracked tree.)
    git_dir = _git(wt_path, "rev-parse", "--git-path", "info/exclude")
    if git_dir:
        exclude_path = Path(git_dir.strip())
        if not exclude_path.is_absolute():
            exclude_path = (wt_path / exclude_path).resolve()
        try:
            exclude_path.parent.mkdir(parents=True, exist_ok=True)
            existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
            if _ENGINE_WORKTREE_MARKER not in existing:
                exclude_path.write_text(
                    existing + ("" if existing.endswith("\n") or not existing else "\n")
                    + _ENGINE_WORKTREE_MARKER + "\n",
                    encoding="utf-8",
                )
        except OSError:
            # Best effort: if we cannot write the exclude, fall back to removing
            # the marker right before commit (handled in the wrapper).
            pass


def _read_engine_marker(path: Path) -> EngineWorktreeMarker | None:
    marker = path / _ENGINE_WORKTREE_MARKER
    try:
        body = marker.read_text(encoding="utf-8")
    except OSError:
        return None
    fields: dict[str, str] = {}
    lines = body.splitlines()
    if not lines or lines[0].strip() != "engine-created":
        return None
    for line in lines[1:]:
        key, sep, value = line.partition("=")
        if sep:
            fields[key.strip()] = value.strip()
    created_at = _parse_marker_created_at(fields.get("created_at", ""))
    if created_at is None:
        return None
    repo_root = fields.get("repo_root", "")
    building_id = fields.get("building_id", "")
    base_sha = fields.get("base_sha", "")
    if not (repo_root and building_id and base_sha):
        return None
    raw_owner_pid = fields.get("owner_pid", "")
    try:
        owner_pid = int(raw_owner_pid) if raw_owner_pid else None
    except ValueError:
        return None
    if owner_pid is not None and owner_pid <= 0:
        return None
    return EngineWorktreeMarker(
        created_at=created_at,
        repo_root=repo_root,
        building_id=building_id,
        base_sha=base_sha,
        owner_pid=owner_pid,
        lease_id=fields.get("lease_id", ""),
    )


def _parse_marker_created_at(value: str) -> datetime | None:
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _marker_owned_by_repo(marker: EngineWorktreeMarker, repo: Path) -> bool:
    try:
        marker_repo = Path(marker.repo_root).resolve()
        caller_repo = repo.resolve()
    except OSError:
        return False
    if marker_repo != caller_repo:
        return False
    return _git(caller_repo, "cat-file", "-e", f"{marker.base_sha}^{{commit}}") is not None


def _claim_worktree_lease(path: Path) -> None:
    try:
        key = str(path.resolve())
    except OSError:
        key = str(path)
    with _ACTIVE_WORKTREE_PATHS_LOCK:
        if key in _ACTIVE_WORKTREE_PATHS:
            raise WorktreeSandboxError(
                f"engine worktree already has an active in-process lease: {path}"
            )
        _ACTIVE_WORKTREE_PATHS.add(key)


def _marker_owner_is_live(marker: EngineWorktreeMarker) -> bool:
    if marker.owner_pid is None or not marker.lease_id:
        return False
    try:
        os.kill(marker.owner_pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _require_anchorable_observation(
    observation: WorktreePreservationObservation,
    *,
    worktree: Path,
    source: str,
) -> None:
    if not observation.status_readable:
        raise WorktreeSandboxError(f"{source} could not read complete git status in {worktree}")
    if observation.ignored_paths:
        raise WorktreeSandboxError(
            f"{source} observed ignored-only writes that a git tree cannot preserve: "
            + ", ".join(observation.ignored_paths)
        )
    if observation.dirty_submodule_paths:
        raise WorktreeSandboxError(
            f"{source} observed dirty submodule worktrees that the parent git tree cannot preserve: "
            + ", ".join(observation.dirty_submodule_paths)
        )


def _dirty_submodule_paths(v2_status: str) -> tuple[str, ...]:
    observed: list[str] = []
    for line in v2_status.splitlines():
        if line.startswith("1 "):
            fields = line.split(" ", 8)
            if len(fields) < 9:
                continue
            submodule_state = fields[2]
            path = fields[8]
        elif line.startswith("2 "):
            fields = line.split(" ", 9)
            if len(fields) < 10:
                continue
            submodule_state = fields[2]
            path = fields[9].split("\t", 1)[0]
        else:
            continue
        if submodule_state.startswith("S"):
            observed.append(path.replace("\\", "/"))
    return tuple(sorted(dict.fromkeys(observed)))


def _snapshot_worktree_tree(worktree: Path) -> str:
    head = _git(worktree, "rev-parse", "HEAD")
    if head is None or not head.strip():
        raise WorktreeSandboxError(f"cannot resolve worktree HEAD for recovery check: {worktree}")
    with tempfile.TemporaryDirectory(prefix="bp-dispose-index-") as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        if _git_env(worktree, env, "read-tree", head.strip()) is None:
            raise WorktreeSandboxError(f"git read-tree failed during recovery check: {worktree}")
        if _git_env(worktree, env, "add", "--all") is None:
            raise WorktreeSandboxError(f"git add failed during recovery check: {worktree}")
        tree = _git_env(worktree, env, "write-tree")
    if tree is None or not tree.strip():
        raise WorktreeSandboxError(f"git write-tree failed during recovery check: {worktree}")
    return tree.strip()


def _wip_commit_message(message: str, *, building_id: str, base_sha: str) -> str:
    return (
        str(message).rstrip()
        + "\n\nbrick-wip-building-id: "
        + json.dumps(str(building_id), ensure_ascii=False)
        + "\nbrick-wip-base-sha: "
        + str(base_sha).strip()
        + "\n"
    )


def _wip_commit_identity(repo: Path, sha: str) -> tuple[str, str]:
    body = _git(repo, "show", "-s", "--format=%B", sha)
    if body is None:
        raise WorktreeSandboxError(f"could not read WIP commit message: {sha}")
    building_id = ""
    declared_base = ""
    for line in body.splitlines():
        if line.startswith("brick-wip-building-id: "):
            encoded = line.removeprefix("brick-wip-building-id: ").strip()
            try:
                decoded = json.loads(encoded)
            except json.JSONDecodeError as exc:
                raise WorktreeSandboxError(
                    f"malformed WIP building identity in {sha}"
                ) from exc
            if isinstance(decoded, str):
                building_id = decoded
        elif line.startswith("brick-wip-base-sha: "):
            declared_base = line.removeprefix("brick-wip-base-sha: ").strip()
    return building_id, declared_base


def _verified_wip_handle(
    repo: Path,
    *,
    ref: str,
    sha: str,
    building_id: str,
    expected_base_sha: str = "",
) -> WipRecoveryHandle:
    object_type = _git(repo, "cat-file", "-t", sha)
    if object_type is None or object_type.strip() != "commit":
        raise WorktreeSandboxError(f"WIP recovery ref is not a commit: {ref} -> {sha}")
    parent_row = _git(repo, "rev-list", "--parents", "-n", "1", sha)
    parents = parent_row.split() if parent_row is not None else []
    if len(parents) != 2:
        raise WorktreeSandboxError(
            f"WIP recovery commit must have exactly one base parent: {ref} -> {sha}"
        )
    base_sha = parents[1]
    owner, declared_base = _wip_commit_identity(repo, sha)
    # Legacy anchors predate the machine trailer and sometimes use a nonstandard
    # subject. The canonical ref remains readable, but every newly installed
    # generation carries an exact owner trailer so future slug collisions fail.
    if owner and owner != str(building_id):
        raise WorktreeSandboxError(
            f"WIP ref slug collision/ownership mismatch at {ref}: "
            f"commit owner={owner or 'unverified'!r}, requested={str(building_id)!r}"
        )
    if declared_base and declared_base != base_sha:
        raise WorktreeSandboxError(
            f"WIP recovery base trailer mismatch at {ref}: {declared_base} != {base_sha}"
        )
    expected = str(expected_base_sha).strip()
    if expected and base_sha != expected:
        raise WorktreeSandboxError(
            f"WIP recovery base mismatch at {ref}: expected {expected}, observed {base_sha}"
        )
    tree = _git(repo, "rev-parse", f"{sha}^{{tree}}")
    if tree is None or not tree.strip():
        raise WorktreeSandboxError(f"could not resolve WIP tree for {ref}: {sha}")
    backup_prefix = f"refs/brick/wip-backup/{_slug(building_id)}-"
    backup_rows = _git(
        repo,
        "for-each-ref",
        "--format=%(refname) %(objectname)",
        backup_prefix,
    )
    backup_refs: list[str] = []
    if backup_rows is not None:
        for row in backup_rows.splitlines():
            backup_ref, separator, backup_sha = row.partition(" ")
            if not separator or not backup_ref.startswith(backup_prefix):
                continue
            try:
                backup_owner, _ = _wip_commit_identity(repo, backup_sha.strip())
            except WorktreeSandboxError:
                continue
            if backup_owner == str(building_id):
                backup_refs.append(backup_ref)
    return WipRecoveryHandle(
        ref=ref,
        sha=sha,
        base_sha=base_sha,
        tree_sha=tree.strip(),
        building_id=str(building_id),
        backup_refs=tuple(sorted(backup_refs)),
    )


def _install_wip_anchor(
    repo_root: Path | str,
    *,
    building_id: str,
    commit_sha: str,
    base_sha: str,
) -> str:
    repo = Path(repo_root).resolve()
    ref = _wip_anchor_ref(building_id)
    new_sha = str(commit_sha).strip()
    _verified_wip_handle(
        repo,
        ref=ref,
        sha=new_sha,
        building_id=building_id,
        expected_base_sha=base_sha,
    )
    current = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    current_sha = current.strip() if current is not None else ""
    if current_sha:
        _verified_wip_handle(
            repo,
            ref=ref,
            sha=current_sha,
            building_id=building_id,
        )
    if current_sha and current_sha != new_sha:
        backup_ref = _wip_backup_ref(building_id, current_sha)
        backup_current = _git(repo, "rev-parse", "--verify", f"{backup_ref}^{{commit}}")
        if backup_current is None:
            if _git(repo, "update-ref", backup_ref, current_sha, "0" * 40) is None:
                raise WorktreeSandboxError(
                    f"git update-ref failed for WIP generation backup {backup_ref}"
                )
        elif backup_current.strip() != current_sha:
            raise WorktreeSandboxError(
                f"WIP generation backup collision at {backup_ref}: "
                f"{backup_current.strip()} != {current_sha}"
            )
    expected_old = current_sha or "0" * 40
    if current_sha != new_sha and _git(repo, "update-ref", ref, new_sha, expected_old) is None:
        raise WorktreeSandboxError(f"git update-ref failed for WIP anchor {ref}")
    verified = reclaim_wip_recovery_handle(
        repo,
        building_id,
        expected_base_sha=base_sha,
    )
    if verified is None or verified.sha != new_sha:
        raise WorktreeSandboxError(
            f"WIP anchor did not verify after update-ref: {ref} -> {new_sha}"
        )
    return ref


def _require_active_disposal_recovery(sandbox: WorktreeSandbox) -> None:
    if not sandbox.path.exists():
        return
    marker = _read_engine_marker(sandbox.path)
    building_id = str(sandbox.building_id).strip()
    if marker is not None:
        if not _marker_owned_by_repo(marker, sandbox.repo_root):
            raise WorktreeSandboxError(
                f"refusing disposal for repo-mismatched engine marker: {sandbox.path}"
            )
        if building_id and marker.building_id != building_id:
            raise WorktreeSandboxError(
                f"refusing disposal for building-mismatched engine marker: {sandbox.path}"
            )
        building_id = building_id or marker.building_id
    observation = observe_worktree_preservation(sandbox.path)
    _require_anchorable_observation(
        observation,
        worktree=sandbox.path,
        source="sandbox dispose",
    )
    sensitive_paths = _raw_sensitive_path_writes(observation.tracked_or_untracked_paths)
    if sensitive_paths:
        raise WorktreeSandboxError(
            "sandbox dispose refuses unpreserved sensitive-path writes: "
            + ", ".join(sensitive_paths)
        )
    if not observation.tracked_or_untracked_paths:
        return
    if not building_id:
        raise WorktreeSandboxError(
            f"sandbox dispose cannot identify the Building recovery ref: {sandbox.path}"
        )
    handle = reclaim_wip_recovery_handle(
        sandbox.repo_root,
        building_id,
        expected_base_sha=sandbox.base_sha,
    )
    if handle is None:
        raise WorktreeSandboxError(
            f"sandbox dispose refuses dirty worktree without verified WIP handle: {sandbox.path}"
        )
    observed_tree = _snapshot_worktree_tree(sandbox.path)
    if observed_tree != handle.tree_sha:
        raise WorktreeSandboxError(
            "sandbox dispose refuses dirty worktree whose bytes differ from WIP handle: "
            f"observed_tree={observed_tree} anchored_tree={handle.tree_sha} ref={handle.ref}"
        )


def _orphan_worktree_payload_present(path: Path) -> bool:
    try:
        return any(child.name != _ENGINE_WORKTREE_MARKER for child in path.iterdir())
    except OSError:
        return True


def _is_stale_engine_worktree(path: Path, *, stale_after_seconds: int) -> bool:
    marker = _read_engine_marker(path)
    if marker is None:
        return False
    try:
        age_seconds = (datetime.now(timezone.utc) - marker.created_at).total_seconds()
    except (OverflowError, OSError):
        return False
    return age_seconds >= max(int(stale_after_seconds), 0)


def _is_engine_worktree(path: Path) -> bool:
    if not _is_under_engine_worktrees_root(path):
        return False
    return (path / _ENGINE_WORKTREE_MARKER).is_file()


def _is_under_engine_worktrees_root(path: Path) -> bool:
    try:
        resolved = path.resolve()
        root = _engine_worktrees_root().resolve()
    except OSError:
        return False
    return root in resolved.parents or resolved == root


def _git_lists_worktree(repo: Path, wt_path: Path) -> bool:
    listing = _git(repo, "worktree", "list", "--porcelain")
    if listing is None:
        return False
    try:
        wanted = wt_path.resolve()
    except OSError:
        wanted = wt_path
    for line in listing.splitlines():
        if not line.startswith("worktree "):
            continue
        raw_path = line.removeprefix("worktree ").strip()
        if not raw_path:
            continue
        try:
            observed = Path(raw_path).resolve()
        except OSError:
            observed = Path(raw_path)
        if observed == wanted:
            return True
    return False


def _force_remove_active_worktree(sandbox: WorktreeSandbox) -> bool:
    # Active disposal has one extra safe proof path: the worktree was just
    # created by this helper, and git still lists it as a worktree for the same
    # repo. This preserves cleanup if an Agent deletes the in-worktree marker
    # while keeping stale reaping marker-gated.
    wt_path = sandbox.path
    marker = _read_engine_marker(wt_path) if wt_path.exists() else None
    if marker is not None and not _marker_owned_by_repo(marker, sandbox.repo_root):
        raise WorktreeSandboxError(
            f"refusing to force-remove a cross-repo engine worktree path: {wt_path}"
        )
    if wt_path.exists() and not (
        _is_engine_worktree(wt_path)
        or (_is_under_engine_worktrees_root(wt_path) and _git_lists_worktree(sandbox.repo_root, wt_path))
    ):
        raise WorktreeSandboxError(
            f"refusing to force-remove a non-engine worktree path: {wt_path}"
        )
    return _force_remove_worktree_unchecked(sandbox.repo_root, wt_path)


def _force_remove_worktree(repo: Path, wt_path: Path) -> bool:
    # GATE: only ever force-remove a path that is BOTH under the engine root and
    # carries the engine marker (or is already gone). Never a user path.
    if wt_path.exists() and not _is_engine_worktree(wt_path):
        raise WorktreeSandboxError(
            f"refusing to force-remove a non-engine worktree path: {wt_path}"
        )
    return _force_remove_worktree_unchecked(repo, wt_path)


def _force_remove_stale_worktree(
    repo: Path,
    wt_path: Path,
    *,
    stale_after_seconds: int,
) -> bool:
    if not _is_engine_worktree(wt_path):
        if wt_path.exists():
            raise WorktreeSandboxError(
                f"refusing to force-remove a non-engine worktree path: {wt_path}"
            )
        return True
    marker = _read_engine_marker(wt_path)
    if marker is None:
        return False
    if not _marker_owned_by_repo(marker, repo):
        return False
    if not _is_stale_engine_worktree(
        wt_path,
        stale_after_seconds=stale_after_seconds,
    ):
        return False
    # Missing lease metadata is uncertain legacy state, not proof of death. New
    # markers carry both fields; old worktrees remain for explicit inventory.
    if marker.owner_pid is None or not marker.lease_id:
        return False
    if _marker_owner_is_live(marker):
        return False
    if not _git_lists_worktree(repo, wt_path):
        # A marker-only orphan can be removed after repo/lease verification. Any
        # payload makes ownership of those bytes uncertain, so preserve it.
        if _orphan_worktree_payload_present(wt_path):
            return False
        return _force_remove_worktree_unchecked(repo, wt_path)
    observation = observe_worktree_preservation(wt_path)
    if not observation.status_readable:
        return False
    if observation.ignored_paths or observation.dirty_submodule_paths:
        return False
    sandbox = WorktreeSandbox(
        path=wt_path,
        base_sha=marker.base_sha,
        repo_root=repo,
        building_id=marker.building_id,
    )
    try:
        anchor_ref = anchor_wip_snapshot(
            sandbox,
            marker.building_id,
            message=(
                f"BRICK WIP anchor: {marker.building_id}\n\n"
                "source=stale-reaper-last-chance"
            ),
            include_clean=True,
        )
        verified = reclaim_wip_recovery_handle(
            repo,
            marker.building_id,
            expected_base_sha=marker.base_sha,
        )
        if not anchor_ref or verified is None or verified.ref != anchor_ref:
            return False
        _require_active_disposal_recovery(sandbox)
    except (OSError, WorktreeSandboxError):
        return False
    return _force_remove_worktree_unchecked(repo, wt_path)


def _force_remove_worktree_unchecked(repo: Path, wt_path: Path) -> bool:
    _git(repo, "worktree", "remove", "--force", str(wt_path))
    if wt_path.exists():
        # git refused (e.g. already detached/unknown) -- prune + best-effort tree
        # removal, still engine-gated by the check above.
        _git(repo, "worktree", "prune")
        _remove_tree(wt_path)
    _git(repo, "worktree", "prune")
    return not wt_path.exists()


def _remove_tree(path: Path) -> None:
    import shutil  # noqa: PLC0415 -- local: cleanup-only, keeps module import light

    try:
        shutil.rmtree(path)
    except OSError:
        pass


def _git_version() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "--version"],
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _git(cwd: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _git_env(cwd: Path, env: Mapping[str, str], *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
            env=dict(env),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _git_status_paths(status: str) -> tuple[str, ...]:
    paths: list[str] = []
    for line in status.splitlines():
        path = _git_status_path(line)
        if path:
            paths.append(path)
    return tuple(sorted(dict.fromkeys(paths)))


def _git_status_path(line: str) -> str:
    if len(line) < 4:
        return ""
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path.replace("\\", "/")


def _recorded_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _slug(value: str) -> str:
    cleaned = []
    for char in str(value).lower():
        if char.isalnum():
            cleaned.append(char)
        elif char in {":", "/", "_", "-", "."}:
            cleaned.append("-")
    slug = "".join(cleaned).strip("-")
    return slug or "building"


__all__ = [
    "ENGINE_WORKTREES_ROOT",
    "WipRecoveryHandle",
    "WorktreeProbe",
    "WorktreePreservationObservation",
    "WorktreeSandbox",
    "WorktreeSandboxError",
    "anchor_wip_snapshot",
    "anchor_wip_worktree_snapshot",
    "anchor_landed_output",
    "commit_sandbox_output",
    "create_worktree_sandbox",
    "dispose_worktree_sandbox",
    "observe_preexisting_dirty_paths",
    "observe_worktree_preservation",
    "probe_worktree_capable",
    "reap_stale_wip_anchors",
    "reap_stale_worktrees",
    "reclaim_wip_anchor",
    "reclaim_wip_recovery_handle",
    "release_wip_anchor",
    "release_worktree_lease",
    "reopen_worktree_sandbox",
    "temp_dir_fallback",
    "verify_worktree_recovery_handle",
]

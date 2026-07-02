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

import subprocess
import tempfile

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


@dataclass(frozen=True)
class EngineWorktreeMarker:
    """Support-only parsed marker fields; not an authority record."""

    created_at: datetime
    repo_root: str
    building_id: str
    base_sha: str


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
    return WorktreeSandbox(path=wt_path, base_sha=base, repo_root=repo)


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
    status = _git(wt, "status", "--porcelain", "--untracked-files=all")
    if status is None:
        raise WorktreeSandboxError(f"git status failed in worktree {wt}")
    if not status.strip():
        return ""
    sensitive_paths = _raw_sensitive_path_writes(_git_status_paths(status))
    if sensitive_paths:
        raise WorktreeSandboxError(
            "observed_sensitive_path_writes block sandbox commit: "
            + ", ".join(sensitive_paths)
        )
    if _git(wt, "add", "--all") is None:
        raise WorktreeSandboxError(f"git add failed in worktree {wt}")
    committed = _git(
        wt,
        "-c",
        "user.name=brick-engine",
        "-c",
        "user.email=engine@brick.local",
        "commit",
        "--no-verify",
        "-m",
        message,
    )
    if committed is None:
        raise WorktreeSandboxError(f"git commit failed in worktree {wt}")
    head = _git(wt, "rev-parse", "HEAD")
    if head is None or not head.strip():
        raise WorktreeSandboxError(f"could not read committed HEAD in worktree {wt}")
    return head.strip()


def dispose_worktree_sandbox(sandbox: WorktreeSandbox) -> bool:
    """Force-remove the engine worktree. Commit + durable evidence survive.

    Decision-4/CLEANUP mitigation: only the ENGINE-created worktree path is
    force-removed (gated to engine-created paths -- deny-hook safe, never a user
    path). The commit object lives in the SHARED repo object store and the
    evidence lives under output_root OUTSIDE the worktree, so both survive.
    Returns True when the worktree directory is gone afterward.
    """

    return _force_remove_active_worktree(sandbox)


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


# ---------------------------------------------------------------------------
# internal mechanics
# ---------------------------------------------------------------------------


def _worktree_path_for(building_id: str) -> Path:
    return _engine_worktrees_root() / _slug(building_id)


def _write_engine_marker(wt_path: Path, *, repo: Path, building_id: str, base: str) -> None:
    marker = wt_path / _ENGINE_WORKTREE_MARKER
    stamp = (
        f"engine-created\nrepo_root={repo}\nbuilding_id={building_id}\n"
        f"base_sha={base}\ncreated_at={_recorded_at()}\n"
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
    return EngineWorktreeMarker(
        created_at=created_at,
        repo_root=repo_root,
        building_id=building_id,
        base_sha=base_sha,
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
    if not _is_stale_engine_worktree(
        wt_path,
        stale_after_seconds=stale_after_seconds,
    ):
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
    "WorktreeProbe",
    "WorktreeSandbox",
    "WorktreeSandboxError",
    "commit_sandbox_output",
    "create_worktree_sandbox",
    "dispose_worktree_sandbox",
    "probe_worktree_capable",
    "reap_stale_worktrees",
    "temp_dir_fallback",
]

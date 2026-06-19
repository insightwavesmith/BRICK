"""Engine-entry auto-loader for the operator report/credentials env files (#56).

PROBLEM (operator-proven 0619, RECURRING): the default report policy fans out to
``[local-inbox, slack, dashboard]`` with real slack+dashboard delivery enabled,
but the slack/dashboard sinks are ENVIRONMENT-GATED -- at delivery time they read
their credentials from ``os.environ`` (``BRICK_REPORT_SLACK_BOT_TOKEN`` etc., see
``support/operator/report_sinks.py`` / ``reporter.py``). If those keys are absent
from the building process, the gated sinks are SILENTLY dropped to local-inbox
only and no slack/dashboard notification ever arrives. Today the operator must
manually ``source ~/.brick/report.env`` before every fire, which is fragile
across cwd / sandbox / ``uv run`` re-exec and silently degrades over and over.

FIX: load the allowlisted credential keys from ``~/.brick/report.env`` (and the
optional ``~/.brick/credentials.env``) ONCE at every engine seam a building run
that emits report events passes through (``run_building_plan`` /
``resume_building_plan`` / ``run_building_once`` in ``support/operator/run.py``,
which thread the loaded ``report_env`` into the report-sink gating + delivery).
The env-gated sinks then always see the creds, regardless of how the operator
launched.

INJECTION SCOPE (codex review 0619, MAJOR-5 -- narrowed):
  - REPORT keys (``BRICK_REPORT_*`` / ``BRICK_DASHBOARD_*``) are returned as a
    threaded ``report_env`` mapping and NOT injected into the global
    ``os.environ``. The slack/dashboard sink gating + delivery accept this
    threaded mapping, so the keys never leak into child subprocesses (codex /
    claude / gemini CLIs, ``ps``, ``lsof`` inherit the parent env).
  - PROVIDER keys (``GEMINI_API_KEY`` / ``GOOGLE_API_KEY``) ARE injected into the
    global ``os.environ`` because the gemini adapter reads them DIRECTLY from
    ``os.environ`` (``support/connection/agent_adapter.py``) with no threaded-env
    seam. That child-inheritance is the unavoidable, accepted minimum: only the
    provider key the adapter must see is global.

This module is support operator mechanics only. It reads two well-known operator
files, parses ``export KEY=VALUE`` lines, and loads ONLY a NARROW allowlist of
credential/provider keys. It does NOT choose Movement, judge source truth /
success / quality, create facts, store secrets at rest, change the report
sink/policy delivery logic, or own Brick / Agent / Link meaning. It NEVER prints
or logs a credential value (mask only).

DISCIPLINE (task #56 / P2 design line 109):
  - NARROW allowlist only: ``BRICK_REPORT_*``, ``BRICK_DASHBOARD_*``,
    ``GEMINI_API_KEY``, ``GOOGLE_API_KEY``. A non-allowlisted key in the file is
    never loaded (no blanket ``os.environ.update``).
  - 0600 PERMISSION GATE: if the file is group- or world-readable, REFUSE to load
    it (do not silently load a loose-perm secret file) and record a typed support
    observation. No crash. The gate is TOCTOU-safe: the file is opened ONCE by
    fd, the permission check runs on ``os.fstat`` of that fd, and the read uses
    the SAME fd -- the check and the read are tied to one inode (a symlink swap /
    file replace between check and read cannot load an unverified file).
  - ENV PRECEDENCE: never override a key already present in the target env (the
    operator's explicit env wins). The loaded file only fills gaps.
  - NO VALUE ECHO: observations and the returned summary carry key NAMES and a
    masked placeholder only -- never a credential value.
  - GRACEFUL: an absent file is a silent no-op; a malformed line is skipped (with
    a masked typed observation), never a crash.

stdlib only; no new dependencies.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path


# The NARROW credential/provider allowlist. EXACT names + the two BRICK_*
# credential prefixes. Anything outside this is never loaded from the file.
ALLOWED_ENV_PREFIXES: tuple[str, ...] = ("BRICK_REPORT_", "BRICK_DASHBOARD_")
ALLOWED_ENV_EXACT: frozenset[str] = frozenset({"GEMINI_API_KEY", "GOOGLE_API_KEY"})

# INJECTION SCOPE split (codex review 0619, MAJOR-5). The allowlist above governs
# what is loaded AT ALL; this split governs WHERE a loaded key lands:
#   - REPORT keys (the two BRICK_* prefixes) are threaded as a report_env mapping
#     and are NOT injected into the global os.environ -- the report sinks accept
#     the threaded mapping, so these never leak to child subprocesses.
#   - PROVIDER keys (GEMINI_API_KEY / GOOGLE_API_KEY) ARE injected into os.environ
#     because the gemini adapter reads them directly from os.environ with no
#     threaded-env seam. This is the unavoidable, accepted child-inheritance.
REPORT_ENV_PREFIXES: tuple[str, ...] = ("BRICK_REPORT_", "BRICK_DASHBOARD_")
PROVIDER_ENV_EXACT: frozenset[str] = frozenset({"GEMINI_API_KEY", "GOOGLE_API_KEY"})

# The two operator env files, in load order. report.env is the primary
# slack/dashboard/provider credential file; credentials.env is an optional
# secondary file (same format, same allowlist) that may not exist.
DEFAULT_REPORT_ENV_PATH = Path("~/.brick/report.env")
DEFAULT_CREDENTIALS_ENV_PATH = Path("~/.brick/credentials.env")

# The required mode: owner read/write only (0600). Any group or other permission
# bit set means the secret file is loosely permissioned and we refuse to load it.
_LOOSE_PERMISSION_MASK = stat.S_IRWXG | stat.S_IRWXO  # 0o077

PROOF_LIMIT = (
    "proof limit: runtime env auto-loader support evidence only; it does not "
    "prove source truth, success judgment, quality judgment, Movement authority, "
    "provider behavior, or that a credential is valid -- it only injects the "
    "allowlisted credential KEYS into the process env so the env-gated report "
    "sinks can read them."
)


@dataclass(frozen=True)
class RuntimeEnvLoadResult:
    """Support evidence of one runtime-env load pass. Carries NO secret values."""

    loaded_keys: tuple[str, ...] = ()
    skipped_already_set_keys: tuple[str, ...] = ()
    skipped_non_allowlisted_keys: tuple[str, ...] = ()
    refused_files: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()


def _is_allowlisted_key(key: str) -> bool:
    return key in ALLOWED_ENV_EXACT or any(key.startswith(p) for p in ALLOWED_ENV_PREFIXES)


def _is_report_key(key: str) -> bool:
    """True iff this allowlisted key is a REPORT key (threaded, not os.environ)."""

    return any(key.startswith(p) for p in REPORT_ENV_PREFIXES)


def _is_provider_key(key: str) -> bool:
    """True iff this allowlisted key is a PROVIDER key (injected into os.environ)."""

    return key in PROVIDER_ENV_EXACT


def _parse_export_line(line: str) -> tuple[str, str] | None:
    """Parse one ``export KEY=VALUE`` (or ``KEY=VALUE``) line.

    Returns ``(key, value)`` or ``None`` for a blank / comment / non-assignment
    line. Strips an optional leading ``export``, surrounding whitespace, and a
    single matched pair of surrounding single/double quotes around the value.
    Never raises -- a malformed line is reported as ``None`` so the caller can
    skip it gracefully.
    """

    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export ") or stripped.startswith("export\t"):
        stripped = stripped[len("export"):].strip()
    if "=" not in stripped:
        return None
    key, _, raw_value = stripped.partition("=")
    key = key.strip()
    if not key:
        return None
    # A bare key with whitespace is not a valid shell identifier; reject it.
    if any(ch.isspace() for ch in key):
        return None
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return key, value


def _file_is_loose_permissioned(mode: int) -> bool:
    """True iff the file mode has any group/other permission bit set (not 0600-tight).

    TOCTOU-SAFE (codex review 0619, MINOR-2): the ``mode`` MUST come from an
    ``os.fstat`` on an OPEN fd (see ``_read_tight_env_file_by_fd``), not a
    ``path.stat()`` on a name that may be re-resolved before the read. The check
    and the read are then tied to the same inode.
    """

    return bool(stat.S_IMODE(mode) & _LOOSE_PERMISSION_MASK)


def _read_tight_env_file_by_fd(
    path: Path,
    *,
    accumulator: "_LoadAccumulator",
) -> str | None:
    """Open ``path`` once by fd, refuse loose perms, and read from the SAME fd.

    TOCTOU-SAFE: ``os.open(O_RDONLY | O_NOFOLLOW)`` opens the file by name a single
    time (``O_NOFOLLOW`` refuses a symlink at the final path component);
    ``os.fstat(fd)`` reads the mode of THAT fd's inode for the 0600 permission
    gate; the content is read from the SAME fd. A symlink swap or file replace
    between the permission check and the read cannot redirect the read to an
    unverified inode, because both operate on the one open descriptor.

    Returns the file text on success, or ``None`` (with a typed accumulator
    observation / refusal recorded) when the file is absent, a symlink, loosely
    permissioned, or unreadable. Never raises. Never echoes a value.
    """

    display = str(path)
    open_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, open_flags)
    except FileNotFoundError:
        return None  # GRACEFUL: absent file -> silent no-op.
    except OSError as exc:
        # ELOOP here means the final path component is a symlink (O_NOFOLLOW); any
        # other OSError is an open failure. Either way: refuse, record, no crash.
        accumulator.observations.append(
            f"observation: could not open {display}: {exc.__class__.__name__} "
            "(no keys loaded from this file; a symlinked secret file is refused)"
        )
        return None
    try:
        try:
            file_stat = os.fstat(fd)
        except OSError as exc:
            accumulator.observations.append(
                f"observation: could not fstat {display}: {exc.__class__.__name__} "
                "(no keys loaded from this file)"
            )
            return None
        # Refuse anything that is not a regular file (fifo/device/dir opened by
        # name) -- the operator's secret file is a plain 0600 file.
        if not stat.S_ISREG(file_stat.st_mode):
            accumulator.refused_files.append(display)
            accumulator.observations.append(
                f"observation: refused to load {display}: not a regular file "
                "(no keys loaded from this file)"
            )
            return None
        if _file_is_loose_permissioned(file_stat.st_mode):
            accumulator.refused_files.append(display)
            # NO VALUE ECHO: octal mode only, never any file content.
            accumulator.observations.append(
                f"observation: refused to load {display}: loose permissions "
                f"{oct(stat.S_IMODE(file_stat.st_mode))} (group/other readable); "
                f"expected 0600 -- run `chmod 600 {display}` (no keys loaded from "
                "this file)"
            )
            return None
        try:
            # Read from the SAME fd the permission check ran on. os.read in a loop
            # up to the fstat size + a small slack drains the regular file fully.
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks).decode("utf-8")
        except OSError as exc:
            accumulator.observations.append(
                f"observation: could not read {display}: {exc.__class__.__name__} "
                "(no keys loaded from this file)"
            )
            return None
        except UnicodeDecodeError:
            accumulator.observations.append(
                f"observation: could not decode {display} as utf-8 "
                "(no keys loaded from this file)"
            )
            return None
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def _load_one_env_file(
    path: Path,
    *,
    environ: dict[str, str],
    accumulator: "_LoadAccumulator",
) -> None:
    """Inject the allowlisted keys from one env file into ``environ`` in place.

    Honors the 0600 gate (TOCTOU-safe, fd-tied), the allowlist, env precedence,
    and the no-echo rule. An absent file is a silent no-op. Never raises on a
    malformed file.
    """

    text = _read_tight_env_file_by_fd(path, accumulator=accumulator)
    if text is None:
        return

    display = str(path)
    for raw_line in text.splitlines():
        parsed = _parse_export_line(raw_line)
        if parsed is None:
            # Blank/comment/non-assignment lines are normal; only a non-empty,
            # non-comment line that failed to parse is worth a masked note.
            candidate = raw_line.strip()
            if candidate and not candidate.startswith("#"):
                accumulator.observations.append(
                    f"observation: skipped unparseable line in {display} "
                    "(masked; not an export KEY=VALUE assignment)"
                )
            continue
        key, value = parsed
        if not _is_allowlisted_key(key):
            # NON-ALLOWLISTED: never load. Record the key NAME only (the env
            # files are operator-owned and key names are not the secret).
            if key not in accumulator.skipped_non_allowlisted:
                accumulator.skipped_non_allowlisted.append(key)
            continue
        if key in environ:
            # ENV PRECEDENCE: the operator's explicit env wins; never override.
            if key not in accumulator.skipped_already_set:
                accumulator.skipped_already_set.append(key)
            continue
        environ[key] = value
        if key not in accumulator.loaded:
            accumulator.loaded.append(key)


@dataclass
class _LoadAccumulator:
    loaded: list[str] = field(default_factory=list)
    skipped_already_set: list[str] = field(default_factory=list)
    skipped_non_allowlisted: list[str] = field(default_factory=list)
    refused_files: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)


def load_runtime_env_files(
    paths: Sequence[Path | str] | None = None,
    *,
    environ: dict[str, str] | None = None,
) -> RuntimeEnvLoadResult:
    """Inject the allowlisted credential keys from the operator env files.

    Loads ``~/.brick/report.env`` then the optional ``~/.brick/credentials.env``
    (or the supplied ``paths``) into ``environ`` (default: the live
    ``os.environ``). Returns support evidence carrying KEY NAMES only -- never a
    credential value. See the module docstring for the full discipline.

    This is the single engine-entry seam. It is idempotent: a second call sees
    the keys already present (env precedence) and loads nothing new.
    """

    target_paths: list[Path]
    if paths is None:
        target_paths = [
            DEFAULT_REPORT_ENV_PATH.expanduser(),
            DEFAULT_CREDENTIALS_ENV_PATH.expanduser(),
        ]
    else:
        target_paths = [Path(p).expanduser() for p in paths]

    env = os.environ if environ is None else environ

    accumulator = _LoadAccumulator()
    for path in target_paths:
        _load_one_env_file(path, environ=env, accumulator=accumulator)

    return RuntimeEnvLoadResult(
        loaded_keys=tuple(accumulator.loaded),
        skipped_already_set_keys=tuple(accumulator.skipped_already_set),
        skipped_non_allowlisted_keys=tuple(accumulator.skipped_non_allowlisted),
        refused_files=tuple(accumulator.refused_files),
        observations=tuple(accumulator.observations),
    )


def load_report_env_into_process(
    *,
    environ: dict[str, str] | None = None,
) -> dict[str, str]:
    """Engine-seam helper: load the operator env files and return the report_env.

    INJECTION SCOPE (codex review 0619, MAJOR-5 -- narrowed). This is the single
    helper every report-emitting building entry in ``run.py`` calls. It:

      1. loads ``~/.brick/report.env`` (+ optional ``credentials.env``) into a
         FRESH working dict seeded with the allowlisted keys already in the target
         env (env precedence: an operator-exported key always wins);
      2. injects ONLY the PROVIDER keys (``GEMINI_API_KEY`` / ``GOOGLE_API_KEY``)
         into the live ``os.environ`` (filling gaps; never overriding), because
         the gemini adapter reads those DIRECTLY from ``os.environ`` and has no
         threaded-env seam. This is the unavoidable, accepted child-inheritance --
         and ONLY the provider key lands global;
      3. returns the REPORT keys (``BRICK_REPORT_*`` / ``BRICK_DASHBOARD_*``) as a
         ``report_env`` mapping for the caller to THREAD into the slack/dashboard
         sink gating + delivery. These report keys are NOT injected into
         ``os.environ``, so they never leak into child subprocesses.

    The returned mapping carries the report keys' values (the caller threads them
    straight to the sinks, which is their only consumer). Absent files are a
    silent no-op. Idempotent. ``environ`` is for tests only (default os.environ).
    """

    target_environ = os.environ if environ is None else environ

    # (1) Seed a fresh working dict with the allowlisted keys already present in
    # the target env so file values can never override an operator-exported key.
    combined: dict[str, str] = {
        key: value
        for key, value in target_environ.items()
        if _is_allowlisted_key(key)
    }
    load_runtime_env_files(environ=combined)

    # (2) PROVIDER keys: inject into the live os.environ (fill gaps, no override).
    for key, value in combined.items():
        if _is_provider_key(key) and key not in target_environ:
            target_environ[key] = value

    # (3) REPORT keys: returned for threading; NEVER injected into os.environ.
    return {key: value for key, value in combined.items() if _is_report_key(key)}

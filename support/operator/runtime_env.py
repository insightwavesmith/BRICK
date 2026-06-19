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
optional ``~/.brick/credentials.env``) into ``os.environ`` ONCE at the single
narrowest engine seam every building run passes through (``run_building_plan`` /
``resume_building_plan`` in ``support/operator/run.py``). The env-gated sinks then
always see the creds, regardless of how the operator launched.

This module is support operator mechanics only. It reads two well-known operator
files, parses ``export KEY=VALUE`` lines, and injects ONLY a NARROW allowlist of
credential/provider keys into ``os.environ``. It does NOT choose Movement, judge
source truth / success / quality, create facts, store secrets at rest, change the
report sink/policy delivery logic, or own Brick / Agent / Link meaning. It NEVER
prints or logs a credential value (mask only).

DISCIPLINE (task #56 / P2 design line 109):
  - NARROW allowlist only: ``BRICK_REPORT_*``, ``BRICK_DASHBOARD_*``,
    ``GEMINI_API_KEY``, ``GOOGLE_API_KEY``. A non-allowlisted key in the file is
    never loaded (no blanket ``os.environ.update``).
  - 0600 PERMISSION GATE: if the file is group- or world-readable, REFUSE to load
    it (do not silently load a loose-perm secret file) and record a typed support
    observation. No crash.
  - ENV PRECEDENCE: never override a key already present in ``os.environ`` (the
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

    def as_report_env(self) -> dict[str, str]:
        """The keys this load injected, read back from os.environ (masked-safe).

        Returns the freshly-loaded allowlisted keys mapped to their current
        ``os.environ`` value so callers may pass them as a ``report_env`` mapping.
        Keys that were skipped (already set / non-allowlisted) are not included.
        """

        return {key: os.environ[key] for key in self.loaded_keys if key in os.environ}


def _is_allowlisted_key(key: str) -> bool:
    return key in ALLOWED_ENV_EXACT or any(key.startswith(p) for p in ALLOWED_ENV_PREFIXES)


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


def _file_is_loose_permissioned(path: Path) -> bool:
    """True iff the file has any group/other permission bit set (not 0600-tight)."""

    mode = stat.S_IMODE(path.stat().st_mode)
    return bool(mode & _LOOSE_PERMISSION_MASK)


def _load_one_env_file(
    path: Path,
    *,
    environ: dict[str, str],
    accumulator: "_LoadAccumulator",
) -> None:
    """Inject the allowlisted keys from one env file into ``environ`` in place.

    Honors the 0600 gate, the allowlist, env precedence, and the no-echo rule.
    An absent file is a silent no-op. Never raises on a malformed file.
    """

    display = str(path)
    try:
        if not path.is_file():
            return  # GRACEFUL: absent file -> silent no-op.
    except OSError:
        return

    try:
        if _file_is_loose_permissioned(path):
            mode = stat.S_IMODE(path.stat().st_mode)
            accumulator.refused_files.append(display)
            # NO VALUE ECHO: octal mode only, never any file content.
            accumulator.observations.append(
                f"observation: refused to load {display}: loose permissions "
                f"{oct(mode)} (group/other readable); expected 0600 -- run "
                f"`chmod 600 {display}` (no keys loaded from this file)"
            )
            return
    except OSError as exc:
        accumulator.observations.append(
            f"observation: could not stat {display}: {exc.__class__.__name__} "
            "(no keys loaded from this file)"
        )
        return

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        accumulator.observations.append(
            f"observation: could not read {display}: {exc.__class__.__name__} "
            "(no keys loaded from this file)"
        )
        return

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


def load_report_env_into_process() -> dict[str, str]:
    """Engine-seam helper: load the operator env files into the live os.environ.

    Returns the freshly-injected allowlisted keys (masked-safe mapping) so the
    caller may also thread them as a ``report_env`` argument. The primary effect
    is the ``os.environ`` injection, which is what the env-gated slack/dashboard
    sinks read at delivery time. Absent files are a silent no-op.
    """

    result = load_runtime_env_files()
    return result.as_report_env()

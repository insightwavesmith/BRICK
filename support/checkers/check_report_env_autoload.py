#!/usr/bin/env python3
"""Behavioral checker for the report.env engine auto-loader (#56).

ENGINE AUTO-LOADER (0619): the default report policy fans out to
``[local-inbox, slack, dashboard]`` with real delivery enabled, but slack +
dashboard are ENVIRONMENT-GATED sinks -- at delivery time they read their creds
from ``os.environ``. If those keys are absent from the building process the gated
sinks silently degrade to local-inbox only and no slack/dashboard notification
arrives. ``support/operator/runtime_env.py`` loads the NARROW allowlist of
credential keys from ``~/.brick/report.env`` (+ optional ``credentials.env``) at
EVERY report-emitting engine seam (``run_building_plan`` / ``resume_building_plan``
/ ``run_building_once`` in ``support/operator/run.py``). The REPORT keys are
THREADED into the report-sink gating + delivery (not injected into the global
``os.environ`` -> no child-subprocess leak); only the PROVIDER key
(``GEMINI_API_KEY`` / ``GOOGLE_API_KEY``) is injected into ``os.environ`` because
the gemini adapter reads it directly from there.

This checker is support evidence only. It IMPORTS the real loader and EXERCISES it
IN-PROCESS against TEMP env files (never the operator's real ~/.brick files, never
the live os.environ) and asserts the behavioral contract:

  1. an allowlisted key (a fake slack token, a fake dashboard url, GEMINI_API_KEY)
     from a 0600 file is injected into a fresh env dict;
  2. a NON-allowlisted key in the same file is NOT injected (no blanket load);
  3. a 0644 (group/world-readable) file is REFUSED -- no keys loaded, a typed
     support observation recorded;
  4. ENV PRECEDENCE: a key already present in the env dict is preserved (the
     loaded value never overrides it);
  5. NO VALUE ECHO: no credential value appears in the result observations, the
     loaded/skipped key lists, or the masked summary;
  6. NARROWED INJECTION (codex review 0619, MAJOR-5): load_report_env_into_process
     RETURNS the report keys for threading and does NOT inject them into the target
     env; it injects ONLY the provider key (GEMINI/GOOGLE) into the target env;
  7. TOCTOU-SAFE PERM GATE (MINOR-2): the loader opens the file ONCE by fd
     (``os.open`` + ``os.fstat`` perm check on that fd + read from that fd), so a
     symlink at the path (``O_NOFOLLOW``) is refused and the 0644 refusal is tied
     to the open inode -- not a separate ``path.stat()`` re-resolve.

It also runs IN-PROCESS MUTATION-RED probes: with the 0600 permission gate
defeated, the 0644 file would be loaded (RED); with the allowlist widened, the
non-allowlisted key would be loaded (RED); with the report/provider injection
split defeated (all-keys treated as provider), the report key would leak into the
target env (RED). These prove the checker is not vacuously green if the loader
ever loses the gate, widens the allowlist, or re-globalizes the report keys.

It does NOT call providers, run a real CLI, choose Movement, judge source truth,
judge success or quality, classify Building outcomes, or touch the operator's real
credential files or the live process env. NO real credential value exists in this
file (only fake fixture tokens that are not real secrets).
"""

from __future__ import annotations

import argparse
import os
import stat
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]

# Fake fixture values -- NOT real secrets. Used only to assert the loader moves
# the right KEYS and never echoes a VALUE.
_FAKE_SLACK_TOKEN = "xoxb-FAKE-FIXTURE-not-a-real-token-000"
_FAKE_CHANNEL_ID = "C0FAKEFIXTURE"
_FAKE_DASHBOARD_URL = "https://fixture.invalid/ingest"
_FAKE_DASHBOARD_SECRET = "fixture-dashboard-secret-not-real-000"
_FAKE_GEMINI_KEY = "AIzaFAKEFIXTUREkey000"
_NON_ALLOWLISTED_KEY = "BRICK_NOT_A_CREDENTIAL_KEY"
_NON_ALLOWLISTED_VALUE = "fixture-non-allowlisted-value"
_PRESET_TOKEN_VALUE = "operator-explicit-env-wins-fixture"

# Every fake value above; used to prove no value leaks into the result evidence.
_ALL_FIXTURE_VALUES = (
    _FAKE_SLACK_TOKEN,
    _FAKE_CHANNEL_ID,
    _FAKE_DASHBOARD_URL,
    _FAKE_DASHBOARD_SECRET,
    _FAKE_GEMINI_KEY,
    _NON_ALLOWLISTED_VALUE,
    _PRESET_TOKEN_VALUE,
)

PROOF_LIMIT = (
    "proof limit: report.env auto-loader checker support evidence only; it does "
    "not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or that a credential is valid -- it proves the "
    "loader injects only the allowlisted KEYS, refuses a loose-perm file, honors "
    "env precedence, and never echoes a value."
)


class ReportEnvAutoloadError(ValueError):
    """Raised when the report.env auto-loader violates its behavioral contract."""


def _import_loader():
    """Import the real loader module via the import-identity package route."""

    import_root = _REPO_ROOT / "support" / "import_identity"
    for entry in (str(import_root), str(_REPO_ROOT)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    try:
        from brick_protocol.support.operator import runtime_env  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover - surfaced as a RED
        raise ReportEnvAutoloadError(
            f"could not import support/operator/runtime_env.py: {exc}"
        ) from exc
    return runtime_env


def _import_reporter():
    """Import the real reporter module (for the sink-gating readiness assertion)."""

    import_root = _REPO_ROOT / "support" / "import_identity"
    for entry in (str(import_root), str(_REPO_ROOT)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    try:
        from brick_protocol.support.operator import reporter  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover - surfaced as a RED
        raise ReportEnvAutoloadError(
            f"could not import support/operator/reporter.py: {exc}"
        ) from exc
    return reporter


def _write_env_file(directory: Path, name: str, lines: Sequence[str], *, mode: int) -> Path:
    path = directory / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(path, mode)
    return path


def _report_env_fixture_lines() -> list[str]:
    return [
        "# fixture report.env (NOT a real secret)",
        f"export BRICK_REPORT_SLACK_BOT_TOKEN={_FAKE_SLACK_TOKEN}",
        f'export BRICK_REPORT_SLACK_CHANNEL_ID="{_FAKE_CHANNEL_ID}"',
        f"export BRICK_DASHBOARD_INGEST_URL={_FAKE_DASHBOARD_URL}",
        f"export GEMINI_API_KEY={_FAKE_GEMINI_KEY}",
        f"export {_NON_ALLOWLISTED_KEY}={_NON_ALLOWLISTED_VALUE}",
        "",
    ]


def _assert_no_value_echo(result, label: str) -> None:
    """No credential VALUE may appear anywhere in the support evidence."""

    haystack_parts: list[str] = []
    haystack_parts.extend(result.loaded_keys)
    haystack_parts.extend(result.skipped_already_set_keys)
    haystack_parts.extend(result.skipped_non_allowlisted_keys)
    haystack_parts.extend(result.refused_files)
    haystack_parts.extend(result.observations)
    haystack = "\n".join(haystack_parts)
    for value in _ALL_FIXTURE_VALUES:
        if value in haystack:
            raise ReportEnvAutoloadError(
                f"{label}: a credential VALUE leaked into the loader's support "
                "evidence (no-echo rule violated)"
            )


def _check_allowlist_injection_and_precedence(runtime_env, tmp: Path) -> list[str]:
    report_path = _write_env_file(tmp, "report.env", _report_env_fixture_lines(), mode=0o600)

    # A FRESH env dict (never the live os.environ) with one key PRE-SET to prove
    # env precedence: the loaded report.env value must NOT override it.
    fresh_env: dict[str, str] = {"BRICK_REPORT_SLACK_BOT_TOKEN": _PRESET_TOKEN_VALUE}

    result = runtime_env.load_runtime_env_files([report_path], environ=fresh_env)

    loaded = set(result.loaded_keys)
    # (1) allowlisted keys (the not-already-set ones) are injected.
    for key in ("BRICK_REPORT_SLACK_CHANNEL_ID", "BRICK_DASHBOARD_INGEST_URL", "GEMINI_API_KEY"):
        if key not in loaded:
            raise ReportEnvAutoloadError(
                f"allowlisted key {key} was not injected into the fresh env"
            )
        if fresh_env.get(key) is None:
            raise ReportEnvAutoloadError(
                f"allowlisted key {key} missing from the fresh env after load"
            )
    # (2) the non-allowlisted key is NOT injected.
    if _NON_ALLOWLISTED_KEY in fresh_env:
        raise ReportEnvAutoloadError(
            f"non-allowlisted key {_NON_ALLOWLISTED_KEY} was injected (blanket load leak)"
        )
    if _NON_ALLOWLISTED_KEY in loaded:
        raise ReportEnvAutoloadError(
            f"non-allowlisted key {_NON_ALLOWLISTED_KEY} appears in loaded_keys"
        )
    if _NON_ALLOWLISTED_KEY not in set(result.skipped_non_allowlisted_keys):
        raise ReportEnvAutoloadError(
            f"non-allowlisted key {_NON_ALLOWLISTED_KEY} not reported as skipped"
        )
    # (4) ENV PRECEDENCE: the pre-set key is preserved, not overridden.
    if fresh_env["BRICK_REPORT_SLACK_BOT_TOKEN"] != _PRESET_TOKEN_VALUE:
        raise ReportEnvAutoloadError(
            "env precedence violated: a pre-set key was overridden by the loaded file"
        )
    if "BRICK_REPORT_SLACK_BOT_TOKEN" in loaded:
        raise ReportEnvAutoloadError(
            "env precedence violated: a pre-set key appears in loaded_keys"
        )
    if "BRICK_REPORT_SLACK_BOT_TOKEN" not in set(result.skipped_already_set_keys):
        raise ReportEnvAutoloadError(
            "pre-set key not reported as skipped_already_set"
        )
    # (5) no value echo anywhere.
    _assert_no_value_echo(result, "allowlist+precedence")

    return [
        "allowlist+precedence green: allowlisted keys "
        "{BRICK_REPORT_SLACK_CHANNEL_ID, BRICK_DASHBOARD_INGEST_URL, GEMINI_API_KEY} "
        "injected; non-allowlisted key NOT injected; pre-set "
        "BRICK_REPORT_SLACK_BOT_TOKEN preserved (operator env wins); no value echoed.",
    ]


def _check_loose_permission_refusal(runtime_env, tmp: Path) -> list[str]:
    loose_path = _write_env_file(
        tmp,
        "report-loose.env",
        [f"export BRICK_REPORT_SLACK_BOT_TOKEN={_FAKE_SLACK_TOKEN}"],
        mode=0o644,
    )
    fresh_env: dict[str, str] = {}
    result = runtime_env.load_runtime_env_files([loose_path], environ=fresh_env)

    # (3) a 0644 file is REFUSED -- no keys loaded.
    if result.loaded_keys:
        raise ReportEnvAutoloadError(
            "a group/world-readable (0644) env file was loaded; the 0600 "
            "permission gate did not refuse it"
        )
    if fresh_env:
        raise ReportEnvAutoloadError(
            "a 0644 env file leaked a key into the env; the 0600 gate failed"
        )
    if str(loose_path) not in set(result.refused_files):
        raise ReportEnvAutoloadError(
            "a 0644 env file was not recorded in refused_files"
        )
    if not any("loose permissions" in obs for obs in result.observations):
        raise ReportEnvAutoloadError(
            "a 0644 env file did not record a typed loose-permission observation"
        )
    _assert_no_value_echo(result, "loose-permission-refusal")

    return [
        "loose-permission-refusal green: a 0644 (group/world-readable) env file is "
        "REFUSED -- no keys loaded, a typed loose-permission observation recorded, "
        "no value echoed.",
    ]


def _check_absent_file_noop(runtime_env, tmp: Path) -> list[str]:
    absent = tmp / "does-not-exist.env"
    fresh_env: dict[str, str] = {}
    result = runtime_env.load_runtime_env_files([absent], environ=fresh_env)
    if result.loaded_keys or result.refused_files or fresh_env:
        raise ReportEnvAutoloadError(
            "an absent env file was not a silent no-op"
        )
    return [
        "absent-file-noop green: a missing env file is a silent no-op "
        "(no keys loaded, no refusal, no crash).",
    ]


def _narrowed_report_env_fixture_lines() -> list[str]:
    """A full slack+dashboard+provider 0600 fixture (no non-allowlisted key)."""

    return [
        "# fixture report.env (NOT a real secret)",
        f"export BRICK_REPORT_SLACK_BOT_TOKEN={_FAKE_SLACK_TOKEN}",
        f"export BRICK_REPORT_SLACK_CHANNEL_ID={_FAKE_CHANNEL_ID}",
        f"export BRICK_DASHBOARD_INGEST_URL={_FAKE_DASHBOARD_URL}",
        f"export BRICK_DASHBOARD_INGEST_SECRET={_FAKE_DASHBOARD_SECRET}",
        f"export GEMINI_API_KEY={_FAKE_GEMINI_KEY}",
        "",
    ]


def _check_narrowed_injection_scope(runtime_env, tmp: Path) -> list[str]:
    """MAJOR-5: report keys are RETURNED (threaded), NOT injected into the env.

    ``load_report_env_into_process`` must:
      - return the BRICK_REPORT_* / BRICK_DASHBOARD_* keys as the threaded mapping;
      - NOT inject any report key into the target env (no child-subprocess leak);
      - inject ONLY the provider key (GEMINI/GOOGLE) into the target env;
      - NOT return the provider key in the threaded mapping (sinks don't need it).

    It also asserts the threaded mapping makes the report-sink gating READY while
    the target env alone is NOT ready -- proving delivery rides the threaded
    mapping, not a global os.environ fallback.
    """

    report_path = _write_env_file(
        tmp, "report-narrow.env", _narrowed_report_env_fixture_lines(), mode=0o600
    )
    orig_report = runtime_env.DEFAULT_REPORT_ENV_PATH
    orig_creds = runtime_env.DEFAULT_CREDENTIALS_ENV_PATH
    runtime_env.DEFAULT_REPORT_ENV_PATH = report_path
    runtime_env.DEFAULT_CREDENTIALS_ENV_PATH = tmp / "absent-credentials.env"
    target_env: dict[str, str] = {}
    try:
        report_env = runtime_env.load_report_env_into_process(environ=target_env)
    finally:
        runtime_env.DEFAULT_REPORT_ENV_PATH = orig_report
        runtime_env.DEFAULT_CREDENTIALS_ENV_PATH = orig_creds

    report_keys = {
        "BRICK_REPORT_SLACK_BOT_TOKEN",
        "BRICK_REPORT_SLACK_CHANNEL_ID",
        "BRICK_DASHBOARD_INGEST_URL",
        "BRICK_DASHBOARD_INGEST_SECRET",
    }
    # Report keys are returned for threading.
    for key in report_keys:
        if key not in report_env:
            raise ReportEnvAutoloadError(
                f"narrowed-injection: report key {key} missing from the threaded "
                "report_env mapping"
            )
        # ...and must NOT have leaked into the target (os.environ-proxy) env.
        if key in target_env:
            raise ReportEnvAutoloadError(
                f"narrowed-injection: report key {key} LEAKED into the target env "
                "(child-subprocess leak); it must be threaded only"
            )
    # Provider key is injected into the target env, NOT returned for threading.
    if target_env.get("GEMINI_API_KEY") != _FAKE_GEMINI_KEY:
        raise ReportEnvAutoloadError(
            "narrowed-injection: provider key GEMINI_API_KEY was not injected into "
            "the target env (the gemini adapter reads it from os.environ)"
        )
    if "GEMINI_API_KEY" in report_env:
        raise ReportEnvAutoloadError(
            "narrowed-injection: provider key GEMINI_API_KEY appears in the threaded "
            "report_env (the report sinks do not consume provider keys)"
        )
    # The threaded mapping makes the report-sink gating READY; the target env
    # alone (report keys absent) is NOT ready -- delivery rides the threaded map.
    reporter = _import_reporter()
    if not reporter._slack_environment_ready(report_env):
        raise ReportEnvAutoloadError(
            "narrowed-injection: threaded report_env did not make slack gating ready "
            "(delivery would silently drop)"
        )
    if not reporter._dashboard_environment_ready(report_env):
        raise ReportEnvAutoloadError(
            "narrowed-injection: threaded report_env did not make dashboard gating "
            "ready"
        )
    if reporter._slack_environment_ready(target_env):
        raise ReportEnvAutoloadError(
            "narrowed-injection: slack gating was ready from the target env alone -- "
            "a report key leaked into os.environ"
        )
    # No value echo across the threaded mapping is implicit (values ARE the
    # threaded payload), but the loader's own observations must still not echo.
    return [
        "narrowed-injection green: report keys {BRICK_REPORT_*, BRICK_DASHBOARD_*} "
        "are RETURNED for threading and NOT injected into the target env; only the "
        "provider key GEMINI_API_KEY is injected into the target env; the threaded "
        "report_env makes slack+dashboard gating READY while the target env alone "
        "is NOT ready (delivery rides the threaded mapping, not a global fallback).",
    ]


def _check_fd_tied_permission_gate(runtime_env, tmp: Path) -> list[str]:
    """MINOR-2 (TOCTOU): the perm check + read are tied to ONE open fd.

    Asserts the loader exposes the fd-tied reader, that a SYMLINK at the path is
    refused (O_NOFOLLOW), and that a 0644 regular file is refused via the
    fstat-on-fd permission check (no separate path.stat re-resolve).
    """

    if not hasattr(runtime_env, "_read_tight_env_file_by_fd"):
        raise ReportEnvAutoloadError(
            "TOCTOU: the loader does not expose _read_tight_env_file_by_fd (the "
            "fd-tied open+fstat+read path); the perm check may still be a separate "
            "path.stat() that re-resolves before the read"
        )

    # The fd-tied reader's perm predicate takes a MODE from fstat (not a Path),
    # proving the check rides the open fd, not a name re-stat.
    import inspect

    sig = inspect.signature(runtime_env._file_is_loose_permissioned)
    params = list(sig.parameters)
    if params != ["mode"]:
        raise ReportEnvAutoloadError(
            "TOCTOU: _file_is_loose_permissioned must take a single `mode` int "
            "(from os.fstat on the open fd), not a Path that re-resolves; got "
            f"params {params}"
        )

    # (a) a SYMLINK at the path is refused (O_NOFOLLOW): no value read.
    real = _write_env_file(
        tmp, "fd-real.env", [f"export BRICK_REPORT_SLACK_BOT_TOKEN={_FAKE_SLACK_TOKEN}"], mode=0o600
    )
    link = tmp / "fd-link.env"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(real)
    acc = runtime_env._LoadAccumulator()
    text = runtime_env._read_tight_env_file_by_fd(link, accumulator=acc)
    if text is not None:
        raise ReportEnvAutoloadError(
            "TOCTOU: a SYMLINK env file was followed and read; O_NOFOLLOW did not "
            "refuse it"
        )
    if not any(("symlink" in obs) or ("could not open" in obs) for obs in acc.observations):
        raise ReportEnvAutoloadError(
            "TOCTOU: a symlinked env file did not record a typed open-refusal "
            "observation"
        )

    # (b) a 0644 regular file is refused via the fstat-on-fd permission check.
    loose = _write_env_file(
        tmp, "fd-loose.env", [f"export BRICK_REPORT_SLACK_BOT_TOKEN={_FAKE_SLACK_TOKEN}"], mode=0o644
    )
    acc2 = runtime_env._LoadAccumulator()
    text2 = runtime_env._read_tight_env_file_by_fd(loose, accumulator=acc2)
    if text2 is not None:
        raise ReportEnvAutoloadError(
            "TOCTOU: a 0644 regular env file was read through the fd-tied path; the "
            "fstat-on-fd permission gate did not refuse it"
        )
    if str(loose) not in set(acc2.refused_files):
        raise ReportEnvAutoloadError(
            "TOCTOU: a 0644 file refused via the fd path was not recorded in "
            "refused_files"
        )

    return [
        "fd-tied-perm green: the loader opens the file ONCE by fd "
        "(os.open + os.fstat perm check + read from that fd); a SYMLINK at the path "
        "is refused (O_NOFOLLOW) and a 0644 regular file is refused via fstat-on-fd "
        "-- the check and the read are tied to one inode (no TOCTOU re-resolve).",
    ]


def _check_mutation_red_fd_permission_gate(runtime_env, tmp: Path) -> str:
    """If the fstat-on-fd perm check is defeated, the 0644 file WOULD be read -> RED.

    Monkeypatches the fd-tied loose-permission predicate to always report 'tight'
    and confirms the SAME 0644 file is then read through the fd path -- proving the
    real fstat-on-fd gate is what blocks it (not some incidental open failure).
    """

    loose = _write_env_file(
        tmp,
        "fd-mutation-perm.env",
        [f"export BRICK_REPORT_SLACK_BOT_TOKEN={_FAKE_SLACK_TOKEN}"],
        mode=0o644,
    )
    original = runtime_env._file_is_loose_permissioned
    try:
        runtime_env._file_is_loose_permissioned = lambda mode: False  # noqa: SLF001
        acc = runtime_env._LoadAccumulator()
        text = runtime_env._read_tight_env_file_by_fd(loose, accumulator=acc)
    finally:
        runtime_env._file_is_loose_permissioned = original
    if text is None:
        raise ReportEnvAutoloadError(
            "mutation RED failed (fd perm gate): with the fstat-on-fd check disabled "
            "the 0644 file was STILL not read, so the behavioral check that the real "
            "fd-tied gate blocks it is vacuous"
        )
    if _FAKE_SLACK_TOKEN not in text:
        raise ReportEnvAutoloadError(
            "mutation RED failed (fd perm gate): the 0644 file was read but its "
            "fixture content is missing"
        )
    return (
        "mutation RED observed (fd perm gate): with the fstat-on-fd check disabled "
        "the 0644 file IS read through the fd path -- the real fstat-on-fd gate is "
        "what refuses the loose-perm file."
    )


def _check_mutation_red_injection_split(runtime_env, tmp: Path) -> str:
    """If the report/provider split collapses, the report key WOULD leak -> RED.

    Monkeypatches ``_is_provider_key`` to classify EVERY key as a provider key (the
    mutation: re-globalizing the report keys) and confirms a report key is then
    injected into the target env -- proving the real split is what keeps the report
    keys threaded-only / out of os.environ.
    """

    report_path = _write_env_file(
        tmp, "report-split-mutation.env", _narrowed_report_env_fixture_lines(), mode=0o600
    )
    orig_report = runtime_env.DEFAULT_REPORT_ENV_PATH
    orig_creds = runtime_env.DEFAULT_CREDENTIALS_ENV_PATH
    original = runtime_env._is_provider_key
    runtime_env.DEFAULT_REPORT_ENV_PATH = report_path
    runtime_env.DEFAULT_CREDENTIALS_ENV_PATH = tmp / "absent-credentials-2.env"
    target_env: dict[str, str] = {}
    try:
        runtime_env._is_provider_key = lambda key: True  # noqa: SLF001
        runtime_env.load_report_env_into_process(environ=target_env)
    finally:
        runtime_env._is_provider_key = original
        runtime_env.DEFAULT_REPORT_ENV_PATH = orig_report
        runtime_env.DEFAULT_CREDENTIALS_ENV_PATH = orig_creds
    if "BRICK_REPORT_SLACK_BOT_TOKEN" not in target_env:
        raise ReportEnvAutoloadError(
            "mutation RED failed (injection split): with every key classified as a "
            "provider key the report key was STILL not injected into the target env, "
            "so the behavioral check that the real split keeps report keys threaded-"
            "only is vacuous"
        )
    return (
        "mutation RED observed (injection split): with _is_provider_key widened to "
        "all-keys the report key BRICK_REPORT_SLACK_BOT_TOKEN IS injected into the "
        "target env -- the real report/provider split is what keeps report keys "
        "threaded-only (out of os.environ / child subprocesses)."
    )


def _check_mutation_red_permission_gate(runtime_env, tmp: Path) -> str:
    """If the 0600 gate is defeated, a 0644 file WOULD be loaded -> RED.

    Monkeypatches the loader's loose-permission predicate to always report
    'tight' (the mutation: dropping the 0600 check) and confirms the SAME loose
    file is then loaded -- proving the real gate is what blocks it.
    """

    loose_path = _write_env_file(
        tmp,
        "report-mutation-perm.env",
        [f"export BRICK_REPORT_SLACK_BOT_TOKEN={_FAKE_SLACK_TOKEN}"],
        mode=0o644,
    )
    original = runtime_env._file_is_loose_permissioned
    try:
        # The predicate now takes a MODE int from os.fstat on the open fd.
        runtime_env._file_is_loose_permissioned = lambda mode: False  # noqa: SLF001
        fresh_env: dict[str, str] = {}
        result = runtime_env.load_runtime_env_files([loose_path], environ=fresh_env)
    finally:
        runtime_env._file_is_loose_permissioned = original
    if "BRICK_REPORT_SLACK_BOT_TOKEN" not in fresh_env:
        raise ReportEnvAutoloadError(
            "mutation RED failed (permission gate): with the 0600 check disabled "
            "the loose file was STILL not loaded, so the behavioral check that the "
            "real gate blocks it is vacuous"
        )
    if result.refused_files:
        raise ReportEnvAutoloadError(
            "mutation RED failed (permission gate): refusal still fired with the "
            "gate disabled"
        )
    return (
        "mutation RED observed (permission gate): with the 0600 check disabled the "
        "0644 file IS loaded -- the real gate is what refuses the loose-perm file."
    )


def _check_mutation_red_allowlist(runtime_env, tmp: Path) -> str:
    """If the allowlist is widened to allow-all, the non-allowlisted key WOULD load -> RED.

    Monkeypatches the loader's allowlist predicate to accept every key (the
    mutation: widening the allowlist) and confirms the non-allowlisted key is then
    injected -- proving the real allowlist is what excludes it.
    """

    report_path = _write_env_file(tmp, "report-mutation-allow.env", _report_env_fixture_lines(), mode=0o600)
    original = runtime_env._is_allowlisted_key
    try:
        runtime_env._is_allowlisted_key = lambda key: True  # noqa: SLF001
        fresh_env: dict[str, str] = {}
        runtime_env.load_runtime_env_files([report_path], environ=fresh_env)
    finally:
        runtime_env._is_allowlisted_key = original
    if _NON_ALLOWLISTED_KEY not in fresh_env:
        raise ReportEnvAutoloadError(
            "mutation RED failed (allowlist): with the allowlist widened to "
            "allow-all the non-allowlisted key was STILL not loaded, so the "
            "behavioral check that the real allowlist excludes it is vacuous"
        )
    return (
        "mutation RED observed (allowlist): with the allowlist widened to allow-all "
        f"the non-allowlisted key {_NON_ALLOWLISTED_KEY} IS loaded -- the real "
        "allowlist is what excludes it."
    )


def _function_calls(func_node: "ast.AST") -> set[str]:
    """The set of simple-name call targets made anywhere inside a function node."""

    import ast

    names: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, ast.Attribute):
                names.add(target.attr)
    return names


def _assert_seam_wires_loader(repo: Path) -> str:
    """SEAM COMPLETENESS (MAJOR-6): every report-emitting building entry in run.py
    crosses ``load_report_env_into_process``.

    AST-scans ``support/operator/run.py`` and finds the report-emitting building
    entries -- the public/top-level functions that DERIVE the report policy
    (``report_event_policy_from_plan``) and/or thread ``report_env`` straight into
    the dynamic walker. Each such entry MUST also call
    ``load_report_env_into_process`` in its own body (so the threaded report_env is
    real and the env-gated sinks deliver). A report-emitting entry that does NOT
    cross the loader is the exact MAJOR-6 gap and fails the checker.
    """

    import ast

    run_path = repo / "support" / "operator" / "run.py"
    try:
        text = run_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReportEnvAutoloadError(f"could not read support/operator/run.py: {exc}") from exc
    if "load_report_env_into_process" not in text:
        raise ReportEnvAutoloadError(
            "support/operator/run.py does not call load_report_env_into_process "
            "(the engine seam is not wired)"
        )
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:  # pragma: no cover - surfaced as a RED
        raise ReportEnvAutoloadError(
            f"could not parse support/operator/run.py: {exc}"
        ) from exc

    # The building-execution entry points whose body emits report events (or hands
    # report_env to the walker that does). These are the entries that MUST cross
    # the loader. Each is matched by function name and verified by its call set.
    required_entries = {
        "run_building_once",
        "run_building_plan",
        "resume_building_plan",
    }
    seen: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in required_entries:
            seen[node.name] = _function_calls(node)

    missing_entry = sorted(required_entries - set(seen))
    if missing_entry:
        raise ReportEnvAutoloadError(
            "seam-completeness: run.py is missing the expected report-emitting "
            f"building entr(y/ies) {missing_entry} -- the checker's seam map is "
            "stale or an entry was renamed; re-anchor it"
        )

    not_crossing = sorted(
        name for name, calls in seen.items()
        if "load_report_env_into_process" not in calls
    )
    if not_crossing:
        raise ReportEnvAutoloadError(
            "seam-completeness (MAJOR-6): the report-emitting building entr(y/ies) "
            f"{not_crossing} in run.py emit report events but do NOT call "
            "load_report_env_into_process -- those paths stay slack/dashboard-"
            "silent (the report_env is never threaded). Cross the loader in each."
        )

    # Each crossing entry must also actually be report-emitting: it either derives
    # the report policy directly (run_building_once) or dispatches to a walker that
    # threads report_env and emits (run_building_plan -> _run_dynamic_graph_walker;
    # resume_building_plan -> _resume_dynamic_graph_walker /
    # _resume_chat_session_parked_building_plan). This keeps the seam map from
    # drifting to non-emitting helpers.
    emit_evidence_calls = {
        "report_event_policy_from_plan",
        "_run_dynamic_graph_walker",
        "_resume_dynamic_graph_walker",
        "_resume_chat_session_parked_building_plan",
    }
    for name, calls in seen.items():
        if not (calls & emit_evidence_calls):
            raise ReportEnvAutoloadError(
                f"seam-completeness: {name} is in the required-entry map but neither "
                "derives the report policy nor dispatches a report-emitting walker; "
                "the seam map is mis-anchored"
            )

    return (
        "seam-completeness green (MAJOR-6): every report-emitting building entry in "
        f"run.py {sorted(seen)} crosses load_report_env_into_process before emitting "
        "(run_building_once on its own; run/resume_building_plan thread report_env "
        "into the walker that emits)."
    )


def check(repo: Path) -> list[str]:
    runtime_env = _import_loader()
    outputs: list[str] = ["report.env auto-loader behavioral checker green:"]
    with tempfile.TemporaryDirectory(prefix="report-env-autoload-check-") as tmp_name:
        tmp = Path(tmp_name)
        outputs.extend(_check_allowlist_injection_and_precedence(runtime_env, tmp))
        outputs.extend(_check_loose_permission_refusal(runtime_env, tmp))
        outputs.extend(_check_absent_file_noop(runtime_env, tmp))
        outputs.extend(_check_narrowed_injection_scope(runtime_env, tmp))
        outputs.extend(_check_fd_tied_permission_gate(runtime_env, tmp))
        outputs.append(_check_mutation_red_permission_gate(runtime_env, tmp))
        outputs.append(_check_mutation_red_allowlist(runtime_env, tmp))
        outputs.append(_check_mutation_red_fd_permission_gate(runtime_env, tmp))
        outputs.append(_check_mutation_red_injection_split(runtime_env, tmp))
    outputs.append(_assert_seam_wires_loader(repo))
    outputs.append(PROOF_LIMIT)
    return outputs


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: the report.env engine auto-loader injects "
            "only the allowlisted credential keys, refuses a loose-perm file, "
            "honors env precedence, and never echoes a value (#56)."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except ReportEnvAutoloadError as exc:
        print("report.env auto-loader checker rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

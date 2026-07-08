#!/usr/bin/env python3
"""Behavioral checker for the report.env engine auto-loader (#56).

ENGINE AUTO-LOADER (0619): the default report policy fans out to
``[local-inbox, slack, dashboard]`` with real delivery enabled, but slack +
dashboard are ENVIRONMENT-GATED sinks -- at delivery time they read their creds
from ``os.environ``. If those keys are absent from the building process the gated
sinks silently degrade to local-inbox only and no slack/dashboard notification
arrives. ``brick_protocol/support/operator/runtime_env.py`` loads the NARROW allowlist of
credential keys from ``~/.brick/report.env`` (+ optional ``credentials.env``) at
EVERY report-emitting engine seam (``run_building_plan`` / ``resume_building_plan``
/ ``run_building_once`` in ``brick_protocol/support/operator/run.py``). The REPORT keys are
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
  4. ENV PRECEDENCE: the generic loader preserves a key already present in the
     env dict (the loaded value never overrides it);
  5. NO VALUE ECHO: no credential value appears in the result observations, the
     loaded/skipped key lists, or the masked summary;
  6. NARROWED INJECTION (codex review 0619, MAJOR-5): load_report_env_into_process
     RETURNS the report keys for threading and does NOT inject them into the target
     env; it injects ONLY the provider key (GEMINI/GOOGLE) into the target env,
     and Brick-file provider keys replace stale inherited provider values at the
     engine seam;
  7. TOCTOU-SAFE PERM GATE (MINOR-2): the loader opens the file ONCE by fd
     (``os.open`` + ``os.fstat`` perm check on that fd + read from that fd), so a
     symlink at the path (``O_NOFOLLOW``) is refused and the 0644 refusal is tied
     to the open inode -- not a separate ``path.stat()`` re-resolve.

It ALSO guards the EVROOT2 VESSEL-GATE (slack-wiring-gap 0619). The building-event
emit path runs TWO sequential gates: the #56 ENV gate (does the threaded env carry
slack/dashboard creds?) and a SECOND, independent VESSEL gate
(``_sink_refs_for_building_event_root`` -> ``_building_root_is_real_vessel``) that
strips the external sinks unless the building root is a real vessel. The pre-fix
guard hard-required ``repo == REPO_ROOT`` (the SOURCE worktree), so EVERY building
whose evidence root lives under the EVROOT2 evidence home (~/.brick / $BRICK_HOME)
was mis-classified as a non-vessel and had slack+dashboard silently stripped to
inbox-only -- a strip (delivered=true, no slack line), not a delivery failure. This
checker drives the REAL emit path through BOTH gates against a synthetic EVROOT2
evidence-home building root (TEMP, never the real ~/.brick) and asserts slack +
dashboard SURVIVE for an evidence-home-rooted vessel, while NOT widening: a no-creds
env still drops slack at the env gate, and a garbage / repo-root-mismatched root is
still rejected by the vessel check.

The fix was further NARROWED (slack-wiring-gap 0619, codex adversarial review):
the recognized-home + path-shape checks alone let a caller point the
caller-controlled $BRICK_HOME at a throwaway tree, ``mkdir -p`` an EMPTY
project/<id>/buildings/<id> path, and have that shape-only mimic fire the real
Slack -- because ``project_ref_for_building_root`` verifies only the PATH SHAPE.
So ``_building_root_is_real_vessel`` now also requires real building-spine
evidence (a declared-building-plan with at least one step) before an external sink
survives. This checker pins the narrowing with an EMPTY-MIMIC negative: an empty
path-shape building under the SAME recognized evidence home (no declared plan) is
rejected as a vessel and has slack+dashboard STRIPPED, while the positive fixtures
write a real declared-plan spine so they model a genuine vessel.

It also runs IN-PROCESS MUTATION-RED probes: with the 0600 permission gate
defeated, the 0644 file would be loaded (RED); with the allowlist widened, the
non-allowlisted key would be loaded (RED); with the report/provider injection
split defeated (all-keys treated as provider), the report key would leak into the
target env (RED); and with the pre-fix repo==REPO_ROOT vessel guard reinstated, the
EVROOT2 evidence-home building's slack+dashboard sinks would be stripped to
inbox-only (RED). These prove the checker is not vacuously green if the loader ever
loses the gate, widens the allowlist, re-globalizes the report keys, or the vessel
check regresses to rejecting evidence-home-rooted vessels.

It does NOT call providers, run a real CLI, choose Movement, judge source truth,
judge success or quality, classify Building outcomes, or touch the operator's real
credential files or the live process env. NO real credential value exists in this
file (only fake fixture tokens that are not real secrets).
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)


_REPO_ROOT = Path(__file__).resolve().parents[3]

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
_PRESET_PROVIDER_VALUE = "AIzaSTALEINHERITEDproviderkey000"

# Every fake value above; used to prove no value leaks into the result evidence.
_ALL_FIXTURE_VALUES = (
    _FAKE_SLACK_TOKEN,
    _FAKE_CHANNEL_ID,
    _FAKE_DASHBOARD_URL,
    _FAKE_DASHBOARD_SECRET,
    _FAKE_GEMINI_KEY,
    _NON_ALLOWLISTED_VALUE,
    _PRESET_TOKEN_VALUE,
    _PRESET_PROVIDER_VALUE,
)

PROOF_LIMIT = (
    "proof limit: report.env auto-loader checker support evidence only; it does "
    "not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or that a credential is valid -- it proves the "
    "loader injects only the allowlisted KEYS, refuses a loose-perm file, honors "
    "generic env precedence, applies Brick-file provider-key precedence at the "
    "engine seam, and never echoes a value."
)


class ReportEnvAutoloadError(ValueError):
    """Raised when the report.env auto-loader violates its behavioral contract."""


def _import_loader():
    """Import the real loader module via the import-identity package route."""

    ensure_checker_imports(_REPO_ROOT)
    try:
        from brick_protocol.support.operator import runtime_env  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover - surfaced as a RED
        raise ReportEnvAutoloadError(
            f"could not import brick_protocol/support/operator/runtime_env.py: {exc}"
        ) from exc
    return runtime_env


def _import_reporter():
    """Import the real reporter module (for the sink-gating readiness assertion)."""

    ensure_checker_imports(_REPO_ROOT)
    try:
        from brick_protocol.support.operator import reporter  # noqa: WPS433
    except ImportError as exc:  # pragma: no cover - surfaced as a RED
        raise ReportEnvAutoloadError(
            f"could not import brick_protocol/support/operator/reporter.py: {exc}"
        ) from exc
    return reporter


def _write_declared_plan_spine(building_root: Path) -> None:
    """Write a minimal but REAL declared-building-plan spine at the building root.

    SLACK VESSEL-GATE narrowing (slack-wiring-gap 0619): the vessel predicate now
    requires real building-spine evidence -- a declared plan with at least one
    step -- before an external (slack/dashboard) sink survives. A genuine EVROOT2
    ~/.brick building always writes this; the positive fixtures here must do the
    same so they model a REAL vessel, not an empty path-shape mimic.
    """

    building_root.mkdir(parents=True, exist_ok=True)
    plan = {
        "brick_steps": [
            {
                "completion_edge_ref": "edge:fixture-design-to-fixture-work",
                "rows": [
                    {
                        "axis": "Brick",
                        "brick_instance_ref": "brick-fixture-design",
                        "brick_work_ref": "work:fixture-design",
                    }
                ],
            }
        ]
    }
    (building_root / "declared-building-plan.json").write_text(
        json.dumps(plan), encoding="utf-8"
    )


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
        "BRICK_REPORT_SLACK_BOT_TOKEN preserved by the generic loader; no value echoed.",
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
      - let the Brick env file's provider key replace a stale inherited provider
        value at the engine seam;
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
    target_env: dict[str, str] = {
        "BRICK_REPORT_SLACK_BOT_TOKEN": _PRESET_TOKEN_VALUE,
        "GEMINI_API_KEY": _PRESET_PROVIDER_VALUE,
    }
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
    preexisting_report_keys = {"BRICK_REPORT_SLACK_BOT_TOKEN"}
    # Report keys are returned for threading.
    for key in report_keys:
        if key not in report_env:
            raise ReportEnvAutoloadError(
                f"narrowed-injection: report key {key} missing from the threaded "
                "report_env mapping"
            )
        # ...and must NOT have leaked into the target (os.environ-proxy) env.
        if key in target_env and key not in preexisting_report_keys:
            raise ReportEnvAutoloadError(
                f"narrowed-injection: report key {key} LEAKED into the target env "
                "(child-subprocess leak); it must be threaded only"
            )
    if report_env.get("BRICK_REPORT_SLACK_BOT_TOKEN") != _PRESET_TOKEN_VALUE:
        raise ReportEnvAutoloadError(
            "narrowed-injection: pre-set report key was not preserved in the "
            "threaded report_env mapping"
        )
    # Provider key is injected into the target env, NOT returned for threading.
    if target_env.get("GEMINI_API_KEY") != _FAKE_GEMINI_KEY:
        raise ReportEnvAutoloadError(
            "narrowed-injection: provider key GEMINI_API_KEY was not injected into "
            "the target env from the Brick env file, replacing the stale inherited "
            "provider value (the gemini adapter reads it from os.environ)"
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
        "provider key GEMINI_API_KEY is injected into the target env, with the "
        "Brick env file replacing stale inherited provider values; the threaded "
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


def _check_evroot2_vessel_gate(runtime_env, tmp: Path) -> list[str]:
    """EVROOT2 VESSEL-GATE (slack-wiring-gap 0619): a building whose evidence root
    lives under the EVROOT2 evidence home (~/.brick / $BRICK_HOME), NOT under the
    source worktree REPO_ROOT, must STILL be recognized as a real vessel so the
    env-gated external sinks (slack, dashboard) survive the post-policy vessel gate.

    The live bug: ``emit_building_event_for_policy`` runs TWO sequential gates --
    (1) the #56 ENV gate ``_event_policy_sink_refs`` (slack survives with threaded
    creds), then (2) the VESSEL gate ``_sink_refs_for_building_event_root`` which
    strips slack+dashboard unless ``_building_root_is_real_vessel(repo, root)`` is
    True. The old guard ``if repo != REPO_ROOT: return False`` rejected EVERY
    ~/.brick-rooted building, so slack+dashboard were silently stripped to
    inbox-only -- a strip (delivered=true, no slack line), not a delivery failure,
    exactly matching the live wiki-dogfood-0619 evidence.

    This probe drives the REAL emit path through BOTH gates against a synthetic
    EVROOT2 building root under a TEMP evidence home (never the operator's real
    ~/.brick, never live os.environ) and asserts: with a THREADED report_env
    carrying slack+dashboard creds, the default-policy emit lists slack AND
    dashboard as delivered sinks even though the building root is under the
    evidence home, not REPO_ROOT. It also asserts the gate does NOT widen: a
    no-creds env still drops slack at the env gate, and a non-vessel garbage root
    under the same repo still has external sinks stripped.
    """

    reporter = _import_reporter()

    policy = reporter._default_report_event_policy()  # noqa: SLF001
    # Sanity: the default (omitted) policy fans out to all three sinks and
    # environment-gates slack + dashboard -- the exact shape the bug acts on.
    if reporter.SLACK_SINK_REF not in policy["sink_refs"]:
        raise ReportEnvAutoloadError(
            "evroot2-vessel: the default report policy no longer includes the slack "
            "sink; the vessel-gate pin is mis-anchored"
        )

    threaded_env = {
        "BRICK_REPORT_SLACK_BOT_TOKEN": _FAKE_SLACK_TOKEN,
        "BRICK_REPORT_SLACK_CHANNEL_ID": _FAKE_CHANNEL_ID,
        "BRICK_DASHBOARD_INGEST_URL": _FAKE_DASHBOARD_URL,
        "BRICK_DASHBOARD_INGEST_SECRET": _FAKE_DASHBOARD_SECRET,
    }

    # A synthetic EVROOT2 evidence home + building vessel under a TEMP dir. We
    # point $BRICK_HOME at it so BRICK_EVIDENCE_HOME() (which the vessel check
    # consults) recognizes THIS temp tree as the evidence home -- exactly as the
    # real ~/.brick is recognized in production -- without ever touching the
    # operator's real ~/.brick.
    evidence_home = (tmp / "evroot2-home").resolve()
    root = evidence_home / "project" / "brick-protocol" / "buildings" / "wiki-dogfood-fixture-0619"
    # A REAL vessel writes its declared-plan spine; the narrowing requires it
    # before slack/dashboard survive, so the positive fixture must model the
    # genuine building (not an empty path-shape mkdir).
    _write_declared_plan_spine(root)
    repo = evidence_home

    # Gate 1: ENV gate -- with threaded creds, slack + dashboard survive. This is
    # the gate diagnostic 1 stopped at; it was always intact.
    env_refs = reporter._event_policy_sink_refs(  # noqa: SLF001
        policy, slack_env=threaded_env, dashboard_env=threaded_env
    )
    for ref in (reporter.SLACK_SINK_REF, reporter.DASHBOARD_SINK_REF):
        if ref not in env_refs:
            raise ReportEnvAutoloadError(
                f"evroot2-vessel: the ENV gate dropped {ref} even with threaded "
                "creds -- the #56 threading chain is broken (not the vessel gate)"
            )

    prior_brick_home = os.environ.get("BRICK_HOME")
    os.environ["BRICK_HOME"] = str(evidence_home)
    try:
        event_root = reporter._building_event_root(repo, root)  # noqa: SLF001

        # Gate 2: VESSEL gate -- the bug site. With the fix, the evidence-home
        # vessel is recognized and slack + dashboard SURVIVE; with the bug they are
        # stripped to inbox-only.
        final_refs = reporter._sink_refs_for_building_event_root(  # noqa: SLF001
            env_refs, repo=repo, root=event_root
        )
        if reporter.SLACK_SINK_REF not in final_refs:
            raise ReportEnvAutoloadError(
                "evroot2-vessel REGRESSION: a building whose evidence root is under "
                "the EVROOT2 evidence home (~/.brick / $BRICK_HOME) had its slack sink "
                "STRIPPED by the vessel gate _sink_refs_for_building_event_root even "
                "though the env gate confirmed creds are threaded -- "
                "_building_root_is_real_vessel rejected the evidence-home-rooted "
                "vessel (the slack-wiring-gap bug). Slack would silently degrade to "
                "inbox-only."
            )
        if reporter.DASHBOARD_SINK_REF not in final_refs:
            raise ReportEnvAutoloadError(
                "evroot2-vessel REGRESSION: the dashboard sink was stripped by the "
                "vessel gate for an EVROOT2 evidence-home-rooted building (same root "
                "cause as the slack strip)"
            )

        # Direct vessel-predicate truth on the evidence-home root.
        if not reporter._building_root_is_real_vessel(repo, root):  # noqa: SLF001
            raise ReportEnvAutoloadError(
                "evroot2-vessel REGRESSION: _building_root_is_real_vessel returned "
                "False for a genuine EVROOT2 evidence-home vessel root "
                "<evidence_home>/project/brick-protocol/buildings/<id>"
            )

        # NO WIDENING (1): a no-creds env still drops slack at the ENV gate -- the
        # fix does not bypass the credential check.
        no_creds_refs = reporter._event_policy_sink_refs(  # noqa: SLF001
            policy, slack_env={}, dashboard_env={}
        )
        if reporter.SLACK_SINK_REF in no_creds_refs:
            raise ReportEnvAutoloadError(
                "evroot2-vessel: slack survived the ENV gate with NO creds -- the "
                "vessel fix must not bypass the credential gate"
            )

        # NO WIDENING (2): a non-vessel garbage path under the SAME (recognized
        # home) repo is still not a vessel; external sinks are stripped.
        garbage = evidence_home / "not-a-vessel" / "scratch"
        garbage.mkdir(parents=True, exist_ok=True)
        garbage_root = reporter._building_event_root(repo, garbage)  # noqa: SLF001
        garbage_refs = reporter._sink_refs_for_building_event_root(  # noqa: SLF001
            env_refs, repo=repo, root=garbage_root
        )
        if reporter.SLACK_SINK_REF in garbage_refs or reporter.DASHBOARD_SINK_REF in garbage_refs:
            raise ReportEnvAutoloadError(
                "evroot2-vessel: a non-vessel garbage path was accepted as a real "
                "vessel -- the fix widened the vessel check (external sinks must be "
                "stripped for non-vessel roots)"
            )

        # NO WIDENING (3): a repo/root mismatch (root under the evidence home but
        # repo claimed as the SOURCE REPO_ROOT) derives project_ref=None and is
        # rejected.
        if reporter._building_root_is_real_vessel(reporter.REPO_ROOT, root):  # noqa: SLF001
            raise ReportEnvAutoloadError(
                "evroot2-vessel: a repo/root mismatch (evidence-home root claimed "
                "under the source REPO_ROOT) was accepted as a vessel -- the "
                "path-membership check is not enforcing that root is under the GIVEN "
                "repo"
            )

        # NO WIDENING (4) -- the CRITICAL non-widening guard: an UNRECOGNIZED repo
        # that merely carries the project/<id>/buildings path shape (a throwaway
        # dir that is NEITHER the source REPO_ROOT NOR the evidence home) is NOT a
        # real vessel. This is the property the original repo==REPO_ROOT equality
        # guard protected; the fix must keep it. Here BRICK_HOME points at
        # ``evidence_home``, so a SIBLING temp tree with the same layout is an
        # unrecognized home.
        stranger_home = (tmp / "stranger-not-a-home").resolve()
        stranger_root = (
            stranger_home / "project" / "brick-protocol" / "buildings" / "stranger-0619"
        )
        stranger_root.mkdir(parents=True, exist_ok=True)
        if reporter._building_root_is_real_vessel(stranger_home, stranger_root):  # noqa: SLF001
            raise ReportEnvAutoloadError(
                "evroot2-vessel: an UNRECOGNIZED repo (neither the source REPO_ROOT "
                "nor the $BRICK_HOME evidence home) that merely carries the "
                "project/<id>/buildings path shape was accepted as a real vessel -- "
                "the fix over-widened (any temp tree with the right shape would now "
                "fire slack/dashboard); acceptance must be scoped to the recognized "
                "homes only"
            )
        stranger_refs = reporter._sink_refs_for_building_event_root(  # noqa: SLF001
            env_refs, repo=stranger_home, root=stranger_root
        )
        if reporter.SLACK_SINK_REF in stranger_refs or reporter.DASHBOARD_SINK_REF in stranger_refs:
            raise ReportEnvAutoloadError(
                "evroot2-vessel: external sinks survived for an UNRECOGNIZED-repo "
                "building (over-widening)"
            )

        # NO WIDENING (5) -- the EMPTY-MIMIC guard (slack-wiring-gap 0619, codex
        # adversarial review). The recognized-home + path-shape checks are NOT
        # enough: $BRICK_HOME is caller-controlled and
        # project_ref_for_building_root verifies only the project/<id>/buildings
        # PATH SHAPE. So a caller can ``mkdir -p`` an EMPTY path-shape building
        # under the SAME recognized evidence home -- with NO declared-plan spine --
        # and the pre-narrowing predicate accepted it, letting a test / foreign
        # building spam the real Slack. The narrowing requires real building-spine
        # evidence (a declared plan). This empty mimic has none, so it MUST be
        # rejected as a vessel and its external sinks MUST be stripped. (The
        # positive fixture ``root`` above DID write a declared plan, so this is a
        # same-home contrast: shape alone is not enough; only real evidence passes.)
        empty_mimic_root = (
            evidence_home / "project" / "brick-protocol" / "buildings" / "empty-mimic-0619"
        )
        empty_mimic_root.mkdir(parents=True, exist_ok=True)  # path shape only, NO spine
        if reporter._building_root_is_real_vessel(repo, empty_mimic_root):  # noqa: SLF001
            raise ReportEnvAutoloadError(
                "evroot2-vessel: an EMPTY path-shape building under the recognized "
                "$BRICK_HOME evidence home (project/<id>/buildings/<id> mkdir with NO "
                "declared-building-plan spine) was accepted as a real vessel -- the "
                "vessel gate degraded to a PATH-SHAPE check, so a test or "
                "foreign-project building under a caller-controlled $BRICK_HOME could "
                "fire the real Slack/dashboard. The gate must require real "
                "building-spine evidence, not just the path shape."
            )
        empty_mimic_event_root = reporter._building_event_root(  # noqa: SLF001
            repo, empty_mimic_root
        )
        empty_mimic_refs = reporter._sink_refs_for_building_event_root(  # noqa: SLF001
            env_refs, repo=repo, root=empty_mimic_event_root
        )
        if (
            reporter.SLACK_SINK_REF in empty_mimic_refs
            or reporter.DASHBOARD_SINK_REF in empty_mimic_refs
        ):
            raise ReportEnvAutoloadError(
                "evroot2-vessel: slack/dashboard SURVIVED for an EMPTY path-shape "
                "mimic building (no declared-plan spine) under the recognized "
                "evidence home -- the vessel gate did not STRIP external sinks for a "
                "shape-only mimic, so a fake building could spam the real Slack"
            )
    finally:
        if prior_brick_home is None:
            os.environ.pop("BRICK_HOME", None)
        else:
            os.environ["BRICK_HOME"] = prior_brick_home

    return [
        "evroot2-vessel-gate green: a building whose evidence root lives under the "
        "EVROOT2 evidence home ($BRICK_HOME / ~/.brick), NOT under the source "
        "REPO_ROOT, is recognized as a real vessel -- with a threaded report_env "
        "the default-policy emit lists slack AND dashboard as delivered sinks "
        "through BOTH the env gate and the vessel gate; no-creds still drops slack "
        "at the env gate, a non-vessel/garbage or mismatched root still has its "
        "external sinks stripped, an UNRECOGNIZED repo (neither REPO_ROOT nor "
        "the evidence home) with the right path shape is STILL rejected, and -- the "
        "slack-wiring-gap 0619 narrowing -- an EMPTY path-shape mimic under the "
        "SAME recognized evidence home (no declared-building-plan spine) is STILL "
        "rejected and has slack+dashboard STRIPPED (shape alone is not a vessel; "
        "only real building-spine evidence passes), so a caller-controlled "
        "$BRICK_HOME mkdir cannot spam the real Slack (no widening).",
    ]


def _check_mutation_red_vessel_gate(runtime_env, tmp: Path) -> str:
    """If the vessel check is re-broken (repo==REPO_ROOT hard-required again), the
    EVROOT2 evidence-home building's slack sink WOULD be stripped -> RED.

    Monkeypatches ``_building_root_is_real_vessel`` to reinstate the pre-fix guard
    (reject any repo != REPO_ROOT) and confirms the SAME emit path then strips
    slack+dashboard from the EVROOT2-rooted building down to inbox-only -- proving
    the real fix (recognizing the evidence-home vessel) is what keeps slack
    delivered, and that this pin is not vacuously green.
    """

    reporter = _import_reporter()

    policy = reporter._default_report_event_policy()  # noqa: SLF001
    threaded_env = {
        "BRICK_REPORT_SLACK_BOT_TOKEN": _FAKE_SLACK_TOKEN,
        "BRICK_REPORT_SLACK_CHANNEL_ID": _FAKE_CHANNEL_ID,
        "BRICK_DASHBOARD_INGEST_URL": _FAKE_DASHBOARD_URL,
        "BRICK_DASHBOARD_INGEST_SECRET": _FAKE_DASHBOARD_SECRET,
    }
    evidence_home = (tmp / "evroot2-mutation-home").resolve()
    root = evidence_home / "project" / "brick-protocol" / "buildings" / "wiki-dogfood-mutation-0619"
    # The REAL fix keeps slack for THIS fixture only if it is a genuine vessel --
    # the narrowing requires a declared-plan spine, so write one (otherwise the
    # baseline-keeps-slack sanity check below would fail on the spine gate, not the
    # mutation).
    _write_declared_plan_spine(root)
    repo = evidence_home
    env_refs = reporter._event_policy_sink_refs(  # noqa: SLF001
        policy, slack_env=threaded_env, dashboard_env=threaded_env
    )

    original = reporter._building_root_is_real_vessel
    repo_root_const = reporter.REPO_ROOT

    def _pre_fix_vessel(vrepo, vroot):
        # The re-introduced bug: the source-worktree REPO_ROOT equality guard.
        if vrepo.resolve() != repo_root_const.resolve():
            return False
        return original(vrepo, vroot)

    prior_brick_home = os.environ.get("BRICK_HOME")
    os.environ["BRICK_HOME"] = str(evidence_home)
    try:
        event_root = reporter._building_event_root(repo, root)  # noqa: SLF001
        # Sanity: with the REAL (unmutated) fix the evidence-home vessel keeps slack
        # -- so the strip below is attributable to the mutation, not the fixture.
        baseline_refs = reporter._sink_refs_for_building_event_root(  # noqa: SLF001
            env_refs, repo=repo, root=event_root
        )
        if reporter.SLACK_SINK_REF not in baseline_refs:
            raise ReportEnvAutoloadError(
                "mutation RED setup invalid (vessel gate): the REAL fix did not keep "
                "slack for the EVROOT2 fixture, so the mutation comparison is "
                "confounded"
            )
        reporter._building_root_is_real_vessel = _pre_fix_vessel  # noqa: SLF001
        mutated_refs = reporter._sink_refs_for_building_event_root(  # noqa: SLF001
            env_refs, repo=repo, root=event_root
        )
    finally:
        reporter._building_root_is_real_vessel = original  # noqa: SLF001
        if prior_brick_home is None:
            os.environ.pop("BRICK_HOME", None)
        else:
            os.environ["BRICK_HOME"] = prior_brick_home

    if reporter.SLACK_SINK_REF in mutated_refs:
        raise ReportEnvAutoloadError(
            "mutation RED failed (vessel gate): with the pre-fix repo==REPO_ROOT "
            "guard reinstated, the EVROOT2 evidence-home building STILL kept its "
            "slack sink -- so the behavioral check that the real vessel fix is what "
            "keeps slack delivered is vacuous"
        )
    if reporter.DASHBOARD_SINK_REF in mutated_refs:
        raise ReportEnvAutoloadError(
            "mutation RED failed (vessel gate): the dashboard sink survived the "
            "reinstated pre-fix guard for an EVROOT2-rooted building"
        )
    return (
        "mutation RED observed (vessel gate): with the pre-fix repo==REPO_ROOT "
        "guard reinstated in _building_root_is_real_vessel, the EVROOT2 "
        "evidence-home building's slack+dashboard sinks ARE stripped to inbox-only "
        "-- the real fix (recognizing the ~/.brick-rooted vessel) is what keeps "
        "slack delivered."
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

    AST-scans ``brick_protocol/support/operator/run.py`` and finds the report-emitting building
    entries -- the public/top-level functions that DERIVE the report policy
    (``report_event_policy_from_plan``) and/or thread ``report_env`` straight into
    the dynamic walker. Each such entry MUST also call
    ``load_report_env_into_process`` in its own body (so the threaded report_env is
    real and the env-gated sinks deliver). A report-emitting entry that does NOT
    cross the loader is the exact MAJOR-6 gap and fails the checker.
    """

    import ast

    run_path = repo / "brick_protocol" / "support" / "operator" / "run.py"
    try:
        text = run_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReportEnvAutoloadError(f"could not read brick_protocol/support/operator/run.py: {exc}") from exc
    if "load_report_env_into_process" not in text:
        raise ReportEnvAutoloadError(
            "brick_protocol/support/operator/run.py does not call load_report_env_into_process "
            "(the engine seam is not wired)"
        )
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:  # pragma: no cover - surfaced as a RED
        raise ReportEnvAutoloadError(
            f"could not parse brick_protocol/support/operator/run.py: {exc}"
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
        outputs.extend(_check_evroot2_vessel_gate(runtime_env, tmp))
        outputs.append(_check_mutation_red_permission_gate(runtime_env, tmp))
        outputs.append(_check_mutation_red_allowlist(runtime_env, tmp))
        outputs.append(_check_mutation_red_fd_permission_gate(runtime_env, tmp))
        outputs.append(_check_mutation_red_injection_split(runtime_env, tmp))
        outputs.append(_check_mutation_red_vessel_gate(runtime_env, tmp))
    outputs.append(_assert_seam_wires_loader(repo))
    outputs.append(PROOF_LIMIT)
    return outputs


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: the report.env engine auto-loader injects "
            "only the allowlisted credential keys, refuses a loose-perm file, "
            "pins generic env precedence plus Brick-file provider precedence, and "
            "never echoes a value (#56)."
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

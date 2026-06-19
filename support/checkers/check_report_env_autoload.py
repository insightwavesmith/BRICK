#!/usr/bin/env python3
"""Behavioral checker for the report.env engine auto-loader (#56).

ENGINE AUTO-LOADER (0619): the default report policy fans out to
``[local-inbox, slack, dashboard]`` with real delivery enabled, but slack +
dashboard are ENVIRONMENT-GATED sinks -- at delivery time they read their creds
from ``os.environ``. If those keys are absent from the building process the gated
sinks silently degrade to local-inbox only and no slack/dashboard notification
arrives. ``support/operator/runtime_env.py`` loads the NARROW allowlist of
credential keys from ``~/.brick/report.env`` (+ optional ``credentials.env``) into
``os.environ`` ONCE at the engine seam (``run_building_plan`` /
``resume_building_plan`` in ``support/operator/run.py``) so the gated sinks always
see the creds, regardless of how the operator launched.

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
     loaded/skipped key lists, or the masked summary.

It also runs IN-PROCESS MUTATION-RED probes: with the 0600 permission gate
defeated, the 0644 file would be loaded (RED); with the allowlist widened, the
non-allowlisted key would be loaded (RED). These prove the checker is not
vacuously green if the loader ever loses the gate or widens the allowlist.

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
_FAKE_GEMINI_KEY = "AIzaFAKEFIXTUREkey000"
_NON_ALLOWLISTED_KEY = "BRICK_NOT_A_CREDENTIAL_KEY"
_NON_ALLOWLISTED_VALUE = "fixture-non-allowlisted-value"
_PRESET_TOKEN_VALUE = "operator-explicit-env-wins-fixture"

# Every fake value above; used to prove no value leaks into the result evidence.
_ALL_FIXTURE_VALUES = (
    _FAKE_SLACK_TOKEN,
    _FAKE_CHANNEL_ID,
    _FAKE_DASHBOARD_URL,
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
        runtime_env._file_is_loose_permissioned = lambda path: False  # noqa: SLF001
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


def _assert_seam_wires_loader(repo: Path) -> str:
    """The loader is called at the run.py engine seam (both run + resume)."""

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
    if text.count("load_report_env_into_process(") < 2:
        raise ReportEnvAutoloadError(
            "support/operator/run.py wires the auto-loader at fewer than the two "
            "expected seams (run_building_plan + resume_building_plan)"
        )
    return (
        "engine-seam green: support/operator/run.py calls load_report_env_into_process "
        "at the run + resume building seams."
    )


def check(repo: Path) -> list[str]:
    runtime_env = _import_loader()
    outputs: list[str] = ["report.env auto-loader behavioral checker green:"]
    with tempfile.TemporaryDirectory(prefix="report-env-autoload-check-") as tmp_name:
        tmp = Path(tmp_name)
        outputs.extend(_check_allowlist_injection_and_precedence(runtime_env, tmp))
        outputs.extend(_check_loose_permission_refusal(runtime_env, tmp))
        outputs.extend(_check_absent_file_noop(runtime_env, tmp))
        outputs.append(_check_mutation_red_permission_gate(runtime_env, tmp))
        outputs.append(_check_mutation_red_allowlist(runtime_env, tmp))
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

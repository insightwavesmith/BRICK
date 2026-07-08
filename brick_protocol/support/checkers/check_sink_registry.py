#!/usr/bin/env python3
"""Sink registry and standalone sink/provider CLI checker.

Uses only temp ``BRICK_HOME`` fixtures and injected network-call fakes. It never
reads the caller's live ``~/.brick/sinks.yaml`` or calls Slack/Dashboard.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import tempfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any


class SinkRegistryError(RuntimeError):
    pass


@contextlib.contextmanager
def _temp_brick_home() -> Iterator[Path]:
    previous_home = os.environ.get("BRICK_HOME")
    with tempfile.TemporaryDirectory(prefix="bp-sink-registry-") as tmp:
        os.environ["BRICK_HOME"] = tmp
        try:
            yield Path(tmp)
        finally:
            if previous_home is None:
                os.environ.pop("BRICK_HOME", None)
            else:
                os.environ["BRICK_HOME"] = previous_home


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml  # type: ignore[import-not-found]

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise SinkRegistryError(f"{path} did not contain a mapping")
    return loaded


def _sink_row(registry: Mapping[str, Any], sink_ref: str) -> Mapping[str, Any]:
    rows = registry.get("sinks")
    if not isinstance(rows, list):
        raise SinkRegistryError("sinks.yaml missing sinks list")
    for row in rows:
        if isinstance(row, Mapping) and row.get("sink_ref") == sink_ref:
            return row
    raise SinkRegistryError(f"sinks.yaml missing row for {sink_ref}")


def _assert_sink_check(row: Mapping[str, Any], *, status: str, label: str) -> None:
    check = row.get("last_reachability_check")
    if not isinstance(check, Mapping):
        raise SinkRegistryError(f"{label}: missing last_reachability_check")
    if check.get("status") != status:
        raise SinkRegistryError(f"{label}: expected status {status}, got {check.get('status')!r}")
    if not isinstance(check.get("checked_at"), str) or not check["checked_at"]:
        raise SinkRegistryError(f"{label}: checked_at timestamp missing")


def _fake_slack_call(*, token: str, channel_id: str, text: str, timeout: float) -> dict[str, Any]:
    if token != "xoxb-fixture" or channel_id != "C123FIXTURE":
        raise SinkRegistryError("slack fake received unexpected credential shape")
    if "BRICK setup readiness check" not in text:
        raise SinkRegistryError("slack fake did not receive setup-confirmation text")
    return {"ok": True}


def _fake_dashboard_call(*, ingest_url: str, secret: str, timeout: float) -> dict[str, Any]:
    if ingest_url != "https://dashboard.example.test/ingest" or secret != "dashboard-fixture":
        raise SinkRegistryError("dashboard fake received unexpected endpoint shape")
    return {"ok": True}


def _fake_dashboard_unreachable(*, ingest_url: str, secret: str, timeout: float) -> dict[str, Any]:
    return {"ok": False, "status": "unreachable", "error_kind": "TimeoutError"}


def _run_cli(argv: list[str]) -> tuple[int, str]:
    from brick_protocol.support.operator import cli

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = cli.main(argv)
    return exit_code, stdout.getvalue()


def run(repo: Path) -> None:
    with _temp_brick_home() as home:
        from brick_protocol.support.operator import cli, onboard
        from brick_protocol.support.operator.sink_registry import sink_registry_path

        path = sink_registry_path()
        if path.exists():
            raise SinkRegistryError("fixture sinks.yaml unexpectedly existed before provisioning")

        slack = onboard.run_slack_provision_step(
            slack_bot_token="xoxb-fixture",
            slack_channel_id="C123FIXTURE",
            slack_api_call=_fake_slack_call,
        )
        if slack.get("action") not in {"installed", "validated"} or not slack.get("slack_ready"):
            raise SinkRegistryError(f"slack provisioning did not report ready fixture evidence: {slack!r}")
        registry = _load_yaml(path)
        slack_row = _sink_row(registry, "report-sink:slack")
        if slack_row.get("credentials_present") is not True:
            raise SinkRegistryError("slack registry row did not record credentials_present true")
        _assert_sink_check(slack_row, status="ready", label="slack fixture")

        dashboard_skip = onboard.run_dashboard_provision_step()
        if dashboard_skip.get("action") != "skipped_not_configured":
            raise SinkRegistryError(
                "dashboard no-credentials path must be a distinct skip, got "
                f"{dashboard_skip!r}"
            )
        dashboard_row = _sink_row(_load_yaml(path), "report-sink:dashboard")
        if dashboard_row.get("credentials_present") is not False:
            raise SinkRegistryError("dashboard skip row should record credentials_present false")
        _assert_sink_check(dashboard_row, status="not_configured", label="dashboard skip")

        dashboard_bad = onboard.run_dashboard_provision_step(
            dashboard_ingest_url="https://dashboard.example.test/ingest",
            dashboard_secret="dashboard-fixture",
            dashboard_http_call=_fake_dashboard_unreachable,
        )
        if dashboard_bad.get("dashboard_ready") is not False or dashboard_bad.get("action") != "installed":
            raise SinkRegistryError(f"dashboard unreachable fixture shape drifted: {dashboard_bad!r}")
        _assert_sink_check(
            _sink_row(_load_yaml(path), "report-sink:dashboard"),
            status="unreachable",
            label="dashboard unreachable",
        )

        dashboard = onboard.run_dashboard_provision_step(
            dashboard_ingest_url="https://dashboard.example.test/ingest",
            dashboard_secret="dashboard-fixture",
            dashboard_http_call=_fake_dashboard_call,
        )
        if dashboard.get("dashboard_ready") is not True:
            raise SinkRegistryError(f"dashboard ready fixture did not report ready: {dashboard!r}")
        _assert_sink_check(
            _sink_row(_load_yaml(path), "report-sink:dashboard"),
            status="ready",
            label="dashboard ready",
        )

        parser = cli.build_parser()
        provider_args = parser.parse_args(["provider", "add", "codex"])
        if not callable(getattr(provider_args, "func", None)):
            raise SinkRegistryError("brick provider add <host> did not bind a CLI handler")
        sink_args = parser.parse_args(["sink", "add", "slack"])
        if not callable(getattr(sink_args, "func", None)):
            raise SinkRegistryError("brick sink add slack did not bind a CLI handler")
        dashboard_args = parser.parse_args(["sink", "add", "dashboard"])
        if not callable(getattr(dashboard_args, "func", None)):
            raise SinkRegistryError("brick sink add dashboard did not bind a CLI handler")

        cli_onboard = cli.onboard
        original_provider = cli_onboard.run_provider_register_step
        original_slack = cli_onboard.run_slack_provision_step
        original_dashboard = cli_onboard.run_dashboard_provision_step
        try:
            cli_onboard.run_provider_register_step = lambda host: {
                "ok": True,
                "action": "registered",
                "adapter_ref": f"adapter:{host}-local",
                "message_ko": "provider fixture registered",
            }
            cli_onboard.run_slack_provision_step = lambda **kwargs: {
                "ok": True,
                "action": "validated",
                "slack_ready": True,
                "message_ko": "slack fixture ready",
            }
            cli_onboard.run_dashboard_provision_step = lambda **kwargs: {
                "ok": True,
                "action": "validated",
                "dashboard_ready": True,
                "message_ko": "dashboard fixture ready",
            }
            for argv, expected in (
                (["provider", "add", "codex"], "provider fixture registered"),
                (["sink", "add", "slack"], "slack fixture ready"),
                (["sink", "add", "dashboard"], "dashboard fixture ready"),
            ):
                exit_code, output = _run_cli(argv)
                if exit_code != 0 or expected not in output:
                    raise SinkRegistryError(
                        f"CLI dispatch failed for {argv}: exit={exit_code}, output={output!r}"
                    )
        finally:
            cli_onboard.run_provider_register_step = original_provider
            cli_onboard.run_slack_provision_step = original_slack
            cli_onboard.run_dashboard_provision_step = original_dashboard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repo root to inspect")
    args = parser.parse_args(argv)
    try:
        run(Path(args.repo).resolve())
    except SinkRegistryError as exc:
        print(f"sink_registry rejected evidence: {exc}")
        return 1
    print("sink_registry green: fixture-only sink registry and CLI dispatch cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Provider registry ladder checker.

Uses only temp ``BRICK_HOME`` fixtures. It never reads the caller's live
``~/.brick/providers.yaml``.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class ProviderRegistryLadderError(RuntimeError):
    pass


@contextmanager
def _temp_brick_home() -> Any:
    previous_home = os.environ.get("BRICK_HOME")
    previous_ladder = os.environ.get("BRICK_PROVIDER_LADDER")
    with tempfile.TemporaryDirectory(prefix="bp-provider-registry-") as tmp:
        os.environ["BRICK_HOME"] = tmp
        os.environ.pop("BRICK_PROVIDER_LADDER", None)
        try:
            yield Path(tmp)
        finally:
            if previous_home is None:
                os.environ.pop("BRICK_HOME", None)
            else:
                os.environ["BRICK_HOME"] = previous_home
            if previous_ladder is None:
                os.environ.pop("BRICK_PROVIDER_LADDER", None)
            else:
                os.environ["BRICK_PROVIDER_LADDER"] = previous_ladder


def _write_registry(home: Path, body: str) -> None:
    path = home / "providers.yaml"
    path.write_text(body, encoding="utf-8")
    path.chmod(0o600)


AGENT_OBJECT_REFS = (
    "agent-object:coo",
    "agent-object:cto-lead",
    "agent-object:design-lead",
    "agent-object:dev",
    "agent-object:inspector",
    "agent-object:pm-lead",
    "agent-object:qa",
    "agent-object:qa-lead",
)


def _selection(repo: Path, agent_object_ref: str = "agent-object:inspector") -> dict[str, str | None]:
    from brick_protocol.support.operator.plan_rendering import _resolve_casting_selection

    return _resolve_casting_selection(
        repo,
        raw_step={},
        agent_object_ref=agent_object_ref,
        plan_casting={
            "selected_adapter_ref": "adapter:local",
            "selected_model_ref": "model:default",
        },
        label="provider-registry-ladder-fixture",
        is_verdict_bearing_node=False,
    )


def _assert_selection(
    observed: Mapping[str, Any],
    *,
    adapter_ref: str,
    model_ref: str,
    label: str,
) -> None:
    if observed.get("selected_adapter_ref") != adapter_ref:
        raise ProviderRegistryLadderError(
            f"{label}: selected_adapter_ref expected {adapter_ref}, "
            f"got {observed.get('selected_adapter_ref')}"
        )
    if observed.get("selected_model_ref") != model_ref:
        raise ProviderRegistryLadderError(
            f"{label}: selected_model_ref expected {model_ref}, "
            f"got {observed.get('selected_model_ref')}"
        )


def _assert_effort_ref_shape(observed: Mapping[str, Any], *, label: str) -> None:
    effort_ref = observed.get("selected_reasoning_effort_ref")
    if not isinstance(effort_ref, str) or not effort_ref.startswith("effort:"):
        raise ProviderRegistryLadderError(
            f"{label}: selected_reasoning_effort_ref expected effort:* value, "
            f"got {effort_ref!r}"
        )


def _agent_allow_list_union(repo: Path) -> set[str]:
    import json

    refs: set[str] = set()
    for path in sorted((repo / "agent" / "objects").glob("*.yaml")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for adapter_ref in data.get("adapter_refs", []):
            if isinstance(adapter_ref, str) and adapter_ref.strip():
                refs.add(adapter_ref.strip())
    return refs


def _unknown_registry_adapter_refs(repo: Path, registry: Mapping[str, Any]) -> list[str]:
    allowed = _agent_allow_list_union(repo)
    rows = registry.get("providers")
    if not isinstance(rows, list):
        return []
    unknown: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        adapter_ref = str(row.get("adapter_ref") or "").strip()
        if adapter_ref and adapter_ref not in allowed:
            unknown.append(adapter_ref)
    return unknown


def run(repo: Path) -> None:
    import json as _json

    # The lane-preference expectation derives from the DECLARED Agent Object so a
    # ratified policy change (e.g. inspector 0702 gemini->claude) moves the pin
    # with the declaration instead of freezing a stale provider here.
    _lane = _json.loads(
        (repo / "agent" / "objects" / "inspector.yaml").read_text(encoding="utf-8")
    )
    lane_adapter_ref = str(_lane["preferred_adapter_ref"])
    lane_model_ref = str(_lane["preferred_model_ref"])
    with _temp_brick_home() as home:
        _assert_selection(
            _selection(repo),
            adapter_ref=lane_adapter_ref,
            model_ref=lane_model_ref,
            label="absent providers.yaml preserves legacy lane preference",
        )

        absent_by_agent = {
            agent_object_ref: _selection(repo, agent_object_ref)
            for agent_object_ref in AGENT_OBJECT_REFS
        }
        os.environ["BRICK_PROVIDER_LADDER"] = "0"
        _write_registry(
            home,
            """
version: 1
preferred_adapter_ref: adapter:codex-local
providers:
  - adapter_ref: adapter:codex-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
    model_ref: model:codex:default
    reasoning_tier: medium
""",
        )
        kill_switch_by_agent = {
            agent_object_ref: _selection(repo, agent_object_ref)
            for agent_object_ref in AGENT_OBJECT_REFS
        }
        os.environ.pop("BRICK_PROVIDER_LADDER", None)
        if kill_switch_by_agent != absent_by_agent:
            raise ProviderRegistryLadderError(
                "absent providers.yaml and BRICK_PROVIDER_LADDER=0 selections "
                f"must be byte-identical for all Agent Objects: {kill_switch_by_agent!r} "
                f"!= {absent_by_agent!r}"
            )

        _write_registry(
            home,
            """
version: 1
preferred_adapter_ref: adapter:gemini-local
providers:
  - adapter_ref: adapter:gemini-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
    model_ref: model:gemini:default
    reasoning_tier: null
""",
        )
        _assert_selection(
            _selection(repo),
            adapter_ref="adapter:gemini-local",
            model_ref="model:gemini:default",
            label="registered ready static preference stays on lane preference",
        )

        _write_registry(
            home,
            """
version: 1
preferred_adapter_ref: adapter:codex-local
providers:
  - adapter_ref: adapter:codex-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
    model_ref: model:codex:default
    reasoning_tier: medium
""",
        )
        _assert_selection(
            observed := _selection(repo),
            adapter_ref="adapter:codex-local",
            model_ref="model:codex:default",
            label="unregistered static preference falls back with model update",
        )
        _assert_effort_ref_shape(
            observed,
            label="provider fallback preserves reasoning-effort dial shape",
        )

        _write_registry(
            home,
            """
version: 1
preferred_adapter_ref: adapter:codex-local
providers:
  - adapter_ref: adapter:codex-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
    model_ref: model:gemini:default
    reasoning_tier: medium
""",
        )
        _assert_selection(
            _selection(repo),
            adapter_ref="adapter:codex-local",
            model_ref="model:codex:default",
            label="malformed registry model_ref falls back to adapter default",
        )

        _write_registry(
            home,
            """
version: 1
preferred_adapter_ref: adapter:not-in-agent-allow-list
providers:
  - adapter_ref: adapter:not-in-agent-allow-list
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
    model_ref: model:codex:default
    reasoning_tier: medium
""",
        )
        _assert_selection(
            _selection(repo),
            adapter_ref=lane_adapter_ref,
            model_ref=lane_model_ref,
            label="fallback outside Agent Object allow-list is rejected",
        )

        os.environ["BRICK_PROVIDER_LADDER"] = "0"
        _write_registry(
            home,
            """
version: 1
preferred_adapter_ref: adapter:codex-local
providers:
  - adapter_ref: adapter:codex-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
    model_ref: model:codex:default
    reasoning_tier: medium
""",
        )
        _assert_selection(
            _selection(repo),
            adapter_ref=lane_adapter_ref,
            model_ref=lane_model_ref,
            label="BRICK_PROVIDER_LADDER=0 forces legacy behavior",
        )
        os.environ.pop("BRICK_PROVIDER_LADDER", None)

    unknown = _unknown_registry_adapter_refs(
        repo,
        {"providers": [{"adapter_ref": "adapter:not-admitted-anywhere"}]},
    )
    if unknown != ["adapter:not-admitted-anywhere"]:
        raise ProviderRegistryLadderError(
            "provider registry allow-list checker did not reject unknown fixture adapter"
        )
    if _unknown_registry_adapter_refs(
        repo,
        {"providers": [{"adapter_ref": "adapter:codex-local"}]},
    ):
        raise ProviderRegistryLadderError(
            "provider registry allow-list checker rejected admitted fixture adapter"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repo root to inspect")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    try:
        run(repo)
    except ProviderRegistryLadderError as exc:
        print(f"provider_registry_ladder rejected evidence: {exc}")
        return 1
    print(
        "provider_registry_ladder green: fixture-only registry ladder cases "
        "and Agent Object allow-list validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

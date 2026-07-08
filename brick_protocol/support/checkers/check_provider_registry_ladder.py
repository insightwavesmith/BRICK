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
    for path in sorted((repo / "brick_protocol" / "agent" / "objects").glob("*.yaml")):
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



def _assert_raises(label: str, fn: Any, contains: str) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - checker wants the exact rejection text
        if contains not in str(exc):
            raise ProviderRegistryLadderError(
                f"{label}: expected rejection containing {contains!r}, got {exc!r}"
            ) from exc
        return
    raise ProviderRegistryLadderError(f"{label}: expected rejection containing {contains!r}")


def _tier_declared_plan_step() -> Mapping[str, Any]:
    return {
        "step_ref": "tier-step",
        "casting_tier_ref": "casting-tier:standard",
        "casting_lens_ref": "casting-lens:qa",
        "brick": {
            "row_ref": "tier-step:brick",
            "brick_work_ref": "brick-work:tier",
            "brick_instance_ref": "brick-tier",
            "work_statement": "tier fixture",
            "comparison_rule": "fixture only",
            "required_return_shape": "observed_evidence,not_proven",
        },
        "agent": {
            "row_ref": "tier-step:agent",
            "agent_object_ref": "agent-object:qa",
        },
        "link": {
            "row_ref": "tier-step:link",
            "movement": "forward",
            "target_ref": "brick-next",
        },
    }


def _tier_declared_plan_intent(step: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "plan_ref": "building-plan:tier-fixture",
        "building_id": "tier-fixture",
        "selected_adapter_ref": "adapter:local",
        "selected_model_ref": "model:default",
        "proof_limits": ["checker fixture only"],
        "not_proven": ["live provider runtime"],
        "steps": [step],
    }


def _render_tier_declared_step() -> Mapping[str, Any]:
    from brick_protocol.support.operator.plan_rendering import render_declared_building_plan

    plan = render_declared_building_plan(_tier_declared_plan_intent(_tier_declared_plan_step()))
    steps = plan.get("steps")
    if not isinstance(steps, list) or len(steps) != 1 or not isinstance(steps[0], Mapping):
        raise ProviderRegistryLadderError("tier declared plan fixture did not render one step")
    return steps[0]


def _run_tier_resolution_cases(repo: Path, home: Path) -> None:
    from brick_protocol.support.operator.provider_registry import resolve_casting_tier

    _write_registry(
        home,
        """
version: 1
preferred_adapter_ref: adapter:claude-local
providers:
  - adapter_ref: adapter:claude-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
    model_ref: model:claude:inherit
    reasoning_tier: xhigh
""",
    )
    step = _render_tier_declared_step()
    _assert_selection(
        step,
        adapter_ref="adapter:claude-local",
        model_ref="model:claude:claude-opus-4-8",
        label="declared casting tier resolves once through ready providers.yaml",
    )
    from brick_protocol.support.operator.plan_rendering import _resolve_casting_selection

    _assert_selection(
        _resolve_casting_selection(
            repo,
            raw_step={
                "casting_tier_ref": "casting-tier:standard",
                "casting_lens_ref": "casting-lens:qa",
            },
            agent_object_ref="agent-object:qa",
            plan_casting={
                "selected_adapter_ref": "adapter:local",
                "selected_model_ref": "model:default",
            },
            label="tier internal selection fixture",
            is_verdict_bearing_node=False,
        ),
        adapter_ref="adapter:claude-local",
        model_ref="model:claude:claude-opus-4-8",
        label="internal casting selection tier resolves through ready providers.yaml",
    )
    if step.get("selected_reasoning_effort_ref") != "effort:xhigh":
        raise ProviderRegistryLadderError(
            "declared casting tier did not stamp selected_reasoning_effort_ref=effort:xhigh"
        )
    provenance = step.get("casting_tier_provenance")
    if not isinstance(provenance, Mapping) or provenance.get("casting_tier_ref") != "casting-tier:standard":
        raise ProviderRegistryLadderError("declared casting tier did not stamp tier provenance")
    if provenance.get("casting_lens_ref") != "casting-lens:qa":
        raise ProviderRegistryLadderError("declared casting tier did not stamp lens provenance")

    _assert_selection(
        resolve_casting_tier(
            {
                "version": 1,
                "providers": [
                    {
                        "adapter_ref": "adapter:codex-fugu-local",
                        "last_preflight": {"status": "ready"},
                    }
                ],
            },
            "casting-tier:deep",
            "casting-lens:work",
        ),
        adapter_ref="adapter:codex-fugu-local",
        model_ref="model:sakana:fugu-ultra",
        label="deep tier maps to fugu-ultra policy row",
    )

    literal_bypass_step = {
        **_tier_declared_plan_step(),
        "selected_adapter_ref": "adapter:claude-local",
    }
    _assert_raises(
        "tier plus selected_* literal bypass",
        lambda: __import__(
            "brick_protocol.support.operator.plan_rendering",
            fromlist=["render_declared_building_plan"],
        ).render_declared_building_plan(_tier_declared_plan_intent(literal_bypass_step)),
        "exclusive with concrete selected_*",
    )

    (home / "providers.yaml").unlink()
    _assert_raises(
        "tier without providers.yaml",
        _render_tier_declared_step,
        "requires a providers.yaml registry",
    )

    _write_registry(
        home,
        """
version: 1
enabled: false
providers:
  - adapter_ref: adapter:claude-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
""",
    )
    _assert_raises(
        "tier with disabled ladder",
        _render_tier_declared_step,
        "requires the provider registry ladder to be enabled",
    )

    _write_registry(
        home,
        """
version: 1
providers:
  - adapter_ref: adapter:gemini-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
""",
    )
    _assert_raises(
        "tier with no ready adapter in declared ladder",
        _render_tier_declared_step,
        "no ready provider in declared tier ladder",
    )

    from brick_protocol.support.operator.assembly import brick, build

    authored = brick("work", "tier authoring fixture", tier="standard", lens="qa")
    if authored.casting.get("casting_tier_ref") != "casting-tier:standard":
        raise ProviderRegistryLadderError("brick(tier=) did not carry casting_tier_ref")
    if authored.casting.get("casting_lens_ref") != "casting-lens:qa":
        raise ProviderRegistryLadderError("brick(lens=) did not carry casting_lens_ref")
    compact = build([["work", "tier compact fixture", {"tier": "standard", "lens": "qa"}]])
    compact_node = compact.nodes[0]
    if compact_node.casting.get("casting_tier_ref") != "casting-tier:standard":
        raise ProviderRegistryLadderError("build(... tier=) did not carry casting_tier_ref")


def _run_preset_tier_resolution_cases(repo: Path, home: Path) -> None:
    from brick_protocol.support.operator.composition_intent import (
        _materializer_preset_step_with_selection_override,
    )

    _write_registry(
        home,
        """
version: 1
providers:
  - adapter_ref: adapter:claude-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
  - adapter_ref: adapter:gemini-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
  - adapter_ref: adapter:codex-fugu-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
""",
    )

    raw_tier_step = {
        "step_template_ref": "building-step-template:code-attack-qa",
        "casting_tier_ref": "casting-tier:standard",
        "casting_lens_ref": "casting-lens:code-attack",
    }
    resolved_raw = _materializer_preset_step_with_selection_override(
        raw_tier_step,
        "building-step-template:code-attack-qa",
        {},
    )
    _assert_selection(
        resolved_raw,
        adapter_ref="adapter:claude-local",
        model_ref="model:claude:claude-opus-4-8",
        label="preset raw tier/lens step resolves before graph copy seam",
    )
    if resolved_raw.get("selected_reasoning_effort_ref") != "effort:xhigh":
        raise ProviderRegistryLadderError(
            "preset raw tier/lens step did not carry selected_reasoning_effort_ref"
        )
    if "casting_tier_ref" in resolved_raw or "casting_lens_ref" in resolved_raw:
        raise ProviderRegistryLadderError(
            "preset tier/lens authoring refs leaked past graph copy resolution seam"
        )

    resolved_override = _materializer_preset_step_with_selection_override(
        {"step_template_ref": "building-step-template:axis-attack-qa"},
        "building-step-template:axis-attack-qa",
        {
            "building-step-template:axis-attack-qa": {
                "casting_tier_ref": "casting-tier:light",
                "casting_lens_ref": "casting-lens:axis-attack",
            }
        },
    )
    _assert_selection(
        resolved_override,
        adapter_ref="adapter:gemini-local",
        model_ref="model:gemini:default",
        label="step_selection_overrides tier/lens resolves before graph copy seam",
    )

    literal_step = _materializer_preset_step_with_selection_override(
        {
            "step_template_ref": "building-step-template:code-attack-qa",
            "selected_adapter_ref": "adapter:codex-local",
            "selected_model_ref": "model:codex:default",
        },
        "building-step-template:code-attack-qa",
        {},
    )
    _assert_selection(
        literal_step,
        adapter_ref="adapter:codex-local",
        model_ref="model:codex:default",
        label="legacy selected_* literal preset step remains accepted",
    )

    _assert_raises(
        "preset tier plus selected_* literal bypass",
        lambda: _materializer_preset_step_with_selection_override(
            {
                "step_template_ref": "building-step-template:code-attack-qa",
                "casting_tier_ref": "casting-tier:standard",
                "selected_adapter_ref": "adapter:codex-local",
            },
            "building-step-template:code-attack-qa",
            {},
        ),
        "exclusive with concrete selected_*",
    )
    _assert_raises(
        "preset lens without tier",
        lambda: _materializer_preset_step_with_selection_override(
            {
                "step_template_ref": "building-step-template:code-attack-qa",
                "casting_lens_ref": "casting-lens:code-attack",
            },
            "building-step-template:code-attack-qa",
            {},
        ),
        "casting_lens_ref requires casting_tier_ref",
    )

    for path in sorted((repo / "brick_protocol" / "brick" / "templates" / "presets").glob("*fleet*.md")):
        text = path.read_text(encoding="utf-8")
        if "selected_adapter_ref:" in text or "selected_model_ref:" in text:
            raise ProviderRegistryLadderError(
                f"fleet preset still carries concrete selected_* literal: {path.relative_to(repo)}"
            )
        if "casting_tier_ref:" not in text or "casting_lens_ref:" not in text:
            raise ProviderRegistryLadderError(
                f"fleet preset does not carry tier/lens authoring refs: {path.relative_to(repo)}"
            )


def run(repo: Path) -> None:
    import json as _json

    # The lane-preference expectation derives from the DECLARED Agent Object so a
    # ratified policy change (e.g. inspector 0702 gemini->claude) moves the pin
    # with the declaration instead of freezing a stale provider here.
    _lane = _json.loads(
        (repo / "brick_protocol" / "agent" / "objects" / "inspector.yaml").read_text(encoding="utf-8")
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

        _run_tier_resolution_cases(repo, home)
        _run_preset_tier_resolution_cases(repo, home)

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
        "provider_registry_ladder green: fixture-only registry ladder, "
        "casting-tier resolution, and Agent Object allow-list validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Hook registry axis behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    rule_items,
)


_HOOK_AXIS_ALLOWED_KINDS = frozenset({"advisory", "guardrail-intent"})
_HOOK_AXIS_ALLOWED_KEYS = frozenset(
    {"owner_axis", "kind", "event_ref", "description", "execution_opened"}
)


def _validate_hook_axis(ref, definition):
    """Raise ValueError(reason) if a hook definition is not axis-clean.

    A hook is an Agent-axis ADVISORY/DENY guard ONLY: it never owns another axis,
    never runs natively (execution stays closed = the P6 advisory policy), and
    never carries a quality/sufficiency/Movement JUDGMENT field (judgment is the
    Link axis, never a hook). The key whitelist blocks a judgment field from being
    smuggled in.
    """
    if not isinstance(definition, dict):
        raise ValueError(f"hook_definition_not_mapping: {ref}")
    if definition.get("owner_axis") != "Agent":
        raise ValueError(f"hook_owner_axis_must_be_agent: {ref}")
    if definition.get("kind") not in _HOOK_AXIS_ALLOWED_KINDS:
        raise ValueError(f"hook_kind_not_advisory_or_guardrail: {ref}")
    if definition.get("execution_opened") is not False:
        raise ValueError(f"hook_execution_must_remain_closed: {ref}")
    extra = set(definition.keys()) - _HOOK_AXIS_ALLOWED_KEYS
    if extra:
        raise ValueError(f"hook_carries_forbidden_field: {ref}: {sorted(extra)}")


def run_hook_registry_axis_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """P6 axis guard: every hook in brick_protocol/agent/hooks/registry.yaml is an Agent-axis
    advisory/deny guard carrying NO judgment; plus each profile-declared negative
    fixture must be rejected with its expected reason."""
    count = 0
    registry_path = repo / "brick_protocol" / "agent" / "hooks" / "registry.yaml"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    hooks = registry.get("hooks")
    if not isinstance(hooks, dict) or not hooks:
        raise ProfileError("hook_registry_axis_case: registry has no hooks")
    for ref, definition in sorted(hooks.items()):
        try:
            _validate_hook_axis(ref, definition)
        except ValueError as exc:
            raise ProfileError(f"hook_registry_axis_case rejected real hook {ref}: {exc}") from exc
        count += 1
    for item in rule_items(profile, "hook_registry_axis_case"):
        mapping = require_mapping(item, "hook_registry_axis_case item")
        label = require_string(mapping.get("label"), "hook_registry_axis_case.label")
        expected_reason = require_string(mapping.get("expected_reason"), f"{label}: expected_reason")
        fixture = require_mapping(mapping.get("hook_definition"), f"{label}: hook_definition")
        try:
            _validate_hook_axis(f"fixture:{label}", dict(fixture))
        except ValueError as exc:
            if expected_reason not in str(exc):
                raise ProfileError(
                    f"hook_registry_axis_case {label}: expected reason {expected_reason!r}, observed {exc!r}"
                ) from exc
        else:
            raise ProfileError(f"hook_registry_axis_case {label}: expected rejection but passed")
        count += 1
    return count

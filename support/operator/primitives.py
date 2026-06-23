"""Shared support primitives for the Building operator split.

These helpers are support mechanics only. They do not own Brick / Agent / Link
meaning, choose Movement, or judge success or quality.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, TypeVar

from brick_protocol.agent.return_fact import RETURNED_FORBIDDEN_KEYS as _RETURN_FORBIDDEN_KEYS
from brick_protocol.link.gate import DECLARED_GATE_REFS as _DECLARED_GATE_REFS
from brick_protocol.link.movement import MovementFact
from brick_protocol.link.transition import (
    BUILDING_LIFECYCLE_STATES as _BUILDING_LIFECYCLE_STATES,
    TRANSITION_LIFECYCLE_ALLOWED_KEYS as _TRANSITION_LIFECYCLE_ALLOWED_KEYS,
    TRANSITION_LIFECYCLE_DISPOSITION_OWNERS as _TRANSITION_LIFECYCLE_DISPOSITION_OWNERS,
    TRANSITION_LIFECYCLE_PROGRESS_STATES as _TRANSITION_LIFECYCLE_PROGRESS_STATES,
    TRANSITION_LIFECYCLE_STATES as _TRANSITION_LIFECYCLE_STATES,
    TransitionFact,
)

_DEFAULT_PROOF_LIMITS: tuple[str, ...] = (
    "support evidence only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
_DEFAULT_NOT_PROVEN: tuple[str, ...] = (
    "brain surface behavior",
    "credential validity",
    "runtime or scheduler behavior",
    "tool or hook execution",
    "source truth",
    "success judgment",
    "quality judgment",
    "Movement authority",
)
_FACT_T = TypeVar("_FACT_T")


# CASTING single-source API (E2/S6): the CastingField descriptor + CASTING_FIELDS
# field-set + its ``selected_*`` projection + the casting transport helpers now
# live on the AGENT axis (agent/spec.py) — the WHO-dials are Agent-axis property,
# not support mechanics. Support re-imports the public names here so existing
# callers keep their import sites; the field-set is ENUMERATED nowhere under
# support/ anymore (agent/spec.py is the single source, registered in
# field_set_registry.yaml's casting_fields row + crossing_registry.yaml's
# agent_spec row). Re-importing a name is not a field-set enumeration, so the
# mirror-guard stays green.
from brick_protocol.agent.spec import (  # noqa: F401  (re-exported for callers)
    CASTING_FIELDS,
    CastingField,
    NATIVE_TARGET_CLAUDE,
    NATIVE_TARGET_CODEX,
    NODE_CASTING_FIELDS,
    casting_bag,
    merge_casting_bags,
    selected_key,
    stamp_casting,
)
# AGENT-OBJECT SCHEMA single source (③ struct-surgery 0623): the agent-object
# allowed-key + ref-field sets now live ONCE on the Agent axis at
# agent/spec.AGENT_OBJECT_SCHEMA (they define the SHAPE of an Agent-axis record).
# Support re-imports the schema and ALIASES the names so existing callers
# (run.py / native_dispatch.py via these names) keep resolving; the literal member
# enumeration lives NOWHERE under support/ anymore (the mirror-guard +
# check_agent_object_schema_single_source stay green). An alias is not a field-set
# enumeration.
from brick_protocol.agent.spec import (  # noqa: F401  (re-exported for callers)
    AGENT_OBJECT_SCHEMA,
)

_AGENT_OBJECT_REF_FIELDS: tuple[str, ...] = AGENT_OBJECT_SCHEMA.ref_fields
_AGENT_OBJECT_ALLOWED_KEYS: frozenset[str] = AGENT_OBJECT_SCHEMA.allowed_keys
_AGENT_ROW_ALLOWED_KEYS: frozenset[str] = frozenset(
    {"axis", "row_ref", "agent_object_ref"}
)
# BRICK-row allowed key-set single-source API (E2/S9): the admitted Brick-row
# key-set a plan may DECLARE now lives on the BRICK axis (brick/spec.py) — the
# declarable Brick contract surface is Brick-axis property, not support mechanics.
# Support re-imports the public name here so existing callers keep their import
# sites; the key-set is ENUMERATED nowhere under support/ anymore (brick/spec.py
# is the single source, registered in field_set_registry.yaml's
# brick_row_allowed_keys row + crossing_registry.yaml's brick_spec row). The
# requires_brick_write_scope marker's VALUE discipline (bool / yes / no,
# fail-closed) moved to brick/spec.declared_brick_write_need at the same step. A
# re-import is not a field-set enumeration, so the mirror-guard stays green.
from brick_protocol.brick.spec import (  # noqa: F401  (re-exported for callers)
    BRICK_ROW_ALLOWED_KEYS as _BRICK_ROW_ALLOWED_KEYS,
)
# LINK_ROW_ALLOWED_KEYS + the Link sub-envelope schemas (route_replay /
# route_decision_basis / transition_authoring / building_lifecycle allowed-keys,
# forbidden-keys, value-markers, author/public-fact prefixes, endpoint-list keys)
# MOVED to the Link single-source API at link/spec.py (E2/S4, mirror M12/M13).
# Support imports them through link/spec.py; they no longer live here.
_FORBIDDEN_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {
        "agent_fact_expansion",
        "agent_fact_shape",
        "agent_status",
        "agentfact_expansion",
        "agentfact_shape",
        "api_call",
        "auth",
        "auth_value",
        "autonomous_movement",
        "call_provider",
        "call_tool",
        "choose_movement",
        "credential",
        "credential_body",
        "credential_value",
        "dashboard",
        "default_gate_fact",
        "default_gatefact",
        "execute",
        "execution",
        "failure",
        "failure_fact",
        "failure_result",
        "launch",
        "movement_choice",
        "provider_call",
        "provider" + "_connector_refs",
        "provider_request",
        "provider_runtime_state",
        "quality",
        "quality_judgment",
        "quality_score",
        "raw_secret",
        "request_body",
        "result",
        "retry",
        "runtime",
        "scheduler",
        "secret",
        "session",
        "session_id",
        "setup_token",
        "setup_token_value",
        "storage",
        "success",
        "success_fact",
        "success_result",
        "tool_call",
        "tool_execution",
        "hook_execution",
        "wiki",
    }
)
# TASK-BY-TEXT inline mechanism (0611, codex FIX-A): a human-spoken task is
# carried ON the declared plan as ``task_statement`` (non-empty text) and the
# plan's ``task_source_ref`` records this literal sentinel token instead of a
# repo path. NO repo-root (or any) ephemeral file is ever written -- the
# evidence writer lands the statement verbatim as work/task.md straight from
# the plan body, and REPLAYING the persisted plan file reproduces task.md
# (the statement travels with the plan). The token is a RECORDED ref-style
# sentinel (like ``model:default``), not a path; plan_validation admits it
# only when the plan actually carries the statement body (fail-closed).
INLINE_TASK_SOURCE_REF = "task-source:inline-statement"
# Fail-closed size guard for the inline statement (codex note): a statement
# over this many UTF-8 bytes must be landed as a repo file + task_source_ref
# instead of being smuggled inline onto every plan/evidence copy.
INLINE_TASK_STATEMENT_MAX_BYTES = 65536
from brick_protocol.support.connection.secret_text import (
    RAW_SECRET_PATTERNS as _RAW_SECRET_PATTERNS,
)
_SESSION_LIKE_UUID_TEXT_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_SESSION_LIKE_ULID_TEXT_RE = re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b")
_REPOSITORY_ARTIFACT_REF_RE = re.compile(
    r"(?:(?:^|[\s`\"'(\[])(?:[ab]/)?"
    r"(?:AGENTS\.md|pyproject\.toml|uv\.lock|support/|brick/|agent/|link/|project/)"
    r"[^\s`\"')\],;]*)|(?:^|\n)@@[^\n]*(?:support/|brick/|agent/|link/|project/)"
)
_GRAPH_PROFILE = "planning-v0"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_AGENT_OBJECT_ROOT = _REPO_ROOT / "agent" / "objects"
_SESSION_CONTINUITY_REQUEST_FIELDS: tuple[str, ...] = (
    "building_session_ref",
    "session_scope_ref",
    "session_continuity_mode",
)
_ROUTE_REPLAY_PLAN_KEY = "route_replay_plan"
_DECLARED_GATE_REFS_KEY = "declared_gate_refs"
_ROUTE_DECISION_BASIS_KEY = "route_decision_basis"
_GATE_SEQUENCE_POLICY_KEY = "gate_sequence_policy"
_TRANSITION_AUTHORING_KEY = "transition_authoring"
_TRANSITION_LIFECYCLE_KEY = "transition_lifecycle"
_BUILDING_LIFECYCLE_KEY = "building_lifecycle"
_WRITE_OBSERVATION_DEFAULT_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".claude",
        "__pycache__",
        ".ruff_cache",
    }
)
_WRITE_OBSERVATION_DEFAULT_EXCLUDED_FILE_NAMES: frozenset[str] = frozenset(
    {
        ".DS_Store",
    }
)
_WRITE_OBSERVATION_DEFAULT_EXCLUDED_SUFFIXES: frozenset[str] = frozenset(
    {
        ".pyc",
        ".pyo",
    }
)
_GRAPH_PLAN_ALLOWED_GROUP_ROLES: frozenset[str] = frozenset(
    {"fan_out", "fan_in", "revision_chain", "review_flow", "support_flow"}
)
_GRAPH_PLAN_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "auto_route",
        "autonomous_movement",
        "choose_movement",
        "chosen_route",
        "chosen_target",
        "default_gate_fact",
        "default_gatefact",
        "failure",
        "quality",
        "queue",
        "retry_policy",
        "runtime",
        "scheduler",
        "success",
        "verdict",
    }
)
_GRAPH_PLAN_FORBIDDEN_GROUP_WORDS: tuple[str, ...] = (
    "success",
    "failure",
    "quality",
    "verdict",
    "approved",
    "movement authority",
    "source truth",
)

def _optional_text_from_mapping(value: Mapping[str, Any], key: str) -> str | None:
    return _optional_text_value(value.get(key))

def _agent_run_not_proven() -> tuple[str, ...]:
    return _DEFAULT_NOT_PROVEN

def _mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value

def _require_mapping_value(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return value

def _require_only_keys(
    name: str,
    value: Mapping[str, Any],
    allowed: frozenset[str],
) -> None:
    for key in value:
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{name} keys must be non-empty text")
        if key not in allowed:
            raise ValueError(f"{name} contains unadmitted key {key!r}")

def _required_text(field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank")
    return cleaned

def _optional_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError("optional value must be text")
    return value.strip()

def _optional_text_or_none(value: Any) -> str | None:
    text = _optional_text(value)
    return text or None

def _optional_text_value(value: Any) -> str | None:
    return _optional_text_or_none(value)

def _path_segment(field_name: str, value: Any) -> str:
    cleaned = _required_text(field_name, value)
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        raise ValueError(f"{field_name} must be one path segment")
    return cleaned

def _resource_slug(field_name: str, value: Any) -> str:
    cleaned = _path_segment(field_name, value)
    if ":" in cleaned:
        raise ValueError(f"{field_name} resource slug must not contain ':'")
    if not cleaned.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"{field_name} resource slug contains unsupported characters")
    return cleaned

def _json_resource_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Agent Object resource not found: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Agent Object resource must be JSON-compatible YAML: {path}") from exc
    return _require_mapping_value(str(path), value)

def _first_text(values: tuple[str, ...]) -> str:
    if not values:
        raise ValueError("required text sequence is empty")
    return values[0]

def _text_tuple(field_name: str, values: Iterable[str] | str | None) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = (values,)
    result: list[str] = []
    for index, value in enumerate(values):
        result.append(_required_text(f"{field_name}[{index}]", value))
    return tuple(result)

def _merge_texts(*values: Any) -> tuple[str, ...]:
    merged: list[str] = []
    for value in values:
        for item in _text_tuple("merged_texts", value):
            if item not in merged:
                merged.append(item)
    return tuple(merged)


def evidence_list_has_repository_artifact_ref(value: Any) -> bool:
    """True when an evidence ref list contains an inspected repo artifact ref."""

    if not isinstance(value, (list, tuple)):
        return False
    return any(
        isinstance(item, str) and bool(_REPOSITORY_ARTIFACT_REF_RE.search(item))
        for item in value
    )


def _raw_ref(kind: str, index: int) -> str:
    return f"raw:{kind}:{index:02d}"


def _event_raw_ref(event_type: str, index: int) -> str:
    if event_type.startswith("agent_"):
        return _raw_ref("agent", index)
    if event_type.startswith("link_"):
        return _raw_ref("link", index)
    return _raw_ref("brick", index)


def _step_fact_ref(kind: str, index: int, step_ref: str) -> str:
    slug = _resource_slug("step_ref", step_ref.replace(":", "-"))
    return f"{kind}:{index:02d}:{slug}"


def _default_brick_work_ref(brick_instance_id: str) -> str:
    """Derive a default brick_work_ref for a brick_instance_id.

    A work brick id (``brick-<slug>``) maps to a ``work:<slug>`` ref so the map
    does not echo the instance id back as its own work ref. An already-namespaced
    id (one containing ``:``, e.g. a ``building-boundary:`` terminal node) is a
    boundary, not work, so it is returned verbatim.
    """

    if ":" in brick_instance_id:
        return brick_instance_id
    if brick_instance_id.startswith("brick-"):
        return "work:" + brick_instance_id[len("brick-") :]
    return brick_instance_id


def _normalize_key(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()

def _validate_no_payload_forbidden(
    name: str,
    value: Any,
    forbidden_keys: frozenset[str],
) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str) or not raw_key.strip():
                raise ValueError(f"{name} contains non-text or blank key")
            key = _normalize_key(raw_key)
            if key in forbidden_keys:
                raise ValueError(f"{name} contains forbidden key {raw_key!r}")
            _validate_no_payload_forbidden(f"{name}.{raw_key}", child, forbidden_keys)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_payload_forbidden(f"{name}[{index}]", child, forbidden_keys)
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in _RAW_SECRET_PATTERNS):
            raise ValueError(f"{name} contains raw credential-looking text")

def _reject_session_like_text(label: str, value: Any) -> None:
    for position_label, text in _iter_string_positions(label, value):
        if _SESSION_LIKE_UUID_TEXT_RE.search(text) or _SESSION_LIKE_ULID_TEXT_RE.search(text):
            raise ValueError(f"{position_label} contains session-id-shaped text")

def _iter_string_positions(label: str, value: Any):
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_label = f"{label}.{key}" if isinstance(key, str) and key.strip() else f"{label}.<key>"
            if isinstance(key, str):
                yield f"{label}.<key>", key
            yield from _iter_string_positions(child_label, child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_string_positions(f"{label}[{index}]", child)
    elif isinstance(value, str):
        yield label, value

def _looks_like_agent_endpoint(value: str) -> bool:
    lowered = value.strip().lower()
    return (
        lowered.startswith("agent:")
        or lowered.startswith("agent-")
        or lowered.startswith("agent-object:")
        or "/agent/" in lowered
    )

def _proof_limits_tuple(values: Iterable[str] | str | None) -> tuple[str, ...]:
    if values is None:
        return _DEFAULT_PROOF_LIMITS
    if isinstance(values, str):
        values = (values,)
    facts: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise TypeError(f"proof_limits[{index}] must be text")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"proof_limits[{index}] must not be blank")
        facts.append(cleaned)
    return tuple(facts) or _DEFAULT_PROOF_LIMITS

def _require_fact(field_name: str, value: object, expected_type: type[_FACT_T]) -> _FACT_T:
    if not isinstance(value, expected_type):
        raise TypeError(f"{field_name} must be {expected_type.__name__}")
    return value

def _optional_fact(
    field_name: str,
    value: object | None,
    expected_type: type[_FACT_T] | str,
    expected_name: str | None = None,
) -> _FACT_T | object | None:
    if value is None:
        return None
    if isinstance(expected_type, str):
        return _require_named_fact(field_name, value, expected_type, expected_name or "")
    return _require_fact(field_name, value, expected_type)

def _require_named_fact(
    field_name: str,
    value: object,
    expected_module: str,
    expected_name: str,
) -> object:
    value_type = value.__class__
    if value_type.__module__ != expected_module or value_type.__name__ != expected_name:
        raise TypeError(f"{field_name} must be {expected_name}")
    return value

def _require_matching_movement(
    link_fact: MovementFact,
    transition_fact: TransitionFact,
) -> None:
    if transition_fact.movement != link_fact.movement:
        raise ValueError("transition_fact.movement must match link_fact.movement")

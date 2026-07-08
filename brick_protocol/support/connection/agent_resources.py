"""Agent resource resolver and renderer for AGENT-RESOURCE-TOOLKIT-0.

This support surface reads Agent-axis resource files and returns
JSON-compatible packets. It does not write provider-native files, call
providers, execute hooks/tools, choose Movement, or own Agent meaning.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.agent.performance import NATIVE_DISPATCH_PERFORMANCE_MODE
from .adapter_constants import (
    ADAPTER_CODEX_LOCAL as _ADAPTER_CODEX_LOCAL,
    ADAPTER_CLAUDE_LOCAL as _ADAPTER_CLAUDE_LOCAL,
    ALLOWED_ADAPTER_REFS as _ALLOWED_ADAPTER_REFS,
    MODEL_PROVIDER_BY_ADAPTER as _MODEL_PROVIDER_BY_ADAPTER,
    WRITE_TIER_TOOL_POLICY_REFS as _WRITE_TIER_TOOL_POLICY_REFS,
    _OBSERVED_WRITE_ADAPTER_REFS,
)
from .agent_adapter import (
    adapter_is_write_capable,
)
from brick_protocol.support.operator.primitives import (
    CASTING_FIELDS,
    NATIVE_TARGET_CLAUDE,
    NATIVE_TARGET_CODEX,
    selected_key,
)
# AGENT-OBJECT SCHEMA single source (③ struct-surgery 0623): the agent-object
# key/ref/forbidden sets are Agent-axis property and live ONCE on the axis at
# brick_protocol/agent/spec.AGENT_OBJECT_SCHEMA. This support load path IMPORTS the schema (never
# a hand copy) to validate the loaded agent-object's key-set and to coerce the
# ref fields. ``validate_agent_object_keys`` is the SAME key-set gate the inline
# compose path (agent.spec.agent()) runs, so both paths admit/reject identically.
from brick_protocol.agent.spec import (
    AGENT_OBJECT_SCHEMA,
    validate_agent_object_keys,
)


_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
_ALLOWED_LANES = frozenset(
    {
        "leader",
        "worker",
        "reviewer",
        "monitor",
        "report",
        "external",
        NATIVE_DISPATCH_PERFORMANCE_MODE,
    }
)
_HOOK_INSTRUCTION_CHAIN_READ = "hook:instruction-chain-read"
_HOOK_LEADER_WRITE_NEED_GATE = "hook:leader-write-need-gate"
_HOOK_REVIEWER_NO_MUTATION = "hook:reviewer-no-mutation"
_HOOK_RESOURCE_REF_REDACTION = "hook:resource-ref-redaction"
_TOOL_POLICY_LEADER_COORDINATION = "tool-policy:leader-coordination"
_TOOL_POLICY_PROBE_WRITE_SCOPED = "tool-policy:probe-write-scoped"
_TOOL_POLICY_READ_WRITE_SCOPED = "tool-policy:read-write-scoped"
_TOOL_POLICY_REVIEWER_READONLY = "tool-policy:reviewer-readonly"
_TOOL_POLICY_WEB_CAPABLE = "tool-policy:web-capable"
# WAVE-B renames (0610): a retired name stated the OPPOSITE of current law
# (e.g. the leader policy is scoped-write coordination, not readonly). A
# retired name on an Agent Object REJECTS loudly naming the canonical
# replacement -- it never silently resolves and never falls through to a
# vague missing-file error.
_RETIRED_TOOL_POLICY_REFS: dict[str, str | None] = {
    "tool-policy:leader-readonly": _TOOL_POLICY_LEADER_COORDINATION,
    "tool-policy:review-readonly": _TOOL_POLICY_REVIEWER_READONLY,
    # deleted outright (0610): 0 binders ever; support surfaces are readers by
    # construction, not Agent tool-policy holders.
    "tool-policy:support-readonly": None,
}
_RETIRED_HOOK_REFS: dict[str, str | None] = {
    "hook:leader-no-code": _HOOK_LEADER_WRITE_NEED_GATE,
}
# Codex has NO per-agent tool allow/deny list. Native tool scope is only
# sandbox_mode (+ which MCP servers are attached). We MAP from the Agent's
# Brick-axis tool-policy: the single read-write-scoped policy (worker or leader
# lane) projects to "workspace-write"; every read-only policy (reviewer /
# support) projects to "read-only". This is a support projection of an existing
# Brick/Agent decision, not a new authority -- Codex still cannot enforce the
# return shape, the Link gate, or the evidence spine (see the honesty note the
# renderer stamps into developer_instructions + the trailing TOML comment).
_CODEX_SANDBOX_WORKSPACE_WRITE = "workspace-write"
_CODEX_SANDBOX_READ_ONLY = "read-only"
_NATIVE_GRANT_SCHEMA = "native-grant/v1"
_NATIVE_GRANT_RESOLUTION_SCHEMA = "native-grant-resolution/v1"
_NATIVE_GRANT_CAPABILITY_READ = "read"
_NATIVE_GRANT_CAPABILITY_WRITE = "write"
_NATIVE_GRANT_CAPABILITY_WEB = "web"
_NATIVE_GRANT_CAPABILITY_ORDER = (
    _NATIVE_GRANT_CAPABILITY_READ,
    _NATIVE_GRANT_CAPABILITY_WRITE,
    _NATIVE_GRANT_CAPABILITY_WEB,
)
_SEMANTIC_CAPABILITY_READ = "read"
_SEMANTIC_CAPABILITY_PROBE_WRITE = "probe_write"
_SEMANTIC_CAPABILITY_VERIFICATION_WRITE = "verification_write"
_SEMANTIC_CAPABILITY_SOURCE_WRITE = "source_write"
_SEMANTIC_CAPABILITY_ARTIFACT_WRITE = "artifact_write"
_SEMANTIC_CAPABILITY_WRITE_CLASSES = frozenset(
    {
        _SEMANTIC_CAPABILITY_PROBE_WRITE,
        _SEMANTIC_CAPABILITY_VERIFICATION_WRITE,
        _SEMANTIC_CAPABILITY_SOURCE_WRITE,
        _SEMANTIC_CAPABILITY_ARTIFACT_WRITE,
    }
)
_SEMANTIC_CAPABILITY_ORDER = (
    _SEMANTIC_CAPABILITY_READ,
    _SEMANTIC_CAPABILITY_PROBE_WRITE,
    _SEMANTIC_CAPABILITY_VERIFICATION_WRITE,
    _SEMANTIC_CAPABILITY_SOURCE_WRITE,
    _SEMANTIC_CAPABILITY_ARTIFACT_WRITE,
)
_SEMANTIC_CAPABILITY_CEILING_SCHEMA = "agent-semantic-capability-ceiling/v1"
_REVIEWER_MAX_SEMANTIC_CAPABILITY_CLASSES = frozenset(
    {
        _SEMANTIC_CAPABILITY_READ,
        _SEMANTIC_CAPABILITY_PROBE_WRITE,
        _SEMANTIC_CAPABILITY_VERIFICATION_WRITE,
    }
)
_REVIEWER_BLOCKED_SEMANTIC_CAPABILITY_CLASSES = frozenset(
    {
        _SEMANTIC_CAPABILITY_SOURCE_WRITE,
        _SEMANTIC_CAPABILITY_ARTIFACT_WRITE,
    }
)
_NATIVE_GRANT_ALLOWED_KEYS = frozenset(
    {
        "schema",
        "capabilities",
        "write_mode",
        "web_scope",
        "exfiltration_enforced",
        "proof_limits",
    }
)
# CASTING keys are DERIVED from the single-source CASTING_FIELDS (each dial's
# Agent-source ``preferred_<base>`` field_name + its node-layer ``selected_<base>``
# key) so a NEW casting dial (e.g. effort) is auto-forbidden in a native_grant with
# no edit here. The bare ``model`` / ``model_ref`` legacy aliases stay covered, plus
# the NON-casting secret keys (credential / session) that are not casting dials.
_NATIVE_GRANT_CASTING_FORBIDDEN_KEYS = frozenset(
    field_name for descriptor in CASTING_FIELDS for field_name in (
        descriptor.field_name,
        selected_key(descriptor),
    )
)
_NATIVE_GRANT_FORBIDDEN_KEYS = _NATIVE_GRANT_CASTING_FORBIDDEN_KEYS | frozenset(
    {
        "model",
        "model_ref",
        "credential",
        "credential_body",
        "setup_token",
        "setup_token_value",
        "session_id",
        "provider_session_id",
    }
)
# Claude DOES have a real per-agent tool allow/deny list in a subagent .md
# (`tools` allowlist + optional `disallowedTools` denylist). Unlike Codex (which
# has only sandbox_mode), the SAME Brick-axis tool-policy must project to a
# DIFFERENT native shape here: a concrete list of Claude tool names. We MAP the
# single read-write-scoped policy (worker or leader lane) to a write-CAPABLE tool
# set (Read + Grep + Glob + Edit + Write + Bash); every read-only policy (reviewer /
# support, or a leader without read-write-scoped) maps to a read-ONLY tool set
# (Read + Grep + Glob, NO Edit/Write/Bash).
# This is a support projection of an existing Brick/Agent decision, not a new
# authority -- Claude still cannot enforce the return shape, the Link gate, or
# the evidence spine (see the honesty note the renderer stamps into the body).
_CLAUDE_TOOLS_READ_ONLY = ("Read", "Grep", "Glob")
_CLAUDE_TOOLS_WRITE_EXTRA = ("Edit", "Write", "Bash")
_CLAUDE_TOOLS_WEB = ("WebFetch", "WebSearch")
_CLAUDE_TOOLS_BY_NATIVE_CAPABILITY = {
    _NATIVE_GRANT_CAPABILITY_READ: _CLAUDE_TOOLS_READ_ONLY,
    _NATIVE_GRANT_CAPABILITY_WRITE: _CLAUDE_TOOLS_WRITE_EXTRA,
    _NATIVE_GRANT_CAPABILITY_WEB: _CLAUDE_TOOLS_WEB,
}
_CLAUDE_CANONICAL_TOOL_UNIVERSE = tuple(
    tool
    for capability in _NATIVE_GRANT_CAPABILITY_ORDER
    for tool in _CLAUDE_TOOLS_BY_NATIVE_CAPABILITY[capability]
)
_RETIRED_WRITE_ADAPTER_REFS = frozenset(
    {
        "adapter:codex-write-local",
        "adapter:claude-write-local",
    }
)
_PROVIDER_IDENTITY_SUFFIXES = (
    "-codex",
    "-claude",
    "-gemini",
    "-openai",
    "-anthropic",
    "-google",
)
_PROOF_LIMITS = (
    "support resolver evidence only",
    "Agent resource meaning remains owned by brick_protocol/agent/",
    "projection seeds are returned dictionaries only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
_NOT_PROVEN = (
    "Codex native sync",
    "Claude native sync",
    "MCP projection behavior",
    "provider quality",
    "tool or hook execution",
    "future Building correctness",
    "source truth",
    "success judgment",
    "quality judgment",
    "Movement authority",
)
# Agent-object key/ref/forbidden sets sourced from the ONE schema (③ struct-surgery
# 0623). These are ALIASES of the Agent-axis single source — NOT re-definitions:
# the literal members live ONLY in brick_protocol/agent/spec.AGENT_OBJECT_SCHEMA, so support holds
# no hand copy (the mirror guard + check_agent_object_schema_single_source stay
# green). Existing readers (the load path below, check_agent_resource_resolution)
# keep their names through these aliases.
_AGENT_OBJECT_KEYS = AGENT_OBJECT_SCHEMA.allowed_keys
_AGENT_OBJECT_HEAD_KEYS = AGENT_OBJECT_SCHEMA.head_keys
_REF_FIELDS = AGENT_OBJECT_SCHEMA.ref_fields
_FORBIDDEN_AGENT_OBJECT_KEYS = AGENT_OBJECT_SCHEMA.forbidden_keys


class AgentResourceError(ValueError):
    """Raised when an Agent resource reference cannot be resolved safely."""


# CHARTER-INJECT (0618): the kind label every charter resource carries (a
# project README delivered into the work packet so the work/qa/closure Agent
# knows WHAT project it is building and WHY before it judges anything). This is
# a soft INJECTION (the Agent reads it); it is NOT enforcement (no checker uses
# it to block) and it carries NO Movement / success / quality authority.
_CHARTER_RESOURCE_KIND = "charter"


def _repo_root(repo_root: str | Path | None) -> Path:
    repo = Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT
    if repo.name == "brick_protocol" and (repo / "agent" / "objects").is_dir():
        return repo.parent
    return repo


def _agent_objects_dir(repo: Path) -> Path:
    if repo.name == "brick_protocol" and (repo / "agent" / "objects").is_dir():
        return repo / "agent" / "objects"
    return repo / "brick_protocol" / "agent" / "objects"


def list_agent_object_refs(repo_root: str | Path | None = None) -> list[str]:
    """List admitted Agent Object refs from brick_protocol/agent/objects/*.yaml."""

    repo = _repo_root(repo_root)
    object_dir = _agent_objects_dir(repo)
    if not object_dir.is_dir():
        raise AgentResourceError(f"missing Agent Object directory: {object_dir}")
    refs: list[str] = []
    for path in sorted(object_dir.glob("*.yaml")):
        role = path.stem
        _reject_provider_specific_role(role)
        refs.append(f"agent-object:{role}")
    return refs


def _reject_provider_specific_role(role: str) -> None:
    if any(role.endswith(suffix) for suffix in _PROVIDER_IDENTITY_SUFFIXES):
        raise AgentResourceError(f"provider-specific Agent identity is not admitted: {role}")


def _normalize_role(role_or_ref: str, repo: Path) -> str:
    if not isinstance(role_or_ref, str) or not role_or_ref.strip():
        raise AgentResourceError("role_or_ref must be a non-empty string")
    value = role_or_ref.strip()
    role = value.removeprefix("agent-object:") if value.startswith("agent-object:") else value
    _reject_provider_specific_role(role)
    if f"agent-object:{role}" not in set(list_agent_object_refs(repo)):
        raise AgentResourceError("role_or_ref must reference an admitted brick_protocol/agent/objects/*.yaml resource")
    return role


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise AgentResourceError(f"missing Agent resource: {path}")
    return path.read_text(encoding="utf-8")


def _read_data(path: Path) -> Any:
    text = _read_text(path)
    return json.loads(text)


def _require_mapping(label: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AgentResourceError(f"{label} must be a JSON object")
    return dict(value)


def _ref_slug(ref: str, prefix: str) -> str:
    if not isinstance(ref, str) or not ref.startswith(prefix):
        raise AgentResourceError(f"reference {ref!r} must start with {prefix!r}")
    slug = ref.removeprefix(prefix)
    if not slug or not slug.replace("-", "").replace("_", "").isalnum():
        raise AgentResourceError(f"reference {ref!r} has invalid slug")
    return slug


def _string_list(label: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AgentResourceError(f"{label} must be an array of strings")
    return list(value)


def _string_sequence(label: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise AgentResourceError(f"{label} must be an array of strings")
    return list(value)


def _validate_native_grant(
    label: str,
    policy: Mapping[str, Any],
    *,
    expected_ref: str | None = None,
) -> dict[str, Any]:
    policy_ref = policy.get("tool_policy_ref")
    if not isinstance(policy_ref, str) or not policy_ref.strip():
        raise AgentResourceError(f"{label}: tool_policy_ref must be non-empty text")
    policy_ref = policy_ref.strip()
    if expected_ref is not None and policy_ref != expected_ref:
        raise AgentResourceError(f"{label}: tool_policy_ref must match {expected_ref}")
    grant_raw = policy.get("native_grant")
    if not isinstance(grant_raw, Mapping):
        raise AgentResourceError(f"{label}: missing native_grant JSON object")
    grant = dict(grant_raw)
    forbidden = sorted(set(grant) & _NATIVE_GRANT_FORBIDDEN_KEYS)
    if forbidden:
        raise AgentResourceError(f"{label}: native_grant carries forbidden keys: {', '.join(forbidden)}")
    unknown = sorted(set(grant) - _NATIVE_GRANT_ALLOWED_KEYS)
    if unknown:
        raise AgentResourceError(f"{label}: native_grant has unknown keys: {', '.join(unknown)}")
    if grant.get("schema") != _NATIVE_GRANT_SCHEMA:
        raise AgentResourceError(f"{label}: native_grant.schema must be {_NATIVE_GRANT_SCHEMA}")
    capabilities = _string_list(f"{label}:native_grant.capabilities", grant.get("capabilities"))
    if not capabilities:
        raise AgentResourceError(f"{label}: native_grant.capabilities must not be empty")
    seen: set[str] = set()
    for capability in capabilities:
        if capability not in _NATIVE_GRANT_CAPABILITY_ORDER:
            raise AgentResourceError(
                f"{label}: native_grant capability {capability!r} is not admitted"
            )
        if capability in seen:
            raise AgentResourceError(f"{label}: native_grant capability {capability!r} is duplicated")
        seen.add(capability)
    ordered = [cap for cap in _NATIVE_GRANT_CAPABILITY_ORDER if cap in seen]
    if capabilities != ordered:
        raise AgentResourceError(
            f"{label}: native_grant.capabilities must use admitted order {ordered!r}"
        )
    if _NATIVE_GRANT_CAPABILITY_WRITE in seen:
        if policy_ref not in _WRITE_TIER_TOOL_POLICY_REFS:
            raise AgentResourceError(
                f"{label}: native_grant write capability is pinned to "
                + " or ".join(sorted(_WRITE_TIER_TOOL_POLICY_REFS))
            )
        if grant.get("write_mode") != "runtime_intersection":
            raise AgentResourceError(
                f"{label}: native_grant.write_mode must be runtime_intersection"
            )
    elif "write_mode" in grant:
        raise AgentResourceError(f"{label}: native_grant.write_mode requires write capability")
    if _NATIVE_GRANT_CAPABILITY_WEB in seen:
        if grant.get("web_scope") != "exfiltration_not_enforced":
            raise AgentResourceError(
                f"{label}: native_grant.web_scope must be exfiltration_not_enforced"
            )
        if grant.get("exfiltration_enforced") is not False:
            raise AgentResourceError(
                f"{label}: native_grant.exfiltration_enforced must be false"
            )
    elif "web_scope" in grant or "exfiltration_enforced" in grant:
        raise AgentResourceError(
            f"{label}: native_grant web fields require web capability"
        )
    if "proof_limits" in grant:
        _string_list(f"{label}:native_grant.proof_limits", grant["proof_limits"])
    return {
        **grant,
        "capabilities": capabilities,
    }


def _validate_semantic_capability_classes(
    label: str,
    policy: Mapping[str, Any],
    *,
    native_capabilities: Sequence[str],
) -> list[str]:
    semantic_classes = _string_list(
        f"{label}:semantic_capability_classes",
        policy.get("semantic_capability_classes"),
    )
    if not semantic_classes:
        raise AgentResourceError(f"{label}: semantic_capability_classes must not be empty")
    seen: set[str] = set()
    for semantic_class in semantic_classes:
        if semantic_class not in _SEMANTIC_CAPABILITY_ORDER:
            raise AgentResourceError(
                f"{label}: semantic_capability_class {semantic_class!r} is not admitted"
            )
        if semantic_class in seen:
            raise AgentResourceError(
                f"{label}: semantic_capability_class {semantic_class!r} is duplicated"
            )
        seen.add(semantic_class)
    ordered = [cap for cap in _SEMANTIC_CAPABILITY_ORDER if cap in seen]
    if semantic_classes != ordered:
        raise AgentResourceError(
            f"{label}: semantic_capability_classes must use admitted order {ordered!r}"
        )
    native_write = _NATIVE_GRANT_CAPABILITY_WRITE in set(native_capabilities)
    semantic_writes = sorted(set(semantic_classes) & _SEMANTIC_CAPABILITY_WRITE_CLASSES)
    if semantic_writes and not native_write:
        raise AgentResourceError(
            f"{label}: semantic write classes require native_grant write capability: "
            + ", ".join(semantic_writes)
        )
    return semantic_classes


def _validate_tool_policy_resource(
    label: str,
    value: Any,
    *,
    expected_ref: str,
) -> dict[str, Any]:
    policy = _require_mapping(label, value)
    grant = _validate_native_grant(label, policy, expected_ref=expected_ref)
    semantic_classes = _validate_semantic_capability_classes(
        label,
        policy,
        native_capabilities=grant["capabilities"],
    )
    return {
        **policy,
        "semantic_capability_classes": semantic_classes,
        "native_grant": grant,
    }


def _load_agent_object(role: str, repo: Path) -> dict[str, Any]:
    path = repo / "brick_protocol" / "agent" / "objects" / f"{role}.yaml"
    agent_object = _require_mapping(str(path), _read_data(path))
    # KEY-SET gate via the ONE schema (③ struct-surgery 0623): the same
    # ``validate_agent_object_keys`` the inline compose path runs. Passing
    # ``str(path)`` as the label reproduces the prior load-path error text
    # byte-identically (``{path}: unknown/forbidden Agent Object keys: ...``).
    try:
        validate_agent_object_keys(str(path), agent_object)
    except ValueError as exc:
        raise AgentResourceError(str(exc)) from exc
    expected_ref = f"agent-object:{role}"
    if agent_object.get("object_ref") != expected_ref:
        raise AgentResourceError(f"{path}: object_ref must be {expected_ref}")
    if agent_object.get("name") != role:
        raise AgentResourceError(f"{path}: name must be {role}")
    for key in ("object_ref", "name", "lane"):
        if not isinstance(agent_object.get(key), str) or not agent_object[key]:
            raise AgentResourceError(f"{path}: {key} must be a non-empty string")
    lane = str(agent_object["lane"])
    if lane not in _ALLOWED_LANES:
        raise AgentResourceError(f"{path}: lane must be one of {sorted(_ALLOWED_LANES)}")
    for key in ("callable_performer_refs", *_REF_FIELDS):
        agent_object[key] = _string_list(f"{path}:{key}", agent_object.get(key, []))
    _validate_agent_authority(role, agent_object, path)
    return agent_object


def _validate_agent_authority(role: str, agent_object: Mapping[str, Any], path: Path) -> None:
    lane = str(agent_object["lane"])
    hook_refs = set(agent_object.get("hook_refs", []))
    tool_policy_refs = set(agent_object.get("tool_policy_refs", []))
    adapter_refs = set(agent_object.get("adapter_refs", []))
    retired_adapters = sorted(adapter_refs & _RETIRED_WRITE_ADAPTER_REFS)
    if retired_adapters:
        raise AgentResourceError(
            f"{path}: retired/unadmitted active adapter_refs: {', '.join(retired_adapters)}"
        )
    for retired_ref in sorted(tool_policy_refs & set(_RETIRED_TOOL_POLICY_REFS)):
        replacement = _RETIRED_TOOL_POLICY_REFS[retired_ref]
        raise AgentResourceError(
            f"{path}: retired tool policy ref {retired_ref}: "
            + (
                f"use {replacement}"
                if replacement
                else "retired outright with no replacement (never bound by any Agent Object)"
            )
        )
    if _TOOL_POLICY_WEB_CAPABLE in tool_policy_refs and role not in {"pm-lead", "design-lead"}:
        raise AgentResourceError(
            f"{path}: tool-policy:web-capable is admitted only for pm-lead and design-lead"
        )
    for retired_ref in sorted(hook_refs & set(_RETIRED_HOOK_REFS)):
        replacement = _RETIRED_HOOK_REFS[retired_ref]
        raise AgentResourceError(
            f"{path}: retired hook ref {retired_ref}: "
            + (
                f"use {replacement}"
                if replacement
                else "retired outright with no replacement"
            )
        )
    unknown_adapters = sorted(adapter_refs - _ALLOWED_ADAPTER_REFS)
    if unknown_adapters:
        raise AgentResourceError(f"{path}: unknown adapter_refs: {', '.join(unknown_adapters)}")
    # E2/S6 (mirror M9): per-dial validation LOOPS CASTING_FIELDS instead of two
    # hand blocks. The constitutional asymmetry is descriptor DATA: the fail-closed
    # adapter dial must be a member of the Agent Object's own adapter_refs; the
    # deferrable model dial (``inherits_source_of`` the adapter) requires the
    # adapter dial to be present AND to carry an admitted model provider, then
    # validates the model ref against it. Each cleaned ``preferred_*`` value is
    # threaded so the model dial can read the (post-strip) adapter it inherits.
    # Byte-identical accept/raise + messages to the prior blocks (adapter dial
    # validated first, exactly as before).
    cleaned: dict[str, str | None] = {}
    for descriptor in CASTING_FIELDS:
        value = agent_object.get(descriptor.field_name)
        if value is None:
            cleaned[descriptor.field_name] = None
            continue
        if not isinstance(value, str) or not value.strip():
            raise AgentResourceError(f"{path}: {descriptor.field_name} must be non-empty text")
        value = value.strip()
        cleaned[descriptor.field_name] = value
        if descriptor.fail_closed:
            # The fail-closed adapter dial's value MUST be a member of the Agent
            # Object's own adapter_refs (the constitutional asymmetry stays here:
            # support refuses an adapter the Agent Object never declared).
            if value not in adapter_refs:
                raise AgentResourceError(
                    f"{path}: {descriptor.field_name} must be one of adapter_refs: "
                    f"{value}"
                )
        else:
            # Deferrable dials (model/effort/...) DISPATCH to the descriptor's own
            # validate hook against the (post-strip) adapter they inherit. The dial
            # ships its whole admission policy in ONE row, so a new dial validates
            # here with no new code path. Byte-identical accept/raise to the prior
            # inline model block.
            inherited = cleaned.get(descriptor.inherits_source_of or "")
            try:
                descriptor.validate(value, inherited)
            except ValueError as exc:
                raise AgentResourceError(f"{path}: {descriptor.field_name} rejected: {exc}") from exc
    write_capable_adapter_refs = sorted(
        adapter_ref
        for adapter_ref in adapter_refs
        if adapter_is_write_capable(adapter_ref)
    )
    if _HOOK_INSTRUCTION_CHAIN_READ not in hook_refs:
        raise AgentResourceError(f"{path}: Agent Object must carry hook:instruction-chain-read")
    if _HOOK_RESOURCE_REF_REDACTION not in hook_refs:
        raise AgentResourceError(f"{path}: Agent Object must carry hook:resource-ref-redaction")
    write_tier_refs = tool_policy_refs.intersection(_WRITE_TIER_TOOL_POLICY_REFS)
    if write_tier_refs and lane not in (
        "worker",
        "leader",
        "reviewer",
    ):
        raise AgentResourceError(
            f"{path}: write-tier tool policy is admitted only for worker, leader, or reviewer lane"
        )
    if write_tier_refs and not adapter_refs.intersection(_OBSERVED_WRITE_ADAPTER_REFS):
        raise AgentResourceError(
            f"{path}: missing_adapter_write_capability: write-tier policy "
            "requires an observed-write adapter ref"
        )
    if lane == "leader":
        if _HOOK_LEADER_WRITE_NEED_GATE not in hook_refs:
            raise AgentResourceError(f"{path}: leader lane must carry hook:leader-write-need-gate")
        if _TOOL_POLICY_LEADER_COORDINATION not in tool_policy_refs:
            raise AgentResourceError(f"{path}: leader lane must carry tool-policy:leader-coordination")
    if lane == "reviewer":
        # hook:reviewer-no-mutation ALWAYS holds: QA-attack writes the building
        # WORK-AREA (run real checkers / FIRE / mutation probes -- its true
        # nature) inside the disposable W1 worktree sandbox, but it never mutates
        # customer source-truth and never claims Movement. The hook is the
        # discipline; probe-write-scoped is the work-area write CAPABILITY.
        if _HOOK_REVIEWER_NO_MUTATION not in hook_refs:
            raise AgentResourceError(f"{path}: reviewer lane must carry hook:reviewer-no-mutation")
        # A reviewer MAY carry tool-policy:probe-write-scoped (probe-capable
        # QA-attack); effective write stays gated by a Brick-declared write_scope
        # NEED plus an observed-write adapter. A reviewer WITHOUT probe-write must still carry the read-only
        # reviewer policy (byte-identical to today's reviewer surface).
        if (
            _TOOL_POLICY_PROBE_WRITE_SCOPED not in tool_policy_refs
            and _TOOL_POLICY_REVIEWER_READONLY not in tool_policy_refs
        ):
            raise AgentResourceError(f"{path}: reviewer lane must carry tool-policy:reviewer-readonly")


def _resource_path(repo: Path, ref: str) -> Path:
    if ref.startswith("prompt:"):
        return repo / "brick_protocol" / "agent" / "prompts" / f"{_ref_slug(ref, 'prompt:')}.md"
    if ref.startswith("skill:"):
        return repo / "brick_protocol" / "agent" / "skills" / _ref_slug(ref, "skill:") / "SKILL.md"
    if ref.startswith("tool-policy:"):
        return repo / "brick_protocol" / "agent" / "tool_policies" / f"{_ref_slug(ref, 'tool-policy:')}.yaml"
    if ref.startswith("discipline:"):
        return repo / "brick_protocol" / "agent" / "disciplines" / f"{_ref_slug(ref, 'discipline:')}.md"
    raise AgentResourceError(f"unsupported resource reference: {ref}")


def _text_resources(repo: Path, refs: list[str], *, kind: str) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for ref in refs:
        path = _resource_path(repo, ref)
        resources.append(
            {
                "ref": ref,
                "kind": kind,
                "path": path.relative_to(repo).as_posix(),
                "body": _read_text(path),
            }
        )
    return resources


# SKILLS NATIVE (0623): the kind a manifest skill row carries. A manifest row is a
# LABELED INDEX (name + when-to-use description + path) the build agent FETCHES on
# demand, instead of the whole SKILL.md body inlined eagerly into the CLI prompt.
# Claude triggers natively on the description; codex/gemini read the path on demand.
_SKILL_MANIFEST_RESOURCE_KIND = "skill-manifest"


def _parse_skill_front_matter(path: Path) -> dict[str, str]:
    """Parse ONLY the leading ``--- name: ... description: ... ---`` front-matter.

    Reads the file but returns just the two manifest scalars (name, description) --
    the SKILL.md BODY is never carried into the manifest row (that is the whole
    point: the body is fetched on demand, not eagerly inlined). A skill whose
    front-matter is missing/malformed degrades to empty strings (the renderer falls
    back to the ref slug for name), never crashing the packet."""

    text = _read_text(path)
    name = ""
    description = ""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {"name": name, "description": description}
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("name:"):
            name = stripped[len("name:") :].strip()
        elif stripped.startswith("description:"):
            description = stripped[len("description:") :].strip()
    return {"name": name, "description": description}


def _skill_manifest_resources(repo: Path, skill_refs: list[str]) -> list[dict[str, Any]]:
    """Render skill refs as a MANIFEST (front-matter only), not eager full bodies.

    Each row carries ``ref / kind=skill-manifest / name / description / path`` so the
    runtime packet ships a labeled index the build agent fetches on demand. The
    SKILL.md body is NEVER read into the row -- only the front-matter scalars -- so
    the CLI argv no longer inlines N full skill bodies. The ``path`` is the
    repo-relative SKILL.md so codex/gemini can read-on-demand and claude can locate
    the projected skill file in the isolated HOME."""

    resources: list[dict[str, Any]] = []
    for ref in skill_refs:
        path = _resource_path(repo, ref)
        front = _parse_skill_front_matter(path)
        name = front["name"] or _ref_slug(ref, "skill:")
        resources.append(
            {
                "ref": ref,
                "kind": _SKILL_MANIFEST_RESOURCE_KIND,
                "name": name,
                "description": front["description"],
                "path": path.relative_to(repo).as_posix(),
            }
        )
    return resources


def _charter_resources(repo: Path, project_ref: str | None) -> list[dict[str, Any]]:
    """CHARTER-INJECT (0618): the project's README charter (헌장 — why the
    project exists, what it builds, what it must keep), delivered into EVERY
    role's work packet so a work/qa/closure Agent judges with the project's
    direction in hand instead of blind.

    Mechanism only (Support reads a declared project record; it does NOT own
    project meaning, success, quality, or Movement). The single project_ref ->
    charter README seam is the project_declaration loader, which already
    resolves and validates ``charter_ref`` -> the project's own README.md.

    Graceful degrade (NEVER crash a Building run on a charter problem):
      * ``project_ref is None`` (ref-less / default-root building) -> no charter;
      * a malformed ref or an undeclared/charterless project -> no charter.
    A returned list of 0 or 1 mirrors the other ``_*_resources`` shapes, so the
    packet renderer treats charter exactly like disciplines/skills (add-only).
    """

    if not project_ref:
        return []
    try:
        from brick_protocol.support.operator.project_declaration import (
            PROJECT_REF_PREFIX,
            load_project_declaration,
        )

        if not isinstance(project_ref, str) or not project_ref.startswith(PROJECT_REF_PREFIX):
            return []
        project_id = project_ref[len(PROJECT_REF_PREFIX) :]
        declaration = load_project_declaration(repo, project_id)
        body = declaration.charter_path.read_text(encoding="utf-8")
    except (AgentResourceError, ValueError, OSError, UnicodeDecodeError):
        # Loudly-nothing: a charter problem degrades to "no charter injected",
        # it never aborts the build (the project-declaration checker is the
        # place a missing/broken charter is RED, not the live work packet).
        return []
    return [
        {
            "ref": declaration.charter_ref,
            "kind": _CHARTER_RESOURCE_KIND,
            "project_ref": declaration.project_ref,
            "path": declaration.charter_path.relative_to(repo).as_posix(),
            "body": body,
        }
    ]


def _data_resources(repo: Path, refs: list[str], *, kind: str) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for ref in refs:
        path = _resource_path(repo, ref)
        data = _read_data(path)
        if kind == "tool_policy":
            data = _validate_tool_policy_resource(str(path), data, expected_ref=ref)
        resources.append(
            {
                "ref": ref,
                "kind": kind,
                "path": path.relative_to(repo).as_posix(),
                "data": data,
            }
        )
    return resources


def _empty_native_grant_resolution(
    tool_policy_refs: list[str],
    *,
    missing_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": _NATIVE_GRANT_RESOLUTION_SCHEMA,
        "tool_policy_refs": list(tool_policy_refs),
        "declared_capabilities": [],
        "capabilities": [],
        "declared_semantic_capability_classes": [],
        "semantic_capability_classes": [],
        "write_effective": False,
        "web_requested": False,
        "missing_tool_policy_refs": list(missing_refs or []),
        "proof_limits": [
            "native_grant resolution uses already-loaded tool-policy data only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def _tool_policy_resource_data(label: str, value: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise AgentResourceError(f"{label} item must be a JSON object")
    if "data" in value:
        ref = value.get("ref")
        data = _require_mapping(f"{label}.data", value.get("data"))
    else:
        data = _require_mapping(label, value)
        ref = data.get("tool_policy_ref")
    if not isinstance(ref, str) or not ref.strip():
        raise AgentResourceError(f"{label}: tool-policy resource ref must be non-empty text")
    ref = ref.strip()
    data = _validate_tool_policy_resource(label, data, expected_ref=ref)
    return ref, data


def resolve_native_grant(
    tool_policy_resources: Any,
    *,
    tool_policy_refs: Any | None = None,
    write_need: bool = False,
) -> dict[str, Any]:
    """Resolve already-loaded tool-policy native_grant data into native capability.

    This is the single support chokepoint for CLI grant projection. It is pure:
    callers pass the tool-policy resource data already present in the Agent
    instruction packet; this function never reads files or consults repo globals.
    Missing policy data fails closed to no capabilities. Malformed loaded data
    raises AgentResourceError, which keeps the live Building from projecting an
    ambiguous native grant.
    """

    refs = _string_sequence("tool_policy_refs", tool_policy_refs)
    selected_refs = set(refs)
    if tool_policy_resources is None:
        return _empty_native_grant_resolution(refs)
    if not isinstance(tool_policy_resources, (list, tuple)):
        raise AgentResourceError("tool_policy_resources must be an array")
    loaded_by_ref: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(tool_policy_resources):
        ref, data = _tool_policy_resource_data(f"tool_policy_resources[{index}]", item)
        loaded_by_ref[ref] = data
    if not refs:
        refs = list(loaded_by_ref)
        selected_refs = set(refs)
    missing_refs = sorted(selected_refs - set(loaded_by_ref))
    if missing_refs:
        return _empty_native_grant_resolution(refs, missing_refs=missing_refs)

    declared: set[str] = set()
    declared_semantic: set[str] = set()
    for ref in refs:
        policy = loaded_by_ref.get(ref)
        if policy is None:
            continue
        grant = policy["native_grant"]
        for capability in grant["capabilities"]:
            if capability == _NATIVE_GRANT_CAPABILITY_WRITE and ref not in _WRITE_TIER_TOOL_POLICY_REFS:
                raise AgentResourceError(
                    "native_grant write capability may resolve only from "
                    + " or ".join(sorted(_WRITE_TIER_TOOL_POLICY_REFS))
                )
            declared.add(capability)
        for semantic_class in policy["semantic_capability_classes"]:
            declared_semantic.add(semantic_class)
    declared_ordered = [cap for cap in _NATIVE_GRANT_CAPABILITY_ORDER if cap in declared]
    declared_semantic_ordered = [
        cap for cap in _SEMANTIC_CAPABILITY_ORDER if cap in declared_semantic
    ]
    effective: list[str] = []
    for capability in declared_ordered:
        if capability == _NATIVE_GRANT_CAPABILITY_WRITE:
            if bool(write_need) and selected_refs.intersection(_WRITE_TIER_TOOL_POLICY_REFS):
                effective.append(capability)
            continue
        effective.append(capability)
    effective_semantic: list[str] = []
    for semantic_class in declared_semantic_ordered:
        if semantic_class in _SEMANTIC_CAPABILITY_WRITE_CLASSES:
            if bool(write_need) and selected_refs.intersection(_WRITE_TIER_TOOL_POLICY_REFS):
                effective_semantic.append(semantic_class)
            continue
        effective_semantic.append(semantic_class)
    return {
        "schema": _NATIVE_GRANT_RESOLUTION_SCHEMA,
        "tool_policy_refs": refs,
        "declared_capabilities": declared_ordered,
        "capabilities": effective,
        "declared_semantic_capability_classes": declared_semantic_ordered,
        "semantic_capability_classes": effective_semantic,
        "write_effective": _NATIVE_GRANT_CAPABILITY_WRITE in effective,
        "web_requested": _NATIVE_GRANT_CAPABILITY_WEB in declared,
        "missing_tool_policy_refs": [],
        "proof_limits": [
            "native_grant resolution uses already-loaded tool-policy data only",
            "semantic_capability_classes are Agent policy class evidence, not provider-native tools",
            "write requires Brick write_scope NEED plus an admitted write-tier tool policy",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def resolve_agent_semantic_capability(
    agent_object: Mapping[str, Any],
    tool_policy_resources: Any,
) -> dict[str, Any]:
    """Resolve the Agent-owned semantic capability ceiling from loaded resources.

    Tool policies declare the broad class vocabulary. The Agent Object's lane and
    hook refs can only narrow that maximum; they never create Brick write NEED or
    Link Movement authority.
    """

    agent = _require_mapping("agent_object", agent_object)
    tool_policy_refs = _string_sequence(
        "agent_object.tool_policy_refs",
        agent.get("tool_policy_refs"),
    )
    hook_refs = _string_sequence("agent_object.hook_refs", agent.get("hook_refs"))
    lane = str(agent.get("lane") or "")
    policy_resolution = resolve_native_grant(
        tool_policy_resources,
        tool_policy_refs=tool_policy_refs,
        write_need=True,
    )
    max_classes = list(policy_resolution["semantic_capability_classes"])
    blocked_classes: list[str] = []
    ceiling_reason = "policy_max"
    if lane == "reviewer" and _HOOK_REVIEWER_NO_MUTATION in set(hook_refs):
        blocked_classes = [
            semantic_class
            for semantic_class in max_classes
            if semantic_class in _REVIEWER_BLOCKED_SEMANTIC_CAPABILITY_CLASSES
        ]
        max_classes = [
            semantic_class
            for semantic_class in max_classes
            if semantic_class in _REVIEWER_MAX_SEMANTIC_CAPABILITY_CLASSES
        ]
        ceiling_reason = "reviewer_no_mutation"
    return {
        "schema": _SEMANTIC_CAPABILITY_CEILING_SCHEMA,
        "agent_object_ref": str(agent.get("object_ref") or ""),
        "role": str(agent.get("name") or ""),
        "lane": lane,
        "tool_policy_refs": tool_policy_refs,
        "hook_refs": hook_refs,
        "declared_policy_semantic_capability_classes": list(
            policy_resolution["declared_semantic_capability_classes"]
        ),
        "max_semantic_capability_classes": max_classes,
        "blocked_semantic_capability_classes": blocked_classes,
        "ceiling_reason": ceiling_reason,
        "proof_limits": [
            "Agent policy/resource capability ceiling only",
            "Brick write_scope NEED still controls effective write",
            "Link Movement remains forward/reroute and is not derived here",
            "hook:reviewer-no-mutation blocks source_write for reviewer lane",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def _hook_resources(repo: Path, refs: list[str], object_ref: str) -> dict[str, Any]:
    registry_path = repo / "brick_protocol" / "agent" / "hooks" / "registry.yaml"
    bindings_path = repo / "brick_protocol" / "agent" / "hooks" / "bindings.yaml"
    registry = _require_mapping(str(registry_path), _read_data(registry_path))
    bindings = _require_mapping(str(bindings_path), _read_data(bindings_path))
    hook_registry = _require_mapping("brick_protocol/agent/hooks/registry.yaml:hooks", registry.get("hooks"))
    hook_bindings = _require_mapping("brick_protocol/agent/hooks/bindings.yaml:bindings", bindings.get("bindings"))
    bound_refs = hook_bindings.get(object_ref)
    if not isinstance(bound_refs, list) or not all(isinstance(item, str) for item in bound_refs):
        raise AgentResourceError(f"brick_protocol/agent/hooks/bindings.yaml: missing hook binding for {object_ref}")
    if list(bound_refs) != refs:
        raise AgentResourceError(f"brick_protocol/agent/hooks/bindings.yaml: binding mismatch for {object_ref}")
    selected: list[dict[str, Any]] = []
    for ref in refs:
        definition = _require_mapping(f"brick_protocol/agent/hooks/registry.yaml:{ref}", hook_registry.get(ref))
        if definition.get("execution_opened") is not False:
            raise AgentResourceError(f"brick_protocol/agent/hooks/registry.yaml:{ref}: native hook execution remains closed")
        selected.append({"ref": ref, "definition": definition})
    return {
        "registry_path": "brick_protocol/agent/hooks/registry.yaml",
        "bindings_path": "brick_protocol/agent/hooks/bindings.yaml",
        "selected": selected,
    }


def _resource_refs(agent_object: Mapping[str, Any]) -> dict[str, list[str]]:
    return {field: list(agent_object.get(field, [])) for field in _REF_FIELDS}


def resolve_agent_object(
    role_or_ref: str,
    repo_root: str | Path | None = None,
    *,
    project_ref: str | None = None,
) -> dict[str, Any]:
    """Resolve one Agent Object and its referenced Agent resources.

    CHARTER-INJECT (0618): ``project_ref`` (optional) names the project vessel
    this resolution serves; its README charter is added to every role's
    resources (graceful degrade when absent). It rides ALONGSIDE the existing
    Agent-axis resources and changes none of them.
    """

    repo = _repo_root(repo_root)
    role = _normalize_role(role_or_ref, repo)
    agent_object = _load_agent_object(role, repo)
    object_ref = str(agent_object["object_ref"])
    prompt_refs = list(agent_object["prompt_refs"])
    skill_refs = list(agent_object["skill_refs"])
    tool_policy_refs = list(agent_object["tool_policy_refs"])
    discipline_refs = list(agent_object["discipline_refs"])
    hook_refs = list(agent_object["hook_refs"])
    tool_policy_resources = _data_resources(repo, tool_policy_refs, kind="tool_policy")
    semantic_capability = resolve_agent_semantic_capability(
        agent_object,
        tool_policy_resources,
    )
    return {
        "kind": "agent-resource-resolution",
        "role": role,
        "agent_object": agent_object,
        "resource_refs": _resource_refs(agent_object),
        "prompt_resources": _text_resources(repo, prompt_refs, kind="prompt"),
        "skill_resources": _text_resources(repo, skill_refs, kind="skill"),
        "hook_resources": _hook_resources(repo, hook_refs, object_ref),
        "tool_policy_resources": tool_policy_resources,
        "semantic_capability": semantic_capability,
        "discipline_resources": _text_resources(repo, discipline_refs, kind="discipline"),
        "charter_resources": _charter_resources(repo, project_ref),
        "adapter_refs": list(agent_object["adapter_refs"]),
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def render_agent_team_context(repo_root: str | Path | None = None) -> dict[str, Any]:
    """Render read-only team context from admitted Agent Object resources."""

    repo = _repo_root(repo_root)
    refs = list_agent_object_refs(repo)
    packets = [render_agent_packet(ref, repo_root=repo) for ref in refs]
    return {
        "kind": "agent-team-context",
        "schema_version": "legacy-agent-harness-system-0",
        "source": "brick_protocol/agent/",
        "agent_object_refs": refs,
        "lane_vocabulary": sorted(_ALLOWED_LANES),
        "write_authority_rule": [
            "Brick-declared write_scope",
            "Agent tool_policy_refs",
            # Derived from the canonical observed-write set (codex-local AND
            # claude-local today), never a hardcoded single-provider literal.
            "observed-write adapter capability ("
            + " / ".join(sorted(_OBSERVED_WRITE_ADAPTER_REFS))
            + ")",
            "runner/write observation",
        ],
        "leader_no_code": [
            "leader lane defaults to coordination and evidence requests when no Brick write_scope NEED is declared",
            "leader lane may carry tool-policy:read-write-scoped; write capability is the tool policy plus a write-capable adapter, gated by a Brick-declared write_scope NEED, not by lane",
            "write-capable adapter_refs remain technical capability refs, not authority",
            "write authority requires Brick write_scope plus Agent write policy plus adapter capability plus write observation",
            "effective write requires Brick write_scope, Agent tool policy, adapter support, and observation",
        ],
        "packets": packets,
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def validate_agent_refs(role_or_ref: str, repo_root: str | Path | None = None) -> dict[str, Any]:
    """Validate that one Agent Object's refs resolve without rendering native files."""

    try:
        resolution = resolve_agent_object(role_or_ref, repo_root=repo_root)
    except AgentResourceError as exc:
        role = role_or_ref if isinstance(role_or_ref, str) else ""
        return {
            "kind": "agent-resource-validation",
            "role_or_ref": role,
            "ok": False,
            "violations": [str(exc)],
            "checked_refs": [],
            "proof_limits": list(_PROOF_LIMITS),
            "not_proven": list(_NOT_PROVEN),
        }
    refs: list[str] = []
    for values in resolution["resource_refs"].values():
        refs.extend(values)
    return {
        "kind": "agent-resource-validation",
        "role": resolution["role"],
        "agent_object_ref": resolution["agent_object"]["object_ref"],
        "ok": True,
        "violations": [],
        "checked_refs": sorted(refs),
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def render_agent_packet(
    role_or_ref: str,
    repo_root: str | Path | None = None,
    *,
    project_ref: str | None = None,
) -> dict[str, Any]:
    """Render a JSON-compatible support packet from Agent-axis resources.

    CHARTER-INJECT (0618): when ``project_ref`` is supplied the packet also
    carries the project's README charter (``charter_resources``) so every role
    sees what project it builds; absent/undeclared -> an empty charter list.
    """

    resolution = resolve_agent_object(role_or_ref, repo_root=repo_root, project_ref=project_ref)
    return {
        "kind": "agent-resource-packet",
        "role": resolution["role"],
        "agent_object": resolution["agent_object"],
        "prompt_resources": resolution["prompt_resources"],
        "skill_resources": resolution["skill_resources"],
        "hook_resources": resolution["hook_resources"],
        "tool_policy_resources": resolution["tool_policy_resources"],
        "semantic_capability": resolution["semantic_capability"],
        "discipline_resources": resolution["discipline_resources"],
        "charter_resources": resolution["charter_resources"],
        "adapter_refs": resolution["adapter_refs"],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def render_agent_instruction_packet(
    role_or_ref: str,
    repo_root: str | Path | None = None,
    *,
    project_ref: str | None = None,
) -> dict[str, Any]:
    """Render runtime Agent instructions from Agent resources, not projection seed text.

    CHARTER-INJECT (0618): ``project_ref`` (optional) injects the project's
    README charter into the runtime instruction packet for EVERY role
    (work/qa/closure alike), so the work packet that reaches the provider
    carries WHAT project the Agent builds and WHY. The injection is add-only:
    the existing prompt/skill/discipline/hook/tool-policy resources are
    byte-identical whether or not a charter is present, and an absent or
    undeclared project degrades to an empty ``charter_resources`` list with no
    ``charter_ref`` field (never a crash).
    """

    repo = _repo_root(repo_root)
    packet = render_agent_packet(role_or_ref, repo_root=repo, project_ref=project_ref)
    agent_object = _require_mapping("agent_resource_packet.agent_object", packet["agent_object"])
    charter_resources = list(packet["charter_resources"])
    # SKILLS NATIVE (0623): the RUNTIME packet carries a skill MANIFEST (front-matter
    # index + path), NOT the eager full SKILL.md bodies. The KEY NAME stays
    # ``skill_resources`` (so the kernel non-empty-list pin and the charter
    # byte-identical pin keep passing -- only the item SHAPE changes), but the build
    # agent now fetches a skill on demand instead of receiving every body inlined in
    # the CLI argv. ``render_agent_packet`` (MCP resources, projections) is untouched:
    # it still carries full bodies; only this runtime instruction packet swaps.
    skill_manifest = _skill_manifest_resources(
        repo, list(agent_object.get("skill_refs", []))
    )
    instruction: dict[str, Any] = {
        "kind": "agent-instruction-packet",
        "agent_object_ref": str(agent_object["object_ref"]),
        "role": str(packet["role"]),
        "prompt_resources": list(packet["prompt_resources"]),
        "skill_resources": skill_manifest,
        "hook_resources": packet["hook_resources"],
        "tool_policy_resources": list(packet["tool_policy_resources"]),
        "semantic_capability": dict(packet["semantic_capability"]),
        "discipline_resources": list(packet["discipline_resources"]),
        "charter_resources": charter_resources,
        "adapter_refs": list(packet["adapter_refs"]),
        "proof_limits": [
            "runtime AgentInstructionPacket support input only",
            "not a projection seed",
            "skill_resources carries a fetch-on-demand manifest, not eager bodies",
            *list(packet["proof_limits"]),
        ],
        "not_proven": [
            "skill_manifest_refs is the DECLARED offered set; whether the agent "
            "actually fetched a given skill is NOT observed/recorded",
            *list(packet["not_proven"]),
        ],
    }
    # DECLARED audit (always-on when skills are offered): stamp the manifest refs +
    # paths OFFERED as a TOP-LEVEL fact, mirroring the charter_ref/project_ref
    # stamps. Records WHICH skills were put in front of the agent (the body is no
    # longer in the prompt, so this DECLARED list replaces the implicit-total record
    # the eager inline used to carry).
    #
    # NOT-PROVEN (honest): this is the DECLARED set (what was offered). The OBSERVED
    # "which skills the agent actually fetched" is NOT recorded -- no observed
    # side-channel exists today. The DECLARED stamp does NOT prove a fetch happened.
    if skill_manifest:
        instruction["skill_manifest_refs"] = [
            {"ref": str(row["ref"]), "path": str(row["path"])}
            for row in skill_manifest
        ]
    # Evidence mirror: stamp the injected charter_ref as a TOP-LEVEL fact next
    # to agent_object_ref (the same level the discipline/agent refs record),
    # so any sink that records the instruction packet records WHICH charter the
    # Agent saw. Omitted entirely when no charter was injected (so a charterless
    # building's evidence carries no empty charter_ref claim).
    if charter_resources:
        instruction["charter_ref"] = str(charter_resources[0]["ref"])
        instruction["project_ref"] = str(charter_resources[0]["project_ref"])
    return instruction


def _render_instruction_text(packet: Mapping[str, Any], *, target: str) -> str:
    role = str(packet["role"])
    object_ref = str(packet["agent_object"]["object_ref"])
    lines = [
        f"# Brick Protocol {role.upper()} Projection Seed",
        "",
        f"projection_target: {target}",
        f"agent_object_ref: {object_ref}",
        "",
        "This is a projection seed only. The source remains brick_protocol/agent/.",
        "",
    ]
    for resource in packet.get("charter_resources", []):
        lines.extend(
            [
                f"## Project Charter {resource['ref']}",
                "",
                "Why this project exists, what it builds, and what it must keep. "
                "Judge the work against this direction.",
                "",
                str(resource["body"]).strip(),
                "",
            ]
        )
    for resource in packet["prompt_resources"]:
        lines.extend([f"## Prompt {resource['ref']}", "", str(resource["body"]).strip(), ""])
    for resource in packet["skill_resources"]:
        lines.extend([f"## Skill {resource['ref']}", "", str(resource["body"]).strip(), ""])
    lines.append("## Advisory Hook Refs")
    for hook in packet["hook_resources"]["selected"]:
        lines.append(f"- {hook['ref']}")
    lines.extend(["", "## Tool Policy Refs"])
    for resource in packet["tool_policy_resources"]:
        lines.append(f"- {resource['ref']}")
    semantic_capability = packet.get("semantic_capability")
    if isinstance(semantic_capability, Mapping):
        lines.extend(["", "## Max Semantic Capability Classes"])
        for semantic_class in semantic_capability.get("max_semantic_capability_classes", []):
            lines.append(f"- {semantic_class}")
        blocked = semantic_capability.get("blocked_semantic_capability_classes", [])
        if blocked:
            lines.extend(["", "## Blocked Semantic Capability Classes"])
            for semantic_class in blocked:
                lines.append(f"- {semantic_class}")
    lines.extend(["", "## Disciplines"])
    for resource in packet["discipline_resources"]:
        lines.extend([f"### {resource['ref']}", "", str(resource["body"]).strip(), ""])
    lines.extend(
        [
            "## Proof Limits",
            "",
            *[f"- {item}" for item in packet["proof_limits"]],
            "",
            "## Not Proven",
            "",
            *[f"- {item}" for item in packet["not_proven"]],
            "",
        ]
    )
    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# Codex-native subagent TOML projection (real per-LLM translation)
#
# The legacy _render_instruction_text emits the SAME generic markdown for codex
# and claude; only the projection_target label differed. That is not a real
# per-host translation. A Codex SUBAGENT is a TOML file (~/.codex/agents/
# <name>.toml) with required name / description / developer_instructions and
# optional model / model_reasoning_effort / sandbox_mode. These renderers emit
# that real native form. They write NO files and run NO subprocess -- they
# return strings only; a human (or a later projection-sync) places them.
# ---------------------------------------------------------------------------


_BRICK_MCP_ENFORCED_NOTES = (
    "required_return_shape ENFORCEMENT (the Brick row decides the return shape; "
    "the host LLM cannot enforce it natively)",
    "Link gate sufficiency + Movement (forward / reroute) -- Link + human own "
    "Movement, never this Agent",
    "3-axis evidence spine recording (Brick / Agent / Link)",
    "NEED <-> CAPABILITY agent selection and the hard human MUST-HALT gate",
)


def codex_sandbox_mode_for_native_grant(
    native_grant_resources: Any,
    *,
    tool_policy_refs: Any | None = None,
    write_need: bool = True,
) -> str:
    resolution = resolve_native_grant(
        native_grant_resources,
        tool_policy_refs=tool_policy_refs,
        write_need=write_need,
    )
    if _NATIVE_GRANT_CAPABILITY_WRITE in resolution["capabilities"]:
        return _CODEX_SANDBOX_WORKSPACE_WRITE
    return _CODEX_SANDBOX_READ_ONLY


def codex_sandbox_mode_for_tool_policies(
    tool_policy_refs: Any,
    *,
    write_need: bool = True,
    native_grant_resources: Any | None = None,
) -> str:
    """Map an Agent's Brick-axis tool policy refs to a Codex sandbox_mode.

    Codex has no per-agent tool allow/deny list; native tool scope is only the
    sandbox_mode. A sandbox is granted "workspace-write" ONLY when BOTH the
    Agent carries read-write-scoped AND the STEP's Brick declares a write NEED
    (``write_need`` True == a non-empty write_scope is present). Otherwise --
    every read-only policy, OR a write-capable agent on a read-only Brick (no
    write_scope NEED) -- maps to "read-only". This mirrors effective_write =
    write_scope AND read-write-scoped AND observed-write-adapter: being
    write-CAPABLE never means write-EFFECTIVE absent the Brick NEED.

    ``write_need`` defaults True for the DESCRIPTIVE "what can this agent do"
    projection (the per-agent native subagent file, not tied to a single step);
    a run-time provider invocation FOR A STEP must pass the step's actual
    write_need so the physical sandbox matches the logical effective_write gate.

    This is a support projection of an existing Brick/Agent decision; it grants
    no authority and proves no provider behavior.
    """

    return codex_sandbox_mode_for_native_grant(
        native_grant_resources,
        tool_policy_refs=tool_policy_refs,
        write_need=write_need,
    )


def _toml_basic_string(value: str) -> str:
    """Encode a string as a TOML basic (double-quoted) string."""

    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\b", "\\b")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\f", "\\f")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def _toml_multiline_string(value: str) -> str:
    """Encode a string as a TOML multiline basic string (triple double-quote).

    A leading newline after the opening delimiter is trimmed by TOML, so we add
    one for readability. Backslashes and triple-quote runs are escaped so the
    body can never break out of the literal.
    """

    body = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    # A trailing double-quote would merge with the closing delimiter; escape it.
    if body.endswith('"'):
        body = body[:-1] + '\\"'
    return f'"""\n{body}\n"""'


def _native_casting_lines(agent_object: Mapping[str, Any], target: str) -> list[str]:
    """Project EVERY casting dial to its native-subagent config line(s) generically.

    LOOPS the single-source ``CASTING_FIELDS`` and dispatches each dial's own
    ``native_config_emit`` against the agent object's declared ``preferred_<base>``
    value (absent -> empty string). A NEW casting dial (e.g. effort) reaches the
    native codex .toml / claude .md with NO per-dial code here. BYTE-IDENTICAL to
    the prior hand-written model-only projection: no admitted Agent Object pins a
    model id, so the model dial keeps the historical default (codex omits the
    ``model`` line, claude emits ``model: "inherit"``) and the effort dial — the
    only other line-bearing dial — emits nothing when undeclared.
    """

    lines: list[str] = []
    for descriptor in CASTING_FIELDS:
        value = agent_object.get(descriptor.field_name) or ""
        lines.extend(descriptor.native_config_emit(str(value), target))
    return lines


def _codex_model_key_for_adapter_refs(adapter_refs: list[str]) -> str:
    """Project the Agent's adapter refs to an optional Codex `model` key value.

    Returns "" to OMIT the key (inherit the Codex default). adapter:local is
    in-process (no model), adapter:codex-local inherits the Codex CLI default,
    and adapter:claude-local is not a Codex model -- all three omit. Only a
    concrete non-default codex model id would emit; the admitted Agent Objects
    carry none, so this honestly omits today rather than inventing a model.
    """

    # No admitted Agent Object pins a concrete codex model id, so we inherit.
    # MODEL_PROVIDER_BY_ADAPTER is referenced to keep the mapping honest: a codex
    # adapter is the only one whose model the key could ever carry.
    if _ADAPTER_CODEX_LOCAL in adapter_refs and _MODEL_PROVIDER_BY_ADAPTER.get(
        _ADAPTER_CODEX_LOCAL
    ):
        return ""
    return ""


def _codex_description(packet: Mapping[str, Any]) -> str:
    role = str(packet["role"])
    lane = str(packet["agent_object"]["lane"])
    return (
        f"Brick Protocol {role} agent ({lane} lane). Provider-neutral source in "
        "brick_protocol/agent/; this TOML is a read-only Codex-native projection."
    )


def _codex_developer_instructions(packet: Mapping[str, Any], *, sandbox_mode: str) -> str:
    role = str(packet["role"])
    lane = str(packet["agent_object"]["lane"])
    sections: list[str] = [
        f"You are the Brick Protocol {role} agent ({lane} lane).",
        "",
    ]
    for resource in packet["prompt_resources"]:
        body = str(resource["body"]).strip()
        if body:
            sections.extend([f"## Prompt ({resource['ref']})", "", body, ""])
    disciplines = packet["discipline_resources"]
    if disciplines:
        sections.append("## Disciplines (summary)")
        sections.append("")
        for resource in disciplines:
            first_line = next(
                (
                    line.strip().lstrip("# ").strip()
                    for line in str(resource["body"]).splitlines()
                    if line.strip()
                ),
                resource["ref"],
            )
            sections.append(f"- {resource['ref']}: {first_line}")
        sections.append("")
    sections.extend(
        [
            "## Native scope (Codex sandbox)",
            "",
            (
                f"sandbox_mode = {sandbox_mode} (mapped from this agent's Brick-axis "
                "tool policy). Codex has no per-agent tool allow/deny list; the "
                "sandbox is the only native tool boundary."
            ),
            "",
            "## Enforced by Brick MCP, NOT by Codex",
            "",
            (
                "The following are NOT expressible in native Codex config. They are "
                "enforced by the Brick Protocol MCP / engine and remain owned by "
                "their axis:"
            ),
            "",
            *[f"- {note}" for note in _BRICK_MCP_ENFORCED_NOTES],
            "",
            (
                "Return one JSON object matching the Brick row's required_return_shape "
                "(enforced by Brick MCP, not by Codex). Do not claim source truth, do "
                "not judge success or quality, and do NOT choose Movement / route / "
                "target -- Link and human own those."
            ),
        ]
    )
    return "\n".join(sections).strip()


def render_codex_subagent_toml(
    role_or_ref: str,
    repo_root: str | Path | None = None,
) -> str:
    """Render a real Codex-native subagent TOML for an admitted Agent Object.

    Emits a VALID TOML document (parseable by tomllib) with the required Codex
    subagent keys (name, description, developer_instructions) plus an optional
    model (omitted when the agent inherits the Codex default) and a sandbox_mode
    that is MAPPED from the Agent's Brick-axis tool policy (read-write-scoped ->
    workspace-write; every read-only policy -> read-only). A trailing TOML
    comment block lists what Brick MCP enforces (return shape, Link gate,
    evidence) so the projection is honest about Codex's native limits.

    This is read-only support projection: it writes no file, runs no subprocess,
    calls no provider, chooses no Movement, and owns no Agent meaning.
    """

    packet = render_agent_packet(role_or_ref, repo_root=repo_root)
    role = str(packet["role"])
    tool_policy_refs = list(packet["agent_object"]["tool_policy_refs"])
    tool_policy_resources = list(packet["tool_policy_resources"])
    sandbox_mode = codex_sandbox_mode_for_tool_policies(
        tool_policy_refs,
        native_grant_resources=tool_policy_resources,
    )
    # The casting LINES loop the single-source CASTING_FIELDS, reading the agent
    # object's declared ``preferred_<base>`` values: the model dial omits its line
    # today (no pinned id, byte-identical to the prior _codex_model_key helper) and
    # the effort dial emits ``model_reasoning_effort = "<level>"`` when declared.
    casting_lines = _native_casting_lines(packet["agent_object"], NATIVE_TARGET_CODEX)
    description = _codex_description(packet)
    developer_instructions = _codex_developer_instructions(
        packet, sandbox_mode=sandbox_mode
    )

    lines = [
        "# Brick Protocol Codex-native subagent projection (read-only).",
        "# Source of truth remains brick_protocol/agent/objects/" + f"{role}.yaml; place this at",
        f"# ~/.codex/agents/{role}.toml. Generated by support; not source truth.",
        "",
        f"name = {_toml_basic_string(role)}",
        f"description = {_toml_basic_string(description)}",
    ]
    lines.extend(casting_lines)
    lines.append(f"sandbox_mode = {_toml_basic_string(sandbox_mode)}")
    lines.append(
        f"developer_instructions = {_toml_multiline_string(developer_instructions)}"
    )
    lines.extend(
        [
            "",
            "# Enforced by Brick MCP, not by native Codex config:",
            *[f"#   - {note}" for note in _BRICK_MCP_ENFORCED_NOTES],
            "# This file projects an existing Brick/Agent decision; it grants no",
            "# authority and proves no provider behavior.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_skill_md(
    name: str,
    description: str,
    body_source: str,
) -> str:
    """Render a portable Agent-Skills standard SKILL.md (frontmatter + body).

    The Agent Skills open standard (a <name>/SKILL.md dir) is read by BOTH Codex
    and Claude, so brick disciplines/kinds project to ONE portable skill, not a
    per-host file. Frontmatter carries name (lowercase + hyphens, <= 64 chars,
    == dir name) and description (<= 1024 chars); the rest is the markdown body.
    This is read-only support projection: it writes no file and owns no meaning.
    """

    slug = str(name).strip()
    if not slug or not slug.replace("-", "").isalnum() or slug != slug.lower():
        raise AgentResourceError(
            "skill name must be lowercase letters/digits/hyphens (Agent-Skills standard)"
        )
    if len(slug) > 64:
        raise AgentResourceError("skill name must be <= 64 characters (Agent-Skills standard)")
    desc = " ".join(str(description).split())
    if not desc:
        raise AgentResourceError("skill description must be non-empty (Agent-Skills standard)")
    if len(desc) > 1024:
        raise AgentResourceError("skill description must be <= 1024 characters (Agent-Skills standard)")
    if "\n" in desc:
        raise AgentResourceError("skill description must be a single line")
    body = str(body_source).strip()
    lines = [
        "---",
        f"name: {slug}",
        f"description: {desc}",
        "---",
        "",
        body,
        "",
    ]
    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# Claude-native subagent .md projection (real per-LLM translation)
#
# A Claude SUBAGENT is a markdown file (.claude/agents/<name>.md) with YAML
# frontmatter (required name + description; optional tools allowlist /
# disallowedTools denylist / model) followed by a body that IS the subagent's
# system prompt. The KEY per-LLM difference vs Codex: Claude has a real per-agent
# tool allow/deny list, whereas Codex has only sandbox_mode -- so the SAME Brick
# tool-policy maps to a DIFFERENT native shape (a concrete tool name list here, a
# sandbox string there). These renderers emit that real native form. They write
# NO files and run NO subprocess -- they return strings only; a human (or a later
# projection-sync) places them under .claude/agents/.
# ---------------------------------------------------------------------------


def claude_tools_for_native_grant(
    native_grant_resources: Any,
    *,
    tool_policy_refs: Any | None = None,
    write_need: bool = True,
) -> dict[str, Any]:
    resolution = resolve_native_grant(
        native_grant_resources,
        tool_policy_refs=tool_policy_refs,
        write_need=write_need,
    )
    tools: list[str] = []
    for capability in _NATIVE_GRANT_CAPABILITY_ORDER:
        if capability not in resolution["capabilities"]:
            continue
        for tool_name in _CLAUDE_TOOLS_BY_NATIVE_CAPABILITY[capability]:
            if tool_name not in tools:
                tools.append(tool_name)
    disallowed = [tool_name for tool_name in _CLAUDE_CANONICAL_TOOL_UNIVERSE if tool_name not in tools]
    return {
        "tools": tools,
        "disallowedTools": disallowed,
        "write_capable": _NATIVE_GRANT_CAPABILITY_WRITE in resolution["capabilities"],
        "web_capable": _NATIVE_GRANT_CAPABILITY_WEB in resolution["capabilities"],
        "native_grant": resolution,
    }


def claude_tools_for_tool_policies(
    tool_policy_refs: Any,
    *,
    write_need: bool = True,
    native_grant_resources: Any | None = None,
) -> dict[str, Any]:
    """Map an Agent's Brick-axis tool policy refs to a Claude tool allow/deny set.

    Claude subagents carry a real per-agent ``tools`` allowlist (and an optional
    ``disallowedTools`` denylist). The write-CAPABLE allowlist that INCLUDES
    Edit + Write is granted ONLY when BOTH the Agent carries read-write-scoped
    AND the STEP's Brick declares a write NEED (``write_need`` True == a
    non-empty write_scope is present). Otherwise -- every read-only policy, OR a
    write-capable agent on a read-only Brick (no write_scope NEED) -- maps to a
    read-ONLY allowlist (Read + Grep + Glob) with Edit + Write explicitly
    denied. This mirrors effective_write = write_scope AND read-write-scoped AND
    observed-write-adapter: being write-CAPABLE never means write-EFFECTIVE
    absent the Brick NEED.

    ``write_need`` defaults True for the DESCRIPTIVE "what can this agent do"
    projection (the per-agent native subagent file, not tied to a single step);
    a run-time provider invocation FOR A STEP must pass the step's actual
    write_need so the physical tool set matches the logical effective_write gate.

    This is the Claude analog of ``codex_sandbox_mode_for_tool_policies`` -- a
    DIFFERENT shape (a list of tool names, not a sandbox string) from the SAME
    source policy. It is a support projection of an existing Brick/Agent
    decision; it grants no authority and proves no provider behavior.
    """

    return claude_tools_for_native_grant(
        native_grant_resources,
        tool_policy_refs=tool_policy_refs,
        write_need=write_need,
    )


def _claude_model_key_for_adapter_refs(adapter_refs: list[str]) -> str:
    """Project the Agent's adapter refs to a Claude subagent ``model`` value.

    adapter:local is in-process (no provider model) and adapter:claude-local
    inherits the Claude session default, so both project to "inherit". A
    codex/gemini adapter is not a native Claude model, so it ALSO projects to
    "inherit" (the renderer notes the non-native provider in the body rather than
    inventing a model id). No admitted Agent Object pins a concrete claude model
    id today, so this honestly inherits rather than fabricating one.
    """

    # MODEL_PROVIDER_BY_ADAPTER is referenced to keep the mapping honest: only a
    # claude adapter's model could ever populate this key, and none is pinned, so
    # every admitted agent inherits the Claude session default.
    if _ADAPTER_CLAUDE_LOCAL in adapter_refs and _MODEL_PROVIDER_BY_ADAPTER.get(
        _ADAPTER_CLAUDE_LOCAL
    ):
        return "inherit"
    return "inherit"


def _claude_non_native_provider_note(adapter_refs: list[str]) -> str:
    """Return a note when the agent carries a non-Claude provider adapter.

    Returns "" when no non-native provider is present. This keeps the projection
    honest: a codex/gemini adapter is a technical capability ref, not a native
    Claude model, so the model key inherits and the body explains why.
    """

    non_native = sorted(
        provider
        for ref in adapter_refs
        if (provider := _MODEL_PROVIDER_BY_ADAPTER.get(ref))
        and provider != "claude"
    )
    if not non_native:
        return ""
    providers = ", ".join(non_native)
    return (
        f"This agent also carries non-Claude provider adapter(s) ({providers}); "
        "those are technical capability refs, not native Claude models, so the "
        "model key inherits the Claude session default rather than pinning one."
    )


def _claude_description(packet: Mapping[str, Any]) -> str:
    role = str(packet["role"])
    lane = str(packet["agent_object"]["lane"])
    return (
        f"Brick Protocol {role} agent ({lane} lane). Delegate {lane}-lane work to "
        "this subagent. Provider-neutral source in brick_protocol/agent/; this .md is a "
        "read-only Claude-native projection."
    )


def _claude_yaml_quote(value: str) -> str:
    """Quote a scalar for a single-line YAML frontmatter value when needed.

    Frontmatter scalars here are short, single-line strings (name / description /
    model). We double-quote and escape backslashes + double-quotes so a value
    with a colon or '#' cannot corrupt the YAML mapping.
    """

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _claude_subagent_body(
    packet: Mapping[str, Any],
    *,
    tool_mapping: Mapping[str, Any],
    non_native_note: str,
) -> str:
    role = str(packet["role"])
    lane = str(packet["agent_object"]["lane"])
    tools = list(tool_mapping["tools"])
    disallowed = list(tool_mapping["disallowedTools"])
    sections: list[str] = [
        f"You are the Brick Protocol {role} agent ({lane} lane).",
        "",
    ]
    for resource in packet["prompt_resources"]:
        body = str(resource["body"]).strip()
        if body:
            sections.extend([f"## Prompt ({resource['ref']})", "", body, ""])
    disciplines = packet["discipline_resources"]
    if disciplines:
        sections.append("## Disciplines (summary)")
        sections.append("")
        for resource in disciplines:
            first_line = next(
                (
                    line.strip().lstrip("# ").strip()
                    for line in str(resource["body"]).splitlines()
                    if line.strip()
                ),
                resource["ref"],
            )
            sections.append(f"- {resource['ref']}: {first_line}")
        sections.append("")
    sections.extend(
        [
            "## Native scope (Claude tools)",
            "",
            (
                "tools (allowlist) = "
                + ", ".join(tools)
                + " (mapped from this agent's Brick-axis tool policy). "
                + (
                    "This agent is write-CAPABLE (Edit + Write present), but "
                    "write is EFFECTIVE only on a step whose Brick declares a "
                    "write_scope NEED; on a read-only Brick the run-time "
                    "projection drops Edit + Write."
                    if "Edit" in tools
                    else "This agent is read-only; Edit + Write are denied."
                )
            ),
            "",
        ]
    )
    if disallowed:
        sections.extend(
            [
                "disallowedTools (denylist) = " + ", ".join(disallowed) + ".",
                "",
            ]
        )
    if non_native_note:
        sections.extend([non_native_note, ""])
    sections.extend(
        [
            "## Enforced by Brick MCP, NOT by Claude",
            "",
            (
                "The following are NOT expressible in native Claude subagent "
                "config (the tools allowlist is the only native tool boundary). "
                "They are enforced by the Brick Protocol MCP / engine and remain "
                "owned by their axis:"
            ),
            "",
            *[f"- {note}" for note in _BRICK_MCP_ENFORCED_NOTES],
            "",
            (
                "Return one JSON object matching the Brick row's "
                "required_return_shape (enforced by Brick MCP, not by Claude). "
                "Do not claim source truth, and do not judge success or quality."
            ),
            "",
            (
                "This agent does NOT choose Movement / route / quality (Link + "
                "human own those)."
            ),
        ]
    )
    return "\n".join(sections).strip()


def render_claude_subagent_md(
    role_or_ref: str,
    repo_root: str | Path | None = None,
) -> str:
    """Render a real Claude-native subagent .md for an admitted Agent Object.

    Emits a markdown document with parseable YAML frontmatter (between ``---``
    fences) carrying the required Claude subagent keys name + description plus a
    ``tools`` allowlist + ``disallowedTools`` denylist that are MAPPED from the
    Agent's Brick-axis tool policy (read-write-scoped -> tools include Edit +
    Write; every read-only policy -> Read + Grep + Glob only, Edit + Write
    denied) and a ``model`` (inherit; no admitted agent pins a claude model id).
    The body is the subagent system prompt: the agent prompt + a discipline
    summary + an explicit "enforced by Brick MCP, not by Claude" honesty note
    (return shape / Link gate / evidence are not native-Claude-expressible) + a
    no-Movement guardrail.

    This is read-only support projection: it writes no file, runs no subprocess,
    calls no provider, chooses no Movement, and owns no Agent meaning.
    """

    packet = render_agent_packet(role_or_ref, repo_root=repo_root)
    role = str(packet["role"])
    adapter_refs = list(packet["agent_object"]["adapter_refs"])
    tool_policy_refs = list(packet["agent_object"]["tool_policy_refs"])
    tool_policy_resources = list(packet["tool_policy_resources"])
    tool_mapping = claude_tools_for_tool_policies(
        tool_policy_refs,
        native_grant_resources=tool_policy_resources,
    )
    # The casting LINES loop the single-source CASTING_FIELDS: the model dial
    # emits ``model: "inherit"`` today (no pinned id, byte-identical to the prior
    # _claude_model_key_for_adapter_refs default) and the effort dial emits
    # ``effort: "<level>"`` when declared. adapter_refs still feeds the non-native
    # provider note in the body.
    casting_lines = _native_casting_lines(packet["agent_object"], NATIVE_TARGET_CLAUDE)
    non_native_note = _claude_non_native_provider_note(adapter_refs)
    description = _claude_description(packet)
    body = _claude_subagent_body(
        packet, tool_mapping=tool_mapping, non_native_note=non_native_note
    )

    frontmatter = [
        "---",
        f"name: {_claude_yaml_quote(role)}",
        f"description: {_claude_yaml_quote(description)}",
        f"tools: {', '.join(tool_mapping['tools'])}",
    ]
    if tool_mapping["disallowedTools"]:
        frontmatter.append(
            f"disallowedTools: {', '.join(tool_mapping['disallowedTools'])}"
        )
    frontmatter.extend(casting_lines)
    frontmatter.append("---")

    lines = [
        "<!-- Brick Protocol Claude-native subagent projection (read-only). -->",
        f"<!-- Source of truth remains brick_protocol/agent/objects/{role}.yaml; place this at -->",
        f"<!-- .claude/agents/{role}.md. Generated by support; not source truth. -->",
        "",
        *frontmatter,
        "",
        body,
        "",
        "<!-- Enforced by Brick MCP, not by native Claude config:",
        *[f"     - {note}" for note in _BRICK_MCP_ENFORCED_NOTES],
        "     This file projects an existing Brick/Agent decision; it grants no",
        "     authority and proves no provider behavior. -->",
    ]
    return "\n".join(lines).strip() + "\n"


def _projection_seed(
    role_or_ref: str,
    *,
    projection_target: str,
    repo_root: str | Path | None = None,
    extra_fields: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = render_agent_packet(role_or_ref, repo_root=repo_root)
    role = str(packet["role"])
    base = {
        "kind": "agent-resource-projection-seed",
        "agent_object_ref": packet["agent_object"]["object_ref"],
        "role": role,
        "projection_target": projection_target,
        "source_packet": packet,
        "resource_refs": {
            "prompt_refs": list(packet["agent_object"]["prompt_refs"]),
            "skill_refs": list(packet["agent_object"]["skill_refs"]),
            "hook_refs": list(packet["agent_object"]["hook_refs"]),
            "tool_policy_refs": list(packet["agent_object"]["tool_policy_refs"]),
            "discipline_refs": list(packet["agent_object"]["discipline_refs"]),
            "adapter_refs": list(packet["agent_object"]["adapter_refs"]),
        },
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }
    return {
        **base,
        "projection_status": "rendered",
        "rendered_instruction_text": _render_instruction_text(packet, target=projection_target),
        **dict(extra_fields or {}),
    }


def render_codex_projection_seed(
    role_or_ref: str,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return a Codex-native projection seed dict without writing files.

    Carries the REAL Codex-native subagent TOML under
    ``rendered_codex_subagent_toml`` (in addition to the structured seed dict +
    the generic ``rendered_instruction_text`` other consumers/checkers rely on),
    plus the mapped ``codex_sandbox_mode``.
    """

    toml_text = render_codex_subagent_toml(role_or_ref, repo_root=repo_root)
    packet = render_agent_packet(role_or_ref, repo_root=repo_root)
    sandbox_mode = codex_sandbox_mode_for_tool_policies(
        packet["agent_object"]["tool_policy_refs"],
        native_grant_resources=packet["tool_policy_resources"],
    )
    return _projection_seed(
        role_or_ref,
        projection_target="codex-native-skill-seed",
        repo_root=repo_root,
        extra_fields={
            "rendered_codex_subagent_toml": toml_text,
            "codex_sandbox_mode": sandbox_mode,
        },
    )


def render_claude_projection_seed(
    role_or_ref: str,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Return a Claude-native projection seed dict without writing files.

    Carries the REAL Claude-native subagent .md under
    ``rendered_claude_subagent_md`` (in addition to the structured seed dict +
    the generic ``rendered_instruction_text`` other consumers/checkers rely on),
    plus the mapped ``claude_tools`` allow/deny set. Does NOT carry the codex
    toml key (that stays in the codex seed only) -- the two host seeds do not
    cross-leak each other's native projection.
    """

    md_text = render_claude_subagent_md(role_or_ref, repo_root=repo_root)
    packet = render_agent_packet(role_or_ref, repo_root=repo_root)
    claude_tools = claude_tools_for_tool_policies(
        packet["agent_object"]["tool_policy_refs"],
        native_grant_resources=packet["tool_policy_resources"],
    )
    return _projection_seed(
        role_or_ref,
        projection_target="claude-native-instruction-seed",
        repo_root=repo_root,
        extra_fields={
            "rendered_claude_subagent_md": md_text,
            "claude_tools": claude_tools,
        },
    )


__all__ = [
    "AgentResourceError",
    "list_agent_object_refs",
    "resolve_agent_object",
    "validate_agent_refs",
    "render_agent_packet",
    "render_agent_instruction_packet",
    "render_agent_team_context",
    "render_codex_projection_seed",
    "render_claude_projection_seed",
    "render_codex_subagent_toml",
    "render_claude_subagent_md",
    "render_skill_md",
    "resolve_native_grant",
    "resolve_agent_semantic_capability",
    "codex_sandbox_mode_for_native_grant",
    "codex_sandbox_mode_for_tool_policies",
    "claude_tools_for_native_grant",
    "claude_tools_for_tool_policies",
]

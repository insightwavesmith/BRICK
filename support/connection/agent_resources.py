"""Agent resource resolver and renderer for AGENT-RESOURCE-TOOLKIT-0.

This support surface reads Agent-axis resource files and returns
JSON-compatible packets. It does not write provider-native files, call
providers, execute hooks/tools, choose Movement, or own Agent meaning.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.agent.performance import NATIVE_DISPATCH_PERFORMANCE_MODE
from .agent_adapter import (
    ADAPTER_CODEX_LOCAL as _ADAPTER_CODEX_LOCAL,
    ADAPTER_CLAUDE_LOCAL as _ADAPTER_CLAUDE_LOCAL,
    ALLOWED_ADAPTER_REFS as _ALLOWED_ADAPTER_REFS,
    MODEL_PROVIDER_BY_ADAPTER as _MODEL_PROVIDER_BY_ADAPTER,
    _OBSERVED_WRITE_ADAPTER_REFS,
    adapter_is_write_capable,
)


_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
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
_TOOL_POLICY_READ_WRITE_SCOPED = "tool-policy:read-write-scoped"
_TOOL_POLICY_REVIEWER_READONLY = "tool-policy:reviewer-readonly"
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
# Claude DOES have a real per-agent tool allow/deny list in a subagent .md
# (`tools` allowlist + optional `disallowedTools` denylist). Unlike Codex (which
# has only sandbox_mode), the SAME Brick-axis tool-policy must project to a
# DIFFERENT native shape here: a concrete list of Claude tool names. We MAP the
# single read-write-scoped policy (worker or leader lane) to a write-CAPABLE tool
# set (Read + Grep + Glob + Edit + Write); every read-only policy (reviewer /
# support, or a leader without read-write-scoped) maps to a read-ONLY tool set
# (Read + Grep + Glob, NO Edit/Write).
# This is a support projection of an existing Brick/Agent decision, not a new
# authority -- Claude still cannot enforce the return shape, the Link gate, or
# the evidence spine (see the honesty note the renderer stamps into the body).
_CLAUDE_TOOLS_READ_ONLY = ("Read", "Grep", "Glob")
_CLAUDE_TOOLS_WRITE_EXTRA = ("Edit", "Write")
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
    "Agent resource meaning remains owned by agent/",
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
_AGENT_OBJECT_KEYS = frozenset(
    {
        "object_ref",
        "name",
        "lane",
        "callable_performer_refs",
        "prompt_refs",
        "skill_refs",
        "hook_refs",
        "tool_policy_refs",
        "discipline_refs",
        "adapter_refs",
        "preferred_adapter_ref",
    }
)
_REF_FIELDS = (
    "prompt_refs",
    "skill_refs",
    "hook_refs",
    "tool_policy_refs",
    "discipline_refs",
    "adapter_refs",
)
_FORBIDDEN_AGENT_OBJECT_KEYS = frozenset(
    {
        "provider_connector_refs",
        "provider_request_body",
        "credential_body",
        "setup_token",
        "setup_token_value",
        "session_id",
        "provider_session_id",
        "agent_fact_shape",
        "agentfact_shape",
        "success",
        "failure",
        "quality",
        "movement_choice",
        "choose_movement",
        "default_gatefact",
        "default_gate_fact",
    }
)


class AgentResourceError(ValueError):
    """Raised when an Agent resource reference cannot be resolved safely."""


def _repo_root(repo_root: str | Path | None) -> Path:
    return Path(repo_root).resolve() if repo_root is not None else _DEFAULT_REPO_ROOT


def _agent_objects_dir(repo: Path) -> Path:
    return repo / "agent" / "objects"


def list_agent_object_refs(repo_root: str | Path | None = None) -> list[str]:
    """List admitted Agent Object refs from agent/objects/*.yaml."""

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
        raise AgentResourceError("role_or_ref must reference an admitted agent/objects/*.yaml resource")
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


def _load_agent_object(role: str, repo: Path) -> dict[str, Any]:
    path = repo / "agent" / "objects" / f"{role}.yaml"
    agent_object = _require_mapping(str(path), _read_data(path))
    unknown = sorted(set(agent_object) - _AGENT_OBJECT_KEYS)
    if unknown:
        raise AgentResourceError(f"{path}: unknown Agent Object keys: {', '.join(unknown)}")
    forbidden = sorted(set(agent_object) & _FORBIDDEN_AGENT_OBJECT_KEYS)
    if forbidden:
        raise AgentResourceError(f"{path}: forbidden Agent Object keys: {', '.join(forbidden)}")
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
    preferred_adapter_ref = agent_object.get("preferred_adapter_ref")
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
    if preferred_adapter_ref is not None:
        if not isinstance(preferred_adapter_ref, str) or not preferred_adapter_ref.strip():
            raise AgentResourceError(f"{path}: preferred_adapter_ref must be non-empty text")
        preferred_adapter_ref = preferred_adapter_ref.strip()
        if preferred_adapter_ref not in adapter_refs:
            raise AgentResourceError(
                f"{path}: preferred_adapter_ref must be one of adapter_refs: "
                f"{preferred_adapter_ref}"
            )
    write_capable_adapter_refs = sorted(
        adapter_ref
        for adapter_ref in adapter_refs
        if adapter_is_write_capable(adapter_ref)
    )
    if _HOOK_INSTRUCTION_CHAIN_READ not in hook_refs:
        raise AgentResourceError(f"{path}: Agent Object must carry hook:instruction-chain-read")
    if _HOOK_RESOURCE_REF_REDACTION not in hook_refs:
        raise AgentResourceError(f"{path}: Agent Object must carry hook:resource-ref-redaction")
    if _TOOL_POLICY_READ_WRITE_SCOPED in tool_policy_refs and lane not in (
        "worker",
        "leader",
        "reviewer",
    ):
        raise AgentResourceError(
            f"{path}: read-write scoped tool policy is admitted only for worker, leader, or reviewer lane"
        )
    if (
        _TOOL_POLICY_READ_WRITE_SCOPED in tool_policy_refs
        and not adapter_refs.intersection(_OBSERVED_WRITE_ADAPTER_REFS)
    ):
        raise AgentResourceError(
            f"{path}: missing_adapter_write_capability: read-write scoped policy "
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
        # discipline; read-write-scoped is the work-area write CAPABILITY.
        if _HOOK_REVIEWER_NO_MUTATION not in hook_refs:
            raise AgentResourceError(f"{path}: reviewer lane must carry hook:reviewer-no-mutation")
        # A reviewer MAY carry tool-policy:read-write-scoped (write-capable
        # QA-attack); effective write stays gated by a Brick-declared write_scope
        # NEED plus an observed-write adapter, exactly like the leader MAY-carry.
        # A reviewer WITHOUT read-write-scoped must still carry the read-only
        # reviewer policy (byte-identical to today's reviewer surface).
        if (
            _TOOL_POLICY_READ_WRITE_SCOPED not in tool_policy_refs
            and _TOOL_POLICY_REVIEWER_READONLY not in tool_policy_refs
        ):
            raise AgentResourceError(f"{path}: reviewer lane must carry tool-policy:reviewer-readonly")


def _resource_path(repo: Path, ref: str) -> Path:
    if ref.startswith("prompt:"):
        return repo / "agent" / "prompts" / f"{_ref_slug(ref, 'prompt:')}.md"
    if ref.startswith("skill:"):
        return repo / "agent" / "skills" / _ref_slug(ref, "skill:") / "SKILL.md"
    if ref.startswith("tool-policy:"):
        return repo / "agent" / "tool_policies" / f"{_ref_slug(ref, 'tool-policy:')}.yaml"
    if ref.startswith("discipline:"):
        return repo / "agent" / "disciplines" / f"{_ref_slug(ref, 'discipline:')}.md"
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


def _data_resources(repo: Path, refs: list[str], *, kind: str) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for ref in refs:
        path = _resource_path(repo, ref)
        resources.append(
            {
                "ref": ref,
                "kind": kind,
                "path": path.relative_to(repo).as_posix(),
                "data": _read_data(path),
            }
        )
    return resources


def _hook_resources(repo: Path, refs: list[str], object_ref: str) -> dict[str, Any]:
    registry_path = repo / "agent" / "hooks" / "registry.yaml"
    bindings_path = repo / "agent" / "hooks" / "bindings.yaml"
    registry = _require_mapping(str(registry_path), _read_data(registry_path))
    bindings = _require_mapping(str(bindings_path), _read_data(bindings_path))
    hook_registry = _require_mapping("agent/hooks/registry.yaml:hooks", registry.get("hooks"))
    hook_bindings = _require_mapping("agent/hooks/bindings.yaml:bindings", bindings.get("bindings"))
    bound_refs = hook_bindings.get(object_ref)
    if not isinstance(bound_refs, list) or not all(isinstance(item, str) for item in bound_refs):
        raise AgentResourceError(f"agent/hooks/bindings.yaml: missing hook binding for {object_ref}")
    if list(bound_refs) != refs:
        raise AgentResourceError(f"agent/hooks/bindings.yaml: binding mismatch for {object_ref}")
    selected: list[dict[str, Any]] = []
    for ref in refs:
        definition = _require_mapping(f"agent/hooks/registry.yaml:{ref}", hook_registry.get(ref))
        if definition.get("execution_opened") is not False:
            raise AgentResourceError(f"agent/hooks/registry.yaml:{ref}: native hook execution remains closed")
        selected.append({"ref": ref, "definition": definition})
    return {
        "registry_path": "agent/hooks/registry.yaml",
        "bindings_path": "agent/hooks/bindings.yaml",
        "selected": selected,
    }


def _resource_refs(agent_object: Mapping[str, Any]) -> dict[str, list[str]]:
    return {field: list(agent_object.get(field, [])) for field in _REF_FIELDS}


def resolve_agent_object(role_or_ref: str, repo_root: str | Path | None = None) -> dict[str, Any]:
    """Resolve one Agent Object and its referenced Agent resources."""

    repo = _repo_root(repo_root)
    role = _normalize_role(role_or_ref, repo)
    agent_object = _load_agent_object(role, repo)
    object_ref = str(agent_object["object_ref"])
    prompt_refs = list(agent_object["prompt_refs"])
    skill_refs = list(agent_object["skill_refs"])
    tool_policy_refs = list(agent_object["tool_policy_refs"])
    discipline_refs = list(agent_object["discipline_refs"])
    hook_refs = list(agent_object["hook_refs"])
    return {
        "kind": "agent-resource-resolution",
        "role": role,
        "agent_object": agent_object,
        "resource_refs": _resource_refs(agent_object),
        "prompt_resources": _text_resources(repo, prompt_refs, kind="prompt"),
        "skill_resources": _text_resources(repo, skill_refs, kind="skill"),
        "hook_resources": _hook_resources(repo, hook_refs, object_ref),
        "tool_policy_resources": _data_resources(repo, tool_policy_refs, kind="tool_policy"),
        "discipline_resources": _text_resources(repo, discipline_refs, kind="discipline"),
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
        "source": "agent/",
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


def render_agent_packet(role_or_ref: str, repo_root: str | Path | None = None) -> dict[str, Any]:
    """Render a JSON-compatible support packet from Agent-axis resources."""

    resolution = resolve_agent_object(role_or_ref, repo_root=repo_root)
    return {
        "kind": "agent-resource-packet",
        "role": resolution["role"],
        "agent_object": resolution["agent_object"],
        "prompt_resources": resolution["prompt_resources"],
        "skill_resources": resolution["skill_resources"],
        "hook_resources": resolution["hook_resources"],
        "tool_policy_resources": resolution["tool_policy_resources"],
        "discipline_resources": resolution["discipline_resources"],
        "adapter_refs": resolution["adapter_refs"],
        "proof_limits": list(_PROOF_LIMITS),
        "not_proven": list(_NOT_PROVEN),
    }


def render_agent_instruction_packet(
    role_or_ref: str,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Render runtime Agent instructions from Agent resources, not projection seed text."""

    packet = render_agent_packet(role_or_ref, repo_root=repo_root)
    agent_object = _require_mapping("agent_resource_packet.agent_object", packet["agent_object"])
    return {
        "kind": "agent-instruction-packet",
        "agent_object_ref": str(agent_object["object_ref"]),
        "role": str(packet["role"]),
        "prompt_resources": list(packet["prompt_resources"]),
        "skill_resources": list(packet["skill_resources"]),
        "hook_resources": packet["hook_resources"],
        "tool_policy_resources": list(packet["tool_policy_resources"]),
        "discipline_resources": list(packet["discipline_resources"]),
        "adapter_refs": list(packet["adapter_refs"]),
        "proof_limits": [
            "runtime AgentInstructionPacket support input only",
            "not a projection seed",
            *list(packet["proof_limits"]),
        ],
        "not_proven": list(packet["not_proven"]),
    }


def _render_instruction_text(packet: Mapping[str, Any], *, target: str) -> str:
    role = str(packet["role"])
    object_ref = str(packet["agent_object"]["object_ref"])
    lines = [
        f"# Brick Protocol {role.upper()} Projection Seed",
        "",
        f"projection_target: {target}",
        f"agent_object_ref: {object_ref}",
        "",
        "This is a projection seed only. The source remains agent/.",
        "",
    ]
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


def codex_sandbox_mode_for_tool_policies(
    tool_policy_refs: Any, *, write_need: bool = True
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

    refs = set(_string_list("tool_policy_refs", tool_policy_refs))
    if _TOOL_POLICY_READ_WRITE_SCOPED in refs and bool(write_need):
        return _CODEX_SANDBOX_WORKSPACE_WRITE
    return _CODEX_SANDBOX_READ_ONLY


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
        "agent/; this TOML is a read-only Codex-native projection."
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
    adapter_refs = list(packet["agent_object"]["adapter_refs"])
    tool_policy_refs = list(packet["agent_object"]["tool_policy_refs"])
    sandbox_mode = codex_sandbox_mode_for_tool_policies(tool_policy_refs)
    model_value = _codex_model_key_for_adapter_refs(adapter_refs)
    description = _codex_description(packet)
    developer_instructions = _codex_developer_instructions(
        packet, sandbox_mode=sandbox_mode
    )

    lines = [
        "# Brick Protocol Codex-native subagent projection (read-only).",
        "# Source of truth remains agent/objects/" + f"{role}.yaml; place this at",
        f"# ~/.codex/agents/{role}.toml. Generated by support; not source truth.",
        "",
        f"name = {_toml_basic_string(role)}",
        f"description = {_toml_basic_string(description)}",
    ]
    if model_value:
        lines.append(f"model = {_toml_basic_string(model_value)}")
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


def claude_tools_for_tool_policies(
    tool_policy_refs: Any, *, write_need: bool = True
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

    refs = set(_string_list("tool_policy_refs", tool_policy_refs))
    if _TOOL_POLICY_READ_WRITE_SCOPED in refs and bool(write_need):
        return {
            "tools": [*_CLAUDE_TOOLS_READ_ONLY, *_CLAUDE_TOOLS_WRITE_EXTRA],
            "disallowedTools": [],
            "write_capable": True,
        }
    return {
        "tools": list(_CLAUDE_TOOLS_READ_ONLY),
        "disallowedTools": list(_CLAUDE_TOOLS_WRITE_EXTRA),
        "write_capable": False,
    }


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
        "this subagent. Provider-neutral source in agent/; this .md is a "
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
    tool_mapping = claude_tools_for_tool_policies(tool_policy_refs)
    model_value = _claude_model_key_for_adapter_refs(adapter_refs)
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
    frontmatter.append(f"model: {_claude_yaml_quote(model_value)}")
    frontmatter.append("---")

    lines = [
        "<!-- Brick Protocol Claude-native subagent projection (read-only). -->",
        f"<!-- Source of truth remains agent/objects/{role}.yaml; place this at -->",
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
    sandbox_mode = codex_sandbox_mode_for_tool_policies(
        render_agent_packet(role_or_ref, repo_root=repo_root)["agent_object"][
            "tool_policy_refs"
        ]
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
    claude_tools = claude_tools_for_tool_policies(
        render_agent_packet(role_or_ref, repo_root=repo_root)["agent_object"][
            "tool_policy_refs"
        ]
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
    "codex_sandbox_mode_for_tool_policies",
    "claude_tools_for_tool_policies",
]

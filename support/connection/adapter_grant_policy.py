"""Native-grant resolution + gemini admin-policy + work-envelope prompt build.

Extracted VERBATIM from ``support/connection/agent_adapter.py`` (E2 split,
extraction 5/7). PURE relocation -- no logic/name/signature change. This module
owns:

* Native-grant resolution (``_native_grant_resolution_for_request`` and the
  capability/web projection helpers built on it).
* Gemini admin-policy TOML projection (``_gemini_*`` partition/policy helpers +
  ``_toml_tool_rule``).
* Work-envelope prompt build (``_build_prompt`` +
  ``_instruction_packet_for_prompt``).
* Structured-return extraction (``_extract_required_return_fields``,
  ``_merge_structured_return_fields``, ``_structured_return_payload``,
  ``_clean_return_field_value``, ``_strip_code_fence``).

The ``agent_adapter`` facade re-exports every symbol here (public AND
underscore-private) so late-bound ``agent_adapter.<sym>`` access never breaks.

This module imports siblings DIRECTLY (adapter_constants) and NEVER
``from support.connection.agent_adapter import ...`` at top level (cycle). The
stay-behind carriers, constants, and helper functions that still live in
``agent_adapter`` (``_CANONICAL_TOOL_UNIVERSE_GEMINI``,
``_GEMINI_TOOLS_BY_NATIVE_CAPABILITY``, ``_RETURN_JSON_FIELDS``,
``_RETURN_LIST_FIELDS``, ``_TOP_LEVEL_VERDICT_KEYS``, ``adapter_has_capability``,
``agent_request_effective_write``, ``agent_request_read_tier``,
``_required_return_shape_fields``, ``_return_field_waivers``,
``_allowed_return_fields``, ``_read_tier_policy_refs_for_request``,
``_source_fact_bodies_for_prompt``, ``_transition_concern_schema_rules``,
``_merge_texts``, ``_try_json_value``) are reached LAZILY in-function (the
``from .agent_adapter import ...`` back-edge runs only at call time, after both
modules are fully loaded) so there is no import cycle and the moved bodies keep
their exact statements. ``_node_casting_fields_ordered`` is imported directly
from its real owner sibling ``adapter_model_casting``. The lazy in-function
``from .agent_resources import resolve_native_grant`` import is kept lazy exactly
as the prior code had it. ``AgentAdapterRequest`` / ``LocalCliSpec`` are
annotation-only here (``from __future__ import annotations`` keeps them strings).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, TYPE_CHECKING

from .adapter_constants import (
    ADAPTER_CAPABILITY_READ,
    ADAPTER_CAPABILITY_WEB,
    ADAPTER_CAPABILITY_WRITE,
    ADAPTER_CODEX_LOCAL,
    ADAPTER_GEMINI_LOCAL,
)

if TYPE_CHECKING:
    from .agent_adapter import AgentAdapterRequest, LocalCliSpec

_HOOK_REVIEWER_NO_MUTATION = "hook:reviewer-no-mutation"


def _request_blocks_source_mutation(request: AgentAdapterRequest) -> bool:
    return _HOOK_REVIEWER_NO_MUTATION in set(request.hook_refs)


def _request_allows_source_mutation(request: AgentAdapterRequest) -> bool:
    from .agent_adapter import agent_request_effective_write

    return agent_request_effective_write(request) and not _request_blocks_source_mutation(request)


def _native_grant_resolution_for_request(
    request: AgentAdapterRequest,
    *,
    write_need: bool | None = None,
) -> Mapping[str, Any]:
    if not request.tool_policy_refs:
        return {
            "schema": "native-grant-resolution/v1",
            "tool_policy_refs": [],
            "declared_capabilities": [],
            "capabilities": [],
            "write_effective": False,
            "web_requested": False,
            "missing_tool_policy_refs": [],
            "proof_limits": [
                "native_grant resolution uses already-loaded tool-policy data only",
                "request without selected tool_policy_refs fails closed",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
        }
    resources = request.agent_instruction_packet.get("tool_policy_resources")
    if resources is None:
        resources = []
    from .agent_resources import resolve_native_grant
    resolved_write_need = bool(request.write_scope) if write_need is None else bool(write_need)

    return resolve_native_grant(
        resources,
        tool_policy_refs=list(request.tool_policy_refs),
        write_need=resolved_write_need,
    )


def _native_capabilities_for_request(request: AgentAdapterRequest) -> frozenset[str]:
    resolution = _native_grant_resolution_for_request(request)
    capabilities = resolution.get("capabilities", ())
    if not isinstance(capabilities, list):
        return frozenset()
    return frozenset(str(capability) for capability in capabilities)


def _native_web_requested_for_request(request: AgentAdapterRequest) -> bool:
    resolution = _native_grant_resolution_for_request(request)
    return bool(resolution.get("web_requested"))


def _adapter_projects_web_for_request(request: AgentAdapterRequest) -> bool:
    from .agent_adapter import adapter_has_capability

    return (
        ADAPTER_CAPABILITY_WEB in _native_capabilities_for_request(request)
        and adapter_has_capability(request.adapter_ref, ADAPTER_CAPABILITY_WEB)
    )


def _gemini_allowed_tool_names_for_request(request: AgentAdapterRequest) -> frozenset[str]:
    from .agent_adapter import _GEMINI_TOOLS_BY_NATIVE_CAPABILITY

    capabilities = _native_capabilities_for_request(request)
    allowed: set[str] = set()
    for capability in (ADAPTER_CAPABILITY_READ, ADAPTER_CAPABILITY_WEB, ADAPTER_CAPABILITY_WRITE):
        if capability in capabilities:
            allowed.update(_GEMINI_TOOLS_BY_NATIVE_CAPABILITY.get(capability, frozenset()))
    return frozenset(allowed)


def _gemini_admin_policy_partition_for_request(
    request: AgentAdapterRequest,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    from .agent_adapter import _CANONICAL_TOOL_UNIVERSE_GEMINI

    allowed_set = _gemini_allowed_tool_names_for_request(request)
    universe_set = set(_CANONICAL_TOOL_UNIVERSE_GEMINI)
    unknown_allowed = sorted(allowed_set - universe_set)
    if unknown_allowed:
        raise ValueError(
            "gemini native grant projected tools outside canonical universe: "
            + ", ".join(unknown_allowed)
        )
    allowed = tuple(tool for tool in _CANONICAL_TOOL_UNIVERSE_GEMINI if tool in allowed_set)
    denied = tuple(tool for tool in _CANONICAL_TOOL_UNIVERSE_GEMINI if tool not in allowed_set)
    if set(allowed).intersection(denied) or set(allowed).union(denied) != universe_set:
        raise ValueError("gemini native grant tool partition is not exhaustive")
    return allowed, denied


def _toml_tool_rule(tool_names: tuple[str, ...], *, decision: str, priority: int) -> str:
    lines = [
        "[[rule]]",
        "toolName = [",
        *[f'  "{tool_name}",' for tool_name in tool_names],
        "]",
        f'decision = "{decision}"',
        f"priority = {priority}",
    ]
    return "\n".join(lines)


def _gemini_admin_policy_for_request(request: AgentAdapterRequest) -> str:
    allowed, denied = _gemini_admin_policy_partition_for_request(request)
    blocks: list[str] = []
    if allowed:
        blocks.append(_toml_tool_rule(allowed, decision="allow", priority=998))
    if denied:
        blocks.append(_toml_tool_rule(denied, decision="deny", priority=999))
    return "\n\n".join(blocks) + "\n"


def _build_prompt(request: AgentAdapterRequest, spec: LocalCliSpec) -> str:
    from .adapter_model_casting import _node_casting_fields_ordered
    from .agent_adapter import (
        _TOP_LEVEL_VERDICT_KEYS,
        _read_tier_policy_refs_for_request,
        _required_return_shape_fields,
        _return_field_waivers,
        _source_fact_bodies_for_prompt,
        _transition_concern_schema_rules,
        agent_request_effective_write,
        agent_request_read_tier,
    )

    required_labels = _required_return_shape_fields(request.required_return_shape)
    waiver_labels = _return_field_waivers(required_labels)
    reserved_top_level_return_keys = ", ".join(sorted(_TOP_LEVEL_VERDICT_KEYS))
    native_grant = _native_grant_resolution_for_request(request)
    web_requested = bool(native_grant.get("web_requested"))
    web_projected = _adapter_projects_web_for_request(request)
    rules = [
        "Do not claim source truth.",
        "Do not judge success or quality.",
        "Do not choose Link Movement.",
        "Do not run git commit or git push.",
        "Do not access or print setup tokens, auth bodies, credentials, or raw provider sessions.",
        "Return concise text only.",
        "Return one JSON object. The object may include only required_return_shape fields and listed return_field_waivers.",
        "Do not use these reserved keys at the top level of the returned JSON object: "
        + reserved_top_level_return_keys
        + ".",
        "If evidence is missing, put it under blocked_or_missing_evidence or not_proven inside that JSON object; do not invent fields.",
    ]
    if "transition_concern_evidence" in required_labels:
        rules.extend(_transition_concern_schema_rules())
    if agent_request_effective_write(request):
        if _request_blocks_source_mutation(request):
            rules.extend(
                (
                    "Agent hook:reviewer-no-mutation blocks source_write for this performer.",
                    "Capability taxonomy: read = repo/evidence/diff/raw/step-output inspection; probe_write / verification_write = disposable W1, temp, cache, test fixture, checker output, negative probe, or generated probe output writes; source_write = real repo source mutation.",
                    "You may use the Brick-declared write_scope only for probe_write / verification_write in the disposable work-area.",
                    "Do not create, edit, delete, or rewrite source files as source truth; return proposed source patches or repair deltas as evidence for a separately declared work / repair Brick.",
                    "Prompt/provider controls distinguish source_write from probe_write by instruction and post-hoc evidence only; a full filesystem-enforced source/probe split is not proven here.",
                    "Do not execute hooks or provider SDKs.",
                    "Return non-judgmental support evidence only.",
                )
            )
        else:
            rules.extend(
                (
                    "You may edit files only inside the Brick-declared write_scope.allowed_paths.",
                    "Do not edit files matching write_scope.forbidden_paths.",
                    "Do not execute hooks or provider SDKs.",
                    "Return non-judgmental support evidence only.",
                )
            )
    elif agent_request_read_tier(request) or web_projected or (
        web_requested and spec.adapter_ref == ADAPTER_CODEX_LOCAL
    ):
        admitted = ", ".join(sorted(_read_tier_policy_refs_for_request(request)))
        if agent_request_read_tier(request):
            rules.extend(
                (
                    "You may use read-only repository inspection tools only: read files, inspect diffs, search with grep/glob, and run checker commands.",
                    f"Read tier is admitted for this adapter only by these Agent tool policies: {admitted}.",
                )
            )
        elif web_requested and spec.adapter_ref == ADAPTER_CODEX_LOCAL:
            rules.append(
                "No adapter-native web tools are available on codex-local for this native_grant."
            )
        else:
            rules.append(
                "You may use only adapter-native web tools granted by native_grant; do not inspect repository files."
            )
        rules.extend(
            (
                "Do not edit, create, delete, or write files.",
                "Do not run git mutations, including commit, push, checkout, reset, merge, rebase, or stash.",
                "Do not execute hooks or provider SDKs.",
                "Return non-judgmental support evidence only.",
            )
        )
        if web_projected:
            rules.append(
                "Web access is adapter-projected from tool-policy:web-capable; use only the adapter-native web tools granted by native_grant."
            )
        elif web_requested and spec.adapter_ref == ADAPTER_CODEX_LOCAL:
            rules.append("Web NOT available on this adapter; do not use network beyond the selected provider itself.")
        else:
            rules.append("Do not use network beyond the selected provider itself.")
    else:
        rules.append("Do not use tools or hooks.")
    if spec.adapter_ref == ADAPTER_GEMINI_LOCAL:
        if _request_allows_source_mutation(request):
            rules.append(
                "Gemini local effective_write may use write_file, replace, and run_shell_command only inside the Brick-declared write_scope; read and web tools remain governed by native_grant."
            )
        elif agent_request_effective_write(request) and _request_blocks_source_mutation(request):
            rules.append(
                "Gemini local effective probe_write / verification_write may use write_file, replace, and run_shell_command only inside the Brick-declared write_scope; source_write remains blocked by hook:reviewer-no-mutation."
            )
        elif agent_request_read_tier(request) or web_projected:
            rules.append(
                "Gemini local native grant may use only read_file, glob, grep_search, search_file_content, list_directory, read_many_files, and when web-capable is present google_web_search/web_fetch; write and shell tools remain blocked."
            )
        rules.extend(
            (
                "Do not call exit_plan_mode or any plan-finalization tool.",
                "Do not write output_packet_ref; it is an evidence label, not a file path.",
                "Return the requested evidence in the CLI response text only.",
            )
        )
    prompt = {
        "task": "Return provider-neutral Brick Protocol support evidence only.",
        "rules": rules,
        "building_id": request.building_id,
        "agent_object_ref": request.agent_object_ref,
        "adapter_ref": spec.adapter_ref,
        # E2/S6★: serialize the casting dials by LOOPING the single-source
        # NODE_CASTING_FIELDS instead of naming the model dial. Each declared
        # (truthy) ``selected_<base>`` value joins the bag; an undeclared dial is
        # absent, so today this emits exactly ``selected_model_ref`` (byte-identical
        # to the prior single key) and a NEW dial (effort) rides along when declared.
        **{
            _ck: getattr(request, _ck)
            for _ck in _node_casting_fields_ordered()
            if getattr(request, _ck)
        },
        "prompt_refs": list(request.prompt_refs),
        "skill_refs": list(request.skill_refs),
        "hook_refs": list(request.hook_refs),
        "tool_policy_refs": list(request.tool_policy_refs),
        "discipline_refs": list(request.discipline_refs),
        "input_packet_ref": request.input_packet_ref,
        "output_packet_ref": request.output_packet_ref,
        "work_statement": request.work_statement,
        "comparison_rule": request.comparison_rule,
        "required_return_shape": request.required_return_shape,
        "required_return_labels": list(required_labels),
        "return_field_waivers": list(waiver_labels),
        "source_fact_bodies": _source_fact_bodies_for_prompt(request, spec),
        "link_handoff_refs": dict(request.link_handoff_refs),
        "agent_instruction_packet": _instruction_packet_for_prompt(request, spec),
        "native_grant": dict(native_grant),
        "write_scope": dict(request.write_scope),
        "building_session_ref": request.building_session_ref,
        "session_scope_ref": request.session_scope_ref,
        "session_continuity_mode": request.session_continuity_mode,
    }
    # ⑤ STATIC KIND INSTRUCTION (the brick.md ## body): delivered as its OWN labeled
    # prompt section, DISTINCT from the dynamic work_statement (fault attribution —
    # static-kind-how-to vs this-building's task). Added ONLY when the brick_row
    # carries a body, so a legacy / no-template row adds NO key and the prompt stays
    # byte-identical to the pre-⑤ output (the design's "two empty-string keys" risk
    # is avoided by present-only injection).
    if request.brick_instruction_body:
        prompt["brick_instruction_body"] = request.brick_instruction_body
    # ④ RE-INSTRUCTION / CORRECTION (Link disposition): the corrected how-to a
    # human/COO HOLD disposition carried to THIS retried target. Delivered as its
    # OWN labeled prompt section, DISTINCT from work_statement (this building's
    # task) and from brick_instruction_body (the static kind how-to) -- fault
    # attribution: a redo prompt names WHY it differs from the original attempt.
    # Added ONLY on the disposition's redo-target step (present-only injection),
    # so every normal step and every non-target step stays byte-identical.
    if request.re_instruction:
        prompt["re_instruction"] = request.re_instruction
    return json.dumps(prompt, ensure_ascii=True, sort_keys=True)


def _instruction_packet_for_prompt(
    request: AgentAdapterRequest,
    spec: LocalCliSpec,
) -> Mapping[str, Any]:
    from .agent_adapter import _required_return_shape_fields

    if not request.agent_instruction_packet:
        return {}
    packet = dict(request.agent_instruction_packet)
    required_labels = _required_return_shape_fields(request.required_return_shape)
    if request.required_return_shape and "required_return_shape" not in packet:
        packet["required_return_shape"] = request.required_return_shape
    if required_labels and "required_return_labels" not in packet:
        packet["required_return_labels"] = list(required_labels)
    if spec.opaque_resource_paths_on_wire:
        packet = _sakana_instruction_packet_for_prompt(packet)
    return packet


def _sakana_instruction_packet_for_prompt(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Remove repo path labels from the Sakana wire copy only.

    The request's original AgentInstructionPacket remains intact for local
    evidence. Sakana sees opaque refs plus inline bodies, avoiding path-shaped
    labels in the provider prompt without changing non-Sakana packet bytes.
    """

    cleaned = dict(packet)
    for key in (
        "prompt_resources",
        "skill_resources",
        "discipline_resources",
        "charter_resources",
        "skill_manifest_refs",
        "tool_policy_resources",
    ):
        rows = cleaned.get(key)
        if isinstance(rows, list):
            cleaned[key] = [_without_path_label(row) for row in rows]
    hooks = cleaned.get("hook_resources")
    if isinstance(hooks, Mapping):
        cleaned["hook_resources"] = _without_hook_path_labels(hooks)
    return cleaned


def _without_path_label(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    cleaned = dict(value)
    cleaned.pop("path", None)
    return cleaned


def _without_hook_path_labels(value: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = dict(value)
    cleaned.pop("registry_path", None)
    cleaned.pop("bindings_path", None)
    return cleaned


def _extract_required_return_fields(
    output_text: str,
    required_return_shape: Any,
) -> Mapping[str, Any]:
    """Lift strictly structured Agent return fields from local CLI text.

    This is a mechanical adapter normalization step. It only accepts a JSON
    object returned by the Agent and only copies keys requested by
    Brick.required_return_shape. It never infers Movement, target, success,
    failure, approval, or quality fields from unstructured prose.
    """

    # Every declared, forbidden-filtered field (U2-3 richer kind shapes). The
    # earlier `if field in _RETURN_LABEL_FIELDS` clause dropped fields the kind's
    # required_return_shape declares but the label set never enumerated (e.g.
    # work: received_work_ref / changed_files / commands_run / handoff_refs), so a
    # model that DID return them lost them from AgentFact.returned and the gate
    # reported them missing. This is safe: forbidden keys are stripped upstream
    # (_required_return_shape_fields) AND re-checked downstream
    # (_validate_returned_payload); an unknown declared field passes through
    # _clean_return_field_value's else-branch verbatim; the JSON-shape guard
    # (_structured_return_payload) is unchanged.
    from .agent_adapter import _allowed_return_fields

    fields = _allowed_return_fields(required_return_shape)
    if not fields:
        return {}
    payload = _structured_return_payload(output_text)
    if payload is None:
        return {}
    extracted: dict[str, Any] = {}
    for field in fields:
        if field not in payload:
            continue
        extracted[field] = _clean_return_field_value(field, payload[field])
    return extracted


def _merge_structured_return_fields(
    returned: dict[str, Any],
    extracted: Mapping[str, Any],
) -> None:
    from .agent_adapter import _merge_texts

    for key, value in extracted.items():
        if key in {"evidence_refs", "not_proven", "proof_limits"} and key in returned:
            if isinstance(value, Mapping):
                value = _mapping_to_text_list(value)
            returned[key] = list(_merge_texts(returned[key], value))
            continue
        if key not in returned:
            returned[key] = value


def _structured_return_payload(output_text: str) -> Mapping[str, Any] | None:
    from .agent_adapter import _try_json_value

    text = output_text.strip()
    parsed = _try_json_value(_strip_code_fence(text))
    if isinstance(parsed, Mapping):
        return parsed
    for match in re.finditer(r"(?s)```(?:json)?\s*(.*?)```", output_text):
        parsed = _try_json_value(match.group(1).strip())
        if isinstance(parsed, Mapping):
            return parsed
    return None


def _clean_return_field_value(field: str, value: Any) -> Any:
    from .agent_adapter import _RETURN_JSON_FIELDS, _RETURN_LIST_FIELDS

    if field in _RETURN_JSON_FIELDS:
        return value
    if field in _RETURN_LIST_FIELDS:
        if isinstance(value, list):
            return _list_items_to_text(value)
        if isinstance(value, Mapping):
            return _mapping_to_text_list(value)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return value
    return value


def _mapping_to_text_list(value: Mapping[str, Any]) -> list[str]:
    """Flatten a mapping-shaped list field to deterministic text values."""

    return _list_items_to_text(value.values())


def _list_items_to_text(values: Any) -> list[str]:
    normalized: list[str] = []
    for item in values:
        text = _return_list_item_to_text(item)
        if text:
            normalized.append(text)
    return normalized


def _return_list_item_to_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if value is None:
        return ""
    return str(value).strip()


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return text

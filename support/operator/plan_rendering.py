"""The BUILDER surface (P3d concern module; the "rendering" name is historical).

This module is not a pure renderer: it is where a declared intent becomes a
materialized plan. It loads the split brick catalog (bricks/<kind>/brick.md
frontmatter -- reached via the legacy-named ``step_template_ref`` key) and the
preset registry (presets/<name>.md frontmatter), serves the shape menu, runs
NEED<->CAPABILITY agent matching (lane + writer tool policy), translates
preset gate labels into declared link-gate:* refs, and expands compact link
expressions into declared rows. It reads declared movement literals via the
canonical link.movement MOVEMENT_LITERALS contract and authors no Movement,
target, or route; it judges no success or quality."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from brick_protocol.link.movement import MOVEMENT_LITERALS
from brick_protocol.agent.spec import (
    CASTING_FIELDS,
    NODE_CASTING_FIELDS,
    CastingField,
    selected_key,
)

from brick_protocol.support.operator.building_operation_common import (
    COMPACT_LINK_GATE_TOKENS,
    DEFAULT_LINK_GATE_REF,
    _clean_text,
    _mapping_value,
    _text_sequence,
)
from brick_protocol.support.connection.agent_resources import (
    list_agent_object_refs,
    resolve_agent_object,
    _TOOL_POLICY_READ_WRITE_SCOPED,
    _TOOL_POLICY_PROBE_WRITE_SCOPED,
)
from brick_protocol.support.operator.provider_registry import (
    first_ready_registered_adapter,
    load_provider_registry,
    model_ref_for_adapter,
    provider_ladder_enabled,
    registry_static_preference_ready,
)


# The writer capability: an Agent Object whose tool_policy_refs carry a
# write-capable tool policy is admitted to perform write/probe work.
# This is now a CAPABILITY any lane may carry (leaders and reviewers carry it too).
# Carrying it never grants EFFECTIVE write by itself -- effective
# write additionally requires the step's Brick to declare a write_scope NEED.
# This rule is OWNED by agent_resources.py.
WRITER_TOOL_POLICY_REFS = {
    _TOOL_POLICY_READ_WRITE_SCOPED,
    _TOOL_POLICY_PROBE_WRITE_SCOPED,
}


SPLIT_SHAPE_CATALOG_PATH = Path("brick/templates/shapes/catalog.yaml")
BRICKS_SPEC_DIR = Path("brick/templates/bricks")
# Unified node/edge model (U3 re-home): a chain preset is now a "Building route
# 설명서" authored as a free-form .md (frontmatter = the preset's structure keys
# verbatim + a `## Route` body the engine does NOT parse). Like bricks/<kind>/brick.md,
# the Builder SOURCES the chain preset rows from frontmatter via
# _chain_presets_from_presets. canonical vs dogfood is split by catalog_scope.
PRESETS_SPEC_DIR = Path("brick/templates/presets")
PRESET_DOGFOOD_SCOPE = "brick_protocol_dogfood"
# Unified model (U4): the per-kind node spec is authored entirely in
# bricks/<kind>/brick.md frontmatter. The two narration fields the declared-plan path
# still reads (brick_word -- the underscore compact-match form, e.g.
# code_attack_qa; performer_word -- the compact performer key) are now carried
# IN that frontmatter alongside identity, agent_object_hint_ref,
# link_movement_literal, brick_contract, and required_return_template_refs, so
# step-templates.yaml is retired (no bridge). The former
# agent_contract / link_contract prose reached no declared-plan output and was
# dropped with the file.


CALLER_OR_COO_DECLARATION_MARKERS = frozenset({"caller", "coo"})
_RETIRED_WRITE_ADAPTER_REFS = frozenset(
    {
        "adapter:codex-write-local",
        "adapter:claude-write-local",
    }
)
_LOCAL_ADAPTER_REF = "adapter:local"
_VERDICT_LANE_NEEDS = frozenset({"reviewer", "leader"})


# KIND REVERT (0611, Smith ruling): brick kind cto-assignment -> development
# (the 0610 rename put a ROLE in the kind name -- an axis smell; "development"
# is the CTO assignment planning step, the coding step is `work`). The
# short-lived cto-assignment name (live on origin/main for about a day) REJECTS
# loudly naming the canonical replacement -- it never silently resolves and
# never falls through to the generic not-in-catalog error.
RETIRED_STEP_TEMPLATE_REFS = {
    "building-step-template:cto-assignment": "building-step-template:development",
}


def render_declared_building_plan(intent: Mapping[str, Any]) -> Mapping[str, Any]:
    """Render a candidate Building Plan from fully declared intent.

    This helper does not infer Building shape, choose Movement, choose targets,
    inline Agent resources, call providers, or write files. The caller must
    declare every Brick row, Agent Object ref, Link Movement, and Link target.
    """

    if not isinstance(intent, Mapping):
        raise TypeError("intent must be an object")
    plan_ref = _clean_text("plan_ref", intent.get("plan_ref", ""))
    building_id = _clean_text("building_id", intent.get("building_id", ""))
    selected_adapter_ref = _clean_selected_adapter_ref(
        "selected_adapter_ref",
        # DEFAULT-PARITY with compose_building (graph path defaults adapter:local);
        # the linear path previously defaulted to "" which plan_validation rejects,
        # so omitting the adapter RED'd only in this path. Now both default the same.
        intent.get("selected_adapter_ref", "adapter:local"),
    )
    selected_model_ref = _clean_text(
        "selected_model_ref",
        intent.get("selected_model_ref", "model:default"),
    )
    proof_limits = _text_sequence("proof_limits", intent.get("proof_limits"))
    not_proven = _text_sequence("not_proven", intent.get("not_proven"))
    raw_steps = intent.get("steps")
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)) or not raw_steps:
        raise ValueError("intent.steps must be a non-empty array")

    steps: list[Mapping[str, Any]] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise TypeError(f"intent.steps[{index}] must be an object")
        steps.append(_render_declared_step(index, raw_step))

    rendered_plan: dict[str, Any] = {
        "plan_ref": plan_ref,
        "owner_axis": "Brick",
        "building_id": building_id,
        "selected_adapter_ref": selected_adapter_ref,
        "selected_model_ref": selected_model_ref,
        "proof_limits": list(proof_limits),
        "not_proven": list(not_proven),
        "steps": steps,
    }
    if intent.get("task_source_ref"):
        rendered_plan["task_source_ref"] = _clean_text("task_source_ref", intent["task_source_ref"])
    raw_task_statement = intent.get("task_statement")
    if raw_task_statement is not None:
        # TASK-BY-TEXT (0611, codex FIX-A): the inline statement is carried
        # VERBATIM (no _clean_text strip -- the materializer normalized it to a
        # single trailing newline and the recorded task_source_hash covers those
        # exact bytes; stripping here would silently break hash re-derivation).
        # Coupling with the sentinel task_source_ref is enforced fail-closed by
        # plan_validation._task_source_ref_from_plan at projection validation.
        if not isinstance(raw_task_statement, str) or not raw_task_statement.strip():
            raise ValueError("task_statement must be non-empty text")
        rendered_plan["task_statement"] = raw_task_statement
    plan_shape = intent.get("plan_shape")
    if plan_shape is not None:
        rendered_plan["plan_shape"] = _clean_text("plan_shape", plan_shape)
    return rendered_plan


def _declared_step_from_step_template(
    index: int,
    raw_step: Mapping[str, Any],
    step_templates: Mapping[str, Mapping[str, Any]],
    repo: Path,
    *,
    plan_casting: Mapping[str, str] | None = None,
) -> Mapping[str, Any]:
    step_ref = _clean_text(f"steps[{index}].step_ref", raw_step.get("step_ref", ""))
    step_template = _lookup_declared_step_template(index, raw_step, step_templates)
    brick = _mapping_value(f"steps[{index}].brick", raw_step.get("brick"))
    raw_link = raw_step.get("link", {})
    compact_link = ""
    if isinstance(raw_link, str):
        compact_link = _clean_text(f"steps[{index}].link", raw_link)
        link: dict[str, Any] = {}
    else:
        link = dict(_mapping_value(f"steps[{index}].link", raw_link))
    raw_target_ref = raw_step.get("target_ref") or link.get("target_ref")
    target_ref = (
        _clean_text(f"steps[{index}].target_ref", raw_target_ref)
        if raw_target_ref is not None
        else ""
    )
    declared_gate_refs: tuple[str, ...] = ()
    if compact_link:
        parsed_link = _parse_compact_link_expression(index, compact_link)
        compact_target = _compact_target_ref(parsed_link["target"])
        if target_ref and target_ref != compact_target:
            raise ValueError("compact link target must match target_ref when both are supplied")
        target_ref = compact_target
        declared_gate_refs = tuple(parsed_link["declared_gate_refs"])
    if any(token in target_ref for token in (" or ", " and ", ",", "|")):
        raise ValueError("Link target must be one declared target")
    movement = _clean_text(f"steps[{index}].step_template.link_word", step_template["link_word"])
    if movement not in MOVEMENT_LITERALS:
        raise ValueError("step template link_word must be forward or reroute")
    if compact_link and movement != "forward":
        raise ValueError("compact link expressions expand only to forward Link rows")
    if any(token in movement for token in (" or ", " and ", ",", "|", "/")):
        raise ValueError("step template link_word must be one declared Movement word")
    if "movement" in link and _clean_text(f"steps[{index}].link.movement", link["movement"]) != movement:
        raise ValueError("caller-supplied link movement must match the declared step template link_word")
    if "movement_literal" in link:
        raise ValueError("step template expansion accepts only the step template link_word as Movement")
    if "target" in link or "target_boundary_ref" in link:
        raise ValueError("step template expansion accepts exactly one target_ref")
    if declared_gate_refs and "declared_gate_refs" in link:
        raise ValueError("compact link expression already declares gate refs")
    if step_template["step_template_ref"] == "building-step-template:development":
        if step_template["agent_object_ref"] != "agent-object:cto-lead":
            raise ValueError("development / cto / forward must resolve to agent-object:cto-lead")
        if "write_scope" in brick:
            raise ValueError("development / cto / forward is CTO assignment only; write_scope belongs to later dev worker Brick")
    # branch (U2-4): author agent override (mirrors the graph path's
    # _resolve_agent_for_need in composition.compose_building). Default = the
    # template's NEED<->CAPABILITY match. A node MAY override it with a step-level
    # agent_object_ref, but only with an agent that itself satisfies this kind's
    # NEED (role_need/write_need carried on the registry row); an override that
    # violates the NEED raises (the linear path is fail-closed). No override = the
    # matched default. The development guard above pins the template to cto-lead,
    # but role_need=leader has 5 candidates, so a same-NEED override would let
    # _resolve_agent_for_need substitute another leader and divert the CTO-only
    # assignment -- block the override for the development template before
    # resolving (codex U2-4 P2).
    agent_object_ref = step_template["agent_object_ref"]
    declared_override = raw_step.get("agent_object_ref")
    if declared_override and declared_override != agent_object_ref:
        if step_template["step_template_ref"] == "building-step-template:development":
            raise ValueError("development / cto / forward is CTO-only; agent override not allowed")
        agent_object_ref = _resolve_agent_for_need(
            repo,
            step_template["role_need"],
            bool(step_template["write_need"]),
            declared_override=declared_override,
                        )

    # Building-wide plan casting defaults (adapter:local / model:default parity with
    # the prior named-param defaults) when the caller supplies no bag.
    resolved_plan_casting = dict(plan_casting or {})
    resolved_plan_casting.setdefault("selected_adapter_ref", "adapter:local")
    resolved_plan_casting.setdefault("selected_model_ref", "model:default")
    casting_selection = _resolve_casting_selection(
        repo,
        raw_step=raw_step,
        agent_object_ref=agent_object_ref,
        plan_casting=resolved_plan_casting,
        label=f"steps[{index}]",
        is_verdict_bearing_node=_is_verdict_bearing_node(
            raw_step,
            step_template=step_template,
        ),
    )

    link["movement"] = movement
    link["target_ref"] = target_ref
    if declared_gate_refs:
        link["declared_gate_refs"] = list(declared_gate_refs)
    link.setdefault("row_ref", f"{step_ref}:link")
    # ⑤ STATIC INSTRUCTION BODY (linear path): carry the kind's brick.md ## body
    # (from the step_template registry row) onto the declared brick_row so the
    # linear path delivers the body to the agent prompt exactly like the graph
    # path (composition_compose._composition_brick_row). A node author value, if
    # ever present, wins; else the kind's body. Built on a fresh dict so the
    # caller's input mapping is not mutated. Empty body -> key omitted (no
    # delivery), parallel to the graph path.
    template_instruction_body = step_template.get("brick_instruction_body")
    author_instruction_body = brick.get("brick_instruction_body")
    author_has_body = isinstance(author_instruction_body, str) and author_instruction_body.strip()
    declared_brick: Mapping[str, Any] = brick
    if template_instruction_body and not author_has_body:
        declared_brick = {**brick, "brick_instruction_body": str(template_instruction_body)}
    template_capability_class = step_template.get("capability_class")
    author_capability_class = brick.get("capability_class")
    author_has_capability_class = (
        isinstance(author_capability_class, str) and author_capability_class.strip()
    )
    if template_capability_class and not author_has_capability_class:
        declared_brick = {**declared_brick, "capability_class": str(template_capability_class)}
    return {
        "step_ref": step_ref,
        "step_template_ref": step_template["step_template_ref"],
        # Every casting dial's selected_<base> value (E2/S6★ generic output): the
        # full NODE_CASTING_FIELDS set, so the effort dial rides along with
        # adapter+model -- not just the two hand-named keys.
        **casting_selection,
        "brick": declared_brick,
        "agent": {
            "row_ref": raw_step.get("agent_row_ref", f"{step_ref}:agent"),
            "agent_object_ref": agent_object_ref,
        },
        "link": link,
    }


def _parse_compact_link_expression(index: int, value: str) -> Mapping[str, Any]:
    if not value:
        raise ValueError(f"steps[{index}].link must be non-empty")
    if value.count("->") > 1:
        raise ValueError("compact link expression must contain at most one ->")
    if "->" in value:
        gate_text, target_text = [part.strip() for part in value.split("->", 1)]
        if not gate_text or not target_text:
            raise ValueError("compact link expression must declare gates and target around ->")
        gate_tokens = [part.strip() for part in gate_text.split("+") if part.strip()]
    else:
        target_text = value.strip()
        gate_tokens = []
    if not target_text:
        raise ValueError("compact link expression target must be non-empty")
    declared_gate_refs = [DEFAULT_LINK_GATE_REF]
    for token in gate_tokens:
        gate_ref = COMPACT_LINK_GATE_TOKENS.get(token)
        if gate_ref is None:
            raise ValueError(f"compact link expression uses unknown gate token: {token}")
        if gate_ref not in declared_gate_refs:
            declared_gate_refs.append(gate_ref)
    return {
        "target": target_text,
        "declared_gate_refs": declared_gate_refs,
    }


def _compact_target_ref(value: str) -> str:
    target = value.strip()
    if any(token in target for token in (" or ", " and ", ",", "|", "/")):
        raise ValueError("compact link target must be one target")
    if target.startswith(("brick-", "building-boundary:")):
        return target
    if ":" in target:
        raise ValueError("compact link target must be a Brick word or brick-* ref")
    return f"brick-{target}"


def _clean_selected_adapter_ref(label: str, value: str) -> str:
    selected = _clean_text(label, value)
    if selected in _RETIRED_WRITE_ADAPTER_REFS:
        raise ValueError(f"{selected} is retired and not admitted as an active adapter")
    return selected


_STEP_ADAPTER_SOURCE_BUILDING_DEFAULT = "building-default"
_STEP_ADAPTER_SOURCE_STEP_DECLARATION = "step-declaration"
_STEP_ADAPTER_SOURCE_LANE_PREFERENCE = "lane-preference"
_STEP_ADAPTER_SOURCE_PROVIDER_REGISTRY_FALLBACK = "provider-registry-fallback"
_STEP_ADAPTER_SOURCE_VERDICT_FLOOR = "verdict-non-local-floor"


def _resolve_casting_selection(
    repo: Path,
    *,
    raw_step: Mapping[str, Any],
    agent_object_ref: str,
    plan_casting: Mapping[str, str],
    label: str,
    is_verdict_bearing_node: bool = False,
) -> dict[str, str | None]:
    """Resolve EVERY casting dial and project the full ``selected_<base>`` map.

    E2/S6★: the resolver is now generic on BOTH input and output. The INPUT loop
    drives the per-dial ladder from ``CASTING_FIELDS`` descriptor DATA; the OUTPUT
    is the matching ``{selected_<base>: value}`` map — one entry per casting dial,
    not just adapter+model — so a NEW casting dial is carried onto the node with
    NO new code here (the effort dial's ``selected_reasoning_effort_ref`` is now
    produced the same way ``selected_adapter_ref``/``selected_model_ref`` are).

    The per-dial resolution and constitutional asymmetry are unchanged: the
    fail-closed adapter dial resolves first (explicit-or-fail) and records its
    SOURCE; the deferrable dials (model, effort) couple to that source via
    ``inherits_source_of`` and resolve to their descriptor default when omitted.
    The single ``building-default`` -> ``None`` projection rule (defer to the
    plan-level value rather than re-stamp it on the step) is applied generically
    to whichever dial resolved from the building-level fallback.
    """

    # Plan-level default per casting dial, DERIVED generically from the single-source
    # CASTING_FIELDS (E2/S6★) over the building-wide ``plan_casting`` bag keyed by the
    # node-layer ``selected_<base>`` names. Only the adapter + model dials carry a
    # building-wide plan arg today; any other (deferrable) dial — effort — has no plan
    # default, so ``plan_casting.get(...)`` returns None and that dial resolves to its
    # descriptor default (defer). A NEW dial never KeyErrors here.
    plan_default_by_field = {
        descriptor.field_name: plan_casting.get(selected_key(descriptor))
        for descriptor in CASTING_FIELDS
    }
    # Per-field resolved (value, source); a deferrable dial reads the adapter dial's
    # source + resolved Agent Object via its ``inherits_source_of`` coupling.
    resolved: dict[str, tuple[str | None, str | None]] = {}
    agent_object: Mapping[str, Any] | None = None
    selection: dict[str, str | None] = {}
    for descriptor in CASTING_FIELDS:
        value, source, agent_object = _resolve_casting_field(
            descriptor,
            repo,
            raw_step=raw_step,
            agent_object=agent_object,
            agent_object_ref=agent_object_ref,
            plan_default=plan_default_by_field.get(descriptor.field_name),
            resolved=resolved,
            label=label,
            is_verdict_bearing_node=is_verdict_bearing_node,
        )
        resolved[descriptor.field_name] = (value, source)
        # building-default -> None (defer to the plan-level value, do not re-stamp
        # it on the step) applied generically over every dial.
        rendered = (
            value if source != _STEP_ADAPTER_SOURCE_BUILDING_DEFAULT else None
        )
        selection[selected_key(descriptor)] = rendered
    return selection


def _resolve_casting_field(
    descriptor: CastingField,
    repo: Path,
    *,
    raw_step: Mapping[str, Any],
    agent_object: Mapping[str, Any] | None,
    agent_object_ref: str,
    plan_default: str,
    resolved: Mapping[str, tuple[str | None, str | None]],
    label: str,
    is_verdict_bearing_node: bool,
) -> tuple[str | None, str | None, Mapping[str, Any] | None]:
    """Resolve ONE casting dial from its descriptor POLICY.

    The single generic resolver behind both ladders (E2/S6 mirror M5). The
    asymmetry is descriptor DATA:

      * ``fail_closed`` True (adapter) -> the explicit-or-fail ladder: explicit
        step ``selected_<rest>`` > Agent Object ``preferred_<field>`` lane
        preference > (verdict-bearing) non-local floor > building-level default
        (CLEANED, never absent — support does NOT default the adapter away). The
        resolved value is validated against the Agent Object and a verdict-bearing
        node rejects a local adapter. Returns (value, source, agent_object) so the
        model dial can couple to the chosen adapter source.
      * ``fail_closed`` False (model) -> the deferrable ladder: explicit step
        ``selected_<rest>`` > Agent Object ``preferred_<field>`` ONLY when the
        ``inherits_source_of`` dial (the adapter) came from the lane preference >
        the ``default_ref`` sentinel when that dial is non-default > else clean the
        plan default and DEFER (None). Returns (value, None, agent_object).

    Byte-identical to the prior ``_step_selected_adapter_ref`` /
    ``_step_selected_model_ref`` ladders.
    """

    selected_key = "selected_" + descriptor.field_name.removeprefix("preferred_")
    raw_step_value = raw_step.get(selected_key)

    if descriptor.fail_closed:
        # ADAPTER dial: explicit-or-fail ladder.
        if raw_step_value is not None:
            selected = _clean_selected_adapter_ref(
                f"{label}.{selected_key}",
                raw_step_value,
            )
            source = _STEP_ADAPTER_SOURCE_STEP_DECLARATION
        else:
            agent_object = _agent_object_for_selection(repo, agent_object_ref, label=label)
            preferred = agent_object.get(descriptor.field_name)
            if preferred is not None:
                preferred_adapter = _clean_selected_adapter_ref(
                    f"{agent_object_ref}.{descriptor.field_name}",
                    preferred,
                )
                registry = load_provider_registry()
                adapter_refs = agent_object.get("adapter_refs")
                allowed_refs: set[str] = set()
                if isinstance(adapter_refs, Sequence) and not isinstance(
                    adapter_refs, (str, bytes)
                ):
                    allowed_refs = {str(item).strip() for item in adapter_refs}
                if (
                    registry is not None
                    and provider_ladder_enabled(registry)
                    and not registry_static_preference_ready(registry, preferred_adapter)
                ):
                    fallback = first_ready_registered_adapter(
                        registry,
                        allowed_adapter_refs=allowed_refs,
                    )
                    if fallback:
                        selected = fallback
                        source = _STEP_ADAPTER_SOURCE_PROVIDER_REGISTRY_FALLBACK
                    else:
                        selected = preferred_adapter
                        source = _STEP_ADAPTER_SOURCE_LANE_PREFERENCE
                else:
                    selected = preferred_adapter
                    source = _STEP_ADAPTER_SOURCE_LANE_PREFERENCE
            elif is_verdict_bearing_node:
                selected = _verdict_non_local_floor(
                    agent_object,
                    agent_object_ref=agent_object_ref,
                    label=label,
                )
                source = _STEP_ADAPTER_SOURCE_VERDICT_FLOOR
            else:
                selected = _clean_selected_adapter_ref(
                    selected_key,
                    plan_default,
                )
                source = _STEP_ADAPTER_SOURCE_BUILDING_DEFAULT
        if is_verdict_bearing_node and selected == _LOCAL_ADAPTER_REF:
            raise ValueError(f"{label}: verdict-bearing node needs a non-local adapter")
        _validate_step_adapter_ref(repo, agent_object_ref, selected, label=label)
        return selected, source, agent_object

    # MODEL dial (deferrable, coupled to the adapter via inherits_source_of).
    if raw_step_value is not None:
        return _clean_text(f"{label}.{selected_key}", raw_step_value), None, agent_object
    inherited = resolved.get(descriptor.inherits_source_of or "")
    inherited_source = inherited[1] if inherited is not None else None
    if inherited_source == _STEP_ADAPTER_SOURCE_LANE_PREFERENCE and isinstance(agent_object, Mapping):
        preferred = agent_object.get(descriptor.field_name)
        if preferred is not None:
            return _clean_text(f"{agent_object_ref}.{descriptor.field_name}", preferred), None, agent_object
    if inherited_source == _STEP_ADAPTER_SOURCE_PROVIDER_REGISTRY_FALLBACK:
        inherited_value = inherited[0] if inherited is not None else None
        if inherited_value:
            return model_ref_for_adapter(load_provider_registry(), inherited_value), None, agent_object
    if inherited_source != _STEP_ADAPTER_SOURCE_BUILDING_DEFAULT:
        return descriptor.default_ref, None, agent_object
    _clean_text(selected_key, plan_default)
    return None, None, agent_object


def _verdict_non_local_floor(
    agent_object: Mapping[str, Any],
    *,
    agent_object_ref: str,
    label: str,
) -> str:
    adapter_refs = agent_object.get("adapter_refs")
    if not isinstance(adapter_refs, Sequence) or isinstance(adapter_refs, (str, bytes)):
        raise ValueError(f"{label}: Agent Object adapter_refs must be an array")
    for adapter_ref in adapter_refs:
        selected = _clean_selected_adapter_ref(
            f"{agent_object_ref}.adapter_refs",
            str(adapter_ref).strip(),
        )
        if selected != _LOCAL_ADAPTER_REF:
            return selected
    raise ValueError(f"{label}: verdict-bearing node has no admitted non-local adapter")


def _is_verdict_bearing_node(
    node: Mapping[str, Any],
    *,
    step_template: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> bool:
    step_template_ref = str(node.get("step_template_ref") or "").strip()
    if not step_template_ref and isinstance(step_template, Mapping):
        step_template_ref = str(step_template.get("step_template_ref") or "").strip()
    if step_template_ref.rsplit(":", 1)[-1] == "closure":
        return True
    if step_template is None and registry is not None:
        step_templates = registry.get("step_templates", {})
        if isinstance(step_templates, Mapping):
            candidate = step_templates.get(step_template_ref)
            if isinstance(candidate, Mapping):
                step_template = candidate
    if not isinstance(step_template, Mapping):
        return False
    lane_need = str(
        step_template.get("performer_lane_need") or step_template.get("role_need") or ""
    ).strip().lower()
    return lane_need in _VERDICT_LANE_NEEDS


def _agent_object_for_selection(
    repo: Path,
    agent_object_ref: str,
    *,
    label: str,
) -> Mapping[str, Any]:
    try:
        resolution = resolve_agent_object(agent_object_ref, repo_root=repo)
    except ValueError as exc:
        raise ValueError(f"{label}: agent_object_ref is not admitted: {agent_object_ref}") from exc
    agent_object = resolution.get("agent_object")
    if not isinstance(agent_object, Mapping):
        raise ValueError(f"{label}: Agent Object resolution returned no object")
    return agent_object


def _validate_step_adapter_ref(
    repo: Path,
    agent_object_ref: str,
    selected_adapter_ref: str,
    *,
    label: str,
) -> None:
    agent_object = _agent_object_for_selection(repo, agent_object_ref, label=label)
    adapter_refs = agent_object.get("adapter_refs")
    if not isinstance(adapter_refs, Sequence) or isinstance(adapter_refs, (str, bytes)):
        raise ValueError(f"{label}: Agent Object adapter_refs must be an array")
    if selected_adapter_ref not in {str(item).strip() for item in adapter_refs}:
        raise ValueError(
            f"{label}.selected_adapter_ref {selected_adapter_ref} must be referenced "
            f"by Agent Object {agent_object_ref}"
        )


def _lookup_declared_step_template(
    index: int,
    raw_step: Mapping[str, Any],
    step_templates: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    step_template_ref = raw_step.get("step_template_ref")
    if step_template_ref is not None:
        key = _clean_text(f"steps[{index}].step_template_ref", step_template_ref)
        if key in RETIRED_STEP_TEMPLATE_REFS:
            raise ValueError(
                f"steps[{index}].step_template_ref {key} is retired: "
                f"use {RETIRED_STEP_TEMPLATE_REFS[key]}"
            )
        if key not in step_templates:
            raise ValueError(f"steps[{index}].step_template_ref is not in Brick template catalog step_templates")
        step_template = step_templates[key]
    else:
        brick_word = _clean_text(f"steps[{index}].brick_word", raw_step.get("brick_word", ""))
        agent_word = _clean_text(f"steps[{index}].agent_word", raw_step.get("agent_word", ""))
        default_link_word = "forward" if isinstance(raw_step.get("link"), str) else ""
        link_word = _clean_text(
            f"steps[{index}].link_word",
            raw_step.get("link_word", default_link_word),
        )
        matches = [
            item
            for item in step_templates.values()
            if item.get("brick_word") == brick_word
            and item.get("agent_word") == agent_word
            and item.get("link_word") == link_word
        ]
        if len(matches) != 1:
            raise ValueError(f"steps[{index}] must declare one registered step template row")
        step_template = matches[0]
    for field in ("brick_word", "agent_word", "link_word"):
        supplied = raw_step.get(field)
        if supplied is not None and _clean_text(f"steps[{index}].{field}", supplied) != step_template[field]:
            raise ValueError(f"steps[{index}].{field} must match the registered step template")
    supplied_spec = raw_step.get("brick_spec_ref")
    if supplied_spec is not None:
        declared_spec = _clean_text(f"steps[{index}].brick_spec_ref", supplied_spec)
        if declared_spec != step_template.get("brick_spec_ref"):
            raise ValueError(
                f"steps[{index}].brick_spec_ref must match the registered single-Brick spec"
            )
    return step_template


def _load_shape_registry(repo: Path) -> Mapping[str, Any]:
    split_catalog_path = repo / SPLIT_SHAPE_CATALOG_PATH
    if split_catalog_path.is_file():
        return _load_split_shape_catalog(repo, split_catalog_path)
    raise ValueError("split Brick template catalog is missing")


def _load_split_shape_catalog(repo: Path, catalog_path: Path) -> Mapping[str, Any]:
    catalog = _load_yaml_mapping(catalog_path, "split catalog")
    catalog_ref = _required_yaml_text(catalog, "catalog_ref", "split catalog")
    files = _required_yaml_mapping(catalog, "files", "split catalog")

    # U5/U5.1 follow-through (0610): selected_shape_ref is an OPTIONAL recorded
    # tag, so the shapes MENU file is no longer load-bearing. Absent menu --
    # the catalog does not declare files.shapes, or the declared file is not on
    # disk -- means an EMPTY shape menu (shape_refs == ()), no error. When the
    # file IS present the previous behavior is unchanged (parse + extract
    # shape_refs; a malformed present file still fails closed).
    shape_refs: tuple[str, ...] = ()
    if files.get("shapes") is not None:
        shapes_path = _split_catalog_file_path(
            repo,
            _required_yaml_text(files, "shapes", "split catalog files"),
        )
        if shapes_path.is_file():
            shapes_doc = _load_yaml_mapping(shapes_path, "split catalog shapes")
            shape_refs = tuple(
                _required_yaml_text(shape, "shape_ref", "split catalog shapes")
                for shape in _yaml_mapping_rows(
                    shapes_doc.get("shapes"),
                    "split catalog shapes.shapes",
                )
            )
    # The Builder SOURCES the step template rows from the per-kind node specs in
    # bricks/<kind>/brick.md (U4 retired step-templates.yaml; the catalog no longer
    # declares or reads a step_templates file).
    step_templates = _step_templates_from_bricks(repo)
    # The catalog index still DECLARES the chain_presets / dogfood_chain_presets
    # source under files (keep the catalog contract honest), but the Builder now
    # SOURCES the chain preset rows from presets/<name>.md frontmatter via
    # _chain_presets_from_presets (mirroring how step templates are sourced from
    # bricks/<kind>/brick.md). canonical vs dogfood is split by catalog_scope inside the
    # presets; the legacy compat_preset_refs alias grammar is retired (rejected loudly).
    common_files = files.get("chain_presets", {})
    if not isinstance(common_files, Mapping):
        raise ValueError("split catalog files.chain_presets must be a mapping")
    dogfood_files = files.get("dogfood_chain_presets", {})
    if dogfood_files is not None and not isinstance(dogfood_files, Mapping):
        raise ValueError("split catalog files.dogfood_chain_presets must be a mapping")
    for _name, relative in {**common_files, **(dogfood_files or {})}.items():
        if not isinstance(relative, str) or not relative.strip():
            raise ValueError("split catalog chain preset source refs must be non-empty text")
        # Validate the declared source path stays inside the repo and resolves
        # (it now points at the presets/ source directory, not a per-preset file).
        if not _split_catalog_file_path(repo, relative.strip()).exists():
            raise ValueError(f"split catalog chain preset source is missing: {relative.strip()}")
    presets = _chain_presets_from_presets(repo)
    chain_presets = presets["chain_presets"]
    common_chain_presets = presets["common_chain_presets"]
    dogfood_chain_presets = presets["dogfood_chain_presets"]
    chain_preset_aliases = presets["chain_preset_aliases"]

    # shape_refs intentionally NOT required here: the shape menu is an optional
    # tag source (U5/U5.1), absent menu => empty tuple above.
    if not step_templates or not chain_presets:
        raise ValueError("split catalog must declare step_templates and chain_presets")
    return {
        "registry_ref": catalog_ref,
        "shape_refs": shape_refs,
        "step_templates": step_templates,
        "chain_presets": chain_presets,
        "common_chain_presets": common_chain_presets,
        "dogfood_chain_presets": dogfood_chain_presets,
        "chain_preset_aliases": chain_preset_aliases,
    }


def _store_step_template(
    step_templates: dict[str, dict[str, Any]],
    step_template: Mapping[str, Any],
    *,
    source: str = "step_templates",
) -> None:
    required = (
        "step_template_ref",
        "brick_word",
        "agent_word",
        "agent_object_ref",
        "link_word",
        "brick_contract",
    )
    missing = [field for field in required if not step_template.get(field)]
    if missing:
        raise ValueError(f"{source} entry is missing field(s): " + ", ".join(missing))
    stored: dict[str, Any] = {field: str(step_template[field]) for field in required}
    if "brick_template_refs" in step_template:
        stored["brick_template_refs"] = _yaml_text_tuple(
            step_template["brick_template_refs"],
            f"{source}.brick_template_refs",
        )
    if "brick_spec_ref" in step_template:
        stored["brick_spec_ref"] = str(step_template["brick_spec_ref"])
    # The brick NEED (role_need + write_need) is carried verbatim when present so
    # the override guard can re-match a node-declared agent against the same NEED.
    # These are not part of the declared-plan output (golden compares only the 4
    # output-affecting fields) -- they are selection metadata on the registry row.
    if "role_need" in step_template:
        stored["role_need"] = str(step_template["role_need"])
    if "write_need" in step_template:
        stored["write_need"] = bool(step_template["write_need"])
    # Non-authoritative Brick capability taxonomy. This is carried beside the
    # hard write NEED so generated rows can show read / probe_write /
    # source_write / artifact_write without using that label as authority.
    if "capability_class" in step_template:
        stored["capability_class"] = str(step_template["capability_class"])
    # The kind's real declared return shape (comma-joined field list from the
    # primary return_template) is carried so composition_compose.py can default a node's
    # required_return_shape to it when the node omits one. Like role_need/
    # write_need this is selection metadata, NOT part of the declared-plan output.
    if "required_return_shape" in step_template:
        stored["required_return_shape"] = str(step_template["required_return_shape"])
    # ⑤ STATIC INSTRUCTION BODY: the brick.md ## body (the markdown after the
    # frontmatter fence) is the agent-readable kind instruction. It is read ONCE
    # here at compose time (the only place brick.md is parsed) and carried onto the
    # registry row so composition_compose.py can stamp it onto the brick_row; the request
    # builder then threads it to the prompt (adapter_grant_policy._build_prompt key
    # ``brick_instruction_body``). Like required_return_shape it is selection
    # metadata, NOT part of the declared-plan output (golden compares only the 4
    # output-affecting fields). Without this carry the body is unreachable at run
    # time (the runtime brick_row / BrickWork carry no kind or brick_spec_ref).
    if "brick_instruction_body" in step_template:
        stored["brick_instruction_body"] = str(step_template["brick_instruction_body"])
    # CARRIES-FORWARD SET: the kind's HANDOFF subset (comma-joined field list from
    # the primary return_template's optional carries_forward_fields). Carried onto
    # the registry row -- like required_return_shape, selection metadata, NOT part
    # of the declared-plan output -- so composition_compose.py can stamp it onto the
    # brick_row and the walker carry seam can FILTER an upstream summary to it.
    # Stored only when NON-EMPTY: a kind with no declared carry-set leaves the key
    # absent and the seam falls back to the full-summary carry (backward-safe).
    # (_store_step_template is a key WHITELIST -- without this clause the row key
    # would be silently dropped here, exactly the declared-but-not-wired trap.)
    carries_forward = str(step_template.get("carries_forward_fields", "")).strip()
    if carries_forward:
        stored["carries_forward_fields"] = carries_forward
    step_templates[str(step_template["step_template_ref"])] = stored


def _brick_spec_frontmatter(text: str, label: str) -> Mapping[str, Any]:
    """Parse the YAML frontmatter mapping between the leading --- fences of a brick spec."""
    if not text.startswith("---"):
        raise ValueError(f"{label} must open with --- frontmatter")
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        raise ValueError(f"{label} frontmatter must be closed with ---")
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ValueError(f"{label} requires PyYAML") from exc
    block = parts[0][len("---"):]
    data = yaml.safe_load(block)
    if not isinstance(data, Mapping):
        raise ValueError(f"{label} frontmatter must parse to a mapping")
    return data


def _brick_spec_instruction_body(text: str) -> str:
    """Return the markdown body after the closing frontmatter fence ('' if none).

    ⑤: the body is the agent-readable kind instruction the Builder carries onto the
    step_template registry row (then the request builder threads it to the prompt).
    Mirrors check_bricks_spec_completeness._instruction_body so the carried body is
    byte-identical to what the alignment guard inspects. This is plain-text
    extraction only; it makes no judgment about the body's content.
    """
    if not text.startswith("---"):
        return text
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return ""
    after = parts[1]
    newline = after.find("\n")
    return after[newline + 1:] if newline != -1 else ""


def _agent_is_writer(agent_object: Mapping[str, Any]) -> bool:
    """True if the Agent Object carries any write-capable tool policy.

    The capability rule lives in agent_resources.py; here we only read the
    already-validated tool_policy_refs. write capability is carried by one of
    the WRITER_TOOL_POLICY_REFS (admissible for worker, leader, or reviewer lane,
    enforced by that module; actual effective write still requires a Brick write_scope NEED).
    """
    return bool(WRITER_TOOL_POLICY_REFS.intersection(agent_object.get("tool_policy_refs", ())))


def _candidate_agents_for_need(repo: Path, role_need: str, write_need: bool) -> list[str]:
    """Agent Object refs whose CAPABILITY SATISFIES the brick NEED.

    candidate = lane == role_need AND (write_need implies writer-capability); a
    write-capable agent may also serve a read-only need (capability >= need).
    Effective write remains gated by the Brick write_scope NEED downstream, so a
    write-capable agent on a read-only-need brick still cannot write. lane and
    tool_policy_refs are read via agent_resources.resolve_agent_object (the Agent
    axis owns the capability rule); this is the NEED<->CAPABILITY match, not a
    re-derivation of capability.
    """
    candidates: list[str] = []
    for ref in list_agent_object_refs(repo):
        agent_object = resolve_agent_object(ref, repo_root=repo)["agent_object"]
        if str(agent_object.get("lane", "")) != role_need:
            continue
        # capability >= need: a write-capable agent may also serve a read-only
        # need; only EXCLUDE a non-writer when the brick NEEDS write. Effective
        # write is still gated by the Brick write_scope NEED downstream.
        if write_need and not _agent_is_writer(agent_object):
            continue
        candidates.append(ref)
    return candidates


def _resolve_agent_for_need(
    repo: Path,
    role_need: str,
    write_need: bool,
    default_agent: str | None = None,
    declared_override: str | None = None,
) -> str:
    """Select the performing Agent by matching the brick NEED to Agent CAPABILITY.

    The match (lane == role_need AND (write_need implies writer-capability); a
    write-capable agent may serve a read-only need; effective write remains gated
    by the Brick write_scope NEED) is the authority. ``default_agent`` is an
    OPTIONAL hint that only pre-fills / breaks
    ties; ``declared_override`` is an author override. Both, if given, MUST be in
    the candidate set (they cannot escape the NEED). With no hint and exactly one
    candidate, that candidate is selected; otherwise the need is ambiguous and the
    author must declare a default_agent hint or an override.
    """
    if not isinstance(role_need, str) or not role_need.strip():
        raise ValueError("role_need must be non-empty text")
    write_need = bool(write_need)
    candidates = _candidate_agents_for_need(repo, role_need, write_need)
    # Normalize/reject malformed optional hints BEFORE the set-membership test
    # (a non-str default_agent like a YAML list would raise an uncaught TypeError
    # on `in candidate_set`); a malformed hint is a clean validation error.
    for _hint_label, _hint in (("default_agent", default_agent), ("agent override", declared_override)):
        if _hint is not None and (not isinstance(_hint, str) or not _hint.strip()):
            raise ValueError(
                f"{_hint_label} must be a non-empty agent-object ref (got {_hint!r})"
            )
    candidate_set = set(candidates)
    if declared_override is not None:
        if declared_override in candidate_set:
            return declared_override
        raise ValueError(
            f"agent override {declared_override} violates NEED "
            f"(role_need={role_need}, write_need={write_need}); "
            f"candidates: {sorted(candidate_set)}"
        )
    if default_agent is not None:
        if default_agent in candidate_set:
            return default_agent
        raise ValueError(
            f"default_agent {default_agent} violates its own NEED "
            f"(role_need={role_need}, write_need={write_need}); "
            f"candidates: {sorted(candidate_set)}"
        )
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(
        f"ambiguous agent for need (role_need={role_need}, write_need={write_need}): "
        "declare default_agent hint or an agent override; "
        f"candidates: {sorted(candidate_set)}"
    )


def _render_candidate_agents_for_need(
    repo: Path,
    role_need: str,
    write_need: bool,
) -> list[dict[str, Any]]:
    """READ-ONLY rows: every Agent CAPABILITY that MATCHES the brick NEED.

    For each ref returned by ``_candidate_agents_for_need`` this resolves the
    Agent Object and records a MECHANICAL match row (lane, writer-capability,
    tool_policy_refs, and a match_reason that states ONLY lane + write scope).
    It MEASURES/RECORDS the candidate set; it does NOT pick among >=2, does NOT
    rank, does NOT recommend, and does NOT judge agent quality. ``qualifies`` is
    a count-fact only: True when the need is ambiguous (total >= 2) and the
    choice therefore belongs to the author / COO. Rows are sorted deterministically
    by ``agent_object_ref`` (not by any quality order). The single-candidate need
    still auto-resolves through ``_resolve_agent_for_need`` (unchanged); this
    surface is the informed view beside the fail-closed >=2 ValueError, never a
    replacement for it.
    """
    if not isinstance(role_need, str) or not role_need.strip():
        raise ValueError("role_need must be non-empty text")
    write_need = bool(write_need)
    refs = _candidate_agents_for_need(repo, role_need, write_need)
    total = len(refs)
    ambiguous = total >= 2
    write_scope_word = "yes" if write_need else "no"
    rows: list[dict[str, Any]] = []
    for ref in refs:
        agent_object = resolve_agent_object(ref, repo_root=repo)["agent_object"]
        tool_policy_refs = list(agent_object.get("tool_policy_refs", ()))
        adapter_refs = list(agent_object.get("adapter_refs", ()))
        rows.append(
            {
                "agent_object_ref": ref,
                "name": str(agent_object.get("name", "")),
                "lane": str(agent_object.get("lane", "")),
                "writer_capable": _agent_is_writer(agent_object),
                "tool_policy_refs": tool_policy_refs,
                "adapter_refs": adapter_refs,
                "preferred_adapter_ref": str(agent_object.get("preferred_adapter_ref") or ""),
                "preferred_model_ref": str(agent_object.get("preferred_model_ref") or ""),
                # MECHANICAL match reason ONLY: the two NEED<->CAPABILITY axes that
                # admitted this ref. No quality, no ranking, no recommendation.
                "match_reason": f"lane={role_need}, write_scope={write_scope_word}",
                # Count-fact: a single candidate auto-resolves; >=2 is a COO/author
                # decision (this is NOT a per-row quality verdict).
                "qualifies": ambiguous,
            }
        )
    return rows


# RETIRED legacy frontmatter spellings (the 0607/08 rename's transition aliases,
# CUT 0610): the loader REJECTS them loudly with the canonical key named, instead
# of reading them (the old behavior) or silently ignoring them. The Builder reads
# ONLY the canonical keys below.
_RETIRED_BRICK_FRONTMATTER_KEYS: dict[str, str] = {
    "agent_word": "performer_word",
    "write_need": "requires_brick_write_scope",
    "role_need": "performer_lane_need",
    "return_template": "required_return_template_refs",
    "default_link": "link_movement_literal",
    "default_agent": "agent_object_hint_ref",
}


def _reject_retired_brick_frontmatter_keys(fm: Mapping[str, Any], label: str) -> None:
    present = sorted(key for key in _RETIRED_BRICK_FRONTMATTER_KEYS if key in fm)
    if present:
        renames = ", ".join(
            f"'{key}' (use '{_RETIRED_BRICK_FRONTMATTER_KEYS[key]}')" for key in present
        )
        raise ValueError(
            f"{label}: retired legacy frontmatter key(s) not admitted: {renames}"
        )


def _frontmatter_write_need(value: Any, label: str) -> bool:
    """Normalize requires_brick_write_scope to a bool (yes/no admitted)."""
    if value is True or value is False:
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text == "yes":
            return True
        if text == "no":
            return False
    raise ValueError(f"{label} must be yes/no (got {value!r})")


_BRICK_CAPABILITY_CLASSES = frozenset(
    {
        "read",
        "probe_write",
        "verification_write",
        "source_write",
        "artifact_write",
    }
)


def _frontmatter_capability_class(value: Any, label: str) -> str:
    """Normalize the non-authoritative Brick capability taxonomy label."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be one admitted capability class")
    text = value.strip()
    if text not in _BRICK_CAPABILITY_CLASSES:
        raise ValueError(
            f"{label} must be one of {sorted(_BRICK_CAPABILITY_CLASSES)!r} "
            f"(got {value!r})"
        )
    return text


def _brick_spec_paths(repo: Path) -> tuple[Path, ...]:
    """Return active Brick spec paths from canonical bricks/<kind>/brick.md."""

    bricks_dir = repo / BRICKS_SPEC_DIR
    if not bricks_dir.is_dir():
        raise ValueError(f"{BRICKS_SPEC_DIR.as_posix()} must exist")
    legacy = sorted(bricks_dir.glob("*.md"))
    if legacy:
        rels = ", ".join(path.relative_to(repo).as_posix() for path in legacy)
        raise ValueError(
            "flat Brick specs are retired; use bricks/<kind>/brick.md "
            f"(found {rels})"
        )
    canonical: dict[str, Path] = {}
    for path in sorted(bricks_dir.glob("*/brick.md")):
        kind = path.parent.name
        if kind in canonical:
            raise ValueError(f"duplicate canonical brick spec for kind {kind}: {path}")
        canonical[kind] = path
    return tuple(canonical[kind] for kind in sorted(canonical))


def _step_templates_from_bricks(repo: Path) -> dict[str, dict[str, Any]]:
    """Build the step_templates registry dict from Brick spec frontmatter.

    The Builder's step template rows are sourced from per-kind Brick specs.
    Active frontmatter names separate Brick work contract fields from Builder
    selection metadata. ONLY the canonical names are read; the retired legacy
    spellings (_RETIRED_BRICK_FRONTMATTER_KEYS) are rejected loudly with the
    canonical key named (L legacy cut, 0610).
    """
    step_templates: dict[str, dict[str, Any]] = {}
    for path in _brick_spec_paths(repo):
        label = f"brick spec {path.relative_to(repo).as_posix()}"
        spec_text = path.read_text(encoding="utf-8")
        fm = _brick_spec_frontmatter(spec_text, label)
        _reject_retired_brick_frontmatter_keys(fm, label)
        kind = _required_yaml_text(fm, "brick_kind", label)
        path_kind = path.parent.name if path.name == "brick.md" else path.stem
        if kind != path_kind:
            raise ValueError(f"{label}: brick_kind '{kind}' must match path kind '{path_kind}'")
        # NEED<->CAPABILITY: the Builder resolves the performing Agent by
        # matching performer_lane_need + requires_brick_write_scope to Agent
        # Object lane / writer capability. agent_object_hint_ref only pre-fills
        # or breaks ties; it cannot escape the NEED.
        role_need = _required_yaml_text(fm, "performer_lane_need", label)
        write_need = _frontmatter_write_need(
            fm.get("requires_brick_write_scope"),
            f"{label}.requires_brick_write_scope",
        )
        agent_object_ref = _resolve_agent_for_need(
            repo,
            role_need,
            write_need,
            default_agent=fm.get("agent_object_hint_ref"),
        )
        return_template_refs = _return_template_refs(
            fm.get("required_return_template_refs"),
            label,
        )
        row: dict[str, Any] = {
            "step_template_ref": f"building-step-template:{kind}",
            "brick_spec_ref": path.relative_to(repo).as_posix(),
            # brick_word and performer_word are compact matching metadata the
            # declared-plan path reads; internally the row keeps the historical
            # agent_word key for compatibility with declared intent fixtures.
            "brick_word": _required_yaml_text(fm, "brick_word", label),
            "agent_word": _required_yaml_text(fm, "performer_word", label),
            "agent_object_ref": agent_object_ref,
            "link_word": _required_yaml_text(fm, "link_movement_literal", label),
            "brick_contract": _required_yaml_text(fm, "brick_contract", label),
            "capability_class": _frontmatter_capability_class(
                fm.get("capability_class"),
                f"{label}.capability_class",
            ),
            "brick_template_refs": return_template_refs,
            # The kind's REAL declared return shape (comma-joined field list),
            # read from the PRIMARY return_template (refs[0]) only. The Builder
            # uses this as the default required_return_shape when a node omits it
            # (document-centric: gate requires the kind's real fields). The 2nd
            # ref (transition-concern) carries no required_return_shape and is
            # intentionally ignored for the field list.
            "required_return_shape": _required_return_shape_from_primary_template(
                repo, return_template_refs[0], label
            ),
            # The kind's HANDOFF subset (carries_forward_fields) read from the SAME
            # primary return_template, comma-joined the same way as
            # required_return_shape so it tokenizes identically downstream. Carried
            # onto the registry row so composition can stamp it onto the brick_row
            # (beside required_return_shape) and the walker carry seam can FILTER the
            # forwarded summary to it. EMPTY when the template omits it (no filter).
            "carries_forward_fields": _carries_forward_fields_from_primary_template(
                repo, return_template_refs[0], label
            ),
            # ⑤ the kind's STATIC instruction (the brick.md ## body) carried onto the
            # registry row from the SAME file read once above, so composition_compose.py can
            # stamp it onto the brick_row and the request builder threads it to the
            # agent prompt. Selection metadata, not declared-plan output.
            "brick_instruction_body": _brick_spec_instruction_body(spec_text),
            # carried so the override guard (composition_graph_validate.py) can re-check a node
            # override against the same NEED without re-parsing the Brick spec.
            "role_need": role_need,
            "write_need": write_need,
        }
        _store_step_template(step_templates, row, source="brick spec frontmatter")
    return step_templates


def _safe_return_template_ref(ref: str, label: str) -> str:
    """Reject a return_template entry that is absolute or escapes the repo via '..'.

    The return_template must be a repo-relative template path (the Builder
    resolves it under the repo root); an absolute path or a '..' segment could
    point outside the repo, so it is rejected fail-closed.
    """
    pure = PurePosixPath(ref)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(
            f"{label}: return_template '{ref}' must be a repo-relative path "
            "(no absolute path, no '..' segment)"
        )
    return ref


def _required_return_shape_from_primary_template(repo: Path, primary_ref: str, label: str) -> str:
    """Derive a comma-joined field list from a kind's PRIMARY return_template YAML.

    Reads the primary return_template (refs[0]) and extracts its top-level
    ``required_return_shape:`` list (a flat list of scalar field names), returning
    them comma-joined (e.g. "made_changes,observed_evidence,..."). This is the
    kind's REAL declared return shape, used as the Builder default when a node
    omits required_return_shape; it stays compatible with
    brick.work.parse_required_return_shape (plain comma-joined field list, no JSON).

    The primary ref must declare a required_return_shape list (every PRIMARY ref
    does); a primary that lacks the key (e.g. the secondary transition-concern
    file, which is never passed here) raises a CLEAR error fail-closed.
    """
    template_path = _split_catalog_file_path(repo, primary_ref)
    doc = _load_yaml_mapping(template_path, f"{label} return_template {primary_ref}")
    shape = doc.get("required_return_shape")
    if not isinstance(shape, Sequence) or isinstance(shape, (str, bytes)):
        raise ValueError(
            f"{label}: primary return_template '{primary_ref}' must declare a "
            "required_return_shape list"
        )
    fields: list[str] = []
    for index, item in enumerate(shape):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{label}: return_template '{primary_ref}' required_return_shape[{index}] "
                "must be non-empty text"
            )
        fields.append(item.strip())
    if not fields:
        raise ValueError(
            f"{label}: return_template '{primary_ref}' required_return_shape is empty"
        )
    return ",".join(fields)


def _carries_forward_fields_from_primary_template(repo: Path, primary_ref: str, label: str) -> str:
    """Derive the comma-joined carries_forward_fields from a kind's PRIMARY return_template.

    Reads the primary return_template (refs[0]) and extracts its OPTIONAL top-level
    ``carries_forward_fields:`` list -- the kind's HANDOFF subset of
    required_return_shape. Returns the fields comma-joined (compatible with
    brick.work.parse_carries_forward_fields), or "" when the key is ABSENT or empty.

    Unlike required_return_shape this is OPTIONAL: a kind that has not (yet)
    declared a carry-forward set yields "", which the walker carry seam reads as
    "no filter" (full-summary carry preserved, backward-safe). A PRESENT key,
    however, must be a list of non-empty strings (fail-closed on a malformed
    declaration so a typo cannot silently disable the filter).
    """
    template_path = _split_catalog_file_path(repo, primary_ref)
    doc = _load_yaml_mapping(template_path, f"{label} return_template {primary_ref}")
    shape = doc.get("carries_forward_fields")
    if shape is None:
        return ""
    if not isinstance(shape, Sequence) or isinstance(shape, (str, bytes)):
        raise ValueError(
            f"{label}: return_template '{primary_ref}' carries_forward_fields must be a "
            "list of field names when present"
        )
    fields: list[str] = []
    for index, item in enumerate(shape):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{label}: return_template '{primary_ref}' carries_forward_fields[{index}] "
                "must be non-empty text"
            )
        fields.append(item.strip())
    return ",".join(fields)


def _return_template_refs(value: Any, label: str) -> list[str]:
    """Normalize a frontmatter return_template (single path or list of paths) to a list."""
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(f"{label}: return_template must be non-empty text")
        return [_safe_return_template_ref(value.strip(), label)]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        refs: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"{label}: return_template[{index}] must be non-empty text")
            refs.append(_safe_return_template_ref(item.strip(), label))
        if not refs:
            raise ValueError(f"{label}: return_template list is empty")
        return refs
    raise ValueError(f"{label}: return_template must be a path or a list of paths")


def _chain_presets_from_presets(repo: Path) -> dict[str, Any]:
    """Build the chain_presets registry dicts from presets/<name>.md frontmatter.

    Each presets/<name>.md frontmatter IS the preset's structure (its former YAML
    keys verbatim: preset_ref, selected_shape_ref, intent, selection_hint,
    catalog_scope, steps[] (including step_template_ref + brick_spec_ref), and
    any of gate_concept_profile / gate_sequence_policy /
    common_basis_ref / proof_limits). The `## Route` body is
    author route-intent prose and is NOT read here. canonical-vs-dogfood is split by
    catalog_scope. The legacy ``compat_preset_refs`` alias expansion is RETIRED
    (L legacy cut, 0610): a preset frontmatter still carrying the key is REJECTED
    loudly here (never silently ignored), and an old short preset ref is no longer
    an alias -- callers get the existing unknown-preset failure. The stored preset
    is dict(frontmatter) (the whole frontmatter mapping verbatim), so the resulting
    chain_presets dict is byte-identical to the former per-file .yaml source.

    A preset carries NO nodes/edges/groups (those stay Builder-synthesized in
    compose_building); it is a DECLARED ROUTE only, and target_word stays a local
    preset hint, never Link Movement.
    """
    presets_dir = repo / PRESETS_SPEC_DIR
    if not presets_dir.is_dir():
        raise ValueError(f"{PRESETS_SPEC_DIR.as_posix()} must exist")
    chain_presets: dict[str, dict[str, Any]] = {}
    common_chain_presets: dict[str, dict[str, Any]] = {}
    dogfood_chain_presets: dict[str, dict[str, Any]] = {}

    # Single pass over a stable (sorted) file order: store every preset_ref
    # (common into common_chain_presets, dogfood into dogfood_chain_presets).
    # The former second pass (compat_preset_refs alias expansion) is RETIRED:
    # a preset declaring the legacy key is rejected loudly below, so an old
    # short preset ref now fails as unknown at the existing call sites.
    for path in sorted(presets_dir.glob("*.md")):
        label = f"preset spec {path.relative_to(repo).as_posix()}"
        fm = _brick_spec_frontmatter(path.read_text(encoding="utf-8"), label)
        if "compat_preset_refs" in fm:
            raise ValueError(
                f"{label}: 'compat_preset_refs' is retired (legacy preset alias "
                "grammar); remove the key -- callers must use the canonical "
                "preset_ref"
            )
        preset_ref = _required_yaml_text(fm, "preset_ref", label)
        scope = _required_yaml_text(fm, "catalog_scope", label)
        # catalog_scope is the common-vs-dogfood separator (codex U3 P2): an unknown
        # value (typo / new scope) must be REJECTED, not silently registered as common
        # (which would expose a local dogfood route as a common preset).
        if scope not in ("common", PRESET_DOGFOOD_SCOPE):
            raise ValueError(
                f"{label}: catalog_scope must be 'common' or '{PRESET_DOGFOOD_SCOPE}' (got {scope!r})"
            )
        stored = dict(fm)
        is_dogfood = scope == PRESET_DOGFOOD_SCOPE
        if preset_ref in chain_presets:
            if is_dogfood and preset_ref in common_chain_presets:
                raise ValueError(
                    f"dogfood chain preset conflicts with common preset: {preset_ref}"
                )
            raise ValueError(f"chain preset conflicts with another preset: {preset_ref}")
        chain_presets[preset_ref] = stored
        if is_dogfood:
            dogfood_chain_presets[preset_ref] = stored
        else:
            common_chain_presets[preset_ref] = stored

    return {
        "chain_presets": chain_presets,
        "common_chain_presets": common_chain_presets,
        "dogfood_chain_presets": dogfood_chain_presets,
        # Shape-compatible projection key: alias grammar is retired, so this is
        # ALWAYS empty now (downstream readers -- composition, declaration
        # packets, design toolkit / MCP projection -- keep their shape).
        "chain_preset_aliases": {},
    }


def _load_yaml_mapping(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} file is missing: {path}")
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ValueError(f"{label} requires PyYAML") from exc
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, Mapping):
        raise ValueError(f"{label} must parse to a mapping")
    return loaded


def _split_catalog_file_path(repo: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("split catalog file refs must stay inside repo")
    return repo / path


def _required_yaml_mapping(
    value: Mapping[str, Any],
    key: str,
    label: str,
) -> Mapping[str, Any]:
    nested = value.get(key)
    if not isinstance(nested, Mapping):
        raise ValueError(f"{label}.{key} must be a mapping")
    return nested


def _required_yaml_text(value: Mapping[str, Any], key: str, label: str) -> str:
    raw = value.get(key)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label}.{key} must be non-empty text")
    return raw.strip()


def _yaml_mapping_rows(value: Any, label: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be an array")
    rows: list[Mapping[str, Any]] = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            raise ValueError(f"{label}[{index}] must be a mapping")
        rows.append(row)
    return tuple(rows)


def _yaml_text_tuple(value: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if allow_empty and value in (None, ()):
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{label} must be an array")
    refs: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}[{index}] must be non-empty text")
        refs.append(item.strip())
    return tuple(refs)


def _is_caller_or_coo_declaration(value: str) -> bool:
    normalized = value.strip().lower().replace("_", "-")
    parts = {part for segment in normalized.split() for part in segment.split("-")}
    return bool(parts & CALLER_OR_COO_DECLARATION_MARKERS)


def _intent_uses_step_templates(intent: Mapping[str, Any]) -> bool:
    raw_steps = intent.get("steps")
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
        return False
    for raw_step in raw_steps:
        if isinstance(raw_step, Mapping) and (
            "step_template_ref" in raw_step
            or (
                {"brick_word", "agent_word"}.issubset(raw_step)
                and ("link_word" in raw_step or isinstance(raw_step.get("link"), str))
            )
        ):
            return True
    return False


def _validate_declared_plan_projection(plan: Mapping[str, Any]) -> None:
    from support.operator.plan_validation import (  # noqa: PLC0415
        _declared_plan_brick_refs,
        _declared_plan_link_edges,
        _task_source_ref_from_plan,
        _validate_declared_plan_route_replay_edges,
        _validate_declared_step_link,
    )

    _task_source_ref_from_plan(plan)
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("rendered plan must contain non-empty steps")
    declared_brick_refs = _declared_plan_brick_refs(steps)
    declared_link_edges = _declared_plan_link_edges(steps)
    _validate_declared_plan_route_replay_edges(steps, declared_link_edges)
    for raw_step in steps:
        _validate_declared_step_link(raw_step, declared_brick_refs=declared_brick_refs)


def _render_declared_step(index: int, raw_step: Mapping[str, Any]) -> Mapping[str, Any]:
    step_ref = _clean_text(f"steps[{index}].step_ref", raw_step.get("step_ref", ""))
    # Read EVERY casting dial generically (E2/S6★): loop the single-source
    # NODE_CASTING_FIELDS rather than naming adapter/model, so a NEW dial (effort)
    # passes through this declared-step renderer with no edit. None == undeclared.
    raw_step_casting = {key: raw_step.get(key) for key in NODE_CASTING_FIELDS}
    brick = _mapping_value(f"steps[{index}].brick", raw_step.get("brick"))
    agent = _mapping_value(f"steps[{index}].agent", raw_step.get("agent"))
    link = _mapping_value(f"steps[{index}].link", raw_step.get("link"))

    agent_extras = {
        "prompt_refs",
        "skill_refs",
        "hook_refs",
        "tool_policy_refs",
        "discipline_refs",
        "adapter_refs",
        "provider_connector_refs",
    }.intersection(agent)
    if agent_extras:
        raise ValueError(
            "Agent resources must stay behind agent_object_ref; inline fields rejected: "
            + ", ".join(sorted(agent_extras))
        )

    movement = _clean_text(f"steps[{index}].link.movement", link.get("movement", ""))
    target_ref = _clean_text(f"steps[{index}].link.target_ref", link.get("target_ref", ""))
    if any(token in movement for token in (" or ", " and ", ",", "|", "/")):
        raise ValueError("Link movement must be one declared literal")
    if any(token in target_ref for token in (" or ", " and ", ",", "|")):
        raise ValueError("Link target must be one declared target")

    rendered: dict[str, Any] = {
        "step_ref": step_ref,
        "rows": [
            {
                "axis": "Brick",
                "row_ref": _clean_text(f"steps[{index}].brick.row_ref", brick.get("row_ref", "")),
                "brick_work_ref": _clean_text(
                    f"steps[{index}].brick.brick_work_ref",
                    brick.get("brick_work_ref", ""),
                ),
                "brick_instance_ref": _clean_text(
                    f"steps[{index}].brick.brick_instance_ref",
                    brick.get("brick_instance_ref", ""),
                ),
                "work_statement": _clean_text(
                    f"steps[{index}].brick.work_statement",
                    brick.get("work_statement", ""),
                ),
                "comparison_rule": _clean_text(
                    f"steps[{index}].brick.comparison_rule",
                    brick.get("comparison_rule", ""),
                ),
                "required_return_shape": _clean_text(
                    f"steps[{index}].brick.required_return_shape",
                    brick.get("required_return_shape", ""),
                ),
            },
            {
                "axis": "Agent",
                "row_ref": _clean_text(f"steps[{index}].agent.row_ref", agent.get("row_ref", "")),
                "agent_object_ref": _clean_text(
                    f"steps[{index}].agent.agent_object_ref",
                    agent.get("agent_object_ref", ""),
                ),
            },
            {
                "axis": "Link",
                "row_ref": _clean_text(f"steps[{index}].link.row_ref", link.get("row_ref", "")),
                "movement": movement,
                "target_ref": target_ref,
            },
        ],
    }
    source_facts = brick.get("source_facts")
    if source_facts is not None:
        rendered["rows"][0]["source_facts"] = list(_text_sequence("source_facts", source_facts))
    write_scope = brick.get("write_scope")
    if write_scope is not None:
        rendered["rows"][0]["write_scope"] = _mapping_value("write_scope", write_scope)
    capability_class = brick.get("capability_class")
    if capability_class is not None:
        rendered["rows"][0]["capability_class"] = _clean_text(
            f"steps[{index}].brick.capability_class",
            capability_class,
        )
    # Carry the EXPLICIT write NEED marker (requires_brick_write_scope; legacy
    # write_need) from the declared brick onto the rendered plan row VERBATIM.
    # Without this carry the linear materializer's stamp would be silently
    # dropped here and strict run admission (require_write_need_marker) would
    # reject every freshly rendered write-needed linear plan. Value validation
    # (bool / yes / no, fail-closed) stays owned by
    # brick.spec.declared_brick_write_need; this is transport only.
    if "requires_brick_write_scope" in brick:
        rendered["rows"][0]["requires_brick_write_scope"] = brick.get(
            "requires_brick_write_scope"
        )
    elif "write_need" in brick:
        rendered["rows"][0]["write_need"] = brick.get("write_need")
    next_brick_instance_ref = link.get("next_brick_instance_ref")
    if next_brick_instance_ref is not None:
        rendered["rows"][2]["next_brick_instance_ref"] = _clean_text(
            f"steps[{index}].link.next_brick_instance_ref",
            next_brick_instance_ref,
        )
    declared_gate_refs = link.get("declared_gate_refs")
    if declared_gate_refs is not None:
        rendered["rows"][2]["declared_gate_refs"] = list(
            _text_sequence("declared_gate_refs", declared_gate_refs)
        )
    for optional_link_object in (
        "gate_sequence_policy",
        # A1 (0610): translated-gate provenance (gate_concept_provenance) is an
        # optional Link-row mapping like the others; carried verbatim when the
        # materializer stamped it, never invented here.
        "gate_concept_provenance",
        "transition_authoring",
        "route_decision_basis",
        "transition_lifecycle",
        "route_replay_plan",
        "building_lifecycle",
    ):
        if optional_link_object in link:
            if optional_link_object == "gate_sequence_policy":
                value = link.get(optional_link_object)
                if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                    raise ValueError("gate_sequence_policy must be an ordered array")
                rendered["rows"][2][optional_link_object] = [
                    dict(
                        _mapping_value(
                            f"steps[{index}].link.{optional_link_object}[{item_index}]",
                            item,
                        )
                    )
                    for item_index, item in enumerate(value)
                ]
            else:
                rendered["rows"][2][optional_link_object] = dict(
                    _mapping_value(
                        f"steps[{index}].link.{optional_link_object}",
                        link.get(optional_link_object),
                    )
                )
    # Emit EVERY declared casting dial generically (E2/S6★): loop CASTING_FIELDS,
    # dispatching the per-dial cleaner — the fail-closed adapter dial keeps its
    # retired-ref check (_clean_selected_adapter_ref, the LAW-adjacent guard), every
    # deferrable dial (model/effort) is plain cleaned text. Byte-identical to the
    # prior two hand-named emits; a NEW dial passes through with no edit.
    for descriptor in CASTING_FIELDS:
        key = selected_key(descriptor)
        value = raw_step_casting.get(key)
        if value is None:
            continue
        if descriptor.fail_closed:
            rendered[key] = _clean_selected_adapter_ref(f"steps[{index}].{key}", value)
        else:
            rendered[key] = _clean_text(f"steps[{index}].{key}", value)
    if raw_step.get("step_template_ref") is not None:
        rendered["step_template_ref"] = _clean_text(
            f"steps[{index}].step_template_ref",
            raw_step.get("step_template_ref"),
        )
    return rendered

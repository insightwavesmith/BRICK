"""Preset -> graph declaration emit (composition concern submodule).

Positional fan-out + declared-topology + sequential graph emitters plus the
node/edge builders and the route-decision-basis carry. PURE relocation out of
composition.py: the members are cut VERBATIM (no logic/name/signature/order
change). composition.py keeps a facade re-export so every existing
``from brick_protocol.support.operator.composition import X`` still resolves.

Sibling helpers that still live in composition.py (compose_building,
_chain_preset_steps, _validate_declared_brick_spec_ref,
_materializer_reject_unused_step_selection_overrides,
_materializer_preset_step_with_selection_override,
_composition_gate_sequence_profile_steps) are imported LAZILY inside the
functions that use them to avoid an import cycle with composition.py.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.link.gate import (
    COO_GATE_REF,
    HUMAN_GATE_REF,
)
from brick_protocol.link.spec import translate_gate_concept
from brick_protocol.support.operator.building_operation_common import (
    DEFAULT_LINK_GATE_REF,
    _clean_text,
    _mapping_value,
    _text_sequence,
)
from brick_protocol.support.operator.primitives import (
    NODE_CASTING_FIELDS,
)
from brick_protocol.support.operator.composition_common import (
    ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT,
    _ROUTE_POLICY_PROVENANCE_VALUES,
    _composition_gate_sequence_ref,
    _composition_optional_text,
    _composition_slug,
    _materializer_step_template_slug,
    _materializer_strip_field,
)
from brick_protocol.support.operator.composition_kinds import (
    _materializer_step_alias,
    _materializer_step_template,
)
from brick_protocol.support.operator.composition_route_policy import (
    _materializer_closure_policy,
    _materializer_preset_closure_policy,
    _materializer_reroute_budget_cascade,
)
from brick_protocol.support.operator.composition_gate_translation import (
    _QA_ROLE_NEED,
    _materializer_gate_concept_provenance,
    _materializer_gate_concept_tokens,
    _materializer_human_gate_hold_policy,
    _materializer_profile_gate_translations,
)


def _materializer_graph_plan(
    intent: Mapping[str, Any],
    preset: Mapping[str, Any],
    registry: Mapping[str, Any],
    *,
    repo: Path,
    building_id: str,
    declared_by: str,
    chain_preset_ref: str,
    task_summary: str,
    task_source_ref: str,
    source_facts: Sequence[str],
    write_scope: Mapping[str, Any] | None,
    step_selection_overrides: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    from brick_protocol.support.operator.composition import compose_building

    # Per-Building OVERRIDE (config cascade): the caller/COO MAY declare route
    # policy values on the intent that beat the preset default. Support reads them
    # verbatim from the intent (a HUMAN-authored declaration) -> provenance
    # per-building; it never invents them. Absent -> preset default. Both go
    # through the SAME validators as the preset values.
    graph = _materializer_graph_declaration(
        preset,
        registry,
        repo=repo,
        building_id=building_id,
        task_summary=task_summary,
        task_source_ref=task_source_ref,
        source_facts=source_facts,
        write_scope=write_scope,
        override_reroute_budgets=intent.get("node_reroute_budgets"),
        override_closure_policy=intent.get("closure_transition_target_policy"),
        chain_preset_ref=chain_preset_ref,
        step_selection_overrides=step_selection_overrides,
    )
    plan = dict(
        compose_building(
            graph["nodes"],
            graph["edges"],
            selected_shape_ref=str(preset.get("selected_shape_ref", intent.get("selected_shape_ref", "")) or ""),
            declared_by=declared_by,
            groups=graph["groups"],
            chain_preset_ref=chain_preset_ref,
            plan_ref=str(intent.get("plan_ref") or f"building-plan:{building_id}"),
            building_id=building_id,
            repo_root=repo,
            # selected_adapter_ref was validated (non-blank) at the materialize entry
            # (materialize_building_intent), so there is no support default path here.
            # model:default stays a sentinel default (adapter picks its own default model).
            selected_adapter_ref=str(intent["selected_adapter_ref"]),
            selected_model_ref=str(intent.get("selected_model_ref", "model:default") or "model:default"),
        )
    )
    plan = _materializer_apply_route_decision_basis(plan, intent)
    plan["task_source_ref"] = task_source_ref
    return plan


def _materializer_apply_route_decision_basis(
    plan: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Deliver the INTENT-declared route_decision_basis to review-gated rows.

    Mechanical carry only: the caller/COO declared the basis (override_refs /
    human_review_refs disposition facts) on the intent; support copies it onto
    each Link row that declares a coo or human review gate and has no basis of
    its own. Works over BOTH plan shapes (graph link_edges rows and linear
    steps rows). Support never invents a basis (absent intent key -> no-op).
    """

    basis = _materializer_route_decision_basis(intent)
    if not basis:
        return plan
    applied = False

    def _patched_rows(rows: Any) -> list[Any]:
        nonlocal applied
        patched: list[Any] = []
        if not isinstance(rows, list):
            return rows
        for row in rows:
            if not isinstance(row, Mapping):
                patched.append(row)
                continue
            patched_row = dict(row)
            if (
                patched_row.get("axis") == "Link"
                and (
                    _materializer_link_row_has_gate_ref(patched_row, COO_GATE_REF)
                    or _materializer_link_row_has_gate_ref(patched_row, HUMAN_GATE_REF)
                )
                and "route_decision_basis" not in patched_row
            ):
                patched_row["route_decision_basis"] = dict(basis)
                applied = True
            patched.append(patched_row)
        return patched

    patched_plan = dict(plan)
    link_edges = plan.get("link_edges")
    if isinstance(link_edges, list):
        patched_edges: list[Any] = []
        for edge in link_edges:
            if not isinstance(edge, Mapping):
                patched_edges.append(edge)
                continue
            patched_edge = dict(edge)
            if isinstance(edge.get("rows"), list):
                patched_edge["rows"] = _patched_rows(edge.get("rows"))
            patched_edges.append(patched_edge)
        patched_plan["link_edges"] = patched_edges
    steps = plan.get("steps")
    if isinstance(steps, list):
        patched_steps: list[Any] = []
        for step in steps:
            if not isinstance(step, Mapping):
                patched_steps.append(step)
                continue
            patched_step = dict(step)
            if isinstance(step.get("rows"), list):
                patched_step["rows"] = _patched_rows(step.get("rows"))
            patched_steps.append(patched_step)
        patched_plan["steps"] = patched_steps
    if not applied:
        return plan
    return patched_plan


def _materializer_route_decision_basis(intent: Mapping[str, Any]) -> Mapping[str, Any]:
    if "route_decision_basis" not in intent:
        return {}
    raw = _mapping_value("route_decision_basis", intent.get("route_decision_basis"))
    basis: dict[str, Any] = {}
    for key in ("override_refs", "human_review_refs"):
        if key in raw:
            basis[key] = list(_text_sequence(f"route_decision_basis.{key}", raw.get(key)))
    if "proof_limits" in raw:
        basis["proof_limits"] = list(_text_sequence("route_decision_basis.proof_limits", raw.get("proof_limits")))
    if "not_proven" in raw:
        basis["not_proven"] = list(_text_sequence("route_decision_basis.not_proven", raw.get("not_proven")))
    return basis


def _materializer_link_row_has_gate_ref(row: Mapping[str, Any], gate_ref: str) -> bool:
    declared_refs = row.get("declared_gate_refs")
    if isinstance(declared_refs, Sequence) and not isinstance(declared_refs, (str, bytes)):
        if gate_ref in {str(item).strip() for item in declared_refs}:
            return True
    sequence = row.get("gate_sequence_policy")
    if isinstance(sequence, Sequence) and not isinstance(sequence, (str, bytes)):
        for item in sequence:
            if isinstance(item, Mapping) and _composition_gate_sequence_ref(item) == gate_ref:
                return True
    return False


def _materializer_graph_declaration(
    preset: Mapping[str, Any],
    registry: Mapping[str, Any],
    *,
    repo: Path,
    building_id: str,
    task_summary: str,
    task_source_ref: str,
    source_facts: Sequence[str],
    write_scope: Mapping[str, Any] | None,
    override_reroute_budgets: Any = None,
    override_closure_policy: Any = None,
    chain_preset_ref: str = "",
    step_selection_overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> Mapping[str, list[Mapping[str, Any]]]:
    from brick_protocol.support.operator.composition import (
        _chain_preset_steps,
        _materializer_preset_step_with_selection_override,
        _materializer_reject_unused_step_selection_overrides,
        _validate_declared_brick_spec_ref,
    )

    raw_steps = list(_chain_preset_steps(preset))
    selection_overrides = step_selection_overrides or {}
    _materializer_reject_unused_step_selection_overrides(raw_steps, selection_overrides)
    steps = []
    for index, raw_step in enumerate(raw_steps):
        step_template_ref = _clean_text(
            f"chain preset steps[{index}].step_template_ref",
            raw_step.get("step_template_ref", ""),
        )
        steps.append(
            _materializer_preset_step_with_selection_override(
                raw_step,
                step_template_ref,
                selection_overrides,
            )
        )
    # E1 FULL-LEGO (opt-in): a preset MAY DECLARE an explicit graph_topology
    # (fan_out/fan_in groups + an explicit terminal). When it does, the
    # materializer emits EXACTLY those declared groups+edges (multi-fan-in
    # Y-shapes the positional inference below cannot express). The key is
    # OPTIONAL: a preset WITHOUT graph_topology.fan_in_groups falls through to
    # the UNCHANGED positional path, so every existing preset materializes
    # byte-identically. Support never infers a route the preset did not declare.
    declared_topology = _materializer_declared_graph_topology(preset)
    if declared_topology is not None:
        return _materializer_declared_graph_declaration(
            steps,
            preset,
            registry,
            topology=declared_topology,
            repo=repo,
            building_id=building_id,
            task_summary=task_summary,
            task_source_ref=task_source_ref,
            source_facts=source_facts,
            write_scope=write_scope,
            override_reroute_budgets=override_reroute_budgets,
            override_closure_policy=override_closure_policy,
            chain_preset_ref=chain_preset_ref,
        )
    fan_out_index = _materializer_graph_fan_out_index(steps)
    if fan_out_index is None:
        return _materializer_sequential_graph_declaration(
            steps,
            preset,
            registry,
            repo=repo,
            building_id=building_id,
            task_summary=task_summary,
            task_source_ref=task_source_ref,
            source_facts=source_facts,
            write_scope=write_scope,
            override_reroute_budgets=override_reroute_budgets,
            chain_preset_ref=chain_preset_ref,
        )
    if len(steps) < fan_out_index + 3:
        raise ValueError("graph preset materialization requires fan-out branches and closure")
    # The closing synthesizer is the TERMINAL step by POSITION (last index). The name
    # "closure" here is descriptive only: this index is the fan-in TARGET / closed
    # boundary purely because it is last, NOT because its Brick kind is "closure". Any
    # Brick kind can be the terminal fan-in synthesizer; the boundary, fan_in_target
    # flag, and closure policy below all gate on this POSITION (== closure_index), with
    # no brick-KIND check anywhere on the graph path.
    closure_index = len(steps) - 1
    branch_indices = tuple(range(fan_out_index + 1, closure_index))
    if not branch_indices:
        raise ValueError("graph preset materialization requires at least one fan-in branch")

    # A + B are DECLARED by a HUMAN (the graph preset frontmatter = a reusable
    # HUMAN-authored default, OR a per-Building OVERRIDE in the intent), not
    # synthesized by support. The closure routing policy and the per-node reroute
    # budgets must be present in the preset OR the per-Building override; the
    # materializer only COPIES them through (fail-closed when neither supplies a
    # required value), honoring this module's own author-only comment below and
    # compose_building's closure_transition_target_policy_missing rejection.
    # Support must not default or invent these route fields.
    #
    # CONFIG CASCADE (mechanism-vs-policy, Smith-ruled): a per-Building OVERRIDE
    # beats the preset default; provenance is stamped per value so an auditor can
    # confirm support never injected it:
    #   * reroute budget: per-KEY merge. A node whose step_template_ref appears in
    #     the override map takes the override value (provenance "per-building");
    #     else the preset value (provenance "preset-default"). Support synthesizes
    #     neither.
    #   * closure policy: WHOLE-policy replacement (the policy is a single mapping
    #     on the closure node; a per-concern_kind merge would be ambiguous). When
    #     the intent supplies a closure policy it REPLACES the preset's entirely
    #     (provenance "per-building"); else the preset's (provenance
    #     "preset-default"). Support synthesizes neither.
    building_slug = _composition_slug(building_id)
    # Per-KEY cascade: override wins per key; provenance recorded per key. The
    # constitutional default tier opens only when the preset carries no budget map
    # of its own, preserving already-budgeted graph presets byte-for-byte.
    declared_budgets, budget_provenance, default_budget = (
        _materializer_reroute_budget_cascade(
            preset,
            repo=repo,
            override_reroute_budgets=override_reroute_budgets,
        )
    )

    # Whole-policy cascade: override replaces preset entirely.
    if override_closure_policy is not None:
        declared_closure_policy = _materializer_closure_policy(
            override_closure_policy,
            building_slug=building_slug,
        )
        closure_policy_provenance = "per-building"
    else:
        declared_closure_policy = _materializer_preset_closure_policy(
            preset,
            building_slug=building_slug,
        )
        closure_policy_provenance = "preset-default"

    nodes: list[Mapping[str, Any]] = []
    node_ids: list[str] = []
    node_id_sources: dict[str, list[str]] = {}
    step_template_sources: dict[str, list[tuple[str, bool]]] = {}
    edge_refs: list[str] = []
    step_template_counts = Counter(
        _clean_text(
            f"chain preset steps[{index}].step_template_ref",
            raw_step.get("step_template_ref", ""),
        )
        for index, raw_step in enumerate(steps)
    )
    for index, raw_step in enumerate(steps):
        step_template_ref = _clean_text(
            f"chain preset steps[{index}].step_template_ref",
            raw_step.get("step_template_ref", ""),
        )
        step_template = _materializer_step_template(registry, step_template_ref)
        _validate_declared_brick_spec_ref(raw_step, step_template, label=f"chain preset steps[{index}]")
        step_alias = _materializer_step_alias(raw_step, index)
        kind_slug = (
            _composition_slug(step_alias)
            if step_alias is not None
            else _materializer_step_template_slug(step_template_ref)
        )
        node_id = f"{building_slug}-{kind_slug}"
        source_label = f"steps[{index}] {step_template_ref}"
        if step_alias is not None:
            source_label = f"{source_label} step_alias={step_alias}"
        node_id_sources.setdefault(node_id, []).append(source_label)
        step_template_sources.setdefault(step_template_ref, []).append(
            (source_label, step_alias is not None)
        )
        node_ids.append(node_id)
        node_budget = declared_budgets.get(step_template_ref)
        node_budget_provenance = budget_provenance.get(step_template_ref)
        if node_budget is None and default_budget is not None:
            node_budget = default_budget
            node_budget_provenance = ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT
        node = _materializer_graph_node(
            index,
            raw_step,
            step_template,
            step_template_ref=step_template_ref,
            node_id=node_id,
            task_summary=task_summary,
            task_source_ref=task_source_ref,
            source_facts=source_facts,
            write_scope=write_scope,
            fan_in_source=index in branch_indices,
            fan_in_target=index == closure_index,
            declared_reroute_budget=node_budget,
            declared_reroute_budget_provenance=node_budget_provenance,
            declared_closure_policy=(
                declared_closure_policy if index == closure_index else None
            ),
            declared_closure_policy_provenance=(
                closure_policy_provenance if index == closure_index else None
            ),
        )
        nodes.append(node)

    alias_problems: list[str] = []
    for step_template_ref, sources in sorted(step_template_sources.items()):
        if step_template_counts[step_template_ref] <= 1:
            continue
        missing_alias_sources = [
            source_label for source_label, has_alias in sources if not has_alias
        ]
        if missing_alias_sources:
            alias_problems.append(
                f"step_alias required for repeated step_template_ref {step_template_ref}: "
                + ", ".join(missing_alias_sources)
            )
    for node_id, sources in sorted(node_id_sources.items()):
        if len(sources) > 1:
            alias_problems.append(
                f"node_id collision {node_id}: " + ", ".join(sources)
            )
    if alias_problems:
        raise ValueError(
            "chain preset step_alias node identity collision: "
            + "; ".join(alias_problems)
        )

    edges: list[Mapping[str, Any]] = []
    completion_edge_by_node: dict[str, str] = {}
    for source_index in range(0, fan_out_index):
        edge = _materializer_graph_edge(
            node_ids[source_index],
            node_ids[source_index + 1],
            preset=preset,
            registry=registry,
            source_step=steps[source_index],
            target_step=steps[source_index + 1],
            chain_preset_ref=chain_preset_ref,
        )
        edge_refs.append(str(edge["edge_ref"]))
        edges.append(edge)
        completion_edge_by_node[node_ids[source_index]] = str(edge["edge_ref"])
    fan_out_edges: list[str] = []
    fan_in_edges: list[str] = []
    for branch_index in branch_indices:
        out_edge = _materializer_graph_edge(
            node_ids[fan_out_index],
            node_ids[branch_index],
            preset=preset,
            registry=registry,
            source_step=steps[fan_out_index],
            target_step=steps[branch_index],
            chain_preset_ref=chain_preset_ref,
        )
        fan_out_edges.append(str(out_edge["edge_ref"]))
        edges.append(out_edge)
        completion_edge_by_node.setdefault(node_ids[fan_out_index], str(out_edge["edge_ref"]))
    for branch_index in branch_indices:
        in_edge = _materializer_graph_edge(
            node_ids[branch_index],
            node_ids[closure_index],
            preset=preset,
            registry=registry,
            source_step=steps[branch_index],
            target_step=steps[closure_index],
            chain_preset_ref=chain_preset_ref,
        )
        fan_in_edges.append(str(in_edge["edge_ref"]))
        edges.append(in_edge)
        completion_edge_by_node[node_ids[branch_index]] = str(in_edge["edge_ref"])
    terminal_edge: dict[str, Any] = {
        "edge_ref": f"edge:{node_ids[closure_index]}-to-boundary",
        "source": node_ids[closure_index],
        "target": f"building-boundary:{_composition_slug(building_id)}-closed",
        "movement": "forward",
        "building_lifecycle": {
            "state": "closed",
            "reason": f"declared closure boundary for {building_id}",
        },
    }
    # GATE-CONCEPT TRANSLATION (see GATE_CONCEPT_TOKEN_GATE_REFS): coo-review /
    # human-review tokens land on the FINAL transition row only -- the terminal
    # boundary edge (target = closure building boundary). A human-review token
    # also carries the canonical declared hold policy so the EXISTING
    # gate-sequence hold path withholds the closing Movement until the human
    # disposition fact exists. No profile tokens -> the edge is byte-identical
    # to the previous shape (support invents no gate).
    terminal_profile_gate_translations = _materializer_profile_gate_translations(
        _materializer_gate_concept_tokens(preset),
        qa_row=False,
        final_transition_row=True,
    )
    terminal_profile_gate_refs = tuple(
        ref for _token, ref in terminal_profile_gate_translations
    )
    if terminal_profile_gate_refs:
        terminal_edge["declared_gate_refs"] = [
            DEFAULT_LINK_GATE_REF,
            *terminal_profile_gate_refs,
        ]
        # A1 PROVENANCE AS DATA (codex review, 0610): record WHICH declared
        # tokens landed on the terminal boundary edge and WHICH preset declared
        # them -- ONLY when translation happened (no-profile edges stay
        # byte-identical and carry no provenance).
        terminal_edge["gate_concept_provenance"] = _materializer_gate_concept_provenance(
            terminal_profile_gate_translations,
            chain_preset_ref=chain_preset_ref,
        )
        if translate_gate_concept("human-review") in terminal_profile_gate_refs:
            terminal_edge["gate_sequence_policy"] = _materializer_human_gate_hold_policy()
    edges.append(terminal_edge)
    completion_edge_by_node[node_ids[closure_index]] = str(terminal_edge["edge_ref"])
    for node in nodes:
        if isinstance(node, dict):
            edge_ref = completion_edge_by_node.get(str(node.get("node_id", "")))
            if edge_ref:
                node["completion_edge_ref"] = edge_ref
    groups = [
        {
            "group_id": f"group:{_composition_slug(building_id)}-fan-out",
            "group_role": "fan_out",
            "member_ref_kind": "link_edge",
            "member_refs": fan_out_edges,
        },
        {
            "group_id": f"group:{_composition_slug(building_id)}-fan-in",
            "group_role": "fan_in",
            "member_ref_kind": "link_edge",
            "member_refs": fan_in_edges,
        },
    ]
    return {"nodes": nodes, "edges": edges, "groups": groups}


def _materializer_declared_graph_topology(
    preset: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Read the OPT-IN ``graph_topology`` declaration off a chain preset.

    Returns ``None`` when the preset does not declare a ``graph_topology`` with
    at least one ``fan_in_groups`` entry (the BACKWARD-COMPAT guarantee: absent
    -> the caller falls through to the unchanged positional path). When present,
    returns the raw mapping; shape validation is the emit function's job.

    A ``graph_topology`` that is present but malformed (not a mapping, or with no
    declared ``fan_in_groups``) is a fail-closed authoring error -- it is NOT a
    silent fall-through, because the author signalled the intent to declare an
    explicit topology.
    """

    if "graph_topology" not in preset:
        return None
    raw = preset.get("graph_topology")
    if not isinstance(raw, Mapping):
        raise ValueError(
            "chain preset graph_topology must be a mapping of declared "
            "fan_out_groups / fan_in_groups / terminal"
        )
    fan_in_groups = raw.get("fan_in_groups")
    if (
        not isinstance(fan_in_groups, Sequence)
        or isinstance(fan_in_groups, (str, bytes))
        or not fan_in_groups
    ):
        raise ValueError(
            "chain preset graph_topology must declare at least one fan_in group "
            "in fan_in_groups"
        )
    return raw


def _materializer_topology_node_handle(raw_step: Mapping[str, Any], index: int) -> str:
    """The canonical per-step handle a graph_topology declaration references.

    DECISION 2 (pinned): node identity in the declaration is ``step_alias`` (the
    canonical per-step handle). When a step declares no alias, the
    step_template_ref is the handle (only unambiguous when that template appears
    once -- the duplicate-handle guard below rejects an ambiguous reference).
    """
    step_alias = _materializer_step_alias(raw_step, index)
    if step_alias is not None:
        return step_alias
    return _clean_text(
        f"chain preset steps[{index}].step_template_ref",
        raw_step.get("step_template_ref", ""),
    )


def _materializer_topology_string_list(raw: Any, *, label: str) -> list[str]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError(f"{label} must be a list of declared node handles")
    out: list[str] = []
    for item in raw:
        handle = str(item).strip()
        if not handle:
            raise ValueError(f"{label} entries must be non-empty node handles")
        out.append(handle)
    return out


def _materializer_declared_graph_declaration(
    steps: Sequence[Mapping[str, Any]],
    preset: Mapping[str, Any],
    registry: Mapping[str, Any],
    *,
    topology: Mapping[str, Any],
    repo: Path,
    building_id: str,
    task_summary: str,
    task_source_ref: str,
    source_facts: Sequence[str],
    write_scope: Mapping[str, Any] | None,
    override_reroute_budgets: Any = None,
    override_closure_policy: Any = None,
    chain_preset_ref: str = "",
) -> Mapping[str, list[Mapping[str, Any]]]:
    """Emit EXACTLY the preset-DECLARED graph_topology (E1 full-lego).

    The preset author declares the graph structure explicitly instead of letting
    the positional inference guess it. The declaration carries:

      * ``edges``: forward node-to-node Link edges (by step handle); the DAG body.
      * ``fan_out_groups``: each ``{source, targets[]}`` -- the branch point(s).
      * ``fan_in_groups``: each ``{target, sources[], [closure_transition_target_policy]}``
        -- one convergence point per group (MULTIPLE distinct targets = the
        Y-shape the positional path cannot express).
      * ``terminal``: the single declared closure node that carries the closing
        building-boundary edge.

    The emitted nodes/edges/groups are the SAME shape compose_building's
    ``_composition_fan_in_target_steps`` / ``_composition_hard_graph_contract_problems``
    validators accept (each fan-in TARGET carries the Link-facing
    transition_concern_evidence closure shape + a closure policy; each fan-in
    SOURCE carries its Brick shape MINUS that field). Support emits only what the
    author declared and infers no extra route.
    """

    from brick_protocol.support.operator.composition import (
        _validate_declared_brick_spec_ref,
    )

    building_slug = _composition_slug(building_id)

    # Resolve every declared node handle -> step index. The handle is step_alias
    # (DECISION 2), else the (unique) step_template_ref. A duplicate handle is an
    # ambiguous reference and fails closed (parity with the positional path's
    # step_alias node-identity collision guard).
    handle_to_index: dict[str, int] = {}
    duplicate_handles: list[str] = []
    for index, raw_step in enumerate(steps):
        handle = _materializer_topology_node_handle(raw_step, index)
        if handle in handle_to_index:
            duplicate_handles.append(handle)
        handle_to_index[handle] = index
    if duplicate_handles:
        raise ValueError(
            "graph_topology node handles must be unique; declare step_alias for "
            "repeated step_template_ref(s): " + ", ".join(sorted(set(duplicate_handles)))
        )

    def _resolve(handle: str, *, where: str) -> int:
        key = str(handle).strip()
        if key not in handle_to_index:
            raise ValueError(
                f"graph_topology {where} references unknown node handle {key!r}; "
                "declare it as a step (step_alias or step_template_ref)"
            )
        return handle_to_index[key]

    # --- declared fan_in groups (one convergence point each) ---
    raw_fan_in_groups = topology.get("fan_in_groups")
    fan_in_groups: list[dict[str, Any]] = []
    fan_in_source_indices: set[int] = set()
    fan_in_target_indices: set[int] = set()
    # per fan-in TARGET index -> declared closure policy (raw, pre-resolution)
    target_closure_policy_raw: dict[int, Any] = {}
    for group_index, raw_group in enumerate(raw_fan_in_groups):
        if not isinstance(raw_group, Mapping):
            raise ValueError("graph_topology.fan_in_groups entries must be mappings")
        # The convergence node handle key is converge_on (NOT the Link-owned bare
        # key 'target', which the Brick-template axis-owned-field scan forbids).
        target_handle = str(raw_group.get("converge_on", "")).strip()
        if not target_handle:
            raise ValueError(
                "graph_topology.fan_in_groups entry must declare a converge_on node"
            )
        target_index = _resolve(target_handle, where=f"fan_in_groups[{group_index}].converge_on")
        source_handles = _materializer_topology_string_list(
            raw_group.get("sources"),
            label=f"graph_topology.fan_in_groups[{group_index}].sources",
        )
        source_indices = [
            _resolve(handle, where=f"fan_in_groups[{group_index}].sources")
            for handle in source_handles
        ]
        if target_index in source_indices:
            raise ValueError(
                f"graph_topology.fan_in_groups[{group_index}] target is also a source "
                "(self-loop)"
            )
        fan_in_target_indices.add(target_index)
        fan_in_source_indices.update(source_indices)
        if "closure_transition_target_policy" in raw_group:
            target_closure_policy_raw[target_index] = raw_group.get(
                "closure_transition_target_policy"
            )
        fan_in_groups.append(
            {"target_index": target_index, "source_indices": source_indices}
        )

    # --- declared terminal (the single closing node) ---
    terminal_handle = str(topology.get("terminal", "")).strip()
    if not terminal_handle:
        raise ValueError(
            "graph_topology must declare an explicit terminal node (the closing "
            "building-boundary owner)"
        )
    terminal_index = _resolve(terminal_handle, where="terminal")
    if terminal_index not in fan_in_target_indices:
        raise ValueError(
            "graph_topology terminal must be a declared fan_in target (the closing "
            "convergence node)"
        )

    # --- declared internal edges (forward DAG body) ---
    raw_edges = topology.get("edges")
    if not isinstance(raw_edges, Sequence) or isinstance(raw_edges, (str, bytes)) or not raw_edges:
        raise ValueError("graph_topology must declare a non-empty edges list")
    declared_edges: list[tuple[int, int]] = []
    seen_edges: set[tuple[int, int]] = set()
    for edge_index, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, Mapping):
            raise ValueError("graph_topology.edges entries must be mappings")
        # Endpoint keys are from/to (NOT the Link-owned bare 'target' key).
        src = _resolve(str(raw_edge.get("from", "")).strip(), where=f"edges[{edge_index}].from")
        tgt = _resolve(str(raw_edge.get("to", "")).strip(), where=f"edges[{edge_index}].to")
        if src == tgt:
            raise ValueError(f"graph_topology.edges[{edge_index}] is a self-loop")
        if (src, tgt) in seen_edges:
            raise ValueError(f"graph_topology.edges[{edge_index}] duplicates an edge")
        seen_edges.add((src, tgt))
        declared_edges.append((src, tgt))

    # Every declared fan_in (source -> target) must be carried by a declared edge
    # (the group names the convergence; the edge is the Link the group members
    # reference). Support does not invent the edge.
    for group in fan_in_groups:
        for source_index in group["source_indices"]:
            if (source_index, group["target_index"]) not in seen_edges:
                raise ValueError(
                    "graph_topology fan_in_groups source->target must be a declared "
                    f"edge: {steps[source_index].get('step_template_ref')} -> "
                    f"{steps[group['target_index']].get('step_template_ref')}"
                )

    # --- route-policy cascade (mechanism-vs-policy parity with the positional path) ---
    declared_budgets, budget_provenance, default_budget = (
        _materializer_reroute_budget_cascade(
            preset,
            repo=repo,
            override_reroute_budgets=override_reroute_budgets,
        )
    )

    # Per fan-in TARGET closure policy + provenance. A per-Building override
    # (whole-policy replacement) beats the declared default for EVERY fan-in
    # target; else each target uses its in-group policy, falling back to the
    # preset-level closure_transition_target_policy. Support synthesizes neither
    # (the node builder fails closed when a fan-in target has no policy).
    resolved_target_policy: dict[int, Mapping[str, Any] | None] = {}
    resolved_target_policy_provenance: dict[int, str] = {}
    preset_level_policy = _materializer_preset_closure_policy(
        preset, building_slug=building_slug
    )
    for target_index in sorted(fan_in_target_indices):
        if override_closure_policy is not None:
            resolved_target_policy[target_index] = _materializer_closure_policy(
                override_closure_policy, building_slug=building_slug
            )
            resolved_target_policy_provenance[target_index] = "per-building"
        elif target_index in target_closure_policy_raw:
            resolved_target_policy[target_index] = _materializer_closure_policy(
                target_closure_policy_raw[target_index], building_slug=building_slug
            )
            resolved_target_policy_provenance[target_index] = "preset-default"
        else:
            resolved_target_policy[target_index] = preset_level_policy
            resolved_target_policy_provenance[target_index] = "preset-default"

    # --- emit nodes (mirror the positional _materializer_graph_node shape) ---
    nodes: list[Mapping[str, Any]] = []
    node_ids: list[str] = []
    for index, raw_step in enumerate(steps):
        step_template_ref = _clean_text(
            f"chain preset steps[{index}].step_template_ref",
            raw_step.get("step_template_ref", ""),
        )
        step_template = _materializer_step_template(registry, step_template_ref)
        _validate_declared_brick_spec_ref(
            raw_step, step_template, label=f"chain preset steps[{index}]"
        )
        step_alias = _materializer_step_alias(raw_step, index)
        kind_slug = (
            _composition_slug(step_alias)
            if step_alias is not None
            else _materializer_step_template_slug(step_template_ref)
        )
        node_id = f"{building_slug}-{kind_slug}"
        node_ids.append(node_id)
        node_budget = declared_budgets.get(step_template_ref)
        node_budget_provenance = budget_provenance.get(step_template_ref)
        if node_budget is None and default_budget is not None:
            node_budget = default_budget
            node_budget_provenance = ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT
        is_fan_in_target = index in fan_in_target_indices
        node = _materializer_graph_node(
            index,
            raw_step,
            step_template,
            step_template_ref=step_template_ref,
            node_id=node_id,
            task_summary=task_summary,
            task_source_ref=task_source_ref,
            source_facts=source_facts,
            write_scope=write_scope,
            fan_in_source=index in fan_in_source_indices,
            fan_in_target=is_fan_in_target,
            declared_reroute_budget=node_budget,
            declared_reroute_budget_provenance=node_budget_provenance,
            declared_closure_policy=(
                resolved_target_policy.get(index) if is_fan_in_target else None
            ),
            declared_closure_policy_provenance=(
                resolved_target_policy_provenance.get(index)
                if is_fan_in_target
                else None
            ),
        )
        nodes.append(node)

    # node_id collision guard (a declared alias may still slug-collide with
    # another step; parity with the positional path's collision rejection).
    seen_node_ids: dict[str, int] = {}
    for index, node_id in enumerate(node_ids):
        if node_id in seen_node_ids:
            raise ValueError(
                f"graph_topology node_id collision {node_id}: steps[{seen_node_ids[node_id]}] "
                f"and steps[{index}]; declare distinct step_alias values"
            )
        seen_node_ids[node_id] = index

    # --- emit edges (declared internal edges, then the terminal boundary edge) ---
    edges: list[Mapping[str, Any]] = []
    completion_edge_by_node: dict[str, str] = {}
    edge_ref_by_pair: dict[tuple[int, int], str] = {}
    for source_index, target_index in declared_edges:
        edge = _materializer_graph_edge(
            node_ids[source_index],
            node_ids[target_index],
            preset=preset,
            registry=registry,
            source_step=steps[source_index],
            target_step=steps[target_index],
            chain_preset_ref=chain_preset_ref,
        )
        edges.append(edge)
        edge_ref_by_pair[(source_index, target_index)] = str(edge["edge_ref"])
        # A fan-out source's completion edge must be explicit (support must not
        # pick the first outgoing edge). The declared fan_in source->target edge
        # is each branch's completion edge; the single-out body nodes record
        # their one outgoing edge. The terminal records the boundary edge below.
        completion_edge_by_node.setdefault(node_ids[source_index], str(edge["edge_ref"]))

    # fan-in SOURCE completion edge = its edge INTO the fan-in target (the branch
    # closes by converging), overriding any earlier body-edge default.
    for group in fan_in_groups:
        for source_index in group["source_indices"]:
            completion_edge_by_node[node_ids[source_index]] = edge_ref_by_pair[
                (source_index, group["target_index"])
            ]

    terminal_edge: dict[str, Any] = {
        "edge_ref": f"edge:{node_ids[terminal_index]}-to-boundary",
        "source": node_ids[terminal_index],
        "target": f"building-boundary:{building_slug}-closed",
        "movement": "forward",
        "building_lifecycle": {
            "state": "closed",
            "reason": f"declared closure boundary for {building_id}",
        },
    }
    terminal_profile_gate_translations = _materializer_profile_gate_translations(
        _materializer_gate_concept_tokens(preset),
        qa_row=False,
        final_transition_row=True,
    )
    terminal_profile_gate_refs = tuple(
        ref for _token, ref in terminal_profile_gate_translations
    )
    if terminal_profile_gate_refs:
        terminal_edge["declared_gate_refs"] = [
            DEFAULT_LINK_GATE_REF,
            *terminal_profile_gate_refs,
        ]
        terminal_edge["gate_concept_provenance"] = _materializer_gate_concept_provenance(
            terminal_profile_gate_translations,
            chain_preset_ref=chain_preset_ref,
        )
        if translate_gate_concept("human-review") in terminal_profile_gate_refs:
            terminal_edge["gate_sequence_policy"] = _materializer_human_gate_hold_policy()
    edges.append(terminal_edge)
    completion_edge_by_node[node_ids[terminal_index]] = str(terminal_edge["edge_ref"])

    for node in nodes:
        if isinstance(node, dict):
            edge_ref = completion_edge_by_node.get(str(node.get("node_id", "")))
            if edge_ref:
                node["completion_edge_ref"] = edge_ref

    # --- emit groups (one fan_out + one fan_in group PER declared group) ---
    groups: list[Mapping[str, Any]] = []
    raw_fan_out_groups = topology.get("fan_out_groups", [])
    if not isinstance(raw_fan_out_groups, Sequence) or isinstance(
        raw_fan_out_groups, (str, bytes)
    ):
        raise ValueError("graph_topology.fan_out_groups must be a list when declared")
    for group_index, raw_group in enumerate(raw_fan_out_groups):
        if not isinstance(raw_group, Mapping):
            raise ValueError("graph_topology.fan_out_groups entries must be mappings")
        source_index = _resolve(
            str(raw_group.get("from", "")).strip(),
            where=f"fan_out_groups[{group_index}].from",
        )
        target_handles = _materializer_topology_string_list(
            raw_group.get("branches"),
            label=f"graph_topology.fan_out_groups[{group_index}].branches",
        )
        member_refs: list[str] = []
        for handle in target_handles:
            tgt = _resolve(handle, where=f"fan_out_groups[{group_index}].targets")
            pair = (source_index, tgt)
            if pair not in edge_ref_by_pair:
                raise ValueError(
                    "graph_topology fan_out_groups member must be a declared edge: "
                    f"{steps[source_index].get('step_template_ref')} -> "
                    f"{steps[tgt].get('step_template_ref')}"
                )
            member_refs.append(edge_ref_by_pair[pair])
        groups.append(
            {
                "group_id": f"group:{building_slug}-fan-out-{group_index + 1}",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": member_refs,
            }
        )
    for group_index, group in enumerate(fan_in_groups):
        target_index = group["target_index"]
        member_refs = [
            edge_ref_by_pair[(source_index, target_index)]
            for source_index in group["source_indices"]
        ]
        groups.append(
            {
                "group_id": f"group:{building_slug}-fan-in-{group_index + 1}",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": member_refs,
            }
        )

    return {"nodes": nodes, "edges": edges, "groups": groups}


def _materializer_sequential_graph_declaration(
    steps: Sequence[Mapping[str, Any]],
    preset: Mapping[str, Any],
    registry: Mapping[str, Any],
    *,
    repo: Path,
    building_id: str,
    task_summary: str,
    task_source_ref: str,
    source_facts: Sequence[str],
    write_scope: Mapping[str, Any] | None,
    override_reroute_budgets: Any = None,
    chain_preset_ref: str = "",
) -> Mapping[str, list[Mapping[str, Any]]]:
    from brick_protocol.support.operator.composition import (
        _validate_declared_brick_spec_ref,
    )

    if not steps:
        raise ValueError("graph preset materialization requires at least one step")

    building_slug = _composition_slug(building_id)
    declared_budgets, budget_provenance, default_budget = (
        _materializer_reroute_budget_cascade(
            preset,
            repo=repo,
            override_reroute_budgets=override_reroute_budgets,
        )
    )
    nodes: list[Mapping[str, Any]] = []
    node_ids: list[str] = []
    node_id_sources: dict[str, list[str]] = {}
    step_template_sources: dict[str, list[tuple[str, bool]]] = {}
    step_template_counts = Counter(
        _clean_text(
            f"chain preset steps[{index}].step_template_ref",
            raw_step.get("step_template_ref", ""),
        )
        for index, raw_step in enumerate(steps)
    )
    for index, raw_step in enumerate(steps):
        step_template_ref = _clean_text(
            f"chain preset steps[{index}].step_template_ref",
            raw_step.get("step_template_ref", ""),
        )
        step_template = _materializer_step_template(registry, step_template_ref)
        _validate_declared_brick_spec_ref(raw_step, step_template, label=f"chain preset steps[{index}]")
        step_alias = _materializer_step_alias(raw_step, index)
        kind_slug = (
            _composition_slug(step_alias)
            if step_alias is not None
            else _materializer_step_template_slug(step_template_ref)
        )
        node_id = f"{building_slug}-{kind_slug}"
        source_label = f"steps[{index}] {step_template_ref}"
        if step_alias is not None:
            source_label = f"{source_label} step_alias={step_alias}"
        node_id_sources.setdefault(node_id, []).append(source_label)
        step_template_sources.setdefault(step_template_ref, []).append(
            (source_label, step_alias is not None)
        )
        node_ids.append(node_id)
        node_budget = declared_budgets.get(step_template_ref)
        node_budget_provenance = budget_provenance.get(step_template_ref)
        if node_budget is None and default_budget is not None:
            node_budget = default_budget
            node_budget_provenance = ROUTE_POLICY_PROVENANCE_CONSTITUTIONAL_DEFAULT
        nodes.append(
            _materializer_graph_node(
                index,
                raw_step,
                step_template,
                step_template_ref=step_template_ref,
                node_id=node_id,
                task_summary=task_summary,
                task_source_ref=task_source_ref,
                source_facts=source_facts,
                write_scope=write_scope,
                fan_in_source=False,
                fan_in_target=False,
                declared_reroute_budget=node_budget,
                declared_reroute_budget_provenance=node_budget_provenance,
                declared_closure_policy=None,
                declared_closure_policy_provenance=None,
            )
        )

    alias_problems: list[str] = []
    for step_template_ref, sources in sorted(step_template_sources.items()):
        if step_template_counts[step_template_ref] <= 1:
            continue
        missing_alias_sources = [
            source_label for source_label, has_alias in sources if not has_alias
        ]
        if missing_alias_sources:
            alias_problems.append(
                f"step_alias required for repeated step_template_ref {step_template_ref}: "
                + ", ".join(missing_alias_sources)
            )
    for node_id, sources in sorted(node_id_sources.items()):
        if len(sources) > 1:
            alias_problems.append(
                f"node_id collision {node_id}: " + ", ".join(sources)
            )
    if alias_problems:
        raise ValueError(
            "chain preset step_alias node identity collision: "
            + "; ".join(alias_problems)
        )

    edges: list[Mapping[str, Any]] = []
    completion_edge_by_node: dict[str, str] = {}
    for source_index in range(0, len(steps) - 1):
        edge = _materializer_graph_edge(
            node_ids[source_index],
            node_ids[source_index + 1],
            preset=preset,
            registry=registry,
            source_step=steps[source_index],
            target_step=steps[source_index + 1],
            chain_preset_ref=chain_preset_ref,
        )
        edges.append(edge)
        completion_edge_by_node[node_ids[source_index]] = str(edge["edge_ref"])
    terminal_index = len(steps) - 1
    terminal_edge: dict[str, Any] = {
        "edge_ref": f"edge:{node_ids[terminal_index]}-to-boundary",
        "source": node_ids[terminal_index],
        "target": f"building-boundary:{_composition_slug(building_id)}-closed",
        "movement": "forward",
        "building_lifecycle": {
            "state": "closed",
            "reason": f"declared closure boundary for {building_id}",
        },
    }
    terminal_profile_gate_translations = _materializer_profile_gate_translations(
        _materializer_gate_concept_tokens(preset),
        qa_row=False,
        final_transition_row=True,
    )
    terminal_profile_gate_refs = tuple(
        ref for _token, ref in terminal_profile_gate_translations
    )
    if terminal_profile_gate_refs:
        terminal_edge["declared_gate_refs"] = [
            DEFAULT_LINK_GATE_REF,
            *terminal_profile_gate_refs,
        ]
        terminal_edge["gate_concept_provenance"] = _materializer_gate_concept_provenance(
            terminal_profile_gate_translations,
            chain_preset_ref=chain_preset_ref,
        )
        if translate_gate_concept("human-review") in terminal_profile_gate_refs:
            terminal_edge["gate_sequence_policy"] = _materializer_human_gate_hold_policy()
    edges.append(terminal_edge)
    completion_edge_by_node[node_ids[terminal_index]] = str(terminal_edge["edge_ref"])
    for node in nodes:
        if isinstance(node, dict):
            edge_ref = completion_edge_by_node.get(str(node.get("node_id", "")))
            if edge_ref:
                node["completion_edge_ref"] = edge_ref
    return {"nodes": nodes, "edges": edges, "groups": []}


def _materializer_graph_fan_out_index(steps: Sequence[Mapping[str, Any]]) -> int | None:
    for index, raw_step in enumerate(steps):
        target_word = str(raw_step.get("target_word", "")).strip().lower()
        if "parallel" in target_word:
            return index
    return None


def _materializer_graph_node(
    index: int,
    raw_preset_step: Mapping[str, Any],
    step_template: Mapping[str, Any],
    *,
    step_template_ref: str,
    node_id: str,
    task_summary: str,
    task_source_ref: str,
    source_facts: Sequence[str],
    write_scope: Mapping[str, Any] | None,
    fan_in_source: bool,
    fan_in_target: bool,
    declared_reroute_budget: int | None,
    declared_reroute_budget_provenance: str | None = None,
    declared_closure_policy: Mapping[str, Any] | None,
    declared_closure_policy_provenance: str | None = None,
) -> Mapping[str, Any]:
    brick_word = _clean_text(f"{step_template_ref}.brick_word", step_template.get("brick_word", ""))
    node: dict[str, Any] = {
        "node_id": node_id,
        "step_template_ref": step_template_ref,
        "work_statement": f"{brick_word} Brick for {task_source_ref}: {task_summary}",
        "comparison_rule": (
            "Observe declared task source, preset, and Brick contract only; "
            "do not choose Movement or judge success/quality."
        ),
        "source_facts": list(source_facts),
    }
    required_shape = _materializer_graph_required_return_shape(
        step_template_ref,
        step_template,
        fan_in_source=fan_in_source,
    )
    if required_shape:
        node["required_return_shape"] = required_shape
    if bool(step_template.get("write_need")):
        if write_scope is None:
            raise ValueError(f"write_scope is required for write-needed Brick {step_template_ref}")
        node["write_scope"] = dict(write_scope)
        # NO SILENT WRITE GRANT (graph parity with the linear materializer): the
        # node that receives a write_scope also records its write NEED EXPLICITLY
        # (requires_brick_write_scope: true); _composition_brick_row carries it
        # onto the declared plan Brick row for the strict run-admission gate.
        node["requires_brick_write_scope"] = True
    # A read-only Brick (no write_need) NEVER carries a write_scope on its node,
    # even when a building-level write_scope is supplied for the write-needed
    # step(s): the building write_scope flows past read-only steps un-stamped, so
    # the run-time provider projection of a read-only step opens no write.
    # B: per-node reroute budget is COPIED from a HUMAN-declared budget map (preset
    # default OR per-Building override), never defaulted by support. Its PROVENANCE
    # (constitutional-default | preset-default | per-building) is stamped alongside
    # the value so an auditor
    # can confirm support did not inject it. Provenance must NEVER be "support" and
    # must NEVER be absent when a value is present (fail closed below).
    if declared_reroute_budget is not None:
        if declared_reroute_budget_provenance not in _ROUTE_POLICY_PROVENANCE_VALUES:
            raise ValueError(
                "node_reroute_budget requires HUMAN provenance "
                "(constitutional-default | preset-default | per-building); "
                "support must not synthesize it"
            )
        node["node_reroute_budget"] = declared_reroute_budget
        node["node_reroute_budget_provenance"] = declared_reroute_budget_provenance
    # Copy EVERY present casting dial from the preset step onto the node generically
    # (E2/S6★): loop the single-source NODE_CASTING_FIELDS rather than naming
    # adapter/model, so a NEW dial (effort) carries through with no edit. A None value
    # is skipped (defer to plan-level), byte-identical to the prior two-field copy.
    for _casting_key in NODE_CASTING_FIELDS:
        if raw_preset_step.get(_casting_key) is not None:
            node[_casting_key] = raw_preset_step.get(_casting_key)
    # A: the fan-in closure routing policy is COPIED from a HUMAN-declared
    # closure_transition_target_policy (preset default OR per-Building override). It
    # MUST be declared by one of them (fail closed in the cascade reader); support
    # synthesizes nothing. Its PROVENANCE is stamped alongside the policy for the
    # same audit reason.
    if fan_in_target:
        if declared_closure_policy is None:
            raise ValueError(
                "graph preset or per-Building override must declare "
                "closure_transition_target_policy for the fan-in closure node; "
                "support must not synthesize the route author's policy"
            )
        if declared_closure_policy_provenance not in _ROUTE_POLICY_PROVENANCE_VALUES:
            raise ValueError(
                "closure_transition_target_policy requires HUMAN provenance "
                "(constitutional-default | preset-default | per-building); "
                "support must not synthesize it"
            )
        node["closure_transition_target_policy"] = dict(declared_closure_policy)
        node["closure_transition_target_policy_provenance"] = declared_closure_policy_provenance
    return node


def _materializer_graph_required_return_shape(
    step_template_ref: str,
    step_template: Mapping[str, Any],
    *,
    fan_in_source: bool,
) -> str:
    # Phase 1 RESOLVED the fan-in TARGET fork: the closure (fan_in_target) shape is
    # no longer synthesized here. The closure Brick return.yaml now DECLARES
    # transition_concern_evidence in its primary required_return_shape, so the
    # closure node derives its shape from the brick return.yaml via the registry
    # default (exactly like the linear path) -- support no longer hardcodes it.
    #
    # Phase 2 RESOLVED the fan-in SOURCE shape (position-driven transform of the
    # Brick's OWN declared shape -- support invents nothing):
    #   The fan-in SOURCE (code-attack-qa / axis-attack-qa / evidence-integrity)
    #   Brick return.yaml DECLARES its real fields (attacked_work / attacked_scope /
    #   ...) INCLUDING transition_concern_evidence, which it legitimately carries in
    #   its LINEAR positions. A fan-in SOURCE position forbids the Link-facing
    #   transition_concern_evidence (qa_transition_concern_shape: closure-synthesis
    #   is the single Link-facing concern source). So the source shape here is the
    #   Brick's OWN registry-derived required_return_shape (the same comma-joined
    #   field list the linear path defaults from) MINUS transition_concern_evidence.
    #   We no longer emit the support-invented `concern_observations` literal (it was
    #   not a Brick-declared field anywhere) and we no longer DISCARD the source
    #   Brick's real declared fields. The fan-in TARGET (closure) is the one that
    #   synthesizes the Link-facing transition_concern_evidence.
    if fan_in_source:
        return _materializer_strip_field(
            _composition_optional_text(step_template.get("required_return_shape")) or "",
            "transition_concern_evidence",
        )
    if step_template_ref == "building-step-template:work":
        return "made_changes, observed_evidence, not_proven"
    return ""


def _materializer_graph_edge(
    source_node_id: str,
    target_node_id: str,
    *,
    preset: Mapping[str, Any],
    registry: Mapping[str, Any],
    source_step: Mapping[str, Any],
    target_step: Mapping[str, Any],
    chain_preset_ref: str = "",
) -> Mapping[str, Any]:
    edge_ref = f"edge:{source_node_id}-to-{target_node_id}"
    edge: dict[str, Any] = {
        "edge_ref": edge_ref,
        "source": source_node_id,
        "target": target_node_id,
        "movement": "forward",
    }
    gate_refs = list(
        _materializer_gate_sequence_refs_for_edge(
            preset,
            source_step_template_ref=str(source_step.get("step_template_ref", "")).strip(),
            target_step_template_ref=str(target_step.get("step_template_ref", "")).strip(),
        )
    )
    # GATE-CONCEPT TRANSLATION (see GATE_CONCEPT_TOKEN_GATE_REFS): a declared
    # strict-evidence token lands link-gate:strict on every QA-row transition --
    # an edge whose SOURCE step template declares the reviewer lane NEED. The
    # final-transition (coo/human) placement is the terminal boundary edge,
    # handled in _materializer_graph_declaration. No profile -> no extra refs.
    source_template = _materializer_step_template(
        registry,
        str(source_step.get("step_template_ref", "")).strip(),
    )
    profile_gate_translations = _materializer_profile_gate_translations(
        _materializer_gate_concept_tokens(preset),
        qa_row=str(source_template.get("role_need", "")).strip() == _QA_ROLE_NEED,
        final_transition_row=False,
    )
    for _token, extra_ref in profile_gate_translations:
        if extra_ref not in gate_refs:
            gate_refs.append(extra_ref)
    if profile_gate_translations:
        # A1 PROVENANCE AS DATA (codex review, 0610): record WHICH declared
        # tokens landed on this edge and WHICH preset declared them -- ONLY
        # when translation happened (other edges carry no provenance).
        edge["gate_concept_provenance"] = _materializer_gate_concept_provenance(
            profile_gate_translations,
            chain_preset_ref=chain_preset_ref,
        )
    if gate_refs:
        edge["declared_gate_refs"] = [DEFAULT_LINK_GATE_REF, *gate_refs]
    return edge


def _materializer_gate_sequence_refs_for_edge(
    preset: Mapping[str, Any],
    *,
    source_step_template_ref: str,
    target_step_template_ref: str,
) -> tuple[str, ...]:
    from brick_protocol.support.operator.composition import (
        _composition_gate_sequence_profile_steps,
    )

    raw_profile = preset.get("gate_sequence_policy", ())
    if not isinstance(raw_profile, Sequence) or isinstance(raw_profile, (str, bytes)):
        return ()
    refs: list[str] = []
    for raw_item in raw_profile:
        if not isinstance(raw_item, Mapping):
            continue
        if str(raw_item.get("source_step_template_ref", "")).strip() != source_step_template_ref:
            continue
        if str(raw_item.get("target_step_template_ref", "")).strip() != target_step_template_ref:
            continue
        for raw_step in _composition_gate_sequence_profile_steps(raw_item):
            gate_ref = str(raw_step.get("declared_link_gate", raw_step.get("gate_ref", ""))).strip()
            if gate_ref and gate_ref != DEFAULT_LINK_GATE_REF and gate_ref not in refs:
                refs.append(gate_ref)
    return tuple(refs)

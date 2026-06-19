"""Behavioral profile case runners.

Lifted verbatim from check_profile.py (P3a behavior-preserving decomposition).
Each run_*_case / run_*_rejects exercises a real support surface (adapter model
selection, route materialization, transition-concern disposition, compose-
building, declared step-template plans, auto-repair replay, child-building
candidates, cascade sweep, BAR-v2 dogfood, fail-fixture rejects) as support
evidence only. They decide nothing and author no axis crossing.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import io
import json
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    json_path_exists,
    load_yaml_subset_file,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)

from support.checkers.lib.rule_runners import (
    _admitted_agent_object_refs,
    validate_building_plan_boundary,
    validate_route_policy_boundary,
)


def run_adapter_model_selection_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "adapter_model_selection_case")
    if not items:
        return 0
    from brick_protocol.support.connection.agent_adapter import project_model_ref_to_cli_arg

    count = 0
    for item in items:
        mapping = require_mapping(item, "adapter_model_selection_case item")
        adapter_ref = require_string(mapping.get("adapter_ref"), "adapter_model_selection_case.adapter_ref")
        selected_model_ref = require_string(
            mapping.get("selected_model_ref", "model:default"),
            "adapter_model_selection_case.selected_model_ref",
        )
        expected_raw = mapping.get("expected_cli_arg", "")
        if not isinstance(expected_raw, str):
            raise ProfileError("adapter_model_selection_case.expected_cli_arg must be a string")
        expected_cli_arg = expected_raw
        observed_cli_arg = project_model_ref_to_cli_arg(adapter_ref, selected_model_ref)
        if observed_cli_arg != expected_cli_arg:
            raise ProfileError(
                "adapter_model_selection_case rejected "
                f"{adapter_ref}/{selected_model_ref}: expected {expected_cli_arg!r}, "
                f"observed {observed_cli_arg!r}"
            )
        count += 1
    return count


def run_adapter_model_selection_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "adapter_model_selection_rejects")
    if not items:
        return 0
    from brick_protocol.support.connection.agent_adapter import project_model_ref_to_cli_arg

    count = 0
    for item in items:
        mapping = require_mapping(item, "adapter_model_selection_rejects item")
        adapter_ref = require_string(mapping.get("adapter_ref"), "adapter_model_selection_rejects.adapter_ref")
        selected_model_ref = require_string(
            mapping.get("selected_model_ref", ""),
            "adapter_model_selection_rejects.selected_model_ref",
        )
        try:
            project_model_ref_to_cli_arg(adapter_ref, selected_model_ref)
        except (TypeError, ValueError):
            count += 1
            continue
        raise ProfileError(
            "adapter_model_selection_rejects expected rejection but passed: "
            f"{adapter_ref}/{selected_model_ref}"
        )
    return count


def run_route_materialization_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "route_materialization_case")
    if not items:
        return 0
    from support.operator.route_materialization import materialize_route_transition
    count = 0
    for item in items:
        mapping = require_mapping(item, "route_materialization_case item")
        case, relative = _profile_case_document(repo, mapping, "route_materialization_case")
        policy = load_yaml_subset_file(
            repo,
            require_string(case.get("route_policy_path"), f"{relative}: route_policy_path"),
        )
        result = materialize_route_transition(
            require_mapping(case.get("route_request"), f"{relative}: route_request"),
            policy,
            require_mapping(case.get("declared_route_replay_plan"), f"{relative}: declared_route_replay_plan"),
        )
        expected = require_mapping(case.get("expected"), f"{relative}: expected")
        for key in ("match_state", "route_path_ref", "movement", "target_ref"):
            if key in expected and result.get(key) != expected.get(key):
                raise ProfileError(
                    f"route_materialization_case rejected {relative}: "
                    f"{key} expected {expected.get(key)!r}, observed {result.get(key)!r}"
                )
        expected_replay_refs = expected.get("replay_segment_refs")
        if expected_replay_refs is not None:
            replay_refs = result.get("link_row", {}).get("route_replay_plan", {}).get("replay_segment_refs")
            if replay_refs != require_string_list(expected_replay_refs, f"{relative}: expected.replay_segment_refs"):
                raise ProfileError(
                    f"route_materialization_case rejected {relative}: replay_segment_refs mismatch"
                )
        count += 1
    return count


def run_transition_concern_disposition_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "transition_concern_disposition_case")
    if not items:
        return 0
    from support.operator.route_materialization import materialize_transition_concern_disposition
    count = 0
    for item in items:
        mapping = require_mapping(item, "transition_concern_disposition_case item")
        case, relative = _profile_case_document(repo, mapping, "transition_concern_disposition_case")
        policy = load_yaml_subset_file(
            repo,
            require_string(case.get("route_policy_path"), f"{relative}: route_policy_path"),
        )
        result = materialize_transition_concern_disposition(
            require_mapping(case.get("transition_concern"), f"{relative}: transition_concern"),
            policy,
            require_mapping(case.get("declared_route_replay_plan"), f"{relative}: declared_route_replay_plan"),
        )
        expected = require_mapping(mapping.get("expected", {}), "transition_concern_disposition_case.expected")
        for key in (
            "match_state",
            "movement",
            "target_ref",
            "source_transition_concern_ref",
            "materialized",
            "materialization_state",
            "materialization_reason",
        ):
            if key in expected and result.get(key) != expected.get(key):
                raise ProfileError(
                    f"transition_concern_disposition_case rejected {relative}: "
                    f"{key} expected {expected[key]!r}, observed {result.get(key)!r}"
                )
        expected_replay_refs = expected.get("replay_segment_refs")
        if expected_replay_refs is not None:
            replay_refs = result.get("link_row", {}).get("route_replay_plan", {}).get("replay_segment_refs")
            if replay_refs != require_string_list(expected_replay_refs, "expected.replay_segment_refs"):
                raise ProfileError(
                    f"transition_concern_disposition_case rejected {relative}: replay_segment_refs mismatch"
                )
        for absent_key in require_string_list(
            expected.get("absent_keys", []),
            "expected.absent_keys",
        ):
            if result.get(absent_key) is not None:
                raise ProfileError(
                    f"transition_concern_disposition_case rejected {relative}: "
                    f"{absent_key} must be absent"
                )
        count += 1
    return count


def run_materialize_building_intent_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "materialize_building_intent_case")
    if not items:
        return 0
    from support.operator.building_operation import materialize_building_intent
    from support.operator.plan_graph import _linear_plan_from_graph_plan
    from support.operator.plan_validation import validate_declared_building_plan
    from support.operator.plan_validation import _task_source_ref_from_plan
    from support.recording.declaration_packets import _write_declaration_work_evidence

    count = 0
    for item in items:
        mapping = require_mapping(item, "materialize_building_intent_case item")
        case, relative = _profile_case_document(repo, mapping, "materialize_building_intent_case")
        strip_keys = _materialize_reject_strip_preset_keys(mapping)
        if strip_keys:
            strip_preset_ref = require_string(
                mapping.get("strip_preset_ref"),
                "materialize_building_intent_case.strip_preset_ref",
            )
            with _stripped_chain_preset_keys(
                materialize_building_intent, strip_preset_ref, strip_keys
            ) as strip_probe:
                plan = materialize_building_intent(case, repo_root=repo)
                if not strip_probe:
                    raise ProfileError(
                        "materialize_building_intent_case strip_preset_ref not in "
                        f"catalog: {strip_preset_ref} ({relative})"
                    )
        else:
            plan = materialize_building_intent(case, repo_root=repo)
        graph_context = None
        validation_plan = plan
        if plan.get("plan_shape") == "graph":
            validation_plan, graph_context = _linear_plan_from_graph_plan(plan)
        try:
            validate_declared_building_plan(validation_plan, repo_root=repo)
        except (TypeError, ValueError) as exc:
            raise ProfileError(f"materialize_building_intent_case rejected {relative}: {exc}") from exc
        expected = require_mapping(mapping.get("expected", {}), "materialize_building_intent_case.expected")
        if "plan_shape" in expected and plan.get("plan_shape") != expected.get("plan_shape"):
            raise ProfileError(
                f"materialize_building_intent_case rejected {relative}: "
                f"plan_shape expected {expected.get('plan_shape')!r}, observed {plan.get('plan_shape')!r}"
            )
        for key in (
            "building_id",
            "chain_preset_ref",
            "selected_adapter_ref",
            "task_source_ref",
        ):
            if key in expected and plan.get(key) != expected[key]:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"{key} expected {expected[key]!r}, observed {plan.get(key)!r}"
                )
        if "node_reroute_budgets" in expected:
            # Budgets are positive ints; the YAML-subset profile parser yields
            # scalars as strings, so normalize both sides to int for the compare
            # (a non-int/non-positive value on either side is a real mismatch).
            def _budget_int(value: Any, where: str) -> int:
                if isinstance(value, bool) or not (
                    isinstance(value, int)
                    or (isinstance(value, str) and value.strip().isdecimal())
                ):
                    raise ProfileError(
                        f"materialize_building_intent_case rejected {relative}: "
                        f"{where} budget must be a positive int, got {value!r}"
                    )
                return int(value)

            expected_budgets = {
                str(k): _budget_int(v, "expected node_reroute_budgets")
                for k, v in require_mapping(
                    expected.get("node_reroute_budgets"),
                    "materialize_building_intent_case.expected.node_reroute_budgets",
                ).items()
            }
            observed_budgets = {
                str(k): _budget_int(v, "observed node_reroute_budgets")
                for k, v in (plan.get("node_reroute_budgets") or {}).items()
            }
            if observed_budgets != expected_budgets:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"node_reroute_budgets expected {expected_budgets!r}, "
                    f"observed {observed_budgets!r}"
                )
        expected_steps = require_string_list(
            expected.get("step_refs", []),
            "materialize_building_intent_case.expected.step_refs",
        )
        if expected_steps:
            step_source = plan.get("steps")
            if plan.get("plan_shape") == "graph":
                step_source = plan.get("brick_steps")
            observed_steps = [
                str(step.get("step_ref"))
                for step in step_source or []
                if isinstance(step, Mapping)
            ]
            if observed_steps != expected_steps:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"step_refs expected {expected_steps!r}, observed {observed_steps!r}"
                )
        for expected_key, step_key in (
            ("selected_adapter_refs_by_step", "selected_adapter_ref"),
            ("selected_model_refs_by_step", "selected_model_ref"),
        ):
            expected_step_values = require_string_list(
                expected.get(expected_key, []),
                f"materialize_building_intent_case.expected.{expected_key}",
            )
            if not expected_step_values:
                continue
            observed_step_values = _materialized_step_values(plan, step_key)
            if observed_step_values != expected_step_values:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"{expected_key} expected {expected_step_values!r}, "
                    f"observed {observed_step_values!r}"
                )
        expected_targets = require_string_list(
            expected.get("target_refs", []),
            "materialize_building_intent_case.expected.target_refs",
        )
        if expected_targets:
            observed_targets = []
            if plan.get("plan_shape") == "graph":
                link_sources = plan.get("link_edges", [])
            else:
                link_sources = plan.get("steps", [])
            for item_value in link_sources or []:
                if not isinstance(item_value, Mapping):
                    continue
                for row in item_value.get("rows", []):
                    if isinstance(row, Mapping) and row.get("axis") == "Link":
                        observed_targets.append(str(row.get("target_ref")))
            if observed_targets != expected_targets:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"target_refs expected {expected_targets!r}, observed {observed_targets!r}"
                )
        expected_movements = require_string_list(
            expected.get("movements", []),
            "materialize_building_intent_case.expected.movements",
        )
        if expected_movements:
            observed_movements = _observed_link_row_values(plan, "movement")
            if observed_movements != expected_movements:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"movements expected {expected_movements!r}, observed {observed_movements!r}"
                )
        expected_gate_refs = expected.get("declared_gate_refs")
        if isinstance(expected_gate_refs, list):
            observed = [
                edge.get("rows", [{}])[0].get("declared_gate_refs")
                for edge in plan.get("link_edges", [])
                if isinstance(edge, Mapping)
                and isinstance(edge.get("rows", [{}])[0], Mapping)
            ]
            if expected_gate_refs not in observed:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: expected gate refs not observed"
                )
        expected_gate_sequence_policy_gate_refs = expected.get("gate_sequence_policy_gate_refs")
        if isinstance(expected_gate_sequence_policy_gate_refs, list):
            observed_sequences = [
                [
                    item.get("gate_ref")
                    for item in edge.get("rows", [{}])[0].get("gate_sequence_policy", [])
                    if isinstance(item, Mapping)
                ]
                for edge in plan.get("link_edges", [])
                if isinstance(edge, Mapping)
                and isinstance(edge.get("rows", [{}])[0], Mapping)
            ]
            if expected_gate_sequence_policy_gate_refs not in observed_sequences:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    "expected gate_sequence_policy gate refs not observed"
                )
        # GATE-WIRING FIRE (a)/(b) (0610): EXACT ordered per-row gate assertions
        # over EVERY Link row (linear steps order / graph link_edges order). One
        # entry per row, written as a comma-joined ref string ("" = none, the
        # profile yaml-subset parser has no nested lists). This asserts BOTH
        # which rows carry the translated gate refs / hold policy AND that every
        # other row does NOT (support invents no gate when the preset declares
        # no profile token for that row).
        expected_gate_refs_by_row = expected.get("declared_gate_refs_by_row")
        if isinstance(expected_gate_refs_by_row, list):
            expected_rows = [_split_ref_row(item) for item in expected_gate_refs_by_row]
            observed_by_row = _link_rows_list_field(plan, "declared_gate_refs")
            if observed_by_row != expected_rows:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"declared_gate_refs_by_row expected {expected_rows!r}, "
                    f"observed {observed_by_row!r}"
                )
        expected_policy_by_row = expected.get("gate_sequence_policy_gate_refs_by_row")
        if isinstance(expected_policy_by_row, list):
            expected_rows = [_split_ref_row(item) for item in expected_policy_by_row]
            observed_policy_by_row = [
                [
                    item.get("gate_ref")
                    for item in (row or [])
                    if isinstance(item, Mapping)
                ]
                for row in _link_rows_list_field(plan, "gate_sequence_policy")
            ]
            if observed_policy_by_row != expected_rows:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"gate_sequence_policy_gate_refs_by_row expected {expected_rows!r}, "
                    f"observed {observed_policy_by_row!r}"
                )
        # GATE-WIRING FIRE A1/A4 (0610): per-row gate_concept_provenance TOKEN
        # assertions (comma-joined token string per row; "" = the field must be
        # ABSENT on that row). PRESENCE pins that a stamped row records WHICH
        # declared tokens landed there; ABSENCE pins that support never invents
        # provenance on un-translated rows (e.g. every app-feature-basic row).
        # gate_concept_provenance_declared_by additionally pins WHO declared the
        # tokens (the chain preset ref) on EVERY provenance-carrying row.
        expected_provenance_by_row = expected.get("gate_concept_provenance_by_row")
        if isinstance(expected_provenance_by_row, list):
            expected_rows = [_split_ref_row(item) for item in expected_provenance_by_row]
            observed_provenance_rows = _link_rows_provenance_tokens(plan, relative)
            if observed_provenance_rows != expected_rows:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"gate_concept_provenance_by_row expected {expected_rows!r}, "
                    f"observed {observed_provenance_rows!r}"
                )
        expected_provenance_declared_by = expected.get(
            "gate_concept_provenance_declared_by"
        )
        if expected_provenance_declared_by is not None:
            expected_provenance_declared_by = require_string(
                expected_provenance_declared_by,
                f"{relative}: gate_concept_provenance_declared_by",
            )
            observed_declared_by = _link_rows_provenance_declared_by(plan, relative)
            if not observed_declared_by:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    "gate_concept_provenance_declared_by expected but NO Link row "
                    "carries gate_concept_provenance"
                )
            wrong = sorted(
                value for value in observed_declared_by
                if value != expected_provenance_declared_by
            )
            if wrong:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"gate_concept_provenance.declared_by expected "
                    f"{expected_provenance_declared_by!r} on every stamped row, "
                    f"observed {wrong!r}"
                )
        expected_group_roles = require_string_list(
            expected.get("group_roles", []),
            "materialize_building_intent_case.expected.group_roles",
        )
        if expected_group_roles:
            observed_group_roles = [
                str(group.get("group_role"))
                for group in plan.get("groups", [])
                if isinstance(group, Mapping)
            ]
            if observed_group_roles != expected_group_roles:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    f"group_roles expected {expected_group_roles!r}, observed {observed_group_roles!r}"
                )
        if expected.get("task_source_hash_present") and not plan.get("task_source_hash"):
            raise ProfileError(
                f"materialize_building_intent_case rejected {relative}: task_source_hash missing"
            )
        expected_evidence = require_mapping(
            expected.get("declaration_evidence", {}),
            "materialize_building_intent_case.expected.declaration_evidence",
        )
        if expected_evidence:
            with tempfile.TemporaryDirectory(prefix="bp-materialize-building-intent-") as tmpdir:
                _write_declaration_work_evidence(
                    Path(tmpdir),
                    building_id=str(plan.get("building_id") or ""),
                    plan_ref=str(plan.get("plan_ref") or ""),
                    plan=plan,
                    declaration_plan=plan,
                    graph_context=graph_context,
                    task_source_ref=_task_source_ref_from_plan(plan, repo_root=repo),
                    proof_limits=tuple(
                        item for item in plan.get("proof_limits", ()) if isinstance(item, str)
                    ),
                    not_proven=tuple(
                        item for item in plan.get("not_proven", ()) if isinstance(item, str)
                    ),
                )
                _check_materialize_building_declaration_evidence(
                    Path(tmpdir),
                    expected=expected_evidence,
                    label=relative,
                )
        if expected.get("assert_materialized_return_shapes"):
            _check_materialized_node_return_shapes(repo, plan, label=relative)
        if expected.get("assert_route_policy_provenance"):
            _check_materialized_route_policy_provenance(
                plan,
                expected_by_node=expected.get("route_policy_provenance"),
                label=relative,
            )
        count += 1
    return count


_ROUTE_POLICY_PROVENANCE_VALUES = (
    "constitutional-default",
    "preset-default",
    "per-building",
)


def _check_materialized_route_policy_provenance(
    plan: Mapping[str, Any],
    *,
    expected_by_node: Any,
    label: str,
) -> None:
    """Assert route-policy values carry HUMAN provenance, never support-synthesized.

    Mechanism-vs-policy guard (Smith-ruled): the reroute BUDGET and closure routing
    POLICY are Movement decisions a HUMAN sets (a reusable preset default OR a
    per-Building override); support must NEVER inject or default them. This guard
    fail-closes when:

      * A node carries ``node_reroute_budget`` or
        ``closure_transition_target_policy`` but its provenance is missing /
        support-synthesized / not in {constitutional-default, preset-default,
        per-building} -- i.e. support injected a value with no HUMAN provenance
        trail.
      * The recorded ``route_policy_provenance.by_node`` references a node that
        carries no such value, or omits a node that carries one (the provenance
        record and the carried values must agree exactly).

    When ``route_policy_provenance`` is supplied in ``expected``, the per-node
    provenance map is also asserted EXACTLY (used by the per-Building override case
    to prove the override value's provenance is ``per-building`` while the
    untouched ones stay ``preset-default``).
    """
    if plan.get("plan_shape") != "graph":
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            "assert_route_policy_provenance requires a graph plan"
        )
    provenance = plan.get("route_policy_provenance")
    if not isinstance(provenance, Mapping):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            "route_policy_provenance block is missing (support must record provenance "
            "for HUMAN-declared route policy)"
        )
    by_node = provenance.get("by_node")
    if not isinstance(by_node, Mapping):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            "route_policy_provenance.by_node is missing or not a mapping"
        )

    # Build the set of (node_id, field) pairs that actually CARRY a value, from the
    # materialized brick steps / plan budgets / link edges, independent of the
    # provenance record -- so the record cannot lie about coverage.
    carried: dict[str, set[str]] = {}
    budgets = plan.get("node_reroute_budgets")
    # node_reroute_budgets is keyed by brick_instance_ref (brick-<node_id>); the
    # provenance record is keyed by node_id, so map brick_ref -> node_id via steps.
    step_node_ids = [
        str(step.get("step_ref"))
        for step in plan.get("brick_steps") or []
        if isinstance(step, Mapping) and step.get("step_ref")
    ]
    if isinstance(budgets, Mapping):
        for brick_ref in budgets:
            node_id = str(brick_ref)
            if node_id.startswith("brick-"):
                node_id = node_id[len("brick-"):]
            if node_id not in step_node_ids:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {label}: "
                    f"node_reroute_budgets references unknown node {brick_ref!r}"
                )
            carried.setdefault(node_id, set()).add("node_reroute_budget")
    # The closure routing policy is consumed internally and not re-emitted onto
    # rows, so the provenance record is the only place it surfaces; cross-check it
    # against the fan-in TARGET (the only node that may carry a closure policy).
    fan_in_target_node_ids: set[str] = set()
    edges = {
        str(edge.get("edge_ref")): edge
        for edge in plan.get("link_edges") or []
        if isinstance(edge, Mapping)
    }
    for group in plan.get("groups") or []:
        if not isinstance(group, Mapping) or group.get("group_role") != "fan_in":
            continue
        for member_ref in group.get("member_refs") or []:
            edge = edges.get(str(member_ref))
            if isinstance(edge, Mapping):
                target = str(edge.get("target_step_ref") or "")
                if target:
                    fan_in_target_node_ids.add(target)

    # Validate every recorded entry: known node, value actually carried, provenance
    # in the allowed HUMAN set (never support / never absent).
    for node_id, entry in by_node.items():
        node_id = str(node_id)
        if not isinstance(entry, Mapping):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"route_policy_provenance.by_node[{node_id!r}] must be a mapping"
            )
        for field, prov in entry.items():
            if str(prov) not in _ROUTE_POLICY_PROVENANCE_VALUES:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {label}: node {node_id} "
                    f"{field} provenance {prov!r} is not HUMAN (expected one of "
                    f"{list(_ROUTE_POLICY_PROVENANCE_VALUES)!r}); support must not "
                    "synthesize route policy"
                )
            if str(field) == "node_reroute_budget":
                if "node_reroute_budget" not in carried.get(node_id, set()):
                    raise ProfileError(
                        f"materialize_building_intent_case rejected {label}: node "
                        f"{node_id} has node_reroute_budget provenance but no carried "
                        "budget value"
                    )
            elif str(field) == "closure_transition_target_policy":
                if node_id not in fan_in_target_node_ids:
                    raise ProfileError(
                        f"materialize_building_intent_case rejected {label}: node "
                        f"{node_id} has closure_transition_target_policy provenance but "
                        "is not a fan-in TARGET node"
                    )

    # Every carried reroute budget MUST have a provenance entry (no value may slip
    # through unprovenanced -- that would be a support injection with no trail).
    for node_id, fields in carried.items():
        recorded = by_node.get(node_id)
        recorded_fields = set(recorded) if isinstance(recorded, Mapping) else set()
        missing = fields - recorded_fields
        if missing:
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: node {node_id} "
                f"carries {sorted(missing)} with no provenance record (support must "
                "record provenance for every route-policy value)"
            )

    if expected_by_node is not None:
        expected_map = require_mapping(
            expected_by_node,
            "materialize_building_intent_case.expected.route_policy_provenance",
        )
        observed_map = {
            str(node_id): {str(k): str(v) for k, v in entry.items()}
            for node_id, entry in by_node.items()
            if isinstance(entry, Mapping)
        }
        normalized_expected = {
            str(node_id): {str(k): str(v) for k, v in require_mapping(
                entry, f"route_policy_provenance.{node_id}"
            ).items()}
            for node_id, entry in expected_map.items()
        }
        if observed_map != normalized_expected:
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"route_policy_provenance expected {normalized_expected!r}, "
                f"observed {observed_map!r}"
            )


def _materialized_return_shape_fields(value: Any) -> list[str]:
    """Split a comma-joined required_return_shape string into trimmed field tokens.

    Whitespace/separator tolerant (the materializer joins with ', ' but the
    declared field ORDER is preserved). Returns the field names in order.
    """
    text = str(value or "")
    return [token.strip() for token in text.split(",") if token.strip()]


def _brick_return_shape_fields(repo: Path, kind: str, label: str) -> list[str]:
    """Read the LIVE brick return.yaml required_return_shape list for a kind.

    Reads ``brick/templates/bricks/<kind>/return.yaml`` (the kind's PRIMARY
    return template — the exact file the Builder derives the default
    required_return_shape from) and returns its declared field list in order.
    Reading the live file (not a static copy) makes the guard track the source
    of truth: if the brick declared shape changes, the expectation changes with
    it.
    """
    relative = f"brick/templates/bricks/{kind}/return.yaml"
    doc = load_yaml_subset_file(repo, relative)
    raw = doc.get("required_return_shape")
    if not isinstance(raw, list):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: brick return template "
            f"{relative} has no required_return_shape list"
        )
    fields: list[str] = []
    for token in raw:
        text = str(token).strip()
        if text:
            fields.append(text)
    return fields


def _materialized_brick_row_shape(step: Mapping[str, Any]) -> str | None:
    """Return the Brick-axis row's required_return_shape text for a materialized step."""
    for row in step.get("rows") or []:
        if isinstance(row, Mapping) and row.get("axis") == "Brick":
            return row.get("required_return_shape")
    return None


def _check_materialized_node_return_shapes(
    repo: Path, plan: Mapping[str, Any], *, label: str
) -> None:
    """Assert the materialized node required_return_shape content (Phase 2.5 guard).

    Closes the false-green gap where the materializer could regress to a
    hardcoded / support-invented shape and stay GREEN. Three assertions, derived
    from the LIVE brick return.yaml + the plan's own fan-in group topology:

      1. NO materialized node's required_return_shape may contain the
         support-invented ``concern_observations`` (hard reject — the invention
         must never reappear).
      2. Each fan-in SOURCE node's required_return_shape MUST equal the source
         brick's declared required_return_shape MINUS transition_concern_evidence
         (proves it is brick-derived, not hardcoded).
      3. The fan-in TARGET (closure) node's required_return_shape MUST contain
         transition_concern_evidence.
    """
    if plan.get("plan_shape") != "graph":
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            "assert_materialized_return_shapes requires a graph plan"
        )
    steps = {
        str(step.get("step_ref")): step
        for step in plan.get("brick_steps") or []
        if isinstance(step, Mapping)
    }

    def _kind_for(step: Mapping[str, Any]) -> str:
        template_ref = str(step.get("step_template_ref") or "")
        return template_ref.split(":", 1)[1] if ":" in template_ref else template_ref

    # (1) concern_observations must never reappear on ANY node.
    for step_ref, step in steps.items():
        fields = _materialized_return_shape_fields(_materialized_brick_row_shape(step))
        if any(field.lower() == "concern_observations" for field in fields):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: node {step_ref} "
                "required_return_shape contains the support-invented "
                "'concern_observations' (the invention must never reappear)"
            )

    # Derive fan-in SOURCE / TARGET steps from the plan's OWN fan-in group + edges.
    edges = {
        str(edge.get("edge_ref")): edge
        for edge in plan.get("link_edges") or []
        if isinstance(edge, Mapping)
    }
    fan_in_groups = [
        group
        for group in plan.get("groups") or []
        if isinstance(group, Mapping) and group.get("group_role") == "fan_in"
    ]
    if not fan_in_groups:
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            "assert_materialized_return_shapes found no fan_in group to verify"
        )
    source_step_refs: list[str] = []
    target_step_refs: set[str] = set()
    for group in fan_in_groups:
        for member_ref in group.get("member_refs") or []:
            edge = edges.get(str(member_ref))
            if not isinstance(edge, Mapping):
                raise ProfileError(
                    f"materialize_building_intent_case rejected {label}: fan_in member "
                    f"{member_ref!r} has no matching link edge"
                )
            source_ref = str(edge.get("source_step_ref") or "")
            target_ref = str(edge.get("target_step_ref") or "")
            if source_ref not in steps or target_ref not in steps:
                raise ProfileError(
                    f"materialize_building_intent_case rejected {label}: fan_in edge "
                    f"{member_ref!r} references unknown step(s)"
                )
            if source_ref not in source_step_refs:
                source_step_refs.append(source_ref)
            target_step_refs.add(target_ref)

    # (2) Each fan-in SOURCE shape == brick-declared shape MINUS transition_concern_evidence.
    for source_ref in source_step_refs:
        step = steps[source_ref]
        kind = _kind_for(step)
        observed = _materialized_return_shape_fields(_materialized_brick_row_shape(step))
        brick_fields = _brick_return_shape_fields(repo, kind, label)
        expected_fields = [
            field
            for field in brick_fields
            if field.lower() != "transition_concern_evidence"
        ]
        if observed != expected_fields:
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: fan-in SOURCE node "
                f"{source_ref} ({kind}) required_return_shape is not brick-derived; "
                f"expected brick-minus-transition_concern_evidence {expected_fields!r}, "
                f"observed {observed!r}"
            )

    # (3) The fan-in TARGET (closure) shape MUST carry transition_concern_evidence.
    for target_ref in sorted(target_step_refs):
        step = steps[target_ref]
        observed = _materialized_return_shape_fields(_materialized_brick_row_shape(step))
        if not any(field.lower() == "transition_concern_evidence" for field in observed):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: fan-in TARGET node "
                f"{target_ref} required_return_shape must contain "
                f"transition_concern_evidence; observed {observed!r}"
            )


def _materialize_reject_strip_preset_keys(mapping: Mapping[str, Any]) -> tuple[str, ...]:
    raw = mapping.get("strip_preset_keys")
    if raw is None:
        return ()
    return tuple(
        require_string_list(raw, "materialize_building_intent_rejects.strip_preset_keys")
    )


def _materialize_reject_patch_preset_steps(mapping: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw = mapping.get("patch_chain_preset_steps")
    if raw is None:
        return ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ProfileError(
            "materialize_building_intent_rejects.patch_chain_preset_steps must be a list"
        )
    steps: list[Mapping[str, Any]] = []
    for index, raw_step in enumerate(raw):
        steps.append(
            require_mapping(
                raw_step,
                f"materialize_building_intent_rejects.patch_chain_preset_steps[{index}]",
            )
        )
    if not steps:
        raise ProfileError(
            "materialize_building_intent_rejects.patch_chain_preset_steps must not be empty"
        )
    return tuple(steps)


@contextlib.contextmanager
def _stripped_chain_preset_keys(materialize_fn, preset_ref: str, keys):
    """Temporarily wrap the materializer's registry loader to drop preset keys.

    Patches ``_load_shape_registry`` in the GLOBALS of the actual
    ``materialize_building_intent`` function (so it works regardless of which
    package alias resolved the function) to return a registry where the named
    preset has the given keys removed. A COPY is stored; the on-disk catalog file
    is never mutated. Yields a probe truthy iff the preset_ref was found and
    stripped. The original loader symbol is always restored on exit. This is
    read-only checker scaffolding that exercises the materializer's fail-closed
    path; it authors nothing.
    """
    globals_ns = materialize_fn.__globals__
    if "_load_shape_registry" not in globals_ns:
        raise ProfileError(
            "materialize_building_intent_rejects strip scaffold cannot find "
            "_load_shape_registry in the materializer's module globals"
        )
    original_loader = globals_ns["_load_shape_registry"]
    found = False

    def _wrapped(repo_root):
        nonlocal found
        registry = dict(original_loader(repo_root))
        chain_presets = registry.get("chain_presets")
        if isinstance(chain_presets, Mapping) and preset_ref in chain_presets:
            preset = dict(chain_presets[preset_ref])
            for key in keys:
                preset.pop(key, None)
            patched = dict(chain_presets)
            patched[preset_ref] = preset
            registry["chain_presets"] = patched
            found = True
        return registry

    globals_ns["_load_shape_registry"] = _wrapped
    try:
        yield _StripProbe(lambda: found)
    finally:
        globals_ns["_load_shape_registry"] = original_loader


@contextlib.contextmanager
def _patched_chain_preset_steps(materialize_fn, preset_ref: str, steps: Sequence[Mapping[str, Any]]):
    """Temporarily replace one resolved chain preset's steps for a RED probe."""

    globals_ns = materialize_fn.__globals__
    if "_load_shape_registry" not in globals_ns:
        raise ProfileError(
            "materialize_building_intent_rejects patch scaffold cannot find "
            "_load_shape_registry in the materializer's module globals"
        )
    original_loader = globals_ns["_load_shape_registry"]
    found = False

    def _wrapped(repo_root):
        nonlocal found
        registry = dict(original_loader(repo_root))
        chain_presets = registry.get("chain_presets")
        if isinstance(chain_presets, Mapping) and preset_ref in chain_presets:
            preset = dict(chain_presets[preset_ref])
            preset["steps"] = [dict(step) for step in steps]
            patched = dict(chain_presets)
            patched[preset_ref] = preset
            registry["chain_presets"] = patched
            found = True
        return registry

    globals_ns["_load_shape_registry"] = _wrapped
    try:
        yield _StripProbe(lambda: found)
    finally:
        globals_ns["_load_shape_registry"] = original_loader


class _StripProbe:
    """Truthy iff the strip target preset_ref was found (evaluated lazily)."""

    def __init__(self, resolver) -> None:
        self._resolver = resolver

    def __bool__(self) -> bool:
        return bool(self._resolver())


def run_materialize_building_intent_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "materialize_building_intent_rejects")
    if not items:
        return 0
    from support.operator.building_operation import materialize_building_intent
    from support.operator.plan_validation import _task_source_ref_from_plan
    from support.recording.declaration_packets import _write_declaration_work_evidence

    count = 0
    for item in items:
        mapping = require_mapping(item, "materialize_building_intent_rejects item")
        case, relative = _profile_case_document(repo, mapping, "materialize_building_intent_rejects")
        expected_message = str(mapping.get("expected_message", "") or "")
        # Anti-false-green guard (Deliverable A/B): drop a DECLARED graph-preset
        # route field from the resolved preset, then assert the materializer fails
        # closed instead of synthesizing it. The strip is applied to a COPY of the
        # registry preset (real catalog file unchanged) by wrapping the loader the
        # materializer uses; the negative proves support never defaults the route
        # author's closure policy / reroute budgets.
        strip_keys = _materialize_reject_strip_preset_keys(mapping)
        patched_steps = _materialize_reject_patch_preset_steps(mapping)
        if patched_steps:
            patch_preset_ref = require_string(
                mapping.get("patch_chain_preset_ref"),
                "materialize_building_intent_rejects.patch_chain_preset_ref",
            )
            with _patched_chain_preset_steps(
                materialize_building_intent, patch_preset_ref, patched_steps
            ) as patch_probe:
                try:
                    materialize_building_intent(case, repo_root=repo)
                except (TypeError, ValueError) as exc:
                    if not patch_probe:
                        raise ProfileError(
                            "materialize_building_intent_rejects patch_chain_preset_ref "
                            f"not in catalog (rejection unrelated to patch): {patch_preset_ref} "
                            f"({relative})"
                        ) from exc
                    if expected_message and expected_message not in str(exc):
                        raise ProfileError(
                            f"materialize_building_intent_rejects rejected {relative}: "
                            f"expected message {expected_message!r}, observed {exc}"
                        ) from exc
                    count += 1
                    continue
                if not patch_probe:
                    raise ProfileError(
                        "materialize_building_intent_rejects patch_chain_preset_ref "
                        f"not in catalog: {patch_preset_ref} ({relative})"
                    )
                raise ProfileError(
                    "materialize_building_intent_rejects expected fail-closed with patched "
                    f"chain preset steps but passed: {relative}"
                )
        if strip_keys:
            strip_preset_ref = require_string(
                mapping.get("strip_preset_ref"),
                "materialize_building_intent_rejects.strip_preset_ref",
            )
            with _stripped_chain_preset_keys(
                materialize_building_intent, strip_preset_ref, strip_keys
            ) as strip_probe:
                try:
                    materialize_building_intent(case, repo_root=repo)
                except (TypeError, ValueError) as exc:
                    if not strip_probe:
                        raise ProfileError(
                            "materialize_building_intent_rejects strip_preset_ref not in "
                            f"catalog (rejection unrelated to strip): {strip_preset_ref} ({relative})"
                        ) from exc
                    if expected_message and expected_message not in str(exc):
                        raise ProfileError(
                            f"materialize_building_intent_rejects rejected {relative}: "
                            f"expected message {expected_message!r}, observed {exc}"
                        ) from exc
                    count += 1
                    continue
                if not strip_probe:
                    raise ProfileError(
                        "materialize_building_intent_rejects strip_preset_ref not in catalog: "
                        f"{strip_preset_ref} ({relative})"
                    )
                raise ProfileError(
                    "materialize_building_intent_rejects expected fail-closed when graph "
                    f"preset omits {sorted(strip_keys)} but passed: {relative}"
                )
        if mapping.get("mutate_materialized_task_source_hash"):
            try:
                plan = dict(materialize_building_intent(case, repo_root=repo))
                plan["task_source_hash"] = "sha256-mismatch-fixture"
                with tempfile.TemporaryDirectory(prefix="bp-materialize-building-intent-reject-") as tmpdir:
                    _write_declaration_work_evidence(
                        Path(tmpdir),
                        building_id=str(plan.get("building_id") or ""),
                        plan_ref=str(plan.get("plan_ref") or ""),
                        plan=plan,
                        declaration_plan=plan,
                        graph_context=None,
                        task_source_ref=_task_source_ref_from_plan(plan, repo_root=repo),
                        proof_limits=tuple(
                            item for item in plan.get("proof_limits", ()) if isinstance(item, str)
                        ),
                        not_proven=tuple(
                            item for item in plan.get("not_proven", ()) if isinstance(item, str)
                        ),
                    )
            except (TypeError, ValueError) as exc:
                if expected_message and expected_message not in str(exc):
                    raise ProfileError(
                        f"materialize_building_intent_rejects rejected {relative}: "
                        f"expected message {expected_message!r}, observed {exc}"
                    ) from exc
                count += 1
                continue
            raise ProfileError(
                f"materialize_building_intent_rejects expected hash rejection but passed: {relative}"
            )
        try:
            materialize_building_intent(case, repo_root=repo)
        except (TypeError, ValueError) as exc:
            if expected_message and expected_message not in str(exc):
                raise ProfileError(
                    f"materialize_building_intent_rejects rejected {relative}: "
                    f"expected message {expected_message!r}, observed {exc}"
                ) from exc
            count += 1
            continue
        raise ProfileError(
            f"materialize_building_intent_rejects expected rejection but passed: {relative}"
        )
    return count


def run_preset_building_completion_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "preset_building_completion_case")
    if not items:
        return 0
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from support.operator.building_operation import materialize_building_intent, observe_building_frontier
    from support.operator.composition import _load_shape_registry
    from support.operator.driver import run_declared_portfolio
    from support.operator.run import run_building_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "preset_building_completion_case item")
        label = require_string(mapping.get("label"), "preset_building_completion_case.label")
        task_source_ref = require_string(
            mapping.get("task_source_ref"),
            f"{label}: task_source_ref",
        )
        selected_adapter_ref = require_string(
            mapping.get("selected_adapter_ref", "adapter:codex-local"),
            f"{label}: selected_adapter_ref",
        )
        selected_model_ref = require_string(
            mapping.get("selected_model_ref", "model:default"),
            f"{label}: selected_model_ref",
        )
        write_scope = require_mapping(mapping.get("write_scope"), f"{label}: write_scope")
        route_decision_basis = require_mapping(
            mapping.get(
                "route_decision_basis",
                {"override_refs": [f"coo:{_case_slug(label)}"]},
            ),
            f"{label}: route_decision_basis",
        )
        expected_preset_refs = require_string_list(
            mapping.get("expected_preset_refs", []),
            f"{label}: expected_preset_refs",
        )
        expected_portfolio_refs = require_string_list(
            mapping.get("expected_portfolio_refs", []),
            f"{label}: expected_portfolio_refs",
        )
        expected_frontier = require_string(
            mapping.get("expected_frontier_kind", "complete"),
            f"{label}: expected_frontier_kind",
        )
        expected_portfolio_frontier = require_string(
            mapping.get("expected_portfolio_frontier_kind", "complete"),
            f"{label}: expected_portfolio_frontier_kind",
        )
        expected_count = _optional_positive_int(
            mapping.get("expected_preset_count"),
            f"{label}: expected_preset_count",
        )

        registry = _load_shape_registry(repo)
        preset_refs = _canonical_chain_preset_refs(registry)
        if expected_count is not None and len(preset_refs) != expected_count:
            raise ProfileError(
                f"preset_building_completion_case rejected {label}: "
                f"expected {expected_count} preset(s), observed {len(preset_refs)}"
            )
        if expected_preset_refs and tuple(expected_preset_refs) != preset_refs:
            raise ProfileError(
                f"preset_building_completion_case rejected {label}: preset ref set mismatch"
            )

        command_runner = _preset_completion_command_runner(LocalCliCompleted)
        materialized_refs: list[str] = []
        portfolio_refs: list[str] = []
        with tempfile.TemporaryDirectory(prefix="bp-preset-building-completion-") as tmpdir:
            tmp = Path(tmpdir)
            output_root = tmp / "buildings"
            for preset_ref in preset_refs:
                building_id = f"{_case_slug(label)}-{_preset_slug(preset_ref)}"
                intent = _preset_completion_intent(
                    label=label,
                    building_id=building_id,
                    task_source_ref=task_source_ref,
                    chain_preset_ref=preset_ref,
                    selected_adapter_ref=selected_adapter_ref,
                    selected_model_ref=selected_model_ref,
                    write_scope=write_scope,
                    route_decision_basis=route_decision_basis,
                )
                try:
                    plan = materialize_building_intent(intent, repo_root=repo)
                except (TypeError, ValueError) as exc:
                    if "target_word requires explicit portfolio/manual materialization" in str(exc):
                        portfolio_refs.append(preset_ref)
                        continue
                    raise ProfileError(
                        f"preset_building_completion_case rejected {label}/{preset_ref}: {exc}"
                    ) from exc
                walker_mode = "dynamic" if plan.get("plan_shape") == "graph" else "linear"
                result = run_building_plan(
                    plan,
                    output_root=output_root,
                    overwrite_existing=True,
                    command_runner=command_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
                frontier = observe_building_frontier(result.lifecycle_write.root, repo_root=repo)
                if frontier.get("frontier_kind") != expected_frontier:
                    raise ProfileError(
                        f"preset_building_completion_case rejected {label}/{preset_ref}: "
                        f"frontier_kind expected {expected_frontier!r}, "
                        f"observed {frontier.get('frontier_kind')!r}"
                    )
                _assert_no_missing_gate_facts(result.lifecycle_write.root, label=f"{label}/{preset_ref}")
                materialized_refs.append(preset_ref)

            if tuple(expected_portfolio_refs) != tuple(portfolio_refs):
                raise ProfileError(
                    f"preset_building_completion_case rejected {label}: "
                    f"portfolio refs expected {expected_portfolio_refs!r}, observed {portfolio_refs!r}"
                )
            for portfolio_ref in portfolio_refs:
                _run_preset_completion_portfolio(
                    label=label,
                    portfolio_ref=portfolio_ref,
                    task_source_ref=task_source_ref,
                    selected_adapter_ref=selected_adapter_ref,
                    selected_model_ref=selected_model_ref,
                    write_scope=write_scope,
                    route_decision_basis=route_decision_basis,
                    repo=repo,
                    tmp=tmp,
                    output_root=output_root,
                    command_runner=command_runner,
                    run_declared_portfolio=run_declared_portfolio,
                    materialize_building_intent=materialize_building_intent,
                    observe_building_frontier=observe_building_frontier,
                    expected_frontier=expected_portfolio_frontier,
                )
        if len(materialized_refs) + len(portfolio_refs) != len(preset_refs):
            raise ProfileError(f"preset_building_completion_case rejected {label}: coverage mismatch")
        count += 1
    return count


def _building_intake_seam_callable(request: Any) -> Mapping[str, Any]:
    """Deterministic adapter:local agent brain for the building-intake seam case.

    Returns every field the Brick's required_return_shape names so any read-only
    preset's bricks complete; carries no Movement, success, or quality judgment.
    """
    from brick_protocol.brick.work import parse_required_return_shape

    labels = parse_required_return_shape(request.required_return_shape)
    returned: dict[str, Any] = {}
    for label in labels:
        if label == "transition_concern_evidence":
            returned[label] = {
                "concern_ref": "transition-concern:building-intake-seam-no-reroute",
                "concern_kind": "unknown",
                "binding": False,
                "reason_refs": ["observation:building-intake-seam-no-reroute"],
                "related_boundary_refs": ["building-boundary:building-intake-seam-no-reroute"],
            }
        elif label in _PRESET_COMPLETION_LIST_RETURN_FIELDS:
            returned[label] = _deterministic_completion_list(label, "building-intake-seam")
        else:
            returned[label] = f"{label}: building-intake-seam deterministic evidence"
    returned.setdefault("observed_evidence", ["building-intake-seam deterministic evidence"])
    returned.setdefault("not_proven", ["building-intake-seam checker proof only"])
    return returned


def run_adapter_gate_shape_union_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """GATE-WIRING FIRE A3 (0610): the adapter ASK is the Brick+gate UNION.

    Pins the NEW correct behavior of run._adapter_required_return_shape over a
    REAL walk: a stored plan row whose Brick required_return_shape LACKS a
    default-gate-required field (the legacy under-ask, repro shape of
    brick/building_plans/fixture-link-route-replay-0.yaml)
    must still be ASKED for the gate-implied union through the adapter prompt.
    The observation is the OUTWARD surface (the CLI prompt's
    required_return_labels actually sent by the adapter), not the helper's own
    return value, so the old Brick-shape-only under-ask REDs this case
    (observed labels would lack the dropped field). The same item also pins the
    VERBATIM passthrough half on an untouched row (gates adding nothing -> the
    declared labels pass through unchanged), so over-asking everywhere cannot
    masquerade as the fix.
    """
    items = rule_items(profile, "adapter_gate_shape_union_case")
    if not items:
        return 0
    from brick_protocol.brick.work import parse_required_return_shape
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from support.operator.building_operation import (
        materialize_building_intent,
        observe_building_frontier,
    )
    from support.operator.run import run_building_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "adapter_gate_shape_union_case item")
        label = require_string(mapping.get("label"), "adapter_gate_shape_union_case.label")
        task_source_ref = require_string(
            mapping.get("task_source_ref"), f"{label}: task_source_ref"
        )
        chain_preset_ref = require_string(
            mapping.get("chain_preset_ref"), f"{label}: chain_preset_ref"
        )
        target_step_index = _optional_non_negative_int(
            mapping.get("target_step_index", 0), f"{label}: target_step_index"
        )
        drop_field = require_string(mapping.get("drop_field"), f"{label}: drop_field")
        expected_request_labels = [
            part.strip()
            for part in require_string(
                mapping.get("expected_request_labels"),
                f"{label}: expected_request_labels",
            ).split(",")
            if part.strip()
        ]
        passthrough_step_index = mapping.get("passthrough_step_index")
        if passthrough_step_index is not None:
            passthrough_step_index = _optional_non_negative_int(
                passthrough_step_index, f"{label}: passthrough_step_index"
            )

        # CLI adapter on purpose: the assertion surface is the OUTWARD CLI
        # prompt (required_return_labels actually sent), so the case must walk
        # a command-runner adapter, not the in-process adapter:local callable.
        selected_adapter_ref = require_string(
            mapping.get("selected_adapter_ref", "adapter:codex-local"),
            f"{label}: selected_adapter_ref",
        )
        building_id = f"{_case_slug(label)}-gate-shape-union"
        intent = {
            "plan_ref": f"building-plan:{building_id}",
            "building_id": building_id,
            "declared_by": "coo",
            "task_source_ref": task_source_ref,
            "chain_preset_ref": chain_preset_ref,
            "selected_adapter_ref": selected_adapter_ref,
            "selected_model_ref": "model:default",
            "not_proven": ["checker fixture task source only"],
        }
        plan = json.loads(json.dumps(materialize_building_intent(intent, repo_root=repo)))
        steps = plan.get("brick_steps") if plan.get("plan_shape") == "graph" else plan.get("steps")
        if not isinstance(steps, list) or target_step_index >= len(steps):
            raise ProfileError(
                f"adapter_gate_shape_union_case rejected {label}: "
                f"target_step_index {target_step_index} outside {len(steps or [])} step(s)"
            )
        brick_row = _gate_shape_union_brick_row(steps[target_step_index], label=label)
        original_fields = list(parse_required_return_shape(brick_row["required_return_shape"]))
        if drop_field not in original_fields:
            raise ProfileError(
                f"adapter_gate_shape_union_case rejected {label}: drop_field "
                f"{drop_field!r} not present in the materialized shape "
                f"{original_fields!r} (fixture must remove a REAL field)"
            )
        # Emulate the stored-legacy under-ask: the plan ROW declares a Brick
        # shape missing a default-gate-required field. Only this string changes;
        # everything else is the freshly materialized plan.
        brick_row["required_return_shape"] = ", ".join(
            field for field in original_fields if field != drop_field
        )

        captured_labels: list[tuple[str, ...]] = []
        base_runner = _preset_completion_command_runner(LocalCliCompleted)

        def _capturing_runner(args: Sequence[str], cwd: Path, timeout_seconds: int) -> Any:
            checked_args = tuple(str(arg) for arg in args)
            if "--version" not in checked_args:
                labels = _return_labels_from_cli_prompt(
                    checked_args[-1] if checked_args else ""
                )
                if labels:
                    captured_labels.append(labels)
            return base_runner(args, cwd, timeout_seconds)

        with tempfile.TemporaryDirectory(prefix="bp-adapter-gate-shape-union-") as tmpdir:
            result = run_building_plan(
                plan,
                output_root=Path(tmpdir) / "buildings",
                overwrite_existing=True,
                command_runner=_capturing_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
            )
            frontier = observe_building_frontier(result.lifecycle_write.root, repo_root=repo)
        if frontier.get("frontier_kind") != "complete":
            raise ProfileError(
                f"adapter_gate_shape_union_case rejected {label}: frontier_kind "
                f"expected 'complete', observed {frontier.get('frontier_kind')!r}"
            )
        if len(captured_labels) != len(steps):
            raise ProfileError(
                f"adapter_gate_shape_union_case rejected {label}: captured "
                f"{len(captured_labels)} adapter prompt(s) for {len(steps)} step(s)"
            )
        observed = list(captured_labels[target_step_index])
        if observed != expected_request_labels:
            raise ProfileError(
                f"adapter_gate_shape_union_case rejected {label}: adapter request "
                f"labels expected {expected_request_labels!r}, observed {observed!r}"
            )
        if drop_field not in observed:
            raise ProfileError(
                f"adapter_gate_shape_union_case rejected {label}: the adapter ask "
                f"must include the gate-implied field {drop_field!r} the Brick "
                f"shape under-asked (old under-ask behavior observed)"
            )
        if passthrough_step_index is not None:
            if passthrough_step_index >= len(steps):
                raise ProfileError(
                    f"adapter_gate_shape_union_case rejected {label}: "
                    f"passthrough_step_index {passthrough_step_index} outside plan"
                )
            passthrough_row = _gate_shape_union_brick_row(
                steps[passthrough_step_index], label=label
            )
            declared = list(parse_required_return_shape(passthrough_row["required_return_shape"]))
            observed_passthrough = list(captured_labels[passthrough_step_index])
            if observed_passthrough != declared:
                raise ProfileError(
                    f"adapter_gate_shape_union_case rejected {label}: untouched row "
                    f"must pass through VERBATIM; declared {declared!r}, adapter "
                    f"asked {observed_passthrough!r}"
                )
        count += 1
    return count


def _gate_shape_union_brick_row(step: Any, *, label: str) -> dict[str, Any]:
    if isinstance(step, Mapping):
        for row in step.get("rows", []):
            if isinstance(row, Mapping) and row.get("axis") == "Brick":
                if not isinstance(row.get("required_return_shape"), str):
                    break
                return row
    raise ProfileError(
        f"adapter_gate_shape_union_case rejected {label}: step has no Brick row "
        "with a text required_return_shape"
    )


def run_building_intake_seam_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """Exercise the PART-2 task.md+preset -> running-Building seam over adapter:local.

    For each declared item: drive run_building_intake (materialize -> write plan ->
    graph-only run dispatch) over an adapter:local deterministic callable and
    assert the seam (1) writes a graph plan file on disk, (2) records dynamic
    dispatch as the run default it expects, and (3) reaches the expected terminal
    frontier with Building evidence. Then assert a NO-PRESET intent HARD-FAILS
    (the seam must not run a Building) -- this is the FIRE: it must RED if the
    hard-fail is bypassed.
    """
    items = rule_items(profile, "building_intake_seam_case")
    if not items:
        return 0
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from support.operator.building_operation import observe_building_frontier
    from support.operator.driver import run_building_intake

    count = 0
    for item in items:
        mapping = require_mapping(item, "building_intake_seam_case item")
        label = require_string(mapping.get("label"), "building_intake_seam_case.label")
        # TASK-BY-TEXT (0611): a case declares EITHER task_source_ref (file
        # flow) OR task_statement (inline text flow) -- mirroring the driver's
        # own EITHER/OR contract.
        task_statement = mapping.get("task_statement")
        if task_statement is not None:
            task_statement = require_string(task_statement, f"{label}: task_statement")
            task_source_ref = ""
        else:
            task_source_ref = require_string(
                mapping.get("task_source_ref"), f"{label}: task_source_ref"
            )
        chain_preset_ref = require_string(
            mapping.get("chain_preset_ref"), f"{label}: chain_preset_ref"
        )
        selected_adapter_ref = require_string(
            mapping.get("selected_adapter_ref", "adapter:codex-local"),
            f"{label}: selected_adapter_ref",
        )
        # C4 (0615): a fixture that walks a write-needing preset (one whose QA
        # bricks now declare requires_brick_write_scope yes) MUST carry a
        # work-area write_scope and drive an observed-write adapter
        # (adapter:codex-local) through the EXISTING command_runner sentinel --
        # no real CLI launches. adapter:local (the in-process LOCAL-LLM stub) is
        # read-only and stays only on a NON-QA, no-write-need preset.
        write_scope = mapping.get("write_scope")
        if write_scope is not None:
            write_scope = require_mapping(write_scope, f"{label}: write_scope")
        expected_plan_shape = require_string(
            mapping.get("expected_plan_shape", "graph"), f"{label}: expected_plan_shape"
        )
        expected_walker_mode = require_string(
            mapping.get("expected_walker_mode", "dynamic"), f"{label}: expected_walker_mode"
        )
        expected_frontier = require_string(
            mapping.get("expected_frontier_kind", "complete"),
            f"{label}: expected_frontier_kind",
        )
        no_preset_chain_preset_ref = require_string(
            mapping.get("no_preset_chain_preset_ref"),
            f"{label}: no_preset_chain_preset_ref",
        )
        # GATE-WIRING FIRE knobs (0610): an OPTIONAL caller-declared
        # route_decision_basis (the human/COO disposition facts) carried onto the
        # intent, plus HOLD expectations for a review-gated walk. A hold case
        # asserts the REAL walker paused at the expected gate with the expected
        # required_disposition_owner and that the recorded missing fact IS the
        # expected disposition fact (not some unrelated insufficiency).
        route_decision_basis = mapping.get("route_decision_basis")
        if route_decision_basis is not None:
            route_decision_basis = require_mapping(
                route_decision_basis, f"{label}: route_decision_basis"
            )
        expected_disposition_owner = mapping.get("expected_required_disposition_owner")
        if expected_disposition_owner is not None:
            expected_disposition_owner = require_string(
                expected_disposition_owner,
                f"{label}: expected_required_disposition_owner",
            )
        expected_hold_gate_ref = mapping.get("expected_hold_gate_ref")
        if expected_hold_gate_ref is not None:
            expected_hold_gate_ref = require_string(
                expected_hold_gate_ref, f"{label}: expected_hold_gate_ref"
            )
        expected_missing_fact = mapping.get("expected_missing_required_fact")
        if expected_missing_fact is not None:
            expected_missing_fact = require_string(
                expected_missing_fact, f"{label}: expected_missing_required_fact"
            )

        building_id = f"{_case_slug(label)}-{_preset_slug(chain_preset_ref)}"
        intent = {
            "plan_ref": f"building-plan:{building_id}",
            "building_id": building_id,
            "declared_by": "coo",
            "chain_preset_ref": chain_preset_ref,
            "selected_adapter_ref": selected_adapter_ref,
            "selected_model_ref": "model:default",
            "report_event_policy": {"enabled": False},
            "proof_limits": [
                "building-intake seam checker support evidence only",
                "not provider behavior",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                f"semantic correctness of {label}",
                "real provider behavior",
            ],
        }
        if write_scope is not None:
            intent["write_scope"] = dict(write_scope)
        if route_decision_basis is not None:
            intent["route_decision_basis"] = dict(route_decision_basis)
        if task_statement is not None:
            intent["task_statement"] = task_statement
        else:
            intent["task_source_ref"] = task_source_ref
        # TASK-BY-TEXT no-repo-root-file FIRE (codex FIX-A, 0611): the inline
        # mechanism must NEVER create a repo-root task-statement file -- not
        # even transiently. The before/after snapshot alone is TAUTOLOGICAL
        # against the retired ephemeral-file mechanism (it deleted its file in
        # a finally), so the statement case ALSO probes DURING the run: the
        # seam callable asserts the repo-root glob is unchanged at every Agent
        # invocation, which REDs a regression back to any transient-file
        # mechanism while the walk is live.
        statement_residue_before = {
            path.name for path in repo.glob("task-statement-*.md")
        }

        def _assert_no_repo_root_statement_file(
            _label: str = label,
            _before: frozenset[str] = frozenset(statement_residue_before),
        ) -> None:
            # TASK-BY-TEXT no-repo-root-file FIRE (codex FIX-A, 0611): the inline
            # mechanism must NEVER create a repo-root task-statement file, not
            # even transiently. Probe the repo-root glob DURING the run so a
            # regression back to any transient-file mechanism REDs mid-walk.
            during = {
                path.name for path in repo.glob("task-statement-*.md")
            } - _before
            if during:
                raise ProfileError(
                    f"building_intake_seam_case rejected {_label}: repo-root "
                    f"task-statement file(s) existed DURING the inline run "
                    f"(the inline mechanism must write no file): {sorted(during)}"
                )

        # C4 (0615): drive the seam through the SAME adapter the fixture
        # declares. adapter:local stays the in-process local_callables path (a
        # NON-QA, no-write-need preset only). A write-needing QA preset declares
        # adapter:codex-local and is driven by the EXISTING preset-completion
        # command_runner sentinel -- a deterministic CLI-shaped return with NO
        # real CLI launch (the runner intercepts the argv).
        local_callables: dict[str, Any] | None = None
        command_runner = None
        if selected_adapter_ref == "adapter:local":
            seam_callable = _building_intake_seam_callable
            if task_statement is not None:
                def _no_repo_root_statement_file_callable(
                    request: Any,
                ) -> Mapping[str, Any]:
                    _assert_no_repo_root_statement_file()
                    return _building_intake_seam_callable(request)

                seam_callable = _no_repo_root_statement_file_callable
            local_callables = {"callable:local:agent-invoke0-smoke": seam_callable}
        else:
            base_runner = _preset_completion_command_runner(LocalCliCompleted)

            def _seam_command_runner(
                args: Sequence[str], cwd: Path, timeout_seconds: int
            ) -> Any:
                checked_args = tuple(str(arg) for arg in args)
                if task_statement is not None and "--version" not in checked_args:
                    _assert_no_repo_root_statement_file()
                return base_runner(args, cwd, timeout_seconds)

            command_runner = _seam_command_runner

        with tempfile.TemporaryDirectory(prefix="bp-building-intake-seam-") as tmpdir:
            output_root = Path(tmpdir) / "buildings"
            result = run_building_intake(
                intent,
                repo_root=repo,
                output_root=output_root,
                overwrite_existing=True,
                local_callables=local_callables,
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
            )
            if result.plan_shape != expected_plan_shape:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: plan_shape expected "
                    f"{expected_plan_shape!r}, observed {result.plan_shape!r}"
                )
            if result.walker_mode != expected_walker_mode:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: walker_mode expected "
                    f"{expected_walker_mode!r}, observed {result.walker_mode!r}"
                )
            if not result.plan_path.is_file():
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: "
                    f"materialized plan not written to disk: {result.plan_path}"
                )
            plan_on_disk = json.loads(result.plan_path.read_text(encoding="utf-8"))
            if plan_on_disk.get("plan_shape") != expected_plan_shape:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: "
                    "on-disk plan_shape mismatch with materialized plan"
                )
            frontier = observe_building_frontier(
                result.run_result.lifecycle_write.root, repo_root=repo
            )
            if frontier.get("frontier_kind") != expected_frontier:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: frontier_kind expected "
                    f"{expected_frontier!r}, observed {frontier.get('frontier_kind')!r}"
                )
            if not result.run_result.written_files:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: "
                    "Building run produced no evidence files"
                )
            lifecycle = frontier.get("latest_transition_lifecycle")
            lifecycle = lifecycle if isinstance(lifecycle, Mapping) else {}
            if expected_disposition_owner is not None:
                observed_owner = lifecycle.get(
                    "transition_lifecycle_required_disposition_owner"
                )
                if observed_owner != expected_disposition_owner:
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: "
                        f"required_disposition_owner expected {expected_disposition_owner!r}, "
                        f"observed {observed_owner!r}"
                    )
            if expected_hold_gate_ref is not None:
                paused_at = str(lifecycle.get("transition_lifecycle_paused_at_ref") or "")
                if expected_hold_gate_ref.replace(":", "-") not in paused_at:
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: hold gate "
                        f"{expected_hold_gate_ref!r} not named by paused_at_ref {paused_at!r}"
                    )
            if expected_frontier == "complete":
                _assert_no_missing_gate_facts(
                    result.run_result.lifecycle_write.root, label=f"{label}/run"
                )
            elif expected_missing_fact is not None:
                # A declared HOLD case: the recorded missing fact must BE the
                # expected disposition fact (the gate withheld Movement for the
                # declared reason, not for an unrelated insufficiency).
                _assert_missing_gate_fact_present(
                    result.run_result.lifecycle_write.root,
                    expected_missing_fact=expected_missing_fact,
                    label=f"{label}/run",
                )
            if task_statement is not None:
                # TASK-BY-TEXT (0611) FIRE: the building's work/task.md must
                # carry the spoken statement VERBATIM (modulo the single
                # trailing newline the evidence writer guarantees), and the
                # intake result must record the task_statement basis.
                expected_body = (
                    task_statement
                    if task_statement.endswith("\n")
                    else task_statement + "\n"
                )
                task_md = result.run_result.lifecycle_write.root / "work" / "task.md"
                observed_body = (
                    task_md.read_text(encoding="utf-8") if task_md.is_file() else ""
                )
                if observed_body != expected_body:
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: work/task.md does "
                        f"not carry the task_statement verbatim (observed "
                        f"{observed_body!r}, expected {expected_body!r})"
                    )
                if getattr(result, "task_source_basis", "") != "task_statement":
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: intake result must "
                        "record task_source_basis == 'task_statement'"
                    )
                # REPLAY READINESS (codex Vector C, 0611): the persisted
                # declared plan is the task CARRIER -- it must record the
                # inline sentinel task_source_ref AND the statement body, so
                # the plan file alone reproduces the task.
                if plan_on_disk.get("task_source_ref") != "task-source:inline-statement":
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: inline plan must "
                        "record task_source_ref 'task-source:inline-statement', observed "
                        f"{plan_on_disk.get('task_source_ref')!r}"
                    )
                if plan_on_disk.get("task_statement") != expected_body:
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: the declared plan "
                        "on disk must carry the normalized task_statement body verbatim "
                        f"(observed {plan_on_disk.get('task_statement')!r})"
                    )
                # REPLAY FIRE (positive, codex Vector C): re-running the SAME
                # persisted inline plan file must reproduce work/task.md
                # verbatim -- no external file exists to lose, the statement
                # travels with the plan.
                from support.operator.run import run_building_plan

                replay_root = Path(tmpdir) / "replay-buildings"
                replay_result = run_building_plan(
                    result.plan_path,
                    output_root=replay_root,
                    overwrite_existing=True,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": seam_callable
                    },
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
                replay_task_md = (
                    replay_result.lifecycle_write.root / "work" / "task.md"
                )
                replay_body = (
                    replay_task_md.read_text(encoding="utf-8")
                    if replay_task_md.is_file()
                    else ""
                )
                if replay_body != expected_body:
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: REPLAY of the "
                        "persisted inline plan did not reproduce work/task.md verbatim "
                        f"(observed {replay_body!r}, expected {expected_body!r})"
                    )

        if task_statement is not None:
            # TASK-BY-TEXT residue FIRE: the driver must leave NO ephemeral
            # statement file at the repo root (success path just ran above).
            statement_residue_after = {
                path.name for path in repo.glob("task-statement-*.md")
            }
            leaked = sorted(statement_residue_after - statement_residue_before)
            if leaked:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: ephemeral "
                    f"task-statement file(s) leaked at the repo root: {leaked}"
                )
            # TASK-BY-TEXT fail-closed FIRE: BOTH task sources -> reject with
            # the EITHER/OR message (never a silent pick); EMPTY statement ->
            # reject. Both probes must not write any output.
            both_intent = dict(intent)
            both_intent["task_source_ref"] = "brick/templates/tasks/source-template.md"
            with tempfile.TemporaryDirectory(
                prefix="bp-building-intake-seam-both-"
            ) as tmpdir:
                both_output = Path(tmpdir) / "buildings"
                try:
                    run_building_intake(
                        both_intent,
                        repo_root=repo,
                        output_root=both_output,
                        overwrite_existing=True,
                        local_callables={
                            "callable:local:agent-invoke0-smoke": _building_intake_seam_callable
                        },
                        adapter_cwd=repo,
                        adapter_timeout_seconds=10,
                    )
                except ValueError as exc:
                    if "EITHER task_source_ref OR task_statement" not in str(exc):
                        raise ProfileError(
                            f"building_intake_seam_case rejected {label}: BOTH-sources "
                            f"intent failed for the WRONG reason: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: an intent with "
                        "BOTH task_source_ref AND task_statement was NOT rejected"
                    )
                if both_output.exists() and any(both_output.rglob("*")):
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: BOTH-sources "
                        "intent wrote Building output despite the reject"
                    )
            empty_intent = dict(intent)
            empty_intent["task_statement"] = "   "
            try:
                run_building_intake(
                    empty_intent,
                    repo_root=repo,
                    output_root=Path(tempfile.gettempdir()) / "bp-intake-empty-never",
                    overwrite_existing=True,
                )
            except ValueError as exc:
                if "task_statement must be non-empty text" not in str(exc):
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: empty "
                        f"task_statement failed for the WRONG reason: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: an empty "
                    "task_statement was NOT rejected"
                )
            # TASK-BY-TEXT size-guard FIRE (codex note, 0611): a statement
            # over the inline byte limit must reject loudly with a pointer to
            # the file flow, and must not write any output.
            oversize_intent = dict(intent)
            oversize_intent["task_statement"] = "x" * (65536 + 1)
            try:
                run_building_intake(
                    oversize_intent,
                    repo_root=repo,
                    output_root=Path(tempfile.gettempdir()) / "bp-intake-oversize-never",
                    overwrite_existing=True,
                )
            except ValueError as exc:
                if "exceeds the inline limit" not in str(exc):
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: oversize "
                        f"task_statement failed for the WRONG reason: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: an oversize "
                    "task_statement was NOT rejected"
                )
            # FIX-IDEMPOTENCY FIRE (0611): with building_id ABSENT on the
            # inline path the default id is a STABLE hash of (statement +
            # preset): (a) the same statement+preset materializes the SAME id
            # twice; (b) a different statement derives a DIFFERENT id; (c) the
            # same statement+preset retried through the seam COLLIDES LOUDLY
            # with the existing declared-plan root instead of duplicating
            # roots. REDs if the derivation regresses to a random/per-call id
            # (a or c fails) or to a statement-independent slug (b fails).
            from support.operator.composition import materialize_building_intent

            derived_intent = {
                key: value
                for key, value in intent.items()
                if key not in {"building_id", "plan_ref"}
            }
            first_id = str(
                materialize_building_intent(derived_intent, repo_root=repo).get("building_id")
            )
            second_id = str(
                materialize_building_intent(dict(derived_intent), repo_root=repo).get("building_id")
            )
            if not first_id or first_id != second_id:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: inline default "
                    f"building_id is not stable across retries ({first_id!r} vs "
                    f"{second_id!r})"
                )
            other_statement_intent = dict(derived_intent)
            other_statement_intent["task_statement"] = f"{task_statement} -- 변형."
            other_id = str(
                materialize_building_intent(other_statement_intent, repo_root=repo).get("building_id")
            )
            if other_id == first_id:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: DIFFERENT inline "
                    "statements derived the SAME default building_id (statement body "
                    "must feed the id)"
                )
            with tempfile.TemporaryDirectory(
                prefix="bp-building-intake-seam-retry-"
            ) as tmpdir:
                retry_output = Path(tmpdir) / "buildings"
                run_building_intake(
                    derived_intent,
                    repo_root=repo,
                    output_root=retry_output,
                    overwrite_existing=False,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": seam_callable
                    },
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
                try:
                    run_building_intake(
                        dict(derived_intent),
                        repo_root=repo,
                        output_root=retry_output,
                        overwrite_existing=False,
                        local_callables={
                            "callable:local:agent-invoke0-smoke": seam_callable
                        },
                        adapter_cwd=repo,
                        adapter_timeout_seconds=10,
                    )
                except ValueError as exc:
                    if "declared Building plan already exists" not in str(exc):
                        raise ProfileError(
                            f"building_intake_seam_case rejected {label}: inline "
                            f"retry collided for the WRONG reason: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: retrying the "
                        "SAME inline statement+preset did NOT collide loudly with "
                        "the existing root (duplicate-root regression)"
                    )

        # FIRE: a no-preset intent MUST hard-fail at materialization; the seam must
        # not write a plan or run a Building. The assertion is SPECIFIC: it requires
        # the registry-absent-preset error AND that no plan file landed on disk, so
        # it REDs both if the hard-fail is bypassed (a Building ran) and if some
        # UNRELATED failure masquerades as the preset hard-fail.
        no_preset_intent = dict(intent)
        no_preset_building_id = f"{building_id}-no-preset"
        no_preset_intent["building_id"] = no_preset_building_id
        no_preset_intent["plan_ref"] = f"building-plan:{no_preset_building_id}"
        no_preset_intent["chain_preset_ref"] = no_preset_chain_preset_ref
        with tempfile.TemporaryDirectory(prefix="bp-building-intake-seam-nopreset-") as tmpdir:
            no_preset_output = Path(tmpdir) / "buildings"
            try:
                run_building_intake(
                    no_preset_intent,
                    repo_root=repo,
                    output_root=no_preset_output,
                    overwrite_existing=True,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _building_intake_seam_callable
                    },
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
            except (ValueError, TypeError) as exc:
                if "must be present in the Brick template catalog" not in str(exc):
                    raise ProfileError(
                        f"building_intake_seam_case rejected {label}: no-preset intent failed "
                        f"for the WRONG reason (not the registry-absent-preset hard-fail): {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: no-preset intent did NOT "
                    "hard-fail; the seam ran a Building without a registry preset"
                )
            if no_preset_output.exists() and any(no_preset_output.rglob("*")):
                raise ProfileError(
                    f"building_intake_seam_case rejected {label}: no-preset intent wrote "
                    "Building output despite hard-fail; the seam must not materialize or run"
                )
        count += 1
    return count


def run_intake_project_vessel_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """PROJECT-0 S3-C: intake <-> project vessel connection, executed four ways.

    One item drives the REAL ``run_building_intake`` over adapter:local against
    a SYNTHETIC vessel created by the S2 creation verb (born checker-legal; no
    dogfood-building dependency) and asserts:

      1. VESSEL FLOW — an intent with ``project_ref: project:<vessel_id>``
         lands the declared plan AND the Building evidence under
         ``project/<vessel_id>/buildings/`` (the root derived through
         ``buildings_root_for``, THE single seam), reaches a complete frontier,
         and the persisted plan records the ``project_ref`` fact verbatim.
      2. BOGUS REF — ``project:<absent-id>`` rejects loudly BEFORE any run
         (no vessel dir appears, no plan is written); a MALFORMED ref rejects
         with the seam's own form error.
      3. CHARTERLESS VESSEL — a HAND-MADE ``project/<id>/`` directory without
         charter+declaration rejects loudly with the S1 loader's own voice
         (undeclared vessels are refused at intake, not discovered later).
      4. COMPAT — the ref-less default root resolves through
         ``default_buildings_root()`` (caller-local evidence home), while
         ``buildings_root_for('project:brick-protocol')`` remains the declared
         project_ref vessel root; no parallel path-join literal survives, and a
         double root declaration (project_ref AND explicit output_root)
         rejects as ambiguous.

    The synthetic vessel (and the hand-made charterless fixture) are removed in
    a ``finally`` so the repo tree is left unchanged. A PRE-EXISTING directory
    under either fixture id REDs the case instead of being reused or deleted
    (a possibly-real vessel is never touched).
    """
    items = rule_items(profile, "intake_project_vessel_case")
    if not items:
        return 0
    import shutil

    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from support.operator.building_operation import observe_building_frontier
    from support.operator.driver import run_building_intake
    from support.operator.project_creation import create_project
    from support.recording.capture import (
        DEFAULT_BUILDINGS_ROOT,
        buildings_root_for,
        default_buildings_root,
    )

    # C4 (0615): governed-change-review's QA bricks now declare a write NEED, so
    # the intent carries a broad work-area write_scope and the seam is driven by
    # adapter:codex-local through the EXISTING command_runner sentinel (no real
    # CLI). adapter:local (read-only in-process stub) must not drive a
    # write-needing QA building. .git/secret/token stay unconditionally forbidden
    # by write_observation.py.
    vessel_command_runner = _preset_completion_command_runner(LocalCliCompleted)
    vessel_write_scope = {"allowed_paths": ["**"], "forbidden_paths": [".git/**"]}

    count = 0
    for item in items:
        mapping = require_mapping(item, "intake_project_vessel_case item")
        label = require_string(mapping.get("label"), "intake_project_vessel_case.label")
        vessel_id = require_string(mapping.get("vessel_id"), f"{label}: vessel_id")
        chain_preset_ref = require_string(
            mapping.get("chain_preset_ref"), f"{label}: chain_preset_ref"
        )
        task_statement = require_string(
            mapping.get("task_statement"), f"{label}: task_statement"
        )
        route_decision_basis = mapping.get("route_decision_basis")
        if route_decision_basis is not None:
            route_decision_basis = require_mapping(
                route_decision_basis, f"{label}: route_decision_basis"
            )

        # COMPAT (leg 4a, no filesystem): the ref-less default root must resolve
        # through the lazy caller-local evidence-home seam; declared project_ref
        # roots still derive through buildings_root_for(project_ref).
        if Path(DEFAULT_BUILDINGS_ROOT) != default_buildings_root():
            raise ProfileError(
                f"intake_project_vessel_case rejected {label}: DEFAULT_BUILDINGS_ROOT "
                "is not default_buildings_root() — the ref-less default must derive "
                "through the lazy evidence-home seam, no parallel literal"
            )
        expected_project_root = repo / "project" / "brick-protocol" / "buildings"
        if buildings_root_for("project:brick-protocol") != expected_project_root:
            raise ProfileError(
                f"intake_project_vessel_case rejected {label}: buildings_root_for("
                "'project:brick-protocol') no longer resolves to the declared "
                "project_ref vessel root"
            )

        project_ref = f"project:{vessel_id}"
        vessel_dir = repo / "project" / vessel_id
        charterless_id = f"{vessel_id}-charterless"
        charterless_dir = repo / "project" / charterless_id
        absent_id = f"{vessel_id}-absent"
        absent_dir = repo / "project" / absent_id
        for fixture_dir in (vessel_dir, charterless_dir, absent_dir):
            if fixture_dir.exists():
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: fixture path "
                    f"{fixture_dir} already exists — refusing to reuse or remove a "
                    "possibly-real vessel; pick an unused fixture vessel_id"
                )

        building_id = f"{_case_slug(label)}-vessel-building"
        intent: dict[str, Any] = {
            "plan_ref": f"building-plan:{building_id}",
            "building_id": building_id,
            "declared_by": "coo",
            "task_statement": task_statement,
            "chain_preset_ref": chain_preset_ref,
            "selected_adapter_ref": "adapter:codex-local",
            "selected_model_ref": "model:default",
            "write_scope": dict(vessel_write_scope),
            "project_ref": project_ref,
            "report_event_policy": {"enabled": False},
            "proof_limits": [
                "intake project-vessel checker support evidence only",
                "not source truth",
                "not success judgment",
                "not quality judgment",
                "not Movement authority",
            ],
            "not_proven": [
                f"semantic correctness of {label}",
                "real provider behavior",
            ],
        }
        if route_decision_basis is not None:
            intent["route_decision_basis"] = dict(route_decision_basis)

        try:
            # Leg 1 — synthetic vessel via the S2 creation verb (checker-legal
            # by construction: charter first, declaration second, skeleton).
            create_project(
                repo,
                project_id=vessel_id,
                label=f"checker fixture vessel for {label}",
                direction="hold one executed intake-seam checker building, then be removed",
                why_exists="checker fixture: proves intake with project_ref lands in this vessel",
                why_now="created and removed inside one intake_project_vessel_case run",
                done_means="the case's assertions ran; the vessel is removed in finally",
                out_of_scope="any real work; this vessel never outlives the checker case",
                managers=["checker-fixture-human"],
                declared_by="coo:intake-project-vessel-case",
            )
            result = run_building_intake(
                intent,
                repo_root=repo,
                overwrite_existing=False,
                command_runner=vessel_command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
            )
            expected_root = buildings_root_for(project_ref)
            if result.plan_path.parent.parent != expected_root:
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: declared plan landed "
                    f"at {result.plan_path}, not under the seam-derived vessel root "
                    f"{expected_root}"
                )
            evidence_root = result.run_result.lifecycle_write.root
            if evidence_root.parent != expected_root:
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: Building evidence "
                    f"landed at {evidence_root}, not under the seam-derived vessel root "
                    f"{expected_root}"
                )
            frontier = observe_building_frontier(evidence_root, repo_root=repo)
            if frontier.get("frontier_kind") != "complete":
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: frontier_kind "
                    f"expected 'complete', observed {frontier.get('frontier_kind')!r}"
                )
            plan_on_disk = json.loads(result.plan_path.read_text(encoding="utf-8"))
            if plan_on_disk.get("project_ref") != project_ref:
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: the persisted plan "
                    f"must record the project_ref fact verbatim, observed "
                    f"{plan_on_disk.get('project_ref')!r}"
                )

            # Leg 4b — double root declaration rejects as ambiguous, BEFORE any run.
            ambiguous_intent = dict(intent)
            ambiguous_intent["building_id"] = f"{building_id}-ambiguous"
            ambiguous_intent["plan_ref"] = f"building-plan:{building_id}-ambiguous"
            with tempfile.TemporaryDirectory(
                prefix="bp-intake-project-vessel-ambiguous-"
            ) as tmpdir:
                ambiguous_output = Path(tmpdir) / "buildings"
                try:
                    run_building_intake(
                        ambiguous_intent,
                        repo_root=repo,
                        output_root=ambiguous_output,
                        command_runner=vessel_command_runner,
                        adapter_cwd=repo,
                        adapter_timeout_seconds=10,
                    )
                except ValueError as exc:
                    if "two output-root declarations are ambiguous" not in str(exc):
                        raise ProfileError(
                            f"intake_project_vessel_case rejected {label}: "
                            f"project_ref+output_root failed for the WRONG reason: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"intake_project_vessel_case rejected {label}: an intent with "
                        "BOTH project_ref AND explicit output_root was NOT rejected"
                    )
                if ambiguous_output.exists() and any(ambiguous_output.rglob("*")):
                    raise ProfileError(
                        f"intake_project_vessel_case rejected {label}: ambiguous-root "
                        "intent wrote Building output despite the reject"
                    )

            # Leg 4c — 'output_root' smuggled as an INTENT KEY (not the driver
            # parameter) must reject loudly, not be silently ignored (operator
            # gate finding 0611: no code reads that key, so without the reject
            # the building silently lands elsewhere than the caller declared).
            smuggled_intent = dict(intent)
            smuggled_intent["building_id"] = f"{building_id}-smuggled-root"
            smuggled_intent["plan_ref"] = f"building-plan:{building_id}-smuggled-root"
            smuggled_intent["output_root"] = "/tmp/intake-project-vessel-smuggled-root"
            try:
                run_building_intake(
                    smuggled_intent,
                    repo_root=repo,
                    command_runner=vessel_command_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
            except ValueError as exc:
                if "must not carry an 'output_root' key" not in str(exc):
                    raise ProfileError(
                        f"intake_project_vessel_case rejected {label}: intent-key "
                        f"output_root failed for the WRONG reason: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: an intent CARRYING "
                    "an 'output_root' key was NOT rejected — the dead key would be "
                    "silently swallowed and the building would land elsewhere"
                )

            # Leg 2 — bogus vessel ref rejects loudly BEFORE any run.
            bogus_intent = dict(intent)
            bogus_intent["building_id"] = f"{building_id}-bogus"
            bogus_intent["plan_ref"] = f"building-plan:{building_id}-bogus"
            bogus_intent["project_ref"] = f"project:{absent_id}"
            try:
                run_building_intake(
                    bogus_intent,
                    repo_root=repo,
                    command_runner=vessel_command_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
            except ValueError as exc:
                if "names no existing vessel" not in str(exc):
                    raise ProfileError(
                        f"intake_project_vessel_case rejected {label}: bogus "
                        f"project_ref failed for the WRONG reason: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: a project_ref naming "
                    "no existing vessel was NOT rejected"
                )
            if absent_dir.exists():
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: the bogus-ref reject "
                    f"still created a vessel dir at {absent_dir} (intake must never "
                    "invent a vessel)"
                )
            malformed_intent = dict(bogus_intent)
            malformed_intent["project_ref"] = "not-a-project-ref"
            try:
                run_building_intake(
                    malformed_intent,
                    repo_root=repo,
                    command_runner=vessel_command_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
            except ValueError as exc:
                if "must look like 'project:<id>'" not in str(exc):
                    raise ProfileError(
                        f"intake_project_vessel_case rejected {label}: malformed "
                        f"project_ref failed for the WRONG reason: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: a malformed "
                    "project_ref was NOT rejected"
                )

            # Leg 3 — hand-made charterless dir rejects with the S1 loader's voice.
            charterless_dir.mkdir(parents=True)
            charterless_intent = dict(intent)
            charterless_intent["building_id"] = f"{building_id}-charterless"
            charterless_intent["plan_ref"] = f"building-plan:{building_id}-charterless"
            charterless_intent["project_ref"] = f"project:{charterless_id}"
            try:
                run_building_intake(
                    charterless_intent,
                    repo_root=repo,
                    command_runner=vessel_command_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
            except ValueError as exc:
                if "project.json is missing" not in str(exc):
                    raise ProfileError(
                        f"intake_project_vessel_case rejected {label}: charterless "
                        f"vessel failed for the WRONG reason: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: a hand-made "
                    "charterless vessel was NOT rejected at intake"
                )
            if any(charterless_dir.rglob("*")):
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: the charterless "
                    "reject still wrote into the hand-made vessel dir"
                )
        finally:
            shutil.rmtree(vessel_dir, ignore_errors=True)
            shutil.rmtree(charterless_dir, ignore_errors=True)
        count += 1
    return count


def run_onboard_seam_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """ONBOARDING-WIZARD-0 PART-2: assert the example routes through the PART-1 seam.

    Drives the REAL ``support.operator.onboard.run_onboard`` end-to-end on the
    default (no real-provider opt-in) path with a TEMP output_root and asserts the
    PART-2 contract:

      1. ROUTED-THROUGH-SEAM: the example_result records ``routed_through ==
         support.operator.driver.run_building_intake`` (the PART-1 seam), not the
         old raw run_building_plan path.
      2. PREFLIGHT-READINESS-EVIDENCE: the result carries a structured
         ``preflight_readiness`` token (ready/unauthed/missing/unknown), mirrored
         onto the example_result -- preflight is auditable evidence, not just a
         Korean string. The example_result also records the adapter it used and the
         ``adapter_choice_basis`` (WHY), so the real-vs-local routing is auditable.
      3. HANDOFF-NAMES-SEAM: the closing handoff_message_ko NAMES the seam verb.
      4. TERMINAL-FRONTIER: the default example runs on adapter:local through the
         seam and reaches the expected terminal frontier with landed evidence
         under the TEMP output_root (never the repo).
      5. NEVER-RAISES-MISSING-PROVIDER: a bogus / missing-provider host stays
         ok-friendly (no raise) and STILL routes the friendly fallback through the
         seam on adapter:local.

    SELF-FIRE: the case REDs if the example bypasses the seam (routed_through is not
    the seam verb, or the default branch did not run on adapter:local) OR if the
    handoff omits the seam pointer OR if preflight readiness is not recorded. The
    last item additionally asserts run_onboard NEVER raises for a missing provider.
    """
    items = rule_items(profile, "onboard_seam_case")
    if not items:
        return 0

    onboard = importlib.import_module("brick_protocol.support.operator.onboard")
    seam_verb = onboard.SEAM_VERB
    expected_local_adapter = "adapter:local"
    allowed_readiness = {"ready", "unauthed", "missing", "unknown"}

    count = 0
    for item in items:
        mapping = require_mapping(item, "onboard_seam_case item")
        label = require_string(mapping.get("label"), "onboard_seam_case.label")
        host = require_string(mapping.get("host", "codex"), f"{label}: host")
        bogus_host = require_string(
            mapping.get("bogus_host", "definitely-not-a-host"), f"{label}: bogus_host"
        )
        expected_frontier = require_string(
            mapping.get("expected_frontier_kind", "complete"),
            f"{label}: expected_frontier_kind",
        )

        # (1)-(4) Default path: no real-provider opt-in -> adapter:local through seam.
        with tempfile.TemporaryDirectory(prefix="bp-onboard-seam-") as tmp:
            tmp_root = Path(tmp)
            try:
                result = onboard.run_onboard(
                    host,
                    repo_root=repo,
                    run_example=True,
                    output_root=tmp_root,
                    allow_real_provider=False,
                )
            except Exception as exc:  # noqa: BLE001 -- no-raise is under test
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: run_onboard raised "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

            readiness = result.get("preflight_readiness")
            if readiness not in allowed_readiness:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: preflight_readiness must be "
                    f"recorded as one of {sorted(allowed_readiness)}, got {readiness!r}"
                )

            handoff = str(result.get("handoff_message_ko") or "")
            if seam_verb not in handoff:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: handoff must NAME the seam verb "
                    f"{seam_verb!r}; got handoff without it"
                )

            example = result.get("example_result")
            if not isinstance(example, Mapping):
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example_result must be a mapping"
                )
            if example.get("routed_through") != seam_verb:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example must route through the seam "
                    f"{seam_verb!r}; got routed_through={example.get('routed_through')!r} "
                    "(the example bypassed the PART-1 seam)"
                )
            if example.get("preflight_readiness") != readiness:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example_result must mirror the "
                    f"recorded preflight_readiness {readiness!r}; got "
                    f"{example.get('preflight_readiness')!r}"
                )
            if not str(example.get("adapter_choice_basis") or "").strip():
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example must record an "
                    "adapter_choice_basis (WHY the adapter was chosen)"
                )
            if example.get("adapter_ref") != expected_local_adapter:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: default (no opt-in) example must "
                    f"use {expected_local_adapter!r}; got {example.get('adapter_ref')!r}"
                )
            if example.get("real_provider") is not False:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: default example must record "
                    f"real_provider False; got {example.get('real_provider')!r}"
                )
            if example.get("ran") is not True:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example did not run (ran != True)"
                )
            if example.get("frontier_kind") != expected_frontier:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example frontier expected "
                    f"{expected_frontier!r}, got {example.get('frontier_kind')!r}"
                )
            evidence_root = str(example.get("evidence_root") or "")
            if not evidence_root:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example missing evidence_root"
                )
            try:
                Path(evidence_root).resolve().relative_to(tmp_root.resolve())
            except ValueError as exc:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example evidence must land under "
                    f"the TEMP output_root, not {evidence_root}"
                ) from exc
            if int(example.get("written_file_count") or 0) <= 0:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example produced no evidence files"
                )

        # (5) FIRE / friendliness: a bogus / missing-provider host must NOT raise and
        #     must STILL route the friendly fallback through the seam on adapter:local.
        with tempfile.TemporaryDirectory(prefix="bp-onboard-seam-missing-") as tmp:
            tmp_root = Path(tmp)
            try:
                missing = onboard.run_onboard(
                    bogus_host,
                    repo_root=repo,
                    run_example=True,
                    output_root=tmp_root,
                    allow_real_provider=True,
                )
            except Exception as exc:  # noqa: BLE001 -- no-raise is the invariant under test
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: run_onboard raised for a "
                    f"missing/bogus provider host (friendly contract broken): "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            missing_example = missing.get("example_result")
            if not isinstance(missing_example, Mapping):
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing-provider example_result "
                    "must be a mapping"
                )
            if missing_example.get("routed_through") != seam_verb:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing-provider fallback must still "
                    f"route through the seam {seam_verb!r}; got "
                    f"{missing_example.get('routed_through')!r}"
                )
            if missing_example.get("adapter_ref") != expected_local_adapter:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: missing-provider fallback must use "
                    f"{expected_local_adapter!r}; got {missing_example.get('adapter_ref')!r}"
                )
            if missing.get("preflight_readiness") not in {"missing", "unauthed", "unknown"}:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: a bogus/missing-provider host must NOT "
                    "record preflight_readiness 'ready' (a readiness mislabel) and must record one "
                    f"of missing/unauthed/unknown; got {missing.get('preflight_readiness')!r}"
                )
        count += 1
    return count


# Pick/rank field names that would betray the axis law if support emitted them:
# the packet records candidates + a mechanical match reason ONLY, and must NEVER
# pick among >= 2, rank, or recommend. The AXIS FIRE asserts NONE of these appear
# anywhere in the packet (top-level or per-row). If the packet were reverted to
# pick/rank one, the case goes RED here.
_AGENT_CANDIDATE_FORBIDDEN_PICK_FIELDS = frozenset(
    {
        "selected",
        "selected_agent",
        "chosen",
        "chosen_agent",
        "recommended",
        "recommended_agent",
        "recommendation",
        "pick",
        "picked",
        "winner",
        "best",
        "rank",
        "ranking",
        "ranked",
        "score",
        "preferred",
        # A "default" is still a support-side PICK among >= 2 candidates: it
        # silently elevates one ref over the others. The packet records the brick
        # NEED + every matching CAPABILITY; choosing a default belongs to the
        # author/COO, never to this read-only surface.
        "default",
        "default_agent",
    }
)


def run_agent_candidate_packet_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """Exercise the READ-ONLY agent NEED<->CAPABILITY candidate packet (PART-2 P3).

    For each declared item this drives ``render_agent_candidate_packet`` over the
    real Agent Object set and asserts:

    * MULTI: an ambiguous need (>= 2 candidates) records ALL qualifying agents
      (none omitted), marks ``ambiguous``/``disposition_required`` True with
      ``required_disposition_owner == 'caller-or-coo'``, and gives each row a
      MECHANICAL ``match_reason`` that states lane + write scope ONLY.
    * SINGLE: a single-candidate need is unambiguous (``disposition_required``
      False).
    * AXIS FIRE: support does NOT auto-pick among >= 2. The packet carries NO
      pick/rank/recommend field (top-level or per-row), AND the matcher
      ``_resolve_agent_for_need`` still RAISES for the >= 2 case (unchanged). This
      is the self-FIRE guard: making the packet pick/rank one reverts to RED.
    """
    items = rule_items(profile, "agent_candidate_packet_case")
    if not items:
        return 0
    from brick_protocol.support.connection.building_design_toolkit import (
        render_agent_candidate_packet,
    )
    from brick_protocol.support.operator.plan_rendering import _resolve_agent_for_need

    count = 0
    for item in items:
        mapping = require_mapping(item, "agent_candidate_packet_case item")
        label = require_string(mapping.get("label"), "agent_candidate_packet_case.label")
        role_need = require_string(mapping.get("role_need"), f"{label}: role_need")
        write_need_raw = mapping.get("write_need", False)
        if not isinstance(write_need_raw, bool):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: write_need must be a YAML bool"
            )
        write_need = write_need_raw
        expect_ambiguous_raw = mapping.get("expect_ambiguous")
        if not isinstance(expect_ambiguous_raw, bool):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: expect_ambiguous must be a YAML bool"
            )
        expect_ambiguous = expect_ambiguous_raw
        expect_min_candidates = int(
            require_string(
                str(mapping.get("expect_min_candidates", "0")),
                f"{label}: expect_min_candidates",
            )
        )
        expected_refs = require_string_list(
            mapping.get("expected_candidate_refs", []),
            f"{label}: expected_candidate_refs",
        )

        packet = render_agent_candidate_packet(role_need, write_need, repo_root=repo)

        if packet.get("kind") != "agent-candidate-packet":
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: "
                f"kind expected 'agent-candidate-packet', observed {packet.get('kind')!r}"
            )
        if packet.get("role_need") != role_need or packet.get("write_need") != write_need:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: packet did not echo the need "
                f"(role_need={packet.get('role_need')!r}, write_need={packet.get('write_need')!r})"
            )

        rows = packet.get("candidate_rows")
        if not isinstance(rows, list):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: candidate_rows must be a list"
            )
        observed_refs = [row.get("agent_object_ref") for row in rows]
        total = packet.get("total_candidates")
        if total != len(rows):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: total_candidates {total!r} "
                f"!= len(candidate_rows) {len(rows)}"
            )
        if total < expect_min_candidates:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: total_candidates {total} "
                f"< expect_min_candidates {expect_min_candidates}"
            )

        # ambiguity / disposition mechanics
        ambiguous = packet.get("ambiguous")
        if ambiguous != expect_ambiguous:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: ambiguous expected "
                f"{expect_ambiguous}, observed {ambiguous!r}"
            )
        if ambiguous != (total >= 2):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: ambiguous {ambiguous!r} "
                f"inconsistent with total_candidates {total}"
            )
        if packet.get("disposition_required") != ambiguous:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: disposition_required must "
                f"track ambiguous; got {packet.get('disposition_required')!r} vs {ambiguous!r}"
            )
        if packet.get("required_disposition_owner") != "caller-or-coo":
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: required_disposition_owner "
                f"expected 'caller-or-coo', observed {packet.get('required_disposition_owner')!r}"
            )

        # ALL qualifying agents present (none omitted) when an explicit set is declared.
        if expected_refs and sorted(observed_refs) != sorted(expected_refs):
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: candidate refs mismatch; "
                f"expected {sorted(expected_refs)}, observed {sorted(observed_refs)}"
            )

        # Each row's match_reason is MECHANICAL: it states lane + write scope ONLY.
        write_scope_word = "yes" if write_need else "no"
        expected_reason = f"lane={role_need}, write_scope={write_scope_word}"
        for row in rows:
            if not isinstance(row, Mapping):
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: each candidate row must be a mapping"
                )
            if row.get("match_reason") != expected_reason:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} match_reason expected {expected_reason!r}, "
                    f"observed {row.get('match_reason')!r} (must be MECHANICAL: lane + write only)"
                )
            if row.get("lane") != role_need:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} lane {row.get('lane')!r} != role_need {role_need!r}"
                )
            # capability >= need: when the brick NEEDS write, EVERY candidate row
            # must be writer_capable; when the need is read-only, writer-capability
            # is UNCONSTRAINED (a write-capable agent may serve a read-only need;
            # effective write stays gated by the Brick write_scope NEED downstream).
            if write_need and not bool(row.get("writer_capable")):
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} writer_capable {row.get('writer_capable')!r} "
                    f"does not satisfy write_need {write_need}"
                )
            if bool(row.get("qualifies")) != ambiguous:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} qualifies must track ambiguity "
                    f"({row.get('qualifies')!r} vs {ambiguous!r})"
                )

        # AXIS FIRE 1: NO pick/rank/recommend field anywhere (top-level or per-row).
        top_hits = sorted(set(packet.keys()) & _AGENT_CANDIDATE_FORBIDDEN_PICK_FIELDS)
        if top_hits:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: packet carries forbidden "
                f"pick/rank field(s) at top level {top_hits}; support must NOT pick among candidates"
            )
        for row in rows:
            row_hits = sorted(set(row.keys()) & _AGENT_CANDIDATE_FORBIDDEN_PICK_FIELDS)
            if row_hits:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: candidate row "
                    f"{row.get('agent_object_ref')!r} carries forbidden pick/rank field(s) "
                    f"{row_hits}; support must NOT rank or recommend"
                )

        # AXIS FIRE 2: the matcher's >= 2 fail-closed halt is UNCHANGED.
        if ambiguous:
            try:
                _resolve_agent_for_need(repo, role_need, write_need)
            except ValueError:
                pass
            else:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: _resolve_agent_for_need did NOT "
                    f"raise for the ambiguous need (role_need={role_need!r}, write_need={write_need}); "
                    "the fail-closed >= 2 halt must stay (the packet is the surface beside it, not a bypass)"
                )
        else:
            # Single candidate must still auto-resolve to that one candidate (unchanged).
            resolved = _resolve_agent_for_need(repo, role_need, write_need)
            if observed_refs and resolved != observed_refs[0]:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: single-candidate need must "
                    f"auto-resolve to {observed_refs[0]!r}, matcher returned {resolved!r}"
                )

        count += 1
    return count


# Pick/recommend field names that would betray the axis law if the preset-ranking
# packet emitted them: the packet ORDERS presets by a MECHANICAL hint-token count
# and MUST NEVER pick one, recommend one, or call one "best"/"use_this". Unlike the
# agent-candidate packet, ``rank`` / ``ranked`` / ``score`` are LEGITIMATE here (the
# mechanical ordering IS the surface), so they are deliberately NOT in this set; only
# decision/recommendation words are forbidden. The AXIS FIRE asserts NONE of these
# appear anywhere (top-level or per-row). Inject any of them and the case goes RED.
_PRESET_RANKING_FORBIDDEN_PICK_FIELDS = frozenset(
    {
        "selected",
        "selected_preset",
        "chosen",
        "chosen_preset",
        "recommended",
        "recommended_preset",
        "recommendation",
        "pick",
        "picked",
        "winner",
        "best",
        "best_preset",
        "use_this",
        "preferred",
        # A "default" preset is a recommendation-to-use by another name: it picks
        # one preset for the caller. The ranking ORDERS by mechanical hint-match
        # only; declaring the active preset stays a caller/COO act.
        "default",
        "default_preset",
    }
)


def run_preset_ranking_packet_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """Exercise the READ-ONLY, NON-BINDING preset-ranking packet (PART-2 P4).

    For each declared item this drives ``render_preset_ranking_packet`` over the
    real chain-preset catalog and asserts:

    * RANK: ranked_rows are ordered by MECHANICAL hint-match (descending
      hint_match_score, deterministic tiebreak by chain_preset_ref ascending);
      total_candidates equals len(ranked_rows); ranking_basis states it is
      "mechanical hint-match (not quality)"; rank is 1-based contiguous; each
      row's hint_match_score is a non-negative int. An optional
      expect_top_ref / expect_min_top_score pins a real hint to its top preset.
    * NON-BINDING / NO-PICK (axis FIRE): the packet carries NO
      selected/chosen/recommended/best/use_this field (top-level or per-row).
      Inject such a field and this goes RED.
    * MATERIALIZER STILL HARD-REFUSES (the biggest-unknown guard): even WITH a
      ranking available, ``materialize_building_intent`` STILL raises for an
      intent with no/blank chain_preset_ref -- the ranking NEVER auto-applies.
      If the materializer were made to fall back to the top-ranked preset, this
      assertion goes RED (proving the ranking is non-binding).
    """
    items = rule_items(profile, "preset_ranking_packet_case")
    if not items:
        return 0
    from brick_protocol.support.connection.building_design_toolkit import (
        render_preset_ranking_packet,
    )
    from brick_protocol.support.operator.composition import materialize_building_intent

    count = 0
    for item in items:
        mapping = require_mapping(item, "preset_ranking_packet_case item")
        label = require_string(mapping.get("label"), "preset_ranking_packet_case.label")
        selection_hint = require_string(
            mapping.get("selection_hint"), f"{label}: selection_hint"
        )
        catalog_scope_raw = mapping.get("catalog_scope")
        if catalog_scope_raw is not None and not isinstance(catalog_scope_raw, str):
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: catalog_scope must be a string or omitted"
            )
        catalog_scope = catalog_scope_raw
        expect_min_candidates = int(
            require_string(
                str(mapping.get("expect_min_candidates", "0")),
                f"{label}: expect_min_candidates",
            )
        )
        expect_top_ref = mapping.get("expect_top_ref")
        if expect_top_ref is not None and not isinstance(expect_top_ref, str):
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: expect_top_ref must be a string or omitted"
            )
        expect_min_top_score = int(
            require_string(
                str(mapping.get("expect_min_top_score", "0")),
                f"{label}: expect_min_top_score",
            )
        )

        packet = render_preset_ranking_packet(
            selection_hint, catalog_scope, repo_root=repo
        )

        if packet.get("kind") != "preset-ranking-packet":
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: kind expected "
                f"'preset-ranking-packet', observed {packet.get('kind')!r}"
            )
        if packet.get("source") != "brick/":
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: source expected 'brick/', "
                f"observed {packet.get('source')!r}"
            )
        if packet.get("selection_rule") != "caller_or_coo_declared_only":
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: selection_rule expected "
                f"'caller_or_coo_declared_only', observed {packet.get('selection_rule')!r}"
            )
        if packet.get("catalog_scope") != catalog_scope:
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: catalog_scope echo expected "
                f"{catalog_scope!r}, observed {packet.get('catalog_scope')!r}"
            )

        rows = packet.get("ranked_rows")
        if not isinstance(rows, list):
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: ranked_rows must be a list"
            )
        total = packet.get("total_candidates")
        if total != len(rows):
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: total_candidates {total!r} "
                f"!= len(ranked_rows) {len(rows)}"
            )
        if total < expect_min_candidates:
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: total_candidates {total} "
                f"< expect_min_candidates {expect_min_candidates}"
            )

        # ranking_basis must state it is mechanical hint-match, NOT quality.
        basis = packet.get("ranking_basis")
        if not isinstance(basis, str) or "mechanical hint-match" not in basis or "not quality" not in basis:
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: ranking_basis must state "
                f"'mechanical hint-match' and 'not quality'; observed {basis!r}"
            )

        # RANK mechanics: 1-based contiguous, sorted by (-score, ref).
        prev_key: tuple[int, str] | None = None
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: each ranked row must be a mapping"
                )
            rank = row.get("rank")
            if rank != index + 1:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: row {index} rank {rank!r} "
                    f"is not 1-based contiguous (expected {index + 1})"
                )
            ref = row.get("chain_preset_ref")
            if not isinstance(ref, str) or not ref:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: row {index} chain_preset_ref "
                    f"must be a non-empty string; observed {ref!r}"
                )
            score = row.get("hint_match_score")
            if not isinstance(score, int) or isinstance(score, bool) or score < 0:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: row {ref!r} hint_match_score "
                    f"must be a non-negative int; observed {score!r}"
                )
            this_key = (-score, ref)
            if prev_key is not None and this_key < prev_key:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: ranked_rows not ordered by "
                    f"(-hint_match_score, chain_preset_ref) at row {ref!r} "
                    f"(score={score}); the ordering must be the mechanical relevance sort"
                )
            prev_key = this_key

        # Optional pin: a real hint must rank a known preset at the top with a
        # minimum mechanical score (proving the mechanical match actually ranks).
        if expect_top_ref is not None:
            if not rows:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: expect_top_ref {expect_top_ref!r} "
                    "but ranked_rows is empty"
                )
            top = rows[0]
            if top.get("chain_preset_ref") != expect_top_ref:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: top ranked preset expected "
                    f"{expect_top_ref!r}, observed {top.get('chain_preset_ref')!r}"
                )
            if int(top.get("hint_match_score", -1)) < expect_min_top_score:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: top preset hint_match_score "
                    f"{top.get('hint_match_score')!r} < expect_min_top_score {expect_min_top_score}"
                )

        # scope filter: if a scope was declared, EVERY row must carry it.
        if catalog_scope is not None:
            offending = [
                row.get("chain_preset_ref")
                for row in rows
                if row.get("catalog_scope") != catalog_scope
            ]
            if offending:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: scope filter {catalog_scope!r} "
                    f"leaked off-scope presets {offending}"
                )

        # AXIS FIRE 1: NO pick/recommend field anywhere (top-level or per-row).
        # (rank / hint_match_score / ranked_rows are the LEGITIMATE mechanical
        # surface and are deliberately NOT forbidden.)
        top_hits = sorted(set(packet.keys()) & _PRESET_RANKING_FORBIDDEN_PICK_FIELDS)
        if top_hits:
            raise ProfileError(
                f"preset_ranking_packet_case rejected {label}: packet carries forbidden "
                f"pick/recommend field(s) at top level {top_hits}; the ranking is NON-BINDING "
                "and support must NEVER pick or recommend a preset"
            )
        for row in rows:
            row_hits = sorted(set(row.keys()) & _PRESET_RANKING_FORBIDDEN_PICK_FIELDS)
            if row_hits:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: ranked row "
                    f"{row.get('chain_preset_ref')!r} carries forbidden pick/recommend field(s) "
                    f"{row_hits}; the ranking is NON-BINDING"
                )

        # AXIS FIRE 2 (the biggest-unknown guard): even WITH this ranking
        # available, the materializer STILL hard-refuses a run with no/blank
        # chain_preset_ref. The ranking NEVER auto-applies. If the materializer
        # were made to fall back to the top-ranked preset, this goes RED.
        base_intent = {
            "declared_by": "coo",
            "task_source_ref": "brick/templates/tasks/source-template.md",
            "selected_adapter_ref": "adapter:codex-local",
            "write_scope": {
                "allowed_paths": ["support/operator/**"],
                "forbidden_paths": [".git/**"],
            },
        }
        for variant_name, variant in (
            ("omitted-chain-preset-ref", dict(base_intent)),
            ("blank-chain-preset-ref", dict(base_intent, chain_preset_ref="")),
        ):
            try:
                materialize_building_intent(variant, repo_root=repo)
            except ValueError:
                pass
            else:
                raise ProfileError(
                    f"preset_ranking_packet_case rejected {label}: materialize_building_intent did "
                    f"NOT raise for {variant_name}; with a ranking available the materializer MUST "
                    "still hard-refuse a run without an explicit confirmed preset (the ranking is "
                    "non-binding and must NEVER auto-apply the top-ranked preset)"
                )

        count += 1
    return count


def _canonical_chain_preset_refs(registry: Mapping[str, Any]) -> tuple[str, ...]:
    chain_presets = require_mapping(registry.get("chain_presets"), "shape registry chain_presets")
    refs = [
        str(ref)
        for ref, preset in chain_presets.items()
        if isinstance(ref, str)
        and isinstance(preset, Mapping)
        and preset.get("preset_ref") == ref
    ]
    return tuple(sorted(refs))


def _preset_completion_intent(
    *,
    label: str,
    building_id: str,
    task_source_ref: str,
    chain_preset_ref: str,
    selected_adapter_ref: str,
    selected_model_ref: str,
    write_scope: Mapping[str, Any],
    route_decision_basis: Mapping[str, Any],
) -> Mapping[str, Any]:
    return {
        "plan_ref": f"building-plan:{building_id}",
        "building_id": building_id,
        "declared_by": "coo",
        "task_source_ref": task_source_ref,
        "chain_preset_ref": chain_preset_ref,
        "selected_adapter_ref": selected_adapter_ref,
        "selected_model_ref": selected_model_ref,
        "write_scope": dict(write_scope),
        "route_decision_basis": dict(route_decision_basis),
        "proof_limits": [
            "all-presets completion checker support evidence only",
            "not real Slack delivery",
            "not provider behavior",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            f"semantic correctness of {label}",
            "real Slack delivery",
            "real provider behavior",
        ],
    }


def _run_preset_completion_portfolio(
    *,
    label: str,
    portfolio_ref: str,
    task_source_ref: str,
    selected_adapter_ref: str,
    selected_model_ref: str,
    write_scope: Mapping[str, Any],
    route_decision_basis: Mapping[str, Any],
    repo: Path,
    tmp: Path,
    output_root: Path,
    command_runner: Callable[..., Any],
    run_declared_portfolio: Callable[..., Any],
    materialize_building_intent: Callable[..., Mapping[str, Any]],
    observe_building_frontier: Callable[..., Mapping[str, Any]],
    expected_frontier: str,
) -> None:
    slug = _preset_slug(portfolio_ref)
    plan_dir = tmp / "portfolio-child-plans" / slug
    candidates: list[tuple[str, Path]] = []
    for index, child_suffix in enumerate(("a", "b"), start=1):
        child_building_id = f"{_case_slug(label)}-{slug}-child-{child_suffix}"
        child_plan = materialize_building_intent(
            _preset_completion_intent(
                label=label,
                building_id=child_building_id,
                task_source_ref=task_source_ref,
                chain_preset_ref="building-chain-preset:fast-fix",
                selected_adapter_ref=selected_adapter_ref,
                selected_model_ref=selected_model_ref,
                write_scope=write_scope,
                route_decision_basis=route_decision_basis,
            ),
            repo_root=repo,
        )
        plan_path = plan_dir / f"{child_suffix}.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(child_plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        candidates.append((f"building-boundary:{slug}-child-{child_suffix}", plan_path))

    candidate_refs = [candidate_ref for candidate_ref, _path in candidates]
    packet = {
        "portfolio_ref": f"portfolio:{_case_slug(label)}-{slug}",
        "declared_by": f"coo:{_case_slug(label)}",
        "mode": "static_order",
        # GATE WIRING (0611): the packet declares WHICH portfolio preset
        # declared this route, so the preset's gate_concept_profile review
        # tokens translate (single-source composition translation) onto the
        # terminal child's closing Link row -- asserted below.
        "chain_preset_ref": portfolio_ref,
        "route_decision_basis": dict(route_decision_basis),
        "candidate_buildings": [
            {
                "candidate_ref": candidate_ref,
                "building_plan_ref": str(path),
            }
            for candidate_ref, path in candidates
        ],
        "static_order": candidate_refs,
        "portfolio_transition_budget": {
            "owner_axis": "Link",
            "max_transitions": len(candidates),
        },
        "proof_limits": [
            "declared portfolio completion checker support evidence only",
            "not real Slack delivery",
            "not provider behavior",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            f"semantic correctness of {portfolio_ref}",
            "real multi-agent autonomy",
        ],
    }
    result = run_declared_portfolio(
        packet,
        repo_root=repo,
        output_root=output_root,
        portfolio_output_root=tmp / "portfolio-projections",
        overwrite_existing=True,
        command_runner=command_runner,
        adapter_cwd=repo,
        adapter_timeout_seconds=10,
    )
    if result.frontier_kind != expected_frontier:
        raise ProfileError(
            f"preset_building_completion_case rejected {label}/{portfolio_ref}: "
            f"portfolio frontier expected {expected_frontier!r}, observed {result.frontier_kind!r}"
        )
    observed_sequence = [str(row.get("candidate_ref")) for row in result.sequence]
    if observed_sequence != candidate_refs:
        raise ProfileError(
            f"preset_building_completion_case rejected {label}/{portfolio_ref}: "
            f"portfolio sequence mismatch"
        )
    for row in result.sequence:
        root = Path(str(row.get("child_evidence_root")))
        frontier = observe_building_frontier(root, repo_root=repo)
        if frontier.get("frontier_kind") != "complete":
            raise ProfileError(
                f"preset_building_completion_case rejected {label}/{portfolio_ref}: "
                f"child frontier observed {frontier.get('frontier_kind')!r}"
            )
        _assert_no_missing_gate_facts(root, label=f"{label}/{portfolio_ref}")

    # GATE WIRING (0611) backstop: the preset-declared review tokens must have
    # become REAL declared gates on the terminal child's closing Link row (the
    # portfolio closure boundary), with provenance naming the declaring preset.
    # Expected refs come from the SAME single-source composition translation,
    # so a bypassed/duplicated translation cannot drift past this assertion.
    from support.operator.composition import declared_portfolio_gate_translations

    expected_gate_refs = tuple(
        declared_portfolio_gate_translations(portfolio_ref, repo_root=repo)["gate_refs"]
    )
    if expected_gate_refs:
        stamp = result.projection.get("portfolio_gate_concept_translation")
        if not isinstance(stamp, Mapping) or tuple(
            stamp.get("stamped_gate_refs") or ()
        ) != expected_gate_refs:
            raise ProfileError(
                f"preset_building_completion_case rejected {label}/{portfolio_ref}: "
                f"projection portfolio_gate_concept_translation expected stamped "
                f"refs {expected_gate_refs!r}, observed {stamp!r}"
            )
        terminal_root = Path(str(result.sequence[-1].get("child_evidence_root")))
        recorded_plan_path = terminal_root / "work" / "declared-building-plan.json"
        recorded_packet = json.loads(recorded_plan_path.read_text(encoding="utf-8"))
        # The recorded file is the declaration packet; the walked plan body is
        # its declared_plan_copy (canonical JSON string or inline mapping).
        recorded_plan = recorded_packet.get("declared_plan_copy", recorded_packet)
        if isinstance(recorded_plan, str):
            recorded_plan = json.loads(recorded_plan)
        if not isinstance(recorded_plan, Mapping):
            raise ProfileError(
                f"preset_building_completion_case rejected {label}/{portfolio_ref}: "
                f"declared_plan_copy is not a plan mapping in {recorded_plan_path}"
            )
        row_groups = (
            recorded_plan.get("link_edges")
            if recorded_plan.get("plan_shape") == "graph"
            else recorded_plan.get("steps")
        )
        closing_rows = [
            row
            for group in (row_groups or [])
            if isinstance(group, Mapping)
            for row in (group.get("rows") or [])
            if isinstance(row, Mapping)
            and row.get("axis") == "Link"
            and isinstance(row.get("building_lifecycle"), Mapping)
            and row["building_lifecycle"].get("state") == "closed"
        ]
        stamped_closing = [
            row
            for row in closing_rows
            if all(ref in (row.get("declared_gate_refs") or []) for ref in expected_gate_refs)
            and isinstance(row.get("gate_concept_provenance"), Mapping)
            and row["gate_concept_provenance"].get("declared_by") == portfolio_ref
        ]
        if not stamped_closing:
            raise ProfileError(
                f"preset_building_completion_case rejected {label}/{portfolio_ref}: "
                f"terminal child closing Link row carries no translated portfolio "
                f"gates {expected_gate_refs!r} with provenance declared_by="
                f"{portfolio_ref!r} (recorded plan {recorded_plan_path})"
            )


def _preset_completion_command_runner(completed_cls: type[Any]) -> Callable[[Sequence[str], Path, int], Any]:
    def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int) -> Any:
        checked_args = tuple(str(arg) for arg in args)
        executable = Path(checked_args[0]).name if checked_args else ""
        if "--version" in checked_args:
            return completed_cls(
                args=checked_args,
                return_code=0,
                stdout=f"{executable or 'local-cli'} preset-completion-fixture 0.0\n",
                stderr="",
            )
        labels = _return_labels_from_cli_prompt(checked_args[-1] if checked_args else "")
        returned: dict[str, Any] = {}
        for label in labels:
            if label == "transition_concern_evidence":
                returned[label] = {
                    "concern_ref": "transition-concern:preset-completion-no-reroute",
                    "concern_kind": "unknown",
                    "binding": False,
                    "reason_refs": ["observation:preset-completion-no-reroute"],
                    "related_boundary_refs": ["building-boundary:preset-completion-no-reroute"],
                    "proof_limits": ["support evidence only"],
                    "not_proven": ["semantic correctness"],
                }
            elif label in _PRESET_COMPLETION_LIST_RETURN_FIELDS:
                returned[label] = _deterministic_completion_list(label, "preset-completion")
            else:
                returned[label] = f"{label}: deterministic preset completion evidence"
        returned.setdefault("observed_evidence", ["deterministic preset completion evidence"])
        returned.setdefault(
            "not_proven",
            ["semantic correctness", "real Slack delivery", "real provider behavior"],
        )
        assistant_text = json.dumps(returned, sort_keys=True)
        # TrackA-A1 FIXTURE FAITHFULNESS: real `codex exec --json` writes the
        # assistant text to the --output-last-message FILE and emits JSONL events on
        # stdout (the assistant payload is NOT on raw stdout). Model that here when
        # the invocation carries --output-last-message (codex): write the text to
        # the file, and put a terminal turn.completed usage event on stdout so the
        # meter side-channel is exercised. The adapter reads text from the file (it
        # must NEVER treat the JSONL stdout as assistant text). Non-codex
        # invocations (no --output-last-message) keep the plain-text stdout shape.
        output_path = _output_last_message_path(checked_args)
        if output_path is not None:
            Path(output_path).write_text(assistant_text, encoding="utf-8")
            stdout = (
                json.dumps(
                    {
                        "type": "turn.completed",
                        "usage": {
                            "input_tokens": 12,
                            "cached_input_tokens": 3,
                            "output_tokens": 4,
                            "reasoning_output_tokens": 5,
                        },
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        else:
            stdout = assistant_text
        return completed_cls(
            args=checked_args,
            return_code=0,
            stdout=stdout,
            stderr="",
        )

    return _runner


def _output_last_message_path(args: Sequence[str]) -> str | None:
    """Return the --output-last-message path from a codex invocation, else None."""
    args = list(args)
    for index, value in enumerate(args):
        if value == "--output-last-message" and index + 1 < len(args):
            return args[index + 1]
    return None


_PRESET_COMPLETION_LIST_RETURN_FIELDS = frozenset(
    {
        "agent_axis_findings",
        "attacked_scope",
        "attacked_work",
        "axis_responsibility",
        "blocked_or_missing_evidence",
        "boundary_findings",
        "boundary_violations",
        "brick_axis_findings",
        "candidate_file_changes",
        "changed_files",
        "checked_sources",
        "checker_or_verifier_plan",
        "checker_overclaim_risks",
        "commands_run",
        "deferred_smith_review_queue",
        "edge_cases",
        "evidence_refs",
        "evidence_scope",
        "evidence_used",
        "failing_or_missing_probes",
        "handoff_refs",
        "integration_risks",
        "invariants",
        "link_axis_findings",
        "made_changes",
        "matched_facts",
        "missing_evidence",
        "missing_facts",
        "missing_or_mismatched_facts",
        "mismatched_facts",
        "narrowly_proven",
        "negative_probe_observations",
        "next_target_candidates",
        "not_proven",
        "observed_evidence",
        "observed_matches",
        "open_questions",
        "persisted_evidence_roots",
        "projection_authority_findings",
        "proof_limit_findings",
        "proof_limits",
        "proposed_changes",
        "regression_risks",
        "relevant_current_structure",
        "remaining_delta",
        "required_outputs",
        "review_needed",
        "risk_boundaries",
        "risks",
        "source_fact_bodies",
        "stale_source_risks",
        "support_leak_findings",
        "unchanged_surfaces",
        "worker_assignments",
    }
)

_PRESET_COMPLETION_REPO_ARTIFACT_FIELDS = frozenset(
    {
        "checked_sources",
        "evidence_refs",
        "evidence_used",
        "relevant_current_structure",
    }
)


def _deterministic_completion_list(label: str, source: str) -> list[str]:
    if label in _PRESET_COMPLETION_REPO_ARTIFACT_FIELDS:
        return [
            f"{label}: {source} deterministic evidence from support/checkers/lib/case_runners.py"
        ]
    return [f"{label}: {source} deterministic evidence"]


def _return_labels_from_cli_prompt(prompt: str) -> tuple[str, ...]:
    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, Mapping):
        return ()
    labels = payload.get("required_return_labels")
    if not isinstance(labels, Sequence) or isinstance(labels, (str, bytes)):
        return ()
    return tuple(str(label).strip() for label in labels if str(label).strip())


def _assert_no_missing_gate_facts(root: Path, *, label: str) -> None:
    for path in _gate_evidence_paths(root):
        for record in _json_records(path):
            for trail, value in _nested_values_for_key(record, "missing_required_facts"):
                if isinstance(value, list) and value:
                    raise ProfileError(
                        f"preset_building_completion_case rejected {label}: "
                        f"{path.relative_to(root)} {'.'.join(trail)} has missing_required_facts"
                    )


def _assert_missing_gate_fact_present(
    root: Path,
    *,
    expected_missing_fact: str,
    label: str,
) -> None:
    """Assert the written gate evidence records EXACTLY the expected missing fact.

    Companion to _assert_no_missing_gate_facts for declared-HOLD cases: the
    walk paused because a declared review gate's disposition fact is absent,
    so that fact (and only facts naming it) must appear under
    missing_required_facts in the persisted gate evidence.
    """

    observed: set[str] = set()
    for path in _gate_evidence_paths(root):
        for record in _json_records(path):
            for _trail, value in _nested_values_for_key(record, "missing_required_facts"):
                if isinstance(value, list):
                    observed.update(str(item) for item in value)
    if expected_missing_fact not in observed:
        raise ProfileError(
            f"building_intake_seam_case rejected {label}: expected missing fact "
            f"{expected_missing_fact!r} not recorded; observed {sorted(observed)!r}"
        )
    unexpected = {item for item in observed if item != expected_missing_fact}
    if unexpected:
        raise ProfileError(
            f"building_intake_seam_case rejected {label}: hold recorded UNRELATED "
            f"missing facts {sorted(unexpected)!r} (expected only {expected_missing_fact!r})"
        )


def _gate_evidence_paths(root: Path) -> tuple[Path, ...]:
    paths = [root / "raw" / "link.jsonl"]
    paths.extend(sorted((root / "work" / "step-outputs").glob("*/step-output.json")))
    return tuple(path for path in paths if path.is_file())


def _json_records(path: Path) -> tuple[Mapping[str, Any], ...]:
    records: list[Mapping[str, Any]] = []
    if path.suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, Mapping):
                records.append(value)
        return tuple(records)
    value = json.loads(path.read_text(encoding="utf-8"))
    return (value,) if isinstance(value, Mapping) else ()


def _nested_values_for_key(value: Any, key: str, trail: tuple[str, ...] = ()) -> tuple[tuple[tuple[str, ...], Any], ...]:
    found: list[tuple[tuple[str, ...], Any]] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            child_trail = (*trail, str(raw_key))
            if raw_key == key:
                found.append((child_trail, child))
            found.extend(_nested_values_for_key(child, key, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_nested_values_for_key(child, key, (*trail, str(index))))
    return tuple(found)


def _preset_slug(preset_ref: str) -> str:
    return _case_slug(preset_ref.split(":", 1)[-1])


def _case_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "case"


def _split_ref_row(value: Any) -> list[str]:
    """One per-row expectation: a comma-joined ref string -> ordered ref list."""

    if not isinstance(value, str):
        raise ProfileError(
            f"per-row gate expectation must be a comma-joined string, got {value!r}"
        )
    return [part.strip() for part in value.split(",") if part.strip()]


def _link_rows_list_field(plan: Mapping[str, Any], key: str) -> list[list[Any]]:
    """Per-Link-row LIST field values in declared row order (both plan shapes).

    Linear plans iterate steps[].rows; graph plans iterate link_edges[].rows.
    A Link row without the field contributes [] so per-row assertions can pin
    ABSENCE as exactly as presence.
    """

    sources = (
        plan.get("link_edges", [])
        if plan.get("plan_shape") == "graph"
        else plan.get("steps", [])
    )
    observed: list[list[Any]] = []
    for item_value in sources or []:
        if not isinstance(item_value, Mapping):
            continue
        for row in item_value.get("rows", []):
            if isinstance(row, Mapping) and row.get("axis") == "Link":
                value = row.get(key)
                observed.append(list(value) if isinstance(value, list) else [])
    return observed


def _materialized_step_values(plan: Mapping[str, Any], key: str) -> list[str]:
    sources = (
        plan.get("brick_steps", [])
        if plan.get("plan_shape") == "graph"
        else plan.get("steps", [])
    )
    return [
        str(step.get(key))
        for step in sources or []
        if isinstance(step, Mapping) and step.get(key) is not None
    ]


def _link_rows_in_declared_order(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Every Link row in declared row order (both plan shapes)."""

    sources = (
        plan.get("link_edges", [])
        if plan.get("plan_shape") == "graph"
        else plan.get("steps", [])
    )
    rows: list[Mapping[str, Any]] = []
    for item_value in sources or []:
        if not isinstance(item_value, Mapping):
            continue
        for row in item_value.get("rows", []):
            if isinstance(row, Mapping) and row.get("axis") == "Link":
                rows.append(row)
    return rows


def _link_rows_provenance_tokens(plan: Mapping[str, Any], label: str) -> list[list[str]]:
    """Per-Link-row gate_concept_provenance token lists (A1/A4 FIRE reader).

    A row WITHOUT the field contributes [] (absence pinned exactly like
    presence). A row WITH the field must carry a well-formed non-empty tokens
    list -- a present-but-empty/malformed provenance is REJECTED here instead
    of aliasing to absence (a malformed stamp must never look like "no stamp").
    """

    observed: list[list[str]] = []
    for row in _link_rows_in_declared_order(plan):
        if "gate_concept_provenance" not in row:
            observed.append([])
            continue
        provenance = row.get("gate_concept_provenance")
        if not isinstance(provenance, Mapping):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"gate_concept_provenance must be a mapping, got {provenance!r}"
            )
        tokens = provenance.get("tokens")
        if (
            not isinstance(tokens, list)
            or not tokens
            or not all(isinstance(token, str) and token.strip() for token in tokens)
        ):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"gate_concept_provenance.tokens must be a non-empty string list, "
                f"got {tokens!r}"
            )
        observed.append([token.strip() for token in tokens])
    return observed


def _link_rows_provenance_declared_by(plan: Mapping[str, Any], label: str) -> list[str]:
    """declared_by values of every provenance-carrying Link row (A4 FIRE reader)."""

    observed: list[str] = []
    for row in _link_rows_in_declared_order(plan):
        if "gate_concept_provenance" not in row:
            continue
        provenance = row.get("gate_concept_provenance")
        if not isinstance(provenance, Mapping):
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"gate_concept_provenance must be a mapping, got {provenance!r}"
            )
        declared_by = provenance.get("declared_by")
        if not isinstance(declared_by, str) or not declared_by.strip():
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: "
                f"gate_concept_provenance.declared_by must be non-empty text, "
                f"got {declared_by!r}"
            )
        observed.append(declared_by.strip())
    return observed


def _observed_link_row_values(plan: Mapping[str, Any], key: str) -> list[str]:
    sources = plan.get("link_edges", []) if plan.get("plan_shape") == "graph" else plan.get("steps", [])
    observed: list[str] = []
    for item_value in sources or []:
        if not isinstance(item_value, Mapping):
            continue
        for row in item_value.get("rows", []):
            if isinstance(row, Mapping) and row.get("axis") == "Link":
                observed.append(str(row.get(key)))
    return observed


def _check_materialize_building_declaration_evidence(
    building_root: Path,
    *,
    expected: Mapping[str, Any],
    label: str,
) -> None:
    work_files = require_string_list(
        expected.get("work_files", []),
        "materialize_building_intent_case.expected.declaration_evidence.work_files",
    )
    for relative in work_files:
        if not (building_root / relative).is_file():
            raise ProfileError(
                f"materialize_building_intent_case rejected {label}: missing declaration evidence {relative}"
            )
    intake = json.loads((building_root / "work" / "building-intake.json").read_text(encoding="utf-8"))
    if expected.get("task_source_hash_state") and intake.get("task_source_hash_state") != expected.get(
        "task_source_hash_state"
    ):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: "
            f"task_source_hash_state expected {expected.get('task_source_hash_state')!r}, "
            f"observed {intake.get('task_source_hash_state')!r}"
        )
    if expected.get("task_source_hash_present") and not intake.get("task_source_hash"):
        raise ProfileError(
            f"materialize_building_intent_case rejected {label}: intake task_source_hash missing"
        )
    preset_expansion = json.loads(
        (building_root / "work" / "preset-expansion.json").read_text(encoding="utf-8")
    )
    _check_declaration_ref_expectations(
        preset_expansion,
        expected,
        label=label,
        case_name="materialize_building_intent_case",
    )


def _check_declaration_ref_expectations(
    observed_packet: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    label: str,
    case_name: str,
) -> None:
    for key, noun in (
        ("expanded_step_template_refs", "step template"),
        ("expanded_brick_spec_refs", "Brick spec"),
        ("expanded_brick_template_refs", "Brick return template"),
    ):
        required = set(
            require_string_list(
                expected.get(key, []),
                f"{case_name}.expected.declaration_evidence.{key}",
            )
        )
        if not required:
            continue
        observed = {
            str(item)
            for item in observed_packet.get(key, [])
            if isinstance(item, str)
        }
        missing = sorted(required - observed)
        if missing:
            raise ProfileError(
                f"{case_name} rejected {label}: missing {noun} provenance {missing}"
            )


def run_declared_step_template_plan_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "declared_step_template_plan_case")
    if not items:
        return 0
    from support.operator.building_operation import render_declared_step_template_plan
    count = 0
    for item in items:
        mapping = require_mapping(item, "declared_step_template_plan_case item")
        case, relative = _profile_case_document(repo, mapping, "declared_step_template_plan_case")
        rendered = render_declared_step_template_plan(case, repo_root=repo)
        expected = require_mapping(mapping.get("expected", {}), "declared_step_template_plan_case.expected")
        steps = rendered.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ProfileError(f"declared_step_template_plan_case rejected {relative}: no rendered steps")
        rows = require_mapping(steps[0], f"{relative}: steps[0]").get("rows")
        if not isinstance(rows, list):
            raise ProfileError(f"declared_step_template_plan_case rejected {relative}: rows missing")
        link_rows = [row for row in rows if isinstance(row, Mapping) and row.get("axis") == "Link"]
        if len(link_rows) != 1:
            raise ProfileError(f"declared_step_template_plan_case rejected {relative}: Link row missing")
        link_row = link_rows[0]
        for key in ("movement", "target_ref"):
            if key in expected and link_row.get(key) != expected[key]:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: "
                    f"{key} expected {expected[key]!r}, observed {link_row.get(key)!r}"
                )
        if "declared_gate_refs" in expected and link_row.get("declared_gate_refs") != expected["declared_gate_refs"]:
            raise ProfileError(
                f"declared_step_template_plan_case rejected {relative}: declared_gate_refs mismatch"
            )
        step = require_mapping(steps[0], f"{relative}: steps[0]")
        for key in ("selected_adapter_ref", "selected_model_ref"):
            if key in expected and step.get(key) != expected[key]:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: "
                    f"{key} expected {expected[key]!r}, observed {step.get(key)!r}"
                )
        # Optional: assert the stamped Agent row (proves a same-NEED author override
        # changes the agent the linear path stamps -- finding-2 regression net).
        if "agent_object_ref" in expected:
            agent_rows = [row for row in rows if isinstance(row, Mapping) and row.get("axis") == "Agent"]
            if len(agent_rows) != 1:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: Agent row missing"
                )
            observed_agent = agent_rows[0].get("agent_object_ref")
            if observed_agent != expected["agent_object_ref"]:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: "
                    f"agent_object_ref expected {expected['agent_object_ref']!r}, observed {observed_agent!r}"
                )
        count += 1
    return count


def run_declared_step_template_plan_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "declared_step_template_plan_rejects")
    if not items:
        return 0
    from support.operator.building_operation import render_declared_step_template_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "declared_step_template_plan_rejects item")
        case, relative = _profile_case_document(repo, mapping, "declared_step_template_plan_rejects")
        expected_message = str(mapping.get("expected_message", "") or "")
        try:
            render_declared_step_template_plan(case, repo_root=repo)
        except (TypeError, ValueError) as exc:
            if expected_message and expected_message not in str(exc):
                raise ProfileError(
                    f"declared_step_template_plan_rejects rejected {relative}: "
                    f"expected message {expected_message!r}, observed {exc}"
                ) from exc
            count += 1
            continue
        raise ProfileError(f"declared_step_template_plan_rejects expected rejection but passed: {relative}")
    return count


def run_compose_building_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "compose_building_case")
    if not items:
        return 0
    from support.operator.building_operation import compose_building, observe_building_frontier
    from support.operator.plan_graph import _linear_plan_from_graph_plan
    from support.operator.plan_validation import validate_declared_building_plan
    from support.operator.run import run_building_plan

    # FAIL-CLOSED provenance probe (Smith ruling): a route-policy value with ABSENT
    # provenance must be REJECTED by _composition_resolve_route_policy_provenance,
    # NOT auto-labeled per-building. This probes the resolver guard DIRECTLY (the
    # compose_building direct-caller intake stamps per-building EXPLICITLY before the
    # resolver sees it, so the guard itself is the only thing rejecting a truly
    # unprovenanced value). The legitimate constitutional-default | preset-default |
    # per-building paths still resolve verbatim. Revert the guard (back to
    # `return "per-building"` for
    # absent/blank) and this probe goes RED.
    from support.operator.composition import _composition_resolve_route_policy_provenance

    for absent in (None, "", "   "):
        try:
            _composition_resolve_route_policy_provenance(
                "probe-node", "node_reroute_budget", absent
            )
        except ValueError:
            pass
        else:
            raise ProfileError(
                "compose_building_case provenance probe: absent/blank route-policy "
                f"provenance ({absent!r}) was not REJECTED fail-closed (it must not "
                "be auto-labeled per-building)"
            )
    for human in ("constitutional-default", "preset-default", "per-building"):
        if _composition_resolve_route_policy_provenance(
            "probe-node", "node_reroute_budget", human
        ) != human:
            raise ProfileError(
                "compose_building_case provenance probe: legitimate HUMAN provenance "
                f"{human!r} was not resolved verbatim"
            )
    try:
        _composition_resolve_route_policy_provenance(
            "probe-node", "node_reroute_budget", "support"
        )
    except ValueError:
        pass
    else:
        raise ProfileError(
            "compose_building_case provenance probe: route-policy provenance "
            "'support' was not REJECTED fail-closed"
        )

    # FAIL-CLOSED Movement-action probe (Smith ruling, same axis-law as provenance):
    # a closure_transition_target_policy row that declares a target_ref but NO explicit
    # action/disposition must NOT have its Movement action INVENTED. support must record
    # the absence (return ""), not infer "target" from the presence of a target_ref.
    # The consumer (_composition_closure_transition_target_policy_problems) then FAILS
    # CLOSED on the empty action ("policy action must be hold or target"). Re-add the
    # `if _composition_policy_target_ref(policy_row): return "target"` fallback and this
    # probe goes RED (support invents the action and the target-without-action row is
    # silently accepted). The explicit-action paths still resolve verbatim.
    from support.operator.composition import _composition_policy_action

    inferred = _composition_policy_action(
        {"target_ref": "building-step-template:work"}
    )
    if inferred != "":
        raise ProfileError(
            "compose_building_case policy-action probe: a closure_transition_target_policy "
            "row with a target_ref but NO explicit action must FAIL CLOSED (return ''), "
            f"but support INVENTED a Movement action {inferred!r} from the target_ref alone"
        )
    for declared in ("target", "hold", "reroute"):
        for key in ("action", "disposition", "disposition_action"):
            resolved = _composition_policy_action(
                {key: declared, "target_ref": "building-step-template:work"}
            )
            if resolved != declared:
                raise ProfileError(
                    "compose_building_case policy-action probe: explicit "
                    f"{key}={declared!r} must resolve verbatim, observed {resolved!r}"
                )

    count = 0
    for item in items:
        mapping = require_mapping(item, "compose_building_case item")
        case, relative = _profile_case_document(repo, mapping, "compose_building_case")
        plan = _compose_building_profile_plan(case, repo)
        try:
            linear_plan, _graph_context = _linear_plan_from_graph_plan(plan)
            validate_declared_building_plan(linear_plan, repo_root=repo)
        except (TypeError, ValueError) as exc:
            raise ProfileError(f"compose_building_case rejected {relative}: {exc}") from exc
        expected = require_mapping(mapping.get("expected", {}), "compose_building_case.expected")
        if expected.get("plan_shape") and plan.get("plan_shape") != expected.get("plan_shape"):
            raise ProfileError(
                f"compose_building_case rejected {relative}: plan_shape mismatch"
            )
        if expected.get("selected_adapter_ref") and plan.get("selected_adapter_ref") != expected.get("selected_adapter_ref"):
            raise ProfileError(
                f"compose_building_case rejected {relative}: selected_adapter_ref mismatch"
            )
        if expected.get("chain_preset_ref") and plan.get("chain_preset_ref") != expected.get(
            "chain_preset_ref"
        ):
                raise ProfileError(
                    f"compose_building_case rejected {relative}: chain_preset_ref mismatch"
                )
        expected_movements = require_string_list(
            expected.get("movements", []),
            "compose_building_case.expected.movements",
        )
        if expected_movements:
            observed_movements = _observed_link_row_values(plan, "movement")
            if observed_movements != expected_movements:
                raise ProfileError(
                    f"compose_building_case rejected {relative}: "
                    f"movements expected {expected_movements!r}, observed {observed_movements!r}"
                )
        expected_gate_refs = expected.get("declared_gate_refs")
        if isinstance(expected_gate_refs, list):
            observed = [
                edge.get("rows", [{}])[0].get("declared_gate_refs")
                for edge in plan.get("link_edges", [])
                if isinstance(edge, Mapping)
            ]
            if expected_gate_refs not in observed:
                raise ProfileError(
                    f"compose_building_case rejected {relative}: expected gate refs not observed"
                )
        expected_gate_sequence_policy_gate_refs = expected.get(
            "gate_sequence_policy_gate_refs"
        )
        if isinstance(expected_gate_sequence_policy_gate_refs, list):
            observed_sequences = [
                [
                    item.get("gate_ref")
                    for item in edge.get("rows", [{}])[0].get(
                        "gate_sequence_policy",
                        [],
                    )
                    if isinstance(item, Mapping)
                ]
                for edge in plan.get("link_edges", [])
                if isinstance(edge, Mapping)
                and isinstance(edge.get("rows", [{}])[0], Mapping)
            ]
            if expected_gate_sequence_policy_gate_refs not in observed_sequences:
                raise ProfileError(
                    f"compose_building_case rejected {relative}: expected gate_sequence_policy gate refs not observed"
                )
        expected_frontier = expected.get("frontier_kind")
        if expected_frontier:
            with tempfile.TemporaryDirectory(prefix="bp-compose-building-case-") as tmpdir:
                result = run_building_plan(
                    plan,
                    output_root=Path(tmpdir),
                    overwrite_existing=True,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _compose_building_ok_callable
                    },
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
                frontier = observe_building_frontier(result.lifecycle_write.root, repo_root=repo)
                _check_compose_building_declaration_evidence(
                    result.lifecycle_write.root,
                    expected=require_mapping(
                        expected.get("declaration_evidence", {}),
                        "compose_building_case.expected.declaration_evidence",
                    ),
                    label=relative,
                )
            if frontier.get("frontier_kind") != expected_frontier:
                raise ProfileError(
                    f"compose_building_case rejected {relative}: frontier_kind "
                    f"expected {expected_frontier!r}, observed {frontier.get('frontier_kind')!r}"
                )
        count += 1
    return count


def _check_compose_building_declaration_evidence(
    building_root: Path,
    *,
    expected: Mapping[str, Any],
    label: str,
) -> None:
    if not expected:
        return
    work_files = require_string_list(
        expected.get("work_files", []),
        "compose_building_case.expected.declaration_evidence.work_files",
    )
    for relative in work_files:
        if not (building_root / relative).is_file():
            raise ProfileError(
                f"compose_building_case rejected {label}: missing declaration evidence {relative}"
            )
    building_map = json.loads((building_root / "work" / "building-map.json").read_text(encoding="utf-8"))
    provenance = require_mapping(
        building_map.get("declaration_provenance"),
        "work/building-map.json.declaration_provenance",
    )
    selected_shape_ref = expected.get("selected_shape_ref")
    if selected_shape_ref and provenance.get("selected_shape_ref") != selected_shape_ref:
        raise ProfileError(
            f"compose_building_case rejected {label}: building-map selected_shape_ref provenance mismatch"
        )
    _check_declaration_ref_expectations(
        provenance,
        expected,
        label=label,
        case_name="compose_building_case",
    )
    declared_plan = json.loads(
        (building_root / "work" / "declared-building-plan.json").read_text(encoding="utf-8")
    )
    declared_copy = require_mapping(
        declared_plan.get("declared_plan_copy"),
        "work/declared-building-plan.json.declared_plan_copy",
    )
    if expected.get("plan_shape") and declared_copy.get("plan_shape") != expected.get("plan_shape"):
        raise ProfileError(
            f"compose_building_case rejected {label}: declared plan copy plan_shape mismatch"
        )


def run_compose_building_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "compose_building_rejects")
    if not items:
        return 0
    from support.operator.building_operation import CompositionError

    count = 0
    for item in items:
        mapping = require_mapping(item, "compose_building_rejects item")
        case, relative = _profile_case_document(repo, mapping, "compose_building_rejects")
        expected_codes = _compose_building_expected_codes(mapping)
        min_problem_count = _optional_positive_int(
            mapping.get("min_problem_count"),
            "compose_building_rejects.min_problem_count",
        )
        try:
            _compose_building_profile_plan(case, repo)
        except CompositionError as exc:
            observed_codes = [problem.code for problem in exc.problems]
            missing = [code for code in expected_codes if code not in observed_codes]
            if missing:
                raise ProfileError(
                    f"compose_building_rejects rejected {relative}: "
                    f"expected code(s) {missing}, observed {observed_codes}"
                ) from exc
            if min_problem_count is not None and len(observed_codes) < min_problem_count:
                raise ProfileError(
                    f"compose_building_rejects rejected {relative}: "
                    f"expected at least {min_problem_count} problems, observed {len(observed_codes)}"
                ) from exc
            count += 1
            continue
        except ValueError as exc:
            raise ProfileError(
                f"compose_building_rejects expected CompositionError for {relative}, observed {type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError(f"compose_building_rejects expected rejection but passed: {relative}")
    return count


def run_gate_sequence_policy_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "gate_sequence_policy_case")
    if not items:
        return 0
    from support.operator.plan_validation import _validate_gate_sequence_policy_for_link_row

    count = 0
    for item in items:
        mapping = require_mapping(item, "gate_sequence_policy_case item")
        case, relative = _profile_case_document(repo, mapping, "gate_sequence_policy_case")
        try:
            _validate_gate_sequence_policy_for_link_row(
                _gate_sequence_policy_link_row(case),
                **_gate_sequence_policy_context(case),
            )
        except (TypeError, ValueError) as exc:
            raise ProfileError(
                f"gate_sequence_policy_case rejected {relative}: {exc}"
            ) from exc
        count += 1
    return count


def run_gate_sequence_policy_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "gate_sequence_policy_rejects")
    if not items:
        return 0
    from support.operator.plan_validation import _validate_gate_sequence_policy_for_link_row

    count = 0
    for item in items:
        mapping = require_mapping(item, "gate_sequence_policy_rejects item")
        case, relative = _profile_case_document(repo, mapping, "gate_sequence_policy_rejects")
        expected_message = str(mapping.get("expected_message", "") or "")
        try:
            _validate_gate_sequence_policy_for_link_row(
                _gate_sequence_policy_link_row(case),
                **_gate_sequence_policy_context(case),
            )
        except (TypeError, ValueError) as exc:
            if expected_message and expected_message not in str(exc):
                raise ProfileError(
                    f"gate_sequence_policy_rejects rejected {relative}: "
                    f"expected message {expected_message!r}, observed {exc}"
                ) from exc
            count += 1
            continue
        raise ProfileError(
            f"gate_sequence_policy_rejects expected rejection but passed: {relative}"
        )
    return count


def run_building_lifecycle_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "building_lifecycle_case")
    if not items:
        return 0
    from support.operator.plan_validation import (
        _validate_building_lifecycle_for_link_row,
        _validate_transition_lifecycle_for_link_row,
    )

    count = 0
    for item in items:
        mapping = require_mapping(item, "building_lifecycle_case item")
        case, relative = _profile_case_document(repo, mapping, "building_lifecycle_case")
        link_row = _gate_sequence_policy_link_row(case)
        try:
            _validate_building_lifecycle_for_link_row(link_row)
            _validate_transition_lifecycle_for_link_row(link_row)
        except (TypeError, ValueError) as exc:
            raise ProfileError(
                f"building_lifecycle_case rejected {relative}: {exc}"
            ) from exc
        count += 1
    return count


def run_building_lifecycle_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    # G5 S1 (gap seal) negative probe: a Link row that DIRECTLY declares a stop
    # state (building_lifecycle.state: waiting / transition_lifecycle.state:
    # paused) WITHOUT a HOLD-causing gate_sequence_policy on the same row would
    # be walked through by the graph walker (walker_kernel) where the linear
    # walker (run.py 1461/1469) breaks. validate_declared_building_plan MUST
    # reject it; this probe RED-flags any regression that drops the invariant.
    items = rule_items(profile, "building_lifecycle_rejects")
    if not items:
        return 0
    from support.operator.plan_validation import (
        _validate_building_lifecycle_for_link_row,
        _validate_transition_lifecycle_for_link_row,
    )

    count = 0
    for item in items:
        mapping = require_mapping(item, "building_lifecycle_rejects item")
        case, relative = _profile_case_document(repo, mapping, "building_lifecycle_rejects")
        expected_message = str(mapping.get("expected_message", "") or "")
        link_row = _gate_sequence_policy_link_row(case)
        try:
            _validate_building_lifecycle_for_link_row(link_row)
            _validate_transition_lifecycle_for_link_row(link_row)
        except (TypeError, ValueError) as exc:
            if expected_message and expected_message not in str(exc):
                raise ProfileError(
                    f"building_lifecycle_rejects rejected {relative}: "
                    f"expected message {expected_message!r}, observed {exc}"
                ) from exc
            count += 1
            continue
        raise ProfileError(
            f"building_lifecycle_rejects expected rejection but passed: {relative}"
        )
    return count


def run_native_dispatch_close_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """FIRE the two native-dispatch close governance guards via real open/close.

    For each declared item (a marker; no required fields) this drives the real
    open_native_dispatch_brick -> close_native_dispatch_brick seam against a TEMP
    output_root and asserts these behaviours that RED the holes and GREEN the fix:

      (1) HOLE A (forced verdict, observed_match_kind): close with a
          comparison_observation carrying observed_match_kind="matched" while
          `returned` is MISSING required fields MUST raise ValueError. ANY caller
          comparison_observation is now rejected outright.
      (1b) HOLE A (forced verdict, comparison_evidence): close with a
          comparison_observation carrying comparison_evidence (e.g.
          ["missing_return_fields: none"]) over a return MISSING required fields
          MUST raise ValueError. The gate sufficiency is driven by
          missing_return_fields parsed from comparison_evidence, NOT by
          observed_match_kind, so a fix that rejected only observed_match_kind
          would let THIS forge a "sufficient" gate. This case proves the fix
          rejects the WHOLE observation: before the fix it produced gate
          sufficiency="sufficient"; now it RAISES.
      (2) HOLE B (smuggled Movement, no basis): close with movement="reroute" and
          EMPTY route_decision_basis MUST raise ValueError.
      (3) HOLE B (smuggled Movement, non-CoO ref): close with movement="reroute"
          by a NON-CoO ref MUST raise ValueError even WITH a basis. Covers both a
          worker-lane ref (agent-object:dev) AND a *-lead ref (agent-object:cto-
          lead) -- the *-lead shares lane="leader" with the CoO, so a lane check
          would WRONGLY admit it; only the agent-object:coo ref is authorized.
      (4) POSITIVE (real successful close over a FRESH building tree): the
          governance guards must NOT over-block legitimate inputs, AND a
          legitimate close must actually COMPLETE and produce a building. A
          forward close (default, agent-object:dev) and a legit reroute
          (agent-object:coo + non-empty basis) must each:
            - NOT raise (no guard ValueError, and -- since the steps regression
              is fixed -- no SpineProjectionError either);
            - return a building_root that is a real directory on disk;
            - record execution_path=native-dispatch;
            - have written work/declared-building-plan.json whose
              declared_plan_copy.steps is a NON-EMPTY JSON list (the exact shape
              whose absence used to RAISE SpineProjectionError);
            - record the expected movement / lane / basis / COMPUTED (never
              forced "matched") comparison.
          This case REDs if a guard wrongly rejects a legitimate forward/reroute
          OR if a fresh close fails to produce a steps-bearing building tree.
      (6) B4-REPAIR defect 1 (0611): harness-envelope tolerance BOTH ways --
          the extracted content of a live-shaped Agent tool_result envelope
          (carrying 'status' + metadata) must close successfully; an
          unknown-shape envelope must fall back to ONE raw JSON string that
          closes; and a Mapping carrying 'status' passed DIRECTLY as returned
          must STILL be rejected (the closed RETURNED_FORBIDDEN_KEYS set was
          NOT opened).
      (7) B4-REPAIR defect 2 (0611): the closed building must record
          declaration_provenance.composition_mode == the single-sourced engine
          linear literal (composition.LINEAR_COMPOSITION_MODE) and pass the
          REAL check_building_declaration_integrity validator.

    HISTORY: a prior baseline made ANY live native-dispatch close raise
    SpineProjectionError at write_accumulated_building_evidence, because the
    close plan declared no declared_plan_copy.steps while the spine projector
    requires them. That regression hid behind the STALE on-disk posA proof
    building (validated by the structural rules; never re-closed). This case now
    runs a FRESH open->close to a temp output_root and asserts the close
    SUCCEEDS, so that regression class can no longer hide behind a stale
    artifact.
    """

    items = rule_items(profile, "native_dispatch_close_case")
    if not items:
        return 0
    from support.operator.building_operation import (
        close_native_dispatch_brick,
        open_native_dispatch_brick,
    )
    # Import from the canonical brick_protocol.* package path so the caught type
    # is the SAME class object that evidence_assembly raises (the support.* alias
    # is a DIFFERENT class under this repo's dual import-identity, and would not
    # match the except clause).
    from brick_protocol.support.recording.spine_projection import SpineProjectionError

    count = 0
    for item in items:
        mapping = require_mapping(item, "native_dispatch_close_case item")
        label = require_string(
            mapping.get("label", "native-dispatch-close"),
            "native_dispatch_close_case.label",
        )
        slug = _case_slug(label)
        # A return that is MISSING the required fields, so the COMPUTED Brick
        # comparison can never be "match". This is the lever the forced verdict
        # would override.
        missing_return = {"unrelated_field": "no required fields present"}
        ok_return = {"observed_evidence": "present", "not_proven": "documented"}

        def _open(building_id: str, agent_object_ref: str, output_root: Path):
            return open_native_dispatch_brick(
                building_id=building_id,
                received_work=f"{label}: native dispatch work",
                required_return_shape="observed_evidence, not_proven",
                agent_object_ref=agent_object_ref,
                declared_gate_refs=["link-gate:default-transition"],
                output_root=output_root,
                overwrite_existing=True,
            )

        with tempfile.TemporaryDirectory(prefix=f"bp-native-dispatch-close-{slug}-") as tmpdir:
            output_root = Path(tmpdir) / "buildings"

            # (1) HOLE A: ANY caller comparison_observation MUST be rejected by the
            # GUARD. observed_match_kind="matched" over a return MISSING the
            # required fields is one forced verdict; the guard now rejects the
            # WHOLE observation before the comparison is built. The assertion pins
            # the GUARD's SPECIFIC message ("caller comparison_observation is not
            # admitted"), so a downstream rejection (different type/message) does
            # NOT masquerade as the guard firing: if the guard is removed, this
            # case REDs (the close raises SpineProjectionError, not this
            # ValueError, and is not caught).
            _GUARD_A_MSG = "caller comparison_observation is not admitted"
            handle_a = _open(f"{slug}-forced-verdict", "agent-object:dev", output_root)
            try:
                close_native_dispatch_brick(
                    handle_a,
                    returned=missing_return,
                    movement="forward",
                    comparison_observation={"observed_match_kind": "matched"},
                )
            except ValueError as exc:
                if _GUARD_A_MSG not in str(exc):
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: forced-verdict "
                        f"was NOT rejected by guard A (expected message "
                        f"{_GUARD_A_MSG!r}); observed: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: HOLE A OPEN -- "
                    "close admitted a caller-forced observed_match_kind"
                )

            # (1b) HOLE A (the REAL P0 lever): a comparison_observation carrying
            # comparison_evidence=["missing_return_fields: none"] over a return
            # MISSING required fields MUST be rejected. The Link gate sufficiency
            # is driven by missing_return_fields parsed from comparison_evidence,
            # NOT by observed_match_kind, so a fix rejecting only
            # observed_match_kind would let THIS forge a "sufficient" gate (it did,
            # before the fix). Same pinned guard message: the WHOLE observation is
            # rejected. If the reject is narrowed back to observed_match_kind-only,
            # this close would SUCCEED with a forged "sufficient" gate and this
            # case REDs (else-branch fires).
            handle_a2 = _open(f"{slug}-spoof-evidence", "agent-object:dev", output_root)
            try:
                close_native_dispatch_brick(
                    handle_a2,
                    returned=missing_return,
                    movement="forward",
                    comparison_observation={
                        "comparison_evidence": ["missing_return_fields: none"]
                    },
                )
            except ValueError as exc:
                if _GUARD_A_MSG not in str(exc):
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: spoofed "
                        f"comparison_evidence was NOT rejected by guard A (expected "
                        f"message {_GUARD_A_MSG!r}); observed: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: HOLE A OPEN -- "
                    "close admitted a caller comparison_observation carrying "
                    "comparison_evidence (would forge a 'sufficient' gate over a "
                    "return missing required fields)"
                )

            # (2) HOLE B: reroute with EMPTY route_decision_basis MUST be rejected.
            handle_b = _open(f"{slug}-reroute-nobasis", "agent-object:coo", output_root)
            try:
                close_native_dispatch_brick(
                    handle_b,
                    returned=ok_return,
                    movement="reroute",
                    route_decision_basis=(),
                )
            except ValueError as exc:
                if "route_decision_basis" not in str(exc):
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: reroute-no-basis "
                        f"raised an unexpected message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: HOLE B OPEN -- "
                    "close admitted a reroute with no route_decision_basis"
                )

            # (3) HOLE B: reroute by a NON-CoO ref MUST be rejected even WITH a
            # basis. Covered by TWO refs:
            #   - agent-object:dev (lane=worker): the obvious non-author.
            #   - agent-object:cto-lead (lane=leader): the SUBTLE one -- it shares
            #     lane="leader" with the CoO, so a lane-membership check would
            #     WRONGLY admit it. Only the agent-object:coo REF is authorized;
            #     a *-lead returns observed-only and must NOT author Movement.
            # Before the ref-based fix, the cto-lead reroute was ADMITTED (lane in
            # {leader}) -> this sub-case REDs the lane-only hole.
            for bad_ref, tag in (
                ("agent-object:dev", "reroute-badlane"),
                ("agent-object:cto-lead", "reroute-leadref"),
            ):
                handle_c = _open(f"{slug}-{tag}", bad_ref, output_root)
                try:
                    close_native_dispatch_brick(
                        handle_c,
                        returned=ok_return,
                        movement="reroute",
                        route_decision_basis=["human:smith/decision-0"],
                    )
                except ValueError as exc:
                    if "authoriz" not in str(exc).lower():
                        raise ProfileError(
                            f"native_dispatch_close_case rejected {label}: {tag} "
                            f"raised an unexpected message: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: HOLE B OPEN -- "
                        f"close admitted a reroute from a non-CoO ref {bad_ref!r}"
                    )

            # (4a) POSITIVE (real successful close): forward by the default
            # dev/worker lane must get PAST the guards AND complete -- producing a
            # building tree whose declared-building-plan carries steps. A
            # SpineProjectionError here is NO LONGER tolerated: it WAS the
            # regression (declared_plan_copy.steps absent), so catching it would
            # let the regression hide again. Any raise REDs.
            handle_d = _open(f"{slug}-forward-ok", "agent-object:dev", output_root)
            try:
                forward_result = close_native_dispatch_brick(
                    handle_d,
                    returned=missing_return,
                    movement="forward",
                )
            except SpineProjectionError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: positive forward "
                    "close RAISED SpineProjectionError -- a fresh native-dispatch "
                    "close must SUCCEED and produce a steps-bearing building "
                    f"(regression returned): {exc}"
                ) from exc
            except ValueError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: positive forward was "
                    f"wrongly rejected by a governance guard: {exc}"
                ) from exc
            if forward_result.get("movement") != "forward":
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: positive forward "
                    f"did not record movement=forward: {forward_result.get('movement')!r}"
                )
            if forward_result.get("observed_match_kind") == "matched":
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: positive forward over "
                    "a return MISSING required fields recorded observed_match_kind=matched "
                    "(the comparison was not COMPUTED from the return)"
                )
            _assert_native_dispatch_building_produced(label, forward_result)

            # (4b) POSITIVE (real successful close): a LEGIT reroute (leader lane +
            # non-empty basis) must get PAST both guards AND complete. Same
            # disposition as (4a): a SpineProjectionError is the regression and is
            # NO LONGER tolerated -- any raise REDs. On success assert
            # movement=reroute + caller_lane=leader + recorded route_decision_basis
            # AND a steps-bearing building tree.
            handle_e = _open(f"{slug}-reroute-ok", "agent-object:coo", output_root)
            try:
                reroute_result = close_native_dispatch_brick(
                    handle_e,
                    returned=ok_return,
                    movement="reroute",
                    route_decision_basis=["human:smith/decision-1", "link:reroute-gate"],
                )
            except SpineProjectionError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute "
                    "close RAISED SpineProjectionError -- a fresh native-dispatch "
                    "close must SUCCEED and produce a steps-bearing building "
                    f"(regression returned): {exc}"
                ) from exc
            except ValueError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute was "
                    f"wrongly rejected by a governance guard: {exc}"
                ) from exc
            if reroute_result.get("movement") != "reroute":
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute did not "
                    f"record movement=reroute: {reroute_result.get('movement')!r}"
                )
            if reroute_result.get("caller_lane") != "leader":
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute did not "
                    f"record caller_lane=leader: {reroute_result.get('caller_lane')!r}"
                )
            if not reroute_result.get("route_decision_basis"):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute did not "
                    "record route_decision_basis"
                )
            _assert_native_dispatch_building_produced(label, reroute_result)

            # (5) B2a PARENT-CHILD ORCHESTRATION LINK (record-only provenance).
            # The native-dispatch open accepts OPTIONAL parent_building_id +
            # parent_step_ref. When BOTH are supplied the CHILD building's
            # work/building-work.json must carry a PLAIN parent_orchestration_ref
            # (both parts), and close's return must surface an orchestration_packet
            # mirroring it + a COMPUTED gate_sufficiency. Supplying EXACTLY ONE is
            # an ORPHAN and MUST raise (fail-closed). Supplying NEITHER is a normal
            # standalone dispatch: NO key on disk, packet.parent_orchestration_ref
            # is None. These RED if the orphan guard or the injection is removed.

            # (5a) BOTH parent refs: child work record carries parent_orchestration_ref
            # after close (close REBUILDS building-work.json, so this also pins the
            # re-injection that survives the rewrite), and orchestration_packet
            # mirrors the ref + carries a COMPUTED gate_sufficiency.
            parent_building_id = f"{slug}-parent-bld"
            parent_step_ref = f"{slug}-parent-bld-step-0"
            handle_p = open_native_dispatch_brick(
                building_id=f"{slug}-orch-child",
                received_work=f"{label}: orchestrated child work",
                required_return_shape="observed_evidence, not_proven",
                agent_object_ref="agent-object:dev",
                declared_gate_refs=["link-gate:default-transition"],
                output_root=output_root,
                overwrite_existing=True,
                parent_building_id=parent_building_id,
                parent_step_ref=parent_step_ref,
            )
            orch_result = close_native_dispatch_brick(
                handle_p,
                returned=ok_return,
                movement="forward",
            )
            _assert_native_dispatch_building_produced(label, orch_result)
            child_root = Path(orch_result["building_root"])
            child_work = json.loads(
                (child_root / "work" / "building-work.json").read_text(encoding="utf-8")
            )
            on_disk_ref = child_work.get("parent_orchestration_ref")
            if not isinstance(on_disk_ref, Mapping):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: B2a child work "
                    "record is MISSING parent_orchestration_ref after close (got "
                    f"{on_disk_ref!r})"
                )
            if (
                on_disk_ref.get("parent_building_id") != parent_building_id
                or on_disk_ref.get("parent_step_ref") != parent_step_ref
            ):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: B2a child work "
                    "record parent_orchestration_ref does not carry BOTH parts "
                    f"(got {dict(on_disk_ref)!r})"
                )
            packet = orch_result.get("orchestration_packet")
            if not isinstance(packet, Mapping):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: close return is "
                    f"MISSING orchestration_packet (got {packet!r})"
                )
            if packet.get("child_building_id") != orch_result.get("building_id"):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: orchestration_packet "
                    "child_building_id does not match the closed building_id"
                )
            packet_ref = packet.get("parent_orchestration_ref")
            if not isinstance(packet_ref, Mapping) or (
                packet_ref.get("parent_building_id") != parent_building_id
                or packet_ref.get("parent_step_ref") != parent_step_ref
            ):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: orchestration_packet "
                    f"parent_orchestration_ref does not mirror the ref (got {packet_ref!r})"
                )
            # gate_sufficiency must be the COMPUTED gate value (the same one the
            # top-level result already reports), not hardcoded/absent.
            if packet.get("gate_sufficiency") != orch_result.get("gate_sufficiency"):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: orchestration_packet "
                    "gate_sufficiency does not match the COMPUTED close gate_sufficiency "
                    f"(packet={packet.get('gate_sufficiency')!r} vs "
                    f"close={orch_result.get('gate_sufficiency')!r})"
                )

            # (5b) ORPHAN: EXACTLY ONE of {parent_building_id, parent_step_ref}
            # MUST raise ValueError at OPEN (fail-closed). Covers both halves.
            for orphan_kwargs, tag in (
                ({"parent_building_id": parent_building_id}, "orphan-bld-only"),
                ({"parent_step_ref": parent_step_ref}, "orphan-step-only"),
            ):
                try:
                    open_native_dispatch_brick(
                        building_id=f"{slug}-{tag}",
                        received_work=f"{label}: orphan",
                        required_return_shape="observed_evidence, not_proven",
                        agent_object_ref="agent-object:dev",
                        declared_gate_refs=["link-gate:default-transition"],
                        output_root=output_root,
                        overwrite_existing=True,
                        **orphan_kwargs,
                    )
                except ValueError as exc:
                    if "requires BOTH parent_building_id and parent_step_ref" not in str(exc):
                        raise ProfileError(
                            f"native_dispatch_close_case rejected {label}: {tag} raised "
                            f"an unexpected message: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: ORPHAN OPEN -- "
                        f"open admitted exactly one parent ref ({tag})"
                    )

            # (5c) NEITHER: a standalone dispatch must close normally with NO
            # parent_orchestration_ref key on disk and a None in the packet.
            handle_s = _open(f"{slug}-standalone", "agent-object:dev", output_root)
            standalone_result = close_native_dispatch_brick(
                handle_s,
                returned=ok_return,
                movement="forward",
            )
            _assert_native_dispatch_building_produced(label, standalone_result)
            standalone_work = json.loads(
                (Path(standalone_result["building_root"]) / "work" / "building-work.json").read_text(
                    encoding="utf-8"
                )
            )
            if "parent_orchestration_ref" in standalone_work:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: standalone close "
                    "wrongly wrote a parent_orchestration_ref onto the child work record"
                )
            standalone_packet = standalone_result.get("orchestration_packet")
            if not isinstance(standalone_packet, Mapping):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: standalone close is "
                    f"MISSING orchestration_packet (got {standalone_packet!r})"
                )
            if standalone_packet.get("parent_orchestration_ref") is not None:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: standalone "
                    "orchestration_packet.parent_orchestration_ref is not None (got "
                    f"{standalone_packet.get('parent_orchestration_ref')!r})"
                )

            # (6) B4-REPAIR defect 1 (0611): HARNESS-ENVELOPE TOLERANCE in BOTH
            # directions. The live Claude Code Agent tool_result is a transport
            # envelope carrying harness metadata keys ('status', durations,
            # token counts, usage) alongside the subagent's content; 'status'
            # is in the closed RETURNED_FORBIDDEN_KEYS set, so the raw envelope
            # fed into close made EVERY hook-driven close fail (B4 hooks log:
            # ValueError "returned_value contains forbidden key 'status'").
            # Direction 1 REDs if the tolerance regresses (extraction stops
            # consuming the content / close starts rejecting the harness
            # payload again). Direction 2 REDs if someone "fixes" defect 1 the
            # WRONG way by opening the closed key set: a raw dict carrying
            # 'status' passed DIRECTLY as returned must STILL raise.
            from support.operator.building_operation import (  # noqa: PLC0415
                returned_value_from_harness_payload,
            )

            harness_text = "observed_evidence: present\nnot_proven: documented"
            harness_envelope = {
                "status": "completed",
                "content": [{"type": "text", "text": harness_text}],
                "totalDurationMs": 4321,
                "totalTokens": 99,
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
            harness_returned, unconsumed = returned_value_from_harness_payload(
                harness_envelope
            )
            if harness_returned != harness_text:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: harness "
                    "extraction did not yield the subagent's content text "
                    f"(got {harness_returned!r})"
                )
            if "status" not in unconsumed or "usage" not in unconsumed:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: harness "
                    "extraction did not report the envelope metadata keys as "
                    f"unconsumed (got {unconsumed!r})"
                )
            handle_h = _open(f"{slug}-harness-close", "agent-object:dev", output_root)
            try:
                harness_result = close_native_dispatch_brick(
                    handle_h,
                    returned=harness_returned,
                    movement="forward",
                )
            except ValueError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: DEFECT 1 "
                    "RETURNED -- a close over the extracted harness content was "
                    f"rejected: {exc}"
                ) from exc
            _assert_native_dispatch_building_produced(label, harness_result)

            # (6b) unknown-shape envelope (no recognized content key): the
            # extraction must fall back to ONE raw JSON string (a string
            # carries no keys) so the close still completes -- nothing lost,
            # no closed set opened.
            raw_returned, raw_keys = returned_value_from_harness_payload(
                {"status": "completed", "unknown_envelope_key": {"detail": "x"}}
            )
            if not isinstance(raw_returned, str) or "unknown_envelope_key" not in raw_returned:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: unknown-shape "
                    "harness envelope was not preserved as one raw JSON string "
                    f"(got {raw_returned!r})"
                )
            handle_h2 = _open(f"{slug}-harness-raw", "agent-object:dev", output_root)
            try:
                close_native_dispatch_brick(
                    handle_h2, returned=raw_returned, movement="forward"
                )
            except ValueError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: raw-string "
                    f"fallback close was rejected: {exc}"
                ) from exc

            # (6c) DIRECTION 2 -- the closed declaration seam stays CLOSED: a
            # Mapping carrying the forbidden 'status' key passed DIRECTLY as
            # returned (an agent return record, NOT a harness envelope) must
            # still be rejected by the unchanged RETURNED_FORBIDDEN_KEYS guard.
            handle_h3 = _open(f"{slug}-harness-strict", "agent-object:dev", output_root)
            try:
                close_native_dispatch_brick(
                    handle_h3,
                    returned={"status": "completed", "observed_evidence": "x"},
                    movement="forward",
                )
            except ValueError as exc:
                if "forbidden key 'status'" not in str(exc):
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: direct "
                        "dict-with-'status' was rejected with an unexpected "
                        f"message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: CLOSED KEY "
                    "SET OPENED -- close admitted a returned Mapping carrying "
                    "the forbidden 'status' key"
                )

            # (7) B4-REPAIR defect 2 (0611): COMPOSITION-MODE STAMP. A
            # native-dispatch close must stamp the SINGLE-SOURCED engine linear
            # composition-authorship literal into the plan so the building-map's
            # declaration_provenance records it; an EMPTY mode fails
            # check_building_declaration_integrity gap 3 and the building can
            # never sit green in the repo tree. Compared against the
            # composition.LINEAR_COMPOSITION_MODE constant (same vocabulary the
            # engine stamps for linear plans -- REDs if the stamp is lost OR if
            # native-dispatch drifts to a different literal), then the REAL
            # declaration-law validator is driven over the produced root.
            from support.operator.composition import (  # noqa: PLC0415
                LINEAR_COMPOSITION_MODE,
            )
            from support.checkers.check_building_declaration_integrity import (  # noqa: PLC0415
                validate_building_root,
            )

            harness_root = Path(harness_result["building_root"])
            harness_map = json.loads(
                (harness_root / "work" / "building-map.json").read_text(encoding="utf-8")
            )
            provenance = harness_map.get("declaration_provenance")
            stamped_mode = (
                provenance.get("composition_mode")
                if isinstance(provenance, Mapping)
                else None
            )
            if stamped_mode != LINEAR_COMPOSITION_MODE:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: DEFECT 2 "
                    "RETURNED -- closed building declaration_provenance."
                    f"composition_mode is {stamped_mode!r}, expected the "
                    f"single-sourced {LINEAR_COMPOSITION_MODE!r}"
                )
            integrity_violations = validate_building_root(harness_root)
            if integrity_violations:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: produced "
                    "native-dispatch building fails the declaration-law "
                    f"validator: {integrity_violations}"
                )

            # (8) posA EVIDENCE-SHAPE BACKSTOP FOLD (CLEAN-YARD v3, Smith 0611):
            # the NATIVE-DISPATCH-BRICK-BACKSTOP-0 profile used to pin the
            # standing posA-native-complete dogfood root (path_exists +
            # json_required_paths + text_contains/text_absent). The product
            # repo ships no standing dogfood evidence, so the SAME properties
            # are asserted here over the FRESHLY generated standalone close
            # tree (ok_return, forward) -- the close-case seam IS the
            # generator. Property list migrated 1:1 from the retired pins; see
            # _assert_native_dispatch_pos_a_shape.
            _assert_native_dispatch_pos_a_shape(
                label, Path(standalone_result["building_root"])
            )

        count += 1
    return count


# posA evidence-shape property set, migrated 1:1 from the retired standing-root
# pins of native_dispatch_brick_backstop.yaml (json_required_paths blocks).
_POS_A_JSON_REQUIRED: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("work", "building-work.json"),
        ("execution_path", "building_id", "step_refs[]", "required_return_shape"),
    ),
    (
        ("work", "building-map.json"),
        (
            "execution_path",
            "kind",
            "agent_bindings[].agent_performer_ref",
            "agent_bindings[].brick_instance_ref",
            "agent_bindings[].produced_public_fact_refs[]",
            "link_edges[].movement_fact_ref",
            "link_edges[].transition_fact_ref",
        ),
    ),
    (("evidence", "evidence-manifest.json"), ("execution_path",)),
    (
        ("evidence", "claim_trace", "brick", "work_contract.json"),
        (
            "facts[].fact.observed_match_kind",
            "facts[].fact.required_return_shape_evidence",
            "facts[].fact.comparison_evidence",
            "facts[].fact.forbidden_shortcut_evidence",
            "facts[].fact.work_statement",
        ),
    ),
    (
        ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
        (
            "facts[].fact.stage",
            "facts[].fact.sufficiency",
            "facts[].fact.required_public_facts[]",
            "facts[].fact.checked_public_fact",
            "facts[].fact.reason",
        ),
    ),
    (
        ("evidence", "claim_trace", "link", "movement_trace.json"),
        (
            "facts[].fact.movement",
            "facts[].fact.declared_gate_refs[]",
            "facts[].fact.public_fact_refs[]",
        ),
    ),
    (
        ("evidence", "claim_trace", "agent", "returned_claims.json"),
        (
            "facts[].fact.agent_object_ref",
            "facts[].fact.received_work",
            "facts[].fact.returned",
        ),
    ),
)
# text_contains pins migrated 1:1 (execution_path literal value, open-capture
# events recorded before the subagent return, COMPUTED-gate honesty notes).
_POS_A_TEXT_CONTAINS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("work", "building-work.json"), ('"execution_path": "native-dispatch"',)),
    (("work", "building-map.json"), ('"execution_path": "native-dispatch"',)),
    (("evidence", "evidence-manifest.json"), ('"execution_path": "native-dispatch"',)),
    (
        ("capture", "events.jsonl"),
        (
            '"event_type":"building_opened"',
            '"event_type":"brick_opened"',
            '"event_type":"brick_compared"',
            '"event_type":"link_movement"',
        ),
    ),
    (
        ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
        ('"stage": "movement"',),
    ),
    (
        ("evidence", "claim_trace", "brick", "work_contract.json"),
        (
            "support/run did not classify Agent return",
            "support/run did not judge success or quality",
        ),
    ),
)
# text_absent pins migrated 1:1 (the gate must be COMPUTED, never hardcoded).
_POS_A_TEXT_ABSENT: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
        ("hardcoded_pass", "default_gatefact", "forced_sufficient"),
    ),
)


def _assert_native_dispatch_pos_a_shape(label: str, building_root: Path) -> None:
    """posA evidence-shape backstop over a FRESH native-dispatch close tree.

    Asserts, 1:1, the property set the retired standing posA-native-complete
    pins asserted: the 8 evidence files exist, the required JSON paths resolve,
    the execution_path literal + open-capture event types + COMPUTED-gate
    honesty notes are present, and no hardcoded-gate literal appears.
    """

    for parts, required in _POS_A_JSON_REQUIRED:
        path = building_root.joinpath(*parts)
        if not path.is_file():
            raise ProfileError(
                f"native_dispatch_close_case rejected {label}: posA shape -- "
                f"evidence file missing on the fresh close tree: {'/'.join(parts)}"
            )
        value = json.loads(path.read_text(encoding="utf-8"))
        for dotted in required:
            if not json_path_exists(value, dotted):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: posA shape -- "
                    f"{'/'.join(parts)} is missing required path {dotted!r}"
                )
    for parts, needles in _POS_A_TEXT_CONTAINS:
        path = building_root.joinpath(*parts)
        if not path.is_file():
            raise ProfileError(
                f"native_dispatch_close_case rejected {label}: posA shape -- "
                f"evidence file missing on the fresh close tree: {'/'.join(parts)}"
            )
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: posA shape -- "
                    f"{'/'.join(parts)} does not contain {needle!r}"
                )
    for parts, needles in _POS_A_TEXT_ABSENT:
        text = building_root.joinpath(*parts).read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: posA shape -- "
                    f"{'/'.join(parts)} must NOT contain {needle!r} (the gate must "
                    "be COMPUTED, never hardcoded)"
                )


def _assert_native_dispatch_building_produced(
    label: str, result: Mapping[str, Any]
) -> None:
    """Assert a native-dispatch close produced a real steps-bearing building.

    Proves the close did NOT just return -- it wrote a building tree marked
    execution_path=native-dispatch whose work/declared-building-plan.json has a
    NON-EMPTY declared_plan_copy.steps list. The absence of that steps list was
    the exact regression that raised SpineProjectionError; asserting its presence
    over a FRESH close (not a stale on-disk proof) closes the backstop hole.
    """

    building_root = result.get("building_root")
    if not building_root or not Path(building_root).is_dir():
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: close did not produce a "
            f"building_root directory (got {building_root!r})"
        )
    if result.get("execution_path") != "native-dispatch":
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: produced building did not "
            f"record execution_path=native-dispatch (got {result.get('execution_path')!r})"
        )
    plan_path = Path(building_root) / "work" / "declared-building-plan.json"
    if not plan_path.is_file():
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: produced building has no "
            f"work/declared-building-plan.json at {plan_path}"
        )
    try:
        packet = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: declared-building-plan.json "
            f"was not readable JSON: {exc}"
        ) from exc
    declared_plan = packet.get("declared_plan_copy")
    steps = declared_plan.get("steps") if isinstance(declared_plan, Mapping) else None
    if not isinstance(steps, list) or not steps:
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: declared_plan_copy.steps is "
            "not a NON-EMPTY JSON list -- the steps regression has returned "
            f"(got {steps!r})"
        )


def run_workflow_import_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """FIRE the IMPORTER honesty pin via a real open -> import over a temp root.

    WHY: workflow-internal agents pass through a harness back door the
    recording hooks cannot observe (B4 measurement), so the importer records a
    workflow's RESULT post-hoc as ONE performer act. The hard rule is HONESTY:
    the importer must NEVER fabricate per-internal-agent evidence it did not
    observe. For each declared item (a marker; no required fields) this drives
    the real support/operator/workflow_import.py verbs and asserts:

      (1) RESULT AS EVIDENCE: the verbatim workflow result text rides the
          existing agent-return raw stream (raw/agent-return.jsonl) -- no new
          raw shape invented.
      (2) HONEST PACKET on disk: work/building-work.json carries the
          workflow_import packet with the workflow_ref, the harness-provided
          totals (agent_count / usage / totalTokens), the passed-in
          timestamps, the ignored envelope key NAMES, AND the verbatim
          "internal agent detail not observable (workflow back door)" note;
          the packet carries NO per-internal-agent identity key.
      (3) HONESTY PIN (one performer act): the Evidence Spine records EXACTLY
          ONE AgentBinding, ONE AgentReceipt, and ONE AgentReturn event, and
          the agent claim trace carries EXACTLY ONE returned fact. A second
          (fabricated) per-agent row REDs this case.
      (4) NO LAUNDERING: a STRUCTURED workflow return (a Mapping under the
          envelope content key) smuggling the forbidden 'status' key MUST
          still be rejected by the unchanged closed RETURNED_FORBIDDEN_KEYS
          validation, THROUGH the import verb (the importer must propagate,
          never swallow or rewrite, the rejection).
      (5) B4-REPAIR NON-RECURRENCE: the imported building records
          declaration_provenance.composition_mode == the single-sourced
          engine linear literal AND passes the REAL
          check_building_declaration_integrity validator.
      (6) FORCED SYNTHETIC PERFORMER (fabrication fix 0612): the spine's
          recorded performer ref VALUE on every AgentBinding / AgentReceipt /
          AgentReturn event EQUALS the checker-side literal
          "agent-object:workflow" (deliberately NOT the producer constant --
          a two-place pin), AND opening with a caller-supplied
          agent_object_ref="agent:fake-specific-person" is rejected loudly
          (TypeError: the override parameter was removed; a compat parameter
          re-introduced with a guard must raise ValueError). A re-introduced
          unguarded override that stamps a caller-claimed specific performer
          REDs on the ref-value pin even though the count pin (3) stays at 1.
      (7) NO NESTED IDENTITY (fabrication fix 0612): usage totals must be a
          FLAT str->non-negative-int tally (nested mapping rejected on BOTH
          the explicit usage argument and the envelope-lifted usage key); an
          identity-shaped key NAME in usage is rejected (since the re-review
          allowlist fix, by the usage-key allowlist firing BEFORE the deep
          packet scan; the deep scan stays as defense in depth and is pinned
          independently on the structured-return path, 7d); a STRUCTURED
          workflow return smuggling a forbidden identity key at any depth is
          rejected before it can ride the single Agent claim fact. The happy
          path (flat allowlisted usage, no identity keys) above proves the
          guards admit honest input.
      (8) HANDLE PERFORMER-REF PIN (importer re-review fix 0612, High): a
          handle of the ACCEPTED class whose agent_object_ref is NOT the
          synthetic "agent-object:workflow" -- built fully consistently via
          the brick_protocol-path open_native_dispatch_brick, the SAME module
          workflow_import imports the class from, so the explicit REF CHECK
          is exercised, not the dual-import-path class accident -- MUST be
          rejected loudly by import_workflow_result. Removing the ref check
          REDs here: pre-fix this exact handle closed cleanly and stamped a
          specific performer the harness never exposed.
      (9) USAGE KEY ALLOWLIST (importer re-review fix 0612, Medium): a usage
          key OUTSIDE the aggregate-metric allowlist (e.g. {"x_team": 3} -- a
          per-agent label under a neutral name the identity deny-list cannot
          enumerate) MUST be rejected loudly; allowlisted flat usage
          ({"input_tokens": 1000, "output_tokens": 234}, the happy path
          above) stays accepted and recorded. Widening the allowlist check to
          accept-all REDs here: {"x_team": 3} would then import cleanly
          (nothing downstream flags a neutral key name).

    Support evidence only: asserts recorded SHAPE/honesty, not workflow
    quality; the gate verdict over the imported result is the Link rule's
    COMPUTED output and is not asserted here.
    """

    items = rule_items(profile, "workflow_import_case")
    if not items:
        return 0
    from support.operator.workflow_import import (
        WORKFLOW_IMPORT_FORBIDDEN_PACKET_KEYS,
        WORKFLOW_IMPORT_NOT_OBSERVABLE_NOTE,
        WORKFLOW_IMPORT_PACKET_KEY,
        import_workflow_result,
        open_workflow_recording,
    )
    from support.operator.composition import LINEAR_COMPOSITION_MODE
    from support.checkers.check_building_declaration_integrity import (
        validate_building_root,
    )

    count = 0
    for item in items:
        mapping = require_mapping(item, "workflow_import_case item")
        label = require_string(
            mapping.get("label", "workflow-import"), "workflow_import_case.label"
        )
        slug = _case_slug(label)
        with tempfile.TemporaryDirectory(prefix=f"bp-workflow-import-{slug}-") as tmpdir:
            output_root = Path(tmpdir) / "buildings"
            result_text = (
                "observed_evidence: workflow produced the verbatim report\n"
                "not_proven: internal agent detail (workflow back door)"
            )
            envelope = {
                "status": "completed",
                "result": result_text,
                "agent_count": 3,
                "totalTokens": 1234,
                "usage": {"input_tokens": 1000, "output_tokens": 234},
                "totalDurationMs": 7777,
            }
            handle = open_workflow_recording(
                building_id=f"{slug}-imported",
                received_work=f"{label}: record a finished workflow's result",
                output_root=output_root,
                overwrite_existing=True,
            )
            record = import_workflow_result(
                handle,
                workflow_result=envelope,
                workflow_ref=f"workflow:{slug}",
                started_at="2026-06-12T01:00:00Z",
                finished_at="2026-06-12T01:30:00Z",
            )
            root = Path(str(record.get("building_root", "")))
            if not root.is_dir():
                raise ProfileError(
                    f"workflow_import_case rejected {label}: import did not produce "
                    f"a building_root directory (got {record.get('building_root')!r})"
                )

            # (1) the verbatim result text rides the existing agent-return raw stream.
            raw_path = root / "raw" / "agent-return.jsonl"
            if not raw_path.is_file():
                raise ProfileError(
                    f"workflow_import_case rejected {label}: raw/agent-return.jsonl "
                    "is missing -- the result did not ride the agent-return raw stream"
                )
            if "workflow produced the verbatim report" not in raw_path.read_text(
                encoding="utf-8"
            ):
                raise ProfileError(
                    f"workflow_import_case rejected {label}: raw/agent-return.jsonl "
                    "does not carry the verbatim workflow result text"
                )

            # (2) the honest packet on the on-disk work record.
            work = json.loads(
                (root / "work" / "building-work.json").read_text(encoding="utf-8")
            )
            packet = work.get(WORKFLOW_IMPORT_PACKET_KEY)
            if not isinstance(packet, Mapping):
                raise ProfileError(
                    f"workflow_import_case rejected {label}: work/building-work.json "
                    f"carries no {WORKFLOW_IMPORT_PACKET_KEY} packet (got {packet!r})"
                )
            recorded_note = packet.get("internal_agent_detail")
            if recorded_note != WORKFLOW_IMPORT_NOT_OBSERVABLE_NOTE:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: HONESTY NOTE LOST -- "
                    "the packet does not carry the verbatim not-observable note "
                    f"(got {recorded_note!r})"
                )
            # ANTI-TAUTOLOGY (operator gate 0612, hardened same day): the
            # equality above compares the packet against the SAME imported
            # constant the producer writes, so gutting the constant itself
            # would pass silently. This checker-side FULL literal is the
            # independent second place: changing the producer constant in ANY
            # way (not just dropping the old phrases -- a misleading future
            # rewording that still CONTAINS them would have slipped a
            # substring check) REDs here until this literal is deliberately
            # updated too. A two-place update is the point.
            expected_note_literal = (
                "internal agent detail not observable (workflow back door); "
                "recorded as one performer act"
            )
            if recorded_note != expected_note_literal:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: HONESTY NOTE CHANGED -- "
                    "the on-disk note must EQUAL the checker-side literal verbatim "
                    f"(expected {expected_note_literal!r}, got {recorded_note!r}); "
                    "if the note wording is deliberately changing, update producer "
                    "constant AND this literal together"
                )
            expected_values = {
                "workflow_ref": f"workflow:{slug}",
                "agent_count": 3,
                "total_tokens": 1234,
                "usage_totals": {"input_tokens": 1000, "output_tokens": 234},
                "recorded_performer_acts": 1,
                "started_at": "2026-06-12T01:00:00Z",
                "finished_at": "2026-06-12T01:30:00Z",
            }
            for key, expected in expected_values.items():
                if packet.get(key) != expected:
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: packet.{key} is "
                        f"{packet.get(key)!r}, expected {expected!r}"
                    )
            ignored = packet.get("envelope_keys_ignored")
            if not isinstance(ignored, list) or "status" not in ignored:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: packet."
                    "envelope_keys_ignored does not name the ignored harness "
                    f"'status' key (got {ignored!r})"
                )
            fabricated_keys = sorted(
                set(packet) & set(WORKFLOW_IMPORT_FORBIDDEN_PACKET_KEYS)
            )
            if fabricated_keys:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: FABRICATION -- the "
                    "packet carries per-internal-agent identity key(s) the harness "
                    f"never exposed: {fabricated_keys}"
                )

            # (3) HONESTY PIN: exactly ONE recorded performer act.
            spine_path = root / "evidence" / "spine" / "spine.jsonl"
            spine_events = [
                json.loads(line)
                for line in spine_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            for event_type in ("AgentBinding", "AgentReceipt", "AgentReturn"):
                observed = sum(
                    1 for event in spine_events if event.get("event_type") == event_type
                )
                if observed != 1:
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: FABRICATION -- the "
                        f"spine records {observed} {event_type} event(s); an imported "
                        "workflow is exactly ONE recorded performer act (internal "
                        "agents are not observable)"
                    )
            # (6) PERFORMER REF VALUE pin (fabrication fix 0612): the count pin
            # alone admits ONE act under a FABRICATED specific identity, so pin
            # the WHO too. The spine.jsonl rows are the hash-chain INDEX; the
            # performer refs live in the event BODY files under event_ref.
            # Checker-side LITERALS, deliberately not the producer constant: a
            # re-introduced caller override (or a changed constant) that stamps
            # any other performer ref REDs here.
            expected_performer_ref = "agent-object:workflow"
            for event in spine_events:
                event_type = event.get("event_type")
                if event_type not in ("AgentBinding", "AgentReceipt", "AgentReturn"):
                    continue
                body = json.loads(
                    (root / str(event.get("event_ref"))).read_text(encoding="utf-8")
                )
                observed_ref = body.get("agent_object_ref")
                if observed_ref != expected_performer_ref:
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: FABRICATED "
                        f"PERFORMER -- spine {event_type} records "
                        f"agent_object_ref {observed_ref!r}; an imported workflow's "
                        "one performer act is ALWAYS the synthetic "
                        f"{expected_performer_ref!r} (specific performer identity "
                        "is not observable through the workflow back door)"
                    )
                if event_type == "AgentBinding":
                    observed_performer = body.get("agent_performer_ref")
                    if observed_performer != f"agent-performer:{expected_performer_ref}":
                        raise ProfileError(
                            f"workflow_import_case rejected {label}: FABRICATED "
                            "PERFORMER -- spine AgentBinding records "
                            f"agent_performer_ref {observed_performer!r}, expected "
                            f"'agent-performer:{expected_performer_ref}'"
                        )
            claims = json.loads(
                (root / "evidence" / "claim_trace" / "agent" / "returned_claims.json")
                .read_text(encoding="utf-8")
            )
            facts = claims.get("facts")
            if not isinstance(facts, list) or len(facts) != 1:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: FABRICATION -- the agent "
                    f"claim trace carries {len(facts) if isinstance(facts, list) else facts!r} "
                    "returned fact(s); expected exactly ONE recorded performer act"
                )

            # (5) B4-REPAIR non-recurrence: composition_mode stamped + the REAL
            # declaration-law validator over the imported building.
            building_map = json.loads(
                (root / "work" / "building-map.json").read_text(encoding="utf-8")
            )
            provenance = building_map.get("declaration_provenance")
            stamped_mode = (
                provenance.get("composition_mode")
                if isinstance(provenance, Mapping)
                else None
            )
            if stamped_mode != LINEAR_COMPOSITION_MODE:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: imported building "
                    f"declaration_provenance.composition_mode is {stamped_mode!r}, "
                    f"expected the single-sourced {LINEAR_COMPOSITION_MODE!r}"
                )
            integrity_violations = validate_building_root(root)
            if integrity_violations:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: imported building fails "
                    f"the declaration-law validator: {integrity_violations}"
                )

            # (4) NO LAUNDERING through the import verb: a STRUCTURED workflow
            # return (a Mapping under the content key) smuggling 'status' must
            # STILL reject via the unchanged closed RETURNED_FORBIDDEN_KEYS set.
            handle_l = open_workflow_recording(
                building_id=f"{slug}-laundering",
                received_work=f"{label}: structured return smuggling status",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_l,
                    workflow_result={
                        "result": {"status": "completed", "observed_evidence": "x"}
                    },
                    workflow_ref=f"workflow:{slug}-laundering",
                )
            except ValueError as exc:
                if "forbidden key 'status'" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: structured return "
                        "with 'status' was rejected with an unexpected message: "
                        f"{exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: CLOSED KEY SET OPENED "
                    "-- the importer admitted a structured return carrying the "
                    "forbidden 'status' key"
                )

            # (6) FORCED PERFORMER: a caller-claimed SPECIFIC performer identity
            # must be rejected loudly at open. TypeError = the override
            # parameter stays removed (current design); ValueError = a compat
            # parameter returned WITH a loud guard. Anything else (the call
            # succeeding) is the High fabrication vector reopened.
            try:
                open_workflow_recording(
                    building_id=f"{slug}-fake-performer",
                    received_work=f"{label}: caller claims a specific performer",
                    output_root=output_root,
                    overwrite_existing=True,
                    agent_object_ref="agent:fake-specific-person",
                )
            except (TypeError, ValueError):
                pass
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: FABRICATED PERFORMER "
                    "ADMITTED -- open_workflow_recording accepted a caller-supplied "
                    "agent_object_ref; the imported performer must ALWAYS be the "
                    "synthetic agent-object:workflow"
                )

            # (7a) NESTED usage via the EXPLICIT argument: a usage tally is
            # flat ints; a nested mapping is an identity smuggling vector.
            handle_u = open_workflow_recording(
                building_id=f"{slug}-nested-usage",
                received_work=f"{label}: nested usage smuggle (explicit arg)",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_u,
                    workflow_result="usage smuggle probe",
                    workflow_ref=f"workflow:{slug}-nested-usage",
                    usage={"input_tokens": {"agent_ids": ["fabricated-agent-1"]}},
                )
            except ValueError as exc:
                if "flat mapping" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: nested usage was "
                        f"rejected with an unexpected message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: NESTED IDENTITY "
                    "ADMITTED -- import_workflow_result accepted a non-flat usage "
                    "mapping carrying agent_ids under an admitted field"
                )

            # (7b) NESTED usage via the ENVELOPE lift: same guard on the lifted
            # path (the old code dict()-copied the envelope usage verbatim).
            handle_e = open_workflow_recording(
                building_id=f"{slug}-envelope-usage",
                received_work=f"{label}: nested usage smuggle (envelope lift)",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_e,
                    workflow_result={
                        "result": "envelope usage smuggle probe",
                        "usage": {"input_tokens": {"agent_ids": ["fabricated-agent-2"]}},
                    },
                    workflow_ref=f"workflow:{slug}-envelope-usage",
                )
            except ValueError as exc:
                if "flat mapping" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: nested envelope "
                        f"usage was rejected with an unexpected message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: NESTED IDENTITY "
                    "ADMITTED -- the envelope usage lift copied a nested mapping "
                    "carrying agent_ids into the packet"
                )

            # (7c) IDENTITY-SHAPED KEY NAME in usage with a FLAT int value:
            # passes the flat-shape check by construction. Since the re-review
            # allowlist fix, the usage-key ALLOWLIST rejects it FIRST
            # ("agent_ids" is not an aggregate metric key); the deep packet
            # scan stays behind it as defense in depth (pinned independently
            # on the structured-return path, 7d). Accept either guard's loud
            # rejection wording -- both close this vector.
            handle_k = open_workflow_recording(
                building_id=f"{slug}-identity-key",
                received_work=f"{label}: identity key name in flat usage",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_k,
                    workflow_result="identity key probe",
                    workflow_ref=f"workflow:{slug}-identity-key",
                    usage={"agent_ids": 3},
                )
            except ValueError as exc:
                if "non-allowlisted" not in str(exc) and "per-internal-agent" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: nested identity "
                        f"key was rejected with an unexpected message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: NESTED IDENTITY "
                    "ADMITTED -- an identity-shaped key name in usage passed both "
                    "the usage-key allowlist and the deep packet scan"
                )

            # (7d) STRUCTURED RETURN carrying identity at depth: the return
            # rides the single Agent claim fact verbatim and the closed
            # RETURNED_FORBIDDEN_KEYS set names no identity keys, so the
            # importer must reject identity shapes in the structured return
            # itself (count pin stays 1 either way -- the WHO is the leak).
            handle_r = open_workflow_recording(
                building_id=f"{slug}-return-identity",
                received_work=f"{label}: structured return smuggling identity",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_r,
                    workflow_result={
                        "result": {
                            "observed_evidence": "x",
                            "detail": {"agent_ids": ["fabricated-agent-3"]},
                        }
                    },
                    workflow_ref=f"workflow:{slug}-return-identity",
                )
            except ValueError as exc:
                if "per-internal-agent" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: identity in the "
                        "structured return was rejected with an unexpected "
                        f"message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: NESTED IDENTITY "
                    "ADMITTED -- a structured workflow return carried agent_ids "
                    "at depth into the single Agent claim fact"
                )

            # (8) HANDLE PERFORMER-REF PIN (importer re-review fix 0612,
            # High): isinstance pins the handle CLASS, not the WHO it claims.
            # Build a fully CONSISTENT forged handle the most direct way that
            # yields the exact class import_workflow_result accepts: the
            # brick_protocol-path open_native_dispatch_brick -- the SAME
            # module workflow_import itself imports the class from. (The
            # support-path twin class is a dual-import accident, not a guard;
            # this construction goes around it, so the explicit REF CHECK is
            # what is exercised.) Pre-fix this exact handle rode through and
            # recorded a specific performer the harness never exposed; remove
            # the ref check and it closes cleanly again -- RED on the else.
            from brick_protocol.support.operator.native_dispatch import (  # noqa: PLC0415
                open_native_dispatch_brick as _bp_open_native_dispatch_brick,
            )

            forged = _bp_open_native_dispatch_brick(
                building_id=f"{slug}-forged-ref",
                received_work=f"{label}: handle claiming a specific performer",
                required_return_shape="",
                agent_object_ref="agent-object:fake-specific-person",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    forged,
                    workflow_result="forged performer-ref probe",
                    workflow_ref=f"workflow:{slug}-forged-ref",
                )
            except ValueError as exc:
                message = str(exc)
                if (
                    "refusing" not in message
                    or "agent-object:workflow" not in message
                ):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: forged "
                        "performer-ref handle was rejected with an unexpected "
                        f"message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: FABRICATED "
                    "PERFORMER ADMITTED -- import_workflow_result accepted a "
                    "handle whose agent_object_ref is not the synthetic "
                    "agent-object:workflow; the performer-ref guard must hold "
                    "independent of class-identity accidents"
                )

            # (9) USAGE KEY ALLOWLIST (importer re-review fix 0612, Medium):
            # a per-agent LABEL under a NEUTRAL key name -- one the identity
            # deny-list does not flag and the deep scan cannot recognize --
            # must be rejected by the aggregate-metric allowlist. Widen the
            # allowlist check to accept-all and {"x_team": 3} imports cleanly
            # (no downstream guard knows the name) -- RED on the else branch.
            # Allowlisted-flat ACCEPTANCE is pinned by the happy path above
            # (usage_totals == {"input_tokens": 1000, "output_tokens": 234}).
            handle_a = open_workflow_recording(
                building_id=f"{slug}-usage-label",
                received_work=f"{label}: per-agent label under neutral usage key",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_a,
                    workflow_result="neutral usage-label probe",
                    workflow_ref=f"workflow:{slug}-usage-label",
                    usage={"x_team": 3},
                )
            except ValueError as exc:
                if "non-allowlisted" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: non-allowlisted "
                        "usage key was rejected with an unexpected message: "
                        f"{exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: PER-AGENT LABEL "
                    "ADMITTED -- import_workflow_result accepted usage key "
                    "'x_team' outside the aggregate-metric allowlist; an "
                    "arbitrary usage key name is recorded per-agent detail"
                )
        count += 1
    return count


def _gate_sequence_policy_link_row(case: Mapping[str, Any]) -> Mapping[str, Any]:
    raw_link_row = case.get("link_row", case)
    return require_mapping(raw_link_row, "gate_sequence_policy link_row")


def _gate_sequence_policy_context(case: Mapping[str, Any]) -> dict[str, Any]:
    declared_refs_raw = case.get("declared_brick_refs")
    declared_refs = None
    if declared_refs_raw is not None:
        declared_refs = frozenset(
            require_string_list(declared_refs_raw, "gate_sequence_policy.declared_brick_refs")
        )
    raw_budgets = case.get("node_reroute_budgets")
    node_reroute_budgets = None
    if raw_budgets is not None:
        node_reroute_budgets = require_mapping(
            raw_budgets,
            "gate_sequence_policy.node_reroute_budgets",
        )
    return {
        "source_brick_ref": str(case.get("source_brick_ref", "") or ""),
        "target_brick_ref": str(case.get("target_brick_ref", "") or ""),
        "declared_brick_refs": declared_refs,
        "node_reroute_budgets": node_reroute_budgets,
    }


def _compose_building_profile_plan(case: Mapping[str, Any], repo: Path) -> Mapping[str, Any]:
    from support.operator.building_operation import compose_building

    return compose_building(
        case.get("nodes", []),
        case.get("edges", []),
        selected_shape_ref=case.get("selected_shape_ref", ""),
        declared_by=require_string(case.get("declared_by"), "compose_building.declared_by"),
        groups=case.get("groups", []),
        chain_preset_ref=str(case.get("chain_preset_ref", "") or ""),
        plan_ref=str(case.get("plan_ref", "") or ""),
        building_id=str(case.get("building_id", "") or ""),
        repo_root=repo,
    )


def _graph_test_plan_from_linear(linear_plan: Mapping[str, Any]) -> Mapping[str, Any]:
    """Convert a checker-only forward linear plan into a graph plan via compose_building."""

    from support.operator.composition import compose_building

    if linear_plan.get("plan_shape") != "linear":
        raise ProfileError("_graph_test_plan_from_linear requires plan_shape: linear")
    raw_steps = linear_plan.get("steps")
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)) or not raw_steps:
        raise ProfileError("_graph_test_plan_from_linear requires a non-empty steps list")

    nodes: list[Mapping[str, Any]] = []
    edges: list[Mapping[str, Any]] = []
    endpoint_refs: set[str] = set()
    building_id = str(linear_plan.get("building_id") or "checker-linear-to-graph")
    prepared_steps: list[tuple[str, Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]] = []
    for index, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise ProfileError(f"_graph_test_plan_from_linear steps[{index}] must be a mapping")
        step_ref = require_string(raw_step.get("step_ref"), f"steps[{index}].step_ref")
        rows = raw_step.get("rows")
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
            raise ProfileError(f"_graph_test_plan_from_linear steps[{index}].rows must be a sequence")
        by_axis = {
            str(row.get("axis")): row
            for row in rows
            if isinstance(row, Mapping) and row.get("axis") in {"Brick", "Agent", "Link"}
        }
        missing_axes = {"Brick", "Agent", "Link"} - set(by_axis)
        if missing_axes:
            raise ProfileError(
                f"_graph_test_plan_from_linear steps[{index}] missing row axis/axes: "
                + ", ".join(sorted(missing_axes))
            )
        brick_row = dict(by_axis["Brick"])
        agent_row = dict(by_axis["Agent"])
        link_row = dict(by_axis["Link"])
        prepared_steps.append((step_ref, raw_step, brick_row, agent_row, link_row))
        endpoint_refs.add(step_ref)
        brick_ref = str(brick_row.get("brick_instance_ref") or "").strip()
        if brick_ref:
            endpoint_refs.add(brick_ref)

    for index, (step_ref, raw_step, brick_row, _agent_row, link_row) in enumerate(prepared_steps):
        node: dict[str, Any] = {
            "node_id": step_ref,
            "step_ref": step_ref,
            "step_template_ref": raw_step.get("step_template_ref", "building-step-template:work"),
        }
        for key in ("selected_adapter_ref", "selected_model_ref"):
            if key in raw_step:
                node[key] = raw_step[key]
        for key, value in brick_row.items():
            if key != "axis":
                if key == "source_facts" and not value:
                    continue
                node[key] = json.loads(json.dumps(value))
        nodes.append(node)

        declared_target_ref = require_string(
            link_row.get("target_ref", link_row.get("next_brick_instance_ref")),
            f"steps[{index}].Link.target_ref",
        )
        if declared_target_ref in endpoint_refs:
            target_ref = declared_target_ref
        elif index == len(prepared_steps) - 1:
            target_ref = (
                declared_target_ref
                if declared_target_ref.startswith(("building-boundary:", "building-boundary-"))
                else f"building-boundary:{_case_slug(building_id)}-closed"
            )
        else:
            target_ref = declared_target_ref
        edge: dict[str, Any] = {
            "edge_ref": f"edge:{step_ref}-to-{_case_slug(target_ref)}",
            "source_step_ref": step_ref,
            "target_ref": target_ref,
            "movement": require_string(link_row.get("movement"), f"steps[{index}].Link.movement"),
            "row_ref": link_row.get("row_ref", f"link-row:{step_ref}"),
        }
        for key in (
            "declared_gate_refs",
            "gate_sequence_policy",
            "gate_concept_provenance",
            "route_replay_plan",
            "route_decision_basis",
            "transition_authoring",
            "transition_lifecycle",
            "building_lifecycle",
        ):
            if key in link_row:
                edge[key] = json.loads(json.dumps(link_row[key]))
        edges.append(edge)

    graph_plan = dict(
        compose_building(
            nodes,
            edges,
            declared_by=str(linear_plan.get("declared_by") or "coo"),
            plan_ref=str(linear_plan.get("plan_ref") or ""),
            building_id=building_id,
            selected_adapter_ref=str(linear_plan.get("selected_adapter_ref") or "adapter:local"),
            selected_model_ref=str(linear_plan.get("selected_model_ref") or "model:default"),
            selected_shape_ref=str(linear_plan.get("selected_shape_ref") or ""),
            chain_preset_ref=str(linear_plan.get("chain_preset_ref") or ""),
        )
    )
    for key in (
        "task_source_ref",
        "task_statement",
        "report_event_policy",
        "route_decision_basis",
        "proof_limits",
        "not_proven",
    ):
        if key in linear_plan:
            graph_plan[key] = json.loads(json.dumps(linear_plan[key]))
    return graph_plan


def _validation_plan_for_declared_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if plan.get("plan_shape") == "graph":
        from support.operator.plan_graph import _linear_plan_from_graph_plan

        validation_plan, _graph_context = _linear_plan_from_graph_plan(plan)
        return validation_plan
    return plan


def _compose_building_expected_codes(mapping: Mapping[str, Any]) -> list[str]:
    if "expected_code" in mapping:
        return [require_string(mapping.get("expected_code"), "compose_building_rejects.expected_code")]
    return require_string_list(
        mapping.get("expected_codes", []),
        "compose_building_rejects.expected_codes",
    )


def _optional_positive_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text.isdecimal() or int(text) <= 0:
        raise ProfileError(f"{label} must be a positive integer")
    return int(text)


def _compose_building_ok_callable(request: Any) -> Mapping[str, Any]:
    return {
        "observed_evidence": [f"adapter:local observed {request.brick_instance_ref}"],
        "not_proven": ["semantic correctness"],
    }


def run_adapter_capability_rehome_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "adapter_capability_rehome_case")
    if not items:
        return 0
    count = 0
    for item in items:
        mapping = require_mapping(item, "adapter_capability_rehome_case item")
        label = require_string(mapping.get("label"), "adapter_capability_rehome_case.label")
        case_kind = require_string(mapping.get("case_kind"), f"{label}: case_kind")
        expected_reason = str(mapping.get("expected_reason", "") or "")
        if case_kind == "ok_all_four":
            _check_adapter_capability_ok_all_four(label)
        elif case_kind == "claude_write_ok":
            _check_adapter_capability_claude_write_ok(label)
        elif case_kind == "missing_brick_scope":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_missing_brick_scope(label),
            )
        elif case_kind == "missing_agent_policy":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_missing_agent_policy(label),
            )
        elif case_kind == "missing_adapter_capability":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_missing_adapter_capability(label),
            )
        elif case_kind == "observation_out_of_scope":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_observation_out_of_scope(label),
            )
        elif case_kind == "poc_read_only_adapter_with_write_scope":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_poc_read_only_with_write_scope(label),
            )
        elif case_kind == "legacy_adapter_identity_only_not_authority":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_legacy_identity_only(label),
            )
        elif case_kind == "write_capable_adapter_without_write_scope_no_write_observation":
            _check_adapter_capability_no_write_observation_without_scope(label)
        elif case_kind == "write_capable_leader_effective_write_gated_by_brick_scope":
            _check_adapter_capability_write_capable_leader_effective_write_gated_by_brick_scope(
                label
            )
        elif case_kind == "write_capable_leader_read_only_brick_projection_read_only":
            _check_adapter_capability_write_capable_leader_read_only_brick_projection(
                label
            )
        elif case_kind == "write_capable_leader_write_needed_brick_projection_write":
            _check_adapter_capability_write_capable_leader_write_needed_brick_projection(
                label
            )
        elif case_kind == "write_scope_on_read_only_brick_rejected":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_write_scope_on_read_only_brick_rejected(
                    label
                ),
            )
        elif case_kind == "silent_write_grant_rejected_at_run_admission":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_silent_write_grant_rejected_at_run_admission(
                    label
                ),
            )
        elif case_kind == "explicit_write_need_marker_admitted_strict":
            _check_adapter_capability_explicit_write_need_marker_admitted_strict(
                label,
                repo,
            )
        elif case_kind == "silent_write_grant_rejected_at_single_step_admission":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_silent_write_grant_rejected_single_step(
                    label
                ),
            )
        elif case_kind == "explicit_write_need_marker_single_step_proceeds":
            _check_adapter_capability_explicit_write_need_marker_single_step_proceeds(
                label
            )
        elif case_kind == "legacy_write_need_marker_not_recognized_strict":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_legacy_write_need_marker_not_recognized(
                    label,
                    repo,
                ),
            )
        elif case_kind == "legacy_write_need_graph_row_key_rejected":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_legacy_write_need_graph_row_key_rejected(
                    label
                ),
            )
        else:
            raise ProfileError(f"unknown adapter_capability_rehome case_kind: {case_kind}")
        count += 1
    return count


def _expect_adapter_capability_rejection(
    label: str,
    expected_reason: str,
    callback: Callable[[], Any],
) -> None:
    if not expected_reason:
        callback()
        return
    try:
        callback()
    except (TypeError, ValueError) as exc:
        if expected_reason not in str(exc):
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: expected reason "
                f"{expected_reason!r}, observed {exc!r}"
            ) from exc
        return
    raise ProfileError(f"adapter_capability_rehome_case expected rejection but passed: {label}")


def _adapter_capability_write_scope() -> Mapping[str, Any]:
    return {
        "allowed_paths": ["support/connection/agent_adapter.py"],
        "forbidden_paths": [".git/**", "*.pem", "*.key"],
    }


def _adapter_capability_request(
    *,
    adapter_ref: str,
    agent_object_ref: str = "agent-object:dev",
    tool_policy_refs: tuple[str, ...] = ("tool-policy:read-write-scoped",),
    write_scope: Mapping[str, Any] | None = None,
) -> Any:
    from brick_protocol.support.connection.agent_adapter import AgentAdapterRequest

    return AgentAdapterRequest(
        building_id="adapter-capability-rehome-case",
        agent_object_ref=agent_object_ref,
        adapter_ref=adapter_ref,
        brick_instance_ref="brick-adapter-capability-work",
        next_brick_instance_ref="brick-adapter-capability-closure",
        tool_policy_refs=tool_policy_refs,
        write_scope=write_scope or {},
        work_statement="Exercise adapter capability intersection.",
        comparison_rule="Support observes stable deny reason categories only.",
        required_return_shape="observed_evidence, not_proven",
    )


def _adapter_capability_plan(
    *,
    selected_adapter_ref: str,
    write_scope: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    brick_row: dict[str, Any] = {
        "axis": "Brick",
        "row_ref": "brick-row:adapter-capability-work",
        "brick_work_ref": "work:adapter-capability-work",
        "brick_instance_ref": "brick-adapter-capability-work",
        "work_statement": "Exercise adapter capability intersection.",
        "comparison_rule": "Support observes stable deny reason categories only.",
        "required_return_shape": "observed_evidence, not_proven",
    }
    if write_scope is not None:
        brick_row["write_scope"] = dict(write_scope)
    linear_plan = {
        "plan_ref": "building-plan:adapter-capability-rehome-case",
        "owner_axis": "Brick",
        "building_id": "adapter-capability-rehome-case",
        "plan_shape": "linear",
        "selected_adapter_ref": selected_adapter_ref,
        "steps": [
            {
                "step_ref": "adapter-capability-work",
                "rows": [
                    brick_row,
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:adapter-capability-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                    {
                        "axis": "Link",
                        "row_ref": "link-row:adapter-capability-work",
                        "movement": "forward",
                        "target_ref": "brick-adapter-capability-closure",
                    },
                ],
            }
        ],
    }
    return _graph_test_plan_from_linear(linear_plan)


def _check_adapter_capability_ok_all_four(label: str) -> None:
    from brick_protocol.support.connection.agent_adapter import adapter_capabilities
    from support.operator.plan_validation import validate_declared_building_plan
    from support.operator.write_observation import _validate_observed_write_path

    write_scope = _adapter_capability_write_scope()
    capabilities = adapter_capabilities("adapter:codex-local")
    if capabilities != ("read", "write"):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: "
            f"expected read/write capabilities, observed {capabilities!r}"
        )
    _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        write_scope=write_scope,
    )
    validate_declared_building_plan(
        _validation_plan_for_declared_plan(
            _adapter_capability_plan(
                selected_adapter_ref="adapter:codex-local",
                write_scope=write_scope,
            )
        )
    )
    _validate_observed_write_path(
        "support/connection/agent_adapter.py",
        tuple(write_scope["allowed_paths"]),
        tuple(write_scope["forbidden_paths"]),
    )


def _check_adapter_capability_claude_write_ok(label: str) -> None:
    from brick_protocol.support.connection.agent_adapter import (
        adapter_capabilities,
        _OBSERVED_WRITE_ADAPTER_REFS as _ADAPTER_OBSERVED_WRITE,
    )
    from support.operator.plan_validation import (
        _validate_declared_step_write_scope,
        _OBSERVED_WRITE_ADAPTER_REFS as _PLAN_OBSERVED_WRITE,
    )

    # Single-source tripwire: the operator preflight layer must gate on the SAME
    # observed-write set as the adapter authority layer. A re-forked stale local
    # copy makes these diverge and silently reject claude write at preflight.
    if _PLAN_OBSERVED_WRITE != _ADAPTER_OBSERVED_WRITE:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: plan_validation "
            f"observed-write set {sorted(_PLAN_OBSERVED_WRITE)!r} diverges from "
            f"adapter canonical {sorted(_ADAPTER_OBSERVED_WRITE)!r}"
        )
    capabilities = adapter_capabilities("adapter:claude-local")
    if capabilities != ("read", "write"):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: expected claude "
            f"read/write capabilities, observed {capabilities!r}"
        )
    # claude-local + Brick write_scope must be ACCEPTED by preflight write_scope
    # validation (fires RED against a codex-only stale observed-write copy).
    step = _adapter_capability_plan(
        selected_adapter_ref="adapter:claude-local",
        write_scope=_adapter_capability_write_scope(),
    )["brick_steps"][0]
    _validate_declared_step_write_scope(step, selected_adapter_ref="adapter:claude-local")


def _check_adapter_capability_missing_brick_scope(label: str) -> None:
    from support.operator.plan_validation import validate_declared_building_plan

    validate_declared_building_plan(
        _validation_plan_for_declared_plan(
            _adapter_capability_plan(
                selected_adapter_ref="adapter:codex-local",
                write_scope=None,
            )
        )
    )


def _check_adapter_capability_missing_agent_policy(label: str) -> None:
    _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        tool_policy_refs=(),
        write_scope=_adapter_capability_write_scope(),
    )


def _check_adapter_capability_missing_adapter_capability(label: str) -> None:
    from support.operator.plan_validation import validate_declared_building_plan

    validate_declared_building_plan(
        _validation_plan_for_declared_plan(
            _adapter_capability_plan(
                selected_adapter_ref="adapter:local",
                write_scope=_adapter_capability_write_scope(),
            )
        )
    )


def _check_adapter_capability_observation_out_of_scope(label: str) -> None:
    from support.operator.write_observation import _validate_observed_write_path

    write_scope = _adapter_capability_write_scope()
    _validate_observed_write_path(
        "support/connection/agent_resources.py",
        tuple(write_scope["allowed_paths"]),
        tuple(write_scope["forbidden_paths"]),
    )

def _check_adapter_capability_poc_read_only_with_write_scope(label: str) -> None:
    _adapter_capability_request(
        adapter_ref="adapter:local",
        write_scope=_adapter_capability_write_scope(),
    )


def _check_adapter_capability_legacy_identity_only(label: str) -> None:
    _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        agent_object_ref="agent-object:cto-lead",
        tool_policy_refs=("tool-policy:leader-coordination",),
        write_scope=_adapter_capability_write_scope(),
    )


def _check_adapter_capability_no_write_observation_without_scope(label: str) -> None:
    from support.operator.write_observation import _write_adapter_observation_before

    request = _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        write_scope=None,
    )
    before = _write_adapter_observation_before(request, adapter_cwd=Path.cwd())
    if before is not None:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: "
            "write-capable adapter without Brick write_scope must remain read-only"
        )


def _check_adapter_capability_write_capable_leader_effective_write_gated_by_brick_scope(
    label: str,
) -> None:
    """Effective-write LAW for a now-WRITE-CAPABLE LEADER Agent Object.

    The NEED<->CAPABILITY matcher dropped only the LANE gate (a write-capable
    leader may now serve a read-only-need brick); it did NOT drop the write NEED
    gate. This proves the NEED gate survives at effective_write: a leader Agent
    Object that carries tool-policy:read-write-scoped (agent-object:cto-lead)
    has effective_write == False when the Brick declares NO write_scope NEED and
    effective_write == True only when the Brick declares a write_scope NEED. So
    being write-CAPABLE never means write-EFFECTIVE absent the Brick NEED.
    """
    from brick_protocol.support.connection.agent_adapter import (
        agent_request_effective_write,
    )

    leader_policies = (
        "tool-policy:leader-coordination",
        "tool-policy:read-write-scoped",
    )
    # No Brick write_scope NEED -> a write-capable leader stays read-only.
    no_scope_request = _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        agent_object_ref="agent-object:cto-lead",
        tool_policy_refs=leader_policies,
        write_scope=None,
    )
    if agent_request_effective_write(no_scope_request) is not False:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader (agent-object:cto-lead) without a Brick write_scope NEED must "
            "have effective_write == False (the NEED gate, not the LANE gate)"
        )
    # Brick write_scope NEED declared -> the same write-capable leader gets write.
    with_scope_request = _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        agent_object_ref="agent-object:cto-lead",
        tool_policy_refs=leader_policies,
        write_scope=_adapter_capability_write_scope(),
    )
    if agent_request_effective_write(with_scope_request) is not True:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader (agent-object:cto-lead) WITH a Brick write_scope NEED must "
            "have effective_write == True"
        )


_WRITE_CAPABLE_LEADER_POLICIES = (
    "tool-policy:leader-coordination",
    "tool-policy:read-write-scoped",
)


def _check_adapter_capability_write_capable_leader_read_only_brick_projection(
    label: str,
) -> None:
    """PHYSICAL projection LAW: write-capable leader on a READ-ONLY Brick.

    The logical gate (agent_request_effective_write) already returns False for a
    write-capable leader on a read-only Brick (no write_scope NEED). This pins
    that the PHYSICAL provider projection -- the codex sandbox_mode and the
    claude tool set the CLI is actually launched with FOR A STEP -- is consistent
    with it: a write-capable leader (read-write-scoped) running a Brick that
    declares NO write NEED (write_need=False) must project a READ-ONLY codex
    sandbox AND a claude tool set with NO Edit / Write. This is the regression
    the projection fix prevents (the agent's CAPABILITY overriding the Brick
    NEED).

    Anti-tautology: this fires RED if either projection function stops gating on
    write_need (i.e. returns workspace-write / Edit+Write from tool_policy alone).
    """
    from brick_protocol.support.connection.agent_resources import (
        claude_tools_for_tool_policies,
        codex_sandbox_mode_for_tool_policies,
    )

    sandbox = codex_sandbox_mode_for_tool_policies(
        list(_WRITE_CAPABLE_LEADER_POLICIES), write_need=False
    )
    if sandbox != "read-only":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader on a read-only Brick (write_need=False) must project codex "
            f"sandbox_mode 'read-only', got {sandbox!r} (capability overrode the "
            "Brick NEED)"
        )
    claude = claude_tools_for_tool_policies(
        list(_WRITE_CAPABLE_LEADER_POLICIES), write_need=False
    )
    tools = list(claude["tools"])
    if "Edit" in tools or "Write" in tools:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader on a read-only Brick (write_need=False) must project a claude "
            f"tool set with NO Edit/Write, got {tools} (capability overrode the "
            "Brick NEED)"
        )
    if claude["write_capable"] is not False:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader on a read-only Brick must report write_capable False"
        )


def _check_adapter_capability_write_capable_leader_write_needed_brick_projection(
    label: str,
) -> None:
    """PHYSICAL projection LAW: write-capable leader on a WRITE-NEEDED Brick.

    The complement of the read-only case: do NOT over-restrict a legitimate
    write. A write-capable leader (read-write-scoped) running a Brick that
    declares a write NEED (write_need=True) must project a workspace-write codex
    sandbox AND a claude tool set that INCLUDES Edit + Write. This keeps the
    write_need gate from collapsing into a constant read-only projection (which
    would silently break every legitimate write step).
    """
    from brick_protocol.support.connection.agent_resources import (
        claude_tools_for_tool_policies,
        codex_sandbox_mode_for_tool_policies,
    )

    sandbox = codex_sandbox_mode_for_tool_policies(
        list(_WRITE_CAPABLE_LEADER_POLICIES), write_need=True
    )
    if sandbox != "workspace-write":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader on a write-needed Brick (write_need=True) must project codex "
            f"sandbox_mode 'workspace-write', got {sandbox!r} (over-restricted a "
            "legitimate write)"
        )
    claude = claude_tools_for_tool_policies(
        list(_WRITE_CAPABLE_LEADER_POLICIES), write_need=True
    )
    tools = list(claude["tools"])
    if "Edit" not in tools or "Write" not in tools:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader on a write-needed Brick (write_need=True) must project a "
            f"claude tool set INCLUDING Edit and Write, got {tools} "
            "(over-restricted a legitimate write)"
        )
    if claude["write_capable"] is not True:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader on a write-needed Brick must report write_capable True"
        )


def _check_adapter_capability_write_scope_on_read_only_brick_rejected(
    label: str,
) -> None:
    """Inverse declared-plan guard: write_scope on a read-only Brick is REJECTED.

    A declared plan brick row that records its write NEED explicitly as NO
    (requires_brick_write_scope false) but ALSO carries a write_scope is an axis
    leak -- the run-time provider projection would open write on a step that
    declared no write NEED. plan_validation must reject it. A write-needed step
    (NEED yes + write_scope) is NOT rejected; this raises only on the mismatch.
    """
    from support.operator.plan_validation import _validate_declared_step_write_scope

    plan = _adapter_capability_plan(
        selected_adapter_ref="adapter:codex-local",
        write_scope=_adapter_capability_write_scope(),
    )
    step = plan["brick_steps"][0]
    brick_row = step["rows"][0]
    # Record the Brick's declared write NEED as explicitly NO on the row, while a
    # write_scope is also present == the misconfiguration this guard catches.
    brick_row["requires_brick_write_scope"] = False
    _validate_declared_step_write_scope(step, selected_adapter_ref="adapter:codex-local")


def _check_adapter_capability_silent_write_grant_rejected_at_run_admission(
    label: str,
) -> None:
    """PIPELINE FIRE: the LIVE run admission rejects a SILENT write grant.

    Drives the REAL chain (run_building_plan -> strict
    validate_declared_building_plan with require_write_need_marker=True), not a
    projection helper: a smuggled plan whose brick row carries a write_scope but
    OMITS the explicit write NEED marker (requires_brick_write_scope) must be
    rejected at run admission BEFORE any provider launch. The command_runner
    sentinel guarantees no provider is reached: if admission silently admits the
    plan, the walk proceeds toward the adapter and the case goes RED (either the
    sentinel raises or a non-matching error surfaces). This is exactly how the
    case REDs when the strict knob is disabled at the run.py call site
    (anti-tautology: the case exercises the live wiring, not the validator in
    isolation).
    """
    from support.operator.run import run_building_plan

    plan = _adapter_capability_plan(
        selected_adapter_ref="adapter:codex-local",
        write_scope=_adapter_capability_write_scope(),
    )

    def _sentinel_command_runner(_args: Any, _cwd: Any, _timeout: Any) -> Any:
        raise AssertionError(
            "silent write grant reached the provider command runner: strict run "
            "admission did not fire"
        )

    with tempfile.TemporaryDirectory(prefix="bp-silent-write-grant-fire-") as tmpdir:
        run_building_plan(
            plan,
            output_root=Path(tmpdir),
            overwrite_existing=True,
            command_runner=_sentinel_command_runner,
            adapter_cwd=Path(tmpdir),
            adapter_timeout_seconds=10,
        )


def _check_adapter_capability_explicit_write_need_marker_admitted_strict(
    label: str,
    repo: Path,
) -> None:
    """PASS leg + physical projection for the strict no-silent-write-grant gate.

    1. The SAME plan shape as the smuggled-plan FIRE case, but WITH the explicit
       positive marker (requires_brick_write_scope: true) on the brick row, must
       PASS strict validation (require_write_need_marker=True) -- the gate
       demands a DECLARED need, it does not block declared writes.
    2. Request construction + sandbox projection (no real CLI launch): a request
       WITHOUT write_scope projects codex sandbox 'read-only' and a read-only
       claude invocation (plan mode, read-only browse tools Read/Grep/Glob, no
       Edit/Write/Bash -- CLEAN-READTIER-0617: a read-only Brick + tool-capable
       Agent browses read-only, it is no longer the none tier); a request WITH
       the scope the marker-bearing row declares projects codex 'workspace-write'
       and a claude invocation including Edit + Write.
    """
    from brick_protocol.support.connection import agent_adapter as adapter
    from support.operator.plan_validation import validate_declared_building_plan

    plan = _adapter_capability_plan(
        selected_adapter_ref="adapter:codex-local",
        write_scope=_adapter_capability_write_scope(),
    )
    brick_row = dict(plan["brick_steps"][0]["rows"][0])
    brick_row["requires_brick_write_scope"] = True
    plan["brick_steps"][0]["rows"][0] = brick_row
    try:
        validate_declared_building_plan(
            _validation_plan_for_declared_plan(plan),
            repo_root=repo,
            require_write_need_marker=True,
        )
    except (TypeError, ValueError) as exc:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a plan whose brick "
            "row EXPLICITLY declares requires_brick_write_scope: true next to its "
            f"write_scope must pass strict run admission, got {exc!r}"
        ) from exc

    no_scope_codex = _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        write_scope=None,
    )
    observed_sandbox = adapter._codex_sandbox_for_request(no_scope_codex)
    if observed_sandbox != "read-only":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: request WITHOUT "
            f"write_scope must project codex sandbox 'read-only', got {observed_sandbox!r}"
        )
    no_scope_claude_request = _adapter_capability_request(
        adapter_ref="adapter:claude-local",
        write_scope=None,
    )
    no_scope_claude = adapter._claude_cli_invocation(no_scope_claude_request)
    # CLEAN-READTIER-0617: a read-only Brick (no write_scope) + a tool-capable
    # Agent (read-write-scoped policy) browses read-only -- plan mode with the
    # Read/Grep/Glob browse tools, NEVER Edit/Write/Bash. Read/write tier is no
    # longer a support authority over the policy label.
    no_scope_tools = [
        tool.strip() for tool in str(no_scope_claude.get("tools", "")).split(",") if tool.strip()
    ]
    if no_scope_claude.get("permission_mode") != "plan" or no_scope_tools != ["Read", "Grep", "Glob"]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: request WITHOUT "
            "write_scope must project the read-only browse claude invocation "
            f"(plan mode, Read/Grep/Glob tools), got {no_scope_claude!r}"
        )
    if any(tool in no_scope_tools for tool in ("Edit", "Write", "Bash")):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: read-only browse "
            f"claude invocation leaked a write/shell tool, got {no_scope_claude!r}"
        )

    scoped_codex = _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        write_scope=_adapter_capability_write_scope(),
    )
    observed_sandbox = adapter._codex_sandbox_for_request(scoped_codex)
    if observed_sandbox != "workspace-write":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: request WITH the "
            "marker-bearing row's write_scope must project codex sandbox "
            f"'workspace-write', got {observed_sandbox!r}"
        )
    scoped_claude = adapter._claude_cli_invocation(
        _adapter_capability_request(
            adapter_ref="adapter:claude-local",
            write_scope=_adapter_capability_write_scope(),
        )
    )
    scoped_tools = str(scoped_claude.get("tools", ""))
    if (
        scoped_claude.get("permission_mode") != "acceptEdits"
        or "Edit" not in scoped_tools.split(",")
        or "Write" not in scoped_tools.split(",")
    ):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: request WITH the "
            "marker-bearing row's write_scope must project a claude invocation "
            f"including Edit + Write (acceptEdits), got {scoped_claude!r}"
        )


def _check_adapter_capability_legacy_write_need_marker_not_recognized(
    label: str,
    repo: Path,
) -> None:
    """L legacy cut FIRE (0610): the retired ``write_need`` row marker is NOT a NEED.

    A plan whose brick row carries a write_scope plus ONLY the retired legacy
    ``write_need: true`` spelling (no ``requires_brick_write_scope``) must FAIL
    strict run admission with the no-SILENT-write-grant rejection: the legacy
    spelling is retired, so it counts as NO declared NEED -- never as a silent
    synonym. Anti-tautology: re-admitting the legacy branch in
    plan_validation._declared_brick_write_need makes this plan pass strict
    validation and the case goes RED (the expected rejection never fires).
    """
    from support.operator.plan_validation import validate_declared_building_plan

    graph_plan = _adapter_capability_plan(
        selected_adapter_ref="adapter:codex-local",
        write_scope=_adapter_capability_write_scope(),
    )
    plan = dict(_validation_plan_for_declared_plan(graph_plan))
    brick_row = dict(plan["steps"][0]["rows"][0])
    brick_row["write_need"] = True
    plan["steps"][0]["rows"][0] = brick_row
    validate_declared_building_plan(
        plan,
        repo_root=repo,
        require_write_need_marker=True,
    )


def _check_adapter_capability_legacy_write_need_graph_row_key_rejected(
    label: str,
) -> None:
    """L legacy cut FIRE (0610): a graph Brick row carrying ``write_need`` is unadmitted.

    POSITIVE control first: the same graph brick step WITHOUT the retired key
    passes the REAL graph row admission (plan_graph._graph_brick_agent_rows ->
    _require_only_keys over primitives._BRICK_ROW_ALLOWED_KEYS). Then the retired
    legacy key is added and the SAME admission must reject the row as carrying an
    unadmitted key (loud, named -- never silently ignored). Anti-tautology:
    re-admitting 'write_need' into _BRICK_ROW_ALLOWED_KEYS makes the mutated step
    pass and the case goes RED (the expected rejection never fires).
    """
    from support.operator.plan_graph import _graph_brick_agent_rows

    def _graph_step(extra_brick_keys: Mapping[str, Any] | None) -> dict[str, Any]:
        brick_row: dict[str, Any] = {
            "axis": "Brick",
            "row_ref": "brick-row:legacy-write-need-graph",
            "brick_work_ref": "work:legacy-write-need-graph",
            "brick_instance_ref": "brick-legacy-write-need-graph",
            "work_statement": "Exercise graph row key admission.",
            "comparison_rule": "Support observes row-key admission only.",
            "required_return_shape": "observed_evidence, not_proven",
        }
        if extra_brick_keys:
            brick_row.update(extra_brick_keys)
        return {
            "step_ref": "legacy-write-need-graph",
            "rows": [
                brick_row,
                {
                    "axis": "Agent",
                    "row_ref": "agent-row:legacy-write-need-graph",
                    "agent_object_ref": "agent-object:dev",
                },
            ],
        }

    try:
        _graph_brick_agent_rows(_graph_step(None))
    except (TypeError, ValueError) as exc:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: the POSITIVE "
            "control graph step (no legacy key) must pass graph row admission, "
            f"got {exc!r}"
        ) from exc
    _graph_brick_agent_rows(_graph_step({"write_need": True}))


def _adapter_capability_single_step_packet(
    *,
    write_scope: Mapping[str, Any] | None,
    requires_brick_write_scope: bool | None,
) -> dict[str, Any]:
    """Single-step ``run_building_once`` packet (``step_rows`` fixture surface).

    Mirrors ``_adapter_capability_plan`` for the OTHER live admission surface:
    the fixture-packet entry that bypasses plan-level validation entirely. The
    brick row optionally smuggles a write_scope with or without the explicit
    write NEED marker.
    """

    brick_row: dict[str, Any] = {
        "axis": "Brick",
        "row_ref": "brick-row:adapter-capability-once",
        "brick_work_ref": "work:adapter-capability-once",
        "brick_instance_ref": "brick-adapter-capability-once",
        "work_statement": "Exercise single-step run admission.",
        "comparison_rule": "Support observes stable deny reason categories only.",
        "required_return_shape": "observed_evidence, not_proven",
    }
    if write_scope is not None:
        brick_row["write_scope"] = dict(write_scope)
    if requires_brick_write_scope is not None:
        brick_row["requires_brick_write_scope"] = requires_brick_write_scope
    return {
        "building_id": "adapter-capability-once-case",
        "selected_adapter_ref": "adapter:codex-local",
        "step_rows": {
            "step_ref": "adapter-capability-once",
            "rows": [
                brick_row,
                {
                    "axis": "Agent",
                    "row_ref": "agent-row:adapter-capability-once",
                    "agent_object_ref": "agent-object:dev",
                },
                {
                    "axis": "Link",
                    "row_ref": "link-row:adapter-capability-once",
                    "movement": "forward",
                    "target_ref": "brick-adapter-capability-closure",
                    "next_brick_instance_ref": "brick-adapter-capability-closure",
                },
            ],
        },
        "caller_supplied_link_facts": {
            "movement_fact": {"movement": "forward"},
            "transition_fact": {
                "movement": "forward",
                "target_fact": "brick-adapter-capability-closure",
            },
        },
    }


def _check_adapter_capability_silent_write_grant_rejected_single_step(
    label: str,
) -> None:
    """PIPELINE FIRE: run_building_once rejects a SILENT write grant at admission.

    Drives the REAL single-step surface (run_building_once over a step_rows
    fixture packet), the one admission point that performs NO plan-level
    validation: a smuggled brick row carrying a write_scope but OMITTING the
    explicit write NEED marker (requires_brick_write_scope) must be rejected
    BEFORE any provider invocation. The command_runner sentinel proves no
    provider is reached: it records every invocation and the case raises if the
    record is non-empty after admission fired. If the single-step admission
    guard is removed, the run proceeds into the adapter, the sentinel records
    its invocation, and the case goes RED (anti-tautology: the case exercises
    the live run_building_once wiring, not the validator helper in isolation).
    """
    from support.operator.run import run_building_once

    packet = _adapter_capability_single_step_packet(
        write_scope=_adapter_capability_write_scope(),
        requires_brick_write_scope=None,
    )
    sentinel_invocations: list[Any] = []

    def _sentinel_command_runner(args: Any, _cwd: Any, _timeout: Any) -> Any:
        sentinel_invocations.append(args)
        raise AssertionError(
            "silent write grant reached the provider command runner on the "
            "single-step surface: strict run_building_once admission did not fire"
        )

    with tempfile.TemporaryDirectory(prefix="bp-silent-write-grant-once-fire-") as tmpdir:
        try:
            run_building_once(
                packet,
                output_root=Path(tmpdir),
                overwrite_existing=True,
                command_runner=_sentinel_command_runner,
                adapter_cwd=Path(tmpdir),
                adapter_timeout_seconds=10,
            )
        finally:
            if sentinel_invocations:
                raise ProfileError(
                    f"adapter_capability_rehome_case rejected {label}: the provider "
                    "sentinel WAS invoked -- the smuggled single-step write_scope "
                    "passed run_building_once admission"
                )


def _check_adapter_capability_explicit_write_need_marker_single_step_proceeds(
    label: str,
) -> None:
    """PASS leg for the single-step strict gate: declared NEED is NOT blocked.

    The SAME single-step packet as the smuggled FIRE case, but WITH the explicit
    positive marker (requires_brick_write_scope: true) on the brick row, must
    proceed PAST run_building_once admission and reach the provider boundary
    (the command_runner sentinel) -- the gate demands a DECLARED need, it does
    not over-restrict declared writes. The sentinel interrupts the adapter, so
    no real CLI launches; run_building_once then surfaces the interruption as
    AdapterFrontierEvidenceWritten (frontier evidence into the tmpdir root),
    which is the expected outcome here, NOT a rejection.
    """
    from support.operator.run import AdapterFrontierEvidenceWritten, run_building_once

    packet = _adapter_capability_single_step_packet(
        write_scope=_adapter_capability_write_scope(),
        requires_brick_write_scope=True,
    )
    sentinel_invocations: list[Any] = []

    class _ProviderSentinelReached(Exception):
        pass

    def _sentinel_command_runner(args: Any, _cwd: Any, _timeout: Any) -> Any:
        sentinel_invocations.append(args)
        raise _ProviderSentinelReached("provider sentinel reached past strict admission")

    with tempfile.TemporaryDirectory(prefix="bp-explicit-write-need-once-pass-") as tmpdir:
        try:
            run_building_once(
                packet,
                output_root=Path(tmpdir),
                overwrite_existing=True,
                command_runner=_sentinel_command_runner,
                adapter_cwd=Path(tmpdir),
                adapter_timeout_seconds=10,
            )
        except AdapterFrontierEvidenceWritten:
            pass  # sentinel interrupted the adapter AFTER admission == expected
        except (TypeError, ValueError) as exc:
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: a single-step "
                "packet whose brick row EXPLICITLY declares "
                "requires_brick_write_scope: true next to its write_scope must "
                f"proceed past strict run_building_once admission, got {exc!r}"
            ) from exc
    if not sentinel_invocations:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: the marker-bearing "
            "single-step packet never reached the provider sentinel "
            "(over-restriction or a pre-provider failure)"
        )


def _once_task_source_packet(task_source_ref: str | None) -> dict[str, Any]:
    """Single-step run_building_once packet for the task-source admission FIRE."""

    packet: dict[str, Any] = {
        "building_id": "once-task-source-admission-case",
        "selected_adapter_ref": "adapter:codex-local",
        "step_rows": {
            "step_ref": "once-task-source-admission",
            "rows": [
                {
                    "axis": "Brick",
                    "row_ref": "brick-row:once-task-source-admission",
                    "brick_work_ref": "work:once-task-source-admission",
                    "brick_instance_ref": "brick-once-task-source-admission",
                    "work_statement": "Exercise single-step task-source admission.",
                    "comparison_rule": "Support observes admission rejects only.",
                    "required_return_shape": "observed_evidence, not_proven",
                },
                {
                    "axis": "Agent",
                    "row_ref": "agent-row:once-task-source-admission",
                    "agent_object_ref": "agent-object:dev",
                },
                {
                    "axis": "Link",
                    "row_ref": "link-row:once-task-source-admission",
                    "movement": "forward",
                    "target_ref": "brick-once-task-source-closure",
                    "next_brick_instance_ref": "brick-once-task-source-closure",
                },
            ],
        },
        "caller_supplied_link_facts": {
            "movement_fact": {"movement": "forward"},
            "transition_fact": {
                "movement": "forward",
                "target_fact": "brick-once-task-source-closure",
            },
        },
    }
    if task_source_ref is not None:
        packet["task_source_ref"] = task_source_ref
    return packet


def run_once_task_source_admission_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """FIX-C (codex review 0611): run_building_once validates the task source.

    Before the fix, run_building_once performed NO task_source_ref validation:
    a fixture declaring a missing task file silently skipped the body
    (_source_fact_bodies returns {} for unreadable refs) and the run proceeded
    without its declared task. This case pins the HARD-FAIL at single-step
    admission, parity with run_building_plan strictness (P11b):

      1. MISSING-FILE REJECT: a once-packet declaring a repo-path
         task_source_ref that does not exist must reject with the VERBATIM
         walker message ("task_source_ref declared file does not exist: ...")
         BEFORE the provider boundary (sentinel command runner never invoked).
      2. VALID PROCEEDS: the SAME packet with an existing task file proceeds
         past admission to the provider sentinel (no over-restriction);
         AdapterFrontierEvidenceWritten is the expected surfaced outcome.
      3. INLINE SENTINEL HONESTY (TASK-BY-TEXT 0611): the
         task-source:inline-statement sentinel WITHOUT a carried
         task_statement body rejects; WITH the body it proceeds to the
         provider sentinel -- both task-source forms stay honest on the
         single-step surface.

    Anti-tautology: remove the run_building_once admission guard and (1) and
    the no-body leg of (3) go RED (the run reaches the provider sentinel,
    which raises and fails the case).
    """
    items = rule_items(profile, "run_once_task_source_admission_case")
    if not items:
        return 0
    from support.operator.run import AdapterFrontierEvidenceWritten, run_building_once

    count = 0
    for item in items:
        mapping = require_mapping(item, "run_once_task_source_admission_case item")
        label = require_string(
            mapping.get("label"), "run_once_task_source_admission_case.label"
        )
        missing_ref = require_string(
            mapping.get("missing_task_source_ref"),
            f"{label}: missing_task_source_ref",
        )
        valid_ref = require_string(
            mapping.get("valid_task_source_ref"), f"{label}: valid_task_source_ref"
        )
        if (repo / missing_ref).exists():
            raise ProfileError(
                f"run_once_task_source_admission_case rejected {label}: the declared "
                f"missing_task_source_ref EXISTS in the repo: {missing_ref}"
            )
        if not (repo / valid_ref).is_file():
            raise ProfileError(
                f"run_once_task_source_admission_case rejected {label}: the declared "
                f"valid_task_source_ref does not exist in the repo: {valid_ref}"
            )

        def _probe(
            packet: dict[str, Any],
            *,
            expect_reject_fragment: str | None,
            leg: str,
        ) -> None:
            sentinel_invocations: list[Any] = []

            def _sentinel_command_runner(args: Any, _cwd: Any, _timeout: Any) -> Any:
                sentinel_invocations.append(args)
                raise _OnceTaskSourceSentinelReached(
                    "provider sentinel reached past single-step admission"
                )

            with tempfile.TemporaryDirectory(
                prefix="bp-once-task-source-admission-"
            ) as tmpdir:
                try:
                    run_building_once(
                        packet,
                        output_root=Path(tmpdir),
                        overwrite_existing=True,
                        command_runner=_sentinel_command_runner,
                        adapter_cwd=Path(tmpdir),
                        adapter_timeout_seconds=10,
                    )
                except AdapterFrontierEvidenceWritten:
                    if expect_reject_fragment is not None:
                        raise ProfileError(
                            f"run_once_task_source_admission_case rejected {label}/{leg}: "
                            "the packet reached the provider boundary; the task-source "
                            "admission guard did not fire"
                        ) from None
                except ValueError as exc:
                    if expect_reject_fragment is None:
                        raise ProfileError(
                            f"run_once_task_source_admission_case rejected {label}/{leg}: "
                            f"expected the packet to proceed past admission, got {exc!r}"
                        ) from exc
                    if expect_reject_fragment not in str(exc):
                        raise ProfileError(
                            f"run_once_task_source_admission_case rejected {label}/{leg}: "
                            f"rejected for the WRONG reason: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"run_once_task_source_admission_case rejected {label}/{leg}: "
                        "run_building_once returned without reject or provider sentinel"
                    )
            if expect_reject_fragment is not None and sentinel_invocations:
                raise ProfileError(
                    f"run_once_task_source_admission_case rejected {label}/{leg}: the "
                    "provider sentinel WAS invoked despite the expected admission reject"
                )
            if expect_reject_fragment is None and not sentinel_invocations:
                raise ProfileError(
                    f"run_once_task_source_admission_case rejected {label}/{leg}: the "
                    "packet never reached the provider sentinel (over-restriction or a "
                    "pre-provider failure)"
                )

        # (1) missing-file -> VERBATIM loud reject before the provider boundary.
        _probe(
            _once_task_source_packet(missing_ref),
            expect_reject_fragment=(
                f"task_source_ref declared file does not exist: {missing_ref}"
            ),
            leg="missing-file-reject",
        )
        # (2) valid file -> proceeds past admission (no over-restriction).
        _probe(
            _once_task_source_packet(valid_ref),
            expect_reject_fragment=None,
            leg="valid-proceeds",
        )
        # (3) inline sentinel honesty on the once surface.
        _probe(
            _once_task_source_packet("task-source:inline-statement"),
            expect_reject_fragment=(
                "requires the plan to carry a non-empty task_statement body"
            ),
            leg="inline-sentinel-without-body-reject",
        )
        inline_packet = _once_task_source_packet("task-source:inline-statement")
        inline_packet["task_statement"] = "단일 스텝 인라인 본문 허용 확인.\n"
        _probe(
            inline_packet,
            expect_reject_fragment=None,
            leg="inline-sentinel-with-body-proceeds",
        )
        count += 1
    return count


class _OnceTaskSourceSentinelReached(Exception):
    """Marker raised by the FIX-C provider sentinel (never escapes the probe)."""


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
    """P6 axis guard: every hook in agent/hooks/registry.yaml is an Agent-axis
    advisory/deny guard carrying NO judgment; plus each profile-declared negative
    fixture must be rejected with its expected reason."""
    count = 0
    registry_path = repo / "agent" / "hooks" / "registry.yaml"
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


def run_write_scope_default_exclude_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "write_scope_default_exclude_case")
    if not items:
        return 0
    count = 0
    for item in items:
        mapping = require_mapping(item, "write_scope_default_exclude_case item")
        label = require_string(mapping.get("label"), "write_scope_default_exclude_case.label")
        case_kind = require_string(mapping.get("case_kind"), f"{label}: case_kind")
        if case_kind == "provider_residue_excluded":
            _check_provider_residue_excluded(label)
        elif case_kind == "directory_allowed_path_is_not_recursive":
            _check_directory_allowed_path_is_not_recursive(label)
        elif case_kind == "explicit_wildcard_allows_children":
            _check_explicit_wildcard_allows_children(label)
        elif case_kind == "token_shaped_filename_short_marker_accepted":
            _check_token_shaped_filename_short_marker_accepted(label)
        elif case_kind == "raw_secret_rejected":
            _check_raw_secret_rejected(label)
        elif case_kind == "building_plan_support_result_no_record_converter":
            _check_building_plan_support_result_no_record_converter(label)
        elif case_kind == "dirty_root_reuse_requires_overwrite_or_new_root":
            _check_dirty_root_reuse_requires_overwrite_or_new_root(label)
        else:
            raise ProfileError(f"unknown write_scope_default_exclude case_kind: {case_kind}")
        count += 1
    return count


def _check_provider_residue_excluded(label: str) -> None:
    from support.operator.write_observation import (
        _is_write_observation_default_excluded_residue,
        _observed_file_snapshot,
    )

    if not _is_write_observation_default_excluded_residue(Path(".claude/launch.json")):
        raise ProfileError(f"write_scope_default_exclude_case rejected {label}: .claude residue not excluded")
    # W2 DOC-DECOUPLE FIRE (0611): the 3 provider-residue names were previously
    # stated only in the (now archived) 0526 spec doc text pin — decoration, not
    # enforcement (removing a name from the code set never REDed). Probe the
    # exact residue set membership so a silent narrowing of the default-exclude
    # set goes RED via the CODE path.
    for residue_path in ("x/__pycache__/y.pyc", "x/.ruff_cache/z", "x/.DS_Store"):
        if not _is_write_observation_default_excluded_residue(Path(residue_path)):
            raise ProfileError(
                f"write_scope_default_exclude_case rejected {label}: provider residue {residue_path} not excluded"
            )
    with tempfile.TemporaryDirectory(prefix="bp-write-scope-default-exclude-") as tmpdir:
        root = Path(tmpdir)
        (root / ".claude").mkdir()
        (root / ".claude" / "launch.json").write_text("{}", encoding="utf-8")
        (root / "work").mkdir()
        (root / "work" / "kept.txt").write_text("kept", encoding="utf-8")
        snapshot = _observed_file_snapshot(root)
    if ".claude/launch.json" in snapshot:
        raise ProfileError(f"write_scope_default_exclude_case rejected {label}: .claude file observed")
    if "work/kept.txt" not in snapshot:
        raise ProfileError(f"write_scope_default_exclude_case rejected {label}: non-residue file missing")


def _check_directory_allowed_path_is_not_recursive(label: str) -> None:
    from support.operator.write_observation import _validate_observed_write_path

    try:
        _validate_observed_write_path(
            "project/example/work/building-map.json",
            ("project/example",),
            (),
        )
    except ValueError as exc:
        if "outside write_scope" not in str(exc):
            raise ProfileError(
                f"write_scope_default_exclude_case rejected {label}: wrong rejection {exc}"
            ) from exc
        return
    raise ProfileError(f"write_scope_default_exclude_case expected directory child rejection: {label}")


def _check_explicit_wildcard_allows_children(label: str) -> None:
    from support.operator.write_observation import _validate_observed_write_path

    try:
        _validate_observed_write_path(
            "project/example/work/building-map.json",
            ("project/example/**",),
            (),
        )
    except ValueError as exc:
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: wildcard did not allow child"
        ) from exc


def _check_token_shaped_filename_short_marker_accepted(label: str) -> None:
    from support.operator.primitives import _FORBIDDEN_PAYLOAD_KEYS, _validate_no_payload_forbidden

    try:
        _validate_no_payload_forbidden(
            "plan",
            # W2 DOC-DECOUPLE (0611): synthetic NON-EXISTENT filename (in-memory
            # payload only); the probe needs a short 'sk-' basename that must
            # NOT be misdetected as a raw secret. Neutral template-tree prefix,
            # no status/kernel doc-shape reference.
            {"task_source_ref": "brick/templates/tasks/sk-demo.md"},
            _FORBIDDEN_PAYLOAD_KEYS,
        )
    except ValueError as exc:
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: short marker filename rejected"
        ) from exc


def _check_raw_secret_rejected(label: str) -> None:
    from support.operator.primitives import _FORBIDDEN_PAYLOAD_KEYS, _validate_no_payload_forbidden

    raw_secret = "sk-" + ("a" * 16)
    try:
        _validate_no_payload_forbidden(
            "plan",
            {"task_source_ref": raw_secret},
            _FORBIDDEN_PAYLOAD_KEYS,
        )
    except ValueError as exc:
        if "raw credential-looking text" not in str(exc):
            raise ProfileError(
                f"write_scope_default_exclude_case rejected {label}: wrong raw secret rejection {exc}"
            ) from exc
        return
    raise ProfileError(f"write_scope_default_exclude_case expected raw secret rejection: {label}")


def _check_building_plan_support_result_no_record_converter(label: str) -> None:
    from support.operator.contracts import BuildingPlanSupportResult

    method_name = "to_" + "record"
    if hasattr(BuildingPlanSupportResult, method_name):
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: unexpected record converter API"
        )


def _check_dirty_root_reuse_requires_overwrite_or_new_root(label: str) -> None:
    from support.operator.run import _preflight_step_output_building_root

    with tempfile.TemporaryDirectory(prefix="bp-dirty-root-reuse-") as tmpdir:
        root = Path(tmpdir)
        building_id = "checker-dirty-root"
        (root / building_id).mkdir()
        try:
            _preflight_step_output_building_root(
                root,
                building_id,
                overwrite_existing=False,
            )
        except FileExistsError as exc:
            if "choose a new building_id or pass overwrite_existing=True" not in str(exc):
                raise ProfileError(
                    f"write_scope_default_exclude_case rejected {label}: wrong root reuse rejection {exc}"
                ) from exc
            return
    raise ProfileError(f"write_scope_default_exclude_case expected dirty-root rejection: {label}")


def run_source_fact_body_carry_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "source_fact_body_carry_case")
    if not items:
        return 0
    from support.operator.walker_kernel import _source_fact_body_carry_for_step

    count = 0
    for item in items:
        mapping = require_mapping(item, "source_fact_body_carry_case item")
        label = require_string(mapping.get("label"), "source_fact_body_carry_case.label")
        target_step_ref = require_string(
            mapping.get("target_step_ref"),
            f"{label}: target_step_ref",
        )
        cascade_depth = _optional_non_negative_int(
            mapping.get("cascade_depth", 0),
            f"{label}: cascade_depth",
        )
        source_facts = require_string_list(
            mapping.get("consumer_source_facts", []),
            f"{label}: consumer_source_facts",
        )
        step_results, step_result_events = _source_fact_body_carry_step_results(
            mapping,
            label=label,
            default_cascade_depth=cascade_depth,
        )
        building_id = str(mapping.get("building_id", "") or "checker-source-fact-body-carry")
        with tempfile.TemporaryDirectory(prefix="bp-source-fact-body-carry-") as tmpdir:
            building_root = Path(tmpdir) / building_id
            _write_source_fact_body_carry_outputs(
                building_root,
                building_id,
                step_results,
            )
            result = _source_fact_body_carry_for_step(
                building_root=building_root,
                building_id=building_id,
                target_step_ref=target_step_ref,
                cascade_depth=cascade_depth,
                step={"rows": [{"axis": "Brick", "source_facts": source_facts}]},
                step_results=step_results,
                step_result_events=step_result_events,
                fan_in_sources_by_target=_source_fact_body_carry_fan_in_sources(mapping, label),
            )
        observation = result.get("observation")
        if not isinstance(observation, Mapping):
            raise ProfileError(f"source_fact_body_carry_case rejected {label}: observation missing")
        expected = require_mapping(
            mapping.get("expected", {}),
            f"{label}: expected",
        )
        _check_expected_bool(
            observation,
            expected,
            key="body_absent",
            label=label,
        )
        _check_expected_sequence(
            list(result.get("source_fact_bodies", {})),
            expected,
            key="source_fact_body_refs",
            label=label,
        )
        _check_expected_sequence(
            list(observation.get("declared_source_fact_refs", ())),
            expected,
            key="declared_source_fact_refs",
            label=label,
        )
        _check_expected_sequence(
            list(observation.get("missing_source_fact_refs", ())),
            expected,
            key="missing_source_fact_refs",
            label=label,
        )
        _check_expected_sequence_contains(
            list(observation.get("missing_source_fact_refs", ())),
            expected,
            key="missing_source_fact_refs_contains",
            label=label,
        )
        _check_source_fact_body_expectations(
            result.get("source_fact_bodies", {}),
            expected.get("body_expectations", []),
            label=label,
        )
        count += 1
    return count


def _write_source_fact_body_carry_outputs(
    building_root: Path,
    building_id: str,
    step_results: list[Any],
) -> None:
    from support.recording.contracts import StepOutputObservation
    from support.recording.step_outputs import write_step_output

    counts: dict[str, int] = {}
    for index, result in enumerate(step_results, start=1):
        step_ref = result.preparation.step_rows.step_ref
        counts[step_ref] = counts.get(step_ref, 0) + 1
        write_step_output(
            building_root,
            building_id,
            StepOutputObservation(
                building_id=building_id,
                step_ref=step_ref,
                brick_instance_ref=result.preparation.brick_instance_ref,
                agent_object_ref=result.preparation.agent_object.object_ref,
                returned=result.adapter_result.returned_value,
                received_work_ref=f"brick-work:{index:02d}:{step_ref}",
                returned_fact_ref=f"agent-fact:{index:02d}:{step_ref}",
                raw_ref=f"raw:agent:{index:02d}",
                not_proven=tuple(result.not_proven),
                recorded_at="2026-01-01T00:00:00Z",
            ),
            attempt_index=counts[step_ref],
            proof_limits=("support checker synthetic result only",),
            recorded_at="2026-01-01T00:00:00Z",
        )


def _source_fact_body_carry_step_results(
    mapping: Mapping[str, Any],
    *,
    label: str,
    default_cascade_depth: int,
) -> tuple[list[Any], list[Mapping[str, Any]]]:
    raw_items = mapping.get("upstream_results", [])
    if not isinstance(raw_items, list):
        raise ProfileError(f"{label}: upstream_results must be a list")
    step_results: list[Any] = []
    step_result_events: list[Mapping[str, Any]] = []
    for index, raw_item in enumerate(raw_items, start=1):
        item = require_mapping(raw_item, f"{label}: upstream_results[{index}]")
        step_ref = require_string(item.get("step_ref"), f"{label}: upstream_results[{index}].step_ref")
        cascade_depth = _optional_non_negative_int(
            item.get("cascade_depth", default_cascade_depth),
            f"{label}: upstream_results[{index}].cascade_depth",
        )
        returned = item.get("returned", {})
        if not isinstance(returned, Mapping):
            raise ProfileError(f"{label}: upstream_results[{index}].returned must be a mapping")
        step_results.append(_source_fact_body_carry_synthetic_result(step_ref, returned))
        step_result_events.append({"step_ref": step_ref, "cascade_depth": cascade_depth})
    return step_results, step_result_events


def _source_fact_body_carry_synthetic_result(step_ref: str, returned: Mapping[str, Any]) -> Any:
    return SimpleNamespace(
        preparation=SimpleNamespace(
            step_rows=SimpleNamespace(step_ref=step_ref),
            brick_instance_ref=f"brick:{step_ref}",
            agent_object=SimpleNamespace(object_ref="agent-object:checker-local"),
        ),
        adapter_result=SimpleNamespace(returned_value=dict(returned)),
        proof_limits=("support checker synthetic result only",),
        not_proven=("semantic sufficiency of carried body",),
    )


def _source_fact_body_carry_fan_in_sources(
    mapping: Mapping[str, Any],
    label: str,
) -> Mapping[str, tuple[str, ...]]:
    raw_sources = mapping.get("fan_in_sources_by_target", {})
    if not isinstance(raw_sources, Mapping):
        raise ProfileError(f"{label}: fan_in_sources_by_target must be a mapping")
    return {
        require_string(target, f"{label}: fan_in_sources_by_target target"): tuple(
            require_string_list(sources, f"{label}: fan_in_sources_by_target[{target}]")
        )
        for target, sources in raw_sources.items()
    }


def _optional_non_negative_int(value: Any, label: str) -> int:
    text = str(value).strip()
    if not text.isdecimal():
        raise ProfileError(f"{label} must be a non-negative integer")
    return int(text)


def _check_expected_bool(
    observed: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    key: str,
    label: str,
) -> None:
    if key not in expected:
        return
    expected_value = expected[key]
    if not isinstance(expected_value, bool):
        raise ProfileError(f"{label}: expected.{key} must be a boolean")
    if bool(observed.get(key)) != expected_value:
        raise ProfileError(
            f"source_fact_body_carry_case rejected {label}: "
            f"{key} expected {expected_value!r}, observed {observed.get(key)!r}"
        )


def _check_expected_sequence(
    observed: Sequence[str],
    expected: Mapping[str, Any],
    *,
    key: str,
    label: str,
) -> None:
    if key not in expected:
        return
    expected_items = require_string_list(expected.get(key, []), f"{label}: expected.{key}")
    if list(observed) != expected_items:
        raise ProfileError(
            f"source_fact_body_carry_case rejected {label}: "
            f"{key} expected {expected_items!r}, observed {list(observed)!r}"
        )


def _check_expected_sequence_contains(
    observed: Sequence[str],
    expected: Mapping[str, Any],
    *,
    key: str,
    label: str,
) -> None:
    if key not in expected:
        return
    expected_items = require_string_list(expected.get(key, []), f"{label}: expected.{key}")
    missing = [item for item in expected_items if item not in observed]
    if missing:
        raise ProfileError(
            f"source_fact_body_carry_case rejected {label}: "
            f"{key} missing {missing!r}, observed {list(observed)!r}"
        )


def _check_source_fact_body_expectations(
    source_fact_bodies: Any,
    raw_expectations: Any,
    *,
    label: str,
) -> None:
    if not raw_expectations:
        return
    if not isinstance(source_fact_bodies, Mapping):
        raise ProfileError(f"source_fact_body_carry_case rejected {label}: bodies missing")
    if not isinstance(raw_expectations, list):
        raise ProfileError(f"{label}: expected.body_expectations must be a list")
    for index, raw in enumerate(raw_expectations, start=1):
        item = require_mapping(raw, f"{label}: expected.body_expectations[{index}]")
        source_fact_ref = require_string(
            item.get("source_fact_ref"),
            f"{label}: expected.body_expectations[{index}].source_fact_ref",
        )
        returned_marker = require_string(
            item.get("returned_marker"),
            f"{label}: expected.body_expectations[{index}].returned_marker",
        )
        body = source_fact_bodies.get(source_fact_ref)
        if not isinstance(body, str):
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"missing body for {source_fact_ref}"
            )
        from support.operator.walker_kernel import (
            _WIKI_CARRY_NOTE,
            _WIKI_CARRY_VIEW_HEADER,
            wiki_carry_path_text,
            wiki_carry_summary_text,
        )

        # WIKI-CARRY shape pin: the carried body is a compact wiki VIEW
        # (summary + absolute path + note), NOT the full step-output envelope.
        if not body.startswith(_WIKI_CARRY_VIEW_HEADER):
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} body is not a wiki carry view"
            )
        if _WIKI_CARRY_NOTE not in body:
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry view missing note"
            )
        carry_path = wiki_carry_path_text(body)
        if not carry_path or not Path(carry_path).is_absolute():
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry view missing absolute path"
            )
        if not carry_path.endswith("step-output.json"):
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry path does not point at a step-output file"
            )
        summary = wiki_carry_summary_text(body)
        if summary is None:
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry view missing summary"
            )
        try:
            returned = json.loads(summary)
        except json.JSONDecodeError as exc:
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} wiki carry summary is not JSON"
            ) from exc
        if not isinstance(returned, Mapping) or returned.get("body_marker") != returned_marker:
            raise ProfileError(
                f"source_fact_body_carry_case rejected {label}: "
                f"{source_fact_ref} returned_marker mismatch"
            )
        # The FULL step-output envelope must NOT be inline: only `returned`
        # rides in the summary. ``raw_stream_ref``/``agent_fact_fields`` are
        # envelope-only keys (never inside the agent's ``returned``); their
        # presence means the full body leaked in.
        for envelope_only_key in ("raw_stream_ref", "agent_fact_fields"):
            if envelope_only_key in body:
                raise ProfileError(
                    f"source_fact_body_carry_case rejected {label}: "
                    f"{source_fact_ref} full step-output envelope leaked into carry "
                    f"({envelope_only_key})"
                )


def run_step_output_drain_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "step_output_drain_case")
    if not items:
        return 0
    from support.operator.run import run_building_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "step_output_drain_case item")
        label = require_string(mapping.get("label"), "step_output_drain_case.label")
        case_kind = require_string(mapping.get("case_kind"), f"{label}: case_kind")
        plan, _walker_mode = _step_output_drain_plan(case_kind, missing=False)
        if case_kind == "live_dynamic_full_replay_n3":
            _check_dynamic_full_replay_policy(plan, label=label)
        expected = require_mapping(mapping.get("expected", {}), f"{label}: expected")
        with tempfile.TemporaryDirectory(prefix="bp-step-output-drain-") as tmpdir:
            output_root = Path(tmpdir)
            observed = _StepOutputDrainObserved(
                output_root=output_root,
                reroute_once_from_brick=(
                    "brick-replay-closure-a"
                    if case_kind == "live_dynamic_full_replay_n3"
                    else ""
                ),
                reroute_target_brick=(
                    "brick-replay-work-b"
                    if case_kind == "live_dynamic_full_replay_n3"
                    else ""
                ),
            )
            result, batch_step_output_write_calls = _run_step_output_drain_plan(
                plan,
                output_root=output_root,
                observed=observed,
                repo=repo,
            )
            if batch_step_output_write_calls:
                raise ProfileError(
                    f"step_output_drain_case rejected {label}: accumulated "
                    "evidence batch touched step-output persistence after "
                    "per-event drain"
                )
            if case_kind == "live_dynamic_full_replay_n3":
                _check_dynamic_full_replay_expected(
                    result,
                    observed,
                    expected,
                    label=label,
                )
            else:
                _check_step_output_drain_expected(
                    result,
                    result.lifecycle_write.root,
                    observed,
                    expected,
                    label=label,
                )
        count += 1
    return count


def _run_step_output_drain_plan(
    plan: Mapping[str, Any],
    *,
    output_root: Path,
    observed: "_StepOutputDrainObserved",
    repo: Path,
) -> tuple[Any, int]:
    from support.operator import evidence_assembly
    from support.operator.run import run_building_plan

    calls = 0
    original_write_step_outputs = evidence_assembly.write_step_outputs

    def _observed_batch_write_step_outputs(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return original_write_step_outputs(*args, **kwargs)

    evidence_assembly.write_step_outputs = _observed_batch_write_step_outputs
    try:
        result = run_building_plan(
            plan,
            output_root=output_root,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": observed.callable},
            adapter_cwd=repo,
            adapter_timeout_seconds=10,
        )
    finally:
        evidence_assembly.write_step_outputs = original_write_step_outputs
    return result, calls


def run_step_output_drain_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "step_output_drain_rejects")
    if not items:
        return 0
    from support.operator.run import _source_fact_bodies, run_building_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "step_output_drain_rejects item")
        label = require_string(mapping.get("label"), "step_output_drain_rejects.label")
        case_kind = require_string(mapping.get("case_kind"), f"{label}: case_kind")
        expected_message = require_string(
            mapping.get("expected_message"),
            f"{label}: expected_message",
        )
        try:
            if case_kind == "step_output_source_fact_disk_fallback_rejected":
                _source_fact_bodies(("work/step-outputs/missing-attempt-1/step-output.json",))
            elif case_kind == "live_dynamic_partial_replay_rejected":
                plan, _walker_mode = _step_output_drain_plan(case_kind, missing=True)
                try:
                    _check_dynamic_full_replay_policy(plan, label=label)
                except ProfileError as exc:
                    if expected_message not in str(exc):
                        raise ProfileError(
                            f"step_output_drain_rejects rejected {label}: "
                            f"expected message {expected_message!r}, observed {str(exc)!r}"
                        ) from exc
                    count += 1
                    continue
            elif case_kind == "live_dynamic_missing_step_output_body":
                plan, _walker_mode = _step_output_drain_plan(case_kind, missing=True)
                with tempfile.TemporaryDirectory(prefix="bp-step-output-drain-red-") as tmpdir:
                    observed = _StepOutputDrainObserved(output_root=Path(tmpdir))
                    result = run_building_plan(
                        plan,
                        output_root=Path(tmpdir),
                        overwrite_existing=True,
                        local_callables={
                            "callable:local:agent-invoke0-smoke": observed.callable
                        },
                        adapter_cwd=repo,
                        adapter_timeout_seconds=10,
                    )
                    _check_step_output_drain_dynamic_hold(
                        result,
                        observed,
                        mapping,
                        label=label,
                    )
                count += 1
                continue
            else:
                plan, _walker_mode = _step_output_drain_plan(case_kind, missing=True)
                with tempfile.TemporaryDirectory(prefix="bp-step-output-drain-red-") as tmpdir:
                    observed = _StepOutputDrainObserved(output_root=Path(tmpdir))
                    run_building_plan(
                        plan,
                        output_root=Path(tmpdir),
                        overwrite_existing=True,
                        local_callables={
                            "callable:local:agent-invoke0-smoke": observed.callable
                        },
                        adapter_cwd=repo,
                        adapter_timeout_seconds=10,
                    )
        except (TypeError, ValueError) as exc:
            if expected_message not in str(exc):
                raise ProfileError(
                    f"step_output_drain_rejects rejected {label}: "
                    f"expected message {expected_message!r}, observed {str(exc)!r}"
                ) from exc
            count += 1
            continue
        raise ProfileError(f"step_output_drain_rejects expected rejection but passed: {label}")
    return count


@dataclass
class _StepOutputDrainObserved:
    output_root: Path
    reroute_once_from_brick: str = ""
    reroute_target_brick: str = ""
    events: list[Mapping[str, Any]] | None = None
    body_text_at_call: dict[str, str] | None = None
    _reroute_emitted: bool = False

    def __post_init__(self) -> None:
        if self.events is None:
            self.events = []
        if self.body_text_at_call is None:
            self.body_text_at_call = {}

    def callable(self, request: Any) -> Mapping[str, Any]:
        refs = list(request.source_fact_bodies)
        file_exists: dict[str, bool] = {}
        markers: list[str] = []
        from support.operator.walker_kernel import wiki_carry_summary_text

        for ref, body in request.source_fact_bodies.items():
            relative_ref = _checker_step_output_relative_ref(ref)
            path = self.output_root / request.building_id / relative_ref
            file_exists[ref] = path.is_file()
            if path.is_file():
                self.body_text_at_call[ref] = path.read_text(encoding="utf-8")
            # WIKI-CARRY: the carried body is a compact wiki view; the worker's
            # curated `returned` rides in the summary section, not the full
            # step-output JSON. Recover the summary and parse it back.
            summary = wiki_carry_summary_text(body)
            if summary is None:
                markers.append("")
                continue
            try:
                returned = json.loads(summary)
            except json.JSONDecodeError:
                markers.append("")
                continue
            markers.append(
                str(returned.get("body_marker"))
                if isinstance(returned, Mapping) and returned.get("body_marker") is not None
                else ""
            )
        assert self.events is not None
        self.events.append(
            {
                "brick_instance_ref": request.brick_instance_ref,
                "source_fact_body_refs": refs,
                "carried_markers": markers,
                "source_fact_files_existed_at_call": file_exists,
            }
        )
        returned: dict[str, Any] = {
            "body_marker": request.brick_instance_ref,
            "source_fact_body_refs": refs,
            "carried_markers": markers,
            "not_proven": ["checker live runner proof only"],
        }
        if (
            self.reroute_once_from_brick
            and self.reroute_target_brick
            and request.brick_instance_ref == self.reroute_once_from_brick
            and not self._reroute_emitted
        ):
            self._reroute_emitted = True
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                "related_boundary_refs": [self.reroute_target_brick],
            }
        return returned


def _check_step_output_drain_expected(
    result: Any,
    building_root: Path,
    observed: _StepOutputDrainObserved,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    consumer_brick = require_string(
        expected.get("consumer_brick_instance_ref"),
        f"{label}: expected.consumer_brick_instance_ref",
    )
    expected_refs = require_string_list(
        expected.get("source_fact_body_refs", []),
        f"{label}: expected.source_fact_body_refs",
    )
    expected_markers = require_string_list(
        expected.get("carried_markers", []),
        f"{label}: expected.carried_markers",
    )
    events = observed.events or []
    consumer_events = [
        event for event in events if event.get("brick_instance_ref") == consumer_brick
    ]
    if len(consumer_events) != 1:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: consumer event count "
            f"expected 1, observed {len(consumer_events)}"
        )
    consumer_event = consumer_events[0]
    if consumer_event.get("source_fact_body_refs") != expected_refs:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source_fact_body_refs mismatch"
        )
    if consumer_event.get("carried_markers") != expected_markers:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: carried_markers mismatch"
        )
    file_exists = require_mapping(
        consumer_event.get("source_fact_files_existed_at_call"),
        f"{label}: source_fact_files_existed_at_call",
    )
    for ref in expected_refs:
        if not file_exists.get(ref):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {ref} was not on disk at consumer call"
            )
        final_text = (building_root / _checker_step_output_relative_ref(ref)).read_text(
            encoding="utf-8"
        )
        observed_text = (observed.body_text_at_call or {}).get(ref)
        if observed_text != final_text:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: final step-output rewrote {ref}"
            )
    if expected.get("carry_gate_sufficiency") is not None:
        dynamic_evidence = require_mapping(
            getattr(result, "_dynamic_walker_evidence", {}),
            f"{label}: _dynamic_walker_evidence",
        )
        observations = dynamic_evidence.get("source_fact_body_carry_observations")
        if not isinstance(observations, list):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: dynamic carry observations missing"
            )
        matching = [
            item
            for item in observations
            if isinstance(item, Mapping)
            and item.get("target_step_ref") == expected.get("consumer_step_ref")
        ]
        if len(matching) != 1:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: carry observation count "
                f"expected 1, observed {len(matching)}"
            )
        carry_gate = require_mapping(
            matching[0].get("carry_gate_observation"),
            f"{label}: carry_gate_observation",
        )
        expected_sufficiency = require_string(
            expected.get("carry_gate_sufficiency"),
            f"{label}: expected.carry_gate_sufficiency",
        )
        if carry_gate.get("sufficiency") != expected_sufficiency:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: carry gate sufficiency mismatch"
            )
        if carry_gate.get("missing_required_facts") != expected.get(
            "carry_gate_missing_required_facts",
            [],
        ):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: carry gate missing facts mismatch"
            )


def _check_step_output_drain_dynamic_hold(
    result: Any,
    observed: _StepOutputDrainObserved,
    mapping: Mapping[str, Any],
    *,
    label: str,
) -> None:
    expected_hold_reason = require_string(
        mapping.get("expected_hold_reason"),
        f"{label}: expected_hold_reason",
    )
    dynamic_evidence = require_mapping(
        getattr(result, "_dynamic_walker_evidence", {}),
        f"{label}: _dynamic_walker_evidence",
    )
    if dynamic_evidence.get("held") is not True:
        raise ProfileError(f"step_output_drain_rejects rejected {label}: dynamic run did not HOLD")
    hold = require_mapping(dynamic_evidence.get("hold"), f"{label}: dynamic hold")
    if hold.get("hold_reason") != expected_hold_reason:
        raise ProfileError(
            f"step_output_drain_rejects rejected {label}: hold_reason mismatch"
        )
    observation = require_mapping(
        hold.get("fan_in_wait_all_observation"),
        f"{label}: fan_in_wait_all_observation",
    )
    carry_gate = require_mapping(
        observation.get("carry_gate_observation"),
        f"{label}: carry_gate_observation",
    )
    if carry_gate.get("sufficiency") != "missing_required_facts":
        raise ProfileError(
            f"step_output_drain_rejects rejected {label}: carry gate was not missing_required_facts"
        )
    if not carry_gate.get("missing_required_facts"):
        raise ProfileError(
            f"step_output_drain_rejects rejected {label}: missing_required_facts empty"
        )
    closure_events = [
        event
        for event in (observed.events or [])
        if event.get("brick_instance_ref") == "brick-fan-closure"
    ]
    if closure_events:
        raise ProfileError(
            f"step_output_drain_rejects rejected {label}: closure was called despite HOLD"
        )


def _check_dynamic_full_replay_policy(plan: Mapping[str, Any], *, label: str) -> None:
    from support.operator.plan_graph import (
        _graph_fan_in_sources_by_target_step_ref,
        _graph_fan_out_targets_by_source_step_ref,
        _linear_plan_from_graph_plan,
    )

    linear_plan, graph_context = _linear_plan_from_graph_plan(plan)
    fan_out_targets = _graph_fan_out_targets_by_source_step_ref(graph_context)
    fan_in_sources = _graph_fan_in_sources_by_target_step_ref(graph_context)
    brick_by_step = _brick_ref_by_step(linear_plan)
    step_by_brick = {brick_ref: step_ref for step_ref, brick_ref in brick_by_step.items()}
    for step in linear_plan.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        link_row = _axis_row(step, "Link")
        route_plan = link_row.get("route_replay_plan")
        if not isinstance(route_plan, Mapping):
            continue
        immediate_target = require_string(
            route_plan.get("immediate_target_ref"),
            f"{label}: route_replay_plan.immediate_target_ref",
        )
        target_step = step_by_brick.get(immediate_target)
        if target_step is None:
            continue
        target_fan_out = list(fan_out_targets.get(target_step, ()))
        if len(target_fan_out) < 2:
            continue
        closure_targets = [
            candidate
            for candidate, sources in fan_in_sources.items()
            if set(sources) == set(target_fan_out)
        ]
        if len(closure_targets) != 1:
            raise ProfileError(
                f"dynamic_full_replay_policy rejected {label}: "
                "replay fan-in closure target was not uniquely declared"
            )
        observed = require_string_list(
            route_plan.get("replay_segment_refs", []),
            f"{label}: route_replay_plan.replay_segment_refs",
        )
        if observed:
            raise ProfileError(
                f"dynamic_full_replay_policy rejected {label}: "
                "partial QA reuse is not admitted; graph fan-in full replay must "
                "reroute to the work target and let the declared fan-out/fan-in "
                "segment replay the QA cohort plus closure"
            )


def _check_dynamic_full_replay_expected(
    result: Any,
    observed: _StepOutputDrainObserved,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    events = observed.events or []
    bricks = [str(event.get("brick_instance_ref", "")) for event in events]
    source_brick = require_string(
        expected.get("reroute_source_brick_instance_ref"),
        f"{label}: expected.reroute_source_brick_instance_ref",
    )
    replay_window = require_string_list(
        expected.get("replay_window_brick_instance_refs", []),
        f"{label}: expected.replay_window_brick_instance_refs",
    )
    try:
        source_index = bricks.index(source_brick)
    except ValueError as exc:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: reroute source was not called"
        ) from exc
    closure_index = _check_replay_closure_carry(events, expected, label=label)
    observed_slice = bricks[source_index + 1 : closure_index + 1]
    if observed_slice != replay_window:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: full replay window mismatch "
            f"(got={observed_slice}, expected={replay_window})"
        )
    dynamic_evidence = require_mapping(
        getattr(result, "_dynamic_walker_evidence", {}),
        f"{label}: _dynamic_walker_evidence",
    )
    records = getattr(result, "_dynamic_walker_reroute_records", ())
    adopted = [
        record
        for record in records
        if isinstance(record, Mapping) and not record.get("disposition_required")
    ]
    if len(adopted) != 1:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: expected one adopted reroute, observed {len(adopted)}"
        )
    expected_replay_steps = require_string_list(
        expected.get("replay_segment_step_refs", []),
        f"{label}: expected.replay_segment_step_refs",
    )
    if adopted[0].get("replay_segment_refs") != expected_replay_steps:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: adopted replay_segment_refs mismatch"
        )
    if dynamic_evidence.get("held") is True:
        raise ProfileError(f"step_output_drain_case rejected {label}: dynamic replay held")


def _check_replay_closure_carry(
    events: Sequence[Mapping[str, Any]],
    expected: Mapping[str, Any],
    *,
    label: str,
) -> int:
    consumer_brick = require_string(
        expected.get("consumer_brick_instance_ref"),
        f"{label}: expected.consumer_brick_instance_ref",
    )
    expected_refs = require_string_list(
        expected.get("source_fact_body_refs", []),
        f"{label}: expected.source_fact_body_refs",
    )
    expected_markers = require_string_list(
        expected.get("carried_markers", []),
        f"{label}: expected.carried_markers",
    )
    matching = [
        (index, event)
        for index, event in enumerate(events)
        if event.get("brick_instance_ref") == consumer_brick
        and event.get("source_fact_body_refs") == expected_refs
    ]
    if not matching:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: replay closure did not receive full QA carry"
        )
    index, event = matching[0]
    if event.get("carried_markers") != expected_markers:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: replay closure carried markers mismatch"
        )
    return index


def _step_output_drain_plan(case_kind: str, *, missing: bool) -> tuple[Mapping[str, Any], str]:
    if case_kind == "live_linear_n1":
        return _linear_step_output_drain_plan(missing=missing), "dynamic"
    if case_kind in {"live_dynamic_fan_in_n2", "live_dynamic_fan_in_n3"}:
        return _dynamic_step_output_drain_plan(missing=missing), "dynamic"
    if case_kind == "live_dynamic_full_replay_n3":
        return _dynamic_full_replay_drain_plan(partial=False), "dynamic"
    if case_kind == "live_dynamic_partial_replay_rejected":
        return _dynamic_full_replay_drain_plan(partial=True), "dynamic"
    if case_kind == "live_linear_missing_step_output_body":
        return _linear_step_output_drain_plan(missing=True), "dynamic"
    if case_kind == "live_dynamic_missing_step_output_body":
        return _dynamic_step_output_drain_plan(missing=True), "dynamic"
    raise ProfileError(f"unknown step_output_drain case_kind: {case_kind}")


def _linear_step_output_drain_plan(*, missing: bool) -> Mapping[str, Any]:
    source_ref = (
        "work/step-outputs/missing-producer-attempt-1/step-output.json"
        if missing
        else "work/step-outputs/linear-producer-attempt-1/step-output.json"
    )
    linear_plan = {
        "plan_ref": "building-plan:checker-live-linear-step-output-drain",
        "building_id": "checker-live-linear-step-output-drain",
        "plan_shape": "linear",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "steps": [
            _linear_step(
                "linear-producer",
                "brick-linear-producer",
                "brick-linear-consumer",
            ),
            _linear_step(
                "linear-consumer",
                "brick-linear-consumer",
                "building-boundary:checker-live-linear-step-output-drain-closed",
                source_facts=[source_ref],
                closed=True,
            ),
        ],
    }
    return _graph_test_plan_from_linear(linear_plan)


def _linear_step(
    step_ref: str,
    brick_ref: str,
    target_ref: str,
    *,
    source_facts: Sequence[str] | None = None,
    closed: bool = False,
) -> Mapping[str, Any]:
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": f"link-row:{step_ref}",
        "movement": "forward",
        "target_ref": target_ref,
        "next_brick_instance_ref": target_ref,
    }
    if closed:
        link_row["building_lifecycle"] = {
            "state": "closed",
            "reason": "checker live step-output drain close",
        }
    return {
        "step_ref": step_ref,
        "rows": [
            _brick_row(step_ref, brick_ref, source_facts=source_facts),
            _agent_row(step_ref),
            link_row,
        ],
    }


def _dynamic_step_output_drain_plan(*, missing: bool) -> Mapping[str, Any]:
    closure_source_facts = (
        ["work/step-outputs/missing-qa-attempt-1/step-output.json"] if missing else []
    )
    return {
        "plan_ref": "building-plan:checker-live-dynamic-step-output-drain",
        "building_id": "checker-live-dynamic-step-output-drain",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "execution_order": [
            "fan-work",
            "fan-code-qa",
            "fan-axis-qa",
            "fan-evidence-qa",
            "fan-closure",
        ],
        "brick_steps": [
            _graph_brick_step("fan-work", "brick-fan-work", "edge:work-to-code"),
            _graph_brick_step("fan-code-qa", "brick-fan-code-qa", "edge:code-to-closure"),
            _graph_brick_step("fan-axis-qa", "brick-fan-axis-qa", "edge:axis-to-closure"),
            _graph_brick_step(
                "fan-evidence-qa",
                "brick-fan-evidence-qa",
                "edge:evidence-to-closure",
            ),
            _graph_brick_step(
                "fan-closure",
                "brick-fan-closure",
                "edge:closure-to-boundary",
                source_facts=closure_source_facts,
            ),
        ],
        "link_edges": [
            _graph_link_edge("edge:work-to-code", "fan-work", "fan-code-qa", "brick-fan-code-qa"),
            _graph_link_edge("edge:work-to-axis", "fan-work", "fan-axis-qa", "brick-fan-axis-qa"),
            _graph_link_edge(
                "edge:work-to-evidence",
                "fan-work",
                "fan-evidence-qa",
                "brick-fan-evidence-qa",
            ),
            _graph_link_edge("edge:code-to-closure", "fan-code-qa", "fan-closure", "brick-fan-closure"),
            _graph_link_edge("edge:axis-to-closure", "fan-axis-qa", "fan-closure", "brick-fan-closure"),
            _graph_link_edge(
                "edge:evidence-to-closure",
                "fan-evidence-qa",
                "fan-closure",
                "brick-fan-closure",
            ),
            _graph_link_edge(
                "edge:closure-to-boundary",
                "fan-closure",
                "",
                "building-boundary:checker-live-dynamic-step-output-drain-closed",
            ),
        ],
        "groups": [
            {
                "group_id": "group:checker-step-output-drain-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:work-to-code",
                    "edge:work-to-axis",
                    "edge:work-to-evidence",
                ],
            },
            {
                "group_id": "group:checker-step-output-drain-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:code-to-closure",
                    "edge:axis-to-closure",
                    "edge:evidence-to-closure",
                ],
            },
        ],
    }


def _dynamic_full_replay_drain_plan(*, partial: bool) -> Mapping[str, Any]:
    route_plan = {
        "route_replay_ref": "route-replay:checker-p6-full-replay",
        "author_ref": "coo:checker-p6-full-replay",
        "authoring_basis_refs": ["observation:checker-p6-closure-implementation-gap"],
        "immediate_target_ref": "brick-replay-work-b",
        "source_brick_refs": ["brick-replay-closure-a"],
        "route_reason_refs": ["transition-concern:brick-replay-closure-a"],
        "affected_downstream_refs": [
            "brick-replay-after-b",
        ],
        "replay_segment_refs": (
            ["brick-replay-code-qa-b", "brick-replay-closure-b"]
            if partial
            else []
        ),
        "max_attempts": 1,
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["semantic correctness of closure concern"],
    }
    return {
        "plan_ref": "building-plan:checker-p6-dynamic-full-replay",
        "building_id": "checker-p6-dynamic-full-replay",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "execution_order": [
            "replay-work-a",
            "replay-code-qa-a",
            "replay-axis-qa-a",
            "replay-evidence-qa-a",
            "replay-closure-a",
            "replay-work-b",
            "replay-code-qa-b",
            "replay-axis-qa-b",
            "replay-evidence-qa-b",
            "replay-closure-b",
            "replay-after-b",
        ],
        "brick_steps": [
            _graph_brick_step("replay-work-a", "brick-replay-work-a", "edge:replay-work-a-to-code-a"),
            _graph_brick_step("replay-code-qa-a", "brick-replay-code-qa-a", "edge:replay-code-a-to-axis-a"),
            _graph_brick_step("replay-axis-qa-a", "brick-replay-axis-qa-a", "edge:replay-axis-a-to-evidence-a"),
            _graph_brick_step("replay-evidence-qa-a", "brick-replay-evidence-qa-a", "edge:replay-evidence-a-to-closure-a"),
            _graph_brick_step("replay-closure-a", "brick-replay-closure-a", "edge:replay-closure-a-to-work-b"),
            _graph_brick_step("replay-work-b", "brick-replay-work-b", "edge:replay-work-b-to-code-b"),
            _graph_brick_step("replay-code-qa-b", "brick-replay-code-qa-b", "edge:replay-code-b-to-axis-b"),
            _graph_brick_step("replay-axis-qa-b", "brick-replay-axis-qa-b", "edge:replay-axis-b-to-evidence-b"),
            _graph_brick_step("replay-evidence-qa-b", "brick-replay-evidence-qa-b", "edge:replay-evidence-b-to-closure-b"),
            _graph_brick_step("replay-closure-b", "brick-replay-closure-b", "edge:replay-closure-b-to-after-b"),
            _graph_brick_step("replay-after-b", "brick-replay-after-b", "edge:replay-after-b-to-boundary"),
        ],
        "link_edges": [
            _graph_link_edge("edge:replay-work-a-to-code-a", "replay-work-a", "replay-code-qa-a", "brick-replay-code-qa-a"),
            _graph_link_edge("edge:replay-work-a-to-axis-a", "replay-work-a", "replay-axis-qa-a", "brick-replay-axis-qa-a"),
            _graph_link_edge("edge:replay-work-a-to-evidence-a", "replay-work-a", "replay-evidence-qa-a", "brick-replay-evidence-qa-a"),
            _graph_link_edge("edge:replay-code-a-to-axis-a", "replay-code-qa-a", "replay-axis-qa-a", "brick-replay-axis-qa-a"),
            _graph_link_edge("edge:replay-code-a-to-closure-a", "replay-code-qa-a", "replay-closure-a", "brick-replay-closure-a"),
            _graph_link_edge("edge:replay-axis-a-to-evidence-a", "replay-axis-qa-a", "replay-evidence-qa-a", "brick-replay-evidence-qa-a"),
            _graph_link_edge("edge:replay-axis-a-to-closure-a", "replay-axis-qa-a", "replay-closure-a", "brick-replay-closure-a"),
            _graph_link_edge("edge:replay-evidence-a-to-closure-a", "replay-evidence-qa-a", "replay-closure-a", "brick-replay-closure-a"),
            _graph_link_edge(
                "edge:replay-closure-a-to-work-b",
                "replay-closure-a",
                "replay-work-b",
                "brick-replay-work-b",
                movement="reroute",
                route_replay_plan=route_plan,
                declared_gate_refs=["link-gate:default-transition"],
            ),
            _graph_link_edge("edge:replay-work-b-to-code-b", "replay-work-b", "replay-code-qa-b", "brick-replay-code-qa-b"),
            _graph_link_edge("edge:replay-work-b-to-axis-b", "replay-work-b", "replay-axis-qa-b", "brick-replay-axis-qa-b"),
            _graph_link_edge("edge:replay-work-b-to-evidence-b", "replay-work-b", "replay-evidence-qa-b", "brick-replay-evidence-qa-b"),
            _graph_link_edge("edge:replay-code-b-to-axis-b", "replay-code-qa-b", "replay-axis-qa-b", "brick-replay-axis-qa-b"),
            _graph_link_edge("edge:replay-code-b-to-closure-b", "replay-code-qa-b", "replay-closure-b", "brick-replay-closure-b"),
            _graph_link_edge("edge:replay-axis-b-to-evidence-b", "replay-axis-qa-b", "replay-evidence-qa-b", "brick-replay-evidence-qa-b"),
            _graph_link_edge("edge:replay-axis-b-to-closure-b", "replay-axis-qa-b", "replay-closure-b", "brick-replay-closure-b"),
            _graph_link_edge("edge:replay-evidence-b-to-closure-b", "replay-evidence-qa-b", "replay-closure-b", "brick-replay-closure-b"),
            _graph_link_edge("edge:replay-closure-b-to-after-b", "replay-closure-b", "replay-after-b", "brick-replay-after-b"),
            _graph_link_edge(
                "edge:replay-after-b-to-boundary",
                "replay-after-b",
                "",
                "building-boundary:checker-p6-dynamic-full-replay-closed",
            ),
        ],
        "groups": [
            {
                "group_id": "group:p6-replay-fan-out-a",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:replay-work-a-to-code-a",
                    "edge:replay-work-a-to-axis-a",
                    "edge:replay-work-a-to-evidence-a",
                ],
            },
            {
                "group_id": "group:p6-replay-fan-in-a",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:replay-code-a-to-closure-a",
                    "edge:replay-axis-a-to-closure-a",
                    "edge:replay-evidence-a-to-closure-a",
                ],
            },
            {
                "group_id": "group:p6-replay-fan-out-b",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:replay-work-b-to-code-b",
                    "edge:replay-work-b-to-axis-b",
                    "edge:replay-work-b-to-evidence-b",
                ],
            },
            {
                "group_id": "group:p6-replay-fan-in-b",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:replay-code-b-to-closure-b",
                    "edge:replay-axis-b-to-closure-b",
                    "edge:replay-evidence-b-to-closure-b",
                ],
            },
        ],
        "node_reroute_budgets": {"brick-replay-work-b": 1},
    }


def _graph_brick_step(
    step_ref: str,
    brick_ref: str,
    completion_edge_ref: str,
    *,
    source_facts: Sequence[str] | None = None,
) -> Mapping[str, Any]:
    return {
        "step_ref": step_ref,
        "completion_edge_ref": completion_edge_ref,
        "rows": [
            _brick_row(step_ref, brick_ref, source_facts=source_facts),
            _agent_row(step_ref),
        ],
    }


def _graph_link_edge(
    edge_ref: str,
    source_step_ref: str,
    target_step_ref: str,
    target_ref: str,
    *,
    movement: str = "forward",
    route_replay_plan: Mapping[str, Any] | None = None,
    declared_gate_refs: Sequence[str] | None = None,
) -> Mapping[str, Any]:
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": f"link-row:{edge_ref}",
        "movement": movement,
        "target_ref": target_ref,
    }
    if declared_gate_refs is not None:
        link_row["declared_gate_refs"] = list(declared_gate_refs)
    if route_replay_plan is not None:
        link_row["route_replay_plan"] = dict(route_replay_plan)
    edge: dict[str, Any] = {
        "edge_ref": edge_ref,
        "source_step_ref": source_step_ref,
        "rows": [link_row],
    }
    if target_step_ref:
        edge["target_step_ref"] = target_step_ref
    else:
        link_row["building_lifecycle"] = {
            "state": "closed",
            "reason": "checker live step-output drain close",
        }
    return edge


def _axis_row(step: Mapping[str, Any], axis: str) -> Mapping[str, Any]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == axis:
            return row
    return {}


def _brick_ref_by_step(plan: Mapping[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    for step in plan.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        step_ref = str(step.get("step_ref", "")).strip()
        brick_row = _axis_row(step, "Brick")
        brick_ref = str(brick_row.get("brick_instance_ref", "")).strip()
        if step_ref and brick_ref:
            refs[step_ref] = brick_ref
    return refs


def _brick_row(
    step_ref: str,
    brick_ref: str,
    *,
    source_facts: Sequence[str] | None,
) -> Mapping[str, Any]:
    return {
        "axis": "Brick",
        "row_ref": f"brick-row:{step_ref}",
        "brick_work_ref": f"work:{step_ref}",
        "brick_instance_ref": brick_ref,
        "work_statement": f"Run checker live step-output drain step {step_ref}.",
        "comparison_rule": "Observe support evidence only; do not choose Movement or judge quality.",
        "required_return_shape": "body_marker, source_fact_body_refs, carried_markers, not_proven",
        "source_facts": list(source_facts or []),
    }


def _agent_row(step_ref: str) -> Mapping[str, Any]:
    return {
        "axis": "Agent",
        "row_ref": f"agent-row:{step_ref}",
        "agent_object_ref": "agent-object:coo",
    }


def _step_output_drain_proof_limits() -> list[str]:
    return [
        "support evidence only",
        "not source truth",
        "not success judgment",
        "not quality judgment",
        "not Movement authority",
    ]


def _checker_step_output_relative_ref(ref: str) -> str:
    marker = "work/step-outputs/"
    normalized = str(ref).replace("\\", "/")
    if marker not in normalized:
        return normalized
    return normalized[normalized.index(marker) :]


def run_auto_repair_replay_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "auto_repair_replay_case")
    if not items:
        return 0
    from support.operator.auto_repair_replay import prepare_declared_auto_repair_replay_case
    count = 0
    for item in items:
        mapping = require_mapping(item, "auto_repair_replay_case item")
        case, relative = _profile_case_document(repo, mapping, "auto_repair_replay_case")
        prepared = prepare_declared_auto_repair_replay_case(case, repo)
        expected = require_mapping(mapping.get("expected", {}), "auto_repair_replay_case.expected")
        for key in (
            "movement",
            "target_ref",
            "repair_replay_building_id",
            "materialized",
            "materialization_state",
            "materialization_reason",
            "required_disposition_owner",
        ):
            if key in expected and prepared.get(key) != expected.get(key):
                raise ProfileError(
                    f"auto_repair_replay_case rejected {relative}: "
                    f"{key} expected {expected.get(key)!r}, observed {prepared.get(key)!r}"
                )
        for absent_key in require_string_list(
            expected.get("absent_keys", []),
            "auto_repair_replay_case.expected.absent_keys",
        ):
            if prepared.get(absent_key) is not None:
                raise ProfileError(
                    f"auto_repair_replay_case rejected {relative}: "
                    f"{absent_key} must be absent"
                )
        count += 1
    return count


def run_child_building_candidate_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "child_building_candidate_case")
    if not items:
        return 0
    from support.operator.child_building_generation import prepare_child_building_candidate_case
    count = 0
    for item in items:
        mapping = require_mapping(item, "child_building_candidate_case item")
        case, relative = _profile_case_document(repo, mapping, "child_building_candidate_case")
        prepared = prepare_child_building_candidate_case(case)
        validate_building_plan_boundary(
            prepared["candidate_plan"],
            f"{relative}: candidate_plan",
            _admitted_agent_object_refs(repo),
            repo,
        )
        expected = require_mapping(mapping.get("expected", {}), "child_building_candidate_case.expected")
        for key in ("selected_delta_ref", "candidate_building_id"):
            if key in expected and prepared.get(key) != expected.get(key):
                raise ProfileError(
                    f"child_building_candidate_case rejected {relative}: "
                    f"{key} expected {expected.get(key)!r}, observed {prepared.get(key)!r}"
                )
        count += 1
    return count


def run_fail_fixture_rejects(repo: Path, profile: Mapping[str, Any]) -> int:
    count = 0
    validators = {
        "building_plan_boundary": lambda document, label: validate_building_plan_boundary(
            document,
            label,
            _admitted_agent_object_refs(repo),
            repo,
        ),
        "route_policy_boundary": validate_route_policy_boundary,
    }
    for item in rule_items(profile, "fail_fixture_rejects"):
        mapping = require_mapping(item, "fail_fixture_rejects item")
        kind = require_string(mapping.get("kind"), "fail_fixture_rejects.kind")
        document, relative = _profile_case_document(repo, mapping, "fail_fixture_rejects")
        validator = validators.get(kind)
        if validator is None:
            raise ProfileError(f"fail_fixture_rejects has unknown kind: {kind}")
        try:
            validator(document, relative)
        except ProfileError:
            count += 1
            continue
        raise ProfileError(f"fail_fixture_rejects expected rejection but passed: {relative}")
    return count


# ---------------------------------------------------------------------------
# CLEAN-YARD v3 (Smith 0611): EPHEMERAL GENERATION cases. The product repo
# ships ZERO standing dogfood buildings / status artifacts; a check that needs
# building evidence GENERATES it with the REAL engine at check time, asserts
# the SAME properties the retired standing-evidence pins asserted, and removes
# it in ``finally``. Property tables below are migrated 1:1 from the retired
# pins (provenance noted per table).
# ---------------------------------------------------------------------------

# Building-map shape -- union of the retired building-map json_required_paths
# pins (coo_operating_chain 0527 / building_automation 0526 /
# structure_template_integrity prune-0527 / read_side design-toolkit-0526 +
# project-orchestration-ledger-0528).
_VESSEL_CASE_BUILDING_MAP_REQUIRED = (
    "kind",
    "task_source_ref",
    "brick_instances[].brick_instance_id",
    "agent_bindings[].step_output_ref",
    "agent_bindings[].agent_binding_id",
    "link_edges[].link_edge_id",
)
# Step-output envelope -- the retired closure/work step-output pins
# (read_side project-orchestration-ledger-0528, link_routing 0526/0527,
# agent_axis preset-three-axis-contract-repair-0528).
_VESSEL_CASE_STEP_OUTPUT_REQUIRED = (
    "attempt_index",
    "brick_instance_ref",
    "step_output_ref",
    "task_source_ref",
    "agent_fact_fields[]",
    "evidence_refs.raw_stream_ref",
    "evidence_refs.claim_trace_ref",
)
# Orchestration-ledger packet shape -- union of the two retired
# json_required_paths blocks on project/brick-protocol/status/
# project-orchestration-ledger.json (read_side_projection_boundary), plus the
# retired text needles that named row fields (current_brick_ref /
# current_agent_ref / current_link_target_ref / latest_movement /
# frontier_kind / board_state / evidence_refs / not process liveness proof).
_VESSEL_CASE_LEDGER_PACKET_REQUIRED = (
    "kind",
    "schema_version",
    "packet_ref",
    "generated_at",
    "project.project_ref",
    "participants[].participant_ref",
    "proof_limits[]",
    "not_proven[]",
)
_VESSEL_CASE_LEDGER_ROW_REQUIRED = (
    "building_ref",
    "building_root",
    "current_brick_ref",
    "current_agent_ref",
    "current_link_target_ref",
    "latest_movement",
    "frontier_kind",
    "board_state",
    "next_action_observation",
    "last_evidence_at",
    "evidence_refs.building_map",
    "proof_limits[]",
)
_LIVE_INBOX_FIXTURE_PACKET_GLOB = "checker-projection-fixture-vessel-*.json"


def _vessel_case_require_json(value: Any, required: Sequence[str], label: str) -> None:
    for dotted in required:
        if not json_path_exists(value, dotted):
            raise ProfileError(f"{label}: required path {dotted!r} missing")


def _live_inbox_fixture_packet_count(repo: Path) -> int:
    inbox = repo / "project" / "brick-protocol" / "status" / "inbox"
    if not inbox.is_dir():
        return 0
    return sum(1 for path in inbox.glob(_LIVE_INBOX_FIXTURE_PACKET_GLOB) if path.is_file())


def _assert_live_inbox_fixture_count_unchanged(
    label: str, before: int, after: int
) -> None:
    if after == before:
        return
    raise ProfileError(
        f"intake_evidence_projection_case rejected {label}: live repo inbox "
        f"{_LIVE_INBOX_FIXTURE_PACKET_GLOB!r} count changed from {before} to {after}; "
        "checker fixtures must not write project/brick-protocol/status/inbox"
    )


def _assert_live_inbox_fixture_count_guard_red(label: str, before: int) -> None:
    try:
        _assert_live_inbox_fixture_count_unchanged(label, before, before + 1)
    except ProfileError:
        return
    raise ProfileError(
        f"intake_evidence_projection_case rejected {label}: live inbox count guard "
        "did not RED on a synthetic fixture packet increase"
    )


def run_intake_evidence_projection_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """CLEAN-YARD v3: generate a vessel + intake building, assert all read-side shapes.

    One item drives, at check time:

      1. S2 vessel creation (``create_project``) -- a synthetic vessel under
         ``project/<vessel_id>``; a PRE-EXISTING dir REDs (a possibly-real
         vessel is never reused or deleted); removed in ``finally``.
      2. PROGRESS over the EMPTY vessel (0 buildings) -- the generator must
         render for an empty vessel (the 0-building product case) and the
         render must carry the declared direction echo.
      3. REAL intake (``run_building_intake``) of the declared chain preset on
         a stubbed write-capable adapter into the vessel; the run must reach a
         complete frontier.
      4. Building-map / task.md / declaration-chain / preset-expansion /
         step-output assertions -- the retired standing-evidence pin
         properties, asserted on the FRESH evidence (tables above).
      5. Orchestration-ledger packet + rendered view + PROGRESS over the
         1-building vessel -- the retired status-artifact pin properties,
         asserted on a FRESH projection (no standing status export needed).
    """

    items = rule_items(profile, "intake_evidence_projection_case")
    if not items:
        return 0
    import shutil

    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from support.operator.building_operation import observe_building_frontier
    from support.operator.driver import run_building_intake
    from support.operator.ledger_projection import (
        project_orchestration_ledger_packet,
        render_project_orchestration_ledger_view,
    )
    from support.operator.progress_projection import render_project_progress
    from support.operator.project_creation import create_project

    count = 0
    for item in items:
        mapping = require_mapping(item, "intake_evidence_projection_case item")
        label = require_string(mapping.get("label"), "intake_evidence_projection_case.label")
        vessel_id = require_string(mapping.get("vessel_id"), f"{label}: vessel_id")
        chain_preset_ref = require_string(
            mapping.get("chain_preset_ref"), f"{label}: chain_preset_ref"
        )
        expected_expansion = require_mapping(
            mapping.get("expected_preset_expansion", {}),
            f"{label}: expected_preset_expansion",
        )
        vessel_dir = repo / "project" / vessel_id
        if vessel_dir.exists():
            raise ProfileError(
                f"intake_evidence_projection_case rejected {label}: fixture path "
                f"{vessel_dir} already exists -- refusing to reuse or remove a "
                "possibly-real vessel; pick an unused fixture vessel_id"
            )
        project_ref = f"project:{vessel_id}"
        building_id = f"{_case_slug(label)}-building"
        task_statement = (
            f"{label}: generate one engine building inside a temp vessel so the "
            "read-side projection shapes can be asserted on fresh evidence."
        )
        command_runner = _preset_completion_command_runner(LocalCliCompleted)
        live_inbox_count_before = _live_inbox_fixture_packet_count(repo)
        _assert_live_inbox_fixture_count_guard_red(label, live_inbox_count_before)
        try:
            create_project(
                repo,
                project_id=vessel_id,
                label=f"checker fixture vessel for {label}",
                direction="hold one generated projection-shape building, then be removed",
                why_exists="checker fixture: generates read-side projection evidence at check time",
                why_now="created and removed inside one intake_evidence_projection_case run",
                done_means="the case's assertions ran; the vessel is removed in finally",
                out_of_scope="any real work; this vessel never outlives the checker case",
                managers=["checker-fixture-human"],
                declared_by="coo:intake-evidence-projection-case",
            )

            # (2) PROGRESS over the EMPTY vessel: the 0-building render is a
            # REAL product case (a brand-new vessel) and must not choke.
            empty_progress = render_project_progress(project_ref, repo_root=repo)
            if "0" not in empty_progress:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: empty-vessel "
                    "PROGRESS render does not show a zero building count"
                )

            # (3) REAL intake on the stubbed write-capable adapter.
            intent: dict[str, Any] = {
                "plan_ref": f"building-plan:{building_id}",
                "building_id": building_id,
                "declared_by": "coo",
                "task_statement": task_statement,
                "chain_preset_ref": chain_preset_ref,
                "selected_adapter_ref": "adapter:codex-local",
                "selected_model_ref": "model:default",
                "project_ref": project_ref,
                "write_scope": {
                    "allowed_paths": ["support/operator/**"],
                    "forbidden_paths": [".git/**"],
                },
                "route_decision_basis": {
                    "override_refs": [f"coo:{_case_slug(label)}"],
                    "human_review_refs": [f"human-review:{_case_slug(label)}"],
                },
                "proof_limits": [
                    "intake evidence-projection checker support evidence only",
                    "not source truth",
                    "not success judgment",
                    "not quality judgment",
                    "not Movement authority",
                ],
                "not_proven": [
                    f"semantic correctness of {label}",
                    "real provider behavior",
                ],
                "report_event_policy": {
                    "enabled": False,
                },
            }
            run_building_intake(
                intent,
                repo_root=repo,
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
            )
            building_root = vessel_dir / "buildings" / building_id
            frontier = observe_building_frontier(building_root, repo_root=repo)
            if frontier.get("frontier_kind") != "complete":
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: generated "
                    f"building frontier is {frontier.get('frontier_kind')!r}, "
                    "expected complete"
                )

            # (4a) declaration chain landed (task placement + launch chain).
            for record in (
                ("work", "task.md"),
                ("work", "building-intake.json"),
                ("work", "preset-expansion.json"),
                ("work", "declared-building-plan.json"),
                ("work", "link-launch-policy.json"),
                ("work", "building-map.json"),
                ("evidence", "evidence-manifest.json"),
            ):
                if not building_root.joinpath(*record).is_file():
                    raise ProfileError(
                        f"intake_evidence_projection_case rejected {label}: generated "
                        f"building is missing {'/'.join(record)}"
                    )
            task_text = (building_root / "work" / "task.md").read_text(encoding="utf-8")
            if task_statement not in task_text:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: work/task.md "
                    "does not carry the declared task statement verbatim"
                )

            # (4b) building-map shape (retired building-map pin union).
            building_map = json.loads(
                (building_root / "work" / "building-map.json").read_text(encoding="utf-8")
            )
            _vessel_case_require_json(
                building_map,
                _VESSEL_CASE_BUILDING_MAP_REQUIRED,
                f"{label}: building-map.json",
            )

            # (4c) preset-expansion declared values (retired p9 dogfood pins;
            # exact-equality per declared expected key).
            expansion = json.loads(
                (building_root / "work" / "preset-expansion.json").read_text(encoding="utf-8")
            )
            for key, expected_value in expected_expansion.items():
                if expansion.get(key) != expected_value:
                    raise ProfileError(
                        f"intake_evidence_projection_case rejected {label}: "
                        f"preset-expansion.json {key} expected {expected_value!r}, "
                        f"observed {expansion.get(key)!r}"
                    )

            # (4d) step-output envelopes (retired step-output pin union) + at
            # least one returned with observed_evidence[] AND not_proven[].
            step_outputs = sorted(
                (building_root / "work" / "step-outputs").glob("*/step-output.json")
            )
            if not step_outputs:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: generated "
                    "building wrote no step outputs"
                )
            saw_observed_and_not_proven = False
            for output_path in step_outputs:
                output_value = json.loads(output_path.read_text(encoding="utf-8"))
                _vessel_case_require_json(
                    output_value,
                    _VESSEL_CASE_STEP_OUTPUT_REQUIRED,
                    f"{label}: {output_path.name}",
                )
                if json_path_exists(output_value, "returned.observed_evidence[]") and (
                    json_path_exists(output_value, "returned.not_proven[]")
                ):
                    saw_observed_and_not_proven = True
            if not saw_observed_and_not_proven:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: no step output "
                    "persisted returned.observed_evidence[] + returned.not_proven[]"
                )

            # (5) ledger packet + rendered view + PROGRESS over the 1-building
            # vessel (retired status-artifact pins, generated fresh).
            packet = project_orchestration_ledger_packet(repo_root=repo)
            _vessel_case_require_json(
                packet, _VESSEL_CASE_LEDGER_PACKET_REQUIRED, f"{label}: ledger packet"
            )
            rows = [
                row
                for row in packet.get("rows", [])
                if isinstance(row, Mapping)
                and str(row.get("building_ref", "")).endswith(building_id)
            ]
            if len(rows) != 1:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: ledger packet "
                    f"does not project exactly one row for {building_id} "
                    f"(observed {len(rows)})"
                )
            _vessel_case_require_json(
                rows[0], _VESSEL_CASE_LEDGER_ROW_REQUIRED, f"{label}: ledger row"
            )
            if "link_disposition" not in rows[0]:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: ledger row is "
                    "missing the link_disposition key (null allowed, key required)"
                )
            packet_text = json.dumps(packet)
            for needle in ("project_orchestration_ledger", "not process liveness proof"):
                if needle not in packet_text:
                    raise ProfileError(
                        f"intake_evidence_projection_case rejected {label}: ledger "
                        f"packet does not carry {needle!r}"
                    )
            rendered_view = render_project_orchestration_ledger_view(repo_root=repo)
            if building_id not in rendered_view:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: rendered ledger "
                    "view does not show the generated building"
                )
            one_progress = render_project_progress(project_ref, repo_root=repo)
            if building_id not in one_progress:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: 1-building "
                    "PROGRESS render does not show the generated building"
                )
        finally:
            live_inbox_count_after = _live_inbox_fixture_packet_count(repo)
            shutil.rmtree(vessel_dir, ignore_errors=True)
            _assert_live_inbox_fixture_count_unchanged(
                label, live_inbox_count_before, live_inbox_count_after
            )

        # PART B -- effective-write step-output shape (retired read_side
        # project-orchestration-ledger-0528 WORK-attempt pins: returned.adapter_ref,
        # returned.changed_files[], returned.worktree_observation.observed_changed_
        # files[], returned.worktree_observation.write_scope.allowed_paths[]) plus
        # the retired agent_axis 0528 development-return pins
        # (returned.worker_assignments[], returned.risks[]). Generated by ONE
        # 1-step effective-write run whose stub CLI WRITES one scoped file inside
        # a TEMP adapter cwd (never the repo) and returns the declared fields.
        from support.operator.run import run_building_plan

        def _writing_runner(args: Sequence[str], cwd: Path, timeout_seconds: int) -> Any:
            checked_args = tuple(str(arg) for arg in args)
            if "--version" in checked_args:
                return LocalCliCompleted(
                    args=checked_args,
                    return_code=0,
                    stdout="codex write-observation-fixture 0.0\n",
                    stderr="",
                )
            scoped = Path(cwd) / "scoped"
            scoped.mkdir(parents=True, exist_ok=True)
            (scoped / "observed-note.md").write_text(
                "write-observation fixture note\n", encoding="utf-8"
            )
            returned = {
                "observed_evidence": ["wrote one scoped fixture note"],
                "made_changes": ["scoped/observed-note.md"],
                "worker_assignments": ["fixture-worker: scoped note"],
                "risks": ["none observed"],
                "blocked_or_missing_evidence": [
                    "fixture observation: no blocking evidence beyond the declared scope"
                ],
                "not_proven": ["semantic correctness of the fixture note"],
            }
            assistant_text = json.dumps(returned, sort_keys=True)
            # TrackA-A1 FIXTURE FAITHFULNESS: real `codex exec --json` writes the
            # assistant text to the --output-last-message FILE; stdout carries JSONL
            # events only (the adapter must NEVER treat that JSONL as text). Model
            # that here so the empty-file path is never exercised with raw stdout.
            output_path = _output_last_message_path(checked_args)
            if output_path is not None:
                Path(output_path).write_text(assistant_text, encoding="utf-8")
                stdout = (
                    json.dumps(
                        {
                            "type": "turn.completed",
                            "usage": {
                                "input_tokens": 12,
                                "cached_input_tokens": 3,
                                "output_tokens": 4,
                                "reasoning_output_tokens": 5,
                            },
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
            else:
                stdout = assistant_text
            return LocalCliCompleted(
                args=checked_args,
                return_code=0,
                stdout=stdout,
                stderr="",
            )

        write_step_ref = f"{_case_slug(label)}-write-observation"
        write_plan: dict[str, Any] = {
            "plan_ref": f"building-plan:{write_step_ref}",
            "owner_axis": "Brick",
            "building_id": write_step_ref,
            "plan_shape": "linear",
            "selected_adapter_ref": "adapter:codex-local",
            "selected_model_ref": "model:default",
            "task_source_ref": "task-source:inline-statement",
            "task_statement": f"{label}: one effective-write step for write-observation shape assertions.",
            "proof_limits": ["support evidence only", "not Movement authority"],
            "not_proven": ["semantic correctness of the fixture write"],
            "steps": [
                {
                    "step_ref": write_step_ref,
                    "rows": [
                        {
                            "axis": "Brick",
                            "row_ref": f"brick-row:{write_step_ref}",
                            "brick_work_ref": f"work:{write_step_ref}",
                            "brick_instance_ref": f"brick-{write_step_ref}",
                            "work_statement": "Write one scoped fixture note and return the declared evidence fields.",
                            "comparison_rule": "Observe returned fields and the write observation only.",
                            "required_return_shape": "observed_evidence, made_changes, worker_assignments, risks, blocked_or_missing_evidence, not_proven",
                            "requires_brick_write_scope": True,
                            "write_scope": {
                                "allowed_paths": ["scoped/**"],
                                "forbidden_paths": [".git/**"],
                            },
                        },
                        {
                            "axis": "Agent",
                            "row_ref": f"agent-row:{write_step_ref}",
                            "agent_object_ref": "agent-object:dev",
                        },
                        {
                            "axis": "Link",
                            "row_ref": f"link-row:{write_step_ref}",
                            "movement": "forward",
                            "target_ref": f"building-boundary:{write_step_ref}-closed",
                            "declared_gate_refs": ["link-gate:default-transition"],
                            "building_lifecycle": {
                                "state": "closed",
                                "reason": "write-observation fixture run closes after one step.",
                            },
                        },
                    ],
                }
            ],
        }
        write_plan = dict(_graph_test_plan_from_linear(write_plan))
        with tempfile.TemporaryDirectory(prefix="bp-write-observation-case-") as wtmp:
            workspace = Path(wtmp) / "workspace"
            workspace.mkdir(parents=True)
            write_result = run_building_plan(
                write_plan,
                output_root=Path(wtmp) / "buildings",
                overwrite_existing=True,
                command_runner=_writing_runner,
                adapter_cwd=workspace,
                adapter_timeout_seconds=10,
            )
            write_root = Path(write_result.lifecycle_write.root)
            write_outputs = sorted(
                (write_root / "work" / "step-outputs").glob("*/step-output.json")
            )
            if not write_outputs:
                raise ProfileError(
                    f"intake_evidence_projection_case rejected {label}: write-observation "
                    "run wrote no step outputs"
                )
            write_output = json.loads(write_outputs[0].read_text(encoding="utf-8"))
            for dotted in (
                "returned.adapter_ref",
                "returned.changed_files[]",
                "returned.worktree_observation.observed_changed_files[]",
                "returned.worktree_observation.write_scope.allowed_paths[]",
                "returned.worker_assignments[]",
                "returned.risks[]",
                "returned.blocked_or_missing_evidence[]",
                "returned.made_changes[]",
                "returned.not_proven[]",
                "evidence_refs.raw_stream_ref",
                "evidence_refs.claim_trace_ref",
            ):
                if not json_path_exists(write_output, dotted):
                    raise ProfileError(
                        f"intake_evidence_projection_case rejected {label}: "
                        f"write-observation step output is missing {dotted!r}"
                    )
        count += 1
    return count


# Link-evidence property tables, migrated 1:1 from the retired standing-root
# pins of link_routing_behavioral.yaml (link-decision-disposition-0527 /
# link-owned-automation-0527 / step-output-and-route-request-0526 /
# building-automation-complete-scope-c-0527 evidence). The
# raw-link "transition_lifecycle_state" needle of the 0527 era is asserted
# here via the fixture plan's declared resumed lifecycle row; the
# disposition-row twin (caller/COO-authored resume) is asserted by the tier-a
# generation harness (check_tier_a_three_axis_conformance assert_link).
_LINK_CASE_CONCERN_JSON_REQUIRED = (
    "binding",
    "transition_boundary",
    "transition_concern_ref",
    "transition_concern_returned.concern_ref",
    "transition_concern_returned.concern_kind",
    "transition_concern_returned.binding",
    "transition_concern_returned.reason_refs[]",
    "transition_concern_returned.related_boundary_refs[]",
)
_LINK_CASE_CONCERN_STEP_OUTPUT_REQUIRED = (
    "attempt_index",
    "brick_instance_ref",
    "step_output_ref",
    "returned.observed_evidence[]",
    "returned.transition_concern_evidence.binding",
    "returned.transition_concern_evidence.concern_ref",
    "returned.transition_concern_evidence.concern_kind",
    "returned.transition_concern_evidence.reason_refs[]",
    "returned.transition_concern_evidence.related_boundary_refs[]",
    "evidence_refs.raw_stream_ref",
    "evidence_refs.claim_trace_ref",
)
_LINK_CASE_DEV_REPLAY_STEP_OUTPUT_REQUIRED = (
    "attempt_index",
    "brick_instance_ref",
    "step_output_ref",
    "agent_fact_fields[]",
    "returned.observed_evidence[]",
    "returned.made_changes[]",
    "returned.not_proven[]",
    "evidence_refs.raw_stream_ref",
    "evidence_refs.claim_trace_ref",
)
_LINK_CASE_QA_REPLAY_STEP_OUTPUT_REQUIRED = (
    "attempt_index",
    "brick_instance_ref",
    "step_output_ref",
    "agent_fact_fields[]",
    "returned.observed_evidence[]",
    "returned.not_proven[]",
    "evidence_refs.raw_stream_ref",
    "evidence_refs.claim_trace_ref",
)
_LINK_CASE_ROUTE_REQUEST_JSON_REQUIRED = (
    "route_request_ref",
    "route_request_returned",
    "route_request_returned.requested_route_scope",
    "route_request_returned.reason_refs",
    "route_phase_boundary",
)
_LINK_CASE_RAW_LINK_NEEDLES = (
    "declared_gate_refs",
    "route_decision_adopted_transition_concern_refs",
    "route_decision_not_adopted_transition_concern_refs",
    "route_decision_override_refs",
    "transition_lifecycle_state",
    "transition-concern:link-owned-automation-0-implementation-gap",
)
_LINK_CASE_MOVEMENT_TRACE_NEEDLES = (
    "declared_gate_refs",
    "route_decision_adopted_transition_concern_refs",
    "movement_source",
)
_LINK_CASE_RETURNED_CLAIMS_NEEDLES = (
    "transition_concern_evidence",
    "binding",
    "implementation_gap",
)
_LINK_CASE_SUFFICIENCY_NEEDLES = (
    # Same property as the retired 0527 needle "declared Link gate evaluation":
    # the sufficiency verdict's provenance is the DECLARED gate set, never a
    # support invention. The modern combined-gate emitter words it as below and
    # names the declared gate ref in the reason; the law-source wording stays
    # pinned on link/gate.py itself.
    "caller_or_declared",
    "combined movement gate derived from ordered per-gate GateFact results",
    "link-gate:default-transition",
)
_LINK_CASE_SUFFICIENCY_JSON_REQUIRED = (
    # retired agent_axis 0528 sufficiency_trace pins
    "facts[].fact.sufficiency",
    "facts[].fact.missing_required_facts",
)
_LINK_CASE_BUILDING_MAP_REQUIRED = (
    "kind",
    "brick_instances[].brick_instance_id",
    "agent_bindings[].step_output_ref",
    "link_edges[].link_edge_id",
)


def run_link_route_evidence_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """CLEAN-YARD v3: generate the Link routing/replay evidence at check time.

    Each item runs the declared fixture plan (a strict-valid graph plan that
    carries the full Link grammar: non-binding concern step, declared
    route_decision_basis, declared route_replay_plan + max_attempts, declared
    resumed transition_lifecycle, attempt-2 replay steps) through the REAL
    ``run_building_plan`` on adapter:local with a deterministic brain that
    returns the structured concern at the declared concern step and the
    route_request at the QA replay step, into a TEMP output root (removed by
    the context manager). It then
    asserts the property tables above -- migrated 1:1 from the retired
    standing-evidence pins.
    """

    items = rule_items(profile, "link_route_evidence_case")
    if not items:
        return 0
    from support.operator.building_operation import observe_building_frontier
    from support.operator.run import run_building_plan

    count = 0
    for item in items:
        mapping = require_mapping(item, "link_route_evidence_case item")
        label = require_string(mapping.get("label"), "link_route_evidence_case.label")
        plan_rel = require_string(mapping.get("plan_path"), f"{label}: plan_path")
        concern_brick = require_string(mapping.get("concern_brick"), f"{label}: concern_brick")
        dev_replay_brick = require_string(
            mapping.get("dev_replay_brick"), f"{label}: dev_replay_brick"
        )
        qa_replay_brick = require_string(
            mapping.get("qa_replay_brick"), f"{label}: qa_replay_brick"
        )
        concern_ref = require_string(mapping.get("concern_ref"), f"{label}: concern_ref")
        plan = load_yaml_subset_file(repo, plan_rel)

        def _brain(request: Any) -> Mapping[str, Any]:
            source = str(getattr(request, "brick_instance_ref", "") or "")
            if source == concern_brick:
                return {
                    "observed_evidence": ["observed an implementation gap in the dev boundary"],
                    "transition_concern_evidence": {
                        "concern_ref": concern_ref,
                        "concern_kind": "implementation_gap",
                        "binding": False,
                        "reason_refs": ["observation:link-owned-automation-0-qa"],
                        "related_boundary_refs": [
                            "building-boundary:link-owned-automation-0-concern-recorded"
                        ],
                    },
                    "not_proven": ["semantic correctness of the concern"],
                }
            if source == qa_replay_brick:
                return {
                    "observed_evidence": [f"replayed declared QA boundary for {source}"],
                    "made_changes": ["declared fixture replay observation"],
                    "route_request": {
                        "request_ref": f"route-request:{_case_slug(label)}",
                        "requested_route_scope": "implementation_only",
                        "reason_refs": ["observation:link-owned-automation-0-qa"],
                        "binding": False,
                    },
                    "not_proven": ["semantic correctness of the replay"],
                }
            returned: dict[str, Any] = {
                "observed_evidence": [f"completed declared work for {source}"],
                "made_changes": [f"declared fixture change for {source}"],
                "not_proven": ["semantic correctness of the returned note"],
            }
            if source.endswith("closure"):
                returned["remaining_delta"] = ["none declared by this fixture run"]
            return returned

        with tempfile.TemporaryDirectory(prefix="bp-link-route-evidence-") as tmpdir:
            result = run_building_plan(
                plan,
                output_root=Path(tmpdir),
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
            )
            root = Path(result.lifecycle_write.root)
            frontier = observe_building_frontier(root, repo_root=repo)
            if frontier.get("frontier_kind") != "complete":
                raise ProfileError(
                    f"link_route_evidence_case rejected {label}: generated building "
                    f"frontier is {frontier.get('frontier_kind')!r}, expected complete"
                )

            outputs_root = root / "work" / "step-outputs"

            def _one_output_dir(brick_ref: str) -> Path:
                # Located by brick_instance_ref: under the modern unroll grammar
                # each replay attempt is its OWN declared step (the attempt
                # semantic lives in the step/brick name; attempt_index presence
                # is asserted by the property tables).
                matches = [
                    path
                    for path in sorted(outputs_root.glob("*/step-output.json"))
                    if json.loads(path.read_text(encoding="utf-8")).get("brick_instance_ref")
                    == brick_ref
                ]
                if len(matches) != 1:
                    raise ProfileError(
                        f"link_route_evidence_case rejected {label}: expected exactly one "
                        f"step output for {brick_ref}, observed {len(matches)}"
                    )
                return matches[0].parent

            concern_dir = _one_output_dir(concern_brick)
            concern_output = json.loads(
                (concern_dir / "step-output.json").read_text(encoding="utf-8")
            )
            for dotted in _LINK_CASE_CONCERN_STEP_OUTPUT_REQUIRED:
                if not json_path_exists(concern_output, dotted):
                    raise ProfileError(
                        f"link_route_evidence_case rejected {label}: concern step output "
                        f"is missing {dotted!r}"
                    )
            concern_record_path = concern_dir / "transition-concern.json"
            if not concern_record_path.is_file():
                raise ProfileError(
                    f"link_route_evidence_case rejected {label}: transition-concern.json "
                    "was not persisted beside the concern step output"
                )
            concern_record = json.loads(concern_record_path.read_text(encoding="utf-8"))
            for dotted in _LINK_CASE_CONCERN_JSON_REQUIRED:
                if not json_path_exists(concern_record, dotted):
                    raise ProfileError(
                        f"link_route_evidence_case rejected {label}: transition-concern.json "
                        f"is missing {dotted!r}"
                    )

            dev_replay_output = json.loads(
                (_one_output_dir(dev_replay_brick) / "step-output.json").read_text(
                    encoding="utf-8"
                )
            )
            for dotted in _LINK_CASE_DEV_REPLAY_STEP_OUTPUT_REQUIRED:
                if not json_path_exists(dev_replay_output, dotted):
                    raise ProfileError(
                        f"link_route_evidence_case rejected {label}: dev replay step "
                        f"output is missing {dotted!r}"
                    )
            qa_replay_dir = _one_output_dir(qa_replay_brick)
            qa_replay_output = json.loads(
                (qa_replay_dir / "step-output.json").read_text(encoding="utf-8")
            )
            for dotted in _LINK_CASE_QA_REPLAY_STEP_OUTPUT_REQUIRED:
                if not json_path_exists(qa_replay_output, dotted):
                    raise ProfileError(
                        f"link_route_evidence_case rejected {label}: qa replay step "
                        f"output is missing {dotted!r}"
                    )
            # route-request persistence (retired step-output-and-route-request-0526
            # pins): the QA replay return carried a non-binding route_request; the
            # writer must persist route-request.json beside the step output and
            # reference it from the step output (route_request_ref).
            route_request_path = qa_replay_dir / "route-request.json"
            if not route_request_path.is_file():
                raise ProfileError(
                    f"link_route_evidence_case rejected {label}: route-request.json was "
                    "not persisted beside the QA replay step output"
                )
            route_request_record = json.loads(route_request_path.read_text(encoding="utf-8"))
            for dotted in _LINK_CASE_ROUTE_REQUEST_JSON_REQUIRED:
                if not json_path_exists(route_request_record, dotted):
                    raise ProfileError(
                        f"link_route_evidence_case rejected {label}: route-request.json "
                        f"is missing {dotted!r}"
                    )
            if "route_request_ref" not in qa_replay_output:
                raise ProfileError(
                    f"link_route_evidence_case rejected {label}: QA replay step output "
                    "does not reference the persisted route request (route_request_ref)"
                )

            for rel, needles in (
                (("raw", "link.jsonl"), _LINK_CASE_RAW_LINK_NEEDLES),
                (
                    ("evidence", "claim_trace", "link", "movement_trace.json"),
                    _LINK_CASE_MOVEMENT_TRACE_NEEDLES,
                ),
                (
                    ("evidence", "claim_trace", "agent", "returned_claims.json"),
                    _LINK_CASE_RETURNED_CLAIMS_NEEDLES,
                ),
                (
                    ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
                    _LINK_CASE_SUFFICIENCY_NEEDLES,
                ),
            ):
                text = root.joinpath(*rel).read_text(encoding="utf-8")
                for needle in needles:
                    if needle not in text:
                        raise ProfileError(
                            f"link_route_evidence_case rejected {label}: "
                            f"{'/'.join(rel)} does not contain {needle!r}"
                        )

            sufficiency_value = json.loads(
                root.joinpath(
                    "evidence", "claim_trace", "link", "sufficiency_trace.json"
                ).read_text(encoding="utf-8")
            )
            for dotted in _LINK_CASE_SUFFICIENCY_JSON_REQUIRED:
                if not json_path_exists(sufficiency_value, dotted):
                    raise ProfileError(
                        f"link_route_evidence_case rejected {label}: sufficiency_trace.json "
                        f"is missing {dotted!r}"
                    )
            building_map = json.loads(
                (root / "work" / "building-map.json").read_text(encoding="utf-8")
            )
            for dotted in _LINK_CASE_BUILDING_MAP_REQUIRED:
                if not json_path_exists(building_map, dotted):
                    raise ProfileError(
                        f"link_route_evidence_case rejected {label}: building-map.json "
                        f"is missing {dotted!r}"
                    )
        count += 1
    return count

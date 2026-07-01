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
import hashlib
import importlib
import io
import json
import os
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

from support.checkers.lib.gate_evidence_readers import (
    _assert_missing_gate_fact_present,
    _assert_no_missing_gate_facts,
    _gate_evidence_paths,
    _json_records,
    _nested_values_for_key,
)
from support.checkers.lib.rule_runners import (
    _admitted_agent_object_refs,
    validate_building_plan_boundary,
    validate_route_policy_boundary,
)
from support.checkers.lib.preset_completion_fixture import (
    _PRESET_COMPLETION_LIST_RETURN_FIELDS,
    _deterministic_completion_list,
    _is_gemini_json_invocation,
    _output_last_message_path,
    _preset_completion_command_runner,
    _preset_completion_prompt_from_cli_args,
    _return_labels_from_cli_prompt,
)
from support.checkers.lib.materialized_plan_observers import (
    _check_declaration_ref_expectations,
    _check_materialize_building_declaration_evidence,
    _link_rows_in_declared_order,
    _link_rows_list_field,
    _link_rows_provenance_declared_by,
    _link_rows_provenance_tokens,
    _materialized_step_values,
    _observed_link_row_values,
)
from support.checkers.lib.materialized_return_shape_guards import (
    _brick_return_shape_fields,
    _check_materialized_node_return_shapes,
    _materialized_brick_row_field,
    _materialized_brick_row_shape,
    _materialized_return_shape_fields,
)
from support.checkers.lib.materialize_reject_scaffold import (
    _materialize_reject_patch_preset_steps,
    _materialize_reject_strip_preset_keys,
    _patched_chain_preset_steps,
    _StripProbe,
    _stripped_chain_preset_keys,
)
from support.checkers.lib.plan_fixture_helpers import (
    _compose_building_expected_codes,
    _compose_building_ok_callable,
    _compose_building_profile_plan,
    _gate_sequence_policy_context,
    _gate_sequence_policy_link_row,
    _graph_test_plan_from_linear,
    _optional_positive_int,
    _validation_plan_for_declared_plan,
)
from support.checkers.lib.adapter_capability_checks import (
    _expect_adapter_capability_rejection,
    _adapter_capability_write_scope,
    _adapter_capability_request,
    _adapter_capability_plan,
    _check_adapter_capability_ok_all_four,
    _check_adapter_capability_claude_write_ok,
    _check_adapter_capability_missing_brick_scope,
    _assert_recorded_write_policy_fact,
    _check_adapter_capability_missing_agent_policy,
    _check_adapter_capability_missing_adapter_capability,
    _check_adapter_capability_observation_out_of_scope,
    _check_adapter_capability_poc_read_only_with_write_scope,
    _check_adapter_capability_legacy_identity_only,
    _check_adapter_capability_no_write_observation_without_scope,
    _check_adapter_capability_write_capable_leader_effective_write_gated_by_brick_scope,
    _native_grant_policy_resource,
    _native_grant_policy_resources,
    _check_adapter_capability_native_grant_roundtrip,
    _check_adapter_capability_native_grant_semantic_codex_gemini_parity,
    _check_adapter_capability_retired_gemini_api_no_write_or_probe,
    _check_adapter_capability_checker_sweep_blocks_live_provider_cli,
    _check_adapter_capability_native_grant_policy_only_fails_closed,
    _check_adapter_capability_native_grant_write_home_pin,
    _check_adapter_capability_native_grant_unknown_capability,
    _check_adapter_capability_write_capable_leader_read_only_brick_projection,
    _check_adapter_capability_write_capable_leader_write_needed_brick_projection,
    _check_adapter_capability_write_scope_on_read_only_brick_rejected,
    _check_adapter_capability_silent_write_grant_rejected_at_run_admission,
    _check_adapter_capability_explicit_write_need_marker_admitted_strict,
    _check_adapter_capability_legacy_write_need_marker_not_recognized,
    _check_adapter_capability_legacy_write_need_graph_row_key_rejected,
    _adapter_capability_single_step_packet,
    _check_adapter_capability_silent_write_grant_rejected_single_step,
    _check_adapter_capability_explicit_write_need_marker_single_step_proceeds,
)
from support.checkers.lib.casting_node_carry_check import (
    _casting_node_carry_base_graph_plan,
    run_casting_node_carry,
)


def run_adapter_model_selection_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "adapter_model_selection_case")
    if not items:
        return 0
    from brick_protocol.support.connection.adapter_model_casting import project_model_ref_to_cli_arg

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
    from brick_protocol.support.connection.adapter_model_casting import project_model_ref_to_cli_arg

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
        expected = require_mapping(mapping.get("expected", {}), "materialize_building_intent_case.expected")
        agent_object_digests_before = (
            _agent_object_file_digests(repo)
            if expected.get("agent_object_hashes_unchanged")
            else {}
        )
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
        if expected.get("agent_object_hashes_unchanged"):
            agent_object_digests_after = _agent_object_file_digests(repo)
            if agent_object_digests_after != agent_object_digests_before:
                before_keys = set(agent_object_digests_before)
                after_keys = set(agent_object_digests_after)
                changed = sorted(
                    path
                    for path in before_keys & after_keys
                    if agent_object_digests_before[path] != agent_object_digests_after[path]
                )
                added = sorted(after_keys - before_keys)
                removed = sorted(before_keys - after_keys)
                raise ProfileError(
                    f"materialize_building_intent_case rejected {relative}: "
                    "agent object files mutated during materialization "
                    f"(changed={changed}, added={added}, removed={removed})"
                )
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


def _agent_object_file_digests(repo: Path) -> dict[str, str]:
    objects_dir = repo / "agent" / "objects"
    digests: dict[str, str] = {}
    for path in sorted(objects_dir.glob("*.yaml")):
        if not path.is_file():
            continue
        relative = path.relative_to(repo).as_posix()
        digests[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


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
    from support.operator.plan_rendering import _load_shape_registry
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
        with tempfile.TemporaryDirectory(
            prefix="bp-preset-building-completion-"
        ) as tmpdir, _fixture_gemini_api_key():
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
                _assert_no_missing_gate_facts(
                    result.lifecycle_write.root,
                    label=f"{label}/{preset_ref}",
                )
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


@contextlib.contextmanager
def _fixture_gemini_api_key():
    """Open gemini-local fixture dispatch without depending on real credentials."""

    from brick_protocol.support.connection.agent_adapter import _GEMINI_API_KEY_ENV_VARS

    saved_env = {name: os.environ.get(name) for name in _GEMINI_API_KEY_ENV_VARS}
    for name in _GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "checker-fixture-key"
    try:
        yield
    finally:
        for name in _GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]


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
                    _preset_completion_prompt_from_cli_args(checked_args)
                )
                if labels:
                    captured_labels.append(labels)
            return base_runner(args, cwd, timeout_seconds)

        with tempfile.TemporaryDirectory(prefix="bp-adapter-gate-shape-union-") as tmpdir, _fixture_gemini_api_key():
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

        with tempfile.TemporaryDirectory(prefix="bp-building-intake-seam-") as tmpdir, _fixture_gemini_api_key():
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
                    local_callables=local_callables,
                    command_runner=command_runner,
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
            from support.operator.composition_intent import materialize_building_intent

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
                    local_callables=local_callables,
                    command_runner=command_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
                try:
                    run_building_intake(
                        dict(derived_intent),
                        repo_root=repo,
                        output_root=retry_output,
                        overwrite_existing=False,
                        local_callables=local_callables,
                        command_runner=command_runner,
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
            with _fixture_gemini_api_key():
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
      4. FRONTIER-EVIDENCE: the default example routes through the seam and
         reaches the expected frontier with landed evidence under the TEMP
         output_root (never the repo). After preferred step-adapter resolution,
         no-provider machines may honestly record agent_incomplete for verdict
         rows that resolve to non-local preferred adapters.
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
    agent_adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    seam_verb = onboard.SEAM_VERB
    command_runner = _preset_completion_command_runner(agent_adapter.LocalCliCompleted)
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
        # FRONTIER is provider-availability dependent (see docstring): the example's
        # preferred-step adapters resolve to non-local providers whose readiness + the
        # design-step outcome decide whether verdict rows complete or honestly record
        # agent_incomplete. BOTH are honest. Accept the declared honest SET, not a
        # single machine-dependent value -- a single pin makes this profile flaky on
        # provider-equipped machines (brick verify / --all). Anything OUTSIDE the set
        # (error/empty/unexpected) still REDs.
        acceptable_raw = mapping.get("acceptable_frontier_kinds")
        if acceptable_raw is not None:
            if not isinstance(acceptable_raw, (list, tuple)) or not acceptable_raw:
                raise ProfileError(
                    f"{label}: acceptable_frontier_kinds must be a non-empty list"
                )
            acceptable_frontiers = {
                require_string(value, f"{label}: acceptable_frontier_kinds item")
                for value in acceptable_raw
            }
        else:
            acceptable_frontiers = {
                require_string(
                    mapping.get("expected_frontier_kind", "complete"),
                    f"{label}: expected_frontier_kind",
                )
            }

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
                    command_runner=command_runner,
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
            if example.get("frontier_kind") not in acceptable_frontiers:
                raise ProfileError(
                    f"onboard_seam_case rejected {label}: example frontier "
                    f"{example.get('frontier_kind')!r} is not one of the honest "
                    f"provider-dependent outcomes {sorted(acceptable_frontiers)}"
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
                    command_runner=command_runner,
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
        selected_adapter_raw = mapping.get("selected_adapter_ref")
        selected_adapter_ref = (
            require_string(selected_adapter_raw, f"{label}: selected_adapter_ref")
            if selected_adapter_raw is not None
            else None
        )
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

        packet = render_agent_candidate_packet(
            role_need,
            write_need,
            selected_adapter_ref=selected_adapter_ref,
            repo_root=repo,
        )

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
        if selected_adapter_ref is None:
            if "selected_adapter_ref" in packet:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: omitted selected_adapter_ref "
                    "must not be invented by support"
                )
        elif packet.get("selected_adapter_ref") != selected_adapter_ref:
            raise ProfileError(
                f"agent_candidate_packet_case rejected {label}: selected_adapter_ref expected "
                f"{selected_adapter_ref!r}, observed {packet.get('selected_adapter_ref')!r}"
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
            adapter_refs = row.get("adapter_refs")
            if not isinstance(adapter_refs, list) or not all(
                isinstance(ref, str) and ref for ref in adapter_refs
            ):
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: row "
                    f"{row.get('agent_object_ref')!r} adapter_refs must be a non-empty string list"
                )
            for preferred_key in ("preferred_adapter_ref", "preferred_model_ref"):
                if not isinstance(row.get(preferred_key), str):
                    raise ProfileError(
                        f"agent_candidate_packet_case rejected {label}: row "
                        f"{row.get('agent_object_ref')!r} {preferred_key} must be rendered as text"
                    )
            if selected_adapter_ref is None:
                for compatibility_key in (
                    "selected_adapter_compatible",
                    "preferred_adapter_matches_selected",
                ):
                    if compatibility_key in row:
                        raise ProfileError(
                            f"agent_candidate_packet_case rejected {label}: row "
                            f"{row.get('agent_object_ref')!r} must not invent {compatibility_key} "
                            "when selected_adapter_ref is omitted"
                        )
            else:
                expected_compatible = selected_adapter_ref in set(adapter_refs)
                if row.get("selected_adapter_compatible") != expected_compatible:
                    raise ProfileError(
                        f"agent_candidate_packet_case rejected {label}: row "
                        f"{row.get('agent_object_ref')!r} selected_adapter_compatible expected "
                        f"{expected_compatible}, observed {row.get('selected_adapter_compatible')!r}"
                    )
                expected_preferred_match = row.get("preferred_adapter_ref") == selected_adapter_ref
                if row.get("preferred_adapter_matches_selected") != expected_preferred_match:
                    raise ProfileError(
                        f"agent_candidate_packet_case rejected {label}: row "
                        f"{row.get('agent_object_ref')!r} preferred_adapter_matches_selected expected "
                        f"{expected_preferred_match}, observed "
                        f"{row.get('preferred_adapter_matches_selected')!r}"
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

        for rejected_ref in require_string_list(
            mapping.get("rejected_selected_adapter_refs", []),
            f"{label}: rejected_selected_adapter_refs",
        ):
            try:
                render_agent_candidate_packet(
                    role_need,
                    write_need,
                    selected_adapter_ref=rejected_ref,
                    repo_root=repo,
                )
            except ValueError:
                pass
            else:
                raise ProfileError(
                    f"agent_candidate_packet_case rejected {label}: selected_adapter_ref "
                    f"{rejected_ref!r} was not rejected"
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
    from brick_protocol.support.operator.composition_intent import materialize_building_intent

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
    from support.operator.composition_gate_translation import declared_portfolio_gate_translations

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
        if "brick_capability_class" in expected:
            brick_rows = [row for row in rows if isinstance(row, Mapping) and row.get("axis") == "Brick"]
            if len(brick_rows) != 1:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: Brick row missing"
                )
            observed_capability = brick_rows[0].get("capability_class")
            if observed_capability != expected["brick_capability_class"]:
                raise ProfileError(
                    f"declared_step_template_plan_case rejected {relative}: "
                    f"brick_capability_class expected {expected['brick_capability_class']!r}, "
                    f"observed {observed_capability!r}"
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
    from support.connection.agent_adapter import LocalCliCompleted
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
    from support.operator.composition_route_policy import _composition_resolve_route_policy_provenance

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
    from support.operator.composition_graph_validate import _composition_policy_action

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
        expected_capability_classes = require_string_list(
            expected.get("brick_capability_classes", []),
            "compose_building_case.expected.brick_capability_classes",
        )
        if expected_capability_classes:
            observed_capability_classes: list[str] = []
            for step in plan.get("brick_steps", []):
                if not isinstance(step, Mapping):
                    continue
                rows = step.get("rows", [])
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if isinstance(row, Mapping) and row.get("axis") == "Brick":
                        observed_capability_classes.append(str(row.get("capability_class", "")))
                        break
            if observed_capability_classes != expected_capability_classes:
                raise ProfileError(
                    f"compose_building_case rejected {relative}: brick_capability_classes "
                    f"expected {expected_capability_classes!r}, observed {observed_capability_classes!r}"
                )
        expected_frontier = expected.get("frontier_kind")
        if expected_frontier:
            with tempfile.TemporaryDirectory(
                prefix="bp-compose-building-case-"
            ) as tmpdir, _fixture_gemini_api_key():
                result = run_building_plan(
                    plan,
                    output_root=Path(tmpdir),
                    overwrite_existing=True,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _compose_building_ok_callable
                    },
                    command_runner=_preset_completion_command_runner(LocalCliCompleted),
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
            from support.operator.composition_intent import (  # noqa: PLC0415
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
    from support.operator.composition_intent import LINEAR_COMPOSITION_MODE
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
            # Smith 0623 LOCK: the request no longer raises -- assert the recorded fact.
            _check_adapter_capability_missing_agent_policy(label, expected_reason)
        elif case_kind == "missing_adapter_capability":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_missing_adapter_capability(label),
            )
        elif case_kind == "observation_out_of_scope":
            # Smith 0623 LOCK: this no longer rejects -- it asserts the recorded fact.
            _check_adapter_capability_observation_out_of_scope(label)
        elif case_kind == "poc_read_only_adapter_with_write_scope":
            # Smith 0623 LOCK: the request no longer raises -- assert the recorded fact.
            _check_adapter_capability_poc_read_only_with_write_scope(label, expected_reason)
        elif case_kind == "legacy_adapter_identity_only_not_authority":
            # Smith 0623 LOCK: the request no longer raises -- assert the recorded fact.
            _check_adapter_capability_legacy_identity_only(label, expected_reason)
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
        elif case_kind == "native_grant_roundtrip":
            _check_adapter_capability_native_grant_roundtrip(label)
        elif case_kind == "native_grant_semantic_codex_gemini_parity":
            _check_adapter_capability_native_grant_semantic_codex_gemini_parity(label)
        elif case_kind == "retired_gemini_api_no_write_or_probe":
            _check_adapter_capability_retired_gemini_api_no_write_or_probe(label)
        elif case_kind == "checker_sweep_blocks_live_provider_cli":
            _check_adapter_capability_checker_sweep_blocks_live_provider_cli(label)
        elif case_kind == "native_grant_policy_only_fails_closed":
            _check_adapter_capability_native_grant_policy_only_fails_closed(label)
        elif case_kind == "native_grant_write_home_pin":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_native_grant_write_home_pin(label),
            )
        elif case_kind == "native_grant_unknown_capability":
            _expect_adapter_capability_rejection(
                label,
                expected_reason,
                lambda: _check_adapter_capability_native_grant_unknown_capability(label),
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
                    "declared_gate_refs": ["link-gate:default-transition"],
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
    # REDO (Smith 0623 struct-surgery): a directory-style allowed path is still NOT
    # recursive -- the child path falls outside the declared scope -- but the
    # written-vs-scope classification moved OUT of write_observation INTO the Brick
    # axis (brick.comparison) and the disposition is a RECORDED FACT, not a raise.
    # The probe asserts the Brick comparison records the child under
    # observed_paths_outside_declared_scope (an explicit wildcard still admits the
    # child, covered by _check_explicit_wildcard_allows_children).
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope

    facts = compare_changed_paths_to_write_scope(
        ["project/example/work/building-map.json"],
        {"allowed_paths": ["project/example"]},
    )
    outside = facts.get("observed_paths_outside_declared_scope", [])
    if "project/example/work/building-map.json" not in outside:
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: a directory-allowed "
            "child path must be RECORDED as observed_paths_outside_declared_scope by "
            f"brick.comparison (directory scope is not recursive; move+record only), "
            f"observed {facts!r}"
        )


def _check_explicit_wildcard_allows_children(label: str) -> None:
    # REDO (Smith 0623 struct-surgery): the written-vs-scope comparison moved to the
    # Brick axis. An explicit ``**`` wildcard must admit the child -- i.e. the Brick
    # comparison records NO out-of-scope bucket for it.
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope

    facts = compare_changed_paths_to_write_scope(
        ["project/example/work/building-map.json"],
        {"allowed_paths": ["project/example/**"]},
    )
    if facts.get("observed_paths_outside_declared_scope"):
        raise ProfileError(
            f"write_scope_default_exclude_case rejected {label}: wildcard did not "
            f"allow child (brick.comparison recorded it out-of-scope), observed {facts!r}"
        )


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


def run_wiki_carry_truncation_survival_case(
    repo: Path, profile: Mapping[str, Any]
) -> int:
    """Pin: the load-bearing PATH + NOTE survive DOWNSTREAM re-truncation.

    The blocker (0619 adversarial verify): the wiki view is floored by
    ``safe_source_fact_body`` once in the walker AND AGAIN downstream in the
    agent adapter (``_clean_source_fact_bodies`` limit 12000,
    ``_source_fact_bodies_for_prompt`` limit 12000 / small-limit probe 4000). Every floor
    truncates the TAIL. When ``returned`` is large the whole serialized view
    blows past a downstream limit; if PATH/NOTE rode in the tail (the old
    layout) they were silently amputated and the worker lost the "go look"
    address (operator measured: 12534-char view -> ``wiki_carry_path_text``
    None at limit 12000 AND 4000).

    This pin builds the view through the REAL ``_wiki_carry_view`` with an
    OVERSIZE ``returned`` (well past every limit), re-truncates it at limit
    12000 AND 4000 via the REAL ``safe_source_fact_body``, and asserts the
    absolute PATH and the NOTE SURVIVE both. It also asserts a small ``returned``
    keeps path + note + a JSON-parseable summary. Reordering the view so PATH/
    NOTE land in the tail REDs this pin (mutation guard).
    """

    items = rule_items(profile, "wiki_carry_truncation_survival_case")
    if not items:
        return 0
    from brick_protocol.support.connection.adapter_validation import (
        _SOURCE_FACT_BODY_LIMIT,
        safe_source_fact_body,
    )
    from support.operator.walker_kernel import (
        _WIKI_CARRY_NOTE,
        _wiki_carry_view,
        wiki_carry_path_text,
        wiki_carry_summary_text,
    )

    count = 0
    for raw in items:
        mapping = require_mapping(raw, "wiki_carry_truncation_survival_case item")
        label = require_string(
            mapping.get("label"), "wiki_carry_truncation_survival_case.label"
        )
        # The YAML subset returns bare scalars as strings; accept int or
        # int-valued string and coerce.
        raw_oversize = mapping.get("oversize_returned_chars", 20000)
        try:
            oversize_chars = int(raw_oversize)
        except (TypeError, ValueError):
            raise ProfileError(
                f"wiki_carry_truncation_survival_case rejected {label}: "
                "oversize_returned_chars must be a positive integer"
            )
        if oversize_chars <= 0:
            raise ProfileError(
                f"wiki_carry_truncation_survival_case rejected {label}: "
                "oversize_returned_chars must be a positive integer"
            )

        # Use a tmp building root so _wiki_carry_view resolves a real absolute
        # path (the on-disk step-output is never read by this pin; only the path
        # text is exercised). The blocker is in the VIEW LAYOUT, not file IO.
        with tempfile.TemporaryDirectory(prefix="bp-wiki-carry-survival-") as tmpdir:
            building_root = Path(tmpdir)
            step_output_ref = "work/step-outputs/oversize-attempt-1/step-output.json"
            absolute_path = str((building_root / step_output_ref).resolve())

            # OVERSIZE returned: a step-output JSON whose `returned.answer` alone
            # dwarfs every downstream limit, so the serialized view is far past
            # 12000 (and 4000).
            oversize_body = json.dumps(
                {
                    "envelope_marker": "should-not-ride",
                    "raw_stream_ref": "should-not-ride",
                    "returned": {
                        "body_marker": "oversize-body",
                        "answer": "X" * oversize_chars,
                    },
                }
            )
            view = _wiki_carry_view(building_root, step_output_ref, oversize_body)

            # The view itself must already exceed both limits, else this pin is
            # not actually exercising the re-truncation seam.
            if len(view) <= _SOURCE_FACT_BODY_LIMIT:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    f"oversize view is only {len(view)} chars, not past limit "
                    f"{_SOURCE_FACT_BODY_LIMIT} -- raise oversize_returned_chars"
                )

            for limit in (_SOURCE_FACT_BODY_LIMIT, 4000):
                retruncated = safe_source_fact_body(view, limit=limit)
                # The downstream floor MUST have actually fired (tail cut), or
                # the pin proves nothing about survival under truncation.
                if len(retruncated) <= len(view) and len(view) <= limit:
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"view did not exceed limit {limit}"
                    )
                carry_path = wiki_carry_path_text(retruncated)
                if carry_path is None:
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"absolute PATH amputated by tail-truncate at limit {limit} "
                        f"(view layout puts PATH in the tail)"
                    )
                if carry_path != absolute_path:
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"PATH corrupted at limit {limit}: {carry_path!r} != "
                        f"{absolute_path!r}"
                    )
                if not Path(carry_path).is_absolute():
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"surviving PATH is not absolute at limit {limit}"
                    )
                if _WIKI_CARRY_NOTE not in retruncated:
                    raise ProfileError(
                        f"wiki_carry_truncation_survival_case rejected {label}: "
                        f"NOTE amputated by tail-truncate at limit {limit}"
                    )

            # Small returned: full fidelity -- path + note + JSON-parseable
            # summary all present (no truncation regression on the common case).
            small_body = json.dumps(
                {
                    "envelope_marker": "should-not-ride",
                    "returned": {"body_marker": "small-body", "answer": "ok"},
                }
            )
            small_view = _wiki_carry_view(building_root, step_output_ref, small_body)
            if wiki_carry_path_text(small_view) != absolute_path:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned view lost its absolute PATH"
                )
            if _WIKI_CARRY_NOTE not in small_view:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned view lost its NOTE"
                )
            summary = wiki_carry_summary_text(small_view)
            if summary is None:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned view lost its SUMMARY"
                )
            try:
                small_returned = json.loads(summary)
            except json.JSONDecodeError as exc:
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned summary is not JSON"
                ) from exc
            if (
                not isinstance(small_returned, Mapping)
                or small_returned.get("body_marker") != "small-body"
            ):
                raise ProfileError(
                    f"wiki_carry_truncation_survival_case rejected {label}: "
                    "small-returned summary did not round-trip `returned`"
                )
        count += 1
    return count


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
                    else "brick-qa-reroute-code-attack-qa"
                    if case_kind == "live_qa_reroute_to_work_n2"
                    else ""
                ),
                reroute_target_brick=(
                    "brick-replay-work-b"
                    if case_kind == "live_dynamic_full_replay_n3"
                    else "brick-qa-reroute-work"
                    if case_kind == "live_qa_reroute_to_work_n2"
                    else ""
                ),
                source_lane_concerns_by_brick=(
                    _source_lane_transition_concern_fixture()
                    if case_kind == "live_dynamic_fan_in_source_concerns_n4"
                    else None
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
            elif case_kind == "live_qa_reroute_to_work_n2":
                _check_qa_reroute_expected(
                    result,
                    expected,
                    label=label,
                )
            elif case_kind == "live_dynamic_fan_in_source_concerns_n4":
                _check_source_lane_transition_concerns_expected(
                    result,
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
    source_lane_concerns_by_brick: Mapping[str, Any] | None = None
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
                "link_handoff_refs": dict(request.link_handoff_refs),
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
        if (
            self.source_lane_concerns_by_brick
            and request.brick_instance_ref in self.source_lane_concerns_by_brick
        ):
            returned["transition_concern_evidence"] = self.source_lane_concerns_by_brick[
                request.brick_instance_ref
            ]
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
    if expected.get("incoming_step_output_refs") is not None:
        expected_step_output_refs = require_string_list(
            expected.get("incoming_step_output_refs", []),
            f"{label}: expected.incoming_step_output_refs",
        )
        handoff_refs = require_mapping(
            consumer_event.get("link_handoff_refs"),
            f"{label}: link_handoff_refs",
        )
        incoming = handoff_refs.get("incoming")
        if not isinstance(incoming, list):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: incoming handoff refs missing"
            )
        observed_step_output_refs = [
            item.get("from_step_output_ref")
            for item in incoming
            if isinstance(item, Mapping) and item.get("from_step_output_ref") is not None
        ]
        if observed_step_output_refs != expected_step_output_refs:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: incoming step-output refs mismatch"
            )
        expected_root = str(building_root.resolve())
        observed_roots = [
            item.get("building_root_path")
            for item in incoming
            if isinstance(item, Mapping) and item.get("from_step_output_ref") is not None
        ]
        if observed_roots != [expected_root for _ in expected_step_output_refs]:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: incoming building_root_path mismatch"
            )
    if expected.get("receipt_handoff_refs") is not None:
        expected_receipt_refs = require_string_list(
            expected.get("receipt_handoff_refs", []),
            f"{label}: expected.receipt_handoff_refs",
        )
        consumer_results = [
            step_result
            for step_result in getattr(result, "step_results", ())
            if step_result.preparation.brick_instance_ref == consumer_brick
        ]
        if len(consumer_results) != 1:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: consumer receipt count "
                f"expected 1, observed {len(consumer_results)}"
            )
        observed_receipt_refs = list(
            consumer_results[0].preparation.receipt_fact.received_handoff_refs
        )
        if observed_receipt_refs != expected_receipt_refs:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: receipt handoff refs mismatch"
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
    source_brick = require_string(
        expected.get("reroute_source_brick_instance_ref"),
        f"{label}: expected.reroute_source_brick_instance_ref",
    )
    consumer_brick = require_string(
        expected.get("consumer_brick_instance_ref"),
        f"{label}: expected.consumer_brick_instance_ref",
    )
    replay_window = require_string_list(
        expected.get("replay_window_brick_instance_refs", []),
        f"{label}: expected.replay_window_brick_instance_refs",
    )
    # CANONICAL-ORDER ORACLE (P6-C parallel fix): the ORDERED replay window is
    # asserted on the RECORDED ledger (result.step_results), NOT on
    # observed.events. observed.events is appended INSIDE the agent callable at
    # invocation time, so under pool>1 the fan-out siblings (code/axis/evidence
    # QA) append in thread-COMPLETION order -- a race that has nothing to do with
    # what BRICK persisted. The drain (walker_kernel._drain_pending_outcomes_
    # before_terminal) records step_results in canonical frontier/declaration
    # order, byte-identical for pool=1 and pool=N. So derive the window from the
    # persisted ledger; the events hook stays the source of truth only for the
    # ORDER-INDEPENDENT carry/marker/source-fact assertions below.
    recorded = [
        str(step_result.preparation.brick_instance_ref)
        for step_result in result.step_results
    ]
    try:
        # LAST occurrence of the reroute source: it is the step the human reroute
        # fired from; the replay segment is everything recorded AFTER it.
        source_index = max(
            index for index, ref in enumerate(recorded) if ref == source_brick
        )
    except ValueError as exc:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: reroute source was not recorded"
        ) from exc
    try:
        # FIRST occurrence of the consumer (fan-in closure) AFTER the source.
        closure_index = next(
            index
            for index, ref in enumerate(recorded)
            if ref == consumer_brick and index > source_index
        )
    except StopIteration as exc:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: replay closure was not recorded"
        ) from exc
    recorded_slice = recorded[source_index + 1 : closure_index + 1]
    if recorded_slice != replay_window:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: full replay window mismatch "
            f"(got={recorded_slice}, expected={replay_window})"
        )
    # Order-independent: the consumer event must still carry the full QA cohort
    # (set/membership + marker check), unaffected by sibling completion order.
    _check_replay_closure_carry(events, expected, label=label)
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


def _check_qa_reroute_expected(
    result: Any,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    recorded = [
        str(step_result.preparation.brick_instance_ref)
        for step_result in result.step_results
    ]
    expected_recorded = require_string_list(
        expected.get("recorded_brick_instance_refs", []),
        f"{label}: expected.recorded_brick_instance_refs",
    )
    if recorded != expected_recorded:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: recorded reroute sequence mismatch "
            f"(got={recorded}, expected={expected_recorded})"
        )
    records = getattr(result, "_dynamic_walker_reroute_records", ())
    adopted = [
        record
        for record in records
        if isinstance(record, Mapping) and not record.get("disposition_required")
    ]
    if len(adopted) != 1:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: expected one adopted QA reroute, observed {len(adopted)}"
        )
    expected_target = require_string(
        expected.get("adopted_target_ref"),
        f"{label}: expected.adopted_target_ref",
    )
    observed_target = str(
        adopted[0].get("target_ref")
        or adopted[0].get("target_brick_ref")
        or adopted[0].get("pending_target_ref")
        or ""
    )
    if observed_target and observed_target != expected_target:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: adopted target mismatch "
            f"(got={observed_target!r}, expected={expected_target!r})"
        )
    dynamic_evidence = require_mapping(
        getattr(result, "_dynamic_walker_evidence", {}),
        f"{label}: _dynamic_walker_evidence",
    )
    if dynamic_evidence.get("held") is True:
        raise ProfileError(f"step_output_drain_case rejected {label}: QA reroute proof held")


def _source_lane_transition_concern_fixture() -> Mapping[str, Any]:
    concerns: dict[str, Any] = {}
    for brick_ref in (
        "brick-source-concern-code-attack-qa",
        "brick-source-concern-axis-attack-qa",
        "brick-source-concern-evidence-integrity",
    ):
        concerns[brick_ref] = {
            "concern_ref": f"transition-concern:{brick_ref}",
            "concern_kind": "implementation_gap",
            "binding": False,
            "reason_refs": [f"observation:{brick_ref}:source-lane"],
            "related_boundary_refs": ["brick-source-concern-work"],
        }
    concerns["brick-source-concern-inspect"] = {
        "concern_ref": "transition-concern:brick-source-concern-inspect",
        "concern_kind": "implementation_gap",
        "binding": False,
        "reason_refs": [],
        "related_boundary_refs": ["brick-source-concern-work"],
    }
    return concerns


def _check_source_lane_transition_concerns_expected(
    result: Any,
    expected: Mapping[str, Any],
    *,
    label: str,
) -> None:
    dynamic_evidence = require_mapping(
        getattr(result, "_dynamic_walker_evidence", {}),
        f"{label}: _dynamic_walker_evidence",
    )
    if dynamic_evidence.get("held") is True:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source-lane concern proof held"
        )
    records = getattr(result, "_dynamic_walker_reroute_records", ())
    adopted = [
        record
        for record in records
        if isinstance(record, Mapping) and not record.get("disposition_required")
    ]
    if adopted:
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source-lane concern adopted reroute"
        )
    observations = dynamic_evidence.get("source_lane_transition_concern_observations")
    if not isinstance(observations, list):
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source-lane observations missing"
        )
    expected_bricks = require_string_list(
        expected.get("observed_source_brick_refs", []),
        f"{label}: expected.observed_source_brick_refs",
    )
    by_brick = {
        str(item.get("source_brick_ref")): item
        for item in observations
        if isinstance(item, Mapping)
    }
    if sorted(by_brick) != sorted(expected_bricks):
        raise ProfileError(
            f"step_output_drain_case rejected {label}: source-lane observation refs mismatch "
            f"(got={sorted(by_brick)}, expected={sorted(expected_bricks)})"
        )
    malformed = require_string_list(
        expected.get("malformed_source_brick_refs", []),
        f"{label}: expected.malformed_source_brick_refs",
    )
    for brick_ref in expected_bricks:
        observation = require_mapping(
            by_brick.get(brick_ref),
            f"{label}: source observation {brick_ref}",
        )
        if observation.get("transition_concern_adoption") != "advisory":
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {brick_ref} did not record advisory policy"
            )
        if observation.get("adopted_as_movement") is not False:
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {brick_ref} was recorded as Movement"
            )
        if brick_ref in malformed:
            if observation.get("concern_state") != "malformed":
                raise ProfileError(
                    f"step_output_drain_case rejected {label}: {brick_ref} was not malformed evidence"
                )
            if not observation.get("invalid_reason"):
                raise ProfileError(
                    f"step_output_drain_case rejected {label}: malformed source lacked invalid_reason"
                )
            continue
        if observation.get("concern_state") != "valid":
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {brick_ref} was not valid evidence"
            )
        if not observation.get("reason_refs") or not observation.get("related_boundary_refs"):
            raise ProfileError(
                f"step_output_drain_case rejected {label}: {brick_ref} lacked reason/related refs"
            )


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
    if case_kind == "live_qa_reroute_to_work_n2":
        return _qa_reroute_to_work_drain_plan(), "dynamic"
    if case_kind == "live_dynamic_fan_in_source_concerns_n4":
        return _dynamic_source_lane_transition_concern_plan(), "dynamic"
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
        "declared_gate_refs": ["link-gate:default-transition"],
    }
    if closed:
        link_row["building_lifecycle"] = {
            "state": "closed",
            "reason": "checker live step-output drain close",
        }
    return {
        "step_ref": step_ref,
        "step_template_ref": "",
        "selected_adapter_ref": "adapter:local",
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


def _qa_reroute_to_work_drain_plan() -> Mapping[str, Any]:
    """Small graph proving a QA-emitted concern is not decorative.

    work -> code-attack-qa -> closure. The observed callable emits one
    implementation_gap transition_concern_evidence from the QA brick targeting
    the upstream work brick. The dynamic walker should adopt the valid concern
    under default-transition, consume the work node's reroute budget, and record
    a second work attempt before closure. This is support evidence only: it does
    not make QA a Movement authority and does not judge success/quality.
    """

    return {
        "plan_ref": "building-plan:checker-live-qa-reroute-to-work",
        "building_id": "checker-live-qa-reroute-to-work",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "execution_order": [
            "qa-reroute-work",
            "qa-reroute-code-attack-qa",
            "qa-reroute-closure",
        ],
        "brick_steps": [
            _graph_brick_step(
                "qa-reroute-work",
                "brick-qa-reroute-work",
                "edge:qa-reroute-work-to-code-attack-qa",
            ),
            _graph_brick_step(
                "qa-reroute-code-attack-qa",
                "brick-qa-reroute-code-attack-qa",
                "edge:qa-reroute-code-attack-qa-to-closure",
            ),
            _graph_brick_step(
                "qa-reroute-closure",
                "brick-qa-reroute-closure",
                "edge:qa-reroute-closure-to-boundary",
            ),
        ],
        "link_edges": [
            _graph_link_edge(
                "edge:qa-reroute-work-to-code-attack-qa",
                "qa-reroute-work",
                "qa-reroute-code-attack-qa",
                "brick-qa-reroute-code-attack-qa",
            ),
            _graph_link_edge(
                "edge:qa-reroute-code-attack-qa-to-closure",
                "qa-reroute-code-attack-qa",
                "qa-reroute-closure",
                "brick-qa-reroute-closure",
            ),
            _graph_link_edge(
                "edge:qa-reroute-closure-to-boundary",
                "qa-reroute-closure",
                "",
                "building-boundary:checker-live-qa-reroute-to-work-closed",
            ),
        ],
        "node_reroute_budgets": {"brick-qa-reroute-work": 1},
    }


def _dynamic_source_lane_transition_concern_plan() -> Mapping[str, Any]:
    return {
        "plan_ref": "building-plan:checker-live-fan-in-source-concerns",
        "building_id": "checker-live-fan-in-source-concerns",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _step_output_drain_proof_limits(),
        "not_proven": ["checker live runner proof only"],
        "execution_order": [
            "source-concern-work",
            "source-concern-code-attack-qa",
            "source-concern-axis-attack-qa",
            "source-concern-evidence-integrity",
            "source-concern-inspect",
            "source-concern-closure",
        ],
        "brick_steps": [
            _graph_brick_step(
                "source-concern-work",
                "brick-source-concern-work",
                "edge:source-concern-work-to-code",
            ),
            _graph_brick_step(
                "source-concern-code-attack-qa",
                "brick-source-concern-code-attack-qa",
                "edge:source-concern-code-to-closure",
                step_template_ref="building-step-template:code-attack-qa",
            ),
            _graph_brick_step(
                "source-concern-axis-attack-qa",
                "brick-source-concern-axis-attack-qa",
                "edge:source-concern-axis-to-closure",
                step_template_ref="building-step-template:axis-attack-qa",
            ),
            _graph_brick_step(
                "source-concern-evidence-integrity",
                "brick-source-concern-evidence-integrity",
                "edge:source-concern-evidence-to-closure",
                step_template_ref="building-step-template:evidence-integrity",
            ),
            _graph_brick_step(
                "source-concern-inspect",
                "brick-source-concern-inspect",
                "edge:source-concern-inspect-to-closure",
                step_template_ref="building-step-template:inspect",
            ),
            _graph_brick_step(
                "source-concern-closure",
                "brick-source-concern-closure",
                "edge:source-concern-closure-to-boundary",
            ),
        ],
        "link_edges": [
            _graph_link_edge(
                "edge:source-concern-work-to-code",
                "source-concern-work",
                "source-concern-code-attack-qa",
                "brick-source-concern-code-attack-qa",
            ),
            _graph_link_edge(
                "edge:source-concern-work-to-axis",
                "source-concern-work",
                "source-concern-axis-attack-qa",
                "brick-source-concern-axis-attack-qa",
            ),
            _graph_link_edge(
                "edge:source-concern-work-to-evidence",
                "source-concern-work",
                "source-concern-evidence-integrity",
                "brick-source-concern-evidence-integrity",
            ),
            _graph_link_edge(
                "edge:source-concern-work-to-inspect",
                "source-concern-work",
                "source-concern-inspect",
                "brick-source-concern-inspect",
            ),
            _graph_link_edge(
                "edge:source-concern-code-to-closure",
                "source-concern-code-attack-qa",
                "source-concern-closure",
                "brick-source-concern-closure",
            ),
            _graph_link_edge(
                "edge:source-concern-axis-to-closure",
                "source-concern-axis-attack-qa",
                "source-concern-closure",
                "brick-source-concern-closure",
            ),
            _graph_link_edge(
                "edge:source-concern-evidence-to-closure",
                "source-concern-evidence-integrity",
                "source-concern-closure",
                "brick-source-concern-closure",
            ),
            _graph_link_edge(
                "edge:source-concern-inspect-to-closure",
                "source-concern-inspect",
                "source-concern-closure",
                "brick-source-concern-closure",
            ),
            _graph_link_edge(
                "edge:source-concern-closure-to-boundary",
                "source-concern-closure",
                "",
                "building-boundary:checker-live-fan-in-source-concerns-closed",
            ),
        ],
        "groups": [
            {
                "group_id": "group:checker-source-concern-fan-out",
                "group_role": "fan_out",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:source-concern-work-to-code",
                    "edge:source-concern-work-to-axis",
                    "edge:source-concern-work-to-evidence",
                    "edge:source-concern-work-to-inspect",
                ],
            },
            {
                "group_id": "group:checker-source-concern-fan-in",
                "group_role": "fan_in",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:source-concern-code-to-closure",
                    "edge:source-concern-axis-to-closure",
                    "edge:source-concern-evidence-to-closure",
                    "edge:source-concern-inspect-to-closure",
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
    step_template_ref: str = "",
) -> Mapping[str, Any]:
    step: dict[str, Any] = {
        "step_ref": step_ref,
        "completion_edge_ref": completion_edge_ref,
        "selected_adapter_ref": "adapter:local",
        "rows": [
            _brick_row(step_ref, brick_ref, source_facts=source_facts),
            _agent_row(step_ref),
        ],
    }
    if step_template_ref:
        step["step_template_ref"] = step_template_ref
    return step


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
    else:
        link_row["declared_gate_refs"] = ["link-gate:default-transition"]
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
            with _fixture_gemini_api_key():
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

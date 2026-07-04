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
import hashlib
import io
import json
import os
import tempfile
import uuid
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
from support.checkers.lib.fixture_graph_helpers import (
    fixture_agent_row,
    fixture_brick_row,
    fixture_graph_brick_step,
    fixture_graph_link_edge,
    fixture_proof_limits,
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
    _fixture_gemini_api_key,
    _optional_non_negative_int,
    run_adapter_model_selection_case,
    run_adapter_model_selection_rejects,
    run_adapter_gate_shape_union_case,
    run_adapter_capability_rehome_case,
)
# Re-export witness for frozen profile text probes:
# adapter_capability_rehome_case covers ok_all_four,
# poc_read_only_adapter_with_write_scope, and
# legacy_adapter_identity_only_not_authority in adapter_capability_checks.py.
from support.checkers.lib.casting_node_carry_check import (
    _casting_node_carry_base_graph_plan,
    run_casting_node_carry,
)

from support.checkers.lib.checker_temp_vessel import (
    _TEMP_VESSEL_REPO_ENV,
    _TEMP_VESSEL_SENTINEL_NAME,
    _copy_checker_temp_repo_resources,
    _patched_temp_repo_roots,
    _write_temp_vessel_sentinel,
    _assert_deletable_checker_vessel,
    _delete_checker_vessel,
    _temp_vessel_cleanup_or_reject,
    _with_temp_vessel_repo,
    _assert_temp_vessel_guard_teeth,
    _preset_slug,
    _case_slug,
    assert_checker_vessel_patch_closure,
)



def _assert_real_repo_env_flag_cleanup_rejected(repo: Path, profile: Mapping[str, Any]) -> None:
    items = rule_items(profile, "intake_project_vessel_case")
    if not items:
        return
    mapping = require_mapping(items[0], "intake_project_vessel_case item")
    label = require_string(mapping.get("label"), "intake_project_vessel_case.label")
    vessel_id = require_string(mapping.get("vessel_id"), f"{label}: vessel_id")
    previous = os.environ.get(_TEMP_VESSEL_REPO_ENV)
    os.environ[_TEMP_VESSEL_REPO_ENV] = "1"
    try:
        with tempfile.TemporaryDirectory(prefix="bp-real-repo-vessel-delete-negative-") as tmpdir:
            probe_repo = Path(tmpdir) / "repo"
            target = probe_repo / "project" / vessel_id
            _write_temp_vessel_sentinel(
                "intake_project_vessel_case-negative-probe",
                label,
                target,
                "real-repo-negative-probe",
            )
            try:
                _temp_vessel_cleanup_or_reject(
                    "intake_project_vessel_case",
                    label,
                    target,
                    repo=probe_repo,
                    temp_repo=Path(tmpdir) / "other-temp-repo",
                    sentinel_nonce="real-repo-negative-probe",
                )
            except ProfileError:
                if not target.exists():
                    raise ProfileError(
                        "intake_project_vessel_case negative probe deleted a repo "
                        "project path before raising"
                    )
                return
            raise ProfileError(
                "intake_project_vessel_case negative probe did not reject env-flagged "
                "repo project cleanup"
            )
    finally:
        if previous is None:
            os.environ.pop(_TEMP_VESSEL_REPO_ENV, None)
        else:
            os.environ[_TEMP_VESSEL_REPO_ENV] = previous


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






def _intake_project_vessel_stale_paths(repo: Path, profile: Mapping[str, Any]) -> Sequence[Path]:
    paths: list[Path] = []
    for item in rule_items(profile, "intake_project_vessel_case"):
        mapping = require_mapping(item, "intake_project_vessel_case item")
        vessel_id = require_string(mapping.get("vessel_id"), "intake_project_vessel_case.vessel_id")
        paths.append(repo / "project" / vessel_id)
    return paths


def run_intake_project_vessel_case(
    repo: Path,
    profile: Mapping[str, Any],
    temp_repo: Path | None = None,
) -> int:
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
    if temp_repo is None:
        _assert_real_repo_env_flag_cleanup_rejected(repo, profile)
        for item in items:
            mapping = require_mapping(item, "intake_project_vessel_case item")
            label = require_string(mapping.get("label"), "intake_project_vessel_case.label")
            vessel_id = require_string(mapping.get("vessel_id"), f"{label}: vessel_id")
            for fixture_id in (vessel_id, f"{vessel_id}-charterless", f"{vessel_id}-absent"):
                _temp_vessel_cleanup_or_reject(
                    "intake_project_vessel_case",
                    label,
                    repo / "project" / fixture_id,
                    repo=repo,
                    temp_repo=repo,
                    sentinel_nonce=None,
                )
        return _with_temp_vessel_repo(
            repo,
            profile,
            run_intake_project_vessel_case,
            _intake_project_vessel_stale_paths,
            "bp-intake-project-vessel-repo-",
        )

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
            _temp_vessel_cleanup_or_reject(
                "intake_project_vessel_case",
                label,
                fixture_dir,
                repo=repo,
                temp_repo=temp_repo,
                sentinel_nonce=None,
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
            _write_temp_vessel_sentinel(
                "intake_project_vessel_case",
                label,
                vessel_dir,
                uuid.uuid4().hex,
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
            _write_temp_vessel_sentinel(
                "intake_project_vessel_case",
                label,
                charterless_dir,
                uuid.uuid4().hex,
            )
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
            charterless_residue = [
                path
                for path in charterless_dir.rglob("*")
                if path.name != _TEMP_VESSEL_SENTINEL_NAME
            ]
            if charterless_residue:
                raise ProfileError(
                    f"intake_project_vessel_case rejected {label}: the charterless "
                    "reject still wrote into the hand-made vessel dir"
                )
        finally:
            _temp_vessel_cleanup_or_reject(
                "intake_project_vessel_case",
                label,
                vessel_dir,
                repo=repo,
                temp_repo=temp_repo,
                sentinel_nonce=None,
            )
            _temp_vessel_cleanup_or_reject(
                "intake_project_vessel_case",
                label,
                charterless_dir,
                repo=repo,
                temp_repo=temp_repo,
                sentinel_nonce=None,
            )
        count += 1
    return count





from support.checkers.lib.agent_packets_check import (
    run_agent_candidate_packet_case,
    run_preset_ranking_packet_case,
)


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



def _split_ref_row(value: Any) -> list[str]:
    """One per-row expectation: a comma-joined ref string -> ordered ref list."""

    if not isinstance(value, str):
        raise ProfileError(
            f"per-row gate expectation must be a comma-joined string, got {value!r}"
        )
    return [part.strip() for part in value.split(",") if part.strip()]



from support.checkers.lib.declared_step_template_check import (
    run_declared_step_template_plan_case,
    run_declared_step_template_plan_rejects,
)


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










from support.checkers.lib.workflow_import_check import run_workflow_import_case




from support.checkers.lib.once_task_source_check import run_once_task_source_admission_case

from support.checkers.lib.hook_registry_axis_check import run_hook_registry_axis_case




from support.checkers.lib.write_scope_default_exclude_check import run_write_scope_default_exclude_case


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


from support.checkers.lib.wiki_carry_check import run_wiki_carry_truncation_survival_case



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
    return fixture_graph_brick_step(
        step_ref,
        brick_ref,
        completion_edge_ref,
        agent_object_ref="agent-object:coo",
        work_statement=f"Run checker live step-output drain step {step_ref}.",
        required_return_shape="body_marker, source_fact_body_refs, carried_markers, not_proven",
        source_facts=source_facts,
        selected_adapter_ref="adapter:local",
        step_template_ref=step_template_ref,
    )


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
    return fixture_graph_link_edge(
        edge_ref,
        source_step_ref,
        target_ref,
        target_step_ref=target_step_ref,
        movement=movement,
        route_replay_plan=route_replay_plan,
        declared_gate_refs=declared_gate_refs,
        close_reason="checker live step-output drain close",
    )


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
    return fixture_brick_row(
        step_ref,
        brick_ref,
        work_statement=f"Run checker live step-output drain step {step_ref}.",
        required_return_shape="body_marker, source_fact_body_refs, carried_markers, not_proven",
        source_facts=source_facts,
    )


def _agent_row(step_ref: str) -> Mapping[str, Any]:
    return fixture_agent_row(step_ref, agent_object_ref="agent-object:coo")


def _step_output_drain_proof_limits() -> list[str]:
    return fixture_proof_limits()


def _checker_step_output_relative_ref(ref: str) -> str:
    marker = "work/step-outputs/"
    normalized = str(ref).replace("\\", "/")
    if marker not in normalized:
        return normalized
    return normalized[normalized.index(marker) :]


from support.checkers.lib.auto_repair_replay_check import run_auto_repair_replay_case














from support.checkers.lib.child_building_candidate_check import run_child_building_candidate_case
from support.checkers.lib.fail_fixture_check import run_fail_fixture_rejects


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


def _intake_evidence_projection_stale_paths(repo: Path, profile: Mapping[str, Any]) -> Sequence[Path]:
    paths: list[Path] = []
    for item in rule_items(profile, "intake_evidence_projection_case"):
        mapping = require_mapping(item, "intake_evidence_projection_case item")
        vessel_id = require_string(
            mapping.get("vessel_id"), "intake_evidence_projection_case.vessel_id"
        )
        paths.append(repo / "project" / vessel_id)
    return paths


def run_intake_evidence_projection_case(
    repo: Path,
    profile: Mapping[str, Any],
    temp_repo: Path | None = None,
) -> int:
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
    if temp_repo is None:
        for item in items:
            mapping = require_mapping(item, "intake_evidence_projection_case item")
            label = require_string(mapping.get("label"), "intake_evidence_projection_case.label")
            vessel_id = require_string(mapping.get("vessel_id"), f"{label}: vessel_id")
            _temp_vessel_cleanup_or_reject(
                "intake_evidence_projection_case",
                label,
                repo / "project" / vessel_id,
                repo=repo,
                temp_repo=repo,
                sentinel_nonce=None,
            )
        return _with_temp_vessel_repo(
            repo,
            profile,
            run_intake_evidence_projection_case,
            _intake_evidence_projection_stale_paths,
            "bp-intake-evidence-projection-repo-",
        )

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
        _temp_vessel_cleanup_or_reject(
            "intake_evidence_projection_case",
            label,
            vessel_dir,
            repo=repo,
            temp_repo=temp_repo,
            sentinel_nonce=None,
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
            _write_temp_vessel_sentinel(
                "intake_evidence_projection_case",
                label,
                vessel_dir,
                uuid.uuid4().hex,
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
            _temp_vessel_cleanup_or_reject(
                "intake_evidence_projection_case",
                label,
                vessel_dir,
                repo=repo,
                temp_repo=temp_repo,
                sentinel_nonce=None,
            )
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


from support.checkers.lib.route_materialization_check import run_route_materialization_case
from support.checkers.lib.building_intake_seam_check import run_building_intake_seam_case
from support.checkers.lib.onboard_seam_check import run_onboard_seam_case
# Native-dispatch POS-A shape fold relocated intact to native_dispatch_close_check.py:
# _assert_native_dispatch_pos_a_shape, _POS_A_JSON_REQUIRED, _POS_A_TEXT_CONTAINS,
# _POS_A_TEXT_ABSENT, agent_bindings[].agent_performer_ref,
# link_edges[].transition_fact_ref, facts[].fact.observed_match_kind,
# facts[].fact.forbidden_shortcut_evidence, facts[].fact.required_public_facts[],
# facts[].fact.checked_public_fact, "event_type":"building_opened",
# "event_type":"brick_compared", support/run did not classify Agent return,
# support/run did not judge success or quality, hardcoded_pass, forced_sufficient.
from support.checkers.lib.native_dispatch_close_check import run_native_dispatch_close_case
from support.checkers.lib.plan_expansion_case_check import run_plan_expansion_case

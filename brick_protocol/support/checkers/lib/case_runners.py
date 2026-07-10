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
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    json_path_exists,
    load_yaml_subset_file,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)

from brick_protocol.support.checkers.lib.gate_evidence_readers import (
    _assert_missing_gate_fact_present,
    _assert_no_missing_gate_facts,
    _gate_evidence_paths,
    _json_records,
    _nested_values_for_key,
)
from brick_protocol.support.checkers.lib.rule_runners import (
    _admitted_agent_object_refs,
    validate_building_plan_boundary,
    validate_route_policy_boundary,
)
from brick_protocol.support.checkers.lib.preset_completion_fixture import (
    _PRESET_COMPLETION_LIST_RETURN_FIELDS,
    _deterministic_completion_list,
    _is_gemini_json_invocation,
    _output_last_message_path,
    _preset_completion_command_runner,
    _preset_completion_prompt_from_cli_args,
    _return_labels_from_cli_prompt,
)
from brick_protocol.support.checkers.lib.materialized_plan_observers import (
    _check_declaration_ref_expectations,
    _check_materialize_building_declaration_evidence,
    _link_rows_in_declared_order,
    _link_rows_list_field,
    _link_rows_provenance_declared_by,
    _link_rows_provenance_tokens,
    _materialized_step_values,
    _observed_link_row_values,
)
from brick_protocol.support.checkers.lib.materialized_return_shape_guards import (
    _brick_return_shape_fields,
    _check_materialized_node_return_shapes,
    _materialized_brick_row_field,
    _materialized_brick_row_shape,
    _materialized_return_shape_fields,
)
from brick_protocol.support.checkers.lib.materialize_reject_scaffold import (
    _materialize_reject_patch_preset_steps,
    _materialize_reject_strip_preset_keys,
    _patched_chain_preset_steps,
    _StripProbe,
    _stripped_chain_preset_keys,
)
from brick_protocol.support.checkers.lib.plan_fixture_helpers import (
    _compose_building_expected_codes,
    _compose_building_ok_callable,
    _compose_building_profile_plan,
    _gate_sequence_policy_context,
    _gate_sequence_policy_link_row,
    _graph_test_plan_from_linear,
    _optional_positive_int,
    _validation_plan_for_declared_plan,
)
from brick_protocol.support.checkers.lib.adapter_capability_checks import (
    _fixture_gemini_api_key,
    run_adapter_model_selection_case,
    run_adapter_model_selection_rejects,
    run_adapter_gate_shape_union_case,
    run_adapter_capability_rehome_case,
)
# Re-export witness for frozen profile text probes:
# adapter_capability_rehome_case covers ok_all_four,
# poc_read_only_adapter_with_write_scope, and
# legacy_adapter_identity_only_not_authority in adapter_capability_checks.py.
from brick_protocol.support.checkers.lib.casting_node_carry_check import (
    _casting_node_carry_base_graph_plan,
    run_casting_node_carry,
)

from brick_protocol.support.checkers.lib.checker_temp_vessel import (
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
    from brick_protocol.support.operator.route_materialization import materialize_transition_concern_disposition
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


from brick_protocol.support.checkers.lib.materialize_intent_check import (
    run_materialize_building_intent_case,
    run_materialize_building_intent_rejects,
)
# Re-export witness for frozen profile text probes: materialize_intent_check.py
# still covers agent_object_hashes_unchanged and _agent_object_file_digests while
# case_runners remains the hub.















from brick_protocol.support.checkers.lib.intake_project_vessel_check import (
    _intake_project_vessel_stale_paths,
    run_intake_project_vessel_case,
)


from brick_protocol.support.checkers.lib.agent_packets_check import (
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







from brick_protocol.support.checkers.lib.preset_completion_check import (
    _preset_completion_intent,
    _run_preset_completion_portfolio,
    run_preset_building_completion_case,
)


from brick_protocol.support.checkers.lib.declared_step_template_check import (
    run_declared_step_template_plan_case,
    run_declared_step_template_plan_rejects,
)


from brick_protocol.support.checkers.lib.compose_building_check import (
    run_compose_building_case,
    run_compose_building_rejects,
)

def run_gate_sequence_policy_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "gate_sequence_policy_case")
    if not items:
        return 0
    from brick_protocol.support.operator.plan_validation import _validate_gate_sequence_policy_for_link_row

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
    from brick_protocol.support.operator.plan_validation import _validate_gate_sequence_policy_for_link_row

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
    from brick_protocol.support.operator.plan_validation import (
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
    from brick_protocol.support.operator.plan_validation import (
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










from brick_protocol.support.checkers.lib.workflow_import_check import run_workflow_import_case




from brick_protocol.support.checkers.lib.once_task_source_check import run_once_task_source_admission_case

from brick_protocol.support.checkers.lib.hook_registry_axis_check import run_hook_registry_axis_case




from brick_protocol.support.checkers.lib.write_scope_default_exclude_check import run_write_scope_default_exclude_case


from brick_protocol.support.checkers.lib.source_fact_body_carry_check import run_source_fact_body_carry_case


from brick_protocol.support.checkers.lib.wiki_carry_check import run_wiki_carry_truncation_survival_case

from brick_protocol.support.checkers.lib.step_output_drain_check import (
    _agent_row,
    _brick_row,
    _graph_brick_step,
    _graph_link_edge,
    _step_output_drain_proof_limits,
    run_step_output_drain_case,
    run_step_output_drain_rejects,
)

























































from brick_protocol.support.checkers.lib.auto_repair_replay_check import run_auto_repair_replay_case














from brick_protocol.support.checkers.lib.child_building_candidate_check import run_child_building_candidate_case
from brick_protocol.support.checkers.lib.fail_fixture_check import run_fail_fixture_rejects


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






from brick_protocol.support.checkers.lib.intake_evidence_projection_check import (
    _intake_evidence_projection_stale_paths,
    run_intake_evidence_projection_case,
)


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
    # pinned on brick_protocol/link/gate.py itself.
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
    from brick_protocol.support.operator.building_operation import observe_building_frontier
    from brick_protocol.support.operator.import_identity import (
        mint_official_launch_token,
        reset_official_launch_token,
    )
    from brick_protocol.support.operator.run import run_building_plan

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
            launch_token = mint_official_launch_token()
            try:
                result = run_building_plan(
                    plan,
                    output_root=Path(tmpdir),
                    overwrite_existing=True,
                    local_callables={"callable:local:agent-invoke0-smoke": _brain},
                    adapter_cwd=repo,
                    adapter_timeout_seconds=10,
                )
            finally:
                reset_official_launch_token(launch_token)
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


from brick_protocol.support.checkers.lib.route_materialization_check import run_route_materialization_case
from brick_protocol.support.checkers.lib.building_intake_seam_check import run_building_intake_seam_case
from brick_protocol.support.checkers.lib.onboard_seam_check import run_onboard_seam_case
from brick_protocol.support.checkers.lib.operator_correction_check import run_operator_correction_case
# Native-dispatch POS-A shape fold relocated intact to native_dispatch_close_check.py:
# _assert_native_dispatch_pos_a_shape, _POS_A_JSON_REQUIRED, _POS_A_TEXT_CONTAINS,
# _POS_A_TEXT_ABSENT, agent_bindings[].agent_performer_ref,
# link_edges[].transition_fact_ref, facts[].fact.observed_match_kind,
# facts[].fact.forbidden_shortcut_evidence, facts[].fact.required_public_facts[],
# facts[].fact.checked_public_fact, "event_type":"building_opened",
# "event_type":"brick_compared", brick_protocol/support/run did not classify Agent return,
# brick_protocol/support/run did not judge success or quality, hardcoded_pass, forced_sufficient.
from brick_protocol.support.checkers.lib.native_dispatch_close_check import run_native_dispatch_close_case
from brick_protocol.support.checkers.lib.plan_expansion_case_check import run_plan_expansion_case

"""Materialize-building-intent behavioral profile runners.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)
from brick_protocol.support.checkers.lib.materialized_plan_observers import (
    _check_materialize_building_declaration_evidence,
    _link_rows_list_field,
    _link_rows_provenance_declared_by,
    _link_rows_provenance_tokens,
    _materialized_step_values,
    _observed_link_row_values,
)
from brick_protocol.support.checkers.lib.materialized_return_shape_guards import (
    _check_materialized_node_return_shapes,
)
from brick_protocol.support.checkers.lib.materialize_reject_scaffold import (
    _materialize_reject_patch_preset_steps,
    _materialize_reject_strip_preset_keys,
    _patched_chain_preset_steps,
    _stripped_chain_preset_keys,
)


_TIER_PRESET_REFS = frozenset(
    {
        "building-chain-preset:postmortem-fleet",
        "building-chain-preset:recon-fleet",
        "building-chain-preset:recon-fleet-light",
        "building-chain-preset:review-fleet",
    }
)


@contextmanager
def _materialize_provider_registry_fixture(enabled: bool) -> Any:
    if not enabled:
        yield
        return
    previous_home = os.environ.get("BRICK_HOME")
    previous_ladder = os.environ.get("BRICK_PROVIDER_LADDER")
    with tempfile.TemporaryDirectory(prefix="bp-materialize-tier-registry-") as tmp:
        home = Path(tmp)
        (home / "providers.yaml").write_text(
            """version: 1
providers:
  - adapter_ref: adapter:claude-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
  - adapter_ref: adapter:gemini-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
  - adapter_ref: adapter:codex-fugu-local
    registered_at: "2026-07-01T00:00:00Z"
    last_preflight: {status: ready, checked_at: "2026-07-01T00:00:00Z"}
""",
            encoding="utf-8",
        )
        os.environ["BRICK_HOME"] = str(home)
        os.environ.pop("BRICK_PROVIDER_LADDER", None)
        try:
            yield
        finally:
            if previous_home is None:
                os.environ.pop("BRICK_HOME", None)
            else:
                os.environ["BRICK_HOME"] = previous_home
            if previous_ladder is None:
                os.environ.pop("BRICK_PROVIDER_LADDER", None)
            else:
                os.environ["BRICK_PROVIDER_LADDER"] = previous_ladder


def _uses_tier_preset(case: Mapping[str, Any]) -> bool:
    return str(case.get("chain_preset_ref") or "").strip() in _TIER_PRESET_REFS


def _split_ref_row(value: Any) -> list[str]:
    """One per-row expectation: a comma-joined ref string -> ordered ref list."""

    if not isinstance(value, str):
        raise ProfileError(
            f"per-row gate expectation must be a comma-joined string, got {value!r}"
        )
    return [part.strip() for part in value.split(",") if part.strip()]


def run_materialize_building_intent_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "materialize_building_intent_case")
    if not items:
        return 0
    from brick_protocol.support.operator.building_operation import materialize_building_intent
    from brick_protocol.support.operator.plan_graph import _linear_plan_from_graph_plan
    from brick_protocol.support.operator.plan_validation import validate_declared_building_plan
    from brick_protocol.support.operator.plan_validation import _task_source_ref_from_plan
    from brick_protocol.support.recording.declaration_packets import _write_declaration_work_evidence

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
        with _materialize_provider_registry_fixture(_uses_tier_preset(case)):
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
    objects_dir = repo / "brick_protocol" / "agent" / "objects"
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
    from brick_protocol.support.operator.building_operation import materialize_building_intent
    from brick_protocol.support.operator.plan_validation import _task_source_ref_from_plan
    from brick_protocol.support.recording.declaration_packets import _write_declaration_work_evidence

    count = 0
    for item in items:
        mapping = require_mapping(item, "materialize_building_intent_rejects item")
        case, relative = _profile_case_document(repo, mapping, "materialize_building_intent_rejects")
        expected_message = str(mapping.get("expected_message", "") or "")

        def _materialize_case() -> Mapping[str, Any]:
            with _materialize_provider_registry_fixture(_uses_tier_preset(case)):
                return materialize_building_intent(case, repo_root=repo)

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
                    _materialize_case()
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
                    _materialize_case()
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
                plan = dict(_materialize_case())
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
            _materialize_case()
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

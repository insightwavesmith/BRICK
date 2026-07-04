"""Compose-building behavioral profile runners.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    _profile_case_document,
    require_mapping,
    require_string_list,
    rule_items,
)
from support.checkers.lib.materialized_plan_observers import (
    _check_declaration_ref_expectations,
    _observed_link_row_values,
)
from support.checkers.lib.plan_fixture_helpers import (
    _compose_building_expected_codes,
    _compose_building_ok_callable,
    _compose_building_profile_plan,
    _optional_positive_int,
)
from support.checkers.lib.adapter_capability_checks import _fixture_gemini_api_key
from support.checkers.lib.preset_completion_fixture import _preset_completion_command_runner


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

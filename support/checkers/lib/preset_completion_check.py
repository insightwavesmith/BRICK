"""Preset completion behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.adapter_capability_checks import _fixture_gemini_api_key
from support.checkers.lib.checker_temp_vessel import _case_slug, _preset_slug
from support.checkers.lib.gate_evidence_readers import _assert_no_missing_gate_facts
from support.checkers.lib.plan_fixture_helpers import _optional_positive_int
from support.checkers.lib.preset_completion_fixture import _preset_completion_command_runner
from support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    require_string_list,
    rule_items,
)


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


from support.checkers.lib.case_runners import _canonical_chain_preset_refs

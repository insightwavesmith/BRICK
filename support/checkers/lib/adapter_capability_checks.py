"""Adapter-capability profile helper checks.

Pure support checker helpers relocated from case_runners.py by the FINAL
architecture conservation ledger. Function bodies below are byte-identical to
their original case_runners.py definitions.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from support.checkers.lib.preset_completion_fixture import (
    _preset_completion_command_runner,
    _preset_completion_prompt_from_cli_args,
    _return_labels_from_cli_prompt,
)
from support.checkers.lib.plan_fixture_helpers import (
    _case_slug,
    _graph_test_plan_from_linear,
    _validation_plan_for_declared_plan,
)
from support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    rule_items,
)


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


def _optional_non_negative_int(value: Any, label: str) -> int:
    text = str(value).strip()
    if not text.isdecimal():
        raise ProfileError(f"{label} must be a non-negative integer")
    return int(text)


def run_adapter_model_selection_case(repo: Path, profile: Mapping[str, Any]) -> int:
    items = rule_items(profile, "adapter_model_selection_case")
    if not items:
        return 0
    from brick_protocol.support.connection.adapter_model_casting import project_model_ref_to_cli_arg
    from brick_protocol.support.operator.provider_registry import resolve_model_alias_ref

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
        observed_cli_arg = project_model_ref_to_cli_arg(
            adapter_ref,
            resolve_model_alias_ref(adapter_ref, selected_model_ref),
        )
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
    from brick_protocol.support.operator.provider_registry import resolve_model_alias_ref

    count = 0
    for item in items:
        mapping = require_mapping(item, "adapter_model_selection_rejects item")
        adapter_ref = require_string(mapping.get("adapter_ref"), "adapter_model_selection_rejects.adapter_ref")
        selected_model_ref = require_string(
            mapping.get("selected_model_ref", ""),
            "adapter_model_selection_rejects.selected_model_ref",
        )
        try:
            project_model_ref_to_cli_arg(
                adapter_ref,
                resolve_model_alias_ref(adapter_ref, selected_model_ref),
            )
        except (TypeError, ValueError):
            count += 1
            continue
        raise ProfileError(
            "adapter_model_selection_rejects expected rejection but passed: "
            f"{adapter_ref}/{selected_model_ref}"
        )
    return count


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

    role = agent_object_ref.removeprefix("agent-object:")
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
        agent_instruction_packet={
            "kind": "agent-instruction-packet",
            "agent_object_ref": agent_object_ref,
            "role": role,
            "tool_policy_resources": _native_grant_policy_resources(tool_policy_refs),
        },
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
                "selected_adapter_ref": selected_adapter_ref,
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
                        "declared_gate_refs": ["link-gate:default-transition"],
                    },
                ],
            }
        ],
    }
    return _graph_test_plan_from_linear(linear_plan)


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
            # Smith 0623 LOCK: the request no longer raises -- it asserts the recorded fact.
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
        elif case_kind == "boundary_matrix_support_only":
            _check_adapter_capability_boundary_matrix_support_only(label)
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


def _check_adapter_capability_ok_all_four(label: str) -> None:
    from brick_protocol.support.connection.agent_adapter import adapter_capabilities
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope
    from support.operator.plan_validation import validate_declared_building_plan

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
    # REDO (Smith 0623 struct-surgery): an in-scope changed path must NOT be recorded
    # out-of-scope by the Brick comparison. (The written-vs-scope classification moved
    # to brick.comparison; write_observation raises nothing -- support is carry +
    # record only, the disposable worktree is the integrity boundary.)
    in_scope_facts = compare_changed_paths_to_write_scope(
        ["support/connection/agent_adapter.py"],
        write_scope,
    )
    if in_scope_facts.get("observed_paths_outside_declared_scope"):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: an in-scope changed "
            f"path was wrongly recorded out-of-scope, observed {in_scope_facts!r}"
        )


def _check_adapter_capability_claude_write_ok(label: str) -> None:
    from brick_protocol.support.connection.agent_adapter import (
        adapter_capabilities,
    )
    from brick_protocol.support.connection.adapter_constants import (
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
    if capabilities != ("read", "write", "web"):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: expected claude "
            f"read/write/web capabilities, observed {capabilities!r}"
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


def _assert_recorded_write_policy_fact(
    label: str,
    request: Any,
    expected_reason: str,
) -> None:
    # REDO (Smith 0623 struct-surgery): the request observer no longer raises and no
    # longer derives the reason-token facts inside the adapter. The ADAPTER exposes
    # the RAW effective-write request inputs (agent_request_effective_write_raw_inputs)
    # and SUPPORT/RECORDING derives the named write-policy facts
    # (derive_effective_write_request_facts). The probe asserts the request constructs
    # WITHOUT raising AND that the recording-derived fact carries the expected token.
    from brick_protocol.support.connection.agent_adapter import (
        agent_request_effective_write_raw_inputs,
    )
    from brick_protocol.support.recording.agent_step_observation import (
        derive_effective_write_request_facts,
    )

    facts = derive_effective_write_request_facts(
        **agent_request_effective_write_raw_inputs(request)
    )
    if not any(expected_reason in fact for fact in facts):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: expected "
            f"support/recording-derived write-policy fact carrying {expected_reason!r} "
            f"(move+record only; adapter raw -> recording derive), observed {facts!r}"
        )


def _check_adapter_capability_missing_agent_policy(label: str, expected_reason: str) -> None:
    request = _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        tool_policy_refs=(),
        write_scope=_adapter_capability_write_scope(),
    )
    _assert_recorded_write_policy_fact(label, request, expected_reason)


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
    # REDO (Smith 0623 struct-surgery): an out-of-scope changed path no longer STOPS
    # the building, and the written-vs-scope classification moved OUT of
    # support/operator/write_observation INTO the Brick axis
    # (brick.comparison.compare_changed_paths_to_write_scope). The probe asserts the
    # Brick comparison produces the recorded-fact bucket (and does NOT raise) for a
    # path outside the declared allowed_paths.
    from brick_protocol.brick.comparison import compare_changed_paths_to_write_scope

    write_scope = _adapter_capability_write_scope()
    facts = compare_changed_paths_to_write_scope(
        ["support/connection/agent_resources.py"],
        write_scope,
    )
    outside = facts.get("observed_paths_outside_declared_scope", [])
    if "support/connection/agent_resources.py" not in outside:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: an out-of-scope "
            "changed path must be RECORDED as observed_paths_outside_declared_scope "
            f"by brick.comparison (move+record only), observed {facts!r}"
        )

def _check_adapter_capability_poc_read_only_with_write_scope(
    label: str, expected_reason: str
) -> None:
    request = _adapter_capability_request(
        adapter_ref="adapter:local",
        write_scope=_adapter_capability_write_scope(),
    )
    _assert_recorded_write_policy_fact(label, request, expected_reason)


def _check_adapter_capability_legacy_identity_only(
    label: str, expected_reason: str
) -> None:
    request = _adapter_capability_request(
        adapter_ref="adapter:codex-local",
        agent_object_ref="agent-object:cto-lead",
        tool_policy_refs=("tool-policy:leader-coordination",),
        write_scope=_adapter_capability_write_scope(),
    )
    _assert_recorded_write_policy_fact(label, request, expected_reason)


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


def _native_grant_policy_resource(policy_ref: str) -> Mapping[str, Any]:
    if policy_ref == "tool-policy:leader-coordination":
        grant = {"schema": "native-grant/v1", "capabilities": ["read"]}
        semantic_classes = ["read"]
    elif policy_ref == "tool-policy:reviewer-readonly":
        grant = {"schema": "native-grant/v1", "capabilities": ["read"]}
        semantic_classes = ["read"]
    elif policy_ref == "tool-policy:read-write-scoped":
        grant = {
            "schema": "native-grant/v1",
            "capabilities": ["read", "write"],
            "write_mode": "runtime_intersection",
        }
        semantic_classes = [
            "read",
            "probe_write",
            "verification_write",
            "source_write",
            "artifact_write",
        ]
    elif policy_ref == "tool-policy:probe-write-scoped":
        grant = {
            "schema": "native-grant/v1",
            "capabilities": ["read", "write"],
            "write_mode": "runtime_intersection",
        }
        semantic_classes = [
            "read",
            "probe_write",
            "verification_write",
        ]
    elif policy_ref == "tool-policy:web-capable":
        grant = {
            "schema": "native-grant/v1",
            "capabilities": ["web"],
            "web_scope": "exfiltration_not_enforced",
            "exfiltration_enforced": False,
        }
        semantic_classes = ["read"]
    else:
        grant = {"schema": "native-grant/v1", "capabilities": ["unknown"]}
        semantic_classes = ["unknown"]
    return {
        "ref": policy_ref,
        "kind": "tool_policy",
        "path": f"agent/tool_policies/{policy_ref.removeprefix('tool-policy:')}.yaml",
        "data": {
            "tool_policy_ref": policy_ref,
            "owner_axis": "Agent",
            "semantic_capability_classes": semantic_classes,
            "native_grant": grant,
        },
    }


def _native_grant_policy_resources(policy_refs: tuple[str, ...]) -> list[Mapping[str, Any]]:
    return [_native_grant_policy_resource(policy_ref) for policy_ref in policy_refs]


def _check_adapter_capability_native_grant_roundtrip(label: str) -> None:
    from brick_protocol.support.connection import agent_resources

    refs = (
        "tool-policy:leader-coordination",
        "tool-policy:read-write-scoped",
        "tool-policy:web-capable",
    )
    native_grant_resources = _native_grant_policy_resources(refs)
    read_resolution = agent_resources.resolve_native_grant(
        native_grant_resources,
        tool_policy_refs=list(refs),
        write_need=False,
    )
    if read_resolution["capabilities"] != ["read", "web"]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: read-only Brick "
            f"must resolve read+web but no write, got {read_resolution['capabilities']!r}"
        )
    if read_resolution["semantic_capability_classes"] != ["read"]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: read-only Brick "
            "must resolve only semantic read, got "
            f"{read_resolution['semantic_capability_classes']!r}"
        )
    if read_resolution["declared_semantic_capability_classes"] != [
        "read",
        "probe_write",
        "verification_write",
        "source_write",
        "artifact_write",
    ]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: declared semantic "
            "classes drifted: "
            f"{read_resolution['declared_semantic_capability_classes']!r}"
        )
    write_resolution = agent_resources.resolve_native_grant(
        native_grant_resources,
        tool_policy_refs=list(refs),
        write_need=True,
    )
    if write_resolution["capabilities"] != ["read", "write", "web"]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: write-needed Brick "
            f"must resolve read+write+web, got {write_resolution['capabilities']!r}"
        )
    if write_resolution["semantic_capability_classes"] != [
        "read",
        "probe_write",
        "verification_write",
        "source_write",
        "artifact_write",
    ]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: write-needed Brick "
            "semantic classes drifted: "
            f"{write_resolution['semantic_capability_classes']!r}"
        )
    if agent_resources.codex_sandbox_mode_for_tool_policies(
        list(refs),
        write_need=False,
        native_grant_resources=native_grant_resources,
    ) != "read-only":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: codex read-only "
            "Brick did not stay read-only from native_grant"
        )
    if agent_resources.codex_sandbox_mode_for_tool_policies(
        list(refs),
        write_need=True,
        native_grant_resources=native_grant_resources,
    ) != "workspace-write":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: codex write-needed "
            "Brick did not project workspace-write from native_grant"
        )
    claude_read = agent_resources.claude_tools_for_tool_policies(
        list(refs),
        write_need=False,
        native_grant_resources=native_grant_resources,
    )
    if "WebFetch" not in claude_read["tools"] or "Edit" in claude_read["tools"]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: claude read/web "
            f"projection drifted: {claude_read['tools']!r}"
        )
    claude_write = agent_resources.claude_tools_for_tool_policies(
        list(refs),
        write_need=True,
        native_grant_resources=native_grant_resources,
    )
    if "WebFetch" not in claude_write["tools"] or "Edit" not in claude_write["tools"]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: claude write/web "
            f"projection drifted: {claude_write['tools']!r}"
        )


def _check_adapter_capability_native_grant_semantic_codex_gemini_parity(
    label: str,
) -> None:
    from brick_protocol.support.connection import adapter_grant_policy, adapter_local_cli
    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_constants

    expected_write_classes = [
        "read",
        "probe_write",
        "verification_write",
        "source_write",
        "artifact_write",
    ]
    adapter_refs = (
        adapter_constants.ADAPTER_CODEX_LOCAL,
        adapter_constants.ADAPTER_GEMINI_LOCAL,
    )

    read_resolutions: dict[str, Mapping[str, Any]] = {}
    write_resolutions: dict[str, Mapping[str, Any]] = {}
    write_prompts: dict[str, Mapping[str, Any]] = {}
    for adapter_ref in adapter_refs:
        read_request = _adapter_capability_request(
            adapter_ref=adapter_ref,
            write_scope=None,
        )
        write_request = _adapter_capability_request(
            adapter_ref=adapter_ref,
            write_scope=_adapter_capability_write_scope(),
        )
        read_resolutions[adapter_ref] = (
            adapter_grant_policy._native_grant_resolution_for_request(read_request)
        )
        write_resolutions[adapter_ref] = (
            adapter_grant_policy._native_grant_resolution_for_request(write_request)
        )
        write_prompts[adapter_ref] = json.loads(
            adapter_grant_policy._build_prompt(
                write_request,
                adapter._LOCAL_CLI_SPECS[adapter_ref],
            )
        )

    for adapter_ref, resolution in read_resolutions.items():
        if resolution.get("declared_semantic_capability_classes") != expected_write_classes:
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: {adapter_ref} "
                "read-only Brick lost declared semantic capability vocabulary; "
                f"observed {resolution.get('declared_semantic_capability_classes')!r}"
            )
        if resolution.get("semantic_capability_classes") != ["read"]:
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: {adapter_ref} "
                "read-only Brick must resolve only semantic read; observed "
                f"{resolution.get('semantic_capability_classes')!r}"
            )
        if resolution.get("write_effective") is not False:
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: {adapter_ref} "
                "read-only Brick resolved write_effective"
            )

    codex_write = write_resolutions[adapter_constants.ADAPTER_CODEX_LOCAL]
    gemini_write = write_resolutions[adapter_constants.ADAPTER_GEMINI_LOCAL]
    if codex_write.get("semantic_capability_classes") != expected_write_classes:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: codex-local write "
            "semantic classes drifted: "
            f"{codex_write.get('semantic_capability_classes')!r}"
        )
    if gemini_write.get("semantic_capability_classes") != expected_write_classes:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: gemini-local write "
            "semantic classes drifted: "
            f"{gemini_write.get('semantic_capability_classes')!r}"
        )
    if codex_write.get("semantic_capability_classes") != gemini_write.get(
        "semantic_capability_classes"
    ):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: codex-local and "
            "gemini-local semantic class vocabulary diverged"
        )

    codex_prompt_grant = write_prompts[adapter_constants.ADAPTER_CODEX_LOCAL].get(
        "native_grant",
        {},
    )
    gemini_prompt_grant = write_prompts[adapter_constants.ADAPTER_GEMINI_LOCAL].get(
        "native_grant",
        {},
    )
    for adapter_ref, prompt_grant in (
        (adapter_constants.ADAPTER_CODEX_LOCAL, codex_prompt_grant),
        (adapter_constants.ADAPTER_GEMINI_LOCAL, gemini_prompt_grant),
    ):
        if prompt_grant.get("semantic_capability_classes") != expected_write_classes:
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: {adapter_ref} "
                "prompt native_grant lost semantic class vocabulary: "
                f"{prompt_grant.get('semantic_capability_classes')!r}"
            )
        if prompt_grant.get("write_effective") is not True:
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: {adapter_ref} "
                "prompt native_grant did not carry write_effective"
            )

    codex_write_request = _adapter_capability_request(
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        write_scope=_adapter_capability_write_scope(),
    )
    if adapter_local_cli._codex_sandbox_for_request(codex_write_request) != "workspace-write":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: codex-local "
            "semantic write classes did not project workspace-write where supported"
        )
    gemini_write_request = _adapter_capability_request(
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        write_scope=_adapter_capability_write_scope(),
    )
    gemini_allow, gemini_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(
        gemini_write_request
    )
    for tool_name in ("write_file", "replace", "run_shell_command"):
        if tool_name not in gemini_allow or tool_name in gemini_deny:
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: gemini-local "
                "semantic write classes did not project provider-native write/probe "
                f"tool {tool_name!r}"
            )


def _check_adapter_capability_retired_gemini_api_no_write_or_probe(label: str) -> None:
    from brick_protocol.support.connection import agent_adapter as adapter
    from brick_protocol.support.connection import adapter_constants

    gemini_api = adapter_constants.ADAPTER_GEMINI_API
    if gemini_api in adapter_constants.ALLOWED_ADAPTER_REFS:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: retired gemini-api "
            "is admitted as an active adapter"
        )
    if gemini_api in adapter_constants._ADAPTER_CAPABILITIES:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: retired gemini-api "
            "still has capability table entries"
        )
    if gemini_api in adapter_constants._OBSERVED_WRITE_ADAPTER_REFS:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: retired gemini-api "
            "is still an observed-write adapter"
        )
    if gemini_api in adapter_constants.MODEL_PROVIDER_BY_ADAPTER:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: retired gemini-api "
            "still owns model/provider routing"
        )
    for probe_name, callback in (
        ("adapter_capabilities", lambda: adapter.adapter_capabilities(gemini_api)),
        (
            "adapter_is_write_capable",
            lambda: adapter.adapter_is_write_capable(gemini_api),
        ),
        (
            "adapter_has_write",
            lambda: adapter.adapter_has_capability(
                gemini_api,
                adapter_constants.ADAPTER_CAPABILITY_WRITE,
            ),
        ),
    ):
        try:
            callback()
        except ValueError as exc:
            if "adapter_ref is not admitted" not in str(exc):
                raise ProfileError(
                    f"adapter_capability_rehome_case rejected {label}: {probe_name} "
                    f"rejected retired gemini-api with wrong reason: {exc}"
                ) from exc
        else:
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: {probe_name} "
                "accepted retired gemini-api"
            )
    try:
        _adapter_capability_request(
            adapter_ref=gemini_api,
            write_scope=_adapter_capability_write_scope(),
        )
    except ValueError as exc:
        if "adapter_ref is not admitted" not in str(exc):
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: retired gemini-api "
                f"write/probe request rejected with wrong reason: {exc}"
            ) from exc
    else:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: retired gemini-api "
            "accepted a write/probe request"
        )


def _check_adapter_capability_checker_sweep_blocks_live_provider_cli(label: str) -> None:
    from brick_protocol.support.connection import adapter_local_cli
    from brick_protocol.support.connection import agent_adapter as adapter

    previous = os.environ.get("BRICK_CHECKER_PROFILE_SWEEP")
    os.environ["BRICK_CHECKER_PROFILE_SWEEP"] = "1"
    try:
        for adapter_ref, spec in adapter._LOCAL_CLI_SPECS.items():
            request = _adapter_capability_request(
                adapter_ref=adapter_ref,
                write_scope=None,
            )
            try:
                adapter_local_cli._invoke_local_cli(
                    spec,
                    request,
                    "checker fixture prompt",
                    cwd=Path.cwd(),
                    timeout_seconds=1,
                    command_runner=None,
                )
            except ValueError as exc:
                expected_label = adapter_ref.removeprefix("adapter:")
                message = str(exc)
                if (
                    "checker profile sweep must not invoke live" not in message
                    or expected_label not in message
                    or "command_runner" not in message
                ):
                    raise ProfileError(
                        f"adapter_capability_rehome_case rejected {label}: "
                        f"{adapter_ref} checker-sweep guard raised wrong reason: {exc}"
                    ) from exc
            except Exception as exc:
                raise ProfileError(
                    f"adapter_capability_rehome_case rejected {label}: {adapter_ref} "
                    "proceeded past the checker-sweep live-provider guard before "
                    f"failing with {type(exc).__name__}: {exc}"
                ) from exc
            else:
                raise ProfileError(
                    f"adapter_capability_rehome_case rejected {label}: {adapter_ref} "
                    "live provider CLI was not blocked during checker profile sweep"
                )
    finally:
        if previous is None:
            os.environ.pop("BRICK_CHECKER_PROFILE_SWEEP", None)
        else:
            os.environ["BRICK_CHECKER_PROFILE_SWEEP"] = previous


def _check_adapter_capability_native_grant_policy_only_fails_closed(label: str) -> None:
    from brick_protocol.support.connection import agent_resources

    refs = ("tool-policy:read-write-scoped",)
    if agent_resources.codex_sandbox_mode_for_tool_policies(
        list(refs),
        write_need=True,
    ) != "read-only":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: policy-ref-only "
            "codex projection must fail closed to read-only"
        )
    claude = agent_resources.claude_tools_for_tool_policies(
        list(refs),
        write_need=True,
    )
    if claude["tools"]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: policy-ref-only "
            f"claude projection must fail closed to no tools, got {claude['tools']!r}"
        )


def _check_adapter_capability_native_grant_write_home_pin(label: str) -> None:
    from brick_protocol.support.connection import agent_resources

    resource = _native_grant_policy_resource("tool-policy:leader-coordination")
    resource = dict(resource)
    data = dict(resource["data"])
    data["native_grant"] = {
        "schema": "native-grant/v1",
        "capabilities": ["read", "write"],
        "write_mode": "runtime_intersection",
    }
    resource["data"] = data
    agent_resources.resolve_native_grant(
        [resource],
        tool_policy_refs=["tool-policy:leader-coordination"],
        write_need=True,
    )


def _check_adapter_capability_native_grant_unknown_capability(label: str) -> None:
    from brick_protocol.support.connection import agent_resources

    resource = _native_grant_policy_resource("tool-policy:read-write-scoped")
    resource = dict(resource)
    data = dict(resource["data"])
    data["native_grant"] = {
        "schema": "native-grant/v1",
        "capabilities": ["read", "unknown"],
    }
    resource["data"] = data
    agent_resources.resolve_native_grant(
        [resource],
        tool_policy_refs=["tool-policy:read-write-scoped"],
        write_need=True,
    )


def _check_adapter_capability_boundary_matrix_support_only(label: str) -> None:
    from brick_protocol.support.connection import adapter_constants
    from brick_protocol.support.connection.agent_adapter import agent_request_effective_write

    rows = adapter_constants.adapter_boundary_matrix()
    refs = {str(row.get("adapter_ref") or "") for row in rows}
    if refs != set(adapter_constants.ALLOWED_ADAPTER_REFS):
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: boundary matrix "
            f"refs {sorted(refs)!r} did not match admitted refs "
            f"{sorted(adapter_constants.ALLOWED_ADAPTER_REFS)!r}"
        )
    for row in rows:
        adapter_ref = str(row.get("adapter_ref") or "")
        row_text = json.dumps(row, sort_keys=True)
        for required_key in (
            "boundary_strength",
            "credential_path_class",
            "write_boundary",
            "known_limits",
            "proof_limits",
            "not_proven",
        ):
            if required_key not in row:
                raise ProfileError(
                    f"adapter_capability_rehome_case rejected {label}: "
                    f"{adapter_ref} boundary row omitted {required_key}"
                )
        for authority_limit in (
            "adapter identity is not write authority",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ):
            if authority_limit not in row_text:
                raise ProfileError(
                    f"adapter_capability_rehome_case rejected {label}: "
                    f"{adapter_ref} boundary row lost proof limit {authority_limit!r}"
                )
        no_scope_request = _adapter_capability_request(
            adapter_ref=adapter_ref,
            write_scope=None,
        )
        if agent_request_effective_write(no_scope_request):
            raise ProfileError(
                f"adapter_capability_rehome_case rejected {label}: boundary matrix "
                f"adapter identity opened write without Brick write_scope: {adapter_ref}"
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

    native_grant_resources = _native_grant_policy_resources(_WRITE_CAPABLE_LEADER_POLICIES)
    sandbox = codex_sandbox_mode_for_tool_policies(
        list(_WRITE_CAPABLE_LEADER_POLICIES),
        write_need=False,
        native_grant_resources=native_grant_resources,
    )
    if sandbox != "read-only":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader on a read-only Brick (write_need=False) must project codex "
            f"sandbox_mode 'read-only', got {sandbox!r} (capability overrode the "
            "Brick NEED)"
        )
    claude = claude_tools_for_tool_policies(
        list(_WRITE_CAPABLE_LEADER_POLICIES),
        write_need=False,
        native_grant_resources=native_grant_resources,
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

    native_grant_resources = _native_grant_policy_resources(_WRITE_CAPABLE_LEADER_POLICIES)
    sandbox = codex_sandbox_mode_for_tool_policies(
        list(_WRITE_CAPABLE_LEADER_POLICIES),
        write_need=True,
        native_grant_resources=native_grant_resources,
    )
    if sandbox != "workspace-write":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: a write-capable "
            "leader on a write-needed Brick (write_need=True) must project codex "
            f"sandbox_mode 'workspace-write', got {sandbox!r} (over-restricted a "
            "legitimate write)"
        )
    claude = claude_tools_for_tool_policies(
        list(_WRITE_CAPABLE_LEADER_POLICIES),
        write_need=True,
        native_grant_resources=native_grant_resources,
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
    # The graph composer now stamps the template-owned write NEED on write-needed
    # rows. This case is the strict admission backstop for a malformed/smuggled
    # row, so remove the marker after composition to exercise that boundary.
    plan["brick_steps"][0]["rows"][0].pop("requires_brick_write_scope", None)

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
       claude invocation (normal acceptEdits plane, read-only browse tools
       Read/Grep/Glob, no Edit/Write/Bash -- CLAUDE-READ-FULL-ADAPTER-0624:
       a read-only Brick + tool-capable Agent browses read-only through the
       declared tool list, not provider plan mode); a request WITH
       the scope the marker-bearing row declares projects codex 'workspace-write'
       and a claude invocation including Edit + Write.
    """
    from brick_protocol.support.connection import adapter_local_cli
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
    observed_sandbox = adapter_local_cli._codex_sandbox_for_request(no_scope_codex)
    if observed_sandbox != "read-only":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: request WITHOUT "
            f"write_scope must project codex sandbox 'read-only', got {observed_sandbox!r}"
        )
    no_scope_claude_request = _adapter_capability_request(
        adapter_ref="adapter:claude-local",
        write_scope=None,
    )
    no_scope_claude = adapter_local_cli._claude_cli_invocation(no_scope_claude_request)
    # CLEAN-READTIER-0617: a read-only Brick (no write_scope) + a tool-capable
    # Agent (read-write-scoped policy) browses read-only through the normal
    # claude invocation plane (acceptEdits) with ONLY Read/Grep/Glob browse
    # tools, NEVER Edit/Write/Bash. YAML/tool-list projection is the control;
    # provider plan mode is not the read boundary.
    no_scope_tools = [
        tool.strip() for tool in str(no_scope_claude.get("tools", "")).split(",") if tool.strip()
    ]
    if no_scope_claude.get("permission_mode") != "acceptEdits" or no_scope_tools != ["Read", "Grep", "Glob"]:
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: request WITHOUT "
            "write_scope must project the read-only browse claude invocation "
            f"(acceptEdits, Read/Grep/Glob tools), got {no_scope_claude!r}"
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
    observed_sandbox = adapter_local_cli._codex_sandbox_for_request(scoped_codex)
    if observed_sandbox != "workspace-write":
        raise ProfileError(
            f"adapter_capability_rehome_case rejected {label}: request WITH the "
            "marker-bearing row's write_scope must project codex sandbox "
            f"'workspace-write', got {observed_sandbox!r}"
        )
    scoped_claude = adapter_local_cli._claude_cli_invocation(
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
    brick_row.pop("requires_brick_write_scope", None)
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
                    "declared_gate_refs": ["link-gate:default-transition"],
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

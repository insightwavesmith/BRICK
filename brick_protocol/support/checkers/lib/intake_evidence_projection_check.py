"""Intake evidence projection behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.adapter_capability_checks import _fixture_gemini_api_key
from brick_protocol.support.checkers.lib.checker_temp_vessel import (
    _case_slug,
    _temp_vessel_cleanup_or_reject,
    _with_temp_vessel_repo,
    _write_temp_vessel_sentinel,
)
from brick_protocol.support.checkers.lib.plan_fixture_helpers import _graph_test_plan_from_linear
from brick_protocol.support.checkers.lib.preset_completion_fixture import (
    _output_last_message_path,
    _preset_completion_command_runner,
)
from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    json_path_exists,
    require_mapping,
    require_string,
    rule_items,
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
    from brick_protocol.support.operator.building_operation import observe_building_frontier
    from brick_protocol.support.operator.driver import run_building_intake
    from brick_protocol.support.operator.ledger_projection import (
        project_orchestration_ledger_packet,
        render_project_orchestration_ledger_view,
    )
    from brick_protocol.support.operator.progress_projection import render_project_progress
    from brick_protocol.support.operator.project_creation import create_project

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
                    "allowed_paths": ["brick_protocol/support/operator/**"],
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
        from brick_protocol.support.operator.run import run_building_plan

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


from brick_protocol.support.checkers.lib.case_runners import (
    _assert_live_inbox_fixture_count_guard_red,
    _assert_live_inbox_fixture_count_unchanged,
    _live_inbox_fixture_packet_count,
    _vessel_case_require_json,
    _VESSEL_CASE_BUILDING_MAP_REQUIRED,
    _VESSEL_CASE_LEDGER_PACKET_REQUIRED,
    _VESSEL_CASE_LEDGER_ROW_REQUIRED,
    _VESSEL_CASE_STEP_OUTPUT_REQUIRED,
)

"""Chat-session PARK seam kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes chat-session park/claim/submit/resume evidence; it owns no axis
crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import fields
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.yaml_subset import KernelResult, ProfileError


def run_chat_session_park_seam(repo: Path) -> KernelResult:
    """Exercise the chat-session PARK/CLAIM/SUBMIT/RESUME seam over temp roots.

    This is support-checker evidence only. It proves the runner writes the
    support records, admits passive claim/submission, and resumes through the
    graph walker; it does not prove provider quality or reader behavior.
    """

    from support.checkers import check_building_lifecycle_path_shape as lifecycle_shape
    from support.checkers import check_package_path_admission as path_admission
    from support.operator import run as run_module
    from support.operator import (
        dashboard_export,
        frontier_observation,
        ledger_projection,
        progress_projection,
    )

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-chat-session-park-seam-") as tmpdir:
        temp_repo = Path(tmpdir) / "repo"
        buildings_root = temp_repo / "project" / "brick-protocol" / "buildings"
        buildings_root.mkdir(parents=True)
        _chat_session_write_temp_project_declaration(temp_repo)
        shutil.copytree(
            repo / "agent",
            temp_repo / "agent",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        _chat_session_assert_declared_adapter_capability(temp_repo)
        _chat_session_assert_undeclared_adapter_rejects(
            run_module,
            buildings_root=buildings_root,
            temp_repo=temp_repo,
        )
        inspected += 2
        _chat_session_assert_non_graph_plan_rejects(
            run_module,
            buildings_root=buildings_root,
            temp_repo=temp_repo,
        )
        inspected += 1
        dynamic_root, dynamic_written = _chat_session_drive_park(
            run_module,
            _chat_session_park_graph_plan(),
            buildings_root=buildings_root,
            temp_repo=temp_repo,
            label="dynamic",
        )
        no_claim_root, _no_claim_written = _chat_session_drive_park(
            run_module,
            _chat_session_park_graph_plan(building_id="chat-session-park-no-claim-case"),
            buildings_root=buildings_root,
            temp_repo=temp_repo,
            label="no-claim",
        )
        inspected += 2
        inspected += _chat_session_assert_park_evidence(
            dynamic_root,
            written_files=dynamic_written,
            temp_repo=temp_repo,
            label="dynamic",
        )
        inspected += _chat_session_assert_park_evidence(
            no_claim_root,
            written_files=_no_claim_written,
            temp_repo=temp_repo,
            label="no-claim",
        )

        _chat_session_assert_resume_rejects(
            run_module,
            no_claim_root,
            temp_repo=temp_repo,
            expected="parked building resume requires active chat-session claim",
            label="parked no claim",
        )
        claim = run_module.claim_chat_session_envelope(
            dynamic_root,
            lane_ref="lane:checker",
        )
        token = str(claim.get("claim_token") or "")
        if not re.fullmatch(r"[a-z]+(?:-[a-z]+){3,7}", token):
            raise ProfileError(f"chat_session_park_seam minted non-word token: {token!r}")
        from support.checkers.lib.agent_session_id_redaction_check import (
            _SESSION_ID_ULID_RE,
            _SESSION_ID_UUID_RE,
        )

        if _SESSION_ID_UUID_RE.search(token) or _SESSION_ID_ULID_RE.search(token):
            raise ProfileError(f"chat_session_park_seam minted session-shaped token: {token!r}")
        uuid_probe = _chat_session_probe_uuid_text()
        ulid_probe = _chat_session_probe_ulid_text()
        _chat_session_assert_second_claim_rejects(run_module, dynamic_root)
        _chat_session_assert_resume_rejects(
            run_module,
            dynamic_root,
            temp_repo=temp_repo,
            expected="parked building resume requires chat-session submission",
            label="claim no submission",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={"secret": "done", "observed_evidence": ["bad"]},
            expected="forbidden key 'secret'",
            label="forbidden secret key",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token="amber-basil-cedar-copper" if token != "amber-basil-cedar-copper" else "amber-basil-cedar-delta",
            returned={
                "made_changes": ["wrong token"],
                "observed_evidence": ["wrong token"],
                "not_proven": ["not resumed"],
            },
            expected="claim_token does not match",
            label="token mismatch",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                "made_changes": ["uuid negative"],
                "observed_evidence": [uuid_probe],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="uuid-shaped submitted text",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                uuid_probe: "session-shaped key must be rejected",
                "made_changes": ["uuid key negative"],
                "observed_evidence": ["ordinary value"],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="uuid-shaped submitted key",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                ulid_probe: "session-shaped key must be rejected",
                "made_changes": ["ulid key negative"],
                "observed_evidence": ["ordinary value"],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="ulid-shaped submitted key",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                "made_changes": ["nested key negative"],
                "observed_evidence": [{"outer": [{"ordinary": "value"}, {uuid_probe: "blocked"}]}],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="nested submitted key",
        )
        _chat_session_assert_submit_rejects(
            run_module,
            dynamic_root,
            token=token,
            returned={
                "made_changes": ["nested value negative"],
                "observed_evidence": [{"outer": ["ordinary", {"inner": ulid_probe}]}],
                "not_proven": ["not resumed"],
            },
            expected="session-id-shaped text",
            label="nested submitted value",
        )
        for key in ("status", "result", "success", "movement", "target", "verdict"):
            _chat_session_assert_submit_rejects(
                run_module,
                dynamic_root,
                token=token,
                returned={
                    "made_changes": [f"top-level {key} negative"],
                    "observed_evidence": ["ordinary evidence"],
                    "not_proven": ["not resumed"],
                    key: "blocked top-level AgentFact return key",
                },
                expected=f"forbidden key '{key}'",
                label=f"top-level returned {key}",
            )
        _chat_session_assert_envelope_session_key_rejects(uuid_probe)
        fire_buildings_root = temp_repo / "project" / "brick-protocol" / "chat-session-fire-buildings"
        fire_buildings_root.mkdir(parents=True)
        _chat_session_assert_key_scan_fire(
            run_module,
            buildings_root=fire_buildings_root,
            temp_repo=temp_repo,
            uuid_probe=uuid_probe,
        )
        submitted = run_module.submit_chat_session_return(
            dynamic_root,
            claim_token=token,
            returned={
                "made_changes": ["checker wrote passive submission"],
                "observed_evidence": [
                    {
                        "status": "nested evidence field accepted",
                        "detail": "claim token matched and payload stayed passive",
                    }
                ],
                "evidence": {"result": "nested evidence object accepted"},
                "task-source": "ordinary hyphenated key accepted",
                "not_proven": ["provider quality", "semantic correctness"],
            },
        )
        if submitted.get("returned", {}).get("observed_evidence") != [
            {
                "status": "nested evidence field accepted",
                "detail": "claim token matched and payload stayed passive",
            }
        ]:
            raise ProfileError("chat_session_park_seam submission returned payload drifted")
        if submitted.get("returned", {}).get("evidence") != {
            "result": "nested evidence object accepted"
        }:
            raise ProfileError("chat_session_park_seam nested evidence result payload drifted")
        before_resume = frontier_observation.observe_building_frontier(
            dynamic_root,
            repo_root=temp_repo,
        )
        if before_resume.get("frontier_kind") != "chat_session_parked":
            raise ProfileError(
                "chat_session_park_seam passive submission triggered frontier movement: "
                f"{before_resume.get('frontier_kind')!r}"
            )
        if (dynamic_root / "raw" / "agent-return.jsonl").exists():
            raise ProfileError("chat_session_park_seam passive submission wrote agent-return evidence")
        original_runner_repo = run_module._REPO_ROOT
        try:
            run_module._REPO_ROOT = temp_repo
            resumed = run_module.resume_building_plan(dynamic_root, overwrite_existing=True)
        finally:
            run_module._REPO_ROOT = original_runner_repo
        if len(resumed.step_results) != 2:
            raise ProfileError(
                "chat_session_park_seam expected resumed graph to close chat step plus "
                f"follow-up step, observed {len(resumed.step_results)}"
            )
        if resumed.step_results[0].adapter_result.returned_value != submitted.get("returned"):
            raise ProfileError("chat_session_park_seam chat step did not consume submitted return")
        if resumed.step_results[1].adapter_result.request.adapter_ref != "adapter:local":
            raise ProfileError("chat_session_park_seam follow-up step did not run live adapter:local")
        after_resume = frontier_observation.observe_building_frontier(
            dynamic_root,
            repo_root=temp_repo,
        )
        if after_resume.get("frontier_kind") != "complete":
            raise ProfileError(
                "chat_session_park_seam resumed Building did not observe complete frontier: "
                f"{after_resume.get('frontier_kind')!r}"
            )
        inspected += 23

        paths = lifecycle_shape.collect_directory_paths(buildings_root)
        lifecycle_violations = _chat_session_lifecycle_violations(buildings_root)
        if lifecycle_violations:
            raise ProfileError(
                "chat_session_park_seam lifecycle checker rejected generated evidence:\n"
                + "\n".join(f"- {violation}" for violation in lifecycle_violations)
            )
        path_violations = path_admission.check_paths(paths)
        if path_violations:
            raise ProfileError(
                "chat_session_park_seam package path admission rejected generated evidence:\n"
                + "\n".join(f"- {violation}" for violation in path_violations)
            )
        inspected += len(paths)

        board_state = ledger_projection._project_ledger_board_state("chat_session_parked")
        if board_state != "waiting_review":
            raise ProfileError(
                "chat_session_park_seam ledger board_state mapping is not the closed "
                f"waiting-review family: {board_state!r}"
            )
        dashboard = dashboard_export.dashboard_export_packet(repo_root=temp_repo)
        parked_dashboard_rows = [
            row
            for row in dashboard.get("buildings", [])
            if isinstance(row, Mapping) and row.get("frontier") == "chat_session_parked"
        ]
        if len(parked_dashboard_rows) != 1:
            raise ProfileError(
                "chat_session_park_seam dashboard_export did not project the remaining parked "
                f"Buildings, observed {len(parked_dashboard_rows)}"
            )
        for row in parked_dashboard_rows:
            if row.get("state") != "waiting_review" or row.get("disp") != "review":
                raise ProfileError(
                    "chat_session_park_seam dashboard_export did not show parked "
                    f"Building in review/waiting family: state={row.get('state')!r} "
                    f"disp={row.get('disp')!r}"
                )
        progress = progress_projection.render_project_progress(
            "project:brick-protocol",
            repo_root=temp_repo,
        )
        if "- waiting_review: 1" not in progress:
            raise ProfileError(
                "chat_session_park_seam PROGRESS projection did not count parked "
                "Buildings under waiting_review"
            )
        inspected += 3

        _chat_session_assert_mutated_lifecycle_rejects(
            no_claim_root,
            "envelope session-like identifier",
            lambda root: _chat_session_mutate_envelope_uuid(root),
        )
        _chat_session_assert_mutated_lifecycle_rejects(
            no_claim_root,
            "adapter-error-shaped park record",
            lambda root: _chat_session_mutate_park_as_adapter_error(root),
        )
        _chat_session_assert_mutated_lifecycle_rejects(
            no_claim_root,
            "missing work-envelope path",
            lambda root: _chat_session_delete_work_envelope(root),
        )
        _chat_session_assert_mutated_lifecycle_rejects(
            dynamic_root,
            "submission forbidden returned key",
            lambda root: _chat_session_mutate_submission_forbidden_key(root),
        )
        _chat_session_assert_mutated_lifecycle_rejects(
            dynamic_root,
            "submission token mismatch",
            lambda root: _chat_session_mutate_submission_token(root),
        )
        inspected += 5

    return KernelResult(
        check_id="chat_session_park_seam",
        inspected=inspected,
        output=(
            "chat-session S2/S3 seam passed: non-graph plans rejected by the "
            "dynamic graph walker guard, "
            "dynamic graph park wrote work-envelope.json + parked.json + raw park evidence, "
            "atomic claim minted a word-form token and second claim rejected, no-claim/"
            "no-submission/token-mismatch/forbidden-key/top-level AgentFact verdict "
            "key/session-id value/key/nested submissions and session-shaped envelope "
            "keys rejected before resume, passive submission preserved nested evidence "
            "status/result fields without computing gates, resume consumed "
            "the submitted return, replayed through the graph walker, ran the next "
            "adapter:local step, lifecycle/path checks accepted claim.json and "
            "submission.json, dashboard/PROGRESS kept only the unsubmitted parked "
            "Building in waiting_review, and mutated claim/submission/path negatives fired RED."
        ),
    )


def _chat_session_park_plan() -> Mapping[str, Any]:
    return {
        "plan_ref": "building-plan:chat-session-park-seam-case",
        "owner_axis": "Brick",
        "building_id": "chat-session-park-seam-case",
        "plan_shape": "linear",
        "selected_adapter_ref": "adapter:chat-session",
        "report_event_policy": {
            "enabled": True,
            "grain": "building",
            "event_kinds": ["building_started", "intervention_required"],
            "sink_refs": ["report-sink:local-inbox", "report-sink:operator-wake-local"],
        },
        "steps": [
            {
                "step_ref": "chat-session-park-work",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:chat-session-park-work",
                        "brick_work_ref": "work:chat-session-park-work",
                        "brick_instance_ref": "brick-chat-session-park-work",
                        "work_statement": "Exercise chat-session S1 park seam.",
                        "comparison_rule": "Support observes parked evidence shape only.",
                        "required_return_shape": "made_changes, observed_evidence, not_proven",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:chat-session-park-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                    {
                        "axis": "Link",
                        "row_ref": "link-row:chat-session-park-work",
                        "movement": "forward",
                        "target_ref": "brick-chat-session-park-closure",
                        "declared_gate_refs": ["link-gate:default-transition"],
                    },
                ],
            }
        ],
    }


def _chat_session_park_graph_plan(
    *,
    building_id: str = "chat-session-park-seam-dynamic-case",
) -> Mapping[str, Any]:
    return {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "graph",
        "report_event_policy": {
            "enabled": True,
            "grain": "building",
            "event_kinds": ["building_started", "intervention_required"],
            "sink_refs": ["report-sink:local-inbox", "report-sink:operator-wake-local"],
        },
        "execution_order": ["chat-session-park-dynamic-work", "chat-session-followup-work"],
        "brick_steps": [
            {
                "step_ref": "chat-session-park-dynamic-work",
                "selected_adapter_ref": "adapter:chat-session",
                "completion_edge_ref": "edge:chat-session-park-dynamic-work-to-followup",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:chat-session-park-dynamic-work",
                        "brick_work_ref": "work:chat-session-park-dynamic-work",
                        "brick_instance_ref": "brick-chat-session-park-dynamic-work",
                        "work_statement": "Exercise chat-session S1 park seam on the dynamic graph walker.",
                        "comparison_rule": "Support observes parked evidence shape only.",
                        "required_return_shape": "made_changes, observed_evidence, not_proven",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:chat-session-park-dynamic-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                ],
            },
            {
                "step_ref": "chat-session-followup-work",
                "selected_adapter_ref": "adapter:local",
                "completion_edge_ref": "edge:chat-session-followup-work-to-boundary",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:chat-session-followup-work",
                        "brick_work_ref": "work:chat-session-followup-work",
                        "brick_instance_ref": "brick-chat-session-followup-work",
                        "work_statement": "Exercise live follow-up after chat-session submission.",
                        "comparison_rule": "Support observes follow-up invocation only.",
                        "required_return_shape": "returned_summary, adapter_ref",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:chat-session-followup-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                ],
            }
        ],
        "link_edges": [
            {
                "edge_ref": "edge:chat-session-park-dynamic-work-to-followup",
                "source_step_ref": "chat-session-park-dynamic-work",
                "target_step_ref": "chat-session-followup-work",
                "rows": [
                    {
                        "axis": "Link",
                        "row_ref": "link-row:chat-session-park-dynamic-work",
                        "movement": "forward",
                        "target_ref": "brick-chat-session-followup-work",
                        "declared_gate_refs": ["link-gate:default-transition"],
                    }
                ],
            },
            {
                "edge_ref": "edge:chat-session-followup-work-to-boundary",
                "source_step_ref": "chat-session-followup-work",
                "rows": [
                    {
                        "axis": "Link",
                        "row_ref": "link-row:chat-session-followup-work",
                        "movement": "forward",
                        "target_ref": "building-boundary:chat-session-park-dynamic-closed",
                        "declared_gate_refs": ["link-gate:default-transition"],
                    }
                ],
            }
        ],
    }


def _chat_session_assert_declared_adapter_capability(temp_repo: Path) -> None:
    dev = _chat_session_agent_object(temp_repo, "dev")
    qa = _chat_session_agent_object(temp_repo, "qa")
    if "adapter:chat-session" not in dev.get("adapter_refs", []):
        raise ProfileError(
            "chat_session_park_seam expected agent/objects/dev.yaml to declare "
            "adapter:chat-session"
        )
    if "adapter:chat-session" in qa.get("adapter_refs", []):
        raise ProfileError(
            "chat_session_park_seam expected undeclared negative-control "
            "agent/objects/qa.yaml to omit adapter:chat-session"
        )


def _chat_session_agent_object(temp_repo: Path, object_name: str) -> Mapping[str, Any]:
    path = temp_repo / "agent" / "objects" / f"{object_name}.yaml"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"chat_session_park_seam failed to read Agent Object {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ProfileError(f"chat_session_park_seam expected mapping Agent Object at {path}")
    return value


def _chat_session_assert_undeclared_adapter_rejects(
    run_module: Any,
    *,
    buildings_root: Path,
    temp_repo: Path,
) -> None:
    plan = _chat_session_plan_with_agent(
        "agent-object:qa",
        building_id="chat-session-park-undeclared-agent-case",
    )
    original_runner_repo = run_module._REPO_ROOT
    try:
        run_module._REPO_ROOT = temp_repo
        try:
            run_module.run_building_plan(
                plan,
                output_root=buildings_root,
                overwrite_existing=True,
            )
        except run_module.ChatSessionParkFrontierEvidenceWritten as exc:
            raise ProfileError(
                "chat_session_park_seam undeclared Agent Object parked instead "
                f"of rejecting adapter admission: {exc}"
            ) from exc
        except ValueError as exc:
            if "selected adapter must be referenced by Agent Object" not in str(exc):
                raise ProfileError(
                    "chat_session_park_seam undeclared Agent Object rejected with "
                    f"the wrong reason: {exc}"
                ) from exc
            root = buildings_root / "chat-session-park-undeclared-agent-case"
            if (root / "raw" / "chat-session-park.jsonl").exists() or any(
                path.is_file()
                for path in (root / "work" / "step-outputs").glob("*/parked.json")
            ):
                raise ProfileError(
                    "chat_session_park_seam undeclared Agent Object wrote park evidence "
                    "after adapter admission rejected"
                )
            if root.exists():
                shutil.rmtree(root)
            return
        except Exception as exc:  # noqa: BLE001 - checker reports unexpected leak type
            raise ProfileError(
                "chat_session_park_seam undeclared Agent Object should fail closed "
                f"with ValueError, observed {type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError(
            "chat_session_park_seam undeclared Agent Object with selected "
            "adapter:chat-session returned normally instead of rejecting"
        )
    finally:
        run_module._REPO_ROOT = original_runner_repo


def _chat_session_assert_non_graph_plan_rejects(
    run_module: Any,
    *,
    buildings_root: Path,
    temp_repo: Path,
) -> None:
    original_runner_repo = run_module._REPO_ROOT
    try:
        run_module._REPO_ROOT = temp_repo
        try:
            run_module.run_building_plan(
                _chat_session_park_plan(),
                output_root=buildings_root,
                overwrite_existing=True,
            )
        except ValueError as exc:
            if "walker_mode='dynamic' requires a plan_shape: graph Building Plan" not in str(exc):
                raise ProfileError(
                    "chat_session_park_seam non-graph dynamic guard had wrong reason: "
                    f"{exc}"
                ) from exc
            return
        except Exception as exc:  # noqa: BLE001
            raise ProfileError(
                "chat_session_park_seam non-graph dynamic guard expected ValueError, "
                f"observed {type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError("chat_session_park_seam non-graph plan did not reject")
    finally:
        run_module._REPO_ROOT = original_runner_repo


def _chat_session_plan_with_agent(agent_object_ref: str, *, building_id: str) -> Mapping[str, Any]:
    plan = json.loads(json.dumps(_chat_session_park_graph_plan(building_id=building_id)))
    plan["building_id"] = building_id
    plan["plan_ref"] = f"building-plan:{building_id}"
    step = plan["brick_steps"][0]
    step["step_ref"] = f"{building_id}-work"
    for row in step["rows"]:
        if row.get("axis") == "Agent":
            row["agent_object_ref"] = agent_object_ref
            row["row_ref"] = f"agent-row:{building_id}-work"
        elif row.get("axis") == "Brick":
            row["row_ref"] = f"brick-row:{building_id}-work"
            row["brick_work_ref"] = f"work:{building_id}-work"
            row["brick_instance_ref"] = f"brick-{building_id}-work"
    plan["execution_order"][0] = step["step_ref"]
    plan["link_edges"][0]["source_step_ref"] = step["step_ref"]
    plan["link_edges"][0]["rows"][0]["row_ref"] = f"link-row:{building_id}-work"
    return plan


def _chat_session_write_temp_project_declaration(temp_repo: Path) -> None:
    project_root = temp_repo / "project" / "brick-protocol"
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "README.md").write_text(
        "# Temp Brick Protocol Project\n\nChecker fixture project declaration.\n",
        encoding="utf-8",
    )
    (project_root / "project.json").write_text(
        json.dumps(
            {
                "project_ref": "project:brick-protocol",
                "label": "Temp Brick Protocol",
                "direction": "Exercise chat-session park projection seams.",
                "done_means": "Checker fixture reaches its closed evidence assertions.",
                "out_of_scope": "External delivery and provider liveness.",
                "managers": ["smith"],
                "declared_by": "smith",
                "declared_at": "2026-06-11T00:00:00+00:00",
                "charter_ref": "project/brick-protocol/README.md",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _chat_session_drive_park(
    run_module: Any,
    plan: Mapping[str, Any],
    *,
    buildings_root: Path,
    temp_repo: Path,
    label: str,
) -> tuple[Path, tuple[str, ...]]:
    original_runner_repo = run_module._REPO_ROOT
    try:
        run_module._REPO_ROOT = temp_repo
        try:
            run_module.run_building_plan(
                plan,
                output_root=buildings_root,
                overwrite_existing=True,
            )
        except run_module.ChatSessionParkFrontierEvidenceWritten as exc:
            return Path(exc.building_root), tuple(str(path) for path in exc.written_files)
        except Exception as exc:  # noqa: BLE001 - assert typed park frontier
            raise ProfileError(
                f"chat_session_park_seam {label} path expected typed "
                "ChatSessionParkFrontierEvidenceWritten, but leaked "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError(
            f"chat_session_park_seam {label} path expected the runner to stop with "
            "ChatSessionParkFrontierEvidenceWritten, but it returned normally"
        )
    finally:
        run_module._REPO_ROOT = original_runner_repo


def _chat_session_assert_second_claim_rejects(run_module: Any, building_root: Path) -> None:
    try:
        run_module.claim_chat_session_envelope(building_root, lane_ref="lane:second-checker")
    except FileExistsError as exc:
        if "already claimed" not in str(exc):
            raise ProfileError(
                "chat_session_park_seam second claim rejected with wrong reason: "
                f"{exc}"
            ) from exc
        return
    raise ProfileError("chat_session_park_seam second claim did not reject")


def _chat_session_probe_uuid_text() -> str:
    return "-".join(("123e4567", "e89b", "42d3", "a456", "426614174000"))


def _chat_session_probe_ulid_text() -> str:
    return "".join(("01ARZ3", "NDEK", "TSV4", "RRFF", "Q69G", "5FAV"))


def _chat_session_assert_envelope_session_key_rejects(uuid_probe: str) -> None:
    from brick_protocol.support.connection.agent_adapter import AgentAdapterRequest
    from support.recording import adapter_error_frontier

    request = AgentAdapterRequest(
        building_id="chat-session-envelope-key-case",
        agent_object_ref="agent-object:dev",
        adapter_ref="adapter:chat-session",
        brick_instance_ref="brick-chat-session-envelope-key-case",
        next_brick_instance_ref="building-boundary:chat-session-envelope-key-case",
        source_fact_bodies={uuid_probe: "ordinary body"},
    )
    try:
        adapter_error_frontier._agent_adapter_request_work_envelope(request)
    except ValueError as exc:
        if "session-id-shaped text" not in str(exc):
            raise ProfileError(
                "chat_session_park_seam envelope session-key rejected with wrong reason: "
                f"{exc}"
            ) from exc
        return
    raise ProfileError("chat_session_park_seam envelope session-shaped key did not reject")


def _chat_session_assert_key_scan_fire(
    run_module: Any,
    *,
    buildings_root: Path,
    temp_repo: Path,
    uuid_probe: str,
) -> None:
    fire_root, _ = _chat_session_drive_park(
        run_module,
        _chat_session_park_graph_plan(building_id="chat-session-key-scan-fire-case"),
        buildings_root=buildings_root,
        temp_repo=temp_repo,
        label="key-scan-fire",
    )
    claim = run_module.claim_chat_session_envelope(
        fire_root,
        lane_ref="lane:key-scan-fire-checker",
    )
    token = str(claim.get("claim_token") or "")
    # The chat-session key-scan lives wherever submit_chat_session_return is
    # DEFINED (S11 relocated it run.py -> run_chat_session.py). Patch the rejector
    # binding on that module so the FIRE mutation reaches the live call path; run's
    # facade re-export points at the same function, so .__module__ tracks the home.
    submit_module = sys.modules[run_module.submit_chat_session_return.__module__]
    original_rejector = submit_module._reject_session_like_text
    submit_module._reject_session_like_text = _chat_session_value_only_session_rejector
    try:
        try:
            run_module.submit_chat_session_return(
                fire_root,
                claim_token=token,
                returned={
                    uuid_probe: "mutated key-skip walker would admit this",
                    "made_changes": ["key-skip FIRE"],
                    "observed_evidence": ["ordinary value"],
                    "not_proven": ["not resumed"],
                },
            )
        except ValueError as exc:
            raise ProfileError(
                "chat_session_park_seam FIRE did not expose key-skip mutation: "
                f"{exc}"
            ) from exc
    finally:
        submit_module._reject_session_like_text = original_rejector


def _chat_session_value_only_session_rejector(label: str, value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _chat_session_value_only_session_rejector(f"{label}.{key}", child)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _chat_session_value_only_session_rejector(f"{label}[{index}]", child)
        return
    if isinstance(value, str):
        from support.checkers.lib.agent_session_id_redaction_check import (
            _SESSION_ID_ULID_RE,
            _SESSION_ID_UUID_RE,
        )

        if _SESSION_ID_UUID_RE.search(value) or _SESSION_ID_ULID_RE.search(value):
            raise ValueError(f"{label} contains session-id-shaped text")
        return


def _chat_session_assert_submit_rejects(
    run_module: Any,
    building_root: Path,
    *,
    token: str,
    returned: Mapping[str, Any],
    expected: str,
    label: str,
) -> None:
    before = (building_root / "work" / "step-outputs")
    submission_count = len(list(before.glob("*/submission.json")))
    try:
        run_module.submit_chat_session_return(
            building_root,
            claim_token=token,
            returned=returned,
        )
    except ValueError as exc:
        if expected not in str(exc):
            raise ProfileError(
                f"chat_session_park_seam {label} rejected with wrong reason: {exc}"
            ) from exc
        after_count = len(list(before.glob("*/submission.json")))
        if after_count != submission_count:
            raise ProfileError(
                f"chat_session_park_seam {label} wrote submission evidence after reject"
            )
        return
    raise ProfileError(f"chat_session_park_seam {label} submit did not reject")


def _chat_session_assert_resume_rejects(
    run_module: Any,
    building_root: Path,
    *,
    temp_repo: Path,
    expected: str,
    label: str,
) -> None:
    original_runner_repo = run_module._REPO_ROOT
    try:
        run_module._REPO_ROOT = temp_repo
        try:
            run_module.resume_building_plan(building_root, overwrite_existing=True)
        except ValueError as exc:
            if expected not in str(exc):
                raise ProfileError(
                    f"chat_session_park_seam {label} resume rejected with wrong reason: {exc}"
                ) from exc
            return
        except Exception as exc:  # noqa: BLE001
            raise ProfileError(
                f"chat_session_park_seam {label} resume expected ValueError, "
                f"observed {type(exc).__name__}: {exc}"
            ) from exc
        raise ProfileError(f"chat_session_park_seam {label} resume did not reject")
    finally:
        run_module._REPO_ROOT = original_runner_repo


def _chat_session_assert_park_evidence(
    building_root: Path,
    *,
    written_files: tuple[str, ...],
    temp_repo: Path,
    label: str,
) -> int:
    from brick_protocol.support.connection.agent_adapter import AgentAdapterRequest
    from support.checkers import check_building_declaration_integrity as declaration_integrity
    from support.operator.frontier_observation import observe_building_frontier
    from support.operator.reporter import (
        OPERATOR_WAKE_LOCAL_SINK_REF,
        building_event_kind_from_frontier,
        render_report_packet,
    )

    if not building_root.is_dir():
        raise ProfileError(f"chat_session_park_seam {label} path did not create a Building root")
    if not written_files:
        raise ProfileError(f"chat_session_park_seam {label} path reported no written evidence files")

    step_dir = _chat_session_single_step_output_dir(building_root)
    envelope_path = step_dir / "work-envelope.json"
    parked_path = step_dir / "parked.json"
    raw_park_path = building_root / "raw" / "chat-session-park.jsonl"
    raw_agent_return_path = building_root / "raw" / "agent-return.jsonl"
    raw_adapter_error_path = building_root / "raw" / "adapter-error.jsonl"
    for required in (envelope_path, parked_path, raw_park_path):
        if not required.is_file():
            raise ProfileError(f"chat_session_park_seam {label} path missing required file: {required}")
    for rel in declaration_integrity.DECLARATION_CHAIN_ARTIFACTS:
        artifact = building_root / Path(*rel)
        if not artifact.is_file():
            raise ProfileError(
                f"chat_session_park_seam {label} path declaration evidence "
                f"lacks required chain artifact {artifact.relative_to(building_root)}"
            )
    if raw_agent_return_path.exists():
        raise ProfileError(f"chat_session_park_seam {label} path fabricated raw/agent-return.jsonl")
    if raw_adapter_error_path.exists():
        raise ProfileError(
            f"chat_session_park_seam {label} path wrote adapter-error raw evidence for a park"
        )

    envelope = _chat_session_json_object(envelope_path)
    parked = _chat_session_json_object(parked_path)
    expected_envelope_keys = {field.name for field in fields(AgentAdapterRequest)}
    observed_envelope_keys = set(envelope)
    if observed_envelope_keys != expected_envelope_keys:
        raise ProfileError(
            f"chat_session_park_seam {label} path work envelope keys drifted: "
            f"missing={sorted(expected_envelope_keys - observed_envelope_keys)} "
            f"unexpected={sorted(observed_envelope_keys - expected_envelope_keys)}"
        )
    if envelope.get("adapter_ref") != "adapter:chat-session":
        raise ProfileError(
            f"chat_session_park_seam {label} path work envelope did not preserve adapter:chat-session"
        )
    if parked.get("kind") != "chat_session_park_record":
        raise ProfileError(f"chat_session_park_seam {label} path parked.json has the wrong kind")
    if parked.get("schema_version") != "chat-session-park-record-0":
        raise ProfileError(
            f"chat_session_park_seam {label} path parked.json has the wrong schema version"
        )
    if "adapter_error_ref" in parked or "agent_fact_created" in parked:
        raise ProfileError(
            f"chat_session_park_seam {label} path parked.json reused adapter-error shape keys"
        )
    if parked.get("work_envelope_ref") == parked.get("parked_ref"):
        raise ProfileError(
            f"chat_session_park_seam {label} path parked ref and envelope ref are not distinct"
        )
    building_map = _chat_session_json_object(building_root / "work" / "building-map.json")
    provenance = building_map.get("declaration_provenance")
    if not isinstance(provenance, Mapping):
        raise ProfileError(
            f"chat_session_park_seam {label} path building-map lacks declaration_provenance"
        )
    if provenance.get("building_id") != building_root.name:
        raise ProfileError(
            f"chat_session_park_seam {label} path declaration_provenance names wrong Building"
        )
    proof_limits = provenance.get("proof_limits")
    if not isinstance(proof_limits, list) or "not Movement authority" not in proof_limits:
        raise ProfileError(
            f"chat_session_park_seam {label} path declaration_provenance lacks support proof limits"
        )

    link_records = [
        json.loads(line)
        for line in (building_root / "raw" / "link.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    park_frontiers = [
        record
        for record in link_records
        if isinstance(record, Mapping) and record.get("frontier_kind") == "chat_session_parked"
    ]
    if not park_frontiers:
        raise ProfileError(
            f"chat_session_park_seam {label} path did not write a chat_session_parked Link frontier row"
        )
    latest_park = park_frontiers[-1]
    if latest_park.get("transition_lifecycle_state") != "paused":
        raise ProfileError(
            f"chat_session_park_seam {label} path did not carry a paused lifecycle row"
        )
    if not latest_park.get("transition_lifecycle_paused_at_ref"):
        raise ProfileError(
            f"chat_session_park_seam {label} path lifecycle row is not hold-addressable"
        )
    if latest_park.get("transition_lifecycle_required_disposition_owner") != "caller-or-coo":
        raise ProfileError(
            f"chat_session_park_seam {label} path lifecycle row has wrong disposition owner"
        )

    frontier = observe_building_frontier(building_root, repo_root=temp_repo)
    if frontier.get("frontier_kind") != "chat_session_parked":
        raise ProfileError(
            f"chat_session_park_seam {label} path frontier branch did not win before incomplete: "
            f"{frontier.get('frontier_kind')!r}"
        )
    event_kind = building_event_kind_from_frontier(building_root, repo_root=temp_repo)
    if event_kind != "intervention_required":
        raise ProfileError(
            f"chat_session_park_seam {label} path reporter event mapping did not ring the bell: "
            f"{event_kind!r}"
        )
    packet = render_report_packet(building_root=building_root, repo_root=temp_repo)
    if packet.get("observed_board_state") != "needs_disposition":
        raise ProfileError(
            f"chat_session_park_seam {label} path report packet did not project needs_disposition"
        )
    inbox = temp_repo / "project" / "brick-protocol" / "status" / "inbox"
    wake_packets = []
    for path in sorted(inbox.glob("*operator-wake*.json")):
        wake_packet = _chat_session_json_object(path)
        if wake_packet.get("building_id") == building_root.name:
            wake_packets.append(wake_packet)
    if not wake_packets:
        raise ProfileError(
            f"chat_session_park_seam {label} path run-surface report_event_policy emitted no operator wake packet"
        )
    wake_targets = wake_packets[-1].get("operator_wake_targets")
    if (
        not isinstance(wake_targets, list)
        or not wake_targets
        or not isinstance(wake_targets[0], Mapping)
        or wake_targets[0].get("sink_ref") != OPERATOR_WAKE_LOCAL_SINK_REF
    ):
        raise ProfileError(f"chat_session_park_seam {label} path wake packet used the wrong sink ref")
    return 17


def _chat_session_lifecycle_violations(target: Path) -> list[str]:
    from support.checkers import check_building_lifecycle_path_shape as lifecycle_shape

    label, paths = lifecycle_shape.collect_paths(target)
    violations = lifecycle_shape.check_paths(
        paths,
        is_u5_5_live=lifecycle_shape.make_u5_5_live_resolver(label),
    )
    if not violations:
        violations.extend(
            lifecycle_shape.collect_content_violations(
                label,
                lifecycle_shape.known_candidates(set(paths)),
            )
        )
    return violations


def _chat_session_single_step_output_dir(building_root: Path) -> Path:
    step_output_root = building_root / "work" / "step-outputs"
    dirs = sorted(path for path in step_output_root.iterdir() if path.is_dir())
    if len(dirs) != 1:
        raise ProfileError(
            "chat_session_park_seam expected exactly one step-output directory, "
            f"observed {len(dirs)}"
        )
    return dirs[0]


def _chat_session_json_object(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"chat_session_park_seam failed to read JSON object {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ProfileError(f"chat_session_park_seam expected JSON object at {path}")
    return value


def _chat_session_write_json_object(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _chat_session_assert_mutated_lifecycle_rejects(
    building_root: Path,
    label: str,
    mutate: Callable[[Path], None],
) -> None:
    mutant = building_root.parent / f"{building_root.name}-mut-{_chat_session_slug(label)}"
    if mutant.exists():
        shutil.rmtree(mutant)
    shutil.copytree(building_root, mutant)
    mutate(mutant)
    violations = _chat_session_lifecycle_violations(mutant)
    if not violations:
        raise ProfileError(f"chat_session_park_seam FIRE did not reject mutated copy: {label}")


def _chat_session_mutate_envelope_uuid(building_root: Path) -> None:
    envelope_path = _chat_session_single_step_output_dir(building_root) / "work-envelope.json"
    envelope = dict(_chat_session_json_object(envelope_path))
    envelope["building_session_ref"] = _chat_session_probe_uuid_text()
    _chat_session_write_json_object(envelope_path, envelope)


def _chat_session_mutate_park_as_adapter_error(building_root: Path) -> None:
    parked_path = _chat_session_single_step_output_dir(building_root) / "parked.json"
    parked = dict(_chat_session_json_object(parked_path))
    parked["adapter_error_ref"] = "adapter-error:mutated"
    parked["agent_fact_created"] = False
    _chat_session_write_json_object(parked_path, parked)


def _chat_session_delete_work_envelope(building_root: Path) -> None:
    envelope_path = _chat_session_single_step_output_dir(building_root) / "work-envelope.json"
    envelope_path.unlink()


def _chat_session_mutate_submission_forbidden_key(building_root: Path) -> None:
    submission_path = _chat_session_submission_path(building_root)
    submission = dict(_chat_session_json_object(submission_path))
    returned = dict(submission.get("returned") or {})
    returned["secret"] = "done"
    submission["returned"] = returned
    _chat_session_write_json_object(submission_path, submission)


def _chat_session_mutate_submission_token(building_root: Path) -> None:
    submission_path = _chat_session_submission_path(building_root)
    submission = dict(_chat_session_json_object(submission_path))
    submission["claim_token"] = "amber-basil-cedar-copper"
    claim_path = submission_path.parent / "claim.json"
    claim = _chat_session_json_object(claim_path)
    if claim.get("claim_token") == submission["claim_token"]:
        submission["claim_token"] = "amber-basil-cedar-delta"
    _chat_session_write_json_object(submission_path, submission)


def _chat_session_submission_path(building_root: Path) -> Path:
    matches = sorted((building_root / "work" / "step-outputs").glob("*/submission.json"))
    if len(matches) != 1:
        raise ProfileError(
            "chat_session_park_seam expected exactly one submission.json, "
            f"observed {len(matches)}"
        )
    return matches[0]


def _chat_session_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "mutation"






def _run_building_automation_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "building_automation",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_chat_session_park_seam(repo: Path) -> KernelResult:"
    poisoned = "def run_chat_session_park_seam_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError("chat_session_park mutation probe could not find seam entrypoint")

    backup = tempfile.NamedTemporaryFile(
        prefix=".chat-session-park-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_building_automation_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "chat_session_park mutation probe did not turn building_automation profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_building_automation_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "chat_session_park mutation probe restored source but building_automation "
            f"remained RED:\n{excerpt}"
        )

    return [
        "chat-session park mutation RED probe passed: disabling the moved "
        "run_chat_session_park_seam entrypoint made check_profile.py --profile "
        "building_automation exit non-zero, then restoring the temp-backed "
        "self file returned building_automation to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for chat-session PARK seam."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved run_chat_session_park_seam "
            "entrypoint, assert building_automation profile exits RED, restore "
            "from a temp backup, then assert building_automation is GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = (
            probe_mutation_red(repo)
            if args.probe_mutation_red
            else [run_chat_session_park_seam(repo).output]
        )
    except ProfileError as exc:
        print("chat-session park check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

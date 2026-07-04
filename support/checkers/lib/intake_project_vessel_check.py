"""Project-vessel intake behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from support.checkers.lib.adapter_capability_checks import _fixture_gemini_api_key
from support.checkers.lib.checker_temp_vessel import (
    _TEMP_VESSEL_SENTINEL_NAME,
    _case_slug,
    _temp_vessel_cleanup_or_reject,
    _with_temp_vessel_repo,
    _write_temp_vessel_sentinel,
)
from support.checkers.lib.preset_completion_fixture import _preset_completion_command_runner
from support.checkers.lib.yaml_subset import ProfileError, require_mapping, require_string, rule_items


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


from support.checkers.lib.case_runners import _assert_real_repo_env_flag_cleanup_rejected

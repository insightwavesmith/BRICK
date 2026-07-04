"""Building intake seam behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from support.checkers.lib.adapter_capability_checks import _fixture_gemini_api_key
from support.checkers.lib.gate_evidence_readers import (
    _assert_missing_gate_fact_present,
    _assert_no_missing_gate_facts,
)
from support.checkers.lib.preset_completion_fixture import (
    _PRESET_COMPLETION_LIST_RETURN_FIELDS,
    _deterministic_completion_list,
    _preset_completion_command_runner,
)
from support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    rule_items,
)


def _preset_slug(preset_ref: str) -> str:
    return _case_slug(preset_ref.split(":", 1)[-1])


def _case_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "case"


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

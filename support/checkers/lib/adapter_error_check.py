"""Adapter-error frontier kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes adapter-error frontier manifest and path-hardening evidence; it owns no
axis crossing, decides no Movement, and judges no success or quality.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from support.checkers.lib.chat_session_park_check import _chat_session_park_graph_plan
from support.checkers.lib.yaml_subset import KernelResult, ProfileError

def run_adapter_error_frontier_manifest_consistency(repo: Path) -> KernelResult:
    """Pin adapter-error frontier raw_ref resolution after final closure rewrite."""

    from support.checkers import check_building_lifecycle_path_shape as lifecycle_shape
    from support.operator import run as run_module
    from support.recording.raw_claim_trace import reconcile_claim_trace_raw_manifest_from_raw
    from support.recording.lifecycle_emit import _accumulated_raw_manifest

    del repo
    with tempfile.TemporaryDirectory(prefix="bp-adapter-error-frontier-manifest-") as tmp:
        dynamic_plan = {
            "dynamic_walker_evidence": {
                "reroute_adoption_records": [
                    {
                        "source_step_ref": "adopted-reroute-manifest-source",
                        "target_brick": "brick-adopted-reroute-manifest-target",
                        "reroute_ref": "reroute:adopted-reroute-manifest:1",
                    }
                ]
            }
        }
        dynamic_manifest = _accumulated_raw_manifest(
            "adopted-reroute-manifest-case",
            (),
            None,
            plan=dynamic_plan,
        )
        dynamic_link_entries = [
            entry
            for entry in dynamic_manifest.get("entries", [])
            if isinstance(entry, Mapping) and entry.get("path") == "raw/link.jsonl"
        ]
        if "raw:link-reroute:01" not in dynamic_manifest.get("raw_refs", []):
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency dynamic-reroute manifest "
                "pin failed: top-level raw_refs lacks raw:link-reroute:01"
            )
        if not dynamic_link_entries or "raw:link-reroute:01" not in dynamic_link_entries[0].get("raw_refs", []):
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency dynamic-reroute manifest "
                "pin failed: raw/link.jsonl entry lacks raw:link-reroute:01"
            )

        dynamic_red_root = Path(tmp) / "adopted-reroute-manifest-red-case"
        _adapter_error_manifest_write_dynamic_reroute_fixture(
            dynamic_red_root,
            include_manifest_reroute=False,
        )
        dynamic_red_violations: list[str] = []
        lifecycle_shape.validate_minimal_content(dynamic_red_root, dynamic_red_violations)
        if not any(
            "raw_ref does not resolve through raw manifest: raw:link-reroute:01" in item
            for item in dynamic_red_violations
        ):
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency dynamic-reroute FIRE "
                "did not observe unresolved raw:link-reroute:01 before manifest repair"
            )

        dynamic_green_root = Path(tmp) / "adopted-reroute-manifest-green-case"
        _adapter_error_manifest_write_dynamic_reroute_fixture(
            dynamic_green_root,
            include_manifest_reroute=True,
        )
        dynamic_green_violations: list[str] = []
        lifecycle_shape.validate_minimal_content(dynamic_green_root, dynamic_green_violations)
        if dynamic_green_violations:
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency dynamic-reroute fixture "
                "did not resolve every claim_trace raw_ref:\n"
                + "\n".join(f"- {violation}" for violation in dynamic_green_violations)
            )

        root = Path(tmp) / "adapter-error-frontier-manifest-case"
        _adapter_error_manifest_write_broken_fixture(root)

        red_violations: list[str] = []
        lifecycle_shape.validate_minimal_content(root, red_violations)
        if not any("raw_ref does not resolve through raw manifest" in item for item in red_violations):
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency FIRE did not observe "
                "unresolved claim_trace raw_refs before reconciliation"
            )

        written = reconcile_claim_trace_raw_manifest_from_raw(root)
        green_violations: list[str] = []
        lifecycle_shape.validate_minimal_content(root, green_violations)
        if green_violations:
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency lifecycle checker rejected "
                "reconciled fixture:\n"
                + "\n".join(f"- {violation}" for violation in green_violations)
            )

        manifest = json.loads((root / "raw" / "raw-manifest.json").read_text(encoding="utf-8"))
        refs = {
            str(ref)
            for entry in manifest.get("entries", [])
            if isinstance(entry, Mapping)
            for ref in entry.get("raw_refs", [])
            if isinstance(ref, str)
        }
        for ref in ("raw:agent-received:02", "raw:adapter-error:02", "raw:link-frontier:02"):
            if ref not in refs:
                raise ProfileError(
                    "adapter_error_frontier_manifest_consistency reconciled manifest "
                    f"does not carry {ref}"
                )

        preserve_root = Path(tmp) / "adapter-error-frontier-preserve-case"
        _adapter_error_manifest_write_broken_fixture(preserve_root)
        _adapter_error_manifest_write_jsonl(
            preserve_root / "raw" / "link.jsonl",
            [
                {
                    "raw_ref": "raw:link:01",
                    "raw_refs": ["raw:link:01"],
                    "step_ref": f"{preserve_root.name}-work",
                },
                _adapter_error_manifest_link_frontier_record(preserve_root.name),
            ],
        )
        snapshot = run_module._adapter_error_frontier_history_snapshot(preserve_root)
        _adapter_error_manifest_write_jsonl(
            preserve_root / "raw" / "link.jsonl",
            [
                {
                    "raw_ref": "raw:link:01",
                    "raw_refs": ["raw:link:01"],
                    "step_ref": f"{preserve_root.name}-work",
                }
            ],
        )
        run_module._preserve_adapter_error_frontier_history_after_resume(preserve_root, snapshot)
        preserve_violations: list[str] = []
        lifecycle_shape.validate_minimal_content(preserve_root, preserve_violations)
        if preserve_violations:
            raise ProfileError(
                "adapter_error_frontier_manifest_consistency lifecycle checker rejected "
                "preserved final-writer fixture:\n"
                + "\n".join(f"- {violation}" for violation in preserve_violations)
            )

    return KernelResult(
        check_id="adapter_error_frontier_manifest_consistency",
        inspected=len(written) + 6,
        output=(
            "adapter-error frontier manifest consistency passed: synthetic "
            "adapter-error->closure fixture fired RED before reconciliation and "
            "the same lifecycle raw_ref resolver accepted both the reconciled root "
            "and the final-writer preserve root; adopted-reroute fixture fired RED "
            "without raw:link-reroute:01 in raw-manifest and GREEN with every "
            "claim_trace raw_ref resolved."
        ),
    )


def run_adapter_error_path_hardening(repo: Path) -> KernelResult:
    """Pin F15/F16/F18/F19 adapter-error hardening invariants."""

    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator import run as run_module
    from brick_protocol.support.operator import walker_kernel
    from brick_protocol.support.operator import walker_resume
    from brick_protocol.support.operator.frontier_observation import observe_building_frontier
    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref
    from support.checkers import check_building_declaration_integrity as declaration_integrity
    from support.checkers import check_building_lifecycle_path_shape as lifecycle_shape

    inspected = 0
    with tempfile.TemporaryDirectory(prefix="bp-adapter-error-hardening-") as tmp:
        output_root = Path(tmp) / "buildings"
        error_building_id = "adapter-error-hardening-first-step"
        root = output_root / error_building_id
        cli_calls: list[tuple[str, ...]] = []

        def failing_codex_runner(
            args: Sequence[str],
            cwd: Path,
            timeout_seconds: int,
        ) -> LocalCliCompleted:
            del cwd, timeout_seconds
            call = tuple(str(arg) for arg in args)
            cli_calls.append(call)
            birth_certificate = root / "work" / "declared-building-plan.json"
            if not birth_certificate.is_file():
                raise ProfileError(
                    "adapter_error_path_hardening F15/F17: first adapter boundary "
                    "was reached before work/declared-building-plan.json existed"
                )
            if "--version" in call:
                return LocalCliCompleted(call, 0, "codex test-version", "")
            return LocalCliCompleted(call, 1, "", "adapter boom")

        # B2: a dynamic adapter exception/timeout no longer crashes the public
        # surface with a bare RuntimeError. run_building_plan now CATCHES the typed
        # AdapterFrontierEvidenceWritten and RETURNS a clean HELD result (the
        # adapter-error frontier is already written + resumable on disk). Assert the
        # clean held return -- a bare RuntimeError escaping here REDs the check.
        try:
            held_result = run_module.run_building_plan(
                _adapter_error_hardening_graph_plan(
                    error_building_id,
                    first_adapter_ref="adapter:codex-local",
                ),
                output_root=output_root,
                overwrite_existing=True,
                command_runner=failing_codex_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=5,
            )
        except RuntimeError as exc:
            raise ProfileError(
                "adapter_error_path_hardening B2: a dynamic adapter exception must "
                "return a clean held result, not raise a bare RuntimeError "
                f"({exc!r})"
            ) from exc
        held_frontier = observe_building_frontier(root, repo_root=repo)
        if held_frontier.get("frontier_kind") != "agent_incomplete":
            raise ProfileError(
                "adapter_error_path_hardening B2: a dynamic adapter exception did not "
                f"end in an agent_incomplete held frontier: {held_frontier.get('frontier_kind')!r}"
            )
        if _persisted_adapter_error_hold_reason(root) != "adapter_error_frontier":
            raise ProfileError(
                "adapter_error_path_hardening B2: held frontier did not carry the "
                "adapter_error_frontier hold_reason"
            )
        if held_result.step_results:
            raise ProfileError(
                "adapter_error_path_hardening B2: first-step adapter error held with "
                "completed step results"
            )
        inspected += len(cli_calls) + 1
        if not cli_calls:
            raise ProfileError("adapter_error_path_hardening did not reach codex adapter probe")
        if not (root / "work" / "declared-building-plan.json").is_file():
            raise ProfileError("adapter_error_path_hardening root lacks birth certificate")
        building_map = json.loads(
            (root / "work" / "building-map.json").read_text(encoding="utf-8")
        )
        if not building_map.get("declaration_provenance"):
            raise ProfileError(
                "adapter_error_path_hardening root lacks declaration_provenance"
            )
        for rel in declaration_integrity.DECLARATION_CHAIN_ARTIFACTS:
            artifact = root / Path(*rel)
            if not artifact.is_file():
                raise ProfileError(
                    "adapter_error_path_hardening declaration_provenance root "
                    f"lacks required chain artifact {artifact.relative_to(root)}"
                )
        declaration_violations = declaration_integrity.validate_building_root(
            root,
            label="adapter-error-hardening-first-step",
        )
        if declaration_violations:
            raise ProfileError(
                "adapter_error_path_hardening declaration-integrity rejected root:\n"
                + "\n".join(f"- {violation}" for violation in declaration_violations)
            )
        diagnostic_root = output_root / "adapter-error-hardening-diagnostics"
        _write_adapter_error_frontier_direct(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=diagnostic_root.name,
            overwrite_existing=True,
        )
        _assert_adapter_error_diagnostics_preserved(diagnostic_root)
        _assert_adapter_error_frontier_report_root_admission(run_module, repo, output_root)
        inspected += 15
        try:
            run_module.resume_building_plan(root, command_runner=failing_codex_runner)
        except ValueError as exc:
            if "birth-certificate" in str(exc):
                raise ProfileError(
                    "adapter_error_path_hardening resume still refused the first-step "
                    "adapter-error root for missing birth certificate"
                ) from exc
        else:
            raise ProfileError("adapter_error_path_hardening resume without disposition did not hold")
        inspected += 1

        _append_adapter_error_stop_disposition(root)
        before_resume_calls = len(cli_calls)
        resumed = run_module.resume_building_plan(
            root,
            command_runner=failing_codex_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=5,
        )
        if len(cli_calls) != before_resume_calls:
            raise ProfileError("adapter_error_path_hardening F16 stop invoked adapter")
        if resumed.step_results:
            raise ProfileError("adapter_error_path_hardening F16 paper stop replayed step results")
        frontier = observe_building_frontier(root, repo_root=repo)
        if frontier.get("frontier_kind") != "complete":
            raise ProfileError(
                "adapter_error_path_hardening F16 paper stop did not observe complete "
                f"frontier: {frontier.get('frontier_kind')!r}"
            )
        inspected += 3

        mutation_root = output_root / "adapter-error-hardening-mutated-stop"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=mutation_root.name,
        )
        _append_adapter_error_stop_disposition(mutation_root)
        original_resume = run_module._resume_dynamic_graph_walker
        mutation_calls: list[tuple[str, ...]] = []

        def mutation_runner(
            args: Sequence[str],
            cwd: Path,
            timeout_seconds: int,
        ) -> LocalCliCompleted:
            del cwd, timeout_seconds
            call = tuple(str(arg) for arg in args)
            mutation_calls.append(call)
            raise RuntimeError("mutated stop path attempted live adapter invocation")

        def mutated_resume(*args: Any, **kwargs: Any) -> Any:
            runner = kwargs.get("command_runner")
            if runner is not None:
                runner(("codex", "exec", "mutated-live-rerun"), Path("."), 1)
            return original_resume(*args, **kwargs)

        try:
            run_module._resume_dynamic_graph_walker = mutated_resume
            try:
                run_module.resume_building_plan(
                    mutation_root,
                    command_runner=mutation_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=5,
                )
            except RuntimeError as exc:
                if "mutated stop path attempted live adapter invocation" not in str(exc):
                    raise
            else:
                raise ProfileError(
                    "adapter_error_path_hardening F16 mutation did not fire RED"
                )
        finally:
            run_module._resume_dynamic_graph_walker = original_resume
        if not mutation_calls:
            raise ProfileError("adapter_error_path_hardening F16 mutation made no adapter call")
        inspected += len(mutation_calls)

        legacy_root = output_root / "adapter-error-hardening-legacy-stop"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=legacy_root.name,
            first_adapter_ref="adapter:local",
            followup_adapter_ref="adapter:codex-local",
            local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
        )
        _rewrite_adapter_error_hold_as_legacy_reason_refs(legacy_root)
        _append_adapter_error_stop_disposition(legacy_root)
        legacy_calls: list[tuple[str, ...]] = []

        def legacy_runner(
            args: Sequence[str],
            cwd: Path,
            timeout_seconds: int,
        ) -> LocalCliCompleted:
            del cwd, timeout_seconds
            call = tuple(str(arg) for arg in args)
            legacy_calls.append(call)
            raise RuntimeError("legacy stop path attempted live adapter invocation")

        legacy_resumed = run_module.resume_building_plan(
            legacy_root,
            local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
            command_runner=legacy_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=5,
        )
        if legacy_calls:
            raise ProfileError("adapter_error_path_hardening F16b legacy stop invoked adapter")
        if legacy_resumed.step_results:
            raise ProfileError("adapter_error_path_hardening F16b legacy paper stop replayed step results")
        legacy_frontier = observe_building_frontier(legacy_root, repo_root=repo)
        if legacy_frontier.get("frontier_kind") != "complete":
            raise ProfileError(
                "adapter_error_path_hardening F16b legacy paper stop did not observe "
                f"complete frontier: {legacy_frontier.get('frontier_kind')!r}"
            )
        inspected += 4

        mutation_legacy_root = output_root / "adapter-error-hardening-legacy-mutated-stop"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=mutation_legacy_root.name,
            first_adapter_ref="adapter:local",
            followup_adapter_ref="adapter:codex-local",
            local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
        )
        _rewrite_adapter_error_hold_as_legacy_reason_refs(mutation_legacy_root)
        _append_adapter_error_stop_disposition(mutation_legacy_root)
        original_adapter_error_predicate = walker_resume._adapter_error_hold_without_return
        mutation_legacy_calls: list[tuple[str, ...]] = []

        def mutation_legacy_runner(
            args: Sequence[str],
            cwd: Path,
            timeout_seconds: int,
        ) -> LocalCliCompleted:
            del cwd, timeout_seconds
            call = tuple(str(arg) for arg in args)
            mutation_legacy_calls.append(call)
            raise RuntimeError("legacy flat-field-only predicate attempted live adapter invocation")

        def flat_field_only_predicate(hold_record: Mapping[str, Any]) -> bool:
            return hold_record.get("hold_reason") == "adapter_error_frontier"

        try:
            walker_resume._adapter_error_hold_without_return = flat_field_only_predicate
            # B2: the broken (flat-field-only) predicate fails to recognize the legacy
            # reason-ref hold, so resume does a LIVE adapter rerun. That live call now
            # ends in a clean held adapter-error frontier instead of a bare RuntimeError
            # crash, so the mutation-RED signal is the live adapter invocation itself
            # (mutation_legacy_calls non-empty), not a propagated exception.
            try:
                run_module.resume_building_plan(
                    mutation_legacy_root,
                    local_callables={
                        "callable:local:agent-invoke0-smoke": _hardening_local_brain
                    },
                    command_runner=mutation_legacy_runner,
                    adapter_cwd=repo,
                    adapter_timeout_seconds=5,
                )
            except RuntimeError:
                # A live adapter call may still surface as a non-adapter RuntimeError
                # depending on the failure shape; either way the live call was made.
                pass
        finally:
            walker_resume._adapter_error_hold_without_return = original_adapter_error_predicate
        if not mutation_legacy_calls:
            raise ProfileError(
                "adapter_error_path_hardening F16b legacy flat-field-only "
                "mutation did not fire RED (no live adapter invocation)"
            )
        inspected += len(mutation_legacy_calls)

        _assert_codex_ephemeral_env_dial(repo)
        inspected += 2

        overwrite_root = output_root / "adapter-error-hardening-overwrite"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=overwrite_root.name,
        )
        if not (overwrite_root / "evidence" / "claim_trace" / "link" / "frontier_trace.json").is_file():
            raise ProfileError("adapter_error_path_hardening overwrite seed lacked frontier trace")
        run_module.run_building_plan(
            _adapter_error_hardening_graph_plan(
                overwrite_root.name,
                first_adapter_ref="adapter:local",
            ),
            output_root=output_root,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
            adapter_cwd=repo,
            adapter_timeout_seconds=5,
        )
        if (overwrite_root / "evidence" / "claim_trace" / "link" / "frontier_trace.json").exists():
            raise ProfileError("adapter_error_path_hardening F19 stale frontier_trace survived")
        manifest = json.loads(
            (overwrite_root / "raw" / "raw-manifest.json").read_text(encoding="utf-8")
        )
        manifest_refs = {
            str(ref)
            for ref in manifest.get("raw_refs", [])
            if isinstance(ref, str)
        }
        if any(ref.startswith("raw:link-frontier:") for ref in manifest_refs):
            raise ProfileError("adapter_error_path_hardening F19 stale link-frontier ref survived")
        violations: list[str] = []
        lifecycle_shape.validate_minimal_content(overwrite_root, violations)
        if violations:
            raise ProfileError(
                "adapter_error_path_hardening F19 overwrite root failed lifecycle shape:\n"
                + "\n".join(f"- {violation}" for violation in violations)
            )
        inspected += 4

        mutation_overwrite_root = output_root / "adapter-error-hardening-overwrite-mutated"
        _write_adapter_error_frontier_fixture(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=mutation_overwrite_root.name,
        )
        original_clear = walker_kernel._clear_overwrite_claim_trace_manifest
        try:
            walker_kernel._clear_overwrite_claim_trace_manifest = lambda root: None
            run_module.run_building_plan(
                _adapter_error_hardening_graph_plan(
                    mutation_overwrite_root.name,
                    first_adapter_ref="adapter:local",
                ),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _hardening_local_brain},
                adapter_cwd=repo,
                adapter_timeout_seconds=5,
            )
        finally:
            walker_kernel._clear_overwrite_claim_trace_manifest = original_clear
        if not (
            mutation_overwrite_root
            / "evidence"
            / "claim_trace"
            / "link"
            / "frontier_trace.json"
        ).exists():
            raise ProfileError("adapter_error_path_hardening F19 mutation did not fire RED")
        inspected += 1

    return KernelResult(
        check_id="adapter_error_path_hardening",
        inspected=inspected,
        output=(
            "adapter-error hardening passed: birth certificate existed before first "
            "codex adapter probe, resume no longer birth-certificate-refuses the "
            "first-step adapter-error root, stop disposition paper-closed without "
            "adapter invocation for flat and legacy reason-ref holds, pre-frontier "
            "report raw logs are admitted only for the same Building, codex "
            "--ephemeral is env-gated, overwrite cleared stale claim_trace/raw "
            "manifest refs, and F16/F16b/F19 mutation probes fired RED."
        ),
    )


def _assert_adapter_error_frontier_report_root_admission(
    run_module: Any,
    repo: Path,
    output_root: Path,
) -> None:
    from support.recording import adapter_error_frontier

    base_building_id = "adapter-error-hardening-report-root"
    reroute_building_id = f"{base_building_id}-reroute1"
    root = output_root / base_building_id
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "work").mkdir(parents=True, exist_ok=True)
    (root / "declared-building-plan.json").write_text(
        json.dumps({"building_id": base_building_id}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "work" / "declared-building-plan.json").write_text(
        json.dumps({"building_id": base_building_id}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "raw" / "report-delivery.jsonl").write_text(
        json.dumps(
            {
                "kind": "report_delivery_observation",
                "schema_version": "report-delivery-0",
                "building_id": base_building_id,
                "report_id": f"report:{base_building_id}:building-started",
                "source_truth": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    thread_path = root / "raw" / "report-thread.jsonl"
    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=(
            f"brick-protocol-{base_building_id}-building-started-event-"
            "2026-06-25T00-00-00-00-00"
        ),
    )
    if not adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: declaration root with pre-frontier "
            "live vessel report raw logs was rejected"
        )

    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=f"report:{base_building_id}:building-started",
    )
    if not adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: declaration root with exact "
            "legacy report: report-thread row was rejected"
        )

    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id="report:other-building:building-started",
    )
    if adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: wrong-building report-thread row "
            "was admitted"
        )

    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=(
            f"brick-protocol-{reroute_building_id}-building-started-event-"
            "2026-06-25T00-00-00-00-00"
        ),
    )
    if adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: prefix-related live vessel "
            "report-thread row was admitted"
        )

    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=(
            f"brick-protocol-rogue-prefix-{base_building_id}-building-started-event-"
            "2026-06-25T00-00-00-00-00"
        ),
    )
    if adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: suffix-collision live vessel "
            "report-thread row was admitted"
        )

    embedded_marker_source_id = (
        f"brick-protocol-{base_building_id}-gate-passed-event-evil"
    )
    embedded_marker_report_id = (
        f"{embedded_marker_source_id}-building-started-event-"
        "2026-06-25T00-00-00-00-00"
    )
    if (
        adapter_error_frontier._report_id_source_id(embedded_marker_report_id)
        != embedded_marker_source_id
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: report id source parser did not "
            "right-anchor on the trailing event suffix"
        )
    _write_adapter_error_report_thread_probe(
        thread_path,
        report_id=embedded_marker_report_id,
    )
    if adapter_error_frontier._root_holds_only_declaration_chain_artifacts(
        root,
        building_id=base_building_id,
    ):
        raise ProfileError(
            "adapter_error_path_hardening P0: embedded event-marker foreign "
            "report-thread row was admitted"
        )

    partial_id = "adapter-error-hardening-partial-root"
    partial_root = output_root / partial_id
    (partial_root / "raw").mkdir(parents=True, exist_ok=True)
    (partial_root / "work").mkdir(parents=True, exist_ok=True)
    (partial_root / "declared-building-plan.json").write_text(
        json.dumps({"building_id": partial_id}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (partial_root / "work" / "declared-building-plan.json").write_text(
        json.dumps({"building_id": partial_id}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (partial_root / "raw" / "partial-write.jsonl").write_text(
        json.dumps(
            {
                "kind": "non_declaration_artifact",
                "building_id": partial_id,
                "source_truth": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if adapter_error_frontier._adapter_error_existing_root_state(
        partial_root,
        building_id=partial_id,
    ) != "partial_write_risk":
        raise ProfileError(
            "adapter_error_path_hardening P0: non-declaration root was not "
            "classified as partial_write_risk"
        )
    partial_result = _write_adapter_error_frontier_direct(
        run_module,
        repo=repo,
        output_root=output_root,
        building_id=partial_id,
        overwrite_existing=True,
    )
    marker_path = partial_root / "adapter-error-frontier-partial-write-risk.json"
    if partial_result.written_files != (marker_path,) or not marker_path.is_file():
        raise ProfileError(
            "adapter_error_path_hardening P0: partial-write-risk marker was not written"
        )
    if not (partial_root / "raw" / "partial-write.jsonl").is_file():
        raise ProfileError(
            "adapter_error_path_hardening P0: partial-write-risk artifact was clobbered"
        )
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    if marker.get("frontier_kind") != "partial_write_risk":
        raise ProfileError(
            "adapter_error_path_hardening P0: partial-write-risk marker lacks "
            "frontier_kind"
        )

    empty_id = "adapter-error-hardening-empty-root"
    empty_root = output_root / empty_id
    empty_root.mkdir(parents=True, exist_ok=True)
    empty_result = _write_adapter_error_frontier_direct(
        run_module,
        repo=repo,
        output_root=output_root,
        building_id=empty_id,
        overwrite_existing=False,
    )
    empty_marker_path = empty_root / "adapter-error-frontier-root-state.json"
    if empty_result.written_files != (empty_marker_path,) or not empty_marker_path.is_file():
        raise ProfileError(
            "adapter_error_path_hardening P0: empty-root marker was not written"
        )
    empty_marker = json.loads(empty_marker_path.read_text(encoding="utf-8"))
    if empty_marker.get("frontier_kind") != "root_exists_without_frontier":
        raise ProfileError(
            "adapter_error_path_hardening P0: empty-root marker lacks "
            "root_exists_without_frontier"
        )

    file_id = "adapter-error-hardening-not-directory"
    (output_root / file_id).write_text("not a directory\n", encoding="utf-8")
    try:
        _write_adapter_error_frontier_direct(
            run_module,
            repo=repo,
            output_root=output_root,
            building_id=file_id,
            overwrite_existing=True,
        )
    except NotADirectoryError as exc:
        if "existing_root_state=not_directory" not in str(exc):
            raise ProfileError(
                "adapter_error_path_hardening P0: not-directory error lacked "
                "root-state evidence"
            ) from exc
    else:
        raise ProfileError(
            "adapter_error_path_hardening P0: not-directory root was not rejected"
        )


def _write_adapter_error_report_thread_probe(path: Path, *, report_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "kind": "report_slack_thread_parent_observation",
                "report_id": report_id,
                "source_truth": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_adapter_error_frontier_direct(
    run_module: Any,
    *,
    repo: Path,
    output_root: Path,
    building_id: str,
    overwrite_existing: bool,
) -> Any:
    from support.recording import adapter_error_frontier

    plan = _adapter_error_hardening_graph_plan(
        building_id,
        first_adapter_ref="adapter:codex-local",
    )
    first_step = plan["brick_steps"][0]
    link_row = plan["link_edges"][0]["rows"][0]
    brick_row = next(row for row in first_step["rows"] if row.get("axis") == "Brick")
    agent_row = next(row for row in first_step["rows"] if row.get("axis") == "Agent")
    packet = {
        "building_id": building_id,
        "selected_adapter_ref": "adapter:codex-local",
        "step_rows": {
            "step_ref": first_step["step_ref"],
            "rows": [brick_row, agent_row, link_row],
        },
    }
    prepared = run_module.prepare_agent_run_from_step_rows(
        packet,
        proof_limits=("checker fixture support evidence only",),
    )
    adapter_request = run_module._adapter_request_from_prepared(
        packet,
        prepared,
        project_ref=None,
    )
    return adapter_error_frontier.write_adapter_error_frontier_evidence(
        building_id=building_id,
        plan_ref=f"plan:{building_id}",
        plan=plan,
        completed_step_results=(),
        failed_preparation=prepared,
        adapter_request=adapter_request,
        adapter_error={
            "error_kind": "local_cli_timeout",
            "exception_type": "TimeoutExpired",
            "message_excerpt": "timeout",
            "timeout_reap_reason": "timeout",
            "timeout_stdout_excerpt": "partial stdout before timeout",
            "timeout_stderr_excerpt": "partial stderr before timeout",
            "proof_limits": ("checker fixture support evidence only",),
            "not_proven": ("complete adapter-error lifecycle frontier",),
        },
        output_root=output_root,
        overwrite_existing=overwrite_existing,
        proof_limits=("checker fixture support evidence only",),
    )


def _assert_adapter_error_diagnostics_preserved(root: Path) -> None:
    expected = {
        "timeout_reap_reason": "timeout",
        "timeout_stdout_excerpt": "partial stdout before timeout",
        "timeout_stderr_excerpt": "partial stderr before timeout",
    }
    raw_path = root / "raw" / "adapter-error.jsonl"
    if not raw_path.is_file():
        raise ProfileError("adapter_error_path_hardening diagnostics root lacks raw adapter-error")
    raw_records = [
        json.loads(line)
        for line in raw_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(raw_records) != 1:
        raise ProfileError("adapter_error_path_hardening diagnostics expected one raw row")
    step_paths = sorted((root / "work" / "step-outputs").glob("*/adapter-error.json"))
    if len(step_paths) != 1:
        raise ProfileError("adapter_error_path_hardening diagnostics expected one step-output")
    step_record = json.loads(step_paths[0].read_text(encoding="utf-8"))
    for label, record in (("raw", raw_records[0]), ("step-output", step_record)):
        for key, value in expected.items():
            if record.get(key) != value:
                raise ProfileError(
                    "adapter_error_path_hardening diagnostics dropped "
                    f"{key} from {label}"
                )


def _adapter_error_hardening_graph_plan(
    building_id: str,
    *,
    first_adapter_ref: str,
    followup_adapter_ref: str = "adapter:local",
) -> Mapping[str, Any]:
    plan = json.loads(json.dumps(_chat_session_park_graph_plan(building_id=building_id)))
    plan.pop("report_event_policy", None)
    first_step = plan["brick_steps"][0]
    first_step["selected_adapter_ref"] = first_adapter_ref
    first_step["step_ref"] = f"{building_id}-work"
    first_step["completion_edge_ref"] = f"edge:{building_id}-work-to-followup"
    for row in first_step["rows"]:
        if row.get("axis") == "Brick":
            row["row_ref"] = f"brick-row:{building_id}-work"
            row["brick_work_ref"] = f"work:{building_id}-work"
            row["brick_instance_ref"] = f"brick-{building_id}-work"
            row["work_statement"] = "Adapter-error hardening fixture first step."
        if row.get("axis") == "Agent":
            row["row_ref"] = f"agent-row:{building_id}-work"
    followup = plan["brick_steps"][1]
    followup["step_ref"] = f"{building_id}-followup"
    followup["selected_adapter_ref"] = followup_adapter_ref
    followup["completion_edge_ref"] = f"edge:{building_id}-followup-to-boundary"
    for row in followup["rows"]:
        if row.get("axis") == "Brick":
            row["row_ref"] = f"brick-row:{building_id}-followup"
            row["brick_work_ref"] = f"work:{building_id}-followup"
            row["brick_instance_ref"] = f"brick-{building_id}-followup"
        if row.get("axis") == "Agent":
            row["row_ref"] = f"agent-row:{building_id}-followup"
    plan["execution_order"] = [first_step["step_ref"], followup["step_ref"]]
    plan["link_edges"] = [
        {
            "edge_ref": first_step["completion_edge_ref"],
            "source_step_ref": first_step["step_ref"],
            "target_step_ref": followup["step_ref"],
            "rows": [
                {
                    "axis": "Link",
                    "row_ref": f"link-row:{building_id}-work",
                    "movement": "forward",
                    "target_ref": f"brick-{building_id}-followup",
                    "declared_gate_refs": ["link-gate:default-transition"],
                }
            ],
        },
        {
            "edge_ref": followup["completion_edge_ref"],
            "source_step_ref": followup["step_ref"],
            "rows": [
                {
                    "axis": "Link",
                    "row_ref": f"link-row:{building_id}-followup",
                    "movement": "forward",
                    "target_ref": f"building-boundary:{building_id}-closed",
                    "declared_gate_refs": ["link-gate:default-transition"],
                }
            ],
        },
    ]
    return plan


def _persisted_adapter_error_hold_reason(root: Path) -> str:
    """Read the persisted dynamic_walker_evidence hold_reason from a held root.

    The adapter-error frontier write records the hold inside the evidence manifest
    plan snapshot (same location _rewrite_adapter_error_hold_as_legacy_reason_refs
    reads). This is the on-disk proof that the held frontier carries the
    adapter_error_frontier reason after the B2 typed-signal/return change.
    """

    manifest_path = root / "evidence" / "evidence-manifest.json"
    if not manifest_path.is_file():
        return ""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot = manifest.get("plan_snapshot") if isinstance(manifest, Mapping) else None
    if not isinstance(snapshot, Mapping):
        return ""
    plan_rows_copy = snapshot.get("plan_rows_copy")
    if not isinstance(plan_rows_copy, str):
        return ""
    plan_copy = json.loads(plan_rows_copy)
    if not isinstance(plan_copy, Mapping):
        return ""
    evidence = plan_copy.get("dynamic_walker_evidence")
    if not isinstance(evidence, Mapping):
        return ""
    hold = evidence.get("hold")
    if not isinstance(hold, Mapping):
        return ""
    return str(hold.get("hold_reason") or "")


def _write_adapter_error_frontier_fixture(
    run_module: Any,
    *,
    repo: Path,
    output_root: Path,
    building_id: str,
    first_adapter_ref: str = "adapter:codex-local",
    followup_adapter_ref: str = "adapter:local",
    local_callables: Mapping[str, Any] | None = None,
) -> None:
    root = output_root / building_id

    def failing_runner(
        args: Sequence[str],
        cwd: Path,
        timeout_seconds: int,
    ) -> Any:
        from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

        del cwd, timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        return LocalCliCompleted(call, 1, "", "adapter boom")

    # B2: the dynamic adapter exception now RETURNS a clean held result rather than
    # raising a bare RuntimeError. The seeded fixture root must still be a held
    # adapter-error frontier on disk.
    try:
        run_module.run_building_plan(
            _adapter_error_hardening_graph_plan(
                building_id,
                first_adapter_ref=first_adapter_ref,
                followup_adapter_ref=followup_adapter_ref,
            ),
            output_root=output_root,
            overwrite_existing=True,
            local_callables=local_callables,
            command_runner=failing_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=5,
        )
    except RuntimeError as exc:
        raise ProfileError(
            "adapter_error_path_hardening fixture: a dynamic adapter exception must "
            f"return a clean held result, not raise a bare RuntimeError ({exc!r})"
        ) from exc
    if not root.is_dir():
        raise ProfileError(f"adapter_error_path_hardening fixture root missing: {root}")
    if _persisted_adapter_error_hold_reason(root) != "adapter_error_frontier":
        raise ProfileError(
            "adapter_error_path_hardening fixture root is not a held adapter-error frontier"
        )


def _rewrite_adapter_error_hold_as_legacy_reason_refs(root: Path) -> None:
    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref

    manifest_path = root / "evidence" / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture manifest is not a mapping")
    snapshot_value = manifest.get("plan_snapshot")
    if not isinstance(snapshot_value, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture lacks plan_snapshot")
    snapshot = dict(snapshot_value)
    plan_rows_copy = snapshot.get("plan_rows_copy")
    if not isinstance(plan_rows_copy, str):
        raise ProfileError("adapter_error_path_hardening legacy fixture lacks plan_rows_copy")
    plan_copy = json.loads(plan_rows_copy)
    if not isinstance(plan_copy, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture plan copy is not a mapping")
    plan_dict = dict(plan_copy)
    evidence_value = plan_dict.get("dynamic_walker_evidence")
    if not isinstance(evidence_value, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture lacks dynamic evidence")
    evidence = dict(evidence_value)
    hold_value = evidence.get("hold")
    if not isinstance(hold_value, Mapping):
        raise ProfileError("adapter_error_path_hardening legacy fixture lacks hold record")
    legacy_hold = dict(hold_value)
    if legacy_hold.get("hold_reason") != "adapter_error_frontier":
        raise ProfileError("adapter_error_path_hardening legacy fixture source hold is not adapter-error")

    source_step_ref = str(legacy_hold.get("source_step_ref") or f"{root.name}-work")
    source_brick_ref = str(legacy_hold.get("source_brick_ref") or f"brick-{source_step_ref}")
    pending_target_ref = str(
        legacy_hold.get("pending_target_ref")
        or legacy_hold.get("target_brick")
        or source_brick_ref
    )
    attempt_number = legacy_hold.get("attempt_number")
    attempt = attempt_number if isinstance(attempt_number, int) and not isinstance(attempt_number, bool) else 1
    reason_refs = [
        f"observation:adapter-error-frontier:{source_step_ref}",
        "observation:reroute-hold-reason-adapter_error_frontier",
    ]
    legacy_hold.pop("hold_reason", None)
    legacy_hold["transition_lifecycle_reason_refs"] = list(reason_refs)
    evidence["hold"] = legacy_hold
    plan_dict["dynamic_walker_evidence"] = evidence
    snapshot["plan_rows_copy"] = json.dumps(
        plan_dict,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    manifest["plan_snapshot"] = snapshot
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    legacy_raw_ref = "raw:link-frontier:legacy-01"
    legacy_paused_at_ref = _hold_paused_at_ref(legacy_hold)
    legacy_row = {
        "@context": {
            "bp": "urn:bp:",
            "ce": "https://cloudevents.io/spec/v1.0/",
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@id": f"urn:bp:building:{root.name}::raw/link.jsonl#legacy-01",
        "adapter_error_ref": f"adapter-error:{source_step_ref}:attempt-{attempt}",
        "building_id": root.name,
        "datacontenttype": "application/json",
        "dataschema": "urn:bp:schema:graph-ready-v1",
        "frontier_kind": "agent_incomplete",
        "generatedAtTime": "2026-06-12T04:00:54Z",
        "id": f"urn:bp:building:{root.name}::raw/link.jsonl#legacy-01",
        "observed_boundary_ref": source_brick_ref,
        "raw_ref": legacy_raw_ref,
        "raw_refs": [legacy_raw_ref],
        "recorded_at": "2026-06-12T04:00:54Z",
        "schema_version": "graph-ready-v1",
        "source": f"urn:bp:building:{root.name}",
        "source_brick_instance_ref": source_brick_ref,
        "specversion": "1.0",
        "step_ref": source_step_ref,
        "subject": source_step_ref,
        "target_brick_instance_ref": pending_target_ref,
        "time": "2026-06-12T04:00:54Z",
        "transition_lifecycle_from_brick_ref": source_brick_ref,
        "transition_lifecycle_not_proven": [
            "semantic correctness of the agent-proposed reroute",
            "parallel runtime execution (P-walker-2 fan-in/fan-out out of scope here)",
            "scheduler / queue / retry behavior",
            "caller/COO disposition after a HOLD",
            "adapter:local resume probes only unless caller uses another adapter",
            "parallel runtime execution",
            "full process-integrity across resumed provider processes",
            "semantic correctness of the human/COO disposition",
        ],
        "transition_lifecycle_paused_at_ref": legacy_paused_at_ref,
        "transition_lifecycle_pending_target_ref": pending_target_ref,
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_proof_limits": [
            "support evidence only",
            "dynamic walker walks declared gate-adopted agent-proposed routes only",
            "support authors no route or Movement",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "transition_lifecycle_reason_refs": list(reason_refs),
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_state": "paused",
        "transition_record_created": False,
        "type": "bp.raw.link",
    }
    with (root / "raw" / "link.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(legacy_row, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + "\n"
        )


def _append_adapter_error_stop_disposition(root: Path) -> None:
    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref

    evidence_manifest = json.loads(
        (root / "evidence" / "evidence-manifest.json").read_text(encoding="utf-8")
    )
    plan_copy = json.loads(evidence_manifest["plan_snapshot"]["plan_rows_copy"])
    evidence = plan_copy["dynamic_walker_evidence"]
    hold_record = evidence["hold"]
    paused_at_ref = _hold_paused_at_ref(hold_record)
    raw_ref = "raw:link-disposition:01"
    row = {
        "raw_ref": raw_ref,
        "raw_refs": [raw_ref],
        "transition_author_ref": "human:adapter-error-hardening-checker",
        "transition_lifecycle_state": "resumed",
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_paused_at_ref": paused_at_ref,
        "transition_lifecycle_resumed_from_ref": paused_at_ref,
        "transition_lifecycle_pending_target_ref": hold_record["pending_target_ref"],
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_disposition_action": "stop",
        "transition_lifecycle_reason_refs": [
            f"checker:adapter-error-hardening:{root.name}:stop"
        ],
    }
    link_path = root / "raw" / "link.jsonl"
    with link_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")


def _assert_codex_ephemeral_env_dial(repo: Path) -> None:
    from brick_protocol.support.connection import agent_adapter
    from brick_protocol.support.connection import adapter_local_cli
    from brick_protocol.support.connection.agent_adapter import (
        AgentAdapterRequest,
        LocalCliCompleted,
    )

    spec = agent_adapter._local_cli_spec("adapter:codex-local")
    request = AgentAdapterRequest(
        building_id="adapter-error-hardening-ephemeral",
        agent_object_ref="agent-object:dev",
        adapter_ref="adapter:codex-local",
        brick_instance_ref="brick-ephemeral",
        next_brick_instance_ref="building-boundary:ephemeral-closed",
        work_statement="Check codex ephemeral argv.",
        required_return_shape="made_changes, observed_evidence, not_proven",
    )

    def runner(args: Sequence[str], cwd: Path, timeout_seconds: int) -> LocalCliCompleted:
        del cwd, timeout_seconds
        call = tuple(str(arg) for arg in args)
        return LocalCliCompleted(
            call,
            0,
            json.dumps(
                {
                    "made_changes": [],
                    "observed_evidence": ["argv captured"],
                    "not_proven": ["provider behavior"],
                }
            ),
            "",
        )

    old = os.environ.get("BRICK_CODEX_EPHEMERAL")
    try:
        os.environ.pop("BRICK_CODEX_EPHEMERAL", None)
        absent = adapter_local_cli._invoke_local_cli(
            spec,
            request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=runner,
        )
        if "--skip-git-repo-check" not in absent.args:
            raise ProfileError("codex-exec-readonly did not emit --skip-git-repo-check")
        # Ephemeral is now the DEFAULT (concurrent-codex shared-state deadlock
        # fix): absent env var must still emit --ephemeral.
        if "--ephemeral" not in absent.args:
            raise ProfileError("BRICK_CODEX_EPHEMERAL absent did not emit --ephemeral (default-on)")
        os.environ["BRICK_CODEX_EPHEMERAL"] = "0"
        optout = adapter_local_cli._invoke_local_cli(
            spec,
            request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=runner,
        )
        if "--skip-git-repo-check" not in optout.args:
            raise ProfileError("codex-exec-readonly dropped --skip-git-repo-check on ephemeral opt-out")
        if "--ephemeral" in optout.args:
            raise ProfileError("BRICK_CODEX_EPHEMERAL=0 still emitted --ephemeral (opt-out broken)")
        os.environ["BRICK_CODEX_EPHEMERAL"] = "1"
        enabled = adapter_local_cli._invoke_local_cli(
            spec,
            request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=runner,
        )
        if "--skip-git-repo-check" not in enabled.args:
            raise ProfileError("codex-exec-readonly dropped --skip-git-repo-check with --ephemeral")
        if "--ephemeral" not in enabled.args:
            raise ProfileError("BRICK_CODEX_EPHEMERAL=1 did not emit --ephemeral")
    finally:
        if old is None:
            os.environ.pop("BRICK_CODEX_EPHEMERAL", None)
        else:
            os.environ["BRICK_CODEX_EPHEMERAL"] = old


def _hardening_local_brain(request: Any) -> Mapping[str, Any]:
    from brick_protocol.brick.work import parse_required_return_shape

    returned: dict[str, Any] = {}
    for label in parse_required_return_shape(request.required_return_shape):
        if label == "made_changes":
            returned[label] = ["adapter-error hardening local fixture"]
        elif label == "observed_evidence":
            returned[label] = [f"observed {request.brick_instance_ref}"]
        elif label == "not_proven":
            returned[label] = ["semantic correctness of fixture work"]
        elif label == "adapter_ref":
            returned[label] = request.adapter_ref
        elif label == "returned_summary":
            returned[label] = "adapter-error hardening local return"
        else:
            returned[label] = f"fixture value for {label}"
    return returned


def _adapter_error_manifest_write_broken_fixture(root: Path) -> None:
    case_id = root.name
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "brick-work.jsonl",
        [{"raw_ref": "raw:brick:01", "raw_refs": ["raw:brick:01"], "step_ref": f"{case_id}-work"}],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "agent-return.jsonl",
        [{"raw_ref": "raw:agent:01", "raw_refs": ["raw:agent:01"], "step_ref": f"{case_id}-work"}],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "agent-received.jsonl",
        [
            {
                "agent_object_ref": "agent-object:coo",
                "raw_ref": "raw:agent-received:02",
                "raw_refs": ["raw:agent-received:02"],
                "received_work_ref": f"brick-work:02:{case_id}-closure",
                "step_ref": f"{case_id}-closure",
            }
        ],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "adapter-error.jsonl",
        [
            {
                "adapter_error_ref": f"adapter-error:{case_id}-closure:attempt-1",
                "agent_fact_created": False,
                "brick_instance_ref": f"brick-{case_id}-closure",
                "raw_ref": "raw:adapter-error:02",
                "raw_refs": ["raw:adapter-error:02"],
                "step_ref": f"{case_id}-closure",
            }
        ],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "link.jsonl",
        [{"raw_ref": "raw:link:01", "raw_refs": ["raw:link:01"], "step_ref": f"{case_id}-work"}],
    )
    _adapter_error_manifest_write_json(
        root / "raw" / "raw-manifest.json",
        {
            "building_id": case_id,
            "raw_refs": ["raw:brick:01", "raw:agent:01", "raw:link:01"],
            "entries": [
                _adapter_error_manifest_entry("raw/brick-work.jsonl", "Brick", ["raw:brick:01"]),
                _adapter_error_manifest_entry("raw/agent-return.jsonl", "Agent", ["raw:agent:01"]),
                _adapter_error_manifest_entry("raw/link.jsonl", "Link", ["raw:link:01"]),
            ],
        },
    )
    _adapter_error_manifest_write_json(
        root / "evidence" / "evidence-manifest.json",
        {"building_id": case_id, "proof_limits": ["support evidence only"]},
    )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "brick" / "work_contract.json",
        "Brick",
        "brick-work:01",
        "raw:brick:01",
        {"work_statement": "fixture work"},
    )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "agent" / "returned_claims.json",
        "Agent",
        "agent-fact:01",
        "raw:agent:01",
        {"received_work": "brick-work:01", "returned_payload_ref": "fixture:return"},
    )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "agent" / "receipt_trace.json",
        "Agent",
        "agent-receipt:02",
        "raw:agent-received:02",
        {"receipt_role": "Agent received declared work before adapter exception observation"},
    )
    for rel, fact_ref, raw_ref in (
        ("transfer_trace.json", "link-transfer:01", "raw:link:01"),
        ("carry_trace.json", "link-carry:01", "raw:link:01"),
        ("sufficiency_trace.json", "link-sufficiency:01", "raw:link:01"),
        ("movement_trace.json", "link-movement:01", "raw:link:01"),
        ("frontier_trace.json", "link-frontier:02", "raw:link-frontier:02"),
    ):
        _adapter_error_manifest_write_claim(
            root / "evidence" / "claim_trace" / "link" / rel,
            "Link",
            fact_ref,
            raw_ref,
            {"frontier_kind": "agent_incomplete"} if rel == "frontier_trace.json" else {"link_ref": fact_ref},
        )


def _adapter_error_manifest_write_dynamic_reroute_fixture(
    root: Path,
    *,
    include_manifest_reroute: bool,
) -> None:
    case_id = root.name
    link_raw_refs = ["raw:link:01"]
    manifest_link_refs = ["raw:link:01"]
    manifest_top_refs = ["raw:brick:01", "raw:agent:01", "raw:link:01"]
    if include_manifest_reroute:
        manifest_link_refs.append("raw:link-reroute:01")
        manifest_top_refs.append("raw:link-reroute:01")
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "brick-work.jsonl",
        [{"raw_ref": "raw:brick:01", "raw_refs": ["raw:brick:01"], "step_ref": f"{case_id}-work"}],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "agent-return.jsonl",
        [{"raw_ref": "raw:agent:01", "raw_refs": ["raw:agent:01"], "step_ref": f"{case_id}-work"}],
    )
    _adapter_error_manifest_write_jsonl(
        root / "raw" / "link.jsonl",
        [
            {
                "movement": "forward",
                "raw_ref": "raw:link:01",
                "raw_refs": link_raw_refs,
                "step_ref": f"{case_id}-work",
            },
            {
                "movement": "reroute",
                "movement_source": "recorded dynamic_walker_evidence reroute adoption record",
                "raw_ref": "raw:link-reroute:01",
                "raw_refs": ["raw:link-reroute:01"],
                "reroute_ref": f"reroute:{case_id}:1",
                "step_ref": f"{case_id}-work",
                "target": f"brick-{case_id}-repair",
            },
        ],
    )
    _adapter_error_manifest_write_json(
        root / "raw" / "raw-manifest.json",
        {
            "building_id": case_id,
            "raw_refs": manifest_top_refs,
            "entries": [
                _adapter_error_manifest_entry("raw/brick-work.jsonl", "Brick", ["raw:brick:01"]),
                _adapter_error_manifest_entry("raw/agent-return.jsonl", "Agent", ["raw:agent:01"]),
                _adapter_error_manifest_entry("raw/link.jsonl", "Link", manifest_link_refs),
            ],
        },
    )
    _adapter_error_manifest_write_json(
        root / "evidence" / "evidence-manifest.json",
        {"building_id": case_id, "proof_limits": ["support evidence only"]},
    )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "brick" / "work_contract.json",
        "Brick",
        "brick-work:01",
        "raw:brick:01",
        {"work_statement": "fixture work"},
    )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "agent" / "returned_claims.json",
        "Agent",
        "agent-fact:01",
        "raw:agent:01",
        {"received_work": "brick-work:01", "returned_payload_ref": "fixture:return"},
    )
    for rel, fact_ref, raw_ref in (
        ("transfer_trace.json", "link-transfer:01", "raw:link:01"),
        ("carry_trace.json", "link-carry:01", "raw:link:01"),
        ("sufficiency_trace.json", "link-sufficiency:01", "raw:link:01"),
        ("movement_trace.json", "link-movement:01", "raw:link:01"),
    ):
        _adapter_error_manifest_write_claim(
            root / "evidence" / "claim_trace" / "link" / rel,
            "Link",
            fact_ref,
            raw_ref,
            {"link_ref": fact_ref},
        )
    _adapter_error_manifest_write_claim(
        root / "evidence" / "claim_trace" / "link" / "movement_trace.json",
        "Link",
        "link-movement-reroute:01",
        "raw:link-reroute:01",
        {
            "movement": "reroute",
            "movement_source": "recorded dynamic_walker_evidence reroute adoption record",
            "target_boundary_ref": f"brick:brick-{case_id}-repair",
        },
    )


def _adapter_error_manifest_link_frontier_record(case_id: str) -> dict[str, Any]:
    return {
        "adapter_error_ref": f"adapter-error:{case_id}-closure:attempt-1",
        "frontier_kind": "agent_incomplete",
        "observed_boundary_ref": f"brick-{case_id}-closure",
        "raw_ref": "raw:link-frontier:02",
        "raw_refs": ["raw:link-frontier:02"],
        "step_ref": f"{case_id}-closure",
        "transition_record_created": False,
    }


def _adapter_error_manifest_entry(path: str, axis_owner: str, raw_refs: Sequence[str]) -> dict[str, Any]:
    return {
        "path": path,
        "source": "support/checkers synthetic fixture",
        "content_shape": "jsonl fixture rows",
        "proof_limit": "support evidence only",
        "axis_owner": axis_owner,
        "record_role": "primary",
        "raw_refs": list(raw_refs),
    }


def _adapter_error_manifest_write_claim(
    path: Path,
    axis: str,
    fact_ref: str,
    raw_ref: str,
    fact: Mapping[str, Any],
) -> None:
    _adapter_error_manifest_write_json(
        path,
        {
            "facts": [
                {
                    "axis": axis,
                    "fact": dict(fact),
                    "fact_ref": fact_ref,
                    "raw_refs": [raw_ref],
                    "proof_limits": ["support evidence only"],
                    "not_proven": ["checker fixture only"],
                }
            ]
        },
    )


def _adapter_error_manifest_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _adapter_error_manifest_write_jsonl(path: Path, values: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
            for value in values
        ),
        encoding="utf-8",
    )


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
    needle = "def run_adapter_error_path_hardening(repo: Path) -> KernelResult:"
    poisoned = "def run_adapter_error_path_hardening_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError("adapter_error mutation probe could not find path-hardening entrypoint")

    backup = tempfile.NamedTemporaryFile(
        prefix=".adapter-error-check.",
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
                "adapter_error mutation probe did not turn building_automation profile RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_building_automation_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "adapter_error mutation probe restored source but building_automation "
            f"remained RED:\n{excerpt}"
        )

    return [
        "adapter-error mutation RED probe passed: disabling the moved "
        "run_adapter_error_path_hardening entrypoint made check_profile.py "
        "--profile building_automation exit non-zero, then restoring the "
        "temp-backed self file returned building_automation to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for adapter-error frontier hardening."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved "
            "run_adapter_error_path_hardening entrypoint, assert "
            "building_automation profile exits RED, restore from a temp backup, "
            "then assert building_automation is GREEN"
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
            else [
                run_adapter_error_frontier_manifest_consistency(repo).output,
                run_adapter_error_path_hardening(repo).output,
            ]
        )
    except ProfileError as exc:
        print("adapter-error check rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

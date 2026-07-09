#!/usr/bin/env python3
"""Run flat declarative checker profiles.

This profile runner is support evidence only. It does not execute arbitrary
shell commands, execute arbitrary checker file paths, call providers, choose
Movement, or judge source truth, success, or quality.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib
import io
import json
import os
import signal
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# --- ELEGANT-REFACTOR P3a: the kernel-check bodies, declarative rule
# runners, behavioral case runners, and the YAML-subset parser were lifted
# into the brick_protocol/support/checkers/lib/ sublayer (engine blueprint 0531 §5 /
# detail-design §D-4 Opt B). This module stays the THIN FACADE: profile
# load + validate, RULE_RUNNERS, run_kernel_check dispatch, the self-test,
# and the CLI. The public names are re-exported below so external importers
# and the structure_template_integrity pins are unchanged.
#
# P3a-FIX-1: the lifted `from support.checkers.lib.*` imports below run at
# module-load time, BEFORE the per-run repo-root sys.path bootstrap further
# down. Pre-decomposition this module had no top-level `support.*` import, so
# the canonical gate `PYTHONPATH=brick_protocol/support/import_identity python3
# brick_protocol/support/checkers/check_profile.py --all` (no repo-root on PYTHONPATH) worked.
# To preserve that public command surface after C2 import-unify, bootstrap the
# checkout repo root (this file's parents[3]) onto sys.path before lib imports.
# The physical `brick_protocol/` tree is now the package root; there is no
# separate support/import_identity package-dir shim.
import os.path as _osp

_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__)))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from brick_protocol.support.checkers.lib.yaml_subset import (
    ProfileError,
    KernelResult,
    strip_comment,
    yaml_lines,
    parse_scalar,
    split_mapping_item,
    looks_like_mapping_item,
    parse_yaml_subset,
    require_mapping,
    require_string,
    require_string_list,
    to_repo_path,
    to_posix,
    extract_path,
    json_path_exists,
    rule_items,
    load_yaml_subset_file,
)
from brick_protocol.support.checkers.lib.rule_runners import (
    run_path_exists,
    run_path_absent,
    run_path_absent_glob,
    run_path_allowlist,
    text_rule,
    run_yaml_literal_set,
    run_json_required_paths,
    run_json_value_paths,
    run_agent_resource_boundary,
    run_agent_preferred_adapter_rejects,
    run_agent_resource_retired_ref_rejects,
    run_building_plan_boundary,
    run_route_policy_boundary,
    validate_building_plan_boundary,
    validate_route_policy_boundary,
)
from brick_protocol.support.checkers.lib.case_runners import (
    assert_checker_vessel_patch_closure,
    _assert_temp_vessel_guard_teeth,
    run_adapter_capability_rehome_case,
    run_casting_node_carry,
    run_hook_registry_axis_case,
    run_adapter_model_selection_case,
    run_adapter_model_selection_rejects,
    run_route_materialization_case,
    run_transition_concern_disposition_case,
    run_materialize_building_intent_case,
    run_materialize_building_intent_rejects,
    run_preset_building_completion_case,
    run_adapter_gate_shape_union_case,
    run_building_intake_seam_case,
    run_intake_evidence_projection_case,
    run_intake_project_vessel_case,
    run_link_route_evidence_case,
    run_once_task_source_admission_case,
    run_onboard_seam_case,
    run_operator_correction_case,
    run_agent_candidate_packet_case,
    run_preset_ranking_packet_case,
    run_declared_step_template_plan_case,
    run_declared_step_template_plan_rejects,
    run_compose_building_case,
    run_compose_building_rejects,
    run_write_scope_default_exclude_case,
    run_source_fact_body_carry_case,
    run_wiki_carry_truncation_survival_case,
    run_step_output_drain_case,
    run_step_output_drain_rejects,
    run_auto_repair_replay_case,
    run_plan_expansion_case,
    run_child_building_candidate_case,
    run_native_dispatch_close_case,
    run_workflow_import_case,
    run_fail_fixture_rejects,
    run_gate_sequence_policy_case,
    run_gate_sequence_policy_rejects,
    run_building_lifecycle_case,
    run_building_lifecycle_rejects,
)
from brick_protocol.support.checkers.lib.kernel_checks import (
    run_axis_vocab_drift,
    call_main,
    run_building_map_graph,
    run_building_plans_boundary_sweep,
    run_agent_adapter_return_shape,
    run_provider_preflight,
    run_building_result_summary,
    run_deliverable_crosscheck_gate,
    run_re_instruction_endline_gate,
    run_codex_connect_stall_classification,
    run_design_ai_text_seams,
    run_gemini_local_only_adapter,
    run_graph_topology_fan_barrier,
    run_onboard_smoke,
    run_install_script_lint,
    run_release_gate_contract,
    run_release_export_exclusion,
    run_product_no_smith_residue,
    run_reporter_notification_projection,
    run_chat_session_park_seam,
    run_adapter_error_frontier_manifest_consistency,
    run_adapter_error_path_hardening,
    run_raw_evidence_stream_scrub,
    run_agent_output_text_preservation,
    run_mcp_stdio_smoke,
    run_connect_config_launch,
    run_codex_projection_native,
    run_claude_projection_native,
    run_agent_session_id_redaction,
    run_dashboard_productization_projection,
    run_brick_cli_entrypoint_smoke,
    run_customer_project_progress_cli,
    run_sakana_wire_packet,
    run_building_call_authoring_contract,
    run_building_call_direct_escape_contract,
    run_building_call_lowering_contract,
)
from brick_protocol.support.checkers.lib.mutation_red_manifest_check import run_mutation_red_manifest
from brick_protocol.support.checkers.lib.install_release_export_lint_check import run_wheel_smoke
from brick_protocol.support.checkers.check_import_identity_modes import run_import_identity_modes


PROFILE_SCHEMA = "checker-profile/v1"
PROOF_LIMIT = (
    "proof limit: profile runner support evidence only; checker/profile pass "
    "does not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or complete checker consolidation."
)
LIVE_INBOX_FIXTURE_PACKET_GLOB = "checker-projection-fixture-vessel-*.json"
CHECKER_PROFILE_SWEEP_ENV = "BRICK_CHECKER_PROFILE_SWEEP"


def live_inbox_fixture_packet_count(repo: Path) -> int:
    inbox = repo / "project" / "brick-protocol" / "status" / "inbox"
    if not inbox.is_dir():
        return 0
    return sum(1 for path in inbox.glob(LIVE_INBOX_FIXTURE_PACKET_GLOB) if path.is_file())


def assert_all_profiles_did_not_write_live_fixture_inbox(
    repo: Path, before: int
) -> None:
    after = live_inbox_fixture_packet_count(repo)
    if after == before:
        return
    raise ProfileError(
        f"--all rejected evidence: live repo inbox {LIVE_INBOX_FIXTURE_PACKET_GLOB!r} "
        f"count changed from {before} to {after}; checker profiles must not write "
        "project/brick-protocol/status/inbox"
    )


@contextlib.contextmanager
def _checker_profile_sweep_env() -> Any:
    previous = os.environ.get(CHECKER_PROFILE_SWEEP_ENV)
    os.environ[CHECKER_PROFILE_SWEEP_ENV] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(CHECKER_PROFILE_SWEEP_ENV, None)
        else:
            os.environ[CHECKER_PROFILE_SWEEP_ENV] = previous


def _ensure_repo_import_path(repo: Path) -> None:
    """Prefer the inspected checkout for checker-time brick_protocol imports."""
    for entry in (repo / "brick_protocol" / "support" / "import_identity", repo):
        entry_text = str(entry)
        if entry_text in sys.path:
            sys.path.remove(entry_text)
        sys.path.insert(0, entry_text)


def _evict_foreign_brick_protocol_modules(repo: Path) -> None:
    repo_root = repo.resolve()
    import_root = (repo / "brick_protocol" / "support" / "import_identity").resolve()
    for name, module in list(sys.modules.items()):
        if name != "brick_protocol" and not name.startswith("brick_protocol."):
            continue
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        try:
            resolved = Path(module_file).resolve()
        except OSError:
            continue
        if resolved.is_relative_to(repo_root) or resolved.is_relative_to(import_root):
            continue
        del sys.modules[name]
PROFILE_DIR = Path("brick_protocol/support/checkers/profiles")
BASE_TOP_LEVEL_KEYS = frozenset(
    {
        "schema",
        "profile_id",
        "description",
        "kernel_checks",
        "proof_limits",
        "not_proven",
    }
)
RULE_RUNNERS: Mapping[str, Callable[[Path, Mapping[str, Any]], int]] = {
    "path_exists": run_path_exists,
    "path_absent": run_path_absent,
    "path_absent_glob": run_path_absent_glob,
    "path_allowlist": run_path_allowlist,
    "text_contains": lambda repo, profile: text_rule("text_contains", repo, profile),
    "text_absent": lambda repo, profile: text_rule("text_absent", repo, profile),
    "yaml_literal_set": run_yaml_literal_set,
    "json_required_paths": run_json_required_paths,
    "json_value_paths": run_json_value_paths,
    "agent_resource_boundary": run_agent_resource_boundary,
    "agent_preferred_adapter_rejects": run_agent_preferred_adapter_rejects,
    "agent_resource_retired_ref_rejects": run_agent_resource_retired_ref_rejects,
    "adapter_capability_rehome_case": run_adapter_capability_rehome_case,
    "hook_registry_axis_case": run_hook_registry_axis_case,
    "adapter_model_selection_case": run_adapter_model_selection_case,
    "adapter_model_selection_rejects": run_adapter_model_selection_rejects,
    "building_plan_boundary": run_building_plan_boundary,
    "route_policy_boundary": run_route_policy_boundary,
    "route_materialization_case": run_route_materialization_case,
    "transition_concern_disposition_case": run_transition_concern_disposition_case,
    "materialize_building_intent_case": run_materialize_building_intent_case,
    "materialize_building_intent_rejects": run_materialize_building_intent_rejects,
    "preset_building_completion_case": run_preset_building_completion_case,
    "adapter_gate_shape_union_case": run_adapter_gate_shape_union_case,
    "building_intake_seam_case": run_building_intake_seam_case,
    "intake_evidence_projection_case": run_intake_evidence_projection_case,
    "intake_project_vessel_case": run_intake_project_vessel_case,
    "link_route_evidence_case": run_link_route_evidence_case,
    "run_once_task_source_admission_case": run_once_task_source_admission_case,
    "onboard_seam_case": run_onboard_seam_case,
    "operator_correction_case": run_operator_correction_case,
    "agent_candidate_packet_case": run_agent_candidate_packet_case,
    "preset_ranking_packet_case": run_preset_ranking_packet_case,
    "compose_building_case": run_compose_building_case,
    "compose_building_rejects": run_compose_building_rejects,
    "write_scope_default_exclude_case": run_write_scope_default_exclude_case,
    "source_fact_body_carry_case": run_source_fact_body_carry_case,
    "wiki_carry_truncation_survival_case": run_wiki_carry_truncation_survival_case,
    "step_output_drain_case": run_step_output_drain_case,
    "step_output_drain_rejects": run_step_output_drain_rejects,
    "declared_step_template_plan_case": run_declared_step_template_plan_case,
    "declared_step_template_plan_rejects": run_declared_step_template_plan_rejects,
    "auto_repair_replay_case": run_auto_repair_replay_case,
    "plan_expansion_case": run_plan_expansion_case,
    "child_building_candidate_case": run_child_building_candidate_case,
    "native_dispatch_close_case": run_native_dispatch_close_case,
    "workflow_import_case": run_workflow_import_case,
    "fail_fixture_rejects": run_fail_fixture_rejects,
    "gate_sequence_policy_case": run_gate_sequence_policy_case,
    "gate_sequence_policy_rejects": run_gate_sequence_policy_rejects,
    "building_lifecycle_case": run_building_lifecycle_case,
    "building_lifecycle_rejects": run_building_lifecycle_rejects,
}
RULE_KEYS = frozenset(RULE_RUNNERS)
TOP_LEVEL_KEYS = BASE_TOP_LEVEL_KEYS | RULE_KEYS

_REPO_ARG = object()


@dataclass(frozen=True)
class _CallMainKernel:
    check_id: str
    module_name: str
    argv: tuple[object, ...] | None

    def __call__(self, repo: Path) -> KernelResult:
        if self.argv is None:
            argv = None
        else:
            argv = [str(repo) if arg is _REPO_ARG else str(arg) for arg in self.argv]
        return call_main(self.check_id, self.module_name, argv)


def _repo_main(check_id: str, module_name: str, *extra_args: str) -> _CallMainKernel:
    return _CallMainKernel(check_id, module_name, ("--repo", _REPO_ARG, *extra_args))


def _run_package_path_admission(repo: Path) -> KernelResult:
    module = importlib.import_module("brick_protocol.support.checkers.check_package_path_admission")
    paths = module.collect_repo_paths(repo)
    violations = module.check_paths(paths)
    if violations:
        detail = "\n".join(f"- {violation}" for violation in violations)
        raise ProfileError(f"kernel check package_path_admission rejected evidence:\n{detail}")
    return KernelResult(
        check_id="package_path_admission",
        inspected=len(paths),
        output=(
            "package path admission passed: full repo path gate inspected "
            f"{len(paths)} path(s)."
        ),
    )


# A4 pure-kernel memoization (compress-ladder W1). KERNEL_PURE names the kernel
# checks that are repo-read-only and leave no process state behind, so a second
# call for the same (check_id, repo) is a pure function of the repo tree and can
# reuse the first KernelResult. This wave admits EXACTLY ONE pure kernel; any
# expansion is a separate admission with attached evidence. The cache is support
# evidence only: it changes no verdict, chooses no Movement, and (see
# run_kernel_check) is GREEN-only because a rejecting kernel raises ProfileError
# before the cache-store line is reached, so a RED is always re-measured.
KERNEL_PURE: frozenset[str] = frozenset({"package_path_admission"})
_KERNEL_MEMO: dict[tuple[str, str], KernelResult] = {}


KERNEL_DISPATCH: Mapping[str, Callable[[Path], KernelResult]] = {
    "axis_vocab_drift": run_axis_vocab_drift,
    # package_path_admission intentionally keeps the inline inspected-count body;
    # call_main would collapse inspected to 1 and lose the full path-gate meaning.
    "package_path_admission": _run_package_path_admission,
    "axis_contract_projection": _repo_main(
        "axis_contract_projection",
        "brick_protocol.support.checkers.check_axis_contract_projection",
    ),
    # HEART-PHASE0-EQUIVALENCE-CHECKER-0616. Executes the structural
    # equivalence guard IN-PROCESS over hand-built compose_building fixtures:
    # 3 accepted corpus shapes including two-fan-in, renamed-ref green, and
    # RED discrimination for wrong gate placement / closure policy drift /
    # missing fan-in group. While brick_protocol/support/operator/assembly.py is absent,
    # the true LHS assembly equivalence corpus logs an advisory skip; if the
    # front door appears, this check fails closed until wired to it.
    "assembly_equivalence": _repo_main(
        "assembly_equivalence",
        "brick_protocol.support.checkers.check_assembly_equivalence",
    ),
    "graph_draft_rules": _repo_main(
        "graph_draft_rules",
        "brick_protocol.support.checkers.check_graph_draft_rules",
    ),
    "building_call_authoring_contract": run_building_call_authoring_contract,
    "building_call_direct_escape_contract": run_building_call_direct_escape_contract,
    "building_call_lowering_contract": run_building_call_lowering_contract,
    "route_v2_views": _repo_main(
        "route_v2_views",
        "brick_protocol.support.checkers.check_route_v2_views",
    ),
    "preflight_injection_survival": _repo_main(
        "preflight_injection_survival",
        "brick_protocol.support.checkers.check_preflight_injection_survival",
    ),
    "declared_verifier_exists": _repo_main(
        "declared_verifier_exists",
        "brick_protocol.support.checkers.check_declared_verifier_exists",
    ),
    "axis_field_enum_parity": _repo_main(
        "axis_field_enum_parity",
        "brick_protocol.support.checkers.check_axis_field_enum_parity",
    ),
    "agentfact_single_home": _repo_main(
        "agentfact_single_home",
        "brick_protocol.support.checkers.check_agentfact_single_home",
    ),
    "building_root_anchor": _repo_main(
        "building_root_anchor",
        "brick_protocol.support.checkers.check_building_root_anchor",
    ),
    "catalog_reader_sync": _repo_main(
        "catalog_reader_sync",
        "brick_protocol.support.checkers.check_catalog_reader_sync",
    ),
    "agent_resource_resolution": _repo_main(
        "agent_resource_resolution",
        "brick_protocol.support.checkers.check_agent_resource_resolution",
    ),
    # E2 / S0 MIRROR-GUARD + SCATTER-GUARD. Executes the registry-driven axis
    # field-set single-source guard IN-PROCESS: AST-scans all of brick_protocol/support/ and
    # rejects any module that ENUMERATES a registered axis field-set (a
    # frozenset/set/tuple/list literal of its members, or a whole @dataclass whose
    # complete field-set equals it) anywhere except its ONE registered single
    # source (field_set_registry.yaml). Scatter-guard folded in: a registered
    # field-set has exactly one defining_module; a second definition is the same
    # RED. A single-field-by-name read (the explicit-adapter fail-close invariant)
    # is NOT a field-set enumeration and is never flagged. GUARD-FIRST: the
    # registry lists only field-sets single-sourced on the current tree, so this is
    # GREEN now and RED on a regression. A non-zero main() raises ProfileError, so
    # a re-added mirror makes --all EXIT non-zero. Imports no axis module; an
    # independent AST oracle.
    # Mutation-RED: add a second frozenset({"preferred_adapter_ref",
    # "preferred_model_ref"}) (or a @dataclass with exactly those two fields) in any
    # support module -> this kernel check RED -> --all RED.
    "axis_field_set_single_source": _repo_main(
        "axis_field_set_single_source",
        "brick_protocol.support.checkers.check_axis_field_set_single_source",
    ),
    # E2/S8 BUILDER-BYPASS-GUARD (STRUCTURE-DESIGN.md §7 guard 4 + §6). AST-scans
    # the builder entrypoints (assembly.py + onboard/driver/cli) and REDs if the
    # builder re-encodes an axis instead of consuming the API: (a) a PER-NODE
    # casting carrier (AgentSpec/BrickSpec dataclass, brick()/agent() function)
    # names a CASTING_FIELDS member (preferred_*/selected_*) as a scalar field/param
    # instead of threading the opaque casting bag; (b) a Gate/Concern/Adoption enum
    # hardcodes (>=2 of) an axis vocabulary (brick_protocol/link/spec GATE_CONCEPT_TOKENS +
    # ADOPTION_LITERALS, brick_protocol/agent/return_fact TRANSITION_CONCERN_KINDS) as literals
    # rather than deriving from it. The building-WIDE selection envelope
    # (ComposedGraph/assemble/intent dict) is NOT a per-node carrier, so a single
    # explicit building-wide selected_adapter_ref scalar there is not flagged.
    # GUARD-FIRST: green on the current tree (carriers thread the bag, enums are
    # axis-derived), RED on a NEW bypass. A non-zero main() raises ProfileError, so
    # a re-encoding makes --all EXIT non-zero. Imports the axis vocab read-only to
    # derive the member-sets it scans for; authors nothing.
    # Mutation-RED: re-add a named adapter/model scalar field to AgentSpec, or
    # `class Gate(Enum): STRICT_EVIDENCE = "strict-evidence"; COO_REVIEW =
    # "coo-review"` -> this kernel check RED -> --all RED.
    "builder_consumes_axis_api": _repo_main(
        "builder_consumes_axis_api",
        "brick_protocol.support.checkers.check_builder_consumes_axis_api",
    ),
    # E2 / S10 JUDGMENT-GUARD (G4) (STRUCTURE-DESIGN.md §7 guard 2 + §8 S10 row).
    # Executes the registry-driven support-no-axis-judgment guard IN-PROCESS:
    # AST-scans all of brick_protocol/support/ (operator/connection/etc.; checkers excluded as the
    # AST oracle source) and REDs if a module OUTSIDE a judgment family's declared
    # consumer set contains the relocated VERDICT SHAPE — a CONDITIONAL assignment
    # of a registered axis verdict FIELD to a registered verdict VALUE literal
    # (an IfExp ternary, or an assignment inside an if/elif branch). That is the
    # ladder/downgrade §4 moved to the owning axis (judgment_home.yaml maps each
    # family J6->Link, J10->Brick, J3->Agent, J5->Brick). An UNCONDITIONAL neutral
    # construction default (run.py observed_match_kind="unknown") and pure transport
    # of an already-decided value (reporter/driver re-emit frontier_kind) are NOT
    # verdicts and are never flagged. GUARD-FIRST: every family is relocated on the
    # current tree, so this is GREEN now and RED on a regression. A non-zero main()
    # raises ProfileError, so a re-inlined verdict makes --all EXIT non-zero. Imports
    # no axis module; an independent AST oracle.
    # Mutation-RED: re-add `observed_match_kind = "missing" if missing else ...` to a
    # support operator module (J10 downgrade), or an `elif ...: frontier_kind =
    # "complete"` ladder branch to a support module other than frontier_observation
    # (J6 ladder) -> this kernel check RED -> --all RED.
    "support_no_axis_judgment": _repo_main(
        "support_no_axis_judgment",
        "brick_protocol.support.checkers.check_support_no_axis_judgment",
    ),
    "bricks_spec_completeness": _repo_main(
        "bricks_spec_completeness",
        "brick_protocol.support.checkers.check_bricks_spec_completeness",
    ),
    "building_lifecycle_path_shape": _repo_main(
        "building_lifecycle_path_shape",
        "brick_protocol.support.checkers.check_building_lifecycle_path_shape",
    ),
    "resume_disposition_surface": _repo_main(
        "resume_disposition_surface",
        "brick_protocol.support.checkers.check_resume_disposition_surface",
    ),
    "resume_replay_disposition_mirror": _repo_main(
        "resume_replay_disposition_mirror",
        "brick_protocol.support.checkers.check_resume_replay_disposition_mirror",
    ),
    "resume_declaration": _repo_main(
        "resume_declaration",
        "brick_protocol.support.checkers.check_resume_declaration",
    ),
    "building_map_graph": run_building_map_graph,
    "graph_topology_fan_barrier": run_graph_topology_fan_barrier,
    # PROJECT-0 S1: every project/<id>/ vessel must declare its charter
    # (README.md) + machine declaration (project.json, closed keys,
    # non-empty direction). Runs IN-PROCESS with anti-tautology probes
    # (violating vessels incl. non-slug ids + a symlinked vessel, slug-law
    # seam parity, creation rollback)
    # (violating synthetic vessels must be rejected); a non-zero main()
    # raises ProfileError, so an undeclared project vessel drives --all RED.
    "project_declaration": _repo_main(
        "project_declaration",
        "brick_protocol.support.checkers.check_project_declaration",
    ),
    "rule13_durable_evidence_ref": _repo_main(
        "rule13_durable_evidence_ref",
        "brick_protocol.support.checkers.check_rule13_durable_evidence_ref",
    ),
    # CHARTER-INJECT (0618): the declared project vessel's README charter is
    # injected into EVERY role's runtime instruction packet (work/qa/closure
    # lanes), reaches the built codex+claude prompt, and stamps the charter_ref
    # evidence field. Runs IN-PROCESS over a synthetic declared vessel (brick_protocol/agent/
    # symlinked to the real axis) driving the REAL renderer. A non-zero main()
    # raises ProfileError, so a regressed/disabled charter injection (the 0%
    # gap the discipline audit found) drives --all RED. Mutation-RED witness:
    # disable _charter_resources -> every role + both providers RED.
    "charter_injection": _repo_main(
        "charter_injection",
        "brick_protocol.support.checkers.check_charter_injection",
    ),
    # Executes the standalone walker checker IN-PROCESS: imports + runs the
    # real dynamic graph walker over adapter:local fixtures (adopt within
    # budget / HOLD on exhaustion / nested shares budget). A non-zero
    # main() raises ProfileError, so a broken walker invariant makes
    # --all EXIT non-zero (no longer text-admitted only).
    "bounded_agent_proposed_routing_loop": _repo_main(
        "bounded_agent_proposed_routing_loop",
        "brick_protocol.support.checkers.check_bounded_agent_proposed_routing_loop0",
    ),
    # Executes the standalone D2 portfolio driver checker IN-PROCESS: imports
    # + drives the real brick_protocol/support/operator/driver.py over declared existing
    # adapter:local Building Plan refs, including the load-bearing negative
    # probes for bare default-transition and undeclared candidates.
    "building_operator_driver0": _repo_main(
        "building_operator_driver0",
        "brick_protocol.support.checkers.check_building_operator_driver0",
    ),
    # Parses driver.py __all__ without importing it: the only public
    # Building-making intake verb in driver remains run_building_intake;
    # run_composed_graph_intake stays callable by direct checker import but
    # is sealed out of the public ordering surface.
    "driver_public_intake_seal": _repo_main(
        "driver_public_intake_seal",
        "brick_protocol.support.checkers.check_driver_public_intake_seal",
    ),
    # CONNECT-STALL PRIMARY CURE (stdin 0619). Parses (AST, no import) the real
    # brick_protocol/support/connection/agent_adapter.py and asserts the two CLI-runner spawns
    # (_run_text_cli_command, _run_command) pass an immediate-EOF child input (the
    # DEVNULL guard) so a provider CLI that inherits an open-no-EOF input pipe cannot
    # block forever at startup (the connect-stall). FAILS CLOSED: a CLI-runner spawn
    # WITHOUT the DEVNULL guard makes main() return non-zero and raises ProfileError,
    # so --all EXITs non-zero. Includes an in-process mutation-RED (a spawn with the
    # guard removed is rejected). This is the PRIMARY cure; the TrackB watchdog stays
    # as defense-in-depth for genuine network hangs.
    "cli_runner_stdin_devnull": _repo_main(
        "cli_runner_stdin_devnull",
        "brick_protocol.support.checkers.check_cli_runner_stdin_devnull",
    ),
    # INSTALL-WIZARD-0623 (engine-native A1: MCP auto-wired). AST-parses (no import)
    # brick_protocol/support/connection/adapter_local_cli.py and asserts the brick-protocol MCP
    # config + the per-provider isolation lever are wired into BOTH dispatch branches
    # (claude: --mcp-config + --strict-mcp-config; codex: -c mcp_servers.* +
    # --ignore-user-config), reusing connect.py's single-source registration shape.
    # FAILS CLOSED: a branch missing its MCP wire / isolation lever makes main()
    # return non-zero and raises ProfileError, so --all EXITs non-zero. Proof-limit:
    # pins the WIRING shape only, NOT that a dispatched agent called a brick MCP tool
    # (a real tools/list round-trip stays NOT-PROVEN until a live dispatch).
    "mcp_dispatch_wire": _repo_main(
        "mcp_dispatch_wire",
        "brick_protocol.support.checkers.check_mcp_dispatch_wire",
    ),
    "provider_registry_ladder": _repo_main(
        "provider_registry_ladder",
        "brick_protocol.support.checkers.check_provider_registry_ladder",
    ),
    "interactive_provider_intake": _repo_main(
        "interactive_provider_intake",
        "brick_protocol.support.checkers.check_interactive_provider_intake",
    ),
    "sink_registry": _repo_main(
        "sink_registry",
        "brick_protocol.support.checkers.check_sink_registry",
    ),
    # F1 RETURN-FIELD MERGE-SET PARITY (return-LANDING binds to brick contract).
    # AST-parses (no import) brick_protocol/support/connection/adapter_grant_policy.py and
    # brick_protocol/support/connection/agent_adapter.py: every field in the structured-return
    # merge-set ({evidence_refs, not_proven, proof_limits} inside
    # _merge_structured_return_fields) MUST also be in _RETURN_LIST_FIELDS, so the
    # return normalizer list-normalizes (and dict-flattens) it BEFORE the merge
    # routes it through _merge_texts. A merge-set field absent from the list-set
    # (exactly how evidence_refs failed F1) lets an agent return it as a bare
    # Mapping and crashes the return-assembly BEFORE the AgentFact is written ->
    # zero step-evidence. FAILS CLOSED: a missing field makes main() return
    # non-zero and raises ProfileError, so --all EXITs non-zero. Includes an
    # in-process mutation-RED (drop a merge-set field from the list-set -> rejected).
    "return_field_merge_set_parity": _repo_main(
        "return_field_merge_set_parity",
        "brick_protocol.support.checkers.check_return_field_merge_set_parity",
    ),
    "declaration_enforcement_parity": _repo_main(
        "declaration_enforcement_parity",
        "brick_protocol.support.checkers.check_declaration_enforcement_parity",
    ),
    # F3 STEP-OUTPUT EVIDENCE FIELD-SET PARITY. AST-parses (no import)
    # brick_protocol/support/recording/step_outputs.py: the normal step-output manifest,
    # adapter-error record, and chat-session park record all carry the same
    # always-present evidence-shape fields through EVIDENCE_SHAPE_FIELDS and the
    # writer helper. task_source_ref remains an optional mirror outside the set.
    # Includes an in-process mutation-RED (drop one builder helper spread ->
    # rejected).
    "step_output_evidence_field_set_parity": _repo_main(
        "step_output_evidence_field_set_parity",
        "brick_protocol.support.checkers.check_step_output_evidence_field_set_parity",
    ),
    # F2 CHAINED-CARRY DEPENDENCY (brick-to-brick CARRY binds to brick contract).
    # Runs the real EASY-tier assemble() composition IN-PROCESS: every WRITE/QA
    # node (write_need=True step template -- work + the QA kinds) reached by a
    # forward edge from an upstream node MUST receive that upstream's step-output
    # as a declared source_fact carry (or be a fan-in convergence target the
    # walker auto-carries), so it does not run blind on the original task alone.
    # READ-ONLY / inspect / review / design / plan / closure nodes (write_need=
    # False) are EXEMPT (they legitimately depend only on the repo -> no false-RED).
    # This is the F2 fake-green regression pin: a downstream writer with no carry
    # sees only the task, changes nothing meaningful, and the walk greens anyway
    # (exactly how the perm-flip work node changed 0 files yet greened). FAILS
    # CLOSED: an unmet dependency raises and main() returns non-zero, so --all
    # EXITs non-zero. Includes an in-process mutation-RED (strip the auto-declared
    # carry from a write node -> the same invariant rejects it).
    "chained_carry_dependency": _repo_main(
        "chained_carry_dependency",
        "brick_protocol.support.checkers.check_chained_carry_dependency",
    ),
    # GATE-REGISTRY SINGLE-SOURCE (struct-surgery ② 0623; data-driven Link gate
    # registry). AST-seals the Link gate-ref VOCABULARY + the materializer
    # PLACEMENT rule to ONE data table -- brick_protocol/link/spec.GATE_REGISTRY (one row per
    # gate). RULE 1 rejects any collection literal of >= 2 link-gate: literals
    # outside brick_protocol/link/spec.py (a re-stated gate vocabulary -- the old
    # DECLARED_GATE_REFS-tuple shape that drifts from the registry), while leaving
    # a lone behavioral "if ref == link-gate:human" comparison clean. RULE 2
    # rejects the support placement helper _materializer_profile_gate_translations
    # if it does not delegate to gate_placement_for_row, or hand-authors placement
    # via translate_gate_concept guarded by row flags. The operator-adds-a-gate-by-
    # adding-a-row goal is only real if neither can be re-stated elsewhere. FAILS
    # CLOSED: an enumeration/authoring outside the registry makes main() return
    # non-zero and raises ProfileError, so --all EXITs non-zero. Includes an
    # in-process mutation-RED (a re-enumerated gate tuple + a hand-authored
    # placement helper are both rejected; a lone comparison is left clean).
    "gate_registry_single_source": _repo_main(
        "gate_registry_single_source",
        "brick_protocol.support.checkers.check_gate_registry_single_source",
    ),
    "gate_policy_action_single_source": _repo_main(
        "gate_policy_action_single_source",
        "brick_protocol.support.checkers.check_gate_policy_action_single_source",
    ),
    "positive_int_bool_boundary": _repo_main(
        "positive_int_bool_boundary",
        "brick_protocol.support.checkers.check_positive_int_bool_boundary",
    ),
    # AGENT-OBJECT SCHEMA SINGLE-SOURCE (③ struct-surgery 0623). AST-seals the
    # agent-OBJECT key/ref/forbidden SCHEMA to ONE source on the Agent axis —
    # brick_protocol/agent/spec.AGENT_OBJECT_SCHEMA (assembled over its _AGENT_OBJECT_REF_FIELDS +
    # _AGENT_OBJECT_FORBIDDEN_KEYS literals, with allowed_keys deriving the casting
    # names from CASTING_FIELDS) + the validate_agent_object_keys() gate the support
    # load path AND the inline agent() compose path both call. RULE 1 positively
    # asserts the schema, the two member literals (exact member-sets), and the gate
    # are defined on the axis; RULE 2 rejects any collection literal whose member-set
    # equals the 6-name ref-field set OR the 16-name forbidden-key set anywhere in
    # the axis/support trees except brick_protocol/agent/spec.py (a re-stated schema fragment — the
    # old _REF_FIELDS / forbidden-frozenset copies that were scattered across
    # agent_resources.py + primitives.py + native_dispatch.py, one of which had
    # OMITTED the casting keys and raised on a real role). A lone by-name read
    # (obj.get("adapter_refs")) can never equal a >=2-member set and is never
    # flagged. FAILS CLOSED: an enumeration outside the source makes main() return
    # non-zero and raises ProfileError, so --all EXITs non-zero. Includes an
    # in-process mutation-RED (a re-stated ref tuple + a re-stated forbidden frozenset
    # both rejected; a lone by-name read left clean).
    # Mutation-RED: re-add a frozenset/tuple of the six *_refs names (or the sixteen
    # forbidden keys) to any axis/support module -> this kernel check RED -> --all RED.
    "agent_object_schema_single_source": _repo_main(
        "agent_object_schema_single_source",
        "brick_protocol.support.checkers.check_agent_object_schema_single_source",
    ),
    # REPORT-ENV-AUTOLOAD (#56). Executes the report.env engine auto-loader
    # IN-PROCESS over TEMP env fixtures (never the operator's real ~/.brick
    # files, never the live os.environ): an allowlisted key from a 0600 file is
    # injected into a fresh env, a NON-allowlisted key is NOT (no blanket load),
    # a 0644 file is REFUSED with a typed observation, a pre-set key is preserved
    # (env precedence / operator env wins), and no credential VALUE is echoed.
    # Includes two in-process mutation-RED probes (defeat the 0600 gate -> the
    # 0644 file loads; widen the allowlist -> the non-allowlisted key loads), and
    # asserts the loader is wired at the run.py engine seam (run + resume). A
    # non-zero main() raises ProfileError, so a regressed gate/allowlist/seam
    # makes --all EXIT non-zero.
    "report_env_autoload": _repo_main(
        "report_env_autoload",
        "brick_protocol.support.checkers.check_report_env_autoload",
    ),
    # ADAPTER TOKEN-USAGE METER (TrackA-A1 INSTRUMENT FIRST 0619). Runs the
    # per-step adapter token-usage meter writer IN-PROCESS with fabricated usage
    # fixtures (NO live codex, NO child process) and AST-scans the real adapter +
    # step-output source. Asserts: the meter record carries only the allowlisted
    # token-counter keys with absent=null (graceful, never fabricated); AND the
    # gate-no-measure half -- token usage NEVER appears in AgentFact.returned (the
    # codex adapter builds `returned` with no usage key) or the per-step return
    # recording writer. Mutation-RED: a dropped allowlist key is rejected, and a
    # usage key assigned into `returned` is flagged. Applies NO cap (a cap is
    # TrackA-A2). A leak or dropped key makes main() return non-zero and raises
    # ProfileError, so --all EXITs non-zero. Reaches no axis module, judges nothing.
    "adapter_usage_meter": _repo_main(
        "adapter_usage_meter",
        "brick_protocol.support.checkers.check_adapter_usage_meter",
    ),
    "session_continuity_adapter": _repo_main(
        "session_continuity_adapter",
        "brick_protocol.support.checkers.check_session_continuity_adapter",
    ),
    # Executes the declaration-integrity checker IN-PROCESS: runs the three
    # anti-tautological negative probes (composition-mode, chain artifacts,
    # provenance<->returned acceptance) AND inspects every persisted building
    # root. A probe that is not rejected, or a real root that violates the
    # invariant, makes main() return non-zero and raises ProfileError, so
    # --all EXITs non-zero.
    "building_declaration_integrity": _repo_main(
        "building_declaration_integrity",
        "brick_protocol.support.checkers.check_building_declaration_integrity",
    ),
    # Global building-plan boundary sweep: runs validate_building_plan_boundary
    # over every linear plan in brick_protocol/brick/building_plans/, rehoming the per-profile
    # single-plan boundary pins into one general guard (pass-1 consolidation).
    "building_plans_boundary_sweep": run_building_plans_boundary_sweep,
    # Executes the required-return-shape waiver probe IN-PROCESS so the work
    # template's no_changes_reason wording cannot drift away from adapter
    # extraction or Brick comparison waiver behavior.
    "agent_adapter_return_shape": run_agent_adapter_return_shape,
    # ONBOARDING-PROVIDER-PREFLIGHT-0. Executes the friendly never-raising
    # provider preflight IN-PROCESS: imports preflight_provider and asserts it
    # returns a well-shaped status dict for an ACTIVE adapter + in-process
    # adapter:local, AND that it returns ok False (never raises) for a
    # deliberately bogus/retired adapter ref. If preflight_provider ever
    # raises (e.g. on a missing CLI), this kernel check goes RED and --all
    # EXITs non-zero. This is the no-raise guard for the onboarding "login"
    # step (a missing/unauthed provider must surface a plain-Korean message,
    # not a mid-run stack-trace).
    "provider_preflight": run_provider_preflight,
    # DESIGN-AI-TEXT-SEAM-0616. Executes the Claude/Codex prompt -> raw text
    # wrappers IN-PROCESS with mock command_runners only: normal raw text,
    # missing executable, timeout propagation, blank-output rejection, and
    # secret-output rejection. NO live provider CLI is called.
    "design_ai_text_seams": run_design_ai_text_seams,
    # CONNECT-STALL CLASSIFICATION (TrackB 0619). Pins the codex DEAD-worker label
    # split IN-PROCESS with mock fixtures only (NO live CLI, NO 20-min wait): the
    # default stall threshold sits in the 90-180s fast-fail band (env override +
    # NaN/neg/zero guards intact); a dead-connection signature fast-fails WITHIN the
    # threshold and maps to the distinct 'local_cli_connect_stall' kind while a plain
    # timeout stays 'local_cli_timeout'; both route to the SAME adapter_error_frontier
    # HOLD with NO auto-retry/scheduler token; and the reap journal carries the last
    # health triple + dead_signature_seconds as support facts only. Mutation-RED:
    # re-flatten _adapter_error_kind (stall -> local_cli_timeout) or restore the
    # ~20-min default threshold -> RED.
    "codex_connect_stall_classification": run_codex_connect_stall_classification,
    # FUGU-PACKET-0706: fixture-only prompt rendering proves sakana/codex-fugu-local
    # removes Agent resource path labels from the provider wire packet while
    # keeping the local evidence packet's ref->path mapping and preserving
    # codex-local resource path labels. Mutation-RED: re-expose a path on a sakana
    # resource row -> RED. No live provider CLI.
    "sakana_wire_packet": run_sakana_wire_packet,
    # CR.P1.GEMINI_LOCAL_ONLY. Executes in-process adapter admission probes:
    # adapter:gemini-local remains the only active Gemini customer adapter and
    # stays a local Gemini CLI + API-key env path; adapter:gemini-api is retired
    # from active admission, capability tables, model provider tables, Agent
    # Objects, and dispatch.
    "gemini_local_only_adapter": run_gemini_local_only_adapter,
    # ONBOARDING-WIZARD-0. Executes the friendly never-raising onboarding flow
    # IN-PROCESS: imports run_onboard and drives the bundled adapter:local
    # example Building END-TO-END to a TEMP output_root (never the repo),
    # asserting it returns the structured {preflight, connect_hint,
    # example_result, handoff_message_ko, ok} dict with ok True + a building_id
    # + landed evidence, AND returns ok False (never raises) for a bogus host.
    # If run_onboard ever raises, this kernel check goes RED and --all EXITs
    # non-zero. This is the no-raise guard for the guided onboarding experience.
    "onboard_smoke": run_onboard_smoke,
    "building_result_summary": run_building_result_summary,
    "deliverable_crosscheck_gate": run_deliverable_crosscheck_gate,
    "re_instruction_endline_gate": run_re_instruction_endline_gate,
    # ONBOARDING-INSTALL-SCRIPT-0. Structural/safety lint of the one-line
    # installer brick_protocol/support/onboarding/install.sh IN-PROCESS: asserts set -eu, all
    # logic in main() invoked as 'main "$@"' on the LAST non-empty line
    # (anti-truncation), no http:// (HTTPS only), no /Users/ literal, no inline
    # secret pattern, and a reference to the onboard wizard entry. A violation
    # makes main() return non-zero and raises ProfileError, so --all EXITs
    # non-zero. PROOF LIMIT: structure/safety only -- it does NOT prove a real
    # fresh-machine install (clone/uv sync/provider auth = manual / Phase-4).
    "install_script_lint": run_install_script_lint,
    # RELEASE-EXPORT-0. Structural exclusion pin for the clean public export
    # verb: project/ local evidence and brick_protocol.egg-info/ build
    # metadata must not ship, and publication stays as printed follow-up
    # commands. Includes a temp mutation that removes project/ and must RED.
    "release_export_exclusion": run_release_export_exclusion,
    "release_gate_contract": run_release_gate_contract,
    "wheel_smoke": run_wheel_smoke,
    # ONBOARDING-LEGACY-SCRUB-0612. Scans shipped newcomer-facing surfaces
    # (README.md, brick_protocol/support/docs/spec, brick_protocol/agent/prompts) for Smith local residue:
    # no Smith user-home literal and no hardcoded Smith GitHub org outside
    # the README working-example allowance. Runs temp-copy FIRE probes for
    # both forbidden families; a non-firing probe makes --all exit non-zero.
    "product_no_smith_residue": run_product_no_smith_residue,
    # Executes reporter validation probes IN-PROCESS. This keeps the profile
    # from merely text-pinning the presence of probe functions while never
    # observing that authority-leaking packets and unadmitted sinks reject.
    "reporter_notification_projection": run_reporter_notification_projection,
    # Executes the dashboard productization guard IN-PROCESS: production
    # /ingest fail-closed static lint with mutated-copy FIRE, deploy literal
    # hygiene with synthetic hardcoded project/URL probes, and the synchronous
    # bake verb round-trip with a source_truth mutation RED case.
    "dashboard_productization_projection": run_dashboard_productization_projection,
    # Executes the chat-session S1 PARK seam IN-PROCESS over a temp project
    # Building root: declared adapter:chat-session must write a closed
    # AgentAdapterRequest envelope + distinct park record, stop before any
    # AgentFact, observe frontier_kind=chat_session_parked before incomplete,
    # map to the reporter intervention bell, and pass both lifecycle/path
    # admission checkers on the generated support evidence.
    "chat_session_park_seam": run_chat_session_park_seam,
    "adapter_error_frontier_manifest_consistency": run_adapter_error_frontier_manifest_consistency,
    "adapter_error_path_hardening": run_adapter_error_path_hardening,
    "raw_evidence_stream_scrub": run_raw_evidence_stream_scrub,
    "agent_output_text_preservation": run_agent_output_text_preservation,
    # P1 brick CLI entrypoint. Externally observes brick_protocol/support/operator/cli.py from
    # outside the repo with PYTHONPATH unset, both as a direct script and through
    # the import-identity package route that mirrors console_script startup. It
    # then imports an existing bare-support module to prove the CLI bootstrap
    # inserted repo root before support seams are loaded. Removing the two
    # sys.path.insert bootstrap lines drives this RED with ModuleNotFoundError.
    "brick_cli_entrypoint_smoke": run_brick_cli_entrypoint_smoke,
    "customer_project_progress_cli": run_customer_project_progress_cli,
    "import_identity_modes": run_import_identity_modes,
    # P3 first-use wizard. Executes the brick init FIRST_USE.md branch
    # IN-PROCESS with simulated doctor/build packets and a temp output root:
    # generated FIRST_USE.md must carry the example-stub disclaimer, the
    # `brick auth login` + `--real-provider` funnel, and the CLI must print
    # "next: read FIRST_USE.md". The checker also mutates the generated temp
    # file by removing the disclaimer and requires that validation reject it;
    # simulated build_error must write no FIRST_USE.md.
    "first_use_wizard": _repo_main(
        "first_use_wizard",
        "brick_protocol.support.checkers.check_first_use_wizard",
    ),
    # Execution smoke: bare-launches brick_protocol/support/connection/mcp_projection.py with
    # a CLEAN env (no PYTHONPATH) like a real MCP host and asserts it answers
    # initialize without crashing at import. Catches the bootstrap regression
    # where the script forgets to put brick_protocol/support/import_identity on sys.path and
    # crashes with ModuleNotFoundError: brick_protocol on a bare host launch.
    # The external bare-launch lives in the checker layer (kernel_checks.py),
    # never in mcp_projection.py, which owns no execution surface.
    "mcp_stdio_smoke": run_mcp_stdio_smoke,
    # R9-MODELLANE-0708. Executes the Agent discipline reconciliation pin
    # IN-PROCESS: the model-lane discipline must preserve the 0702
    # codex/sonnet/gemini defaults while retiring active fable dispatch,
    # pinning Opus 4.8 for Claude design / important QA, and keeping the fugu
    # high-depth tier. The checker carries built-in mutation-RED probes for
    # removing the retirement row or reintroducing active fable allowance.
    "model_lane_matching_discipline": _repo_main(
        "model_lane_matching_discipline",
        "brick_protocol.support.checkers.check_model_lane_matching_discipline",
    ),
    # Execution proof for the CONNECT-GENERATOR-0 read-only generator: imports
    # brick_protocol/support/connection/connect.py, renders the Codex MCP config for THIS
    # repo, extracts the command + server script + --repo it emits, then
    # externally launches EXACTLY that with a CLEAN env (no PYTHONPATH) and
    # pipes one initialize. Asserts a JSON-RPC result with no crash, that the
    # emitted script == <repo>/support/connection/mcp_projection.py (and
    # exists), and that connect.py source carries no hardcoded user-home path.
    # This proves "generated config -> actually working connection". The
    # external launch lives in the checker layer; connect.py runs none.
    "connect_config_launch": run_connect_config_launch,
    # Execution proof that the Claude projection is a REAL Claude-native .md
    # subagent (--- YAML frontmatter --- + body), not a label-only generic
    # blob. Imports the read-only renderer (brick_protocol/support/connection/
    # agent_resources.py) and asserts over admitted Agent Objects: (a)
    # render_claude_subagent_md parses with name/description/tools in the
    # frontmatter; (b) a REAL tool-policy -> tools mapping (dev read-write-
    # scoped tools INCLUDE Edit AND Write; a leader/reviewer EXCLUDES both),
    # so a constant tools list turns this RED; (c) the claude .md is
    # materially DIFFERENT from the codex TOML (markdown, not a TOML table);
    # (d) the "enforced by Brick MCP" honesty note is present in the body.
    # The renderer it pins spawns no external process and writes no file; the
    # checker imports it in-process.
    "claude_projection_native": run_claude_projection_native,
    # Execution proof that the Codex projection is a REAL Codex-native TOML
    # subagent, not a label-only generic blob. Imports the read-only renderer
    # (brick_protocol/support/connection/agent_resources.py) and asserts over admitted Agent
    # Objects: (a) render_codex_subagent_toml parses as valid TOML with the
    # required name/description/developer_instructions; (b) sandbox_mode is a
    # REAL tool-policy mapping (read-write-scoped dev -> workspace-write;
    # leader/reviewer read-only policies -> read-only), so a constant
    # sandbox_mode turns this RED; (c) the codex TOML is materially DIFFERENT
    # from the claude markdown seed; (d) developer_instructions carries the
    # "enforced by Brick MCP" honesty note. The renderer it pins spawns no
    # external process and writes no file; the checker imports it in-process.
    "codex_projection_native": run_codex_projection_native,
    # Executes the standalone zeta6 checker IN-PROCESS: derives the dynamic-walker
    # evidence shape from brick_protocol/support/recording/contracts.py and runs the real
    # walk, catching contract-required-field drift AND independent axis-value
    # drift. A non-zero main() raises ProfileError, so an evidence-contract
    # regression makes --all EXIT non-zero.
    "recording_checker_derived_contract": _repo_main(
        "recording_checker_derived_contract",
        "brick_protocol.support.checkers.check_recording_checker_derived_contract",
    ),
    # FAULT-SEPARATION gate-no-measure half (0618). Executes the link-gate
    # measurement-separation seal IN-PROCESS: AST-scans brick_protocol/link/gate.py and rejects
    # any import of the Brick measurement module/symbol (brick_protocol/brick/comparison.py
    # BrickComparisonFact, the brick_comparison crossing) or any
    # construction/derivation of that measurement -- the gate JUDGES sufficiency
    # and must never re-compute the measurement it reads (string-form public-fact
    # references stay allowed). A built-in synthetic mutation-RED probe asserts a
    # gate body that imports + constructs the measurement is rejected; a non-zero
    # main() raises ProfileError, so a measurement leak into the gate makes --all
    # EXIT non-zero. Parses gate.py, imports no axis module, judges nothing.
    "link_gate_measurement_separation": _repo_main(
        "link_gate_measurement_separation",
        "brick_protocol.support.checkers.check_link_gate_measurement_separation",
    ),
    # FAULT-SEPARATION fan-out sibling-evidence independence (F1, the 0609
    # cross-vouch invariant, 0618). Executes the byte-distinctness guard
    # IN-PROCESS over a self-contained synthetic building-map fixture: a parent
    # that fans out to siblings whose returned-evidence bodies (AgentFact /
    # claim_trace) are all byte-distinct passes, while copying one fan-out
    # sibling's body onto a SAME-PARENT sibling (the cross-vouch leak) is
    # rejected. Scoped to fan-out siblings only (sequential/chain carry-sharing +
    # parent->child sharing excluded). A non-zero main() raises ProfileError, so
    # a weakened guard makes --all EXIT non-zero. Reaches no axis module, judges
    # nothing; complements the walker_kernel structural defence (0609).
    "fan_out_sibling_evidence_independence": _repo_main(
        "fan_out_sibling_evidence_independence",
        "brick_protocol.support.checkers.check_fan_out_sibling_evidence_independence",
    ),
    # ELEGANT-REFACTOR P-guard. Executes the elegance guard IN-PROCESS: runs
    # the six anti-tautological G1-G6 negative probes AND validates the live
    # crossing_registry.yaml + module_registry.yaml + the support module
    # tree (one canonical contract per crossing, no mixing, cross-via-
    # canonical-only, every module registered, consume-not-author,
    # decomposition ceiling - a self-consistency check, not a one-way
    # ratchet; see check_axis_crossing_elegance G6 proof-limit). A probe
    # that is not rejected, or a real
    # registry/code violation, makes main() return non-zero and raises
    # ProfileError, so --all EXITs non-zero. Independent oracle: this checker
    # imports no axis module (and is not imported here in a way that would).
    "axis_crossing_elegance": _repo_main(
        "axis_crossing_elegance",
        "brick_protocol.support.checkers.check_axis_crossing_elegance",
    ),
    # HALF-2 Tier A. Executes the conformance harness IN-PROCESS: runs the
    # anti-tautological FIRE probe (a degraded copy with the reroute trace and
    # declaration_provenance dropped MUST be reported unmet) AND asserts the
    # engine-produced tier-a-3axis-conformance-0 root carries all three axes +
    # Link mechanics + evidence + declaration_provenance. A probe that does not
    # fire, or an unmet assertion, makes main() return non-zero and raises
    # ProfileError, so --all EXITs non-zero. This is the deterministic
    # regression net re-run after each P3 extraction.
    "tier_a_three_axis_conformance": _repo_main(
        "tier_a_three_axis_conformance",
        "brick_protocol.support.checkers.check_tier_a_three_axis_conformance",
    ),
    # BRICK-TEMPLATE-CATALOG-RESTRUCTURE-0 P10 checker/FIRE closure. Executes
    # the split catalog checker IN-PROCESS: synthetic RED-first FIRE fixtures
    # prove stable problem codes, while live enforcement reads split
    # step_template_catalog.rows as active binding evidence after old compact
    # registry deletion. Link refs anchor in brick_protocol/link/gate.py,
    # Agent refs in brick_protocol/agent/objects payloads, link_word in brick_protocol/link/movement.py,
    # and checker output remains support evidence only.
    "brick_template_catalog_restructure": _repo_main(
        "brick_template_catalog_restructure",
        "brick_protocol.support.checkers.check_brick_template_catalog_restructure",
        "--mode",
        "p10-delete",
    ),
    # U5.5 SLICE-1A. Executes the spine structural checker IN-PROCESS over
    # every persisted building root: for each building tagged
    # evidence_generation == u5_5_live it verifies pairing (.md ==
    # render(.json)), the content/prev hash chain, monotonic sequence_index +
    # run_segment, spine.json/.jsonl/.md == re-derived from events/, admitted
    # event types + axis scope, and no forbidden success/quality key.
    # Untagged (pre-U5.5) buildings are skipped, so existing evidence is
    # untouched. A real spine violation makes main() return non-zero and
    # raises ProfileError, so --all EXITs non-zero.
    "evidence_spine": _repo_main(
        "evidence_spine",
        "brick_protocol.support.checkers.check_evidence_spine",
    ),
    # U5.5 SLICE-2. Executes the spine PROJECTION-completeness checker
    # IN-PROCESS over every persisted building root: for each building tagged
    # evidence_generation == u5_5_live it verifies the spine projection covers
    # the building-scope declarations (exactly one each of PresetExpansion and
    # LinkLaunchPolicy in events/). This is the coverage guard, complementary
    # to evidence_spine (the structural guard). Untagged (pre-U5.5) buildings
    # are skipped, so existing evidence is untouched. A real coverage gap makes
    # main() return non-zero and raises ProfileError, so --all EXITs non-zero.
    "evidence_spine_projection": _repo_main(
        "evidence_spine_projection",
        "brick_protocol.support.checkers.check_evidence_spine_projection",
    ),
    "plan_revision_chain": _repo_main(
        "plan_revision_chain",
        "brick_protocol.support.checkers.check_plan_revision_chain",
    ),
    # A+ W2 mutation-RED manifest gate. Fails closed when an allowlisted surface
    # row disappears or points at a non-existent fixture/probe literal.
    "mutation_red_manifest": run_mutation_red_manifest,
    # TREASURE PORT 1 (ACTIVE-SPEC-SPINE disciplines, concept-lifted from
    # d5bc86e:brick_protocol/support/checkers/check_doc_grounding.py). Executes the
    # pin-estate checker IN-PROCESS: (a) rejects decorative history-doc pins
    # (path-existence-only / blank needles / keyless json_required_paths),
    # (b) runs adversarial pin probes (temp copy of the pinned doc, mutate
    # the pinned text, the REAL text_rule runner must RED - proving the
    # surviving KEEP-LIVE/GUARD-ONLY pins actually fire), and (c) enforces
    # the pin-estate ratchet (estate count changes - path_exists/path_absent
    # items, text_contains/text_absent blocks, and json_required_paths
    # blocks on the history prefixes - vs brick_protocol/support/checkers/
    # pin_estate_baseline.yaml without a new dated human disposition entry
    # RED; tamper-EVIDENT, not tamper-proof - see the checker docstring).
    # Six synthetic FIRE probes run RED-first on every invocation; a
    # non-rejecting probe makes main() return non-zero, so --all EXITs
    # non-zero.
    "pin_estate_integrity": _repo_main(
        "pin_estate_integrity",
        "brick_protocol.support.checkers.check_pin_estate_integrity",
    ),
    # TREASURE PORT 2 (lifted from 2d44fc7:brick_protocol/support/checkers/lib/
    # kernel_checks.py run_agent_session_id_redaction). Forbids any
    # provider/runtime session id (bare UUID/ULID, keyed session_id/
    # conversation_id forms, sess_/sess-/provider-session-/resume-token-/
    # chatcmpl-/ya29./JWT tokens) in the kernel/buildings/reviews/archive
    # surfaces. Operator policy 0611: frozen building evidence and archived
    # history are NOT rewritten; the 6 investigator-verified legacy leak
    # files are carried on an explicit per-path allowlist of frozen
    # line-content sha256[:16] hashes (codex-review tightening C: every
    # offending line must match a frozen allowlisted line - count<=budget
    # is no longer sufficient), and any NEW leak (outside the allowlist,
    # or any non-matching/extra line inside an allowlisted file) REDs.
    "agent_session_id_redaction": run_agent_session_id_redaction,
    # CASTING-NODE-CARRY (E/S1 follow-on, Smith B-policy). Replaces the brittle
    # text_contains grep shape-pin (plan_graph.py text_contains selected_model_ref)
    # that S1 invalidated when it folded the per-field casting carry into the
    # opaque bag (casting_bag / merge_casting_bags / stamp_casting). Executes the
    # REAL brick_protocol/support/operator/plan_graph._linear_plan_from_graph_plan IN-PROCESS over
    # a composed graph plan and asserts the projected linear step carries every
    # primitives.NODE_CASTING_FIELDS member with step-OR-plan precedence (step value
    # when truthy, else plan; None when declared on neither side). Iterating the real
    # field table auto-covers any future casting field. Mutation-RED: drop a field in
    # stamp_casting (or merge_casting_bags) -> the step-wins scenario sees that field
    # return None instead of the declared step value -> RED.
    "casting_node_carry": run_casting_node_carry,
}
KERNEL_CHECK_IDS = frozenset(KERNEL_DISPATCH)


# CHECKER-PROGRESS-GUARD-0: support-only liveness evidence for long profile runs.
# A checker/profile pass is still only support evidence; these knobs only make an
# ongoing support check observable and bounded so an operator can distinguish
# "working" from "stalled". They do not choose Movement, judge quality, call
# providers, or change any checker invariant.
_CHECK_PROFILE_STEP_TIMEOUT_ENV = "BRICK_CHECK_PROFILE_STEP_TIMEOUT_SECONDS"
_CHECK_PROFILE_HEARTBEAT_ENV = "BRICK_CHECK_PROFILE_HEARTBEAT_SECONDS"
_CHECK_PROFILE_STALL_WARNING_ENV = "BRICK_CHECK_PROFILE_STALL_WARNING_SECONDS"
_DEFAULT_STEP_TIMEOUT_SECONDS = 900.0
_DEFAULT_HEARTBEAT_SECONDS = 60.0
_DEFAULT_STALL_WARNING_SECONDS = 300.0


class _ProfileStepTimeout(TimeoutError):
    pass


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if value != value or value in {float("inf"), float("-inf")} or value < 0:
        return default
    return value


@dataclass(frozen=True)
class _ProfileProgressScope:
    profile_id: str
    kind: str
    item_ref: str

    @property
    def label(self) -> str:
        return f"profile={self.profile_id} {self.kind}={self.item_ref}"


@contextlib.contextmanager
def _profile_progress_guard(scope: _ProfileProgressScope):
    timeout_seconds = _float_env(
        _CHECK_PROFILE_STEP_TIMEOUT_ENV,
        _DEFAULT_STEP_TIMEOUT_SECONDS,
    )
    heartbeat_seconds = _float_env(
        _CHECK_PROFILE_HEARTBEAT_ENV,
        _DEFAULT_HEARTBEAT_SECONDS,
    )
    stall_warning_seconds = _float_env(
        _CHECK_PROFILE_STALL_WARNING_ENV,
        _DEFAULT_STALL_WARNING_SECONDS,
    )
    started = time.monotonic()
    stop = threading.Event()
    timed_out = False
    stall_warned = False
    previous_handler: Any = None
    use_signal_timeout = (
        timeout_seconds > 0
        and hasattr(signal, "SIGALRM")
        and threading.current_thread() is threading.main_thread()
    )

    def _heartbeat() -> None:
        nonlocal stall_warned
        if heartbeat_seconds <= 0:
            return
        while not stop.wait(heartbeat_seconds):
            elapsed = time.monotonic() - started
            if (
                stall_warning_seconds > 0
                and elapsed >= stall_warning_seconds
                and not stall_warned
            ):
                stall_warned = True
                print(
                    "profile progress: STALL "
                    f"{scope.label} elapsed={elapsed:.1f}s "
                    f"stall_warning={stall_warning_seconds:.1f}s",
                    file=sys.stderr,
                    flush=True,
                )
            print(
                "profile progress: RUNNING "
                f"{scope.label} elapsed={elapsed:.1f}s timeout={timeout_seconds:.1f}s",
                file=sys.stderr,
                flush=True,
            )

    def _raise_timeout(_signum: int, _frame: Any) -> None:
        nonlocal timed_out
        timed_out = True
        elapsed = time.monotonic() - started
        raise _ProfileStepTimeout(
            f"profile progress timeout: {scope.label} elapsed={elapsed:.1f}s "
            f"timeout={timeout_seconds:.1f}s"
        )

    print(
        "profile progress: START "
        f"{scope.label} timeout={timeout_seconds:.1f}s heartbeat={heartbeat_seconds:.1f}s",
        file=sys.stderr,
        flush=True,
    )
    thread = threading.Thread(target=_heartbeat, daemon=True)
    thread.start()
    if use_signal_timeout:
        previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _raise_timeout)
        signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield
    except _ProfileStepTimeout as exc:
        raise ProfileError(str(exc)) from exc
    finally:
        if use_signal_timeout:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
        stop.set()
        elapsed = time.monotonic() - started
        status = "TIMEOUT" if timed_out else "DONE"
        print(
            f"profile progress: {status} {scope.label} elapsed={elapsed:.1f}s",
            file=sys.stderr,
            flush=True,
        )


def _raw_profile(path: Path) -> Mapping[str, Any]:
    parsed = parse_yaml_subset(path.read_text(encoding="utf-8"))
    return require_mapping(parsed, str(path))


def assert_registry_closure(repo: Path) -> None:
    missing_top_level = sorted(set(RULE_RUNNERS) - TOP_LEVEL_KEYS)
    if missing_top_level:
        raise ProfileError(f"self-test failed: RULE_RUNNERS key(s) missing from TOP_LEVEL_KEYS: {missing_top_level}")
    synthetic = {
        "schema": PROFILE_SCHEMA,
        "profile_id": "self-test-rule-key-closure",
        "description": "self-test profile proving RULE_RUNNERS keys remain admitted profile teeth",
        "proof_limits": ["checker profile self-test support evidence only"],
        "not_proven": ["runtime behavior of every admitted rule runner"],
    }
    for key in RULE_RUNNERS:
        synthetic[key] = []
    synthetic["path_absent"] = ["<self-test-rule-key-closure-no-such-path>"]
    validate_profile(synthetic, Path("<self-test-rule-key-closure>"))
    assert_checker_vessel_patch_closure()
    _assert_temp_vessel_guard_teeth()

    profile_files = sorted((repo / PROFILE_DIR).glob("*.yaml"))
    if not profile_files:
        raise ProfileError(f"self-test failed: no profile YAML files found in {repo / PROFILE_DIR}")
    unknown_checks: dict[str, list[str]] = {}
    unknown_rules: dict[str, list[str]] = {}
    for path in profile_files:
        profile = _raw_profile(path)
        check_ids = require_string_list(profile.get("kernel_checks", []), f"{path}: kernel_checks")
        missing = sorted(set(check_ids) - KERNEL_DISPATCH.keys())
        if missing:
            unknown_checks[to_posix(path)] = missing
        rule_keys = sorted((set(profile) - BASE_TOP_LEVEL_KEYS) - RULE_RUNNERS.keys())
        if rule_keys:
            unknown_rules[to_posix(path)] = rule_keys
    if unknown_checks:
        raise ProfileError(f"self-test failed: profile kernel_checks not in KERNEL_DISPATCH: {unknown_checks}")
    if unknown_rules:
        raise ProfileError(f"self-test failed: profile rule keys not in RULE_RUNNERS: {unknown_rules}")
    # A4: KERNEL_PURE must name only admitted kernel checks. This runs at
    # self-test/runtime after the module-tail KERNEL_DISPATCH merge, so the
    # closure is measured against the full dispatch table.
    missing_pure = sorted(KERNEL_PURE - set(KERNEL_DISPATCH))
    if missing_pure:
        raise ProfileError(
            f"self-test failed: KERNEL_PURE kernel id(s) not in KERNEL_DISPATCH: {missing_pure}"
        )


def read_profile(path: Path) -> Mapping[str, Any]:
    parsed = parse_yaml_subset(path.read_text(encoding="utf-8"))
    profile = require_mapping(parsed, str(path))
    validate_profile(profile, path)
    return profile


def validate_profile(profile: Mapping[str, Any], path: Path) -> None:
    unknown = set(profile) - TOP_LEVEL_KEYS
    if unknown:
        raise ProfileError(f"{path}: unknown top-level key(s): {sorted(unknown)}")
    if profile.get("schema") != PROFILE_SCHEMA:
        raise ProfileError(f"{path}: schema must be {PROFILE_SCHEMA!r}")
    require_string(profile.get("profile_id"), f"{path}: profile_id")
    description = require_string(profile.get("description"), f"{path}: description")
    if not description.strip():
        raise ProfileError(f"{path}: description must be a non-empty string")
    proof_limits = require_string_list(profile.get("proof_limits"), f"{path}: proof_limits")
    if not proof_limits:
        raise ProfileError(f"{path}: proof_limits must be a non-empty list of strings")
    not_proven = require_string_list(profile.get("not_proven"), f"{path}: not_proven")
    if not not_proven:
        raise ProfileError(f"{path}: not_proven must be a non-empty list of strings")
    for check_id in require_string_list(profile.get("kernel_checks", []), f"{path}: kernel_checks"):
        if check_id not in KERNEL_CHECK_IDS:
            raise ProfileError(f"{path}: unknown kernel check id: {check_id}")
    has_active_tooth = bool(profile.get("kernel_checks")) or any(profile.get(key) for key in RULE_KEYS)
    if not has_active_tooth:
        raise ProfileError(
            f"{path}: profile must declare at least one active inspection item "
            "(kernel_checks or a non-empty rule list)"
        )
    for key in RULE_KEYS:
        if key in profile and not isinstance(profile[key], list):
            raise ProfileError(f"{path}: {key} must be a list")


def profile_path(repo: Path, value: str) -> Path:
    raw = Path(value)
    if raw.exists():
        return raw
    name = value[:-5] if value.endswith(".yaml") else value
    candidates = [
        repo / PROFILE_DIR / f"{name}.yaml",
        repo / PROFILE_DIR / f"{name.replace('-', '_')}.yaml",
        repo / PROFILE_DIR / f"{name.replace('_', '-')}.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ProfileError(f"profile not found: {value}")


def profile_paths(repo: Path, args: argparse.Namespace) -> list[Path]:
    if args.all:
        paths = sorted((repo / PROFILE_DIR).glob("*.yaml"))
        if not paths:
            raise ProfileError(f"no profiles found in {repo / PROFILE_DIR}")
        return paths
    if args.profile:
        return [profile_path(repo, args.profile)]
    raise ProfileError("provide --profile, --all, or --self-test")


def run_kernel_check(
    repo: Path,
    check_id: str,
    *,
    profile_id: str = "<unknown>",
) -> KernelResult:
    memo_key = (check_id, str(repo.resolve()))
    if check_id in KERNEL_PURE and memo_key in _KERNEL_MEMO:
        return _KERNEL_MEMO[memo_key]
    try:
        runner = KERNEL_DISPATCH[check_id]
    except KeyError as exc:
        raise ProfileError(f"unknown kernel check id: {check_id}") from exc
    with _profile_progress_guard(
        _ProfileProgressScope(profile_id, "kernel_check", check_id)
    ):
        result = runner(repo)
    # GREEN-only cache: a rejecting pure kernel raises ProfileError inside
    # runner(repo) above (e.g. _run_package_path_admission :331-333), so this
    # store line is unreachable on RED and a violation is always re-measured.
    if check_id in KERNEL_PURE:
        _KERNEL_MEMO[memo_key] = result
    return result


@dataclass(frozen=True)
class ProfileCheckFailure:
    profile_id: str
    check_id: str
    observation_kind: str
    detail: str


def _profile_exception_observation_kind(exc: BaseException) -> str:
    """Classify a profile/kern_check exception as support-observed blocked/red."""

    if isinstance(exc, UnicodeDecodeError):
        return "blocked(non_utf8)"
    if isinstance(exc, FileNotFoundError):
        return "blocked(missing_file_or_cli)"
    if isinstance(exc, OSError):
        return "blocked(os_error)"
    text = str(exc).lower()
    blocked_needles = (
        "unicode",
        "utf-8",
        "no such file or directory",
        "command not found",
        "missing executable",
        "executable not found",
        "not installed",
        "cli missing",
        "cli absent",
        "gemini cli",
        "gemini executable",
        "gemini-local cli",
    )
    if any(needle in text for needle in blocked_needles):
        return "blocked(environment)"
    return "red(source)"


def _profile_exception_detail(exc: BaseException) -> str:
    text = str(exc).replace("\n", " ").strip()
    if not text:
        text = exc.__class__.__name__
    return text[:600]


def _format_profile_check_failures(failures: Sequence[ProfileCheckFailure]) -> str:
    return "\n".join(
        "- profile={failure.profile_id} kernel_check={failure.check_id} "
        "observation={failure.observation_kind}: {failure.detail}".format(
            failure=failure
        )
        for failure in failures
    )


def _run_profile_kernel_checks(
    repo: Path,
    profile: Mapping[str, Any],
    *,
    profile_id: str,
) -> tuple[list[KernelResult], list[ProfileCheckFailure]]:
    kernel_results: list[KernelResult] = []
    failures: list[ProfileCheckFailure] = []
    for check_id in require_string_list(profile.get("kernel_checks", []), "kernel_checks"):
        try:
            kernel_results.append(run_kernel_check(repo, check_id, profile_id=profile_id))
        except Exception as exc:  # support observation: isolate one kernel check.
            failure = ProfileCheckFailure(
                profile_id=profile_id,
                check_id=check_id,
                observation_kind=_profile_exception_observation_kind(exc),
                detail=_profile_exception_detail(exc),
            )
            failures.append(failure)
            print(
                "profile kernel_check observed: "
                f"profile={failure.profile_id} check={failure.check_id} "
                f"observation={failure.observation_kind} detail={failure.detail}",
                file=sys.stderr,
                flush=True,
            )
    return kernel_results, failures


def _run_profile_rule(
    repo: Path,
    profile: Mapping[str, Any],
    *,
    profile_id: str,
    rule_key: str,
) -> int:
    # Preserve pre-guard semantics: every registered rule runner is called even
    # when the profile does not carry that top-level key. Some runners include
    # always-on support checks, so skipping empty/missing keys silently weakens
    # the profile. The progress guard is observational only.
    with _profile_progress_guard(
        _ProfileProgressScope(profile_id, "rule", rule_key)
    ):
        return RULE_RUNNERS[rule_key](repo, profile)


def run_profile(repo: Path, path: Path) -> tuple[int, list[KernelResult]]:
    _ensure_repo_import_path(repo)
    _evict_foreign_brick_protocol_modules(repo)
    profile = read_profile(path)
    profile_id = str(profile["profile_id"])
    rule_count = 0
    for key in sorted(RULE_RUNNERS):
        rule_count += _run_profile_rule(
            repo,
            profile,
            profile_id=profile_id,
            rule_key=key,
        )
    kernel_results, kernel_failures = _run_profile_kernel_checks(
        repo,
        profile,
        profile_id=profile_id,
    )
    if kernel_failures:
        raise ProfileError(
            "profile kernel_check exception isolation observed rejecting "
            "kernel_check(s); sweep may continue to later profiles under --all:\n"
            + _format_profile_check_failures(kernel_failures)
        )
    print(
        f"profile passed: {profile['profile_id']} "
        f"({rule_count} declarative rule observation(s), "
        f"{sum(result.inspected for result in kernel_results)} kernel target(s) inspected)"
    )
    for result in kernel_results:
        first_line = result.output.splitlines()[0] if result.output else "no output"
        print(f"- {result.check_id}: {first_line}")
    return rule_count, kernel_results


def _emit_profile_sweep_start(index: int, total: int, path: Path) -> None:
    print(
        f"profile sweep: START {index}/{total} profile={path.stem}",
        file=sys.stderr,
        flush=True,
    )


def _emit_profile_sweep_done(index: int, total: int, path: Path) -> None:
    # D2 sweep-progress twin: the START line announces which profile the --all
    # sweep is entering; this DONE line announces the k/N COMPLETION so an
    # operator watching a long --all can see forward progress (k of N done)
    # instead of a silent stall between START lines. Observation-only: it emits
    # only after run_profile returned without raising, judges no success/quality,
    # and authors no Movement.
    print(
        f"profile sweep: DONE {index}/{total} profile={path.stem}",
        file=sys.stderr,
        flush=True,
    )


@contextlib.contextmanager
def _temporary_env(updates: Mapping[str, str]):
    previous = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_checker_progress_observability(repo: Path) -> KernelResult:
    del repo
    stderr = io.StringIO()
    with _temporary_env(
        {
            _CHECK_PROFILE_HEARTBEAT_ENV: "0.01",
            _CHECK_PROFILE_STALL_WARNING_ENV: "0.01",
            _CHECK_PROFILE_STEP_TIMEOUT_ENV: "0",
        }
    ), contextlib.redirect_stderr(stderr):
        _emit_profile_sweep_start(3, 7, Path("brick_protocol/support/checkers/profiles/core.yaml"))
        with _profile_progress_guard(
            _ProfileProgressScope("core", "kernel_check", "checker_progress_observability")
        ):
            # D3-1 evidence-wait: the STALL/RUNNING heartbeat lines arrive from a
            # background thread. Instead of racing them with a fixed wall-clock
            # sleep (banned: 벽시계 상한 금지 / 숫자 조정 금지), POLL the redirected
            # stderr until BOTH the STALL and RUNNING evidence-shape needles have
            # been observed, then exit the guard (which emits the progress DONE
            # line). The guard's own optional wall-clock timeout stays 0, so this
            # loop has NO upper wall-clock cap -- it exits ONLY on evidence shape.
            stall_needle = (
                "profile progress: STALL "
                "profile=core kernel_check=checker_progress_observability"
            )
            running_needle = (
                "profile progress: RUNNING "
                "profile=core kernel_check=checker_progress_observability"
            )
            while True:
                observed_so_far = stderr.getvalue()
                if stall_needle in observed_so_far and running_needle in observed_so_far:
                    break
                time.sleep(0.005)
        _emit_profile_sweep_done(3, 7, Path("brick_protocol/support/checkers/profiles/core.yaml"))
    observed = stderr.getvalue()
    required = (
        "profile sweep: START 3/7 profile=core",
        "profile sweep: DONE 3/7 profile=core",
        "profile progress: STALL profile=core kernel_check=checker_progress_observability",
        "profile progress: RUNNING profile=core kernel_check=checker_progress_observability",
        "profile progress: DONE profile=core kernel_check=checker_progress_observability",
    )
    missing = [needle for needle in required if needle not in observed]
    if missing:
        raise ProfileError(
            "checker progress observability rejected evidence: missing line(s): "
            + ", ".join(missing)
        )
    # D4 mutation-RED (stall-detection removed): with the STALL warning disabled
    # (BRICK_CHECK_PROFILE_STALL_WARNING_SECONDS=0), the heartbeat must NOT emit a
    # STALL line -- so a mutation that hard-wires STALL on (or drops the disable
    # guard) is caught: the disabled run would still carry a STALL needle. This
    # probe proves the stall-detection surface is genuinely gated, not decorative.
    stall_disabled_observed = _run_progress_guard_probe(
        heartbeat="0.01",
        stall_warning="0",
        emit_running_wait=True,
    )
    if "profile progress: STALL" in stall_disabled_observed:
        raise ProfileError(
            "checker progress observability mutation-RED: STALL line emitted while "
            "stall detection was disabled (stall_warning=0) -- stall detection is "
            "not actually gated"
        )
    # D4 mutation-RED (heartbeat removed): with the heartbeat disabled
    # (BRICK_CHECK_PROFILE_HEARTBEAT_SECONDS=0), neither STALL nor RUNNING may be
    # emitted, so a mutation that emits progress unconditionally is caught.
    heartbeat_disabled_observed = _run_progress_guard_probe(
        heartbeat="0",
        stall_warning="0.01",
        emit_running_wait=False,
    )
    if (
        "profile progress: RUNNING" in heartbeat_disabled_observed
        or "profile progress: STALL" in heartbeat_disabled_observed
    ):
        raise ProfileError(
            "checker progress observability mutation-RED: RUNNING/STALL emitted while "
            "the heartbeat was disabled (heartbeat=0) -- progress emission is not gated"
        )
    return KernelResult(
        check_id="checker_progress_observability",
        inspected=len(required) + 2,
        output=(
            "checker progress observability passed: sweep START/DONE k/N and "
            "STALL/RUNNING/DONE progress lines observed by evidence-wait; "
            "stall-detection + heartbeat mutation-RED probes gated."
        ),
    )


def _run_progress_guard_probe(
    *,
    heartbeat: str,
    stall_warning: str,
    emit_running_wait: bool,
) -> str:
    """Run one bounded progress-guard scope and return the captured stderr.

    D4 mutation-RED helper: drives a single ``_profile_progress_guard`` scope
    with the supplied heartbeat / stall-warning env so the caller can assert what
    the guard emits (or must NOT emit) under a disabled surface. When
    ``emit_running_wait`` is set it polls for the RUNNING needle (evidence-wait,
    no wall-clock ceiling); otherwise it returns quickly (the disabled-heartbeat
    case, where no RUNNING line can appear). Support probe only -- authors no
    Movement / success / quality.
    """

    probe_stderr = io.StringIO()
    with _temporary_env(
        {
            _CHECK_PROFILE_HEARTBEAT_ENV: heartbeat,
            _CHECK_PROFILE_STALL_WARNING_ENV: stall_warning,
            _CHECK_PROFILE_STEP_TIMEOUT_ENV: "0",
        }
    ), contextlib.redirect_stderr(probe_stderr):
        with _profile_progress_guard(
            _ProfileProgressScope("core", "kernel_check", "checker_progress_observability_probe")
        ):
            if emit_running_wait:
                running_needle = (
                    "profile progress: RUNNING "
                    "profile=core kernel_check=checker_progress_observability_probe"
                )
                while running_needle not in probe_stderr.getvalue():
                    time.sleep(0.005)
            else:
                # Heartbeat disabled: give the (silent) heartbeat thread a brief
                # yield so a REGRESSION that emits anyway would be observed. This
                # is a small fixed yield, not an arrival-order wall-clock cap.
                time.sleep(0.02)
    return probe_stderr.getvalue()


@dataclass(frozen=True)
class ProfileRunFailure:
    path: Path
    observation_kind: str
    detail: str


def _format_profile_run_failures(failures: Sequence[ProfileRunFailure]) -> str:
    return "\n".join(
        "- profile={failure.path.stem} observation={failure.observation_kind}: "
        "{failure.detail}".format(failure=failure)
        for failure in failures
    )


def _run_profile_path_sweep(
    repo: Path,
    paths: Sequence[Path],
    *,
    continue_after_error: bool,
    profile_runner: Callable[[Path, Path], tuple[int, list[KernelResult]]] = run_profile,
) -> list[ProfileRunFailure]:
    failures: list[ProfileRunFailure] = []
    total = len(paths)
    for index, path in enumerate(paths, start=1):
        if continue_after_error:
            _emit_profile_sweep_start(index, total, path)
        try:
            profile_runner(repo, path)
        except Exception as exc:
            failure = ProfileRunFailure(
                path=path,
                observation_kind=_profile_exception_observation_kind(exc),
                detail=_profile_exception_detail(exc),
            )
            if not continue_after_error:
                raise
            failures.append(failure)
            print(
                "profile sweep: OBSERVED "
                f"{index}/{total} profile={path.stem} "
                f"observation={failure.observation_kind} detail={failure.detail}",
                file=sys.stderr,
                flush=True,
            )
            continue
        if continue_after_error:
            _emit_profile_sweep_done(index, total, path)
    return failures


def run_checker_profile_exception_isolation(repo: Path) -> KernelResult:
    """D2 fixtures for kernel-check and --all profile exception isolation."""

    inspected = 0
    observed_kernel_checks: list[str] = []

    def fixture_non_utf8(_repo: Path) -> KernelResult:
        observed_kernel_checks.append("fixture_non_utf8")
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "fixture non-UTF8")

    def fixture_after(_repo: Path) -> KernelResult:
        observed_kernel_checks.append("fixture_after")
        return KernelResult(
            check_id="fixture_after",
            inspected=1,
            output="fixture after observed",
        )

    original_non_utf8 = KERNEL_DISPATCH.get("fixture_non_utf8")
    original_after = KERNEL_DISPATCH.get("fixture_after")
    try:
        KERNEL_DISPATCH["fixture_non_utf8"] = fixture_non_utf8
        KERNEL_DISPATCH["fixture_after"] = fixture_after
        kernel_results, kernel_failures = _run_profile_kernel_checks(
            repo,
            {"kernel_checks": ["fixture_non_utf8", "fixture_after"]},
            profile_id="exception-isolation-fixture",
        )
    finally:
        if original_non_utf8 is None:
            KERNEL_DISPATCH.pop("fixture_non_utf8", None)
        else:
            KERNEL_DISPATCH["fixture_non_utf8"] = original_non_utf8
        if original_after is None:
            KERNEL_DISPATCH.pop("fixture_after", None)
        else:
            KERNEL_DISPATCH["fixture_after"] = original_after
    if observed_kernel_checks != ["fixture_non_utf8", "fixture_after"]:
        raise ProfileError(
            "checker_profile_exception_isolation mutation-RED: kernel loop did "
            "not continue after a forced non-UTF8 exception; observed "
            f"{observed_kernel_checks!r}"
        )
    if len(kernel_results) != 1 or len(kernel_failures) != 1:
        raise ProfileError(
            "checker_profile_exception_isolation fixture expected one kernel "
            f"result and one isolated failure; observed {kernel_results!r} / "
            f"{kernel_failures!r}"
        )
    if kernel_failures[0].observation_kind != "blocked(non_utf8)":
        raise ProfileError(
            "checker_profile_exception_isolation fixture expected "
            f"blocked(non_utf8); observed {kernel_failures[0].observation_kind}"
        )
    inspected += 2

    with tempfile.TemporaryDirectory(prefix="bp-profile-sweep-isolation-") as tmp:
        profile_dir = Path(tmp)
        first = profile_dir / "001-crash.yaml"
        second = profile_dir / "002-after.yaml"
        first.write_text("schema: checker-profile/v1\nprofile_id: first\n", encoding="utf-8")
        second.write_text("schema: checker-profile/v1\nprofile_id: second\n", encoding="utf-8")
        observed_profiles: list[str] = []

        def fixture_profile_runner(_repo: Path, path: Path) -> tuple[int, list[KernelResult]]:
            observed_profiles.append(path.stem)
            if path == first:
                raise FileNotFoundError("fixture missing provider CLI")
            return 0, []

        failures = _run_profile_path_sweep(
            repo,
            [first, second],
            continue_after_error=True,
            profile_runner=fixture_profile_runner,
        )
        if observed_profiles != ["001-crash", "002-after"]:
            raise ProfileError(
                "checker_profile_exception_isolation mutation-RED: --all sweep "
                "did not continue to the next profile after a forced profile "
                f"exception; observed {observed_profiles!r}"
            )
        if len(failures) != 1 or failures[0].observation_kind != "blocked(missing_file_or_cli)":
            raise ProfileError(
                "checker_profile_exception_isolation fixture expected one "
                "blocked(missing_file_or_cli) observation; observed "
                f"{failures!r}"
            )
        inspected += 2

    return KernelResult(
        check_id="checker_profile_exception_isolation",
        inspected=inspected,
        output=(
            "checker profile exception isolation passed: forced non-UTF8 "
            "kernel_check exception was observed as blocked and the following "
            "kernel_check still ran; forced per-profile missing-CLI exception "
            "under --all was observed as blocked and the following profile still "
            "ran. Both fixtures are mutation-RED probes for removing the "
            "isolation catch."
        ),
    )


KERNEL_DISPATCH = {
    **KERNEL_DISPATCH,
    "checker_progress_observability": run_checker_progress_observability,
    "checker_profile_exception_isolation": run_checker_profile_exception_isolation,
}
KERNEL_CHECK_IDS = frozenset(KERNEL_DISPATCH)


def write_self_test_files(root: Path) -> Path:
    repo = root / "repo"
    (repo / "brick_protocol/support/checkers/profiles").mkdir(parents=True)
    (repo / "brick_protocol/support/checkers").mkdir(parents=True, exist_ok=True)
    (repo / "brick_protocol" / "link").mkdir()
    (repo / "project/brick-protocol/buildings/demo/work").mkdir(parents=True)
    (repo / "notes").mkdir()
    (repo / "notes/keep.txt").write_text("Brick Agent Link\n", encoding="utf-8")
    # The hook-registry axis guard scans brick_protocol/agent/hooks/registry.yaml on EVERY
    # profile run (always-on), so the synthetic self-test repo needs a minimal
    # valid registry fixture.
    (repo / "brick_protocol/agent/hooks").mkdir(parents=True)
    (repo / "brick_protocol/agent/hooks/registry.yaml").write_text(
        json.dumps(
            {
                "hooks": {
                    "hook:self-test-advisory": {
                        "owner_axis": "Agent",
                        "kind": "advisory",
                        "event_ref": "before-agent-work",
                        "description": "Self-test fixture hook.",
                        "execution_opened": False,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (repo / "brick_protocol/link/movement.yaml").write_text(
        "\n".join(
            [
                "movement_literals:",
                "  - movement: forward",
                "  - movement: reroute",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "project/brick-protocol/buildings/demo/work/building-map.json").write_text(
        json.dumps({"kind": "building_graph_map", "brick_instances": [{"id": "b1"}]}),
        encoding="utf-8",
    )
    profile_path_value = repo / "brick_protocol/support/checkers/profiles/self.yaml"
    profile_path_value.write_text(
        "\n".join(
            [
                "schema: checker-profile/v1",
                "profile_id: self",
                "description: self-test profile",
                "kernel_checks: []",
                "path_exists:",
                "  - notes/keep.txt",
                "path_absent:",
                "  - notes/missing.txt",
                "path_absent_glob:",
                "  - notes/*.tmp",
                "path_allowlist:",
                "  - root: brick_protocol/support/checkers/profiles",
                "    paths:",
                "      - brick_protocol/support/checkers/profiles/self.yaml",
                "text_contains:",
                "  - path: notes/keep.txt",
                "    text: Brick",
                "text_absent:",
                "  - path: notes/keep.txt",
                "    text: source truth",
                "yaml_literal_set:",
                "  - path: brick_protocol/link/movement.yaml",
                "    key: movement_literals[].movement",
                "    values:",
                "      - forward",
                "      - reroute",
                "json_required_paths:",
                "  - path: project/brick-protocol/buildings/demo/work/building-map.json",
                "    required:",
                "      - kind",
                "      - brick_instances[].id",
                "proof_limits:",
                "  - support evidence only",
                "not_proven:",
                "  - source truth",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return repo


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="checker-profile-self-test-") as tmp:
        repo = write_self_test_files(Path(tmp))
        profile = repo / PROFILE_DIR / "self.yaml"
        run_profile(repo, profile)
        assert_registry_closure(Path(_REPO_ROOT))
        print("self-test passed: registry closure asserted")
        bad_profile = dict(read_profile(profile))
        bad_profile["kernel_checks"] = ["brick_protocol/support/checkers/check_package_path_admission.py"]
        try:
            validate_profile(bad_profile, profile)
        except ProfileError:
            print("self-test passed: arbitrary checker file path rejected")
        else:
            raise ProfileError("self-test failed: arbitrary checker file path was accepted")
        toothless_profile = {
            "schema": PROFILE_SCHEMA,
            "profile_id": "self-test-toothless-profile",
            "description": "negative probe for profile guard",
            "kernel_checks": [],
            "proof_limits": ["checker profile negative probe support evidence only"],
            "not_proven": ["runtime behavior"],
        }
        try:
            validate_profile(toothless_profile, Path("<self-test-toothless-profile>"))
        except ProfileError:
            print("self-test passed: toothless profile rejected")
        else:
            raise ProfileError("self-test failed: toothless profile was accepted")
        # Permanent negative probes: duplicate same-path/same-key blocks must be
        # a HARD parse error, never a silent drop (false-green vector: a whole
        # text_contains enforcement block could vanish without a RED).
        duplicate_top_level_block = "\n".join(
            [
                "text_contains:",
                "  - path: notes/keep.txt",
                "    text: Brick",
                "text_contains:",
                "  - path: notes/keep.txt",
                "    text: Agent",
                "",
            ]
        )
        try:
            parse_yaml_subset(duplicate_top_level_block)
        except ProfileError:
            print("self-test passed: duplicate same-key top-level block rejected (no silent drop)")
        else:
            raise ProfileError("self-test failed: duplicate same-key top-level block was silently accepted")
        duplicate_key_in_list_item = "\n".join(
            [
                "text_contains:",
                "  - path: notes/keep.txt",
                "    path: notes/other.txt",
                "    text: Brick",
                "",
            ]
        )
        try:
            parse_yaml_subset(duplicate_key_in_list_item)
        except ProfileError:
            print("self-test passed: duplicate mapping key inside list item rejected (no silent drop)")
        else:
            raise ProfileError("self-test failed: duplicate mapping key inside list item was silently accepted")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run admitted flat checker profiles as support evidence. Profiles "
            "may name only whitelisted kernel check ids and declarative rules."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    parser.add_argument("--profile", help="Profile name or profile YAML path.")
    parser.add_argument("--all", action="store_true", help="Run every brick_protocol/support/checkers/profiles/*.yaml profile.")
    parser.add_argument("--self-test", action="store_true", help="Run profile parser/rule self-test.")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.self_test:
            run_self_test()
            print(PROOF_LIMIT)
            return 0
        if args.profile and args.all:
            raise ProfileError("use --profile or --all, not both")
        repo = Path(args.repo).resolve()
        if not repo.is_dir():
            raise ProfileError(f"--repo must be a directory: {repo}")
        paths = profile_paths(repo, args)
        live_inbox_count_before = (
            live_inbox_fixture_packet_count(repo) if args.all else None
        )
        try:
            with _checker_profile_sweep_env():
                # A4: cache lifetime = one sweep. Clear the pure-kernel memo at
                # sweep entry so a reused process (e.g. an in-process caller that
                # invokes main() twice) never serves a stale KernelResult across
                # sweeps. Within one sweep, repeated pure kernels reuse the cache.
                _KERNEL_MEMO.clear()
                profile_failures = _run_profile_path_sweep(
                    repo,
                    paths,
                    continue_after_error=args.all,
                )
                if profile_failures:
                    raise ProfileError(
                        "--all observed rejecting profile(s) after continuing "
                        "through the full declared profile set:\n"
                        + _format_profile_run_failures(profile_failures)
                    )
        finally:
            if live_inbox_count_before is not None:
                assert_all_profiles_did_not_write_live_fixture_inbox(
                    repo, live_inbox_count_before
                )
        print(PROOF_LIMIT)
        return 0
    except (OSError, json.JSONDecodeError, ProfileError) as exc:
        print(f"profile runner rejected evidence: {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

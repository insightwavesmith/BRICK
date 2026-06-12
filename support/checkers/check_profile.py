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
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# --- ELEGANT-REFACTOR P3a: the kernel-check bodies, declarative rule
# runners, behavioral case runners, and the YAML-subset parser were lifted
# into the support/checkers/lib/ sublayer (engine blueprint 0531 §5 /
# detail-design §D-4 Opt B). This module stays the THIN FACADE: profile
# load + validate, RULE_RUNNERS, run_kernel_check dispatch, the self-test,
# and the CLI. The public names are re-exported below so external importers
# and the checker_strict_validation pins are unchanged.
#
# P3a-FIX-1: the lifted `from support.checkers.lib.*` imports below run at
# module-load time, BEFORE the per-run repo-root sys.path bootstrap further
# down. Pre-decomposition this module had no top-level `support.*` import, so
# the canonical gate `PYTHONPATH=support/import_identity python3
# support/checkers/check_profile.py --all` (no repo-root on PYTHONPATH) worked.
# To preserve that public command surface, bootstrap the repo root (this file's
# parents[2]) onto sys.path here, before the lib imports. stdlib only; the
# import_identity router governs only `brick_protocol.*`, not `support.*`.
import os.path as _osp

_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from support.checkers.lib.yaml_subset import (
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
from support.checkers.lib.rule_runners import (
    run_path_exists,
    run_path_absent,
    run_path_absent_glob,
    run_path_allowlist,
    text_rule,
    run_yaml_literal_set,
    run_json_required_paths,
    run_json_value_paths,
    run_agent_resource_boundary,
    run_agent_resource_retired_ref_rejects,
    run_building_plan_boundary,
    run_route_policy_boundary,
    validate_building_plan_boundary,
    validate_route_policy_boundary,
)
from support.checkers.lib.case_runners import (
    run_adapter_capability_rehome_case,
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
    run_agent_candidate_packet_case,
    run_preset_ranking_packet_case,
    run_declared_step_template_plan_case,
    run_declared_step_template_plan_rejects,
    run_compose_building_case,
    run_compose_building_rejects,
    run_write_scope_default_exclude_case,
    run_source_fact_body_carry_case,
    run_step_output_drain_case,
    run_step_output_drain_rejects,
    run_auto_repair_replay_case,
    run_child_building_candidate_case,
    run_native_dispatch_close_case,
    run_workflow_import_case,
    run_fail_fixture_rejects,
    run_gate_sequence_policy_case,
    run_gate_sequence_policy_rejects,
)
from support.checkers.lib.kernel_checks import (
    run_axis_vocab_drift,
    captured_output,
    patched_argv,
    call_main,
    run_building_map_graph,
    run_building_plans_boundary_sweep,
    run_agent_adapter_return_shape,
    run_provider_preflight,
    run_onboard_smoke,
    run_install_script_lint,
    run_reporter_notification_projection,
    run_chat_session_park_seam,
    run_mcp_stdio_smoke,
    run_connect_config_launch,
    run_codex_projection_native,
    run_claude_projection_native,
    run_agent_session_id_redaction,
)


PROFILE_SCHEMA = "checker-profile/v1"
PROOF_LIMIT = (
    "proof limit: profile runner support evidence only; checker/profile pass "
    "does not prove source truth, success judgment, quality judgment, Movement "
    "authority, provider behavior, or complete checker consolidation."
)
PROFILE_DIR = Path("support/checkers/profiles")
KERNEL_CHECK_IDS = {
    "axis_vocab_drift",
    "package_path_admission",
    "axis_contract_projection",
    "declared_verifier_exists",
    "axis_field_enum_parity",
    "agentfact_single_home",
    "building_root_anchor",
    "catalog_reader_sync",
    "agent_resource_resolution",
    "bricks_spec_completeness",
    "building_lifecycle_path_shape",
    "building_map_graph",
    "project_declaration",
    "bounded_agent_proposed_routing_loop",
    "building_operator_driver0",
    "building_declaration_integrity",
    "building_plans_boundary_sweep",
    "agent_adapter_return_shape",
    "provider_preflight",
    "onboard_smoke",
    "install_script_lint",
    "reporter_notification_projection",
    "chat_session_park_seam",
    "mcp_stdio_smoke",
    "connect_config_launch",
    "codex_projection_native",
    "claude_projection_native",
    "recording_checker_derived_contract",
    "axis_crossing_elegance",
    "tier_a_three_axis_conformance",
    "brick_template_catalog_restructure",
    "evidence_spine",
    "evidence_spine_projection",
    "pin_estate_integrity",
    "agent_session_id_redaction",
}
RULE_KEYS = {
    "path_exists",
    "path_absent",
    "path_absent_glob",
    "path_allowlist",
    "text_contains",
    "text_absent",
    "yaml_literal_set",
    "json_required_paths",
    "json_value_paths",
    "agent_resource_boundary",
    "agent_resource_retired_ref_rejects",
    "adapter_capability_rehome_case",
    "hook_registry_axis_case",
    "adapter_model_selection_case",
    "adapter_model_selection_rejects",
    "building_plan_boundary",
    "route_policy_boundary",
    "route_materialization_case",
    "transition_concern_disposition_case",
    "materialize_building_intent_case",
    "materialize_building_intent_rejects",
    "preset_building_completion_case",
    "adapter_gate_shape_union_case",
    "building_intake_seam_case",
    "intake_evidence_projection_case",
    "intake_project_vessel_case",
    "link_route_evidence_case",
    "run_once_task_source_admission_case",
    "onboard_seam_case",
    "agent_candidate_packet_case",
    "preset_ranking_packet_case",
    "compose_building_case",
    "compose_building_rejects",
    "write_scope_default_exclude_case",
    "source_fact_body_carry_case",
    "step_output_drain_case",
    "step_output_drain_rejects",
    "declared_step_template_plan_case",
    "declared_step_template_plan_rejects",
    "auto_repair_replay_case",
    "child_building_candidate_case",
    "native_dispatch_close_case",
    "workflow_import_case",
    "fail_fixture_rejects",
    "gate_sequence_policy_case",
    "gate_sequence_policy_rejects",
}
TOP_LEVEL_KEYS = {
    "schema",
    "profile_id",
    "description",
    "kernel_checks",
    "proof_limits",
    "not_proven",
} | RULE_KEYS


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
    for check_id in require_string_list(profile.get("kernel_checks", []), f"{path}: kernel_checks"):
        if check_id not in KERNEL_CHECK_IDS:
            raise ProfileError(f"{path}: unknown kernel check id: {check_id}")
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
    "agent_candidate_packet_case": run_agent_candidate_packet_case,
    "preset_ranking_packet_case": run_preset_ranking_packet_case,
    "compose_building_case": run_compose_building_case,
    "compose_building_rejects": run_compose_building_rejects,
    "write_scope_default_exclude_case": run_write_scope_default_exclude_case,
    "source_fact_body_carry_case": run_source_fact_body_carry_case,
    "step_output_drain_case": run_step_output_drain_case,
    "step_output_drain_rejects": run_step_output_drain_rejects,
    "declared_step_template_plan_case": run_declared_step_template_plan_case,
    "declared_step_template_plan_rejects": run_declared_step_template_plan_rejects,
    "auto_repair_replay_case": run_auto_repair_replay_case,
    "child_building_candidate_case": run_child_building_candidate_case,
    "native_dispatch_close_case": run_native_dispatch_close_case,
    "workflow_import_case": run_workflow_import_case,
    "fail_fixture_rejects": run_fail_fixture_rejects,
    "gate_sequence_policy_case": run_gate_sequence_policy_case,
    "gate_sequence_policy_rejects": run_gate_sequence_policy_rejects,
}


def run_kernel_check(repo: Path, check_id: str) -> KernelResult:
    if check_id == "axis_vocab_drift":
        return run_axis_vocab_drift(repo)
    if check_id == "package_path_admission":
        module = importlib.import_module("support.checkers.check_package_path_admission")
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
    if check_id == "axis_contract_projection":
        return call_main(
            check_id,
            "support.checkers.check_axis_contract_projection",
            ["--repo", str(repo)],
        )
    if check_id == "declared_verifier_exists":
        return call_main(
            check_id,
            "support.checkers.check_declared_verifier_exists",
            ["--repo", str(repo)],
        )
    if check_id == "axis_field_enum_parity":
        return call_main(
            check_id,
            "support.checkers.check_axis_field_enum_parity",
            ["--repo", str(repo)],
        )
    if check_id == "agentfact_single_home":
        return call_main(
            check_id,
            "support.checkers.check_agentfact_single_home",
            ["--repo", str(repo)],
        )
    if check_id == "building_root_anchor":
        return call_main(
            check_id,
            "support.checkers.check_building_root_anchor",
            ["--repo", str(repo)],
        )
    if check_id == "catalog_reader_sync":
        return call_main(
            check_id,
            "support.checkers.check_catalog_reader_sync",
            ["--repo", str(repo)],
        )
    if check_id == "agent_resource_resolution":
        return call_main(
            check_id,
            "support.checkers.check_agent_resource_resolution",
            ["--repo", str(repo)],
        )
    if check_id == "bricks_spec_completeness":
        return call_main(
            check_id,
            "support.checkers.check_bricks_spec_completeness",
            ["--repo", str(repo)],
        )
    if check_id == "building_lifecycle_path_shape":
        return call_main(
            check_id,
            "support.checkers.check_building_lifecycle_path_shape",
            ["--repo", str(repo)],
        )
    if check_id == "building_map_graph":
        return run_building_map_graph(repo)
    if check_id == "project_declaration":
        # PROJECT-0 S1: every project/<id>/ vessel must declare its charter
        # (README.md) + machine declaration (project.json, closed keys,
        # non-empty direction). Runs IN-PROCESS with anti-tautology probes
        # (violating vessels incl. non-slug ids + a symlinked vessel, slug-law
        # seam parity, creation rollback)
        # (violating synthetic vessels must be rejected); a non-zero main()
        # raises ProfileError, so an undeclared project vessel drives --all RED.
        return call_main(
            check_id,
            "support.checkers.check_project_declaration",
            ["--repo", str(repo)],
        )
    if check_id == "bounded_agent_proposed_routing_loop":
        # Executes the standalone walker checker IN-PROCESS: imports + runs the
        # real dynamic graph walker over adapter:local fixtures (adopt within
        # budget / HOLD on exhaustion / nested shares budget). A non-zero
        # main() raises ProfileError, so a broken walker invariant makes
        # --all EXIT non-zero (no longer text-admitted only).
        return call_main(
            check_id,
            "support.checkers.check_bounded_agent_proposed_routing_loop0",
            ["--repo", str(repo)],
        )
    if check_id == "building_operator_driver0":
        # Executes the standalone D2 portfolio driver checker IN-PROCESS: imports
        # + drives the real support/operator/driver.py over declared existing
        # adapter:local Building Plan refs, including the load-bearing negative
        # probes for bare default-transition and undeclared candidates.
        return call_main(
            check_id,
            "support.checkers.check_building_operator_driver0",
            ["--repo", str(repo)],
        )
    if check_id == "building_declaration_integrity":
        # Executes the declaration-integrity checker IN-PROCESS: runs the three
        # anti-tautological negative probes (composition-mode, chain artifacts,
        # provenance<->returned acceptance) AND inspects every persisted building
        # root. A probe that is not rejected, or a real root that violates the
        # invariant, makes main() return non-zero and raises ProfileError, so
        # --all EXITs non-zero.
        return call_main(
            check_id,
            "support.checkers.check_building_declaration_integrity",
            ["--repo", str(repo)],
        )
    if check_id == "building_plans_boundary_sweep":
        # Global building-plan boundary sweep: runs validate_building_plan_boundary
        # over every linear plan in brick/building_plans/, rehoming the per-profile
        # single-plan boundary pins into one general guard (pass-1 consolidation).
        return run_building_plans_boundary_sweep(repo)
    if check_id == "agent_adapter_return_shape":
        # Executes the required-return-shape waiver probe IN-PROCESS so the work
        # template's no_changes_reason wording cannot drift away from adapter
        # extraction or Brick comparison waiver behavior.
        return run_agent_adapter_return_shape(repo)
    if check_id == "provider_preflight":
        # ONBOARDING-PROVIDER-PREFLIGHT-0. Executes the friendly never-raising
        # provider preflight IN-PROCESS: imports preflight_provider and asserts it
        # returns a well-shaped status dict for an ACTIVE adapter + in-process
        # adapter:local, AND that it returns ok False (never raises) for a
        # deliberately bogus/retired adapter ref. If preflight_provider ever
        # raises (e.g. on a missing CLI), this kernel check goes RED and --all
        # EXITs non-zero. This is the no-raise guard for the onboarding "login"
        # step (a missing/unauthed provider must surface a plain-Korean message,
        # not a mid-run stack-trace).
        return run_provider_preflight(repo)
    if check_id == "onboard_smoke":
        # ONBOARDING-WIZARD-0. Executes the friendly never-raising onboarding flow
        # IN-PROCESS: imports run_onboard and drives the bundled adapter:local
        # example Building END-TO-END to a TEMP output_root (never the repo),
        # asserting it returns the structured {preflight, connect_hint,
        # example_result, handoff_message_ko, ok} dict with ok True + a building_id
        # + landed evidence, AND returns ok False (never raises) for a bogus host.
        # If run_onboard ever raises, this kernel check goes RED and --all EXITs
        # non-zero. This is the no-raise guard for the guided onboarding experience.
        return run_onboard_smoke(repo)
    if check_id == "install_script_lint":
        # ONBOARDING-INSTALL-SCRIPT-0. Structural/safety lint of the one-line
        # installer support/onboarding/install.sh IN-PROCESS: asserts set -eu, all
        # logic in main() invoked as 'main "$@"' on the LAST non-empty line
        # (anti-truncation), no http:// (HTTPS only), no /Users/ literal, no inline
        # secret pattern, and a reference to the onboard wizard entry. A violation
        # makes main() return non-zero and raises ProfileError, so --all EXITs
        # non-zero. PROOF LIMIT: structure/safety only -- it does NOT prove a real
        # fresh-machine install (clone/uv sync/provider auth = manual / Phase-4).
        return run_install_script_lint(repo)
    if check_id == "reporter_notification_projection":
        # Executes reporter validation probes IN-PROCESS. This keeps the profile
        # from merely text-pinning the presence of probe functions while never
        # observing that authority-leaking packets and unadmitted sinks reject.
        return run_reporter_notification_projection(repo)
    if check_id == "chat_session_park_seam":
        # Executes the chat-session S1 PARK seam IN-PROCESS over a temp project
        # Building root: declared adapter:chat-session must write a closed
        # AgentAdapterRequest envelope + distinct park record, stop before any
        # AgentFact, observe frontier_kind=chat_session_parked before incomplete,
        # map to the reporter intervention bell, and pass both lifecycle/path
        # admission checkers on the generated support evidence.
        return run_chat_session_park_seam(repo)
    if check_id == "mcp_stdio_smoke":
        # Execution smoke: bare-launches support/connection/mcp_projection.py with
        # a CLEAN env (no PYTHONPATH) like a real MCP host and asserts it answers
        # initialize without crashing at import. Catches the bootstrap regression
        # where the script forgets to put support/import_identity on sys.path and
        # crashes with ModuleNotFoundError: brick_protocol on a bare host launch.
        # The external bare-launch lives in the checker layer (kernel_checks.py),
        # never in mcp_projection.py, which owns no execution surface.
        return run_mcp_stdio_smoke(repo)
    if check_id == "connect_config_launch":
        # Execution proof for the CONNECT-GENERATOR-0 read-only generator: imports
        # support/connection/connect.py, renders the Codex MCP config for THIS
        # repo, extracts the command + server script + --repo it emits, then
        # externally launches EXACTLY that with a CLEAN env (no PYTHONPATH) and
        # pipes one initialize. Asserts a JSON-RPC result with no crash, that the
        # emitted script == <repo>/support/connection/mcp_projection.py (and
        # exists), and that connect.py source carries no hardcoded user-home path.
        # This proves "generated config -> actually working connection". The
        # external launch lives in the checker layer; connect.py runs none.
        return run_connect_config_launch(repo)
    if check_id == "claude_projection_native":
        # Execution proof that the Claude projection is a REAL Claude-native .md
        # subagent (--- YAML frontmatter --- + body), not a label-only generic
        # blob. Imports the read-only renderer (support/connection/
        # agent_resources.py) and asserts over admitted Agent Objects: (a)
        # render_claude_subagent_md parses with name/description/tools in the
        # frontmatter; (b) a REAL tool-policy -> tools mapping (dev read-write-
        # scoped tools INCLUDE Edit AND Write; a leader/reviewer EXCLUDES both),
        # so a constant tools list turns this RED; (c) the claude .md is
        # materially DIFFERENT from the codex TOML (markdown, not a TOML table);
        # (d) the "enforced by Brick MCP" honesty note is present in the body.
        # The renderer it pins spawns no external process and writes no file; the
        # checker imports it in-process.
        return run_claude_projection_native(repo)
    if check_id == "codex_projection_native":
        # Execution proof that the Codex projection is a REAL Codex-native TOML
        # subagent, not a label-only generic blob. Imports the read-only renderer
        # (support/connection/agent_resources.py) and asserts over admitted Agent
        # Objects: (a) render_codex_subagent_toml parses as valid TOML with the
        # required name/description/developer_instructions; (b) sandbox_mode is a
        # REAL tool-policy mapping (read-write-scoped dev -> workspace-write;
        # leader/reviewer read-only policies -> read-only), so a constant
        # sandbox_mode turns this RED; (c) the codex TOML is materially DIFFERENT
        # from the claude markdown seed; (d) developer_instructions carries the
        # "enforced by Brick MCP" honesty note. The renderer it pins spawns no
        # external process and writes no file; the checker imports it in-process.
        return run_codex_projection_native(repo)
    if check_id == "recording_checker_derived_contract":
        # Executes the standalone ζ6 checker IN-PROCESS: derives the dynamic-walker
        # evidence shape from support/recording/contracts.py and runs the real
        # walk, catching contract-required-field drift AND independent axis-value
        # drift. A non-zero main() raises ProfileError, so an evidence-contract
        # regression makes --all EXIT non-zero.
        return call_main(
            check_id,
            "support.checkers.check_recording_checker_derived_contract",
            ["--repo", str(repo)],
        )
    if check_id == "axis_crossing_elegance":
        # ELEGANT-REFACTOR P-guard. Executes the elegance guard IN-PROCESS: runs
        # the six anti-tautological G1-G6 negative probes AND validates the live
        # crossing_registry.yaml + module_registry.yaml + the support module
        # tree (one canonical contract per crossing, no mixing, cross-via-
        # canonical-only, every module registered, consume-not-author,
        # decomposition ceiling — a self-consistency check, not a one-way
        # ratchet; see check_axis_crossing_elegance G6 proof-limit). A probe
        # that is not rejected, or a real
        # registry/code violation, makes main() return non-zero and raises
        # ProfileError, so --all EXITs non-zero. Independent oracle: this checker
        # imports no axis module (and is not imported here in a way that would).
        return call_main(
            check_id,
            "support.checkers.check_axis_crossing_elegance",
            ["--repo", str(repo)],
        )
    if check_id == "tier_a_three_axis_conformance":
        # HALF-2 Tier A. Executes the conformance harness IN-PROCESS: runs the
        # anti-tautological FIRE probe (a degraded copy with the reroute trace and
        # declaration_provenance dropped MUST be reported unmet) AND asserts the
        # engine-produced tier-a-3axis-conformance-0 root carries all three axes +
        # Link mechanics + evidence + declaration_provenance. A probe that does not
        # fire, or an unmet assertion, makes main() return non-zero and raises
        # ProfileError, so --all EXITs non-zero. This is the deterministic
        # regression net re-run after each P3 extraction.
        return call_main(
            check_id,
            "support.checkers.check_tier_a_three_axis_conformance",
            ["--repo", str(repo)],
        )
    if check_id == "brick_template_catalog_restructure":
        # BRICK-TEMPLATE-CATALOG-RESTRUCTURE-0 P10 checker/FIRE closure. Executes
        # the split catalog checker IN-PROCESS: synthetic RED-first FIRE fixtures
        # prove stable problem codes, while live enforcement reads split
        # step_template_catalog.rows as active binding evidence after old compact
        # registry deletion. Link refs anchor in link/gate.py,
        # Agent refs in agent/objects payloads, link_word in link/movement.py,
        # and checker output remains support evidence only.
        return call_main(
            check_id,
            "support.checkers.check_brick_template_catalog_restructure",
            ["--repo", str(repo), "--mode", "p10-delete"],
        )
    if check_id == "evidence_spine":
        # U5.5 SLICE-1A. Executes the spine structural checker IN-PROCESS over
        # every persisted building root: for each building tagged
        # evidence_generation == u5_5_live it verifies pairing (.md ==
        # render(.json)), the content/prev hash chain, monotonic sequence_index +
        # run_segment, spine.json/.jsonl/.md == re-derived from events/, admitted
        # event types + axis scope, and no forbidden success/quality key.
        # Untagged (pre-U5.5) buildings are skipped, so existing evidence is
        # untouched. A real spine violation makes main() return non-zero and
        # raises ProfileError, so --all EXITs non-zero.
        return call_main(
            check_id,
            "support.checkers.check_evidence_spine",
            ["--repo", str(repo)],
        )
    if check_id == "evidence_spine_projection":
        # U5.5 SLICE-2. Executes the spine PROJECTION-completeness checker
        # IN-PROCESS over every persisted building root: for each building tagged
        # evidence_generation == u5_5_live it verifies the spine projection covers
        # the building-scope declarations (exactly one each of PresetExpansion and
        # LinkLaunchPolicy in events/). This is the coverage guard, complementary
        # to evidence_spine (the structural guard). Untagged (pre-U5.5) buildings
        # are skipped, so existing evidence is untouched. A real coverage gap makes
        # main() return non-zero and raises ProfileError, so --all EXITs non-zero.
        return call_main(
            check_id,
            "support.checkers.check_evidence_spine_projection",
            ["--repo", str(repo)],
        )
    if check_id == "pin_estate_integrity":
        # TREASURE PORT 1 (ACTIVE-SPEC-SPINE disciplines, concept-lifted from
        # d5bc86e:support/checkers/check_doc_grounding.py). Executes the
        # pin-estate checker IN-PROCESS: (a) rejects decorative history-doc pins
        # (path-existence-only / blank needles / keyless json_required_paths),
        # (b) runs adversarial pin probes (temp copy of the pinned doc, mutate
        # the pinned text, the REAL text_rule runner must RED — proving the
        # surviving KEEP-LIVE/GUARD-ONLY pins actually fire), and (c) enforces
        # the pin-estate ratchet (estate count changes — path_exists/path_absent
        # items, text_contains/text_absent blocks, and json_required_paths
        # blocks on the history prefixes — vs support/checkers/
        # pin_estate_baseline.yaml without a new dated human disposition entry
        # RED; tamper-EVIDENT, not tamper-proof — see the checker docstring).
        # Six synthetic FIRE probes run RED-first on every invocation; a
        # non-rejecting probe makes main() return non-zero, so --all EXITs
        # non-zero.
        return call_main(
            check_id,
            "support.checkers.check_pin_estate_integrity",
            ["--repo", str(repo)],
        )
    if check_id == "agent_session_id_redaction":
        # TREASURE PORT 2 (lifted from 2d44fc7:support/checkers/lib/
        # kernel_checks.py run_agent_session_id_redaction). Forbids any
        # provider/runtime session id (bare UUID/ULID, keyed session_id/
        # conversation_id forms, sess_/sess-/provider-session-/resume-token-/
        # chatcmpl-/ya29./JWT tokens) in the kernel/buildings/reviews/archive
        # surfaces. Operator policy 0611: frozen building evidence and archived
        # history are NOT rewritten; the 6 investigator-verified legacy leak
        # files are carried on an explicit per-path allowlist of frozen
        # line-content sha256[:16] hashes (codex-review tightening C: every
        # offending line must match a frozen allowlisted line — count<=budget
        # is no longer sufficient), and any NEW leak (outside the allowlist,
        # or any non-matching/extra line inside an allowlisted file) REDs.
        return run_agent_session_id_redaction(repo)
    raise ProfileError(f"unknown kernel check id: {check_id}")


def run_profile(repo: Path, path: Path) -> tuple[int, list[KernelResult]]:
    repo_text = str(repo)
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)
    profile = read_profile(path)
    rule_count = 0
    for key in sorted(RULE_RUNNERS):
        rule_count += RULE_RUNNERS[key](repo, profile)
    kernel_results = [
        run_kernel_check(repo, check_id)
        for check_id in require_string_list(profile.get("kernel_checks", []), "kernel_checks")
    ]
    print(
        f"profile passed: {profile['profile_id']} "
        f"({rule_count} declarative rule observation(s), "
        f"{sum(result.inspected for result in kernel_results)} kernel target(s) inspected)"
    )
    for result in kernel_results:
        first_line = result.output.splitlines()[0] if result.output else "no output"
        print(f"- {result.check_id}: {first_line}")
    return rule_count, kernel_results


def write_self_test_files(root: Path) -> Path:
    repo = root / "repo"
    (repo / "support/checkers/profiles").mkdir(parents=True)
    (repo / "support/checkers").mkdir(parents=True, exist_ok=True)
    (repo / "link").mkdir()
    (repo / "project/brick-protocol/buildings/demo/work").mkdir(parents=True)
    (repo / "notes").mkdir()
    (repo / "notes/keep.txt").write_text("Brick Agent Link\n", encoding="utf-8")
    # The hook-registry axis guard scans agent/hooks/registry.yaml on EVERY
    # profile run (always-on), so the synthetic self-test repo needs a minimal
    # valid registry fixture.
    (repo / "agent/hooks").mkdir(parents=True)
    (repo / "agent/hooks/registry.yaml").write_text(
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
    (repo / "link/movement.yaml").write_text(
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
    profile_path_value = repo / "support/checkers/profiles/self.yaml"
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
                "  - root: support/checkers/profiles",
                "    paths:",
                "      - support/checkers/profiles/self.yaml",
                "text_contains:",
                "  - path: notes/keep.txt",
                "    text: Brick",
                "text_absent:",
                "  - path: notes/keep.txt",
                "    text: source truth",
                "yaml_literal_set:",
                "  - path: link/movement.yaml",
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
        bad_profile = dict(read_profile(profile))
        bad_profile["kernel_checks"] = ["support/checkers/check_package_path_admission.py"]
        try:
            validate_profile(bad_profile, profile)
        except ProfileError:
            print("self-test passed: arbitrary checker file path rejected")
        else:
            raise ProfileError("self-test failed: arbitrary checker file path was accepted")
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
    parser.add_argument("--all", action="store_true", help="Run every support/checkers/profiles/*.yaml profile.")
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
        for path in profile_paths(repo, args):
            run_profile(repo, path)
        print(PROOF_LIMIT)
        return 0
    except (OSError, json.JSONDecodeError, ProfileError) as exc:
        print(f"profile runner rejected evidence: {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

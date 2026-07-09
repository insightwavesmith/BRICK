"""In-process kernel-check bodies + axis-vocab drift scan + subprocess shim.

Lifted verbatim from check_profile.py (P3a behavior-preserving decomposition).
Holds the kernel-check implementations the profile runner's run_kernel_check
dispatches to (axis_vocab_drift, building_map_graph, agent_adapter_return_shape,
reporter_notification_projection) plus the in-process call_main shim. Support
checker mechanics only: it derives/observes evidence shapes; it authors no axis
crossing and decides nothing.
"""

from __future__ import annotations

import argparse
import ast
import base64
import contextlib
import hashlib
import hmac
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
    to_posix,
    to_repo_path,
)
from brick_protocol.support.checkers.lib.provider_preflight_check import (
    _PROVIDER_PREFLIGHT_AUTHED_LITERALS,
    _PROVIDER_PREFLIGHT_REQUIRED_KEYS,
    _provider_preflight_assert_shape,
    run_provider_preflight,
)
from brick_protocol.support.checkers.lib.onboard_smoke_check import (
    _ONBOARD_SMOKE_REQUIRED_KEYS,
    run_onboard_smoke,
    _onboard_smoke_assert_shape,
)


from brick_protocol.support.checkers.lib.axis_vocab_drift_check import (
    _AXIS_VOCAB_EXPECTED_MOVEMENT,
    _AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS,
    _AXIS_VOCAB_EXPECTED_DISPOSITION_OWNERS,
    _AXIS_VOCAB_EXPECTED_PROGRESS_STATES,
    _AXIS_VOCAB_EXPECTED_AUTHOR_PREFIXES,
    _AXIS_VOCAB_REQUIRED_TRANSITION_KEYS,
    _AXIS_VOCAB_CONCERN_KIND_SOURCE,
    _AXIS_VOCAB_CONCERN_KIND_CONST,
    _AXIS_VOCAB_CONCERN_KIND_DOC,
    _AXIS_VOCAB_CONCERN_KIND_DOC_HEADER,
    _AXIS_VOCAB_EXPECTED_ADAPTER_REFS,
    _AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS,
    _AXIS_VOCAB_DOC_PATHS,
    _AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST,
    _AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST,
    _AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST,
    _AXIS_VOCAB_TRANSITION_AUTHOR_PREFIX_CONSUMERS,
    _AXIS_VOCAB_PYTHON_SCAN_ROOTS,
    _axis_vocab_parse_python,
    _axis_vocab_read_literal,
    _axis_vocab_all_strings,
    _axis_vocab_module_env,
    _axis_vocab_sequence,
    _axis_vocab_set,
    _axis_vocab_literal_string_set,
    _axis_vocab_import_aliases,
    _axis_vocab_absolute_import_aliases,
    _axis_vocab_assigned_names,
    _axis_vocab_name_used,
    _axis_vocab_python_files,
    _axis_vocab_scan_exact_enum_redefinitions,
    _axis_vocab_check_link_sources,
    _axis_vocab_check_transition_author_prefix_consumers,
    _axis_vocab_check_docs,
    _axis_vocab_check_agent_adapter_refs,
    _axis_vocab_doc_fenced_block,
    _axis_vocab_check_concern_kind_parity,
    run_axis_vocab_drift,
)
from brick_protocol.support.checkers.lib.building_plan_graph_check import (
    run_building_map_graph,
    run_building_plans_boundary_sweep,
)
from brick_protocol.support.checkers.lib.building_result_summary_check import (
    _assert_no_forbidden_summary_key,
    _init_git_repo_with_wip_anchor,
    _write_json,
    _write_jsonl,
    run_building_result_summary,
)
from brick_protocol.support.checkers.lib.deliverable_crosscheck_gate_check import (
    run_deliverable_crosscheck_gate,
)
from brick_protocol.support.checkers.lib.re_instruction_endline_gate_check import (
    run_re_instruction_endline_gate,
)
from brick_protocol.support.checkers.lib.raw_evidence_stream_scrub_check import run_raw_evidence_stream_scrub
from brick_protocol.support.checkers.lib.agent_output_text_preservation_check import (
    run_agent_output_text_preservation,
)
from brick_protocol.support.checkers.lib.agent_adapter_return_shape_check import (
    _agent_adapter_request_instruction_packet_probe,
    _agent_effective_write_probe,
    _agent_instruction_packet_probe,
    _agent_read_tier_probe,
    _artifact_grounding_probe,
    _proof_obligation_pipeline_probe,
    run_agent_adapter_return_shape,
)
from brick_protocol.support.checkers.lib.brick_cli_entrypoint_check import (
    run_brick_cli_entrypoint_smoke,
    run_customer_project_progress_cli,
)
from brick_protocol.support.checkers.lib.mcp_connect_projection_check import (
    run_claude_projection_native,
    run_codex_projection_native,
    run_connect_config_launch,
    run_mcp_stdio_smoke,
)
from brick_protocol.support.checkers.lib.chat_session_park_check import (
    _chat_session_assert_envelope_session_key_rejects,
    _chat_session_assert_key_scan_fire,
    _chat_session_assert_undeclared_adapter_rejects,
    _chat_session_delete_work_envelope,
    _chat_session_mutate_envelope_uuid,
    _chat_session_mutate_park_as_adapter_error,
    _chat_session_park_graph_plan,
    _chat_session_probe_ulid_text,
    _chat_session_probe_uuid_text,
    _chat_session_value_only_session_rejector,
    _chat_session_write_temp_project_declaration,
    run_chat_session_park_seam,
)
from brick_protocol.support.checkers.lib.adapter_error_check import (
    run_adapter_error_frontier_manifest_consistency,
    run_adapter_error_path_hardening,
)
from brick_protocol.support.checkers.lib.agent_session_id_redaction_check import run_agent_session_id_redaction
from brick_protocol.support.checkers.lib.dashboard_productization_projection_check import (
    run_dashboard_productization_projection,
)
from brick_protocol.support.checkers.lib.sakana_wire_packet_check import run_sakana_wire_packet

# chat_session_park_seam facade pins retained for unchanged profiles after pure relocation:
# _chat_session_mutate_envelope_uuid / _chat_session_mutate_park_as_adapter_error /
# _chat_session_delete_work_envelope / _chat_session_assert_undeclared_adapter_rejects /
# _chat_session_assert_envelope_session_key_rejects / _chat_session_assert_key_scan_fire /
# _chat_session_value_only_session_rejector / _chat_session_probe_uuid_text /
# _chat_session_probe_ulid_text
# agent_session_id_redaction facade retained for unchanged check_profile dispatch.
# Facade text pins retained for unchanged profiles after pure relocation:
# raw_evidence_stream_scrub / brick-work.jsonl / agent-received.jsonl /
# agent-return.jsonl / agent-output-text.jsonl / adapter-error.jsonl
# agent_output_text_preservation / mutation RED observed / AgentFact.returned
# agent_adapter_return_shape facade text pins retained for unchanged profiles after pure relocation:
# gemini-local read-write-scoped request did not enter read tier
# gemini-local non-zero adapter error omitted
# gemini-client-error-probe.json
# brick_cli_entrypoint_smoke / customer graph_packet may not author Brick template-owned field
# hidden _p3_easy_large_graph_packet helper / status revived legacy ~/.brick/builds
# plain CLI error leaked raw operator detail / internal/onboard route became public
# --dev-lanes became a public official build mode
# lane_return helper must stay absent/fail-closed
# support-only observation lost proof limit
# bare brick --json did not default to status
# status packet omitted adapter_boundary_matrix



@contextlib.contextmanager
def captured_output() -> Any:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        yield out, err


@contextlib.contextmanager
def patched_argv(argv: list[str]) -> Any:
    previous = sys.argv[:]
    sys.argv = argv
    try:
        yield
    finally:
        sys.argv = previous


from brick_protocol.support.checkers.lib.reporter_notification_projection_check import (
    _minimal_reporter_packet,
    run_reporter_notification_projection,
)

# reporter_notification_projection facade text pins retained for unchanged profiles after pure relocation:
# reporter negative probe(s) / owner vocabulary probe(s) / delivery wake probe(s) /
# label parity map(s) / Slack message shape assertion(s) / auto-wire assertion(s) /
# no-scheduler source file(s) / local inbox write / operator wake write /
# event hook probe(s) / raw secret shaped field / unadmitted sink reject



def call_main(check_id: str, module_name: str, argv: list[str] | None) -> KernelResult:
    module = importlib.import_module(module_name)
    with captured_output() as (out, err):
        if argv is None:
            with patched_argv([check_id]):
                code = int(module.main())
        elif check_id == "package_path_admission":
            with patched_argv([check_id] + argv):
                code = int(module.main())
        else:
            code = int(module.main(argv))
    output = (out.getvalue() + err.getvalue()).strip()
    if code != 0:
        raise ProfileError(f"kernel check {check_id} rejected evidence:\n{output}")
    return KernelResult(check_id=check_id, inspected=1, output=output)


def run_building_call_authoring_contract(repo: Path) -> KernelResult:
    """Validate the ⑤f positive fixture and reject the sequence-violation fixture."""

    from brick_protocol.support.operator.building_call_authoring import (
        AUTHORING_STEP_REFS,
        BuildingCallAuthoringValidationError,
        normalize_building_call_authoring_return,
        render_authoring_sequence_rule,
        validate_building_call_authoring_return,
    )

    fixture_root = repo / "brick_protocol/support/checkers/fixtures/building_call_authoring"
    positive_path = fixture_root / "positive_return.json"
    negative_path = fixture_root / "negative_sequence_violation.json"
    positive = json.loads(positive_path.read_text(encoding="utf-8"))
    negative = json.loads(negative_path.read_text(encoding="utf-8"))

    normalized = normalize_building_call_authoring_return(positive)
    if normalized["five_step_order"] != list(AUTHORING_STEP_REFS):
        raise ProfileError("building_call_authoring_contract: positive fixture order was not preserved")

    negative_violations = validate_building_call_authoring_return(negative)
    if not negative_violations:
        raise ProfileError(
            "building_call_authoring_contract: negative sequence fixture was accepted"
        )
    if not any("five_step_order must be exactly" in item for item in negative_violations):
        raise ProfileError(
            "building_call_authoring_contract: negative fixture did not trip the sequence-order violation"
        )
    try:
        normalize_building_call_authoring_return(negative)
    except BuildingCallAuthoringValidationError:
        pass
    else:
        raise ProfileError(
            "building_call_authoring_contract: negative fixture normalization did not fail closed"
        )

    sequence_rule = render_authoring_sequence_rule()
    if sequence_rule["step_refs"] != list(AUTHORING_STEP_REFS):
        raise ProfileError("building_call_authoring_contract: sequence-rule render drifted")

    unknown_top_level = dict(positive)
    unknown_top_level["route_target_hint"] = "brick-next"
    unknown_violations = validate_building_call_authoring_return(unknown_top_level)
    if not any("unknown top-level field(s): route_target_hint" in item for item in unknown_violations):
        raise ProfileError(
            "building_call_authoring_contract: unknown top-level field probe was accepted"
        )

    remaining_delta_exposure = dict(positive)
    remaining_delta_exposure["remaining_delta"] = ["please use adapter:codex-local now"]
    remaining_delta_violations = validate_building_call_authoring_return(remaining_delta_exposure)
    if not any(
        "forbidden draft value marker at remaining_delta[0]" in item
        for item in remaining_delta_violations
    ):
        raise ProfileError(
            "building_call_authoring_contract: remaining_delta adapter exposure probe was accepted"
        )

    nested_scan_exposure = dict(positive)
    nested_scan_exposure["forbidden_exposure_scan"] = {"Selected_Adapter_Ref": "absent"}
    nested_scan_violations = validate_building_call_authoring_return(nested_scan_exposure)
    if not any(
        "forbidden draft key: forbidden_exposure_scan.Selected_Adapter_Ref" in item
        for item in nested_scan_violations
    ):
        raise ProfileError(
            "building_call_authoring_contract: forbidden_exposure_scan key probe was accepted"
        )

    embedded_case_exposure = dict(positive)
    embedded_case_exposure["scope_draft"] = {
        **positive["scope_draft"],
        "note": "Operator asked for Adapter:codex-local",
    }
    embedded_case_violations = validate_building_call_authoring_return(embedded_case_exposure)
    if not any(
        "forbidden draft value marker at scope_draft.note" in item
        for item in embedded_case_violations
    ):
        raise ProfileError(
            "building_call_authoring_contract: embedded case-varied adapter exposure probe was accepted"
        )

    return KernelResult(
        check_id="building_call_authoring_contract",
        inspected=6,
        output=(
            "positive fixture accepted; negative sequence-violation fixture rejected; "
            "unknown top-level, remaining_delta exposure, forbidden_exposure_scan key, "
            "and embedded case-varied exposure probes rejected"
        ),
    )


def run_building_call_lowering_contract(repo: Path) -> KernelResult:
    """Validate ⑤g confirmed-only Building Call lowering fixtures."""

    from brick_protocol.support.operator.building_call import (
        BuildingCallLoweringError,
        building_call_lowering_v1,
        render_building_call_lowering_cases,
        validate_building_call_lowering_request,
    )

    fixture_root = repo / "brick_protocol/support/checkers/fixtures/building_call_lowering"
    positive = json.loads((fixture_root / "positive_confirmed_request.json").read_text(encoding="utf-8"))
    draft = json.loads((fixture_root / "negative_draft_request.json").read_text(encoding="utf-8"))
    held = json.loads((fixture_root / "negative_held_for_coo_review.json").read_text(encoding="utf-8"))

    lowered = building_call_lowering_v1(positive)
    intent = lowered.get("lowered_intent")
    if not isinstance(intent, Mapping):
        raise ProfileError("building_call_lowering_contract: lowered_intent missing")
    if intent.get("chain_preset_ref") != "building-chain-preset:app-feature-inspected":
        raise ProfileError("building_call_lowering_contract: building_case did not lower to expected preset")
    if "step_selection_overrides" not in intent:
        raise ProfileError("building_call_lowering_contract: roster variant/override did not lower")
    overrides = intent["step_selection_overrides"]
    if not isinstance(overrides, Mapping):
        raise ProfileError("building_call_lowering_contract: step_selection_overrides not a mapping")
    work_row = overrides.get("building-step-template:work")
    review_row = overrides.get("building-step-template:review")
    if not isinstance(work_row, Mapping) or work_row.get("casting_tier_ref") != "casting-tier:deep":
        raise ProfileError("building_call_lowering_contract: deep_work variant did not lower")
    if not isinstance(review_row, Mapping) or review_row.get("casting_tier_ref") != "casting-tier:light":
        raise ProfileError("building_call_lowering_contract: explicit roster override did not lower")
    if "selected_adapter_ref" in review_row or "selected_model_ref" in review_row:
        raise ProfileError("building_call_lowering_contract: concrete selected_* leaked into step override")
    provenance = lowered.get("selected_casting_provenance")
    if not isinstance(provenance, Mapping) or provenance.get("roster_variant") != "deep_work":
        raise ProfileError("building_call_lowering_contract: selected_casting_provenance missing")

    draft_violations = validate_building_call_lowering_request(draft)
    if not any("kind must be confirmed_building_call_request_v1_1" in item for item in draft_violations):
        raise ProfileError("building_call_lowering_contract: draft fixture did not trip kind guard")
    if not any("confirmation_state must be confirmed" in item for item in draft_violations):
        raise ProfileError("building_call_lowering_contract: draft fixture did not trip confirmation guard")
    try:
        building_call_lowering_v1(draft)
    except BuildingCallLoweringError:
        pass
    else:
        raise ProfileError("building_call_lowering_contract: draft fixture normalization did not fail closed")

    held_violations = validate_building_call_lowering_request(held)
    if not any("held_for_coo_review requests must not be lowered" in item for item in held_violations):
        raise ProfileError("building_call_lowering_contract: held fixture did not trip hold guard")

    selected_exposure = dict(positive)
    selected_exposure["roster_overrides"] = [
        {
            "step_template_ref": "building-step-template:work",
            "selected_adapter_ref": "adapter:codex-local",
        }
    ]
    selected_violations = validate_building_call_lowering_request(selected_exposure)
    if not any("observed selected_adapter_ref" in item for item in selected_violations):
        raise ProfileError("building_call_lowering_contract: selected_* roster override was accepted")

    launch_probe = dict(positive)
    launch_probe["movement_choice"] = "forward"
    launch_violations = validate_building_call_lowering_request(launch_probe)
    if not any("forbidden request field(s): movement_choice" in item for item in launch_violations):
        raise ProfileError("building_call_lowering_contract: movement field probe was accepted")

    cases = render_building_call_lowering_cases()
    case_map = cases.get("building_case_to_chain_preset_ref")
    if not isinstance(case_map, Mapping) or case_map.get("order_authoring") != "building-chain-preset:building-call-authoring":
        raise ProfileError("building_call_lowering_contract: case table render drifted")

    return KernelResult(
        check_id="building_call_lowering_contract",
        inspected=7,
        output=(
            "confirmed fixture lowered; draft and held fixtures rejected; selected_* "
            "override and movement field probes rejected"
        ),
    )


def run_building_call_direct_escape_contract(repo: Path) -> KernelResult:
    """Validate ⑤h direct-preset admission and fast-confirm fixtures."""

    from brick_protocol.support.operator.building_call import (
        BuildingCallLoweringError,
        building_call_direct_preset_admission_v1,
        render_building_call_direct_preset_policy,
        validate_building_call_direct_preset_admission_request,
    )

    fixture_root = repo / "brick_protocol/support/checkers/fixtures/building_call_direct_escape"
    quick_fix = json.loads((fixture_root / "positive_quick_fix.json").read_text(encoding="utf-8"))
    quick_check = json.loads((fixture_root / "positive_quick_check.json").read_text(encoding="utf-8"))
    standard = json.loads((fixture_root / "negative_standard_delivery_direct.json").read_text(encoding="utf-8"))
    missing_fast = json.loads((fixture_root / "negative_missing_fast_confirm.json").read_text(encoding="utf-8"))
    red_flag = json.loads((fixture_root / "negative_red_flag_direct.json").read_text(encoding="utf-8"))
    critical = json.loads((fixture_root / "negative_critical_red_flag_direct.json").read_text(encoding="utf-8"))

    quick_fix_evidence = building_call_direct_preset_admission_v1(quick_fix)
    if quick_fix_evidence.get("routing_mode_evidence") != "direct_preset":
        raise ProfileError("building_call_direct_escape_contract: quick_fix did not direct")
    if quick_fix_evidence.get("chain_preset_ref") != "building-chain-preset:fast-fix":
        raise ProfileError("building_call_direct_escape_contract: quick_fix preset drifted")
    if "lowered_intent" not in quick_fix_evidence:
        raise ProfileError("building_call_direct_escape_contract: quick_fix did not lower")

    quick_check_evidence = building_call_direct_preset_admission_v1(quick_check)
    if quick_check_evidence.get("chain_preset_ref") != "building-chain-preset:quick-check":
        raise ProfileError("building_call_direct_escape_contract: quick_check preset drifted")

    standard_violations = validate_building_call_direct_preset_admission_request(standard)
    if not any("quick_fix or quick_check" in item for item in standard_violations):
        raise ProfileError("building_call_direct_escape_contract: standard_delivery direct was accepted")
    for fixture, expected, label in (
        (missing_fast, "fast_confirm is required before direct lowering", "missing fast_confirm"),
        (red_flag, "red flags require order_authoring", "red flag"),
        (critical, "critical red flags require human_gate_first", "critical red flag"),
    ):
        violations = validate_building_call_direct_preset_admission_request(fixture)
        if not any(expected in item for item in violations):
            raise ProfileError(f"building_call_direct_escape_contract: {label} fixture was accepted")
        try:
            building_call_direct_preset_admission_v1(fixture)
        except BuildingCallLoweringError:
            pass
        else:
            raise ProfileError(f"building_call_direct_escape_contract: {label} fixture normalized")

    exposure_probe = dict(quick_fix)
    exposure_probe["selected_model_ref"] = "model:codex:default"
    exposure_violations = validate_building_call_direct_preset_admission_request(exposure_probe)
    if not any("selected_model_ref" in item for item in exposure_violations):
        raise ProfileError("building_call_direct_escape_contract: selected_* exposure was accepted")

    for field_name in ("model", "provider", "model_ref", "provider_ref", "adapter_ref"):
        exposure_probe = dict(quick_fix)
        exposure_probe[field_name] = "request-facing exposure"
        exposure_violations = validate_building_call_direct_preset_admission_request(exposure_probe)
        if not any(field_name in item for item in exposure_violations):
            raise ProfileError(f"building_call_direct_escape_contract: {field_name} exposure was accepted")

    malformed_flag_probes = (
        (
            "red flag bool",
            "red_flags",
            True,
            "red_flags must be text or an array of text",
        ),
        (
            "red flag int",
            "red_flags",
            1,
            "red_flags must be text or an array of text",
        ),
        (
            "critical red flag mapping",
            "critical_red_flags",
            {"reason": "credential exposure risk"},
            "critical_red_flags must be text or an array of text",
        ),
        (
            "critical red flag object list",
            "critical_red_flags",
            [{"severity": "critical", "reason": "credential exposure risk"}],
            "critical_red_flags[0] must be text",
        ),
    )
    for label, field_name, field_value, expected in malformed_flag_probes:
        malformed_probe = dict(quick_fix)
        malformed_probe[field_name] = field_value
        violations = validate_building_call_direct_preset_admission_request(malformed_probe)
        if not any(expected in item for item in violations):
            raise ProfileError(f"building_call_direct_escape_contract: {label} was accepted")
        try:
            building_call_direct_preset_admission_v1(malformed_probe)
        except BuildingCallLoweringError:
            pass
        else:
            raise ProfileError(f"building_call_direct_escape_contract: {label} normalized")

    policy = render_building_call_direct_preset_policy()
    if policy.get("default_routing_mode_evidence") != "order_authoring":
        raise ProfileError("building_call_direct_escape_contract: default route evidence drifted")
    if policy.get("fast_confirm_required") is not True:
        raise ProfileError("building_call_direct_escape_contract: fast_confirm policy drifted")

    return KernelResult(
        check_id="building_call_direct_escape_contract",
        inspected=16,
        output=(
            "quick_fix and quick_check lowered only after admission + fast_confirm; "
            "standard_delivery, missing fast_confirm, red flag, critical red flag, "
            "selected_*, provider/model/adapter, and malformed red-flag probes rejected"
        ),
    )





























from brick_protocol.support.checkers.lib.design_ai_text_seams_check import run_design_ai_text_seams
from brick_protocol.support.checkers.lib.codex_connect_stall_classification_check import (
    run_codex_connect_stall_classification,
)
from brick_protocol.support.checkers.lib.gemini_local_only_adapter_check import run_gemini_local_only_adapter
from brick_protocol.support.checkers.lib.graph_topology_fan_barrier import run_graph_topology_fan_barrier


# FINAL architecture leaf (0630): the install_script_lint + release_export_exclusion
# cluster moved VERBATIM into the flat checker-lib sibling
# install_release_export_lint_check.py (conservation ledger
# customer-ready-final-architecture-install-release-export-lint-ledger-0630.md).
# Re-exported here so check_profile imports stay byte-identical.
from brick_protocol.support.checkers.lib.install_release_export_lint_check import (
    _INSTALL_SCRIPT_REL,
    _RELEASE_EXPORT_REL,
    _RELEASE_EXPORT_REQUIRED_EXCLUSIONS,
    _INSTALL_SCRIPT_SECRET_PATTERNS,
    run_install_script_lint,
    _release_export_exclusions,
    _release_export_exclusion_violations,
    _release_export_exclusion_fire_probe,
    run_release_export_exclusion,
    run_release_gate_contract,
)


# FINAL architecture leaf (0630): the product no-Smith-residue scan cluster
# moved VERBATIM into the flat checker-lib sibling no_smith_residue_check.py
# (conservation ledger customer-ready-final-architecture-no-smith-residue-ledger-0630.md).
# Re-exported here so check_profile imports and the in-file _SMITH_USER_HOME_LITERAL
# call site stay byte-identical.
from brick_protocol.support.checkers.lib.no_smith_residue_check import (
    _SMITH_USER_HOME_LITERAL,
    _SMITH_GITHUB_ORG_LITERAL,
    _SMITH_GITHUB_REPO_LITERAL,
    _NO_SMITH_RESIDUE_SURFACES,
    _no_smith_residue_text_paths,
    _no_smith_residue_allowed_org_line,
    _collect_no_smith_residue_violations,
    _copy_no_smith_residue_surfaces,
    _no_smith_residue_fire_probe,
    run_product_no_smith_residue,
)

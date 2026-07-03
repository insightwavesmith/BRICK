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

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
    to_posix,
    to_repo_path,
)
from support.checkers.lib.provider_preflight_check import (
    _PROVIDER_PREFLIGHT_AUTHED_LITERALS,
    _PROVIDER_PREFLIGHT_REQUIRED_KEYS,
    _provider_preflight_assert_shape,
    run_provider_preflight,
)
from support.checkers.lib.onboard_smoke_check import (
    _ONBOARD_SMOKE_REQUIRED_KEYS,
    run_onboard_smoke,
    _onboard_smoke_assert_shape,
)


from support.checkers.lib.axis_vocab_drift_check import (
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
from support.checkers.lib.building_plan_graph_check import (
    run_building_map_graph,
    run_building_plans_boundary_sweep,
)
from support.checkers.lib.building_result_summary_check import (
    _assert_no_forbidden_summary_key,
    _init_git_repo_with_wip_anchor,
    _write_json,
    _write_jsonl,
    run_building_result_summary,
)
from support.checkers.lib.raw_evidence_stream_scrub_check import run_raw_evidence_stream_scrub
from support.checkers.lib.agent_output_text_preservation_check import (
    run_agent_output_text_preservation,
)
from support.checkers.lib.agent_adapter_return_shape_check import (
    _agent_adapter_request_instruction_packet_probe,
    _agent_effective_write_probe,
    _agent_instruction_packet_probe,
    _agent_read_tier_probe,
    _artifact_grounding_probe,
    _proof_obligation_pipeline_probe,
    run_agent_adapter_return_shape,
)
from support.checkers.lib.brick_cli_entrypoint_check import run_brick_cli_entrypoint_smoke
from support.checkers.lib.mcp_connect_projection_check import (
    run_claude_projection_native,
    run_codex_projection_native,
    run_connect_config_launch,
    run_mcp_stdio_smoke,
)
from support.checkers.lib.chat_session_park_check import (
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
from support.checkers.lib.adapter_error_check import (
    run_adapter_error_frontier_manifest_consistency,
    run_adapter_error_path_hardening,
)
from support.checkers.lib.agent_session_id_redaction_check import run_agent_session_id_redaction
from support.checkers.lib.dashboard_productization_projection_check import (
    run_dashboard_productization_projection,
)

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


from support.checkers.lib.reporter_notification_projection_check import (
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




























def _gemini_api_classify_error_kind(exc: Exception) -> str:
    """Read-only mirror of run.py._adapter_error_kind (we cannot edit run.py).

    The B2-hardened hold path classifies adapter exceptions by type/message. We
    replicate the mapping here ONLY to assert (in-process) that a gemini-api
    no-key error flows the SAME clean typed adapter-error path, never a crash.

    INTENTIONAL DIVERGENCE from run.py._adapter_error_kind (codex-review F4): the
    TimeoutExpired branch here maps to plain 'local_cli_timeout' and is NOT given
    the connect-stall split. Gemini is an HTTP API adapter with no codex
    dead-connection watchdog, so a stall-tagged TimeoutExpired can never reach it
    and 'local_cli_connect_stall' is correctly absent. Every OTHER branch mirrors
    run.py._adapter_error_kind.
    """
    message = str(exc).lower()
    if isinstance(exc, FileNotFoundError):
        return "local_cli_missing"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "local_cli_timeout"
    if "non-zero" in message or "returned non-zero" in message:
        return "local_cli_nonzero"
    if "returned payload" in message or "forbidden returned" in message:
        return "adapter_return_shape_rejected"
    return "adapter_exception"


from support.checkers.lib.design_ai_text_seams_check import run_design_ai_text_seams
from support.checkers.lib.codex_connect_stall_classification_check import (
    run_codex_connect_stall_classification,
)
from support.checkers.lib.gemini_local_only_adapter_check import run_gemini_local_only_adapter
from support.checkers.lib.graph_topology_fan_barrier import run_graph_topology_fan_barrier


# FINAL architecture leaf (0630): the install_script_lint + release_export_exclusion
# cluster moved VERBATIM into the flat checker-lib sibling
# install_release_export_lint_check.py (conservation ledger
# customer-ready-final-architecture-install-release-export-lint-ledger-0630.md).
# Re-exported here so check_profile imports stay byte-identical.
from support.checkers.lib.install_release_export_lint_check import (
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
from support.checkers.lib.no_smith_residue_check import (
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

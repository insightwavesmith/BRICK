#!/usr/bin/env python3
"""Check that the current package path set has not opened forbidden surfaces."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_MODULE_REGISTRY = Path(__file__).resolve().parent / "module_registry.yaml"


def _registry_checker_files(registry_path: Path) -> frozenset[str]:
    """Single-source the admitted checker-file set from module_registry.yaml.

    CHECKER-CONSOLIDATION-0: this set used to be hand-maintained here AND
    duplicated in a now-retired cascade-sweep FINAL_CHECKER_ALLOWLIST, so
    adding one checker meant editing three lists. The registry is now the
    single source; this consumer derives from it with a tiny line scanner
    (no PyYAML dependency, no cross-layer import). The elegance guard G4
    enforces that every on-disk module is registered, so the registry cannot
    silently drift from reality.
    """
    files: set[str] = set()
    current: str | None = None
    for raw in registry_path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0]
        match = re.match(r"\s*-\s*module:\s*(\S+)\s*$", line)
        if match:
            current = match.group(1)
            continue
        if current and re.match(r"\s*layer:\s*checkers\s*$", line):
            files.add(current)
            current = None
    return frozenset(files)


FINAL_CHECKER_FILES = _registry_checker_files(_MODULE_REGISTRY)

# ELEGANT-REFACTOR P-guard registries (engine blueprint 0531 §3/§4). Append-only
# governance projection YAML pinned like the axis projection files; they live
# directly under support/checkers (not under profiles/). Support record only.
CROSSING_ELEGANCE_REGISTRY_FILES = {
    "support/checkers/crossing_registry.yaml",
    "support/checkers/module_registry.yaml",
    # PIN-ESTATE RATCHET ledger (TREASURE PORT 1 0611): dated human-disposition
    # baseline for the history-doc pin estate, consumed by
    # check_pin_estate_integrity.py. Same governance shape as the registries:
    # append-only support record directly under support/checkers.
    "support/checkers/pin_estate_baseline.yaml",
    # E2 / S0 AXIS FIELD-SET SINGLE-SOURCE REGISTRY: the mirror-guard +
    # scatter-guard source listing each axis field-set that is single-source on the
    # current tree, consumed by check_axis_field_set_single_source.py. Same
    # governance shape as the registries: append-only support record directly under
    # support/checkers.
    "support/checkers/field_set_registry.yaml",
    # E2 / S10 JUDGMENT-GUARD REGISTRY: the judgment-home map listing each
    # relocated judgment family + its owning axis module + declared consumer set,
    # consumed by check_support_no_axis_judgment.py. Same governance shape as the
    # registries: append-only support record directly under support/checkers.
    "support/checkers/judgment_home.yaml",
}

ROOT_FILES = {
    ".gitignore",
    "README.md",
    "AGENTS.md",
    # Ratified single-source law (0702) -- lives at root so release_export
    # (which excludes project/) ships it to customers.
    "BRICK-CONSTITUTION.md",
    "pyproject.toml",
    "uv.lock",
}

PACKAGE_MARKERS = {
    "support/import_identity/brick_protocol/__init__.py",
    "brick/__init__.py",
    "agent/__init__.py",
    "link/__init__.py",
    "support/__init__.py",
    "support/checkers/__init__.py",
    "support/checkers/lib/__init__.py",
    "support/connection/__init__.py",
    "support/operator/__init__.py",
    "support/recording/__init__.py",
}

PHASE4_CORE_TARGETS = {
    "brick/work.py",
    "brick/work.yaml",
    "agent/return_fact.py",
    "agent/return_fact.yaml",
    "link/movement.py",
    "link/movement.yaml",
}

PHASE4_EXPANSION_TARGETS = {
    "agent/receipt.py",
    "agent/receipt.yaml",
    "agent/performance.py",
    "agent/performance.yaml",
    "brick/building.py",
    "brick/building.yaml",
    "brick/comparison.py",
    "brick/comparison.yaml",
    "link/gate.py",
    "link/gate.yaml",
    "link/transition.py",
    "link/transition.yaml",
}

PHASE4_TARGETS = PHASE4_CORE_TARGETS | PHASE4_EXPANSION_TARGETS

LTC0_LINK_TRANSFER_CARRY_TARGETS = {
    "link/transfer.py",
    "link/transfer.yaml",
    "link/carry.py",
    "link/carry.yaml",
}

# E2 / S3 (mirror M11): link/spec.py — the START of the Link single-source plan-
# grammar API. Owns the gate-concept translation table + translate_gate_concept
# (moved from support/operator/composition.py); later E2 steps fold the Link
# envelope schemas + LINK_ROW_ALLOWED_KEYS here. A code-only axis module (no
# paired projection YAML yet); admitted as a Link axis surface.
LINK_SPEC0_TARGETS = {
    "link/spec.py",
}

# E2 / S6 (mirror M5+M6+M9): agent/spec.py — the Agent single-source CASTING API.
# Owns the CastingField descriptor + CASTING_FIELDS field-set (moved from
# support/operator/primitives.py), its selected_* projection, and the casting
# transport helpers. A code-only axis module (no paired projection YAML yet);
# admitted as an Agent axis surface, the Agent-axis sibling of link/spec.py.
AGENT_SPEC0_TARGETS = {
    "agent/spec.py",
}

# E2 / S9 (mirror M + J5 + axis-leak fix): brick/spec.py — the Brick single-source
# DECLARABLE-contract API. Owns BRICK_ROW_ALLOWED_KEYS (moved from
# support/operator/primitives.py), the WriteScope value object (shape +
# clean/validate, MOVED from support/connection/agent_adapter.py — a Brick-axis
# value object that had been in a support file named for the AGENT axis), the
# default worktree write envelope (moved from support/operator/assembly.py), and
# the write-NEED value interpreter (J5, moved from
# support/operator/plan_validation.py). A code-only axis module (no paired
# projection YAML yet); admitted as a Brick axis surface, the Brick-axis sibling
# of link/spec.py + agent/spec.py.
BRICK_SPEC0_TARGETS = {
    "brick/spec.py",
}

SIMPLE_RUN0_RUN_TARGETS = {
    "support/operator/run.py",
    # E2/S11 GOD-MODULE SPLIT: the chat-session step subsystem lifted verbatim
    # out of run.py (pure relocation; run.py re-imports the names it references).
    "support/operator/run_chat_session.py",
}

AGENT_ADAPTER0_TARGETS = {
    "support/connection/agent_adapter.py",
    # MODULE-SEP agent_adapter god-module split: agent_adapter.py (was 3391
    # lines) was decomposed into a thin facade + these 7 single-concern sibling
    # sub-modules (pure no-op relocation; the facade re-exports each name). All
    # connection-layer adapter mechanics only: no new fact class, no crossing
    # ownership moved.
    "support/connection/adapter_constants.py",
    "support/connection/adapter_validation.py",
    "support/connection/adapter_subprocess.py",
    "support/connection/adapter_model_casting.py",
    "support/connection/adapter_grant_policy.py",
    "support/connection/adapter_gemini_http.py",
    "support/connection/adapter_local_cli.py",
}

AGENT_RESOURCE_TOOLKIT0_TARGETS = {
    "support/connection/agent_resources.py",
}

COO_SYNC0_TARGETS = {
    "support/connection/coo_sync.py",
}

MCP_PROJECTION0_TARGETS = {
    "support/connection/mcp_projection.py",
}

BUILDING_DESIGN_TOOLKIT0_TARGETS = {
    "support/connection/building_design_toolkit.py",
}

# F8-SECRET-SCAN-SINGLE-SOURCE-0: the single source of raw-credential ("raw
# secret") regex patterns (RAW_SECRET_PATTERNS + contains_raw_secret_text),
# consumed by the four credential-rejection sites (agent_adapter.py,
# primitives.py, step_outputs.py, building_design_toolkit.py). A leaf connection
# module importing only re; owns no crossing, judges nothing.
SECRET_TEXT0_TARGETS = {
    "support/connection/secret_text.py",
}

# CONNECT-GENERATOR-0: the read-only MCP connect-config generator that emits a
# portable codex/claude config computed from the user's own checkout.
CONNECT_GENERATOR0_TARGETS = {
    "support/connection/connect.py",
}

BUILDING_OPERATION_SURFACE0_TARGETS = {
    "support/operator/building_operation.py",
}

# ONBOARDING-WIZARD-0: the friendly, never-raising onboarding flow that ties the
# existing preflight + connect + a bundled adapter:local example Building into
# one guided, plain-Korean beginner experience. Support operator mechanics only:
# reuses existing functions, owns no crossing, judges nothing.
ONBOARD_WIZARD0_TARGETS = {
    "support/operator/onboard.py",
}

# PROVIDER-REGISTRY-LADDER-0: per-user provider registry persistence plus the
# support adapter-resolution ladder read seam. Runtime code may read the live
# registry; checker coverage must use injected/temp fixtures only.
PROVIDER_REGISTRY_LADDER0_TARGETS = {
    "support/operator/provider_registry.py",
}

# SINK-REGISTRY-0: per-user report sink registry persistence plus mocked/live
# reachability observation cache. Runtime code may read the live registry;
# checker coverage must use injected/temp fixtures only.
SINK_REGISTRY0_TARGETS = {
    "support/operator/sink_registry.py",
}

# BRICK-CLI-ENTRYPOINT-0: the customer-facing `brick` console-script support
# wrapper. It bootstraps repo/import-identity paths, then delegates to existing
# doctor/build/verify/status seams. Support operator mechanics only: owns no
# crossing, judges nothing, chooses no Movement.
BRICK_CLI_ENTRYPOINT0_TARGETS = {
    "support/operator/cli.py",
    "support/operator/first_use.py",
}

# PROJECT-0 S1-A: the project declaration record loader (reads + validates
# project/<id>/project.json against the closed 9-key charter-shadow schema).
# Support operator mechanics only: records facts, owns no crossing, judges
# nothing. Pinned by the project_declaration kernel check (core profile).
PROJECT_DECLARATION0_TARGETS = {
    "support/operator/project_declaration.py",
}

# PROJECT-0 S2-A: the project creation verb (charter-first 기계 박제). Writes
# project/<id>/README.md (charter) FIRST, then project.json (the shadow
# declaration), then the vessel skeleton dirs, and fail-closed round-trips
# through the S1 loader — a rejected declaration removes the vessel. Support
# operator mechanics only: records direction facts, owns no crossing, judges
# nothing. Pinned by the project_declaration kernel check (core profile).
PROJECT_CREATION0_TARGETS = {
    "support/operator/project_creation.py",
}

# PROJECT-0 S4-C: the per-vessel PROGRESS.md machine projection (TRUTH layer
# only). Renders + writes project/<id>/PROGRESS.md (the admitted closed
# root-declaration file set already reserves that filename) from already-
# written Building evidence — facts only, no judgment vocabulary, no wallclock
# in the body (idempotent over unchanged evidence). Optional output: the
# project_declaration kernel check never requires it. Owns no crossing,
# judges nothing.
PROJECT_PROGRESS0_TARGETS = {
    "support/operator/progress_projection.py",
}

# WORKFLOW-IMPORT-0 (IMPORTER, 0612): the post-hoc workflow-result recording
# verbs. Workflow-internal agents pass through a harness back door the
# recording hooks cannot observe (B4 measurement), so the operator opens a
# recording building first, runs the workflow, then import_workflow_result
# stamps the RESULT as evidence through the SAME repaired native close seam
# (envelope-tolerant extraction; closed return-record key set unchanged).
# HONESTY: one recorded performer act + an explicit not-observable note; no
# per-internal-agent rows fabricated. Owns no crossing, judges nothing.
WORKFLOW_IMPORT0_TARGETS = {
    "support/operator/workflow_import.py",
}

# ONBOARDING-INSTALL-SCRIPT-0: the one-line (curl | sh) installer. A non-.py
# support onboarding artifact: a portable POSIX sh script that gets a teammate
# from a fresh machine to a ready Brick checkout, then points at the onboard
# wizard. Structure/safety is policed by the install_script_lint kernel check
# (set -eu, main()+'main "$@"' last line, HTTPS-only, no /Users/ literal, no
# inline secret, references the onboard entry). Owns no crossing, judges nothing.
ONBOARD_INSTALL_SCRIPT0_TARGETS = {
    "support/onboarding/install.sh",
}

# RELEASE-EXPORT-0: the operator-run clean public release export verb plus the
# local release gate that dry-runs it after compileall + check_profile.py --all.
# These are inert onboarding support artifacts: they may prepare local evidence
# and print follow-up commands, but do not change repository settings, publish,
# choose Movement, or judge success/quality.
ONBOARD_RELEASE_EXPORT0_TARGETS = {
    "support/onboarding/release_export.sh",
    "support/onboarding/release_gate.sh",
}

# ONBOARDING-RECORDING-HOOKS (0610): TRACKED machine-neutral templates for the
# per-LLM auto-recording hooks. These are the SOURCE the onboard wizard's
# opt-in recording step (support/operator/onboard.py) copies into a checkout's
# .claude/hooks/ + .codex/hooks/ (machine config, gitignored). Without these
# tracked templates the AGENTS.md auto-record promise is unrealizable from a
# fresh clone. They carry NO machine default (BRICK_REPO_ROOT is required),
# own no crossing, judge nothing, and never block a dispatch (always exit 0).
ONBOARD_RECORDING_HOOK_TEMPLATE_TARGETS = {
    "support/onboarding/claude-hooks/open-recording.py",
    "support/onboarding/claude-hooks/close-recording.py",
    "support/onboarding/codex-hooks/codex-open-recording.py",
    "support/onboarding/codex-hooks/codex-close-recording.py",
}

BAR_V2_OPERATOR_TARGETS = {
    "support/operator/auto_repair_replay.py",
    "support/operator/child_building_generation.py",
    "support/operator/contracts.py",
    # BOUNDED-AGENT-PROPOSED-ROUTING-LOOP-0 admits the dynamic graph walker as a
    # new support/operator module (the only new module the amendment admits).
    "support/operator/dynamic_walker.py",
    "support/operator/evidence_assembly.py",
    "support/operator/plan_graph.py",
    "support/operator/plan_validation.py",
    "support/operator/portfolio_projection.py",
    "support/operator/primitives.py",
    "support/operator/proof_observation.py",
    "support/operator/route_materialization.py",
    "support/operator/write_observation.py",
    # BUILDING-OPERATOR-DRIVER-0 admits the bounded declared portfolio driver.
    "support/operator/driver.py",
}

REPORTER_NOTIFICATION_PROJECTION0_TARGETS = {
    "support/operator/label_map.json",
    "support/operator/reporter.py",
    "support/operator/report_sinks.py",
}

# REPORT-ENV-AUTOLOAD-0 (#56): the engine-entry auto-loader that injects the
# narrow allowlist of slack/dashboard/provider credential keys from
# ~/.brick/report.env (+ ~/.brick/credentials.env) into os.environ at the run.py
# building seam, so the environment-gated report sinks can deliver regardless of
# how the operator launched. Support operator mechanics only: allowlist-only,
# 0600-gated, env-precedence, no value echo; owns no crossing, stores no secret
# at rest, chooses no Movement, judges nothing.
REPORT_ENV_AUTOLOAD0_TARGETS = {
    "support/operator/runtime_env.py",
}

# DASHBOARD-EVENT-DELTA-0 + DASHBOARD-SURFACE-0 (M-union 0610): the read-side
# dashboard projection module (reshapes the ledger packet into a dashboard-readable
# snapshot, and one building into the same per-building row/detail shape as an
# EVENT DELTA). The dashboard SINK lives in the already-admitted report_sinks.py
# (report-sink:dashboard, delta + connect seed). The dashboard RUNTIME (React +
# SSE server) is the vendored support/dashboard surface admitted ONLY via
# is_dashboard_surface_path (scoped: that subtree, web-source extensions, root
# config files, and the deployment doc; node_modules / dist / generated data stay
# residue-filtered).
DASHBOARD_EXPORT0_TARGETS = {
    "support/operator/dashboard_export.py",
}
DASHBOARD_SURFACE_ROOT = "support/dashboard"
DASHBOARD_SURFACE_ROOT_FILES = {"Dockerfile", ".dockerignore", ".gcloudignore", ".gitignore"}
DASHBOARD_SURFACE_FILE_EXTS = (".jsx", ".js", ".mjs", ".css", ".html", ".json", ".md")

# ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): the
# dynamic graph walker god-module's separable concerns were lifted into
# single-concern operator collaborators behind the thin facade in
# support/operator/dynamic_walker.py. Each is a registered module_registry.yaml
# row (G4 bidirectional tie). Support operator mechanics only: NESTED walker
# evidence, no BAL fact class, no fourth axis.
ELEGANT_REFACTOR_WALKER_TARGETS = {
    "support/operator/walker_common.py",
    "support/operator/walker_step_fixture.py",
    "support/operator/walker_reroute_budget.py",
    "support/operator/walker_fan_in.py",
    "support/operator/walker_transition_concern.py",
    "support/operator/gate_sequence.py",
    "support/operator/walker_hold.py",
    "support/operator/walker_frontier.py",
    "support/operator/walker_frontier_driver.py",
    "support/operator/walker_carry.py",
    "support/operator/walker_runtime_mail.py",
    "support/operator/walker_resume_seed.py",
    "support/operator/walker_report_events.py",
    "support/operator/walker_kernel.py",
    "support/operator/walker_resume.py",
}

# ELEGANT-REFACTOR P3d (engine blueprint 0531 §5 Opt 2 / detail-design §D-1): the
# largest god-module (building_operation.py) was decomposed into single-concern
# operator collaborators behind the thin facade in
# support/operator/building_operation.py. Each is a registered
# module_registry.yaml row (G4 bidirectional tie). Support operator mechanics
# only: read projections / records, no new fact class, no fourth axis.
ELEGANT_REFACTOR_BUILDING_OPERATION_TARGETS = {
    "support/operator/building_operation_common.py",
    "support/operator/checker_runner.py",
    "support/operator/evidence_status.py",
    "support/operator/ledger_projection.py",
    "support/operator/frontier_observation.py",
    "support/operator/coo_operating_chain.py",
    "support/operator/plan_rendering.py",
    *PROVIDER_REGISTRY_LADDER0_TARGETS,
    *SINK_REGISTRY0_TARGETS,
    # MODULE-SEP composition god-module split: composition.py (was 4489 lines)
    # was decomposed into these single-concern sibling collaborators (pure
    # relocation; callers import the real homes directly — the facade is gone).
    # Each is a registered module_registry.yaml row (G4 bidirectional tie).
    # Support operator mechanics only: composition lowering, no new fact class,
    # no fourth axis.
    "support/operator/composition_problem.py",
    "support/operator/composition_common.py",
    "support/operator/composition_kinds.py",
    "support/operator/composition_route_policy.py",
    "support/operator/composition_gate_translation.py",
    "support/operator/composition_graph_emit.py",
    "support/operator/composition_graph_validate.py",
    "support/operator/composition_compose.py",
    "support/operator/composition_intent.py",
    "support/operator/orchestration_packet.py",
    "support/operator/native_dispatch.py",
    # W1: thin worktree-sandbox lifecycle helper for customer-facing dispatch
    # (create->run->commit-on-complete->dispose around run_building_intake).
    "support/operator/worktree_sandbox.py",
}

# HEART front door: assembly.py -- the refined 3-axis builder API
# (brick/agent/chain/fan_out/fan_in/edge/converge/reroute/hold/assemble). The
# main agent expresses STRUCTURE only; assemble() lowers verbatim to the
# compose_building (nodes, edges, groups) args. Imports composition.py only;
# authors no Movement or route.
HEART_FRONTDOOR0_TARGETS = {
    "support/operator/assembly.py",
}

# BUILDING-EASE-0 (0623): the make-a-brick skill's scaffold helper. Pure support
# operator mechanics: it WRITES a new brick kind's two template files
# (bricks/<kind>/brick.md + return.yaml) with the body↔return invariant pre-
# satisfied and REGISTERS the kind's primary return template in the catalog active
# list so it is not an orphan. A new kind is DATA (no brick/spec edit). Owns no
# crossing, casts no agent, judges nothing.
BRICK_KIND_SCAFFOLD0_TARGETS = {
    "support/operator/brick_kind_scaffold.py",
}

TASK_ORDER_PREFLIGHT0_TARGETS = {
    "support/operator/task_order_preflight.py",
}

PLAN_EXPANSION0_TARGETS = {
    "support/operator/plan_expansion.py",
}

PLAN_EXPANSION0_FIXTURES = {
    "support/checkers/fixtures/plan_expansion/valid_merge.json",
    "support/checkers/fixtures/plan_expansion/cycle.json",
    "support/checkers/fixtures/plan_expansion/missing_fan_in_member.json",
    "support/checkers/fixtures/plan_expansion/upstream_target.json",
    "support/checkers/fixtures/plan_expansion/duplicate_step_ref.json",
}

PRH_B_RECORDER_TARGETS = {
    "support/recording/__init__.py",
    "support/recording/records.py",
    "support/recording/building_map.py",
    "support/recording/contracts.py",
    "support/recording/capture.py",
    # U5.5 SLICE-1A: the Evidence Spine shared pure functions module (event_type
    # set + canonical_json/content_hash/render_event_md). A support recording
    # shape module only: no BAL fact class, no fourth axis, no disk writer yet.
    "support/recording/spine.py",
    # U5.5 SLICE-2 BUILD-2: the Evidence Spine building-scope DECLARATION
    # projector — reads work/preset-expansion.json + work/link-launch-policy.json
    # and appends the PresetExpansion + LinkLaunchPolicy events via the slice-1B
    # writer (spine.append_spine_events). A support recording shape module only:
    # imports spine (recording), imports NO checker, owns no crossing, judges
    # nothing (mechanical refs/enums/counts; the two forbidden launch-row keys
    # renamed + kept nested).
    "support/recording/spine_projection.py",
    "support/recording/raw_claim_trace.py",
    "support/recording/step_outputs.py",
    # TrackA-A1 (INSTRUMENT FIRST 0619): the per-step adapter token-usage METER
    # journal writer (raw/adapter-usage.jsonl). A support recording shape module
    # only: NESTED graph-ready JSONL, no BAL fact class, no fourth axis. Records
    # the codex turn.completed token counters as a Brick-axis SUPPORT FACT with no
    # quality/fault label and no cap (measurement only).
    "support/recording/adapter_usage_meter.py",
    # P-evidence-arch / ζ6 contract-derived dynamic-walker evidence emitters
    # (reroute-adoption record, HOLD record, structured field observation). A
    # support recording shape module only: NESTED evidence, no BAL fact class.
    "support/recording/walker_evidence.py",
    # P-evidence-arch increment 2 / ζ6 contract-derived accumulated-Building
    # operator evidence emitters (lifecycle capture events, building-map per-step
    # rows, frontier observation). A support recording shape module only: NESTED
    # evidence, no BAL fact class, no fourth axis.
    "support/recording/operator_evidence.py",
    # ELEGANT-REFACTOR P3b (engine blueprint 0531 §5 / detail-design §D-2 Opt B):
    # the evidence_assembly god-module's per-crossing-family emitters were lifted
    # here as single-concern recording collaborators behind the writer facade in
    # support/operator/evidence_assembly.py. Each is a registered
    # module_registry.yaml row (G4 bidirectional tie). Support recording shape
    # only: NESTED evidence, no BAL fact class, no fourth axis.
    "support/recording/claims_common.py",
    "support/recording/claims_brick.py",
    "support/recording/claims_agent.py",
    "support/recording/claims_link.py",
    "support/recording/claims_carry_budget.py",
    "support/recording/claims_assembly.py",
    "support/recording/declaration_packets.py",
    "support/recording/building_map_emit.py",
    "support/recording/lifecycle_emit.py",
    "support/recording/adapter_error_frontier.py",
    # REDO (Smith 0623 struct-surgery): the per-step Agent support-observation
    # fact deriver. Support = move+record only -- the ADAPTER exposes raw (gemini
    # tool-call list, stripped verdict-key names, effective-write request inputs)
    # and the support WRITE OBSERVER exposes raw worktree observation; this module
    # RECORDS the named facts and calls brick.comparison for the written-vs-scope
    # classification. NESTED support evidence, no BAL fact class, no fourth axis,
    # no building-stop.
    "support/recording/agent_step_observation.py",
}

V03_DOGFOOD_ROOT = "project/brick-protocol/status/v03-dogfood"
V03_DOGFOOD_ROLE_DIRS = {"brick", "agent", "link", "output"}
# REPO-SPLIT seed 0611: the v03 dogfood pilot records moved to the history
# repo with project #1's status/v03-dogfood tree; product table is EMPTY (the
# predicate mechanism ships, the legacy data rows do not).
V03_DOGFOOD_ALLOWED_RECORDS: set[tuple[str, str]] = set()

BES_DOGFOOD_ROOT = "project/brick-protocol/status/building-evidence-dogfood"
# REPO-SPLIT seed 0611: the building-evidence-dogfood pilot tree moved to the
# history repo; product tables are EMPTY (mechanism ships, legacy rows do not).
BES_RUN_RECORDS: set[str] = set()
BES_BRICK_DIRS: set[str] = set()
BES_CLAIM_TRACE_DIRS: set[str] = set()
BES_EVENTS_RECORDS: set[str] = set()
BES_RAW_RECORDS: set[str] = set()
BES_CLAIM_TRACE_RECORDS: set[tuple[str, str]] = set()
BES_EVALUATION_RECORDS: set[str] = set()


PRH_B_BUILDING_EVIDENCE_ROOT = "project/brick-protocol/building-evidence"
# REPO-SPLIT seed 0611: project #1's building-evidence exact-file tree moved
# to the history repo; product tables are EMPTY (mechanism ships, rows do not).
PRH_B_RUN_RECORDS: set[str] = set()
PRH_B_BRICK_DIRS: set[str] = set()
PRH_B_CLAIM_TRACE_DIRS: set[str] = set()
PRH_B_EVENTS_RECORDS: set[str] = set()
PRH_B_RAW_RECORDS: set[str] = set()
PRH_B_CLAIM_TRACE_RECORDS: set[tuple[str, str]] = set()

BUILDING_LIFECYCLE_DIRS = {
    ("work",),
    ("capture",),
    ("raw",),
    ("evidence",),
    ("evidence", "claim_trace"),
    ("evidence", "claim_trace", "brick"),
    ("evidence", "claim_trace", "agent"),
    ("evidence", "claim_trace", "link"),
    ("evidence", "evaluation_improvement"),
}
BUILDING_LIFECYCLE_RECORDS = {
    ("work", "building-work.json"),
    ("work", "building-map.json"),
    ("work", "task.md"),
    ("work", "building-intake.json"),
    ("work", "preset-expansion.json"),
    ("work", "declared-building-plan.json"),
    ("work", "link-launch-policy.json"),
    ("capture", "events.jsonl"),
    ("raw", "raw-manifest.json"),
    ("raw", "user-turns.jsonl"),
    ("raw", "brick-work-issued.jsonl"),
    ("raw", "handoffs.jsonl"),
    ("raw", "agent-received.jsonl"),
    ("raw", "agent-actions.jsonl"),
    ("raw", "agent-returns.jsonl"),
    ("raw", "gate-checks.jsonl"),
    ("raw", "review-raw.jsonl"),
    ("evidence", "evidence-manifest.json"),
    ("evidence", "claim_trace", "brick", "work_contract.json"),
    ("evidence", "claim_trace", "agent", "returned_claims.json"),
    ("evidence", "claim_trace", "link", "transfer_trace.json"),
    ("evidence", "claim_trace", "link", "carry_trace.json"),
    ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
    ("evidence", "claim_trace", "link", "movement_trace.json"),
    # E1 (U5.5 slice-3): the live gate-sequence receipts + final policy action.
    ("evidence", "claim_trace", "link", "gate_receipt_trace.json"),
    ("evidence", "claim_trace", "link", "policy_action_trace.json"),
    ("evidence", "evaluation_improvement", "process_integrity_check.json"),
    ("evidence", "evaluation_improvement", "operator_quality_evaluation.json"),
    ("evidence", "evaluation_improvement", "integrity_quality_crossing.json"),
    ("evidence", "evaluation_improvement", "curator_axis_attribution.json"),
    ("evidence", "evaluation_improvement", "candidate_variable_change.json"),
    ("evidence", "evaluation_improvement", "change_safety_assessment.json"),
    ("evidence", "support-record.md"),
    ("evidence", "review-disposition.md"),
}
COMPACT_HISTORICAL_CAP_BOOT_BUILDINGS = {
    "cap-boot-4-conversation-dogfood-0521",
    "cap-boot-5-subagent-lane-dogfood-0521",
}
FULL_HISTORICAL_CAP_BOOT_BUILDINGS = {
    "cap-boot-1-capture-event-contract-0521",
    "cap-boot-2-building-lifecycle-path-admission-0521",
    "cap-boot-3-lifecycle-checker-and-capture-writer-0521",
    "cap-boot-6-recording-honesty-gate-dogfood-0521",
    "cap-boot-7-evidence-axis-improvement-analysis-0521",
    "cap-boot-8-three-axis-operation-guard-admission-0521",
}
HISTORICAL_BUILDING_LIFECYCLE_DIRS = {("work",), ("capture",), ("raw",), ("evidence",)}
HISTORICAL_BUILDING_LIFECYCLE_RECORDS = {
    ("work", "building-work.json"),
    ("work", "building-map.json"),
    ("work", "spec.md"),
    ("capture", "events.jsonl"),
    ("raw", "raw-manifest.json"),
    ("evidence", "evidence-manifest.json"),
    ("evidence", "support-record.md"),
    ("evidence", "review-disposition.md"),
}
MINIMAL_BUILDING_LIFECYCLE_DIRS = {
    ("work",),
    ("capture",),
    ("raw",),
    ("evidence",),
    ("evidence", "claim_trace"),
    ("evidence", "claim_trace", "brick"),
    ("evidence", "claim_trace", "agent"),
    ("evidence", "claim_trace", "link"),
    ("evidence", "evaluation_improvement"),
    # U5.5 SLICE-1A: the Evidence Spine projection dirs. ALLOW-only here (this
    # checker enforces NO presence; the lifecycle-shape checker is the sole
    # presence authority, generation-gated to u5_5_live buildings).
    ("evidence", "spine"),
    ("evidence", "spine", "events"),
}
MINIMAL_BUILDING_LIFECYCLE_RECORDS = {
    # run_building_intake (support/operator/driver.py) writes its materialized
    # INPUT plan at the building ROOT (declared-building-plan.json) before the
    # walk; the run's own work/declared-building-plan.json declaration packet
    # below is a different file. Both are admitted so the documented
    # first-day intake flow never turns this gate RED.
    ("declared-building-plan.json",),
    ("proposed-building-graph.json",),
    ("work", "building-work.json"),
    ("work", "building-map.json"),
    ("work", "task.md"),
    ("work", "building-intake.json"),
    ("work", "preset-expansion.json"),
    ("work", "declared-building-plan.json"),
    ("work", "link-launch-policy.json"),
    ("work", "proposed-building-graph.json"),
    ("capture", "events.jsonl"),
    ("raw", "raw-manifest.json"),
    ("evidence", "evidence-manifest.json"),
    ("evidence", "claim_trace", "brick", "work_contract.json"),
    ("evidence", "claim_trace", "agent", "returned_claims.json"),
    ("evidence", "claim_trace", "link", "transfer_trace.json"),
    ("evidence", "claim_trace", "link", "carry_trace.json"),
    ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
    ("evidence", "claim_trace", "link", "movement_trace.json"),
    # E1 (U5.5 slice-3): the live gate-sequence receipts + final policy action.
    ("evidence", "claim_trace", "link", "gate_receipt_trace.json"),
    ("evidence", "claim_trace", "link", "policy_action_trace.json"),
    ("evidence", "support-record.md"),
    ("evidence", "review-disposition.md"),
    ("evidence", "evaluation_improvement", "process_integrity_check.json"),
    ("evidence", "evaluation_improvement", "operator_quality_evaluation.json"),
    ("evidence", "evaluation_improvement", "integrity_quality_crossing.json"),
    ("evidence", "evaluation_improvement", "curator_axis_attribution.json"),
    ("evidence", "evaluation_improvement", "candidate_variable_change.json"),
    ("evidence", "evaluation_improvement", "change_safety_assessment.json"),
}
BUILDING_LIFECYCLE_FORBIDDEN_SEGMENTS = {
    "storage",
    "wiki",
    "runtime",
    "provider",
    "scheduler",
    "dashboard",
}

# ARCHIVE MUSEUM class PRUNED (CLEAN-YARD v3, Smith 0611): the entire archive/
# museum left for the frozen history repo (the prior private workspace
# preserves every original). The product repo admits NO archive/ root; a
# resurrected archive/ path REJECTS loudly via the default-deny below.

# USER-WORKSPACE class REMOVED (0611, Smith ruling TASK-BY-TEXT): humans SPEAK
# tasks (run_building_intake task_statement); the machine records them as
# building evidence (work/task.md). There is no in-repo user draft estate any
# more -- a stray file at the repo root or under a former workspace/ path
# REJECTS loudly here (fail-closed, no silent residue).

# work_contract_template.md moved to the archive museum (#24, 0610); the
# support/docs/templates admission class is retired with it (no live template
# files remain under support/docs/templates).
SUPPORT_DOC_TEMPLATE_FILES: set[str] = set()

TEMPLATE0_BRICK_TEMPLATE_DIRS = {
    "brick/templates",
    "brick/templates/closure",
    "brick/templates/design",
    "brick/templates/bricks",
    "brick/templates/do",
    "brick/templates/presets",
    "brick/templates/review",
    "brick/templates/shapes",
    "brick/templates/skills",
    "brick/templates/tasks",
}
TEMPLATE0_BRICK_KINDS = {
    "axis-attack-qa",
    "closure",
    "code-attack-qa",
    "design",
    "development",
    "evidence-integrity",
    "inspect",
    "plan",
    "review",
    "work",
}

BRICK_TASK_DIRS: set[str] = set()

BAR_V2_BRICK_DATA_DIRS: set[str] = set()

BRICK_BUILDING_PLAN_DIRS = {
    "brick/building_plans",
}

BAR_V2_LINK_DATA_DIRS = {
    "link/route_policies",
}

AGENT_RESOURCE0_DIRS = {
    "agent/objects",
    "agent/prompts",
    "agent/skills",
    "agent/hooks",
    "agent/tool_policies",
    "agent/disciplines",
}

# PROJECT-0 S1-D: the status / portfolio-projection / root-declaration path
# classes are matched PER PROJECT VESSEL (project/<id>/...) by the is_project_*
# predicates below — the former PROJECT_STATUS_DIRS literal set collapsed into
# is_project_status_path(is_dir=True). Everything else stays closed; the
# project_declaration kernel check rejects any vessel without charter+declaration.
# CLEAN-YARD v3 (Smith 0611): the two standing dogfood status exports left
# for the frozen museum; their shapes are EXECUTED projections now
# (intake_evidence_projection_case generates the ledger packet fresh). The
# admitted set is EMPTY -- a standing status-root export must be re-admitted
# deliberately, never inherited.
PROJECT_STATUS_ROOT_RECORDS: set[str] = set()
# CLEAN-YARD v3 (Smith 0611): the 3 standing dogfood inbox packets left for
# the frozen museum; their shapes are EXECUTED by the reporter kernel check
# over packets the REAL sinks write into a temp inbox each run. The shipped
# inbox is the empty skeleton.
PROJECT_STATUS_INBOX_RECORDS = {
    ".gitkeep",
}
PROJECT_PORTFOLIO_PROJECTION_SEGMENT = "_portfolio-projections"
PROJECT_STATUS_SEGMENT = "status"
PROJECT_STATUS_GRAPH_PACKET_DIR = "GOAL"
# PROJECT-0: the closed per-vessel root declaration file set (charter +
# machine declaration + the S4 machine-generated progress projection).
PROJECT_ROOT_DECLARATION_FILES = {
    "project.json",
    "README.md",
    "PROGRESS.md",
}

ALLOWED_DIRS = {
    ".github",
    ".github/workflows",
    "support",
    "support/docs",
    "support/docs/spec",
    "support/docs/spec/full-spec",
    "support/docs/spec/physical-blueprint",
    "support/docs/reviews",
    "support/docs/references",
    "support/docs/projection",
    # support/docs/templates retired (#24, 0610): its only file
    # (work_contract_template.md) moved to archive/docs-templates/.
    "support/checkers/fixtures",
    "support/checkers/fixtures/plan_expansion",
    "support/connection",
    "support/operator",
    "support/onboarding",
    "support/onboarding/claude-hooks",
    "support/onboarding/codex-hooks",
    "support/import_identity",
    "support/import_identity/brick_protocol",
    "project",
    "project/brick-protocol",
    # REPO-SPLIT seed 0611: project/brick-protocol/building-evidence row moved
    # to the history repo with the tree (no building-evidence/ in the product).
    "project/brick-protocol/buildings",
    "brick_protocol",
    "brick",
    *BRICK_TASK_DIRS,
    *TEMPLATE0_BRICK_TEMPLATE_DIRS,
    *BRICK_BUILDING_PLAN_DIRS,
    *BAR_V2_BRICK_DATA_DIRS,
    "agent",
    *AGENT_RESOURCE0_DIRS,
    "link",
    *BAR_V2_LINK_DATA_DIRS,
    "support/recording",
    "support/checkers",
    "support/checkers/lib",
    "support/checkers/profiles",
}


def slug_part(value: str) -> bool:
    return bool(value) and value.replace("-", "").replace("_", "").isalnum()


def task_statement_node_part(value: str) -> bool:
    prefix = "task-statement-"
    suffix = "-node"
    if not value.startswith(prefix) or not value.endswith(suffix):
        return False
    stem = value[len(prefix) : -len(suffix)]
    return slug_part(stem)


# PROJECT-0 S5-FIX: project VESSEL ids are stricter than generic slug parts —
# lowercase ascii [-_a-z0-9] with a [a-z0-9] first char, mirroring THE single
# slug law in support/recording/capture.is_project_id_slug (this foundational
# path gate carries no cross-layer import by design; the
# check_project_declaration FIRE probes hold the two in lockstep).
_VESSEL_ID_RE = re.compile(r"[a-z0-9][-_a-z0-9]*")


def vessel_id_part(value: str) -> bool:
    return bool(_VESSEL_ID_RE.fullmatch(value))


def is_agent_resource0_path(path: str, *, is_dir: bool) -> bool:
    parts = path.split("/")
    if len(parts) < 2 or parts[0] != "agent":
        return False
    family = parts[1]
    if family == "objects":
        return (
            (len(parts) == 2 and is_dir)
            or (
                len(parts) == 3
                and not is_dir
                and parts[2].endswith(".yaml")
                and slug_part(parts[2].removesuffix(".yaml"))
            )
        )
    if family == "prompts":
        return (
            (len(parts) == 2 and is_dir)
            or (
                len(parts) == 3
                and not is_dir
                and parts[2].endswith(".md")
                and slug_part(parts[2].removesuffix(".md"))
            )
        )
    if family == "skills":
        if len(parts) == 2:
            return is_dir
        if len(parts) == 3:
            return is_dir and slug_part(parts[2])
        return len(parts) == 4 and not is_dir and parts[3] == "SKILL.md" and slug_part(parts[2])
    if family == "hooks":
        return (
            (len(parts) == 2 and is_dir)
            or (len(parts) == 3 and not is_dir and parts[2] in {"registry.yaml", "bindings.yaml"})
        )
    if family == "tool_policies":
        return (
            (len(parts) == 2 and is_dir)
            or (
                len(parts) == 3
                and not is_dir
                and parts[2].endswith(".yaml")
                and slug_part(parts[2].removesuffix(".yaml"))
            )
        )
    if family == "disciplines":
        return (
            (len(parts) == 2 and is_dir)
            or (
                len(parts) == 3
                and not is_dir
                and parts[2].endswith(".md")
                and slug_part(parts[2].removesuffix(".md"))
            )
        )
    return False


def is_support_connector_resource0_path(path: str, *, is_dir: bool) -> bool:
    return False


def is_template0_brick_template_path(path: str, is_dir: bool) -> bool:
    parts = path.split("/")
    if is_dir:
        if parts == ["brick", "templates", "blocks"]:
            # PRESET-RESTRUCTURE-S1 (0705) checker companion: admit exactly the
            # blocks/ corpus directory under the existing Brick template family.
            # The file branch below keeps the contents closed to slugged .md docs.
            return True
        if path in TEMPLATE0_BRICK_TEMPLATE_DIRS:
            return True
        if (
            len(parts) == 4
            and parts[:3] == ["brick", "templates", "bricks"]
            and parts[3] in TEMPLATE0_BRICK_KINDS
        ):
            return True
        # BUILDING-EASE-0 (0623): a shipped operator skill is a slug DIR under
        # skills/ (nested folder model, like bricks/<kind>/). Admit the slug dir;
        # its SKILL.md file is admitted by the file branch below.
        return (
            len(parts) == 4
            and parts[:3] == ["brick", "templates", "skills"]
            and bool(slug_part(parts[3]))
        )
    parts = path.split("/")
    if len(parts) == 3 and parts[:2] == ["brick", "templates"]:
        # T-FLATTEN (0611): templates-root CLOSED set — the building-level
        # human<->COO design-contract table (building-level by design, so
        # deliberately NOT a brick sheet under bricks/) + the stranger's-map
        # README, Smith-declared reroute defaults, and the declaration enforcement
        # ledger. Exactly these filenames; no root file class opens up.
        return parts[2] in {
            "building-design-contract.yaml",
            "enforcement-ledger.yaml",
            "README.md",
            "reroute-defaults.yaml",
        }
    if parts[:3] == ["brick", "templates", "tasks"]:
        return (
            len(parts) == 4
            and not is_dir
            and parts[3].endswith(".md")
            and slug_part(parts[3].removesuffix(".md"))
        )
    if parts[:3] == ["brick", "templates", "bricks"]:
        # Single-Brick folder model: each active Brick has exactly a slug dir with
        # brick.md (frontmatter + instruction) and return.yaml (primary returned
        # shape). Do not admit an arbitrary subtree under bricks/.
        if len(parts) == 4 and is_dir:
            return parts[3] in TEMPLATE0_BRICK_KINDS
        if len(parts) == 4 and not is_dir:
            # T-FLATTEN (0611): the ONE shared transition-concern complaint form
            # every brick carries as its second return ref lives at the bricks/
            # family root. CLOSED FORM: exactly this filename, nothing else —
            # a root file never enters kind discovery (dirs-only iteration).
            return parts[3] == "transition-concern-return.yaml"
        return (
            len(parts) == 5
            and not is_dir
            and parts[3] in TEMPLATE0_BRICK_KINDS
            and parts[4] in {"brick.md", "return.yaml"}
        )
    if parts[:3] == ["brick", "templates", "presets"]:
        # U3 re-home: a chain preset is a "Building route 설명서" authored as a
        # free-form .md (frontmatter = structure + `## Route` prose). Like tasks/
        # and bricks/, presets/ admits .md (not .yaml).
        return (
            len(parts) == 4
            and not is_dir
            and parts[3].endswith(".md")
            and slug_part(parts[3].removesuffix(".md"))
        )
    if parts[:3] == ["brick", "templates", "blocks"]:
        # PRESET-RESTRUCTURE-S1 (0705) checker companion: reusable stage blocks
        # are documentation corpus entries only, admitted as Brick template docs.
        # They may carry front matter and a DSL snippet for human/COO authoring
        # vocabulary, but no operator/CLI/materializer reads this directory.
        return (
            len(parts) == 4
            and not is_dir
            and parts[3].endswith(".md")
            and slug_part(parts[3].removesuffix(".md"))
        )
    if parts[:3] == ["brick", "templates", "skills"]:
        # BUILDING-EASE-0 (0623): shipped OPERATOR skills (sizing + launch +
        # the three make-a-* creation skills). Like bricks/, each skill is a slug
        # dir containing exactly SKILL.md (nested folder model, NOT the flat .md of
        # tasks/presets). The skills-root also admits exactly the APPLY-LIST.md
        # operator note (the live ~/.claude/skills copy/delete instructions) — a
        # closed root filename, never entering skill discovery.
        if len(parts) == 4 and is_dir:
            return bool(slug_part(parts[3]))
        if len(parts) == 4 and not is_dir:
            return parts[3] == "APPLY-LIST.md"
        return (
            len(parts) == 5
            and not is_dir
            and bool(slug_part(parts[3]))
            and parts[4] == "SKILL.md"
        )
    return (
        len(parts) == 4
        and parts[0] == "brick"
        and parts[1] == "templates"
        and parts[2] in {item.rsplit("/", 1)[-1] for item in TEMPLATE0_BRICK_TEMPLATE_DIRS if item != "brick/templates"}
        and parts[3].endswith((".json", ".yaml", ".yml"))
        and slug_part(parts[3].rsplit(".", 1)[0])
    )


def is_brick_task_path(path: str, *, is_dir: bool) -> bool:
    return False


def is_brick_building_plan_path(path: str, *, is_dir: bool) -> bool:
    parts = path.split("/")
    if parts[:2] != ["brick", "building_plans"]:
        return False
    if len(parts) == 2:
        return is_dir
    return (
        len(parts) == 3
        and not is_dir
        and parts[2].endswith((".yaml", ".yml", ".json"))
        and slug_part(parts[2].rsplit(".", 1)[0])
    )


def is_bar_v2_brick_data_path(path: str, *, is_dir: bool) -> bool:
    parts = path.split("/")
    if len(parts) < 2:
        return False
    root = "/".join(parts[:2])
    if root not in BAR_V2_BRICK_DATA_DIRS:
        return False
    if len(parts) == 2:
        return is_dir
    return (
        len(parts) == 3
        and not is_dir
        and parts[2].endswith((".yaml", ".yml", ".json"))
        and slug_part(parts[2].rsplit(".", 1)[0])
    )


def is_bar_v2_link_data_path(path: str, *, is_dir: bool) -> bool:
    parts = path.split("/")
    if len(parts) < 2:
        return False
    root = "/".join(parts[:2])
    if root not in BAR_V2_LINK_DATA_DIRS:
        return False
    if len(parts) == 2:
        return is_dir
    return (
        len(parts) == 3
        and not is_dir
        and parts[2].endswith((".yaml", ".yml"))
        and slug_part(parts[2].rsplit(".", 1)[0])
    )


def _project_family_tail(path: str, family_segment: str) -> list[str] | None:
    """Tail of ``project/<id>/<family_segment>/...`` for ANY slug project id.

    PROJECT-0 S1-D: the per-vessel sibling families (status /
    _portfolio-projections) are matched per project id instead of pinning
    project #1's literal. Returns None when the path is not in the family.
    """

    parts = path.split("/")
    if len(parts) < 3 or parts[0] != "project":
        return None
    if not vessel_id_part(parts[1]) or parts[2] != family_segment:
        return None
    return parts[3:]


def is_project_root_declaration_path(path: str, *, is_dir: bool) -> bool:
    """The project vessel root dir ``project/<id>/`` plus its own
    ``{project.json,README.md,PROGRESS.md}`` — charter + machine declaration +
    progress projection (closed 3-file set)."""

    parts = path.split("/")
    if is_dir:
        return len(parts) == 2 and parts[0] == "project" and vessel_id_part(parts[1])
    return (
        len(parts) == 3
        and parts[0] == "project"
        and vessel_id_part(parts[1])
        and parts[2] in PROJECT_ROOT_DECLARATION_FILES
    )


def is_project_status_path(path: str, *, is_dir: bool) -> bool:
    parts = _project_family_tail(path, PROJECT_STATUS_SEGMENT)
    if parts is None:
        return False
    if len(parts) == 0:
        return is_dir
    if parts[0] != "kernel":
        if parts[0] == "inbox":
            if len(parts) == 1:
                return is_dir
            return (
                len(parts) == 2
                and not is_dir
                and (
                    parts[1] in PROJECT_STATUS_INBOX_RECORDS
                    or (
                        parts[1].endswith(".json")
                        and slug_part(parts[1].rsplit(".", 1)[0])
                    )
                )
            )
        if len(parts) == 1 and not is_dir:
            return parts[0] in PROJECT_STATUS_ROOT_RECORDS
        return is_v03_dogfood_pilot_path(path, is_dir=is_dir) or is_bes_dogfood_pilot_path(
            path, is_dir=is_dir
        )
    if len(parts) == 1:
        return is_dir
    if len(parts) == 2 and parts[1] == "source-records":
        return is_dir
    if len(parts) == 3 and parts[1] == "source-records":
        return is_dir and parts[2] in {"full-spec", "physical-blueprint"}
    if is_dir:
        return len(parts) >= 2 and all(slug_part(part) for part in parts[1:])
    if (
        len(parts) == 3
        and parts[1] == PROJECT_STATUS_GRAPH_PACKET_DIR
        and parts[2].endswith(".json")
        and slug_part(parts[2].removesuffix(".json"))
    ):
        # Graph packets under project/<vessel>/status/kernel/GOAL are support
        # input packets, not admitted source/status truth. Keep the JSON opening
        # narrow so arbitrary status JSON remains closed.
        return True
    if len(parts) == 2 and parts[1] == "lessons-ledger.yaml":
        # The prescription-lineage ledger is the single admitted kernel YAML
        # (T11, Smith 0704 ratified landing path); arbitrary kernel YAML/JSON
        # stays closed.
        return True
    return len(parts) >= 2 and parts[-1].endswith(".md")


def package_path_admission_self_probe_violations() -> list[str]:
    cases = {
        "project/brick-protocol/status/kernel/GOAL/cr-v3-p2-official-replay-graph-0628b.json": True,
        "project/brick-protocol/status/kernel/GOAL/cr_v3_p2_official_replay_graph_0628b.json": True,
        "project/brick-protocol/status/kernel/GOAL/not-a-graph.jsonl": False,
        "project/brick-protocol/status/kernel/OTHER/cr-v3-p2-official-replay-graph-0628b.json": False,
        "project/brick-protocol/status/kernel/GOAL/nested/graph.json": False,
        "project/brick-protocol/status/kernel/GOAL/.hidden.json": False,
        "project/brick-protocol/status/kernel/arbitrary.json": False,
        "project/brick-protocol/status/kernel/lessons-ledger.yaml": True,
        "project/brick-protocol/status/kernel/other-ledger.yaml": False,
        "project/brick-protocol/status/arbitrary.json": False,
        "project/brick-protocol/buildings/agents-md-align-0702a/task-statement-30d7bc45e2bc-node/": True,
        "project/brick-protocol/buildings/agents-md-align-0702a/task-statement-30d7bc45e2bc-node/capture/": True,
        "project/brick-protocol/buildings/agents-md-align-0702a/task-statement-30d7bc45e2bc-node/capture/events.jsonl": True,
        "project/brick-protocol/buildings/agents-md-align-0702a/task-statement-30d7bc45e2bc-node/evidence/claim_trace/agent/returned_claims.json": True,
        "project/brick-protocol/buildings/agents-md-align-0702a/task-statement-30d7bc45e2bc-node/proposed-building-graph.json": True,
        "project/brick-protocol/buildings/agents-md-align-0702a/task-statement-30d7bc45e2bc-node/work/proposed-building-graph.json": True,
        "project/brick-protocol/buildings/agents-md-align-0702a/not-a-vessel-node/capture/events.jsonl": False,
        "project/brick-protocol/buildings/agents-md-align-0702a/task-statement--node/capture/events.jsonl": False,
        "project/brick-protocol/buildings/agents-md-align-0702a/task-statement-30d7bc45e2bc-node/stray.txt": False,
    }
    violations: list[str] = []
    for path, expected in cases.items():
        observed = allowed_path(path)
        if observed != expected:
            violations.append(
                "package_path_admission self-probe expected "
                f"{path} allowed={expected}, observed allowed={observed}"
            )
    return violations


def is_project_portfolio_projection_path(path: str, *, is_dir: bool) -> bool:
    parts = _project_family_tail(path, PROJECT_PORTFOLIO_PROJECTION_SEGMENT)
    if parts is None:
        return False
    if len(parts) == 0:
        return is_dir
    if len(parts) == 1:
        return is_dir and slug_part(parts[0])
    return (
        len(parts) == 2
        and not is_dir
        and slug_part(parts[0])
        and parts[1] == "portfolio-projection.json"
    )


def is_dashboard_surface_path(path: str, *, is_dir: bool) -> bool:
    """DASHBOARD-SURFACE-0: the vendored read-only dashboard runtime subtree.

    A self-contained React + SSE-server surface under support/dashboard. Its JS
    deps / build output / generated data are residue-filtered (ignored_repo_path),
    so what remains here is source: dirs plus files with a web-source/doc
    extension or the root config files. Owns no crossing, judges nothing, runs
    no engine.
    """

    parts = path_tail(path, DASHBOARD_SURFACE_ROOT)
    if parts is None:
        return False
    if len(parts) == 0:
        return is_dir
    if is_dir:
        return True
    name = parts[-1]
    if name in DASHBOARD_SURFACE_ROOT_FILES:
        return True
    return name.endswith(DASHBOARD_SURFACE_FILE_EXTS)


def to_posix(path: Path | str) -> str:
    value = str(path).replace("\\", "/").strip()
    while value.startswith("./"):
        value = value[2:]
    return value


def path_tail(path: str, root: str) -> list[str] | None:
    parts = path.split("/")
    root_parts = root.split("/")
    if parts[: len(root_parts)] != root_parts:
        return None
    return parts[len(root_parts) :]


def is_v03_dogfood_pilot_path(path: str, *, is_dir: bool) -> bool:
    parts = path_tail(path, V03_DOGFOOD_ROOT)
    if parts is None:
        return False

    if len(parts) == 0:
        return is_dir

    run_id = parts[0]
    if not run_id:
        return False

    if len(parts) == 1:
        return is_dir

    role = parts[1]
    if role not in V03_DOGFOOD_ROLE_DIRS:
        return False

    if len(parts) == 2:
        return is_dir

    if len(parts) != 3 or is_dir:
        return False

    filename = parts[2]
    return (role, filename) in V03_DOGFOOD_ALLOWED_RECORDS


def is_bes_dogfood_pilot_path(path: str, *, is_dir: bool) -> bool:
    parts = path_tail(path, BES_DOGFOOD_ROOT)
    if parts is None:
        return False

    if len(parts) == 0:
        return is_dir

    run_id = parts[0]
    if not run_id:
        return False

    if len(parts) == 1:
        return is_dir

    if len(parts) == 2:
        if is_dir:
            return parts[1] == "bricks"
        return parts[1] in BES_RUN_RECORDS

    if parts[1] != "bricks":
        return False

    brick_id = parts[2]
    if not brick_id:
        return False

    if len(parts) == 3:
        return is_dir

    brick_child = parts[3]
    if len(parts) == 4:
        if is_dir:
            return brick_child in BES_BRICK_DIRS
        return brick_child == "variables.json"

    if brick_child == "events":
        return len(parts) == 5 and not is_dir and parts[4] in BES_EVENTS_RECORDS

    if brick_child == "raw":
        return len(parts) == 5 and not is_dir and parts[4] in BES_RAW_RECORDS

    if brick_child == "claim_trace":
        if len(parts) == 5:
            return is_dir and parts[4] in BES_CLAIM_TRACE_DIRS
        if len(parts) == 6 and not is_dir:
            return (parts[4], parts[5]) in BES_CLAIM_TRACE_RECORDS
        return False

    if brick_child == "evaluation_improvement":
        return len(parts) == 5 and not is_dir and parts[4] in BES_EVALUATION_RECORDS

    return False


def is_prh_b_building_evidence_path(path: str, *, is_dir: bool) -> bool:
    parts = path_tail(path, PRH_B_BUILDING_EVIDENCE_ROOT)
    if parts is None:
        return False

    if len(parts) == 0:
        return is_dir

    building_id = parts[0]
    if not building_id:
        return False

    if len(parts) == 1:
        return is_dir

    if len(parts) == 2:
        if is_dir:
            return parts[1] == "bricks"
        return parts[1] in PRH_B_RUN_RECORDS

    if parts[1] != "bricks":
        return False

    brick_id = parts[2]
    if not brick_id:
        return False

    if len(parts) == 3:
        return is_dir

    brick_child = parts[3]
    if len(parts) == 4:
        if is_dir:
            return brick_child in PRH_B_BRICK_DIRS
        return brick_child == "variables.json"

    if brick_child == "events":
        return len(parts) == 5 and not is_dir and parts[4] in PRH_B_EVENTS_RECORDS

    if brick_child == "raw":
        return len(parts) == 5 and not is_dir and parts[4] in PRH_B_RAW_RECORDS

    if brick_child == "claim_trace":
        if len(parts) == 5:
            return is_dir and parts[4] in PRH_B_CLAIM_TRACE_DIRS
        if len(parts) == 6 and not is_dir:
            return (parts[4], parts[5]) in PRH_B_CLAIM_TRACE_RECORDS
        return False

    return False


_SPINE_EVENT_TYPES_CACHE: frozenset[str] | None = None


def _spine_event_types() -> frozenset[str]:
    """The admitted spine event_type set, single-sourced from spine.py.

    Lazy + cached so this foundational path gate carries NO import-time
    dependency on brick_protocol (other checkers import this module early and
    only ever classify support/*.py paths through it). Bootstraps the
    import_identity router onto sys.path if needed.
    """

    global _SPINE_EVENT_TYPES_CACHE
    if _SPINE_EVENT_TYPES_CACHE is None:
        import os.path as _osp
        import sys as _sys

        repo_root = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
        import_identity = _osp.join(repo_root, "support", "import_identity")
        for entry in (import_identity, repo_root):
            if entry not in _sys.path:
                _sys.path.insert(0, entry)
        from brick_protocol.support.recording.spine import SPINE_EVENT_TYPES

        _SPINE_EVENT_TYPES_CACHE = SPINE_EVENT_TYPES
    return _SPINE_EVENT_TYPES_CACHE


def spine_event_filename_admitted(filename: str) -> bool:
    """A spine per-event file name <seq>-<type>.(json|md) (NEVER .tmp).

    <seq> = digits; <type> = a real spine event_type (single-sourced); ext =
    json|md. ALLOW-only (this checker enforces no presence). A .tmp is a torn
    write residue-filtered by the collector, never reaching here.
    """

    for ext in (".json", ".md"):
        if filename.endswith(ext):
            stem = filename[: -len(ext)]
            seq_text, sep, type_segment = stem.partition("-")
            if not sep or not seq_text.isdigit():
                return False
            return type_segment in _spine_event_types()
    return False


def is_project_building_lifecycle_path(path: str, *, is_dir: bool) -> bool:
    parts = path.split("/")
    if len(parts) < 3 or parts[0] != "project":
        return False
    if any(part in BUILDING_LIFECYCLE_FORBIDDEN_SEGMENTS for part in parts):
        return False

    project_id = parts[1]
    if not vessel_id_part(project_id):
        return False

    if len(parts) == 2:
        return is_dir

    if parts[2] != "buildings":
        return False

    if len(parts) == 3:
        return is_dir

    if len(parts) == 4 and not is_dir:
        filename = parts[3]
        suffix = "-composed-plan.json"
        stem = filename[: -len(suffix)] if filename.endswith(suffix) else ""
        # support/operator/onboard.py persists a pre-run frozen composed-plan
        # input at the buildings root before the Building evidence root exists.
        # The later run copies the same declared plan into the Building root.
        return bool(stem and slug_part(stem))

    building_id = parts[3]
    if not building_id:
        return False

    if len(parts) == 4:
        return is_dir

    # Declared Building vessel layout:
    # project/<project>/buildings/<slug>/task-statement-*-node/<lifecycle...>.
    # The outer slug is only a grouping container; lifecycle admission remains
    # the same closed record/dir set under the task-statement node.
    if len(parts) >= 5 and task_statement_node_part(parts[4]):
        if not slug_part(building_id):
            return False
        building_id = parts[4]
        if len(parts) == 5:
            return is_dir
        tail = tuple(parts[5:])
    else:
        tail = tuple(parts[4:])

    if building_id in COMPACT_HISTORICAL_CAP_BOOT_BUILDINGS:
        allowed_dirs = HISTORICAL_BUILDING_LIFECYCLE_DIRS
        allowed_records = HISTORICAL_BUILDING_LIFECYCLE_RECORDS
    elif building_id in FULL_HISTORICAL_CAP_BOOT_BUILDINGS:
        allowed_dirs = BUILDING_LIFECYCLE_DIRS
        allowed_records = BUILDING_LIFECYCLE_RECORDS
    else:
        allowed_dirs = MINIMAL_BUILDING_LIFECYCLE_DIRS
        allowed_records = MINIMAL_BUILDING_LIFECYCLE_RECORDS

    if is_dir:
        if len(tail) in {2, 3} and tail[:2] == ("work", "step-outputs"):
            return True
        return tail in allowed_dirs
    if tail in allowed_records:
        return True
    if (
        len(tail) == 4
        and tail[:2] == ("work", "step-outputs")
        and tail[3]
        in {
            "step-output.json",
            "route-request.json",
            "transition-concern.json",
            "adapter-error.json",
            "work-envelope.json",
            "parked.json",
            "claim.json",
            "submission.json",
        }
        and slug_part(tail[2])
    ):
        return True
    if (
        len(tail) == 4
        and tail[:2] == ("evidence", "claim_trace")
        and tail[2] in {"agent", "link"}
        and tail[3]
        in {
            "receipt_trace.json",
            "frontier_trace.json",
        }
    ):
        return True
    if len(tail) == 2 and tail[0] == "raw":
        filename = tail[1]
        return filename not in {".DS_Store", "debug.log"} and filename.endswith(
            (".jsonl", ".json", ".md", ".txt", ".log")
        )
    # U5.5 SLICE-1A: the Evidence Spine projection files. ALLOW-only (no presence
    # logic — the lifecycle-shape checker owns generation-gated presence). The 3
    # index records by fixed name; the per-event artifacts by PATTERN (variable
    # filename). A .tmp never reaches here (collector residue-filter). (quality/
    # admission is DEFERRED to slice-4 with its Layer-2 validator.)
    if (
        len(tail) == 3
        and tail[:2] == ("evidence", "spine")
        and tail[2] in {"spine.json", "spine.jsonl", "spine.md"}
    ):
        return True
    if len(tail) == 4 and tail[:3] == ("evidence", "spine", "events"):
        return spine_event_filename_admitted(tail[3])
    return False


def read_fixture_list(path: Path) -> list[str]:
    paths: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        paths.append(to_posix(stripped))
    return paths


def ignored_repo_path(path: str) -> bool:
    if path == ".git" or path.startswith(".git/"):
        return True
    if path == ".claude" or path.startswith(".claude/"):
        return True
    # .codex/ is the SAME machine-config-dir class as .claude/: per-LLM hook/config
    # files (gitignored, engine never parses them). Excluded the same way.
    if path == ".codex" or path.startswith(".codex/"):
        return True
    # W1 worktree sandbox marker: support/operator/worktree_sandbox.py stamps
    # engine-created disposable worktrees with this untracked file so cleanup can
    # prove the path is engine-owned. It is support residue, not a source surface.
    if path == ".brick-engine-worktree":
        return True
    # ONBOARDING (0610): machine/build-artifact class produced by the
    # documented installer (support/onboarding/install.sh -> uv sync). The
    # local virtualenv remains gitignored machine state.
    if path == ".venv" or path.startswith(".venv/"):
        return True
    if path == ".ruff_cache" or path.startswith(".ruff_cache/"):
        return True
    if path == ".pytest_cache" or path.startswith(".pytest_cache/"):
        return True
    if path == "build" or path.startswith("build/"):
        return True
    if path.endswith(".egg-info") or ".egg-info/" in path:
        return True
    if path == ".DS_Store" or path.endswith("/.DS_Store"):
        return True
    if "__pycache__" in path.split("/"):
        return True
    if path.endswith((".pyc", ".pyo")):
        return True
    # DASHBOARD-SURFACE-0: the vendored dashboard surface keeps its JS deps + build
    # output + generated data out of source admission (gitignored, rebuilt on deploy).
    if "node_modules" in path.split("/"):
        return True
    if path == "support/dashboard/dist" or path.startswith("support/dashboard/dist/"):
        return True
    if path == "support/dashboard/public/dashboard-data.json":
        return True
    # U5.5 SLICE-1A: a stale ``*.tmp`` is a torn atomic write (the spine writer +
    # os.replace consume the temp on the normal path; a crash may leave one).
    # RESIDUE-FILTER it in the collector so it is never handed to allow/reject.
    if path.endswith(".tmp"):
        return True
    return False


def has_collectable_descendant(path: Path, repo: Path) -> bool:
    for descendant in path.rglob("*"):
        rel = to_posix(descendant.relative_to(repo))
        if not ignored_repo_path(rel):
            return True
    return False


def collect_repo_paths(repo: Path) -> list[str]:
    paths: list[str] = []
    for path in sorted(repo.rglob("*")):
        rel = to_posix(path.relative_to(repo))
        if ignored_repo_path(rel):
            continue
        if path.is_dir() and not has_collectable_descendant(path, repo):
            continue
        paths.append(rel + "/" if path.is_dir() else rel)
    return paths


def collect_paths(args: argparse.Namespace) -> tuple[str, list[str]]:
    if args.target:
        target = Path(args.target)
        if target.is_file():
            return str(target), read_fixture_list(target)
        if target.is_dir():
            return str(target), collect_repo_paths(target)
        raise FileNotFoundError(f"target does not exist: {target}")

    if args.repo:
        repo = Path(args.repo)
        if not repo.is_dir():
            raise FileNotFoundError(f"repo does not exist: {repo}")
        return str(repo), collect_repo_paths(repo)

    if args.fixture:
        fixture = Path(args.fixture)
        if fixture.is_file():
            return str(fixture), read_fixture_list(fixture)
        if fixture.is_dir():
            fixture_lists = sorted(fixture.glob("*.txt"))
            if fixture_lists:
                paths: list[str] = []
                for fixture_list in fixture_lists:
                    paths.extend(read_fixture_list(fixture_list))
                return str(fixture), paths
            return str(fixture), collect_repo_paths(fixture)
        raise FileNotFoundError(f"fixture does not exist: {fixture}")

    return ".", collect_repo_paths(Path("."))


def forbidden_reason(path: str) -> str | None:
    clean = path.rstrip("/")
    is_dir = path.endswith("/")
    old_physical_roots = {
        "brick_protocol/brick": "brick/",
        "brick_protocol/agent": "agent/",
        "brick_protocol/link": "link/",
        "brick_protocol/runner": "support/operator/run.py",
        "brick_protocol": "support/import_identity/brick_protocol/",
        "brick_recorder": "support/recording/",
        "tests/checkers": "support/checkers/",
        "docs": "support/docs/",
        ".status": "project/brick-protocol/status/",
        "building-evidence": "project/brick-protocol/building-evidence/",
    }
    for old_root, new_root in old_physical_roots.items():
        if clean == old_root or clean.startswith(f"{old_root}/"):
            return f"old physical path {clean} is superseded by {new_root}"

    if clean == "architecture-review-site" or clean.startswith("architecture-review-site/"):
        return (
            f"removed projection root {clean} is not admitted; "
            "root-level public docs site / Vercel projection surfaces are closed"
        )

    if clean.startswith("brick_protocol/"):
        return (
            f"unadmitted root-level brick_protocol path {clean}; the import "
            "identity marker lives under support/import_identity/brick_protocol"
        )

    if (
        clean in {
            "gate.py",
            "gate.yaml",
            "gate.yml",
            "brick/gate.py",
            "brick/gate.yaml",
            "brick/gate.yml",
            "agent/gate.py",
            "agent/gate.yaml",
            "agent/gate.yml",
            "brick_protocol/gate.py",
            "brick_protocol/gate.yaml",
            "brick_protocol/gate.yml",
        }
        or clean == "gate"
        or clean.startswith("gate/")
        or clean == "brick/gate"
        or clean.startswith("brick/gate/")
        or clean == "agent/gate"
        or clean.startswith("agent/gate/")
        or clean == "brick_protocol/gate"
        or clean.startswith("brick_protocol/gate/")
        or clean == "link/gate"
        or clean.startswith("link/gate/")
    ):
        return f"standalone Gate path {clean} is not admitted"

    if (
        clean in {
            "transfer.py",
            "transfer.yaml",
            "transfer.yml",
            "carry.py",
            "carry.yaml",
            "carry.yml",
            "brick/transfer.py",
            "brick/transfer.yaml",
            "brick/transfer.yml",
            "agent/transfer.py",
            "agent/transfer.yaml",
            "agent/transfer.yml",
            "brick_protocol/transfer.py",
            "brick_protocol/transfer.yaml",
            "brick_protocol/transfer.yml",
            "brick/carry.py",
            "brick/carry.yaml",
            "brick/carry.yml",
            "agent/carry.py",
            "agent/carry.yaml",
            "agent/carry.yml",
            "brick_protocol/carry.py",
            "brick_protocol/carry.yaml",
            "brick_protocol/carry.yml",
        }
        or clean in {"transfer", "carry", "brick/transfer", "agent/transfer", "brick/carry", "agent/carry"}
        or clean.startswith("transfer/")
        or clean.startswith("carry/")
        or clean.startswith("brick/transfer/")
        or clean.startswith("agent/transfer/")
        or clean.startswith("brick/carry/")
        or clean.startswith("agent/carry/")
        or clean == "brick_protocol/transfer"
        or clean.startswith("brick_protocol/transfer/")
        or clean == "brick_protocol/carry"
        or clean.startswith("brick_protocol/carry/")
    ):
        return f"standalone transfer/carry path {clean} is not admitted"

    if clean.split("/", 1)[0] in {
        "brick_engine",
        "engine",
        "runtime",
        "storage",
        "wiki",
        "legacy",
        "provider",
        "scheduler",
        "dashboard",
    }:
        return f"legacy/runtime/support owner root {clean} is not admitted"

    if clean == "support/recording/__main__.py":
        return (
            "support/recording/__main__.py is a superseded public recorder "
            "entrypoint; SIMPLE-RUN-0 keeps support/operator/run.py as the public "
            "Building run entrypoint"
        )

    if clean == "support/run.py":
        return (
            "support/run.py is superseded by support/operator/run.py as the "
            "active public Building run surface"
        )

    if clean in {
        "support/agent_adapter.py",
        "support/agent_resources.py",
        "support/coo_sync.py",
        "support/mcp_projection.py",
    }:
        return (
            f"{clean} is superseded by support/connection/ as the active "
            "support connection folder"
        )

    if clean.startswith("support/recording/") and clean.endswith(".py"):
        if clean not in PRH_B_RECORDER_TARGETS:
            return (
                f"unadmitted support recording path {clean}; PRH-B admits only "
                "the packet writer namespace under support/recording"
            )

    if clean.startswith("tests/legacy/") or clean == "tests/legacy":
        return f"legacy tests as active tests are not admitted: {clean}"

    if clean == ".status" or clean.startswith(".status/"):
        return f"old status path {clean} is superseded by project/brick-protocol/status/"

    if clean == "support/status" or clean.startswith("support/status/"):
        return (
            f"old support status path {clean} is superseded by "
            "project/brick-protocol/status/ as the active status root"
        )

    if clean.startswith(("brick/", "agent/", "link/")) and clean.endswith((".py", ".yaml", ".yml")):
        if is_agent_resource0_path(clean, is_dir=is_dir):
            return None
        if is_template0_brick_template_path(clean, is_dir=is_dir):
            return None
        if is_brick_task_path(clean, is_dir=is_dir):
            return None
        if is_brick_building_plan_path(clean, is_dir=is_dir):
            return None
        if is_bar_v2_brick_data_path(clean, is_dir=is_dir):
            return None
        if is_bar_v2_link_data_path(clean, is_dir=is_dir):
            return None
        if (
            clean not in PACKAGE_MARKERS
            and clean not in PHASE4_TARGETS
            and clean not in LTC0_LINK_TRANSFER_CARRY_TARGETS
            and clean not in LINK_SPEC0_TARGETS
            and clean not in AGENT_SPEC0_TARGETS
            and clean not in BRICK_SPEC0_TARGETS
        ):
            return (
                f"unadmitted axis path {clean}; only seed markers and "
                "Phase 4 target surfaces plus the LTC-0 Link transfer/carry "
                "file pairs and the E2/S3 link/spec.py + E2/S6 agent/spec.py "
                "+ E2/S9 brick/spec.py axis surfaces are open now"
            )

    if clean == "support/runner" or clean.startswith("support/runner/"):
        return (
            f"superseded support runner path {clean}; SIMPLE-RUN-0 admits "
            "support/operator/run.py as the only public Building run surface"
        )

    if clean == "support/invocation" or clean.startswith("support/invocation/"):
        return (
            f"superseded support invocation path {clean}; SIMPLE-RUN-0 admits "
            "support/connection/agent_adapter.py as the only public Agent brain connection surface"
        )

    if clean == "support/building_run" or clean.startswith("support/building_run/"):
        return (
            f"superseded support building_run path {clean}; SIMPLE-RUN-0 admits "
            "support/operator/run.py as the only public Building run surface"
        )

    return None


def allowed_path(path: str) -> bool:
    clean = path.rstrip("/")
    is_dir = path.endswith("/")

    if is_dir:
        return (
            clean in ALLOWED_DIRS
            or is_project_root_declaration_path(clean, is_dir=True)
            or is_agent_resource0_path(clean, is_dir=True)
            or is_support_connector_resource0_path(clean, is_dir=True)
            or is_template0_brick_template_path(clean, is_dir=True)
            or is_brick_task_path(clean, is_dir=True)
            or is_brick_building_plan_path(clean, is_dir=True)
            or is_bar_v2_brick_data_path(clean, is_dir=True)
            or is_bar_v2_link_data_path(clean, is_dir=True)
            or is_project_status_path(clean, is_dir=True)
            or is_project_portfolio_projection_path(clean, is_dir=True)
            or is_v03_dogfood_pilot_path(clean, is_dir=True)
            or is_bes_dogfood_pilot_path(clean, is_dir=True)
            or is_prh_b_building_evidence_path(clean, is_dir=True)
            or is_project_building_lifecycle_path(clean, is_dir=True)
            or is_dashboard_surface_path(clean, is_dir=True)
        )

    if (
        clean in ROOT_FILES
        or clean in PACKAGE_MARKERS
        or clean in PHASE4_TARGETS
        or clean in LTC0_LINK_TRANSFER_CARRY_TARGETS
        or clean in LINK_SPEC0_TARGETS
        or clean in AGENT_SPEC0_TARGETS
        or clean in BRICK_SPEC0_TARGETS
    ):
        return True

    if clean in SIMPLE_RUN0_RUN_TARGETS:
        return True

    if clean in AGENT_ADAPTER0_TARGETS:
        return True

    if clean in AGENT_RESOURCE_TOOLKIT0_TARGETS:
        return True

    if clean in COO_SYNC0_TARGETS:
        return True

    if clean in MCP_PROJECTION0_TARGETS:
        return True

    if clean in BUILDING_DESIGN_TOOLKIT0_TARGETS:
        return True

    if clean in SECRET_TEXT0_TARGETS:
        return True

    if clean in CONNECT_GENERATOR0_TARGETS:
        return True

    if clean in BUILDING_OPERATION_SURFACE0_TARGETS:
        return True

    if clean in ONBOARD_WIZARD0_TARGETS:
        return True

    if clean in SINK_REGISTRY0_TARGETS:
        return True

    if clean in BRICK_CLI_ENTRYPOINT0_TARGETS:
        return True

    if clean in PROJECT_DECLARATION0_TARGETS:
        return True

    if clean in PROJECT_CREATION0_TARGETS:
        return True

    if clean in PROJECT_PROGRESS0_TARGETS:
        return True

    if clean in WORKFLOW_IMPORT0_TARGETS:
        return True

    if clean in ONBOARD_INSTALL_SCRIPT0_TARGETS:
        return True

    if clean in ONBOARD_RELEASE_EXPORT0_TARGETS:
        return True

    if clean == ".github/workflows/release-gate.yaml":
        return True

    if clean in ONBOARD_RECORDING_HOOK_TEMPLATE_TARGETS:
        return True

    if clean in BAR_V2_OPERATOR_TARGETS:
        return True

    if clean in REPORTER_NOTIFICATION_PROJECTION0_TARGETS:
        return True

    if clean in REPORT_ENV_AUTOLOAD0_TARGETS:
        return True

    if clean in DASHBOARD_EXPORT0_TARGETS:
        return True

    if clean in HEART_FRONTDOOR0_TARGETS:
        return True

    if clean in BRICK_KIND_SCAFFOLD0_TARGETS:
        return True

    if clean in TASK_ORDER_PREFLIGHT0_TARGETS:
        return True

    if clean in PLAN_EXPANSION0_TARGETS:
        return True

    if clean in PLAN_EXPANSION0_FIXTURES:
        return True

    if is_dashboard_surface_path(clean, is_dir=False):
        return True


    if clean in ELEGANT_REFACTOR_WALKER_TARGETS:
        return True

    if clean in ELEGANT_REFACTOR_BUILDING_OPERATION_TARGETS:
        return True

    if clean in PRH_B_RECORDER_TARGETS:
        return True

    if clean in SUPPORT_DOC_TEMPLATE_FILES:
        return True

    if is_template0_brick_template_path(clean, is_dir=False):
        return True

    if is_brick_task_path(clean, is_dir=False):
        return True

    if is_brick_building_plan_path(clean, is_dir=False):
        return True

    if is_bar_v2_brick_data_path(clean, is_dir=False):
        return True

    if is_bar_v2_link_data_path(clean, is_dir=False):
        return True

    if is_agent_resource0_path(clean, is_dir=False):
        return True

    # ELEGANT-REFACTOR P3a: the checker-runner helper sublayer. common.py plus
    # the lifted check_profile bodies (yaml_subset / rule_runners / case_runners
    # / kernel_checks) live directly under support/checkers/lib as a flat package
    # of single-concern checker-lib modules (engine blueprint 0531 §5). Each is a
    # registered module_registry.yaml row (G4 bidirectional tie).
    lib_parts = clean.split("/")
    if (
        len(lib_parts) == 4
        and lib_parts[:3] == ["support", "checkers", "lib"]
        and lib_parts[3].endswith(".py")
    ):
        return True

    if clean in CROSSING_ELEGANCE_REGISTRY_FILES:
        return True

    profile_parts = clean.split("/")
    if (
        len(profile_parts) == 4
        and profile_parts[:3] == ["support", "checkers", "profiles"]
        and profile_parts[3].endswith(".yaml")
    ):
        return True

    if clean in FINAL_CHECKER_FILES:
        return True

    if is_project_root_declaration_path(clean, is_dir=False):
        return True
    if is_project_status_path(clean, is_dir=False):
        return True
    if is_project_portfolio_projection_path(clean, is_dir=False):
        return True

    if is_v03_dogfood_pilot_path(clean, is_dir=False):
        return True
    if is_bes_dogfood_pilot_path(clean, is_dir=False):
        return True
    if is_prh_b_building_evidence_path(clean, is_dir=False):
        return True
    if is_project_building_lifecycle_path(clean, is_dir=False):
        return True
    if clean.startswith("support/docs/spec/") and clean.endswith(".md"):
        return True
    if clean.startswith("support/docs/reviews/") and clean.endswith(".md"):
        return True
    if clean.startswith("support/docs/references/") and clean.endswith(".md"):
        return True
    if clean.startswith("support/docs/projection/") and clean.endswith(".md"):
        return True
    return False


def check_paths(paths: list[str]) -> list[str]:
    violations: list[str] = []
    for raw_path in paths:
        path = to_posix(raw_path)
        if not path:
            continue
        if ignored_repo_path(path):
            continue
        reason = forbidden_reason(path)
        if reason:
            violations.append(reason)
            continue
        if not allowed_path(path):
            violations.append(f"path {path.rstrip('/')} is not listed in current seed admission set")
    return violations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for package path admission; it does not "
            "prove implementation correctness, source truth, Movement, or project success."
        )
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument("--target", default=None)
    parser.add_argument("--policy", default=None, help="Accepted for planned commands; not used as authority.")
    parser.add_argument("--fixture", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        label, paths = collect_paths(args)
    except OSError as exc:
        print(f"package path admission rejected: {exc}", file=sys.stderr)
        return 1

    violations = package_path_admission_self_probe_violations()
    violations.extend(check_paths(paths))
    if violations:
        print("package path admission rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(
            "proof limit: this checker only inspects path admission; absence is not semantic readiness.",
            file=sys.stderr,
        )
        return 1

    print(
        "package path admission passed: "
        f"{len(paths)} inspected path(s) in {label}; inspected paths are within "
        "current admitted seed/checker/support/templates, Phase 4 target "
        "surfaces including the Link Gate contract "
        "file pair, SIMPLE-RUN-0 support/operator/run.py and support/connection/agent_adapter.py "
        "surfaces, the AGENT-RESOURCE-TOOLKIT-0 support/connection/agent_resources.py "
        "surface, the COO-SYNC-0 support/connection/coo_sync.py projection writer "
        "surface, the MCP-PROJECTION-0 support/connection/mcp_projection.py call-door "
        "surface, the BUILDING-OPERATION-SURFACE-0 support/operator helper "
        "surface, the project-status V03-4 dogfood pilot exact-file path family, "
        "the BES dogfood pilot exact-file path family, the PRH-B recorder "
        "support/recording exact-file family without __main__.py, the "
        "AGENT-RESOURCE-0 Agent resource families, the Brick-owned "
        "building_plans family, the project building-evidence exact-file family, "
        "or the project Building lifecycle historical/full/minimal "
        "manifest-driven path families."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

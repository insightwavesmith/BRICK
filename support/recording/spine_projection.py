"""U5.5 Evidence Spine — declaration + per-step spine projector.

This module projects the on-disk Builder / run support packets under ``work/`` into
the Evidence Spine via the append-only writer (``spine.append_spine_events``).
It covers the two once-per-building declaration packets and the per-executed-step
spine required by ``check_evidence_spine_projection.py``:

  * ``PresetExpansion`` from ``work/preset-expansion.json``.
  * ``LinkLaunchPolicy`` from ``work/link-launch-policy.json``.
  * ``BrickInput`` / ``AgentBinding`` / ``AgentReceipt`` / ``AgentReturn`` for each
    unique executed ``step_ref`` enumerated from
    ``work/step-outputs/*/step-output.json``.
  * the two Agent->Link SEAM events (``TransitionConcern`` / ``RouteRequest``) read
    from ``work/step-outputs/<step>-attempt-N/{transition-concern,route-request}.json``
    — PRESENT-WHEN-RAISED (zero-or-more per step, only when the Agent raised one);
    emitted AFTER ``AgentReturn`` and BEFORE the Link events so a ``Movement`` that
    adopts a concern finds it already listed.
  * the six per-step Link events (``LinkSufficiency`` / ``LinkGateCheck`` /
    ``LinkPolicyAction`` / ``Movement`` / ``LinkTransfer`` / ``LinkCarry``) read from
    ``evidence/claim_trace/link/*.json``.
  * the two TERMINAL building-scope events emitted ONCE per building AFTER all
    per-step events: exactly one ``Frontier`` (COMPUTED from
    ``observe_building_frontier`` — never read from a trace) and zero-or-more
    ``ResumeDisposition`` (read from the on-disk evidence-manifest plan_snapshot's
    resume observations).

The projector is DELTA-based and resume-safe: it reads the existing spine events'
``event_type`` + ``step_ref`` keys, computes only the missing declaration / per-step
events, and appends those missing bodies in one ordered batch. A second unchanged
assembly returns ``[]`` and writes nothing; a resume with new step-output dirs
appends only the new step refs. The writer remains honest append-only and performs
the structural / forbidden-key enforcement.

AXIS SCOPE (design §2, single-sourced via spine.SPINE_AXIS_SCOPE_LITERALS):
  * PresetExpansion -> ["Brick"]  (the Builder's preset/template expansion).
  * LinkLaunchPolicy -> ["Link"]  (the declared Link launch baseline).
  * BrickInput -> ["Brick"]       (the declared Brick row for the executed step).
  * AgentBinding -> ["Agent"]     (the declared Agent binding row for the step).
  * AgentReceipt -> ["Agent"]     (the agent "received the work" coordinates).
  * AgentReturn -> ["Agent"]      (the closed AgentFact return coordinates).

FORBIDDEN-KEY DISCIPLINE (design §6; spine._FORBIDDEN_KEYS_NORMALIZED): support
RECORDS facts and JUDGES NOTHING, so an event body must carry NO success / quality
/ fault / movement / target KEY ANYWHERE (the spine writer's scan is RECURSIVE and
KEY-only). The raw ``link_launch_policy_provenance`` packet nests two FORBIDDEN
KEYS inside every ``launch_rows[]`` entry — ``movement`` and ``target_ref`` (both
are in FORBIDDEN_CAPTURE_KEYS / RETURNED_FORBIDDEN_KEYS). They are NOT hoisted to
the body top level; they are kept NESTED in ``launch_rows[]`` but RENAMED to the
design's own non-forbidden run-event vocabulary so the projection records the SAME
mechanical facts without a forbidden key:
    movement   -> declared_movement      (the at-time declared edge movement)
    target_ref -> target_boundary_ref    (the at-time declared target boundary;
                                           the SAME rename MovementEvent uses for
                                           its target, design line 223)
This mirrors the design's consistent rename discipline (e.g. LinkGateCheckEvent
uses ``sufficiency`` not the forbidden ``result``, design line 214). The values are
copied verbatim; only the KEY name changes, so no information is lost and the body
passes the forbidden-key guard.

Every other field projected is a mechanical REF / ENUM / COUNT copied verbatim from
the packet (preset/shape/template refs, declared_gate_refs, node_reroute_budgets,
…). The projector adds NO new judgment field and copies NO success/quality/fault
field. Per-step AgentReturn copies only refs/enums/observed field names from
``step-output.json``; it never copies the raw ``returned`` blob.

Dependency direction (correct): spine_projection -> spine (recording). This module
imports the WRITER (spine.append_spine_events) + the single-source vocab constants;
it imports NO checker. It is pure-ish: it READS on-disk support packets and calls
the honest append-only writer (which refuses an unclean spine), and otherwise
judges nothing, launches nothing, chooses no Movement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from brick_protocol.support.recording.spine import (
    append_spine_events,
    spine_structural_violations,
)

# SINGLE-SOURCE every Link value vocabulary from its OWNING module (never re-list
# a literal here): MOVEMENT_LITERALS is Link's owned Movement tuple
# ('forward','reroute'); GATE_SUFFICIENCY_LITERALS is Gate's owned sufficiency tuple
# ('sufficient','insufficient','missing_required_facts'); ADMITTED_POLICY_ACTIONS is
# the operator gate-sequence's owned action tuple ('forward','hold','next','reroute').
# Importing them means the projector and the owning axis/observer agree by
# construction; if any drifts, the projector breaks at import, not silently.
from brick_protocol.link.movement import MOVEMENT_LITERALS
from brick_protocol.link.gate import GATE_SUFFICIENCY_LITERALS
from brick_protocol.support.operator.gate_sequence import ADMITTED_POLICY_ACTIONS

# SINGLE-SOURCE the two TERMINAL building-scope value vocabularies + the frontier
# observer from their OWNING modules (never re-list a literal here):
#   * FRONTIER_KINDS is the operator-observer's owned six frontier_kind literals;
#     observe_building_frontier COMPUTES the terminal frontier observation (it reads
#     already-written evidence, ALWAYS returns a frontier_kind, NEVER raises). The
#     projector COPIES that observation's facts into the Frontier event body — it does
#     not re-derive the frontier, it records the observer's computed fact.
#   * DISPOSITION_ACTIONS is Link's owned disposition-action tuple
#     ('raise','forward','stop'); a ResumeDisposition's disposition_action must be one
#     of these. Importing them means the projector and the owning observer/axis agree
#     by construction; a drift breaks at import, not silently.
from brick_protocol.support.operator.frontier_observation import (
    FRONTIER_KINDS,
    observe_building_frontier,
)
from brick_protocol.link.transition import DISPOSITION_ACTIONS

# SINGLE-SOURCE the step_ref->slug transform from the SAME primitive the claim_trace
# emitters use to BUILD a fact_ref's suffix (claims_*.py call _step_fact_ref, which
# slugs the step_ref via _resource_slug("step_ref", step_ref.replace(":", "-"))). The
# per-step join MUST match against the SLUGGED step_ref, not the raw step_ref, so a
# step_ref that the emitter would have slugged (e.g. a ':' -> '-') still joins to its
# facts. Importing the primitive means the projector's join and the emitter's fact_ref
# construction agree by construction.
from brick_protocol.support.operator.primitives import _resource_slug
from brick_protocol.support.recording.declaration_packets import latest_valid_declared_plan_packet

# Packet file names + their declared ``kind`` (single-sourced from the Builder's
# declaration_packets.py packet builders). The projector only projects a packet
# whose on-disk ``kind`` matches — a defence against pointing at the wrong file.
_PRESET_EXPANSION_PACKET = "preset-expansion.json"
_PRESET_EXPANSION_KIND = "preset_expansion_provenance"
_LINK_LAUNCH_POLICY_PACKET = "link-launch-policy.json"
_LINK_LAUNCH_POLICY_KIND = "link_launch_policy_provenance"
# slice-3 A+ ITEM 4: the building-intake provenance packet (TaskSource source).
_BUILDING_INTAKE_PACKET = "building-intake.json"
_BUILDING_INTAKE_KIND = "building_intake_provenance"
_DECLARED_BUILDING_PLAN_PACKET = "declared-building-plan.json"
_DECLARED_BUILDING_PLAN_KIND = "declared_building_plan_provenance"
_BUILDING_MAP_PACKET = "building-map.json"
_BUILDING_MAP_KIND = "building_graph_map"
_STEP_OUTPUT_PACKET = "step-output.json"

# Spine event types (single-sourced names that the slice-1A + projection checkers
# admit). Kept as constants so the event_type spelling is asserted in one place.
_PRESET_EXPANSION_EVENT = "PresetExpansion"
_LINK_LAUNCH_POLICY_EVENT = "LinkLaunchPolicy"
_BRICK_INPUT_EVENT = "BrickInput"
_AGENT_BINDING_EVENT = "AgentBinding"
# The MIDDLE of the Agent row per step: the agent "received the work" record
# (AgentBinding -> AgentReceipt -> AgentReturn). Read from the SAME step-output.json
# the AgentReturn body reads (the closed AgentFact's received_work coordinates +
# evidence ref); per-step, keyed by (event_type, step_ref) exactly like the other
# Brick/Agent rows.
_AGENT_RECEIPT_EVENT = "AgentReceipt"
_AGENT_RETURN_EVENT = "AgentReturn"
# slice-3 A+ ITEM 2: the Brick-axis MATCH fact per executed step (what the support
# observer recorded about how the Agent's return compared to the declared Brick
# contract). Read from evidence/claim_trace/brick/work_contract.json brick-comparison
# facts. Per-step, delta-keyed by (event_type, source_fact_ref) — a multi-attempt step
# carries multiple brick-comparison facts.
_BRICK_COMPARED_EVENT = "BrickCompared"
# slice-3 A+ part 2 ITEM 1: the Agent->Link SEAM events — what the Agent RAISED at the
# end of a step (a transition concern OR a route request; the two are MUTUALLY EXCLUSIVE
# per attempt, see step_outputs.py:80-81). Read from the on-disk
# work/step-outputs/<step>-attempt-N/{transition-concern,route-request}.json files
# (written by step_outputs.write_step_output ONLY when the Agent returned one). PRESENT-
# WHEN-RAISED: zero-or-more per step. Per-step, delta-keyed by (event_type,
# source_fact_ref) — the source_fact_ref is the file's own transition_concern_ref /
# route_request_ref. These sit on the Agent->Link seam (AgentReturn -> seam -> Link), so
# they are emitted AFTER AgentReturn and BEFORE the Link events, so a Movement that cites
# an adopted concern finds an already-listed TransitionConcern (the dangling guard
# resolves).
_TRANSITION_CONCERN_EVENT = "TransitionConcern"
_ROUTE_REQUEST_EVENT = "RouteRequest"
# slice-3 A+ ITEM 4: the building-intake provenance (the task source) recorded ONCE per
# building. Read from work/building-intake.json. Building-scope, delta-keyed by
# event_type alone (mirrors PresetExpansion / LinkLaunchPolicy).
_TASK_SOURCE_EVENT = "TaskSource"
# TERMINAL building-scope events (slice-3 INC-2): emitted once per building AFTER
# all per-step events. Frontier is exactly-one-per-building (keyed by event_type
# alone, like the two declarations); ResumeDisposition is zero-or-more (keyed by its
# own (resumed_from, disposition_action, paused_at_ref) — see below).
_FRONTIER_EVENT = "Frontier"
_RESUME_DISPOSITION_EVENT = "ResumeDisposition"

_BUILDING_SCOPE_DECLARATION_EVENTS = (
    _PRESET_EXPANSION_EVENT,
    _LINK_LAUNCH_POLICY_EVENT,
    # slice-3 A+ ITEM 4: TaskSource is a once-per-building intake-provenance
    # declaration, emitted exactly once like the other two (delta-keyed by event_type).
    _TASK_SOURCE_EVENT,
)

# The building-scope EVENT-TYPE-keyed events whose presence is tracked by event_type
# alone for the resume-safe delta (a 2nd projection is then a no-op). Frontier joins
# the two declarations here: it is exactly-one-per-building and carries no step_ref /
# source key, so event_type IS its unique delta key (mirrors PresetExpansion).
_BUILDING_SCOPE_EVENT_TYPE_KEYED = _BUILDING_SCOPE_DECLARATION_EVENTS + (
    _FRONTIER_EVENT,
)
_PER_STEP_EVENTS = (
    _BRICK_INPUT_EVENT,
    _AGENT_BINDING_EVENT,
    # AgentReceipt sits BETWEEN binding and return — the agent first received the
    # work, then returned. Keyed by (event_type, step_ref) like its siblings.
    _AGENT_RECEIPT_EVENT,
    _AGENT_RETURN_EVENT,
)

# Axis scope per event (design §2). Non-empty subset of
# spine.SPINE_AXIS_SCOPE_LITERALS — validated again by the writer.
_PRESET_EXPANSION_AXIS_SCOPE = ["Brick"]
_LINK_LAUNCH_POLICY_AXIS_SCOPE = ["Link"]
_BRICK_INPUT_AXIS_SCOPE = ["Brick"]
_AGENT_BINDING_AXIS_SCOPE = ["Agent"]
_AGENT_RECEIPT_AXIS_SCOPE = ["Agent"]
_AGENT_RETURN_AXIS_SCOPE = ["Agent"]
# slice-3 A+: BrickCompared records a Brick-axis match observation; TaskSource records
# the Builder/COO's Brick-axis intake (the task source). Both ["Brick"] (a non-empty
# subset of spine.SPINE_AXIS_SCOPE_LITERALS — re-validated by the writer).
_BRICK_COMPARED_AXIS_SCOPE = ["Brick"]
_TASK_SOURCE_AXIS_SCOPE = ["Brick"]
# slice-3 A+ part 2 ITEM 1: the seam events record an Agent->Link causal handoff (the
# Agent RAISED a concern / route request; the Link may adopt, not adopt, or override),
# so axis_scope = ["Agent", "Link"] (a non-empty subset of
# spine.SPINE_AXIS_SCOPE_LITERALS — re-validated by the writer).
_TRANSITION_CONCERN_AXIS_SCOPE = ["Agent", "Link"]
_ROUTE_REQUEST_AXIS_SCOPE = ["Agent", "Link"]

# TERMINAL events both record Link-axis facts (the frontier observation reads Link
# lifecycle records; the resume disposition records a Link transition_lifecycle
# disposition). axis_scope = ["Link"] for both (a non-empty subset of
# spine.SPINE_AXIS_SCOPE_LITERALS — re-validated by the writer).
_FRONTIER_AXIS_SCOPE = ["Link"]
_RESUME_DISPOSITION_AXIS_SCOPE = ["Link"]

# Frontier body fields COPIED VERBATIM from observe_building_frontier(...)'s return
# (all mechanical: an enum + a reason string + a counts map + the proof_limits /
# not_proven lists). NONE is a forbidden success/quality/fault/movement/target KEY
# (verified by the grounding + the forbidden-key guard). The observer's other return
# keys (kind / schema_version / building_root / latest_transition_lifecycle /
# missing_required_files) are DELIBERATELY OMITTED — the event records the frontier
# FACTS, not the observer envelope.
_FRONTIER_FIELDS = (
    "frontier_kind",
    "frontier_reason",
    "observed_counts",
    "proof_limits",
    "not_proven",
)

# ResumeDisposition body fields COPIED VERBATIM from each on-disk resume_observation
# (the SAME field-spec build_resume_observation emits: refs / an enum / counts / the
# proof_limits / not_proven lists). NONE is a forbidden KEY. The observation's
# envelope keys (kind / schema_version) are OMITTED — the event records the resume
# FACTS, not the observation envelope. ``disposition_action`` is enum-checked against
# Link's DISPOSITION_ACTIONS below (a value outside it RAISEs, fail-closed).
_RESUME_DISPOSITION_FIELDS = (
    "disposition_action",
    "resumed_from",
    "paused_at_ref",
    "pending_target_ref",
    "applied",
    "budget_increment",
    "node_budget",
    "node_landings",
    "proof_limits",
    "not_proven",
)

# The LOAD-BEARING ResumeDisposition fields that MUST be present in the source
# observation (mirror the _require_present_fields fail-closed pattern). A sparse
# observation missing one is a corrupt source -> RAISE, not a sparse event. The
# delta-key fields (resumed_from / disposition_action / paused_at_ref) plus the
# remaining mechanical facts are all required (a real resume observation always
# carries them — see walker_evidence.build_resume_observation).
_RESUME_DISPOSITION_REQUIRED = _RESUME_DISPOSITION_FIELDS

# The string fields that contribute to a ResumeDisposition's UNIQUE delta key. Read
# off the existing ResumeDisposition event BODIES on disk; a new observation whose key
# already has a spine event is skipped (idempotent re-projection + partial resume).
#
# These THREE string fields ALONE are NOT a sufficient key: a fan-in hold falls back
# to the sentinel "reroute-hold:unknown" for BOTH resumed_from and paused_at_ref (see
# walker_hold.py:107 `reroute_ref = ... or "reroute-hold:unknown"`), so two DISTINCT
# fan-in resumes that share a disposition_action collide on
# (resumed_from, disposition_action, paused_at_ref) and
# the 2nd would be silently DROPPED at the delta. The ``resume_ordinal`` field below
# (the observation's stable 0-based index in dynamic_walker_evidence.resume_observations)
# disambiguates them: it is appended to the key so two sentinel-colliding resumes are
# distinct. resume_observations is append-only / stable-ordered post-run, so the ordinal
# is stable across re-projection (idempotent) and partial resume (a new resume lands at
# a new index). ``resume_ordinal`` is an int and is NOT a forbidden success/quality/fault
# key (the forbidden rule is KEY-only over the success/quality/fault vocabulary).
_RESUME_DISPOSITION_KEY_FIELDS = (
    "resumed_from",
    "disposition_action",
    "paused_at_ref",
)

# The int field that makes two sentinel-colliding fan-in resumes distinct (F1 fix).
# The observation's 0-based index in dynamic_walker_evidence.resume_observations.
_RESUME_ORDINAL_FIELD = "resume_ordinal"

# Mechanical declaration fields copied verbatim from the preset_expansion packet.
# ALL refs / enums / counts; NONE is a forbidden success/quality/fault key. The
# agent_binding_declarations sub-field is DELIBERATELY OMITTED: the Agent ROW is a
# SEPARATE AgentBinding event, not part of the building-scope declaration event.
_PRESET_EXPANSION_FIELDS = (
    "building_id",
    "plan_ref",
    "composition_mode",
    "selected_shape_ref",
    "selected_preset_ref",
    "chain_preset_ref",
    "shape_catalog_ref",
    "chain_preset_catalog_source",
    "canonical_chain_preset_ref",
    "compat_chain_preset_ref",
    "chain_preset_catalog_scope",
    "common_basis_ref",
    "expanded_step_template_refs",
    "expanded_brick_template_refs",
)

# Mechanical top-level declaration fields copied verbatim from the
# link_launch_policy packet. ``launch_rows`` is handled separately (its per-row
# forbidden keys are renamed). NONE of these top-level keys is forbidden (the raw
# packet's only forbidden keys live INSIDE launch_rows).
_LINK_LAUNCH_POLICY_FIELDS = (
    "building_id",
    "plan_ref",
    "plan_shape",
    "selected_shape_ref",
    "declared_gate_refs",
    "node_reroute_budgets",
    "max_attempts_by_boundary",
)

# launch_rows[] per-row fields to copy verbatim (all non-forbidden) PLUS the two
# renamed forbidden keys handled explicitly below. ``route_replay_plan`` is NOT a
# forbidden key (only route_choice / route_target are); ``max_attempts`` is the
# optional carry-budget count the packet sometimes lifts out of route_replay_plan.
_LAUNCH_ROW_VERBATIM_FIELDS = (
    "step_ref",
    "edge_ref",
    "declared_gate_refs",
    "route_replay_plan",
    "max_attempts",
)

# The two forbidden launch-row keys -> their non-forbidden rename (kept NESTED).
_LAUNCH_ROW_RENAME = {
    "movement": "declared_movement",
    "target_ref": "target_boundary_ref",
}

# Per-step event field allowlists. These are deliberately narrow; the projector
# copies only the fields named by the BUILD-3b contract.
_BRICK_INPUT_FIELDS = (
    "work_statement",
    "comparison_rule",
    "required_return_shape",
)
_AGENT_BINDING_FIELDS = (
    "binding_role",
    "agent_performer_ref",
    "brick_instance_ref",
    "step_output_ref",
)

# slice-3 A+ ITEM 2: BrickCompared inner-fact fields. The two LOAD-BEARING fields that
# a real brick-comparison fact ALWAYS carries (a fact missing either is corrupt source
# and RAISES, fail-closed); copied verbatim plus the wider mechanical allowlist below.
# observed_match_kind / comparison_rule are open Agent-/support-returned strings — NOT
# an enum (do not invent one). ``comparison_observation`` MAY carry the phrase "not
# success judgment" in its VALUE — that is fine (the forbidden-key rule is KEY-only;
# none of these KEYS is a forbidden success/quality/fault/movement/target key).
_BRICK_COMPARED_REQUIRED_FIELDS = (
    "observed_match_kind",
    "comparison_rule",
)
# The full mechanical allowlist copied IF present (the two required above + the
# observation/work refs + the *_evidence list fields the emitter writes). Narrow on
# purpose: the projector records the SAME mechanical fields the comparison fact holds
# and judges nothing.
_BRICK_COMPARED_FIELDS = (
    "observed_match_kind",
    "comparison_rule",
    "comparison_observation",
    "work_reference",
    "comparison_evidence",
    "required_return_shape_evidence",
    "forbidden_shortcut_evidence",
)

# slice-3 A+ part 2 ITEM 1: the two Agent->Link SEAM files step_outputs.py writes (only
# when the Agent raised one; mutually exclusive per attempt). The seam events project
# from the ON-DISK files (NOT a re-run / re-derivation) — at-time recorded Agent returns.
_TRANSITION_CONCERN_FILE = "transition-concern.json"
_ROUTE_REQUEST_FILE = "route-request.json"
_STEP_OUTPUTS_DIR = "step-outputs"

# The TOP-LEVEL fields step_outputs.write_step_output stamps on each seam file (mechanical
# refs / an int / a bool — NO forbidden success/quality/fault/movement/target key). The
# file-level ``transition_concern_ref`` / ``route_request_ref`` is the SOURCE fact_ref
# (the delta key) and is carried explicitly; these are the OTHER mechanical coordinates
# copied verbatim IF present. The graph-ready envelope keys (@id / @context / id / source
# / type / time / etc.) + the proof_limits / not_proven / *_role / *_boundary prose are
# DELIBERATELY OMITTED — the seam event records the seam FACTS, not the whole envelope.
_TRANSITION_CONCERN_TOPLEVEL_FIELDS = (
    "step_ref",
    "agent_object_ref",
    "binding",
    "attempt_index",
    "step_output_ref",
)
_ROUTE_REQUEST_TOPLEVEL_FIELDS = _TRANSITION_CONCERN_TOPLEVEL_FIELDS

# The file-level REF key that IS the seam event's source_fact_ref + delta key. step_outputs
# writes it as ``transition-concern:<step-slug>:attempt-N`` / ``route-request:<step-slug>:
# attempt-N``; it is REQUIRED (a seam file that lacks it is corrupt source and RAISES).
_TRANSITION_CONCERN_REF_FIELD = "transition_concern_ref"
_ROUTE_REQUEST_REF_FIELD = "route_request_ref"

# The NESTED Agent-returned blob each seam file carries (already validated forbidden-clean
# at WRITE time by step_outputs._validate_no_payload_forbidden against RETURNED_FORBIDDEN_KEYS,
# so copying it verbatim adds no forbidden key — re-scanned by the writer regardless). Its
# inner ``concern_ref`` (the Agent's OWN concern handle) is what a Movement fact's adopted/
# not_adopted refs cite, so it is recorded as an ALIAS for ref-resolution (req-f 3c).
_TRANSITION_CONCERN_RETURNED_FIELD = "transition_concern_returned"
_ROUTE_REQUEST_RETURNED_FIELD = "route_request_returned"
# The inner handle inside ``transition_concern_returned`` a Movement's adopted/not_adopted
# refs cite (verified on real evidence: movement-fact route_decision_adopted_transition
# _concern_refs == the nested concern_ref, NOT the file-level transition_concern_ref).
_TRANSITION_CONCERN_INNER_REF_FIELD = "concern_ref"

# slice-3 A+ ITEM 4: TaskSource body fields copied verbatim from the building-intake
# packet IF present (refs + the proof_limits / not_proven lists). ``task_source_ref`` is
# REQUIRED (the KEY must exist; the packet builder may set it to "" when no task source
# ref was supplied, so an EMPTY string is allowed — only an absent KEY RAISES). The
# other named fields are copied if present; the packet's envelope keys (kind / building_id
# / declared_by / composition_mode / selected_* / declaration_evidence_refs) are
# DELIBERATELY OMITTED — TaskSource records the task-source FACTS, not the whole intake
# envelope. NONE of these is a forbidden success/quality/fault key.
_TASK_SOURCE_REQUIRED_FIELD = "task_source_ref"
_TASK_SOURCE_FIELDS = (
    "task_source_ref",
    "plan_ref",
    "proof_limits",
    "not_proven",
)

# ---------------------------------------------------------------------------
# PER-STEP LINK EVENTS (slice-3 INC-1): the six Link spine events emitted per
# executed step by READING the on-disk claim_trace/link/*.json (at-time recorded
# facts only — the projector NEVER re-runs the engine, re-derives, or simulates a
# Movement). Each claim_trace fact's step is encoded ONLY in its fact_ref SUFFIX
# ("{kind}:{NN}:{step_ref}"); step_refs carry no ':', so a step's facts in a trace
# are exactly those whose fact_ref endswith ":<step_ref>" (the unambiguous join).
# ---------------------------------------------------------------------------

# Spine event_type names (single-sourced from the writer-admitted SPINE_EVENT_TYPES;
# kept as constants so the spelling is asserted in one place — NO "Event" suffix).
_LINK_SUFFICIENCY_EVENT = "LinkSufficiency"
_LINK_GATE_CHECK_EVENT = "LinkGateCheck"
_LINK_POLICY_ACTION_EVENT = "LinkPolicyAction"
_MOVEMENT_EVENT = "Movement"
_LINK_TRANSFER_EVENT = "LinkTransfer"
_LINK_CARRY_EVENT = "LinkCarry"

# The CAUSAL emit order (append_spine_events assigns sequence_index in input-list
# order). Sufficiency FIRST so a later Movement can cite an already-listed gate
# review; GateCheck/PolicyAction next; Movement; then Transfer/Carry.
_LINK_PER_STEP_EVENTS = (
    _LINK_SUFFICIENCY_EVENT,
    _LINK_GATE_CHECK_EVENT,
    _LINK_POLICY_ACTION_EVENT,
    _MOVEMENT_EVENT,
    _LINK_TRANSFER_EVENT,
    _LINK_CARRY_EVENT,
)

# The per-step events keyed by (event_type, source_fact_ref) for the resume-safe delta.
# A step may legitimately carry MULTIPLE of one of these types (multiple gates, multiple
# attempts -> multiple brick-comparison facts), so the unique key is the SOURCE fact_ref,
# not (event_type, step). The six Link events PLUS BrickCompared (slice-3 A+ ITEM 2) PLUS
# the two Agent->Link SEAM events (slice-3 A+ part 2 ITEM 1: TransitionConcern /
# RouteRequest) all carry a ``source_fact_ref`` and share this delta basis. (BrickInput /
# AgentBinding / AgentReturn stay keyed by (event_type, step_ref) — one of each per step —
# in the separate per_step set.)
_PER_FACT_KEYED_EVENTS = _LINK_PER_STEP_EVENTS + (
    _BRICK_COMPARED_EVENT,
    _TRANSITION_CONCERN_EVENT,
    _ROUTE_REQUEST_EVENT,
)

# axis_scope = ["Link"] for ALL six (a non-empty subset of
# spine.SPINE_AXIS_SCOPE_LITERALS — re-validated by the writer).
_LINK_PER_STEP_AXIS_SCOPE = ["Link"]

# claim_trace/link source file names (NEVER raw/link.jsonl — at-time recorded facts
# only). gate_receipt / policy_action are NEW from E1 and MAY be absent for a
# building/step with no gates or no admitted policy action; the projector emits none
# for those (tolerant absence, NOT a fail-closed RAISE).
_SUFFICIENCY_TRACE = "sufficiency_trace.json"
_GATE_RECEIPT_TRACE = "gate_receipt_trace.json"
_POLICY_ACTION_TRACE = "policy_action_trace.json"
_MOVEMENT_TRACE = "movement_trace.json"
_TRANSFER_TRACE = "transfer_trace.json"
_CARRY_TRACE = "carry_trace.json"

# The forbidden RAW key the movement claim_trace fact still carries (only
# target_boundary_ref is pre-renamed there). The projector LAUNDERS it to the
# design's non-forbidden run-event vocabulary EXACTLY as _LINK_LAUNCH_POLICY uses
# _LAUNCH_ROW_RENAME: movement -> declared_movement (the at-time declared edge
# movement). The value is copied verbatim; only the KEY name changes, so the body
# passes the writer's recursive forbidden-key scan.
_MOVEMENT_FACT_RENAME = {
    "movement": "declared_movement",
}

# slice-3 A+ part 2 ITEM 2: the Agent->Link causal SEAM refs a movement_trace fact carries
# in its inner ``fact`` body — the transition-concern refs the Link ADOPTED / did NOT adopt
# at this movement, plus a route-request ref if the movement cited one. Source keys ->
# their (non-forbidden) Movement-event body keys. The route_decision_ prefix is dropped so
# the Movement body uses the design's seam vocabulary; the VALUES (ref lists / a string)
# are copied verbatim. NONE of these keys is forbidden (route_request_ref / *_concern_refs
# are refs; only ``route_target``/``target``/``target_ref`` are forbidden). A movement with
# NONE of these seam keys gets the list keys emitted as ``[]`` (consistent presence) and
# omits the optional string route_request_ref.
_MOVEMENT_SEAM_LIST_REFS = {
    "route_decision_adopted_transition_concern_refs": "adopted_transition_concern_refs",
    "route_decision_not_adopted_transition_concern_refs": "not_adopted_transition_concern_refs",
}
# The optional route-request ref a movement fact may carry (a string). step_outputs writes
# the seam route-request file's ref as ``route_request_ref``; a movement fact that paired
# with it carries the SAME key. Omitted from the body when the movement has none.
_MOVEMENT_SEAM_ROUTE_REQUEST_REF_KEY = "route_request_ref"

# Mechanical inner-``fact``-body fields copied verbatim per Link event (refs / enums
# / counts ONLY; NO success/quality/fault key; the absence variants copy the absence
# marker fields). These are deliberately narrow allowlists — the projector records
# the SAME mechanical facts the claim_trace already holds and judges nothing.
_SUFFICIENCY_PRESENT_FIELDS = (
    "sufficiency",
    "stage",
    "checked_public_fact",
    "required_public_facts",
    "missing_required_facts",
)
_ABSENCE_MARKER_FIELDS = (
    "trace_role",
    "absent_fact_type",
    "caller_supplied",
    "support_created_bal_fact",
)
_GATE_CHECK_FIELDS = (
    "gate_ref",
    "ordinal",
    "sufficiency",
    "checked_public_fact",
)
_POLICY_ACTION_FIELDS = (
    "policy_action",
    "action_reason",
    "reason_refs",
    "pending_target_ref",
    "target_brick_ref",
)
_TRANSFER_PRESENT_FIELDS = (
    "source_boundary_ref",
    "target_boundary_ref",
    "public_fact_refs",
    "work_context_ref",
    "required_public_facts",
    "transfer_gate_reference",
    "evidence_reference",
)
_CARRY_PRESENT_FIELDS = (
    "carried_fact_refs",
    "source_owner_axis",
    "target_boundary_ref",
    "carry_gate_reference",
    "evidence_reference",
)
# FIX #3: a BUILDING-SCOPE carry-budget fact (fact_ref
# "carry-budget:<building_id>:<scope_tag>:<budget_ref>") records a node's
# reroute/replay budget observation. Its inner body shape VARIES by scope (node vs
# route-replay), so the projection copies a defined SUPERSET present-if-present (the
# full union of inner keys observed across the corpus); a scope-specific field is
# simply absent for the other scope, never fail-closed. ALL of these are
# forbidden-key-SAFE (none normalizes to a forbidden success/quality/fault/movement/
# target key — note ``immediate_target_ref`` / ``target_boundary_ref`` are NOT the
# forbidden ``target`` / ``target_ref``). The minimum REQUIRED is budget_kind +
# budget_scope (every real carry-budget fact carries both; a fact lacking either is a
# torn source and RAISES — mirrors the present-Link fail-closed minimum pattern).
_CARRY_BUDGET_FIELDS = (
    "budget_exhausted",
    "budget_kind",
    "budget_missing",
    "budget_scope",
    "budget_source_refs",
    "carry_budget_evidence_ref",
    "declared_budget",
    "declared_by_ref",
    "disposition_required",
    "exhaustion_record_refs",
    "exhaustion_status",
    "immediate_target_ref",
    "not_proven",
    "observed_replay_execution_count_by_boundary",
    "observed_reroute_landings",
    "observed_step_attempt_count",
    "observed_total_execution_count_by_boundary",
    "proof_limits",
    "replay_segment_refs",
    "route_replay_ref",
    "source_step_ref",
    "support_created_bal_fact",
    "target_boundary_ref",
    "trace_role",
)
_CARRY_BUDGET_REQUIRED = ("budget_kind", "budget_scope")
# The fact_ref prefix of a BUILDING-SCOPE carry-budget fact in carry_trace.json.
# FIX P1#2: the prefix is COLON-ANCHORED ("carry-budget:") so the partition between the
# building-scope budget pass and the per-step carry pass is disjoint BY CONSTRUCTION — the
# colon both anchors the prefix (it can never match an unrelated "carry-budgetX") and is
# the same separator the real fact_ref ("carry-budget:<building_id>:...") uses.
_CARRY_BUDGET_FACT_PREFIX = "carry-budget:"

# The stage value the movement-stage sufficiency fact carries (Gate's owned stage
# literal). Used to pick the gate review a Movement event cites.
_MOVEMENT_GATE_STAGE = "movement"

# The fact_ref prefix of a movement-stage sufficiency fact ("sufficiency-fact-movement:
# NN:STEP"). A movement fact's inner ``public_fact_refs`` lists the SINGLE sufficiency
# review it actually paired with under this prefix, so a multi-attempt step's three
# Movements (movement-fact:01/03/06) cite their OWN suff:01/03/06 — not a single shared
# first one. Anchoring on this prefix (not a stage scan) lets each Movement pick the
# review IT paired with, read straight off the source movement fact. The values are the
# fact_refs of LinkSufficiency events the projector already emits for the same step, so
# the citation always resolves to an already-listed gate review.
_MOVEMENT_SUFFICIENCY_REF_PREFIX = "sufficiency-fact-movement:"

# The fact_ref INFIX that marks a per-EDGE graph-edge Link fact (built by
# plan_graph._graph_movement_fact_ref / _graph_transition_fact_ref as
# "movement-fact:graph-edge:<edge_slug>"). A graph-edge fact is per-edge, NOT
# per-step, so the per-step join must EXCLUDE it: a per-step join must never
# attribute a graph-edge fact to a step. Per-edge graph-edge Movement projection is
# a SEPARATE concern (OUT OF SCOPE for the per-step projector) — here we only
# exclude these facts, we do not project them.
_GRAPH_EDGE_FACT_INFIX = ":graph-edge:"


def _step_ref_slug(step_ref: str) -> str:
    """Slug a step_ref the SAME way _step_fact_ref slugged it into a fact_ref.

    The emitters build a step fact_ref via
    ``_step_fact_ref(kind, index, step_ref)`` ->
    ``f"{kind}:{index:02d}:{_resource_slug('step_ref', step_ref.replace(':', '-'))}"``.
    So the suffix the join matches against is ``":" + slug`` where
    ``slug = _resource_slug('step_ref', step_ref.replace(':', '-'))``. A step_ref
    that _resource_slug would REJECT (e.g. a path separator) raises here exactly as
    the emitter would have raised — fail-closed, never a silent mismatch.
    """

    return _resource_slug("step_ref", step_ref.replace(":", "-"))


class SpineProjectionError(RuntimeError):
    """A source packet could not be read / is malformed for projection.

    Raised when a required source is absent, unreadable, non-JSON, not a JSON
    object, carries the wrong declared ``kind``, or cannot be joined to the
    declared step/binding rows. A spine-writer integrity refusal surfaces as
    ``spine.SpineWriteError`` from append_spine_events; this error type covers the
    projector's own READ-side failures.
    """


def _load_json_object(packet_path: Path, *, source_label: str) -> dict[str, Any]:
    try:
        text = packet_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SpineProjectionError(f"{packet_path}: {source_label} unreadable: {exc}") from exc
    try:
        body = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SpineProjectionError(f"{packet_path}: {source_label} is not JSON: {exc}") from exc
    if not isinstance(body, dict):
        raise SpineProjectionError(f"{packet_path}: {source_label} is not a JSON object")
    return body


def _load_packet(packet_path: Path, expected_kind: str) -> dict[str, Any]:
    """Read one source packet, asserting it is the expected JSON-object kind.

    Raises SpineProjectionError on absence / unreadability / non-JSON / non-object
    / kind mismatch. (The CALLER decides whether to project at all by checking both
    declaration packets exist first — see ``declaration_packets_present``.)
    """

    body = _load_json_object(packet_path, source_label="projection source packet")
    if body.get("kind") != expected_kind:
        raise SpineProjectionError(
            f"{packet_path}: projection source packet kind {body.get('kind')!r} != "
            f"expected {expected_kind!r}"
        )
    return body


def _require_string(
    body: dict[str, Any],
    field: str,
    source_path: Path,
    *,
    allow_empty: bool = False,
) -> str:
    value = body.get(field)
    if not isinstance(value, str) or (not allow_empty and not value):
        raise SpineProjectionError(
            f"{source_path}: expected {'string' if allow_empty else 'non-empty string'} "
            f"{field!r}"
        )
    return value


def _require_string_list(body: dict[str, Any], field: str, source_path: Path) -> list[str]:
    value = body.get(field)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise SpineProjectionError(
            f"{source_path}: expected {field!r} to be a list of non-empty strings"
        )
    return list(value)


def _require_evidence_raw_ref(body: dict[str, Any], source_path: Path) -> str:
    """The stable raw evidence ref for this step's AgentReceipt, fail-closed.

    A step-output.json nests its evidence refs under ``evidence_refs`` (a JSON object
    carrying ``raw_ref`` — the at-time recorded raw stream entry for this receipt). The
    AgentReceipt's ``evidence_reference`` is that ``raw_ref``. FAIL-CLOSED (mirrors
    ``_require_string``): a real step-output always carries a JSON-object ``evidence_refs``
    with a non-empty string ``raw_ref`` (verified across every building's step-outputs),
    so an absent / non-object ``evidence_refs`` or a missing / non-string / empty
    ``raw_ref`` is a corrupt receipt source and RAISES. ``raw_ref`` is NOT a forbidden key.
    """

    evidence_refs = body.get("evidence_refs")
    if not isinstance(evidence_refs, dict):
        raise SpineProjectionError(
            f"{source_path}: expected JSON-object 'evidence_refs' carrying the receipt "
            "evidence ref"
        )
    raw_ref = evidence_refs.get("raw_ref")
    if not isinstance(raw_ref, str) or not raw_ref:
        raise SpineProjectionError(
            f"{source_path}: expected non-empty string 'evidence_refs.raw_ref' for the "
            "AgentReceipt evidence_reference"
        )
    return raw_ref


def _copy_required_fields(
    source: dict[str, Any],
    fields: tuple[str, ...],
    source_path: Path,
    body: dict[str, Any],
) -> None:
    for field in fields:
        if field not in source:
            raise SpineProjectionError(f"{source_path}: missing required field {field!r}")
        body[field] = source[field]


def _preset_expansion_event_body(packet: dict[str, Any]) -> dict[str, Any]:
    """Build the PresetExpansion ([Brick]) event body from the preset packet.

    Copies the mechanical preset/shape/template declaration fields verbatim (refs /
    enums / counts only). Absent fields are simply not copied (the writer + checkers
    do not require any of them — only event_type + non-empty axis_scope). No
    forbidden success/quality/fault key is ever added.
    """

    body: dict[str, Any] = {
        "event_type": _PRESET_EXPANSION_EVENT,
        "axis_scope": list(_PRESET_EXPANSION_AXIS_SCOPE),
    }
    for field in _PRESET_EXPANSION_FIELDS:
        if field in packet:
            body[field] = packet[field]
    return body


def _projected_launch_row(row: Any) -> dict[str, Any]:
    """Project one launch row: copy non-forbidden fields, RENAME the forbidden ones.

    A non-mapping row is a CORRUPT declaration packet -> RAISE SpineProjectionError
    (fail-closed). It is NOT laundered into a ``{"malformed_launch_row": repr(row)}``
    string marker: stringifying a degenerate row would HIDE any forbidden key
    (``movement`` / ``target_ref``) inside an opaque string, so the writer's
    recursive KEY-only forbidden-key scan would accept the corrupt packet. A
    malformed declaration packet must be REFUSED, not projected. For a mapping row
    the verbatim non-forbidden fields are copied and ``movement`` / ``target_ref``
    are copied under their non-forbidden rename, kept NESTED in the row.
    """

    if not isinstance(row, dict):
        raise SpineProjectionError(
            f"link_launch_policy launch_rows[] entry is not a JSON object "
            f"(corrupt declaration packet): {row!r}"
        )
    projected: dict[str, Any] = {}
    for field in _LAUNCH_ROW_VERBATIM_FIELDS:
        if field in row:
            projected[field] = row[field]
    for forbidden_key, renamed_key in _LAUNCH_ROW_RENAME.items():
        if forbidden_key in row:
            projected[renamed_key] = row[forbidden_key]
    return projected


def _link_launch_policy_event_body(packet: dict[str, Any]) -> dict[str, Any]:
    """Build the LinkLaunchPolicy ([Link]) event body from the link-policy packet.

    Copies the mechanical top-level declaration fields verbatim, then projects each
    ``launch_rows[]`` entry with its two forbidden keys renamed (kept nested). No
    forbidden success/quality/fault key is ever added; the only structural change
    from the raw packet is the per-row key rename.
    """

    body: dict[str, Any] = {
        "event_type": _LINK_LAUNCH_POLICY_EVENT,
        "axis_scope": list(_LINK_LAUNCH_POLICY_AXIS_SCOPE),
    }
    for field in _LINK_LAUNCH_POLICY_FIELDS:
        if field in packet:
            body[field] = packet[field]
    raw_rows = packet.get("launch_rows")
    if isinstance(raw_rows, list):
        body["launch_rows"] = [_projected_launch_row(row) for row in raw_rows]
    return body


def _task_source_event_body(packet: dict[str, Any], source_path: Path) -> dict[str, Any]:
    """Build the TaskSource ([Brick]) event body from the building-intake packet (ITEM 4).

    Copies the mechanical intake-provenance fields verbatim IF present (the task source
    ref + the proof_limits / not_proven lists + the declared plan_ref). FAIL-CLOSED: the
    ``task_source_ref`` KEY MUST exist (the packet builder always emits it, defaulting to
    "" when no task source ref was supplied — so an EMPTY string value is allowed; only an
    ABSENT key is a corrupt packet and RAISES). The intake envelope keys (kind /
    building_id / declared_by / composition_mode / selected_* / declaration_evidence_refs)
    are DELIBERATELY OMITTED. NO forbidden success/quality/fault key is ever added.
    """

    if _TASK_SOURCE_REQUIRED_FIELD not in packet:
        raise SpineProjectionError(
            f"{source_path}: building-intake packet is missing required field "
            f"{_TASK_SOURCE_REQUIRED_FIELD!r} for its TaskSource event body"
        )
    body: dict[str, Any] = {
        "event_type": _TASK_SOURCE_EVENT,
        "axis_scope": list(_TASK_SOURCE_AXIS_SCOPE),
    }
    for field in _TASK_SOURCE_FIELDS:
        if field in packet:
            body[field] = packet[field]
    return body


def _packet_path(building_root: Path, packet_name: str) -> Path:
    return building_root / "work" / packet_name


def declaration_packets_present(building_root: Path | str) -> bool:
    """True iff BOTH building-scope declaration packets exist as files on disk.

    The hook uses this to project ONLY for eligible buildings: a build that
    legitimately lacks the declaration packets is NOT forced into a u5_5_live spine
    + a failing projection. (See the module docstring for the increment-1 design
    decision: project only when both packets are present; if projection then RAISES,
    let it surface.)
    """

    root = Path(building_root)
    return (
        _packet_path(root, _PRESET_EXPANSION_PACKET).is_file()
        and _packet_path(root, _LINK_LAUNCH_POLICY_PACKET).is_file()
    )


def _resume_disposition_key(
    body: dict[str, Any],
) -> tuple[str, str, str, int] | None:
    """The (resumed_from, disposition_action, paused_at_ref, resume_ordinal) delta key.

    Reads the three string key fields plus the int ``resume_ordinal`` off an EXISTING
    ResumeDisposition event body on disk. Returns None iff any string key field is
    missing / non-string / empty OR ``resume_ordinal`` is missing / not an int (a
    malformed prior projection) — the caller RAISES on a None so the delta is never
    computed over a ResumeDisposition whose key cannot be read (which would let a resume
    append a duplicate, parity with the Link source_fact_ref fail-closed guard below).

    ``resume_ordinal`` is what makes two sentinel-colliding fan-in resumes distinct
    (F1): without it, two distinct fan-in resumes sharing a disposition_action would map
    to the SAME three-string key (both fall back to the reroute-hold sentinel for
    resumed_from + paused_at_ref) and the 2nd would be dropped at the delta.
    """

    parts: list[str] = []
    for field in _RESUME_DISPOSITION_KEY_FIELDS:
        value = body.get(field)
        if not isinstance(value, str) or not value:
            return None
        parts.append(value)
    ordinal = body.get(_RESUME_ORDINAL_FIELD)
    # bool is a subclass of int; a True/False ordinal is malformed, so reject it.
    if not isinstance(ordinal, int) or isinstance(ordinal, bool):
        return None
    return (parts[0], parts[1], parts[2], ordinal)


def _existing_projection_keys(
    building_root: Path,
) -> tuple[
    set[str],
    set[tuple[str, str]],
    set[tuple[str, str]],
    set[tuple[str, str, str, int]],
]:
    """Return existing declaration types, per-step, Link-fact, and resume keys.

    This is the resume-safe delta basis. It reads the four keys needed for
    idempotency:
      * building-scope ``event_type`` (the two once-per-building declarations PLUS
        the Frontier terminal event — all EVENT-TYPE-keyed exactly-one-per-building,
        see ``_BUILDING_SCOPE_EVENT_TYPE_KEYED``);
      * per-step ``(event_type, step_ref)`` for the Brick/Agent rows (BrickInput /
        AgentBinding / AgentReturn) — one of each per step, so (type, step) is a
        sufficient unique key;
      * per-Link-event ``(event_type, source_fact_ref)`` for the six Link events —
        a step may legitimately carry MULTIPLE of a Link type (multiple gates,
        present + absence), so the unique key is the SOURCE fact_ref, not (type,
        step). Re-projection then re-no-ops without duplicating NOR dropping.
      * per-ResumeDisposition
        ``(resumed_from, disposition_action, paused_at_ref, resume_ordinal)`` — a
        building may resume MULTIPLE times (zero-or-more ResumeDisposition), so the
        unique key is read off each existing ResumeDisposition BODY's own fields (not
        event_type, which would cap it at one). The int ``resume_ordinal`` (the
        observation's stable index in resume_observations) is part of the key so two
        DISTINCT fan-in resumes that collide on the three sentinel strings stay
        distinct (F1). Re-projection + a partial resume then re-no-ops the
        already-projected resumes and appends only new ones.
    A structurally dirty existing spine raises fail-closed instead of letting a
    no-op hide a torn append.
    """

    structural = spine_structural_violations(building_root, require_index_present=False)
    if structural:
        raise SpineProjectionError(
            f"{building_root}: existing spine is not structurally clean: {structural}"
        )
    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.exists():
        return set(), set(), set(), set()
    if not events_dir.is_dir():
        raise SpineProjectionError(f"{events_dir}: existing spine events path is not a directory")
    declarations: set[str] = set()
    per_step: set[tuple[str, str]] = set()
    link_per_fact: set[tuple[str, str]] = set()
    resume_dispositions: set[tuple[str, str, str, int]] = set()
    for event_path in sorted(events_dir.glob("*.json")):
        body = _load_json_object(event_path, source_label="existing spine event")
        event_type = body.get("event_type")
        if not isinstance(event_type, str) or not event_type:
            raise SpineProjectionError(f"{event_path}: existing spine event has no event_type")
        if event_type in _BUILDING_SCOPE_EVENT_TYPE_KEYED:
            declarations.add(event_type)
        if event_type == _RESUME_DISPOSITION_EVENT:
            # FAIL-CLOSED (parity with the Link source_fact_ref guard below): every
            # ResumeDisposition the projector writes carries its three string key fields
            # (resumed_from / disposition_action / paused_at_ref) PLUS the int
            # resume_ordinal (the F1 disambiguator). A ResumeDisposition ON DISK that
            # LACKS one is a malformed prior projection — without the full key the delta
            # scan could neither match nor dedupe it, so a resume could append a
            # duplicate and leave the malformed one behind. REJECT it (raise) rather
            # than silently ignoring it.
            key = _resume_disposition_key(body)
            if key is None:
                raise SpineProjectionError(
                    f"{event_path}: existing {event_type} spine event is missing a "
                    f"string key field {_RESUME_DISPOSITION_KEY_FIELDS!r} or an int "
                    f"{_RESUME_ORDINAL_FIELD!r} (malformed prior projection); refusing "
                    "to compute a delta over a malformed ResumeDisposition event"
                )
            resume_dispositions.add(key)
        step_ref = body.get("step_ref")
        if isinstance(step_ref, str) and step_ref:
            per_step.add((event_type, step_ref))
        if event_type in _PER_FACT_KEYED_EVENTS:
            source_fact_ref = body.get("source_fact_ref")
            # FAIL-CLOSED: every per-fact-keyed spine event the projector writes (the six
            # Link events + BrickCompared) carries its source_fact_ref (the delta key). A
            # per-fact-keyed event ON DISK that LACKS one is a malformed prior projection —
            # without the key the delta scan could neither match nor dedupe it, so a
            # resume could append a replacement and leave the orphan behind. REJECT it
            # (raise) rather than silently ignoring it (which is what would let the orphan
            # persist).
            if not isinstance(source_fact_ref, str) or not source_fact_ref:
                raise SpineProjectionError(
                    f"{event_path}: existing {event_type} spine event has no string "
                    "source_fact_ref (malformed prior projection); refusing to "
                    "compute a delta over a malformed per-fact-keyed event"
                )
            link_per_fact.add((event_type, source_fact_ref))
    return declarations, per_step, link_per_fact, resume_dispositions


def _executed_step_outputs(building_root: Path) -> list[dict[str, Any]]:
    """Executed steps from ``work/step-outputs/*/step-output.json``, deduped.

    The dedupe key is the string ``step_ref``. If the same step_ref appears again
    with the same ``brick_instance_ref`` (for example, a later attempt), the first
    sorted record is kept because the current req-a projection is per step_ref, not
    per attempt. A duplicate step_ref with a different Brick instance is corrupt
    source evidence and raises. Adapter-error-only attempt dirs have no AgentFact
    return and are frontier evidence, not executed-step projection sources.
    """

    step_outputs_dir = building_root / "work" / "step-outputs"
    if not step_outputs_dir.exists():
        return []
    if not step_outputs_dir.is_dir():
        raise SpineProjectionError(f"{step_outputs_dir}: step-outputs is not a directory")

    by_step: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []
    for step_dir in sorted(path for path in step_outputs_dir.iterdir() if path.is_dir()):
        output_path = step_dir / _STEP_OUTPUT_PACKET
        if not output_path.is_file():
            if (step_dir / "adapter-error.json").is_file():
                continue
            raise SpineProjectionError(
                f"{output_path}: step output packet unreadable: missing step-output.json"
            )
        body = _load_json_object(output_path, source_label="step output packet")
        step_ref = _require_string(body, "step_ref", output_path)
        brick_instance_ref = _require_string(body, "brick_instance_ref", output_path)
        record = {
            "source_path": output_path,
            "source_relpath": output_path.relative_to(building_root).as_posix(),
            "step_ref": step_ref,
            "brick_instance_ref": brick_instance_ref,
            "agent_object_ref": _require_string(body, "agent_object_ref", output_path),
            "returned_fact_ref": _require_string(body, "returned_fact_ref", output_path),
            # AgentReceipt coordinates (the agent "received the work" record), read
            # from the SAME step-output.json: the received-work ref + the stable raw
            # evidence ref for this receipt. FAIL-CLOSED (mirrors returned_fact_ref):
            # a real step-output always carries these (verified across every building),
            # so an executed step whose receipt source is missing/non-string RAISES.
            "received_work_ref": _require_string(body, "received_work_ref", output_path),
            "evidence_reference": _require_evidence_raw_ref(body, output_path),
            "observed_fields": _require_string_list(body, "agent_fact_fields", output_path),
            "step_output_ref": _require_string(body, "step_output_ref", output_path),
            "route_request_ref": _require_string(
                body,
                "route_request_ref",
                output_path,
                allow_empty=True,
            ),
        }
        existing = by_step.get(step_ref)
        if existing is not None:
            if existing["brick_instance_ref"] != brick_instance_ref:
                raise SpineProjectionError(
                    f"{output_path}: duplicate step_ref {step_ref!r} carries "
                    f"brick_instance_ref {brick_instance_ref!r}, already saw "
                    f"{existing['brick_instance_ref']!r}"
                )
            continue
        by_step[step_ref] = record
        ordered.append(record)
    # Guard the per-step Link JOIN against SLUG collisions: the claim_trace fact_ref
    # suffix is the SLUGGED step_ref (':' -> '-' via _step_ref_slug), so two DISTINCT
    # executed step_refs that slug to the SAME suffix (e.g. "a:x" and "a-x") would
    # cross-attribute each other's Link facts (and false-green req-e). Real step_refs
    # are colon-free so this never collides today; assert it so a future colon-bearing
    # step_ref fails CLOSED instead of silently mis-joining.
    slug_owner: dict[str, str] = {}
    for record in ordered:
        slug = _step_ref_slug(record["step_ref"])
        prior = slug_owner.get(slug)
        if prior is not None and prior != record["step_ref"]:
            raise SpineProjectionError(
                f"{building_root}: executed step_refs {prior!r} and "
                f"{record['step_ref']!r} slug to the same fact_ref suffix {slug!r}; "
                "the per-step Link join would be ambiguous"
            )
        slug_owner[slug] = record["step_ref"]
    return ordered


def _declared_plan_steps(building_root: Path) -> list[Any]:
    packet = _latest_declared_plan_packet(building_root)
    declared_plan = packet.get("declared_plan_copy")
    if not isinstance(declared_plan, dict):
        raise SpineProjectionError(
            f"{_packet_path(building_root, _DECLARED_BUILDING_PLAN_PACKET)}: "
            "declared_plan_copy is not a JSON object"
        )
    steps = declared_plan.get("steps")
    if not isinstance(steps, list):
        # Graph Building declarations use brick_steps for the same Brick/Agent
        # row shape. Linear/preset declarations keep steps[]. Supporting both
        # source shapes keeps the projector closed over admitted Building plans
        # while still emitting the same narrow BrickInput body.
        steps = declared_plan.get("brick_steps")
    if not isinstance(steps, list):
        raise SpineProjectionError(
            f"{_packet_path(building_root, _DECLARED_BUILDING_PLAN_PACKET)}: "
            "declared_plan_copy.steps/brick_steps is not a JSON list"
        )
    return steps


def _latest_declared_plan_packet(building_root: Path) -> dict[str, Any]:
    try:
        packet = latest_valid_declared_plan_packet(building_root)
    except ValueError as exc:
        raise SpineProjectionError(f"{building_root}: latest declared plan packet is invalid: {exc}") from exc
    if not isinstance(packet, dict):
        raise SpineProjectionError(f"{building_root}: latest declared plan packet is not a JSON object")
    return packet


def _declared_link_edges(building_root: Path) -> list[Any]:
    """The declared graph ``link_edges`` (``declared_plan_copy.link_edges``) or [].

    GUARD #6c (graph): a GRAPH plan's Link rows — including any ``gate_sequence_policy`` —
    live under ``link_edges`` (each edge carries a Link ``rows[]`` keyed by
    ``source_step_ref``), NOT under ``brick_steps[].rows``. The gate-sequence-coverage
    guard reads these to demand gate events for a graph edge's SOURCE step (plan_graph
    linearizes the edge's Link row onto its source step at run). Reads the SAME
    declared-building-plan packet ``_declared_plan_steps`` reads. Returns the list, or []
    when the key is ABSENT (a linear plan has no link_edges); RAISES on a present-but-non-
    list link_edges (a torn declaration) — fail closed.
    """

    packet = _latest_declared_plan_packet(building_root)
    declared_plan = packet.get("declared_plan_copy")
    if not isinstance(declared_plan, dict):
        raise SpineProjectionError(
            f"{_packet_path(building_root, _DECLARED_BUILDING_PLAN_PACKET)}: "
            "declared_plan_copy is not a JSON object"
        )
    edges = declared_plan.get("link_edges")
    if edges is None:
        return []
    if not isinstance(edges, list):
        raise SpineProjectionError(
            f"{_packet_path(building_root, _DECLARED_BUILDING_PLAN_PACKET)}: "
            "declared_plan_copy.link_edges is present but not a JSON list"
        )
    return edges


def _declared_execution_order(building_root: Path) -> list[str] | None:
    """The graph runtime WALK order (``declared_plan_copy.execution_order``) or None.

    FIX P1#1: a GRAPH plan's runtime walk order is ``execution_order`` (plan_graph walks
    it EXACTLY); the declared ``brick_steps[]`` LIST order is NOT guaranteed to equal it.
    So per-step events must be sorted by ``execution_order`` WHEN PRESENT, falling back to
    the steps[] list position (linear/preset shapes, where execution_order is absent or
    already equals the list order). This reads the SAME declared-building-plan packet
    ``_declared_plan_steps`` reads.

    Returns the execution_order list iff it is a NON-EMPTY list of non-empty strings.
    Returns None when the key is ABSENT or an empty list (no graph walk order to honor —
    the caller falls back to steps[] position). RAISES SpineProjectionError when the key is
    PRESENT but malformed (not a list, or any entry not a non-empty string) — fail closed on
    a torn declaration rather than silently recording the wrong sequence.
    """

    packet = _latest_declared_plan_packet(building_root)
    declared_plan = packet.get("declared_plan_copy")
    if not isinstance(declared_plan, dict):
        raise SpineProjectionError(
            f"{_packet_path(building_root, _DECLARED_BUILDING_PLAN_PACKET)}: "
            "declared_plan_copy is not a JSON object"
        )
    if "execution_order" not in declared_plan:
        return None
    execution_order = declared_plan.get("execution_order")
    if execution_order == []:
        return None
    if not isinstance(execution_order, list):
        raise SpineProjectionError(
            f"{_packet_path(building_root, _DECLARED_BUILDING_PLAN_PACKET)}: "
            "declared_plan_copy.execution_order is present but not a JSON list"
        )
    for position, entry in enumerate(execution_order):
        if not isinstance(entry, str) or not entry:
            raise SpineProjectionError(
                f"{_packet_path(building_root, _DECLARED_BUILDING_PLAN_PACKET)}: "
                f"declared_plan_copy.execution_order[{position}] is not a non-empty string"
            )
    return execution_order


def _building_map_agent_bindings(building_root: Path) -> list[Any]:
    packet = _load_packet(
        _packet_path(building_root, _BUILDING_MAP_PACKET),
        _BUILDING_MAP_KIND,
    )
    bindings = packet.get("agent_bindings")
    if not isinstance(bindings, list):
        raise SpineProjectionError(
            f"{_packet_path(building_root, _BUILDING_MAP_PACKET)}: "
            "agent_bindings is not a JSON list"
        )
    return bindings


def _declared_step_refs(declared_steps: list[Any]) -> set[str]:
    """Return declared non-empty step refs without validating unrelated rows."""

    refs: set[str] = set()
    for step in declared_steps:
        if not isinstance(step, dict):
            continue
        step_ref = step.get("step_ref")
        if isinstance(step_ref, str) and step_ref:
            refs.add(step_ref)
    return refs


def _ordered_by_declared_plan(
    step_records: list[dict[str, Any]],
    declared_steps: list[Any],
    execution_order: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Stable-sort executed step records into declared CAUSAL order.

    The spine records the JUDGMENT SEQUENCE per building: the append order IS the
    sequence_index (append_spine_events assigns sequence_index in input-list order).
    The executed step-output dirs are enumerated ALPHABETICALLY by dir name (see
    ``_executed_step_outputs``), which is NOT the order the steps actually ran — so
    without this re-order the recorded sequence is alphabetical, not causal.

    FIX P1#1: the authoritative causal source is the GRAPH runtime walk order
    ``execution_order`` (plan_graph walks it EXACTLY); the declared ``steps[]`` /
    ``brick_steps[]`` LIST order is NOT guaranteed to equal it for a graph plan. So when
    ``execution_order`` is PRESENT (a non-empty list, from ``_declared_execution_order``)
    the position map is built from it (first-occurrence index of each step_ref); ELSE it
    falls back to the declared steps[] list position (the linear/preset case, where
    execution_order is absent or already equals the list order). Both shapes record the
    correct sequence.

    The SAME dict objects are reordered (``sorted`` returns the same objects), so any
    references already built over these records (e.g. ``missing_per_step``, matched by
    identity with ``is``) remain valid.

    An ORPHAN executed step (a step_ref in NEITHER ordering source) keeps its existing
    relative order and sorts AFTER all ordered steps — it is filtered from per-step
    emission anyway (orphan-skip discipline), this only pins its otherwise-undefined
    slot deterministically.
    """

    position: dict[str, int] = {}
    if execution_order is not None:
        for index, step_ref in enumerate(execution_order):
            if step_ref not in position:
                position[step_ref] = index
        # FIX P1#3: a PRESENT execution_order is the authoritative walk order, so it MUST
        # cover every DECLARED step (graph law: every brick step appears in execution_order
        # exactly once; a linear execution_order equals steps[]). A declared step ABSENT
        # from execution_order would silently sort to the sentinel tail = a WRONG recorded
        # sequence — fail closed instead. (Duplicate / extra entries are harmless and are
        # NOT rejected: first-occurrence indexes the order, an unmatched entry simply indexes
        # no record, and a linear reroute is recorded via attempt DIRS, not repeated
        # execution_order entries — so a coverage check does not false-close a reroute plan.)
        missing = sorted(_declared_step_refs(declared_steps) - set(execution_order))
        if missing:
            raise SpineProjectionError(
                "declared_plan_copy.execution_order is present but does not cover declared "
                f"step_ref(s) {missing!r}; the recorded judgment sequence would be wrong"
            )
        sentinel = len(execution_order)
    else:
        for index, step in enumerate(declared_steps):
            if isinstance(step, dict):
                step_ref = step.get("step_ref")
                if isinstance(step_ref, str) and step_ref and step_ref not in position:
                    position[step_ref] = index
        sentinel = len(declared_steps)
    return sorted(step_records, key=lambda r: position.get(r["step_ref"], sentinel))


def _brick_row_for_step(
    declared_steps: list[Any],
    step_record: dict[str, Any],
    source_path: Path,
) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for index, step in enumerate(declared_steps):
        if not isinstance(step, dict) or step.get("step_ref") != step_record["step_ref"]:
            continue
        rows = step.get("rows")
        if not isinstance(rows, list):
            raise SpineProjectionError(f"{source_path}: steps[{index}].rows is not a JSON list")
        for row_index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise SpineProjectionError(
                    f"{source_path}: steps[{index}].rows[{row_index}] is not a JSON object"
                )
            if (
                row.get("axis") == "Brick"
                and row.get("brick_instance_ref") == step_record["brick_instance_ref"]
            ):
                matches.append(row)
    if not matches and step_record["step_ref"] not in _declared_step_refs(declared_steps):
        return None
    if len(matches) != 1:
        raise SpineProjectionError(
            f"{source_path}: expected exactly one Brick row for step_ref "
            f"{step_record['step_ref']!r} and brick_instance_ref "
            f"{step_record['brick_instance_ref']!r}; found {len(matches)}"
        )
    return matches[0]


def _agent_binding_for_step(
    agent_bindings: list[Any],
    declared_steps: list[Any],
    step_record: dict[str, Any],
    source_path: Path,
) -> dict[str, Any] | None:
    accepted_output_refs = {
        step_record["source_relpath"],
        step_record["step_output_ref"],
    }
    matches: list[dict[str, Any]] = []
    for index, binding in enumerate(agent_bindings):
        if not isinstance(binding, dict):
            raise SpineProjectionError(
                f"{source_path}: agent_bindings[{index}] is not a JSON object"
            )
        if (
            binding.get("brick_instance_ref") == step_record["brick_instance_ref"]
            and binding.get("step_output_ref") in accepted_output_refs
        ):
            matches.append(binding)
    # ORPHAN-SKIP (parity with _brick_row_for_step): a step-output dir whose
    # step_ref is NOT in ANY declared step is a genuine orphan — SKIP it (return
    # None) so it does not crash the whole projection. Keep RAISING only when the
    # step_ref DOES match a declared step but the binding row is missing/duplicate
    # (a real bug — defensive).
    if not matches and step_record["step_ref"] not in _declared_step_refs(declared_steps):
        return None
    if len(matches) != 1:
        raise SpineProjectionError(
            f"{source_path}: expected exactly one agent_binding for step_ref "
            f"{step_record['step_ref']!r}, brick_instance_ref "
            f"{step_record['brick_instance_ref']!r}, and step_output_ref in "
            f"{sorted(accepted_output_refs)!r}; found {len(matches)}"
        )
    return matches[0]


def _brick_input_event_body(
    declared_steps: list[Any],
    step_record: dict[str, Any],
    source_path: Path,
) -> dict[str, Any] | None:
    brick_row = _brick_row_for_step(declared_steps, step_record, source_path)
    if brick_row is None:
        return None
    body: dict[str, Any] = {
        "event_type": _BRICK_INPUT_EVENT,
        "axis_scope": list(_BRICK_INPUT_AXIS_SCOPE),
        "step_ref": step_record["step_ref"],
        "brick_instance_ref": step_record["brick_instance_ref"],
    }
    _copy_required_fields(brick_row, _BRICK_INPUT_FIELDS, source_path, body)
    if "source_facts" in brick_row:
        body["source_facts"] = brick_row["source_facts"]
    return body


def _agent_binding_event_body(
    agent_bindings: list[Any],
    declared_steps: list[Any],
    step_record: dict[str, Any],
    source_path: Path,
) -> dict[str, Any] | None:
    binding = _agent_binding_for_step(
        agent_bindings, declared_steps, step_record, source_path
    )
    if binding is None:
        return None
    body: dict[str, Any] = {
        "event_type": _AGENT_BINDING_EVENT,
        "axis_scope": list(_AGENT_BINDING_AXIS_SCOPE),
        "step_ref": step_record["step_ref"],
        "agent_object_ref": step_record["agent_object_ref"],
    }
    _copy_required_fields(binding, _AGENT_BINDING_FIELDS, source_path, body)
    return body


def _agent_receipt_event_body(step_record: dict[str, Any]) -> dict[str, Any]:
    """AgentReceipt ([Agent]) — the agent "received the work" record per step.

    The MIDDLE Agent-row event (AgentBinding -> AgentReceipt -> AgentReturn), built
    from the SAME ``step_record`` (step-output.json) AgentReturn reads, so it correlates
    to its step by the SAME (event_type, step_ref) key. ``source_fact_ref`` cites the
    closed AgentFact ref (``agent-fact:NN:step`` — the SAME fact AgentReturn cites as
    ``returned_fact_ref``); that fact carries the closed ``AgentFact(received_work,
    returned)``, so it is the stable per-step handle for the receipt. ``received_work_ref``
    is the work the agent received; ``evidence_reference`` is the receipt's raw evidence
    ref. Mechanical refs ONLY (no timestamp, no returned blob); NO forbidden key.
    """

    return {
        "event_type": _AGENT_RECEIPT_EVENT,
        "axis_scope": list(_AGENT_RECEIPT_AXIS_SCOPE),
        "step_ref": step_record["step_ref"],
        "brick_instance_ref": step_record["brick_instance_ref"],
        "agent_object_ref": step_record["agent_object_ref"],
        "source_fact_ref": step_record["returned_fact_ref"],
        "received_work_ref": step_record["received_work_ref"],
        "evidence_reference": step_record["evidence_reference"],
    }


def _agent_return_event_body(step_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": _AGENT_RETURN_EVENT,
        "axis_scope": list(_AGENT_RETURN_AXIS_SCOPE),
        "step_ref": step_record["step_ref"],
        "brick_instance_ref": step_record["brick_instance_ref"],
        "agent_object_ref": step_record["agent_object_ref"],
        "returned_fact_ref": step_record["returned_fact_ref"],
        "observed_fields": list(step_record["observed_fields"]),
        "step_output_ref": step_record["step_output_ref"],
        "route_request_ref": step_record["route_request_ref"],
    }


# ---------------------------------------------------------------------------
# TERMINAL building-scope events (slice-3 INC-2): Frontier (exactly one, COMPUTED
# from observe_building_frontier) + ResumeDisposition (zero-or-more, READ from the
# on-disk evidence-manifest plan_snapshot's resume_observations). Both record FACTS
# and JUDGE NOTHING (no success / quality / movement authority). Emitted ONCE per
# building, AFTER all per-step events.
# ---------------------------------------------------------------------------


def _frontier_event_body(building_root: Path) -> dict[str, Any]:
    """Build the Frontier ([Link]) event body — COMPUTED, not read from a trace.

    Calls the operator-observer ``observe_building_frontier(building_root)`` (a static
    read over already-written evidence that ALWAYS returns a frontier_kind and NEVER
    raises) and COPIES the five frontier FACT fields (frontier_kind / frontier_reason
    / observed_counts / proof_limits / not_proven) verbatim into the body. The
    projector records the observer's computed fact; it does NOT re-derive the frontier
    and judges nothing.

    FAIL-CLOSED single-source guard: the observed frontier_kind MUST be in the
    operator-observer's single-source FRONTIER_KINDS (it always is — the observer
    assigns only those literals); a value outside it would be an observer/guard drift,
    so we RAISE rather than project an unadmitted frontier_kind (it would fail the
    committed INC-2 guard anyway — fail loud here with a clear message).
    """

    observation = observe_building_frontier(building_root)
    frontier_kind = observation.get("frontier_kind")
    if not isinstance(frontier_kind, str) or frontier_kind not in FRONTIER_KINDS:
        raise SpineProjectionError(
            f"{building_root}: observe_building_frontier returned frontier_kind "
            f"{frontier_kind!r} not in single-source FRONTIER_KINDS {FRONTIER_KINDS!r}"
        )
    body: dict[str, Any] = {
        "event_type": _FRONTIER_EVENT,
        "axis_scope": list(_FRONTIER_AXIS_SCOPE),
    }
    for field in _FRONTIER_FIELDS:
        if field not in observation:
            raise SpineProjectionError(
                f"{building_root}: observe_building_frontier return is missing required "
                f"frontier field {field!r}"
            )
        body[field] = observation[field]
    return body


def _resume_observations(building_root: Path) -> list[dict[str, Any]]:
    """The on-disk resume observations for one building, fail-closed.

    SOURCE: ``evidence/evidence-manifest.json`` -> ``plan_snapshot.plan_rows_copy``
    (a JSON STRING of the walked plan) -> ``dynamic_walker_evidence`` ->
    ``resume_observations`` (a list). Returns the list of observation objects (each a
    JSON object). VACUOUS (returns ``[]``, NOT an error) when the resume context is
    legitimately absent: no manifest / no plan_snapshot / no plan_rows_copy / no
    dynamic_walker_evidence KEY / no resume_observations key — a building that never
    paused + resumed simply has no ResumeDisposition.

    FAIL-CLOSED for a building whose resume data is PRESENT-but-CORRUPT: an unparseable
    / non-object ``plan_rows_copy`` RAISEs (a torn manifest snapshot — the same
    fail-closed discipline the rest of the file uses: a present-but-corrupt source
    surfaces loudly, never silently skipped); a ``dynamic_walker_evidence`` that is
    PRESENT but NOT a JSON object RAISEs (F2 — a present-but-torn dwe is corrupt, NOT
    vacuous); and a ``resume_observations`` that is present-but-non-list (or carries a
    non-object entry) RAISEs. A genuinely ABSENT key is vacuous; a present-but-malformed
    one is a RAISE.
    """

    manifest_path = building_root / "evidence" / "evidence-manifest.json"
    if not manifest_path.is_file():
        return []
    manifest = _load_json_object(manifest_path, source_label="evidence manifest")
    snapshot = manifest.get("plan_snapshot")
    if not isinstance(snapshot, dict):
        # No plan_snapshot at all => no dynamic-walker context => vacuous (the 124
        # non-dynamic buildings take this branch — they never paused/resumed).
        return []
    plan_rows_copy = snapshot.get("plan_rows_copy")
    if plan_rows_copy is None or (isinstance(plan_rows_copy, str) and not plan_rows_copy):
        # Absent / empty snapshot copy => no dynamic-walker context => vacuous.
        return []
    if not isinstance(plan_rows_copy, str):
        # Present but the WRONG TYPE (not a JSON string) — a torn manifest snapshot.
        raise SpineProjectionError(
            f"{manifest_path}: plan_snapshot.plan_rows_copy is present but is not a "
            "JSON string (corrupt manifest snapshot)"
        )
    try:
        plan = json.loads(plan_rows_copy)
    except json.JSONDecodeError as exc:
        # Present-but-unparseable plan_rows_copy is a torn manifest snapshot for a
        # dynamic-walker building -> RAISE (fail-closed; same discipline as the rest
        # of the file's loaders, which never silently swallow corrupt JSON).
        raise SpineProjectionError(
            f"{manifest_path}: plan_snapshot.plan_rows_copy is present but is not JSON "
            f"(corrupt manifest snapshot): {exc}"
        ) from exc
    if not isinstance(plan, dict):
        raise SpineProjectionError(
            f"{manifest_path}: plan_snapshot.plan_rows_copy did not decode to a JSON "
            "object (corrupt manifest snapshot)"
        )
    if "dynamic_walker_evidence" not in plan:
        # ABSENT dynamic_walker_evidence => NOT a dynamic-walker building => vacuous:
        # this building never paused/resumed, so it imposes no ResumeDisposition + no
        # fail-closed requirement on its (absent) resume_observations.
        return []
    dynamic_walker_evidence = plan.get("dynamic_walker_evidence")
    if not isinstance(dynamic_walker_evidence, dict):
        # PRESENT-but-non-dict dynamic_walker_evidence is a TORN snapshot for what is
        # declared to be a dynamic-walker building -> RAISE (F2 fix; parity with the
        # other fail-closed cases above — a present-but-corrupt source surfaces loudly,
        # never silently zeroed). Absent dwe (handled above) stays vacuous.
        raise SpineProjectionError(
            f"{manifest_path}: plan_snapshot.plan_rows_copy.dynamic_walker_evidence is "
            "present but is not a JSON object (corrupt resume evidence)"
        )
    resume_observations = dynamic_walker_evidence.get("resume_observations")
    if resume_observations is None:
        # dynamic-walker building that simply did not resume => vacuous.
        return []
    if not isinstance(resume_observations, list):
        # PRESENT-but-non-list for a dynamic-walker building => corrupt => RAISE.
        raise SpineProjectionError(
            f"{manifest_path}: dynamic_walker_evidence.resume_observations is present "
            "but is not a JSON list (corrupt resume evidence)"
        )
    observations: list[dict[str, Any]] = []
    for position, observation in enumerate(resume_observations):
        if not isinstance(observation, dict):
            raise SpineProjectionError(
                f"{manifest_path}: dynamic_walker_evidence.resume_observations"
                f"[{position}] is not a JSON object (corrupt resume evidence)"
            )
        observations.append(observation)
    return observations


def _resume_disposition_event_body(
    observation: dict[str, Any],
    resume_ordinal: int,
    source_path: Path,
) -> dict[str, Any]:
    """Build one ResumeDisposition ([Link]) event body from a resume_observation.

    Copies the mechanical resume FACT fields verbatim (refs / an enum / counts / the
    proof_limits / not_proven lists) and stamps ``resume_ordinal`` = the observation's
    0-based index in dynamic_walker_evidence.resume_observations (the F1 disambiguator
    so two sentinel-colliding fan-in resumes stay distinct at the delta). REQUIRES the
    load-bearing fields present (mirror the ``_require_present_fields`` fail-closed
    pattern — a sparse observation RAISEs, not a sparse event). ``disposition_action``
    is enum-checked against Link's single-source DISPOSITION_ACTIONS; a value outside it
    is corrupt resume evidence and RAISEs (it would fail the committed INC-2 guard
    anyway). No forbidden success/quality/fault/movement/target KEY is ever added (the
    field names — including the int ``resume_ordinal`` — are all forbidden-key-SAFE).
    """

    for field in _RESUME_DISPOSITION_REQUIRED:
        if field not in observation:
            raise SpineProjectionError(
                f"{source_path}: resume_observation is missing required field "
                f"{field!r} for its ResumeDisposition event body (malformed/sparse "
                "resume observation)"
            )
    disposition_action = observation.get("disposition_action")
    if (
        not isinstance(disposition_action, str)
        or disposition_action not in DISPOSITION_ACTIONS
    ):
        raise SpineProjectionError(
            f"{source_path}: resume_observation disposition_action "
            f"{disposition_action!r} is not one of single-source "
            f"DISPOSITION_ACTIONS {DISPOSITION_ACTIONS!r}"
        )
    body: dict[str, Any] = {
        "event_type": _RESUME_DISPOSITION_EVENT,
        "axis_scope": list(_RESUME_DISPOSITION_AXIS_SCOPE),
    }
    for field in _RESUME_DISPOSITION_FIELDS:
        body[field] = observation[field]
    body[_RESUME_ORDINAL_FIELD] = resume_ordinal
    return body


# ---------------------------------------------------------------------------
# PER-STEP LINK EVENTS — read the on-disk claim_trace/link/*.json (at-time facts).
# ---------------------------------------------------------------------------


# slice-3 A+ ITEM 2: the Brick claim_trace file BrickCompared projects from. A real
# u5_5_live building with executed steps always carries it (the support observer writes
# one brick-comparison fact per attempt); an ABSENT file with executed declared steps is
# a torn source and RAISES (required) so a dropped BrickCompared cannot false-green.
_BRICK_WORK_CONTRACT_TRACE = "work_contract.json"
_BRICK_COMPARISON_FACT_PREFIX = "brick-comparison:"
# The forward-path writer (claims_brick.py) emits TWO brick-comparison facts per step:
# the canonical ``brick-comparison:NN:step`` AND a building-scoped ALIAS
# ``brick-comparison:{building_id}:step`` carrying an ``alias_for`` pointer back to the
# canonical fact_ref. Both share the ``:slug(step_ref)`` suffix, so the per-step suffix
# join would pull BOTH and emit TWO BrickCompared events per attempt — DOUBLE-recording
# the SAME comparison observation (the truth layer must record each observation ONCE; an
# alias is a pointer, not a distinct per-attempt observation). The alias is cleanly
# self-identifying via this inner-body marker, so the loader SKIPS it; only the canonical
# observation projects to a BrickCompared event.
_BRICK_COMPARISON_ALIAS_MARKER = "alias_for"


def _brick_trace_path(building_root: Path, trace_name: str) -> Path:
    return building_root / "evidence" / "claim_trace" / "brick" / trace_name


def _link_trace_path(building_root: Path, trace_name: str) -> Path:
    return building_root / "evidence" / "claim_trace" / "link" / trace_name


def _load_brick_comparison_facts(
    building_root: Path,
    *,
    required: bool,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]] | None:
    """Load the brick-comparison facts from claim_trace/brick/work_contract.json (ITEM 2).

    The brick work_contract holds BOTH ``brick-work:NN:step`` and
    ``brick-comparison:NN:step`` facts; this returns ONLY the brick-comparison facts (the
    Brick-axis MATCH observations BrickCompared projects from). FAIL-CLOSED, mirroring
    ``_load_link_trace_facts``: a PRESENT file that is unreadable / non-JSON / not a JSON
    object / has a non-list ``facts`` / a non-object fact / a fact missing a non-empty
    string ``fact_ref`` RAISES (a corrupt trace surfaces loudly). ``required=True`` RAISES
    on absence (a u5_5_live building with declared executed steps must carry it);
    ``required=False`` lets a genuinely ABSENT file return None. A present-but-corrupt file
    ALWAYS raises regardless of ``required``.

    Returns ``(canonical_facts, alias_map)`` (or None for an absent non-required file):
      * ``canonical_facts`` is the list of CANONICAL brick-comparison facts (the ALIAS
        facts, which carry an inner ``alias_for`` pointer, are SKIPPED so the SAME
        comparison observation is not double-recorded as a second BrickCompared event —
        only the canonical observation projects).
      * ``alias_map`` (F1) maps each CANONICAL fact_ref to the list of ALIAS fact_refs that
        point at it (every brick-comparison fact whose inner ``alias_for`` equals that
        canonical fact_ref). The forward-path writer emits a building-scoped alias
        ``brick-comparison:{building_id}:step`` whose ``alias_for`` is the canonical
        ``brick-comparison:NN:step``; OTHER events (e.g. LinkSufficiency.checked_public_fact)
        faithfully cite the ALIAS ref, so the projected canonical BrickCompared event must
        record its alias refs (in ``alias_fact_refs``) for those citations to be RESOLVABLE
        without projecting a duplicate event for the alias.
    """

    path = _brick_trace_path(building_root, _BRICK_WORK_CONTRACT_TRACE)
    if not path.exists():
        if required:
            raise SpineProjectionError(f"{path}: required Brick claim_trace is absent")
        return None
    envelope = _load_json_object(path, source_label="Brick claim_trace")
    raw_facts = envelope.get("facts")
    if not isinstance(raw_facts, list):
        raise SpineProjectionError(f"{path}: Brick claim_trace 'facts' is not a JSON list")
    facts: list[dict[str, Any]] = []
    # F1: collect each canonical fact_ref's alias refs in ONE pass over the same facts.
    alias_map: dict[str, list[str]] = {}
    for position, fact in enumerate(raw_facts):
        if not isinstance(fact, dict):
            raise SpineProjectionError(
                f"{path}: Brick claim_trace facts[{position}] is not a JSON object"
            )
        fact_ref = fact.get("fact_ref")
        if not isinstance(fact_ref, str) or not fact_ref:
            raise SpineProjectionError(
                f"{path}: Brick claim_trace facts[{position}] has no string fact_ref"
            )
        if not fact_ref.startswith(_BRICK_COMPARISON_FACT_PREFIX):
            continue
        # Skip the ALIAS comparison fact (carries an inner ``alias_for`` pointer to the
        # canonical fact) so the SAME comparison observation is not double-recorded as a
        # second BrickCompared event. Only the canonical observation projects — BUT record
        # the alias's own fact_ref against the canonical it points at (F1) so a citation of
        # the alias ref resolves to the canonical BrickCompared event.
        inner = fact.get("fact")
        if isinstance(inner, dict) and _BRICK_COMPARISON_ALIAS_MARKER in inner:
            alias_for = inner.get(_BRICK_COMPARISON_ALIAS_MARKER)
            if isinstance(alias_for, str) and alias_for:
                alias_map.setdefault(alias_for, []).append(fact_ref)
            continue
        facts.append(fact)
    return facts, alias_map


def _brick_compared_event_body(
    fact: dict[str, Any],
    alias_fact_refs: list[str],
) -> dict[str, Any]:
    """BrickCompared ([Brick]) from one brick-comparison claim_trace fact (ITEM 2).

    Copies the mechanical comparison fields verbatim (observed_match_kind /
    comparison_rule / comparison_observation / work_reference + the *_evidence list
    fields if present). FAIL-CLOSED: a real brick-comparison fact ALWAYS carries
    observed_match_kind + comparison_rule, so a fact missing either is a corrupt source
    and RAISES (not a sparse event). observed_match_kind / comparison_rule are open
    support-returned strings — NOT an enum (no enum is invented). The source fact_ref is
    carried verbatim as ``source_fact_ref`` (the delta key). NO forbidden KEY is added —
    ``comparison_observation`` may carry the phrase "not success judgment" in its VALUE,
    which is allowed (the forbidden rule is KEY-only).

    F1: ``alias_fact_refs`` is the list of ALIAS brick-comparison fact_refs that point at
    THIS canonical fact (every alias whose inner ``alias_for`` equals this canonical's
    fact_ref), recorded on the body as ``alias_fact_refs`` (``[]`` when none). It makes a
    citation of an alias ref (e.g. LinkSufficiency.checked_public_fact, which cites the
    building-scoped alias) RESOLVABLE to this single canonical BrickCompared event — by
    its ``source_fact_ref`` OR by an entry in ``alias_fact_refs`` — WITHOUT projecting a
    duplicate event for the alias. It is forbidden-key-safe (it carries only refs).
    """

    inner = _fact_inner_body(fact, _BRICK_WORK_CONTRACT_TRACE)
    _require_present_fields(
        inner, _BRICK_COMPARED_REQUIRED_FIELDS, fact["fact_ref"], _BRICK_WORK_CONTRACT_TRACE
    )
    body: dict[str, Any] = {
        "event_type": _BRICK_COMPARED_EVENT,
        "axis_scope": list(_BRICK_COMPARED_AXIS_SCOPE),
        "source_fact_ref": fact["fact_ref"],
        # F1: stable, deduped-into-a-list alias refs (sorted for determinism). Always a
        # list (empty when the canonical carries no alias) so a consumer/guard can always
        # read it. Refs only — forbidden-key-safe.
        "alias_fact_refs": sorted(set(alias_fact_refs)),
    }
    _copy_present_fields(inner, _BRICK_COMPARED_FIELDS, body)
    return body


# ---------------------------------------------------------------------------
# AGENT->LINK SEAM EVENTS (slice-3 A+ part 2 ITEM 1): TransitionConcern / RouteRequest
# read from the on-disk work/step-outputs/<step>-attempt-N/{transition-concern,
# route-request}.json files step_outputs.write_step_output wrote ONLY when the Agent
# raised one (mutually exclusive per attempt). PRESENT-WHEN-RAISED: zero-or-more per
# step; no presence requirement. The projector READS these files (NOT a re-run /
# re-derivation) and records the at-time Agent return. fail-closed on a present-but-
# corrupt file.
# ---------------------------------------------------------------------------


def _seam_event_body(
    seam_file: dict[str, Any],
    source_path: Path,
    *,
    event_type: str,
    axis_scope: list[str],
    ref_field: str,
    toplevel_fields: tuple[str, ...],
    returned_field: str,
    alias_inner_ref_field: str | None,
) -> tuple[str, str, dict[str, Any]]:
    """Build one (event_type, source_fact_ref, body) seam spec from a seam file.

    The seam file's own ref field (``transition_concern_ref`` / ``route_request_ref``) is
    the SOURCE fact_ref + delta key (REQUIRED — a file lacking it is corrupt source and
    RAISES). The mechanical top-level coordinates (step_ref / agent_object_ref / binding /
    attempt_index / step_output_ref) are copied verbatim IF present, and the NESTED
    Agent-returned blob (``transition_concern_returned`` / ``route_request_returned``) is
    carried verbatim under its own key (already validated forbidden-clean at WRITE time, so
    copying it adds no forbidden key — re-scanned by the writer regardless). NO judgment
    field is added.

    ``alias_inner_ref_field`` (TransitionConcern only): the inner handle inside the returned
    blob (``concern_ref``) a Movement's adopted/not_adopted refs cite. It is recorded in
    ``alias_fact_refs`` (mirrors the BrickCompared alias mechanism) so a Movement that cites
    the Agent's OWN concern_ref resolves to this TransitionConcern event by alias (req-f 3c).
    None for RouteRequest (movement facts cite a route_request_ref directly, which is the
    source_fact_ref). ``alias_fact_refs`` is ALWAYS a list (``[]`` when none).
    """

    source_fact_ref = _require_string(seam_file, ref_field, source_path)
    body: dict[str, Any] = {
        "event_type": event_type,
        "axis_scope": list(axis_scope),
        "source_fact_ref": source_fact_ref,
    }
    _copy_present_fields(seam_file, toplevel_fields, body)
    # The nested Agent-returned blob (REQUIRED — a seam file always carries it; a file that
    # lacks it is corrupt source and RAISES, not a sparse event). Carried verbatim.
    returned = seam_file.get(returned_field)
    if not isinstance(returned, dict):
        raise SpineProjectionError(
            f"{source_path}: seam file is missing required JSON-object {returned_field!r}"
        )
    body[returned_field] = returned
    # F1-style alias: the inner concern_ref a Movement's adopted/not_adopted refs cite.
    alias_refs: list[str] = []
    if alias_inner_ref_field is not None:
        inner_ref = returned.get(alias_inner_ref_field)
        if isinstance(inner_ref, str) and inner_ref and inner_ref != source_fact_ref:
            alias_refs.append(inner_ref)
    body["alias_fact_refs"] = sorted(set(alias_refs))
    return event_type, source_fact_ref, body


def _seam_event_specs_for_attempt_dir(
    attempt_dir: Path,
    building_root: Path,
) -> list[tuple[str, str, dict[str, Any]]]:
    """The seam specs (zero, one, or — defensively — two) for one step-output attempt dir.

    Reads ``transition-concern.json`` and/or ``route-request.json`` IF present in the dir.
    They are MUTUALLY EXCLUSIVE per attempt — an Agent raises a TransitionConcern OR a
    RouteRequest, never both. If BOTH files exist in the SAME attempt dir (a torn source —
    e.g. a stale sibling left under the writer's existing_policy="replace"), the source is
    corrupt and this RAISES (fail-closed) rather than emitting both seam events. An ABSENT
    file imposes no requirement (PRESENT-WHEN-RAISED); ONE or NEITHER is fine. A PRESENT-
    but-corrupt file (unreadable / non-JSON / non-object / missing its ref field / missing
    its returned blob) RAISES (fail-closed). Returns the specs in TransitionConcern-then-
    RouteRequest order (stable; only one ever exists).
    """

    specs: list[tuple[str, str, dict[str, Any]]] = []
    concern_path = attempt_dir / _TRANSITION_CONCERN_FILE
    route_path = attempt_dir / _ROUTE_REQUEST_FILE
    # MUTUAL EXCLUSION: a TransitionConcern and a RouteRequest are mutually exclusive per
    # attempt. Both present in one attempt dir is a torn / corrupt source — fail closed
    # instead of emitting both (which would be a corrupt double-seam projection).
    if concern_path.is_file() and route_path.is_file():
        raise SpineProjectionError(
            f"{attempt_dir}: torn Agent->Link seam source — both "
            f"{_TRANSITION_CONCERN_FILE!r} and {_ROUTE_REQUEST_FILE!r} present in one "
            "attempt dir, but they are mutually exclusive (an Agent raises one OR the other)"
        )
    if concern_path.is_file():
        seam_file = _load_json_object(concern_path, source_label="transition-concern seam file")
        specs.append(
            _seam_event_body(
                seam_file,
                concern_path,
                event_type=_TRANSITION_CONCERN_EVENT,
                axis_scope=_TRANSITION_CONCERN_AXIS_SCOPE,
                ref_field=_TRANSITION_CONCERN_REF_FIELD,
                toplevel_fields=_TRANSITION_CONCERN_TOPLEVEL_FIELDS,
                returned_field=_TRANSITION_CONCERN_RETURNED_FIELD,
                alias_inner_ref_field=_TRANSITION_CONCERN_INNER_REF_FIELD,
            )
        )
    if route_path.is_file():
        seam_file = _load_json_object(route_path, source_label="route-request seam file")
        specs.append(
            _seam_event_body(
                seam_file,
                route_path,
                event_type=_ROUTE_REQUEST_EVENT,
                axis_scope=_ROUTE_REQUEST_AXIS_SCOPE,
                ref_field=_ROUTE_REQUEST_REF_FIELD,
                toplevel_fields=_ROUTE_REQUEST_TOPLEVEL_FIELDS,
                returned_field=_ROUTE_REQUEST_RETURNED_FIELD,
                alias_inner_ref_field=None,
            )
        )
    return specs


def _seam_event_specs_by_step(
    building_root: Path,
    declared_step_refs: set[str],
) -> dict[str, list[tuple[str, str, dict[str, Any]]]]:
    """Map each DECLARED step_ref to its Agent->Link seam specs (zero-or-more).

    Enumerates every ``work/step-outputs/*/`` attempt dir, reads the seam file(s) present
    in each, and groups the specs by the seam file's own top-level ``step_ref`` — but ONLY
    for a step_ref in the DECLARED plan (orphan-skip parity with the Brick/Agent + Link
    rows: an orphan step-output gets no per-step events). A seam file whose top-level
    step_ref is absent / non-string / not declared is skipped here (an orphan's seam is not
    projected; the declared-step filter is the same one the rest of the projector uses).
    VACUOUS (empty map) when there is no step-outputs dir or no seam file was raised.
    FAIL-CLOSED: a present-but-corrupt seam file RAISES via the body builders above.
    """

    by_step: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    step_outputs_dir = building_root / "work" / _STEP_OUTPUTS_DIR
    if not step_outputs_dir.is_dir():
        return by_step
    for attempt_dir in sorted(p for p in step_outputs_dir.iterdir() if p.is_dir()):
        for event_type, source_fact_ref, body in _seam_event_specs_for_attempt_dir(
            attempt_dir, building_root
        ):
            step_ref = body.get("step_ref")
            if not isinstance(step_ref, str) or not step_ref:
                # A seam file with no usable step_ref cannot be joined to a declared step;
                # skip it (orphan-skip parity — it is not attributed to any step). The
                # file's own ref field was already required by the builder, so this is only
                # reachable for a degenerate file missing the top-level step_ref.
                continue
            if step_ref not in declared_step_refs:
                continue
            by_step.setdefault(step_ref, []).append(
                (event_type, source_fact_ref, body)
            )
    return by_step


def _load_link_trace_facts(
    building_root: Path,
    trace_name: str,
    *,
    required: bool,
) -> list[dict[str, Any]] | None:
    """Load one claim_trace/link/*.json file's ``facts`` list, fail-closed.

    Returns the list of fact objects (each a JSON object carrying ``fact_ref`` +
    nested ``fact``). FAIL-CLOSED, mirroring the projector's other join-failure
    handling: a PRESENT trace that is unreadable / non-JSON / not a JSON object /
    has a non-list ``facts`` / a non-object fact entry / a fact missing a non-empty
    string ``fact_ref`` RAISES SpineProjectionError (a corrupt trace must surface
    loudly, never be silently skipped). ``required=False`` lets a genuinely ABSENT
    file return None (the NEW-from-E1 gate_receipt / policy_action traces, which a
    building with no gates / no policy action legitimately lacks); ``required=True``
    RAISES on absence (the four always-emitted Link traces). A present-but-corrupt
    file ALWAYS raises regardless of ``required``.
    """

    path = _link_trace_path(building_root, trace_name)
    if not path.exists():
        if required:
            raise SpineProjectionError(f"{path}: required Link claim_trace is absent")
        return None
    envelope = _load_json_object(path, source_label="Link claim_trace")
    raw_facts = envelope.get("facts")
    if not isinstance(raw_facts, list):
        raise SpineProjectionError(f"{path}: Link claim_trace 'facts' is not a JSON list")
    facts: list[dict[str, Any]] = []
    for position, fact in enumerate(raw_facts):
        if not isinstance(fact, dict):
            raise SpineProjectionError(
                f"{path}: Link claim_trace facts[{position}] is not a JSON object"
            )
        fact_ref = fact.get("fact_ref")
        if not isinstance(fact_ref, str) or not fact_ref:
            raise SpineProjectionError(
                f"{path}: Link claim_trace facts[{position}] has no string fact_ref"
            )
        facts.append(fact)
    return facts


def _step_link_facts(facts: list[dict[str, Any]], step_ref: str) -> list[dict[str, Any]]:
    """The trace facts belonging to one step (the unambiguous suffix join).

    A claim_trace fact carries NO step_ref field; its step is encoded ONLY in the
    fact_ref SUFFIX ("{kind}:{NN}:{slug}"), where ``slug`` is the step_ref slugged by
    the emitter's ``_resource_slug('step_ref', step_ref.replace(':', '-'))``. The join
    matches against that SAME slug (``_step_ref_slug``), not the raw step_ref, so a
    step_ref the emitter would have slugged (e.g. a ':' -> '-') still joins to its
    facts. Real step_refs are colon-free today, so the slug equals the step_ref and
    this is behavior-identical; the slug match makes the join correct REGARDLESS.

    GRAPH-EDGE EXCLUSION: a per-EDGE graph-edge fact (fact_ref
    "movement-fact:graph-edge:<edge_slug>") is NOT a per-step fact and must NEVER be
    attributed to a step. Any fact whose fact_ref contains ``:graph-edge:`` is
    excluded here (its per-edge projection is a separate, out-of-scope concern). This
    also guards the degenerate case where an edge slug's tail happens to equal a
    step's slug — the infix exclusion removes it before the suffix test.
    """

    suffix = ":" + _step_ref_slug(step_ref)
    return [
        fact
        for fact in facts
        if _GRAPH_EDGE_FACT_INFIX not in fact["fact_ref"]
        and fact["fact_ref"].endswith(suffix)
    ]


def _fact_inner_body(fact: dict[str, Any], trace_name: str) -> dict[str, Any]:
    inner = fact.get("fact")
    if not isinstance(inner, dict):
        raise SpineProjectionError(
            f"{trace_name}: claim_trace fact {fact['fact_ref']!r} has no JSON-object "
            "'fact' body"
        )
    return inner


def _copy_present_fields(
    inner: dict[str, Any],
    fields: tuple[str, ...],
    body: dict[str, Any],
) -> None:
    """Copy each named field verbatim IF present (mechanical refs/enums/counts only).

    Absent fields are simply not copied — the claim_trace fact bodies are stable but
    this stays tolerant of an optional mechanical field, exactly like the existing
    declaration body builders (``_preset_expansion_event_body``).
    """

    for field in fields:
        if field in inner:
            body[field] = inner[field]


def _require_present_fields(
    inner: dict[str, Any],
    fields: tuple[str, ...],
    fact_ref: str,
    trace_name: str,
) -> None:
    """FAIL-CLOSED guard: each named LOAD-BEARING field MUST be present in the source.

    Mirrors the existing ``_copy_required_fields`` fail-closed pattern (the per-step
    Brick/Agent builders use it): a real claim_trace fact always carries the minimum
    fields an event needs, so a malformed / sparse fact that is MISSING one of them is
    a corrupt source and must RAISE — not silently emit a sparse event. This only
    asserts PRESENCE of the minimum; the actual copy (incl. optional extras) is still
    done by ``_copy_present_fields`` with the wider allowlist.
    """

    for field in fields:
        if field not in inner:
            raise SpineProjectionError(
                f"{trace_name}: claim_trace fact {fact_ref!r} is missing required "
                f"field {field!r} for its Link spine event body (malformed/sparse "
                "source fact)"
            )


# REQUIRED-MINIMUM load-bearing fields per present Link body (single-sourced here so
# the fail-closed minimum is asserted in one place). These are the fields a real
# claim_trace present fact ALWAYS carries (see claims_link.py present-body shapes);
# a fact missing one is malformed and RAISES rather than projecting a sparse event.
# The enum-checked fields (sufficiency, policy_action) are NOT re-listed here — their
# absence already RAISEs via the enum membership check below.
_SUFFICIENCY_PRESENT_REQUIRED = ("sufficiency", "stage")
_GATE_CHECK_REQUIRED = ("gate_ref", "ordinal", "sufficiency")
_POLICY_ACTION_REQUIRED = ("policy_action",)
_TRANSFER_PRESENT_REQUIRED = ("source_boundary_ref", "target_boundary_ref")
_CARRY_PRESENT_REQUIRED = ("carried_fact_refs", "target_boundary_ref")
# The two absence markers that IDENTIFY an absence placeholder of a specific type.
_ABSENCE_REQUIRED = ("trace_role", "absent_fact_type")


def _is_absence_fact(inner: dict[str, Any]) -> bool:
    return inner.get("trace_role") == "absence_placeholder"


def _link_sufficiency_event_body(fact: dict[str, Any]) -> dict[str, Any]:
    """LinkSufficiency ([Link]) from one sufficiency_trace.json stage fact.

    PRESENT facts copy the mechanical sufficiency fields (sufficiency in
    GATE_SUFFICIENCY_LITERALS, stage, checked_public_fact, required_public_facts,
    missing_required_facts); ABSENCE facts (trace_role=absence_placeholder /
    absent_fact_type=GateFact) copy the absence marker fields. The source fact_ref
    is carried verbatim (the delta key + the stable handle a Movement event cites).
    """

    inner = _fact_inner_body(fact, _SUFFICIENCY_TRACE)
    body: dict[str, Any] = {
        "event_type": _LINK_SUFFICIENCY_EVENT,
        "axis_scope": list(_LINK_PER_STEP_AXIS_SCOPE),
        "source_fact_ref": fact["fact_ref"],
    }
    if _is_absence_fact(inner):
        # FAIL-CLOSED: an absence fact must carry its identifying absence markers; a
        # sparse one (no absent_fact_type) is malformed -> RAISE, not a near-empty body.
        _require_present_fields(inner, _ABSENCE_REQUIRED, fact["fact_ref"], _SUFFICIENCY_TRACE)
        _copy_present_fields(inner, _ABSENCE_MARKER_FIELDS, body)
    else:
        # FAIL-CLOSED: a present sufficiency fact must carry the load-bearing
        # sufficiency + stage (a malformed/sparse fact missing them RAISEs).
        _require_present_fields(
            inner, _SUFFICIENCY_PRESENT_REQUIRED, fact["fact_ref"], _SUFFICIENCY_TRACE
        )
        # The sufficiency enum is single-sourced from Gate (GATE_SUFFICIENCY_LITERALS);
        # a present fact whose sufficiency is outside it is a corrupt trace -> RAISE
        # (fail-closed), rather than projecting an unadmitted enum value.
        sufficiency = inner.get("sufficiency")
        if sufficiency not in GATE_SUFFICIENCY_LITERALS:
            raise SpineProjectionError(
                f"{_SUFFICIENCY_TRACE}: present sufficiency fact {fact['fact_ref']!r} "
                f"sufficiency {sufficiency!r} is not one of {GATE_SUFFICIENCY_LITERALS!r}"
            )
        _copy_present_fields(inner, _SUFFICIENCY_PRESENT_FIELDS, body)
    return body


def _link_gate_check_event_body(fact: dict[str, Any]) -> dict[str, Any]:
    """LinkGateCheck ([Link]) from one gate_receipt_trace.json (E1) gate fact."""

    inner = _fact_inner_body(fact, _GATE_RECEIPT_TRACE)
    # FAIL-CLOSED: a gate-receipt fact must carry the load-bearing gate_ref + ordinal
    # + sufficiency (a malformed/sparse fact missing them RAISEs, not a sparse event).
    _require_present_fields(inner, _GATE_CHECK_REQUIRED, fact["fact_ref"], _GATE_RECEIPT_TRACE)
    # gate sufficiency single-sourced from Gate (GATE_SUFFICIENCY_LITERALS).
    sufficiency = inner.get("sufficiency")
    if sufficiency not in GATE_SUFFICIENCY_LITERALS:
        raise SpineProjectionError(
            f"{_GATE_RECEIPT_TRACE}: gate-receipt fact {fact['fact_ref']!r} sufficiency "
            f"{sufficiency!r} is not one of {GATE_SUFFICIENCY_LITERALS!r}"
        )
    body: dict[str, Any] = {
        "event_type": _LINK_GATE_CHECK_EVENT,
        "axis_scope": list(_LINK_PER_STEP_AXIS_SCOPE),
        "source_fact_ref": fact["fact_ref"],
    }
    _copy_present_fields(inner, _GATE_CHECK_FIELDS, body)
    return body


def _link_policy_action_event_body(fact: dict[str, Any]) -> dict[str, Any]:
    """LinkPolicyAction ([Link]) from one policy_action_trace.json (E1) fact."""

    inner = _fact_inner_body(fact, _POLICY_ACTION_TRACE)
    # FAIL-CLOSED: a policy-action fact must carry policy_action. (The enum check
    # below already RAISEs on absence since None is not an admitted action; the
    # explicit require keeps the fail-closed minimum uniform with the other builders.)
    _require_present_fields(inner, _POLICY_ACTION_REQUIRED, fact["fact_ref"], _POLICY_ACTION_TRACE)
    # policy_action single-sourced from the operator gate-sequence
    # (ADMITTED_POLICY_ACTIONS = forward/hold/next/reroute).
    policy_action = inner.get("policy_action")
    if policy_action not in ADMITTED_POLICY_ACTIONS:
        raise SpineProjectionError(
            f"{_POLICY_ACTION_TRACE}: policy-action fact {fact['fact_ref']!r} "
            f"policy_action {policy_action!r} is not one of {ADMITTED_POLICY_ACTIONS!r}"
        )
    body: dict[str, Any] = {
        "event_type": _LINK_POLICY_ACTION_EVENT,
        "axis_scope": list(_LINK_PER_STEP_AXIS_SCOPE),
        "source_fact_ref": fact["fact_ref"],
    }
    _copy_present_fields(inner, _POLICY_ACTION_FIELDS, body)
    return body


def _movement_event_body(
    fact: dict[str, Any],
    gate_review_event_ref: str,
) -> dict[str, Any]:
    """Movement ([Link]) from one movement_trace.json step fact.

    LAUNDERS the forbidden RAW ``movement`` key to ``declared_movement`` (the SAME
    rename mechanism _LINK_LAUNCH_POLICY uses for its launch_rows, _LAUNCH_ROW_RENAME)
    so the body carries NO raw movement/target/target_ref key — only the renamed
    ``declared_movement`` + the pre-renamed ``target_boundary_ref``. The value is
    copied verbatim; only the key name changes. ``gate_review_event_ref`` cites the
    STABLE fact_ref of THIS step's movement-stage gate review (present
    sufficiency-fact-movement OR the gate-sufficiency absence fact — one always
    exists for a moved step, so it is non-empty + resolvable). This passes the
    already-committed INC-1 guard (validate_movement_events).

    slice-3 A+ part 2 ITEM 2: ALSO carries the Agent->Link causal SEAM refs the movement
    fact records — the transition-concern refs the Link adopted / did not adopt
    (``adopted_transition_concern_refs`` / ``not_adopted_transition_concern_refs``, ALWAYS
    a list — ``[]`` when the movement adopted none) and the optional ``route_request_ref``
    (omitted when the movement has none). They are copied verbatim from the source movement
    fact's ``route_decision_*`` keys (the route_decision_ prefix dropped), so the dangling
    guard (req-f 3c) can verify each cited concern/request resolves to a projected
    TransitionConcern / RouteRequest event. FAIL-CLOSED: a present-but-non-list-of-strings
    seam ref (corrupt trace) RAISES rather than emitting a malformed body.
    """

    inner = _fact_inner_body(fact, _MOVEMENT_TRACE)
    # FAIL-CLOSED: a Movement event needs BOTH the (renamed) movement value AND a
    # target_boundary_ref — the two load-bearing fields. A movement fact missing the
    # raw ``movement`` key or ``target_boundary_ref`` is malformed/sparse and must
    # RAISE, not emit a Movement with no target_boundary_ref. (``movement`` presence
    # is also covered by the enum check below; required here for an explicit message.)
    _require_present_fields(
        inner, ("movement", "target_boundary_ref"), fact["fact_ref"], _MOVEMENT_TRACE
    )
    body: dict[str, Any] = {
        "event_type": _MOVEMENT_EVENT,
        "axis_scope": list(_LINK_PER_STEP_AXIS_SCOPE),
        "source_fact_ref": fact["fact_ref"],
        "gate_review_event_ref": gate_review_event_ref,
    }
    # The movement enum is single-sourced from Link (MOVEMENT_LITERALS =
    # forward/reroute; never the LinkPolicyAction hold/next). A step movement fact
    # whose raw movement is outside it is a corrupt trace -> RAISE (fail-closed).
    raw_movement = inner.get("movement")
    if raw_movement not in MOVEMENT_LITERALS:
        raise SpineProjectionError(
            f"{_MOVEMENT_TRACE}: movement fact {fact['fact_ref']!r} movement "
            f"{raw_movement!r} is not one of {MOVEMENT_LITERALS!r}"
        )
    # LAUNDER movement -> declared_movement (kept verbatim value; the only forbidden
    # key in the movement fact body). target_boundary_ref is already non-forbidden in
    # the trace and copied verbatim (its presence is required above). NO other field is
    # copied (the movement fact also nests transition_lifecycle_* / building_lifecycle_*
    # that this event does NOT record — the narrow allowlist keeps the body
    # forbidden-key-clean).
    for raw_key, renamed_key in _MOVEMENT_FACT_RENAME.items():
        if raw_key in inner:
            body[renamed_key] = inner[raw_key]
    body["target_boundary_ref"] = inner["target_boundary_ref"]
    # slice-3 A+ part 2 ITEM 2: the Agent->Link seam refs. The two adopted/not_adopted
    # transition-concern ref LISTS are ALWAYS emitted (``[]`` when the movement has none)
    # so the body shape is consistent; the optional route_request_ref string is omitted
    # when absent. Copied verbatim from the movement fact's route_decision_* keys (prefix
    # dropped). FAIL-CLOSED on a present-but-malformed value (a corrupt trace).
    for source_key, body_key in _MOVEMENT_SEAM_LIST_REFS.items():
        if source_key in inner:
            value = inner[source_key]
            if not isinstance(value, list) or any(
                not isinstance(item, str) or not item for item in value
            ):
                raise SpineProjectionError(
                    f"{_MOVEMENT_TRACE}: movement fact {fact['fact_ref']!r} seam ref "
                    f"{source_key!r} is not a list of non-empty strings: {value!r}"
                )
            body[body_key] = list(value)
        else:
            body[body_key] = []
    route_request_ref = inner.get(_MOVEMENT_SEAM_ROUTE_REQUEST_REF_KEY)
    if route_request_ref is not None:
        if not isinstance(route_request_ref, str) or not route_request_ref:
            raise SpineProjectionError(
                f"{_MOVEMENT_TRACE}: movement fact {fact['fact_ref']!r} "
                f"{_MOVEMENT_SEAM_ROUTE_REQUEST_REF_KEY!r} is present but is not a "
                f"non-empty string: {route_request_ref!r}"
            )
        body[_MOVEMENT_SEAM_ROUTE_REQUEST_REF_KEY] = route_request_ref
    return body


def _link_transfer_event_body(fact: dict[str, Any]) -> dict[str, Any]:
    """LinkTransfer ([Link]) from one transfer_trace.json step fact.

    PRESENT facts copy the mechanical transfer refs (source/target boundary,
    public_fact_refs, required_public_facts, gate reference, evidence reference);
    ABSENCE facts (absent_fact_type=TransferFact) copy the absence marker fields.
    """

    inner = _fact_inner_body(fact, _TRANSFER_TRACE)
    body: dict[str, Any] = {
        "event_type": _LINK_TRANSFER_EVENT,
        "axis_scope": list(_LINK_PER_STEP_AXIS_SCOPE),
        "source_fact_ref": fact["fact_ref"],
    }
    if _is_absence_fact(inner):
        # FAIL-CLOSED: absence markers identify the absence; a sparse one RAISEs.
        _require_present_fields(inner, _ABSENCE_REQUIRED, fact["fact_ref"], _TRANSFER_TRACE)
        _copy_present_fields(inner, _ABSENCE_MARKER_FIELDS, body)
    else:
        # FAIL-CLOSED: a present transfer fact needs its source/target boundary refs.
        _require_present_fields(
            inner, _TRANSFER_PRESENT_REQUIRED, fact["fact_ref"], _TRANSFER_TRACE
        )
        _copy_present_fields(inner, _TRANSFER_PRESENT_FIELDS, body)
    return body


def _link_carry_event_body(fact: dict[str, Any]) -> dict[str, Any]:
    """LinkCarry ([Link]) from one carry_trace.json step fact.

    PRESENT facts copy the mechanical carry refs (carried_fact_refs,
    source_owner_axis, target boundary, gate reference, evidence reference); ABSENCE
    facts (absent_fact_type=CarryFact) copy the absence marker fields.
    """

    inner = _fact_inner_body(fact, _CARRY_TRACE)
    body: dict[str, Any] = {
        "event_type": _LINK_CARRY_EVENT,
        "axis_scope": list(_LINK_PER_STEP_AXIS_SCOPE),
        "source_fact_ref": fact["fact_ref"],
    }
    if _is_absence_fact(inner):
        # FAIL-CLOSED: absence markers identify the absence; a sparse one RAISEs.
        _require_present_fields(inner, _ABSENCE_REQUIRED, fact["fact_ref"], _CARRY_TRACE)
        _copy_present_fields(inner, _ABSENCE_MARKER_FIELDS, body)
    else:
        # FAIL-CLOSED: a present carry fact needs its carried refs + target boundary.
        _require_present_fields(
            inner, _CARRY_PRESENT_REQUIRED, fact["fact_ref"], _CARRY_TRACE
        )
        _copy_present_fields(inner, _CARRY_PRESENT_FIELDS, body)
    return body


def _link_carry_budget_event_body(fact: dict[str, Any]) -> dict[str, Any]:
    """LinkCarry ([Link]) from one BUILDING-SCOPE carry-budget fact.

    FIX #3: a carry-budget fact (fact_ref
    "carry-budget:<building_id>:<scope_tag>:<budget_ref>") is a Link-axis observation
    of a node's reroute/replay budget (budget_kind, budget_scope, exhaustion_status,
    declared_budget, observed_step_attempt_count, …). It is a BUILDING-scope fact, not
    a step fact — its fact_ref tail is "-<node>" (preceded by "brick-"), never
    ":<step-slug>", so the per-step suffix join NEVER matched it and it was DROPPED.

    The inner body shape VARIES by scope (node vs route-replay), so the mechanical
    observation fields are copied present-if-present over the defined SUPERSET
    (``_CARRY_BUDGET_FIELDS``) — a scope-specific field absent for the other scope is
    simply not copied, never fail-closed. FAIL-CLOSED only on the minimum every real
    carry-budget fact carries (budget_kind + budget_scope); a fact lacking either is a
    torn source and RAISES (mirrors the present-Link fail-closed minimum).
    """

    inner = _fact_inner_body(fact, _CARRY_TRACE)
    body: dict[str, Any] = {
        "event_type": _LINK_CARRY_EVENT,
        "axis_scope": list(_LINK_PER_STEP_AXIS_SCOPE),
        "source_fact_ref": fact["fact_ref"],
    }
    _require_present_fields(
        inner, _CARRY_BUDGET_REQUIRED, fact["fact_ref"], _CARRY_TRACE
    )
    _copy_present_fields(inner, _CARRY_BUDGET_FIELDS, body)
    return body


def _carry_budget_event_specs(
    building_root: Path,
) -> list[tuple[str, str, dict[str, Any]]]:
    """The BUILDING-SCOPE carry-budget LinkCarry specs for this building.

    FIX P1#3: read the carry trace DIRECTLY off ``carry_trace.json`` (the SAME loader the
    ``_LinkTraceBundle`` uses) so the building-scope carry-budget facts project even when
    NO declared step executed (no ``work/step-outputs`` / empty step_results). Previously
    these specs were built only inside the ``if declared_step_records:`` block (where the
    bundle is constructed), so a building with carry-budget facts but no executed steps
    silently DROPPED them — and a 2nd projection returned [] (a permanent drop).

    The carry trace is OPTIONAL here (``required=False``): an ABSENT file => [] => no
    specs (a present-but-corrupt trace still RAISES in the loader). Filters to the
    colon-anchored carry-budget prefix (disjoint from the per-step carry facts) and
    returns the (LinkCarry, fact_ref, body) spec per matched fact. Same per-fact delta
    basis as the per-step Link events (LinkCarry is in _PER_FACT_KEYED_EVENTS), so a 2nd
    projection finds them present and emits nothing.
    """

    carry_facts = _load_link_trace_facts(building_root, _CARRY_TRACE, required=False) or []
    return [
        (
            _LINK_CARRY_EVENT,
            fact["fact_ref"],
            _link_carry_budget_event_body(fact),
        )
        for fact in carry_facts
        if fact["fact_ref"].startswith(_CARRY_BUDGET_FACT_PREFIX)
    ]


class _LinkTraceBundle:
    """The six claim_trace/link fact lists, loaded once per building (fail-closed).

    The four always-emitted traces (sufficiency / movement / transfer / carry) are
    REQUIRED — an absent one for a u5_5_live building with executed steps is a torn
    source and RAISES. The two NEW-from-E1 traces (gate_receipt / policy_action) are
    OPTIONAL — a building/step with no gates or no admitted policy action lacks them,
    so they default to an empty list (emit none). A present-but-corrupt trace ALWAYS
    raises (see _load_link_trace_facts).
    """

    def __init__(self, building_root: Path) -> None:
        self.sufficiency = _load_link_trace_facts(building_root, _SUFFICIENCY_TRACE, required=True)
        self.movement = _load_link_trace_facts(building_root, _MOVEMENT_TRACE, required=True)
        self.transfer = _load_link_trace_facts(building_root, _TRANSFER_TRACE, required=True)
        self.carry = _load_link_trace_facts(building_root, _CARRY_TRACE, required=True)
        self.gate_receipt = (
            _load_link_trace_facts(building_root, _GATE_RECEIPT_TRACE, required=False) or []
        )
        self.policy_action = (
            _load_link_trace_facts(building_root, _POLICY_ACTION_TRACE, required=False) or []
        )


def _movement_gate_review_ref(step_sufficiency_facts: list[dict[str, Any]], step_ref: str) -> str:
    """The stable fact_ref a Movement event cites as its authorizing gate review.

    For a moved step exactly one of these ALWAYS exists, so the result is non-empty
    + resolvable (it is itself a LinkSufficiency event's source_fact_ref):
      * the PRESENT movement-stage sufficiency fact (inner fact.stage == "movement",
        fact_ref "sufficiency-fact-movement:NN:STEP"); else
      * the gate-sufficiency ABSENCE fact (fact_ref "absence:link-gate-sufficiency:NN:STEP").
    A seq-based filename is NEVER used (it is not stable across re-projection).
    """

    absence_ref: str | None = None
    for fact in step_sufficiency_facts:
        inner = fact.get("fact")
        if not isinstance(inner, dict):
            continue
        if _is_absence_fact(inner):
            absence_ref = absence_ref or fact["fact_ref"]
            continue
        if inner.get("stage") == _MOVEMENT_GATE_STAGE:
            return fact["fact_ref"]
    if absence_ref is not None:
        return absence_ref
    raise SpineProjectionError(
        f"{_MOVEMENT_TRACE}: moved step {step_ref!r} has no movement-stage sufficiency "
        "fact and no gate-sufficiency absence fact to cite as gate_review_event_ref"
    )


def _movement_fact_step_suffix(movement_fact_ref: str) -> str | None:
    """The STEP suffix of a ``movement-fact:NN:STEP`` fact_ref, or None if malformed.

    A movement fact's fact_ref is ``movement-fact:NN:STEP`` (the prefix ``movement-fact``
    and the ordinal ``NN`` are colon-free; ``STEP`` is the slugged step_ref tail, which
    real step_refs make colon-free). Splitting on ``:`` with maxsplit=2 yields
    ``[prefix, ordinal, step]``; the third part is the STEP. A fact_ref that does not fit
    the three-part shape (e.g. a per-edge ``movement-fact:graph-edge:<edge>`` or a torn
    ref) yields None.
    """

    parts = movement_fact_ref.split(":", 2)
    if len(parts) != 3 or not parts[2]:
        return None
    return parts[2]


def _movement_paired_sufficiency_ref(movement_fact: dict[str, Any]) -> str | None:
    """The sufficiency review THIS movement fact actually paired with, or None.

    A movement_trace fact's inner ``public_fact_refs`` lists the ONE
    ``sufficiency-fact-movement:NN:STEP`` review it paired with (verified on real
    evidence: movement-fact:03 -> sufficiency-fact-movement:03, :06 -> :06). Returning
    the entry under that prefix lets each Movement event of a MULTI-ATTEMPT step cite its
    OWN sufficiency review instead of the shared first one (the misattribution bug). The
    inner body / public_fact_refs may be malformed/absent (a torn source) or carry no
    such entry (e.g. a gate-absence step) — in those cases return None so the caller
    falls back to ``_movement_gate_review_ref`` (the movement-stage sufficiency OR the
    gate-absence fact for the step).

    F2 (cross-step guard): only a ``sufficiency-fact-movement:MM:STEP`` entry whose STEP
    suffix MATCHES this movement fact's OWN step (extracted from its
    ``movement-fact:NN:STEP`` fact_ref) is accepted. A malformed/hostile movement fact that
    lists another step's sufficiency ref (``sufficiency-fact-movement:99:other-step``) would
    otherwise mis-pair the Movement to a DIFFERENT step's sufficiency review; the step-suffix
    check rejects it and the caller falls back to this step's own gate review. Real
    single/multi-attempt data is unaffected (a real movement pairs with its own step's
    sufficiency, same STEP suffix). The FIRST same-step entry is taken; a real movement fact
    lists exactly one.
    """

    movement_fact_ref = movement_fact.get("fact_ref")
    if not isinstance(movement_fact_ref, str):
        return None
    step_suffix = _movement_fact_step_suffix(movement_fact_ref)
    if step_suffix is None:
        return None
    # Only accept a sufficiency-fact-movement entry for the SAME step (matching STEP tail).
    same_step_suffix = ":" + step_suffix
    inner = movement_fact.get("fact")
    if not isinstance(inner, dict):
        return None
    refs = inner.get("public_fact_refs")
    if not isinstance(refs, list):
        return None
    for ref in refs:
        if (
            isinstance(ref, str)
            and ref.startswith(_MOVEMENT_SUFFICIENCY_REF_PREFIX)
            and ref.endswith(same_step_suffix)
        ):
            return ref
    return None


def _link_per_step_event_specs(
    bundle: _LinkTraceBundle,
    step_ref: str,
) -> list[tuple[str, str, dict[str, Any]]]:
    """The (event_type, source_fact_ref, body) specs for one step, in CAUSAL order.

    Reads each trace's facts for THIS step (suffix join) and builds the bodies in
    the order Sufficiency -> GateCheck -> PolicyAction -> Movement -> Transfer ->
    Carry, so a Movement spec follows (and can cite) this step's already-listed
    sufficiency facts. The source_fact_ref is the stable per-fact delta key.
    """

    step_sufficiency = _step_link_facts(bundle.sufficiency, step_ref)
    specs: list[tuple[str, str, dict[str, Any]]] = []
    for fact in step_sufficiency:
        specs.append(
            (_LINK_SUFFICIENCY_EVENT, fact["fact_ref"], _link_sufficiency_event_body(fact))
        )
    for fact in _step_link_facts(bundle.gate_receipt, step_ref):
        specs.append(
            (_LINK_GATE_CHECK_EVENT, fact["fact_ref"], _link_gate_check_event_body(fact))
        )
    for fact in _step_link_facts(bundle.policy_action, step_ref):
        specs.append(
            (_LINK_POLICY_ACTION_EVENT, fact["fact_ref"], _link_policy_action_event_body(fact))
        )
    step_movement = _step_link_facts(bundle.movement, step_ref)
    if step_movement:
        # PER-MOVEMENT pairing (slice-3 A+ ITEM 1 fix): each movement fact cites the
        # sufficiency review IT actually paired with (its own
        # ``sufficiency-fact-movement:NN:STEP`` in its public_fact_refs), NOT one shared
        # first-stage review for the whole step. A multi-attempt step's Movements
        # (movement-fact:01/03/06) then cite suff:01/03/06 respectively. Only when a
        # movement fact carries no such paired entry (e.g. a gate-absence step) does it
        # fall back to the step-wide _movement_gate_review_ref (the movement-stage
        # sufficiency OR the gate-absence fact). Single-attempt steps already pair 1:1,
        # so this is behavior-identical for them (no regression).
        fallback_gate_review_ref: str | None = None
        for fact in step_movement:
            gate_review_ref = _movement_paired_sufficiency_ref(fact)
            if gate_review_ref is None:
                if fallback_gate_review_ref is None:
                    fallback_gate_review_ref = _movement_gate_review_ref(
                        step_sufficiency, step_ref
                    )
                gate_review_ref = fallback_gate_review_ref
            specs.append(
                (_MOVEMENT_EVENT, fact["fact_ref"], _movement_event_body(fact, gate_review_ref))
            )
    for fact in _step_link_facts(bundle.transfer, step_ref):
        specs.append(
            (_LINK_TRANSFER_EVENT, fact["fact_ref"], _link_transfer_event_body(fact))
        )
    for fact in _step_link_facts(bundle.carry, step_ref):
        # FIX P1#2: EXCLUDE a building-scope carry-budget fact whose colon-anchored tail
        # happens to equal this step's slug (e.g. "carry-budget:b:node:review" endswith
        # ":review"). Its inner body lacks the per-step ``carried_fact_refs`` that
        # ``_link_carry_event_body`` fail-closes on (it would RAISE); the building-scope
        # budget pass picks it up instead. Mirrors the ``:graph-edge:`` exclusion style.
        if fact["fact_ref"].startswith(_CARRY_BUDGET_FACT_PREFIX):
            continue
        specs.append(
            (_LINK_CARRY_EVENT, fact["fact_ref"], _link_carry_event_body(fact))
        )
    return specs


def _brick_compared_event_specs(
    brick_comparison_facts: list[dict[str, Any]],
    alias_map: dict[str, list[str]],
    step_ref: str,
) -> list[tuple[str, str, dict[str, Any]]]:
    """The (event_type, source_fact_ref, body) BrickCompared specs for one step (ITEM 2).

    Joins the brick-comparison facts to THIS step via the SAME suffix join the Link facts
    use (``fact_ref endswith ":" + slug(step_ref)``, EXCLUDING a ``:graph-edge:`` fact —
    a per-edge fact is not a per-step fact). A multi-attempt step carries multiple
    brick-comparison facts, so one BrickCompared spec is built per matched fact, each
    delta-keyed by its source fact_ref.

    F1: ``alias_map`` maps each CANONICAL fact_ref to the ALIAS fact_refs pointing at it;
    each spec's body records its canonical's alias refs in ``alias_fact_refs`` so a citation
    of the alias resolves to the (single) canonical BrickCompared event.
    """

    return [
        (
            _BRICK_COMPARED_EVENT,
            fact["fact_ref"],
            _brick_compared_event_body(fact, alias_map.get(fact["fact_ref"], [])),
        )
        for fact in _step_link_facts(brick_comparison_facts, step_ref)
    ]


def project_declaration_spine(building_root: Path | str) -> list[dict[str, Any]]:
    """Project missing declaration and per-step events into the building's spine.

    READS the existing spine events to compute the delta, then reads only the source
    packets needed to build missing event bodies. Declarations remain once per
    building; the Brick/Agent per-step coverage is keyed by ``(event_type, step_ref)``
    (one of each per step) and dedupes executed step-output dirs by ``step_ref``; the
    six per-step LINK events (LinkSufficiency / LinkGateCheck / LinkPolicyAction /
    Movement / LinkTransfer / LinkCarry) are READ from the on-disk
    ``evidence/claim_trace/link/*.json`` (at-time recorded facts only — NEVER a
    re-run / re-derivation / runtime simulation) and keyed by the SOURCE
    ``fact_ref`` (a step may carry multiple of a Link type). After all per-step
    events it emits the two TERMINAL building-scope events: exactly ONE ``Frontier``
    (computed from ``observe_building_frontier`` — keyed by event_type, mirrors the
    declarations) and ZERO-OR-MORE ``ResumeDisposition`` events (read from the on-disk
    ``evidence/evidence-manifest.json`` plan_snapshot's resume observations — keyed by
    ``(resumed_from, disposition_action, paused_at_ref, resume_ordinal)``, where the int
    resume_ordinal keeps two sentinel-colliding fan-in resumes distinct). A no-op
    returns ``[]`` without touching disk.

    Raises ``SpineProjectionError`` if a packet / required Link trace is absent /
    unreadable / malformed / wrong-kind or if the per-step sources cannot be joined.
    The caller (the assembly hook) gates on ``declaration_packets_present`` first, so
    this is normally called only when both declaration packets exist; the read-side
    guards remain so a corrupt packet surfaces loudly rather than producing a half
    spine.

    Returns the written event bodies (with sequence_index / run_segment /
    spine_schema_version filled in by the writer), in write order.
    """

    root = Path(building_root)

    (
        existing_declarations,
        existing_per_step,
        existing_link_per_fact,
        existing_resume_dispositions,
    ) = _existing_projection_keys(root)
    step_records = _executed_step_outputs(root)

    missing_declarations = [
        event_type
        for event_type in _BUILDING_SCOPE_DECLARATION_EVENTS
        if event_type not in existing_declarations
    ]
    missing_per_step: list[tuple[dict[str, Any], str]] = []
    for step_record in step_records:
        for event_type in _PER_STEP_EVENTS:
            if (event_type, step_record["step_ref"]) not in existing_per_step:
                missing_per_step.append((step_record, event_type))

    declared_steps: list[Any] | None = None
    agent_bindings: list[Any] | None = None
    event_bodies: list[dict[str, Any]] = []

    # Determine which step_records are in the declared plan (orphan-skip discipline,
    # parity with the Brick/Agent rows) — only declared steps contribute per-step
    # events. Computed once and reused for BOTH the Brick/Agent and the Link rows.
    declared_step_refs: set[str] = set()
    if step_records:
        declared_steps = _declared_plan_steps(root)
        declared_step_refs = _declared_step_refs(declared_steps)
        # FIX #2: reorder the alphabetically-enumerated executed step records into
        # the declared CAUSAL order so the recorded judgment SEQUENCE (the spine's
        # append order == sequence_index) follows the order steps actually ran, not
        # the dir-name alphabet. SAME dict objects reordered, so missing_per_step
        # (built above, matched by identity below) stays valid; declared_step_records
        # (filtered from step_records later) inherits the causal order too.
        # FIX P1#1: prefer the GRAPH runtime walk order (execution_order) when present,
        # else fall back to the steps[] list position (linear/preset shape).
        step_records = _ordered_by_declared_plan(
            step_records, declared_steps, _declared_execution_order(root)
        )
        missing_per_step = [
            (step_record, event_type)
            for step_record, event_type in missing_per_step
            if step_record["step_ref"] in declared_step_refs
        ]

    # The six per-step LINK events from the on-disk claim_trace, deltad by source
    # fact_ref. Built per declared executed step in CAUSAL order; a step whose Link
    # facts are all already projected contributes nothing (clean re-projection no-op).
    link_bundle: _LinkTraceBundle | None = None
    missing_link_specs: list[tuple[dict[str, Any], str, str, dict[str, Any]]] = []
    # FIX #3: the BUILDING-SCOPE carry-budget LinkCarry specs (a node's reroute/replay
    # budget observation). Disjoint from the per-step carry facts; deltad through the
    # SAME (event_type, source_fact_ref) per-fact key basis, EMITTED building-scope
    # (after all per-step Link events, before the terminal Frontier/ResumeDisposition).
    missing_carry_budget_specs: list[tuple[str, str, dict[str, Any]]] = []
    declared_step_records = [
        step_record
        for step_record in step_records
        if step_record["step_ref"] in declared_step_refs
    ]
    # BATCH-LOCAL DEDUP: a Link spine event is uniquely keyed by
    # (event_type, source_fact_ref). The on-disk delta below excludes keys already
    # projected (existing_link_per_fact). This separate set ALSO excludes a key already
    # QUEUED in THIS batch, so a trace that contains two facts with the SAME fact_ref
    # (a malformed/duplicate source trace) never queues two specs for one source fact
    # in one batch (the writer would otherwise append two events sharing a key, which
    # later re-projection could neither match nor de-duplicate cleanly).
    queued_link_keys: set[tuple[str, str]] = set()
    # slice-3 A+ ITEM 2: the BrickCompared facts for declared executed steps, loaded once
    # (required — a u5_5_live building with declared executed steps must carry the Brick
    # work_contract, else a dropped BrickCompared would false-green its per-step coverage).
    brick_comparison_facts: list[dict[str, Any]] | None = None
    # F1: each canonical brick-comparison fact_ref -> the alias fact_refs pointing at it.
    brick_comparison_alias_map: dict[str, list[str]] = {}
    # slice-3 A+ part 2 ITEM 1: the Agent->Link SEAM specs (TransitionConcern / RouteRequest)
    # per DECLARED step, read from the on-disk seam files (PRESENT-WHEN-RAISED). They share
    # the (event_type, source_fact_ref) per-fact delta basis, but are EMITTED between the
    # Brick/Agent rows and the Link events (the Agent->Link seam), so they get their OWN
    # queue (written in the per-step section between (1) and (2)).
    missing_seam_specs: list[tuple[dict[str, Any], str, str, dict[str, Any]]] = []
    seam_specs_by_step: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
    if declared_step_records:
        link_bundle = _LinkTraceBundle(root)
        brick_comparison_facts, brick_comparison_alias_map = _load_brick_comparison_facts(
            root, required=True
        )
        # The seam specs grouped by DECLARED step_ref (orphan-skip parity). Read once over
        # the step-output attempt dirs; zero-or-more per step (only when the Agent raised).
        seam_specs_by_step = _seam_event_specs_by_step(root, declared_step_refs)
        for step_record in declared_step_records:
            # The six Link per-step specs (in CAUSAL order) AND the per-step BrickCompared
            # specs share the (event_type, source_fact_ref) per-fact delta basis, so they
            # are queued through the SAME dedup + delta below. BrickCompared is appended
            # after the Link specs for the step; write order is the per-step section below.
            per_fact_specs = _link_per_step_event_specs(
                link_bundle, step_record["step_ref"]
            ) + _brick_compared_event_specs(
                brick_comparison_facts, brick_comparison_alias_map, step_record["step_ref"]
            )
            for event_type, source_fact_ref, body in per_fact_specs:
                key = (event_type, source_fact_ref)
                if key in existing_link_per_fact or key in queued_link_keys:
                    continue
                queued_link_keys.add(key)
                missing_link_specs.append(
                    (step_record, event_type, source_fact_ref, body)
                )
            # The seam specs for THIS step, deltad through the SAME per-fact key set (they
            # are now in _PER_FACT_KEYED_EVENTS, so existing_link_per_fact tracks them too).
            for event_type, source_fact_ref, body in seam_specs_by_step.get(
                step_record["step_ref"], []
            ):
                key = (event_type, source_fact_ref)
                if key in existing_link_per_fact or key in queued_link_keys:
                    continue
                queued_link_keys.add(key)
                missing_seam_specs.append(
                    (step_record, event_type, source_fact_ref, body)
                )

    # FIX P1#3: the BUILDING-SCOPE carry-budget LinkCarry specs, built UNCONDITIONALLY
    # (read directly off carry_trace.json, NOT off the bundle) so a building with
    # carry-budget facts but NO executed declared steps still projects them. Disjoint from
    # the per-step carry facts (colon-anchored prefix), deltad through the SAME per-fact key
    # set (LinkCarry is in _PER_FACT_KEYED_EVENTS, so existing_link_per_fact +
    # queued_link_keys both track them; carry-budget refs never collide with per-step keys).
    # Runs AFTER the per-step block so queued_link_keys is already populated when steps
    # exist. Building-scope, so no step_record — emitted after all per-step events below.
    for event_type, source_fact_ref, body in _carry_budget_event_specs(root):
        key = (event_type, source_fact_ref)
        if key in existing_link_per_fact or key in queued_link_keys:
            continue
        queued_link_keys.add(key)
        missing_carry_budget_specs.append((event_type, source_fact_ref, body))

    # TERMINAL building-scope events (slice-3 INC-2), computed AFTER the per-step
    # delta and emitted AFTER all per-step events below.
    #   * Frontier — exactly one per building, keyed by event_type alone (mirrors the
    #     declarations). observe_building_frontier ALWAYS returns a frontier_kind, so
    #     Frontier is always emittable; a 2nd projection finds it already present and
    #     emits nothing (no-op).
    #   * ResumeDisposition — zero-or-more, keyed by (resumed_from, disposition_action,
    #     paused_at_ref, resume_ordinal) read off existing bodies + deduped within this
    #     batch, so re-projection + partial resume is idempotent (no dup, no drop). The
    #     int resume_ordinal disambiguates two sentinel-colliding fan-in resumes (F1).
    needs_frontier = _FRONTIER_EVENT not in existing_declarations
    missing_resume_observations: list[dict[str, Any]] = []
    queued_resume_keys: set[tuple[str, str, str, int]] = set()
    for resume_ordinal, observation in enumerate(_resume_observations(root)):
        body = _resume_disposition_event_body(
            observation,
            resume_ordinal,
            root / "evidence" / "evidence-manifest.json",
        )
        # The 4-part delta key (3 strings + the int resume_ordinal). The ordinal makes
        # two sentinel-colliding fan-in resumes distinct (F1): without it, two distinct
        # fan-in holds that share a disposition_action map to the SAME three strings
        # (both fall back to the reroute-hold sentinel) and the 2nd would be dropped.
        key = (
            body["resumed_from"],
            body["disposition_action"],
            body["paused_at_ref"],
            body[_RESUME_ORDINAL_FIELD],
        )
        if key in existing_resume_dispositions or key in queued_resume_keys:
            continue
        queued_resume_keys.add(key)
        missing_resume_observations.append(body)

    if (
        not missing_declarations
        and not missing_per_step
        and not missing_link_specs
        and not missing_seam_specs
        and not missing_carry_budget_specs
        and not needs_frontier
        and not missing_resume_observations
    ):
        return []

    if _PRESET_EXPANSION_EVENT in missing_declarations:
        preset_packet = _load_packet(
            _packet_path(root, _PRESET_EXPANSION_PACKET),
            _PRESET_EXPANSION_KIND,
        )
        event_bodies.append(_preset_expansion_event_body(preset_packet))
    if _LINK_LAUNCH_POLICY_EVENT in missing_declarations:
        link_packet = _load_packet(
            _packet_path(root, _LINK_LAUNCH_POLICY_PACKET),
            _LINK_LAUNCH_POLICY_KIND,
        )
        event_bodies.append(_link_launch_policy_event_body(link_packet))
    if _TASK_SOURCE_EVENT in missing_declarations:
        # slice-3 A+ ITEM 4: the once-per-building TaskSource from the building-intake
        # packet (read fail-closed via _load_packet, which asserts the declared kind).
        intake_path = _packet_path(root, _BUILDING_INTAKE_PACKET)
        intake_packet = _load_packet(intake_path, _BUILDING_INTAKE_KIND)
        event_bodies.append(_task_source_event_body(intake_packet, intake_path))

    for step_record in step_records:
        # (1) the Brick/Agent rows for this step (BrickInput / AgentBinding /
        # AgentReturn), in their existing order.
        for missing_record, event_type in missing_per_step:
            if missing_record is not step_record:
                continue
            if event_type == _BRICK_INPUT_EVENT:
                if declared_steps is None:
                    declared_steps = _declared_plan_steps(root)
                event_body = _brick_input_event_body(
                    declared_steps,
                    step_record,
                    _packet_path(root, _DECLARED_BUILDING_PLAN_PACKET),
                )
                if event_body is not None:
                    event_bodies.append(event_body)
            elif event_type == _AGENT_BINDING_EVENT:
                if agent_bindings is None:
                    agent_bindings = _building_map_agent_bindings(root)
                if declared_steps is None:
                    declared_steps = _declared_plan_steps(root)
                agent_binding_body = _agent_binding_event_body(
                    agent_bindings,
                    declared_steps,
                    step_record,
                    _packet_path(root, _BUILDING_MAP_PACKET),
                )
                if agent_binding_body is not None:
                    event_bodies.append(agent_binding_body)
            elif event_type == _AGENT_RECEIPT_EVENT:
                event_bodies.append(_agent_receipt_event_body(step_record))
            elif event_type == _AGENT_RETURN_EVENT:
                event_bodies.append(_agent_return_event_body(step_record))
        # (1b) the Agent->Link SEAM events for this step (TransitionConcern / RouteRequest),
        # AFTER AgentReturn and BEFORE the Link events — the Agent raised the concern /
        # request at the seam, so a later Movement that ADOPTS one finds it already listed
        # (append_spine_events assigns seq in input order, so the dangling guard resolves).
        for missing_record, _event_type, _source_fact_ref, body in missing_seam_specs:
            if missing_record is step_record:
                event_bodies.append(body)
        # (2) the six per-step LINK events for this step, AFTER its Brick/Agent rows + seam,
        # in the CAUSAL order the spec list already carries (Sufficiency -> GateCheck
        # -> PolicyAction -> Movement -> Transfer -> Carry), so a Movement appends
        # after the sufficiency it cites. The bodies were already built (and deltad)
        # above; here they are placed in write order.
        for missing_record, _event_type, _source_fact_ref, body in missing_link_specs:
            if missing_record is step_record:
                event_bodies.append(body)

    # FIX #3: the BUILDING-SCOPE carry-budget LinkCarry events, emitted AFTER all
    # per-step Link events and BEFORE the terminal Frontier / ResumeDisposition — they
    # are building-scope observations (a node's reroute/replay budget), not step facts.
    # Already built + deltad above; placed here in write order.
    for _event_type, _source_fact_ref, body in missing_carry_budget_specs:
        event_bodies.append(body)

    # TERMINAL building-scope events, emitted ONCE per building AFTER all per-step
    # events: the single Frontier (computed from observe_building_frontier) then the
    # zero-or-more ResumeDisposition events (read from the on-disk resume
    # observations). Both were already deltad above; here they are placed in write
    # order at the tail of the batch.
    if needs_frontier:
        event_bodies.append(_frontier_event_body(root))
    event_bodies.extend(missing_resume_observations)

    # Append as ONE ordered batch. The writer assigns sequence_index / run_segment,
    # validates admitted type + non-empty axis_scope subset + no forbidden key, and
    # rebuilds the derived index — so the produced spine matches what BOTH checkers
    # verify.
    return append_spine_events(root, event_bodies)


__all__ = [
    "SpineProjectionError",
    "declaration_packets_present",
    "project_declaration_spine",
]

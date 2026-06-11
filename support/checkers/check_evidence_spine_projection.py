#!/usr/bin/env python3
"""Validate the U5.5 Evidence Spine PROJECTION is complete (Truth Layer).

GUARD-FIRST (slice-2): this checker exists and FIRES before the slice-2
projector. ``check_evidence_spine.py`` (slice-1) is the single-concern
STRUCTURAL guard — it proves the spine on disk is internally consistent
(pairing, hash chain, monotonic order, index == re-derivation). This SECOND
checker is the single-concern PROJECTION-COMPLETENESS guard: it proves the
spine actually CONTAINS the events the projection must cover. The two are kept
separate on purpose (structure vs coverage are different questions).

For a building whose ``evidence/evidence-manifest.json`` declares
``evidence_generation == "u5_5_live"`` this checker verifies the building-scope
declaration coverage. Any building WITHOUT that tag (every pre-U5.5 building) is
SKIPPED, so existing evidence is untouched.

What it verifies for a u5_5_live building (two assertions, both must hold):
  * (req-b) the spine ``events/`` directory contains the two BUILDING-SCOPE
    declaration events ``PresetExpansion`` AND ``LinkLaunchPolicy`` — exactly one
    of EACH. Missing OR duplicated either => RED. These are the once-per-building
    declarations (the Builder's preset expansion and the Link launch policy), so
    a complete projection must carry exactly one of each; zero means the
    projection dropped it, two means it double-counted.
  * (req-a) PER-EXECUTED-STEP COVERAGE: every executed step (enumerated from
    ``work/step-outputs/*/`` by the string ``step_ref`` in each step-output.json,
    deduped per step_ref) has at least one ``BrickInput`` AND one ``AgentBinding``
    AND one ``AgentReturn`` whose event BODY carries that same step_ref. A step
    whose identity cannot be determined (missing/unparseable/non-object
    step-output.json, or no string step_ref) is a RED. A building with no executed
    step dirs contributes no per-step requirement (req-b still applies). The
    per-step PROJECTOR is a LATER build; this guard lands FIRST and will RED a
    building that lacks the per-step events — the guard-first intent.

  * (req-e) PER-EXECUTED-STEP LINK COVERAGE: req-a covers only the Brick/Agent rows
    (BrickInput/AgentBinding/AgentReturn), so a projector that DROPPED a step's LINK
    events would false-green. req-e closes that hole: for every executed step it reads
    the per-step Link claim_trace facts (``evidence/claim_trace/link/{sufficiency,
    movement,transfer,carry,gate_receipt,policy_action}_trace.json``, filtered to the
    step via the SAME slug join + ``:graph-edge:`` exclusion the projector uses,
    present + absence facts alike) and requires the spine ``events/`` to carry a Link
    spine event whose ``source_fact_ref`` equals each such fact's ``fact_ref``. A trace
    fact with NO corresponding spine event => RED (a dropped Link projection). This
    READS claim_trace (allowed for a checker) and stays support-only: it judges nothing,
    it only verifies coverage. It is TOLERANT of absent E1 traces (a building/step with
    no gate_receipt / policy_action file imposes no requirement for those) and VACUOUS
    when there is no executed step or no claim_trace.

  * (req-g) PER-EXECUTED-STEP SEAM COVERAGE: the seam ANALOGUE of req-e. req-e covers the
    Link claim_trace facts but the two Agent->Link SEAM files a step may raise
    (``work/step-outputs/<step>-attempt-N/{transition-concern,route-request}.json``, written
    by step_outputs.py ONLY when the Agent raised one) had NO presence guard. req-f catches a
    seam ref ONLY when a ``Movement`` CITES it, so a seam RAISED-but-never-adopted (no movement
    adopts it) has no citing ref and false-greens if the projector silently drops its event —
    losing that Truth-Layer record. req-g closes that hole: for every RAISED seam file whose
    top-level ``step_ref`` is in the DECLARED plan (orphan-skip parity with the projector's
    _seam_event_specs_by_step) it requires the spine ``events/`` to carry a seam spine event of
    the matching kind (``TransitionConcern`` / ``RouteRequest``) whose ``source_fact_ref``
    equals the file's own ref field (``transition_concern_ref`` / ``route_request_ref`` — the
    SAME field the projector stamps). A raised+declared seam file with NO matching spine event
    => RED. PRESENT-WHEN-RAISED (an absent seam file imposes no requirement); fail-closed on a
    present-but-corrupt seam file; VACUOUS when no seam file was raised. This READS the on-disk
    seam files (allowed for a checker) and judges nothing — it only verifies COVERAGE.

  * (req-c) MOVEMENT-VALUE: every recorded ``Movement`` event body is well-formed
    — its ``declared_movement`` is a string in the Link-owned Movement literals
    (forward/reroute; never the LinkPolicyAction values hold/next), it cites a
    non-empty ``gate_review_event_ref``, it carries NO forbidden key (the projected
    body must use ``declared_movement``/``target_boundary_ref``, never the raw
    ``movement``/``target``/``target_ref``), and its filename type and body type
    AGREE about being a ``Movement`` event (no relabel spoof). GUARD-FIRST: the
    ``Movement`` projector is a LATER increment, so this is additive + vacuous on
    today's disk (no ``Movement`` event => no requirement) and will RED a future
    malformed movement. This checks the STRUCTURE/VALUE of a recorded movement
    FACT; it does NOT decide movement and is not Movement authority.

  * (req-d) TERMINAL FRONTIER / RESUME-DISPOSITION value+shape+cardinality: every
    recorded ``Frontier`` event body carries a ``frontier_kind`` that is a string in the
    operator-observer's single-source ``FRONTIER_KINDS`` (the six observed frontier
    literals) PLUS its load-bearing SHAPE (``frontier_reason`` a non-empty string,
    ``observed_counts`` an object); every recorded ``ResumeDisposition`` event body
    carries a ``disposition_action`` that is a string in Link's single-source
    ``DISPOSITION_ACTIONS`` (raise/forward/stop) PLUS its load-bearing SHAPE
    (``resumed_from`` / ``paused_at_ref`` / ``pending_target_ref`` non-empty strings,
    ``resume_ordinal`` an int) — the SHAPE sets MIRROR what the projector's fail-closed
    builders emit, so a SPARSE terminal body from a future buggy projector RED-s
    instead of false-greening (F3); neither carries a forbidden KEY (so a frontier_kind
    VALUE of ``complete`` is allowed — the forbidden rule is KEY-only); each terminal
    type's filename type and body type AGREE (no relabel spoof); and at MOST ONE
    ``Frontier`` event exists per building (the terminal frontier observation is unique;
    ``ResumeDisposition`` is zero-or-more — a building may resume multiple times). GUARD-FIRST: the Frontier / ResumeDisposition
    projector is a LATER increment, so this is additive + vacuous on today's disk
    (no terminal event => no requirement) and PRESENCE is NOT required (a building
    with no Frontier yet is fine; the presence-if-closed requirement is deferred to
    when the projector defines "closed"). It checks the STRUCTURE/VALUE of a recorded
    terminal FACT; it judges nothing and is not Movement / Quality authority.

MORE ASSERTIONS MAY BE ADDED HERE LATER (e.g. a judgment-token scan over event
bodies). New assertions are new helpers called from ``validate_projection``
without reshaping the gate / glob / main.

This checker is support evidence only. It is not source truth, not success
judgment, not quality judgment, and not Movement authority. It judges nothing
about the building's content; it only enforces that the spine projection covers
the building-scope declarations.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# stdlib-only path bootstrap so the canonical command
# `PYTHONPATH=support/import_identity python3 ...` (no repo-root on PYTHONPATH)
# can still import the support tree when this checker is run standalone. The
# import_identity router governs only brick_protocol.*, not support.*.
import os.path as _osp

_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_IMPORT_IDENTITY = _osp.join(_REPO_ROOT, "support", "import_identity")
if _IMPORT_IDENTITY not in sys.path:
    sys.path.insert(0, _IMPORT_IDENTITY)

# REUSE the existing u5_5_live gate (single-source) so every pre-U5.5 building is
# SKIPPED exactly as the lifecycle-path checker skips it. building_root_is_u5_5_live
# reads <building_root>/evidence/evidence-manifest.json and returns True iff it
# declares evidence_generation == "u5_5_live"; an absent/unparsable manifest or an
# absent tag => False => SKIP. (make_u5_5_live_resolver is the path-list-mode
# wrapper; this checker globs real building roots, so it gates per-root directly.)
from support.checkers.check_building_lifecycle_path_shape import (
    building_root_is_u5_5_live,
)

# SINGLE-SOURCE the value vocabularies and the forbidden-key scanner. Do NOT
# re-hardcode any of these literals here: MOVEMENT_LITERALS is Link's owned
# Movement literal tuple ('forward','reroute'); DISPOSITION_ACTIONS is Link's owned
# disposition-action tuple ('raise','forward','stop'); FRONTIER_KINDS is the
# operator-observer's owned six frontier_kind literals; _forbidden_keys_in_body is
# the spine writer's recursive forbidden-key scanner. Importing them means the
# guard and the owning axis/observer agree by construction (router governs
# brick_protocol.*).
from brick_protocol.link.movement import MOVEMENT_LITERALS
from brick_protocol.link.transition import DISPOSITION_ACTIONS
from brick_protocol.support.operator.frontier_observation import FRONTIER_KINDS
from brick_protocol.support.recording.spine import (
    SPINE_EVENT_TYPES,
    _forbidden_keys_in_body,
)

# req-e: SINGLE-SOURCE the step_ref->slug transform from the SAME primitive the
# claim_trace emitters use to BUILD a fact_ref's step suffix (claims_*.py call
# _step_fact_ref, which slugs via _resource_slug("step_ref", step_ref.replace(":",
# "-"))). The coverage guard must join a step to its trace facts against the SLUGGED
# step_ref, identical to the projector, so the two never disagree about which facts
# belong to a step.
from brick_protocol.support.operator.primitives import _resource_slug

# ORPHAN-SKIP PARITY (single-source): the per-step PROJECTOR intentionally emits NO
# per-step events for an ORPHAN step-output — a work/step-outputs/<dir> whose step_ref
# is NOT in the building's DECLARED plan (see spine_projection.project_declaration_spine,
# which filters both the Brick/Agent rows and the Link rows to
# step_record["step_ref"] in declared_step_refs). The coverage guard must use the SAME
# notion of "declared step" or it would RED a building whose projection behaved
# correctly. So this REUSES the projector's own declared-plan readers
# (_declared_plan_steps reads work/declared-building-plan.json declared_plan_copy
# steps[]/brick_steps[]; _declared_step_refs extracts each step's string step_ref) and
# its read-side error type, rather than re-deriving the plan shape here. Importing them
# means the checker and the projector agree by construction about which executed steps
# are declared vs orphan.
from brick_protocol.support.recording.spine_projection import (
    SpineProjectionError,
    _declared_link_edges,
    _declared_plan_steps,
    _declared_step_refs,
)


PROJECT_ROOT = "project"
BUILDINGS_SEGMENT = "buildings"

# The BUILDING-SCOPE declaration event types this increment requires exactly once
# in the spine projection. These are once-per-building declarations: the Builder's
# preset expansion + the Link launch policy + the building intake (TaskSource, slice-3
# A+ ITEM 4 — the task source recorded once per building). Each must appear exactly one
# time in events/.
BUILDING_SCOPE_DECLARATION_TYPES = ("PresetExpansion", "LinkLaunchPolicy", "TaskSource")

# The PER-EXECUTED-STEP event types this increment requires AT LEAST ONE of, for
# EACH unique executed step_ref. One per axis row of the unified node/edge model:
# BrickInput (the Brick row — the brick instance fed to the step), BrickCompared
# (the Brick-axis MATCH observation — how the Agent return compared to the declared
# Brick contract), AgentBinding (the Agent row — which agent was bound by
# NEED<->CAPABILITY match), AgentReceipt (the Agent "received the work" record —
# the MIDDLE of the Agent row, AgentBinding->AgentReceipt->AgentReturn),
# AgentReturn (the Agent->Link seam — what the agent returned). The per-step
# PROJECTOR stamps the executed step's step_ref into the Brick/Agent-row events;
# BrickCompared is correlated by its source_fact_ref's step SUFFIX (it carries no
# step_ref field — see _per_step_event_types). At-least-one (not exactly-one): a step
# may be re-attempted, so a step_ref can legitimately carry multiple
# BrickInput/BrickCompared/AgentReceipt/AgentReturn events.
PER_STEP_REQUIRED_TYPES = (
    "BrickInput",
    "BrickCompared",
    "AgentBinding",
    "AgentReceipt",
    "AgentReturn",
)

# CORRELATION SPLIT: the per-step required types correlate to a step by TWO different
# handles, so the coverage check must use the right one for each:
#   * STEP-REF-KEYED types stamp the executed step's ``step_ref`` into their BODY
#     (BrickInput / AgentBinding / AgentReceipt / AgentReturn) — correlated by that
#     in-body step_ref. AgentReceipt ALSO carries a ``source_fact_ref`` (the closed
#     AgentFact ref), but its step is correlated by its in-body ``step_ref`` (the SAME
#     handle as AgentReturn), so it is a STEP-REF-KEYED type, NOT a source-ref-keyed one.
#   * SOURCE-REF-KEYED types carry NO step_ref field; the step is encoded in their
#     ``source_fact_ref`` SUFFIX (BrickCompared, like the Link events) — correlated by
#     the SAME slug-suffix join (+ ``:graph-edge:`` exclusion) the projector uses. A
#     BrickCompared has one per attempt; at-least-one per step is required.
PER_STEP_STEP_REF_KEYED_TYPES = (
    "BrickInput",
    "AgentBinding",
    "AgentReceipt",
    "AgentReturn",
)
PER_STEP_SOURCE_REF_KEYED_TYPES = ("BrickCompared",)

# req-e: the six PER-STEP LINK spine event types. Every Link spine event carries the
# SOURCE claim_trace fact's ``fact_ref`` in its ``source_fact_ref`` field; req-e
# matches a per-step claim_trace link fact to its spine event BY that ref, so a
# dropped Link projection (a trace fact with no corresponding spine event) is a RED.
PER_STEP_LINK_TYPES = (
    "LinkSufficiency",
    "LinkGateCheck",
    "LinkPolicyAction",
    "Movement",
    "LinkTransfer",
    "LinkCarry",
)

# req-e: the six claim_trace/link source files the per-step Link events project from.
# The first four are always emitted for a run with executed steps; gate_receipt /
# policy_action are NEW-from-E1 and a building/step with no gates / no admitted policy
# action legitimately LACKS them — an ABSENT file imposes no requirement (tolerant),
# a PRESENT file is read fail-closed. (Same file names the projector reads.)
LINK_TRACE_FILES = (
    "sufficiency_trace.json",
    "gate_receipt_trace.json",
    "policy_action_trace.json",
    "movement_trace.json",
    "transfer_trace.json",
    "carry_trace.json",
)

# req-e (P2 TYPE-AWARE coverage): each per-step Link TRACE FILE projects to exactly ONE
# spine event TYPE. A per-step trace fact must have a spine event OF THAT TYPE carrying
# its source_fact_ref. A FLAT type-agnostic set would let an IN-FAMILY relabel (a dropped
# LinkTransfer masked by a LinkSufficiency that shares the source_fact_ref) false-green.
# Values are string literals, pinned below against the writer's SPINE_EVENT_TYPES AND the
# LINK_TRACE_FILES set (fail LOUD on drift or an unmapped trace file).
LINK_TRACE_FILE_EVENT_TYPE = {
    "sufficiency_trace.json": "LinkSufficiency",
    "gate_receipt_trace.json": "LinkGateCheck",
    "policy_action_trace.json": "LinkPolicyAction",
    "movement_trace.json": "Movement",
    "transfer_trace.json": "LinkTransfer",
    "carry_trace.json": "LinkCarry",
}
if set(LINK_TRACE_FILE_EVENT_TYPE) != set(LINK_TRACE_FILES):
    raise RuntimeError(
        "LINK_TRACE_FILE_EVENT_TYPE keys must equal LINK_TRACE_FILES — a per-step Link "
        "trace file with no mapped event type would escape type-aware coverage"
    )
for _trace_name, _trace_event_type in LINK_TRACE_FILE_EVENT_TYPE.items():
    if _trace_event_type not in SPINE_EVENT_TYPES:
        raise RuntimeError(
            f"req-e trace->event map: {_trace_event_type!r} (for {_trace_name!r}) not in "
            "SPINE_EVENT_TYPES — checker/writer event-type drift"
        )

# req-e: a per-EDGE graph-edge Link fact (fact_ref "movement-fact:graph-edge:<edge>")
# is NOT a per-step fact and the per-step projector excludes it; the coverage guard
# uses the SAME exclusion so it never demands a per-step spine event for a per-edge
# fact (which would be a false RED).
GRAPH_EDGE_FACT_INFIX = ":graph-edge:"

# req-h (GUARD #3c): the fact_ref prefix of a BUILDING-SCOPE carry-budget fact in
# carry_trace.json (fact_ref "carry-budget:<building_id>:<scope_tag>:<budget_ref>").
# The projector lifts these DISJOINT-from-per-step carry facts into LinkCarry spine
# events whose source_fact_ref EQUALS the fact_ref (see spine_projection
# _carry_budget_event_specs / _link_carry_budget_event_body). req-e demands ONLY
# per-step Link facts (suffix-matched to a step), so a carry-budget fact — whose ref
# tail is "-<node>", never a step slug — is NEVER demanded by req-e; a DROPPED
# carry-budget LinkCarry projection therefore false-greens today. req-h closes that
# hole: every on-disk carry-budget fact_ref must have a matching LinkCarry spine event.
# Single source for the prefix the projector matches on.
# COLON-ANCHORED to match the projector's _CARRY_BUDGET_FACT_PREFIX exactly (P2#4): the
# real ref is "carry-budget:<id>:...", and the colon prevents a future non-budget fact
# like "carry-budgeted-fact:01:review" from being demanded here but not projected there.
CARRY_BUDGET_FACT_PREFIX = "carry-budget:"
# req-h: the on-disk carry-budget source file (building-scope carry facts live in the
# SAME carry_trace.json the per-step carry facts use).
CARRY_TRACE_FILE = "carry_trace.json"

# req-i (GUARD #6c): a step that DECLARES a non-empty gate-sequence policy and was
# EXECUTED must have produced recorded gate decisions in the spine. A step's declared
# plan row with ``axis == "Link"`` carrying a NON-EMPTY ``gate_sequence_policy`` list
# means its Link Gate evaluated gates at run; the spine must then carry at least one
# LinkGateCheck AND one LinkPolicyAction event for that step. req-e demands a Link spine
# event ONLY for a claim_trace fact that EXISTS — so a building that declared+ran a gate
# policy but recorded ZERO gate_receipt / policy_action facts (an incomplete spine) has
# nothing for req-e to demand and false-greens (fail-open). req-i closes that hole by
# anchoring the demand on the DECLARED policy, not the on-disk trace. Single source for
# the declared-row axis + policy-list field, and for the two demanded event types.
LINK_AXIS = "Link"
GATE_SEQUENCE_POLICY_FIELD = "gate_sequence_policy"
STEP_ROWS_FIELD = "rows"
LINK_GATE_CHECK_EVENT_TYPE = "LinkGateCheck"
LINK_POLICY_ACTION_EVENT_TYPE = "LinkPolicyAction"
# req-h (GUARD #3c): the event type a carry-budget fact MUST resolve to. P2 fix — the
# coverage check must demand a LinkCarry event SPECIFICALLY (not just any per-step Link
# event with a matching source_fact_ref), else a dropped carry-budget LinkCarry could be
# masked by an unrelated Movement / LinkTransfer that happens to carry the same ref.
LINK_CARRY_EVENT_TYPE = "LinkCarry"

# SINGLE-SOURCE DRIFT GUARDS (fail LOUD at module load): the two event-type literals
# req-i keys on MUST be admitted spine event_types. The writer is the single source of
# the admitted set (SPINE_EVENT_TYPES); if either literal ever drifts out of that set
# (a typo — this codebase had a real "MovementEvent" vs "Movement" false-green), req-i
# would silently recognize ZERO real gate events => a declared+executed gate policy that
# produced no recorded decisions would pass GREEN. An explicit raise (NOT a bare assert
# — assert is stripped under python -O) turns that class of typo into a load-time crash
# instead of a false-green. (Same pattern as the MOVEMENT_EVENT_TYPE / terminal pins.)
for _gate_event_type in (
    LINK_GATE_CHECK_EVENT_TYPE,
    LINK_POLICY_ACTION_EVENT_TYPE,
    LINK_CARRY_EVENT_TYPE,
):
    if _gate_event_type not in SPINE_EVENT_TYPES:
        raise RuntimeError(
            f"gate-coverage event type {_gate_event_type!r} not in SPINE_EVENT_TYPES — "
            "checker/writer event-type drift"
        )

# req-f: the DANGLING-REF guard event types + ref keys. req-f checks that EVERY
# cross-event ref a projected event carries RESOLVES to a projected event of the right
# KIND, building the resolvable-ref index from every projected event's source_fact_ref
# PLUS its alias_fact_refs. It is support-only (pure ref-integrity — it judges nothing).
SUFFICIENCY_EVENT_TYPE = "LinkSufficiency"
BRICK_COMPARED_EVENT_TYPE = "BrickCompared"
TRANSITION_CONCERN_EVENT_TYPE = "TransitionConcern"
ROUTE_REQUEST_EVENT_TYPE = "RouteRequest"

# req-g: the Agent->Link SEAM presence-coverage guard (the analogue of req-e for the
# seam files). req-e joins each per-step claim_trace LINK fact back to a projected Link
# spine event; req-g does the SAME for the two on-disk seam files a step may raise —
# work/step-outputs/<step>-attempt-N/{transition-concern,route-request}.json (written by
# step_outputs.py ONLY when the Agent raised one; mutually exclusive per attempt). A
# projector that DROPPED a raised-but-never-adopted seam event would false-green (req-f
# fires ONLY when a Movement CITES the ref; a seam raised but adopted by no movement has
# no citing ref, so req-f never demands it). req-g closes that hole by enumerating the
# raised seam files for each DECLARED executed step and asserting a matching
# TransitionConcern / RouteRequest spine event exists by source_fact_ref. The two seam
# files + their event type + the file-level REF field that IS the projected event's
# source_fact_ref (the SAME field the projector stamps — see spine_projection
# _seam_event_body). Single source for the file<->event<->ref-field triple.
SEAM_FILE_SPECS = (
    ("transition-concern.json", TRANSITION_CONCERN_EVENT_TYPE, "transition_concern_ref"),
    ("route-request.json", ROUTE_REQUEST_EVENT_TYPE, "route_request_ref"),
)
# req-g: the two seam event types whose source_fact_ref the presence guard indexes.
SEAM_EVENT_TYPES = (TRANSITION_CONCERN_EVENT_TYPE, ROUTE_REQUEST_EVENT_TYPE)
# req-g: the seam file's top-level step_ref field (used for the orphan-skip declared-step
# filter — the SAME field the projector groups seam files by, see _seam_event_specs_by_step).
SEAM_STEP_REF_FIELD = "step_ref"
# req-f (b): a checked_public_fact citing a brick-comparison fact must resolve to a
# projected BrickCompared event. Only refs under this prefix are demanded (a sufficiency
# fact may check OTHER public facts — e.g. an agent-fact — that BrickCompared does not
# cover; those are not req-f's concern). Single source for the prefix the writer uses.
BRICK_COMPARISON_FACT_PREFIX = "brick-comparison:"
# req-f (c): the Movement body keys carrying the Agent->Link causal SEAM refs (the
# projector ITEM 2 stamps them). The two list keys cite TransitionConcern events; the
# optional string key cites a RouteRequest event.
MOVEMENT_ADOPTED_CONCERN_REFS_KEYS = (
    "adopted_transition_concern_refs",
    "not_adopted_transition_concern_refs",
)
MOVEMENT_ROUTE_REQUEST_REF_KEY = "route_request_ref"
# req-f (a): the Movement body key citing its authorizing gate review (a LinkSufficiency).
MOVEMENT_GATE_REVIEW_REF_KEY = "gate_review_event_ref"
# req-f (b): the LinkSufficiency body key carrying the checked public fact.
SUFFICIENCY_CHECKED_PUBLIC_FACT_KEY = "checked_public_fact"
# req-f index: a projected event resolves a ref by its own source_fact_ref OR by an entry
# in its alias_fact_refs (the building-scoped alias a BrickCompared records, or the inner
# concern_ref a TransitionConcern records). Single source for the two index ref keys.
EVENT_SOURCE_FACT_REF_KEY = "source_fact_ref"
EVENT_ALIAS_FACT_REFS_KEY = "alias_fact_refs"

PROOF_LIMIT = (
    "proof limit: this checker proves only that a u5_5_live building's spine "
    "projection covers (a) the building-scope declarations (exactly one each of "
    "PresetExpansion, LinkLaunchPolicy, and TaskSource in events/), (b) per-executed-step "
    "Brick/Agent coverage (each executed step_ref has at least one "
    "BrickInput, BrickCompared, AgentBinding, AgentReceipt, and AgentReturn carrying it "
    "in events/), (e) "
    "per-executed-step LINK coverage (each per-step claim_trace link fact has a "
    "matching Link spine event by source_fact_ref, tolerant of absent E1 traces), (g) "
    "per-executed-step SEAM coverage (each RAISED transition-concern / route-request "
    "seam file whose step_ref is declared has a matching TransitionConcern / RouteRequest "
    "spine event by source_fact_ref, present-when-raised), and "
    "(c) the Movement-value shape of any recorded Movement event (declared_movement "
    "in the Link Movement literals, a non-empty gate_review_event_ref, no forbidden "
    "key, filename/body type agree), and (d) the value+SHAPE+cardinality of any "
    "recorded terminal event (Frontier.frontier_kind in FRONTIER_KINDS plus "
    "frontier_reason/observed_counts present and well-typed; "
    "ResumeDisposition.disposition_action in DISPOSITION_ACTIONS plus "
    "resumed_from/paused_at_ref/pending_target_ref/resume_ordinal present and "
    "well-typed; no forbidden key, filename/body type agree, at most one Frontier), and "
    "(f) cross-event ref INTEGRITY (no dangling ref): every Movement.gate_review_event_ref "
    "resolves to a projected LinkSufficiency event, every LinkSufficiency.checked_public_fact "
    "that is a brick-comparison ref resolves to a projected BrickCompared event (by "
    "source_fact_ref or an alias_fact_refs entry), and every Movement "
    "adopted/not_adopted_transition_concern_refs entry resolves to a projected "
    "TransitionConcern event + any Movement.route_request_ref resolves to a projected "
    "RouteRequest event — an unresolved ref => RED; "
    "(h) building-scope carry-budget coverage (every carry_trace fact whose fact_ref "
    "starts 'carry-budget:' has a matching LinkCarry spine event by source_fact_ref), and "
    "(i) declared gate-sequence-policy coverage (every EXECUTED step that declares a "
    "non-empty gate_sequence_policy — on a linear step row OR a graph link_edge's source "
    "step — has at least one LinkGateCheck and one LinkPolicyAction spine event); it "
    "does not prove the spine's structural integrity (that is check_evidence_spine), "
    "content correctness, source truth, success judgment, quality judgment, or Movement "
    "authority — the Movement-value, terminal-value, and ref-integrity assertions check the "
    "STRUCTURE/VALUE/SHAPE/RESOLVABILITY of a recorded fact, they do not decide movement or "
    "judge the building."
)


def _reject_non_finite(token: str):
    """parse_constant hook: REJECT the non-finite JSON constants NaN/Infinity.

    Python's ``json.loads`` ACCEPTS the non-standard tokens ``NaN``, ``Infinity``
    and ``-Infinity`` by default (via ``parse_constant``). A canonical spine event
    body never contains them; a body that does is non-canonical and must NOT count
    as a valid event. Raising ``ValueError`` here turns such a body into a parse
    failure (RED) in ``_load_event_type`` instead of a silently-accepted float.
    """

    raise ValueError(f"non-finite JSON constant {token!r}")


def _load_event_body(event_path: Path, violations: list[str]) -> dict | None:
    """Return one event ``.json`` body as a validated dict, or None on failure.

    The SINGLE fail-closed event-body load both assertions read through (event_type
    for declaration coverage; event_type + step_ref for per-step coverage), so the
    NaN/Infinity rejection is enforced once. A parse failure / non-object body is a
    RED and yields None (the event does not count). Structural validity of the body
    is the slice-1 structural checker's concern; here we only read the fields the
    coverage assertions need, defensively.

    The body is parsed with ``parse_constant=_reject_non_finite`` so a NaN /
    Infinity body is REJECTED (RED), not silently accepted as a float. The except
    catches ``ValueError`` (the parse_constant raise; also the superclass of
    ``json.JSONDecodeError``) so a non-canonical body becomes a RED + None.
    """

    try:
        body = json.loads(
            event_path.read_text(encoding="utf-8"),
            parse_constant=_reject_non_finite,
        )
    except (OSError, ValueError) as exc:
        violations.append(f"{event_path}: event .json parse failed: {exc}")
        return None
    if not isinstance(body, dict):
        violations.append(f"{event_path}: event body must be a JSON object")
        return None
    # CLOSE THE WHOLE non-finite CLASS: parse_constant above only rejects the
    # literal tokens NaN/Infinity/-Infinity; a numeric OVERFLOW like 1e999999
    # parses to inf via parse_float and slips past. json.dumps(..., allow_nan=False)
    # raises ValueError on NaN/inf/-inf ANYWHERE in the structure (literal or
    # overflow), so a non-finite body becomes a RED + None (not counted).
    try:
        json.dumps(body, allow_nan=False)
    except ValueError as exc:
        violations.append(f"{event_path}: non-finite value in event body: {exc}")
        return None
    return body


def _load_event_type(event_path: Path, violations: list[str]) -> str | None:
    """Return the ``event_type`` of one event ``.json`` body, or None on failure.

    A parse failure / non-object body / missing-or-non-string event_type is
    recorded as a RED and yields None (the event does not count toward coverage).
    Reads through the shared ``_load_event_body`` so the non-finite rejection is
    applied identically to the per-step coverage assertion.
    """

    body = _load_event_body(event_path, violations)
    if body is None:
        return None
    event_type = body.get("event_type")
    if not isinstance(event_type, str) or not event_type:
        violations.append(f"{event_path}: event body has no string event_type")
        return None
    return event_type


def _filename_event_type(event_path: Path) -> str | None:
    """Return the ``<Type>`` segment of a ``<digits>-<Type>.json`` event filename.

    The slice-1 writer names every event file ``<seq>-<Type>.json`` (see
    ``spine.EVENT_FILENAME_RE``). We parse the type out of the FILENAME so a body
    whose event_type disagrees with its filename (an identity spoof) can be caught
    rather than counted by body alone. A stdlib-only parse: strip the ``.json``
    suffix, split once on ``-`` so ``0001-TaskSource`` -> ``TaskSource``. A name
    that does not fit the ``<digits>-<Type>`` shape yields None (treated as a
    mismatch by the caller).
    """

    stem = event_path.name[: -len(".json")] if event_path.name.endswith(".json") else event_path.name
    seq, sep, type_segment = stem.partition("-")
    if not sep or not seq.isdigit() or not type_segment:
        return None
    return type_segment


def _building_scope_type_counts(
    building_root: Path,
    violations: list[str],
) -> Counter[str]:
    """Count occurrences of each building-scope declaration type in events/.

    Reads every ``evidence/spine/events/*.json`` body's event_type and tallies
    the building-scope declaration types. Counts ONLY the .json bodies (the .md
    is a pure render of the same body; counting both would double everything).
    A missing spine/ or events/ directory yields an empty Counter (the
    assert-coverage step then reports each required type as missing == RED for a
    u5_5_live building, which must already carry its spine projection).

    IDENTITY GUARD (fail-closed): the count is keyed on the BODY event_type, so a
    file ``0001-TaskSource.json`` whose body claims ``event_type=PresetExpansion``
    would otherwise be miscounted. Before counting, the filename ``<Type>`` segment
    must EQUAL the body event_type; a mismatch is a RED and the event is NOT
    counted. The slice-1 writer guarantees filename == body, so a valid spine never
    false-REDs here — this only catches a tampered/spoofed events/ directory.
    """

    counts: Counter[str] = Counter()
    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return counts
    for event_path in sorted(events_dir.glob("*.json")):
        event_type = _load_event_type(event_path, violations)
        if event_type is None:
            continue
        filename_type = _filename_event_type(event_path)
        if filename_type != event_type:
            violations.append(
                f"{event_path}: filename/body event_type mismatch "
                f"(filename declares {filename_type!r}, body declares "
                f"{event_type!r}); refusing to count this event"
            )
            continue
        if event_type in BUILDING_SCOPE_DECLARATION_TYPES:
            counts[event_type] += 1
    return counts


def _executed_step_refs(building_root: Path, violations: list[str]) -> set[str]:
    """The set of executed step_refs under building_root/work/step-outputs/.

    ENUMERATE executed steps by globbing the ``work/step-outputs/*/`` directories;
    each holds a ``step-output.json`` whose string ``step_ref`` field is the step
    identity. DEDUPE into a set (the same step_ref repeats across attempt-N dirs;
    coverage is per step_ref, not per attempt).

    FAIL-CLOSED on an indeterminate step identity: a step-output dir whose
    step-output.json is missing / unparseable / non-object / lacks a string
    step_ref appends a RED (we cannot say which step it covers, so coverage for
    it is unverifiable) and contributes no step_ref. An ABSENT step-outputs/ or
    zero step dirs yields the empty set (req-a then contributes no per-step
    requirement; req-b still applies — see ``validate_per_step_coverage``).
    """

    step_refs: set[str] = set()
    step_outputs_dir = building_root / "work" / "step-outputs"
    if not step_outputs_dir.is_dir():
        return step_refs
    for step_dir in sorted(p for p in step_outputs_dir.iterdir() if p.is_dir()):
        output_path = step_dir / "step-output.json"
        if not output_path.is_file():
            # ADAPTER-ERROR OCCURRENCE (0612): a breakdown step writes an
            # adapter-error.json capsule and NO step-output.json — the step
            # never returned (no AgentFact), so there is no executed-step
            # coverage to demand; the capsule is the admitted record of the
            # occurrence (validated by the lifecycle path-shape checker).
            # A dir with NEITHER file stays RED (fail-closed unchanged).
            if (step_dir / "adapter-error.json").is_file():
                continue
            violations.append(
                f"{step_dir}: cannot determine executed step identity for coverage "
                "(missing step-output.json)"
            )
            continue
        # Reuse the SAME fail-closed json load the event bodies use (non-finite
        # NaN/Infinity rejected via _reject_non_finite + allow_nan=False). A
        # parse failure / non-object body already appends its own RED here.
        body = _load_event_body(output_path, violations)
        if body is None:
            continue
        step_ref = body.get("step_ref")
        if not isinstance(step_ref, str) or not step_ref:
            violations.append(
                f"{output_path}: cannot determine executed step identity for "
                "coverage (no string step_ref)"
            )
            continue
        step_refs.add(step_ref)
    return step_refs


def _declared_plan_step_refs(building_root: Path, violations: list[str]) -> set[str] | None:
    """The set of step_refs in this building's DECLARED plan, or None if unreadable.

    Reads the declared plan EXACTLY as the per-step projector does — via the
    projector's own ``_declared_plan_steps`` (work/declared-building-plan.json ->
    declared_plan_copy -> steps[]/brick_steps[]) and ``_declared_step_refs`` (each
    step's string step_ref) — so the checker's notion of "declared step" matches the
    projector's by construction. This is the orphan filter: a step-output whose
    step_ref is NOT in this set is an ORPHAN, which the projector SKIPS (emits no
    per-step events for it), so the coverage guards must not require per-step events
    for it.

    FAIL-CLOSED (NOT a silent pass): the projector's readers RAISE
    SpineProjectionError when the declared plan is absent / unreadable / non-JSON /
    wrong-kind / non-object declared_plan_copy / non-list steps. For a u5_5_live
    building (this is only called from the per-step validators, which run only for an
    inspected u5_5_live building) that is a RED — we cannot tell declared from orphan,
    so coverage is unverifiable. We append the RED and return None; the caller then
    skips the per-step requirement (the run is already failing via this RED), rather
    than treating every executed step as orphan (a vacuous false-green) or every
    executed step as declared (a false RED on a genuinely orphaned step).
    """

    try:
        declared_steps = _declared_plan_steps(building_root)
    except SpineProjectionError as exc:
        violations.append(
            f"{building_root}: u5_5_live building's declared plan could not be read to "
            f"separate declared steps from orphan step-outputs for per-step coverage; "
            f"failing closed ({exc})"
        )
        return None
    return _declared_step_refs(declared_steps)


def _per_step_event_types(building_root: Path, violations: list[str]) -> dict[str, set[str]]:
    """Map each in-body step_ref to the STEP-REF-KEYED event_types carrying it in events/.

    Reads every ``evidence/spine/events/*.json`` body (the .json only — the .md is
    a pure render, counting both would double) through the shared fail-closed load.
    For each body that carries a string ``step_ref`` AND a PER_STEP_STEP_REF_KEYED_TYPES
    event_type (BrickInput / AgentBinding / AgentReturn), records
    ``step_ref -> {event_type, ...}``. The SOURCE-REF-KEYED types (BrickCompared) carry no
    step_ref field and are correlated separately by source_fact_ref suffix
    (see ``_source_ref_keyed_steps``). Events without a string step_ref (the
    building-scope declarations, the Link/BrickCompared per-fact events) contribute
    nothing here. A missing spine/events/ dir yields an empty map (every executed step is
    then reported as fully uncovered == RED for the step-ref-keyed types).

    The body event_type is read via ``_load_event_type`` (which also REDs a
    missing/non-string event_type); a body that fails to load contributes nothing.
    """

    by_step: dict[str, set[str]] = {}
    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return by_step
    for event_path in sorted(events_dir.glob("*.json")):
        body = _load_event_body(event_path, violations)
        if body is None:
            continue
        event_type = body.get("event_type")
        if not isinstance(event_type, str) or event_type not in PER_STEP_STEP_REF_KEYED_TYPES:
            continue
        step_ref = body.get("step_ref")
        if not isinstance(step_ref, str) or not step_ref:
            continue
        by_step.setdefault(step_ref, set()).add(event_type)
    return by_step


def _source_ref_keyed_steps(building_root: Path, violations: list[str]) -> dict[str, set[str]]:
    """Map each step SLUG-SUFFIX to the SOURCE-REF-KEYED event_types covering it.

    The SOURCE-REF-KEYED per-step types (BrickCompared) carry no step_ref field; their
    step is the SUFFIX of ``source_fact_ref`` (``"{kind}:{NN}:{slug(step_ref)}"``), the
    SAME join the projector + req-e use. This reads every spine event whose body
    event_type is a PER_STEP_SOURCE_REF_KEYED_TYPES, EXCLUDES a ``:graph-edge:`` per-edge
    source ref (not a per-step fact), and records ``slug -> {event_type, ...}`` keyed on
    the source_fact_ref tail after the final ``:``. The CALLER joins a step to this map by
    slugging the step_ref the same way. A source-ref-keyed body with no string
    source_fact_ref is a malformed projection -> RED (and contributes nothing). A missing
    spine/events/ dir yields an empty map (the type is then reported missing for every
    step).
    """

    by_slug: dict[str, set[str]] = {}
    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return by_slug
    for event_path in sorted(events_dir.glob("*.json")):
        body = _load_event_body(event_path, violations)
        if body is None:
            continue
        event_type = body.get("event_type")
        if not isinstance(event_type, str) or event_type not in PER_STEP_SOURCE_REF_KEYED_TYPES:
            continue
        source_fact_ref = body.get("source_fact_ref")
        if not isinstance(source_fact_ref, str) or not source_fact_ref:
            violations.append(
                f"{event_path}: {event_type} spine event has no string source_fact_ref "
                "(cannot correlate it to an executed step for per-step coverage)"
            )
            continue
        if GRAPH_EDGE_FACT_INFIX in source_fact_ref:
            continue
        slug = source_fact_ref.rsplit(":", 1)[-1]
        if not slug:
            continue
        by_slug.setdefault(slug, set()).add(event_type)
    return by_slug


def validate_per_step_coverage(building_root: Path, violations: list[str]) -> None:
    """req-a: every EXECUTED step has Brick/Agent run events in the spine.

    For each unique executed step_ref (from work/step-outputs/), the spine events/
    MUST carry at least one BrickInput AND BrickCompared AND AgentBinding AND
    AgentReceipt AND AgentReturn covering that step. The STEP-REF-KEYED types
    (BrickInput / AgentBinding / AgentReceipt / AgentReturn) are correlated by their
    in-body ``step_ref``; the SOURCE-REF-KEYED type (BrickCompared) is correlated by its
    ``source_fact_ref`` SUFFIX (the SAME slug join + ``:graph-edge:`` exclusion the
    projector uses), since it carries no step_ref field. A missing event type for a step
    is a RED naming the step_ref + each missing event_type.

    If work/step-outputs/ is absent or has zero step dirs, ``_executed_step_refs``
    returns the empty set and this contributes no per-step requirement (a building
    with no executed steps has no per-step coverage to verify). req-b (declarations)
    is enforced separately in ``validate_projection`` regardless.
    """

    executed_step_refs = _executed_step_refs(building_root, violations)
    if not executed_step_refs:
        return
    # ORPHAN-SKIP (parity with the projector): require per-step events ONLY for
    # executed steps whose step_ref IS in the declared plan. An ORPHAN step-output
    # (step_ref not in the declared plan) gets NO per-step events from the projector,
    # so demanding them here would RED a correct projection. FAIL-CLOSED: an unreadable
    # declared plan returns None (the RED is already appended) — skip the per-step
    # requirement rather than demand it of every step (false RED) or no step (vacuous).
    declared_step_refs = _declared_plan_step_refs(building_root, violations)
    if declared_step_refs is None:
        return
    required_step_refs = executed_step_refs & declared_step_refs
    if not required_step_refs:
        return
    by_step = _per_step_event_types(building_root, violations)
    by_slug = _source_ref_keyed_steps(building_root, violations)
    for step_ref in sorted(required_step_refs):
        present = set(by_step.get(step_ref, set()))
        # SOURCE-REF-KEYED coverage: a BrickCompared whose source_fact_ref suffix slug
        # equals this step's slug covers it.
        present |= by_slug.get(_step_ref_slug(step_ref), set())
        missing = [t for t in PER_STEP_REQUIRED_TYPES if t not in present]
        if missing:
            violations.append(
                f"{building_root}: u5_5_live spine projection is missing per-step "
                f"event(s) for executed step {step_ref!r}: "
                f"{', '.join(missing)} (expected at least one of each covering "
                "that step in events/)"
            )


def _step_ref_slug(step_ref: str) -> str:
    """Slug a step_ref the SAME way the emitters slugged it into a fact_ref suffix.

    Identical to the projector's join transform: a step fact_ref's suffix is
    ``":" + _resource_slug("step_ref", step_ref.replace(":", "-"))``. Matching against
    the slug (not the raw step_ref) keeps the coverage guard and the projector in
    agreement about which trace facts belong to a step.
    """

    return _resource_slug("step_ref", step_ref.replace(":", "-"))


def _load_link_trace_facts(
    building_root: Path,
    trace_name: str,
    violations: list[str],
) -> list[dict]:
    """Load one claim_trace/link/*.json file's ``facts``, fail-closed (checker side).

    Returns the list of fact objects (each carrying a string ``fact_ref``). An ABSENT
    file returns ``[]`` (no requirement — the NEW-from-E1 gate_receipt / policy_action
    traces a building legitimately lacks). A PRESENT file that is unreadable / non-JSON
    / non-object / has a non-list ``facts`` / a non-object fact / a fact with no string
    ``fact_ref`` appends a RED and contributes the facts it could parse (fail-closed:
    the RED already fails the run). This READS claim_trace, which is allowed for a
    checker; it JUDGES NOTHING about the facts — it only enumerates them for coverage.
    """

    path = building_root / "evidence" / "claim_trace" / "link" / trace_name
    if not path.exists():
        return []
    if not path.is_file():
        violations.append(f"{path}: claim_trace link file exists but is not a plain file")
        return []
    # Reuse the SAME fail-closed body load the event bodies use (non-finite rejected).
    envelope = _load_event_body(path, violations)
    if envelope is None:
        return []
    raw_facts = envelope.get("facts")
    if not isinstance(raw_facts, list):
        violations.append(f"{path}: claim_trace 'facts' is not a JSON list")
        return []
    facts: list[dict] = []
    for position, fact in enumerate(raw_facts):
        if not isinstance(fact, dict):
            violations.append(f"{path}: claim_trace facts[{position}] is not a JSON object")
            continue
        fact_ref = fact.get("fact_ref")
        if not isinstance(fact_ref, str) or not fact_ref:
            violations.append(f"{path}: claim_trace facts[{position}] has no string fact_ref")
            continue
        facts.append(fact)
    return facts


def _step_link_fact_refs(facts: list[dict], step_ref: str) -> list[str]:
    """The fact_refs of one step's per-step link facts (slug join + graph-edge exclude).

    Mirrors the projector's ``_step_link_facts``: a fact belongs to a step iff its
    fact_ref endswith ``":" + slug(step_ref)`` AND its fact_ref does NOT contain the
    per-edge ``:graph-edge:`` infix (a per-edge graph-edge fact is not a per-step fact
    and is not projected per step — excluding it keeps the coverage demand correct).
    """

    suffix = ":" + _step_ref_slug(step_ref)
    return [
        fact["fact_ref"]
        for fact in facts
        if GRAPH_EDGE_FACT_INFIX not in fact["fact_ref"]
        and fact["fact_ref"].endswith(suffix)
    ]


def validate_per_step_link_coverage(building_root: Path, violations: list[str]) -> None:
    """req-e: every per-step claim_trace LINK fact has a matching Link spine event.

    A projector that DROPS a step's Link events would pass req-a (Brick/Agent only)
    and false-green. req-e closes that hole: for each EXECUTED step (work/step-outputs/,
    the same enumeration req-a uses), it reads the per-step claim_trace link facts from
    ``evidence/claim_trace/link/*.json`` (filtered to the step via the SAME slug join
    and the SAME ``:graph-edge:`` exclusion the projector uses, present + absence facts
    alike) and asserts the spine ``events/`` carries a Link spine event whose
    ``source_fact_ref`` EQUALS each such fact's ``fact_ref``. A trace fact with NO
    corresponding spine event is a dropped projection == RED.

    TOLERANT of absent E1 traces: an absent gate_receipt / policy_action file imposes
    no requirement (``_load_link_trace_facts`` returns [] for an absent file). VACUOUS
    when there is no executed step (``_executed_step_refs`` empty) or no claim_trace at
    all. FAIL-CLOSED: a present-but-corrupt trace appends its own RED.

    This guard READS claim_trace (allowed for a checker) and stays support-only: it
    JUDGES NOTHING about the facts — it only verifies COVERAGE (each recorded per-step
    link fact was projected). It is not source truth, success / quality, or Movement
    authority.
    """

    executed_step_refs = _executed_step_refs(building_root, violations)
    if not executed_step_refs:
        return
    # ORPHAN-SKIP (parity with the projector + req-a): the projector projects per-step
    # Link events ONLY for declared executed steps (declared_step_records), so a per-step
    # Link fact that belongs to an ORPHAN step-output has NO spine event by design.
    # Require Link coverage ONLY for executed steps in the declared plan. FAIL-CLOSED on
    # an unreadable declared plan (None => the RED is already appended; skip).
    declared_step_refs = _declared_plan_step_refs(building_root, violations)
    if declared_step_refs is None:
        return
    required_step_refs = executed_step_refs & declared_step_refs
    if not required_step_refs:
        return
    # Load each trace once (absent E1 files => []); then join per step.
    trace_facts_by_file = {
        trace_name: _load_link_trace_facts(building_root, trace_name, violations)
        for trace_name in LINK_TRACE_FILES
    }
    # P2 TYPE-AWARE: each trace file projects to ONE event type; require the fact's ref in
    # THAT type's spine source-ref set, so an in-family relabel (a dropped LinkTransfer
    # masked by a LinkSufficiency sharing the ref) cannot false-green. (Mirrors req-h's
    # type-aware pattern via _spine_source_fact_refs_by_type.)
    by_type = _spine_source_fact_refs_by_type(
        building_root,
        tuple(dict.fromkeys(LINK_TRACE_FILE_EVENT_TYPE.values())),
        violations,
    )
    for step_ref in sorted(required_step_refs):
        for trace_name in LINK_TRACE_FILES:
            event_type = LINK_TRACE_FILE_EVENT_TYPE[trace_name]
            type_refs = by_type.get(event_type, set())
            for fact_ref in _step_link_fact_refs(trace_facts_by_file[trace_name], step_ref):
                if fact_ref not in type_refs:
                    violations.append(
                        f"{building_root}: u5_5_live spine projection DROPPED a per-step "
                        f"Link event for executed step {step_ref!r}: claim_trace fact "
                        f"{fact_ref!r} (from {trace_name}) has no {event_type} spine event "
                        "whose source_fact_ref matches it in events/"
                    )


def validate_carry_budget_coverage(building_root: Path, violations: list[str]) -> None:
    """req-h (GUARD #3c): every BUILDING-SCOPE carry-budget fact has a LinkCarry event.

    req-e demands coverage ONLY for per-step Link facts (suffix-matched to an executed
    step). A BUILDING-SCOPE carry-budget fact (fact_ref
    "carry-budget:<building_id>:<scope_tag>:<budget_ref>") is DISJOINT from the per-step
    facts — its ref tail is "-<node>", never a step slug — so req-e NEVER demands it. A
    projector that DROPPED a carry-budget LinkCarry event therefore false-greens. req-h
    closes that hole: for every on-disk carry-budget fact_ref, the spine ``events/`` must
    carry a LinkCarry spine event whose ``source_fact_ref`` EQUALS it (the projector
    stamps the carry-budget fact_ref as the LinkCarry source_fact_ref — see
    spine_projection ``_link_carry_budget_event_body``).

    Reads carry_trace.json via the existing ``_load_link_trace_facts`` (absent file => []
    => vacuous, no requirement; present-but-corrupt already RED-s inside that loader),
    then collects every fact whose ``fact_ref`` startswith "carry-budget:". The spine
    LinkCarry source refs come from ``_spine_source_fact_refs_by_type`` restricted to
    ``LinkCarry`` (P2 fix: demanding LinkCarry SPECIFICALLY, so a same-ref Movement /
    LinkTransfer cannot mask a dropped carry-budget LinkCarry). A carry-budget fact_ref
    NOT present in the spine LinkCarry source refs => RED.

    This guard READS claim_trace (allowed for a checker) and stays support-only: it
    JUDGES NOTHING about the budget — it only verifies COVERAGE (each recorded
    carry-budget fact was projected). It is not source truth, success / quality, or
    Movement authority. VACUOUS when carry_trace.json is absent or carries no
    carry-budget fact.
    """

    carry_facts = _load_link_trace_facts(building_root, CARRY_TRACE_FILE, violations)
    carry_budget_refs = [
        fact["fact_ref"]
        for fact in carry_facts
        if fact["fact_ref"].startswith(CARRY_BUDGET_FACT_PREFIX)
    ]
    if not carry_budget_refs:
        return
    # P2 FIX: demand a LinkCarry event SPECIFICALLY (not any per-step Link type). Using the
    # flat PER_STEP_LINK_TYPES source-ref set would let a dropped carry-budget LinkCarry be
    # MASKED by an unrelated Movement / LinkTransfer event that happens to carry the same
    # source_fact_ref (false-green). The projector stamps the carry-budget fact_ref as the
    # source_fact_ref of a LinkCarry event, so only LinkCarry refs count here.
    spine_source_refs = _spine_source_fact_refs_by_type(
        building_root, (LINK_CARRY_EVENT_TYPE,), violations
    )[LINK_CARRY_EVENT_TYPE]
    for fact_ref in carry_budget_refs:
        if fact_ref not in spine_source_refs:
            violations.append(
                f"{building_root}: u5_5_live spine projection DROPPED a building-scope "
                f"carry-budget Link event: claim_trace fact {fact_ref!r} (from "
                f"{CARRY_TRACE_FILE}) has no LinkCarry spine event whose source_fact_ref "
                "matches it in events/"
            )


def _spine_source_fact_refs_by_type(
    building_root: Path,
    event_types: tuple[str, ...],
    violations: list[str],
) -> dict[str, set[str]]:
    """Map each of ``event_types`` to the set of source_fact_refs it carries in events/.

    req-i helper: reads every ``evidence/spine/events/*.json`` body (the .json only —
    the .md is a pure render). For each body whose event_type is in ``event_types``,
    records its ``source_fact_ref`` against that event_type. A matching-type body with no
    string source_fact_ref is a malformed projection -> RED (and contributes nothing). A
    missing spine/events/ dir yields the empty-set-per-type map. Keyed BY event_type (not
    a flat set) so the gate-coverage check demands a LinkGateCheck ref distinctly from a
    LinkPolicyAction ref. (Same per-type shape as ``_spine_seam_source_fact_refs``.)
    """

    by_type: dict[str, set[str]] = {event_type: set() for event_type in event_types}
    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return by_type
    for event_path in sorted(events_dir.glob("*.json")):
        body = _load_event_body(event_path, violations)
        if body is None:
            continue
        event_type = body.get("event_type")
        if not isinstance(event_type, str) or event_type not in by_type:
            continue
        source_fact_ref = body.get("source_fact_ref")
        if not isinstance(source_fact_ref, str) or not source_fact_ref:
            violations.append(
                f"{event_path}: {event_type} spine event has no string "
                "source_fact_ref (req-i cannot correlate it to an executed step)"
            )
            continue
        by_type[event_type].add(source_fact_ref)
    return by_type


def _step_declares_gate_policy(step: object) -> bool:
    """True iff a declared-plan step has a Link row with a non-empty gate_sequence_policy.

    req-i helper: a step ``rows[]`` row with ``axis == "Link"`` carrying a NON-EMPTY
    LIST ``gate_sequence_policy`` means the step declared gates to evaluate. A step
    that is not a dict, has no list ``rows``, or has no such Link row declares no policy
    (False). An empty-list or non-list gate_sequence_policy is NOT a declared policy.
    """

    if not isinstance(step, dict):
        return False
    rows = step.get(STEP_ROWS_FIELD)
    if not isinstance(rows, list):
        return False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("axis") != LINK_AXIS:
            continue
        policy = row.get(GATE_SEQUENCE_POLICY_FIELD)
        if isinstance(policy, list) and policy:
            return True
    return False


def _edge_has_gate_policy(edge: object) -> bool:
    """True iff a declared graph link_edge has a row with a non-empty gate_sequence_policy.

    GUARD #6c (graph): a GRAPH plan's gate_sequence_policy lives on a link_edge row
    (``edge["rows"][i].gate_sequence_policy``), NOT on a brick_steps[].rows row. At run,
    plan_graph linearizes that edge's Link row onto the edge's SOURCE step, so the gate
    decisions are recorded under ``source_step_ref``. (An edge is a Link edge by
    construction, so a gate_sequence_policy on any of its rows is a Link policy — no axis
    check is required, mirroring how the runtime reads it.) The caller resolves + validates
    the source_step_ref separately so a policy edge with a MISSING source fails CLOSED (P3a)
    rather than being silently skipped.
    """

    if not isinstance(edge, dict):
        return False
    rows = edge.get("rows")
    if not isinstance(rows, list):
        return False
    return any(
        isinstance(row, dict)
        and isinstance(row.get(GATE_SEQUENCE_POLICY_FIELD), list)
        and row.get(GATE_SEQUENCE_POLICY_FIELD)
        for row in rows
    )


def _ref_suffix_matches_step(source_fact_ref: str, step_ref: str) -> bool:
    """True iff a spine source_fact_ref belongs to ``step_ref`` (slug suffix + no graph-edge).

    The SAME join req-e / the projector use: a per-step fact_ref endswith
    ``":" + slug(step_ref)`` and does NOT contain the per-edge ``:graph-edge:`` infix.
    Reuses ``_step_ref_slug`` so the gate-coverage match never disagrees with the rest of
    the file about which fact belongs to a step.
    """

    if GRAPH_EDGE_FACT_INFIX in source_fact_ref:
        return False
    return source_fact_ref.endswith(":" + _step_ref_slug(step_ref))


def validate_gate_sequence_coverage(building_root: Path, violations: list[str]) -> None:
    """req-i (GUARD #6c): an EXECUTED step that DECLARES gates recorded gate decisions.

    A step whose declared plan row (``axis == "Link"``) carries a NON-EMPTY
    ``gate_sequence_policy`` list declared gates to evaluate; if that step was also
    EXECUTED, its Link Gate evaluated those gates at run and the spine MUST carry at least
    one ``LinkGateCheck`` AND one ``LinkPolicyAction`` event for it. req-e only demands a
    Link spine event for a claim_trace fact that EXISTS, so a building that declared+ran a
    gate policy but recorded ZERO gate_receipt / policy_action facts (an incomplete spine)
    has nothing for req-e to demand and false-greens (fail-open). req-i closes that hole by
    anchoring the demand on the DECLARED policy, not the on-disk trace.

    For each EXECUTED declared step that declares a non-empty gate policy, it requires a
    LinkGateCheck event AND a LinkPolicyAction event whose ``source_fact_ref`` SUFFIX-matches
    the step via the SAME slug join the rest of the file uses (``":" + _step_ref_slug(step_ref)``,
    excluding ``:graph-edge:``). A missing LinkGateCheck OR missing LinkPolicyAction for such a
    step => RED naming the building, step_ref, and which event type is missing.

    Restricted to EXECUTED declared steps (intersection with ``_executed_step_refs``): a
    declared-but-never-run step never evaluated its gates (orphan-skip / not-run parity), so
    no demand. FAIL-CLOSED on an unreadable declared plan: matches the file's
    ``_declared_plan_step_refs`` pattern — appends a RED and returns (we cannot tell which
    steps declared gates; the run is already failing via the RED) rather than raising.

    This guard READS the declared plan (allowed for a checker) and stays support-only: it
    JUDGES NOTHING about the gate decisions — it only verifies COVERAGE (a declared+executed
    gate policy recorded its decisions). It is not source truth, success / quality, or
    Movement authority. VACUOUS when no executed step declares a gate policy.
    """

    try:
        declared_steps = _declared_plan_steps(building_root)
    except SpineProjectionError as exc:
        violations.append(
            f"{building_root}: u5_5_live building's declared plan could not be read to "
            f"check declared gate-sequence-policy coverage; failing closed ({exc})"
        )
        return
    gate_declaring_step_refs = {
        step["step_ref"]
        for step in declared_steps
        if _step_declares_gate_policy(step)
        and isinstance(step.get("step_ref"), str)
        and step.get("step_ref")
    }
    # FIX P1#2 (graph): a GRAPH plan's gate_sequence_policy lives on a link_edge row, NOT on
    # a brick_steps[].rows row, so the step-rows scan above misses it. Read link_edges and
    # add each gate-declaring edge's SOURCE step_ref (where plan_graph attributes the gate
    # decisions at run). FAIL-CLOSED on an unreadable link_edges (same pattern as the plan
    # read above) rather than silently missing a graph gate policy.
    try:
        link_edges = _declared_link_edges(building_root)
    except SpineProjectionError as exc:
        violations.append(
            f"{building_root}: u5_5_live building's declared link_edges could not be read to "
            f"check declared gate-sequence-policy coverage; failing closed ({exc})"
        )
        return
    for edge in link_edges:
        if not _edge_has_gate_policy(edge):
            continue
        source_step_ref = edge.get("source_step_ref") if isinstance(edge, dict) else None
        if isinstance(source_step_ref, str) and source_step_ref:
            gate_declaring_step_refs.add(source_step_ref)
        else:
            # P3a: a policy edge with no resolvable source step cannot be coverage-checked.
            # Graph admission rejects this shape, but fail CLOSED here rather than skip it.
            violations.append(
                f"{building_root}: a declared link_edge carries a non-empty "
                f"{GATE_SEQUENCE_POLICY_FIELD} but has no string source_step_ref; its "
                "gate-sequence coverage cannot be verified (failing closed)"
            )
    if not gate_declaring_step_refs:
        return
    executed_step_refs = _executed_step_refs(building_root, violations)
    required_step_refs = gate_declaring_step_refs & executed_step_refs
    if not required_step_refs:
        return
    by_type = _spine_source_fact_refs_by_type(
        building_root,
        (LINK_GATE_CHECK_EVENT_TYPE, LINK_POLICY_ACTION_EVENT_TYPE),
        violations,
    )
    for step_ref in sorted(required_step_refs):
        for event_type in (LINK_GATE_CHECK_EVENT_TYPE, LINK_POLICY_ACTION_EVENT_TYPE):
            if not any(
                _ref_suffix_matches_step(ref, step_ref)
                for ref in by_type.get(event_type, set())
            ):
                violations.append(
                    f"{building_root}: u5_5_live spine projection is missing a "
                    f"{event_type!r} event for executed step {step_ref!r}, which declares a "
                    f"non-empty {GATE_SEQUENCE_POLICY_FIELD} (a declared+executed gate policy "
                    "that produced no recorded gate decision is an incomplete spine)"
                )


def _spine_seam_source_fact_refs(
    building_root: Path,
    violations: list[str],
) -> dict[str, set[str]]:
    """Map each SEAM event_type to the set of source_fact_refs it carries in events/.

    The req-g analogue of ``_spine_source_fact_refs_by_type``: reads every
    ``evidence/spine/events/*.json`` body (the .json only — the .md is a pure render).
    For each body whose event_type is a SEAM_EVENT_TYPES (TransitionConcern /
    RouteRequest), records its ``source_fact_ref`` against that event_type. A seam-type
    body with no string source_fact_ref is a malformed projection -> RED (and contributes
    nothing). A missing spine/events/ dir yields an empty map (every demanded seam ref is
    then reported missing == RED — correct for a u5_5_live building that lost its events).

    Keyed by event_type (not a flat set) so the presence check demands a TransitionConcern
    ref resolve to a TransitionConcern event (not, e.g., a RouteRequest event that happened
    to share a ref) — the SAME kind-aware match req-f uses.
    """

    by_type: dict[str, set[str]] = {seam_type: set() for seam_type in SEAM_EVENT_TYPES}
    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return by_type
    for event_path in sorted(events_dir.glob("*.json")):
        body = _load_event_body(event_path, violations)
        if body is None:
            continue
        event_type = body.get("event_type")
        if not isinstance(event_type, str) or event_type not in SEAM_EVENT_TYPES:
            continue
        source_fact_ref = body.get("source_fact_ref")
        if not isinstance(source_fact_ref, str) or not source_fact_ref:
            violations.append(
                f"{event_path}: {event_type} spine event has no string "
                "source_fact_ref (req-g cannot correlate it to a raised seam file)"
            )
            continue
        by_type[event_type].add(source_fact_ref)
    return by_type


def validate_per_step_seam_coverage(building_root: Path, violations: list[str]) -> None:
    """req-g: every RAISED Agent->Link seam file has a matching seam spine event.

    The seam analogue of req-e. req-a/req-e cover the Brick/Agent rows and the Link
    claim_trace facts; the two Agent->Link SEAM files (transition-concern.json /
    route-request.json, written per attempt ONLY when the Agent raised one) had NO
    presence-coverage guard. req-f catches a seam ref ONLY when a Movement CITES it, so a
    seam RAISED-but-never-adopted (no movement adopts it) has no citing ref and req-f never
    demands it — a projector that silently DROPPED such a seam event passed GREEN, losing
    that Truth-Layer record. req-g closes that hole.

    For each ``work/step-outputs/*/`` attempt dir it reads the seam file(s) present
    (transition-concern.json / route-request.json), and for every seam file whose top-level
    ``step_ref`` is in the DECLARED plan (orphan-skip parity with the projector's
    _seam_event_specs_by_step — an orphan step-output's seam is NOT projected), it requires
    the spine ``events/`` to carry a seam spine event of the matching kind
    (TransitionConcern / RouteRequest) whose ``source_fact_ref`` EQUALS the file's own
    ref field (transition_concern_ref / route_request_ref — the SAME field the projector
    stamps as source_fact_ref). A raised+declared seam file with NO matching spine event is
    a dropped projection == RED.

    PRESENCE is per-file (PRESENT-WHEN-RAISED — zero-or-more per step): an absent seam file
    imposes no requirement. ORPHAN-SKIP: a seam file whose step_ref is NOT in the declared
    plan is skipped (the projector emits no event for it). FAIL-CLOSED: a present-but-corrupt
    seam file (unreadable / non-JSON / non-object / missing its ref field / non-string /
    non-string step_ref) appends its own RED (the run is already failing). VACUOUS when
    there is no step-outputs dir or no seam file was raised.

    This guard READS the on-disk seam files (allowed for a checker) and stays support-only:
    it JUDGES NOTHING about the seam content — it only verifies COVERAGE (each raised+declared
    seam was projected). It is not source truth, success / quality, or Movement authority.
    """

    step_outputs_dir = building_root / "work" / "step-outputs"
    if not step_outputs_dir.is_dir():
        return
    # ORPHAN-SKIP (parity with the projector + req-a/req-e): the projector projects a seam
    # event ONLY for a seam file whose top-level step_ref is in the declared plan. Require
    # coverage ONLY for declared steps. FAIL-CLOSED on an unreadable declared plan (None =>
    # the RED is already appended; skip rather than demand it of every / no seam).
    declared_step_refs = _declared_plan_step_refs(building_root, violations)
    if declared_step_refs is None:
        return
    spine_seam_refs = _spine_seam_source_fact_refs(building_root, violations)
    for attempt_dir in sorted(p for p in step_outputs_dir.iterdir() if p.is_dir()):
        for seam_file_name, seam_event_type, ref_field in SEAM_FILE_SPECS:
            seam_path = attempt_dir / seam_file_name
            if not seam_path.is_file():
                # PRESENT-WHEN-RAISED: an absent seam file imposes no requirement.
                continue
            # Reuse the SAME fail-closed body load the event bodies use (non-finite
            # rejected). A parse failure / non-object body already appends its own RED.
            seam_body = _load_event_body(seam_path, violations)
            if seam_body is None:
                continue
            # The seam file's top-level step_ref is what the projector groups by; a
            # non-string step_ref means the projector could not attribute it to a step
            # (it is skipped there). Treat it as a corrupt-source RED (the projector would
            # have emitted nothing, but a real raised seam always carries a string step_ref).
            step_ref = seam_body.get(SEAM_STEP_REF_FIELD)
            if not isinstance(step_ref, str) or not step_ref:
                violations.append(
                    f"{seam_path}: raised seam file has no string {SEAM_STEP_REF_FIELD!r} "
                    "(req-g cannot attribute it to an executed step)"
                )
                continue
            if step_ref not in declared_step_refs:
                # ORPHAN: the projector skips this seam (orphan-skip parity); no demand.
                continue
            # The file's own ref field IS the projected event's source_fact_ref + delta key
            # (the SAME field the projector stamps). A seam file lacking it is corrupt source
            # — the projector would RAISE on it; here it is a RED (we cannot verify coverage).
            source_fact_ref = seam_body.get(ref_field)
            if not isinstance(source_fact_ref, str) or not source_fact_ref:
                violations.append(
                    f"{seam_path}: raised seam file has no string {ref_field!r} "
                    "(req-g cannot correlate it to a seam spine event)"
                )
                continue
            if source_fact_ref not in spine_seam_refs.get(seam_event_type, set()):
                violations.append(
                    f"{building_root}: u5_5_live spine projection DROPPED a raised "
                    f"Agent->Link seam event for declared step {step_ref!r}: seam file "
                    f"{seam_path} ({ref_field}={source_fact_ref!r}) has no projected "
                    f"{seam_event_type!r} spine event whose source_fact_ref matches it in "
                    "events/"
                )


MOVEMENT_EVENT_TYPE = "Movement"

# SINGLE-SOURCE DRIFT GUARD (fail LOUD at module load): the Movement event_type
# literal the value-guard keys on MUST be an admitted spine event_type. The writer
# is the single source of the admitted set (SPINE_EVENT_TYPES); if this literal
# ever drifts out of that set (a typo, e.g. an accidental "...Event" suffix), the
# guard would silently recognize ZERO real movement events => a malformed movement
# passes GREEN. An explicit raise (NOT a bare assert — assert is stripped under
# python -O) turns that class of typo into a load-time crash instead of a false-green.
if MOVEMENT_EVENT_TYPE not in SPINE_EVENT_TYPES:
    raise RuntimeError(
        f"MOVEMENT_EVENT_TYPE {MOVEMENT_EVENT_TYPE!r} not in SPINE_EVENT_TYPES — "
        "checker/writer event-type drift"
    )


def validate_movement_events(building_root: Path, violations: list[str]) -> None:
    """Movement-value guard: every recorded Movement event is well-formed (req-c).

    GUARD-FIRST: the Movement projector is a LATER increment. Zero buildings
    emit Movement events today, so on real disk this guard is additive + vacuous
    (no Movement file => no requirement => existing buildings stay green); it
    will RED a future malformed movement the moment one is projected.

    For every ``evidence/spine/events/*.json`` whose BODY event_type is
    ``Movement`` (the .json only — the .md is a pure render), ALL must hold:
      1. ``declared_movement`` is a STRING in MOVEMENT_LITERALS (Link-owned,
         ('forward','reroute')); 'hold'/'next' (LinkPolicyAction, not Movement),
         absent, or non-string => RED.
      2. ``gate_review_event_ref`` is a NON-EMPTY string (every movement must cite
         the gate review that authorized it); absent/empty/non-string => RED.
      3. NO forbidden key anywhere in the body (reusing the writer's single-source
         scanner); a raw ``movement`` / ``target`` / ``target_ref`` key
         (the body must use ``declared_movement`` / ``target_boundary_ref``) => RED.
      4. SPOOF guard: filename type and body type must AGREE about being a
         ``Movement`` event — a ``Movement`` filename with a non-movement body, or a
         movement body under a non-``Movement`` filename (XOR), => RED.
      5. Agent->Link seam-ref fields, WHEN PRESENT, are well-TYPED:
         ``adopted_transition_concern_refs`` / ``not_adopted_transition_concern_refs``
         must each be a LIST of non-empty strings, and ``route_request_ref`` a non-empty
         string. A malformed type (a concern-refs STRING, a route_request_ref INT, a
         list with a non-string entry, ...) => RED here (fail-closed), so req-f's
         resolution pass — which only descends into well-typed values — never silently
         skips it. ABSENT is fine (a Movement may adopt no concern / request no route).

    FAIL-CLOSED: a movement file whose body is missing/unparseable/non-object (via
    the shared ``_load_event_body``, which also REJECTs NaN/Infinity) is already a
    RED there; this never silently skips a malformed movement without a RED. A
    missing spine/events/ dir yields no movement files => no requirement.

    This guard checks the STRUCTURE/VALUE of a recorded movement FACT; it does NOT
    decide movement and is not Movement authority.
    """

    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return
    for event_path in sorted(events_dir.glob("*.json")):
        filename_type = _filename_event_type(event_path)
        # Load the body fail-closed. _load_event_body appends its own RED on a
        # parse failure / non-object body (incl. NaN/Infinity) and returns None.
        body = _load_event_body(event_path, violations)
        body_type = body.get("event_type") if isinstance(body, dict) else None
        is_movement_filename = filename_type == MOVEMENT_EVENT_TYPE
        is_movement_body = body_type == MOVEMENT_EVENT_TYPE
        # (4) SPOOF guard: filename and body must AGREE about being a Movement event.
        # XOR => one side hides/relabels a movement; RED. (A body that failed to
        # load is None here, so a Movement filename with an unloadable body
        # still trips the XOR in addition to the load RED.)
        if is_movement_filename != is_movement_body:
            violations.append(
                f"{event_path}: Movement event identity spoof — filename declares "
                f"{filename_type!r}, body declares {body_type!r}; exactly one is "
                f"{MOVEMENT_EVENT_TYPE!r}"
            )
        # Only enforce the value rules on a body that genuinely IS a Movement event.
        if not is_movement_body:
            continue
        # (1) declared_movement is a string in the Link-owned Movement literals.
        declared_movement = body.get("declared_movement")
        if not isinstance(declared_movement, str) or declared_movement not in MOVEMENT_LITERALS:
            violations.append(
                f"{event_path}: Movement event declared_movement must be one of "
                f"{MOVEMENT_LITERALS!r}; got {declared_movement!r}"
            )
        # (2) gate_review_event_ref is a non-empty string citing the gate review.
        gate_review_event_ref = body.get("gate_review_event_ref")
        if not isinstance(gate_review_event_ref, str) or not gate_review_event_ref:
            violations.append(
                f"{event_path}: Movement event gate_review_event_ref must be a "
                f"non-empty string citing the authorizing gate review; got "
                f"{gate_review_event_ref!r}"
            )
        # (3) no forbidden key anywhere in the body (raw movement/target/target_ref).
        forbidden = _forbidden_keys_in_body(body)
        if forbidden:
            violations.append(
                f"{event_path}: Movement event body carries forbidden key(s) "
                f"{sorted(forbidden)!r}; the projected body must use "
                f"declared_movement / target_boundary_ref, never the originals"
            )
        # (5) Agent->Link seam-ref fields, when PRESENT, must be well-TYPED (a malformed
        # type must fail closed here, never be silently skipped by req-f's resolution
        # pass — which only descends into well-typed values). ABSENT is fine (a Movement
        # may adopt no concern / request no route).
        #   * adopted_/not_adopted_transition_concern_refs: a LIST of non-empty strings.
        #   * route_request_ref: a non-empty string.
        for concern_key in MOVEMENT_ADOPTED_CONCERN_REFS_KEYS:
            if concern_key not in body:
                continue
            concern_refs = body.get(concern_key)
            if not isinstance(concern_refs, list):
                violations.append(
                    f"{event_path}: Movement event {concern_key!r} must be a list of "
                    f"non-empty strings when present; got {concern_refs!r}"
                )
                continue
            for entry in concern_refs:
                if not isinstance(entry, str) or not entry:
                    violations.append(
                        f"{event_path}: Movement event {concern_key!r} entry must be a "
                        f"non-empty string; got {entry!r}"
                    )
        if MOVEMENT_ROUTE_REQUEST_REF_KEY in body:
            route_request_ref = body.get(MOVEMENT_ROUTE_REQUEST_REF_KEY)
            if not isinstance(route_request_ref, str) or not route_request_ref:
                violations.append(
                    f"{event_path}: Movement event {MOVEMENT_ROUTE_REQUEST_REF_KEY!r} must "
                    f"be a non-empty string when present; got {route_request_ref!r}"
                )


FRONTIER_EVENT_TYPE = "Frontier"
RESUME_DISPOSITION_EVENT_TYPE = "ResumeDisposition"

# SINGLE-SOURCE DRIFT GUARDS (fail LOUD at module load): each terminal event_type
# literal the value-guard keys on MUST be an admitted spine event_type. The writer
# is the single source of the admitted set (SPINE_EVENT_TYPES); if either literal
# ever drifts out of that set (a typo, e.g. an accidental "...Event" suffix), the
# guard would silently recognize ZERO real terminal events => a malformed Frontier /
# ResumeDisposition passes GREEN. An explicit raise (NOT a bare assert — assert is
# stripped under python -O) turns that class of typo into a load-time crash instead
# of a false-green. Same pattern as MOVEMENT_EVENT_TYPE above.
if FRONTIER_EVENT_TYPE not in SPINE_EVENT_TYPES:
    raise RuntimeError(
        f"FRONTIER_EVENT_TYPE {FRONTIER_EVENT_TYPE!r} not in SPINE_EVENT_TYPES — "
        "checker/writer event-type drift"
    )
if RESUME_DISPOSITION_EVENT_TYPE not in SPINE_EVENT_TYPES:
    raise RuntimeError(
        f"RESUME_DISPOSITION_EVENT_TYPE {RESUME_DISPOSITION_EVENT_TYPE!r} not in "
        "SPINE_EVENT_TYPES — checker/writer event-type drift"
    )

# TERMINAL-BODY SHAPE (F3): the load-bearing fields a well-formed terminal body MUST
# carry — MIRRORS the fields the projector's fail-closed builders emit
# (_frontier_event_body copies _FRONTIER_FIELDS; _resume_disposition_event_body copies
# _RESUME_DISPOSITION_FIELDS + stamps resume_ordinal). They are REPLICATED inline here
# (same pattern as the req-c Movement guard, which replicates declared_movement /
# gate_review_event_ref inline rather than importing the projector) so a sparse body
# from a future buggy projector RED-s instead of false-greening. The drift risk is
# bounded: a projector that stops emitting one of these names breaks its real-building
# projection (covered by the confirming pass), and the value enums (frontier_kind /
# disposition_action) are still single-sourced from their owning modules above.
#
# Field-kind split: the enum fields (frontier_kind / disposition_action) are already
# value-checked below against their owning-module literals; these sets add the REMAINING
# load-bearing fields, typed.
#   * Frontier (besides frontier_kind): frontier_reason (non-empty string),
#     observed_counts (object).
#   * ResumeDisposition (besides disposition_action): resumed_from / paused_at_ref /
#     pending_target_ref (non-empty strings) + resume_ordinal (int — the F1 key field).
_FRONTIER_REQUIRED_STRING_FIELDS = ("frontier_reason",)
_FRONTIER_REQUIRED_OBJECT_FIELDS = ("observed_counts",)
_RESUME_DISPOSITION_REQUIRED_STRING_FIELDS = (
    "resumed_from",
    "paused_at_ref",
    "pending_target_ref",
)
_RESUME_DISPOSITION_REQUIRED_INT_FIELDS = ("resume_ordinal",)


def validate_frontier_and_resume_disposition(
    building_root: Path,
    violations: list[str],
) -> None:
    """Terminal-value + cardinality guard for Frontier / ResumeDisposition (req-d).

    GUARD-FIRST: the Frontier / ResumeDisposition projector is a LATER increment
    (INC-5). Zero buildings emit these terminal events today, so on real disk this
    guard is additive + vacuous (no Frontier / ResumeDisposition file => no
    requirement => existing buildings stay green); it will RED a future malformed
    terminal event the moment one is projected.

    This does NOT require PRESENCE: a building with no Frontier event yet is fine.
    The "a closed building MUST carry a Frontier" presence requirement is DEFERRED
    to when the INC-5 projector defines "closed". The guard only fires on terminal
    events that EXIST.

    For every ``evidence/spine/events/*.json`` (the .json only — the .md is a pure
    render of the same body), per terminal type:

      SPOOF guard (BOTH terminal types): filename type and body type must AGREE
      about being that terminal event — a ``Frontier`` filename with a non-Frontier
      body, or a Frontier body under a non-``Frontier`` filename (XOR), => RED; same
      for ``ResumeDisposition``.

      If the BODY event_type is ``Frontier``:
        1. ``frontier_kind`` is a STRING in FRONTIER_KINDS (the operator-observer's
           single-source six literals); absent / non-string / unknown => RED. NOTE:
           ``"complete"`` is a LEGAL frontier_kind VALUE and must pass.
        2. SHAPE (F3): the remaining load-bearing Frontier fields the projector emits
           are present + well-typed — ``frontier_reason`` is a non-empty STRING and
           ``observed_counts`` is an OBJECT; absent / wrong-type => RED. (Mirrors
           _frontier_event_body's _FRONTIER_FIELDS so a SPARSE body cannot false-green.)
        3. NO forbidden key anywhere in the body (the writer's single-source
           scanner). The forbidden rule is KEY-only, so a frontier_kind VALUE of
           ``"complete"`` does NOT trip it.

      If the BODY event_type is ``ResumeDisposition``:
        1. ``disposition_action`` is a STRING in DISPOSITION_ACTIONS (Link's
           single-source ('raise','forward','stop')); absent / non-string /
           unknown => RED.
        2. SHAPE (F3): the remaining load-bearing ResumeDisposition fields the
           projector emits are present + well-typed — ``resumed_from`` /
           ``paused_at_ref`` / ``pending_target_ref`` are non-empty STRINGS and
           ``resume_ordinal`` (the F1 delta-key disambiguator) is an INT (bool, an int
           subclass, is rejected); absent / wrong-type => RED. (Mirrors
           _resume_disposition_event_body's emitted fields so a SPARSE body cannot
           false-green.)
        3. NO forbidden key anywhere in the body.

      CARDINALITY: at most ONE ``Frontier`` event per building — the frontier is the
      unique terminal observation; two-or-more => RED. ``ResumeDisposition`` has NO
      cardinality limit (zero-or-more — a building may resume multiple times).

    FAIL-CLOSED: a terminal event whose body is missing/unparseable/non-object (via
    the shared ``_load_event_body``, which also REJECTs NaN/Infinity) is already a
    RED there; this never silently skips a malformed terminal event without a RED. A
    missing spine/events/ dir yields no terminal files => no requirement.

    This guard checks the STRUCTURE/VALUE of a recorded terminal FACT; it judges
    nothing about the building's content and is not Movement / Quality authority.
    """

    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return
    frontier_count = 0
    for event_path in sorted(events_dir.glob("*.json")):
        filename_type = _filename_event_type(event_path)
        # Load the body fail-closed. _load_event_body appends its own RED on a
        # parse failure / non-object body (incl. NaN/Infinity) and returns None.
        body = _load_event_body(event_path, violations)
        body_type = body.get("event_type") if isinstance(body, dict) else None

        # SPOOF guard for EACH terminal type: filename and body must AGREE about
        # being that terminal event. XOR => one side hides/relabels it; RED. (A body
        # that failed to load is None here, so a terminal filename with an unloadable
        # body still trips the XOR in addition to the load RED.)
        for terminal_type in (FRONTIER_EVENT_TYPE, RESUME_DISPOSITION_EVENT_TYPE):
            if (filename_type == terminal_type) != (body_type == terminal_type):
                violations.append(
                    f"{event_path}: {terminal_type} event identity spoof — filename "
                    f"declares {filename_type!r}, body declares {body_type!r}; "
                    f"exactly one is {terminal_type!r}"
                )

        if body_type == FRONTIER_EVENT_TYPE:
            frontier_count += 1
            # (1) frontier_kind is a string in the observer-owned literals.
            frontier_kind = body.get("frontier_kind")
            if not isinstance(frontier_kind, str) or frontier_kind not in FRONTIER_KINDS:
                violations.append(
                    f"{event_path}: Frontier event frontier_kind must be one of "
                    f"{FRONTIER_KINDS!r}; got {frontier_kind!r}"
                )
            # (2) SHAPE (F3): the remaining load-bearing Frontier fields the projector
            # emits must be present + well-typed (a sparse body false-greens otherwise).
            for field in _FRONTIER_REQUIRED_STRING_FIELDS:
                value = body.get(field)
                if not isinstance(value, str) or not value:
                    violations.append(
                        f"{event_path}: Frontier event {field!r} must be a non-empty "
                        f"string; got {value!r}"
                    )
            for field in _FRONTIER_REQUIRED_OBJECT_FIELDS:
                value = body.get(field)
                if not isinstance(value, dict):
                    violations.append(
                        f"{event_path}: Frontier event {field!r} must be an object; "
                        f"got {value!r}"
                    )
            # (3) no forbidden key anywhere in the body (KEY-only rule).
            forbidden = _forbidden_keys_in_body(body)
            if forbidden:
                violations.append(
                    f"{event_path}: Frontier event body carries forbidden key(s) "
                    f"{sorted(forbidden)!r}"
                )
        elif body_type == RESUME_DISPOSITION_EVENT_TYPE:
            # (1) disposition_action is a string in Link's owned literals.
            disposition_action = body.get("disposition_action")
            if (
                not isinstance(disposition_action, str)
                or disposition_action not in DISPOSITION_ACTIONS
            ):
                violations.append(
                    f"{event_path}: ResumeDisposition event disposition_action must "
                    f"be one of {DISPOSITION_ACTIONS!r}; got {disposition_action!r}"
                )
            # (2) SHAPE (F3): the remaining load-bearing ResumeDisposition fields the
            # projector emits must be present + well-typed. resume_ordinal (the F1
            # delta-key disambiguator) is an int; bool is an int subclass and is NOT a
            # valid ordinal, so reject it.
            for field in _RESUME_DISPOSITION_REQUIRED_STRING_FIELDS:
                value = body.get(field)
                if not isinstance(value, str) or not value:
                    violations.append(
                        f"{event_path}: ResumeDisposition event {field!r} must be a "
                        f"non-empty string; got {value!r}"
                    )
            for field in _RESUME_DISPOSITION_REQUIRED_INT_FIELDS:
                value = body.get(field)
                if not isinstance(value, int) or isinstance(value, bool):
                    violations.append(
                        f"{event_path}: ResumeDisposition event {field!r} must be an "
                        f"int; got {value!r}"
                    )
            # (3) no forbidden key anywhere in the body (KEY-only rule).
            forbidden = _forbidden_keys_in_body(body)
            if forbidden:
                violations.append(
                    f"{event_path}: ResumeDisposition event body carries forbidden "
                    f"key(s) {sorted(forbidden)!r}"
                )

    # CARDINALITY: the Frontier terminal observation is unique per building.
    # ResumeDisposition is intentionally NOT bounded (zero-or-more resumes).
    if frontier_count > 1:
        violations.append(
            f"{building_root}: u5_5_live spine projection has {frontier_count} "
            f"{FRONTIER_EVENT_TYPE!r} events (expected at most one — the frontier "
            "terminal observation is unique per building)"
        )


# SINGLE-SOURCE DRIFT GUARDS (fail LOUD at module load): each event_type literal req-f
# keys on MUST be an admitted spine event_type. If one ever drifts out of SPINE_EVENT_TYPES
# (a typo), req-f would silently build an index/demand over ZERO real events => a dangling
# ref passes GREEN. An explicit raise (NOT a bare assert — stripped under python -O) turns
# that typo into a load-time crash instead of a false-green (same pattern as the Movement /
# terminal guards above).
for _req_f_event_type in (
    MOVEMENT_EVENT_TYPE,
    SUFFICIENCY_EVENT_TYPE,
    BRICK_COMPARED_EVENT_TYPE,
    TRANSITION_CONCERN_EVENT_TYPE,
    ROUTE_REQUEST_EVENT_TYPE,
):
    if _req_f_event_type not in SPINE_EVENT_TYPES:
        raise RuntimeError(
            f"req-f event_type {_req_f_event_type!r} not in SPINE_EVENT_TYPES — "
            "checker/writer event-type drift"
        )

# SINGLE-SOURCE DRIFT GUARD (fail LOUD at module load): each seam event_type literal req-g
# keys on MUST be an admitted spine event_type. If one ever drifts out of SPINE_EVENT_TYPES
# (a typo), req-g would index ZERO real seam events => a DROPPED seam event passes GREEN.
# An explicit raise (NOT a bare assert — stripped under python -O) turns that typo into a
# load-time crash instead of a false-green (same pattern as the req-f guard above).
for _req_g_event_type in SEAM_EVENT_TYPES:
    if _req_g_event_type not in SPINE_EVENT_TYPES:
        raise RuntimeError(
            f"req-g seam event_type {_req_g_event_type!r} not in SPINE_EVENT_TYPES — "
            "checker/writer event-type drift"
        )


def _build_resolvable_ref_index(
    building_root: Path,
    violations: list[str],
) -> dict[str, set[str]]:
    """Map each RESOLVABLE ref -> the set of projected event_types that provide it (req-f).

    Reads every ``evidence/spine/events/*.json`` body (the .json only — the .md is a pure
    render). For each body it records, against the body's event_type, both:
      * its ``source_fact_ref`` (the canonical handle), and
      * each entry in its ``alias_fact_refs`` list (the building-scoped alias a
        BrickCompared records, or the inner concern_ref a TransitionConcern records).
    A ref a Movement / LinkSufficiency cites RESOLVES iff this index maps it to an event of
    the demanded KIND. Building the index over BOTH ref handles is what closes the alias /
    typo-alias_for hostile cases (req-f b) and the inner-concern_ref seam case (req-f c).

    Defensive: a body that fails to load contributes nothing (it already RED-s elsewhere);
    a non-string / empty alias entry is skipped (it cannot resolve anything). A missing
    spine/events/ dir yields an empty index (every demanded ref then dangles == RED — the
    correct behavior for a u5_5_live building that lost its events).
    """

    index: dict[str, set[str]] = {}
    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return index
    for event_path in sorted(events_dir.glob("*.json")):
        body = _load_event_body(event_path, violations)
        if body is None:
            continue
        event_type = body.get("event_type")
        if not isinstance(event_type, str) or not event_type:
            continue
        source_fact_ref = body.get(EVENT_SOURCE_FACT_REF_KEY)
        if isinstance(source_fact_ref, str) and source_fact_ref:
            index.setdefault(source_fact_ref, set()).add(event_type)
        alias_fact_refs = body.get(EVENT_ALIAS_FACT_REFS_KEY)
        if isinstance(alias_fact_refs, list):
            for alias in alias_fact_refs:
                if isinstance(alias, str) and alias:
                    index.setdefault(alias, set()).add(event_type)
    return index


def _ref_resolves(index: dict[str, set[str]], ref: str, expected_type: str) -> bool:
    """True iff ``ref`` resolves to a projected event of ``expected_type`` in the index."""

    return expected_type in index.get(ref, set())


def validate_ref_integrity(building_root: Path, violations: list[str]) -> None:
    """req-f: every cross-event ref RESOLVES to a projected event of the right KIND.

    The audit's missing "no-dangle checker rule": req-a/req-e prove per-step COVERAGE
    (the right events EXIST), but a Movement could cite a non-existent sufficiency ordinal,
    a LinkSufficiency could check a brick-comparison alias that was never projected, or a
    Movement could adopt a transition-concern ref with no projected TransitionConcern — all
    of which pass coverage yet leave a DANGLING ref. req-f closes that hole.

    Builds the resolvable-ref index (every projected event's source_fact_ref +
    alias_fact_refs) and asserts, for the building's projected spine events:
      (a) every Movement ``gate_review_event_ref`` resolves to a projected LinkSufficiency
          event (its source_fact_ref) — closes the "non-existent sufficiency ordinal" case.
      (b) every LinkSufficiency ``checked_public_fact`` that is a brick-comparison ref
          (prefix ``brick-comparison:``) resolves to a projected BrickCompared event by
          source_fact_ref OR an alias_fact_refs entry — closes alias-dangling + typo
          alias_for. Non-brick-comparison checked facts are NOT demanded (out of scope).
      (c) every Movement ``adopted_transition_concern_refs`` /
          ``not_adopted_transition_concern_refs`` entry resolves to a projected
          TransitionConcern event, and ``route_request_ref`` (if present) resolves to a
          projected RouteRequest event — closes the dangling Agent->Link seam.

    An unresolved ref => RED naming the citing event + the dangling ref + the demanded kind.

    Support-only: this judges NOTHING (pure ref-integrity over the projected events). It is
    fail-closed (a body that fails to load already RED-s) and VACUOUS when the building has
    none of these citing events / refs (a building with no Movement / LinkSufficiency
    imposes no req-f demand). A missing spine/events/ dir yields an empty index, so any
    demanded ref dangles == RED — correct for a u5_5_live building that lost its events.
    """

    events_dir = building_root / "evidence" / "spine" / "events"
    if not events_dir.is_dir():
        return
    index = _build_resolvable_ref_index(building_root, violations)
    for event_path in sorted(events_dir.glob("*.json")):
        body = _load_event_body(event_path, violations)
        if body is None:
            continue
        event_type = body.get("event_type")
        if not isinstance(event_type, str) or not event_type:
            continue

        if event_type == MOVEMENT_EVENT_TYPE:
            # (a) the authorizing gate review must resolve to a LinkSufficiency.
            gate_review_ref = body.get(MOVEMENT_GATE_REVIEW_REF_KEY)
            if isinstance(gate_review_ref, str) and gate_review_ref:
                if not _ref_resolves(index, gate_review_ref, SUFFICIENCY_EVENT_TYPE):
                    violations.append(
                        f"{event_path}: Movement event {MOVEMENT_GATE_REVIEW_REF_KEY!r} "
                        f"{gate_review_ref!r} does not resolve to a projected "
                        f"{SUFFICIENCY_EVENT_TYPE!r} event (dangling gate-review ref)"
                    )
            # (c) the adopted / not-adopted transition-concern refs must each resolve to a
            # TransitionConcern, and any route_request_ref to a RouteRequest. A MALFORMED
            # type of any of these seam-ref fields is RED'd fail-closed by req-c
            # (validate_movement_events rule 5); this resolution pass only descends into
            # well-typed values (a non-list / non-string skip here is therefore safe — the
            # malformation has already produced a RED, it is not silently dropped).
            for concern_key in MOVEMENT_ADOPTED_CONCERN_REFS_KEYS:
                concern_refs = body.get(concern_key)
                if not isinstance(concern_refs, list):
                    continue
                for concern_ref in concern_refs:
                    if not isinstance(concern_ref, str) or not concern_ref:
                        continue
                    if not _ref_resolves(
                        index, concern_ref, TRANSITION_CONCERN_EVENT_TYPE
                    ):
                        violations.append(
                            f"{event_path}: Movement event {concern_key!r} entry "
                            f"{concern_ref!r} does not resolve to a projected "
                            f"{TRANSITION_CONCERN_EVENT_TYPE!r} event (dangling "
                            "Agent->Link seam ref)"
                        )
            route_request_ref = body.get(MOVEMENT_ROUTE_REQUEST_REF_KEY)
            if isinstance(route_request_ref, str) and route_request_ref:
                if not _ref_resolves(
                    index, route_request_ref, ROUTE_REQUEST_EVENT_TYPE
                ):
                    violations.append(
                        f"{event_path}: Movement event {MOVEMENT_ROUTE_REQUEST_REF_KEY!r} "
                        f"{route_request_ref!r} does not resolve to a projected "
                        f"{ROUTE_REQUEST_EVENT_TYPE!r} event (dangling Agent->Link seam ref)"
                    )

        elif event_type == SUFFICIENCY_EVENT_TYPE:
            # (b) a checked_public_fact citing a brick-comparison must resolve to a
            # BrickCompared (by source_fact_ref OR an alias_fact_refs entry). Other checked
            # public facts (e.g. an agent-fact) are not BrickCompared's concern.
            checked_public_fact = body.get(SUFFICIENCY_CHECKED_PUBLIC_FACT_KEY)
            if (
                isinstance(checked_public_fact, str)
                and checked_public_fact.startswith(BRICK_COMPARISON_FACT_PREFIX)
            ):
                if not _ref_resolves(
                    index, checked_public_fact, BRICK_COMPARED_EVENT_TYPE
                ):
                    violations.append(
                        f"{event_path}: LinkSufficiency event "
                        f"{SUFFICIENCY_CHECKED_PUBLIC_FACT_KEY!r} {checked_public_fact!r} "
                        f"does not resolve to a projected {BRICK_COMPARED_EVENT_TYPE!r} "
                        "event (dangling brick-comparison ref)"
                    )


def validate_projection(building_root: Path, violations: list[str]) -> None:
    """Validate one u5_5_live building's spine PROJECTION coverage.

    TWO assertions, both run for every u5_5_live building (either failing => RED):
      * req-b (building-scope declarations): each declaration type
        (PresetExpansion, LinkLaunchPolicy) appears EXACTLY ONCE in events/.
        Zero => the projection dropped a required declaration (RED); two-or-more
        => it duplicated it (RED). One RED per failing type.
      * req-a (per-step coverage): each EXECUTED step (work/step-outputs/) has at
        least one BrickInput + AgentBinding + AgentReturn carrying its step_ref in
        events/ — see ``validate_per_step_coverage``.
      * req-e (per-step LINK coverage): each per-step claim_trace LINK fact (read from
        evidence/claim_trace/link/*.json, filtered to the executed step via the SAME
        slug join + ``:graph-edge:`` exclusion the projector uses, present + absence
        alike) has a matching Link spine event whose source_fact_ref equals its
        fact_ref. A trace fact with NO corresponding spine event => RED (a dropped Link
        projection) — see ``validate_per_step_link_coverage``. Tolerant of absent E1
        traces (gate_receipt / policy_action) and vacuous when there is no executed
        step or no claim_trace.
      * req-g (per-step SEAM coverage): each RAISED Agent->Link seam file
        (work/step-outputs/*/{transition-concern,route-request}.json — PRESENT-WHEN-RAISED)
        whose top-level step_ref is in the DECLARED plan has a matching seam spine event
        (TransitionConcern / RouteRequest) whose source_fact_ref equals the file's own ref
        field. A raised+declared seam file with NO matching spine event => RED (a dropped
        seam projection — req-f catches a seam ref only when a Movement CITES it, so a seam
        raised-but-never-adopted needs this independent presence guard) — see
        ``validate_per_step_seam_coverage``. Orphan-skip parity with the projector; vacuous
        when no seam file was raised.
      * req-c (Movement-value): every recorded Movement event body is well-formed
        (declared_movement in the Link Movement literals, a non-empty
        gate_review_event_ref, no forbidden key, filename/body type agree) — see
        ``validate_movement_events``. Additive + vacuous until a Movement event is
        projected.
      * req-d (terminal Frontier / ResumeDisposition value + SHAPE + cardinality):
        every recorded Frontier event has a frontier_kind in the observer's
        FRONTIER_KINDS plus its load-bearing shape (frontier_reason / observed_counts),
        every recorded ResumeDisposition event has a disposition_action in Link's
        DISPOSITION_ACTIONS plus its load-bearing shape (resumed_from / paused_at_ref /
        pending_target_ref / resume_ordinal), neither carries a forbidden key,
        filename/body type agree, and at most one Frontier event exists
        (ResumeDisposition is zero-or-more) — see
        ``validate_frontier_and_resume_disposition``. PRESENCE is NOT required
        (guard-first); additive + vacuous until a terminal event is projected.
      * req-f (cross-event ref INTEGRITY / no-dangle): every Movement
        gate_review_event_ref resolves to a projected LinkSufficiency, every
        LinkSufficiency checked_public_fact that is a brick-comparison ref resolves to a
        projected BrickCompared (by source_fact_ref or an alias_fact_refs entry), and
        every Movement adopted/not_adopted_transition_concern_refs entry resolves to a
        projected TransitionConcern + any route_request_ref to a projected RouteRequest —
        an unresolved ref => RED. See ``validate_ref_integrity``. Vacuous when the building
        has none of these citing events / refs.
    """

    counts = _building_scope_type_counts(building_root, violations)
    for declaration_type in BUILDING_SCOPE_DECLARATION_TYPES:
        count = counts.get(declaration_type, 0)
        if count == 0:
            violations.append(
                f"{building_root}: u5_5_live spine projection is missing the "
                f"building-scope declaration event {declaration_type!r} "
                "(expected exactly one in events/)"
            )
        elif count > 1:
            violations.append(
                f"{building_root}: u5_5_live spine projection has {count} "
                f"{declaration_type!r} building-scope declaration events "
                "(expected exactly one in events/)"
            )
    validate_per_step_coverage(building_root, violations)
    validate_per_step_link_coverage(building_root, violations)
    validate_per_step_seam_coverage(building_root, violations)
    validate_carry_budget_coverage(building_root, violations)
    validate_gate_sequence_coverage(building_root, violations)
    validate_movement_events(building_root, violations)
    validate_frontier_and_resume_disposition(building_root, violations)
    validate_ref_integrity(building_root, violations)


def _should_inspect_building(building_root: Path, violations: list[str]) -> bool:
    """Decide whether to inspect a building, FAILING CLOSED on a corrupt manifest.

    The shared gate ``building_root_is_u5_5_live`` returns False for a
    present-but-unparseable / non-dict manifest, so such a building would be
    silently SKIPPED (a present-but-broken manifest must not be a free pass). This
    LOCAL pre-check (it does NOT modify the shared gate) closes that hole:

      (1) if ``evidence/evidence-manifest.json`` EXISTS but is unparseable JSON or
          not a dict -> append a RED and return False (DO-NOT-INSPECT, but the run
          is already RED via the appended violation);
      (2) otherwise defer the live decision to ``building_root_is_u5_5_live`` -> an
          ABSENT manifest, or a VALID-but-not-live manifest, SKIPs exactly as today
          (so the 154 existing buildings with valid-or-absent manifests stay green).

    Returns True iff the building should be inspected (valid + live).
    """

    manifest_path = building_root / "evidence" / "evidence-manifest.json"
    # (B1) Manifest path EXISTS but is not a plain file (e.g. a directory): we
    # cannot read it as a manifest, so its liveness is undeterminable -> fail
    # closed. Checked BEFORE the is_file() read branch (a directory is not a file,
    # so it would otherwise fall through to building_root_is_u5_5_live and SKIP).
    if manifest_path.exists() and not manifest_path.is_file():
        violations.append(
            f"{building_root}: evidence-manifest.json exists but is not a plain "
            "file; failing closed"
        )
        return False
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            violations.append(
                f"{building_root}: present but corrupt evidence-manifest.json; "
                f"cannot determine liveness; failing closed ({exc})"
            )
            return False
        if not isinstance(manifest, dict):
            violations.append(
                f"{building_root}: present but corrupt evidence-manifest.json "
                "(not a JSON object); cannot determine liveness; failing closed"
            )
            return False
        # (B2) Complete the manifest-trust class: a manifest carrying a non-finite
        # value (literal NaN, or NaN/inf via overflow) anywhere is not trustworthy.
        # This catches {"evidence_generation":NaN} AND a live-but-malformed
        # {"evidence_generation":"u5_5_live","x":NaN} -> RED (do not inspect).
        try:
            json.dumps(manifest, allow_nan=False)
        except ValueError:
            violations.append(
                f"{building_root}: non-finite value in evidence-manifest.json; "
                "failing closed"
            )
            return False
    # GUARD #4: inspect when tagged u5_5_live OR when the spine is already
    # populated (a dropped manifest tag must NOT free a built spine from
    # projection-coverage validation). The corrupt-manifest fail-closed branches
    # ABOVE are unchanged (they already return False with a RED appended); this
    # only WIDENS the live gate for a valid-or-absent manifest whose spine has
    # events on disk.
    return building_root_is_u5_5_live(building_root) or _spine_is_populated(building_root)


def _spine_is_populated(building_root: Path) -> bool:
    """True iff the building carries a NON-EMPTY spine events/ directory.

    GUARD #4 (populated-spine anchor): the u5_5_live manifest tag is the normal
    inspect gate, but capture.py can blind-overwrite the manifest and DROP the
    tag — silently freeing an ALREADY-BUILT spine from projection-coverage
    validation (false-green). A spine with ANY recorded artifact on disk MUST be
    inspected regardless of the tag, so inspection fails CLOSED on a populated
    spine. POPULATED iff the spine carries ANY part of its recorded set: an
    ``events/`` entry (``*.json`` OR its ``*.md`` render half) OR a
    ``spine.{json,jsonl,md}`` index file (P2 widening — counting ``*.json`` alone
    let a bulk file-op that left only the ``*.md`` halves + the index, plus a
    dropped tag, free a recorded spine from validation).

    The 154 pre-U5.5 buildings have NO ``evidence/spine/`` dir at all, so this is
    False for them — they stay SKIPPED exactly as today (no regression).
    """

    spine_dir = building_root / "evidence" / "spine"
    if not spine_dir.is_dir():
        return False
    events_dir = spine_dir / "events"
    if events_dir.is_dir() and (
        any(events_dir.glob("*.json")) or any(events_dir.glob("*.md"))
    ):
        return True
    return any(
        (spine_dir / name).is_file()
        for name in ("spine.json", "spine.jsonl", "spine.md")
    )


def building_roots_under(repo: Path) -> list[Path]:
    """Every project/*/buildings/<id>/ directory under repo."""

    roots: list[Path] = []
    project_root = repo / PROJECT_ROOT
    if not project_root.is_dir():
        return roots
    for buildings_root in sorted(project_root.glob(f"*/{BUILDINGS_SEGMENT}")):
        if not buildings_root.is_dir():
            continue
        for building_root in sorted(buildings_root.iterdir()):
            if building_root.is_dir():
                roots.append(building_root)
    return roots


def find_violations(repo: Path) -> tuple[list[str], int]:
    """Return (violations, inspected_u5_5_live_count) over every building."""

    violations: list[str] = []
    inspected = 0
    for building_root in building_roots_under(repo):
        if not _should_inspect_building(building_root, violations):
            continue
        inspected += 1
        validate_projection(building_root, violations)
    return violations, inspected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for the U5.5 Evidence Spine PROJECTION "
            "completeness (building-scope declaration coverage) of u5_5_live "
            "buildings. It does not prove the spine's structural integrity, "
            "content correctness, source truth, success, quality, or Movement "
            "authority."
        )
    )
    parser.add_argument("--repo", default=".", help="Repository root to inspect.")
    parser.add_argument(
        "--target",
        default=None,
        help="A single building root (or a buildings/ parent) to inspect directly.",
    )
    args = parser.parse_args(argv)

    try:
        if args.target:
            target = Path(args.target).resolve()
            if not target.is_dir():
                raise FileNotFoundError(f"target does not exist: {target}")
            violations = []
            inspected = 0
            # Accept either a single building root or a buildings/ parent.
            roots = (
                [child for child in sorted(target.iterdir()) if child.is_dir()]
                if target.name == BUILDINGS_SEGMENT
                else [target]
            )
            for building_root in roots:
                if not _should_inspect_building(building_root, violations):
                    continue
                inspected += 1
                validate_projection(building_root, violations)
        else:
            repo = Path(args.repo).resolve()
            if not repo.is_dir():
                raise FileNotFoundError(f"--repo must be a directory: {repo}")
            violations, inspected = find_violations(repo)
    except OSError as exc:
        print(f"evidence spine projection rejected: {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    if violations:
        print("evidence spine projection rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    print(
        "evidence spine projection passed: "
        f"{inspected} u5_5_live building spine projection(s) verified "
        "(exactly one each of the building-scope declaration events "
        "PresetExpansion, LinkLaunchPolicy, and TaskSource; per-executed-step "
        "BrickInput/BrickCompared/AgentBinding/AgentReceipt/AgentReturn coverage; "
        "per-executed-step Link coverage by source_fact_ref; per-executed-step "
        "raised-seam (TransitionConcern/RouteRequest) coverage by source_fact_ref; "
        "building-scope carry-budget LinkCarry coverage; and declared "
        "gate-sequence-policy LinkGateCheck/LinkPolicyAction coverage)."
    )
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

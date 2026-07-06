"""Recording input contracts for operator evidence writers.

These are support recording inputs only. They are not BAL facts and do not carry
Movement authority or success/quality judgments.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


def require_positive_int(
    value: Any,
    label: str,
    *,
    allow_decimal_text: bool = True,
    error_text: str = "must be a positive integer",
) -> int:
    """Return a positive int while rejecting bool explicitly."""

    if isinstance(value, bool):
        raise ValueError(f"{label} {error_text}; bool is not admitted")
    if isinstance(value, int) and value > 0:
        return value
    if allow_decimal_text and isinstance(value, str) and value.strip().isdecimal():
        parsed = int(value.strip())
        if parsed > 0:
            return parsed
    raise ValueError(f"{label} {error_text}")


@dataclass(frozen=True)
class StepOutputObservation:
    building_id: str
    step_ref: str
    brick_instance_ref: str
    agent_object_ref: str
    returned: Any
    received_work_ref: str
    returned_fact_ref: str
    raw_ref: str
    task_source_ref: str = ""
    not_proven: tuple[str, ...] = field(default_factory=tuple)
    # δ-b PER-STEP recorded_at: optional per-step wall-clock time. Empty string
    # means the writer falls back to a single graph_ready_timestamp so other
    # callers stay backward-compatible.
    recorded_at: str = ""
    # U5.5 RESUME-GATE-RECORD: a JSON-safe dict projection of the step's live
    # gate-sequence decision (or None when the step declared no gate policy). The
    # step-output writer persists it AT-TIME so a later resume can READ the
    # recorded decision back (it is never recomputed on replay). Last + defaulted
    # so every existing construction stays valid.
    gate_sequence_decision_record: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class AdapterErrorObservation:
    building_id: str
    step_ref: str
    brick_instance_ref: str
    next_brick_instance_ref: str
    agent_object_ref: str
    adapter_ref: str
    selected_model_ref: str
    input_packet_ref: str
    output_packet_ref: str
    error_kind: str
    exception_type: str
    message_excerpt: str
    received_work_ref: str
    adapter_error_ref: str
    raw_ref: str
    task_source_ref: str = ""
    diagnostic_excerpts: Mapping[str, str] = field(default_factory=dict)
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ChatSessionParkObservation:
    building_id: str
    step_ref: str
    brick_instance_ref: str
    next_brick_instance_ref: str
    agent_object_ref: str
    adapter_ref: str
    selected_model_ref: str
    input_packet_ref: str
    output_packet_ref: str
    received_work_ref: str
    parked_ref: str
    work_envelope_ref: str
    raw_ref: str
    work_envelope: Mapping[str, Any]
    task_source_ref: str = ""
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RawClaimTracePacket:
    brick_raw_records: tuple[Mapping[str, Any], ...]
    agent_raw_records: tuple[Mapping[str, Any], ...]
    link_raw_records: tuple[Mapping[str, Any], ...]
    brick_claim_facts: tuple[Mapping[str, Any], ...]
    agent_claim_facts: tuple[Mapping[str, Any], ...]
    link_transfer_claim_facts: tuple[Mapping[str, Any], ...]
    link_carry_claim_facts: tuple[Mapping[str, Any], ...]
    link_sufficiency_claim_facts: tuple[Mapping[str, Any], ...]
    link_movement_claim_facts: tuple[Mapping[str, Any], ...]
    # E1 (U5.5 slice-3): the live gate-sequence GateFact receipts (per gate) and
    # the FINAL policy action (per step), recorded from run.py's gate-sequence
    # disposition. Default to empty so existing constructors stay valid.
    link_gate_receipt_claim_facts: tuple[Mapping[str, Any], ...] = ()
    link_policy_action_claim_facts: tuple[Mapping[str, Any], ...] = ()
    agent_output_text_raw_records: tuple[Mapping[str, Any], ...] = ()
    # receipt-writer-join 0707 (rootfix 2): the NORMAL-completion Agent receipt
    # rows. Same shape as the adapter-error / chat-session-park frontier
    # receipt rows (received work observation only; no returned payload, no
    # verdict). Default to empty so existing constructors stay valid; the
    # forward writer still emits raw/agent-received.jsonl in the SAME
    # transaction as the returned rows (as an empty file for zero-step / empty
    # packets) so the design ledger is deterministic.
    agent_received_raw_records: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class AdapterErrorFrontierTracePacket:
    brick_raw_records: tuple[Mapping[str, Any], ...]
    agent_received_raw_records: tuple[Mapping[str, Any], ...]
    adapter_error_raw_records: tuple[Mapping[str, Any], ...]
    link_raw_records: tuple[Mapping[str, Any], ...]
    brick_claim_facts: tuple[Mapping[str, Any], ...]
    agent_receipt_claim_facts: tuple[Mapping[str, Any], ...]
    link_frontier_claim_facts: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class ChatSessionParkFrontierTracePacket:
    brick_raw_records: tuple[Mapping[str, Any], ...]
    agent_received_raw_records: tuple[Mapping[str, Any], ...]
    park_raw_records: tuple[Mapping[str, Any], ...]
    link_raw_records: tuple[Mapping[str, Any], ...]
    brick_claim_facts: tuple[Mapping[str, Any], ...]
    agent_receipt_claim_facts: tuple[Mapping[str, Any], ...]
    link_frontier_claim_facts: tuple[Mapping[str, Any], ...]


# ---------------------------------------------------------------------------
# DYNAMIC-WALKER EVIDENCE-SHAPE CONTRACT (single canonical source)
# ---------------------------------------------------------------------------
#
# P-evidence-arch / ζ6: the dynamic walker's reroute-adoption record, HOLD
# record, and structured field-set observation are SUPPORT RECORDING shapes
# (NESTED evidence; NOT a new BAL fact class, NOT a fourth axis, NO Movement
# authority, NO success/quality/fault judgment). This contract is the ONE home
# for those shapes so the emitter builds the record FROM the field-spec and the
# ζ6 checker DERIVES the expected shape FROM the same spec. When a feature impl
# changes, the evidence shape can NO LONGER drift silently -- only a change to
# THIS contract moves the shape, and the checker rejects an emitter that drops a
# required field or adds an undeclared one.


@dataclass(frozen=True)
class EvidenceFieldSpec:
    """One declared field of a support recording evidence shape.

    ``presence`` is "required" or "optional". These are recording-input shape
    declarations only; they carry no authority and judge nothing.
    """

    name: str
    presence: str  # "required" | "optional"


# Common reroute lineage fields shared by the adoption record and the HOLD
# record. Derived from the existing record literals (see support/operator/
# dynamic_walker.py history) so the shape is identical, only contract-derived.
_REROUTE_COMMON_REQUIRED: tuple[str, ...] = (
    "kind",
    "schema_version",
    "reroute_ref",
    "adoption_sequence_number",
    "cascade_depth",
    "parent_reroute_ref",
    "source_step_ref",
    "source_brick_ref",
    "source_transition_concern_ref",
    "transition_concern_binding",
    "immediate_target_ref",
    "target_brick",
    "attempt_number",
    "node_budget",
    "budget_exhausted",
    "disposition_required",
    "proof_limits",
    "not_proven",
)

# An ADOPTED reroute-landing record (disposition_required is False). Adds the
# adopting gate ref, the landed step ref, and the declared replay scope. The
# structured field observation (field sets + deltas at this boundary) is an
# OPTIONAL nested observation -- a pure FACT record, no judgment.
REROUTE_ADOPTION_REQUIRED_FIELDS: tuple[str, ...] = _REROUTE_COMMON_REQUIRED + (
    "adopted_by",
    "target_step_ref",
    "replay_segment_refs",
)
REROUTE_ADOPTION_OPTIONAL_FIELDS: tuple[str, ...] = (
    "structured_field_observation",
    "carry_budget_evidence_ref",
    # Knot ③ cohort re-verification plan for a landing on a fan-in SOURCE.
    # Persisted so a HOLD-then-resume reconstruction rebuilds the SAME pending
    # state the live walk had (re-verify siblings + carry vouched-skipped sibling
    # bodies). OPTIONAL: only present when the landing targets a fan-in source
    # with a non-empty cohort. Both are sibling SOURCE step_refs; cohort items are
    # FORWARD REPLAY (is_reroute_landing False => BUDGET-FREE).
    "cohort_replay_segment_refs",
    "cohort_skipped_segment_refs",
)

# A HOLD record (NOT adopted; disposition_required is True). Support HALTS and
# RECORDS -- it does NOT decide raise/forward/stop. Adds the pending target, the
# hold reason, the required disposition owner, and the paused lifecycle state.
HOLD_RECORD_REQUIRED_FIELDS: tuple[str, ...] = _REROUTE_COMMON_REQUIRED + (
    "pending_target_ref",
    "hold_reason",
    "required_disposition_owner",
    "transition_lifecycle_state",
)
HOLD_RECORD_OPTIONAL_FIELDS: tuple[str, ...] = (
    "structured_field_observation",
    "carry_budget_evidence_ref",
)

# A resume-after-HOLD observation is nested under dynamic_walker_evidence. It is
# not a BAL fact class and does not choose the disposition; it records the
# human/COO-authored disposition row that support replayed.
RESUME_OBSERVATION_REQUIRED_FIELDS: tuple[str, ...] = (
    "kind",
    "schema_version",
    "resumed_from",
    "paused_at_ref",
    "pending_target_ref",
    "disposition_action",
    "applied",
    "budget_increment",
    "node_budget",
    "node_landings",
    "proof_limits",
    "not_proven",
)
RESUME_OBSERVATION_OPTIONAL_FIELDS: tuple[str, ...] = (
    # FIX 3 (0611 replay provenance): the SELECTED disposition row's
    # discriminator, PERSISTED so it survives the raw/link.jsonl rewrite a
    # resume performs (write_text, not append -- the transient seed provenance
    # alone dangles on later replay). Data only (refs + an int): the
    # generation-unique hold identity (disposition_row_paused_at_ref, which
    # embeds source/depth/attempt -- see walker_hold._hold_paused_at_ref), the
    # row's own raw_ref, and the pre-resume-snapshot-relative 1-based match
    # index. OPTIONAL: observations recorded before this field existed, and
    # synthetic dispositions, legitimately lack it. NO judgment fields.
    "disposition_row_provenance",
)

# STRUCTURED FIELD-SET OBSERVATION (no judgment). Pure machine-readable
# observation of the field sets at a gate/reroute boundary:
#   - brick_required_fields: what Brick DECLARED (required_return_shape).
#   - observed_fields:       what Agent RETURNED (closed AgentFact returned keys).
#   - gate_required_fields:  what the gate/route REQUIRED.
#   - missing_from_observed: gate/brick required fields not present in observed.
#   - demanded_beyond_brick: gate-required fields NOT declared by Brick.
# These are FACTS (field sets + set deltas). There is NO failing_axis label, NO
# fault/failed/success verdict -- attribution is the reader's inference.
STRUCTURED_FIELD_OBSERVATION_REQUIRED_FIELDS: tuple[str, ...] = (
    "kind",
    "schema_version",
    "brick_required_fields",
    "observed_fields",
    "gate_required_fields",
    "missing_from_observed",
    "demanded_beyond_brick",
)
STRUCTURED_FIELD_OBSERVATION_OPTIONAL_FIELDS: tuple[str, ...] = ()

# Schema-version + kind literals (the ONE home; emitter + checker read these).
REROUTE_ADOPTION_RECORD_KIND = "reroute_adoption_record"
REROUTE_ADOPTION_RECORD_SCHEMA_VERSION = "reroute-adoption-record-0"
# The HOLD record shares the reroute_adoption_record kind (it IS a non-adopted
# RerouteAdoptionRecord), distinguished by disposition_required=True.
HOLD_RECORD_KIND = "reroute_adoption_record"
HOLD_RECORD_SCHEMA_VERSION = "reroute-adoption-record-0"
RESUME_OBSERVATION_KIND = "dynamic_walker_resume_observation"
RESUME_OBSERVATION_SCHEMA_VERSION = "dynamic-walker-resume-observation-0"
STRUCTURED_FIELD_OBSERVATION_KIND = "structured_field_observation"
STRUCTURED_FIELD_OBSERVATION_SCHEMA_VERSION = "structured-field-observation-0"


def reroute_adoption_field_specs() -> tuple[EvidenceFieldSpec, ...]:
    return tuple(
        EvidenceFieldSpec(name, "required") for name in REROUTE_ADOPTION_REQUIRED_FIELDS
    ) + tuple(
        EvidenceFieldSpec(name, "optional") for name in REROUTE_ADOPTION_OPTIONAL_FIELDS
    )


def hold_record_field_specs() -> tuple[EvidenceFieldSpec, ...]:
    return tuple(
        EvidenceFieldSpec(name, "required") for name in HOLD_RECORD_REQUIRED_FIELDS
    ) + tuple(
        EvidenceFieldSpec(name, "optional") for name in HOLD_RECORD_OPTIONAL_FIELDS
    )


def resume_observation_field_specs() -> tuple[EvidenceFieldSpec, ...]:
    return tuple(
        EvidenceFieldSpec(name, "required") for name in RESUME_OBSERVATION_REQUIRED_FIELDS
    ) + tuple(
        EvidenceFieldSpec(name, "optional") for name in RESUME_OBSERVATION_OPTIONAL_FIELDS
    )


def structured_field_observation_specs() -> tuple[EvidenceFieldSpec, ...]:
    return tuple(
        EvidenceFieldSpec(name, "required")
        for name in STRUCTURED_FIELD_OBSERVATION_REQUIRED_FIELDS
    ) + tuple(
        EvidenceFieldSpec(name, "optional")
        for name in STRUCTURED_FIELD_OBSERVATION_OPTIONAL_FIELDS
    )


# ---------------------------------------------------------------------------
# OPERATOR EVIDENCE-SHAPE CONTRACT (A2: capture events + building map + frontier)
# ---------------------------------------------------------------------------
#
# P-evidence-arch increment 2 / ζ6. The accumulated-Building operator evidence
# writer in ``support/operator/evidence_assembly.py`` previously HAND-WROTE the
# capture-event lifecycle dicts, the per-step building-map rows
# (brick_instances / agent_bindings / link_edges), and the frontier observation
# dict inline. This contract is the ONE home for those shapes so a contract-
# derived emitter (``support/recording/operator_evidence.py``) builds each record
# FROM the field-spec and the ζ6 checker DERIVES the expected shape FROM the same
# spec. These are SUPPORT RECORDING shapes only: NOT a new BAL fact class, NOT a
# fourth axis, NO Movement authority, NO success / quality / fault judgment.
#
# AXIS BACKBONE: each axis field-set is derived from ITS axis -- building-map
# brick_instances from the Brick backbone, agent_bindings from Agent, link_edges
# from Link; each of the 8 capture events from the relevant axis. The
# axis_attribution VALUE per capture event is declared here ONCE; the ζ6 checker
# verifies the emitted value against an INDEPENDENT rule (event_type prefix), NOT
# by reading this dict (so the check cannot be a tautology).


# ---- Capture-event lifecycle shape (the 8 inline events) ----
#
# The 8 lifecycle capture events in canonical emission order. Each event carries a
# common header (event_id, event_type, role_in_event, axis_attribution, raw_ref,
# not_proven) plus the per-event payload field NAMES it emits, in order. The
# emitter supplies the payload VALUES; the contract fixes the SHAPE + the axis +
# role literal. ``axis_attribution`` is a FACT label of which axis the event
# observes; it is NOT a verdict. ``building_opened`` is a non-axis lifecycle event
# whose attribution is the support-residue literal (the only allowed non-axis
# value -- the ζ6 checker pins exactly this string).
CAPTURE_EVENT_TYPES: tuple[str, ...] = (
    "building_opened",
    "brick_opened",
    "agent_received",
    "agent_returned",
    "brick_compared",
    "link_transfer",
    "link_carry",
    "link_movement",
)

# The non-axis attribution literal for non-axis lifecycle events (building_opened).
# This is the ONLY allowed non-axis axis_attribution value; the ζ6 checker pins it.
CAPTURE_EVENT_NON_AXIS_ATTRIBUTION = "Support residue"

# Declared axis_attribution per event_type. NOTE for the ζ6 checker author: do NOT
# verify the emitted value by reading THIS dict (that is circular). The checker has
# its own independent rule (event_type prefix -> axis) and pins the non-axis literal
# above for building_opened.
CAPTURE_EVENT_AXIS_ATTRIBUTION: dict[str, str] = {
    "building_opened": CAPTURE_EVENT_NON_AXIS_ATTRIBUTION,
    "brick_opened": "Brick",
    "agent_received": "Agent",
    "agent_returned": "Agent",
    "brick_compared": "Brick",
    "link_transfer": "Link",
    "link_carry": "Link",
    "link_movement": "Link",
}

# Declared role_in_event per event_type (a descriptive recording role, no authority).
CAPTURE_EVENT_ROLE: dict[str, str] = {
    "building_opened": "operator",
    "brick_opened": "work_author",
    "agent_received": "performer",
    "agent_returned": "performer",
    "brick_compared": "comparison_recorder",
    "link_transfer": "transfer_recorder",
    "link_carry": "carry_recorder",
    "link_movement": "movement_recorder",
}

# Declared event_id literal per event_type (stable identifier in the emitted record).
CAPTURE_EVENT_ID: dict[str, str] = {
    "building_opened": "agent-run-building-opened",
    "brick_opened": "agent-run-brick-opened",
    "agent_received": "agent-run-agent-received",
    "agent_returned": "agent-run-agent-returned",
    "brick_compared": "agent-run-brick-compared",
    "link_transfer": "agent-run-link-transfer",
    "link_carry": "agent-run-link-carry",
    "link_movement": "agent-run-link-movement",
}

# Common header fields emitted by every capture event, in order.
CAPTURE_EVENT_HEADER_FIELDS: tuple[str, ...] = (
    "event_id",
    "event_type",
    "role_in_event",
    "axis_attribution",
    "raw_ref",
    "not_proven",
)

# Per-event-type payload field NAMES (after the header, before/including facts), in
# the exact order the inline literals emitted them. ``facts`` is always last.
CAPTURE_EVENT_PAYLOAD_FIELDS: dict[str, tuple[str, ...]] = {
    "building_opened": ("building_ref", "facts"),
    "brick_opened": ("brick_ref", "facts"),
    "agent_received": ("actor_ref", "brick_ref", "public_fact_refs", "facts"),
    "agent_returned": ("actor_ref", "brick_ref", "public_fact_refs", "receipt_text", "facts"),
    "brick_compared": ("brick_ref", "public_fact_refs", "facts"),
    "link_transfer": ("public_fact_refs", "facts"),
    "link_carry": ("public_fact_refs", "facts"),
    "link_movement": ("public_fact_refs", "receipt_text", "facts"),
}


def capture_event_field_specs(event_type: str) -> tuple[EvidenceFieldSpec, ...]:
    """Ordered field-spec for one capture event = header + per-type payload.

    Every declared field is required; the emitter supplies the value. The order is
    the canonical on-disk key order, preserved for byte-identical output.
    """

    if event_type not in CAPTURE_EVENT_PAYLOAD_FIELDS:
        raise ValueError(f"unknown capture event_type: {event_type!r}")
    names = CAPTURE_EVENT_HEADER_FIELDS + CAPTURE_EVENT_PAYLOAD_FIELDS[event_type]
    return tuple(EvidenceFieldSpec(name, "required") for name in names)


# ---- Building-map per-step row shapes (Brick / Agent / Link backbones) ----
#
# brick_instances rows come from the BRICK backbone, agent_bindings from AGENT,
# link_edges from LINK. The emitter supplies the per-step values; the contract
# fixes the field set + order. ``optional`` fields are emitted only when supplied
# (e.g. the edge metadata fields the route-replay layer overlays).

# A performer brick_instance row (a step that an Agent performs).
BUILDING_MAP_BRICK_INSTANCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "brick_instance_id",
    "brick_work_ref",
    "attempt_index",
    "agent_binding_refs",
    "raw_refs",
    "proof_limits",
    "not_proven",
)

# An agent_binding row (Agent backbone): which Agent performed which brick.
BUILDING_MAP_AGENT_BINDING_REQUIRED_FIELDS: tuple[str, ...] = (
    "agent_binding_id",
    "brick_instance_ref",
    "agent_performer_ref",
    "binding_role",
    "produced_public_fact_refs",
    "step_output_ref",
    "raw_refs",
    "proof_limits",
    "not_proven",
)

# A link_edge row (Link backbone): the declared transition between two bricks. The
# base fields are required; the route-replay layer overlays OPTIONAL metadata
# (edge_metadata) that the emitter merges only when present.
BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS: tuple[str, ...] = (
    "link_edge_id",
    "edge_role",
    "source_brick_instance_ref",
    "target_brick_instance_ref",
    "input_public_fact_refs",
    "public_fact_refs",
    "movement_fact_ref",
    "transition_fact_ref",
    "step_output_ref",
)


def building_map_brick_instance_specs() -> tuple[EvidenceFieldSpec, ...]:
    return tuple(
        EvidenceFieldSpec(name, "required")
        for name in BUILDING_MAP_BRICK_INSTANCE_REQUIRED_FIELDS
    )


def building_map_agent_binding_specs() -> tuple[EvidenceFieldSpec, ...]:
    return tuple(
        EvidenceFieldSpec(name, "required")
        for name in BUILDING_MAP_AGENT_BINDING_REQUIRED_FIELDS
    )


def building_map_link_edge_specs() -> tuple[EvidenceFieldSpec, ...]:
    return tuple(
        EvidenceFieldSpec(name, "required")
        for name in BUILDING_MAP_LINK_EDGE_REQUIRED_FIELDS
    )


# ---- Frontier observation shape (agent-incomplete frontier) ----
#
# The frontier observation recorded on the building-map when an adapter raised
# after Agent receipt and before the returned AgentFact. It is a FACT of where the
# Building stopped (frontier_kind + the adapter-error ref) plus the standard proof
# limits. NO verdict.
FRONTIER_OBSERVATION_REQUIRED_FIELDS: tuple[str, ...] = (
    "frontier_kind",
    "proof_limits",
)
FRONTIER_OBSERVATION_OPTIONAL_FIELDS: tuple[str, ...] = (
    "adapter_error_ref",
    "parked_ref",
)
FRONTIER_OBSERVATION_AGENT_INCOMPLETE_KIND = "agent_incomplete"
FRONTIER_OBSERVATION_CHAT_SESSION_PARKED_KIND = "chat_session_parked"
FRONTIER_OBSERVATION_PROOF_LIMITS: tuple[str, ...] = (
    "graph support projection only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)


def frontier_observation_specs() -> tuple[EvidenceFieldSpec, ...]:
    return tuple(
        EvidenceFieldSpec(name, "required")
        for name in FRONTIER_OBSERVATION_REQUIRED_FIELDS
    ) + tuple(
        EvidenceFieldSpec(name, "optional")
        for name in FRONTIER_OBSERVATION_OPTIONAL_FIELDS
    )

"""Support-only contracts for the Building operator walker.

These dataclasses describe runner support observations. They are not new BAL
facts and do not make support a fourth axis.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # E1 (U5.5 slice-3): carry the support-only gate-sequence disposition forward
    # to the claim-trace seam for recording. Imported under TYPE_CHECKING ONLY to
    # avoid a runtime import cycle (gate_sequence.py imports BuildingRunSupportResult
    # from here). With `from __future__ import annotations` the annotation stays a
    # string, so the field carries no runtime import.
    from brick_protocol.support.operator.gate_sequence import GateSequenceDecision

from brick_protocol.agent.performance import AgentPerformerFact
from brick_protocol.agent.receipt import ReceiptFact
from brick_protocol.agent.return_fact import AgentFact
from brick_protocol.brick.comparison import BrickComparisonFact
from brick_protocol.brick.work import BrickWork
from brick_protocol.link.carry import CarryFact
from brick_protocol.link.gate import GateFact
from brick_protocol.link.movement import MovementFact
from brick_protocol.link.transition import TransitionFact
from brick_protocol.link.transfer import TransferFact
from brick_protocol.support.connection.agent_adapter import AgentAdapterResult
from brick_protocol.support.recording.building_map import BuildingMapWriteResult
from brick_protocol.support.recording.capture import BuildingLifecycleWriteResult
from brick_protocol.support.operator.primitives import (
    _optional_fact,
    _proof_limits_tuple,
    _require_fact,
    _require_matching_movement,
)

@dataclass(frozen=True)
class AgentObjectContractData:
    """Provider-neutral Agent Object refs used to prepare an Agent run.

    E2/S7 (mirror M1): the per-dial casting scalars (``preferred_adapter_ref`` /
    ``preferred_model_ref`` / ``preferred_reasoning_effort_ref``) that used to be
    NAMED dataclass fields here — a mirror of the Agent-axis casting field-set —
    are replaced by ONE opaque ``casting`` bag keyed by the ``CASTING_FIELDS``
    names. A ``@dataclass`` cannot splice a tuple into named fields, so a NEW
    casting dial would otherwise cost a new hand-typed scalar here; with the bag
    the dataclass never names a dial. The bag is built ONCE at the intent seam
    (``run._agent_object_from_mapping`` loops ``CASTING_FIELDS``) and threaded
    verbatim; support neither inspects nor defaults the carried casting values.
    A field absent from the source Agent Object is simply absent from the bag.
    """

    object_ref: str
    name: str
    lane: str
    callable_performer_refs: tuple[str, ...] = ()
    prompt_refs: tuple[str, ...] = ()
    skill_refs: tuple[str, ...] = ()
    hook_refs: tuple[str, ...] = ()
    tool_policy_refs: tuple[str, ...] = ()
    discipline_refs: tuple[str, ...] = ()
    adapter_refs: tuple[str, ...] = ()
    casting: Mapping[str, str] = field(default_factory=dict)

@dataclass(frozen=True)
class ThreeAxisStepRows:
    """One Building Plan step with exactly one Brick, Agent, and Link row."""

    step_ref: str
    brick_row: Mapping[str, Any]
    agent_row: Mapping[str, Any]
    link_row: Mapping[str, Any]
    proof_limits: tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class AgentRunPreparationRecord:
    """Support-only preparation record; no brain call is made here."""

    building_id: str
    step_rows: ThreeAxisStepRows
    brick_work: BrickWork
    brick_instance_ref: str
    next_brick_instance_ref: str
    agent_object: AgentObjectContractData
    agent_performer_fact: AgentPerformerFact
    receipt_fact: ReceiptFact
    call_preparation_refs: Mapping[str, Any]
    raw_refs: tuple[str, ...] = ()
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class AgentRunCompletionRecord:
    """Support-only completion record from adapter return and Link facts."""

    preparation: AgentRunPreparationRecord
    adapter_result: AgentAdapterResult | None
    agent_fact: AgentFact
    brick_comparison: BrickComparisonFact
    crossing_record: "MinimalCrossingRecord"
    link_handoff_packet: Mapping[str, Any]
    building_map_packet: Mapping[str, Any]
    lifecycle_packet_mapping: Mapping[str, Any]
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class MinimalCrossingRecord:
    """Narrow crossing evidence made only from public BAL facts."""

    brick_work: BrickWork
    agent_fact: AgentFact
    brick_comparison: BrickComparisonFact
    link_fact: MovementFact
    transition_fact: TransitionFact
    transfer_gate_fact: GateFact | None = None
    carry_gate_fact: GateFact | None = None
    movement_gate_fact: GateFact | None = None
    transfer_fact: "TransferFact | None" = None
    carry_fact: "CarryFact | None" = None
    proof_limits: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        checked_brick_work = _require_fact("brick_work", self.brick_work, BrickWork)
        checked_agent_fact = _require_fact("agent_fact", self.agent_fact, AgentFact)
        checked_brick_comparison = _require_fact(
            "brick_comparison",
            self.brick_comparison,
            BrickComparisonFact,
        )
        checked_link_fact = _require_fact("link_fact", self.link_fact, MovementFact)
        checked_transition_fact = _require_fact(
            "transition_fact",
            self.transition_fact,
            TransitionFact,
        )
        _require_matching_movement(checked_link_fact, checked_transition_fact)
        object.__setattr__(self, "brick_work", checked_brick_work)
        object.__setattr__(self, "agent_fact", checked_agent_fact)
        object.__setattr__(self, "brick_comparison", checked_brick_comparison)
        object.__setattr__(self, "link_fact", checked_link_fact)
        object.__setattr__(self, "transition_fact", checked_transition_fact)
        object.__setattr__(
            self,
            "transfer_gate_fact",
            _optional_fact("transfer_gate_fact", self.transfer_gate_fact, GateFact),
        )
        object.__setattr__(
            self,
            "carry_gate_fact",
            _optional_fact("carry_gate_fact", self.carry_gate_fact, GateFact),
        )
        object.__setattr__(
            self,
            "movement_gate_fact",
            _optional_fact("movement_gate_fact", self.movement_gate_fact, GateFact),
        )
        object.__setattr__(
            self,
            "transfer_fact",
            _optional_fact(
                "transfer_fact",
                self.transfer_fact,
                "brick_protocol.link.transfer",
                "TransferFact",
            ),
        )
        object.__setattr__(
            self,
            "carry_fact",
            _optional_fact(
                "carry_fact",
                self.carry_fact,
                "brick_protocol.link.carry",
                "CarryFact",
            ),
        )
        object.__setattr__(self, "proof_limits", _proof_limits_tuple(self.proof_limits))

@dataclass(frozen=True)
class BuildingRunSupportResult:
    """Support-only result for one mechanically coordinated Building pass."""

    building_id: str
    preparation: AgentRunPreparationRecord
    adapter_result: AgentAdapterResult
    completion: AgentRunCompletionRecord
    lifecycle_write: BuildingLifecycleWriteResult
    building_map_write: BuildingMapWriteResult
    written_files: tuple[Path, ...]
    capture_event_types: tuple[str, ...]
    building_map_packet: Mapping[str, Any]
    proof_limits: tuple[str, ...]
    not_proven: tuple[str, ...]
    # δ-b PER-STEP recorded_at: optional per-step wall-clock time captured when
    # this step's adapter dispatch completed. Empty string means "no per-step
    # time supplied" so writers fall back to a single graph_ready_timestamp.
    recorded_at: str = ""
    # E1 (U5.5 slice-3): the support-only GateSequenceDecision computed in run.py
    # AFTER this step closed (the live gate-sequence evaluation + final policy
    # action). None when no declared gate_sequence_policy applied. Support
    # recording shape only: it carries gate sufficiency + the FINAL policy action;
    # it is NOT a BAL fact, authors no Movement, and judges no success/quality.
    gate_sequence_decision: "GateSequenceDecision | None" = None

@dataclass(frozen=True)
class BuildingPlanSupportResult:
    """Support-only result for walking a declared Building plan."""

    building_id: str
    plan_ref: str
    step_results: tuple[BuildingRunSupportResult, ...]
    lifecycle_write: BuildingLifecycleWriteResult
    building_map_write: BuildingMapWriteResult
    written_files: tuple[Path, ...]
    capture_event_types: tuple[str, ...]
    building_map_packet: Mapping[str, Any]
    proof_limits: tuple[str, ...]
    not_proven: tuple[str, ...]
    anchored_ref: str = ""


# ---------------------------------------------------------------------------
# D1 (0706 r2-carry): post-assembly side-channel carry, single source.
# ---------------------------------------------------------------------------
# The dynamic walker attaches in-memory side channels onto a
# ``BuildingPlanSupportResult`` via ``object.__setattr__`` -- they are NOT frozen
# dataclass fields and NOT new BAL facts: the nested reroute records, the
# dynamic-walker evidence, and the opt-in report-event observations. Any
# post-assembly re-mint (``dataclasses.replace``) of such a result mints a NEW
# frozen instance whose ``__dict__`` side channels are DROPPED. Every caller that
# re-mints a post-assembly plan result MUST route the new instance back through
# ``carry_plan_result_side_channels`` so the close-time anchor stamp (or any
# future ``replace()``) cannot silently strip walker evidence / reroute records /
# report observations (0706 live-sweep catch: bounded_agent P4 AttributeError on
# ``_dynamic_walker_evidence`` after the anchor ``replace()``). The field-name
# literals live here ONCE (I1 single-source); attach + carry sites reference this
# tuple rather than re-typing the names.
PLAN_RESULT_SIDE_CHANNEL_FIELDS: tuple[str, ...] = (
    "_dynamic_walker_reroute_records",
    "_dynamic_walker_evidence",
    "_report_event_observations",
)


def carry_plan_result_side_channels(
    source: BuildingPlanSupportResult,
    minted: BuildingPlanSupportResult,
) -> BuildingPlanSupportResult:
    """Copy the in-memory side channels from ``source`` onto ``minted`` in place.

    Copy-only (I3): a channel ABSENT on ``source`` stays ABSENT on ``minted`` --
    the helper never originates an attachment and never mints an empty tuple for a
    channel the walk did not produce, so getattr-with-default and ``hasattr``
    consumers keep their current semantics. The tuple order of any carried channel
    is preserved by reference (I4), never rebuilt. Returns ``minted`` for
    call-site chaining. This is support recording carry only: it authors no
    Movement, gate, route, success, or quality, and adds no BAL fact class.
    """

    for field_name in PLAN_RESULT_SIDE_CHANNEL_FIELDS:
        if hasattr(source, field_name):
            object.__setattr__(minted, field_name, getattr(source, field_name))
    return minted

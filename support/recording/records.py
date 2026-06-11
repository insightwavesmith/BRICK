"""Typed packet records for deterministic Building evidence writing.

The recorder package is residual support mechanics. These records carry caller
supplied evidence packets only; they do not judge success, quality, or Movement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, TypeAlias, Union

from brick_protocol.agent.return_fact import AGENT_FACT_FIELDS


JsonScalar: TypeAlias = Union[str, int, float, bool, None]
JsonValue: TypeAlias = Union[JsonScalar, "JsonObject", tuple["JsonValue", ...]]

DEFAULT_PROOF_LIMITS: tuple[str, ...] = (
    "support evidence only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
    "not production readiness",
)

FORBIDDEN_PACKET_KEYS: frozenset[str] = frozenset(
    {
        "success",
        "failure",
        "failed",
        "done",
        "not_done",
        "result",
        "verdict",
        "quality",
        "score",
        "final_weight",
        "movement",
        "destination",
        "route",
        "rollback",
        "retry",
        "next_target",
        "evaluation_improvement",
        "review_runs",
        "review_synthesis",
        "received_work_ref",
        "provider",
        "model",
        "runtime",
        "scheduler",
        "timeout",
    }
)

TRACE_ONLY_FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "success",
        "failure",
        "done",
        "not_done",
        "result",
        "verdict",
        "quality",
        "score",
        "source_truth",
        "movement",
        "movement_choice",
        "destination_choice",
        "performer_choice",
        "runtime",
        "provider",
        "model",
        "tool",
        "session",
        "storage",
        "wiki",
        "scheduler",
        "queue",
        "retry",
        "rollback",
    }
)

# TRANSFER_TRACE_FIELDS and CARRY_TRACE_FIELDS are EVIDENCE-RECORD shapes for the
# durable trace: they extend the Link transfer/carry axis facts with evidence-only
# fields (fact_type, protocol_baseline, *_fact_ref, proof_limits, not_proven,
# evidence_reference). They are intentionally a SUPERSET of the axis fact and are NOT
# a 1:1 mirror of it; do not collapse them to the axis fact's field set.
TRANSFER_TRACE_FIELDS: frozenset[str] = frozenset(
    {
        "fact_type",
        "protocol_baseline",
        "transfer_fact_ref",
        "source_boundary_ref",
        "target_boundary_ref",
        "public_fact_refs",
        "required_public_facts",
        "transfer_gate_reference",
        "proof_limits",
        "not_proven",
        "evidence_reference",
    }
)

CARRY_TRACE_FIELDS: frozenset[str] = frozenset(
    {
        "fact_type",
        "protocol_baseline",
        "carry_fact_ref",
        "carried_fact_refs",
        "source_owner_axis",
        "target_boundary_ref",
        "carry_gate_reference",
        "proof_limits",
        "not_proven",
        "evidence_reference",
    }
)

CARRY_TRACE_SOURCE_OWNER_AXES: frozenset[str] = frozenset({"Brick", "Agent", "Link"})


@dataclass(frozen=True)
class JsonField:
    """One ordered JSON object field."""

    key: str
    value: JsonValue

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _required_text("JsonField.key", self.key))
        object.__setattr__(self, "value", _normalize_json_value(self.value))


@dataclass(frozen=True)
class JsonObject:
    """Ordered JSON object input without exposing a generic dict contract."""

    fields: tuple[JsonField, ...]

    def __post_init__(self) -> None:
        fields = _field_tuple(self.fields)
        seen: set[str] = set()
        for field_value in fields:
            if field_value.key in seen:
                raise ValueError(f"duplicate JSON field {field_value.key!r}")
            normalized = _normalize_key(field_value.key)
            if normalized in FORBIDDEN_PACKET_KEYS or normalized == "source_truth":
                raise ValueError(f"forbidden recorder packet key {field_value.key!r}")
            seen.add(field_value.key)
        object.__setattr__(self, "fields", fields)

    @classmethod
    def from_pairs(
        cls,
        *pairs: JsonField | tuple[str, JsonValue],
    ) -> "JsonObject":
        fields: list[JsonField] = []
        for index, pair in enumerate(pairs):
            if isinstance(pair, JsonField):
                fields.append(pair)
                continue
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise TypeError(f"pairs[{index}] must be JsonField or (key, value)")
            fields.append(JsonField(pair[0], pair[1]))
        return cls(tuple(fields))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "JsonObject":
        _reject_forbidden_packet_keys(value)
        return cls(tuple(JsonField(str(key), nested) for key, nested in value.items()))


@dataclass(frozen=True)
class TextRecord:
    """Plain text record content."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("TextRecord.text must be text")


@dataclass(frozen=True)
class JsonlRecord:
    """Ordered JSONL record entries."""

    entries: tuple[JsonObject, ...]

    def __post_init__(self) -> None:
        entries = _json_object_tuple("JsonlRecord.entries", self.entries)
        if not entries:
            raise ValueError("JsonlRecord.entries must not be empty")
        object.__setattr__(self, "entries", entries)


@dataclass(frozen=True)
class RawEvidenceRecords:
    """Raw support records for one Brick."""

    input_text: TextRecord
    agent_return_text: TextRecord
    timeline: JsonlRecord
    transcript: JsonlRecord
    tool_events: JsonlRecord
    prompt_stack: TextRecord
    context_manifest: JsonObject

    def __post_init__(self) -> None:
        _require_type("input_text", self.input_text, TextRecord)
        _require_type("agent_return_text", self.agent_return_text, TextRecord)
        _require_type("timeline", self.timeline, JsonlRecord)
        _require_type("transcript", self.transcript, JsonlRecord)
        _require_type("tool_events", self.tool_events, JsonlRecord)
        _require_type("prompt_stack", self.prompt_stack, TextRecord)
        _require_type("context_manifest", self.context_manifest, JsonObject)


@dataclass(frozen=True)
class WorkClaimTraceRecords:
    """Claim / Trace records for a normal Work Building Brick."""

    brick_work_contract: JsonObject
    agent_returned_claims: JsonObject
    link_transfer_trace: JsonObject
    link_carry_trace: JsonObject
    link_sufficiency_trace: JsonObject

    def __post_init__(self) -> None:
        _require_type("brick_work_contract", self.brick_work_contract, JsonObject)
        _require_type("agent_returned_claims", self.agent_returned_claims, JsonObject)
        _require_type("link_transfer_trace", self.link_transfer_trace, JsonObject)
        _require_type("link_carry_trace", self.link_carry_trace, JsonObject)
        _require_type("link_sufficiency_trace", self.link_sufficiency_trace, JsonObject)
        _assert_agent_fact_shape("agent_returned_claims", self.agent_returned_claims)
        _validate_link_transfer_trace(self.link_transfer_trace)
        _validate_link_carry_trace(self.link_carry_trace)


@dataclass(frozen=True)
class ReviewClaimTraceRecords:
    """Claim / Trace records for a Review Building Brick."""

    review_work_contract: JsonObject
    reviewer_returned_claims: JsonObject
    reviewed_building_handoff: JsonObject

    def __post_init__(self) -> None:
        _require_type("review_work_contract", self.review_work_contract, JsonObject)
        _require_type("reviewer_returned_claims", self.reviewer_returned_claims, JsonObject)
        _require_type("reviewed_building_handoff", self.reviewed_building_handoff, JsonObject)
        _assert_agent_fact_shape(
            "reviewer_returned_claims",
            self.reviewer_returned_claims,
        )


@dataclass(frozen=True)
class WorkBrickEvidencePacket:
    """One Work Building Brick evidence packet."""

    brick_id: str
    brick_timeline: JsonlRecord
    raw_records: RawEvidenceRecords
    claim_trace: WorkClaimTraceRecords
    variables: JsonObject

    def __post_init__(self) -> None:
        object.__setattr__(self, "brick_id", _required_path_text("brick_id", self.brick_id))
        _require_type("brick_timeline", self.brick_timeline, JsonlRecord)
        _require_type("raw_records", self.raw_records, RawEvidenceRecords)
        _require_type("claim_trace", self.claim_trace, WorkClaimTraceRecords)
        _require_type("variables", self.variables, JsonObject)


@dataclass(frozen=True)
class ReviewBrickEvidencePacket:
    """One Review Building Brick evidence packet."""

    brick_id: str
    brick_timeline: JsonlRecord
    raw_records: RawEvidenceRecords
    claim_trace: ReviewClaimTraceRecords
    variables: JsonObject

    def __post_init__(self) -> None:
        object.__setattr__(self, "brick_id", _required_path_text("brick_id", self.brick_id))
        _require_type("brick_timeline", self.brick_timeline, JsonlRecord)
        _require_type("raw_records", self.raw_records, RawEvidenceRecords)
        _require_type("claim_trace", self.claim_trace, ReviewClaimTraceRecords)
        _require_type("variables", self.variables, JsonObject)


@dataclass(frozen=True)
class WorkBuildingEvidencePacket:
    """A complete Work Building evidence packet."""

    building_id: str
    building_timeline: JsonlRecord
    bricks: tuple[WorkBrickEvidencePacket, ...]
    proof_limits: tuple[str, ...] = DEFAULT_PROOF_LIMITS

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "building_id",
            _required_path_text("building_id", self.building_id),
        )
        _require_type("building_timeline", self.building_timeline, JsonlRecord)
        bricks = _typed_tuple("bricks", self.bricks, WorkBrickEvidencePacket)
        if not bricks:
            raise ValueError("bricks must not be empty")
        _reject_duplicate_brick_ids(bricks)
        object.__setattr__(self, "bricks", bricks)
        object.__setattr__(self, "proof_limits", _proof_limits_tuple(self.proof_limits))


@dataclass(frozen=True)
class ReviewBuildingEvidencePacket:
    """A complete Review Building evidence packet."""

    building_id: str
    building_timeline: JsonlRecord
    bricks: tuple[ReviewBrickEvidencePacket, ...]
    proof_limits: tuple[str, ...] = DEFAULT_PROOF_LIMITS

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "building_id",
            _required_path_text("building_id", self.building_id),
        )
        _require_type("building_timeline", self.building_timeline, JsonlRecord)
        bricks = _typed_tuple("bricks", self.bricks, ReviewBrickEvidencePacket)
        if not bricks:
            raise ValueError("bricks must not be empty")
        _reject_duplicate_brick_ids(bricks)
        object.__setattr__(self, "bricks", bricks)
        object.__setattr__(self, "proof_limits", _proof_limits_tuple(self.proof_limits))


BuildingEvidencePacket: TypeAlias = Union[
    WorkBuildingEvidencePacket,
    ReviewBuildingEvidencePacket,
]


def building_evidence_packet_from_mapping(value: Mapping[str, Any]) -> BuildingEvidencePacket:
    """Build a typed packet from a parsed JSON object."""

    if not isinstance(value, Mapping):
        raise TypeError("building evidence packet must be a JSON object")
    _reject_forbidden_packet_keys(value)
    packet_kind = _required_text(
        "packet_kind",
        _required_mapping_value(value, "packet_kind"),
    )
    if packet_kind == "work_building":
        return _work_building_from_mapping(value)
    if packet_kind == "review_building":
        return _review_building_from_mapping(value)
    raise ValueError("packet_kind must be work_building or review_building")


def to_plain_json(value: JsonValue) -> Any:
    """Convert typed JSON values to plain JSON-compatible values."""

    if isinstance(value, JsonObject):
        return {field_value.key: to_plain_json(field_value.value) for field_value in value.fields}
    if isinstance(value, tuple):
        return [to_plain_json(item) for item in value]
    return value


def _work_building_from_mapping(value: Mapping[str, Any]) -> WorkBuildingEvidencePacket:
    return WorkBuildingEvidencePacket(
        building_id=_required_text("building_id", _required_mapping_value(value, "building_id")),
        building_timeline=_jsonl_from_sequence(
            "building_timeline",
            _required_mapping_value(value, "building_timeline"),
        ),
        bricks=tuple(
            _work_brick_from_mapping(item)
            for item in _required_sequence("bricks", _required_mapping_value(value, "bricks"))
        ),
        proof_limits=_optional_proof_limits(value.get("proof_limits", DEFAULT_PROOF_LIMITS)),
    )


def _review_building_from_mapping(value: Mapping[str, Any]) -> ReviewBuildingEvidencePacket:
    return ReviewBuildingEvidencePacket(
        building_id=_required_text("building_id", _required_mapping_value(value, "building_id")),
        building_timeline=_jsonl_from_sequence(
            "building_timeline",
            _required_mapping_value(value, "building_timeline"),
        ),
        bricks=tuple(
            _review_brick_from_mapping(item)
            for item in _required_sequence("bricks", _required_mapping_value(value, "bricks"))
        ),
        proof_limits=_optional_proof_limits(value.get("proof_limits", DEFAULT_PROOF_LIMITS)),
    )


def _work_brick_from_mapping(value: Any) -> WorkBrickEvidencePacket:
    mapping = _required_mapping("bricks[]", value)
    return WorkBrickEvidencePacket(
        brick_id=_required_text("brick_id", _required_mapping_value(mapping, "brick_id")),
        brick_timeline=_jsonl_from_sequence(
            "brick_timeline",
            _required_mapping_value(mapping, "brick_timeline"),
        ),
        raw_records=_raw_records_from_mapping(_required_mapping_value(mapping, "raw_records")),
        claim_trace=_work_claim_trace_from_mapping(
            _required_mapping_value(mapping, "claim_trace"),
        ),
        variables=_json_object_from_mapping(_required_mapping_value(mapping, "variables")),
    )


def _review_brick_from_mapping(value: Any) -> ReviewBrickEvidencePacket:
    mapping = _required_mapping("bricks[]", value)
    return ReviewBrickEvidencePacket(
        brick_id=_required_text("brick_id", _required_mapping_value(mapping, "brick_id")),
        brick_timeline=_jsonl_from_sequence(
            "brick_timeline",
            _required_mapping_value(mapping, "brick_timeline"),
        ),
        raw_records=_raw_records_from_mapping(_required_mapping_value(mapping, "raw_records")),
        claim_trace=_review_claim_trace_from_mapping(
            _required_mapping_value(mapping, "claim_trace"),
        ),
        variables=_json_object_from_mapping(_required_mapping_value(mapping, "variables")),
    )


def _raw_records_from_mapping(value: Any) -> RawEvidenceRecords:
    mapping = _required_mapping("raw_records", value)
    return RawEvidenceRecords(
        input_text=TextRecord(
            _required_text("input_text", _required_mapping_value(mapping, "input_text"))
        ),
        agent_return_text=TextRecord(
            _required_text(
                "agent_return_text",
                _required_mapping_value(mapping, "agent_return_text"),
            )
        ),
        timeline=_jsonl_from_sequence(
            "raw_records.timeline",
            _required_mapping_value(mapping, "timeline"),
        ),
        transcript=_jsonl_from_sequence(
            "raw_records.transcript",
            _required_mapping_value(mapping, "transcript"),
        ),
        tool_events=_jsonl_from_sequence(
            "raw_records.tool_events",
            _required_mapping_value(mapping, "tool_events"),
        ),
        prompt_stack=TextRecord(
            _required_text("prompt_stack", _required_mapping_value(mapping, "prompt_stack"))
        ),
        context_manifest=_json_object_from_mapping(
            _required_mapping_value(mapping, "context_manifest")
        ),
    )


def _work_claim_trace_from_mapping(value: Any) -> WorkClaimTraceRecords:
    mapping = _required_mapping("claim_trace", value)
    return WorkClaimTraceRecords(
        brick_work_contract=_json_object_from_mapping(
            _required_mapping_value(mapping, "brick_work_contract")
        ),
        agent_returned_claims=_json_object_from_mapping(
            _required_mapping_value(mapping, "agent_returned_claims")
        ),
        link_transfer_trace=_json_object_from_mapping(
            _required_mapping_value(mapping, "link_transfer_trace")
        ),
        link_carry_trace=_json_object_from_mapping(
            _required_mapping_value(mapping, "link_carry_trace")
        ),
        link_sufficiency_trace=_json_object_from_mapping(
            _required_mapping_value(mapping, "link_sufficiency_trace")
        ),
    )


def _review_claim_trace_from_mapping(value: Any) -> ReviewClaimTraceRecords:
    mapping = _required_mapping("claim_trace", value)
    return ReviewClaimTraceRecords(
        review_work_contract=_json_object_from_mapping(
            _required_mapping_value(mapping, "review_work_contract")
        ),
        reviewer_returned_claims=_json_object_from_mapping(
            _required_mapping_value(mapping, "reviewer_returned_claims")
        ),
        reviewed_building_handoff=_json_object_from_mapping(
            _required_mapping_value(mapping, "reviewed_building_handoff")
        ),
    )


def _json_object_from_mapping(value: Any) -> JsonObject:
    return JsonObject.from_mapping(_required_mapping("json object", value))


def _jsonl_from_sequence(label: str, value: Any) -> JsonlRecord:
    return JsonlRecord(
        tuple(_json_object_from_mapping(item) for item in _required_sequence(label, value))
    )


def _reject_duplicate_brick_ids(
    bricks: tuple[WorkBrickEvidencePacket, ...] | tuple[ReviewBrickEvidencePacket, ...],
) -> None:
    seen: set[str] = set()
    for brick in bricks:
        if brick.brick_id in seen:
            raise ValueError(f"duplicate brick_id {brick.brick_id!r}")
        seen.add(brick.brick_id)


def _reject_forbidden_packet_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            normalized = _normalize_key(key_text)
            if normalized in FORBIDDEN_PACKET_KEYS:
                raise ValueError(f"{path}.{key_text}: forbidden recorder packet key")
            if normalized == "source_truth":
                raise ValueError(f"{path}.{key_text}: source_truth is forbidden")
            _reject_forbidden_packet_keys(nested, f"{path}.{key_text}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_forbidden_packet_keys(nested, f"{path}[{index}]")


def _validate_link_transfer_trace(value: JsonObject) -> None:
    _reject_forbidden_trace_keys(value, "$")
    _assert_closed_json_object("link_transfer_trace", value, TRANSFER_TRACE_FIELDS)
    _assert_json_field_literal("link_transfer_trace", value, "fact_type", "TransferTrace")
    _assert_json_field_literal("link_transfer_trace", value, "protocol_baseline", "LEP-0")


def _validate_link_carry_trace(value: JsonObject) -> None:
    _reject_forbidden_trace_keys(value, "$")
    _assert_closed_json_object("link_carry_trace", value, CARRY_TRACE_FIELDS)
    _assert_json_field_literal("link_carry_trace", value, "fact_type", "CarryTrace")
    _assert_json_field_literal("link_carry_trace", value, "protocol_baseline", "LEP-0")
    source_owner_axis = _json_object_field_value(value, "source_owner_axis")
    if source_owner_axis not in CARRY_TRACE_SOURCE_OWNER_AXES:
        raise ValueError("link_carry_trace.source_owner_axis must be Brick, Agent, or Link")


def _reject_forbidden_trace_keys(value: JsonValue, path: str) -> None:
    forbidden = FORBIDDEN_PACKET_KEYS | TRACE_ONLY_FORBIDDEN_KEYS | frozenset({"source_truth"})
    if isinstance(value, JsonObject):
        for field_value in value.fields:
            key = _normalize_key(field_value.key)
            if key in forbidden:
                raise ValueError(f"{path}.{field_value.key}: forbidden Link trace key")
            _reject_forbidden_trace_keys(field_value.value, f"{path}.{field_value.key}")
    elif isinstance(value, tuple):
        for index, nested in enumerate(value):
            _reject_forbidden_trace_keys(nested, f"{path}[{index}]")


def _assert_closed_json_object(
    label: str,
    value: JsonObject,
    allowed_fields: frozenset[str],
) -> None:
    keys = {field_value.key for field_value in value.fields}
    if keys != allowed_fields:
        missing = sorted(allowed_fields - keys)
        extra = sorted(keys - allowed_fields)
        details: list[str] = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"extra {', '.join(extra)}")
        raise ValueError(f"{label} must contain exactly its LEP-0 fields: {'; '.join(details)}")


def _assert_json_field_literal(
    label: str,
    value: JsonObject,
    key: str,
    expected: str,
) -> None:
    actual = _json_object_field_value(value, key)
    if actual != expected:
        raise ValueError(f"{label}.{key} must be {expected!r}")


def _json_object_field_value(value: JsonObject, key: str) -> JsonValue:
    for field_value in value.fields:
        if field_value.key == key:
            return field_value.value
    raise ValueError(f"missing required field {key!r}")


def _assert_agent_fact_shape(label: str, value: JsonObject) -> None:
    keys = {field_value.key for field_value in value.fields}
    if keys != set(AGENT_FACT_FIELDS):
        raise ValueError(f"{label} must contain exactly received_work and returned")


def _normalize_json_value(value: Any) -> JsonValue:
    if isinstance(value, JsonObject):
        return value
    if isinstance(value, JsonField):
        raise TypeError("JsonField cannot be used as a JSON value")
    if isinstance(value, Mapping):
        return JsonObject.from_mapping(value)
    if isinstance(value, list):
        return tuple(_normalize_json_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_normalize_json_value(item) for item in value)
    if isinstance(value, (str, bool)) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("JSON float values must be finite")
        return value
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def _required_text(label: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _required_path_text(label: str, value: Any) -> str:
    text = _required_text(label, value)
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if "/" in text or "\\" in text or text in {".", ".."}:
        raise ValueError(f"{label} must be a single path segment")
    if any(character not in allowed for character in text):
        raise ValueError(f"{label} contains an unsafe path character")
    return text


def _required_mapping(label: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a JSON object")
    _reject_forbidden_packet_keys(value)
    return value


def _required_mapping_value(value: Mapping[str, Any], key: str) -> Any:
    if key not in value:
        raise ValueError(f"missing required field {key!r}")
    return value[key]


def _required_sequence(label: str, value: Any) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{label} must be a JSON array")
    if not value:
        raise ValueError(f"{label} must not be empty")
    return value


def _field_tuple(fields: Any) -> tuple[JsonField, ...]:
    if not isinstance(fields, tuple):
        raise TypeError("JsonObject.fields must be a tuple")
    for index, item in enumerate(fields):
        if not isinstance(item, JsonField):
            raise TypeError(f"JsonObject.fields[{index}] must be JsonField")
    return fields


def _json_object_tuple(label: str, values: Any) -> tuple[JsonObject, ...]:
    return _typed_tuple(label, values, JsonObject)


def _typed_tuple(label: str, values: Any, expected_type: type[Any]) -> tuple[Any, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be a tuple")
    for index, item in enumerate(values):
        if not isinstance(item, expected_type):
            raise TypeError(f"{label}[{index}] must be {expected_type.__name__}")
    return values


def _text_tuple(label: str, values: Any) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be a tuple")
    return tuple(_required_text(f"{label}[]", item) for item in values)


def _proof_limits_tuple(values: Any) -> tuple[str, ...]:
    limits = _text_tuple("proof_limits", values)
    if "support evidence only" not in limits:
        raise ValueError("proof_limits must include 'support evidence only'")
    return limits


def _optional_proof_limits(values: Any) -> tuple[str, ...]:
    if isinstance(values, list):
        values = tuple(values)
    return _proof_limits_tuple(values)


def _require_type(label: str, value: Any, expected_type: type[Any]) -> None:
    if not isinstance(value, expected_type):
        raise TypeError(f"{label} must be {expected_type.__name__}")


def _normalize_key(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()


__all__ = [
    "BuildingEvidencePacket",
    "DEFAULT_PROOF_LIMITS",
    "FORBIDDEN_PACKET_KEYS",
    "JsonField",
    "JsonObject",
    "JsonlRecord",
    "RawEvidenceRecords",
    "ReviewBrickEvidencePacket",
    "ReviewBuildingEvidencePacket",
    "ReviewClaimTraceRecords",
    "TextRecord",
    "WorkBrickEvidencePacket",
    "WorkBuildingEvidencePacket",
    "WorkClaimTraceRecords",
    "building_evidence_packet_from_mapping",
    "to_plain_json",
]

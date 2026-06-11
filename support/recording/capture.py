"""Minimal CAP-BOOT-3 Building lifecycle capture writer.

The writer stores caller-supplied packets only. It does not infer facts, run an
Agent, call a provider, judge success or quality, or choose Movement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any, TypeAlias, Union


JsonScalar: TypeAlias = Union[str, int, float, bool, None]
JsonValue: TypeAlias = Union[JsonScalar, Mapping[str, "JsonValue"], Sequence["JsonValue"]]
JsonObject: TypeAlias = Mapping[str, JsonValue]

# Canonical, repo-anchored Building root: derived from this file's location so
# building output always lands inside the repo regardless of the process working
# directory. This is the single source for the Building root (other modules
# import it; see check_building_root_anchor).
REPO_ROOT = Path(__file__).resolve().parents[2]

# PROJECT-0 S5-FIX: THE single project-id slug law. The declared rule
# everywhere (loader messages, this seam) is [-_a-z0-9]; the old
# ``.isalnum()`` predicate silently admitted uppercase AND unicode ids
# ('ABC', '프로젝트'), which then propagated through buildings_root_for and
# path admission. Strict form: lowercase ascii [-_a-z0-9] only, and the
# FIRST character must be [a-z0-9] (no leading '-'/'_' — a vessel dir that
# starts with '-' or '_' reads as a flag/hidden-family path). One home —
# the declaration loader (support/operator/project_declaration.py) imports
# this predicate; check_package_path_admission mirrors it locally (that
# foundational path gate carries no cross-layer import by design) and
# check_project_declaration FIRE-probes all three seams in lockstep.
PROJECT_ID_SLUG_PATTERN = r"[a-z0-9][-_a-z0-9]*"
_PROJECT_ID_SLUG_RE = re.compile(PROJECT_ID_SLUG_PATTERN)


def is_project_id_slug(value: object) -> bool:
    """True iff ``value`` is a strict project-id slug (see law above)."""

    return isinstance(value, str) and bool(_PROJECT_ID_SLUG_RE.fullmatch(value))


def buildings_root_for(project_ref: str) -> Path:
    """PROJECT-0 S1-D: THE single derivation seam from a project_ref to its
    buildings root (one function, one home — pinned by check_building_root_anchor).

    ``project:<id>`` -> ``REPO_ROOT / "project" / <id> / "buildings"``. Path is
    the first-class membership fact; this seam is the only place a buildings
    root is derived from a declared project_ref (S3 intake consumes it).
    Raises ValueError on a malformed ref. DEFAULT_BUILDINGS_ROOT stays the
    project #1 default for ref-less callers.
    """

    prefix = "project:"
    if not isinstance(project_ref, str) or not project_ref.startswith(prefix):
        raise ValueError(f"project_ref must look like 'project:<id>', got {project_ref!r}")
    project_id = project_ref[len(prefix) :]
    if not is_project_id_slug(project_id):
        raise ValueError(
            f"project_ref id must be a non-empty [-_a-z0-9] slug "
            f"(lowercase ascii; first char [a-z0-9]), got {project_id!r}"
        )
    return REPO_ROOT / "project" / project_id / "buildings"


def project_ref_for_building_root(
    building_root: "str | Path",
    repo_root: "str | Path | None" = None,
) -> "str | None":
    """DECISIONS-WIRE AUTO-ON (Smith 0611): THE single INVERSE derivation seam
    from a building-root PATH to its vessel project_ref. The vessel is a PATH
    fact; this is the one place that fact is read back out of a path (one
    function, one home, next to ``buildings_root_for`` — path-parsing must not
    scatter into emit sites).

    ``<repo>/project/<id>/buildings[/...]`` -> ``'project:<id>'`` (accepts a
    building root under the vessel buildings root, or that buildings root
    itself). The result is round-tripped through ``buildings_root_for`` so the
    forward and inverse seams cannot diverge silently. Any other path —
    outside the repo, legacy/tmp, malformed id — returns None: loudly nothing,
    callers keep the legacy (un-segmented) report ids unchanged.
    """

    repo = Path(repo_root).resolve() if repo_root is not None else REPO_ROOT
    candidate = Path(building_root)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo / candidate).resolve()
    try:
        parts = resolved.relative_to(repo).parts
    except ValueError:
        return None
    if len(parts) < 3 or parts[0] != "project" or parts[2] != "buildings":
        return None
    if not is_project_id_slug(parts[1]):
        return None
    project_ref = f"project:{parts[1]}"
    # Round-trip through THE forward seam: the inverse is valid only if the
    # forward derivation lands exactly on the observed vessel buildings root.
    if buildings_root_for(project_ref).relative_to(REPO_ROOT).parts != parts[:3]:
        return None
    return project_ref


# PROJECT-0 S3-A: the ref-less default root is ITSELF derived through the
# single seam above (project #1 = project:brick-protocol) — no parallel
# "project/brick-protocol" path-join literal survives anywhere. The
# root-anchor checker admits seam-derived values as repo-anchored because the
# seam's own returns are proven REPO_ROOT-anchored (rule 3 of that checker).
DEFAULT_BUILDINGS_ROOT = buildings_root_for("project:brick-protocol")


GRAPH_READY_SCHEMA_VERSION = "graph-ready-v1"
GRAPH_READY_DATASCHEMA = "urn:bp:schema:graph-ready-v1"
GRAPH_READY_CONTEXT: dict[str, str] = {
    "bp": "urn:bp:",
    "ce": "https://cloudevents.io/spec/v1.0/",
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

CAPTURE_EVENT_TYPES = frozenset(
    {
        "building_opened",
        "brick_opened",
        "brick_compared",
        "agent_received",
        "agent_returned",
        "link_transfer",
        "link_carry",
        "link_gate_receipt",
        "link_movement",
        "support_note",
    }
)

CAPTURE_ROLE_LITERALS = frozenset(
    {
        "operator",
        "work_author",
        "performer",
        "delegated_performer",
        "delegated_reviewer",
        "transfer_recorder",
        "carry_recorder",
        "comparison_recorder",
        "gate_recorder",
        "movement_recorder",
        "support_writer",
        "observer",
    }
)

CAPTURE_AXIS_ATTRIBUTIONS = frozenset({"Brick", "Agent", "Link", "Support residue"})

FORBIDDEN_CAPTURE_KEYS = frozenset(
    {
        "success",
        "failure",
        "failed",
        "approved",
        "complete",
        "pass",
        "fail",
        "done",
        "not_done",
        "result",
        "verdict",
        "quality",
        "movement",
        "movement_choice",
        "destination_choice",
        "route_choice",
        "provider",
        "runtime",
        "storage",
        "wiki",
        "scheduler",
        "queue",
        "retry",
        "rollback",
        "rollback_execution",
        "dashboard",
    }
)
MOVEMENT_LITERAL_KEY = "movement"
# INTENTIONAL historical raw-capture tolerance: the raw lifecycle log must accept the
# superseded/historical movement words emitted by older runs and replays. Link's ACTIVE
# Movement vocabulary is ONLY forward/reroute (the single source is
# link/movement.py MOVEMENT_LITERALS). This raw-capture set is deliberately broader and
# is NOT the active Movement contract.
#
# CLOSE/codex-review-3 P2-A: renamed from MOVEMENT_LITERALS ->
# RAW_CAPTURE_MOVEMENT_WORDS so it is NOT mistaken for the active Link Movement
# enum (a reviewer read the old same-name constant as if support re-accepted
# return/hold/stop/pass as live Link movements). It is raw-log historical
# tolerance only; it authors no Movement and is not read as the active contract.
RAW_CAPTURE_MOVEMENT_WORDS = frozenset({"forward", "return", "hold", "stop", "reroute", "pass"})
ENVELOPE_FIELD_KEYS = frozenset(
    {
        "event_id",
        "source_truth",
        "event_type",
        "role_in_event",
        "axis_attribution",
        "raw_ref",
        "not_proven",
        "actor_ref",
        "building_ref",
        "brick_ref",
        "public_fact_refs",
        "receipt_text",
    }
)

DEFAULT_PROOF_LIMITS = (
    "support evidence only",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)
BRICK_WORK_KEYS = frozenset(
    {
        "work_statement",
        "comparison_rule",
        "required_return_shape",
        "source_facts",
    }
)


@dataclass(frozen=True)
class CaptureEvent:
    """One passive CAP-BOOT-1 receipt event."""

    event_id: str
    event_type: str
    role_in_event: str
    axis_attribution: str
    raw_ref: str
    not_proven: tuple[str, ...]
    source_truth: bool = False
    actor_ref: str | None = None
    building_ref: str | None = None
    brick_ref: str | None = None
    public_fact_refs: tuple[str, ...] = ()
    receipt_text: str | None = None
    facts: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _required_text("event_id", self.event_id))
        object.__setattr__(self, "event_type", _required_literal("event_type", self.event_type, CAPTURE_EVENT_TYPES))
        object.__setattr__(
            self,
            "role_in_event",
            _required_literal("role_in_event", self.role_in_event, CAPTURE_ROLE_LITERALS),
        )
        object.__setattr__(
            self,
            "axis_attribution",
            _required_literal("axis_attribution", self.axis_attribution, CAPTURE_AXIS_ATTRIBUTIONS),
        )
        object.__setattr__(self, "raw_ref", _required_text("raw_ref", self.raw_ref))
        object.__setattr__(self, "not_proven", _text_tuple("not_proven", self.not_proven, required=True))
        if self.source_truth is not False:
            raise ValueError("source_truth must be false when present")
        object.__setattr__(self, "actor_ref", _optional_text("actor_ref", self.actor_ref))
        object.__setattr__(self, "building_ref", _optional_text("building_ref", self.building_ref))
        object.__setattr__(self, "brick_ref", _optional_text("brick_ref", self.brick_ref))
        object.__setattr__(
            self,
            "public_fact_refs",
            _text_tuple("public_fact_refs", self.public_fact_refs, required=False),
        )
        object.__setattr__(self, "receipt_text", _optional_text("receipt_text", self.receipt_text))
        facts = _normalize_json_object(
            "facts",
            self.facts,
            allow_top_level_movement=self.event_type == "link_movement",
            forbidden_normalized_keys=ENVELOPE_FIELD_KEYS,
        )
        _validate_movement_fact_context(self.event_type, facts)
        object.__setattr__(self, "facts", facts)
        _validate_event_minimum_evidence(self)

    def to_json_object(self) -> dict[str, JsonValue]:
        base: dict[str, JsonValue] = {
            "event_id": self.event_id,
            "source_truth": False,
            "event_type": self.event_type,
            "role_in_event": self.role_in_event,
            "axis_attribution": self.axis_attribution,
            "raw_ref": self.raw_ref,
            "not_proven": self.not_proven,
        }
        if self.actor_ref is not None:
            base["actor_ref"] = self.actor_ref
        if self.building_ref is not None:
            base["building_ref"] = self.building_ref
        if self.brick_ref is not None:
            base["brick_ref"] = self.brick_ref
        if self.public_fact_refs:
            base["public_fact_refs"] = self.public_fact_refs
        if self.receipt_text is not None:
            base["receipt_text"] = self.receipt_text
        for key, value in self.facts.items():
            if key in base:
                raise ValueError(f"facts must not override capture envelope field {key!r}")
            base[key] = value
        return base


@dataclass(frozen=True)
class BuildingLifecyclePacket:
    """Caller-supplied Building lifecycle material."""

    building_id: str
    building_work: JsonObject
    capture_events: tuple[CaptureEvent, ...]
    raw_manifest: JsonObject
    evidence_manifest: JsonObject
    proof_limits: tuple[str, ...] = DEFAULT_PROOF_LIMITS

    def __post_init__(self) -> None:
        object.__setattr__(self, "building_id", _path_segment("building_id", self.building_id))
        object.__setattr__(self, "building_work", _normalize_json_object("building_work", self.building_work))
        _require_fact_keys(self.building_work, BRICK_WORK_KEYS, "building_work")
        object.__setattr__(
            self,
            "capture_events",
            _capture_event_tuple("capture_events", self.capture_events),
        )
        object.__setattr__(self, "raw_manifest", _normalize_json_object("raw_manifest", self.raw_manifest))
        object.__setattr__(
            self,
            "evidence_manifest",
            _normalize_json_object("evidence_manifest", self.evidence_manifest),
        )
        object.__setattr__(
            self,
            "proof_limits",
            _text_tuple("proof_limits", self.proof_limits, required=True),
        )


@dataclass(frozen=True)
class BuildingLifecycleWriteResult:
    """Files written for one Building lifecycle packet."""

    root: Path
    written_files: tuple[Path, ...]
    proof_limits: tuple[str, ...] = DEFAULT_PROOF_LIMITS


@dataclass(frozen=True)
class BuildingLifecycleRecorder:
    """Write caller-supplied lifecycle records without judging them."""

    output_root: Path | str = DEFAULT_BUILDINGS_ROOT
    overwrite_existing: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_root", Path(self.output_root))
        object.__setattr__(self, "overwrite_existing", bool(self.overwrite_existing))

    def planned_paths(self, packet: BuildingLifecyclePacket) -> tuple[Path, ...]:
        """Return deterministic lifecycle output paths without writing files."""

        root = self._building_root(packet.building_id)
        return (
            root / "work" / "building-work.json",
            root / "capture" / "events.jsonl",
            root / "raw" / "raw-manifest.json",
            root / "evidence" / "evidence-manifest.json",
        )

    def write_building_lifecycle(
        self,
        packet: BuildingLifecyclePacket,
    ) -> BuildingLifecycleWriteResult:
        """Write one caller-supplied Building lifecycle packet."""

        root = self._building_root(packet.building_id)
        self._prepare_building_root(root)
        written: list[Path] = []
        recorded_at = graph_ready_timestamp()
        self._write_json(
            root / "work" / "building-work.json",
            graph_ready_json_object(
                packet.building_work,
                building_id=packet.building_id,
                local_id="work/building-work.json",
                recorded_at=recorded_at,
                event_type="bp.building_work",
            ),
            written,
        )
        self._write_jsonl(
            root / "capture" / "events.jsonl",
            tuple(
                graph_ready_capture_event(
                    event.to_json_object(),
                    building_id=packet.building_id,
                    recorded_at=recorded_at,
                )
                for event in packet.capture_events
            ),
            written,
        )
        self._write_json(
            root / "raw" / "raw-manifest.json",
            graph_ready_json_object(
                packet.raw_manifest,
                building_id=packet.building_id,
                local_id="raw/raw-manifest.json",
                recorded_at=recorded_at,
                event_type="bp.raw_manifest",
            ),
            written,
        )
        self._write_json(
            root / "evidence" / "evidence-manifest.json",
            graph_ready_json_object(
                packet.evidence_manifest,
                building_id=packet.building_id,
                local_id="evidence/evidence-manifest.json",
                recorded_at=recorded_at,
                event_type="bp.evidence_manifest",
            ),
            written,
        )
        return BuildingLifecycleWriteResult(
            root=root,
            written_files=tuple(written),
            proof_limits=packet.proof_limits,
        )

    def _building_root(self, building_id: str) -> Path:
        return self.output_root / building_id

    def _prepare_building_root(self, root: Path) -> None:
        if root.exists():
            if not root.is_dir():
                raise NotADirectoryError(f"Building lifecycle root is not a directory: {root}")
            if not self.overwrite_existing:
                raise FileExistsError(
                    "Building lifecycle root already exists; choose a new building_id "
                    "or pass overwrite_existing=True"
                )
        root.mkdir(parents=True, exist_ok=True)

    def _write_json(self, path: Path, value: JsonObject, written: list[Path]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_json_text(value), encoding="utf-8")
        written.append(path)

    def _write_jsonl(
        self,
        path: Path,
        values: tuple[JsonObject, ...],
        written: list[Path],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(_json_line(value) for value in values), encoding="utf-8")
        written.append(path)


def planned_building_lifecycle_paths(
    packet: BuildingLifecyclePacket,
    output_root: Path | str = DEFAULT_BUILDINGS_ROOT,
) -> tuple[Path, ...]:
    """Return deterministic lifecycle output paths without writing files."""

    return BuildingLifecycleRecorder(output_root=output_root).planned_paths(packet)


def write_building_lifecycle(
    packet: BuildingLifecyclePacket,
    output_root: Path | str = DEFAULT_BUILDINGS_ROOT,
    overwrite_existing: bool = False,
) -> BuildingLifecycleWriteResult:
    """Write a Building lifecycle packet to the output root."""

    return BuildingLifecycleRecorder(
        output_root=output_root,
        overwrite_existing=overwrite_existing,
    ).write_building_lifecycle(packet)


def graph_ready_timestamp() -> str:
    """Return an RFC 3339 UTC timestamp for support compatibility metadata."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def graph_ready_building_urn(building_id: str, local_id: str) -> str:
    """Return the Brick Protocol graph-ready URN for a local Building item."""

    safe_building_id = _path_segment("building_id", building_id)
    safe_local = _required_text("local_id", local_id).replace("\\", "/").strip("/")
    if not safe_local or any(part in {"", ".", ".."} for part in safe_local.split("/")):
        raise ValueError("local_id must be a safe relative identifier")
    return f"urn:bp:building:{safe_building_id}::{safe_local}"


def graph_ready_json_object(
    value: Mapping[str, Any],
    *,
    building_id: str,
    local_id: str,
    recorded_at: str,
    event_type: str,
    subject: str | None = None,
) -> dict[str, JsonValue]:
    """Attach graph-ready compatibility metadata to a JSON object."""

    normalized = _normalize_graph_ready_json_object("graph_ready", value)
    graph_id = graph_ready_building_urn(building_id, local_id)
    envelope: dict[str, JsonValue] = {
        "@context": GRAPH_READY_CONTEXT,
        "@id": graph_id,
        "id": graph_id,
        "source": f"urn:bp:building:{_path_segment('building_id', building_id)}",
        "specversion": "1.0",
        "type": _required_text("event_type", event_type),
        "time": _required_text("recorded_at", recorded_at),
        "recorded_at": _required_text("recorded_at", recorded_at),
        "generatedAtTime": _required_text("recorded_at", recorded_at),
        "dataschema": GRAPH_READY_DATASCHEMA,
        "schema_version": GRAPH_READY_SCHEMA_VERSION,
        "datacontenttype": "application/json",
        "subject": subject or local_id,
    }
    envelope.update(normalized)
    return envelope


def graph_ready_capture_event(
    event: Mapping[str, Any],
    *,
    building_id: str,
    recorded_at: str,
) -> dict[str, JsonValue]:
    """Attach graph-ready compatibility metadata to one capture event."""

    normalized = _normalize_graph_ready_json_object("capture_event", event)
    event_id = normalized.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("capture_event requires event_id for graph-ready metadata")
    event_type = normalized.get("event_type")
    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError("capture_event requires event_type for graph-ready metadata")
    subject = (
        normalized.get("brick_ref")
        or normalized.get("actor_ref")
        or normalized.get("building_ref")
        or normalized.get("raw_ref")
        or event_id
    )
    if not isinstance(subject, str):
        subject = event_id
    return {
        **graph_ready_json_object(
            {"data": normalized},
            building_id=building_id,
            local_id=f"capture/events.jsonl/{event_id}",
            recorded_at=recorded_at,
            event_type=f"bp.capture.{event_type}",
            subject=subject,
        ),
        **normalized,
    }


def _normalize_graph_ready_json_object(name: str, value: Mapping[str, Any]) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object mapping")
    normalized: dict[str, JsonValue] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError(f"{name} keys must be non-empty text")
        key = raw_key.strip()
        normalized[key] = _normalize_graph_ready_json_value(f"{name}.{key}", raw_value)
    return normalized


def _normalize_graph_ready_json_value(name: str, value: object) -> JsonValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return _normalize_graph_ready_json_object(name, value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_graph_ready_json_value(f"{name}[]", item) for item in value]
    raise TypeError(f"{name} must be JSON-serializable")


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def _optional_text(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _required_text(name, value)


def _required_literal(name: str, value: str, allowed: frozenset[str]) -> str:
    text = _required_text(name, value)
    if text not in allowed:
        raise ValueError(f"{name} must be one of {sorted(allowed)!r}")
    return text


def _path_segment(name: str, value: str) -> str:
    text = _required_text(name, value)
    if "/" in text or "\\" in text or text in {".", ".."}:
        raise ValueError(f"{name} must be one path segment")
    return text


def _text_tuple(name: str, value: Sequence[str], *, required: bool) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence of text values")
    texts = tuple(_required_text(f"{name}[{index}]", item) for index, item in enumerate(value))
    if required and not texts:
        raise ValueError(f"{name} must not be empty")
    return texts


def _capture_event_tuple(
    name: str,
    value: Sequence[CaptureEvent],
) -> tuple[CaptureEvent, ...]:
    if isinstance(value, CaptureEvent) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence of CaptureEvent values")
    events: list[CaptureEvent] = []
    for index, item in enumerate(value):
        if not isinstance(item, CaptureEvent):
            raise TypeError(f"{name}[{index}] must be CaptureEvent")
        events.append(item)
    return tuple(events)


def _normalize_json_object(
    name: str,
    value: JsonObject,
    *,
    allow_top_level_movement: bool = False,
    forbidden_normalized_keys: frozenset[str] = frozenset(),
) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a JSON object mapping")
    normalized: dict[str, JsonValue] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError(f"{name} keys must be non-empty text")
        key = raw_key.strip()
        normalized_key = _normalize_key(key)
        if normalized_key in forbidden_normalized_keys:
            raise ValueError(f"{name} must not override capture envelope field {raw_key!r}")
        if normalized_key == MOVEMENT_LITERAL_KEY and allow_top_level_movement:
            if MOVEMENT_LITERAL_KEY in normalized:
                raise ValueError(f"{name} contains duplicate movement fact key")
            normalized[MOVEMENT_LITERAL_KEY] = _normalize_json_value(f"{name}.{key}", raw_value)
            continue
        if normalized_key in FORBIDDEN_CAPTURE_KEYS:
            raise ValueError(f"{name} contains forbidden capture key {raw_key!r}")
        if normalized_key == "source_truth" and raw_value is not False:
            raise ValueError(f"{name} may not set source_truth to anything except false")
        normalized[key] = _normalize_json_value(f"{name}.{key}", raw_value)
    return normalized


def _validate_movement_fact_context(event_type: str, facts: JsonObject) -> None:
    movement_value = facts.get(MOVEMENT_LITERAL_KEY)
    if movement_value is None:
        return
    if event_type != "link_movement":
        raise ValueError("movement may appear only on link_movement capture events")
    if movement_value not in RAW_CAPTURE_MOVEMENT_WORDS:
        raise ValueError(
            "raw-capture movement word must be in the historical raw-capture set "
            "(NOT the active Link Movement contract, which is forward/reroute only)"
        )


def _validate_event_minimum_evidence(event: CaptureEvent) -> None:
    facts = event.facts
    event_type = event.event_type

    if event_type == "building_opened":
        _require_event_attr(event, "building_ref")
        _require_one_fact(facts, ("goal_ref", "initiating_work_ref", "work_ref"), event_type)
    elif event_type == "brick_opened":
        _require_event_attr(event, "brick_ref")
        if not event.public_fact_refs:
            _require_fact_keys(facts, BRICK_WORK_KEYS, event_type)
    elif event_type == "agent_received":
        _require_event_attr(event, "actor_ref")
        _require_fact_keys(facts, ("received_work_ref",), event_type)
    elif event_type == "agent_returned":
        _require_event_attr(event, "actor_ref")
        _require_fact_keys(facts, ("received_work_ref",), event_type)
        if event.receipt_text is None and not _has_normalized_key(facts, "returned_summary"):
            raise ValueError("agent_returned requires receipt_text or returned_summary")
    elif event_type == "link_transfer":
        _require_fact_keys(facts, ("from_ref", "to_ref", "transferred_fact_refs"), event_type)
    elif event_type == "link_carry":
        _require_fact_keys(facts, ("from_ref", "to_ref", "carried_fact_refs"), event_type)
    elif event_type == "link_gate_receipt":
        _require_fact_keys(facts, ("stage", "sufficiency"), event_type)
        _require_one_fact(facts, ("required_public_facts", "missing_required_facts"), event_type)
    elif event_type == "brick_compared":
        _require_fact_keys(
            facts,
            ("expected_work_ref", "observed_return_ref", "comparison_rule_ref"),
            event_type,
        )
        _require_one_fact(facts, ("matched", "mismatched", "unknown"), event_type)
    elif event_type == "link_movement":
        if not event.public_fact_refs:
            raise ValueError("link_movement requires public_fact_refs used as Movement input")
        if event.receipt_text is None and not _has_normalized_key(facts, "reason_ref"):
            raise ValueError("link_movement requires receipt_text or reason_ref")
    elif event_type == "support_note":
        if event.receipt_text is None:
            raise ValueError("support_note requires receipt_text")


def _require_event_attr(event: CaptureEvent, attr: str) -> None:
    if getattr(event, attr) is None:
        raise ValueError(f"{event.event_type} requires {attr}")


def _require_fact_keys(facts: JsonObject, keys: Sequence[str] | frozenset[str], event_type: str) -> None:
    missing = [key for key in keys if not _has_normalized_key(facts, key)]
    if missing:
        raise ValueError(f"{event_type} requires facts keys {missing!r}")


def _require_one_fact(facts: JsonObject, keys: Sequence[str], event_type: str) -> None:
    if not any(_has_normalized_key(facts, key) for key in keys):
        raise ValueError(f"{event_type} requires one of facts keys {tuple(keys)!r}")


def _has_normalized_key(facts: JsonObject, expected: str) -> bool:
    expected_key = _normalize_key(expected)
    return any(_normalize_key(key) == expected_key for key in facts)


def _normalize_json_value(name: str, value: object) -> JsonValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return _normalize_json_object(name, value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(_normalize_json_value(f"{name}[]", item) for item in value)
    raise TypeError(f"{name} must be JSON-serializable")


def _normalize_key(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()


def _json_text(value: JsonObject) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _json_line(value: JsonObject) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


__all__ = [
    "BuildingLifecyclePacket",
    "BuildingLifecycleRecorder",
    "BuildingLifecycleWriteResult",
    "buildings_root_for",
    "CAPTURE_AXIS_ATTRIBUTIONS",
    "CAPTURE_EVENT_TYPES",
    "CAPTURE_ROLE_LITERALS",
    "CaptureEvent",
    "DEFAULT_BUILDINGS_ROOT",
    "REPO_ROOT",
    "GRAPH_READY_CONTEXT",
    "GRAPH_READY_DATASCHEMA",
    "GRAPH_READY_SCHEMA_VERSION",
    "graph_ready_building_urn",
    "graph_ready_capture_event",
    "graph_ready_json_object",
    "graph_ready_timestamp",
    "is_project_id_slug",
    "planned_building_lifecycle_paths",
    "project_ref_for_building_root",
    "write_building_lifecycle",
]

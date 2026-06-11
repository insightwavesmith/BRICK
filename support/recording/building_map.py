"""Deterministic writer for Building Graph maps.

This support writer materializes a graph-map packet exactly as supplied by the
caller, or folds an existing Building evidence root into the same graph-map
shape through a conservative support projection. It does not judge graph
quality, choose Movement, or replace raw / claim_trace evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, TypeAlias, Union

from .capture import DEFAULT_BUILDINGS_ROOT, graph_ready_json_object, graph_ready_timestamp


JsonScalar: TypeAlias = Union[str, int, float, bool, None]
JsonValue: TypeAlias = Union[JsonScalar, dict[str, "JsonValue"], list["JsonValue"]]
JsonObject: TypeAlias = dict[str, JsonValue]

# The Building map lives under the canonical Building root; alias the single
# repo-anchored source rather than redefine a cwd-relative string.
DEFAULT_BUILDING_MAP_ROOT = DEFAULT_BUILDINGS_ROOT
GRAPH_MAP_KIND = "building_graph_map"
SAFE_PATH_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")
GRAPH_PROFILE = "planning-v0"

FORBIDDEN_TOP_LEVEL_KEYS = frozenset(
    {
        "source_truth",
        "success",
        "success_judgment",
        "failure",
        "verdict",
        "quality",
        "quality_judgment",
        "runtime",
        "provider",
        "scheduler",
        "storage",
        "wiki",
        "dashboard",
        "movement_authority",
    }
)


@dataclass(frozen=True)
class BuildingMapWriteResult:
    """File written for one caller-supplied Building Graph map."""

    root: Path
    path: Path
    written_files: tuple[Path, ...]


def planned_building_map_path(
    packet: Mapping[str, Any],
    output_root: Path | str = DEFAULT_BUILDING_MAP_ROOT,
) -> Path:
    """Return the deterministic building-map output path without writing."""

    normalized = _validated_packet(packet)
    return _building_map_path(normalized["building_id"], output_root)


def write_building_map(
    packet: Mapping[str, Any],
    output_root: Path | str = DEFAULT_BUILDING_MAP_ROOT,
    overwrite_existing: bool = False,
) -> BuildingMapWriteResult:
    """Write one caller-supplied graph-map packet to work/building-map.json."""

    normalized = _validated_packet(packet)
    recorded_at = graph_ready_timestamp()
    normalized = _validated_packet(
        graph_ready_json_object(
            normalized,
            building_id=str(normalized["building_id"]),
            local_id="work/building-map.json",
            recorded_at=recorded_at,
            event_type="bp.building_graph_map",
        )
    )
    path = _building_map_path(normalized["building_id"], output_root)
    if path.exists():
        if path.is_dir():
            raise IsADirectoryError(f"Building map path is a directory: {path}")
        if not overwrite_existing:
            raise FileExistsError(
                "Building map already exists; pass overwrite_existing=True "
                "to replace it"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json_text(normalized), encoding="utf-8")
    return BuildingMapWriteResult(
        root=path.parent.parent,
        path=path,
        written_files=(path,),
    )


def building_map_packet_from_evidence(
    building_root: Path | str,
) -> JsonObject:
    """Create a conservative graph-map packet from one Building evidence root.

    The packet is a support projection over observed files and refs. It does
    not invent missing Brick boundaries, Agent returns, Link movements, or
    sufficiency facts. If only one Brick boundary is observed, no Link edge is
    created.
    """

    root = Path(building_root)
    if not root.is_dir():
        raise NotADirectoryError(f"Building root does not exist: {root}")
    building_id = _building_id_from_root(root)
    raw_manifest = _read_json_if_present(root / "raw" / "raw-manifest.json")
    work_contract = _read_json_if_present(root / "evidence" / "claim_trace" / "brick" / "work_contract.json")
    agent_claims = _read_json_if_present(root / "evidence" / "claim_trace" / "agent" / "returned_claims.json")

    all_raw_refs = _raw_refs_from_manifest(raw_manifest)
    brick_raw_refs = _raw_refs_from_value(work_contract) or _raw_refs_from_value(
        _read_json_if_present(root / "work" / "building-work.json")
    )
    agent_raw_refs = _raw_refs_from_value(agent_claims)

    agent_binding_refs: list[JsonValue] = []
    agent_bindings: list[JsonValue] = []
    if agent_claims:
        agent_binding_refs.append("binding-001")
        agent_bindings.append(
            {
                "agent_binding_id": "binding-001",
                "brick_instance_ref": "brick-001",
                "agent_performer_ref": _agent_performer_ref(root, agent_claims),
                "binding_role": "primary",
                "raw_refs": agent_raw_refs,
                "proof_limits": [
                    "Agent binding is projected from observed agent claim/raw refs only",
                    "not source truth",
                    "not success judgment",
                    "not quality judgment",
                    "not Movement authority",
                ],
                "not_proven": [
                    "performer quality",
                    "provider/runtime behavior",
                    "Agent self-classification",
                ],
            }
        )

    packet: JsonObject = {
        "kind": GRAPH_MAP_KIND,
        "building_id": building_id,
        "profile": GRAPH_PROFILE,
        "brick_instances": [
            {
                "brick_instance_id": "brick-001",
                "brick_work_ref": "work/building-work.json",
                "attempt_index": 1,
                "parent_building_ref": building_id,
                "agent_binding_refs": agent_binding_refs,
                "raw_refs": brick_raw_refs,
                "proof_limits": [
                    "Brick instance is projected from observed work/claim refs only",
                    "not source truth",
                    "not success judgment",
                    "not quality judgment",
                    "not Movement authority",
                ],
                "not_proven": [
                    "content quality",
                    "work completion",
                    "source truth",
                ],
            }
        ],
        "agent_bindings": agent_bindings,
        "link_edges": [],
        "groups": [],
        "raw_refs": all_raw_refs,
        "proof_limits": [
            "support graph projection only",
            "raw and claim_trace evidence remain authoritative evidence surfaces",
            "single observed Brick boundary creates no Link edge",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "graph semantic completeness",
            "external graph database import",
            "runtime behavior",
            "source truth",
            "success judgment",
            "quality judgment",
            "Movement authority",
        ],
    }
    return _validated_packet(packet)


def write_building_map_from_evidence(
    building_root: Path | str,
    *,
    overwrite_existing: bool = False,
) -> BuildingMapWriteResult:
    """Materialize a graph map for one existing Building evidence root."""

    root = Path(building_root)
    packet = building_map_packet_from_evidence(root)
    return write_building_map(
        packet,
        output_root=root.parent,
        overwrite_existing=overwrite_existing,
    )


def building_graph_index_from_evidence_roots(
    building_roots: list[Path | str],
) -> JsonObject:
    """Create a multi-Building support index from Building evidence roots."""

    packets = [building_map_packet_from_evidence(root) for root in building_roots]
    buildings: list[JsonValue] = []
    brick_nodes: list[JsonValue] = []
    agent_binding_nodes: list[JsonValue] = []
    link_edges: list[JsonValue] = []
    for packet in packets:
        building_id = packet["building_id"]
        buildings.append(
            {
                "building_id": building_id,
                "map_ref": f"project/brick-protocol/buildings/{building_id}/work/building-map.json",
                "raw_refs": packet.get("raw_refs", []),
            }
        )
        for brick in packet.get("brick_instances", []):
            if isinstance(brick, Mapping):
                brick_nodes.append(
                    {
                        "building_id": building_id,
                        "brick_instance_id": brick.get("brick_instance_id"),
                        "agent_binding_refs": brick.get("agent_binding_refs", []),
                    }
                )
        for binding in packet.get("agent_bindings", []):
            if isinstance(binding, Mapping):
                agent_binding_nodes.append(
                    {
                        "building_id": building_id,
                        "agent_binding_id": binding.get("agent_binding_id"),
                        "brick_instance_ref": binding.get("brick_instance_ref"),
                    }
                )
        for edge in packet.get("link_edges", []):
            if isinstance(edge, Mapping):
                link_edges.append(
                    {
                        "building_id": building_id,
                        "link_edge_id": edge.get("link_edge_id"),
                        "source_brick_instance_ref": edge.get("source_brick_instance_ref"),
                        "target_brick_instance_ref": edge.get("target_brick_instance_ref"),
                    }
                )
    index: JsonObject = {
        "kind": "building_graph_index",
        "profile": GRAPH_PROFILE,
        "buildings": buildings,
        "brick_nodes": brick_nodes,
        "agent_binding_nodes": agent_binding_nodes,
        "link_edges": link_edges,
        "proof_limits": [
            "multi-building support projection only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
            "not semantic graph completeness",
        ],
        "not_proven": [
            "external graph database import",
            "multi-building inference correctness",
            "source truth",
            "success judgment",
            "quality judgment",
            "Movement authority",
        ],
    }
    return _validated_index(index)


def _building_map_path(building_id: JsonValue, output_root: Path | str) -> Path:
    if not isinstance(building_id, str):
        raise TypeError("building_id must be text")
    return Path(output_root) / building_id / "work" / "building-map.json"


def _building_id_from_root(root: Path) -> str:
    building_work = _read_json_if_present(root / "work" / "building-work.json")
    if isinstance(building_work, Mapping):
        value = building_work.get("building_id")
        if isinstance(value, str) and value.strip():
            return _path_segment("building_id", value.strip())
    return _path_segment("building_id", root.name)


def _read_json_if_present(path: Path) -> Any:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_refs_from_manifest(value: Any) -> list[JsonValue]:
    refs: list[str] = []
    if not isinstance(value, Mapping):
        return refs
    raw_refs = value.get("raw_refs")
    if isinstance(raw_refs, Mapping):
        refs.extend(key for key in raw_refs if isinstance(key, str) and key.strip())
    elif isinstance(raw_refs, list):
        refs.extend(item for item in raw_refs if isinstance(item, str) and item.strip())
    for key in ("entries", "raw_streams"):
        entries = value.get(key)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, Mapping):
                    refs.extend(_raw_refs_from_value(entry))
    return sorted(dict.fromkeys(refs))


def _raw_refs_from_value(value: Any) -> list[JsonValue]:
    refs: list[str] = []
    if isinstance(value, Mapping):
        raw_ref = value.get("raw_ref")
        if isinstance(raw_ref, str) and raw_ref.strip():
            refs.append(raw_ref)
        raw_refs = value.get("raw_refs")
        if isinstance(raw_refs, Mapping):
            refs.extend(key for key in raw_refs if isinstance(key, str) and key.strip())
        elif isinstance(raw_refs, list):
            refs.extend(item for item in raw_refs if isinstance(item, str) and item.strip())
        for child in value.values():
            refs.extend(str(item) for item in _raw_refs_from_value(child))
    elif isinstance(value, list):
        for item in value:
            refs.extend(str(child) for child in _raw_refs_from_value(item))
    return sorted(dict.fromkeys(refs))


def _agent_performer_ref(root: Path, agent_claims: Any) -> str:
    observed_agents: list[str] = []
    for raw_path in sorted((root / "raw").glob("agent-*.jsonl")):
        try:
            for line in raw_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if isinstance(record, Mapping):
                    agent = record.get("agent")
                    if isinstance(agent, str) and agent.strip():
                        observed_agents.append(agent.strip())
        except (OSError, json.JSONDecodeError):
            continue
    distinct_agents = sorted(dict.fromkeys(observed_agents))
    if len(distinct_agents) > 1:
        raise ValueError(
            "multiple observed agent performers require an explicit Agent binding"
        )
    if distinct_agents:
        return _performer_ref(distinct_agents[0])
    if isinstance(agent_claims, Mapping):
        performer = agent_claims.get("agent") or agent_claims.get("performer")
        if isinstance(performer, str) and performer.strip():
            return _performer_ref(performer)
    return "performer-unknown"


def _performer_ref(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return f"performer-{normalized or 'unknown'}"


def _validated_packet(packet: Mapping[str, Any]) -> JsonObject:
    if not isinstance(packet, Mapping):
        raise TypeError("packet must be a JSON object mapping")
    normalized = _normalize_json_object("packet", packet)

    _reject_forbidden_top_level_keys("packet", normalized)

    if normalized.get("kind") != GRAPH_MAP_KIND:
        raise ValueError("packet.kind must be 'building_graph_map'")

    building_id = normalized.get("building_id")
    if not isinstance(building_id, str):
        raise TypeError("packet.building_id must be text")
    _path_segment("building_id", building_id)

    profile = normalized.get("profile")
    if not isinstance(profile, str) or not profile.strip():
        raise ValueError("packet.profile must be present as non-empty text")

    for key in ("brick_instances", "agent_bindings", "link_edges"):
        if not isinstance(normalized.get(key), list):
            raise TypeError(f"packet.{key} must be a JSON array")

    groups = normalized.get("groups", [])
    if not isinstance(groups, list):
        raise TypeError("packet.groups must be absent or a JSON array")

    return normalized


def _validated_index(index: Mapping[str, Any]) -> JsonObject:
    if not isinstance(index, Mapping):
        raise TypeError("index must be a JSON object mapping")
    normalized = _normalize_json_object("index", index)
    _reject_forbidden_top_level_keys("index", normalized)
    if normalized.get("kind") != "building_graph_index":
        raise ValueError("index.kind must be 'building_graph_index'")
    profile = normalized.get("profile")
    if not isinstance(profile, str) or not profile.strip():
        raise ValueError("index.profile must be present as non-empty text")
    for key in ("buildings", "brick_nodes", "agent_binding_nodes", "link_edges"):
        if not isinstance(normalized.get(key), list):
            raise TypeError(f"index.{key} must be a JSON array")
    return normalized


def _reject_forbidden_top_level_keys(name: str, value: Mapping[str, JsonValue]) -> None:
    forbidden = sorted(
        raw_key
        for raw_key in value
        if _normalize_key(raw_key) in FORBIDDEN_TOP_LEVEL_KEYS
    )
    if forbidden:
        raise ValueError(f"{name} contains forbidden top-level key(s): {forbidden!r}")


def _normalize_json_object(name: str, value: Mapping[str, Any]) -> JsonObject:
    normalized: JsonObject = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            raise ValueError(f"{name} keys must be non-empty text")
        key = raw_key.strip()
        normalized[key] = _normalize_json_value(f"{name}.{key}", raw_value)
    return normalized


def _normalize_json_value(name: str, value: Any) -> JsonValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return _normalize_json_object(name, value)
    if isinstance(value, list):
        return [_normalize_json_value(f"{name}[]", item) for item in value]
    raise TypeError(f"{name} must be JSON-serializable")


def _path_segment(name: str, value: str) -> str:
    if not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    if (
        "/" in value
        or "\\" in value
        or value in {".", ".."}
        or value.startswith(".")
    ):
        raise ValueError(f"{name} must be one safe path segment")
    if SAFE_PATH_SEGMENT.fullmatch(value) is None:
        raise ValueError(f"{name} contains an unsafe path character")
    return value


def _normalize_key(value: str) -> str:
    return value.strip().replace("-", "_").replace(" ", "_").lower()


def _json_text(value: JsonObject) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


__all__ = [
    "BuildingMapWriteResult",
    "DEFAULT_BUILDING_MAP_ROOT",
    "GRAPH_PROFILE",
    "GRAPH_MAP_KIND",
    "building_graph_index_from_evidence_roots",
    "building_map_packet_from_evidence",
    "planned_building_map_path",
    "write_building_map",
    "write_building_map_from_evidence",
]

#!/usr/bin/env python3
"""Validate Building Graph Model support maps.

This checker is support evidence only. It checks graph-map shape, reference
resolution, and forbidden support-surface authority claims. It does not prove
source truth, success judgment, quality judgment, or Movement authority.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


GRAPH_KIND = "building_graph_map"
ADMITTED_PROFILES = {"planning-v0"}
# FRONTIER-FOSSIL (Smith disposition 0612, option c): adapter-30-s1-park's map
# was REWRITTEN by the PRE-REPAIR crashed-resume frontier writer (phantom
# binding/edge/group refs), and the building is unresumable by design (no held
# record predates the fix). Evidence is append-only, so the map cannot be
# corrected. This dated registry names THAT ONE building as a preserved fossil;
# it exempts nothing else — any other map with the same defects still REDs.
CRASHED_RESUME_FOSSIL_BUILDING_IDS: set[str] = {"adapter-30-s1-park"}

BINDING_ROLES = {"primary", "support", "review"}
EDGE_ROLES = {
    "primary_flow",
    "fan_out",
    "fan_in",
    "reroute",
    "replay_segment",
    "revision_chain",
    "review_flow",
    "support_flow",
}
GROUP_ROLES = {
    "fan_out",
    "fan_in",
    "revision_chain",
    "review_flow",
    "support_flow",
}
GROUP_MEMBER_KINDS = {"brick_instance", "link_edge"}
CLAIM_TRACE_RELATIVE_PATHS = (
    ("evidence", "claim_trace", "brick", "work_contract.json"),
    ("evidence", "claim_trace", "agent", "returned_claims.json"),
    ("evidence", "claim_trace", "link", "transfer_trace.json"),
    ("evidence", "claim_trace", "link", "carry_trace.json"),
    ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
    ("evidence", "claim_trace", "link", "movement_trace.json"),
)

HISTORICAL_MAP_KEYS = {"record_type", "status", "file_groups", "root"}
ENDPOINT_KEYS = {
    "source_brick_instance_ref",
    "target_brick_instance_ref",
    "source_boundary_ref",
    "target_boundary_ref",
    "handoff_target",
    "handoff_target_ref",
    "endpoint",
    "source",
    "target",
}
LABEL_KEYS = {
    "label",
    "group_label",
    "display_label",
    "role_label",
    "name",
    "title",
    "description",
    "note",
    "notes",
    "reason",
    "status",
    "verdict",
    "classification",
    "result",
    "claim",
    "content",
    "authority_claim",
    "owner_claim",
}
AUTHORITY_KEYS = {
    "source_truth",
    "success_judgment",
    "quality_judgment",
    "movement_authority",
}
FORBIDDEN_OWNER_VALUES = {
    "runtime",
    "provider",
    "scheduler",
    "storage",
    "wiki",
    "dashboard",
    "reviewer",
    "operator",
    "model",
    "tool",
    "evidence",
}
FORBIDDEN_OWNER_KEYS = {
    "runtime_owner",
    "provider_owner",
    "scheduler_owner",
    "storage_owner",
    "wiki_owner",
    "dashboard_owner",
    "reviewer_endpoint",
    "operator_endpoint",
    "model_endpoint",
    "tool_endpoint",
    "evidence_actor",
    "checker_as_success",
    "writer_admission",
    "cap_boot_9",
}
INLINE_RAW_KEYS = {
    "raw_body",
    "raw_text",
    "raw_content",
    "raw_payload",
    "raw_transcript",
    "transcript",
    "prompt_stack",
}
CLAIM_TRACE_BODY_KEYS = {
    "claim_trace_body",
    "claim_trace_fact_body",
    "claim_trace_fact",
    "public_fact_body",
    "fact_body",
}
TRANSITION_BODY_KEYS = {
    "transition_trace",
    "transition_trace_json",
    "transition_fact",
    "transition_body",
}
GRAPH_FACT_REF_KEYS = {
    "input_public_fact_refs",
    "produced_public_fact_refs",
    "public_fact_refs",
    "carried_fact_refs",
    "transfer_fact_ref",
    "transfer_fact_refs",
    "carry_fact_ref",
    "carry_fact_refs",
    "gate_fact_ref",
    "gate_fact_refs",
    "movement_fact_ref",
    "movement_fact_refs",
    "sufficiency_fact_ref",
    "sufficiency_fact_refs",
    "claim_trace_refs",
}
FORBIDDEN_LABEL_WORDS = {
    "success",
    "failure",
    "done",
    "not_done",
    "failed",
    "approved",
    "approval",
    "complete",
    "pass",
    "fail",
    "sufficiency",
    "sufficiency_verdict",
    "sufficiency verdict",
    "sufficient",
    "insufficient",
    "missing_required_facts",
    "source_truth",
    "source truth",
    "success_judgment",
    "success judgment",
    "quality_judgment",
    "quality judgment",
    "quality_judgement",
    "quality judgement",
    "movement_authority",
    "movement authority",
    "forward",
    "return",
    "hold",
    "stop",
    "reroute",
}
PROOF_LIMIT = (
    "proof limit: building-map graph support check only; this does not prove "
    "source truth, success judgment, quality judgment, Movement authority, "
    "runtime behavior, writer correctness, or graph semantic correctness."
)


def normalize_name(value: Any) -> str:
    return str(value).strip().replace("-", "_").replace(" ", "_").lower()


def truthy(value: Any) -> bool:
    return value not in (False, None, "", [], {})


def to_text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def scalar_texts(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from scalar_texts(item)


def nested_dicts(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from nested_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_dicts(child)


def path_label(path: Path, detail: str) -> str:
    return f"{path}: {detail}"


def read_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except OSError as exc:
        return None, [f"{path}: JSON read failed: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"{path}:{exc.lineno}: JSON parse failed: {exc.msg}"]


def resolve_map_path(path: Path) -> Path:
    if path.is_file():
        return path
    candidate = path / "work" / "building-map.json"
    if candidate.is_file():
        return candidate
    if path.name == "work" and (path / "building-map.json").is_file():
        return path / "building-map.json"
    return candidate


def building_root_for_map_path(map_path: Path) -> Path | None:
    if map_path.name == "building-map.json" and map_path.parent.name == "work":
        return map_path.parent.parent
    return None


def fixture_paths(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(child for child in path.rglob("*.json") if child.is_file())
    return [path]


def require_list(value: Mapping[str, Any], key: str, path: Path, violations: list[str]) -> list[Any]:
    item = value.get(key)
    if not isinstance(item, list):
        violations.append(path_label(path, f"{key} must be a JSON array"))
        return []
    return item


def require_mapping(item: Any, label: str, path: Path, violations: list[str]) -> Mapping[str, Any] | None:
    if not isinstance(item, Mapping):
        violations.append(path_label(path, f"{label} must be a JSON object"))
        return None
    return item


def text_id(item: Mapping[str, Any], key: str, label: str, path: Path, violations: list[str]) -> str | None:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        violations.append(path_label(path, f"{label} requires non-empty {key}"))
        return None
    return value


def duplicate_violations(values: list[str], label: str, path: Path) -> list[str]:
    counts = Counter(values)
    return [
        path_label(path, f"duplicate {label}: {value}")
        for value, count in sorted(counts.items())
        if count > 1
    ]


def is_raw_ref(value: str, raw_refs: set[str]) -> bool:
    lowered = value.strip().lower()
    return (
        lowered.startswith("raw:")
        or lowered.startswith("raw/")
        or "/raw/" in lowered
        or value in raw_refs
    )


def endpoint_problem(
    value: Any,
    *,
    brick_ids: set[str],
    agent_binding_ids: set[str],
    agent_performer_refs: set[str],
    agent_fact_refs: set[str],
    raw_refs: set[str],
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "endpoint must be a non-empty string"
    lowered = value.strip().lower()
    if lowered.startswith("agent:"):
        return "endpoint must not use an agent:* ref"
    if lowered.startswith(("agentfact:", "agent_fact:")):
        return "endpoint must not resolve to AgentFact refs"
    if value in agent_binding_ids:
        return "endpoint must not resolve to agent_binding_id"
    if value in agent_performer_refs:
        return "endpoint must not resolve to agent_performer_ref"
    if value in agent_fact_refs:
        return "endpoint must not resolve to AgentFact refs"
    if is_raw_ref(value, raw_refs):
        return "endpoint must not resolve to a raw evidence ref"
    if value not in brick_ids:
        return "endpoint must resolve to brick_instance_id, not prefix-only text"
    return None


def contains_forbidden_label_text(text: str) -> str | None:
    lowered = text.lower()
    normalized = lowered.replace("-", "_")
    tokenized = re.sub(r"[^a-z0-9]+", " ", lowered.replace("_", " "))
    for word in sorted(FORBIDDEN_LABEL_WORDS, key=len, reverse=True):
        word_norm = word.replace("-", "_").lower()
        if " " in word or "_" in word:
            if word_norm in normalized or word.lower() in lowered:
                return word
            continue
        if re.search(rf"(?<![a-z0-9_]){re.escape(word_norm)}(?![a-z0-9_])", normalized):
            return word
        if re.search(rf"(?<![a-z0-9]){re.escape(word.lower())}(?![a-z0-9])", tokenized):
            return word
    return None


def validate_forbidden_content(value: Any, path: Path, violations: list[str]) -> None:
    for item in nested_dicts(value):
        for key, child in item.items():
            key_norm = normalize_name(key)
            if key_norm in AUTHORITY_KEYS and truthy(child):
                violations.append(path_label(path, f"{key}: graph must not claim authority"))
            if key_norm in FORBIDDEN_OWNER_KEYS and truthy(child):
                violations.append(path_label(path, f"{key}: forbidden owner/authority claim"))
            if key_norm in {
                "owner",
                "owned_by",
                "authority",
                "authority_claim",
                "endpoint_owner",
                "owner_claim",
            }:
                child_text = to_text(child)
                if child_text and normalize_name(child_text) in FORBIDDEN_OWNER_VALUES:
                    violations.append(path_label(path, f"{key}: forbidden owner value {child_text!r}"))
            if key_norm in INLINE_RAW_KEYS and truthy(child):
                violations.append(path_label(path, f"{key}: graph must not inline raw bodies"))
            if key_norm in CLAIM_TRACE_BODY_KEYS and truthy(child):
                violations.append(path_label(path, f"{key}: graph must not duplicate claim_trace bodies"))
            if key_norm in TRANSITION_BODY_KEYS and truthy(child):
                violations.append(path_label(path, f"{key}: transition_trace/body is not admitted in graph map"))
            if key_norm in LABEL_KEYS:
                for text in scalar_texts(child):
                    forbidden = contains_forbidden_label_text(text)
                    if forbidden:
                        violations.append(
                            path_label(path, f"{key}: label/content smuggles forbidden term {forbidden!r}")
                        )
            if isinstance(child, str) and "transition_trace.json" in child:
                violations.append(
                    path_label(path, f"{key}: transition_trace.json is not admitted in graph map")
                )


def collect_raw_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    for item in nested_dicts(value):
        raw_refs = item.get("raw_refs")
        if isinstance(raw_refs, list):
            refs.update(ref for ref in raw_refs if isinstance(ref, str) and ref.strip())
        raw_ref = item.get("raw_ref")
        if isinstance(raw_ref, str) and raw_ref.strip():
            refs.add(raw_ref)
    return refs


def manifest_entries(raw_manifest: Any) -> list[Mapping[str, Any]]:
    if not isinstance(raw_manifest, Mapping):
        return []
    entries = raw_manifest.get("entries")
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, Mapping)]
    streams = raw_manifest.get("raw_streams")
    if isinstance(streams, list):
        return [entry for entry in streams if isinstance(entry, Mapping)]
    return []


def evidence_raw_refs(building_root: Path | None, path: Path, violations: list[str]) -> set[str]:
    if building_root is None:
        return set()
    raw_manifest_path = building_root / "raw" / "raw-manifest.json"
    if not raw_manifest_path.exists():
        return set()
    raw_manifest, load_violations = read_json(raw_manifest_path)
    violations.extend(load_violations)
    refs: set[str] = set()
    if isinstance(raw_manifest, Mapping):
        raw_refs = raw_manifest.get("raw_refs")
        if isinstance(raw_refs, list):
            refs.update(ref for ref in raw_refs if isinstance(ref, str) and ref.strip())
        elif isinstance(raw_refs, Mapping):
            refs.update(ref for ref in raw_refs if isinstance(ref, str) and ref.strip())
    for entry in manifest_entries(raw_manifest):
        raw_refs = entry.get("raw_refs")
        if isinstance(raw_refs, list):
            refs.update(ref for ref in raw_refs if isinstance(ref, str) and ref.strip())
        raw_ref = entry.get("raw_ref")
        if isinstance(raw_ref, str) and raw_ref.strip():
            refs.add(raw_ref)
    if not refs:
        violations.append(path_label(path, "raw manifest is present but exposes no raw refs"))
    return refs


def claim_facts(claim: Any) -> list[Mapping[str, Any]]:
    if not isinstance(claim, Mapping):
        return []
    facts = claim.get("facts")
    if isinstance(facts, list):
        return [fact for fact in facts if isinstance(fact, Mapping)]
    return [claim]


def fact_reference(fact: Mapping[str, Any]) -> str | None:
    for key in ("fact_ref", "fact_id", "gate_ref", "transfer_id", "carry_id", "movement_id", "id"):
        value = fact.get(key)
        if isinstance(value, str) and value.strip():
            return value
    body = fact.get("fact")
    if isinstance(body, Mapping):
        for key in ("fact_ref", "fact_id", "gate_ref", "transfer_id", "carry_id", "movement_id", "id"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def evidence_claim_refs(building_root: Path | None, path: Path, violations: list[str]) -> set[str]:
    if building_root is None:
        return set()
    refs: set[str] = set()
    for relative in CLAIM_TRACE_RELATIVE_PATHS:
        claim_path = building_root.joinpath(*relative)
        if not claim_path.exists():
            continue
        claim, load_violations = read_json(claim_path)
        violations.extend(load_violations)
        for fact in claim_facts(claim):
            ref = fact_reference(fact)
            if ref:
                refs.add(ref)
    return refs


def evidence_agent_fact_refs(building_root: Path | None, path: Path, violations: list[str]) -> set[str]:
    if building_root is None:
        return set()
    claim_path = building_root / "evidence" / "claim_trace" / "agent" / "returned_claims.json"
    if not claim_path.exists():
        return set()
    claim, load_violations = read_json(claim_path)
    violations.extend(load_violations)
    refs: set[str] = set()
    for fact in claim_facts(claim):
        ref = fact_reference(fact)
        if ref:
            refs.add(ref)
    return refs


def fact_refs_from_value(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str) and value.strip():
        refs.add(value)
    elif isinstance(value, Mapping):
        for key in ("fact_ref", "ref", "id"):
            ref = value.get(key)
            if isinstance(ref, str) and ref.strip():
                refs.add(ref)
    elif isinstance(value, list):
        for item in value:
            refs.update(fact_refs_from_value(item))
    return refs


def collect_graph_fact_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    for item in nested_dicts(value):
        for key, child in item.items():
            if normalize_name(key) in GRAPH_FACT_REF_KEYS:
                refs.update(fact_refs_from_value(child))
    return refs


def collect_agent_fact_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    for item in nested_dicts(value):
        owner = item.get("source_owner_axis")
        fact_ref = item.get("fact_ref")
        if owner == "Agent" and isinstance(fact_ref, str) and fact_ref.strip():
            refs.add(fact_ref)
        for key, child in item.items():
            key_norm = normalize_name(key)
            if key_norm in {
                "agent_fact_ref",
                "agent_fact_refs",
                "agent_returned_fact_ref",
                "agent_returned_fact_refs",
                "returned_fact_ref",
                "returned_fact_refs",
                "produced_public_fact_refs",
            }:
                refs.update(text for text in scalar_texts(child) if text.strip())
    return refs


def validate_evidence_refs(
    value: Any,
    *,
    path: Path,
    known_raw_refs: set[str],
    known_claim_refs: set[str],
    violations: list[str],
) -> None:
    graph_raw_refs = collect_raw_refs(value)
    if known_raw_refs:
        for ref in sorted(graph_raw_refs):
            if ref not in known_raw_refs:
                violations.append(path_label(path, f"graph raw_ref does not resolve through raw manifest: {ref}"))

    graph_fact_refs = collect_graph_fact_refs(value)
    if known_claim_refs:
        for ref in sorted(graph_fact_refs):
            if ref not in known_claim_refs:
                violations.append(path_label(path, f"graph public fact ref does not resolve through claim_trace: {ref}"))


def validate_role(
    item: Mapping[str, Any],
    key: str,
    allowed: set[str],
    label: str,
    path: Path,
    violations: list[str],
) -> None:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        violations.append(path_label(path, f"{label} requires {key}"))
        return
    if value not in allowed:
        violations.append(path_label(path, f"{label}.{key} has unadmitted value: {value!r}"))
        return
    if label == "link edge" and key == "edge_role" and value in {"reroute", "replay_segment"}:
        return
    forbidden = contains_forbidden_label_text(value)
    if forbidden:
        violations.append(path_label(path, f"{label}.{key} smuggles forbidden term {forbidden!r}"))


def validate_transition_ref(
    edge: Mapping[str, Any],
    *,
    path: Path,
    brick_ids: set[str],
    agent_binding_ids: set[str],
    agent_performer_refs: set[str],
    agent_fact_refs: set[str],
    raw_refs: set[str],
    violations: list[str],
) -> None:
    if "transition_fact_ref" not in edge or edge.get("transition_fact_ref") in (None, ""):
        return
    transition_ref = edge.get("transition_fact_ref")
    if not isinstance(transition_ref, str):
        violations.append(path_label(path, "transition_fact_ref must be a citation ref, not a graph-owned body"))
        return
    lowered = transition_ref.lower()
    if "transition_trace" in lowered:
        violations.append(path_label(path, "transition_fact_ref must not admit transition_trace"))
    if "agent:" in lowered:
        violations.append(path_label(path, "transition_fact_ref must not smuggle an Agent endpoint"))
    if "raw:" in lowered or "raw/" in lowered or "/raw/" in lowered:
        violations.append(path_label(path, "transition_fact_ref must not smuggle a raw endpoint"))
    endpoint_like_problem = endpoint_problem(
        transition_ref,
        brick_ids=brick_ids | {transition_ref},
        agent_binding_ids=agent_binding_ids,
        agent_performer_refs=agent_performer_refs,
        agent_fact_refs=agent_fact_refs,
        raw_refs=raw_refs,
    )
    if endpoint_like_problem and (
        transition_ref.lower().startswith("agent:")
        or transition_ref in agent_binding_ids
        or transition_ref in agent_performer_refs
        or transition_ref in agent_fact_refs
        or is_raw_ref(transition_ref, raw_refs)
    ):
        violations.append(path_label(path, f"transition_fact_ref {endpoint_like_problem}"))


def validate_link_endpoint_fields(
    edge: Mapping[str, Any],
    *,
    path: Path,
    brick_ids: set[str],
    agent_binding_ids: set[str],
    agent_performer_refs: set[str],
    agent_fact_refs: set[str],
    raw_refs: set[str],
    violations: list[str],
) -> None:
    edge_id = edge.get("link_edge_id", "<unknown>")
    for key in ("source_brick_instance_ref", "target_brick_instance_ref"):
        problem = endpoint_problem(
            edge.get(key),
            brick_ids=brick_ids,
            agent_binding_ids=agent_binding_ids,
            agent_performer_refs=agent_performer_refs,
            agent_fact_refs=agent_fact_refs,
            raw_refs=raw_refs,
        )
        if problem:
            violations.append(path_label(path, f"link edge {edge_id}.{key}: {problem}"))
    for key in sorted(ENDPOINT_KEYS):
        if key in {"source_brick_instance_ref", "target_brick_instance_ref"} or key not in edge:
            continue
        problem = endpoint_problem(
            edge.get(key),
            brick_ids=brick_ids,
            agent_binding_ids=agent_binding_ids,
            agent_performer_refs=agent_performer_refs,
            agent_fact_refs=agent_fact_refs,
            raw_refs=raw_refs,
        )
        if problem:
            violations.append(path_label(path, f"link edge {edge_id}.{key}: {problem}"))


def validate_group_topology(
    group: Mapping[str, Any],
    *,
    path: Path,
    link_edges_by_id: Mapping[str, Mapping[str, Any]],
    violations: list[str],
) -> None:
    group_id = group.get("group_id", "<unknown>")
    role = group.get("group_role")
    if role not in {"fan_out", "fan_in"}:
        return
    if group.get("member_ref_kind") != "link_edge":
        violations.append(path_label(path, f"group {group_id}: {role} requires link_edge member_ref_kind"))
        return
    member_refs = group.get("member_refs")
    if not isinstance(member_refs, list) or len(member_refs) < 2:
        violations.append(path_label(path, f"group {group_id}: {role} requires at least two link edge refs"))
        return
    edges = [link_edges_by_id.get(ref) for ref in member_refs if isinstance(ref, str)]
    if len(edges) != len(member_refs) or any(edge is None for edge in edges):
        return
    sources = {edge.get("source_brick_instance_ref") for edge in edges if isinstance(edge, Mapping)}
    targets = {edge.get("target_brick_instance_ref") for edge in edges if isinstance(edge, Mapping)}
    if role == "fan_out" and not (len(sources) == 1 and len(targets) >= 2):
        violations.append(path_label(path, f"group {group_id}: fan_out requires multiple outgoing edges"))
    if role == "fan_in" and not (len(targets) == 1 and len(sources) >= 2):
        violations.append(path_label(path, f"group {group_id}: fan_in requires multiple incoming edges"))


def validate_graph_map(
    value: Any,
    path: Path,
    *,
    fixture_mode: bool,
    building_root: Path | None = None,
) -> list[str]:
    violations: list[str] = []
    if not isinstance(value, Mapping):
        return [path_label(path, "building-map payload must be a JSON object")]

    kind = value.get("kind")
    if kind != GRAPH_KIND:
        if kind is None:
            return [path_label(path, "graph fixture/map requires kind == 'building_graph_map'")]
        return [path_label(path, f"kind must be {GRAPH_KIND!r}")]

    profile = value.get("profile")
    if profile not in ADMITTED_PROFILES:
        violations.append(path_label(path, f"profile must be one of {sorted(ADMITTED_PROFILES)}"))

    brick_instances = require_list(value, "brick_instances", path, violations)
    agent_bindings = require_list(value, "agent_bindings", path, violations)
    link_edges = require_list(value, "link_edges", path, violations)
    groups_value = value.get("groups", [])
    if not isinstance(groups_value, list):
        violations.append(path_label(path, "groups must be absent or a JSON array"))
        groups: list[Any] = []
    else:
        groups = groups_value

    validate_forbidden_content(value, path, violations)
    known_raw_refs = evidence_raw_refs(building_root, path, violations)
    known_claim_refs = evidence_claim_refs(building_root, path, violations)
    agent_fact_refs = collect_agent_fact_refs(value) | evidence_agent_fact_refs(
        building_root,
        path,
        violations,
    )
    validate_evidence_refs(
        value,
        path=path,
        known_raw_refs=known_raw_refs,
        known_claim_refs=known_claim_refs,
        violations=violations,
    )
    raw_refs = collect_raw_refs(value) | known_raw_refs

    brick_items = [
        item for index, item in enumerate(brick_instances) if require_mapping(item, f"brick_instances[{index}]", path, violations)
    ]
    binding_items = [
        item for index, item in enumerate(agent_bindings) if require_mapping(item, f"agent_bindings[{index}]", path, violations)
    ]
    edge_items = [
        item for index, item in enumerate(link_edges) if require_mapping(item, f"link_edges[{index}]", path, violations)
    ]
    group_items = [
        item for index, item in enumerate(groups) if require_mapping(item, f"groups[{index}]", path, violations)
    ]

    brick_ids = [
        value
        for item in brick_items
        if (value := text_id(item, "brick_instance_id", "brick instance", path, violations))
    ]
    binding_ids = [
        value
        for item in binding_items
        if (value := text_id(item, "agent_binding_id", "agent binding", path, violations))
    ]
    edge_ids = [
        value
        for item in edge_items
        if (value := text_id(item, "link_edge_id", "link edge", path, violations))
    ]
    group_ids = [
        value
        for item in group_items
        if (value := text_id(item, "group_id", "group", path, violations))
    ]

    violations.extend(duplicate_violations(brick_ids, "brick_instance_id", path))
    violations.extend(duplicate_violations(binding_ids, "agent_binding_id", path))
    violations.extend(duplicate_violations(edge_ids, "link_edge_id", path))
    violations.extend(duplicate_violations(group_ids, "group_id", path))

    brick_id_set = set(brick_ids)
    binding_id_set = set(binding_ids)
    edge_id_set = set(edge_ids)
    group_id_set = set(group_ids)
    for value in sorted(binding_id_set & edge_id_set):
        violations.append(
            path_label(
                path,
                f"agent_binding_id must not be reused as link_edge_id: {value}",
            )
        )
    agent_performer_refs = {
        item["agent_performer_ref"]
        for item in binding_items
        if isinstance(item.get("agent_performer_ref"), str) and item["agent_performer_ref"].strip()
    }
    link_edges_by_id = {
        item["link_edge_id"]: item
        for item in edge_items
        if isinstance(item.get("link_edge_id"), str)
    }

    for item in binding_items:
        validate_role(item, "binding_role", BINDING_ROLES, "agent binding", path, violations)
        ref = item.get("brick_instance_ref")
        if not isinstance(ref, str) or ref not in brick_id_set:
            violations.append(path_label(path, f"agent binding brick_instance_ref does not resolve: {ref!r}"))

    bindings_by_brick: dict[str, set[str]] = {}
    for item in binding_items:
        binding_id = item.get("agent_binding_id")
        brick_ref = item.get("brick_instance_ref")
        if isinstance(binding_id, str) and isinstance(brick_ref, str):
            bindings_by_brick.setdefault(brick_ref, set()).add(binding_id)

    for item in brick_items:
        brick_id = item.get("brick_instance_id")
        refs = item.get("agent_binding_refs", [])
        if refs in (None, ""):
            refs = []
        if not isinstance(refs, list):
            violations.append(path_label(path, f"brick {brick_id}: agent_binding_refs must be a JSON array"))
        else:
            for ref in refs:
                if ref not in binding_id_set:
                    violations.append(path_label(path, f"brick {brick_id}: agent_binding_ref does not resolve: {ref!r}"))
            expected_refs = bindings_by_brick.get(brick_id, set())
            if expected_refs:
                ref_set = {ref for ref in refs if isinstance(ref, str)}
                missing_refs = sorted(expected_refs - ref_set)
                if missing_refs:
                    violations.append(
                        path_label(
                            path,
                            f"brick {brick_id}: agent_binding_refs missing referenced agent bindings: {missing_refs}",
                        )
                    )
        supersedes = item.get("supersedes_instance_ref")
        if isinstance(supersedes, str) and supersedes:
            if supersedes == brick_id:
                violations.append(path_label(path, f"brick {brick_id}: supersedes_instance_ref must not self-reference"))
            elif supersedes not in brick_id_set:
                violations.append(path_label(path, f"brick {brick_id}: supersedes_instance_ref does not resolve: {supersedes!r}"))
        if any(normalize_name(key) in {"mutates_instance_ref", "mutated_instance_ref", "updates_prior_instance"} for key in item):
            violations.append(path_label(path, f"brick {brick_id}: rerun/revision must create a new instance, not mutate an old one"))

    for item in edge_items:
        validate_role(item, "edge_role", EDGE_ROLES, "link edge", path, violations)
        validate_link_endpoint_fields(
            item,
            path=path,
            brick_ids=brick_id_set,
            agent_binding_ids=binding_id_set,
            agent_performer_refs=agent_performer_refs,
            agent_fact_refs=agent_fact_refs,
            raw_refs=raw_refs,
            violations=violations,
        )
        validate_transition_ref(
            item,
            path=path,
            brick_ids=brick_id_set,
            agent_binding_ids=binding_id_set,
            agent_performer_refs=agent_performer_refs,
            agent_fact_refs=agent_fact_refs,
            raw_refs=raw_refs,
            violations=violations,
        )

    for item in group_items:
        validate_role(item, "group_role", GROUP_ROLES, "group", path, violations)
        member_kind = item.get("member_ref_kind")
        if member_kind not in GROUP_MEMBER_KINDS:
            violations.append(path_label(path, f"group {item.get('group_id', '<unknown>')}: member_ref_kind must be brick_instance or link_edge"))
            continue
        member_refs = item.get("member_refs")
        if not isinstance(member_refs, list):
            violations.append(path_label(path, f"group {item.get('group_id', '<unknown>')}: member_refs must be a JSON array"))
            continue
        namespace = brick_id_set if member_kind == "brick_instance" else edge_id_set
        for ref in member_refs:
            if ref not in namespace:
                violations.append(path_label(path, f"group {item.get('group_id', '<unknown>')}: member_ref does not resolve: {ref!r}"))
        validate_group_topology(item, path=path, link_edges_by_id=link_edges_by_id, violations=violations)

    for item in edge_items:
        for key in ("source_brick_instance_ref", "target_brick_instance_ref"):
            value = item.get(key)
            if value in group_id_set:
                violations.append(path_label(path, f"link edge endpoint must not resolve to group_id: {value}"))

    return violations


def check_one(path: Path, *, fixture_mode: bool) -> tuple[Path, list[str], bool]:
    map_path = path if fixture_mode else resolve_map_path(path)
    value, load_violations = read_json(map_path)
    if load_violations:
        return map_path, load_violations, False
    building_root = None if fixture_mode else building_root_for_map_path(map_path)
    if (
        not fixture_mode
        and building_root is not None
        and building_root.name in CRASHED_RESUME_FOSSIL_BUILDING_IDS
    ):
        # Dated fossil (Smith 0612): preserved verbatim, counted as historical.
        return map_path, [], True
    violations = validate_graph_map(
        value,
        map_path,
        fixture_mode=fixture_mode,
        building_root=building_root,
    )
    return map_path, violations, False


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check Building Graph Model work/building-map.json support maps."
    )
    parser.add_argument("--target", help="Building root or building-map JSON file to inspect.")
    parser.add_argument("--fixture", help="Fixture JSON file or fixture directory to inspect.")
    parser.add_argument("--repo", help="Repository root; inspect every project building map.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    selected_modes = [bool(args.target), bool(args.fixture), bool(args.repo)]
    if sum(selected_modes) != 1:
        print("building map graph rejected: provide exactly one of --target, --fixture, or --repo", file=sys.stderr)
        return 2

    if args.repo:
        repo = Path(args.repo)
        # PROJECT-0 S1-C: scan EVERY project vessel (project/<id>/buildings/*),
        # not only project #1 — a new project must never be silently unscanned.
        paths = sorted((repo / "project").glob("*/buildings/*/work/building-map.json"))
        if not paths:
            print("building map graph rejected: no project building maps found", file=sys.stderr)
            print(PROOF_LIMIT, file=sys.stderr)
            return 1
        fixture_mode = False
    else:
        selected = Path(args.fixture) if args.fixture else Path(args.target)
        paths = fixture_paths(selected) if args.fixture else [selected]
        fixture_mode = bool(args.fixture)
    all_violations: list[str] = []
    inspected = 0
    historical = 0

    for path in paths:
        inspected += 1
        _, violations, historical_map = check_one(path, fixture_mode=fixture_mode)
        if historical_map:
            historical += 1
        all_violations.extend(violations)

    if all_violations:
        print("building map graph rejected:", file=sys.stderr)
        for violation in all_violations:
            print(f"- {violation}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    print(
        "building map graph passed: "
        f"{inspected} map(s) inspected, {historical} historical support map(s) preserved."
    )
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

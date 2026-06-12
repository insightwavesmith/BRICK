"""Evidence presence/analysis read projection (P3d concern module).

Inspects which required evidence files are present under a Building root and
reports mechanical layer counts/gap flags. Static read only: not content
correctness, not source truth, not success/quality judgment, not Movement
authority. Reaches no axis."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.building_operation_common import (
    DEFAULT_BUILDINGS_ROOT,
    REPO_ROOT,
    _clean_text,
    _list_count,
    _rel,
    _repo_path,
)


REQUIRED_EVIDENCE_FILES: tuple[str, ...] = (
    "capture/events.jsonl",
    "raw/raw-manifest.json",
    "raw/brick-work.jsonl",
    "raw/agent-return.jsonl",
    "raw/link.jsonl",
    "evidence/evidence-manifest.json",
    "evidence/claim_trace/brick/work_contract.json",
    "evidence/claim_trace/agent/returned_claims.json",
    "evidence/claim_trace/link/transfer_trace.json",
    "evidence/claim_trace/link/carry_trace.json",
    "evidence/claim_trace/link/sufficiency_trace.json",
    "evidence/claim_trace/link/movement_trace.json",
    "work/building-work.json",
    "work/building-map.json",
)


DECLARATION_EVIDENCE_FILES: tuple[str, ...] = (
    "work/task.md",
    "work/building-intake.json",
    "work/preset-expansion.json",
    "work/declared-building-plan.json",
    "work/link-launch-policy.json",
)


DECLARATION_EVIDENCE_MARKER_FILES: tuple[str, ...] = (
    "work/building-intake.json",
    "work/preset-expansion.json",
    "work/declared-building-plan.json",
    "work/link-launch-policy.json",
)


FRONTIER_EVIDENCE_FILES: tuple[str, ...] = (
    "capture/events.jsonl",
    "raw/raw-manifest.json",
    "raw/agent-received.jsonl",
    "raw/adapter-error.jsonl",
    "evidence/evidence-manifest.json",
    "evidence/claim_trace/brick/work_contract.json",
    "evidence/claim_trace/agent/receipt_trace.json",
    "evidence/claim_trace/link/frontier_trace.json",
    "work/building-work.json",
    "work/building-map.json",
)

PARKED_EVIDENCE_FILES: tuple[str, ...] = (
    "capture/events.jsonl",
    "raw/raw-manifest.json",
    "raw/agent-received.jsonl",
    "raw/chat-session-park.jsonl",
    "evidence/evidence-manifest.json",
    "evidence/claim_trace/brick/work_contract.json",
    "evidence/claim_trace/agent/receipt_trace.json",
    "evidence/claim_trace/link/frontier_trace.json",
    "work/building-work.json",
    "work/building-map.json",
)


@dataclass(frozen=True)
class EvidenceStatus:
    """Support-only evidence root status."""

    building_root: str
    present_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BuildingEvidenceAnalysis:
    """Mechanical evidence-layer analysis for one Building root."""

    building_root: str
    present_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    capture_event_count: int
    raw_stream_counts: Mapping[str, int]
    claim_trace_fact_counts: Mapping[str, int]
    graph_counts: Mapping[str, int]
    mechanical_gap_flags: tuple[str, ...]
    proof_limits: tuple[str, ...] = field(default_factory=tuple)
    not_proven: tuple[str, ...] = field(default_factory=tuple)

    def to_packet(self) -> Mapping[str, Any]:
        """Return JSON-compatible support projection."""

        return {
            "building_root": self.building_root,
            "present_files": list(self.present_files),
            "missing_files": list(self.missing_files),
            "capture_event_count": self.capture_event_count,
            "raw_stream_counts": dict(self.raw_stream_counts),
            "claim_trace_fact_counts": dict(self.claim_trace_fact_counts),
            "graph_counts": dict(self.graph_counts),
            "mechanical_gap_flags": list(self.mechanical_gap_flags),
            "proof_limits": list(self.proof_limits),
            "not_proven": list(self.not_proven),
        }


def evidence_status(
    building_root: str | Path,
    *,
    repo_root: Path | str = REPO_ROOT,
) -> EvidenceStatus:
    """Inspect required evidence files under one Building root."""

    repo = Path(repo_root).resolve()
    root = _repo_path(repo, building_root)
    required_files = _evidence_required_files_for_root(root)
    present: list[str] = []
    missing: list[str] = []
    for rel_path in required_files:
        target = root / rel_path
        if target.is_file():
            present.append(rel_path)
        else:
            missing.append(rel_path)
    if _parked_marker_present(root):
        parked_files = sorted(
            path.relative_to(root).as_posix()
            for path in (root / "work" / "step-outputs").glob("*/parked.json")
            if path.is_file()
        )
        envelope_files = sorted(
            path.relative_to(root).as_posix()
            for path in (root / "work" / "step-outputs").glob("*/work-envelope.json")
            if path.is_file()
        )
        if parked_files:
            present.extend(parked_files)
        else:
            missing.append("work/step-outputs/<step-ref>-attempt-N/parked.json")
        if envelope_files:
            present.extend(envelope_files)
        else:
            missing.append("work/step-outputs/<step-ref>-attempt-N/work-envelope.json")
    elif _frontier_marker_present(root):
        adapter_error_files = sorted(
            path.relative_to(root).as_posix()
            for path in (root / "work" / "step-outputs").glob("*/adapter-error.json")
            if path.is_file()
        )
        if adapter_error_files:
            present.extend(adapter_error_files)
        else:
            missing.append("work/step-outputs/<step-ref>-attempt-N/adapter-error.json")
    return EvidenceStatus(
        building_root=_rel(repo, root),
        present_files=tuple(present),
        missing_files=tuple(missing),
        proof_limits=(
            "file presence support evidence only",
            "not content correctness",
            "not source truth",
        ),
        not_proven=(
            "semantic correctness of evidence",
            "graph semantic completeness",
            "Movement authority",
        ),
    )


def _evidence_required_files_for_root(root: Path) -> tuple[str, ...]:
    if _complete_marker_present(root):
        if _declaration_evidence_marker_present(root):
            return REQUIRED_EVIDENCE_FILES + DECLARATION_EVIDENCE_FILES
        return REQUIRED_EVIDENCE_FILES
    if _parked_marker_present(root):
        return PARKED_EVIDENCE_FILES
    if _frontier_marker_present(root):
        return FRONTIER_EVIDENCE_FILES
    return REQUIRED_EVIDENCE_FILES


def _declaration_evidence_marker_present(root: Path) -> bool:
    manifest = root / "evidence" / "evidence-manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        refs = data.get("declaration_evidence_refs")
        if isinstance(refs, Sequence) and not isinstance(refs, (str, bytes)):
            for ref in refs:
                if isinstance(ref, str) and ref in DECLARATION_EVIDENCE_FILES:
                    return True
    return any((root / rel_path).is_file() for rel_path in DECLARATION_EVIDENCE_MARKER_FILES)


def _complete_marker_present(root: Path) -> bool:
    return (
        (root / "raw" / "agent-return.jsonl").is_file()
        or (root / "raw" / "agent-returns.jsonl").is_file()
        or (root / "evidence" / "claim_trace" / "agent" / "returned_claims.json").is_file()
    )


def _frontier_marker_present(root: Path) -> bool:
    return (
        (root / "raw" / "adapter-error.jsonl").is_file()
        or (root / "evidence" / "claim_trace" / "agent" / "receipt_trace.json").is_file()
        or any(
            path.is_file()
            for path in (root / "work" / "step-outputs").glob("*/adapter-error.json")
        )
    )


def _parked_marker_present(root: Path) -> bool:
    return (
        (root / "raw" / "chat-session-park.jsonl").is_file()
        or any(
            path.is_file()
            for path in (root / "work" / "step-outputs").glob("*/parked.json")
        )
    )


def analyze_building_evidence(
    building_root: str | Path,
    *,
    repo_root: Path | str = REPO_ROOT,
) -> BuildingEvidenceAnalysis:
    """Analyze evidence layer presence and counts without judging meaning."""

    repo = Path(repo_root).resolve()
    root = _repo_path(repo, building_root)
    status = evidence_status(root, repo_root=repo)
    capture_count = _line_count(root / "capture" / "events.jsonl")
    raw_counts = {
        "brick_work": _line_count(root / "raw" / "brick-work.jsonl"),
        "agent_return": _line_count(root / "raw" / "agent-return.jsonl"),
        "link": _line_count(root / "raw" / "link.jsonl"),
    }
    if (root / "raw" / "agent-received.jsonl").is_file():
        raw_counts["agent_received"] = _line_count(root / "raw" / "agent-received.jsonl")
    if (root / "raw" / "chat-session-park.jsonl").is_file():
        raw_counts["chat_session_park"] = _line_count(root / "raw" / "chat-session-park.jsonl")
    claim_counts = {
        "brick_work_contract": _fact_count(root / "evidence" / "claim_trace" / "brick" / "work_contract.json"),
        "agent_returned_claims": _fact_count(root / "evidence" / "claim_trace" / "agent" / "returned_claims.json"),
        "link_transfer_trace": _fact_count(root / "evidence" / "claim_trace" / "link" / "transfer_trace.json"),
        "link_carry_trace": _fact_count(root / "evidence" / "claim_trace" / "link" / "carry_trace.json"),
        "link_sufficiency_trace": _fact_count(root / "evidence" / "claim_trace" / "link" / "sufficiency_trace.json"),
        "link_movement_trace": _fact_count(root / "evidence" / "claim_trace" / "link" / "movement_trace.json"),
    }
    if (root / "evidence" / "claim_trace" / "agent" / "receipt_trace.json").is_file():
        claim_counts["agent_receipt_trace"] = _fact_count(
            root / "evidence" / "claim_trace" / "agent" / "receipt_trace.json"
        )
    if (root / "evidence" / "claim_trace" / "link" / "frontier_trace.json").is_file():
        claim_counts["link_frontier_trace"] = _fact_count(
            root / "evidence" / "claim_trace" / "link" / "frontier_trace.json"
        )
    graph_counts = _graph_counts(root / "work" / "building-map.json")
    return BuildingEvidenceAnalysis(
        building_root=status.building_root,
        present_files=status.present_files,
        missing_files=status.missing_files,
        capture_event_count=capture_count,
        raw_stream_counts=raw_counts,
        claim_trace_fact_counts=claim_counts,
        graph_counts=graph_counts,
        mechanical_gap_flags=tuple(_mechanical_gap_flags(status.missing_files, capture_count, raw_counts, claim_counts, graph_counts)),
        proof_limits=(
            "mechanical evidence analysis support projection only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ),
        not_proven=(
            "semantic correctness of evidence",
            "root cause of any mechanical gap",
            "graph semantic completeness",
            "provider or Agent quality",
        ),
    )


def evidence_analysis_packet(
    building_roots: Sequence[str | Path],
    *,
    repo_root: Path | str = REPO_ROOT,
    packet_ref: str = "evidence-analysis:evidence-auto-0",
) -> Mapping[str, Any]:
    """Build a support-only packet from one or more Building evidence roots."""

    if not building_roots:
        raise ValueError("evidence analysis requires at least one Building root")
    analyses = [
        analyze_building_evidence(root, repo_root=repo_root).to_packet()
        for root in building_roots
    ]
    return {
        "kind": "building_evidence_analysis_packet",
        "schema_version": "evidence-auto-0",
        "packet_ref": _clean_text("packet_ref", packet_ref),
        "analyses": analyses,
        "proof_limits": [
            "support projection only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic correctness",
            "repair correctness",
            "future evidence completeness",
            "graph semantic completeness",
        ],
    }


def building_index_packet(
    *,
    repo_root: Path | str = REPO_ROOT,
    buildings_root: Path | str = DEFAULT_BUILDINGS_ROOT,
    packet_ref: str = "building-index:building-index-1",
) -> Mapping[str, Any]:
    """Build a project-local Building root index projection."""

    repo = Path(repo_root).resolve()
    root = _repo_path(repo, buildings_root)
    if not root.is_dir():
        raise ValueError("buildings_root must be an existing directory")
    entries: list[Mapping[str, Any]] = []
    for building_root in sorted(path for path in root.iterdir() if path.is_dir()):
        analysis = analyze_building_evidence(building_root, repo_root=repo)
        entries.append(
            {
                "building_id": building_root.name,
                "building_root": analysis.building_root,
                "missing_required_file_count": len(analysis.missing_files),
                "capture_event_count": analysis.capture_event_count,
                "agent_fact_count": analysis.claim_trace_fact_counts.get(
                    "agent_returned_claims",
                    0,
                ),
                "link_edge_count": analysis.graph_counts.get("link_edges", 0),
                "mechanical_gap_flags": list(analysis.mechanical_gap_flags),
            }
        )
    return {
        "kind": "building_index_projection",
        "schema_version": "building-index-1",
        "packet_ref": _clean_text("packet_ref", packet_ref),
        "buildings_root": _rel(repo, root),
        "root_count": len(entries),
        "roots": entries,
        "proof_limits": [
            "support projection only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "complete historical inventory outside buildings_root",
            "semantic correctness of listed roots",
            "repair correctness",
            "graph semantic completeness",
        ],
    }


def _line_count(path: Path) -> int:
    if not path.is_file():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def _fact_count(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    facts = payload.get("facts") if isinstance(payload, Mapping) else None
    return len(facts) if isinstance(facts, list) else 0


def _graph_counts(path: Path) -> Mapping[str, int]:
    if not path.is_file():
        return {
            "brick_instances": 0,
            "agent_bindings": 0,
            "link_edges": 0,
            "groups": 0,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "brick_instances": 0,
            "agent_bindings": 0,
            "link_edges": 0,
            "groups": 0,
        }
    if not isinstance(payload, Mapping):
        return {
            "brick_instances": 0,
            "agent_bindings": 0,
            "link_edges": 0,
            "groups": 0,
        }
    return {
        "brick_instances": _list_count(payload.get("brick_instances")),
        "agent_bindings": _list_count(payload.get("agent_bindings")),
        "link_edges": _list_count(payload.get("link_edges")),
        "groups": _list_count(payload.get("groups")),
    }


def _mechanical_gap_flags(
    missing_files: Sequence[str],
    capture_count: int,
    raw_counts: Mapping[str, int],
    claim_counts: Mapping[str, int],
    graph_counts: Mapping[str, int],
) -> tuple[str, ...]:
    flags: list[str] = []
    if missing_files:
        flags.append("missing_required_evidence_file")
    if capture_count <= 0:
        flags.append("no_capture_events")
    for name, count in raw_counts.items():
        if count <= 0:
            flags.append(f"empty_raw_stream:{name}")
    for name, count in claim_counts.items():
        if count <= 0:
            flags.append(f"empty_claim_trace:{name}")
    for name in ("brick_instances", "agent_bindings", "link_edges"):
        if graph_counts.get(name, 0) <= 0:
            flags.append(f"empty_graph_projection:{name}")
    return tuple(flags)

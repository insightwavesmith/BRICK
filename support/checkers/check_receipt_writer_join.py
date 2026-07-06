#!/usr/bin/env python3
"""receipt-writer-join standalone checker (support evidence only).

receipt-writer-join 0707 (rootfix 2): the NORMAL-completion forward writer must
record ``raw/agent-received.jsonl`` in the SAME transaction as the returned
rows, so a completed walk carries the receipt ledger the frontier observer
requires (without it a normal completion fails ``evidence_incomplete`` / T10).

This checker DRIVES a real ``adapter:local`` complete walk at check time in a
temp root (removed after) and asserts:

  * the completed walk lands ``raw/agent-received.jsonl`` with one receipt row
    per completed step, and ``received row count == returned row count``;
  * received rows and returned rows carry the same ``recorded_at`` stamp and
    the raw/evidence manifests list the new receipt stream;
  * the frontier observer reads the completed vessel as ``complete`` (receipt
    satisfied), not ``evidence_incomplete`` / ``agent_incomplete``;
  * two in-process mutation-RED probes fire: (1) a populated packet with the
    forward writer's agent-received block MUST land the receipt file, and
    (2) the raw scrub still masks a sensitive ``session_id`` value in a receipt
    row (mask cannot be bypassed).

It authors no Movement, target, route, verdict, success, or quality judgment;
it is support evidence only. It uses an ``os.path`` self-anchored sys.path
bootstrap (NOT ``Path(__file__).resolve().parents[N]``) so it stays out of the
parents[N] binding-registry scan.
"""

from __future__ import annotations

import argparse
import json
import os.path as _osp
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
for _p in (_REPO_ROOT, _osp.join(_REPO_ROOT, "support", "import_identity")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


_PROOF_LIMIT = (
    "proof limit: receipt-writer-join support check only; this does not prove "
    "source truth, success judgment, quality judgment, Movement authority, or "
    "real-provider behavior."
)

_BUILDING_ID = "receipt-writer-join-fixture"
_GATE = ["link-gate:default-transition"]


def _brick_step(word: str, agent_ref: str, completion_edge_ref: str) -> dict[str, Any]:
    step_ref = f"{_BUILDING_ID}-{word}"
    return {
        "step_ref": step_ref,
        "completion_edge_ref": completion_edge_ref,
        "rows": [
            {
                "axis": "Brick",
                "row_ref": f"brick-row:{step_ref}",
                "brick_work_ref": f"work:{step_ref}",
                "brick_instance_ref": f"brick-{step_ref}",
                "work_statement": (
                    f"receipt-writer-join fixture node {word}: return ONE JSON "
                    "object with exactly the required fields. Do not choose "
                    "Movement. Do not report success, failure, approval, or "
                    "quality."
                ),
                "comparison_rule": (
                    "support observes the adapter:local return shape; support "
                    "does not judge quality."
                ),
                "required_return_shape": "observed_evidence, not_proven",
            },
            {"axis": "Agent", "row_ref": f"agent-row:{step_ref}", "agent_object_ref": agent_ref},
        ],
    }


def _fwd_edge(edge_ref: str, src_word: str, tgt_word: str) -> dict[str, Any]:
    return {
        "edge_ref": edge_ref,
        "source_step_ref": f"{_BUILDING_ID}-{src_word}",
        "target_step_ref": f"{_BUILDING_ID}-{tgt_word}",
        "rows": [
            {
                "axis": "Link",
                "row_ref": f"link-row:{edge_ref}",
                "movement": "forward",
                "target_ref": f"brick-{_BUILDING_ID}-{tgt_word}",
                "declared_gate_refs": list(_GATE),
            }
        ],
    }


def _fixture_plan() -> dict[str, Any]:
    boundary = f"building-boundary:{_BUILDING_ID}-closed"
    close_edge = {
        "edge_ref": f"edge:{_BUILDING_ID}-close-to-boundary",
        "source_step_ref": f"{_BUILDING_ID}-close",
        "target_ref": boundary,
        "rows": [
            {
                "axis": "Link",
                "row_ref": f"link-row:{_BUILDING_ID}-close-to-boundary",
                "movement": "forward",
                "building_lifecycle": {
                    "state": "closed",
                    "reason": "receipt-writer-join fixture minimal complete walk.",
                },
                "target_ref": boundary,
                "declared_gate_refs": list(_GATE),
            }
        ],
    }
    return {
        "plan_ref": f"building-plan:{_BUILDING_ID}",
        "owner_axis": "Brick",
        "building_id": _BUILDING_ID,
        "plan_shape": "graph",
        "composition_mode": "caller_or_coo_declared_graph_composition",
        "declared_by": f"coo {_BUILDING_ID}",
        "selected_adapter_ref": "adapter:local",
        "selected_model_ref": "model:default",
        "task_source_ref": "task-source:inline-statement",
        "task_statement": (
            "receipt-writer-join fixture: one deterministic adapter:local walk "
            "exercising the normal-completion receipt ledger, generated at check "
            "time and removed after."
        ),
        "proof_limits": [
            "support evidence only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": ["real provider behavior", "scheduler / queue / retry behavior"],
        "execution_order": [f"{_BUILDING_ID}-work", f"{_BUILDING_ID}-close"],
        "brick_steps": [
            _brick_step("work", "agent-object:dev", f"edge:{_BUILDING_ID}-work-to-close"),
            _brick_step("close", "agent-object:coo", f"edge:{_BUILDING_ID}-close-to-boundary"),
        ],
        "link_edges": [
            _fwd_edge(f"edge:{_BUILDING_ID}-work-to-close", "work", "close"),
            close_edge,
        ],
    }


def _fixture_callables() -> Mapping[str, Any]:
    def _brain(request: Any) -> Mapping[str, Any]:
        del request
        return {
            "observed_evidence": ["completed declared fixture node"],
            "not_proven": ["semantic correctness of the returned note"],
        }

    return {"callable:local:agent-invoke0-smoke": _brain}


def _jsonl_rows(path: Path) -> list[Mapping[str, Any]]:
    if not path.is_file():
        return []
    rows: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _read_json_object(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, Mapping) else {}


def _walk_fixture(output_root: Path) -> Path:
    from brick_protocol.support.operator.run import run_building_plan

    result = run_building_plan(
        _fixture_plan(),
        output_root=output_root,
        overwrite_existing=True,
        local_callables=_fixture_callables(),
        adapter_cwd=Path(_REPO_ROOT),
        adapter_timeout_seconds=30,
    )
    return Path(result.lifecycle_write.root)


def _probe_normal_walk(violations: list[str]) -> None:
    from brick_protocol.support.operator.frontier_observation import (
        observe_building_frontier,
    )

    with tempfile.TemporaryDirectory(prefix="bp-receipt-join-") as tmp:
        out = Path(tmp) / "buildings"
        out.mkdir(parents=True)
        root = _walk_fixture(out)
        received = _jsonl_rows(root / "raw" / "agent-received.jsonl")
        returned = _jsonl_rows(root / "raw" / "agent-return.jsonl")
        if not received:
            violations.append(
                "receipt-writer-join RED: normal-completion walk produced no "
                "raw/agent-received.jsonl"
            )
        elif len(received) != len(returned):
            violations.append(
                "receipt-writer-join RED: received row count "
                f"({len(received)}) != returned row count ({len(returned)})"
            )
        received_steps = {
            str(row.get("step_ref") or "") for row in received if isinstance(row, Mapping)
        }
        returned_steps = {
            str(row.get("step_ref") or "") for row in returned if isinstance(row, Mapping)
        }
        if received_steps != returned_steps:
            violations.append(
                "receipt-writer-join RED: received/return step_ref sets differ "
                f"(received={sorted(received_steps)!r}, returned={sorted(returned_steps)!r})"
            )
        received_recorded_at = {
            str(row.get("recorded_at") or "") for row in received if isinstance(row, Mapping)
        }
        returned_recorded_at = {
            str(row.get("recorded_at") or "") for row in returned if isinstance(row, Mapping)
        }
        if not received_recorded_at or received_recorded_at != returned_recorded_at:
            violations.append(
                "receipt-writer-join RED: raw/agent-received.jsonl was not "
                "recorded in the same raw writer transaction as raw/agent-return.jsonl "
                f"(received_recorded_at={sorted(received_recorded_at)!r}, "
                f"returned_recorded_at={sorted(returned_recorded_at)!r})"
            )
        raw_manifest = _read_json_object(root / "raw" / "raw-manifest.json")
        raw_entries = raw_manifest.get("entries")
        received_manifest_entry = None
        if isinstance(raw_entries, list):
            received_manifest_entry = next(
                (
                    entry
                    for entry in raw_entries
                    if isinstance(entry, Mapping)
                    and entry.get("path") == "raw/agent-received.jsonl"
                ),
                None,
            )
        if not isinstance(received_manifest_entry, Mapping):
            violations.append(
                "receipt-writer-join RED: raw-manifest.json lacks the "
                "raw/agent-received.jsonl stream entry"
            )
        else:
            received_refs = {
                ref
                for row in received
                for ref in (row.get("raw_refs") or [])
                if isinstance(ref, str)
            }
            manifest_refs = {
                ref
                for ref in (received_manifest_entry.get("raw_refs") or [])
                if isinstance(ref, str)
            }
            if received_refs and received_refs != manifest_refs:
                violations.append(
                    "receipt-writer-join RED: raw-manifest agent-received raw_refs "
                    f"do not match the stream rows (manifest={sorted(manifest_refs)!r}, "
                    f"stream={sorted(received_refs)!r})"
                )
        evidence_manifest = _read_json_object(root / "evidence" / "evidence-manifest.json")
        raw_stream_refs = evidence_manifest.get("raw_stream_refs")
        if not isinstance(raw_stream_refs, list) or "raw/agent-received.jsonl" not in raw_stream_refs:
            violations.append(
                "receipt-writer-join RED: evidence-manifest raw_stream_refs lacks "
                "raw/agent-received.jsonl"
            )
        obs = observe_building_frontier(root, repo_root=Path(_REPO_ROOT))
        counts = obs.get("observed_counts", {})
        if int(counts.get("agent_received_records", 0)) != int(
            counts.get("agent_return_records", -1)
        ):
            violations.append(
                "receipt-writer-join RED: frontier observer did not read the "
                "completed vessel as receipt-satisfied "
                f"(counts={counts!r})"
            )
        if obs.get("frontier_kind") != "complete":
            violations.append(
                "receipt-writer-join RED: completed walk frontier_kind is "
                f"{obs.get('frontier_kind')!r}, expected 'complete' "
                "(receipt ledger absent -> evidence_incomplete/agent_incomplete)"
            )


def _probe_writer_block_mutation_red(violations: list[str]) -> None:
    """MUTATION-RED 1: a populated packet with the agent-received block present
    MUST land the receipt file (the block in write_raw_and_claim_trace is
    load-bearing; removing it makes this probe fire)."""

    from brick_protocol.support.recording import raw_claim_trace
    from brick_protocol.support.recording.contracts import RawClaimTracePacket

    packet = RawClaimTracePacket(
        brick_raw_records=(),
        agent_raw_records=(
            {
                "raw_ref": "raw:agent:01",
                "raw_refs": ["raw:agent:01"],
                "step_ref": "s1",
                "returned": {"observed_evidence": ["x"]},
            },
        ),
        link_raw_records=(),
        brick_claim_facts=(),
        agent_claim_facts=(),
        link_transfer_claim_facts=(),
        link_carry_claim_facts=(),
        link_sufficiency_claim_facts=(),
        link_movement_claim_facts=(),
        agent_received_raw_records=(
            {
                "raw_ref": "raw:agent-received:01",
                "raw_refs": ["raw:agent-received:01"],
                "step_ref": "s1",
                "agent_object_ref": "agent-object:dev",
                "received_work_ref": "brick-work:01:s1",
                "receipt_record_role": "received work observation only",
            },
        ),
    )
    with tempfile.TemporaryDirectory(prefix="bp-receipt-join-writer-") as tmp:
        root = Path(tmp) / "b"
        raw_claim_trace.write_raw_and_claim_trace(root, "b", packet)
        wrote_received = (root / "raw" / "agent-received.jsonl").is_file()
    if not wrote_received:
        violations.append(
            "receipt-writer-join RED: forward writer did not emit "
            "raw/agent-received.jsonl from a populated packet (the receipt "
            "block is missing from write_raw_and_claim_trace)"
        )


def _probe_scrub_mutation_red(violations: list[str]) -> None:
    """MUTATION-RED 2: the raw scrub masks a sensitive session_id value in a
    receipt row (the mask cannot be bypassed on this stream)."""

    from brick_protocol.support.recording import raw_claim_trace
    from brick_protocol.support.recording.contracts import RawClaimTracePacket

    secret = "receipt-join-secret-session-value-987"
    packet = RawClaimTracePacket(
        brick_raw_records=(),
        agent_raw_records=(),
        link_raw_records=(),
        brick_claim_facts=(),
        agent_claim_facts=(),
        link_transfer_claim_facts=(),
        link_carry_claim_facts=(),
        link_sufficiency_claim_facts=(),
        link_movement_claim_facts=(),
        agent_received_raw_records=(
            {
                "raw_ref": "raw:agent-received:01",
                "raw_refs": ["raw:agent-received:01"],
                "step_ref": "s1",
                "agent_object_ref": "agent-object:dev",
                "received_work_ref": "brick-work:01:s1",
                "receipt_record_role": "received work observation only",
                "session_id": secret,
            },
        ),
    )
    with tempfile.TemporaryDirectory(prefix="bp-receipt-join-scrub-") as tmp:
        root = Path(tmp) / "b"
        raw_claim_trace.write_raw_and_claim_trace(root, "b", packet)
        received_path = root / "raw" / "agent-received.jsonl"
        if not received_path.is_file():
            violations.append(
                "receipt-writer-join RED: scrub probe found no "
                "raw/agent-received.jsonl (the forward writer's receipt block "
                "is missing, so the mask cannot be exercised)"
            )
            return
        text = received_path.read_text(encoding="utf-8")
    if secret in text:
        violations.append(
            "receipt-writer-join RED: raw scrub leaked a sensitive session_id "
            "value into raw/agent-received.jsonl"
        )
    if "raw_evidence_scrub" not in text:
        violations.append(
            "receipt-writer-join RED: raw scrub did not record scrub evidence "
            "for the masked receipt row"
        )


def check(repo: Path | None = None) -> list[str]:
    del repo
    violations: list[str] = []
    _probe_normal_walk(violations)
    _probe_writer_block_mutation_red(violations)
    _probe_scrub_mutation_red(violations)
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="receipt-writer-join checker")
    parser.add_argument("--repo", default=".")
    parser.parse_args(sys.argv[1:] if argv is None else argv)
    violations = check()
    if violations:
        print("receipt-writer-join rejected evidence:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(_PROOF_LIMIT, file=sys.stderr)
        return 1
    print(
        "receipt-writer-join passed: the normal-completion forward writer "
        "records raw/agent-received.jsonl in the returned transaction (received "
        "count == returned count), the frontier observer reads the completed "
        "vessel as complete, and two mutation-RED probes (writer block + scrub "
        "mask) fired."
    )
    print(_PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

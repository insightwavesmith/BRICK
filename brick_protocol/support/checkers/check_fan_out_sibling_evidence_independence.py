#!/usr/bin/env python3
"""Guard fan-out sibling-evidence INDEPENDENCE (F1, the 0609 cross-vouch invariant).

Law (AGENTS.md, Building / Portfolio Boundaries): the fan-out sibling nodes that
split from one parent each hold their OWN independent evidence. One sibling's
returned-evidence body (its AgentFact / claim_trace) must never appear as another
sibling's evidence — a copied/shared sibling body is a cross-vouch leak (sibling A
standing in for sibling B). The 0609 incident was exactly this: a fan-out
sibling's PASS evidence leaked across to vouch for a sibling that had not been
independently walked.

The structural defence already mostly stands (walker_kernel
``sibling_independence`` + per-branch ``raised_exception`` exception isolation,
0609): each fan-out sibling is walked and recorded on its own per-branch lane.
This checker is the missing GENERAL GUARD — a byte-distinctness scan over fan-out
sibling evidence bodies that catches a FUTURE copy/leak the structure does not.

It is a SCAN/READ checker (it does not re-run the walker, touch axis modules, or
rewrite anything). It proves itself via a self-contained synthetic FIRE probe:

  * GREEN fixture — a parent that fans out to siblings whose evidence bodies are
    all byte-distinct passes.
  * mutation-RED fixture — making two same-parent fan-out sibling bodies IDENTICAL
    (the cross-vouch leak) is rejected.

Scope (deliberately narrow, matching the law):
  * Only SAME-PARENT FAN-OUT SIBLINGS are compared. Sequential/chain Bricks share
    carry/spine by design and are NOT compared. Parent->child shared evidence is
    expected and NOT compared. Only same-parent fan-out sibling bodies must be
    byte-distinct.

This checker is support evidence only. It does not call providers, choose
Movement, judge source truth, judge success or quality, or classify Building
outcomes.

Pass => exit 0. Reject => exit 1.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]

PROOF_LIMIT = (
    "proof limit: fan-out sibling-evidence independence checker support evidence "
    "only; it does not prove source truth, success judgment, quality judgment, "
    "Movement authority, provider behavior, or that any sibling's evidence is "
    "CORRECT. It proves only that same-parent fan-out sibling evidence bodies are "
    "byte-distinct (no cross-vouch copy/leak), the 0609 invariant."
)


class FanOutSiblingEvidenceError(ValueError):
    """Raised when same-parent fan-out siblings share an evidence body."""


def _fan_out_sibling_groups(
    building_map: Mapping[str, object],
) -> list[tuple[str, tuple[str, ...]]]:
    """Collect (parent_ref, sibling_node_refs) for each fan-out group.

    Reads the building-map ``groups`` rows whose ``group_role`` is ``fan_out``,
    resolving each member ``link_edge`` ref to its TARGET step (the sibling node).
    Sequential/chain edges and non-fan-out groups are ignored by construction.
    """

    groups_raw = building_map.get("groups", [])
    edges_raw = building_map.get("link_edges", [])
    edge_by_id: dict[str, Mapping[str, object]] = {}
    for edge in edges_raw if isinstance(edges_raw, list) else []:
        if isinstance(edge, Mapping):
            edge_id = edge.get("link_edge_id")
            if isinstance(edge_id, str):
                edge_by_id[edge_id] = edge

    fan_outs: list[tuple[str, tuple[str, ...]]] = []
    for group in groups_raw if isinstance(groups_raw, list) else []:
        if not isinstance(group, Mapping):
            continue
        if group.get("group_role") != "fan_out":
            continue
        parent_ref = str(group.get("source_step_ref") or group.get("group_id") or "")
        sibling_refs: list[str] = []
        member_refs = group.get("member_refs", [])
        for member in member_refs if isinstance(member_refs, list) else []:
            edge = edge_by_id.get(str(member))
            if edge is None:
                continue
            target = edge.get("target_step_ref") or edge.get("to_step_ref")
            if isinstance(target, str):
                sibling_refs.append(target)
        if len(sibling_refs) >= 2:
            fan_outs.append((parent_ref, tuple(sibling_refs)))
    return fan_outs


def _sibling_evidence_body(
    node_evidence: Mapping[str, object], node_ref: str
) -> str:
    """Return the byte body a fan-out sibling node carries as its evidence.

    The body is the sibling's returned-evidence (AgentFact / claim_trace) text.
    A missing body is itself a fault (a sibling with no independent evidence
    cannot be distinguished from a leak), so it is reported as a violation by the
    caller rather than silently treated as distinct.
    """

    body = node_evidence.get(node_ref)
    if body is None:
        return ""
    return str(body)


def check_building_evidence(
    building_map: Mapping[str, object],
    node_evidence: Mapping[str, object],
) -> list[str]:
    """Return cross-vouch-leak violations for one building's fan-out evidence."""

    violations: list[str] = []
    for parent_ref, sibling_refs in _fan_out_sibling_groups(building_map):
        seen_bodies: dict[str, str] = {}
        for node_ref in sibling_refs:
            body = _sibling_evidence_body(node_evidence, node_ref)
            if body == "":
                violations.append(
                    "fan-out.sibling-independence: fan-out sibling "
                    f"{node_ref!r} (parent {parent_ref!r}) carries no independent "
                    "evidence body"
                )
                continue
            prior = seen_bodies.get(body)
            if prior is not None:
                violations.append(
                    "fan-out.sibling-independence: cross-vouch leak — fan-out "
                    f"siblings {prior!r} and {node_ref!r} (parent {parent_ref!r}) "
                    "carry a byte-identical evidence body; same-parent fan-out "
                    "siblings must each hold their own independent evidence (0609)"
                )
            else:
                seen_bodies[body] = node_ref
    return violations


def _green_fixture() -> tuple[Mapping[str, object], Mapping[str, object]]:
    """A parent that fans out to 3 siblings with byte-distinct evidence bodies."""

    building_map = {
        "kind": "building_graph_map",
        "groups": [
            {
                "group_id": "group:f1-fan-out",
                "group_role": "fan_out",
                "source_step_ref": "step:f1-work",
                "member_ref_kind": "link_edge",
                "member_refs": [
                    "edge:f1-work-to-code-attack-qa",
                    "edge:f1-work-to-axis-attack-qa",
                    "edge:f1-work-to-evidence-integrity",
                ],
            }
        ],
        "link_edges": [
            {
                "link_edge_id": "edge:f1-work-to-code-attack-qa",
                "target_step_ref": "step:f1-code-attack-qa",
            },
            {
                "link_edge_id": "edge:f1-work-to-axis-attack-qa",
                "target_step_ref": "step:f1-axis-attack-qa",
            },
            {
                "link_edge_id": "edge:f1-work-to-evidence-integrity",
                "target_step_ref": "step:f1-evidence-integrity",
            },
        ],
    }
    node_evidence = {
        "step:f1-code-attack-qa": (
            "claim_trace: code-attack-qa observed missing bounds check at L42"
        ),
        "step:f1-axis-attack-qa": (
            "claim_trace: axis-attack-qa observed Brick row crossing Link boundary"
        ),
        "step:f1-evidence-integrity": (
            "claim_trace: evidence-integrity observed manifest hash chain intact"
        ),
    }
    return building_map, node_evidence


def _assert_green_then_mutation_red() -> str:
    """FIRE probe: distinct sibling bodies pass; a copied sibling body REDs.

    This is the permanent mutation-RED guard. The GREEN fixture (3 byte-distinct
    fan-out sibling bodies) must pass; mutating it so two same-parent siblings
    share one body (the 0609 cross-vouch leak) must be rejected. If a future edit
    weakens ``check_building_evidence``, this probe stops firing and the checker
    REDs.
    """

    building_map, green_evidence = _green_fixture()
    green_violations = check_building_evidence(building_map, green_evidence)
    if green_violations:
        raise FanOutSiblingEvidenceError(
            "self-probe failed: the byte-distinct fan-out sibling GREEN fixture "
            f"was wrongly rejected: {green_violations}"
        )

    leaked_evidence = dict(green_evidence)
    # Copy the first sibling's body onto the second sibling (the cross-vouch leak).
    leaked_evidence["step:f1-axis-attack-qa"] = green_evidence[
        "step:f1-code-attack-qa"
    ]
    red_violations = check_building_evidence(building_map, leaked_evidence)
    if not any("cross-vouch leak" in line for line in red_violations):
        raise FanOutSiblingEvidenceError(
            "mutation RED failed: a fan-out fixture with two byte-identical "
            "sibling evidence bodies was NOT rejected as a cross-vouch leak"
        )
    return (
        "mutation RED observed: copying one fan-out sibling's evidence body onto "
        "a same-parent sibling (a cross-vouch leak) was rejected; the byte-"
        "distinct GREEN fixture passed"
    )


def check() -> list[str]:
    mutation_line = _assert_green_then_mutation_red()
    return [
        "fan-out sibling-evidence independence green: same-parent fan-out sibling "
        "evidence bodies are required byte-distinct (no cross-vouch copy/leak); "
        "sequential/chain carry-sharing and parent->child sharing are out of "
        "scope (0609 invariant).",
        mutation_line,
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for fan-out sibling-evidence independence "
            "(F1, the 0609 cross-vouch invariant): same-parent fan-out sibling "
            "evidence bodies must be byte-distinct."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    parse_args(argv)
    try:
        outputs = check()
    except FanOutSiblingEvidenceError as exc:
        print("fan-out sibling-evidence independence rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

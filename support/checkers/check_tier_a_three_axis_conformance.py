#!/usr/bin/env python3
"""Tier-A 3-axis automation conformance assertion harness.

HALF-2 Tier A (refactor/automation goal 0601 §3). CLEAN-YARD v3 (Smith 0611):
the product repo ships NO standing dogfood Building; a check that needs a
conformant Building GENERATES it with the REAL engine at check time, asserts,
and removes it. On every run this harness drives ``run_building_plan``
(dynamic graph dispatch, adapter:local) over a declared graph plan that
replays the original tier-a topology -- work, a review that proposes a
non-binding reroute back to work (ADOPTED under the default gate within the
per-node budget of 1), a mid node, a second review that proposes the same
reroute past the exhausted budget (HOLD), then a caller/COO ``raise``
disposition row + ``resume_building_plan`` to an unheld close with
caller-supplied Carry/Transfer facts -- into a TEMP output root (never the
repo tree; removed in ``finally``). It then ASSERTS that this authentic engine
run exercised all three axes plus the Link mechanics plus the full evidence
shape, and that the engine wrote ``declaration_provenance`` (closing the P1
hole). The Building id is parameterized (``TIER_A_BUILDING_ID``); no project
vessel is touched. It is the deterministic regression net re-run after each
P3 extraction.

It asserts, per the goal axis table:

  Brick     -- the declared launch chain is persisted (task.md + building-intake +
               preset-expansion + declared-building-plan + link-launch-policy +
               building-map) AND a BrickWork contract per executed step.
  Agent     -- every returned Agent fact is the closed 2-field AgentFact
               (received_work, returned), names a declared performer binding
               (agent_object_ref), and its received_work references the declared
               Brick/Agent binding it answered.
  Link      -- forward Movement present + at least one ADOPTED declared reroute +
               a gate sufficiency decision + a Link-assigned reroute budget +
               transition pause (HOLD) then resume + carry and transfer across a
               boundary, all read from the persisted link traces / walker evidence.
  Evidence  -- claim_trace/{brick,agent,link} + raw streams + raw-manifest +
               evidence-manifest + building-map are present, and the root is a
               complete-run root (not a frontier-only / stub root).

This checker is SUPPORT EVIDENCE ONLY. It decides nothing; it is not source
truth, not success judgment, not quality judgment, and not Movement authority.
It admits no axis / fact class and imports no axis module (independent oracle).
A family of anti-tautological FIRE negative probes synthesizes degraded copies of
the produced root: the original combined probe drops the reroute trace AND the
declaration_provenance, and five sibling probes each drop exactly ONE axis-evidence
-- the Brick work_statement, the closed AgentFact shape, the Link carry, the Link
transfer, and the Link gate sufficiency. Each probe requires the harness to report
that copy unmet WITH the specific violation the dropped evidence raises. The kernel
check raises if any probe was not reported, so a harness that silently stops
asserting any one axis-evidence drives ``--all`` RED.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


# CLEAN-YARD v3: the asserted root is GENERATED per run into a temp dir; the
# id is parameterized and intentionally distinct from the retired project #1
# dogfood id (tier-a-3axis-conformance-0, preserved in the frozen museum repo).
TIER_A_BUILDING_ID = "tier-a-3axis-case0"

BUILDING_MAP_REL = ("work", "building-map.json")
EVIDENCE_MANIFEST_REL = ("evidence", "evidence-manifest.json")
RAW_MANIFEST_REL = ("raw", "raw-manifest.json")
RETURNED_CLAIMS_REL = ("evidence", "claim_trace", "agent", "returned_claims.json")
MOVEMENT_TRACE_REL = ("evidence", "claim_trace", "link", "movement_trace.json")
SUFFICIENCY_TRACE_REL = ("evidence", "claim_trace", "link", "sufficiency_trace.json")
CARRY_TRACE_REL = ("evidence", "claim_trace", "link", "carry_trace.json")
TRANSFER_TRACE_REL = ("evidence", "claim_trace", "link", "transfer_trace.json")
WORK_CONTRACT_REL = ("evidence", "claim_trace", "brick", "work_contract.json")

# The four declared launch-chain artifacts a declaration_provenance engine run
# must persist (goal §3 Brick row + the P1 declaration-integrity gap-2 set).
DECLARATION_CHAIN_ARTIFACTS = (
    ("work", "task.md"),
    ("work", "building-intake.json"),
    ("work", "preset-expansion.json"),
    ("work", "declared-building-plan.json"),
    ("work", "link-launch-policy.json"),
    ("work", "building-map.json"),
)

# The evidence-shape files a complete-run root must carry (goal §3 Evidence row).
EVIDENCE_SHAPE_FILES = (
    RAW_MANIFEST_REL,
    EVIDENCE_MANIFEST_REL,
    WORK_CONTRACT_REL,
    RETURNED_CLAIMS_REL,
    MOVEMENT_TRACE_REL,
    SUFFICIENCY_TRACE_REL,
    CARRY_TRACE_REL,
    TRANSFER_TRACE_REL,
)

AGENT_PERFORMER_PREFIX = "agent-performer:"

PROOF_LIMIT = (
    "proof limit: tier-a 3-axis conformance support check only; this does not "
    "prove content correctness, source truth, success judgment, quality "
    "judgment, Movement authority, or real-provider behavior."
)


class TierAConformanceError(ValueError):
    """Raised when the produced Tier-A Building root fails a conformance assertion."""


# ---------------------------------------------------------------------------
# evidence readers
# ---------------------------------------------------------------------------
def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    value = _read_json(path)
    return value if isinstance(value, Mapping) else {}


def _read_jsonl(path: Path) -> list[Mapping[str, Any]]:
    if not path.is_file():
        return []
    records: list[Mapping[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            records.append(value)
    return records


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _facts(claim: Any) -> list[Mapping[str, Any]]:
    if not isinstance(claim, Mapping):
        return []
    out = claim.get("facts")
    if isinstance(out, list):
        return [item for item in out if isinstance(item, Mapping)]
    return []


def _dynamic_walker_evidence(building_root: Path) -> Mapping[str, Any]:
    """Read the dynamic-walker evidence from the written evidence-manifest snapshot.

    The reroute-adoption records, node reroute budget map, landing map, held flag,
    and resume observations are persisted inside
    ``evidence/evidence-manifest.json`` -> ``plan_snapshot.plan_rows_copy`` (a JSON
    string of the walked plan) -> ``dynamic_walker_evidence``.
    """

    manifest = _read_json_mapping(building_root / Path(*EVIDENCE_MANIFEST_REL))
    snapshot = manifest.get("plan_snapshot")
    if not isinstance(snapshot, Mapping):
        return {}
    plan_copy = _text(snapshot.get("plan_rows_copy"))
    if not plan_copy:
        return {}
    try:
        plan = json.loads(plan_copy)
    except json.JSONDecodeError:
        return {}
    if not isinstance(plan, Mapping):
        return {}
    evidence = plan.get("dynamic_walker_evidence")
    return evidence if isinstance(evidence, Mapping) else {}


# ---------------------------------------------------------------------------
# per-axis assertions
# ---------------------------------------------------------------------------
def assert_brick(building_root: Path, *, label: str, unmet: list[str]) -> None:
    """Brick: the persisted launch chain + a BrickWork contract per executed step."""

    for artifact in DECLARATION_CHAIN_ARTIFACTS:
        if not (building_root / Path(*artifact)).is_file():
            unmet.append(
                f"{label}: Brick launch-chain artifact work/{artifact[-1]} is not persisted"
            )

    work_contract = _read_json(building_root / Path(*WORK_CONTRACT_REL))
    brick_facts = _facts(work_contract)
    if not brick_facts:
        unmet.append(f"{label}: Brick work_contract.json carries no BrickWork contract facts")
        return
    has_work_statement = any(
        isinstance(fact.get("fact"), Mapping)
        and _text(fact["fact"].get("work_statement"))
        for fact in brick_facts
    )
    if not has_work_statement:
        unmet.append(
            f"{label}: no Brick fact records a work_statement (BrickWork contract per step)"
        )


def assert_agent(building_root: Path, *, label: str, unmet: list[str]) -> None:
    """Agent: closed AgentFact {received_work, returned} + performer + declared binding.

    Reuses the persisted building-map declared bindings as the truth of what was
    declared, and asserts every returned Agent fact answers one of them.
    """

    building_map = _read_json_mapping(building_root / Path(*BUILDING_MAP_REL))
    declared_object_refs = _declared_performer_object_refs(building_map)
    declared_tails = _declared_binding_tails(building_map)

    returned = _read_json(building_root / Path(*RETURNED_CLAIMS_REL))
    agent_facts = [fact for fact in _facts(returned) if fact.get("axis") == "Agent"]
    if not agent_facts:
        unmet.append(f"{label}: no returned Agent facts in returned_claims.json")
        return

    for index, fact in enumerate(agent_facts):
        envelope = fact.get("fact")
        envelope_map = envelope if isinstance(envelope, Mapping) else {}
        fact_ref = _text(fact.get("fact_ref")) or f"#{index}"

        # closed 2-field AgentFact: received_work + returned, nothing else load-bearing.
        agent_fields = envelope_map.get("agent_fact_fields")
        if not (isinstance(agent_fields, list) and set(agent_fields) == {"received_work", "returned"}):
            unmet.append(
                f"{label}: Agent fact {fact_ref} is not the closed 2-field AgentFact "
                "(received_work, returned)"
            )
        if "received_work" not in envelope_map or "returned" not in envelope_map:
            unmet.append(
                f"{label}: Agent fact {fact_ref} envelope is missing received_work/returned"
            )

        # performer binding: a declared agent_object_ref.
        object_ref = _text(envelope_map.get("agent_object_ref"))
        if not object_ref or object_ref not in declared_object_refs:
            unmet.append(
                f"{label}: Agent fact {fact_ref} agent_object_ref {object_ref!r} is not a "
                "declared performer binding"
            )

        # returned references the declared binding it answered (shared step-slug tail).
        received_tail = _ref_tail(_text(envelope_map.get("received_work")))
        if not received_tail or received_tail not in declared_tails:
            unmet.append(
                f"{label}: Agent fact {fact_ref} received_work does not reference a declared "
                "Brick/Agent binding"
            )


def assert_link(
    building_root: Path,
    *,
    label: str,
    unmet: list[str],
    held_stage_root: Path | None = None,
) -> None:
    """Link: forward + reroute + gate sufficiency + budget + pause/resume + carry/transfer.

    ``held_stage_root``: the engine's resume path regenerates the final
    evidence with the held proposal re-recorded as an adoption, so the
    budget-exhaustion HOLD record exists in the evidence written AT THE HELD
    STAGE (link_paused, before the caller/COO disposition). The generation
    flow snapshots that stage; the HOLD assertion consults the final records
    first (historical complete roots carried it) and falls back to the held
    snapshot. Without either, the bound is reported unmet.
    """

    # forward Movement present (movement_trace records forward movement facts).
    movement_trace = _read_json(building_root / Path(*MOVEMENT_TRACE_REL))
    movement_facts = _facts(movement_trace)
    forward_movements = [
        fact
        for fact in movement_facts
        if isinstance(fact.get("fact"), Mapping)
        and _text(fact["fact"].get("movement")) == "forward"
    ]
    if not forward_movements:
        unmet.append(f"{label}: Link movement_trace records no forward Movement")

    evidence = _dynamic_walker_evidence(building_root)
    records = evidence.get("reroute_adoption_records")
    records = records if isinstance(records, list) else []

    # >= 1 ADOPTED declared reroute (disposition_required false, a real attempt).
    adopted = [
        rec
        for rec in records
        if isinstance(rec, Mapping)
        and rec.get("disposition_required") is False
        and _text(rec.get("target_brick"))
        and int(rec.get("attempt_number", 0)) >= 1
    ]
    if not adopted:
        unmet.append(f"{label}: no ADOPTED reroute-adoption record in dynamic_walker_evidence")

    # Link-assigned reroute budget (the per-target-node budget map).
    budgets = evidence.get("node_reroute_budgets")
    if not (isinstance(budgets, Mapping) and any(
        isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in budgets.values()
    )):
        unmet.append(f"{label}: no positive Link-assigned node reroute budget recorded")

    # budget / max_attempts bounded: a HOLD on budget exhaustion was reached.
    def _budget_holds(record_list: list[Any]) -> list[Mapping[str, Any]]:
        return [
            rec
            for rec in record_list
            if isinstance(rec, Mapping)
            and rec.get("disposition_required") is True
            and rec.get("budget_exhausted") is True
        ]

    budget_holds = _budget_holds(records)
    if not budget_holds and held_stage_root is not None:
        held_evidence = _dynamic_walker_evidence(held_stage_root)
        held_records = held_evidence.get("reroute_adoption_records")
        budget_holds = _budget_holds(held_records if isinstance(held_records, list) else [])
    if not budget_holds:
        unmet.append(
            f"{label}: no budget-exhaustion HOLD record (budget/max_attempts bound not exercised)"
        )

    # pause (HOLD) then resume: a resume observation closed the held landing AND the
    # final walk is not left held.
    resume_observations = evidence.get("resume_observations")
    resume_observations = resume_observations if isinstance(resume_observations, list) else []
    # A resume observation records the applied disposition. We only assert a
    # disposition_action was PRESENT (the resume happened) and that the landing
    # re-entered; the engine (link/transition.py) owns the disposition_action
    # enum, so this oracle does not re-list it (axis-vocab single-source).
    applied_resume = [
        obs
        for obs in resume_observations
        if isinstance(obs, Mapping)
        and _text(obs.get("disposition_action"))
        and _text(obs.get("applied"))
    ]
    if not applied_resume:
        unmet.append(f"{label}: no resume observation (transition pause/resume not exercised)")
    if evidence.get("held") is not False:
        unmet.append(
            f"{label}: dynamic_walker_evidence.held is not False after resume (Building not "
            "resumed to an unheld frontier)"
        )

    # the held disposition row was authored by a caller/COO owner and persisted.
    disposition_rows = [
        record
        for record in _read_jsonl(building_root / "raw" / "link.jsonl")
        if _disposition_action_from_record(record)
    ]
    if not any(
        _disposition_author_ref(record).startswith(("human:", "coo:"))
        for record in disposition_rows
    ):
        unmet.append(
            f"{label}: no caller/COO-authored resume disposition row persisted in raw/link.jsonl"
        )

    # carry AND transfer across a boundary (a caller-supplied present fact, not an
    # absence placeholder).
    if not _has_present_caller_fact(building_root / Path(*CARRY_TRACE_REL)):
        unmet.append(f"{label}: no present caller-supplied CarryFact in carry_trace.json")
    if not _has_present_caller_fact(building_root / Path(*TRANSFER_TRACE_REL)):
        unmet.append(f"{label}: no present caller-supplied TransferFact in transfer_trace.json")

    # gate sufficiency decision recorded (a sufficiency trace fact with a verdict).
    sufficiency = _read_json(building_root / Path(*SUFFICIENCY_TRACE_REL))
    sufficiency_facts = _facts(sufficiency)
    has_sufficiency = any(
        isinstance(fact.get("fact"), Mapping)
        and (
            _text(fact["fact"].get("sufficiency"))
            or "sufficiency" in fact["fact"]
            or _text(fact["fact"].get("checked_public_fact"))
        )
        for fact in sufficiency_facts
    )
    if not has_sufficiency:
        unmet.append(f"{label}: no Link gate sufficiency decision recorded in sufficiency_trace.json")


def assert_evidence(building_root: Path, *, label: str, unmet: list[str]) -> None:
    """Evidence: claim_trace/{brick,agent,link} + raw + manifest + building-map + complete-run."""

    for record in EVIDENCE_SHAPE_FILES:
        if not (building_root / Path(*record)).is_file():
            unmet.append(f"{label}: evidence-shape file {'/'.join(record)} is missing")

    # complete-run-only root: the AgentFact returned trace exists (not a frontier
    # stub that only carries receipt/frontier traces).
    if not (building_root / Path(*RETURNED_CLAIMS_REL)).is_file():
        unmet.append(
            f"{label}: returned_claims.json absent -- this is not a complete-run root"
        )

    # raw manifest has entries with raw_refs (the raw streams are recorded).
    raw_manifest = _read_json_mapping(building_root / Path(*RAW_MANIFEST_REL))
    entries = raw_manifest.get("entries")
    if not (isinstance(entries, list) and entries):
        unmet.append(f"{label}: raw-manifest.json has no raw stream entries")


def assert_declaration_provenance(building_root: Path, *, label: str, unmet: list[str]) -> None:
    """The engine wrote declaration_provenance (closes the P1 hole)."""

    building_map = _read_json_mapping(building_root / Path(*BUILDING_MAP_REL))
    provenance = building_map.get("declaration_provenance")
    if not isinstance(provenance, Mapping) or not provenance:
        unmet.append(f"{label}: building-map.json records no declaration_provenance")
        return
    if not _text(provenance.get("composition_mode")):
        unmet.append(f"{label}: declaration_provenance records no composition_mode")
    if not _text(provenance.get("task_source_ref")):
        unmet.append(f"{label}: declaration_provenance records no task_source_ref")


# ---------------------------------------------------------------------------
# binding helpers (read declared truth from the persisted building-map)
# ---------------------------------------------------------------------------
def _ref_tail(value: str) -> str:
    text = _text(value)
    if ":" not in text:
        return ""
    return text.split(":", 1)[1].strip()


def _declared_performer_object_refs(building_map: Mapping[str, Any]) -> set[str]:
    refs: set[str] = set()
    bindings = building_map.get("agent_bindings")
    if isinstance(bindings, list):
        for binding in bindings:
            if not isinstance(binding, Mapping):
                continue
            performer = _text(binding.get("agent_performer_ref"))
            if performer.startswith(AGENT_PERFORMER_PREFIX):
                object_ref = performer[len(AGENT_PERFORMER_PREFIX):].strip()
                if object_ref:
                    refs.add(object_ref)
            object_ref = _text(binding.get("agent_object_ref"))
            if object_ref:
                refs.add(object_ref)
    return refs


def _declared_binding_tails(building_map: Mapping[str, Any]) -> set[str]:
    tails: set[str] = set()
    bindings = building_map.get("agent_bindings")
    if isinstance(bindings, list):
        for binding in bindings:
            if not isinstance(binding, Mapping):
                continue
            tail = _ref_tail(_text(binding.get("agent_binding_id")))
            if tail:
                tails.add(tail)
    return tails


def _disposition_action_from_record(record: Mapping[str, Any]) -> str:
    nested = record.get("transition_lifecycle")
    if isinstance(nested, Mapping):
        return _text(nested.get("disposition_action"))
    return _text(record.get("transition_lifecycle_disposition_action"))


def _disposition_author_ref(record: Mapping[str, Any]) -> str:
    for key in ("author_ref", "transition_author_ref", "route_replay_author_ref"):
        value = _text(record.get(key))
        if value:
            return value
    authoring = record.get("transition_authoring")
    if isinstance(authoring, Mapping):
        value = _text(authoring.get("author_ref"))
        if value:
            return value
    return ""


def _has_present_caller_fact(trace_path: Path) -> bool:
    """A carry/transfer trace fact that is a PRESENT caller-supplied fact.

    The accumulated writer emits an ``absence_placeholder`` fact for every step
    that declared no carry/transfer, plus a real fact (``caller_supplied: true``,
    no ``absent_fact_type``) for the step that declared one. The mechanic is
    evidenced only by a present real fact.
    """

    for fact in _facts(_read_json(trace_path)):
        envelope = fact.get("fact")
        if not isinstance(envelope, Mapping):
            continue
        if envelope.get("caller_supplied") is True and not _text(envelope.get("absent_fact_type")):
            return True
    return False


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def assert_building_conformance(
    building_root: Path,
    *,
    label: str | None = None,
    held_stage_root: Path | None = None,
) -> list[str]:
    """Run every Tier-A conformance assertion against one Building root."""

    root_label = label or building_root.name
    unmet: list[str] = []
    if not building_root.is_dir():
        return [f"{root_label}: Tier-A Building root does not exist: {building_root}"]
    assert_brick(building_root, label=root_label, unmet=unmet)
    assert_agent(building_root, label=root_label, unmet=unmet)
    assert_link(building_root, label=root_label, unmet=unmet, held_stage_root=held_stage_root)
    assert_evidence(building_root, label=root_label, unmet=unmet)
    assert_declaration_provenance(building_root, label=root_label, unmet=unmet)
    return unmet


# ---------------------------------------------------------------------------
# EPHEMERAL GENERATION (CLEAN-YARD v3): build the conformant root with the
# REAL engine at check time. Engine modules are imported lazily inside the
# generator only; the ASSERTIONS above read evidence files and import no axis
# module (independent oracle preserved).
# ---------------------------------------------------------------------------
def _ensure_import_identity(repo: Path) -> None:
    identity = repo / "support" / "import_identity"
    for candidate in (str(identity), str(repo)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


def _tier_a_proof_limits() -> list[str]:
    return [
        "support evidence only",
        "tier-a deterministic adapter:local 3-axis conformance run",
        "support authors no route or Movement",
        "not source truth",
        "not success judgment",
        "not quality judgment",
        "not Movement authority",
    ]


def _tier_a_brick_step(
    prefix: str,
    word: str,
    brick_ref: str,
    agent_ref: str,
    completion_edge_ref: str,
    *,
    required_return_shape: str = "observed_evidence, not_proven",
) -> dict[str, Any]:
    step_ref = f"{prefix}-{word}"
    return {
        "step_ref": step_ref,
        "completion_edge_ref": completion_edge_ref,
        "rows": [
            {
                "axis": "Brick",
                "row_ref": f"brick-row:{step_ref}",
                "brick_work_ref": f"work:{step_ref}",
                "brick_instance_ref": brick_ref,
                "work_statement": (
                    f"Tier-A case node {word}: produce a one-line build note. "
                    "Return ONE JSON object with exactly the required fields. "
                    "Do not choose Movement. Do not report success, failure, "
                    "approval, or quality."
                ),
                "comparison_rule": (
                    "support observes the adapter:local return shape; "
                    "support does not judge quality."
                ),
                "required_return_shape": required_return_shape,
            },
            {"axis": "Agent", "row_ref": f"agent-row:{step_ref}", "agent_object_ref": agent_ref},
        ],
    }


def tier_a_case_plan(building_id: str) -> tuple[dict[str, Any], dict[str, str]]:
    """The declared graph plan replaying the original tier-a topology."""

    prefix = building_id
    bricks = {
        "work": f"brick-{prefix}-work",
        "review-1": f"brick-{prefix}-review-1",
        "mid": f"brick-{prefix}-mid",
        "review-2": f"brick-{prefix}-review-2",
        "close": f"brick-{prefix}-close",
    }
    boundary = f"building-boundary:{building_id}-closed"
    default_gate = ["link-gate:default-transition"]

    def _fwd(edge: str, src_word: str, tgt_word: str) -> dict[str, Any]:
        return {
            "edge_ref": edge,
            "source_step_ref": f"{prefix}-{src_word}",
            "target_step_ref": f"{prefix}-{tgt_word}",
            "rows": [
                {
                    "axis": "Link",
                    "row_ref": f"link-row:{edge}",
                    "movement": "forward",
                    "target_ref": bricks[tgt_word],
                    "declared_gate_refs": list(default_gate),
                }
            ],
        }

    close_edge = {
        "edge_ref": f"edge:{prefix}-close-to-boundary",
        "source_step_ref": f"{prefix}-close",
        "caller_supplied_link_facts": {
            "carry_fact": {
                "carried_fact_refs": [f"agent-fact:{building_id}:{prefix}-work"],
                "evidence_reference": f"carry:{prefix}-work-to-boundary",
                "source_owner_axis": "Agent",
                "target_boundary_ref": boundary,
                "proof_limits": ["support evidence only", "not Movement authority"],
                "not_proven": ["semantic correctness of the carried fact"],
            },
            "transfer_fact": {
                "evidence_reference": f"transfer:{prefix}-close-to-boundary",
                "source_boundary_ref": bricks["close"],
                "target_boundary_ref": boundary,
                "work_context_ref": f"work:{prefix}-close",
                "public_fact_refs": [f"agent-fact:{building_id}:{prefix}-close"],
                "required_public_facts": [f"agent-fact:{building_id}:{prefix}-close"],
                "proof_limits": ["support evidence only", "not Movement authority"],
                "not_proven": ["semantic correctness of the transferred work context"],
            },
        },
        "rows": [
            {
                "axis": "Link",
                "row_ref": f"link-row:{prefix}-close-to-boundary",
                "movement": "forward",
                "building_lifecycle": {
                    "state": "closed",
                    "reason": (
                        "tier-a case walked work, a review that proposed a "
                        "non-binding reroute to the work node (adopted within "
                        "the per-node budget of 1), a mid node, a second review "
                        "that proposed the same reroute past the exhausted "
                        "budget (HOLD), and after a caller/COO raise disposition "
                        "resumed and closed."
                    ),
                },
                "target_ref": boundary,
                "declared_gate_refs": list(default_gate),
            }
        ],
    }

    plan: dict[str, Any] = {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "graph",
        "composition_mode": "caller_or_coo_declared_graph_composition",
        "declared_by": f"coo {building_id}",
        "selected_adapter_ref": "adapter:local",
        "selected_model_ref": "model:default",
        # TASK-BY-TEXT inline flow: the sentinel task_source_ref admits the
        # inline statement; the evidence writer lands it as work/task.md.
        "task_source_ref": "task-source:inline-statement",
        "task_statement": (
            "Tier-A 3-axis conformance case: one deterministic adapter:local "
            "engine run exercising Brick + Agent + Link mechanics + Evidence + "
            "declaration provenance, generated at check time and removed after."
        ),
        "proof_limits": _tier_a_proof_limits(),
        "not_proven": [
            "semantic correctness of the agent-proposed reroute",
            "real provider behavior",
            "scheduler / queue / retry behavior",
        ],
        "execution_order": [
            f"{prefix}-work",
            f"{prefix}-review-1",
            f"{prefix}-mid",
            f"{prefix}-review-2",
            f"{prefix}-close",
        ],
        "brick_steps": [
            _tier_a_brick_step(prefix, "work", bricks["work"], "agent-object:dev", f"edge:{prefix}-work-to-review-1"),
            _tier_a_brick_step(
                prefix,
                "review-1",
                bricks["review-1"],
                "agent-object:qa",
                f"edge:{prefix}-review-1-to-mid",
                required_return_shape="observed_evidence, transition_concern_evidence, not_proven",
            ),
            _tier_a_brick_step(prefix, "mid", bricks["mid"], "agent-object:inspector", f"edge:{prefix}-mid-to-review-2"),
            _tier_a_brick_step(
                prefix,
                "review-2",
                bricks["review-2"],
                "agent-object:qa",
                f"edge:{prefix}-review-2-to-close",
                required_return_shape="observed_evidence, transition_concern_evidence, not_proven",
            ),
            _tier_a_brick_step(prefix, "close", bricks["close"], "agent-object:coo", f"edge:{prefix}-close-to-boundary"),
        ],
        "link_edges": [
            _fwd(f"edge:{prefix}-work-to-review-1", "work", "review-1"),
            _fwd(f"edge:{prefix}-review-1-to-mid", "review-1", "mid"),
            _fwd(f"edge:{prefix}-mid-to-review-2", "mid", "review-2"),
            _fwd(f"edge:{prefix}-review-2-to-close", "review-2", "close"),
            close_edge,
        ],
        "node_reroute_budgets": {bricks["work"]: 1},
    }
    return plan, bricks


def _tier_a_case_callable(bricks: Mapping[str, str]):
    """adapter:local brain: reviews propose a non-binding reroute to work."""

    review_sources = {bricks["review-1"], bricks["review-2"]}

    def _callable(request: Any) -> Mapping[str, Any]:
        source = str(getattr(request, "brick_instance_ref", "") or "")
        if source in review_sources:
            return {
                "observed_evidence": [f"reviewed {bricks['work']} and found it incomplete"],
                "transition_concern_evidence": {
                    "concern_ref": f"transition-concern:{source}-incomplete-work",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"observation:{source}"],
                    "related_boundary_refs": [bricks["work"]],
                },
                "not_proven": ["semantic correctness of the proposed reroute"],
            }
        return {
            "observed_evidence": [f"completed declared work for {source}"],
            "not_proven": ["semantic correctness of the returned note"],
        }

    return _callable


def _append_raise_disposition_row(
    building_root: Path,
    *,
    building_id: str,
    pending_target_ref: str,
) -> None:
    """Append the caller/COO ``raise`` disposition row (the human seam).

    The disposition row is the CALLER/COO-authored resume input the engine
    requires; support records it verbatim and never decides it.

    FIX 2 (0611, "THIS resume only"): the row must be ADDRESSED to the hold it
    disposes -- the resume reader (walker_resume._read_disposition_row) now
    requires the row's ``resumed_from_ref``/``paused_at_ref`` to equal the
    CURRENT hold's identity (``link-transition:<reroute_ref>``). Mirror the
    real human seam: read the held record back from the written evidence and
    echo its identity.
    """

    from brick_protocol.support.operator.walker_hold import (  # noqa: PLC0415
        _hold_paused_at_ref,
    )
    from brick_protocol.support.operator.walker_resume import (  # noqa: PLC0415
        _read_written_dynamic_plan,
    )

    _plan, evidence = _read_written_dynamic_plan(building_root)
    hold = evidence.get("hold")
    if not isinstance(hold, Mapping) or not evidence.get("held"):
        raise ValueError(
            "tier-a disposition authoring requires a held dynamic_walker_evidence "
            "record to address (FIX 2: a disposition row names ITS hold)"
        )
    row = {
        "raw_ref": "raw:link:disposition:raise",
        "building_id": building_id,
        "step_ref": "coo-disposition-raise",
        "transition_lifecycle_state": "resumed",
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_resumed_from_ref": _hold_paused_at_ref(hold),
        "transition_lifecycle_pending_target_ref": pending_target_ref,
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_disposition_action": "raise",
        "transition_lifecycle_budget_increment": 1,
        "transition_author_ref": f"coo:{building_id}",
    }
    with (building_root / "raw" / "link.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def generate_tier_a_case_root(repo: Path, output_root: Path) -> tuple[Path, Path]:
    """Drive the REAL engine end-to-end; return (final_root, held_stage_root).

    run -> HOLD on budget exhaustion (link_paused; the held stage is
    SNAPSHOTTED because the resume path regenerates the evidence with the
    held proposal re-recorded as an adoption) -> caller/COO raise disposition
    -> resume -> unheld close. Raises on any engine failure (fail-closed).
    """

    _ensure_import_identity(repo)
    from brick_protocol.support.operator.building_operation import (  # noqa: PLC0415
        observe_building_frontier,
    )
    from brick_protocol.support.operator.run import (  # noqa: PLC0415 -- lazy engine import
        resume_building_plan,
        run_building_plan,
    )

    plan, bricks = tier_a_case_plan(TIER_A_BUILDING_ID)
    brain = _tier_a_case_callable(bricks)
    callables = {"callable:local:agent-invoke0-smoke": brain}
    result = run_building_plan(
        plan,
        output_root=output_root,
        overwrite_existing=True,
        local_callables=callables,
        adapter_cwd=repo,
        adapter_timeout_seconds=30,
    )
    root = Path(result.lifecycle_write.root)
    held_frontier = observe_building_frontier(root, repo_root=repo)
    if held_frontier.get("frontier_kind") != "link_paused":
        raise ValueError(
            "tier-a generation did not HOLD on budget exhaustion "
            f"(frontier={held_frontier.get('frontier_kind')!r}); the budget bound "
            "was not exercised"
        )
    held_stage_root = output_root.parent / "held-snapshot" / root.name
    held_stage_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root, held_stage_root)
    _append_raise_disposition_row(
        root,
        building_id=TIER_A_BUILDING_ID,
        pending_target_ref=bricks["work"],
    )
    resume_building_plan(
        root,
        local_callables=callables,
        adapter_cwd=repo,
        adapter_timeout_seconds=30,
    )
    return root, held_stage_root


def check_generated_root(root: Path, held_stage_root: Path | None = None) -> list[str]:
    if not root.is_dir():
        return [
            f"tier-a generated building root not found: {root} "
            "(the engine generation failed to land a root)"
        ]
    return assert_building_conformance(
        root, label=f"generated:{root.name}", held_stage_root=held_stage_root
    )


# ---------------------------------------------------------------------------
# anti-tautological FIRE probe
# ---------------------------------------------------------------------------
def fire_probe(source: Path) -> Mapping[str, Any]:
    """FIRE: a degraded copy with the reroute trace + provenance dropped must fail.

    Copies the GENERATED Tier-A root into a temp dir, then mutates the evidence
    to (a) drop the dynamic_walker_evidence reroute records (so reroute / budget /
    pause-resume can no longer be evidenced) and (b) drop declaration_provenance
    from the building-map. The harness MUST report unmet assertions on the
    degraded copy; if it does not, the harness has stopped asserting.
    """

    if not source.is_dir():
        return {
            "probe_ref": "tier-a-conformance-probe:reroute_and_provenance_dropped",
            "fired": False,
            "reason": "tier-a generated building root not present to derive a FIRE probe from",
        }

    with tempfile.TemporaryDirectory(prefix="bp-tier-a-fire-") as tmp:
        degraded = Path(tmp) / "buildings" / (TIER_A_BUILDING_ID + "-degraded")
        shutil.copytree(source, degraded)

        # (a) drop the reroute records / budget / held flag from the persisted
        # evidence-manifest plan snapshot.
        _degrade_drop_reroute_evidence(degraded)

        # (b) drop declaration_provenance from the building-map.
        _degrade_drop_declaration_provenance(degraded)

        unmet = assert_building_conformance(degraded, label="tier-a-degraded-probe")
        mentions_reroute = any("reroute" in violation.lower() for violation in unmet)
        mentions_provenance = any("declaration_provenance" in violation for violation in unmet)
    return {
        "probe_ref": "tier-a-conformance-probe:reroute_and_provenance_dropped",
        "fired": bool(unmet) and mentions_reroute and mentions_provenance,
        "unmet_count": len(unmet),
        "unmet": unmet,
        "proof_limits": ["negative probe support evidence only"],
    }


# ---------------------------------------------------------------------------
# per-axis degradation mutators (each applies ONE degradation to a copied root)
# ---------------------------------------------------------------------------
def _rewrite_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _degraded_facts_claim(path: Path) -> tuple[dict[str, Any], list[Any]]:
    """Return the (mutable claim mapping, mutable facts list) at ``path``.

    Returns empty containers when the claim is absent/malformed so a degradation
    mutator can no-op cleanly; the caller decides whether the no-op is acceptable.
    """

    claim = _read_json(path)
    if not isinstance(claim, Mapping):
        return {}, []
    claim_dict = dict(claim)
    facts = claim_dict.get("facts")
    facts_list = list(facts) if isinstance(facts, list) else []
    return claim_dict, facts_list


def _degrade_drop_reroute_evidence(degraded: Path) -> None:
    """Drop dynamic_walker_evidence from the persisted evidence-manifest snapshot.

    Removes the reroute-adoption records / budget map / held flag so reroute,
    budget, and pause/resume can no longer be evidenced.
    """

    manifest_path = degraded / Path(*EVIDENCE_MANIFEST_REL)
    manifest = _read_json_mapping(manifest_path)
    snapshot = manifest.get("plan_snapshot")
    if not isinstance(snapshot, Mapping):
        return
    plan_copy = _text(snapshot.get("plan_rows_copy"))
    if not plan_copy:
        return
    try:
        plan = json.loads(plan_copy)
    except json.JSONDecodeError:
        return
    if not isinstance(plan, dict):
        return
    plan.pop("dynamic_walker_evidence", None)
    new_snapshot = dict(snapshot)
    new_snapshot["plan_rows_copy"] = json.dumps(plan)
    new_manifest = dict(manifest)
    new_manifest["plan_snapshot"] = new_snapshot
    _rewrite_json(manifest_path, new_manifest)


def _degrade_drop_declaration_provenance(degraded: Path) -> None:
    """Drop declaration_provenance from the persisted building-map."""

    map_path = degraded / Path(*BUILDING_MAP_REL)
    building_map = _read_json_mapping(map_path)
    if not building_map:
        return
    mutated = dict(building_map)
    mutated.pop("declaration_provenance", None)
    _rewrite_json(map_path, mutated)


def _degrade_break_agent_fact_shape(degraded: Path) -> None:
    """Break the closed AgentFact shape (Agent axis).

    Appends a third field to every Agent fact's ``agent_fact_fields`` so the
    envelope is no longer the closed 2-field {received_work, returned}. The
    assert_agent closed-shape check must then report the fact unmet.
    """

    path = degraded / Path(*RETURNED_CLAIMS_REL)
    claim, facts = _degraded_facts_claim(path)
    if not facts:
        return
    new_facts: list[Any] = []
    for fact in facts:
        if isinstance(fact, Mapping) and fact.get("axis") == "Agent":
            fact = dict(fact)
            envelope = fact.get("fact")
            if isinstance(envelope, Mapping):
                envelope = dict(envelope)
                fields = envelope.get("agent_fact_fields")
                fields_list = list(fields) if isinstance(fields, list) else []
                fields_list.append("smuggled_third_field")
                envelope["agent_fact_fields"] = fields_list
                envelope["smuggled_third_field"] = "not-a-closed-AgentFact"
                fact["fact"] = envelope
        new_facts.append(fact)
    claim["facts"] = new_facts
    _rewrite_json(path, claim)


def _degrade_drop_present_carry(degraded: Path) -> None:
    """Drop the present caller-supplied CarryFact (Link).

    Keeps only the ``absence_placeholder`` facts, so no present carry across a
    boundary is evidenced; assert_link's carry check must report it unmet.
    """

    path = degraded / Path(*CARRY_TRACE_REL)
    claim, facts = _degraded_facts_claim(path)
    if not facts:
        return
    claim["facts"] = [
        fact
        for fact in facts
        if not (
            isinstance(fact, Mapping)
            and isinstance(fact.get("fact"), Mapping)
            and fact["fact"].get("caller_supplied") is True
            and not _text(fact["fact"].get("absent_fact_type"))
        )
    ]
    _rewrite_json(path, claim)


def _degrade_drop_present_transfer(degraded: Path) -> None:
    """Drop the present caller-supplied TransferFact (Link).

    Keeps only the ``absence_placeholder`` facts, so no present transfer across a
    boundary is evidenced; assert_link's transfer check must report it unmet.
    """

    path = degraded / Path(*TRANSFER_TRACE_REL)
    claim, facts = _degraded_facts_claim(path)
    if not facts:
        return
    claim["facts"] = [
        fact
        for fact in facts
        if not (
            isinstance(fact, Mapping)
            and isinstance(fact.get("fact"), Mapping)
            and fact["fact"].get("caller_supplied") is True
            and not _text(fact["fact"].get("absent_fact_type"))
        )
    ]
    _rewrite_json(path, claim)


def _degrade_empty_sufficiency(degraded: Path) -> None:
    """Empty the Link gate sufficiency_trace facts (Link gate).

    Removes every sufficiency decision so no gate sufficiency verdict is
    evidenced; assert_link's sufficiency check must report it unmet.
    """

    path = degraded / Path(*SUFFICIENCY_TRACE_REL)
    claim, facts = _degraded_facts_claim(path)
    if not facts:
        return
    claim["facts"] = []
    _rewrite_json(path, claim)


def _degrade_drop_work_statement(degraded: Path) -> None:
    """Drop work_statement from every Brick work_contract fact (Brick).

    Removes the BrickWork work_statement so no Brick fact records a per-step work
    contract; assert_brick's work_statement check must report it unmet.
    """

    path = degraded / Path(*WORK_CONTRACT_REL)
    claim, facts = _degraded_facts_claim(path)
    if not facts:
        return
    new_facts: list[Any] = []
    for fact in facts:
        if isinstance(fact, Mapping) and isinstance(fact.get("fact"), Mapping):
            fact = dict(fact)
            envelope = dict(fact["fact"])
            envelope.pop("work_statement", None)
            fact["fact"] = envelope
        new_facts.append(fact)
    claim["facts"] = new_facts
    _rewrite_json(path, claim)


# ---------------------------------------------------------------------------
# per-axis sibling FIRE probes (each proves dropping ONE axis-evidence -> FAIL)
# ---------------------------------------------------------------------------
def _degraded_copy_probe(
    source: Path,
    *,
    probe_ref: str,
    degrade: "callable",
    catch: "callable",
) -> Mapping[str, Any]:
    """Generic sibling probe: copy the generated root, apply ONE degradation, assert FAIL.

    Copies the GENERATED Tier-A root into a temp dir, applies ``degrade`` (which
    drops exactly one axis-evidence), runs the full conformance harness over the
    copy, and requires that the harness reports it unmet AND that the unmet set
    contains the specific ``catch`` violation. The ``catch`` predicate makes the
    probe anti-tautological: it is satisfied only by the violation the dropped
    evidence is supposed to raise, not by any incidental unmet message.
    """

    if not source.is_dir():
        return {
            "probe_ref": probe_ref,
            "fired": False,
            "reason": "tier-a generated building root not present to derive a FIRE probe from",
        }
    with tempfile.TemporaryDirectory(prefix="bp-tier-a-fire-") as tmp:
        degraded = Path(tmp) / "buildings" / (TIER_A_BUILDING_ID + "-degraded")
        shutil.copytree(source, degraded)
        degrade(degraded)
        unmet = assert_building_conformance(degraded, label="tier-a-degraded-probe")
        caught = any(catch(violation) for violation in unmet)
    return {
        "probe_ref": probe_ref,
        "fired": bool(unmet) and caught,
        "unmet_count": len(unmet),
        "unmet": unmet,
        "proof_limits": ["negative probe support evidence only"],
    }


def agent_fact_shape_probe(source: Path) -> Mapping[str, Any]:
    """FIRE (Agent): a non-closed AgentFact shape must be reported unmet."""

    return _degraded_copy_probe(
        source,
        probe_ref="tier-a-conformance-probe:agent_fact_shape_broken",
        degrade=_degrade_break_agent_fact_shape,
        catch=lambda violation: "closed 2-field agentfact" in violation.lower(),
    )


def carry_probe(source: Path) -> Mapping[str, Any]:
    """FIRE (Link): a missing present CarryFact must be reported unmet."""

    return _degraded_copy_probe(
        source,
        probe_ref="tier-a-conformance-probe:carry_dropped",
        degrade=_degrade_drop_present_carry,
        catch=lambda violation: "carryfact in carry_trace" in violation.lower(),
    )


def transfer_probe(source: Path) -> Mapping[str, Any]:
    """FIRE (Link): a missing present TransferFact must be reported unmet."""

    return _degraded_copy_probe(
        source,
        probe_ref="tier-a-conformance-probe:transfer_dropped",
        degrade=_degrade_drop_present_transfer,
        catch=lambda violation: "transferfact in transfer_trace" in violation.lower(),
    )


def sufficiency_probe(source: Path) -> Mapping[str, Any]:
    """FIRE (Link gate): an empty sufficiency_trace must be reported unmet."""

    return _degraded_copy_probe(
        source,
        probe_ref="tier-a-conformance-probe:sufficiency_dropped",
        degrade=_degrade_empty_sufficiency,
        catch=lambda violation: "sufficiency decision recorded in sufficiency_trace"
        in violation.lower(),
    )


def work_contract_probe(source: Path) -> Mapping[str, Any]:
    """FIRE (Brick): a missing work_statement must be reported unmet."""

    return _degraded_copy_probe(
        source,
        probe_ref="tier-a-conformance-probe:work_statement_dropped",
        degrade=_degrade_drop_work_statement,
        catch=lambda violation: "work_statement" in violation.lower(),
    )


def budget_hold_probe(source: Path) -> Mapping[str, Any]:
    """FIRE (Link budget bound): an UN-evidenced budget HOLD must be reported unmet.

    The resume path regenerates the final evidence with the held proposal
    re-recorded as an adoption, so on a resumed root the HOLD is evidenced
    ONLY through the held-stage snapshot. Running the harness over the final
    root WITHOUT that snapshot must therefore report the budget bound unmet --
    proving the HOLD assertion still fires when the held-stage evidence is
    dropped (the harness has not stopped asserting the bound).
    """

    return _degraded_copy_probe(
        source,
        probe_ref="tier-a-conformance-probe:budget_hold_unevidenced",
        degrade=lambda degraded: None,
        catch=lambda violation: "budget-exhaustion hold" in violation.lower(),
    )


def negative_probe_observations(source: Path) -> tuple[Mapping[str, Any], ...]:
    """All anti-tautological FIRE probes (the original combined probe + 5 siblings).

    Each sibling drops exactly ONE axis-evidence and requires the harness to FAIL
    with that evidence's specific violation, so a harness that stops asserting any
    one axis-evidence drives ``--all`` RED.
    """

    return (
        fire_probe(source),
        work_contract_probe(source),
        agent_fact_shape_probe(source),
        carry_probe(source),
        transfer_probe(source),
        sufficiency_probe(source),
        budget_hold_probe(source),
    )


def run_negative_probe(source: Path) -> str:
    """Run every FIRE probe; return a reason if any did NOT fire (else empty)."""

    for observation in negative_probe_observations(source):
        if observation.get("fired") is not True:
            probe_ref = str(observation.get("probe_ref") or "tier-a conformance FIRE probe")
            reason = observation.get("reason")
            if reason:
                return f"{probe_ref}: {reason}"
            return f"{probe_ref} did not fire"
    return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Assert Tier-A 3-axis automation conformance over the engine-produced "
            "tier-a-3axis-conformance-0 Building. Support evidence only."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else Path(".").resolve()

    # CLEAN-YARD v3: generate the evidence with the REAL engine at check time
    # into a TEMP root, assert the SAME properties the standing-root era pinned,
    # and remove it (the TemporaryDirectory context is the ``finally``).
    with tempfile.TemporaryDirectory(prefix="bp-tier-a-case-") as tmp:
        try:
            generated_root, held_stage_root = generate_tier_a_case_root(
                repo, Path(tmp) / "buildings"
            )
        except Exception as exc:  # noqa: BLE001 -- engine generation failure is RED, never green
            print(
                "tier-a 3-axis conformance rejected: engine generation failed "
                f"({type(exc).__name__}: {exc})",
                file=sys.stderr,
            )
            print(PROOF_LIMIT, file=sys.stderr)
            return 1

        not_fired = run_negative_probe(generated_root)
        if not_fired:
            print(
                "tier-a 3-axis conformance rejected: anti-tautological FIRE probe did "
                f"not fire: {not_fired}",
                file=sys.stderr,
            )
            print(PROOF_LIMIT, file=sys.stderr)
            return 1

        try:
            unmet = check_generated_root(generated_root, held_stage_root)
        except OSError as exc:
            print(f"tier-a 3-axis conformance rejected: {exc}", file=sys.stderr)
            return 1

    if unmet:
        print("tier-a 3-axis conformance rejected:", file=sys.stderr)
        for violation in unmet:
            print(f"- {violation}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1

    print(
        "tier-a 3-axis conformance passed: FIRE probe fired; the engine-GENERATED "
        f"check-time {TIER_A_BUILDING_ID} root (temp, removed after) asserts Brick "
        "(launch chain + work contracts), "
        "Agent (closed AgentFact + performer + declared binding), Link (forward + "
        "adopted reroute + gate sufficiency + budget + pause/resume + carry/transfer), "
        "Evidence (claim_trace + raw + manifests + building-map, complete-run), and "
        "declaration_provenance."
    )
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

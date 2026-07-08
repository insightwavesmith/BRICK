#!/usr/bin/env python3
"""Rule-pinning checker for the graph-draft drafter (Building #15).

Drives ``draft_graph_declaration`` IN-PROCESS over fixed answer fixtures and
asserts the rule-source teeth ①~⑩ hold. This checker is support evidence only:
it is not source truth, success judgment, quality judgment, or Movement
authority. It NEVER writes files — drafts are composed in memory only
(``write_draft_declaration`` is not called), so there is no fixture home dispute
and no live-inbox write.

Probes:
  P1  rule ①②⑧  walker-adjacent+complex → fugu work + deep-design + 10800s
  P2  no over-escalation  simple-doc → codex work, no deep-design, no 10800
  P4  rule ④  every fan block is followed by a convergence node
  P3  rule ⑩  both fixture drafts return the COMPOSED OK literal
  P5  Rule 3  the drafter/CLI draft surfaces reach no launch seam (text scan)
  P6  rule ⑤  bare-directory write_scope entries normalize to explicit globs
  P7  RED-1  a width>3 partition draft is rejected
  P8  RED-2  intersecting-write-set branches are rejected
  P9  RED-3  deep-tier casting below 10800s is rejected
  P10 RED-4  a fan branch missing concern_key/objective is rejected
  P11 RED-5  a stage-2 draft missing done_line/residual_owner is rejected
  P12 RED-6  a mixed expansion budget mode is rejected
  P13 WARN-1 an xhigh burst surfaces a WARN-1 rationale row (composed_ok stays)
  P14 WARN-2 risky surface + low-tier work surfaces a WARN-2 advisory
  P15 net    a green §A2 partition draft still composes (rules do not over-reject)
  P16 seam   a RED partition draft rejects end-to-end (RED-REJECT-SEAM)
  P17 RED-4  a malformed (non-mapping) partition branch is rejected (fail-closed)
  P18 RED-4  a malformed (non-mapping) fan branch is rejected (fail-closed)
  P19 RED-2  a partition branch with no write_set fails closed (fail-open #1)
  P20 RED-6  a stage-2 draft with no/empty/malformed/non-positive budget fails closed (fail-open #2)
  P21 RED-3  a case-variant deep-tier model ref still trips the timeout gate (fail-open #3)
  P22 WARN-2 file_conflict==yes + low-tier work is reachable through the drafter (fail-open #4)
  P23 mark   a rejected draft is persisted with a draft_rejected marker (fail-open #5)
  P24 D2     splittable+deep answers draft a parallel design fan (width proposal)
  P25 D2     width_signals>3 clamps to exactly 3 branches (RULE-WIDTH-CEILING)
  P26 D2     splittable non-deep + disjoint scopes draft a work fan over the partitions
  P27 D1     a malformed width_signals value is rejected fail-closed (ValueError)
  P28 D2     width_signals=0 falls through to the single-work spine (note-split absorbed)
  P29 D2     an overlapping single-group scope collapses the work fan to width 1
  P30 D2     file_conflict==yes blocks the fan trigger (work 병렬화 금지)
  P31 0707pm the escalated QA fan casts code-attack-qa=opus-4-8, evidence-integrity=opus-4-8 (fable5 branch removed; §G1 승계)
  P32 G1     a non-escalated QA fan casts code-attack-qa=opus-4-8 (the else arm fires)
  P33 D1     source_facts propagate to every work-fan write lane (branches + merge)
  P34 D1     source_facts propagate to every design-fan branch
  P35 D2     ceiling-truncated partitions are recorded on a residual_owner row
  P36 D1     draft-diff shape-flip vs casting-flip are SEPARATE aggregates
  P37 D1     the flip ledger is append-only-by-one and the window reads it
  P38 D1     a full zero-flip window fires the operator-thought-stall canary; a
             sub-window sample does not; a flipped record suppresses it
  P39 D1     malformed draft-diff input raises (rc=1 surface); a valid pair does not
  P40 D2     a blind pre-registration is compared field-by-field with a forge proof-limit
  P41 D3     the drafted rationale carries the canonical answer_fingerprint line
  P42 D1     casting classification keys on the LEAF key only (ancestor-token
             collision — nodes[0].model.training_corpus — stays a shape flip)
  P43 D2     the flip ledger / blind pre-registration are repo-outside evidence;
             a repo-internal --ledger/--prereg-dir is refused (repo 안 산출 금지)
  P44 D1     the rolling flip-rate window is scoped to the current building_id;
             cross-building ledger records never mask or fire another building's canary
  P45 D1     a real leaf equal to the absent render sentinel still diffs as a
             real add/removal (sentinel-collision-zero-flip closed)
  P46 D1     a scalar type flip (int/bool/null -> str) is recorded, never
             absorbed by a bare-string diff (type-flip-invisible closed)
  P47 D1     a blank building_id window scopes to blank-id records only and
             never absorbs named-Building records (blank-id absorption closed)
  P48 D1     a non-positive rolling window falls back to the default window and
             never fires the canary at sample=1 (negative-window clamp closed)
  P49 D2     the repo-outside guard applies to the DEFAULT ledger/prereg path
             too; a BRICK_HOME resolving inside the repo is refused
  P50 0707pm the work promotion (deep-tier) candidate set is fugu-ultra only;
             re-adding fable5 is a variant-RED (fable5 봉쇄; §K work=opus/fugu)
  P51 0707pm no QA-fan casting lane carries fable5 (all claude QA = opus-4-8);
             re-introducing fable5 on any QA lens is a variant-RED (fable5 봉쇄)
  P52 0707pm a live draft normalizes a fable5 QA casting input back to opus-4-8
             and emits the normalization rationale row (normalized wiring pin)
  P53 0707pm the canonical QA branch casting source is opus-4-8 xhigh, not
             fable5; replacing the source arm with fable5 is a variant-RED
  P54 B       graph_draft's new tier/lens casting constants carry no provider
             literals; reintroducing adapter/model/provider names is RED
  P55 B       graph_draft's public draft nodes/branches carry tier/lens
             authoring keys, not legacy literal casting fields

P4 runs before P3 so mutation M3 (deleting the convergence emission) hits the
P4 literal first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]
_IMPORT_IDENTITY_ROOT = _REPO_ROOT / "support" / "import_identity"
for _path in (str(_REPO_ROOT), str(_IMPORT_IDENTITY_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from brick_protocol.support.operator.graph_draft import draft_graph_declaration
from brick_protocol.support.operator.graph_draft import (
    draft_rule_violations,
    write_draft_declaration,
    RED1_FAN_WIDTH,
    RED2_WRITE_SET_OVERLAP,
    RED3_DEEP_TIER_TIMEOUT,
    RED4_BRANCH_CONTRACT,
    RED5_STAGE2_FINISH,
    RED6_BUDGET_MODE,
    WARN1_XHIGH_BURST,
    WARN2_LOW_TIER_WORK,
)
from brick_protocol.support.operator.graph_draft import (
    answer_fingerprint,
    ANSWER_FINGERPRINT_PREFIX,
)
from brick_protocol.support.operator.graph_draft import DEEP_TIER_MODEL_REFS
from brick_protocol.support.operator.graph_draft import (
    CASTING_TIER_PLAN,
    CASTING_TIER_DEEP,
    CASTING_TIER_STANDARD,
    CASTING_TIER_LIGHT,
    CASTING_LENS_DESIGN,
    CASTING_LENS_WORK,
    CASTING_LENS_REVIEW,
    CASTING_LENS_CLOSURE,
)
from brick_protocol.support.operator import graph_draft as _graph_draft
from brick_protocol.support.operator import draft_diff as _draft_diff

PROOF_LIMIT = "support evidence only; not source truth / success / quality / Movement"

# --- fixtures -------------------------------------------------------------
WALKER_COMPLEX_ANSWERS: Mapping[str, str] = {
    "walker_adjacent": "yes",
    "size": "medium",
    "splittable": "no",
    "file_conflict": "no",
    "failure_cost": "high",
    "human_approval": "no",
    "termination_shape": "checker-pinned",
    "difficulty": "complex",
}
SIMPLE_DOC_ANSWERS: Mapping[str, str] = {
    "walker_adjacent": "no",
    "size": "small",
    "splittable": "no",
    "file_conflict": "no",
    "failure_cost": "low",
    "human_approval": "no",
    "termination_shape": "doc",
    "difficulty": "simple",
}
HARD_TASK = "walker 인접 엔진 작업 — 심층 구현."
SIMPLE_TASK = "간단한 문서 한 줄 정리."

# A green §A2 partition_plan: width 2, disjoint write_sets, full keys, per-node
# budgets keyed by branch_id. P15 asserts the rule table does NOT reject it.
PARTITION_OK: Mapping[str, Any] = {
    "width_decision": {
        "n": 2,
        "rationale_signals": ["s1", "s2"],
        "partition_count": 2,
        "kappa_proxy": {"overlapping_write_pairs": 0, "shared_contract_files": []},
    },
    "branches": [
        {
            "branch_id": "b1",
            "concern_key": "ops",
            "objective": "o1",
            "output_format": "json",
            "write_set": {"allowed": ["brick_protocol/support/operator/**"], "forbidden": [".git/**"]},
            "returns_field": "observed_evidence",
            "sibling_independent": True,
            "casting": {"adapter": "codex-local", "model": "", "effort": "", "timeout_seconds": 3600},
        },
        {
            "branch_id": "b2",
            "concern_key": "checks",
            "objective": "o2",
            "output_format": "json",
            "write_set": {"allowed": ["brick_protocol/support/checkers/**"], "forbidden": [".git/**"]},
            "returns_field": "observed_evidence",
            "sibling_independent": True,
            "casting": {"adapter": "codex-local", "model": "", "effort": "", "timeout_seconds": 3600},
        },
    ],
    "done_line": "체커 rc=0",
    "residual_owner": "coo",
    "qa_plan": {"lenses": ["code-attack-qa"], "second_verdict_path": "hold", "max_concurrent_xhigh": 2, "stagger": True},
    "env_plan": {"preflight_probe": True, "provider_risk": "none"},
    "expansion": {"attach_to_step_ref": "step:work", "budget_mode": "per-node", "budgets": {"b1": 1, "b2": 1}},
}


def _mutated(base: Mapping[str, Any], **overrides: Any) -> dict[str, Any]:
    """Shallow deep-ish copy of a partition_plan with top-level overrides."""
    import copy

    clone = copy.deepcopy(dict(base))
    clone.update(copy.deepcopy(overrides))
    return clone


def _budget_plan(budgets: Any) -> dict[str, Any]:
    """A PARTITION_OK clone whose per-node expansion carries the given budgets."""
    plan = _mutated(PARTITION_OK)
    plan["expansion"] = {
        "attach_to_step_ref": "step:work",
        "budget_mode": "per-node",
        "budgets": budgets,
    }
    return plan


# Fail-open #4: file_conflict==yes is a genuine entanglement signal that does NOT
# force escalation, so the drafted work node stays codex-local (low-tier) on a
# risky surface — the exact 얽힘+저티어 case WARN-2 exists to surface.
WARN2_REACHABLE_ANSWERS: Mapping[str, str] = {
    "walker_adjacent": "no",
    "size": "medium",
    "splittable": "no",
    "file_conflict": "yes",
    "failure_cost": "low",
    "human_approval": "no",
    "termination_shape": "doc",
    "difficulty": "medium",
}

# D2 width-proposal fixtures. SPLIT_DEEP is a §E mirror (splittable large entangled
# → deep tier → a parallel DESIGN fan). SPLIT_WORK is a non-deep splittable task
# → a parallel WORK fan over disjoint write scopes. width_signals is the optional
# 9th key (never a member of the required-8 contract).
SPLIT_DEEP_ANSWERS: Mapping[str, Any] = {
    **WALKER_COMPLEX_ANSWERS,
    "size": "large",
    "splittable": "yes",
    "termination_shape": "doc",
    "difficulty": "entangled",
    "width_signals": 3,
}
SPLIT_WORK_ANSWERS: Mapping[str, Any] = {
    "walker_adjacent": "no",
    "size": "medium",
    "splittable": "yes",
    "file_conflict": "no",
    "failure_cost": "low",
    "human_approval": "no",
    "termination_shape": "checker-pinned",
    "difficulty": "medium",
    "width_signals": 2,
}

# P32 fixture — a NON-escalated QA fan: walker_adjacent no, failure_cost low, no
# contract vocab, medium difficulty → the standard QA casting arm. (The
# escalated WALKER_COMPLEX fixture exercises the same active Opus QA target.)
NONESC_QA_ANSWERS: Mapping[str, str] = {
    "walker_adjacent": "no",
    "size": "medium",
    "splittable": "no",
    "file_conflict": "no",
    "failure_cost": "low",
    "human_approval": "no",
    "termination_shape": "doc",
    "difficulty": "medium",
}

# P33/P34 — a real repo-tracked file used as a source_fact probe (rule ⑥ verifies
# test -f + git ls-files, so it must exist and be tracked).
_SOURCE_FACT_PROBE = "brick_protocol/support/operator/graph_draft.py"

# Rule 3 launch-seam tokens that must NOT appear in the draft surfaces.
_LAUNCH_SEAM_TOKENS = (
    "run_customer_building_in_sandbox",
    "run_goal_approve_entry",
    "operator.driver",
    "operator import driver",
    "fire(",
    '"action": "forward"',
    "'action': 'forward'",
)


def _nodes(result: Any) -> list[Mapping[str, Any]]:
    return list(result.declaration["nodes"])


def _first_kind(nodes: Sequence[Mapping[str, Any]], kind: str) -> Mapping[str, Any] | None:
    for node in nodes:
        if node.get("kind") == kind:
            return node
    return None


def _has_kind(nodes: Sequence[Mapping[str, Any]], kind: str) -> bool:
    return _first_kind(nodes, kind) is not None


def _is_convergence(node: Mapping[str, Any]) -> bool:
    return "fan" not in node and node.get("kind") in {
        "closure",
        "work",
        "review",
        "inspect",
    }


def _violations(repo: Path) -> list[str]:
    out: list[str] = []
    hard = draft_graph_declaration(
        HARD_TASK,
        WALKER_COMPLEX_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
    )
    simple = draft_graph_declaration(
        SIMPLE_TASK,
        SIMPLE_DOC_ANSWERS,
        repo_root=repo,
        allowed_paths=("brick_protocol/support/operator/**",),
    )
    hard_nodes = _nodes(hard)
    simple_nodes = _nodes(simple)

    # P1 — rule ①②⑧: walker-adjacent+complex → fugu work + deep-design + 10800s.
    hard_work = _first_kind(hard_nodes, "work")
    if (
        hard_work is None
        or hard_work.get("casting_tier_ref") != CASTING_TIER_DEEP
        or hard_work.get("casting_lens_ref") != CASTING_LENS_WORK
        or not _has_kind(hard_nodes, "deep-design")
        or hard.declaration.get("adapter_timeout_seconds") != 10800
    ):
        out.append(
            "graph-draft RED: walker-adjacent answers drafted a codex-solo work node (rule 1/2/8 violated)"
        )

    # P6 — rule ⑤: bare directory write_scope entries normalize to explicit globs.
    if hard_work is None or hard_work.get("write_scope", {}).get("allowed_paths") != ["brick_protocol/support/**"]:
        out.append(
            "graph-draft RED: bare-directory write_scope was not normalized to an explicit glob"
        )

    # P2 — no over-escalation: simple-doc → codex work, no deep-design, no 10800.
    simple_work = _first_kind(simple_nodes, "work")
    if (
        simple_work is None
        or simple_work.get("casting_tier_ref") != CASTING_TIER_STANDARD
        or simple_work.get("casting_lens_ref") != CASTING_LENS_WORK
        or _has_kind(simple_nodes, "deep-design")
        or simple.declaration.get("adapter_timeout_seconds") == 10800
    ):
        out.append(
            "graph-draft RED: simple-doc answers escalated casting without a declared risk basis"
        )

    # P4 — rule ④: every fan block is followed by exactly one convergence node.
    # (Runs before P3 so mutation M3 hits this literal first.)
    # --- §A3 draft-time rule table probes (P7-P15) -----------------------
    # A minimal spine declaration to feed draft_rule_violations directly.
    def _decl(nodes: list[Mapping[str, Any]], **top: Any) -> dict[str, Any]:
        base: dict[str, Any] = {"building_id": "bid", "nodes": list(nodes)}
        base.update(top)
        return base

    # P7 — RED-1: a partition width>3 must be rejected.
    wide = _mutated(
        PARTITION_OK,
        width_decision={**PARTITION_OK["width_decision"], "n": 4},
    )
    reds, _ = draft_rule_violations(_decl([]), partition_plan=wide)
    if RED1_FAN_WIDTH not in reds:
        out.append("graph-draft RED: width>3 partition draft was not rejected (RED-1)")

    # P8 — RED-2: intersecting branch write-sets must be rejected.
    overlap = _mutated(PARTITION_OK)
    overlap["branches"][1]["write_set"]["allowed"] = ["brick_protocol/support/operator/**"]
    reds, _ = draft_rule_violations(_decl([]), partition_plan=overlap)
    if RED2_WRITE_SET_OVERLAP not in reds:
        out.append(
            "graph-draft RED: intersecting write-set partition draft was not rejected (RED-2)"
        )

    # P9 — RED-3: deep-tier casting below 10800s must be rejected.
    deep_decl = _decl(
        [{"kind": "work", "casting_tier_ref": CASTING_TIER_DEEP}],
        adapter_timeout_seconds=3600,
    )
    reds, _ = draft_rule_violations(deep_decl)
    if RED3_DEEP_TIER_TIMEOUT not in reds:
        out.append(
            "graph-draft RED: deep-tier casting below 10800s was not rejected (RED-3)"
        )
    branch_low_timeout = _decl(
        [
            {
                "fan": {
                    "branches": [
                        {
                            "kind": "design",
                            "concern_key": "deep",
                            "objective": "deep",
                            "casting_tier_ref": CASTING_TIER_DEEP,
                            "timeout_seconds": 3600,
                        }
                    ]
                }
            }
        ],
        adapter_timeout_seconds=10800,
    )
    reds, _ = draft_rule_violations(branch_low_timeout)
    if RED3_DEEP_TIER_TIMEOUT not in reds:
        out.append(
            "graph-draft RED: branch-local deep-tier timeout below 10800s was not rejected (RED-3)"
        )

    # P10 — RED-4: a fan branch without concern_key/objective must be rejected.
    no_contract = _mutated(PARTITION_OK)
    no_contract["branches"][0]["concern_key"] = ""
    reds, _ = draft_rule_violations(_decl([]), partition_plan=no_contract)
    if RED4_BRANCH_CONTRACT not in reds:
        out.append(
            "graph-draft RED: fan branch without concern_key/objective was not rejected (RED-4)"
        )

    # P17 — RED-4 fail-closed: a malformed (non-mapping) partition branch cannot
    # name the contract fields, so it must NOT be silently dropped — it counts as
    # a RED-4 violation. (Neutralizing the fail-closed guard makes this pass RED.)
    malformed_partition = _mutated(PARTITION_OK)
    malformed_partition["branches"] = ["not-a-mapping", PARTITION_OK["branches"][0]]
    reds, _ = draft_rule_violations(_decl([]), partition_plan=malformed_partition)
    if RED4_BRANCH_CONTRACT not in reds:
        out.append(
            "graph-draft RED: malformed (non-mapping) partition branch was not rejected (RED-4 fail-closed)"
        )

    # P18 — RED-4 fail-closed: a malformed (non-mapping) fan branch is likewise a
    # RED-4 violation rather than a silently dropped entry.
    malformed_fan = _decl(
        [{"fan": {"branches": ["bad", {"concern_key": "a", "objective": "b"}]}}]
    )
    reds, _ = draft_rule_violations(malformed_fan)
    if RED4_BRANCH_CONTRACT not in reds:
        out.append(
            "graph-draft RED: malformed (non-mapping) fan branch was not rejected (RED-4 fail-closed)"
        )

    # P11 — RED-5: a stage-2 draft missing done_line/residual_owner must be rejected.
    no_finish = _mutated(PARTITION_OK, done_line="")
    reds, _ = draft_rule_violations(_decl([]), partition_plan=no_finish)
    if RED5_STAGE2_FINISH not in reds:
        out.append(
            "graph-draft RED: stage-2 draft without done_line/residual_owner was not rejected (RED-5)"
        )

    # P12 — RED-6: a mixed expansion budget mode must be rejected.
    mixed = _mutated(PARTITION_OK)
    mixed["expansion"] = {
        "attach_to_step_ref": "step:work",
        "budget_mode": "per-node",
        "budgets": {"total": 2, "b1": 1},
    }
    reds, _ = draft_rule_violations(_decl([]), partition_plan=mixed)
    if RED6_BUDGET_MODE not in reds:
        out.append(
            "graph-draft RED: mixed expansion budget mode was not rejected (RED-6)"
        )

    # P13 — WARN-1: generated >2 xhigh fan siblings surface a WARN rationale row
    # without flipping composed_ok. This pins both the pure rule table and the
    # draft_graph_declaration WARN→rationale integration seam.
    burst = draft_graph_declaration(
        "gate 계약이 있는 walker 인접 엔진 작업 — 심층 구현.",
        WALKER_COMPLEX_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
    )
    warn_rows = [row for row in burst.rationale_rows if row.get("decision") == WARN1_XHIGH_BURST]
    if not burst.precheck.get("composed_ok") or not warn_rows:
        out.append(
            "graph-draft RED: xhigh burst did not surface a WARN-1 rationale row (or flipped RED)"
        )

    # P14 — WARN-2: risky answers + low-tier work surface a WARN-2 advisory.
    low_tier_risky = _decl(
        [{"kind": "work", "adapter_ref": "adapter:codex-local"}],
        adapter_timeout_seconds=10800,
    )
    reds, warns = draft_rule_violations(
        low_tier_risky,
        answers={"walker_adjacent": "yes", "difficulty": "complex"},
    )
    if WARN2_LOW_TIER_WORK not in warns or reds:
        out.append(
            "graph-draft RED: low-tier work on risky surface did not surface a WARN-2 advisory (or flipped RED)"
        )

    # P15 — net: a green §A2 partition draft still composes (rules do not over-reject).
    green = draft_graph_declaration(
        HARD_TASK,
        WALKER_COMPLEX_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
        partition_plan=PARTITION_OK,
    )
    if not str(green.precheck.get("literal", "")).startswith("COMPOSED OK"):
        out.append(
            "graph-draft RED: valid partition draft failed to compose (partition rules over-reject)"
        )

    # P16 — RED-REJECT-SEAM: a RED partition_plan driven through the FULL
    # draft_graph_declaration pipeline must reject end-to-end (composed_ok False,
    # empty literal, RED literal carried in reject_evidence). P7-P12 pin the pure
    # rule table; this pins the integration seam that maps RED literals onto the
    # precheck reject dict — neutralizing that seam (assembling anyway) survives
    # every rule-table probe but must be caught here.
    import copy as _copy

    red_partition = _copy.deepcopy(dict(PARTITION_OK))
    red_partition["done_line"] = ""  # triggers RED-5 inside the rule table
    rejected = draft_graph_declaration(
        HARD_TASK,
        WALKER_COMPLEX_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
        partition_plan=red_partition,
    )
    reject_evidence = str(rejected.precheck.get("reject_evidence", ""))
    if (
        rejected.precheck.get("composed_ok") is not False
        or str(rejected.precheck.get("literal", "")) != ""
        or RED5_STAGE2_FINISH not in reject_evidence
    ):
        out.append(
            "graph-draft RED: RED partition draft was not rejected end-to-end (RED-REJECT-SEAM)"
        )

    # P19 — RED-2 fail-closed (fail-open #1): a §A2 partition branch that declares
    # NO write_set cannot be proven disjoint, so it must fail closed to RED-2.
    no_write_set = _mutated(PARTITION_OK)
    del no_write_set["branches"][0]["write_set"]
    reds, _ = draft_rule_violations(_decl([]), partition_plan=no_write_set)
    if RED2_WRITE_SET_OVERLAP not in reds:
        out.append(
            "graph-draft RED: partition branch without a write_set was not rejected (RED-2 fail-closed)"
        )
    # A drafted read-only QA fan branch legitimately carries NO write_set — it must
    # stay green (the presence rule is partition-scoped, not fan-scoped).
    readonly_fan = _decl(
        [{"fan": {"branches": [{"concern_key": "a", "objective": "b"}]}}]
    )
    reds, _ = draft_rule_violations(readonly_fan)
    if RED2_WRITE_SET_OVERLAP in reds:
        out.append(
            "graph-draft RED: read-only fan branch was wrongly rejected for missing write_set (RED-2 over-reject)"
        )

    # P20 — RED-6 fail-closed (fail-open #2): a stage-2 draft whose expansion is
    # missing / empty-budgeted / malformed-budget / non-positive fails closed.
    _missing_exp = _mutated(PARTITION_OK)
    del _missing_exp["expansion"]
    for label, plan in (
        ("missing-expansion", _missing_exp),
        ("empty-budgets", _budget_plan({})),
        ("nonmapping-budgets", _budget_plan([1, 2])),
        ("nonpositive-budget", _budget_plan({"b1": 0, "b2": -3})),
    ):
        reds, _ = draft_rule_violations(_decl([]), partition_plan=plan)
        if RED6_BUDGET_MODE not in reds:
            out.append(
                f"graph-draft RED: {label} stage-2 draft was not rejected (RED-6 fail-closed)"
            )

    # P21 — RED-3 fail-closed (fail-open #3): a case-variant deep-tier model ref
    # still trips the ≥10800s timeout gate (case normalization).
    case_variant = _decl(
        [{"kind": "work", "model_ref": "model:sakana:FUGU-ULTRA"}],
        adapter_timeout_seconds=3600,
    )
    reds, _ = draft_rule_violations(case_variant)
    if RED3_DEEP_TIER_TIMEOUT not in reds:
        out.append(
            "graph-draft RED: case-variant deep-tier model bypassed the timeout gate (RED-3 fail-closed)"
        )

    # P22 — WARN-2 reachability (fail-open #4): file_conflict==yes leaves a
    # codex-local work node on a risky surface; the drafter must surface WARN-2.
    warn2 = draft_graph_declaration(
        "간단한 한 줄 정리 작업.",
        WARN2_REACHABLE_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
    )
    warn2_rows = [row for row in warn2.rationale_rows if row.get("decision") == WARN2_LOW_TIER_WORK]
    if not warn2.precheck.get("composed_ok") or not warn2_rows:
        out.append(
            "graph-draft RED: file_conflict low-tier work did not surface a WARN-2 rationale row (or flipped RED)"
        )

    # P23 — persisted marker (fail-open #5): a rejected draft written to disk must
    # carry the passive draft_rejected marker; a green draft must NOT.
    import json as _json
    import tempfile as _tempfile

    red_persist = _mutated(PARTITION_OK, done_line="")  # RED-5
    with _tempfile.TemporaryDirectory() as _tmp:
        rej_result = draft_graph_declaration(
            HARD_TASK,
            WALKER_COMPLEX_ANSWERS,
            repo_root=repo,
            allowed_paths=("support",),
            partition_plan=red_persist,
        )
        rej_path = write_draft_declaration(rej_result, Path(_tmp) / "rej-decl.json")
        rej_doc = _json.loads(rej_path.read_text(encoding="utf-8"))
        rej_marker = rej_doc.get("draft_rejected")
        if not isinstance(rej_marker, Mapping) or RED5_STAGE2_FINISH not in str(
            rej_marker.get("reject_evidence", "")
        ):
            out.append(
                "graph-draft RED: rejected draft was persisted without a draft_rejected marker (fail-open #5)"
            )
        green_result = draft_graph_declaration(
            HARD_TASK,
            WALKER_COMPLEX_ANSWERS,
            repo_root=repo,
            allowed_paths=("support",),
            partition_plan=PARTITION_OK,
        )
        green_path = write_draft_declaration(green_result, Path(_tmp) / "green-decl.json")
        green_doc = _json.loads(green_path.read_text(encoding="utf-8"))
        if "draft_rejected" in green_doc:
            out.append(
                "graph-draft RED: green draft was wrongly stamped with a draft_rejected marker (fail-open #5 over-mark)"
            )

    # --- D2 width-proposal probes (P24-P31) ------------------------------
    # P24 — design fan: splittable+deep answers draft [fan(design×3 ladder)]→closure
    # at 10800s, COMPOSED OK, a width-decision row present, and NO surviving
    # note-split-candidate detect row (absorption).
    split_deep = draft_graph_declaration(
        "분할 가능 심층 표본", SPLIT_DEEP_ANSWERS, repo_root=repo, allowed_paths=("support",)
    )
    sd_nodes = _nodes(split_deep)
    fan0 = sd_nodes[0].get("fan", {}).get("branches", []) if sd_nodes and "fan" in sd_nodes[0] else []
    if (
        len(sd_nodes) != 2
        or len(fan0) != 3
        or [b.get("casting_tier_ref") for b in fan0]
        != [CASTING_TIER_PLAN, CASTING_TIER_DEEP, CASTING_TIER_STANDARD]
        or [b.get("casting_lens_ref") for b in fan0]
        != [CASTING_LENS_DESIGN, CASTING_LENS_DESIGN, CASTING_LENS_DESIGN]
        or any(b.get("kind") != "design" or not str(b.get("concern_key") or "").strip() for b in fan0)
        or sd_nodes[1].get("kind") != "closure"
        or sd_nodes[1].get("casting_lens_ref") != CASTING_LENS_CLOSURE
        or split_deep.declaration.get("adapter_timeout_seconds") != 10800
        or not str(split_deep.precheck.get("literal", "")).startswith("COMPOSED OK")
    ):
        out.append(
            "graph-draft RED: splittable deep answers did not draft a parallel design fan (width proposal absent)"
        )
    sd_row_ids = [r.get("rule_id") for r in split_deep.rationale_rows]
    if "rule-width-decision" not in sd_row_ids:
        out.append(
            "graph-draft RED: width decision rationale row absent for a splittable draft"
        )
    if "note-split-candidate" in sd_row_ids:
        out.append(
            "graph-draft RED: note-split-candidate row survived absorption (detect-only path not removed)"
        )

    # P25 — ceiling: width_signals=5 over FOUR disjoint work scopes must clamp to
    # exactly 3 work branches (RULE-WIDTH-CEILING). A work fan exercises the min
    # ceiling (the design ladder is naturally length-capped at 3, so it could not
    # prove the clamp). Removing the min-clamp emits 4 branches (probe RED) AND
    # trips RED-1 → composed_ok False — either path is caught here.
    wide_work = draft_graph_declaration(
        "분할 가능 표본",
        {**SPLIT_WORK_ANSWERS, "width_signals": 5},
        repo_root=repo,
        allowed_paths=("brick_protocol/support/operator/**", "brick_protocol/support/checkers/**", "brick_protocol/brick/**", "brick_protocol/link/**"),
    )
    ww_nodes = _nodes(wide_work)
    ww_fan = ww_nodes[0].get("fan", {}).get("branches", []) if ww_nodes and "fan" in ww_nodes[0] else []
    if len(ww_fan) != 3 or not str(wide_work.precheck.get("literal", "")).startswith("COMPOSED OK"):
        out.append(
            "graph-draft RED: drafted fan width exceeded the ceiling of 3 (min ceiling absent)"
        )

    # P26 — work fan: a non-deep splittable draft over two disjoint write scopes
    # drafts [fan(work×2 with disjoint write_scope), work(merge convergence),
    # fan(standard attack-QA), closure] and composes. D2①: a width-fan does NOT
    # downgrade QA to a single gemini review — the standard attack-QA fan
    # (code-attack-qa + evidence-integrity) is retained after the merge.
    split_work = draft_graph_declaration(
        "분할 가능 표본",
        SPLIT_WORK_ANSWERS,
        repo_root=repo,
        allowed_paths=("brick_protocol/support/operator/**", "brick_protocol/support/checkers/**"),
    )
    sw_nodes = _nodes(split_work)
    sw_fan = sw_nodes[0].get("fan", {}).get("branches", []) if sw_nodes and "fan" in sw_nodes[0] else []
    sw_allowed = sorted(
        tuple(b.get("write_scope", {}).get("allowed_paths", ())) for b in sw_fan
    )
    sw_qa_fan = (
        sw_nodes[2].get("fan", {}).get("branches", [])
        if len(sw_nodes) > 2 and "fan" in sw_nodes[2]
        else []
    )
    sw_qa_kinds = {b.get("kind") for b in sw_qa_fan}
    if (
        len(sw_nodes) != 4
        or len(sw_fan) != 2
        or any(b.get("kind") != "work" for b in sw_fan)
        or sw_nodes[1].get("kind") != "work"
        or {"code-attack-qa", "evidence-integrity"} - sw_qa_kinds
        or sw_nodes[3].get("kind") != "closure"
        or sw_allowed != [("brick_protocol/support/checkers/**",), ("brick_protocol/support/operator/**",)]
        or not str(split_work.precheck.get("literal", "")).startswith("COMPOSED OK")
    ):
        out.append(
            "graph-draft RED: splittable non-deep answers with disjoint scopes did not draft a work fan"
        )

    # P26b D2① — the work-fan QA lens must NOT be degraded to a single gemini
    # review node: no top-level review(gemini) node may replace the attack-QA fan
    # on a width-fan draft (the exact 1st-pass QA observation: 폭-팬이 QA 팬을
    # gemini 단일 review로 강등).
    if any(
        "fan" not in n
        and n.get("kind") == "review"
        and n.get("casting_tier_ref") == CASTING_TIER_LIGHT
        and n.get("casting_lens_ref") == CASTING_LENS_REVIEW
        for n in sw_nodes
    ):
        out.append(
            "graph-draft RED: work-fan QA was downgraded to a single gemini review (QA fan retention absent)"
        )

    # P27 — fail-closed: a malformed width_signals value is rejected with
    # ValueError before any shaping (bool/negative/non-digit text all rejected).
    for bad in ("lots", -1, True):
        try:
            draft_graph_declaration(
                "분할 가능 표본",
                {**SPLIT_WORK_ANSWERS, "width_signals": bad},
                repo_root=repo,
                allowed_paths=("support",),
            )
            out.append(
                "graph-draft RED: malformed width_signals was not rejected fail-closed"
            )
            break
        except ValueError:
            pass

    # P28 — absorption: width_signals=0 (safe default) on a splittable deep draft
    # falls through to the single-work spine, still emits the width-decision row at
    # N=1, and carries NO note-split-candidate row.
    absorb = draft_graph_declaration(
        "분할 가능 심층 표본",
        {**SPLIT_DEEP_ANSWERS, "width_signals": 0},
        repo_root=repo,
        allowed_paths=("support",),
    )
    ab_nodes = _nodes(absorb)
    ab_rows = [r.get("rule_id") for r in absorb.rationale_rows]
    ab_partition_fan = any(
        "fan" in n
        and any(b.get("kind") in {"design", "work"} for b in n.get("fan", {}).get("branches", []))
        for n in ab_nodes
    )
    if (
        not _has_kind(ab_nodes, "work")
        or ab_partition_fan
        or "rule-width-decision" not in ab_rows
        or "note-split-candidate" in ab_rows
    ):
        out.append(
            "graph-draft RED: note-split-candidate row survived absorption (detect-only path not removed)"
        )

    # P29 — collapse: a splittable draft whose whole write scope is one overlapping
    # group (partition_count==1) collapses to width 1 — no fan.
    collapse = draft_graph_declaration(
        "분할 가능 표본",
        SPLIT_WORK_ANSWERS,
        repo_root=repo,
        allowed_paths=("brick_protocol/support/**",),
    )
    if any(
        "fan" in n
        and any(b.get("kind") in {"design", "work"} for b in n.get("fan", {}).get("branches", []))
        for n in _nodes(collapse)
    ):
        out.append(
            "graph-draft RED: work fan without disjoint scope partitions was not collapsed to width 1"
        )

    # P30 — file_conflict: file_conflict==yes ("work 병렬화 금지") blocks the fan
    # trigger even on a splittable deep draft.
    fileconflict = draft_graph_declaration(
        "분할 가능 심층 표본",
        {**SPLIT_DEEP_ANSWERS, "file_conflict": "yes"},
        repo_root=repo,
        allowed_paths=("support",),
    )
    fc_nodes = _nodes(fileconflict)
    if any(
        "fan" in n
        and any(b.get("kind") in {"design", "work"} for b in n.get("fan", {}).get("branches", []))
        for n in fc_nodes
    ):
        out.append(
            "graph-draft RED: file_conflict answers drafted a parallel fan (work 병렬화 금지)"
        )

    # P31 — casting rider (Smith 0707 오후 판정): in the ESCALATED QA fan the
    # code-attack-qa lens is now opus-4-8 (엔진급 fable5 분기 폐지) and evidence-
    # integrity is opus-4-8 too — claude-측 QA 전부 opus-4.8 xhigh (§G1 두-티어 승계·
    # §K 정합). Re-introducing fable5 on the code-attack-qa lens flips this probe RED.
    g1 = draft_graph_declaration(
        "walker 인접 엔진 작업 — 심층 구현.",
        WALKER_COMPLEX_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
    )
    g1_fan: list[Mapping[str, Any]] = []
    for node in _nodes(g1):
        if "fan" in node:
            g1_fan = list(node.get("fan", {}).get("branches", []))
            break
    g1_by_kind = {b.get("kind"): b for b in g1_fan}
    code_qa = g1_by_kind.get("code-attack-qa")
    ei = g1_by_kind.get("evidence-integrity")
    if (
        code_qa is None
        or code_qa.get("casting_tier_ref") != CASTING_TIER_STANDARD
        or code_qa.get("casting_lens_ref") != "casting-lens:code-attack"
        or ei is None
        or ei.get("casting_tier_ref") != CASTING_TIER_STANDARD
        or ei.get("casting_lens_ref") != "casting-lens:evidence-integrity"
    ):
        # NOTE: literal string kept verbatim — the graph_draft.yaml profile
        # text_contains rule (line 104, outside this Brick's write_scope) pins it.
        # Smith 0707 오후 판정 now makes BOTH the escalated and non-escalated QA
        # lenses opus-4-8 (the pinned literal wording is retained for the profile).
        out.append(
            "graph-draft RED: non-escalated QA lens casting is not opus-4-8 tier (G1)"
        )

    # P32 — G1 non-escalated arm live-fire: a NON-escalated QA fan casts the
    # code-attack-qa lens as opus-4-8. WALKER_COMPLEX is escalated; this fixture
    # keeps the ordinary medium QA path pinned to the same active Opus target.
    nonesc = draft_graph_declaration(
        "간단 정리 작업 — 표준 medium.",
        NONESC_QA_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
    )
    nonesc_fan: list[Mapping[str, Any]] = []
    for node in _nodes(nonesc):
        if "fan" in node:
            nonesc_fan = list(node.get("fan", {}).get("branches", []))
            break
    nonesc_by_kind = {b.get("kind"): b for b in nonesc_fan}
    ne_code_qa = nonesc_by_kind.get("code-attack-qa")
    ne_ei = nonesc_by_kind.get("evidence-integrity")
    if (
        ne_code_qa is None
        or ne_code_qa.get("casting_tier_ref") != CASTING_TIER_STANDARD
        or ne_code_qa.get("casting_lens_ref") != "casting-lens:code-attack"
        or ne_ei is None
        or ne_ei.get("casting_tier_ref") != CASTING_TIER_STANDARD
        or ne_ei.get("casting_lens_ref") != "casting-lens:evidence-integrity"
    ):
        out.append(
            "graph-draft RED: non-escalated code-attack-qa arm did not fire opus-4-8 casting (G1 else arm)"
        )

    # P33 — D1 source_facts 전파: a width-fan draft carrying verified source_facts
    # must attach them to EVERY fan branch (work-partition branches AND the
    # retained attack-QA branches) plus the merge convergence work node, never
    # just the first. Reverting to a first-petal-only attach (the mutation) drops
    # sibling branches and this probe fires (1st-pass QA obs: work-fan source_facts
    # drop).
    sf_work = draft_graph_declaration(
        "분할 가능 표본",
        SPLIT_WORK_ANSWERS,
        repo_root=repo,
        allowed_paths=("brick_protocol/support/operator/**", "brick_protocol/support/checkers/**"),
        source_facts=(_SOURCE_FACT_PROBE,),
    )
    sf_nodes = _nodes(sf_work)
    sf_fan = sf_nodes[0].get("fan", {}).get("branches", []) if sf_nodes and "fan" in sf_nodes[0] else []
    sf_work_petals = [b for b in sf_fan if b.get("kind") == "work"]
    sf_merge = sf_nodes[1] if len(sf_nodes) > 1 else {}
    sf_qa_fan = (
        sf_nodes[2].get("fan", {}).get("branches", [])
        if len(sf_nodes) > 2 and "fan" in sf_nodes[2]
        else []
    )
    if (
        len(sf_work_petals) != 2
        or any(b.get("source_facts") != [_SOURCE_FACT_PROBE] for b in sf_work_petals)
        or sf_merge.get("kind") != "work"
        or sf_merge.get("source_facts") != [_SOURCE_FACT_PROBE]
        or len(sf_qa_fan) < 2
        or any(b.get("source_facts") != [_SOURCE_FACT_PROBE] for b in sf_qa_fan)
    ):
        out.append(
            "graph-draft RED: verified source_facts were not propagated to every work-fan branch/merge lane (D1)"
        )

    # P34 — D1 design-fan 전파: a splittable-deep width-fan attaches the verified
    # source_facts to EVERY design branch (the design fan carries no top-level
    # work node — a first-petal-only attach would leave siblings starved).
    sf_deep = draft_graph_declaration(
        "분할 가능 심층 표본",
        SPLIT_DEEP_ANSWERS,
        repo_root=repo,
        allowed_paths=("support",),
        source_facts=(_SOURCE_FACT_PROBE,),
    )
    sf_deep_fan: list[Mapping[str, Any]] = []
    for node in _nodes(sf_deep):
        if "fan" in node:
            sf_deep_fan = list(node.get("fan", {}).get("branches", []))
            break
    sf_design_petals = [b for b in sf_deep_fan if b.get("kind") == "design"]
    if len(sf_design_petals) != 3 or any(
        b.get("source_facts") != [_SOURCE_FACT_PROBE] for b in sf_design_petals
    ):
        out.append(
            "graph-draft RED: verified source_facts were not propagated to every design-fan branch (D1)"
        )

    # P35 — D2② residual-partition record: when the width ceiling truncates the
    # disjoint partition set, the leftover partitions are recorded on a
    # rule-residual-partition row (owner named) rather than dropped silently.
    residual = draft_graph_declaration(
        "분할 가능 표본",
        {**SPLIT_WORK_ANSWERS, "width_signals": 5},
        repo_root=repo,
        allowed_paths=(
            "brick_protocol/support/operator/**",
            "brick_protocol/support/checkers/**",
            "brick_protocol/brick/**",
            "brick_protocol/link/**",
        ),
    )
    residual_rows = [r for r in residual.rationale_rows if r.get("rule_id") == "rule-residual-partition"]
    if not residual_rows or "residual_owner" not in str(residual_rows[0].get("decision", "")):
        out.append(
            "graph-draft RED: ceiling-truncated partitions were not recorded on a residual_owner row (D2②)"
        )

    # P50 — fable5 봉쇄 variant-RED ② (Smith 0707 오후 판정): the work 상위-두뇌 승격 후보 집합
    # (DEEP_TIER_MODEL_REFS) must be fugu-ultra 단독. Re-adding fable5 to that set
    # (the mutation) flips this probe RED — fable5 is a 기획-라인-only model, never
    # a work/QA promotion candidate.
    if "model:claude:claude-fable-5" in DEEP_TIER_MODEL_REFS:
        out.append(
            "graph-draft RED: fable5 re-added to the work promotion (deep-tier) candidate set (fable5 봉쇄)"
        )

    # P51 — fable5 봉쇄 variant-RED ① (Smith 0707 오후 판정): NO QA-fan casting lane may carry fable5.
    # Drive both an escalated and a non-escalated QA fan and assert no branch is
    # cast with fable5 (claude-측 QA 전부 opus-4-8 xhigh). Re-introducing fable5 on
    # any QA lens (the mutation) flips this probe RED.
    for _qa_answers, _qa_task in (
        (WALKER_COMPLEX_ANSWERS, "walker 인접 엔진 작업 — 심층 구현."),
        (NONESC_QA_ANSWERS, "간단 정리 작업 — 표준 medium."),
    ):
        _qa_draft = draft_graph_declaration(
            _qa_task, _qa_answers, repo_root=repo, allowed_paths=("support",)
        )
        _qa_fable5 = False
        for _node in _nodes(_qa_draft):
            if "fan" not in _node:
                continue
            for _branch in _node.get("fan", {}).get("branches", []):
                if (
                    str(_branch.get("casting_tier_ref") or "").strip() == CASTING_TIER_PLAN
                    or str(_branch.get("model_ref") or "").strip() == "model:claude:claude-fable-5"
                ):
                    _qa_fable5 = True
        if _qa_fable5:
            out.append(
                "graph-draft RED: fable5 re-introduced on a QA-fan casting lane (fable5 봉쇄)"
            )
            break

    # P52 — normalized wiring behavior pin: temporarily make the QA branch
    # casting source return fable5, then drive the public draft pipeline. The
    # emitted QA branches must be rewritten to opus-4-8 and the rationale must
    # explicitly record the normalization. This catches the exact NOT-RED
    # mutation from gate M7 (``normalized = _contain_fable5(branches)`` →
    # ``normalized = False``) because that mutation leaves the live output
    # carrying fable5 and drops the "재도입 → opus-4-8 정규화" row suffix.
    _original_qa_branch_casting = _graph_draft._qa_branch_casting
    try:
        _graph_draft._qa_branch_casting = lambda _kind: _graph_draft.PLAN_DESIGN
        normalized_probe = draft_graph_declaration(
            "QA fable5 재도입 정규화 프로브",
            NONESC_QA_ANSWERS,
            repo_root=repo,
            allowed_paths=("support",),
        )
    finally:
        _graph_draft._qa_branch_casting = _original_qa_branch_casting
    normalized_fan: list[Mapping[str, Any]] = []
    for _node in _nodes(normalized_probe):
        if "fan" in _node:
            normalized_fan = list(_node.get("fan", {}).get("branches", []))
            break
    if (
        len(normalized_fan) < 2
        or any(
            _branch.get("casting_tier_ref") != CASTING_TIER_STANDARD
            or str(_branch.get("casting_lens_ref") or "").strip() not in {
                "casting-lens:code-attack",
                "casting-lens:evidence-integrity",
                "casting-lens:axis-attack",
                "casting-lens:qa",
            }
            for _branch in normalized_fan
        )
    ):
        out.append(
            "graph-draft RED: fable5 QA casting input was not normalized to opus-4-8 xhigh in draft output (fable5 containment wiring)"
        )
    if not any(
        _row.get("rule_id") == "rule9-fable5-containment"
        and "plan-tier 재도입" in str(_row.get("decision", ""))
        and "standard tier 정규화" in str(_row.get("decision", ""))
        for _row in normalized_probe.rationale_rows
    ):
        out.append(
            "graph-draft RED: fable5 QA normalization did not emit the rule9 containment rationale row"
        )

    # P53 — canonical source behavior pin: the live QA-casting source itself
    # must be opus-4-8 xhigh. P52 proves fable5 input is normalized; this probe
    # separately prevents the source arm from being silently changed to fable5.
    for _kind in ("code-attack-qa", "evidence-integrity", "axis-attack-qa"):
        _casting = _graph_draft._qa_branch_casting(_kind)
        if (
            _casting.get("casting_tier_ref") != CASTING_TIER_STANDARD
            or str(_casting.get("casting_lens_ref") or "").strip()
            not in {
                "casting-lens:code-attack",
                "casting-lens:evidence-integrity",
                "casting-lens:axis-attack",
            }
        ):
            out.append(
                "graph-draft RED: canonical QA branch casting source is not opus-4-8 xhigh (fable5 source-arm reintroduction)"
            )
            break

    # P54 — B branch provider-neutrality pin: the emitted casting constants are
    # tier/lens authoring tokens only. Legacy provider/model literals are still
    # admitted in fallback scanners (DEEP_TIER_MODEL_REFS, old draft probes), but
    # they must not re-enter the NEW tier/lens casting constants.
    _provider_literal_needles = (
        "adapter:",
        "model:",
        "codex",
        "gemini",
        "fable",
        "fugu",
        "claude",
        "sakana",
    )
    for _name in (
        "PLAN_DESIGN",
        "FUGU",
        "FUGU_DESIGN",
        "CODEX",
        "CODEX_DESIGN",
        "CODEX_CLOSURE",
        "GEMINI_REVIEW",
        "OPUS48_QA",
    ):
        _row = getattr(_graph_draft, _name)
        if not isinstance(_row, Mapping):
            out.append(
                "graph-draft RED: tier/lens casting constants reintroduced provider literals (provider-neutral B branch)"
            )
            break
        _values = [str(v).strip().lower() for v in _row.values()]
        if any(any(_needle in _value for _needle in _provider_literal_needles) for _value in _values):
            out.append(
                "graph-draft RED: tier/lens casting constants reintroduced provider literals (provider-neutral B branch)"
            )
            break

    # P55 — output-shape companion: provider-neutral graph_draft declarations
    # must not leak legacy literal casting fields on emitted nodes/branches. The
    # precheck copy may resolve tiers in memory; the public draft declaration
    # remains tier/lens authoring evidence only.
    _legacy_casting_keys = {
        "adapter_ref",
        "model_ref",
        "reasoning_effort_ref",
        "selected_adapter_ref",
        "selected_model_ref",
        "selected_reasoning_effort_ref",
    }

    def _iter_mappings(_value: Any) -> list[Mapping[str, Any]]:
        if isinstance(_value, Mapping):
            _out = [_value]
            for _child in _value.values():
                _out.extend(_iter_mappings(_child))
            return _out
        if isinstance(_value, Sequence) and not isinstance(_value, (str, bytes, bytearray)):
            _out: list[Mapping[str, Any]] = []
            for _child in _value:
                _out.extend(_iter_mappings(_child))
            return _out
        return []

    for _draft in (
        hard,
        simple,
        split_deep,
        wide_work,
        split_work,
        g1,
        nonesc,
        sf_work,
        sf_deep,
        residual,
        normalized_probe,
    ):
        _nodes_doc = _draft.declaration.get("nodes", ())
        if any(_legacy_casting_keys & set(_mapping) for _mapping in _iter_mappings(_nodes_doc)):
            out.append(
                "graph-draft RED: emitted graph_draft nodes leaked literal provider casting keys (provider-neutral B branch)"
            )
            break

    for nodes in (hard_nodes, simple_nodes):
        for index, node in enumerate(nodes):
            if "fan" in node:
                following = nodes[index + 1] if index + 1 < len(nodes) else None
                if following is None or not _is_convergence(following):
                    out.append(
                        "graph-draft RED: fan block without following convergence node in draft"
                    )
                    break

    # P3 — rule ⑩: both fixture drafts return the COMPOSED OK literal.
    for res in (hard, simple):
        if not str(res.precheck.get("literal", "")).startswith("COMPOSED OK"):
            out.append(
                "graph-draft RED: draft precheck did not return the COMPOSED OK literal"
            )

    # P5 — Rule 3 structural absence: the draft surfaces reach no launch seam.
    surface_texts: list[str] = []
    module_src = (repo / "brick_protocol/support/operator/graph_draft.py").read_text(encoding="utf-8")
    surface_texts.append(module_src)
    cli_src = (repo / "brick_protocol/support/operator/cli.py").read_text(encoding="utf-8")
    draft_body = _extract_draft_bodies(cli_src)
    surface_texts.append(draft_body)
    reached_seam = False
    for text in surface_texts:
        for token in _LAUNCH_SEAM_TOKENS:
            if token in text:
                reached_seam = True
                break
        if reached_seam:
            break
    # The drafted declaration must carry no forward action.
    for res in (hard, simple):
        action = str(res.declaration.get("action", "")).strip().lower()
        if action == "forward":
            reached_seam = True
    if reached_seam:
        out.append("graph-draft RED: draft surface reaches a launch seam (Rule 3)")

    out.extend(_draft_diff_violations(repo))
    return out


def _extract_draft_bodies(cli_src: str) -> str:
    """Return only the draft-related CLI function bodies for the Rule 3 scan.

    The rest of cli.py legitimately imports the launch driver; we scan only the
    ``_run_draft`` / ``_cmd_draft`` / ``_render_draft`` (and the ``draft-diff``
    sibling) bodies so the check fires exactly when a launch seam is wired into
    the draft path.
    """

    lines = cli_src.splitlines()
    body: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("def "):
            capture = line.startswith(
                (
                    "def _run_draft",
                    "def _cmd_draft",
                    "def _render_draft",
                    "def _run_draft_diff",
                    "def _cmd_draft_diff",
                    "def _render_draft_diff",
                )
            )
        if capture:
            body.append(line)
    return "\n".join(body)


# CANARY-LITERAL-PIN — the exact advisory literal, hardcoded here so a drift of
# the module constant (graph_draft draft_diff.THOUGHT_STALL_CANARY) is caught by
# the emitted-line pin below rather than silently tracking the drifted constant.
_CANARY_LITERAL_PIN = "operator-thought-stall canary"


def _draft_diff_violations(repo: Path) -> list[str]:
    """D4 — draft-diff (shape/casting split + flip ledger + canary + D3 지문) probes.

    P36  D1  shape-flip vs casting-flip are SEPARATE aggregates (a casting-only
             change lands only in casting_flips; a shape-only change only in
             shape_flips) — the 분리집계 is load-bearing.
    P37  D1  the append-only flip ledger GROWS by exactly one line per run and
             the rolling window reads the appended record (append-only, no rewrite).
    P38  D1  a full window (N) of zero-flip records surfaces the exact
             ``operator-thought-stall canary`` literal; a sub-window sample does
             NOT (미실측 기본 태그) — variant-RED for a canary-literal drift.
    P39  D1  malformed input raises ValueError (rc=1 surface); a valid pair does
             not — the exit code is keyed only to input malformation.
    P40  D2  a present blind pre-registration is compared field-by-field and the
             prereg-first ordering is recorded with its forge proof-limit.
    P41  D3  the drafted rationale carries the canonical answer_fingerprint line
             (sha256 + UTC); removing it is a variant-RED.
    P42  D1  casting classification keys on the LEAF key only; a structural
             sub-field under a casting-named ancestor
             (nodes[0].model.training_corpus) stays a shape flip — an
             ancestor-token-collision regression flips this RED.
    P43  D2  the flip ledger and blind pre-registration are repo-outside
             (<brick_home>) evidence; a caller --ledger/--prereg-dir that
             resolves inside the repo tree is refused (repo 안 산출 금지).
    P44  D1  the rolling flip-rate window is scoped to the current building_id:
             a shared append-only ledger polluted with another Building's flipped
             records must not mask this Building's zero-flip canary, and a
             Building's own window must not absorb cross-building records.

    P45  D1  a real leaf whose value equals the absent render sentinel still
             diffs as a real add/removal (presence is decided by key membership,
             not by a sentinel default — sentinel-collision-zero-flip closed).
    P46  D1  a scalar type flip (int->str, bool->str, null->"") is recorded; a
             bare-string diff would be blind to it (type-flip-invisible closed).
    P47  D1  a blank building_id window scopes to blank-id records ONLY and never
             absorbs named-Building records (blank-id absorption closed).
    P48  D1  a non-positive rolling window falls back to the default window and
             never fires the canary at sample=1 (negative-window clamp closed).

    P49  D2  the repo-outside guard applies to the DEFAULT <brick_home>
             ledger/prereg path too (not only explicit --ledger/--prereg-dir);
             a BRICK_HOME resolving inside the repo tree is refused (repo 안
             산출 금지 default-path bypass closed).
    """
    import json as _json
    import tempfile as _tempfile

    out: list[str] = []
    dd = _draft_diff

    # Two minimal declarations that differ ONLY in casting (adapter_ref/model_ref).
    base_decl = {
        "building_id": "dd-bld",
        "task": "t",
        "nodes": [{"kind": "work", "adapter_ref": "adapter:codex-local"}],
    }
    casting_only = {
        "building_id": "dd-bld",
        "task": "t",
        "nodes": [{"kind": "work", "adapter_ref": "adapter:claude-local"}],
    }
    shape_only = {
        "building_id": "dd-bld",
        "task": "t-changed",
        "nodes": [{"kind": "work", "adapter_ref": "adapter:codex-local"}],
    }

    # P36 — separated aggregates.
    cast_diff = dd.diff_declarations(base_decl, casting_only)
    shape_diff = dd.diff_declarations(base_decl, shape_only)
    if (
        cast_diff["casting_flip_count"] < 1
        or cast_diff["shape_flip_count"] != 0
        or shape_diff["shape_flip_count"] < 1
        or shape_diff["casting_flip_count"] != 0
    ):
        out.append(
            "graph-draft RED: draft-diff shape/casting aggregates collapsed (분리집계 중화, D1)"
        )

    with _tempfile.TemporaryDirectory(prefix="bp-draft-diff-") as tmp:
        root = Path(tmp)
        before_p = root / "before.json"
        after_cast_p = root / "after-cast.json"
        same_p = root / "same.json"
        before_p.write_text(_json.dumps(base_decl), encoding="utf-8")
        after_cast_p.write_text(_json.dumps(casting_only), encoding="utf-8")
        same_p.write_text(_json.dumps(base_decl), encoding="utf-8")
        ledger = root / "flip-ledger.jsonl"
        prereg_dir = root / "preregistration"

        # P37 — append-only ledger grows by exactly one line and window reads it.
        r1 = dd.run_draft_diff(
            before_path=before_p, after_path=after_cast_p,
            ledger_path=ledger, prereg_dir=prereg_dir, window=dd.DEFAULT_FLIP_WINDOW,
        )
        after_first = len(ledger.read_text(encoding="utf-8").splitlines())
        r2 = dd.run_draft_diff(
            before_path=before_p, after_path=after_cast_p,
            ledger_path=ledger, prereg_dir=prereg_dir, window=dd.DEFAULT_FLIP_WINDOW,
        )
        after_second = len(ledger.read_text(encoding="utf-8").splitlines())
        if after_first != 1 or after_second != 2 or r2["rolling_window"]["sample"] != 2:
            out.append(
                "graph-draft RED: draft-diff flip ledger is not append-only-by-one (D1)"
            )

        # P38 — canary: a full window of zero-flip records surfaces the literal;
        # a sub-window sample must NOT (미실측 기본 태그). Also a variant-RED on
        # the exact canary literal.
        canary_ledger = root / "canary-ledger.jsonl"
        last = None
        for _ in range(dd.DEFAULT_FLIP_WINDOW):
            last = dd.run_draft_diff(
                before_path=same_p, after_path=same_p,
                ledger_path=canary_ledger, prereg_dir=prereg_dir,
                window=dd.DEFAULT_FLIP_WINDOW,
            )
        if last is None or last["canary"] is None or dd.THOUGHT_STALL_CANARY not in str(last["canary"]):
            out.append(
                "graph-draft RED: full zero-flip window did not surface the operator-thought-stall canary (D1)"
            )
        # variant-RED: the emitted canary must carry the EXACT hardcoded literal
        # (a drift of the module constant is caught here, not silently tracked).
        if last is not None and last["canary"] is not None and _CANARY_LITERAL_PIN not in str(last["canary"]):
            out.append(
                "graph-draft RED: emitted canary line drifted from the exact literal (D4 literal pin)"
            )
        # sub-window: the very first record must not fire the canary.
        early_ledger = root / "early-ledger.jsonl"
        early = dd.run_draft_diff(
            before_path=same_p, after_path=same_p,
            ledger_path=early_ledger, prereg_dir=prereg_dir,
            window=dd.DEFAULT_FLIP_WINDOW,
        )
        if early["canary"] is not None or early["rolling_window"]["measured"]:
            out.append(
                "graph-draft RED: sub-window zero-flip sample wrongly fired the canary (미실측 기본 태그, D1)"
            )
        # variant-RED: a flipped record inside the window suppresses the canary.
        mixed_ledger = root / "mixed-ledger.jsonl"
        for i in range(dd.DEFAULT_FLIP_WINDOW - 1):
            dd.run_draft_diff(
                before_path=same_p, after_path=same_p,
                ledger_path=mixed_ledger, prereg_dir=prereg_dir,
                window=dd.DEFAULT_FLIP_WINDOW,
            )
        mixed = dd.run_draft_diff(
            before_path=before_p, after_path=after_cast_p,
            ledger_path=mixed_ledger, prereg_dir=prereg_dir,
            window=dd.DEFAULT_FLIP_WINDOW,
        )
        if mixed["canary"] is not None:
            out.append(
                "graph-draft RED: a flipped record in the window did not suppress the canary (D1)"
            )

        # P39 — malformed input raises ValueError; a valid pair does not.
        bad_p = root / "bad.json"
        bad_p.write_text("not json{", encoding="utf-8")
        raised = False
        try:
            dd.run_draft_diff(
                before_path=bad_p, after_path=after_cast_p,
                ledger_path=ledger, prereg_dir=prereg_dir, window=dd.DEFAULT_FLIP_WINDOW,
            )
        except ValueError:
            raised = True
        if not raised:
            out.append(
                "graph-draft RED: malformed draft-diff input did not raise (rc=1 surface absent, D1)"
            )

        # P40 — blind pre-registration cross-check + prereg-first proof limit.
        prereg_dir.mkdir(parents=True, exist_ok=True)
        (prereg_dir / "dd-bld.json").write_text(
            _json.dumps({"width": 1, "kind_family": ["work"], "gates": []}),
            encoding="utf-8",
        )
        pr = dd.run_draft_diff(
            before_path=before_p, after_path=same_p,
            ledger_path=ledger, prereg_dir=prereg_dir, window=dd.DEFAULT_FLIP_WINDOW,
        )
        prereg = pr.get("preregistration", {})
        comparison = prereg.get("comparison")
        obs = prereg.get("prereg_first_observation", {})
        if (
            not prereg.get("present")
            or not isinstance(comparison, Mapping)
            or comparison.get("compared_field_count", 0) < 1
            or "forged" not in str(obs.get("proof_limit", ""))
        ):
            out.append(
                "graph-draft RED: blind pre-registration cross-check absent or missing the forge proof-limit (D2)"
            )

    # P41 — D3: the drafted rationale carries the answer_fingerprint line.
    with _tempfile.TemporaryDirectory(prefix="bp-draft-fp-") as tmp:
        res = draft_graph_declaration(
            SIMPLE_TASK, SIMPLE_DOC_ANSWERS, repo_root=repo,
            allowed_paths=("brick_protocol/support/operator/**",),
        )
        decl_path = write_draft_declaration(res, Path(tmp) / "fp-decl.json")
        rationale = decl_path.with_name(decl_path.stem + "-rationale.md").read_text(encoding="utf-8")
        fp = answer_fingerprint(res.sizing_answers)
        if ANSWER_FINGERPRINT_PREFIX not in rationale or f"sha256:{fp}" not in rationale:
            out.append(
                "graph-draft RED: drafted rationale is missing the canonical answer_fingerprint line (D3)"
            )

    # P42 — D1: casting classification keys on the LEAF key only, never on an
    # ancestor token. A structural sub-field beneath an ancestor named like a
    # casting key (nodes[0].model.training_corpus — ``model`` is a CONTAINER,
    # ``training_corpus`` is the changed leaf) must classify as a SHAPE flip, and
    # a structural change to it must land in shape_flips, never casting_flips.
    # Regressing classify_flip to ancestor-token matching (the 0707 collision
    # gap) flips this probe RED. The performer-selection leaves stay casting.
    _shape_leaves = (
        "nodes[0].model.training_corpus",
        "nodes[0].model.provider",
        "nodes[0].work.model_family_notes",
        "adapter_refs[1]",
    )
    _casting_leaves = (
        "nodes[0].model",
        "nodes[0].adapter_ref",
        "branches[2].casting.model",
        "nodes[0].fan.branches[0].effort",
    )
    if any(dd.classify_flip(p) != "shape" for p in _shape_leaves) or any(
        dd.classify_flip(p) != "casting" for p in _casting_leaves
    ):
        out.append(
            "graph-draft RED: casting classification used ancestor-token collision instead of the leaf key (D1)"
        )
    # End-to-end: a structural change to a sub-field under a casting-named ancestor
    # must aggregate as a shape flip, not a casting flip.
    ancestor_before = {
        "building_id": "dd-anc",
        "nodes": [{"kind": "work", "model": {"training_corpus": "c-v1"}}],
    }
    ancestor_after = {
        "building_id": "dd-anc",
        "nodes": [{"kind": "work", "model": {"training_corpus": "c-v2"}}],
    }
    anc_diff = dd.diff_declarations(ancestor_before, ancestor_after)
    if anc_diff["shape_flip_count"] != 1 or anc_diff["casting_flip_count"] != 0:
        out.append(
            "graph-draft RED: a structural sub-field under a casting-named ancestor was aggregated as a casting flip (D1 ancestor-token collision)"
        )

    # P43 — D2/law: the flip ledger and blind pre-registration are repo-outside
    # (<brick_home>) evidence (repo 안 산출 금지). A caller-supplied --ledger /
    # --prereg-dir that resolves inside the repo tree must be refused with a
    # ValueError; a repo-outside path must pass. Regressing the guard flips RED.
    from brick_protocol.support.operator import cli as _cli
    import tempfile as _tf2

    _inside = repo / "brick_protocol" / "support" / "operator" / "leaked-ledger.jsonl"
    _refused_inside = False
    try:
        _cli._assert_repo_outside(_inside, repo, flag="--ledger")
    except ValueError:
        _refused_inside = True
    _outside_ok = True
    with _tf2.TemporaryDirectory(prefix="bp-repo-outside-") as _outdir:
        try:
            _cli._assert_repo_outside(Path(_outdir) / "led.jsonl", repo, flag="--ledger")
        except ValueError:
            _outside_ok = False
    if not _refused_inside or not _outside_ok:
        out.append(
            "graph-draft RED: draft-diff ledger/prereg repo-outside guard missing (repo 안 산출 금지, D2)"
        )

    # P44 — D1: the rolling flip-rate window is SCOPED to the current building_id.
    # A shared append-only ledger may carry other Buildings' records; this
    # Building's canary must never be masked or fired by them (0707 attack-QA
    # cross-building pollution gap). Fill a full zero-flip window for building A,
    # then pollute the SAME ledger with flipped records for building B: A's canary
    # must still fire (B's flips don't mask it), and B's own window must NOT fire
    # the canary (A's zero-flip records don't leak into B's sample). Regressing to
    # an unfiltered whole-ledger window flips this probe RED.
    with _tempfile.TemporaryDirectory(prefix="bp-draft-scope-") as tmp:
        root = Path(tmp)
        shared_ledger = root / "shared-ledger.jsonl"
        prereg_dir = root / "preregistration"
        a_same = root / "a-same.json"
        b_before = root / "b-before.json"
        b_after = root / "b-after.json"
        a_same.write_text(
            _json.dumps({"building_id": "bld-A", "nodes": [{"kind": "work"}]}),
            encoding="utf-8",
        )
        b_before.write_text(
            _json.dumps(
                {"building_id": "bld-B", "nodes": [{"kind": "work", "adapter_ref": "adapter:codex-local"}]}
            ),
            encoding="utf-8",
        )
        b_after.write_text(
            _json.dumps(
                {"building_id": "bld-B", "nodes": [{"kind": "work", "adapter_ref": "adapter:claude-local"}]}
            ),
            encoding="utf-8",
        )
        # Full zero-flip window for building A on the shared ledger.
        a_last = None
        for _ in range(dd.DEFAULT_FLIP_WINDOW):
            a_last = dd.run_draft_diff(
                before_path=a_same, after_path=a_same,
                ledger_path=shared_ledger, prereg_dir=prereg_dir,
                window=dd.DEFAULT_FLIP_WINDOW,
            )
        if a_last is None or a_last["canary"] is None:
            out.append(
                "graph-draft RED: building-A zero-flip canary did not fire on the shared ledger (D1 window scope)"
            )
        # Pollute the SAME ledger with flipped building-B records; A's canary must
        # still fire on a re-diff (B's flips must not mask A's zero-flip window).
        for _ in range(dd.DEFAULT_FLIP_WINDOW):
            dd.run_draft_diff(
                before_path=b_before, after_path=b_after,
                ledger_path=shared_ledger, prereg_dir=prereg_dir,
                window=dd.DEFAULT_FLIP_WINDOW,
            )
        a_recheck = dd.run_draft_diff(
            before_path=a_same, after_path=a_same,
            ledger_path=shared_ledger, prereg_dir=prereg_dir,
            window=dd.DEFAULT_FLIP_WINDOW,
        )
        if a_recheck["canary"] is None:
            out.append(
                "graph-draft RED: cross-building flipped records masked building-A's canary (D1 window not building-scoped)"
            )
        # Building B's own window is all flips → its canary must NOT fire, and its
        # scoped sample must exclude A's records.
        b_last = dd.run_draft_diff(
            before_path=b_before, after_path=b_after,
            ledger_path=shared_ledger, prereg_dir=prereg_dir,
            window=dd.DEFAULT_FLIP_WINDOW,
        )
        if (
            b_last["canary"] is not None
            or b_last["rolling_window"].get("sample", 0) != dd.DEFAULT_FLIP_WINDOW
            or b_last["rolling_window"].get("ledger_total_records", 0) <= b_last["rolling_window"].get("building_records", 0)
        ):
            out.append(
                "graph-draft RED: building-B window absorbed cross-building records instead of scoping by building_id (D1)"
            )

    # P45 — D1: a real leaf value equal to the absent render sentinel must still
    # diff as a real add/removal. Presence is decided by key membership, never by
    # a sentinel default, so a leaf whose value literally equals the missing
    # marker cannot be laundered as "unchanged" (0707 attack-QA P1:
    # sentinel-collision-zero-flip). Regressing to a sentinel-default diff (``
    # flat.get(path, SENTINEL)``) flips this probe RED.
    _sentinel_before = {"building_id": "dd-sc", "a": "\u2205"}
    _sentinel_after = {"building_id": "dd-sc"}
    _sc_diff = dd.diff_declarations(_sentinel_before, _sentinel_after)
    if _sc_diff["total_flip_count"] < 1:
        out.append(
            "graph-draft RED: a real leaf equal to the absent sentinel was diffed as unchanged (D1 sentinel-collision)"
        )

    # P46 — D1: a scalar TYPE flip (int->str, bool->str, null->"") must be
    # recorded. A bare ``str(value)`` diff is blind to a type change (``str(1)
    # == str("1")``), an invisible edit an operator could launder past the
    # ledger (0707 attack-QA P2: type-flip-invisible-zero-flip). The diff keys on
    # typed tokens, so each type flip is a real flip; regressing to a bare-string
    # diff flips this probe RED. Equal-typed values still diff as unchanged.
    _type_pairs = (
        ({"building_id": "dd-tp", "n": 1}, {"building_id": "dd-tp", "n": "1"}),
        ({"building_id": "dd-tp", "b": True}, {"building_id": "dd-tp", "b": "True"}),
        ({"building_id": "dd-tp", "z": None}, {"building_id": "dd-tp", "z": ""}),
    )
    _type_ok = all(
        dd.diff_declarations(bef, aft)["total_flip_count"] >= 1 for bef, aft in _type_pairs
    )
    _same_typed = dd.diff_declarations(
        {"building_id": "dd-tp", "n": 1}, {"building_id": "dd-tp", "n": 1}
    )
    if not _type_ok or _same_typed["total_flip_count"] != 0:
        out.append(
            "graph-draft RED: a scalar type flip (int/bool/null) was invisible to the diff (D1 type-flip-invisible)"
        )

    # P47 — D1: the rolling window is scoped by EXACT building_id, and a
    # blank/absent target scopes to blank-id records ONLY — it must NOT absorb
    # every named Building's records (0707 attack-QA P10: blank-building_id-
    # window-absorbs-cross-building-records). Regressing ``records_for_building``
    # to "blank returns all" flips this probe RED.
    _mixed_records = [
        {"building_id": "A", "flipped": True},
        {"building_id": "B", "flipped": True},
        {"building_id": "", "flipped": False},
    ]
    _blank_scope = dd.records_for_building(_mixed_records, "")
    if len(_blank_scope) != 1 or _blank_scope[0].get("building_id") not in ("", None):
        out.append(
            "graph-draft RED: a blank building_id window absorbed named-Building records (D1 blank-id absorption)"
        )

    # P48 — D1: a non-positive rolling window is invalid input and must fall back
    # to the full default window, NOT clamp to 1. Clamping ``<=0`` to 1 let a
    # single zero-flip record satisfy ``sample >= window`` and fire the canary at
    # sample=1 (0707 attack-QA: negative-window-canary-sample-one). A single
    # zero-flip record under a negative window must stay unmeasured (no canary).
    _neg_rate = dd.rolling_flip_rate([{"flipped": False}], window=-5)
    _zero_rate = dd.rolling_flip_rate([{"flipped": False}], window=0)
    if (
        _neg_rate.get("measured")
        or _neg_rate.get("window") != dd.DEFAULT_FLIP_WINDOW
        or dd.thought_stall_canary_line(_neg_rate) is not None
        or _zero_rate.get("measured")
        or _zero_rate.get("window") != dd.DEFAULT_FLIP_WINDOW
    ):
        out.append(
            "graph-draft RED: a non-positive rolling window clamped to 1 and fired the canary at sample=1 (D1 negative-window)"
        )

    # P49 — D2/law: the repo-outside guard applies to the DEFAULT ledger/prereg
    # path too, not only caller-supplied --ledger/--prereg-dir. If BRICK_HOME
    # resolves inside the repo/worktree the default <brick_home>/drafts path lands
    # in the repo tree; the earlier "guard only explicit flags" logic bypassed the
    # guard entirely (0707 attack-QA P8: brick-home-in-repo-default-ledger-guard-
    # bypass). Driving _run_draft_diff with BRICK_HOME set INSIDE the repo and no
    # explicit ledger flag must be refused with a ValueError; regressing to guard
    # only the explicit flags flips this probe RED.
    import os as _os
    import argparse as _argparse
    import tempfile as _tf3
    from brick_protocol.support.operator import cli as _cli3

    _default_guarded = False
    with _tf3.TemporaryDirectory(prefix="bp-default-guard-") as _outdir:
        # Use a THROWAWAY repo dir as both the --repo arg and BRICK_HOME so the
        # default <brick_home>/drafts path resolves INSIDE that fake repo. A
        # regressed guard would then write into this temp dir (auto-cleaned),
        # never the real checkout — the probe fires RED without leaking a repo
        # artifact. A working guard raises before any write.
        _fake_repo = Path(_outdir) / "fake-repo"
        _fake_repo.mkdir(parents=True, exist_ok=True)
        _draft_p = _fake_repo / "d.json"
        _launch_p = _fake_repo / "l.json"
        _draft_p.write_text(_json.dumps({"building_id": "dg", "nodes": []}), encoding="utf-8")
        _launch_p.write_text(_json.dumps({"building_id": "dg", "nodes": []}), encoding="utf-8")
        _ns = _argparse.Namespace(
            repo=str(_fake_repo), draft=str(_draft_p), launched=str(_launch_p),
            ledger="", prereg_dir="", window=10,
        )
        _prev_home = _os.environ.get("BRICK_HOME")
        _os.environ["BRICK_HOME"] = str(_fake_repo)  # brick_home INSIDE the (fake) repo tree
        try:
            _cli3._run_draft_diff(_ns)
        except ValueError:
            _default_guarded = True
        except Exception:
            _default_guarded = False
        finally:
            if _prev_home is None:
                _os.environ.pop("BRICK_HOME", None)
            else:
                _os.environ["BRICK_HOME"] = _prev_home
    if not _default_guarded:
        out.append(
            "graph-draft RED: the default <brick_home> ledger/prereg path bypassed the repo-outside guard when BRICK_HOME was inside the repo (repo 안 산출 금지, D2)"
        )

    return out


def run(repo: Path) -> list[str]:
    violations = _violations(repo)
    return violations

def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence rule-pinning checker for the graph-draft drafter."
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    violations = run(repo)
    if violations:
        print("graph_draft_rules rejected evidence:", file=sys.stderr)
        for line in violations:
            print(f"- {line}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    print("graph_draft_rules passed: 55 probe(s)")
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

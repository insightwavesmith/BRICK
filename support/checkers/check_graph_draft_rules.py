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

P4 runs before P3 so mutation M3 (deleting the convergence emission) hits the
P4 literal first.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
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
            "write_set": {"allowed": ["support/operator/**"], "forbidden": [".git/**"]},
            "returns_field": "observed_evidence",
            "sibling_independent": True,
            "casting": {"adapter": "codex-local", "model": "", "effort": "", "timeout_seconds": 3600},
        },
        {
            "branch_id": "b2",
            "concern_key": "checks",
            "objective": "o2",
            "output_format": "json",
            "write_set": {"allowed": ["support/checkers/**"], "forbidden": [".git/**"]},
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
        allowed_paths=("support/operator/**",),
    )
    hard_nodes = _nodes(hard)
    simple_nodes = _nodes(simple)

    # P1 — rule ①②⑧: walker-adjacent+complex → fugu work + deep-design + 10800s.
    hard_work = _first_kind(hard_nodes, "work")
    if (
        hard_work is None
        or hard_work.get("adapter_ref") != "adapter:codex-fugu-local"
        or not _has_kind(hard_nodes, "deep-design")
        or hard.declaration.get("adapter_timeout_seconds") != 10800
    ):
        out.append(
            "graph-draft RED: walker-adjacent answers drafted a codex-solo work node (rule 1/2/8 violated)"
        )

    # P6 — rule ⑤: bare directory write_scope entries normalize to explicit globs.
    if hard_work is None or hard_work.get("write_scope", {}).get("allowed_paths") != ["support/**"]:
        out.append(
            "graph-draft RED: bare-directory write_scope was not normalized to an explicit glob"
        )

    # P2 — no over-escalation: simple-doc → codex work, no deep-design, no 10800.
    simple_work = _first_kind(simple_nodes, "work")
    if (
        simple_work is None
        or simple_work.get("adapter_ref") != "adapter:codex-local"
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
    overlap["branches"][1]["write_set"]["allowed"] = ["support/operator/**"]
    reds, _ = draft_rule_violations(_decl([]), partition_plan=overlap)
    if RED2_WRITE_SET_OVERLAP not in reds:
        out.append(
            "graph-draft RED: intersecting write-set partition draft was not rejected (RED-2)"
        )

    # P9 — RED-3: deep-tier casting below 10800s must be rejected.
    deep_decl = _decl(
        [{"kind": "work", "model_ref": "model:sakana:fugu-ultra"}],
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
                            "kind": "code-attack-qa",
                            "concern_key": "deep",
                            "objective": "deep",
                            "model_ref": "model:claude:claude-fable-5",
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
    module_src = (repo / "support/operator/graph_draft.py").read_text(encoding="utf-8")
    surface_texts.append(module_src)
    cli_src = (repo / "support/operator/cli.py").read_text(encoding="utf-8")
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

    return out


def _extract_draft_bodies(cli_src: str) -> str:
    """Return only the draft-related CLI function bodies for the Rule 3 scan.

    The rest of cli.py legitimately imports the launch driver; we scan only the
    ``_run_draft`` / ``_cmd_draft`` / ``_render_draft`` bodies so the check
    fires exactly when a launch seam is wired into the draft path.
    """

    lines = cli_src.splitlines()
    body: list[str] = []
    capture = False
    for line in lines:
        if line.startswith("def "):
            capture = line.startswith(
                ("def _run_draft", "def _cmd_draft", "def _render_draft")
            )
        if capture:
            body.append(line)
    return "\n".join(body)


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
    print("graph_draft_rules passed: 23 probe(s)")
    print(PROOF_LIMIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

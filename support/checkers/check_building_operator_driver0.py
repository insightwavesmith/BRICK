#!/usr/bin/env python3
"""Check BUILDING-OPERATOR-DRIVER-0 bounded portfolio driver invariants.

This checker is support evidence only. It runs the admitted
support/operator/driver.py over adapter:local deterministic fixtures. It does
not call providers, choose Movement, judge source truth, judge success or
quality, or claim concurrency / process-integrity behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


def _repo_root_from_arg(repo: str | None) -> Path:
    if repo:
        return Path(repo).resolve()
    return Path(__file__).resolve().parents[2]


def _ensure_import_path(repo: Path) -> None:
    import_identity = repo / "support" / "import_identity"
    for entry in (str(import_identity), str(repo)):
        if entry not in sys.path:
            sys.path.insert(0, entry)


def _proof_limits() -> list[str]:
    return [
        "support evidence only",
        "adapter:local deterministic fixture only",
        "not source truth",
        "not success judgment",
        "not quality judgment",
        "not Movement authority",
        "not concurrency proof",
        "not real-provider proof",
    ]


def _child_plan(
    prefix: str,
    *,
    candidate_ref: str,
    propose_candidate_ref: str | None = None,
    hold: bool = False,
) -> Mapping[str, Any]:
    brick_ref = f"brick-{prefix}-work"
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": f"link-row:{prefix}",
        "movement": "forward",
        "target_ref": candidate_ref,
        "next_brick_instance_ref": candidate_ref,
        "declared_gate_refs": ["link-gate:default-transition"],
    }
    if hold:
        link_row["transition_lifecycle"] = {
            "state": "paused",
            "progress_state": "in_progress",
            "paused_at_ref": f"link-transition:{prefix}-paused",
            "from_brick_ref": brick_ref,
            "pending_target_ref": candidate_ref,
            "required_disposition_owner": "caller-or-coo",
            "reason_refs": ["observation:d2-child-hold"],
        }
    else:
        link_row["building_lifecycle"] = {
            "state": "closed",
            "reason": f"{prefix} closed for BUILDING-OPERATOR-DRIVER-0 checker evidence.",
        }
    required_return = "observed_evidence, not_proven"
    if propose_candidate_ref:
        required_return = "observed_evidence, transition_concern_evidence, not_proven"
    return {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0530",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": _proof_limits(),
        "not_proven": ["semantic correctness of this synthetic portfolio child"],
        "steps": [
            {
                "step_ref": f"{prefix}-step",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": f"brick-row:{prefix}",
                        "brick_work_ref": f"work:{prefix}",
                        "brick_instance_ref": brick_ref,
                        "work_statement": (
                            "Return deterministic JSON fields for the D2 driver checker. "
                            "Do not choose Movement, target, quality, or disposition."
                        ),
                        "comparison_rule": (
                            "Observe returned field presence only; support does not judge quality."
                        ),
                        "required_return_shape": required_return,
                        "source_facts": [
                            "AGENTS.md"
                        ],
                    },
                    {
                        "axis": "Agent",
                        "row_ref": f"agent-row:{prefix}",
                        "agent_object_ref": "agent-object:coo",
                    },
                    link_row,
                ],
            }
        ],
    }


def _write_plan(plan_dir: Path, prefix: str, plan: Mapping[str, Any]) -> Path:
    path = plan_dir / f"{prefix}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _portfolio(
    label: str,
    *,
    candidates: Sequence[tuple[str, Path]],
    mode: str,
    budget: int,
    static_order: Sequence[str] | None = None,
    start_candidate_ref: str | None = None,
    policy: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    packet: dict[str, Any] = {
        "portfolio_ref": f"portfolio:{label}",
        "declared_by": "coo:d2-checker",
        "mode": mode,
        "candidate_buildings": [
            {"candidate_ref": candidate_ref, "building_plan_ref": str(path)}
            for candidate_ref, path in candidates
        ],
        "portfolio_transition_budget": {
            "owner_axis": "Link",
            "max_transitions": budget,
        },
        "proof_limits": _proof_limits(),
        "not_proven": ["real-provider multi-Building autonomy"],
    }
    if static_order is not None:
        packet["static_order"] = list(static_order)
    if start_candidate_ref is not None:
        packet["start_candidate_ref"] = start_candidate_ref
    if policy is not None:
        packet["portfolio_adoption_policy"] = dict(policy)
    return packet


def _policy(
    *,
    label: str,
    from_candidate_ref: str,
    candidate_ref: str,
    adopted_by: str = "coo:d2-checker",
    gate_ref: str = "link-gate:coo",
) -> Mapping[str, Any]:
    return {
        "policy_ref": f"portfolio-policy:{label}",
        "adopter_ref": adopted_by,
        "declared_gate_refs": [gate_ref],
        "adoptions": [
            {
                "from_candidate_ref": from_candidate_ref,
                "candidate_ref": candidate_ref,
                "adopted_by": adopted_by,
                "gate_ref": gate_ref,
                "reason_refs": [f"observation:{label}-declared-adoption"],
            }
        ],
    }


def _callable(proposals_by_brick_ref: Mapping[str, str]):
    def _inner(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {
            "observed_evidence": [f"observed {request.brick_instance_ref}"],
            "not_proven": [
                "semantic correctness",
                "real-provider behavior",
            ],
        }
        proposed = proposals_by_brick_ref.get(request.brick_instance_ref)
        if proposed:
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": [f"observation:{request.brick_instance_ref}-proposed-next"],
                "related_boundary_refs": [proposed],
                "proof_limits": ["Agent concern only", "not Movement authority"],
                "not_proven": ["semantic correctness of the proposed next Building"],
            }
        return returned

    return _inner


def _case_paths(tmp: Path, label: str) -> tuple[Path, Path, Path]:
    root = tmp / label
    return root / "plans", root / "buildings", root / "portfolio-projections"


def _run_driver(repo: Path, portfolio: Mapping[str, Any], output_root: Path, projection_root: Path, proposals: Mapping[str, str]):
    from brick_protocol.support.operator.driver import run_declared_portfolio

    return run_declared_portfolio(
        portfolio,
        repo_root=repo,
        output_root=output_root,
        portfolio_output_root=projection_root,
        overwrite_existing=True,
        local_callables={"callable:local:agent-invoke0-smoke": _callable(proposals)},
        adapter_cwd=repo,
        adapter_timeout_seconds=30,
    )


def _candidate_refs(result: Any) -> list[str]:
    return [str(row.get("candidate_ref")) for row in result.sequence]


def _adopted_by(result: Any) -> list[str]:
    return [str(row.get("adopted_by")) for row in result.sequence]


def _child_roots(result: Any) -> list[Path]:
    return [Path(str(row.get("child_evidence_root"))) for row in result.sequence]


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check(repo: Path) -> tuple[list[str], Mapping[str, Any]]:
    _ensure_import_path(repo)
    violations: list[str] = []
    summary: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="bp-d2-driver0-") as tmp_raw:
        tmp = Path(tmp_raw)

        # MODE 1: declared two-Building static order, default-transition between
        # closed children, portfolio reaches complete.
        plan_dir, out_root, projection_root = _case_paths(tmp, "mode1")
        b1 = "building-boundary:d2-mode1-building-1-closed"
        b2 = "building-boundary:d2-mode1-building-2-closed"
        p1 = _write_plan(plan_dir, "mode1-building-1", _child_plan("d2-mode1-building-1", candidate_ref=b1))
        p2 = _write_plan(plan_dir, "mode1-building-2", _child_plan("d2-mode1-building-2", candidate_ref=b2))
        mode1_portfolio = _portfolio(
            "d2-mode1",
            candidates=[(b1, p1), (b2, p2)],
            mode="static_order",
            static_order=[b1, b2],
            budget=2,
        )
        mode1 = _run_driver(repo, mode1_portfolio, out_root, projection_root, {})
        summary["mode1_sequence"] = [
            f"{row['sequence_number']}:{row['candidate_ref']} via {row['adopted_by']}"
            for row in mode1.sequence
        ]
        if mode1.frontier_kind != "complete":
            violations.append(f"mode1: expected complete frontier, got {mode1.frontier_kind}")
        if _candidate_refs(mode1) != [b1, b2]:
            violations.append(f"mode1: sequence drifted: {_candidate_refs(mode1)}")
        if _adopted_by(mode1)[1] != "link-gate:default-transition":
            violations.append("mode1: second Building was not default-transition adopted")

        # MODE 2: building-1 proposes among >=2 candidates; declared COO/Link
        # policy adopts b2, then exactly-one eligible b3 proceeds by default.
        plan_dir, out_root, projection_root = _case_paths(tmp, "mode2-policy")
        a = "building-boundary:d2-mode2-building-1-closed"
        b = "building-boundary:d2-mode2-building-2-closed"
        c = "building-boundary:d2-mode2-building-3-closed"
        pa = _write_plan(plan_dir, "mode2-building-1", _child_plan("d2-mode2-building-1", candidate_ref=a, propose_candidate_ref=b))
        pb = _write_plan(plan_dir, "mode2-building-2", _child_plan("d2-mode2-building-2", candidate_ref=b))
        pc = _write_plan(plan_dir, "mode2-building-3", _child_plan("d2-mode2-building-3", candidate_ref=c))
        mode2_policy_portfolio = _portfolio(
            "d2-mode2-policy",
            candidates=[(a, pa), (b, pb), (c, pc)],
            mode="adoption_policy",
            start_candidate_ref=a,
            budget=3,
            policy=_policy(label="d2-mode2-policy", from_candidate_ref=a, candidate_ref=b),
        )
        mode2_policy = _run_driver(
            repo,
            mode2_policy_portfolio,
            out_root,
            projection_root,
            {"brick-d2-mode2-building-1-work": b},
        )
        summary["mode2_policy_sequence"] = [
            f"{row['sequence_number']}:{row['candidate_ref']} via {row['adopted_by']}"
            for row in mode2_policy.sequence
        ]
        if _candidate_refs(mode2_policy)[:2] != [a, b]:
            violations.append(f"mode2-policy: adopted target drifted: {_candidate_refs(mode2_policy)}")
        if _adopted_by(mode2_policy)[1] != "coo:d2-checker":
            violations.append("mode2-policy: second Building was not adopted by declared COO policy")
        if mode2_policy.frontier_kind != "complete":
            violations.append(f"mode2-policy: expected complete frontier, got {mode2_policy.frontier_kind}")

        # MODE 2 negative: same agent proposal, but the only declared row is bare
        # default-transition. Must HOLD, not auto-adopt the selection.
        plan_dir, out_root, projection_root = _case_paths(tmp, "mode2-bare-default")
        pa = _write_plan(plan_dir, "bare-building-1", _child_plan("d2-bare-building-1", candidate_ref=a, propose_candidate_ref=b))
        pb = _write_plan(plan_dir, "bare-building-2", _child_plan("d2-bare-building-2", candidate_ref=b))
        pc = _write_plan(plan_dir, "bare-building-3", _child_plan("d2-bare-building-3", candidate_ref=c))
        bare_default_portfolio = _portfolio(
            "d2-mode2-bare-default",
            candidates=[(a, pa), (b, pb), (c, pc)],
            mode="adoption_policy",
            start_candidate_ref=a,
            budget=3,
            policy=_policy(
                label="d2-mode2-bare-default",
                from_candidate_ref=a,
                candidate_ref=b,
                adopted_by="link-gate:default-transition",
                gate_ref="link-gate:default-transition",
            ),
        )
        bare_default = _run_driver(
            repo,
            bare_default_portfolio,
            out_root,
            projection_root,
            {"brick-d2-bare-building-1-work": b},
        )
        summary["mode2_bare_default_frontier"] = bare_default.projection["frontier"]
        if bare_default.frontier_kind != "link_paused":
            violations.append(
                f"mode2-bare-default: expected link_paused rejection, got {bare_default.frontier_kind}"
            )
        if _candidate_refs(bare_default) != [a]:
            violations.append("mode2-bare-default: bare default-transition auto-adopted a multi-candidate target")
        if bare_default.projection["frontier"].get("frontier_reason") != "multi_candidate_requires_declared_policy":
            violations.append(
                "mode2-bare-default: HOLD reason did not preserve multi_candidate_requires_declared_policy"
            )

        # Negative: Agent proposes a candidate not in the declared set. Even with
        # a policy-looking row, the driver must not open it or substitute another.
        plan_dir, out_root, projection_root = _case_paths(tmp, "candidate-not-declared")
        rogue = "building-boundary:d2-rogue-building-closed"
        pa = _write_plan(plan_dir, "rogue-building-1", _child_plan("d2-rogue-building-1", candidate_ref=a, propose_candidate_ref=rogue))
        pb = _write_plan(plan_dir, "rogue-building-2", _child_plan("d2-rogue-building-2", candidate_ref=b))
        pc = _write_plan(plan_dir, "rogue-building-3", _child_plan("d2-rogue-building-3", candidate_ref=c))
        rogue_portfolio = _portfolio(
            "d2-candidate-not-declared",
            candidates=[(a, pa), (b, pb), (c, pc)],
            mode="adoption_policy",
            start_candidate_ref=a,
            budget=3,
            policy=_policy(label="d2-rogue-policy", from_candidate_ref=a, candidate_ref=rogue),
        )
        rogue_result = _run_driver(
            repo,
            rogue_portfolio,
            out_root,
            projection_root,
            {"brick-d2-rogue-building-1-work": rogue},
        )
        summary["candidate_not_declared_frontier"] = rogue_result.projection["frontier"]
        if rogue_result.frontier_kind != "link_paused":
            violations.append(
                f"candidate-not-in-declared-set: expected link_paused rejection, got {rogue_result.frontier_kind}"
            )
        if _candidate_refs(rogue_result) != [a]:
            violations.append("candidate-not-in-declared-set: driver opened or substituted an undeclared candidate")
        if rogue_result.projection["frontier"].get("frontier_reason") != "proposed_candidate_not_in_declared_set":
            violations.append("candidate-not-in-declared-set: HOLD reason did not name undeclared proposal")

        # Negative: support-authored selection row is not an adopting authority.
        plan_dir, out_root, projection_root = _case_paths(tmp, "support-authored")
        pa = _write_plan(plan_dir, "support-building-1", _child_plan("d2-support-building-1", candidate_ref=a, propose_candidate_ref=b))
        pb = _write_plan(plan_dir, "support-building-2", _child_plan("d2-support-building-2", candidate_ref=b))
        pc = _write_plan(plan_dir, "support-building-3", _child_plan("d2-support-building-3", candidate_ref=c))
        support_policy_portfolio = _portfolio(
            "d2-support-authored-selection",
            candidates=[(a, pa), (b, pb), (c, pc)],
            mode="adoption_policy",
            start_candidate_ref=a,
            budget=3,
            policy=_policy(
                label="d2-support-authored",
                from_candidate_ref=a,
                candidate_ref=b,
                adopted_by="support:driver",
                gate_ref="link-gate:coo",
            ),
        )
        support_authored = _run_driver(
            repo,
            support_policy_portfolio,
            out_root,
            projection_root,
            {"brick-d2-support-building-1-work": b},
        )
        if support_authored.frontier_kind != "link_paused" or _candidate_refs(support_authored) != [a]:
            violations.append("support-authored-selection: support-authored adoption was not rejected")

        # Budget exhaustion: a two-Building static order with budget 1 runs the
        # first child, then HOLDs before the second. The frontier reuses
        # link_paused + disposition_action surface.
        plan_dir, out_root, projection_root = _case_paths(tmp, "budget")
        p1 = _write_plan(plan_dir, "budget-building-1", _child_plan("d2-budget-building-1", candidate_ref=b1))
        p2 = _write_plan(plan_dir, "budget-building-2", _child_plan("d2-budget-building-2", candidate_ref=b2))
        budget_portfolio = _portfolio(
            "d2-budget",
            candidates=[(b1, p1), (b2, p2)],
            mode="static_order",
            static_order=[b1, b2],
            budget=1,
        )
        budget_result = _run_driver(repo, budget_portfolio, out_root, projection_root, {})
        budget_frontier = budget_result.projection["frontier"]
        summary["budget_frontier"] = budget_frontier
        if budget_result.frontier_kind != "link_paused":
            violations.append(f"budget: expected link_paused frontier, got {budget_result.frontier_kind}")
        lifecycle = budget_frontier.get("latest_transition_lifecycle", {})
        if not isinstance(lifecycle, Mapping) or lifecycle.get("transition_lifecycle_pending_target_ref") != b2:
            violations.append("budget: paused frontier did not carry pending second Building")
        surface = budget_frontier.get("disposition_action_surface", {})
        if not isinstance(surface, Mapping) or surface.get("allowed_values") != ["raise", "forward", "stop"]:
            violations.append("budget: disposition_action surface did not expose raise/forward/stop")

        # Child roots independent: use MODE1, where two children closed. The
        # portfolio projection references both roots and is outside both roots.
        roots = _child_roots(mode1)
        summary["child_roots"] = [str(root) for root in roots]
        summary["projection_path"] = str(mode1.projection_path)
        if len(roots) != 2 or roots[0] == roots[1]:
            violations.append(f"child-root-independence: expected two distinct roots, got {roots}")
        for root in roots:
            if not root.is_dir():
                violations.append(f"child-root-independence: missing child root {root}")
            if _is_under(mode1.projection_path, root):
                violations.append("child-root-independence: portfolio projection was written inside a child root")
        projected_roots = [row.get("child_evidence_root") for row in mode1.projection.get("sequence", [])]
        if projected_roots != [str(root) for root in roots]:
            violations.append("child-root-independence: projection did not reference exact child roots")

        summary["portfolio_projection_kind"] = mode1.projection.get("kind")

    return violations, summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker for BUILDING-OPERATOR-DRIVER-0; adapter:local only."
        )
    )
    parser.add_argument("--repo", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    repo = _repo_root_from_arg(args.repo)
    try:
        violations, summary = check(repo)
    except Exception as exc:  # noqa: BLE001 - checker should surface any driver break
        print(f"building operator driver checker rejected: {exc}", file=sys.stderr)
        return 1
    if violations:
        print("building operator driver checker rejected:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        print(
            "proof limit: support evidence only; this checker does not prove source truth, "
            "Movement authority, success, quality, real-provider behavior, concurrency, or process integrity.",
            file=sys.stderr,
        )
        return 1
    print(
        "building operator driver passed: "
        f"MODE1 sequence={summary['mode1_sequence']}; "
        f"MODE2 policy sequence={summary['mode2_policy_sequence']}; "
        "MODE2 bare-default rejected "
        f"frontier={summary['mode2_bare_default_frontier'].get('frontier_kind')} "
        f"reason={summary['mode2_bare_default_frontier'].get('frontier_reason')}; "
        "candidate-not-in-declared-set rejected "
        f"frontier={summary['candidate_not_declared_frontier'].get('frontier_kind')} "
        f"reason={summary['candidate_not_declared_frontier'].get('frontier_reason')}; "
        "budget frontier="
        f"{summary['budget_frontier'].get('frontier_kind')} "
        f"pending={summary['budget_frontier'].get('latest_transition_lifecycle', {}).get('transition_lifecycle_pending_target_ref')} "
        "disposition_actions="
        f"{summary['budget_frontier'].get('disposition_action_surface', {}).get('allowed_values')}; "
        f"child_roots={summary['child_roots']} projection={summary['projection_path']}."
    )
    print(
        "proof limit: support evidence only; checker pass does not prove source truth, "
        "success judgment, quality judgment, Movement authority, real provider behavior, "
        "concurrency, or full process integrity."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

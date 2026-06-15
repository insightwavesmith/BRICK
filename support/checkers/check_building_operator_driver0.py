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
import subprocess
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
    from support.checkers.lib.case_runners import _graph_test_plan_from_linear

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
    linear_plan = {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0530",
        "plan_shape": "linear",
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
    return _graph_test_plan_from_linear(linear_plan)


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


# ---------------------------------------------------------------------------
# W1 worktree-sandbox FIRE: a customer-facing WRITE dispatch must leave the
# customer repo's live tree UNTOUCHED (refs + tracked files unchanged), land
# the writes inside the engine worktree, commit ONLY on genuine completion, and
# keep the evidence durable after the worktree is disposed. Mutation-RED: bypass
# the worktree (adapter_cwd=repo) -> the live-tree-untouched assertion REDs.
#
# These cases drive the REAL support/operator/driver.run_customer_building_in_sandbox
# wrapper. They never call a real provider: a deterministic command_runner stands
# in for codex, writing the in-scope file into the dispatch cwd and returning a
# completing AgentFact. The "customer repo" is a FRESH /tmp git repo seeded with
# THIS repo's HEAD via `git archive` (so it carries the Brick template catalog a
# real customer install would have); it is NEVER nested inside the live tree.
# ---------------------------------------------------------------------------

_W1_WRITE_REL = "onboarding-example/fix.txt"
_W1_WRITE_SCOPE: dict[str, Any] = {
    "allowed_paths": ["onboarding-example/**"],
    "forbidden_paths": [".git/**", "AGENTS.md", "agent/**", "brick/**", "link/**",
                        "support/**", "project/**", "**/.env"],
}


def _remove_git_dir(path: Path) -> None:
    import shutil

    git_dir = path / ".git"
    if git_dir.is_dir():
        shutil.rmtree(git_dir)
    elif git_dir.exists():
        git_dir.unlink()


def _dir_snapshot(path: Path) -> tuple[str, ...]:
    return tuple(sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()))


def _git_text(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    return completed.stdout.strip()


# The minimal working-tree surfaces a customer install needs for the catalog +
# plan materialization the wrapper exercises. Copying from the WORKING TREE (not
# `git archive`) keeps this FIRE independent of whether the repo under test is a
# git checkout (a clean `git archive` overlay tree is NOT a git repo), so the
# proof never REDs on an environment artifact.
_W1_SEED_DIRS: tuple[str, ...] = ("brick", "support", "agent", "link")
_W1_SEED_FILES: tuple[str, ...] = ("AGENTS.md",)


def _seed_customer_repo(repo: Path, dest: Path) -> str:
    """Seed a fresh git repo at ``dest`` with the Brick catalog + plan surfaces
    copied from ``repo``'s WORKING TREE (a real customer install carries these).

    Returns the seeded HEAD SHA. Works whether or not ``repo`` is itself a git
    repo, and never nests anything inside the live tree.
    """

    import shutil

    def _ignore(_dirpath: str, names: list[str]) -> set[str]:
        # Skip git metadata, build caches, and the heavy generated project vessel
        # (not read by plan materialization) so the seed stays small + clean.
        skip = {".git", "__pycache__", ".pytest_cache", "node_modules", "public"}
        return {name for name in names if name in skip}

    for rel in _W1_SEED_DIRS:
        src = repo / rel
        if src.is_dir():
            shutil.copytree(src, dest / rel, ignore=_ignore, symlinks=False)
    for rel in _W1_SEED_FILES:
        src = repo / rel
        if src.is_file():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / rel)
    subprocess.run(["git", "-C", str(dest), "init", "-q"], check=True, timeout=60)
    subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True, timeout=120)
    subprocess.run(
        ["git", "-C", str(dest), "-c", "user.name=customer", "-c",
         "user.email=customer@brick.local", "commit", "-q", "-m", "seed BRICK catalog"],
        check=True,
        timeout=120,
    )
    return _git_text(dest, "rev-parse", "HEAD")


def _w1_intent(building_id: str) -> dict[str, Any]:
    return {
        "declared_by": "coo",
        "task_statement": f"Write {_W1_WRITE_REL} for the W1 worktree-sandbox FIRE.",
        "chain_preset_ref": "building-chain-preset:fast-fix",
        "selected_adapter_ref": "adapter:codex-local",
        "building_id": building_id,
        "write_scope": dict(_W1_WRITE_SCOPE),
    }


def _w1_completing_codex_runner(*, write: bool):
    """A deterministic stand-in for codex. Optionally writes the in-scope file
    into the dispatch cwd, then returns a completing AgentFact JSON."""

    def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int):
        from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

        del timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        if write:
            target = Path(cwd) / _W1_WRITE_REL
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixed by the W1 FIRE runner\n", encoding="utf-8")
        payload = {
            "observed_evidence": [f"wrote {_W1_WRITE_REL}"],
            "changed_files": [_W1_WRITE_REL],
            "commands_run": ["echo fix"],
            "handoff_refs": ["handoff:w1-work-done"],
            "received_work_ref": "work:w1-fast-fix",
            "not_proven": ["semantic correctness of the W1 fixture edit"],
            "attack_findings": [],
            "qa_observed_evidence": ["ran attack qa over the W1 fixture"],
            "closure_observed_evidence": ["closed the W1 fixture building"],
        }
        return LocalCliCompleted(call, 0, json.dumps(payload), "")

    return _runner


def _w1_incomplete_codex_runner():
    """A stand-in that writes the in-scope file but raises at the adapter
    boundary AFTER the first step, so the building holds (no complete frontier)
    and the wrapper must produce NO commit."""

    state = {"prompted": 0}

    def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int):
        from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

        del timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        state["prompted"] += 1
        # First real step: write the in-scope file, then fail with non-zero so
        # the building ends incomplete/held. (A non-zero codex exit is the
        # adapter-error path; the wrapper observes a non-complete frontier.)
        target = Path(cwd) / _W1_WRITE_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("partial W1 work\n", encoding="utf-8")
        return LocalCliCompleted(call, 1, "", "W1 incomplete: adapter boom")

    return _runner


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

    # W1 worktree-sandbox FIRE (the load-bearing customer-safety proof). Run in
    # its OWN system-temp dirs (a fresh /tmp customer repo + a durable evidence
    # root), never nested in the checker's tmp above and never the live tree.
    _w1_worktree_sandbox_fire(repo, violations, summary)

    # H2a direct-graph intake FIRE (heart H2 deterministic plumbing): a
    # pre-composed graph + inline task_statement runs through the NEW
    # run_composed_graph_intake seam (NO preset) and produces an evidence spine
    # INDISTINGUISHABLE in validity from a preset run.
    _h2a_direct_graph_intake_fire(repo, violations, summary)

    # H2b design-AI caller FIRE (heart H2 centerpiece): a CANNED design-AI
    # response is parsed/validated by compose_building_from_task into a VALIDATED
    # graph PROPOSAL (anti-lazy), then that proposal's graph is fed to H2a's
    # run_composed_graph_intake and runs to a complete frontier -- proving the
    # AI-SHAPED graph is actually runnable end to end. No live provider.
    _h2b_design_ai_caller_fire(repo, violations, summary)

    # H3b GOAL-journey FIRE (customer ENTRY): a free-form goal + a CANNED design
    # AI + a sentinel runner -> run_goal_in_sandbox COMPOSES a validated graph and
    # RUNS it INSIDE the SAME W1 worktree sandbox the preset customer path uses, to
    # a complete frontier with durable evidence, leaving the customer LIVE tree
    # byte-identical (HEAD + status). Mutation-RED: an INVALID proposal raises
    # BEFORE any run (no evidence, live tree clean). NO live AI / network.
    _h3b_goal_journey_fire(repo, violations, summary)

    # H3c gap2 TERMINAL-CLOSE NORMALIZE FIRE: a canned proposal whose terminal
    # target is the NON-closed boundary 'building-boundary:done' is normalized to
    # '...-closed' by compose_building_from_task and then runs to a COMPLETE
    # frontier (un-normalized it lands at closure_pending). The normalize is the
    # load-bearing fix that lets a customer goal reach complete.
    _h3c_terminal_close_normalize_fire(repo, violations, summary)

    # H3c gap4 COMPOSE-RETRY FIRE: compose_building_from_task's bounded retry
    # (max_attempts) returns the first VALID proposal across a non-deterministic
    # AI (invalid-then-valid -> retry succeeds; always-invalid -> raises after N;
    # always-valid attempt 1 -> single invoke, retry never engages).
    _h3c_compose_retry_fire(repo, violations, summary)

    # H3c gap1 BRAIN-CHOICE FIRE: run_goal_in_sandbox with a write-capable
    # adapter:codex-local actually routes through the codex CLI seam (sentinel
    # argv intercepted, NO real CLI) AND the W1 invariant holds (live tree byte-
    # identical). The CLI --brain -> adapter ref mapping is exact.
    _h3c_brain_choice_fire(repo, violations, summary)

    # H3d EFFECTIVE-WRITE FIRE: a goal-composed 'work' write-brick node that lands
    # with NO write_scope is STAMPED with the work-area write_scope (read-only
    # 'closure' stays unstamped); the stamped node + adapter:codex-local becomes
    # effective_write=True (opens real write), and the SAME node without the stamp
    # is effective_write=False (the stamp is load-bearing). This closes the gap a
    # live --brain claude dogfood hit (empty scope -> made_changes=False ->
    # link_paused). The stamp SUPPLIES scope; it never weakens the observed-write
    # invariant. NOT proven here: a LIVE claude actually writing a file (operator
    # re-dogfoods that separately).
    _h3d_effective_write_fire(repo, violations, summary)

    return violations, summary


# ---------------------------------------------------------------------------
# H2b design-AI caller FIRE: the NEW compose_building_from_task seam takes a
# task + the board, hands a CANNED design-AI response (deterministic, no live
# provider) through its parse/whitelist/validate gates, and RETURNS a VALIDATED
# graph PROPOSAL (anti-lazy: every requirement maps to a real node). We then
# FEED that proposal's validated graph to H2a's run_composed_graph_intake and
# assert it runs to a COMPLETE frontier (the AI-shaped graph is runnable). The
# proposal's graph is the SAME real-board shape the H2a FIRE composes by hand --
# here it arrives THROUGH the design-AI caller instead. compose_building_from_task
# PROPOSES only; the run is the separate H2a seam (post-approval).
# Mutation-RED: a canned response with an UNMAPPED requirement RAISES; a canned
# response whose graph carries movement='sideways' RAISES.
# ---------------------------------------------------------------------------

_H2B_TASK = (
    "Build the H2b design-AI smoke payload and synthesize its evidence "
    "deterministically; do not choose Movement or judge quality."
)


def _h2b_canned_proposal() -> Mapping[str, Any]:
    """A CANNED design-AI proposal over the SAME real-board 2-node graph the H2a
    FIRE hand-builds (work -> closure -> boundary). Both requirements map to real
    nodes (anti-lazy satisfied)."""

    nodes, edges = _h2a_graph()
    return {
        "requirements": ["implement-payload", "synthesize-evidence"],
        "graph": {"nodes": nodes, "edges": edges, "groups": []},
        "requirement_node_map": {
            "implement-payload": "work",
            "synthesize-evidence": "closure",
        },
        "preset_delta": "fresh",
    }


def _h2b_canned_ai_invoke(proposal: Mapping[str, Any]):
    """Return an ai_invoke(prompt)->text that ignores the prompt and replies with
    the canned proposal JSON (so the FIRE is deterministic; no live provider)."""

    text = json.dumps(proposal)

    def _invoke(_prompt: str) -> str:
        return text

    return _invoke


def _h2b_design_ai_caller_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.auto_compose import (
        AutoComposeError,
        compose_building_from_task,
    )
    from brick_protocol.support.operator.building_operation import (
        observe_building_frontier,
    )
    from brick_protocol.support.operator.driver import run_composed_graph_intake

    # FIRE: canned design-AI response -> VALIDATED graph proposal (anti-lazy).
    # selected_adapter_ref is the WRITE-CAPABLE adapter:codex-local (the same the
    # downstream run uses) so the H3d fail-closed write_scope stamped onto the
    # 'work' write-brick node validates against the observed-write invariant --
    # MIRRORING the real goal flow, where run_goal_in_sandbox threads the brain's
    # write-capable adapter into compose_building_from_task.
    proposal = compose_building_from_task(
        _H2B_TASK,
        ai_invoke=_h2b_canned_ai_invoke(_h2b_canned_proposal()),
        repo_root=repo,
        selected_adapter_ref="adapter:codex-local",
    )

    # H3d: the design AI emitted NO write_scope, but the 'work' node's brick is
    # write-needing -> the fail-closed default STAMPED the work-area write_scope +
    # marker. (read-only 'closure' node stays unstamped.) Assert the stamp landed.
    h2b_work_node = next(
        (
            node
            for node in proposal["graph"]["nodes"]
            if node.get("node_id") == "work"
        ),
        None,
    )
    h2b_closure_node = next(
        (
            node
            for node in proposal["graph"]["nodes"]
            if node.get("node_id") == "closure"
        ),
        None,
    )
    summary["h2b_work_write_scope"] = (
        h2b_work_node.get("write_scope") if isinstance(h2b_work_node, Mapping) else None
    )
    summary["h2b_work_write_need_marker"] = (
        h2b_work_node.get("requires_brick_write_scope")
        if isinstance(h2b_work_node, Mapping)
        else None
    )
    summary["h2b_closure_has_write_scope"] = (
        isinstance(h2b_closure_node, Mapping)
        and h2b_closure_node.get("write_scope") is not None
    )
    if summary["h2b_work_write_scope"] != {
        "allowed_paths": ["**"],
        "forbidden_paths": [".git/**"],
    }:
        violations.append(
            "h3d: the write-needing 'work' node was NOT stamped with the work-area "
            f"write_scope (got {summary['h2b_work_write_scope']!r})"
        )
    if summary["h2b_work_write_need_marker"] is not True:
        violations.append(
            "h3d: the stamped 'work' node did not carry requires_brick_write_scope=true"
        )
    if summary["h2b_closure_has_write_scope"]:
        violations.append(
            "h3d: the read-only 'closure' node was WRONGLY stamped with a write_scope"
        )
    summary["h2b_proposal_keys"] = sorted(proposal.keys())
    summary["h2b_requirements"] = list(proposal.get("requirements", []))
    summary["h2b_requirement_node_map"] = dict(proposal.get("requirement_node_map", {}))
    summary["h2b_preset_delta"] = proposal.get("preset_delta")
    summary["h2b_proposal_plan_shape"] = (
        proposal.get("composed_plan", {}).get("plan_shape")
        if isinstance(proposal.get("composed_plan"), Mapping)
        else None
    )

    if proposal.get("kind") != "building-graph-proposal":
        violations.append(
            f"h2b: proposal kind drifted: {proposal.get('kind')!r}"
        )
    if sorted(proposal.get("requirement_node_map", {})) != sorted(
        ["implement-payload", "synthesize-evidence"]
    ):
        violations.append(
            "h2b: validated proposal did not carry the full requirement->node map"
        )
    if summary["h2b_proposal_plan_shape"] != "graph":
        violations.append(
            f"h2b: composed plan in proposal is not plan_shape graph: "
            f"{summary['h2b_proposal_plan_shape']!r}"
        )

    # FEED the VALIDATED graph to H2a's run_composed_graph_intake (sentinel
    # codex runner; NO real CLI) -> the AI-shaped graph runs to complete.
    proposed_graph = proposal["graph"]
    with tempfile.TemporaryDirectory(prefix="bp-h2b-run-") as tmp_raw:
        out_root = Path(tmp_raw) / "fire"
        run_result = run_composed_graph_intake(
            proposed_graph["nodes"],
            proposed_graph["edges"],
            groups=proposed_graph.get("groups", []),
            task_statement=_H2B_TASK,
            declared_by="coo",
            selected_adapter_ref="adapter:codex-local",
            repo_root=repo,
            output_root=out_root,
            overwrite_existing=True,
            command_runner=_h2a_completing_codex_runner(),
            adapter_timeout_seconds=30,
        )
        root = Path(run_result.run_result.lifecycle_write.root)
        frontier = observe_building_frontier(root, repo_root=repo)
        summary["h2b_run_plan_shape"] = run_result.plan_shape
        summary["h2b_run_frontier_kind"] = frontier.get("frontier_kind")
        if run_result.plan_shape != "graph":
            violations.append(
                f"h2b-run: expected plan_shape graph, got {run_result.plan_shape!r}"
            )
        if frontier.get("frontier_kind") != "complete":
            violations.append(
                "h2b-run: the AI-shaped graph did NOT run to a complete frontier "
                f"(got {frontier.get('frontier_kind')!r})"
            )

    # MUTATION-RED (anti-lazy): a canned response that leaves a requirement
    # UNMAPPED must HARD-RAISE (anti-lazy coverage is load-bearing).
    unmapped = json.loads(json.dumps(_h2b_canned_proposal()))
    unmapped["requirement_node_map"].pop("synthesize-evidence", None)
    h2b_unmapped_raised = False
    try:
        compose_building_from_task(
            _H2B_TASK,
            ai_invoke=_h2b_canned_ai_invoke(unmapped),
            repo_root=repo,
            selected_adapter_ref="adapter:codex-local",
        )
    except AutoComposeError:
        h2b_unmapped_raised = True
    summary["h2b_unmapped_red_raised"] = h2b_unmapped_raised
    if not h2b_unmapped_raised:
        violations.append(
            "h2b-mutation-RED: an UNMAPPED requirement did NOT raise, so the "
            "anti-lazy requirement->node coverage is not load-bearing"
        )

    # MUTATION-RED (graph contract): a canned response whose edge movement is the
    # non-literal 'sideways' must HARD-RAISE via the compose_building contract.
    sideways = json.loads(json.dumps(_h2b_canned_proposal()))
    sideways["graph"]["edges"][0]["movement"] = "sideways"
    h2b_movement_raised = False
    try:
        compose_building_from_task(
            _H2B_TASK,
            ai_invoke=_h2b_canned_ai_invoke(sideways),
            repo_root=repo,
            selected_adapter_ref="adapter:codex-local",
        )
    except AutoComposeError:
        h2b_movement_raised = True
    summary["h2b_movement_red_raised"] = h2b_movement_raised
    if not h2b_movement_raised:
        violations.append(
            "h2b-mutation-RED: an edge movement='sideways' did NOT raise, so the "
            "compose_building graph contract is not enforced on the proposal"
        )


# ---------------------------------------------------------------------------
# H3b GOAL-journey FIRE: the customer ENTRY seam run_goal_in_sandbox takes a
# free-form GOAL + a CANNED design-AI ai_invoke (deterministic, NO live AI/
# network) + a command_runner sentinel (NO real CLI), COMPOSES a validated graph
# proposal, and RUNS that proposal's graph INSIDE the W1 disposable worktree
# sandbox. We assert:
#   * the goal COMPOSED to the expected nodes (the AI-shaped graph);
#   * the sandboxed run reached a COMPLETE frontier with DURABLE evidence
#     (outside the worktree);
#   * the customer's LIVE TREE is UNCHANGED -- HEAD + git status byte-identical
#     before/after (sandbox isolation proven), isolation_mode == "worktree";
#   * the SAME worktree sandbox the preset customer path uses was used (shared,
#     not forked): a worktree was created and disposed.
# Mutation-RED: a CANNED INVALID proposal (an UNMAPPED requirement -> anti-lazy;
# and a bad-graph movement='sideways') HARD-RAISES BEFORE any run -- the live
# tree stays clean and NO evidence root is produced. The FIRE NEVER calls a live
# provider or the network: ai_invoke is canned and command_runner is a sentinel.
# NOT proven here: a LIVE gemini call (the operator dogfoods invoke_gemini_text
# live, separately).
# ---------------------------------------------------------------------------

_H3B_GOAL = (
    "Build the H3b customer-goal smoke payload and synthesize its evidence "
    "deterministically; do not choose Movement or judge quality."
)


def _h3b_canned_proposal() -> Mapping[str, Any]:
    """A CANNED design-AI proposal over the SAME real-board 2-node graph the H2a
    FIRE hand-builds (work -> closure -> boundary). Both requirements map to real
    nodes (anti-lazy satisfied). This is what a customer's design AI would emit
    for the goal; here it arrives through the canned ai_invoke."""

    nodes, edges = _h2a_graph()
    return {
        "requirements": ["implement-payload", "synthesize-evidence"],
        "graph": {"nodes": nodes, "edges": edges, "groups": []},
        "requirement_node_map": {
            "implement-payload": "work",
            "synthesize-evidence": "closure",
        },
        "preset_delta": "fresh",
    }


def _h3b_canned_ai_invoke(proposal: Mapping[str, Any]):
    """An ai_invoke(prompt)->text that ignores the prompt and replies with the
    canned proposal JSON (deterministic; NO live provider, NO network)."""

    text = json.dumps(proposal)

    def _invoke(_prompt: str) -> str:
        return text

    return _invoke


def _h3b_goal_journey_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.auto_compose import AutoComposeError
    from brick_protocol.support.operator.driver import run_goal_in_sandbox

    with tempfile.TemporaryDirectory(prefix="bp-h3b-customer-") as cust_raw, \
            tempfile.TemporaryDirectory(prefix="bp-h3b-evidence-") as ev_raw:
        # The customer "repo" is its OWN subdir so the shared temp root is never
        # itself a git repo; it is seeded with THIS repo's catalog + a git HEAD
        # (the W1 helper) and is NEVER nested inside the live tree.
        customer = Path(cust_raw) / "customer-live"
        customer.mkdir(parents=True, exist_ok=True)
        evidence_root = Path(ev_raw)

        # CASE 1 (THE proof): free-form GOAL -> canned design AI COMPOSES a graph
        # -> the SAME worktree sandbox runs it to a COMPLETE frontier, and the
        # customer LIVE tree is left UNTOUCHED (HEAD + status byte-identical).
        head_before = _seed_customer_repo(repo, customer)
        status_before = _git_text(customer, "status", "--porcelain", "--untracked-files=all")
        result = run_goal_in_sandbox(
            _H3B_GOAL,
            ai_invoke=_h3b_canned_ai_invoke(_h3b_canned_proposal()),
            repo_root=customer,
            output_root=evidence_root / "complete",
            selected_adapter_ref="adapter:codex-local",
            command_runner=_h2a_completing_codex_runner(),
            adapter_timeout_seconds=30,
            overwrite_existing=True,
        )
        head_after = _git_text(customer, "rev-parse", "HEAD")
        status_after = _git_text(customer, "status", "--porcelain", "--untracked-files=all")

        summary["h3b_isolation_mode"] = result.isolation_mode
        summary["h3b_frontier_kind"] = result.frontier_kind
        summary["h3b_composed_node_ids"] = list(result.composed_node_ids)
        summary["h3b_building_id"] = result.building_id
        summary["h3b_head_unchanged"] = head_before == head_after
        summary["h3b_live_status_clean"] = status_before == "" and status_after == ""
        summary["h3b_evidence_dir"] = result.evidence_root

        # (a) the goal COMPOSED the AI-shaped graph (the proposal's nodes).
        if list(result.composed_node_ids) != ["work", "closure"]:
            violations.append(
                f"h3b: goal did not compose the expected nodes: {result.composed_node_ids!r}"
            )
        if result.proposal.get("kind") != "building-graph-proposal":
            violations.append(
                f"h3b: composed proposal kind drifted: {result.proposal.get('kind')!r}"
            )
        # (b) the sandboxed run reached a COMPLETE frontier with DURABLE evidence.
        if result.frontier_kind != "complete":
            violations.append(
                f"h3b: the composed goal did NOT run to a complete frontier "
                f"(got {result.frontier_kind!r})"
            )
        if not result.evidence_root or not Path(result.evidence_root).is_dir():
            violations.append("h3b: durable evidence root is missing after the sandboxed run")
        elif _is_under(Path(result.evidence_root), customer):
            violations.append("h3b: evidence was written INSIDE the customer repo (not durable)")
        # (c) SANDBOX ISOLATION: the live tree is byte-identical (HEAD + status).
        if result.isolation_mode != "worktree":
            violations.append(
                f"h3b: expected worktree isolation, got {result.isolation_mode!r}"
            )
        if head_before != head_after:
            violations.append(
                f"h3b-live-tree: customer HEAD moved {head_before} -> {head_after}"
            )
        if status_before != "" or status_after != "":
            violations.append(
                f"h3b-live-tree: customer git status not clean (before={status_before!r} "
                f"after={status_after!r})"
            )
        # The worktree must be gone after disposal (commit + evidence survive).
        wt_path = result.sandbox_result.worktree_path
        if not result.sandbox_result.worktree_disposed or (wt_path and Path(wt_path).exists()):
            violations.append("h3b-live-tree: the worktree was not disposed after the run")

        # MUTATION-RED (anti-lazy, BEFORE any run): a canned INVALID proposal with
        # an UNMAPPED requirement must HARD-RAISE in compose_building_from_task
        # BEFORE the sandbox run -- so the live tree stays clean and NO evidence
        # root is produced. We point at a FRESH customer repo and assert it is
        # byte-identical after the raise.
        customer_red = Path(cust_raw) / "customer-red"
        customer_red.mkdir(parents=True, exist_ok=True)
        red_head_before = _seed_customer_repo(repo, customer_red)
        red_status_before = _git_text(customer_red, "status", "--porcelain", "--untracked-files=all")
        unmapped = json.loads(json.dumps(_h3b_canned_proposal()))
        unmapped["requirement_node_map"].pop("synthesize-evidence", None)
        h3b_unmapped_raised = False
        try:
            run_goal_in_sandbox(
                _H3B_GOAL,
                ai_invoke=_h3b_canned_ai_invoke(unmapped),
                repo_root=customer_red,
                output_root=evidence_root / "red-unmapped",
                selected_adapter_ref="adapter:codex-local",
                command_runner=_h2a_completing_codex_runner(),
                adapter_timeout_seconds=30,
                overwrite_existing=True,
            )
        except AutoComposeError:
            h3b_unmapped_raised = True
        red_head_after = _git_text(customer_red, "rev-parse", "HEAD")
        red_status_after = _git_text(customer_red, "status", "--porcelain", "--untracked-files=all")
        summary["h3b_unmapped_red_raised"] = h3b_unmapped_raised
        summary["h3b_red_evidence_absent"] = not (evidence_root / "red-unmapped").exists()
        if not h3b_unmapped_raised:
            violations.append(
                "h3b-mutation-RED: an UNMAPPED requirement did NOT raise BEFORE the run, "
                "so the anti-lazy gate is not load-bearing on the goal entry"
            )
        # The raise happened BEFORE any run: no evidence root, live tree untouched.
        if (evidence_root / "red-unmapped").exists():
            violations.append(
                "h3b-mutation-RED: an INVALID proposal still produced an evidence root "
                "(the run was NOT skipped before composition failed)"
            )
        if red_head_before != red_head_after or red_status_before != "" or red_status_after != "":
            violations.append(
                "h3b-mutation-RED: an INVALID-proposal goal still mutated the live tree"
            )

        # MUTATION-RED (graph contract, BEFORE any run): a canned proposal whose
        # edge movement is the non-literal 'sideways' must HARD-RAISE too.
        sideways = json.loads(json.dumps(_h3b_canned_proposal()))
        sideways["graph"]["edges"][0]["movement"] = "sideways"
        h3b_movement_raised = False
        try:
            run_goal_in_sandbox(
                _H3B_GOAL,
                ai_invoke=_h3b_canned_ai_invoke(sideways),
                repo_root=customer,
                output_root=evidence_root / "red-movement",
                selected_adapter_ref="adapter:codex-local",
                command_runner=_h2a_completing_codex_runner(),
                adapter_timeout_seconds=30,
                overwrite_existing=True,
            )
        except AutoComposeError:
            h3b_movement_raised = True
        summary["h3b_movement_red_raised"] = h3b_movement_raised
        if not h3b_movement_raised:
            violations.append(
                "h3b-mutation-RED: an edge movement='sideways' did NOT raise BEFORE the run, "
                "so the compose_building graph contract is not enforced on the goal entry"
            )


# ---------------------------------------------------------------------------
# H3c gap2 TERMINAL-CLOSE NORMALIZE FIRE: a CANNED design-AI proposal whose
# terminal edge target is the NON-closed boundary ``building-boundary:done``
# (exactly what the live design AI emits per the old prompt example) is handed to
# compose_building_from_task. The seam NORMALIZES the terminal target to
# ``building-boundary:done-closed`` BEFORE composing, so the returned proposal's
# graph carries the closed boundary. We then FEED that proposal's graph to H2a's
# run_composed_graph_intake (sentinel codex runner; NO real CLI) and assert it
# runs to frontier=COMPLETE -- which it would NOT have done without the normalize
# (the un-closed boundary lands at closure_pending). Mutation-RED: the SAME graph
# run with the un-closed target UN-NORMALIZED lands at closure_pending (proving
# the normalize is load-bearing for reaching complete).
# ---------------------------------------------------------------------------

_H3C_TASK = (
    "Build the H3c terminal-close smoke payload and synthesize its evidence "
    "deterministically; do not choose Movement or judge quality."
)


def _h3c_unclosed_boundary_graph() -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """The SAME real-board work->closure 2-node graph the H2a FIRE hand-builds,
    but with the terminal edge targeting the NON-closed boundary
    ``building-boundary:done`` (the old prompt example) instead of a ``-closed``
    ref. The closing edge still carries building_lifecycle.state=closed, exactly
    as a realistic design-AI close edge would; only the target suffix is missing
    ``closed``."""

    nodes, edges = _h2a_graph()
    # Deep-copy via json so we never mutate the shared _h2a_graph fixtures.
    nodes = json.loads(json.dumps(nodes))
    edges = json.loads(json.dumps(edges))
    # The terminal edge is the second one (closure -> boundary). Point it at the
    # NON-closed boundary the live AI emits.
    edges[1]["target"] = "building-boundary:done"
    return nodes, edges


def _h3c_canned_proposal() -> Mapping[str, Any]:
    nodes, edges = _h3c_unclosed_boundary_graph()
    return {
        "requirements": ["implement-payload", "synthesize-evidence"],
        "graph": {"nodes": nodes, "edges": edges, "groups": []},
        "requirement_node_map": {
            "implement-payload": "work",
            "synthesize-evidence": "closure",
        },
        "preset_delta": "fresh",
    }


def _h3c_canned_ai_invoke(proposal: Mapping[str, Any]):
    text = json.dumps(proposal)

    def _invoke(_prompt: str) -> str:
        return text

    return _invoke


def _h3c_terminal_close_normalize_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.auto_compose import compose_building_from_task
    from brick_protocol.support.operator.building_operation import (
        observe_building_frontier,
    )
    from brick_protocol.support.operator.driver import run_composed_graph_intake

    # FIRE: canned proposal with the un-closed terminal -> compose_building_from_task
    # NORMALIZES it -> the returned proposal's terminal target ENDS in -closed.
    proposal = compose_building_from_task(
        _H3C_TASK,
        ai_invoke=_h3c_canned_ai_invoke(_h3c_canned_proposal()),
        repo_root=repo,
        selected_adapter_ref="adapter:codex-local",
    )
    proposed_graph = proposal["graph"]
    terminal_edge = proposed_graph["edges"][1]
    summary["h3c_normalized_terminal_target"] = terminal_edge.get("target")
    if terminal_edge.get("target") != "building-boundary:done-closed":
        violations.append(
            "h3c gap2: the un-closed terminal target was NOT normalized to "
            f"'building-boundary:done-closed' (got {terminal_edge.get('target')!r})"
        )

    # FEED the NORMALIZED graph to H2a's run_composed_graph_intake -> COMPLETE.
    with tempfile.TemporaryDirectory(prefix="bp-h3c-norm-") as tmp_raw:
        out_root = Path(tmp_raw) / "fire"
        run_result = run_composed_graph_intake(
            proposed_graph["nodes"],
            proposed_graph["edges"],
            groups=proposed_graph.get("groups", []),
            task_statement=_H3C_TASK,
            declared_by="coo",
            selected_adapter_ref="adapter:codex-local",
            repo_root=repo,
            output_root=out_root,
            overwrite_existing=True,
            command_runner=_h2a_completing_codex_runner(),
            adapter_timeout_seconds=30,
        )
        root = Path(run_result.run_result.lifecycle_write.root)
        frontier = observe_building_frontier(root, repo_root=repo)
        summary["h3c_normalized_frontier"] = frontier.get("frontier_kind")
        if frontier.get("frontier_kind") != "complete":
            violations.append(
                "h3c gap2: the NORMALIZED graph did NOT run to a complete frontier "
                f"(got {frontier.get('frontier_kind')!r})"
            )

    # MUTATION-RED (the normalize is load-bearing): the SAME graph run with the
    # un-closed boundary target UN-normalized lands at closure_pending, NOT
    # complete. This proves the un-closed target is the real blocker the normalize
    # removes (and that the normalize did not paper over an unrelated failure).
    raw_nodes, raw_edges = _h3c_unclosed_boundary_graph()
    with tempfile.TemporaryDirectory(prefix="bp-h3c-raw-") as tmp_raw:
        out_root = Path(tmp_raw) / "fire"
        run_result = run_composed_graph_intake(
            raw_nodes,
            raw_edges,
            task_statement=_H3C_TASK,
            declared_by="coo",
            selected_adapter_ref="adapter:codex-local",
            repo_root=repo,
            output_root=out_root,
            overwrite_existing=True,
            command_runner=_h2a_completing_codex_runner(),
            adapter_timeout_seconds=30,
        )
        root = Path(run_result.run_result.lifecycle_write.root)
        frontier = observe_building_frontier(root, repo_root=repo)
        summary["h3c_unnormalized_frontier"] = frontier.get("frontier_kind")
        if frontier.get("frontier_kind") == "complete":
            violations.append(
                "h3c gap2 mutation-RED: the UN-normalized un-closed boundary still "
                "reached complete, so the normalize is not load-bearing"
            )


# ---------------------------------------------------------------------------
# H3c gap4 COMPOSE-RETRY FIRE: compose_building_from_task is handed a STATEFUL
# canned ai_invoke that returns an INVALID proposal on attempt 1 (an edge
# movement='sideways' the compose_building contract rejects) and a VALID proposal
# on attempt 2. With max_attempts>=2 the seam re-invokes the AI and RETURNS the
# valid attempt-2 proposal (retry proven; invoke called exactly twice). A SECOND
# canned ai_invoke that is ALWAYS invalid RAISES AutoComposeError after exactly
# max_attempts invocations (bounded; the LAST error is surfaced). A canned
# ALWAYS-valid invoke with max_attempts=3 is called exactly ONCE (single-attempt
# behavior preserved when attempt 1 validates). NO live provider.
# ---------------------------------------------------------------------------


def _h3c_compose_retry_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.auto_compose import (
        AutoComposeError,
        compose_building_from_task,
    )

    def _valid_proposal() -> Mapping[str, Any]:
        nodes, edges = _h2a_graph()
        return {
            "requirements": ["implement-payload", "synthesize-evidence"],
            "graph": {"nodes": nodes, "edges": edges, "groups": []},
            "requirement_node_map": {
                "implement-payload": "work",
                "synthesize-evidence": "closure",
            },
            "preset_delta": "fresh",
        }

    def _invalid_proposal() -> Mapping[str, Any]:
        bad = json.loads(json.dumps(_valid_proposal()))
        # movement='sideways' is rejected by the compose_building contract.
        bad["graph"]["edges"][0]["movement"] = "sideways"
        return bad

    # CASE 1: invalid on attempt 1, valid on attempt 2 -> retry returns the valid
    # proposal. The invoke is called exactly twice.
    sequence = [_invalid_proposal(), _valid_proposal()]
    call_box = {"n": 0}

    def _invoke_then_valid(_prompt: str) -> str:
        index = min(call_box["n"], len(sequence) - 1)
        call_box["n"] += 1
        return json.dumps(sequence[index])

    proposal = compose_building_from_task(
        _H3C_TASK,
        ai_invoke=_invoke_then_valid,
        repo_root=repo,
        max_attempts=3,
        selected_adapter_ref="adapter:codex-local",
    )
    summary["h3c_retry_returned_valid"] = (
        proposal.get("kind") == "building-graph-proposal"
    )
    summary["h3c_retry_invoke_calls"] = call_box["n"]
    if proposal.get("kind") != "building-graph-proposal":
        violations.append(
            "h3c gap4: invalid-then-valid retry did NOT return a valid proposal"
        )
    if call_box["n"] != 2:
        violations.append(
            "h3c gap4: invalid-then-valid retry did not re-invoke exactly twice "
            f"(invoke calls={call_box['n']})"
        )

    # CASE 2: ALWAYS invalid -> raises AutoComposeError after exactly max_attempts
    # invocations (bounded; surfaces the last error).
    always_box = {"n": 0}

    def _invoke_always_invalid(_prompt: str) -> str:
        always_box["n"] += 1
        return json.dumps(_invalid_proposal())

    h3c_always_raised = False
    try:
        compose_building_from_task(
            _H3C_TASK,
            ai_invoke=_invoke_always_invalid,
            repo_root=repo,
            max_attempts=3,
            selected_adapter_ref="adapter:codex-local",
        )
    except AutoComposeError:
        h3c_always_raised = True
    summary["h3c_always_invalid_raised"] = h3c_always_raised
    summary["h3c_always_invalid_invoke_calls"] = always_box["n"]
    if not h3c_always_raised:
        violations.append(
            "h3c gap4: an ALWAYS-invalid proposal did NOT raise after max_attempts"
        )
    if always_box["n"] != 3:
        violations.append(
            "h3c gap4: an ALWAYS-invalid proposal was not retried exactly "
            f"max_attempts=3 times (invoke calls={always_box['n']})"
        )

    # CASE 3: ALWAYS valid + max_attempts=3 -> invoked exactly ONCE (single-attempt
    # behavior preserved when attempt 1 validates; the retry never engages).
    once_box = {"n": 0}

    def _invoke_always_valid(_prompt: str) -> str:
        once_box["n"] += 1
        return json.dumps(_valid_proposal())

    compose_building_from_task(
        _H3C_TASK,
        ai_invoke=_invoke_always_valid,
        repo_root=repo,
        max_attempts=3,
        selected_adapter_ref="adapter:codex-local",
    )
    summary["h3c_valid_single_invoke_calls"] = once_box["n"]
    if once_box["n"] != 1:
        violations.append(
            "h3c gap4: a VALID attempt-1 proposal engaged the retry loop "
            f"(invoke calls={once_box['n']}, expected 1)"
        )


# ---------------------------------------------------------------------------
# H3c gap1 BRAIN-CHOICE FIRE: run_goal_in_sandbox is handed the write-capable
# adapter ref ``adapter:codex-local`` + a command_runner SENTINEL (NO real CLI).
# We assert the codex-local adapter was actually used (the sentinel's argv was
# intercepted: argv[0] == 'codex') and that the customer LIVE tree is byte-
# identical (HEAD + status) before/after -- the W1 invariant holds for a real
# write-capable brain. The CLI ``--brain codex`` parse -> the adapter:codex-local
# ref is exercised separately (run_goal_entry brain pass-through).
# ---------------------------------------------------------------------------


def _h3c_brain_choice_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.driver import run_goal_in_sandbox

    seen_argv0: list[str] = []

    def _codex_sentinel_runner():
        inner = _h2a_completing_codex_runner()

        def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int):
            call = [str(arg) for arg in args]
            if call:
                seen_argv0.append(call[0])
            return inner(args, cwd, timeout_seconds)

        return _runner

    with tempfile.TemporaryDirectory(prefix="bp-h3c-brain-") as cust_raw, \
            tempfile.TemporaryDirectory(prefix="bp-h3c-brain-ev-") as ev_raw:
        customer = Path(cust_raw) / "customer-live"
        customer.mkdir(parents=True, exist_ok=True)
        evidence_root = Path(ev_raw)

        head_before = _seed_customer_repo(repo, customer)
        status_before = _git_text(customer, "status", "--porcelain", "--untracked-files=all")
        result = run_goal_in_sandbox(
            _H3C_TASK,
            ai_invoke=_h3c_canned_ai_invoke(
                {
                    "requirements": ["implement-payload", "synthesize-evidence"],
                    "graph": {
                        "nodes": _h2a_graph()[0],
                        "edges": _h2a_graph()[1],
                        "groups": [],
                    },
                    "requirement_node_map": {
                        "implement-payload": "work",
                        "synthesize-evidence": "closure",
                    },
                    "preset_delta": "fresh",
                }
            ),
            repo_root=customer,
            output_root=evidence_root / "brain",
            selected_adapter_ref="adapter:codex-local",
            command_runner=_codex_sentinel_runner(),
            adapter_timeout_seconds=30,
            overwrite_existing=True,
        )
        head_after = _git_text(customer, "rev-parse", "HEAD")
        status_after = _git_text(customer, "status", "--porcelain", "--untracked-files=all")

        summary["h3c_brain_argv0_seen"] = sorted(set(seen_argv0))
        summary["h3c_brain_frontier"] = result.frontier_kind
        summary["h3c_brain_head_unchanged"] = head_before == head_after
        summary["h3c_brain_live_status_clean"] = (
            status_before == "" and status_after == ""
        )

        # The codex-local adapter actually ran: the sentinel intercepted a 'codex'
        # argv (no real CLI was spawned). adapter:local would never shell out.
        if "codex" not in seen_argv0:
            violations.append(
                "h3c gap1: selected_adapter_ref=adapter:codex-local did NOT route "
                f"through the codex CLI seam (argv0 seen={sorted(set(seen_argv0))})"
            )
        if result.frontier_kind != "complete":
            violations.append(
                "h3c gap1: the codex-local goal run did not reach complete "
                f"(got {result.frontier_kind!r})"
            )
        # W1 INVARIANT (LAW): a real write-capable brain still NEVER writes the live
        # tree -- HEAD + git status byte-identical before/after.
        if head_before != head_after:
            violations.append(
                f"h3c gap1: codex-local moved the customer HEAD {head_before} -> {head_after}"
            )
        if status_before != "" or status_after != "":
            violations.append(
                "h3c gap1: codex-local dirtied the customer live tree "
                f"(before={status_before!r} after={status_after!r})"
            )

    # The CLI --brain parse -> adapter ref pass-through (no run): run_goal_entry is
    # the CLI wrapper; we assert its brain->adapter mapping is exact.
    from brick_protocol.support.operator.onboard import _brain_to_adapter_ref

    summary["h3c_brain_map"] = {
        "codex": _brain_to_adapter_ref("codex"),
        "claude": _brain_to_adapter_ref("claude"),
        "local": _brain_to_adapter_ref("local"),
    }
    expected = {
        "codex": "adapter:codex-local",
        "claude": "adapter:claude-local",
        "local": "adapter:local",
    }
    if summary["h3c_brain_map"] != expected:
        violations.append(
            "h3c gap1: --brain -> adapter ref mapping drifted: "
            f"{summary['h3c_brain_map']!r} (expected {expected!r})"
        )


# ---------------------------------------------------------------------------
# H3d EFFECTIVE-WRITE FIRE: the load-bearing proof that the H3d stamp opens real
# write. compose_building_from_task is handed a canned AI graph with a 'work'
# write-brick node carrying NO write_scope. The fail-closed default STAMPS the
# work-area write_scope + marker (read-only 'closure' node stays unstamped). We
# then build an AgentAdapterRequest from the STAMPED node + adapter:codex-local
# and assert agent_request_effective_write == True (the brain opens write); the
# SAME node WITHOUT the stamp (empty write_scope) -> effective_write == False.
# This proves the stamp is what makes the real brain able to write -- the gap a
# live --brain claude dogfood hit (made_changes=False -> link_paused).
# Mutation-RED is intrinsic: drop the stamped write_scope and effective_write
# falls to False, so the stamp is load-bearing (not decorative).
# ---------------------------------------------------------------------------

_H3D_TASK = (
    "Build the H3d effective-write smoke payload; do not choose Movement or "
    "judge quality."
)


def _h3d_effective_write_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.connection.agent_adapter import (
        ADAPTER_CODEX_LOCAL,
        READ_WRITE_TOOL_POLICY_REF,
        AgentAdapterRequest,
        agent_request_effective_write,
    )
    from brick_protocol.support.operator.auto_compose import compose_building_from_task

    # A canned AI graph (the SAME work->closure shape) with NO write_scope on the
    # write-brick 'work' node -- exactly the empty-scope landing the goal flow hit.
    canned = {
        "requirements": ["implement-payload", "synthesize-evidence"],
        "graph": {
            "nodes": _h2a_graph()[0],
            "edges": _h2a_graph()[1],
            "groups": [],
        },
        "requirement_node_map": {
            "implement-payload": "work",
            "synthesize-evidence": "closure",
        },
        "preset_delta": "fresh",
    }

    def _invoke(_prompt: str) -> str:
        return json.dumps(canned)

    proposal = compose_building_from_task(
        _H3D_TASK,
        ai_invoke=_invoke,
        repo_root=repo,
        selected_adapter_ref="adapter:codex-local",
    )
    nodes = proposal["graph"]["nodes"]
    work_node = next((n for n in nodes if n.get("node_id") == "work"), None)
    closure_node = next((n for n in nodes if n.get("node_id") == "closure"), None)

    stamped_scope = work_node.get("write_scope") if isinstance(work_node, Mapping) else None
    summary["h3d_stamped_work_scope"] = stamped_scope
    summary["h3d_closure_unstamped"] = (
        isinstance(closure_node, Mapping) and closure_node.get("write_scope") is None
    )
    if stamped_scope != {"allowed_paths": ["**"], "forbidden_paths": [".git/**"]}:
        violations.append(
            "h3d: compose_building_from_task did NOT stamp the work-area write_scope "
            f"on the write-brick node (got {stamped_scope!r})"
        )
    if not summary["h3d_closure_unstamped"]:
        violations.append(
            "h3d: the read-only 'closure' node was stamped with a write_scope"
        )

    # LOAD-BEARING: the STAMPED node + codex-local -> effective_write True.
    stamped_request = AgentAdapterRequest(
        building_id="h3d-effective-write",
        agent_object_ref="agent-object:dev",
        adapter_ref=ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-h3d-work",
        next_brick_instance_ref="brick-h3d-closure",
        tool_policy_refs=(READ_WRITE_TOOL_POLICY_REF,),
        write_scope=stamped_scope or {},
    )
    stamped_effective = agent_request_effective_write(stamped_request)
    summary["h3d_stamped_effective_write"] = stamped_effective
    if stamped_effective is not True:
        violations.append(
            "h3d: a STAMPED write node + adapter:codex-local did NOT become "
            "effective_write (the stamp did not open real write)"
        )

    # MUTATION-RED (the stamp is load-bearing): the SAME node WITHOUT the stamp
    # (empty write_scope) -> effective_write False. Drop the scope, re-probe.
    unstamped_request = AgentAdapterRequest(
        building_id="h3d-effective-write-unstamped",
        agent_object_ref="agent-object:dev",
        adapter_ref=ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-h3d-work",
        next_brick_instance_ref="brick-h3d-closure",
        tool_policy_refs=(READ_WRITE_TOOL_POLICY_REF,),
        write_scope={},
    )
    unstamped_effective = agent_request_effective_write(unstamped_request)
    summary["h3d_unstamped_effective_write"] = unstamped_effective
    if unstamped_effective is not False:
        violations.append(
            "h3d-mutation-RED: the SAME node WITHOUT the stamp (empty write_scope) "
            "still became effective_write, so the stamp is NOT load-bearing"
        )

    # PRE-SUPPLIED write_scope is UNCHANGED: a canned graph whose 'work' node
    # ALREADY carries a narrower write_scope must NOT be overridden by the stamp.
    pre_scope = {
        "allowed_paths": ["support/operator/**"],
        "forbidden_paths": [".git/**", "*.pem"],
    }
    pre_nodes = json.loads(json.dumps(_h2a_graph()[0]))
    for node in pre_nodes:
        if node.get("node_id") == "work":
            node["write_scope"] = dict(pre_scope)
            node["requires_brick_write_scope"] = True
    pre_canned = {
        "requirements": ["implement-payload", "synthesize-evidence"],
        "graph": {"nodes": pre_nodes, "edges": _h2a_graph()[1], "groups": []},
        "requirement_node_map": {
            "implement-payload": "work",
            "synthesize-evidence": "closure",
        },
        "preset_delta": "fresh",
    }

    def _invoke_pre(_prompt: str) -> str:
        return json.dumps(pre_canned)

    pre_proposal = compose_building_from_task(
        _H3D_TASK,
        ai_invoke=_invoke_pre,
        repo_root=repo,
        selected_adapter_ref="adapter:codex-local",
    )
    pre_work = next(
        (n for n in pre_proposal["graph"]["nodes"] if n.get("node_id") == "work"),
        None,
    )
    pre_work_scope = pre_work.get("write_scope") if isinstance(pre_work, Mapping) else None
    summary["h3d_pre_supplied_scope_unchanged"] = pre_work_scope == pre_scope
    if pre_work_scope != pre_scope:
        violations.append(
            "h3d: a PRE-SUPPLIED write_scope was OVERRIDDEN by the fail-closed stamp "
            f"(expected {pre_scope!r}, got {pre_work_scope!r})"
        )


# ---------------------------------------------------------------------------
# H2a direct-graph intake FIRE: the NEW run_composed_graph_intake seam takes a
# PRE-COMPOSED graph (compose_building args -- real board step templates/agents)
# + an inline task_statement, runs it through compose_building WITHOUT a preset,
# reattaches the REQUIRED inline task-source carry, and runs it. We assert the
# building materializes + RUNS to a complete frontier and that the evidence
# spine is INDISTINGUISHABLE in validity from a preset-intake run:
#   * task_source_ref == INLINE_TASK_SOURCE_REF (the inline sentinel)
#   * work/task.md body == the inline task_statement, verbatim
#   * building_id is STABLE on re-run (idempotent), dup root collides loudly
#   * plan_shape == graph
# Mutation-RED: omit task_statement -> the seam hard-RAISES (the carry is
# load-bearing). The adapter never calls a real CLI: a deterministic
# command_runner stands in for codex (mirroring case_runners 3845 / 1144).
# ---------------------------------------------------------------------------

_H2A_TASK = (
    "Build the H2a direct-graph smoke payload deterministically; "
    "do not choose Movement or judge quality."
)


def _h2a_graph() -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """A small hand-built 2-node graph (work -> closure) over REAL board step
    templates/agents -- the same node/edge shape compose_building admits, with
    NO chain preset declared."""

    nodes: list[Mapping[str, Any]] = [
        {
            "node_id": "work",
            "step_template_ref": "building-step-template:work",
            "brick_instance_ref": "brick-h2a-work",
            "brick_work_ref": "work:h2a",
            "work_statement": "Implement the H2a smoke payload.",
            "comparison_rule": "Observe support evidence only; do not judge quality.",
            "required_return_shape": "made_changes, observed_evidence, not_proven",
            "completion_edge_ref": "edge:h2a-work-to-closure",
        },
        {
            "node_id": "closure",
            "step_template_ref": "building-step-template:closure",
            "brick_instance_ref": "brick-h2a-closure",
            "brick_work_ref": "work:h2a-closure",
            "work_statement": "Synthesize the H2a smoke evidence.",
            "comparison_rule": "Closure synthesis returns its own fields; not Movement authority.",
            "required_return_shape": "observed_evidence, narrowly_proven, not_proven, remaining_delta",
            "completion_edge_ref": "edge:h2a-closure-to-boundary",
        },
    ]
    edges: list[Mapping[str, Any]] = [
        {
            "edge_ref": "edge:h2a-work-to-closure",
            "source": "work",
            "target": "closure",
            "movement": "forward",
        },
        {
            "edge_ref": "edge:h2a-closure-to-boundary",
            "source": "closure",
            "target": "building-boundary:h2a-closed",
            "movement": "forward",
            "building_lifecycle": {"state": "closed", "reason": "H2a smoke closed."},
        },
    ]
    return nodes, edges


def _h2a_completing_codex_runner():
    """Deterministic stand-in for codex: returns a completing AgentFact for both
    the work and closure bricks. NEVER calls a real CLI."""

    def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int):
        from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

        del cwd, timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        payload = {
            "observed_evidence": ["did the H2a smoke work"],
            "made_changes": True,
            "changed_files": [],
            "narrowly_proven": ["the H2a seam ran end to end"],
            "remaining_delta": ["nothing semantic proven by the smoke"],
            "not_proven": ["semantic correctness of the H2a smoke"],
        }
        return LocalCliCompleted(call, 0, json.dumps(payload), "")

    return _runner


def _h2a_run(repo: Path, out_root: Path, *, task_statement: Any = _H2A_TASK, overwrite: bool = False):
    from brick_protocol.support.operator.driver import run_composed_graph_intake

    nodes, edges = _h2a_graph()
    return run_composed_graph_intake(
        nodes,
        edges,
        task_statement=task_statement,
        declared_by="coo",
        selected_adapter_ref="adapter:codex-local",
        repo_root=repo,
        output_root=out_root,
        overwrite_existing=overwrite,
        command_runner=_h2a_completing_codex_runner(),
        adapter_timeout_seconds=30,
    )


def _h2a_direct_graph_intake_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.building_operation import observe_building_frontier
    from brick_protocol.support.operator.primitives import INLINE_TASK_SOURCE_REF

    with tempfile.TemporaryDirectory(prefix="bp-h2a-intake-") as tmp_raw:
        tmp = Path(tmp_raw)

        # FIRE: compose the no-preset graph + inline task, run it to a frontier.
        result = _h2a_run(repo, tmp / "fire", overwrite=True)
        root = Path(result.run_result.lifecycle_write.root)
        frontier = observe_building_frontier(root, repo_root=repo)
        plan_on_disk = json.loads(result.plan_path.read_text(encoding="utf-8"))
        task_md = root / "work" / "task.md"
        task_md_body = task_md.read_text(encoding="utf-8") if task_md.is_file() else None

        summary["h2a_building_id"] = result.building_id
        summary["h2a_plan_shape"] = result.plan_shape
        summary["h2a_frontier_kind"] = frontier.get("frontier_kind")
        summary["h2a_task_source_ref"] = plan_on_disk.get("task_source_ref")
        summary["h2a_task_source_hash"] = plan_on_disk.get("task_source_hash")
        summary["h2a_task_md_matches"] = task_md_body == (_H2A_TASK + "\n")

        if result.plan_shape != "graph":
            violations.append(f"h2a: expected plan_shape graph, got {result.plan_shape!r}")
        if frontier.get("frontier_kind") != "complete":
            violations.append(
                f"h2a: expected complete frontier, got {frontier.get('frontier_kind')!r}"
            )
        # Evidence spine INDISTINGUISHABLE from a preset run: inline sentinel ref.
        if plan_on_disk.get("task_source_ref") != INLINE_TASK_SOURCE_REF:
            violations.append(
                f"h2a: plan task_source_ref is not the inline sentinel: "
                f"{plan_on_disk.get('task_source_ref')!r}"
            )
        if plan_on_disk.get("task_source_hash_algorithm") != "sha256" or not plan_on_disk.get(
            "task_source_hash"
        ):
            violations.append("h2a: plan is missing the sha256 task_source_hash carry")
        # work/task.md body == the inline task_statement, verbatim.
        if task_md_body is None:
            violations.append("h2a: work/task.md was not landed from the carried task_statement")
        elif task_md_body != _H2A_TASK + "\n":
            violations.append(
                f"h2a: work/task.md body != inline task_statement (got {task_md_body!r})"
            )

        # IDEMPOTENCY: the same inline intent re-derives the SAME building_id
        # (independent of output root), and a SECOND write under the SAME root
        # collides loudly instead of duplicating.
        again = _h2a_run(repo, tmp / "fire-b", overwrite=False)
        summary["h2a_idempotent_id"] = again.building_id == result.building_id
        if again.building_id != result.building_id:
            violations.append(
                f"h2a-idempotency: same intent drifted building_id "
                f"{result.building_id!r} -> {again.building_id!r}"
            )
        try:
            _h2a_run(repo, tmp / "fire-b", overwrite=False)
        except ValueError:
            summary["h2a_dup_root_collides"] = True
        else:
            summary["h2a_dup_root_collides"] = False
            violations.append(
                "h2a-idempotency: a second intake under the same root did NOT collide "
                "(building_id is not load-bearing for de-dup)"
            )
        # A DIFFERENT statement must derive a DIFFERENT id.
        other = _h2a_run(repo, tmp / "fire-c", task_statement="A different H2a task statement.")
        if other.building_id == result.building_id:
            violations.append("h2a-idempotency: a different task_statement reused the same id")

        # MUTATION-RED: omit the task_statement -> the seam must HARD-RAISE
        # (the inline carry is load-bearing; a missing body is a broken road).
        red_raised = False
        try:
            _h2a_run(repo, tmp / "fire-red", task_statement=None, overwrite=True)
        except (ValueError, TypeError):
            red_raised = True
        summary["h2a_mutation_red_raised"] = red_raised
        if not red_raised:
            violations.append(
                "h2a-mutation-RED: omitting task_statement did NOT raise, so the inline "
                "task-source carry is not load-bearing"
            )


def _w1_worktree_sandbox_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.driver import (
        run_building_intake,
        run_customer_building_in_sandbox,
    )

    with tempfile.TemporaryDirectory(prefix="bp-w1-customer-") as cust_raw, \
            tempfile.TemporaryDirectory(prefix="bp-w1-evidence-") as ev_raw:
        # Each customer "repo" is its OWN subdir so the shared temp root is never
        # itself a git repo (otherwise a subdir whose .git we remove would still
        # resolve UP to the root repo and misreport its probe reason).
        customer = Path(cust_raw) / "customer-live"
        customer.mkdir(parents=True, exist_ok=True)
        evidence_root = Path(ev_raw)

        # CASE 1 (THE proof): customer-facing WRITE dispatch through the worktree
        # wrapper leaves the live tree UNTOUCHED; writes land in the worktree;
        # commit on completion; evidence durable; worktree gone after dispose.
        head_before = _seed_customer_repo(repo, customer)
        status_before = _git_text(customer, "status", "--porcelain", "--untracked-files=all")
        result = run_customer_building_in_sandbox(
            _w1_intent("w1-live-tree-untouched-0"),
            customer_repo_root=customer,
            output_root=evidence_root / "complete",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=True),
            adapter_timeout_seconds=30,
        )
        head_after = _git_text(customer, "rev-parse", "HEAD")
        status_after = _git_text(customer, "status", "--porcelain", "--untracked-files=all")
        summary["w1_isolation_mode"] = result.isolation_mode
        summary["w1_frontier_kind"] = result.frontier_kind
        summary["w1_commit_sha"] = result.commit_sha
        summary["w1_head_unchanged"] = head_before == head_after
        summary["w1_live_status_clean"] = status_after == ""

        if result.isolation_mode != "worktree":
            violations.append(
                f"w1-live-tree: expected worktree isolation, got {result.isolation_mode!r}"
            )
        # (a) live tree untouched: refs + tracked/untracked status unchanged.
        if head_before != head_after:
            violations.append(
                f"w1-live-tree: customer HEAD moved {head_before} -> {head_after}"
            )
        if status_before != "" or status_after != "":
            violations.append(
                f"w1-live-tree: customer git status not clean (before={status_before!r} "
                f"after={status_after!r})"
            )
        if (customer / _W1_WRITE_REL).exists():
            violations.append("w1-live-tree: the write landed in the LIVE customer tree")
        # (b) writes landed in the engine worktree (it is force-disposed, but the
        # commit captured exactly the in-scope write).
        # (c) commit exists on completion + (d) evidence durable outside worktree.
        if result.frontier_kind != "complete":
            violations.append(
                f"w1-live-tree: expected complete frontier, got {result.frontier_kind!r}"
            )
        if not result.commit_sha:
            violations.append("w1-live-tree: completion produced NO commit")
        else:
            committed_files = _git_text(
                customer, "diff-tree", "--no-commit-id", "--name-only", "-r", result.commit_sha
            )
            summary["w1_commit_files"] = committed_files
            if committed_files != _W1_WRITE_REL:
                violations.append(
                    f"w1-live-tree: commit did not capture exactly {_W1_WRITE_REL}: "
                    f"{committed_files!r}"
                )
            committed_body = _git_text(customer, "show", f"{result.commit_sha}:{_W1_WRITE_REL}")
            if "fixed by the W1 FIRE runner" not in committed_body:
                violations.append("w1-live-tree: committed file body did not match the write")
            on_branch = _git_text(customer, "branch", "--contains", result.commit_sha)
            if on_branch:
                violations.append(
                    f"w1-live-tree: output commit moved a branch (expected dangling): {on_branch!r}"
                )
        if not Path(result.evidence_root).is_dir():
            violations.append("w1-live-tree: durable evidence root is missing")
        if result.worktree_path and Path(result.evidence_root).resolve().is_relative_to(
            Path(result.worktree_path).resolve().parent
        ) and result.worktree_path in result.evidence_root:
            violations.append("w1-live-tree: evidence was written inside the worktree")
        # (e) worktree disposed: directory gone, but commit + evidence remain.
        if not result.worktree_disposed or (result.worktree_path and Path(result.worktree_path).exists()):
            violations.append("w1-live-tree: worktree was not disposed after capture")
        if result.commit_sha:
            survived = _git_text(customer, "cat-file", "-t", result.commit_sha)
            if survived != "commit":
                violations.append("w1-live-tree: output commit did not survive worktree disposal")

        # CASE 2 (non-git refuse): point the wrapper at a NON-git dir that still
        # carries the Brick catalog (a checkout whose .git was removed) -> the
        # probe fails closed, the wrapper falls back to a temp dir, creates NO
        # worktree, does NOT mutate the dir, and reports degraded mode. The write
        # lands in the temp dir (so even a real provider never touches the dir).
        non_git = Path(cust_raw) / "not-a-repo"
        non_git.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, non_git)
        _remove_git_dir(non_git)  # now a non-git dir that still has the catalog
        before_snapshot = _dir_snapshot(non_git)
        degraded = run_customer_building_in_sandbox(
            _w1_intent("w1-non-git-refuse-0"),
            customer_repo_root=non_git,
            output_root=evidence_root / "degraded",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=True),
            adapter_timeout_seconds=30,
        )
        after_snapshot = _dir_snapshot(non_git)
        summary["w1_degraded_mode"] = degraded.isolation_mode
        summary["w1_degraded_reason"] = degraded.isolation_reason
        summary["w1_degraded_frontier"] = degraded.frontier_kind
        if degraded.isolation_mode != "temp_dir":
            violations.append(
                f"w1-non-git: expected temp_dir fallback, got {degraded.isolation_mode!r}"
            )
        if degraded.isolation_reason != "not-a-git-work-tree":
            violations.append(
                f"w1-non-git: degraded reason drifted: {degraded.isolation_reason!r}"
            )
        if degraded.worktree_path:
            violations.append("w1-non-git: a worktree was created over a non-git dir")
        if degraded.commit_sha:
            violations.append("w1-non-git: a commit was produced in degraded mode")
        if (non_git / _W1_WRITE_REL).exists():
            violations.append("w1-non-git: the write landed in the non-git customer dir")
        if before_snapshot != after_snapshot:
            violations.append("w1-non-git: the non-git customer dir was mutated")

        # CASE 2b (dirty refuse): a DIRTY git tree must ALSO degrade (a dirty base
        # cannot guarantee carry isolation) -> temp_dir fallback, dir untouched.
        dirty = Path(cust_raw) / "customer-dirty"
        dirty.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, dirty)
        (dirty / "uncommitted.txt").write_text("dirty carry\n", encoding="utf-8")
        dirty_status_before = _git_text(dirty, "status", "--porcelain", "--untracked-files=all")
        dirty_result = run_customer_building_in_sandbox(
            _w1_intent("w1-dirty-refuse-0"),
            customer_repo_root=dirty,
            output_root=evidence_root / "dirty",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=True),
            adapter_timeout_seconds=30,
        )
        dirty_status_after = _git_text(dirty, "status", "--porcelain", "--untracked-files=all")
        summary["w1_dirty_mode"] = dirty_result.isolation_mode
        summary["w1_dirty_reason"] = dirty_result.isolation_reason
        if dirty_result.isolation_mode != "temp_dir":
            violations.append(
                f"w1-dirty: expected temp_dir fallback over a dirty tree, got "
                f"{dirty_result.isolation_mode!r}"
            )
        if dirty_result.isolation_reason != "dirty-work-tree":
            violations.append(f"w1-dirty: degraded reason drifted: {dirty_result.isolation_reason!r}")
        if dirty_result.worktree_path or dirty_result.commit_sha:
            violations.append("w1-dirty: a dirty tree was not refused (worktree/commit produced)")
        if (dirty / _W1_WRITE_REL).exists() or dirty_status_before != dirty_status_after:
            violations.append("w1-dirty: the dirty customer tree was further mutated")

        # CASE 3 (incomplete = no commit): a building that does NOT complete ->
        # no commit produced; reported not-complete; live tree still untouched.
        customer3 = Path(cust_raw) / "customer-incomplete"
        customer3.mkdir(parents=True, exist_ok=True)
        head3_before = _seed_customer_repo(repo, customer3)
        incomplete = run_customer_building_in_sandbox(
            _w1_intent("w1-incomplete-no-commit-0"),
            customer_repo_root=customer3,
            output_root=evidence_root / "incomplete",
            overwrite_existing=True,
            command_runner=_w1_incomplete_codex_runner(),
            adapter_timeout_seconds=30,
        )
        head3_after = _git_text(customer3, "rev-parse", "HEAD")
        status3_after = _git_text(customer3, "status", "--porcelain", "--untracked-files=all")
        summary["w1_incomplete_frontier"] = incomplete.frontier_kind
        summary["w1_incomplete_commit"] = incomplete.commit_sha
        if incomplete.frontier_kind == "complete":
            violations.append("w1-incomplete: a non-completing building reported a complete frontier")
        if incomplete.commit_sha:
            violations.append(
                f"w1-incomplete: a non-completing building produced a commit {incomplete.commit_sha}"
            )
        if head3_before != head3_after or status3_after != "":
            violations.append("w1-incomplete: the live tree was mutated by a held building")

        # MUTATION-RED: bypass the worktree (run the SAME write dispatch directly
        # with adapter_cwd = the live customer repo). The live-tree-untouched
        # assertion MUST now RED: the write lands in the live tree / its status
        # goes dirty. If bypassing the wrapper leaves the live tree clean, the
        # whole proof is vacuous, so we fail closed.
        customer4 = Path(cust_raw) / "customer-mutation"
        customer4.mkdir(parents=True, exist_ok=True)
        head4_before = _seed_customer_repo(repo, customer4)
        try:
            run_building_intake(
                _w1_intent("w1-mutation-red-0"),
                repo_root=customer4,
                output_root=evidence_root / "mutation",
                overwrite_existing=True,
                command_runner=_w1_completing_codex_runner(write=True),
                adapter_cwd=customer4,  # BYPASS: write straight into the live tree
                adapter_timeout_seconds=30,
            )
        except Exception:  # noqa: BLE001 -- the bypass may raise; the live mutation is the point
            pass
        head4_after = _git_text(customer4, "rev-parse", "HEAD")
        status4_after = _git_text(customer4, "status", "--porcelain", "--untracked-files=all")
        bypass_left_live_tree_dirty = (
            (customer4 / _W1_WRITE_REL).exists()
            or status4_after != ""
            or head4_before != head4_after
        )
        summary["w1_mutation_bypass_dirtied_live_tree"] = bypass_left_live_tree_dirty
        if not bypass_left_live_tree_dirty:
            violations.append(
                "w1-mutation-RED: bypassing the worktree did NOT dirty the live tree, so the "
                "live-tree-untouched proof is vacuous"
            )


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
        "W1 worktree-sandbox FIRE passed: "
        f"live-tree-untouched isolation={summary.get('w1_isolation_mode')} "
        f"frontier={summary.get('w1_frontier_kind')} commit={summary.get('w1_commit_sha')} "
        f"commit_files={summary.get('w1_commit_files')} "
        f"head_unchanged={summary.get('w1_head_unchanged')} "
        f"live_status_clean={summary.get('w1_live_status_clean')}; "
        f"non-git-refuse mode={summary.get('w1_degraded_mode')} reason={summary.get('w1_degraded_reason')}; "
        f"dirty-refuse mode={summary.get('w1_dirty_mode')} reason={summary.get('w1_dirty_reason')}; "
        f"incomplete frontier={summary.get('w1_incomplete_frontier')} commit={summary.get('w1_incomplete_commit')!r}; "
        f"mutation-RED bypass_dirtied_live_tree={summary.get('w1_mutation_bypass_dirtied_live_tree')}."
    )
    print(
        "H2a direct-graph intake FIRE passed: "
        f"building_id={summary.get('h2a_building_id')} plan_shape={summary.get('h2a_plan_shape')} "
        f"frontier={summary.get('h2a_frontier_kind')} "
        f"task_source_ref={summary.get('h2a_task_source_ref')} "
        f"task_md_matches={summary.get('h2a_task_md_matches')} "
        f"idempotent_id={summary.get('h2a_idempotent_id')} "
        f"dup_root_collides={summary.get('h2a_dup_root_collides')} "
        f"mutation_red_raised={summary.get('h2a_mutation_red_raised')}."
    )
    print(
        "H2b design-AI caller FIRE passed: "
        f"proposal_keys={summary.get('h2b_proposal_keys')} "
        f"requirements={summary.get('h2b_requirements')} "
        f"requirement_node_map={summary.get('h2b_requirement_node_map')} "
        f"preset_delta={summary.get('h2b_preset_delta')!r} "
        f"proposal_plan_shape={summary.get('h2b_proposal_plan_shape')} "
        f"run_frontier={summary.get('h2b_run_frontier_kind')}; "
        f"anti-lazy unmapped_red_raised={summary.get('h2b_unmapped_red_raised')} "
        f"movement_red_raised={summary.get('h2b_movement_red_raised')}."
    )
    print(
        "H3b GOAL-journey FIRE passed: "
        f"composed_nodes={summary.get('h3b_composed_node_ids')} "
        f"building_id={summary.get('h3b_building_id')} "
        f"isolation={summary.get('h3b_isolation_mode')} "
        f"frontier={summary.get('h3b_frontier_kind')} "
        f"head_unchanged={summary.get('h3b_head_unchanged')} "
        f"live_status_clean={summary.get('h3b_live_status_clean')} "
        f"evidence={summary.get('h3b_evidence_dir')}; "
        f"mutation-RED unmapped_raised={summary.get('h3b_unmapped_red_raised')} "
        f"red_evidence_absent={summary.get('h3b_red_evidence_absent')} "
        f"movement_raised={summary.get('h3b_movement_red_raised')} "
        "(LIVE gemini NOT exercised here -- operator dogfoods invoke_gemini_text live separately)."
    )
    print(
        "H3c completion FIREs passed: "
        f"gap2 normalize terminal={summary.get('h3c_normalized_terminal_target')!r} "
        f"-> frontier={summary.get('h3c_normalized_frontier')} "
        f"(un-normalized={summary.get('h3c_unnormalized_frontier')}); "
        f"gap4 retry invalid-then-valid returned_valid={summary.get('h3c_retry_returned_valid')} "
        f"invoke_calls={summary.get('h3c_retry_invoke_calls')}, "
        f"always-invalid raised={summary.get('h3c_always_invalid_raised')} "
        f"after {summary.get('h3c_always_invalid_invoke_calls')} attempts, "
        f"valid-attempt-1 single_invoke={summary.get('h3c_valid_single_invoke_calls')}; "
        f"gap1 brain argv0={summary.get('h3c_brain_argv0_seen')} "
        f"frontier={summary.get('h3c_brain_frontier')} "
        f"head_unchanged={summary.get('h3c_brain_head_unchanged')} "
        f"live_status_clean={summary.get('h3c_brain_live_status_clean')} "
        f"brain_map={summary.get('h3c_brain_map')}."
    )
    print(
        "H3d effective-write FIRE passed: "
        f"stamped work write_scope={summary.get('h3d_stamped_work_scope')} "
        f"closure_unstamped={summary.get('h3d_closure_unstamped')}; "
        f"stamped_effective_write={summary.get('h3d_stamped_effective_write')} "
        f"unstamped_effective_write={summary.get('h3d_unstamped_effective_write')} "
        f"pre_supplied_scope_unchanged={summary.get('h3d_pre_supplied_scope_unchanged')} "
        "(stamp is load-bearing; LIVE claude writing a file NOT proven here -- "
        "operator re-dogfoods)."
    )
    print(
        "proof limit: support evidence only; checker pass does not prove source truth, "
        "success judgment, quality judgment, Movement authority, real provider behavior, "
        "concurrency, or full process integrity."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

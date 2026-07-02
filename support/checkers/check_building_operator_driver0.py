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
import os
import subprocess
import sys
import tempfile

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
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


class _TemporaryHome:
    def __init__(self, root: Path):
        self.root = root
        self._old_home: str | None = None

    def __enter__(self) -> Path:
        self._old_home = os.environ.get("HOME")
        self.root.mkdir(parents=True, exist_ok=True)
        os.environ["HOME"] = str(self.root)
        return self.root

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._old_home


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
                "step_template_ref": "",
                "selected_adapter_ref": "adapter:local",
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


def _w1_completing_codex_runner(*, write: bool, delete_engine_marker: bool = False):
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
        if delete_engine_marker:
            try:
                (Path(cwd) / ".brick-engine-worktree").unlink()
            except FileNotFoundError:
                pass
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
        if not isinstance(surface, Mapping) or surface.get("allowed_values") != ["raise", "forward", "stop", "reroute"]:
            violations.append("budget: disposition_action surface did not expose raise/forward/stop/reroute")

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

    # Customer graph wrapper FIRE: fluent fan-in packets carry an engine-derived
    # required_return_shape on fan-in source nodes, and omitted output_root must
    # use the default buildings vessel without touching the live customer tree.
    _customer_graph_fluent_sandbox_fire(repo, violations, summary)

    # Thin fire(graph) sugar FIRE: operator-drawn GraphSpec launches through the
    # SAME customer graph sandbox route without caller-authored JSON packet files.
    _fire_graph_sugar_fire(repo, violations, summary)

    # H2a direct-graph intake FIRE (heart H2 deterministic plumbing): a
    # pre-composed graph + inline task_statement runs through the NEW
    # run_composed_graph_intake seam (NO preset) and produces an evidence spine
    # INDISTINGUISHABLE in validity from a preset run.
    _h2a_direct_graph_intake_fire(repo, violations, summary)

    # Lane1 launch safety: the already-composed launch helper must not let a
    # caller point adapter_cwd back at the live repo/customer tree.
    _launch_assembled_adapter_cwd_fire(repo, violations, summary)

    # P2 resume/approve isolation + explicit disposition FIRE: approve must not
    # silently supply disposition defaults, and post-HOLD resume must not run a
    # live adapter in the customer repo by accident.
    _resume_isolation_disposition_fire(repo, violations, summary)

    # P2 raw sensitive write observation FIRE: provider-session-like path writes
    # must be marked for downstream disposition/merge review evidence.
    _sensitive_write_observation_fire(violations, summary)

    return violations, summary


# ---------------------------------------------------------------------------
# Lane1 launch safety FIRE: launch_assembled_building runs inside the engine
# sandbox. A caller-supplied adapter_cwd that points at the live repo (self or
# child) must be refused before the composed plan is persisted or dispatched.
# ---------------------------------------------------------------------------


def _launch_assembled_adapter_cwd_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.assembly import Authority, assemble, brick, chain
    from brick_protocol.support.operator.onboard import launch_assembled_building

    called = {"value": False}

    def _runner(_args: Sequence[str], _cwd: Path, _timeout_seconds: int):
        called["value"] = True
        raise AssertionError("launch_assembled_building dispatched after adapter_cwd refusal")

    graph = assemble(
        chain([brick("closure", "Lane1 adapter_cwd refusal probe.")]),
        declared_by="coo",
        authority=Authority.COO,
        task="Refuse live repo adapter_cwd before launch dispatch.",
        building_id="lane1-adapter-cwd-refusal",
        adapter="codex-local",
        repo_root=repo,
    )
    result = launch_assembled_building(
        graph,
        repo_root=repo,
        adapter_cwd=repo,
        command_runner=_runner,
        adapter_timeout_seconds=30,
    )

    summary["launch_adapter_cwd_refusal_error"] = result.get("error_kind")
    summary["launch_adapter_cwd_refusal_ran"] = result.get("ran")
    summary["launch_adapter_cwd_refusal_dispatched"] = called["value"]
    summary["launch_adapter_cwd_refusal_plan_written"] = "plan_path" in result

    if result.get("error_kind") != "adapter_cwd_refused_live_repo":
        violations.append(
            "launch-adapter-cwd-RED: adapter_cwd=repo_root was not refused with "
            f"adapter_cwd_refused_live_repo; got {result.get('error_kind')!r}"
        )
    if result.get("ran") is not False:
        violations.append("launch-adapter-cwd-RED: refused launch reported ran != False")
    if called["value"]:
        violations.append("launch-adapter-cwd-RED: refusal still dispatched the adapter runner")
    if "plan_path" in result:
        violations.append("launch-adapter-cwd-RED: refusal wrote a composed plan before preflight")


def _resume_isolation_disposition_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator import onboard as onboard_module
    from brick_protocol.support.operator.onboard import run_approve_entry
    from brick_protocol.support.operator.run import _unsafe_resume_adapter_cwd

    missing_action = run_approve_entry(
        "p2-missing-action",
        author_ref="coo:smith",
        repo_root=repo,
    )
    missing_author = run_approve_entry(
        "p2-missing-author",
        action="forward",
        repo_root=repo,
    )
    summary["resume_missing_action_error"] = missing_action.get("error_kind")
    summary["resume_missing_author_error"] = missing_author.get("error_kind")
    if missing_action.get("error_kind") != "missing_disposition_action":
        violations.append("resume-disposition-RED: missing action did not fail closed")
    if missing_author.get("error_kind") != "missing_disposition_author":
        violations.append("resume-disposition-RED: missing author did not fail closed")

    held_frontier = {
        "frontier_kind": "link_paused",
        "latest_transition_lifecycle": {
            "transition_lifecycle_pending_target_ref": "brick-p2-held-work",
            "transition_lifecycle_paused_at_ref": "link-transition:p2-held",
        },
    }
    original_observe = onboard_module.observe_building_frontier
    onboard_module.observe_building_frontier = lambda *_args, **_kwargs: dict(held_frontier)
    try:
        with tempfile.TemporaryDirectory(prefix="bp-p2-resume-isolation-") as tmp:
            root = Path(tmp) / "building"
            missing_cwd = run_approve_entry(
                root,
                action="forward",
                author_ref="coo:smith",
                repo_root=repo,
            )
            live_cwd = run_approve_entry(
                root,
                action="forward",
                author_ref="coo:smith",
                adapter_cwd=repo,
                repo_root=repo,
            )
    finally:
        onboard_module.observe_building_frontier = original_observe
    summary["resume_missing_adapter_cwd_error"] = missing_cwd.get("error_kind")
    summary["resume_live_adapter_cwd_error"] = live_cwd.get("error_kind")
    if missing_cwd.get("error_kind") != "resume_requires_isolated_adapter_cwd":
        violations.append("resume-isolation-RED: missing adapter_cwd was not refused")
    if live_cwd.get("error_kind") != "adapter_cwd_refused_live_repo":
        violations.append("resume-isolation-RED: live repo adapter_cwd was not refused")

    direct_error = _unsafe_resume_adapter_cwd(repo, repo_root=repo)
    summary["resume_direct_live_adapter_cwd_refused"] = (
        "adapter_cwd_refused_live_repo" in direct_error
    )
    if "adapter_cwd_refused_live_repo" not in direct_error:
        violations.append("resume-isolation-RED: live repo adapter_cwd helper did not refuse")


def _sensitive_write_observation_fire(
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.operator.worktree_sandbox import (
        WorktreeSandboxError,
        anchor_wip_snapshot,
        commit_sandbox_output,
        create_worktree_sandbox,
        dispose_worktree_sandbox,
        probe_worktree_capable,
    )
    from brick_protocol.support.operator.write_observation import _raw_sensitive_path_writes

    observed = _raw_sensitive_path_writes(
        [
            "support/operator/run_chat_session.py",
            "logs/provider-session-state.json",
            "runs/conversation_id.txt",
            "nested/runtime-session/body.json",
            "ordinary/output.txt",
        ]
    )
    summary["sensitive_provider_session_paths"] = list(observed)
    expected = {
        "logs/provider-session-state.json",
        "runs/conversation_id.txt",
        "nested/runtime-session/body.json",
    }
    if not expected.issubset(set(observed)):
        violations.append(
            "sensitive-write-RED: provider-session-like paths were not marked "
            f"observed_sensitive_path_writes (observed={observed!r})"
        )
    if "support/operator/run_chat_session.py" in observed:
        violations.append(
            "sensitive-write-RED: ordinary source path run_chat_session.py was over-marked sensitive"
        )
    if "ordinary/output.txt" in observed:
        violations.append("sensitive-write-RED: ordinary output path was over-marked sensitive")

    with tempfile.TemporaryDirectory(prefix="bp-sensitive-commit-") as tmp_raw:
        tmp = Path(tmp_raw)
        home = tmp / "home"
        repo = tmp / "repo"
        repo.mkdir()
        (repo / "README.md").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, timeout=60)
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True, timeout=60)
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.name=customer",
                "-c",
                "user.email=customer@brick.local",
                "commit",
                "-q",
                "-m",
                "seed",
            ],
            check=True,
            timeout=60,
        )
        with _TemporaryHome(home):
            probe = probe_worktree_capable(repo)
            if not probe.ok:
                violations.append(
                    f"sensitive-commit-RED: temp repo was not worktree-capable ({probe.reason})"
                )
                return
            sandbox = create_worktree_sandbox(
                repo,
                building_id="sensitive-commit-red",
                base_sha=probe.base_sha,
            )
            try:
                (sandbox.path / ".env").write_text("redacted\n", encoding="utf-8")
                try:
                    commit_sandbox_output(sandbox, message="should not commit sensitive path")
                except WorktreeSandboxError as exc:
                    error_text = str(exc)
                else:
                    error_text = ""
                summary["sensitive_commit_blocked"] = bool(error_text)
                summary["sensitive_commit_error"] = error_text
                if "observed_sensitive_path_writes" not in error_text or ".env" not in error_text:
                    violations.append(
                        "sensitive-commit-RED: sandbox commit did not block .env with "
                        f"observed_sensitive_path_writes evidence (error={error_text!r})"
                    )
                staged = _git_text(sandbox.path, "diff", "--cached", "--name-only")
                summary["sensitive_commit_staged_paths"] = staged
                if staged:
                    violations.append(
                        "sensitive-commit-RED: sensitive path was staged before the commit block"
                    )
            finally:
                dispose_worktree_sandbox(sandbox)

            sandbox = create_worktree_sandbox(
                repo,
                building_id="sensitive-anchor-red",
                base_sha=probe.base_sha,
            )
            try:
                (sandbox.path / ".env").write_text("redacted\n", encoding="utf-8")
                try:
                    anchor_wip_snapshot(
                        sandbox,
                        "sensitive-anchor-red",
                        message="should not anchor sensitive path",
                    )
                except WorktreeSandboxError as exc:
                    anchor_error_text = str(exc)
                else:
                    anchor_error_text = ""
                summary["sensitive_anchor_red_execution_log"] = {
                    "attempted_wip_anchor": True,
                    "sensitive_path": ".env",
                    "blocked": bool(anchor_error_text),
                    "error": anchor_error_text,
                    "proof_limit": "mutation-RED support evidence only",
                }
                if (
                    "observed_sensitive_path_writes" not in anchor_error_text
                    or ".env" not in anchor_error_text
                ):
                    violations.append(
                        "sensitive-anchor-RED: WIP anchor did not block .env with "
                        f"observed_sensitive_path_writes evidence (error={anchor_error_text!r})"
                    )
                anchor_ref = _git_text(repo, "for-each-ref", "--format=%(refname)", "refs/brick/wip/")
                if "sensitive-anchor-red" in anchor_ref:
                    violations.append("sensitive-anchor-RED: sensitive WIP anchor ref was created")
            finally:
                dispose_worktree_sandbox(sandbox)


# ---------------------------------------------------------------------------
# Customer graph fluent sandbox FIRE: run_customer_graph_building_in_sandbox
# accepts the fluent assemble() fan-in packet's engine-derived
# required_return_shape, keeps non-fan-in customer overrides rejected, and uses
# DEFAULT_BUILDINGS_ROOT when output_root is omitted.
# ---------------------------------------------------------------------------


def _customer_graph_fluent_runner():
    def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int):
        from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

        del cwd, timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        payload = {
            "received_work_ref": "work:customer-graph-fluent",
            "made_changes": False,
            "changed_files": [],
            "commands_run": [],
            "blocked_or_missing_evidence": [],
            "handoff_refs": {},
            "observed_evidence": ["customer graph fluent sandbox checker ran"],
            "attacked_scope": "fluent fan-in guard",
            "brick_axis_findings": [],
            "agent_axis_findings": [],
            "link_axis_findings": [],
            "support_leak_findings": [],
            "projection_authority_findings": [],
            "evidence_scope": "fluent fan-in guard",
            "persisted_evidence_roots": [],
            "proof_limit_findings": [],
            "stale_source_risks": [],
            "checker_overclaim_risks": [],
            "missing_evidence": [],
            "evidence_used": [],
            "narrowly_proven": ["driver accepted fluent fan-in packet"],
            "remaining_delta": [],
            "parent_goal_delta_status": {"matched_delta_refs": [], "evidence_refs": []},
            "next_target_candidates": [],
            "deferred_smith_review_queue": [],
            "not_proven": ["semantic correctness of customer graph work"],
        }
        return LocalCliCompleted(call, 0, json.dumps(payload), "")

    return _runner


def _customer_graph_fluent_sandbox_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    import brick_protocol.support.operator.driver as driver
    from brick_protocol.support.operator.assembly import (
        Authority,
        assemble,
        build,
        fan,
    )

    with tempfile.TemporaryDirectory(prefix="bp-customer-graph-") as cust_raw, \
            tempfile.TemporaryDirectory(prefix="bp-customer-graph-default-") as out_raw, \
            _TemporaryHome(Path(cust_raw) / "engine-home"):
        customer = Path(cust_raw) / "customer-live"
        customer.mkdir(parents=True, exist_ok=True)
        head_before = _seed_customer_repo(repo, customer)
        default_root = Path(out_raw) / "default-buildings"
        old_default = driver.DEFAULT_BUILDINGS_ROOT
        driver.DEFAULT_BUILDINGS_ROOT = default_root
        try:
            graph = assemble(
                build(
                    [
                        ["work", "Prepare customer graph fluent fixture."],
                        fan(
                            [
                                [
                                    "axis-attack-qa",
                                    "Inspect fan-in branch A.",
                                    {"adapter": "codex-local"},
                                ],
                                [
                                    "evidence-integrity",
                                    "Inspect fan-in branch B.",
                                    {"adapter": "codex-local"},
                                ],
                            ]
                        ),
                        ["closure", "Close customer graph fluent fixture.", {"adapter": "codex-local"}],
                    ]
                ),
                declared_by="coo",
                authority=Authority.COO,
                task="Run fluent fan-in customer graph through the sandbox wrapper.",
                building_id="customer-graph-fluent-default",
                adapter="codex-local",
                repo_root=customer,
            )
            fan_in_sources = {
                str(edge.get("source"))
                for group in graph.groups
                if str(group.get("group_role")) == "fan_in"
                for ref in group.get("member_refs", ())
                for edge in graph.edges
                if str(edge.get("edge_ref")) == str(ref)
            }
            fan_in_shapes = {
                str(node.get("node_id")): str(node.get("required_return_shape"))
                for node in graph.nodes
                if str(node.get("node_id")) in fan_in_sources
            }
            summary["customer_graph_fluent_fan_in_shapes"] = fan_in_shapes
            if not fan_in_shapes or not any(
                "transition_concern_evidence" in shape for shape in fan_in_shapes.values()
            ):
                violations.append(
                    "customer-graph-fluent: assemble() did not preserve template-full "
                    "fan-in source required_return_shape"
                )

            result = driver.run_customer_graph_building_in_sandbox(
                graph,
                customer_repo_root=customer,
                overwrite_existing=True,
                command_runner=_customer_graph_fluent_runner(),
                adapter_timeout_seconds=30,
            )
        finally:
            driver.DEFAULT_BUILDINGS_ROOT = old_default

        summary["customer_graph_fluent_frontier"] = result.frontier_kind
        summary["customer_graph_fluent_evidence_root"] = result.evidence_root
        summary["customer_graph_fluent_default_root"] = str(default_root)
        if result.frontier_kind != "complete":
            violations.append(
                f"customer-graph-fluent: expected complete frontier, got {result.frontier_kind!r}"
            )
        if not _is_under(Path(result.evidence_root), default_root):
            violations.append(
                "customer-graph-fluent: omitted output_root did not use DEFAULT_BUILDINGS_ROOT"
            )
        if _git_text(customer, "rev-parse", "HEAD") != head_before:
            violations.append("customer-graph-fluent: live customer HEAD moved")
        if _git_text(customer, "status", "--porcelain", "--untracked-files=all") != "":
            violations.append("customer-graph-fluent: live customer tree was left dirty")

        def _required_return_shape_override_rejected(
            *,
            node_id: str,
            shape: str,
            building_id: str,
            summary_key: str,
            violation: str,
        ) -> None:
            forbidden_packet = graph.as_intake_args()
            forbidden_nodes = [dict(node) for node in forbidden_packet["nodes"]]
            for node in forbidden_nodes:
                if str(node.get("node_id")) == node_id:
                    node["required_return_shape"] = shape
                    break
            else:
                violations.append(f"{violation}: checker could not find node {node_id!r}")
                return
            forbidden_packet = dict(forbidden_packet)
            forbidden_packet["building_id"] = building_id
            forbidden_packet["nodes"] = forbidden_nodes
            try:
                driver.run_customer_graph_building_in_sandbox(
                    forbidden_packet,
                    customer_repo_root=customer,
                    output_root=default_root / building_id,
                    overwrite_existing=True,
                    command_runner=_customer_graph_fluent_runner(),
                    adapter_timeout_seconds=30,
                )
            except ValueError as exc:
                summary[summary_key] = "required_return_shape" in str(exc)
                if not summary[summary_key]:
                    violations.append(f"{violation}: rejection did not name required_return_shape")
            else:
                summary[summary_key] = False
                violations.append(violation)

        graph_nodes = [dict(node) for node in graph.as_intake_args()["nodes"]]
        _required_return_shape_override_rejected(
            node_id=str(graph_nodes[0].get("node_id")) if graph_nodes else "",
            shape="observed_evidence, not_proven",
            building_id="customer-graph-forbidden-required-return",
            summary_key="customer_graph_forbidden_override_rejected",
            violation="customer-graph-fluent-RED: non-fan-in required_return_shape override was accepted",
        )

        fan_in_tiny_node = next(iter(fan_in_shapes))
        _required_return_shape_override_rejected(
            node_id=fan_in_tiny_node,
            shape="observed_evidence, not_proven",
            building_id="customer-graph-forbidden-fanin-tiny-return",
            summary_key="customer_graph_forbidden_fanin_tiny_rejected",
            violation=(
                "customer-graph-fluent-RED: fan-in source required_return_shape shrink "
                "to observed_evidence, not_proven was accepted"
            ),
        )

        fan_in_without_concern = next(
            (
                (node_id, ", ".join(field.strip() for field in shape.split(",") if field.strip() != "transition_concern_evidence"))
                for node_id, shape in fan_in_shapes.items()
                if "transition_concern_evidence" in shape
            ),
            None,
        )
        if fan_in_without_concern is None:
            violations.append(
                "customer-graph-fluent-RED setup: no fan-in source carried template transition_concern_evidence"
            )
        else:
            _required_return_shape_override_rejected(
                node_id=fan_in_without_concern[0],
                shape=fan_in_without_concern[1],
                building_id="customer-graph-forbidden-fanin-no-concern-return",
                summary_key="customer_graph_forbidden_fanin_no_concern_rejected",
                violation=(
                    "customer-graph-fluent-RED: fan-in source manual "
                    "transition_concern_evidence removal was accepted"
                ),
            )


# ---------------------------------------------------------------------------
# Thin fire(graph) sugar FIRE: the P3 zero-ritual authoring surface accepts a
# drawn GraphSpec and fires it through the official customer graph sandbox route
# without requiring the caller to persist a graph JSON packet by hand.
# ---------------------------------------------------------------------------


def _fire_graph_sugar_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    import brick_protocol.support.operator.driver as driver
    from brick_protocol.support.operator.assembly import Authority, build, fan, fire

    with tempfile.TemporaryDirectory(prefix="bp-fire-graph-") as cust_raw, \
            tempfile.TemporaryDirectory(prefix="bp-fire-graph-default-") as out_raw, \
            _TemporaryHome(Path(cust_raw) / "engine-home"):
        customer = Path(cust_raw) / "customer-live"
        customer.mkdir(parents=True, exist_ok=True)
        head_before = _seed_customer_repo(repo, customer)
        default_root = Path(out_raw) / "default-buildings"
        old_default = driver.DEFAULT_BUILDINGS_ROOT
        driver.DEFAULT_BUILDINGS_ROOT = default_root
        try:
            result = fire(
                build(
                    [
                        ["work", "Prepare fire(graph) fixture."],
                        fan(
                            [
                                ["axis-attack-qa", "Inspect fire branch A.", {"adapter": "codex-local"}],
                                ["evidence-integrity", "Inspect fire branch B.", {"adapter": "codex-local"}],
                            ]
                        ),
                        ["closure", "Close fire(graph) fixture.", {"adapter": "codex-local"}],
                    ]
                ),
                declared_by="coo",
                authority=Authority.COO,
                task="Run a drawn graph through fire() without a caller JSON packet.",
                building_id="fire-graph-sugar-default",
                adapter="codex-local",
                repo_root=customer,
                overwrite_existing=True,
                command_runner=_customer_graph_fluent_runner(),
                adapter_timeout_seconds=30,
            )
        finally:
            driver.DEFAULT_BUILDINGS_ROOT = old_default

        summary["fire_graph_sugar_frontier"] = result.frontier_kind
        summary["fire_graph_sugar_evidence_root"] = result.evidence_root
        summary["fire_graph_sugar_default_root"] = str(default_root)
        summary["fire_graph_sugar_intake_plan"] = (
            str(result.intake_result.plan_path) if result.intake_result is not None else ""
        )
        if result.frontier_kind != "complete":
            violations.append(
                f"fire-graph-sugar: expected complete frontier, got {result.frontier_kind!r}"
            )
        if not _is_under(Path(result.evidence_root), default_root):
            violations.append("fire-graph-sugar: omitted output_root did not use DEFAULT_BUILDINGS_ROOT")
        if _git_text(customer, "rev-parse", "HEAD") != head_before:
            violations.append("fire-graph-sugar: live customer HEAD moved")
        if _git_text(customer, "status", "--porcelain", "--untracked-files=all") != "":
            violations.append("fire-graph-sugar: live customer tree was left dirty")


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
    from brick_protocol.support.operator.worktree_sandbox import (
        _ENGINE_WORKTREE_MARKER,
        _engine_worktrees_root,
        reclaim_wip_anchor,
        release_wip_anchor,
        reap_stale_wip_anchors,
        reap_stale_worktrees,
    )

    with tempfile.TemporaryDirectory(prefix="bp-w1-customer-") as cust_raw, \
            tempfile.TemporaryDirectory(prefix="bp-w1-evidence-") as ev_raw, \
            _TemporaryHome(Path(cust_raw) / "engine-home") as engine_home:
        # Each customer "repo" is its OWN subdir so the shared temp root is never
        # itself a git repo (otherwise a subdir whose .git we remove would still
        # resolve UP to the root repo and misreport its probe reason).
        customer = Path(cust_raw) / "customer-live"
        customer.mkdir(parents=True, exist_ok=True)
        evidence_root = Path(ev_raw)
        engine_root = _engine_worktrees_root()
        summary["w1_fixture_engine_root"] = str(engine_root)
        summary["w1_fixture_engine_root_isolated"] = _is_under(engine_root, engine_home)
        if not _is_under(engine_root, engine_home):
            violations.append(
                "w1-fixture-route-isolation: checker worktree root was not under temporary HOME"
            )

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

        # CASE 1b (stale liveness gate): stale reap touches only parseable
        # engine markers older than the threshold, and it runs inside the
        # checker's temporary HOME route. Fresh or unparseable marker bodies are
        # preserved so a stale sweep cannot delete uncertain work.
        old_marker = engine_root / "stale-old-marker"
        fresh_marker = engine_root / "stale-fresh-marker"
        bad_marker = engine_root / "stale-bad-marker"
        for marker_dir in (old_marker, fresh_marker, bad_marker):
            marker_dir.mkdir(parents=True, exist_ok=True)
        old_created = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
        fresh_created = datetime.now(timezone.utc).isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
        (old_marker / _ENGINE_WORKTREE_MARKER).write_text(
            "engine-created\n"
            f"repo_root={customer}\n"
            "building_id=stale-old-marker\n"
            f"base_sha={head_before}\n"
            f"created_at={old_created}\n",
            encoding="utf-8",
        )
        (fresh_marker / _ENGINE_WORKTREE_MARKER).write_text(
            "engine-created\n"
            f"repo_root={customer}\n"
            "building_id=stale-fresh-marker\n"
            f"base_sha={head_before}\n"
            f"created_at={fresh_created}\n",
            encoding="utf-8",
        )
        (bad_marker / _ENGINE_WORKTREE_MARKER).write_text(
            "engine-created\n"
            f"repo_root={customer}\n"
            "building_id=stale-bad-marker\n"
            f"base_sha={head_before}\n"
            "created_at=not-a-timestamp\n",
            encoding="utf-8",
        )
        reaped = reap_stale_worktrees(customer, stale_after_seconds=60 * 60)
        summary["w1_stale_reaped_paths"] = list(reaped)
        summary["w1_stale_old_removed"] = not old_marker.exists()
        summary["w1_stale_fresh_preserved"] = fresh_marker.exists()
        summary["w1_stale_bad_preserved"] = bad_marker.exists()
        if str(old_marker) not in reaped or old_marker.exists():
            violations.append("w1-stale-liveness: old parseable engine marker was not reaped")
        if not fresh_marker.exists():
            violations.append("w1-stale-liveness: fresh engine marker was reaped")
        if not bad_marker.exists():
            violations.append("w1-stale-liveness: unparseable engine marker did not fail closed")

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

        # CASE 2b (dirty host): a DIRTY git tree still hosts a detached worktree
        # at HEAD. The worktree boundary is the isolation; the live dirty tree
        # stays byte-for-byte in its pre-run dirty state.
        dirty = Path(cust_raw) / "customer-dirty"
        dirty.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, dirty)
        dirty_head_before = _git_text(dirty, "rev-parse", "HEAD")
        (dirty / "uncommitted.txt").write_text("dirty carry\n", encoding="utf-8")
        dirty_status_before = _git_text(dirty, "status", "--porcelain", "--untracked-files=all")
        dirty_result = run_customer_building_in_sandbox(
            _w1_intent("w1-dirty-worktree-0"),
            customer_repo_root=dirty,
            output_root=evidence_root / "dirty",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=True),
            adapter_timeout_seconds=30,
        )
        dirty_head_after = _git_text(dirty, "rev-parse", "HEAD")
        dirty_status_after = _git_text(dirty, "status", "--porcelain", "--untracked-files=all")
        summary["w1_dirty_mode"] = dirty_result.isolation_mode
        summary["w1_dirty_reason"] = dirty_result.isolation_reason
        summary["w1_dirty_base_sha"] = dirty_result.base_sha
        if dirty_result.isolation_mode != "worktree":
            violations.append(
                f"w1-dirty: expected worktree isolation over a dirty tree, got "
                f"{dirty_result.isolation_mode!r}"
            )
        if dirty_result.isolation_reason != "git-head-resolved":
            violations.append(
                f"w1-dirty: worktree reason drifted: {dirty_result.isolation_reason!r}"
            )
        if dirty_result.base_sha != dirty_head_before:
            violations.append(
                f"w1-dirty: worktree base did not pin HEAD "
                f"{dirty_head_before} (got {dirty_result.base_sha!r})"
            )
        if not dirty_result.worktree_path:
            violations.append("w1-dirty: no worktree path was recorded")
        if not dirty_result.commit_sha:
            violations.append("w1-dirty: completion over dirty host produced no worktree commit")
        if (
            (dirty / _W1_WRITE_REL).exists()
            or dirty_head_before != dirty_head_after
            or dirty_status_before != dirty_status_after
        ):
            violations.append("w1-dirty: the dirty customer tree was further mutated")

        # CASE 2c (active marker erased): a provider may delete the in-worktree
        # marker while still running inside the active engine-created worktree.
        # Disposal must still be safe because the active sandbox object plus
        # `git worktree list` prove the path; stale reaping remains marker-gated.
        marker_loss = Path(cust_raw) / "customer-marker-loss"
        marker_loss.mkdir(parents=True, exist_ok=True)
        marker_head_before = _seed_customer_repo(repo, marker_loss)
        marker_result = run_customer_building_in_sandbox(
            _w1_intent("w1-active-marker-loss-0"),
            customer_repo_root=marker_loss,
            output_root=evidence_root / "marker-loss",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=True, delete_engine_marker=True),
            adapter_timeout_seconds=30,
        )
        marker_head_after = _git_text(marker_loss, "rev-parse", "HEAD")
        marker_status_after = _git_text(marker_loss, "status", "--porcelain", "--untracked-files=all")
        summary["w1_marker_loss_mode"] = marker_result.isolation_mode
        summary["w1_marker_loss_disposed"] = marker_result.worktree_disposed
        summary["w1_marker_loss_worktree_exists"] = (
            bool(marker_result.worktree_path) and Path(marker_result.worktree_path).exists()
        )
        if marker_result.isolation_mode != "worktree":
            violations.append(
                f"w1-marker-loss: expected worktree isolation, got {marker_result.isolation_mode!r}"
            )
        if not marker_result.worktree_disposed or summary["w1_marker_loss_worktree_exists"]:
            violations.append("w1-marker-loss: active worktree was not disposed after marker loss")
        if not marker_result.commit_sha:
            violations.append("w1-marker-loss: completion after marker loss produced no commit")
        if (
            (marker_loss / _W1_WRITE_REL).exists()
            or marker_head_before != marker_head_after
            or marker_status_after != ""
        ):
            violations.append("w1-marker-loss: the live customer tree was mutated")

        # CASE 3 (incomplete = WIP anchor, no completion commit): a building
        # that does NOT complete produces no completion commit, but provider WIP
        # is pinned under refs/brick/wip/* before dispose.
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
        summary["w1_incomplete_wip_anchor_ref"] = incomplete.wip_anchor_ref
        summary["w1_incomplete_wip_commit_sha"] = incomplete.wip_commit_sha
        if incomplete.frontier_kind == "complete":
            violations.append("w1-incomplete: a non-completing building reported a complete frontier")
        if incomplete.commit_sha:
            violations.append(
                f"w1-incomplete: a non-completing building produced a commit {incomplete.commit_sha}"
            )
        if not incomplete.wip_anchor_ref.startswith("refs/brick/wip/"):
            violations.append(
                f"w1-incomplete: WIP anchor ref used an unadmitted namespace "
                f"{incomplete.wip_anchor_ref!r}"
            )
        if not incomplete.wip_commit_sha:
            violations.append("w1-incomplete: non-complete provider WIP was not pinned")
        else:
            anchor_type = _git_text(customer3, "cat-file", "-t", incomplete.wip_commit_sha)
            summary["w1_incomplete_wip_commit_type"] = anchor_type
            if anchor_type != "commit":
                violations.append("w1-incomplete: WIP commit did not survive worktree disposal")
            anchor_files = _git_text(
                customer3,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                incomplete.wip_commit_sha,
            )
            summary["w1_incomplete_wip_commit_files"] = anchor_files
            if anchor_files != _W1_WRITE_REL:
                violations.append(
                    f"w1-incomplete: WIP anchor did not capture exactly {_W1_WRITE_REL}: "
                    f"{anchor_files!r}"
                )
            branch_contains_wip = _git_text(
                customer3, "branch", "--contains", incomplete.wip_commit_sha
            )
            if branch_contains_wip:
                violations.append(
                    "w1-incomplete: WIP anchor moved or landed on a branch "
                    f"{branch_contains_wip!r}"
                )
        reclaimed = reclaim_wip_anchor(customer3, "w1-incomplete-no-commit-0")
        summary["w1_incomplete_reclaimed_anchor"] = reclaimed[0] if reclaimed else ""
        summary["w1_incomplete_reclaimed_commit"] = reclaimed[1] if reclaimed else ""
        if reclaimed != (incomplete.wip_anchor_ref, incomplete.wip_commit_sha):
            violations.append(
                "w1-incomplete: reclaim_wip_anchor did not return the recorded anchor/commit"
            )
        release_wip_anchor(customer3, "w1-incomplete-no-commit-0")
        released = reclaim_wip_anchor(customer3, "w1-incomplete-no-commit-0")
        summary["w1_incomplete_release_cleared"] = released is None
        if released is not None:
            violations.append("w1-incomplete: release_wip_anchor did not clear the WIP ref")
        if head3_before != head3_after or status3_after != "":
            violations.append("w1-incomplete: the live tree was mutated by a held building")

        old_wip_customer = Path(cust_raw) / "customer-old-wip"
        old_wip_customer.mkdir(parents=True, exist_ok=True)
        old_wip_base = _seed_customer_repo(repo, old_wip_customer)
        old_wip_ref = "refs/brick/wip/stale-anchor"
        old_wip_sha = _git_text(
            old_wip_customer,
            "-c",
            "user.name=brick-engine",
            "-c",
            "user.email=engine@brick.local",
            "commit-tree",
            f"{old_wip_base}^{{tree}}",
            "-p",
            old_wip_base,
            "-m",
            "stale WIP anchor",
        )
        if old_wip_sha:
            _git_text(old_wip_customer, "update-ref", old_wip_ref, old_wip_sha)
            reaped_wip = reap_stale_wip_anchors(old_wip_customer, stale_after_seconds=-1)
            summary["w1_stale_wip_reaped_refs"] = list(reaped_wip)
            if old_wip_ref not in reaped_wip:
                violations.append("w1-stale-wip-anchor: old refs/brick/wip anchor was not reaped")
        else:
            violations.append("w1-stale-wip-anchor: could not create stale WIP fixture commit")

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
        summary["w1_mutation_red_execution_log"] = {
            "bypassed_wrapper": True,
            "adapter_cwd_was_live_repo": True,
            "head_moved": head4_before != head4_after,
            "status_after": status4_after,
            "write_landed_in_live_tree": (customer4 / _W1_WRITE_REL).exists(),
            "bypass_dirtied_live_tree": bypass_left_live_tree_dirty,
            "proof_limit": "mutation-RED support evidence only",
        }
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
        f"dirty-worktree mode={summary.get('w1_dirty_mode')} reason={summary.get('w1_dirty_reason')} "
        f"base={summary.get('w1_dirty_base_sha')}; "
        f"fixture_root_isolated={summary.get('w1_fixture_engine_root_isolated')} "
        f"stale_old_removed={summary.get('w1_stale_old_removed')} "
        f"stale_fresh_preserved={summary.get('w1_stale_fresh_preserved')} "
        f"stale_bad_preserved={summary.get('w1_stale_bad_preserved')}; "
        f"incomplete frontier={summary.get('w1_incomplete_frontier')} "
        f"commit={summary.get('w1_incomplete_commit')!r} "
        f"wip_anchor={summary.get('w1_incomplete_wip_anchor_ref')!r} "
        f"wip_commit={summary.get('w1_incomplete_wip_commit_sha')!r} "
        f"release_cleared={summary.get('w1_incomplete_release_cleared')} "
        f"stale_wip_reaped={summary.get('w1_stale_wip_reaped_refs')}; "
        f"mutation-RED bypass_dirtied_live_tree={summary.get('w1_mutation_bypass_dirtied_live_tree')} "
        f"execution_log={summary.get('w1_mutation_red_execution_log')}; "
        f"sensitive_anchor_RED={summary.get('sensitive_anchor_red_execution_log')}."
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
        "fire(graph) sugar FIRE passed: "
        f"frontier={summary.get('fire_graph_sugar_frontier')} "
        f"evidence_root={summary.get('fire_graph_sugar_evidence_root')} "
        f"default_root={summary.get('fire_graph_sugar_default_root')} "
        f"plan={summary.get('fire_graph_sugar_intake_plan')}."
    )
    print(
        "Lane1 launch adapter_cwd FIRE passed: "
        f"error={summary.get('launch_adapter_cwd_refusal_error')} "
        f"ran={summary.get('launch_adapter_cwd_refusal_ran')} "
        f"dispatched={summary.get('launch_adapter_cwd_refusal_dispatched')} "
        f"plan_written={summary.get('launch_adapter_cwd_refusal_plan_written')}."
    )
    print(
        "P2 resume isolation/disposition FIRE passed: "
        f"missing_action={summary.get('resume_missing_action_error')} "
        f"missing_author={summary.get('resume_missing_author_error')} "
        f"missing_cwd={summary.get('resume_missing_adapter_cwd_error')} "
        f"live_cwd={summary.get('resume_live_adapter_cwd_error')} "
        f"direct_refused={summary.get('resume_direct_live_adapter_cwd_refused')} "
        f"sensitive_paths={summary.get('sensitive_provider_session_paths')}."
    )
    print(
        "proof limit: support evidence only; checker pass does not prove source truth, "
        "success judgment, quality judgment, Movement authority, real provider behavior, "
        "concurrency, or full process integrity."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

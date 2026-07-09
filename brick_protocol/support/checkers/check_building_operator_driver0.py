#!/usr/bin/env python3
"""Check BUILDING-OPERATOR-DRIVER-0 bounded portfolio driver invariants.

This checker is support evidence only. It runs the admitted
brick_protocol/support/operator/driver.py over adapter:local deterministic fixtures. It does
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
import time

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from brick_protocol.support.checkers.lib.bootstrap import ensure_checker_imports

ensure_checker_imports(_REPO_ROOT)

from brick_protocol.support.checkers.lib.checker_temp_vessel import checker_temp_path


def _repo_root_from_arg(repo: str | None) -> Path:
    if repo:
        return Path(repo).resolve()
    return Path(__file__).resolve().parents[3]


def _ensure_import_path(repo: Path) -> None:
    ensure_checker_imports(repo)


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
    from brick_protocol.support.checkers.lib.case_runners import _graph_test_plan_from_linear

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
# These cases drive the REAL brick_protocol/support/operator/driver.run_customer_building_in_sandbox
# wrapper. They never call a real provider: a deterministic command_runner stands
# in for codex, writing the in-scope file into the dispatch cwd and returning a
# completing AgentFact. The "customer repo" is a FRESH /tmp git repo seeded with
# THIS repo's HEAD via `git archive` (so it carries the Brick template catalog a
# real customer install would have); it is NEVER nested inside the live tree.
# ---------------------------------------------------------------------------

_W1_WRITE_REL = "onboarding-example/fix.txt"
_W1_WRITE_SCOPE: dict[str, Any] = {
    "allowed_paths": ["onboarding-example/**"],
    "forbidden_paths": [".git/**", "AGENTS.md", "brick_protocol/agent/**", "brick_protocol/brick/**", "brick_protocol/link/**",
                        "brick_protocol/support/**", "project/**", "**/.env"],
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


def _jsonl_records(path: Path) -> tuple[Mapping[str, Any], ...]:
    if not path.is_file():
        return ()
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
    return tuple(records)


# The minimal working-tree surfaces a customer install needs for the catalog +
# plan materialization the wrapper exercises. Copying from the WORKING TREE (not
# `git archive`) keeps this FIRE independent of whether the repo under test is a
# git checkout (a clean `git archive` overlay tree is NOT a git repo), so the
# proof never REDs on an environment artifact.
_W1_SEED_DIRS: tuple[str, ...] = ("brick_protocol",)
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


def _w1_completing_codex_runner(
    *,
    write: bool,
    delete_engine_marker: bool = False,
    write_rel: str = _W1_WRITE_REL,
    extra_write_rels: Sequence[str] = (),
):
    """A deterministic stand-in for codex. Optionally writes the in-scope file
    into the dispatch cwd, then returns a completing AgentFact JSON."""

    def _runner(args: Sequence[str], cwd: Path, timeout_seconds: int):
        from brick_protocol.support.connection.agent_adapter import LocalCliCompleted

        del timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        if write:
            for rel in (write_rel, *extra_write_rels):
                target = Path(cwd) / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("fixed by the W1 FIRE runner\n", encoding="utf-8")
        if delete_engine_marker:
            try:
                (Path(cwd) / ".brick-engine-worktree").unlink()
            except FileNotFoundError:
                pass
        payload = {
            "observed_evidence": [f"wrote {write_rel}" if write else "observed no file write"],
            "changed_files": [write_rel] if write else [],
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
    with checker_temp_path("bp-d2-driver0-") as tmp:

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
        from brick_protocol.support.operator.portfolio_projection import (
            portfolio_projection_with_hold_guidance,
            write_portfolio_projection_with_hold_guidance,
        )

        budget_guidance_projection = portfolio_projection_with_hold_guidance(
            budget_result.projection
        )
        budget_guidance_path = write_portfolio_projection_with_hold_guidance(
            budget_result.projection_path
        )
        budget_written_guidance_projection = json.loads(
            budget_guidance_path.read_text(encoding="utf-8")
        )
        budget_frontier = budget_result.projection["frontier"]
        budget_guidance_frontier = budget_guidance_projection["frontier"]
        budget_written_guidance_frontier = budget_written_guidance_projection["frontier"]
        summary["budget_frontier"] = budget_frontier
        summary["budget_guidance_frontier"] = budget_guidance_frontier
        summary["budget_guidance_projection_path"] = str(budget_guidance_path)
        if budget_result.frontier_kind != "link_paused":
            violations.append(f"budget: expected link_paused frontier, got {budget_result.frontier_kind}")
        lifecycle = budget_frontier.get("latest_transition_lifecycle", {})
        if not isinstance(lifecycle, Mapping) or lifecycle.get("transition_lifecycle_pending_target_ref") != b2:
            violations.append("budget: paused frontier did not carry pending second Building")
        surface = budget_frontier.get("disposition_action_surface", {})
        if not isinstance(surface, Mapping) or surface.get("allowed_values") != ["raise", "forward", "stop", "reroute"]:
            violations.append("budget: disposition_action surface did not expose raise/forward/stop/reroute")
        if budget_guidance_frontier.get("not_resumable_by") != ["forward"]:
            violations.append("budget: projection guidance did not publish not_resumable_by=['forward']")
        if budget_written_guidance_frontier.get("not_resumable_by") != ["forward"]:
            violations.append(
                "budget: written projection guidance did not publish not_resumable_by=['forward']"
            )
        reroute_guidance = budget_guidance_frontier.get("reroute_guidance")
        if not isinstance(reroute_guidance, str) or "declared portfolio candidate set" not in reroute_guidance:
            violations.append("budget: projection guidance did not publish declared-candidate reroute wording")
        written_reroute_guidance = budget_written_guidance_frontier.get("reroute_guidance")
        if (
            not isinstance(written_reroute_guidance, str)
            or "declared portfolio candidate set" not in written_reroute_guidance
        ):
            violations.append(
                "budget: written projection guidance did not publish declared-candidate reroute wording"
            )

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

    # R3 fan-death detection FIRE: a silent fan child must hit the adapter-timeout
    # deadline, write raw dispatch_child_timeout evidence, and surface a COO-owned
    # loud HOLD instead of waiting for the child indefinitely.
    _fan_dispatch_child_timeout_fire(repo, violations, summary)
    _fan_dispatch_slow_normal_child_no_false_hold_fire(repo, violations, summary)

    # D1 park-stop WIP anchor + launch dirty-cwd observation FIRE: a direct
    # adapter_cwd walk that PARKS/STOPS before a clean result must still anchor
    # the worktree's dirty bytes under refs/brick/wip/<building_id> (the
    # completion-time anchor never runs on the early-exit path), and a
    # pre-existing dirty adapter_cwd must be WARNED (observation-only) at launch.
    _park_stop_anchor_and_launch_dirty_fire(repo, violations, summary)

    return violations, summary


# ---------------------------------------------------------------------------


def _fan_dispatch_child_timeout_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator.frontier_observation import observe_building_frontier
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.support.checkers.lib.preset_completion_fixture import (
        _preset_completion_command_runner,
        _preset_completion_prompt_from_cli_args,
    )
    from brick_protocol.support.checkers.lib.step_output_drain_check import _dynamic_step_output_drain_plan
    from brick_protocol.support.operator import walker_kernel

    plan = json.loads(json.dumps(_dynamic_step_output_drain_plan(missing=False)))
    plan["building_id"] = "checker-fan-dispatch-child-timeout"
    plan["plan_ref"] = "building-plan:checker-fan-dispatch-child-timeout"
    plan["selected_adapter_ref"] = "adapter:codex-local"
    for step in plan.get("brick_steps", []):
        if isinstance(step, dict):
            step["selected_adapter_ref"] = "adapter:codex-local"
            step["selected_model_ref"] = "model:codex:default"
            if step.get("step_ref") == "fan-axis-qa":
                _set_graph_step_work_statement(
                    step,
                    "fan-axis-qa silent child timeout fixture; the command_runner "
                    "must not return before the adapter timeout.",
                )

    complete_runner = _preset_completion_command_runner(LocalCliCompleted)

    def _timeout_runner(args: Sequence[str], cwd: Path, timeout_seconds: int, **_kwargs: Any) -> Any:
        prompt = _preset_completion_prompt_from_cli_args(tuple(str(arg) for arg in args))
        try:
            prompt_packet = json.loads(prompt)
        except json.JSONDecodeError:
            prompt_packet = {}
        work_statement = (
            str(prompt_packet.get("work_statement") or "")
            if isinstance(prompt_packet, Mapping)
            else ""
        )
        if "fan-axis-qa" in work_statement:
            time.sleep(timeout_seconds + 1.5)
            raise TimeoutError("silent child fixture exceeded adapter timeout")
        return complete_runner(args, cwd, timeout_seconds)

    default_join_seconds = walker_kernel._adapter_timeout_join_seconds(1)
    original_floor = walker_kernel._ADAPTER_TIMEOUT_JOIN_MARGIN_FLOOR_SECONDS
    walker_kernel._ADAPTER_TIMEOUT_JOIN_MARGIN_FLOOR_SECONDS = 0.25
    try:
        with checker_temp_path("bp-fan-child-timeout-") as output_root:
            started = time.monotonic()
            result = run_building_plan(
                plan,
                output_root=output_root,
                overwrite_existing=True,
                command_runner=_timeout_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=1,
            )
            elapsed = time.monotonic() - started
            root = result.lifecycle_write.root
            # Let the timed-out worker unwind after the main walk has already held;
            # this keeps the in-process checker deterministic without trusting it as
            # process-integrity proof.
            time.sleep(0.75)
            timeout_records = _jsonl_records(root / "raw" / "dispatch-child-timeout.jsonl")
            adapter_error_records = _jsonl_records(root / "raw" / "adapter-error.jsonl")
            link_records = _jsonl_records(root / "raw" / "link.jsonl")
            frontier = observe_building_frontier(root)
    finally:
        walker_kernel._ADAPTER_TIMEOUT_JOIN_MARGIN_FLOOR_SECONDS = original_floor

    hold_records = [
        record
        for record in link_records
        if "fan_dispatch_child_unresponsive"
        in json.dumps(record.get("transition_lifecycle_reason_refs", []))
    ]
    summary["fan_dispatch_child_timeout_elapsed_seconds"] = round(elapsed, 3)
    summary["fan_dispatch_child_timeout_records"] = len(timeout_records)
    summary["fan_dispatch_child_timeout_frontier"] = frontier.get("frontier_kind")
    summary["fan_dispatch_child_timeout_hold_owner"] = (
        hold_records[-1].get("transition_lifecycle_required_disposition_owner")
        if hold_records
        else ""
    )
    summary["fan_dispatch_child_timeout_adapter_error_kind"] = (
        adapter_error_records[-1].get("error_kind") if adapter_error_records else ""
    )
    summary["fan_dispatch_child_timeout_mutation_red_execution_log"] = {
        "silent_child_step_ref": "fan-axis-qa",
        "adapter_timeout_seconds": 1,
        "default_join_seconds": round(default_join_seconds, 3),
        "checker_join_seconds": round(1 + 0.25, 3),
        "elapsed_seconds": round(elapsed, 3),
        "timeout_raw_rows": len(timeout_records),
        "hold_rows": len(hold_records),
        "proof_limit": "mutation-RED support evidence only",
    }
    if default_join_seconds < 31.0:
        violations.append(
            "fan-dispatch-child-timeout margin-RED: production join margin floor "
            "was removed or lowered below adapter_timeout_seconds + 30s"
        )
    # LOAD-AGNOSTIC judgment (Smith 0706-evening: no wall-clock ceilings, redesign
    # to evidence-shape). Whether the join returned "near adapter_timeout" instead
    # of waiting for the silent child forever is judged by the EVIDENCE the deadline
    # firing leaves behind, not by an `elapsed` wall-clock literal (which flaked
    # under load AND self-contradicted: the deterministic 1.25s join + ~1.2s
    # unwind/record cost exceeds any tight ceiling). The mutation that removes the
    # production deadline (walker waits forever) produces NEITHER a dispatch_child_
    # timeout raw row NOR an agent_incomplete frontier NOR a coo HOLD — so the four
    # evidence checks below ARE the mutation-RED discriminator. This block only
    # asserts the deadline actually bounded the wait: the child never returned a
    # completed step result (no fabricated success), proven load-agnostically.
    slow_wait_bounded = bool(timeout_records) and frontier.get("frontier_kind") == "agent_incomplete"
    if not slow_wait_bounded:
        violations.append(
            "fan-dispatch-child-timeout mutation-RED: fan walk did not bound the "
            "silent-child wait with a timeout (no dispatch_child_timeout evidence "
            "and/or no agent_incomplete frontier) — deadline did not fire"
        )
    if frontier.get("frontier_kind") != "agent_incomplete":
        violations.append(
            "fan-dispatch-child-timeout: timeout did not surface an agent_incomplete frontier"
        )
    if not timeout_records:
        violations.append("fan-dispatch-child-timeout: raw dispatch_child_timeout evidence missing")
    if not adapter_error_records or adapter_error_records[-1].get("error_kind") != "dispatch_child_timeout":
        violations.append("fan-dispatch-child-timeout: adapter-error row did not preserve timeout kind")
    if not hold_records:
        violations.append("fan-dispatch-child-timeout: paused lifecycle row with fan_dispatch_child_unresponsive missing")
    elif hold_records[-1].get("transition_lifecycle_required_disposition_owner") != "coo":
        violations.append("fan-dispatch-child-timeout: HOLD owner was not coo")


def _fan_dispatch_slow_normal_child_no_false_hold_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator.frontier_observation import observe_building_frontier
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.support.checkers.lib.preset_completion_fixture import (
        _preset_completion_command_runner,
        _preset_completion_prompt_from_cli_args,
    )
    from brick_protocol.support.checkers.lib.step_output_drain_check import _dynamic_step_output_drain_plan
    from brick_protocol.support.operator import walker_kernel

    plan = json.loads(json.dumps(_dynamic_step_output_drain_plan(missing=False)))
    plan["building_id"] = "checker-fan-dispatch-slow-normal-child"
    plan["plan_ref"] = "building-plan:checker-fan-dispatch-slow-normal-child"
    plan["selected_adapter_ref"] = "adapter:codex-local"
    for step in plan.get("brick_steps", []):
        if isinstance(step, dict):
            step["selected_adapter_ref"] = "adapter:codex-local"
            step["selected_model_ref"] = "model:codex:default"
            if step.get("step_ref") == "fan-axis-qa":
                _set_graph_step_work_statement(
                    step,
                    "fan-axis-qa slow normal child margin fixture; the command_runner "
                    "returns after adapter_timeout_seconds but before the outer join margin.",
                )

    complete_runner = _preset_completion_command_runner(LocalCliCompleted)
    slow_branch_hits = 0

    def _slow_normal_runner(args: Sequence[str], cwd: Path, timeout_seconds: int, **_kwargs: Any) -> Any:
        nonlocal slow_branch_hits
        prompt = _preset_completion_prompt_from_cli_args(tuple(str(arg) for arg in args))
        try:
            prompt_packet = json.loads(prompt)
        except json.JSONDecodeError:
            prompt_packet = {}
        work_statement = (
            str(prompt_packet.get("work_statement") or "")
            if isinstance(prompt_packet, Mapping)
            else ""
        )
        if "slow normal child margin fixture" in work_statement:
            slow_branch_hits += 1
            time.sleep(timeout_seconds + 0.12)
        return complete_runner(args, cwd, timeout_seconds)

    default_join_seconds = walker_kernel._adapter_timeout_join_seconds(1)
    original_floor = walker_kernel._ADAPTER_TIMEOUT_JOIN_MARGIN_FLOOR_SECONDS
    walker_kernel._ADAPTER_TIMEOUT_JOIN_MARGIN_FLOOR_SECONDS = 0.25
    try:
        with checker_temp_path("bp-fan-slow-normal-") as output_root:
            started = time.monotonic()
            result = run_building_plan(
                plan,
                output_root=output_root,
                overwrite_existing=True,
                command_runner=_slow_normal_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=1,
            )
            elapsed = time.monotonic() - started
            root = result.lifecycle_write.root
            timeout_records = _jsonl_records(root / "raw" / "dispatch-child-timeout.jsonl")
            adapter_error_records = _jsonl_records(root / "raw" / "adapter-error.jsonl")
            link_records = _jsonl_records(root / "raw" / "link.jsonl")
            frontier = observe_building_frontier(root)
    finally:
        walker_kernel._ADAPTER_TIMEOUT_JOIN_MARGIN_FLOOR_SECONDS = original_floor

    hold_records = [
        record
        for record in link_records
        if "fan_dispatch_child_unresponsive"
        in json.dumps(record.get("transition_lifecycle_reason_refs", []))
    ]
    summary["fan_dispatch_slow_normal_elapsed_seconds"] = round(elapsed, 3)
    summary["fan_dispatch_slow_normal_branch_hits"] = slow_branch_hits
    summary["fan_dispatch_slow_normal_timeout_records"] = len(timeout_records)
    summary["fan_dispatch_slow_normal_frontier"] = frontier.get("frontier_kind")
    summary["fan_dispatch_slow_normal_margin_removal_mutation_red_execution_log"] = {
        "slow_child_step_ref": "fan-axis-qa",
        "adapter_timeout_seconds": 1,
        "default_join_seconds": round(default_join_seconds, 3),
        "checker_join_seconds": round(1 + 0.25, 3),
        "elapsed_seconds": round(elapsed, 3),
        "slow_branch_hits": slow_branch_hits,
        "timeout_raw_rows": len(timeout_records),
        "hold_rows": len(hold_records),
        "proof_limit": "mutation-RED support evidence only",
    }
    if default_join_seconds < 31.0:
        violations.append(
            "fan-dispatch-slow-normal margin-RED: production join margin floor "
            "was removed or lowered below adapter_timeout_seconds + 30s"
        )
    if slow_branch_hits != 1:
        violations.append("fan-dispatch-slow-normal: slow child fixture branch did not execute exactly once")
    if frontier.get("frontier_kind") != "complete":
        violations.append("fan-dispatch-slow-normal: slow normal child did not complete")
    if timeout_records:
        violations.append("fan-dispatch-slow-normal: slow normal child was mis-recorded as dispatch_child_timeout")
    if adapter_error_records:
        violations.append("fan-dispatch-slow-normal: slow normal child produced adapter-error evidence")
    if hold_records:
        violations.append("fan-dispatch-slow-normal: slow normal child produced fan_dispatch_child_unresponsive HOLD")


def _set_graph_step_work_statement(step: dict[str, Any], work_statement: str) -> None:
    for row in step.get("rows", []):
        if isinstance(row, dict) and row.get("axis") == "Brick":
            row["work_statement"] = work_statement
            return
    raise ValueError("checker fan dispatch fixture step missing Brick row")


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

    missing_re_instruction = run_approve_entry(
        "p2-missing-re-instruction",
        action="reroute",
        author_ref="human:smith",
        reroute_target_ref="brick:p2-reroute-target",
        repo_root=repo,
    )
    summary["resume_missing_re_instruction_error"] = missing_re_instruction.get("error_kind")
    if missing_re_instruction.get("error_kind") != "missing_re_instruction":
        violations.append(
            "resume-disposition-RED: human reroute without re_instruction did not fail closed"
        )
    invalid_re_instruction = run_approve_entry(
        "p2-invalid-re-instruction",
        action="reroute",
        author_ref="human:smith",
        reroute_target_ref="brick:p2-reroute-target",
        re_instruction=(
            "Retry against the explicit reroute target and prove the result with "
            "focused checks only."
        ),
        repo_root=repo,
    )
    summary["resume_invalid_re_instruction_error"] = invalid_re_instruction.get("error_kind")
    if invalid_re_instruction.get("error_kind") != "re_instruction_endline_rule_violation":
        violations.append(
            "resume-disposition-RED: invalid reroute re_instruction did not fail closed"
        )

    held_frontier = {
        "frontier_kind": "link_paused",
        "latest_transition_lifecycle": {
            "transition_lifecycle_pending_target_ref": "brick-p2-held-work",
            "transition_lifecycle_paused_at_ref": "link-transition:p2-held",
        },
    }
    original_observe = onboard_module.observe_building_frontier
    original_prepare_cwd = onboard_module._prepare_resume_adapter_cwd
    onboard_module.observe_building_frontier = lambda *_args, **_kwargs: dict(held_frontier)
    try:
        with checker_temp_path("bp-p2-resume-isolation-") as tmp:
            root = tmp / "building"
            (root / "raw").mkdir(parents=True)
            (root / "work").mkdir()
            auto_cwd = tmp / "auto-adapter-cwd"
            auto_cwd.mkdir()

            def _fake_prepare_cwd(*, repo_root, building_id, adapter_cwd):
                if adapter_cwd is None:
                    return auto_cwd, {
                        "adapter_cwd_auto_created": True,
                        "adapter_cwd_source": "checker_fake_worktree",
                    }
                return original_prepare_cwd(
                    repo_root=repo_root,
                    building_id=building_id,
                    adapter_cwd=adapter_cwd,
                )

            onboard_module._prepare_resume_adapter_cwd = _fake_prepare_cwd
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
            reroute_with_instruction = run_approve_entry(
                root,
                action="reroute",
                author_ref="human:smith",
                reroute_target_ref="brick:p2-reroute-target",
                re_instruction=(
                    "Done endline: retry against the explicit reroute target and "
                    "return the declared evidence before DONE. Proof must be "
                    "executable in the receiving lane. Repairs outside the "
                    "receiving lane's scope are COO gate items, not re-dispatch."
                ),
                repo_root=repo,
            )
    finally:
        onboard_module.observe_building_frontier = original_observe
        onboard_module._prepare_resume_adapter_cwd = original_prepare_cwd
    summary["resume_missing_adapter_cwd_error"] = missing_cwd.get("error_kind")
    summary["resume_live_adapter_cwd_error"] = live_cwd.get("error_kind")
    summary["resume_reroute_with_instruction_error"] = reroute_with_instruction.get(
        "error_kind"
    )
    if missing_cwd.get("error_kind") == "resume_requires_isolated_adapter_cwd":
        violations.append("resume-isolation-RED: missing adapter_cwd was still refused")
    if missing_cwd.get("adapter_cwd_auto_created") is not True:
        violations.append("resume-isolation-RED: missing adapter_cwd did not auto-create")
    if live_cwd.get("error_kind") != "adapter_cwd_refused_live_repo":
        violations.append("resume-isolation-RED: live repo adapter_cwd was not refused")
    if reroute_with_instruction.get("error_kind") == "resume_requires_isolated_adapter_cwd":
        violations.append(
            "resume-disposition: reroute with re_instruction did not pass to later "
            f"resume preflight ({reroute_with_instruction.get('error_kind')!r})"
        )

    def write_held_dynamic_manifest(
        root: Path,
        *,
        hold_reason: str,
        budget_exhausted: bool = False,
    ) -> None:
        (root / "evidence").mkdir(parents=True, exist_ok=True)
        (root / "raw").mkdir(parents=True, exist_ok=True)
        plan = {
            "plan_ref": "building-plan:resume-menu-fixture",
            "dynamic_walker_evidence": {
                "walker_mode": "dynamic",
                "held": True,
                "hold": {
                    "hold_reason": hold_reason,
                    "budget_exhausted": budget_exhausted,
                    "pending_target_ref": "brick-p2-held-work",
                    "paused_at_ref": "link-transition:p2-held",
                    "source_step_ref": "p2-source",
                },
            },
        }
        manifest = {
            "plan_snapshot": {
                "plan_rows_copy": json.dumps(plan, separators=(",", ":")),
            },
        }
        (root / "evidence" / "evidence-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    original_observe = onboard_module.observe_building_frontier
    try:
        with checker_temp_path("bp-p2-resume-menu-") as menu_root:
            budget_root = menu_root / "budget"
            adapter_root = menu_root / "adapter"
            write_held_dynamic_manifest(
                budget_root,
                hold_reason="target_node_budget_exhausted",
                budget_exhausted=True,
            )
            write_held_dynamic_manifest(
                adapter_root,
                hold_reason="adapter_error_frontier",
            )
            onboard_module.observe_building_frontier = lambda *_args, **_kwargs: dict(held_frontier)
            budget_forward = run_approve_entry(
                budget_root,
                action="forward",
                author_ref="coo:smith",
                repo_root=repo,
            )
            adapter_agent_incomplete_frontier = {
                "frontier_kind": "agent_incomplete",
                "frontier_reason": "adapter_error_frontier",
            }
            onboard_module.observe_building_frontier = (
                lambda *_args, **_kwargs: dict(adapter_agent_incomplete_frontier)
            )
            adapter_raise = run_approve_entry(
                adapter_root,
                action="raise",
                author_ref="coo:smith",
                budget_increment=1,
                repo_root=repo,
            )
            adapter_stop = run_approve_entry(
                adapter_root,
                action="stop",
                author_ref="coo:smith",
                repo_root=repo,
            )
    finally:
        onboard_module.observe_building_frontier = original_observe
    summary["resume_budget_forward_error"] = budget_forward.get("error_kind")
    summary["resume_budget_forward_allowed"] = budget_forward.get("allowed_disposition_actions")
    summary["resume_adapter_raise_error"] = adapter_raise.get("error_kind")
    summary["resume_adapter_raise_allowed"] = adapter_raise.get("allowed_disposition_actions")
    summary["resume_adapter_stop_error"] = adapter_stop.get("error_kind")
    summary["resume_adapter_stop_approval_hold_source"] = adapter_stop.get("approval_hold_source")
    if budget_forward.get("error_kind") != "invalid_disposition_for_hold":
        violations.append("resume-menu-RED: budget-exhaustion forward was not refused")
    if budget_forward.get("allowed_disposition_actions") != ["raise", "stop", "reroute"]:
        violations.append("resume-menu-RED: budget-exhaustion menu did not publish raise/stop/reroute")
    if adapter_raise.get("error_kind") != "invalid_disposition_for_hold":
        violations.append("resume-menu-RED: adapter-error raise was not refused")
    if adapter_raise.get("allowed_disposition_actions") != ["stop"]:
        violations.append("resume-menu-RED: adapter-error menu did not publish stop-only")
    if adapter_stop.get("error_kind") != "resume_requires_isolated_adapter_cwd":
        violations.append(
            "resume-menu: adapter-error stop did not pass to later adapter_cwd guard "
            f"({adapter_stop.get('error_kind')!r})"
        )
    if adapter_stop.get("approval_hold_source") != "dynamic_walker_evidence.adapter_error_frontier":
        violations.append(
            "resume-menu: adapter-error agent_incomplete frontier did not use dynamic HOLD evidence"
        )

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
            "brick_protocol/support/operator/run_chat_session.py",
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
    if "brick_protocol/support/operator/run_chat_session.py" in observed:
        violations.append(
            "sensitive-write-RED: ordinary source path run_chat_session.py was over-marked sensitive"
        )
    if "ordinary/output.txt" in observed:
        violations.append("sensitive-write-RED: ordinary output path was over-marked sensitive")

    with checker_temp_path("bp-sensitive-commit-") as tmp:
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

        del timeout_seconds
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return LocalCliCompleted(call, 0, "codex test-version", "")
        write_rel = "customer-graph-fluent-output.txt"
        target = Path(cwd) / write_rel
        target.write_text("customer graph fluent sandbox checker output\n", encoding="utf-8")
        payload = {
            "received_work_ref": "work:customer-graph-fluent",
            "made_changes": True,
            "changed_files": [write_rel],
            "commands_run": [f"write {write_rel}"],
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

    with checker_temp_path("bp-h2a-intake-") as tmp:

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
        _LAND_FORCE_COMMIT_ABSENT_REASON,
        _WRITE_SCOPE_FORBIDDEN_DIFF_PRESENT_REASON,
        _WRITE_SCOPE_OUTSIDE_DIFF_PRESENT_REASON,
        _write_need_complete_with_outside_scope_diff,
        _write_need_complete_with_forbidden_diff,
        _write_need_complete_without_scoped_diff,
        run_building_intake,
        run_customer_building_in_sandbox,
    )
    from brick_protocol.support.operator import driver as driver_module
    from brick_protocol.support.operator import run as run_module
    from brick_protocol.support.operator.building_operation import observe_building_frontier
    from brick_protocol.support.operator.onboard import run_approve_entry
    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref
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
        # N1 mutation-RED: complete+dirty cannot fall through to silent WIP-only
        # if the land-force commit primitive produces no commit SHA.
        land_absent = Path(cust_raw) / "customer-land-force-absent"
        land_absent.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, land_absent)
        original_commit_sandbox_output = driver_module.commit_sandbox_output
        driver_module.commit_sandbox_output = lambda *_args, **_kwargs: ""
        try:
            land_absent_result = run_customer_building_in_sandbox(
                _w1_intent("w1-land-force-commit-absent-0"),
                customer_repo_root=land_absent,
                output_root=evidence_root / "land-force-commit-absent",
                overwrite_existing=True,
                command_runner=_w1_completing_codex_runner(write=True),
                adapter_timeout_seconds=30,
            )
        finally:
            driver_module.commit_sandbox_output = original_commit_sandbox_output
        land_absent_reobserved = observe_building_frontier(
            land_absent_result.evidence_root,
            repo_root=land_absent,
        )
        land_absent_link_records = _jsonl_records(
            Path(land_absent_result.evidence_root) / "raw" / "link.jsonl"
        )
        land_absent_hold_rows = [
            record
            for record in land_absent_link_records
            if record.get("hold_reason") == _LAND_FORCE_COMMIT_ABSENT_REASON
        ]
        summary["w1_land_force_absent_frontier"] = land_absent_result.frontier_kind
        summary["w1_land_force_absent_reason"] = land_absent_result.frontier_reason
        summary["w1_land_force_absent_commit"] = land_absent_result.commit_sha
        summary["w1_land_force_absent_wip_anchor"] = land_absent_result.wip_anchor_ref
        summary["w1_land_force_absent_hold_row_count"] = len(land_absent_hold_rows)
        if land_absent_result.frontier_kind != "human_review_waiting":
            violations.append(
                "w1-land-force-absent: complete+dirty with absent commit stayed "
                f"{land_absent_result.frontier_kind!r}"
            )
        if land_absent_result.frontier_reason != _LAND_FORCE_COMMIT_ABSENT_REASON:
            violations.append(
                "w1-land-force-absent: absent commit did not surface land-force reason "
                f"(reason={land_absent_result.frontier_reason!r})"
            )
        if land_absent_result.commit_sha:
            violations.append("w1-land-force-absent: absent commit probe produced a commit")
        if land_absent_reobserved.get("frontier_kind") != "human_review_waiting":
            violations.append(
                "w1-land-force-absent: durable frontier did not reobserve the HOLD "
                f"(frontier={land_absent_reobserved.get('frontier_kind')!r})"
            )
        if not land_absent_hold_rows:
            violations.append("w1-land-force-absent: land-force HOLD row was not persisted")

        # N1 real exception branch: a complete write-needed plan with in-scope
        # dirty bytes can still be blocked by the raw sensitive-path commit
        # guard. That must return a loud hold, not crash in the later WIP anchor.
        land_sensitive = Path(cust_raw) / "customer-land-force-sensitive"
        land_sensitive.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, land_sensitive)
        land_sensitive_result = run_customer_building_in_sandbox(
            _w1_intent("w1-land-force-sensitive-0"),
            customer_repo_root=land_sensitive,
            output_root=evidence_root / "land-force-sensitive",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(
                write=True,
                extra_write_rels=("onboarding-example/provider-session-state.json",),
            ),
            adapter_timeout_seconds=30,
        )
        land_sensitive_link_records = _jsonl_records(
            Path(land_sensitive_result.evidence_root) / "raw" / "link.jsonl"
        )
        land_sensitive_hold_rows = [
            record
            for record in land_sensitive_link_records
            if record.get("hold_reason") == _LAND_FORCE_COMMIT_ABSENT_REASON
        ]
        summary["w1_land_force_sensitive_frontier"] = land_sensitive_result.frontier_kind
        summary["w1_land_force_sensitive_reason"] = land_sensitive_result.frontier_reason
        summary["w1_land_force_sensitive_commit"] = land_sensitive_result.commit_sha
        summary["w1_land_force_sensitive_wip_anchor"] = land_sensitive_result.wip_anchor_ref
        summary["w1_land_force_sensitive_disposed"] = land_sensitive_result.worktree_disposed
        summary["w1_land_force_sensitive_hold_row_count"] = len(land_sensitive_hold_rows)
        if land_sensitive_result.frontier_kind != "human_review_waiting":
            violations.append(
                "w1-land-force-sensitive: commit exception did not return a loud hold "
                f"(frontier={land_sensitive_result.frontier_kind!r})"
            )
        if land_sensitive_result.frontier_reason != _LAND_FORCE_COMMIT_ABSENT_REASON:
            violations.append(
                "w1-land-force-sensitive: commit exception did not surface land-force reason "
                f"(reason={land_sensitive_result.frontier_reason!r})"
            )
        if land_sensitive_result.commit_sha:
            violations.append("w1-land-force-sensitive: sensitive commit unexpectedly landed")
        if land_sensitive_result.wip_anchor_ref:
            violations.append(
                "w1-land-force-sensitive: land-force commit absence fell through to WIP anchor"
            )
        if not land_sensitive_result.worktree_disposed:
            violations.append("w1-land-force-sensitive: worktree was not disposed after hold")
        if not land_sensitive_hold_rows:
            violations.append("w1-land-force-sensitive: land-force HOLD row was not persisted")
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

        # D2 read-only exemption: a declared plan with zero write-need rows is
        # outside the fake-landing gate even when the sandbox has no diff.
        read_only_plan = evidence_root / "read-only-plan.json"
        read_only_plan.write_text(
            json.dumps(
                {
                    "brick_steps": [
                        {
                            "step_ref": "read-only-development",
                            "rows": [
                                {
                                    "axis": "Brick",
                                    "requires_brick_write_scope": False,
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        read_only_gate_fired = _write_need_complete_without_scoped_diff(
            customer,
            read_only_plan,
        )
        summary["w1_read_only_fake_landing_gate_fired"] = read_only_gate_fired
        if read_only_gate_fired:
            violations.append("w1-read-only: zero-write-need plan triggered the fake-landing gate")

        # D3(a): probe-write QA lenses are write-scope-capable because their
        # normal product is probe evidence; net-zero source diff must not fire
        # the product fake-landing gate.
        probe_write_plan = evidence_root / "probe-write-plan.json"
        probe_write_plan.write_text(
            json.dumps(
                {
                    "brick_steps": [
                        {
                            "step_ref": "read-only-graph-qa-lens",
                            "rows": [
                                {
                                    "axis": "Brick",
                                    "requires_brick_write_scope": True,
                                    "capability_class": "probe_write",
                                    "write_scope": {
                                        "allowed_paths": ["."],
                                        "forbidden_paths": [],
                                    },
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        source_write_plan = evidence_root / "source-write-plan.json"
        source_write_plan.write_text(
            json.dumps(
                {
                    "brick_steps": [
                        {
                            "step_ref": "source-write-work",
                            "rows": [
                                {
                                    "axis": "Brick",
                                    "requires_brick_write_scope": True,
                                    "capability_class": "source_write",
                                    "write_scope": dict(_W1_WRITE_SCOPE),
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        probe_write_gate_fired = _write_need_complete_without_scoped_diff(
            customer,
            probe_write_plan,
        )
        summary["w1_probe_write_fake_landing_gate_fired"] = probe_write_gate_fired
        if probe_write_gate_fired:
            violations.append("w1-probe-write: probe-write plan triggered the fake-landing gate")

        mixed_probe = Path(cust_raw) / "customer-mixed-probe"
        mixed_probe.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, mixed_probe)
        (mixed_probe / _W1_WRITE_REL).parent.mkdir(parents=True, exist_ok=True)
        (mixed_probe / _W1_WRITE_REL).write_text("allowed fixture bytes\n", encoding="utf-8")
        (mixed_probe / "AGENTS.md").write_text("forbidden fixture bytes\n", encoding="utf-8")
        mixed_forbidden_gate_fired = _write_need_complete_with_forbidden_diff(
            mixed_probe,
            probe_write_plan,
        )
        summary["w1_probe_write_forbidden_gate_fired"] = mixed_forbidden_gate_fired
        if mixed_forbidden_gate_fired:
            violations.append("w1-probe-write: probe-write plan triggered the forbidden-diff gate")

        outside_probe = Path(cust_raw) / "customer-outside-probe"
        outside_probe.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, outside_probe)
        (outside_probe / _W1_WRITE_REL).parent.mkdir(parents=True, exist_ok=True)
        (outside_probe / _W1_WRITE_REL).write_text("allowed fixture bytes\n", encoding="utf-8")
        (outside_probe / "README.md").write_text("outside fixture bytes\n", encoding="utf-8")
        outside_scope_gate_fired = _write_need_complete_with_outside_scope_diff(
            outside_probe,
            source_write_plan,
        )
        summary["w1_probe_write_outside_scope_gate_fired"] = outside_scope_gate_fired
        if not outside_scope_gate_fired:
            violations.append("w1-outside-scope: allowed+outside source-write diff did not fire")
        outside_scope_probe_gate_fired = _write_need_complete_with_outside_scope_diff(
            outside_probe,
            probe_write_plan,
        )
        summary["w1_probe_write_outside_scope_probe_gate_fired"] = outside_scope_probe_gate_fired
        if outside_scope_probe_gate_fired:
            violations.append("w1-probe-write: probe-write plan triggered the outside-scope gate")

        # D1 fake-landing gate: a write-needed Building that reports a complete
        # frontier without any scoped sandbox diff is held on the existing human
        # review surface, so no empty completion commit lands.
        fake_empty = Path(cust_raw) / "customer-fake-empty"
        fake_empty.mkdir(parents=True, exist_ok=True)
        fake_empty_head_before = _seed_customer_repo(repo, fake_empty)
        fake_empty_result = run_customer_building_in_sandbox(
            _w1_intent("w1-fake-empty-write-0"),
            customer_repo_root=fake_empty,
            output_root=evidence_root / "fake-empty",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=False),
            adapter_timeout_seconds=30,
        )
        fake_empty_head_after = _git_text(fake_empty, "rev-parse", "HEAD")
        summary["w1_fake_empty_frontier"] = fake_empty_result.frontier_kind
        summary["w1_fake_empty_frontier_reason"] = fake_empty_result.frontier_reason
        summary["w1_fake_empty_commit"] = fake_empty_result.commit_sha
        summary["w1_fake_empty_wip_anchor"] = fake_empty_result.wip_anchor_ref
        fake_empty_reobserved = observe_building_frontier(
            fake_empty_result.evidence_root,
            repo_root=fake_empty,
        )
        fake_empty_link_records = _jsonl_records(
            Path(fake_empty_result.evidence_root) / "raw" / "link.jsonl"
        )
        fake_empty_hold_rows = [
            record
            for record in fake_empty_link_records
            if record.get("hold_reason") == "fake_landing_write_scope_diff_absent"
        ]
        summary["w1_fake_empty_reobserved_frontier"] = fake_empty_reobserved.get(
            "frontier_kind"
        )
        summary["w1_fake_empty_hold_row_count"] = len(fake_empty_hold_rows)
        if fake_empty_result.frontier_kind != "human_review_waiting":
            violations.append(
                "w1-fake-empty: write-needed complete-without-diff did not hold "
                f"(frontier={fake_empty_result.frontier_kind!r})"
            )
        if fake_empty_result.frontier_reason != "fake_landing_write_scope_diff_absent":
            violations.append(
                "w1-fake-empty: hold did not surface fake landing frontier_reason "
                f"(reason={fake_empty_result.frontier_reason!r})"
            )
        if fake_empty_result.commit_sha:
            violations.append("w1-fake-empty: empty fake landing produced a completion commit")
        if fake_empty_head_before != fake_empty_head_after:
            violations.append("w1-fake-empty: fake landing moved the customer HEAD")
        if fake_empty_reobserved.get("frontier_kind") != "human_review_waiting":
            violations.append(
                "w1-fake-empty: durable frontier re-observation did not match the hold "
                f"(frontier={fake_empty_reobserved.get('frontier_kind')!r})"
            )
        if not fake_empty_hold_rows:
            violations.append("w1-fake-empty: fake landing hold row was not persisted")
        else:
            fake_empty_hold = fake_empty_hold_rows[-1]
            if fake_empty_hold.get("transition_lifecycle_state") != "paused":
                violations.append(
                    "w1-fake-empty: fake landing hold row did not carry paused lifecycle"
                )
            fake_empty_paused_at_ref = str(
                fake_empty_hold.get("transition_lifecycle_paused_at_ref") or ""
            )
            fake_empty_expected_ref = _hold_paused_at_ref(fake_empty_hold)
            summary["w1_fake_empty_paused_at_ref"] = fake_empty_paused_at_ref
            summary["w1_fake_empty_expected_paused_at_ref"] = fake_empty_expected_ref
            if not fake_empty_paused_at_ref:
                violations.append(
                    "w1-fake-empty: fake landing hold row did not carry paused_at_ref"
                )
            elif fake_empty_paused_at_ref != fake_empty_expected_ref:
                violations.append(
                    "w1-fake-empty: fake landing paused_at_ref did not match hold identity "
                    f"{fake_empty_expected_ref!r}: {fake_empty_paused_at_ref!r}"
                )
            if fake_empty_reobserved.get("latest_transition_lifecycle", {}).get(
                "transition_lifecycle_paused_at_ref"
            ) != fake_empty_expected_ref:
                violations.append(
                    "w1-fake-empty: frontier did not publish the fake landing hold identity"
                )

            fake_empty_link_path = (
                Path(fake_empty_result.evidence_root) / "raw" / "link.jsonl"
            )
            fake_empty_link_records = list(_jsonl_records(fake_empty_link_path))
            fake_empty_original_link_records = [
                dict(record) for record in fake_empty_link_records
            ]
            for record in reversed(fake_empty_link_records):
                if record.get("hold_reason") == "fake_landing_write_scope_diff_absent":
                    record.pop("transition_lifecycle_paused_at_ref", None)
                    break
            fake_empty_link_path.write_text(
                "\n".join(
                    json.dumps(record, separators=(",", ":"), ensure_ascii=False)
                    for record in fake_empty_link_records
                )
                + "\n",
                encoding="utf-8",
            )
            try:
                with checker_temp_path("bp-w1-missing-paused-at-") as missing_raw:
                    missing_identity = run_approve_entry(
                        fake_empty_result.evidence_root,
                        action="forward",
                        author_ref="coo:d2-checker",
                        adapter_cwd=missing_raw,
                        adapter_timeout_seconds=30,
                        repo_root=fake_empty,
                    )
            finally:
                fake_empty_link_path.write_text(
                    "\n".join(
                        json.dumps(
                            record,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        )
                        for record in fake_empty_original_link_records
                    )
                    + "\n",
                    encoding="utf-8",
                )
            summary["w1_fake_missing_paused_at_error"] = missing_identity.get(
                "error_kind"
            )
            if missing_identity.get("error_kind") != "missing_paused_at_ref":
                violations.append(
                    "w1-fake-missing-paused-at-RED: missing fake-landing paused_at_ref "
                    f"was not refused (error={missing_identity.get('error_kind')!r})"
                )

            original_resume_building_plan = run_module.resume_building_plan

            def _resume_with_w1_runner(building_root: Path | str, **kwargs: Any):
                kwargs["command_runner"] = _w1_completing_codex_runner(write=True)
                return original_resume_building_plan(building_root, **kwargs)

            run_module.resume_building_plan = _resume_with_w1_runner
            try:
                with checker_temp_path("bp-w1-fake-resume-") as resume_cwd:
                    _seed_customer_repo(repo, resume_cwd)
                    resume_target = resume_cwd / _W1_WRITE_REL
                    resume_target.parent.mkdir(parents=True, exist_ok=True)
                    resume_target.write_text(
                        "fixed by the W1 forward disposition fixture\n",
                        encoding="utf-8",
                    )
                    forward_disposition = run_approve_entry(
                        fake_empty_result.evidence_root,
                        action="forward",
                        author_ref="coo:d2-checker",
                        adapter_cwd=resume_cwd,
                        adapter_timeout_seconds=30,
                        repo_root=fake_empty,
                    )
                    summary["w1_fake_empty_forward_wrote_file"] = (
                        resume_target
                    ).is_file()
            finally:
                run_module.resume_building_plan = original_resume_building_plan
            summary["w1_fake_empty_forward_error"] = forward_disposition.get("error_kind")
            summary["w1_fake_empty_forward_frontier"] = forward_disposition.get(
                "frontier_kind"
            )
            summary["w1_fake_empty_forward_disposition_written"] = (
                forward_disposition.get("disposition_written")
            )
            if forward_disposition.get("error_kind") == "missing_paused_at_ref":
                violations.append(
                    "w1-fake-empty: forward disposition still failed missing_paused_at_ref"
                )
            if forward_disposition.get("frontier_kind") != "complete":
                violations.append(
                    "w1-fake-empty: forward disposition did not close the resumed boundary "
                    f"(frontier={forward_disposition.get('frontier_kind')!r}, "
                    f"error={forward_disposition.get('error_kind')!r}, "
                    f"message={forward_disposition.get('error_message')!r})"
                )
            if not summary["w1_fake_empty_forward_wrote_file"]:
                violations.append(
                    "w1-fake-empty: resumed forward disposition had no in-scope bytes"
                )

        # D1 out-of-scope variant: when bytes exist but none are inside the
        # declared write_scope, the same hold path preserves them under WIP.
        fake_outside = Path(cust_raw) / "customer-fake-outside"
        fake_outside.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, fake_outside)
        outside_rel = "outside-scope.txt"
        fake_outside_result = run_customer_building_in_sandbox(
            _w1_intent("w1-fake-outside-write-0"),
            customer_repo_root=fake_outside,
            output_root=evidence_root / "fake-outside",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(
                write=True,
                write_rel=outside_rel,
            ),
            adapter_timeout_seconds=30,
        )
        summary["w1_fake_outside_frontier"] = fake_outside_result.frontier_kind
        summary["w1_fake_outside_frontier_reason"] = fake_outside_result.frontier_reason
        summary["w1_fake_outside_commit"] = fake_outside_result.commit_sha
        summary["w1_fake_outside_wip_anchor"] = fake_outside_result.wip_anchor_ref
        summary["w1_fake_outside_wip_commit"] = fake_outside_result.wip_commit_sha
        if fake_outside_result.frontier_kind != "human_review_waiting":
            violations.append(
                "w1-fake-outside: out-of-scope-only diff did not hold "
                f"(frontier={fake_outside_result.frontier_kind!r})"
            )
        if fake_outside_result.commit_sha:
            violations.append("w1-fake-outside: out-of-scope-only fake landing produced a completion commit")
        if not fake_outside_result.wip_commit_sha:
            violations.append("w1-fake-outside: out-of-scope WIP bytes were not pinned")
        else:
            fake_wip_files = _git_text(
                fake_outside,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                fake_outside_result.wip_commit_sha,
            )
            summary["w1_fake_outside_wip_files"] = fake_wip_files
            if fake_wip_files != outside_rel:
                violations.append(
                    "w1-fake-outside: WIP anchor did not preserve the out-of-scope diff "
                    f"{outside_rel!r}: {fake_wip_files!r}"
                )

        fake_mixed = Path(cust_raw) / "customer-fake-mixed"
        fake_mixed.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, fake_mixed)
        fake_mixed_result = run_customer_building_in_sandbox(
            _w1_intent("w1-fake-mixed-write-0"),
            customer_repo_root=fake_mixed,
            output_root=evidence_root / "fake-mixed",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(
                write=True,
                extra_write_rels=("AGENTS.md",),
            ),
            adapter_timeout_seconds=30,
        )
        fake_mixed_link_records = _jsonl_records(
            Path(fake_mixed_result.evidence_root) / "raw" / "link.jsonl"
        )
        fake_mixed_hold_rows = [
            record
            for record in fake_mixed_link_records
            if record.get("hold_reason") == _WRITE_SCOPE_FORBIDDEN_DIFF_PRESENT_REASON
        ]
        summary["w1_fake_mixed_frontier"] = fake_mixed_result.frontier_kind
        summary["w1_fake_mixed_reason"] = fake_mixed_result.frontier_reason
        summary["w1_fake_mixed_commit"] = fake_mixed_result.commit_sha
        summary["w1_fake_mixed_hold_row_count"] = len(fake_mixed_hold_rows)
        if fake_mixed_result.frontier_kind != "human_review_waiting":
            violations.append(
                "w1-fake-mixed: allowed+forbidden diff did not hold "
                f"(frontier={fake_mixed_result.frontier_kind!r})"
            )
        if fake_mixed_result.frontier_reason != _WRITE_SCOPE_FORBIDDEN_DIFF_PRESENT_REASON:
            violations.append(
                "w1-fake-mixed: hold did not surface forbidden-diff reason "
                f"(reason={fake_mixed_result.frontier_reason!r})"
            )
        if fake_mixed_result.commit_sha:
            violations.append("w1-fake-mixed: forbidden mixed diff produced a completion commit")
        if not fake_mixed_hold_rows:
            violations.append("w1-fake-mixed: forbidden-diff hold row was not persisted")

        fake_allowed_outside = Path(cust_raw) / "customer-fake-allowed-outside"
        fake_allowed_outside.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, fake_allowed_outside)
        fake_allowed_outside_result = run_customer_building_in_sandbox(
            _w1_intent("w1-fake-allowed-outside-write-0"),
            customer_repo_root=fake_allowed_outside,
            output_root=evidence_root / "fake-allowed-outside",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(
                write=True,
                extra_write_rels=("README.md",),
            ),
            adapter_timeout_seconds=30,
        )
        fake_allowed_outside_link_records = _jsonl_records(
            Path(fake_allowed_outside_result.evidence_root) / "raw" / "link.jsonl"
        )
        fake_allowed_outside_hold_rows = [
            record
            for record in fake_allowed_outside_link_records
            if record.get("hold_reason") == _WRITE_SCOPE_OUTSIDE_DIFF_PRESENT_REASON
        ]
        fake_allowed_outside_support_authored_rows = [
            record
            for record in fake_allowed_outside_link_records
            if record.get("transition_author_ref") == "support:operator-driver"
        ]
        fake_allowed_outside_gate_authored_rows = [
            record
            for record in fake_allowed_outside_hold_rows
            if record.get("transition_author_ref") == "link-gate:coo"
        ]
        fake_allowed_outside_observation_refs = [
            ref
            for record in fake_allowed_outside_hold_rows
            for ref in record.get("reason_refs", ())
            if isinstance(ref, str)
            and ref.startswith("observation:observed_paths_outside_declared_scope:")
        ]
        fake_allowed_outside_gate_consumptions = [
            record.get("gate_consumption_evidence")
            for record in fake_allowed_outside_hold_rows
            if isinstance(record.get("gate_consumption_evidence"), Mapping)
            and record["gate_consumption_evidence"].get("gate_ref") == "link-gate:coo"
            and record["gate_consumption_evidence"].get("sufficiency")
            == "missing_required_facts"
            and "Link.route_decision_basis.override_refs"
            in record["gate_consumption_evidence"].get("missing_required_facts", ())
            and isinstance(
                record["gate_consumption_evidence"].get("checked_public_fact"),
                str,
            )
            and record["gate_consumption_evidence"]["checked_public_fact"].startswith(
                "observation:observed_paths_outside_declared_scope:"
            )
            and record["gate_consumption_evidence"].get("evidence_reference")
            == record["gate_consumption_evidence"].get("checked_public_fact")
        ]
        summary["w1_fake_allowed_outside_frontier"] = fake_allowed_outside_result.frontier_kind
        summary["w1_fake_allowed_outside_reason"] = fake_allowed_outside_result.frontier_reason
        summary["w1_fake_allowed_outside_commit"] = fake_allowed_outside_result.commit_sha
        summary["w1_fake_allowed_outside_hold_row_count"] = len(fake_allowed_outside_hold_rows)
        summary["w1_fake_allowed_outside_support_authored_row_count"] = len(
            fake_allowed_outside_support_authored_rows
        )
        summary["w1_fake_allowed_outside_gate_authored_row_count"] = len(
            fake_allowed_outside_gate_authored_rows
        )
        summary["w1_fake_allowed_outside_observation_ref_count"] = len(
            fake_allowed_outside_observation_refs
        )
        summary["w1_fake_allowed_outside_gate_consumption_count"] = len(
            fake_allowed_outside_gate_consumptions
        )
        if fake_allowed_outside_result.frontier_kind != "human_review_waiting":
            violations.append(
                "w1-fake-allowed-outside: allowed+outside diff did not hold "
                f"(frontier={fake_allowed_outside_result.frontier_kind!r})"
            )
        if fake_allowed_outside_result.frontier_reason != _WRITE_SCOPE_OUTSIDE_DIFF_PRESENT_REASON:
            violations.append(
                "w1-fake-allowed-outside: hold did not surface outside-scope reason "
                f"(reason={fake_allowed_outside_result.frontier_reason!r})"
            )
        if fake_allowed_outside_result.commit_sha:
            violations.append(
                "w1-fake-allowed-outside: allowed+outside diff produced a completion commit"
            )
        if not fake_allowed_outside_hold_rows:
            violations.append("w1-fake-allowed-outside: outside-scope hold row was not persisted")
        if fake_allowed_outside_support_authored_rows:
            violations.append(
                "w1-fake-allowed-outside: support-authored Link hold rows were persisted"
            )
        if not fake_allowed_outside_gate_authored_rows:
            violations.append(
                "w1-fake-allowed-outside: declared Link gate author evidence was not persisted"
            )
        if not fake_allowed_outside_observation_refs:
            violations.append(
                "w1-fake-allowed-outside: support outside-scope observation ref was not preserved"
            )
        if not fake_allowed_outside_gate_consumptions:
            violations.append(
                "w1-fake-allowed-outside: declared Link gate consumption evidence was not persisted"
            )

        with checker_temp_path("bp-w1-no-diff-forward-") as no_diff_raw:
            no_diff_forward = run_approve_entry(
                fake_empty_result.evidence_root,
                action="forward",
                author_ref="coo:d2-checker",
                adapter_cwd=no_diff_raw,
                adapter_timeout_seconds=30,
                repo_root=fake_empty,
            )
        no_diff_reobserved = observe_building_frontier(
            fake_empty_result.evidence_root,
            repo_root=fake_empty,
        )
        summary["w1_fake_no_diff_forward_frontier"] = no_diff_forward.get("frontier_kind")
        summary["w1_fake_no_diff_forward_reason"] = no_diff_forward.get("frontier_reason")
        summary["w1_fake_no_diff_forward_reobserved_frontier"] = no_diff_reobserved.get(
            "frontier_kind"
        )
        no_diff_link_records = _jsonl_records(
            Path(fake_empty_result.evidence_root) / "raw" / "link.jsonl"
        )
        no_diff_basis_rows = [
            record
            for record in no_diff_link_records
            if record.get("transition_lifecycle_disposition_action") == "forward"
            and "override:fake_landing_write_scope_diff_absent"
            in record.get("route_decision_override_refs", [])
        ]
        summary["w1_fake_no_diff_forward_basis_row_count"] = len(no_diff_basis_rows)
        if no_diff_forward.get("frontier_kind") != "complete":
            violations.append(
                "w1-fake-no-diff-forward: recorded forward disposition did not suppress "
                f"fake-landing re-hold (frontier={no_diff_forward.get('frontier_kind')!r}, "
                f"error={no_diff_forward.get('error_kind')!r})"
            )
        if no_diff_reobserved.get("frontier_kind") != "complete":
            violations.append(
                "w1-fake-no-diff-forward: durable frontier re-observation did not stay "
                f"complete (frontier={no_diff_reobserved.get('frontier_kind')!r})"
            )
        if not no_diff_basis_rows:
            violations.append(
                "w1-fake-no-diff-forward: durable forward disposition row did not carry "
                "route_decision override basis for the fake-landing hold"
            )

        fake_variant = Path(cust_raw) / "customer-fake-variant"
        fake_variant.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, fake_variant)
        fake_variant_result = run_customer_building_in_sandbox(
            _w1_intent("w1-fake-variant-write-0"),
            customer_repo_root=fake_variant,
            output_root=evidence_root / "fake-variant",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=False),
            adapter_timeout_seconds=30,
        )
        original_fake_landing_reader = driver_module._fake_landing_forward_disposition_recorded
        driver_module._fake_landing_forward_disposition_recorded = lambda *_args, **_kwargs: False
        try:
            with checker_temp_path("bp-w1-no-diff-forward-red-") as red_raw:
                no_diff_red = run_approve_entry(
                    fake_variant_result.evidence_root,
                    action="forward",
                    author_ref="coo:d2-checker",
                    adapter_cwd=red_raw,
                    adapter_timeout_seconds=30,
                    repo_root=fake_variant,
                )
        finally:
            driver_module._fake_landing_forward_disposition_recorded = original_fake_landing_reader
        summary["w1_fake_no_diff_forward_red_frontier"] = no_diff_red.get("frontier_kind")
        summary["w1_fake_no_diff_forward_red_reason"] = no_diff_red.get("frontier_reason")
        if no_diff_red.get("frontier_kind") != "human_review_waiting":
            violations.append(
                "w1-fake-no-diff-forward-variant-RED: disabling suppression did not "
                f"re-hold (frontier={no_diff_red.get('frontier_kind')!r}, "
                f"error={no_diff_red.get('error_kind')!r})"
            )
        if no_diff_red.get("frontier_reason") != "fake_landing_write_scope_diff_absent":
            violations.append(
                "w1-fake-no-diff-forward-variant-RED: re-hold did not preserve "
                f"fake-landing reason (reason={no_diff_red.get('frontier_reason')!r})"
            )

        fake_undispositioned = Path(cust_raw) / "customer-fake-undispositioned"
        fake_undispositioned.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, fake_undispositioned)
        fake_undispositioned_result = run_customer_building_in_sandbox(
            _w1_intent("w1-fake-undispositioned-write-0"),
            customer_repo_root=fake_undispositioned,
            output_root=evidence_root / "fake-undispositioned",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=False),
            adapter_timeout_seconds=30,
        )
        summary["w1_fake_undispositioned_frontier"] = (
            fake_undispositioned_result.frontier_kind
        )
        summary["w1_fake_undispositioned_reason"] = (
            fake_undispositioned_result.frontier_reason
        )
        if fake_undispositioned_result.frontier_kind != "human_review_waiting":
            violations.append(
                "w1-fake-undispositioned: no-diff write-needed completion without "
                f"disposition did not hold (frontier={fake_undispositioned_result.frontier_kind!r})"
            )
        if (
            fake_undispositioned_result.frontier_reason
            != "fake_landing_write_scope_diff_absent"
        ):
            violations.append(
                "w1-fake-undispositioned: hold did not preserve fake-landing reason "
                f"(reason={fake_undispositioned_result.frontier_reason!r})"
            )

        with checker_temp_path("bp-w1-no-diff-reroute-") as reroute_raw:
            no_diff_reroute = run_approve_entry(
                fake_undispositioned_result.evidence_root,
                action="reroute",
                reroute_target_ref="brick:w1-explicit-reroute-target",
                re_instruction=(
                    "Done endline: retry the held W1 fixture against the explicit "
                    "target and return declared evidence before DONE. Proof must "
                    "be executable in the receiving lane. Repairs outside the "
                    "receiving lane's scope are COO gate items, not re-dispatch."
                ),
                author_ref="coo:d2-checker",
                adapter_cwd=reroute_raw,
                adapter_timeout_seconds=30,
                repo_root=fake_undispositioned,
            )
        summary["w1_fake_no_diff_reroute_frontier"] = no_diff_reroute.get("frontier_kind")
        if no_diff_reroute.get("frontier_kind") != "human_review_waiting":
            violations.append(
                "w1-fake-no-diff-reroute: non-forward disposition was consumed as "
                f"suppression (frontier={no_diff_reroute.get('frontier_kind')!r}, "
                f"error={no_diff_reroute.get('error_kind')!r})"
            )

        fake_other_hold = Path(cust_raw) / "customer-fake-other-hold"
        fake_other_hold.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, fake_other_hold)
        fake_other_hold_result = run_customer_building_in_sandbox(
            _w1_intent("w1-fake-other-hold-write-0"),
            customer_repo_root=fake_other_hold,
            output_root=evidence_root / "fake-other-hold",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=False),
            adapter_timeout_seconds=30,
        )
        other_link_path = Path(fake_other_hold_result.evidence_root) / "raw" / "link.jsonl"
        other_link_records = _jsonl_records(other_link_path)
        for record in reversed(other_link_records):
            if record.get("hold_reason") == "fake_landing_write_scope_diff_absent":
                wrong_ref = str(record.get("transition_lifecycle_paused_at_ref") or "")
                record["transition_lifecycle_paused_at_ref"] = wrong_ref + "-other"
                break
        other_link_path.write_text(
            "\n".join(
                json.dumps(record, separators=(",", ":"), ensure_ascii=False)
                for record in other_link_records
            )
            + "\n",
            encoding="utf-8",
        )
        with checker_temp_path("bp-w1-other-hold-forward-") as other_raw:
            other_hold_forward = run_approve_entry(
                fake_other_hold_result.evidence_root,
                action="forward",
                author_ref="coo:d2-checker",
                adapter_cwd=other_raw,
                adapter_timeout_seconds=30,
                repo_root=fake_other_hold,
            )
        summary["w1_fake_other_hold_forward_error"] = other_hold_forward.get("error_kind")
        summary["w1_fake_other_hold_forward_frontier"] = other_hold_forward.get(
            "frontier_kind"
        )
        if (
            other_hold_forward.get("error_kind") is None
            and other_hold_forward.get("frontier_kind") == "complete"
        ):
            violations.append(
                "w1-fake-other-hold: mismatched hold identity was consumed as a "
                "clean complete forward"
            )

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

        # CASE 3b (direct close = WIP anchor): a normal run that uses a caller-
        # supplied adapter_cwd and completes with uncommitted output must still
        # preserve that output under refs/brick/wip/<building_id>. Mutation-RED:
        # bypassing run.py's close-time anchor leaves anchored_ref empty and the
        # ref absent.
        customer4 = Path(cust_raw) / "customer-direct-close-anchor"
        customer4.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, customer4)
        direct_building_id = "w1-direct-close-anchor-0"
        # D3 (0706 r2-carry): declare an opt-in building-grain report policy so the
        # dynamic walk attaches the THIRD side channel (_report_event_observations)
        # in addition to reroute records + walker evidence. local-inbox is the only
        # sink (dry-run, no creds); a non-vessel temp root strips external sinks.
        # This lets the survival check below assert 3-of-3 channels, not 2, across
        # the close-time anchor replace().
        direct_intent = dict(_w1_intent(direct_building_id))
        direct_intent["report_event_policy"] = {
            "enabled": True,
            "grain": "building",
            "event_kinds": ["building_finished"],
            "sink_refs": ["report-sink:local-inbox"],
        }
        direct = run_building_intake(
            direct_intent,
            output_root=evidence_root / "direct-close-anchor",
            overwrite_existing=True,
            command_runner=_w1_completing_codex_runner(write=True),
            adapter_cwd=customer4,
            adapter_timeout_seconds=30,
        )
        direct_anchor_ref = direct.run_result.anchored_ref
        direct_reclaimed = reclaim_wip_anchor(customer4, direct_building_id)
        summary["w1_direct_close_anchored_ref"] = direct_anchor_ref
        summary["w1_direct_close_reclaimed_anchor"] = (
            direct_reclaimed[0] if direct_reclaimed else ""
        )
        summary["w1_direct_close_reclaimed_commit"] = (
            direct_reclaimed[1] if direct_reclaimed else ""
        )
        if not direct_anchor_ref.startswith("refs/brick/wip/"):
            violations.append(
                f"w1-direct-close-anchor: run result missing anchored_ref: {direct_anchor_ref!r}"
            )
        # anchor stamping mints a new frozen result (dataclasses.replace) — ALL
        # THREE dynamic-walker side channels must SURVIVE the stamp via the D1
        # single-source carry helper (0706 live-sweep catch: a stripped
        # _dynamic_walker_evidence broke the routing-loop checker and silently
        # dropped report observations). D3 whole-channel survival: assert the FULL
        # PLAN_RESULT_SIDE_CHANNEL_FIELDS set survives, and that the report channel
        # is present AND non-empty (a partial hand-copy that dropped it would RED
        # here — see the partial-copy mutation-RED below).
        direct_report_obs = getattr(direct.run_result, "_report_event_observations", ())
        summary["w1_direct_close_report_observation_count"] = len(direct_report_obs)
        if not hasattr(direct.run_result, "_dynamic_walker_evidence"):
            violations.append(
                "w1-direct-close-anchor: anchored result LOST the "
                "_dynamic_walker_evidence side channel (replace() strip)"
            )
        if not hasattr(direct.run_result, "_dynamic_walker_reroute_records"):
            violations.append(
                "w1-direct-close-anchor: anchored result LOST the "
                "_dynamic_walker_reroute_records side channel (replace() strip)"
            )
        if not hasattr(direct.run_result, "_report_event_observations") or not direct_report_obs:
            violations.append(
                "w1-direct-close-anchor: anchored result LOST the "
                "_report_event_observations side channel (replace() strip / partial "
                "hand-copy) — the report policy emitted no surviving observation"
            )
        if direct_reclaimed is None or direct_reclaimed[0] != direct_anchor_ref:
            violations.append("w1-direct-close-anchor: close-time WIP ref was not reclaimable")
        elif direct_reclaimed[1]:
            direct_anchor_files = _git_text(
                customer4,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                direct_reclaimed[1],
            )
            summary["w1_direct_close_anchor_files"] = direct_anchor_files
            if direct_anchor_files != _W1_WRITE_REL:
                violations.append(
                    "w1-direct-close-anchor: WIP anchor did not capture the direct "
                    f"adapter_cwd output exactly: {direct_anchor_files!r}"
                )
        # --- D3 MUTATION-RED #1 (channel-strip): neuter the D1 carry helper so
        # the close-time anchor replace() mints a NEW frozen result WITHOUT any
        # side channels. The whole-channel survival proof above MUST now RED, i.e.
        # the anchored result loses every dynamic-walker channel. If stripping the
        # carry still leaves the channels present, the carry helper is not the
        # load-bearing surface and the survival proof is vacuous.
        original_carry = run_module.carry_plan_result_side_channels

        def _strip_carry(_source, minted):  # noqa: ANN001 - checker-local mutant
            return minted  # carry NOTHING onto the reminted result

        strip_customer = Path(cust_raw) / "customer-direct-close-strip"
        strip_customer.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, strip_customer)
        strip_building_id = "w1-direct-close-strip-0"
        strip_intent = dict(direct_intent)
        strip_intent["building_id"] = strip_building_id
        strip_intent["write_scope"] = dict(_W1_WRITE_SCOPE)
        try:
            run_module.carry_plan_result_side_channels = _strip_carry
            strip_result = run_building_intake(
                strip_intent,
                output_root=evidence_root / "direct-close-strip",
                overwrite_existing=True,
                command_runner=_w1_completing_codex_runner(write=True),
                adapter_cwd=strip_customer,
                adapter_timeout_seconds=30,
            ).run_result
        finally:
            run_module.carry_plan_result_side_channels = original_carry
        release_wip_anchor(strip_customer, strip_building_id)
        strip_channels_present = [
            field_name
            for field_name in (
                "_dynamic_walker_reroute_records",
                "_dynamic_walker_evidence",
                "_report_event_observations",
            )
            if hasattr(strip_result, field_name)
        ]
        strip_anchored = strip_result.anchored_ref.startswith("refs/brick/wip/")
        summary["w1_direct_close_channel_strip_mutation_red_execution_log"] = {
            "carry_helper_neutered": True,
            "anchored_ref_still_stamped": strip_anchored,
            "channels_present_after_strip": strip_channels_present,
            "proof_limit": "mutation-RED support evidence only",
        }
        if strip_channels_present:
            violations.append(
                "w1-direct-close-anchor channel-strip mutation-RED: neutering the "
                "carry helper still left side channels "
                f"{strip_channels_present!r} on the anchored result -- the carry "
                "helper is not the load-bearing surface"
            )
        if not strip_anchored:
            violations.append(
                "w1-direct-close-anchor channel-strip mutation-RED: the anchor stamp "
                "did not run, so the strip did not actually exercise the replace() path"
            )

        # --- D3 MUTATION-RED #2 (partial hand-copy regression): a carry that
        # copies ONLY the first channel (the pre-helper failure mode: a hand-rolled
        # loop that drops _report_event_observations). The 3-of-3 whole-channel
        # survival above MUST RED because the report channel vanishes while the
        # reroute channel survives -- proving the survival assertion checks the
        # WHOLE set, not just one channel.
        def _partial_carry(source, minted):  # noqa: ANN001 - checker-local mutant
            first = "_dynamic_walker_reroute_records"
            if hasattr(source, first):
                object.__setattr__(minted, first, getattr(source, first))
            return minted  # deliberately DROP evidence + report channels

        partial_customer = Path(cust_raw) / "customer-direct-close-partial"
        partial_customer.mkdir(parents=True, exist_ok=True)
        _seed_customer_repo(repo, partial_customer)
        partial_building_id = "w1-direct-close-partial-0"
        partial_intent = dict(direct_intent)
        partial_intent["building_id"] = partial_building_id
        partial_intent["write_scope"] = dict(_W1_WRITE_SCOPE)
        try:
            run_module.carry_plan_result_side_channels = _partial_carry
            partial_result = run_building_intake(
                partial_intent,
                output_root=evidence_root / "direct-close-partial",
                overwrite_existing=True,
                command_runner=_w1_completing_codex_runner(write=True),
                adapter_cwd=partial_customer,
                adapter_timeout_seconds=30,
            ).run_result
        finally:
            run_module.carry_plan_result_side_channels = original_carry
        release_wip_anchor(partial_customer, partial_building_id)
        partial_report_present = (
            hasattr(partial_result, "_report_event_observations")
            and bool(getattr(partial_result, "_report_event_observations", ()))
        )
        partial_reroute_present = hasattr(partial_result, "_dynamic_walker_reroute_records")
        summary["w1_direct_close_partial_copy_mutation_red_execution_log"] = {
            "carry_helper_partial": True,
            "reroute_channel_survived": partial_reroute_present,
            "report_channel_survived": partial_report_present,
            "proof_limit": "mutation-RED support evidence only",
        }
        # The regression the whole-channel assertion catches: report channel gone.
        if partial_report_present:
            violations.append(
                "w1-direct-close-anchor partial-copy mutation-RED: the partial carry "
                "still preserved _report_event_observations -- the 3-of-3 survival "
                "assertion would not catch a dropped-report regression"
            )
        if not partial_reroute_present:
            violations.append(
                "w1-direct-close-anchor partial-copy mutation-RED: the partial carry "
                "dropped even the first channel, so the mutant does not isolate the "
                "report-channel-only regression"
            )
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


def _d1_park_stop_graph_plan(building_id: str) -> Mapping[str, Any]:
    """A two-step graph whose FIRST step parks on adapter:chat-session.

    The park frontier is written before an AgentFact returns, so the direct
    adapter_cwd run raises ChatSessionParkFrontierEvidenceWritten past the
    completion-time anchor -- the D1 park-stop anchor path.
    """

    return {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "graph",
        "execution_order": ["d1-park-work", "d1-followup-work"],
        "brick_steps": [
            {
                "step_ref": "d1-park-work",
                "selected_adapter_ref": "adapter:chat-session",
                "completion_edge_ref": "edge:d1-park-work-to-followup",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:d1-park-work",
                        "brick_work_ref": "work:d1-park-work",
                        "brick_instance_ref": "brick-d1-park-work",
                        "work_statement": "Exercise chat-session park on a direct adapter_cwd run.",
                        "comparison_rule": "Support observes parked evidence shape only.",
                        "required_return_shape": "made_changes, observed_evidence, not_proven",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:d1-park-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                ],
            },
            {
                "step_ref": "d1-followup-work",
                "selected_adapter_ref": "adapter:local",
                "completion_edge_ref": "edge:d1-followup-work-to-boundary",
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": "brick-row:d1-followup-work",
                        "brick_work_ref": "work:d1-followup-work",
                        "brick_instance_ref": "brick-d1-followup-work",
                        "work_statement": "Live follow-up after chat-session submission.",
                        "comparison_rule": "Support observes follow-up invocation only.",
                        "required_return_shape": "returned_summary, adapter_ref",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": "agent-row:d1-followup-work",
                        "agent_object_ref": "agent-object:dev",
                    },
                ],
            },
        ],
        "link_edges": [
            {
                "edge_ref": "edge:d1-park-work-to-followup",
                "source_step_ref": "d1-park-work",
                "target_step_ref": "d1-followup-work",
                "rows": [
                    {
                        "axis": "Link",
                        "row_ref": "link-row:d1-park-work",
                        "movement": "forward",
                        "target_ref": "brick-d1-followup-work",
                        "declared_gate_refs": ["link-gate:default-transition"],
                    }
                ],
            },
            {
                "edge_ref": "edge:d1-followup-work-to-boundary",
                "source_step_ref": "d1-followup-work",
                "rows": [
                    {
                        "axis": "Link",
                        "row_ref": "link-row:d1-followup-work",
                        "movement": "forward",
                        "target_ref": "building-boundary:d1-park-closed",
                        "declared_gate_refs": ["link-gate:default-transition"],
                    }
                ],
            },
        ],
    }


def _park_stop_anchor_and_launch_dirty_fire(
    repo: Path,
    violations: list[str],
    summary: dict[str, Any],
) -> None:
    """D1 FIRE: park-stop WIP anchor + launch dirty-cwd observation.

    Two proofs over a DIRECT adapter_cwd run (not the engine worktree sandbox):

      * park-stop anchor: a walk that PARKS before a clean result still preserves
        the worktree's dirty bytes under refs/brick/wip/<building_id>, because the
        run surface anchors on the ChatSessionParkFrontierEvidenceWritten path
        before re-raising. Mutation-RED: an in-process monkeypatch that neuters
        _anchor_park_stop_wip leaves the ref absent.
      * launch dirty observation: a pre-existing dirty adapter_cwd emits one
        stderr DIRTY-CWD warning at launch and NEVER refuses. Mutation-RED: a
        clean adapter_cwd emits NO warning (so the warning is genuinely gated).
    """

    import contextlib
    import io

    from brick_protocol.support.operator import run as run_module
    from brick_protocol.support.operator.run import (
        ChatSessionParkFrontierEvidenceWritten,
        run_building_plan,
    )
    from brick_protocol.support.operator.worktree_sandbox import (
        reclaim_wip_anchor,
        release_wip_anchor,
    )

    with tempfile.TemporaryDirectory(prefix="bp-d1-customer-") as cust_raw, \
            tempfile.TemporaryDirectory(prefix="bp-d1-evidence-") as ev_raw, \
            _TemporaryHome(Path(cust_raw) / "engine-home"):
        customer = Path(cust_raw) / "customer-live"
        customer.mkdir(parents=True, exist_ok=True)
        evidence_root = Path(ev_raw)
        _seed_customer_repo(repo, customer)
        original_runner_repo = run_module._REPO_ROOT
        try:
            run_module._REPO_ROOT = customer

            # --- park-stop anchor (GREEN): dirty the worktree, then park. ---
            (customer / "d1-provider-wip.txt").write_text(
                "provider WIP written before the park\n", encoding="utf-8"
            )
            park_building_id = "d1-park-stop-anchor-0"
            park_stderr = io.StringIO()
            parked_ok = False
            with contextlib.redirect_stderr(park_stderr):
                try:
                    run_building_plan(
                        _d1_park_stop_graph_plan(park_building_id),
                        output_root=evidence_root / "park-stop",
                        overwrite_existing=True,
                        adapter_cwd=customer,
                    )
                except ChatSessionParkFrontierEvidenceWritten:
                    parked_ok = True
                except Exception as exc:  # noqa: BLE001 - surface unexpected leak
                    violations.append(
                        f"d1-park-stop-anchor: expected chat-session park, got {type(exc).__name__}: {exc}"
                    )
            if not parked_ok:
                violations.append(
                    "d1-park-stop-anchor: direct adapter_cwd run did not park on the chat-session step"
                )
            park_reclaimed = reclaim_wip_anchor(customer, park_building_id)
            summary["d1_park_stop_anchor_ref"] = park_reclaimed[0] if park_reclaimed else ""
            if park_reclaimed is None or not park_reclaimed[0].startswith("refs/brick/wip/"):
                violations.append(
                    "d1-park-stop-anchor: park path did NOT anchor the dirty worktree "
                    f"({park_reclaimed!r})"
                )
            elif park_reclaimed[1]:
                anchored_files = _git_text(
                    customer, "diff-tree", "--no-commit-id", "--name-only", "-r", park_reclaimed[1]
                )
                summary["d1_park_stop_anchor_files"] = anchored_files
                if "d1-provider-wip.txt" not in anchored_files:
                    violations.append(
                        "d1-park-stop-anchor: WIP anchor did not capture the provider WIP "
                        f"({anchored_files!r})"
                    )
            release_wip_anchor(customer, park_building_id)

            # --- park-stop anchor MUTATION-RED: neuter the anchor -> ref absent. ---
            (customer / "d1-provider-wip.txt").write_text(
                "provider WIP written before the parked mutation run\n", encoding="utf-8"
            )
            mutation_building_id = "d1-park-stop-anchor-mutation-0"
            original_anchor = run_module._anchor_park_stop_wip
            neutered_calls = {"count": 0}

            def _neutered_anchor(*_args: Any, **_kwargs: Any) -> None:
                neutered_calls["count"] += 1
                return None

            try:
                run_module._anchor_park_stop_wip = _neutered_anchor
                with contextlib.redirect_stderr(io.StringIO()):
                    try:
                        run_building_plan(
                            _d1_park_stop_graph_plan(mutation_building_id),
                            output_root=evidence_root / "park-stop-mutation",
                            overwrite_existing=True,
                            adapter_cwd=customer,
                        )
                    except ChatSessionParkFrontierEvidenceWritten:
                        pass
                    except Exception:  # noqa: BLE001 - the mutation still parks/raises
                        pass
            finally:
                run_module._anchor_park_stop_wip = original_anchor
            mutation_reclaimed = reclaim_wip_anchor(customer, mutation_building_id)
            summary["d1_park_stop_anchor_mutation_red_execution_log"] = {
                "neutered_anchor_calls": neutered_calls["count"],
                "ref_absent_after_neuter": mutation_reclaimed is None,
                "proof_limit": "mutation-RED support evidence only",
            }
            if mutation_reclaimed is not None:
                release_wip_anchor(customer, mutation_building_id)
                violations.append(
                    "d1-park-stop-anchor mutation-RED: neutering the park-stop anchor still "
                    "produced a WIP ref -- the anchor is not the load-bearing surface"
                )
            if neutered_calls["count"] == 0:
                violations.append(
                    "d1-park-stop-anchor mutation-RED: the park-stop anchor hook was never "
                    "invoked on the park path -- the anchor is not wired into run_building_plan"
                )

            # --- launch dirty observation (GREEN): dirty cwd warns at launch. ---
            (customer / "d1-preexisting-dirt.txt").write_text(
                "pre-existing uncommitted change at launch\n", encoding="utf-8"
            )
            dirty_building_id = "d1-launch-dirty-0"
            dirty_stderr = io.StringIO()
            with contextlib.redirect_stderr(dirty_stderr):
                try:
                    run_building_plan(
                        _d1_park_stop_graph_plan(dirty_building_id),
                        output_root=evidence_root / "launch-dirty",
                        overwrite_existing=True,
                        adapter_cwd=customer,
                    )
                except ChatSessionParkFrontierEvidenceWritten:
                    pass
                except Exception:  # noqa: BLE001 - the warning is emitted before dispatch
                    pass
            dirty_observed = dirty_stderr.getvalue()
            summary["d1_launch_dirty_warned"] = "building launch: DIRTY-CWD" in dirty_observed
            if f"building launch: DIRTY-CWD building={dirty_building_id}" not in dirty_observed:
                violations.append(
                    "d1-launch-dirty: a pre-existing dirty adapter_cwd did NOT emit the "
                    "launch DIRTY-CWD warning"
                )
            release_wip_anchor(customer, dirty_building_id)

            # --- launch dirty MUTATION-RED: a CLEAN cwd emits NO warning. ---
            clean_customer = Path(cust_raw) / "customer-clean"
            clean_customer.mkdir(parents=True, exist_ok=True)
            _seed_customer_repo(repo, clean_customer)
            run_module._REPO_ROOT = clean_customer
            clean_building_id = "d1-launch-clean-0"
            clean_stderr = io.StringIO()
            with contextlib.redirect_stderr(clean_stderr):
                try:
                    run_building_plan(
                        _d1_park_stop_graph_plan(clean_building_id),
                        output_root=evidence_root / "launch-clean",
                        overwrite_existing=True,
                        adapter_cwd=clean_customer,
                    )
                except ChatSessionParkFrontierEvidenceWritten:
                    pass
                except Exception:  # noqa: BLE001
                    pass
            clean_observed = clean_stderr.getvalue()
            summary["d1_launch_dirty_mutation_red_execution_log"] = {
                "clean_cwd_warned": "building launch: DIRTY-CWD" in clean_observed,
                "proof_limit": "mutation-RED support evidence only",
            }
            if "building launch: DIRTY-CWD" in clean_observed:
                violations.append(
                    "d1-launch-dirty mutation-RED: a CLEAN adapter_cwd emitted the DIRTY-CWD "
                    "warning -- the observation is not actually gated on dirt"
                )
            release_wip_anchor(clean_customer, clean_building_id)
        finally:
            run_module._REPO_ROOT = original_runner_repo

    summary["d1_park_stop_and_launch_dirty_fire"] = "passed"


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
        f"fake_landing read_only_gate_fired={summary.get('w1_read_only_fake_landing_gate_fired')} "
        f"empty_frontier={summary.get('w1_fake_empty_frontier')} "
        f"empty_reason={summary.get('w1_fake_empty_frontier_reason')} "
        f"outside_frontier={summary.get('w1_fake_outside_frontier')} "
        f"outside_reason={summary.get('w1_fake_outside_frontier_reason')} "
        f"outside_wip_files={summary.get('w1_fake_outside_wip_files')}; "
        "deliverable_crosscheck deferred: gate is building-level, so per-node "
        "masking by a sibling in-scope diff remains follow-up evidence work; "
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
        "W1 direct close anchor FIRE passed: "
        f"anchored_ref={summary.get('w1_direct_close_anchored_ref')} "
        f"reclaimed={summary.get('w1_direct_close_reclaimed_anchor')} "
        f"files={summary.get('w1_direct_close_anchor_files')} "
        f"report_obs={summary.get('w1_direct_close_report_observation_count')}; "
        "side-channel carry (D1/D3): "
        f"channel_strip_RED={summary.get('w1_direct_close_channel_strip_mutation_red_execution_log')} "
        f"partial_copy_RED={summary.get('w1_direct_close_partial_copy_mutation_red_execution_log')}."
    )
    print(
        "D1 park-stop anchor + launch dirty FIRE passed: "
        f"park_anchor_ref={summary.get('d1_park_stop_anchor_ref')} "
        f"park_anchor_files={summary.get('d1_park_stop_anchor_files')} "
        f"park_mutation_red={summary.get('d1_park_stop_anchor_mutation_red_execution_log')} "
        f"launch_dirty_warned={summary.get('d1_launch_dirty_warned')} "
        f"launch_mutation_red={summary.get('d1_launch_dirty_mutation_red_execution_log')}."
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

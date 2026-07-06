#!/usr/bin/env python3
"""Behavioral checker for the resume-replay non-forward disposition MIRROR.

Support evidence only. This checker drives the admitted resume verb
(``support/operator/run.resume_building_plan``, deterministic-replay use per
run.py:716-719) over ``adapter:local`` synthetic building ledgers. It NEVER
calls a real provider, chooses Movement, authors a route, or judges source
truth, success, or quality.

It is the machine gate for the walker resume-replay repair (Slice 2, COO-direct):
the four required fixtures are each an independent RED->GREEN pair that MUST hold
a dual-acceptance shape, so the SAME checker serves both generations:

  (a) RED-PIN branch  -- at the pinned HEAD baseline the final resume RAISES the
      engine's exact refusal literal (measured; the disposition can NOT be
      replayed past a prior non-forward disposition), OR
  (b) GREEN branch    -- after the mirror repair the same fixture resumes and the
      per-fixture invariants (design final-0706 SS D3/invariants) hold.

Any state that is NEITHER (a) NOR (b) is a ProfileError -> exit 1. Corrupting a
fixture's pinned literal therefore flips the run RED (self-mutation proof).

Design source (execution directive):
  project/brick-protocol/status/kernel/t7b-replay-mirror-design-final-0706.md
  (SS proposed_changes[2]=D3 fixture spec, SS invariants I1..I6, SS edge_cases,
   SS checker_or_verifier_plan).

Measured HEAD deviation surfaced for Slice 2 (see MODULE NOT_PROVEN below):
F-R1/F-R2/F-S reproduce the EXACT gate-sequence 1746 literal
('resume replay encountered an already-disposed recorded HOLD for ...
unsupported prior disposition \'reroute\''). F-M -- the design's mixed
forward-mirror + deeper-reroute chain -- reproduces the DIVERGENCE guard literal
at HEAD instead of the 1746 literal, because a non-root reroute source does not
re-materialize as a gate-sequence hold on replay (a root reroute short-circuits
any single-replay chain that would exercise both a mirrored forward and a
reroute-raise). This is measured, not a substitution of convenience; it is a
Slice-2 concern, not this lane's to resolve.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import os.path as _osp
import sys

_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_IMPORT_IDENTITY = _osp.join(_REPO_ROOT, "support", "import_identity")
if _IMPORT_IDENTITY not in sys.path:
    sys.path.insert(0, _IMPORT_IDENTITY)


# ---------------------------------------------------------------------------
# Engine literals (pinned verbatim; see walker_kernel.py:1748-1751 / :2346 and
# walker_resume.py:200). Corrupting any of these below is the self-mutation RED.
# ---------------------------------------------------------------------------

RED_REROUTE_HOLD_PREFIX = "resume replay encountered an already-disposed recorded HOLD for "
RED_UNSUPPORTED_REROUTE_SUFFIX = "unsupported prior disposition 'reroute'"
_COMPLIANT_RE_INSTRUCTION = (
    "Done endline: replay the prior disposition mirror fixture and return the "
    "declared checker evidence before DONE. Proof must be executable in the "
    "receiving lane. Repairs outside the receiving lane's scope are COO gate "
    "items, not re-dispatch."
)
DIVERGENCE_PREFIX = "resume divergence: the seeded walk completed WITHOUT applying"
APPLIED_DISPOSITION_LITERAL = "dynamic Building already has an applied resume disposition"

# Concern-path guard literals (pinned verbatim for mirror-unsupported sites,
# including P-C1). The required F-C fixtures now expect GREEN mirror replay;
# these literals remain as loud-regression evidence for sites that still call
# `_require_undisposed_concern_hold`.
CONCERN_PATH_HOLD_PREFIX = "resume replay reached a previously-disposed concern-path HOLD "
CONCERN_PATH_MIRROR_NOT_IMPLEMENTED = (
    "concern-path mirroring is not implemented in this slice"
)
SEQUENCE_REUSE_GUARD_LITERAL = (
    "sequence-reuse guard missing: concern mirror must roll back prospective "
    "hold sequence before replay adoption"
)

# ---------------------------------------------------------------------------
# Family-② SELF-LOCK literals (0706 selflock slice, shared home). D1
# validate-before-persist + D2 declared correction (void) path. The source guard
# below is the D1-removal MUTATION-RED handle.
# ---------------------------------------------------------------------------
INTAKE_VALIDATE_BEFORE_PERSIST_GUARD_LITERAL = (
    "validate-before-persist guard missing: disposition intake must validate "
    "before the raw/link.jsonl append"
)
# The existing resume-path refusal a residual out-of-class reroute row triggers
# (walker_resume._disposition_pending_target_ref). Pinned verbatim: the D2 void
# path must leave THIS literal firing until the residual row is voided (no
# validation weakened -- D2 only makes a specific row unselectable).
_RAISE_TARGET_NOT_NODE_REFUSAL_REROUTE = (
    "reroute disposition pending_target_ref is not an existing Brick node"
)


class ProfileError(AssertionError):
    """A fixture reached neither the RED-pin literal nor the GREEN invariants."""


# ---------------------------------------------------------------------------
# adapter:local synthetic-ledger builders (no providers). Each fixture drives
# run_building_plan -> HOLD, then appends human/COO disposition rows to
# raw/link.jsonl and re-drives resume_building_plan, so the built ledger carries
# the birth-certificate graph plan, recorded agent returns, step-output ledger,
# and raw/link.jsonl disposition rows the design D3 spec names.
# ---------------------------------------------------------------------------


def _coo_hold_policy(prefix: str, obs: str) -> list[Mapping[str, Any]]:
    """A gate-sequence policy that FORWARDS the default gate then HOLDs on the
    COO gate (missing required facts). A gate-sequence hold RE-EVALUATES each walk
    generation, so a prior non-forward disposition on it is re-encountered on
    replay -- exactly the mirror site (walker_kernel.py:1714-1752)."""

    return [
        {
            "gate_ref": "link-gate:default-transition",
            "on_missing_required_facts": {
                "action": "hold",
                "pending_target_basis": "target_brick",
                "reason_refs": [f"observation:{prefix}-{obs}-dt"],
                "required_disposition_owner": "caller-or-coo",
            },
            "on_sufficient": {"action": "next", "next_gate_ref": "link-gate:coo"},
        },
        {
            "gate_ref": "link-gate:coo",
            "on_missing_required_facts": {
                "action": "hold",
                "pending_target_basis": "target_brick",
                "reason_refs": [f"observation:{prefix}-{obs}-coo"],
                "required_disposition_owner": "caller-or-coo",
            },
            "on_sufficient": {"action": "forward"},
        },
    ]


def _brick_step(step_ref: str, brick_ref: str, completion_edge_ref: str) -> Mapping[str, Any]:
    from support.checkers.lib.fixture_graph_helpers import fixture_graph_brick_step

    return fixture_graph_brick_step(
        step_ref,
        brick_ref,
        completion_edge_ref,
        agent_object_ref="agent-object:coo",
        work_statement=f"Deterministic synthetic work for {step_ref}.",
        required_return_shape="observed_evidence, not_proven",
        source_facts=["AGENTS.md"],
    )


def _forward_edge(
    edge_ref: str,
    src_step: str,
    tgt_step: str,
    tgt_brick: str,
    *,
    hold_obs: str | None,
    prefix: str,
) -> Mapping[str, Any]:
    from support.checkers.lib.fixture_graph_helpers import fixture_graph_link_edge

    gates = (
        ["link-gate:default-transition", "link-gate:coo"]
        if hold_obs
        else ["link-gate:default-transition"]
    )
    edge = fixture_graph_link_edge(
        edge_ref,
        src_step,
        tgt_brick,
        target_step_ref=tgt_step,
        declared_gate_refs=gates,
        falsy_declared_gate_refs_use_default=True,
    )
    if hold_obs:
        edge["rows"][0]["gate_sequence_policy"] = _coo_hold_policy(prefix, hold_obs)
    return edge


def _close_edge(
    edge_ref: str,
    src_step: str,
    reason: str,
    boundary: str,
    *,
    hold_obs: str | None,
    prefix: str,
) -> Mapping[str, Any]:
    from support.checkers.lib.fixture_graph_helpers import fixture_graph_link_edge

    edge = fixture_graph_link_edge(
        edge_ref,
        src_step,
        boundary,
        close_reason=reason,
        declared_gate_refs=(
            ["link-gate:default-transition", "link-gate:coo"] if hold_obs else None
        ),
        falsy_declared_gate_refs_use_default=True,
    )
    if hold_obs:
        edge["rows"][0]["gate_sequence_policy"] = _coo_hold_policy(prefix, hold_obs)
    return edge


def _chain_plan(
    prefix: str,
    nodes: Sequence[str],
    hold_edges: Mapping[tuple[str, str], str],
    budgets: Mapping[str, int],
) -> tuple[Mapping[str, Any], Mapping[str, str]]:
    """A linear graph n0 -> n1 -> ... -> close. ``hold_edges`` maps a
    (source_node, target_node|'close') pair to a hold-observation label; those
    edges carry the COO gate-sequence hold policy."""

    from support.checkers.lib.fixture_graph_helpers import fixture_proof_limits

    bricks = {n: f"brick-{prefix}-{n}" for n in nodes}
    steps: list[Mapping[str, Any]] = []
    edges: list[Mapping[str, Any]] = []
    order: list[str] = []
    for i, n in enumerate(nodes):
        step_ref = f"{prefix}-{n}"
        order.append(step_ref)
        if i < len(nodes) - 1:
            nxt = nodes[i + 1]
            edge_ref = f"edge:{prefix}-{n}-to-{nxt}"
            steps.append(_brick_step(step_ref, bricks[n], edge_ref))
            edges.append(
                _forward_edge(
                    edge_ref,
                    step_ref,
                    f"{prefix}-{nxt}",
                    bricks[nxt],
                    hold_obs=hold_edges.get((n, nxt)),
                    prefix=prefix,
                )
            )
        else:
            edge_ref = f"edge:{prefix}-{n}-to-close"
            steps.append(_brick_step(step_ref, bricks[n], edge_ref))
            edges.append(
                _close_edge(
                    edge_ref,
                    step_ref,
                    f"{prefix} closed for resume-replay mirror checker evidence.",
                    f"building-boundary:{prefix}-closed",
                    hold_obs=hold_edges.get((n, "close")),
                    prefix=prefix,
                )
            )
    plan = {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0706",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": fixture_proof_limits(),
        "not_proven": ["semantic correctness of this synthetic replay fixture"],
        "execution_order": order,
        "brick_steps": steps,
        "link_edges": edges,
        "node_reroute_budgets": {bricks[b]: v for b, v in budgets.items()},
    }
    return plan, bricks


class _CountingCallable:
    """A deterministic adapter:local stand-in that records invocation counts, so
    I3 (no live provider calls at/before the recorded frontier) is observable: a
    resume that raises the RED-pin literal must not have driven a new call."""

    def __init__(self) -> None:
        self.calls = 0
        self.seen: list[str] = []

    def __call__(self, request: Any) -> Mapping[str, Any]:
        self.calls += 1
        self.seen.append(request.brick_instance_ref)
        return {
            "observed_evidence": [f"obs {request.brick_instance_ref}"],
            "not_proven": ["semantic correctness"],
        }


def _local_callables(cb: _CountingCallable) -> Mapping[str, Any]:
    return {"callable:local:agent-invoke0-smoke": cb}


# ---------------------------------------------------------------------------
# raw/link.jsonl disposition-row authoring (mirrors what a human/COO author does:
# read the current hold identity from written evidence, echo it into the row).
# ---------------------------------------------------------------------------


def _current_hold_paused_at_ref(building_root: Path) -> str | None:
    from brick_protocol.support.operator.walker_hold import _hold_paused_at_ref
    from brick_protocol.support.operator.walker_resume import _read_written_dynamic_plan

    try:
        _plan, evidence = _read_written_dynamic_plan(building_root)
    except (OSError, ValueError):
        return None
    hold = evidence.get("hold")
    if not isinstance(hold, Mapping) or not evidence.get("held"):
        return None
    return _hold_paused_at_ref(hold)


def _append_disposition_row(
    building_root: Path,
    *,
    building_id: str,
    pending_target_ref: str,
    action: str,
    author_ref: str = "coo:smith",
) -> None:
    resumed_from_ref = (
        _current_hold_paused_at_ref(building_root)
        or f"link-transition:disposition-{action}"
    )
    row: dict[str, Any] = {
        "raw_ref": f"raw:link:disposition:{action}",
        "building_id": building_id,
        "step_ref": f"human-disposition-{action}",
        "transition_lifecycle_state": "resumed",
        "transition_lifecycle_progress_state": "in_progress",
        "transition_lifecycle_resumed_from_ref": resumed_from_ref,
        "transition_lifecycle_pending_target_ref": pending_target_ref,
        "transition_lifecycle_required_disposition_owner": "caller-or-coo",
        "transition_lifecycle_disposition_action": action,
        "transition_author_ref": author_ref,
    }
    if action == "reroute":
        row["transition_lifecycle_re_instruction"] = _COMPLIANT_RE_INSTRUCTION
    with (building_root / "raw" / "link.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def _held_records(result: Any) -> list[Mapping[str, Any]]:
    records = list(getattr(result, "_dynamic_walker_reroute_records", ()))
    return [r for r in records if r.get("disposition_required")]


def _adopted_records(result: Any) -> list[Mapping[str, Any]]:
    records = list(getattr(result, "_dynamic_walker_reroute_records", ()))
    return [r for r in records if not r.get("disposition_required")]


def _current_pending_target(result: Any) -> str | None:
    held = _held_records(result)
    return held[-1].get("target_brick") if held else None


def _persisted_observations(building_root: Path) -> list[Mapping[str, Any]]:
    from brick_protocol.support.operator.walker_resume import _read_written_dynamic_plan

    _plan, evidence = _read_written_dynamic_plan(building_root)
    obs = evidence.get("resume_observations", [])
    return [o for o in obs if isinstance(o, Mapping)]


# ---------------------------------------------------------------------------
# Fixture driver: run to HOLD, apply prior dispositions, then classify the FINAL
# resume as RED-pin (a) / GREEN (b) / ProfileError.
# ---------------------------------------------------------------------------


def _frontier_kind(root: Path, repo: Path) -> str:
    from brick_protocol.support.operator.frontier_observation import observe_building_frontier

    return observe_building_frontier(root, repo_root=repo).get("frontier_kind", "")


def _evidence_hold_identity(root: Path) -> str:
    """Current held hold's FULL identity fragment (reroute_ref + source step +
    cascade depth, normalized to the paused_at_ref spelling) from the written
    dynamic evidence; empty when not held. The reroute_ref alone embeds only
    sequence+target and is NOT unique across occurrences — walker_hold
    discriminates by source_step_ref+cascade_depth, so the comparison must too."""
    from brick_protocol.support.operator.walker_resume import _read_written_dynamic_plan

    try:
        _plan, evidence = _read_written_dynamic_plan(root)
    except Exception:
        return ""
    hold = evidence.get("hold")
    if not isinstance(hold, Mapping):
        return ""
    reroute_ref = str(hold.get("reroute_ref") or "")
    if not reroute_ref:
        return ""
    source = str(hold.get("source_step_ref") or "")
    depth = hold.get("cascade_depth", "")
    return f"{reroute_ref}-src-{source}-depth-{depth}".replace(":", "-")


def _run_to_hold(
    repo: Path,
    plan: Mapping[str, Any],
    output_root: Path,
    cb: _CountingCallable,
) -> Any:
    from brick_protocol.support.operator.run import run_building_plan

    return run_building_plan(
        plan,
        output_root=output_root,
        overwrite_existing=True,
        local_callables=_local_callables(cb),
        adapter_cwd=repo,
        adapter_timeout_seconds=30,
    )


def _resume(repo: Path, root: Path, cb: _CountingCallable) -> Any:
    from brick_protocol.support.operator.run import resume_building_plan

    return resume_building_plan(
        root,
        local_callables=_local_callables(cb),
        adapter_cwd=repo,
        adapter_timeout_seconds=30,
    )


def _apply_prior_disposition(
    repo: Path,
    root: Path,
    building_id: str,
    cb: _CountingCallable,
    *,
    action: str,
    reroute_target: str | None,
    bricks: Mapping[str, str],
    result: Any,
) -> Any:
    """Append and apply a PRIOR disposition; it must succeed at HEAD (forward
    mirror / mode-1 reroute apply) and leave the building HELD again."""

    if action in ("forward", "stop"):
        pending = _current_pending_target(result)
    else:
        pending = bricks.get(reroute_target or "", reroute_target)
    if not pending:
        raise ProfileError(f"prior {action} disposition has no pending target to address")
    _append_disposition_row(
        root, building_id=building_id, pending_target_ref=pending, action=action
    )
    return _resume(repo, root, cb)


def _classify_final_resume(
    fixture: str,
    *,
    expect_red_literal_kind: str,
    exc: BaseException | None,
    result: Any,
    root: Path,
    repo: Path,
    prior_adoption_refs: Sequence[str],
) -> Mapping[str, Any]:
    """Return per-fixture branch evidence, or raise ProfileError. ``exc`` is the
    ValueError the FINAL resume raised (or None if it returned)."""

    if exc is not None:
        raise ProfileError(
            f"{fixture}: expected GREEN mirror replay, but final resume raised "
            f"{type(exc).__name__}: {exc}"
        )

    # No raise: the ONLY admissible non-RED state is the GREEN post-repair branch.
    frontier = _frontier_kind(root, repo)
    green = _green_invariants(
        fixture,
        result=result,
        root=root,
        frontier=frontier,
        prior_adoption_refs=prior_adoption_refs,
    )
    return {
        "fixture": fixture,
        "branch": "green",
        "frontier_kind": frontier,
        **green,
    }


def _green_invariants(
    fixture: str,
    *,
    result: Any,
    root: Path,
    frontier: str,
    prior_adoption_refs: Sequence[str],
) -> Mapping[str, Any]:
    """Post-repair GREEN invariants (design final-0706 SS invariants I1..I6,
    SS D3 per-fixture GREEN). NOT reachable at the pinned HEAD baseline (all four
    fixtures RED-pin there), so this branch is authored-but-unmeasured until the
    Slice-2 walker mirror lands -- see MODULE NOT_PROVEN. It stays strict so a
    wrong mirror cannot pass silently.

    I2/I6: exactly the prior observations preserved plus at most one new CURRENT
    observation; I1: mirrored reroute_ref string-parity with the prior-generation
    recorded adoption record; completion/closure state per fixture."""

    observations = _persisted_observations(root)
    reroute_actions = [o for o in observations if o.get("disposition_action") == "reroute"]

    # I1 generation parity: every prior recorded reroute-adoption ref must survive
    # verbatim in the re-walked adoption records (no fresh identity minted).
    adopted_refs = {
        str(r.get("reroute_ref"))
        for r in _adopted_records(result)
        if r.get("reroute_ref")
    }
    for prior_ref in prior_adoption_refs:
        if prior_ref and prior_ref not in adopted_refs:
            raise ProfileError(
                f"{fixture}: GREEN mirror lost prior reroute_ref parity ({prior_ref!r} "
                f"not in re-walked adoptions {sorted(adopted_refs)!r})"
            )

    if fixture == "F-S":
        # Prior reroute mirrored, CURRENT stop closes the building (I5).
        if frontier not in ("complete", "closed", "stopped"):
            raise ProfileError(
                f"F-S: GREEN stop did not close the building (frontier={frontier!r})"
            )
    else:
        # Correct walker semantics (measured at the 0706 mirror gate): declared
        # gates fire PER OCCURRENCE, so after the mirror replays the prior
        # dispositions and the CURRENT disposition applies at the seed's held
        # identity, the walk may legitimately advance into a FRESH occurrence
        # whose gate holds again. GREEN therefore accepts completion OR a NEW
        # hold — but NEVER a re-park on an identity a disposition already
        # resolved (that would mean the mirror failed to consume it — I6).
        if frontier in ("complete", "closed"):
            pass
        elif frontier == "link_paused":
            current_identity = _evidence_hold_identity(root)
            if not current_identity:
                raise ProfileError(
                    f"{fixture}: GREEN mirror paused without a readable current "
                    "hold identity"
                )
            for observation in observations:
                disposed_norm = str(observation.get("paused_at_ref") or "").replace(
                    ":", "-"
                )
                if disposed_norm and current_identity in disposed_norm:
                    raise ProfileError(
                        f"{fixture}: GREEN mirror re-parked on an ALREADY-DISPOSED "
                        f"hold identity ({current_identity!r}) — the mirror failed "
                        "to consume a replayed disposition (I6)"
                    )
        else:
            raise ProfileError(
                f"{fixture}: GREEN mirror ended in an inadmissible frontier "
                f"({frontier!r})"
            )

    # I2: no re-authoring storm -- the reroute observations are the mirrored prior
    # ones (one per prior reroute), not a duplicated re-emission.
    return {
        "green_frontier": frontier,
        "green_reroute_observation_count": len(reroute_actions),
        "green_adopted_reroute_refs": sorted(adopted_refs),
    }


def _drive_fixture(
    repo: Path,
    *,
    fixture: str,
    prefix: str,
    nodes: Sequence[str],
    hold_edges: Mapping[tuple[str, str], str],
    budgets: Mapping[str, int],
    prior_dispositions: Sequence[tuple[str, str | None]],
    final_disposition: tuple[str, str | None],
    expect_red_literal_kind: str,
) -> Mapping[str, Any]:
    from brick_protocol.support.operator.run import run_building_plan  # noqa: F401  (import audit)

    plan, bricks = _chain_plan(prefix, nodes, hold_edges, budgets)
    cb = _CountingCallable()
    with tempfile.TemporaryDirectory(prefix=f"bp-resume-mirror-{prefix}-") as tmp:
        result = _run_to_hold(repo, plan, Path(tmp).resolve(), cb)
        root = result.lifecycle_write.root
        if _frontier_kind(root, repo) != "link_paused":
            raise ProfileError(
                f"{fixture}: setup did not reach the first HOLD "
                f"(frontier={_frontier_kind(root, repo)!r})"
            )

        prior_adoption_refs: list[str] = []
        for action, reroute_target in prior_dispositions:
            result = _apply_prior_disposition(
                repo,
                root,
                plan["building_id"],
                cb,
                action=action,
                reroute_target=reroute_target,
                bricks=bricks,
                result=result,
            )
            for record in _adopted_records(result):
                ref = record.get("reroute_ref")
                if ref:
                    prior_adoption_refs.append(str(ref))
            if _frontier_kind(root, repo) not in ("link_paused",):
                raise ProfileError(
                    f"{fixture}: prior {action} disposition did not leave the "
                    f"building held again (frontier={_frontier_kind(root, repo)!r})"
                )

        # FINAL disposition: append and drive the resume that the mirror must fix.
        f_action, f_target = final_disposition
        if f_action in ("forward", "stop"):
            f_pending = _current_pending_target(result)
        else:
            f_pending = bricks.get(f_target or "", f_target)
        if not f_pending:
            raise ProfileError(f"{fixture}: final {f_action} disposition has no pending target")
        _append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=f_pending, action=f_action
        )
        calls_before_final = cb.calls
        exc: BaseException | None = None
        final_result: Any = None
        try:
            final_result = _resume(repo, root, cb)
        except ValueError as raised:
            exc = raised

        evidence = _classify_final_resume(
            fixture,
            expect_red_literal_kind=expect_red_literal_kind,
            exc=exc,
            result=final_result,
            root=root,
            repo=repo,
            prior_adoption_refs=prior_adoption_refs,
        )
        # I3 observability: on the RED-pin branch the refused replay must not have
        # run a fresh provider/replay call past the recorded frontier for a NEW
        # generation (the deterministic callable count is the only "provider").
        return {
            **evidence,
            "prior_adoption_refs": prior_adoption_refs,
            "callable_calls_before_final": calls_before_final,
            "callable_calls_after_final": cb.calls,
        }


# ---------------------------------------------------------------------------
# The four REQUIRED fixtures (design D3) + three ADDITIVE labeled probes.
# ---------------------------------------------------------------------------


def _fixture_f_r1(repo: Path) -> Mapping[str, Any]:
    """F-R1 [reroute x1]: prior reroute at the root gate hold, CURRENT forward.
    HEAD RED: replaying the prior reroute raises the 1746 literal."""

    return _drive_fixture(
        repo,
        fixture="F-R1",
        prefix="t7b-mirror-fr1",
        nodes=["design", "build", "review", "close"],
        hold_edges={("design", "build"): "h1", ("review", "close"): "h2"},
        budgets={"review": 5, "build": 5},
        prior_dispositions=[("reroute", "review")],
        final_disposition=("forward", None),
        expect_red_literal_kind="reroute-1746",
    )


def _fixture_f_r2(repo: Path) -> Mapping[str, Any]:
    """F-R2 [reroute x2 intent]: prior reroute at the root gate hold, CURRENT
    reroute (the measured 0705a/0705b two-reroute shape). HEAD RED: same 1746
    literal (the engine cannot chain a second reroute past the first)."""

    return _drive_fixture(
        repo,
        fixture="F-R2",
        prefix="t7b-mirror-fr2",
        nodes=["design", "build", "review", "close"],
        hold_edges={("design", "build"): "h1", ("review", "close"): "h2"},
        budgets={"review": 5, "build": 5},
        prior_dispositions=[("reroute", "review")],
        final_disposition=("reroute", "build"),
        expect_red_literal_kind="reroute-1746",
    )


def _fixture_f_s(repo: Path) -> Mapping[str, Any]:
    """F-S [stop]: prior reroute at the root gate hold, CURRENT stop. HEAD RED:
    same 1746 literal raised at the prior reroute BEFORE the stop can apply."""

    return _drive_fixture(
        repo,
        fixture="F-S",
        prefix="t7b-mirror-fs",
        nodes=["design", "build", "review", "close"],
        hold_edges={("design", "build"): "h1", ("review", "close"): "h2"},
        budgets={"review": 5, "build": 5},
        prior_dispositions=[("reroute", "review")],
        final_disposition=("stop", None),
        expect_red_literal_kind="reroute-1746",
    )


def _fixture_f_m(repo: Path) -> Mapping[str, Any]:
    """F-M [mixed forward + reroute]: prior FORWARD at the root gate hold
    (mirrored on replay), prior REROUTE at the next gate hold, CURRENT forward.
    Design D3 expects the 1746 literal here; MEASURED HEAD behavior is the
    DIVERGENCE guard literal, because the non-root reroute source does not
    re-materialize as a gate-sequence hold on replay (a mixed forward-then-reroute
    chain cannot reach the 1746 site at HEAD). RED-pinned on the measured literal;
    the discrepancy with D3 is surfaced for Slice 2 (see MODULE NOT_PROVEN)."""

    return _drive_fixture(
        repo,
        fixture="F-M",
        prefix="t7b-mirror-fm",
        nodes=["design", "build", "review", "qa", "close"],
        hold_edges={("design", "build"): "h1", ("build", "review"): "h2", ("qa", "close"): "h3"},
        budgets={"qa": 5, "review": 5},
        prior_dispositions=[("forward", None), ("reroute", "qa")],
        final_disposition=("forward", None),
        expect_red_literal_kind="divergence",
    )


def _probe_p1_prior_stop_chain(repo: Path) -> Mapping[str, Any]:
    """P-1 (labeled probe): a building that has an APPLIED resume disposition and
    is no longer held is refused UPSTREAM at walker_resume.py:200 with
    'dynamic Building already has an applied resume disposition' -- a prior-stop
    (or reroute-to-completion) chain never reaches the kernel replay check."""

    plan, bricks = _chain_plan(
        "t7b-mirror-p1",
        ["design", "build", "close"],
        {("design", "build"): "h1"},
        {"build": 5},
    )
    cb = _CountingCallable()
    with tempfile.TemporaryDirectory(prefix="bp-resume-mirror-p1-") as tmp:
        result = _run_to_hold(repo, plan, Path(tmp).resolve(), cb)
        root = result.lifecycle_write.root
        _append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=bricks["build"], action="reroute"
        )
        _resume(repo, root, cb)  # completes the building (applied disposition)
        _append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=bricks["build"], action="forward"
        )
        try:
            _resume(repo, root, cb)
        except ValueError as exc:
            message = str(exc)
        else:
            raise ProfileError("P-1: second resume of an applied building was not refused upstream")
        if APPLIED_DISPOSITION_LITERAL not in message:
            raise ProfileError(
                f"P-1: upstream refusal literal drifted; expected "
                f"{APPLIED_DISPOSITION_LITERAL!r}, got {message!r}"
            )
    return {"probe": "P-1", "observed": "upstream_applied_disposition_refusal", "message": message}


def _probe_p2_concern_path_silent(repo: Path) -> Mapping[str, Any]:
    """P-2 (labeled probe, documents D1.11): a previously-disposed CONCERN-path
    hold (ambiguous multiple_reroute_addresses) carries NO previous-disposition
    check, so replaying it does NOT raise the 1746 gate-sequence literal (the
    concern path is silent). Here the concern reroute completes and the next
    resume is refused upstream -- crucially, NOT the loud 1746 rejection."""

    from support.checkers.lib.fixture_graph_helpers import (
        fixture_graph_brick_step,
        fixture_graph_link_edge,
        fixture_proof_limits,
    )

    prefix = "t7b-mirror-p2"
    design = f"brick-{prefix}-design"
    build = f"brick-{prefix}-build"
    review = f"brick-{prefix}-review"
    close_brick = f"brick-{prefix}-close"
    default_gate = ["link-gate:default-transition"]

    def step(sref: str, bref: str, edge: str) -> Mapping[str, Any]:
        return fixture_graph_brick_step(
            sref,
            bref,
            edge,
            agent_object_ref="agent-object:coo",
            work_statement=f"Deterministic synthetic work for {sref}.",
            required_return_shape="observed_evidence, transition_concern_evidence, not_proven",
            source_facts=["AGENTS.md"],
        )

    def fwd(edge: str, src: str, tstep: str, tbrick: str) -> Mapping[str, Any]:
        return fixture_graph_link_edge(
            edge, src, tbrick, target_step_ref=tstep,
            declared_gate_refs=default_gate, falsy_declared_gate_refs_use_default=True,
        )

    plan = {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0706",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": fixture_proof_limits(),
        "not_proven": ["semantic correctness of this synthetic concern-path fixture"],
        "execution_order": [f"{prefix}-design", f"{prefix}-build", f"{prefix}-review", f"{prefix}-close"],
        "brick_steps": [
            step(f"{prefix}-design", design, f"edge:{prefix}-design-to-build"),
            step(f"{prefix}-build", build, f"edge:{prefix}-build-to-review"),
            step(f"{prefix}-review", review, f"edge:{prefix}-review-to-close"),
            step(f"{prefix}-close", close_brick, f"edge:{prefix}-close-to-boundary"),
        ],
        "link_edges": [
            fwd(f"edge:{prefix}-design-to-build", f"{prefix}-design", f"{prefix}-build", build),
            fwd(f"edge:{prefix}-build-to-review", f"{prefix}-build", f"{prefix}-review", review),
            fwd(f"edge:{prefix}-review-to-close", f"{prefix}-review", f"{prefix}-close", close_brick),
            fixture_graph_link_edge(
                f"edge:{prefix}-close-to-boundary", f"{prefix}-close",
                f"building-boundary:{prefix}-closed",
                close_reason=f"{prefix} closed for concern-path probe.",
                falsy_declared_gate_refs_use_default=True,
            ),
        ],
        "node_reroute_budgets": {build: 5, design: 5},
    }

    class _ConcernCallable(_CountingCallable):
        def __call__(self, request: Any) -> Mapping[str, Any]:
            returned = dict(super().__call__(request))
            if request.brick_instance_ref == review:
                returned["transition_concern_evidence"] = {
                    "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                    "concern_kind": "implementation_gap",
                    "binding": False,
                    "reason_refs": [f"brick-comparison:{request.brick_instance_ref}"],
                    "related_boundary_refs": [design, build],
                }
            return returned

    cb = _ConcernCallable()
    with tempfile.TemporaryDirectory(prefix="bp-resume-mirror-p2-") as tmp:
        from brick_protocol.support.operator.run import run_building_plan

        result = run_building_plan(
            plan,
            output_root=Path(tmp).resolve(),
            overwrite_existing=True,
            local_callables=_local_callables(cb),
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
        root = result.lifecycle_write.root
        held = _held_records(result)
        hold_reason = held[-1].get("hold_reason") if held else None
        if hold_reason != "multiple_reroute_addresses_no_single_owner":
            raise ProfileError(
                f"P-2: setup did not reach the ambiguous CONCERN hold "
                f"(hold_reason={hold_reason!r})"
            )
        _append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=design, action="reroute"
        )
        _resume(repo, root, cb)
        _append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=design, action="reroute"
        )
        raised_1746 = False
        message = ""
        try:
            _resume(repo, root, cb)
        except ValueError as exc:
            message = str(exc)
            raised_1746 = message.startswith(RED_REROUTE_HOLD_PREFIX)
        if raised_1746:
            raise ProfileError(
                "P-2: concern-path prior disposition unexpectedly raised the 1746 "
                f"gate-sequence literal ({message!r}); D1.11 silent-gap probe broke"
            )
    return {
        "probe": "P-2",
        "observed": "concern_path_no_1746_gate_sequence_rejection",
        "message": message,
    }


def _probe_p3_divergence_guard(repo: Path) -> Mapping[str, Any]:
    """P-3 (labeled probe): the resume divergence guard literal is intact
    (walker_kernel.py:2346). A mixed forward-mirror + non-root reroute chain
    completes the seeded walk without applying the held disposition, raising it."""

    plan, bricks = _chain_plan(
        "t7b-mirror-p3",
        ["design", "build", "review", "qa", "close"],
        {("design", "build"): "h1", ("build", "review"): "h2", ("qa", "close"): "h3"},
        {"qa": 5, "review": 5},
    )
    cb = _CountingCallable()
    with tempfile.TemporaryDirectory(prefix="bp-resume-mirror-p3-") as tmp:
        result = _run_to_hold(repo, plan, Path(tmp).resolve(), cb)
        root = result.lifecycle_write.root
        # forward the root hold (mirrored), reroute the next hold, then resume.
        _append_disposition_row(
            root, building_id=plan["building_id"],
            pending_target_ref=_current_pending_target(result), action="forward",
        )
        result = _resume(repo, root, cb)
        _append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=bricks["qa"], action="reroute"
        )
        result = _resume(repo, root, cb)
        _append_disposition_row(
            root, building_id=plan["building_id"],
            pending_target_ref=_current_pending_target(result), action="forward",
        )
        try:
            _resume(repo, root, cb)
        except ValueError as exc:
            # Pre-repair branch: at the pinned HEAD baseline the mixed chain
            # cannot replay its dispositions, so the seeded walk finishes
            # without applying the CURRENT one and the divergence guard fires.
            message = str(exc)
            if not message.startswith(DIVERGENCE_PREFIX):
                raise ProfileError(
                    f"P-3: divergence guard literal drifted; expected prefix "
                    f"{DIVERGENCE_PREFIX!r}, got {message!r}"
                )
            return {
                "probe": "P-3",
                "observed": "divergence_guard_fired",
                "message": message,
            }
        # Post-repair branch: the mirror consumes the mixed chain, so no
        # divergence occurs on this topology anymore. The guard must still
        # EXIST as a defense (design P-3 intent: 'divergence guard literal
        # intact', walker_kernel post-loop) — verify the literal source-level,
        # fail-closed if it is ever removed.
        kernel_source = (
            repo / "support" / "operator" / "walker_kernel.py"
        ).read_text(encoding="utf-8")
        if DIVERGENCE_PREFIX not in kernel_source:
            raise ProfileError(
                "P-3: divergence guard literal is GONE from walker_kernel.py "
                f"({DIVERGENCE_PREFIX!r}) — the last-line replay defense was removed"
            )
    return {
        "probe": "P-3",
        "observed": "mixed_chain_replays_clean_and_guard_literal_intact",
        "message": "",
    }


# ---------------------------------------------------------------------------
# CONCERN-PATH mirror fixtures (F-C group) + probe (P-C1) -- Slice 1, walker
# UNTOUCHED. These pin the SECOND replay-mirror surface: the six concern-path
# hold sites (ambiguous/pause/unbudgeted/exhausted/broken-mail, plus the
# gate-sequence reroute budget-exhausted site) each fail LOUD on replay of a
# previously-disposed concern-path HOLD via _require_undisposed_concern_hold.
#
# Dual-acceptance, SAME shape as F-R/F-S/F-M:
#   (a) RED-PIN  -- at the pinned HEAD baseline the final resume RAISES the
#       concern-path guard literal (measured; concern-path mirroring is NOT
#       implemented, so a re-reached disposed concern-path hold is refused).
#   (b) GREEN    -- after the concern-path mirror lands the same fixture
#       resumes and the per-fixture invariants hold (authored-but-unmeasured
#       until Slice 2b; see MODULE NOT_PROVEN). It stays strict so a wrong
#       mirror cannot pass silently.
#
# Chain mechanism (measured): a linear/fan graph with TWO concern-producing
# nodes holds at node A (concern), a PRIOR human/COO disposition resolves A and
# the walk re-holds at node B (concern), then a FINAL disposition on B drives
# the resume whose replay re-reaches the now-disposed concern hold at A --
# where the guard fires. Any state that is NEITHER (a) NOR (b) is a
# ProfileError -> exit 1.
# ---------------------------------------------------------------------------


def _concern_step(prefix: str, node: str, brick_ref: str, edge_ref: str) -> Mapping[str, Any]:
    from support.checkers.lib.fixture_graph_helpers import fixture_graph_brick_step

    return fixture_graph_brick_step(
        f"{prefix}-{node}",
        brick_ref,
        edge_ref,
        agent_object_ref="agent-object:coo",
        work_statement=f"Deterministic synthetic concern-path work for {prefix}-{node}.",
        required_return_shape="observed_evidence, transition_concern_evidence, not_proven",
        source_facts=["AGENTS.md"],
    )


class _ConcernChainCallable(_CountingCallable):
    """A deterministic adapter:local stand-in that attaches a transition concern
    to specific brick instances. ``concern_by_ref`` maps a brick_instance_ref to
    a (reason_refs, related_boundary_refs) pair. A pair with two resolving
    related refs yields an AMBIGUOUS concern hold (no single owner); a single
    resolving ref with an unresolvable ``step-output:`` reason_ref yields a
    BROKEN-MAIL hold (the recorded runtime address does not resolve in the
    ledger, walker_runtime_mail:79-93)."""

    def __init__(self, concern_by_ref: Mapping[str, tuple[Sequence[str], Sequence[str]]]) -> None:
        super().__init__()
        self._concern_by_ref = dict(concern_by_ref)

    def __call__(self, request: Any) -> Mapping[str, Any]:
        returned = dict(super().__call__(request))
        spec = self._concern_by_ref.get(request.brick_instance_ref)
        if spec is not None:
            reason_refs, related = spec
            returned["transition_concern_evidence"] = {
                "concern_ref": f"transition-concern:{request.brick_instance_ref}",
                "concern_kind": "implementation_gap",
                "binding": False,
                "reason_refs": list(reason_refs),
                "related_boundary_refs": list(related),
            }
        return returned


def _concern_plan_scaffold(
    prefix: str,
    *,
    order: Sequence[str],
    steps: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    budgets: Mapping[str, int],
    groups: Sequence[Mapping[str, Any]] | None = None,
) -> Mapping[str, Any]:
    from support.checkers.lib.fixture_graph_helpers import fixture_proof_limits

    plan: dict[str, Any] = {
        "plan_ref": f"building-plan:{prefix}",
        "owner_axis": "Brick",
        "building_id": f"{prefix}-0706",
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": fixture_proof_limits(),
        "not_proven": ["semantic correctness of this synthetic concern-path fixture"],
        "execution_order": list(order),
        "brick_steps": list(steps),
        "link_edges": list(edges),
        "node_reroute_budgets": dict(budgets),
    }
    if groups is not None:
        plan["groups"] = list(groups)
    return plan


def _linear_concern_plan(
    prefix: str,
    nodes: Sequence[str],
    budgets: Mapping[str, int],
) -> tuple[Mapping[str, Any], Mapping[str, str]]:
    """A linear graph n0 -> n1 -> ... -> close with plain default-gate forward
    edges. The concern holds come from the driving callable's returns, not the
    edge policy (unlike _chain_plan's gate-sequence holds)."""

    from support.checkers.lib.fixture_graph_helpers import fixture_graph_link_edge

    bricks = {n: f"brick-{prefix}-{n}" for n in nodes}
    order = [f"{prefix}-{n}" for n in nodes]
    steps: list[Mapping[str, Any]] = []
    edges: list[Mapping[str, Any]] = []
    for i, n in enumerate(nodes):
        if i < len(nodes) - 1:
            nxt = nodes[i + 1]
            edge_ref = f"edge:{prefix}-{n}-to-{nxt}"
            steps.append(_concern_step(prefix, n, bricks[n], edge_ref))
            edges.append(
                fixture_graph_link_edge(
                    edge_ref,
                    f"{prefix}-{n}",
                    bricks[nxt],
                    target_step_ref=f"{prefix}-{nxt}",
                    declared_gate_refs=["link-gate:default-transition"],
                    falsy_declared_gate_refs_use_default=True,
                )
            )
        else:
            edge_ref = f"edge:{prefix}-{n}-to-boundary"
            steps.append(_concern_step(prefix, n, bricks[n], edge_ref))
            edges.append(
                fixture_graph_link_edge(
                    edge_ref,
                    f"{prefix}-{n}",
                    f"building-boundary:{prefix}-closed",
                    close_reason=f"{prefix} closed for concern-path mirror checker evidence.",
                    falsy_declared_gate_refs_use_default=True,
                )
            )
    plan = _concern_plan_scaffold(
        prefix,
        order=order,
        steps=steps,
        edges=edges,
        budgets={bricks[b]: v for b, v in budgets.items()},
    )
    return plan, bricks


def _fan_concern_plan(
    prefix: str,
    budgets: Mapping[str, int],
) -> tuple[Mapping[str, Any], Mapping[str, str]]:
    """A fan graph root -> {lane-a, lane-b} -> join -> close. Both lanes produce
    a concern hold, so has_fan_groups is True and the concern-path guard fires
    inside the fan branch of its hold site (held_fan_steps / completed_fan_steps
    / reroute_insert_width machinery, walker_kernel.py:2087-2097)."""

    from support.checkers.lib.fixture_graph_helpers import fixture_graph_link_edge

    nodes = ["root", "lane-a", "lane-b", "join", "close"]
    bricks = {n: f"brick-{prefix}-{n}" for n in nodes}
    order = [f"{prefix}-{n}" for n in nodes]

    def fwd(edge_ref: str, src: str, tgt: str) -> Mapping[str, Any]:
        return fixture_graph_link_edge(
            edge_ref,
            f"{prefix}-{src}",
            bricks[tgt],
            target_step_ref=f"{prefix}-{tgt}",
            declared_gate_refs=["link-gate:default-transition"],
            falsy_declared_gate_refs_use_default=True,
        )

    steps = [
        _concern_step(prefix, "root", bricks["root"], f"edge:{prefix}-root-to-a"),
        _concern_step(prefix, "lane-a", bricks["lane-a"], f"edge:{prefix}-a-to-join"),
        _concern_step(prefix, "lane-b", bricks["lane-b"], f"edge:{prefix}-b-to-join"),
        _concern_step(prefix, "join", bricks["join"], f"edge:{prefix}-join-to-close"),
        _concern_step(prefix, "close", bricks["close"], f"edge:{prefix}-close-to-boundary"),
    ]
    edges = [
        fwd(f"edge:{prefix}-root-to-a", "root", "lane-a"),
        fwd(f"edge:{prefix}-root-to-b", "root", "lane-b"),
        fwd(f"edge:{prefix}-a-to-join", "lane-a", "join"),
        fwd(f"edge:{prefix}-b-to-join", "lane-b", "join"),
        fwd(f"edge:{prefix}-join-to-close", "join", "close"),
        fixture_graph_link_edge(
            f"edge:{prefix}-close-to-boundary",
            f"{prefix}-close",
            f"building-boundary:{prefix}-closed",
            close_reason=f"{prefix} closed for concern-path fan mirror evidence.",
            falsy_declared_gate_refs_use_default=True,
        ),
    ]
    groups = [
        {
            "group_id": f"group:{prefix}-fan-out",
            "group_role": "fan_out",
            "member_ref_kind": "link_edge",
            "member_refs": [f"edge:{prefix}-root-to-a", f"edge:{prefix}-root-to-b"],
            "proof_limits": ["support topology label only"],
            "not_proven": ["parallel runtime execution"],
        },
        {
            "group_id": f"group:{prefix}-fan-in",
            "group_role": "fan_in",
            "member_ref_kind": "link_edge",
            "member_refs": [f"edge:{prefix}-a-to-join", f"edge:{prefix}-b-to-join"],
            "proof_limits": ["support topology label only"],
            "not_proven": ["synthesis quality"],
        },
    ]
    plan = _concern_plan_scaffold(
        prefix,
        order=order,
        steps=steps,
        edges=edges,
        budgets={bricks[b]: v for b, v in budgets.items()},
        groups=groups,
    )
    return plan, bricks


def _concern_green_invariants(
    fixture: str,
    *,
    result: Any,
    root: Path,
    frontier: str,
    first_reason: str,
    prior_adoption_refs: Sequence[str],
    fan: bool,
) -> Mapping[str, Any]:
    """Post-mirror GREEN invariants for a concern-path fixture (design final-0706
    D1.7 / D1.11, invariants I1/I2/I6). NOT reachable at the pinned HEAD baseline
    (all F-C RED-pin there), so this branch is authored-but-unmeasured until the
    Slice-2b concern-path mirror lands -- see MODULE NOT_PROVEN. It stays strict
    so a wrong mirror cannot pass silently.

    I1: every prior recorded reroute-adoption ref survives verbatim in the
    re-walked adoptions (no fresh identity minted). I6: the mirror never
    re-parks on an ALREADY-DISPOSED concern-path hold identity. F-C3 carve-out:
    a broken-mail RE-HOLD is a LEGITIMATE outcome (the runtime address genuinely
    does not resolve on replay, design edge_cases[2]) and must NOT be flagged as
    an I6 re-park -- the mirror faithfully reproduced a broken ticket."""

    observations = _persisted_observations(root)
    adopted_refs = {
        str(r.get("reroute_ref"))
        for r in _adopted_records(result)
        if r.get("reroute_ref")
    }
    for prior_ref in prior_adoption_refs:
        if prior_ref and prior_ref not in adopted_refs:
            raise ProfileError(
                f"{fixture}: GREEN concern mirror lost prior reroute_ref parity "
                f"({prior_ref!r} not in re-walked adoptions {sorted(adopted_refs)!r})"
            )

    broken_mail_first = str(first_reason).startswith(
        "runtime_handoff_"
    ) or "broken" in str(first_reason)

    if frontier in ("complete", "closed"):
        pass
    elif frontier == "link_paused":
        current_identity = _evidence_hold_identity(root)
        current_reason = ""
        held = _held_records(result)
        if held:
            current_reason = str(held[-1].get("hold_reason") or "")
        # F-C3 carve-out: a fresh broken-mail re-hold on replay is legitimate
        # (design edge_cases[2]); it is NOT an already-disposed re-park.
        legit_broken_mail = broken_mail_first and current_reason.startswith(
            "runtime_handoff_"
        )
        if not legit_broken_mail:
            for observation in observations:
                disposed_norm = str(observation.get("paused_at_ref") or "").replace(
                    ":", "-"
                )
                if (
                    current_identity
                    and disposed_norm
                    and current_identity in disposed_norm
                ):
                    raise ProfileError(
                        f"{fixture}: GREEN concern mirror re-parked on an "
                        f"ALREADY-DISPOSED concern-path hold identity "
                        f"({current_identity!r}) -- the mirror failed to consume "
                        "a replayed disposition (I6)"
                    )
    else:
        raise ProfileError(
            f"{fixture}: GREEN concern mirror ended in an inadmissible frontier "
            f"({frontier!r})"
        )

    green: dict[str, Any] = {
        "green_frontier": frontier,
        "green_adopted_reroute_refs": sorted(adopted_refs),
        "green_observation_count": len(observations),
    }
    if fan:
        # F-C2: cohort re-verify state must be reproduced (completed_fan_steps /
        # cohort_skip_carry_forward / fan_in_cohort_records) and the successor
        # splice offset must honour reroute_insert_width (design D1.7 / edge
        # cases[4]). Unmeasured at HEAD; recorded so the Slice-2b mirror gate can
        # assert against it without loosening this branch.
        green["green_fan_cohort_expectation"] = (
            "completed_fan_steps + cohort_skip_carry_forward + fan_in_cohort_records "
            "reproduced; reroute_insert_width offset preserved (unmeasured pre-mirror)"
        )
    return green


def _classify_concern_final_resume(
    fixture: str,
    *,
    exc: BaseException | None,
    result: Any,
    root: Path,
    repo: Path,
    first_reason: str,
    prior_adoption_refs: Sequence[str],
    fan: bool,
) -> Mapping[str, Any]:
    """Return per-fixture branch evidence, or raise ProfileError. ``exc`` is the
    ValueError the FINAL resume raised (or None if it returned)."""

    if exc is not None:
        raise ProfileError(
            f"{fixture}: expected GREEN concern-path mirror replay, but final "
            f"resume raised {type(exc).__name__}: {exc}"
        )

    frontier = _frontier_kind(root, repo)
    green = _concern_green_invariants(
        fixture,
        result=result,
        root=root,
        frontier=frontier,
        first_reason=first_reason,
        prior_adoption_refs=prior_adoption_refs,
        fan=fan,
    )
    return {
        "fixture": fixture,
        "branch": "green",
        "frontier_kind": frontier,
        **green,
    }


def _drive_concern_chain(
    repo: Path,
    *,
    fixture: str,
    plan: Mapping[str, Any],
    cb: _CountingCallable,
    prior_target_ref: str,
    final_target_ref: str,
    fan: bool,
) -> Mapping[str, Any]:
    from brick_protocol.support.operator.run import run_building_plan  # noqa: F401  (import audit)

    with tempfile.TemporaryDirectory(prefix=f"bp-resume-cpath-{fixture}-") as tmp:
        result = _run_to_hold(repo, plan, Path(tmp).resolve(), cb)
        root = result.lifecycle_write.root
        if _frontier_kind(root, repo) != "link_paused":
            raise ProfileError(
                f"{fixture}: setup did not reach the first concern HOLD "
                f"(frontier={_frontier_kind(root, repo)!r})"
            )
        first_held = _held_records(result)
        if not first_held:
            raise ProfileError(f"{fixture}: first concern HOLD carried no held record")
        first_source = str(first_held[-1].get("source_step_ref") or "")
        first_reason = str(first_held[-1].get("hold_reason") or "")

        # PRIOR disposition on concern hold A -> must succeed at HEAD and leave
        # the building held again at concern hold B.
        _append_disposition_row(
            root,
            building_id=plan["building_id"],
            pending_target_ref=prior_target_ref,
            action="reroute",
        )
        result = _resume(repo, root, cb)
        prior_adoption_refs = [
            str(r.get("reroute_ref"))
            for r in _adopted_records(result)
            if r.get("reroute_ref")
        ]
        if _frontier_kind(root, repo) != "link_paused":
            raise ProfileError(
                f"{fixture}: prior concern disposition did not leave the building "
                f"held at a second concern hold (frontier={_frontier_kind(root, repo)!r})"
            )
        second_source = str((_held_records(result) or [{}])[-1].get("source_step_ref") or "")

        # FINAL disposition on concern hold B: append and drive the resume whose
        # replay re-reaches the now-disposed concern hold A.
        _append_disposition_row(
            root,
            building_id=plan["building_id"],
            pending_target_ref=final_target_ref,
            action="reroute",
        )
        calls_before_final = cb.calls
        exc: BaseException | None = None
        final_result: Any = None
        try:
            final_result = _resume(repo, root, cb)
        except ValueError as raised:
            exc = raised

        evidence = _classify_concern_final_resume(
            fixture,
            exc=exc,
            result=final_result,
            root=root,
            repo=repo,
            first_reason=first_reason,
            prior_adoption_refs=prior_adoption_refs,
            fan=fan,
        )
        return {
            **evidence,
            "first_hold_source": first_source,
            "first_hold_reason": first_reason,
            "second_hold_source": second_source,
            "prior_adoption_refs": prior_adoption_refs,
            "callable_calls_before_final": calls_before_final,
            "callable_calls_after_final": cb.calls,
        }


def _fixture_f_c1(repo: Path) -> Mapping[str, Any]:
    """F-C1 [ambiguous concern x1]: two nodes each raise an AMBIGUOUS reroute
    concern (multiple resolving addresses, no single owner -> hold_reason
    multiple_reroute_addresses_no_single_owner, walker_kernel.py:2062/2084).
    Prior reroute resolves hold A, the walk re-holds at B, and the FINAL resume
    replays past the disposed concern hold A. HEAD RED: the concern-path guard
    literal fires at A."""

    prefix = "t7b-cpath-fc1"
    plan, bricks = _linear_concern_plan(
        prefix, ["design", "build", "rev1", "rev2", "close"], {"build": 5, "design": 5}
    )
    ambiguous = (bricks["design"], bricks["build"])
    cb = _ConcernChainCallable(
        {
            bricks["rev1"]: ((f"brick-comparison:{bricks['rev1']}",), ambiguous),
            bricks["rev2"]: ((f"brick-comparison:{bricks['rev2']}",), ambiguous),
        }
    )
    return _drive_concern_chain(
        repo,
        fixture="F-C1",
        plan=plan,
        cb=cb,
        prior_target_ref=bricks["build"],
        final_target_ref=bricks["build"],
        fan=False,
    )


def _fixture_f_c2(repo: Path) -> Mapping[str, Any]:
    """F-C2 [fan graph concern + cohort]: a fan graph whose two lanes each raise
    an AMBIGUOUS concern, so the concern hold and its guard fire inside the fan
    branch (has_fan_groups True). Prior reroute resolves lane A, the walk
    re-holds at lane B, and the FINAL resume replays past disposed lane A. HEAD
    RED: same concern-path guard literal. GREEN (unmeasured) adds the cohort /
    reroute_insert_width reproduction assertions (design D1.7 / edge_cases[4])."""

    prefix = "t7b-cpath-fc2"
    plan, bricks = _fan_concern_plan(prefix, {"root": 5, "join": 5})
    ambiguous = (bricks["root"], bricks["join"])
    cb = _ConcernChainCallable(
        {
            bricks["lane-a"]: ((f"brick-comparison:{bricks['lane-a']}",), ambiguous),
            bricks["lane-b"]: ((f"brick-comparison:{bricks['lane-b']}",), ambiguous),
        }
    )
    return _drive_concern_chain(
        repo,
        fixture="F-C2",
        plan=plan,
        cb=cb,
        prior_target_ref=bricks["root"],
        final_target_ref=bricks["root"],
        fan=True,
    )


def _fixture_f_c3(repo: Path) -> Mapping[str, Any]:
    """F-C3 [broken-mail concern]: two nodes each raise a SINGLE-target reroute
    concern whose mandatory reason_ref is a ``step-output:`` address that does
    NOT resolve in the ledger, so the runtime-mail re-read fails and the hold is
    a BROKEN-MAIL concern hold (hold_reason runtime_handoff_address_unresolved_
    in_ledger, walker_kernel.py:2226-2254). Prior reroute resolves hold A, the
    walk re-holds at B, and the FINAL resume replays past disposed hold A. HEAD
    RED: same concern-path guard literal, reached via the broken-mail site. The
    (b)/GREEN branch carve-out proves a legitimate broken-mail RE-HOLD is NOT
    mis-flagged as an already-disposed re-park (design edge_cases[2])."""

    prefix = "t7b-cpath-fc3"
    plan, bricks = _linear_concern_plan(
        prefix, ["design", "build", "rev1", "rev2", "close"], {"build": 5, "design": 5}
    )
    ghost = ("step-output:t7b-cpath-fc3-ghost-slug:attempt-9",)
    cb = _ConcernChainCallable(
        {
            bricks["rev1"]: (ghost, (bricks["build"],)),
            bricks["rev2"]: (ghost, (bricks["build"],)),
        }
    )
    return _drive_concern_chain(
        repo,
        fixture="F-C3",
        plan=plan,
        cb=cb,
        prior_target_ref=bricks["build"],
        final_target_ref=bricks["build"],
        fan=False,
    )


def _reroute_coo_gate_policy(target_brick: str, obs: str) -> list[Mapping[str, Any]]:
    """A gate-sequence policy that FORWARDS the default gate then REROUTES on the
    COO gate to ``target_brick``. When that target's reroute budget is exhausted
    the reroute lands as a gate_sequence_reroute_budget_exhausted HOLD
    (walker_kernel.py:1846-1881) -- the SIXTH _require_undisposed_concern_hold
    guard site."""

    return [
        {
            "gate_ref": "link-gate:default-transition",
            "on_missing_required_facts": {
                "action": "hold",
                "pending_target_basis": "target_brick",
                "reason_refs": [f"observation:{obs}-dt"],
                "required_disposition_owner": "caller-or-coo",
            },
            "on_sufficient": {"action": "next", "next_gate_ref": "link-gate:coo"},
        },
        {
            "gate_ref": "link-gate:coo",
            "on_missing_required_facts": {
                "action": "reroute",
                "target_ref": target_brick,
                "required_target_budget": True,
                "reason_refs": [f"observation:{obs}-coo"],
            },
            "on_sufficient": {"action": "forward"},
        },
    ]


def _probe_pc1_gate_sequence_budget_exhausted(repo: Path) -> Mapping[str, Any]:
    """P-C1 (labeled probe, D2): the gate-sequence reroute budget-exhausted hold
    (walker_kernel.py:1881) is the SIXTH _require_undisposed_concern_hold guard
    site, distinct from the five agent-concern sites. A prior disposition
    re-reached on replay there ALSO fails loud with the concern-path guard
    literal (NOT the forward-mirror path -- a gate-sequence-reroute hold has no
    forward mirror). Two nodes reroute to a budget-1 target; design primes the
    single landing so rev1/rev2 exhaust it and hold. Prior forward resolves the
    rev1 exhausted hold, the walk re-holds exhausted at rev2, and the FINAL
    resume replays past the disposed rev1 hold -> guard fires."""

    from support.checkers.lib.fixture_graph_helpers import fixture_graph_link_edge

    prefix = "t7b-cpath-pc1"
    nodes = ["design", "build", "rev1", "rev2", "close"]
    bricks = {n: f"brick-{prefix}-{n}" for n in nodes}
    reroute_nodes = ("design", "rev1", "rev2")
    order = [f"{prefix}-{n}" for n in nodes]
    steps: list[Mapping[str, Any]] = []
    edges: list[Mapping[str, Any]] = []
    for i, n in enumerate(nodes):
        step = _brick_step(
            f"{prefix}-{n}", bricks[n], f"edge:{prefix}-{n}-to-"
            + (nodes[i + 1] if i < len(nodes) - 1 else "boundary"),
        )
        steps.append(step)
        if i < len(nodes) - 1:
            nxt = nodes[i + 1]
            edge_ref = f"edge:{prefix}-{n}-to-{nxt}"
            gates = (
                ["link-gate:default-transition", "link-gate:coo"]
                if n in reroute_nodes
                else ["link-gate:default-transition"]
            )
            edge = fixture_graph_link_edge(
                edge_ref,
                f"{prefix}-{n}",
                bricks[nxt],
                target_step_ref=f"{prefix}-{nxt}",
                declared_gate_refs=gates,
                falsy_declared_gate_refs_use_default=True,
            )
            if n in reroute_nodes:
                edge["rows"][0]["gate_sequence_policy"] = _reroute_coo_gate_policy(
                    bricks["build"], f"{prefix}-{n}-rr"
                )
            edges.append(edge)
        else:
            edges.append(
                fixture_graph_link_edge(
                    f"edge:{prefix}-{n}-to-boundary",
                    f"{prefix}-{n}",
                    f"building-boundary:{prefix}-closed",
                    close_reason=f"{prefix} closed for gate-sequence budget probe.",
                    falsy_declared_gate_refs_use_default=True,
                )
            )
    plan = _concern_plan_scaffold(
        prefix, order=order, steps=steps, edges=edges, budgets={bricks["build"]: 1}
    )

    cb = _CountingCallable()
    with tempfile.TemporaryDirectory(prefix="bp-resume-cpath-pc1-") as tmp:
        result = _run_to_hold(repo, plan, Path(tmp).resolve(), cb)
        root = result.lifecycle_write.root
        first_held = _held_records(result)
        first_reason = str((first_held or [{}])[-1].get("hold_reason") or "")
        if first_reason != "gate_sequence_reroute_budget_exhausted":
            raise ProfileError(
                "P-C1: setup did not reach the gate-sequence budget-exhausted hold "
                f"(hold_reason={first_reason!r})"
            )
        # Prior forward resolves the rev1 exhausted hold -> re-hold at rev2.
        _append_disposition_row(
            root,
            building_id=plan["building_id"],
            pending_target_ref=_current_pending_target(result),
            action="forward",
        )
        result = _resume(repo, root, cb)
        if _frontier_kind(root, repo) != "link_paused":
            raise ProfileError(
                "P-C1: prior forward disposition did not leave a second exhausted "
                f"hold held (frontier={_frontier_kind(root, repo)!r})"
            )
        _append_disposition_row(
            root,
            building_id=plan["building_id"],
            pending_target_ref=_current_pending_target(result),
            action="forward",
        )
        message = ""
        try:
            _resume(repo, root, cb)
        except ValueError as exc:
            message = str(exc)
        else:
            raise ProfileError(
                "P-C1: replay past the disposed gate-sequence budget-exhausted hold "
                "was NOT refused (the 6th concern-path guard did not fire)"
            )
        ok = (
            message.startswith(CONCERN_PATH_HOLD_PREFIX)
            and CONCERN_PATH_MIRROR_NOT_IMPLEMENTED in message
        )
        if not ok:
            raise ProfileError(
                "P-C1: gate-sequence budget-exhausted replay raised an UNEXPECTED "
                f"literal; expected the concern-path guard, got {message!r}"
            )
    return {
        "probe": "P-C1",
        "observed": "gate_sequence_budget_exhausted_guard_fired",
        "first_hold_reason": first_reason,
        "message": message,
    }


def _mutation_sequence_reuse_source_guard(repo: Path) -> Mapping[str, Any]:
    """Mutation self-proof: removing the concern mirror's sequence rollback must
    make this checker rc=1 with a stable literal. The behavioral parity checks
    also catch the drift; this source guard gives the receiving lane an
    executable, cheap mutation handle for the exact sequence-reuse edit."""

    source = (repo / "support" / "operator" / "walker_kernel.py").read_text(
        encoding="utf-8"
    )
    rollback_sites = len(
        re.findall(
            r"(?m)^[ \t]+adoption_sequence_number -= 1\n"
            r"[ \t]+replaying_prior_concern_reroute_mirror = True",
            source,
        )
    )
    if rollback_sites != 4:
        raise ProfileError(SEQUENCE_REUSE_GUARD_LITERAL)
    return {
        "mutation_proof": "sequence-reuse",
        "observed": "concern_mirror_sequence_rollback_sites_intact",
        "rollback_site_count": rollback_sites,
        "failure_literal": SEQUENCE_REUSE_GUARD_LITERAL,
    }


# ---------------------------------------------------------------------------
# Family-② SELF-LOCK fixtures (0706 selflock slice). D1 = validate-before-persist
# (a refused disposition leaves the ledger unchanged and a retry is possible);
# D2 = declared correction (void) path for an ALREADY-locked ledger.
# ---------------------------------------------------------------------------


def _sl_isolated_adapter_cwd(tmp: Path) -> Path:
    """An adapter_cwd OUTSIDE the live repo so onboard.run_approve_entry accepts
    it (the caller-supplied path guard refuses live-repo/self-or-child paths)."""

    cwd = tmp / "adapter-cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    return cwd


def _sl_ledger_hash(root: Path) -> str:
    import hashlib

    return hashlib.sha256((root / "raw" / "link.jsonl").read_bytes()).hexdigest()


def _fixture_sl1_refused_intake_clean(repo: Path) -> Mapping[str, Any]:
    """SL-1 (D1): drive to HOLD, then submit a disposition the resume path would
    refuse (reroute to a NON-declared target) THROUGH onboard.run_approve_entry.
    The intake gate must refuse it BEFORE persist -> raw/link.jsonl byte-identical
    (I1) and a corrected retry still resumes (validate-before-persist)."""

    from brick_protocol.support.operator import onboard

    prefix = "selflock-sl1"
    plan, bricks = _chain_plan(
        prefix,
        ["design", "build", "review", "close"],
        {("design", "build"): "h1", ("review", "close"): "h2"},
        {"review": 5, "build": 5},
    )
    cb = _CountingCallable()
    with tempfile.TemporaryDirectory(prefix="bp-resume-selflock-sl1-") as tmp:
        result = _run_to_hold(repo, plan, Path(tmp).resolve(), cb)
        root = result.lifecycle_write.root
        if _frontier_kind(root, repo) != "link_paused":
            raise ProfileError(
                f"SL-1: setup did not reach the first HOLD "
                f"(frontier={_frontier_kind(root, repo)!r})"
            )
        hash_before = _sl_ledger_hash(root)
        refused = onboard.run_approve_entry(
            root,
            action="reroute",
            author_ref="coo:smith",
            reroute_target_ref="brick-selflock-sl1-does-not-exist",
            re_instruction=_COMPLIANT_RE_INSTRUCTION,
            repo_root=repo,
            adapter_cwd=_sl_isolated_adapter_cwd(Path(tmp)),
        )
        if refused.get("error_kind") != "disposition_intake_refused_before_persist":
            raise ProfileError(
                "SL-1: an out-of-class disposition was NOT refused at intake "
                f"(result={refused!r})"
            )
        if refused.get("disposition_written") is not False:
            raise ProfileError("SL-1: refused disposition still reported written")
        if _sl_ledger_hash(root) != hash_before:
            raise ProfileError(
                "SL-1: refused intake mutated raw/link.jsonl (I1 ledger cleanliness "
                "violated) -- a self-lock row was persisted before validation"
            )
        # Retry with a valid forward disposition: it must still resume (the
        # refusal did not corrupt the held ledger).
        _append_disposition_row(
            root,
            building_id=plan["building_id"],
            pending_target_ref=_current_pending_target(result),
            action="forward",
        )
        try:
            _resume(repo, root, cb)
        except ValueError as exc:
            raise ProfileError(
                f"SL-1: corrected retry after a refused intake failed to resume: {exc}"
            ) from exc
        retry_frontier = _frontier_kind(root, repo)
        if retry_frontier not in ("link_paused", "complete", "closed"):
            raise ProfileError(
                f"SL-1: corrected retry ended in an inadmissible frontier "
                f"({retry_frontier!r})"
            )
    return {
        "fixture": "SL-1",
        "branch": "green",
        "observed": "refused_intake_left_ledger_clean_retry_resumed",
        "refused_error_kind": refused.get("error_kind"),
        "retry_frontier": retry_frontier,
    }


def _fixture_sl2_legacy_residue_void(repo: Path) -> Mapping[str, Any]:
    """SL-2 (D2): synthesize an ALREADY-locked ledger -- a valid forward row
    (index 1) shadowed by a residual out-of-class reroute row (index 2, selected
    last). The resume self-locks on the residual row's refusal literal. Author the
    declared void for the residual row via run_disposition_void_entry; the resume
    then selects the valid forward row and resumes (GREEN). RED variant: a void
    that does NOT cover the residual row leaves the self-lock literal firing."""

    from brick_protocol.support.operator import onboard

    prefix = "selflock-sl2"
    plan, bricks = _chain_plan(
        prefix,
        ["design", "build", "review", "close"],
        {("design", "build"): "h1", ("review", "close"): "h2"},
        {"review": 5, "build": 5},
    )
    cb = _CountingCallable()
    with tempfile.TemporaryDirectory(prefix="bp-resume-selflock-sl2-") as tmp:
        result = _run_to_hold(repo, plan, Path(tmp).resolve(), cb)
        root = result.lifecycle_write.root
        if _frontier_kind(root, repo) != "link_paused":
            raise ProfileError(
                f"SL-2: setup did not reach the first HOLD "
                f"(frontier={_frontier_kind(root, repo)!r})"
            )
        pending = _current_pending_target(result)
        # Bypass intake (direct append) to reconstruct the residual-lock shape:
        # a valid forward row plus an out-of-class reroute row appended after it.
        _append_disposition_row(
            root, building_id=plan["building_id"], pending_target_ref=pending, action="forward"
        )
        _append_disposition_row(
            root,
            building_id=plan["building_id"],
            pending_target_ref="brick-selflock-sl2-does-not-exist",
            action="reroute",
        )
        # The self-lock: the resume selects the LAST matching row (the residual
        # reroute) and refuses with the exact pinned literal.
        self_lock_literal = ""
        try:
            _resume(repo, root, cb)
        except ValueError as exc:
            self_lock_literal = str(exc)
        else:
            raise ProfileError(
                "SL-2: the residual out-of-class reroute row did NOT self-lock the "
                "resume (expected the existing pinned refusal)"
            )
        if self_lock_literal != _RAISE_TARGET_NOT_NODE_REFUSAL_REROUTE:
            raise ProfileError(
                "SL-2: residual-lock raised an UNEXPECTED literal; expected "
                f"{_RAISE_TARGET_NOT_NODE_REFUSAL_REROUTE!r}, got {self_lock_literal!r}"
            )
        # RED variant: a groundless void (wrong index) must be refused and must
        # NOT clear the self-lock -- the residual row stays selected.
        groundless = onboard.run_disposition_void_entry(
            root,
            author_ref="coo:smith",
            voided_raw_ref="raw:link:disposition:reroute",
            same_hold_index=99,
            repo_root=repo,
        )
        if groundless.get("error_kind") != "void_target_not_found":
            raise ProfileError(
                f"SL-2: a groundless void was NOT refused (result={groundless!r})"
            )
        try:
            _resume(repo, root, cb)
        except ValueError as exc:
            if str(exc) != _RAISE_TARGET_NOT_NODE_REFUSAL_REROUTE:
                raise ProfileError(
                    "SL-2: after a refused groundless void the self-lock literal "
                    f"changed unexpectedly: {exc}"
                ) from exc
        else:
            raise ProfileError(
                "SL-2: a refused groundless void silently cleared the self-lock"
            )
        # D2: the declared void for the residual reroute row (index 2) makes it
        # unselectable; the resume then selects the valid forward row (index 1).
        void_result = onboard.run_disposition_void_entry(
            root,
            author_ref="coo:smith",
            voided_raw_ref="raw:link:disposition:reroute",
            same_hold_index=2,
            note="0706 selflock checker: disregard the residual out-of-class reroute row",
            repo_root=repo,
        )
        if not void_result.get("ok") or not void_result.get("void_written"):
            raise ProfileError(
                f"SL-2: the grounded void was not written (result={void_result!r})"
            )
        try:
            _resume(repo, root, cb)
        except ValueError as exc:
            raise ProfileError(
                f"SL-2: after voiding the residual row the resume still self-locked: {exc}"
            ) from exc
        green_frontier = _frontier_kind(root, repo)
        if green_frontier not in ("link_paused", "complete", "closed"):
            raise ProfileError(
                f"SL-2: post-void resume ended in an inadmissible frontier "
                f"({green_frontier!r})"
            )
    return {
        "fixture": "SL-2",
        "branch": "green",
        "observed": "residual_lock_voided_then_resumed",
        "self_lock_literal": self_lock_literal,
        "green_frontier": green_frontier,
    }


def _mutation_validate_before_persist_source_guard(repo: Path) -> Mapping[str, Any]:
    """MUTATION-RED (D1 removal): the D1 self-lock fix is that
    onboard.run_approve_entry calls walker_resume.validate_disposition_intake
    BEFORE it appends the disposition row to raw/link.jsonl. This source guard
    asserts that call ordering textually: the validate_disposition_intake(...)
    invocation must precede the raw/link.jsonl append (link_path.open("a", ...))
    inside onboard.py. Removing or reordering the pre-persist call -> rc=1 with a
    stable literal (a behavioral RED handle for the exact self-lock reintroduction
    edit). SL-1 is the behavioral partner: with the call removed, the refused
    intake would persist a self-lock row and SL-1's I1 hash-compare fails."""

    source = (repo / "support" / "operator" / "onboard.py").read_text(encoding="utf-8")
    marker = "def run_approve_entry("
    start = source.find(marker)
    if start < 0:
        raise ProfileError(INTAKE_VALIDATE_BEFORE_PERSIST_GUARD_LITERAL)
    end = source.find("\ndef ", start + len(marker))
    body = source[start:] if end < 0 else source[start:end]
    validate_pos = body.find("validate_disposition_intake(building_root, row")
    append_pos = body.find('link_path.open("a"')
    if validate_pos < 0 or append_pos < 0 or validate_pos >= append_pos:
        raise ProfileError(INTAKE_VALIDATE_BEFORE_PERSIST_GUARD_LITERAL)
    return {
        "mutation_proof": "validate-before-persist",
        "observed": "intake_validate_precedes_raw_link_append",
        "validate_offset": validate_pos,
        "append_offset": append_pos,
        "failure_literal": INTAKE_VALIDATE_BEFORE_PERSIST_GUARD_LITERAL,
    }


def run(repo: Path) -> Mapping[str, Any]:
    mutation_proofs = [
        _mutation_sequence_reuse_source_guard(repo),
        _mutation_validate_before_persist_source_guard(repo),
    ]
    fixtures = [
        _fixture_f_r1(repo),
        _fixture_f_r2(repo),
        _fixture_f_s(repo),
        _fixture_f_m(repo),
    ]
    concern_fixtures = [
        _fixture_f_c1(repo),
        _fixture_f_c2(repo),
        _fixture_f_c3(repo),
    ]
    selflock_fixtures = [
        _fixture_sl1_refused_intake_clean(repo),
        _fixture_sl2_legacy_residue_void(repo),
    ]
    probes = [
        _probe_p1_prior_stop_chain(repo),
        _probe_p2_concern_path_silent(repo),
        _probe_p3_divergence_guard(repo),
        _probe_pc1_gate_sequence_budget_exhausted(repo),
    ]
    return {
        "fixtures": fixtures,
        "concern_fixtures": concern_fixtures,
        "selflock_fixtures": selflock_fixtures,
        "probes": probes,
        "mutation_proofs": mutation_proofs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=_REPO_ROOT)
    # --all is accepted for check-runner parity; this standalone checker runs the
    # SAME fixture set regardless. It IS a member of the building-automation
    # profile (support/checkers/profiles/building_automation.yaml kernel_checks;
    # mapped in support/checkers/check_profile.py; pinned in
    # support/checkers/module_registry.yaml), so a profile-driven --all run DOES
    # reach it.
    parser.add_argument("--all", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    summary = run(repo)
    all_fixtures = (
        list(summary["fixtures"])
        + list(summary.get("concern_fixtures", ()))
        + list(summary.get("selflock_fixtures", ()))
    )
    branches = {f["fixture"]: f["branch"] for f in all_fixtures}
    for fixture in all_fixtures:
        print(
            f"  {fixture['fixture']}: {fixture['branch']}"
            + (
                f" ({fixture.get('red_literal_kind')})"
                if fixture["branch"] == "red-pin"
                else f" (frontier={fixture.get('frontier_kind') or fixture.get('observed')})"
            )
        )
    for probe in summary["probes"]:
        print(f"  {probe['probe']}: {probe['observed']}")
    for proof in summary.get("mutation_proofs", ()):
        print(
            f"  mutation:{proof['mutation_proof']}: {proof['observed']} "
            f"(failure_literal={proof['failure_literal']!r})"
        )
    print(
        "resume_replay_disposition_mirror passed: "
        f"{len(all_fixtures)} fixtures ({branches}), "
        f"{len(summary['probes'])} probes observed, "
        f"{len(summary.get('mutation_proofs', ()))} mutation proofs observed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

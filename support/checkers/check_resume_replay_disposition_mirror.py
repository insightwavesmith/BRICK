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
DIVERGENCE_PREFIX = "resume divergence: the seeded walk completed WITHOUT applying"
APPLIED_DISPOSITION_LITERAL = "dynamic Building already has an applied resume disposition"


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
        message = str(exc)
        if expect_red_literal_kind == "reroute-1746":
            ok = message.startswith(RED_REROUTE_HOLD_PREFIX) and message.endswith(
                RED_UNSUPPORTED_REROUTE_SUFFIX
            )
            literal = f"{RED_REROUTE_HOLD_PREFIX}...{RED_UNSUPPORTED_REROUTE_SUFFIX}"
        elif expect_red_literal_kind == "divergence":
            ok = message.startswith(DIVERGENCE_PREFIX)
            literal = DIVERGENCE_PREFIX
        else:  # pragma: no cover - guarded caller
            raise ProfileError(f"{fixture}: unknown expected literal kind {expect_red_literal_kind!r}")
        if not ok:
            raise ProfileError(
                f"{fixture}: final resume raised an UNEXPECTED literal; "
                f"expected {expect_red_literal_kind!r} ({literal!r}) but got {message!r}"
            )
        return {
            "fixture": fixture,
            "branch": "red-pin",
            "red_literal_kind": expect_red_literal_kind,
            "red_message": message,
        }

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


def run(repo: Path) -> Mapping[str, Any]:
    fixtures = [
        _fixture_f_r1(repo),
        _fixture_f_r2(repo),
        _fixture_f_s(repo),
        _fixture_f_m(repo),
    ]
    probes = [
        _probe_p1_prior_stop_chain(repo),
        _probe_p2_concern_path_silent(repo),
        _probe_p3_divergence_guard(repo),
    ]
    return {"fixtures": fixtures, "probes": probes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=_REPO_ROOT)
    # --all is accepted for check-runner parity; this standalone checker runs the
    # SAME fixture set regardless (it is not yet a profiles/*.yaml member, so a
    # profile-driven --all run does not reach it).
    parser.add_argument("--all", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    summary = run(repo)
    branches = {f["fixture"]: f["branch"] for f in summary["fixtures"]}
    for fixture in summary["fixtures"]:
        print(
            f"  {fixture['fixture']}: {fixture['branch']}"
            + (
                f" ({fixture.get('red_literal_kind')})"
                if fixture["branch"] == "red-pin"
                else f" (frontier={fixture.get('frontier_kind')})"
            )
        )
    for probe in summary["probes"]:
        print(f"  {probe['probe']}: {probe['observed']}")
    print(
        "resume_replay_disposition_mirror passed: "
        f"4 fixtures ({branches}), 3 probes observed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

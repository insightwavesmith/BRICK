#!/usr/bin/env python3
"""Single-source pin for the resume-admission validation sequence (D3).

Support evidence only. This checker asserts that the two resume-admission firing
points in ``support/operator/walker_resume.py`` -- the live resume path
``_resume_dynamic_graph_walker`` and the pre-persist intake gate
``validate_disposition_intake`` -- both delegate their overlapping validation
clause chain to the ONE shared pure sequence ``resume_admission_decision`` and do
NOT keep an inline copy of the sequence validators (Rule 11: the writer and
reader of the same contract share the same validation rules). It also drives the
shared function in-process over minimal synthetic mappings (no disk, no
provider) and asserts each pinned fail-closed refusal literal still raises.

It never calls a real provider, chooses Movement, authors a route, or judges
source truth, success, or quality.

Why a standalone checker (declared limit): the profile RULE_RUNNERS
(``support/checkers/lib/rule_runners.py``) are whole-file substring
presence/absence checks only -- they cannot express "exactly one delegating
Call inside each firing function body and ZERO inline references (bare call,
alias, attribute call, or getattr string) to the banned sequence validators",
nor can they drive the function in-process to prove each refusal still fires.
New kernel_checks cannot be registered without editing the
unwritable ``check_profile.py`` (KERNEL_DISPATCH lives there). So the AST
delegation pin and the behavioral refusal probes ride here; the profile layer
carries the complementary text_contains needles. This checker does NOT ride
``--all`` (it is not registered); direct-run evidence is required instead.
"""

from __future__ import annotations

import ast
import os.path as _osp
import sys
from collections.abc import Mapping, Sequence
from typing import Any, Callable

_REPO_ROOT = _osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_IMPORT_IDENTITY = _osp.join(_REPO_ROOT, "support", "import_identity")
if _IMPORT_IDENTITY not in sys.path:
    sys.path.insert(0, _IMPORT_IDENTITY)


_WALKER_RESUME_PATH = _osp.join(
    _REPO_ROOT, "support", "operator", "walker_resume.py"
)

_SHARED_FN = "resume_admission_decision"
_FIRING_FUNCTIONS = ("_resume_dynamic_graph_walker", "validate_disposition_intake")
# The sequence validators the firing bodies must NOT call inline anymore -- they
# are all folded inside resume_admission_decision. The ledger loaders
# (_recorded_agent_returns / _completed_step_frontier) are EXEMPT: they still
# appear inside the caller-supplied loader lambdas by design.
_BANNED_INLINE_CALLEES = (
    "validate_hold_disposition_action",
    "resume_budget_recovery_decision",
    "_required_disposition_action",
    "_disposition_pending_target_ref",
    "_require_budget_exhaustion_raise",
    "_adapter_error_hold_without_return",
)


class _CheckError(Exception):
    """A single-source pin violation (prints then exits rc=1)."""


# ---------------------------------------------------------------------------
# P1: AST delegation pin
# ---------------------------------------------------------------------------


def _named_calls_in(node: ast.AST) -> list[str]:
    names: list[str] = []
    for inner in ast.walk(node):
        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
            names.append(inner.func.id)
    return names


def _banned_identifier_references_in(node: ast.AST) -> set[str]:
    """Every banned validator name referenced in ANY form inside ``node``.

    The delegation-count check (``_named_calls_in``) only sees a banned name when
    it is a bare ``Name`` call. A firing body could smuggle the inline validator
    back in through an alias (``_v = validate_hold_disposition_action``), an
    attribute call (``walker.validate_hold_disposition_action(...)`` /
    ``self.validate_hold_disposition_action(...)``), or a ``getattr`` string
    (``getattr(mod, "validate_hold_disposition_action")``). This collects banned
    names appearing as ``Name`` ids, ``Attribute`` attrs, or string constants so
    every such alias form is a single-source violation, not a silent bypass.
    """

    banned = set(_BANNED_INLINE_CALLEES)
    referenced: set[str] = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Name) and inner.id in banned:
            referenced.add(inner.id)
        elif isinstance(inner, ast.Attribute) and inner.attr in banned:
            referenced.add(inner.attr)
        elif (
            isinstance(inner, ast.Constant)
            and isinstance(inner.value, str)
            and inner.value in banned
        ):
            referenced.add(inner.value)
    return referenced


def _delegation_violations() -> list[str]:
    with open(_WALKER_RESUME_PATH, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=_WALKER_RESUME_PATH)
    found: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in _FIRING_FUNCTIONS:
            found[node.name] = node
    violations: list[str] = []
    for name in _FIRING_FUNCTIONS:
        node = found.get(name)
        if node is None:
            violations.append(
                f"resume-admission single-source violated: firing function "
                f"{name} not found in walker_resume.py"
            )
            continue
        calls = _named_calls_in(node)
        delegations = calls.count(_SHARED_FN)
        if delegations != 1:
            violations.append(
                "resume-admission single-source violated: "
                f"{name} must call {_SHARED_FN} exactly once "
                f"(found {delegations})"
            )
        # Catch the banned sequence validators in EVERY reference form (bare
        # call, alias, attribute call, or getattr string) -- not just a bare
        # Name call -- so an alias-form inline copy cannot bypass the pin.
        for banned in sorted(_banned_identifier_references_in(node)):
            violations.append(
                "resume-admission single-source violated: "
                f"{name} must delegate to {_SHARED_FN} and must not reference "
                f"sequence validators directly (found: {banned})"
            )
    return violations


# ---------------------------------------------------------------------------
# P2: behavioral refusal probes (drive the shared function in-process)
# ---------------------------------------------------------------------------


def _one_node_plan() -> Mapping[str, Any]:
    from support.checkers.lib.fixture_graph_helpers import (
        fixture_graph_brick_step,
        fixture_graph_link_edge,
        fixture_proof_limits,
    )

    step = fixture_graph_brick_step(
        "s1",
        "brick-a",
        "edge:s1-close",
        agent_object_ref="agent-object:dev",
        work_statement="single-source checker synthetic step",
        required_return_shape="observed_evidence",
    )
    edge = fixture_graph_link_edge(
        "edge:s1-close",
        "s1",
        "building-boundary:done",
        close_reason="single-source checker synthetic close",
    )
    return {
        "plan_shape": "graph",
        "plan_ref": "building-plan:resume-admission-single-source",
        "building_id": "resume-admission-single-source",
        "owner_axis": "Brick",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": fixture_proof_limits(),
        "not_proven": ["semantic correctness of this synthetic probe fixture"],
        "execution_order": ["s1"],
        "brick_steps": [step],
        "link_edges": [edge],
    }


def _loader_must_not_fire() -> Any:
    raise AssertionError(
        "ledger loader was invoked before/at a paper-stop short-circuit"
    )


def _assert_refuses(
    walker: Any,
    case_id: str,
    expected_literal: str,
    *,
    evidence: Mapping[str, Any],
    disposition: Mapping[str, Any],
    declared_plan: Mapping[str, Any] | None,
    recorded_returns_loader: Callable[[], Sequence[Mapping[str, Any]]],
    completed_step_frontier_loader: Callable[[], Mapping[str, int]],
    returned_claims_present_loader: Callable[[], bool],
    enforce_raise_budget_increment: bool,
    adapter_error_stop_short_circuit: bool,
    literal_is_prefix: bool = False,
) -> None:
    try:
        walker.resume_admission_decision(
            evidence=evidence,
            disposition=disposition,
            declared_plan=declared_plan,
            recorded_returns_loader=recorded_returns_loader,
            completed_step_frontier_loader=completed_step_frontier_loader,
            returned_claims_present_loader=returned_claims_present_loader,
            enforce_raise_budget_increment=enforce_raise_budget_increment,
            adapter_error_stop_short_circuit=adapter_error_stop_short_circuit,
        )
    except ValueError as exc:
        text = str(exc)
        matched = text.startswith(expected_literal) if literal_is_prefix else (
            expected_literal in text
        )
        if not matched:
            raise _CheckError(
                f"resume-admission refusal probe failed: {case_id} raised a "
                f"DIFFERENT literal (expected: {expected_literal!r}; got: {text!r})"
            ) from exc
        return
    raise _CheckError(
        f"resume-admission refusal probe failed: {case_id} was ACCEPTED "
        f"(expected refusal: {expected_literal})"
    )


def _refusal_probe_count() -> int:
    import brick_protocol.support.operator.walker_resume as walker

    plan = _one_node_plan()
    ok_returns: Callable[[], Sequence[Mapping[str, Any]]] = lambda: [
        {"step_ref": "s1", "returned": {}}
    ]
    gate_pause_evidence = {
        "held": True,
        "hold": {
            "pending_target_ref": "brick-a",
            "hold_reason": "human_or_coo_gate_pause",
        },
    }
    fired = 0

    # not-held (no prior applied resume observation)
    _assert_refuses(
        walker,
        "not-held",
        walker._NOT_HELD_REFUSAL,
        evidence={"held": False},
        disposition={"disposition_action": "forward"},
        declared_plan=plan,
        recorded_returns_loader=_loader_must_not_fire,
        completed_step_frontier_loader=_loader_must_not_fire,
        returned_claims_present_loader=_loader_must_not_fire,
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # applied-resume (not held BUT prior resume observation exists)
    _assert_refuses(
        walker,
        "applied-resume",
        walker._APPLIED_RESUME_REFUSAL,
        evidence={"held": False, "resume_observations": [{"applied": "x"}]},
        disposition={"disposition_action": "forward"},
        declared_plan=plan,
        recorded_returns_loader=_loader_must_not_fire,
        completed_step_frontier_loader=_loader_must_not_fire,
        returned_claims_present_loader=_loader_must_not_fire,
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # birth-certificate absent (declared_plan None)
    _assert_refuses(
        walker,
        "birth-cert-none",
        walker._BIRTH_CERTIFICATE_ABSENT_REFUSAL,
        evidence=gate_pause_evidence,
        disposition={"disposition_action": "forward"},
        declared_plan=None,
        recorded_returns_loader=_loader_must_not_fire,
        completed_step_frontier_loader=_loader_must_not_fire,
        returned_claims_present_loader=_loader_must_not_fire,
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # non-menu action (raise on a gate-pause hold is not admitted)
    _assert_refuses(
        walker,
        "non-menu-action",
        "not admitted for hold_reason",
        evidence=gate_pause_evidence,
        disposition={"disposition_action": "raise", "budget_increment": 1},
        declared_plan=plan,
        recorded_returns_loader=_loader_must_not_fire,
        completed_step_frontier_loader=_loader_must_not_fire,
        returned_claims_present_loader=_loader_must_not_fire,
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # no recorded returns
    _assert_refuses(
        walker,
        "no-recorded-returns",
        walker._NO_RECORDED_RETURNS_REFUSAL,
        evidence=gate_pause_evidence,
        disposition={"disposition_action": "forward"},
        declared_plan=plan,
        recorded_returns_loader=lambda: [],
        completed_step_frontier_loader=lambda: {},
        returned_claims_present_loader=lambda: True,
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # completed-step frontier ahead of recorded returns
    _assert_refuses(
        walker,
        "frontier-ahead",
        "the step-output frontier is ahead of raw/agent-return.jsonl",
        evidence=gate_pause_evidence,
        disposition={"disposition_action": "forward"},
        declared_plan=plan,
        recorded_returns_loader=ok_returns,
        completed_step_frontier_loader=lambda: {"s1": 2},
        returned_claims_present_loader=lambda: True,
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # claim-trace returned_claims.json absent while replay obligations exist
    _assert_refuses(
        walker,
        "claims-file-absent",
        "required claim_trace agent/returned_claims.json",
        evidence=gate_pause_evidence,
        disposition={"disposition_action": "forward"},
        declared_plan=plan,
        recorded_returns_loader=ok_returns,
        completed_step_frontier_loader=lambda: {"s1": 1},
        returned_claims_present_loader=lambda: False,
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # recorded returns overrun the completed frontier
    _assert_refuses(
        walker,
        "recorded-overrun",
        "the recorded-return ledger and the step-output ledger disagree",
        evidence=gate_pause_evidence,
        disposition={"disposition_action": "forward"},
        declared_plan=plan,
        recorded_returns_loader=lambda: [
            {"step_ref": "s1", "returned": {}},
            {"step_ref": "s1", "returned": {}},
        ],
        completed_step_frontier_loader=lambda: {"s1": 1},
        returned_claims_present_loader=lambda: True,
        enforce_raise_budget_increment=False,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # raise-target not an existing Brick node (budget-exhaustion hold)
    budget_hold_evidence = {
        "held": True,
        "hold": {
            "pending_target_ref": "brick-nope",
            "budget_exhausted": True,
            "hold_reason": "target_node_budget_exhausted",
            "node_budget": 1,
        },
        "node_reroute_budgets": {"brick-nope": 1},
        "node_reroute_landings": {"brick-nope": 1},
    }
    _assert_refuses(
        walker,
        "raise-target-not-node",
        walker._RAISE_TARGET_NOT_NODE_REFUSAL,
        evidence=budget_hold_evidence,
        disposition={
            "disposition_action": "raise",
            "budget_increment": 1,
            "pending_target_ref": "brick-nope",
        },
        declared_plan=plan,
        recorded_returns_loader=ok_returns,
        completed_step_frontier_loader=lambda: {"s1": 1},
        returned_claims_present_loader=lambda: True,
        enforce_raise_budget_increment=True,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    return fired


def _raise_budget_increment_coercion_probe() -> None:
    """Resume-side raise budget_delta seed keeps the positive-int coercion.

    ``_required_disposition_action`` already refuses malformed
    ``budget_increment`` values for both firing points. The resume-only
    ``enforce_raise_budget_increment`` clause also matters on the accepted path:
    it converts a decimal-text increment into the integer value carried on
    ``ResumeAdmissionDecision.raise_budget_increment``. A mutation that replaces
    that clause with ``disposition.get("budget_increment")`` preserves the
    refusal set for malformed values but leaks a string into the resume seed.
    This acceptance probe catches that edge directly.
    """

    import brick_protocol.support.operator.walker_resume as walker

    decision = walker.resume_admission_decision(
        evidence={
            "held": True,
            "hold": {
                "pending_target_ref": "brick-a",
                "budget_exhausted": True,
                "hold_reason": "target_node_budget_exhausted",
                "node_budget": 1,
            },
            "node_reroute_budgets": {"brick-a": 1},
            "node_reroute_landings": {"brick-a": 1},
        },
        disposition={
            "disposition_action": "raise",
            "budget_increment": "2",
            "pending_target_ref": "brick-a",
        },
        declared_plan=_one_node_plan(),
        recorded_returns_loader=lambda: [{"step_ref": "s1", "returned": {}}],
        completed_step_frontier_loader=lambda: {"s1": 1},
        returned_claims_present_loader=lambda: True,
        enforce_raise_budget_increment=True,
        adapter_error_stop_short_circuit=False,
    )
    if decision.raise_budget_increment != 2 or not isinstance(
        decision.raise_budget_increment, int
    ):
        raise _CheckError(
            "resume-admission positive-path probe failed: raise budget_increment "
            "must be coerced to int 2 when enforce_raise_budget_increment=True "
            f"(got {decision.raise_budget_increment!r})"
        )


def _short_circuit_probe() -> None:
    """The resume-only paper-stop early-accept must return BEFORE any ledger read
    (loaders that raise if invoked prove the ordering)."""

    import brick_protocol.support.operator.walker_resume as walker

    decision = walker.resume_admission_decision(
        evidence={
            "held": True,
            "hold": {
                "hold_reason": "adapter_error_frontier",
                "pending_target_ref": "brick-a",
            },
        },
        disposition={"disposition_action": "stop"},
        declared_plan=_one_node_plan(),
        recorded_returns_loader=_loader_must_not_fire,
        completed_step_frontier_loader=_loader_must_not_fire,
        returned_claims_present_loader=_loader_must_not_fire,
        enforce_raise_budget_increment=True,
        adapter_error_stop_short_circuit=True,
    )
    if not decision.adapter_error_stop:
        raise _CheckError(
            "resume-admission refusal probe failed: adapter-error stop short-circuit "
            "did not set adapter_error_stop=True"
        )


def main() -> int:
    try:
        violations = _delegation_violations()
        if violations:
            for line in violations:
                print(line)
            return 1
        fired = _refusal_probe_count()
        _raise_budget_increment_coercion_probe()
        _short_circuit_probe()
    except _CheckError as exc:
        print(str(exc))
        return 1
    print(
        "resume-admission single-source: OK "
        f"(2 firing points delegate, no inline/alias sequence-validator reference; "
        f"{fired} refusal probes fired; "
        "raise budget increment coerces to int; "
        "paper-stop short-circuit precedes ledger reads)"
    )
    print(
        "proof limit: support evidence only; this checker does not prove source "
        "truth, success judgment, quality judgment, or Movement authority."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

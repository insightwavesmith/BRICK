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
# P1b: residual pre-delegation guard pin (D3)
# ---------------------------------------------------------------------------

# The live resume firing point (``_resume_dynamic_graph_walker``) MUST keep a
# residual not-held / applied-resume guard that runs BEFORE
# ``_read_disposition_row`` -- that reader needs the ``hold_record`` mapping,
# which is only present on a HELD record, so the not-held / already-applied cases
# must be refused first. ``resume_admission_decision`` re-checks the SAME two
# conditions inside the delegated sequence, but the live path cannot delegate
# them first because it must read the disposition row before delegating. So this
# guard is a MEASURED DECLARED RESIDUAL, not a duplicate to fold away (0707: the
# not-held branch reaches ``_read_disposition_row(root, hold_record)`` before the
# delegation call, so the guard cannot move without breaking the live path).
#
# Being a declared residual, it must raise the SHARED module-constant literals
# (``_NOT_HELD_REFUSAL`` / ``_APPLIED_RESUME_REFUSAL``) so its accept/refuse
# literal can never drift away from the delegated sequence (invariant I2). The
# delegation pin above does NOT cover this: it only forbids the banned SEQUENCE
# validators and counts the delegating call; it says nothing about these two
# refusal constants. Without this pin the residual guard could drift to an inline
# string, or vanish entirely, while the checker stayed green (0707 measured gap:
# both a literal drift and a full removal of the residual guard stayed rc=0).
#
# 0707 QA follow-up (M3/M4/M5/M6 closure): a NAME-PRESENCE-ONLY pin (does the
# constant appear inside ANY raise anywhere in the function body?) is NOT
# enough. Code-attack-QA measured four bypass forms that all kept the constant
# names somewhere in the body and stayed rc=0:
#   M3 (position): move the guard AFTER the ``_read_disposition_row`` call, so a
#       not-held / already-applied record reaches the disposition reader first.
#   M4 (dead code): keep the ``raise`` statements but under a branch that can
#       never execute (e.g. ``if False:`` / an unreachable else), so the names
#       survive but never fire.
#   M5 (condition inversion): invert the guard predicate (``if evidence.get(
#       "held")`` instead of ``if not evidence.get("held")``), so the refusals
#       fire on the HELD case and a not-held record slips through.
#   M6 (compound): any combination of the above.
# So the pin below is STRUCTURAL, not name-presence: it locates the guard as an
# ``if`` statement whose test is the not-held predicate (``not <held-read>``),
# asserts BOTH refusal constants are raised on that not-held branch (reachably,
# at guard nesting depth -- not merely somewhere in the function), and asserts
# the guard STATEMENT precedes the first ``_read_disposition_row`` call in the
# function body. Each of M3/M4/M5/M6 flips at least one of these facts, so each
# now reddens. Name-presence remains a fallback error only when no structural
# guard is found at all.
_RESIDUAL_GUARD_FUNCTION = "_resume_dynamic_graph_walker"
_RESIDUAL_GUARD_CONSTANTS = ("_NOT_HELD_REFUSAL", "_APPLIED_RESUME_REFUSAL")
_DISPOSITION_READER = "_read_disposition_row"
# The evidence read the not-held predicate must consult. The live guard is
# ``if not evidence.get("held"):`` -- the guard predicate MUST be a boolean-NOT
# over a read of the ``held`` flag, otherwise M5 (condition inversion) or a
# predicate swap could let a not-held record through while the names survive.
_HELD_FLAG_KEY = "held"


def _raised_name_ids_in(node: ast.AST) -> set[str]:
    """Every ``ast.Name`` id appearing inside a ``raise ...`` statement in node.

    A residual guard that raises ``ValueError(_NOT_HELD_REFUSAL)`` exposes the
    constant as a ``Name`` inside the ``Raise`` expression; a drift to
    ``ValueError("inline string")`` or an outright removal of the guard makes the
    constant name disappear from the raised set, which is the D3 violation.
    """

    names: set[str] = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Raise) and inner.exc is not None:
            for sub in ast.walk(inner.exc):
                if isinstance(sub, ast.Name):
                    names.add(sub.id)
    return names


def _static_bool(test: ast.expr) -> bool | None:
    """Static truthiness of ``test`` when it is a literal constant, else None.

    ``if False:`` / ``if 0:`` / ``if None:`` are statically-dead branches; ``if
    True:`` / ``if 1:`` are statically-live. Anything non-constant returns None
    (unknown -- treated as reachable). This lets the reachable-raise collector
    prune a dead-code branch (M4: raises kept under ``if False:`` so their names
    survive an ``ast.walk`` but can never fire).
    """

    if isinstance(test, ast.Constant):
        return bool(test.value)
    return None


def _reachable_raised_name_ids_in(node: ast.AST) -> set[str]:
    """Raised ``ast.Name`` ids reachable in ``node``, pruning statically-dead
    ``if`` branches.

    Unlike :func:`_raised_name_ids_in` (a flat ``ast.walk``), this walks the
    statement tree and, at every ``ast.If``, drops the dead side when the test is
    a literal constant: a constant-false test prunes the ``body`` (M4 dead code),
    a constant-true test prunes the ``orelse``. A raise buried under ``if
    False:`` therefore no longer counts as a guard refusal, so M4 reddens.
    """

    names: set[str] = set()

    def _visit(n: ast.AST) -> None:
        if isinstance(n, ast.Raise):
            if n.exc is not None:
                for sub in ast.walk(n.exc):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
            return
        if isinstance(n, ast.If):
            truth = _static_bool(n.test)
            branches: list[list[ast.stmt]] = []
            if truth is None:
                branches = [n.body, n.orelse]
            elif truth:
                branches = [n.body]
            else:
                branches = [n.orelse]
            for branch in branches:
                for stmt in branch:
                    _visit(stmt)
            return
        for child in ast.iter_child_nodes(n):
            _visit(child)

    _visit(node)
    return names


def _reads_held_flag(node: ast.AST) -> bool:
    """True when ``node`` reads the ``held`` flag off the evidence mapping.

    Matches both ``evidence.get("held")`` (a ``Call`` to a ``.get`` attribute
    with the ``held`` string as first arg) and ``evidence["held"]`` (a
    ``Subscript`` with the ``held`` constant). This is how the not-held guard
    predicate consults the HELD flag; requiring it inside the guard test blocks a
    predicate swap (M5-adjacent) that keeps the raises but tests something else.
    """

    for inner in ast.walk(node):
        if (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "get"
            and inner.args
            and isinstance(inner.args[0], ast.Constant)
            and inner.args[0].value == _HELD_FLAG_KEY
        ):
            return True
        if isinstance(inner, ast.Subscript):
            key = inner.slice
            if isinstance(key, ast.Constant) and key.value == _HELD_FLAG_KEY:
                return True
    return False


def _is_not_held_test(test: ast.expr) -> bool:
    """True when ``test`` is a boolean-NOT over a read of the ``held`` flag.

    The live guard is ``if not evidence.get("held"):``. Requiring the ``not``
    (``ast.UnaryOp`` with ``ast.Not``) directly over a HELD-flag read means M5
    (inverting to ``if evidence.get("held"):`` -- dropping the ``not``) no longer
    matches this guard shape, so no structural guard is found on the not-held
    branch and the pin reddens.
    """

    if not (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)):
        return False
    return _reads_held_flag(test.operand)


def _first_disposition_reader_index(body: list[ast.stmt]) -> int | None:
    """Index of the first top-level statement in ``body`` that calls
    ``_read_disposition_row``; ``None`` when it is never called at top level."""

    for index, stmt in enumerate(body):
        for inner in ast.walk(stmt):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == _DISPOSITION_READER
            ):
                return index
    return None


def _residual_guard_violations() -> list[str]:
    with open(_WALKER_RESUME_PATH, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=_WALKER_RESUME_PATH)
    target: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == _RESIDUAL_GUARD_FUNCTION
        ):
            target = node
            break
    violations: list[str] = []
    if target is None:
        violations.append(
            "resume-admission residual-guard violated: firing function "
            f"{_RESIDUAL_GUARD_FUNCTION} not found in walker_resume.py"
        )
        return violations

    # Locate the STRUCTURAL guard: the FIRST top-level ``if not <held-read>:``
    # statement in the function body. Searching only top-level statements (not
    # ast.walk) pins the guard at guard nesting depth -- a raise buried inside an
    # unrelated nested branch does not qualify, and neither does a dead-code
    # (``if False:``) block, because its test is not the not-held predicate.
    guard_index: int | None = None
    guard_stmt: ast.If | None = None
    for index, stmt in enumerate(target.body):
        if isinstance(stmt, ast.If) and _is_not_held_test(stmt.test):
            guard_index = index
            guard_stmt = stmt
            break

    if guard_stmt is None:
        # No structural not-held guard. Report the name-presence gap too so the
        # message names exactly which constant(s) are missing when someone has
        # simply deleted the guard (M4 full removal) or inverted the predicate
        # (M5) so the ``not <held-read>`` shape disappeared.
        raised = _raised_name_ids_in(target)
        missing = [c for c in _RESIDUAL_GUARD_CONSTANTS if c not in raised]
        detail = (
            f" (constants absent from all raises: {', '.join(missing)})"
            if missing
            else " (constants present but not on an `if not evidence.get(\"held\")` "
            "guard branch -- position/condition/reachability drift)"
        )
        violations.append(
            "resume-admission residual-guard violated: "
            f"{_RESIDUAL_GUARD_FUNCTION} must keep an "
            "`if not evidence.get(\"held\"): ... raise` pre-delegation guard that "
            "refuses the not-held / applied-resume cases before "
            f"{_DISPOSITION_READER}" + detail
        )
        return violations

    # The guard exists and tests the not-held predicate. Both refusal constants
    # must be raised REACHABLY on this guard branch (its body / nested orelse),
    # not merely somewhere in the function -- this blocks M4 (dead-code raises
    # elsewhere) because those raises are outside the guard statement.
    #
    # ``_reachable_raised_name_ids_in`` prunes statically-dead ``if False:``
    # branches, so a raise kept under a constant-false test INSIDE the guard body
    # (M4 dead-code inside the guard) no longer counts and reddens too.
    guard_raised = _reachable_raised_name_ids_in(guard_stmt)
    for constant in _RESIDUAL_GUARD_CONSTANTS:
        if constant not in guard_raised:
            violations.append(
                "resume-admission residual-guard violated: "
                f"{_RESIDUAL_GUARD_FUNCTION} must raise the shared module constant "
                f"{constant} INSIDE its `if not evidence.get(\"held\")` guard branch "
                "(the not-held / applied-resume refusal) -- a raise moved outside "
                "the guard, dropped, or drifted to an inline literal is not admitted"
            )

    # Position: the guard STATEMENT must precede the first _read_disposition_row
    # call in the function body. This blocks M3 (guard moved after the reader):
    # the disposition reader needs the hold_record mapping that only a HELD record
    # carries, so a not-held record must be refused BEFORE it is read.
    reader_index = _first_disposition_reader_index(target.body)
    if reader_index is None:
        violations.append(
            "resume-admission residual-guard violated: "
            f"{_RESIDUAL_GUARD_FUNCTION} no longer calls {_DISPOSITION_READER} at "
            "top level -- the pre-delegation guard ordering can no longer be pinned"
        )
    elif guard_index >= reader_index:
        violations.append(
            "resume-admission residual-guard violated: "
            f"the not-held guard in {_RESIDUAL_GUARD_FUNCTION} must precede the "
            f"first {_DISPOSITION_READER} call (guard at statement {guard_index}, "
            f"reader at statement {reader_index}) -- refusing not-held/applied-resume "
            "records only AFTER reading the disposition row is not admitted"
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

    # D2 refusal pin: action=raise with a missing budget_increment must refuse
    # before any ledger read when the resume firing point enforces the
    # budget-increment clause. This is the malformed/absent half of D2; the
    # positive-path coercion probe below pins the accepted string->int half.
    _assert_refuses(
        walker,
        "raise-budget-increment-absent",
        "transition_lifecycle.budget_increment must be a positive integer",
        evidence=gate_pause_evidence,
        disposition={"disposition_action": "raise"},
        declared_plan=plan,
        recorded_returns_loader=_loader_must_not_fire,
        completed_step_frontier_loader=_loader_must_not_fire,
        returned_claims_present_loader=_loader_must_not_fire,
        enforce_raise_budget_increment=True,
        adapter_error_stop_short_circuit=False,
    )
    fired += 1

    # D2 refusal pin: malformed budget_increment values must also refuse at the
    # same pre-ledger sequence point. A mutation that loosens or removes
    # ``_required_disposition_action`` / ``require_positive_int`` now reddens
    # directly instead of being covered only by the accepted-path coercion probe.
    _assert_refuses(
        walker,
        "raise-budget-increment-malformed",
        "transition_lifecycle.budget_increment must be a positive integer",
        evidence=gate_pause_evidence,
        disposition={"disposition_action": "raise", "budget_increment": "nope"},
        declared_plan=plan,
        recorded_returns_loader=_loader_must_not_fire,
        completed_step_frontier_loader=_loader_must_not_fire,
        returned_claims_present_loader=_loader_must_not_fire,
        enforce_raise_budget_increment=True,
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
        violations += _residual_guard_violations()
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
        "residual not-held/applied-resume guard raises shared constants; "
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

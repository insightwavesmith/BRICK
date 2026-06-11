"""Bounded, agent-proposed, gate-adopted dynamic graph walker (THIN FACADE).

BOUNDED-AGENT-PROPOSED-ROUTING-LOOP-0 admits this module. It walks a declared
Building graph FORWARD over the existing ``execution_order`` linearization and,
after a node completes, inspects the Agent return for a NON-BINDING
``transition_concern_evidence`` (binding:false) proposing a reroute to an
EXISTING Brick node in the same Building. If the completing node's declared Link
gate ADOPTS the proposal (template: / link-gate:default-transition => auto-adopt;
human: / coo: => PAUSE) and the TARGET node's Link-assigned budget is available,
the walker re-executes the target node (and its declared replay scope) at RUNTIME
by appending to the live attempt sequence -- it does NOT require pre-declared
attempt-2 steps.

ζ7 boundary preserved at every decision point:
- the Agent PROPOSES (non-binding transition_concern, binding:false);
- the DECLARED Link gate (template: / human: / coo:) ADOPTS or PAUSEs;
- support WALKS the adopted route and RECORDS; it authors NO route or Movement.

The reroute budget belongs to the TARGET Brick node (Link-assigned, keyed by the
target node ref) and is SHARED across all reroute-landings on that node -- outer
and nested, at any depth. A nested reroute landing on a node draws that node's
existing shared budget; it never receives a fresh budget. Budget is consumed per
REROUTE-LANDING, not per forward-replay-execution. A Building has a finite set of
Brick nodes and a reroute may only target an existing node, so total
reroute-landings are bounded by the sum of per-node budgets => no infinite loop.

On budget exhaustion the next reroute landing is NOT adopted; the Building HOLDs
(transition_lifecycle.state=paused, required_disposition_owner=caller-or-coo,
carrying the cascade lineage and pending target) so observe_building_frontier
reports a human/Link gate (disposition_required). Support HALTS and RECORDS; it
does NOT decide raise/forward/stop -- that is the human/COO, a later phase.

This module is support mechanics. It does not choose Movement, invent a route,
judge success or quality, schedule, retry, or call providers. It reuses the
existing step executor and graph linearization; it adds only the runtime
append-to-the-live-attempt-sequence + per-node budget + HOLD behavior:
support authors no route or Movement (this facade and every walker_* collaborator
preserve that ζ7 boundary).

ELEGANT-REFACTOR P3c (engine blueprint 0531 §5 / detail-design §D-3 Opt B): this
module was a ~2638 LOC god-module that mixed the forward walk + reroute adoption
+ per-node budget/carry + HOLD + fan-in/out + resume + adapter-error frontier in
one file. Its separable concerns were lifted into single-concern collaborator
modules under ``support/operator/`` (one concern per module) and this module is
now the THIN FACADE: it re-exports every previously-public name so external
importers (run.py's walk/resume entry, the bounded-routing-loop checker's
``_node_reroute_budgets`` import) keep working identically. It chooses no
Movement and judges no success or quality.

Collaborator sublayer (each a registered module_registry.yaml row, G4):
  operator/walker_common.py             shared proof-limit / not-proven vocab
  operator/walker_step_fixture.py       per-step Brick/Link row + gate disposition
  operator/walker_reroute_budget.py     per-node reroute budget + Carry-budget refs
  operator/walker_fan_in.py             fan-out splice + fan-in wait-all hold
  operator/walker_transition_concern.py Agent non-binding concern adoption
  operator/walker_hold.py               HOLD construction + paused-link injection
  operator/walker_frontier.py           adapter-error frontier write-plan + writer
  operator/walker_kernel.py             the forward step-walk kernel
  operator/walker_resume.py             the resume-after-HOLD verb
"""

from __future__ import annotations

# Shared proof-limit / not-proven vocabularies (public; re-exported).
from brick_protocol.support.operator.walker_common import (
    FAN_TOPOLOGY_NOT_PROVEN,
    FAN_TOPOLOGY_PROOF_LIMITS,
    NOT_PROVEN,
    PROOF_LIMITS,
    RESUME_NOT_PROVEN,
)

# The public walk/resume entry that run.py imports (thin delegators: the bodies
# live in the kernel / resume collaborators).
from brick_protocol.support.operator.walker_kernel import _run_dynamic_graph_walker
from brick_protocol.support.operator.walker_resume import (
    _disposition_author_ref,
    _flattened_or_nested_transition_lifecycle,
    _read_disposition_row,
    _read_written_dynamic_plan,
    _recorded_agent_returns,
    _resume_dynamic_graph_walker,
    _resume_observations,
    _step_output_recorded_at,
)

# Adapter-error frontier write-plan + writer.
from brick_protocol.support.operator.walker_frontier import (
    _dynamic_frontier_write_plan,
    _write_dynamic_adapter_error_frontier,
)

# Per-target-node reroute budget + Carry-budget evidence refs. The standalone
# bounded-routing-loop checker imports ``_node_reroute_budgets`` from this facade.
from brick_protocol.support.operator.walker_reroute_budget import (
    _BRICK_REF_PREFIXES,
    CARRY_BUDGET_TRACE_PATH,
    _carry_budget_evidence_ref,
    _carry_budget_fact_ref,
    _jsonl_records,
    _mapping_value,
    _node_reroute_budgets,
    _positive_int,
    _required_disposition_action,
    _resume_budget_map,
    _resume_landing_map,
)

# Fan-out scheduling + fan-in wait-all observation/HOLD.
from brick_protocol.support.operator.walker_fan_in import (
    _build_fan_in_wait_all_hold,
    _build_fan_in_wait_all_observation,
    _fan_in_wait_all_observations_for_held_source,
    _fan_in_wait_all_state,
    _graph_has_fan_groups,
    _graph_root_step_refs,
    _graph_successor_step_refs_by_source_step_ref,
    _latest_completed_source_result,
    _splice_declared_successors,
)

# HOLD construction + paused transition_lifecycle injection.
from brick_protocol.support.operator.walker_hold import (
    _build_hold,
    _caller_supplied_link_facts_for_replay,
    _hold_paused_at_ref,
    _inject_fan_in_paused_link,
    _inject_hold_paused_link,
    _replace_held_source_with_lifecycle,
    _resumed_lifecycle_from_hold,
    _step_result_with_paused_lifecycle,
)

# Agent non-binding transition-concern adoption.
from brick_protocol.support.operator.walker_transition_concern import (
    _TransitionConcernObservation,
    _build_invalid_transition_concern_hold,
    _proposed_target_brick,
    _transition_concern_from_step_result,
    _transition_concern_observation_from_step_result,
)

# Per-step Brick/Link row readers + declared gate disposition.
from brick_protocol.support.operator.walker_step_fixture import (
    _HUMAN_GATE_REFS,
    _TEMPLATE_AUTHOR_PREFIXES,
    _TEMPLATE_GATE_REFS,
    _adopted_by_ref,
    _brick_instance_ref_from_linear_step,
    _brick_required_fields,
    _brick_row_from_linear_step,
    _coerce_name_list,
    _declared_replay_scope_step_refs,
    _gate_disposition_for_step,
    _gate_required_fields,
    _link_row_from_linear_step,
    _observed_returned_fields,
    _split_field_names,
    _structured_field_observation_for_step,
)

# CLOSE-1/F2: the pre-decomposition dynamic_walker.py had NO __all__ (so default
# `import *` exposed its non-underscore top-level names — codex review 4 P3
# correction: it was NOT "0 public names"; the earlier wording here was wrong).
# This facade keeps the same star-import surface via an explicit __all__. The
# walk/resume entry points and the reroute-budget helper are intentionally
# underscore-private; run.py and check_bounded_agent_proposed_routing_loop0.py
# import them DIRECTLY by name (e.g. `from ...dynamic_walker import
# _node_reroute_budgets`), which is unaffected by __all__. Listing _private
# names in __all__ wrongly re-publishes them via star-import, so __all__ now
# carries ONLY the public shared-vocab constants. The direct-import surface is
# unchanged (verified: no `import *` consumer exists).
#
# codex-review-3 P2-B: the facade re-imports CARRY_BUDGET_TRACE_PATH (a public,
# non-underscore name) from walker_reroute_budget, so `hasattr(dynamic_walker,
# "CARRY_BUDGET_TRACE_PATH")` is True. To keep the star-import surface consistent
# with the direct-attribute surface (no name that resolves directly but vanishes
# under `import *`), it is listed in __all__ here.
__all__ = [
    "PROOF_LIMITS",
    "NOT_PROVEN",
    "RESUME_NOT_PROVEN",
    "FAN_TOPOLOGY_PROOF_LIMITS",
    "FAN_TOPOLOGY_NOT_PROVEN",
    "CARRY_BUDGET_TRACE_PATH",
]

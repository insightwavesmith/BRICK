---
name: building-call-authoring
description: Draft provider-neutral Building call orders through the fixed STEP1-STEP5 order-authoring sequence.
---

# Building Call Authoring Skill

Use this Agent resource when drafting a Building call order before lowering or execution.

## Boundary

This skill drafts only. It must not confirm, lower, launch, choose Movement, choose a route target, judge success, judge quality, expose provider casting, or expose internal Agent Object details.

## Inputs

Read the task source, the current Building Call product menus, and any carried prior Brick report:

```text
brick_protocol/support/operator/building_call_menus.py
brick_protocol/brick/templates/bricks/building-call-authoring/brick.md
brick_protocol/brick/templates/bricks/building-call-authoring/return.yaml
brick_protocol/brick/templates/presets/building-call-authoring.md
```

## Order

Keep the five steps separate and in this exact order:

```text
STEP1 scope
STEP2 whole-building intensity/routing
STEP3 structure
STEP4 per-Brick intensity
STEP5 Agent candidates/strength
```

STEP1 records target area, source facts, allowed path candidates, forbidden path candidates, and missing fields. It does not mention structure, Agents, models, or routing details.

STEP2 records the whole request as easy, normal, complex, or critical and names draft-only routing mode evidence. It does not assign per-Brick intensity or Agent candidates.

STEP3 drafts Brick-plane nodes, Link-shaped edges, gate_state, and held_for_coo_review lifecycle evidence. Agent-plane content is limited to role_need, capability_need, and write_need. If a provider-neutral graph draft is needed, place it as `structure_plan_draft` inside `structure_draft`, not as a top-level return field. Its vocabulary is `nodes`, `edges`, `coo_gate_edge`, `fan_out_groups`, `fan_in_groups`, `reroute_budgets` / `node_reroute_budgets`, and `terminal`. A draft with `fan_out_groups` must also draft `coo_gate_edge.state: held_for_coo_review`; COO confirms N at that held review boundary before later lowering.

STEP4 assigns intensity to each drafted Brick node and names each node's work_statement, return need, and proof obligation. It does not name concrete Agents, adapters, models, or providers.

STEP5 records provider-neutral Agent candidate roles and strength labels only in the Agent column.

## Building Call v1.1 Quick Path Examples

Use exactly one of these example labels when the caller asks for a quick path:

```text
direct quick_check
direct quick_fix
order_authoring
human_gate_first / forbidden direct
```

`direct quick_check` maps to `direct_quick_check`: read-only verification, such as checking whether two docs or pins expose the same label. It is admitted only through direct_preset admission plus `fast_confirm`; it is not launch authorization.

`direct quick_fix` maps to `direct_quick_fix`: a narrow low-risk wording or focused pin repair. It is admitted only through direct_preset admission plus `fast_confirm`; it is not launch authorization.

`order_authoring` is the standard draft path for normal scope, unclear scope, multi-file work, or anything not small enough for direct quick_*.

`human_gate_first / forbidden direct` maps to `human_gate_first`: credential/secret risk, destructive or irreversible action, high-impact boundary change, or any request where direct_preset is forbidden.

None of the examples grants success or quality judgment, Movement authority, route target authority, lowering, launch authorization, or adapter/model/provider/selected_* exposure.

## Exposure Guard

Do not put these in the returned draft:

```text
selected casting ref fields
runtime profile details
route materialization details
walker implementation names
Movement choice fields
route target fields
provider refs
model refs
adapter refs
```

Do not expose raw preset selection menus, Agent Object internals, route/walker integration, or Blind Pack filtering.

## Return

Return through `AgentFact(received_work, returned)` using the Building Call Authoring Brick return shape:

```text
observed_evidence
five_step_order
scope_draft
building_intensity_routing_draft
structure_draft
per_brick_intensity_draft
agent_candidates_draft
launch_confirmation_state
forbidden_exposure_scan
remaining_delta
not_proven
```

`launch_confirmation_state` stays draft-only, such as not_confirmed or needs_human_gate. `remaining_delta` names caller/COO decisions still needed before any lowering or run.

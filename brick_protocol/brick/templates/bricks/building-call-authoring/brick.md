---
brick_kind: building-call-authoring
brick_word: building-call-authoring
performer_word: order-author
requires_brick_write_scope: no
capability_class: read
performer_lane_need: leader
agent_object_hint_ref: agent-object:order-author
required_return_template_refs:
  - brick_protocol/brick/templates/bricks/building-call-authoring/return.yaml
  - brick_protocol/brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Building Call Authoring Brick drafts a provider-neutral Building order in the fixed five-step sequence.
---
## Building Call Authoring

Draft a Building call order **only**. Do not confirm, lower, launch, execute, judge success, judge quality, choose Movement, choose a route target, expose provider casting, or place adapter/model/provider fields in Brick sections.

Input: the prior Brick's report or task source (carried via the Link edge) plus this node's declared `work_statement`. Use the Building Call product menus as support vocabulary, but do not expose raw preset selection menus, Agent Object internals, route or walker integration, runtime profile details, Blind Pack filtering, or selected casting fields.

Preserve this exact order and do not mix steps:

1. STEP1 scope: produce `scope_draft` with target area, source facts, allowed path candidates, forbidden path candidates, and missing fields. Do not discuss structure, Agents, models, or routing details here.
2. STEP2 whole-building intensity/routing: produce `building_intensity_routing_draft` with easy, normal, complex, or critical plus draft-only routing mode evidence. Easy may mention direct quick_check or quick_fix only as draft evidence after admission and fast confirm are needed; critical records human_gate_first need.
3. STEP3 structure: produce `structure_draft` with Brick-plane nodes, Link-shaped edges, gate_state, and held_for_coo_review lifecycle evidence. Agent-plane content is limited to role_need, capability_need, and write_need.
4. STEP4 per-Brick intensity: produce `per_brick_intensity_draft` by assigning easy, normal, complex, or critical to each drafted Brick node and naming each node's work_statement, return need, and proof obligation. Do not name concrete Agents, adapters, models, or providers here.
5. STEP5 Agent candidates/strength: produce `agent_candidates_draft` with provider-neutral Agent candidate roles and strength labels only in the Agent column.

Return: fill the `required_return_shape` from the return_template (`brick_protocol/brick/templates/bricks/building-call-authoring/return.yaml`): `observed_evidence`, `five_step_order`, `scope_draft`, `building_intensity_routing_draft`, `structure_draft`, `per_brick_intensity_draft`, `agent_candidates_draft`, `launch_confirmation_state`, `forbidden_exposure_scan`, `remaining_delta`, `not_proven`.

Keep `launch_confirmation_state` draft-only, such as not_confirmed or needs_human_gate. `forbidden_exposure_scan` records whether the returned draft avoided selected casting refs, runtime profile details, route materialization details, walker details, raw preset menus, Agent Object internals, and success/quality/Movement decision fields. `remaining_delta` records what the caller or COO must still decide before any later lowering or Building run.

Do NOT return success, failure, approval, quality, good_enough, Movement choice, route target, or selected casting ref fields - sufficiency and Movement are the Link gate's; quality and success are the human's.

> This `## Building Call Authoring` body IS delivered to the Agent in the prompt as the static kind instruction
> (brick_protocol/support/connection/adapter_grant_policy._build_prompt, key `brick_instruction_body`), carried from
> this file by the Builder (plan_rendering carries the ## body onto the step_template row; composition
> stamps it onto the brick_row). It is a SEPARATE prompt section from the dynamic `work_statement`.
> Each `required_return_shape` field is guarded to appear here with guidance, both directions, across
> EVERY return template (check_bricks_spec_completeness._prose_return_shape_drift_violations), so this
> body and the return.yaml cannot drift. The frontmatter carries Brick contract fields plus Builder
> selection metadata (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared BAL
> rows. Keep this instruction GENERAL to the kind (building-specifics ride `work_statement`); do not
> claim it raises quality - the Link gate checks sufficiency, quality is the human's.

---
brick_kind: design
brick_word: design
performer_word: design
requires_brick_write_scope: no
capability_class: read
performer_lane_need: leader
agent_object_hint_ref: agent-object:design-lead
required_return_template_refs:
  - brick_protocol/brick/templates/bricks/design/return.yaml
  - brick_protocol/brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Design Brick turns the plan into architecture, UX, data, or protocol design boundaries.
---
## Design

Turn the prior plan into **architecture, UX, data, or protocol design boundaries** — design only,
**without writing implementation**.

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`work_statement`. Study the relevant current structure, then propose design boundaries: how the
change is shaped, which axis owns each responsibility, the invariants it must hold, the edge cases
it must survive, and the checker/verifier that would enforce it. Name `candidate_file_changes` as
*proposed* targets only — do not edit, create, or mutate any file.
Produce `reading_scope_map`: an ordered, most-important-first list of file/dir paths the work step
should START reading from to make this change — the bounded read-set you prescribe to the worker so it
need not explore the repository blindly. It is GUIDANCE the worker may exceed (read further as the work
requires); it is never a write fence and is never fed to the Link gate.
`evidence_refs` MUST include inspected repository artifact references (file paths such as
`brick_protocol/support/...`, `brick_protocol/brick/...`, `brick_protocol/agent/...`, `brick_protocol/link/...`, `project/...`, or diff hunks actually read).
Packet-only labels are not enough for this grounding requirement.

When the design proposes that the NEXT stage run as a parallel fan, describe that proposal inside
`proposed_changes` and `checker_or_verifier_plan` using the deep-design `partition_plan` contract
(`brick_protocol/brick/templates/bricks/deep-design/return.yaml`) as its home — the design kind's own return shape
does not carry a top-level `partition_plan` field yet (deep-design first, staged adoption). Parallel
design lanes are mutually blind by law (상호 열람 금지): sibling design branches must not read each
other's evidence, and any fan you propose declares width ≤ 3 with pairwise-disjoint write fences.

Return: fill the `required_return_shape` from the return_template
(`brick_protocol/brick/templates/bricks/design/return.yaml`):
`observed_evidence`, `design_summary`, `relevant_current_structure`, `proposed_changes`, `unchanged_surfaces`,
`axis_responsibility`, `invariants`, `edge_cases`, `checker_or_verifier_plan`,
`candidate_file_changes`, `evidence_refs`, `not_proven`, `reading_scope_map`.
Keep everything as observed facts, options, and gaps — record what is *not yet proven*
(implementation readiness, semantic fitness of the proposed design) rather than asserting it works.

Do NOT return `success` / `failure` / `approved` / `quality` / `good_enough` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's. This Brick designs and
observes; it does not implement, judge, or route.

> This `## Design` body IS delivered to the Agent in the prompt as the static kind instruction
> (brick_protocol/support/connection/adapter_grant_policy._build_prompt, key `brick_instruction_body`), carried from
> this file by the Builder (plan_rendering carries the ## body onto the step_template row; composition
> stamps it onto the brick_row). It is a SEPARATE prompt section from the dynamic `work_statement`.
> Each `required_return_shape` field is guarded to appear here with guidance, both directions, across
> EVERY return template (check_bricks_spec_completeness._prose_return_shape_drift_violations), so this
> body and the return.yaml cannot drift. The frontmatter carries Brick contract fields plus Builder
> selection metadata (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared BAL
> rows. Keep this instruction GENERAL to the kind (building-specifics ride `work_statement`); do not
> claim it raises quality — the Link gate checks sufficiency, quality is the human's.

---
brick_kind: work
brick_word: work
performer_word: dev
requires_brick_write_scope: yes
capability_class: source_write
performer_lane_need: worker
agent_object_hint_ref: agent-object:dev
required_return_template_refs:
  - brick/templates/bricks/work/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Work Brick is the implementer — it does the declared implementation inside the Brick write scope, coding directly or using subagents/workflows as tools when the work is large or benefits from parallelism.
---
## Work

Perform the declared implementation or document work **inside the Brick write scope only**.
You are the implementer. Do the work yourself — but you are NOT limited to working alone: when the
work is large or benefits from parallel/independent effort, you MAY spawn subagents or workflows as
**tools** (the same way a capable engineer delegates pieces), then merge their results into ONE set of
changes under this Brick's `write_scope`. Orchestrating helpers is a **capability, not a separate role** —
you remain the single responsible implementer, and you do NOT bear verdicts (sufficiency and quality
stay the Link gate's and the human's).

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`work_statement`. The design report's `reading_scope_map` (when present) is an ordered,
most-important-first list of paths/dirs the design Brick recommends you START reading from — begin
there to orient quickly. It is GUIDANCE, not a fence: you MAY read further (any file) as the work
requires, and nothing enforces or limits your reads. Do the real work — implement / edit / write —
within `write_scope` (the write fence is separate and hard; reading is unconstrained).

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/work/return.yaml`):
`received_work_ref`, `made_changes`, `changed_files`, `observed_evidence`, `commands_run`,
`blocked_or_missing_evidence`, `handoff_refs`, `not_proven`.
(`no_changes_reason` is the `made_changes` waiver when no file/content change was made.)

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's.

> This `## Work` body IS delivered to the Agent in the prompt as the static kind instruction
> (support/connection/adapter_grant_policy._build_prompt, key `brick_instruction_body`), carried from
> this file by the Builder (plan_rendering carries the ## body onto the step_template row; composition
> stamps it onto the brick_row). It is a SEPARATE prompt section from the dynamic `work_statement`.
> Each `required_return_shape` field is guarded to appear here with guidance, both directions, across
> EVERY return template (check_bricks_spec_completeness._prose_return_shape_drift_violations), so this
> body and the return.yaml cannot drift. The frontmatter carries Brick contract fields plus Builder
> selection metadata (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared BAL
> rows. Keep this instruction GENERAL to the kind (building-specifics ride `work_statement`); do not
> claim it raises quality — the Link gate checks sufficiency, quality is the human's.

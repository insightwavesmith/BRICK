---
brick_kind: work
brick_word: work
performer_word: dev
requires_brick_write_scope: yes
performer_lane_need: worker
agent_object_hint_ref: agent-object:dev
required_return_template_refs:
  - brick/templates/bricks/work/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Work Brick performs declared implementation or document work inside the Brick write scope.
---
## Work

Perform the declared implementation or document work **inside the Brick write scope only**.

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

> This `## Work` body is the rich, free-form instruction the AGENT reads; the Builder does not
> parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

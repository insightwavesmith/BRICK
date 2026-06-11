---
brick_kind: closure
brick_word: closure
performer_word: coo
requires_brick_write_scope: no
performer_lane_need: leader
agent_object_hint_ref: agent-object:coo
required_return_template_refs:
  - brick/templates/bricks/closure/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Closure Brick records evidence, narrowly_proven, not_proven, remaining_delta, and next candidate movement.
---
## Closure

Record the closure synthesis for the Building so the parent objective is carried across child phases —
**without** judging success, quality, or Movement.

Input: the prior Bricks' reports (carried via the Link edges) plus this node's declared
`work_statement` / closure scope. Read the accumulated evidence and the parent objective; synthesize
what was observed, what is narrowly proven, what remains, and where the work could go next.

Do: assemble the closure from the carried evidence only. State `narrowly_proven` as the strictly
evidence-backed slice (proof scope may narrow, but the objective scope must be carried forward).
Name concrete future work in `remaining_delta` and `next_target_candidates`. Express
`parent_goal_delta_status` as observation language (matched / closed / open / missing / unknown delta
refs with evidence_refs) — **not** a percentage. Queue anything needing a human decision into
`deferred_smith_review_queue`.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/closure/return.yaml`):
`observed_evidence`, `narrowly_proven`, `not_proven`, `remaining_delta`, `parent_goal_delta_status`,
`next_target_candidates`, `deferred_smith_review_queue`, `transition_concern_evidence`.
(`not_proven` is next-target material, not a failure verdict.)

`transition_concern_evidence` (shape: `brick/templates/bricks/transition-concern-return.yaml`)
is **non-binding** Agent evidence — it carries `concern_ref`, `concern_kind`, `reason_refs`,
`related_boundary_refs`, `binding: false`; it MUST NOT carry `movement` / `target` / `target_ref` /
`route_target`. The forward Link carries this evidence onward; the concern never reroutes by itself.

Do NOT return `success` / `failure` / `approved` / `good_enough` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's. This Brick writes no
files and declares no source truth — it returns closure synthesis (observed facts + remaining delta)
only.

> This `## Closure` body is the rich, free-form instruction the AGENT reads; the Builder does not
> parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

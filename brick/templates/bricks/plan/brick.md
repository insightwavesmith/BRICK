---
brick_kind: plan
brick_word: plan
performer_word: pm
requires_brick_write_scope: no
performer_lane_need: leader
agent_object_hint_ref: agent-object:pm-lead
required_return_template_refs:
  - brick/templates/bricks/plan/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Plan Brick defines objective, scope, constraints, and next work boundary without implementation.
---
## plan

Define the objective, scope, constraints, and next work boundary **without doing any
implementation**.

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`work_statement`. Read the instruction chain, detect gaps, and bound the work — do NOT
write code, edit files, or produce implementation.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/plan/return.yaml`):
`objective_summary`, `scope_boundaries`, `constraints`, `missing_scope`,
`proposed_next_work_boundaries`, `observed_evidence`, `not_proven`, `transition_concern_evidence`.
Report `missing_scope` and `not_proven` honestly — an unbounded or unknown area is a
fact to surface, not a gap to fill by guessing.

`transition_concern_evidence` (shape: `brick/templates/bricks/transition-concern-return.yaml`)
is **non-binding** Agent evidence — it carries `concern_ref`, `concern_kind`, `reason_refs`,
`related_boundary_refs`, `binding: false`; it MUST NOT carry `movement` / `target` / `target_ref` /
`route_target`. The forward Link carries this evidence onward; the concern never reroutes by itself.
When you raise a concern for a REAL reproduced defect, point `related_boundary_refs` at the upstream
WORK node responsible (e.g. `brick:<the-work-node-id>`) — NOT yourself, NOT a `building-boundary:`
sentinel. The engine silently walks-on a self-ref or sentinel, so no reroute ever fires. Environment
or runtime constraints (no temp dir, write-scope limits, provider limits, read-only status, "live not
run") are NOT defects — record them in `not_proven`, never as a `transition_concern`.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's.
`proposed_next_work_boundaries` is a proposed boundary only, never a Movement decision.

> This `## plan` body is the rich, free-form instruction the AGENT reads; the Builder does not
> parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

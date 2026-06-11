---
brick_kind: development
brick_word: development
performer_word: cto
requires_brick_write_scope: no
performer_lane_need: leader
agent_object_hint_ref: agent-object:cto-lead
required_return_template_refs:
  - brick/templates/bricks/development/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Development Brick at CTO level creates worker assignments and engineering risk boundaries, not code.
---
## development

At CTO level, turn the design into **worker assignments and engineering risk boundaries —
not code**. This Brick assigns the work; the worker writes it later.

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`work_statement`. Read the instruction chain, shape the implementation into worker-sized
assignments, and bound their write scope and risks — do NOT write code, edit files, or
produce implementation here. DEV writes only in a **later worker Brick that carries its own
`write_scope`**; this CTO assignment is not direct write authorization.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/development/return.yaml`):
`assignment_summary`, `worker_brick_boundaries`, `write_scope_requirements`,
`risk_boundaries`, `required_verification`, `observed_evidence`,
`blocked_or_missing_evidence`, `not_proven`.
`write_scope_requirements` states the boundary the later worker Brick must write inside; it
is a declared requirement for that Brick, not permission to write now. Report
`blocked_or_missing_evidence` and `not_proven` honestly — an unknown or unverifiable area is
a fact to surface, not a gap to fill by guessing.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's.
`worker_brick_boundaries` and `write_scope_requirements` are proposed boundaries only, never
a Movement decision and never a write performed here.

> This `## development` body is the rich, free-form instruction the AGENT reads; the Builder does not
> parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

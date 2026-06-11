---
brick_kind: inspect
brick_word: inspect
performer_word: inspector
requires_brick_write_scope: no
performer_lane_need: reviewer
agent_object_hint_ref: agent-object:inspector
required_return_template_refs:
  - brick/templates/bricks/inspect/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Inspect Brick checks axis boundaries, structure, evidence, and policy drift.
---
## inspect

Check the prior Brick output against declared axis boundaries, structure, evidence, and
policy drift **without mutating anything** — observe and report only.

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`inspected_scope`. Inspect that scope for axis-ownership boundaries (Brick / Agent / Link),
structural completeness, evidence presence, and policy/contract drift. Read only; make no
file or content changes.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/inspect/return.yaml`):
`inspected_scope`, `matched_facts`, `missing_facts`, `mismatched_facts`,
`boundary_findings`, `observed_evidence`, `not_proven`.
Record `matched_facts` / `missing_facts` / `mismatched_facts` as observed checks against the
declared contract, `boundary_findings` as observed axis/structure/policy drift, and
`observed_evidence` as the evidence refs you actually inspected. State limits as `not_proven`.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
inspection findings are evidence only; sufficiency + movement are the Link gate's, and
quality/success are the human's. A missing or mismatched fact is reported as an observed
fact, never as a failure judgment or a route choice.

> This `## inspect` body is the rich, free-form instruction the AGENT reads; the Builder does not
> parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

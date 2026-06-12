---
brick_kind: design
brick_word: design
performer_word: design
requires_brick_write_scope: no
performer_lane_need: leader
agent_object_hint_ref: agent-object:design-lead
required_return_template_refs:
  - brick/templates/bricks/design/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
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
`evidence_refs` MUST include inspected repository artifact references (file paths such as
`support/...`, `brick/...`, `agent/...`, `link/...`, `project/...`, or diff hunks actually read).
Packet-only labels are not enough for this grounding requirement.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/design/return.yaml`):
`observed_evidence`, `design_summary`, `relevant_current_structure`, `proposed_changes`, `unchanged_surfaces`,
`axis_responsibility`, `invariants`, `edge_cases`, `checker_or_verifier_plan`,
`candidate_file_changes`, `evidence_refs`, `not_proven`.
Keep everything as observed facts, options, and gaps — record what is *not yet proven*
(implementation readiness, semantic fitness of the proposed design) rather than asserting it works.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's. This Brick designs and
observes; it does not implement, judge, or route.

> This `## Design` body is the rich, free-form instruction the AGENT reads; the Builder does not
> parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

---
brick_kind: review
brick_word: review
performer_word: qa_lead
requires_brick_write_scope: no
performer_lane_need: leader
agent_object_hint_ref: agent-object:qa-lead
required_return_template_refs:
  - brick/templates/bricks/review/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Review Brick checks the prior Brick output against declared work and return shape.
---
## Review

Check the prior Brick's output against the **declared work** and the **declared return shape** —
observe and report, do **not** mutate anything.

Input: the prior Brick's report (carried via the Link edge), the prior node's declared
`work_statement` / `return_template`, and this node's review intent. Compare what was actually
returned against what the work and the return shape required. Read sources to confirm — never
edit, write, or fix.

Do: identify what matches, what is missing or mismatched, and any axis/boundary violations,
each tied to the evidence you actually inspected. Optional `transition_concern_evidence` is
**non-binding** — it is evidence a Link disposition *may* adopt, never a Movement decision you make.
`evidence_used` MUST include inspected repository artifact references (file paths such as
`support/...`, `brick/...`, `agent/...`, `link/...`, `project/...`, or diff hunks actually read).
Packet-only labels are not enough for this grounding requirement.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/review/return.yaml`):
`observed_evidence`, `checked_work`, `checked_sources`, `observed_matches`, `missing_or_mismatched_facts`,
`boundary_violations`, `evidence_used`, `transition_concern_evidence`, `narrowly_proven`,
`not_proven`.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success/approval are the human's. Report only
observed FACTS, observations, and `not_proven`; `transition_concern_evidence` stays non-binding.

> This `## Review` body is the rich, free-form instruction the AGENT reads; the Builder does not
> parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

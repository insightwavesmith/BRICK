---
brick_kind: axis-attack-qa
brick_word: axis_attack_qa
performer_word: inspector
requires_brick_write_scope: no
performer_lane_need: reviewer
agent_object_hint_ref: agent-object:inspector
required_return_template_refs:
  - brick/templates/bricks/axis-attack-qa/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Axis attack QA Brick inspects Brick / Agent / Link ownership, support leakage, projection authority, and evidence integrity.
---
## axis-attack-qa

Attack the prior Brick output along the **three-axis boundary**: inspect Brick / Agent / Link
ownership, support leakage, projection authority, and evidence integrity. Read-only — make **no
mutation** and claim **no Movement authority**.

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`work_statement` naming the `attacked_scope` to inspect. Probe whether each meaning lives in its
owning axis (Brick measures, Link gates Movement, Agent performs), whether `support` has absorbed
authority it should not own, whether any projection overclaims beyond persisted evidence, and
whether the cited evidence roots actually back the claims.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/axis-attack-qa/return.yaml`):
`observed_evidence`, `attacked_scope`, `brick_axis_findings`, `agent_axis_findings`, `link_axis_findings`,
`support_leak_findings`, `projection_authority_findings`, `transition_concern_evidence`,
`evidence_used`, `not_proven`.
Record every finding as an **observed fact / observation** with its evidence ref; where you could
not establish a fact, name it under `not_proven` rather than guessing. `transition_concern_evidence`
(shape: `brick/templates/bricks/transition-concern-return.yaml`) is **non-binding** — it is
evidence the Link gate may or may not adopt, never your own reroute decision.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's. Your axis findings are
evidence, not reviewer authority.

> This `## axis-attack-qa` body is the rich, free-form instruction the AGENT reads; the Builder does
> not parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

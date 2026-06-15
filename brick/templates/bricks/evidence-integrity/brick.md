---
brick_kind: evidence-integrity
brick_word: evidence_integrity
performer_word: inspector
requires_brick_write_scope: yes
performer_lane_need: reviewer
agent_object_hint_ref: agent-object:inspector
required_return_template_refs:
  - brick/templates/bricks/evidence-integrity/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Evidence Integrity Brick checks persisted evidence roots, proof limits, and checker-overclaim risk.
---
## evidence-integrity

Check persisted evidence roots, proof limits, and checker-overclaim risk. QA-attack verifies by
**writing the BUILDING WORK-AREA** (run real checkers / FIRE / mutation probes to test the
evidence); the building runs in a **disposable W1 worktree sandbox**, so this work-area write
**never touches the customer live tree**. Still declare **no source truth** and claim **no Movement
authority**.

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`work_statement`. Inspect the persisted evidence — its roots, what it actually proves, where a
source may be stale, and where a checker or report may overclaim beyond the evidence it holds.
You MAY write the work-area to run checkers / probes (sandboxed in W1); you do NOT mutate the
customer source-truth and do NOT decide what the source truth *is*.
`evidence_used` MUST include inspected repository artifact references (file paths such as
`support/...`, `brick/...`, `agent/...`, `link/...`, `project/...`, or diff hunks actually read).
Packet-only labels are not enough for this grounding requirement.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/evidence-integrity/return.yaml`):
`observed_evidence`, `evidence_scope`, `persisted_evidence_roots`, `proof_limit_findings`, `stale_source_risks`,
`checker_overclaim_risks`, `missing_evidence`, `evidence_used`, `not_proven`.
Report what you observed as facts and observations — evidence gaps, stale-source risks, and
`not_proven` — never a verdict on whether the evidence is sufficient.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's; declaring the source
truth is not this Brick's to make.

> This `## evidence-integrity` body is the rich, free-form instruction the AGENT reads; the Builder
> does not parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

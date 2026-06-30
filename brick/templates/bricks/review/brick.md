---
brick_kind: review
brick_word: review
performer_word: qa_lead
requires_brick_write_scope: no
capability_class: read
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

Scope boundary: this Brick is a **read-only review**, not adversarial code QA. If the upstream work
is implementation, you still must inspect the actual changed files, diffs, checker output, or other
repository artifacts before recording `checked_sources`, `observed_matches`,
`missing_or_mismatched_facts`, or `boundary_violations`. If you only inspected a carried packet,
step-output summary, or report label, record the code/artifact claim under `not_proven` instead of
presenting it as checked. Use `code-attack-qa` when the Building needs sandboxed probe-writing,
negative-path reproduction, or regression attack.

Do: identify what matches, what is missing or mismatched, and any axis/boundary violations,
each tied to the evidence you actually inspected. Optional `transition_concern_evidence` is
**non-binding** — it is evidence a Link disposition *may* adopt, never a Movement decision you make.
`evidence_used` MUST include inspected repository artifact references (file paths such as
`support/...`, `brick/...`, `agent/...`, `link/...`, `project/...`, or diff hunks actually read).
Packet-only labels are not enough for this grounding requirement.

`transition_concern_evidence` (shape: `brick/templates/bricks/transition-concern-return.yaml`) is
**non-binding** Agent evidence; it carries `concern_ref`, `concern_kind`, `reason_refs`,
`related_boundary_refs`, `binding: false`. When you raise a concern for a REAL reproduced defect, aim
`related_boundary_refs` at the upstream WORK node responsible (plain declared node id,
`brick:<declared-node>`, `brick-instance:<declared-node>`, or
`brick-boundary:<declared-node>`) — NOT yourself, NOT a `building-boundary:` sentinel. The engine
silently walks-on a self-ref or sentinel, so no reroute ever fires. If the concern may be adopted,
keep `reason_refs` current-ledger-local and resolvable from this Building's recorded rows; cite
external files, prior Building evidence paths, URLs, or packet labels under `observed_evidence` /
`evidence_used`, not `reason_refs`. Environment or runtime constraints (no temp dir, write-scope
limits, provider limits, read-only status, "live not run") are NOT defects — record them in
`not_proven`, never as a `transition_concern`.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/review/return.yaml`):
`observed_evidence`, `checked_work`, `checked_sources`, `observed_matches`, `missing_or_mismatched_facts`,
`boundary_violations`, `evidence_used`, `transition_concern_evidence`, `narrowly_proven`,
`not_proven`.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success/approval are the human's. Report only
observed FACTS, observations, and `not_proven`; `transition_concern_evidence` stays non-binding.

> This `## Review` body IS delivered to the Agent in the prompt as the static kind instruction
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

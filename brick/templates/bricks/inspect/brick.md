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

Scope boundary: this Brick is **inspection**, not code QA. It may inspect repository artifacts when
the declared `inspected_scope` names them, but it must not substitute carried summaries for source
inspection. If code correctness, regression behavior, or negative-path reproduction is required,
the Building should use `code-attack-qa`; if three-axis ownership or support-authority leakage is
the target, use `axis-attack-qa`. For this `inspect` Brick, any uninspected source, diff, evidence
root, or policy surface stays in `not_proven`.

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

> This `## inspect` body IS delivered to the Agent in the prompt as the static kind instruction
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

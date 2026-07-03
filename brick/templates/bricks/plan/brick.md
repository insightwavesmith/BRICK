---
brick_kind: plan
brick_word: plan
performer_word: pm
requires_brick_write_scope: no
capability_class: read
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
WORK node responsible (plain declared node id, `brick:<declared-node>`,
`brick-instance:<declared-node>`, or `brick-boundary:<declared-node>`) — NOT yourself, NOT a
`building-boundary:` sentinel. The engine silently walks-on a self-ref or sentinel, so no reroute
ever fires. If the concern may be adopted, keep `reason_refs` current-ledger-local and resolvable
from this Building's recorded rows; cite external files, prior Building evidence paths, URLs, or
packet labels under `observed_evidence`, not `reason_refs`. A slash-containing `reason_refs`
address must name an existing step-output document under this Building's `work/step-outputs/`
subtree, with no `#fragment`; put step-output fragments, bare `file:line` citations,
non-step-output slash paths, document paths, and descriptive refs under `observed_evidence`, or use a
slashless opaque token such as `observation:<id>`. Environment or runtime constraints (no
temp dir, write-scope limits, provider limits, read-only status, "live not run") are NOT defects —
record them in `not_proven`, never as a `transition_concern`.

Do NOT return `success` / `failure` / `approved` / `quality` / `good_enough` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's.
`proposed_next_work_boundaries` is a proposed boundary only, never a Movement decision.

> This `## plan` body IS delivered to the Agent in the prompt as the static kind instruction
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

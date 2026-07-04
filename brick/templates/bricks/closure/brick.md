---
brick_kind: closure
brick_word: closure
performer_word: coo
requires_brick_write_scope: no
capability_class: read
performer_lane_need: leader
agent_object_hint_ref: agent-object:coo
required_return_template_refs:
  - brick/templates/bricks/closure/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Closure Brick records evidence, narrowly_proven, not_proven, remaining_delta, and next candidate movement.
---
## Closure

Record the closure synthesis for the Building so the parent objective is carried across child phases —
**without** judging success, quality, or Movement.

Input: the prior Bricks' reports (carried via the Link edges) plus this node's declared
`work_statement` / closure scope. Read the accumulated evidence and the parent objective; synthesize
what was observed, what is narrowly proven, what remains, and where the work could go next.

Do: assemble the closure from the carried evidence only. State `narrowly_proven` as the strictly
evidence-backed slice (proof scope may narrow, but the objective scope must be carried forward).
Name concrete future work in `remaining_delta` and `next_target_candidates`. Express
`parent_goal_delta_status` as a MAPPING whose keys are ONLY the six allowed sub-fields from the
return_template — `matched_delta_refs`, `closed_delta_refs`, `open_delta_refs`,
`missing_delta_refs`, `unknown_delta_refs`, `evidence_refs` — each holding plain-text refs.
Never place a `status`, verdict, or free-text key INSIDE this mapping (a sub-key containing
`status` is a forbidden return key and the whole return is rejected); it is observation
language, **not** a percentage or a verdict. Queue anything needing a human decision into
`deferred_smith_review_queue`.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/closure/return.yaml`):
`observed_evidence`, `narrowly_proven`, `not_proven`, `remaining_delta`, `parent_goal_delta_status`,
`next_target_candidates`, `deferred_smith_review_queue`, `transition_concern_evidence`,
`deliverable_crosscheck`.
(`not_proven` is next-target material, not a failure verdict.)

`deliverable_crosscheck` lists every numbered task deliverable as an audit row
(`deliverable_ref`, `implementation_status`, `diff_artifact_refs`, `evidence_refs`);
`implementation_status` is observation language (`implemented` / `partial` / `not_implemented` /
`not_applicable_read_only`), not a verdict. An implementation deliverable row with empty
`diff_artifact_refs` must be accompanied by `transition_concern_evidence` (`implementation_gap`) —
never by a complete-style return, and never deferred to a human review queue as a substitute
(0702 fake-landing postmortem).
When prior Work returns include `received_deliverables_echo`, compare the original contract's
numbered deliverables, the Work echo, and the diff artifacts as three separate observations. Record
any contract/echo/diff mismatch in `deliverable_crosscheck` without turning that comparison into
success, quality, approval, sufficiency, or Movement language.

`transition_concern_evidence` (shape: `brick/templates/bricks/transition-concern-return.yaml`)
is **non-binding** Agent evidence — it carries `concern_ref`, `concern_kind`, `reason_refs`,
`related_boundary_refs`, `binding: false`; it MUST NOT carry `movement` / `target` / `target_ref` /
`route_target`. The forward Link carries this evidence onward; the concern never reroutes by itself.
If there is no real transition concern, return `transition_concern_evidence: null` or omit the field;
never return `{}` as a no-concern placeholder. An empty object is malformed concern evidence and may
pause at the Link frontier instead of closing.
When you raise a concern for a REAL reproduced defect, aim `related_boundary_refs` at the upstream
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
If `concern_kind` is `verification_gap`, it is non-reroute evidence: leave
`related_boundary_refs` empty or use a `building-boundary:` sentinel, never an upstream Brick node.

Do NOT return `success` / `failure` / `approved` / `quality` / `good_enough` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's. This Brick writes no
files and declares no source truth — it returns closure synthesis (observed facts + remaining delta)
only.

> This `## Closure` body IS delivered to the Agent in the prompt as the static kind instruction
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

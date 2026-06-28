---
brick_kind: code-attack-qa
brick_word: code_attack_qa
performer_word: qa
requires_brick_write_scope: yes
capability_class: probe_write
performer_lane_need: reviewer
agent_object_hint_ref: agent-object:qa
required_return_template_refs:
  - brick/templates/bricks/code-attack-qa/return.yaml
  - brick/templates/bricks/transition-concern-return.yaml
link_movement_literal: forward
brick_contract: Code attack QA Brick attacks implementation, regression, and negative-probe evidence against the declared work contract.
---
## code-attack-qa

Attack the prior Brick's implementation against the **declared work contract** — probe for
regression, negative-path failures, and boundary violations. QA-attack verifies by **writing the
BUILDING WORK-AREA**: run real checkers / FIRE / mutation probes to break the contract. The
building runs in a **disposable W1 worktree sandbox**, so this work-area write **never touches the
customer live tree**. You still claim **NO Movement authority** and **no source-truth verdict** — a
failing probe is an observed fact, not a judgment. Run `check_profile.py --all` from INSIDE this
building's W1 worktree (your dispatch cwd) — never from a separate `/tmp` git-archive copy: the
archive lacks the changes under test, and reaching outside the worktree is blocked by the sandbox.
Capability taxonomy: `read` means repo/evidence/diff/raw/step-output inspection;
`probe_write` / `verification_write` means disposable W1/temp/cache/test fixture/checker
output/negative probe/generated probe output writes; `source_write` means real repo source
mutation. This Brick may perform probe_write / verification_write only. It must not create, edit,
delete, or rewrite real repo source files as source truth.

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`work_statement` (the work contract under attack). Read the changed files and the evidence the
upstream Brick returned. Run negative probes / regression probes against the declared contract —
hunt for the cases that break it, not the ones that confirm it.

Do: read the implementation and its returned evidence; design and run negative probes and
regression probes; record which probes failed or could not be run; note boundary violations
against the declared contract; capture the exact evidence (commands, outputs, refs) you relied on.
`evidence_used` MUST include inspected repository artifact references (file paths such as
`support/...`, `brick/...`, `agent/...`, `link/...`, `project/...`, or diff hunks actually read).
Packet-only labels are not enough for this grounding requirement.

Outer-lens duty: independently reproduce the reported symptom from this node's task source or
incoming Link handoff, not from the upstream builder's fixtures or happy-path probes. Build your
own QA probes for that reproduction; builder fixtures may be inspected as evidence, but they MUST
NOT be reused as the QA proof. Drive at least one real entry surface that a real caller uses
(command, function, projection bake, checker profile, or other declared verb/surface) and record
the observed output. In `observed_evidence`, include the required evidence triple as structured
entries: `symptom_reproduction` (what was independently reproduced and how), `own_probes` (QA-built
probes distinct from builder fixtures), and `real_entry_surface` (which real verb/surface was
driven and what it produced). These are structured `observed_evidence` entries, not additional
top-level return keys, so the closed AgentFact return shape stays the one declared below.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/code-attack-qa/return.yaml`):
`observed_evidence`, `attacked_work`, `checked_sources`, `regression_risks`, `negative_probe_observations`,
`failing_or_missing_probes`, `boundary_violations`, `transition_concern_evidence`, `evidence_used`,
`not_proven`.
`transition_concern_evidence` (shape: `brick/templates/bricks/transition-concern-return.yaml`)
is **local, non-binding** Agent evidence for this fan-in source QA lane — it remains in the
Brick-required return shape, but it is **not Link-facing before closure-synthesis**. Support filters
Link carry through this return.yaml's `carries_forward_fields`, which excludes
`transition_concern_evidence`; closure / closure-synthesis may return Link-facing
`transition_concern_evidence` only under declared policy. This field carries `concern_ref`,
`concern_kind`, `reason_refs`, `related_boundary_refs`, `binding: false`; it MUST NOT carry
`movement` / `target` / `target_ref` / `route_target`, and it never reroutes by itself.
When a probe reproduces a REAL defect, aim `related_boundary_refs` at the upstream WORK node
responsible (e.g. `brick:<the-work-node-id>`) — NOT yourself, NOT a `building-boundary:` sentinel.
The engine silently walks-on a self-ref or sentinel, so no reroute ever fires. Environment, runtime,
provider, read-only, no-temp-dir, missing-probe, or "live not run" constraints are NOT upstream
implementation defects — record them in `not_proven`, or as non-reroute `verification_gap` evidence
with empty `related_boundary_refs` or a `building-boundary:` sentinel. Never attach a Brick-node
reroute address to `verification_gap`.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
a failing probe is an observed **fact**, not a verdict. Whether the failures are sufficient to
reroute is the Link gate's; success / quality are the human's. Report only observed facts, failing
or missing probes, and `not_proven` (full regression coverage, semantic correctness of the
implementation, and support loader behavior are explicitly out of your proof reach).

> This `## code-attack-qa` body IS delivered to the Agent in the prompt as the static kind instruction
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

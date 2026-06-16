---
brick_kind: code-attack-qa
brick_word: code_attack_qa
performer_word: qa
requires_brick_write_scope: yes
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
is **non-binding** Agent evidence — it carries `concern_ref`, `concern_kind`, `reason_refs`,
`related_boundary_refs`, `binding: false`; it MUST NOT carry `movement` / `target` / `target_ref` /
`route_target`. Forward Link carries this evidence to the declared fan-in or closure boundary; the
concern never reroutes by itself.
When a probe reproduces a REAL defect, aim `related_boundary_refs` at the upstream WORK node
responsible (e.g. `brick:<the-work-node-id>`) — NOT yourself, NOT a `building-boundary:` sentinel.
The engine silently walks-on a self-ref or sentinel, so no reroute ever fires. Environment or runtime
constraints (no temp dir, write-scope limits, provider limits, read-only status, "live not run") are
NOT defects — record them in `not_proven`, never as a `transition_concern`.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
a failing probe is an observed **fact**, not a verdict. Whether the failures are sufficient to
reroute is the Link gate's; success / quality are the human's. Report only observed facts, failing
or missing probes, and `not_proven` (full regression coverage, semantic correctness of the
implementation, and support loader behavior are explicitly out of your proof reach).

> This `## code-attack-qa` body is the rich, free-form instruction the AGENT reads; the Builder does
> not parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

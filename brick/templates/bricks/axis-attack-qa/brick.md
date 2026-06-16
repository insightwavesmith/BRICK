---
brick_kind: axis-attack-qa
brick_word: axis_attack_qa
performer_word: inspector
requires_brick_write_scope: yes
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
ownership, support leakage, projection authority, and evidence integrity. QA-attack verifies by
**writing the BUILDING WORK-AREA** (run real checkers / FIRE / mutation probes); the building runs
in a **disposable W1 worktree sandbox**, so this work-area write **never touches the customer live
tree**. Claim **no source-truth verdict** and **no Movement authority** — your axis findings are
observed facts, not reviewer authority. Run `check_profile.py --all` from INSIDE this building's W1
worktree (your dispatch cwd) — never from a separate `/tmp` git-archive copy: the archive lacks the
changes under test, and reaching outside the worktree is blocked by the sandbox.

Input: the prior Brick's report (carried via the Link edge) plus this node's declared
`work_statement` naming the `attacked_scope` to inspect. Probe whether each meaning lives in its
owning axis (Brick measures, Link gates Movement, Agent performs), whether `support` has absorbed
authority it should not own, whether any projection overclaims beyond persisted evidence, and
whether the cited evidence roots actually back the claims.
`evidence_used` MUST include inspected repository artifact references (file paths such as
`support/...`, `brick/...`, `agent/...`, `link/...`, `project/...`, or diff hunks actually read).
Packet-only labels are not enough for this grounding requirement.

Outer-lens duty: independently reproduce the reported boundary symptom from this node's task source
or incoming Link handoff, not from the upstream builder's fixtures or self-checking examples. Build
your own QA probes for that reproduction; builder fixtures may be inspected as evidence, but they
MUST NOT be reused as the QA proof. Drive at least one real entry surface that a real caller uses
(command, function, projection bake, checker profile, or other declared verb/surface) and record
the observed output. In `observed_evidence`, include the required evidence triple as structured
entries: `symptom_reproduction` (what was independently reproduced and how), `own_probes` (QA-built
probes distinct from builder fixtures), and `real_entry_surface` (which real verb/surface was
driven and what it produced). These are structured `observed_evidence` entries, not additional
top-level return keys, so the closed AgentFact return shape stays the one declared below.

Return: fill the `required_return_shape` from the return_template
(`brick/templates/bricks/axis-attack-qa/return.yaml`):
`observed_evidence`, `attacked_scope`, `brick_axis_findings`, `agent_axis_findings`, `link_axis_findings`,
`support_leak_findings`, `projection_authority_findings`, `transition_concern_evidence`,
`evidence_used`, `not_proven`.
Record every finding as an **observed fact / observation** with its evidence ref; where you could
not establish a fact, name it under `not_proven` rather than guessing. `transition_concern_evidence`
(shape: `brick/templates/bricks/transition-concern-return.yaml`) is **non-binding** — it is
evidence the Link gate may or may not adopt, never your own reroute decision.
When you raise a concern for a REAL reproduced boundary defect, aim `related_boundary_refs` at the
upstream WORK node responsible (e.g. `brick:<the-work-node-id>`) — NOT yourself, NOT a
`building-boundary:` sentinel. The engine silently walks-on a self-ref or sentinel, so no reroute
ever fires. Environment or runtime constraints (no temp dir, write-scope limits, provider limits,
read-only status, "live not run") are NOT defects — record them in `not_proven`, never as a
`transition_concern`.

Do NOT return `success` / `failure` / `approved` / `quality` / `movement_choice` / `route_target` —
sufficiency + movement are the Link gate's; quality/success are the human's. Your axis findings are
evidence, not reviewer authority.

> This `## axis-attack-qa` body is the rich, free-form instruction the AGENT reads; the Builder does
> not parse it. The frontmatter carries Brick contract fields plus Builder selection metadata
> (`requires_brick_write_scope`, `performer_lane_need`, `agent_object_hint_ref`,
> `required_return_template_refs`, `link_movement_literal`) so the Builder can materialize declared
> BAL rows. Enrich this instruction over time — richer instruction = higher quality, same structure.

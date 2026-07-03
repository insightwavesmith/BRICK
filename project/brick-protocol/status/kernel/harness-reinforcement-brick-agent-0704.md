# Harness Reinforcement — Brick Contract + Agent Lane Surfaces (0704)

Landing commit: `87ae5df0`. Scope: Brick axis (work-unit + instruction contract
surfaces) and Agent axis (lane capability declaration surfaces) ONLY — no
engine, link, or support mutation. Origin: 0704 two-axis harness audit
(13 candidates → adversarial verify → 9 survivors + 4 critic-missing items),
every item anchored to a measured 0702–0703 incident.

## What landed

Brick axis (brick/templates/bricks/*):
- `forbidden_return_keys` unified across all 10 KINDs to
  {success, failure, approved, quality, good_enough, movement_choice,
  route_target} — previously only closure forbade `good_enough` and closure
  alone omitted `quality`; the `Do NOT return` prose lines were synced in the
  same commit.
- work: new `rules:` block (return.yaml) + self-report/measurement coherence
  prose (brick.md) — `made_changes` must not contradict the measured
  `changed_files` overwrite; no complete-style narrative without a real diff
  artifact (0702 fake-landing).
- QA triad (code-attack-qa / axis-attack-qa / evidence-integrity): standard
  upstream crosscheck item in each brick.md — self-reported
  `made_changes`/`changed_files` vs actual diff artifacts, each phrased in the
  KIND's own return vocabulary (`implementation_gap` finding /
  `agent_axis_findings` / `checker_overclaim_risks`).
- development: `required_verification` must now declare per-assignment
  completion line + lane-environment-executable proofs (0703: unbounded
  meta-verification and permanent not_proven noise both traced to missing
  verification boundaries).

Agent axis (agent/*):
- prompts/dev.md rebuilt to the house 5-section structure (was 4 generic
  sentences); carries the deliverable-vs-diff self-crosscheck and the
  "no complete-style narrative without diff" rule — the 0702 prescription
  previously existed only on the catching side (qa.md/coo.md), not the
  committing side.
- prompts/{cto-lead,design-lead,pm-lead,qa-lead}.md: Output sections now
  require file:line grounding for repo-state observed_evidence; ungrounded
  carried claims belong under not_proven.
- prompts/qa.md: explicit Output section (closed AgentFact + code-attack-qa
  field list); prompts/coo.md + qa.md + qa-lead.md: positive-form clause that
  cause-isolating honest partial returns are CORRECT lane behavior (0703 #14).
- disciplines/model-lane-matching.md (new) bound via discipline_refs on all 8
  agent objects: codex=implementation/finishing/code-QA, claude
  sonnet-xhigh=investigation/axis/evidence-QA, gemini=low-risk review lenses
  only, fable5=never a lane model. Dispatch outside the constraint is an
  Agent-axis deviation to surface.
- hooks/registry.yaml token-cost-discipline description now states structured
  step-output fields persist in full (output_excerpt is a 600-char preview) so
  lanes do not over-truncate returns for cost.

## Verification (execution evidence)

- Focused checkers green: check_bricks_spec_completeness (10 specs, prose
  drift guard), check_agent_resource_resolution (119 refs incl. 8 new
  discipline refs), check_agent_object_schema_single_source,
  check_brick_template_catalog_restructure.
- Full profile green in a detached gate worktree at `87ae5df0`:
  `check_profile.py --all` RC=0 (structure-template-integrity 5,543 targets;
  tier-a three-axis conformance FIRE probe).
- Independent two-lens diff attack (sonnet, xhigh; not self-verified): both
  lenses ok, 0 critical. Findings recorded below.

## Recorded gaps (follow-on candidates, NOT landed here)

1. Declaration/enforcement split (major, pre-existing, now visible):
   `forbidden_return_keys` in return.yaml is a catalog-projected declaration
   only; the runtime return gate is the separate constant
   `agent/return_fact.py` TOP_LEVEL_VERDICT_KEYS (which does not contain
   `good_enough`). Per the axis rule the field is the declaration and the gate
   is a later consumer — the enforcement sync is a small follow-on work Brick
   (add `good_enough` to TOP_LEVEL_VERDICT_KEYS + behavior-RED proof).
2. False-RED latency: check_brick_template_catalog_restructure
   `_return_field_declarations` treats free-text `rules:` sentences as field
   name candidates; safe today (verified by execution), but a future rules
   sentence containing a bare forbidden token (e.g. "movement_choice") would
   false-RED. Whitelisting `rules:` in that walker is a follow-on candidate.
3. Held for Smith: reroute-defaults.yaml (declared_by: smith,
   constitutional-default) — proposed but NOT applied: re_instruction should
   restate the contract termination line it serves. Needs Smith's declaration
   gate.
4. QA-triad return.yamls carry no `rules:` blocks (prose attack items only) —
   deliberate: their crosscheck is an attack instruction, not a return-shape
   rule; noted so the asymmetry is not read as an omission.

Proof limits: checker/profile green and the diff-attack lenses are support
evidence only — not source truth, not success judgment, not quality judgment,
not Movement authority.

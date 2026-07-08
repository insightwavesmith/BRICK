# Route V2 ⑥d/⑥e Human Gate Packet — 0709

Status: support evidence only. This packet does not approve implementation,
does not choose Movement, does not judge success or quality, and does not make
Route V2 source truth. It prepares the human/Smith gate required before any
Route V2 `route_materialization.py` extension or walker integration Building.

## 0. Gate question

Human gate asks whether to open the next declared Building(s) for Route V2
post-R2 work:

```text
⑥d: route_materialization view/provenance extension review
⑥e: walker_kernel / walker_resume integration design and implementation
```

Default state remains HOLD until this gate is explicitly approved.

## 1. Evidence already landed

```text
R0 architecture doc:
  project/brick-protocol/status/kernel/route-v2-sealed-materialization-architecture.md
  landed: 47cf35a4b

R1 checker fence / fixtures:
  brick_protocol/support/checkers/profiles/route_v2_sealed_materialization.yaml
  brick_protocol/support/checkers/fixtures/route_v2/**
  landed: 47cf35a4b

R2 read-only view builder:
  brick_protocol/support/operator/route_v2_views.py
  brick_protocol/support/checkers/check_route_v2_views.py
  landed: 134ad9550
  import-identity registry repair: 6f5a4a73e

R2 dogfood:
  project/brick-protocol/status/kernel/dogfood/0708-route-v2-view-dogfood.md
  landed: 39e120ac0

GOAL SHA correction:
  project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
  landed: 3412604e3
```

## 2. Narrowly proven before this gate

Observed by the Route V2 checker/dogfood track:

```text
- concern_kind remains sealed to the current 8 kinds.
- verification_gap is non-reroute evidence.
- Movement literals remain forward | reroute.
- hold, paused, held_for_coo_review are gate/lifecycle states, not Movement.
- implementation_gap can render route-policy eligibility and the existing
  route_materialization view.
- verification_gap does not materialize into a reroute view.
- gate_state and movement_candidate remain separate projection fields.
- delta-QA factual fields are preserved:
  made_changes, changed_files, diff_refs, evidence_refs.
- success, quality, movement, movement_choice, and route_target probes are
  rejected before Route V2 view rendering.
```

## 3. Three-axis attribution

```text
Brick evidence:
  Route V2 post-R2 work is a work-contract question: whether to extend the
  existing materialization view/provenance and whether to declare a walker
  integration Building. The work must preserve the existing route work contract:
  sealed concern kinds, non-reroute verification_gap, delta-QA facts, and no new
  route engine.

Agent evidence:
  Agent-facing input remains transition_concern_evidence inside the closed
  returned fact. No new AgentFact field, Agent singleton runtime_profile, or
  provider/model/adapter exposure is admitted by this packet.

Link evidence:
  Link owns Movement and route replay facts. Any future reroute row must remain
  caller/COO/human-declared or later admitted policy/template evidence. hold /
  paused / held_for_coo_review remain lifecycle/gate states only.

Support surface:
  route_v2_views.py and route_materialization.py are support evidence plumbing.
  walker_kernel.py and walker_resume.py are support walkers over declared plans.
  None of these support surfaces may become source truth, quality judgment,
  success judgment, Movement authority, or a route target selector.

Rejected shortcut:
  Do not treat the R2 dogfood green result as permission to edit walker_kernel,
  walker_resume, link resources, Agent return facts, or a new route_scope /
  route_v2_engine surface.
```

## 4. ⑥d candidate — route_materialization extension review

### 4.1 Allowed candidate scope after explicit approval

A ⑥d Building may inspect and, only if needed, narrowly extend the existing
route materialization/provenance view:

```text
candidate write_scope after approval:
  - brick_protocol/support/operator/route_materialization.py
  - brick_protocol/support/checkers/check_route_v2_views.py or a narrowly named
    existing/admitted checker if the extension needs checker coverage
  - brick_protocol/support/checkers/profiles/route_v2_sealed_materialization.yaml
  - project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
  - this packet or a follow-up support evidence note
```

### 4.2 Required constraints

```text
- Prefer extending the existing route_materialization view over adding a new
  module.
- Do not create route_scope.py.
- Do not create route_v2_engine.py.
- Do not add a new concern_kind.
- Do not make verification_gap reroute-eligible.
- Do not promote route_policy_contract to source-truth RoutePolicyFact.
- Do not add success, quality, approved, good_enough, movement_choice, or
  support-chosen route_target fields.
- Do not create automatic repair/replay execution.
- Keep route_replay_plan caller/COO/human-declared or later admitted by an
  explicit Link policy/template.
- Preserve author_ref seals: support, Agent, provider, session, tool, hook,
  credential, secret, and token refs must not author route replay plans.
```

### 4.3 ⑥d acceptance evidence

A ⑥d Building is not accepted by code diff alone. Required evidence:

```text
- Explicit human/Smith approval record for opening ⑥d.
- Exact changed_files list.
- Checker coverage for any changed materialization/provenance behavior.
- Negative probes for forbidden authority fields and forbidden new surfaces.
- python3 -m compileall -q brick_protocol
- python3 brick_protocol/support/checkers/check_route_v2_views.py
- python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_sealed_materialization
- clean detached worktree: python3 brick_protocol/support/checkers/check_profile.py --all
- git diff --check
- GOAL/status update with remaining_delta and next gate.
```

## 5. ⑥e candidate — walker integration

### 5.1 Gate state

⑥e remains higher risk than ⑥d and should open only after ⑥d disposition is
clear or after Smith explicitly approves skipping/deferring ⑥d changes.

### 5.2 Allowed candidate scope after explicit approval

```text
candidate write_scope after approval:
  - brick_protocol/support/operator/walker_kernel.py
  - brick_protocol/support/operator/walker_resume.py
  - narrowly required checker/profile/fixture files
  - project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
  - a follow-up dogfood / human-gate evidence note
```

### 5.3 Required constraints

```text
- Walker must consume declared route/movement evidence only; it must not choose
  Movement or route target by itself.
- Walker must not classify Agent return success/failure/quality.
- Walker must not create undeclared GateFacts.
- Walker must not make hold/paused/held_for_coo_review Movement literals.
- Walker must preserve fake-landing defense by carrying factual QA claims:
  made_changes, changed_files, diff_refs, evidence_refs.
- Walker must not treat verification_gap as reroute eligibility.
- Walker must not mutate AgentFact, Link resources, or concern_kind vocabulary.
- Walker must not introduce scheduler/queue/retry runtime ownership.
```

### 5.4 ⑥e acceptance evidence

```text
- Explicit human/Smith approval record for opening ⑥e.
- Declared Building/worktree sandbox evidence; no live checkout run_building_intake.
- Exact changed_files list.
- Before/after route/walker fixture proving declared route evidence is consumed
  without support-chosen Movement.
- Negative probe: hold/paused/held_for_coo_review cannot become Movement.
- Negative probe: verification_gap cannot reroute.
- Negative probe: success/quality/movement_choice/route_target authority fields
  cannot be emitted as walker decision fields.
- Dogfood over at least one implementation_gap route and one verification_gap
  non-reroute observation.
- python3 -m compileall -q brick_protocol
- focused route/walker checker profile(s)
- clean detached worktree: python3 brick_protocol/support/checkers/check_profile.py --all
- git diff --check
- GOAL/status update with remaining_delta and next gate.
```

## 6. Human decision options

```text
Option A — APPROVE ⑥d only:
  Open a declared sandbox Building for route_materialization view/provenance
  extension review. Keep walker integration HOLD.

Option B — APPROVE ⑥d then ⑥e sequence:
  First run ⑥d. If ⑥d proof is green and no new human gate is triggered, then
  prepare/open ⑥e walker integration Building.

Option C — APPROVE ⑥e without ⑥d code change:
  Allowed only if Smith explicitly decides the existing route_materialization
  surface is sufficient and ⑥e must consume the current R2 view as-is. Record
  that as a human gate fact before opening ⑥e.

Option D — KEEP HOLD:
  Do not open ⑥d/⑥e. Proceed to ⑩ cleanup/customer UX planning instead.
```

Recommended COO disposition candidate:

```text
Option B, but only as a candidate for Smith/human approval:
  ⑥d route_materialization review first, then ⑥e walker integration only after
  ⑥d evidence is green or explicitly deemed unnecessary.
```

## 7. Not proven / remaining delta

```text
- No ⑥d implementation has been opened by this packet.
- No walker integration has been opened by this packet.
- Semantic correctness of future Agent concerns is not proven.
- Runtime behavior of future route/walker integration is not proven.
- Automatic repair/replay execution is not proven and not approved.
- Customer UX / cleanup ⑩a~⑩g remains pending.
```

## 8. Movement language

This packet uses no Link Movement as its own disposition. The next operational
state is a human/Smith gate state:

```text
gate_state: held_for_human_gate
movement_candidate: none supplied by this packet
```

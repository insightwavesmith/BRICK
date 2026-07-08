# Route V2 6e Walker Integration Design — 0709

Status: support/design evidence only. This document does not edit
`walker_kernel.py` or `walker_resume.py`, does not implement walker integration,
does not choose Link Movement, does not judge success or quality, and does not
make Route V2 source truth. It is the 6e design note required by the human-gate
approval before any declared walker integration Building may be opened.

## 0. Gate / approval lineage

```text
human-gate packet:   project/brick-protocol/status/kernel/route-v2-human-gate-packet-0709.md
human-gate approval: project/brick-protocol/status/kernel/route-v2-human-gate-approval-0709.md
6d review:           project/brick-protocol/status/kernel/route-v2-6d-materialization-review-0709.md
R0/R1 architecture:  project/brick-protocol/status/kernel/route-v2-sealed-materialization-architecture.md
R2 view dogfood:     project/brick-protocol/status/kernel/dogfood/0708-route-v2-view-dogfood.md
```

Approved sequence (Option B): open 6d first; keep 6e HOLD until 6d is green or
explicitly unnecessary. 6d is now closed as `no code change needed`
(`route_materialization.py` sufficient as-is for the R2 -> 6e design input).
Therefore 6e may move from generic HOLD to this design step only. Walker
implementation remains gated: it requires a separate explicit human/Smith
approval and a declared Building/worktree sandbox.

This design note is COO operating work (docs/status/gate evidence). It is not a
walker code change and must not be treated as launch authorization.

## 1. Problem statement

Route V2 R0/R1/R2 produced a sealed, read-only materialization view over
already-declared Brick/Agent/Link facts. The walker is the runtime that actually
crosses one step at a time and records reroute-adoption evidence. 6e must answer
one question:

```text
How does the runtime walker relate to the Route V2 sealed materialization view
WITHOUT (a) duplicating walker logic, (b) giving Route V2 Movement authority,
or (c) letting the walker inherit any Route V2 authoring power it does not
already have?
```

### 1.1 Critical grounding fact (avoids a duplicate-engine mistake)

The walker does NOT currently call Route V2. It already owns an independent
concern -> reroute classification path:

```text
brick_protocol/support/operator/walker_transition_concern.py
  _transition_concern_observation_from_step_result(...)
  _classify_reroute_target(...)            # classifies, does not pick
  _build_invalid_transition_concern_hold(...)
```

And Route V2 renders an independent read-only projection:

```text
brick_protocol/support/operator/route_v2_views.py
  render_route_v2_view(...)                 # read-only, forbids movement/target keys
  -> route_materialization.materialize_transition_concern_disposition(...)
```

Both consume the same sealed source facts (`transition_concern_evidence`,
`concern_kind`, the route policy, and a caller/COO-declared route replay plan),
but through two separate code paths. So 6e is not "make the walker use a new
engine." The two legitimate design shapes are:

```text
SHAPE A (recommended): observation-only overlay
  Walker keeps its existing reroute classification as the authority path.
  Route V2 view is attached as READ-ONLY evidence next to the walker's own
  reroute-adoption/hold record. No walker control flow consumes the Route V2
  view to decide Movement or target.

SHAPE B (deferred, higher risk): shared-helper consolidation
  Walker and Route V2 both call one shared classifier so the view and the
  runtime decision cannot drift. Requires editing walker_transition_concern.py
  and re-proving the entire reroute/hold/fan-in matrix. NOT in 6e scope.
```

6e adopts SHAPE A. SHAPE B is recorded as a future candidate only.

### 1.2 Corrections from live-code re-derivation

Two implementation hazards are visible in the current code and must be part of
the 6e design before any worker touches walker code:

```text
H1. route_policy is NOT currently a direct walker input.
    The walker currently reads the completed step, the projected Link row,
    route_replay_plan fields on that Link row, reroute budgets, and route-policy
    provenance. It does not currently hold the loaded route-policy YAML mapping
    that render_route_v2_view(...) needs for materialization. A 6e Building must
    therefore use only caller/COO/Link-declared policy input or render the view
    without policy/materialization. It must not silently load or default a route
    policy from support.

H2. reroute_adoption_record and hold_record are contract-derived closed shapes.
    build_reroute_adoption_record(...) and build_hold_record(...) reject
    undeclared fields through support/recording/contracts.py. Therefore 6e must
    not casually add route_v2_view_evidence inside those records. The recommended
    home is a top-level dynamic_walker_evidence.route_v2_view_observations list
    keyed back to reroute_ref / source_step_ref / source_transition_concern_ref.
    If a future worker wants to nest the view inside reroute/hold records, that
    is a recording-contract extension and needs its own checker update.
```

These two hazards do not change the safe direction (SHAPE A), but they narrow
the implementation seam: Route V2 evidence is a dynamic-walker evidence sibling,
not a hidden new field inside the existing reroute/hold record contract, and its
policy input must be declared/proven rather than support-invented.

## 2. Exact walker integration seam

### 2.1 Where the seam is

The only admitted 6e seam is a read-only evidence attachment at the point where
the walker has already finished classifying a completed node's transition concern
and is about to record its reroute-adoption or hold evidence.

```text
process_one_node(...)                         # walker_kernel.py
  -> _transition_concern_observation_from_step_result(step_result)   [existing]
  -> _classify_reroute_target(concern, declared_bricks)              [existing]
  -> (existing) build_reroute_adoption_record / build_hold_record
  -> [6e] append route_v2_view_observation to dynamic_walker_evidence as a
         NON-BINDING sibling observation keyed back to the existing record refs
```

The seam is after the walker's own decision is computed and only on the
recording/evidence carry, never on the loop control that reads
`gate_sequence_decision` (walker_kernel.py around the `hold / reroute / fan-in /
next / break` control block). The Route V2 view must not feed that control block.
The recommended persistent home is:

```text
dynamic_walker_evidence["route_v2_view_observations"] = [
  {
    "kind": "route_v2_view_observation",
    "binding": "advisory",
    "adopted_as_movement": False,
    "reroute_ref": "<existing reroute/hold ref, if any>",
    "source_step_ref": "<existing step ref>",
    "source_transition_concern_ref": "<existing concern ref>",
    "route_policy_input_state": "declared|absent|blocked",
    "route_v2_view": <render_route_v2_view packet>
  }
]
```

Do not place that packet inside `reroute_adoption_record` or `hold_record` unless
the recording contract and its checker are explicitly extended in the same
Building.

### 2.2 What crosses the seam (inputs the walker already holds)

```text
transition_concern_evidence   <- from the completed Agent return (existing)
concern_kind                  <- sealed 8-kind vocabulary (existing)
route_policy                  <- declared/proven input only; NOT currently a direct walker input
declared_route_replay_plan    <- caller/COO/human-declared Link row/input, if present
gate_state                    <- lifecycle word (hold|paused|held_for_coo_review) or ""
movement_candidate            <- the walker's OWN classified movement (forward|reroute) or ""
delta_qa_fact                 <- observed closed-return facts only; missing fields stay empty
```

No new Agent field, no AgentFact mutation, no new concern_kind, no new Link row
shape is introduced. The walker passes what it already computed.

### 2.3 What comes back across the seam (evidence only)

`render_route_v2_view(...)` returns a packet whose top-level keys are already
forbidden from containing `movement`, `movement_choice`, `route_target`,
`target_ref`, `success`, `failure`, `quality`, `approved`, `good_enough`,
`auto_repair`, `auto_replay`, `walker_kernel`, `walker_resume`, `route_scope`,
and `route_v2_engine` (enforced today by `_reject_forbidden_keys` /
`_FORBIDDEN_TOP_LEVEL_KEYS` in `route_v2_views.py`). The walker attaches this
packet verbatim only under the top-level dynamic-walker observation list
shown in section 2.1. It must carry explicit advisory markers:

```text
route_v2_view_observation.binding = "advisory"
route_v2_view_observation.adopted_as_movement = False
route_v2_view_observation.route_policy_input_state = declared|absent|blocked
```

This mirrors the existing `fan_in_source_transition_concern_observation`
advisory pattern (`walker_kernel.py` `_source_lane_transition_concern_observation`,
which already records `transition_concern_adoption="advisory"` and
`adopted_as_movement=False`). It also respects the existing reroute/hold
recording contract, whose emitters reject undeclared fields.

## 3. How the walker consumes declared route/movement evidence

```text
1. Walker completes a node and builds its transition-concern observation
   (existing path). The concern is Agent-authored evidence inside the closed
   return; the walker does not invent it.
2. Walker classifies the reroute target with _classify_reroute_target (existing).
   This remains the SOLE authority for whether the runtime reroutes and where.
3. Walker records its reroute-adoption/hold evidence (existing).
4. [6e] Walker ALSO renders a Route V2 read-only view from the same inputs
   that are already present or explicitly declared for this Building. If no
   declared route_policy mapping is available, the view must render with
   route_policy=None (eligibility observation only) or record
   route_policy_input_state=blocked; it must not load a support default. The
   view's movement_candidate is populated from the walker's ALREADY-CLASSIFIED
   movement, not the reverse.
```

The direction of authority is one-way: walker decision -> Route V2 view. The view
never sources the walker's decision.

## 4. How the walker avoids choosing Movement or target

```text
- The walker's Movement/target authority is unchanged. It stays in
  _classify_reroute_target + the existing reroute-budget/hold/fan-in path.
- render_route_v2_view is called with movement_candidate = the walker's own
  classified movement (forward|reroute) or "". The view cannot widen it: the
  helper already raises if movement_candidate is not a MOVEMENT_LITERAL.
- The Route V2 view returns no top-level movement/target key (forbidden today),
  so there is nothing for the walker to read back as a decision.
- The attachment is advisory/non-binding and adopted_as_movement=False, so the
  walker control flow cannot branch on it.
```

If a future change ever made the walker branch on `route_v2_view_observations`, that
would be a new 6-phase requiring its own human gate. It is explicitly out of 6e.

## 5. How verification_gap remains non-reroute

```text
- Source seal: is_non_reroute_transition_concern_kind(verification_gap) = True
  (brick_protocol/agent/return_fact.py). Both paths import this same predicate.
- Walker path: _classify_reroute_target returns kind="non_reroute" for
  verification_gap with no reroute address; the walker WALKS ON, it does not
  reroute.
- Route V2 view path: render_route_v2_view marks
  sealed_concern_kind_observation.non_reroute=True and
  route_policy_eligibility_observation.match_state="non_reroute_concern_kind"
  with eligible=False, EVEN when a replay plan is supplied (proven in 6d 2.2:
  materialized=false, match_state=missing/disposition_required).
- 6e adds no path that converts verification_gap into a reroute. A negative
  probe (section 9) must prove verification_gap yields no reroute in BOTH paths.
```

## 6. How hold / paused / held_for_coo_review remain gate/lifecycle, not Movement

```text
- Movement literals are exactly forward | reroute (brick_protocol/link/movement.yaml,
  MOVEMENT_LITERALS). hold/paused/held_for_coo_review are NOT literals.
- Route V2 view: gate_state accepts these three lifecycle words and raises if a
  gate_state equals a Movement literal; movement_candidate raises if it is not a
  Movement literal. So the two fields cannot cross over.
- Walker: the existing hold/paused/fan-in-paused lifecycle injection
  (_inject_hold_paused_link / _step_result_with_paused_lifecycle) stays a
  lifecycle mutation, never a MovementFact. 6e does not route these words into
  movement_candidate.
- Negative probe (section 9): feeding a lifecycle word as movement_candidate must
  raise; feeding a Movement literal as gate_state must raise.
```

## 7. How delta-QA facts are carried (fake-landing defense)

```text
- The walker already carries the factual return; 6e forwards the four factual
  fields into the Route V2 view's delta_qa_fact input:
    made_changes, changed_files, diff_refs, evidence_refs
- render_route_v2_view normalizes them (bool + string-lists) and returns them
  under delta_qa_fact WITHOUT classifying success/quality/approval.
- These remain factual observations only. The walker must not derive
  success/quality/movement from them.
- Negative probe (section 9): delta_qa_fact carrying a forbidden key (e.g.
  success) must raise (existing _reject_forbidden_keys on delta_qa_fact).
```

Implementation note: these fields must be read from the closed AgentFact
`returned` body or from already-recorded support evidence that points to that
body. Missing optional fields are recorded as empty lists/false. Support must not
infer `made_changes=True` from a diff existing on disk, and must not synthesize
`diff_refs` or `evidence_refs` from git state without an evidence ref in the
Building record.

## 8. Hard boundaries preserved by 6e (unchanged constraints)

```text
Do NOT create: route_scope.py, route_v2_engine.py, new concern_kind.
Do NOT make verification_gap reroute-eligible.
Do NOT add success/quality/approved/good_enough/movement_choice/route_target
  authority fields as walker decision fields.
Do NOT give the walker scheduler/queue/retry runtime ownership.
Do NOT mutate: brick_protocol/agent/return_fact.py, brick_protocol/link/**,
  concern_kind vocabulary, AgentFact shape, Agent runtime_profile/adapter/model.
Do NOT let route_v2_view_observations feed the walker's gate_sequence/reroute control.
Do NOT silently load/default a route_policy mapping from support; route policy
  input must be caller/COO/Link-declared, otherwise record absent/blocked.
Do NOT add undeclared keys to reroute_adoption_record or hold_record; extend the
  recording contract/checker first if nesting is chosen.
Do NOT run a Building on the live checkout; use a declared worktree sandbox.
```

Candidate write scope for the FUTURE 6e implementation Building (after a separate
explicit approval), from the human-gate packet 5.2:

```text
- brick_protocol/support/operator/walker_kernel.py    (advisory attachment only)
- brick_protocol/support/operator/walker_resume.py    (read-back parity only)
- narrowly required checker/profile/fixture files
- brick_protocol/support/recording/contracts.py only if the chosen implementation
  nests Route V2 evidence inside reroute/hold records (not recommended)
- project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
- a follow-up dogfood / human-gate evidence note
```

Note on `walker_resume.py`: because resume reads back recorded evidence without
recompute, the advisory `route_v2_view_observations` must be recorded in the dynamic-walker
evidence snapshot and read back verbatim on replay. Resume must not recompute or mutate
the Route V2 view, and a resumed reroute/hold must mirror the recorded advisory exactly (parallel to the existing gate-decision read-back rule in
walker_kernel.py replay path).

## 9. Negative probes required BEFORE any 6e implementation lands

A 6e Building is not accepted by diff alone. It must prove, in a declared
sandbox, at least:

```text
P1. verification_gap: walker classification = non_reroute AND Route V2 view
    eligible=false, even with a replay plan supplied. No reroute occurs.
P2. hold|paused|held_for_coo_review supplied as movement_candidate -> raises.
P3. a Movement literal supplied as gate_state -> raises.
P4. delta_qa_fact / transition_concern / route_policy carrying a forbidden
    authority key (success/quality/movement/movement_choice/route_target) ->
    raises before view render.
P5. route replay plan authored by support/Agent/provider/session/tool/hook/
    credential/token author_ref -> raises (existing route_materialization seal).
P6. dynamic_walker_evidence.route_v2_view_observations is present as advisory
    (adopted_as_movement=false) and the walker's reroute/hold decision is
    byte-identical WITH and WITHOUT the attachment (proves non-binding /
    control-flow-inert behavior).
P7. resume replay reads back the recorded route_v2_view_observations verbatim
    and does not recompute them unless an explicit live-recompute gate is added;
    a resumed step's Movement matches the recorded one.
P8. route_policy input is declared/proven. If absent, the observation records
    route_policy_input_state=absent/blocked and no materialization view is
    produced; support must not silently load basic_qa_repair.yaml as a default.
P9. no new module (route_scope.py / route_v2_engine.py) and no new concern_kind
    appear; forbidden-surface scan is clean.
P10. reroute_adoption_record and hold_record field sets remain unchanged unless
     support/recording/contracts.py and its checker are intentionally updated.
```

## 10. Required proof commands for the 6e implementation Building

```text
python3 -m compileall -q brick_protocol
python3 brick_protocol/support/checkers/check_route_v2_views.py
python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_sealed_materialization
# plus the focused walker/route checker profile(s) that cover the new advisory attachment
# clean detached worktree:
python3 brick_protocol/support/checkers/check_profile.py --all
git diff --check
# GOAL/status update with remaining_delta and next gate.
```

Reason for the clean detached worktree: the live checkout contains many untracked
Building evidence dirs and inbox events
(`project/brick-protocol/buildings/**`, `status/inbox/**`,
`status/kernel/resume-declarations/**`) that must not be committed and can
pollute `--all`.

## 11. Three-axis attribution

```text
Brick evidence:
  6e is a walker-integration DESIGN work contract. The design keeps the walker's
  runtime one-step reroute contract intact and only adds read-only Route V2
  evidence next to the existing reroute-adoption/hold record. No engine, no new
  route scope.

Agent evidence:
  Input remains transition_concern_evidence inside the closed Agent return with a
  sealed concern_kind. No AgentFact field, Agent runtime_profile, or
  provider/model/adapter identity becomes a decision authority.

Link evidence:
  Link owns Movement (forward|reroute) and route replay facts. The walker's
  reroute classification stays the runtime authority path; the Route V2 view
  authors no Movement/target. hold/paused/held_for_coo_review stay lifecycle/gate
  states only.

Support surface:
  walker_kernel.py / walker_resume.py are support walkers over declared plans;
  route_v2_views.py / route_materialization.py are support evidence plumbing.
  None becomes source truth, success/quality judgment, Movement authority, a
  route target selector, or a scheduler/queue/retry owner.

Rejected shortcut:
  Do not treat this design note or the R2 dogfood green as permission to edit
  walker code now. Implementation requires a separate explicit human/Smith
  approval and a declared Building/worktree sandbox.
```

## 12. Disposition

```text
6e design state: design note produced (this file). Implementation still HOLD.
recommended integration shape: SHAPE A (read-only advisory overlay).
deferred: SHAPE B (shared-classifier consolidation) - future candidate only.
next gate: explicit Smith/human approval to open a declared 6e walker-integration
  Building with the write scope in section 8 and the negative probes in section 9.
```

## 13. Not proven

```text
- 6e walker integration runtime behavior is not proven (no walker code changed).
- SHAPE A vs SHAPE B final choice is a recommendation, not an executed decision.
- Automatic repair/replay execution remains not approved.
- Semantic correctness of future Agent concern evidence remains not proven.
- Whether the advisory attachment needs a new dedicated checker profile vs.
  extending an existing one is not yet decided; the 6e Building must decide and
  prove it.
- The exact declared route_policy input source for a live walker observation is
  not yet chosen; current walker code does not directly hold a loaded policy
  mapping.
- The persistent observation home is recommended as
  dynamic_walker_evidence.route_v2_view_observations; nesting inside reroute/hold
  records is not admitted without a recording-contract extension.
```

## 14. Movement language

This note authors no Link Movement. The next operational state is a human/Smith
gate state:

```text
gate_state: held_for_human_gate
movement_candidate: none supplied by this design note
```

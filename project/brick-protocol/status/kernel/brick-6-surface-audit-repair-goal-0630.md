# BRICK 6-Surface Audit Repair Goal - 2026-06-30

## Goal Symbol

```yaml
goal_ref: goal:brick-6-surface-audit-repair-0630
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
status: draft_for_smith_review_not_system_goal
objective: turn the 6-surface audit into a bounded Building repair programme without creating a new engine, hidden authority layer, or preset-only habit.
```

## Adopted Audit Packets

These packets are adopted as routing/audit support evidence, not as source truth or success judgment.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-s1-brick-axis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s2-agent-axis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s3-link-axis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s4-support-machine-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s5-checker-system-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-readiness-tuples-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-coverage-matrix-0630.md`

Support review evidence:

- `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-report-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-review-addenda-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-opinion-0630.md`

## Global Operating Rules

1. COO/operator tokens are for operation, judgment, graph declaration, Brick/Agent/Link attribution, HOLD/reroute candidate reasoning, and evidence synthesis.
2. Except for this goal/phase documentation, implementation must be done by declared Buildings through the official `build()` / `brick build` route.
3. Do not create `--large`, a second engine, a scheduler/queue/retry authority, or support-owned Movement/quality/success judgment.
4. Do not use a preset just because it is familiar. Pick the smallest graph that preserves Brick work, Agent performer, Link carry/gate/Movement, QA fan-in, repair routing, and evidence integrity.
5. Public operator/customer language is `build()` / `brick build`; internal/debug helper names are not customer route instructions.
6. If evidence conflicts, do not patch around it. Ask the Brick/Agent/Link questions named in the relevant phase document and HOLD if a required row is missing.
7. Every phase return must separate `observed_evidence`, `narrowly_proven`, `not_proven`, and `next Movement candidate`.
8. (0701 addition, REQUIRED) Graph packet admission MUST be checker-first, not
   discover-at-runtime. Before any `graph_packet` is accepted for a real
   `brick build --graph` run, a graph-topology checker must reject a packet
   where a `fan_in` group's `fan_in_target_ref` node is also the direct
   `source` of a `fan_out` group with no intervening single-target barrier
   node between them (fan-in and fan-out must never be the same event, per
   `agent/skills/building-coordination/SKILL.md`). This is not optional
   polish: P7a/P7b/P7d all burned a full real-provider Building cycle
   discovering this exact same shape defect only at closure time, after
   design+work+QA had already run. A schema/admission-time checker turns an
   expensive runtime discovery into a cheap pre-flight rejection, the same
   checker-first discipline already required for every other invariant in
   this goal. Scope this as part of P8 (or a dedicated small Building before
   P8 if P7 closes first); do not let it slip.

   **Resolution (0701, PARTIAL, explicit COO disposition): the DETECTOR half
   is closed** -- `graph_topology_fan_barrier` (task #5,
   `brick-6-graph-topology-fan-barrier-checker-closure-0701.md`) rejects the
   named shape via `check_profile.py --all` / focused-profile runs, using
   real P7d/P7d2/P7d3 fixtures. **The ADMISSION-GATE half is NOT closed**: the
   checker is not wired into the live `brick build --graph` materialization
   path (`composition_compose.py` / `driver.py` / `plan_validation.py`), so a
   malformed packet can still be fired through the real CLI and is only
   caught if the COO runs the checker sweep first -- a discipline-dependent
   habit, not an automatic gate. Both the task #5 closure and the task #8
   closure (`brick-6-graph-write-scope-default-closure-0701.md`) already
   recorded this as `not_proven` and recommended folding it into a follow-on;
   this paragraph is the explicit Smith/COO disposition the Completion
   Definition requires: **defer the admission-gate wiring to the Follow-On
   Goal bucket below (do not block P0-P9 goal completion on it), tracked as
   the fourth Follow-On item.** See `brick-6-three-report-crosscheck-0701.md`
   for the full cross-check that surfaced this gap explicitly.
9. (0701 addition) There are currently TWO plan-materialization producers:
   `support/operator/composition_compose.py::compose_building()` (old,
   actually reachable from the live `brick build --graph` CLI route today)
   and `support/operator/assembly.py::assemble()` (intended future
   canonical producer per `support/checkers/check_assembly_equivalence.py`'s
   own docstring: "Guard structural equivalence for future assembly.py
   lowering"). This is a standing violation of rule 3's no-second-engine
   principle, tolerated only because the equivalence guard proves the two
   are not yet interchangeable. Smith: address this before/within P8, not
   as a side effect of any narrower engine fix (e.g. not folded into the
   0701 write_scope-default fix). Before attempting the cutover: (a) verify
   `assemble()` supports every graph_packet feature the live `--graph` CLI
   route currently exercises (fan_in/fan_out groups, `sibling_independence`,
   `closure_transition_target_policy`, the graph-topology fan-barrier
   checker from rule 8, etc. -- `composition_compose.py` kept receiving
   real feature work through 0701, so parity is not proven); (b) decide
   whether the outcome is completing the migration (CLI route switches to
   `assemble()`, `compose_building` retired) or explicitly declaring
   `compose_building` permanently canonical and retiring the "future
   lowering" framing on the equivalence checker -- either resolution is
   acceptable, indefinite duplication is not.

   **Resolution (0701, Building design + 35-agent independent workflow, both
   converged): `compose_building()` stays the ENGINE, permanently canonical
   -- see `brick-6-dual-producer-reconciliation-synthesis-0701.md`. This is
   settled and does not change with rule 10 below.**

10. (0701 addition, Smith decision) This is a SEPARATE axis from rule 9: not
    "which engine" (settled, rule 9) but "which AUTHORING/LAUNCH interface is
    official." Smith's call: the `assemble()`/`build()`/`fan()` Python DSL
    (`support/operator/assembly.py`) + `run_building_plan()` becomes the
    official way to construct and launch a Building; hand-authored
    `graph_packet` JSON via the `brick build --graph <file>` CLI flag is
    discarded. Reasoning: today's repeated operational friction (museum-cwd
    launch mistakes, forgotten `--overwrite-existing`, verbose ~150-line
    hand-JSON with 7+ manual wiring conventions to get right, at least two
    confirmed silent-omission gaps -- `write_scope` pre-0701/task-#8 and
    `source_facts` still open -- that only exist because raw JSON has no
    validation for them) traces overwhelmingly to hand-authoring raw JSON,
    not to the engine underneath. The DSL auto-derives node/edge/group
    wiring and was empirically verified byte-identical to hand-JSON for
    every case it currently supports (same `plan_shape`, same
    `execution_order`, same `edge_ref`s).

    **Known blockers before `--graph` can be FULLY discarded** (two now
    confirmed, both found live while constructing the P9 proof-run graph,
    0701):
    1. `sibling_independence` (the mechanism that closed the P7d3 fan-in
    cohort blind spot) is NOT yet expressible via the DSL --
    `GroupSpec` (assembly.py) has only `role`/`members` fields, zero
    references to `sibling_independence` anywhere in assembly.py.
    2. **Per-node `write_scope` narrowing is not expressible via `brick()`
    at all** -- `write_scope` is in `brick/spec.py`'s
    `_FORBIDDEN_BRICK_KWARGS`, confirmed live: `brick("work", ..., write_scope=...)`
    raises `TypeError: brick() derives these fields; do not declare them:
    write_scope`. `write_scope` is always derived (task #8's worktree-minus-
    `.git` default, unconditionally) with no DSL-level override to a
    narrower explicit path. A `graph_packet` via `--graph` CAN declare an
    explicit narrower `write_scope` per node (this is how every P0-P8
    Building this session that needed a narrow write lane did it before
    task #8's default even existed). Until the DSL gains an explicit
    per-node write_scope kwarg, `--graph` remains the only way to declare a
    narrower-than-worktree write lane.
    Until the DSL is extended to support both, `--graph` must remain
    available as a low-level escape hatch for these two cases -- not fully
    removable yet.
    **Scope of "discard" (Smith 0701, deferred): NOT decided now.** Whether
    this ends up recommend-DSL-only (docs/skills point to `assemble()`,
    `--graph` stays wired but de-emphasized) or literal CLI flag removal
    from `cli.py`/`driver.py` is a decision for LATER -- after one real
    deployment cycle, bundled into the broader architecture cleanup pass
    together with the god-module/checker-cleanup follow-on goal (see
    "Follow-On Goal" section near the end of this document). Do not attempt
    this execution now; this rule records the DIRECTION decision only
    (assemble() is official, `--graph` is headed for retirement), not an
    authorization to execute the removal in this goal cycle.

    **Operational note**: a Building already in flight when this decision
    landed (`brick-6-dual-producer-impl-0701a`) has a work lane (Lane B)
    whose task instructions still encode the OLD framing ("`--graph` is the
    customer route, `assemble()` is operator-only"). That lane's output
    must NOT be adopted as-is -- reject/redo it with the corrected framing
    above; Lanes A and C are unaffected by this rule and may still be
    adopted normally.

## Standard Phase Building Graph (dual-design fan-out, Smith-confirmed 0701)

This is the DEFAULT operating shape for high-risk phase Buildings. It is a
declared-graph thinking template for `build()` / `brick build`, not a preset and
not a new engine. It persists here so that even after context compaction the COO
can reload the intended shape from this document.

```text
0. task-source / phase contract
   - COO drafts task.md from the phase doc + adopted audit refs. No implementation here.
1. design-fanout (independent siblings, byte-distinct evidence)
   1a. Codex design  -> code surface, checker-first feasibility, write_scope, file/test boundaries
   1b. Claude design -> architecture, Brick/Agent/Link boundaries, product/customer comprehension,
                        failure scenarios, anti-bandaid risk
2. design-fanin-synthesis
   - merge both designs: conflicts / common ground / gaps / phase questions / not_proven. No dev yet.
3. design-QA (planning review)
   - only asks "is this design safe to send to build()?": Brick evidence sufficient?
     Agent lane/write_scope correct? Link Movement/target not stolen by support?
     do checkers actually cover the requirement? no new raw/secret/provider/dashboard/release risk?
4. COO planning gate (operator judgment, doc-edit only)
   - COO reads synthesis + design-QA, edits phase doc / task contract, leaves open items as
     phase questions (no bandaid), then releases to development or HOLDs.
5. development / work
   - performer lane implements (usually Codex worker); Claude stays on design/QA/axis-attack, not impl.
6. verification fan-out (hard fan-in QA cohort)
   6a. code-attack-QA  6b. axis-attack-QA  6c. evidence-integrity
   6d. optional product/customer-comprehension QA
7. closure-synthesis
   - collect ALL QA bodies first; only closure emits Link-facing transition_concern_evidence.
8. COO forward / reroute judgment on current evidence.
```

Graph rules that must hold:

- Claude/Codex designs are support evidence only; agreement between them is not source truth,
  success, quality, or Movement authority. The contract closes on phase doc + task.md +
  declared Building graph + evidence root.
- Tiering: apply dual-design fan-out to high-risk phases (P1, P2, P3, P5, P7, P8). Low-risk /
  doc / cleanup phases (P0, simple status, simple notes) may use COO direct doc + single review.
- Fan-out siblings hold independent byte-distinct evidence; a copied sibling body is a cross-vouch leak.
- QA lanes do not choose Movement. In hard fan-in, QA lanes do not emit Link-facing
  transition_concern_evidence; closure-synthesis alone does.
- If development fails, default is full work + QA replay, not partial QA reuse, until a later
  freshness / Work Packet Building admits reuse.
- No ai-cli / ai-cli-backed helper / subagent route for diagnosis; dual-design runs as declared
  Building lanes through the official route only.
- Do not interrupt an in-flight official build to swap in this shape; apply it to the NEXT
  phase / reroute / retry graph.

## Phase Structure Revision (Smith/Codex review 0701)

The original draft bundled too much into P7, which risked skipping verification-
surface honesty on the internal dogfood path (P0..P6,P8). This revision splits the
tail into P0..P9 so verification honesty is closed BEFORE the product/ship phases,
and folds the review feedback into the named phases below. Phase doc files keep
their current filenames; the phase NUMBER and scope below are authoritative when a
filename's embedded number lags this mapping.

## Per-Phase Common Template (mandatory)

Every phase Building and every phase status doc MUST carry these, so scope never
blurs:

```text
invariant                         the single property this phase must make true
Brick / Agent / Link attribution  which axis owns the change; support stays support
write_scope                       allowed_paths / forbidden_paths for the work Brick
checker-first negative probe      a probe that REDs before the fix, GREENs after
focused checker / profile         the targeted profile run for this phase
check_profile.py --all            full-profile result recorded as support evidence
evidence_root                     the Building evidence root path
changed_files / diff              exact files and diff stat from the work step
observed_evidence / narrowly_proven / not_proven / next Movement candidate
QA discipline                     QA/Inspector lanes: probe_write only, NO source mutation
```

Support/checker green, Slack/reporter, and model output remain support evidence
only; none of them is source truth, success, quality, or Movement authority.

## Failure Attribution Taxonomy (shared)

When a phase Building does not close, attribute the failure with this closed
vocabulary instead of a generic "failed":

```text
task_definition_gap
missing_source_evidence
brick_contract_gap
agent_return_shape_gap
provider_runtime_failure
link_gate_insufficient
human_disposition_required
write_scope_mismatch
checker_limit
dashboard_projection_stale
```

## Symbolic Phase Documents (P0..P9)

- `phase:P0` -> `...-p0-audit-adoption-baseline-0630.md` — Audit adoption and baseline.
- `phase:P1` -> `...-p1-raw-evidence-stream-scrub-0630.md` — Raw evidence stream secret/PII/provider-session scrub.
- `phase:P2` -> `...-p2-resume-post-hold-isolation-0630.md` — Resume/post-HOLD isolation, explicit disposition, AND sensitive-path write commit block/mark (moved up from ship-safety because the readiness tuples put it on the protocol-live path, not only on public ship).
- `phase:P3` -> `...-p3-brick-return-shape-link-carry-0630.md` — Brick return-shape truth and Link carry filtering.
- `phase:P4` -> `...-p4-agentfact-pre-persistence-closure-0630.md` — AgentFact pre-persistence closure.
- `phase:P5` -> `...-p5-link-declaration-concern-safety-0630.md` — Link declaration law and invalid concern target safety.
- `phase:P6` -> `...-p6-verification-surface-honesty-0701.md` — NEW. Verification surface honesty: pytest/test surface honesty, checker reentrancy, no false-green, focused-vs-`--all` parity, profile-count drift. Closed BEFORE product/ship because honest verification is needed for the internal dogfood path, not only at release.
- `phase:P7` -> `...-p6-product-route-p3-easy-surface-0630.md` — Product route and Easy Building surface (was P6).
- `phase:P8` -> `...-p7-ship-safety-release-dashboard-provider-0630.md` — Ship-safety: release/dashboard/provider/CI/supply-chain (was P7).
- `phase:P9` -> `...-p8-final-dynamic-proof-customer-replay-0630.md` — Final dynamic proof and customer-ready replay (was P8).

(Filenames are historical; the P0..P9 numbers and scopes in this list win. A later
doc-rename Building may align filenames; do not block phase work on the rename.)

## Phase Scope Additions (from 0701 review)

### P2 add
- sensitive-path write commit block/mark: a write Brick must not silently commit
  secret/credential/PII/provider-session-bearing paths; block or mark them.
- invariant: resume/post-HOLD isolation holds AND no sensitive-path write reaches a
  durable commit unblocked/unmarked.

### P6 (new — Verification surface honesty)
- pytest/test surface honesty: tests/checkers must not pass by skipping, stubbing
  away the asserted behavior, or reading a stale archive instead of the worktree.
- checker reentrancy: a focused profile and `--all` must agree; no false-green from
  tempdir/archive divergence.
- profile-count / setup.md style stale-doc drift recorded and fixed.

### P7 (Product route / Easy Building) add
- Named product observations: `readiness_blocker_observation`,
  `protocol_compliance_observation`, plus the shared failure attribution taxonomy.
- CLI raw `str(exc)` exposure cleanup (no raw traceback/exception leakage to the
  operator surface).
- bare `brick` default behavior product decision: status vs help.
- stale profile-count / setup docs cleanup at the product surface.
- Easy Building big-work shape MUST be declared as the route (so work never escapes
  into a `--large`/hardcoded path):

```text
make X
-> task intake
-> design (Codex + Claude fan-out)
-> design QA / axis QA
-> closure plan-confirm
-> parallel dev lanes
-> lane QA
-> fan-in
-> Codex QA + axis QA
-> closure
```

### P8 (Ship safety) add — full deployment surface, not just dashboard ingest
- dashboard container/viewer access wall.
- dependency lock / release reproducibility.
- installer supply-chain / pinned `uv` policy.
- GitHub Actions: not just "add CI" but branch protection / required-gate verified.
- Slack/reporting reliability: if delivery is not proven, docs must NOT claim it as
  delivery proof.

### P9 (Final dynamic proof) add — stub vs real provider split
- stubbed proof closes the protocol path ONLY.
- real-provider / fresh-machine customer-ready claim remains `not_proven` unless a
  separate real-provider run is performed and recorded.

## Preferred Priority

For current BRICK dogfood/internal correctness, use protocol-live order:

```text
P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> P8 -> P9
```

The internal dogfood path MUST include P6 (verification honesty) before P7/P8/P9;
it may NOT skip verification honesty on the way to the dynamic proof. If public
release/customer install is imminent, P8 (ship-safety) may be pulled earlier, then
return to protocol-live order.

## Completion Definition

- P0 audit adoption is committed or explicitly parked.
- P1-P8 named repair requirements are closed by current evidence or explicitly
  deferred with Smith/COO disposition (each using the per-phase common template).
- P6 verification-surface honesty is closed on the internal path, not deferred to
  ship-time.
- P9 current-main dynamic proof closes through the official `build()` / `brick build`
  route with frontier/evidence/artifact proof; the stub/real-provider split above is
  recorded.
- `check_profile.py --all` is green at final close (support evidence).
- Repo state at final close: repair branch / main is clean, pushed or explicitly
  parked, and `git status` / `HEAD` / upstream delta are recorded. (This replaces the
  ambiguous `main = origin/main`, since P0 audit commits can legitimately put local
  main ahead of origin.)
- Customer comprehension and real-provider/fresh-machine readiness are externally
  validated or explicitly left `not_proven` / `waived`.
- (0701 addition) Global Operating Rules 8 and 9 — and any future rule added
  with a REQUIRED marker — are resolved or explicitly deferred with
  Smith/COO disposition, using the same per-phase common template as P0-P9.
  These rules are engine-level findings scoped "before/within P8" in their
  own text, not phase items, so without this bullet a phase-only completion
  sweep (checking only P0-P9) could silently skip them.

## Not Proven At Goal Start

- Customer-ready broad claim.
- Public ship readiness.
- Fresh-machine install/provider reliability.
- Dashboard/network exploit behavior.
- Complete dynamic resume/fan-out/fan-in behavior beyond current evidence.
- Real-provider dynamic proof (stub proof does not establish it).

## Follow-On Goal (explicitly NOT part of this goal, Smith 0701)

God-module decomposition (`kernel_checks.py` 10201 LOC, `case_runners.py`
8507 LOC, `check_bounded_agent_proposed_routing_loop0.py` 7087 LOC,
never-inspected) and checker/profile cleanup (checker-diet completion, CI
gate, non-reentrant fixture isolation) is real, confirmed-still-needed work
-- see `godmodule-checker-cleanup-synthesis-0701.md` (17-agent workflow,
0701, 8 sources cross-checked against fresh measurements) for the full
scope. Smith's explicit disposition: keep this separate from P0-P9, do not
fold it in, and start it only after this goal's P9 closes -- it sits at the
tail end of this goal's lifecycle, as the natural next goal, not a phase
inside this one.

**Second item in this same follow-on bucket (0701, Smith decision, see rule
10 above)**: execute the `--graph` CLI-flag retirement / full cutover to the
`assemble()` DSL as the sole official launch interface. Direction is
decided (rule 10); execution scope (recommend-only vs literal code removal)
and timing are explicitly deferred by Smith: "우선 두자... 이거 배포 한번하고
아키텍처 정리 할 때 정리하자" (park it for now; clean this up after one
deployment cycle, during the architecture cleanup pass). Do not execute
before then. Blocked on: extending the DSL to support `sibling_independence`
(currently inexpressible -- `GroupSpec` has only `role`/`members` fields)
before `--graph` can be fully removed rather than merely de-emphasized.

**Third item in this same follow-on bucket (0701, Smith decision)**: full
documentation consolidation, not just code/checker cleanup. Evidence this is
a real, comparably-sized problem (not just a code issue): (a) this session
alone created 20+ new `project/brick-protocol/status/kernel/*.md` files
(finding/closure/synthesis/disposition docs); (b) the COO's own memory
index needed emergency compaction today (29KB -> 17.5KB); (c) BRICK already
went through one prior large consolidation pass (see
`productization-team-dogfood-handoff-0606.md`: checkers 47->13, docs
890->286) -- growth-then-consolidate appears to be BRICK's actual operating
cycle, not a one-time event. Smith: "반영하자. 이번에 끝장보자. 리팩토링까지"
(do it properly this time, including the refactor) -- this follow-on pass
should be thorough (code decomposition + checker-diet + doc consolidation
together), not a partial pass, when it starts after P9 closes.

**Fourth item in this same follow-on bucket (0701, three-report cross-check,
Smith: "지금 저거 포함해서 다음페이즈 정리해두자")**: a full empirical
cross-check of the GPT-Pro, Codex, and Claude-workflow architecture audit
reports against current (post-P0-P9-repair) state -- see
`brick-6-three-report-crosscheck-0701.md` for the complete evidence. All
top-priority items from all three reports are confirmed closed by P0-P9.
Confirmed gaps to carry into this follow-on, ranked:

1. Rule 8 admission-gate wiring (see the Rule 8 resolution paragraph above --
   this is the one item with goal-document-level disposition; the rest below
   are informational carry-forward, not goal-blocking).
2. `support/operator/walker_carry.py` (Link carry runtime) was never
   inspected or given a dedicated checker, despite P3 being scoped as
   "Brick return-shape truth AND Link carry filtering."
3. `brick/work.py`'s return-shape parser was never directly probed (P3 added
   materializer-level equivalence checking only).
4. `agent/skills/make-an-agent/SKILL.md` still teaches the stale
   `observed-write`/`reviewer-readonly` taxonomy instead of the current
   `read/probe_write/source_write` vocabulary.
5. Dashboard `participants` map (`support/dashboard/server/index.mjs:21`) has
   no TTL/pruning and grows unbounded (P8 Lane 3 cleaned up `clients` but not
   `participants`).
6. Native child-dispatch recording (`support/operator/native_dispatch.py`)
   exists and is wired via skill hooks, but live-activation proof remains
   unresolved; P8 did not touch it.
7. Dashboard frontend/UI concerns (Movement/historical-alias label confusion,
   client-side delta-ordering) -- P8 Lane 3 hardened server-side ingest only.
8. Provider write-boundary was disclosed (P8 Lane 5) but not asymmetrically
   hardened -- GPT-Pro asked for Claude/Gemini write to default to
   worktree-only, stricter than Codex; all providers currently carry the
   same write_boundary condition.
9. Agent adapter catalog physical-location debt (move to Agent axis) and
   install.sh pinned-installer option -- neither touched by any P-phase.

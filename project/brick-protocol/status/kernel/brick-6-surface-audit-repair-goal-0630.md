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

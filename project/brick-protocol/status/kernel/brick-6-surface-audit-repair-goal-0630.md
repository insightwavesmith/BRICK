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

## Symbolic Phase Documents

- `phase:P0` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p0-audit-adoption-baseline-0630.md` (Audit adoption and baseline)
- `phase:P1` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p1-raw-evidence-stream-scrub-0630.md` (Raw evidence stream secret/PII scrub)
- `phase:P2` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p2-resume-post-hold-isolation-0630.md` (Resume/post-HOLD isolation and explicit disposition)
- `phase:P3` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p3-brick-return-shape-link-carry-0630.md` (Brick return-shape truth and Link carry filtering)
- `phase:P4` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p4-agentfact-pre-persistence-closure-0630.md` (AgentFact pre-persistence closure)
- `phase:P5` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p5-link-declaration-concern-safety-0630.md` (Link declaration law and invalid concern target safety)
- `phase:P6` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p6-product-route-p3-easy-surface-0630.md` (Product route and P3 Easy Building surface)
- `phase:P7` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p7-ship-safety-release-dashboard-provider-0630.md` (Ship-safety release/dashboard/provider hardening)
- `phase:P8` -> `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-p8-final-dynamic-proof-customer-replay-0630.md` (Final dynamic proof and customer-ready replay)

## Preferred Priority

For current BRICK dogfood/internal correctness, use protocol-live order:

```text
P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> P8
```

If public release/customer install is imminent, move `phase:P7` before P1 and then return to protocol-live order.

## Completion Definition

- P0 audit adoption is committed or explicitly parked.
- P1-P7 named repair requirements are closed by current evidence or explicitly deferred with Smith/COO disposition.
- P8 current-main dynamic proof closes through official `build()` route with frontier/evidence/artifact proof.
- `check_profile.py --all` is green at final close.
- `main = origin/main` after Smith-approved push.
- Customer comprehension is externally validated or explicitly left `not_proven/waived`.

## Not Proven At Goal Start

- Customer-ready broad claim.
- Public ship readiness.
- Fresh-machine install/provider reliability.
- Dashboard/network exploit behavior.
- Complete dynamic resume/fan-out/fan-in behavior beyond current evidence.

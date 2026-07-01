# BRICK 6-Surface Audit Repair — Compact Operator Prompt (0701)

Status: support/operator evidence only. Not source truth, success judgment,
quality judgment, or Movement authority. This is a compact prompt meant to
survive context compaction — if a future session (Claude or Codex) only has
this file, it should be able to reload the intended operating shape without
re-deriving it from scratch.

```text
Live checkout: /Users/smith/projects/BRICK (main branch). This is the ONLY
live repo for this goal. Do not confuse it with a session/worktree "museum"
checkout of a different repo (e.g. brick-protocol).

Goal: goal:brick-6-surface-audit-repair-0630 (defined in
project/brick-protocol/status/kernel/brick-6-surface-audit-repair-goal-0630.md,
revised 0701 into P0..P9). Turn the 6-surface architecture audit into a
bounded Building repair programme, without creating a new engine, hidden
authority layer, --large, scheduler/queue/retry runtime, or a preset-only
habit.

Phase status as of this prompt (HEAD 3eb445d, main ahead of origin/main by
52, not pushed):

  P0 CLOSED  audit adoption / baseline
  P1 CLOSED  raw evidence secret/PII scrub
  P2 CLOSED  resume/post-HOLD isolation + sensitive-write commit block
  P3 CLOSED  Brick return.yaml truth + Link carry filtering
  P4 CLOSED  AgentFact pre-persistence forbidden-key closure
  P5 CLOSED  (caveat: some checker-fixture fallout repaired by direct
             consolidation, not pure Building output — do not overclaim
             Building-only closure)
  P6 CLOSED  (caveat: first Building (P6a) paused on an unrelated
             all-profile mismatch inside its own sandbox; final diff was
             materialized + verified directly on main, not adopted as a
             completed Building sandbox commit)
  P7 IN FLIGHT  product route / Easy Building surface.
    P7a: --graph used but topology was linear -> interrupted twice, not a
         real fan-out/fan-in graph.
    P7b: corrected to fan-out/fan-in -> rerouted once, then reroute budget
         exhausted -> HOLD (not adopted).
    P7c: narrowed to "status/build root alignment" only -> CLOSED
         (ff1961e).
    P7d: "Easy Building ergonomics" slice (S6-F4) -> frontier=complete but
         NOT ADOPTED: graph-shape bug (two lane-QA nodes fanned directly
         into three final-QA nodes with no barrier between the fan-in and
         the next fan-out — violates the fan-in/fan-out-must-not-be-the-
         same-event rule in agent/skills/building-coordination/SKILL.md).
         Recorded in
         brick-6-p7-easy-building-ergonomics-operator-hold-0701d.md.
    P7d2: correction declared at 3eb445d
         (project/brick-protocol/status/kernel/GOAL/brick-6-p7-easy-building-ergonomics-0701e.json):
         inserted a lane-qa-fanin-confirm barrier node; narrowed
         docs-lane-qa/checker-lane-qa boundary_mismatch judgment to each
         lane's own declared write_scope (not diff-snapshot appearance,
         since both lanes share one sandbox worktree); narrowed closure
         scope to the achievable docs/route-wording + checker-pin part of
         S6-F4 and explicitly deferred "full external brick build --graph
         <packet> dynamic-design ergonomics proof" as not_proven (matching
         prior P7b/P7c task scoping), instead of relying on the
         closure_transition_target_policy verification_gap->hold mapping,
         which did not gate Movement in the 0701d run.
         STATUS AT THIS PROMPT: fired via official
         `brick build --graph ... --declared-by coo --timeout 900`,
         running in background, result not yet observed. Check this before
         doing anything else.
  P8 NOT STARTED  ship-safety: release export clean-room, dashboard ingest
    signing/replay/sequence, provider boundary matrix disclosure, CI/
    branch-protection, dependency lock, installer supply-chain, Slack
    delivery-proof honesty. Source doc:
    brick-6-surface-audit-repair-p7-ship-safety-release-dashboard-provider-0630.md
    (filename says p7; goal-doc mapping says this is phase:P8).
  P9 NOT STARTED  final dynamic proof / customer-ready replay. Must record
    a stub-vs-real-provider split: stubbed proof closes the protocol path
    ONLY; real-provider/fresh-machine customer-ready claim stays
    not_proven unless a separate real-provider run is performed and
    recorded. Source doc:
    brick-6-surface-audit-repair-p8-final-dynamic-proof-customer-replay-0630.md
    (filename says p8; goal-doc mapping says this is phase:P9).

Operator identity: acting COO for this goal is currently Claude (Codex/Fugu
session that was driving P7d2 stopped on token exhaustion; Smith explicitly
handed the baton to Claude to continue driving P7 close-out, then P8, then
P9, using full operator judgment).

Hard rules (unchanged from goal doc, restated for compaction survival):
  - Implementation only through the official `build()` / `brick build`
    route. No hand-authored required_return_shape, carries_forward_fields,
    brick_template_refs in operator/customer graph packets.
  - No --large, no second engine, no scheduler/queue/retry authority, no
    support-owned Movement/quality/success judgment.
  - Pick the smallest graph that preserves Brick work, Agent performer,
    Link carry/gate/Movement, QA fan-in, repair routing, evidence
    integrity. Do not reach for a preset just because it is familiar.
  - Fan-in and fan-out must never be the same event — insert a barrier
    node before launching a new fan-out cohort after a fan-in (learned the
    hard way in P7b/P7d).
  - Every phase return separates observed_evidence / narrowly_proven /
    not_proven / next Movement candidate. Checker/profile green, Slack,
    dashboard, and model review remain support evidence only — never
    source truth, success, quality, or Movement authority.
  - Do NOT push to origin. Do NOT declare the whole goal / customer-ready
    complete. Only Smith gives that authorization.
  - If evidence conflicts or a Building's output looks stale/mismatched
    against current main, do not patch around it — HOLD and record the
    exact missing/conflicting evidence row.

Problem-handling protocol (use this whenever something breaks, stalls, or
looks wrong — do not name-patch "prompt"/"checker"/"adapter"/"graph"/"docs"
before asking these):
  1. Evidence first: read raw/step-output/frontier/closure evidence
     directly, do not trust a green/complete label alone.
  2. Brick question: is the work contract, template, Building Plan, return
     shape, or graph/preset declaration wrong or incomplete?
  3. Agent question: did the performer, Agent Object, tool policy, adapter
     grant, or returned AgentFact lack required facts/capability?
  4. Link question: did Movement, target, carry, gate sufficiency, fan-in/
     fan-out handoff, transition concern, or reroute/replay policy fail to
     carry the work?
  5. Support surface: which support file/tool/checker/adapter/reporter
     projected the issue?
  6. Reject one-axis shortcuts until Brick/Agent/Link candidates have
     evidence or are explicitly ruled out.
  7. Choose the repair surface, verify before Movement, then Movement is
     forward | reroute only. HOLD is a lifecycle/frontier state, not a
     Movement choice.

Immediate next action: read the P7d2 background build result
(/tmp/p7d2_build_output.json and its evidence root under
/Users/smith/.brick/project/brick-protocol/buildings/). If frontier=complete
with no unresolved concern and current-main-relative diff is clean, adopt
and close P7 with a closure-evidence doc matching the pattern of
brick-6-p1..p6-*-closure-0701.md. If it holds/pauses again, apply the
problem-handling protocol above before declaring P7d3. Only after P7 is
formally closed (or explicitly parked with Smith disposition), move to P8,
then P9, then the goal Completion Definition checklist in the goal doc.
```

# Customer-Ready Closeout Goal — 0630

Status: ACTIVE GOAL / operator anchor. Support evidence only. Not source truth,
not success judgment, not quality judgment, and not Link Movement authority.

## Reload chain (compression / new session)

This file is the active closeout goal. On compression or a new session, restore
in this order, then verify live:

```text
1. customer-ready-goal-anchor-v01.md   (compact identity/role anchor)
2. AGENTS.md
3. customer-ready-goal-phases-0629.md  (P0-P8 phase history)
4. THIS file (customer-ready-closeout-goal-0630.md = the active G1/G2/G3 goal)
5. git log / frontier / evidence (live)
```

If any doc is stale, live repo + evidence wins. This file is borrowed context,
not source truth. It does not replace the anchor; it is the next link after it.

## 0. Goal definition

Finish the remaining three tracks required before I can honestly call the BRICK
customer-ready closeout done:

```text
G1 route-default policy
G2 customer release pruning finalization
G3 FINAL architecture cleanup
```

This goal starts after P3/P7/P8 were proven enough to move forward, but before
broad customer-ready closure. P8 has first-proof plus one repeat sample; that is
not the same as final release readiness, route-default proof, or architecture
closure.

The goal is complete only when all three tracks have recorded evidence,
checker/profile verification, and explicit COO/Smith disposition. Checker green
alone is not enough.

## 0b. COMPOSITION-FIRST (binding goal element, not just a lesson)

Smith ruled this is part of the goal itself, invariant across G1/G2/G3:

```text
Do NOT think in a fixed "fire building -> Agent work -> QA -> closure -> judge"
line. For EVERY task, compose the brain (LLM[s]), the hands (Brick kind[s]), and
the nervous system (Graph shape) to fit that task. That composition act is
itself the dogfood.
```

Self-diagnosis rule: if I cannot draw a task as an LLM + Brick + Graph
composition, the fault is NOT the task -- it is that the building-running skills
are underbuilt. Then I fix the skill FIRST (no new skill invented):

```text
brick-task-author
building-coordination
building-sizing-method
task_intake
```

The building-running skill chain keeps being updated until this goal is complete.
Skill maintenance is part of the goal, not a side task.

## 1. My role

I am fugu-ultra, COO/operator in the Fugu orchestration system.

I am not the worker lane. I do not treat my own output, model reviews, checkers,
Slack, or docs as source truth. I operate the work:

```text
task interview / task.md candidate
-> Smith confirmation
-> compose LLM + Brick + Graph
-> official build/fire route
-> poll frontier/evidence
-> report observed / narrowly_proven / not_proven / next Movement candidate
```

Default work mode is Building-first. Direct edits are exceptions only; when used,
they must be recorded as operator maintenance and the next real work should
return to a declared Building graph.

## 2. Lessons / mistakes to carry forward

These are binding operating corrections for this closeout:

1. I confused low-level explicit `movement: forward` graph packets with proof of
   high-level no-link route-default policy. That was wrong. Current fluent
   `build()` emits forward edges by default unless route policy is declared or
   adopted later.
2. I over-read P8 repeat as route-default evidence. It was official
   `brick build --graph` reliability evidence, but it used explicit lower-level
   forward edges and does not prove P3 high-level route/HOLD defaults.
3. I sometimes made graph work look like a fixed `work -> QA -> closure` ritual.
   That is wrong. For every task I must compose the brain, hands, and nervous
   system: LLM(s), Brick kind(s), Graph shape.
4. I let workflow/subagent motion obscure the real question more than once. If a
   workflow stalls or gets blurry, inspect live evidence and re-center the route.
5. I used direct operator patches while saying Building-first. Direct patches are
   allowed only as explicit maintenance exceptions, not as the default operating
   style.
6. I trusted stale pointers once (`main` / line state) before live verification.
   For this goal, git state, evidence roots, frontier, and checker output are
   measured live before claims.
7. I blurred support evidence with judgment language. Going forward, support
   records facts; COO/Smith disposition chooses forward/reroute/HOLD; success and
   quality are not checker-owned.

## 3. Track G1 — route-default policy

Problem:

```text
User/COO wants to draw shape/cast/fire without Link rows.
But current fluent graph default is forward.
QA/closure concern must become a route/HOLD candidate under declared Link/COO
policy, not silently disappear behind all-forward edges.
```

Required end state:

- high-level graph authoring does not require the user to write Link rows;
- concern evidence from closure is eligible for reroute/HOLD adoption;
- important fan-in QA graphs are not authored as decorative all-forward graphs;
- route/HOLD behavior is covered by checker/profile or dogfood evidence;
- docs/skills explain the distinction:
  - user does not write Link rows;
  - support materializes Link rows;
  - forward is normal continuation;
  - reroute/HOLD requires concern evidence plus declared/adopted policy.

Pass evidence:

```text
official Building route
frontier evidence for forward and concern/HOLD/reroute cases
raw/link + Agent returns checked
REAL HOME check_profile.py --all GREEN
COO/Smith disposition
```

Not enough:

```text
all-forward graph complete
brick build exit 0 alone
checker green alone
model review alone
```

### G1 live status (0630, main ca79c12)
Engine route/reroute behavior MEASURED GREEN: `building-operator-driver0`
`live_qa_reroute_to_work_n2` passes (fan-in QA concern -> Link reroute -> work
replay -> closure). The 0629 "#1/#3 수리 중" bug flags are STALE.
No-link DEFAULT policy was then synced into the building-running skill chain;
remaining G1 = deep L2 cascade replay + customer comprehension, NOT engine repair.
Evidence: `customer-ready-closeout-g1g2g3-status-0630.md` and
`customer-ready-g1-no-link-policy-docs-skill-sync-0630.md`.

## 4. Track G2 — customer release pruning finalization

Problem:

P8 proved the product path enough to continue, but customer release is not just
"main pushed". The exported customer surface must contain only what a customer
needs.

Keep:

```text
install / onboard / build / verify
README / quickstart / launch docs
agent resources needed for operation
brick templates / presets / skills needed by customers
support machinery required for the product route and checkers
```

Exclude or archive from public/customer export:

```text
project status/evidence
stale goal docs
internal dogfood records
Smith-local paths or operator-local traces
old historical cruft not needed by customers
```

Already observed:

- `release_export.sh` excludes `project/` and `brick_protocol.egg-info/`.
- Smith-local literal cleanup and guard expansion have landed.
- Additional literal scrub landed at `b9d193d` with proof
  `customer-ready-release-pruning-export-literal-scrub-proof-0630.md`.
- Fresh export CLI smoke (`customer-ready-g2-fresh-export-cli-smoke-0630.md`)
  proves `uv sync`, import, CLI help, and `brick verify` on the exported tree;
  it also narrows first-build docs so provider-free `adapter:local` verdict
  lanes are honestly described as possible `agent_incomplete`/`not_ready`.

Pass evidence:

```text
release export generated from current origin/main
export grep/lint clean
customer-facing docs coherent
fresh export install/build/verify story measured or explicitly caveated
REAL HOME check_profile.py --all GREEN
COO/Smith disposition
```

## 5. Track G3 — FINAL architecture cleanup

Problem:

BRICK still carries godmodules and support-heavy surfaces. The goal is not to add
new abstraction; it is to reduce and clarify existing boundaries.

Targets:

```text
case_runners.py remaining leaves
kernel_checks.py oversized checker clusters
walker/run support seams if live measurement says they are still godmodule-like
giants profiles / duplicated support logic
```

Rules:

```text
conservation ledger first
byte-identical move where possible
mutation-RED for behavior pins
net-negative LOC / simpler module map
no new axis
no new runtime / scheduler / queue / retry owner
no support-owned success, quality, Movement, or target selection
```

Pass evidence per leaf:

```text
Building-produced or explicitly recorded maintenance patch
ledger / proof doc
compileall
targeted checker/profile
REAL HOME check_profile.py --all GREEN
optional Claude/Gemini/Codex review as support evidence only
COO/Smith disposition
```

### G3 live target correction (0630)
On current main `kernel_checks.py` (11452 LOC) is the LARGEST godmodule,
exceeding `case_runners.py` (8503). The 0628 plan LOC coordinates are stale;
next leaf target is re-pointed to `kernel_checks.py` by live measurement.
Evidence: `customer-ready-closeout-g1g2g3-status-0630.md`.

## 6. Operating order

Default next order:

```text
1. G1 route-default policy
2. G2 customer release pruning finalization
3. G3 FINAL architecture cleanup next leaves
```

Reason: G1 fixes the graph/Movement misunderstanding that keeps contaminating
future Building design. After that, G2 makes the product surface honest, and G3
finishes structural cleanup without changing the customer contract mid-flight.

## 7. Closeout definition

This closeout goal is complete only when:

```text
G1 = route-default/no-link policy proven or explicitly narrowed with docs/checkers
G2 = customer export/release surface proven clean enough for handoff
G3 = final architecture cleanup reaches agreed stop condition with remaining debt named
composition-first + building-running skill chain updated and still coherent
main = origin/main
worktree clean
REAL HOME check_profile.py --all GREEN
final closeout record written
Smith/COO says forward
```

Anything less is partial. If a track is intentionally deferred, it must be named
as deferred with owner, reason, and proof limit; it cannot be silently treated as
done.

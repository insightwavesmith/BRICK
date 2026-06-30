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

Canonical Korean goal statement (Smith wording, 0630):

```text
BRICK 고객 제공 준비 마감 작업:

남아 있는 3개 트랙을 완료한다.

1. route-default 정책
2. customer release pruning 최종화
3. FINAL 아키텍처 정리

단, 다음 기준은 반드시 유지한다.

COO/operator 역할을 보존하고, Building-first 워크플로우를 유지하며,
evidence-first 보고 방식을 지킨다. 또한 이전의 실수와 오판에서 얻은
교훈을 문서화하고 계속 반영한다.

메인 에이전트는 G1/G2/G3 구현 슬라이스를 위해 실제 Building을 직접
그리고 실행해야 한다는 구속력 있는 규칙을 지킨다. 이를 통해 메인
에이전트의 Building 실행 스킬 체인이 처음부터 끝까지 실제로 훈련되고
검증되도록 한다.

메인 에이전트의 토큰은 판단, 사고, route/Movement 판정, Building graph
구성, 최종 synthesis에 우선 사용한다. broad code reading, raw/evidence
JSONL 덤프, 긴 check log 읽기, 대규모 실측 진단은 기본적으로 단일 진단 Building으로 발주한다.
필요한 Brain은 Codex lane으로 배정하되 “Codex Ultra” 같은 비존재 모델명은 쓰지 않는다.
메인 스레드는 bounded field extraction + short verdict로 보고한다.
```

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

## 0c. MAIN-AGENT MUST DRAW & FIRE BUILDINGS (binding goal element)

Smith ruling (0630): the main agent (me, fugu-ultra/COO) must ACTUALLY draw the
graph and FIRE the Building through the official route for G1/G2/G3 IMPLEMENTATION
slices. Only by drawing/firing real Buildings does the MAIN AGENT's building-running
skill chain get exercised end to end and stay connected:

```text
main agent draws graph (LLM + Brick + Graph)
-> brick-task-author / building-coordination / building-sizing-method / task_intake
-> assembly.build/fan/fire OR brick build --graph (official route)
-> frontier/evidence
-> COO judge forward/reroute/HOLD
```

Why this is in the goal (not just a style note): if I keep doing implementation
by direct operator patch, the main-agent skill chain is NEVER walked, so it is
never proven or improved. A direct patch that is "byte-identical / mechanically
checkable" is STILL a skipped-chain shortcut; that judgment ("byte-identical => I
may patch directly") was a documented misjudgment (0630) and is rejected here.

Binding rules for this goal:

```text
- Default for every G1/G2/G3 implementation slice = draw + fire a Building.
- Direct operator patches are reserved for non-implementation maintenance
  (status docs, anchor/reload wiring, reverting a wrong slice) and must be
  recorded as exceptions.
- If I "cannot" express an implementation slice as a Building graph, that is a
  building-running-skill gap to FIX FIRST (0b), not a license to patch directly.
- The building-running skill chain is updated from what each real firing teaches,
  until the goal is complete.
```

## 0d. TOKEN-COST DISCIPLINE (binding goal element)

Smith ruling (0630): the main agent must treat token budget as an operating
resource. The largest avoidable token waste in this goal is broad reading of
raw/evidence JSONL, full check logs, unbounded grep/find output, and long
re-explanations after the same fact is already established.

Binding rules for this goal:

```text
- Default evidence inspection = field extraction + short verdict.
- Do NOT broadly cat raw/agent-return.jsonl, capture/events.jsonl, whole evidence
  folders, or full check_profile logs unless debugging a concrete failure.
- Use bounded commands by default: wc -c, tail -20/-40, jq/python field extraction,
  grep for exact keys, and summarized rc/pass/failure counts.
- check_profile --all output goes to /tmp/*.txt; report only rc, profile pass count,
  failure marker count, and at most tail -2 unless failure requires more.
- Polling Buildings should be fire-and-forget + thin frontier/result checks; do not
  repeatedly print logs.
- If a broad investigation or expensive evidence scan is useful, declare a single
  diagnostic Building and assign the appropriate Codex lane. Do not use or document
  non-existent model names such as “Codex Ultra”.
- Final reports default to compact: observed / narrowly_proven / not_proven / next.
  Longer explanations only when Smith asks or when ambiguity would mislead.
```

Why this is in the goal: wasting the main thread on huge support logs makes the
operator worse at the actual closeout work. Token-heavy support reading is not
source truth, success judgment, quality judgment, or Movement authority; it is a
last-resort debugging surface.

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
- Release export payload parity proof (`customer-ready-g2-release-export-parity-proof-0630.md`)
  now proves two fresh exports from the same checkout produce identical
  git-tracked payload file lists and SHA-256 manifests, while excluding `.git/`
  metadata parity from the claim.

Pass evidence:

```text
release export generated from current origin/main or declared current checkout
export grep/lint clean
customer-facing docs coherent
fresh export install/build/verify story measured or explicitly caveated
payload parity measured across repeated exports (excluding generated .git metadata)
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

Per-leaf requirements / edge cases (binding for G3):

```text
1. live-measure exact spans + AST/import/call-site dependencies first.
2. if the cluster is not a true leaf, HOLD or use a heavier Building shape; do
   not force a mechanical extraction.
3. conservation ledger before or with the patch; name direct operator
   maintenance when the patch is not Building-produced.
4. move bodies byte-identical when possible; behavior changes need separate
   checker/admission before implementation.
5. prefer one flat checker-lib sibling; no new folder/module family/axis/runtime.
6. preserve public import path, re-export compatibility, profile IDs, and
   check_profile dispatch identity.
7. update module_registry.yaml for every new sibling.
8. mutation-RED or equivalent failing observation must prove the checker still
   detects the pinned bad case.
9. run compileall, git diff --check, focused profile/check, and REAL HOME --all.
10. write proof doc with narrowly_proven / not_proven / next Movement candidate.
11. stop condition must be declared before closing G3; remaining debt must be
    named instead of silently treated as done.
```

### G3 live target correction (0630)
On current main `kernel_checks.py` is the LARGEST godmodule, exceeding
`case_runners.py` (8503). The 0628 plan LOC coordinates are stale; the leaf
series was re-pointed to `kernel_checks.py` by live measurement.

Two kernel_checks.py leaves LANDED (0630):
- leaf 1 (commit `a779a2c`): product no-Smith-residue scan cluster ->
  `support/checkers/lib/no_smith_residue_check.py` (165 LOC), 11452 -> 11325.
- leaf 2: onboarding install-script + release-export exclusion lints ->
  `support/checkers/lib/install_release_export_lint_check.py` (213 LOC),
  11325 -> 11151. Ledger/proof=
  `customer-ready-final-architecture-install-release-export-lint-{ledger,proof}-0630.md`.
Both: byte-identical bodies, re-export + dispatch identity preserved,
mutation-RED, REAL HOME `check_profile.py --all` GREEN, `module_registry.yaml`
rows added. Cumulative kernel_checks.py: 11452 -> 11151 (net -301).

G3 remaining (live): `kernel_checks.py` (11151) is still the largest godmodule;
more pure leaves remain (provider_preflight / onboard_smoke are audited
near-leaves with one shared `_ensure_import_identity` ref; mcp_stdio_smoke /
connect_config_launch are further candidates), and the agreed STOP CONDITION for
FINAL architecture cleanup is not yet declared.
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

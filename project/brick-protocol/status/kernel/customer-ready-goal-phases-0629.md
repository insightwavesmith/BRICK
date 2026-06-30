# Customer-Ready BRICK — Goal Phases Index — 0629

Status: support evidence only (operator index). Not source truth / success / Movement authority.
Context anchor: `customer-ready-goal-anchor-v01.md` is the compact reload target for compression/session handoff.
THE phase index: each phase → its detail doc. Goal-of-record (full spec) =
`customer-ready-goal-current-definition-0627.md`. Consolidation / audit / decisions / standard shapes
= `customer-ready-plan-audit-roadmap-0629.md`. Browse: the `GOAL/` folder carries P0–P8 symlinks to the detail docs below.

## Goal (one line)
A customer installs BRICK, connects their LLMs, says `make X`; an AGENT (COO) drives the official
`brick build` route (Brick / Agent / Link) and returns artifact + evidence. Final proof = self-dogfood
through that same customer path.

## GOAL PROMPT (operator discipline — must survive context compression)
```
GOAL: customer installs BRICK -> connects LLMs -> says `make X`. YOU (operator) drive the official
`brick build` route; Brick/Agent/Link declare the work, performers run it, evidence returns.
Final proof = BRICK self-dogfoods that same customer path.

YOU = OPERATOR / COO (never a worker lane):
- You JUDGE — define the dev decomposition from the design; disposition closure (forward/reroute).
  Judgment is yours, never auto-pilot.
- You do NOT become the worker. Implementation/QA/closure run through Building Agents.
- Claude/Codex/Gemini output = support evidence ONLY — never source truth / success / quality / Movement.

OFFICIAL ROUTE ONLY: implementation/QA/closure go through `brick build` -> cli/driver -> Builder ->
declared Building Plan -> run.py/walker -> evidence. No bypass (no direct build()/helper/hand-runner
calls; no operator-injected return-shape/ref/carry).

WHEN SOMETHING IS WRONG — think in AXES, not in modules:
 1. ASK WHICH AXIS first — Brick (work contract/template/plan/return-shape/graph) · Agent (performer/
    policy/capability/receipt/AgentFact) · Link (Movement/target/carry/gate/reroute).
    NOT "patch the nearest visible support noun."
 2. FIND YOUR OWN ERROR FIRST — is it your operating mistake or a contaminated measurement (wrong HOME/
    env), not a code defect? Re-measure in the REAL environment before calling it a bug.
 3. CHECK IT ALREADY EXISTS — the mechanism is probably already built; FIND it before adding anything.
 4. DERIVE THE REAL FIX — root cause; fix size = cause size. NO band-aid, NO module proliferation, NO
    feature-adding reflex. Prefer SIMPLIFY / DELETE over add — the complexity itself makes the holes.
 5. PER THE 3-AXIS CONSTITUTION — support records FACTS, judges nothing. Sufficiency + Movement = Link
    gate. Quality + success = human. Brick = WHAT, Agent = WHO/HOW, Link = Movement.

MEASURE, DON'T INFER. Execution results only, in the real environment. Verify your own output
adversarially before committing.
```

## Success judgment (how EVERY phase is judged)
Success is **MEASURED, never claimed.** A phase PASSES only when ALL of:
1. `check_profile.py --all` GREEN with the **REAL HOME** (never `HOME=$(mktemp -d)`), AND
2. the phase's PASS criteria below are met **end-to-end** (not slice-claims, not "the record says done"), AND
3. for a Building: `frontier_kind=="complete"` (read from `--json`) or `brick verify` exit 0 — **NOT** `brick build`'s exit 0 (that is intentional 3-axis and judges nothing), AND
4. the **COO (Claude) dispositions it forward** after adversarial self-verify.
Support records FACTS; the COO/human JUDGES. "CR record/audit" commits are not proof.

## Phases — progress in this ORDER (each → `GOAL/` symlink)
Execution order = critical path: **P3 sealed → P5 → P7 → P8 = GOAL.** P0/P1/P2/P3/P4 DONE; P6 off-path (later). Each gated by its PASS.

## 현재 상태 (0630 — P3 clean smoke seal 반영)
- **P3 code baseline = `f3744e9`; skill/goal sync = `3e29acf`; formal clean smoke = `p3-fire-clean-smoke-0630-c1`.** P0/1/2/3/4 DONE. Compact reload anchor = `customer-ready-goal-anchor-v01.md`.
- **P3 ENGINEERING CLOSED:** `brick build --graph <packet>` fan-in dogfood는 이미 `frontier=complete` + 실산출물 + spine + Slack로 증명됨. `f3744e9`에서 남은 두 지뢰도 닫힘: ① thin `fire(graph)` sugar(손 JSON/packet ritual 제거) ② caller-local output/slack root(`BRICK_HOME`/`~/.brick`, Smith 경로 제거). 검증: `brick_cli_entrypoint`, `building_operator_driver0`, `--all`, `compileall`, `diff --check` GREEN.
- **P3 formal seal PASS (0630 clean smoke):** `p3-fire-clean-smoke-0630-c1` ran through official `fire(graph)` customer route with work node `write=True` + bounded `write_scope`; result `frontier_kind=complete`, sandbox commit `ababf2a2628efd2062f472bd61d4d52455531ddf`, evidence root `/Users/smith/.brick/project/brick-protocol/buildings/p3-fire-clean-smoke-0630-c1`. Work return `made_changes=true` + changed file `project/brick-protocol/status/kernel/p3-fire-clean-smoke-0630.md`; closure return `transition_concern_evidence=null`; Link rows all `forward`; REAL HOME `check_profile.py --all` GREEN. P3 is sealed; support-recorded next target candidate = P5 (#2-#6). This status line does not choose Link Movement or phase disposition.
- **P5-B1 landed (0630):** `p5-b1-first-run-doc-route-align-0630` completed with `frontier_kind=complete`, sandbox commit `cf26e4c09e8faf4728e997e916b55e71344565bd`, merged as `bf67279`. Changed docs only: README.md, quickstart.md, launch-guide.md, setup.md. #2 README/quickstart preset-adapter mismatch is closed by using harmless `design-contract-only` + `adapter:local` first-run examples and separating real repository-changing work behind `--real-provider`/observed-write adapter. #5 launch-guide Python/helper hand-runner drift is cleaned by marking helper snippets advanced/internal/operator-only, not customer first-run route; if strict total snippet removal is required, leave a follow-up. Later P5-B3 aligned the frontier story; P5-B4 measured the former empty-HOME #6 prep hazard. P7 full fresh-machine proof remains separate.
- **P5-B1 landed (0630):** `p5-b1-first-run-doc-route-align-0630` completed with `frontier_kind=complete`, sandbox commit `cf26e4c09e8faf4728e997e916b55e71344565bd`, merged as `bf67279`. Changed docs only: README.md, quickstart.md, launch-guide.md, setup.md. #2 README/quickstart preset-adapter mismatch is closed by using harmless `design-contract-only` + `adapter:local` first-run examples and separating real repository-changing work behind `--real-provider`/observed-write adapter. #5 launch-guide Python/helper hand-runner drift is cleaned by marking helper snippets advanced/internal/operator-only, not customer first-run route; if strict total snippet removal is required, leave a follow-up. Later P5-B3 aligned the frontier story; P5-B4 measured the former empty-HOME #6 prep hazard. P7 full fresh-machine proof remains separate.
- **P8 PROVEN first-proof (0630):** `p8-dogfood-required-shape-20260629T182113Z` ran the official `brick build --graph` customer entrypoint (Codex work → Codex code-attack QA → Gemini axis-attack QA → Codex closure) to `frontier_kind=complete`, sandbox commit `89d72b54`, artifact `support/docs/references/p8-dogfood-capstone-20260629T182113Z.md`, 41-event spine hash-chain intact. Proof=`customer-ready-p8-dogfood-capstone-proof-0630.md`. First proof, NOT reliability proof.
- **Post-P8 landings (0630):** (a) customer release pruning first slice merged `ec0233c` (Smith-local path leak removed from 5 customer-surface skill docs); proof=`customer-ready-release-pruning-0630.md`. (b) durable release guard `release-guard-product-no-smith-scope-0630a` merged `065727f` widened `product_no_smith_residue` to scan `agent/skills` + `brick/templates/skills` with FIRE probes; proof=`customer-ready-release-guard-product-no-smith-scope-proof-0630.md`. (c) FINAL architecture leaves: first leaf `final-case-runners-leaf-extraction-0630a` merged `abcd439` (`case_runners.py` shrank ~194 LOC into `preset_completion_fixture.py`, byte-identical bodies, mutation-RED proven; ledger=`customer-ready-final-architecture-conservation-ledger-0630.md`, proof=`customer-ready-final-architecture-leaf-extraction-proof-0630.md`); second leaf `final-materialized-plan-observers-extraction-0630a` merged `c24667e` (`case_runners.py` shrank again to 10527 LOC via `materialized_plan_observers.py`, byte-identical bodies, mutation-RED proven; ledger=`customer-ready-final-architecture-materialized-plan-observers-ledger-0630.md`, proof=`customer-ready-final-architecture-materialized-plan-observers-proof-0630.md`); third leaf `final-plan-fixture-helpers-extraction-0630a` merged `44be7fa` (`case_runners.py` shrank again to 10340 LOC via `plan_fixture_helpers.py`, byte-identical bodies, mutation-RED proven; ledger=`customer-ready-final-architecture-plan-fixture-helpers-ledger-0630.md`, proof=`customer-ready-final-architecture-plan-fixture-helpers-proof-0630.md`); fourth leaf `final-gate-evidence-readers-extraction-0630a` merged `8420cc8` (`case_runners.py` shrank again to 10269 LOC via `gate_evidence_readers.py`, byte-identical bodies, mutation-RED proven; ledger=`customer-ready-final-architecture-gate-evidence-readers-ledger-0630.md`, proof=`customer-ready-final-architecture-gate-evidence-readers-proof-0630.md`); fifth leaf `final-materialize-reject-scaffold-extraction-0630a` merged `5f749c6` (`case_runners.py` shrank again to 10158 LOC via `materialize_reject_scaffold.py`, byte-identical bodies, mutation-RED proven; ledger=`customer-ready-final-architecture-materialize-reject-scaffold-ledger-0630.md`, proof=`customer-ready-final-architecture-materialize-reject-scaffold-proof-0630.md`); sixth leaf `final-adapter-capability-checks-extraction-0630a` merged `6470794` (largest leaf: `case_runners.py` shrank 10158 -> 8842 LOC via `adapter_capability_checks.py`, 34 helpers byte-identical, dispatcher kept in case_runners, mutation-RED proven; ledger=`customer-ready-final-architecture-adapter-capability-checks-ledger-0630.md`, proof=`customer-ready-final-architecture-adapter-capability-checks-proof-0630.md`); seventh leaf `final-materialized-return-shape-guards-extraction-0630a` merged `5a06a1f` (`case_runners.py` shrank 8842 -> 8659 LOC via `materialized_return_shape_guards.py`, byte-identical bodies, mutation-RED proven; ledger=`customer-ready-final-architecture-materialized-return-shape-guards-ledger-0630.md`, proof=`customer-ready-final-architecture-materialized-return-shape-guards-proof-0630.md`). (d) composition-first dogfood mandate + skill-as-diagnostic baked into anchor + `building-coordination` skill (`8fabf48`), then extended into `task_intake` so intake must extract LLM/Brick/Graph composition and reject the stale fixed pipeline (`c1c5e2a`). REAL HOME `--all` GREEN (28 profiles) after each.
- **FINAL architecture leaf #8 landed (0630):** `final-casting-node-carry-extraction-0630a` produced sandbox commit `0cfde8d`, verified in REAL HOME, and integrated as `4ac4b9d`. It moves `_casting_node_carry_base_graph_plan` + `run_casting_node_carry` into `support/checkers/lib/casting_node_carry_check.py`, keeps `case_runners.py` re-export compatibility, and adds one checker-lib module registry row. Verification: `compileall`, `git diff --cached --check`, `agent_axis_behavioral`, REAL HOME `--all`, and Claude read-only code QA all GREEN/FORWARD. Proof=`customer-ready-final-architecture-casting-node-carry-proof-0630.md`. Route lesson: this Building forwarded because I authored all Link rows as `movement: forward` with no route policy/budget; QA blockers must become concern evidence and be adopted as reroute/HOLD by Link/COO under declared policy.
- **⚠️ P7 proof is against STALE origin:** `customer-ready-p7-real-provider-fresh-clone-proof-0630.md` cloned `origin/main HEAD=ebf5930`, but `origin/main` at that proof time did not include later local landings; current ahead/behind must be checked live with `git status`. That P7 fresh-clone proof therefore does NOT cover the current customer surface (P3 seal residue fixes, P5-B1, release pruning/guard, FINAL leaf). A real P7 PASS for the current product requires pushing `main` to origin first, then re-running the fresh-clone documented-steps proof. Push is an external-state change held for explicit Smith OK.
- **남은 임계경로:** P5(#6 prep measured enough to stop carrying the empty-HOME `intake_evidence_projection_case` hazard as an unmeasured active blocker; optional #5 strict-removal review remains only if Smith requires zero Python snippets; #3은 P5-B3 얇은 docs/FIRST_USE/checker/status wording alignment로 `brick build` exit 0 != PASS, closure=`frontier_kind=complete`, non-complete=`not_ready`+`evidence_root` inspect를 맞춤; #4는 FIRST_USE readiness evidence 보존으로 좁혀 수리, Agent YAML auto-population은 explicitly deferred/not_proven) → P7(fresh-machine origin/main clone→install→init/doctor/auth/onboard→build/fire→evidence/frontier inspection by documented steps only) → P8(dogfood 골) → customer release pruning → FINAL architecture cleanup.
- **cruft(비차단·위생):** stash/worktree/evidence 누적은 골을 막지 않으면 P7/P8 뒤 release pruning에서 고객 surface만 남기며 정리.
- **다음 임계경로 한 줄 (0630 sync):** current `main`/`origin/main` sync must be checked live; the product line contains P3 seal·P5-B1·release pruning·release guard·FINAL leaf가 이미 랜딩됨 → (1) if local commits are ahead, push with Smith/operator OK → (2) P7 fresh-clone proof against that current origin → (3) P8 reliability(반복 dogfood) → (4) customer release pruning 확대(과거 docs/내부 evidence/project status/stale goal 아카이브) → (5) FINAL architecture 다음 leaf들. P8 first-proof는 닫혔지만 reliability·release·FINAL은 not_proven.

### P0 freeze — DONE → `GOAL/P0-freeze.md`
PASS: evidence inventory frozen; old C6 evidence = HOLD; no stale-spine override. (Met.)

### P1 adapter authority — DONE → `GOAL/P1-adapter-authority.md`
PASS: gemini-local write only at NEED ∧ Agent-policy ∧ adapter-capability; empty tool_policy_refs fail closed. Measured: agent_axis_behavioral + resource_boundary green. (Met.)

### P2 capability taxonomy — DONE, one open gap → `GOAL/P2-capability-taxonomy.md`
PASS: read/probe_write/source_write declared (Brick) + admitted (Agent) + ENFORCED with teeth (reviewer-source-write mutation fires RED — verified). Measured: --all green + mutation-RED.
OPEN: the qa-lead leak (leader-lane review role escapes the reviewer ceiling) → closed only by the policy-split (reviewers → probe-write-scoped) = the FIRST dogfood.

### P3 Easy Building official route — SEALED (0630 clean smoke) → `GOAL/P3-easy-building.md`
PASS: a customer/COO can draw with `build`/`fan` and fire once with `fire(graph)` through the ONE official customer graph route → `frontier=complete` + raw/spine evidence. `f3744e9` closes the zero-footgun plumbing; `3e29acf` records composition-first + write-hand skill rules; `c1c5e2a` extends the same composition-first rule into `task_intake` so the first interview step does not collapse back to a fixed `work -> QA -> closure` pipeline; `p3-fire-clean-smoke-0630-c1` proves the clean route with real codex-local work+closure: `made_changes=true`, changed file exactly `project/brick-protocol/status/kernel/p3-fire-clean-smoke-0630.md`, closure concern null, Link all-forward, sandbox commit `ababf2a2628efd2062f472bd61d4d52455531ddf`, REAL HOME `--all` GREEN. Compact write-hand invariant remains: BOTH node `write=True` and launch `write_scope=...` are required.

### P4 resume fan-out — DONE → `GOAL/P4-resume-fanout.md`
PASS: resume recovers declared fan-out parallelism after forward disposition; replay deterministic. Measured: bounded_agent_proposed_routing_loop green + timed fixture. (Met.)

### P5 first-run / onboarding — ASSESSED · P7 proof still pending → `GOAL/P5-first-run.md`
PASS: install/init/doctor/onboard truthful for the available-LLM customer; gemini readiness honest; FIRST_USE delivered; a real-provider first task runs → evidence; no hidden machine-local dep.
**STATUS (0630 after P5-B4 fresh-machine prep):** 정직성 골격 OK · 게이트2(brick_cli_entrypoint·building_operator_driver0) green. **#1 output_root hardcode는 P3에서 CLOSED. #2 [HIGH] README/quickstart preset-adapter mismatch는 `bf67279`에서 CLOSED. #3 [MED] frontier story는 narrowed/aligned: `brick build` exit 0은 support evidence 반환일 뿐 PASS가 아니고, customer-visible Building closure는 `frontier_kind=complete`, non-complete frontier는 `not_ready` + `evidence_root` inspect로 문서/FIRST_USE/checker/status를 맞춤. #4 [MED·Agent]는 narrowed: FIRST_USE now preserves structured doctor readiness fields including Gemini `api_key_env_present` and `credential_validity=not_proven`; Agent YAML auto-population remains explicitly deferred/not_proven until a later Agent-owned admission. #5 [MED] launch-guide/Python helper drift는 customer-first-run 표면에서 advanced/internal로 fenced/cleaned; strict snippet deletion이 필요하면 follow-up. #6 [LOW→P7] fresh-machine prep now has a fresh-HOME `read-side-projection-boundary` measurement covering the former empty-HOME `intake_evidence_projection_case` hazard.** Remaining P7 gate: real origin/main fresh clone -> install -> init/doctor/auth/onboard -> brick build/fire -> evidence/frontier inspection using documented steps only. P5/P7/P8 final customer-ready claim remains not_proven.

### P6 cleanup / godmodule — BLOCKED, off critical path → `GOAL/P6-cleanup.md`
PASS: each god-module split **byte-identical** (behavior unchanged) — `--all` green oracle + mutation-RED + net-negative LOC. Includes the dead-pair sweep (development + cto-lead) landing --all green.

### P7 fresh-machine — BLOCKED → `GOAL/P7-fresh-machine.md`
PASS: origin/main clone → install → init/doctor/auth/onboard with at least one real provider → official build/fire/`uv run python3 -m brick_protocol.support.operator.cli build` route → evidence/frontier inspection on a clean machine, **documented steps ONLY**, `frontier=complete`, ZERO undocumented manual steps, NO hidden machine-local dep. The install-free `uv run ... cli build` form is the same official build surface when bare `brick` is not guaranteed; providerless `adapter:local` examples remain support evidence only and do not satisfy P7 PASS. P5-B4 fresh-HOME profile evidence removes the former empty-HOME `intake_evidence_projection_case` item as an unmeasured active blocker; it does not replace the full fresh-clone P7 proof.
**STATUS (0630):** A minimal real-provider fresh-clone probe (`p7-min-graph-codex-fresh-clone-20260629T180942Z`, proof=`customer-ready-p7-real-provider-fresh-clone-proof-0630.md`) reached `frontier=complete` — but it cloned `origin/main HEAD=ebf5930`, which is now behind local `main`. So P7 remains NOT PASS for the current product: the proof must be re-run against an origin that includes the P3-seal/P5-B1/release-pruning/release-guard/FINAL-leaf landings. Gating step = push local `main` to origin (external-state change, explicit Smith OK), then re-run the documented fresh-clone proof.

### P8 dogfood capstone = GOAL — PROVEN FIRST-PROOF (0630) → `GOAL/P8-dogfood.md`
PASS evidence: `p8-dogfood-required-shape-20260629T182113Z` ran through official `brick build --graph` customer entrypoint using Codex work → Codex code-attack QA → Gemini axis-attack QA → Codex closure. Frontier=`complete`; sandbox commit=`89d72b54e20c645c4ea18a4c129784f3a710cc5c`; artifact=`support/docs/references/p8-dogfood-capstone-20260629T182113Z.md`; raw/spine operator check passed (41 events ending Frontier, hash chain intact, no forbidden top-level return keys in checked set). Proof doc=`customer-ready-p8-dogfood-capstone-proof-0630.md`. Single run = first proof, NOT reliability. Next: customer release pruning, then FINAL architecture cleanup.

## Building patterns (how each item runs)
**운영 원칙 (0630 Smith ruling):** 빌딩을 “발사 → Agent work → QA → closure → 판정” 고정 파이프라인으로 생각하지 않는다. COO는 사용 가능한 LLM, Brick 종류, Graph shape를 보고 매번 두뇌/손발 구성을 설계한다. 이 구성 사고 자체가 dogfood다. 만약 운영자가 이 사고를 못 하면 `brick-task-author` / `building-sizing-method` / `building-coordination` 스킬 구성이 부족한 것이므로, 빌딩굴리기 스킬은 P8까지 계속 업데이트한다.

**개발 큰것 (BIG) — TWO buildings, the COO (Claude) judges between:**
```
빌딩1: design (Fugu Ultra ∥ Claude → 종합)    → [COO reads design, DEFINES N parallel devs + what each]
빌딩2: fan([dev(Codex) → qa(Codex+Claude+Gemini)] × N) → closure → [COO disposition: forward / reroute]
```
The design→dev decomposition (how many, what) is a COO JUDGMENT (not automatic) — so design is cut as its own building.

**개발 작은것 (SMALL) — ONE building:**
```
design → dev → qa → closure → COO 보고
```

Both run via the official `brick build` route (P3 sealed-fluent). Capability layers stay clean:
read (design/closure) · probe_write (qa) · source_write (dev).

## P3 casting-pick (workflow-style performer selection)
When the COO launches workflow-style, it can PICK the performer per node — Fugu / Gemini / Claude / Codex —
not only the default cast.
- **Default cast (ratified 0629)**:
  - design = **Fugu Ultra** (`adapter:codex-fugu-local` + `model:sakana:fugu-ultra`) — small work uses Fugu Ultra alone; **개발 큰것 adds Claude** (design = Fugu Ultra ∥ Claude).
  - work/dev = **Codex** (codex-local).
  - **QA default = Claude** (base single reviewer); the 3-axis review (Codex + Claude + Gemini) is attached via **per-node adapter refs when declaring the graph** — not a fixed default.
  - closure = COO (Claude) / Codex.

**Per-node casting recipe (ALREADY in the official route — measured 0629, NO build needed):**
- Graph packet (`brick build --graph`): each node declares `selected_adapter_ref` + `selected_model_ref`. e.g. design → `adapter:codex-fugu-local` + `model:sakana:fugu-ultra`; a QA node → `adapter:codex-local` / `claude-local` / `gemini-local`. (Proven: four-llm-standard-graph already casts work=codex, axis-qa=gemini, closure=codex per node.)
- Assemble: `brick(kind, work, adapter="codex-fugu-local")` per node → flows to `selected_adapter_ref`.
- So multi-LLM (3-axis QA, Fugu Ultra design, +Claude for 개발 큰것) is attached per-node at graph-author time — no new code.
- PENDING (small re-wire, after the current dogfood, touches agent/objects): role-yaml DEFAULTS → design default = Fugu Ultra, QA default = Claude. (The weekend cast Codex/Gemini is still wired; that is why the current dogfood ran Codex+Gemini.)
- **Override (경우의 수)**: the COO picks per node — especially 개발 큰것, where the design's needs drive the casting.
- This belongs to P3's "sealed + fluent" launch = draw the shape + pick the cast + fire once; the official route swallows the plumbing.

## Stale — do NOT use as current
- `customer-ready-goal-plan-2track-0626.md` (old 2-track framing)
- the 11 `customer-ready-*-0627.md` sub-docs (C6-era HOLD chain — historical, superseded by the 0629 rechecks)
- `GOAL/` folder's old `00-…`–`06-…` symlinks (0626) — refreshed to P0–P8 here. The `GOAL/*.json` graph packets are current (keep).

# BRICK 6-Surface Architecture Audit - Final Synthesis - 2026-06-30

## Scope

- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit and planning only.
- Source/code repair: none.
- Audit packets:
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-s1-brick-axis-0630.md`
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-s2-agent-axis-0630.md`
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-s3-link-axis-0630.md`
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-s4-support-machine-0630.md`
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-s5-checker-system-0630.md`
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
- External deployment reports reviewed and re-measured against current checkout:
  - `/Users/smith/Desktop/BRICK_main_static_architecture_deployment_review.md`
  - `/Users/smith/Desktop/BRICK_main_static_architecture_deployment_review.docx`
- Claude independent review packets reviewed and partially re-measured against
  current checkout:
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-report-0630.md`
    (`claude-report-0630.md` alias; 9,718 bytes): Korean workflow summary,
    method, verdict, core corrections, and index.
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-review-addenda-0630.md`
    (`claude-review-addenda-0630.md` alias; 22,276 bytes): C1-C19 corrections
    plus ADD-1-ADD-20 with file:line tables.
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-opinion-0630.md`
    (`claude-opinion-0630.md` alias; 10,572 bytes): six methodology and
    architecture opinions.
- Final integration companions:
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-final-coverage-matrix-0630.md`
    locks where Smith/operator, external report, and Claude C1-C19 / ADD-1-ADD-20
    inputs were routed across S1-S6.
  - `project/brick-protocol/status/kernel/brick-6-surface-audit-readiness-tuples-0630.md`
    replaces flat `ISSUE` as the implementation-priority lens with per-surface
    readiness tuples.

## Overall Verdict

`ISSUE`

All six audited surfaces returned `ISSUE`. After Claude review incorporation,
this verdict should be read as a findings-inventory label, not as a flat
readiness grade. The packet-level evidence carries gradients that the single
label hides: axis integrity, customer ship safety, dynamic-runtime proof, and
deployment hardening must be scored separately before implementation priority is
chosen.

Final integration correction: do not run another full S1-S6 document rewrite
just because more review evidence arrived. The S1-S6 packets now carry the
review additions as findings, coverage gaps, or repair candidates. The practical
priority lens is the companion readiness tuple:
`brick-6-surface-audit-readiness-tuples-0630.md`. The evidence-routing lock is
`brick-6-surface-audit-final-coverage-matrix-0630.md`.

This does not mean BRICK is dead or that the official route is fake. The audit found the opposite in several places: the official `brick build` route exists, active profile sweeps can pass, Gemini-local remains active while Gemini API is retired, `--large` is not canonical, and the route generally walks declared Building evidence.

The broad customer-ready claim is not yet proven because several high-risk boundaries are mixed:

- Brick return-shape truth versus Link carry/filtering.
- Agent return closure versus pre-persistence support intake.
- Link gate declaration versus support default adoption.
- Product route clarity versus stale docs/helper surfaces.
- Checker green versus what the checker is actually preserving.
- Current-machine proof versus fresh-machine customer proof.
- Public release export cleanliness.
- Dashboard ingest integrity and deployment hardening.
- Provider-specific write boundary disclosure.
- CI/required release gate proof.
- Raw evidence stream secret/PII scrub before ledger persistence.
- Resume/post-HOLD disposition isolation.
- Declared pytest surface honesty.

Claude review correction: the prior S4-F8 claim that `~/.brick/builds` appears
in CLI/status/init metadata is wrong at this commit. Direct search shows the
legacy string appears as a checker anti-regression message only, while live
resume help points at `~/.brick/goal-runs`. `building-evidence/` wording is also
an admitted active evidence-destination term, not automatically stale.

## Architecture Map

### Brick Axis

Owns:

- Work contracts.
- Building Plan composition.
- Brick templates and kind vocabulary.
- Required return shapes.
- Comparison facts.
- Write NEED interpretation.

Primary pressure:

- Fan-in source return shapes can be shrunk outside the template truth path.
- Easy graph sugar strips `transition_concern_evidence` from fan-in source shapes.
- Brick templates/presets co-locate Agent and Link selection metadata.
- Brick-side skills contain provider/role/verdict wording.
- `brick/spec.py` is a godmodule/coupling candidate.

### Agent Axis

Owns:

- Performer identity.
- Agent Object resources.
- Prompt/skill/hook/tool-policy refs.
- Adapter refs as provider-neutral capability connections.
- Closed `AgentFact` return.

Primary pressure:

- Chat-session submission can persist a returned payload that `AgentFact` later rejects.
- Constitution wording still lags `read / probe_write / source_write-artifact_write`.
- Agent prompts/skills leak Brick/Link authority language.
- Probe-write versus source-write is checker/policy/prompt separated, not proven filesystem-hard.
- Local provider projections are duplicated/stale.

### Link Axis

Owns:

- Transfer/carry.
- Gate sufficiency.
- Movement.
- Transition and route policy.
- Fan-out/fan-in transition meaning.
- Portfolio adoption policy.

Primary pressure:

- Raw rows without `declared_gate_refs` can later receive default adoption semantics.
- Invalid Agent transition concern evidence can still shape a HOLD pending target.
- Raw graph admission and composition fan-in policy checks are not fully unified.
- `re_instruction` is active in code but not clearly admitted in visible lifecycle shape.
- Link/support godmodule pressure is high.

### Support Machine

Owns:

- Expanding declared inputs.
- Walking declared roads.
- Sandboxing customer worktrees.
- Recording raw/evidence/projection.
- Rendering reports and status.

Primary pressure:

- `onboard approve` carries hidden default disposition author/action.
- Support uses a live frontier queue/pool for dynamic fan execution; this needs explicit admission as walking mechanics or a narrower rule.
- Absent report policy can default to external sink refs with real-delivery flags.
- Official route has several wrapper/sugar surfaces with a checker blind spot.
- Native child-dispatch auto-recording is not active/proven in this checkout.
- Support modules are large and boundary-sensitive.
- Public release export can include untracked unignored local files.
- Dashboard ingest is shared-secret-only and lacks replay/sequence/HMAC integrity.
- Gemini provider keys still enter parent `os.environ`.
- Sensitive path writes are recorded but do not block sandbox output commit.
- Dashboard container/viewer protection depends on deployment environment hardening.

### Checker System

Owns:

- Support evidence production.
- Profile/rule/kernel observations.
- Negative probes.
- Proof-limit reporting.

Primary pressure:

- `check_profile.py --all` is green but preserves known mixed invariants such as fan-in return-shape shrinking.
- Chat-session verdict-key intake gap is not caught early enough.
- Missing `declared_gate_refs` is not negatively probed as raw absence.
- Profile sweep writes temporary fixtures under live repo `project/` paths.
- `kernel_checks.py`, `case_runners.py`, and large standalone checkers are godmodule-heavy.
- Active checker maps/count docs are stale.
- Local checker strength is not proven as a CI/branch-protection release gate.
- Deployment hardening gaps need behavioral negative probes, not only text pins.

### Product Surface

Owns:

- Customer-facing entry.
- CLI ergonomics.
- Install/init/doctor/onboarding wording.
- FIRST_USE/docs.
- Declaration experience for "make X".

Primary pressure:

- Official `brick build` route exists and is checker-covered.
- Install/init/onboard docs drift across `onboard codex`, `brick init`, and nonexistent `brick onboard`.
- Graph packet docs blur compact graph packet with full internal Building Plan.
- P3 Easy Building is partial: the desired big-work graph shape is described in skills, but not yet easy enough as customer/operator product surface.
- Provider wiring is current enough to avoid hidden Claude-only claims, but repeated provider reliability is not proven.
- Fresh-machine customer-ready proof is not proven at current HEAD.
- Release export can copy untracked unignored local files into a public export.
- Dashboard ingest/container/viewer hardening is not customer-ready.
- Provider write-boundary strength differs by adapter and is not customer-visible enough.
- Dependency/release reproducibility policy is unclear.
- CLI/dashboard still need a stronger "state -> reason -> next action -> proof
  limit" product language.
- Engine state, product readiness, and human approval are not yet fully separated
  as customer-visible concepts.
- Ordinary customer product runs should not expose checker/profile complexity as
  the main operating interface.

## Cross-Surface Findings

### C1 - Return shape and carry are still mixed

- Surfaces: Brick, Link, Support, Checker.
- Evidence: S1-F1, S1-F2, S5-F1.
- Meaning: the system can preserve green while fan-in source Brick return shapes are reduced. The intended behavior should be: Brick return shape comes from `return.yaml`; Link carry/closure synthesis controls what moves forward.
- Repair candidate: restore template-full return shapes and move fan-in concern filtering to Link carry/closure policy, with a negative checker that fails any `observed_evidence, not_proven` shrink on work/QA/axis QA rows.

### C2 - AgentFact closure is not enforced early enough

- Surfaces: Agent, Support, Checker.
- Evidence: S2-F1, S5-F2.
- Meaning: a payload containing top-level verdict/Movement words can be accepted by chat-session intake before later AgentFact rejection.
- Repair candidate: add pre-persistence validation for AgentFact-forbidden top-level keys at submission intake.

### C3 - Link gate declaration absence can be normalized into behavior

- Surfaces: Link, Support, Checker.
- Evidence: S3-F1, S5-F3.
- Meaning: missing gate refs can be accepted and later mapped to default transition adoption. That makes "declared Link basis" too soft.
- Repair candidate: either reject missing `declared_gate_refs` on active rows or explicitly materialize the default at an admitted authoring boundary before runtime.

### C4 - Transition concern evidence can influence lifecycle before full validity is proven

- Surfaces: Agent, Link, Support.
- Evidence: S3-F2.
- Meaning: invalid concern evidence should not be able to set a pending target. Concern evidence is non-binding; only Link/caller/COO disposition can select route/target.
- Repair candidate: invalid concerns HOLD at source boundary without pending target, unless a declared disposition row supplies one.

### C5 - Official route exists, but route surfaces are too easy to confuse

- Surfaces: Support, Product, Brick.
- Evidence: S4-F4, S6-F1, S6-F2, S6-F3, S6-F10.
- Meaning: `brick build` is real, but docs and helper names still make `onboard.py`, `assembly.py`, `run_building_plan`, and full Building Plans look like alternative customer routes.
- Repair candidate: classify route surfaces as public CLI, official internal wrapper, advanced helper, or historical seam; checker-pin that classification.

### C6 - P3 Easy Building should be product ergonomics, not a new engine

- Surfaces: Product, Brick, Agent, Link, Support.
- Evidence: S6-F4 plus S1/S4 route findings.
- Meaning: no `--large` or hard-coded large route should be restored. The missing piece is an easy declaration layer that turns "this is big; design first; split it" into a `preset_task` or `graph_packet` over the official route.
- Repair candidate: implement/declare task-intake -> sizing -> design/QA -> graph packet -> official `brick build`, preserving template refs and return shapes.

### C7 - Checker green is useful but not enough

- Surfaces: Checker and all axes.
- Evidence: S5-F1 through S5-F13 plus Claude ADD-3 and methodology Opinion 6.
- Meaning: `--all` can be green while preserving undesired behavior. Checker green must remain support evidence; direct repros and negative probes decide whether the invariant is actually guarded.
- Repair candidate: add focused negative probes for the high-risk seams before broad checker diet.

### C8 - Customer-ready proof is narrower than the product story

- Surfaces: Product, Support, Agent.
- Evidence: S6-F5, S6-F8.
- Meaning: prior P7/P8/dogfood/provider proofs are valuable but do not prove current-HEAD fresh-machine readiness, repeated provider reliability, Slack reliability, or customer comprehension.
- Repair candidate: after P0/P1 repairs, run a current-main fresh-machine proof with exact proof limits.

### C9 - Public release export is not fail-closed against local secret residue

- Surfaces: Support, Product, Checker.
- Evidence: S4-F9, S5-F13, S6-F9.
- Meaning: `release_export.sh` currently exports tracked plus untracked unignored files, while `.gitignore` does not cover common secret/local config patterns. This can publish local residue even when the protocol architecture is otherwise clean.
- Repair candidate: tracked-only export by default, explicit `--include-untracked`, dirty-tree guard, denylist for `.env`, key, token, credential, and local config patterns, plus negative probes.

### C10 - Dashboard projection integrity is under-hardened for deployment

- Surfaces: Support, Product, Checker.
- Evidence: S4-F10, S4-F12, S5-F13, S6-F11.
- Meaning: dashboard is not source truth, but `/ingest` can alter the operator-visible projection using shared-secret equality only. There is no HMAC, timestamp skew, event id replay cache, or participant sequence.
- Repair candidate: add signed ingest contract and replay/sequence rejection; add container/runtime hardening and explicit viewer access-wall requirements.

### C11 - Provider write boundary and sensitive-write publication need product policy

- Surfaces: Agent, Support, Product, Checker.
- Evidence: S4-F11, S6-F12.
- Meaning: effective write is still gated by Brick NEED, Agent policy, adapter capability, and observation, but provider isolation strength differs. A `complete` frontier can still lead to sandbox output commit even if sensitive paths were observed.
- Repair candidate: expose provider boundary matrix in CLI/docs, keep Claude/Gemini write worktree-only by default, pass provider env through adapter subprocess env instead of parent `os.environ`, and block/mark commits when sensitive paths changed.

### C12 - Checker strength is not release governance until wired into CI or release gate

- Surfaces: Checker, Product.
- Evidence: S5-F12, S6-F13.
- Meaning: local `check_profile.py --all` green is useful support evidence, but it does not protect main or public release unless required by CI/branch protection or an admitted release process.
- Repair candidate: add GitHub Actions or equivalent release gate for compileall, pytest/checkers, `check_profile.py --all`, `brick verify`, dashboard build, and release-export negative probes.

### C13 - Product surface should be an operator decision console, not a new authority layer

- Surfaces: Product, Support, Link, Agent.
- Evidence: S6-F16.
- Meaning: BRICK's product identity is not "AI secretly succeeded"; it is an evidence operating surface that shows what the agents did, what the engine observed, what remains not proven, and what human/COO action is needed. The product surface should translate evidence into operator action while preserving source-truth, quality, success, and Movement boundaries.
- Repair candidate: standardize CLI and dashboard around state, reason, next action, evidence refs, proof limits, provider boundary strength, and approval/readiness separation.

### C14 - Checker complexity should be hidden behind product status for ordinary customer work

- Surfaces: Product, Checker, Support.
- Evidence: S5-F5, S5-F7, S5-F12, S6-F17.
- Meaning: BRICK-internal protocol development legitimately exposes checker detail because the product being built is the protocol/evidence/checker system itself. Ordinary customer product work should not require users to operate checker/profile internals. Checkers remain safety gates and support evidence, while the product surface translates their outcomes into state, reason, next action, evidence refs, proof limits, and not-proven facts.
- Repair candidate: add customer-facing status mapping for checker outcomes and keep detailed checker/profile output in an expandable evidence/debug path.

### C15 - Raw evidence streams can persist secrets or PII before export hardening sees them

- Surfaces: Support, Product, Checker.
- Evidence: Claude ADD-2, direct read of `support/recording/raw_claim_trace.py`.
- Meaning: prior secret analysis focused on local files entering release export.
  A separate risk exists earlier: raw BRICK evidence streams such as
  `raw/brick-work.jsonl`, `raw/agent-received.jsonl`, and
  `raw/adapter-error.jsonl` are written by `raw_claim_trace._write_jsonl` through
  `path.write_text(...)`. The current raw writer path does not call the
  credential-looking text guard that exists in narrower step-output /
  adapter-error diagnostic surfaces. This does not prove a real leak occurred,
  but it proves the ledger persistence path is not uniformly scrubbed.
- Repair candidate: add a raw-stream scrub/redaction seam before JSONL
  persistence or add an explicit checker that proves all raw-stream writers are
  guarded. Treat this as evidence-integrity hardening, not a Brick/Agent/Link
  authority change.

### C16 - Resume/post-HOLD approval is not covered by the customer worktree-sandbox wrapper

- Surfaces: Support, Link, Product.
- Evidence: Claude ADD-1, direct read of `support/operator/onboard.py` and
  `support/operator/driver.py`.
- Meaning: `run_approve_entry` appends a human/COO disposition row and calls
  `resume_building_plan(...)` directly. The customer-facing
  `_run_in_worktree_sandbox` wrapper is the home of the live-tree-untouched
  invariant for fresh customer runs, but this post-HOLD resume path does not
  route through that wrapper. This is not a new Movement issue: the disposition
  row remains Link/lifecycle evidence. It is an isolation boundary gap for
  resumed execution.
- Repair candidate: either run resumed customer work through an equivalent
  worktree/temp isolation bracket or require an explicit adapter_cwd isolation
  contract before post-HOLD resume.

### C17 - The declared pytest surface is misleading

- Surfaces: Checker, Product.
- Evidence: Claude ADD-3, direct read of `pyproject.toml` and
  `support/checkers/check_adapter_usage_meter.py`.
- Meaning: `pyproject.toml` points pytest at `support/checkers`, but current
  repo shape has no `test_*.py` files and only checker-internal `def test_*`
  helper names. One such helper takes a `repo` argument, so a bare pytest run is
  not the same verification surface as `brick verify` / `check_profile.py --all`.
  This is a product honesty and release-governance problem, not proof that the
  checker system has no teeth.
- Repair candidate: remove or correct the pytest declaration, rename internal
  checker helpers if needed, or wire pytest to a real smoke layer that delegates
  intentionally to BRICK's checker profile system.

### C18 - Priority must split protocol-correctness from ship-security

- Surfaces: Product, Support, Checker, all axes as applicable.
- Evidence: Claude opinion 1-5 plus direct review of the final priority stack.
- Meaning: one P0 list currently mixes live protocol correctness
  (`return.yaml` truth, AgentFact closure, Link concern validity) with
  ship-imminent deployment hardening (release export, dashboard ingest, CI
  gates). These are both important but have different urgency triggers. If
  public shipping is imminent, security/export/dashboard gates move first. If
  the next work is dogfood/internal Building correctness, protocol invariants
  move first.
- Repair candidate: publish two implementation orderings: `protocol-live-order`
  and `ship-imminent-order`, then select the active one explicitly.

### C19 - Static audit cannot certify dynamic runtime behavior

- Surfaces: Support, Checker, Product.
- Evidence: Claude opinion 6 and this audit's final proof limits.
- Meaning: this audit is strong as a static findings inventory but cannot certify
  concurrency, resume/replay interleavings, live provider behavior, or
  fresh-machine customer execution. This does not mean the dynamic walker is
  broken; it means the audit method cannot prove it. Dynamic claims require at
  least one end-to-end live/stubbed Building plus resume-across-HOLD proof before
  "core sound" or "customer-ready" language is promoted.
- Repair candidate: add a dynamic proof slice after the first repair set:
  real or stubbed provider run, worktree isolation, HOLD/resume, fan-out/fan-in,
  and dashboard/report projection inspection.

## Godmodule / Decomposition Candidates

These are candidates only. No split or deletion is admitted by this audit.

- `support/checkers/lib/kernel_checks.py`
- `support/checkers/lib/case_runners.py`
- `support/checkers/check_bounded_agent_proposed_routing_loop0.py`
- `support/operator/onboard.py`
- `support/operator/driver.py`
- `support/operator/run.py`
- `support/operator/dynamic_walker.py`
- `support/operator/assembly.py`
- `support/operator/walker_kernel.py`
- `link/spec.py`
- `brick/spec.py`
- `agent/spec.py`
- `brick/comparison.py`

Required rule for later cleanup:

- Facade-preserving split first.
- Conservation ledger before and after.
- Mutation-RED or behavior-conservation checks before deletion.
- Do not split dynamic graph walker until resume/fan-out proof is stable.

## Stale / Duplicate / Delete Candidates

These are not deletion instructions.

- Stale profile/preset counts in docs.
- Stale `struct-surgery-0623` and machine-local proof references in active customer docs.
- Stale weekend/Monday provider wording.
- Retired adapter/API names that are not serving negative probes.
- Old `onboard codex` public-route wording.
- "assembly.py customer front door" wording.
- Stale checker profile map.
- Text-pin duplicate rows in profile YAMLs.

Deletion condition:

- Keep retired/stale names if they are negative probes or historical evidence.
- Remove or move them only after a checker distinguishes "active customer docs" from "museum/history".

## Checker Gaps

High-priority gaps:

1. Fan-in source `required_return_shape` shrink must RED.
2. Customer graph packets carrying template-authority fields must RED, with no fan-in source loophole unless explicitly admitted.
3. Chat-session pre-persistence payload with top-level AgentFact verdict/Movement keys must RED.
4. Missing raw `declared_gate_refs` must RED or be explicitly normalized before runtime.
5. Invalid `transition_concern_evidence` must not set pending target.
6. Product docs must prove only two public build input modes: `preset_task` and `graph_packet`.
7. Ordinary checker sweeps must not directly invoke live providers, and fixture/probe writes must be bounded.
8. Release export must RED on synthetic untracked `.env`, tracked forbidden secret path, and dirty checkout unless explicitly allowed.
9. Dashboard ingest must RED on missing signature, wrong HMAC, old timestamp, duplicate event id, and sequence rollback.
10. Sensitive path writes in customer sandbox must RED or block/mark output commit.
11. Release governance must prove checker/dashboard/release-export gates are required before publication.

Medium-priority gaps:

1. Profile schemas should require meaningful teeth/proof limits.
2. Checker fixture writes inside the live repo should be isolated or explicitly documented as probe-write support behavior.
3. Stale doc/count checks should be separated from runtime proofs.
4. Dependency lock/release-resolution policy should be checker-visible before customer publication.

## Customer-Ready Blockers

Critical blockers before broad public claim:

- Raw evidence streams do not have a proven uniform secret/PII scrub before
  JSONL ledger persistence.
- Resume/post-HOLD approval is not proven to preserve the same worktree/temp
  isolation boundary as fresh customer runs.
- The declared pytest surface is misleading; current verification is the BRICK
  checker/profile system, not a real pytest suite.
- Public release export is not fail-closed against untracked unignored local secret/config files.
- Dashboard ingest lacks signed/replay-safe/ordered integrity.
- Current-HEAD fresh-machine install/init/doctor/build proof is not proven.
- P3 Easy Building is not yet easy enough as a product surface.
- Graph packet documentation can still lead operators into internal Building Plan/return-shape fields.
- Provider reliability and credentials are not proven beyond narrow local support evidence.
- Install/init/onboard docs disagree on the public route.
- Provider write-boundary strength is not customer-visible as a matrix.
- CI/required release gate is not proven.
- Dashboard/CLI do not yet fully present "why stopped / what to do next / which
  evidence to open / who must dispose" as the default product reading path.
- `complete`, checker green, closed dashboard display, commit SHA, and human
  approval need a customer-visible separation.
- Checker/profile internals are still too visible as the operating vocabulary
  for non-BRICK product work.

Important blockers:

- Slack/reporting reliability is not proven; docs should not imply delivery proof.
- Native child-dispatch recording is not active/proven in this checkout.
- Stale docs and old worktree references can mislead customer-first operation.
- Container hardening, viewer access wall, dependency reproducibility, and installer supply-chain policy remain deployment hardening items.

## Implementation Priority

### P0 Critical

Select the active ordering explicitly before repair. If public release is
imminent, run the ship-security order first. If the next target is internal
dogfood/customer-run correctness, run the protocol-live order first.

Protocol-live order:

1. Add raw-stream secret/PII scrub or a checker-proven guard before JSONL ledger
   persistence.
2. Preserve customer isolation on resume/post-HOLD approval or require an
   explicit adapter_cwd isolation contract.
3. Restore Brick return-shape truth and move fan-in filtering to Link carry/closure policy.
4. Reject AgentFact-forbidden top-level keys at chat-session pre-persistence intake.
5. Close the `declared_gate_refs` absence path or admit explicit default materialization before runtime.
6. Prevent invalid concern evidence from setting pending targets.
7. Correct the declared pytest surface so release/governance docs do not imply a
   nonexistent runtime test suite.
8. Block or explicitly mark sandbox output commits when sensitive path writes are observed.

Ship-imminent order:

1. Harden public release export: tracked-only default, dirty-tree guard, explicit `--include-untracked`, and secret/local denylist.
2. Add dashboard ingest integrity: HMAC, timestamp skew, event id, replay cache, and participant sequence.
3. Add CI/release gate for compileall, checker sweep, `brick verify`, dashboard
   build, release-export negative probes, and the corrected pytest/smoke story.
4. Then run the protocol-live order above before broad customer-ready language.

### P1 High

1. P3 Easy Building declaration surface: intake/sizing/graph-packet over official route.
2. Align install/init/onboard/FIRST_USE docs with actual CLI.
3. Clarify public route docs around `brick build`, compact graph packets, and internal helpers.
4. Add focused negative probes for the P0 seams.
5. Expose provider write-boundary matrix in CLI JSON and docs.
6. Add CI/release gate for compileall, checker sweep, `brick verify`, dashboard build, and release-export negative probes.
7. Classify route wrappers and helper APIs with checker coverage.
8. Narrow support report-policy defaults or require explicit external sink declaration.
9. Standardize CLI result format around state, reason, next action,
   evidence_root, proof limits, and not-proven facts.
10. Promote dashboard into an operator decision console: Attention Queue, Next
    Action Card, Proof Limit Badge, Provider Boundary Badge, and evidence links.
11. Add customer-facing checker-result mapping so ordinary product runs show
    product status and next action first, with checker/profile details behind an
    evidence/debug affordance.
12. Add a dynamic proof slice that exercises one Building with fan-out/fan-in and
    resume-across-HOLD before promoting static audit reassurance into
    customer-ready wording.

### P2 Cleanup

1. Checker diet after P0/P1 negative probes exist.
2. Godmodule decomposition with conservation ledgers.
3. Stale docs/museum separation.
4. Projection regeneration or review.
5. Dashboard container hardening and viewer access-wall docs.
6. Dependency lock/release-resolution policy.
7. Installer supply-chain/pinned uv path note.
8. Customer-facing glossary separating engine state, product readiness, human
   approval, checker evidence, and source truth.
9. Documentation rule: BRICK-internal development may expose checker details;
   ordinary customer product work should expose checker outcomes as product
   status, not checker machinery.
10. Keep the re-issued per-surface readiness tuple as the priority lens:
    `core_sound`, `axis_integrity_blockers`, `ship_safety_blockers`,
    `dynamic_runtime_not_proven`, `worst_severity`, `product_confusion_risk`,
    `ai_blame_prevention_impact`, and `shared_protocol_impact`.

### Later

1. Fresh-machine proof at current main.
2. Provider reliability/repeated-run proof.
3. Slack/dashboard/thread wake proof.
4. Dogfood capstone rerun after P0/P1 repairs.

## Next Recommended Work Declaration

Recommended next work should not be "six-surface audit again." The audit is complete enough to declare the first repair Building or direct repair plan. Use the coverage matrix to avoid re-litigating already-routed review evidence, and use the readiness tuple to choose protocol-live versus ship-imminent ordering.

Recommended first repair slice:

```text
Repair release export clean-room.

Invariant:
Public export includes tracked admitted files only by default.
Untracked files require explicit opt-in.
Secret/local config patterns are denied whether tracked or untracked.
Dirty checkout is refused unless explicitly allowed.

Checker first:
Add negative probes for synthetic .env, *.pem/*.key, .npmrc, credential/secret/token names, and dirty checkout.

Then patch:
.gitignore, support/onboarding/release_export.sh, release/export checker/profile.
```

Protocol correctness repair slice:

```text
Repair fan-in return-shape truth.

Invariant:
Brick return shape comes from brick/templates/bricks/<kind>/return.yaml.
Fan-in/carry filtering is Link/closure policy, not Brick return-shape shrink.
Customer/operator graph packets cannot author required_return_shape or carries_forward_fields.

Checker first:
Add negative probes for template-shape shrink and graph-packet template-authority fields.

Then patch:
driver/composition/assembly/checker surfaces only as needed.
```

Alternative protocol repair slice:

```text
Repair AgentFact pre-persistence closure.

Invariant:
Chat-session submission cannot persist returned payloads with top-level AgentFact-forbidden verdict/Movement keys.

Checker first:
Add a pre-persist RED case.

Then patch:
run_chat_session intake validation and profile coverage.
```

Evidence-integrity repair slice:

```text
Repair raw-stream secret/PII scrub.

Invariant:
Raw evidence JSONL writers do not persist credential-looking or high-risk PII
text without a redaction/guard decision. The guard is support evidence only and
does not judge source truth, success, quality, or Movement.

Checker first:
Add synthetic raw-stream records containing common provider/API/token/credential
and PII-looking patterns. The raw writer path must RED before the guard and pass
after redaction or explicit refusal.

Then patch:
support/recording/raw_claim_trace.py and the smallest shared secret-text guard
surface needed.
```

Resume-isolation repair slice:

```text
Repair post-HOLD resume isolation.

Invariant:
Customer resume/post-HOLD approval preserves the same live-tree-untouched
boundary as fresh customer runs, or refuses without an explicit isolated
adapter_cwd.

Checker first:
Add a held Building fixture whose resume-capable adapter attempts a write. The
live checkout must remain untouched.

Then patch:
support/operator/onboard.py / driver isolation wrapper seams only as needed.
```

Test-surface honesty repair slice:

```text
Repair declared pytest surface.

Invariant:
Published test commands and pyproject declarations describe runnable checks that
actually exist. BRICK's checker/profile system may remain primary, but pytest
must not be advertised as a dead or broken surface.

Checker first:
Add a command-level smoke proving the documented local verification command.

Then patch:
pyproject.toml, checker helper names, or a tiny pytest wrapper around the
intended BRICK verification command.
```

## Final Proof Limits

- This audit used subagents and model reviews, but final findings are based on Codex operator direct file reads, targeted command probes, and the six written audit packets.
- Subagent/model/checker green remains support evidence only.
- No source repair was performed.
- No fresh-machine proof was performed.
- No provider reliability proof was performed.
- No Slack delivery proof was performed.
- No dashboard ingest/network exploit test was performed.
- No Docker build or container runtime test was performed.
- No GitHub branch protection or required-check query was performed.
- No release export negative fixture was executed.
- No safe deletion was proven.
- No customer-ready claim is made by this audit.
- External `.md`/`.docx` reports were treated as support evidence only; every
  adopted finding was rechecked against current local files before integration.
- Claude review packets were treated as support evidence only. The adopted
  headline findings were rechecked against current local files. Lower-tier
  Claude ADD items have been routed into the relevant S1-S6 surface reports as
  corrections, coverage gaps, or repair candidates; unless explicitly marked as
  directly re-measured, they remain review evidence to verify in a later
  repair/audit slice.

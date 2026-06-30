# BRICK 6-Surface Audit - Final Coverage Matrix - 2026-06-30

## Scope

- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit integration only.
- Source/code repair: none.
- This file is not a new six-surface audit. It is the closure matrix proving how
  Claude review, Smith/operator corrections, and the external architecture
  reports were routed into the already-written S1-S6 packets and final
  synthesis.

Authoritative audit packets:

- `brick-6-surface-audit-s1-brick-axis-0630.md`
- `brick-6-surface-audit-s2-agent-axis-0630.md`
- `brick-6-surface-audit-s3-link-axis-0630.md`
- `brick-6-surface-audit-s4-support-machine-0630.md`
- `brick-6-surface-audit-s5-checker-system-0630.md`
- `brick-6-surface-audit-s6-product-surface-0630.md`
- `brick-6-surface-audit-final-synthesis-0630.md`

Support review packets:

- `brick-6-surface-audit-claude-report-0630.md`
- `brick-6-surface-audit-claude-review-addenda-0630.md`
- `brick-6-surface-audit-claude-opinion-0630.md`
- `/Users/smith/Desktop/BRICK_main_static_architecture_deployment_review.md`
- `/Users/smith/Desktop/BRICK_main_static_architecture_deployment_review.docx`
- Smith/operator product philosophy and correction notes in this thread.

## Integration Rule

Support/model/checker/dashboard evidence is not source truth. This matrix does
not say "Claude was right" or "Codex was right." It says which support evidence
was assigned to which surface, whether it is already embedded, and what proof
status remains.

Status vocabulary:

- `embedded`: reflected in S1-S6 or final synthesis.
- `embedded-as-coverage-gap`: carried as missing coverage, not as a proven bug.
- `embedded-as-repair-candidate`: carried as a future repair target.
- `directly-remeasured-in-packet`: the audit packet/final synthesis says the
  Codex operator or the review packet directly rechecked the local file claim.
- `review-evidence-only`: useful support review that still needs a later direct
  repair/audit proof before implementation.
- `not-applicable`: not a live current-repo issue after correction.

## Reaudit Decision

The attached "reaudit kickoff" direction was correct in spirit but its premise
is now mostly stale. The right closure is not another full rewrite of S1-S6. The
right closure is:

1. Lock the coverage matrix.
2. Re-issue flat `ISSUE` as readiness tuples.
3. Keep first repair candidates separate from audit evidence.
4. Start a repair Building only after selecting the active priority order.

Rejected shortcut:

- "Run the whole six-surface audit again" is rejected for now. It risks document
  churn without changing the next actionable repair surface.

## Smith / Product Philosophy Coverage

| Product intent | Assigned surface | Current coverage | Proof status | Next repair implication |
|---|---|---|---|---|
| Do not end with "AI failed." Preserve condition, evidence, blocker, and remaining proof limits. | S2 Agent, S4 Support, S6 Product | S6-F18, final C13-C14, readiness tuple below | embedded | Add `readiness_blocker_observation` / failure-attribution projection. |
| Everyone works under one shared protocol. | S1 Brick, S2 Agent, S3 Link, S6 Product | S1-F1/F2, S2-F1/F2, S3-F1/F2, S6-F16/F18 | embedded | Add protocol-compliance observation and product display. |
| P3 Easy Building is "declare the graph easily," not `--large` or a new engine. | S1 Brick, S4 Support, S6 Product | S1 External Review, final C6, S6-F4 | embedded | Build intake/sizing/graph-packet sugar over official route only. |
| Checkers stay safety gates; ordinary customer work sees product status first. | S5 Checker, S6 Product | S5 External Review, S6-F17, final C14 | embedded | Map checker results to state/reason/next action/evidence refs. |
| Infra/security findings are not automatically BAL axis leaks. | S4 Support, S6 Product | final C18 plus readiness tuple split | embedded | Score ship-safety separately from axis-integrity. |
| Operator should not manually inject `return_shape`, `brick.md`, or template refs. | S1 Brick, S4 Support, S6 Product | S1-F1/F2, final C1/C6, S6-F3/F4 | embedded | Preserve template `return.yaml`; customer graph packet cannot author template authority fields. |

## Claude C1-C19 Correction Coverage

| ID | Correction / framing change | Routed to | Current status | Notes |
|---|---|---|---|---|
| C1 | `brick/spec.py` locator for `brick()` spans `522-576`. | S1-F5, final synthesis | embedded | Locator correction only; finding remains a Brick godmodule/coupling candidate. |
| C2 | COO reroute-author wording locator is `agent/prompts/coo.md:40-41`. | S2-F3 | embedded | Preserves the Agent prompt authority-leak wording without wrong line pin. |
| C3 | `walker_reroute_budget.py` stale string locator is line 161. | S3-F5 | embedded | Severity reduced to low/cosmetic because runtime accepts `reroute`. |
| C4 | Dashboard `INGEST_SECRET` locator is `index.mjs:14-16`. | S4-F10, S6-F11, final C10 | embedded | Line 17 is production flag, not the secret derivation. |
| C5 | Chat-session evidence chain is `run_chat_session.py` -> `primitives` -> `return_fact`. | S5-F2, S2-F1 | embedded | Avoids mislabeling `run_chat_session.py` as a checker lib. |
| C6 | Final C7 evidence should account for S5-F1 through S5-F13. | final synthesis C7/C12/C9/C10 | embedded | Final synthesis now references F1-F13 and carries F12/F13 separately. |
| C7 | Link route policy glob is effectively one file: `basic_qa_repair.yaml`. | S3 Map | embedded | Prevents overstating the route-policy surface. |
| C8 | `make_agent_fact` is keyword-only. | S2 Map | embedded | Cosmetic but relevant to exact AgentFact closure language. |
| C9 | Old `~/.brick/builds` claim is wrong; live default is `~/.brick/goal-runs`. | S4-F8, final synthesis | embedded, directly-remeasured-in-packet | The remaining `.brick/builds` string is a negative checker message. |
| C10 | Missing `declared_gate_refs` is a normalization/admission seam, not arbitrary-route proof. | S3-F1, final C3 | embedded | Needs either raw absence reject or explicit default materialization before runtime. |
| C11 | Stale reroute error text is low/cosmetic. | S3-F5 | embedded | Runtime imports active `DISPOSITION_ACTIONS`. |
| C12 | Walker frontier queue/pool is not automatically a constitutional queue violation. | S4-F2 | embedded | Reframed as walker internal mechanics plus dynamic proof gap. |
| C13 | Chat-session verdict-key issue still high because poisoned submission can wedge. | S2-F1, S5-F2, final C2 | embedded | Fix must be pre-persistence and top-level-only. |
| C14 | `onboard approve` concern is silent default action/identity, sharper on post-HOLD. | S4-F1, final C16 | embedded | Also ties to resume isolation gap ADD-1. |
| C15 | Provider env gap is narrow: Gemini keys land in parent `os.environ`. | S4-F11, S6-F12, final C11 | embedded | Existing env mitigations are credited. |
| C16 | Dashboard ingest also has non-constant comparison and `dev-secret` default. | S4-F10, S6-F11, final C10 | embedded | Deployment-hardening, not BAL authority by itself. |
| C17 | Release export denylist only excludes `project` and egg-info. | S4-F9, S6-F9, final C9 | embedded | Reinforces tracked-only/denylist repair. |
| C18 | Invalid concern shapes a HOLD target but does not autonomously reroute. | S3-F2, final C4 | embedded | Keeps Link Movement distinction intact. |
| C19 | GOAL shape drift is 8 of 10 non-catalog shapes. | S1-F6 | embedded | Strengthens drift severity. |

## Claude ADD-1-ADD-20 Coverage

| ID | Addition | Routed to | Current status | Next repair implication |
|---|---|---|---|---|
| ADD-1 | Resume/post-HOLD disposition runs outside the credited worktree-sandbox wrapper. | S4, S3, S6, final C16 | embedded-as-repair-candidate | P0 protocol-live: resume isolation proof/repair. |
| ADD-2 | Raw agent transcript streams lack uniform secret/PII scrub. | S4, S5, S6, final C15 | embedded-as-repair-candidate | P0 protocol-live: raw-stream scrub or writer guard checker. |
| ADD-3 | Declared pytest surface is dead/misleading. | S5, S6, final C17 | embedded-as-repair-candidate | P0 protocol-live: test-surface honesty. |
| ADD-4 | `brick/work.py` return-shape parser was in scope but uninspected. | S1 | embedded-as-coverage-gap | Add parser/materializer equivalence negative probe. |
| ADD-5 | `walker_carry.py` was not inspected despite Link carry priority. | S3 | embedded-as-coverage-gap | Link carry audit before carry repair. |
| ADD-6 | Fan-in classification error path was not audited. | S1, S3, S5 | embedded-as-coverage-gap | Add malformed group/fan-in classification probes. |
| ADD-7 | Verdict-key validator asymmetry can over-reject nested keys. | S2, S5 | embedded-as-repair-candidate | Pre-persist fix must be top-level-only. |
| ADD-8 | Poisoned `submission.json` can wedge resume. | S2, S4, S5 | embedded-as-repair-candidate | Convert pre-persist reject into clean HOLD before file admission. |
| ADD-9 | Sensitive-write observation is not consulted on commit/resume path. | S4, S5, S6 | embedded-as-repair-candidate | Block or mark sandbox output commit when sensitive paths changed. |
| ADD-10 | Fixed fixture vessel makes checker sweep non-reentrant. | S5 | embedded-as-coverage-gap | Use unique/isolated fixture root or cleanup guard. |
| ADD-11 | `make-an-agent` skill still teaches stale read-write taxonomy. | S2 | embedded-as-repair-candidate | Update Agent authoring skill after capability taxonomy repair. |
| ADD-12 | CLI error path emits raw `str(exc)`. | S6 | embedded-as-coverage-gap | Add product-safe error taxonomy/scrub. |
| ADD-13 | `setup.md` still says 24 profiles while live profile count is 28. | S6 | embedded-as-coverage-gap | Fix first-use docs after profile governance decision. |
| ADD-14 | Portfolio adoption boundary in `driver.py` not probed. | S3 | embedded-as-coverage-gap | Add driver portfolio adopter negative probes. |
| ADD-15 | `crossing_registry.yaml` and `module_registry.yaml` not fully inspected. | S5 | embedded-as-coverage-gap | Registry drift/dead-row inspection before checker diet. |
| ADD-16 | `assembly.py` fan-in guard uses naive substring matching. | S1 | embedded-as-coverage-gap | Fold into return-shape parser/materializer repair. |
| ADD-17 | `brick/building.py` was named but uninspected. | S1 | embedded-as-coverage-gap | Inspect before any Brick fact split. |
| ADD-18 | Bare `brick` defaults to status, not help. | S6 | embedded-as-coverage-gap | Decide whether this is desired first-run UX. |
| ADD-19 | Dashboard participant/client memory can go stale/grow. | S4, S6 | embedded-as-coverage-gap | Fold into dashboard ingest/sequence hardening. |
| ADD-20 | Resume target-divergence controls exist and should be credited. | S3 | embedded | Keeps resume target concern bounded, not an open route-collapse claim. |

## External Architecture Report Coverage

| External theme | Routed to | Current status | Next repair implication |
|---|---|---|---|
| BRICK core is more viable than the product surface; prioritize product surface. | final synthesis, S6 | embedded | P3 Easy Building plus operator decision console. |
| Product should show accountability, not only automation. | S6-F16/F18, final C13/C14 | embedded | Add readiness/protocol projections. |
| Dashboard/CLI should show state, reason, next action, decision owner, evidence refs, proof limits. | S6-F16/F18, S4 External Review | embedded | Create `readiness_blocker_observation` and `protocol_compliance_observation`. |
| Failure attribution should be explicit and non-blaming. | S2, S4, S6 | embedded-as-repair-candidate | Use rule-derived blocker categories first; AI review can support later. |
| Checker complexity should not be the ordinary product interface. | S5, S6, final C14 | embedded | Hide detailed checker internals behind evidence/debug path. |
| Release/deployment hardening is real but not a BAL axis. | S4, S6, final C18 | embedded | Score ship-safety separately. |
| Dynamic runtime proof is still missing. | S4, S5, S6, final C19 | embedded | Add one end-to-end live/stubbed Building proof before customer-ready language. |

## Final-Synthesis C1-C19 Coverage

| Cross finding | Primary surfaces | Closure status |
|---|---|---|
| C1 Return shape and carry are mixed. | S1, S3, S4, S5 | Embedded; P0 protocol-live repair candidate. |
| C2 AgentFact closure too late. | S2, S4, S5 | Embedded; P0 protocol-live repair candidate. |
| C3 Link gate declaration absence normalized into behavior. | S3, S4, S5 | Embedded; repair can reject absence or materialize default before runtime. |
| C4 Invalid concern evidence can influence lifecycle. | S2, S3, S4 | Embedded; no autonomous reroute claim. |
| C5 Official route exists but surfaces confuse route levels. | S4, S6, S1 | Embedded; product docs/classification repair. |
| C6 P3 Easy Building is ergonomics, not engine. | S1, S4, S6 | Embedded; no `--large`. |
| C7 Checker green is useful but not enough. | S5, all surfaces | Embedded; negative probes required. |
| C8 Customer-ready proof is narrower than story. | S6, S4, S5 | Embedded; dynamic/fresh proof needed. |
| C9 Release export not fail-closed. | S4, S5, S6 | Embedded; ship-imminent repair. |
| C10 Dashboard ingest under-hardened. | S4, S5, S6 | Embedded; ship-imminent repair. |
| C11 Provider boundary and sensitive writes need product policy. | S2, S4, S6 | Embedded; protocol-live plus product repair. |
| C12 Checker strength not release governance. | S5, S6 | Embedded; CI/release gate repair. |
| C13 Product surface should be operator decision console. | S6, S4, S3 | Embedded; product philosophy anchor. |
| C14 Checker complexity hidden behind product status. | S5, S6 | Embedded; customer UX repair. |
| C15 Raw evidence stream secret/PII persistence. | S4, S5, S6 | Embedded; P0 protocol-live repair. |
| C16 Resume/post-HOLD isolation gap. | S4, S3, S6 | Embedded; P0 protocol-live repair. |
| C17 Declared pytest surface misleading. | S5, S6 | Embedded; P0 protocol-live repair. |
| C18 Priority must split protocol-correctness and ship-security. | all surfaces | Embedded; implemented by readiness tuple. |
| C19 Static audit cannot certify dynamic runtime behavior. | S4, S5, S6 | Embedded; dynamic proof slice required. |

## Remaining Proof Limits

- This matrix is not a repair.
- It does not prove a fresh-machine run.
- It does not prove live provider reliability.
- It does not prove dashboard/network exploit behavior.
- It does not prove CI or branch protection.
- It does not prove release export negative fixtures.
- It does not prove dynamic resume/fan-out/fan-in correctness beyond already
  cited checker/static support evidence.
- Lower-tier Claude ADD items remain review evidence unless the target surface
  explicitly says they were directly re-measured.

## Closure

The six-surface audit should now be read through two companion files:

- This file: coverage closure and evidence routing.
- `brick-6-surface-audit-readiness-tuples-0630.md`: priority/readiness grading.

The next work should be a repair Building or direct repair slice, not another
document-only reaudit.

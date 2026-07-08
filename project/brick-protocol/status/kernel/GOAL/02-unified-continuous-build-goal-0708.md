# BRICK 연속 시공 통합 GOAL — 0708 unified

Status: support evidence only. 이 문서는 source truth·성공/품질 판정·Movement 권한이 아니다.
Smith가 0708에 지시한 “골까지 쭉 이어가기”를 한 판으로 합친 운영 지도다.
이 문서는 기존 `01-continuous-build-goal-0708.md`, C3 handoff, order/route 피드백,
Route V2 검수 프롬프트, 그리고 현재 실행 중인 `building-call-v11-cleanup-first-0708a`
상태를 한곳에 모은다.

---

## 0. 정본 관계

```text
Live repo: /Users/smith/projects/BRICK
Current pushed base at 작성 시점: 69988d815ed77bb6b2006c04c37c2083d473e3df
C2 import-unify base: 7b99b8f7fd4e00a94d797620c4905afd9f957f7c
C3 status docs base: 3bce21bf4e58932b6233a1360ec3ce3825df286c
GOAL ⑤/⑥ updates: 6100e3eb6, fb765bdc3, 197b7df51, 69988d815, 28cfda632, 82a1b9699, 47cf35a4b
```

Source hierarchy:

```text
1. live repo files and emitted Building evidence
2. this unified GOAL support doc
3. prior GOAL doc: project/brick-protocol/status/kernel/GOAL/01-continuous-build-goal-0708.md
4. handoff: project/brick-protocol/status/kernel/handoff-coo-0708.md
5. order feedback: project/brick-protocol/status/kernel/order-architecture-feedback-0708.md
6. route feedback: project/brick-protocol/status/kernel/route-architecture-feedback-0708.md
7. route review prompt: project/brick-protocol/status/kernel/route-v2-review-prompt-0708.md
8. external draft docs in /Users/smith/Downloads/
```

External draft inputs currently admitted as design evidence only:

```text
/Users/smith/Downloads/brick_building_call_skill_full_architecture_v1.md
/Users/smith/Downloads/brick_building_call_skill_v1_1_rearchitecture_report.md
/Users/smith/Downloads/brick_building_call_skill_v1_1_product_plan.md
/Users/smith/Downloads/brick_building_call_audit_cleanup_plan.md
/Users/smith/Downloads/brick_route_v2_dev_implementation_architecture_v1.md
/Users/smith/Downloads/BRICK_order_architecture_v2_existing_overlay.md
```

Historical draft docs in Downloads are not repo source truth. If they are used, they must be
converted into repo-local support docs, checkers, or fixtures before implementation relies on them.

---

## 1. 골 한 줄

```text
C2 import-unify로 물리/패키지 이중신원을 없앤 뒤,
발주서/빌딩콜 v1.1을 cleanup-first로 세워 “발주서작성 → 확인 → lowering → run_building_intake”를 안정화하고,
Route V2는 sealed materialization/checker-first 트랙으로 분리해 검수·체커·view까지 병렬 가능한 slice만 진행한다.
walker/run/link/AgentFact 변경은 human gate 전까지 HOLD한다.
```

---


## 1.1 COO 운영권한 고정 — 0708 update

```text
COO는 실무 수행자가 아니다.
COO는 운영, 경계감시, 판단, gate/disposition, Building 조율만 한다.
구현/삭제/수정/검증 실무는 declared Building으로 진행한다.
COO가 직접 live checkout에서 source/code/resource를 고치는 방식은 이 현재 진행 중인 slice 이후 금지한다.
새 작업은 task intake -> declared Building -> sandbox/worktree execution -> evidence review -> COO/Smith disposition 순서를 탄다.
```

적용 시점:

```text
현재 이미 시작된 ⑤d menu/API 수습 이후부터 적용.
이후 ⑤e~⑤j 및 Route V2 R0/R1/R2는 COO 직접 구현이 아니라 Building으로 진행한다.
GOAL 문서/status 갱신, evidence 판독, gate 판단은 COO 운영 작업으로 허용한다.
```

Proof limit: 이 절은 운영정책 support evidence이며 source truth·성공/품질·Movement 권한이 아니다.

---

## 2. 전체 상태판

| # | 트랙 | 상태 | 현재 판단 |
|---|---|---|---|
| ① | repo/worktree 위생 | ✓ | 0708 기준 정리 완료. 단 현재 active building 변경물이 main checkout에 남아 있어 착지 전 분리 관리 필요 |
| ② | 소형 필수 수리 | ✓ | 게이트 .DS_Store, Rule13 durable evidence 등 기존 origin 착지 |
| ③ | 캐스팅 전환 | ✓ | fable5 active dispatch 퇴장 착지 `82a1b9699`; opus/sonnet 사용 가능성 probe 확인 |
| ④a | C1 import canonicalization | ✓ | `af60198cb` 포함, origin/main 착지 |
| ④b | C2 physical root unification | ✓ | `7b99b8f7f`, `brick_protocol/*`, top-level import 실패 확인 |
| ④c | C3 문서/human gate | ✓ | C3 상태문서 착지 + Smith 승인 후 BRICK-CONSTITUTION active physical roots 조항 착지. Proof limit: support evidence only |
| ⑤ | 발주서/빌딩콜 v1.1 | ✓ | ⑤a~⑤j 착지/관찰 완료(⑤b/⑤c `28cfda632`, ⑤f `298b28a86`, ⑤g `201e502d3`, ⑤h `569458a0d`, ⑤i `15ecf8bcc`, ⑤j dogfood evidence `6d7a0acf5`; sandbox output refs `e8b6f953`/`f0e75cae`는 origin/main에 도달하지 않는 sandbox-worktree ref다). Proof limit: support evidence only |
| ⑥ | Route V2 sealed materialization | 부분 착지 | R0/R1 sealed materialization checker/document slice `47cf35a4b` 착지. ⑥c R2 read-only view builder landed `134ad9550`; read-only view dogfood recorded at `project/brick-protocol/status/kernel/dogfood/0708-route-v2-view-dogfood.md`; ⑥d/⑥e HOLD |
| ⑦ | route/walker integration | HOLD | checker green + human gate + route_materialization view 안정 후에만 |
| ⑧ | 발주서작성 preset/Agent/menu/lowering | ✓ | ⑤d~⑤j declared Building/sandbox 경로로 관찰 완료. COO 직접 구현 금지 원칙 유지 |
| ⑨ | dogfood/골 closure | 부분 완료 | Building Call quick direct + order_authoring dogfood 관찰 완료. Route V2 read-only view dogfood 관찰 완료. remaining human gates/cleanup 이후 parent closure |

---

## 3. ④ C1/C2/C3 개헌 이주 요약

### 3.1 이미 완료

```text
C1: runtime층 최상위 import canonicalization
C2: brick/ agent/ link/ support/ 물리루트를 brick_protocol/ 아래로 git mv
```

Active roots:

```text
brick_protocol/brick/    = Brick axis physical surface
brick_protocol/agent/    = Agent axis physical surface
brick_protocol/link/     = Link axis physical surface
brick_protocol/support/  = support machine location only
project/                 = project-local evidence / status destination only
```

C2 proof snapshot:

```text
commit: 7b99b8f7fd4e00a94d797620c4905afd9f957f7c
origin/main: pushed
compileall brick_protocol: rc=0
import brick_protocol.support.operator.cli: rc=0
top-level import support/agent/brick/link: rc=1 each, expected fail
check_profile.py --all: rc=0, passed_count=55
```

### 3.2 human gate 승인 — 2026-07-08

```text
Smith 승인 1: BRICK-CONSTITUTION.md active physical roots 조항 추가 승인.
진행 방식: COO 직접 구현 금지 원칙에 따라 별도 declared Building으로 문서 패치/검증/착지.
proof limit: human approval 기록은 support evidence only; source truth·성공/품질·Movement 권한이 아니다.
```

---

## 4. ⑤ 발주서/빌딩콜 v1.1 — 현재 active track

### 4.1 핵심 정책

```text
Default route: order_authoring
Fast path:     direct_preset only after direct_preset_admission + fast_confirm
Critical:      human_gate_first
```

Direct preset 2-FIX:

```text
FIX 1. direct_preset_admission 통과는 launch 권한이 아니다.
       direct_preset도 fast_confirm 1회가 필요하다.

FIX 2. direct_preset 허용 case는 quick_fix / quick_check만.
       standard_delivery 이상은 order_authoring으로 보낸다.
```

운영문:

```text
Direct preset is an escape hatch, not the default path.
Direct preset admission is not launch authorization.
Only quick_fix and quick_check may use the direct path.
If COO hesitates or cannot prove triviality, route to order_authoring.
Preset is not a mold to force work into; it is the execution path after triviality is proven.
```

### 4.2 발주서작성 Agent 순서 규율

발주서작성 Agent는 “구조/브릭/에이전트”를 한꺼번에 사고하지 않는다. 순서가 핵심이다.

```text
STEP 1. 업무 파악(scope)
  - 대상 영역, allowed/forbidden path 후보, source_facts, 빠진 정보.
  - 구조/에이전트/LLM 언급 금지.

STEP 2. building 전체 과중 → 라우팅(triage only)
  - easy | normal | complex | critical.
  - easy 증명 -> direct_preset(quick_fix/quick_check) + fast_confirm.
  - normal/complex -> order_authoring 계속.
  - critical -> human_gate_first.
  - per-brick 세부/에이전트/LLM 금지.

STEP 3. 구조 그린다(structure)
  - Brick plane: 어떤 Brick들이 필요한가 = brick_kind + role.
  - Link plane: edges, fan-out/fan-in, 3d 구조, gate_state, held_for_coo_review.
  - Agent plane은 아직 role_need/capability_need/write_need만.

STEP 4. 업무 과중 넣는다(per-brick intensity)
  - STEP 3의 각 node에 easy | normal | complex | critical 부여.
  - 각 Brick의 work_statement/return need/proof obligation 확정.
  - 구체 Agent/LLM 금지.

STEP 5. 에이전트 선택(agent + strength)
  - 각 node의 role_need + capability_need + write_need + per-brick 경중으로
    Agent candidate + strength(cheap/default/deep/critical)를 Agent 칸에만 기록.
  - Brick 칸에는 adapter/model/provider 금지.
```

순서 위반 RED:

```text
- STEP 1 전에 구조/에이전트부터 고름
- STEP 3 전에 per-brick 경중이나 에이전트를 고름
- 구조/브릭/에이전트를 한 응답에서 동시 확정함
- Brick section에 selected_adapter_ref/model/provider를 씀
- preset 이름을 먼저 고르고 일을 끼워맞춤
```

### 4.3 ⑤ 세부 페이즈

| Phase | 이름 | 산출물 | 상태 |
|---|---|---|---|
| ⑤a | 정책/용어 고정 | order_authoring 기본, direct_preset 2-FIX, 순서 규율, selected_* 외부 금지 | ✓ |
| ⑤b | cleanup checker fence | external selected_* 금지, common preset selected_* 금지, gate_state_not_movement, no-success-fields, deep-design casting RED fixtures | ✓ pushed `28cfda632` |
| ⑤c | 오염 표면 정리 | `postmortem.md` selected_* 제거, `four-llm` product alias 제외/격리, deep-design return casting 제거 | ✓ pushed `28cfda632` |
| ⑤d | 메뉴/API | `building_call_menus.py`, brick/agent-role/intensity/strength/graph motif menu | 수습 완료 예정: 이번 direct 예외 slice로만 마감, 이후 실무는 Building-only |
| ⑤e | 발주서작성 preset/Brick/Agent | `building-call-authoring` preset, 전용 Brick/return, 발주서 전용 Agent skill(prompt) | landed candidate: repair-2 green, 착지/푸시 검증 중 |
| ⑤f | authoring module | `building_call_authoring.py`, `building_call_authoring_return_v1`, 순서 위반 checker | ✓ pushed `298b28a86`, clean --all green |
| ⑤g | lowering layer | `building_call.py`, fixture cases, confirmed-only lowering, provenance | ✓ landed candidate from `building-call-lowering-0708g` WIP; clean review worktree `--all` green before main landing |
| ⑤h | direct escape hatch | triage/admission/fast_confirm, quick_fix/quick_check만 direct | ✓ focused proof green in `building-call-direct-escape-0708h` |
| ⑤i | docs/skill examples | brick-task-author/building-call Quick Path, 4개 worked examples, 메뉴얼 규칙 | ✓ origin/main 착지 commit `15ecf8bcc` (sandbox output ref `e8b6f953`는 도달 불가); clean worktree focused profiles + `check_profile.py --all` rc=0 |
| ⑤j | dogfood | quick_check direct, quick_fix direct, order_authoring path 각 1회 증거 | ✓ observed via sandbox Buildings; quick_fix artifact origin/main 착지 commit `6d7a0acf5` (sandbox output ref `f0e75cae`는 도달 불가) |

### 4.4 현재 active building

```text
building_id: building-call-v11-cleanup-first-0708a
preset: building-chain-preset:app-feature-inspected
flow: plan -> design -> work -> review -> inspect -> closure
scope: ⑤b cleanup checker fence + ⑤c contamination cleanup
route v2: out of scope
```

Current observed closure/push snapshot:

```text
latest frontier: complete
frontier_reason: declared closed boundary observed after paused frontier disposition
observed_counts: agent_received_records=8, agent_return_records=8, link_records=16
tracked cleanup commit: 28cfda632 building-call: add cleanup-first fences
focused proof: compileall rc=0; check_profile.py --profile mutation_red_manifest rc=0; graph_draft rc=0; structure_template_integrity rc=0; git diff --check rc=0
--all status: not used as landing gate for this slice; live --all is polluted by local Building evidence Rule13 absolute/session-temp refs, so treat as remaining support cleanup, not ⑤b/⑤c tracked-code proof.
```

Note: 이 빌딩은 내가 `run_building_intake(... repo_root=., adapter_cwd=.)`로 직접 호출해 live checkout에 변경이 생겼다.
원래 병렬/정식 고객-facing 빌딩은 `run_customer_building_in_sandbox()` / worktree sandbox 경로를 써야 한다.
이 active building은 중복 발사하지 않고 closure까지 추적 후 착지한다.

Current local evidence surfaces after push:

```text
Tracked source/checker changes: pushed in 28cfda632.
Local untracked Building evidence remains intentionally uncommitted:
  project/brick-protocol/buildings/building-call-v11-cleanup-first-0708a/
  project/brick-protocol/status/inbox/*building-call-v11-cleanup-first-0708a*.json
Reason: evidence includes local absolute/session-temp refs and is support evidence, not product source.
```


⑤e Building-driven attempt status:

```text
primary Building: building-call-authoring-0708e
primary WIP ref: refs/brick/wip/building-call-authoring-0708e @ b51d7ebec
primary frontier: link_paused at closure/human gate
repair Building: building-call-authoring-0708e-repair
repair WIP ref: refs/brick/wip/building-call-authoring-0708e-repair @ 6356964d
repair frontier: link_paused at closure/human gate
superseding repair WIP ref: refs/brick/wip/building-call-authoring-0708e-repair-2 @ 8f85af1b
COO landing judgment: forward candidate; repair-2 is being landed after all-profile proof.

Narrowly proven by evidence:
- Building, not COO, performed ⑤e implementation attempts in sandbox/worktree.
- Primary WIP added preset, Brick kind/return shape, Agent skill/prompt, catalog/admission/profile wiring.
- Repair WIP added dedicated order-author Agent Object.
- Repair-2 narrowed building-call-authoring return.yaml forbidden_return_keys back to the Agent return_fact enforcement set.
- Repair-2 updated order-author candidate packet expectations and the all-current-presets fixture for the new common preset.
- check_profile.py --all on repair-2 observed 56/56 profiles passed, real red observations=0.

Resolved blocking observations:
- declaration_enforcement_parity is green after narrowing forbidden_return_keys to currently enforced return keys.
- building_skill_preset_agent_packet_boundary is green after admitting agent-object:order-author as the sixth read-only leader candidate.
- building_skill_preset_intake_adapter_gate is green after updating expected preset count/ref list to 30 including building-chain-preset:building-call-authoring.

Still out of scope:
- ⑤f/⑤g/⑤h/⑤i are now landed through declared Building work; ⑤j remains undone and must proceed through declared Building work.
```

⑤d menu/API 수습 slice:

```text
surface: brick_protocol/support/operator/building_call_menus.py
checker: brick_protocol/support/checkers/profiles/building_call_menus.yaml
module admission: check_package_path_admission.py + module_registry.yaml
purpose: read-only product menu for order-authoring sequence, Brick menu, Agent role menu, work intensity, agent strength, graph motif, routing mode
proof: render_building_call_menus import/invariant smoke rc=0; compileall rc=0; check_profile.py --profile building_call_menus rc=0; git diff --check rc=0
limits: this is a direct COO cleanup exception already in progress; after this slice, ⑤e~⑤j and Route V2 work must be Building-driven.
```

0708 landing update — model lane / Route V2:

```text
fable5-token-retire-0708h:
  frontier: complete
  landed commit: 82a1b9699 model-lane: retire fable5 active dispatch
  effect: adapter:claude-local rejects model:claude:claude-fable-5 as retired from active dispatch; model:claude:claude-opus-4-8, model:claude:sonnet, and model:claude:opus remain accepted by the validation probe.
  clean proof: temp detached worktree at 47cf35a4b observed compileall OK, git diff --check OK, focused model_lane_matching_discipline / agent_axis_behavioral / graph_draft profiles green, and check_profile.py --all rc=0.

route-v2-r0-r1-0708g:
  frontier: complete
  landed commit: 47cf35a4b route-v2: add sealed materialization checks
  effect: R0 canonical sealed-materialization architecture doc and R1 checker/profile/fixtures are now in origin/main; forbidden integration paths were not touched.
  clean proof: temp detached worktree at 47cf35a4b observed compileall OK, git diff --check OK, focused route_v2_sealed_materialization / structure_template_integrity / core profiles green, and check_profile.py --all rc=0.

constitution-active-roots-0708g:
  original frontier: agent_incomplete because code-attack-qa used adapter:claude-local + model:claude:sonnet, dispatched claude-sonnet-5, local_cli_nonzero, return_code=143.
  landed resolution: applied only the WIP commit's BRICK-CONSTITUTION.md active physical roots clause onto current HEAD; did not apply stale WIP changes to ⑤/⑥ surfaces.
  landed commit: pending in current patch.
  surfaces: BRICK-CONSTITUTION.md and this GOAL status note.
  proof: grep exact active roots in BRICK-CONSTITUTION.md; compileall; check_profile.py --all from clean detached worktree before landing.
  proof limit: constitution/status support evidence only; not source truth beyond Smith-ratified constitution text, not success judgment, not quality judgment, not Movement authority.

building-call-lowering-0708g:
  frontier: agent_incomplete on original Building because code-attack-qa used adapter:claude-local + model:claude:sonnet, dispatched claude-sonnet-5, local_cli_nonzero, return_code=143.
  WIP anchor: refs/brick/wip/building-call-lowering-0708g @ 792a4c34bc3cc298944286bc35bcc1bb8cb6caee.
  COO disposition: WIP anchor was applied to a clean detached review worktree on top of current HEAD; stale GOAL conflict was discarded; code/checker surfaces were verified independently.
  landing proof before main commit: compileall OK, git diff --check OK, building_call_lowering / building_call_authoring / building_call_menus / structure_template_integrity focused profiles green, and check_profile.py --all rc=0 in /tmp/brick-review-lowering-73593.
  proof limit: this lands the ⑤g lowering support surface; it does not prove ⑤j dogfood, future request semantic fitness, source truth, success, quality, or Movement authority.

building-call-docs-examples-0708i-repair2:
  frontier: complete
  output commit: e8b6f9530baf4be0160814d77c45c953ff7acaac
  origin/main landing commit: 15ecf8bcc (the e8b6f953 sandbox output ref is NOT reachable in origin/main; the same content landed under 15ecf8bcc)
  surfaces: brick_protocol/agent/skills/brick-task-author/SKILL.md, brick_protocol/brick/templates/skills/brick-task-author/SKILL.md, brick_protocol/agent/skills/building-call-authoring/SKILL.md, brick_protocol/support/checkers/profiles/building_call_menus.yaml
  effect: Agent-source and ship-copy brick-task-author Quick Path sections match and contain the four explicit examples: direct quick_check, direct quick_fix, order_authoring, human_gate_first / forbidden direct. Building-call-authoring skill carries equivalent labels and exposure limits.
  proof: clean detached worktree applied e8b6f953; compileall OK; git diff --check OK; focused profiles building_call_menus, building_call_authoring, building_skill_preset_agent_resource_boundary green; check_profile.py --all rc=0.
  proof limit: docs/skill/checker support evidence only; no dogfood execution, no launch authorization, no route/walker integration, no source truth, no success judgment, no quality judgment, no Movement authority. ⑤j now covered by later sandbox dogfood evidence; this prior proof itself still did not launch a Building.

building-call-direct-escape-0708h:
  frontier: focused implementation evidence recorded.
  surface: brick_protocol/support/operator/building_call.py
  checker/profile: brick_protocol/support/checkers/profiles/building_call_direct_escape.yaml
  fixtures: brick_protocol/support/checkers/fixtures/building_call_direct_escape/*.json
  effect: direct_preset_admission + fast_confirm lowers only quick_fix -> building-chain-preset:fast-fix and quick_check -> building-chain-preset:quick-check. Default triage evidence stays order_authoring; standard_delivery, missing fast_confirm, red flag, critical red flag, selected_*, provider/model/adapter, and malformed red-flag probes are rejected.
  proof: compileall rc=0; check_profile.py --profile building_call_direct_escape rc=0; check_profile.py --profile building_call_lowering rc=0; git diff --check rc=0; check_profile.py --all rc=0.
  coverage repair: reroute pass tightened direct-preset validation so dict/list-of-dict/bool/int red_flags or critical_red_flags no longer collapse to an empty list, and bare model/provider/model_ref/provider_ref/adapter_ref request fields are rejected alongside selected_* fields.
  proof limit: support triage/lowering evidence only; no launch authorization, no route/walker integration, no source truth, no success judgment, no quality judgment, no Movement authority. ⑤j now covered by later sandbox dogfood evidence; this prior proof itself still did not launch a Building.
```

⑤j dogfood sandbox Buildings:

```text
quick_check direct:
  building_id: building-call-0708j-quick-check-direct-dogfood
  route evidence: building_call_direct_preset_admission_v1 -> lowered_intent chain_preset_ref building-chain-preset:quick-check
  frontier: complete
  evidence_root: /Users/smith/.brick/project/brick-protocol/buildings/building-call-0708j-quick-check-direct-dogfood
  commit_sha: none (read-only quick-check route; no sandbox source diff expected)

quick_fix direct initial RED:
  building_id: building-call-0708j-quick-fix-direct-dogfood
  route evidence: building_call_direct_preset_admission_v1 -> lowered_intent chain_preset_ref building-chain-preset:fast-fix
  frontier: human_review_waiting
  frontier_reason: fake_landing_write_scope_diff_absent
  interpretation: direct path reached Building execution, but write-need route had no scoped diff; fake-landing guard correctly stopped it.

quick_fix direct repair:
  building_id: building-call-0708j-quick-fix-direct-dogfood-repair
  frontier: complete
  output commit: f0e75cae08cfe6e8cd80cb414c73cb09ece507a7
  origin/main landing commit: 6d7a0acf5 (the f0e75cae sandbox output ref is NOT reachable in origin/main; the quick_fix artifact landed under 6d7a0acf5)
  landed artifact: project/brick-protocol/status/kernel/dogfood/0708j-quick-fix-direct.md
  evidence_root: /Users/smith/.brick/project/brick-protocol/buildings/building-call-0708j-quick-fix-direct-dogfood-repair
  interpretation: quick_fix direct path can produce a scoped sandbox diff and avoid fake-landing.

order_authoring:
  building_id: building-call-0708j-order-authoring-dogfood
  route evidence: confirmed_building_call_request_v1_1 building_case=order_authoring -> lowered_intent chain_preset_ref building-chain-preset:building-call-authoring
  frontier: complete
  evidence_root: /Users/smith/.brick/project/brick-protocol/buildings/building-call-0708j-order-authoring-dogfood
  commit_sha: none (draft/evidence route; no sandbox source diff expected)

clean detached verification:
  verify root: /tmp/brick-verify-0708j-47245
  base: f937d407e35a03418a448000b2bfb27aa65d93b1
  commands: python3 -m compileall -q brick_protocol; check_profile.py --profile building_call_direct_escape; --profile building_call_authoring; --profile building_call_lowering; --profile building_operator_driver0; git diff --check
  rc: 0

proof limits:
  support evidence only; deterministic command_runner dogfood, not real provider quality proof; no source truth, success judgment, quality judgment, or Movement authority.
```

⑤f authoring module Building slice:

```text
building_id: building-call-authoring-0708f
surface: brick_protocol/support/operator/building_call_authoring.py
checker/profile: brick_protocol/support/checkers/profiles/building_call_authoring.yaml
fixtures:
  positive: brick_protocol/support/checkers/fixtures/building_call_authoring/positive_return.json
  negative sequence violation: brick_protocol/support/checkers/fixtures/building_call_authoring/negative_sequence_violation.json
purpose: draft-only validation/normalization for building_call_authoring_return_v1 and the fixed STEP1_SCOPE -> STEP2_BUILDING_INTENSITY -> STEP3_STRUCTURE -> STEP4_PER_BRICK_INTENSITY -> STEP5_AGENT_CANDIDATES sequence.
coverage repair: reroute pass tightened validation to reject unknown top-level fields, scan every declared return field for forbidden draft exposure, and catch embedded/case-varied provider/model/adapter markers.
checker evidence: clean review worktree observed compileall rc=0, git diff --check rc=0, focused ⑤f profiles green, and check_profile.py --all rc=0 with 57/57 profile passes and real red observations=0. building_call_authoring_contract rejects unknown top-level, remaining_delta exposure, forbidden_exposure_scan key, and embedded case-varied exposure probes.
limits: no launch authorization, no lowering, no route/walker integration, no source truth, no success judgment, no quality judgment, no Movement authority. ⑤j now covered by later sandbox dogfood evidence; this prior proof itself still did not launch a Building.
```

---

## 5. ⑥ Route V2 — sealed materialization / checker-first track

### 5.1 Current input

```text
review prompt: project/brick-protocol/status/kernel/route-v2-review-prompt-0708.md
architecture input: /Users/smith/Downloads/brick_route_v2_dev_implementation_architecture_v1.md
```

Route V2는 새 라우터가 아니다.

```text
Agent concern
→ sealed 8 concern_kind validation
→ Link route policy eligibility
→ existing route_materialization / route_replay_plan view
→ gate_state + movement_candidate separation
→ checker green 후에만 walker integration
```

### 5.2 핵심 금지선 / human gate 승인 — 2026-07-08

```text
Smith 승인 2: Route V2를 실제 엔진(walker_kernel)에 통합하는 방향 승인.
조건: R0/R1/R2 green + dogfood 이후에만 walker_kernel 통합 Building을 연다.
현재 즉시 허용: R0 sealed materialization architecture, R1 route_v2 checker/fixtures, R2 route_v2_views.py.
현재 계속 HOLD: route_materialization.py 변경, walker_kernel.py / walker_resume.py 변경, link/* 변경, agent/return_fact.py 변경.
DO NOT create new engine.
DO NOT create new route_scope.py unless later human gate explicitly approves.
DO NOT add new concern_kind.
DO NOT reroute verification_gap.
DO NOT hide factual claims from QA.
DO NOT use hold as Movement.
DO NOT merge Route V2 work into building_call track.
proof limit: 통합 방향 승인은 support evidence only; green/dogfood 전 walker 통합 착수 권한이 아니다.
```

### 5.3 ⑥ 세부 페이즈

| Phase | 이름 | 산출물 | 병렬성 | 상태 |
|---|---|---|---|---|
| ⑥a | 정본 문서 | `route-v2-sealed-materialization-architecture.md` | ⑤와 병렬 가능, 문서 only | ✓ landed `47cf35a4b`; R0 evidence: `project/brick-protocol/status/kernel/route-v2-sealed-materialization-architecture.md` |
| ⑥b | checker fence | `route_v2_sealed_materialization.yaml` + `fixtures/route_v2/**` | ⑥a 이후 병렬 가능, fixtures owner 하나 | ✓ landed `47cf35a4b`; declarative profile pins concern seal / gate-Movement separation / delta-QA facts |
| ⑥c | read-only view builder | `brick_protocol/support/operator/route_v2_views.py` + `check_route_v2_views.py` + dogfood status record | ⑥a/⑥b schema 확정 후 | ✓ landed `134ad9550`; dogfood recorded at `project/brick-protocol/status/kernel/dogfood/0708-route-v2-view-dogfood.md`; ⑥d/⑥e still HOLD |
| ⑥d | route_materialization 확장 검토 | route_replay_plan view/provenance 확장 여부 | reviewed, no code change needed | ✓ review disposition at `project/brick-protocol/status/kernel/route-v2-6d-materialization-review-0709.md`; current route_materialization sufficient as R2 view/provenance input |
| ⑥e | walker integration | walker_kernel/walker_resume integration | design produced, implementation still gated | ◐ design evidence at `route-v2-6e-walker-integration-design-0709.md`; implementation remains HOLD pending explicit declared Building/proof |

⑥c R2 read-only view builder candidate:

```text
worktree: /tmp/brick-route-v2-views-0708c
landed commit: 134ad9550457ae70faac71930cfe0488de5d8f48
surfaces:
  - brick_protocol/support/operator/route_v2_views.py
  - brick_protocol/support/checkers/check_route_v2_views.py
  - brick_protocol/support/checkers/profiles/route_v2_sealed_materialization.yaml
  - brick_protocol/support/checkers/check_profile.py
  - brick_protocol/support/checkers/check_package_path_admission.py
  - brick_protocol/support/checkers/module_registry.yaml
  - brick_protocol/support/checkers/profiles/core.yaml
observed behavior:
  - implementation_gap renders a read-only materialization view over existing route_materialization.
  - verification_gap remains non-reroute and not route-policy eligible.
  - gate_state and movement_candidate are separate projection fields; no Movement is authored.
  - delta-QA factual fields made_changes/changed_files/diff_refs/evidence_refs are preserved.
  - forbidden success/quality/Movement/route_target keys are rejected.
forbidden surfaces untouched:
  - route_materialization.py
  - walker_kernel.py / walker_resume.py
  - brick_protocol/link/**
  - brick_protocol/agent/return_fact.py
  - route_scope.py / route_v2_engine.py
proof:
  - python3 -m compileall -q brick_protocol
  - python3 brick_protocol/support/checkers/check_route_v2_views.py
  - python3 brick_protocol/support/checkers/check_profile.py --profile route_v2_sealed_materialization
  - python3 brick_protocol/support/checkers/check_profile.py --profile core
proof limits:
  support evidence only; not source truth, not success judgment, not quality judgment, not Movement authority, not walker integration approval.
```

⑥c Route V2 read-only view dogfood — 2026-07-09 KST:

```text
dogfood record: project/brick-protocol/status/kernel/dogfood/0708-route-v2-view-dogfood.md
observed implementation_gap:
  eligible=true; requested_route_scope=implementation_only; materialization_view.materialized=true; gate_state=paused; movement_candidate=reroute; delta_qa_fact preserved.
observed verification_gap:
  non_reroute=true; eligible=false; match_state=non_reroute_concern_kind; materialization_view=null; gate_state=held_for_coo_review; delta_qa_fact preserved.
forbidden key probes:
  success, quality, movement, movement_choice, route_target rejected before rendering.
not touched:
  route_materialization.py, walker_kernel.py, walker_resume.py, link/**, agent/return_fact.py, route_scope.py, route_v2_engine.py.
proof limit:
  support evidence only; not source truth, not success judgment, not quality judgment, not Movement authority, not walker integration approval.
next gate:
  ⑥d/⑥e human-gate packet prepared at project/brick-protocol/status/kernel/route-v2-human-gate-packet-0709.md.
  Smith/human approval is still required before any route_materialization or walker integration Building.
```

⑥d/⑥e human-gate packet — 2026-07-09 KST:

```text
packet: project/brick-protocol/status/kernel/route-v2-human-gate-packet-0709.md
purpose: prepare Smith/human decision before any held ⑥d route_materialization extension or ⑥e walker integration Building.
state: held_for_human_gate; not implementation approval; not Movement; not success/quality judgment.
recommended candidate: ⑥d route_materialization review first, then ⑥e walker integration only after ⑥d evidence is green or explicitly deemed unnecessary.
not opened by the packet: route_materialization.py changes, walker_kernel.py / walker_resume.py changes, link/** changes, agent/return_fact.py changes.
```

⑥d/⑥e human-gate approval — 2026-07-09 KST:

```text
approval: project/brick-protocol/status/kernel/route-v2-human-gate-approval-0709.md
Smith decision: "휴먼게이트 너의 의견대로한다."
interpreted option: Option B — open ⑥d route_materialization review first; open ⑥e walker integration only after ⑥d evidence is green or explicitly unnecessary.
next Building candidate: route-v2-6d-route-materialization-review-0709
still held: immediate walker_kernel.py / walker_resume.py implementation, link/** changes, agent/return_fact.py changes, new route_scope.py, new route_v2_engine.py.
proof limit: support evidence only; not Movement, not implementation, not success/quality judgment.
```

⑥d route_materialization review — 2026-07-09 KST:

```text
review: project/brick-protocol/status/kernel/route-v2-6d-materialization-review-0709.md
observed: implementation_gap materializes with link_decision_packet + link_row provenance; verification_gap remains non-materialized disposition_required even when replay plan is supplied.
negative probes: success_judgment, support_chosen_movement, provider_endpoint, and agent: author_ref rejected.
disposition: route_materialization.py sufficient as-is for R2 -> ⑥e design input; no code change warranted in ⑥d.
next Route V2 candidate: ⑥e walker integration design Building.
still not proven: walker integration behavior, automatic repair/replay execution.
```

⑥e walker integration design — 2026-07-09 KST:

```text
design: project/brick-protocol/status/kernel/route-v2-6e-walker-integration-design-0709.md
recommended shape: SHAPE A read-only advisory overlay.
seam: append dynamic_walker_evidence.route_v2_view_observations as non-binding sibling evidence after walker classification/recording; do not feed walker control flow.
live-code correction: route_policy is not currently direct walker input, so ⑥e must use declared/proven policy input or record absent/blocked; support must not silently load a default policy.
recording correction: reroute_adoption_record and hold_record are contract-derived closed shapes; do not nest Route V2 view inside them unless recording contracts/checkers are explicitly extended.
implementation state: HOLD; requires explicit declared Building/worktree and negative probes before touching walker_kernel.py/walker_resume.py.
still not proven: runtime walker integration, resume read-back parity, exact checker profile home, automatic repair/replay execution.
```

### 5.4 병렬 전략

Because active ⑤ was launched in the live checkout, new parallel Route V2 work must use sandbox/worktree dispatch.

Parallel lanes:

```text
Lane R0 — Route V2 canonical doc
write_scope:
  - project/brick-protocol/status/kernel/route-v2-sealed-materialization-architecture.md

Lane R1 — Route V2 checker fence
write_scope:
  - brick_protocol/support/checkers/profiles/route_v2_sealed_materialization.yaml
  - brick_protocol/support/checkers/fixtures/route_v2/**

Lane R2 — Route V2 view builder
write_scope:
  - brick_protocol/support/operator/route_v2_views.py
condition:
  - R0/R1 schema names fixed first, or R2 uses only documented schema from dev architecture v1
```

Serialize/HOLD lanes:

```text
route_materialization.py 변경
walker_kernel.py / walker_resume.py 변경
link/* 변경
agent/return_fact.py 변경
```

---

## 6. 병렬 운영 원칙

```text
1. Active ⑤ building은 현재 live checkout에 변경을 만들었으므로, 중복 발사 금지.
2. 앞으로 새 병렬 빌딩은 run_customer_building_in_sandbox / worktree sandbox 경로만 사용.
3. 병렬은 write_scope가 완전히 분리된 경우에만.
4. 병렬 착지는 직렬. push/merge는 한 줄로.
5. 토큰 절약: building status는 inbox 이벤트 파일명만 먼저 보고, 새 brick_returned/gate_passed/intervention/building_finished 때만 좁게 읽는다.
```

Current cheap polling target:

```text
project/brick-protocol/status/inbox/*building-call-v11-cleanup-first-0708a*.json
```

Event stages to watch:

```text
brick_received
brick_returned
gate_passed
intervention_required
building_finished
```

---

## 7. ⑩ 후속 CLEANUP / customer UX layer — ⑤/⑥ 이후 실행

Status: planned after current Building Call / Route V2 slices. 이 절은 source truth·성공/품질·Movement 권한이 아니라 후속 Building 운영지도다.

### 7.1 사용자 요구 재분해

```text
목표: 현재 작업(⑤/⑥)을 닫은 뒤, COO 발주 체인·스킬체인·디렉토리 중복·루트/프로젝트 vessel·고객 UX 층을 별도 cleanup phase로 정리한다.
핵심 기준: 작은 일은 direct preset 후보로 보되, 구조/여러 축/admission/checker/경로 이동이 걸리면 Building으로 보낸다.
COO 역할: 운영/판단/Building 조율만 한다. 실제 이동·삭제·구현·검증은 declared Building/sandbox로 진행한다.
```

### 7.2 live tree 근거

```text
brick_protocol/brick/building_plans/ exists. It is load-bearing: onboard.py, run.py, coo_operating_chain.py, orchestration_packet.py, check_package_path_admission.py, building_plan_graph_check, adapter_capability checks, and profile YAMLs reference brick_protocol/brick/building_plans.
brick_protocol/brick/templates/blocks/ exists. Current support/operator direct references were not observed; presets mention blocks/motifs. Treat as cleanup/archive candidate, not source deletion by assumption.
brick_protocol/brick/templates/shapes/ exists and is load-bearing: catalog/shapes are consumed by template catalog/checkers/operator readers. Do not delete as "duplicate" without a dedicated Building proving replacement.
brick_protocol/brick/templates/tasks/ exists and already lives under the Brick axis template surface. Keep unless a later Building proves better naming/placement.
brick_protocol/brick/templates/skills/ exists as ship copy. agent/skills/ is the Agent-axis source. APPLY-LIST defines agent -> template -> live sync. Drift observed for brick-task-author and building-coordination, so cleanup is synchronization/repackaging, not blind deletion.
project/brick-protocol/ exists as the current dogfood project vessel carrying buildings/status/GOAL. It should not be conflated with product source, but immediate removal would break active evidence/status.
project-creation already exists: brick_protocol/agent/skills/project-creation/SKILL.md and brick_protocol/support/operator/project_creation.py. progress projection exists: brick_protocol/support/operator/progress_projection.py. Missing piece is customer-facing UX flow tying install -> project creation -> buildings/status/progress board -> project definition.
```

### 7.3 ⑩ 세부 페이즈

| Phase | 이름 | 산출물 | 라우팅 | 상태/주의 |
|---|---|---|---|---|
| ⑩a | cleanup scope / invariants doc | `project/brick-protocol/status/kernel/cleanup-scope-invariants-0709.md` | docs-simple-review 가능 | ✓ doc prepared; shapes/building_plans/tasks/skills/project vessel no-delete/no-move invariants recorded |
| ⑩b | blocks 정리 | `project/brick-protocol/status/kernel/blocks-retained-map-0709.md` | docs-only map done | ✓ map prepared: 8 retained / 0 archive / 0 supersede / 0 delete. 모든 block related_presets 실존, runtime reader 0, admission checker가 corpus를 admit. 삭제/이동 불필요 |
| ⑩c | building_plans 위치 결정 | `project/brick-protocol/status/kernel/building-plans-location-decision-0709.md` | docs decision complete | ✓ KEEP for now; no move/delete/archive; future migration requires declared Building with reader/checker/admission/profile proof |
| ⑩d | skills ship-copy 정리 | `project/brick-protocol/status/kernel/skills-ship-copy-drift-map-0709.md` | docs-only drift map done | ✓ map prepared: common 7, identical 5, real drift candidate `building-coordination`, checker/pin overlay candidate `building-sizing-method`, agent-only maybe-ship candidates recorded, `.DS_Store` residue observed |
| ⑩e | COO 발주 스킬체인 정합 | `project/brick-protocol/status/kernel/coo-order-chain-consistency-0709.md` | docs-only consistency map done | ✓ map prepared: Quick Path policy aligned across brick-task-author/building-call-authoring/building_call.py/building_call_menus.py; watch items recorded for building-coordination ship-copy drift, brick-task-author selected_* example context, building-sizing-method checker overlay |
| ⑩f | customer UX layer | `project/brick-protocol/status/kernel/customer-ux-layer-design-0709.md` | design produced | ◐ design doc landed; core gap = missing `brick project`/`brick progress` CLI tie over existing create_project/progress_projection; implementation pending declared Building |
| ⑩g | `project/brick-protocol` dogfood vessel 분리 | `project/brick-protocol/status/kernel/dogfood-vessel-separation-human-gate-0709.md`; `project/brick-protocol/status/kernel/dogfood-vessel-separation-approval-0709.md` | human gate closed | ✓ Smith approved Option A KEEP+clarify; no move/delete/archive; future split/migration remains HOLD until a later explicit human-gated Building |

⑩a cleanup scope / invariants — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/cleanup-scope-invariants-0709.md
measured: building_plans, templates/blocks, templates/shapes, templates/tasks, templates/skills, agent/skills, project/brick-protocol, project_creation, progress_projection.
recorded invariants: no blind delete, no simple building_plans git-mv, no shapes deletion, no templates/skills blind delete, no project vessel move before human gate, no cleanup mixed into Route V2 ⑥d/⑥e.
next cleanup candidate: ⑩b blocks retained/archive/superseded map; alternate ⑩d skills ship-copy drift map if COO order-chain consistency is prioritized.
proof limit: support evidence only; no cleanup implementation completed.
```

⑩b blocks retained/archive/superseded map — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/blocks-retained-map-0709.md
measured: 8 block files, related_presets integrity vs presets/*.md, inbound ref scan, admission checker branch.
decision: RETAIN 8, ARCHIVE 0, SUPERSEDE 0, DELETE 0.
evidence: every block related_preset resolves to an existing preset (0 dangling); no operator/CLI/materializer reads blocks; check_package_path_admission.py admits the corpus dir + slugged docs.
result: no block cleanup Building needed now; block removal/rename would be a coordinated admission+checker Building, not a direct docs edit.
next cleanup candidate: ⑩d skills ship-copy drift map or ⑩e COO order-chain consistency.
proof limit: support evidence only; no block file changed.
```

⑩d skills ship-copy drift map — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/skills-ship-copy-drift-map-0709.md
measured: agent/skills tracked SKILL.md=18, templates/skills tracked SKILL.md=7, common=7, template-only=0, agent-only=11.
byte-identical common skills: 5 (brick-task-author, make-a-brick, make-a-gate, make-an-agent, task_intake).
drift candidates: building-coordination (template missing agent-source hold disposition vocabulary reference); building-sizing-method (template checker compatibility overlay, do not blind sync).
agent-only maybe-ship candidates: building-call-authoring, evidence-verification, protocol-boundary-watch, project-creation.
tracked residue observed: brick_protocol/agent/skills/.DS_Store.
next cleanup candidate: ⑩d-repair-1 Building or ⑩e COO order-chain consistency design.
proof limit: support evidence only; no skill file changed.
```

⑩e COO order-chain consistency map — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/coo-order-chain-consistency-0709.md
observed aligned policy: direct_preset escape hatch only for quick_check/quick_fix with direct_preset_admission + fast_confirm; order_authoring default; human_gate_first for critical/destructive/credential/high-impact cases.
positive surfaces: brick-task-author source+ship-copy, building-call-authoring source, building_call.py, building_call_authoring.py, building_call_menus.py.
watch items: building-coordination ship-copy drift; brick-task-author selected_* example context needs focused classification; building-sizing-method template checker overlay must not be blind-synced.
next cleanup candidate: ⑩f implementation Building request prepared; next operational step is declared ⑩f Building intake/run, ⑩g Smith decision record, or optional cleanup-10e-order-chain-consistency-0709a Building.
proof limit: support evidence only; no skill/prompt/hook/projection changed.
```

⑩c building_plans location decision — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/building-plans-location-decision-0709.md
decision: KEEP for now.
measured surface: brick_protocol/brick/building_plans/ has 4 fixture/example plan files.
reason: current refs from package path admission, building_plans_boundary_sweep, core/link_routing_behavioral/building_operator_driver0 profiles, onboarding/quickstart docs, onboard.py, run.py, coo_operating_chain.py, and orchestration_packet.py make this path load-bearing.
forbidden shortcut: no simple git mv under templates; no delete/archive now.
future migration: declared Building only, with reader/checker/admission/profile/docs migration and clean detached --all proof.
remaining_delta: ⑩f implementation Building; ⑥e/⑦ Smith implementation approval + declared route-walker Building run/landing; optional ⑩e repair candidate.
closed_delta: ⑩g Smith decision recorded as Option A KEEP+clarify; no move/delete/archive.
```

⑩f customer UX layer design — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/customer-ux-layer-design-0709.md
result: design-first note; ⑩f is not greenfield.
live-code finding: pyproject.toml [project.scripts] brick entry EXISTS (0618 doc "no scripts" is stale); create_project and progress_projection backends EXIST but have NO brick CLI caller.
core gap: brick CLI lacks `project new/list/show` and `progress` subcommands, so vessel create + progress board are internal-API-only.
design: thin CLI tie only (subcommand -> existing support verb, no vessel/board logic in CLI); non-TTY refuses to auto-stamp; progress read-only unless --write; secret masking parity.
checker plan: CLI orchestrator purity, non-TTY stamp safety, progress read-only, secret masking, keep project_declaration/intake_project_vessel green.
implementation state: pending declared design-build Building in worktree sandbox; no code changed.
still not proven: ⑩f CLI code, charter-fill prompt-level UX, build->progress auto-refresh decision, 0618 first-green funnel impl status.
```

⑩g dogfood vessel separation human-gate packet — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/dogfood-vessel-separation-human-gate-0709.md
live vessel facts: project/brick-protocol has README.md + project.json + PROGRESS.md, 58 building roots, 94 status/kernel files, and 929 status/inbox event files.
classification: active declared dogfood vessel, not product/source root and not stray clutter.
recommended gate choice: Option A KEEP + clarify wording only; no filesystem migration now.
forbidden shortcut: no move/delete/archive while active GOAL/status/building/inbox evidence lives here.
other options: Option B design split map only; Option C high-risk migration Building only after explicit approval; Option D delete/archive rejected.
approval: project/brick-protocol/status/kernel/dogfood-vessel-separation-approval-0709.md
state: closed_as_keep_and_clarify; Smith approved Option A KEEP+clarify. No move/delete/archive/split/migration is approved now; any future physical split remains a separate human-gated migration Building.
```

⑩f implementation Building request — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/customer-ux-10f-implementation-building-request-0709.md
building_candidate: customer-ux-10f-cli-tie-0709
recommended_chain_preset_ref: building-chain-preset:brick-protocol-engine-feature-hard
route_family_candidate: preset_guided_graph
scope: implement thin `brick project new/list/show` and `brick progress [--write]` CLI tie over existing project_creation/progress_projection, with checker coverage.
direct_preset: rejected (multi-file support-code/checker/docs, customer-facing CLI, non-TTY and secret-safety behavior).
state: ready_for_declared_building_intake; no code changed by this packet.
```

⑥e/⑦ route-walker implementation Building request — 2026-07-09 KST:

```text
doc: project/brick-protocol/status/kernel/route-walker-6e-7-implementation-building-request-0709.md
building_candidate: route-walker-6e-7-advisory-view-0709
recommended_chain_preset_ref: building-chain-preset:brick-protocol-engine-feature-hard
route_family_candidate: preset_guided_graph
scope: implement SHAPE A read-only advisory route_v2_view_observations beside dynamic_walker_evidence, without changing walker control flow, Link Movement, route targets, reroute/hold record contracts, AgentFact, Link resources, or concern_kind vocabulary.
direct_preset: rejected (walker runtime seam, route/Movement boundary, resume parity, checker coverage).
state: held_for_smith_implementation_approval; no code changed by this packet.
```

### 7.4 direct preset vs Building 판정 규칙

```text
direct preset 후보:
  - 문서-only, 단일 표면, 경로/admission/checker 영향 없음
  - quick_check / quick_fix 범위
  - direct_preset_admission + fast_confirm 필요

Building 필수:
  - directory move / git mv / package path admission 변경
  - checker/profile/fixture/module_registry 동시 변경
  - Agent skill source vs ship copy 동기화
  - prompt/hook/projection 3면 정합
  - project vessel / customer UX / first-run workflow
  - human gate 또는 root/status/evidence migration
```

### 7.5 금지/보류

```text
- shapes 삭제 금지: 현재 load-bearing.
- building_plans 이동을 단순 정리로 처리 금지: 여러 reader/checker/admission 경로를 동시 갱신해야 한다.
- templates/skills blind delete 금지: agent/skills 정본과 ship/live 사본의 3면 동기화 계약이 있다.
- project/brick-protocol 즉시 삭제/이동 금지: 현재 GOAL/status/building evidence vessel이다. 분리는 human gate 후 별도 Building.
- 과거 설계문서 삭제 금지: 필요하면 archive/superseded 표시.
- cleanup을 ⑤/⑥ active work와 섞지 말 것.
```

### 7.6 proof limits

```text
이 ⑩ 절은 cleanup 작업을 완료하지 않는다.
디렉토리 이동, 스킬 동기화, UX 구현, project vessel 분리는 아직 not_proven이다.
완료 증거는 각 Building의 changed_files, checker profile, clean worktree --all, GOAL/status update, 그리고 필요한 human gate 기록으로만 인정한다.
```

---

## 8. 다음 실행 순서

Immediate:

```text
A. Active ⑤ building-call-v11-cleanup-first-0708a closure 추적: complete frontier observed.
B. ⑤b/⑤c 변경물 검증/commit/push: done at 28cfda632.
C. 현재 이미 시작된 ⑤d menus/API 수습까지만 직접 마감 가능. 그 이후 ⑤e~⑤j와 Route V2 R0/R1/R2는 declared Building/sandbox로 진행.
```

Parallel candidate after active ⑤ is stable or via sandbox immediately:

```text
R0 Route V2 canonical doc building
R1 Route V2 checker fence building
```

Then:

```text
⑤d menus/API
⑤e 발주서작성 preset/Brick/Agent
⑤f authoring module
⑤g lowering layer
⑤h direct escape hatch
⑤i docs/examples
⑤j dogfood (observed; quick_fix artifact landed in origin/main as `6d7a0acf5`; sandbox output ref `f0e75cae`는 도달 불가)
⑥c route_v2 read-only view builder + read-only view dogfood
⑩a cleanup scope / invariants doc — prepared at `project/brick-protocol/status/kernel/cleanup-scope-invariants-0709.md`
⑩b blocks retained/archive/superseded map — done at `project/brick-protocol/status/kernel/blocks-retained-map-0709.md` (8 retained, 0 archive/supersede/delete)
⑩d skills ship-copy drift map — done at `project/brick-protocol/status/kernel/skills-ship-copy-drift-map-0709.md`
⑩e COO order-chain consistency map — done at `project/brick-protocol/status/kernel/coo-order-chain-consistency-0709.md`
⑩c building_plans decision — done at `project/brick-protocol/status/kernel/building-plans-location-decision-0709.md` (KEEP for now; no move/delete/archive). ⑩f customer UX design — done at `project/brick-protocol/status/kernel/customer-ux-layer-design-0709.md` (core gap = missing brick project/progress CLI tie; implementation pending). ⑩g dogfood vessel separation — gate closed by `project/brick-protocol/status/kernel/dogfood-vessel-separation-approval-0709.md` as Option A KEEP+clarify; no move/delete/archive. Remaining: declared ⑩f implementation Building run/landing, ⑥e/⑦ Smith approval + declared route-walker Building run/landing, optional cleanup-10e-order-chain-consistency-0709a
⑥d route_materialization review — done at `project/brick-protocol/status/kernel/route-v2-6d-materialization-review-0709.md` (no code change needed); ⑥e walker integration design produced at `project/brick-protocol/status/kernel/route-v2-6e-walker-integration-design-0709.md`; implementation remains HOLD pending explicit declared Building/proof
```

---

## 9. Proof limits

```text
- This unified GOAL is support evidence only.
- It does not prove current active building success.
- It does not approve Route V2 implementation.
- It does not authorize walker/run/link/AgentFact changes.
- It records current operating plan and phase boundaries only.
```

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
GOAL ⑤/⑥ updates: 6100e3eb6, fb765bdc3, 197b7df51, 69988d815, 28cfda632
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
| ③ | 캐스팅 전환 | ✓ | fable5 기본 퇴장, opus/fugu/codex/gemini 역할 재정렬 |
| ④a | C1 import canonicalization | ✓ | `af60198cb` 포함, origin/main 착지 |
| ④b | C2 physical root unification | ✓ | `7b99b8f7f`, `brick_protocol/*`, top-level import 실패 확인 |
| ④c | C3 문서/human gate | 부분 완료 | C3 상태문서 착지. BRICK-CONSTITUTION 물리 루트 조항은 Smith human gate 전까지 HOLD |
| ⑤ | 발주서/빌딩콜 v1.1 | 부분 착지 | `building-call-v11-cleanup-first-0708a` frontier complete 관측. ⑤b/⑤c tracked cleanup slice는 `28cfda632`로 push. ⑤d~⑤j 남음 |
| ⑥ | Route V2 sealed materialization | ☐ 준비 | prompt/GOAL 반영 완료. ⑥a/⑥b 병렬 가능, ⑥d/⑥e HOLD |
| ⑦ | route/walker integration | HOLD | checker green + human gate + route_materialization view 안정 후에만 |
| ⑧ | 발주서작성 preset/Agent/menu/lowering | 대기 | ⑤d 수습 후 ⑤e~⑤j는 COO 직접 구현 금지, declared Building/sandbox로 진행 |
| ⑨ | dogfood/골 closure | 대기 | quick direct + order_authoring + Route V2 view/checker 증거까지 모은 뒤 closure |

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
| ⑤g | lowering layer | `building_call.py`, `building_call_cases.yaml`, confirmed-only lowering, provenance | ☐ |
| ⑤h | direct escape hatch | triage/admission/fast_confirm, quick_fix/quick_check만 direct | ☐ |
| ⑤i | docs/skill examples | brick-task-author/building-call Quick Path, 4개 worked examples, 메뉴얼 규칙 | ☐ |
| ⑤j | dogfood | quick_check direct, quick_fix direct, order_authoring path 각 1회 증거 | ☐ |

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
- ⑤f/⑤g/⑤h remain undone and must proceed through declared Building work.
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
limits: no launch authorization, no lowering, no route/walker integration, no source truth, no success judgment, no quality judgment, no Movement authority. ⑤g/⑤h/⑤i/⑤j remain out of scope.
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
| ⑥a | 정본 문서 | `route-v2-sealed-materialization-architecture.md` | ⑤와 병렬 가능, 문서 only | ☐ |
| ⑥b | checker fence | `check_route_v2_concern_kind_seal.py`, `check_route_v2_gate_movement_shape.py`, `check_route_v2_delta_qa_fake_landing.py`, `check_route_v2_no_new_route_scope.py`, `check_route_v2_no_walker_touch.py` + fixtures | ⑥a 이후 병렬 가능, fixtures owner 하나 | ☐ |
| ⑥c | read-only view builder | `brick_protocol/support/operator/route_v2_views.py` | ⑥a/⑥b schema 확정 후 | ☐ |
| ⑥d | route_materialization 확장 검토 | route_replay_plan view/provenance 확장 여부 | HOLD, human gate | ☐ |
| ⑥e | walker integration | walker_kernel/walker_resume integration | HOLD, 최고위험 | ☐ |

### 5.4 병렬 전략

Because active ⑤ was launched in the live checkout, new parallel Route V2 work must use sandbox/worktree dispatch.

Parallel lanes:

```text
Lane R0 — Route V2 canonical doc
write_scope:
  - project/brick-protocol/status/kernel/route-v2-sealed-materialization-architecture.md

Lane R1 — Route V2 checker fence
write_scope:
  - brick_protocol/support/checkers/check_route_v2_*.py
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

## 7. 다음 실행 순서

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
⑤j dogfood
⑥c route_v2 read-only view builder
⑥d/⑥e only after human gate
```

---

## 8. Proof limits

```text
- This unified GOAL is support evidence only.
- It does not prove current active building success.
- It does not approve Route V2 implementation.
- It does not authorize walker/run/link/AgentFact changes.
- It records current operating plan and phase boundaries only.
```

# W1 Authoring 설계리뷰 — COO Record 0709

Date: 2026-07-09 KST.
Parent goal: `GOAL/03-remaining-frontier-goal-0709.md` W1 (#1 authoring 제품층 구현).
Reviewed artifact: `buildings/building-call-authoring-architecture-plan-0709a` (planning Building, code 0줄).
Proof limit: support evidence only; not source truth, not success/quality judgment, not Movement authority. 이 리뷰는 관측·COO 판정 기록이며 설계 품질을 승인하지 않는다.

## Brick / Agent / Link 귀속

```text
Brick: W1 설계리뷰 = authoring architecture plan이 구현 발주 가능한 형태로 닫혔는지 관측하고, load-bearing open decision의 처분을 COO gate로 잡는다.
Agent: COO가 evidence-shape 렌즈로 직접 관측(설계는 타 세션 Building 산출이라 자기검증 아님).
Link: 이 리뷰의 Movement는 forward가 아니라 held — A/B 구조경로 채택이 human gate에서 미결이기 때문. gate 해소 전 dev fan-out 발주 금지.
Support: check_profile.py, git worktree, status/kernel 문서는 evidence/support only.
```

## §Structure pass — 발주요구 6항목 (관측: matched)

```text
phases:            matched — P0 scope → P1 intensity → P2 structure ladder → P3/P4 → P5 confirmation handoff
decision points:   matched — DP1 triviality → DP2 design → DP3 COO gate → DP4 fan-out width → DP5 fan-in QA → DP6 resume
data shape 후보:   matched — Candidate A/B/C + structure_class enum + launch_confirmation_state 값 후보
examples:          matched — E1 linear / E2 design_then_gate / E3 conditional_fanout / E4 resume_tail / E5 human_gate_first
forbidden exposures: matched — preset id / agent internals / route·walker names / Link Movement authoring 금지
3앵커 통합:        matched — building_call_request_v1_1(draft 개념) / held_for_coo_review(기존 fail-close 재사용) / confirmed_(lowering 계약)
grounding:         code 좌표 grounded — building_call.py:17/111/304-314, building_call_authoring.py:18/48
```

## §Gap pass — load-bearing open decisions (관측)

```text
G1. draft-stage kind 'building_call_request_v1_1'를 코드 상수로 materialize할지 — 현재 grep상 코드 상수 없음, 라이프사이클 개념만.
G2. C(COO-gate)/D(N-fan) 구조가 confirmed-request를 통과할 경로: Candidate A(기존 topology preset 재사용) vs B(선언 structure_plan 필드) — 미결.
G3. DEVELOPMENT lane fan-out N cap — DESIGN은 mutually-blind 3으로 측정됨, DEV는 미증명.
관측 note: G1/G3은 G2 채택에 종속되어 함께 정해진다.
```

## COO 판정

### cap 정책 — 확정 (Smith 0709)

```text
결정: DEV fan-out 폭을 하드코딩하지 않는다. 파라미터 N으로 열어둔다.
gate: fan-out 실행 직전에 held_for_coo_review hold를 강제한다.
확정 주체: 그 hold 지점에서 COO가 실제 서브스코프 수를 보고 N을 확정한다.
정합: 설계 DP4(disjoint write fence)·DP5(단일 fan-in wait-all + closure_transition_target_policy)와 맞물려 안전.
→ G3은 "cap 미정 리스크"가 아니라 "실행시점 COO 확정" 구조로 닫힘.
```

### 구조경로 G2 — 채택 CONFIRMED = Candidate B (Smith 0709 human gate 통과)

```text
채택: Candidate B (선언 structure_plan). Smith 0709 승인.
근거: 이 골이 겨냥한 병 = preset-first anchoring. A는 매칭 preset 부재 시 근사 preset을 강제해 anchoring을 재유입 → 목적 부분 달성. B는 conditional·N-width를 그대로 표현 → anchoring 정면 제거 = 골 목적 정합.
채택된 비용/제약 (dev 빌딩이 반드시 지켜야 함):
 - confirmed_building_call_request_v1_1 에 OPTIONAL structure_plan 필드 추가 {nodes, edges, coo_gate_edge, fan_out_groups(N), fan_in_groups(converge_on, closure_transition_target_policy), reroute_budgets}.
 - lowering(building_call.py) 확장 + 전용 checker(fan-out 불변식·held_for_coo_review 일관성) 추가.
 - 기존 fail-close(held_for_coo_review는 lowering 차단) 약화 금지 — 재사용만.
 - provider-neutral 유지. casting / movement_choice / route_target / launch_authorization 노출 금지.
 - structure_plan 은 OPTIONAL — 미지정 시 기존 building_case→chain_preset_ref 경로 그대로(하위호환).
기각된 대안: A(anchoring 재유입), A→B 단계적(Smith가 B 직행 선택).
```

## 처분

```text
Movement candidate: forward.
이유: cap 정책 확정 + G2 human gate 통과(B 채택)로 dev fan-out write-scope 축이 규정됨.
Next boundary: W1 dev 구현 Building 발주 — Candidate B(structure_plan) 경로. brick-task-author 스킬로 발주서 작성, building-sizing-method로 모양 사이징.
Not proven: 설계의 의미적 적합성, 미래 Building 실행 정합성, structure_plan payload의 lowering 런타임 거동(코드 미실행) — dev Building이 실측으로 닫는다.
```

# 공통 Route/HOLD 아키텍처 설계서 — COO 피드백 (codex 개정용, 0708)

> C3 status note: C2 import-unify is now landed on origin/main (`7b99b8f7f`, --all rc=0). Route v2 remains HOLD until 발주/operator-safe launch envelope work is closed; do not merge route policy work into the 발주 track.


대상 문서: `BRICK_common_route_architecture.md` (21장, §S)
검증: 발주 아키텍처 Explore 코드 대조에서 파생 확인 @ C1 (`af60198cb`). 원장 §S·§T-정정 동반.
성격: **문서 개정 요청. codex가 이 피드백으로 route 설계서를 고친다.**

---

## 총평

**방향은 옳다** — 모든 레인(dev/design/closure/QA)이 route를 직접 치지 않고 `route_concern_evidence`만 발화, Link route policy가 `route_scope`를 확정, support/walker는 실행만, 근거 부족하면 HOLD. QA 반려 시 fan-in cohort 전체 재실행(토큰 낭비)의 구조 답안으로 정확.

**그러나 발주 아키텍처 문서와 같은 병 — "새로 만든다"는 전제가 틀렸다.** route_scope와 concern route 매핑이 **이미 리포에 더 성숙하게 존재**하는데, 설계서는 이를 인용하지 않고 신규 구현으로 제안한다. 얹는 게 아니라 평행 재구현.

개정 방향 한 줄: **route_scope를 신규가 아니라 기존 `route_materialization.py` 확장으로 재정위**하고, concern_kind는 봉인 8종과 정합.

---

## 시공 전 필수 해소 3건

### 1. route_scope는 이미 존재 — 신규 아닌 확장으로 재정위 (§6, §13 대상)

**기존 실물 (설계서 미언급):**
- `brick_protocol/support/operator/route_materialization.py:78` `materialize_transition_concern_disposition` — concern → route_scope 매핑을 **이미 실행**
- `route_materialization.py:305` `route_replay_plan` — 설계서 route_scope의 live_retry/carry_forward/replay 개념을 **이미 담은 구조**
- `brick_protocol/support/operator/route_materialization.py:457-461` — author_ref 금지 프리픽스(support:/agent:/provider:) **이미 봉인**(link/spec 단일소스)
- `brick_protocol/link/route_policies/basic_qa_repair.yaml:38-54` — owner_axis=Link, concern_kind→requested_route_scope 매핑, **verification_gap 의도적 제외 명시**

**문제:** 설계서 §6 route_scope(신규 `brick_protocol/link/route_scope.py`) + §13 walker 실행 + §18 체커들(check_route_scope_authority 등)이 위 기존 구현과 **중복 재구현**. 기존이 더 성숙(literal-match state machine, link_decision_packet evidence view).

**개정 요청:**
- 설계서 §6 route_scope의 필드(repair_target_refs, live_retry_refs, carry_forward_refs, affected_qa_refs, carry_forward_qa_refs, recompute_join_refs, replay_mode)를 **기존 route_replay_plan(brick_protocol/support/operator/route_materialization.py:305) 구조에 매핑**해서 제시. 무엇이 신규 필드이고 무엇이 기존 필드 재명명인지 표로.
- §18 check_route_scope_authority가 기존 author_ref 봉인(route_materialization.py:457-461)과 **중복 아님**을 증명하거나 통합.
- basic_qa_repair.yaml의 verification_gap 제외를 설계서 §10.2가 재발명 말고 **인용**.

### 2. concern_kind 봉인 8종과 정합 (§5, §8 대상 — 발주 문서와 공유 문제)

**봉인 실물 (3중 단일소스):** `brick_protocol/agent/return_fact.py:10-21` 8종(design_gap·implementation_gap·upstream_gap·boundary_mismatch·insufficient_input·replay_needed·verification_gap·unknown) + `transition-concern-return.yaml:10` + `basic_qa_repair.yaml`. `validate_transition_concern_evidence`가 enum 밖 fail-closed.

**문제:** 설계서 §8 concern_kind 목록(implementation_gap·verification_gap·design_gap·insufficient_input·upstream_gap·integration_gap·boundary_mismatch·qa_defect·closure_gap·budget_gap·human_gate_required·provider_gap = 12종)이 봉인 8종과 다름. 신규 6종(integration_gap·qa_defect·closure_gap·budget_gap·human_gate_required·provider_gap) 추가, replay_needed·unknown 누락.

**개정 요청:**
- 설계서 §5.2/§8의 concern_kind를 봉인 8종 기준으로 재정렬. 신규 필요분만 **명시적 확장 절차**(return_fact.py + transition-concern-return.yaml + basic_qa_repair.yaml + validate + 체커 동시 개정)로. fact-class shape 변경 = human gate 명시.
- 발주 아키텍처 문서 §4.7/4.8/4.9와 **concern_kind 목록을 하나로 통일**(두 문서가 같은 enum 써야 함).

### 3. delta QA가 fake-landing 방어를 안 깨뜨림 (§14 대상 — 발주 문서 Blind Pack과 연동)

**충돌 실물:** `brick_protocol/brick/templates/bricks/code-attack-qa/brick.md:43-48` — QA 핵심 임무 = upstream의 self-reported made_changes/changed_files를 실제 diff와 대조 공격(0702 fake-landing 방어).

**문제:** 설계서 §14 delta QA("reason_refs·changed_refs 밖은 열지 마라")는 diff 밖 회귀·상호작용 결함을 못 볼 뿐 아니라, 발주 문서 Blind Pack(producer 주장 은닉)과 결합하면 fake-landing 대조 임무가 깨질 수 있다.

**개정 요청:**
- delta QA가 **좁혀도 producer 주장-diff 대조(fake-landing 방어)는 유지**됨을 증명. 또는 머지 직전 빌딩은 full-QA 백스톱 정책 추가(기존 §S 4핀 중 하나).
- 발주 아키텍처 Blind Pack 세분화(verdict 은닉 / 사실주장 노출)와 정합.

---

## 그 외 관찰

- **자동화 상한 (§10, §11)**: `walker_fan_in.py:279-288` 자인 — "Brick은 movement topology만 모델링, **node-to-node data-dependency graph 없음** → 형제 stale을 기계가 못 앎". 설계서의 impact resolver("dev-B가 design-plan-1 소비하나?")는 **계산 기질 자체가 없다**. HOLD 폴백이 있어 설계는 안 무너지나, **초기 효과 = COO 승인 부분범위 재실행이지 전자동 아님**. Phase 4 자동승인은 산출물 소비 추적이라는 별도 공사 선행. 설계서에 이 상한을 명시하라.
- **sibling_independence (§2.4)**: 이건 설계서가 기존 것(assembly.py:248-287, plan_graph.py:276-282)을 올바로 인용한 드문 지점. 유지.

---

## 발주 아키텍처와의 관계

이 route 설계서(§S)는 발주 아키텍처 기획서의 **Phase 6~7(Common Route Policy + COO Disposition/HOLD)에 흡수**된다(원장 §T). 따라서:
- 두 문서의 concern_kind·route_scope 어휘는 **하나로 통일**돼야 한다.
- route 설계서 개정 v2는 발주 아키텍처 v2와 **정합**해야 한다(별개로 가면 어휘 분열).
- 발주 피드백 파일: `order-architecture-feedback-0708.md` (동반 참조).

---

## 위험도 (개정 후 시공 참고)

- **Phase 3/§13 walker 실행 (최고위험)**: walker_kernel.py 3053줄 / 26 모듈 의존 + walker_resume.py. routing rule = high-impact. 개헌 이주(§R) 착지 후에만.
- **Phase 1/§5 concern schema (고위험)**: 봉인 분열 = human gate.
- 나머지는 route_materialization 확장이라 반경 축소 가능(재정위 후).

---

## 개정 산출물 요청

codex는 위 3건 해소 + route_scope 재정위를 반영한 **route 설계서 v2**를 낸다. v2는 발주 아키텍처 v2와 concern_kind·route_scope 어휘를 공유한다. v2 도착 후 COO 재검증 → Smith 채택.

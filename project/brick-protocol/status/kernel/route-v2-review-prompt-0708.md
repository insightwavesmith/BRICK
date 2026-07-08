# Route V2 검수 요청 프롬프트 (GPT deep-architecture용, 0708)

> 용도: BRICK 공통 Route/HOLD 아키텍처 v2 설계서를 외부 모델(GPT)에게 깊게 검수시키는 프롬프트.
> 성격: 검수/개정 요청. 이 프롬프트로 GPT가 route 설계서 v2를 낸다. COO/Smith가 재검증 후 채택.
> 중요: Route V2는 지금 구현 대상이 아니다(HOLD). 이 프롬프트는 설계 검수만 요청한다.
> 실행 seam(run_building_intake -> materialize_building_intent -> run_building_plan),
> walker_kernel, walker_resume, Link 봉인은 검수 단계에서 바꾸지 않는다.

---

## 0. 역할 지정 (프롬프트에 그대로 넣을 것)

```text
You are reviewing the BRICK common Route/HOLD architecture design (Route V2).
This is a design review, not an implementation task.
Do not propose a new engine. Prefer extending existing sealed surfaces.
Ground every claim against the provided repo evidence, not against the design doc's own claims.
If evidence is missing in the pack, say NOT CONFIRMED — do not guess.
Output must separate: OK / FIX / BLOCKER, each with file:line evidence.
```

---

## 1. 배경 (변하지 않는 사실 — 프롬프트에 명시)

```text
- Active physical roots are brick_protocol/{brick,agent,link,support}/ and project/.
  Legacy top-level brick/agent/link/support are NOT active import roots.
- Official execution seam:
  run_building_intake -> materialize_building_intent -> declared-building-plan.json -> run_building_plan
- Movement is binary: forward | reroute. hold/stop are lifecycle/gate states, not Movement.
- concern_kind is sealed to 8 kinds (single source of truth, triple-pinned):
  brick_protocol/agent/return_fact.py TRANSITION_CONCERN_KINDS
  = design_gap, implementation_gap, upstream_gap, boundary_mismatch,
    insufficient_input, replay_needed, verification_gap, unknown
  + brick_protocol/brick/templates/bricks/transition-concern-return.yaml
  + brick_protocol/link/route_policies/basic_qa_repair.yaml
  validate_transition_concern_evidence fails closed outside the enum.
- verification_gap is intentionally NON-reroute (basic_qa_repair.yaml excludes it).
- route_scope / concern->route mapping ALREADY EXISTS and is more mature than the design doc assumes:
  brick_protocol/support/operator/route_materialization.py
    :78  materialize_transition_concern_disposition (concern -> route_scope)
    :305 route_replay_plan (live_retry / carry_forward / replay already modeled)
    :457-461 author_ref forbidden-prefix seal (support:/agent:/provider:)
- fake-landing defense is live and must not break:
  brick_protocol/brick/templates/bricks/code-attack-qa/brick.md:43-48
  (QA cross-checks upstream made_changes/changed_files against real diff)
- Automation ceiling is real: brick_protocol/support/operator/walker_fan_in.py
  models movement topology only, NOT node-to-node data-dependency graph.
  So sibling-stale impact cannot be machine-computed; HOLD fallback is required.
```

---

## 2. 검수 대상 문서

```text
대상 설계서: BRICK_common_route_architecture.md (§S) 및 그 v2 개정본.
동반 참조: order-architecture-feedback-0708.md, route-architecture-feedback-0708.md.
```

---

## 3. 반드시 판정할 항목 (각 항목 OK/FIX/BLOCKER + file:line 근거)

### A. route_scope 신규 vs 기존 확장
```text
- 설계서 §6 route_scope가 신규 brick_protocol/link/route_scope.py로 가는가?
- 그렇다면 기존 route_materialization.py:78/305와의 중복을 증명하고,
  신규가 아니라 route_materialization 확장으로 재정위하라.
- route_scope 필드(repair_target_refs, live_retry_refs, carry_forward_refs,
  affected_qa_refs, carry_forward_qa_refs, recompute_join_refs, replay_mode)를
  기존 route_replay_plan(route_materialization.py:305)에 매핑한 표를 요구하라.
  무엇이 신규 필드이고 무엇이 기존 필드 재명명인지 구분.
```

### B. concern_kind 봉인 8종 정합
```text
- 설계서 §5.2/§8의 concern_kind가 봉인 8종과 일치하는가?
- 신규 kind(integration_gap/qa_defect/closure_gap/budget_gap/human_gate_required/provider_gap)
  추가나 replay_needed/unknown 누락이 있으면 BLOCKER로 잡아라.
- 신규 kind가 정말 필요하면 명시적 확장 절차를 요구하라:
  return_fact.py + transition-concern-return.yaml + basic_qa_repair.yaml + validate + checker 동시 개정.
  이것은 fact-class shape 변경 = human gate 대상임을 명시.
- 발주 아키텍처 문서와 concern_kind enum을 하나로 통일하라.
```

### C. verification_gap 비리라우트 보존
```text
- 설계서가 verification_gap을 reroute 가능하게 만들면 BLOCKER.
- basic_qa_repair.yaml의 verification_gap 제외를 재발명하지 말고 인용하라.
```

### D. delta QA vs fake-landing 방어
```text
- 설계서 §14 delta QA가 좁혀도, producer 주장(made_changes/changed_files)-실제 diff 대조가
  유지됨을 증명하라. 유지 못 하면 BLOCKER.
- 발주 Blind Pack(verdict 은닉 / factual claim 노출)과 정합시켜라.
- 머지 직전 빌딩은 full-QA 백스톱 정책을 명시하라.
```

### E. author_ref 봉인 중복 여부
```text
- §18 check_route_scope_authority가 기존 author_ref 봉인
  (route_materialization.py:457-461)과 중복이 아님을 증명하거나 통합하라.
```

### F. 자동화 상한 명시
```text
- 설계서가 impact resolver로 sibling-stale 자동판정을 전제하면 FIX.
- walker_fan_in.py 자인(data-dependency graph 부재)을 근거로,
  초기 효과는 "COO 승인 부분범위 재실행"이지 전자동이 아님을 설계서에 명시하게 하라.
- 전자동(Phase 4)은 산출물 소비 추적이라는 별도 선행 공사가 필요함을 명시.
```

### G. Movement/gate/lifecycle 분리
```text
- 설계서가 hold를 Movement로 쓰면 FIX.
- gate_state/lifecycle_state와 movement_candidate(forward|reroute|null)를 분리하라.
```

### H. 순서/위험도
```text
- §13 walker 실행(walker_kernel 3053줄 / 26모듈 의존 + walker_resume)은 최고위험.
- 개헌 이주 착지 후에만, human gate + checker green 후에만 시공 가능함을 설계서에 못박아라.
```

---

## 4. 기대 산출물

```text
VERDICT: FORWARD | HOLD-WITH-FIXES | HOLD

SUMMARY:
- ...

FINDINGS (each with OK/FIX/BLOCKER + file:line):
A route_scope reposition
B concern_kind seal parity
C verification_gap non-reroute
D delta QA vs fake-landing
E author_ref seal duplication
F automation ceiling
G movement/gate separation
H sequencing/risk

ROUTE V2 REVISION PATCHES:
- field mapping table (new route_scope -> existing route_replay_plan)
- unified concern_kind enum with 발주 doc
- explicit extension procedure for any new sealed kind

SHARED-VOCAB CHECK WITH 발주 v2:
- concern_kind
- route_scope

HUMAN GATES:
- ...

PROOF LIMITS / NOT CONFIRMED:
- list anything not verifiable from the provided pack
```

---

## 5. 제한 (프롬프트 말미에 명시)

```text
- Route V2 is design review only. Do not implement.
- Do not modify run.py, walker_kernel.py, walker_resume.py, link/*, agent/return_fact.py.
- Do not merge route policy work into the 발주/building-call track.
- Prefer extending route_materialization.py over any new route_scope.py.
- Source truth is the live repo, not the design doc's own claims.
```

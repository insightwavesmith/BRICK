# 하네싱 로드맵 T1~T6 — COO 발주 준비 문서 (0704)

> **0705 낮 조사자 실효 스탬프 — T1~T6 전부 기집행, 이 문서 근거 재발주 금지.**
> 실측: t1-tasklint-0704a(+t1s2 v2~v4)·t2-contractecho-0704a·t3-parityledger-0704a·
> t4-behavior-red-0705a·t5-pin-diet-0705a/t5v2-qadelegate-0705a·t6-holdvocab-0704a 빌딩
> 실존 + 실물 배선(task_order_preflight.py, work/return.yaml:9 received_deliverables_echo,
> return_fact.py TOP_LEVEL_VERDICT_KEYS의 good_enough, check_declaration_enforcement_parity.py,
> probe_prompt_behavior_red.py, coo.md 327줄 축소). 아래 본문의 "현재 실물/부재" 서술은
> 0704 작성 시점 스냅샷(역사 기록)이다. 잔여 트랙은 harness-roadmap-orders-t7-t11-0704.md
> — 그 문서도 발주 시 앵커 재확인 필수(external-audit-repair-orders-0705.md 0705 낮 증보).

0704 하네싱 강화(87ae5df0, 정본: harness-reinforcement-brick-agent-0704.md) 후
남은 구조 개선 6건. 각 항목은 COO 세션이 빌딩을 굴릴 수 있게 발주-준비 상태로
기술한다. 모든 항목은 0702~0704 실측 사고에 앵커되며, "이미 반영됨" 실물 확인을
0704에 마쳤다(각 항목의 '현재 실물' 절).

## 공통 발주 규율 (모든 T 공통 — 발주문에 그대로 상속)

- 모델: fable5 레인 금지. codex=구현·마감·code QA / claude sonnet(xhigh)=조사·축·증거 QA / gemini=저위험 review 렌즈만 (agent/disciplines/model-lane-matching.md).
- 규범 계약(Deliverables 원문·종료선·리터럴 프로브)은 각 노드 work_statement에 인라인. 참고문서는 source_facts로 — 이 문서의 repo 경로를 쓰라 (커밋된 트리 경로만, 발사 전 test -f).
- 발주문에 "근거 file:line만 반환" 류 문구 금지 — file:line 인용은 observed_evidence로, reason_refs엔 스텝 주소·불투명 토큰만.
- 레인이 격리 워크트리/write_scope 안에서 물리적으로 충족 불가능한 수용 기준은 "COO 게이트 항목"으로 계약에 분리 선언. 기계 게이트를 원하는 D는 proof_obligations로.
- Deliverables에 명시적 종료선(DONE). proof는 수신 렌즈 환경에서 실행 가능한 것만 배정.
- 사이징: 토큰 효율이 아니라 "이 발주가 업무를 종료시키는가". 파일 비충돌 병행 발사.
- 엔진 불가침: `_run_dynamic_graph_walker` 수정 금지. walker 인접 수정은 Smith 게이트.

## 의존 순서

```text
T1(발주문 린트) ─┐
T2(계약 에코)   ─┼─ 상호 독립, 병행 가능 (파일 비충돌)
T3(패리티 원장) ─┘   단 T3은 Gap1(good_enough 집행 동기화) 선/후 결정 필요
T4(프롬프트 행동-RED) → T5(핀 통합)   ← T5는 T4 없이 발주 금지 (측정 없는 다이어트 금지)
T6(홀드 자기서술) — 선언 슬라이스만 독립, 소비 슬라이스는 엔진(Smith 게이트)
```

---

## T1. 발주문 린트 — 계약 템플릿의 기계 게이트화 (최우선)

**문제/실측**: task.md 8항목·종료선·렌즈-proof 매핑은 전부 산문 권고. compose/launch
경로에 work_statement 내용 검사가 0 (0704 grep: support/operator/composition_*.py,
run.py에 validate/lint 부재). 실측 비용 — 0703 종료선 부재 6라운드, 0704
proof_obligations 모순 발주 6라운드(레인 방어는 work/return.yaml rules에 랜딩됐으나
저자 쪽 검사는 여전히 없음), reason_refs 유도 문구 fail-closed 홀드. 현재 방어선은
COO 기억뿐 — 단일 실패점.

**목표 상태**: 발사 전 프리플라이트 린트가 오염 발주를 RED로 막는다.

**린트 규칙 초안 (design 노드가 확정)**:
- L1: work/development 노드 work_statement에 종료선 마커(Done/종료선/DONE Criteria) 존재.
- L2: proof_obligations 명령이 대상 노드 KIND의 capability_class와 모순 없음 (read 렌즈에 source-mutation/재실행 명령 배정 금지).
- L3: work_statement 내 reason_refs 유도 문구 패턴("file:line만 반환" 류) 검출.
- L4: numbered Deliverables 존재 + write_scope와 Deliverables 대상 파일 합치.

**착지 표면**: 1단계(이 발주) = 독립 프리플라이트 모듈(support/operator/ 신설,
COO가 발사 전 호출) + brick/templates/tasks/source-template.md에 "기계 검사 항목"
선언 섹션. 2단계(별도 발주, Smith 게이트) = composition_compose 경로 배선.

**그래프**: design(sonnet: 규칙·경계 확정) → work(codex: 모듈+픽스처) →
fan(code-attack-qa codex, axis-attack-qa sonnet) → closure.

**task.md 조각**:
- Objective: 발주문 프리플라이트 린트 1단계 — 독립 모듈 + 오염 픽스처 RED.
- Deliverables: D1 린트 모듈(L1~L4) / D2 오염 픽스처 3종(종료선 없음·렌즈 모순·유도 문구)이 각각 RED / D3 클린 발주 픽스처 green / D4 source-template.md 선언 섹션 / 종료선: D1~D4 + 격리 워크트리 --all green이면 DONE, compose 배선은 이 발주 범위 밖.
- Proof required: `uv run python -m <신설 모듈> <오염픽스처>` rc!=0 리터럴 출력 3종 + 클린 rc=0 + `check_profile.py --all` (QA 렌즈는 W1 워크트리 내).
- Write scope: support/operator/<신설 파일>, support/checkers/<신설 체커 1>, brick/templates/tasks/source-template.md, 픽스처 디렉터리.
- Hard constraints: composition_compose.py 수정 금지(2단계), 기존 발주 경로 무변경.

**함정**: 린트가 산문 자연어를 과잉 매칭하면 false-RED — 규칙은 마커/패턴 기반으로
좁게 시작(0704 catalog checker의 rules: 자유문장 교훈). 기존 프리셋 발주문 전수를
클린 픽스처로 돌려 회귀 확인.

---

## T2. 계약 수신 에코 — 해석 이탈 검출 구조

**문제/실측**: 레인은 task.md를 못 볼 수 있고(0702 실측), 자기가 이행해야 한다고
이해한 내용을 아무도 확인 안 한다. 반환엔 received_work_ref(참조)뿐, 이해 에코 필드
전무(0704 grep: 전 return.yaml에 received_contract/echo 계열 0건). 0702 llm-alias
반복 수리 — 동일 계열 concern이 여러 attempt에 재발했고(audit-0703/guide-1 원문 raw:
work-attempt 1/2/4 재발), "요청과 다른 걸 만듦"을 diff 대조(만들었나)로는 못 잡았다.
계약↔이해↔diff 3자 대조가 필요.

**목표 상태**: work 반환이 "내가 이행해야 한다고 이해한 번호 목록"을 에코하고,
closure deliverable_crosscheck가 계약 원문과 대조.

**착지 표면**: brick/templates/bricks/work/return.yaml required_return_shape에
`received_deliverables_echo` 추가 + work/brick.md 산문 동반(산문 드리프트 체커
양방향 강제) + closure/brick.md crosscheck 지침에 3자 대조 문구. 소비 게이트는
차후(패턴: 필드가 선언, 게이트는 소비자).

**그래프**: work(codex: 표면 2+픽스처 스윕) → fan(code-attack-qa codex,
evidence-integrity sonnet) → closure.

**task.md 조각**:
- Deliverables: D1 work/return.yaml 필드+rules 추가 / D2 work/brick.md 산문 /
  D3 closure/brick.md 3자 대조 지침 / D4 기존 FIRE·재생 픽스처 전수 스윕 —
  required_return_shape 추가가 깨는 픽스처 목록과 수정 / 종료선: 체커 green +
  D4 스윕 결과 보고면 DONE. 런타임 소비 게이트는 범위 밖.
- Proof: `check_bricks_spec_completeness` rc=0 + 필드 누락 반환이 비교기에서 걸리는
  실행 출력 1건(behavior 확인) + --all green.
- Write scope: brick/templates/bricks/{work,closure}/, 관련 픽스처.

**함정 (발주문에 명시)**: required_return_shape에 필드를 추가하면 기존 재생/픽스처
전부가 그 필드를 요구받는다 — D4 스윕이 핵심이며, 하위호환이 크게 깨지면 레인은
partial로 정직 보고하고 COO 게이트로 넘긴다(레인-불가능 D 분리).

---

## T3. 선언-집행 패리티 원장

**문제/실측**: 선언과 집행이 따로 살면 조용히 썩는다 — good_enough가 증명
(return.yaml 10곳 금지 선언 vs agent/return_fact.py TOP_LEVEL_VERDICT_KEYS:49-74에
부재, 0704 독립 QA 실측). closure deliverable_crosscheck도 "future gate consumes"
상태로 원장 없이 대기 중(closure/return.yaml:44-45). "차후 소비자" 패턴에 차후가
왔는지 추적하는 장치가 없다.

**목표 상태**: "집행자 없는 선언"이 기계로 열거되고, 신규 선언은 enforced_by 또는
gate-pending을 명시해야 한다.

**착지 표면**: design 노드가 결정할 논점 — (a) 각 return.yaml에 enforcement 매핑
분산 선언 vs (b) 단일 원장 파일(brick/templates/enforcement-ledger.yaml) 집중.
+ 신설 체커 check_declaration_enforcement_parity(forbidden_return_keys 전수 ×
return_fact.TOP_LEVEL_VERDICT_KEYS 대조, "later consumer" 선언 문구 → 원장 등재 강제).

**선행 결정 (Smith/COO)**: Gap 1(good_enough를 TOP_LEVEL_VERDICT_KEYS에 추가)을
먼저 랜딩하면 체커가 green으로 태어나고, 안 하면 체커의 첫 RED가 Gap 1이 된다 —
후자가 도그푸드 증명으로 더 가치 있음(체커가 실제 갭을 잡는 라이브 증명). 추천: 후자.

**그래프**: design(sonnet: 분산/집중 결정) → work(codex) → fan(code-attack-qa,
axis-attack-qa) → closure.

**task.md 조각**:
- Deliverables: D1 원장/스키마 선언 / D2 패리티 체커 신설 / D3 현재 갭 전수 보고
  (good_enough 포함 예상) / 종료선: 체커가 기지 갭을 정확히 열거(RED)하고 원장
  등재 후 green이면 DONE.
- Proof: 체커 실행 리터럴 출력(갭 열거 → 등재 → green 2단) + --all.
- Write scope: brick/templates/, support/checkers/<신설>.
- Hard constraints: return_fact.py 수정은 이 발주 범위 밖(Gap 1 별도).

---

## T4. 프롬프트 행동-RED — 에이전트 축의 mutation-RED

**문제/실측**: 구조 체커(참조 해소·산문 드리프트)는 있으나 프롬프트가 실제 레인
행동을 바꾸는지 측정 장치가 0. 0704 dev.md 강화도 "레인이 diff 없이 complete를
실제로 거부하는가"는 not_proven. 체커 문화(mutation-RED)가 에이전트 축에만 없다.

**목표 상태**: 유혹 픽스처를 실제 레인에 먹여 거부를 판정하는 재실행 가능한 프로브.

**설계 골자**: LLM 호출이 있어 결정적 체커가 아니라 fixture-driven 프로브 빌딩으로
분류. 판정은 기계(반환에 금지 키/패턴 존재 여부, forbidden key ValueError 발화 여부).
비결정성은 N=3 샘플 + "3/3 거부" 통과 기준을 계약에 선언. 1차 대상 2종:
- P1 dev 레인: diff 없는 상황 + complete 유혹 계약 → made_changes:false/no_changes_reason 반환하면 통과 (0702 재현).
- P2 qa 레인: 상류 complete-style 반환 + 실제 diff 부재 픽스처 → implementation_gap 보고하면 통과.

**착지 표면**: 프로브 픽스처 + 러너(support/fixtures 또는 프로브 전용 디렉터리,
design이 확정). 프롬프트 자체는 무수정(측정만).

**그래프**: design(sonnet: 판정 규격·픽스처 설계) → work(codex: 러너+픽스처) →
fan(evidence-integrity sonnet: 판정이 과잉주장 안 하는지) → closure.
어댑터 실행 비용 있으므로 프로브 N은 계약에 고정.

**task.md 조각**:
- Deliverables: D1 프로브 러너 / D2 P1·P2 픽스처 / D3 현행 프롬프트 기준 측정
  보고(통과/실패 리터럴) / 종료선: P1·P2가 현행 프롬프트에서 3/3 통과(또는 실패를
  정직 보고 — 실패면 그 자체가 다음 프롬프트 수리 발주의 입력)면 DONE.
- Proof: 러너 실행 리터럴 출력(반환 페이로드 판정 근거 포함).
- Hard constraints: agent/prompts/ 수정 금지(측정 발주), 프로브 반환을 실계약
  원장에 기록 금지(픽스처 격리).

**함정**: 프로브가 레인 프롬프트+브릭 계약 결합을 재현해야 의미 있다 — 어댑터
경유 실제 dispatch(adapter:codex-local 등)로. 모의 프롬프트 직접 호출은 측정 무효.

---

## T5. 핀 통합 주기 — T4 선행 필수

**문제/실측**: 사건마다 산문 핀이 append돼 프롬프트가 자란다 — coo.md 332줄,
qa.md:24-32·coo.md:293-310에 근사중복 "Operational pin"(0704 정독 확인). 늦은 핀의
가중치 희석 = dev.md 15줄 문제의 역방향. 스킬은 resize-audit(정본:
skill-doc-resize-audit-0702.md)를 했는데 프롬프트는 미실시.

**목표 상태**: 프롬프트별 중복 핀 통합 + T4 행동-RED로 통합 전후 등가 증명.

**그래프**: work(sonnet: 측정+통합안 — 조사 성격) → fan(T4 프로브 재실행 codex,
axis-attack-qa sonnet) → closure. **T4 랜딩 전 발주 금지** (측정 없는 다이어트 금지).

**task.md 조각**:
- Deliverables: D1 프롬프트별 중복/길이 측정표 / D2 통합안(핀 의미 보존 표) /
  D3 통합 적용 / D4 T4 프로브 전후 동일 통과 / 종료선: D4 등가 증명이면 DONE.
- Proof: T4 러너 전/후 리터럴 출력 쌍.
- Write scope: agent/prompts/*.md.

---

## T6. 홀드 패킷 자기서술 — 선언 슬라이스만

**문제/실측**: 처분 오판 3회 실측(0702 budget_exhaustion raise/forward 혼동 2회,
0703 reroute-제안 홀드에 forward 오판 — "채택"이 아니라 "선언 경로 계속"이었음,
support/operator/walker_resume.py:410이 잘못된 raise를 명시 거부). hold_reason별 합법 처분과 의미가
문서·운영자 기억에만 있고 홀드 패킷엔 안 실린다.

**목표 상태 (이 발주 = 선언만)**: hold_reason → {합법 처분, 각 처분의 실제 의미,
오판 사례} 매핑 정본을 link 어휘 표면에 커밋. walker가 홀드에 메뉴를 실어 나르는
소비 슬라이스는 엔진 수정(walker 인접)이라 별도 발주 + Smith 게이트.

**착지 표면**: link/ 어휘 문서(design이 GATE_REGISTRY 인접 배치 결정) + 
agent/skills/building-coordination 참조 갱신.

**그래프**: 소형 — work(sonnet: 실측 사례 수집·정본화, 조사 성격) →
review(gemini 가능: 저위험 문서 렌즈) → closure.

**task.md 조각**:
- Deliverables: D1 매핑 정본 문서(실측 3사례 인용) / D2 building-coordination 참조 /
  종료선: 문서 커밋 + 체커 green이면 DONE. walker 소비는 범위 밖.
- Hard constraints: walker_*.py 수정 금지.

---

## 부록 — 골플랜 등재 대기 (Smith 직접 전달 예정, 0704)

- Gap 1: good_enough 집행 동기화(agent/return_fact.py TOP_LEVEL_VERDICT_KEYS) —
  T3과 선/후 결정 필요(§T3 선행 결정).
- Gap 3: reroute-defaults.yaml re_instruction 종료선 선언 3줄 — declared_by: smith
  파일이라 Smith 비준 게이트.
- 정본: harness-reinforcement-brick-agent-0704.md §Recorded gaps.

증거 한계: 이 문서는 발주 준비 기획이며 source truth·성공 판정·품질 판정·Movement
권한이 아니다. 각 '현재 실물' 절은 0704 시점 측정이고, 발주 시점에 재확인하라.

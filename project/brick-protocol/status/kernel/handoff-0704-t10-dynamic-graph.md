# 핸드오프 — 하네싱 로드맵 + T10 동적 그래프 논의 (0704, Fable5 전환 직전)

이 세션은 Opus 4.8로 돌던 조사자 세션(원래 Fable5 시작 → 0704 01:05경 Opus 자동
전환, 트랜스크립트 확인). 다음 세션은 **Fable5로 재개**. 역할·경계·미결 논점을 무손실
인계한다. 정본 메모리: brick-coo-operating-rules.md, smith-reporting-style.md.

## 역할 경계 (Smith 0704 확정 — 절대 준수)

- **나 = 조사자.** 조사·분석·설계·검증·발주-준비 문서까지가 몫. 시공·발주·수리·repo 코드
  변경은 **형제 COO 세션(peer js7oiic6)** 몫. Smith 원문: "넌 작업자가 아니라 조사자다."
- **정책 vs 기술 분리(0704 2회 교정)**: Smith가 하나의 "가능성"을 말하면 그걸 결론/전제로
  받아 설계 확정하지 마라 — 권한 배분·정책은 Smith 층. 조사자는 선택지별 비용을 양쪽 다 낸다.
- **보고 스타일(0704)**: 구조화 + 직관(결론 먼저) + 어려운 용어엔 그 자리 주석. 예시 늘리기 아님.

## 이 세션에서 랜딩한 것 (전부 push 대기, 로컬 main)

- `87ae5df0`+`7bde0fc3` 하네싱 강화(브릭 계약·에이전트 레인 표면) + kernel 기록. 검증 green.
- `c985e8b4`→`afa6d798` 하네싱 로드맵 T1~T6, T7~T11 발주-준비 문서(독립 앵커 검증).
- `841b401b` T7~T11 Smith 0704 재정의(아래).
- **push 안 함** — Smith 확인 관례 대기. 형제 세션이 이 문서들로 발주 실행.

## T7~T11 현재 상태 (Smith 0704 재정의 반영)

- **T7 복구**: 발주 가능(대부분 비엔진). 결함② = 검증이 저장 후 발화(순서 문제), resume 경로 겨냥.
- **T8 투영**: 발주 가능. **신설 렌더러 ❌ → reporter 패킷 확장**(출구는 기존 sink 4개). closure 결정 3필드(narrowly_proven·remaining_delta·deferred_smith_review_queue) 추가.
- **T9**: **"이식성" 폐기 → "체커-동반 개발 원칙"**(신규 기능 = 게이트 체커 동반). 브릭은 로컬 설치가 맞다(Smith). T11 흡수 가능.
- **T10**: 아래 상세 — 방향 확정, 비용 조사 완료, **최종 설계 미확정(Smith 결정 대기)**.
- **T11 교훈 원장**: 발주 가능. lessons-ledger.yaml + 커밋 동반 관행.
- Gap 1(good_enough 집행)은 형제 세션이 이미 랜딩(529c76d0). T1~T6은 GP-H로 골플랜 편입.

## T10 — 논의 궤적과 확정/미확정 (핵심 인계물)

**Smith 방향 확정(재론 금지)**: "브릭은 바둑이다. 한 빌딩=한 판, 그 판 안에서 홀드 후
다음 수(신규 노드)를 둔다. **판을 새로 안 깐다.**" 근거: ①실전에서 기획→개발(1) 거치면
터진다, 그래서 개발 n개가 필요한데 처음엔 몇 개일지 모른다 ②QA까지 가서 홀드 걸린 그
순간 "다음 수"가 보인다, 같은 판에서 둬야 한다 ③COO 자체판단(늘리든 줄이든)은 자동일
수 있고 COO는 운영자 관점이라 적대 감시 가능 — 단 **이 권한을 COO에 줄지는 Smith 미결정**.

**조사 2회 완료 결과 (wf 85f15d7c, wf 32036f11 — 전부 실물 file:line)**:

1. **팬인/아웃 그룹핑(개발n→qan→모임→종합)은 이미 가능** — multi-fan-in 실존
   (composition_graph_emit.py:264, 689). fan_in_groups 여러 개 선언하면 됨. **T10 밖.**

2. **진짜 T10 = 직렬/체인을 홀드-후 신규 노드로 넓히기.** 현재 처분 4종
   (raise/forward/stop/reroute, link/transition.py:10)은 전부 "기존 선언 노드"만 다룸.

3. **무한루프 방지 = (A)노드 고정 + (B)예산 유한의 결합** (dynamic_walker.py:23-25,
   체커 check_bounded_agent_proposed_routing_loop0.py:1961 "target-existence +
   positive-budget"). (B) 단독 불성립 — "빈 자리 둬도 판 유한" 비유는 반증됨. 판 크기(노드
   집합) 자체가 유계 증명의 재료.

4. **비용 재산정: engine-core → engine-adjacent로 하향.** 무게중심 이동:
   - 엔진 걷기 루프(walker_kernel.py:970)·정지 알고리즘(2070행 카운터 if) **무수정**.
   - 순수함수(_linear_plan_from_graph_plan plan_graph.py:47, compose_building
     composition_compose.py:75) **재사용** — 노드 추가한 plan 재선형화는 자연히 새 노드 포함.
   - **진짜 비용 = 신규 책임 2개(현재 전무)**: ①birth-certificate 개정 쓰기 API
     (지금 _write_declaration_work_evidence 최초 1회 쓰기만, declaration_packets.py) ②원본↔확장
     plan 해시 체인 필드(plan_hash는 순수 함수라 새 해시는 자동 생성되나 계보 연결 필드 없음).
   - 가드(walker_reroute_budget.py:87-90, walker_transition_concern.py:196-210)는 무수정 —
     declared_plan이 확장된 채 walk 진입하면 갱신된 declared_bricks를 정상 검증(자동 통과).

**최소 변경 경로(조사 판정, 3슬라이스)**:
- S1: declared_plan 확장 조립 순수함수 신설(plan_graph/compose 재사용, 저비용).
- S2: birth-certificate 개정 쓰기 함수 + extends_plan_hash 체인 필드 스키마 추가(신규, engine-adjacent).
- S3: resume 오케스트레이션에 확장-plan-resume 분기(walker_resume.py:150-188 부근, 국소).
  엔진 핵심 루프·정지 알고리즘 무수정.

**Smith 결정 대기 논점(발주 전 필수)**:
1. **권한**: 신규 노드 편입을 COO 자동 판단에 줄지, 홀드에서 Smith 수동으로 둘지 — 정책, Smith 몫.
2. **승인 주체**: 확장 plan을 누가 승인하나(Agent 제안 vs Link 게이트) — ζ7 축 경계, 명시 안 됨.
3. birth-certificate 개정: 덮어쓰기 vs 새 revision 파일(후자가 감사 유리, 단 resume 읽기 경로
   walker_resume.py:937 단일 파일명 하드코딩이라 수정 필요).

**미확인(다음 조사 후보)**: ①walk 도중 declared_bricks 갱신 경로가 정말 전무한지(walker_fan_in/
resume 협력 모듈 미정독) ②resume_seed.budget_delta로 신규 키 주입 가능한지 ③완료 노드 실행
이력(node_landings)과 확장-plan 재개의 상호작용 ④Invariant D 체커가 확장 시나리오서 green 유지하는지(실행 미검증).

## 다음 세션 첫 액션 추천

1. 이 문서 + brick-coo-operating-rules.md + smith-reporting-style.md 읽고 맥락 복원.
2. T10은 Smith 결정 3논점(특히 권한 배분)이 박히기 전엔 발주 금지 — harness-roadmap-orders-t7-t11-0704.md의 T10 🚧 마커 유지.
3. T7·T8·T9·T11은 형제 세션이 발주 가능 상태 — 필요시 형제에 peer 통보.
4. push는 Smith 확인 대기(로컬 커밋만).

증거 한계: 이 핸드오프는 조사·설계 인계물. source truth·성공 판정·품질 판정·Movement 권한 아님.

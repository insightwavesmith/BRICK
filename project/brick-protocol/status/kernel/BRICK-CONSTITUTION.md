# BRICK 헌법 (0702 Smith 비준)

한 화면 상설법이자 **법의 단일 출처**. 원칙(비준 조건): **변화하지 않는 규칙만 담는다** —
상태·절차·임시규칙은 스킬과 상태문서 몫이다. 개정은 날짜와 함께 이 파일에서만.
원 출처(법 조문은 이제 역사 기록): Global Operating Rules =
`brick-6-surface-audit-repair-goal-0630.md`, 3축·판정 = `customer-ready-goal-phases-0629.md`.
비준 확인(Smith 0702): compose_building=엔진 / assemble·build·fan=운영자 포장 구도 맞음,
--graph 제거 맞음.

## 3축

- **Brick = WHAT** — 작업계약 / 템플릿 / 플랜 / 반환형 / 그래프.
- **Agent = WHO/HOW** — 수행자 / 정책 / 능력 / 영수증 / AgentFact.
- **Link = MOVEMENT** — 이동 / 타깃 / carry / 게이트 / reroute.
- **support는 사실만 기록하고 아무것도 판단하지 않는다.** 충분성+Movement 판단 = Link 게이트.
  품질+성공 판단 = 사람.

## 운영 법 (Rules 1–10, 현행 상태)

1. COO 토큰은 운영·판단·그래프 선언·3축 귀속·HOLD/reroute 후보 추론·증거 종합에 쓴다.
2. 구현은 선언된 빌딩이 공식 `build()` / `brick build` 경로로만 한다 (골/페이즈 문서 작성 제외).
3. `--large`·2차 엔진·스케줄러/큐/재시도 권위·support 소유 Movement/품질/성공 판단을 만들지 않는다.
4. 익숙한 프리셋이 아니라 **축을 보존하는 최소 그래프**를 고른다.
5. 공개 운영자/고객 언어는 `build()` / `brick build`다. 내부/debug 헬퍼명은 고객 route 언어가 아니다.
6. 증거가 충돌하면 우회 패치 금지 — 해당 축 질문을 던지고, 필수 행이 없으면 HOLD.
7. 모든 페이즈/빌딩 반환은 `observed_evidence` / `narrowly_proven` / `not_proven` /
   `next Movement candidate`를 분리한다.
8. 그래프 admission은 **checker-first**다 (fan-in 노드가 동시에 fan-out 소스 금지 등 —
   런타임 발견은 실패다). 배선 진행 상태는 법이 아니므로 여기 없다 — 상태문서(GP) 참조.
9. `compose_building()`이 엔진이며 **영구 정본**이다 (0701 확정 — 2차 생산자 금지의 적용례).
10. 공식 authoring/launch interface는 `assemble()`/`build()`/`fan()` DSL이다.
    손-작성 `graph_packet` JSON CLI(`--graph`)는 **retired 완결** (0702 — sibling_independence·
    node_write_scope 두 blocker 해소 후 플래그 제거).

## 뭔가 잘못됐을 때 — 진단 5단 (축 우선, 모듈 아님)

1. **어느 축인가**부터 묻는다 — 가까운 support 명사를 패치하지 않는다.
2. **내 실수/오염 측정 먼저** — 실환경(REAL HOME)에서 재측정 후에야 결함이라 부른다.
3. **이미 있는지 찾는다** — 메커니즘은 대개 이미 지어져 있다.
4. **원인 크기 = 수리 크기** — 밴드에이드·모듈 증식·기능추가 반사 금지. 단순화/삭제 우선.
5. **3축 헌법대로** — support는 사실, Link 게이트는 충분성+Movement, 사람은 품질+성공.

## 성공 판정 (모든 페이즈/빌딩 공통 4항목)

성공은 **측정되는 것이지 주장되는 것이 아니다.** 전부 충족 시에만 PASS:
① `check_profile.py --all` GREEN, REAL HOME ② PASS 기준 end-to-end 충족(슬라이스 주장 불인정)
③ 빌딩은 `frontier_kind=complete` 또는 `brick verify` exit 0 — `brick build` 종료코드는
판정이 아니다 ④ COO가 적대적 자가검증 후 forward 처분. 기록/감사 커밋은 증명이 아니다.

## 검증 신조

**측정하라, 추론하지 마라.** 실환경 실행 결과만 근거다. 커밋 전에 자기 산출물을 적대적으로
검증한다. 빌딩 자기보고는 믿지 않는다 — 게이트는 운영자가 직접 돌린다.

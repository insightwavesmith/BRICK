# A+ 2차 웨이브 기획 정본 (0705) — Smith 채택, 착수 조건부

출처: 지피티 "A+ 아키텍처 전환 기획서" → 조사자 검토(순서 역전·경계 강제·범위 조정) →
**Smith 결정 3(0705 오후): 2차 웨이브로 채택**. 발주-준비 상위 기획이며, 슬라이스별 실발주는
착수 게이트 통과 후 별도 task로 사이징한다. 시공 = 형제 COO. source truth·성공 판정 아님.

## 0. 한 줄 정의

1차 웨이브(external-audit-repair-phases-0705.md = 점수리)가 구멍을 막는 것이라면, A+ 웨이브는
**같은 구멍이 다시 뚫릴 수 없게 감시 구조를 상설화**하는 것 — declare → validate → record →
replay → mutate-RED → generate-docs → customer-safe 루프의 제품화. 새 기능 추가가 아니라
"원칙의 자동 재검증"이 목표다. 헌법 비목표 7종(스케줄러/큐/재시도 금지, support 무판단,
2차 엔진 금지, 무정지 동적 팬 금지 등)은 그대로 유효하다.

## 1. 착수 게이트 (이 조건 전 A+ 명의 코드 발주 금지)

| 게이트 | 조건 | 사유 |
|---|---|---|
| G1 | phases Phase 1 랜딩(묶음5 + 묶음1 잔여) | T10 무결성 점수리가 W1이 흡수할 기반 |
| G2 | 묶음2 랜딩(S4+S1 재배선) | W3·W1이 딛는 "관찰→게이트 소비" 배선의 확정 |
| G3 | T10 첫 실전 확장 운전 1회 완료(조사자) | Contract Kernel이 흡수할 실전 데이터 확보 |
| G4(권장) | Phase 3 잔여(묶음6·4·7) 랜딩 | 미랜딩 시 W1과 파일 겹침 — 병행하려면 write_scope 분리 필수 |

사유 요약: A+ W1~W3가 리팩터하는 파일(declaration_packets·plan_expansion·walker_resume·
driver·gate_sequence)이 1차 웨이브 시공 파일과 동일하다. 병행하면 충돌·재검증 낭비.
지피티 원안도 "거대한 새 설계 불필요, 점수리 먼저"가 자기 판정이었다.

## 2. 슬라이스 W1~W6

### W1 — Contract Kernel 통합 (writer-reader 해석기 단일화)
- 목적: Rule 11(0705 등재)의 집행 구조 — durable 계약마다 해석기 1개를 writer/reader/체커가 공유.
- 흡수: 묶음1(bool seal)·묶음5(reader 재검증)·묶음6(require_positive_int)·묶음7(matcher
  단일화) 랜딩분을 산발 수리 상태에서 공용 모듈로 이관.
- **축 소유 배치(수용 기준 — 위반 시 반려)**: write_scope 해석 = brick/(comparison 정본 유지)
  · budget·lifecycle·gate 어휘 = link/ · support/recording/contracts/는 JSON persistence·
  replay 계약만 — **support가 해석 권위가 되면 4축화**(지피티 원안 스스로 지목한 위험).
- 종료선: S12-WR-001~007 재현 픽스처 전건 reject/align + 이관 전후 행동 동등성(기존 RED
  전부 유지) + 격리 --all.

### W2 — mutation-RED manifest 게이트
- 목적: 체커-동반 원칙(AGENTS.md:404-409)의 기계 집행 — 신규 표면은 RED 명세 없이 반입 불가.
- **방식(조사자 조정): 허용목록-우선** — 이미 사고 난 7표면(declared_plan_revision ·
  plan_expansion · route_materialization · step_output · gate_sequence_decision ·
  write_scope_commit_gate · hold_lifecycle)의 manifest부터. 정규식 자동 탐지(write_declared_*
  류)는 2단계에서 오탐률 실측 후 도입.
- 종료선: manifest mutant ↔ 실제 픽스처 이름 연결(픽스처 삭제 시 fail) + S11 mutant 5종 등록
  + manifest 커버리지 체커가 core 프로파일에 편입.

### W3 — HOLD 생애주기 registry
- 목적: hold_reason을 문자열에서 typed registry로 — 홀드마다 생성→통지→처분→재개 픽스처 의무.
- 흡수: hold-disposition-vocabulary-0704.md(수동 문서 — 이번 스윕에서 드리프트 실측: 출처
  오귀속·앵커 밀림)를 generated matrix로 대체. 묶음4 A안 결과가 registry 초기값
  (adapter_error_frontier = stop-only).
- 종료선: 코드 내 hold_reason 리터럴 전수 추출 = registry 100% 커버(체커) + allowed/rejected
  처분마다 픽스처/RED + quickstart가 generated matrix를 참조.

### W4 — generated docs (문서 부패 근본 봉합)
- 목적: current-tree 수치·표를 담는 문서를 생성물로 전환 — S15에서 실측한 부패 클래스
  (checker-profile-map 30→41, 162→212 등)의 재발 차단.
- 최소 시작 4종: checker-profile-map / hold-lifecycle-matrix / contract-interpreter-map /
  customer-frontier-recovery. 묶음8(1차 웨이브 수동 정정)은 유지하되 W4 발주 시 중복 항목 제거.
- **경계**: `brick docs`류 생성 명령은 운영자/개발 표면으로 명시(공개 고객 언어는
  build/verify 유지 — Rule 5).
- 종료선: 재생성-diff 체커 green(stale이면 fail) + README expected 출력 smoke.

### W5 — privacy egress 체커
- 목적: Rule 13(0705 등재)의 상설 집행 — 센티널 HOME 픽스처로 유출 0 증명.
- 흡수: 묶음3 랜딩(91e4005f) + 0703 세션경로 redaction 사고 계열.
- 종료선: 감시 8표면(Agent prompt · link_handoff_refs · step-output · raw/*.jsonl ·
  evidence-manifest · report payload · FIRST_USE.md · doctor/status JSON)에서 sentinel leak 0,
  절대경로 재도입 시 fail.

### W6 — release·install·audit matrix
- 목적: 지원 설치 표면 명시+smoke, 감사 재현성 공식화.
- 흡수: 묶음10(wheel packages 확장+smoke — 사실상 Option B-lite로 착지 중) + 핸드오프 §5
  아카이브 지시.
- **잔여 Smith 결정 1건(급하지 않음)**: wheel을 "공식 지원 설치면"으로 선언(Option B 완성)
  vs "source checkout 전용" 명시(Option A) — 묶음10 smoke 결과 보고 후 결정.
- 종료선: editable smoke + wheel smoke(또는 unsupported 명시 체커) + audit-full archive
  manifest로 외부 감사자가 S11~S17 계열을 1-archive 재현.

## 3. Phase 0 준비물 (착수 게이트 대기 중 선행 가능 — 코드 무접촉)

1. 지피티 감사 CSV 12종(S11~S17 산출물) 이관 요청 또는 로컬 재생성 →
   status/kernel/audit-0705/ 보관(베이스라인 고정).
2. confirmed finding별 재현 커맨드 목록화 — 각 W 종료선의 RED→GREEN 판정 기준.
3. audit-full archive manifest 초안(핸드오프 §5 명령의 공식화).

## 4. 성공 지표 / DoD (측정 가능한 것만)

confirmed writer-reader mismatch 0 · bool boundary 실패 0 · hold registry 커버 100% ·
manifest 커버(허용목록 7표면) 100% · support 저작 Link lifecycle 신규 row 0 · privacy
sentinel leak 0 · generated docs drift 0 · fresh no-provider `brick verify` rc=0(묶음9) ·
1-archive 감사 재현. 지피티 원안 §8의 DoD 13항 중 12항 채택(6번 adapter-error는 A안으로
기확정), 각 항은 체커/픽스처로 측정 가능해야 완료 처리.

## 5. 지피티 원안 대비 조정 내역 (투명성)

1. **순서 역전**: 원안은 Contract Kernel을 Phase 1로 — 조사자는 1차 점수리 웨이브
   (걷는 중인 묶음들과 동일 파일) 완료 후로 지연. 근거: 충돌·재검증 낭비 + 원안 자신의
   직전 판정("거대 설계 불필요").
2. **manifest 탐지 축소**: 정규식 전면 탐지 → 허용목록 우선(오탐 소음 방지).
3. **verify 계층화 선행**: 원안 Phase 5 → 1차 웨이브 묶음9로 이미 이동(Smith 0705 승인).
4. **헌법 반영 선행**: 원안 §8-13 → 0705 개정으로 이미 완료(Rules 11~13).
5. **support 배치 강제**: contracts 모듈의 해석 권위 금지를 W1 수용 기준으로 명문화.
6. CSV 베이스라인은 지피티 환경 산출물이라 이관/재생성 없이는 Phase 0 미충족(§3-1).

증거 한계: 발주-준비 상위 기획. 슬라이스 발주 시점에 앵커·랜딩 상태 재확인(1차 웨이브가
계속 걷는 중). 처분 확정·품질 판정은 사람 몫.

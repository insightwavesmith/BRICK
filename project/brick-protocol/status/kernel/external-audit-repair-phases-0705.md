# 외부 감사 수정기획서 — 페이즈 정본 (0705 오후)

출처: 지피티 종합보고(S11~S17 통합, 패키지 A~I, 최종순위 11항) + 조사자 로컬 교차검증 +
형제 랜딩 실측(HEAD ce35122b 기준). **발견·판정 정본은 external-audit-repair-orders-0705.md**
— 이 문서는 그 위의 실행 순서(페이즈) 층이다. 발주-준비 문서이며 source truth·성공 판정
아님. 시공 = 형제 COO. 각 묶음 발주 시점에 앵커 재확인.

## 0. 제외 목록 — 이미 완료/진행 중 (재발주 금지)

지피티 종합보고는 업로드 아카이브 기준이라 아래 랜딩분을 전부 미수리로 표기한다.
**아래 항목을 이 보고서 근거로 재발주하지 마라.**

| 항목 | 종합보고 대응 | 실측 앵커(조사자 재확인) |
|---|---|---|
| 묶음1 본체 — expansion_node_budgets bool seal(writer 2곳)+RED | 패키지A 일부(S11-RED-001·S12-WR-003) | 커밋 125bfcff |
| 묶음3 — handoff 절대경로 상대화 | 최종순위 8(absolute path handoff 제거) | 커밋 91e4005f |
| T10 gap1 — expansion budget 출생 선언 kwarg | — | 커밋 c89f1732 |
| **T10 gap2 v2 — 승인근거→처분행 도달, approve-from-hold 공식화** | S13-HOLD-003 계열("route_decision_basis 주입 경로 없음") | 커밋 df9feb6c + 실빌딩 라이브 증명 ce35122b. gap2 발주에 편입됐던 S13-HOLD-003 픽스처 재검 결과는 형제 산출 확인 대기 |
| 묶음2 — S4 write_scope mixed diff + S1 재배선 (= **패키지 C 전체**, P3+P4+S11-RED-004) | 종합보고 P3·P4 | **걷는 중, 미랜딩**(driver.py:1214 `support:operator-driver` 저자 잔존으로 확인). 수용기준 7항 기확정 — 초안 나오면 지피티 독립 리뷰(핸드오프 §5) |
| harness-roadmap T1~T6 | — | 실효 스탬프(커밋 c00b26c4) |
| 감사 아카이브 재현성(P13/패키지 I) | — | 핸드오프 §5 각인 완료. 공식 tar 타깃 스크립트화만 묶음8 동승 |

## 1. 페이즈

### Phase 1 — T10 운전 선결 【1급, 병렬 가능, Smith 결정 불요】
- **묶음5** (= 패키지 A 일부 + 패키지 E):
  - WR-001: revision reader가 writer 선검증 재사용 — 최소 `_verify_add_only_revision` +
    `_verify_immutable_budget_fields` + `_verify_expansion_node_budgets` (지피티 P0
    최소수리안 채택; approval read-side 재확인 여부는 구현 시 정책 메모로).
  - WR-006: `gate_sequence_decision_from_record`가 ADMITTED_POLICY_ACTIONS 강제,
    `gate_action_sequence` 내부 action까지.
  - RED: forged valid-hash revision reject / record action="sideways" reject.
- **묶음1 잔여** (= 패키지 A 잔여):
  - base `expansion_budget=True` 거부(`_verify_expansion_budget_available`) + RED.
  - approval **hold identity** 소비(P2): revision packet에 `approval_hold_ref` 기록 +
    `_verify_approval_not_consumed` 확장(같은 hold, 새 approval ref 재사용 거부) + RED
    (expansion_budget=2 판에서 동일-홀드 이중 소비).
- 종료선: check_plan_revision_chain 전 프로브 green + 신규 RED revert 시 rc=1 + 격리 --all.

### Phase 2 — T10 첫 실전 확장 운전 【조사자, Phase 1 랜딩 후】
리허설 조각 확보됨(cleanup-wave-a design 산출물). S14 6단계 runbook, 단계5 strict
checker 필수(S14-T10-003 — corrupt 최신 rev의 조용한 직전-rev 후퇴 대비). 운전 직전
확장 조각 지피티 공격(핸드오프 §5 예약).

### Phase 3 — 행동 결함 마감 【2~3급】
- 묶음2 완주 게이트(진행 중 → 조사자 게이트 보고, 7항 대조).
- **묶음6** (패키지 B로 증보): 기존 잔여 bool 위생(route `max_attempts` 3곳 · step
  `attempt_index` · DSL `back(True)`/`reroute(budget=True)`) + **증보 2건**:
  `require_positive_int` 공용 helper(bool 명시 거부) 도입·위 표면 전부 경유 +
  정적 체커 `check_positive_int_bool_boundary`(bool guard 없는 positive-int 패턴 RED,
  픽스처로 각 표면 실제 파괴).
- **묶음4** (= 패키지 D, A안 기확정): onboard 승인 경로 공개 에러 + walker_resume generic
  처분 거부(stop만) + 동승 2건(portfolio projection `not_resumable_by` 표기 ·
  reroute 문구) + **문서 표면**(setup.md:227 held-result 정정 · quickstart
  frontier×hold_reason 처분 매트릭스).
- **묶음7** (P9): write_scope 매처 단일화 — assembly·task_order_preflight가
  Brick 정본(`brick.comparison._path_matches_scope`)을 공유.

### Phase 4 — 고객·릴리스 표면 【신설 2건】
- **묶음9 신설** (= 패키지 F, P7 — free-green 계층화) 【0705 오후 **Smith 승인 — 발주 가능**】:
  실측(지피티, 무-provider 환경): `check_profile.py --all` rc=1
  (`local CLI executable not found for adapter:gemini-local`), `--profile core` rc=0.
  조사자 기전 확인: `brick verify`(무인자)=--all(cli.py:623), gemini 체커의 sweep 가드
  (BRICK_CHECKER_PROFILE_SWEEP)보다 CLI 부재 에러가 선행 가능. 즉 **README가 약속한
  "provider 없이 초록불"이 fresh 머신에서 깨진다**.
  수리 방향(지피티 안): `brick verify`=hermetic no-provider green / `--all`=developer
  full sweep / `--live-provider`=실 CLI 준비도. **Smith 결정이 필요한 이유**: 헌법
  성공판정 ③("brick verify exit 0")과 README·install.sh·FIRST_USE 고객 표면의 의미가
  바뀌고, 온보딩 트랙(무료 초록불 단일화)과 합류함.
  종료선: provider CLI 없는 fresh 환경에서 brick verify rc=0 실측 + 기존 --all 동등성.
- **묶음10 신설** (= 패키지 G, P8 — wheel 패키징) 【소형, Smith 결정 불요】:
  조사자 실행 증거: `uv build --wheel` 산출물에 `brick_protocol/support/operator/`·
  `checkers/`·`connection/` **0파일**(recording 23·brick 5만 포함 — pyproject packages
  수동 목록 누락), 콘솔 스크립트는 `support.operator.cli` 지시 → non-editable 설치
  즉사(지피티 import 실측 ModuleNotFoundError와 합치). 현 고객 경로(pipx --editable)는
  무사고 — 릴리스 경로 전용.
  수리: packages 확장(우선) 후 discovery 검토 + wheel smoke 체커(빌드→격리 venv
  설치→cli import)를 release_gate에 동승.
- 순서 유연 조항: 실제 고객 fresh 설치가 임박하면 묶음9를 Phase 3 앞으로 당겨도 된다
  (S4 조항과 동형).

### Phase 5 — 문서·각인·후속
- **묶음8** (= 패키지 H + 0705 낮 증보분): 코드 수리 반영 후 실행 — checker-profile-map
  재생성 · 스킬 참조 수리 · 출처 오귀속 정정 · 집행 스탬프류 · README(온보딩 몫과 합류)
  · 감사 아카이브 공식 타깃 스크립트.
- **헌법 개정 비준**(constitution-amendment-draft-0705.md — Smith. 적대 검증 반영:
  16·15·14 등재 가능 / 11은 묶음5 후 재작성 문안 / 13은 AGENTS→헌법 이전 안건 / 12 폐기).
- **묶음11 신설(조건부)** (P11): pending gate consumer 4건 실구현
  (enforcement-ledger.yaml:13-22 — closure 완료 게이트 ×2 · adopted-reroute 재파견 텍스트
  · re_instruction 종료선). 묶음2 랜딩으로 "관찰→Link 게이트 소비" 배선 선례가 서면
  그 동형으로 착수. **착수 조건 = 묶음2 랜딩.**
- 회귀 재감사(동일 S1~S10 프롬프트, 델타 측정 — plus-status 아카이브 사용).

### 백로그 (재발주 대상 아님, 숙성)
S3 adapter-usage 타이밍 원장 창 · S12-WR-008/P10 raw/link 파서 규율 분열(strict vs
best-effort 명명 분리) · LOC-002 프로필 YAML 2건 표준화 · discipline-audit-0618 leaked
text 재작성/삭제 검토 · GOAL/ 링크 재지정(Smith 확인 후 묶음8 동승 가능) · 잔여 언트래킹.

## 2. Smith 결정 — 0705 오후 3건 전부 처리 완료

1. **헌법 비준 ✅** — Rules 11~13 등재 + 역사 문단 삭제 + 성공판정 ③ 갱신(0705 개정 반영 완료).
2. **묶음9 verify 계층화 ✅ 승인** — 발주 가능 상태로 전환(고객 표면 문구는 온보딩 트랙과 조율).
3. **A+ 2차 웨이브 ✅ 채택** — 정본 `aplus-wave-plan-0705.md` 신설. 착수 게이트 = Phase 1 랜딩
   + 묶음2 랜딩 + T10 첫 운전(상세는 그 문서 §1). 게이트 전 A+ 명의 코드 발주 금지.

## 3. 지피티 최종순위와의 조정 내역 (투명성)

지피티 순서(1 T10 parity → 2 bool → 3 free green → 4 write_scope → 5 재배선 →
6 홀드정책 → 7 gate replay → 8 경로 → 9 wheel → 10 docs → 11 archive) 대비:
- gate replay(7)를 Phase 1 묶음5에 동승(같은 T10 운전 차단 클래스 — 기존 묶음5 구성 유지).
- free green(3)은 Phase 4로 — Smith 게이트 필요 + T10 운전을 차단하지 않음.
- write_scope(4)·재배선(5)은 이미 묶음2로 걷는 중 — 신규 발주 없음.
- 경로(8)는 랜딩 완료(91e4005f) — 제외.
- 홀드정책(6)은 A안 기확정 — 결정 단계 생략, 착지만(묶음4).

증거 한계: 발주-준비 문서. 지피티 실측 중 무-provider rc=1(P7)과 wheel import 실패(P8)의
"실행"은 지피티 환경 산출이며, 조사자는 기전(코드)·wheel 내용물(로컬 빌드)로 재확인함 —
P7의 fresh 환경 rc 실측은 묶음9 종료선에서 닫는다. 처분 확정·품질 판정은 사람 몫.

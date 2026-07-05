# 외부 감사 수리 발주-준비 (0705) — 형제 COO 인계 정본

출처: 외부(GPT) 아키텍처 감사(S1~S10, 헌법 기준) → 조사자 세션이 로컬 실물로 전건
교차검증(MAJOR 5/5 CONFIRMED). 외부 감사 종합 판정 "철학 A급, 경계 집행 B급 미만 —
support 비판단 원칙이 안전장치에서 압박받는 중"은 조사자 판정과 일치. 이 문서는
발주-준비 산출물이며 source truth·성공 판정 아님. 실행 = 형제 COO.

## 검증 판정표

| id | 결함 | 실물 앵커(조사자 재확인) | 판정 |
|---|---|---|---|
| S9 | T10 예산 bool writer-reader 불일치 | 쓰기 무방비: plan_expansion.py:196, declaration_packets.py:1518(`not isinstance(v,int) or v<=0` — bool은 int 서브클래스라 True 통과) / 읽기 거부: walker_resume.py:415·427·482 | CONFIRMED |
| S5 | 위 결함의 RED 프로브 부재 | check_plan_revision_chain.py 'True' 히트 2건 전부 mkdir 옵션 | CONFIRMED |
| S4 | write_scope 반쪽 집행 — **실제 집행 결함**(Smith 0705: 구조 부채 아님, mixed diff commit 실오작동 경로) | driver.py `_write_need_complete_without_scoped_diff_for_plan` — allowed 경로 1개만 끼면 통과(any 판정), `observed_paths_outside_declared_scope` driver 소비 0회(grep) | CONFIRMED |
| S1 | support-authored Link HOLD | driver.py:1214 `transition_author_ref:"support:operator-driver"` + :105 frontier 전환 | CONFIRMED — 단 0702 가짜랜딩 사고 후 의도 랜딩된 안전장치(알고 진 축 부채) |
| S6 | 절대경로 handoff 유출 | walker_kernel.py:421 `str(building_root.resolve())` → :433 handoff 적재 → adapter_grant_policy.py:324 프롬프트 포함 | CONFIRMED |
| S3 | adapter-usage 타이밍 원장 창 | 재현 경로 미확정 | PLAUSIBLE — 백로그 |
| S8 | README expected 드리프트 | 기확인(온보딩 세션 통보 완료) | CONFIRMED — 온보딩 몫 |
| S10 | gh 전제 미표기 | README 첫 명령 구조 확인 | CONFIRMED — 온보딩 몫(무개발 기획 v2 §2 관문 인벤토리와 합치) |

## 발주 묶음 (id는 기존 피어 통보와 동일, 실행 순서는 아래 순서표)

### 묶음 1 — T10 bool 예산 봉합 (+RED 프로브) 【1순위·소형·비엔진】
- 내용: reader의 기존 방어 패턴(`isinstance(value,bool)` 거부)을 writer 2곳에 복제 —
  plan_expansion.py:196 `_validate_expansion_node_budgets`, declaration_packets.py:1518
  `_positive_int_mapping`. + check_plan_revision_chain.run_fixture_probes()에
  `expansion_node_budgets={<노드>: True}` reject 프로브 1건.
- 왜 1순위: 다음 매듭(T10 첫 실전 확장 운전)에서 밟는 지뢰 — writer가 받아준 개정판을
  재개가 거부하는 실오작동 경로.
- 종료선: 신규 프로브 RED/GREEN 쌍 + 기존 revision 체커 전 프로브 green + 격리 --all.

### 묶음 3 — handoff 절대경로 상대화 【2순위·소형·엔진 인접(Smith 게이트)】
- **원칙(Smith 확정)**: provider prompt / link_handoff_refs / durable evidence에
  `/Users/...`, `/home/...`, scratchpad 경로, 세션성 로컬 경로를 싣지 않는다.
- 내용: walker_kernel.py:421·433의 building_root 절대경로를 repo-상대 ref로 —
  예: building_root_ref="project/brick-protocol/buildings/<building_id>",
  from_step_output_ref="work/step-outputs/<...>/step-output.json". 실제 파일 접근이
  필요하면 support 내부에서만 resolve하고 Agent 프롬프트에는 evidence ref만 준다.
  세션경로 redaction 사고(0703 kc-slice1) 계열의 상류 봉합.
- 종료선: handoff payload에 절대경로 0건(픽스처 grep) + 기존 handoff/runtime-mail
  픽스처 green + 격리 --all.

### 묶음 2 — driver 커밋 게이트 재배선 (S4+S1) 【3순위·엔진 인접 — **Smith 0705 확정: 재배선**】
- **성격(Smith 프레임 확정)**: "S1 단독은 구조 부채다. S4는 실제 집행 결함이다. 묶음2는
  S4 때문에 반드시 수리하고, 그 김에 S1을 축 순화한다." — 철학 정리가 아니라
  **철학 정리 + write_scope 집행 결함 수리**. safety guard 제거가 아니라 저자/권한
  재배선이다.
- 목표 형태(Smith 결정문):
  ```
  support observes bad diff / fake landing
  → support records observation only
  → declared Link gate consumes that observation
  → Link gate produces HOLD / forward / reroute decision
  ```
- S4 신규 RED 사양(Smith 명세): allowed_paths=["src/**"], changed_paths=["src/fix.py",
  "README.md"] → 기대: HOLD/no commit/frontier not complete. 금지: allowed 경로가
  하나 있다는 이유로 commit.
- **수용 기준 7항(Smith 확정 — 전부 동시 충족 = 행동 동등성 + 축 순화)**:
  1. 기존 fake-landing 방어 픽스처 전부 green.
  2. no scoped diff → 기존처럼 human/COO 처분 필요 상태로.
  3. forbidden diff → 기존처럼 human/COO 처분 필요 상태로.
  4. allowed+outside mixed diff → 신규 RED: 반드시 HOLD/no commit.
  5. raw/link.jsonl에 transition_author_ref="support:operator-driver" 신규 행 0.
  6. support observation은 남음.
  7. Link gate 또는 declared policy consumption evidence가 남음.
- 구현 방향: 커밋 게이트가 `observed_paths_outside_declared_scope`(brick/comparison·
  write_observation이 이미 생성)를 fail-closed 소비. 홀드 도장은 Link 선언 게이트가
  관찰을 소비해 발화(필요 시 make-a-gate로 write-scope 게이트 어휘 1행 신설 —
  T10 expansion-approval 선례 동형).
- **순서 유연 조항(Smith)**: 실제 provider write / customer run이 임박하면 묶음2를
  묶음3보다 앞으로 당겨도 된다 — S4가 실오작동 경로이기 때문.

## 선행 통보분과의 통합 순서표 (T10 운전까지의 전체 길)

```
1급(운전 선결, 병렬 가능): 묶음1 · T10 저작 갭(assemble에 expansion_budget 인자)
                          · 대화형 승인 갭(run_approve_entry에 승인근거 인자)
2급: 묶음3(경로 유출)
3급(방향 확정 후): 묶음2(게이트 재배선, 행동 동등성 동반)
운전: T10 첫 실전 확장(조사자 — 리허설 조각 확보됨: cleanup-wave-a design 산출물)
각인: 스킬 3종 + 헌법·체인 문서 + 문서 체커 (각인 재료 10건 적립)
온보딩 몫: S8·S10 → 축2/3 발주에 흡수 (기통보)
백로그: S3 타이밍 원장 창 · adapter-error 홀드 forward no-op 기전 · wave-A 홀드 종결
       · 잔여 언트래킹 1,848(숙성 후)
```

## 0705 밤 증보 — 외부 감사 2차분(S13 홀드 생애주기 · S14 T10 운전 공격) 교차검증 반영

2차분은 아카이브 업로드로 전수+로컬 실측까지 수행됨. 조사자 교차검증 결과:

| id | 주장 | 조사자 검증 | 처분 |
|---|---|---|---|
| S13-HOLD-001 | adapter_error_frontier는 막다른 골목 — frontier 우선순위(link/spec.py:912)가 agent_incomplete로 노출, 승인 표면(onboard.py:3341 not_approval_hold)이 거부, 수동 forward는 재생물 부재 fail-closed, stop만 paper-stop 완결 | ✅ 앵커 전부 실물 일치. **조사자 백로그 "재개 no-op 기전 미규명"이 이것으로 규명·종결** (legacy-refgraph closure 사건의 정확한 기전) | **묶음 4 신설 + Smith 결정 1건**(아래) |
| S13-HOLD-002 | portfolio projection 홀드는 처분 표면을 보이지만 resume 불가한 별도 생애주기 | 앵커 확인 | 묶음 4에 동승(표면 분리 표기: not_resumable_by 명시 또는 개명) |
| S13-HOLD-003 | coo/human 게이트 홀드는 forward/reroute로 "통과 가능"하나 gate 충족이 아니라 우회 | ⚠️ **상충 실측**: 조사자 wave-A에서는 forward가 재홀드로 귀결 — 조건 차이(홀드 지점/게이트 재평가 시점) 미규명. **픽스처 재검 예약** — 기존 "대화형 승인 갭" 발주에 재검 D항목으로 편입 | 재검 후 확정 |
| S13-HOLD-004 | 처분 에러 문구가 reroute 누락 | ✅ walker_reroute_budget.py:161 실물 | 묶음 4 동승(문구 1줄) |
| S14-T10-001 | **같은 홀드를 새 승인 ref로 반복 소비 가능**(expansion_budget≥2 시 이중 확장) — 소비 추적이 approval ref만 봄 | ✅ 실물: _verify_approval_not_consumed(:727)가 ref만 검사, packet에 approval_hold_ref 저장 0건 | **묶음 1에 편입**: revision packet에 approval_hold_ref 기록 + 소비 검사에 hold identity 추가 + RED 프로브 |
| S14-T10-002 | bool 예산 (기확인) | 묶음 1 기존 항목과 동일 | — |
| S14-T10-003/004 | corrupt 최신 revision은 reader가 조용히 직전 rev로 후퇴 — strict 체커 필수 / 승인-후-크래시는 재시도 가능(OK) | 코드 경로 확인 | **T10 운전 runbook에 채택** — S14의 6단계 체크리스트(단계5 strict checker 필수)를 조사자 운전 절차 정본으로 |

### 묶음 4 (신설) — 홀드 생애주기 명확화 【소형·**Smith 0705 확정: A안**】
- **adapter-error 홀드 = 승인 홀드가 아니다(확정)**: generic 처분 표면에서 **stop만 허용**,
  forward/reroute/raise는 명시적 공개 에러로 거부(예: "adapter_error_frontier는 승인
  홀드가 아니에요 — stop으로 닫거나 재발주하세요"). frontier 우선순위·live 재실행 엔진
  수정은 하지 않는다(B안 폐기). 문서·고객 표면 안내도 stop/재발주로 통일.
  - 착지: onboard.py 승인 경로(3341 not_approval_hold 부근)의 adapter_error 분기 공개
    에러 문구 + walker_resume의 generic 처분 거부. 종료선: adapter-error 픽스처에서
    forward/reroute/raise rc≠0(공개 에러) · stop rc=0(paper-stop 완결) 쌍.
- 동승 소형 2건: portfolio projection 표면 분리 표기(S13-002 — not_resumable_by 명시
  또는 개명) + 처분 에러 문구 reroute 추가(walker_reroute_budget.py:161).

### 묶음 1 증보
- 기존(bool 봉합+RED)에 추가: revision packet `approval_hold_ref` 필드 기록 +
  `_verify_approval_not_consumed`가 hold identity 소비도 거부 + 동일-홀드 재소비 RED
  프로브. 근거: S14-T10-001 — 확장 예산 2 이상인 판에서 stale 승인 이중 소비 실측.

## 0705 심야 증보 — 외부 감사 3차분(S11 체커 커버리지 · S12 writer-reader 전수) 교차검증

형제 병행 랜딩 반영(c89f1732 T10예산 kwarg · 125bfcff bool seal · 91e4005f handoff 상대화).
**이미 봉합됨(재발주 금지)**: expansion_node_budgets bool(plan_expansion.py:199 +
_positive_int_mapping) = S11-RED-001·S12-WR-003. handoff 절대경로 = 묶음3. **잔여만 아래.**

| id | 주장 | 조사자 검증 | 처분 |
|---|---|---|---|
| S12-WR-001 | **위조 개정판을 reader가 합법으로 읽음** — writer 선검증(add-only·immutable·approval)은 강한데 reader(_load_declared_plan_packet)는 kind+plan_hash만 검사. 해시는 "파일이 자기자신과 일치"만 증명하지 "합법 개정"을 증명 못 함 | ✅ 실물: preverify는 :671 _verify_add_only_revision 호출하나 reader 로드경로엔 그 재검 0건 | **묶음5 신설(신규 MAJOR·구조)**: reader가 add-only·immutable validator 재사용 — writer 선검증이 정본 |
| S12-WR-006 | **resume이 기록된 게이트 결정을 재검증 없이 믿음** — writer는 허용 어휘(forward/hold/next/reroute)만 내는데 replay reader(from_record)는 임의 문자열 수용. 오염된 "sideways" 액션이 hold/reroute 분기를 빠져나감 | ✅ from_record에 ADMITTED 검증 0건(상수는 실존:26) | **묶음5 동승**: from_record가 ADMITTED_POLICY_ACTIONS 강제 |
| S11-RED-004 | driver 커밋 게이트가 allowed+forbidden 혼합은 잡는데 allowed+**scope밖-비금지** 혼합은 못 잡음 — 실제 customer sandbox에서 complete+commit 실측 | ✅ = S4의 체커면. **묶음2에 이미 포함**(체커 RED = README.md 혼합 픽스처 추가) | 묶음2 증보(RED 픽스처 명시) |
| S12-WR-002/S11-RED-002 | base plan expansion_budget=True 미봉합(형제는 node_budgets만 닫음) | ✅ isinstance(budget,bool) 미존재 확인 | **묶음1 잔여**: _verify_expansion_budget_available에 bool 거부 + RED |
| S12-WR-004/S11-RED-003 | route max_attempts=True — materializer 수용, plan_validation 거부(불일치) | ✅ route_materialization._positive_int에 bool 0건 | **묶음6 신설(소형)**: route bool 봉합 3곳 + reject 케이스 |
| S12-WR-005 | step-output attempt_index=True — writer 수용, resume reader 거부 | ✅ step_outputs 미봉합 | 묶음6 동승 |
| S12-WR-007 | write_scope 글롭 매처 드리프트 — 런타임(fnmatch)은 넓게, 저작/preflight(exact·/**만)는 좁게. 숨은 좁은 해석기 | ✅ 세 매처 실물 확인 | **묶음7 신설(MINOR)**: 저작 매처를 Brick 매처로 단일화(권고) |
| S11-RED-005/S12 DSL | back(True)·reroute(budget=True) 표면 수용 | PLAUSIBLE(후단 일부 방어) | 묶음6 동승(위생) |
| S12-WR-008 | raw/link.jsonl 파싱 규율 분열(driver skip vs resume hard-fail) | PLAUSIBLE(크래시 창) | 백로그 |

### 신설 묶음 요약
- **묶음5(구조·MAJOR)**: T10 개정판 reader 검증 강화(WR-001) + 게이트 replay 어휘 강제(WR-006).
  둘 다 "writer는 검증하는데 reader가 안 믿을 걸 믿는" 같은 클래스 — **T10 첫 확장 운전 전
  최우선**(위조 개정판이 운전 중 latest로 읽히면 상류 편입 금지가 무력화).
- **묶음6(소형)**: 잔여 bool 위생 — expansion_budget(base)·route max_attempts·step
  attempt_index·DSL back/reroute, 각 봉합 + RED. 묶음1 잔여 흡수.
- **묶음7(MINOR)**: write_scope 글롭 매처 단일화 — 저작측을 Brick 런타임 매처(정본)로 위임.

### 우선순위 갱신(T10 운전 선결 = 묶음1잔여 + 묶음5)
```
1급: 묶음5(reader 검증·게이트 어휘 — 구조) + 묶음1 잔여(base expansion_budget bool)
2급: 묶음2(S4+S1, README 혼합 RED 포함) — Smith 재배선 확정됨
3급: 묶음6(bool 위생) · 묶음4(홀드 명확화, Smith A/B) · 묶음7(매처) · 묶음3 ✅랜딩
```

## 0705 낮 증보 — 외부 감사 4차분(S15 문서드리프트 · S16 온보딩 여정 · S17 헌법 개정) 교차검증 + 조사자 로컬 잔여 수행

4차분 아카이브에는 project/** 부재 → 지피티가 status/kernel 정본 대조 불가(S15-DOC-011).
그 잔여 범위는 조사자가 로컬 스윕(kernel 정본 11문서, 문서별 레인 + 적대 렌즈 1, 전 레인
sonnet)으로 직접 수행. S15 수치 계열은 조사자 실행 재측정으로 전건 재확인.

### S15 교차검증 (지피티 발견 11 + 조사자 신규 2)

| id | 주장 | 조사자 검증 | 처분 |
|---|---|---|---|
| DOC-001/002 | README expected 불일치·첫 명령이 installer 진단 우회 | ✅ README.md:45 vs install.sh:186·193 / :133-148 분기 재확인 | **기존 S8·S10 동일건 — 온보딩 몫 기이관(v2 §5-1). 재발주 금지** |
| DOC-003~007 | checker-profile-map.md 수치 전면 stale | ✅ 실행 재측정 = 지피티 값 일치: profiles **41**·presets **29**·distinct kernel_checks **75**·module rows **212**·live ceiling **2**·walker **14**·overlap **16/13/9/8** (문서값 30/28/66/162/9/12/10). 추가: 문서 profile 표(:42)가 **삭제된 프로필**(agent_tool_hardening — diet 배치로 8분할 완료)을 현행 등재 | **묶음8 신설** |
| DOC-008 | setup.md:227 "raises an exception" | ✅ MAJOR — run.py:592-618이 held result 반환(:513-546 `_held_result_from_adapter_frontier_signal`) | **묶음4 동승**(A안 문서 표면) |
| DOC-009 | quickstart.md:62-63 홀드 처분 매트릭스 부재 | ✅ MAJOR — raise 가드 실물 walker_resume.py:395·:493 | **묶음4 동승** |
| DOC-010 | 헌법 역사 anchor 미해결 | **종결 — 발견 아님**: 두 문서 로컬 실존(goal-phases-0629 kernel 루트 / brick-6-…-0630 archive/0702-doc-archive/) | — |
| DOC-011 | project/ 스코프 누락 | **종결 — 조사자 로컬 수행**(아래 스윕). 회귀 재감사 시 아카이브에 status/kernel 포함(핸드오프 §5) | — |
| LOC-001(조사자) | **스킬 정본 참조 깨짐**: brick-task-author SKILL.md:475(+템플릿 사본 :470) → stall-attribution-amendment-0613.md가 archive/0702-doc-archive/로 이동 | ✅ find 재확인 | 묶음8 |
| LOC-002(조사자) | 프로필 YAML 2건 표준 위반(백틱 스칼라): building_skill_preset_agent_resource_boundary.yaml:75·gate_registry_single_source.yaml — 커스텀 `parse_yaml_subset`(check_profile.py:1096)만 통과, 표준 PyYAML 파스 실패 → 외부 도구 집계 함정 | ✅ 재현(MINOR) | 묶음8 동승 후보/백로그 |

### 로컬 스윕 — status/kernel 정본 11문서 (S15 잔여분, 조사자 직접)

| 문서 | 발견 | 처분 |
|---|---|---|
| goal-phases-consolidated-0702.md | 실질 0 (앵커갱신 3: HEAD 헤더 f4d7b58b→현행, declaration_packets :1491→1489, assembly :603 주석지점) | 갱신만 |
| **harness-roadmap-orders-0704.md** | **문서 실효(사고 위험)** — T1·T2·T3·T4·T5·T6 전부 이미 랜딩/발사(t1-tasklint-0704a~t6-holdvocab-0704a 빌딩 + task_order_preflight.py 배선 + work/return.yaml:9 received_deliverables_echo + return_fact.py good_enough, 조사자 재확인). 문서는 전부 미착수로 서술 | **실효 스탬프 각인(이번 커밋) — 재발주 금지** |
| harness-roadmap-orders-t7-t11-0704.md | 앵커갱신 다수(walker_kernel +24줄 패턴 등) + **오지점 앵커 2**(declaration_packets.py:403·:968 → plan_hash 실물 :1372, manifest hash :1606 — 조사자 재확인) + T11 종료선 커맨드 rc=1(lessons-ledger.yaml 최상위 dict, list assert 실패 — 조사자 재현) | T7~T11 발주 시 앵커 전면 재확인 필수 + 종료선 정정(묶음8) |
| checker-diet-order-plan-0704.md | 정본 지칭 파일(hardening.yaml) 삭제 완료(diet-batch0~5 집행 결과) — 집행-완료 표시 부재. 배치 수치는 정합 | 집행 스탬프(묶음8) |
| hold-disposition-vocabulary-0704.md | **출처 오귀속 1**(표 53·86행 "설계-질문 concern 재파견" 출처를 harness-roadmap §T6로 인용 — 실물은 goal-phases-consolidated-0702.md:242-244, 조사자 grep 재확인) + 수치 1(2회 vs 출처 1건) + 앵커갱신 3 | 출처 정정 1줄(묶음8) |
| evidence-postmortem-task-template-0612.md | 스킬명 낡음 1 (brick-hold-triage → brick-task-author PHASE 3 흡수, APPLY-LIST.md:24) | 명칭 갱신(묶음8) |
| coo-goal-loop-prompt-0702.md | 발견 0 (8건 전수 일치) | — |
| kernel-archive-classification-0705.md | 레인 보고 "git mv 서술 vs rename 이력 모순"은 **조사자 기각(오검)** — git rename 표시는 diff 시점 유사도 추론이라 plain mv를 반증 못 함. 유효 발견 1: discipline-audit-0618.md leaked-text 의심(skill-doc-resize-audit-0702.md:45 "일괄이동 제외" 지정 미언급 채 이관, 실물 첫 줄 확인) | 백로그(재작성/삭제 검토) |
| legacy-refgraph-census-0705.md | 후보 어조 잔존(이미 집행됨) + 4건 중 1건 이름 미특정 | 집행 스탬프(묶음8) |
| **GOAL/00-GOAL-OF-RECORD.md·00-INDEX.md** | **골 내비게이션 실효** — 심볼릭 링크가 0627/0629 문서를 지시. closeout-goal-0630이 ACTIVE GOAL 자기선언, 실운영 골 정본은 goal-phases-consolidated-0702. 00-GOAL-OF-RECORD의 Live checkout 지시(struct-surgery-0623 워크트리, HEAD 70160fb 0630)도 현행 main과 불일치 | GOAL/ 링크 재지정 or 안내 스탬프 — 묶음8, 골 내비게이션이라 **형제/Smith 확인 후** |

### 묶음4 증보 (문서 표면 확정 착지 — DOC-008/009 편입)
- setup.md:227 교체: "public `run_building_plan`은 adapter-error frontier 기록 후 **held
  결과를 반환**(hold_reason=adapter_error_frontier, 재개 가능 paused). 일부 하위/내부
  표면만 typed frontier signal을 raise."
- quickstart.md:62-63 아래 frontier_kind×hold_reason 처분 매트릭스 행 추가:
  human_review_waiting+fake_landing→forward 가능 / link_paused+budget→raise는
  budget_exhaustion만 / **agent_incomplete+adapter_error_frontier→generic approve 불가,
  stop 또는 fresh 재발주**(A안 어휘와 통일).
- 종료선 추가: 두 문서의 해당 절이 A안 어휘(stop-only)와 일치함을 grep으로 확인.

### 묶음 8 (신설) — 문서 드리프트 수리 【소형·비엔진·3급】
1. checker-profile-map.md: 고정 수치 제거(측정 명령만 유지) 또는 재측정값 갱신
   (41/29/75/212/2/14, overlap 16/13/9/8) + profile 표에서 삭제 프로필 제거.
2. 스킬 정본 참조 수리: brick-task-author SKILL.md:475 + 템플릿 사본 :470 →
   archive/0702-doc-archive/ 경로로 갱신(양 사본 동기).
3. hold-disposition-vocabulary 출처 오귀속 1줄 정정(→ goal-phases-consolidated:242-244).
4. harness-roadmap-t7-t11: declaration_packets 오지점 앵커 2건 재지정(:1372·:1606) +
   T11 종료선 커맨드를 dict 구조 기준으로 정정.
5. checker-diet-order-plan·legacy-refgraph-census 집행-완료 스탬프.
6. evidence-postmortem 템플릿 스킬명 갱신(brick-task-author PHASE 3).
7. 동승 후보: 프로필 YAML 2건 표준화(LOC-002) · architecture-map.md 날짜/재생성 ·
   GOAL/ 링크 재지정(형제/Smith 확인 후).
- 종료선: 갱신 수치 = 본 증보에 박은 재측정 명령 출력과 일치 · 갱신 참조 전건
  `test -f` green · 격리 --all green.

### S16 처분 — 온보딩 몫 통보 자료 (v2 정본 대조는 조사자가 로컬 완료)
- 지피티 제안 G01~G20 대조 결과: G01~G14 = v2 14관문과 일치 / **순신규 2건만**:
  G16(네트워크·프록시·SSL·다운로드), G17(디스크 용량·HOME 쓰기권한) / 인벤토리 승격
  후보 3건: G15(브라우저 device-code — v2 §3 "고객 몫 4종"에 기존재), G18(Windows —
  v2 §7-4 하중벽로 기존재), G19(앱 도구권한 — 앱 설치 관문에 권한 승인 단계 보강) /
  **중복 1건**: G20(지원 채널 — v2 §5-5 기존재).
- 지피티 L2 대본 초안은 v2 §3 보안 경계(결제 대행 금지·API 키 대행 금지·curl|sh 신뢰
  판단 금지·인증은 사람 몫)와 정합 — 온보딩 세션 입력으로 전달.
- 무료 초록불 이중 표면(install.sh:198-200 `brick verify` vs README:66-67 check_profile
  직접 실행): 고객 표면은 `brick verify` 단일화 권고 — 온보딩 몫.
- 처분: 온보딩 트랙 통보(기존 S8·S10 경로와 동일). 이 트랙 발주 없음.

### S17 처분 — 헌법 개정 후보: constitution-amendment-draft-0705.md 신설
적대 검증 렌즈 반영 결과: 등재 가능 **16(무수정)·15(경미수정)·14(신조어 제거)** /
**11은 묶음5 랜딩 후** 재작성 문안으로 상정(원안 "parent hash 바인딩"이 S12-WR-001이
지목한 해시-only 결함을 봉인하는 꼴) / **13은 신규 아님** — AGENTS.md:404-409 기존
원칙의 헌법 승격-이전 안건으로 재분류 / **12는 폐기 권고**(헌법 15행 동어반복 +
Movement 2종/lifecycle 어휘 구분 훼손). 비준·배치는 Smith.

### 우선순위 갱신 (0705 낮)
```
1급: 묶음5(구조 — T10 운전 선결) + 묶음1 잔여(base expansion_budget bool)
2급: 묶음2(S4+S1 재배선, README 혼합 RED 포함)
3급: 묶음6(bool 위생) · 묶음4(A안 확정 + setup/quickstart 문서 표면 동승) ·
     묶음7(매처) · 묶음8(문서 드리프트, 신설)
각인 대기: 헌법 개정(constitution-amendment-draft-0705.md, Smith 비준 후) +
          T9류 문서 체커(온보딩 v2 §3 T9와 합류 — expected/command 드리프트 RED)
경고: harness-roadmap-orders-0704.md 실효(T1~T6 기집행) — 재발주 금지 스탬프 각인됨.
```

증거 한계: 외부 감사 1차는 클론 불가 환경(커넥터 열람), 2차·3차는 업로드 아카이브 실측,
4차는 아카이브에 project/** 부재로 조사자 로컬 스윕이 잔여를 수행 — 조사자 교차검증이
실물 앵커를 보강했으나, 각 묶음 발주 시점에 앵커 재확인하라(코드 계속 변경 중).
처분 확정·품질 판정은 사람 몫.

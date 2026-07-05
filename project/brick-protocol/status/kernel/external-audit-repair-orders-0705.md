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

### 묶음 4 (신설) — 홀드 생애주기 명확화 【소형·Smith 결정 1건 대기】
- **Smith 결정: adapter-error 홀드의 정체** — (A) "승인 홀드가 아니다" 명확화: generic
  처분에서 stop만 허용, forward/reroute/raise는 명시적 공개 에러로 거부 + 문서·표면
  안내(외부 감사 권고 + 조사자 실측 지지 — 작고 안전) / (B) 승인 대상화: frontier
  우선순위 변경 + 실패 스텝 live 재실행(엔진 수정 큼). 조사자 권고 = **A**.
- 동승 소형 2건: portfolio projection 표면 분리 표기(S13-002) + 처분 에러 문구
  reroute 추가(S13-004).

### 묶음 1 증보
- 기존(bool 봉합+RED)에 추가: revision packet `approval_hold_ref` 필드 기록 +
  `_verify_approval_not_consumed`가 hold identity 소비도 거부 + 동일-홀드 재소비 RED
  프로브. 근거: S14-T10-001 — 확장 예산 2 이상인 판에서 stale 승인 이중 소비 실측.

증거 한계: 외부 감사 1차는 클론 불가 환경(커넥터 열람), 2차는 업로드 아카이브 실측 —
조사자 교차검증이 실물 앵커를 보강했으나, 각 묶음 발주 시점에 앵커 재확인하라(코드
계속 변경 중). 처분 확정·품질 판정은 사람 몫.

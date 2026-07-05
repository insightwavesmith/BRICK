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
| S4 | write_scope 반쪽 집행 | driver.py `_write_need_complete_without_scoped_diff_for_plan` — allowed 경로 1개만 끼면 통과(any 판정), `observed_paths_outside_declared_scope` driver 소비 0회(grep) | CONFIRMED |
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
- 내용: walker_kernel.py:421·433의 building_root 절대경로를 repo-상대 evidence ref로
  (예: project/brick-protocol/buildings/<building_id>). 세션경로 redaction 사고(0703
  kc-slice1) 계열의 상류 봉합.
- 종료선: handoff payload에 절대경로 0건(픽스처 grep) + 기존 handoff/runtime-mail
  픽스처 green + 격리 --all.

### 묶음 2 — driver 커밋 게이트 재배선 (S4+S1) 【3순위·엔진 인접·Smith 게이트】
- **Smith 확정 대기 1건**: S1 방향 — 재배선(권고: 조사자+외부 감사 일치) vs 현행 유지
  +헌법 각주. 아래는 재배선 채택 시 계약.
- S4: 커밋 게이트가 `observed_paths_outside_declared_scope`(이미 생성됨 — brick/comparison,
  write_observation)를 fail-closed 소비 — allowed+범위밖 혼합 diff는 커밋 전 정지.
- S1: driver의 Link lifecycle 직저작 제거 — support는 write-scope 관찰 기록까지만,
  홀드 도장은 Link 선언 게이트가 그 관찰을 소비해 발화(필요 시 make-a-gate로
  write-scope 게이트 어휘 1행 신설 — T10 expansion-approval 선례 동형).
- **필수 조건: 행동 동등성 증명** — 기존 가짜랜딩·forbidden-diff 방어 시나리오
  (postmortem-default-route-fake-landing-0702 계열 픽스처) 전부에서 "정지한다"는 결과
  동일, 저자만 Link로 이동함을 RED/GREEN 쌍으로.

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

증거 한계: 외부 감사는 클론 불가 환경(커넥터 열람)이었고 전수 실행 게이트는 미수행 —
조사자 교차검증이 실물 앵커를 보강했으나, 각 묶음 발주 시점에 앵커 재확인하라(코드
계속 변경 중). 처분 확정·품질 판정은 사람 몫.

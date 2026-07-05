# 헌법 개정 후보 초안 (0705) — S17 산출, Smith 비준 대기

출처: 외부(GPT) 아키텍처 감사 S17 제안 6건 → 조사자 로컬 교차검증(헌법·AGENTS 인용
전건 실물 일치 확인) → 적대 검증 렌즈(sonnet xhigh) 반증 시도 통과분만 문안 확정.
**이 문서는 제안이며 비준 전까지 헌법이 아니다** — 헌법 원칙("변화하지 않는 규칙만,
개정은 날짜와 함께 헌법 파일에서만")에 따라 비준·등재는 Smith가 BRICK-CONSTITUTION.md
에서 직접 한다. 번호 11~16은 추적용(현행 Rules 1–10 뒤 가정)이며 최종 번호는 비준 몫.

## 판정 요약 (적대 검증 후)

| 후보 | 주제 | 적대 판정 | 처분 권고 |
|---|---|---|---|
| 16 | bool은 예산 정수가 아니다 | **생존(무수정)** | 헌법 등재 1순위 |
| 15 | 경로·세션 식별자 durable/prompt 금지 | 생존(경미 수정) | 헌법 등재 |
| 14 | writer-reader 검증 대칭 | 부분수정(신조어 제거) | 수정 문안으로 등재 |
| 11 | plan 원본보존 + append-only revision | 부분수정(hash 문구 결함) | **묶음5 랜딩 후** 재작성 문안으로 상정 |
| 13 | 체커-동반 개발 | 기각(신규 아님) | **AGENTS.md:404-409 기존 원칙의 헌법 승격-이전** 안건으로 재분류 |
| 12 | support 관찰/결정 분리 | 기각(동어반복) | 폐기 — 헌법 15행+AGENTS.md:230-233이 이미 커버 |

## 등재 후보 문안 (수정 반영 확정본)

```
16. Movement, graph expansion, route replay, evidence attempt index 등 유한 예산·횟수
    값은 명시적 positive integer여야 한다. boolean은 어떤 경우에도 budget integer가 아니다.

15. durable evidence와 Agent prompt는 stable repo-relative 또는 evidence-relative ref로
    충분한 경우 absolute local path, username-bearing path, 세션 임시 식별자(영구
    evidence ref가 아닌 것)를 싣지 않는다.

14. 같은 durable contract를 쓰는 writer와 읽는 reader는 같은 검증 규칙을 공유해야
    한다. reader가 더 엄격하게 거부할 값은 writer가 persistence 전에 먼저 거부해야 한다.

13(이전). 새 feature/선언 표면은 그 표면을 게이트하는 체커 또는 mutation-RED 프로브와
    함께 land한다. 같은 슬라이스에 못 실으면 그 갭을 support evidence로 명명하고
    집행으로 치지 않는다. (AGENTS.md:404-409 원문의 승격-이전 — 중복 등재 금지,
    AGENTS에는 참조만 남긴다.)

11(묶음5 랜딩 후 상정). 선언된 Building Plan birth-certificate는 불변이다. HOLD 이후
    graph 확장은 최신 valid declared plan을 parent로 삼는 append-only revision으로만
    편입한다. revision은 원본을 덮어쓰지 않으며, 현재 HOLD에 대한 human/COO approval과
    합법성 검증(add-only·immutable validator 통과)에 바인딩되어야 한다.
```

## 후보별 근거·판정 상세

- **16 (생존, 무수정)**: 근거 실측 = S9·S14-T10-002(expansion_node_budgets bool),
  S12-WR-002(base expansion_budget), S12-WR-004(route max_attempts), S12-WR-005(step
  attempt_index) — 전부 "bool은 int 서브클래스" 단일 근본원인의 반복 표면. 기존 선례
  AGENTS.md:437 `budget_increment: <finite positive integer>` 의 일반화이며 랜딩된
  묶음1(125bfcff)과 정합. 순수 타입 불변식이라 구현 세부 없음 — 헌법 원칙에 최적합.
- **15 (생존, 경미 수정)**: Smith 기확정 원칙(external-audit-repair-orders-0705.md 묶음3
  원칙문)과 사실상 동일 — 랜딩(91e4005f)이 지킬 불변식의 사후 격상. 수정점: 원안
  "provider/session identifier" 가 정당한 영구 승인 ref까지 막을 소지 → "세션 임시
  식별자(영구 evidence ref가 아닌 것)"로 한정.
- **14 (부분수정 후 생존)**: 근거 실측 = S12-WR-001(위조 개정판 reader 통과),
  S12-WR-006(게이트 replay 어휘 무검증), S9 — "writer는 검증하는데 reader가 안 믿을
  걸 믿는" 클래스(묶음5와 동일 유형화). 수정점: 원안의 "declared interpreter",
  "predicate parity"는 repo 어디에도 없는 신조어(grep 0건)로 미확정 구현 개념을 헌법에
  선봉인하는 위험 — 존재하는 개념(같은 검증 규칙 공유)으로 재서술.
- **11 (재작성 후 상정, 묶음5 선행)**: T10 원본보존·append-only·승인-바인딩은 Smith
  기확정. 단 원안 "parent hash에 바인딩"은 S12-WR-001이 결함으로 지목한 바로 그
  메커니즘(해시는 자기일치만 증명, 합법 개정 증명 못 함)을 헌법에 봉인하는 꼴 —
  묶음5의 수리 방향(reader가 add-only·immutable validator 재사용)과 충돌. 묶음5 랜딩
  후 위 재작성 문안으로 상정.
- **13 (기각 → 승격-이전 안건)**: 동일 원칙이 이미 AGENTS.md:404-409에 명문화("체커-동반
  개발 원칙"). 신규 조항으로 넣으면 같은 법이 두 곳에 존재해 헌법 3행 "법의 단일 출처"
  위반. 올리려면 신규가 아니라 이전(AGENTS→헌법, AGENTS엔 참조만)으로 — 그 자체는
  Smith 배치 판단.
- **12 (폐기 권고)**: 헌법 15행("support는 사실만 기록하고 아무것도 판단하지 않는다.
  충분성+Movement 판단 = Link 게이트")의 동어반복 — 신규 규범 없음. 또한 원안이
  HOLD/forward/reroute/stop을 한 "lifecycle" 묶음으로 나열해 AGENTS.md:230-233의 정밀
  구분(Movement 리터럴은 forward/reroute 2종뿐, hold/stop은 lifecycle·판정 어휘)을
  뭉갠다. S1의 실질 교정은 신규 조항이 아니라 묶음2 재배선(수용 기준 7항)이 담당.

## 헌법에 올리지 않는 것 (S17 원 제안 중 상태·절차 판정 유지)

check_plan_revision_chain 실행 명령 / brick verify를 첫 초록불로 삼는 온보딩 절차 /
driver·plan_expansion 함수명 / RED 픽스처 이름 / adapter-error stop-only 정책(묶음4
A안으로 이미 운영 확정 — 규범이 더 필요하면 차기 개정에서).

증거 한계: 발주-준비·제안 문서. source truth·성공 판정·Movement 권한 아님. 비준·번호
확정·배치(헌법 vs AGENTS)는 Smith 몫. 근거 앵커는 0705 낮 기준 — 등재 시점에 재확인.

# BRICK Remaining-Frontier GOAL — 0709

Date: 2026-07-09 KST.
Parent: `02-unified-continuous-build-goal-0708.md` §11 parent closure의 `remaining_not_proven` 7항목을 부모로 상속.
Proof limit: support evidence only; not source truth, not success/quality judgment, not Movement authority.

## 골 한 줄

0709 parent closure 이후 남은 7 프론티어를, SHAPE/human-gate 경계를 지키며 전부 착지시킨다.

## 스코프 — 7 프론티어

```text
1. authoring 제품층 구현 (설계 完: building-call-authoring-architecture-plan-0709a → module/API/skill/hook 구현)
2. Route V2 SHAPE A 초과 확장 (Movement/route_target/concern_kind/Link/Agent/AgentFact) — 설계-먼저·human gate
3. cleanup-10e order-chain 수리 (optional 소형)
4. project vessel 물리분리 / 디렉토리·템플릿 이주 — 설계-먼저·human gate
5. build -> progress 자동 refresh UX
6. charter-fill 프롬프트-레벨 UX
7. 릴리스/배포 준비 (현재 repo proof 너머)
```

## 실행 물결

```text
W1: #1 authoring 구현 (설계리뷰 -> dev fan-out -> fan-in QA -> closure) + #3 병렬 소형
W2: #5·#6 고객 UX (W1 안정 후; 표면 불변 확인 시 병렬 가능)
W3: #4·#2 구조·확장 (각자 설계-먼저, 승인선 재확인 후 코드)
W4: #7 릴리스 게이트 (#1~#6 착지 후에만 개시)
```

순서 근거: 의존성·리스크·준비도 3축. #1은 설계 완료로 준비도 최상이자 UX(#5·#6)의 토대. #4/#2는 토대를 흔드는 구조·확장이라 뒤. #7은 배포 대상(1~6)이 서야 proof가 성립하므로 최후.

## 금지선

```text
- #2: 설계·human gate 이전 코드 확장 금지. 기본은 SHAPE A read-only advisory 유지.
- #4: vessel 파괴적 이동/삭제는 Smith 승인 후. 작업보존물 삭제 금지.
- COO는 축을 흐리지 않는다: Brick/Agent/Link/support 경계·Movement 권위 침범 금지.
- 반복실패 시 얕은 패치 금지: 3라운드+ 반복이면 근본원인부터.
```

## 증거 규율

```text
- 착지 판정 = clean detached worktree에서 check_profile.py --all RC=0 재현.
- 별도 commit -> push -> origin/main == HEAD 외부 재확인.
- 자기검증 금지: 내가 만든 문서를 내가 좋다 판정하지 않는다. 실행결과만 근거.
- 각 물결 종료 시 evidence 기록 후 forward 판정. 확장은 새 declared Building/human gate.
```

## COO 사고 규율 — 0709

```text
이 골 진행 동안 COO의 모든 결정·판단(발주 판정, 순서, 게이트, 착지 판정)은 sequentialthinking 커넥터로 사고한 뒤 내린다. Smith 0709 지시.
```

## 진행 로그

```text
[W1a 착지] structure_plan schema (커밋 ed092ae637, salvage anchor 94e4bbbf4에서 착지)
  - #1 authoring 선행: confirmed_building_call_request_v1_1 에 optional structure_plan 수용 + graph_topology validate + building-map lowering + 하위호환.
  - D1(building_call.py 수용·lowering) implemented / D3(하위호환 회귀 fixture) implemented / D2(fan-barrier checker) 코어 implemented.
  - 착지 판정: delta-green. baseline fcf937117 clean --all RED set == 착지 ed092ae63 RED set (양쪽 유일 RED=agent_session_id_redaction, 선재). W1a 새 RED=0, passed 61→62. write_scope 100% 준수(operator/checkers만).
```

## 마스터 잔여큐

```text
[W1a defer — 후속 소형 브릭] D2 방어 fixture 2갭 (Smith 0709 승인 defer):
  - duplicate_branch_source_rejection: structure_plan fan_out_groups/fan_in_groups 중복 브랜치·소스명 거부 probe 부재.
  - multiple_fan_out_groups: 복수 fan-out이 단일 fan_in 수렴하는 shape fixture 부재("if that shape is intended to be admitted" 조건부).
  (코드 로직은 존재, negative fixture·변이RED만 미비. authoring 프리셋으로 발주서 뽑아 COO 재검토 후 정식 CLI.)

[선재 결함 — 별건, Smith 판단 대기] agent_session_id_redaction RED:
  - handoff-coo-0709-remaining-frontier.md:107 artifact URL의 bare UUID(8f7781ef-...)가 session-id 패턴에 감지. baseline fcf937117부터 존재(W1a 무관). --all RC1의 유일 원인.
  - 성격: 진짜 session-id 누출 아님(claude.ai artifact id 오탐 성격). 핸드오프 문서 수정 + artifact 참조 처리 방식은 Smith 판단.

[W1b — 다음] authoring STEP3 방출 + 스킬 노출 + cap-hold enforcement (building-call-authoring 프리셋으로 발주서→COO 재검토→태우기).
[#3] cleanup-10e order-chain 수리 (소형, W1 병렬).
[방지책] "어떤 AI도 정식루트만 사고" 3층 기계강제 설계 — Smith 0709 지시로 워크플로 설계 진행 중(별도).
```

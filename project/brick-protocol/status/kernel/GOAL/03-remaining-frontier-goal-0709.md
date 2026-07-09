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

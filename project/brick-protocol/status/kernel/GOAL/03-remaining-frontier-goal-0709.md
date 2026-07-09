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

## 진행 로그 (0709, HEAD==origin==2d7cdb02e)

```text
[✅ W1a 착지] structure_plan schema (ed092ae637 + 골기록 3fc20420e). salvage anchor 94e4bbbf4.
  - D1(building_call.py 수용·lowering)·D3(하위호환 fixture) implemented / D2(fan-barrier checker) 코어 implemented.
  - 착지 판정: delta-green (baseline 대비 새 RED=0, passed 61→62). write_scope 100% 준수.

[✅ 방지책 3층 설계 착지] prevention-official-route-3layer-design-0709.md (22bb27baf).
  - 워크플로 wf_36994c47-3d4(11에이전트, 우회59건, 적대검증). L1 SessionStart / L2 PreToolUse Bash / L3 walker contextvar 토큰 게이트(유일 hard closure). 롤아웃 2단(observe→raise).

[✅ checker 오탐 수정 착지] agent_session_id_redaction claude.ai artifact URL UUID 예외 (2d7cdb02e).
  - 정탐 6종 불변(sess_/chatcmpl-/JWT/ULID/keyed/non-URL bare-UUID 여전히 감지) + evil.com URL도 감지(위장방어) + artifact URL만 통과. 직접 함수프로브+clean-tree --all RC0 검증.
  - ★효과: handoff:107 선재 session-id RED 근본 해소 → 이후 --all이 깨끗한 RC0. delta-green 우회 불요.
  - 이력: v1 design 어댑터 크래시(task의 session-id 리터럴이 어댑터 출력가드 자극) → v2에서 리터럴 제거·프로브헬퍼 재사용으로 재발주 complete.

[🔄 방지책 L3-3a observe 재발주] prevention-l3-3a-observe-0709-v2 (도는 중, design 단계).
  - v1 work-2에서 세션전환 사망(resume=dead_end 미완사망). 작업물 salvage refs/brick-salvage/prevention-l3-3a-observe-0709(9a9b7cf0f, +248: walker_kernel+5 토큰게이트·import_identity+49·cli.py+10 mint). v2가 이 참조로 이어받아 QA·closure 완주 목표.

[🔄 방지책 L1/L2 hook 재발주] prevention-l1-l2-hook-0709-v2 (도는 중, work 단계).
  - .claude/settings.json + SessionStart/PreToolUse 스크립트. v1은 작업물 0줄 사망 → fresh 재발주.

[✅ 정리] 워크트리 106→3(BRICK+도는 v2 2), buildings 산출물 30개 /tmp 아카이브(비파괴). 미커밋 작업물 전량 salvage(refs/brick-salvage/ 21개, c2-recovery 541파일·struct-surgery 447줄 포함). 디스크 ~1.1G 회수.
```

## 마스터 잔여큐

```text
[🔄 도는 중 — 완주·게이트·착지 대기]
  - L3-3a-v2 (walker 토큰 게이트 observe): 완주 시 게이트(observe전용·변이RED·clean floor build/resume/resume absent=0) → 착지.
  - L1/L2-v2 (hook): 완주 시 게이트(스크립트 단위실행·deny/allow 변이) → 착지. 실 hook 발동은 착지 후 새 세션에서 확인.

[⏳ Smith 결정 대기]
  - L3-3b (raise 살상 게이트): L3-3a observe clean floor 확인 후. walker raise 전환 = chokepoint critical. Smith 승인 필수.
  - 방지책 정직한 한계 2개(코드로 못막음): managed-settings hook잠금(allowManagedHooksOnly)=조직정책 / 고의 토큰위조 하드닝=별건(AI격리서명).
  - W2 UX(#5 build→progress refresh, #6 charter-fill) 착수 시점: W1a 착지됨, 표면 불변이면 병렬 가능.
  - W3(#4 vessel 물리분리, #2 Route V2 확장): 설계-먼저·human gate.

[⏳ W1 잔여 소형 (병렬 가능)]
  - W1a defer 2갭: structure_plan checker의 duplicate-branch·multiple-fan-out negative fixture + 변이RED. 코드 로직 존재, fixture만 미비.
  - W1b: authoring STEP3 방출 + 스킬 노출 + cap-hold enforcement (authoring 프리셋→COO 재검토→정식 CLI).
  - #3: cleanup-10e order-chain 수리 (소형).

[📦 보존 자산] refs/brick-salvage/ 21개 (git checkout으로 회수). buildings 아카이브=/private/tmp/brick-buildings-archive-0709(30개).
```

## 참고 아티팩트

```text
골 진행 대시보드 (0709, HEAD 2d3a8b077 기준): https://claude.ai/code/artifact/8a893a43-27c5-42a4-8bb8-a69a48cd2f28
방지책 3층 설계 전문: prevention-official-route-3layer-design-0709.md
```

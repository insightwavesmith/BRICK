# HANDOFF — 0710 COO 세션 (툴 버그로 조기 종료 / 새 세션 인계)

**Written:** 2026-07-10
**Checkout:** `/Users/smith/projects/BRICK` (git root) · HEAD `4f59421b7`
**Board:** `project/brick-protocol/status/kernel/ACTIVE_COO_GOAL.md` = necessity master ACTIVE
**작성자 처지:** 이 세션은 Claude Code 알려진 버그(tool-call 직렬화 오염, 아래 §6)로 조기 종료.
새 세션이 이어받는다. 이 파일은 넘겨받은 요약이므로 — **믿지 말고 실측 대조하라** (헌장 규율).

---

## 0. 이 세션이 실제로 한 일 (정직)

| 한 일 | 상태 |
|---|---|
| COO 헌장 정독 (`brick_protocol/agent/prompts/coo.md`) | 완료 · 순수 read-only 운영자 확인 |
| 이전 handoff(0709-pure-dev-master) 실측 대조 | 완료 · 대체로 정직했음, 단 워크트리 유실 근본원인은 놓침 |
| deku vs brick-protocol 경계 확정 | 완료 · 정상 구조 (아래 §3) |
| 0709→0710 타임라인 복원 | 완료 · 아티팩트 + master 큐 §9 |
| 전체 작업 리스트업 (#1–#44 실측 갱신) | 완료 · 보드 + master 큐 §9 |
| "정식 build 안전" 판단 | **부분 철회** — 성급했음, 아래 §4 |
| 프리셋 vs 발주서 워크트리 소실 샘플 테스트 | **미완** — 툴 버그로 중단, 아래 §5 = 다음 세션 최우선 |

**하지 말았어야 / 정정할 것:** "정식 build는 안전하다"를 코드 일부만 보고 단정하고 골 문서에
박았다. Smith가 "그럼 없던 문제를 있다고 판단한 거네?"로 지적. 실측을 더 하니 소실의 진짜 축이
L3 토큰 게이트가 아니라 **미완 시 WIP 앵커 비대칭**일 수 있음이 드러남 (§4–§5). 이건 아직 미확정.

---

## 1. 골 문서 상태 — ★커밋 안 됨 (최우선 처리)

이 세션에서 편집한 골 문서 3개 중 2개가 git untracked다. 새 세션이 clean checkout하면 사라진다.

```text
ACTIVE_COO_GOAL.md              = M (tracked, 수정됨)  · Live NOW 실측 갱신 + 0710 인계 요약절
master-work-queue-necessity-0709.md = ?? UNTRACKED · ★§9 절 신규(실측 상세) — 커밋 안 하면 소실
GOAL-PROMPT-necessity-master-0709.md = ?? UNTRACKED · 보드 authority인데 미추적
```

→ **다음 세션 첫 판단:** 이 3개를 Smith 승인 하에 git add + commit 할지. §9 실측 상세가
   여기 없으면 재조사 필요. (COO는 커밋 권한 밖 — Smith 지시 시 손으로.)

---

## 2. 실측으로 확정된 것 (믿어도 되나, 새 세션이 재확인 권장)

### 타임라인 세 사고 (상세 = master 큐 §9, 아티팩트)

```text
뿌리   = #2 hold/dispose 엔진 구멍 (driver.py finally가 hold/미완에도 워크트리 dispose)
사고1  = 워크트리 소실. L3 게이트 2번 land: fbbbe93e0(21:13 observe안전) / 15ccd10ac(22:14 lethal raise)
         → ★이전 handoff는 lethal land 15ccd10ac를 놓쳤음
사고2  = RV2 엔진 미착수. SHAPE A 뷰만 land, 엔진(route_scope/route_v2_engine) 코드 부재.
         못 연 이유 = #1-2 부채 (본발사=유실 재생산이라 금지에 가까움) = 사고1과 같은 뿌리
사고3  = 골 핀 thrash. 0709 하루에 ACTIVE 골 6회+ EXIT/재핀 (쉬운닫기 반복)
```

### git 사실 (재확인됨)

```text
가짜 EXIT f2fd50a35, 8f7d03b16 = 여전히 main ancestry 잔존 (보드 Status로만 무효화)
e87fe03af = operator WIP harvest (커밋 메시지에 harvest_from_wip=3700ea983), D3 Exit 아님
D3 3갈래 = body-v1(미완 NO_FRONTIER) / body-reland-0709c(frontier=complete + WIP 미수확) / token-harden(link_paused)
```

---

## 3. deku vs brick-protocol 경계 (정상 — 헷갈리지 말 것)

```text
BRICK repo (/Users/smith/projects/BRICK) = 빌딩 오케스트레이션 워크스페이스 (개발 도구)
  project/brick-protocol/ = 제품① 브릭 자기개발 dogfood. write_scope=brick_protocol/ 코드. ← master 골 대상
  project/deku/           = 제품② Smith의 Fugu-Ultra 재현 오케스트레이터.
                            write_scope = /Users/smith/projects/deku (별도 repo!). BRICK엔 에비던스만.
```

- deku 에비던스 63개 untracked는 **정상 흐름 미완결**(별개 프로젝트), brick 골과 무관. 혼입 금지.
- 물리 분리는 0709 human-gate에서 "KEEP, 미래 분할은 새 게이트+빌딩" 으로 결정됨. 지금 손대지 말 것.

---

## 4. "정식 build 안전" 판단 — 부분 철회 (미확정)

이 세션이 코드로 본 것 (맞는 부분):
```text
cli.py:2141 main() → :2153 mint_official_launch_token() (typed OfficialLaunchProof)
driver.py:719 "no fork" in-process → contextvar 토큰이 walker까지 전파
import_identity.py:278/290 enforce: token_present=True면 통과
→ 정식 brick build는 L3 토큰 게이트를 통과한다 (이 부분은 코드상 맞음)
```

**그러나 이것만으로 "안전"이라 한 건 성급했다.** 소실에는 두 번째 축이 있다:

```text
축1 (L3 게이트): 비정식 진입이 walker에 닿으면 raise → 그 워크트리 dispose. (정식 build는 통과)
축2 (WIP 앵커 비대칭): 정식으로 들어가도, 미완(QA 반려 등)으로 끝나면
     경로에 따라 작업물이 refs/brick/wip/에 남거나(run_building_plan park/stop) 소멸한다.
     → ★이 축을 이 세션은 끝까지 확인 못 함. 이게 Smith가 짚은 진짜 우려.
```

**결론: "정식 build 안전"은 축1에 대해서만 참. 축2(미완 시 소실)는 미확정.**
골 문서(보드·§9.2)에 "정식 build 안전, 우회 금지"라 박아뒀는데 — 이건 축2 확인 후 재검토 필요.

---

## 5. ★다음 세션 최우선: 프리셋 vs 발주서 워크트리 소실 샘플 테스트

Smith 지시: 빌딩 만들기 스킬의 두 경로를 실제로 돌려 워크트리 소실 여부를 실행 결과로 확인.

```text
경로A 프리셋 모드   = brick build --task/--preset
경로B 발주서/그래프 = build() one-call 또는 cli build --graph-decl
질문 = 각 경로가 미완(QA 반려 등)일 때 워크트리가 사라지나? WIP ref 남나?
```

### 스킬이 이미 준 결정적 단서 (brick-task-author 발사 체크 7·8번)

```text
- WIP 보존은 run_building_plan의 park/stop 경로에만 걸린다 (run.py:756 _anchor_park_stop_wip).
- cli build --graph-decl (= run_goal_approve_entry proposal-approval 분기)은
  최초 발사에서 QA 반려로 미완되면 WIP 앵커 없이 워크트리 처분 → 작업물 소멸.
  (0708 실측: fugu 3h 개헌 이주 500+파일 소멸)
- 즉 소실 여부는 authoring form(프리셋/그래프)이 아니라, 그 form이 어느 launch 경로로
  materialize되느냐 (run_building_plan park vs proposal-approval 최초발사)에 달렸다.
```

### 이 세션이 코드로 확인한 것 (run.py쪽만, cli쪽 미완)

```text
run.py:643 _anchor_park_stop_wip 정의, :756 에서 호출.
run.py:749/767 _with_close_wip_anchor (정상완료/held 경로).
→ run_building_plan은 park/stop 미완에서도 WIP 앵커를 건다 (확인됨).
→ ★남은 확인: cli의 proposal-approval 최초발사 경로가 이 앵커를 정말 안 거치는지.
   (grep proposal_approval brick_protocol/support/operator/cli.py 부터 이어가면 됨)
```

### 샘플 테스트 안전 설계 (미실행 — 다음 세션이 판단해 실행)

```text
- adapter:local work 노드로 무해 발사 가능 (실제 LLM 불요, 빠름). 단 verdict 노드는 local 금지.
- write_scope를 /tmp scratch 등 무의미 경로로 한정 → project/ 실파일 안 건드림.
- 미완 유도: QA 반려 or 없는 deliverable. 발사 후 worktree 경로 실존 + WIP ref 존재 실측.
- 이건 빌딩 발주가 아니라 엔진 동작 프로브 = "unavoidable operator maintenance" 예외로 손 실행.
  단 실 어댑터/시간 드는 발사는 Smith 확인 후.
```

---

## 6. 왜 이 세션이 끝났나 — 툴 버그 (Claude Code 알려진 회귀)

```text
증상: 긴 세션에서 tool-call 직렬화 오염 → 툴 호출이 실행 안 되고 XML 텍스트로 새어나옴.
      한 번 깨지면 in-context few-shot poisoning으로 뒤 호출까지 연쇄 오염 (세션 내 복구 불가).
트리거: 시퀀셜 씽킹의 거대한 thought 블록(한국어+코드블록+특수문자) + 파이프/멀티라인 Bash.
근거: GitHub 이슈 #66400, #63870, #62344, #64235.
완화: 새 세션 시작(근본) · CLAUDE_CODE_DISABLE_1M_CONTEXT=1 · 툴 호출 작게 쪼개기.
→ 새 세션에서는: 시퀀셜 씽킹 thought를 짧게, Bash에 파이프/멀티라인 최소화.
```

---

## 7. 다음 세션 체크리스트

```text
1. COO 헌장 먼저 읽기 (brick_protocol/agent/prompts/coo.md).
2. 골 문서 3개 커밋 여부 Smith 결정 (§1). master 큐 §9가 없으면 이 handoff로 복원.
3. ★프리셋 vs 발주서 워크트리 소실 샘플 테스트 (§5) — Smith 최우선 지시.
   먼저 cli proposal-approval 경로 코드 확인 → 무해 샘플 2건 실발사 → 소실/WIP 실측.
4. 그 결과로 "정식 build 안전" 판단(§4) 및 골 문서 §9.2 확정/정정.
5. 그 다음에야 기반 3종(#2/#24/#1) 발주 논의 — 소실 메커니즘 확정이 선행.
6. 경로 오기록 주의: 코드=brick_protocol/(언더스코어), 문서=project/brick-protocol/(하이픈),
   빌딩=~/.brick/project/brick-protocol/buildings/ (repo 밖 홈).
```

---

## 8. 경로

```text
Board:    project/brick-protocol/status/kernel/ACTIVE_COO_GOAL.md
Charter:  project/brick-protocol/status/kernel/GOAL-PROMPT-necessity-master-0709.md (UNTRACKED)
Queue:    project/brick-protocol/status/kernel/master-work-queue-necessity-0709.md (UNTRACKED, §9=이 세션)
COO헌장:  brick_protocol/agent/prompts/coo.md
Prev HO:  project/brick-protocol/status/kernel/HANDOFF-session-0709-pure-dev-master.md
This:     project/brick-protocol/status/kernel/HANDOFF-session-0710-coo-worktree-probe.md
Skill:    brick-task-author (발사 체크 7·8 = WIP 앵커 비대칭 정본)
Buildings:~/.brick/project/brick-protocol/buildings/
```

## 9. 한 줄

```text
이 세션: 타임라인 복원 + 리스트업 완료. "정식 build 안전"은 성급 판단(축1만 참, 축2 미확정).
다음 세션 최우선 = 프리셋/발주서 워크트리 소실 샘플 테스트로 축2 확정 후 골 문서 정정.
골 문서 2개 UNTRACKED — 먼저 보존. 툴 버그로 조기 종료, 새 세션 필수.
```

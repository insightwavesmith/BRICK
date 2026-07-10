# HANDOFF — 0710c COO 세션 (소실 프로브 1발 + 정적 워크플로우 발사 / 사용자 조기 마감)

**Written:** 2026-07-10
**Checkout:** `/Users/smith/projects/BRICK` (git root)
**직전 커밋(무변경):** `dce5160d0` — 이 세션은 **커밋/파일 변경 없음** (프로브·워크플로우만, project/ 무접촉)
**Board:** `project/brick-protocol/status/kernel/ACTIVE_COO_GOAL.md` = necessity master ACTIVE (그대로)
**진입정본(직전):** `HANDOFF-session-0710b-tool-bug-restart.md`
**This:** `HANDOFF-session-0710c-loss-probe.md`
**마감 사유:** Smith가 워크플로우 회수 전 "지금까지 정리해 넘겨라" 지시 → 조기 마감.
  이 세션은 툴버그 없이 정상. **믿지 말고 실측 대조하라.**

---

## 0. 이 세션이 실제로 한 일 (정직)

| 한 일 | 상태 |
|---|---|
| 0710b handoff 실측 대조 | 완료 · 아래 §1 표. 대부분 일치, refs 값만 정정 |
| COO 헌장 정독 (`brick_protocol/agent/prompts/coo.md`) | 완료 · 순수 read-only 재확인 |
| ★소실 프로브 A 발사 (Smith 2회 승인) | 완료 · 결과 결정적 (§2) |
| 프로브 A 잔재 정리 | 완료 · git 상태 무변화 확인, /tmp marker 제거 (§2) |
| ★축2 정적 워크플로우 발사 (Smith 교정: "실발사 말고 워크플로우로 실측") | **발사됨 · 결과 미회수** (§3) |
| project/ 파일·커밋 변경 | **없음** (프로브는 scratch/tmp만) |

**다음 세션 최우선:** §3 워크플로우 결과 회수(resume) → 축2 확정 → queue §9.2·보드 최종 판정.

---

## 1. 0710b handoff 실측 대조 결과

| 0710b 주장 | 이 세션 실측 | 판정 |
|---|---|---|
| HEAD = `dce5160d0` | `git log` 일치 | ✅ |
| charter/queue/발주서 tracked | `git ls-files` 3파일 확인 | ✅ |
| 보드 = necessity master ACTIVE | `ACTIVE_COO_GOAL.md` head 확인 | ✅ |
| .venv 정본 실행 정상 | `build --help` EXIT 0 | ✅ |
| 발사표면 `--graph-decl`/`--action{forward,stop}` | help 출력 일치 | ✅ |
| pipx `brick` 깨짐 | 심링크는 존재, **실행은 미검증**(안 돌려봄) | ⚠️ 부분 |
| baseline worktree=12 | 실측 12 | ✅ |
| baseline refs/brick/salvage=**378** | 실측 **355** (`git for-each-ref refs/brick/ \| wc -l`) | ❌ **정정** |

★ refs 값 378은 stale. 이 세션 실측 정본 = **worktree 12 / refs/brick 355**. 다음 세션도 재측정하라
  (프로브가 남긴 게 있으면 변함 — 단 이 세션 프로브 A는 git에 아무것도 안 남김, §2 확인).

---

## 2. ★프로브 A — 결정적 결과 (graph-decl proposal-approval 첫 발사)

Smith 2회 승인(발사 GO + "adapter는 codex-local로 그대로 발사"). 실 codex-local로 발사함.

### 발주서 (scratch, session-isolated)
`<scratch>/probe-loss-A-graphdecl-incomplete.yaml` — work 노드 1개, `write:true`,
write_scope=`/tmp/brick-probe-A-marker.txt`, D1=dirty marker 생성, D2=존재않는 파일 read(미완 강제유도).

### 발사 명령 (재현용)
```text
.venv/bin/python -m brick_protocol.support.operator.cli build \
  --graph-decl <probe-A.yaml> --forward --adapter adapter:local \
  --output-root <scratch>/probe-out --overwrite-existing
```
주의: `--action stop` dry검증을 먼저 하면 evidence root가 생겨 `--forward`가 `building_root_exists`로
  거부됨 → `--overwrite-existing` 필요. (또는 dry 생략)

### 실측 결과 (베이스라인 12/355 대비)
```text
frontier_kind          = human_review_waiting   ← dispose 아님, review 대기 park
customer_visible       = not_ready
worktrees 발사후        = 12  (delta 0)
refs/brick 발사후       = 355 (delta 0)
capture/events.jsonl event_type 시퀀스:
  building_opened → brick_opened → agent_received → agent_returned
  → brick_compared → link_carry/movement/transfer
  ★ worktree/sandbox/dispose/wip lifecycle event 없음
     (grep이 초기에 "worktree" 2건 잡았으나 = work_statement 텍스트 반향, 실 이벤트 아님. 오판 정정함)
agent-return: made_changes=true / changed_files=[]  (codex가 /tmp에 직접 씀, worktree 밖이라 git 미추적)
/tmp/brick-probe-A-marker.txt = 실제 생성됨(14B) → agent가 codex로 진짜 실행됨(스텁 아님)
```

### ★결론 (신중)
```text
이 경로(graph-decl proposal-approval 첫 발사)는 worktree sandbox를 생성하지 않음.
0710b §5가 소실 뿌리로 지목한 driver.py:940 create_worktree_sandbox = 이 경로에서 미호출.
미완(D2)이 유도됐지만 결과 = dispose(소실) 아니라 human_review_waiting park.
∴ 이 경로에서는 축2 소실이 재현되지 않음.
```

### ★★단정 금지 (핵심 한계)
```text
이건 "축2=소실없음" 확증이 아니다. 프로브가 worktree 생성 지점에 도달 못 했으므로
dispose 관찰 기회 자체가 없었다. 소실 뿌리는 worktree를 실제 만드는 경로
(run_building_plan work-write / driver.py:940 실호출)에서 봐야 하며, 그건 아직 안 봤다.
0710b §2의 "정식진입해도 미완이면 소멸" 의심 = 이 경로로는 검증 불가. 다른 경로 필요.
```

### 잔재 정리 (완료)
```text
git worktree/refs = 12/355 무변화 확인 (프로브가 git에 아무것도 안 남김).
/tmp/brick-probe-A-marker.txt = rm 완료.
evidence root <scratch>/probe-out/... = scratchpad(session격리, project/ 무접촉)에 프로브 기록으로 보존.
```

---

## 3. ★축2 정적 워크플로우 — 발사됨·결과 미회수 (다음 세션 즉시 resume)

Smith 교정: **"이거 꼭 발사해야 돼? 워크플로우로 실측 때리면 되잖아. 정식루트 타서 홀드 물려두면 되는거 아냐?"**
→ 소실 뿌리는 driver.py finally 분기에 **정적으로** 존재하므로, 실 LLM 발사 없이 코드 read로 확정 가능.
→ 워크플로우 발사(read 3 → adversarial verify → synthesize).

### 워크플로우 좌표
```text
Run ID:     wf_631b8b7f-429
scriptPath: /Users/smith/.claude/projects/-Users-smith-projects-BRICK/26dd2693-2c81-40a3-88e3-b07aedeb5b34/workflows/scripts/loss-axis2-static-probe-wf_631b8b7f-429.js
Transcript: /Users/smith/.claude/projects/-Users-smith-projects/26dd2693-2c81-40a3-88e3-b07aedeb5b34/subagents/workflows/wf_631b8b7f-429/
상태(마감시): read 3개 agent started, journal에 completed 미기록. agent jsonl 02:37~02:39 갱신·대용량(110~301KB) = 진행중.
```

### ★다음 세션 회수법
```text
1) 먼저 journal 확인: Read <Transcript>/journal.jsonl — completed 있으면 결과 거기.
2) 미완이면 resume: Workflow({scriptPath: "<위 scriptPath>", resumeFromRunId: "wf_631b8b7f-429"})
   완료된 agent는 캐시 반환, 미완만 재실행.
3) 반환 스키마: { synth: {headline, per_path_verdict[], residual_not_proven[]}, findings[] }
   per_path_verdict = driver worktree-run / run_building_plan park-stop / proposal-approval 3경로별
   SAFE_ANCHORED | LOSS_RISK_DISPOSE | NOT_A_WORKTREE_PATH | UNCERTAIN.
```

### 워크플로우가 답하는 3질문 (COO가 좌표 사전정찰)
```text
Q1 driver-finally: driver.py ~940 worktree run의 미완 close가 무조건 dispose냐,
   anchor_wip_snapshot로 WIP 먼저 보존 후 dispose냐. dispose가 anchor 건너뛰는 미완경로 있냐.
Q2 run-park-stop: run.py:643 _anchor_park_stop_wip / :564 _with_close_wip_anchor —
   park/stop close가 항상 앵커 거치냐. 앵커 안 거치고 release하는 경로 있냐.
Q3 proposal-approval: onboard.py:2769 run_goal_approve_entry 첫발사가 worktree 만드냐
   (프로브 A: 안 만듦 = human_review_waiting에서 멈춤. 코드로 확인/반박).
   승인 후 continuation은 driver worktree 경로 타냐. 이 family가 소실위험 경로냐 아니냐.
```

### ★★COO가 발견한 신호 (0710b §5 단정과 어긋남 — 워크플로우가 확정 중)
```text
0710b §5: "driver.py finally가 미완이면 무조건 dispose(작업물 소멸)".
그러나 이 세션 grep 실측:
  driver.py:176-177  wip_anchor_ref = "" unless a non-complete worktree run preserved WIP
  driver.py:1059 finally → :1066 anchor_wip_snapshot(...) → :1076 reclaim_wip_anchor
  driver.py:50/55  anchor_wip_snapshot / reclaim_wip_anchor import
→ finally 안에 이미 WIP 앵커 시도 로직 존재. "무조건 dispose"가 아닐 수 있음(조건부일 것).
  어떤 미완이 anchor 타고 어떤 게 안 타는지 = 정확히 축2 핵심 질문 = 워크플로우가 확정.
∴ 다음 세션은 "무조건 dispose" 전제로 #2 발주하지 말 것. 워크플로우 결과로 실제 분기부터.
```

---

## 4. 다음 세션 체크리스트

```text
1. COO 헌장 먼저 (brick_protocol/agent/prompts/coo.md) + 헌법(BRICK-CONSTITUTION.md).
2. HEAD=dce5160d0 위에서 시작 확인. baseline 재측정(worktree/refs 12/355 대비).
3. ★워크플로우 wf_631b8b7f-429 결과 회수 (§3 회수법) — 축2 3경로 판정 확보.
4. 그 결과 + 프로브 A(이 경로는 소실 아님)로 축2 확정 → queue §9.2·보드 "정식 build 안전" 최종 판정/정정.
   ★ driver.py finally에 anchor 로직 실존(§3말미) → "무조건 dispose" 전제 폐기하고 실제 분기부터.
5. 필요시 프로브 B(정식 write 경로 = worktree 실생성) — 단 Smith 지시는 "워크플로우 실측 우선".
   정식루트 홀드 park 관찰이 필요하면 실발사보다 코드 read/워크플로우 먼저.
6. 그 다음 기반 3종(#2 hold/dispose · #24 L3-3b raise · #1 land강제) 발주 논의.
```

## 5. 경로

```text
Board:    project/brick-protocol/status/kernel/ACTIVE_COO_GOAL.md
Charter:  project/brick-protocol/status/kernel/GOAL-PROMPT-necessity-master-0709.md (tracked)
Queue:    project/brick-protocol/status/kernel/master-work-queue-necessity-0709.md (§9.2 축1/축2, tracked)
COO헌장:  brick_protocol/agent/prompts/coo.md
헌법:     BRICK-CONSTITUTION.md
Prev HO:  project/brick-protocol/status/kernel/HANDOFF-session-0710b-tool-bug-restart.md
This:     project/brick-protocol/status/kernel/HANDOFF-session-0710c-loss-probe.md
CLI실행:  .venv/bin/python -m brick_protocol.support.operator.cli
소실뿌리 좌표: driver.py 176-177/940/1059-1080(finally+anchor) · run.py 564/643 · onboard.py 2769
워크플로우: scriptPath 위 §3 · Run ID wf_631b8b7f-429 · resumeFromRunId로 회수
```

## 6. 한 줄

```text
이 세션: 프로브 A 발사(Smith승인) = graph-decl proposal-approval 첫발사는 worktree 안 만들고
human_review_waiting park (소실경로 아님, 단 worktree생성경로는 미검증). Smith교정으로 축2를
실발사 대신 정적 워크플로우(wf_631b8b7f-429)로 실측 발사 = 결과 미회수. ★COO 발견: driver.py
finally에 anchor_wip_snapshot 실존 → 0710b "무조건 dispose" 전제 흔들림. 다음: 워크플로우 회수
→ 축2 확정 → §9.2 최종판정. project/ 무변경, 툴버그 없음.
```

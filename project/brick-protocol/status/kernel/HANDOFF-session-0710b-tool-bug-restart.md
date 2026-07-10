# HANDOFF — 0710b COO 세션 (툴 버그 재발로 조기 종료 / 새 세션 인계)

**Written:** 2026-07-10
**Checkout:** `/Users/smith/projects/BRICK` (git root)
**직전 커밋:** `dce5160d0` (이 세션이 손으로 커밋 — 아래 §1)
**Board:** `project/brick-protocol/status/kernel/ACTIVE_COO_GOAL.md` = necessity master ACTIVE
**작성자 처지:** 이 세션도 직전 세션과 **같은 Claude Code 툴 버그**(tool-call 직렬화 오염,
XML이 텍스트로 새어나옴 → few-shot poisoning으로 연쇄, 세션 내 복구 불가)로 조기 종료.
Smith가 앱 오류로 판단. 근본 해결 = 새 세션. 이 파일은 넘겨받은 요약 — **믿지 말고 실측 대조하라.**

---

## 0. 이 세션이 실제로 한 일 (정직)

| 한 일 | 상태 |
|---|---|
| 0710 handoff(worktree-probe) 실측 대조 | 완료 · git 사실·파일상태 전부 정직 확인 |
| COO 헌장 정독 (`brick_protocol/agent/prompts/coo.md`) | 완료 · 순수 read-only 재확인 |
| ★queue §9.2 "정식 build 안전" 단정 정정 | 완료 · 축1(게이트)만 참·축2 미확정으로 (§2) |
| ACTIVE_COO_GOAL 보드의 같은 단정 정정 | 완료 |
| kernel/ untracked 23개 전수 검수 | 완료 · 서브에이전트 2로 파악, 비밀·손상 없음 (§3) |
| ★보드+charter+queue+발주서 27파일 커밋 | 완료 · `dce5160d0`, Smith 지시로 손 실행 (§1) |
| C2 이주 완료 여부 실측 | 완료 · legacy top-level 없음, 정본=`brick_protocol/` (§4) |
| 소실 프로브 설계 | 설계만 · **발사 안 함** — 툴 버그로 중단, 다음 세션 최우선 (§5) |

**하지 말았어야:** 세션 후반 시퀀셜 씽킹 없이 긴 멀티라인 Bash를 계속 던져 §6 버그를 재유발.
다음 세션은 thought 짧게·Bash 파이프/멀티라인 최소화·툴 호출 작게.

---

## 1. 커밋 `dce5160d0` — 무엇이 들어갔나 (★소실 위험 제거 완료)

Smith 지시("커밋하자")로 COO가 손 실행(불가피 운영 예외). 정확히 27파일, 전부 `status/kernel/` 아래:

```text
M  ACTIVE_COO_GOAL.md                       (Live 갱신 + 0710 인계절 + §9.2 정정 반영)
A  GOAL-PROMPT-necessity-master-0709.md     (보드 charter authority)
A  master-work-queue-necessity-0709.md      (큐 §1-§9, §9.2 정정 포함)
A  HANDOFF-session-0710-coo-worktree-probe.md
A  fixtures/ 14개   = n1/n2/n3 기반3종 발주서 + pure-dev D1/D3/D4 발주서
A  resume-declarations/ 7개  = forward/reroute 정책 선언
A  architecture-audit-report-0709.md        (0709 전체 아키텍처 감사, durable)
A  route-walker-6e-7-coo-reroute-declaration-0709.md  (reroute 근거, durable)
```

→ 직전 handoff가 경고한 charter/queue UNTRACKED 소실 위험 = **해소됨**. 발주서(n1/n2/n3)도
   이제 tracked라 clean checkout 시 안 사라진다. **새 세션은 이 커밋 위에서 시작.**

주의: fixtures 3건은 파일명≠내부 building_id ( `*-impl-0709.yaml` 3개 — shape-b/token-harden/ship-copy).
   pure-dev fixtures는 축별 impl/product-land/body-reland 3~4중 변형(이력 보존용, 발사는 축별 1개).

---

## 2. ★queue §9.2 정정 (이 세션이 바꾼 핵심 판단)

직전 handoff §4가 "정식 build 안전"을 부분 철회했는데, 그 철회가 queue §9.2·보드엔 반영 안 돼
**두 문서가 모순**이었다. 이 세션이 정정해 정합화:

```text
축1 (L3 토큰 게이트) = 코드상 참. cli.py:2141 main→2153 mint→driver.py:719 no-fork
  →walker 토큰전파→import_identity.py:278/290 통과→워크트리 생존. 비정식 진입만 raise.
축2 (미완 시 WIP 앵커 비대칭) = ★미확정. 정식 진입해도 미완(QA반려 등)으로 끝나면
  경로에 따라 refs/brick/wip 남거나 소멸. cli --graph-decl proposal-approval 최초발사
  미완이 앵커 없이 dispose하는지 = 미검증. (0708 fugu 3h 500+파일 소멸이 이 축 의심)
∴ "정식 build 안전"은 축1 한해 참. 축2는 소실 프로브로 확증 후 확정한다.
```

---

## 3. kernel/ untracked 검수 결과 (커밋 판단 근거)

서브에이전트 2개로 23개 전수 파악. 사실:
- **비밀/자격증명 없음.** "token"은 도메인 어휘(OfficialLaunchProof mint 등), 실제 secret 아님.
- **개인 절대경로** `/Users/smith/.brick/...`가 일부 JSON building_ref에 있으나 **이미 tracked인
  형제 파일(g1/g2 forward)의 확립된 관행** — 커밋 차단 사유 아님. (단 헌법 Rule13은 이걸
  지양하라 함 — 미래 정리 후보, 지금은 관행 따름.)
- **손상/빈 파일 없음.** 전부 valid.
- superseded 후보 1: `prevention-l3-3a-observe-0709-forward.json`은 `l3-3a-v3-reroute.json`에 밀림(무해).

---

## 4. C2 이주 = 완료 (경로 혼동 방지)

헌법(`BRICK-CONSTITUTION.md`) §Active Physical Roots (0708 개정) + 디스크 실측:

```text
정본 = brick_protocol/ 패키지 트리 하나:
  brick_protocol/brick/   = Brick 축
  brick_protocol/agent/   = Agent 축 (coo.md 헌장 여기)
  brick_protocol/link/    = Link 축
  brick_protocol/support/ = support 기계 위치 (operator/driver.py, run.py, cli.py 등)
  project/                = project-local 증거/상태 (문서·발주서·보드 여기)
legacy top-level brick/·agent/·link/·support/ = 디스크에 없음 = 이주 완료. active import root 아님.
```

★ Smith가 "3축 서포트를 브릭프로토콜 안으로 옮겼다"고 한 게 이 C2 이주. **정본 경로가 맞으니
   코드 실측은 `brick_protocol/support/...`로.** (스킬 원문의 old hardcoded path 문구는 역사 증거.)

---

## 5. ★다음 세션 최우선 — 소실 프로브 (설계 완료, 발사만 남음)

Smith 지시: **동적 무해 프로브 먼저 → 결과로 정적 인과 빌딩.** 그 다음 기반 3종 페이즈.

### 실행 환경 (실측 확정)
```text
★ pipx `brick` CLI 깨짐: /Users/smith/.local/bin/brick → "No module named brick_protocol".
★ 정본 실행 = repo .venv:  .venv/bin/python -m brick_protocol.support.operator.cli build ...
  (.venv import OK, build --help 정상 확인)
```

### 발사 표면 (cli.py:1875 build 파서 실측)
```text
경로A 프리셋 = build --task "<한줄>" --adapter adapter:local
경로B 발주서 = build --graph-decl <파일> --forward --adapter adapter:local
  (--action 기본 stop=파일만 씀·발사 안 함; --forward로 실발사)
```

### 코드로 확인한 소실 뿌리 (더 파지 말 것 — 프로브가 실행결과로 확정)
```text
driver.py:940 create_worktree_sandbox → 미완이면 finally(@928/1059/1080)가 dispose(@1081).
  = "완료 시에만 커밋" 설계라 미완 처분 = 작업물 소멸. (§0 뿌리·§9.1 코드위치 실측 일치)
run.py:643 _anchor_park_stop_wip / :564 _with_close_wip_anchor = park/stop 경로엔 WIP 앵커 있음.
proposal-approval 경로 = onboard.run_goal_approve_entry (onboard.py:2769, cli.py:598 호출).
  ★남은 정적 질문 = 이 경로가 park/stop 앵커를 안 거치는지 → 이건 code-heavy라 빌딩감.
```

### 프로브 안전 설계 (헌장 §5 준수 — 미실행)
```text
- adapter:local work 노드만(실 LLM 불요, 빠름). verdict 노드 local 금지.
- write_scope = /tmp scratch (project/ 실파일·main 무접촉).
- 미완 유도: 없는 deliverable or QA 반려. 발사 후 worktree 경로 실존 + WIP ref +1 실측.
- 이건 빌딩 발주 아니라 엔진 프로브 = operator maintenance 예외로 손 가능(핸드오프 §5).
  ★단 실발사는 worktree 생성/dispose 부작용 있음 → Smith 확인 후 발사.
- 베이스라인(발사 전 측정): worktree 12개, refs/brick/wip+salvage 378개. 발사 후 이 수 변화로 판정.
- 프로브가 남긴 잔재(새 worktree/ref)는 프로브 후 손으로 정리.
```

### Smith가 붙인 골 = 기반 3종 + 전구간 큐 (프로브 다음)
```text
기반 3종(한 덩어리, 워크트리 유실 뿌리·RV2 봉쇄 원인):
  #2  hold/dispose 보존 정합 (driver.py finally 무조건 폐기 → 보존 정책) · write=True · 상
  #24 L3-3b lethal raise 회귀 수리 (15ccd10ac가 정당 호출자까지 죽임) · RED 프로브+수리 · 중
  #1  complete/write 후 land 강제 (write diff가 main land 없이 complete 종료 금지) · 상
전체 구간 I~X = master-work-queue-necessity-0709.md §1. #9(D3) 3갈래 엉킴 정리 격상 주의.
```

---

## 6. 왜 이 세션이 끝났나 — 툴 버그 재발 (직전 세션과 동일)

```text
증상: tool-call 직렬화 오염. 툴 호출이 실행 안 되고 XML(count/invoke/parameter)이 텍스트로 새어나옴.
      한 번 깨지면 few-shot poisoning으로 연쇄 → 세션 내 복구 불가.
트리거(이 세션): 긴 멀티라인 Bash 연속 투입(파이프·heredoc·다중 echo). 시퀀셜 씽킹 미사용.
근거: GitHub #66400·#63870·#62344·#64235. Smith도 앱 오류로 판단.
완화: ★새 세션(근본) · CLAUDE_CODE_DISABLE_1M_CONTEXT=1 · 툴 호출 작게·Bash 파이프/멀티라인 최소.
```

---

## 7. 다음 세션 체크리스트

```text
1. COO 헌장 먼저 (brick_protocol/agent/prompts/coo.md) + 헌법(BRICK-CONSTITUTION.md).
2. 이 커밋(dce5160d0) 위에서 시작 확인 — charter/queue/발주서 tracked 실측 (git ls-files).
3. ★소실 프로브 발사 (§5) — .venv python -m으로, 무해 2발, Smith 확인 후. worktree/WIP 실측.
4. 그 결과로 축2(§2) 확정 → queue §9.2·보드 "정식 build 안전" 최종 판정/정정.
5. 그 다음 기반 3종(#2/#24/#1) 발주 논의 — 소실 메커니즘 확정이 선행.
6. 버그 재발 방지: thought 짧게, Bash 단순하게, 툴 호출 작게.
```

## 8. 경로

```text
Board:    project/brick-protocol/status/kernel/ACTIVE_COO_GOAL.md
Charter:  project/brick-protocol/status/kernel/GOAL-PROMPT-necessity-master-0709.md (이제 tracked)
Queue:    project/brick-protocol/status/kernel/master-work-queue-necessity-0709.md (§9.2 정정본, tracked)
COO헌장:  brick_protocol/agent/prompts/coo.md
헌법:     BRICK-CONSTITUTION.md (repo 루트, 법 단일출처)
Prev HO:  project/brick-protocol/status/kernel/HANDOFF-session-0710-coo-worktree-probe.md
This:     project/brick-protocol/status/kernel/HANDOFF-session-0710b-tool-bug-restart.md
CLI실행:  .venv/bin/python -m brick_protocol.support.operator.cli  (pipx brick 깨짐)
Skill:    brick-task-author (발사 체크 7·8 = WIP 앵커 비대칭 정본)
```

## 9. 한 줄

```text
이 세션: kernel 27파일 커밋(dce5160d0)으로 보드·발주서 소실위험 제거 + §9.2 축1/축2 정정 +
C2 이주완료 확인. 다음 최우선 = 소실 프로브(.venv python -m, 무해 2발, Smith확인후) → 축2 확정
→ 기반3종. 툴버그 재발로 조기종료 — 새 세션 필수(thought짧게·Bash단순).
```

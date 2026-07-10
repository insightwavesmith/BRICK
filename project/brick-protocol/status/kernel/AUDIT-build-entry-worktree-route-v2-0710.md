# COO 통합 감사 — 빌드 입구·워크트리 수명주기·Reroute/Route V2 (0710)

| 항목 | 값 |
|---|---|
| 작성일 | 2026-07-10 KST |
| 체크아웃 | `/Users/smith/projects/BRICK` |
| 관측 HEAD | `dce5160d0850588742564c0b2c95d43778613c29` |
| `origin/main` | `1367adb5f0f1451f0663e2f4f279e6b9d68f5997` |
| 동기 상태 | local main ahead 8 / behind 0 |
| 보고서 성격 | COO support evidence · source truth/성공/품질/Movement 권위 아님 |
| 변경 범위 | 이 감사의 파일 변경은 이 보고서 1개만. 커밋·push·정리·수리 없음 |

## 0. 최종 판정

Smith가 잡은 두 축은 정확하다. 다만 현재 장애를 더 좁히면 다음과 같다.

1. **입구는 이름만 하나이고 authoring·승인·실행·복구 funnel은 하나가 아니다.**
   `brick build` 아래에 preset-task와 graph-decl 두 파이프가 있고, 그 옆에 preset ranker,
   8답 graph-draft, Building Call authoring/lowering, Python DSL이 겹친다. “업무 과중에 따라
   direct preset 또는 발주서 Building을 고르고 엔진이 계획을 그린다”는 구성요소는 있으나,
   하나의 상시 제품 경로로 닫히지 않았다.

2. **워크트리 사고의 핵심은 단순한 `hold이면 무조건 dispose`가 아니다.**
   최초 고객 sandbox 실행은 미완이면 WIP anchor를 먼저 시도한다. 그러나 anchor 실패에도
   worktree를 폐기하고, 다음 resume은 그 WIP를 복원하지 않고 현재 HEAD에서 새 worktree를
   만든다. 새 resume worktree도 동일한 close bracket으로 닫히지 않으며, 나중에는 24시간
   marker-age reaper가 dirty/hold/WIP/liveness를 보지 않고 지울 수 있다. 즉 **Link evidence
   continuity와 작업 바이트 continuity가 분리**되어 있다.

3. **기존 reroute/resume 엔진은 사라지지 않았다.**
   과거 공식 trace에서 `implementation_gap → work reroute → QA replay → closure`가 실제로
   완주했다. 현재 reroute 정책과 runtime 삽입 본체도 존재한다. 지금 막힌 것은 Route V2를
   새로 설계하지 않아서가 아니라, L3-3b 공식 launch admission 회귀, hold/resume workspace
   lifecycle, SHAPE A/B 상태원장 충돌이다.

4. 따라서 지금의 우선순위는 **Route V2 전면 재설계가 아니다.**
   먼저 살아 있는 작업장을 비파괴 회수하고, lifecycle과 공식 launch admission을 닫고,
   build authoring funnel을 하나로 수렴시킨 뒤, 과거 known-good n2 reroute trace를 현재 CLI에서
   재증명해야 한다. 그 뒤에도 정책 결함이 남을 때만 beyond-A 설계를 연다.

5. **Deku는 Brick Protocol이 아니다.**
   Deku는 Brick으로 개발하는 별도 프로젝트다. `project/deku/**`는 Protocol 제품 결함 집계와
   수리 범위에서 제외한다. 다만 Deku dogfood가 남긴 worktree와 Protocol inbox 투영은
   lifecycle 결함과 control-plane 오염을 보여 주는 운영 증거로만 사용한다.

요약 상태:

```text
BUILD ENTRY       PARTIAL — 명령명 1개, 의미·권위·복구 funnel 다수
WORKTREE SAFETY   FAIL   — evidence resume과 byte resume 불일치
OLD REROUTE       EXISTS — 과거 E2E 및 현재 runtime 본체 확인
ROUTE V2 BEYOND-A FROZEN/NOT_IMPLEMENTED — 지금 재개하지 않음
RELEASE           NOT_PROVEN — current --all RED, dirty main, origin보다 8 ahead
```

---

## 1. 범위와 제외선

### 감사 범위

- public build/resume 입구와 실제 내부 분기
- 업무 과중 → preset/authoring/graph 제안 경로
- worktree create → hold/complete → anchor/commit → dispose → resume → reap
- 기존 reroute의 과거 실행 증거와 현재 runtime 본체
- Route V2 SHAPE A, 최소 SHAPE B helper, beyond-A freeze 경계
- 현재 checkout의 worktree/WIP/salvage/inbox 정리 위험

### 명시적 제외

- `project/deku/**` 제품 구현·완료 판정
- Route V2 beyond-A 신규 설계/구현
- 현재 dirty source 수정, worktree 삭제, ref 삭제, salvage/harvest, commit, push
- 모델 설정 변경의 품질 판정

### 판단 규율

- handoff보다 live checkout과 현재 코드가 우선이다.
- checker green 하나를 E2E green으로 확대하지 않는다.
- `frontier_kind=complete`와 제품 성공/품질, main landing을 같은 뜻으로 쓰지 않는다.
- Deku 제품 상태와 Brick Protocol 제품 상태를 합산하지 않는다.

---

## 2. 라이브 체크아웃 스냅샷

보고서 작성 직전 파일 단위 `git status --porcelain --untracked-files=all`은 98개였다.

| 구분 | 수 | 해석 |
|---|---:|---|
| `brick_protocol/**` modified | 11 | 앞선 model/casting 설정 작업. 이 감사가 수정하지 않음 |
| Protocol status 문서 modified | 2 | `ACTIVE_COO_GOAL`, master queue의 0710d 갱신. 이 감사가 수정하지 않음 |
| `project/deku/**` modified | 5 | 별도 Deku 프로젝트 |
| `project/deku/**` untracked | 15 | 별도 Deku 프로젝트 |
| Protocol inbox의 `deku-*` untracked | 63 | cross-project report projection |
| Protocol kernel handoff untracked | 2 | 0710b/0710c handoff |

현재 worktree는 main 포함 13개다.

| 상태 | 수/대상 |
|---|---|
| main dirty | 98 file-status rows |
| clean disposition/review worktree | 9 |
| dirty disposition worktree | `pure-dev-d3-r7-token-harden-0709` 1건 |
| dirty engine worktree | `deku-d2-real-conduct-0709` 7건 |
| dirty engine worktree | `pure-dev-d3-body-v1-0709` 2건, 대응 WIP ref 미확인 |

현재 ref 실측:

```text
refs/brick/wip/*       357
refs/brick-salvage/*    23
```

Route V2 checker 감사 중 다음 두 WIP ref가 생성되어 현재 존재한다. 추적 파일은 바뀌지 않았고,
이 감사에서는 삭제하지 않았다.

```text
refs/brick/wip/route-v2-walker-advisory-adopt-0530
refs/brick/wip/route-v2-walker-advisory-vg-0530
```

**운영 판정:** 이 상태에서 “청소”를 곧바로 삭제로 해석하면 안 된다. 특히 dirty engine
worktree와 357 WIP/23 salvage ref는 먼저 내용·base·관련 Building·frontier·land 여부를
목록화해야 한다.

---

## 3. 빌드 입구 감사

### 3.1 하나인 것과 하나가 아닌 것

실행 파일 이름은 하나다.

- `pyproject.toml:22-23` — `brick = brick_protocol.support.operator.cli:main`
- `brick_protocol/support/operator/__init__.py:12` — package export는 `build` 하나

그러나 `brick build` 내부는 즉시 두 파이프로 갈린다.

```text
PRESET-TASK
brick build --task ... [--preset ...]
→ cli._run_build
→ run_customer_building_in_sandbox
→ run_building_intake
→ materialize declared plan
→ run_building_plan

GRAPH-DECL
brick build --graph-decl ... [--forward]
→ assemble_graph_declaration
→ persist proposal
→ run_goal_approve_entry
→ launch/resume family
→ runner
```

근거: `cli.py:509-527`, `cli.py:573-627`, public option `cli.py:1915-1937`.

또한 `driver.py:2548-2555`는 `run_building_intake`, preset sandbox, graph sandbox,
portfolio를 함께 export한다. 이는 `AGENTS.md:56-57,282`의 “run.py는 single Building,
driver.py는 portfolio” 설명과 실제 public seam이 어긋나는 지점이다.

**판정:** `brick build`라는 이름은 하나지만 authoring/approval/lifecycle 의미는 하나가 아니다.

### 3.2 현재 자동 preset 선택은 업무 과중 선택이 아니다

`--preset`을 생략하면 현재 CLI는 다음처럼 고른다.

```text
task가 있고 adapter가 write-capable → DEFAULT_REAL_TASK_PRESET_REF (fast-fix)
그 외                              → DEFAULT_LOCAL_PRESET_REF
```

근거: `cli.py:319-325`, help `cli.py:1887-1893`.

이는 업무 크기·모호성·실패비용·fan-out·human gate를 본 선택이 아니다. 동시에
`AGENTS.md:69-73`의 “support authors nothing” 및 preset catalog의
`caller_or_coo_declared_only`와 긴장한다.

반대로 preset ranker는 30개 preset을 token overlap으로 정렬하지만, 스스로 다음을 금지한다.

- auto-select 안 함
- chosen/recommended/best field 안 만듦
- materializer의 명시적 `chain_preset_ref` 요구를 우회하지 않음

근거: `support/connection/building_design_toolkit.py:334-358`.

즉 “실제 적용되는 단순 default”와 “업무에 맞추려는 advisory ranker”가 서로 다른 표면에 있다.

### 3.3 자동으로 그리는 체계도 둘이며, 둘 다 수직 제품 경로가 아니다

#### A. Graph Draft

`graph_draft.py:1-16`은 task와 8개 sizing answer로 launch-ready candidate를 만든다. 실제로
size, partitionability, conflict, failure cost, approval, done shape, difficulty 등을 이용해
fan 구조, design/work/QA/closure, casting tier/lens, timeout, gate를 제안한다.

그러나 이것은 `brick draft`라는 별도 제품 입구다. 자동 launch하지 않고 operator가 파일을
검토한 뒤 다시 `brick build --graph-decl ... --forward`를 실행해야 한다
(`cli.py:1948-1964`).

#### B. Building Call Authoring

Building Call은 발주를 다음 5단계로 나눈다.

```text
scope
→ Building 전체 과중
→ structure
→ Brick별 과중
→ Agent 후보
```

confirmed request를 `building_case → chain_preset_ref`로 lowering하는 코드는 존재한다
(`building_call.py:24-35,126-175`). quick_check/quick_fix만 `fast_confirm`과 red-flag 부재 시
direct preset이 되고, 나머지는 order_authoring으로 보낸다
(`building_call.py:203-274`). 이 정책 방향은 Smith의 의도와 가장 가깝다.

하지만 저장소 내 정적 production callsite에서는 authoring validator/lowerer가 CLI/운영 경로에
연결된 것이 확인되지 않았다. 현재 master queue도 다음을 OPEN으로 둔다.

- #20 발주서 Building → COO 검토 → build 제품 경로 재증명
- #22 어려운 발주 = authoring preset chain 상시화

**판정:** 구성요소는 구현돼 있으나
`발주서 Building → COO confirm → canonical lower → 동일 build dispatch` 수직 경로는
**NOT_PROVEN**이다.

### 3.4 공식 경로의 권위도 충돌한다

- README/launch guide는 `assemble/build/fan` Python DSL을 공식 그래프 경로로 설명한다.
- 실제 walker의 L3-3b gate는 CLI main에서 mint한 official launch token을 요구한다.
- sandbox-safe Python wrapper인 `fire()`는 존재하지만 운영 skill은 internal/debug로 가르친다.
- `build`라는 이름도 assembly의 graph compile, onboard의 proposal/approval launch,
  package export에서 서로 다른 의미로 쓰인다.

근거:

- `assembly.py:576`, `assembly.py:1374-1444`
- `onboard.py:2703`, `onboard.py:2986-2989`
- `walker_kernel.py:1372-1379`
- `import_identity.py:291-294`
- `cli.py:2141-2157`

따라서 green인 `driver_public_intake_seal`은 특정 driver export seal만 증명할 뿐,
전체 authoring/launch 권위가 하나라는 증거가 아니다.

### 3.5 복잡성이 커진 객관적 이유

주요 이력은 “한 번의 거대한 설계 실패”보다 다음 누적이다.

```text
disposable customer worktree 도입
→ goal/AI compose 경로 추가
→ auto-compose 제거
→ graph CLI 추가 후 raw graph 퇴역
→ graph-decl + graph-draft + --forward 추가
→ Building Call authoring + validator + lowerer + direct escape 추가
→ CLI-only lethal launch token 추가
→ land-force/WIP/park anchor를 사후 보강
```

대표 커밋: `9ea374ca7`, `cfffc07c3`, `f2ccd1622`, `7dbea6104`, `aaf29754f`,
`121b1d6f2`, `843e60d45`, `25d0162ad`, `07e1bb899`, `298b28a86`,
`201e502d3`, `569458a0d`, `ed092ae63`, `15ccd10ac`, `da14f95f8`.

각 안전장치의 의도는 이해되지만 이전 경로를 완전히 흡수하지 않은 채 새 authoring/policy/
checker/문서 계층을 더했다. 그 결과 visible command 수보다 semantic seam 수가 늘었다.

---

## 4. Worktree·hold·resume 감사

### 4.1 최초 고객 sandbox 실행의 실제 동작

`driver._run_in_worktree_sandbox()`의 정상 git 경로는 다음과 같다.

```text
create detached worktree at pinned HEAD
→ run dispatch
→ observe Link frontier
→ complete이면 scoped diff 검증 후 commit
→ non-complete이면 WIP anchor 시도
→ finally에서 worktree force-dispose
```

근거: `driver.py:803-834,938-1081`.

따라서 과거 문구인 “미완이면 아무 보존 없이 무조건 dispose”는 너무 넓다. 정상적인
non-complete는 `anchor_wip_snapshot()`을 먼저 시도한다 (`driver.py:1059-1079`).

그러나 핵심 결함은 남는다.

#### P0-A. anchor 성공 확인 없이 dispose

`anchor_wip_snapshot()`은 git status/add/write-tree/commit-tree/update-ref 실패 또는 sensitive
path 발견 시 raise할 수 있다 (`worktree_sandbox.py:226-278`). 바깥 `finally` 안의 다시 중첩된
`finally`가 그 성공 여부와 무관하게 `dispose_worktree_sandbox()`를 호출한다
(`driver.py:1059-1081`).

즉 현재 불변식은:

```text
anchor를 시도한다 → 반드시 dispose한다
```

이어야 할 불변식은:

```text
landed commit 또는 검증된 WIP commit/ref 또는 명시 discard가 증명됨
→ 그때만 dispose
```

이다.

#### P0-B. WIP anchor는 resume 재료로 연결되지 않음

`onboard._prepare_resume_adapter_cwd()`는 caller cwd가 없으면 현재 repo의 현재 HEAD를 probe하고
새 worktree를 만든 뒤 `sandbox.path`만 반환한다 (`onboard.py:286-335`). 이전
`refs/brick/wip/<building-id>`를 찾거나 checkout/apply하지 않는다.

그러므로 현재 흐름은:

```text
hold evidence = 이전 실행의 graph/history를 이어감
resume cwd    = 현재 HEAD에서 새로 만든 깨끗한 worktree
```

이다. **evidence resume은 있으나 workspace resume은 없다.**

#### P0-C. resume-created worktree 소유권이 닫히지 않음

`run_approve_entry()`는 disposition을 쓰고 `resume_building_plan()`을 호출한다
(`onboard.py:3979-3988`). `_prepare_resume_adapter_cwd()`가 `WorktreeSandbox` 객체를 버리고 path만
넘기므로, 최초 실행의 commit/anchor/dispose bracket을 재사용하지 못한다.

`resume_building_plan()`은 정상 반환과 adapter-error에 `_with_close_wip_anchor()`를 쓰지만,
main `_resume_dynamic_graph_walker()`의 `ChatSessionParkFrontierEvidenceWritten`을 잡지 않는다
(`run.py:773-862`). `run_approve_entry()`는 이 예외를 friendly error로 바꾸고 반환한다
(`onboard.py:4061-4071`). 이때 auto-created worktree는 dirty 상태로 남을 수 있다.

#### P1-A. 24시간 reaper가 held workspace의 생존을 판정

모든 `create_worktree_sandbox()`는 먼저 `reap_stale_worktrees()`를 호출한다
(`worktree_sandbox.py:129-160`). reaper는 engine marker의 `created_at`이 기본 24시간보다 오래됐는지만
보고 force-remove한다 (`worktree_sandbox.py:430-461,568-576,643-671`).

현재 확인되지 않는 것:

- hold/frontier 상태
- dirty 여부
- WIP anchor 존재 및 일치
- PID/lease/liveness
- marker `repo_root`와 현재 호출 repo의 소유권 일치

특히 현재 repo에서 `git worktree remove`가 실패하면 디렉터리를 직접 지우므로, 동일한
`~/.brick/worktrees`를 공유하는 다른 repo의 engine worktree까지 건드릴 cross-repo 위험이 있다.

#### P1-B. temp-dir fallback은 write 결과를 보존하지 않음

git probe/create가 실패하면 adapter는 temp dir에서 실행되고, commit/WIP anchor 없이
`finally`에서 temp dir가 삭제된다 (`driver.py:836-929`). write-capable provider가 hold/park 또는
commit 불가 상태에 도달하면 evidence만 남고 바이트가 사라질 수 있다.

#### P2. WIP ref 수명주기가 완결되지 않음

direct `adapter_cwd` close/park anchor는 best-effort이며 오류를 삼킨다
(`run.py:564-672`). production에서 stale WIP reaper를 호출하는 곳은 확인되지 않았고 checker만
호출한다. 반대로 complete/land 뒤 자동 WIP release도 full lifecycle로 고정되지 않았다.

현재 357개라는 수치는 단순 “보존을 잘했다”가 아니라, 보존·복원·해제 상태 머신이 없다는
운영 신호다.

### 4.2 “공식 루트가 성공판정한다”는 감각의 정확한 뜻

semantic sufficiency와 Movement는 Link가 소유한다. support가 품질을 판단하는 것은 아니다.
그러나 support는 Link frontier를 다음 물리 정책으로 번역한다.

```text
frontier complete → commit 시도, ok/ready 표기
그 외            → WIP 취급, anchor 시도
모든 정상 close  → worktree dispose
```

CLI도 `customer_visible_not_ready = frontier_kind != complete`를 만든다 (`cli.py:547-550`).

따라서 Smith의 감각은 운영상 맞다. support는 의미/품질 success가 아니라 **workspace를
commit·보존·폐기할 lifecycle success 판정**을 수행한다. 문제는 그 판정에 workspace identity와
복구 가능성 증명이 포함되지 않았다는 것이다.

### 4.3 경로별 판정

| 경로 | 현재 동작 | 판정 |
|---|---|---|
| preset/graph customer sandbox 최초 실행 | incomplete WIP anchor 시도 후 dispose | `SAFE_IF_ANCHOR_SUCCEEDS`, fail-closed 아님 |
| graph-decl proposal/review-only | 관측 probe에서는 worktree 미생성, proposal/human wait | `NOT_A_WORKTREE_PATH` |
| direct `run_building_plan` caller cwd | close/park best-effort WIP anchor, caller가 cwd 소유 | `PARTIAL` |
| onboard approve → resume auto cwd | 현재 HEAD 새 worktree, WIP 미복원, 동일 close bracket 없음 | `LOSS_RISK` |
| stale engine worktree | marker age만으로 강제삭제 가능 | `LOSS_RISK` |
| temp-dir fallback | commit/anchor 없이 cleanup | `LOSS_RISK_FOR_WRITES` |

이 표가 0710c handoff의 미회수 축2를 현재 코드 기준으로 좁힌 최종 판정이다.

---

## 5. 기존 reroute와 Route V2 감사

### 5.1 “원래 됐다”는 기억은 맞다

다음 과거 증거에서 실제 reroute/resume가 관측됐다.

- 0630 `live_qa_reroute_to_work_n2`:
  `implementation_gap → Link reroute → work attempt 2 → closure`
- 0701 route proof:
  closure-origin concern이 work로 reroute되고 QA/closure attempt 2 후 complete
- 0701 P2:
  closure→work repair, QA/closure 2회차, full profile PASS, main land
- 0709 G0/G1 dogfood:
  graph-decl → COO hold → resume → fake-landing hold → resume → complete

증거 문서:

- `status/kernel/archive/0702-doc-archive/customer-ready-closeout-requirements-audit-0630.md:23-24`
- `status/kernel/archive/0702-doc-archive/customer-ready-closeout-g1g2g3-status-0630.md:39`
- `status/kernel/archive/0702-doc-archive/brick-6-route-proof-findings-0701.md:13`
- `status/kernel/archive/0702-doc-archive/brick-6-p2-resume-isolation-disposition-closure-0701.md:9`
- `status/kernel/g0-g1-exit-evidence-0709.md:38`

대표 복구 계보도 남아 있다.

- `ac84af40d` — concern-hold reroute disposition mirror/replay
- `d2758433c` — `brick resume --decl`, multi-hold chain
- `d30517894` — resume fuel honesty와 G0/G1 continuity

따라서 현재 문제를 “reroute 기능이 원래 없었다”로 정의하면 틀린다.

### 5.2 현재도 살아 있는 범위

`brick_protocol/link/route_policies/basic_qa_repair.yaml`은 현재도 concern별 정책을 선언한다.

- `implementation_gap` → dev target + QA replay
- `design_gap`, `upstream_gap`, `boundary_mismatch`, `insufficient_input` → design/work/QA replay + human gate
- `verification_gap` → non-reroute

`agent/return_fact.py:22-24`도 `verification_gap`을 명시적 non-reroute concern으로 둔다.
`walker_transition_concern.py`의 runtime classifier와 `walker_kernel.py`의 budget/HOLD/runtime mail/
target landing/replay/fan-in sibling 재검증/adoption 삽입도 존재한다.

즉 정책 선언과 실행 본체는 살아 있다.

### 5.3 Route V2의 정확한 경계

0709 freeze의 승인 범위는 SHAPE A다.

```text
walker가 기존 정책으로 결정
→ Route V2는 sealed observation/view만 기록
→ Movement, route_target, concern_kind, Link/AgentFact 권위는 확장하지 않음
```

`route-v2-beyond-a-smith-close-0709.md:14-21`은 beyond-A full engine expansion이 구현되지 않았고,
재개하려면 새 design Building과 별도 Smith 승인이 필요하다고 고정한다.

그런데 이후 main의 `route_v2_views.py:79-98,150`에는 `shape_b_shared_helper`가 들어왔다. 이 helper는
concern eligibility 관측을 공유하지만 target 선택이나 walker control-flow를 구동하지 않는다.
실제 target classifier는 여전히 별도다.

따라서 현재 상태는:

```text
SHAPE A observation                 IMPLEMENTED
SHAPE B eligibility helper min-slice PRESENT
SHAPE B target/control integration  NOT_IMPLEMENTED
beyond-A full engine                NOT_IMPLEMENTED / FROZEN
```

이다. 엔진 완성 과장은 금지해야 하지만, “SHAPE A 동결” 문서와 `shape_b_shared_helper` 표기의
상태원장도 맞춰야 한다.

### 5.4 현재의 실제 blocker

#### L3-3b launch admission 회귀

`15ccd10ac` 이후 walker entry는 official launch token이 없으면 lethal raise한다. 현재 checkout에서
다음 profile/check가 공식/정당 caller임에도 token admission에 막혔다.

- `building_operator_driver0`
- `graphdecl_fix`
- `link_routing_behavioral`
- `route_v2_sealed_materialization`
- `route_v2_walker_advisory`

따라서 현재 n2/reroute 회귀를 green으로 재증명할 수 없다. 이는 route policy 자체의 RED가 아니라
공식 실행·검증 입구의 admission RED다.

#### hold/resume byte continuity

과거 G1 dogfood는 evidence root로 resume한 것을 증명했지만, 최초 write bytes가 같은 workspace
identity로 resume되어 land했다는 증명은 아니다. 이 결함은 Route V2와 독립적이며 Route V2보다
먼저 닫아야 한다.

**판정:** 옛 reroute를 현재 공식 CLI와 수정된 workspace lifecycle 위에서 다시 통과시키는 것이
먼저다. 그 결과가 정책 자체의 부족을 보여 줄 때만 beyond-A를 연다.

---

## 6. Brick / Agent / Link / Support 귀속

| 축 | 관측 | 귀속 |
|---|---|---|
| Brick | preset, task, structure, Building Plan 선언 권위가 ranker/graph-draft/Building Call/CLI default에 분산 | authoring contract 수렴 필요 |
| Agent | casting tier/lens 선택 시점이 여러 표면에 있으나, provider가 쓴 바이트의 손실 원인은 아님 | 복잡성 기여, 손실 root 아님 |
| Link | reroute/hold/frontier evidence는 존재하지만 workspace identity/WIP recovery handle과 결합되지 않음 | lifecycle contract gap |
| Support | CLI/onboard/assembly/driver/run/reaper가 분산된 결정을 실제 호출·폐기·복구 구조로 고정 | 직접 수리 표면 |

핵심 수리 표면은 `brick_protocol/support/operator/**`의 lifecycle/launch funnel이다. 다만 장기 수렴은
Brick의 authoring 계약을 하나로 정리해야 끝난다. Agent 모델을 바꾸거나 Route V2 정책만 확장해서
해결할 문제는 아니다.

---

## 7. 권고 복구 순서

### P0. 새 삭제·대량 발사를 잠깐 멈추고 자산부터 고정

1. `pure-dev-d3-body-v1-0709` dirty 2건을 최우선으로 diff/파일/base SHA/관련 evidence와 묶어
   salvage한다. 대응 WIP ref가 없어 가장 취약하다.
2. `deku-d2-real-conduct-0709`는 Deku 자산으로 별도 인벤토리·salvage한다. Protocol 완료나 결함
   수에 합치지 않는다.
3. 9개 clean disposition/review worktree도 관련 Building/ref/land를 확인한 뒤 제거한다.
4. 357 WIP와 23 salvage ref를 `ref → commit → parent/base → changed paths → Building/frontier → main 포함 여부`
   표로 만든다. blind delete 금지.
5. 63 Deku inbox packet은 Protocol source 결함이 아니라 cross-project projection으로 분리 보관한다.
6. 이 salvage 전에는 `create_worktree_sandbox()`를 부르는 신규 대량 Building 발사를 피한다.
   새 create가 stale reaper를 먼저 실행하기 때문이다.

### P1. lifecycle을 하나의 fail-closed state machine으로 수리

필수 close invariant:

```text
DISPOSE 허용 =
  landed commit + verified SHA
  OR verified WIP ref + WIP commit SHA + durable recovery handle
  OR human/COO explicit discard record
```

구현 요구:

1. anchor 실패 시 worktree를 남기고 recovery handle/path를 반환한다.
2. evidence에 `base_sha`, `wip_ref`, `wip_sha`, workspace owner/lease를 고정한다.
3. resume은 현재 HEAD에서 새로 시작하지 말고 원 WIP commit에서 worktree를 만들거나 검증된 방식으로
   복원한다. HEAD drift는 명시적 rebase/adoption 없이는 섞지 않는다.
4. resume도 최초 실행과 동일한 commit/anchor/dispose bracket을 사용한다.
5. complete/land 뒤 WIP ref를 release하고, hold 중에는 유지하며, discard 뒤에만 해제한다.
6. reaper는 `repo_root`, building id, base, lease/PID, dirty, hold, WIP 일치를 확인한다.
   cross-repo fallback `rmtree`는 금지한다.
7. write-capable temp fallback은 금지하거나, temp bytes를 durable WIP bundle로 보존한 뒤에만 cleanup한다.
8. preset/graph/resume CLI packet 모두 같은 `recovery_handle {ref, sha, base, resume_command}`를 반환한다.

필수 RED→GREEN probe:

- anchor의 status/add/write-tree/commit-tree/update-ref 각 실패에서 worktree 생존
- hold가 쓴 바이트가 resume cwd에 byte-identical하게 존재
- main HEAD가 움직여도 원 base/WIP에서 resume
- resume park/예외 뒤 WIP/worktree 생존
- stale reaper cross-repo 격리
- temp fallback write 보존 또는 fail-closed refusal
- land 뒤 WIP ref release
- preset과 graph 경로의 recovery handle 동등성

### P1 병행. L3-3b 공식 launch admission 수리

- lethal deny는 유지한다.
- 정식 CLI와 정당한 internal/checker caller만 정확한 checkout identity로 허용한다.
- suffix 기반 caller 인정, 잔존 nonce, hardcoded provenance 우회는 금지한다.
- 수리 후 현재 RED인 route/driver/graph profiles를 재실행한다.

### P2. public authoring funnel을 실제로 하나로 수렴

최종 제품 계약을 다음으로 고정한다.

```text
brick build <task>
→ intake/triage
→ 정확히 둘 중 하나
   A. direct_preset
      - quick_check / quick_fix만
      - fast_confirm + 명시 preset 확정
   B. authoring_building
      - normal / complex / critical
      - Building Call authoring 실행
      - COO confirm
      - canonical lowering
→ 하나의 declared-plan dispatch
→ 하나의 sandbox lifecycle
→ runner

continuation = brick resume
```

수렴 규칙:

- write-capable 여부만으로 fast-fix를 고르는 CLI hidden default를 제거한다.
- preset ranker는 direct 후보를 보여 주는 advisory 재료로만 둔다.
- graph-draft의 sizing/shape/casting 로직은 독립 public entrance가 아니라 authoring Building 내부
  도구로 내린다.
- `--graph-decl`은 canonical authoring 결과의 호환 transport로 내리고 신규 사용자 입구로
  가르치지 않는다. 수직 경로가 green이 되기 전 급하게 삭제하지는 않는다.
- `assemble/build/fan/compose/fire`는 Builder 내부 재료로 통일한다.
- portfolio와 repair/replay는 별도 entrance가 아니라 declared plan kind로 취급한다.
- public launch는 `brick build`, continuation은 `brick resume`만 남긴다.

### P3. 기존 reroute를 복구 증명

1. Movement `forward|reroute`, 기존 concern kind, `basic_qa_repair` 정책을 먼저 동결한다.
2. 과거 known-good n2 trace를 현재 공식 CLI로 재실행한다.

```text
implementation_gap
→ reroute work
→ work attempt 2
→ QA sibling replay/fan-in
→ closure complete
```

3. 별도 write fixture로 다음을 증명한다.

```text
write bytes
→ hold
→ process 종료
→ resume
→ 원 WIP bytes 유지
→ complete + main-adoptable commit
→ dispose + WIP release
```

4. SHAPE B helper를 observation-only 승인 슬라이스로 상태원장에 명시하거나 SHAPE A 표기로 되돌린다.
5. 위 복구 뒤 정책 행동이 부족하다는 RED가 나올 때만 새 design Building + Smith 승인으로
   beyond-A를 연다.

---

## 8. 현재 검증 결과

이 감사에서 관측한 focused 결과:

| 검사 | 결과 | 의미 |
|---|---|---|
| `driver_public_intake_seal` | GREEN | 좁은 driver export seal |
| `graph_draft` | GREEN | draft 규칙/shape checker |
| `brick verify --self-test` | GREEN | self-test 범위만 |
| `model-lane-matching-discipline` | GREEN | 앞선 model lane 변경의 focused 범위 |
| `building_operator_driver0` | RED | onboard example `ran != True` |
| `graphdecl_fix` | RED | official token + lifecycle path pollution/manifest drift |
| `resume_declaration` | RED | orphan-harvest guidance pin drift |
| `link_routing_behavioral` | RED | official launch token absent |
| `route_v2_sealed_materialization` | RED | checker caller token admission 실패 |
| `route_v2_walker_advisory` | RED | checker caller token admission 실패 |
| full `check_profile.py --all` | RED | current checkout release/closure 불가 |

따라서 현재 HEAD는 “수정 중인 개발 checkout”이지 customer-ready/Route V2 complete가 아니다.

---

## 9. 즉시 의사결정

### 진행

1. dirty engine worktree와 refs 비파괴 inventory/salvage
2. #2 lifecycle repair와 #24 launch admission repair를 같은 기반 구간으로 발주
3. lifecycle GREEN 뒤 build funnel 수렴
4. old n2 reroute + write-byte continuity E2E
5. 그 결과로 Route V2 beyond-A 재개 여부 판단

### 지금 하지 않음

- dirty worktree, WIP, salvage ref 일괄 삭제
- Deku를 Brick Protocol 수리 범위에 포함
- Route V2 beyond-A 전면 구현
- graph-draft/graph-decl/DSL 급퇴역
- checker 일부 green만으로 DONE/EXIT/customer-ready 선언
- 현재 dirty main에서 release 판정

### COO 최종 의견

브릭은 “망가져서 처음부터 다시 만들어야 하는 엔진”은 아니다. 기존 reroute, hold evidence,
materialization, sandbox, authoring 부품은 상당 부분 실제로 존재한다. 문제는 부품이 늘어난 동안
**누가 한 작업장의 생애를 끝까지 소유하는지**가 사라졌고, 입구 통합이 command 이름 통합에서
멈췄다는 것이다.

그러므로 복구의 중심 문장은 하나다.

> 한 task는 하나의 authoring 결정과 하나의 declared plan을 만들고, 하나의 workspace identity가
> hold부터 resume·land·dispose까지 이어져야 한다.

이 불변식을 먼저 되찾으면, 원래 되던 “CLI에서 reroute하고 수정해서 다시 완주하는 작업 시스템”을
큰 재설계 없이 복구할 수 있다.

---

## 10. 남은 NOT_PROVEN

- Building Call authoring → confirm → lower → official build의 상시 수직 E2E
- hold WIP bytes의 자동 rehydrate와 main-adoptable landing
- anchor 실패/park/예외/temp fallback에서 byte loss 0
- stale reaper의 repo/lease/frontier 안전성
- 현재 HEAD의 known-good n2 reroute 재현
- SHAPE B helper의 Smith 승인/원장 정합
- Route V2 beyond-A full engine
- fresh clone + brand-new human auth
- commercial release/customer-ready forever
- Deku 제품 완료 상태

## 11. 핵심 근거 위치

```text
입구/CLI
  pyproject.toml:22-23
  brick_protocol/support/operator/cli.py:319-325,509-627,1875-1964,2141-2157
  brick_protocol/support/operator/__init__.py:6-12

authoring
  brick_protocol/support/connection/building_design_toolkit.py:334-468
  brick_protocol/support/operator/graph_draft.py:1-16
  brick_protocol/support/operator/building_call.py:24-35,126-175,203-274
  brick_protocol/brick/templates/presets/building-call-authoring.md
  brick_protocol/brick/templates/bricks/building-call-authoring/brick.md

lifecycle
  brick_protocol/support/operator/driver.py:667-800,803-1081
  brick_protocol/support/operator/worktree_sandbox.py:129-173,226-278,281-341,430-461,568-680
  brick_protocol/support/operator/onboard.py:286-335,3979-4077
  brick_protocol/support/operator/run.py:564-672,730-862

reroute/Route V2
  brick_protocol/agent/return_fact.py:22-24
  brick_protocol/link/route_policies/basic_qa_repair.yaml
  brick_protocol/support/operator/walker_transition_concern.py
  brick_protocol/support/operator/walker_kernel.py
  brick_protocol/support/operator/route_v2_views.py:79-98,150-165
  project/brick-protocol/status/kernel/route-v2-beyond-a-smith-close-0709.md:14-40

operations
  brick_protocol/support/operator/report_sinks.py:1051-1117
  project/brick-protocol/status/kernel/HANDOFF-session-0710c-loss-probe.md
  project/brick-protocol/status/kernel/ACTIVE_COO_GOAL.md
  project/brick-protocol/status/kernel/master-work-queue-necessity-0709.md
```

---

## 12. COO 교차검증 부록 (0710d · Claude COO — 워크플로우 실측 15에이전트, read-only)

이 부록은 위 Codex 감사(§0–§11)를 독립 워크플로우 실측(입구/어휘/리라우트 설문 4 +
전면 감사 4 + 축2 검증 7)과 대조한 결과다. 실행·변경 없음(보호앵커 2건은 Smith GO로 별도 실행).

### 12.1 확인 — Codex 신규 주장 3건 전부 실측 지지

```text
P0-B resume WIP 미복원  ✅ _prepare_resume_adapter_cwd(onboard.py:286-335)에 wip ref 조회 0줄,
                          현재 HEAD probe로 새 worktree 생성. evidence resume ≠ workspace resume 확정.
n2 known-good           ✅ 0630 아카이브 G1.2 "live_qa_reroute_to_work_n2 measured ... narrowly_proven"
                          실존 + 계보커밋 ac84af40d/d2758433c 실존. ac84af40d 메시지 자체가
                          "worktree reaped ... work preserved and landed from WIP anchor 6a4191e2" 기록.
reaper cross-repo       ✅ 정밀화: rmtree 폴백은 engine-marker 게이트는 있으나 marker.repo_root와
                          호출 repo 대조 없음 — 같은 HOME 공유 시 타 repo 엔진 worktree reap 가능.
                          (critic 확정: deku 발사가 brick 잔재를 지울 수 있고 역도 성립)
```

### 12.2 정정 — Codex 감사의 오류/부정확 3곳

```text
① §4.3 "graph-decl proposal/review-only = worktree 미생성 = NOT_A_WORKTREE_PATH" 행:
   0710c 관찰 착시의 승계. 실행증거(프로브A agent-return worktree_observation: detached HEAD·
   dce5160d0·clean) + 코드(onboard.py:2894 forward 무조건 bracket 진입)로 정정 —
   --forward 첫발사는 worktree 생성→(클린이면 무앵커)→dispose. action=stop만 진짜 무-worktree.
② "정책 권위 어긋남" 강도: 실측상 gate-policy(기계 라우트표)→disposition(멈춤의 인간결정)→
   Movement(기록 사실)는 서로 다른 질문에 순차 작동하는 설계된 계층이고 기계적으로 강제됨.
   disposition reroute는 gate 어휘로 번역돼 단일 reroute 엔진 재사용(walker_kernel.py:2133-2137
   주석 명시). 남는 실결함 = README:28 오해 문구 + resume --decl의 reroute 미허용
   (RESUME_DECL_ACTIONS=raise/forward/stop, resume_declaration.py:27 — 거부 fixture 실존).
③ §2 ref 센서스 "salvage 미분리": refs/brick-salvage/ 최상위 네임스페이스 23 refs 실존
   (전부 main 미도달 = 순수 미착지 salvage, w1a 94e4bbbf4 포함). 분리는 이미 존재·사용 중.
```

### 12.3 Codex 감사에 없는 신규 발견 (COO 워크플로우 실측)

```text
★두 번째 CLI: python -m brick_protocol.support.operator.onboard (main :4333) —
  goal-approve/approve 서브커맨드, approve는 --reroute-target/--re-instruction로 reroute
  disposition 전체 수용. install.sh:62가 실사용. off-route 훅 분류기 실행 결과 deny=False =
  차단 밖. → P2 입구 수렴 범위에 onboard 모듈 CLI 봉인 필수. 역으로 "명령줄 reroute 입구"는
  이미 존재 — brick 콘솔 아래로 이설이 과제.
★declared-plan 리비전/확장 체인 live: write_declared_plan_revision(declaration_packets.py:287)로
  홀드된 빌딩에 repair 노드+budget add-only 추가(승인증거+확장예산 검증), resume은 최신 승인
  리비전으로 재수화(walker_resume.py:1223)해 같은 frontier/원장에서 계속. 쓰기=checker-only,
  읽기=모든 graph resume에서 live. → "제자리 확장-수리" 경로 실존 = 최소 리라우트 폐쇄 갭 축소.
★stash@{0} 단일본: "pre-c2-landing-main-dirty-20260708" — 커널문서 4개 204줄, 고유줄 137/146이
  main 전체에 부재, 아카이브 태그 없음(stash@{1}–@{4}만 태그됨). 가장 취약한 ref에 단일본.
★gitignored 맹점의 라이브 실증: deku-d2 미보전 4파일 전부 deku-home-real/sessions/ =
  .gitignore "sessions/" 매치 → add 기반 앵커가 영원히 못 담음. 축2 §9.6 맹점①의 실물.
  reap eligible 2026-07-10T14:27Z(23:27 KST)부터.
★refs/brick/wip 356 중 80(22%)는 main 기도달(이미 착지) = 정리 후보 목록 확보. 276 = 순수 앵커.
★main 로컬이 origin보다 8커밋 ahead — 0708–0710 커널 handoff 전부 로컬 단일본(push 미실행).
★model-lane 0710 recast(11파일: fable-5 기획 복귀·dev=gpt-5.6-sol xhigh, 일관된 1유닛)가
  무앵커 dirty로 main 체크아웃에만 존재 — 트리 내 최고 소실위험 항목(단 reaper 사정권 밖).
★brick init = 4번째 build형 공개 입구(예제 빌딩 실행 + 자체 adapter 자동선택 onboard.py:617).
★스케줄/데몬 무인 reap 트리거는 repo 내 부재 확인(트리거 = build + approve/resume 인간 개시뿐).
```

### 12.4 순서 판정 (Codex §7·§9와 COO 실측의 종합)

```text
Codex 권고 순서 유지 + 실측 반영 수정:
P0 회수: pure-dev-d3-body-v1 앵커 ✅완료(de524962b, byte-identical 확인) ·
        deku-d2 앵커 ✅완료(81068c09f, 단 sessions/ 4파일은 gitignore로 앵커 불가 — 별도 처분 필요) ·
        추가 긴급 3건 = model-lane recast 무앵커 유닛 · stash@{0} 태그 보존 · push 8커밋(Smith 결정)
P1 수리(#2+#24 병행): 축2 §9.6 수리표면 + P0-A(anchor 실패 fail-closed) + P0-B(WIP 재수화) +
        reaper(앵커+liveness+repo_root 대조) + gitignored/서브모듈 맹점 처리
P2 입구 수렴: brick 콘솔(실행동사 build/resume 2개뿐임은 실측 확인) + onboard 모듈 CLI 봉인 +
        Python-import 표면(driver 4러너·fire·launch_assembled_building·orchestration_packet) 정리 +
        무호출 광고표면 2건(run_declared_portfolio·auto_repair_replay ← mcp_projection이 COO에 광고) 정돈
P3 n2 재증명: run_approve_entry는 오늘도 reroute+target+re_instruction 수용, resume이 reroute 지점부터
        하류 라이브 재주행 — "복원" 성격 재확인. resume --decl에 reroute 어휘 추가가 CLI측 최소 갭.
        route_replay_plan의 disposition seam 부재는 리비전/확장 체인이 대안 경로일 수 있음(설계 판단).
beyond-A: 동결 유지 (Codex §5.3 상태원장 정합 필요성에 동의).
```

### 12.5 남은 not_proven (COO 측 추가)

```text
- 전 판정이 정적 판독+과거 증거 기반 — 현 HEAD 라이브 파이어 재현 없음 (L3-3b RED가 선결).
- stash@{0} 내용의 의미적 대체 여부(문자 부재만 실측).
- deku-d2 sessions/ 4파일의 보존 가치(소유자 판단).
- 리비전/확장 체인의 쓰기측 공식 경로 승격 가능성(현재 checker-only).
- 사용자 crontab/launchd/스케줄러의 무인 brick build 존재 여부(repo 밖 미검사).
```

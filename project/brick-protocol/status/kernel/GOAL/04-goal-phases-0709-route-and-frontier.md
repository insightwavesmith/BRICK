# BRICK Goal Phases — 0709 Route Repair + Remaining Frontier

| | |
|---|---|
| **Status** | support evidence only · COO operating map · **ACTIVE ladder** |
| **Date** | 2026-07-09 |
| **Live repo** | `/Users/smith/projects/BRICK` |
| **Parents** | `03-remaining-frontier-goal-0709.md` · `02-unified-continuous-build-goal-0708.md` · `parent-goal-closure-0709.md` · route resume brief (COO 0709) |
| **Active COO goal** | `status/kernel/ACTIVE_COO_GOAL.md` — **이 문서(G0–G6) 완벽 완료** |
| **Official route memo** | `status/kernel/OFFICIAL_ROUTE_MEMO.md` (update every Goal Exit) |
| **Impl split** | G0–G1: Grok subagents OK · **after G1 Exit: BRICK buildings only** |
| **Deku** | design frozen (`deku/docs/DEKU_STATUS.md`); reopen after BRICK G0–G1 |
| **Proof limit** | not source truth · not success/quality · not Movement authority |

---

## 0. 한 줄 골

```text
공식 앞문(brick build --graph-decl)이 “한 길”로 좁혀진 뒤에도
  (1) pause → resume(route) 가 다시 살아 있고
  (2) 0709 remaining frontier(발주·방지·UX·구조)가 그 길 위에서만 전진하며
  (3) salvage/WIP 가 route 를 대체하는 상시 운영이 아니게 한다.
```

**Customer-ready 상위 북극(유지):**  
고객이 LLM 연결 후 공식 Building 루트로 일하고, 산출+evidence를 받는다.  
0709 parent closure는 **landing 묶음만** 닫았고, 제품 잔여는 `03`의 7항목 + **지금 드러난 route 연료 회귀**다.

---

## 1. 왜 이 판을 다시 짜는가

### 1.1 Claude가 연 판 (`03-remaining-frontier-goal-0709`)

| # | 프론티어 | 0709 로그상 상태 |
|---|---|---|
| 1 | authoring 제품층 구현 | 설계完 · **W1a partial** · **W1b 미완** |
| 2 | Route V2 SHAPE A 초과 | HOLD · human gate 전 금지 |
| 3 | cleanup-10e order-chain | 미완 소형 |
| 4 | project vessel 물리분리 | 설계-먼저 · human gate |
| 5 | build→progress auto-refresh UX | 미착수 |
| 6 | charter-fill prompt UX | 미착수 |
| 7 | 릴리스/배포 | #1–#6 후 |

진행된 것: W1a structure_plan(delta-green) · prevention 3-layer **설계** · session-id checker 오탐 수정 · salvage/정리.  
막힌 것: prevention L3/L1-L2 **v1이 resume dead_end로 사망** → v2 재발주 · **공식 발사 전반 resume dead_end**.

### 1.2 새로 확정된 막힘 (route 회귀) — 이전 판에 없던 critical path

```text
공식 발사(--graph-decl / assemble-arg only)
  → concern walk-on 으로 closure까지
  → hold ledger 없음
  → brick build resume → dead_end
  → dispose 는 red herring · salvage/WIP 만 유효
```

**함의:** `03`의 W1–W4는 “official route only”를 전제로 한다.  
그 전제 위에서 **resume/route가 죽으면** authoring dogfood · prevention 재발주 · UX 검증이 **전부 salvage 우회로에 기생**한다.  
그래서 잔여 7항목 **앞**에 **G0 Route Fuel** 을 끼운다.

### 1.3 두 종류의 pause (운영 모델 — 필수)

| | **(A) approval-hold** | **(B) closure walk-on concern** |
|---|---|---|
| ledger | hold 장부 있음 | 없음 |
| resume | 가능 | **dead_end** |
| 지금 기본 생산 | 거의 없음 | **이게 기본** |
| 처분 | resume forward/reroute | salvage 또는 제품 수리 후 재발사 |

---

## 2. Goal Phases (능력 계단)

구현 나열이 아니라 **닫히면 다음이 열리는 게이트**다.  
아래 단계 Exit 없이 위 단계 Building을 양산하지 않는다.

```text
G0  Route Fuel        pause 형태 정합 · resume 가능 경로 복구
G1  Official Continuity  한 앞문 위에서 hold→resume→완주 dogfood
G2  Authoring Product    발주서작성 제품층 (W1 잔여)
G3  Prevention Live      공식루트 우회 방지 3층 live (observe→raise)
G4  Customer Surfaces    UX #5·#6 + 소형 #3
G5  Structural Gates     vessel #4 · Route V2 beyond A (#2) — 설계+human gate
G6  Release Readiness    #7 · 고객 path 자기개밥 재증명
```

---

### G0 — Route Fuel (지금 최우선)

**의도**  
공식 앞문이 resume이 **먹을 수 있는** pause를 다시 생산하거나,  
생산하지 못하는 pause를 resume 표면에서 **속이지 않게** 자른다.

**사용자/COO 체감**
- `brick build resume --decl …` 이 정상 hold에서 dead_end가 아니다.
- hold 없는 건물에 dead_end가 나면 메시지가 “harvest 맹신”이 아니라 **원인 종류(A/B)** 를 가리킨다.
- mid-walk COO/human hold를 **문서화된 graph-decl 문법**으로 재현 가능하다 (또는 공식 확장이 착지했다).

**필수 능력 (택1 이상이 Exit 조건에 명시적으로 충족)**

| 트랙 | 내용 | 비고 |
|---|---|---|
| **G0-A Repair** | assemble-arg/`--graph-decl`에서 mid gate-hold + completion edge 충돌 없이 선언 | raw packet 전면 부활은 최후 수단 |
| **G0-B Semantics** | concern/`implementation_gap` walk-on이 hold ledger를 남기거나, frontier kind를 resume 불가 kind로 분리 | 가짜 link_paused 유인 제거 |
| **G0-C Surface** | resume preflight: no-hold vs evidence_incomplete vs match fail 구분 + salvage 힌트 | 운영 정합 |

**권장 순서:** G0-C(즉시 정직) → G0-A 또는 G0-B(제품 수리) 중 하나를 본 Building으로.

**필수 증거**
- probe: (1) hold 있는 최소 graph → resume forward 1회 ok  
- probe: (2) 현재 walk-on 건물 → dead_end + **명확한 이유 kind**  
- 코드 좌표: `assembly.py` packet reject / gates outgoing=1 · `resume_declaration.py` dead_end · `driver.py` dispose  
- `check_profile.py` focused (resume/hold 관련) + 회귀 `--all` delta 정직 기록  

**Exit**
- [ ] G0-A **또는** G0-B 중 최소 하나 착지 (commit + clean-tree 재현)  
- [ ] G0-C 메시지/문서 정합 (발주 템플릿: hold 그래프 vs salvage 분기)  
- [ ] “한 루트” 유지: 사람 앞문은 여전히 `brick build` (+ resume)  
- [ ] salvage는 **예외 경로**로 문서화 (상시 운영 아님)  

**비범위**
- Route V2 Movement/route_target 확장 (#2)  
- authoring 제품 전체 구현  
- vessel 물리 이동  

**의존** 없음 (지금 막힌 critical path의 입구).

---

### G1 — Official Continuity

**의도**  
G0 위에서 **발사 → (선택 hold) → resume → complete** 가 한 체인으로 돈다.  
prevention·authoring 재발주가 salvage 없이 공식 경로로 완주 가능하다.

**Exit**
- [ ] dogfood Building 1: graph-decl 발사 → intentional hold → resume forward → `frontier_kind=complete`  
- [ ] dogfood Building 2: concern이 의도된 정책대로 hold 또는 non-resume frontier로 **정직 표기**  
- [ ] dispose 후 WIP anchor + evidence root만으로 resume 가능 (워크트리 잔존 불필요) 증명  
- [ ] REAL HOME focused profiles green  

**비범위** UX polish · vessel · release.

**의존** G0 Exit.

---

### G2 — Authoring Product (`03` #1 / W1 잔여)

**의도**  
`building-call-authoring-architecture-plan-0709a` 의 **제품층** 착지.  
설계·리뷰는 이미 있음. 구현이 남음.

**하위**
| ID | 내용 | 상태 힌트 |
|---|---|---|
| G2-a | W1a defer: structure_plan negative fixtures (duplicate-branch · multi fan-out) + 변이 RED | 코드 로직, fixture 미비 |
| G2-b | W1b: authoring STEP3 방출 · 스킬 노출 · cap-hold · 프리셋→COO→정식 CLI | **미완 본체** |
| G2-c | #3 cleanup-10e order-chain (소형, 병렬 가능) | 미완 |

**Exit**
- [ ] G2-a fixture/변이 닫힘  
- [ ] G2-b: 발주서작성 → 확인 → lowering → `brick build` 가 **G1 경로**로 dogfood complete  
- [ ] direct_preset = trivial only 정책 문서+체커 정합  
- [ ] clean-tree profile green  

**금지:** COO live checkout 직접 제품 구현. declared Building only.

**의존** G1 (authoring dogfood가 resume/공식 연속성에 묶이므로).  
*예외:* G2-a fixture-only / G2-c order-chain 은 G0와 **병렬 가능** (route 비의존).

---

### G3 — Prevention Live (`03` prevention 트랙)

**의도**  
`prevention-official-route-3layer-design-0709.md` 를 **observe → (승인 후) raise** 로 live.

| 층 | 내용 |
|---|---|
| L1 | SessionStart hook |
| L2 | PreToolUse Bash hook |
| L3-3a | walker token gate **observe** (hard closure 후보의 관측만) |
| L3-3b | raise 살상 — **Smith 승인 필수** |

**현재 정직 상태**
- 설계 착지됨.  
- L3-3a/L1-L2 v1: **resume dead_end / 작업 0** 으로 사망 → salvage 존재.  
- v2 재발주 이력 있음 — **G0/G1 없이 재발사하면 같은 구멍**.

**Exit**
- [ ] L1/L2: 스크립트 단위 allow/deny 변이 + (착지 후) 새 세션 hook 실발동 증거  
- [ ] L3-3a observe: clean floor (build/resume/resume-absent 관측 0 위반 정책)  
- [ ] L3-3b: Smith 승인 문서 후에만 Building  
- [ ] 한계 2개 문서화 유지 (managed-settings lock · 고의 토큰위조)  

**의존** G1 권장 (재발주가 공식 resume/hold 를 타야 함). salvage 완주만으로 G3 Exit 선언 금지.

---

### G4 — Customer Surfaces (`03` #5·#6 + 잔여 소형)

**의도**  
고객이 보는 표면: progress 자동성 · charter-fill.  
W1 표면 불변 확인 후.

**Exit**
- [ ] #5 build→progress auto-refresh: 문서+실측 1회  
- [ ] #6 charter-fill prompt UX: 문서+실측 1회  
- [ ] 공식 루트 우회 없는 구현 (G3 관찰과 충돌 시 G3 우선)  

**의존** G2-b 기본 완료 (authoring 토대). G2-a/c 와 병렬 가능하면 병기.

---

### G5 — Structural Gates (`03` #4·#2)

**의도**  
토대를 흔드는 일. **설계-먼저 + human gate.** 코드 확장 선제 금지.

| ID | 내용 | 게이트 |
|---|---|---|
| G5-a | project vessel 물리분리 / 템플릿 이주 | Smith 승인 · 파괴적 이동 금지 기본 |
| G5-b | Route V2 beyond SHAPE A | 설계 · human gate · Movement/route_target/Link/AgentFact 경계 재확인 |

**Exit**
- [ ] 각 항목: 설계 Building complete + human gate 기록 + (승인 시에만) 구현 Building  
- [ ] SHAPE A advisory 기본선 유지 증명 (확장 전)  

**의존** G2–G3 안정 (안 그러면 구조 작업이 salvage 지옥과 겹침).

---

### G6 — Release Readiness (`03` #7)

**의도**  
#1–#6(및 G0–G5 해당분) 착지 후, 고객 path 자기개밥·배포 준비.

**Exit**
- [ ] fresh/minimal customer path 재증명 (P7 계열 정직 caveats 유지)  
- [ ] release surface scrub · guard profiles  
- [ ] remaining_not_proven 명시 리스트  

**의존** G0–G5 중 제품 경로에 해당하는 Exit (최소 G0–G2–G4; G5는 승인한 것만).

---

## 3. 의존 그래프

```text
                    ┌──────────────┐
                    │ G0 Route Fuel│  ← 지금 입구
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ G1 Continuity│
                    └──────┬───────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           G2 Authoring  G3 Prevention  (G2-a/c 소형은 G0∥ 가능)
              │            │
              └─────┬──────┘
                    ▼
                 G4 UX
                    │
                    ▼
         G5 Structural (human gate)
                    │
                    ▼
                 G6 Release
```

**병렬 허용**
- G0 진행 중: G2-a fixture · G2-c order-chain · 문서/GOAL 갱신 · salvage 회수  
- G0 미완 상태에서 G2-b/G3 **본발사 양산 금지** (같은 dead_end 재생산)

---

## 4. 지금 당장 운영 규칙 (COO)

```text
1. 이미 나온 link_paused + no hold ledger 건물
   → resume 반복 금지
   → 가치 있으면 salvage(c) · 없으면 archive
   → harvest는 orphan tail 실측 있을 때만

2. 새 Building 발사
   → G0 Exit 전: hold가 필요하면 발주서에 "hold 불가 시 salvage 전제" 명시
   → G0 Exit 후: hold/resume dogfood 템플릿 사용

3. COO는 live 구현 금지. declared Building + worktree.
4. frontier_kind=complete ≠ parent GOAL complete.
5. Movement = forward|reroute only. hold/paused ≠ Movement.
6. 측정: clean detached worktree · REAL HOME · check_profile.
7. 3회+ 동일 실패 → 얕은 패치 금지, 근본(G0 모델)으로.
```

---

## 5. 마스터 큐 (이 문서 작성 시점)

### 지금 (G0–G1) — 2026-07-09 EXIT

```text
[x] G0-B/C resume dead_end_kind + salvage/harvest next_command
[x] mid-node gates:[coo-review] assemble HOLD + live link_paused
[x] G1 dogfood g1-mid-hold-resume-dogfood-0709 → resume → complete
[x] OFFICIAL_ROUTE_MEMO exit log updated
Evidence: status/kernel/g0-g1-exit-evidence-0709.md
```

### 다음 (G2+ — BRICK buildings only)

```text
[ ] G2-b authoring STEP3 제품 dogfood
[ ] G3 L1/L2/L3-3a 공식 경로 재발사
[ ] L3-3b Smith 승인 게이트
```

### 병렬 소형 (route 비의존)

```text
[ ] G2-a structure_plan negative fixtures
[ ] G2-c cleanup-10e order-chain
[ ] salvage refs 회수·착지 후보 목록 유지 (refs/brick-salvage/*)
```

### 나중 (human gate)

```text
[ ] G4 #5 #6
[ ] G5 #4 #2
[ ] G6 release
```

### 명시적 remaining_not_proven (상속)

```text
- Route V2 beyond SHAPE A (Movement/route_target/concern_kind/Link/Agent/AgentFact)
- vessel 파괴적 이주
- managed-settings hook 잠금 / 고의 토큰 위조 하드닝
- 광의 provider reliability · 완전 fresh-human auth transcript
- parent customer-ready "always" 주장
```

---

## 6. 성공 판정 규율 (모든 G에 공통)

Success is **measured, never claimed.**

1. 해당 G Exit 체크리스트 전부.  
2. 코드 착지 시: clean worktree에서 관련 profile 또는 `--all` (delta 정직).  
3. Building이면 `frontier_kind` + evidence_root 실측 (exit 0 ≠ PASS).  
4. COO disposition forward는 **증거 열거 후**.  
5. 자기문서 “좋다” 판정 금지.

---

## 7. 산출물 / 다음 발주 힌트

| 다음 Building 후보 | Goal | 한 줄 |
|---|---|---|
| `route-fuel-hold-semantics-…` | G0-B/C | walk-on vs hold 구분 · resume 메시지 · 발주 템플릿 분기 |
| `route-fuel-graph-decl-hold-…` | G0-A | graph-decl mid hold 문법/엣지 자동 · probe fixture |
| `route-fuel-resume-dogfood-…` | G1 | hold→resume→complete |
| `authoring-w1b-…` | G2-b | STEP3 제품 dogfood (G1 후) |
| `prevention-l3-3a-…` | G3 | observe live on official path (G1 후) |

---

## 8. 문서 관계

```text
00-GOAL-OF-RECORD / customer-ready-goal-phases-0629  → 장기 customer-ready 북극
02-unified-continuous-build-0708                     → 0708 통합 (상당수 ✓)
03-remaining-frontier-0709                           → 7항목 + W1–W4 (Claude 연 판)
parent-goal-closure-0709                             → 0709 landing 묶음 마감 기록
04 (this file)                                       → 03 + route 회귀를 합친 **현재 실행 계단**
```

충돌 시: **라이브 코드·Building evidence > 이 문서 > 03 > 02**.  
이 문서는 03을 폐기하지 않고 **critical path를 G0로 재삽입**한다.

---

## 9. COO disposition (이 문서 작성 시)

```text
Movement candidate for planning: forward into G0
Reason:
  - 03 frontier remains open (authoring/prevention/UX/…)
  - resume dead_end makes official-route-only dogfood structurally unreliable
  - salvage works but must not become the permanent second route
Next: open one declared Building for G0-A or G0-B (+ thin G0-C), not a broad authoring fan-out.
```

---

**복기:**  
Claude의 남은 골은 **제품 프론티어 7개**였고, 그 전제(공식 한 길)가 **resume 연료 회귀**로 흔들렸다.  
그래서 계단 입구를 **G0 Route Fuel** 로 다시 박고, 그 위에 G1 Continuity → G2 Authoring → G3 Prevention → G4 UX → G5 구조 → G6 Release 로 쌓는다.  
지금 할 일 하나는 선명하다: **hold ledger가 있는 pause를 공식 앞문이 다시 만들게 하거나, 못 만드는 pause를 resume에서 잘라 salvage로 보내라.**

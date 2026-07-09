# 업무 전체 목록 (필요성 순서 · 볼륨 상/중/하)

| | |
|---|---|
| **Status** | support evidence · COO master work queue |
| **Date** | 2026-07-09 |
| **Authority** | BRICK COO · necessity-ordered (not ease-ordered) |
| **Parents** | `GOAL/03-remaining-frontier-goal-0709.md` · `GOAL/04-goal-phases-0709-route-and-frontier.md` · `GOAL/05-coo-ladder-closure-0709.md` · `handoff-coo-0709-remaining-frontier.md` · `residual-push-exit-0709.md` · pure-dev ACTIVE · `OFFICIAL_ROUTE_MEMO.md` · prevention / route-v2* · brick-task-author 실측 |
| **Proof limit** | not source truth · not success/quality · not Movement authority |

---

## 작성 규율

```text
- 순서 = 필요성(의존·차단·정직 부채), 쉬운 일 우선 아님.
- 볼륨 = 일의 크기(상/중/하), 우선순위 아님.
- 근거 = GOAL/03·04·05 · handoff · residual · pure-dev ACTIVE · OFFICIAL_ROUTE_MEMO · prevention · route-v2* · brick-task-author 실측 결함.
- 이미 닫힌 것은 재작업이 아니라 잔여/검증/후속만 적음.
- 땜빵 한 줄 패치로 대체하지 않음.
- 빠뜨리지 않음 · 편한 길 찾지 않음.
```

### 범례

| 기호 | 의미 |
|---|---|
| **볼륨 상** | 프로그램/다 Building·다 페이즈 또는 엔진 핵심 시임 |
| **볼륨 중** | Building 1~수 발 또는 의미 있는 엔진/제품 슬라이스 |
| **볼륨 하** | 회수·보드·관측·ops·단발 검증 |
| **A** | 세션 직접 (회수·보드·관측·발주·resume) |
| **B** | 공식 Building (`brick build` / resume) |
| **S** | Smith 승인/조직 정책 전제 |

---

## 0. 문서 스택에서 뽑은 의존 골격

```text
[기반 신뢰]  공식 빌딩 land/WIP가 안 사라짐 · hold/resume 정직
     ↓
[정직 부채]  pure-dev D1–D4 · residual overclaim 가드 유지
     ↓
[제품 층]    G2 잔여 → G3 잔여 → G4 잔여
     ↓
[구조]       G5 Route V2 beyond A (프로그램) · vessel migrate(승인 시)
     ↓
[릴리스]     G6 fresh-auth · commercial
     ↓
[별축]       Deku · ops hygiene (병렬 가능하나 제품 대체 아님)
```

- `04` 의존: G0→G1→(G2∥G3)→G4→G5→G6.
- `05`: **운영 사다리 CLOSED / 제품 residual OPEN**.
- residual R1–R11: **보드 터미널 ≠ 제품 전부 구현됨**.

---

## 1. 순서 목록 (전부)

### 구간 I — 공식 루트로 개발해도 결과가 안 사라지게 (기반)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **1** | **complete/write 후 land 강제** ← write=True로 diff가 있는데 building-output/main land 없이 complete로 끝나는 경로를 금지하거나 강제 land/WIP 성공을 엔진이 보장 | skill 0708 교훈 · D3/D4 WIP-only · `driver.py` commit/WIP/dispose | **상** | **B** | 미착수 (D3/D4가 증상) |
| **2** | **hold·미완 시 dispose/회수 정합** ← hold/incomplete에서도 worktree dispose는 유지 가능하되, WIP anchor·adapter_cwd·resume 재료가 **실패 closed** 되게 하거나 hold 시 보존 정책 명시 구현 | `driver.py` finally 무조건 dispose · G1은 “dispose 후 evidence로 resume” 증명했으나 **main land와 별개** · skill: proposal-approval 최초 미완 WIP 없음 | **상** | **B** | 미착수 · 예전에 밀림 |
| **3** | **cli `--graph-decl` 미완 경로 WIP 앵커** ← `run_building_plan` park만 앵커 있고 proposal-approval 최초 미완은 소멸하는 비대칭 제거 | brick-task-author §발사 체크 7–8 · 0708 fugu 사건 | **중** | **B** | 엔진 수리 후보로 skill 명시 |
| **4** | **walk-on(G0-B) 제품 정합 (잔여)** ← concern walk-on이 hold ledger를 남기거나 resume 불가 frontier로 **운영 기본이 salvage가 아니게** (G0 Exit은 B/C 정직·A 문법 쪽; 생산 기본이 아직 walk-on이면 잔여) | `04` G0-B · G0 probe · OFFICIAL_ROUTE (A/B pause) | **상** | **B** | 운영 정직은 EXIT; **생산 경로 수리 여부는 OPEN** |
| **5** | **공식 루트 운영 규율 준수 (상시)** ← 제품 구현은 Building only; live COO 구현 금지; no-hold에 resume 반복 금지; salvage=예외 | handoff · `04` §4 · OFFICIAL_ROUTE · pure-dev 규율 | **하**(규율) / 위반 시 **상** | **A** | 상시 · 위반 이력 있음(live 선코딩) |

---

### 구간 II — pure-dev 큐 정직 마감 (ACTIVE 부채)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **6** | **D4 ship-copy 결과 main harvest** ← building `pure-dev-d4-r4-ship-copy-0709` complete 후 WIP `457fbc875`를 main에 반영 | pure-dev D4=R4 · G2-c · residual R4 deferred → pure-dev 재오픈 | **하** | **A** | WIP only · main 없음 |
| **7** | **D4 focused 검증** ← ship-copy에 hold-disposition 포인터·land stamp 실측 | pure-dev Exit 조건 4 | **하** | **A** | harvest 후 |
| **8** | **D4 실패 시 재발사** ← harvest 불가·WIP 손상 시 graph-decl 구현 Building 재완주 | pure-dev 규율 Building only | **중** | **B** | 조건부 |
| **9** | **D3 보드 DONE 포인터** ← bid + land `0876ae2cd` + probe 요약 기입 (typed proof stamp land 완료분) | pure-dev D3=R7 · residual R7 일부 | **하** | **A** | land·profile green · 보드 PENDING |
| **10** | **D2 보드 CANCELLED(KEEP)** ← vessel 물리 분리 안 함(Smith Option A) 명시 · migrate Building 열지 않음 | pure-dev D2=R6 · vessel-keep · G5-a KEEP · residual R6 | **하** | **A** | 결정 있음 · 보드 미기입 |
| **11** | **D1 증거 재확인** ← Route V2 beyond-A **min slice** (shared classifier 등) building complete + sha + probe 유지 확인 · **로드맵 완주 주장 금지** | pure-dev D1=R5 · residual R5 freeze + pure-dev 재오픈 slice | **하** | **A** | land 됨 · min only |
| **12** | **pure-dev Exit 검증 묶음** ← D1–D4 ∈ {DONE, CANCELLED, OUT_OF_SCOPE} + 1–5 조건 + overclaim 0 | pure-dev 골 Exit | **하** | **A** | 6–11 후 |
| **13** | **D5 Deku 비혼입 유지** ← pure-dev 보드 OUT_OF_SCOPE 유지 · BRICK 큐에 가짜 DONE 금지 | pure-dev · residual R11 · `05` | **하** | **A** | OUT_OF_SCOPE |

**pure-dev D 큐 정의**

| ID | 정의 |
|---|---|
| **D1** | Route V2 beyond SHAPE A **최소 슬라이스** 코드 land + focused check (로드맵 전체 아님) |
| **D2** | vessel 물리 분리 — Smith KEEP면 CANCELLED(개발 불요) |
| **D3** | token-forgery harden 코드 land + probe |
| **D4** | G2-c ship-copy skill/prompt 동기 + 엔진 정책 불일치 0 |
| **D5** | Deku — 별 골 · 미열면 OUT_OF_SCOPE |

---

### 구간 III — 자산·ops hygiene (제품 대체 아님 · 유실 방지)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **14** | **stale worktree/sandbox 정리** ← disposable·종료 샌드박스 remove (파괴적 vessel 이동 아님) | `04` 병렬 ops · `05` ops hygiene · 03 log 과거 1회 | **하~중** | **A** | 반복 필요 |
| **15** | **untracked buildings/inbox 아카이브** ← 비파괴 /tmp 아카이브 · salvage ref 유지 | `04` · `05` | **하~중** | **A** | inbox flood 관측됨 |
| **16** | **salvage ref 목록·회수 후보 유지** ← `refs/brick-salvage/*` harvest-blind 금지 · 가치 있으면 착지 | `04` · handoff · 03 보존 자산 | **중** | **A** (+필요 시 **B**) | 다수 salvage 존재 |
| **17** | **WIP/building-output 미회수 전수 스캔** ← pure-dev 외 포함, complete+WIP-only·commit 없는 빌딩 목록화 후 harvest | skill · 실측 패턴 | **중** | **A** | 미착수 |

---

### 구간 IV — G2 Authoring 제품 잔여 (`03` #1 · `04` G2 · `05` 일부 EXIT)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **18** | **G2-a structure_plan negative fixtures** ← duplicate-branch · multiple fan-out fixture + 변이 RED (로직 있고 fixture 미비분) | `03` W1a defer · `04` G2-a 체크 미체크 · g2-focused “fixture 안 닫힘” | **중** | **B** | OPEN으로 문서 잔존 |
| **19** | **G2-c order-chain / ship-copy 본절** ← `coo-order-chain-consistency` map 이후 Watch A 동기·B 분류·(C는 pin 동시) · skill/ship-copy/엔진 정책 불일치 0 · D4 stamp는 부분집합 | `03` #3 · `04` G2-c · parallel-hygiene · residual R4 · pure-dev D4 | **중** | **B** (+A harvest) | map done · repair optional/OPEN · D4 WIP |
| **20** | **G2-b authoring 제품 경로 재증명** ← 발주서 빌딩(building-call-authoring) → COO 검토 → `brick build` dogfood complete가 **G1 경로**로 재현 가능한지 확인; 갭 있으면 구현 Building | `03` W1b · `04` G2-b · handoff 발주 규율 · `05` G2 EXIT(profiles) | **상** | **A** 관측 후 갭 시 **B** | 운영 EXIT 주장 있음 · **풀 체인 상시 사용은 미정** |
| **21** | **direct_preset=trivial only 정책 정합** ← 문서+체커 (`04` G2 Exit 항목) | `04` G2 Exit | **중** | **B** | G2 묶음 잔여 가능 |
| **22** | **어려운 발주 = authoring preset 체인 상시화** ← architecture-plan≠발주서; COO 손 task 실무자화 금지 | handoff Smith 교정 · brick-task-author | **중**(습관+스킬/템플릿) | **A**+필요 시 **B** | 규율 · 자동화 미완 가능 |

---

### 구간 V — G3 Prevention 잔여 (`03` 방지 · `04` G3 · `05` · residual)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **23** | **G3 prevention live 재 dogfood** ← L1/L2/L3-3a land 이후 **공식 경로**에서 allow/deny·observe clean floor 재증명 (land-only EXIT 아님) | `05` remaining · residual R2 DONE은 dogfood 1회 · “full re-dogfood residual” | **상** | **B** | residual R2 complete 있으나 `05`는 re-dogfood residual로 남김 |
| **24** | **L3-3b raise 유지·회귀 방지** ← lethal `enforce_official_launch_token` land·dogfood 후 회귀 프로브; 완화 금지 | residual R1 DONE · prevention 설계 L3-3b | **중** | **A** probe / 회귀 시 **B** | land `15ccd10ac` 등 |
| **25** | **고의 토큰 위조 harden 다음 층** ← typed proof(D3) 너머 process-attested/mint 좁히기 등 (org managed-settings와 분리) | prevention 한계 · residual R7 · pure-dev D3 일부 | **상** | **B** + **S** | R7 DEFERRED · D3 stamp층만 |
| **26** | **managed-settings hook 잠금** ← `allowManagedHooksOnly` 등 조직 정책 | prevention · residual R7 · `05` | **중** | **S** (+문서/가이드 **A**) | 코드만으로 불가 명시 |

---

### 구간 VI — G4 Customer surfaces 잔여 (`03` #5·#6 · `04` G4 · residual R3)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **27** | **#5 progress auto-refresh 다중 경로 dogfood** ← land 이후 customer path 다경로 재증명 | `05` G4 EXIT land · broader dogfood residual · residual R3 | **중** | **B** | land `f3976946b` |
| **28** | **#6 charter-fill UX 다중 경로 dogfood** ← 동일 | `05` · residual R3 | **중** | **B** | land `ef1a36977` |

---

### 구간 VII — G5 Structural (`03` #2·#4 · `04` G5 · residual R5·R6)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **29** | **Route V2 beyond SHAPE A — 프로그램 재오픈 게이트** ← residual R5는 **freeze DONE**(엔진 미구현); 확장 시 **새 설계 Building + 별도 Smith 승인** 필수. SHAPE A advisory 기본선 유지 증명 | residual R5 · route-v2-beyond-a-smith-close · `03` #2 금지선 · `04` G5-b · `05` remaining | **하**(게이트) / 프로그램 전체는 **상** | **S**+**A** 후 **B** | freeze 상태 · pure-dev D1은 min slice일 뿐 |
| **30** | **Route V2 beyond A — 설계 페이즈** ← Movement / route_target / concern_kind / Link / Agent / AgentFact 경계 재설계 · 6e SHAPE A와 충돌 없이; SHAPE B shared classifier는 설계상 deferred 고위험으로 이미 구분 | route-v2-6e design · human-gate packet/approval · 6d review | **상** | **B** (design Building) | 설계 노트 일부 있음 · beyond-A 엔진 설계 미개봉 |
| **31** | **Route V2 beyond A — 구현 페이즈 분할 실행** ← 승인 후 walker/runtime/policy/surface를 **다발 Building**으로 (단일 “한 줄” 금지). 예: 관측 확장 → 분류 정합 → walker 연결(승인 범위 내) → resume/hold 정합 → dogfood·회귀 프로브 | `03` #2 · `04` G5-b · pure-dev remaining_not_proven beyond-A 전체 | **상** | **B** 다발 | **미착수 프로그램** |
| **32** | **Route V2 회귀 프로브 고정** ← SHAPE A 불변 + beyond 슬라이스별 focused profile/변이 RED | `04` 성공 규율 · 03 증거 규율 | **중** | **B** | 31과 병행 |
| **33** | **vessel 물리 분리/이주** ← `project/brick-protocol` 파괴적 이동·템플릿 이주. **현재 KEEP**; 재개 시 새 human gate + Building | `03` #4 · G5-a · dogfood-vessel approval · residual R6 · pure-dev D2 | **상** | **S** 후 **B** | KEEP · 지금 개발 금지에 가까움 |
| **34** | **building_plans 위치 등 구조 결정 후속** ← KEEP 결정 이후 실제 이동이 필요해지면 별 게이트 | building-plans-location-decision 등 | **중** | **S**/**B** | KEEP 계열 |

---

### 구간 VIII — G6 Release (`03` #7 · `04` G6 · residual R8·R9)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **35** | **fresh-clone + brand-new-human auth 신뢰성** ← 측정 transcript · NOT_PROVEN 유지 구간 축소 | `05` G6 · residual R8 · `04` remaining | **상** | **B**+**A** 측정 | NOT_PROVEN |
| **36** | **commercial release / publication** ← repo proof 너머 배포 | residual R9 · `03` #7 · `05` | **상** | **S**+**B** | NOT_PROVEN |
| **37** | **release surface scrub · guard profiles** ← `04` G6 Exit 항목 | `04` G6 | **중** | **B** | G6 묶음 |
| **38** | **customer entry path 재증명** ← P7 계열 caveats 유지하며 최소 고객 path | `04` G6 · `05` measured slice EXIT | **중** | **B** | measured slice만 EXIT |

---

### 구간 IX — 어댑터·주변 제품

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **39** | **adapter:grok-local 유지·회귀** ← first-class performer land 후 회귀 | residual R10 DONE · adapter-grok-local-land | **하~중** | **A**/**B** | DONE · 회귀만 |
| **40** | **Deku 구현 (별 골)** ← design frozen; residual R11 DEFER; pure-dev D5 OUT; `05` separate ACTIVE only after residual choice | residual R11 · `05` · pure-dev | **상**(프로그램) | 별 골 **B** | 지금 BRICK 큐 밖 |

---

### 구간 X — 메타·보고·원장 (개발 아님 그러나 필수 업무)

| # | 업무 ← 정의 | 출처 | 볼륨 | 누가 | 상태 힌트 |
|---:|---|---|---|---|---|
| **41** | **ACTIVE / OFFICIAL_ROUTE / GOAL 문서 정합** ← 사다리 CLOSED vs 제품 OPEN vs pure-dev ACTIVE 혼선 제거 (문서 작업이지만 **허위 DONE 방지**에 필요) | ACTIVE · OFFICIAL_ROUTE stale 문구 · 05 · pure-dev | **하** | **A** | 메모 서로 어긋남 관측 |
| **42** | **origin/main push (Smith 요청 시)** ← 착지 후 origin==HEAD | 03 증거 규율 · 05 next Smith | **하** | **A** (+승인) | ahead 상태 이력 |
| **43** | **착지 판정 규율** ← clean detached worktree · profile/`--all` · 자기검증 금지 · frontier≠parent complete | 03 · 04 §6 · handoff | **하**(상시) | **A** | 상시 |
| **44** | **3회+ 동일 실패 시 근본 복귀** ← 얕은 패치 금지 | 03 금지선 · 04 §4 | **하**(상시) | **A** | 상시 |

---

## 2. 필요성 순서 한 줄 (번호만)

```text
1 land강제 → 2 hold/dispose·회수 → 3 graph-decl미완 WIP
→ 4 walk-on제품정합(잔여) → 5 공식루트규율(상시)
→ 6–13 pure-dev 정직마감
→ 14–17 ops·salvage·미회수스캔
→ 18–22 G2 잔여
→ 23–26 G3 잔여
→ 27–28 G4 잔여
→ 29–34 G5 (Route V2 프로그램 + vessel)
→ 35–38 G6
→ 39–40 주변·Deku
→ 41–44 메타·상시
```

### 병렬 허용 (`04`)

```text
- 1–3 진행 중: 14–17 ops, 18 G2-a, 6–13 pure-dev 회수.
- 1–2 없이 Route V2 본발사 양산 = 같은 유실 재생산 → 필요성상 금지에 가깝다.
- G5 Route V2(29–32)는 게이트(29) 전 코드 확장 금지 (03·R5 freeze).
```

---

## 3. 볼륨 요약

| 볼륨 | 번호 |
|---|---|
| **상** | 1, 2, 4, 20, 23, 25, 30, 31, 33, 35, 36, 40(별) |
| **중** | 3, 8, 16, 17, 18, 19, 21, 22, 24, 26–28, 32, 34, 37, 38, 39 |
| **하** | 5(상시), 6–13, 14–15, 41–44 |

---

## 4. “이미 닫힘” (재구현 말고 잔여만 위에 반영)

| 항목 | 문서상 | 위에 남은 일 |
|---|---|---|
| G0-A/C 문법·dead_end 정직 | EXIT | 4(생산 walk-on), 1–3(land/dispose) |
| G1 hold→resume dogfood | EXIT | 1–3과 별개 land 문제 |
| G2 profiles / W1b 일부 | 05 EXIT | 18–22 잔여 정직 |
| G3 L1/L2/L3-3a land · L3-3b residual DONE | land | 23–26 |
| G4 land #5#6 | land | 27–28 dogfood |
| G5 residual R5/R6 게이트 DONE | freeze/KEEP | 29–33 구현은 OPEN/금지 |
| G6 measured slice | EXIT 일부 | 35–38 full |
| pure-dev D1 min · D3 land | 부분 | 6–13 |
| R10 grok | DONE | 39 회귀 |

---

## 5. residual R1–R11 대조 (보드 터미널 ≠ 전부 구현)

| R | residual 처분 | 이 원장에서의 후속 |
|---|---|---|
| R1 L3-3b | DONE land | #24 회귀 |
| R2 prevention dogfood | DONE 1회 | #23 re-dogfood |
| R3 G4 UX dogfood | DONE 1회 | #27–28 multi-path |
| R4 G2-c ship-copy | DEFERRED | #6–8 · #19 |
| R5 Route V2 beyond A | DONE freeze · **엔진 미구현** | #29–32 프로그램 |
| R6 vessel split | DONE KEEP | #10 · #33(재승인 시) |
| R7 token/org | DEFERRED | #9 · #25–26 |
| R8 fresh-auth | NOT_PROVEN | #35 |
| R9 commercial | NOT_PROVEN | #36 |
| R10 grok adapter | DONE | #39 |
| R11 Deku | DEFERRED | #13 · #40 |

---

## 6. 한 줄

```text
필요성 순서의 본체:
  ① 공식 빌딩 결과 보존 엔진 (#1–#3)
  ② pure-dev 정직 마감 (#6–#13)
  ③ G2→G3→G4 잔여 (#18–#28)
  ④ Route V2 beyond A 프로그램 (#29–#32, 볼륨 상)
  ⑤ G6 (#35–#38)

Route V2를 작게 쓴 것이 아니라 앞에 엔진·부채가 막고,
beyond-A는 게이트 후 프로그램(상)으로 잡혀 있다.
```

---

## 7. COO disposition

```text
이 파일 = 필요성 순서 master work queue (support evidence).
NOT = customer-ready forever.
NOT = residual 문서 DONE 재주장.
NOT = pure-dev min slice = Route V2 전체.
NOT = 쉬운 일 우선 큐.

Next movement: Smith/COO가 #1부터 Building 발주할지,
pure-dev #6–#13 먼저 닫을지 선택. 순서 정의는 이 원장이 기준.
```

---

## 8. 재발 방지 — 지금까지의 실수 → 운영 프롬프트

이 절은 0709 pure-dev / residual / route / worktree 세션에서 **실제로 저지른 실패**를 근거로 한다.  
추상 미덕이 아니라 **금지 행동 + 대체 행동**이다. 이후 COO/에이전트는 이 프롬프트를 작업 전 로드한다.

### 8.1 실수 원장 (무엇을 잘못했는지)

| ID | 실수 | 결과 |
|---|---|---|
| M1 | Smith가 말한 **기반(worktree/land, 홀드여도 dispose)** 을 “pure-dev 밖 백로그”로 미룸 | 같은 유실 클래스(D3/D4 WIP-only) 재발 |
| M2 | **쉬운 닫기**(보드 CANCELLED, harvest, min slice)를 “지금 개발 전부”처럼 보드에 올림 | Route V2 등 **큰 제품**이 중/하로 밀려 보임 |
| M3 | residual **문서/게이트 DONE** 과 **제품 엔진 구현**을 한 보드에 섞음 | overclaim · “이미 끝난 것 같다” 착각 |
| M4 | **live-checkout** 으로 제품 코드 선구현 후 Building stamp로 메움 | 정식 루트 규율 위반 · 귀속 혼선 |
| M5 | Building `frontier=complete` 만 보고 **main land 없이** DONE에 가깝게 취급 | 제품 트리에 코드 없음 · harvest 사후 땜 |
| M6 | **발주서 빌딩 체인** 없이 graph-decl 짧은 경로만 반복 (풀 COO 체인 생략) | 발주 규율 붕괴 · 스킬 우회 습관 |
| M7 | hold/walk-on 구분 없이 **resume** 또는 harvest 힌트 남용 | dead_end · harvest-blind |
| M8 | pure-dev **min slice** 를 Route V2 **프로그램 완주**처럼 말하거나 축소 표기 | 크기·필요성 왜곡 |
| M9 | 우선순위를 **쉬운 것 / 빠른 증거** 로 잡음 | 필요성 원장(#1–#3) 역행 |
| M10 | 골 pause/clear 요청 중에도 **백그라운드 빌딩 셸** 방치·혼선 | 운영 통제 실패 체감 |
| M11 | 착지 후 **보드 포인터 미갱신** (D3 land 됐는데 PENDING) | Exit 조건 5 미충족 · 상태 거짓 |
| M12 | “운영 사다리 G0–G6 EXIT” 를 “제품 residual 완료”로 읽음 | `05` split claim 위반 |
| M13 | 엔진 구멍을 **세션 회수 루틴**으로만 감당**하고 수리 Building을 안 엶 | 땜빵 운영 고착 |
| M14 | 확 신 없으면 물어야 하는데 **추측으로 큐/완료 주장** | 거짓 진행 |

### 8.2 복붙용 운영 프롬프트 (작업 시작 전 · 매 발주 전)

아래 블록을 그대로 시스템/유저 프롬프트 또는 세션 첫 지시로 사용한다.

```text
You are BRICK COO / implementer on the live checkout.
Authority order: (1) this master-work-queue-necessity-0709.md §1–§8
(2) GOAL/04 then 03/05 (3) OFFICIAL_ROUTE_MEMO (4) brick-task-author skill.
Proof limit: support evidence only — not source truth, not success/quality, not Movement.

══════════════════════════════════════
HARD FAILS (stop; do not soft-reinterpret)
══════════════════════════════════════

1) NECESSITY ORDER, NOT EASE
   - Work order follows §2 of this file (#1 → #2 → …), not “smallest first”.
   - If Smith named a foundation fix (land/dispose/worktree), it is NOT “out of
     pure-dev backlog” unless Smith re-ranks in writing.
   - Do not rebuild a board that makes large product (Route V2 beyond A) look
     small or optional while listing harvest/board ticks as the main work.

2) NO FAKE DONE
   - residual / gate / document DONE ≠ product engine implemented.
   - frontier=complete ≠ land on main ≠ parent GOAL complete ≠ customer-ready.
   - pure-dev D1 min slice ≠ Route V2 program complete.
   - operator ladder G0–G6 EXIT ≠ product residual closed (see GOAL/05 split).
   - Board row DONE requires: building_id + commit/sha on product tree + probe
     summary. Missing any → not DONE.

3) OFFICIAL ROUTE ONLY FOR PRODUCT CODE
   - Product implementation: brick build --graph-decl|--preset --forward
     and brick resume --decl only.
   - Forbidden: live-checkout product coding then claiming Building DONE;
     py launcher as main path; walker/run_building_plan as human front door;
     raw --graph packet.
   - Emergency live hotfix: immediately re-attribute via follow-up Building +
     verify; never leave live-only as success.

4) LAND / WORKTREE HONESTY
   - Official path disposes sandbox worktrees (including on hold). That is
     expected. Code survival = output commit and/or WIP/salvage — not the
     worktree path.
   - complete + write=True + scoped diff with only WIP / no main land =
     NOT development-complete. Harvest or re-fire before DONE.
   - Do not paper over engine gaps (#1–#3) with permanent manual harvest as
     the strategy. Session harvest is recovery, not the product fix.
   - no-hold walk-on: resume is dead_end; salvage or re-fire. No harvest-blind.

5) AUTHORING CHAIN (when order is non-trivial)
   - Hard/ambiguous orders: building-call-authoring preset Building → COO
     review (Brick/Agent/Link) → implementation Building.
   - building-call-authoring is draft-only; it does not launch or land product.
   - Do not equate “I wrote a graph-decl yaml by hand” with full COO chain;
     short path is allowed only when scope is already fixed and stated.

6) SCOPE & SIZE HONESTY
   - Route V2 beyond SHAPE A is a PROGRAM (design gate + multi-Building).
     Never one-line “T2-1” as if it were a small residual tick.
   - R5 residual DONE = freeze SHAPE A, NOT beyond-A engine built.
   - R6 KEEP = no migrate; CANCELLED on pure-dev board — not “split done”.
   - D5 Deku stays OUT_OF_SCOPE unless a separate goal + Smith open.

7) MEASUREMENT
   - Only execution results count. No self-praise of your own docs/plans.
   - Probes: focused profile/checker + at least one RED variant when claiming
     harden/land. Save rc + summary under session scratch.
   - clean detached worktree measurements when judging land; delta-honest
     --all when required by goal docs.
   - 3+ same failure → root cause (engine/route model), no shallow patch loop.

8) BOARD & PROCESS CONTROL
   - After every land/harvest: update ACTIVE board pointers same turn.
   - On /goal pause|clear|stop: stop launching and say what background builds
     still run; do not silently continue product work.
   - Uncertainty → ask Smith. No guessed DONE, no guessed KEEP, no guessed
     beyond-A approval.

9) CLAIM LANGUAGE
   Forbidden claims:
     - customer-ready forever
     - Route V2 beyond A fully shipped (unless program exit evidence)
     - vessel migrated (while KEEP)
     - prevention forever / auth forever
   Allowed: measured slice land + sha + probe + remaining_not_proven list.

══════════════════════════════════════
BEFORE EACH ACTION (checklist; answer in evidence)
══════════════════════════════════════

[ ] Which master-queue # is this? Necessity rank vs ease?
[ ] Product code or session ops (harvest/board/probe)? If product → Building.
[ ] If Building: write=True? write_scope? after complete, where is sha on main?
[ ] Hold vs walk-on? Resume only if approval-hold ledger exists.
[ ] Does DONE language match § HARD FAILS 2 and 6?
[ ] Did I update the board if land changed?
[ ] Am I avoiding #1–#3 by manual workaround only? If yes, flag debt explicitly.

══════════════════════════════════════
DEFAULT NEXT WHEN UNSURE
══════════════════════════════════════

Open master-work-queue-necessity-0709.md §1, take the lowest unfinished
necessity number that Smith has not deferred, and either:
  - A: harvest/board/probe only, or
  - B: brick build --graph-decl … --forward (or authoring preset first),
never invent a smaller parallel board for comfort.
```

### 8.3 한 줄 (실수 요약)

```text
쉬운 닫기·문서 DONE·live 선코딩·complete-only DONE·Route V2 축소 표기·
기반 엔진 뒤로 미루기·보드 미갱신 = 금지.
필요성 원장 순서 + 공식 빌딩 + main land sha + 정직 remaining_not_proven 만 진행.
```

### 8.4 ≤4KB 골 프롬프트 (심볼릭 페이즈)

```text
정본: status/kernel/GOAL-PROMPT-necessity-master-0709.md
(§8.2 HARD FAILS + ΦI–ΦX 페이즈 + 심볼 · UTF-8 ≤4KB)
```

---

## 9. 0710 COO 인계 실측 갱신 (신규 COO · 넘겨받은 요약 실측 대조)

이 절은 0710 COO 인계 직후, 이전 세션 handoff(`HANDOFF-session-0709-pure-dev-master.md`)를
**믿지 않고** git 커밋 89개 + 코드 diff + 빌딩 frontier 실측으로 대조한 결과다.
§1 큐(0709 작성)를 실측 상태로 갱신한다. 근거는 support evidence — success/quality/Movement 아님.

### 9.1 워크트리 유실 근본원인 (사고① 확정)

```text
L3 게이트가 2번 land됨:
  fbbbe93e0 (07-09 21:13)  = observe-only, record_only_no_raise  [안전]
  15ccd10ac (07-09 22:14)  = "L3-3b raise" enforce_official_launch_token() 신설  [사고 트리거]
메커니즘: driver.py:940 워크트리 먼저 생성 → :959 run_dispatch로 walker 실행
  → walker_kernel.py:1377 게이트가 토큰 없으면 RuntimeError raise
  → non-complete(commit_sha 없음)라 finally가 그 워크트리 dispose → 유실.
트리거: cli.main mint 안 거친 비정식 in-process 진입(별프로세스 스폰/직접 import/mint없는 resume).
        설계(prevention-official-route-3layer-design-0709.md)가 [NOT PROVEN]으로 경고한 그 경로.
family: 0702 onecall-worktree-loss family(2) 재발(non-complete stop→dispose), 다른 트리거.
        reap storm(family 1) 아님 — reap은 24h staleness로 이미 막힘.
★ 이전 handoff는 fbbbe93e0만 알고 lethal land 15ccd10ac를 놓쳤다.
```

### 9.2 판단 — 정식 빌딩 vs 우회 (실측) ★0710 정정: "안전 단정"은 성급, 축2 미확정

★ 정정 사유(0710): 아래 "지금 안전"은 축1(L3 게이트)만 본 성급한 단정이었다.
   Smith가 "그럼 없던 문제를 있다고 판단한 거네?"로 지적. 소실에는 두 축이 있고
   축2는 아직 미확정 → 프로브로 확증 전까지 "안전"이라 박지 않는다. (상세=HANDOFF §4)

```text
축1 (L3 토큰 게이트) — 코드상 참 (이 부분은 실측 확인):
  cli.py:2141 main() → :2153 mint_official_launch_token() (typed OfficialLaunchProof)
  → driver.py:719 "no fork" in-process → contextvar 토큰이 walker까지 전파
  → import_identity.py:278/290 enforce: token_present=True → 통과 → 워크트리 생존.
  ∴ 비정식 진입(cli.main 밖 walker 직접 호출)만 게이트에서 raise→dispose.
     서브에이전트/워크플로가 walker 직접 호출 = 비정식 진입 = 유실 자초 → 안 한다.

축2 (미완 시 WIP 앵커 비대칭) — ★미확정 (이게 Smith가 짚은 진짜 우려):
  정식으로 들어가도, 미완(QA 반려/없는 deliverable 등)으로 끝나면 경로에 따라
  작업물이 refs/brick/wip/에 남거나(run_building_plan park/stop) 소멸한다.
  특히 cli --graph-decl proposal-approval 최초발사 미완 경로가 WIP 앵커 없이
  워크트리 처분하는지 = 미검증. (0708 fugu 3h 이주 500+파일 소멸이 이 축 의심)
  → HANDOFF §5 = 프리셋 vs 발주서 소실 샘플 프로브가 이 축을 확정한다.

∴ 결론(정정): "정식 build 안전"은 축1에 한해 참. 축2 미확정.
  #2/#24 수리를 정식 빌딩으로 한다는 방향은 유지하되, 그 전에 무해 소실 프로브로
  축2(미완 시 소실/생존)를 실행 결과로 확증한 뒤 "안전" 판정을 확정/정정한다.
```

### 9.3 §1 큐 상태 갱신 (실측이 바꾼 지점)

```text
#2  hold/dispose  : "예전에 밀림" → ★워크트리 유실 뿌리. #24와 한 덩어리. 최우선.
#24 L3-3b raise    : "유지" → ★정당 호출자까지 죽이는 raise 회귀 수리. 첫 스텝=RED 프로브로 유실 재현.
#1  land 강제      : 미착수 유지. D3/D4가 증상.
#9  D3            : "보드 DONE 포인터"(하,A) → ★3갈래 엉킴 정리+정당 land(중,B)로 격상.
                    body-v1(미완 NO_FRONTIER)/body-reland-0709c(complete+WIP 미수확)/token-harden(link_paused).
#31 RV2 beyond-A  : 엔진 코드(route_scope/route_v2_engine) 부재 실측 확인. #1-2 전 본발사 금지 재확인.
```

### 9.4 신규 지뢰 (0709 큐 작성 후 발생)

```text
- charter/queue UNTRACKED: GOAL-PROMPT-necessity-master-0709.md + master-work-queue-necessity-0709.md
  둘 다 git 미추적. 보드가 authority로 가리키는데 clean checkout 시 소실 위험. (#15/#41)
- 가짜 EXIT 2커밋: f2fd50a35, 8f7d03b16 이 여전히 main ancestry에 존재. 보드 Status로만 무효화. (#41)
- worktree 11개: dispo 잔재 9(/private/tmp/brick-coo-dispo-*) + 실작업 2(~/.brick). (#14)
- deku 에비던스 63 untracked: 별개 프로젝트(project:deku). brick 골과 무관 — 혼입 금지. (#13/#15)
```

### 9.5 미확인 (정직)

```text
- 워크트리 유실의 캡처된 런타임 로그: 없음. 코드경로+Smith 보고로 확정. #24 빌딩이 RED로 재현.
- shipped shape_b 태그가 SHAPE-A-only 승인 위반인지: 미확정.
- rerouted route-walker-6e-7 QA-repair 세그먼트 green closure: 없음(미확인).
```
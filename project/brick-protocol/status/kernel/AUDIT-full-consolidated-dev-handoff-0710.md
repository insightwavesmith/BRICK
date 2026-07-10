# BRICK 통합 감사 · 개발 인계 문서 (0710 — 빌드 입구 · 워크트리 수명주기 · 리라우트 복원)

| 항목 | 값 |
|---|---|
| 작성 | 2026-07-10 · Claude COO (워크플로우 실측 15에이전트 + Codex 감사 교차검증) |
| 대상 독자 | **Codex 개발자** — 이 문서만으로 P1~P3 개발 착수 가능하도록 작성 |
| 관측 HEAD | `dce5160d0` (main, origin/main `1367adb5f`보다 8커밋 ahead) |
| 근거 문서 | `AUDIT-build-entry-worktree-route-v2-0710.md` (Codex 감사 §0–11 + COO 교차검증 §12) · `master-work-queue-necessity-0709.md` §9.6 (축2 확정) |
| 성격 | COO support evidence. source truth·성공·품질·Movement 권위 아님 |
| 규율 | 모든 좌표는 0710 실측. **개발 착수 시 재확인하라 — dirty 트리가 착지되면 줄번호가 밀린다** |

---

## 0. 개발자 사용법 (읽는 순서)

```text
1) §1 현재 상태 스냅샷 — 지금 트리가 어떤 상태인지
2) §2 확정 사실 — 왜 이 수리가 필요한지 (전부 file:line 근거)
3) §3 작업 명세 WO-1~WO-4 — 무엇을 어떤 불변식으로 만들지 + RED→GREEN 프로브
4) §4 경계와 금지 — 하지 말 것
5) §5 수용 기준 — 끝났다고 판정하는 조건
부록 A — 좌표 총람
```

착수 전 필수: 이 문서의 주장을 믿지 말고 **핵심 좌표 몇 곳을 직접 열어 재확인**하라
(BRICK 규율: 실행 결과만 근거로 인정). 특히 driver.py finally 블록과
worktree_sandbox.py reaper는 이 문서의 척추다.

---

## 1. 현재 상태 스냅샷 (0710 실측)

### 1.1 dirty 트리 (main 체크아웃, 총 88 porcelain 엔트리)

| 그룹 | 규모 | 정체 | 처분 후보 |
|---|---|---|---|
| (a) brick_protocol/** | 11 M | **"Smith 0710 model-lane recast" 단일 유닛**: fable-5 기획 복귀(pm-lead), dev=gpt-5.6-sol xhigh. discipline·agent objects 2·casting·checker·profiles 4·registry가 상호 일관(체커 _REQUIRED_TEXT ↔ discipline 원문 일치 실측) | 앵커 후 recast 체커 green 확인 → 정식 착지. **커널문서와 절대 혼합 금지** |
| (b) project/deku/** | 5 M + 5 ?? (20파일 184K) | 별도 프로젝트 deku. **주의: project/deku는 tracked(457파일)라 blanket 커밋에 휩쓸림** | 브릭 착지에서 명시 제외 |
| (c) status/inbox deku-* | 63 ?? | deku 빌딩이 브릭 inbox에 쏜 이벤트. tracked inbox 657파일 중 deku 선례 **0** | 정책 결정 전 커밋 금지 (control-plane 오염) |
| (d) status/kernel | 2 M + 2 ?? | 0710 COO 판정(보드·큐 §9.6) + 핸드오프 0710b/c | 별도 커널 커밋 후보 |

### 1.2 워크트리 13개 · refs

```text
main 1 + /private/tmp 10 (reaper 사정권 밖 — 엔진루트 밖 + 마커 없음 이중게이트 실측)
  · dispo 9개: 전원 clean 또는 앵커/main 보전 — 유실물 0, 삭제 후보
  · n24 리뷰 1개: 앵커됨(55c2ab80e), main 미착지 → keep
~/.brick/worktrees 2 (reaper 사정권 안):
  · pure-dev-d3-body-v1-0709: dirty 2파일(+91/-6, OfficialLaunchProof 타입증명 하드닝 = #24 선행시도)
    → 보호앵커 완료 de524962b (byte-identical 실측)
  · deku-d2-real-conduct-0709: untracked 11파일 → 앵커 81068c09f (7/11 포함),
    잔여 4파일 = deku-home-real/sessions/ = .gitignore "sessions/" 매치 → 앵커 불가
    reap eligible: deku-d2 = 07-10T14:27Z(23:27 KST)~, body-v1 = 07-10T15:45Z~
refs: refs/brick/wip 357 (그중 80개=main 기도달=정리후보, 276=순수 앵커) ·
      refs/brick-salvage 23 (전부 미착지) · refs/brick/wip-backup 1(9b2c3b7d7)
stash@{0} "pre-c2-landing-...-20260708": 커널문서 204줄, 고유줄 137/146이 main 전체 부재,
      무태그 단일본 (stash@{1}–@{4}만 archive/stash/* 태그됨) → 태그 보존 후보
```

### 1.3 체커 상태 (Codex 실행 실측)

```text
GREEN: driver_public_intake_seal · graph_draft · brick verify --self-test · model-lane(focused)
RED:   building_operator_driver0 (onboard example ran!=True)
       graphdecl_fix (official token + manifest drift)
       resume_declaration (orphan-harvest pin drift)
       link_routing_behavioral / route_v2_sealed_materialization / route_v2_walker_advisory
         (전부 official launch token admission — WO-2의 대상)
       check_profile.py --all = RED (현 HEAD는 개발 체크아웃, release 불가 상태)
```

---

## 2. 확정 사실 (판정 + 근거 좌표)

### 2.1 워크트리 소실 메커니즘 — 경로별 최종 판정 (축2, 적대검증 7에이전트)

| # | 경로 | 판정 | 결정 근거 |
|---|---|---|---|
| 1 | driver worktree-run 미완 close | SAFE_IF_ANCHOR_SUCCEEDS | driver.py:1059-1081 중첩 finally: 가드(:1061-1065 `not commit_sha ∧ frontier≠"complete" ∧ not land_force_commit_absent`) → anchor_wip_snapshot :1066 → reclaim :1076-1079 → **inner finally :1080이 dispose :1081 무조건 실행** |
| 2 | run_building_plan park/stop | SAFE_ANCHORED | run.py:750 except park → _anchor_park_stop_wip :756-760(모듈 유일 호출처) → re-raise :761. 정상/adapter-hold close는 _with_close_wip_anchor :749/:767 |
| 3 | resume 재park | **LOSS_RISK** | run.py:773-862의 유일 except = AdapterFrontierEvidenceWritten :854. park 클래스는 :849/:1001로 스레딩되나 어디서도 안 잡힘 → :818-831 인자평가 중 전파 = :862 앵커 미실행 |
| 4 | 승인후 continuation (onboard approve) | **LOSS_RISK** | onboard.py:3982 resume_building_plan **직접 호출 = driver bracket 밖**. worktree는 :318에서 자동생성(engine-owned), **dispose 주체 전무**(전 코드 유일 dispose = driver.py:1081), 크래시는 :4061-4071 generic 삼킴(무앵커) |
| 5 | 24h stale reaper | **LOSS_RISK** | worktree_sandbox.py:148(모든 create 진입 시) → :430-461 루프(:449 `_engine_worktrees_root().iterdir()`= `~/.brick/worktrees`, :48-54) → :568-576 **marker 나이만 판정(liveness/PID/hold/dirty/WIP 무확인)** → :643-671 `git worktree remove --force` → 실패 시 rmtree. **앵커 시도 0줄. marker.repo_root와 호출 repo 대조 없음 = cross-repo reap 가능** |
| 6 | proposal-approval 첫발사(--forward) | SAFE (1번과 동일 표면) | onboard.py:2894 무조건 `_run_in_worktree_sandbox` 진입. 프로브A 실행증거(agent-return worktree_observation: detached HEAD·clean)로 "worktree 안 만듦" 관찰착시 정정. `action=stop`만 진짜 무-worktree(:2843-2851) |
| 7 | temp-dir 폴백 | LOSS_RISK_FOR_WRITES | driver.py:836-929: probe/create 실패 시 temp 실행, commit/anchor 없이 :929 cleanup. isolation_mode="temp_dir" 기록은 됨 |
| 8 | coo_gate_runner.sh:192 | 소형 LOSS | 앵커 없는 force-remove (게이트 scratch 한정) |
| 9 | wip ref 덮어쓰기 | UNCERTAIN | worktree_sandbox.py:276 update-ref 덮어쓰기 + _slug 충돌(:756-764, `:/._`→`-`) → 구커밋 고아화. 삭제 경로는 production에 없음(checker 전용). gc 타이밍 미실험 |

**앵커 자체의 맹점 4종** (worktree_sandbox.py anchor_wip_snapshot :226-278):
- clean 트리 → `""` 반환·무동작 (:246-247) — 정상.
- **gitignored-only 변경 = 앵커 무대상** (status --porcelain이 ignored 제외) → 무소음 소실. **라이브 실증: deku-d2의 sessions/ 4파일**.
- **서브모듈 dirty 바이트 미포착** (:254-259, gitlink만) — 앵커 ref가 보고되어도 바이트는 사라짐. 무소음.
- **sensitive-path 발견 시 raise** (:248-253) → 경로1의 inner finally가 그래도 dispose = **앵커 실패 후 파괴** (유소음이나 실손실).
- 추가 skip 경로: driver.py:1032-1034 (frontier=complete + commit raise + scoped dirt 없음 → 무앵커 re-raise 후 dispose, 유소음).

**P0-B — resume은 WIP를 복원하지 않는다** (Codex 발견, COO 확인):
`_prepare_resume_adapter_cwd`(onboard.py:286-338)에 wip ref 조회 **0줄** — 현재 HEAD probe로
새 worktree 생성(`create_worktree_sandbox(repo_root, building_id, base_sha=probe.base_sha)` :318).
즉 **evidence resume(frontier/원장 계속)은 있으나 workspace resume(바이트 계속)은 없음**.
WorktreeSandbox 객체를 버리고 path만 넘겨(:335 부근) 최초 실행의 close bracket도 재사용 불가.

### 2.2 실행 입구 실인벤토리

```text
공식 콘솔(brick = cli:main, pyproject.toml:22-23) — 15개 동사 중 실행동사 2개:
  build  (cli.py:1120/:1946) ┬ preset 모드 → run_customer_building_in_sandbox (cli.py:520)
                             └ --graph-decl 모드 → assemble→proposal persist→
                               run_goal_approve_entry (cli.py:598)
  resume (cli.py:1420/:2030) → resume_declaration.run_resume_declaration (:180)
                             → onboard.run_approve_entry (:525 경유)
  (+ init이 예제 빌딩을 실제 실행: cli.py:1517 → onboard.py:761,
     자체 어댑터 자동선택 _choose_example_adapter onboard.py:617)
  draft(:1251)=계획만·발사 seam 없음(cli.py:1182-1186) · draft-diff(:1374)=관측만

★제2 CLI (미봉인·프로덕션): python -m brick_protocol.support.operator.onboard
  main :4333 / __main__ :4584 · goal-approve :4345→:4392 (빌딩 시작)
  · approve :4407→:4469 — --reroute-target(:4435)/--re-instruction(:4441)로
    reroute disposition 전체 수용 · install.sh:62가 실사용
  · off-route 훅(.claude/hooks/pretooluse_block_offroute_launch.py:28)은 함수명 7개 +
    비-`-m` .py 정규식만 거부 — 이 입구는 deny=False (분류기 실행으로 실측)

Python-import 표면(콘솔 밖 실행 권위):
  driver __all__(:2548-2556): run_building_intake :386 ·
    run_customer_building_in_sandbox :667 · run_customer_graph_building_in_sandbox :741
    (CLI 미도달 — 유일 호출자 assembly.fire() :1374/:1435; raw-graph CLI 퇴역 cli.py:151-156)
    · run_declared_portfolio :1703 (**production 호출자 0 — 그런데 mcp_projection.py:337이
    COO startup 표면으로 광고**)
  run_composed_graph_intake :535 = internal seal (check_driver_public_intake_seal.py:23-24) ✅
  onboard: build_preset :2634 (어댑터 codex-local 하드코딩 :2290/:2736) · build :2703 ·
    run_goal_approve_entry :2769 · launch_assembled_building :2940("historical plumbing")
  auto_repair_replay.run_declared_auto_repair_replay_case :120 (production 호출자 0,
    mcp_projection.py:340 광고)
  coo_run_orchestration_packet (orchestration_packet.py:38, :124→run_building_plan :127,
    building_operation.py:199/:252 재수출, latent)
  run.py: run_building_once :329 · run_building_plan :676 · resume_building_plan :773 ·
    chat-session 동사 3종 :2522-2531
무인 트리거: repo 내 cron/daemon/CI schedule 없음 (release-gate.yaml은 pr/push만,
  체커 reap은 HOME 스왑 하 실행 check_building_operator_driver0.py:52-54/:2925).
  실 reaper 트리거 = build 발사(driver.py:940) + approve/resume(onboard.py:318/:3872) 뿐.
```

### 2.3 라우팅 어휘 — "충돌"이 아니라 설계된 3계층 (실측 판정)

```text
gate-policy (forward/hold/next/reroute, gate.py:21-23)
  = 기계의 선언 라우트표. 검증 plan_validation.py:1404-1476 ·
    런타임 gate_sequence.py:67-250 (all-next→암묵 forward :244-250) ·
    커널 hold :2183-2293 / reroute :2294-2395 (adopted_by="link-policy:gate-sequence")
disposition (raise/forward/stop/reroute, transition.py:10)
  = 멈춤 지점의 인간/COO 결정. 기록 onboard.py:3907-3920 · 메뉴 walker_resume.py:157/:189 ·
    런타임 분기 walker_kernel.py:2106(stop)/2120(forward)/2133-2152(reroute)/1474(raise)
  ★ reroute disposition은 GateSequenceDecision으로 "재작성"되어 게이트 reroute 엔진을 재사용
    — walker_kernel.py:2133-2137 주석 명시("second reroute engine 도입 안 함") = 단일 엔진
Movement (forward/reroute, movement.py)
  = 기록되는 Link 사실. 유일 런타임 분기 assembly.py:2197 (비-forward edge는 carry 미체인)
번역 사이트 T1–T7: assembly.py:2097-2159 · composition_gate_translation.py:91-120 ·
  gate_sequence.py:105-250 · walker_kernel.py:2183/:2294 · :2106-2152 ·
  claims_link.py:178-224/:712-753 · onboard.py:2288/:2806-2815(goal-approve=사전 seam)
추가 라우팅 다이얼(크리틱 발견): TRANSITION_CONCERN_KINDS 8종 + verification_gap=비리라우트
  (return_fact.py:10-25, 런타임 walker_transition_concern.py:186) ·
  ADOPTION_LITERALS binding/advisory (link/spec.py:260, walker_kernel.py:2494/:2569) ·
  closure_transition_target_policy (선언시만, composition_graph_validate.py:33-34/:386-436) ·
  EXPANSION_APPROVAL_HOLD_LITERALS (link/spec.py:268-272)
실결함은 2개뿐: link/README.md:28 "게이트가 Movement를 정한다" 오해문구(gate.py 독스트링과 모순) ·
  resume --decl의 reroute 미허용 (RESUME_DECL_ACTIONS=raise/forward/stop,
  resume_declaration.py:27; 거부 fixture check_resume_declaration.py:65-74)
```

### 2.4 리라우트/리플레이 — 현황과 갭 (8단계 E2E 실측)

```text
과거 완주 실증(n2): 0630 G1.2 "live_qa_reroute_to_work_n2 measured:
  fan-in QA concern → Link reroute → work replay → closure | narrowly_proven"
  (archive/0702-doc-archive/customer-ready-closeout-requirements-audit-0630.md)
  계보 커밋: ac84af40d(concern-hold mirror/replay) · d2758433c(brick resume --decl) ·
  d30517894(resume fuel honesty). ac84af40d 메시지가 앵커 생존 사례 자체를 기록
  ("worktree reaped ... work preserved and landed from WIP anchor 6a4191e2").

현재 살아있는 것:
  · 정책: link/route_policies/basic_qa_repair.yaml (implementation_gap→dev+QA replay ·
    design/upstream/boundary/insufficient→human gate · verification_gap→비리라우트)
  · run_approve_entry는 오늘도 action="reroute" 수용: reroute_target_ref :3589-3597 +
    re_instruction :3617-3625 → disposition row(pending_target_ref) :3903-3914
  · resume 의미론: 기록 FIFO 재생 + 홀드 지점에 disposition 적용 + forward walk 위임 —
    reroute 지점 이후 하류(QA·closure)는 라이브 재주행 (walker_resume.py:239-257/:340-341/:365-368)
  · 제약: reroute 타깃에 node_reroute_budget 선선언 필요, 없으면 HOLD (:308-333)
  ★ 리비전/확장 체인 (제자리 수리 경로, 크리틱 발견):
    write_declared_plan_revision(declaration_packets.py:287)이 홀드 빌딩에 repair 노드+budget을
    add-only 추가(승인증거 :691-757 · 확장예산 :774-780 · add-only :783-830 · 예산불변 :858-871)
    → resume이 최신 승인 리비전으로 재수화(walker_resume.py:1223) + 신규노드 budget 오버레이
    (:1246-1292→:326-332). 읽기측 = 모든 graph resume에서 live. 쓰기측 = checker 전용
    (check_plan_revision_chain.py). 진입 배관: composition_compose.py:756-766 · onboard.py:2712
  · route_replay_plan/replay_segment_refs: 선언 어휘로 실존·중검증(link/spec.py:302/:312,
    plan_validation.py:1555-1650, :1565 movement:reroute 전용)이나 disposition seam에서 표현 불가
    (파라미터·TRANSITION_LIFECYCLE_ALLOWED_KEYS 부재) — 소비처는 standalone
    auto_repair_replay(:120-155, 새 빌딩으로 실행, production 호출자 0)뿐
  · route_v2 = SHAPE A live advisory: walker_kernel.py:86-89 import · plan key :254-264 ·
    관측패킷 8사이트 emit · resume 재주입 walker_resume.py:317-323 · adopted_as_movement=False
    · shape_b_shared_helper(route_v2_views.py:79-98/:150)는 관측 공유만 — beyond-A 동결 유지
    (route-v2-beyond-a-smith-close-0709.md:14-21)

8단계 판정: S1 빌드✅ S2 QA concern✅ S3 closure✅ S6 land✅ /
  S4 reroute+replay 선언 PARTIAL(Python seam만, CLI 거부) ·
  S5 재주행 PARTIAL(budget 선선언 필요·CLI 입구 없음) ·
  S7 anchor-확인-후-dispose PARTIAL(fail-closed 아님 = WO-1) ·
  S8 kill/restart 동일 frontier PARTIAL(evidence는 됨, workspace는 안 됨 = WO-1)
```

### 2.5 복잡성 원장 — 자동선택 사이트 전수

```text
파이프라인 스테이지(실측): 0 공개입구 4개(§2.2) → 1 입력모드(--graph-decl 유무, 선언적) →
  2 어댑터 자동 → 3 프리셋 자동 → 4 intent 통일(onboard.py:2575, build-unify #12) →
  5a 프리셋 물질화 / 5b 그래프 조립 → 6 캐스팅 단일점 → 7 액션(기본 stop) →
  8 격리 자동(worktree/temp) → 9 워커(dynamic 고정, driver.py:494-498)

자동선택 사이트와 등급 (수렴 시 처분 판단 재료):
  [제거후보-히든디폴트] 프리셋 자동: task+write-capable→fast-fix, 그외→onboarding-example
    (cli.py:319-325, :113-114) — 업무 과중 판단이 아님. Smith 의도와 배치
  [제거후보-교리위반] onboard.build 어댑터 codex-local 하드코딩(onboard.py:2290/:2736)
    — materializer는 blank 어댑터 fail-closed(composition_intent.py:101-108)인데 상류가 우회
  [주의-드리프트원] readiness 의존 자동: --real-provider 첫-준비 어댑터(cli.py:373-402,
    순서 :105-110 claude→codex→gemini→grok) · 캐스팅 티어 사다리 첫-준비
    (plan_rendering.py:544-558, provider_registry.py:276/:345-405) · init 예제 어댑터
    (onboard.py:617) — 환경에 따라 결과가 달라지는 클래스
  [유지-편의] EASY-tier 자동: auto-id(assembly.py:526) · auto-returns(:505) ·
    auto-carry(:2161, load-bearing) · 선언 디폴트(adapter local :1085 · 모델 per adapter
    :1089-1094 · authority coo :1077) · building_id 해시(:2429-2442, composition_intent.py:562)
  [유지-안전] action 기본 stop(assembly.py:891-921) · 격리 자동(driver.py:803, W1 불변식) ·
    출력루트 모호성 fail-closed(driver.py:482-510) · 에이전트 자동은 단일후보만+모호 fail-closed
    (plan_rendering.py:948)
  [별채] graph_draft.py 1,678줄(brick draft): 8답→그래프 자동설계(_shape_nodes :674 191줄,
    deep-tier 승급 :1459-1463) — 자동발사 없음. authoring 내부 도구로 지위 정리 대상
  [잠재] 포트폴리오 자동채택 _resolve_next_adoption(driver.py:2105, 라이브러리 전용)
복잡성 누적 이력(대표 커밋): 9ea374ca7→cfffc07c3→f2ccd1622→…→15ccd10ac(토큰게이트)→
  da14f95f8(land-force) — 이전 경로를 흡수하지 않고 계층을 얹어온 누적이 원인
```

---

## 3. 작업 명세 (개발 발주)

> 순서: **WO-1과 WO-2 병행 → WO-3 → WO-4**. beyond-A는 WO-4 결과가 정책 RED일 때만 별도 승인으로.

### WO-1. 작업장 생애 소유권 — lifecycle fail-closed 상태기계 (#2)

**불변식 (이것이 전부다):**
```text
DISPOSE 허용 조건 =
  landed commit + 검증된 SHA
  OR 검증된 WIP ref + WIP commit SHA + durable recovery handle
  OR 인간/COO의 명시 discard 기록
이 셋 중 하나가 증명되기 전의 dispose/reap/cleanup = 버그
```

**구현 항목 (좌표는 §2.1):**
1. **anchor 실패 시 dispose 금지** — driver.py:1059-1081 재구성: anchor raise/실패 시
   worktree 잔존 + recovery handle 반환 + 오류는 전파(현행 유지). sensitive-path
   (worktree_sandbox.py:248-253)는 민감경로 제외 부분앵커 or fail-closed 잔존 중 택1 설계.
2. **anchor 맹점 처리** — gitignored-only 변경: 별도 durable 번들로 보존하거나 "미보존"을
   recovery handle에 명시 기록(무소음 금지). 서브모듈 dirty: 검출 시 fail-closed 잔존.
   driver.py:1032-1034 제3 skip 경로: 앵커 시도 추가.
3. **resume workspace 재수화 (P0-B)** — _prepare_resume_adapter_cwd(onboard.py:286-338):
   refs/brick/wip/<building_id> 존재 시 그 커밋을 base로 worktree 생성(현재 HEAD 아님).
   HEAD drift는 명시적 rebase/adoption 없이 혼합 금지. wip ref 부재 시에만 현행 로직.
4. **resume close bracket 통일** — onboard.py:3982의 bracket 밖 직호출 수리: resume도
   최초 실행과 동일한 commit/anchor/dispose bracket을 사용. run.py 두 resume 분기
   (:818-831 인자평가 / :854 단일 except)에 run.py:750-761의 park-앵커 미러 추가.
   onboard.py:4061-4071 generic 삼킴 전에 앵커 시도.
5. **resume worktree dispose 주체 신설** — 현재 전무. bracket 통일(항목4)로 자연 해소되는지
   확인하고, 아니면 명시 dispose+release 경로 추가.
6. **reaper 안전화** — worktree_sandbox.py:430-461/:568-576/:643-671:
   ①marker.repo_root ↔ 호출 repo 대조(불일치 = 건너뜀) ②liveness/lease 확인
   ③dirty면 last-chance anchor 1회 후 remove ④hold/frontier 상태 확인
   ⑤cross-repo rmtree 폴백 금지.
7. **temp-dir write 보존** — driver.py:836-929: write-capable provider의 temp 폴백 금지
   또는 cleanup 전 temp 바이트를 durable WIP 번들로 보존.
8. **WIP ref 수명주기** — land 후 release / hold 중 유지 / discard 후에만 해제.
   재발사 덮어쓰기(worktree_sandbox.py:276)는 구타깃 백업 ref 또는 세대 suffix로 무손실화
   (_slug 충돌 :756-764 포함).
9. **recovery_handle 공통 반환** — preset/graph/resume 패킷 모두
   `{ref, sha, base, resume_command}` 반환 (cli.py 패킷 lift 포함 — 현재 evidence_root/
   frontier_kind만 lift됨 cli.py:631-638, isolation 기본값 오표기 :656 함께 수정).

**RED→GREEN 프로브 (각각 먼저 RED로 재현 후 수리로 GREEN):**
```text
R1 anchor의 status/add/write-tree/commit-tree/update-ref 각 실패 지점에서 worktree 생존
R2 hold가 쓴 바이트가 resume cwd에 byte-identical 존재 (P0-B)
R3 main HEAD 전진 후에도 원 base/WIP에서 resume
R4 resume 중 park/일반예외 후 WIP·worktree 생존
R5 reaper: 타 repo marker 격리 · live(>24h) 빌딩 미reap · dirty 잔재는 anchor 후 remove
R6 temp 폴백 write 보존 or fail-closed 거부
R7 land 후 WIP ref release · 재발사 덮어쓰기 무손실(백업/세대)
R8 preset/graph/resume 경로의 recovery handle 동등성
R9 gitignored-only 변경의 명시 기록(무소음 소실 0) · 서브모듈 dirty fail-closed
```

### WO-2. L3-3b 공식 launch admission 수리 (#24)

```text
유지: lethal deny 자체 (비정식 walker 직호출 차단은 설계 의도)
수리: 정식 CLI(cli.py:2141-2157 mint_official_launch_token → driver.py:719 in-process →
     import_identity.py:278/290 enforce)와 정당한 internal/checker 호출자를
     정확한 checkout identity로 admit. suffix 기반 인정·잔존 nonce·하드코딩 provenance 우회 금지.
선행 검토: 보호앵커 de524962b (pure-dev-d3-body-v1 dirty: import_identity.py +68/-6 +
     check_import_identity_modes.py +29 = OfficialLaunchProof 타입증명 하드닝의 미완 선행시도)
     — 채택/폐기를 먼저 판단하고 시작하라. 중복 개발 금지.
수용: 현재 RED 5프로파일(building_operator_driver0 · graphdecl_fix · link_routing_behavioral ·
     route_v2_sealed_materialization · route_v2_walker_advisory) 재실행 green
     + 비정식 진입은 여전히 deny(RED 프로브 유지).
```

### WO-3. 입구 수렴 — 이름이 아니라 권위를 하나로

> ★0710 오후 확정 스펙 = `DESIGN-order-chain-casting-vocabulary-0710.md` — 캐스팅 규칙(환경 선택
> 금지)·발주빌딩 체인(검수 1회 접이식, lowering을 빌딩 안 기계 스텝으로)·어휘 봉인(운영 v1
> 스냅샷 + 개정=승인 행위)이 그 문서에 조항·수용기준·미결까지 정리됨. 아래 항목들과 함께 읽되
> 충돌 시 DESIGN 문서가 우선.

```text
최종 계약:
  brick build <task> → intake/triage → {A. direct_preset (quick_check/quick_fix +
    fast_confirm + 명시 확정만) | B. authoring_building (그 외 전부: Building Call authoring
    → COO confirm → canonical lowering)} → 단일 declared-plan dispatch → 단일 sandbox lifecycle
  brick resume = 유일 continuation (disposition: forward/stop/raise/reroute+target+re_instruction)
  pause는 Movement가 아니다 (현행 MOVEMENT-BINARY-0 유지 — 이미 코드가 그렇게 되어 있음)

항목:
1. ★onboard 모듈 CLI 봉인 — __main__(:4584)/main(:4333) 제거 또는 brick 콘솔로 위임.
   install.sh:62 갱신. off-route 훅 deny 패턴에 `-m ...onboard` 계열 추가.
2. resume --decl에 reroute 어휘 추가 — RESUME_DECL_ACTIONS(resume_declaration.py:27)에
   reroute+reroute_target_ref+re_instruction 확장, 거부 fixture(check_resume_declaration.py:65-74)
   를 수용 fixture로 갱신. (run_approve_entry는 이미 받는다 — CLI 표면만 갭)
3. 프리셋 히든 디폴트 제거 — cli.py:319-325: 명시 --preset 요구 or advisory ranker
   (building_design_toolkit.py:334-358, auto-select 금지 자기선언 유지) 제안+확인 흐름.
4. onboard.build 어댑터 하드코딩 제거 — onboard.py:2290/:2736 → 명시 선언 요구
   (materializer 교리 composition_intent.py:101-108와 정렬).
5. 광고-무호출 표면 정돈 — mcp_projection.py:335-341 startup_surface_refs에서
   run_declared_portfolio·run_declared_auto_repair_replay_case 제외(또는 internal 명기).
   launch_assembled_building·fire()·coo_run_orchestration_packet = Builder 내부 재료로 표기 통일.
6. graph-draft/graph-decl 지위 — 급퇴역 금지. draft는 authoring Building 내부 도구로,
   --graph-decl은 canonical authoring 산출물의 호환 transport로 문서/스킬 정리.
7. link/README.md:28 오해 문구 수정 (게이트는 충분성 관측, Movement는 Link 소유).
8. portfolio·repair/replay = 별도 입구가 아니라 declared plan kind로 취급.
9. (0710 시퀀스 추적 추가) **프리셋 레인에 검토 정거장 부재 해소** — 현재 preset 흐름은
   엔터→첫 브릭이 단일 동기 콜체인(검토 pause 0, COO 사전 가시물 = repo_root 한 줄뿐,
   캐스팅표는 런 종료 후에야 출력 cli.py:1135-1139). 발주서 레인과 동일한
   stop(proposal+캐스팅표 검수)→명시 forward 이중열쇠를 주거나, 프리셋 레인을
   quick_check/quick_fix 전용으로 강등(WO-3 최종계약 A분기와 정렬).
10. (추가) 어댑터 자동선택 fail-open → 명시화 — --real-provider 전 프로바이더 미준비 시
    adapter:local 조용 폴백(cli.py:395-402) + 그로 인해 프리셋이 fast-fix→
    onboarding-example-graph로 **루트째 조용히 뒤바뀜**(cli.py:319-325 결합, 검증 CONFIRMED).
    폴백 시 fail-closed 거부 or 명시 확인 요구로.
11. (추가) 타임아웃 비대칭 해소 — preset 레인은 --timeout 기본 120초가 실작업에 조용히
    적용(cli.py:1945→driver.py:675), draft 레인은 deep이면 10800 자동 상향(graph_draft.py:1520-1529).
12. (추가) gates:["human-review"] 자동배치가 final_transition 전용임을 표면화 —
    중간 검토는 노드에 수동 배치해야 하며, 누락 시 hold ledger 없이 종결→resume 불가
    dead-end(resume_declaration.py:50-55). 최소한 발사 전 경고 or 중간 게이트 선언 지원.
13. (추가) stop→forward 재발사 마찰 — proposal 기존재로 FileExistsError→--overwrite-existing
    강제(프로브A에서도 걸림). 검토 후 forward가 자연스러운 기본 동선이 되도록 수리.
수용: 실행 입구 = brick build/resume(+init 예제 명시) 뿐임을 훅+seal+체커로 강제,
     driver_public_intake_seal green 유지, 신규 seal 체커(onboard __main__ 부재) green.
```

### WO-4. n2 리라우트 복원 증명 (E2E)

```text
동결: Movement forward|reroute · 기존 concern kinds · basic_qa_repair.yaml (신규 분류 금지)
1. n2 trace 재실행 (현 CLI · WO-1/2 완료 후):
   implementation_gap → reroute work → work attempt 2 → QA sibling replay/fan-in →
   closure complete. 사례 플랜에 node_reroute_budget 명시 선언(부재 시 HOLD가 정상임을 확인).
2. write-byte continuity fixture:
   write → hold → 프로세스 kill → resume → 원 WIP 바이트 유지 → complete +
   main-adoptable commit → dispose + WIP release. (WO-1 R2/R4의 E2E 봉인)
3. route_replay_plan의 disposition seam 표현 — 리비전/확장 체인(§2.4)을 공식 쓰기 경로로
   승격하는 것과 신규 파라미터 추가 중 설계 선택 1건 (Smith/COO 확인 후 진행).
4. SHAPE B helper 상태원장 정합 — observation-only 승인 슬라이스로 명기 or SHAPE A 표기 회귀.
수용: 위 1·2가 현 공식 CLI에서 green + 그 증거로 queue §9.2/보드 "정식 build 안전" 최종 갱신.
beyond-A: 여기까지 하고도 정책 행동 부족 RED가 나올 때만, 새 design Building + Smith 승인.
```

---

## 4. 경계와 금지

```text
- deku 분리: project/deku/**는 tracked임 — brick 커밋에 절대 혼입 금지.
  inbox의 deku-* 63개는 정책 결정 전 커밋 금지 (tracked inbox에 deku 선례 0).
- 삭제 금지: worktree·WIP ref·salvage ref·stash blind delete 금지. 정리는 §1.2의
  실측 목록 기반으로 Smith 승인 후 별건. (wip 80개 기착지분 포함)
- model-lane recast 11파일(§1.1a)은 이 발주와 무관한 선행 유닛 — 건드리지 말 것.
  착지도 별도 커밋으로.
- checker green ≠ DONE. frontier complete ≠ 제품 성공. delta-green 착지법 적용
  (baseline 대비 새 RED 0 — 현재 --all RED이므로 "전체 green"이 아니라 "새 RED 0"이 기준).
- MOVEMENT-BINARY-0 유지. 새 route-target 분류·복수 concern 일반화·부분 QA 재사용·
  fan-in 조합 일반화·beyond-A 전면 재설계 = 이번 범위 밖.
- 커밋·push는 Smith 지시로만.
```

## 5. 수용 기준 총괄 (이 발주의 Exit)

```text
E1 WO-1 프로브 R1–R9 전부: 수리 전 RED 재현 기록 + 수리 후 GREEN
E2 WO-2: RED 5프로파일 green + 비정식 진입 deny 유지 프로브
E3 WO-3: 입구 계약 체커(신규 포함) green + 히든디폴트/하드코딩 제거 diff
E4 WO-4: n2 E2E green + write-byte continuity green (증거 root 경로 제출)
E5 delta-green: check_profile --all에서 baseline(이 문서 §1.3) 대비 새 RED 0
E6 정직 반환: 각 WO의 remaining_not_proven 목록 명시 (없으면 "없음"을 증명으로)
```

---

## 부록 A. 좌표 총람

```text
lifecycle : driver.py 803-1081 (finally 1059-1081 · guard 1061-1065 · dispose 1081 ·
            temp 836-929 · skip 1032-1034 · walker모드 고정 494-498)
            worktree_sandbox.py 48-54(엔진루트) 64-65(마커·24h) 129-173(create+reap)
            196-223(commit) 226-278(anchor: clean 246-247 · sensitive 248-253 · 서브모듈 254-259)
            276(ref 덮어쓰기) 281-341(worktree anchor) 366(reclaim) 430-461(reap 루프)
            568-582(stale 판정·마커 게이트) 643-671(force-remove·rmtree) 756-764(_slug)
            run.py 564-672(close/park anchor) 728-767(build close) 773-862(resume) 1001·849(park 스레딩)
            onboard.py 286-338(resume cwd 준비·318 create) 2769-2934(goal-approve·2894 bracket·
            2912 ok판정·2916-2924 결과필드) 3516-4077(approve·3982 직호출·3903-3914 disposition·
            4061-4071 삼킴)
입구      : pyproject.toml 22-23 · cli.py 105-114(디폴트) 151-156(퇴역) 319-331(프리셋/스코프 자동)
            373-437(어댑터 자동) 509-627(build 본체) 631-656(패킷 lift·오표기) 1120-1517(cmd들)
            1833-2157(파서·토큰 mint 2141-2157)
            onboard.py 617(예제 어댑터) 2290/2736(하드코딩) 2634/2703/2940(수출) 4333-4584(제2 CLI)
            driver.py 386/535/667/741/1703/2105/2548-2556 · assembly.py 1374-1444(fire)
            auto_repair_replay.py 120-155 · orchestration_packet.py 38/124-127
            mcp_projection.py 335-341/492-530 · .claude/hooks/pretooluse_block_offroute_launch.py 28
어휘/라우팅: movement.py · transition.py 10/20-45 · gate.py 21-23/62-75 · link/README.md 28
            plan_validation.py 389-476/1156-1203/1404-1476/1555-1650
            gate_sequence.py 67-260 · walker_kernel.py 1474/2106-2395/2494/2569/86-89/254-264
            walker_resume.py 157-189/239-368/1223/1246-1292 · walker_reroute_budget.py 153-167
            walker_transition_concern.py 186/209/331-366 · return_fact.py 10-25 · link/spec.py 260-272/302-312
            resume_declaration.py 27/180/525 · route_materialization.py 169/323/337
            claims_link.py 146-224/676-753 · route_v2_views.py 1-8/79-98/150
            declaration_packets.py 88/287/691-871/1502 · composition_compose.py 756-766/1171-1194
authoring : composition_intent.py 70-187/101-108/562/784-817 · assembly.py 505-526/576/824-921/
            1039-1094/2097-2161/2197/2375-2442 · plan_rendering.py 376-599/948
            graph_draft.py 674/1459-1463 · building_call.py 24-35/126-274
            building_design_toolkit.py 334-358 · provider_registry.py 162/276/345-405
증거/이력  : queue §9.6(축2 정본) · AUDIT-...-route-v2-0710.md §0-12 ·
            archive 0630/0701 n2 문서들 · 커밋 ac84af40d/d2758433c/d30517894/15ccd10ac/da14f95f8
            보호앵커: de524962b(#24 선행시도) · 81068c09f(deku-d2) · 9b2c3b7d7(백업)
```

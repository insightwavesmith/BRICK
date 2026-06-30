# Customer-Ready BRICK — fan-in route / Link-track plan (Smith 확정 0629)

Status: support evidence only / operator plan. Smith가 코드 직접 재확인 + 두 조사 에이전트가 놓친 결정적 사실 1개를 찾아 확정한 기획. 골 임계경로(P3→P5→P7→P8) 밖의 병렬 Link 트랙.

## 핵심 정정 (Smith 코드 확인 — 두 에이전트가 놓침)
- **cascade replay = 미구현 아님. 선언 표면이 이미 있다.** `link/route_policies/basic_qa_repair.yaml`:
  - `design_gap → {target_step: design, replay_steps: [work, qa], human_gate_required: true}`
  - `implementation_gap → {target_step: dev, replay_steps: [qa]}`
  - AUTO-REPAIR-REPLAY-0 + ROUTE-MATCH-AND-MATERIALIZATION-0 경계에 묶임.
  - → **L2 = "cascade 새로 만들기"가 아니라 "선언된 replay_steps가 fan-in(병렬) 경로서 실제 walk되나 측정/수리"**. 범위 훨씬 작다.
- **design_gap = 이미 human_gate(HOLD-for-human) 정책** (자동 budget 아님, 사람 승인). AGENTS.md human-gate MUST-HALT와 정렬. → "디자인 틀림은 사람으로" 직관이 이미 코드.
- **budget = per-node(`_node_reroute_budgets`) + cascade 재진입은 `(step_ref, cascade_depth)` 튜플로 구별 추적** → 같은 노드도 깊이 다르면 다른 점유, per-node budget이 막음. 무한루프 막힘이 코드 구조로 뒷받침.

## 0630 LIVE 재측정 정정 (main ca79c12)
- **#1 fluent fan-in 거부 · #3 reroute redo carry 크래시 = 더 이상 재현 안 됨 (main 기준).** `building-operator-driver0` 프로파일의 `live_qa_reroute_to_work_n2`가 통과: 실 fan-in 그래프에서 code-attack-qa가 implementation_gap concern 발화 → default-transition 채택 → walker가 work 2회차 기록 후 closure. walker_kernel.py:525는 이제 구조화된 `_build_fan_in_wait_all_hold`(cascade_depth 추적)라 0629의 line:525 크래시 참조는 STALE.
- 따라서 G1 잔여는 **엔진 수리 아님 → no-link DEFAULT 정책 + 고객 docs/skills**다. 증거: `customer-ready-closeout-g1g2g3-status-0630.md`.

## 상태 4단
- **CONFIRMED (코드/yaml 직접 확인):** forward 생략 · 단일 reroute · related_boundary_refs 주소 resolve · ambiguous→HOLD · garbage→HOLD(unresolvable_reroute_address) · self-reroute strip · verification_gap→non-reroute · concern_kind→route_scope 매핑(yaml) · per-node budget · design_gap→human_gate · replay_steps 선언.
- **수리 중:** #1 fluent fan-in 거부 (커밋 4e335bf Lane2 착수) · #3 reroute redo carry 크래시 (walker_kernel.py:525). [지금 fix-building 검증 중]
- **측정 필요:** 선언된 replay_steps가 fan-in 경로서 실제 walk되나 (= L2 Step0).
- **금지 (admission 대상):** 새 문법(lane()/retry_lane()/dict route) · early abort · dependency-cone 가드.

## 케이스 매트릭스 (live 상태)
| 케이스 | 처리 | live |
|---|---|---|
| 전부 성공 | gather 통합 → forward | ✅ |
| dev 자기 구현 문제 | impl_gap → 그 dev, replay [qa] | ✅선언 / fan-in 실행=L2 |
| dev가 상위 디자인(D3) 지목 | design_gap → design, human gate, replay [work,qa] | ✅선언 / 실행=L2 |
| dev가 설계모음 지목 | design_gap + ref=설계모음 → 설계모음 | ✅ resolve 있음 |
| 여러 dev 같은 주소 | single | ✅ |
| 여러 dev 다른 주소 | ambiguous → HOLD | ✅ |
| ref 없음/declared 밖/garbage | HOLD | ✅ |
| verification_gap / unknown | non-reroute / HOLD | ✅ |
| branch 무반환 | route 아님 → frontier/HOLD | ✅ |
| budget 소진 | HOLD (forward 아님) | ✅ |
| upstream reroute 후 downstream | replay_steps 선언대로 재실행 | ⚠️ L2 측정 |
| early abort | 금지 (의도적 wait-all) | ✅ |

(dependency-cone 가드 = Agent2 직관 좋으나 지금 금지 — `_classify_reroute_target`은 declared면 resolve만, cone 안 봄. cone 추가=checker-first admission. ambiguous/garbage→HOLD로 충분. 과설계 방지.)

## 3 트랙 (확정)
**P3 (지금·임계경로·linear):** output_root 자동 — 남은 지뢰 1개, dev에 던질 유일 작업. DoD: output_root 미기재로 durable evidence root 자동생성 · linear frontier=complete · 수동 worktree/dict/path/adapter_cwd 0. **P3 제외: fan-in route·replay 실행·새 문법.** → 닫고 P5.

**L1 (P8 전 필수·병렬):** #1 fluent fan-in 거부 해제 (원인=assemble이 fan-in 소스에 required_return_shape 자동주입 → 고객가드가 고객입력 오인 거부; 경계=엔진파생 vs 고객선언) + #3 reroute redo carry 크래시(walker_kernel:525, ⚠️안전장치=P8 전 필수). DoD: fan([a,b,c])→gather route 고객루트 통과 · single ref · reroute 착지 · redo carry 크래시 0 · ambiguous/garbage/budget→HOLD · checker negative probe. **주의: 주소-인지 route 새로 만들지 마라 — 이미 있다, 기존 vocab만 고친다.**

**L2 (P8 밖·나중):** replay 실행 검증 (새 기능 아님). Step0=측정 먼저(선언 replay_steps가 fan-in서 walk?). design_gap reroute시 work+qa fan stale→재실행(human gate 경유) · 각 sibling 새 evidence(F1 cross-vouch 금지 유지) · budget cascade 재진입 유지((step_ref,cascade_depth) 추적). 기본=보수적(정밀 dep X, downstream 전체 재실행).

임계경로 P3→P5→P7→P8 (P8=task 1개=linear 충분). L1=P8 전 합류(특히 #3) · L2=P8 후 무방.

## 운영 원칙 (7)
1. forward 생략(기본). route = 모음에 `reroute()`/`hold()` 한 줄 또는 yaml 정책.
2. Agent = concern_kind + related_boundary_refs 증거만. Link = Movement. Support = 기록.
3. 원인 boundary 직행(2-hop 아님). 모음 = 재판소 아닌 집계/재계산 지점.
4. 모호/충돌/무반환/budget소진 = HOLD. design_gap = human gate(이미 정책).
5. 되돌림 대상 = ref 문자열 지명. `back(N)` 금지(fan 브랜치 못 집음).
6. cascade = upstream 바뀌면 그 sub-fan 전부 재실행(보수적). 정밀 dep는 후순위.
7. 새 문법/early abort/cone 가드 = 지금 금지(admission 대상).

## 불확실성 플래그 (정직)
- NOT CONFIRMED: 선언 replay_steps가 fan-in서 실제 walk되나(L2 Step0) · budget이 cascade 재진입서 유지/리셋(추적 구조는 있음, 실동작 미측정).
- SUSPECTED: #1이 커밋 4e335bf로 수리 진행중 — 완료/검증 미확인(지금 fix-building 검증 중).

# 빌딩 그래프 사고법 v2 — 설계 듀오 투입용 브리프

작성 0706 야간 원장 기준. 소비자 = 3개 독립 설계 레인(fable5, fugu/sakana, codex). 각 레인은 BRICK 오퍼레이터의 **그래프-저작 사고법**을 재설계한다: 일을 3축 — **공간**(팬 폭/파티셔닝) · **시간**(순서·단계·홀드·적응 확장) · **권위**(캐스팅 티어·게이트·QA 렌즈 깊이) — 으로 갈라 빌딩 그래프로 조각하는 방법. 여기에 **순서 사고**(2-페이즈 적응 디스패치: 설계-우선 + 홀드, 이후 설계의 파티션 판정에 따라 나머지를 expand()로 전개)를 더한다.

원칙: 이 브리프는 **입력이 실측한 것만** 나른다. 측정되지 않은 것은 전부 "미해결/미검증"으로 표시하며, 설계 레인이 답을 채운다. §1의 file:line 앵커는 설계 레인이 엔진을 직접 항해하도록 그대로 보존한다.

---

## 1. 표면 표현력 실측 (엔진이 오늘 표현 가능한 것 — Input 1)

이 절은 v2 사고법이 가정할 수 있는 것의 상한이다. 아래 "Hard limits"와 "Unverified combinations"를 넘어서는 방법은 오늘 발사 불가 — 설계는 이 경계 안에서만 선언 표면을 짜야 한다.

### 1.1 프리미티브 (assembly.py)
- `chain()` :247 / `edge()` :312 / `fan_out()` :256 / `fan_in()` :270 (모든 source는 `returns=` 선언 필수; self-reroute 금지) / `converge()` :318 / `build()` :573 (최종 팬 불가; AUTO-ID/RETURNS/CARRY 처리) / `fan()` :458 (branch는 fan 블록이 아님; branch에 `route=` 금지) / `reroute()` :783 / `hold()` :800 / `back()` :397 / `assemble()` :1110 (terminal은 non-None 필수; 게이트 human-review/coo-review/strict-evidence) / `expand()` :1208 (append-only dry-run, **절대 영속/실행 안 됨**) / `assemble_graph_declaration()` :841 (기본 action=stop) / `fire()` :1328

### 1.2 노드별 옵션 (assembly.py:365-369, 943-995)
`effort→reasoning_effort`, `adapter/adapter_ref`, `model/model_ref`, `source_facts`, `node_write_scope/write_scope`(템플릿 write_need 필요, 그래프 scope의 부분집합), `gates`(노드엔 human-review/coo-review만; brick 게이트 노드는 나가는 엣지 정확히 1개 :2037), `route`(reroute/hold 마크는 **수렴 노드에만** :463), `returns`, `alias/label`, `write(bool)`.

### 1.3 팬 3법칙
1. source N 뒤 fan-out → N개의 N→branch 엣지
2. `fan()` 직후 반드시 수렴 노드
3. `sibling_independence`는 known-parallel branch를 표시 (:737)

제약: `fan()`은 build 첫 항목이 fan이 아닌 한 첫 자리 불가; 마지막 자리 불가 (:593); 수렴 노드 필수 후행 (:642); 모든 branch는 `returns=` 선언 또는 템플릿 상속 (:506); `route=`는 수렴 노드에만 (:463).

### 1.4 write_scope 2법칙
1. **AUTO-CARRY**: 상류 step_output을 하류 source_fact로 선언 — 단 fan_in 타깃/이미-carry됨/non-forward는 제외 (:2140)
2. 노드 allowed_paths는 그래프 allowed의 증명된 부분집합이어야 하고, 그래프 forbidden을 보존해야 함 (:2451)

### 1.5 게이트 로워링
`stamp_profile_gates` :1731 (QA 행에 strict-evidence, 최종 전이에 human/coo); `node.gates` :2034 (human/coo만, 나가는 엣지 정확히 1개); brick 게이트 → `node_reroute_budget=1` :2948. `RerouteMark(on,to,budget)` / `HoldMark(on)`는 수렴 노드의 `closure_transition_target_policy`로 구현됨 :1776; 타깃은 존재+budget 있어야 함 :2340; hold는 target_ref를 carry하면 안 됨 :2330.

### 1.6 검증된 합법 조합
build() 중첩 fan; 동일 수렴 노드에 다중 reroute/hold; build() 내 위치 기반 `back(N)`; node.gates + 수렴 route (분리); **held plan 위 expand()** (append-only dry-run, :1208); expand()+attach_to_step_ref (roots만); write_need 노드 위 write_scope; sibling_independence 주석; AUTO-CARRY가 fan_in 타깃 건너뜀.

### 1.7 미검증 조합 (합법으로 보이나 증명 안 됨 — **설계에서 반드시 표시**)
- expand()+reroute를 fan-in으로 되돌리기
- hold()-then-forward-override를 resume-decl 라운드 간 교차
- 내부 fan branch에서 expand() (roots만 인정됨)
- non-final 엣지 위 node gates
- 중첩 fan()
- reroute budget vs node.gates budget 충돌
- **HELD 수렴 노드를 가진 plan 위 expand()** (append-only 검증에서 hold 상태가 re-route를 막음 — **미검증**)

### 1.8 Hard limits (오늘 표현 불가 — 어떤 v2 방법도 넘을 수 없음)
1. build()에 multi-sink 수렴 불가
2. fan-out source에 hold 불가 — route는 fan-in 전용
3. 재귀 fan 중첩 불가
4. 빌더에서 명시적 backward/lateral per-edge 이동 불가 (forward만)
5. 빌더에서 non-completion 내부 엣지에 게이트 불가
6. conditional/concern-independent reroute 불가 — route는 concern-keyed
7. 중첩 write_scope 계층 불가
8. build()에서 동적/템플릿 기반 fan size 불가 — 명시적 branch 리스트 필수 (선언은 프리셋 처리 :841, build()는 아님)
9. 빌더에서 final 외 per-node 게이트 불가
10. 혼합 expansion budget 불가 (per-node **또는** aggregate, 둘 다 아님)
11. build() 내부에 "defer to resume-decl" 메커니즘 없음 — resume은 onboard-tier
12. source_facts carry FIELD 필터링 없음 — build 티어에선 all-or-nothing
13. sibling_independence는 advisory이지 ordering 아님
14. per-node timeout 없음 — graph/preset 전역
15. builder-level 커스텀 증명 의무 없음 — brick spec에 사전 선언

### 1.9 드래프터 / Resume 선언기 (참고)
- 드래프터(graph_draft.py): `draft_graph_declaration` :513, `_shape_nodes` :383 (deep-design/work/QA fan/closure emission), `_normalize_write_scope` :269, `_verify_source_facts` :309, `_scaffold_work_statement` :352
- Resume 선언기(resume_declaration.py): `validate` :77, `preflight` :303, `run_resume_declaration` :143 (single/until-terminal chain)

---

## 2. 야간 실측 교훈 (lens-corpus)

### 2.1 라운드-원인 분류 (무엇이 각 라운드/사망을 만들었나)
- **work deviation** (work brain이 얽힌 표면에서 낸 이탈): graphdecl-fix R1(round-1 doc artifact), resume-decl R1–R4(얕은 이탈이나 여전히 발생), r9-modellane R1(paraphrase-adjacent gaps).
- **design blind spot** (설계 레인 부재로 표면화 못 한 매핑 누락): graphdecl-fix R2/R3 — 미매핑 table-17 캐스팅 lattice; 설계 레인이 없어 각 티어 누출을 라운드로만 발견.
- **convergence tail** (앞 라운드 구조적 누출의 수렴 꼬리): graphdecl-fix R4–R5 — "cheap work brain on an entangled surface repays its savings in QA repair rounds."
- **meta-verification loop** (선언된 DONE 라인 밖의 재검증 루프): graphdecl-fix R6(DECLINED, 계약-DONE-라인 규율로 정지), r2-carry ledger(4 forwards cycled holds — receipts-tail 규율로 park).
- **environment** (콘텐츠 아님, 대부분 사망의 지배 원인):
  - throttle: resume-decl R5, cpath 0706c R2, selflock attack-QA, fugupacket 최종 QA — 밤 후반 fable5 xhigh 동시 3레인 → rc=1 연쇄(직후 pong 정상 = 일시 스로틀).
  - timeout: build-unify / friction-bundle의 fugu work가 3600s에서 사망 — **operator dispatch-parameter fault, 콘텐츠 아님**.
  - provider 451: cpath 0706a/b 두 레인이 Sakana 451 content filter(fugu wire packet)로 사망, R3 부재로 레인이 **조용히 동결**(Case 9).

**throttle 근본 측정(0706 야간 원장):** "fable5 xhigh 공격QA 동시 3레인 → 밤 후반 rc=1 연쇄. 교정 규율 = fable5 QA 동시 1~2레인 시차 발주."

### 2.2 1-라운드 승자 공통점 (winners: r2-carry, graph-draft #15, selflock, t10rev1)
1. **얽힌 표면엔 강한 work brain.** 3개 코드 승자 전부 fugu work 캐스팅; 5-라운드 walk 둘 다 codex work. 독트린: "work brain이 라운드 수를 지배; deep-design은 라운드 QUALITY와 QA 정밀도를 올리고 fugu와 짝지어 killer combo."
2. **일 시작 전에 결정을 닫음.** graph-draft: deep-design(fable5)이 모든 열린 결정을 닫음 → fugu가 1,163줄을 ONE round에 빌드. work 레인은 열린 질문이 아니라 **transcription-narrow plan**을 받음.
3. **사전 측정 좌표 / 사전 진단된 결함 클래스.** work 레인 안에서 in-flight discovery 없음.
4. **의도적으로 비충돌인 write scope.** selflock은 walker_kernel 무접촉으로 R2와 비충돌; t10rev1은 read-only census + 2 ledger docs.
5. **QA 이중화가 환경 사망을 흡수.** attack-QA가 throttle로 죽어도(selflock) EI가 완료 + COO 게이트 mutation-RED가 판정을 나름 — 판정 경로가 단일 fable5 레인에 의존하지 않으면 환경 사망이 0 라운드 추가.
6. **번호 매긴 산출물 + 사전 명시 mutation 설계**로 게이트에 실행 가능한 계약 부여.

### 2.3 모양 교훈 (shape lessons)
1. **캐스팅이 라운드-수 레버 — 설계 깊이가 아니라.** (no-design+codex)=5R, (deep-design+codex)=여전히 5R, (deep-design+fugu)=1R. 난이도-비례 캐스팅(얽힘/walker-adjacent → fugu work)이 5R walk들의 누출 라운드를 build-time 정확성으로 전환. 이제 graph-draft 룰 체커가 REDs: walker-adjacent 답에 codex-only work 레인을 draft하면 RED.
2. **deep-design은 어차피 살 가치 있음 — 라운드 QUALITY 때문에.** QA 거부를 cross-profile whack-a-mole에서 named/numbered deviation("deviation #13 caught by name")으로 전환. 값싼 brain을 정당화하지 말고 강한 brain과 짝지어라.
3. **deep 레인은 timeout을 선언 시점에 올려라 — 사망 시점에 발견 말고.** 두 3600s fugu 사망 전부 dispatch-parameter fault. 해법: deep-lane timeout auto-raise(10800s) + auto WIP anchoring(table 13) + attach-QA-at-anchor 게이트 복구 → 두 사망 모두 0 re-implementation 비용.
4. **fable5 QA 팬 폭은 throttle envelope을 존중해야.** 동시 3 fable5 xhigh attack-QA가 직렬로 사망. 해법: 1–2 시차 fable5 QA 레인 + 두 번째 판정 경로(EI lens + 게이트 mutation-RED)로 throttle 사망이 라운드를 소비하지 않게.
5. **Provider 생존성은 discovery가 아니라 pre-flight.** cpath가 아무도 보기 전에 두 dispatch를 Sakana 451에 잃음. 해법 쌍: fan 발사 전 환경 probe(fugu-fieldprobe) + receipt-no-response에 R3 loud-HOLD로 죽은 레인이 얼어붙지 않고 비명 지르게.
6. **DONE 라인과 residual-handoff 행을 그래프에 선언.** graphdecl-fix의 6번째 라운드는 오퍼레이터 규율로만 정지됨; scope 사전 선언 + 일반 lattice를 build-unify에 명시적 인계 = residual owner를 이름 붙인 그래프는 meta-verification으로 reroute 불가.
7. **구성을 사전 검증해 pre-dispatch 사망 클래스를 제거.** model:default hard-injection과 lint 거부가 work 전에 dispatch를 죽임; COMPOSED-OK 필수 사전 검증 + source_facts 존재 사전 체크 + L1/L4 scaffold가 그 클래스 전체를 draft time으로 이동.

---

## 3. 외부 패턴 카탈로그 (orchestration + decomposition 병합)

각 패턴에 "BRICK 적용" — §1 프리미티브에 묶는 한 줄. 결정 이론(CPM/Amdahl/USL/Conway/batch)은 폭·순서 다이얼의 근거이므로 패턴과 함께 나열한다.

### 3.1 오케스트레이션 패턴
1. **Plan-then-execute (정적 상류 계획).** 계획이 side effect 전에 검사됨. 승리: 알려진 하위작업 + 안정 의존; 낭비: 환경이 계획 아래에서 변함. — **BRICK 적용:** deep-design 레인이 결정을 닫고(§2.2-2) work가 transcription-narrow plan을 받는 정확한 형태. build() 위 deep-design→work chain.
2. **Interleaved plan-act (ReAct).** 매 관찰이 다음 결정에 피드. 승리: 미지/적대 환경, 짧은 horizon; 낭비: 긴 예측 가능 궤적(토큰 폭발). — **BRICK 적용:** build()의 forward-only 모델(Hard limit 4)은 ReAct를 표현 못 함; 탐색이 필요하면 §3.2-7대로 scout 레인을 먼저 sequence.
3. **Compiled parallel DAG (ReWOO/LLMCompiler).** 출력은 미지여도 엣지는 사전 명명; placeholder 변수로 데이터 흐름 상징화. — **BRICK 적용:** fan_out(:256)+returns 선언 + AUTO-CARRY(:2140)가 이 "엣지는 알되 출력은 미지" 형태. 단, branch structure가 결과에 의존하면(Hard limit 8) build()로는 불가.
4. **Scatter-gather / orchestrator-workers.** 리드가 분해→N워커 병렬(독립 컨텍스트)→합성; 워커는 서로 대화 안 함. 승리: breadth-first, read-dominant; 낭비: shared evolving context, write-heavy(암묵 결정이 unmergeable). — **BRICK 적용:** fan()+수렴(:458/:642) + sibling_independence(:737). effort-scaling: 사실조회 1레인, 비교 2–4, 진짜 breadth만 3(BRICK 상한3).
5. **Staged adaptive pipeline / dynamic DAG expansion.** 후행 단계 shape가 부분만 사전 선언; instance count가 앞 단계 출력에서 런타임 바인딩(Airflow `.expand()`, max_map_length=1024). 승리: 단계1이 워크로드 발견→단계2가 항목당 균일 작업; 낭비: cardinality가 이미 알려짐. — **BRICK 적용:** 이것이 2-페이즈 사고법의 정확한 근거. `expand()`(:1208, append-only dry-run) + held plan. 단 fan-out ceiling과 concurrency cap 필수(§1.8-10 혼합 budget 불가).
6. **Judge panel / independent redundancy (self-consistency, MoA, debate).** 같은 질문을 다중 독립 샘플/모델로 돌려 집계. 승리: high-stakes, 비교 가능 답 또는 critique가 draft를 개선; 낭비: 쉬운 일, 공유-prior wrong answer로 수렴. — **BRICK 적용:** QA 팬(§2.2-5의 이중 판정 경로 = attack-QA + EI + 게이트 mutation-RED). stamp_profile_gates(:1731)가 strict-evidence를 QA 행에 찍음. **집계 함수를 사전에 알아야 함**.
7. **Speculative execution with late binding (PASTE).** deciding 단계 커밋 전에 유망한 미래 작업 시작, 마지막에 값 바인딩. 승리: latency가 희소, 안정 패턴; 낭비: open-ended, side-effect. — **BRICK 적용:** `expand()`가 dry-run이고 절대 영속/실행 안 됨(:1208)이라 side-effect 없는 speculation의 안전판. 단 hold→forward-override 교차(§1.7)는 미검증.
8. **Evaluator-optimizer loop (generate→critique→regenerate).** 명확 기준까지 반복. 승리: 객관적 pass/fail 기준 + 반복 budget; 낭비: 모호한 기준(원형 churn). — **BRICK 적용:** reroute(:783)+node_reroute_budget=1(:2948)이 유한 반복 budget. 정지 조건 = 게이트 판정. meta-verification loop(§2.1) 회피 = DONE 라인 선언(§2.3-6).

### 3.2 분해 결정 규칙 (폭·순서 다이얼의 계량 근거)
1. **팹 크기 = min(⌈W/S⌉, 비충돌 write-set 파티션 수, √(1/κ)).** 셋 중 최소가 이김; 에이전트 공급은 절대 제약이 아님. — **BRICK 적용:** 폭 사다리 상한3(§5)의 계량적 정당화; 얽힘(κ 큼)은 N*를 낮춤.
2. **비충돌 write-set 사이만 병렬; 하나 안에선 sequence.** 공유 read는 OK, 공유 write는 안 됨. — **BRICK 적용:** write_scope 2법칙(§1.4)이 이걸 강제; AUTO-CARRY가 forward 의존을 표현. selflock의 "walker_kernel 무접촉"(§2.2-4)이 라이브 증명.
3. **Interface-first waves.** 공유 계약/스키마 변경은 wave 1 단독; 의존체는 frozen interface 대상으로 wave 2 팬아웃. — **BRICK 적용:** build() 위 chain(계약 노드)→fan(의존체) 순서. §2.3-6의 residual owner 선언과 결합.
4. **Fast-track 전에 crash.** critical path가 길면 먼저 critical task를 쪼개거나 강한 에이전트를 투입(crashing); 의존 작업 overlap(fast-tracking)은 rework 도박. — **BRICK 적용:** "강한 brain을 critical에"가 §2.3-1(얽힘→fugu)과 정확히 일치.
5. **큰 배치보다 작은 sequenced wave.** 각 wave의 통합/리뷰가 오케스트레이터 한 자리에 맞게; wave 끝마다 통합. 절반 wave = 절반 cycle time, 절반 blast radius. — **BRICK 적용:** 단계(시간축) 사이징; 홀드로 wave 경계 표시.
6. **Amdahl gate on marginal agents.** N+1 추가 전 marginal gain 확인; 추가 에이전트의 이득이 그것이 f에 더하는 리뷰 시간보다 작으면 정지. — **BRICK 적용:** 폭 사다리를 신호에 묶는 이유 — 리뷰어(게이트) 대역폭이 숨은 serial fraction.
7. **탐색은 직렬.** write-set을 예측 못 하면 파티션 불가. scout/diagnosis 1개 먼저 dispatch, 구조를 안 뒤에만 팬아웃. — **BRICK 적용:** **2-페이즈 사고법의 핵심** — design 레인(scout)을 먼저 hold와 함께, 구조 판정 후 expand(). Hard limit 4(forward-only)와 정합.
8. **Float는 load-balancing에 쓰되 scope creep엔 안 씀.** 유휴 용량은 high-float 작업(테스트/문서/독립 모듈)에. — **BRICK 적용:** QA/문서 레인을 high-float filler로 병렬.

### 3.3 통합 비용 경고 (금지 근거)
- **Retrograde scaling은 실재.** N* ≈ √(1/κ) 넘으면 총 산출이 **감소**(plateau 아님). merge-conflict rate 상승 = κ 가시화 = 정지 신호. — BRICK: 폭 상한3의 하드 근거.
- **모든 파티션 경계는 결함 site.** 버그는 다른 저자 코드 사이 interface에 몰림; 에이전트마다 interface가 n(n−1)/2로 증가. — BRICK: §2.1 design blind spot이 이 경계 누출.
- **리뷰어 대역폭이 숨은 serial fraction.** 10-에이전트 팹의 출력이 한 리뷰어로 funnel되면 f가 그 리뷰어에 지배됨. — BRICK: 게이트/QA 팬 폭을 §2.3-4대로 throttle envelope에 묶는 이유.
- **Big-batch 통합은 rework를 곱함.** 잘못된 공유 가정 위 큰 병렬 배치 = 끝에서 n× rework. — BRICK: 작은 wave(§3.2-5) + 홀드 경계.
- **늦고 얽힌 노력에 에이전트 추가 금지(Brooks).** 옳은 수: 경계 재절단, scope 축소, sequencing. — BRICK: §2.3-1이 라이브 사례.

### 3.4 안티패턴 (문서화된 실패 모드)
- ReAct token bleed / stale-plan rigidity / broken placeholder wiring / **fan-out overallocation**(단순 쿼리에 50 subagent) / **duplicate-labor fan-out**(모호한 워커 지시 → 같은 검색 반복) / **conflicting implicit decisions**(병렬 워커가 style/architecture를 암묵 커밋 → unmergeable) / token multiplier blindness(multi-agent ≈ 15x) / **unbounded/illegal expansion**(ceiling 없는 runaway 팬, mapped group 안 중첩 mapping 금지, zero-length map 조용히 skip) / consensus on wrong answer / unsafe speculation / circular refinement / **MAST 3-cluster**(poor specification, inter-agent misalignment, weak verification — 실패는 architectural이지 구현 버그 아님, 그러니 디스패치 언어가 spec·boundary·verification을 first-class로).

---

## 4. 미해결 설계 질문 (설계 3인이 각자 반드시 답할 것)

§1 한계 · §2 교훈 · §3 패턴 사이의 긴장에서 도출. 이 절이 3인이 실제로 소비하는 부분이므로 exhaustive하게 나열한다. 각 질문은 답의 **형태**(어디에 어떻게 인코딩되는지)까지 요구한다.

### 4.1 순서 사고 — 2-페이즈[design→hold→expand]는 언제 one-shot을 이기나
- Q1. **2-페이즈 발동 조건의 결정 규칙은 무엇인가?** §3.2-7("write-set을 예측 못 하면 파티션 불가 → scout 먼저")과 §2.2-2("결정을 닫고 transcription-narrow plan을 넘김")의 긴장을 해소하라. one-shot이 이기는 경계 = 파티션이 이미 알려진 경우(§3.1-5 낭비 조건: cardinality 사전 인지). **어떤 신호가 "폭이 아직 미지 → 홀드하고 design에게 물어라"를 트리거하는가?** 답의 형태 = task 본문에서 읽어낼 수 있는 관찰 가능한 술어(predicate).
- Q2. **design 페이즈의 홀드는 §1의 어느 프리미티브로 실현되나?** hold()는 수렴 노드에만(§1.5, Hard limit 2). design→(hold at 수렴)→expand가 legal 조합(§1.6 "held plan 위 expand()")인 것은 확인됨. 그러나 **§1.7의 "HELD 수렴 노드 위 expand()"는 미검증** — design이 이 경로를 밟는다면 반드시 미검증 표시 + 대안 경로를 병기하라.
- Q3. **one-shot으로 충분한데도 2-페이즈를 쓰면 무엇을 잃나?** batch-size U-curve(lens-decomp §22): work가 fixed dispatch+review overhead의 ~2–3배 미만이면 inline. 2-페이즈는 그 자체가 wave 하나의 transaction cost. **어느 크기 이하에서 2-페이즈가 순손실인가?**

### 4.2 폭/N 사다리 — 어떻게 결정 규칙으로 인코딩하나
- Q4. **폭 사다리(신호0=1인 / 1~2개=2인이종 / ③④급=3인이종, 상한3)를 §3.2-1의 min(⌈W/S⌉, 파티션 수, √(1/κ))과 어떻게 조화시키나?** 사다리는 "신호 개수"로 폭을 매기고, 결정 이론은 "병렬성·파티션·coherence"로 매긴다. **둘이 충돌하면 어느 것이 이기나?** (예: 신호 2개이나 write-set이 겹쳐 파티션이 1개뿐이면?) 답의 형태 = 사다리를 하드 상한으로, 결정 이론을 그 안에서의 하향 조정으로 두는 규칙인가, 아니면 별도인가.
- Q5. **폭은 build()에서 명시적 branch 리스트여야 한다(Hard limit 8: 동적 fan size 불가).** 따라서 폭은 발사 시점에 리터럴로 확정. **그런데 2-페이즈의 expand()는 폭을 런타임에 정하려는 시도다.** 이 둘을 어떻게 양립시키나 — design 페이즈가 폭을 리터럴로 확정한 뒤 expand()가 그 리터럴을 append하는가? expand()가 roots에만 attach 가능(§1.6)한 제약이 여기 어떻게 걸리나?
- Q6. **Amdahl/USL 정지 규칙(§3.2-6, §3.3 retrograde)을 폭 신호에 어떻게 노출하나?** 상한3은 √(1/κ)의 근사인데, **오퍼레이터가 κ(coherence, 공유 write/스키마)를 어떻게 관찰해 "3도 너무 많다 → 2로 내려라"를 판단하나?** 답의 형태 = write-set 겹침 카운트 같은 관찰 가능한 프록시.

### 4.3 partition_plan 반환 필드 — 무슨 모양인가
- Q7. **design 레인이 반환하는 partition_plan 필드의 스키마는 무엇인가?** §1엔 이 필드가 없다 — 신규 반환 형태다. 최소한 담아야 할 것(§2·§3에서 도출): (a) 폭 판정(N 및 각 branch의 concern-key — route가 concern-keyed이므로, Hard limit 6), (b) 각 branch의 write-set(§3.2-2 비충돌 증명용), (c) sibling_independence 후보(:737), (d) 캐스팅 티어(난이도-비례, §5), (e) DONE 라인 + residual owner(§2.3-6), (f) QA 렌즈 깊이 + 이중 판정 경로(§2.2-5). **이 필드가 expand()의 입력으로 어떻게 소비되나?**
- Q8. **partition_plan은 어디에 사는가 — brick return.yaml(사전 선언, §1.8-15) 아니면 그래프 런타임 상태?** Hard limit 15("builder-level 커스텀 증명 의무 없음 — brick spec에 사전 선언")가 이걸 제약한다. design 레인의 반환을 새 brick KIND의 return 계약으로 봉인해야 하나?

### 4.4 expand()-at-hold 리터럴 문법 — §1.7 미검증 조합을 어떻게 다루나
- Q9. **홀드된 plan 위 expand()의 정확한 리터럴 문법은 무엇인가?** 확인된 것: expand()는 :1208, append-only dry-run, roots에만 attach(§1.6). 미확인: **HELD 수렴 노드가 append-only 검증에서 re-route를 막는지**(§1.7 마지막 항목, 명시적 UNVERIFIED). design은 이 경로를 (a) 검증 실험을 요청하는 open question으로 표시하거나 (b) hold를 밟지 않는 대안(예: forward-override 없이 새 roots만 append)을 제시해야 한다. **추측 금지 — 미검증이면 미검증으로.**
- Q10. **expand()가 절대 영속/실행 안 됨(:1208)이라면, 2-페이즈의 두 번째 페이즈는 무엇이 실제로 발사하나?** expand()는 dry-run 미리보기이지 dispatch가 아니다. **design 판정 후 실제 나머지 레인을 발사하는 것은 어느 verb인가 — fire()(:1328)인가, 새 build() 라운드인가, resume 선언기(resume_declaration.py)인가?** §1.8-11("build() 내부에 defer-to-resume 없음; resume은 onboard-tier")이 여기 결정적. 2-페이즈가 사실 (build 1: design+hold) → (resume/build 2: 나머지)의 두 온보드 라운드인가?

### 4.5 금지할 안티패턴 — 어느 것을 그래프 레벨에서 막나
- Q11. **§3.4 안티패턴 중 어느 것이 v2 사고법에서 하드 금지(그래프가 REDs)이고 어느 것이 soft 경고인가?** 야간 실측이 지목한 것: fan-out overallocation(§3.3), conflicting implicit decisions(§2.2-4 비충돌 write scope의 역), unbounded expansion(§1.8-10 혼합 budget 불가), meta-verification loop(§2.1, §2.3-6). **각 금지가 §1의 어느 체크로 lower되나?** (예: unbounded expansion → expansion budget이 per-node XOR aggregate 강제.)
- Q12. **duplicate-labor fan-out과 conflicting implicit decisions를 막으려면 각 branch가 무엇을 명시해야 하나?** §3.1-4 precondition: per-worker spec(objective, output format, scope) + effort-scaling. 이것이 §1의 branch returns=(:506) + write_scope + concern-key로 충분한가, 아니면 partition_plan(Q7)이 더 담아야 하나?

### 4.6 공간/시간/권위 다이얼 상호작용 — 독립인가 결합인가
- Q13. **세 다이얼은 독립적으로 돌릴 수 있나, 아니면 결합돼 있나?** 실측이 시사하는 결합:
  - 공간↔권위: 폭(공간)을 올리면 캐스팅(권위)이 난이도-비례로 따라감(§2.3-1: 얽힘 폭 → fugu work). 독립 아님.
  - 시간↔권위: QA 렌즈 깊이(권위)가 fable5 throttle envelope에 묶임 → QA 팬을 시차(시간)로 벌려야(§2.3-4). 결합.
  - 공간↔시간: 폭이 미지면 홀드(시간)로 미뤄 design에 물음(§4.1 Q1). 결합.
  **답의 형태 = 세 다이얼의 결합 그래프 — 어느 쌍이 함께 움직이고, 어느 순서로 정해야 하나(예: 시간축 2-페이즈를 먼저 정해야 공간 폭이 정해지나)?**
- Q14. **캐스팅 독트린(단순=codex / 얽힘=푸구+fable5)과 폭 사다리가 충돌할 때?** 신호가 ③④급이라 폭3을 부르지만 표면이 얽혀 있지 않으면(단순) — 폭3 codex인가, 아니면 얽힘 없음이 폭을 눌러 폭1 codex인가? **난이도와 신호 개수가 다른 방향을 가리킬 때의 우선순위 규칙.**
- Q15. **권위축의 "게이트 깊이"는 §1의 어느 표면으로 실현되나, 그리고 그 상한은?** stamp_profile_gates(:1731)는 QA 행 strict-evidence + 최종 human/coo만; node.gates(:2034)는 human/coo만 + 나가는 엣지 정확히 1개; brick 게이트 → budget=1(:2948). Hard limit 5·9(non-completion 내부 엣지/final 외 per-node 게이트 불가)가 게이트 깊이의 상한. **v2가 원하는 게이트 깊이가 이 상한을 넘으면 어떻게 표현하나 — 아니면 넘을 수 없다고 인정하나?**

### 4.7 환경 강건성 (야간 사망의 지배 원인이므로 별도 질문)
- Q16. **환경 사망(throttle/timeout/451)이 라운드를 소비하지 않게 하는 것을 v2 사고법이 어떻게 구조로 보장하나?** 실측 해법(§2.3-3,4,5): deep-lane timeout auto-raise(10800s), 1–2 시차 fable5 QA + 이중 판정 경로, fan 발사 전 환경 probe + R3 loud-HOLD. **이것들이 partition_plan 필드인가, 그래프 룰 체커 REDs인가, 캐스팅 시점 파라미터인가?** 특히 **R3 loud-HOLD(receipt-no-response에 비명)**를 §1의 어느 route/hold 표면으로 실현하나 — hold는 수렴 노드에만이고 fan-out source엔 불가(Hard limit 2)인데.

---

## 5. 제약 (불변)

아래는 설계가 넘을 수 없는 고정 경계다. 어떤 v2 사고법도 이걸 유지해야 한다.

1. **공식 build 표면 하나** — 저작 진입점은 단일 공식 build 표면. 병렬 표면 신설 금지.
2. **Link 권위 불변** — Link 게이트 어휘/권위는 그래프 저작이 건드리지 않는다.
3. **자동발사 금지 (Rule 3)** — expand()는 dry-run이며 절대 영속/실행 안 됨(§1 :1208). 실제 발사는 오퍼레이터/게이트를 거친다. 어떤 2-페이즈 설계도 홀드 뒤 자동 fire를 도입하면 안 됨.
4. **커버리지 무손실** — 파티셔닝·홀드·expand 어느 것도 원래 task의 커버리지를 떨어뜨리면 안 됨. AUTO-CARRY(§1.4)와 residual owner 선언(§2.3-6)이 이를 지킨다.
5. **난이도-비례 캐스팅 독트린** — 단순 = codex; 얽힘 = 푸구 + fable5. (§2.2-1, §2.3-1의 라운드-수 레버.)
6. **폭 사다리** — 신호0 = 1인 / 1~2개 = 2인 이종 / ③④급 = 3인 이종, **상한 3**. (§3.2-1 min-규칙, §3.3 retrograde scaling의 근사.)
7. **신규 조립기 금지 (Rule 9)** — 새 assembler/build verb를 만들지 않는다. v2 사고법은 §1의 기존 프리미티브로만 표현돼야 한다 — 표현 못 하는 것은 Hard limit으로 인정하고 미해결 질문으로 남긴다.

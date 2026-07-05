We were given the analysis results and need to produce a Korean markdown report for Smith. The data is already provided in the system context (the three-axis mapping JSON). I have everything I need. Let me write the report directly since I'm asked to return it as my final message.

Let me build the report following the requested section structure, preserving the file:line citations from the measured data.

---

# BRICK 규율 3종 — 현재 어떻게 하고 있나 (정직 보고)

> 실측 기준: repo `/Users/smith/projects/BRICK`, HEAD `781bf8d`, `check_profile.py --all` = exit 0(green) 확인. 읽기전용.

---

## ① 한 줄 요약 + 3축 그림

**한 줄:** 3축 경계와 원인분리는 "법 → 런타임 → 체커" 3층으로 **진짜** 박혀 있는데, 강제 방식이 거의 다 **키-이름 블랙리스트**라서 *의미상* 판정(자유텍스트로 "PASS")은 못 잡고, **헌법(AGENTS.md) 전문과 축 불변식은 작업 에이전트 패킷에 0% 주입**된다 — 즉 "법은 선언됐는데 일꾼은 그 법을 못 본다."

```
                        AGENTS.md (헌법 = 선언만)
                        "Brick/Agent/Link 셋만 의미축, support는 4번째 아님"
                                     │
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
         ┌──────────┐         ┌──────────┐         ┌──────────┐
         │  BRICK   │  ──일──▶ │  AGENT   │  ──반려▶ │  LINK    │
         │  (일)    │ work    │ (수행자) │ concern │ (이동)   │
         │ 측정만   │◀─충분성─ │ 닫힌2필드│ 비구속  │ 판단만   │
         └────┬─────┘  읽음   └────┬─────┘         └────┬─────┘
              │ comparison.py      │ return_fact.py     │ gate.py
              │ (측정값 author)    │ (success 금지)     │ (Movement 안 고름)
              └────────────────────┼────────────────────┘
                                   │ FACTS만 기록 (판단 0)
                                   ▼
                        ┌─────────────────────┐
                        │  support (비-축)    │  ← run.py / walker_kernel / recording
                        │  측정·기록·격리만   │     "failing_axis/fault/success 못 씀"
                        │  worktree 샌드박스   │     "Movement·route 발명 안 함"
                        └─────────────────────┘
                                   ▲
                        체커 5종이 이 경계를 사후 스캔 (--all green)
```

핵심 직관: **support는 일을 적는 서기(書記)지 판사(判事)가 아니다.** 서기가 판결문을 쓰면(success/fault 키) 체커가 RED. 단, 서기가 판결을 *본문 산문에 슬쩍* 적으면(자유텍스트) 아무도 못 잡는다.

---

## ② 각 축 경계 — 선언 / 강제 / 런타임 + 갭

| 축 | 법(선언) | 체커가 잡는 것 | 런타임 강제 |
|---|---|---|---|
| **Brick (일)** | `AGENTS.md:29-67, 194-465` — 일·측정 소유 | `check_axis_contract_projection` BRICK_FORBIDDEN(`:42-54`): brick/*.yaml에 agent/movement/route/success 키 금지 | 측정만 산출(`brick/comparison.py`), Movement 안 만듦 |
| **Agent (수행자)** | `AGENTS.md` Agent owns/forbidden | AGENT_FORBIDDEN(`:72-86`)+AGENT_REQUIRED(`:56`): return_fact.yaml에 success/failure/verdict 금지, 닫힌 2필드 강제 | **`make_agent_fact()`** (`agent/return_fact.py:103-162`)가 received_work+returned 둘 다 강제, 최상위 verdict키(`TOP_LEVEL_VERDICT_KEYS :32-57`) 있으면 `ValueError`. 실호출 `run.py:2033·2230` |
| **Link (이동)** | `AGENTS.md:419-421` — 이동충분성만 판정, 측정 안 함 | LINK_GATE_FORBIDDEN(`:194-205`)+ENGLISH_MOVEMENT_LITERALS(`:213-216`): movement 리터럴 `forward/reroute` 2개만, hold/stop/return/pass/한글 거부 | `GateFact`(`link/gate.py:153-212`)가 Brick 측정을 **읽어서** sufficient/missing만 산출, route/target 안 고름 |
| **support (비-축)** | `AGENTS.md:509-594` — 기계·증거·투영뿐, source truth 아님 | `check_recording_checker_derived_contract`: evidence에 failing_axis/fault/success 토큰 금지 / `check_axis_crossing_elegance` G3 AST: canonical 심볼로만 축에 닿음 / `check_package_path_admission`: 1241경로 표면 게이트 | walker는 caller 선언 row만 walk, Movement 발명 안 함(`run.py:3-4·313`), 격리 worktree에 증거만 |

**경계 갭:**
- 🟡 **minor** — Agent Object yaml에 명시적 `axis: Agent` 필드 없음. 축 귀속이 **폴더 위치(`agent/objects/`)로만** 결정 (`coo.yaml`/`dev.yaml` 실측). 잘못된 위치에 두면 직접 axis 검증이 아니라 `check_package_path_admission` 경로 게이트에만 의존.
- 🟡 **minor** — `axis_responsibility`는 축-강제 라벨처럼 보이지만 실제론 design 브릭의 **선언된 return 필드 한 칸**(`brick/templates/bricks/design/return.yaml:13`). AgentFact 체커는 이 필드 존재/정확성 검증 안 함 — 이름이 메커니즘처럼 보이는 함정.

---

## ③ 원인분리 — 격리 / 축귀속 자동인가 사람인가 / gate=판단·measure=측정 분리

**F1 per-branch 격리 (실재함):**
한 브랜치 예외가 형제를 안 죽인다. 예외를 던지지 않고 **데이터로 봉인**한다.

```
배치 디스패치 (walker_kernel.py:2244-2275)
  ├─ 브랜치 A ─▶ 정상 outcome ──┐
  ├─ 브랜치 B ─▶ 💥예외 ──▶ NodeProcessingOutcome.raised_exception 에 봉인
  │                          (raise 안 함 → 형제 future 안 죽음) :1745-1768
  └─ 브랜치 C ─▶ 정상 outcome ──┘
                    │
          declared 순서로 드레인 (:2348-2358)
          실패 직전까지 부분진척을 evidence로 확정
                    │
          실패 브랜치만 frontier로 물질화 (:2546-2548)
```

**축귀속 = 자동도 사람도 아닌 "안 함"(by design):**
support는 FACTS만 적고, **어느 축이 fault인지 라벨링하지 않는다.** `walker_evidence.py:11-16` 가 명시: *"attribution is the reader's inference."* 체커 `_FORBIDDEN_JUDGMENT_TOKENS`(`check_recording_checker_derived_contract.py:49-55`)가 emit record와 emitter 소스 **양쪽**에서 failing_axis/fault/failed/success/quality verdict를 막고, 이 체커가 `building_automation.yaml:75`에 등재돼 **--all green에 실제 포함**된다. 실측: 소스 전역 failing_axis/fault assign **0건**.
→ 귀속은 **사람(독자)의 추론에만** 존재.

**gate=판단 / measure=측정 분리 (실재하나 체커는 약함):**
`link/gate.py:153-212`가 Brick이 만든 `BrickComparisonFact`를 **읽어서** sufficient/missing만 산출, 측정값을 다시 안 만듦(`AGENTS.md:419-421`). 모듈경계+법+docstring으로 분리는 **실재**.

**원인분리 갭:**
- 🔴 **major** — **실패→축귀속을 기계가 산출 안 함.** "자동 원인분리"를 기대하면 갭(의도된 2층 모델이긴 함). 사람 판단에만 있음. (`walker_evidence.py:11-16`)
- 🔴 **major** — **gate가 "측정 안 함"을 소스레벨로 막는 전용 체커 부재.** `check_axis_contract_projection`은 YAML projection drift만 검사(`:1-40`). 누군가 `gate.py` 함수 본문에 측정/판정 로직을 혼입해도 green일 수 있음.
- 🟡 **minor** — 다중 동시실패는 첫 실패에서 **직렬 컷오프**(`:2348-2358, 2546-2548`). 실패 브랜치 이후 형제는 그 walk에서 안 찍히고 frontier로 미룸 → 완전 병렬 원인분리는 아님.
- 🟡 **minor** — `disposition_action`이 raise/forward/stop/reroute로 한정(`link/transition.py:10`). 사람이 "기획으로 임의 재기획" 귀속하는 Link 어휘 여전히 없음(MEMORY 0616 갭 재확인).

---

## ④ 헌법 주입 — 작업 패킷에 정확히 뭐가 들어가나

작업 에이전트 패킷에 **정확히 주입되는 것** (`agent_resources.py:543-567`, `agent_adapter.py:_build_prompt 2076-2158`, 런타임 `run.py:2562-2609`):

```
패킷 (render_agent_instruction_packet)
  ├─ prompt        : 그 role 1개      → 전문(full body) ✅
  ├─ discipline    : 2개(closed-agentfact, proof-limits) → 전문 ✅
  │                   ※ 단 네이티브 서브에이전트 투영에선 "첫 줄만" 축약
  ├─ hook          : 4개              → advisory 설명문(장식) ⚠️ 실행 안 됨
  ├─ skill         : ref body
  ├─ tool_policy / proof_limits / not_proven
  ├─ 하드코딩 rules : "source truth 주장 마라/Movement 고르지 마라/commit·push 마라"
  ├─ work_statement (Brick row에서)
  ├─ write_scope / required_return_shape
  └─ AGENTS.md     : ❌ 0% (전혀 안 들어감)
```

**AGENTS.md 전체 vs 일부:** **0이다.** 일부도 아니다. ref 해석기(`agent_resources.py:360-368`)가 `prompt:/skill:/tool-policy:/discipline:`만 알고 AGENTS.md는 모름. 런타임 어디에도 AGENTS.md를 읽어 패킷에 넣는 코드 없음. 그런데 `AGENTS.md:8-10`은 *"패킷의 AGENTS-governed operating context가 active operation을 통제한다"*고 선언 → **선언-실재 불일치.**

**축 불변식 주입 갭 (F1 뿌리):** 질문의 F1 = '독립 팬아웃 → 독립 증거'(0609 cross-vouch leak 사건의 뿌리)가 **작업 지시에 텍스트로 안 들어간다.** 주입되는 discipline 2종은 '반환/보고 모양'만 규율하고 스스로 *"judge the work 안 한다"*고 명시(`proof-limits.md:12`). cross-vouch/독립증거 류는 작업 패킷에도, **체커 grep에서도** 강제 지점을 못 찾음 → **사람 기억(MEMORY 0609)에만 사는 것으로 보임**(suspected, 전수 grep 기준).

---

## ⑤ 3층 닫힘표 — 핵심 불변식별 [법 / 주입 / 강제]

> ✅ 닫힘 · ⬜ 비어있음 · 🟡 부분/약함

| 핵심 불변식 | 법(AGENTS.md 선언) | 주입(패킷에 실림) | 강제(체커/엔진/런타임) |
|---|:---:|:---:|:---:|
| Agent 반환 = 닫힌 2필드, verdict키 금지 | ✅ | 🟡 (rules로 soft) | ✅ `return_fact.py:103-162` |
| concern = binding=false + 닫힌 8종 | ✅ | ✅ (스키마) | ✅ `return_fact.py:112-134` |
| Movement = forward/reroute 2리터럴만 | ✅ | ⬜ | ✅ `check_axis_contract_projection` |
| 3축 evidence spine 존재 | ✅ | ⬜ (에이전트 미리 못 봄) | ✅ `check_tier_a` 7 FIRE 프로브 |
| support = fault/verdict 안 찍음 | ✅ | n/a | ✅ `check_recording_checker_derived_contract` |
| gate=판단만, 측정 안 함 | ✅ | ⬜ | 🟡 모듈경계만, 소스체커 없음 |
| **AGENTS.md 헌법 전문** | ✅ | **⬜ 0%** | ⬜ |
| **축 불변식 (F1 독립증거)** | ⬜ (헌법에도 약함) | **⬜** | **⬜ (체커도 grep 무결과)** |
| hook 가드 (no-mutation 등) | ✅ | 🟡 (advisory 텍스트) | ⬜ "never executed" `registry.yaml:1-5` |
| write_scope 봉쇄 | ✅ | 🟡 (soft 프롬프트) | 🟡 worktree 격리가 진짜 봉쇄 |
| 의미상 success 판정(자유텍스트) | ✅ | ⬜ | ⬜ Not Proven `AGENTS.md:927` |

**읽는 법:** 위 5줄은 3칸 다 찼다(진짜 닫힘). 아래 6줄은 **한 칸 이상 비었다** — 특히 F1(축 불변식)은 **3칸 다 비었고**, 헌법 전문은 선언만 있고 주입·강제 0.

---

## ⑥ 가장 큰 갭 1~3 + 처방 방향

**갭 1 (major) — 헌법·축 불변식이 일꾼에게 0% 도달.**
`AGENTS.md:8-10`이 "패킷이 AGENTS-governed context로 통제"라 적지만 실제 주입은 0. F1('독립 팬아웃→독립 증거')은 패킷·discipline·체커 어디에도 없고 **사람 기억에만** 산다. 0609 clobber 사건이 재발할 구조적 빈칸.
→ **처방:** ref 해석기(`agent_resources.py:360-368`)에 `axis-invariant:` ref 종류 신설 → 해당 브릭에 관련된 축 불변식만 골라 패킷에 주입(전문 덤프 말고 bounded). 그리고 F1을 **체커로 승격**: sibling fan-out 노드의 evidence 파일이 byte-distinct한지 스캔하는 oracle 추가(현재 `check_tier_a`의 sibling 프로브를 cross-vouch 독립성으로 확장). 선언→주입→강제 3칸을 F1부터 메운다.

**갭 2 (major) — gate가 "측정 안 함"을 소스레벨로 막는 체커 부재.**
법+모듈경계+docstring으로만 서 있고, `gate.py` 본문에 측정 혼입을 직접 막는 게 없음(`check_axis_contract_projection`은 YAML drift만).
→ **처방:** evidence emitter에 이미 있는 import-boundary 체커(`_check_emitter_axis_separation` 패턴)를 `link/gate.py`에 복제 적용 — gate가 `brick/comparison.py`를 **소비(import)**는 하되 측정 심볼을 **재정의/재계산**하면 RED. 원인분리 신뢰성의 뿌리.

**갭 3 (major) — 강제가 키-이름 블랙리스트라 의미상 판정은 못 잡음.**
Agent가 `observed_evidence` 자유텍스트에 "PASS"를 박으면 런타임도 체커도 통과. `AGENTS.md:927`이 semantic correctness를 **Not Proven으로 자인**.
→ **처방:** 이건 정직하게 **"체커로 닫기 어려운 칸"**으로 인정하는 게 맞다(자유텍스트 의미판정은 LLM 없이 못 잡음). 처방은 강제가 아니라 **측정**: 회고 빌딩에서 자유텍스트 verdict 누수 케이스를 채굴해 빈도를 재고, 임계 넘으면 그때 LLM-judge 보조 oracle 검토. 지금은 Not Proven을 **명시적으로 들고 가는** 게 정직.

---

**정직 마무리:** green은 "감사된 현재 표면에서 축 침범 0"을 뜻하지, "미래 누수 부재"나 "완전 커버리지"를 뜻하지 않는다(`AGENTS.md:596-607, 932` 자인). 진짜 닫힌 건 **return shape / concern 어휘 / 3축 evidence 존재 / support no-judgment** 네 개. 비어 있는 가장 아픈 칸은 **F1 축 불변식이 법·주입·강제 3칸 다 빈 것** — 여기가 다음 한 수다.
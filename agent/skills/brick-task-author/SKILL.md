---
name: brick-task-author
description: BRICK 빌딩 발주 한 스킬 — PHASE 1 task 본문 쓰기 → 입력 모드 결정(프리셋/DSL 그래프) → PHASE 2 공식 빌딩 build 입력 → PHASE 3 홀드 분류(걸리면). 새 빌딩 발주, 수리·기능·부검 task를 쓸 때 이 절차로. 모양 사이징은 building-sizing-method 스킬.
---

# BRICK 발주 (운영자 표준, 3-PHASE)

> 현재 호출자가 준 활성 체크아웃과 활성 vessel evidence root를 기준으로 발사·측정·코드수정한다.
> old hardcoded operator-local paths 및 the frozen history repo 문구는 현재
> Customer-Ready Goal v3와 충돌하면 역사/박물관 증거다.

## 공식 경로는 하나

공식 실행 경로는 한 줄이다:

```
brick build / support.operator.cli build
→ Builder/materializer
→ declared Building Plan
→ support/operator/run.py walker
→ active vessel evidence root
→ reporter / Slack / frontier
```

프리셋 모드와 DSL 그래프 모드는 **공식 build surface로 들어가는 두 authoring form**이다.
공식 authoring/launch interface는 `assemble()` / `build()` / `fan()` Python DSL
(`support/operator/assembly.py`) plus `run_building_plan()`이다.
graph packet JSON을 `brick build --graph <packet>` 또는
`support.operator.cli build --graph <packet>`에 넘기던 저수준 CLI escape hatch는 Rule 10에
따라 retired다. `sibling_independence`, per-node `write_scope` narrowing, mid-graph
human/coo gates는 이제 DSL gap이 아니다.
Profile compatibility note: the former example spellings `brick build --graph <packet.json>`
and `support.operator.cli build --graph <packet.json>` are mentioned here only as
retired text, not as active instructions. The old phrases "같은 공식 route의 저수준 입력" and
"같은 공식 build surface로 들어가는 두 입력 모드" are likewise retained only as
historical checker text, not current operating guidance.
P3 이후 zero-ritual 운영자 경로는 `task_intake` 확인 뒤 **`build()` 하나로** compact graph를
넣는 것이다. 운영자-facing 언어는 `build()`다. `fan()`은 `build()` 안의 병렬 블록 재료일
뿐이고, `fire()`/`launch_assembled_building`은 내부 구현·debug/advanced 용어다.
프롬프트/발주문에서 운영자에게 `fire(graph)`를 하라고 쓰지 마라. 파일 handoff/감사
목적이면 DSL 출력/plan evidence를 남겨라. 기본 운영 프롬프트는 `build()`만 말한다.
helper를 별도 공식 route처럼 말하지 마라.

## 한눈 결정나무

먼저 고정 파이프라인을 버린다. 운영자는 이 task에 필요한 두뇌(LLM), 손발(Brick),
수렴/분기(Graph)를 구성한다. `work -> QA -> closure`는 한 가지 흔한 모양일 뿐 기본 사고가
아니다. 이 구성이 막히면 스킬을 갱신하는 것도 dogfood다.

```
무엇을 발주하나?
│
├─ 표준 작업(수리·기능·부검·조사), 모양이 프리셋에 이미 있음
│     → PRESET 입력 모드 (PHASE 2-A). render_preset_ranking_packet로 랭킹(advisory — 내가 고름).
│
└─ 새 모양(팬아웃·팬인·병렬·다단), 맞는 프리셋 없음
      → 먼저 building-sizing-method 스킬로 모양 산출 → DSL GRAPH 입력. 누가 보나로 가른다:
        ├─ 사람이 머지 전 승인(감독)  → graph packet에 human gate를 선언
        └─ 골까지 무인(Smith 기본)    → DSL graph를 PHASE 2-B 공식 route로 제출
```

발주 공개 surface = **공식 빌딩 build surface 하나**다. 프리셋은 task/preset 입력으로
materialize되고, 그래프는 DSL graph 입력으로 materialize되며,
둘 다 Builder/materializer → declared Building Plan → `support/operator/run.py` walker →
active vessel evidence root → reporter/Slack/frontier로 간다.
`driver_public_intake_seal` 체커는 raw 뒷문(`run_composed_graph_intake`)을 driver.py 공개표면에서
막는다. `assemble`과 launch helper들은 graph/materialization helper이지 별도 실행 route가 아니다.
3번째로 사고하지 마라.

## 큰 일 P3 규칙

크거나 번질 가능성이 큰 task를 한 `work` Brick에 바로 던지지 마라.
사용자에게 보이는 축약은 이 정도면 충분하다:

> this is big; design first, split it, and run the lanes in parallel.

의도한 모양은:

```
task intake
→ design
→ design QA / axis inspection
→ closure confirms execution plan
→ parallel dev lanes
→ each lane dev then QA
→ fan-in integration/summary
→ Codex code/regression QA + Gemini-local axis/evidence QA
→ Codex closure
```

이것은 design-first fan-out 또는 DSL graph로 설명해도 된다. 그래도 Link가
Movement authority를 소유하고, support/model/checker/Slack은 source truth나
quality/success judge가 아니다.

---

# PHASE 1 — task 본문 쓰기

## 엔진이 task.md에서 진짜 요구하는 것 (실측)

| 필드 | 진실 |
|---|---|
| 노드 `work=` | **유일한 구조적 필수.** `brick("work","<한 줄>")`. 빠지면 CompositionError. returns/alias/comparison_rule은 build()가 자동채움 — 쓰지 마라. |
| 빌딩 `task=` | 비어있지 않은 텍스트 ≤64KB면 됨. **안의 heading 하나도 엔진 검증 안 함** — sha256 후 `work/task.md`로 그대로 쓰여 에이전트 프롬프트가 됨. |
| 그 외 | 모든 섹션은 에이전트 행동용(admission용 아님). write hand는 두 잠금: 노드 `write=True` + launch `write_scope`. `write_scope`만 넘기면 scope가 찍히지 않아 read-only가 정상이다. adapter/model/gates는 assemble()/fire 인자(task.md 안 아님). |

**스톨의 진짜 레버(실측 0615):** 엔진은 task.md로 인한 스톨 0(불투명 텍스트). 60분 vs 2분은 **에이전트의 읽기범위 바운디드냐**다 — "fix the adapter"(무바운드)=트리 전체 훑어 60분 / "이 영역만, 딴 데 훑지 마"=2분. **레버 = 바운디드 스코프 한 줄(모듈·영역 단위면 충분).** file:line 좌표 박기는 목표 아니라 **fallback**(설계 노드 못 믿을 때만). §AUTO엔 그 읽기목록 산출이 **design 노드의 일**이다.

**task.md 주입 없음(0702 실측):** `task=`/`goal=`은 `work/task.md` **증거물**로만 쓰이고, 어떤 경로도 레인 프롬프트에 주입하지 않는다. 레인이 반드시 봐야 할 계약(반환 스키마·경계·금지선)은 각 노드 `work_statement`에 직접 박아라. 프리셋 materializer 요약도 `## First-Line Contract`/`## Objective`/`## Desired Outcome` 헤딩만 스캔한다.

## 샤프 템플릿 (이대로 — 더 보태지 마라)

```
# <한 줄 제목: 결함번호 또는 기능명>

## Objective
<불변식 한 문장: "이후 X는 Z일 때도 항상 Y다.">

## Context (자급자족·실측 — 어디 보고 어디는 안 보나)
<중요 표면을 모듈·영역 단위로 지명: 본뜰 파일·선례·무는 제약 하나.
 실측값(재현 행·ref·에러) 있으면 인라인. 마지막 줄 "다른 모듈은 훑지 마라." ← anti-stall 레버>

## Deliverables (번호)
1. <변경 본체>
2. <체커 핀: 픽스처+변이 RED 보임, 없으면 왜 없는지 한 줄>

## Proof required (직접 실행·정직 보고 — 주장은 실행 결과만)
<포커스 체커 green + 변이 RED → check_profile.py --all은 /tmp 로그로 저장하고 rc/pass/failure-marker만 요약 → (코드면) compileall + git diff --check>

## Hard constraints (law)
<write_scope는 "support/operator/**" glob(★"support/" 금지 = fnmatch 함정).
 금지선: 실루트 수정 / 핀 완화 / 스케줄러·신규의존성 / project/ 손대기>
```

부검은 `project/brick-protocol/status/kernel/evidence-postmortem-task-template-0612.md` 사용([TARGETS]=대상 루트 + 대조군 1동, 사건은 장부에 있는 것만).

## 그래프 모양은 building-sizing-method 스킬

그림→코드 번역(`build() IS pipeline`, `fan() IS parallel`, KIND→에이전트 바인딩, QA깊이
그라데이션, 과대-사이징 금지)은 **building-sizing-method** 스킬로 분리됐다. 새 모양을 짜야 하면
그 스킬을 먼저 돌려 `GraphSpec`을 얻고, 여기 PHASE 2로 와서 발사한다. 운영자의 일 = **모양 판단
하나**(몇 단계·누가 병렬·어디 수렴)뿐.

---

# PHASE 2-A — PRESET 입력 모드 (brick build --task/--preset)

```python
# cd <active checkout> && uv run python3 -c "..."
from brick_protocol.support.connection.building_design_toolkit import render_preset_ranking_packet
pkt = render_preset_ranking_packet("<task 요지 한 줄>", repo_root="<active checkout>")
# 토큰겹침 점수 desc. ADVISORY(자동선택 아님) — 내가 골라 chain_preset_ref로 박는다. 카탈로그=brick/templates/presets/
```
공식 입력은 CLI build다. 예:

```bash
brick build --task "$TASK" --preset building-chain-preset:<프리셋> --real-provider --adapter adapter:codex-local
```

---

# PHASE 2-B — GRAPH 입력 모드 — compact graph는 build() 하나로 넣는다

P3의 기본 목표는 “쉽게 그린다”다. task interview가 끝났으면 먼저 compact graph를 그린다:

```
task_intake → task.md 후보 확인 → graph = assembly.build([... fan([...]) ...]) → operator build(graph, goal=...)
```

## G1 no-link / route-default 정책 (0630 closeout)

사용자·COO 표면에서는 **Link row를 직접 쓰지 않는 것**이 맞다. 그러나 이것은
"모든 edge가 자동 route"라는 뜻이 아니다. 현재 compact `build()`/`fan()`은 인접 edge를
materialize할 때 기본 `movement="forward"`를 만든다. 즉:

```text
사용자 표면: Link row 안 씀
support materializer: Link row를 만든다
기본 Movement: forward = 선언된 길을 계속 감
reroute/HOLD: concern evidence + 선언/채택된 route policy가 있을 때만
```

따라서 QA/closure가 blocker를 낼 수 있는 fan-in 그래프를 짤 때는 decorative all-forward
그래프로 끝냈다고 route-default를 증명했다고 말하지 마라. 필요한 모양은:

```text
work/design → fan(QA lanes) → closure-synthesis
closure-synthesis만 Link-facing transition_concern_evidence를 반환
Link/COO가 declared policy(route-policy:qa-basic-repair 등)나 convergence route= mark를 보고
forward / reroute / HOLD 중 하나를 채택
```

hard fan-in QA에서는 QA lane이 직접 Movement를 고르지 않는다. QA는 자기 관찰을 반환하고,
closure가 concern evidence를 종합한다. ambiguous / conflicting / unresolvable / budget-exhausted는
forward가 아니라 HOLD 후보로 보고한다.

쓰기 작업이면 compact graph와 발사 인자가 둘 다 필요하다(0630 smoke 실측):

```python
from brick_protocol.brick.spec import brick
from brick_protocol.support.operator.assembly import build as graph
from brick_protocol.support.operator import build

build(
    graph([
        brick("work", "정해진 파일만 변경하라", write=True, adapter="codex-local"),
        brick("closure", "산출물과 evidence를 확인하라", adapter="codex-local"),
    ]),
    goal="<task.md 한 줄 요약>",
    declared_by="coo-smith",
    author_ref="coo:smith",
)
```

write_scope가 필요한 구현 Building이면 현재 one-call `support.operator.build()`가 숨기는
발사 인자와 실제 write hand가 맞는지 먼저 확인한다. write hand를 직접 맞춰야 하는 디버그/감사
상황이면 DSL/plan evidence를 확인하되, 운영 프롬프트의 기본 언어는 여전히 `build()`다.

`write_scope`만 넘기고 work 노드에 `write=True`가 없으면 assembly가 scope를 찍지 않으므로
Agent는 read-only grant를 받는다. 그 경우 `frontier=complete`라도 `made_changes=false`가
나올 수 있으며, 이것은 발사자 그래프 선언 문제다.

`fire()`는 수동 worktree/dict/path/adapter_cwd/json ritual을 삼키는 내부 sugar일 뿐,
운영자-facing 발주 언어가 아니다. 별도 runtime, direct launch runner, phase runner,
work-return proof, QA-return proof, closeout proof, 또는 Movement route도 아니다. 사람이
승인해야 하는 파일 handoff나 디버그가 필요할 때도 raw packet CLI 입력으로 낮추지 않는다.
기본 프롬프트와 골 운영 문구는 `build()`만 말한다.

```json
{
  "task_statement": "<한 줄 task 본문 - work/task.md 됨>",
  "declared_by": "coo-smith",
  "building_id": "<슬러그>-MMDD",
  "selected_adapter_ref": "adapter:codex-local",
  "selected_model_ref": "model:default",
  "nodes": [
    {"node_id": "<id>-design", "step_ref": "<id>-design", "step_template_ref": "building-step-template:design", "work_statement": "범위를 좁혀라"},
    {"node_id": "<id>-work", "step_ref": "<id>-work", "step_template_ref": "building-step-template:work", "work_statement": "변경하라", "requires_brick_write_scope": true, "write_scope": {"allowed_paths": ["."], "forbidden_paths": [".git/**"]}},
    {"node_id": "<id>-closure", "step_ref": "<id>-closure", "step_template_ref": "building-step-template:closure", "work_statement": "검증·보고하라"}
  ],
  "edges": [
    {"edge_ref": "edge:<id>-design-to-work", "source": "<id>-design", "target": "<id>-work", "movement": "forward"},
    {"edge_ref": "edge:<id>-work-to-closure", "source": "<id>-work", "target": "<id>-closure", "movement": "forward"},
    {"edge_ref": "edge:<id>-closure-to-boundary", "source": "<id>-closure", "target": "building-boundary:<id>-closed", "movement": "forward", "building_lifecycle": {"state": "closed", "reason": "declared graph closed"}}
  ],
  "groups": []
}
```

build 결과 packet은 `build_input_mode`, `building_id`, `evidence_root`, `frontier_kind`,
`worktree_path` 같은 support evidence를 보여준다. 이것은 source truth, success/quality
judgment, 또는 Link Movement 선택이 아니다.

## 발사 전 DSL 구조 규칙 (0702 엔진 실측 — 재발사 루프 방지)

발사 실패의 대부분이 이 두 가족이다. 그리기 전에 확인하고, 에러가 나면 아래 표에서 메시지로 찾아라.

**fan() 위치 3법칙** (`support/operator/assembly.py` build() 하강부 실측):
1. fan 블록 **바로 뒤는 반드시 단일 수렴 노드**다. fan 뒤에 fan을 붙이면
   `a fan() block needs a following convergence node`. 두 팬 사이에 수렴 브릭(review/closure 등) 1개를 넣어라.
2. build() 리스트는 **fan으로 끝날 수 없다**: `build() cannot end with a fan() block`.
3. fan이 첫 항목인 것은 **허용**된다(가지=병렬 루트, 다음 항목=수렴). `route=` 마크는 수렴 노드에만 —
   가지에 달면 `route= is a fan-in opt; declare it on the convergence node, not a fan branch`.

**write_scope 승계 2법칙** (`_validate_node_write_scope_subset` 실측):
1. write_scope 매핑은 `allowed_paths`(비어있으면 안 됨) + `forbidden_paths`(빈 배열이라도 키 자체 필수) 둘 다 요구한다.
2. 노드별 스코프를 좁힐 때: 노드 allowed는 그래프 allowed glob에 커버되는 부분집합이어야 하고,
   그래프 forbidden_paths는 **전부 문자 그대로** 노드 forbidden_paths에 포함해야 한다.

**에러 → 처방 표:**

| 에러 (부분 문자열) | 처방 |
|---|---|
| `needs a following convergence node` | 두 fan 사이에 수렴 브릭 1개 삽입 |
| `cannot end with a fan() block` | 마지막에 closure 등 수렴 노드 추가 |
| `a Fan block cannot be coerced to a node` | fan을 노드 자리(가지 안 등)에 넣었음 — build() 항목으로만 |
| `route= is a fan-in opt` | route=를 가지에서 수렴 노드로 이동 |
| `allowed_paths must be a proven subset` | 노드 allowed를 그래프 allowed glob 안쪽으로 좁힘 |
| `must preserve assemble() write_scope forbidden_paths` | 그래프 forbidden 전체를 노드 forbidden에 복사-포함 |
| `write_scope.forbidden_paths must be an array` | `forbidden_paths: []`라도 키를 명시 |
| `brick() got unexpected keyword argument(s): label` | 직접 `brick()` 호출은 `alias=` — `label`/`effort` 별칭은 build() 노드 리터럴 `[kind, work, opts]` 전용 |
| `ModuleNotFoundError: No module named 'support'` | `PYTHONPATH=support/import_identity:.` — repo 루트(`:.`) 누락이 원인, cd만으론 부족 |
| `route= must be a list of reroute()/hold() marks` 등 route 계열 | route=는 fan 수렴 노드에만, reroute()/hold() 마크 리스트로 |
| `require exactly one outgoing completion edge` 등 gates 계열 | per-node gates 단 노드는 outgoing edge 1개(분기점에 달지 마라), human-review/coo-review만 |
| write_scope 경로 상세 거부 (절대경로/`..`/.git·.env·.pem·secret·token 세그먼트/bare dir) | 상대 glob만, 금지 세그먼트 회피, 디렉토리는 `dir/**` 꼴 |
| `brick kind ... repeats; declare alias=` | 같은 kind를 직접 brick()으로 반복 선언 시 alias= 부여 (build() sugar는 자동 mint) |
| `declared_by must be bare text ... colon is not admitted` | declared_by는 `coo-smith` 꼴(콜론 금지) — 콜론 ref는 author_ref에 |

올바른 이중 fan + write_scope 승계 예시:

```python
graph([
    brick("design", "범위를 좁혀라"),
    fan([
        brick("work", "영역 A만 변경", write=True),
        brick("work", "영역 B만 변경", write=True),
    ]),
    brick("review", "두 레인 반환 대조"),      # ← fan 뒤 수렴 노드 (필수)
    fan([
        brick("code-attack-qa", "구현 공격"),
        brick("axis-attack-qa", "축 위반 공격"),
    ]),
    brick("closure", "종합·판정"),             # ← 마지막 = 수렴 노드 (필수)
])
# 발사 write_scope={"allowed_paths": ["support/operator/**"], "forbidden_paths": [".git/**"]}
# 노드 스코프를 좁히면: allowed ⊂ 위 glob + forbidden에 ".git/**" 그대로 포함
```

## 발사 직전 체크리스트 (5행 — 본문에 흩어진 함정을 한 화면으로)

1. `cd <활성 체크아웃>` 절대경로 명시 — 셸 cwd 리셋 트랩. 발사 명령 앞에 항상.
2. `set -a; source ~/.brick/report.env; set +a` — 벨+대시보드. resume 전에도 동일.
3. `output_root` — one-call `build()`는 `~/.brick/goal-runs/`에 하드코딩한다(0702 실측, `_build_output_root`) = 슬랙 벨 끊김. 벨이 필요하면 `run_goal_approve_entry(output_root=REPO/project/brick-protocol/buildings/...)`로 발사하거나 goal-runs 산출을 발사자가 직접 회수.
4. 쓰기 노드 = 노드 `write=True` + 발사 `write_scope` **둘 다** (하나만이면 read-only smoke). glob은 `support/operator/**` 꼴 (★`support/` 금지 = fnmatch 함정).
5. `adapter_timeout_seconds` 상향 — one-call build() 기본 120초는 정독/구현 레인에 짧다. resume엔 `adapter_cwd=<워크트리>` 절대 누락 금지.
6. one-call `build()`엔 `gates=`/`write_scope=`/`output_root=` 인자가 **없다**(0702 실측) = 항상 완전무인 + 기본 워크트리 스코프 + goal-runs(벨 단절) + 완료 시 워크트리 자동처분(sandbox commit_sha만 남음 — 반드시 회수). 사람 게이트는 per-node `brick(gates=...)`, 좁은 스코프는 `node_write_scope=`, 벨/경로 지정은 `run_goal_approve_entry(output_root=...)` 계층으로.

## 알아둘 것

- **assemble의 top-level `adapter=`는 roled 노드에 무효.** design/closure/review/QA는 Agent Object와 per-node override가 이긴다. 현재 dogfood 기본(0630 채택 — 날짜 조건부 로직 아님, 서술일 뿐)은 work+closure+code QA=codex-local, axis/evidence/review QA=gemini-local이다. 노드를 role 디폴트에서 옮기려면 **per-node** `brick("design","...", adapter="codex-local")` override만이 레버.
- **Claude adapter는 active다(0702 실사용).** per-node `adapter="claude-local"` override로 즉시 사용 가능. dogfood 기본 풀은 **codex=구현/closure/code QA · gemini=axis/evidence/review QA · QA fan=codex+gemini**, claude는 override로 정독/합성 등에 투입.
- **캐스팅 다이얼 어휘(실측, agent/spec.py EFFORT_LEVELS/EFFORT_SCOPE):** `effort=`는 {none, minimal, low, medium, high, xhigh} (bare `"xhigh"` 또는 `"effort:xhigh"` ref형). 적용 어댑터는 codex-local/codex-fugu-local/claude-local뿐 — gemini는 다이얼 자체가 없어 선언하면 out-of-scope. `model=`은 SHAPE 검증(`model:<provider>:<name>` 꼴), 예: `model:claude:sonnet`, `model:claude:opus`.
- **verdict 노드는 `adapter:local` 금지.** design/closure/review/inspect는 verdict-bearing → `adapter:local` 거부. local 스텁 무인발사는 **work 노드로만** 가능. verdict 노드는 진짜 CLI(codex/gemini/claude) 필요.
- **부하 주의.** raw graph packet CLI 입력은 retired다. 검증은 가능하면 DSL/materialization 체크로, 진짜 실행이 필요하면 `adapter:local` 또는 단일 `codex-local`/`gemini-local` 노드 1개로.
- **QA 주의.** QA는 inspect/probe evidence를 만들 수 있지만 source-truth mutation 권한이 아니다. QA source mutation이 관찰되면 HOLD로 보고한다.

## 게이트 진실 (실측)
- `gates=()` ⇒ **완전 무인**(최종 closure→boundary 포함 전 edge가 `link-gate:default-transition`만 달고 자동전진).
- `gates=("human-review",)` ⇒ **최종 boundary edge에만** HOLD. 중간 design→work는 그대로 auto.
- top-level `gates=("coo-review",)`(assemble 프로파일 경로)는 link-gate ref만 붙이고 **HOLD 안 박음** — 머지에서 진짜 멈추려면 `human-review`.
- **per-node는 다르다(0702 실측, `_node_gate_sequence_entry`)**: `brick(..., gates=("coo-review",))`는 coo-review도 human-review도 **HOLD를 박는다**(owner=coo/caller-or-coo). 노드 단위 사람게이트는 per-node로. gates 단 노드는 outgoing completion edge가 정확히 1개여야 한다.
- 프리셋도 박음: `engine-feature-hard`=design→work HOLD; `fast-fix`/`quick-check`는 안 박음.
- 홀드된 빌딩은 `observe_building_frontier`로 보이고 `resume_building_plan`으로 전진.

---

# 발사 후 — 게이트는 내가 한다 (codex green 안 믿음)

- 워크트리에서 `REAL HOME에서 `PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all > /tmp/<id>-all.txt 2>&1` 실행 후 rc/pass count/failure-marker count만 보고 + 포커스 체커 green + **변이 RED 직접 확인**.
- build 결과는 support evidence다. closure가 엉키면(temp-HOME concern 연쇄→resume divergence) **추격 금지** — 코드만 독립검증되면 declared follow-up Building으로 처리한다.
- 미완/홀드 빌딩은 untracked로 `--all`을 RED로 만듦 → merge·게이트 전 `mv project/.../buildings/<미완id> /tmp/`로 치움(비파괴).
- 라이브 repo를 다른 세션/빌딩과 공유 중이면 게이트 지문이 시점마다 흔들린다(0702 실측: 병행 아카이브로 같은 프로파일 실패 6→1→0). 공유 중 측정은 detached 워크트리에서 하거나, 내 변경만 stash로 걷어낸 baseline과 실패 지문 diff로 무죄/유죄를 가려라.

---

# PHASE 3 — 홀드/실패/스톨 분류 (걸렸을 때만)

빌딩이 홀드 벨(intervention-required)·걸음 복귀·타임아웃·resume 거부·게이트 RED에 빠지면
**도장 찍기 전에 먼저 분류한다.** 원칙: **도장보다 분석이 먼저.** 모든 판단은 장부(증거)에서만.
빌딩 루트는 읽기 전용 — 분석 중 어떤 파일도 수정하지 않는다. 실험은 /tmp 사본에서만.

## 3.1 증거 수집 (전부 읽기 전용)

빌딩 루트 = build 결과 packet이 반환한 `evidence_root`.

```bash
# (a) 마지막 홀드 행: raw/link.jsonl에서 transition_lifecycle_state=paused 마지막 행
#     → raw_ref, pending_target_ref, reason_refs, required_disposition_owner
# (b) 어댑터 에러: raw/adapter-error.jsonl 존재 여부 + message_excerpt
# (c) 영수증 균형: raw/agent-received.jsonl 행수 vs raw/agent-return.jsonl 행수
# (d) 걸음 타임라인: work/step-outputs/* mtime 순서 (어느 스텝까지 왔나)
# (e) 프로세스 생존: ps -axo pid,etime,command 에서 codex exec --cd <워크트리>
# (f) 런처 로그 tail (0바이트=버퍼링, 죽은 게 아님)
# (g) codex 산출 캡처: lsof로 bp-codex-cli-*.txt 크기 (0바이트 장시간 = 스톨)
```

## 3.2 원인 가족 분류 (0612 실측 분류표)

| 가족 | 식별 신호 | 처분 권고 |
|---|---|---|
| **정상 사람게이트** | reason_refs에 `gate-sequence`+`link-gate:human/coo` | 해당 스텝 반환물 검수 → 합격이면 forward 도장 |
| **반환 양식 위반** | adapter-error에 `forbidden return key` (예: status 키) | forward 재시도 1회. 같은 키로 2회+ 반복 = 템플릿/지시문 유도 결함 의심 → 소수선 후보 보고 |
| **어댑터 스톨/타임아웃** | codex 살아있는데 산출 0바이트 30분+, 또는 TimeoutExpired | ① **로우 먼저**: `ps -o time`(CPU)·`pgrep -P`(도구자식)·`lsof -a -p PID -i`(소켓 — **-a 필수**) ② **소켓 0+CPU 0+자식 0 = 죽은 접속(무재시도 행)** → 즉시 회수+재발주, 발주 후 2~3분 소켓 체크 동반 ③ 소켓 살아있으면 작업 중 — 기다림 ④ 반복 스톨이면 task 문장 무게 의심 → 좌표+경계 박아 재발주 |
| **출생증명서 누락** | resume이 `declared-building-plan.json ... absent` 거부 | 같은 intent로 `overwrite_existing=True` 재발주 (손으로 파일 써넣기 금지) |
| **증거 불일치 게이트 RED** | `raw_ref does not resolve through raw manifest` 류 | 증거 커밋 보류, 결함 빌딩 발주. 핀 완화 절대 금지 — 체커가 옳다 |
| **방치 어댑터-에러 홀드** | 오래된 홀드 + 일은 딴 데서 완성 | ⚠ stop 처분은 멈춘 스텝을 LIVE 재실행함 — 종이-stop 생기기 전까지 함부로 stop 금지 |

## 3.3 처분 실행 규칙

- forward/stop 처분 행 append 후 `resume_building_plan(ROOT, adapter_cwd=<워크트리>, adapter_timeout_seconds=3600)`.
- **adapter_cwd 절대 누락 금지** — 누락 시 codex가 실repo를 작업장으로 받는다 (0612 실측).
- resume 전 `set -a; source ~/.brick/report.env; set +a` — 벨+대시보드 자동.

## 3.4 스톨 사건 귀속 주의 (Smith 0613 정본)

스톨은 **단독 귀속 금지** — 반드시 3축 복합 점검: Agent(반환위반·provider) × Link(처분경로) ×
support(기록 구조 — 출생증명서·벨 순서·transcript·잔재). "왜 멈췄는지 증명 못 하는 구조" 자체가
결함의 본체일 수 있다. 정본: project/brick-protocol/status/kernel/stall-attribution-amendment-0613.md

## 3.5 보고

Smith 5문 형식 축약: ① 무슨 가족인지 한 문장+비유 ② 식별 근거(실측 행/값) ③ 한 처분 ④ 안 한 것
⑤ 반복되면 누가 잡나(체커/소수선). 새 가족 발견 시 이 분류표에 행을 추가한다.

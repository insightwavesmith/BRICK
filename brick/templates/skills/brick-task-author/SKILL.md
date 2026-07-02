---
name: brick-task-author
description: BRICK 빌딩 발주 한 스킬 — PHASE 1 task 본문 쓰기 → 입력 모드 결정(프리셋/DSL 그래프) → PHASE 2 공식 빌딩 build 입력 → PHASE 3 홀드 분류(걸리면). 새 빌딩 발주, 수리·기능·부검 task를 쓸 때 이 절차로. 모양 사이징은 building-sizing-method 스킬.
---

# BRICK 발주 (운영자 표준, 3-PHASE)

> 현재 호출자가 준 활성 체크아웃과 활성 vessel evidence root를 기준으로 발사·측정·코드수정한다.
> old hardcoded operator-local paths 및 the frozen history repo 문구는 현재
> Customer-Ready Goal v3와 충돌하면 역사/박물관 증거다.
> **법의 단일 출처 = repo 루트 `BRICK-CONSTITUTION.md`** (3축·support 무판단·최소 그래프 등
> 불변법 — 발주 전에 한 번 읽어라. release export에 포함되는 유일한 법 문서다.)

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
(`support/operator/assembly.py`) plus `run_building_plan()`이다. graph packet JSON을
`brick build --graph <packet>` 또는 `support.operator.cli build --graph <packet>`에 넘기던
저수준 CLI escape hatch는 retired다. `sibling_independence`, per-node `write_scope`
narrowing, mid-graph human/coo gates는 이제 DSL gap이 아니다.
Profile compatibility note: `brick build --graph <packet.json>` /
`support.operator.cli build --graph <packet.json>`, "같은 공식 route의 저수준 입력", "같은 공식 build surface로 들어가는 두 입력 모드" are retained once as historical checker text.
P3 이후 zero-ritual 운영자 경로는 `task_intake` 확인 뒤 **`build()` 하나로** compact graph를
넣는 것이다. 운영자-facing 언어는 `build()`다. `fan()`은 병렬 블록 재료이고
`fire()`/`launch_assembled_building`은 내부 구현·debug/advanced 용어다. helper를 별도 공식 route처럼 말하지 마라.

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

발주 공개 surface = **공식 빌딩 build surface 하나**다. 프리셋은 task/preset 입력으로,
그래프는 DSL graph 입력으로 materialize되며, 둘 다 Builder/materializer → declared Building
Plan → `support/operator/run.py` walker → active vessel evidence root → reporter/Slack/frontier로
간다. `assemble`과 launch helper들은 graph/materialization helper이지 별도 실행 route가 아니다.

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

design-first fan-out 또는 DSL graph로 설명한다. 그래도 Link가 Movement authority를 소유하고,
support/model/checker/Slack은 source truth나 quality/success judge가 아니다.

---

# PHASE 1 — task 본문 쓰기

## 엔진이 task.md에서 진짜 요구하는 것 (실측)

| 필드 | 진실 |
|---|---|
| 노드 `work=` | **유일한 구조적 필수.** `brick("work","<한 줄>")`. 빠지면 CompositionError. returns/alias/comparison_rule은 build()가 자동채움 — 쓰지 마라. |
| 빌딩 `task=` | 비어있지 않은 텍스트 ≤64KB면 됨. **안의 heading 하나도 엔진 검증 안 함** — sha256 후 `work/task.md`로 그대로 쓰여 에이전트 프롬프트가 됨. |
| 그 외 | 모든 섹션은 에이전트 행동용(admission용 아님). write hand는 두 잠금: 노드 `write=True` + launch `write_scope`. `write_scope`만 넘기면 scope가 찍히지 않아 read-only가 정상이다. adapter/model/gates는 assemble()/fire 인자(task.md 안 아님). |

**스톨 레버(실측 0615):** 엔진은 task.md를 불투명 텍스트로 보며, 지연 차이는 에이전트
읽기범위가 bounded인지에서 난다. 레버 = 모듈·영역 단위 바운디드 스코프 한 줄. file:line은
fallback이며, §AUTO 읽기목록 산출은 design 노드의 일이다.

**task.md 주입 없음(0702 실측):** `task=`/`goal=`은 `work/task.md` **증거물**로만 쓰이고, 어떤 경로도 레인 프롬프트에 주입하지 않는다. 레인이 반드시 봐야 할 계약(반환 스키마·경계·금지선)은 각 노드 `work_statement`에 직접 박아라. 프리셋 materializer 요약도 `## First-Line Contract`/`## Objective`/`## Desired Outcome` 헤딩만 스캔한다.

## 샤프 템플릿 (이대로 — 더 보태지 마라)

```
# <한 줄 제목: 결함번호 또는 기능명>

## Objective
<불변식 한 문장: "이후 X는 Z일 때도 항상 Y다.">

## Required Sources (실측 근거 — 착수 전 실제로 읽은 파일 전수 나열)
<이 task를 쓰기 전 직접 grep/read한 파일을 file:line까지 하나씩 나열. 산문에 묻지 마라 —
 체크리스트로 뽑아놓으면 "읽은 범위보다 write_scope가 좁은가"가 스스로 드러난다(0702
 실측: returns-persistence가 support/connection/만 grep하고 support/recording/의 진짜
 배선처를 놓쳐 write_scope 누락 → work 5라운드 허비). 이 리스트 밖의 write_scope 경로가
 있으면 그 자체가 위험 신호 — 다시 조사하거나 design에 확정을 넘겨라.>

## Brick / Agent / Link Boundary (1줄씩 — 조사 없이 바로 아는 계약 사실)
<이 task에서 Brick(계약)이 정확히 뭘 소유하나 — 특히 "정확히 어느 함수/어느 진입점"까지
 모호함 없이. Agent(수행)가 뭘 받고 뭘 반환하나. Link가 뭘 기록할 수 있나. 0702 실측:
 llm= 별칭 1차가 "brick(..., llm=...) 파라미터"라고만 쓰고 정확한 호출 형태를 안 박아서
 work가 다른 해석(리스트 리터럴 DSL)으로 갔다 — 2회 반려 후에야 복붙 코드블록으로 못박음.>

## Context (자급자족·실측 — 어디 보고 어디는 안 보나)
<중요 표면을 모듈·영역 단위로 지명: 본뜰 파일·선례·무는 제약 하나.
 실측값(재현 행·ref·에러) 있으면 인라인. 마지막 줄 "다른 모듈은 훑지 마라." ← anti-stall 레버>

## Deliverables (번호)
1. <변경 본체>
2. <체커 핀: 픽스처+변이 RED 보임, 없으면 왜 없는지 한 줄>

## Read Scope / Write Scope (Hard constraints에서 분리 — Required Sources와 대조하며 쓸 것)
<read_scope는 대개 Required Sources+Context가 지명한 범위. write_scope는 glob 전수
 열거("support/operator/**" 식, ★"support/" 단독 금지 = fnmatch 함정). Required Sources에
 없는 폴더가 write_scope에 있거나(발명), write_scope에 없는 폴더를 Required Sources가
 가리키면(누락) — 둘 다 재검토 신호.>

## Proof required (직접 실행·정직 보고 — 주장은 실행 결과만)
<포커스 체커 green + 변이 RED → check_profile.py --all은 /tmp 로그로 저장하고 rc/pass/failure-marker만 요약 → (코드면) compileall + git diff --check.
 구현 task면 발주자가 직접 실행할 반려 시나리오 프로브 명령을 RED 기준으로 명시(0702 가짜 랜딩 교훈).
 **새 인터페이스/신규 진입점이면 복붙 가능한 리터럴 성공 명령 + 리터럴 거부 명령을 코드블록으로 박아라**
 (일반적 "확인해라" 문구 금지 — 해석의 여지를 없앤다. 0702 실측: llm= 2차가 일반 문구로
 썼다가 다른 해석으로 반려, 3차에서 리터럴 코드블록 강제 후 통과).

## Hard constraints (law)
<금지선: 실루트 수정 / 핀 완화 / 스케줄러·신규의존성 / project/ 손대기.
 구현 deliverable 있으면 필수 조항: "write_scope 안 diff 실물 없이 complete 반환 금지 — implementation_gap concern">
```

인터뷰가 필요한 고객 기원 task(사람과 대화 루프로 요구사항을 뽑아야 하는 경우)는 이 샤프
템플릿이 아니라 `task_intake` 스킬 + `brick/templates/tasks/source-template.md`(Deep
Intake Result·Human/Review Gate·Risk 포함 정본)를 쓴다 — 용도가 다르다, 섞지 마라.

부검은 `project/brick-protocol/status/kernel/evidence-postmortem-task-template-0612.md`를 쓴다.

## 그래프 모양은 building-sizing-method 스킬

그림→코드 번역은 **building-sizing-method** 스킬이 맡는다. 새 모양이면 먼저 `GraphSpec`을
얻고, 여기 PHASE 2로 와서 발사한다. 운영자의 일 = 모양 판단 하나.

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

사용자·COO 표면에서는 **Link row를 직접 쓰지 않는 것**이 맞다. 이것은 "모든 edge가 자동
route"라는 뜻이 아니다. compact `build()`/`fan()`은 인접 edge를 materialize할 때 기본
`movement="forward"`를 만든다.

```text
사용자 표면: Link row 안 씀
support materializer: Link row를 만든다
기본 Movement: forward = 선언된 길을 계속 감
reroute/HOLD: concern evidence + 선언/채택된 route policy가 있을 때만
```

QA/closure가 blocker를 낼 수 있는 fan-in 그래프에서 decorative all-forward 그래프로 끝냈다고
route-default를 증명했다고 말하지 마라. 필요한 모양은:

```text
work/design → fan(QA lanes) → closure-synthesis
closure-synthesis만 Link-facing transition_concern_evidence를 반환
Link/COO가 declared policy(route-policy:qa-basic-repair 등)나 convergence route= mark를 보고
forward / reroute / HOLD 중 하나를 채택
```

hard fan-in QA에서 QA lane은 Movement를 고르지 않는다. QA는 관찰을 반환하고 closure가 concern
evidence를 종합한다. ambiguous / conflicting / unresolvable / budget-exhausted는 HOLD 후보다.

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

write_scope가 필요한 구현 Building이면 one-call `support.operator.build()`가 숨기는 발사 인자와
write hand를 먼저 확인한다. 디버그/감사에서도 기본 운영 언어는 `build()`다.

`write_scope`만 넘기고 work 노드에 `write=True`가 없으면 assembly가 scope를 찍지 않으므로
Agent는 read-only grant를 받는다. 그 경우 `frontier=complete`라도 `made_changes=false`가
나올 수 있으며, 이것은 발사자 그래프 선언 문제다.

`fire()`는 내부 sugar일 뿐 운영자-facing 발주 언어가 아니다. 별도 runtime, direct launch runner, phase runner,
proof, 또는 Movement route도 아니다. 기본 프롬프트와 골 운영 문구는 `build()`만
말한다.

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

build 결과 packet의 `build_input_mode`, `building_id`, `evidence_root`, `frontier_kind`,
`worktree_path`는 support evidence다. source truth, success/quality judgment, Link Movement
선택이 아니다.

## 발사 전 DSL 구조 규칙 (0702 엔진 실측 — 재발사 루프 방지)

발사 실패 대부분은 아래 두 가족이다. 그리기 전 확인하고 에러는 표에서 찾는다.

**fan() 위치 3법칙** (`support/operator/assembly.py` build() 하강부 실측):
1. fan 블록 **바로 뒤는 반드시 단일 수렴 노드**다. fan 뒤 fan은
   `a fan() block needs a following convergence node`; 중간에 review/closure 등 수렴 브릭 1개.
2. build() 리스트는 **fan으로 끝날 수 없다**: `build() cannot end with a fan() block`.
3. fan이 첫 항목인 것은 **허용**된다(가지=병렬 루트, 다음 항목=수렴). `route=` 마크는 수렴 노드에만 —
   가지에 달면 `route= is a fan-in opt; declare it on the convergence node, not a fan branch`.

**write_scope 승계 2법칙** (`_validate_node_write_scope_subset` 실측):
1. write_scope 매핑은 `allowed_paths`(비어있으면 안 됨) + `forbidden_paths`(빈 배열이라도 키 자체 필수) 둘 다 요구한다.
2. 노드별 스코프를 좁힐 때: 노드 allowed는 그래프 allowed glob에 커버되는 부분집합이어야 하고,
   그래프 forbidden_paths는 **전부 문자 그대로** 노드 forbidden_paths에 포함해야 한다.

**write_scope는 COO의 사전 조사만으로 정밀하게 못 맞출 수 있다** (0702 실측: returns
전문 보존 빌딩 — COO가 grep 하나로 배선처를 좁혀 write_scope를 확정했는데, 실제 배선은
그 밖의 폴더 하나에 더 있었다. work가 attempt-3 자기 보고서에 "필요한데 write_scope
밖"이라 실토할 때까지 3라운드를 허비하고 결국 허용된 좁은 구역 안에서 약한 우회로
귀결됐다 — Link의 write_scope 강제 자체는 설계대로 작동했다, 문제는 애초에 그은 경계선
이 방 하나를 빼먹은 것). 현재 엔진은 `candidate_file_changes`/`reading_scope_map`
(design 반환 필드, 있음)을 work의 실제 write_scope로 **역산하지 않는다** —
node_write_scope는 assemble()/build() 호출 시점에 COO가 고정하고, design이 나중에
뭘 알아내도 그 경계는 안 바뀐다(엔진 개선 후보, 미착수). **오늘부터 관행 교정**: 대상
파일 배선을 COO 자신이 완전히 확신 못 하면, write_scope는 **의심되는 하위시스템
전체**로 넓게 잡고(예: 폴더 하나가 아니라 그 폴더가 속한 상위 트리), task 본문에
"design의 candidate_file_changes/reading_scope_map이 실제 작업 경계다 — work는 그
밖을 스스로 자제하라"를 명시 지침으로 박아라. code-attack-qa 공격 항목에 "design이
지목 안 한 파일까지 손댔는지"를 추가해 사후 검사로 대체한다(하드 벽 대신 소프트
규율+검사).

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
| write_scope 경로 상세 거부 | 상대 glob만, 금지 세그먼트 회피, 디렉토리는 `dir/**` 꼴 |
| `brick kind ... repeats; declare alias=` | 같은 kind를 직접 brick()으로 반복 선언 시 alias= 부여 (build() sugar는 자동 mint) |
| `declared_by must be bare text ... colon is not admitted` | declared_by는 `coo-smith` 꼴(콜론 금지) — 콜론 ref는 author_ref에 |

## 발사 직전 체크리스트 (5행 — 본문에 흩어진 함정을 한 화면으로)

1. `cd <활성 체크아웃>` 절대경로 명시 — 셸 cwd 리셋 트랩. 발사 명령 앞에 항상.
2. `set -a; source ~/.brick/report.env; set +a` — 벨+대시보드. resume 전에도 동일.
3. `output_root` — one-call `build()`는 `~/.brick/goal-runs/`에 하드코딩한다(0702 실측, `_build_output_root`) = 슬랙 벨 끊김. 벨이 필요하면 `run_goal_approve_entry(output_root=REPO/project/brick-protocol/buildings/...)`로 발사하거나 goal-runs 산출을 발사자가 직접 회수.
4. 쓰기 노드 = 노드 `write=True` + 발사 `write_scope` **둘 다** (하나만이면 read-only smoke). glob은 `support/operator/**` 꼴 (★`support/` 금지 = fnmatch 함정).
5. `adapter_timeout_seconds` 상향 — one-call build() 기본 120초는 정독/구현 레인에 짧다. resume엔 `adapter_cwd=<워크트리>` 절대 누락 금지.
6. one-call `build()`엔 `gates=`/`write_scope=`/`output_root=` 인자가 **없다**(0702 실측) = 항상 완전무인 + 기본 워크트리 스코프 + goal-runs(벨 단절) + 완료 시 워크트리 자동처분(sandbox commit_sha만 남음 — 반드시 회수). 사람 게이트는 per-node `brick(gates=...)`, 좁은 스코프는 `node_write_scope=`, 벨/경로 지정은 `run_goal_approve_entry(output_root=...)` 계층으로.
7. (0702 저녁 해소) 병행 발사·홀드 모두 안전 — reap liveness(bec5b16)+WIP 보존(0741a56) 랜딩. 미완/홀드 빌딩의 작업물은 `refs/brick/wip/<building_id>`에서 회수(`git log <ref>` → checkout). 홀드는 raise/forward로 처분하면 된다.

## 알아둘 것

- **assemble의 top-level `adapter=`는 roled 노드에 무효.** design/closure/review/QA는 Agent Object와 per-node override가 이긴다. dogfood 기본은 work+closure+code QA=codex-local, inspect/axis/evidence QA=claude-local sonnet·xhigh, review QA=gemini-local이다. 옮기려면 per-node override.
- **Claude adapter는 active다(0702 실사용).** inspector 레인 기본이자 per-node `adapter="claude-local"` override로 어디든 투입 가능. 3-way 풀: **codex=구현/closure/code QA · claude=조사/축·증거 QA · gemini=review QA**.
- **캐스팅 다이얼 어휘:** `effort=`는 {none, minimal, low, medium, high, xhigh}; 적용 어댑터는 codex-local/codex-fugu-local/claude-local뿐. `model=`은 `model:<provider>:<name>` 꼴.
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

- 워크트리에서 `PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all > /tmp/<id>-all.txt 2>&1` 실행 후 rc/pass count/failure-marker count만 보고 + 포커스 체커 green + **변이 RED 직접 확인**.
- build 결과는 support evidence다. closure가 엉키면(temp-HOME concern 연쇄→resume divergence) **추격 금지** — 코드만 독립검증되면 declared follow-up Building으로 처리한다.
- 미완/홀드 빌딩은 untracked로 `--all`을 RED로 만듦 → merge·게이트 전 `mv project/.../buildings/<미완id> /tmp/`로 치움(비파괴).
- 라이브 repo를 다른 세션/빌딩과 공유 중이면 게이트 지문이 시점마다 흔들린다(0702 실측: 병행 아카이브로 같은 프로파일 실패 6→1→0). 공유 중 측정은 detached 워크트리에서 하거나, 내 변경만 stash로 걷어낸 baseline과 실패 지문 diff로 무죄/유죄를 가려라.
- 수동/레거시 워크트리에서 게이트 변이·복원 조작 전에 **작업물부터 커밋**하라 — 미커밋 워크트리에 `git checkout --` 복원은 작업물을 지운다(0702 실측, COO 자가 유실 1회). 커밋 위에서만 변이가 안전하다.
- 게이트의 closure 대조는 **task Deliverables 번호별 전수**로 한다 — 포커스 green·변이 RED·스윕이 전부 통과해도 deliverable 하나가 통째로 미구현일 수 있다(0702 3차 유실 실측: reaper 빌딩 deliverable 2 누락 랜딩).
- 구현 deliverable은 **diff 실물(file:line) 대조 + 반려 시나리오 직접 프로브**까지 — 체커 pin green은 이미-작동하는 경로만 pin했을 수 있다(0702 실측: default-route 1차가 pin +189줄만 넣고 엔진 무변경 complete 자기보고; COO 무선언 compact 프로브 3필드 null로 반려).

---

# PHASE 3 — 홀드/실패/스톨 분류 (걸렸을 때만)

빌딩이 홀드 벨(intervention-required)·걸음 복귀·타임아웃·resume 거부·게이트 RED에 빠지면
**도장 찍기 전에 먼저 분류한다.** 원칙: **도장보다 분석이 먼저.** 모든 판단은 장부(증거)에서만.
(아래 인용된 status/kernel 문서들은 이 체크아웃의 역사 근거다 — release export 미포함.
분류표·절차의 정본은 이 스킬 본문이므로 문서 부재 시에도 기능은 완결된다.)
빌딩 루트는 읽기 전용 — 분석 중 어떤 파일도 수정하지 않는다. 실험은 /tmp 사본에서만.

## 3.0 항상 먼저 던지는 질문 (3축 + 엔진 — 처분보다 먼저)

실무(반복 재발주)에 빠지면 운영자 관점이 사라진다 — 처분 내기 전에 매번 이 4갈래를
스스로 자문한다. 전부 0702 실측 사고가 근거(추상 원칙 아님):

- **Brick(계약)**: 이 실패가 계약의 틈(허용돼 있었음) 때문인가, 명시했는데 무시됐기
  때문인가?(postmortem-default-route-fake-landing-0702.md §2 판정 방식) 성공 기준을
  리터럴 복붙 명령으로 못박았나, 해석 여지가 있는 산문이었나?(llm-alias v2 "brick(...,
  llm=...) 파라미터" 문구가 두 가지로 읽혀 반려 2회) COO가 Required Sources로 실제
  읽은 범위가 write_scope보다 좁지 않았나?(returns-persistence 1차, support/recording/
  누락으로 5라운드 허비)
- **Agent(수행)**: 이탈이 최초 어느 레인에서 시작됐고, 뒤 레인(QA)이 그걸 공격 목록에
  넣어 잡았나 방치했나? 자기보고(returned)가 스스로 문제를 실토했는데 판정(closure)이
  그걸 무시하고 complete로 갔나?(default-route v1 — "no local diff exists" 자기 기록
  하고도 완주)
- **Link(이동/게이트)**: write=True 노드의 complete에 diff 실물을 내가 직접 확인했나,
  자기보고·체커 green만 믿었나? 처분 클래스를 먼저 확인했나 — hold_reason이
  budget_exhaustion이면 raise, 그 외(예: runtime_handoff_address_unresolved_in_ledger)면
  forward(0702 실측 2회 오판, walker_resume.py:410 `_require_budget_exhaustion_raise`가
  잘못된 raise를 명시 거부)?
- **엔진(support 기반)**: 지금 이 홀드가 콘텐츠 문제(레인이 뭘 잘못 짬)인가, 엔진 자체
  결함(resume/disposition 메커니즘 — 0702 하루에만 3종: 예산 미소비/처분 자기잠금/
  resume corrupt evidence)인가? 후자면 같은 그래프 모양에서 반복 재현되는지부터
  확인하고, 더 안 파고 fresh 재발주로 우회한다(resume을 억지로 밀어붙이지 마라).
  격리 워크트리에서 직접 재현했나, vessel 자기보고만 믿었나?

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
| **워크트리 reap 파괴 (0702 원인 확정)** | adapter-error `error_kind=local_cli_missing` + 워크트리 경로 부재 | 원인: `reap_stale_worktrees()`에 생존 검사 없음 — 새 샌드박스 생성(다른 발사·체커 픽스처)이 도는 빌딩 워크트리를 전부 제거. `git fsck --lost-found`에 그 빌딩 커밋 있으면 회수, 없으면 재발주. **liveness 게이트 수리 전까지 빌딩 실행 중 발사·체커 실행 전면 금지.** 정본: onecall-worktree-loss-incident-0702.md |
| **미완 처분 작업물 유실 (0702)** | `frontier=agent_incomplete` + `worktree_disposed=true` + `commit_sha` 빈값 | 완료 시에만 커밋하는 설계라 미완 처분 = 작업물 소멸 + resume 불가(adapter_cwd 소멸). agent-return의 주장 기록만 회수 가능 → 재발주가 정답. 미완 빌딩 발견 시 처분 전에 워크트리 실존부터 확인 |

## 3.3 처분 실행 규칙

- forward/stop 처분 행 append 후 `resume_building_plan(ROOT, adapter_cwd=<워크트리>, adapter_timeout_seconds=3600)`.
- **adapter_cwd 절대 누락 금지** — 누락 시 codex가 실repo를 작업장으로 받는다 (0612 실측).
- resume 전 `set -a; source ~/.brick/report.env; set +a` — 벨+대시보드 자동.
- **예산 주입(0702 실전 검증)**: `run_approve_entry(ROOT, action="raise", author_ref="coo:smith", budget_increment=N, adapter_cwd=<격리경로>)` — "예산 미선언" 홀드는 `budget_exhausted`로 분류돼 raise 대상. concern 접수·완주는 `action="forward"`. 기본 예산 5는 brick/templates/reroute-defaults.yaml(Smith 선언) — compact DSL 자동 적용은 인체공학 4번 대기.

## 3.4 스톨 사건 귀속 주의 (Smith 0613 정본)

스톨은 **단독 귀속 금지** — Agent(반환위반·provider) × Link(처분경로) × support(기록 구조)를
함께 점검한다. 정본: project/brick-protocol/status/kernel/stall-attribution-amendment-0613.md

## 3.5 보고

Smith 5문 형식 축약: ① 무슨 가족인지 한 문장+비유 ② 식별 근거(실측 행/값) ③ 한 처분 ④ 안 한 것
⑤ 반복되면 누가 잡나(체커/소수선). 새 가족 발견 시 이 분류표에 행을 추가한다.

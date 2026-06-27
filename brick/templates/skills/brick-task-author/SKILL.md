---
name: brick-task-author
description: BRICK 빌딩 발주 한 스킬 — PHASE 1 task 본문 쓰기 → 입력 모드 결정(프리셋/그래프) → PHASE 2 공식 빌딩 발사 → PHASE 3 홀드 분류(걸리면). 새 빌딩 발주, 수리·기능·부검 task를 쓸 때 이 절차로. 모양 사이징은 building-sizing-method 스킬.
---

# BRICK 발주 (운영자 표준, 3-PHASE)

> 현재 호출자가 준 활성 체크아웃과 활성 vessel evidence root를 기준으로 발사·측정·코드수정한다.
> `/Users/smith/projects/BRICK` 및 오래된 `/Users/smith/projects/brick-protocol` 문구는 현재
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

프리셋 모드와 그래프 모드는 **같은 공식 launch surface로 들어가는 두 입력 모드**다.
`build()`, `fan()`, `compose_building()`, `assemble()`, `launch_assembled_building`은
Builder/front-door 재료다. 실행 안내에 이 이름을 쓰더라도 반드시 위 공식 vessel
evidence/reporter/frontier 경로로 보내라. 별도 공식 route처럼 말하지 마라.

## 한눈 결정나무

```
무엇을 발주하나?
│
├─ 표준 작업(수리·기능·부검·조사), 모양이 프리셋에 이미 있음
│     → PRESET 입력 모드 (PHASE 2-A). render_preset_ranking_packet로 랭킹(advisory — 내가 고름).
│
└─ 새 모양(팬아웃·팬인·병렬·다단), 맞는 프리셋 없음
      → 먼저 building-sizing-method 스킬로 모양 산출 → GRAPH 입력 모드. 누가 보나로 가른다:
        ├─ 사람이 머지 전 승인(감독)  → assemble(gates=("human-review",))
        └─ 골까지 무인(Smith 기본)    → §AUTO 직행 (PHASE 2-B)
```

발주 공개 surface = **공식 빌딩 발사 surface 하나**다. 프리셋은 `run_building_intake`로
materialize되고, 그래프는 `assemble()`/`launch_assembled_building` 재료로 materialize되지만,
둘 다 Builder/materializer → declared Building Plan → `support/operator/run.py` walker →
active vessel evidence root → reporter/Slack/frontier로 간다.
`driver_public_intake_seal` 체커는 raw 뒷문(`run_composed_graph_intake`)을 driver.py 공개표면에서
막는다. `assemble`은 shape/front-door 재료이지 별도 실행 route가 아니다. 3번째로 사고하지 마라.

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

이것은 design-first fan-out 또는 manual graph mode로 설명해도 된다. 그래도 Link가
Movement authority를 소유하고, support/model/checker/Slack은 source truth나
quality/success judge가 아니다.

---

# PHASE 1 — task 본문 쓰기

## 엔진이 task.md에서 진짜 요구하는 것 (실측)

| 필드 | 진실 |
|---|---|
| 노드 `work=` | **유일한 구조적 필수.** `brick("work","<한 줄>")`. 빠지면 CompositionError. returns/alias/comparison_rule은 build()가 자동채움 — 쓰지 마라. |
| 빌딩 `task=` | 비어있지 않은 텍스트 ≤64KB면 됨. **안의 heading 하나도 엔진 검증 안 함** — sha256 후 `work/task.md`로 그대로 쓰여 에이전트 프롬프트가 됨. |
| 그 외 | 모든 섹션은 에이전트 행동용(admission용 아님). write_scope는 write=True 노드에만. adapter/model/gates는 assemble() 인자(task.md 안 아님). |

**스톨의 진짜 레버(실측 0615):** 엔진은 task.md로 인한 스톨 0(불투명 텍스트). 60분 vs 2분은 **에이전트의 읽기범위 바운디드냐**다 — "fix the adapter"(무바운드)=트리 전체 훑어 60분 / "이 영역만, 딴 데 훑지 마"=2분. **레버 = 바운디드 스코프 한 줄(모듈·영역 단위면 충분).** file:line 좌표 박기는 목표 아니라 **fallback**(설계 노드 못 믿을 때만). §AUTO엔 그 읽기목록 산출이 **design 노드의 일**이다.

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
<포커스 체커 green + 변이 RED → check_profile.py --all exit 0 → (코드면) compileall + git diff --check>

## Hard constraints (law)
<write_scope는 "support/operator/**" glob(★"support/" 금지 = fnmatch 함정).
 금지선: 실루트 수정 / 핀 완화 / 스케줄러·신규의존성 / project/ 손대기>
```

부검은 `status/kernel/evidence-postmortem-task-template-0612.md` 사용([TARGETS]=대상 루트 + 대조군 1동, 사건은 장부에 있는 것만).

## 그래프 모양은 building-sizing-method 스킬

그림→코드 번역(`build() IS pipeline`, `fan() IS parallel`, KIND→에이전트 바인딩, QA깊이
그라데이션, 과대-사이징 금지)은 **building-sizing-method** 스킬로 분리됐다. 새 모양을 짜야 하면
그 스킬을 먼저 돌려 `GraphSpec`을 얻고, 여기 PHASE 2로 와서 발사한다. 운영자의 일 = **모양 판단
하나**(몇 단계·누가 병렬·어디 수렴)뿐.

---

# PHASE 2-A — PRESET 입력 모드 (run_building_intake)

```python
# cd <active checkout> && uv run python3 -c "..."
from brick_protocol.support.connection.building_design_toolkit import render_preset_ranking_packet
pkt = render_preset_ranking_packet("<task 요지 한 줄>", repo_root="<active checkout>")
# 토큰겹침 점수 desc. ADVISORY(자동선택 아님) — 내가 골라 chain_preset_ref로 박는다. 카탈로그=brick/templates/presets/
```
intent → `run_building_intake(intent, repo_root=<active checkout>, adapter_cwd=<전용 워크트리>, adapter_timeout_seconds=3600)`. **adapter_cwd 절대 누락 금지**(누락 시 활성 체크아웃에 작업).
```python
intent = { "task_statement": TASK, "building_id": "<슬러그>-MMDD",
  "chain_preset_ref": "building-chain-preset:<프리셋>",
  "declared_by": "caller-codex-operator",
  "selected_adapter_ref": "adapter:codex-local", "selected_model_ref": "model:default",
  "write_scope": {"allowed_paths": ["support/operator/**"], "forbidden_paths": []} }  # 읽기조사면 생략
```

---

# PHASE 2-B — GRAPH 입력 모드 — launch_assembled_building front-door 재료

`assemble`로 모양을 조립하고 **`launch_assembled_building`** front door로 공식 경로에 넣는다.
이 동사는 Builder/materializer 재료를 declared Building Plan으로 내려서 `support/operator/run.py`
walker와 active vessel evidence/reporter/frontier 경로로 연결한다. 별도 runtime이나 별도
Movement route가 아니다.

```python
# cd <active checkout> && uv run python3 -c "exec(open('/tmp/launch.py').read())"
from brick_protocol.support.operator.assembly import assemble, build, fan, Authority  # ★build = assembly.build(그래프). NEVER `from onboard import build`★
from brick_protocol.brick.spec import brick
from brick_protocol.support.operator.onboard import launch_assembled_building

graph = build([
    brick("design",  "범위를 좁혀라(바운디드 읽기목록 산출)"),
    brick("work",    "변경하라", write=True),
    brick("closure", "검증·보고하라"),
])
composed = assemble(graph, declared_by="coo-operator", authority=Authority.COO,
    task="<한 줄 task 본문 — work/task.md 됨>",
    adapter="codex-local",
    gates=())   # ()=완전 무인 / ("human-review",)=머지 edge에만 HOLD

result = launch_assembled_building(
    composed,                          # ★ ComposedGraph 그대로 — 객체/딕트 헷갈릴 필요 없음(동사가 처리)
    project_ref="project:brick-protocol",  # ★ 베슬(그릇). 생략 시 기본 project #1 베슬 = 둘 다 슬랙 발화
    declared_by="coo:smith",
    adapter_timeout_seconds=3600,
    # report_env 생략 ⇒ admitted env loader가 있으면 reporter/Slack/frontier evidence 관찰
)
print("building_id:", result["building_id"], "| ok:", result["ok"],
      "| frontier:", result.get("frontier_kind"), "| evidence:", result.get("evidence_root"),
      "| worktree:", result.get("worktree_path"))
```

`result`는 딕트: `ok`(frontier=complete냐), `ran`, `building_id`, `evidence_root`,
`frontier_kind`, `worktree_path`(샌드박스), `commit_sha`(complete면 자동커밋). 실패는
`error_kind`/`error_message`/`message_ko`로 친절히 떨어진다(예외 안 던짐).

## 알아둘 것

- **assemble의 top-level `adapter=`는 roled 노드에 무효.** design/closure/review/QA는 Agent Object와 per-node override가 이긴다. 주말 default는 work+closure+code QA=codex-local, axis/evidence/review QA=gemini-local이다. 노드를 role 디폴트에서 옮기려면 **per-node** `brick("design","...", adapter="codex-local")` override만이 레버.
- **Claude는 퇴역이 아니라 주말 active pool 제외다.** Claude token이 복귀하면 `step_selection_overrides`나 per-node adapter override로 다시 쓸 수 있다. 지금 고객-ready dogfood 기본은 **codex=구현/closure/code QA · gemini=axis/evidence/review QA · QA fan=codex+gemini**다.
- **verdict 노드는 `adapter:local` 금지.** design/closure/review/inspect는 verdict-bearing → `adapter:local` 거부. local 스텁 무인발사는 **work 노드로만** 가능. verdict 노드는 진짜 CLI(codex/gemini/claude) 필요.
- **부하 주의.** `launch_assembled_building`은 공식 경로에 그래프 입력을 넘기는 front door다. 검증은 가능하면 `assemble()`/레지스트리 체크로, 진짜 실행이 필요하면 `adapter:local` 또는 단일 `codex-local`/`gemini-local` 노드 1개로.
- **QA 주의.** QA는 inspect/probe evidence를 만들 수 있지만 source-truth mutation 권한이 아니다. QA source mutation이 관찰되면 HOLD로 보고한다.

## 게이트 진실 (실측)
- `gates=()` ⇒ **완전 무인**(최종 closure→boundary 포함 전 edge가 `link-gate:default-transition`만 달고 자동전진).
- `gates=("human-review",)` ⇒ **최종 boundary edge에만** HOLD. 중간 design→work는 그대로 auto.
- `coo-review`는 link-gate만 붙이고 **HOLD 안 박음**. 머지에서 진짜 멈추려면 `human-review`.
- 프리셋도 박음: `engine-feature-hard`=design→work HOLD; `fast-fix`/`quick-check`는 안 박음.
- 홀드된 빌딩은 `observe_building_frontier`로 보이고 `resume_building_plan`으로 전진.

---

# 발사 후 — 게이트는 내가 한다 (codex green 안 믿음)

- 워크트리에서 `HOME=$(mktemp -d) PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py --all` exit 0 + 포커스 체커 green + **변이 RED 직접 확인**.
- `launch_assembled_building`은 frontier=complete면 워크트리 변경을 **자동 커밋**(commit_sha 반환). closure가 엉키면(temp-HOME concern 연쇄→resume divergence) **추격 금지** — 코드만 독립검증되면 워크트리 diff를 `git commit`+`git -C BRICK merge --ff-only <branch>`로 직접 main에.
- 미완/홀드 빌딩은 untracked로 `--all`을 RED로 만듦 → merge·게이트 전 `mv project/.../buildings/<미완id> /tmp/`로 치움(비파괴).

---

# PHASE 3 — 홀드/실패/스톨 분류 (걸렸을 때만)

빌딩이 홀드 벨(intervention-required)·걸음 복귀·타임아웃·resume 거부·게이트 RED에 빠지면
**도장 찍기 전에 먼저 분류한다.** 원칙: **도장보다 분석이 먼저.** 모든 판단은 장부(증거)에서만.
빌딩 루트는 읽기 전용 — 분석 중 어떤 파일도 수정하지 않는다. 실험은 /tmp 사본에서만.

## 3.1 증거 수집 (전부 읽기 전용)

빌딩 루트 = `<BRICK>/project/brick-protocol/buildings/<id>/` (또는 `launch_assembled_building`이
반환한 `evidence_root`).

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
결함의 본체일 수 있다. 정본: status/kernel/stall-attribution-amendment-0613.md

## 3.5 보고

Smith 5문 형식 축약: ① 무슨 가족인지 한 문장+비유 ② 식별 근거(실측 행/값) ③ 한 처분 ④ 안 한 것
⑤ 반복되면 누가 잡나(체커/소수선). 새 가족 발견 시 이 분류표에 행을 추가한다.

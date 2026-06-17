# Launch guide (운영자 + 고객)

이 문서는 빌딩을 "어떻게 시작하느냐"를 한 장으로 정리합니다. 개념은
[three-axis overview](three-axis-overview.md)·[quickstart](quickstart.md)에
있고, 여기서는 **정문 하나**·**실행 방법**·**프리셋**·**점검**·**함정**만
다룹니다.

관련: [quickstart](quickstart.md) · onboard CLI 도움말
(`uv run python3 -m brick_protocol.support.operator.onboard --help`,
`... onboard goal-approve --help`)

---

## 정문 (단 하나의 입구)

빌딩을 설계하는 AI는 **메인 에이전트 자신**입니다. 고객이 쓰는 그 메인 AI
(claude code 그 자체)가 곧 설계 지능이에요. **별도의 "디자인 AI"는 없습니다.**

흐름은 한 줄로:

```
task(말로 전한 일)
  -> 메인 에이전트가 구조를 정함 (몇 단계 · 누가 · 어떻게 이어지나)
  -> assemble(brick/agent/chain) 로 그래프를 조립        [메인이 STRUCTURE 결정]
  -> 빌더가 FORMAT 채움 (refs · ids · 문법)               [엔진이 채움]
  -> 사람/COO 승인 (render_proposal_for_human + onboard goal-approve) [사람 게이트]
  -> 엔진이 굴림 (run_building_plan, 격리 워크트리)
```

축의 분업이 핵심입니다:

- **STRUCTURE = 메인 에이전트**: 몇 단계인지, 각 단계가 누구(agent)인지,
  단계들이 어떻게 이어지는지(chain/fan-out/fan-in)를 **판단**합니다.
- **FORMAT = 빌더(`assemble`)**: node_id, step_template_ref, edge_ref,
  gate_refs, 문법·검증을 **자동으로 채웁니다**. 메인은 ref/id를 손으로 쓰지
  않습니다.
- **승인 = 사람/COO**: 굴리기 전 frozen proposal을 보고 forward/stop을 정합니다.

### 1) 조립 (메인 에이전트가 하는 일)

`support/operator/assembly.py` 의 핸들 기반 API로 그래프를 선언합니다.
브릭 종류·일·누구만 말하면 됩니다 (ref/id는 빌더가 채움):

```python
from brick_protocol.support.operator.assembly import (
    assemble, brick, agent, chain, Authority,
)

graph = chain([
    brick("design", "온보딩 환영 문구를 한 줄로 다듬을 방향을 잡아 주세요"),
    brick("work",   "그 방향대로 문구를 고쳐 주세요", write=True),
    brick("closure","고친 결과를 닫아 주세요"),
])

composed = assemble(
    graph,
    declared_by="smith",
    authority=Authority.COO,
    task="온보딩 환영 문구를 한 줄로 다듬어 주세요",
    adapter="local",
)
```

`assemble()` 는 `compose_building` 을 호출해 **검증된 frozen 플랜**
(`composed.composed_plan`)을 만들어 돌려줍니다. 조립 헬퍼:

- `brick(kind, work, ...)` — 한 단계. `alias=`, `write=True`(+ `assemble(write_scope=...)`),
  `returns=`(fan-in 소스 필수), `agent=`, `adapter=`, `model=`.
- `agent(role, ...)` — 그 단계를 누가 맡는지(레인).
- `chain([...])` — 직선. `fan_out(source, [branches])` / `fan_in(sources, converge_on, route=[...])` /
  `converge(...)` 로 갈래·합류도 조립합니다.
- `reroute(on, to, budget=...)` / `hold(on)` — 합류점의 concern별 처분.
  (self-reroute, 즉 합류점이 자기 자신으로 되돌리는 건 막혀 있습니다.)

### 2) 승인 게이트 (사람/COO)

조립한 proposal을 디스크에 얼린 뒤 사람이 봅니다:

```python
from brick_protocol.support.operator.assembly import persist_proposed_building_graph
from brick_protocol.support.operator.onboard import render_proposal_for_human

path = persist_proposed_building_graph(composed, "~/.brick/goal-runs")
print(render_proposal_for_human(path))   # 단계·누구·링크·게이트·쓰기영역을 한글로 미리보기
```

미리보기를 확인하고 굴립니다 (frozen `proposed-building-graph.json` 위에서만 동작):

```bash
uv run python3 -m brick_protocol.support.operator.onboard goal-approve \
  ~/.brick/goal-runs/<building-id> --action forward --author coo:smith
```

`--action stop` 이면 아무것도 굴리지 않습니다. `forward` 는 그 frozen 플랜을
`run_building_plan` 으로 (워크트리 샌드박스 안에서) 한 번 굴립니다.
`render_proposal_for_human` 과 `run_goal_approve_entry` 는
`support/operator/onboard.py` 에 있습니다.

### 빠른 길: 좌표 박힌 표준 작업이면 바로 intake

설계가 필요 없는 **좌표-바운디드** 작업(자율 수리 등)은 조립·승인 단계를
건너뛰고, 프리셋을 골라 `run_building_intake` 로 바로 굴릴 수 있습니다.
빌더(materializer)가 그래프를 자동으로 채웁니다:

```python
from brick_protocol.support.operator.driver import run_building_intake

result = run_building_intake({
    "declared_by": "caller-me",
    "task_statement": "버튼 라벨 오타를 고쳐 주세요",     # 말로 전한 일이 work/task.md로 기록됨
    "chain_preset_ref": "building-chain-preset:fast-fix", # 프리셋이 구조를 줌
    "selected_adapter_ref": "adapter:local",
})
print(result.building_id, result.run_result.lifecycle_write.root)
```

발주를 **만드는 공개 길은 둘 뿐**입니다: 프리셋이면 `run_building_intake`,
새 구조면 `assemble`. (`run_composed_graph_intake` 는 RAW dict 직결 뒷문이라
공개 표면에서 **봉인**됐습니다 — `driver.__all__` 에 없고 체커/내부 전용.
손-dict 그래프 발주 대신 `assemble` 빌더DSL을 쓰세요.) 두 공개 길 모두
`plan_shape: graph` 로 같은 `run_building_plan` 입구에 넘어갑니다.

---

## 실행 방법 (어떻게 호출하나)

**저장소 루트에서 `uv run python3 -c` 또는 `-m` 으로 호출하세요.**

```bash
cd ~/BRICK   # 또는 네 클론 위치
uv run python3 -c 'from brick_protocol.support.operator.driver import run_building_intake; ...'
```

- ❌ **`/tmp` 에 스크립트 파일을 만들어 직접 PYTHONPATH 를 박지 마세요.**
  파일 스크립트는 저장소 루트를 `sys.path` 에 올리지 않기 때문에, 패키지의
  벌거벗은 `support.` import 가 `ModuleNotFoundError` 로 깨집니다. 루트에서
  `uv run python3 -c/-m` 으로 호출하면 import identity 가 올바르게 잡힙니다.
  (uv 가 없으면 `PYTHONPATH=support/import_identity python3 ...` 를 루트에서
  쓰되, 전역 `python3` 에 PyYAML 이 설치돼 있어야 합니다.)

- **`adapter_cwd` = 격리된 git 워크트리.** 어댑터(codex/claude 같은 실제
  provider)는 `adapter_cwd` 안에서만 파일을 씁니다. 격리 워크트리를 주면 그
  diff 가 워크트리에 남아 게이트+머지로 흘러갑니다. `adapter_cwd` 를 빠뜨리면
  실제 provider 가 **진짜 저장소를 수정**합니다.
  (고객용 경로는 `run_customer_building_in_sandbox`/goal-approve 가 워크트리
  샌드박스를 자동으로 만들고, 완주했을 때만 커밋합니다.)

- **`report.env` 를 먼저 source 하세요** (벨/대시보드 알림):

  ```bash
  source ~/.brick/report.env
  ```

---

## 프리셋

| 프리셋 | 언제 | COO 게이트 | reroute |
| --- | --- | --- | --- |
| `building-chain-preset:fast-fix` | 좌표-바운디드 자율 수리/문서 수리 (task.md가 명확하고 설계 불필요) | **없음** (자율) | work 노드에 reroute 예산 5 |
| `building-chain-preset:brick-protocol-engine-feature-hard` | 설계가 필요한 엔진/드라이버/체커/게이트/어댑터/자동화 변경 | **있음** (사람 COO 게이트) | design·work 각 예산 1 |

- **fast-fix** (`brick/templates/presets/fast-fix.md`): work → code-attack-qa →
  closure. COO 게이트가 없어 사람 개입 없이 자율로 굴러갑니다. work 단계가
  막히면 reroute 예산(5) 안에서 스스로 되돌아갑니다.
- **engine-feature-hard** (`brick/templates/presets/brick-protocol-engine-feature-hard.md`):
  design → work → (code-attack / axis-attack / evidence-integrity 병렬 QA) →
  합류 최종 게이트 → closure. `gate_concept_profile` 에 `coo-review`·`human-review`
  가 있어 **design 다음에서 사람 disposition 이 생길 때까지 HOLD** 합니다.
  사람 승인이 필요하니 "왜 안 끝나지?" 하지 말고 게이트를 처분하세요
  (`onboard approve <building> --action forward`).

---

## 점검 (check)

체커 프로필은 **워크트리 안에서, 제자리에서** 돌리세요:

```bash
cd /path/to/this/worktree
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all
# 초록불 = exit 0
```

❌ 별도 `/tmp` git-archive 사본에서 돌리지 마세요. 점검은 지금 작업 중인
워크트리의 실제 파일을 봐야 합니다. 워크트리 밖으로 손을 뻗으면 방금 한
수정을 놓칩니다.

---

## 예제 위자드

번들된 예제 빌딩을 한 번 굴려 보려면:

```bash
uv run python3 -m brick_protocol.support.operator.onboard codex
```

(host 자리: `codex | claude | gemini | local` — provider CLI 가 하나도 없으면
`local`. provider 없이도 `adapter:local` 로 돕니다.) provider 준비 점검 → 연결
설정 안내 → 첫 예제 빌딩 → 다음 단계 안내까지 진행합니다. 진단만 하려면
`... onboard doctor` (항상 exit 0).

---

## ❌ 제거됨 (옛문, 쓰지 마세요)

아래는 **gate-2 에서 제거된** 옛 경로입니다. 더 이상 존재하지 않으니 찾지
마세요:

- `onboard goal "<text>"` CLI — 제거됨. (혼동 주의: `onboard goal-approve` 는
  **남아 있는 새 흐름**입니다. `goal`(제거)과 `goal-approve`(유지)는 다릅니다.)
- `support/operator/auto_compose.py` / `auto_compose` — 제거됨.
- `--design-brain` / `--brain` (별도 디자인 AI 선택) — 제거됨.
- `driver.run_goal_in_sandbox` / `run_goal_entry` / `compose_building_from_task`
  / `GOAL_SEAM_VERB` — 제거됨.

옛 모델은 "별도의 디자인 AI 가 보드를 보고 자동으로 빌딩을 합성한다" 였습니다.
지금은 **메인 에이전트가 그 설계 지능**입니다. 메인이 `assemble()` 로 구조를
짜고, 빌더가 형식을 채우고, 사람이 `onboard goal-approve` 로 승인합니다.

---

## 함정 모음 (실제 운영자 실수)

1. **`/tmp` PYTHONPATH** — 파일 스크립트에 손으로 PYTHONPATH 를 박으면 저장소
   루트가 `sys.path` 에 안 올라가 `ModuleNotFoundError: No module named
   'support'`(또는 `brick_protocol`). 루트에서 `uv run python3 -c/-m` 로 호출.
2. **프리셋 잘못 고름** — `engine-feature-hard` 는 COO 게이트에서 HOLD 하는데
   "멈췄다"고 오해. 자율로 끝까지 굴러야 하는 좌표-바운디드 작업이면
   `fast-fix`(게이트 없음). 설계가 필요한 변경이면 `engine-feature-hard` 의
   HOLD 는 정상이니 게이트를 처분.
3. **`adapter_cwd` 빠뜨림** — 실제 provider 어댑터가 격리 워크트리가 아니라
   **진짜 저장소**를 수정. 고객용은 샌드박스 경로(goal-approve /
   `run_customer_building_in_sandbox`)를 쓰거나 `adapter_cwd` 를 명시.
4. **`report.env` 안 source** — 벨/대시보드 알림이 안 옴. 세션 시작에
   `source ~/.brick/report.env`.
5. **점검을 워크트리 밖에서 돌림** — 별도 `/tmp` git-archive 사본에서 체커를
   돌리면 방금 한 수정을 못 봄. `check_profile.py --all` 은 **제자리**(작업
   워크트리 안)에서.

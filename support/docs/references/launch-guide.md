# Launch guide (운영자 + 고객)

이 문서는 빌딩을 "어떻게 시작하느냐"를 한 장으로 정리합니다. 개념은
[three-axis overview](three-axis-overview.md)·[quickstart](quickstart.md)에
있고, 여기서는 **정문 하나**·**실행 방법**·**프리셋**·**점검**·**함정**만
다룹니다.

관련: [quickstart](quickstart.md) · `brick --help` · `brick build --help`

---

## 정문 (단 하나의 고객 실행 표면)

고객이 빌딩을 시작하는 공식 표면은 **`brick build` 하나**입니다. 입력 모드는
둘입니다:

```bash
brick build --task "..." --preset building-chain-preset:fast-fix
brick build --graph /path/to/declared-graph-packet.json
```

첫 번째는 `preset_task` 경로입니다. 할 일을 말로 주고(`--task`), 필요하면
선언된 프리셋을 고릅니다(`--preset`). 두 번째는 `graph_packet` 경로입니다.
caller/COO가 이미 선언한 그래프 packet을 같은 `brick build` 표면에 넘깁니다.

`run_building_intake`, `assemble`, `launch_assembled_building`, and
`goal-approve` are support/operator helpers or advanced/internal paths. They
are not separate customer execution routes.

빌딩을 설계하는 AI는 **메인 에이전트 자신**입니다. 고객이 쓰는 그 메인 AI가
곧 설계 지능이에요. **별도의 "디자인 AI"는 없습니다.**

흐름은 한 줄로:

```
task(말로 전한 일)
  -> brick build --task / --preset                         [고객 표면]
  -> support가 선언된 preset_task를 Building Plan으로 물질화
  -> support runner가 선언된 Brick / Agent / Link row를 격리 워크트리에서 걸음
  -> evidence_root, frontier_kind, proof_limits를 출력

declared graph packet
  -> brick build --graph <packet.json>                     [같은 고객 표면]
  -> support가 graph_packet을 검증하고 선언된 그래프를 걸음
  -> evidence_root, frontier_kind, proof_limits를 출력
```

축의 분업이 핵심입니다:

- **STRUCTURE = declared input**: preset_task는 선언된 프리셋이 구조를 주고,
  graph_packet은 caller/COO가 이미 선언한 그래프가 구조를 줍니다.
- **FORMAT = support builder/materializer**: refs, ids, 문법·검증을 채워
  Building Plan으로 물질화합니다.
- **RUN = support runner**: 선언된 Brick / Agent / Link row를 걷고 증거를
  기록합니다. Movement를 고르거나 품질/성공을 판단하지 않습니다.

이 문서는 지원 증거용 안내입니다. provider reliability, customer
comprehension, success, quality, source truth, Movement authority는 이 문서나
CLI 출력으로 증명되지 않습니다.

### 1) 표준 작업: `brick build --task`

```bash
brick build \
  --task "버튼 라벨 오타를 고쳐 주세요" \
  --preset building-chain-preset:fast-fix \
  --real-provider
```

`--real-provider`는 Claude, Codex, Gemini local readiness를 선언된 support
순서로 관찰하고, 준비된 첫 observed-write adapter를 고릅니다. 명시적인
`--adapter`가 있으면 그 값이 우선합니다. 준비된 provider가 없으면
`adapter:local`로 fallback하며, 그 사실도 support evidence로 출력됩니다.

### 2) 선언된 그래프: `brick build --graph`

```bash
brick build --graph /path/to/declared-graph-packet.json
```

이 경로는 이미 선언된 graph packet용입니다. support는 packet을 검증하고
걷습니다. support가 route target, Movement, 성공, 품질을 발명하지 않습니다.

### Advanced/internal: assembly helper

`support/operator/assembly.py` 의 핸들 기반 API로 그래프를 선언합니다.
브릭 종류·일·누구만 말하면 됩니다 (ref/id는 빌더가 채움). 이 API는
support/operator helper이며, 고객 실행 표면은 여전히 `brick build --graph`입니다:

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
    adapter="codex-local",
)
```

`assemble()` 는 `compose_building` 을 호출해 **검증된 frozen 플랜**
(`composed.composed_plan`)을 만들어 돌려줍니다. 조립 헬퍼:

- 종합/closure 노드(closure kind 또는 reviewer/leader lane)는
  `adapter="codex-local"`처럼 명시적인 non-local adapter로 조립하세요.
  `adapter="local"`/기본값으로 떨어지면 `assemble()`이 fail-closed합니다.
- `brick(kind, work, ...)` — 한 단계. `alias=`, `write=True`(+ `assemble(write_scope=...)`),
  `returns=`(fan-in 소스 필수), `agent=`, `adapter=`, `model=`.
- `agent(role, ...)` — 그 단계를 누가 맡는지(레인).
- `chain([...])` — 직선. `fan_out(source, [branches])` / `fan_in(sources, converge_on, route=[...])` /
  `converge(...)` 로 갈래·합류도 조립합니다.
- `reroute(on, to, budget=...)` / `hold(on)` — 합류점의 concern별 처분.
  (self-reroute, 즉 합류점이 자기 자신으로 되돌리는 건 막혀 있습니다.)

### Advanced/internal: approval helper

조립한 proposal을 디스크에 얼린 뒤 사람이 봅니다:

```python
from brick_protocol.support.operator.assembly import persist_proposed_building_graph
from brick_protocol.support.operator.onboard import render_proposal_for_human

path = persist_proposed_building_graph(composed, "~/.brick/goal-runs")
print(render_proposal_for_human(path))   # 단계·누구·링크·게이트·쓰기영역을 한글로 미리보기
```

미리보기를 확인하고 내부 승인 helper로 굴릴 수 있습니다 (frozen
`proposed-building-graph.json` 위에서만 동작). 고객-facing 실행 route로
문서화할 때는 선언된 graph packet을 `brick build --graph`로 넘깁니다:

```bash
uv run python3 -m brick_protocol.support.operator.onboard goal-approve \
  ~/.brick/goal-runs/<building-id> --action forward --author coo:smith
```

`--action stop` 이면 아무것도 굴리지 않습니다. `forward` 는 그 frozen 플랜을
`run_building_plan` 으로 (워크트리 샌드박스 안에서) 한 번 굴립니다.
`render_proposal_for_human` 과 `run_goal_approve_entry` 는
`support/operator/onboard.py` 에 있습니다.

### Internal helper: intake seam

`run_building_intake`는 `brick build --task/--preset` 아래의 support/operator
helper입니다. 고객 문서에서는 이 helper를 별도 실행 route로 세우지 않습니다.
운영자나 테스트가 직접 호출할 때는 프리셋을 골라 intent를 넘깁니다:

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

공식 고객 실행 표면은 하나입니다: `brick build`. 그 아래 입력 모드가
`preset_task`(`--task`/`--preset`)와 `graph_packet`(`--graph`)입니다.
`run_composed_graph_intake` 는 RAW dict 직결 뒷문이라 공개 표면에서 **봉인**됐습니다
— `driver.__all__` 에 없고 체커/내부 전용. 손-dict 그래프 발주 대신 선언된
graph packet을 `brick build --graph`로 넘기세요.

---

## 실행 방법 (어떻게 호출하나)

**저장소 루트에서 `uv run python3 -c` 또는 `-m` 으로 호출하세요.**

```bash
cd ~/BRICK   # 또는 네 클론 위치
brick build --task "..." --preset building-chain-preset:fast-fix
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
  (`brick build`가 customer sandbox helper를 통해 워크트리 샌드박스를 만들고,
  완주했을 때만 커밋합니다.)

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
  (내부 disposition/approval helper로 처분).

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
  남아 있는 support/operator helper입니다. `goal`(제거)과
  `goal-approve`(helper)는 다릅니다.)
- `support/operator/auto_compose.py` / `auto_compose` — 제거됨.
- `--design-brain` / `--brain` (별도 디자인 AI 선택) — 제거됨.
- `driver.run_goal_in_sandbox` / `run_goal_entry` / `compose_building_from_task`
  / `GOAL_SEAM_VERB` — 제거됨.

옛 모델은 "별도의 디자인 AI 가 보드를 보고 자동으로 빌딩을 합성한다" 였습니다.
지금은 **메인 에이전트가 그 설계 지능**입니다. helper 수준에서는 메인이
`assemble()` 로 구조를 짜고, 빌더가 형식을 채우고, 사람이 `goal-approve`
계열 helper로 승인할 수 있습니다. 고객-facing 실행 표면은 여전히
`brick build` 하나입니다.

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
   **진짜 저장소**를 수정. 고객용은 `brick build` 샌드박스 경로를 쓰거나
   내부 helper를 직접 호출할 때 `adapter_cwd` 를 명시.
4. **`report.env` 안 source** — 벨/대시보드 알림이 안 옴. 세션 시작에
   `source ~/.brick/report.env`.
5. **점검을 워크트리 밖에서 돌림** — 별도 `/tmp` git-archive 사본에서 체커를
   돌리면 방금 한 수정을 못 봄. `check_profile.py --all` 은 **제자리**(작업
   워크트리 안)에서.

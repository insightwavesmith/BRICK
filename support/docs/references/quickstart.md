# Run your first Building

Brick Protocol is a three-axis work protocol for human-agent work: Brick is the work, Agent is the performer, and Link is the transfer/carry/movement between work boundaries. A Building is a declared packet of one or more steps; when you run it, the support runner walks the declared Brick / Agent / Link rows and records support evidence about what was received, what was returned, and what Link facts were declared. That evidence is not source truth, not a success judgment, not a quality judgment, and not Movement authority.

You do not author task files for the common path: SPEAK your task as text
through `brick build --task`. The official customer-facing route is one
surface:

```text
brick build --task "..." --preset <preset-ref>   # preset_task input
brick build --graph <packet.json>                # graph_packet input
```

`run_building_intake`, `assemble`, `launch_assembled_building`, and
`goal-approve` are support/operator helpers or advanced/internal paths. They
are not separate customer execution routes. Files dropped at the repository
root (or anywhere unadmitted) are rejected by the admission checker — keep any
scratch files of your own outside the repository.

## Customer-entry readiness matrix

This is the minimum cold-start map for a fresh customer or customer-like
session. It is support documentation only: it is not source truth, not a
success judgment, not a quality judgment, and not Movement authority.

| Question | Current customer-facing answer | Evidence / proof limit |
| --- | --- | --- |
| What reads first? | Start at repo-root `README.md`, then this `support/docs/references/quickstart.md`, then `support/docs/references/setup.md` when you need prerequisite and checker details. After `brick init`, read the generated `FIRST_USE.md` under the chosen output root. | `README.md` links this quickstart and setup guide. `support/operator/first_use.py` renders `FIRST_USE.md` after the local example. Whether a customer understands the sequence without help is not proven. |
| Active checkout or frozen/history repo? | Use this product checkout or its release export for active work. The frozen HISTORY repository is for archived evidence only; do not start new customer work there. In this checkout, `brick status` reports the resolved `repo_root`, current `cwd`, entrypoint file, and default builds root. Release exports omit `project/`; the first onboard/run creates local project evidence as needed. | `README.md` documents release export and HISTORY separation. `support/operator/cli.py` implements `brick status`. Byte-for-byte release parity and fresh-machine behavior remain not proven until measured. |
| Official Building launch route? | Common customer path: install, run the onboarding wizard, then speak the task through `brick build --task`. Use `--preset` for the declared chain preset. When caller/COO already has a declared graph packet, use `brick build --graph <packet.json>`. | This page and `launch-guide.md` document one public execution surface: `brick build`. Its input modes are `preset_task` (`--task`/`--preset`) and `graph_packet` (`--graph`). Support walks declared rows; it does not choose Movement. Provider reliability, customer comprehension, success, quality, source truth, and Movement authority are not proven by these docs. |
| Slack expectation? | Slack is optional. The first local path does not require Slack and should not expect a direct Slack check. Operator notification uses `~/.brick/report.env` only after provisioning/source, and real Slack delivery remains gated by declared delivery flags and environment credentials. | `launch-guide.md` notes `source ~/.brick/report.env` for bell/dashboard notifications. Reporter/Slack delivery is support projection only and must not expose credentials or become a scheduler/queue/retry runtime. |
| Where does evidence land? | Ref-less defaults land under `$BRICK_HOME/project/brick-protocol/buildings/<building_id>/`, or `~/.brick/project/brick-protocol/buildings/<building_id>/` when `BRICK_HOME` is unset. Runs that declare `project_ref: "project:brick-protocol"` land in the repo-local vessel `project/brick-protocol/buildings/<building_id>/`. Customer CLI builds use the declared output root and report `evidence_root`; `FIRST_USE.md` repeats that root for the local example. | The root contains `capture/`, `raw/`, `evidence/`, and `work/`. These are support evidence and projections, not source truth or judgments. |
| Not proven / proof limits | A green checker or written Building root is evidence only. Provider behavior, credential readiness, customer comprehension, release/export parity, and fresh-machine install/run behavior are not proven by this page. | Close those with separate run evidence, not by wording in docs. |

## 가장 빠른 길: 위자드

`install.sh` 가 끝났다면, 첫 빌딩까지는 이 한 줄이 전부예요:

```bash
uv run python3 -m brick_protocol.support.operator.onboard codex
```

(host 자리는 `codex | claude | gemini | local` — provider CLI가 하나도 없으면
`local`. provider 없이도 돌아갑니다.) 위자드는 provider 준비 상태 점검 → 연결
설정 안내 → 첫 예제 빌딩(기본은 provider 없이 `adapter:local`, 결과는 임시
폴더에만 기록) → 다음 단계 안내까지 알아서 진행해요. 이후 고객이 직접 쓰는
공식 실행 표면은 `brick build` 하나입니다.

## AI-runnable onboarding checklist

Fresh clone부터 첫 Building과 dashboard snapshot까지 운영자 AI가 그대로
따라갈 수 있는 확인 줄입니다.

```text
step: clone + install
command: gh repo clone {OWNER}/BRICK ~/BRICK && sh ~/BRICK/support/onboarding/install.sh
expected: "5) 설치 점검 완료" 와 다음 온보딩 명령이 출력된다.
failure signal: BRICK_REPO={OWNER}/BRICK 요청, gh auth login 요청, python3/uv 진단, 또는 clone/pull 실패.

step: doctor
command: cd ~/BRICK && uv run python3 -m brick_protocol.support.operator.onboard doctor
expected: provider별 준비 상태 표와 증상 -> 처방 표가 출력되고 exit 0.
failure signal: doctor 자체 stack trace, 또는 repo 루트가 아닌 곳에서 실행한 import 실패.

step: first Building from text
command: cd ~/BRICK && brick build --task "첫 온보딩 빌딩을 support evidence only로 기록해 주세요." --preset building-chain-preset:design-contract-only --building-id quickstart-ai-runnable-001 --adapter adapter:local --output-root project/brick-protocol/buildings
expected: build_input_mode=preset_task, quickstart-ai-runnable-001, evidence_root=.../project/brick-protocol/buildings/quickstart-ai-runnable-001, frontier_kind가 출력된다.
failure signal: FileExistsError이면 building_id를 새로 정한다; ModuleNotFoundError이면 uv run 또는 PYTHONPATH를 확인한다.

step: dashboard snapshot
command: cd ~/BRICK && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity uv run python3 support/operator/dashboard_export.py --bake-public
expected: "baked support/dashboard/public/dashboard-data.json | buildings N | source_truth False".
failure signal: source_truth가 False가 아니거나, dashboard-data.json 생성 실패, 또는 project evidence shape 거절.

step: checker gate
command: cd ~/BRICK && PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py --all
expected: profile passed: 줄들이 출력되고 마지막 proof-limit 줄 뒤 exit 0.
failure signal: "profile runner rejected evidence:" 뒤 첫 줄이 수리 대상이다.
```

운영자 세션은 status inbox 감시를 같이 켭니다. release export에는 `project/`가
없으므로 첫 onboard/run 뒤부터 경로가 생길 수 있습니다.

```bash
cd ~/BRICK
while true; do
  if [ -d project/brick-protocol/status/inbox ]; then
    find project/brick-protocol/status/inbox -maxdepth 1 -type f -name '*.json' -print | tail -20
  else
    printf '%s\n' 'status inbox not created yet'
  fi
  sleep 5
done
```

예상 출력은 알림이 없으면 빈 줄 또는 `status inbox not created yet`, 알림이
있으면 `project/brick-protocol/status/inbox/*.json` 경로입니다. 실패 신호는
repo 루트가 아닌 곳에서 실행하거나 `find`가 숨기지 않은 `No such file or
directory`를 반복하는 경우입니다.

## 막혔을 때: 증상 → 처방

`uv run python3 -m brick_protocol.support.operator.onboard doctor` 를 돌리면
지금 컴퓨터의 준비 상태 점검과 함께 아래 표를 출력해요 (진단만 하고 항상
exit 0).

| 증상 | 처방 |
| --- | --- |
| `ModuleNotFoundError: No module named 'brick_protocol'` (또는 `'yaml'`) | 저장소 루트에서 `uv run python3 ...` 형식으로 실행 (uv 없이는 `PYTHONPATH=support/import_identity python3 ...` + 전역 PyYAML 필요) |
| `FileExistsError` (Building root already exists) | 새 `building_id` 를 정하거나 `overwrite_existing=True` 를 의도적으로 전달 (위자드 예제는 자동 처리) |
| `local_cli_missing` (codex 어댑터) | `npm install -g @openai/codex` 후 `codex login` |
| `local_cli_missing` (claude 어댑터) | `npm install -g @anthropic-ai/claude-code` |
| gh 인증 에러 (clone/pull 실패) | `gh auth login` (gh가 없으면 https://cli.github.com 에서 설치) |

## Speak your task: `brick build --task`

The human flow is one command — pass your task as text and, when needed, name
the declared preset:

```bash
brick build \
  --task "온보딩 화면의 환영 문구를 한 줄로 다듬어 주세요." \
  --preset building-chain-preset:design-contract-only \
  --adapter adapter:local
```

`brick build` records support evidence that includes `build_input_mode:
preset_task`, the Building id, the selected adapter, the declared preset, the
evidence root, frontier observation, proof limits, and not-proven facts. The
underlying support/operator helper materializes the selected chain preset into
a declared plan and records your exact words as the Building's `work/task.md`
evidence. That helper is not a separate customer execution route.

Use `--real-provider` after `brick auth login` if you want the CLI to observe
Claude, Codex, and Gemini readiness in declared support order and select the
first ready observed-write adapter. An explicit `--adapter` still wins.

## Declared graph packets: `brick build --graph`

When a caller/COO-declared graph packet already exists, keep the same customer
surface and pass the packet:

```bash
brick build --graph /path/to/declared-graph-packet.json
```

The graph packet path is the `graph_packet` input mode. It is for already
declared graph packets; it is not permission for support to invent route
targets or Movement.

## Direct plan runner (advanced/internal)

You can also run a full plan file directly through `run_building_plan`. This is
an advanced support/operator path, not a separate customer execution route; the
customer route remains `brick build`. The repository already ships a verified,
runnable first plan at `brick/building_plans/onboarding-example-0.yaml`; point
the runner at it rather than hand-writing one (a hand-written copy would drift
from the real, tested shape).

A Building plan is GRAPH-shaped: `plan_shape: graph` at the top, then
`execution_order`, `brick_steps`, and `link_edges`. The support runner always
dispatches to the dynamic graph walker, which rejects any plan that is not
`plan_shape: graph`. Here is the bundled plan, faithfully (the file is the
source of truth — read it for the full, current text):

```yaml
plan_ref: building-plan:onboarding-example-0
owner_axis: Brick
building_id: onboarding-example-0-0607
plan_shape: graph
declared_by: coo
selected_adapter_ref: adapter:local
proof_limits:
  - support evidence only
  - bundled onboarding example only
  - runs in-process on adapter:local (no provider needed)
  - not source truth
  - not success judgment
  - not quality judgment
  - not Movement authority
not_proven:
  - real provider behavior
  - quality of the returned greeting
  - repeated provider reliability
  - production runtime readiness
execution_order:
  - onboarding-example-0-hello
brick_steps:
  - step_ref: onboarding-example-0-hello
    completion_edge_ref: link-row:onboarding-example-0-hello-closed
    rows:
      - axis: Brick
        row_ref: brick-row:onboarding-example-0-hello
        brick_work_ref: work:onboarding-example-0
        brick_instance_ref: brick-onboarding-example-0-hello
        work_statement: Say hello to the new operator and name the three axes of the Brick Protocol (Brick = the work, Agent = the worker, Link = the handoff). This is a tiny harmless first example; do not change any files.
        comparison_rule: Observe whether the returned greeting evidence is present; this example records a first run, not success or quality.
        required_return_shape: observed_evidence, proof_limits, not_proven
      - axis: Agent
        row_ref: agent-row:onboarding-example-0-hello
        agent_object_ref: agent-object:coo
link_edges:
  - edge_ref: link-row:onboarding-example-0-hello-closed
    source_step_ref: onboarding-example-0-hello
    target_brick_instance_ref: building-boundary:onboarding-example-0-closed
    rows:
      - axis: Link
        row_ref: link-row:onboarding-example-0-hello-closed
        declared_gate_refs:
          - link-gate:default-transition
        movement: forward
        building_lifecycle:
          state: closed
          reason: ONBOARDING-EXAMPLE-0 first example run recorded on adapter:local; no further Movement chosen inside this example.
        target_ref: building-boundary:onboarding-example-0-closed
        next_brick_instance_ref: building-boundary-onboarding-example-0-closed
```

The plan declares the whole road up front. The Brick row says what work is requested and which return fields are expected. The Agent row names the provider-neutral Agent Object that receives the work. The Link edge declares the movement and closed target for this one-step example; support does not choose that movement.

## Run it

From the repository root (`uv run` uses the `.venv` that `install.sh` / `uv sync` prepared, where brick-protocol and PyYAML live). The path is repo-relative, so this runs the bundled plan as-is:

```bash
uv run python3 -c 'from brick_protocol.support.operator.run import run_building_plan; result = run_building_plan("brick/building_plans/onboarding-example-0.yaml"); print(result.building_id); print(result.lifecycle_write.root); print("\n".join(str(path) for path in result.written_files))'
```

No `uv`? The bare-Python alternative works only if PyYAML is installed for your global `python3`:

```bash
PYTHONPATH=support/import_identity python3 -c 'from brick_protocol.support.operator.run import run_building_plan; result = run_building_plan("brick/building_plans/onboarding-example-0.yaml"); print(result.building_id); print(result.lifecycle_write.root); print("\n".join(str(path) for path in result.written_files))'
```

The bundled plan uses `adapter:local`, so the COO Agent Object uses its registered local callable reference: no provider CLI, no login, runs in-process. That is useful for a smoke run of the support path, but it does not prove provider behavior or work quality. (Rerunning lands in the same Building root; pass `overwrite_existing=True` to reuse it, or give a fresh `building_id`.)

### 업그레이드: 실제 provider로

For the customer CLI, `brick build --task "..." --real-provider` observes
Claude, Codex, and Gemini local readiness in declared support order, selects
the first ready observed-write adapter, and falls back to `adapter:local` when
none is ready. An explicit `--adapter` still wins. The CLI output remains
support evidence only; it does not prove provider reliability, customer
comprehension, success, quality, source truth, or Movement authority.

For a direct plan run, copy the bundled plan OUTSIDE the repository (the repo
tree admits no scratch files) and change its top-level adapter field (the
bundled plan declares the adapter only at the top level), then point
`run_building_plan` at your copy. Codex is one explicit adapter example:

```yaml
selected_adapter_ref: adapter:codex-local
selected_model_ref: model:codex:default
```

`adapter:codex-local` invokes the local Codex CLI in read-only mode for this plan because the Brick row has no `write_scope`. It requires the local `codex` command and local provider state to be available — if the CLI is missing you get a `local_cli_missing` adapter error (처방은 위의 증상→처방 표). `adapter:claude-local` works the same way for the Claude CLI. `adapter:gemini-local` invokes the local Gemini CLI and observes only `GEMINI_API_KEY` / `GOOGLE_API_KEY` presence, never credential bodies.

## Evidence location

Ref-less defaults write Building evidence under:

```text
$BRICK_HOME/project/brick-protocol/buildings/<building_id>/
```

or, when `BRICK_HOME` is unset:

```text
~/.brick/project/brick-protocol/buildings/<building_id>/
```

When the intent declares `project_ref: "project:brick-protocol"`, the driver
derives the repo-local project vessel and writes under:

```text
project/brick-protocol/buildings/<building_id>/
```

For the bundled example above, the root is:

```text
project/brick-protocol/buildings/onboarding-example-0-0607/
```

Important files and directories include:

```text
capture/events.jsonl
  Passive capture events for the Building lifecycle.

evidence/evidence-manifest.json
  The evidence manifest for the Building root.

evidence/claim_trace/
  Support claim traces for Brick, Agent, and Link facts.

work/building-work.json
  The recorded Building work packet.

work/building-map.json
  A support projection of the walked Building map.

work/step-outputs/onboarding-example-0-hello-attempt-1/step-output.json
  The returned payload and per-step support evidence for the first attempt.

raw/
  Raw support streams such as Brick work, Agent return, and Link records.
```

If the Building root already exists, choose a new `building_id` or pass
`--overwrite-existing` deliberately. If the local CLI adapter fails before
returning an AgentFact, the runner records adapter-error frontier evidence and
raises an exception; that still remains support evidence only.

## File-backed preset task (automation helper)

Machine flows (scripts, checkers, pipelines) that already manage a task file
can still use the support/operator helper with a repo-relative
`task_source_ref` instead of inline text. This is an automation helper path,
not the official customer first-run route:

```bash
uv run python3 -c '
from brick_protocol.support.operator.driver import run_building_intake
result = run_building_intake({
    "declared_by": "caller-me",
    "task_source_ref": "brick/templates/tasks/source-template.md",
    "chain_preset_ref": "building-chain-preset:design-contract-only",
    "selected_adapter_ref": "adapter:local",
})
print(result.building_id)
print(result.run_result.lifecycle_write.root)'
```

(No `uv`? Replace `uv run python3` with `PYTHONPATH=support/import_identity python3` — that needs PyYAML installed for your global `python3`.)

Intent dict fields (grounded in
`support/operator/composition_intent.py::materialize_building_intent` and the
`run_building_intake` driver seam):

- `declared_by` (required) — a caller / COO declaration containing a
  `caller` or `coo` token (e.g. `caller-me`, `coo`). Support never authors
  this.
- `task_statement` (human flow) — your task as non-empty inline text; the
  driver records it verbatim as the Building's `work/task.md` evidence.
  Mutually exclusive with `task_source_ref`.
- `task_source_ref` (automation flow) — safe repo-relative path to an
  existing, admitted task file (for example a template under
  `brick/templates/tasks/`). Must exist; its sha256 is recorded. Mutually
  exclusive with `task_statement`; declaring NEITHER also rejects.
- `chain_preset_ref` (required) — a preset present in the Brick template
  catalog registry; it must expand to at least one step.
- `selected_adapter_ref` (required, fail-closed) — support does NOT default
  the adapter; an omitted/blank value hard-fails at entry.
- `building_id` (optional) — defaults to a slug derived from the task source
  + the preset. With `task_statement` the default is a STABLE hash of
  (statement + preset): retrying the same statement with the same preset
  re-derives the same id and rejects loudly against the existing Building
  root ("declared Building plan already exists") instead of duplicating
  roots. Declare `building_id` explicitly for a readable id (or to
  intentionally run the same statement again).
- `selected_model_ref` (optional) — `model:default` is a sentinel meaning
  "the declared adapter picks its own default model".
- `write_scope` (optional) — only if the work needs repository write; omitted
  means read-only.
- `plan_ref` (optional) — defaults to `building-plan:<building_id>`.

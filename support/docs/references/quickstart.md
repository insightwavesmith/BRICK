# Run your first Building

Brick Protocol is a three-axis work protocol for human-agent work: Brick is the work, Agent is the performer, and Link is the transfer/carry/movement between work boundaries. A Building is a declared packet of one or more steps; when you run it, the support runner walks the declared Brick / Agent / Link rows and records support evidence about what was received, what was returned, and what Link facts were declared. That evidence is not source truth, not a success judgment, not a quality judgment, and not Movement authority.

You do not author task files for the common path: SPEAK your task as text
through `brick build --task`. The official customer-facing route is one
surface:

```text
brick build --task "첫 Building을 support evidence only로 기록해 주세요." --preset building-chain-preset:design-contract-only
```

The command is the `preset_task` input path. Graph-shaped work uses the
`assemble()` / `build()` / `fan()` DSL path; raw `graph_packet` CLI input is
retired.

`run_building_intake`, `assemble`, `launch_assembled_building`, and
`goal-approve` are support/operator helpers or advanced/internal paths. They
are not separate customer execution routes. Files dropped at the repository
root (or anywhere unadmitted) are rejected by the admission checker — keep any
scratch files of your own outside the repository.

## Easy Building for bigger work

The product route for bigger work is a declared road over the same public
surface, not a new mode. The customer/operator still starts from a spoken task:

```text
make X
  -> task intake
  -> design fan-out / review
  -> plan confirm
  -> parallel dev lanes
  -> lane QA
  -> final QA
  -> closure
  -> assemble() / build() / fan()
```

If a declared preset exactly preserves the needed shape, use `brick build
--task ... --preset ...`. If the work needs that bigger road, the caller/COO
declares a DSL graph. Support validates and walks the declared Brick / Agent /
Link rows; it does not choose route targets, invent Movement, judge success, or
judge quality. `--large`,
`--dev-lanes`, `_p3_easy_large`, and `lane_return` are not public route
features.

## Customer-entry readiness matrix

This is the minimum cold-start map for a fresh customer or customer-like
session. It is support documentation only: it is not source truth, not a
success judgment, not a quality judgment, and not Movement authority.

| Question | Current customer-facing answer | Evidence / proof limit |
| --- | --- | --- |
| What reads first? | Start at repo-root `README.md`, then this `support/docs/references/quickstart.md`, then `support/docs/references/setup.md` when you need prerequisite and checker details. After `brick init`, read the generated `FIRST_USE.md` under the chosen output root. | `README.md` links this quickstart and setup guide. `support/operator/first_use.py` renders `FIRST_USE.md` after the local example. Whether a customer understands the sequence without help is not proven. |
| Active checkout or frozen/history repo? | Use this product checkout or its release export for active work. The frozen HISTORY repository is for archived evidence only; do not start new customer work there. In this checkout, `brick status` reports the resolved `repo_root`, current `cwd`, entrypoint file, and the default evidence root used by `brick build` when `--output-root` is omitted. Release exports omit `project/`; the first onboard/run creates local project evidence as needed. | `README.md` documents release export and HISTORY separation. `support/operator/cli.py` implements `brick status`. Byte-for-byte release parity and fresh-machine behavior remain not proven until measured. |
| Official Building launch route? | Common customer path: install, run the onboarding wizard, then speak the task through `brick build --task`. Use `--preset` for the declared chain preset. For graph-shaped work, use `assemble()` / `build()` / `fan()`. | This page and `launch-guide.md` document one public CLI execution surface: `brick build --task`/`--preset`, plus the official DSL graph authoring path. Support walks declared rows; it does not choose Movement. Provider reliability, customer comprehension, success, quality, source truth, and Movement authority are not proven by these docs. |
| How does bigger work stay easy? | Treat "make X" as task intake. Use a preset only when it preserves the declared route. For design-first or multi-lane work, caller/COO declares a DSL graph shaped as design fan-out/review -> plan confirm -> parallel dev lanes -> lane QA -> final QA -> closure. | This is route documentation, not a new CLI mode. It does not revive `--large`, `_p3_easy_large`, `--dev-lanes`, `lane_return`, a scheduler/queue/retry runtime, or support-owned route selection. |
| When should the graph be WIDE instead of a single lane? | Before drawing the graph, ask two questions: is the work partitionable, and are the partitions file-disjoint (read-only, or separated write scopes)? If both yes, the default shape is `fan(work partitions x N) -> convergence node -> fan(review lenses) -> closure`. `fan()` is a general parallel stage, not a verification-lens idiom; a `fan()` block must be followed by a convergence node (`fan -> fan` is rejected by the DSL). Same-file writers must stay serial. | Route-shape guidance only, measured on 0703 dogfood (a single-lane serial read of an 11k-line file ground 4 rounds; a 13-way fan partition of the same work closed every node in 1 round). It does not prove provider behavior, success, or quality, and does not add any scheduler or support-owned route selection. |
| How do I read frontier output? | `brick build` exit 0 means the CLI returned support evidence. Customer-visible Building closure is `frontier_kind=complete`. Any other `frontier_kind` is `not_ready`; inspect the printed `evidence_root` before rerunning or escalating. | `support/operator/cli.py` renders `customer_visible_frontier_state=frontier_complete` only for `complete`; non-complete frontiers render `not_ready` and preserve `evidence_root`. This is evidence handling, not a phase PASS or quality judgment. |
| My read-only task ended `human_review_waiting`? | The `work` brick kind DECLARES write intent by contract, so a `work` walk that changes no files pauses at the fake-landing gate (an intentional guard, not an error). Two ways forward: (a) for investigation/observation tasks, use a non-writing kind (e.g. `inspect`) instead of `work`; (b) if the no-change completion is genuinely correct, approve it: `run_approve_entry(<evidence_root>, action="forward", author_ref="human:<you>", repo_root=<repo>, adapter_cwd=<a detached worktree>)` — the walk then closes `complete`. | Measured live (P8 probe 0703): read-only `work` order → gate HOLD → forward disposition → `complete`. The gate consumes the recorded human disposition and does not re-fire. Guard rationale: `p8-dogfood-probe-0703.md` G-1. |
| My build paused after several retries (budget exhausted)? | The engine retries a rejected step automatically (default budget 5). When retries run out, the Building pauses for a human. Read the pause row's reason, then either `action="raise"` with `budget_increment=N` (only when the hold is budget-exhaustion and more attempts could plausibly succeed), `action="stop"` (abandon), or fix the declaration (e.g. an impossible `proof_obligations` command) and relaunch fresh. | Measured live (P8 probe 0703): an impossible declared proof → machine reject → 5 auto-redispatches → budget HOLD, by design. Guidance: `p8-dogfood-probe-0703.md` G-2. Dispositions are human/COO authority; support only records them. |
| Slack expectation? | Slack is optional. The first local path does not require Slack and should not expect a direct Slack check. Operator notification uses `~/.brick/report.env` only after provisioning/source, and real Slack delivery remains gated by declared delivery flags and environment credentials. | `launch-guide.md` notes `source ~/.brick/report.env` for bell/dashboard notifications. Reporter/Slack delivery is support projection only and must not expose credentials or become a scheduler/queue/retry runtime. |
| Where does evidence land? | Ref-less defaults land under `$BRICK_HOME/project/brick-protocol/buildings/<building_id>/`, or `~/.brick/project/brick-protocol/buildings/<building_id>/` when `BRICK_HOME` is unset. Runs that declare `project_ref: "project:brick-protocol"` land in the repo-local vessel `project/brick-protocol/buildings/<building_id>/`. Customer CLI builds use the declared output root and report `evidence_root`; `FIRST_USE.md` repeats that root for the local example. | The root contains `capture/`, `raw/`, `evidence/`, and `work/`. These are support evidence and projections, not source truth or judgments. |
| Not proven / proof limits | A green checker or written Building root is evidence only. Provider behavior, credential readiness, customer comprehension, release/export parity, and fresh-machine install/run behavior are not proven by this page. | Close those with separate run evidence, not by wording in docs. |

## Frontier disposition matrix

This table is a support guide for `onboard approve` / `run_approve_entry`.
The menu is recalculated from recorded hold evidence by
`support/operator/walker_resume.py::hold_disposition_action_menu`; the approve
entry refuses actions outside that menu before writing a disposition row.
Support still does not choose the action, Movement, route target, sufficiency,
success, or quality.

| frontier_kind | hold_reason anchor | Allowed disposition actions | Refused examples |
| --- | --- | --- | --- |
| `agent_incomplete` or `link_paused` | `adapter_error_frontier` (`support/operator/walker_resume.py::_adapter_error_hold_without_return`) | `stop` | `forward`, `raise`, `reroute` |
| `link_paused` | `target_node_budget_exhausted` or `budget_exhausted=True` (`support/operator/walker_resume.py::hold_disposition_action_menu`) | `raise` with positive `budget_increment`, `stop`, or explicit `reroute` | `forward` |
| `human_review_waiting` | `fake_landing_write_scope_diff_absent` or `write_scope_forbidden_diff_present` (`support/operator/frontier_observation.py::_latest_hold_reason`) | `forward`, `stop`, or explicit `reroute` | `raise` |
| `link_paused` | `human_or_coo_gate_pause` (`support/operator/walker_resume.py::hold_disposition_action_menu`) | `forward`, `stop`, or explicit `reroute` | `raise` |

## 가장 빠른 길: 설치 후 진단

`install.sh` 가 끝났다면, 준비 상태 진단은 이 한 줄입니다:

```bash
brick doctor
```

진단은 provider 준비 상태와 증상 -> 처방 표를 보여줍니다. 이후 고객이
직접 쓰는 공식 실행 표면은 `brick build` 하나입니다. provider 없이도
`brick doctor` 와 `brick verify` 는 실행할 수 있습니다.

## AI-runnable onboarding checklist

Fresh clone부터 첫 Building과 dashboard snapshot까지 운영자 AI가 그대로
따라갈 수 있는 확인 줄입니다. `{OWNER}`는 (중괄호까지 함께) 실제 GitHub
org/user로 바꾸세요 (현재 동작 예: insightwavesmith/BRICK).

```text
step: clone + install
command: gh repo clone {OWNER}/BRICK ~/BRICK && sh ~/BRICK/support/onboarding/install.sh
expected: 먼저 "선검사 (preflight):" 체크리스트가 전부 ✓로 나온 뒤 "5) 설치 점검 완료" 와 다음 온보딩 명령이 출력된다.
failure signal: 선검사 단계의 "지금 치세요" 한 줄 처방(pipx/git/uv/python3.11+/디스크/gh 로그인 중 하나) 또는 이후 clone/pull 실패.

step: doctor
command: cd ~/BRICK && brick doctor
expected: provider별 준비 상태 표와 증상 -> 처방 표가 출력되고 exit 0.
failure signal: doctor 자체 stack trace, 또는 repo 루트가 아닌 곳에서 실행한 import 실패.

step: first Building from text
command: cd ~/BRICK && brick build --task "첫 온보딩 빌딩을 support evidence only로 기록해 주세요." --preset building-chain-preset:design-contract-only --building-id quickstart-ai-runnable-001 --adapter adapter:local --timeout 20 --output-root project/brick-protocol/buildings
expected: build_input_mode=preset_task, quickstart-ai-runnable-001, evidence_root=.../project/brick-protocol/buildings/quickstart-ai-runnable-001, frontier_kind가 출력된다. provider 준비 전에는 agent_incomplete/not_ready가 정상 support evidence일 수 있고, closure로 읽는 값은 frontier_kind=complete뿐이다.
failure signal: FileExistsError이면 building_id를 새로 정한다; ModuleNotFoundError이면 uv run 또는 PYTHONPATH를 확인한다; complete가 아닌 frontier_kind는 not_ready로 보고 evidence_root를 inspect한다.

step: dashboard snapshot
command: cd ~/BRICK && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity uv run python3 support/operator/dashboard_export.py --bake-public
expected: "baked support/dashboard/public/dashboard-data.json | buildings N | source_truth False".
failure signal: source_truth가 False가 아니거나, dashboard-data.json 생성 실패, 또는 project evidence shape 거절.

step: checker gate
command: cd ~/BRICK && PYTHONPATH=support/import_identity uv run python3 support/checkers/check_profile.py --all
expected: profile passed: 줄들이 출력되고 마지막 proof-limit 줄 뒤 exit 0.
failure signal: "profile runner rejected evidence:" 뒤 첫 줄이 수리 대상이다. checker green은 support evidence이지 phase PASS가 아니다.
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

`brick doctor` 를 돌리면
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

This example intentionally uses `building-chain-preset:design-contract-only`
with `--adapter adapter:local --timeout 20`: it is a harmless support-evidence
check for first contact, not a repository-changing task and not provider proof.
Because design/review/closure are verdict-bearing lanes, provider readiness may
still be required for `frontier_kind=complete`; without it the expected customer
state is `not_ready` with an evidence root to inspect. `brick build` records support evidence that includes `build_input_mode:
preset_task`, the Building id, the selected adapter, the declared preset, the
evidence root, frontier observation, proof limits, and not-proven facts. The
underlying support/operator helper materializes the selected chain preset into
a declared plan and records your exact words as the Building's `work/task.md`
evidence. That helper is not a separate customer execution route.

Use `--real-provider` after `brick auth login` for real repository-changing
work if you want the CLI to observe Claude, Codex, and Gemini readiness in
declared support order and select the first ready observed-write adapter. An
explicit observed-write `--adapter` still wins.

## Declared graphs: DSL

When caller/COO needs a declared graph, use `assemble()` / `build()` / `fan()`.
Raw `graph_packet` JSON through `brick build --graph` is retired from the
customer CLI. DSL graph materialization is still not permission for support to
invent route targets or Movement.

## Direct plan runner (advanced/internal only)

You can also run a full plan file directly through `run_building_plan`. This is
an internal/operator support path for automation and debugging, not a first-run
instruction and not a separate customer execution route; the customer route
remains `brick build --task` for preset tasks and the DSL graph path for larger
declared graphs. The repository already
ships a verified, runnable first plan at
`brick/building_plans/onboarding-example-0.yaml`; point the runner at it rather
than hand-writing one (a hand-written copy would drift from the real, tested
shape).

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

For an internal/operator direct plan run, copy the bundled plan OUTSIDE the
repository (the repo tree admits no scratch files) and change its top-level
adapter field (the bundled plan declares the adapter only at the top level),
then point `run_building_plan` at your copy. Customer execution should still
use `brick build --task ... --real-provider` or the DSL graph path. Codex is
one explicit adapter example:

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

## File-backed preset task (advanced/internal automation helper)

Machine flows (scripts, checkers, pipelines) that already manage a task file
can still use the support/operator helper with a repo-relative
`task_source_ref` instead of inline text. This is an automation helper path,
not the official customer first-run route; customer runs should speak the task
with `brick build --task` or use the DSL graph path:

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

# Run your first Building

Brick Protocol is a three-axis work protocol for human-agent work: Brick is the work, Agent is the performer, and Link is the transfer/carry/movement between work boundaries. A Building is a declared packet of one or more steps; when you run it, the support runner walks the declared Brick / Agent / Link rows and records support evidence about what was received, what was returned, and what Link facts were declared. That evidence is not source truth, not a success judgment, not a quality judgment, and not Movement authority.

You do not author task files: SPEAK your task as text. The intake seam accepts
your task as a plain `task_statement` string and the machine records it as the
Building's task evidence (`work/task.md`). Files dropped at the repository
root (or anywhere unadmitted) are rejected by the admission checker — keep any
scratch files of your own outside the repository.

## 가장 빠른 길: 위자드

`install.sh` 가 끝났다면, 첫 빌딩까지는 이 한 줄이 전부예요:

```bash
uv run python3 -m brick_protocol.support.operator.onboard codex
```

(host 자리는 `codex | claude | gemini | local` — provider CLI가 하나도 없으면
`local`. provider 없이도 돌아갑니다.) 위자드는 provider 준비 상태 점검 → 연결
설정 안내 → 첫 예제 빌딩(기본은 provider 없이 `adapter:local`, 결과는 임시
폴더에만 기록) → 다음 단계 안내까지 알아서 진행해요. 아래의 손으로 조립하는
경로 없이도 같은 입구(seam, `run_building_intake`)를 통과합니다.

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

## Speak your task: `run_building_intake` with `task_statement`

The human flow is one call — pass your task as text, pick a preset, name the
adapter:

```bash
uv run python3 -c '
from brick_protocol.support.operator.driver import run_building_intake
result = run_building_intake({
    "declared_by": "caller-me",
    "task_statement": "온보딩 화면의 환영 문구를 한 줄로 다듬어 주세요.",
    "chain_preset_ref": "building-chain-preset:design-contract-only",
    "selected_adapter_ref": "adapter:local",
    "project_ref": "project:brick-protocol",  # 일이 쌓일 그릇(project/<id>); 생략하면 1호 기계 기본값(compat)
})
print(result.building_id)
print(result.run_result.lifecycle_write.root)'
```

(No `uv`? Replace `uv run python3` with `PYTHONPATH=support/import_identity
python3` — that needs PyYAML installed for your global `python3`.)

The seam materializes the selected chain preset into a declared plan, runs it,
and lands your exact words verbatim as the Building's `work/task.md` evidence.
`task_statement` and the file-based `task_source_ref` are mutually exclusive
(declaring both rejects, fail-closed); the file form stays available as the
automation path (see the intake section below).

## 직접 조립하고 싶다면: minimal hand-written plan (advanced)

You can also hand-write a full plan — this is the advanced path; the wizard
and the `task_statement` one-liner above cover the common cases without it.
Save this OUTSIDE the repository (for example `/tmp/first-building.yaml` —
the repo tree itself admits no scratch files):

```yaml
plan_ref: building-plan:first-building
owner_axis: Brick
building_id: first-building-001
selected_adapter_ref: adapter:local
selected_model_ref: model:default
proof_limits:
  - support evidence only
  - not source truth
  - not success judgment
  - not quality judgment
  - not Movement authority
not_proven:
  - provider availability
  - quality of returned work
steps:
  - step_ref: first-building-01
    selected_adapter_ref: adapter:local
    selected_model_ref: model:default
    rows:
      - axis: Brick
        row_ref: brick-row:first-building-01
        brick_work_ref: work:first-building-01
        brick_instance_ref: brick-first-building-01
        work_statement: Return one JSON object with observed_evidence and not_proven fields only. Do not choose Movement, success, or quality.
        comparison_rule: Observe only whether returned fields match required_return_shape.
        required_return_shape: observed_evidence, not_proven
      - axis: Agent
        row_ref: agent-row:first-building-01
        agent_object_ref: agent-object:coo
      - axis: Link
        row_ref: link-row:first-building-01
        movement: forward
        target_ref: building-boundary:first-building-closed
        declared_gate_refs:
          - link-gate:default-transition
        building_lifecycle:
          state: closed
          reason: First Building example closes after one declared step.
```

The plan declares the whole road up front. The Brick row says what work is requested and which return fields are expected. The Agent row names the provider-neutral Agent Object that receives the work. The Link row declares the movement and closed target for this one-step example; support does not choose that movement.

## Run it

From the repository root (`uv run` uses the `.venv` that `install.sh` / `uv sync` prepared, where brick-protocol and PyYAML live):

```bash
uv run python3 -c 'from brick_protocol.support.operator.run import run_building_plan; result = run_building_plan("/tmp/first-building.yaml"); print(result.building_id); print(result.lifecycle_write.root); print("\n".join(str(path) for path in result.written_files))'
```

No `uv`? The bare-Python alternative works only if PyYAML is installed for your global `python3`:

```bash
PYTHONPATH=support/import_identity python3 -c 'from brick_protocol.support.operator.run import run_building_plan; result = run_building_plan("/tmp/first-building.yaml"); print(result.building_id); print(result.lifecycle_write.root); print("\n".join(str(path) for path in result.written_files))'
```

For `adapter:local` (the default above), the COO Agent Object uses its registered local callable reference: no provider CLI, no login, runs in-process. That is useful for a smoke run of the support path, but it does not prove provider behavior or work quality.

### 업그레이드: 실제 provider로 (adapter:codex-local)

To run the same shape on the real local Codex CLI instead, change these fields (top-level AND per-step):

```yaml
selected_adapter_ref: adapter:codex-local
selected_model_ref: model:codex:default
```

`adapter:codex-local` invokes the local Codex CLI in read-only mode for this plan because the Brick row has no `write_scope`. It requires the local `codex` command and local provider state to be available — if the CLI is missing you get a `local_cli_missing` adapter error (처방은 위의 증상→처방 표). `adapter:claude-local` works the same way for the Claude CLI.

## Evidence location

By default, Building evidence is written under:

```text
project/brick-protocol/buildings/<building_id>/
```

For the example above, the root is:

```text
project/brick-protocol/buildings/first-building-001/
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

work/step-outputs/first-building-01-attempt-1/step-output.json
  The returned payload and per-step support evidence for the first attempt.

raw/
  Raw support streams such as Brick work, Agent return, and Link records.
```

If the Building root already exists, choose a new `building_id` or pass `overwrite_existing=True` deliberately. (One exception: a root holding ONLY the intake seam's own `declared-building-plan.json` is admitted, so `run_building_intake` does not collide with itself.) If the local CLI adapter fails before returning an AgentFact, the runner records adapter-error frontier evidence and raises an exception; that still remains support evidence only.

## From a task FILE (the automation path): `run_building_intake` with `task_source_ref`

Machine flows (scripts, checkers, pipelines) that already manage a task file
hand the intake seam a repo-relative `task_source_ref` instead of inline text
(the two are mutually exclusive — declaring both rejects, fail-closed):

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
`support/operator/composition.py::materialize_building_intent` and the
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

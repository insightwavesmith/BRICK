# Setup and run guide

This guide gets a newcomer from a fresh checkout to a green checker gate and a first Building run. Brick Protocol is a three-axis work protocol for human-agent work: Brick is the work, Agent is the performer, and Link is the transfer/carry/movement between work boundaries. The repository is a clean-room protocol repository, not a runtime engine. The support runner walks a declared Building plan and records support evidence; that evidence is not source truth, not a success judgment, not a quality judgment, and not Movement authority.

For the guided first-run route, see `quickstart.md` in this same directory.
The official customer-facing Building route is one surface: `brick build`.
Use `brick build --task ... --preset ...` for the `preset_task` path and
`brick build --graph <packet.json>` for a declared `graph_packet`. This guide
covers prerequisites, the checker gate, and the advanced `run_building_plan`
signature in detail.

## Prerequisites

- **Python >= 3.11** (`requires-python` in `pyproject.toml`). The support runner and checkers are stdlib-first Python. Run all commands from the repository root.
- **The `codex` CLI** (only if you want to use `adapter:codex-local`). The Codex adapter invokes the local `codex` command and local provider state. If the CLI is missing, an adapter run raises a `local_cli_missing` adapter error and the runner records frontier evidence instead of an AgentFact. You do not need the `codex` CLI to run the checker gate, and you do not need it for the built-in `adapter:local` callable path.
- **PyYAML** — a declared runtime dependency (`pyproject.toml`), installed by `uv sync` / the installer. It is required on EVERY intake/preset run: the operator surface loads the split brick catalog and preset registry via YAML (`support/operator/plan_rendering.py`), not only when your own plan file is `.yaml`/`.yml`. (A hand-written JSON plan passed straight to `run_building_plan` is the one path that does not touch it.)

The Python import identity lives under `support/import_identity/brick_protocol/`. The package is not installed into site-packages, so every command below puts that directory on `PYTHONPATH`. The namespace is `brick_protocol`.

## Run the checker gate

The checker gate is the support-evidence baseline. Run every admitted profile:

```bash
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all
```

A green gate is **exit code 0**. On success the runner prints one `profile passed:` line per profile (24 profiles live under `support/checkers/profiles/`), then the closing proof-limit line. On any rejection it prints `profile runner rejected evidence: ...` to stderr and returns exit code 1.

Run a single profile by name (the `.yaml` suffix is optional, and `-`/`_` are interchangeable in the name):

```bash
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile core
```

The profile name resolves against `support/checkers/profiles/`. Current profile names include `core`, `building_automation`, `agent_axis_behavioral`, `link_routing_behavioral`, `tier_a_three_axis_conformance`, and others — list them with `ls support/checkers/profiles/`.

Two more flags exist:

```bash
# Run the parser/rule self-test (no profiles touched):
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --self-test

# Inspect a repo other than the current directory:
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all --repo /path/to/repo
```

`--profile` and `--all` are mutually exclusive. Passing both rejects with exit code 1. A profile pass is support evidence only: it does not prove source truth, success, quality, Movement authority, or provider behavior.

## Run a first Building

A Building plan declares the whole road up front: each step carries exactly three rows (Brick, Agent, Link). The runner walks the declared rows, calls the selected adapter for each step, and writes one accumulated Building root. It never invents Movement, GateFacts, or judgments.

The human flow needs NO file at all: pass your task as text through
`brick build --task`. Choose the declared preset with `--preset`; the CLI
records `build_input_mode: preset_task` and writes the Building evidence root.
When caller/COO already has a declared graph packet, use `brick build --graph
<packet.json>`; that records `build_input_mode: graph_packet`.

The lower-level support/operator helpers (`run_building_intake`, `assemble`,
`launch_assembled_building`, and `goal-approve`) are helper or
advanced/internal paths for operators, automation, and debugging, not first-run
instructions and not separate customer execution routes.

To inspect the lower-level runner directly as an advanced/internal operator
path, use the bundled, verified-runnable first plan that ships in the repository at
`brick/building_plans/onboarding-example-0.yaml` (it is GRAPH-shaped, which the
runner requires) and run it through the advanced `run_building_plan` surface.
This is not the customer first-run route; use `brick build --task` or `brick
build --graph` for customer execution:

```bash
PYTHONPATH=support/import_identity python3 -c 'from brick_protocol.support.operator.run import run_building_plan; result = run_building_plan("brick/building_plans/onboarding-example-0.yaml"); print(result.building_id); print(result.lifecycle_write.root); print("\n".join(str(path) for path in result.written_files))'
```

`run_building_plan` accepts a plan as a mapping, or a path to a `.json` /
`.yaml` / `.yml` file. Its real signature (from `support/operator/run.py`) is:

```python
def run_building_plan(
    plan,                              # Mapping | str | Path  (plan dict or file path)
    *,
    output_root=DEFAULT_BUILDINGS_ROOT,  # where the Building root is written
    overwrite_existing=False,            # reuse an existing Building root?
    local_callables=None,                # name -> callable, for adapter:local
    command_runner=None,                 # injected CLI runner (testing)
    adapter_cwd=None,                    # working dir for the local CLI adapter
    adapter_timeout_seconds=120,         # per-adapter-call timeout
    proof_limits=None,                   # if set, OVERRIDES the plan's own proof_limits (then merged with adapter/completion limits)
    report_env=None,                     # env mapping for report delivery sinks
    report_slack_sender=None,            # injected Slack sender (testing)
)
```

The fields most newcomers touch:

- **`output_root`** — directory the Building root is written under. Defaults to `DEFAULT_BUILDINGS_ROOT`, the ref-less caller-local evidence home: `$BRICK_HOME/project/brick-protocol/buildings/` when `BRICK_HOME` is set, otherwise `~/.brick/project/brick-protocol/buildings/`. The actual root is `output_root/<building_id>`. If the intent declares `project_ref: "project:brick-protocol"` instead of relying on the ref-less default, the driver derives the repo-local vessel root through `buildings_root_for(project_ref)`: `project/brick-protocol/buildings/`.
- **`overwrite_existing`** — defaults to `False`. If the Building root already exists and this is `False`, the runner raises `FileExistsError` and tells you to choose a new `building_id` or pass `overwrite_existing=True`. Pass `True` deliberately to reuse a root.
- **`adapter_cwd`** — the working directory handed to the local CLI adapter (e.g. where `codex` runs). Leave it `None` to use the process default.
- **`adapter_timeout_seconds`** — per-adapter-call timeout, default `120`. A slower-than-this Codex call raises a `local_cli_timeout` adapter error and the runner records frontier evidence.

`run_building_plan` dispatches to the dynamic graph walker, so the plan **must**
be GRAPH-shaped (`plan_shape: graph` plus non-empty `brick_steps`,
`link_edges`, and `execution_order`). A non-graph packet is rejected at the
walker admission guard (`support/operator/walker_kernel.py`) with a
`ValueError`. The bundled `brick/building_plans/onboarding-example-0.yaml` is
already graph-shaped, which is why the run command above works as written.

### Choosing the adapter

The adapter is declared in the plan, not passed as an argument. The bundled
first plan uses `adapter:local`, so it does not require a provider CLI and
does not prove provider behavior. The selected adapter must be one of the Agent
Object's `adapter_refs`. The admitted provider-neutral adapter refs are
`adapter:local`, `adapter:codex-local`, `adapter:codex-fugu-local`,
`adapter:claude-local`, `adapter:gemini-local`, and `adapter:chat-session`.
`adapter:codex-local` invokes the local `codex` CLI; `adapter:gemini-local`
invokes the local Gemini CLI and uses `GEMINI_API_KEY` or `GOOGLE_API_KEY` for
Gemini auth; `adapter:chat-session` is the parked / human-as-agent adapter.

To smoke-test the support path without any provider, use the built-in local callable:

```yaml
selected_adapter_ref: adapter:local
selected_model_ref: model:default
```

For `adapter:local` the Agent Object uses its registered local callable
reference. This exercises the support runner end to end but does **not** prove
provider behavior or work quality. For real repository-changing work through
the customer CLI, authenticate first and use `brick build --task "..."
--real-provider`, or choose an explicit observed-write adapter.

### Read-only by default

`adapter:codex-local` invokes the Codex CLI in read-only mode for a step when the Brick row declares no `write_scope`. The bundled plan declares none, so the first run is read-only. Write scope is opt-in per Brick row.

## Where evidence lands

Each run writes one Building root under `output_root/<building_id>`.
With the ref-less default, that means:

```text
$BRICK_HOME/project/brick-protocol/buildings/<building_id>/
```

or, when `BRICK_HOME` is unset:

```text
~/.brick/project/brick-protocol/buildings/<building_id>/
```

With a declared `project_ref: "project:brick-protocol"`, the driver writes to
the repo-local project vessel:

```text
project/brick-protocol/buildings/<building_id>/
```

Inside that root (see `quickstart.md` for the full list):

```text
capture/events.jsonl
  Passive capture events for the Building lifecycle.

evidence/
  evidence-manifest.json plus evidence/claim_trace/ — support claim
  traces for Brick, Agent, and Link facts.

work/
  building-work.json, building-map.json, and the per-step outputs.

work/step-outputs/<step_ref>-attempt-<n>/step-output.json
  The returned payload and per-step support evidence for each attempt.

raw/
  Raw support streams (Brick work, Agent return, Link records).
```

The `result` object returned by `run_building_plan` exposes `result.building_id`, `result.lifecycle_write.root` (the Building root path), and `result.written_files` (every file written), so you can print exactly where evidence went.

## Honest limitations

- **Support records, it does not judge.** Every artifact carries proof-limit lines stating it is not source truth, not success, not quality, and not Movement authority. Reviews and checkers are likewise not source truth and not Movement authority.
- **Read-only adapter.** A Brick row with no `write_scope` runs read-only; this is the default.
- **Adapter failures are recorded, not hidden.** If the local CLI adapter fails before returning an AgentFact (missing CLI, timeout, non-zero exit, rejected return shape), the runner writes adapter-error frontier evidence and then raises an exception. That frontier evidence is still support evidence only.
- **Provider behavior and customer comprehension are not proven.** Running a
  plan or reading these docs does not prove the provider behaved correctly,
  that a customer understood the route, that the work is correct, or that the
  work is high quality. Those are not-proven facts; the example plan and CLI
  packets list them explicitly.
- **Smith remains closure authority and commit/push authority.** A green gate or a written Building root is evidence, not a decision.

# Customer-Ready BRICK Live Empirical Investigation

Date: 2026-06-26
Live repo root: `/Users/smith/.brick/worktrees/struct-surgery-0623`
HEAD: `3d22955cab63801b530d2253fa63a0e527f5f834`
Mode: read-only empirical investigation, except this saved report artifact.

## Executive Summary

This rerun deliberately discards the prior `/Users/smith/projects/brick-protocol`
inspection. The live pin is valid: `support/operator/cli.py` exists, `brick`
entrypoint resolves to `brick_protocol.support.operator.cli:main`
(`pyproject.toml:22-23`), and `run_customer_building_in_sandbox` is present in
both CLI and driver (`support/operator/cli.py:32`,
`support/operator/cli.py:114`, `support/operator/driver.py:477`).

Area recommendations:

| Area | Customer-ready verdict | Reason |
| --- | --- | --- |
| Area 1 - Building launch ergonomics | HOLD for customer-ready launch; FORWARD for a narrow launcher-design repair | Preset `brick build` is one-call and sandboxed, but can return exit 0 with `frontier_kind=agent_incomplete`; custom graph has a Python launcher (`launch_assembled_building`) that absorbs the four footguns, but no equivalent CLI public surface and it sits outside the sealed driver public intake. |
| Area 2 - Customer onboarding | HOLD | Installer failures are mostly loud, but MCP/skills/recording/Slack are advisory and can leave a customer with an apparently OK init while important toolchain pieces are absent, stale, not trusted, or not auto-delivered. COO operating-chain is not delivered by MCP initialize. Doctor omits Gemini readiness. Verify path is slow and can enter provider subprocess waits. |
| Area 3 - God-module decomposition | HOLD for split/delete; FORWARD for guard-first freeze inventory | The three large files remain large (`9808 / 10219 / 3803` LOC), but live registry does not set decomposition targets for them. Checker-diet split profiles coexist with the 195KB original, but they preserve only a small subset of original assertion labels; original deletion would silently drop many negative cases. |

Largest blockers:

1. Launch honesty gap: `_cmd_build` returns 0 after emitting a support packet
   regardless of frontier kind (`support/operator/cli.py:241-247`). Main probe
   produced `frontier_kind=agent_incomplete` in 31.33s while exit remained 0.
2. Onboarding advisory success gap: `run_install_wizard()` records advisory
   step status separately and gates only on example `ok` (`support/operator/onboard.py:1181-1217`);
   renderer still defaults a missing step `ok` to visual `ok`
   (`support/operator/cli.py:415-424`).
3. Checker/decomposition proof gap: the split checker profiles are explicit
   "staging copies only" (`support/checkers/profiles/building_skill_preset_agent_resource_boundary.yaml:165-175`,
   `support/checkers/profiles/building_skill_preset_builder_composition.yaml:265-274`,
   `support/checkers/profiles/building_skill_preset_intake_adapter_gate.yaml:121-131`),
   and original-only assertion labels remain numerous.

Prior claim disposition:

| Claim | Verdict | Evidence |
| --- | --- | --- |
| `support/operator/cli.py`, `assembly.py`, `first_use.py` absent | FALSE on live line | Files exist and are tracked; `cli.py` has 592 LOC, `assembly.py` 1405 LOC, `first_use.py` 105 LOC. |
| `brick build --task` hides worktree/output/sandbox for preset path | CONFIRMED | `_run_build` calls `run_customer_building_in_sandbox` and emits isolation/evidence/frontier packet (`support/operator/cli.py:108-152`). |
| Custom graph still only hand-wired through assemble -> worktree -> run_building_plan | DRIFT/PARTIAL | Direct hand-wiring still exists and footguns reproduce, but live `onboard.launch_assembled_building()` now absorbs ComposedGraph persistence, vessel output, worktree ownership, and name collision (`support/operator/onboard.py:1728-1910`). It is not exposed as `brick build` CLI. |
| `run_composed_graph_intake` is public | FALSE | It is explicitly internal/checker-only (`support/operator/driver.py:334-390`) and absent from `driver.__all__` (`support/operator/driver.py:1525-1532`); checker enforces that (`support/checkers/check_driver_public_intake_seal.py:118-160`). |
| Fresh-machine proof exists via checker lint | FALSE | `install_script_lint` states it is structural/safety lint only and not a real fresh-machine install proof (`support/checkers/lib/kernel_checks.py:3365-3386`, `support/checkers/lib/kernel_checks.py:3445-3455`). |
| Doctor covers Gemini readiness | FALSE | `SUPPORTED_HOSTS` contains only codex/claude/local (`support/operator/onboard.py:131-141`); doctor iterates that tuple (`support/operator/onboard.py:1297-1329`). |
| God-module LOC roughly `~10231 / ~10222 / ~3803` | CONFIRMED/DRIFT | Live counts: `kernel_checks.py=9808`, `case_runners.py=10219`, `walker_kernel.py=3803`; prior ordering was partly off, but the scale claim holds. |
| Original 195KB hardening profile coexists with 3 condensed split profiles | CONFIRMED | Original: 4170 LOC / 194810 bytes; split profiles: 175, 274, 131 LOC. |
| Split profiles conserve original assertions | FALSE / NOT PROVEN | Original has 97 labels; split union has 12 matching labels, 85 original-only labels by measured label-set comparison. |

## Command Evidence

Start verification:

```text
pwd
=> /Users/smith/.brick/worktrees/struct-surgery-0623

git rev-parse --short HEAD
=> 3d22955

git rev-parse HEAD
=> 3d22955cab63801b530d2253fa63a0e527f5f834

git ls-files support/operator/cli.py
=> support/operator/cli.py

grep -rl run_customer_building_in_sandbox support/operator/
=> support/operator/cli.py
=> support/operator/driver.py
=> __pycache__ hits also present
```

Initial status before this report had no tracked source edits, only pre-existing
untracked Gemini evidence/status paths under:

```text
project/brick-protocol/buildings/gemini-local-removal-0626/
project/brick-protocol/buildings/gemini-local-trim-0626/
project/brick-protocol/status/inbox/brick-protocol-gemini-local-*.json
```

Measured LOC and size:

| File | LOC | Bytes / du |
| --- | ---: | ---: |
| `support/operator/cli.py` | 592 | not separately byte-counted |
| `support/operator/driver.py` | 1532 | not separately byte-counted |
| `support/operator/assembly.py` | 1405 | not separately byte-counted |
| `support/operator/run.py` | 2217 | not separately byte-counted |
| `support/operator/onboard.py` | 2739 | not separately byte-counted |
| `support/connection/mcp_projection.py` | 659 | not separately byte-counted |
| `support/connection/agent_resources.py` | 1829 | not separately byte-counted |
| `support/checkers/lib/kernel_checks.py` | 9808 | 434307 bytes / 428K |
| `support/checkers/lib/case_runners.py` | 10219 | 474450 bytes / 464K |
| `support/operator/walker_kernel.py` | 3803 | 173030 bytes / 172K |
| `support/checkers/module_registry.yaml` | 1842 | 92559 bytes |
| `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml` | 4170 | 194810 bytes / 192K |

Profile directory: 28 `*.yaml` files at maxdepth 1.

Timed probes:

| Command / probe | Runtime | Exit | Result |
| --- | ---: | ---: | --- |
| `brick_protocol.support.operator.cli doctor --json` | 0.59s | 0 | Rows: gh, codex, claude, local; no Gemini row. |
| MCP JSON-RPC initialize/tools/resources/coo-context direct Python probe | 0.19s | 0 | initialize instructions short; COO chain only via tool/resource. |
| Main `brick build --task ... --adapter adapter:local --output-root /tmp/...` | 31.33s | 0 | `isolation_mode=worktree`, `worktree_disposed=true`, `frontier_kind=agent_incomplete`. |
| A2 CLI build probe | 21.34s | 0 | Same pattern; subagent observed step adapter resolving to `adapter:claude-local`. |
| A2 direct `run_building_intake` graph preset | 5.43s | 0 | `plan_shape=graph`, `walker_mode=dynamic`, adapter timeout. |
| A2 direct assemble local no-write `work` graph | 0.56s | 0 | `frontier_kind=complete` with built-in local callable; not quality/success proof. |
| `building_operator_driver0` profile, main run with PYTHONPATH | 217.12s | 130 after manual interrupt | Stuck in `onboard_seam_case` -> provider subprocess wait. |
| F3 `building_operator_driver0` profile with PYTHONPATH | 190.64s | 130 after manual interrupt | Same slow path. |

## Area 1 - Building-Launch Ergonomics

### Current Public Launch Structure

The `brick` console entrypoint is active (`pyproject.toml:22-23`). `support/operator/cli.py`
is explicitly the customer-facing CLI support entrypoint and bootstraps import
identity (`support/operator/cli.py:1-6`, `support/operator/cli.py:13-18`).

`brick build` path:

1. Parser exposes `build` with `--task`, `--task-source-ref`, `--preset`,
   `--adapter`, `--real-provider`, `--building-id`, `--declared-by`,
   `--output-root`, `--overwrite-existing`, and `--timeout`
   (`support/operator/cli.py:508-535`).
2. `_build_intent()` turns `--task` into inline `task_statement`; absent task uses
   `task_source_ref` (`support/operator/cli.py:82-105`).
3. `--real-provider` upgrades the default adapter to `adapter:codex-local` if
   the user did not pass an explicit adapter (`support/operator/cli.py:82-89`).
4. `_run_build()` creates output root and calls `run_customer_building_in_sandbox`
   (`support/operator/cli.py:108-121`).
5. It returns a support packet with `isolation_mode`, `base_sha`, `worktree_path`,
   `evidence_root`, `frontier_kind`, `commit_sha`, `plan_path`, `plan_shape`,
   and `walker_mode` (`support/operator/cli.py:123-152`).
6. `_cmd_build()` prints that packet and returns 0 unconditionally if no exception
   is raised (`support/operator/cli.py:241-247`).

`run_building_intake()` is the preset/materialized-intent core seam. It records
that it is pure support mechanics and does not choose Movement, preset, success,
sufficiency, or quality (`support/operator/driver.py:186-195`). It accepts either
`task_source_ref` or `task_statement`, carries inline task body through the plan,
rejects ambiguous source declarations, and writes the materialized plan to
`output_root/<building_id>/declared-building-plan.json`
(`support/operator/driver.py:197-253`). It rejects `project_ref` plus explicit
`output_root` before materialization (`support/operator/driver.py:267-275`),
requires `plan_shape: graph` (`support/operator/driver.py:282-289`), derives
vessel output through `buildings_root_for(project_ref)` when present
(`support/operator/driver.py:291-303`), writes JSON plan (`support/operator/driver.py:303-310`),
then calls `run_building_plan(...)` with `adapter_cwd` threaded
(`support/operator/driver.py:312-321`).

`run_customer_building_in_sandbox()` adds the customer safety bracket. It is a
thin wrapper over `run_building_intake`, and its docstring states that live/working
tree is never written, dispatch runs in an engine-created disposable git worktree,
and code output is committed only on genuine completion (`support/operator/driver.py:477-517`).
The shared `_run_in_worktree_sandbox()`:

- falls back to a temp dir when git/worktree probing fails, with adapter writes
  kept out of the live tree (`support/operator/driver.py:584-612`);
- probes worktree capability first (`support/operator/driver.py:614-620`);
- creates detached worktree at resolved base SHA (`support/operator/driver.py:621-629`);
- runs dispatch with both `repo_root` and `adapter_cwd` pointing at sandbox
  (`support/operator/driver.py:635-638`);
- observes durable evidence frontier and commits only when `frontier_kind == "complete"`
  (`support/operator/driver.py:639-656`);
- disposes the worktree in `finally` (`support/operator/driver.py:657-671`).

`run_building_plan()` is still the public single-Building run surface. It accepts
`Mapping[str, Any] | str | Path`, turns it into a packet through `_fixture_mapping`,
auto-loads report env when `report_env` is falsy, and always dispatches to
`_run_dynamic_graph_walker` (`support/operator/run.py:544-607`).

### Custom Graph Structure

The live line has a real assembly front door:

- `ComposedGraph` stores `composed_plan` as a mapping and exposes `as_intake_args()`
  (`support/operator/assembly.py:167-205`).
- `assembly.build(items)` compiles the ergonomic list/fan syntax into `GraphSpec`
  (`support/operator/assembly.py:516-529`).
- `assemble(graph, ...)` lowers the graph, validates fan-in, calls `compose_building`,
  freezes task carry, and returns a `ComposedGraph`
  (`support/operator/assembly.py:687-762`).

There is also an operator-facing Python launcher:

- `launch_assembled_building(composed, ...)` is exported from `onboard.__all__`
  (`support/operator/onboard.py:2709-2735`).
- It explicitly states it launches an already `assemble()`-d `ComposedGraph`
  with no forced human gate (`support/operator/onboard.py:1728-1748`).
- It names and absorbs the four known sharp edges:
  ComposedGraph object vs dict (`support/operator/onboard.py:1752-1756`),
  vessel output root (`support/operator/onboard.py:1757-1762`),
  worktree ownership (`support/operator/onboard.py:1763-1767`),
  and `build` name collision (`support/operator/onboard.py:1768-1771`).
- It rejects non-`ComposedGraph` with a friendly error (`support/operator/onboard.py:1792-1810`).
- It derives durable root from `project_ref` or `DEFAULT_BUILDINGS_ROOT`
  (`support/operator/onboard.py:1815-1832`).
- It persists `composed.composed_plan` to JSON before calling `run_building_plan`
  (`support/operator/onboard.py:1834-1852`, `support/operator/onboard.py:1856-1883`).
- It uses `_run_in_worktree_sandbox` for one worktree per launch
  (`support/operator/onboard.py:1885-1910`).

This means the prior "custom graph still requires the caller to own all four
sharp edges" claim is stale on the Python API. The gap is narrower: the Python
one-call exists, but it is not a `brick build` CLI path and it is outside the
sealed driver public intake vocabulary.

### Sealed / Bypass-Prohibited Surfaces

The driver public-intake seal is explicit:

- Public Building-making intake set is exactly `{"run_building_intake"}`;
  sealed internal intake is `{"run_composed_graph_intake"}`;
  assembly is out of scope (`support/checkers/check_driver_public_intake_seal.py:19-29`).
- `run_composed_graph_intake` docstring must open with the internal/checker-only
  seal (`support/checkers/check_driver_public_intake_seal.py:104-115`).
- `run_building_intake` must remain in `driver.__all__`, and
  `run_composed_graph_intake` must not leak through exports
  (`support/checkers/check_driver_public_intake_seal.py:118-132`).
- Mutation RED appends `run_composed_graph_intake` to exports and must reject
  (`support/checkers/check_driver_public_intake_seal.py:135-160`).
- Profile text pins the same boundary and proof limits
  (`support/checkers/profiles/driver_public_intake_seal.yaml:1-35`).
- Actual driver exports include only `run_building_intake`,
  `run_customer_building_in_sandbox`, and `run_declared_portfolio` among run verbs
  (`support/operator/driver.py:1525-1532`).

Therefore a minimal custom-graph launcher must not simply export
`run_composed_graph_intake`. The seam to reuse is the worktree bracket
`_run_in_worktree_sandbox` or an admitted public wrapper around the already
exported `onboard.launch_assembled_building`, with a checker update that preserves
the seal: raw composed-graph intake stays internal, public launch persists an
already caller/COO-declared graph and walks it through the same sandbox bracket.

### Empirical Launch Gaps

Main probe:

- Command: `python3 -m brick_protocol.support.operator.cli build --task ... --adapter adapter:local --output-root /tmp/... --overwrite-existing --json`.
- Runtime: 31.33s.
- Exit: 0.
- Packet: `isolation_mode=worktree`, `worktree_disposed=true`,
  `frontier_kind=agent_incomplete`, `commit_sha=""`,
  `plan_shape=graph`, `walker_mode=dynamic`.

This proves the wrapper works as support evidence, but it does not prove a
successful build. `_cmd_build()` returning 0 over `agent_incomplete` is a
customer-facing honesty gap (`support/operator/cli.py:241-247`).

A2 probes add:

- CLI `adapter:local` build can materialize into a step that uses
  `adapter:claude-local` and times out. This indicates selected adapter at the
  intent surface is not necessarily the effective per-step adapter for the preset.
  That is a customer surprise, especially because CLI packet reports top-level
  `adapter_ref`.
- Direct `run_building_intake` graph preset reproduced dynamic graph run and
  timeout.
- Candidate linear presets `building-chain-preset:onboarding-example-linear` and
  `building-chain-preset:onboarding-example` fail-closed as absent from catalog.
- Direct assembly no-write `work` path with local callable can complete quickly
  (0.56s), but that is not the same as `brick build` preset path.
- `run_building_plan(composed)` fails because `ComposedGraph` is not a
  Mapping/str/Path; `run_building_plan(composed.composed_plan)` runs. This
  footgun is still real on direct use and absorbed by `launch_assembled_building`
  (`support/operator/onboard.py:1752-1756`).
- `project_ref + output_root` fail-closes as ambiguous (`support/operator/driver.py:267-275`).
- `assembly.build` and `onboard.build` are both named `build` but mean different
  things (`support/operator/assembly.py:516-529`,
  `support/operator/onboard.py:1516-1532`).

### Fix Would Touch

Minimal customer-ready launch repair should touch:

- `support/operator/cli.py`: expose a CLI/custom-graph launch or an explicit
  "assembled graph launch" command, and gate exit code/wording on frontier kind
  rather than returning 0 for non-complete support packets.
- `support/operator/onboard.py`: either graduate `launch_assembled_building`
  contract into the public operator launch surface or move the wrapper to a
  better-named module; preserve its four-footgun absorption.
- `support/operator/driver.py` and `support/checkers/check_driver_public_intake_seal.py`:
  update the seal only if the admitted public graph launch lives in driver;
  do not export `run_composed_graph_intake` raw.
- `support/operator/assembly.py`: keep `ComposedGraph` contract stable and
  document direct-run boundary.

Risk:

- Opening raw graph intake risks bypassing `driver_public_intake_seal`.
- Hiding non-complete frontier behind exit 0 can mislead customers into thinking
  the build completed.
- Any fix touching graph launch must preserve Brick/Agent/Link attribution:
  Brick owns declared graph/work rows, Agent owns performer resource/return,
  Link owns Movement/gates/targets, Support only persists and walks.

Required discipline: feature-design plus checker-first. Add a seal-preserving
checker before changing the public surface; then prove preset launch and custom
graph launch both use the sandbox bracket and report frontier honestly.

## Area 2 - Customer Onboarding

### Install Script Path

`support/onboarding/install.sh` is loud-fail for prerequisites:

- It uses `set -eu` (`support/onboarding/install.sh:45`).
- It checks Python 3.11 and returns 1 on missing/old Python
  (`support/onboarding/install.sh:73-87`).
- It installs/locates `uv`, and returns 1 if unavailable
  (`support/onboarding/install.sh:89-105`).
- Fresh clone requires `BRICK_REPO`, `gh`, and `gh auth status`, and fails with
  plain guidance if missing/unauthed (`support/onboarding/install.sh:107-137`).
- It runs `uv sync` (`support/onboarding/install.sh:139-142`).
- It requires `pipx`, installs editable entrypoint, and verifies executable path
  (`support/onboarding/install.sh:144-177`).
- It then runs `brick init --non-interactive --repo "$target"` by absolute path;
  under `set -eu`, nonzero init aborts before completion text
  (`support/onboarding/install.sh:179-184`).

But the script itself admits its checker is not fresh-machine proof:
comments say structural lint does not prove actual fresh install
(`support/onboarding/install.sh:41-43`), and the checker repeats the same limit
(`support/checkers/lib/kernel_checks.py:3365-3386`,
`support/checkers/lib/kernel_checks.py:3445-3455`).

### Init / Wizard Path

`brick init` combines doctor, MCP registration, skills placement, recording
hooks, Slack provision, onboard/example, and verify:

- `_cmd_init()` passes `host` default `claude`, `allow_real_provider=False`,
  and plugin/recording/slack options into `run_install_wizard`
  (`support/operator/cli.py:281-311`).
- Verify runs `check_profile --all` at the end unless skipped
  (`support/operator/cli.py:351-363`).
- Init exits 1 on build error or verify red; skipped verify does not contribute
  (`support/operator/cli.py:403-412`).

The wizard itself makes only the example hard gate:

- It documents that each step degrades to advisory and continues, with only the
  example fatal (`support/operator/onboard.py:1122-1150`).
- It runs doctor, MCP register, skills place, recording, Slack, and onboard/example
  in order (`support/operator/onboard.py:1152-1179`).
- It sets `fatal_ok = example.get("ok") is True`
  (`support/operator/onboard.py:1181-1190`).
- It records advisory step ok only when each step explicitly says `ok is True`
  (`support/operator/onboard.py:1190-1202`).
- It returns aggregate `ok=fatal_ok`, plus `advisory_step_ok` and `not_proven`
  (`support/operator/onboard.py:1207-1217`).

This is more honest than a fully silent success in JSON, but the plain renderer
still has a visual trap: for wizard steps, `step.get("ok", True)` renders missing
`ok` as `ok` (`support/operator/cli.py:415-424`). Also, advisory failures do not
block init if the example and verify pass.

### Clean Machine Scenario: Claude Logged In Only, No Codex, No Slack

Expected code-path classification:

| Step | Behavior | Evidence |
| --- | --- | --- |
| Install prerequisites | Loud fail if missing Python/uv/gh/pipx/auth/entrypoint | `support/onboarding/install.sh:73-184` |
| `brick init --host claude` preflight | Observes Claude CLI readiness, but not login proof; readiness is CLI runnable | `support/operator/onboard.py:187-209` |
| First example | Defaults to local fallback because CLI passes `allow_real_provider=False` | `support/operator/cli.py:299-311`, `support/operator/onboard.py:249-303` |
| MCP register | If Claude CLI available, runs `claude mcp add`; always also merges Codex MCP config to `~/.codex/config.toml` | `support/operator/onboard.py:772-841` |
| Skills place | Installs rendered Agent skills under `~/.claude/skills/<name>/SKILL.md`; does not prove app reload/native triggering | `support/operator/onboard.py:874-920` |
| Recording setup | Writes repo-local `.claude` and `.codex` hook config; Codex trust still must be accepted later | `support/operator/onboard.py:440-478`, `support/operator/onboard.py:682-737` |
| Slack | No token/no file is `ok=True`, `action=skipped`, `slack_configured=False` | `support/operator/onboard.py:1029-1119` |
| Verify | Runs `--all` unless skipped; may be slow/hang in provider subprocess path | `support/operator/cli.py:351-363`; timed evidence below |

Silent-broken or misleading-green paths:

1. Slack absent is visible in `message_ko` but `ok=True` and does not block init
   (`support/operator/onboard.py:1086-1096`).
2. MCP register can create Codex config even when no Codex readiness is proven;
   `_codex_mcp_config_merge` is called unconditionally after Claude branch
   (`support/operator/onboard.py:832-841`).
3. Skills placement proves file projection into `~/.claude/skills`, not app reload
   or that the user session will auto-trigger the skill (`support/operator/onboard.py:874-920`).
4. Recording setup writes hooks but Codex auto-recording remains off until trust
   acceptance; the string says this explicitly (`support/operator/onboard.py:463-467`).
5. `brick build --real-provider` defaults to `adapter:codex-local`, which is
   wrong for a Claude-only customer unless they pass `--adapter` explicitly
   (`support/operator/cli.py:35-40`, `support/operator/cli.py:82-89`,
   `support/operator/cli.py:519-524`).
6. `brick build` returns 0 for non-complete frontier if the driver returns a
   packet instead of raising (`support/operator/cli.py:241-247`).

### Doctor, Gemini, Verify

Doctor:

- Host map is only codex/claude/local (`support/operator/onboard.py:131-141`).
- `run_doctor()` iterates `SUPPORTED_HOSTS` plus gh and always returns diagnosis
  rows; CLI doctor exits 0 (`support/operator/onboard.py:1297-1329`,
  `support/operator/cli.py:223-229`).
- Timed doctor command returned rows `gh`, `codex`, `claude`, `local` in 0.59s.
- There is no Gemini row. Therefore `doctor all_ok=true` does not mean Gemini
  readiness.

Gemini checker evidence:

- `agent_axis_behavioral.yaml` includes `gemini_api_adapter` as in-process,
  no-key/mocked HTTP shape check (`support/checkers/profiles/agent_axis_behavioral.yaml:12-20`).
- The kernel check admits `adapter:gemini-api`, asserts READ+REVIEW, not write-capable,
  not local CLI, no-key clean error, no subprocess, mocked request, and clean
  ValueErrors (`support/checkers/lib/kernel_checks.py:2966-3072`).
- The profile `not_proven` includes provider login/session quality and production
  runtime (`support/checkers/profiles/agent_axis_behavioral.yaml:483-500`).

Verify timing:

- `building_operator_driver0.yaml` includes `building_operator_driver0` and
  `onboard_smoke` kernel checks (`support/checkers/profiles/building_operator_driver0.yaml:1-7`).
- It includes `onboard_seam_case` with provider-dependent acceptable frontiers
  (`support/checkers/profiles/building_operator_driver0.yaml:85-97`).
- `check_profile.run_profile()` runs all registered `RULE_RUNNERS` for a profile,
  not only explicitly populated top-level blocks (`support/checkers/check_profile.py:1161-1175`).
- Main timed run with PYTHONPATH was manually interrupted after 217.12s; stack
  showed `onboard_seam_case -> run_onboard -> run_building_intake -> run_building_plan
  -> _run_dynamic_graph_walker -> process_one_node -> connect_agent_brain ->
  adapter_local_cli -> subprocess communicate`.
- F3 independently observed interrupt at 190.64s/190.92s on the same path.

Checker/profile pass remains support evidence only, not source truth, success,
quality, Movement, provider proof, or complete coverage proof (`AGENTS.md:629-631`).

### MCP / Skills / Hooks / COO Delivery

MCP initialize:

- `_initialize_result()` returns only a short instruction:
  "Brick Protocol MCP projection is read-only support evidence. Agent meaning
  remains in agent/. Link owns Movement." (`support/connection/mcp_projection.py:554-563`).
- `handle_mcp_message()` separately handles `resources/list`, `resources/read`,
  `tools/list`, and `tools/call` (`support/connection/mcp_projection.py:566-605`).
- Direct JSON-RPC probe confirmed initialize does not include COO chain content.

COO operating-chain delivery:

- Resource URI is `brick-protocol://coo/operating-chain/context`
  (`support/connection/mcp_projection.py:50-61`, `support/connection/mcp_projection.py:98-104`).
- Tool is `brick_protocol_render_coo_operating_chain_context`
  (`support/connection/mcp_projection.py:262-327`).
- The context source is `brick/ + agent/ + support/`, with `coo_projection_skill`,
  `coo_agent_object_ref`, `task_intake_skill_ref`, chain preset candidates, startup
  paths, and operating-chain order (`support/connection/mcp_projection.py:330-430`).

Skills/projection layout:

- Agent resource refs map `skill:<x>` to `agent/skills/<x>/SKILL.md`
  (`support/connection/agent_resources.py:537-546`).
- Runtime agent instruction packet uses a front-matter/path manifest, not eager
  full SKILL bodies (`support/connection/agent_resources.py:564-621`,
  `support/connection/agent_resources.py:972-1015`).
- MCP packet/projection seed still uses full resources outside that runtime
  manifest path (`support/connection/agent_resources.py:988-994`).
- Codex skill projection target is `~/.codex/skills/brick-protocol-<role>/SKILL.md`;
  Claude target is `~/.claude/agents/brick-protocol-<role>.md`
  (`support/connection/coo_sync.py:155-200`,
  `support/connection/coo_sync.py:365-391`).
- `observe_agent_projection_freshness()` is read-only and not app reload proof
  (`support/connection/coo_sync.py:311-362`).

Hooks and personal environment:

- Recording setup copies tracked templates into repo-local `.claude/hooks` and
  `.codex/hooks`, and merges repo-local settings/hook JSON
  (`support/operator/onboard.py:440-478`, `support/operator/onboard.py:682-737`).
- Hook commands embed absolute `BRICK_REPO_ROOT=<repo>` (`support/operator/onboard.py:470-477`).
- Slack token/channel live in `~/.brick/report.env`; the provision step checks
  presence/perms and says it never echoes secret values (`support/operator/onboard.py:1029-1119`).

### Fix Would Touch

Minimal customer-ready onboarding repair should touch:

- `support/operator/cli.py`: render advisory steps as `advisory/missing/not_proven`
  when `ok` is absent; consider making `brick build` exit nonzero or clearly
  label non-complete frontier.
- `support/operator/onboard.py`: separate "projection file written" from "tool
  actually usable"; expose Codex readiness as absent on Claude-only machine;
  make Slack skipped visibly advisory, not green.
- `support/connection/mcp_projection.py`: either include a short COO bootstrap
  pointer in initialize instructions or add an explicit first-session tool prompt
  path. Do not inline full operating-chain unless token budget and authority
  boundaries are explicitly admitted.
- `support/checkers/profiles/building_operator_driver0.yaml` / checker runner:
  isolate slow provider-dependent `onboard_seam_case` from normal verify or mock
  it tighter. Current profile can exceed 3 minutes.
- `support/operator/onboard.py` doctor host map: add Gemini readiness if Gemini
  is now customer-facing, or state explicitly that doctor does not cover it.

Risk:

- Making advisory steps hard gates could block valid local-only installs.
- Auto-delivering too much COO context through MCP initialize can turn support
  projection into perceived authority.
- Verify speed repairs must preserve no-provider/no-auth friendly behavior.

Required discipline: feature-design with honest degradation semantics; checker-first
for renderer/exit behavior; no claim that MCP/checker/projection green is source
truth, success, quality, or Movement authority.

## Area 3 - God-Module Decomposition

### Census

Measured live size:

| File | LOC | Bytes | Top-level def/class | All def/class | Unique imports |
| --- | ---: | ---: | ---: | ---: | ---: |
| `support/checkers/lib/kernel_checks.py` | 9808 | 434307 | 164 | 224 | 68 |
| `support/checkers/lib/case_runners.py` | 10219 | 474450 | 163 | 190 | 97 |
| `support/operator/walker_kernel.py` | 3803 | 173030 | 55 | 70 | 29 |

Largest top-level functions/classes measured by AST:

- `kernel_checks.py`: `_assert_reporter_brick_grain_threading` 663 lines
  (`support/checkers/lib/kernel_checks.py:4176`), `_artifact_grounding_probe`
  464 lines (`support/checkers/lib/kernel_checks.py:1514`),
  `run_codex_connect_stall_classification` 358 lines
  (`support/checkers/lib/kernel_checks.py:2606`),
  `run_adapter_error_path_hardening` 354 lines
  (`support/checkers/lib/kernel_checks.py:5286`).
- `case_runners.py`: `run_native_dispatch_close_case` 611 lines
  (`support/checkers/lib/case_runners.py:4286`),
  `run_workflow_import_case` 572 lines (`support/checkers/lib/case_runners.py:5086`),
  `run_building_intake_seam_case` 543 lines
  (`support/checkers/lib/case_runners.py:1528`),
  `run_intake_evidence_projection_case` 420 lines
  (`support/checkers/lib/case_runners.py:9475`).
- `walker_kernel.py`: `_run_dynamic_graph_walker` 1447 lines
  (`support/operator/walker_kernel.py:2357`), `process_one_node` 418 lines
  (`support/operator/walker_kernel.py:1937`),
  `_source_fact_body_carry_for_step` 145 lines
  (`support/operator/walker_kernel.py:333`).

Registry:

- `case_runners.py` is registered as checker-lib with `decomposition_target: ""`
  and pinned by route materialization / compose cases
  (`support/checkers/module_registry.yaml:537-545`).
- `kernel_checks.py` is registered as checker-lib with `decomposition_target: ""`
  and many profile pins (`support/checkers/module_registry.yaml:547-555`).
- `walker_kernel.py` is registered as operator with `decomposition_target: ""`
  and pinned by `bounded_agent_proposed_routing_loop`
  (`support/checkers/module_registry.yaml:1384-1392`).
- Registry decomposition ceilings target only `check_profile.py` and
  `report_sinks.py`, not these three files
  (`support/checkers/module_registry.yaml:1818-1831`).

Thus "large and coupled" is confirmed, but "registry directly ceilings these
three god modules" is false on current HEAD.

### Natural Split Seams

`case_runners.py`:

- Natural seams are profile rule families: materialize, compose, intake,
  native dispatch, adapter capability, source-fact carry, wiki carry,
  step-output drain, link route.
- `check_profile.py` imports runner names directly from `case_runners`
  (`support/checkers/check_profile.py:86-109`) and binds them into `RULE_RUNNERS`
  (`support/checkers/check_profile.py:231-252`), so a split must preserve import
  names or introduce a facade.
- Profiles directly pin rule keys such as `compose_building_case`,
  `compose_building_rejects`, `source_fact_body_carry_case`, and
  `step_output_drain_case` (`support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:188-193`,
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1578-1790`).

`kernel_checks.py`:

- Natural seams: static AST/text oracles, in-process adapter/provider probes,
  reporter/dashboard probes, external smoke/projection probes, session-id
  redaction families.
- Coupling risks include `case_runners` helper reuse
  (`support/checkers/lib/kernel_checks.py:3978`,
  `support/checkers/lib/kernel_checks.py:4853`), `walker_kernel` monkeypatching
  (`support/checkers/lib/kernel_checks.py:5601`), and external subprocess smoke
  (`support/checkers/lib/kernel_checks.py:8762`).

`walker_kernel.py`:

- Helper extraction seams exist: `_FrontierDriver` (`support/operator/walker_kernel.py:148`),
  source-fact/wiki carry (`support/operator/walker_kernel.py:333`),
  runtime handoff containment (`support/operator/walker_kernel.py:962`),
  resume seed helpers (`support/operator/walker_kernel.py:1187`),
  report event helpers (`support/operator/walker_kernel.py:1572`).
- Wholesale split is high risk because `process_one_node` and
  `_run_dynamic_graph_walker` share executor/writer/frontier/report/resume state
  across wide function bodies (`support/operator/walker_kernel.py:1937`,
  `support/operator/walker_kernel.py:2357`).

### Guard-First Requirements

Before any behavior-identical split:

1. Dispatch freeze: guard the exact `KERNEL_DISPATCH` and `RULE_RUNNERS` key set,
   existing import names, and profile closure. Current `assert_registry_closure`
   catches unknown keys but not byte-identical dispatch behavior
   (`support/checkers/check_profile.py:1050-1077`).
2. Case-runner byte freeze: run selected profiles for materialize, compose,
   source-fact carry, wiki truncation, step-output drain, and native dispatch
   into temp roots; compare normalized persisted output before/after.
3. Walker byte freeze: preserve existing bounded-agent proofs and add a fresh
   forward no-resume graph/linear normalized evidence equality probe. E2 cited
   existing parity anchors in `check_bounded_agent_proposed_routing_loop0.py`.
4. Runtime handoff freeze: mail address containment, lexical-prefix boundary,
   and fan-in step-output body carrying must stay red/green pinned.
5. Kernel-check smoke freeze: clean-env CLI/MCP/connect subprocess behavior,
   non-byte-identical host projections, and session-id redaction families must
   be frozen before moving helper bodies.

Required discipline: GUARD-FIRST, then split, then byte-identical proof. A
checker green after the fact is not enough; the guard must fail red on a
behavior-changing move.

### Checker-Diet / Assertion Conservation

Files coexist on current HEAD:

| Profile | LOC | Bytes | Meaning |
| --- | ---: | ---: | --- |
| `building_skill_preset_agent_tool_hardening.yaml` | 4170 | 194810 | Original 195KB profile |
| `building_skill_preset_agent_resource_boundary.yaml` | 175 | 6351 | Condensed agent/resource slice |
| `building_skill_preset_builder_composition.yaml` | 274 | 10404 | Condensed builder/composition slice |
| `building_skill_preset_intake_adapter_gate.yaml` | 131 | 5387 | Condensed intake/adapter/gate slice |

The split profiles explicitly say "staging copies only; original profile remains
intact" (`support/checkers/profiles/building_skill_preset_agent_resource_boundary.yaml:165-175`,
`support/checkers/profiles/building_skill_preset_builder_composition.yaml:265-274`,
`support/checkers/profiles/building_skill_preset_intake_adapter_gate.yaml:121-131`).

Measured label conservation:

- Original labels: 97.
- Split union labels: 12 matching original labels.
- Original-only labels: 85.
- Split-only labels: 0.

Major original-only or partially copied blocks:

- `preset_building_completion_case` original-only starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1360`.
- `intake_project_vessel_case` original-only starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1531`.
- `source_fact_body_carry_case` original-only starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1578`.
- `wiki_carry_truncation_survival_case` original-only starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1743`.
- `step_output_drain_case` and rejects original-only start at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1746`
  and `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1790`.
- `gate_sequence_policy_case` original-only starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1804`.
- `declared_step_template_plan_case` and rejects original-only/mostly omitted
  start at `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:3659`
  and `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:3866`.
- `agent_candidate_packet_case` and `preset_ranking_packet_case` original-only
  start at `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:4102`
  and `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:4146`.

Partial-copy examples:

- `materialize_building_intent_case`: original starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:256`;
  split only copies two cases starting at
  `support/checkers/profiles/building_skill_preset_builder_composition.yaml:47`.
- `materialize_building_intent_rejects`: original starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1133`;
  split copies three cases at
  `support/checkers/profiles/building_skill_preset_builder_composition.yaml:134`.
- `compose_building_case`: original starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:1834`;
  split copies one case at
  `support/checkers/profiles/building_skill_preset_builder_composition.yaml:174`.
- `compose_building_rejects`: original starts at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:2120`;
  split has only two rejects at
  `support/checkers/profiles/building_skill_preset_builder_composition.yaml:215`.
  Original-only rejects include missing movement, unknown step template,
  malformed shape, gate ordering/sequence failures, unknown endpoint, self-loop,
  duplicate id, missing fields/review gate, empty composition, group coherence,
  graph preset group omissions, fan-out completion edge, hard-graph transition
  policy/source-fact/budget cases, and unknown concern kind
  (`support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:2121-3425`).
- `agent_resource_boundary`: original has eight roles starting at
  `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml:3426`;
  split has only `coo/dev/qa` starting at
  `support/checkers/profiles/building_skill_preset_agent_resource_boundary.yaml:74`.

Deletion requirement:

Before the 195KB original can be deleted, create an assertion-conservation
inventory mapping every original top-level block, label, role row, retired-ref
reject, preferred-adapter reject, path pin, and text pin to:

```text
original file:line
split owner profile
mutation RED fixture
expected RED message
checker command
GREEN restore evidence
```

Without that inventory, original deletion is HOLD.

## Attribution

Brick:

- Area 1 custom graph and preset issues are primarily Brick work/plan/graph
  contract issues when the caller declares graph/preset/task rows.
- Area 3 profile assertion conservation is Brick/checker support evidence about
  work composition templates, not a Movement authority issue.

Agent:

- Area 1 adapter mismatch and provider timeout are Agent adapter/per-step
  performer selection/readiness issues.
- Area 2 Claude-only/Codex config projection and Gemini readiness are Agent
  provider/adapter readiness issues.

Link:

- Area 1 must not let Support select Movement or route while adding launch UX.
- Area 3 walker split must preserve Link gate/frontier/handoff behavior
  byte-identically.

Support:

- Area 1 CLI/driver/onboard launcher and worktree bracket are Support surfaces.
- Area 2 installer/onboard/MCP/projection/doctor/checker are Support surfaces.
- Area 3 checker registry/profile splitting and module ceilings are Support
  governance surfaces.

## Narrowly Proven

- The investigation ran on live worktree `/Users/smith/.brick/worktrees/struct-surgery-0623`,
  HEAD `3d22955`.
- `brick build` preset path uses `run_customer_building_in_sandbox`.
- `run_customer_building_in_sandbox` brackets dispatch in worktree or temp dir
  and disposes worktree.
- `onboard.launch_assembled_building` exists and absorbs the known custom-graph
  direct-run footguns at Python API level.
- `run_composed_graph_intake` is sealed internal/checker-only and not in
  `driver.__all__`.
- Install script is loud-fail for core prerequisites.
- MCP initialize does not auto-deliver COO operating-chain.
- Doctor omits Gemini readiness.
- `building_operator_driver0` can be slow; two independent runs exceeded 190s.
- God-module sizes and LOC were measured on live line.
- Original 195KB checker profile and 3 split profiles coexist; split profiles
  are condensed and do not conserve the original assertion inventory.

## Not Proven

- Provider reliability, login/session quality, app reload behavior, production
  runtime behavior, real Slack delivery, Gemini live API readiness, semantic
  correctness of Agent returns, and future Building quality.
- That `brick build --adapter adapter:local` keeps all effective steps on
  `adapter:local`.
- That `brick init` leaves MCP/skills/hooks/Slack actually usable in the current
  user app session.
- That checker/profile green is source truth, success, quality, Movement
  authority, provider proof, or complete coverage.
- That any god-module split would be byte-identical without new guard-first
  freeze probes.
- That the 195KB hardening profile can be deleted safely.

## Subagent Evidence Disposition

All subagents were treated as support evidence and reconciled against live code
or main command probes:

- A1 confirmed CLI/preset path and driver seal; main reconciliation corrected
  custom graph conclusion with live `launch_assembled_building`.
- A2 ran empirical temp-output launch probes; main probe independently reproduced
  `brick build` exit 0 with `agent_incomplete`.
- F1 mapped install/onboard path; main code review confirmed advisory/fatal split
  and renderer risk.
- F2 mapped MCP/skills/hooks/COO; main JSON-RPC probe confirmed initialize/tools/resources.
- F3 timed doctor/verify; main timed profile run independently confirmed slow
  `onboard_seam_case` path to 217.12s before interrupt.
- E1 measured god-module census; main AST/LOC script confirmed counts and registry rows.
- E2 mapped split feasibility; main registry/check_profile lines confirmed direct
  dispatch coupling and guard-first requirement.
- E3 measured checker-diet conservation; main label comparison confirmed
  97 original labels, 12 split-union matches, 85 original-only labels.

## Commands Run

Representative commands:

```text
pwd
git rev-parse --short HEAD
git rev-parse HEAD
git status --short
git ls-files support/operator/cli.py
grep -rl run_customer_building_in_sandbox support/operator/
wc -l <bounded files>
du -h <god modules and profiles>
find support/checkers/profiles -maxdepth 1 -type f -name '*.yaml'
rg -n <function/check/profile patterns> <bounded files>
nl -ba <file> | sed -n '<range>p'
python3 AST census script over kernel_checks.py / case_runners.py / walker_kernel.py
python3 profile label comparison script over original + split hardening profiles
/usr/bin/time -p env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 -m brick_protocol.support.operator.cli doctor --repo ... --json
/usr/bin/time -p env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 -m brick_protocol.support.operator.cli build --repo ... --task ... --output-root /tmp/... --json
/usr/bin/time -p env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --repo ... --profile support/checkers/profiles/building_operator_driver0.yaml
PYTHONPATH=support/import_identity:. python3 JSON-RPC MCP initialize/tools/list/resources/list/tools/call probe
```

No formatting, source code generation, source edits, commits, or destructive git
commands were performed. Temporary output roots under `/tmp` and worktree
sandbox paths under `~/.brick/worktrees` were used for probes.

## Next Movement Recommendation

Area 1: HOLD customer-ready launch claim. FORWARD only on a narrow launcher
design/repair that makes frontier/exit semantics honest, exposes custom graph
launch without bypassing the driver public-intake seal, and pins sandbox usage.

Area 2: HOLD customer-ready onboarding claim. FORWARD on advisory rendering,
COO first-session delivery, Gemini readiness wording/checking, and verify
speed isolation.

Area 3: HOLD code split and original-profile deletion. FORWARD on guard-first
freeze probe design and assertion-conservation inventory only.

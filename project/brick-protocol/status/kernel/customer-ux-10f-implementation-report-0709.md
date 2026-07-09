# ⑩f Customer UX Implementation Report — 0709

Status: support evidence only. This report records implementation observations
from the `customer-ux-10f-cli-tie-0709` worktree Building. It is not source
truth, not success judgment, not quality judgment, and not Movement authority.

## Changed surfaces

```text
brick_protocol/support/operator/cli.py
brick_protocol/support/operator/progress_projection.py
brick_protocol/support/checkers/check_profile.py
brick_protocol/support/checkers/lib/kernel_checks.py
brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py
brick_protocol/support/checkers/profiles/core.yaml
brick_protocol/support/checkers/profiles/customer_project_progress_cli.yaml
project/brick-protocol/status/kernel/customer-ux-10f-implementation-report-0709.md
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

No `brick_protocol/agent/**`, `brick_protocol/link/**`,
`project/brick-protocol/project.json`, `project/brick-protocol/README.md`,
`project/brick-protocol/status/inbox/**`, credential, secret, provider session,
scheduler, queue, retry-runtime, Agent, or Link surface was intentionally edited.

## Implementation observation

`brick_protocol/support/operator/cli.py` now exposes:

```text
brick project new [--id <slug>] [--label <name>] [--non-interactive]
brick project list
brick project show [<id>]
brick progress [<id>] [--write]
```

The implementation is a CLI wrapper over existing support seams:

```text
project_creation.create_project
progress_projection.render_project_progress
progress_projection.generate_project_progress
project_declaration.load_project_declaration
```

P7 repair observation after re-instruction:

```text
brick_protocol/support/operator/cli.py now redacts the generated PROGRESS.md body after `generate_project_progress(...)` returns, through `_redact_written_progress(...)`, so secret/session/provider-credential-shaped strings are removed from the file body before the CLI returns.
brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py now opens the generated PROGRESS.md after `brick progress --write` and asserts the raw P7 probe needles are absent.
```

Observed code references:

```text
brick_protocol/support/operator/cli.py:61 imports generate_project_progress/render_project_progress.
brick_protocol/support/operator/cli.py:64 imports create_project.
brick_protocol/support/operator/cli.py:946 refuses non-interactive project creation without explicit charter fields.
brick_protocol/support/operator/cli.py:959 requires typed project-id confirmation before interactive creation.
brick_protocol/support/operator/cli.py:965 defines _cmd_project_new.
brick_protocol/support/operator/cli.py:997 defines _cmd_project_list.
brick_protocol/support/operator/cli.py:1020 defines _cmd_project_show.
brick_protocol/support/operator/cli.py:1055 defines _cmd_progress.
brick_protocol/support/operator/cli.py:1060 calls generate_project_progress for --write.
brick_protocol/support/operator/cli.py:1078 calls render_project_progress for default progress.
brick_protocol/support/operator/cli.py:2021 wires the project command.
brick_protocol/support/operator/cli.py:2057 wires the progress command.
```

## Checker observation

Focused checker/profile added:

```text
brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1020 defines run_customer_project_progress_cli.
brick_protocol/support/checkers/check_profile.py:846 registers customer_project_progress_cli.
brick_protocol/support/checkers/profiles/customer_project_progress_cli.yaml:5 runs the customer_project_progress_cli kernel check.
brick_protocol/support/checkers/profiles/core.yaml:106 admits the new profile path in core's profile inventory.
```

The focused checker uses a temporary repo and observes:

```text
P1 parser exposes project/progress commands.
P2 CLI imports/calls existing create_project and progress projection seams.
P3 non-TTY project new without explicit charter fields refuses and leaves no vessel.
P4 full project new requires explicit charter data; interactive path has typed confirmation before create_project.
P5 project list/show preserve a file snapshot of the vessel.
P6 progress default preserves a file snapshot; progress --write calls generate_project_progress and writes PROGRESS.md.
P7 secret-shaped declaration text is redacted from project/progress customer packets.
P7 generated PROGRESS.md omits raw secret-shaped declaration text after progress --write.
P10 no success/quality/Movement authority was observed in the new customer CLI behavior.
```

## P1-P10 evidence map

| Proof | Evidence |
|---|---|
| P1 parser exposes `project` and `progress` | `run_customer_project_progress_cli` parser assertions at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1035` and command wiring at `brick_protocol/support/operator/cli.py:2021`, `brick_protocol/support/operator/cli.py:2057`. |
| P2 wrapper uses existing backends | Imports at `brick_protocol/support/operator/cli.py:61`, `brick_protocol/support/operator/cli.py:64`; checker import needles at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1055`; calls at `brick_protocol/support/operator/cli.py:969`, `brick_protocol/support/operator/cli.py:1060`, `brick_protocol/support/operator/cli.py:1078`. |
| P3 non-TTY no silent project creation | CLI refusal at `brick_protocol/support/operator/cli.py:946`; temp-repo no-files assertion at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1097`. |
| P4 explicit confirmation before stamping | Interactive confirmation at `brick_protocol/support/operator/cli.py:959`; non-interactive requires all charter slots at `brick_protocol/support/operator/cli.py:934`. |
| P5 list/show read-only | Snapshot assertions at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1150` and `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1171`. |
| P6 progress default read-only / --write uses generator | Render-only call assertion at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1207`; default snapshot assertion at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1212`; generator call assertion at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1233`; path assertion at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1239`. |
| P7 secret/session masking | Packet redaction helper at `brick_protocol/support/operator/cli.py:827`; generated PROGRESS.md file-body redaction helper at `brick_protocol/support/operator/cli.py:1094`; checker leak assertions at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1137`, `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1153`, `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1174`, `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1215`, `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1249`, and generated file body assertion at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1250`. |
| P8 host profiles green | `check_profile.py --profile building_skill_preset_intake_adapter_gate` rc=0; `check_profile.py --profile read_side_projection_boundary` rc=0. |
| P9 import identity still works | `check_profile.py --profile core` rc=0 includes `check_import_identity_modes.py` profile inventory; `check_profile.py --profile brick_cli_entrypoint` is indirectly covered by the full sweep when it completes. |
| P10 no new source truth / success / quality / Movement fields | Focused profile text_absent in `brick_protocol/support/checkers/profiles/customer_project_progress_cli.yaml`; runtime forbidden text scan at `brick_protocol/support/checkers/lib/brick_cli_entrypoint_check.py:1066`. |

## Commands run

```text
python3 brick_protocol/support/checkers/check_profile.py --profile customer_project_progress_cli
  rc=0; profile passed: customer-project-progress-cli (36 declarative rule observation(s), 10 kernel target(s) inspected)

python3 -m compileall -q brick_protocol
  rc=0

python3 brick_protocol/support/checkers/check_profile.py --profile core
  rc=0; profile passed: core (142 declarative rule observation(s), 6262 kernel target(s) inspected)

python3 brick_protocol/support/checkers/check_profile.py --profile building_skill_preset_intake_adapter_gate
  rc=0; profile passed: building-skill-preset-intake-adapter-gate (69 declarative rule observation(s), 5874 kernel target(s) inspected)

python3 brick_protocol/support/checkers/check_profile.py --profile read_side_projection_boundary
  rc=0; profile passed: read-side-projection-boundary (353 declarative rule observation(s), 6230 kernel target(s) inspected)

git diff --check
  rc=0

python3 brick_protocol/support/checkers/check_profile.py --all
  rc=0; 61/61 profile sweep exited 0; customer_project_progress_cli passed inside the sweep; proof limit remains checker/profile support evidence only.
```

## Not proven

```text
semantic correctness of future customer project charters
real provider behavior
future Building correctness
customer shell/PATH behavior beyond checker-observed CLI import/parser behavior
that checker/profile pass is source truth, success judgment, quality judgment, or Movement authority
```

## Remaining delta / repair observation

No source repair need is currently observed from the focused profile, compileall,
core, required host profiles, `git diff --check`, or the `check_profile.py --all`
rc=0 sweep. This is support evidence only and does not make source truth,
success judgment, quality judgment, or Movement authority.

# Customer-Ready P5 CLI / Onboard First-Run Repair 0627

Status: support evidence only.

This record does not create source truth, success judgment, quality judgment, or
Movement authority.

## Scope

Goal phase: P5 -- B2 onboarding and customer first run.

Focused repair:

- `brick init` default host is Codex for the weekend Codex/Gemini path.
- `brick build --task ... --real-provider` defaults to the task-first
  `building-chain-preset:fast-fix` route instead of the local onboarding graph.
- That real-provider task intent carries the Brick-owned derived worktree
  `write_scope` (`allowed_paths: ["."]`, `forbidden_paths: [".git/**"]`) so
  write-needed work Bricks can materialize honestly.
- `adapter:gemini-api` remains non-write; CLI task intent does not attach
  `write_scope` for that read/review adapter.
- Onboarding/doctor host map now includes `gemini` / `adapter:gemini-local`.

## Brick / Agent / Link Attribution

Evidence first:

- P1 already admitted `adapter:gemini-local` as observed-write capable only at
  the effective-write intersection.
- P3 Building evidence still HOLDS at `adapter:gemini-local` provider/auth
  failure (`API_KEY_INVALID`), which this P5 repair does not close.
- P5 first-run inspection found a separate customer CLI gap: the task path could
  be real-provider/write-needed while no Brick `write_scope` was declared.

Brick candidate:

- The work route selection and `write_scope` declaration are Brick work
  composition facts. A write-needed `work` Brick needs a declared write envelope.

Agent candidate:

- The selected adapter remains an Agent brain/capability connection. Codex-local
  is the default real-provider task adapter; Gemini-local is exposed in the
  onboard host map; Gemini-api stays read/review only.

Link candidate:

- No Link Movement, target, route policy, or gate semantics changed.

Support surface:

- `support/operator/cli.py`
- `support/operator/onboard.py`
- checker support in `support/checkers/lib/kernel_checks.py`
- profile pins in `support/checkers/profiles/brick_cli_entrypoint.yaml` and
  `support/checkers/profiles/building_operator_driver0.yaml`

Rejected one-axis shortcut:

- This was not treated as "adapter authority" or "Gemini permission" alone. P1
  handled adapter capability. P5 needed a Brick first-run declaration repair.

Chosen repair surface:

- Support CLI/onboarding projection only, with checker coverage. No new runtime,
  scheduler, queue, retry owner, Movement literal, source truth, or provider SDK
  adapter was added.

## Verification

Commands run:

```text
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile brick_cli_entrypoint
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile building_operator_driver0
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile bounded_agent_proposed_routing_loop
python3 -m compileall -q support/operator support/checkers
git diff --check
```

Observed focused evidence:

- `brick_cli_entrypoint` passed and now checks that:
  - local task defaults stay read-only (`adapter:local`,
    `building-chain-preset:onboarding-example-graph`, no `write_scope`);
  - `--real-provider` task defaults to `adapter:codex-local` +
    `building-chain-preset:fast-fix`;
  - the real-provider task materializes a write-needed work Brick row carrying
    the derived worktree `write_scope` and `requires_brick_write_scope: true`;
  - `adapter:gemini-api` task intent remains non-write.
- `building_operator_driver0` passed and now checks that Gemini appears in
  onboard doctor/readiness host evidence.
- `bounded_agent_proposed_routing_loop` passed, preserving the P4 resume/fan-out
  repair while this P5 patch is present.
- `compileall` passed for `support/operator` and `support/checkers`.
- `git diff --check` passed.

## Narrowly Proven

- The weekend default `brick init` host is no longer Claude.
- The first real-provider task CLI path now carries a materialized Brick
  `write_scope` for write-needed work.
- Gemini-local appears in the onboarding host/readiness surface.
- Gemini-api remains non-write on the customer CLI task intent.
- This focused patch does not regress the P4 resume/fan-out focused profile.

## Not Proven

- P3 C6 customer-ready launch remains HOLD on live Gemini-local provider/auth.
- Gemini-local live provider success is not proven by this record.
- Fresh-machine install/onboard is not fully proven.
- Full `check_profile.py --all` remains not claimed here.
- Slack/customer notification reliability is not proven by this record.

## Movement

P5 focused repair: FORWARD as support evidence.

Global customer-ready goal: HOLD until P3 Gemini-local provider/auth is fixed or
the operator declares a different non-Claude route.

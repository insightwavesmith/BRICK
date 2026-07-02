# Claude QA Execution Fresh Smoke Support Record (0625)

Status: SUPPORT RECORD. This document records the fresh-smoke intent and
expected evidence for `claude-qa-execution-fresh-smoke-0625`. It is not source
truth, not a success judgment, not a quality judgment, and not Movement
authority.

## Scope

This Building smokes the post-`ec43f0b` Claude QA execution-permission repair in
a fresh official Building process. The specific prior failure mode was a Claude
QA lane reporting harmless shell/checker execution as approval-gated even when
the Brick had effective write scope and Bash was present in the Claude `--tools`
allowlist.

The expected adapter boundary is narrow: for write-effective or read-tier
requests that declare allowed Claude tools, `adapter:claude-local` should pass
the same tool set through `--allowedTools` as it passes through `--tools`, so
harmless Bash/checker commands are not provider-approval gated only because the
permission flag was omitted.

## Declared Smoke Commands

The QA step is expected to independently drive these commands from its
sandbox/cwd if permitted:

```text
python3 -c 'print(42)'
git diff --check
uv run python3 -m py_compile support/connection/adapter_local_cli.py
```

The `uv run` compile command is optional in the task statement. If `uv` is not
available or provider execution is still approval-gated, that belongs in QA
evidence as a bounded adapter/runtime observation, not as a success/failure
verdict.

## Observed Setup Evidence

- Fresh Building evidence was started under
  `project/brick-protocol/buildings/claude-qa-execution-fresh-smoke-0625/`.
- Inbox events were recorded under `project/brick-protocol/status/inbox/` for
  Building start and Brick receipt for this fresh smoke.
- `support/connection/adapter_local_cli.py` currently appends
  `--allowedTools <allowed_tools>` after `--tools <tools>` when the Claude local
  invocation has a non-empty `allowed_tools` value.
- `support/checkers/lib/kernel_checks.py` contains a verifier branch that
  captures Claude effective-write argv and rejects omission of `--tools`,
  omission of `--allowedTools`, drift between the two arguments, or absence of
  `Bash` in the allowed-tools set.

## Checker-First Observation

The relevant broad profile was attempted before this record was authored:

```text
python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening
```

It did not return green in this checkout. The observed rejection was:

```text
profile runner rejected evidence: preset_building_completion_case rejected all-current-presets-slack-alert: expected 27 preset(s), observed 28
```

That rejection is recorded as blocked verifier evidence for this work step. It
does not by itself prove the Claude execution-permission fix failed; the
rejected rule is a preset-count expectation, not the specific
`--allowedTools`/`--tools` argv parity check.

## Local Command Observation

From this Codex work step's sandbox/cwd, the harmless command shapes used for
the smoke were locally executable:

```text
python3 -c 'print(42)' -> exit 0, printed 42
git diff --check -> exit 0
uv run python3 -m py_compile support/connection/adapter_local_cli.py -> exit 0
```

This is local Codex support evidence only. The required smoke remains the
independent QA-lane observation under `adapter:claude-local`.

## Expected QA Evidence

The QA return should record whether the three harmless command attempts were
executed, approval-gated, missing due to local tooling, or otherwise blocked.
If execution remains approval-gated, the return should carry non-binding
`transition_concern_evidence` against the adapter invocation boundary.

The QA return should preserve proof limits: this smoke is support evidence only.
It does not prove provider quality, provider reliability, source truth, success,
quality, future Building correctness, or Movement authority.

## Commands Recorded For This Work Step

```text
sed -n '1,220p' agent/skills/scoped-implementation/SKILL.md
sed -n '1,220p' agent/skills/protocol-boundary-watch/SKILL.md
sed -n '1,160p' project/brick-protocol/PROGRESS.md
ls support/checkers/profiles | sed -n '1,80p'
ls project/brick-protocol/status/kernel | sed -n '1,120p'
rg -n "fresh smoke|Claude QA|approval-gated|allowedTools|adapter:claude-local" project/brick-protocol/status support agent brick link -S
git status --short
sed -n '1,220p' project/brick-protocol/status/kernel/gap2-customer-entry-readiness-0625.md
python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening
rg --files project/brick-protocol/buildings/claude-qa-execution-fresh-smoke-0625 | sed -n '1,160p'
sed -n '680,720p' support/connection/adapter_local_cli.py
sed -n '1160,1195p' support/checkers/lib/kernel_checks.py
python3 -c 'print(42)'
git diff --check
uv run python3 -m py_compile support/connection/adapter_local_cli.py
python3 support/checkers/check_profile.py --help | sed -n '1,160p'
```

## Proof Limits

- This record is support evidence only.
- This record does not mutate `AGENTS.md`, Brick / Agent / Link contracts,
  runtime behavior, gate behavior, Movement literals, or route targets.
- This record does not prove Claude provider behavior, provider quality,
  execution reliability, source truth, success, quality, or Movement authority.

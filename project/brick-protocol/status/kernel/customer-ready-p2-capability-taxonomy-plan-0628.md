# Customer-Ready P2 Capability Taxonomy Plan - 0628

Status: support evidence only. 0629 operator recheck: P2 taxonomy is closed for
the v4 goal with proof limits below.

This record is not source truth, success judgment, quality judgment, Movement
authority, route authority, or provider proof. It records the operator plan for
P2 after read-only subagent measurement, two-agent attack review, and Codex
operator reconciliation. Subagent output is support evidence only.

## Phase

P2 - Agent casting, preset recast, and capability taxonomy.

## Operator Read

P2 is not another adapter permission patch. The active repair is to stop using
the old binary "read/write" frame where it confuses QA, Inspector, and
verification work.

The admitted vocabulary for planning is:

```text
read
probe_write / verification_write
source_write / artifact_write
```

These classes are recommendations / declared needs, not a new authority system.
They must not become Movement, route selection, quality judgment, success
judgment, provider identity, or source truth.

## Current Measurement

Observed live surfaces already contain partial implementation:

```text
agent/tool_policies/read-write-scoped.yaml
agent/prompts/qa.md
agent/prompts/inspector.md
brick/templates/bricks/code-attack-qa/brick.md
brick/templates/bricks/axis-attack-qa/brick.md
brick/templates/bricks/evidence-integrity/brick.md
support/connection/adapter_grant_policy.py
support/connection/agent_adapter.py
support/connection/adapter_local_cli.py
support/checkers/profiles/agent_axis_behavioral.yaml
support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml
```

The current checkout states that QA/Inspector may use disposable verification
writes while still forbidding real source mutation. The adapter side has grant
translation and Gemini-local mock coverage.

Historical measured gaps before 0629 recheck:

```text
- Brick templates do not consistently expose a first-class capability class.
- active Brick row/spec admission currently centers write_scope and
  requires_brick_write_scope, not capability_class.
- work implies source/artifact mutation but does not name source_write/artifact_write.
- Agent objects infer max capability from policy/lane/hook instead of exposing
  a clear max class view.
- native grant/admitted adapter capability still collapses machine behavior to
  read/write/web/review classes; probe/source distinction is semantic/prompt and
  post-hoc evidence unless separately enforced.
- reviewer source/probe separation is partly prompt/admin-policy/post-hoc
  observation, not fully filesystem-enforced.
- candidate/materialized plan rendering lacks a digest sentinel proving Agent
  YAML resources are not mutated.
- live Gemini/provider calls must remain out of ordinary checker sweeps; Gemini
  has a focused guard, but a global ordinary-profile provider-call guard is not
  yet proven.
- web/search/native tool classes need explicit placement as adapter-native
  read/research tools, not source mutation permission.
```

## 0629 Operator Recheck / Closure Evidence

Current live evidence after focused and full profile runs:

```text
Brick:
  work carries capability_class: source_write.
  code-attack-qa / axis-attack-qa / evidence-integrity carry
  capability_class: probe_write.
  generated rows expose capability_class as a non-authoritative Brick/rendering
  fact; it does not choose Movement or target.

Agent:
  agent/tool_policies/read-write-scoped.yaml declares read, probe_write,
  verification_write, source_write, artifact_write.
  reviewer lanes with hook:reviewer-no-mutation block source_write while keeping
  probe_write / verification_write for disposable checks.
  materialization includes an agent/objects/*.yaml digest sentinel.

Adapter / support:
  Codex-local and Gemini-local expose the same semantic capability vocabulary
  when write_need is true.
  Gemini-api is retired from active write/probe-write path.
  checker-profile sweep live Gemini dispatch fails closed.
  Gemini-local probe_write prompt/admin-policy allows write_file / replace /
  run_shell_command inside Brick-declared write_scope while source_write remains
  blocked by reviewer-no-mutation.

Link:
  capability_class remains non-authoritative. It does not derive Movement,
  target, gate sufficiency, reroute, success, or quality.
```

Commands run on 0629:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile agent_axis_behavioral
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening
PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q support/connection support/operator support/checkers
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

Observed result: all commands exited 0.

## Attack Review Delta

Two independent attack reviews originally agreed on the same P2 closure risk.
The 0629 recheck resolves the P2 v4 taxonomy closure items except the explicit
proof limits below:

```text
P2 direction is right.

PROVEN-AS-SUPPORT-EVIDENCE:
- generated rows carry capability_class as a non-authoritative Brick/rendering
  fact
- reviewer source_write is blocked by reviewer-no-mutation policy/prompt
- reviewer probe_write / verification_write is allowed for disposable work-area
  probes when declared
- Agent resource materialization leaves agent/objects/*.yaml byte-identical
- Gemini/Codex semantic capability vocabulary parity is checked
- ordinary profile sweep live Gemini dispatch fails closed
```

Do not claim machine-enforced source/probe separation from prompt text alone.
The closed P2 claim is semantic/prompt/evidence/checker discipline with explicit
proof limits, not an OS-level guarantee that source mutation is impossible.

## Three-Axis Attribution

Brick:

```text
owns the work need.
Brick may recommend/declaratively need read, probe_write, or source_write /
artifact_write for a node.
This is not a route selector and not a quality/success verdict.
```

Agent:

```text
owns performer capability ceiling.
Agent tool policy says what a performer may do at most.
QA/Inspector may receive probe_write for checks, fixtures, temp/cache, and
negative probes, but must not source_write.
```

Link:

```text
owns transfer, carry, gate sufficiency, Movement, and reroute.
Link must not derive Movement from the capability class.
```

Support / Adapter:

```text
translates semantic capability into provider-native sandbox/tool policy.
Gemini-local uses Gemini CLI plus GEMINI_API_KEY or GOOGLE_API_KEY.
Gemini-api is retired from active write/probe-write path.
ordinary profiles must not live-call Gemini.
```

## Implementation Plan

1. Checker-first invariant.

```text
Add or tighten focused checks proving:
- reviewer source mutation is RED
- reviewer probe_write temp/output fixture writes are allowed when declared
- generated candidate/materialized packets do not mutate agent/objects/*.yaml
- ordinary profile sweeps do not live-call Gemini or other providers
- Gemini-local and Codex-local expose the same semantic class vocabulary where
  technically supported
- materialized Brick rows expose capability_class only as non-authoritative
  declared/recommended need; it must not choose Movement or targets
```

2. Brick row projection.

```text
Add a non-authoritative capability-class declaration/recommendation to relevant
Brick templates or materialized rows.
Keep requires_brick_write_scope as the hard existing write gate.
Do not use capability_class as Movement, target selection, or success.
```

3. Agent policy projection.

```text
Expose max admissible classes from tool policies:
read
probe_write / verification_write
source_write / artifact_write

Keep reviewer-no-mutation binding on QA/Inspector lanes.
Keep COO read-only.
```

4. Adapter/native grant projection.

```text
Map each class into provider-native policy:
Codex-local: sandbox/tool mode for read, probe_write, source/artifact write.
Gemini-local: CLI admin-policy and isolated workspace for same semantic classes
where supported.
Claude-local: compatible class vocabulary when active again.
Gemini-api: no active write/probe-write lane.
```

5. Generated plan visibility.

```text
Generated active plans must show lane, adapter, Brick kind, write scope, and
capability class without collapsing QA probe_write into source_write.
```

## Exit Checks

Minimum focused checks before P2 closure:

```text
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile agent_axis_behavioral
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening
python3 -m compileall -q support/connection support/operator support/checkers
git diff --check
```

The broad profiles above are not sufficient unless they include explicit cases
for:

```text
reviewer source-mutation RED
Agent resource digest sentinel
capability_class visible but non-authoritative in generated rows
Gemini/Codex semantic class parity
ordinary-profile provider-call guard
```

Full sweep is required only after focused green:

```text
PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all
```

## Movement

Recommendation:

```text
FORWARD to P3 official Easy Building repair/proof.
P2 taxonomy closure is closed-with-proof-limits for the v4 goal.
Do not reopen P2 unless current raw/checker evidence contradicts the 0629
support evidence above.
```

## Not Proven

```text
filesystem-enforced source/probe split
live Gemini availability or credential validity
future authority leak absence
provider behavior or provider quality
fresh customer path proof
```

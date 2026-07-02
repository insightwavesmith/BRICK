# Customer-Ready P3 Timeout Diagnostic Preservation 0627

Status: support repair evidence.

Building evidence root inspected:

```text
project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-8
```

Observed frontier:

```text
frontier_kind: agent_incomplete
adapter_ref: adapter:codex-local
error_kind: local_cli_timeout
exception_type: TimeoutExpired
customer_visible_frontier_state: not_ready
```

Three-axis attribution:

```text
Brick candidate:
  The C6 work boundary was declared. The observed blocker did not prove a Brick
  work-definition failure.

Agent candidate:
  The dev Agent received work, but no closed AgentFact was produced because the
  adapter raised TimeoutExpired. This proves agent_incomplete, not Agent
  semantic failure.

Link candidate:
  Link transition was not recorded because Agent returned evidence was absent.
  Link did not choose a route or Movement from this adapter exception.

Support surface:
  run.py built timeout diagnostic fields, but adapter_error_frontier recording
  dropped extra adapter_error mapping fields before raw/step-output persistence.
```

Chosen repair surface:

```text
support recording only:
  support/recording/contracts.py
  support/recording/adapter_error_frontier.py
  support/recording/step_outputs.py
  support/checkers/lib/kernel_checks.py
```

Repair:

```text
AdapterErrorObservation now carries whitelisted timeout diagnostics:
  timeout_reap_reason
  timeout_stdout_excerpt
  timeout_stderr_excerpt

The adapter-error raw row and step-output adapter-error record preserve those
fields as support diagnostics. They are not source truth, success judgment,
quality judgment, Movement authority, target selection, or route policy.
```

Verifier:

```text
adapter_error_path_hardening now includes a synthetic direct adapter-error
frontier fixture that fails if timeout diagnostics are dropped from raw or
step-output evidence.
```

Commands:

```text
PYTHONPATH=support/import_identity:. python3 - <<'PY'
from pathlib import Path
from support.checkers.lib.kernel_checks import run_adapter_error_path_hardening
result = run_adapter_error_path_hardening(Path.cwd())
print(result)
PY

PYTHONPATH=support/import_identity:. python3 -m support.checkers.check_step_output_evidence_field_set_parity

PYTHONPATH=support/import_identity:. python3 -m support.checkers.check_building_lifecycle_path_shape --target project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-8

python3 -m py_compile support/recording/contracts.py support/recording/adapter_error_frontier.py support/recording/step_outputs.py support/checkers/lib/kernel_checks.py support/operator/run.py support/connection/adapter_subprocess.py

git diff --check -- support/recording/contracts.py support/recording/adapter_error_frontier.py support/recording/step_outputs.py support/checkers/lib/kernel_checks.py support/operator/run.py support/connection/adapter_subprocess.py
```

Verification result:

```text
adapter_error_path_hardening: green
step_output_evidence_field_set_parity: green
recast-8 lifecycle path shape: green
py_compile: green
git diff --check: green
```

Known profile caveat:

```text
check_profile.py --profile building_automation still fails on pre-existing
project/brick-protocol/buildings/gemini-adapter-fileread-0626 building-map
evidence refs. That failure predates this repair and is not proof against the
timeout diagnostic preservation patch.
```

Movement:

```text
P3 remains HOLD.

This repair makes the next Codex local timeout frontier inspectable instead of
opaque. It does not prove customer-ready launch, provider reliability, Agent
semantic completion, or C6 closure.
```

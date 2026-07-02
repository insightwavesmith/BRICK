# Customer-Ready P3 Launch Frontier Honesty 0627

Status: support evidence only.

This record does not create source truth, success judgment, quality judgment, or
Movement authority.

## Scope

Goal phase: P3 -- C6 one-call launch close.

Focused repair:

- The customer-facing `brick build` packet now carries the observed
  `frontier_kind` plus customer-visible frontier fields:
  - `customer_visible_frontier_state`
  - `customer_visible_not_ready`
  - `customer_visible_frontier_message`
- Non-`complete` frontiers render as `not_ready` in both JSON packet shape and
  plain CLI output.
- `FIRST_USE.md` receives the same frontier fields from the init/onboard example
  packet, so first-session delivery does not hide the frontier state.
- The CLI checker now asserts that an `agent_incomplete` frontier is rendered as
  customer-visible not-ready evidence.

## Brick / Agent / Link Attribution

Evidence first:

- P3 C6 remains HOLD on live `adapter:gemini-local` provider/auth.
- The customer CLI already emitted `frontier_kind`, but a plain
  `agent_incomplete` value was too weak as a customer-visible "not ready" surface.
- Goal v2 requires the launch wrapper to surface non-ready frontier as
  customer-visible not-ready evidence.

Brick candidate:

- The customer launch work must carry the actual Building frontier in a form a
  customer can understand before treating any output as customer-ready.

Agent candidate:

- No Agent capability or adapter authority changed. The same returned frontier is
  projected through the customer CLI.

Link candidate:

- No Link Movement, target, route policy, gate, or transition semantics changed.

Support surface:

- `support/operator/cli.py`
- `support/operator/first_use.py`
- `support/checkers/check_first_use_wizard.py`
- `support/checkers/lib/kernel_checks.py`
- `support/checkers/profiles/brick_cli_entrypoint.yaml`

Rejected one-axis shortcut:

- This was not treated as a provider/Gemini repair. It is launch-surface honesty:
  the already-observed frontier is made explicit to the customer.

Chosen repair surface:

- Support CLI/FIRST_USE projection and checker pins. No new provider SDK adapter,
  runtime, scheduler, queue, retry service, Movement literal, route selector, or
  source-truth surface was added.

## Verification

Commands run:

```text
python3 -m py_compile support/operator/cli.py support/checkers/lib/kernel_checks.py
PYTHONPATH=support/import_identity python3 - <<'PY'
from support.operator import cli
packet = {
    'repo_root': '/repo',
    'building_id': 'probe',
    'adapter_ref': 'adapter:gemini-local',
    'chain_preset_ref': cli.DEFAULT_REAL_TASK_PRESET_REF,
    'isolation_mode': 'worktree',
    'evidence_root': '/evidence',
    'frontier_kind': 'agent_incomplete',
    'customer_visible_frontier_state': cli._customer_visible_frontier_state('agent_incomplete'),
    'customer_visible_not_ready': True,
    'customer_visible_frontier_message': cli._customer_visible_frontier_message('agent_incomplete'),
    'proof_limits': list(cli.PROOF_LIMITS),
    'not_proven': list(cli.NOT_PROVEN),
}
print(cli._render_build(packet))
PY
python3 -m py_compile support/operator/cli.py support/operator/first_use.py support/checkers/check_first_use_wizard.py support/checkers/lib/kernel_checks.py
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile brick_cli_entrypoint
python3 -m compileall -q support/operator support/checkers
git diff --check
```

Observed focused evidence:

- The rendered `agent_incomplete` probe prints:
  - `frontier_kind: agent_incomplete`
  - `customer_visible_frontier_state: not_ready`
  - `customer_visible_not_ready: yes`
  - `frontier_message: not ready: Building frontier is agent_incomplete; inspect evidence_root before treating output as customer-ready.`
- `brick_cli_entrypoint` passed after the checker red from stale FIRST_USE
  fixture shape was repaired.
- `FIRST_USE.md` checker now requires the customer-visible frontier state fields.
- `compileall` passed for `support/operator` and `support/checkers`.
- `git diff --check` passed.

## Narrowly Proven

- Public CLI build rendering no longer relies only on raw `frontier_kind` for a
  non-complete Building.
- Non-complete frontier state is exposed as customer-visible not-ready evidence.
- Init/FIRST_USE first-session output carries the same frontier state fields.
- This repair does not change Link Movement or provider/adapter authority.

## Not Proven

- P3 C6 remains not customer-ready while live `adapter:gemini-local` provider/auth
  is blocked.
- Gemini Building QA success remains not proven.
- Fresh-machine install/onboard remains not fully proven.
- Full `check_profile.py --all` remains not claimed here.

## Movement

P3 launch frontier honesty: FORWARD as support evidence.

Global customer-ready goal: HOLD until Gemini-local provider/auth is fixed or
the operator declares a different non-Claude route.

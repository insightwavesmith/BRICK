# Customer-Ready P5 Gemini Readiness Honesty 0627

Status: support evidence only.

This record does not create source truth, success judgment, quality judgment, or
Movement authority.

## Scope

Goal phase: P5 -- B2 onboarding and customer first run.

Focused repair:

- `adapter:gemini-local` and `adapter:gemini-api` preflight now separate API-key
  environment presence from credential validity.
- `run_doctor()` preserves Gemini key-presence and credential-validity evidence
  instead of reducing the row to a plain `ok` boolean and message.
- CLI doctor rendering surfaces the same structured evidence.
- `building_operator_driver0` / `onboard_smoke` now checks that the Gemini doctor
  row exposes `api_key_env_present` and `credential_validity=not_proven`.
- `provider_preflight` now checks Gemini key-presence separation directly.

## Brick / Agent / Link Attribution

Evidence first:

- P3 C6 remains HOLD on live `adapter:gemini-local` provider/auth, with
  `API_KEY_INVALID` observed in Gemini client error evidence.
- P5 doctor previously reported Gemini as `ok: true` with only "gemini installed"
  style readiness when the CLI version probe passed.
- That readiness could hide the distinction between "key env exists" and "key is
  valid for a live Gemini call".

Brick candidate:

- The customer first-run work needs truthful readiness evidence before the user
  trusts a Codex/Gemini path.

Agent candidate:

- `adapter:gemini-local` is a local Agent brain connection that uses Gemini
  API-key auth. The adapter may be technically write-capable under P1, but
  credential validity is a separate provider/auth fact.

Link candidate:

- No Movement, route target, gate, or transition semantics changed.

Support surface:

- `support/connection/adapter_subprocess.py`
- `support/operator/onboard.py`
- `support/operator/cli.py`
- `support/checkers/lib/kernel_checks.py`
- `support/checkers/profiles/building_operator_driver0.yaml`

Rejected one-axis shortcut:

- This was not treated as more adapter authority. The repair does not broaden
  Gemini write capability. It only records preflight evidence more honestly.

Chosen repair surface:

- Support preflight/doctor/checker projection. No new provider SDK adapter,
  runtime, scheduler, queue, retry service, Movement literal, or source-truth
  surface was added.

## Verification

Commands run:

```text
PYTHONPATH=support/import_identity python3 - <<'PY'
from brick_protocol.support.operator import onboard
import json
packet=onboard.run_doctor()
for row in packet.get('rows', []):
    if row.get('target') == 'gemini':
        print(json.dumps(row, ensure_ascii=False, indent=2))
PY
python3 -m py_compile support/connection/adapter_subprocess.py support/operator/onboard.py support/operator/cli.py support/checkers/lib/kernel_checks.py
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile building_operator_driver0
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile brick_cli_entrypoint
PYTHONPATH=support/import_identity python3 - <<'PY'
from pathlib import Path
from support.checkers.lib.kernel_checks import run_provider_preflight
result = run_provider_preflight(Path.cwd())
print(result.check_id)
print(result.inspected)
print(result.output)
PY
python3 -m compileall -q support/connection support/operator support/checkers
git diff --check
```

Observed focused evidence:

- Gemini doctor row now carries:
  - `adapter_ref: adapter:gemini-local`
  - `authed: unknown`
  - `api_key_env_present: true` on this machine
  - `credential_validity: not_proven`
  - a message that says key validity is not proven without a live call and
    points `API_KEY_INVALID` to a new Gemini API key.
- `building_operator_driver0` passed and its `onboard_smoke` output reports:
  `gemini host appears in doctor/readiness evidence with API-key presence and
  credential_validity=not_proven`.
- `brick_cli_entrypoint` passed after the doctor rendering change.
- `provider_preflight` direct kernel passed with 7 refs inspected, including the
  Gemini key-presence / credential-validity separation.
- `compileall` passed for `support/connection`, `support/operator`, and
  `support/checkers`.
- `git diff --check` passed.

## Narrowly Proven

- P5 doctor no longer treats Gemini CLI/key presence as credential validity.
- Gemini readiness evidence is visible as structured data, not only prose.
- The customer-facing CLI doctor includes the Gemini key-presence and
  `credential_validity=not_proven` details.
- This repair does not change Link Movement or broaden Gemini write authority.

## Not Proven

- P3 C6 is still not customer-ready; live Gemini-local remains blocked until the
  provider/auth issue is fixed or a different declared non-Claude route is chosen.
- A valid Gemini key is not proven.
- Fresh-machine install/onboard remains not fully proven.
- Full `check_profile.py --all` remains not claimed here.
- Gemini Building QA success remains not proven.

## Movement

P5 focused readiness honesty repair: FORWARD as support evidence.

Global customer-ready goal: HOLD at P3 until Gemini-local provider/auth is fixed
or the operator declares a different non-Claude route.

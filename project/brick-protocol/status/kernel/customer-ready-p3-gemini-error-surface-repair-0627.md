# Customer-Ready P3 Gemini Error Surface Repair 0627

Status: support evidence only.

This record does not create source truth, success judgment, quality judgment, or
Movement authority.

## Scope

Goal phase: P3 -- C6 one-call launch close, honest frontier reporting.

Focused repair:

- `adapter:gemini-local` nonzero CLI failures already detected a
  `gemini-client-error-*.json` path in stderr.
- The previous adapter-error message carried only the terminal warning/path and
  did not surface the actual Gemini client error body.
- `support/connection/adapter_local_cli.py` now reads a small Gemini client
  error JSON file (64KB cap) and appends a redacted
  `gemini_client_error_excerpt` to the local CLI nonzero adapter-error message.

## Brick / Agent / Link Attribution

Evidence first:

- P3 rematerialized C6 evidence root:
  `project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-2`
- Raw frontier: `agent_incomplete` at the Gemini broad-review step.
- Adapter row: `adapter_ref=adapter:gemini-local`,
  `agent_object_ref=agent-object:inspector`,
  `selected_model_ref=model:gemini:default`,
  `error_kind=local_cli_nonzero`, `return_code=144`.
- Current environment has `GEMINI_API_KEY` present and `gemini --version`
  reports `0.46.0`, but the captured Gemini client error says the key is invalid.

Brick candidate:

- C6 work composition and fan shape are not changed by this repair.

Agent candidate:

- The Agent brain connection is still `adapter:gemini-local`; the failure is
  provider/auth evidence at the Agent Adapter support surface, not an Agent
  success/failure verdict.

Link candidate:

- The Link frontier remains `agent_incomplete` because no AgentFact was created.
  No Movement or target changed.

Support surface:

- `support/connection/adapter_local_cli.py`
- focused checker fixture in `support/checkers/lib/kernel_checks.py`
- source pin in `support/checkers/profiles/agent_axis_behavioral.yaml`

Rejected one-axis shortcut:

- This was not treated as a Gemini QA quality issue or as Brick route failure.
  It is an adapter-error evidence-quality repair for a provider/auth failure.

## Verification

Commands run:

```text
PYTHONPATH=support/import_identity python3 -m py_compile support/connection/adapter_local_cli.py support/checkers/lib/kernel_checks.py
PYTHONPATH=support/import_identity python3 - <<'PY' ... _local_cli_nonzero_error_message(...) ...
git diff --check
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile agent_axis_behavioral
```

Observed focused evidence:

- The direct helper probe against the captured Gemini client error file produced
  a nonzero adapter message containing:
  - `gemini_client_error_excerpt=`
  - `API_KEY_INVALID`
  - `INVALID_ARGUMENT`
  - `generativelanguage.googleapis.com`
- `py_compile` passed for the changed support/checker files.
- `git diff --check` passed.
- `agent_axis_behavioral` executed the declarative rules and reached kernel
  checks, but the full profile was blocked by stale untracked Building evidence:
  `project/brick-protocol/buildings/gemini-adapter-fileread-0626/work/building-map.json`
  has pre-existing `building_map_graph` endpoint/member-ref violations.

## Narrowly Proven

- Future Gemini-local nonzero CLI adapter-errors can surface the client error
  summary in the adapter-error message instead of only a generic terminal warning.
- The P3 observed blocker is better classifiable as provider/auth
  (`API_KEY_INVALID`) when the Gemini client error file is available.

## Not Proven

- P3 C6 is not closed.
- Gemini-local live provider success is not proven.
- Credential validity is not proven; current captured evidence says invalid key.
- The full `agent_axis_behavioral` profile is not green because stale untracked
  Building evidence blocks `building_map_graph`.
- Full `check_profile.py --all` is not claimed.

## Movement

P3 diagnostic surface repair: FORWARD as support evidence.

Global customer-ready goal: HOLD until Gemini-local provider/auth is fixed and a
rematerialized C6 Building reaches Codex work, Codex QA, Gemini QA, and Codex
closure evidence, or the operator declares a different non-Claude route.
